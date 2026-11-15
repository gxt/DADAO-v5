# m12-infra-003: 子模块补丁机制（恢复 `INFRA-137t` 方向）

**模块**：infra
**项目里程碑**：M12
**可并行分片**：否（工具改动单写者；试点需 chipyard 源树独占）
**状态**：已验证

## 用户裁定（原话）

「我们当然需要给子模块打 patch，现在不做，以后也要做」（2026-11-09）

此前 2026-11-08 以「不调试 chipyard 本身」为由撤销了 `INFRA-137t`；该理由现被推翻，方向恢复。

## 背景与事实

- `tools/infra/apply_series.py` 只处理顶层组件：读 `component["patch_dir"]`/`patch_series`，在组件源树根应用。
- `manifests/components.lock.toml` 的组件体例没有子模块路径字段；`check_patch_tree.py` 的断言按顶层路径匹配。
- `m12-chipyard-003` 需要给 `generators/testchipip/src/main/resources/testchipip/vsrc/SimDRAM.v` 打补丁（`MEM_BASE` 未声明位宽，默认 32 位，Tiny 的 48 位基址会被截断），当前机制做不到。

## 目标

1. **manifest schema**：组件条目新增可选字段（如 `submodule_patches`），声明「子模块路径 → 补丁目录/系列」；不破坏现有顶层补丁组件。
2. **`apply_series.py`**：按声明进入子模块工作树（`<源树>/<子模块路径>`）应用对应系列，生成独立本地 commit；顶层与子模块两类互不影响。
3. **`make_patch.py`**：支持从子模块工作树导出补丁（一文件一补丁、`new file mode` 齐备）。
4. **`check_patch_tree.py`**：断言覆盖子模块补丁（HEAD diff、patch↔worktree 一致性、source-state clean）。
5. **`docs/Process-01`**：登记子模块补丁的组织方式与适用范围（不复制 chipyard 全量子模块，只登记实际要改的）。
6. **试点**：用 testchipip 的 `SimDRAM.cc`/`SimDRAM.v` 补丁验证端到端——补丁导出、`apply-series`、门控、`check-source-state`。
   - 选型理由：`SimDRAM.cc` 的 `get_target_endianness()` 固定返回 `little`，即使 fesvr 开 `--enable-dual-endian` 仍会在 dual-endian 分支 throw；这是**已确认的实际缺口**（不依赖 Tiny 当前是否用 SimDRAM）。

## 验收标准

1. 试点补丁可 `git apply --check` 重放；`apply-series` 后子模块工作树 state 正确（独立 commit、clean）
2. `check-patch-tree` 覆盖子模块且能对「补丁与源树不一致」报红（可达 FAIL 注入）
3. 顶层组件补丁行为不变（回归：现有 314 份仍 OK）
4. `make apply-series` / `check-source-state` / `check-patch-tree` / L1 / L2 rc=0（两节点验证；改完执行 `make sync-node-repo`）
5. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
6. 完成区 ≤30 行、无运行期路径

## 非范围

- 不批量纳入所有子模块（只登记实际要改的）
- 不改 chipyard 上游代码语义（只做补丁机制）
- 不动 `m12-chipyard-003` 的核实现（该任务返工另行处置）

## 说明

- 子模块工作树由 `fetch.py` 从本地镜像检出；补丁必须能在这份检出上重放，不能依赖联网。
- 构建/运行在 `server207`；仓库修改在主控机。

## 完成区

