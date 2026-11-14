# Test Vector Inventory


M1 覆盖矩阵。每行唯一对应一个覆盖率主键 `id`
（对应 `contracts/opcodes.yaml` 的 `id`，**唯一**）。
`format` 保留为普通字段，不入主键。

> **本表是 `TESTCASES-002t` 冻结的「覆盖要求矩阵」**：`✓` = 该身份须有该类
> active case；`—` = 该类不适用；`deferred <reason>` = 该类暂缓（须记原因）。
> `file` 列 = **载体** `<册>/<id>.S`（汇编套件；**唯一**载体模型，YAML 载体已全退役）。
> 覆盖判据：`.S` 载体由 L2 `check-inst-asm` **逐镜像执行**（`tools/testcases/inst/
> run_asm_suite.py`，链例比结果字节流、故障例比 monitor 段退出码），`validate_vectors.py`
> 只断言载体存在且结构完好（`<id>.S` 是 `contracts/opcodes.yaml` 的身份、含用例行、
> 检查点号 1..N 连续）；类级覆盖（每类 ≥1 条）由各 `.S` 的 `@@ 用例：` 头与逐点断言承担。
>
> `validate_vectors.py` 机械校验本表的 M1 行集与 `contracts/opcodes.yaml`
> 中 `scope == "m1"` 的身份集一致（无缺、无多、无重复），且每行至少声明一类覆盖（不得静默缺席）；
> 另校验 `file` 列的 basename 在 `tests/inst/<册>/` 现场存在（无悬空引用）。
> **非 id 载体**：`tests/inst/00-isa-design/undi_reserved.S` 承载 3 条保留编码（QFC 空白格 ⇒
> UNDI），文件名不是 opcode id，故不在本矩阵行集内；它在 `check_tests_index.NON_ID_CARRIERS`
> 与 `validate_vectors.NON_ID_CARRIERS` 显式登记（不是目录级豁免）。

## M1 覆盖矩阵（156 条）

