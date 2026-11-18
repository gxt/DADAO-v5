# m13-integ-003: 整数与访存三平台逐例差分（qemu / gem5 / chipyard）

> 由 `tools/testcases/parity/int_diff.py` 从已入库输入确定性重建；不写生成时刻、不写运行期路径。

## 0. 口径与分母（现场统计）

- `tests/inst` 的 `.S` 载体**总数 265**（现场枚举，不写死）
- 排除 FP：**66** 条 `scope: fp` 载体（`contracts/opcodes.yaml`；其中 52 条在 `07-floating-point`，其余散落在 01/02/03 册）——归 `m13-integ-002`
- 排除 cfx：**5** 条（册 `11-cfx`）——归 CFX 专项
- 非 id 载体：**1** 条：`undi_reserved`（保留编码 ⇒ UNDI；以自身文件头的 spec 出处计）
- 本报告分母：**194** 个载体（其中 193 个有 opcode id）/ **629** 个镜像（链例 193，故障例 436）
- 三平台完成数：分母 629；qemu 629 / gem5 629 / chipyard 629；缺失 qemu=0, gem5=0, chipyard=0

## 1. 语义依据出处（每族：spec 章节 + contract）

族 = `.S` 载体所在册；册号直接对应 `spec/SimRISC-NN-*` 章节号；逐 id 的 `spec_cite`（`contracts/opcodes.yaml`）解析到该章节，并在章内核对助记符。人读契约正文统一指 `.tao/contracts/contract-isa.md`（FP 段归 `contract-fp.md`，不在范围）。

| 族（册） | spec 章节 | id 数 | 载体 | 链例点 | 故障例 | 镜像 | spec_cite 可解析 | 缺口 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `00-isa-design` | `spec/SimRISC-00-指令系统设计.md` | 0 | 1 | 0 | 3 | 3 | 1 | 0 |
| `01-load-store` | `spec/SimRISC-01-取数存数.md` | 30 | 30 | 433 | 159 | 189 | 30 | 0 |
| `02-reg-copy` | `spec/SimRISC-02-寄存器复制.md` | 11 | 11 | 141 | 32 | 43 | 11 | 0 |
| `03-wyde-imm` | `spec/SimRISC-03-16位立即数操作.md` | 7 | 7 | 98 | 7 | 14 | 7 | 0 |
| `04-arith-logic-octa` | `spec/SimRISC-04-64位数据运算.md` | 33 | 33 | 472 | 43 | 76 | 33 | 0 |
| `05-arith-addr` | `spec/SimRISC-05-64位地址运算.md` | 6 | 6 | 75 | 6 | 12 | 6 | 0 |
| `06-control-flow` | `spec/SimRISC-06-控制流.md` | 15 | 15 | 184 | 20 | 35 | 15 | 0 |
| `08-arith-logic-tetra` | `spec/SimRISC-08-32位数据运算.md` | 21 | 21 | 362 | 34 | 55 | 21 | 0 |
| `09-arith-logic-wyde` | `spec/SimRISC-09-16位数据运算.md` | 21 | 21 | 335 | 56 | 77 | 21 | 0 |
| `10-arith-logic-byte` | `spec/SimRISC-10-8位数据运算.md` | 21 | 21 | 293 | 31 | 52 | 21 | 0 |
| `12-misc` | `spec/SimRISC-12-其它指令.md` | 28 | 28 | 475 | 45 | 73 | 28 | 0 |

### 语义出处缺口（0）

(none) — 每条载体的 `spec_cite` 都能解析到现存章节且章内有该助记符；非 id 载体取自身文件头出处。

## 2. 三平台逐例结果

- 镜像 **629**；三方一致通过 **629**；三方一致非通过 **0**；平台差异 **0**。

| id | 链例/故障 | 观测 | 归因 |
| --- | --- | --- | --- |
| — | — | 无平台差异 | — |

### 逐 id 聚合（链例/故障镜像数、三方一致通过数）