**测试结果**：一键证据 28/28 PASS、rc=0（运行期证据目录，未归档）；`check-patch-tree` 9 集 324 份（顶层 322 + testchipip 2）；两节点 L2 rc=0、L1 51 目标 rc=0（合并后台账状态，见验收 4 与遗留①），日志在运行期日志目录（`m12-infra-003-s207-ledger-L1.log` / `-s207-L2.log` / `-s208-ledger-L1.log` / `-s208-ledger-L2.log`，均未归档）。
**修改文件**：
1. `tools/infra/submodule_patches.py`（新）：`submodule_patch` schema 唯一读取点（`patch_sets`/`lock_commits`/`base_commit`/`worktree`）。
2. `tools/infra/{apply_series,check_patch_tree,make_patch,fetch,manifest_check,check_index_blobs}.py`。
3. `manifests/components.lock.toml`：chipyard 增 `[[component.submodule_patch]]`（`generators/testchipip`）。
4. `components/chipyard/submodules/testchipip/{series,patches/src/main/resources/testchipip/csrc/SimDRAM.cc.patch,patches/src/main/resources/testchipip/vsrc/SimDRAM.v.patch}`（新，试点）。
5. `components/chipyard/{README.md,changelog.md}`、`docs/Process-01-组件补丁组织与构建编排.md`（§7/§8/§13/§14）、`docs/repository-layout.md`、`docs/README.md`（索引行）、`Makefile`（2 条 help 文本）、本任务书。
**验收结果**：
1. 试点可重放：两份补丁在 pin `26f821b` 上 `git apply --cached --check` rc=0、工作树 `--reverse` rc=0；`make apply-series` 后 testchipip `count=1 clean=True`（独立 commit）、chipyard `count=1 clean=True` 且 `HEAD:generators/testchipip` == 子模块 HEAD；再跑二者均 `already applied`。
2. 门控覆盖子模块：9 集 324 份 rc=0。可达 FAIL 注入三条——改 hunk 上下文 ⇒ 断言④/⑨ 红；子模块多一空 commit ⇒ 断言⑦/⑧/⑩ 红；patchless 组件带 `submodule_patch` ⇒ manifest-check 红；均 `cp`+md5 还原后回绿。另注入「去掉 `make_patch` 的 gitlink skip」⇒ 试跑确实列出 `generators/testchipip.patch`（该 skip 承重），真件列出 0 条。
3. 顶层回归：`make-patch` 顶层 16 份 0 改写、322 份总数不变；顶层集不导出 gitlink 路径。
4. `make apply-series`/`check-source-state`/`check-patch-tree`/`fetch` rc=0（fetch 报 testchipip `locally patched HEAD`，不覆盖本地补丁 commit）。**两节点**（server207/server208，注入本交付 18 文件后实测）：L2 `module checks (L2): PASS` rc=0；L1 51 目标 `repository checks (L1): PASS` rc=0，含 `check-musl-freshness: PASS` 与 `check-patch-tree: 9 patch set(s), 324 patches OK`。**未覆盖台账的分支原样跑**只剩 `check-milestones-fresh` 一项红（A1/R1 均指向本任务行，属基线差异，见遗留①）。
5. 证据脚本：运行期证据目录 `run.sh`（非交互、逐项打印期望/实际、失败非零、内置 4 处注入→还原自检），28/28 rc=0。
**新发现/坑**：①组件索引对子模块路径只有 gitlink ⇒ `git apply --cached` 报 `does not exist in index`，子模块补丁集只能在子模块仓库成集、父 commit 记录 gitlink，否则 E1 永不干净；②子模块 commit 必须被父 commit 钉住（新断言⑩），`fetch` 就绪判据须放宽为「pin 或其干净后代」，否则 checkout 会丢补丁 commit；③组件补丁集新增子模块集后父仓 HEAD 落在 E5 白区外 ⇒ 必须 `reset --hard base` 再 apply（§7 补注），节点仓库跳跃后同样要先做；④节点 `.work` 全部 reset+重放刷新 mtime ⇒ 触发 LLVM/lld/qemu 全量重建（每节点约 40 min），L2 成本远超改动本身；⑤台账/临时目录类门控按 worktree 快照判，跨 worktree 必然出现「表/册不一致」与「别人的陈旧临时目录」——证据脚本对这两项只记录（INFO），对 L1 其余 49 目标严格判绿；⑥子模块工作树缺失时断言⑩原先会抛 `CalledProcessError`，已改为明确报错（返工 F9）。
**遗留问题**：①**基线差异（已在完成区与本条说明）**：分支 HEAD `5131e048` 落后派单提交 `fda31e1b` 一个台账提交（该提交只把 m12-infra-003 行移入「进行中」）⇒ worktree 内 `check-milestones-fresh` rc=2（A1 表=待开始/册=待验收 + R1），master 上 M11/M12 两册 PASS，合入后消失；两节点 L1 rc=0 的日志取「台账按主控机 master 覆盖」= 合并后状态，未覆盖的原样跑日志亦留存（仅此一项红）。②主工作树 L1 另有一项非本改动红：`check-temp-dirs`（其它任务新落的 5 个陈旧临时目录：GEM5-032t、TESTCASES-057..060t；按规则不删）。③server208 首轮 L1/L2 红系其安装根陈旧（`qemu-system-dadao` 只认 `dadao-m1`），与本改动无关；该节点 `make install-host` + `make build-musl-shared JOBS=8` 后与 207 同绿；两节点已 `make sync-node-repo` 回到 master。④`sync_cache.py` 无需改：只校验节点镜像含 pin commit，子模块补丁的本地 commit 按设计不进镜像（同组件本地 commit）。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查 6 个工具改动 + 新 schema 模块 + manifest + 试点补丁 + 文档，判决：全部 finding 已修，可标待验收。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 不记录 gitlink ⇒ 父仓永远脏（E1 不成立） | ✅已修 | `apply_series` 把子模块 HEAD 写入父 commit 的期望树；`check_patch_tree` 增断言⑩ | 验收 1、注入 9a/9b |
| F2 `patchless` 组件可绕过带 `submodule_patch` | ✅已修 | `manifest_check` 对 patchless 同样拒绝 | 注入 10a/10b |
| F3 `make_patch` 若把 gitlink 当顶层补丁导出会产假补丁 | ✅已修 | 顶层集按声明路径 `skip_paths` 过滤 | 2c/11a/11b |
| F4 `fetch` 会把已打补丁的子模块 checkout 回 pin（丢 commit） | ✅已修 | `submodule_ready` 接受「pin 的干净后代」 | 7a/7b |
| F5 父仓索引无法对子模块路径 `--cached --check` | ✅已修 | 断言①–⑨按集合在各自仓库判（`check_patch_set`），父仓只判⑩ | 4a/6b/8a |
| F6 新补丁目录未进 blob 索引扫描面 | ✅已修 | `check_index_blobs` 扫子模块 `patch_dir` | 6b（239 new-file 全绿） |
| F7 证据脚本注入 D 期望写反 | ✅已修 | 改为「真件 gitlinks=1 / 注入件=0 / 命中≥1」 | 11a |
| F8 证据脚本对外部门控判据过严 | ✅已修 | 12a 归因白名单 + 12b/12c 降为 INFO | 12a、末轮 28/28 |

