# Test Vector Inventory

M1 覆盖矩阵。每行唯一对应一个覆盖率主键 `(insn, format)`
（等价机器键 `(op, ha)`，`op = value>>24`、`ha = (value>>18)&0x3f`）。

> **本表是 `TESTCASES-002t` 冻结的「覆盖要求矩阵」**：`✓` = 该身份须有该类
> active case；`—` = 该类不适用；`deferred <reason>` = 该类暂缓（须记原因）。
> 向量数据（`tests/vectors/isa/*.yaml`）由 `TESTCASES-003t`~`007t` 生成；
> `file` 列为目标文件名，下游重组任务负责更新为最终文件名。
>
> `validate_vectors.py` 机械校验本表的 M1 行集与 `contracts/opcodes.yaml`
> 的 M1 身份集一致（无缺、无多、无重复），且每行至少声明一类覆盖（不得静默缺席）。

## M1 覆盖矩阵（178 条）

| insn | format | file | encoding | legality | semantic | boundary | overlap | notes |
|---|---|---|---|---|---|---|---|---|
| `illi` | `oiii` | `misc.yaml` | — | ✓ | — | — | — | 恒 ILLI（§9.1）；encoding/semantic 豁免（F6），覆盖率由 legality 满足 |
| `fence` | `oiii` | `misc.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `ld.ub-rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `ld.uw-rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `ld.ut-rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `ld.sb-rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `ld.sw-rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `ld.st-rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `st.b-rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `st.w-rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `st.t-rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `ld.o-rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `st.o-rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `ld.o-rb` | `rrii` | `mem-rb.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `st.o-rb` | `rrii` | `mem-rb.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `ld.o-ra` | `rrii` | `mem-ra.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `st.o-ra` | `rrii` | `mem-ra.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `ldm.ub-rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `ldm.uw-rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `ldm.ut-rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `ldm.sb-rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `ldm.sw-rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `ldm.st-rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `stm.b-rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `stm.w-rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `stm.t-rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `ldm.o-rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `stm.o-rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `ldm.o-rb` | `rrri` | `mem-rb.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `stm.o-rb` | `rrri` | `mem-rb.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `ldm.o-ra` | `rrri` | `mem-ra.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `stm.o-ra` | `rrri` | `mem-ra.yaml` | ✓ | ✓ | ✓ |  ✓  | — |  |
| `and.o` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `or.o` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `xor.o` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `xnor.o` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `ext.uo` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.so` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.uo` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.so` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.uo` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.uo` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.so` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.uo` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.so` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.uo` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.so-rb` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.so-rb` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `cmp.uo-rb` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.uo` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.so` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `rd2rd` | `orri` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | ✓ |  |
| `rd2ra` | `orri` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | ✓ |  |
| `ra2rd` | `orri` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | ✓ |  |
| `rb2rb` | `orri` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | ✓ |  |
| `rd2rb` | `orri` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | ✓ |  |
| `rb2rd` | `orri` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | ✓ |  |
| `div.uo` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.so` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.uo` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.so` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `and.t` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `or.t` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `xor.t` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `xnor.t` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `ext.ut` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.st` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.ut` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.st` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.ut` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.ut` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.st` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.ut` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.st` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.ut` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.ut` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.st` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.ut` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.st` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `cmp.ut` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.st` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `mul.ut` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `mul.st` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.ut` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.st` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.ut` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.st` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `and.w` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `or.w` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `xor.w` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `xnor.w` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `ext.uw` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.sw` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.uw` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.sw` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.uw` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.uw` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.sw` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.uw` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.sw` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.uw` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.uw` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.sw` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.uw` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.sw` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `cmp.uw` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.sw` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `mul.uw` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `mul.sw` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.uw` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.sw` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.uw` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.sw` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `and.b` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `or.b` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `xor.b` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `xnor.b` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `ext.ub` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.sb` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.ub` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.sb` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.ub` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.ub` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.sb` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.ub` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.sb` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.ub` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.ub` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.sb` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.ub` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.sb` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `cmp.ub` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.sb` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `mul.ub` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `mul.sb` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.ub` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.sb` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.ub` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.sb` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `or.w-rd` | `rwii` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `andn.w-rd` | `rwii` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `or.w-rb` | `rwii` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `andn.w-rb` | `rwii` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `set.zw-rd` | `rwii` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `set.ow-rd` | `rwii` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `set.zw-rb` | `rwii` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `add.uo-rd` | `rrrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `add.so-rd` | `rrrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `sub.uo-rd` | `rrrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `sub.so-rd` | `rrrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `mul.uo-rd` | `rrrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `mul.so-rd` | `rrrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `add.si-rd` | `riii` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rela.si-rb` | `riii` | `reg-arith.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `add.si-rb` | `riii` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `cmp.ui-rd` | `rrii` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.si-rd` | `rrii` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `cs.n-rd` | `rrrr` | `reg-cond-assign.yaml` | ✓ | ✓ | ✓ | — | deferred C-27 | overlap（C-27 条件赋值快照）deferred |
| `cs.z-rd` | `rrrr` | `reg-cond-assign.yaml` | ✓ | ✓ | ✓ | — | deferred C-27 | overlap（C-27 条件赋值快照）deferred |
| `cs.p-rd` | `rrrr` | `reg-cond-assign.yaml` | ✓ | ✓ | ✓ | — | deferred C-27 | overlap（C-27 条件赋值快照）deferred |
| `cs.eq-rd` | `rrrr` | `reg-cond-assign.yaml` | ✓ | ✓ | ✓ | — | deferred C-27 | overlap（C-27 条件赋值快照）deferred |
| `cs.ne-rd` | `rrrr` | `reg-cond-assign.yaml` | ✓ | ✓ | ✓ | — | deferred C-27 | overlap（C-27 条件赋值快照）deferred |
| `br.n-rd` | `riii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | legality 不适用：br.* 目标恒 4 对齐（无 IALIGN），无 legality 规则适用；boundary 补 UNMAPPED case |
| `br.nn-rd` | `riii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.z-rd` | `riii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.nz-rd` | `riii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.p-rd` | `riii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.np-rd` | `riii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.eq-rd` | `rrii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.ne-rd` | `rrii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | 同上 |
| `jump-iiii` | `iiii` | `ctrl-jump.yaml` | ✓ | — | ✓ | ✓ | — | legality 不适用：目标恒 4 对齐（无 IALIGN）、48 位不溢出；boundary 补 UNMAPPED case |
| `jump-rrii` | `rrii` | `ctrl-jump.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `br.z-rb` | `riii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | legality 不适用：br.* 目标恒 4 对齐（无 IALIGN），无 legality 规则适用；boundary 补 UNMAPPED case |
| `br.nz-rb` | `riii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | 同上 |
| `call-iiii` | `iiii` | `ctrl-call.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `call-rrii` | `rrii` | `ctrl-call.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `ret-riii` | `riii` | `ctrl-ret.yaml` | — | ✓ | ✓ | — | — | encoding 豁免：返回目标依赖 harness 布局、单指令不可构造（非恒 fault，见 `TESTCASES-006t`） |
| `swym-iiii` | `iiii` | `misc.yaml` | ✓ | — | ✓ | — | — | 占位指令（§7），无 fault，legality 不适用 |

