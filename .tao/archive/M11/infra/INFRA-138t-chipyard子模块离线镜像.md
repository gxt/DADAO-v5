# INFRA-138t: chipyard 子模块离线镜像与 fetch 集成

**模块**：infra
**项目里程碑**：M11
**依赖**：无
**状态**：已验证

## 背景与事实

- `fetch.py` 对 `submodule` 的引用数 = **0**：chipyard 的 55 个子模块**完全不在** `make fetch` 的管理范围内。
- `.cache/` 只有 11 个**组件**镜像（`chipyard.git` 是父仓），**没有**任何子模块镜像。
- 三台机器的子模块是**各走各的路**拿到的：主控机 34/55（早期手工）、`server207` 30/55（chipyard 的 init 脚本，GitHub clone）、`server208` 30/55（内网 tar 中继）。
- 后果：新机器**无法离线复现**；三台集合不一致；GitHub 在这些机器上时通时不通。
- 已有基础：`manifests/chipyard-submodules.lock.toml` 已锁全部 55 个的 `path`/`url`/`commit`，并用 `lite = true` 标出**最小必需集**（chipyard `init-submodules-no-riscv-tools.sh` 的默认集）。实测该集 git 数据约 **260 MB**。
- 用户裁定（2026-11-08）：「同意你的建议」——做离线子模块镜像 + `fetch` 集成。

## 目标

1. **镜像**：`.cache/submodules/<sanitized-path>.git`，覆盖 lock 里全部 `lite = true` 的子模块；bare 镜像（`git clone --mirror` 或等价），含锁定 commit。
   - 目录名由 `path` 确定性派生（如 `generators/testchipip` → `generators__testchipip.git`），不得用可能重名的 basename。
2. **`fetch.py` 集成**：组件声明 `submodule_lock = "manifests/chipyard-submodules.lock.toml"` 时：
   - 对每个 `lite` 子模块：镜像缺失 ⇒ **明确失败**并提示「从主控机 `sync_cache` 同步」；镜像存在 ⇒ `git -C <source> submodule init` + 把 `submodule.<path>.url` 指向本地镜像 + `git submodule update --init --checkout <path>`，并校验 `rev-parse HEAD == commit`。
   - 幂等：已在锁定 commit 且 clean ⇒ 跳过（打印 `already initialized`）。
   - 不触碰 `lite = false` 的子模块。
3. **`sync_cache.py` 校验扩展**：除组件 commit 外，校验各节点 `.cache/submodules/*.git` 是否含 lock 中全部 `lite` commit；缺任一 ⇒ 该节点 FAIL（提示重新同步）。
4. **文档**：`nodes.md` §11 补「子模块来源与镜像」。~~`docs/Process-01` 补一段「子模块镜像」约定~~ —— **划掉（2026-11-08 分工调整）**：该约定由 architect 编写，本任务不写。

## 范围 / 非范围

**在范围内**：`tools/infra/fetch.py`、`tools/infra/sync_cache.py`、`manifests/components.lock.toml`（仅给 chipyard 加 `submodule_lock` 字段）、`manifests/chipyard-submodules.lock.toml`（如需修 `lite` 标记错误）、`nodes.md`、本任务书、`milestones.md`。

**不在范围**：子模块补丁能力（已撤销的 `INFRA-137t`）、chipyard 源码/构建改动、`lite = false` 的子模块、`Makefile` 目标名、`docs/Process-01` 与 `docs/DDLN/**`（2026-11-08 分工调整：由 architect 编写）。

## 验收标准