### 第 1 轮 reviewer 验收

**重跑记录（reviewer 亲跑，逐条真实输出 / 退出码）**
1. `manifest_check.py` → `manifest validation: PASS` rc=0；`check_patch_tree.py` → `check-patch-tree: 9 patch set(s), 324 patches OK` rc=0；`--source-state` → 12 行含 `chipyard:generators/testchipip: OK HEAD=925f454cc82c count=1 clean=True` rc=0；`check_index_blobs.py` → `239 new-file patch(es) OK` rc=0。
2. `make apply-series` → 含 `apply-series: chipyard/generators/testchipip already applied (base+1, matches patches); skipped` 共 12 条 rc=0；`make_patch.py chipyard --dry-run` → 顶层 16 条 + 子模块 2 条、**无** `generators/testchipip.patch`，rc=0。
3. 一键证据脚本（运行期证据目录 `run.sh`）→ `合计: PASS=28 FAIL=0` rc=0；其中 `12a` 实测 `rc=2 失败目标=[check-run-artifacts]`（外部门控、本任务归因=0，脚本白名单放行）。
4. **隔离全新重放**（审查用临时树，独立于共享源树）：检出 pin `0acc1e1` + 子模块 pin `26f821b` 且均干净 ⇒ `apply_series` 首跑 `chipyard/generators/testchipip 2 applied … committed` 与 `chipyard 16 applied … committed` rc=0；子模块 `count=1`、父仓 `count=1`、`git status` 干净、`gitlink == 子模块 HEAD`；二跑两条均 `already applied`；`check_patch_tree` rc=0；`make_patch` 真跑 `0 written, 16/2 unchanged`，产物与共享树 `diff -r` 完全一致。
5. **独立反例注入（engineer 未用；均 cp+md5 还原）**：① 删子模块 `series` 的 `SimDRAM.v.patch` 行 ⇒ rc=1，报 `patch not listed in series` + `assertion ⑨`，还原后 rc=0；② 子模块 `commit --amend`（仍 base+1、内容不变）⇒ rc=1，子模块⑦⑧⑨**全过**、仅 `assertion ⑩`（+父仓⑦）报错；再注入空 commit ⇒ ⑩ 打印 `HEAD records 8283e3b86c7e … but the submodule HEAD is d98ec37691a8`；还原后 rc=0。
6. **两节点**（`gxt@server207` / `gxt@server208`；reviewer 注入本任务 18 文件后实测，随后 cp+md5 还原、`git status` 为空）：`manifest-check`/`apply-series`/`check-source-state`/`check-patch-tree` 均 rc=0（`9 集 324 份`、子模块 `OK … clean=True`）；L2 `make check-modules` 两节点均 `module checks (L2): PASS` rc=0；**L1（51 目标）208 rc=0、207 rc=2**：`check-musl-freshness: FAIL (2 check(s))`（`toolchain stamp == current clang/ld.lld: different`、`builtins stamp == current compiler-rt archive`）——207 的 clang/ld.lld 今日 14:52 / 15:09 重装而 musl stamp 仍 03:29；该门控文件 md5 == 节点 HEAD、18 文件改动集内 0 个 musl 相关文件 ⇒ 与本交付无因果（节点环境陈旧）。
7. 快照对账：审查前后 `git status --porcelain -uall` 均为同一 18 行、目标文件 md5 全等；共享源树终态 `chipyard` / `testchipip` 均 `count=1 clean=True`；两节点 `git status` 空、md5 全 OK。