| id | format | file | encoding | legality | semantic | boundary | overlap | notes |
|---|---|---|---|---|---|---|---|---|
| `ld.ub_rrii_rd` | `rrii` | `01-load-store/ld.ub_rrii_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ld.uw_rrii_rd` | `rrii` | `01-load-store/ld.uw_rrii_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ld.ut_rrii_rd` | `rrii` | `01-load-store/ld.ut_rrii_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ld.sb_rrii_rd` | `rrii` | `01-load-store/ld.sb_rrii_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ld.sw_rrii_rd` | `rrii` | `01-load-store/ld.sw_rrii_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ld.st_rrii_rd` | `rrii` | `01-load-store/ld.st_rrii_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `st.b_rrii_rd` | `rrii` | `01-load-store/st.b_rrii_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `st.w_rrii_rd` | `rrii` | `01-load-store/st.w_rrii_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `st.t_rrii_rd` | `rrii` | `01-load-store/st.t_rrii_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ld.o_rrii_rd` | `rrii` | `01-load-store/ld.o_rrii_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `st.o_rrii_rd` | `rrii` | `01-load-store/st.o_rrii_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ld.o_rrii_rb` | `rrii` | `01-load-store/ld.o_rrii_rb.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `st.o_rrii_rb` | `rrii` | `01-load-store/st.o_rrii_rb.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ld.o_rrii_ra` | `rrii` | `01-load-store/ld.o_rrii_ra.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `st.o_rrii_ra` | `rrii` | `01-load-store/st.o_rrii_ra.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.ub_rrri_rd` | `rrri` | `01-load-store/ldm.ub_rrri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.uw_rrri_rd` | `rrri` | `01-load-store/ldm.uw_rrri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.ut_rrri_rd` | `rrri` | `01-load-store/ldm.ut_rrri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.sb_rrri_rd` | `rrri` | `01-load-store/ldm.sb_rrri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.sw_rrri_rd` | `rrri` | `01-load-store/ldm.sw_rrri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.st_rrri_rd` | `rrri` | `01-load-store/ldm.st_rrri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `stm.b_rrri_rd` | `rrri` | `01-load-store/stm.b_rrri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `stm.w_rrri_rd` | `rrri` | `01-load-store/stm.w_rrri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `stm.t_rrri_rd` | `rrri` | `01-load-store/stm.t_rrri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.o_rrri_rd` | `rrri` | `01-load-store/ldm.o_rrri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `stm.o_rrri_rd` | `rrri` | `01-load-store/stm.o_rrri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.o_rrri_rb` | `rrri` | `01-load-store/ldm.o_rrri_rb.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `stm.o_rrri_rb` | `rrri` | `01-load-store/stm.o_rrri_rb.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ldm.o_rrri_ra` | `rrri` | `01-load-store/ldm.o_rrri_ra.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `stm.o_rrri_ra` | `rrri` | `01-load-store/stm.o_rrri_ra.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `or.w_rwii_rd` | `rwii` | `03-wyde-imm/or.w_rwii_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `andn.w_rwii_rd` | `rwii` | `03-wyde-imm/andn.w_rwii_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `or.w_rwii_rb` | `rwii` | `03-wyde-imm/or.w_rwii_rb.S` | ✓ | ✓ | ✓ | — | — |  |
| `andn.w_rwii_rb` | `rwii` | `03-wyde-imm/andn.w_rwii_rb.S` | ✓ | ✓ | ✓ | — | — |  |
| `set.zw_rwii_rd` | `rwii` | `03-wyde-imm/set.zw_rwii_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `set.ow_rwii_rd` | `rwii` | `03-wyde-imm/set.ow_rwii_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `set.zw_rwii_rb` | `rwii` | `03-wyde-imm/set.zw_rwii_rb.S` | ✓ | ✓ | ✓ | — | — |  |
| `add.uo_rrrr_rd` | `rrrr` | `04-arith-logic-octa/add.uo_rrrr_rd.S` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `add.so_rrrr_rd` | `rrrr` | `04-arith-logic-octa/add.so_rrrr_rd.S` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `sub.uo_rrrr_rd` | `rrrr` | `04-arith-logic-octa/sub.uo_rrrr_rd.S` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `sub.so_rrrr_rd` | `rrrr` | `04-arith-logic-octa/sub.so_rrrr_rd.S` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `mul.uo_rrrr_rd` | `rrrr` | `04-arith-logic-octa/mul.uo_rrrr_rd.S` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `mul.so_rrrr_rd` | `rrrr` | `04-arith-logic-octa/mul.so_rrrr_rd.S` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `add.si_riii_rd` | `riii` | `04-arith-logic-octa/add.si_riii_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.si_riii_rb` | `riii` | `05-arith-addr/add.si_riii_rb.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `aip.si_riii_rb` | `riii` | `05-arith-addr/aip.si_riii_rb.S` | ✓ | ✓ | ✓ | ✓ | — | IP 相对寻址（ADR-0029 D1 + §修订注记；指令名 `rela.si` → `aip.si`）；手写向量：L1 编码往返（`ha`/`imms18` 正负各 ≥1，SPEC-145t）+ 目的 `rb0` ⇒ ILLI；汇编层操作数按**字节**（`imms30` = `imms18` << 12）；semantic/boundary **QEMU-061t 落地**（执行层：`rbHA = IP + (sext18(imms18) << 12)`，`IP` = 自身地址，期望值 host 侧独立派生） |
| `cmp.ui_rrii_rd` | `rrii` | `04-arith-logic-octa/cmp.ui_rrii_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.si_rrii_rd` | `rrii` | `04-arith-logic-octa/cmp.si_rrii_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `cs.n_rrrr_rd` | `rrrr` | `02-reg-copy/cs.n_rrrr_rd.S` | ✓ | ✓ | ✓ | — | — | overlap ✓（条件↔源别名，spec §2 读后写序确定）；dest↔条件 快照仍 deferred C-27 |
| `cs.z_rrrr_rd` | `rrrr` | `02-reg-copy/cs.z_rrrr_rd.S` | ✓ | ✓ | ✓ | — | — | overlap ✓（条件↔源别名，spec §2 读后写序确定）；dest↔条件 快照仍 deferred C-27 |
| `cs.p_rrrr_rd` | `rrrr` | `02-reg-copy/cs.p_rrrr_rd.S` | ✓ | ✓ | ✓ | — | — | overlap ✓（条件↔源别名，spec §2 读后写序确定）；dest↔条件 快照仍 deferred C-27 |
| `cs.eq_rrrr_rd` | `rrrr` | `02-reg-copy/cs.eq_rrrr_rd.S` | ✓ | ✓ | ✓ | — | — | overlap ✓（条件↔源别名，spec §2 读后写序确定）；dest↔条件 快照仍 deferred C-27 |
| `cs.ne_rrrr_rd` | `rrrr` | `02-reg-copy/cs.ne_rrrr_rd.S` | ✓ | ✓ | ✓ | — | — | overlap ✓（条件↔源别名，spec §2 读后写序确定）；dest↔条件 快照仍 deferred C-27 |
| `br.n_riii_rd` | `riii` | `06-control-flow/br.n_riii_rd.S` | ✓ | — | ✓ | ✓ | — | legality 不适用：br.* 目标恒 4 对齐（无 IALIGN），无 legality 规则适用；boundary 补 UNMAPPED case |
| `br.nn_riii_rd` | `riii` | `06-control-flow/br.nn_riii_rd.S` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.z_riii_rd` | `riii` | `06-control-flow/br.z_riii_rd.S` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.nz_riii_rd` | `riii` | `06-control-flow/br.nz_riii_rd.S` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.p_riii_rd` | `riii` | `06-control-flow/br.p_riii_rd.S` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.np_riii_rd` | `riii` | `06-control-flow/br.np_riii_rd.S` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.eq_rrii_rd` | `rrii` | `06-control-flow/br.eq_rrii_rd.S` | ✓ | — | ✓ | ✓ | — | 同上 |
| `br.ne_rrii_rd` | `rrii` | `06-control-flow/br.ne_rrii_rd.S` | ✓ | — | ✓ | ✓ | — | 同上 |
| `jump_iiii_rb` | `iiii` | `06-control-flow/jump_iiii_rb.S` | ✓ | — | ✓ | ✓ | — | legality 不适用：目标恒 4 对齐（无 IALIGN）、48 位不溢出；boundary 补 UNMAPPED case |
| `jump_rrii_rb` | `rrii` | `06-control-flow/jump_rrii_rb.S` | ✓ | ✓ | ✓ | — | — |  |
| `br.z_riii_rb` | `riii` | `06-control-flow/br.z_riii_rb.S` | ✓ | — | ✓ | ✓ | — | legality 不适用：br.* 目标恒 4 对齐（无 IALIGN），无 legality 规则适用；boundary 补 UNMAPPED case |
| `br.nz_riii_rb` | `riii` | `06-control-flow/br.nz_riii_rb.S` | ✓ | — | ✓ | ✓ | — | 同上 |
| `call_iiii_ra` | `iiii` | `06-control-flow/call_iiii_ra.S` | ✓ | ✓ | ✓ | — | — |  |
| `call_rrii_ra` | `rrii` | `06-control-flow/call_rrii_ra.S` | ✓ | ✓ | ✓ | — | — |  |
| `ret_riii_ra` | `riii` | `06-control-flow/ret_riii_ra.S` | — | ✓ | ✓ | — | — | encoding 豁免：返回目标依赖 harness 布局、单指令不可构造（非恒 fault，见 `TESTCASES-006t`）；semantic 5 条已由 `TESTCASES-063t` 恢复 `active`（harness `build_ret_binary` 用向量自身 RA + 在 `expected_pc` 处放 landing pad；不再合成 call 覆盖 ra63） |
| `swym_oiii_imm` | `oiii` | `12-misc/swym_oiii_imm.S` | ✓ | — | ✓ | — | — | 占位指令（§13.1），无 fault，legality 不适用 |
| `and.o_orrr_rd` | `orrr` | `04-arith-logic-octa/and.o_orrr_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `or.o_orrr_rd` | `orrr` | `04-arith-logic-octa/or.o_orrr_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `xor.o_orrr_rd` | `orrr` | `04-arith-logic-octa/xor.o_orrr_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `xnor.o_orrr_rd` | `orrr` | `04-arith-logic-octa/xnor.o_orrr_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `ext.uo_orrr_rd` | `orrr` | `04-arith-logic-octa/ext.uo_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.so_orrr_rd` | `orrr` | `04-arith-logic-octa/ext.so_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.uo_orrr_rd` | `orrr` | `04-arith-logic-octa/shr.uo_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.so_orrr_rd` | `orrr` | `04-arith-logic-octa/shr.so_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.o_orrr_rd` | `orrr` | `04-arith-logic-octa/shl.o_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.uo_orri_rd` | `orri` | `04-arith-logic-octa/ext.uo_orri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `ext.so_orri_rd` | `orri` | `04-arith-logic-octa/ext.so_orri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.uo_orri_rd` | `orri` | `04-arith-logic-octa/shr.uo_orri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.so_orri_rd` | `orri` | `04-arith-logic-octa/shr.so_orri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.o_orri_rd` | `orri` | `04-arith-logic-octa/shl.o_orri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.o_orrr_bbd` | `orrr` | `05-arith-addr/add.o_orrr_bbd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.o_orrr_bbd` | `orrr` | `05-arith-addr/sub.o_orrr_bbd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `cmp.uo_orrr_dbb` | `orrr` | `05-arith-addr/cmp.uo_orrr_dbb.S` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.uo_orrr_rd` | `orrr` | `04-arith-logic-octa/cmp.uo_orrr_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.so_orrr_rd` | `orrr` | `04-arith-logic-octa/cmp.so_orrr_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `rd2rd_orri_rd` | `orri` | `02-reg-copy/rd2rd_orri_rd.S` | ✓ | ✓ | ✓ | — | ✓ |  |
| `rd2ra_orri_ra` | `orri` | `02-reg-copy/rd2ra_orri_ra.S` | ✓ | ✓ | ✓ | — | ✓ |  |
| `ra2rd_orri_ra` | `orri` | `02-reg-copy/ra2rd_orri_ra.S` | ✓ | ✓ | ✓ | — | ✓ |  |
| `rb2rb_orri_rb` | `orri` | `02-reg-copy/rb2rb_orri_rb.S` | ✓ | ✓ | ✓ | — | ✓ |  |
| `rd2rb_orri_rb` | `orri` | `02-reg-copy/rd2rb_orri_rb.S` | ✓ | ✓ | ✓ | — | ✓ |  |
| `rb2rd_orri_rb` | `orri` | `02-reg-copy/rb2rd_orri_rb.S` | ✓ | ✓ | ✓ | — | ✓ |  |
| `div.uo_orrr_rd` | `orrr` | `04-arith-logic-octa/div.uo_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.so_orrr_rd` | `orrr` | `04-arith-logic-octa/div.so_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.uo_orrr_rd` | `orrr` | `04-arith-logic-octa/rem.uo_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.so_orrr_rd` | `orrr` | `04-arith-logic-octa/rem.so_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.ut_orrr_rd` | `orrr` | `08-arith-logic-tetra/shr.ut_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.st_orrr_rd` | `orrr` | `08-arith-logic-tetra/shr.st_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.t_orrr_rd` | `orrr` | `08-arith-logic-tetra/shl.t_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.ut_orri_rd` | `orri` | `08-arith-logic-tetra/shr.ut_orri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.st_orri_rd` | `orri` | `08-arith-logic-tetra/shr.st_orri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.t_orri_rd` | `orri` | `08-arith-logic-tetra/shl.t_orri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.ut_orrr_rd` | `orrr` | `08-arith-logic-tetra/add.ut_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.st_orrr_rd` | `orrr` | `08-arith-logic-tetra/add.st_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.ut_orrr_rd` | `orrr` | `08-arith-logic-tetra/sub.ut_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.st_orrr_rd` | `orrr` | `08-arith-logic-tetra/sub.st_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `cmp.ut_orrr_rd` | `orrr` | `08-arith-logic-tetra/cmp.ut_orrr_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.st_orrr_rd` | `orrr` | `08-arith-logic-tetra/cmp.st_orrr_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `mul.ut_orrr_rd` | `orrr` | `08-arith-logic-tetra/mul.ut_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `mul.st_orrr_rd` | `orrr` | `08-arith-logic-tetra/mul.st_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.ut_orrr_rd` | `orrr` | `08-arith-logic-tetra/div.ut_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.st_orrr_rd` | `orrr` | `08-arith-logic-tetra/div.st_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.ut_orrr_rd` | `orrr` | `08-arith-logic-tetra/rem.ut_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.st_orrr_rd` | `orrr` | `08-arith-logic-tetra/rem.st_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.uw_orrr_rd` | `orrr` | `09-arith-logic-wyde/shr.uw_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.sw_orrr_rd` | `orrr` | `09-arith-logic-wyde/shr.sw_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.w_orrr_rd` | `orrr` | `09-arith-logic-wyde/shl.w_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.uw_orri_rd` | `orri` | `09-arith-logic-wyde/shr.uw_orri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.sw_orri_rd` | `orri` | `09-arith-logic-wyde/shr.sw_orri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.w_orri_rd` | `orri` | `09-arith-logic-wyde/shl.w_orri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.uw_orrr_rd` | `orrr` | `09-arith-logic-wyde/add.uw_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.sw_orrr_rd` | `orrr` | `09-arith-logic-wyde/add.sw_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.uw_orrr_rd` | `orrr` | `09-arith-logic-wyde/sub.uw_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.sw_orrr_rd` | `orrr` | `09-arith-logic-wyde/sub.sw_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `cmp.uw_orrr_rd` | `orrr` | `09-arith-logic-wyde/cmp.uw_orrr_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.sw_orrr_rd` | `orrr` | `09-arith-logic-wyde/cmp.sw_orrr_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `mul.uw_orrr_rd` | `orrr` | `09-arith-logic-wyde/mul.uw_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `mul.sw_orrr_rd` | `orrr` | `09-arith-logic-wyde/mul.sw_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.uw_orrr_rd` | `orrr` | `09-arith-logic-wyde/div.uw_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.sw_orrr_rd` | `orrr` | `09-arith-logic-wyde/div.sw_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.uw_orrr_rd` | `orrr` | `09-arith-logic-wyde/rem.uw_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.sw_orrr_rd` | `orrr` | `09-arith-logic-wyde/rem.sw_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.ub_orrr_rd` | `orrr` | `10-arith-logic-byte/shr.ub_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.sb_orrr_rd` | `orrr` | `10-arith-logic-byte/shr.sb_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.b_orrr_rd` | `orrr` | `10-arith-logic-byte/shl.b_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.ub_orri_rd` | `orri` | `10-arith-logic-byte/shr.ub_orri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shr.sb_orri_rd` | `orri` | `10-arith-logic-byte/shr.sb_orri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `shl.b_orri_rd` | `orri` | `10-arith-logic-byte/shl.b_orri_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.ub_orrr_rd` | `orrr` | `10-arith-logic-byte/add.ub_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `add.sb_orrr_rd` | `orrr` | `10-arith-logic-byte/add.sb_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.ub_orrr_rd` | `orrr` | `10-arith-logic-byte/sub.ub_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `sub.sb_orrr_rd` | `orrr` | `10-arith-logic-byte/sub.sb_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `cmp.ub_orrr_rd` | `orrr` | `10-arith-logic-byte/cmp.ub_orrr_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `cmp.sb_orrr_rd` | `orrr` | `10-arith-logic-byte/cmp.sb_orrr_rd.S` | ✓ | ✓ | ✓ | — | — |  |
| `mul.ub_orrr_rd` | `orrr` | `10-arith-logic-byte/mul.ub_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `mul.sb_orrr_rd` | `orrr` | `10-arith-logic-byte/mul.sb_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.ub_orrr_rd` | `orrr` | `10-arith-logic-byte/div.ub_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `div.sb_orrr_rd` | `orrr` | `10-arith-logic-byte/div.sb_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.ub_orrr_rd` | `orrr` | `10-arith-logic-byte/rem.ub_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `rem.sb_orrr_rd` | `orrr` | `10-arith-logic-byte/rem.sb_orrr_rd.S` | ✓ | ✓ | ✓ | ✓ | — |  |
| `cfx2rc_crrr_cfx` | `crrr` | — | deferred TESTCASES-033t | deferred TESTCASES-033t | deferred TESTCASES-033t | deferred TESTCASES-033t | deferred TESTCASES-033t | 特权 cfx；SPEC-115t re-scope excluded→m1（已实现，MC 可汇编），向量待 TESTCASES-033t |
| `cfx2rd_crrr_cfx` | `crrr` | — | deferred TESTCASES-033t | deferred TESTCASES-033t | deferred TESTCASES-033t | deferred TESTCASES-033t | deferred TESTCASES-033t | 同上 |
| `escape_ciii_cfx` | `ciii` | `11-cfx/escape_ciii_cfx.S` | deferred TESTCASES-033t | ✓ | deferred TESTCASES-033t | deferred TESTCASES-033t | deferred TESTCASES-033t | 位宽：汇编 `imms20`（合法 0/4）⇔ 编码 `imms18 ∈ {0,1}`；legality = `imms18[17:1]` SBZ 非零 ⇒ ILLI（SPEC-180t）；合法偏移的执行期覆盖见 `min_rom_probe_integ044t.py` escape_return 与 `tests/arch/umon/m5_trap_escape.s` |
| `trap_ciii_cfx` | `ciii` | — | deferred TESTCASES-033t | deferred TESTCASES-033t | deferred TESTCASES-033t | deferred TESTCASES-033t | deferred TESTCASES-033t | 同上 |

