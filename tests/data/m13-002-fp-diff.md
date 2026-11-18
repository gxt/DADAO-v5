# m13-integ-002: 浮点指令三平台逐例差分（qemu / gem5 / chipyard）

> 由 `tools/testcases/parity/fp_diff.py` 从已入库输入确定性重建；不写生成时刻、不写运行期路径。

## 0. 计数口径（现场统计）

- `contracts/opcodes.yaml` 的 `scope: fp`：**66** 条（机器可读口径，本报告的覆盖全集）
- `spec/SimRISC-07` 附录 A：**52** 行（人读排版口径；与 scope:fp 的差集 = 8 条 rf 访存 + 3 条 `cs.*` + `set.w rf` + `rd2rf`/`rf2rd`）
- 历史别名「47 条」：**47** —— 在任何机器可读源里都复现不出（`issues.yaml` 已登记；47 退役，不再作判据）

## 1. 覆盖（每条 id：载体 / 链例点 / 故障例 / 索引）

- scope:fp **66** 条；有 `.S` 载体 **66**；在 `tests/inst.yaml` 登记 **62**。

| id | 助记符 | 类别 | 载体 | 链例点 | 故障例 | 索引 |
| --- | --- | --- | --- | --- | --- | --- |
| `cs.n_rrrr_rf` | `cs.n` | fp_extended | `tests/inst/02-reg-copy/cs.n_rrrr_rf.S` | 14 | 1 | yes |
| `cs.p_rrrr_rf` | `cs.p` | fp_extended | `tests/inst/02-reg-copy/cs.p_rrrr_rf.S` | 14 | 1 | yes |
| `cs.z_rrrr_rf` | `cs.z` | fp_extended | `tests/inst/02-reg-copy/cs.z_rrrr_rf.S` | 14 | 1 | yes |
| `fo2fo_orri_rf` | `fo2fo` | fp_arithmetic | `tests/inst/07-floating-point/fo2fo_orri_rf.S` | 11 | 5 | yes |
| `fo2ft_orri_rf` | `fo2ft` | fp_arithmetic | `tests/inst/07-floating-point/fo2ft_orri_rf.S` | 30 | 3 | yes |
| `fo2io_orri_rf` | `fo2io` | fp_arithmetic | `tests/inst/07-floating-point/fo2io_orri_rf.S` | 25 | 4 | yes |
| `fo2it_orri_rf` | `fo2it` | fp_arithmetic | `tests/inst/07-floating-point/fo2it_orri_rf.S` | 24 | 4 | yes |
| `fo2uo_orri_rf` | `fo2uo` | fp_arithmetic | `tests/inst/07-floating-point/fo2uo_orri_rf.S` | 26 | 4 | yes |
| `fo2ut_orri_rf` | `fo2ut` | fp_arithmetic | `tests/inst/07-floating-point/fo2ut_orri_rf.S` | 25 | 4 | yes |
| `foadd_orrr_rf` | `foadd` | fp_arithmetic | `tests/inst/07-floating-point/foadd_orrr_rf.S` | 18 | 1 | yes |
| `focls_orri_rf` | `focls` | fp_arithmetic | `tests/inst/07-floating-point/focls_orri_rf.S` | 18 | 4 | yes |
| `fodiv_orrr_rf` | `fodiv` | fp_arithmetic | `tests/inst/07-floating-point/fodiv_orrr_rf.S` | 21 | 1 | yes |
| `fofma_rrrr_rf` | `fofma` | fp_arithmetic | `tests/inst/07-floating-point/fofma_rrrr_rf.S` | 19 | 1 | yes |
| `fomax_orrr_rf` | `fomax` | fp_arithmetic | `tests/inst/07-floating-point/fomax_orrr_rf.S` | 16 | 1 | yes |
| `fomin_orrr_rf` | `fomin` | fp_arithmetic | `tests/inst/07-floating-point/fomin_orrr_rf.S` | 16 | 1 | yes |
| `fomul_orrr_rf` | `fomul` | fp_arithmetic | `tests/inst/07-floating-point/fomul_orrr_rf.S` | 16 | 1 | yes |
| `foqcmp_orrr_rf` | `foqcmp` | fp_arithmetic | `tests/inst/07-floating-point/foqcmp_orrr_rf.S` | 18 | 1 | yes |
| `forem_orrr_rf` | `forem` | fp_arithmetic | `tests/inst/07-floating-point/forem_orrr_rf.S` | 19 | 1 | yes |
| `fornd_orri_rf` | `fornd` | fp_arithmetic | `tests/inst/07-floating-point/fornd_orri_rf.S` | 24 | 4 | yes |
| `foroot_orri_rf` | `foroot` | fp_arithmetic | `tests/inst/07-floating-point/foroot_orri_rf.S` | 18 | 2 | yes |
| `fosclb_orrr_rf` | `fosclb` | fp_arithmetic | `tests/inst/07-floating-point/fosclb_orrr_rf.S` | 22 | 1 | yes |
| `foscmp_orrr_rf` | `foscmp` | fp_arithmetic | `tests/inst/07-floating-point/foscmp_orrr_rf.S` | 17 | 1 | yes |
| `fosgnj_orrr_rf` | `fosgnj` | fp_arithmetic | `tests/inst/07-floating-point/fosgnj_orrr_rf.S` | 15 | 1 | yes |
| `fosgnn_orrr_rf` | `fosgnn` | fp_arithmetic | `tests/inst/07-floating-point/fosgnn_orrr_rf.S` | 15 | 1 | yes |
| `fosub_orrr_rf` | `fosub` | fp_arithmetic | `tests/inst/07-floating-point/fosub_orrr_rf.S` | 18 | 1 | yes |
| `ft2fo_orri_rf` | `ft2fo` | fp_arithmetic | `tests/inst/07-floating-point/ft2fo_orri_rf.S` | 15 | 3 | yes |
| `ft2ft_orri_rf` | `ft2ft` | fp_arithmetic | `tests/inst/07-floating-point/ft2ft_orri_rf.S` | 11 | 5 | yes |
| `ft2io_orri_rf` | `ft2io` | fp_arithmetic | `tests/inst/07-floating-point/ft2io_orri_rf.S` | 24 | 4 | yes |
| `ft2it_orri_rf` | `ft2it` | fp_arithmetic | `tests/inst/07-floating-point/ft2it_orri_rf.S` | 30 | 4 | yes |
| `ft2uo_orri_rf` | `ft2uo` | fp_arithmetic | `tests/inst/07-floating-point/ft2uo_orri_rf.S` | 26 | 4 | yes |
| `ft2ut_orri_rf` | `ft2ut` | fp_arithmetic | `tests/inst/07-floating-point/ft2ut_orri_rf.S` | 25 | 4 | yes |
| `ftadd_orrr_rf` | `ftadd` | fp_arithmetic | `tests/inst/07-floating-point/ftadd_orrr_rf.S` | 18 | 1 | yes |
| `ftcls_orri_rf` | `ftcls` | fp_arithmetic | `tests/inst/07-floating-point/ftcls_orri_rf.S` | 20 | 4 | yes |
| `ftdiv_orrr_rf` | `ftdiv` | fp_arithmetic | `tests/inst/07-floating-point/ftdiv_orrr_rf.S` | 21 | 1 | yes |
| `ftfma_rrrr_rf` | `ftfma` | fp_arithmetic | `tests/inst/07-floating-point/ftfma_rrrr_rf.S` | 19 | 1 | yes |
| `ftmax_orrr_rf` | `ftmax` | fp_arithmetic | `tests/inst/07-floating-point/ftmax_orrr_rf.S` | 16 | 1 | yes |
| `ftmin_orrr_rf` | `ftmin` | fp_arithmetic | `tests/inst/07-floating-point/ftmin_orrr_rf.S` | 16 | 1 | yes |
| `ftmul_orrr_rf` | `ftmul` | fp_arithmetic | `tests/inst/07-floating-point/ftmul_orrr_rf.S` | 16 | 1 | yes |
| `ftqcmp_orrr_rf` | `ftqcmp` | fp_arithmetic | `tests/inst/07-floating-point/ftqcmp_orrr_rf.S` | 18 | 1 | yes |
| `ftrem_orrr_rf` | `ftrem` | fp_arithmetic | `tests/inst/07-floating-point/ftrem_orrr_rf.S` | 19 | 1 | yes |
| `ftrnd_orri_rf` | `ftrnd` | fp_arithmetic | `tests/inst/07-floating-point/ftrnd_orri_rf.S` | 24 | 4 | yes |
| `ftroot_orri_rf` | `ftroot` | fp_arithmetic | `tests/inst/07-floating-point/ftroot_orri_rf.S` | 18 | 2 | yes |
| `ftsclb_orrr_rf` | `ftsclb` | fp_arithmetic | `tests/inst/07-floating-point/ftsclb_orrr_rf.S` | 22 | 1 | yes |
| `ftscmp_orrr_rf` | `ftscmp` | fp_arithmetic | `tests/inst/07-floating-point/ftscmp_orrr_rf.S` | 17 | 1 | yes |
| `ftsgnj_orrr_rf` | `ftsgnj` | fp_arithmetic | `tests/inst/07-floating-point/ftsgnj_orrr_rf.S` | 15 | 1 | yes |
| `ftsgnn_orrr_rf` | `ftsgnn` | fp_arithmetic | `tests/inst/07-floating-point/ftsgnn_orrr_rf.S` | 15 | 1 | yes |
| `ftsub_orrr_rf` | `ftsub` | fp_arithmetic | `tests/inst/07-floating-point/ftsub_orrr_rf.S` | 18 | 1 | yes |
| `io2fo_orri_rf` | `io2fo` | fp_arithmetic | `tests/inst/07-floating-point/io2fo_orri_rf.S` | 17 | 3 | yes |
| `io2ft_orri_rf` | `io2ft` | fp_arithmetic | `tests/inst/07-floating-point/io2ft_orri_rf.S` | 17 | 3 | yes |
| `it2fo_orri_rf` | `it2fo` | fp_arithmetic | `tests/inst/07-floating-point/it2fo_orri_rf.S` | 10 | 3 | yes |
| `it2ft_orri_rf` | `it2ft` | fp_arithmetic | `tests/inst/07-floating-point/it2ft_orri_rf.S` | 17 | 3 | yes |
| `ld.o_rrii_rf` | `ld.o` | fp_extended | `tests/inst/01-load-store/ld.o_rrii_rf.S` | 15 | 2 | yes |
| `ld.t_rrii_rf` | `ld.t` | fp_extended | `tests/inst/01-load-store/ld.t_rrii_rf.S` | 15 | 2 | yes |
| `ldm.o_rrri_rf` | `ldm.o` | fp_extended | `tests/inst/01-load-store/ldm.o_rrri_rf.S` | 15 | 7 | **NO** |
| `ldm.t_rrri_rf` | `ldm.t` | fp_extended | `tests/inst/01-load-store/ldm.t_rrri_rf.S` | 12 | 7 | **NO** |
| `rd2rf_orri_rf` | `rd2rf` | fp_extended | `tests/inst/02-reg-copy/rd2rf_orri_rf.S` | 12 | 3 | yes |
| `rf2rd_orri_rf` | `rf2rd` | fp_extended | `tests/inst/02-reg-copy/rf2rd_orri_rf.S` | 11 | 4 | yes |
| `set.w_rwii_rf` | `set.w` | fp_extended | `tests/inst/03-wyde-imm/set.w_rwii_rf.S` | 17 | 0 | yes |
| `st.o_rrii_rf` | `st.o` | fp_extended | `tests/inst/01-load-store/st.o_rrii_rf.S` | 14 | 2 | yes |
| `st.t_rrii_rf` | `st.t` | fp_extended | `tests/inst/01-load-store/st.t_rrii_rf.S` | 14 | 2 | yes |
| `stm.o_rrri_rf` | `stm.o` | fp_extended | `tests/inst/01-load-store/stm.o_rrri_rf.S` | 8 | 8 | **NO** |
| `stm.t_rrri_rf` | `stm.t` | fp_extended | `tests/inst/01-load-store/stm.t_rrri_rf.S` | 8 | 8 | **NO** |
| `uo2fo_orri_rf` | `uo2fo` | fp_arithmetic | `tests/inst/07-floating-point/uo2fo_orri_rf.S` | 16 | 3 | yes |
| `uo2ft_orri_rf` | `uo2ft` | fp_arithmetic | `tests/inst/07-floating-point/uo2ft_orri_rf.S` | 16 | 3 | yes |
| `ut2fo_orri_rf` | `ut2fo` | fp_arithmetic | `tests/inst/07-floating-point/ut2fo_orri_rf.S` | 10 | 3 | yes |
| `ut2ft_orri_rf` | `ut2ft` | fp_arithmetic | `tests/inst/07-floating-point/ut2ft_orri_rf.S` | 16 | 3 | yes |

