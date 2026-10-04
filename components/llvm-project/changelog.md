# LLVM 组件变更记录

> 粒度：**按任务一条**，追加式。补丁集的生成/应用/校验规范见 `spec/Process-01-组件补丁组织与构建编排.md`。

| 日期 | 任务 | 变更 |
|---|---|---|
| 2026-09-23 | — | **M1 补丁集重整**：由「16 份编号补丁 + `git am`」改为「树形补丁集 + `git apply`」（本组件 8 → **36** 份 = 新增 32 + 修改 4）。应用后最终 tree hash = `0e058573eb70da9e57db6995d6caef6bbe8985da`（与重整前一致，语义未变）。决策见 `ADR-0002 D4`（rev. 2026-09-23）。 |
| 2026-10-02 | LLVM-026t | **汇编立即数字节化**：AsmParser 去 `i` 后缀、按字节解析、`%4` 校验 + 范围校验 + 编码 `>>2`；MCInstPrinter 反汇编 `<<2`、去 `i` 后缀。符号 fixup 保留（bypass matcher for expr operands）。顺带更新 `tests/lit/MC/Dadao/*.s`（4 文件）与 `tools/llvm/test_encoding_oracle.py`（语法同步，属 TESTCASES-021t 范围重叠）。 |
| 2026-10-03 | LLVM-027t | **`ret rd0` 静态检查**：AsmParser `matchAndEmitInstruction` 中，`ret rdHA, imms18` 当 `rdHA == rd0` 且 `imms18 != 0` 时硬报错（`Error` 级，汇编失败、非零退出码；不降 warning），落地 `SPEC-083t` 规则 `dst_rd0_nonzero` 的汇编期半边。新增 lit `tests/lit/MC/Dadao/ret-rd0-legality.s`。 |
| 2026-10-03 | LLVM-029t | **FP 编码层（scope: fp，60 条）**：新增 `DADAOInstrInfoFP.td`（60 条 FP def，`op`/`ha` 逐条取自 `contracts/opcodes.yaml`）；`DADAOInstrInfo.td` 仅 +1 行 `include`。AsmParser 组 count 白名单 +22 条 FP 块 mnemonic，并对 FP 块「两个 `{start:end}` 组 count 不等」硬报错（`Error` 级；M1 `rd2rd`/`rb2rb` 行为不变）；MCInstPrinter 块渲染白名单 +22。新增 lit `tests/lit/MC/Dadao/fp-encoding.s`（60 条）+ 独立 oracle 用例 61→121。 |
| 2026-10-03 | LLVM-030t | **FP 汇编期静态合法性检查**（`SPEC-088t` 的汇编期半边）：`DADAOAsmParser::matchAndEmitInstruction` 新增 4 类 `Error` 级硬报错——`dst_rf0`（35 条目的 rf0；rf0 作源/例外放行）、`mreg_range_overlap`（convert_ff 4 条同组范围交集，含完全重合）、`mreg_range_overflow`（FP 28 条任一组 count>63，覆盖 `{rf0:rf63}` 截断）、`encode_fp_root_n`（ftroot/foroot 仅 n=2）。新增 lit `tests/lit/MC/Dadao/fp-legality.s`；AsmParser 源 +165 行（1177→1342）。 |
| 2026-10-04 | LLVM-031t | **FP `dst_rd0` 汇编期静态检查**（`SPEC-089t` 的汇编期半边）：`DADAOAsmParser::matchAndEmitInstruction` 新增对 15 条 rd-目的 FP 指令（`convert_f2i` 8 + `classify` 2 + `compare` 4 + `rf2rd` 1）目的为 `rd0` 的 `Error` 级硬报错（`dst_rd0`；含 `{rd0:rd2}` 组首；rf0 作源放行）。新增 lit `tests/lit/MC/Dadao/fp-dst-rd0-legality.s`；AsmParser 源 +24 行（1342→1366）。 |