> 保留 cfxha（6–14、16–31、35–61）的普通 `ld/st` ⇒ `CFXMEM` 的覆盖位于 4 个访存 id 的 `.S` 故障例（`ld.ub_rrii_rd`/`ld.o_rrii_rd`/`st.b_rrii_rd`/`st.o_rrii_rd`，原 `base/reserved.yaml` 的 6 条 legality 例，已随 YAML 退役迁入；`check-inst-asm` 执行），不改变本矩阵行集与门控载体集。

## 非 M1 向量（独立文件，不入本矩阵）

`rev.o`/`rev.t`/`rev.w`/`rev.b`（逐块反转）为 `scope: m8`（`ADR-0012 D10`），**不是 M1 身份**，
故**不**在本文 M1 覆盖矩阵中登记（矩阵的 id 行集须与 `contracts/opcodes.yaml` 的 `scope == "m1"`
身份集**严格一致**——多一行即 `validate_vectors.py` 报 `INVENTORY EXTRA`，缺一行报
`INVENTORY MISSING`）。

它们的载体是 `tests/inst/<册>/<id>.S`（`.S` 唯一载体模型；`rev` 的 4 个 id 在
`04-arith-logic-octa/` 等册内，按 id 文件名现场派生）。覆盖范围：

| 指令 | 载体 | 覆盖 |
|------|------|------|
| `rev.o` | `tests/inst/<册>/rev.o_orri_rd.S` | encoding + 每个合法 `k`（1/2/4/8/16/32）的 semantic + 边界（`rdHC=0`/全 1/`rdHB==rdHC`/`rdHC=rd0`）+ legality（非 one-hot / `k≥S` / 目的 `rd0`） |
| `rev.t` | `tests/inst/<册>/rev.t_orri_rd.S` | 同上（合法 `k` = 1/2/4/8/16） |
| `rev.w` | `tests/inst/<册>/rev.w_orri_rd.S` | 同上（合法 `k` = 1/2/4/8） |
| `rev.b` | `tests/inst/<册>/rev.b_orri_rd.S` | 同上（合法 `k` = 1/2/4） |

