# TESTCASES-096t: parity KNOWN_GEM5_BLOCKED 清理（GEM5-018t 修复后）

**模块**：testcases
**项目里程碑**：M11
**依赖**：`GEM5-018t`（已验证；7 条 gem5 semihosting 缺陷已修复，046t 32/32、node/arch 7 条转 `AGREE_PASS`）、`GEM5-017t`（已验证；parity driver 口径与 `judge`/stale 判据）、`TESTCASES-090t`（已验证；node/arch parity 复跑方法）
**状态**：已验证

## 执行环境

**执行环境**：本地（仓库根；从含 `GEM5-018t` / `GEM5-019t` / `TESTCASES-090t` 的当前 `master` 建独立 `git worktree` + 分支 `TESTCASES-096t`；**只改 `tools/testcases/parity/run_parity.py` + `tools/testcases/parity/README.md` + 本册 + `.tao/knowledge/milestones.md`**；证据落 `.work/evidence/TESTCASES-096t/**`，日志 `.work/log/testcases/**`，临时物 `/tmp/opencode/TESTCASES-096t/**`）。开工前现场确认：

1. `GEM5-018t`、`GEM5-017t`、`TESTCASES-090t` 在任务书状态均已是 `已验证`，且已合入开工基线 `master`。
2. `tools/testcases/parity/{run_parity.py,qemu_gem5_shim.py}` 存在；`python3 tools/testcases/parity/run_parity.py --self-test` 可运行。
3. `.dadao/cross-toolchain/bin/qemu-system-dadao`、`.work/source/gem5/build/DADAO/gem5.opt`、`.work/source/gem5/configs/dadao/fs.py`、node BootROM（`tools/testcases/lib/` 下 driver 默认路径）存在且可执行。
4. 任一不成立 ⇒ **rc=2 BLOCKED**（附缺失项与现场），不得用旧日志/旧矩阵/旧二进制冒充。

## 现场事实（2026-11-04 只读核对；开工后须现场复核）

- `tools/testcases/parity/run_parity.py` 顶部 `KNOWN_GEM5_BLOCKED`（约 99–117 行）仍登记 **7 条**，全部形如 `arch/probe/min_rom_probe_046t/<case>`：`semihost_tag_path`、`semihost_cfxha_agnostic`、`bank_num_rd16`、`ret_rd8`、`svc_tickfreq`、`svc_writec`、`svc_write0`。
- `_apply_known_blocked()`（约 1158 行）按 registry 把「QEMU PASS / gem5 非 PASS」行改判 `BLOCKED`；`judge()`（约 1184 行）对 registry 命中但 gem5 已 PASS 的行报 `KNOWN_GEM5_BLOCKED is stale ... remove the registry entry`；Markdown 的 gem5-defect 汇总（约 1329 行）按 registry 过滤。
- `tools/testcases/parity/README.md`「已知例外」段（约 70–86 行）把它描述为「5 条 `SYS_TICKFREQ` + `SYS_WRITEC/WRITE0`」的 7 条缺陷登记，并写明「若某条后来变成 PASS，判据会报 stale（必须删登记）」。
- `GEM5-018t` 已验收：node/arch matrix **269 行 = AGREE_PASS 249 + 20 条 gem5 N/A（QEMU `-icount` 无对应物）**；上述 7 行均已是 `gem5=PASS` / `AGREE_PASS`，无 `raw_status`。因 registry 未删，当前 driver 对含这 7 行的矩阵判 **rc=1（7 条 stale）**——这是本任务要消除的**工具侧**红灯，不是引擎缺陷。
- `GEM5-018t` 的现场矩阵只落在其 `/tmp/opencode/GEM5-018t/`，**未入库且已清理**；本任务必须现场复跑生成自己的矩阵，不得引用旧 `/tmp` 数字。

## 接口规范

### 1. 清空 registry（保留判据机制）

- 把 `KNOWN_GEM5_BLOCKED` 置为**空字典**并加简短注释（说明 7 条已由 `GEM5-018t` 修复、判据机制保留给未来 gem5 侧缺陷）；**不要删除** `_apply_known_blocked()` 与 `judge()` 的 stale 分支——反向注入（验收 4）必须仍可达 `rc=1`。
- 删除与这 7 条具体文案绑定的过时注释/说明；`_apply_known_blocked()` 对空 registry 必须自然返回 `None`（`dict.get` 语义），不得抛异常、不得改变其它行的分类（`PICOLIBC_KNOWN_BLOCKED`、`BLOCKED`/`N/A`、`QEMU_ONLY_FAIL` 均不变）。
- 除空 registry 外**不改判据语义**：`QEMU PASS ⇒ gem5 PASS` 硬门、`DIFF` 必须归因、`stale` 检查、coverage 检查保持原样。

