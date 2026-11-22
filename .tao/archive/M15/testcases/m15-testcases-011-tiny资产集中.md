# m15-testcases-011: tiny 资产集中到 `tests/ee-tiny/`（脚本 + bootrom + lds）

**模块**：testcases
**项目里程碑**：M15
**依赖**：无（纯目录/路径迁移；测试集内容不变）
**可并行分片**：否（跨目录引用唯一）
**预估**：2–3 h
**档位**：中改（迁移 + 引用更新 + 门控回绿）
**状态**：已验证

## 背景（用户 2026-11-17 指示）

把 kaiwu-tiny 专属的**脚本、bootrom、lds** 集中到 `tests/ee-tiny/`；**不建子目录**（平铺，文件名说明用途）；**测试集不移动**（`tests/inst`、`tests/tset`、`tests/unit` 原地不动）。

## 目标（迁移清单，共 17 个文件）

**脚本（4）**

1. `tools/testcases/inst/run_asm_suite.py`
2. `tools/testcases/picolibc_tests.py`
3. `tools/testcases/tset/embench/run_embench_e2e.py`
4. `tools/linux/run_semihosting_smoke.py`

**BootROM（10）**

5. `tests/shared/bootrom/tiny/power.S`
6. `tests/shared/bootrom/tiny/hmon.S`
7. `tests/shared/bootrom/tiny/tiny_common.inc`
8. `tests/shared/bootrom/tiny/power.lds`
9. `tests/shared/bootrom/tiny/hmon.lds`
10. `tests/shared/bootrom/bootrom.S`
11. `tests/shared/bootrom/bootrom_app.S`
12. `tests/shared/bootrom/semihost_smoke.S`
13. `tests/shared/bootrom/tiny_smoke.lds`
14. `tests/shared/bootrom/semihost_smoke.lds`

**LDS（3）**

15. `tests/shared/linker/kaiwu-tiny.lds`
16. `tests/shared/linker/kaiwu-tiny-app.lds`
17. `tests/shared/linker/picolibc-tiny.ld`

**不移动**：`tests/inst/linker/inst-tiny.lds`（属 inst 测试集布局，测试集不动）；`tests/shared/bootrom/step5/**`（Vast）；`tests/shared/linker/dadao-*.lds`、`kaiwu-vast.lds`（多机型/其它）；`tests/unit/picolibc/**`、`tests/tset/**`、`tests/inst/**`。

**迁移后目录**：`tests/ee-tiny/` 平铺上述 13 个 bootrom/lds 文件（脚本 4 个也放 `tests/ee-tiny/`，按用户指示）。

## 引用更新（必须全量 grep，不得漏）

- `Makefile`：`build-bootrom` 目标与 `BOOTROM_*` 变量、`build-picolibc`、相关门控的路径。
- `tools/`：`check_tests_index.py`、`check_inst_*`/`check_asm_*`、`picolibc_tests.py`、`run_asm_suite.py`、`run_embench_e2e.py`、`run_semihosting_smoke.py` 自身及调用方。
- `tests/README.md`、`tests/INVENTORY.md`、`tests/inst/README.md` 等文档中的路径。
- 门控扫描面（`check-dirs`、`check-no-residue`、`check-inst-macro-scope`、`check-run-artifacts` 等）若按目录枚举，需同步。

## 验收（逐条贴真实 rc）

1. `git mv` 后旧路径不存在、新路径存在；17 个文件内容逐字节不变（md5 对账）。
2. `make build-bootrom` rc=0；tiny bootrom md5 与迁移前一致。
3. `check-inst-asm` **272/272**（测试集未动）；`check-tests-index`、`check-case-ledger`、`check-inst-macro-scope`、`check-dirs`、`check-no-residue` 全 rc=0。
4. `python3 tests/ee-tiny/run_asm_suite.py --help`、`python3 tests/ee-tiny/picolibc_tests.py --list`（或等价轻量路径）可运行；`run_embench_e2e.py --help`、`run_semihosting_smoke.py --help` 可运行。
5. 1 路注入：把引用改回旧路径 ⇒ 对应门控/构建红；`cp`+md5 还原 ⇒ 回绿。
6. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：上述 17 文件、调用方（`Makefile`/`tools/`/文档/门控扫描面）、本任务书。**不动**测试集内容、`spec/`、`.tao/contracts/`、组件补丁。
3. **不改版本号**；不提交 git；`cp`+md5 还原。
4. 迁移用 `git mv`（保留历史）。

## 待裁定

（无）

## 审阅记录