| id | 族 | 语义出处 | 镜像 | 链例 | 故障 | 一致通过 |
| --- | --- | --- | --- | --- | --- | --- |
| `add.o_orrr_bbd` | arith-addr | `SimRISC-05: add.o` | 2 | 1 | 1 | 2 |
| `add.sb_orrr_rd` | arith-logic-byte | `SimRISC-10: add.sb` | 2 | 1 | 1 | 2 |
| `add.si_riii_rb` | arith-addr | `SimRISC-05: add.si` | 2 | 1 | 1 | 2 |
| `add.si_riii_rd` | arith-logic-octa | `SimRISC-04: add.si` | 2 | 1 | 1 | 2 |
| `add.so_rrrr_rd` | arith-logic-octa | `SimRISC-04: add.so` | 3 | 1 | 2 | 3 |
| `add.st_orrr_rd` | arith-logic-tetra | `SimRISC-08: add.st` | 2 | 1 | 1 | 2 |
| `add.sw_orrr_rd` | arith-logic-wyde | `SimRISC-09: add.sw` | 3 | 1 | 2 | 3 |
| `add.ub_orrr_rd` | arith-logic-byte | `SimRISC-10: add.ub` | 2 | 1 | 1 | 2 |
| `add.uo_rrrr_rd` | arith-logic-octa | `SimRISC-04: add.uo` | 3 | 1 | 2 | 3 |
| `add.ut_orrr_rd` | arith-logic-tetra | `SimRISC-08: add.ut` | 2 | 1 | 1 | 2 |
| `add.uw_orrr_rd` | arith-logic-wyde | `SimRISC-09: add.uw` | 3 | 1 | 2 | 3 |
| `aip.si_riii_rb` | arith-addr | `SimRISC-05: aip.si` | 2 | 1 | 1 | 2 |
| `and.o_orrr_rd` | arith-logic-octa | `SimRISC-04: and.o` | 2 | 1 | 1 | 2 |
| `andn.w_rwii_rb` | wyde-imm | `SimRISC-03: andn.w` | 2 | 1 | 1 | 2 |
| `andn.w_rwii_rd` | wyde-imm | `SimRISC-03: andn.w` | 2 | 1 | 1 | 2 |
| `br.eq_rrii_rd` | control-flow | `SimRISC-06: br.eq` | 2 | 1 | 1 | 2 |
| `br.n_riii_rd` | control-flow | `SimRISC-06: br.n` | 2 | 1 | 1 | 2 |
| `br.ne_rrii_rd` | control-flow | `SimRISC-06: br.ne` | 2 | 1 | 1 | 2 |
| `br.nn_riii_rd` | control-flow | `SimRISC-06: br.nn` | 2 | 1 | 1 | 2 |
| `br.np_riii_rd` | control-flow | `SimRISC-06: br.np` | 2 | 1 | 1 | 2 |
| `br.nz_riii_rb` | control-flow | `SimRISC-06: br.nz` | 2 | 1 | 1 | 2 |
| `br.nz_riii_rd` | control-flow | `SimRISC-06: br.nz` | 2 | 1 | 1 | 2 |
| `br.p_riii_rd` | control-flow | `SimRISC-06: br.p` | 2 | 1 | 1 | 2 |
| `br.z_riii_rb` | control-flow | `SimRISC-06: br.z` | 2 | 1 | 1 | 2 |
| `br.z_riii_rd` | control-flow | `SimRISC-06: br.z` | 2 | 1 | 1 | 2 |
| `call_iiii_ra` | control-flow | `SimRISC-06: call` | 2 | 1 | 1 | 2 |
| `call_rrii_ra` | control-flow | `SimRISC-06: call` | 3 | 1 | 2 | 3 |
| `clmul.o_rrrr_rd` | arith-logic-octa | `SimRISC-04: clmul.o` | 3 | 1 | 2 | 3 |
| `cmp.sb_orrr_rd` | arith-logic-byte | `SimRISC-10: cmp.sb` | 2 | 1 | 1 | 2 |
| `cmp.si_rrii_rd` | arith-logic-octa | `SimRISC-04: cmp.si` | 2 | 1 | 1 | 2 |
| `cmp.so_orrr_rd` | arith-logic-octa | `SimRISC-04: cmp.so` | 2 | 1 | 1 | 2 |
| `cmp.st_orrr_rd` | arith-logic-tetra | `SimRISC-08: cmp.st` | 2 | 1 | 1 | 2 |
| `cmp.sw_orrr_rd` | arith-logic-wyde | `SimRISC-09: cmp.sw` | 3 | 1 | 2 | 3 |
| `cmp.ub_orrr_rd` | arith-logic-byte | `SimRISC-10: cmp.ub` | 2 | 1 | 1 | 2 |
| `cmp.ui_rrii_rd` | arith-logic-octa | `SimRISC-04: cmp.ui` | 2 | 1 | 1 | 2 |
| `cmp.uo_orrr_dbb` | arith-addr | `SimRISC-05: cmp.uo` | 2 | 1 | 1 | 2 |
| `cmp.uo_orrr_rd` | arith-logic-octa | `SimRISC-04: cmp.uo` | 2 | 1 | 1 | 2 |
| `cmp.ut_orrr_rd` | arith-logic-tetra | `SimRISC-08: cmp.ut` | 2 | 1 | 1 | 2 |
| `cmp.uw_orrr_rd` | arith-logic-wyde | `SimRISC-09: cmp.uw` | 3 | 1 | 2 | 3 |
| `cs.eq_rrrr_rd` | reg-copy | `SimRISC-02: cs.eq` | 2 | 1 | 1 | 2 |
| `cs.n_rrrr_rd` | reg-copy | `SimRISC-02: cs.n` | 2 | 1 | 1 | 2 |
| `cs.ne_rrrr_rd` | reg-copy | `SimRISC-02: cs.ne` | 2 | 1 | 1 | 2 |
| `cs.p_rrrr_rd` | reg-copy | `SimRISC-02: cs.p` | 2 | 1 | 1 | 2 |
| `cs.z_rrrr_rd` | reg-copy | `SimRISC-02: cs.z` | 2 | 1 | 1 | 2 |
| `ctlz_orri_rd` | misc | `SimRISC-12: ctlz` | 2 | 1 | 1 | 2 |
| `ctpop_orri_rd` | misc | `SimRISC-12: ctpop` | 2 | 1 | 1 | 2 |
| `cttz_orri_rd` | misc | `SimRISC-12: cttz` | 2 | 1 | 1 | 2 |
| `div.sb_orrr_rd` | arith-logic-byte | `SimRISC-10: div.sb` | 2 | 1 | 1 | 2 |
| `div.so_orrr_rd` | arith-logic-octa | `SimRISC-04: div.so` | 2 | 1 | 1 | 2 |
| `div.st_orrr_rd` | arith-logic-tetra | `SimRISC-08: div.st` | 2 | 1 | 1 | 2 |
| `div.sw_orrr_rd` | arith-logic-wyde | `SimRISC-09: div.sw` | 3 | 1 | 2 | 3 |
| `div.ub_orrr_rd` | arith-logic-byte | `SimRISC-10: div.ub` | 2 | 1 | 1 | 2 |
| `div.uo_orrr_rd` | arith-logic-octa | `SimRISC-04: div.uo` | 2 | 1 | 1 | 2 |
| `div.ut_orrr_rd` | arith-logic-tetra | `SimRISC-08: div.ut` | 2 | 1 | 1 | 2 |
| `div.uw_orrr_rd` | arith-logic-wyde | `SimRISC-09: div.uw` | 3 | 1 | 2 | 3 |
| `ext.so_orri_rd` | arith-logic-octa | `SimRISC-04: ext.so` | 2 | 1 | 1 | 2 |
| `ext.so_orrr_rd` | arith-logic-octa | `SimRISC-04: ext.so` | 2 | 1 | 1 | 2 |
| `ext.uo_orri_rd` | arith-logic-octa | `SimRISC-04: ext.uo` | 2 | 1 | 1 | 2 |
| `ext.uo_orrr_rd` | arith-logic-octa | `SimRISC-04: ext.uo` | 2 | 1 | 1 | 2 |
| `jump_iiii_rb` | control-flow | `SimRISC-06: jump` | 2 | 1 | 1 | 2 |
| `jump_rrii_rb` | control-flow | `SimRISC-06: jump` | 2 | 1 | 1 | 2 |
| `ld.o_rrii_ra` | load-store | `SimRISC-01: ld.o` | 3 | 1 | 2 | 3 |
| `ld.o_rrii_rb` | load-store | `SimRISC-01: ld.o` | 4 | 1 | 3 | 4 |
| `ld.o_rrii_rd` | load-store | `SimRISC-01: ld.o` | 5 | 1 | 4 | 5 |
| `ld.sb_rrii_rd` | load-store | `SimRISC-01: ld.sb` | 3 | 1 | 2 | 3 |
| `ld.st_rrii_rd` | load-store | `SimRISC-01: ld.st` | 4 | 1 | 3 | 4 |
| `ld.sw_rrii_rd` | load-store | `SimRISC-01: ld.sw` | 4 | 1 | 3 | 4 |
| `ld.ub_rrii_rd` | load-store | `SimRISC-01: ld.ub` | 4 | 1 | 3 | 4 |
| `ld.ut_rrii_rd` | load-store | `SimRISC-01: ld.ut` | 4 | 1 | 3 | 4 |
| `ld.uw_rrii_rd` | load-store | `SimRISC-01: ld.uw` | 4 | 1 | 3 | 4 |
| `ldm.o_rrri_ra` | load-store | `SimRISC-01: ldm.o` | 8 | 1 | 7 | 8 |
| `ldm.o_rrri_rb` | load-store | `SimRISC-01: ldm.o` | 10 | 1 | 9 | 10 |
| `ldm.o_rrri_rd` | load-store | `SimRISC-01: ldm.o` | 10 | 1 | 9 | 10 |
| `ldm.sb_rrri_rd` | load-store | `SimRISC-01: ldm.sb` | 9 | 1 | 8 | 9 |
| `ldm.st_rrri_rd` | load-store | `SimRISC-01: ldm.st` | 10 | 1 | 9 | 10 |
| `ldm.sw_rrri_rd` | load-store | `SimRISC-01: ldm.sw` | 10 | 1 | 9 | 10 |
| `ldm.ub_rrri_rd` | load-store | `SimRISC-01: ldm.ub` | 9 | 1 | 8 | 9 |
| `ldm.ut_rrri_rd` | load-store | `SimRISC-01: ldm.ut` | 10 | 1 | 9 | 10 |
| `ldm.uw_rrri_rd` | load-store | `SimRISC-01: ldm.uw` | 10 | 1 | 9 | 10 |
| `lr.b.an_orrr_rd` | misc | `SimRISC-12: lr.b.an` | 2 | 1 | 1 | 2 |
| `lr.b.ar_orrr_rd` | misc | `SimRISC-12: lr.b.ar` | 2 | 1 | 1 | 2 |
| `lr.b.nn_orrr_rd` | misc | `SimRISC-12: lr.b.nn` | 2 | 1 | 1 | 2 |
| `lr.o.an_orrr_rd` | misc | `SimRISC-12: lr.o.an` | 3 | 1 | 2 | 3 |
| `lr.o.ar_orrr_rd` | misc | `SimRISC-12: lr.o.ar` | 3 | 1 | 2 | 3 |
| `lr.o.nn_orrr_rd` | misc | `SimRISC-12: lr.o.nn` | 3 | 1 | 2 | 3 |
| `lr.t.an_orrr_rd` | misc | `SimRISC-12: lr.t.an` | 3 | 1 | 2 | 3 |
| `lr.t.ar_orrr_rd` | misc | `SimRISC-12: lr.t.ar` | 3 | 1 | 2 | 3 |
| `lr.t.nn_orrr_rd` | misc | `SimRISC-12: lr.t.nn` | 3 | 1 | 2 | 3 |
| `lr.w.an_orrr_rd` | misc | `SimRISC-12: lr.w.an` | 3 | 1 | 2 | 3 |
| `lr.w.ar_orrr_rd` | misc | `SimRISC-12: lr.w.ar` | 3 | 1 | 2 | 3 |
| `lr.w.nn_orrr_rd` | misc | `SimRISC-12: lr.w.nn` | 3 | 1 | 2 | 3 |
| `mul.sb_orrr_rd` | arith-logic-byte | `SimRISC-10: mul.sb` | 2 | 1 | 1 | 2 |
| `mul.so_rrrr_rd` | arith-logic-octa | `SimRISC-04: mul.so` | 3 | 1 | 2 | 3 |
| `mul.st_orrr_rd` | arith-logic-tetra | `SimRISC-08: mul.st` | 2 | 1 | 1 | 2 |
| `mul.sw_orrr_rd` | arith-logic-wyde | `SimRISC-09: mul.sw` | 3 | 1 | 2 | 3 |
| `mul.ub_orrr_rd` | arith-logic-byte | `SimRISC-10: mul.ub` | 2 | 1 | 1 | 2 |
| `mul.uo_rrrr_rd` | arith-logic-octa | `SimRISC-04: mul.uo` | 3 | 1 | 2 | 3 |
| `mul.ut_orrr_rd` | arith-logic-tetra | `SimRISC-08: mul.ut` | 2 | 1 | 1 | 2 |
| `mul.uw_orrr_rd` | arith-logic-wyde | `SimRISC-09: mul.uw` | 3 | 1 | 2 | 3 |
| `or.o_orrr_rd` | arith-logic-octa | `SimRISC-04: or.o` | 2 | 1 | 1 | 2 |
| `or.w_rwii_rb` | wyde-imm | `SimRISC-03: or.w` | 2 | 1 | 1 | 2 |
| `or.w_rwii_rd` | wyde-imm | `SimRISC-03: or.w` | 2 | 1 | 1 | 2 |
| `ra2rd_orri_ra` | reg-copy | `SimRISC-02: ra2rd` | 5 | 1 | 4 | 5 |
| `rb2rb_orri_rb` | reg-copy | `SimRISC-02: rb2rb` | 7 | 1 | 6 | 7 |
| `rb2rd_orri_rb` | reg-copy | `SimRISC-02: rb2rd` | 5 | 1 | 4 | 5 |
| `rd2ra_orri_ra` | reg-copy | `SimRISC-02: rd2ra` | 4 | 1 | 3 | 4 |
| `rd2rb_orri_rb` | reg-copy | `SimRISC-02: rd2rb` | 5 | 1 | 4 | 5 |
| `rd2rd_orri_rd` | reg-copy | `SimRISC-02: rd2rd` | 7 | 1 | 6 | 7 |
| `rem.sb_orrr_rd` | arith-logic-byte | `SimRISC-10: rem.sb` | 2 | 1 | 1 | 2 |
| `rem.so_orrr_rd` | arith-logic-octa | `SimRISC-04: rem.so` | 2 | 1 | 1 | 2 |
| `rem.st_orrr_rd` | arith-logic-tetra | `SimRISC-08: rem.st` | 2 | 1 | 1 | 2 |
| `rem.sw_orrr_rd` | arith-logic-wyde | `SimRISC-09: rem.sw` | 3 | 1 | 2 | 3 |
| `rem.ub_orrr_rd` | arith-logic-byte | `SimRISC-10: rem.ub` | 2 | 1 | 1 | 2 |
| `rem.uo_orrr_rd` | arith-logic-octa | `SimRISC-04: rem.uo` | 2 | 1 | 1 | 2 |
| `rem.ut_orrr_rd` | arith-logic-tetra | `SimRISC-08: rem.ut` | 2 | 1 | 1 | 2 |
| `rem.uw_orrr_rd` | arith-logic-wyde | `SimRISC-09: rem.uw` | 3 | 1 | 2 | 3 |
| `ret_riii_ra` | control-flow | `SimRISC-06: ret` | 6 | 1 | 5 | 6 |
| `rev.b_orri_rd` | arith-logic-byte | `SimRISC-10: rev.b` | 4 | 1 | 3 | 4 |
| `rev.o_orri_rd` | arith-logic-octa | `SimRISC-04: rev.o` | 5 | 1 | 4 | 5 |
| `rev.t_orri_rd` | arith-logic-tetra | `SimRISC-08: rev.t` | 7 | 1 | 6 | 7 |
| `rev.w_orri_rd` | arith-logic-wyde | `SimRISC-09: rev.w` | 9 | 1 | 8 | 9 |
| `rol.b_orri_rd` | arith-logic-byte | `SimRISC-10: rol.b` | 4 | 1 | 3 | 4 |
| `rol.b_orrr_rd` | arith-logic-byte | `SimRISC-10: rol.b` | 2 | 1 | 1 | 2 |
| `rol.o_orri_rd` | arith-logic-octa | `SimRISC-04: rol.o` | 2 | 1 | 1 | 2 |
| `rol.o_orrr_rd` | arith-logic-octa | `SimRISC-04: rol.o` | 2 | 1 | 1 | 2 |
| `rol.t_orri_rd` | arith-logic-tetra | `SimRISC-08: rol.t` | 4 | 1 | 3 | 4 |
| `rol.t_orrr_rd` | arith-logic-tetra | `SimRISC-08: rol.t` | 2 | 1 | 1 | 2 |
| `rol.w_orri_rd` | arith-logic-wyde | `SimRISC-09: rol.w` | 5 | 1 | 4 | 5 |
| `rol.w_orrr_rd` | arith-logic-wyde | `SimRISC-09: rol.w` | 3 | 1 | 2 | 3 |
| `sc.b.ar_orrr_rd` | misc | `SimRISC-12: sc.b.ar` | 2 | 1 | 1 | 2 |
| `sc.b.nn_orrr_rd` | misc | `SimRISC-12: sc.b.nn` | 2 | 1 | 1 | 2 |
| `sc.b.nr_orrr_rd` | misc | `SimRISC-12: sc.b.nr` | 2 | 1 | 1 | 2 |
| `sc.o.ar_orrr_rd` | misc | `SimRISC-12: sc.o.ar` | 3 | 1 | 2 | 3 |
| `sc.o.nn_orrr_rd` | misc | `SimRISC-12: sc.o.nn` | 3 | 1 | 2 | 3 |
| `sc.o.nr_orrr_rd` | misc | `SimRISC-12: sc.o.nr` | 3 | 1 | 2 | 3 |
| `sc.t.ar_orrr_rd` | misc | `SimRISC-12: sc.t.ar` | 3 | 1 | 2 | 3 |
| `sc.t.nn_orrr_rd` | misc | `SimRISC-12: sc.t.nn` | 3 | 1 | 2 | 3 |
| `sc.t.nr_orrr_rd` | misc | `SimRISC-12: sc.t.nr` | 3 | 1 | 2 | 3 |
| `sc.w.ar_orrr_rd` | misc | `SimRISC-12: sc.w.ar` | 3 | 1 | 2 | 3 |
| `sc.w.nn_orrr_rd` | misc | `SimRISC-12: sc.w.nn` | 3 | 1 | 2 | 3 |
| `sc.w.nr_orrr_rd` | misc | `SimRISC-12: sc.w.nr` | 3 | 1 | 2 | 3 |
| `set.ow_rwii_rd` | wyde-imm | `SimRISC-03: set.ow` | 2 | 1 | 1 | 2 |
| `set.zw_rwii_rb` | wyde-imm | `SimRISC-03: set.zw` | 2 | 1 | 1 | 2 |
| `set.zw_rwii_rd` | wyde-imm | `SimRISC-03: set.zw` | 2 | 1 | 1 | 2 |
| `shl.b_orri_rd` | arith-logic-byte | `SimRISC-10: shl.b` | 4 | 1 | 3 | 4 |
| `shl.b_orrr_rd` | arith-logic-byte | `SimRISC-10: shl.b` | 2 | 1 | 1 | 2 |
| `shl.o_orri_rd` | arith-logic-octa | `SimRISC-04: shl.o` | 2 | 1 | 1 | 2 |
| `shl.o_orrr_rd` | arith-logic-octa | `SimRISC-04: shl.o` | 2 | 1 | 1 | 2 |
| `shl.t_orri_rd` | arith-logic-tetra | `SimRISC-08: shl.t` | 4 | 1 | 3 | 4 |
| `shl.t_orrr_rd` | arith-logic-tetra | `SimRISC-08: shl.t` | 2 | 1 | 1 | 2 |
| `shl.w_orri_rd` | arith-logic-wyde | `SimRISC-09: shl.w` | 5 | 1 | 4 | 5 |
| `shl.w_orrr_rd` | arith-logic-wyde | `SimRISC-09: shl.w` | 3 | 1 | 2 | 3 |
| `shr.sb_orri_rd` | arith-logic-byte | `SimRISC-10: shr.sb` | 4 | 1 | 3 | 4 |
| `shr.sb_orrr_rd` | arith-logic-byte | `SimRISC-10: shr.sb` | 2 | 1 | 1 | 2 |
| `shr.so_orri_rd` | arith-logic-octa | `SimRISC-04: shr.so` | 2 | 1 | 1 | 2 |
| `shr.so_orrr_rd` | arith-logic-octa | `SimRISC-04: shr.so` | 2 | 1 | 1 | 2 |
| `shr.st_orri_rd` | arith-logic-tetra | `SimRISC-08: shr.st` | 4 | 1 | 3 | 4 |
| `shr.st_orrr_rd` | arith-logic-tetra | `SimRISC-08: shr.st` | 2 | 1 | 1 | 2 |
| `shr.sw_orri_rd` | arith-logic-wyde | `SimRISC-09: shr.sw` | 5 | 1 | 4 | 5 |
| `shr.sw_orrr_rd` | arith-logic-wyde | `SimRISC-09: shr.sw` | 3 | 1 | 2 | 3 |
| `shr.ub_orri_rd` | arith-logic-byte | `SimRISC-10: shr.ub` | 4 | 1 | 3 | 4 |
| `shr.ub_orrr_rd` | arith-logic-byte | `SimRISC-10: shr.ub` | 2 | 1 | 1 | 2 |
| `shr.uo_orri_rd` | arith-logic-octa | `SimRISC-04: shr.uo` | 2 | 1 | 1 | 2 |
| `shr.uo_orrr_rd` | arith-logic-octa | `SimRISC-04: shr.uo` | 2 | 1 | 1 | 2 |
| `shr.ut_orri_rd` | arith-logic-tetra | `SimRISC-08: shr.ut` | 4 | 1 | 3 | 4 |
| `shr.ut_orrr_rd` | arith-logic-tetra | `SimRISC-08: shr.ut` | 2 | 1 | 1 | 2 |
| `shr.uw_orri_rd` | arith-logic-wyde | `SimRISC-09: shr.uw` | 5 | 1 | 4 | 5 |
| `shr.uw_orrr_rd` | arith-logic-wyde | `SimRISC-09: shr.uw` | 3 | 1 | 2 | 3 |
| `st.b_rrii_rd` | load-store | `SimRISC-01: st.b` | 4 | 1 | 3 | 4 |
| `st.o_rrii_ra` | load-store | `SimRISC-01: st.o` | 3 | 1 | 2 | 3 |
| `st.o_rrii_rb` | load-store | `SimRISC-01: st.o` | 3 | 1 | 2 | 3 |
| `st.o_rrii_rd` | load-store | `SimRISC-01: st.o` | 5 | 1 | 4 | 5 |
| `st.t_rrii_rd` | load-store | `SimRISC-01: st.t` | 3 | 1 | 2 | 3 |
| `st.w_rrii_rd` | load-store | `SimRISC-01: st.w` | 3 | 1 | 2 | 3 |
| `stm.b_rrri_rd` | load-store | `SimRISC-01: stm.b` | 7 | 1 | 6 | 7 |
| `stm.o_rrri_ra` | load-store | `SimRISC-01: stm.o` | 8 | 1 | 7 | 8 |
| `stm.o_rrri_rb` | load-store | `SimRISC-01: stm.o` | 8 | 1 | 7 | 8 |
| `stm.o_rrri_rd` | load-store | `SimRISC-01: stm.o` | 8 | 1 | 7 | 8 |
| `stm.t_rrri_rd` | load-store | `SimRISC-01: stm.t` | 8 | 1 | 7 | 8 |
| `stm.w_rrri_rd` | load-store | `SimRISC-01: stm.w` | 8 | 1 | 7 | 8 |
| `sub.o_orrr_bbd` | arith-addr | `SimRISC-05: sub.o` | 2 | 1 | 1 | 2 |
| `sub.o_orrr_dbb` | arith-addr | `SimRISC-05: sub.o` | 2 | 1 | 1 | 2 |
| `sub.sb_orrr_rd` | arith-logic-byte | `SimRISC-10: sub.sb` | 2 | 1 | 1 | 2 |
| `sub.so_rrrr_rd` | arith-logic-octa | `SimRISC-04: sub.so` | 3 | 1 | 2 | 3 |
| `sub.st_orrr_rd` | arith-logic-tetra | `SimRISC-08: sub.st` | 2 | 1 | 1 | 2 |
| `sub.sw_orrr_rd` | arith-logic-wyde | `SimRISC-09: sub.sw` | 3 | 1 | 2 | 3 |
| `sub.ub_orrr_rd` | arith-logic-byte | `SimRISC-10: sub.ub` | 2 | 1 | 1 | 2 |
| `sub.uo_rrrr_rd` | arith-logic-octa | `SimRISC-04: sub.uo` | 3 | 1 | 2 | 3 |
| `sub.ut_orrr_rd` | arith-logic-tetra | `SimRISC-08: sub.ut` | 2 | 1 | 1 | 2 |
| `sub.uw_orrr_rd` | arith-logic-wyde | `SimRISC-09: sub.uw` | 3 | 1 | 2 | 3 |
| `swym_oiii_imm` | misc | `SimRISC-12: swym` | 1 | 1 | 0 | 1 |
| `undi_reserved` | isa-design | `SimRISC-00: §2.9` | 3 | 0 | 3 | 3 |
| `xnor.o_orrr_rd` | arith-logic-octa | `SimRISC-04: xnor.o` | 2 | 1 | 1 | 2 |
| `xor.o_orrr_rd` | arith-logic-octa | `SimRISC-04: xor.o` | 2 | 1 | 1 | 2 |