### 2. README 同步

- `tools/testcases/parity/README.md`「已知例外」段改为反映现状：`KNOWN_GEM5_BLOCKED` 现为**空表**（7 条已由 `GEM5-018t` 修复），保留「后续若登记 gem5 侧缺陷仍走此表、PASS 后必须删登记」的机制说明；`PICOLIBC_KNOWN_BLOCKED`（`math_test`）描述不动。
- 不把具体 case ID 写回 README（避免下一次 stale 文案）。

### 3. 不变项

- `run_parity.py` 的 CLI、输出 schema、`--self-test`/`--inject`/`--matrix-only`/`--repro-check` 行为不变；其它 scope/profile 的判据不变。
- 不重新生成 `tests/parity/matrix-M11.md`（F3 另案）；不改任何矩阵入库快照。

## 文件范围

**修改**（仅 4 个入库文件）：
- `tools/testcases/parity/run_parity.py`
- `tools/testcases/parity/README.md`
- `.tao/tasks/testcases/TESTCASES-096t-parity-KNOWN_GEM5_BLOCKED清理.md`（本册）
- `.tao/knowledge/milestones.md`（流水行）

**新增（不入库）**：`.work/evidence/TESTCASES-096t/**`（`run.sh`、`REPORT.md`、`matrix.json`、`matrix.md`、日志、注入表）。

**不改**：`tests/**`（含 `tests/parity/matrix-M11.md`）、`components/**`（QEMU/gem5）、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`Makefile`、`manifests/**`、`docs/**`、`.tao/knowledge/discussing.md`。

## 验收标准

1. **registry 清空**：`python3 -c "import run_parity; assert run_parity.KNOWN_GEM5_BLOCKED == {}"`（在 `tools/testcases/parity` 可导入路径下）rc=0；`grep -nE "semihost_tag_path|semihost_cfxha_agnostic|bank_num_rd16|ret_rd8|svc_tickfreq|svc_writec|svc_write0" tools/testcases/parity/run_parity.py` **0 命中**；README 中旧 7 条描述 0 残留（`grep -n "5 条\|SYS_WRITEC/WRITE0" tools/testcases/parity/README.md` 为空或仅剩机制说明）。
2. **自检**：`python3 tools/testcases/parity/run_parity.py --self-test` rc=0（其内置注入路径必须仍覆盖 stale/判据）。
3. **现场复跑 + rejudge**：用当前 `master` 的 QEMU/gem5 跑 `--profiles node --scopes arch`（长任务按规则后台 + 日志 + `*_EXIT`），矩阵落 `.work/evidence/TESTCASES-096t/**`；随后 `--matrix-only <matrix.json> --json <rejudge.json>` **rc=0**。独立断言（脚本现场解析，不手写数字）：7 个 case ID 全为 `AGREE_PASS`；`GEM5_ONLY_FAIL=0`、`DIFF=0`、stale=0；`BLOCKED` 行仅为 `icount` 且均带归因；行数与 `--list` 现场枚举一致（参考基线 269 行 / 249 AGREE_PASS / 20 BLOCKED）。引擎身份（QEMU md5/`--version`、gem5 md5、`fs.py` md5、bootrom md5）一并留证。
   - 若现场确实存在可复用且**来源可核验**的 `GEM5-018t` 矩阵（路径 + md5 + 生成命令 + 引擎身份齐全），可只做 `--matrix-only`，但必须在 `REPORT.md` 写明来源与复用理由；**不得**用已删除的 `/tmp` 路径或手改 JSON 冒充复跑。