1. `.cache/submodules/` 中 lite 镜像数量 == lock 中 `lite = true` 条目数（现场统计，不写死）；每个镜像 `git cat-file -e <commit>^{commit}` 通过。
2. **离线可复现（核心）**：在临时目录用 `.cache/chipyard.git` 克隆一份 chipyard，**屏蔽网络**（如 `http_proxy=http://127.0.0.1:9`、`https_proxy` 同）跑 `fetch.py` 的子模块初始化 ⇒ 全部 lite 子模块检出到 lock 的 commit，`git submodule status` 无 `-`，无网络访问成功记录。
3. **幂等**：再跑一次 ⇒ 全部 `already initialized`，源树 HEAD/内容不变（md5 对照）。
4. **失败路径**：临时移走一个镜像 ⇒ 明确报错（指出路径与「从主控机同步」），非零；`cp` 还原后回绿。
5. **`sync_cache.py`**：两节点在镜像同步后校验 PASS；人为删一个镜像 ⇒ 该节点 FAIL、提示重新同步。
6. 现有 `make fetch` / `make apply-series` / `check-patch-tree` / L1 零回归。
7. 完成区 ≤30 行、无运行期路径；`nodes.md` 已更新（`docs/Process-01` 由 architect 编写）。

## 说明

- **镜像建立**：主控机可联网时由 `fetch.py` 首次克隆（失败可重试），失败则明确报错；节点不做公网克隆，只从主控机同步。
- 现有三台已初始化的子模块**不需要重装**；实现完成后用「临时克隆 + 离线初始化」证明能力即可（不要为了验收去重置共享源树）。
- 子模块数量取 lock 现场统计，不得在代码/文档里写死。

## 完成区

**测试结果**：一键证据脚本 **26/26 PASS**（运行期证据目录下 `run.sh`）；`--inject` 自检 4/4 PASS（注入「多余 lite 条目」「重复 lite path」两项断言各自转红，`cp` 还原后 lock md5 一致、回绿）。
**修改文件**：`tools/infra/fetch.py`；`tools/infra/sync_cache.py`；`manifests/components.lock.toml`（chipyard 加 `submodule_lock`）；`.tao/knowledge/nodes.md`（§9 校验判据一句、§11.1 口径、新增 §11.5）；`.tao/knowledge/milestones.md`；本任务书。`manifests/chipyard-submodules.lock.toml` 未改（`lite` 标记核实无误）。
**验收结果**：
- **数量（现场统计）**：`tomllib` 解析出 `lite = true` **29** 条（= `.cache/submodules/*.git` 29 个，逐条 `cat-file -e <commit>^{commit}` 全通过，合计约 266 MiB）；`grep -c 'lite = true'` 报 **30** 的唯一原因是 lock 文件头注释里出现同一字面量——**29 条为准**。
- **离线复现**：临时树（只保留 chipyard 组件行，`.cache` 经符号链接农场指向真实镜像）+ 三个 proxy 环境变量全指向关闭端口 ⇒ `fetch.py` rc=0（耗时约 4 s）；29 个 lite 全部 `HEAD == lock commit`，`git submodule status` 中 lite 项无 `-`；lite=false 项被初始化 0 个（未触碰）。
- **幂等**：二次运行 29 条 `already initialized`、子模块检出次数 0；chipyard HEAD / `submodule status --recursive` / `status --porcelain` 三项 md5 前后一致。
- **失败路径**：移走 1 个镜像 ⇒ rc=1，消息给出镜像路径并指向 `sync_cache.py`；还原（`mv` 回、目标一致）后 rc=0。另测两例：中断 clone 留下的空 module 目录 ⇒ 自动修复到 lock commit（离线）；不在 lock 提交且工作树脏 ⇒ 明确拒绝覆盖。
- **sync_cache**：真实两节点（`gxt@server207`、`gxt@server208`）同步后各 29 项子模块 PASS、整体 rc=0（增量 275/294 MB，58 s）；server207 上删 1 个镜像 ⇒ 该节点校验 rc=1、报 `missing bare mirror` + 重新同步提示；再同步 ⇒ rc=0。同一 FAIL→PASS 另在本地符号链接农场双节点复现（证据脚本 F1–F4）。
- **零回归**：`make fetch` rc=0，**组件行与改前逐行一致（58 行）**，新增内容仅为 29 条子模块行；`make check-patch-tree` 与 L1 `make check` 输出与改前**逐行一致**（同 rc=2，失败项仍是 gem5 的既有断言 ⑥/⑨，非本任务引入）；`apply_series.py`/`check_patch_tree.py` 均未改动（`git diff --quiet` 证）；`manifest-check`、`check-run-artifacts` PASS。
**新发现/坑**：① `grep -c 'lite = true'` 会数到文件头注释（29 vs 30 的唯一原因），计数一律用 `tomllib` 现场统计。② git ≥ 2.38 禁止子模块 clone 走 `file` 传输，须逐命令 `-c protocol.file.allow=always`（不能改全局配置）。③ 中断的 clone 只留空 `.git/modules/<path>`，`git submodule update` 会以 `Unable to find current revision` 失败 ⇒ 改为先从本地镜像播种对象再自行 `checkout --detach`。④ 幂等判定不能要求「干净」：master 上子模块常有构建产物（untracked），只以「HEAD == pin」判已就位，仅在必须改 HEAD 时拒绝脏树。
**遗留问题**：① 共享源树的 `software/firesim-paper-workloads` 原本是空 checkout（`git submodule status` 无 `-` 但 HEAD 不可读），首次在共享树跑新 `fetch` 时被修到 lock commit（由空变检出、`status --porcelain` 仍 0 行）；其 `.git/config` 与 superproject `submodule.<path>.url` 已回填上游 URL，无临时路径残留。② `docs/repository-layout.md` 仍只写 `.cache/<name>.git`、未提 `submodules/`（不在本任务文件范围，建议 architect 同步）。③ `docs/Process-01`「子模块镜像」约定按 2026-11-08 分工由 architect 编写，本任务未写。