> 逐镜像的三平台 `exit` / 结果字节流 md5 在配套 JSON 的 `results.per_image`（每条记录即一份状态文件摘要）。

## 3. 覆盖缺口与未跑项

- 覆盖缺口（非语义类）：**0**
- 未在三平台跑的 id：**0**
  - (none) — 本任务范围内全部载体都是单 hart 可执行例（chipyard `WumingTinyConfig` 单 hart）；多 hart 原子语义无观测载体，记 GAP 不造用例（`m13-chipyard-002` GAP 同口径）

## 4. 已知项（单列，不混入平台差异）

- `ISS-357`（open）：SE dual-fd output capture loses fd1/fd2 order（not applicable: this differential uses a single semihosting output channel and compares bytes only）
- `ISS-373`（open）：shared install root may diverge from the build tree (m13-qemu-014: installed-root qemu is still the pre-fix build); a differential must pin the executed binary instead of assuming they agree（run identity: the engine fingerprint below is the binary actually executed (the build tree), not the installed root）
- `m13-testcases-037`（tracked）：sc/sys reservation granularity (exact address + width) formal vectors are a separate task; do not mix them into this count（vector surface: this report covers the .S carriers present in the input commit; sc reservation-granularity vectors land afterwards and require regeneration）

## 5. 输入与可重算