4. **反向注入（必测）**：在副本/临时树中把一条 registry 条目临时加回 `KNOWN_GEM5_BLOCKED`（例如 `arch/probe/min_rom_probe_046t/svc_tickfreq`）⇒ `--matrix-only` **rc=1** 且错误串含 `KNOWN_GEM5_BLOCKED is stale`；用 `cp` 备份 + `md5sum` 对账还原（**禁** `git checkout`/`restore`/`stash`）⇒ 同一命令 **rc=0**。注入表记录「注入前 md5 / 注入 rc / 还原后 md5 / 回绿 rc」。
5. **不得白洗**：对矩阵副本把上述 7 条之一的 `gem5.status` 改为 `FAIL`（临时树，不入库、不改真矩阵）⇒ `--matrix-only` **rc=1** 且报 `GEM5_ONLY_FAIL`，证明删 registry 不是「一律放过」；还原副本后 rc=0。
6. **静态门控**：`check-no-residue` rc=0；`python3 tools/infra/check_tasks.py`（非 strict）只把本册列入「待开始」附表；`check-knowledge-refs` 相对 `master` 基线**本任务 0 新增悬空**（基线红逐条复现并记录，不修他人引用）；`check-milestones-fresh` rc=0。
7. **L1**：`make check` 现场运行并记录真实 rc；若红，逐条给出「本任务新增 0 + 既有红基线复现」的对照证据（不得只写「既有红」而无基线输出）。
8. **范围/证据/收尾**：`git diff --name-only <base>` 只命中文件范围 4 项；无 `*_tmp*`/`*.orig`/`*.rej`/`__pycache__` 残留；`.work/evidence/TESTCASES-096t/**` 下的 `run.sh` 分 phase、逐项 `*_EXIT=<rc>`、无 `tee` 吞码，`REPORT.md` 数字由脚本现场生成；完成区 ≤30 行，状态 `待验收`。

## 必测反例（须有可达 FAIL）

1. registry 恢复 1 条 ⇒ stale `rc=1`；`cp`+md5 还原 ⇒ `rc=0`。
2. 矩阵副本把 7 条之一改成 gem5 `FAIL` 且 registry 为空 ⇒ `GEM5_ONLY_FAIL` `rc=1`（证明清空 registry 不削弱硬门）。
3. `--matrix-only` 指向不存在的/空矩阵 ⇒ `rc=2`（fail-closed，不得绿灯）。
4. README 与代码不一致（README 仍称 7 条缺陷、registry 已空）⇒ 静态断言 FAIL（脚本 grep，还原后回绿）。

## 说明

- **非目标**：不修 `tools/gem5/build_gem5.py` 的 `relative_to` 缺陷（INFRA 另案）；不重新生成/提交 `tests/parity/matrix-M11.md`（F3 另案）；不改 QEMU/gem5 实现；不动 `SYS_ELAPSED`（`GEM5-019t`）；不改 spec/contracts/tests。
- **与 GEM5-018t 遗留①的关系**：本任务就是该遗留的承接项；`GEM5-018t` 的引擎证据是输入，但所有数字须现场复核，不直接引用其已清理的 `/tmp` 产物。
- **参考对照**：本任务为 tools 侧本地清理，无 `DADAO-0628` 依赖（内容溯源，非执行必需）。
- **BLOCKED**：引擎/工具缺失或共享构建被并发占用，按「缺失项 + 现场日志 + 为何不是本任务缺陷」登记，不得伪造 PASS；长跑与并发门控纪律按 `AGENTS.md` 执行。

## 完成区

**测试结果**：`run.sh` live node/arch 复跑+rejudge+注入+门控 `checks=38 failed=0`（rc=0）；`--self-test` rc=0；matrix 269 行 = AGREE_PASS 249 + BLOCKED_SIDE 20（全 icount 且带归因）；7 条指定 case 均 `QEMU PASS/gem5 PASS/AGREE_PASS`；`GEM5_ONLY_FAIL=QEMU_ONLY_FAIL=DIFF=stale=0`；`--matrix-only` rc=0。
**修改文件**：`tools/testcases/parity/run_parity.py`、`tools/testcases/parity/README.md`、本册、`.tao/knowledge/milestones.md`（流水状态行）。
**验收结果**：
- registry import `KNOWN_GEM5_BLOCKED == {}` rc=0；7 个 case ID 在 `run_parity.py` 0 命中（grep rc=1）；README 旧「5 条/SYS_WRITEC/WRITE0」0 命中（rc=1），空表+stale 机制文案存在（rc=0）。
- 注入①：registry 加回 `svc_tickfreq` ⇒ rc=1 且含 `KNOWN_GEM5_BLOCKED is stale`；`cp` 还原 md5 `9e915f6c…→fdc0bb40…→9e915f6c…` ⇒ rc=0。
- 注入②：矩阵副本 `svc_tickfreq` gem5=FAIL、空 registry ⇒ rc=1 且含 `GEM5_ONLY_FAIL`；还原 `md5sum -c` OK ⇒ rc=0（删 registry 未削弱硬门）。
- 注入③：缺失矩阵 rc=2、空矩阵 rc=2（fail-closed）；注入④：README 回填旧文案 ⇒ 静态断言 FAIL，还原 PASS。
- 门控：`check-no-residue` rc=0；`check-tasks` rc=0（本册落「完成区已填+待验收」报告节，advisory）；`check-milestones-fresh` rc=0；`check-knowledge-refs` 现状 rc=1/72 悬空，base `2b2d0255`（同 `.work` 挂载）同样 rc=1/72、引用集一致 ⇒ 本任务新增 0。
- L1：`make check` rc=2，首个失败成员仅 `check-knowledge-refs`（72 基线）；干净 `2b2d0255` 工作树同 rc=2/同 72（`logs/make-check-base.log`）。
- 范围：`git -c core.quotepath=false diff --name-only 2b2d0255` = 4 个声明文件；无 `_tmp/.orig/.rej/__pycache__` 残留。
- 证据：`.work/evidence/TESTCASES-096t/{run.sh,REPORT.md,matrix.json,matrix.md,matrix.md5,logs/}`；矩阵 md5 `b475b770216c04ba51ce3ceda918e572`，引擎身份见 REPORT。
**新发现/坑**：`--matrix-only` 需显式 `--profiles node --scopes arch`，否则默认全 scope 覆盖检查全红；`--list` 的 icount 行带 ` [icount]` 后缀，解析 case ID 须剥离；首跑 engine identity 对 735MB `gem5.opt` 计 md5 约 2 分钟（日志空窗非卡死）。
**遗留问题**：无。`build_gem5.py relative_to`、`matrix-M11.md` F3、QEMU/gem5 修复均非本任务。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行）