### 第 1 轮 engineer 自审

1. **`tests/ee-tiny/` 不是合法模块名**（连字符）：`check_k1.py` 原 `from tools.linux import run_semihosting_smoke` 迁后无法 import ⇒ 改 `importlib.util.spec_from_file_location` 按文件加载；`--help` rc=0。**✅已修**
2. **`INCLUDE dadao-common.lds` 的解析面**：实测 ld.lld 对 `INCLUDE` 只搜 cwd + `-L`（脚本目录不搜）⇒ `-L dirname(lds)` 迁后会指到 `tests/ee-tiny/`。5 处调用点（`run_elf_e2e` / `run_embench_e2e` / `run_suite` / `build_musl` / `test_picolibc_smoke` / `min_rom_probe_integ007t`）改 `-L tests/shared/linker`；`lit.cfg.py` 的 `%ld` 原有 `-L` 保留。**✅已修**（test-elf 5/5、lit e2e 21/21、integ007t 64 checks）
3. **`.include` 同为 cwd 相对**（llvm-mc 实测：脚本目录的 `inc.inc` 未被选中）⇒ `.S` 内 include 必须指向新路径。改 `tests/ee-tiny/power.S` 1 行 + `tools/chipyard/excp/app.S` 1 行；`tiny bootrom` md5 前后一致（`514300876ea66ec108396334f3ef2b0f`）。**✅已修**
4. **脚本仓库根深度**：`run_asm_suite`/`picolibc_tests`/`run_embench_e2e` 由 3–4 层改 `parents[2]`；`picolibc_tests` 的 `CRT0_STUB` 与 `lib/` 改指向 `tools/testcases/`（未随迁移）。**✅已修**（4 个 `--help` rc=0）
5. **任务号/目录名两次变更**：`git mv` 任务书 → `m15-testcases-011`，`git mv tests/tiny tests/ee-tiny`，全仓 `tests/tiny` / `m14-testcases-007` 残留 = 0（`.tao/knowledge/**` 由主会话维护，不在此列）。**✅已修**
6. **证据脚本首次 `A3` 计 16**：`DATA_FILES` 漏 `power.S`（现场统计逮到）⇒ 补入后 22/22 全绿。**✅已修**
7. `components/*`（chipyard/musl README、changelog）与 `docs/TestReports/M17-*` 仍写旧路径：组件文档/冻结报告不在本任务「引用更新」面内（重组件的改动须走组件补丁流程）。**⏸延后**
8. `check_tests_index` 对「lds 缺失」的 INCLUDE 复核会抛 `FileNotFoundError` 而非干净 FAIL（既有健壮性问题，非本次引入）。**❌不修**（超范围，建议另立 issue）

### 第 1 轮 reviewer 验收

**自证/快照**：`git rev-parse --show-toplevel` = `/tmp/opencode/m14-testcases-007/wt`；分支 `m15-testcases-011`；**基线与终态 `git status --porcelain -uall` 均空**，逐行对账一致。`f32f4830..HEAD` = 2 提交 / 66 文件，全部改动行（343 行）逐行过目：**无语义改动**，仅路径与注释。

**迁移完整性**：17 文件全以 R100/R098/R097 平铺 `tests/ee-tiny/`（`find -maxdepth 1 -type f` = 17），17 项旧路径 `[ -e ]` **全否**；`__pycache__` 属 `.gitignore:11` 运行期产物。与 `f32f4830` 版逐 md5：**12/13 数据文件字节相同**；`power.S` 仅 1 行 `.include`（`diff` = `26c26` 单行）；4 脚本仅路径常量/注释/`-L`。

**引用清零（逐条判定）**：活跃代码仅 `Makefile:808` 引 `tests/shared/bootrom/tiny_smoke.S`——**该文件不在 17 清单、仍在旧处，引用有效**。其余为除外面：`.tao/archive/**`、7 份 `已验证` 任务书、`components/{chipyard,musl}/**.md`（⏸组件文档）、`docs/TestReports/M17-*`（⏸冻结）、`.tao/knowledge/{milestones-m14,issues.yaml}`（台账归主会话）。

**越界**：`spec/`、`.tao/contracts/`、`contracts/`、`components/`、`manifests/` **0 命中**；`tests/inst/**` 仅 README·MIGRATION·schema 三份 md（任务书明列）；`tests/arch/hmon/*.S`、`dadao-dyn.lds`、`causeid.S` 改动**全为 `@@` 注释行**；`chipyard/excp/app.S` 仅 1 行 `.include`。测试集内容零改动。