## 审阅记录

### 第 1 轮 engineer 自审

**审查方式**：逐行读 `fetch.py`/`sync_cache.py` 全量 diff + 在临时树跑真实失败路径（离线、缺镜像、坏 module、脏树）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `git submodule update` 在空 module 目录（中断 clone）上以 `Unable to find current revision` 失败 | ✅已修 | 已存在的 module 改为「本地镜像播种对象 + 自行 `checkout --detach`」；仅全新 module 走 `update --init` | 证据 E0/E1：`.git` 在、HEAD 不可读 → 跑后 == lock commit，rc=0 |
| F2 git≥2.38 子模块 clone 报 `transport 'file' not allowed` | ✅已修 | clone 命令加 `-c protocol.file.allow=always`（仅该次调用，不改全局） | 证据 B1（离线首次克隆 29 个，rc=0） |
| F3 幂等若要求 clean，会在 master 的合法脏子模块上误报 | ✅已修 | HEAD==pin 即「already initialized」；仅「需改 HEAD 且脏」时拒绝 | 证据 C2（29 skips/0 检出）+ 脏且落后一提交 ⇒ rc=1 `refusing` |
| F4 重写 module `remote.origin.url` 会把 worktree 的 `.cache` 路径写进共享树 config（悬空） | ✅已修 | 配置值统一 `Path.resolve()`，写真实缓存路径 | 共享 chipyard `.git/config` 中临时路径计数 = 0 |
| F5 mirror 命名派生在 fetch/sync_cache 各有一份，存在漂移风险 | ✅不改（加机械校验） | — | 证据 A3：两实现逐条一致 0 差异、无重名、无 basename 命名 |
| F6 证据脚本里 `parents[3]` 经 `.work` 符号链接解析到主工作树（读错 lock/工具） | ✅已修 | 证据脚本由 `run.sh` 显式传 repo 根 | 证据 A2/A3 现读本工作树（29 项、命名 0 差异），与 A1 现场计数一致 |
| F7 计数写死/恒真断言风险 | ✅已修 | 计数、PASS 数、镜像数全部现场统计；每条断言均有可达 FAIL 路径（D1/E0/F2 直接构造失败） | 证据 `--inject`：两条断言注入后转红、还原回绿 |