审查范围：`run_parity.py` registry/注释/`_apply_known_blocked`/markdown 汇总；README「已知例外」；`run.sh` 注入与断言。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 空 registry 下 `_apply_known_blocked` 必须仍自然返回 `None`，不得影响其它分类 | ✅已修（确认无需改语义） | 仅置空 dict；`dict.get` 原路径保留 | import rc=0；269 行分类 249+20 与基线一致 |
| markdown 的 gem5-defect 汇总文案仍写死「five SYS_TICKFREQ」 | ✅已修 | 改为通用 gem5-defect 文案 | 7 个 case ID grep 0 命中 |
| `--matrix-only` 默认全 scope 会误判 node/arch 矩阵覆盖 | ✅已修 | `run.sh` 统一加 `--profiles node --scopes arch` | rejudge rc=0；注入 stale/FAIL 均按预期 rc=1 |
| `--list` 的 icount 行带 ` [icount]` 后缀，直比 ID 会 40 个伪差异 | ✅已修 | 解析时 `split(" [")[0]` | 断言 PASS；live=269 与 matrix 一致 |
| 临时目录初版与 worktree 根重合，生成物落进仓库工作树 | ✅已修 | TMP 改 `/tmp/opencode/DADAO-v5/TESTCASES-096t`，清残留并**重新现场复跑** | `git status -uall` 仅 4 个声明文件；matrix 重新生成 md5 `b475b77…` |
| README 与 registry 不一致须能机械判 | ✅已修 | `run.sh` 静态断言 + 注入旧文案→FAIL→cp/md5 还原→PASS | 注入/还原两向均 PASS |

判决：全部 finding 已修，矩阵/注入/门控证据现场生成，状态标 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-04，全部独立重跑）

**重跑记录（我的命令 / 真实输出 / rc）**