> 端序：本项目为**大端**；`k = 8` 档的语义用例同时由「块内单元倒序」与「大端字节序 →
> 块内字节倒序」两条独立派生路径给出，逐例一致；期望值内联在 `.S`，由 `check-inst-asm` 执行。

`ctlz`/`cttz`/`ctpop`（位扫描 / 位计数）同为 `scope: m8`（`ADR-0012 D11`），**不是 M1 身份**（同上，
不入本矩阵）。载体是 `tests/inst/<册>/<id>.S`（每 id ≤127 例，由 `check-tests-index` 的
`CASE_LIMIT` 门控；点号 1..N 连续）：

| 指令 | 载体 | 覆盖 |
|------|------|------|
| `ctlz` | `tests/inst/<册>/ctlz_orri_rd.S` | encoding + `hd` 抽样（非特殊值 + 边界，`hd ∈ 0..63` 全合法）+ 定值（有效位全 0 ⇒ `hd+1`）+ 边界（`hd=0`/`hd=63`/`rdHC=rd0`/`rdHB==rdHC`/高位掩码/单 bit 位编号）+ legality（仅目的 `rd0` ⇒ ILLI） |
| `cttz` | `tests/inst/<册>/cttz_orri_rd.S` | 同上（定值同 `hd+1`） |
| `ctpop` | `tests/inst/<册>/ctpop_orri_rd.S` | 同上（定值 = 0） |

