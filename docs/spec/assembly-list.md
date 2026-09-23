# DADAO 汇编指令完整列表（自动生成）

> **生成器**：`tools/llvm/gen_asm_list.py`（本文件为生成物，请勿手工编辑；改生成器后重跑）
> **源**：`contracts/opcodes.yaml`（256 条 = M1 178 + `excluded_m1` 78）
> **推导规则**：操作数取 `role ∈ {dst, src, imm, wyde_pos, cfxcode, cfx_cg, cfx_rc}`；
> `minor_op`（165 处）已内嵌助记符，不作操作数；拆分的立即数字段合并为单一操作数。
> **验证**：M1 条目逐条送 `llvm-mc --triple=dadao-unknown-elf` 汇编（示例列即被验证的真实行）；
> `excluded_m1` 条目 M1 未实现，仅列出规范推导形式。
> **统计**：M1 验证通过 **178** 条，失败 **0** 条。

## 立即数范围速查

| 字段 | 范围 |
|---|---|
| `imms12` | s12: -2048..2047 |
| `imms18` | s18: -131072..131071 |
| `imms24` | s24: -8388608..8388607 |
| `immu6` | u6: 0..63 |
| `immu12` | u12: 0..4095 |
| `immu16` | u16: 0..65535 |
| `immu18` | u18: 0..262143 |
| `immu24` | u24: 0..16777215 |
| `wpN` | wyde 位置 0..3（写作数字；`wpN` 记法不是合法汇编语法） |

### `ciii`（2 条）

| insn | 汇编形式（模板） | 汇编形式（示例） | 操作数（role/bank） | 立即数范围 | op/mask/value | 范围 | lit | llvm-mc |
|---|---|---|---|---|---|---|---|---|
| `escape-ciii` | `escape cfx_<name>, imms18` | `escape cfx_power, 1` | cfxcode:imm, imms18:imm | imms18 s18: -131072..131071 | `0x7E` / `0xFF000000` / `0x7E000000` | excluded | — | — (excluded_m1) |
| `trap-ciii` | `trap cfx_<name>, immu18` | `trap cfx_power, 1` | cfxcode:imm, immu18:imm | immu18 u18: 0..262143 | `0x7F` / `0xFF000000` / `0x7F000000` | excluded | — | — (excluded_m1) |

### `crii`（2 条）

| insn | 汇编形式（模板） | 汇编形式（示例） | 操作数（role/bank） | 立即数范围 | op/mask/value | 范围 | lit | llvm-mc |
|---|---|---|---|---|---|---|---|---|
| `cfxld-crii` | `cfxld cfx_<name>, rbN, immu12` | `cfxld cfx_power, rb2, 1` | cfxcode:imm, rb:reg, immu12:imm | immu12 u12: 0..4095 | `0x7C` / `0xFF000000` / `0x7C000000` | excluded | — | — (excluded_m1) |
| `cfxst-crii` | `cfxst cfx_<name>, rbN, immu12` | `cfxst cfx_power, rb2, 1` | cfxcode:imm, rb:reg, immu12:imm | immu12 u12: 0..4095 | `0x7D` / `0xFF000000` / `0x7D000000` | excluded | — | — (excluded_m1) |

### `crrr`（2 条）

| insn | 汇编形式（模板） | 汇编形式（示例） | 操作数（role/bank） | 立即数范围 | op/mask/value | 范围 | lit | llvm-mc |
|---|---|---|---|---|---|---|---|---|
| `cfx2rd-crrr` | `cfx2rd cfx_<name>, cfx_<name>, cfx_<name>, rdN` | `cfx2rd cfx_power, cfx_power, cfx_power, rd8` | cfxcode:imm, cghb:imm, rchc:imm, rd:reg | — | `0x7A` / `0xFF000000` / `0x7A000000` | excluded | — | — (excluded_m1) |
| `cfx2rc-crrr` | `cfx2rc cfx_<name>, cfx_<name>, cfx_<name>, rdN` | `cfx2rc cfx_power, cfx_power, cfx_power, rd8` | cfxcode:imm, cghb:imm, rchc:imm, rd:reg | — | `0x7B` / `0xFF000000` / `0x7B000000` | excluded | — | — (excluded_m1) |

### `iiii`（3 条）

| insn | 汇编形式（模板） | 汇编形式（示例） | 操作数（role/bank） | 立即数范围 | op/mask/value | 范围 | lit | llvm-mc |
|---|---|---|---|---|---|---|---|---|
| `jump-iiii` | `jump imms24` | `jump 1` | imms24:imm | imms24 s24: -8388608..8388607 | `0x70` / `0xFF000000` / `0x70000000` | M1 | e_flags.s | ✅ |
| `call-iiii` | `call imms24` | `call 1` | imms24:imm | imms24 s24: -8388608..8388607 | `0x74` / `0xFF000000` / `0x74000000` | M1 | iiii_jump.s | ✅ |
| `swym-iiii` | `swym immu24` | `swym 1` | immu24:imm | immu24 u24: 0..16777215 | `0x77` / `0xFF000000` / `0x77000000` | M1 | basic-encoding.s | ✅ |

### `oiii`（2 条）

| insn | 汇编形式（模板） | 汇编形式（示例） | 操作数（role/bank） | 立即数范围 | op/mask/value | 范围 | lit | llvm-mc |
|---|---|---|---|---|---|---|---|---|
| `illi` | `illi immu18` | `illi 1` | immu18:imm | immu18 u18: 0..262143 | `0x00` / `0xFFFC0000` / `0x00000000` | M1 | oiii.s | ✅ |
| `fence` | `fence immu18` | `fence 1` | immu18:imm | immu18 u18: 0..262143 | `0x00` / `0xFFFC0000` / `0x00040000` | M1 | — | ✅ |

### `orri`（54 条）