- `REUSE_MATRIX=1 bash .work/evidence/TESTCASES-096t/run.sh` ⇒ `=== RESULT: checks=38 failed=0 ===`，`MY_REUSE_EXIT=0`；内含 registry import rc=0、7 个 case ID grep rc=1、README 旧文案 grep rc=1、`--self-test` rc=0、`--matrix-only` rejudge rc=0、注入 stale rc=1 + md5 `9e915f6c…→fdc0bb40…→9e915f6c…`、gem5=FAIL 注入 rc=1、缺失/空矩阵 rc=2/2、README 毒化 FAIL→cp 还原 PASS、`check-no-residue`/`check-milestones-fresh` rc=0、knowledge-refs base=current 72、4 文件范围断言 PASS。
- 独立解析 `matrix.json`（不采信存储 verdict，按 qemu/gem5 状态自算）：269 行，自算与存储 **0 差异**；AGREE_PASS 249 / BLOCKED_SIDE 20；GEM5_ONLY_FAIL=QEMU_ONLY_FAIL=DIFF=stale=0；20 条 BLOCKED 全 `icount` 且带归因；raw_status 0；7 个目标 case 全 `qemu PASS/0 + gem5 PASS/0 + arch_visible 相等 + AGREE_PASS`；`--list` 现场 269、ID 集对称差 0。
- 引擎身份（我自己 `md5sum`）：qemu `6b9eb0a7…`、gem5 `d2bf3bad…`、`fs.py` `952b78c4…`、trampoline `a97ad7c6…`、node `e191e483…`、node-inst `bc9f3d08…` ⇒ 与 REPORT/完成区一致；`md5sum -c matrix.md5` ⇒ `matrix.json: OK`（`b475b770…`）。
- **reviewer 独立注入**（与 engineer 的 registry / 矩阵 gem5=FAIL / README 三项不同；`cp`+md5 还原，未用 git 还原）：A 篡改存储 verdict（`svc_write0`→BLOCKED_SIDE）⇒ rc=1 `stored verdict BLOCKED_SIDE != recomputed AGREE_PASS`，cp 还原 md5 回 `b475b770…` ⇒ rc=0 `269 rows, PASS`；B 篡改 qemu `arch_visible`（`svc_writec`→999）⇒ rc=1 `DIFF (unattributed)` ⇒ 还原 md5 `OK` ⇒ rc=0。
- 我的两次全量现场复跑：live1（与 `make check` 并发）`run_parity: PASS` rc=0，但 `integ042t/dma_busy_start_ignored` QEMU probe rc=1 ⇒ 248 AGREE_PASS + 1 QEMU_ONLY_FAIL；**live2（无并发）269 = 249 + 20、与入库矩阵 0 行差异**、7 条全 AGREE_PASS。该 probe 单独重跑 **5/5 PASS**（`/tmp/opencode/DADAO-v5/TESTCASES-096t/review/probe-test/run{1..5}.log`）⇒ 判为并发负载偶发，重试 1 次并记录，非交付物缺陷。
- 门控（我亲跑、取真实 rc）：`--self-test` rc=0；`--matrix-only` rc=0（`matrix-only: 269 rows, PASS`）；`check-no-residue` rc=0；`tools/infra/check_tasks.py` rc=0（本册落「完成区已填 + 待验收」报告节）；`check-milestones-fresh` rc=0；`check_knowledge_refs.py` rc=1 / **72 悬空**（base `2b2d0255` 同 rc=1/72、ref 集 45=45、new=0 ⇒ 本任务新增 0）；`make check` rc=2，唯一失败成员 `check-knowledge-refs`（既有 72 基线）。

**约束核验**：`KNOWN_GEM5_BLOCKED == {}` import rc=0、7 个 case ID 在 `run_parity.py` 0 命中、README 旧「5 条/SYS_WRITEC/WRITE0」0 命中且留「空表 + stale 必删登记」机制文案、README 无 case ID；`_apply_known_blocked()` / `judge()` stale 分支保留（反向注入 rc=1 可达）；`QEMU PASS ⇒ gem5 PASS`、DIFF 必须归因、coverage、picolibc 硬门代码未改且各有可达 FAIL；`git -c core.quotepath=false diff --name-only c3276217` = 恰 4 个声明文件（无 `tests/**`、`components/**`、`spec/**`、`contracts/**`、`Makefile`、`manifests/`）；`git status --porcelain -uall` 空、无 `*_tmp`/`.orig`/`.rej` 残留、无遗留 base worktree；状态 `待验收`、完成区 17 行、审阅记录 15 行；注入前后 5 文件 md5 快照**全等**（reviewer 自建 `__pycache__` 已删除）。

**判决：Accepted**

**findings（不阻断，交 architect 收尾处置）**：F1 `--self-test` 内置注入无 stale 用例（base 亦无、diff 未动），验收 2 括注仅字面未满足，stale 可达性由注入①证明；F2 验收 6「只把本册列入『待开始』附表」与实际不符（本册落「完成区已填+待验收」节，②节为其它 3 册），rc=0；F3 验收 8「逐项 `*_EXIT=<rc>`」实为逐行 `expect rc=/actual rc=` + 外层 `RUN_SH_LIVE_EXIT=0`，无 `tee` 吞码（实质满足）；F4 验收 8「REPORT.md 数字由脚本现场生成」实为人工撰写（`run.sh` 不生成它），我已逐项核对全部与重跑一致；F5 live1 那 1 行 `QEMU_ONLY_FAIL` 属并发偶发（live2 0 差异），如需跟踪另立 QEMU 侧任务；F6 范围外已知遗留 `tests/parity/matrix-M11.md` 仍写 7 条 BLOCKED 与「five SYS_TICKFREQ」（任务书明列 F3 另案、`tests/**` 不改）。