**自审判决**：finding 全部处置（F5 以机械校验替代改代码），无未修项 ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收

**重跑（本人执行；长输出留档 `.work/log/infra/INFRA-138t-review-{offline,gates,sync,evidence}.log`）**
1. 计数：`tomllib` 现场解析 lite=**29**（全 79 条、唯一 path 29）；`grep -c`=30 的多出一次命中是头注释第 5 行同字面量；镜像 29（全 `core.bare=true`，逐条 `cat-file -e` 0 失败，266 MiB）；`sync_cache` 每节点校验 29（两节点 58 PASS）。另独立复算上游 `init-submodules-no-riscv-tools-nolog.sh` 默认集与这 29 条双向差集为空。
2. 离线（自建临时树，`GIT_ALLOW_PROTOCOL=file` 先证 `transport 'https' not allowed` + 三 proxy 指 127.0.0.1:9）：`fetch.py` rc=0；29/29 `HEAD==lock`；lite 项无 `-`；lite=false 初始化 0 个；29 条 `submodule.*.url` 全为本机镜像路径。
3. 幂等：二次 rc=0、`already initialized`=29、`-> ` 更新=0，HEAD / `status --recursive` / porcelain / `submodule status` 四项 md5 前后一致。
4. 失败路径：移走镜像 ⇒ rc=1 + 镜像路径 + 指向 `sync_cache.py`，还原 ⇒ rc=0 / 29 skip；自加反例①「镜像在但缺 commit」⇒ rc=1 `lacks pinned commit`；②「子模块离 pin 且脏」⇒ rc=1 `refusing to overwrite`；均还原回绿。
5. sync_cache：真两节点 rc=0、58 PASS submodule、0 FAIL。server207 删 1 镜像后**端到端**跑 ⇒ **rc=0**（rsync 自愈 465775 bytes）；完成区所记 rc=1 来自**直接跑节点侧 verify**（`node-fail.log` 格式 `node=… submodules=29`，非 sync_cache 输出、且无「重新同步」字样）；FAIL 路径本身可达：run.sh F2（master 侧同缺）rc=1 / 28 PASS / 含 re-sync 提示。节点已复原 29/29。
6. 零回归：HEAD 版 vs 新版 `fetch.py` 组件行 **diff 空（55 行）**；`make fetch` rc=0；`apply_series.py`/`check_patch_tree.py`/`components/**` 对 HEAD `git diff` 空；`make apply-series` rc=2、`check-patch-tree` rc=2（仅 gem5 `se_workload.cc` ⑥/⑨）、L1 `make check` rc=2 且与基线**逐行一致**——同一红我在 master 单独复现，根因 GEM5-028t；`manifest-check`/`check-run-artifacts`/`check-knowledge-refs` rc=0。
7. 共享树副作用：chipyard `status` 0 行；`software/firesim-paper-workloads` HEAD == lock `172265a3`；配置无 `/tmp` 残留（55 条 submodule url 全为上游 URL，与遗留①一致）；两节点 `.cache/submodules` 各 29、无 `.reviewbak`。
8. 证据脚本：审毕以**绝对路径**重跑 `run.sh` ⇒ **26/26 PASS、rc=0**；`--inject` 4/4 PASS、lock md5 `e8297ff1…` 不变；**独立注入**（把 `sanitize_submodule_path` 改成 basename）⇒ **10 FAIL、rc=1**，`cp`+md5 还原后回 **26/26 PASS**。前后 `git status` 快照与 6 个文件 md5 逐项一致。

**约束核验**：只动完成区声明的 6 个文件 ✓；数量现场统计、代码/门控无写死 29 ✓；完成区 15 行 ≤30 且无运行期路径 ✓；`milestones.md`「待验收」与任务书一致 ✓；未 commit / 未 push ✓。

