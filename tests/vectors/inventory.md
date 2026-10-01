# Test Vector Inventory


M1 覆盖矩阵。每行唯一对应一个覆盖率主键 `id`
（对应 `contracts/opcodes.yaml` 的 `id`，**唯一**）。
`format` 保留为普通字段，不入主键。

> **本表是 `TESTCASES-002t` 冻结的「覆盖要求矩阵」**：`✓` = 该身份须有该类
> active case；`—` = 该类不适用；`deferred <reason>` = 该类暂缓（须记原因）。
> 向量数据（`tests/vectors/isa/*.yaml`）由 `TESTCASES-003t`~`007t` 生成；
> `file` 列为目标文件名，下游重组任务负责更新为最终文件名。
>
> `validate_vectors.py` 机械校验本表的 M1 行集与 `contracts/opcodes.yaml`
> 的 M1 身份集一致（无缺、无多、无重复），且每行至少声明一类覆盖（不得静默缺席）。

## M1 覆盖矩阵（152 条）

| id | format | file | encoding | legality | semantic | boundary | overlap | notes |
|---|---|---|---|---|---|---|---|---|
| `ld.ub_rrii_rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ld.uw_rrii_rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ld.ut_rrii_rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ld.sb_rrii_rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ld.sw_rrii_rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ld.st_rrii_rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `st.b_rrii_rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `st.w_rrii_rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `st.t_rrii_rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ld.o_rrii_rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `st.o_rrii_rd` | `rrii` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ld.o_rrii_rb` | `rrii` | `mem-rb.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `st.o_rrii_rb` | `rrii` | `mem-rb.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ld.o_rrii_ra` | `rrii` | `mem-ra.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `st.o_rrii_ra` | `rrii` | `mem-ra.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.ub_rrri_rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.uw_rrri_rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.ut_rrri_rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.sb_rrri_rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.sw_rrri_rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.st_rrri_rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `stm.b_rrri_rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `stm.w_rrri_rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `stm.t_rrri_rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.o_rrri_rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `stm.o_rrri_rd` | `rrri` | `mem-rd.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.o_rrri_rb` | `rrri` | `mem-rb.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `stm.o_rrri_rb` | `rrri` | `mem-rb.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.o_rrri_ra` | `rrri` | `mem-ra.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `stm.o_rrri_ra` | `rrri` | `mem-ra.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `or.w_rwii_rd` | `rwii` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `andn.w_rwii_rd` | `rwii` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `or.w_rwii_rb` | `rwii` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `andn.w_rwii_rb` | `rwii` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `set.zw_rwii_rd` | `rwii` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `set.ow_rwii_rd` | `rwii` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `set.zw_rwii_rb` | `rwii` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `add.uo_rrrr_rd` | `rrrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `add.so_rrrr_rd` | `rrrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `sub.uo_rrrr_rd` | `rrrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `sub.so_rrrr_rd` | `rrrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `mul.uo_rrrr_rd` | `rrrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `mul.so_rrrr_rd` | `rrrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `add.si_riii_rd` | `riii` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.si_riii_rb` | `riii` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `cmp.ui_rrii_rd` | `rrii` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.si_rrii_rd` | `rrii` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `cs.n_rrrr_rd` | `rrrr` | `reg-cond-assign.yaml` | ✓ | ✓ | ✓ | — | deferred C-27 | overlap（C-27 条件赋值快照）deferred |
| `cs.z_rrrr_rd` | `rrrr` | `reg-cond-assign.yaml` | ✓ | ✓ | ✓ | — | deferred C-27 | overlap（C-27 条件赋值快照）deferred |
| `cs.p_rrrr_rd` | `rrrr` | `reg-cond-assign.yaml` | ✓ | ✓ | ✓ | — | deferred C-27 | overlap（C-27 条件赋值快照）deferred |
| `cs.eq_rrrr_rd` | `rrrr` | `reg-cond-assign.yaml` | ✓ | ✓ | ✓ | — | deferred C-27 | overlap（C-27 条件赋值快照）deferred |
| `cs.ne_rrrr_rd` | `rrrr` | `reg-cond-assign.yaml` | ✓ | ✓ | ✓ | — | deferred C-27 | overlap（C-27 条件赋值快照）deferred |
| `br.n_riii_rd` | `riii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | legality 不适用：br.* 目标恒 4 对齐（无 IALIGN），无 legality 规则适用；boundary 补 UNMAPPED case |
| `br.nn_riii_rd` | `riii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.z_riii_rd` | `riii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.nz_riii_rd` | `riii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.p_riii_rd` | `riii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.np_riii_rd` | `riii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.eq_rrii_rd` | `rrii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.ne_rrii_rd` | `rrii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | 同上 |
| `jump_iiii_rb` | `iiii` | `ctrl-jump.yaml` | ✓ | — | ✓ | ✓ | — | legality 不适用：目标恒 4 对齐（无 IALIGN）、48 位不溢出；boundary 补 UNMAPPED case |
| `jump_rrii_rb` | `rrii` | `ctrl-jump.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `br.z_riii_rb` | `riii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | legality 不适用：br.* 目标恒 4 对齐（无 IALIGN），无 legality 规则适用；boundary 补 UNMAPPED case |
| `br.nz_riii_rb` | `riii` | `ctrl-br.yaml` | ✓ | — | ✓ | ✓ | — | 同上 |
| `call_iiii_ra` | `iiii` | `ctrl-call.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `call_rrii_ra` | `rrii` | `ctrl-call.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `ret_riii_ra` | `riii` | `ctrl-ret.yaml` | — | ✓ | ✓ | — | — | encoding 豁免：返回目标依赖 harness 布局、单指令不可构造（非恒 fault，见 `TESTCASES-006t`） |
| `swym_oiii_imm` | `oiii` | `misc.yaml` | ✓ | — | ✓ | — | — | 占位指令（§7），无 fault，legality 不适用 |
| `illi_oiii_imm` | `oiii` | `misc.yaml` | — | ✓ | — | — | — | 恒 ILLI（§9.1）；encoding/semantic 豁免（F6），覆盖率由 legality 满足 |
| `and.o_orrr_rd` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `or.o_orrr_rd` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `xor.o_orrr_rd` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `xnor.o_orrr_rd` | `orrr` | `reg-logic.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `ext.uo_orrr_rd` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.so_orrr_rd` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.uo_orrr_rd` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.so_orrr_rd` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.uo_orrr_rd` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.uo_orri_rd` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.so_orri_rd` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.uo_orri_rd` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.so_orri_rd` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.uo_orri_rd` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.so_orrr_rb` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.so_orrr_rb` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `cmp.uo_orrr_rb` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.uo_orrr_rd` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.so_orrr_rd` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `rd2rd_orri_rd` | `orri` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | ✓ |  |
| `rd2ra_orri_ra` | `orri` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | ✓ |  |
| `ra2rd_orri_ra` | `orri` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | ✓ |  |
| `rb2rb_orri_rb` | `orri` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | ✓ |  |
| `rd2rb_orri_rb` | `orri` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | ✓ |  |
| `rb2rd_orri_rb` | `orri` | `reg-imm-block.yaml` | ✓ | ✓ | ✓ | — | ✓ |  |
| `div.uo_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.so_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.uo_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.so_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.ut_orrr_rd` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.st_orrr_rd` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.ut_orrr_rd` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.ut_orri_rd` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.st_orri_rd` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.ut_orri_rd` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.ut_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.st_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.ut_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.st_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `cmp.ut_orrr_rd` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.st_orrr_rd` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `mul.ut_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `mul.st_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.ut_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.st_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.ut_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.st_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.uw_orrr_rd` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.sw_orrr_rd` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.uw_orrr_rd` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.uw_orri_rd` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.sw_orri_rd` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.uw_orri_rd` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.uw_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.sw_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.uw_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.sw_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `cmp.uw_orrr_rd` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.sw_orrr_rd` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `mul.uw_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `mul.sw_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.uw_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.sw_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.uw_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.sw_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.ub_orrr_rd` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.sb_orrr_rd` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.ub_orrr_rd` | `orrr` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.ub_orri_rd` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.sb_orri_rd` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.ub_orri_rd` | `orri` | `reg-shift-extend.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.ub_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.sb_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.ub_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.sb_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `cmp.ub_orrr_rd` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.sb_orrr_rd` | `orrr` | `reg-compare.yaml` | ✓ | ✓ | ✓ | — | — |  |
| `mul.ub_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `mul.sb_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.ub_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.sb_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.ub_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.sb_orrr_rd` | `orrr` | `reg-arith.yaml` | ✓ | ✓ | ✓ | ✓ | — |  |