### 覆盖缺口（4）

- `ldm.o_rrri_rf` — not_indexed：inst/01-load-store/ldm.o_rrri_rf.S missing from tests/inst.yaml
- `ldm.t_rrri_rf` — not_indexed：inst/01-load-store/ldm.t_rrri_rf.S missing from tests/inst.yaml
- `stm.o_rrri_rf` — not_indexed：inst/01-load-store/stm.o_rrri_rf.S missing from tests/inst.yaml
- `stm.t_rrri_rf` — not_indexed：inst/01-load-store/stm.t_rrri_rf.S missing from tests/inst.yaml

> 缺口按现场统计如实列出，不以 `N/A` 冒充覆盖；载体存在但未登记索引的条目仍由 L2 `check-inst-asm` 执行。

## 2. 三平台逐例结果

- 镜像 **232**；三方一致通过 **232**；三方一致非通过 **0**；平台差异 **0**。

| id | 链例/故障 | 观测 | 归因 |
| --- | --- | --- | --- |
| — | — | 无平台差异 | — |

## 3. 舍入方向 × 异常标志矩阵（链例点，4 × 6）

单元 = 该 `rf0[33:32]` 档下期望该标志（或 flags=0）的链例点数 / 三平台逐点一致数；`rf0-sensitive` = 其中舍入真正受 `rf0` 控制的点数。

