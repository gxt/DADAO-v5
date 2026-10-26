# TESTCASES-073t: arch 迁移（cfx/权限）

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-071t
**状态**：待验收

## 目标（P3）
1. `tests/llvm/codegen/m5`（semihosting/CFX 权限）+ `tools/qemu/min_rom_probe_*` + bootrom → `tests/arch/<cfx>/`（bootrom/lds 进 `tests/shared` 或就近）。
2. 新门控 `check-arch-smoke`（L2，代表集）、`check-arch`（L3）；旧 `test-semihost`/min-ROM 入口保留别名。
3. 更新 `tests/arch.yaml`、ledger、Makefile/文档。

## 验收
- arch 代表集绿；旧 `test-semihost` 仍绿；无期望改动；`make check` 绿。

## 约束
- 只改本任务范围内的 `tests/`、`tools/testcases/`、`Makefile`、索引/`case-ledger`、`milestones.md`；不改 spec/qemu/LLVM 语义。
- **旧路径/旧门控在本任务内保留**（薄 wrapper/别名）；删除旧入口只在 `TESTCASES-076t` 做。
- 不改测试期望、不放宽断言；只做“搬家 + 接线 + 兼容层”。
- 只跑 smoke/定向；全量 `check-full`/夜跑留到 `TESTCASES-076t` 或任务空档。
- 临时目录 `/tmp/opencode/<任务号>/`；不提交。

## 完成区

**测试结果**：`.work/evidence/TESTCASES-073t/run.sh` ⇒ **18/18 PASS, RESULT: PASS（rc=0）**；4 处注入（索引/期望码/接线/wrapper）各自「改坏→FAIL→`cp`+md5 还原→回绿」；全量总耗时约 8 min（含 `make check` + `make test-semihost`）。

**修改文件**（只搬家/接线/兼容，**无期望值改动**）：
- 搬迁：`tests/llvm/codegen/m5/*`（10 `.s` + `expected.yaml` + `README`）→ `tests/arch/umon/`（旧路径留符号链接）；`tools/qemu/min_rom_probe_*`（31 `.py` + 1 `.sh`）→ `tools/testcases/arch/`（旧路径留 32 个薄 wrapper）；`tools/integ/run_m5_e2e.py` → `tools/testcases/arch/`（旧路径 wrapper）；`tests/scripts/{bootrom.S,bootrom_app.S,bootrom.lds}` → `tests/shared/bootrom/`（旧路径符号链接 3 个）
- 探针仅改路径上溯（`_REPO`/`_REPO_ROOT` 3→4 层、`os.chdir(_REPO_ROOT)`；逐文件 diff 只有这些行）；`run_m5_e2e.py` 仅改 `REPO_ROOT` 深度 + 默认 `--vectors-dir/--expected/--work-dir`（判据未改）
- 新增：`tests/arch/README.md`、`tests/arch/umon/README.md`（随迁改写）、`tools/testcases/arch/README.md`、本证据脚本
- 门控：`Makefile`（+`check-arch-smoke` L2 / `check-arch` L3；L2 成员 `test-semihost`→`check-arch-smoke`；L3 + `check-arch`；`test-semihost` = 别名并保留旧前置；`build-bootrom` 指 `tests/shared/bootrom/`；`GATE_LOCKED_TARGETS`/`.PHONY`/help）
- 索引/台账/文档：`tests/arch.yaml`（10 条 `arch-umon-*`）、`tests/{README,INVENTORY,qemu/README,scripts/README}`、`tests/llvm/lit/MC/DADAO/README-m5.md`、`tools/testcases/validate_m5_vectors.py`、`docs/Process-09`（§2 P3 注 + §11）、`.tao/knowledge/milestones.md`、本任务书

**验收结果**（真实输出；日志 `.work/log/testcases/TESTCASES-073t-*.log`、`/tmp/opencode/TESTCASES-073t/`）：
- `make check` rc=0（`repository checks (L1): PASS`）；`check-tests-index` rc=0（`arch=10` == 用例文件数）；`check-case-ledger` rc=0 且 `--write` 后**逐字节未变**（1958 条）
- `make check-arch-smoke` rc=0（10/10 逐例 PASS + `run_m5_e2e: PASS` + 25 服务 `RESULT: PASS`）；`make check-arch` rc=0（+ cfx 探针 044/045/049 各 `RESULT: PASS`）
- 旧命令 `make test-semihost` rc=0（走 `check-arch-smoke` + 旧前置 `test-elf/test-codegen/check`）；旧入口 `tools/integ/run_m5_e2e.py`、`tools/qemu/min_rom_probe_{044,045,046,049}t.py`、`min_rom_probe_022t.sh` 均等价可用
- 独立 oracle `validate_m5_vectors.py` rc=0（141 checks）；10 个 `.s` md5 与迁移前逐字节相同，`expected.yaml` 仅注释行变化（`git show HEAD:` 对账）

