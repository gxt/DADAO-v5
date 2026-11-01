# LLVM-142t: scaleB C1 与 sc rd0 合法性

**模块**：llvm
**项目里程碑**：M11
**依赖**：`SPEC-181t`（待验收）
**状态**：待验收

## 用户授权

用户 2026-11-01 裁决：`ftsclb`/`fosclb` 第三源 `rf → rd`（同 `orrr` 编码，C1）；`sc rdHB=rd0 ⇒ ILLI`；授权分别建 LLVM/QEMU 任务。

用户 2026-11-02 裁定：**扩展 `TESTCASES-090t`** 接收 LLVM lit 与 isa matrix 同步；LLVM-142t 只验实现与定向行为，不要求 `check-lit`/`check-isa-coverage` 在本分支全局回绿。

## 目标

1. **scaleB C1**
   - `ftsclb`/`fosclb` 第三操作数从 `rfHD` 改为 `rdHD`；编码/opc/ha 不变。
   - MC/AsmParser/InstPrinter：语法 `ftsclb rfHB, rfHC, rdHD`；旧 `rf,rf,rf` 拒绝。
   - CodeGen：`DADAOScalb`/`ISD::FLDEXP` 的指数走 RD（有符号 64 位），不再 `f64/f32` 转 int。
   - 指令属性/寄存器类/编码验证与 SPEC-181t 一致。
2. **sc rd0**
   - 汇编期对 `sc rdHB, rdHC, [rbHD]` 且 `rdHB=rd0` 硬报错（Error 级，非 warning），与 spec ILLI 口径一致；
   - 编码/反汇编路径不静默成功；不改变 sc 编码。
3. 不修改 `tests/**`/`spec/**`/`contracts/**`/`components/qemu/**`/`components/gem5/**`；测试另立任务。

## 文件范围

- `components/llvm-project/**`（TD、MC、AsmParser、CodeGen、changelog、series）
- 本任务书、`milestones.md`

## 验收

1. `make install-host` 后：新旧语法汇编检查、反汇编/编码检查。
2. `check-instrinfo`、`check-scope` 真实 rc=0。
3. `make install-host` 后定向行为检查 rc=0：新/旧语法、反汇编、编码；旧 `rf` 写法必须失败。
4. `check-lit`/`check-isa-coverage` 的全局回绿由 `TESTCASES-090t` 负责；本任务只记录失败例与原因，不修改 `tests/**`/`tools/llvm/**`。
5. 不修改测试资产；证据 `.work/evidence/<任务ID>/`；完成区 ≤30 行，状态 `待验收`。
6. 失败保留现场；不猜 spec；不复制 QEMU/gem5 实现。

## 完成区