**约束核验**
- schema 唯一读取点 ✅：`submodule_patch` 三键只由 `submodule_patches.patch_sets` 解析，`apply_series`/`check_patch_tree`/`make_patch`/`manifest_check`/`check_index_blobs` 全部 import 它；manifest 不重复写 base，`base_commit()` 取 `submodule_lock` 同 `path` 的 pin；patchless 组件带 `submodule_patch` ⇒ manifest-check rc=1（证据 10a）。
- 断言 ①–⑨ 对顶层集与每个子模块集各跑一次（子模块集在子模块仓库内判，断言④ 才有意义），⑩ 由 `check_submodule_pin` 比对 `HEAD:<path>` 与子模块 HEAD；可达 FAIL 已由上述注入证实。
- `make_patch` 跳过 gitlink ✅：父仓 `git diff --name-only <base>` 实测 17 条（含 `generators/testchipip`），导出面 16 条；顶层 322 份 = 324 − 2 未受影响。
- 完成区 19 行 ≤30、无运行期/绝对路径；18 文件与「修改文件」逐项一致（`git status` 18 行 ↔ 完成区 18 项）。

**判决：Needs Revision**
- 失败项 = 验收标准 4「L1 两节点 rc=0」：207 实测 rc=2（见上 6），与完成区「两节点 L1/L2 rc=0」不符（声称与实测不符即打回）。
- 具体修改建议：① 在 server207 跑门控自带 remedy `make build-musl-shared JOBS=8` 后重跑 51 目标 L1，预期 rc=0——**不得**把 `check-musl-freshness` 加入白名单 / skip 放行；② 完成区「两节点 L1/L2 rc=0」按实测改写，并把 207 环境陈旧登记为遗留；③ 写明基线差异：分支 HEAD `5131e048` 落后派单提交 `fda31e1b` 一个台账提交（worktree 内 `check-milestones-fresh` 因此 rc=2，master 上 M11/M12 两册均 PASS，合并后消失）。
- 非阻断 finding：`check_submodule_pin` 在子模块工作树缺失时抛 `CalledProcessError` traceback（仍 rc=1 fail-closed，建议改为明确报错）；完成区「check-temp-dirs 5 个陈旧目录」实测现为 0。
- 其余验收项（1/2/3/5/6 + 两节点 L2 + 证据脚本 28/28）在我的重跑下全部通过。