**独立重跑（我方命令 / 输出 / rc）**：`make build-bootrom` → **rc=0**，`bootrom_tiny.bin` md5 = `514300876ea66ec108396334f3ef2b0f` ✅；`make check-inst-asm` → **rc=0**，`272/272 镜像通过`（`find tests/inst -name '*.S'` = 272 现场派生）；`check-tests-index`/`check-case-ledger`/`check-inst-macro-scope`/`check-dirs`/`check-no-residue`/`check-interface` → 全 **rc=0**；4 驱动 `--help` → 全 **rc=0**（`picolibc_tests --list` 非法参数 rc=2，任务书允许「等价轻量路径」）；终态复跑 6 门控 + 证据脚本 → 全 **rc=0**。

**反例注入 4 路（`cp`+md5 还原；全程未用 `git checkout/restore/stash/show`）**：
1. `tests/ee-tiny/power.S` 的 `.include` 改回旧路径 → `make build-bootrom` **rc=2**（`Could not find include file 'tests/shared/bootrom/tiny/tiny_common.inc'`）→ 还原 md5 `2fded63a…` 相等 → **rc=0**、bin md5 复原。
2. **（任务书未列）** `tools/linux/check_k1.py` importlib 改回旧 `from tools.linux import …` → `--help` **rc=1**（`ImportError: cannot import name 'run_semihosting_smoke'`）→ 还原 md5 `3c6eab1f…` 相等 → **rc=0**。
3. **（任务书未列）** `run_elf_e2e.py` 的 `-L` 改回 `dirname(lds)` → **rc=1 / 0-5**（`kaiwu-tiny-app.lds:45: cannot find linker script dadao-common.lds`）→ 还原 md5 `1da92ded…` 相等 → **rc=0 / 5-5**。
4. **（任务书未列）** `check_tests_index.py` import 路径改回旧目录 → **重跑同一证据脚本** **rc=1**（`PASS=20 FAIL=2`，C5 `check-tests-index rc=2`）→ 还原 md5 `ebb76f7a…` 相等 → **rc=0**（`PASS=22 FAIL=0`）。

**证据脚本审核**：`run.sh` 逐条断言均有**可达 FAIL 路径**（A1/A2/A3/B1/B2/C1–C5/D1 + inject 4 断言，`chk` 双参现场对账，无恒真、无两支同果），计数**现场派生**（`find|wc -l`、`total/identical` 现算）非写死；`md5-before.txt` 与我方独立算的 BASE md5 **逐条相同**；还原用 `cp -p`+md5。我方重跑 22/22 rc=0、注入后 20/22 rc=1。

**两坑核验（最小性/新风险）**：① `INCLUDE`/`.include` 按 cwd(+`-L`) 解析 ⇒ 修复 = 6 处 `-L tests/shared/linker` + 2 处 `.include` 改路径，**最小且必要**（注入 1/3 反证）；**新风险登记**：`-L` 由 `dirname(lds)` 改为固定目录，若将来 `--lds` 指向**其它含自引用 INCLUDE 的目录**会失效——现行 2 份 tiny lds 唯一 `INCLUDE` 目标 `dadao-common.lds` 正在 `tests/shared/linker`，**当前无风险**。② 连字符目录不能作包 ⇒ `check_k1.py` 走 `importlib` 按文件加载（最小；模块有 `__main__` 守卫，`--help` rc=0 实证无副作用），其余 8 处用 `sys.path.insert(dir)`+模块名 import（模块名无连字符，合法）。

**约束核验**：① 独立 worktree、未改主工作树 ✅；② 只动 17 文件 + 调用方 + 本任务书，禁改区 0 命中 ✅；③ 未改任何版本号 ✅、未提交 git ✅、还原全程 `cp`+md5 ✅；④ 迁移用 `git mv`（R 检出）✅；⑤ 全程无 `cmd | tee` 吞码、命令均带 `timeout` 且无 124 ✅。

**判决：Accepted**（中改档：全量 diff + 4 路注入 + 全部门控 + 越界核对，均以本方重跑为准）。