| insn | 汇编形式（模板） | 汇编形式（示例） | 操作数（role/bank） | 立即数范围 | op/mask/value | 范围 | lit | llvm-mc |
|---|---|---|---|---|---|---|---|---|
| `ext.uo` | `ext.uo rdN, rdN, immu6` | `ext.uo rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x40` / `0xFFFC0000` / `0x40600000` | M1 | orri.s | ✅ |
| `ext.so` | `ext.so rdN, rdN, immu6` | `ext.so rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x40` / `0xFFFC0000` / `0x40640000` | M1 | — | ✅ |
| `shr.uo` | `shr.uo rdN, rdN, immu6` | `shr.uo rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x40` / `0xFFFC0000` / `0x40680000` | M1 | — | ✅ |
| `shr.so` | `shr.so rdN, rdN, immu6` | `shr.so rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x40` / `0xFFFC0000` / `0x406C0000` | M1 | — | ✅ |
| `shl.uo` | `shl.uo rdN, rdN, immu6` | `shl.uo rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x40` / `0xFFFC0000` / `0x40700000` | M1 | — | ✅ |
| `rd2rd` | `rd2rd rdN, rdN, immu6` | `rd2rd rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x40` / `0xFFFC0000` / `0x40B00000` | M1 | rb_ops.s | ✅ |
| `rd2ra` | `rd2ra raN, rdN, immu6` | `rd2ra ra1, rd8, 1` | ra:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x40` / `0xFFFC0000` / `0x40B40000` | M1 | ra.s | ✅ |
| `ra2rd` | `ra2rd rdN, raN, immu6` | `ra2rd rd8, ra1, 1` | rd:reg, ra:reg, immu6:imm | immu6 u6: 0..63 | `0x40` / `0xFFFC0000` / `0x40B80000` | M1 | ra.s | ✅ |
| `rb2rb` | `rb2rb rbN, rbN, immu6` | `rb2rb rb2, rb2, 1` | rb:reg, rb:reg, immu6:imm | immu6 u6: 0..63 | `0x40` / `0xFFFC0000` / `0x40D00000` | M1 | — | ✅ |
| `rd2rb` | `rd2rb rbN, rdN, immu6` | `rd2rb rb2, rd8, 1` | rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x40` / `0xFFFC0000` / `0x40D40000` | M1 | — | ✅ |
| `rb2rd` | `rb2rd rdN, rbN, immu6` | `rb2rd rd8, rb2, 1` | rd:reg, rb:reg, immu6:imm | immu6 u6: 0..63 | `0x40` / `0xFFFC0000` / `0x40D80000` | M1 | rb_ops.s | ✅ |
| `rd2rf` | `rd2rf rfN, rdN, immu6` | `rd2rf rf2, rd8, 1` | rf:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x40` / `0xFFFC0000` / `0x40F40000` | excluded | — | — (excluded_m1) |
| `rf2rd` | `rf2rd rdN, rfN, immu6` | `rf2rd rd8, rf2, 1` | rd:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x40` / `0xFFFC0000` / `0x40F80000` | excluded | — | — (excluded_m1) |
| `ext.ut` | `ext.ut rdN, rdN, immu6` | `ext.ut rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x41` / `0xFFFC0000` / `0x41600000` | M1 | — | ✅ |
| `ext.st` | `ext.st rdN, rdN, immu6` | `ext.st rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x41` / `0xFFFC0000` / `0x41640000` | M1 | — | ✅ |
| `shr.ut` | `shr.ut rdN, rdN, immu6` | `shr.ut rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x41` / `0xFFFC0000` / `0x41680000` | M1 | — | ✅ |
| `shr.st` | `shr.st rdN, rdN, immu6` | `shr.st rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x41` / `0xFFFC0000` / `0x416C0000` | M1 | — | ✅ |
| `shl.ut` | `shl.ut rdN, rdN, immu6` | `shl.ut rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x41` / `0xFFFC0000` / `0x41700000` | M1 | — | ✅ |
| `ext.uw` | `ext.uw rdN, rdN, immu6` | `ext.uw rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x42` / `0xFFFC0000` / `0x42600000` | M1 | — | ✅ |
| `ext.sw` | `ext.sw rdN, rdN, immu6` | `ext.sw rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x42` / `0xFFFC0000` / `0x42640000` | M1 | — | ✅ |
| `shr.uw` | `shr.uw rdN, rdN, immu6` | `shr.uw rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x42` / `0xFFFC0000` / `0x42680000` | M1 | — | ✅ |
| `shr.sw` | `shr.sw rdN, rdN, immu6` | `shr.sw rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x42` / `0xFFFC0000` / `0x426C0000` | M1 | — | ✅ |
| `shl.uw` | `shl.uw rdN, rdN, immu6` | `shl.uw rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x42` / `0xFFFC0000` / `0x42700000` | M1 | — | ✅ |
| `ext.ub` | `ext.ub rdN, rdN, immu6` | `ext.ub rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x43` / `0xFFFC0000` / `0x43600000` | M1 | — | ✅ |
| `ext.sb` | `ext.sb rdN, rdN, immu6` | `ext.sb rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x43` / `0xFFFC0000` / `0x43640000` | M1 | — | ✅ |
| `shr.ub` | `shr.ub rdN, rdN, immu6` | `shr.ub rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x43` / `0xFFFC0000` / `0x43680000` | M1 | — | ✅ |
| `shr.sb` | `shr.sb rdN, rdN, immu6` | `shr.sb rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x43` / `0xFFFC0000` / `0x436C0000` | M1 | — | ✅ |
| `shl.ub` | `shl.ub rdN, rdN, immu6` | `shl.ub rd8, rd8, 1` | rd:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x43` / `0xFFFC0000` / `0x43700000` | M1 | — | ✅ |
| `ftcls` | `ftcls rdN, rfN, immu6` | `ftcls rd8, rf2, 1` | rd:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44000000` | excluded | — | — (excluded_m1) |
| `ft2fo` | `ft2fo rfN, rfN, immu6` | `ft2fo rf2, rf2, 1` | rf:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44040000` | excluded | — | — (excluded_m1) |
| `ft2ft` | `ft2ft rfN, rfN, immu6` | `ft2ft rf2, rf2, 1` | rf:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44080000` | excluded | — | — (excluded_m1) |
| `ftroot` | `ftroot rfN, rfN, immu6` | `ftroot rf2, rf2, 1` | rf:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44180000` | excluded | — | — (excluded_m1) |
| `ftlog` | `ftlog rfN, rfN, immu6` | `ftlog rf2, rf2, 1` | rf:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x441C0000` | excluded | — | — (excluded_m1) |
| `focls` | `focls rdN, rfN, immu6` | `focls rd8, rf2, 1` | rd:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44200000` | excluded | — | — (excluded_m1) |
| `fo2ft` | `fo2ft rfN, rfN, immu6` | `fo2ft rf2, rf2, 1` | rf:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44240000` | excluded | — | — (excluded_m1) |
| `fo2fo` | `fo2fo rfN, rfN, immu6` | `fo2fo rf2, rf2, 1` | rf:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44280000` | excluded | — | — (excluded_m1) |
| `foroot` | `foroot rfN, rfN, immu6` | `foroot rf2, rf2, 1` | rf:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44380000` | excluded | — | — (excluded_m1) |
| `folog` | `folog rfN, rfN, immu6` | `folog rf2, rf2, 1` | rf:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x443C0000` | excluded | — | — (excluded_m1) |
| `ft2it` | `ft2it rdN, rfN, immu6` | `ft2it rd8, rf2, 1` | rd:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44C00000` | excluded | — | — (excluded_m1) |
| `ft2io` | `ft2io rdN, rfN, immu6` | `ft2io rd8, rf2, 1` | rd:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44C40000` | excluded | — | — (excluded_m1) |
| `ft2ut` | `ft2ut rdN, rfN, immu6` | `ft2ut rd8, rf2, 1` | rd:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44C80000` | excluded | — | — (excluded_m1) |
| `ft2uo` | `ft2uo rdN, rfN, immu6` | `ft2uo rd8, rf2, 1` | rd:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44CC0000` | excluded | — | — (excluded_m1) |
| `it2ft` | `it2ft rfN, rdN, immu6` | `it2ft rf2, rd8, 1` | rf:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44D00000` | excluded | — | — (excluded_m1) |
| `io2ft` | `io2ft rfN, rdN, immu6` | `io2ft rf2, rd8, 1` | rf:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44D40000` | excluded | — | — (excluded_m1) |
| `ut2ft` | `ut2ft rfN, rdN, immu6` | `ut2ft rf2, rd8, 1` | rf:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44D80000` | excluded | — | — (excluded_m1) |
| `uo2ft` | `uo2ft rfN, rdN, immu6` | `uo2ft rf2, rd8, 1` | rf:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44DC0000` | excluded | — | — (excluded_m1) |
| `fo2it` | `fo2it rdN, rfN, immu6` | `fo2it rd8, rf2, 1` | rd:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44E00000` | excluded | — | — (excluded_m1) |
| `fo2io` | `fo2io rdN, rfN, immu6` | `fo2io rd8, rf2, 1` | rd:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44E40000` | excluded | — | — (excluded_m1) |
| `fo2ut` | `fo2ut rdN, rfN, immu6` | `fo2ut rd8, rf2, 1` | rd:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44E80000` | excluded | — | — (excluded_m1) |
| `fo2uo` | `fo2uo rdN, rfN, immu6` | `fo2uo rd8, rf2, 1` | rd:reg, rf:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44EC0000` | excluded | — | — (excluded_m1) |
| `it2fo` | `it2fo rfN, rdN, immu6` | `it2fo rf2, rd8, 1` | rf:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44F00000` | excluded | — | — (excluded_m1) |
| `io2fo` | `io2fo rfN, rdN, immu6` | `io2fo rf2, rd8, 1` | rf:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44F40000` | excluded | — | — (excluded_m1) |
| `ut2fo` | `ut2fo rfN, rdN, immu6` | `ut2fo rf2, rd8, 1` | rf:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44F80000` | excluded | — | — (excluded_m1) |
| `uo2fo` | `uo2fo rfN, rdN, immu6` | `uo2fo rf2, rd8, 1` | rf:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x44` / `0xFFFC0000` / `0x44FC0000` | excluded | — | — (excluded_m1) |

### `orrr`（109 条）

| insn | 汇编形式（模板） | 汇编形式（示例） | 操作数（role/bank） | 立即数范围 | op/mask/value | 范围 | lit | llvm-mc |
|---|---|---|---|---|---|---|---|---|
| `lr_nn.o` | `lr_nn.o rdN, rdN, rbN` | `lr_nn.o rd8, rd8, rb2` | rd:reg, rd:reg, rb:reg | — | `0x00` / `0xFFFC0000` / `0x00400000` | excluded | — | — (excluded_m1) |
| `lr_nr.o` | `lr_nr.o rdN, rdN, rbN` | `lr_nr.o rd8, rd8, rb2` | rd:reg, rd:reg, rb:reg | — | `0x00` / `0xFFFC0000` / `0x00440000` | excluded | — | — (excluded_m1) |
| `lr_an.o` | `lr_an.o rdN, rdN, rbN` | `lr_an.o rd8, rd8, rb2` | rd:reg, rd:reg, rb:reg | — | `0x00` / `0xFFFC0000` / `0x00480000` | excluded | — | — (excluded_m1) |
| `lr_ar.o` | `lr_ar.o rdN, rdN, rbN` | `lr_ar.o rd8, rd8, rb2` | rd:reg, rd:reg, rb:reg | — | `0x00` / `0xFFFC0000` / `0x004C0000` | excluded | — | — (excluded_m1) |
| `sc_nn.o` | `sc_nn.o rdN, rdN, rbN` | `sc_nn.o rd8, rd8, rb2` | rd:reg, rd:reg, rb:reg | — | `0x00` / `0xFFFC0000` / `0x00600000` | excluded | — | — (excluded_m1) |
| `sc_nr.o` | `sc_nr.o rdN, rdN, rbN` | `sc_nr.o rd8, rd8, rb2` | rd:reg, rd:reg, rb:reg | — | `0x00` / `0xFFFC0000` / `0x00640000` | excluded | — | — (excluded_m1) |
| `sc_an.o` | `sc_an.o rdN, rdN, rbN` | `sc_an.o rd8, rd8, rb2` | rd:reg, rd:reg, rb:reg | — | `0x00` / `0xFFFC0000` / `0x00680000` | excluded | — | — (excluded_m1) |
| `sc_ar.o` | `sc_ar.o rdN, rdN, rbN` | `sc_ar.o rd8, rd8, rb2` | rd:reg, rd:reg, rb:reg | — | `0x00` / `0xFFFC0000` / `0x006C0000` | excluded | — | — (excluded_m1) |
| `and.o` | `and.o rdN, rdN, rdN` | `and.o rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x40` / `0xFFFC0000` / `0x40200000` | M1 | — | ✅ |
| `or.o` | `or.o rdN, rdN, rdN` | `or.o rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x40` / `0xFFFC0000` / `0x40240000` | M1 | orrr.s | ✅ |
| `xor.o` | `xor.o rdN, rdN, rdN` | `xor.o rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x40` / `0xFFFC0000` / `0x40280000` | M1 | — | ✅ |
| `xnor.o` | `xnor.o rdN, rdN, rdN` | `xnor.o rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x40` / `0xFFFC0000` / `0x402C0000` | M1 | — | ✅ |
| `ext.uo` | `ext.uo rdN, rdN, rdN` | `ext.uo rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x40` / `0xFFFC0000` / `0x40400000` | M1 | orri.s | ✅ |
| `ext.so` | `ext.so rdN, rdN, rdN` | `ext.so rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x40` / `0xFFFC0000` / `0x40440000` | M1 | — | ✅ |
| `shr.uo` | `shr.uo rdN, rdN, rdN` | `shr.uo rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x40` / `0xFFFC0000` / `0x40480000` | M1 | — | ✅ |
| `shr.so` | `shr.so rdN, rdN, rdN` | `shr.so rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x40` / `0xFFFC0000` / `0x404C0000` | M1 | — | ✅ |
| `shl.uo` | `shl.uo rdN, rdN, rdN` | `shl.uo rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x40` / `0xFFFC0000` / `0x40500000` | M1 | — | ✅ |
| `add.so-rb` | `add.so rbN, rbN, rdN` | `add.so rb2, rb2, rd8` | rb:reg, rb:reg, rd:reg | — | `0x40` / `0xFFFC0000` / `0x40800000` | M1 | rrrr.s | ✅ |
| `sub.so-rb` | `sub.so rbN, rbN, rdN` | `sub.so rb2, rb2, rd8` | rb:reg, rb:reg, rd:reg | — | `0x40` / `0xFFFC0000` / `0x40A00000` | M1 | — | ✅ |
| `cmp.uo-rb` | `cmp.uo rdN, rbN, rbN` | `cmp.uo rd8, rb2, rb2` | rd:reg, rb:reg, rb:reg | — | `0x40` / `0xFFFC0000` / `0x40A40000` | M1 | — | ✅ |
| `cmp.uo` | `cmp.uo rdN, rdN, rdN` | `cmp.uo rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x40` / `0xFFFC0000` / `0x40A80000` | M1 | — | ✅ |
| `cmp.so` | `cmp.so rdN, rdN, rdN` | `cmp.so rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x40` / `0xFFFC0000` / `0x40AC0000` | M1 | — | ✅ |
| `div.uo` | `div.uo rdN, rdN, rdN` | `div.uo rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x40` / `0xFFFC0000` / `0x40E00000` | M1 | — | ✅ |
| `div.so` | `div.so rdN, rdN, rdN` | `div.so rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x40` / `0xFFFC0000` / `0x40E40000` | M1 | — | ✅ |
| `rem.uo` | `rem.uo rdN, rdN, rdN` | `rem.uo rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x40` / `0xFFFC0000` / `0x40E80000` | M1 | — | ✅ |
| `rem.so` | `rem.so rdN, rdN, rdN` | `rem.so rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x40` / `0xFFFC0000` / `0x40EC0000` | M1 | — | ✅ |
| `and.t` | `and.t rdN, rdN, rdN` | `and.t rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41200000` | M1 | — | ✅ |
| `or.t` | `or.t rdN, rdN, rdN` | `or.t rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41240000` | M1 | — | ✅ |
| `xor.t` | `xor.t rdN, rdN, rdN` | `xor.t rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41280000` | M1 | — | ✅ |
| `xnor.t` | `xnor.t rdN, rdN, rdN` | `xnor.t rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x412C0000` | M1 | — | ✅ |
| `ext.ut` | `ext.ut rdN, rdN, rdN` | `ext.ut rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41400000` | M1 | — | ✅ |
| `ext.st` | `ext.st rdN, rdN, rdN` | `ext.st rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41440000` | M1 | — | ✅ |
| `shr.ut` | `shr.ut rdN, rdN, rdN` | `shr.ut rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41480000` | M1 | — | ✅ |
| `shr.st` | `shr.st rdN, rdN, rdN` | `shr.st rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x414C0000` | M1 | — | ✅ |
| `shl.ut` | `shl.ut rdN, rdN, rdN` | `shl.ut rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41500000` | M1 | — | ✅ |
| `add.ut` | `add.ut rdN, rdN, rdN` | `add.ut rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41800000` | M1 | — | ✅ |
| `add.st` | `add.st rdN, rdN, rdN` | `add.st rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41840000` | M1 | — | ✅ |
| `sub.ut` | `sub.ut rdN, rdN, rdN` | `sub.ut rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41A00000` | M1 | — | ✅ |
| `sub.st` | `sub.st rdN, rdN, rdN` | `sub.st rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41A40000` | M1 | — | ✅ |
| `cmp.ut` | `cmp.ut rdN, rdN, rdN` | `cmp.ut rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41A80000` | M1 | — | ✅ |
| `cmp.st` | `cmp.st rdN, rdN, rdN` | `cmp.st rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41AC0000` | M1 | — | ✅ |
| `mul.ut` | `mul.ut rdN, rdN, rdN` | `mul.ut rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41C00000` | M1 | — | ✅ |
| `mul.st` | `mul.st rdN, rdN, rdN` | `mul.st rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41C40000` | M1 | — | ✅ |
| `div.ut` | `div.ut rdN, rdN, rdN` | `div.ut rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41E00000` | M1 | — | ✅ |
| `div.st` | `div.st rdN, rdN, rdN` | `div.st rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41E40000` | M1 | — | ✅ |
| `rem.ut` | `rem.ut rdN, rdN, rdN` | `rem.ut rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41E80000` | M1 | — | ✅ |
| `rem.st` | `rem.st rdN, rdN, rdN` | `rem.st rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x41` / `0xFFFC0000` / `0x41EC0000` | M1 | — | ✅ |
| `and.w` | `and.w rdN, rdN, rdN` | `and.w rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42200000` | M1 | — | ✅ |
| `or.w` | `or.w rdN, rdN, rdN` | `or.w rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42240000` | M1 | — | ✅ |
| `xor.w` | `xor.w rdN, rdN, rdN` | `xor.w rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42280000` | M1 | — | ✅ |
| `xnor.w` | `xnor.w rdN, rdN, rdN` | `xnor.w rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x422C0000` | M1 | — | ✅ |
| `ext.uw` | `ext.uw rdN, rdN, rdN` | `ext.uw rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42400000` | M1 | — | ✅ |
| `ext.sw` | `ext.sw rdN, rdN, rdN` | `ext.sw rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42440000` | M1 | — | ✅ |
| `shr.uw` | `shr.uw rdN, rdN, rdN` | `shr.uw rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42480000` | M1 | — | ✅ |
| `shr.sw` | `shr.sw rdN, rdN, rdN` | `shr.sw rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x424C0000` | M1 | — | ✅ |
| `shl.uw` | `shl.uw rdN, rdN, rdN` | `shl.uw rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42500000` | M1 | — | ✅ |
| `add.uw` | `add.uw rdN, rdN, rdN` | `add.uw rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42800000` | M1 | — | ✅ |
| `add.sw` | `add.sw rdN, rdN, rdN` | `add.sw rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42840000` | M1 | — | ✅ |
| `sub.uw` | `sub.uw rdN, rdN, rdN` | `sub.uw rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42A00000` | M1 | — | ✅ |
| `sub.sw` | `sub.sw rdN, rdN, rdN` | `sub.sw rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42A40000` | M1 | — | ✅ |
| `cmp.uw` | `cmp.uw rdN, rdN, rdN` | `cmp.uw rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42A80000` | M1 | — | ✅ |
| `cmp.sw` | `cmp.sw rdN, rdN, rdN` | `cmp.sw rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42AC0000` | M1 | — | ✅ |
| `mul.uw` | `mul.uw rdN, rdN, rdN` | `mul.uw rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42C00000` | M1 | — | ✅ |
| `mul.sw` | `mul.sw rdN, rdN, rdN` | `mul.sw rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42C40000` | M1 | — | ✅ |
| `div.uw` | `div.uw rdN, rdN, rdN` | `div.uw rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42E00000` | M1 | — | ✅ |
| `div.sw` | `div.sw rdN, rdN, rdN` | `div.sw rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42E40000` | M1 | — | ✅ |
| `rem.uw` | `rem.uw rdN, rdN, rdN` | `rem.uw rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42E80000` | M1 | — | ✅ |
| `rem.sw` | `rem.sw rdN, rdN, rdN` | `rem.sw rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x42` / `0xFFFC0000` / `0x42EC0000` | M1 | — | ✅ |
| `and.b` | `and.b rdN, rdN, rdN` | `and.b rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43200000` | M1 | — | ✅ |
| `or.b` | `or.b rdN, rdN, rdN` | `or.b rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43240000` | M1 | — | ✅ |
| `xor.b` | `xor.b rdN, rdN, rdN` | `xor.b rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43280000` | M1 | — | ✅ |
| `xnor.b` | `xnor.b rdN, rdN, rdN` | `xnor.b rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x432C0000` | M1 | — | ✅ |
| `ext.ub` | `ext.ub rdN, rdN, rdN` | `ext.ub rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43400000` | M1 | — | ✅ |
| `ext.sb` | `ext.sb rdN, rdN, rdN` | `ext.sb rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43440000` | M1 | — | ✅ |
| `shr.ub` | `shr.ub rdN, rdN, rdN` | `shr.ub rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43480000` | M1 | — | ✅ |
| `shr.sb` | `shr.sb rdN, rdN, rdN` | `shr.sb rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x434C0000` | M1 | — | ✅ |
| `shl.ub` | `shl.ub rdN, rdN, rdN` | `shl.ub rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43500000` | M1 | — | ✅ |
| `add.ub` | `add.ub rdN, rdN, rdN` | `add.ub rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43800000` | M1 | — | ✅ |
| `add.sb` | `add.sb rdN, rdN, rdN` | `add.sb rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43840000` | M1 | — | ✅ |
| `sub.ub` | `sub.ub rdN, rdN, rdN` | `sub.ub rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43A00000` | M1 | — | ✅ |
| `sub.sb` | `sub.sb rdN, rdN, rdN` | `sub.sb rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43A40000` | M1 | — | ✅ |
| `cmp.ub` | `cmp.ub rdN, rdN, rdN` | `cmp.ub rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43A80000` | M1 | — | ✅ |
| `cmp.sb` | `cmp.sb rdN, rdN, rdN` | `cmp.sb rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43AC0000` | M1 | — | ✅ |
| `mul.ub` | `mul.ub rdN, rdN, rdN` | `mul.ub rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43C00000` | M1 | — | ✅ |
| `mul.sb` | `mul.sb rdN, rdN, rdN` | `mul.sb rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43C40000` | M1 | — | ✅ |
| `div.ub` | `div.ub rdN, rdN, rdN` | `div.ub rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43E00000` | M1 | — | ✅ |
| `div.sb` | `div.sb rdN, rdN, rdN` | `div.sb rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43E40000` | M1 | — | ✅ |
| `rem.ub` | `rem.ub rdN, rdN, rdN` | `rem.ub rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43E80000` | M1 | — | ✅ |
| `rem.sb` | `rem.sb rdN, rdN, rdN` | `rem.sb rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg | — | `0x43` / `0xFFFC0000` / `0x43EC0000` | M1 | — | ✅ |
| `ftadd` | `ftadd rfN, rfN, rfN` | `ftadd rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x44400000` | excluded | — | — (excluded_m1) |
| `ftsub` | `ftsub rfN, rfN, rfN` | `ftsub rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x44440000` | excluded | — | — (excluded_m1) |
| `ftmul` | `ftmul rfN, rfN, rfN` | `ftmul rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x44480000` | excluded | — | — (excluded_m1) |
| `ftdiv` | `ftdiv rfN, rfN, rfN` | `ftdiv rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x444C0000` | excluded | — | — (excluded_m1) |
| `ftrem` | `ftrem rfN, rfN, rfN` | `ftrem rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x44500000` | excluded | — | — (excluded_m1) |
| `ftsclb` | `ftsclb rfN, rfN, rfN` | `ftsclb rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x44540000` | excluded | — | — (excluded_m1) |
| `ftsgnn` | `ftsgnn rfN, rfN, rfN` | `ftsgnn rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x44580000` | excluded | — | — (excluded_m1) |
| `ftsgnj` | `ftsgnj rfN, rfN, rfN` | `ftsgnj rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x445C0000` | excluded | — | — (excluded_m1) |
| `foadd` | `foadd rfN, rfN, rfN` | `foadd rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x44600000` | excluded | — | — (excluded_m1) |
| `fosub` | `fosub rfN, rfN, rfN` | `fosub rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x44640000` | excluded | — | — (excluded_m1) |
| `fomul` | `fomul rfN, rfN, rfN` | `fomul rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x44680000` | excluded | — | — (excluded_m1) |
| `fodiv` | `fodiv rfN, rfN, rfN` | `fodiv rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x446C0000` | excluded | — | — (excluded_m1) |
| `forem` | `forem rfN, rfN, rfN` | `forem rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x44700000` | excluded | — | — (excluded_m1) |
| `fosclb` | `fosclb rfN, rfN, rfN` | `fosclb rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x44740000` | excluded | — | — (excluded_m1) |
| `fosgnn` | `fosgnn rfN, rfN, rfN` | `fosgnn rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x44780000` | excluded | — | — (excluded_m1) |
| `fosgnj` | `fosgnj rfN, rfN, rfN` | `fosgnj rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x447C0000` | excluded | — | — (excluded_m1) |
| `ftqcmp` | `ftqcmp rdN, rfN, rfN` | `ftqcmp rd8, rf2, rf2` | rd:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x44800000` | excluded | — | — (excluded_m1) |
| `ftscmp` | `ftscmp rdN, rfN, rfN` | `ftscmp rd8, rf2, rf2` | rd:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x44840000` | excluded | — | — (excluded_m1) |
| `foqcmp` | `foqcmp rdN, rfN, rfN` | `foqcmp rd8, rf2, rf2` | rd:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x44A00000` | excluded | — | — (excluded_m1) |
| `foscmp` | `foscmp rdN, rfN, rfN` | `foscmp rd8, rf2, rf2` | rd:reg, rf:reg, rf:reg | — | `0x44` / `0xFFFC0000` / `0x44A40000` | excluded | — | — (excluded_m1) |

### `riii`（12 条）

| insn | 汇编形式（模板） | 汇编形式（示例） | 操作数（role/bank） | 立即数范围 | op/mask/value | 范围 | lit | llvm-mc |
|---|---|---|---|---|---|---|---|---|
| `add.si-rd` | `add.si rdN, imms18` | `add.si rd8, 1` | rd:reg, imms18:imm | imms18 s18: -131072..131071 | `0x59` / `0xFF000000` / `0x59000000` | M1 | basic-encoding.s | ✅ |
| `rela.si-rb` | `rela.si rbN, imms18` | `rela.si rb2, 1` | rb:reg, imms18:imm | imms18 s18: -131072..131071 | `0x5A` / `0xFF000000` / `0x5A000000` | M1 | — | ✅ |
| `add.si-rb` | `add.si rbN, imms18` | `add.si rb2, 1` | rb:reg, imms18:imm | imms18 s18: -131072..131071 | `0x5B` / `0xFF000000` / `0x5B000000` | M1 | basic-encoding.s | ✅ |
| `br.n-rd` | `br.n rdN, imms18` | `br.n rd8, 1` | rd:reg, imms18:imm | imms18 s18: -131072..131071 | `0x68` / `0xFF000000` / `0x68000000` | M1 | basic-encoding.s | ✅ |
| `br.nn-rd` | `br.nn rdN, imms18` | `br.nn rd8, 1` | rd:reg, imms18:imm | imms18 s18: -131072..131071 | `0x69` / `0xFF000000` / `0x69000000` | M1 | riii_branch.s | ✅ |
| `br.z-rd` | `br.z rdN, imms18` | `br.z rd8, 1` | rd:reg, imms18:imm | imms18 s18: -131072..131071 | `0x6A` / `0xFF000000` / `0x6A000000` | M1 | riii_branch.s | ✅ |
| `br.nz-rd` | `br.nz rdN, imms18` | `br.nz rd8, 1` | rd:reg, imms18:imm | imms18 s18: -131072..131071 | `0x6B` / `0xFF000000` / `0x6B000000` | M1 | riii_branch.s | ✅ |
| `br.p-rd` | `br.p rdN, imms18` | `br.p rd8, 1` | rd:reg, imms18:imm | imms18 s18: -131072..131071 | `0x6C` / `0xFF000000` / `0x6C000000` | M1 | riii_branch.s | ✅ |
| `br.np-rd` | `br.np rdN, imms18` | `br.np rd8, 1` | rd:reg, imms18:imm | imms18 s18: -131072..131071 | `0x6D` / `0xFF000000` / `0x6D000000` | M1 | riii_branch.s | ✅ |
| `br.z-rb` | `br.z rbN, imms18` | `br.z rb2, 1` | rb:reg, imms18:imm | imms18 s18: -131072..131071 | `0x72` / `0xFF000000` / `0x72000000` | M1 | riii_branch.s | ✅ |
| `br.nz-rb` | `br.nz rbN, imms18` | `br.nz rb2, 1` | rb:reg, imms18:imm | imms18 s18: -131072..131071 | `0x73` / `0xFF000000` / `0x73000000` | M1 | riii_branch.s | ✅ |
| `ret-riii` | `ret rdN, imms18` | `ret rd8, 1` | rd:reg, imms18:imm | imms18 s18: -131072..131071 | `0x76` / `0xFF000000` / `0x76000000` | M1 | riii_ret.s | ✅ |

### `rrii`（25 条）

| insn | 汇编形式（模板） | 汇编形式（示例） | 操作数（role/bank） | 立即数范围 | op/mask/value | 范围 | lit | llvm-mc |
|---|---|---|---|---|---|---|---|---|
| `ld.ub-rd` | `ld.ub rdN, rbN, imms12` | `ld.ub rd8, rb2, 1` | rd:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x10` / `0xFF000000` / `0x10000000` | M1 | rrii_load.s | ✅ |
| `ld.uw-rd` | `ld.uw rdN, rbN, imms12` | `ld.uw rd8, rb2, 1` | rd:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x11` / `0xFF000000` / `0x11000000` | M1 | — | ✅ |
| `ld.ut-rd` | `ld.ut rdN, rbN, imms12` | `ld.ut rd8, rb2, 1` | rd:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x12` / `0xFF000000` / `0x12000000` | M1 | — | ✅ |
| `ld.sb-rd` | `ld.sb rdN, rbN, imms12` | `ld.sb rd8, rb2, 1` | rd:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x13` / `0xFF000000` / `0x13000000` | M1 | rrii_load.s | ✅ |
| `ld.sw-rd` | `ld.sw rdN, rbN, imms12` | `ld.sw rd8, rb2, 1` | rd:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x14` / `0xFF000000` / `0x14000000` | M1 | — | ✅ |
| `ld.st-rd` | `ld.st rdN, rbN, imms12` | `ld.st rd8, rb2, 1` | rd:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x15` / `0xFF000000` / `0x15000000` | M1 | — | ✅ |
| `ld.t-rf` | `ld.t rfN, rbN, imms12` | `ld.t rf2, rb2, 1` | rf:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x16` / `0xFF000000` / `0x16000000` | excluded | — | — (excluded_m1) |
| `st.t-rf` | `st.t rfN, rbN, imms12` | `st.t rf2, rb2, 1` | rf:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x17` / `0xFF000000` / `0x17000000` | excluded | — | — (excluded_m1) |
| `st.b-rd` | `st.b rdN, rbN, imms12` | `st.b rd8, rb2, 1` | rd:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x18` / `0xFF000000` / `0x18000000` | M1 | rrii_store.s | ✅ |
| `st.w-rd` | `st.w rdN, rbN, imms12` | `st.w rd8, rb2, 1` | rd:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x19` / `0xFF000000` / `0x19000000` | M1 | — | ✅ |
| `st.t-rd` | `st.t rdN, rbN, imms12` | `st.t rd8, rb2, 1` | rd:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x1A` / `0xFF000000` / `0x1A000000` | M1 | — | ✅ |
| `ld.o-rd` | `ld.o rdN, rbN, imms12` | `ld.o rd8, rb2, 1` | rd:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x20` / `0xFF000000` / `0x20000000` | M1 | ra.s | ✅ |
| `st.o-rd` | `st.o rdN, rbN, imms12` | `st.o rd8, rb2, 1` | rd:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x21` / `0xFF000000` / `0x21000000` | M1 | ra.s | ✅ |
| `ld.o-rb` | `ld.o rbN, rbN, imms12` | `ld.o rb2, rb2, 1` | rb:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x22` / `0xFF000000` / `0x22000000` | M1 | ra.s | ✅ |
| `st.o-rb` | `st.o rbN, rbN, imms12` | `st.o rb2, rb2, 1` | rb:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x23` / `0xFF000000` / `0x23000000` | M1 | ra.s | ✅ |
| `ld.o-ra` | `ld.o raN, rbN, imms12` | `ld.o ra1, rb2, 1` | ra:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x24` / `0xFF000000` / `0x24000000` | M1 | ra.s | ✅ |
| `st.o-ra` | `st.o raN, rbN, imms12` | `st.o ra1, rb2, 1` | ra:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x25` / `0xFF000000` / `0x25000000` | M1 | ra.s | ✅ |
| `ld.o-rf` | `ld.o rfN, rbN, imms12` | `ld.o rf2, rb2, 1` | rf:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x26` / `0xFF000000` / `0x26000000` | excluded | ra.s | — (excluded_m1) |
| `st.o-rf` | `st.o rfN, rbN, imms12` | `st.o rf2, rb2, 1` | rf:reg, rb:reg, imms12:imm | imms12 s12: -2048..2047 | `0x27` / `0xFF000000` / `0x27000000` | excluded | ra.s | — (excluded_m1) |
| `cmp.ui-rd` | `cmp.ui rdN, rdN, immu12` | `cmp.ui rd8, rd8, 1` | rd:reg, rd:reg, immu12:imm | immu12 u12: 0..4095 | `0x5C` / `0xFF000000` / `0x5C000000` | M1 | rrii_alu.s | ✅ |
| `cmp.si-rd` | `cmp.si rdN, rdN, imms12` | `cmp.si rd8, rd8, 1` | rd:reg, rd:reg, imms12:imm | imms12 s12: -2048..2047 | `0x5D` / `0xFF000000` / `0x5D000000` | M1 | rrii_alu.s | ✅ |
| `br.eq-rd` | `br.eq rdN, rdN, imms12` | `br.eq rd8, rd8, 1` | rd:reg, rd:reg, imms12:imm | imms12 s12: -2048..2047 | `0x6E` / `0xFF000000` / `0x6E000000` | M1 | rrii_branch.s | ✅ |
| `br.ne-rd` | `br.ne rdN, rdN, imms12` | `br.ne rd8, rd8, 1` | rd:reg, rd:reg, imms12:imm | imms12 s12: -2048..2047 | `0x6F` / `0xFF000000` / `0x6F000000` | M1 | — | ✅ |
| `jump-rrii` | `jump rbN, rdN, imms12` | `jump rb2, rd8, 1` | rb:reg, rd:reg, imms12:imm | imms12 s12: -2048..2047 | `0x71` / `0xFF000000` / `0x71000000` | M1 | e_flags.s | ✅ |
| `call-rrii` | `call rbN, rdN, imms12` | `call rb2, rd8, 1` | rb:reg, rd:reg, imms12:imm | imms12 s12: -2048..2047 | `0x75` / `0xFF000000` / `0x75000000` | M1 | iiii_jump.s | ✅ |

### `rrri`（19 条）

| insn | 汇编形式（模板） | 汇编形式（示例） | 操作数（role/bank） | 立即数范围 | op/mask/value | 范围 | lit | llvm-mc |
|---|---|---|---|---|---|---|---|---|
| `ldm.ub-rd` | `ldm.ub rdN, rbN, rdN, immu6` | `ldm.ub rd8, rb2, rd8, 1` | rd:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x28` / `0xFF000000` / `0x28000000` | M1 | rrri.s | ✅ |
| `ldm.uw-rd` | `ldm.uw rdN, rbN, rdN, immu6` | `ldm.uw rd8, rb2, rd8, 1` | rd:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x29` / `0xFF000000` / `0x29000000` | M1 | — | ✅ |
| `ldm.ut-rd` | `ldm.ut rdN, rbN, rdN, immu6` | `ldm.ut rd8, rb2, rd8, 1` | rd:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x2A` / `0xFF000000` / `0x2A000000` | M1 | — | ✅ |
| `ldm.sb-rd` | `ldm.sb rdN, rbN, rdN, immu6` | `ldm.sb rd8, rb2, rd8, 1` | rd:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x2B` / `0xFF000000` / `0x2B000000` | M1 | — | ✅ |
| `ldm.sw-rd` | `ldm.sw rdN, rbN, rdN, immu6` | `ldm.sw rd8, rb2, rd8, 1` | rd:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x2C` / `0xFF000000` / `0x2C000000` | M1 | — | ✅ |
| `ldm.st-rd` | `ldm.st rdN, rbN, rdN, immu6` | `ldm.st rd8, rb2, rd8, 1` | rd:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x2D` / `0xFF000000` / `0x2D000000` | M1 | — | ✅ |
| `ldm.t-rf` | `ldm.t rfN, rbN, rdN, immu6` | `ldm.t rf2, rb2, rd8, 1` | rf:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x2E` / `0xFF000000` / `0x2E000000` | excluded | — | — (excluded_m1) |
| `stm.t-rf` | `stm.t rfN, rbN, rdN, immu6` | `stm.t rf2, rb2, rd8, 1` | rf:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x2F` / `0xFF000000` / `0x2F000000` | excluded | — | — (excluded_m1) |
| `stm.b-rd` | `stm.b rdN, rbN, rdN, immu6` | `stm.b rd8, rb2, rd8, 1` | rd:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x30` / `0xFF000000` / `0x30000000` | M1 | — | ✅ |
| `stm.w-rd` | `stm.w rdN, rbN, rdN, immu6` | `stm.w rd8, rb2, rd8, 1` | rd:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x31` / `0xFF000000` / `0x31000000` | M1 | — | ✅ |
| `stm.t-rd` | `stm.t rdN, rbN, rdN, immu6` | `stm.t rd8, rb2, rd8, 1` | rd:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x32` / `0xFF000000` / `0x32000000` | M1 | — | ✅ |
| `ldm.o-rd` | `ldm.o rdN, rbN, rdN, immu6` | `ldm.o rd8, rb2, rd8, 1` | rd:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x38` / `0xFF000000` / `0x38000000` | M1 | ra.s | ✅ |
| `stm.o-rd` | `stm.o rdN, rbN, rdN, immu6` | `stm.o rd8, rb2, rd8, 1` | rd:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x39` / `0xFF000000` / `0x39000000` | M1 | ra.s | ✅ |
| `ldm.o-rb` | `ldm.o rbN, rbN, rdN, immu6` | `ldm.o rb2, rb2, rd8, 1` | rb:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x3A` / `0xFF000000` / `0x3A000000` | M1 | ra.s | ✅ |
| `stm.o-rb` | `stm.o rbN, rbN, rdN, immu6` | `stm.o rb2, rb2, rd8, 1` | rb:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x3B` / `0xFF000000` / `0x3B000000` | M1 | ra.s | ✅ |
| `ldm.o-ra` | `ldm.o raN, rbN, rdN, immu6` | `ldm.o ra1, rb2, rd8, 1` | ra:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x3C` / `0xFF000000` / `0x3C000000` | M1 | ra.s | ✅ |
| `stm.o-ra` | `stm.o raN, rbN, rdN, immu6` | `stm.o ra1, rb2, rd8, 1` | ra:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x3D` / `0xFF000000` / `0x3D000000` | M1 | ra.s | ✅ |
| `ldm.o-rf` | `ldm.o rfN, rbN, rdN, immu6` | `ldm.o rf2, rb2, rd8, 1` | rf:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x3E` / `0xFF000000` / `0x3E000000` | excluded | ra.s | — (excluded_m1) |
| `stm.o-rf` | `stm.o rfN, rbN, rdN, immu6` | `stm.o rf2, rb2, rd8, 1` | rf:reg, rb:reg, rd:reg, immu6:imm | immu6 u6: 0..63 | `0x3F` / `0xFF000000` / `0x3F000000` | excluded | ra.s | — (excluded_m1) |

### `rrrr`（18 条）

| insn | 汇编形式（模板） | 汇编形式（示例） | 操作数（role/bank） | 立即数范围 | op/mask/value | 范围 | lit | llvm-mc |
|---|---|---|---|---|---|---|---|---|
| `add.uo-rd` | `add.uo rdN, rdN, rdN, rdN` | `add.uo rd8, rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg, rd:reg | — | `0x50` / `0xFF000000` / `0x50000000` | M1 | rrrr.s | ✅ |
| `add.so-rd` | `add.so rdN, rdN, rdN, rdN` | `add.so rd8, rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg, rd:reg | — | `0x51` / `0xFF000000` / `0x51000000` | M1 | rrrr.s | ✅ |
| `sub.uo-rd` | `sub.uo rdN, rdN, rdN, rdN` | `sub.uo rd8, rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg, rd:reg | — | `0x52` / `0xFF000000` / `0x52000000` | M1 | — | ✅ |
| `sub.so-rd` | `sub.so rdN, rdN, rdN, rdN` | `sub.so rd8, rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg, rd:reg | — | `0x53` / `0xFF000000` / `0x53000000` | M1 | — | ✅ |
| `mul.uo-rd` | `mul.uo rdN, rdN, rdN, rdN` | `mul.uo rd8, rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg, rd:reg | — | `0x54` / `0xFF000000` / `0x54000000` | M1 | — | ✅ |
| `mul.so-rd` | `mul.so rdN, rdN, rdN, rdN` | `mul.so rd8, rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg, rd:reg | — | `0x55` / `0xFF000000` / `0x55000000` | M1 | — | ✅ |
| `ftmadd` | `ftmadd rfN, rfN, rfN, rfN` | `ftmadd rf2, rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg, rf:reg | — | `0x56` / `0xFF000000` / `0x56000000` | excluded | — | — (excluded_m1) |
| `fomadd` | `fomadd rfN, rfN, rfN, rfN` | `fomadd rf2, rf2, rf2, rf2` | rf:reg, rf:reg, rf:reg, rf:reg | — | `0x57` / `0xFF000000` / `0x57000000` | excluded | — | — (excluded_m1) |
| `cs.eq-rf` | `cs.eq rdN, rdN, rfN, rfN` | `cs.eq rd8, rd8, rf2, rf2` | rd:reg, rd:reg, rf:reg, rf:reg | — | `0x5E` / `0xFF000000` / `0x5E000000` | excluded | — | — (excluded_m1) |
| `cs.ne-rf` | `cs.ne rdN, rdN, rfN, rfN` | `cs.ne rd8, rd8, rf2, rf2` | rd:reg, rd:reg, rf:reg, rf:reg | — | `0x5F` / `0xFF000000` / `0x5F000000` | excluded | — | — (excluded_m1) |
| `cs.n-rd` | `cs.n rdN, rdN, rdN, rdN` | `cs.n rd8, rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg, rd:reg | — | `0x60` / `0xFF000000` / `0x60000000` | M1 | — | ✅ |
| `cs.n-rf` | `cs.n rdN, rfN, rfN, rfN` | `cs.n rd8, rf2, rf2, rf2` | rd:reg, rf:reg, rf:reg, rf:reg | — | `0x61` / `0xFF000000` / `0x61000000` | excluded | — | — (excluded_m1) |
| `cs.z-rd` | `cs.z rdN, rdN, rdN, rdN` | `cs.z rd8, rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg, rd:reg | — | `0x62` / `0xFF000000` / `0x62000000` | M1 | — | ✅ |
| `cs.z-rf` | `cs.z rdN, rfN, rfN, rfN` | `cs.z rd8, rf2, rf2, rf2` | rd:reg, rf:reg, rf:reg, rf:reg | — | `0x63` / `0xFF000000` / `0x63000000` | excluded | — | — (excluded_m1) |
| `cs.p-rd` | `cs.p rdN, rdN, rdN, rdN` | `cs.p rd8, rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg, rd:reg | — | `0x64` / `0xFF000000` / `0x64000000` | M1 | — | ✅ |
| `cs.p-rf` | `cs.p rdN, rfN, rfN, rfN` | `cs.p rd8, rf2, rf2, rf2` | rd:reg, rf:reg, rf:reg, rf:reg | — | `0x65` / `0xFF000000` / `0x65000000` | excluded | — | — (excluded_m1) |
| `cs.eq-rd` | `cs.eq rdN, rdN, rdN, rdN` | `cs.eq rd8, rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg, rd:reg | — | `0x66` / `0xFF000000` / `0x66000000` | M1 | — | ✅ |
| `cs.ne-rd` | `cs.ne rdN, rdN, rdN, rdN` | `cs.ne rd8, rd8, rd8, rd8` | rd:reg, rd:reg, rd:reg, rd:reg | — | `0x67` / `0xFF000000` / `0x67000000` | M1 | — | ✅ |

