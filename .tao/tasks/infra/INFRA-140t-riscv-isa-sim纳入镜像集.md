# INFRA-140t: 把 `riscv-isa-sim` 纳入子模块镜像集（ISS-354）

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-138t`（子模块镜像机制，已合入）
**状态**：已验证

## 用户授权（原话）

> 「做」

承接上一问「把 `toolchains/riscv-tools/riscv-isa-sim` 纳入镜像集，要不要做？」。

## 背景与事实

- `INFRA-138t` 建了 29 个 `lite = true` 子模块镜像（chipyard 上游最小集）。
- 但 conda 版 `riscv-tools` **不含 fesvr**；我们是从 `toolchains/riscv-tools/riscv-isa-sim` 源码编出 `libfesvr.a` 并装进 `<env>/riscv-tools` 的（`INFRA-133t` 记录）。
- 因此**全新机器**离线重建 RTL 环境时，还缺这一个源 ⇒ 已登记 `ISS-354`。
- 该子模块属于 chipyard 自身（`160000` gitlink，在 `.gitmodules` 中），**不是**新组件。
- 镜像已由 architect 预建：`.cache/submodules/toolchains__riscv-tools__riscv-isa-sim.git`（9.2 MiB，含锁定 commit `9c190a0…`）。

## 目标

1. **语义**：`lite` 保持「chipyard 上游最小集」原义，**不改**；为 `toolchains/riscv-tools/riscv-isa-sim` 条目新增标记 `dadao_extra = true`（并在 lock 注释里写明理由：conda 缺 fesvr，需源码编 fesvr）。
2. **`fetch.py`**：子模块选取条件由 `lite` 改为 **`lite or dadao_extra`**；`--populate-submodules` 建立镜像时同样按并集。
3. **`sync_cache.py`**：节点校验项由 `lite` 改为同一并集（当前 30 项）。
4. **文档**：
   - `docs/Process-01 §14`：补充 `lite` 与 `dadao_extra` 的区别（上游最小集 vs 本仓库额外需要）；
   - `.tao/knowledge/nodes.md §11.5`：同步说明并给出当前数量。
5. 关闭 `ISS-354`（`resolved_by: INFRA-140t`）。

## 范围 / 非范围

**在范围内**：`manifests/chipyard-submodules.lock.toml`（仅该条加标记 + 注释）、`tools/infra/fetch.py`、`tools/infra/sync_cache.py`、上述两处文档、本任务书、`milestones.md`、`issues.yaml`。

**不在范围**：其它子模块、`lite` 语义、组件镜像、chipyard 源码/构建。

## 验收标准

1. **离线复现（核心）**：临时树 + `GIT_ALLOW_PROTOCOL=file`（+ 关闭端口 proxy）跑 fetch 子模块初始化 ⇒ **30** 个（29 lite + `riscv-isa-sim`）全部在 lock commit，`submodule status` 无 `-`。
2. `sync_cache.py` 对两节点校验 **30** 项 PASS（镜像已同步后）；人为移走该镜像 ⇒ 该节点 FAIL。
3. **零回归**：原 29 个镜像与选取结果不变（数量现场统计并打印）；`make fetch` 组件部分逐行一致；`apply-series`/`check-patch-tree`/L1 与改前一致（并发任务导致的红需核实归属）。
4. 文档与实现一致（字段名 `dadao_extra`、选取并集、`sync_cache` 数量）。
5. 完成区 ≤30 行、无运行期路径。

## 说明

- 镜像已预建，`--populate-submodules` 对本条应为「已存在，跳过」；不要重新从公网克隆。
- 数量一律现场统计，不在代码/文档里写死；文档里的「30」以实测为准。

## 完成区

**测试结果**：`./run.sh`（证据脚本）**30/30 PASS**，exit 0；`./run.sh --inject` **5/5 PASS**——摘掉 `dadao_extra` ⇒ lock/fetch/sync 三项选择检查全红，`cp`+md5 还原后回绿（md5 一致）。
**修改文件**：`manifests/chipyard-submodules.lock.toml`（该条加 `dadao_extra = true` + 两条注释，`lite` 未动）、`tools/infra/fetch.py`、`tools/infra/sync_cache.py`、`docs/Process-01-组件补丁组织与构建编排.md`（§14 + §13 rev）、`.tao/knowledge/nodes.md`（§9/§11.1/§11.5）、`.tao/knowledge/issues.yaml`（ISS-354 → closed/`resolved_by`）、`.tao/knowledge/milestones.md`（流水行）、本任务书、证据脚本与 oracle（落盘于运行期证据目录，按任务号命名）。
**验收结果**（全部真实现场输出，计数现场统计）：
- 离线复现（临时树 + `GIT_ALLOW_PROTOCOL=file` + 死端口 proxy）：fetch rc=0；**30** 个必需子模块全部在 lock commit、`submodule status` 无 `-`；非必需子模块 0 个被初始化；`--populate-submodules` 同样离线 rc=0 且对本条报 `has 9c190a07c683`（未回源公网）。
- 幂等：二次 fetch 30 条 `already initialized`、0 次更新、树状态 md5 前后一致。
- `sync_cache.py`：两**真实**节点各 30 项 PASS（组件 11 项 PASS，`overall rc=0`）；本地模拟「master 侧移走该镜像」⇒ 该节点 rc=1、29 项 PASS + FAIL 指名 `riscv-isa-sim` 并提示重新同步，还原后回 rc=0/30。
- 零回归：pre-change `lite` 选取 **29** → 现并集 **30**，仅新增该条（`removed=0`）；`make fetch` 的组件部分与改前 `fetch.py` 逐行一致（33 行）。
- `apply-series`/`check-patch-tree`/L1：与改前（`HEAD` 的 detached 工作树、共享同一 `.cache`/`.work`）**一致**——`apply-series`/`check-patch-tree` 输出逐行相同，L1 失败集合逐条相同（台账行数变化属本任务正常改动，故按失败集合对照）；三者当前均 rc=2，唯一红点是 `check-patch-tree` 报 qemu `linux-user/mmap.c`、gem5 `src/arch/dadao/se_workload.cc` 的本地 commit/worktree 与本册补丁集不符 ⇒ 归属并发 `QEMU-085t`/`GEM5-028t` 改共享源树，**非本任务引入**。
- `make check-modules`（L2）rc=0；`check-run-artifacts` PASS；`manifest-check`/`check-issues`（10 closed/5 open，`resolved_by` 约束 OK）/`check-knowledge-refs`/`check-knowledge-dir`/`check-tasks`/`check-milestones-fresh` 均 rc=0。
**新发现/坑**：① 计数：`grep -c 'lite = true'` 会数进文件头注释（报 30），一律 `tomllib` 现场统计。② 「改前对照」不要依赖旧日志（缺基线即形同恒绿）：用 `git worktree add --detach HEAD` 起 pristine 树、共享同一 `.cache`/`.work`，再与任务树逐行 diff，可把并发任务造成的红与本次改动区分开。③ 对照 L1 输出须先归一化两棵树的绝对路径并剔 `gate-lock:` 行（并发持锁行会造成伪 diff）。④ `sync_cache.py` 无法在真节点上演示「镜像缺失失败」——rsync 会立即把它补回去，只能在本地模拟 master 侧缺镜像。⑤ `--populate-submodules` 的「已存在」判定看 `cat-file -e <pin>^{commit}`，不是看目录是否存在。
**遗留问题**：本任务无未完成项。共享源树的 `apply-series`/`check-patch-tree`/L1 目前为红（并发任务所致，与改前逐行一致），建议 `/complete` 收尾时在并发任务落地后复跑确认；本改动不触编译输入，未重建任何组件。

## 审阅记录

### 第 1 轮 reviewer 验收

**重跑记录（本人终端输出 / 真实退出码）**
- 证据脚本全量：`checks=30 failures=0`、`RUNSH_EXIT=0`（两次：首跑 + 还原后回绿）；`--inject` 重跑 `checks=5 failures=0`、`INJECT_EXIT=0`，还原 md5 与注入前一致。
- **独立注入**（`cp` 备份 + md5 记录，删该条 `dadao_extra = true`，重跑同一脚本）：`INJECTED_RUN_EXIT=1`、`checks=30 failures=14`，红含 A1/A2/A3（`expected=30 actual=29`）、B2、E3/E4（FAIL 指名 `riscv-isa-sim` + 重新同步提示）、G1（两节点各 29）；`cp` 还原后 md5 相等、`git status` 与注入前快照逐行相同，再跑同一脚本 `checks=30 failures=0`、`RESTORED_RUN_EXIT=0`。
- 离线复现（本人自建临时树 + `GIT_ALLOW_PROTOCOL=file` + 三 proxy 死端口 + 空 git 全局配置）：fetch `rc=0`；55 行 `submodule status` = 30 初始化 / 25 未初始化，30 个必需项全在 lock commit，非必需初始化 0 个，`fatal/error/not allowed/unable to access` 均 0；`--populate-submodules` 同样 `rc=0`、30 条 `has <pin>`、克隆 0 次。
- 失败路径（本人自建 master/node fixture，master 侧移走该镜像 + 全新节点）：`RC_FAIL=1`、`PASS submodule=29`、`FAIL submodule toolchains/riscv-tools/riscv-isa-sim: missing bare mirror …` + `re-run the sync`；还原 `RC_GREEN=0`、`PASS=30`、FAIL 0。fetch 侧移走镜像 `rc=1` 并指名该子模块，还原 `rc=0` / 30。
- 零回归：`tomllib` 现场统计 `lite` 29→29 且集合逐条相同、并集 30、`dadao_extra` 仅该条、该条仍 `lite = false`；组件行 33 = 33 逐行 `IDENTICAL`；子模块行 29→30，diff 仅新增该条。
- L1：`make -k check` `L1_K_EXIT=2`，唯一红点 `check-patch-tree: 4 problem(s)`（qemu `linux-user/mmap.c` ×2、gem5 `src/arch/dadao/se_workload.cc` ×2），与 HEAD 基线失败集合逐条相同；本任务 8 个改动文件不涉 `components/`，共享源树的本地 commit 属并发 `QEMU-085t`/`GEM5-028t` ⇒ 非本任务引入。`manifest-check` / `check_issues`（5 open、10 closed，`resolved_by` 约束 OK）/ `check-tasks` 均 rc=0；L2 `check-modules` rc=0。
- 文档：`du` 现场 275 与 §14「约 275 MiB」一致；镜像目录 30 个；`tomllib` 29+1=30 与 nodes.md §9/§11.1/§11.5 一致；两真实节点 `gxt@server207:30, gxt@server208:30 (overall rc=0)`。
- 快照对账：审查前后 `git status --porcelain -uall` 逐行相同（8 个改动文件），被改的 5 个文件 md5 前后相同。

**约束核验**：`lite` 未改；选取条件为 `lite or dadao_extra` 并集（`fetch.py` / `sync_cache.py` 各一处，无硬编码计数）；完成区 14 行、无运行期路径；`ISS-354` 已 `closed` + `resolved_by: INFRA-140t`；本人未 commit / 未 push。

**判决**：**Accepted**。非阻断 finding（交 architect 收尾改）：① `docs/repository-layout.md` 仍写「当前为 chipyard 的 `lite` 集」，未随并集口径更新（措辞滞后，非数字/门控问题）；② 台账已按新规则三表化，而本行按其基线的「任务流水（已开工）」表落位，合并时需把该行移入「进行中」表。

**三问**：① `lite` 语义是否保持 —— **是**（29 条集合逐条相同、该条仍 `lite = false`，本仓库额外需求单列 `dadao_extra`）。② 离线是否真的只靠镜像 —— **是**（协议白名单 + 死端口 + 空全局配置下 rc=0、克隆 0 次、无任何网络错误）。③ 文档数字与现场是否一致 —— **是**（275 / 30 / 29+1 现场复测均相符；仅 `repository-layout.md` 一处措辞滞后，不涉数字）。

### 第 1 轮 engineer 自审

逐行审查 `fetch.py` 并集条件、`sync_cache.py` 同并集、锁册标记与两处文档口径的一致性；并逐条核对证据脚本每项断言是否存在可达 FAIL 路径。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| 1. `fetch.py` 报错文案仍写 "lite submodule"，与并集语义不符 | ✅已修 | 改 "required submodule"，空集提示 "no lite = true / dadao_extra = true submodule" | A2/B1 现场输出 |
| 2. §14「理由」仍写镜像「约 260 MB」，与实测（含新镜像 275 MiB）不符 | ✅已修 | 改「当前 30 条合计约 275 MiB（`du` 现场统计）」 | `du -sm .cache/submodules` = 275 |
| 3. 首版「改前对照」依赖旧日志，基线缺失即 SKIP（可恒绿） | ✅已修 | 改为 `worktree add --detach HEAD` pristine 树逐行对照，删掉 SKIP 分支 | F5/F6/F7 真 rc + 逐行一致 |
| 4. 归一化先替换 `$REPO`，把 baseline 路径截成 `@REPO@-tmp/baseline` 伪 diff | ✅已修 | 先替换长前缀（baseline）再替换 `$REPO`，并剔 `gate-lock:` 行 | F7 当时由 FAIL 转 PASS（63 行全文一致；后按失败集合对照，见 #8） |
| 5. 未覆盖「`--populate-submodules` 不得回源公网」（任务要求） | ✅已修 | 加 B4/B5：死端口 proxy 下跑 populate，要求 rc=0 且报「已含 pin」 | B4/B5 PASS |
| 6. 未跑 L2（AGENTS 收尾要求） | ✅已修 | 证据脚本加 H1 跑 `make check-modules` | H1 PASS（rc=0） |
| 7. `oracle.py check-lock` 传 dict 给只接受 commit 字符串的比较函数（首跑崩） | ✅已修 | 取出 commit 建映射后再比较，另加 url 比对 | A1 rc=0（30/30） |
| 8. L1 对照用全文 diff 会因本任务改台账行数（流水 95→96 等）产生**合法**差异，掩盖真实回归 | ✅已修 | L1 改为对照「rc + 失败集合」；工具链输出仍用全文 diff | F7 failure-set 一致（5 条）；改前/改后同 rc=2 |
| 9. 完成区写了具体 `.work/**` 证据路径 ⇒ `check-knowledge-refs` 红 | ✅已修 | 改为「落盘于运行期证据目录」 | check-knowledge-refs rc=0 |
| 10. 台账流水行状态非 `已验证` 未加 `（登记）` ⇒ `check-milestones-fresh` 红 | ✅已修 | 完成时间改为 `12:40（登记）` | check-milestones-fresh rc=0 |

#### 收尾（architect，2026-11-08 14:20）

- 判决 Accepted：reviewer 独立注入（删 `dadao_extra`）⇒ 14 条 FAIL（`expected=30 actual=29`、两节点 `29/29`），还原后 30/30；离线复现 30 个全到位、`--populate-submodules` 克隆 0 次；`lite` 29→29 集合不变。
- F1：`docs/repository-layout.md` 的 `.cache/submodules` 说明改为「`lite ∪ dadao_extra` 并集（29 + `riscv-isa-sim`）」，与实现一致。
- F2：台账行按三分表规则处理（本任务 `已验证` → 「已验证」表 + 完成时间）；分支基线为旧表格式，合并时以主树台账为准。
- 数字口径：镜像 30 个 / 275 MiB；`lite` 29 不变；`ISS-354` 关闭。