- `contracts/opcodes.yaml` sha256 `53e296460272d8e5`
- `tests/inst.yaml` sha256 `bd27cdd8d7e1451c`
- `.tao/contracts/contract-isa.md` sha256 `22cd75750d644dfe`
- `spec/SimRISC-00-指令系统设计.md` sha256 `dee1c73d757650a0`
- `spec/SimRISC-01-取数存数.md` sha256 `1a6367885643fee8`
- `spec/SimRISC-02-寄存器复制.md` sha256 `f4883ea46e9677db`
- `spec/SimRISC-03-16位立即数操作.md` sha256 `f7dff2ac968bc9b0`
- `spec/SimRISC-04-64位数据运算.md` sha256 `186b375d4f586936`
- `spec/SimRISC-05-64位地址运算.md` sha256 `5c77bdf96a9a8779`
- `spec/SimRISC-06-控制流.md` sha256 `2549942a9a966ff5`
- `spec/SimRISC-08-32位数据运算.md` sha256 `7c77f6419576430f`
- `spec/SimRISC-09-16位数据运算.md` sha256 `01ceb91779631c30`
- `spec/SimRISC-10-8位数据运算.md` sha256 `299ddc18a256bb5c`
- `spec/SimRISC-12-其它指令.md` sha256 `3f051f49639001fa`
- run `ics150`：157 条记录 sha256 `86138df79aef6c0a`
- run `ics160`：157 条记录 sha256 `ea80d6a6f4fba64d`
- run `ics180`：158 条记录 sha256 `d63aad1d0c2e6bc2`
- run `server207`：157 条记录 sha256 `e081b1fe004b15c8`

引擎指纹（md5，报告身份）：
- qemu: `725c5da788cf4ca7ceba569221f9f1f6`
- gem5: `6e436d1bfe5935ed949491b509e63a29`
- chipyard: `079ae01569e5fbf9fa9944bd6aee89cd`

## 6. 判据

- 每个非 `AGREE_PASS` 差异均已归因；语义出处/覆盖/索引缺口逐条列出；平台完成数与现场枚举分母一致