空白格 = **现有 `.S` 向量没有该组合**（测试资产缺口），不是引擎差异；本任务不改向量，逐格原因见下。矩阵只统计 `AGREE_PASS` 链例镜像的点，失败镜像已在 §2 单列。

| rf0[33:32] | NONE | NV | DZ | OF | UF | NX |
| --- | --- | --- | --- | --- | --- | --- |
| 0 RNE | 583 / 583 (rf0 171) | 147 / 147 (rf0 32) | 4 / 4 (rf0 4) | 22 / 22 (rf0 14) | 13 / 13 (rf0 10) | 167 / 167 (rf0 41) |
| 1 RTZ | 0 / 0 (rf0 0) | 0 / 0 (rf0 0) | 0 / 0 (rf0 0) | 8 / 8 (rf0 8) | 0 / 0 (rf0 0) | 19 / 19 (rf0 17) |
| 2 RDN | 8 / 8 (rf0 6) | 0 / 0 (rf0 0) | 0 / 0 (rf0 0) | 0 / 0 (rf0 0) | 0 / 0 (rf0 0) | 11 / 11 (rf0 5) |
| 3 RUP | 8 / 8 (rf0 8) | 0 / 0 (rf0 0) | 0 / 0 (rf0 0) | 0 / 0 (rf0 0) | 2 / 2 (rf0 2) | 26 / 26 (rf0 18) |