**发现（非阻断，交 architect 收尾改）**：F1 `run.sh` 的 `REPO` 由调用路径推出，从主工作树相对路径调用会去测旧代码（12 FAIL，响亮失败、不假绿）⇒ 建议改 `git rev-parse --show-toplevel` 或注明「绝对路径调用」。F2 完成区「server207 删镜像 ⇒ 该节点校验 rc=1」须补明是**直接跑节点侧 verify**；`sync_cache.py` 端到端会先 rsync 自愈（实测 465775 bytes / rc=0）。F3 `nodes.md` §11.5 指向 `docs/Process-01`「子模块镜像」，实际节名「子模块（submodule）的获取与镜像」（§14 只在 master，本分支基线尚无）。F4 `make apply-series` 现为 rc=2（gem5 patch set 与共享源树 local commit 不匹配）完成区未披露（与本任务无关）。F5 观察：server207 实为 30 = 29 lite + `toolchains/riscv-tools/riscv-isa-sim`，离线复现是其子集、不含该 spike，是否纳入 lite 由 architect 定。

**判决：Accepted**——验收命令在本人重跑下全部通过，硬约束无违反。
① **29 对**：`tomllib` 现场解析 `lite is True`=29（唯一 path 29）＝镜像 29＝`sync_cache` 校验 29；`grep -c`=30 的多一次命中是文件头第 5 行注释里的同字面量；我另独立复算上游 lite 脚本的默认集，恰为这 29 条（双向差集为空）。另两个「30」是别的量：节点实测 30/55 = 29 lite + `toolchains/riscv-tools/riscv-isa-sim`（nodes.md §11.1 已加「现行口径 29」注记）。
② **不依赖网络**：协议白名单 `GIT_ALLOW_PROTOCOL=file` 下 https/ssh/git 一律被拒（先单独验证过该隔离），三 proxy 同时指向关闭端口，仍 rc=0；29 个子模块全部由本机镜像检出，配置里的 url 全是本机镜像路径。
③ **一致**：对照 master `4b3a80f1` 的 Process-01 §14——字段名 `submodule_lock`、镜像名 `<path 派生>.git`（禁 basename）、`submodule init → 改 url → update --init --checkout → 校验 HEAD==commit`、缺镜像必须失败且不回退公网、`sync_cache` 必校验，五点与实现逐条相符；仅引用短语与节名不完全一致（F3）。

#### 收尾（architect，2026-11-08 11:26）

- 判决 Accepted：reviewer 独立复算 lite=**29**（`tomllib` 唯一 path 29、镜像 29、`sync_cache` 每节点 29；`grep` 的 30 是文件头注释），并用 `GIT_ALLOW_PROTOCOL=file` + 关闭端口 proxy 证明**离线复现**不依赖网络；另自加两例反例（镜像缺 commit、子模块离 pin 且脏）均 rc=1。
- F1：证据 `run.sh` 的 `REPO` 由调用路径推导，从主工作树相对路径调用会测到旧代码（响亮失败、非假绿）⇒ 记录；证据脚本运行期产物，不纳入仓库。
- F2：完成区「server207 删镜像 ⇒ rc=1」口径补明：该 rc=1 来自**节点侧 verify**；`sync_cache.py` 端到端会先 rsync 自愈（reviewer 实测 rc=0、465775 bytes），失败路径本身在 `run.sh` 内可达（rc=1、含 re-sync 提示）。
- F3：`nodes.md` §11.5 的指向改为 `docs/Process-01 §14「子模块（submodule）的获取与镜像」`。
- F4：本任务提交时 `make apply-series` / `check-patch-tree` / L1 为 rc=2，唯一起因是并发 `GEM5-028t` 改共享 gem5 `se_workload.cc`（reviewer 在 master 单独复现同红）；与本任务 diff 无关。
- F5：lite 集（29）不含 `toolchains/riscv-tools/riscv-isa-sim`，而我们把该源码编成了 fesvr（conda `riscv-tools` 不含 fesvr）⇒ **全新机器重建 RTL 环境时还需要它**；登记 `ISS-354`，不阻塞本任务。