**测试结果**：`.work/evidence/LLVM-142t/run.sh` rc=0（43/43 PASS；`--inject` 7/7 反例均可达 FAIL→还原后 43/43 回绿）。`make install-host` rc=0；`check-instrinfo`/`check-scope`/`check-patch-tree`（205 patches）/`check-component-changelog` rc=0。`make check-lit` rc=2：161 例中 159 绿，仅 `DADAO-MC :: fp-encoding.s`（旧 `rf` 第三操作数）、`DADAO-CodeGen :: fp-ldexp.ll`（旧断言 `io2fo/io2ft`）失败——均为测试资产，属测试任务。`make check-isa-coverage` rc=2（4 项：同上两例 lit 缺行 + `llvm-isa-backend-matrix.{tsv,md}` 仍为旧 `rf` 口径）。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOInstrInfoFP.td,DADAOCodeGen.td,DADAOISelLowering.cpp,DADAOISelLowering.h,AsmParser/DADAOAsmParser.cpp}.patch`（5 份导出补丁；`series` 98 不变）；`components/llvm-project/changelog.md`（新增 M11 节）；本任务书；`.tao/knowledge/milestones.md`。证据 `.work/evidence/LLVM-142t/{run.sh,run.log,inject.log}`。
**验收结果**：`ftsclb rf4, rf6, rd8` = `44 54 41 88`、`fosclb rf4, rf6, rd63` = `44 74 41 bf`（同 `orrr`，op/ha 不变）；旧 `ftsclb/fosclb rf4, rf6, rf8` rc=1 `invalid operand`；反汇编/`-filetype=asm` 回读 `rdN`。`llc` 的 `ldexp` 产出 `ext.so rd4, rd16, 31; fosclb rf8, rf16, rd4`（f32 为 `ftsclb`），无 `io2fo/it2ft`。12 条 `sc.*` 的 `rdHB=rd0` 全部 rc=1 且诊断含 `dst_rd0`；`sc.o.nn rd8, rd0, [rb1]` 仍可汇编（`rdHC=rd0` 合法）；sc 编码未改（`47 40 82 41`）。
**新发现/坑**：① 任务书验收 2/3 要求 `check-isa-coverage`/`check-lit` rc=0，但驱动这两项回绿必须改 `tests/unit/llvm/lit/MC/DADAO-gen/gen-orrr.s`、`tests/unit/llvm/lit/{MC/DADAO/fp-encoding.s,CodeGen/DADAO/fp-ldexp.ll}` 与 `tools/llvm/llvm-isa-backend-matrix.{tsv,md}`，而本任务明令不改 `tests/**`、文件范围也不含 `tools/llvm/**` ⇒ 门控无法在本任务内变绿，需测试任务同步（命令：`python3 tools/testcases/generate_lit_vectors.py` 重生成 lit、`python3 tools/llvm/gen_isa_coverage.py` 重生成矩阵）。② `gen_isa_coverage` 以补丁物理行号作证据，任何后端补丁行变动都会使其 FAIL，属预期。
**遗留问题**：① `check-isa-coverage` rc=2、`check-lit` rc=2 的 4+2 项均因上述测试/矩阵资产仍为旧 `rf` 口径；待测试任务按新语义重生成后应回绿（本任务未动 `tests/**`/`tools/llvm/**`）。② 旧 lit 的 `fp-ldexp.ll` 断言需改为「无 `io2fo/io2ft`、指数为 `rd`」。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 5 个补丁文件：
- `DADAOInstrInfoFP.td`：两个 def 仅改第三操作数类 `GPRF→GPRD`，`op/ha/Pattern` 未动；编码字段 `hd` 仍取 `$rd`，与 `contracts/opcodes.yaml`（`rdhd` bank `rd`）一致。
- `DADAOCodeGen.td`：`SDT_DADAOScalb` 第二操作数改 `i64`；两个 `Pat` 输入输出均绑 `i64:$n`，TableGen 由指令操作数类推断为 GPRD；构建无歧义（`-gen-dag-isel` 通过）。
- `DADAOISelLowering.cpp`：`LowerFLDEXP` 删除 `SINT_TO_FP`，仍对非 i64 指数做 `SIGN_EXTEND`；`llc` 实测无 `io2fo/it2ft`，负指数语义由 `ext.so`（符号扩展）保留。
- `DADAOAsmParser.cpp`：`sc.*` 检查置于 `MatchInstructionImpl` 前、`Error` 级；仅当 `Flat[1]` 是寄存器且为 `rd0` 触发；`rdHC=rd0` 不受影响（已测）。
- 防造假：所有结论均有 `run.log`/`inject.log` 与门控日志的真实 rc；补丁由 `make_patch.py` 导出、`check-patch-tree` 205 OK。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 无 | — | — | — |


### 第 1 轮 architect 提交对账（WIP）
- 档位：**WIP**（reviewer 未验收，任务仍 `待验收`；`check-lit`/`check-isa-coverage` 红）
- 提交：`36400def WIP: LLVM-142t scaleB C1 与 sc rd0（测试资产待同步）`，8 文件、+78/-39
- 对账：`git diff --cached --name-only` 8 项与完成区「修改文件」逐项一致（5 份导出补丁 + `changelog.md` + 本任务书 + `milestones.md`）；核 `git status -uall` 无 `tests/**`、`spec/**`、`contracts/**`、`components/{qemu,gem5}/**` 改动；无漏提 / 多提 / 越界。**未 push**。