### 空白格说明（11）

- 1 RTZ × NONE：该舍入档没有 flags=0 的链例点
- 1 RTZ × NV：该标志位只在 0 RNE 档有点（本档无）
- 1 RTZ × DZ：该标志位只在 0 RNE 档有点（本档无）
- 1 RTZ × UF：该标志位只在 0 RNE / 3 RUP 档有点（本档无）
- 2 RDN × NV：该标志位只在 0 RNE 档有点（本档无）
- 2 RDN × DZ：该标志位只在 0 RNE 档有点（本档无）
- 2 RDN × OF：该标志位只在 0 RNE / 1 RTZ 档有点（本档无）
- 2 RDN × UF：该标志位只在 0 RNE / 3 RUP 档有点（本档无）
- 3 RUP × NV：该标志位只在 0 RNE 档有点（本档无）
- 3 RUP × DZ：该标志位只在 0 RNE 档有点（本档无）
- 3 RUP × OF：该标志位只在 0 RNE / 1 RTZ 档有点（本档无）

## 4. 已知项（单列，不混入 FP 语义差异）

- `ISS-357`：SE dual-fd output capture loses fd1/fd2 order（本差分包 not applicable: this differential uses a single semihosting output channel and compares bytes only）
- picolibc `math_test`：picolibc math_test gap stays in its own matrix（not in scope: separate picolibc suite, excluded by task）

## 5. 输入与可重算

- `contracts/opcodes.yaml` sha256 `53e296460272d8e5`
- `spec/SimRISC-07-浮点运算.md` sha256 `95d90ac2198ef966`
- `tests/inst.yaml` sha256 `18e69dd6817b5085`
- run `fp-book`：170 条记录 sha256 `1c3e89e432a377b3`
- run `fp-extras`：62 条记录 sha256 `34e546443044342c`

引擎指纹（md5，报告身份）：
- qemu: `b34ed7f99d8b1d90821f4b819eeb15c9`
- gem5: `6e436d1bfe5935ed949491b509e63a29`
- chipyard: `ac35dffbc90cef736e5e0788cecb51d2`

## 6. 判据

- 每个非 `AGREE_PASS` 差异均已归因；覆盖/索引缺口逐条列出

