# INFRA-132t: 节点 `.cache` 增量同步与校验

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-130t`（`remote.py` 已有 ssh 约定）
**状态**：已验证

## 背景与事实

节点无法稳定访问公网（`curl 28` / `GnuTLS recv error`），组件裸仓库 `.cache/<name>.git` 必须由主控机提供。当前做法是**一次性 rsync 全量**，之后无人维护，风险是：

- 主控机更新了 `.cache`（新组件 / 新 commit），节点仍停在旧内容；
- 节点 `make fetch` 发现缺 commit 会转去 **访问公网**，表现为长时间挂起后失败，报错指向网络而不是「缓存过期」。

另有两项已确认事实：

- 主控机到节点**只走 Tailscale**（`ip route` = `dev tailscale0`），节点自身在 `10.42.0.207/24`，与主控机不同网；曾观测到 DERP 中继。
- `.cache` **可写**：`fetch.py` 在镜像缺失时 `git clone --mirror`、缺 commit 时 `git fetch --prune`，二者都写 `.cache`。

用户裁定（2026-11-07）：「增量同步 + 校验」；**不做 NFS/sshfs 挂载**（跨 Tailscale 挂载断链会**挂起**而非报错；只读挂载与 `fetch.py` 写入路径冲突；运行期引入主控机单点依赖）。

## 目标

新增主控机侧脚本，把「主控机 → 节点 `.cache` 增量同步 → 逐 commit 校验」固化为一条命令：

1. **增量同步**：`rsync -a` 推送 `.cache/` 到各节点（裸仓库对象 append-only，增量应显著小于全量）；带 `--dry-run` 只看计划。
2. **逐 commit 校验**：读 `manifests/components.lock.toml`，对每个组件在节点上执行
   `git -C <cache>/<name>.git cat-file -e <commit>^{commit}`，
   全部存在才算该节点 PASS；缺任意一个即 FAIL，并明确提示「缓存过期，请重新同步」。
3. **多节点**：节点清单只从 `--hosts a,b` 或环境变量 `DADAO_NODES` 取（无内置清单）；ssh 一律 `BatchMode=yes`；并发执行、逐节点汇总 `host -> rc`，任一非零则整体非零。
4. **远端路径**：节点侧仓库位置由 `--repo`（仓库根，支持 `~/`）推导出 `<repo>/.cache`；不得写死绝对路径。

## 范围 / 非范围

**在范围内**：新增 `tools/infra/sync_cache.py`、其证据脚本、本任务书、`milestones.md`、`.tao/knowledge/nodes.md`（补「缓存维护」一节）。

**不在范围**：`fetch.py` 逻辑、`Makefile` 目标、`remote.py` 子命令、组件清单、挂载方案。

## 验收标准

1. **`--dry-run`**：打印将同步的源/目标与组件清单，退出码 0，且**不产生任何远端写入**（用两个节点的 `.cache` mtime 或 `du` 前后对比证明）。
2. **真机增量**：对两台节点首次运行完整同步成功；**连续第二次运行**传输量显著小于首次（给出 `rsync` 的 `Total transferred` 实测对比）。
3. **校验正路径**：同步后两节点校验 PASS（逐组件 commit 存在），整体 rc=0。
4. **校验负路径（可达 FAIL）**：给一个**不存在的 commit**（可用临时伪造的清单条目，或在校验器上注入一个假 commit 哈希）⇒ 该节点 FAIL、整体非零，且提示「缓存过期」。注入用临时树或 `cp`+md5，禁 git 还原。
5. **节点不可达**：给一个不可达 host ⇒ 该 host FAIL、整体非零，不静默跳过。
6. **无节点清单** ⇒ rc≠0 并提示如何提供（不得有内置默认）。
7. **不写死主机信息**：脚本内无 IP / 主机名 / 账号 / 家目录字面量（`~/` 由 `$HOME` 展开）。
8. `make check`（L1）rc=0；若唯一红为外部占用（共享 gem5 源树被其它任务占用导致 `check-patch-tree`），核实归属后不算本任务失败。
9. 完成区 ≤30 行、无运行期路径；`nodes.md` 新增「缓存维护」小节：同步命令、校验判据、**禁止挂载**的原因。

## 说明

- 脚本只负责「让节点缓存与主控机一致且可校验」，**不**负责去公网更新 `.cache`（那是主控机 `make fetch` 的职责）。
- 若实测发现 rsync 对裸仓库不安全（例如并发 fetch 导致临时对象），如实记录并给出调用前提（如「主控机不得同时执行 `make fetch`」），不要用 `--delete` 静默兜底。

## 完成区

**测试结果**：证据脚本封闭模式 34/34 PASS、真实节点模式 42/42 PASS；注入→FAIL→`cp`+md5 还原→回绿全部通过；L1 唯一红为外部并发（见验收）。
**修改文件**：`tools/infra/sync_cache.py`（新增）、`.tao/knowledge/nodes.md`（§9）、`.tao/knowledge/milestones.md`、本任务书、运行期证据脚本（新增，未归档）。
**验收结果**（真实 rc）：
- `--dry-run`：两真节点 rc=0，计划传输 4,496,848 B；`.cache` 指纹（du 字节 + path/size/mtime md5）前后逐字相同 ⇒ 无远端写入。
- 真机增量：第一次 `Total transferred=4,496,848`、第二次 `0`；两节点各 11/11 PASS、overall rc=0/0。
- 全量→增量（同代码路径、完整源缓存）：首次 1,263,651,401 B、第二次 0 B，均 rc=0、10/10 PASS。
- 校验负路径：伪造 qemu commit（`deadbeef…`）⇒ `FAIL qemu … 缓存过期，请重新同步`、节点 rc=1、overall 1；`cp` 还原后 md5 与原件一致、qemu 回 PASS、整体回基线 rc。
- 不可达 host ⇒ `-> 255 (FAIL)`、overall rc=1；无节点清单 ⇒ rc=2 且提示 `--hosts`/`DADAO_NODES`；`--help` rc=0。
- 不写死主机信息：静态扫描无 IP/主机名/账号/家目录字面量；ssh 全带 `BatchMode=yes`；argv 无 `--delete`。
- `make -k check`（L1）rc=2，唯一 Error `check-patch-tree`（gem5 5 文件 × ⑥⑨，10 problem）；归属 `GEM5-030t` 未提交的 5 个 patch，与共享 gem5 源树 HEAD 的 diff 逐文件 5/5 内容一致 ⇒ 外部并发，非本任务回归。
**新发现/坑**：① 主控机 `.cache` 缺 `gem5.git`（manifest enabled），新目标节点会 `FAIL gem5: missing bare repository`；两台节点因历史缓存 + 无 `--delete` 仍 PASS。② rsync 只创建最后一层目录，`<repo>` 不存在时 mkdir 失败 rc=11 ⇒ 真跑前 `mkdir -p <repo>/.cache`（dry-run 不建）。③ dry-run 的 `--stats` 无 `Total transferred`，回落 `Total transferred file size`（计划量）。④ 并发 `make fetch` 会让 rsync rc=23/24，保留非零并提示重跑，不用 `--delete` 兜底。
**遗留问题**：主控机补 `gem5.git` 属 `fetch.py`/组件清单范围（本任务非范围）；已把「主控机缓存须先齐全」写入 nodes.md，新节点会明确 FAIL 而非假绿。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 dry-run 的 `--stats` 不打印 `Total transferred`，解析为空 | ✅已修 | 回落 `Total transferred file size` | dry-run 显示计划 4,496,848 B；真跑第二次 0 |
| F2 rsync 不建中间目录，`<repo>` 缺失时 mkdir rc=11 | ✅已修 | 真跑前远端 `mkdir -p <repo>/.cache`（dry-run 不建） | 修前 rc=11；修后首次全量 rc=0 |
| F3 enabled 组件缺 `commit` 会被静默跳过（假绿） | ✅已修 | 显式 fail rc=2 | 证据：缺 commit 清单 ⇒ rc=2 + `has no pinned commit` |
| F4 `--local` 多 host 共用同一目标目录 | ✅已修 | 多 host + `--local` ⇒ fail | 证据：`a,b` ⇒ rc=2 + `single host` |
| F5 rsync 统计行受 locale 影响 | ✅已修 | 子进程 `LC_ALL=C` | 真机与 `--local` 解析均为数值，无 `unknown` |
| F6 证据临时目录落在 worktree 根（未跟踪残留） | ✅已修 | 默认目录改到已被忽略的 `.work` 证据目录下 | `git status -uall` 仅工具/文档改动 |
| F7 证据「present 组件数」误用总数（expected=11 actual=10） | ✅已修 | 改为打印 `len(present)` | 重跑 expected=10 actual=10 |
| F8 还原后 rc 断言两侧量纲不一致（恒 FAIL） | ✅已修 | 用 `want_missing` 推基线 rc | 还原后 rc 与基线一致，PASS |
| F9 真机 PASS 计数用「主控机已有组件」而非 enabled 总数 | ✅已修 | 改用 `total_enabled` | 真机 2×11=22 PASS |

判决：F1–F9 全部已修 ⇒ 置「待验收」。

### 第 1 轮 reviewer 验收（独立重跑）

**判决：Accepted**（gem5 缺失单列见文末；2 条非阻断发现）

**重跑记录（reviewer 自行执行，真实 rc）**
- 读码：`sync_argv` = `["rsync","-a","--stats"(+"-n")]`，全文无 `--delete`（仅 3 处文档字符串提及）；`SSH_OPTS` 含 `BatchMode=yes`，`ssh_argv` 与 `rsync -e` 全走它；IP/主机名/账号/家目录字面量 grep 命中 0（rc=1）；`~/` 由 `remote_home()` 读远端 `$HOME` 拼接；校验读 `REPO_ROOT/manifests/components.lock.toml`（tomllib，enabled+commit 过滤），无硬编码组件表。
- `--dry-run` 零写入：两节点 `.cache` 指纹（`du -sb` 字节 + `find -printf '%P %s %T@' | sort | md5sum`）前 = 后、逐字相同（1282832679 / b62153ad… 与 1282832679 / 2a851d59…）；dry-run rc=0，打印目标与 11 个组件清单。
- 真机增量（造差异：节点侧暂移走 `libc-test.git`，master 持有其 pin commit）：第 1 次两节点各 `total_transferred=2573051`，第 2 次各 `0`；两次均 rc=0、各 11/11 PASS、overall rc=0；重同步 pack 与原件 `cmp` 一致后删备份，节点指纹回到与开工时完全相同（14 项 / 1282832679 B）。
- 正路径：两节点各 11 PASS（含 `gem5 c8222cc6…`）、overall rc=0。
- 负路径（临时树注入，未碰工作树）：qemu → `deadbeef…` ⇒ `FAIL qemu … 缓存过期，请重新同步`、两节点 `-> 1 (FAIL)`、overall rc=1；`cp` 还原后 md5 `882590520d3eea8afa985b2310510a79` 与原件一致，工作树 manifest md5 未变。
- 失败路径：不可达 host ⇒ `-> 255 (FAIL)`、overall rc=1；`env -u DADAO_NODES` 与 `DADAO_NODES=''` 均 rc=2 且提示 `--hosts`/`DADAO_NODES`（无内置清单）；`--help` rc=0。
- 证据脚本：default 模式 `checks=34 fails=0 / RESULT: PASS` rc=0；真节点模式 `checks=42 fails=0` rc=0（`transfer: first=1263651401 second=0`）。
- reviewer 自选注入（改被测产物）：`return verify.returncode, lines` → `return 0, lines` ⇒ 同一脚本 `checks=34 fails=3`、`RESULT: FAIL` rc=1；`cp` 还原 md5 `7f05872e2fa4b4fe9a66b5a057d06b8f` 相等后重跑回 `fails=0` rc=0。
- `make -k check` rc=2，唯一 Error `check-patch-tree`（gem5 5 文件 ×⑥⑨ = 10 problem）：本任务对 `components/gem5` 改动 0 行；共享源树 HEAD diff 与 GEM5-030t 未提交 patch **5/5 逐文件相同**、与本树 HEAD 版 5/5 不同；主工作树 `make check-patch-tree` 同样 10 problem ⇒ 外部占用，非本任务回归。
- 文档：完成区 12 行 ≤30、无运行期路径；任务书状态与 `milestones.md` 均 `待验收`；`nodes.md` §9 含同步命令 / 校验判据 / 禁挂载原因。

**约束核验**：无 `--delete` ✓｜ssh 全 `BatchMode=yes` ✓｜无主机字面量 ✓｜`~/`→`$HOME` ✓｜校验读 manifest 真源 ✓｜未动 `fetch.py`/`Makefile`/`remote.py`/组件清单 ✓｜未 commit、未 push ✓｜快照对账：`git status -uall` 与注入前逐行相同、被注入文件 md5 复原相等 ✓。

**非阻断发现**：① dry-run 只打印目标与计划量，未打印源路径（验收 1 字面要求「源/目标」），建议补一行 `source:`；② 完成区记 dry-run 计划 4,496,848 B，本次复测为 0（其后已被同步刷成一致，非判据值、时点差异）。

**gem5 单列结论**：主控机 `.cache` 确无 `gem5.git`（现有 12 个 bare 不含 gem5），manifest 中 `gem5 enabled=true commit=c8222cc6…`；两节点持有 `gem5.git` 故 PASS；空缓存模拟全新节点 ⇒ `FAIL gem5: missing bare repository`、overall rc=1。**不阻断本任务**：校验以 manifest 为真源、不会假绿，`nodes.md` §9 已写「主控机缓存须先齐全」；但同步对 gem5 失去来源保真（节点内容不来自主控机）。修复 = 主控机 `make fetch` 补 `gem5.git`，属 `fetch.py`/组件清单范围（本任务非范围）⇒ **归 architect**：本批次执行一次 fetch，或另立任务排查 gem5 拉取失败。

#### 收尾（architect，2026-11-07 22:23）

- 判决 Accepted：reviewer 独立复核 dry-run 零写入（两节点字节数与 mtime 指纹前后逐字相同）、增量 2,573,051→0 B、负路径「缓存过期」、不可达 host、无清单，均为其自跑 rc。
- F1（非阻断）：`--dry-run` 只打印目标与计划量、未打印源路径；判据字面要求「源/目标」⇒ 记为**外观缺口**，不另立任务，后续改动该脚本时顺手补。
- F2：主控机 `.cache` 缺 `gem5.git` 已单列 `ISS-349`，由 architect 在本批次修复（不塞回本任务）。
- 交付 `tools/infra/sync_cache.py`（无 `--delete`、BatchMode、manifest 真源校验、`--dry-run`/`--jobs`），`nodes.md` §9 记录同步命令/判据/禁挂载理由。