### `rwii`（8 条）

| insn | 汇编形式（模板） | 汇编形式（示例） | 操作数（role/bank） | 立即数范围 | op/mask/value | 范围 | lit | llvm-mc |
|---|---|---|---|---|---|---|---|---|
| `or.w-rd` | `or.w rdN, wpN, immu16` | `or.w rd8, 0, 0x1234` | rd:reg, wpN:imm, immu16:imm | wpN 0..3 (wyde position); immu16 u16: 0..65535 | `0x48` / `0xFF000000` / `0x48000000` | M1 | — | ✅ |
| `andn.w-rd` | `andn.w rdN, wpN, immu16` | `andn.w rd8, 0, 0x1234` | rd:reg, wpN:imm, immu16:imm | wpN 0..3 (wyde position); immu16 u16: 0..65535 | `0x49` / `0xFF000000` / `0x49000000` | M1 | — | ✅ |
| `or.w-rb` | `or.w rbN, wpN, immu16` | `or.w rb2, 0, 0x1234` | rb:reg, wpN:imm, immu16:imm | wpN 0..3 (wyde position); immu16 u16: 0..65535 | `0x4A` / `0xFF000000` / `0x4A000000` | M1 | — | ✅ |
| `andn.w-rb` | `andn.w rbN, wpN, immu16` | `andn.w rb2, 0, 0x1234` | rb:reg, wpN:imm, immu16:imm | wpN 0..3 (wyde position); immu16 u16: 0..65535 | `0x4B` / `0xFF000000` / `0x4B000000` | M1 | — | ✅ |
| `set.zw-rd` | `set.zw rdN, wpN, immu16` | `set.zw rd8, 0, 0x1234` | rd:reg, wpN:imm, immu16:imm | wpN 0..3 (wyde position); immu16 u16: 0..65535 | `0x4C` / `0xFF000000` / `0x4C000000` | M1 | rwii.s | ✅ |
| `set.ow-rd` | `set.ow rdN, wpN, immu16` | `set.ow rd8, 0, 0x1234` | rd:reg, wpN:imm, immu16:imm | wpN 0..3 (wyde position); immu16 u16: 0..65535 | `0x4D` / `0xFF000000` / `0x4D000000` | M1 | — | ✅ |
| `set.zw-rb` | `set.zw rbN, wpN, immu16` | `set.zw rb2, 0, 0x1234` | rb:reg, wpN:imm, immu16:imm | wpN 0..3 (wyde position); immu16 u16: 0..65535 | `0x4E` / `0xFF000000` / `0x4E000000` | M1 | rwii.s | ✅ |
| `set.w-rf` | `set.w rfN, wpN, immu16` | `set.w rf2, 0, 0x1234` | rf:reg, wpN:imm, immu16:imm | wpN 0..3 (wyde position); immu16 u16: 0..65535 | `0x4F` / `0xFF000000` / `0x4F000000` | excluded | — | — (excluded_m1) |