**三个单独问题**：① **子模块补丁可重放且父仓干净**——是：隔离全新检出上一次应用即得子模块与父仓各自 `clean + base+1`、gitlink 一致，二跑幂等 skip，共享树与两节点同态。② **断言⑩真能拦 gitlink 漂移**——是：amend 注入下子模块⑦⑧⑨全过而⑩单独报红（`8283e3b86c7e` vs `a7a5d4fdfdca`），还原回绿。③ **试点不影响 stock 行为**——是：`loadmem_big_endian` 默认 `false`，`get_target_endianness()` 默认仍返 `endianness_little`（仅显式 `+loadmem_be` 才返 big，仓内目前无该 plusarg 的产生方）；`MEM_BASE` 仅参数默认值 `0 → 64'h0`，值仍为 0，唯一使用点是传 `memory_init(…, long long mem_base, …)`，故只改位宽不改值。

### 第 2 轮 engineer 返工（Needs Revision → 待验收）

阻断项：验收 4「两节点 L1 rc=0」原为不实——207 实测 rc=2，唯一红 `check-musl-freshness`（clang/ld.lld 当日 14:52/15:09 重装、musl stamp 仍 03:29），主会话已在 207 跑 `make build-musl-shared JOBS=8`（EXIT=0）修好前置。返工处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F9 子模块工作树缺失时断言⑩抛 `CalledProcessError` traceback | ✅已修 | `check_submodule_pin` 先判 `(sub/.git)`，缺失即明确报错（仍 fail-closed） | 合成 gitlink 仓库直调：输出 `assertion ⑩: submodule worktree … is absent`、rc=1、无 traceback |
| F10 完成区「两节点 L1/L2 rc=0」与实测不符 | ✅已修 | 按实测改写，并写明 207 首轮红因与主会话修复 | 完成区验收 4 + 遗留① |
| F11 「check-temp-dirs 5 个陈旧目录」已过期 | ✅已修 | 改为实测（GEM5-032t、TESTCASES-057..060t，其它任务） | 证据脚本 INFO 行 |
| F12 两节点运行无留存日志 | ✅已修 | 207/208 复跑日志落运行期日志目录并取回主控机 | `m12-infra-003-s207-ledger-L1.log`、`-s207-L2.log`、`-s208-ledger-L1.log`、`-s208-ledger-L2.log` |
| F13 基线差异未写明 | ✅已修 | 完成区遗留①记录 `5131e048` vs `fda31e1b` | 207 原样跑日志仅 A1/R1 |

复跑（真实 rc，均未把 `check-musl-freshness` 放进 skip/白名单）：server207 `L1=0`（`repository checks (L1): PASS`、`check-musl-freshness: PASS`）、`L2=0`；server208 `L1=0`、`L2=0`；207 未覆盖台账原样跑 `L1=2`（FAIL 目标仅 `check-milestones-fresh`，A1+R1 指向本任务行）；本机一键证据 28/28 rc=0。

### 第 2 轮 reviewer 验收