**新发现/坑**：① 迁移后目录深度变化使 `_REPO`/`REPO_ROOT` 少一层 → 探针解析到 `tools/`（`paths` 导入失败/找不到 qemu）；以括号配平重写（幂等）替代增量替换，并核查 `os.chdir`。② 目录符号链接的 `..` 层数按**链接所在目录**算（`tests/llvm/codegen/m5` → `../../arch/umon`），错一层会让 oracle 读不到文件；且 `ln -s` 落在已存在目录内会嵌套，须先 `rmdir`。③ `.work/log/**` 新文件名受 L1 A3 约束（`check-<name>.log` 或 `<TASK-ID>-<purpose>.log`），证据脚本内部日志须带任务号前缀。④ 注入用值必须按 manifest 实际写法（`expected_exit_code: 0x43` 非十进制 67）。⑤ L2 改造后**不再顺带跑 L1**（原 `test-semihost` 自带 `check` 前置）；已按「一个检查只在一层」处理后记入 Makefile 注，旧命令保留旧前置。

**遗留问题**：① `tools/qemu/min_rom_probe_047t.py` 的 `stack_in_ram0` 期望常量（`0xFC00_0000_00F0_0000`）与 `bootrom.S` 实际写入（`0xFC00_00F0_0000`，RAM+15 MiB）不一致 ⇒ 迁移前即 FAIL，按「不改期望」未纳入 `check-arch`，待 QEMU/INTEG 侧另立任务订正。② 5 个探针迁移前即 FAIL（030t/034t/035t/038t/040t：RAS/`cs.eq`/`ftcls`/`sub.o` 期望与现行 spec 漂移；035t 引用的 `SimRISC-07` 节名已变）⇒ 迁移前亦未入门控，保持原状。③ `validate_m5_vectors.py`（独立 oracle）仍未接入任何 make 目标（迁移前亦如此），建议 `TESTCASES-076t` 或 L1 增补。④ `tests/scripts/` 的 bootrom 符号链接、`tests/llvm/codegen/m5/` 符号链接与 32 个探针 wrapper 待 `TESTCASES-076t` 删除。⑤ 全量 `check-full`/夜跑未跑（任务约束）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

逐行审查范围：31 个探针（仅 `_REPO`/`chdir` 行）、`run_m5_e2e.py`（`REPO_ROOT` + 3 个默认值）、32 个 wrapper（模板逐字比对 + 目标存在性 + 抽样实跑 044/045/046/049/022t.sh/run_m5_e2e）、`022t.sh`（`cd` 深度 + import 路径）、`Makefile` 门控块、`tests/arch.yaml`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `run_m5_e2e.py` 迁到 3 层后 `REPO_ROOT` 少一层 ⇒ `import paths` 失败（实测 `ModuleNotFoundError`） | ✅已修 | `REPO_ROOT` 改为 `..×3` | C8/C10 绿；`run_m5_e2e: PASS` |
| 探针 `_REPO` 增量替换**非幂等**（首轮中断后重跑叠成 5 层） | ✅已修 | 括号配平重写为固定 4 层（幂等）+ `os.chdir(_REPO_ROOT)` | 逐文件 diff 仅路径行；044/045/046/049/042/070/071/072/074 ×2 轮 PASS |
| `tests/llvm/codegen/m5` 符号链接 `..` 少一层 ⇒ 指向 `arch/umon`（不存在），且 `ln -s` 嵌进旧空目录 | ✅已修 | 删嵌套链接 + `rmdir` 后重建 `../../arch/umon` | C2 路径相等；`validate_m5_vectors` 141 checks PASS |
| 证据脚本 `probe_wiring` 复用会写计数器的 `c12_wiring` ⇒ 计数器被污染（C12 假红、I3 假绿） | ✅已修 | 改为独立 grep 探针；所有 `cN` 显式 `return "$rc"` | 18/18 PASS；I3 `fail_rc=1 ok_rc=0 md5=same` |
| 证据脚本日志名违反 L1 `check-run-artifacts` A3（`.work/log/**` 命名） ⇒ C13 假红 | ✅已修 | 内部日志统一前缀 `TESTCASES-073t-` | C13 rc=0；`check-run-artifacts` PASS |
| 注入 I2 用十进制 `67`，manifest 实为 `0x43` | ✅已修 | 注入改 `0x43→0x44`（按 YAML 块定位） | I2 `fail_rc=1 ok_rc=0` |
| `grep -c` 无匹配时 `|| echo 0` 产生双值 ⇒ 计数比较异常 | ✅已修 | 去掉 `|| echo 0`，用 `${passes:-0}` | C8 `期望=10 实际=10` |
| 047t `stack_in_ram0` 期望与 `bootrom.S` 不一致（迁移前即 FAIL） | ⏸延后 | 不改期望、不入 `check-arch`，登记遗留①（bootrom 与探针常量对账属 QEMU/INTEG 面） | 迁移前后均 FAIL；`grep` 证据见完成区 |
| 030/034/035/038/040 探针期望与现行 spec 漂移（迁移前即 FAIL） | ⏸延后 | 保持原状、不入任何门控（迁移前亦未入），登记遗留② | 迁移前后均 FAIL；未纳入 `check-arch` |
| L2 因 `test-semihost`→`check-arch-smoke` 后不再顺带跑 L1（原前置 `check`） | ✅已修（明示） | Makefile 注释说明「一个检查只在一层」；旧命令保留旧前置 | C12 接线检查；`make test-semihost` rc=0 |

**判决**：改动范围内无未修 finding（2 项 ⏸ 属**迁移前既有失败**、按任务「不改期望」约束不动，已登记）；状态 `待验收`。