## 覆盖豁免与例外

- `illi`（`oiii`，恒 ILLI，`contract-isa.md` §8.2/§9.1）：`encoding` 与
  `semantic` 均不可构造（恒 fault），覆盖率由 `legality` active 满足——见
  `schema.md` 的 encoding 类豁免条款（F6）。
- **保留编码 → UNDI**（`encoding.reserved: true`）：QFC 主表 / MISC 子表
  空白单元格**无** `(insn, format)` 身份（`contracts/opcodes.yaml` 只含已定义
  编码），故**不参与** `(insn, format)` 覆盖率门控。`UNDI` 覆盖由
  `tests/vectors/isa/reserved.yaml` 中 `class: legality` +
  `encoding.reserved: true` 的 active case 满足，由 `inventory.md` 显式登记。
  详见 `schema.md`「保留编码 case」与 `TESTCASES-008t`。
- `ret-riii`：无 `encoding` case，但**理由不同**（返回目标依赖 harness 布局、
  单指令不可构造），**非**恒 fault；处置见 `TESTCASES-006t`。
- `cs.*`（条件赋值快照，C-27）：`overlap` 类显式 `deferred`，不得静默缺席。
- M1 scope 判据：`contracts/opcodes.yaml` 的 `excluded_m1 != true`；
  其余 78 条（浮点 RF / 特权 cfx / LR-SC）不在本表。

## 目标文件分布

| file | 身份数 |
|---|---|
| `ctrl-br.yaml` | 10 |
| `ctrl-call.yaml` | 2 |
| `ctrl-jump.yaml` | 2 |
| `ctrl-ret.yaml` | 1 |
| `mem-ra.yaml` | 4 |
| `mem-rb.yaml` | 4 |
| `mem-rd.yaml` | 22 |
| `misc.yaml` | 3 |
| `reg-arith.yaml` | 45 |
| `reg-compare.yaml` | 11 |
| `reg-cond-assign.yaml` | 5 |
| `reg-imm-block.yaml` | 13 |
| `reg-logic.yaml` | 16 |
| `reg-shift-extend.yaml` | 40 |
| `reserved.yaml` | 0 |