**未闭合项（不阻断）**：① 组件文档/冻结报告仍写旧路径（⏸已披露，须走组件补丁流程）；② `.tao/knowledge/{milestones-m14.md,issues.yaml}` 台账旧路径/旧任务号（归主会话）；③ `picolibc_tests --stage fast`、`run_embench_e2e` 真实跑批未跑（本 worktree 无 `.work/source` 语料）；④ `check_tests_index` 缺 lds 抛 traceback 而非干净 FAIL（既有问题，实测 rc=2、fail-closed 成立）；⑤ **设计层供 architect 定夺**：`tiny_smoke.S`/`tiny_crt.S`/`bootrom.lds` 不在 17 清单、留 `tests/shared/bootrom/`，与已迁的 `tiny_smoke.lds` **分居两目录**（`Makefile:808-809` 一行引旧一行引新），实现忠实于任务书清单；⑥ **文档笔误**：自审第 2 条写「5 处调用点」实为 **6** 处（我已逐处核对均指向 `tests/shared/linker`）。

## 完成区

**测试结果**：22/22 检查全绿（一键脚本：迁移结构 3、内容对账 2、构建/门控 8、4 驱动 `--help`、注入自检 3）；另跑 `validate-vectors`（156/156，272 载体）、`check-tests-index --self-test`（28 例）、`check-inst-macro-scope --selfcheck`、`check-case-ledger --self-test`、`check-writer-guards`（27/27）、`check-lit`(e2e 21/21)、`test-elf`（5/5）、`linux-semihosting-smoke`、`min_rom_probe_integ007t`（64 checks）均 rc=0。失败项 0。

**修改文件**：17 文件 `git mv` → `tests/ee-tiny/`（平铺）；`Makefile`；`tools/` 25 个调用方/门控（`testcases/`、`infra/`、`gem5/`、`qemu/`、`linux/`、`chipyard/excp/`）；`tests/` 14 个文档/配置（README·INVENTORY·shared·arch·inst·tset·unit·`lit.cfg.py`）；`docs/Process-09`；本任务书（改名 + 状态）。逐文件清单见 `git diff HEAD --stat`（65 项）。

**验收结果**：① 迁移后旧路径 0 存在、`tests/ee-tiny/` 17 文件齐（平铺）；**12/13 数据文件 md5 逐字节一致**（`power.S` 仅 1 行 `.include` 路径差，见自审 3；4 个脚本按需改路径常量）；② `make build-bootrom` rc=0，`bootrom_tiny.bin` md5 `514300876ea66ec108396334f3ef2b0f` 与迁移前**一致**（`bootrom.bin`/`bootrom_app.bin`/`semihost_smoke.elf`/`tiny_smoke.elf` 亦一致）；③ `check-inst-asm` **272/272**（`find tests/inst -name '*.S'`=272，现场派生）；`check-tests-index`/`check-case-ledger`/`check-inst-macro-scope`/`check-dirs`/`check-no-residue`/`check-interface` 全 rc=0；④ 4 个驱动 `--help` rc=0；⑤ 2 路注入：`lds_map` 改回旧路径 ⇒ `check-tests-index` rc=2；`Makefile` power.S 改回旧路径 ⇒ `build-bootrom` rc=2（llvm-mc 报 `No such file`）；`cp`+md5 还原（`ebb76f7a…`/`109d538b…` 前后一致）后回绿；⑥ 证据脚本 运行期证据目录内的 `run.sh`（默认 22 检查，`--inject` 自检）。

**新发现/坑**：① ld.lld 的 `INCLUDE` 与 llvm-mc 的 `.include` **只按 cwd（+`-L`）解析，不搜脚本所在目录**——迁移任何 lds/`.S` 到新目录时，要么改路径、要么补 `-L`，否则「文件在、构建却在旧路径找」。② 目录名带 `-` 不能作 Python 包 ⇒ 跨目录复用脚本须 `sys.path` + 平铺 import 或 `importlib` 按文件加载。③ `check_tests_index` 缺 lds 时在 INCLUDE 复核段抛异常（建议后续改成干净 FAIL）。

**遗留问题**：`components/{chipyard,musl}` 文档与 `docs/TestReports/M17-wuming-timing.md` 仍写旧路径（⏸，组件文档/冻结报告，须按组件流程另行处理）；`picolibc_tests --stage fast` 与 `run_embench_e2e` 的真实跑批未执行（本 worktree 无 `.work/source/{picolibc,embench-iot}` 语料，需 `make fetch`；两脚本的路径常量由 `--help` 与文件存在性覆盖，链接布局由 `test-elf`/lit/integ007t 间接验证）；`check-milestones-fresh` 在本 worktree 红 4 项（本分支台账早于 master 的任务号/目录名迁移与 `m14-linux-020/021` 入库，属分支态，非本改动引入；master 侧 `m15-testcases-011` 已在 `milestones-m15` 进行中表）；`.tao/knowledge/issues.yaml` 中 `picolibc_tests.py` 旧路径属台账（主会话维护）。