**重跑记录（reviewer 亲跑，逐条真实输出 / 退出码）**
1. 主工作树：一键证据 `run.sh` → `合计: PASS=28 FAIL=0` rc=0；`make apply-series` rc=0；`make check-source-state`（含 `chipyard:generators/testchipip: OK HEAD=925f454cc82c count=1 clean=True`）rc=0；`make check-patch-tree` → `9 patch set(s), 324 patches OK` rc=0；`make fetch` rc=0 且 `already initialized (locally patched HEAD 925f454cc82c (base 26f821be9425))`。
2. **两节点 L1 自跑（决定性）**：节点复位任务基线 `5131e048` → 注入本交付 18 文件 → 仅把承载本任务行的 M12 台账按 `c157dda1` 覆盖（模拟合入后；两册都覆盖会因基线任务归档状态不同产生 113 条假阳性）→ `make check`（`_locked-check` 51 目标）：**207 与 208 均 `L1_rc=0`**，日志含 `check-musl-freshness: PASS (installed libc.so built from the current musl sources + toolchain)`、`check-patch-tree: 9 patch set(s), 324 patches OK`、`check-milestones-fresh` 两册各跑 1 次均 `结果: PASS`、`check-temp-dirs` 已执行、末行 `repository checks (L1): PASS`，`FAIL=0 / Error=0 / VIOLATION=0`。
3. **无白名单**：`git diff --name-only` 仅本交付 18 文件；`Makefile` 改动仅 2 条 help echo（`_locked-check` 原样、仍含 `check-musl-freshness`）；改动集内 0 个 musl 相关文件；该门控在两节点日志中有真实 PASS 输出行（非跳过、非排除）。
4. **F9 自测**（隔离树：全新检出并应用后把子模块工作树挪走）：rc=1、输出 `check-patch-tree: chipyard:generators/testchipip: assertion ⑩: submodule worktree generators/testchipip is absent (cannot compare with the recorded gitlink; run make fetch)`、`Traceback` 计数 0；还原后 rc=0。
5. **两节点终态**：`HEAD=c157dda188`、`git status --porcelain -uall` 0 行、注入残留 0（reviewer 的备份/注入包/日志已删）。
6. **产物一致性**：审查前后 `git status` 同为 18 行；`submodule_patches.py`/manifest/`series`/两份试点补丁 md5 与第 1 轮全等；工具改动仅 `check_patch_tree.py`（F9），其余 6 个工具与 `Makefile` md5 与第 1 轮相同；共享源树 `chipyard`/`testchipip` 均 `count=1 clean=True`。
7. 完成区 19 行 ≤30、无运行期/绝对路径；18 文件与「修改文件」逐项一致；`check-temp-dirs` 实测 5 项与遗留②一致。

**判决：Accepted**
- 验收 4「两节点 L1 rc=0」已由我自跑复现（musl 门控真实 PASS、未加 skip/白名单）；验收 1/2/3/5/6 全部通过。L2 本轮采信 engineer 日志（两节点 `module checks (L2): PASS`）：第 1 轮我已两节点自跑 L2 PASS，且本轮返工只改 L1 门控 `check_patch_tree.py` 与文档，`_locked-check-modules` 成员不涉及改动文件。
- **非本任务的阻断提示（供 architect 定夺）**：master 当前自身 `check-knowledge-refs` FAIL —— `m13-testcases-001` 任务书内有一条具体运行期证据路径引用（ISS-352：`.work/**` 被 gitignore、不可复现），我在主工作树实测 rc=1；我按 master 基线跑两节点 L1 也红在同一处。合入后 master L1 将因此红，与本任务 18 文件无关（改动集内无具体运行期路径引用），建议另立任务修。
- 文档级小错（不阻断）：返工段「207 原样跑 … A1+R1」，其日志实为 **A1 一条**（节点无该任务 worktree，R1 不触发），A1+R1 是主工作树实测；遗留② 目录名实测为 `GEM5-032t-work`。

#### 收尾（architect，2026-11-09 19:02）

- 第 1 轮 Needs Revision（207 的 L1 与「两节点 rc=0」不符）→ 返工 → 第 2 轮 **Accepted**。
- reviewer 自跑复现：207/208 `make check`（51 目标）**rc=0**，`check-musl-freshness: PASS`（非白名单）、`check-patch-tree: 9 集 324 份`、`FAIL=0/Error=0/VIOLATION=0`。
- **F9 已修**：子模块工作树缺失 ⇒ `assertion ⑩: … is absent` + rc=1，无 traceback。
- `sync-node-repo` 两节点 = master、干净。
- 试点补丁：`SimDRAM.cc` 的 `get_target_endianness()` 按 `+loadmem_be` 返回 big（默认 little，stock 行为不变）；`SimDRAM.v` 的 `MEM_BASE` 默认改 `64'h0`（只改位宽不改值）。
- 外部阻断已由主会话修：`m13-001` 任务书的具体 `.work` 引用（`06edf69a`）。
