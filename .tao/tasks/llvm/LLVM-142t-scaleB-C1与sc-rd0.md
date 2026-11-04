# LLVM-142t: scaleB C1 与 sc rd0 合法性

**模块**：llvm
**项目里程碑**：M11
**依赖**：`SPEC-181t`（待验收）
**状态**：已验证

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
5. 不修改测试资产；证据 `运行期证据（已清理，未归档）`；完成区 ≤30 行，状态 `待验收`。
6. 失败保留现场；不猜 spec；不复制 QEMU/gem5 实现。

## 完成区

**测试结果**：`运行期证据脚本（已清理，未归档）` rc=0（43/43 PASS；`--inject` 7/7 反例均可达 FAIL→还原后 43/43 回绿）。`make install-host` rc=0；`check-instrinfo`/`check-scope`/`check-patch-tree`（205 patches）/`check-component-changelog` rc=0。`make check-lit` rc=2：161 例中 159 绿，仅 `DADAO-MC :: fp-encoding.s`（旧 `rf` 第三操作数）、`DADAO-CodeGen :: fp-ldexp.ll`（旧断言 `io2fo/io2ft`）失败——均为测试资产，属测试任务。`make check-isa-coverage` rc=2（4 项：同上两例 lit 缺行 + `llvm-isa-backend-matrix.{tsv,md}` 仍为旧 `rf` 口径）。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOInstrInfoFP.td,DADAOCodeGen.td,DADAOISelLowering.cpp,DADAOISelLowering.h,AsmParser/DADAOAsmParser.cpp}.patch`（5 份导出补丁；`series` 98 不变）；`components/llvm-project/changelog.md`（新增 M11 节）；本任务书；`.tao/knowledge/milestones.md`。证据 `运行期证据（已清理，未归档）`。
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

### 第 1 轮 reviewer 验收（2026-11-02，独立重跑）

**环境/范围**：分支 `LLVM-142t`（HEAD `d0d72427`），`git status --porcelain -uall` 前/后均空；`git diff a211c9b0..HEAD` 恰 8 文件（5 补丁 + changelog + 本任务书 + milestones），对 `tests/ spec/ contracts/ components/{qemu,gem5}/ tools/` 改动数 = 0；`series` 98 未动。
**门控（我方重跑，真实 rc）**：`make install-host` rc=0（ninja 增量 23 步、重链 `llvm-mc`/`llc`，安装根 mtime 07:23/07:25）；`check-instrinfo` rc=0、`check-scope` rc=0、`check-patch-tree` rc=0（205 patches OK）、`check-component-changelog` rc=0。
**证据脚本**：`run.sh` rc=0（43/43 PASS）；`--inject` rc=0（7/7 反例检出，还原后 43/43）。逐条审脚本：每条 check 均为 expected/actual 字符串比对、有可达 FAIL 路径，无恒真/两支同果；`c_lit_full` 同时断言 rc=2 与失败集恰为两例，不掩盖新失败。
**独立注入（非现成脚本）**：`mv` 安装根 `llvm-mc`→恒失败 stub（先记 md5 `3693b3fe…`）→ 重跑同一 `run.sh`：**rc=1、21 FAIL**（含「check-lit failing set」FAIL）→ `mv` 还原 → md5 复核一致 → 重跑 rc=0、43/43；无 `*.preinject` 残留、仓库状态与注入前一致。
**行为核验（独立命令）**：`ftsclb rf4, rf6, rd8`=`[0x44,0x54,0x41,0x88]`、`fosclb rf4, rf6, rd63`=`[0x44,0x74,0x41,0xbf]`（与 `opcodes.yaml` orrr 位域 op=0x44/ha=0x15|0x1D/rdhd[5:0] 手工核算一致）；旧 `rf,rf,rf` 两条均 rc=1 `invalid operand`；objdump 回读 `rd8/rd63`；`llc` ldexp 产出 `ext.so rd4, rd16, 31; fosclb rf8, rf16, rd4`（f32 为 `ftsclb`），`grep io2fo|it2ft` 无命中；12 条 `sc.*` rdHB=rd0 全 rc=1、`error:` 级且诊断含 `dst_rd0`；`sc.o.nn rd8, rd0, [rb1]`（rdHC=rd0）rc=0；`sc.o.nn rd8, rd9, [rb1]`=`[0x47,0x40,0x82,0x41]` 与契约 `0x47408241` 一致（编码未改）。
**允许红的边界（用户 2026-11-02 裁定）**：`check-lit` rc=2，161 例 159 绿，FAIL 恰为 `fp-encoding.s`（旧 `ftsclb/fosclb rf4, rf6, rf8` 行 123/171 报 invalid operand）与 `fp-ldexp.ll`（旧断言 `CHECK-COUNT-1: io2fo/io2ft`）——单例 `-v` 复跑证实根因即旧资产；`check-isa-coverage` rc=2 恰 4 项（`gen-orrr.s` 缺 `ftsclb/fosclb rf8, rf9, rd10` 两行 + 矩阵 tsv/md：ftsclb/fosclb 行仍 `rf10`、`DADAOCodeGen.td.patch` 行号 +1 漂移），全为测试/矩阵资产（归 TESTCASES-090t），无其它失败被掩盖。
**输出真实性**：工程师 `run.log`/`inject.log` 与我方重跑逐行 diff 一致；完成区各数字（43/43、7/7、205、159/161、4 项、各编码值、`llc` 输出）逐项复核吻合。
**判决：Accepted**。约束逐条守住：未改 `tests/**`/`spec/**`/`contracts/**`/`components/{qemu,gem5}/**`；语义对齐实查 spec/contracts（`SimRISC-07` §2.1/附录B：`ftsclb/fosclb rfHB, rfHC, rdHD`、旧写法不再接受；`SimRISC-12`/`legality_rules.yaml`：`dst_rd0` 含 12 条 `sc.*`，rdHC 可为 rd0）；失败留痕于 `运行期临时日志`。