> 语义口径：`hd` = **有效位上界**，参与运算的是 `rdHC[hd:0]`（`hd+1` 位）；`hd ∈ 0..63`
> **全部合法**（**无** `hd` 触发 ILLI）。期望值内联在 `.S`（独立派生，不从实现反推），
> 由 `check-inst-asm` 逐镜像执行。


## `.S` 载体覆盖（L2 `check-inst-asm`）

`tests/inst/<册>/*.S` 是**执行型**载体：每个 `<id>.S` 一个 ELF，`run_asm_suite.py` 对链例
（`CASE_N=0`）比**结果字节流**（`8 × 检查点数`，逐字节）、对故障例（`-defsym CASE_N=<点号>`）
比 monitor 段退出码 `0xF0|异常位索引`。`make check-inst-asm`（L2，单平台 QEMU
`dadao-tiny`）跑本表全部册；chipyard / gem5 的三方逐字节是各册任务的验收口径（不在 L2）。

本表是**读者面登记**，`make check-inst-asm` 的载体集 = `tests/inst/` 下**含 `.S` 的子
目录**（现场派生，`run_asm_suite.py --books-root tests/inst`），册名/册数不写死。

### 覆盖边界（如实）

- **拦得住**：现存每个 `<id>.S` 的结构 —— stem 必须是 `contracts/opcodes.yaml` 的身份、
  含 ≥1 用例行、检查点号 1..N 连续（`validate_vectors.py` 的 `ASM CARRIER *` 断言），
  且 L2 `check-inst-asm` 会把**现存**载体逐镜像真跑（链例字节流 + 故障例退出码）。
  删单个 `.S` 但保留 `tests/inst.yaml` 条目 ⇒ `check-tests-index` 红（`file` 不存在）。
- **拦得住（逐条删除哨兵）**：`check-case-ledger` 自本任务起派生**`.S` 载体逐用例身份**
  （`asm` 行 = 载体路径 + 用例行文本 + 同内容序号，无行号）⇒ 删任一用例行 ⇒ 少一行 ⇒ 红；
  整册删除时须同时删 `tests/inst.yaml` 条目并 `--write` 重生成台账（两处都留下痕迹）。
- **拦不住（现状，如实）**：`validate-vectors`/`check-tests-index` 仍按「现存载体」判，
  单删 `.S` 且同步删索引条目时二者只看现场、不看历史（由台账行数变化暴露）；
  「载体册集 == 注册册集」尚未做双向断言（`ISS-441` 余项，另立任务）。

| 册 | 载体 | 门控 | 判据 |
|---|---|---|---|
| `01-load-store/` | `ld.*`/`st.*`/`ldm.*`/`stm.*` | `check-inst-asm` | 链例字节流 + 故障例退出码 |
| `02-reg-copy/` | 块复制 + `cs.*` | `check-inst-asm` | 链例字节流 + 故障例退出码 |
| `03-wyde-imm/` | 16 位立即数操作 | `check-inst-asm` | 链例字节流 + 故障例退出码 |
| `04-arith-logic-octa/` | 64 位数据运算 | `check-inst-asm` | 链例字节流 + 故障例退出码 |
| `05-arith-addr/` | 64 位地址运算 | `check-inst-asm` | 链例字节流 + 故障例退出码 |
| `06-control-flow/` | 控制流 | `check-inst-asm` | 链例字节流 + 故障例退出码 |
| `07-floating-point/` | 浮点运算 | `check-inst-asm` | 链例字节流 + 故障例退出码 |
| `08-arith-logic-tetra/` | 32 位数据运算 | `check-inst-asm` | 链例字节流 + 故障例退出码 |
| `09-arith-logic-wyde/` | 16 位数据运算 | `check-inst-asm` | 链例字节流 + 故障例退出码 |
| `10-arith-logic-byte/` | 8 位数据运算 | `check-inst-asm` | 链例字节流 + 故障例退出码 |
| `11-cfx/` | 核芯功能扩展 | `check-inst-asm` | 链例字节流 + 故障例退出码 |
| `12-misc/` | `swym`/`ct*`/`lr`/`sc` | `check-inst-asm` | 链例字节流 + 故障例退出码 |

## 门控覆盖（L2/L3）

> **YAML 全退役（`m13-testcases-043`）后本表作废**：原表登记的是 YAML 载体册与
> `check-inst`/`check-inst-smoke` 的载体集，两者均已退役。现行口径：
>
> - **L2** = `make check-inst-asm`：`tests/inst/` 下**全部含 `.S` 的子目录**（现场派生），
>   单平台 QEMU `dadao-tiny`，链例比结果字节流、故障例比 monitor 段退出码；
> - **L3 不再有 inst 全量执行**：Vast 的 ISA 级执行覆盖**明确放弃**（用户 2026-11-14 裁定），
>   其 ISA 语义由 `spec/` + M13 三平台差分矩阵承担（inst 行 = `.S` 的
>   `run_asm_suite.py --platforms chipyard,qemu,gem5`，Tiny）；`check-inst`/`check-inst-smoke`
>   两个目标已删除（`docs/Process-07`）。
> - 各册见上「`.S` 载体覆盖（L2 `check-inst-asm`）」表；`00-isa-design` 是非 id 载体册。
