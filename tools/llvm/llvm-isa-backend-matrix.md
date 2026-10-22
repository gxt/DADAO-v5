# ISA↔后端覆盖矩阵（生成式，两层分列）

> **生成器**：`tools/llvm/gen_isa_coverage.py`（生成物，勿手工编辑；改生成器或真源后重跑）
> **真源**：`contracts/opcodes.yaml`（**264** 条 = `m1` 156 + `fp` 60 + `excluded` 31 + `m3` 1 + `m8` 7 + `m9` 9；计数由脚本现场统计，不写死）
> **重跑**：`python3 tools/llvm/gen_isa_coverage.py`　**门控（反例可失败）**：`python3 tools/llvm/gen_isa_coverage.py --check`
> **机器可读**：`tools/llvm/llvm-isa-backend-matrix.tsv`（同源同批生成）

## 1. 两层口径

### 第①层「汇编器可受理」

逐条记录取**规范操作数形态**（每记录一个合法 shape）喂 `llvm-mc (--triple=dadao-unknown-elf -filetype=obj)`，记 `accept`/`reject`。

- 形态来源：`tools/testcases/generate_lit_vectors.py` 的 `build_case()`（与现有 lit 全量档 `tests/llvm/lit/MC/DADAO-gen/gen-*.s` **同一口径、同一行文本**；本工具不另立操作数拼装逻辑）。
- 受理后**另做编码复核**：由对象 `.text` 取 4 字节大端字，要求「按真源 `(word & mask) == value` 唯一命中本记录」且等于真源派生编码（`L1_encoding = ok / mismatch`）。这一列把第①层钉在真源上，而非只看 `llvm-mc` 自洽。
- 现场统计：`accept` **258** / `reject` **6**；编码复核不符 **0**。
- `scope: excluded` 且后端未实现者（`cfxld`/`cfxst`/`fomax`/`fomin`/`ftmax`/`ftmin`，现场派生）由汇编器**显式拒绝**（`reject`）；其余 `scope: excluded` 记录（MC 层已受理、执行侧仍 ILLI）与 `tests/llvm/lit/MC/DADAO-gen/gen-excluded.s` 的反例同口径。

### 第②层「ISel 用得上」（机械提取，非人工判读）

对每条记录，取其 `.td` def（由 `(mnemonic, format, op, ha)` 显式 join 真源），在后端补丁树中机械收集引用：

| 证据类型 | 含义 | 采集点 |
|---|---|---|
| `pat` | TableGen `Pat<...>` DAG 体内出现的指令 def 名（自动生成的 ISel 选入表） | `DADAOCodeGen.td.patch` 等 |
| `pat-args` | `def`/`defm` 的 Pat 类实参（含 `multiclass` 经 `defm` 传入的指令） | `DADAOCodeGen.td.patch` |
| `isel-cpp` | `DADAO::<def>` 显式引用（自定义选择器 / lowering 发射） | `DADAOISelDAGToDAG.cpp.patch`、`DADAOISelLowering.cpp.patch` |

现场统计：证据条数 = isel-cpp 34 + pat 113 + pat-args 8；判「用得上」的记录 **103** 条。

### 提取方法的局限（盲区披露）

- **纯静态**：只读已入库补丁源码，不看构建产物（`.inc`）与运行期；`multiclass`/类继承经人工写了机械展开规则（`Pat<` 体 + 实例化实参），若日后新增其它间接引用形式，须同步扩充提取规则。
- **post-ISel 不计入第②层**：伪指令展开（`DADAOInstrInfo::expandPostRAPseudo`）、分支松弛、帧处理、寄存器分配 `copyPhysReg` 等发射的指令，其引用点在 `DADAOInstrInfo.cpp` / `DADAOFrameLowering.cpp` / `DADAORegisterInfo.cpp`——**不属于 ISel**，单列为辅助列 `backend_post_isel`（仅作背景，不参与第②层判定）。
- **间接引用已覆盖**：`DAG.getNode(DADAOISD::…)` 自定义节点本身不是指令名，其落地指令由 `Pat` 覆盖（如 `cs.*` / `br.*`）；若某自定义节点的落地指令**只在 C++ 里 `BuildMI`**，则由 `isel-cpp` 捕获。
- **`.td` def 无真源记录者不入选**：CodeGen-only 伪指令（`*_PSEUDO`/`GLOBAL_ADDR`/`JT_ADDR`/`tailjmp_*`）不是 ISA 记录；`tailjmp_*` 与 `jump` 同编码，归入 `jump` 记录的证据。
- **MC-only 指令**：`fence` 汇编可得但无 ISel 模式 ⇒ 第②层 `no`（属正常，非缺陷）。

## 2. 矩阵（全量 264 条，按 id 排序）

列：`id` ｜ `mnemonic` ｜ `format` ｜ `scope` ｜ **①汇编器** ｜ **②ISel** ｜ 证据
（证据格式 `kind:文件:补丁物理行号:def名`，可直接 `sed -n '<行号>p' <文件>` 复核；完整形态行见 TSV 的 `L1_asm` 列）

| id | mnemonic | format | scope | ①汇编器 | ②ISel | 证据 |
|---|---|---|---|---|---|---|
| `add.o_orrr_bbd` | `add.o` | `orrr` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:167:add_o_bbd;isel-cpp:DADAOISelDAGToDAG.cpp.patch:199:add_o_bbd;isel-cpp:DADAOISelDAGToDAG.cpp.patch:448:add_o_bbd;isel-cpp:DADAOISelDAGToDAG.cpp.patch:475:add_o_bbd;isel-cpp:DADAOISelDAGToDAG.cpp.patch:529:add_o_bbd |
| `add.sb_orrr_rd` | `add.sb` | `orrr` | `m1` | accept | no | — |
| `add.si_riii_rb` | `add.si` | `riii` | `m1` | accept | no | — |
| `add.si_riii_rd` | `add.si` | `riii` | `m1` | accept | no | — |
| `add.so_rrrr_rd` | `add.so` | `rrrr` | `m1` | accept | no | — |
| `add.st_orrr_rd` | `add.st` | `orrr` | `m1` | accept | no | — |
| `add.sw_orrr_rd` | `add.sw` | `orrr` | `m1` | accept | no | — |
| `add.ub_orrr_rd` | `add.ub` | `orrr` | `m1` | accept | no | — |
| `add.uo_rrrr_rd` | `add.uo` | `rrrr` | `m1` | accept | no | — |
| `add.ut_orrr_rd` | `add.ut` | `orrr` | `m1` | accept | no | — |
| `add.uw_orrr_rd` | `add.uw` | `orrr` | `m1` | accept | no | — |
| `aip.si_riii_rb` | `aip.si` | `riii` | `m1` | accept | no | — |
| `and.o_orrr_rd` | `and.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:412:and_o;pat:DADAOCodeGen.td.patch:735:and_o |
| `andn.w_rwii_rb` | `andn.w` | `rwii` | `m1` | accept | no | — |
| `andn.w_rwii_rd` | `andn.w` | `rwii` | `m1` | accept | no | — |
| `br.eq_rrii_rd` | `br.eq` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:583:br_eq_rd |
| `br.n_riii_rd` | `br.n` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:577:br_n_rd |
| `br.ne_rrii_rd` | `br.ne` | `rrii` | `m1` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2454:br_ne_rd;pat:DADAOCodeGen.td.patch:584:br_ne_rd |
| `br.nn_riii_rd` | `br.nn` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:578:br_nn_rd |
| `br.np_riii_rd` | `br.np` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:580:br_np_rd |
| `br.nz_riii_rb` | `br.nz` | `riii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:718:br_nz_rb |
| `br.nz_riii_rd` | `br.nz` | `riii` | `m1` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2465:br_nz_rd;pat:DADAOCodeGen.td.patch:576:br_nz_rd |
| `br.p_riii_rd` | `br.p` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:579:br_p_rd |
| `br.z_riii_rb` | `br.z` | `riii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:717:br_z_rb |
| `br.z_riii_rd` | `br.z` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:575:br_z_rd |
| `call_iiii_ra` | `call` | `iiii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:605:call_iiii |
| `call_rrii_ra` | `call` | `rrii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:605:call_rrii |
| `cfx2rc_crrr_cfx` | `cfx2rc` | `crrr` | `m1` | accept | no | — |
| `cfx2rd_crrr_cfx` | `cfx2rd` | `crrr` | `m1` | accept | no | — |
| `cfxld_crii_cfx` | `cfxld` | `crii` | `excluded` | reject | no | — |
| `cfxst_crii_cfx` | `cfxst` | `crii` | `excluded` | reject | no | — |
| `clmul.o_rrrr_rd` | `clmul.o` | `rrrr` | `m9` | accept | no | — |
| `cmp.sb_orrr_rd` | `cmp.sb` | `orrr` | `m1` | accept | no | — |
| `cmp.si_rrii_rd` | `cmp.si` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:564:cmp_si_rd;pat:DADAOCodeGen.td.patch:731:cmp_si_rd;pat:DADAOCodeGen.td.patch:733:cmp_si_rd;pat:DADAOCodeGen.td.patch:735:cmp_si_rd;pat:DADAOCodeGen.td.patch:739:cmp_si_rd |
| `cmp.so_orrr_rd` | `cmp.so` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:563:cmp_so |
| `cmp.st_orrr_rd` | `cmp.st` | `orrr` | `m1` | accept | no | — |
| `cmp.sw_orrr_rd` | `cmp.sw` | `orrr` | `m1` | accept | no | — |
| `cmp.ub_orrr_rd` | `cmp.ub` | `orrr` | `m1` | accept | no | — |
| `cmp.ui_rrii_rd` | `cmp.ui` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:572:cmp_ui_rd |
| `cmp.uo_orrr_dbb` | `cmp.uo` | `orrr` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:703:cmp_uo_dbb |
| `cmp.uo_orrr_rd` | `cmp.uo` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:571:cmp_uo |
| `cmp.ut_orrr_rd` | `cmp.ut` | `orrr` | `m1` | accept | no | — |
| `cmp.uw_orrr_rd` | `cmp.uw` | `orrr` | `m1` | accept | no | — |
| `cs.eq_rrrr_rd` | `cs.eq` | `rrrr` | `m1` | accept | no | — |
| `cs.n_rrrr_rd` | `cs.n` | `rrrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:590:cs_n_rd |
| `cs.n_rrrr_rf` | `cs.n` | `rrrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:600:cs_n_rrrr_rf;pat:DADAOCodeGen.td.patch:606:cs_n_rrrr_rf;pat-args:DADAOCodeGen.td.patch:745:cs_n_rrrr_rf;pat-args:DADAOCodeGen.td.patch:748:cs_n_rrrr_rf |
| `cs.ne_rrrr_rd` | `cs.ne` | `rrrr` | `m1` | accept | no | — |
| `cs.p_rrrr_rd` | `cs.p` | `rrrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:592:cs_p_rd;pat:DADAOCodeGen.td.patch:735:cs_p_rd;pat:DADAOCodeGen.td.patch:739:cs_p_rd |
| `cs.p_rrrr_rf` | `cs.p` | `rrrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:604:cs_p_rrrr_rf;pat:DADAOCodeGen.td.patch:610:cs_p_rrrr_rf;pat-args:DADAOCodeGen.td.patch:746:cs_p_rrrr_rf;pat-args:DADAOCodeGen.td.patch:749:cs_p_rrrr_rf |
| `cs.z_rrrr_rd` | `cs.z` | `rrrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:591:cs_z_rd;pat:DADAOCodeGen.td.patch:736:cs_z_rd;pat:DADAOCodeGen.td.patch:740:cs_z_rd |
| `cs.z_rrrr_rf` | `cs.z` | `rrrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:602:cs_z_rrrr_rf;pat:DADAOCodeGen.td.patch:608:cs_z_rrrr_rf;pat-args:DADAOCodeGen.td.patch:745:cs_z_rrrr_rf;pat-args:DADAOCodeGen.td.patch:748:cs_z_rrrr_rf |
| `ctlz_orri_rd` | `ctlz` | `orri` | `m8` | accept | no | — |
| `ctpop_orri_rd` | `ctpop` | `orri` | `m8` | accept | no | — |
| `cttz_orri_rd` | `cttz` | `orri` | `m8` | accept | no | — |
| `div.sb_orrr_rd` | `div.sb` | `orrr` | `m1` | accept | no | — |
| `div.so_orrr_rd` | `div.so` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:453:div_so |
| `div.st_orrr_rd` | `div.st` | `orrr` | `m1` | accept | no | — |
| `div.sw_orrr_rd` | `div.sw` | `orrr` | `m1` | accept | no | — |
| `div.ub_orrr_rd` | `div.ub` | `orrr` | `m1` | accept | no | — |
| `div.uo_orrr_rd` | `div.uo` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:452:div_uo |
| `div.ut_orrr_rd` | `div.ut` | `orrr` | `m1` | accept | no | — |
| `div.uw_orrr_rd` | `div.uw` | `orrr` | `m1` | accept | no | — |
| `escape_ciii_cfx` | `escape` | `ciii` | `m1` | accept | no | — |
| `ext.so_orri_rd` | `ext.so` | `orri` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:472:ext_so_orri;pat:DADAOCodeGen.td.patch:473:ext_so_orri;pat:DADAOCodeGen.td.patch:474:ext_so_orri;pat:DADAOCodeGen.td.patch:479:ext_so_orri |
| `ext.so_orrr_rd` | `ext.so` | `orrr` | `m1` | accept | no | — |
| `ext.uo_orri_rd` | `ext.uo` | `orri` | `m1` | accept | no | — |
| `ext.uo_orrr_rd` | `ext.uo` | `orrr` | `m1` | accept | no | — |
| `fence_oiii_imm` | `fence` | `oiii` | `excluded` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:662:fence |
| `fo2fo_orri_rf` | `fo2fo` | `orri` | `fp` | accept | no | — |
| `fo2ft_orri_rf` | `fo2ft` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:764:fo2ft_orri_rf |
| `fo2io_orri_rf` | `fo2io` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:770:fo2io_orri_rf |
| `fo2it_orri_rf` | `fo2it` | `orri` | `fp` | accept | no | — |
| `fo2uo_orri_rf` | `fo2uo` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:772:fo2uo_orri_rf |
| `fo2ut_orri_rf` | `fo2ut` | `orri` | `fp` | accept | no | — |
| `foadd_orrr_rf` | `foadd` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:625:foadd_orrr_rf |
| `focls_orri_rf` | `focls` | `orri` | `fp` | accept | no | — |
| `fodiv_orrr_rf` | `fodiv` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:628:fodiv_orrr_rf |
| `fomax_orrr_rf` | `fomax` | `orrr` | `excluded` | reject | no | — |
| `fomin_orrr_rf` | `fomin` | `orrr` | `excluded` | reject | no | — |
| `fomul_orrr_rf` | `fomul` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:627:fomul_orrr_rf |
| `foqcmp_orrr_rf` | `foqcmp` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:689:foqcmp_orrr_rf;pat-args:DADAOCodeGen.td.patch:745:foqcmp_orrr_rf |
| `forem_orrr_rf` | `forem` | `orrr` | `fp` | accept | no | — |
| `fornd_orri_rf` | `fornd` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:673:fornd_orri_rf;pat:DADAOCodeGen.td.patch:674:fornd_orri_rf;pat:DADAOCodeGen.td.patch:675:fornd_orri_rf;pat:DADAOCodeGen.td.patch:676:fornd_orri_rf;pat:DADAOCodeGen.td.patch:677:fornd_orri_rf;pat:DADAOCodeGen.td.patch:678:fornd_orri_rf;pat:DADAOCodeGen.td.patch:679:fornd_orri_rf |
| `foroot_orri_rf` | `foroot` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:630:foroot_orri_rf |
| `fosclb_orrr_rf` | `fosclb` | `orrr` | `fp` | accept | no | — |
| `foscmp_orrr_rf` | `foscmp` | `orrr` | `fp` | accept | no | — |
| `fosgnj_orrr_rf` | `fosgnj` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:641:fosgnj_orrr_rf;pat:DADAOCodeGen.td.patch:643:fosgnj_orrr_rf |
| `fosgnn_orrr_rf` | `fosgnn` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:632:fosgnn_orrr_rf |
| `fosub_orrr_rf` | `fosub` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:626:fosub_orrr_rf |
| `ft2fo_orri_rf` | `ft2fo` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:763:ft2fo_orri_rf |
| `ft2ft_orri_rf` | `ft2ft` | `orri` | `fp` | accept | no | — |
| `ft2io_orri_rf` | `ft2io` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:771:ft2io_orri_rf |
| `ft2it_orri_rf` | `ft2it` | `orri` | `fp` | accept | no | — |
| `ft2uo_orri_rf` | `ft2uo` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:773:ft2uo_orri_rf |
| `ft2ut_orri_rf` | `ft2ut` | `orri` | `fp` | accept | no | — |
| `ftadd_orrr_rf` | `ftadd` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:646:ftadd_orrr_rf |
| `ftcls_orri_rf` | `ftcls` | `orri` | `fp` | accept | no | — |
| `ftdiv_orrr_rf` | `ftdiv` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:649:ftdiv_orrr_rf |
| `ftmax_orrr_rf` | `ftmax` | `orrr` | `excluded` | reject | no | — |
| `ftmin_orrr_rf` | `ftmin` | `orrr` | `excluded` | reject | no | — |
| `ftmul_orrr_rf` | `ftmul` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:648:ftmul_orrr_rf |
| `ftqcmp_orrr_rf` | `ftqcmp` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:690:ftqcmp_orrr_rf;pat-args:DADAOCodeGen.td.patch:748:ftqcmp_orrr_rf |
| `ftrem_orrr_rf` | `ftrem` | `orrr` | `fp` | accept | no | — |
| `ftrnd_orri_rf` | `ftrnd` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:680:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:681:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:682:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:683:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:684:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:685:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:686:ftrnd_orri_rf |
| `ftroot_orri_rf` | `ftroot` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:650:ftroot_orri_rf |
| `ftsclb_orrr_rf` | `ftsclb` | `orrr` | `fp` | accept | no | — |
| `ftscmp_orrr_rf` | `ftscmp` | `orrr` | `fp` | accept | no | — |
| `ftsgnj_orrr_rf` | `ftsgnj` | `orrr` | `fp` | accept | no | — |
| `ftsgnn_orrr_rf` | `ftsgnn` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:651:ftsgnn_orrr_rf |
| `ftsub_orrr_rf` | `ftsub` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:647:ftsub_orrr_rf |
| `io2fo_orri_rf` | `io2fo` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:777:io2fo_orri_rf |
| `io2ft_orri_rf` | `io2ft` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:778:io2ft_orri_rf |
| `it2fo_orri_rf` | `it2fo` | `orri` | `fp` | accept | no | — |
| `it2ft_orri_rf` | `it2ft` | `orri` | `fp` | accept | no | — |
| `jump_iiii_rb` | `jump` | `iiii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:650:tailjmp_iiii;pat:DADAOCodeGen.td.patch:613:jump_iiii |
| `jump_rrii_rb` | `jump` | `rrii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:538:jump_rrii;isel-cpp:DADAOISelDAGToDAG.cpp.patch:560:jump_rrii;isel-cpp:DADAOISelDAGToDAG.cpp.patch:650:tailjmp_rrii |
| `ld.o_rrii_ra` | `ld.o` | `rrii` | `m1` | accept | no | — |
| `ld.o_rrii_rb` | `ld.o` | `rrii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:175:ld_o_rb;isel-cpp:DADAOISelDAGToDAG.cpp.patch:531:ld_o_rb |
| `ld.o_rrii_rd` | `ld.o` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:521:ld_o_rd |
| `ld.o_rrii_rf` | `ld.o` | `rrii` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:753:ld_o_rrii_rf |
| `ld.sb_rrii_rd` | `ld.sb` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:528:ld_sb_rd |
| `ld.st_rrii_rd` | `ld.st` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:540:ld_st_rd |
| `ld.sw_rrii_rd` | `ld.sw` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:534:ld_sw_rd |
| `ld.t_rrii_rf` | `ld.t` | `rrii` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:757:ld_t_rrii_rf |
| `ld.ub_rrii_rd` | `ld.ub` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:526:ld_ub_rd;pat:DADAOCodeGen.td.patch:527:ld_ub_rd |
| `ld.ut_rrii_rd` | `ld.ut` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:538:ld_ut_rd;pat:DADAOCodeGen.td.patch:539:ld_ut_rd |
| `ld.uw_rrii_rd` | `ld.uw` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:532:ld_uw_rd;pat:DADAOCodeGen.td.patch:533:ld_uw_rd |
| `ldm.o_rrri_ra` | `ldm.o` | `rrri` | `m1` | accept | no | — |
| `ldm.o_rrri_rb` | `ldm.o` | `rrri` | `m1` | accept | no | — |
| `ldm.o_rrri_rd` | `ldm.o` | `rrri` | `m1` | accept | no | — |
| `ldm.o_rrri_rf` | `ldm.o` | `rrri` | `fp` | accept | no | — |
| `ldm.sb_rrri_rd` | `ldm.sb` | `rrri` | `m1` | accept | no | — |
| `ldm.st_rrri_rd` | `ldm.st` | `rrri` | `m1` | accept | no | — |
| `ldm.sw_rrri_rd` | `ldm.sw` | `rrri` | `m1` | accept | no | — |
| `ldm.t_rrri_rf` | `ldm.t` | `rrri` | `fp` | accept | no | — |
| `ldm.ub_rrri_rd` | `ldm.ub` | `rrri` | `m1` | accept | no | — |
| `ldm.ut_rrri_rd` | `ldm.ut` | `rrri` | `m1` | accept | no | — |
| `ldm.uw_rrri_rd` | `ldm.uw` | `rrri` | `m1` | accept | no | — |
| `lr.b.an_orrr_rd` | `lr.b.an` | `orrr` | `excluded` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2387:lr_b_an |
| `lr.b.ar_orrr_rd` | `lr.b.ar` | `orrr` | `excluded` | accept | no | — |
| `lr.b.nn_orrr_rd` | `lr.b.nn` | `orrr` | `excluded` | accept | no | — |
| `lr.o.an_orrr_rd` | `lr.o.an` | `orrr` | `excluded` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2399:lr_o_an |
| `lr.o.ar_orrr_rd` | `lr.o.ar` | `orrr` | `excluded` | accept | no | — |
| `lr.o.nn_orrr_rd` | `lr.o.nn` | `orrr` | `excluded` | accept | no | — |
| `lr.t.an_orrr_rd` | `lr.t.an` | `orrr` | `excluded` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2395:lr_t_an |
| `lr.t.ar_orrr_rd` | `lr.t.ar` | `orrr` | `excluded` | accept | no | — |
| `lr.t.nn_orrr_rd` | `lr.t.nn` | `orrr` | `excluded` | accept | no | — |
| `lr.w.an_orrr_rd` | `lr.w.an` | `orrr` | `excluded` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2391:lr_w_an |
| `lr.w.ar_orrr_rd` | `lr.w.ar` | `orrr` | `excluded` | accept | no | — |
| `lr.w.nn_orrr_rd` | `lr.w.nn` | `orrr` | `excluded` | accept | no | — |
| `mul.sb_orrr_rd` | `mul.sb` | `orrr` | `m1` | accept | no | — |
| `mul.so_rrrr_rd` | `mul.so` | `rrrr` | `m1` | accept | no | — |
| `mul.st_orrr_rd` | `mul.st` | `orrr` | `m1` | accept | no | — |
| `mul.sw_orrr_rd` | `mul.sw` | `orrr` | `m1` | accept | no | — |
| `mul.ub_orrr_rd` | `mul.ub` | `orrr` | `m1` | accept | no | — |
| `mul.uo_rrrr_rd` | `mul.uo` | `rrrr` | `m1` | accept | no | — |
| `mul.ut_orrr_rd` | `mul.ut` | `orrr` | `m1` | accept | no | — |
| `mul.uw_orrr_rd` | `mul.uw` | `orrr` | `m1` | accept | no | — |
| `or.o_orrr_rd` | `or.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:413:or_o;pat:DADAOCodeGen.td.patch:739:or_o |
| `or.w_rwii_rb` | `or.w` | `rwii` | `m1` | accept | no | — |
| `or.w_rwii_rd` | `or.w` | `rwii` | `m1` | accept | no | — |
| `ra2rd_orri_ra` | `ra2rd` | `orri` | `m1` | accept | no | — |
| `rb2rb_orri_rb` | `rb2rb` | `orri` | `m1` | accept | no | — |
| `rb2rd_orri_rb` | `rb2rd` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:472:rb2rd |
| `rd2ra_orri_ra` | `rd2ra` | `orri` | `m1` | accept | no | — |
| `rd2rb_orri_rb` | `rd2rb` | `orri` | `m1` | accept | no | — |
| `rd2rd_orri_rd` | `rd2rd` | `orri` | `m1` | accept | no | — |
| `rd2rf_orri_rf` | `rd2rf` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:324:rd2rf_orri_rf;pat:DADAOCodeGen.td.patch:643:rd2rf_orri_rf;pat:DADAOCodeGen.td.patch:788:rd2rf_orri_rf |
| `rem.sb_orrr_rd` | `rem.sb` | `orrr` | `m1` | accept | no | — |
| `rem.so_orrr_rd` | `rem.so` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:455:rem_so |
| `rem.st_orrr_rd` | `rem.st` | `orrr` | `m1` | accept | no | — |
| `rem.sw_orrr_rd` | `rem.sw` | `orrr` | `m1` | accept | no | — |
| `rem.ub_orrr_rd` | `rem.ub` | `orrr` | `m1` | accept | no | — |
| `rem.uo_orrr_rd` | `rem.uo` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:454:rem_uo |
| `rem.ut_orrr_rd` | `rem.ut` | `orrr` | `m1` | accept | no | — |
| `rem.uw_orrr_rd` | `rem.uw` | `orrr` | `m1` | accept | no | — |
| `ret_riii_ra` | `ret` | `riii` | `m1` | accept | no | — |
| `rev.b_orri_rd` | `rev.b` | `orri` | `m8` | accept | no | — |
| `rev.o_orri_rd` | `rev.o` | `orri` | `m8` | accept | no | — |
| `rev.t_orri_rd` | `rev.t` | `orri` | `m8` | accept | no | — |
| `rev.w_orri_rd` | `rev.w` | `orri` | `m8` | accept | no | — |
| `rf2rd_orri_rf` | `rf2rd` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:789:rf2rd_orri_rf |
| `rol.b_orri_rd` | `rol.b` | `orri` | `m9` | accept | no | — |
| `rol.b_orrr_rd` | `rol.b` | `orrr` | `m9` | accept | no | — |
| `rol.o_orri_rd` | `rol.o` | `orri` | `m9` | accept | yes | pat:DADAOCodeGen.td.patch:446:rol_o_orri |
| `rol.o_orrr_rd` | `rol.o` | `orrr` | `m9` | accept | yes | pat:DADAOCodeGen.td.patch:447:rol_o_orrr |
| `rol.t_orri_rd` | `rol.t` | `orri` | `m9` | accept | no | — |
| `rol.t_orrr_rd` | `rol.t` | `orrr` | `m9` | accept | no | — |
| `rol.w_orri_rd` | `rol.w` | `orri` | `m9` | accept | no | — |
| `rol.w_orrr_rd` | `rol.w` | `orrr` | `m9` | accept | no | — |
| `sc.b.ar_orrr_rd` | `sc.b.ar` | `orrr` | `excluded` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2388:sc_b_ar |
| `sc.b.nn_orrr_rd` | `sc.b.nn` | `orrr` | `excluded` | accept | no | — |
| `sc.b.nr_orrr_rd` | `sc.b.nr` | `orrr` | `excluded` | accept | no | — |
| `sc.o.ar_orrr_rd` | `sc.o.ar` | `orrr` | `excluded` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2400:sc_o_ar |
| `sc.o.nn_orrr_rd` | `sc.o.nn` | `orrr` | `excluded` | accept | no | — |
| `sc.o.nr_orrr_rd` | `sc.o.nr` | `orrr` | `excluded` | accept | no | — |
| `sc.t.ar_orrr_rd` | `sc.t.ar` | `orrr` | `excluded` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2396:sc_t_ar |
| `sc.t.nn_orrr_rd` | `sc.t.nn` | `orrr` | `excluded` | accept | no | — |
| `sc.t.nr_orrr_rd` | `sc.t.nr` | `orrr` | `excluded` | accept | no | — |
| `sc.w.ar_orrr_rd` | `sc.w.ar` | `orrr` | `excluded` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2392:sc_w_ar |
| `sc.w.nn_orrr_rd` | `sc.w.nn` | `orrr` | `excluded` | accept | no | — |
| `sc.w.nr_orrr_rd` | `sc.w.nr` | `orrr` | `excluded` | accept | no | — |
| `set.ow_rwii_rd` | `set.ow` | `rwii` | `m1` | accept | no | — |
| `set.w_rwii_rf` | `set.w` | `rwii` | `fp` | accept | no | — |
| `set.zw_rwii_rb` | `set.zw` | `rwii` | `m1` | accept | no | — |
| `set.zw_rwii_rd` | `set.zw` | `rwii` | `m1` | accept | no | — |
| `shl.b_orri_rd` | `shl.b` | `orri` | `m1` | accept | no | — |
| `shl.b_orrr_rd` | `shl.b` | `orrr` | `m1` | accept | no | — |
| `shl.o_orri_rd` | `shl.o` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:527:shl_o_orri |
| `shl.o_orrr_rd` | `shl.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:436:shl_o_orrr |
| `shl.t_orri_rd` | `shl.t` | `orri` | `m1` | accept | no | — |
| `shl.t_orrr_rd` | `shl.t` | `orrr` | `m1` | accept | no | — |
| `shl.w_orri_rd` | `shl.w` | `orri` | `m1` | accept | no | — |
| `shl.w_orrr_rd` | `shl.w` | `orrr` | `m1` | accept | no | — |
| `shr.sb_orri_rd` | `shr.sb` | `orri` | `m1` | accept | no | — |
| `shr.sb_orrr_rd` | `shr.sb` | `orrr` | `m1` | accept | no | — |
| `shr.so_orri_rd` | `shr.so` | `orri` | `m1` | accept | no | — |
| `shr.so_orrr_rd` | `shr.so` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:438:shr_so_orrr |
| `shr.st_orri_rd` | `shr.st` | `orri` | `m1` | accept | no | — |
| `shr.st_orrr_rd` | `shr.st` | `orrr` | `m1` | accept | no | — |
| `shr.sw_orri_rd` | `shr.sw` | `orri` | `m1` | accept | no | — |
| `shr.sw_orrr_rd` | `shr.sw` | `orrr` | `m1` | accept | no | — |
| `shr.ub_orri_rd` | `shr.ub` | `orri` | `m1` | accept | no | — |
| `shr.ub_orrr_rd` | `shr.ub` | `orrr` | `m1` | accept | no | — |
| `shr.uo_orri_rd` | `shr.uo` | `orri` | `m1` | accept | no | — |
| `shr.uo_orrr_rd` | `shr.uo` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:437:shr_uo_orrr |
| `shr.ut_orri_rd` | `shr.ut` | `orri` | `m1` | accept | no | — |
| `shr.ut_orrr_rd` | `shr.ut` | `orrr` | `m1` | accept | no | — |
| `shr.uw_orri_rd` | `shr.uw` | `orri` | `m1` | accept | no | — |
| `shr.uw_orrr_rd` | `shr.uw` | `orrr` | `m1` | accept | no | — |
| `st.b_rrii_rd` | `st.b` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:529:st_b_rd |
| `st.o_rrii_ra` | `st.o` | `rrii` | `m1` | accept | no | — |
| `st.o_rrii_rb` | `st.o` | `rrii` | `m1` | accept | no | — |
| `st.o_rrii_rd` | `st.o` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:522:st_o_rd |
| `st.o_rrii_rf` | `st.o` | `rrii` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:755:st_o_rrii_rf |
| `st.t_rrii_rd` | `st.t` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:541:st_t_rd |
| `st.t_rrii_rf` | `st.t` | `rrii` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:759:st_t_rrii_rf |
| `st.w_rrii_rd` | `st.w` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:535:st_w_rd |
| `stm.b_rrri_rd` | `stm.b` | `rrri` | `m1` | accept | no | — |
| `stm.o_rrri_ra` | `stm.o` | `rrri` | `m1` | accept | no | — |
| `stm.o_rrri_rb` | `stm.o` | `rrri` | `m1` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:1071:stm_o_rb |
| `stm.o_rrri_rd` | `stm.o` | `rrri` | `m1` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:1069:stm_o_rd |
| `stm.o_rrri_rf` | `stm.o` | `rrri` | `fp` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:1073:stm_o_rrri_rf |
| `stm.t_rrri_rd` | `stm.t` | `rrri` | `m1` | accept | no | — |
| `stm.t_rrri_rf` | `stm.t` | `rrri` | `fp` | accept | no | — |
| `stm.w_rrri_rd` | `stm.w` | `rrri` | `m1` | accept | no | — |
| `sub.o_orrr_bbd` | `sub.o` | `orrr` | `m1` | accept | no | — |
| `sub.o_orrr_dbb` | `sub.o` | `orrr` | `m3` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:207:sub_o_dbb |
| `sub.sb_orrr_rd` | `sub.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:427:sub_sb |
| `sub.so_rrrr_rd` | `sub.so` | `rrrr` | `m1` | accept | no | — |
| `sub.st_orrr_rd` | `sub.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:429:sub_st |
| `sub.sw_orrr_rd` | `sub.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:428:sub_sw |
| `sub.ub_orrr_rd` | `sub.ub` | `orrr` | `m1` | accept | no | — |
| `sub.uo_rrrr_rd` | `sub.uo` | `rrrr` | `m1` | accept | no | — |
| `sub.ut_orrr_rd` | `sub.ut` | `orrr` | `m1` | accept | no | — |
| `sub.uw_orrr_rd` | `sub.uw` | `orrr` | `m1` | accept | no | — |
| `swym_oiii_imm` | `swym` | `oiii` | `m1` | accept | no | — |
| `trap_ciii_cfx` | `trap` | `ciii` | `m1` | accept | no | — |
| `uo2fo_orri_rf` | `uo2fo` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:779:uo2fo_orri_rf |
| `uo2ft_orri_rf` | `uo2ft` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:780:uo2ft_orri_rf |
| `ut2fo_orri_rf` | `ut2fo` | `orri` | `fp` | accept | no | — |
| `ut2ft_orri_rf` | `ut2ft` | `orri` | `fp` | accept | no | — |
| `xnor.o_orrr_rd` | `xnor.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:419:xnor_o |
| `xor.o_orrr_rd` | `xor.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:414:xor_o |

## 3. 缺口汇总（未被 ISel 使用，161 条）

候选优化面（供后续里程碑参考）。按性质分四类（现场统计）：

1. **真缺口·候补优化面**（`scope != excluded`，且后端 ISel/post-ISel 均未引用，且非汇编层/特权族）：**111** 条 —— ISA 有、后端一次都没发射，最有价值。
2. **真缺口·汇编层/特权族**（同上但 `format ∈ {crrr, ciii, crii}` 或助记符 ∈ {fence, swym}，机械判据）：**5** 条 —— 经 cfx 访问/内联汇编/占位语义使用，不经 ISel 选入属预期。
3. **仅 post-ISel 引用**（伪指令展开/帧/寄存器分配会发射，非 ISel 选入）：**23** 条。
4. **`scope: excluded` 未实现**（汇编器拒绝、执行 ILLI）：**22** 条 —— 不在本期范围。

### 3.1 真缺口·候补优化面（111 条）

| id | mnemonic | format | scope |
|---|---|---|---|
| `add.sb_orrr_rd` | `add.sb` | `orrr` | `m1` |
| `add.so_rrrr_rd` | `add.so` | `rrrr` | `m1` |
| `add.st_orrr_rd` | `add.st` | `orrr` | `m1` |
| `add.sw_orrr_rd` | `add.sw` | `orrr` | `m1` |
| `add.ub_orrr_rd` | `add.ub` | `orrr` | `m1` |
| `add.ut_orrr_rd` | `add.ut` | `orrr` | `m1` |
| `add.uw_orrr_rd` | `add.uw` | `orrr` | `m1` |
| `andn.w_rwii_rb` | `andn.w` | `rwii` | `m1` |
| `cmp.sb_orrr_rd` | `cmp.sb` | `orrr` | `m1` |
| `cmp.st_orrr_rd` | `cmp.st` | `orrr` | `m1` |
| `cmp.sw_orrr_rd` | `cmp.sw` | `orrr` | `m1` |
| `cmp.ub_orrr_rd` | `cmp.ub` | `orrr` | `m1` |
| `cmp.ut_orrr_rd` | `cmp.ut` | `orrr` | `m1` |
| `cmp.uw_orrr_rd` | `cmp.uw` | `orrr` | `m1` |
| `cs.eq_rrrr_rd` | `cs.eq` | `rrrr` | `m1` |
| `cs.ne_rrrr_rd` | `cs.ne` | `rrrr` | `m1` |
| `ctlz_orri_rd` | `ctlz` | `orri` | `m8` |
| `ctpop_orri_rd` | `ctpop` | `orri` | `m8` |
| `cttz_orri_rd` | `cttz` | `orri` | `m8` |
| `div.sb_orrr_rd` | `div.sb` | `orrr` | `m1` |
| `div.st_orrr_rd` | `div.st` | `orrr` | `m1` |
| `div.sw_orrr_rd` | `div.sw` | `orrr` | `m1` |
| `div.ub_orrr_rd` | `div.ub` | `orrr` | `m1` |
| `div.ut_orrr_rd` | `div.ut` | `orrr` | `m1` |
| `div.uw_orrr_rd` | `div.uw` | `orrr` | `m1` |
| `ext.so_orrr_rd` | `ext.so` | `orrr` | `m1` |
| `ext.uo_orri_rd` | `ext.uo` | `orri` | `m1` |
| `ext.uo_orrr_rd` | `ext.uo` | `orrr` | `m1` |
| `fo2it_orri_rf` | `fo2it` | `orri` | `fp` |
| `fo2ut_orri_rf` | `fo2ut` | `orri` | `fp` |
| `focls_orri_rf` | `focls` | `orri` | `fp` |
| `forem_orrr_rf` | `forem` | `orrr` | `fp` |
| `fosclb_orrr_rf` | `fosclb` | `orrr` | `fp` |
| `foscmp_orrr_rf` | `foscmp` | `orrr` | `fp` |
| `ft2ft_orri_rf` | `ft2ft` | `orri` | `fp` |
| `ft2it_orri_rf` | `ft2it` | `orri` | `fp` |
| `ft2ut_orri_rf` | `ft2ut` | `orri` | `fp` |
| `ftcls_orri_rf` | `ftcls` | `orri` | `fp` |
| `ftrem_orrr_rf` | `ftrem` | `orrr` | `fp` |
| `ftsclb_orrr_rf` | `ftsclb` | `orrr` | `fp` |
| `ftscmp_orrr_rf` | `ftscmp` | `orrr` | `fp` |
| `ftsgnj_orrr_rf` | `ftsgnj` | `orrr` | `fp` |
| `it2fo_orri_rf` | `it2fo` | `orri` | `fp` |
| `it2ft_orri_rf` | `it2ft` | `orri` | `fp` |
| `ld.o_rrii_ra` | `ld.o` | `rrii` | `m1` |
| `ldm.o_rrri_ra` | `ldm.o` | `rrri` | `m1` |
| `ldm.o_rrri_rf` | `ldm.o` | `rrri` | `fp` |
| `ldm.sb_rrri_rd` | `ldm.sb` | `rrri` | `m1` |
| `ldm.st_rrri_rd` | `ldm.st` | `rrri` | `m1` |
| `ldm.sw_rrri_rd` | `ldm.sw` | `rrri` | `m1` |
| `ldm.t_rrri_rf` | `ldm.t` | `rrri` | `fp` |
| `ldm.ub_rrri_rd` | `ldm.ub` | `rrri` | `m1` |
| `ldm.ut_rrri_rd` | `ldm.ut` | `rrri` | `m1` |
| `ldm.uw_rrri_rd` | `ldm.uw` | `rrri` | `m1` |
| `mul.sb_orrr_rd` | `mul.sb` | `orrr` | `m1` |
| `mul.st_orrr_rd` | `mul.st` | `orrr` | `m1` |
| `mul.sw_orrr_rd` | `mul.sw` | `orrr` | `m1` |
| `mul.ub_orrr_rd` | `mul.ub` | `orrr` | `m1` |
| `mul.ut_orrr_rd` | `mul.ut` | `orrr` | `m1` |
| `mul.uw_orrr_rd` | `mul.uw` | `orrr` | `m1` |
| `ra2rd_orri_ra` | `ra2rd` | `orri` | `m1` |
| `rd2ra_orri_ra` | `rd2ra` | `orri` | `m1` |
| `rem.sb_orrr_rd` | `rem.sb` | `orrr` | `m1` |
| `rem.st_orrr_rd` | `rem.st` | `orrr` | `m1` |
| `rem.sw_orrr_rd` | `rem.sw` | `orrr` | `m1` |
| `rem.ub_orrr_rd` | `rem.ub` | `orrr` | `m1` |
| `rem.ut_orrr_rd` | `rem.ut` | `orrr` | `m1` |
| `rem.uw_orrr_rd` | `rem.uw` | `orrr` | `m1` |
| `rev.b_orri_rd` | `rev.b` | `orri` | `m8` |
| `rev.o_orri_rd` | `rev.o` | `orri` | `m8` |
| `rev.t_orri_rd` | `rev.t` | `orri` | `m8` |
| `rev.w_orri_rd` | `rev.w` | `orri` | `m8` |
| `rol.b_orri_rd` | `rol.b` | `orri` | `m9` |
| `rol.b_orrr_rd` | `rol.b` | `orrr` | `m9` |
| `rol.t_orri_rd` | `rol.t` | `orri` | `m9` |
| `rol.t_orrr_rd` | `rol.t` | `orrr` | `m9` |
| `rol.w_orri_rd` | `rol.w` | `orri` | `m9` |
| `rol.w_orrr_rd` | `rol.w` | `orrr` | `m9` |
| `set.w_rwii_rf` | `set.w` | `rwii` | `fp` |
| `shl.b_orri_rd` | `shl.b` | `orri` | `m1` |
| `shl.b_orrr_rd` | `shl.b` | `orrr` | `m1` |
| `shl.t_orri_rd` | `shl.t` | `orri` | `m1` |
| `shl.t_orrr_rd` | `shl.t` | `orrr` | `m1` |
| `shl.w_orri_rd` | `shl.w` | `orri` | `m1` |
| `shl.w_orrr_rd` | `shl.w` | `orrr` | `m1` |
| `shr.sb_orri_rd` | `shr.sb` | `orri` | `m1` |
| `shr.sb_orrr_rd` | `shr.sb` | `orrr` | `m1` |
| `shr.so_orri_rd` | `shr.so` | `orri` | `m1` |
| `shr.st_orri_rd` | `shr.st` | `orri` | `m1` |
| `shr.st_orrr_rd` | `shr.st` | `orrr` | `m1` |
| `shr.sw_orri_rd` | `shr.sw` | `orri` | `m1` |
| `shr.sw_orrr_rd` | `shr.sw` | `orrr` | `m1` |
| `shr.ub_orri_rd` | `shr.ub` | `orri` | `m1` |
| `shr.ub_orrr_rd` | `shr.ub` | `orrr` | `m1` |
| `shr.uo_orri_rd` | `shr.uo` | `orri` | `m1` |
| `shr.ut_orri_rd` | `shr.ut` | `orri` | `m1` |
| `shr.ut_orrr_rd` | `shr.ut` | `orrr` | `m1` |
| `shr.uw_orri_rd` | `shr.uw` | `orri` | `m1` |
| `shr.uw_orrr_rd` | `shr.uw` | `orrr` | `m1` |
| `st.o_rrii_ra` | `st.o` | `rrii` | `m1` |
| `stm.b_rrri_rd` | `stm.b` | `rrri` | `m1` |
| `stm.o_rrri_ra` | `stm.o` | `rrri` | `m1` |
| `stm.t_rrri_rd` | `stm.t` | `rrri` | `m1` |
| `stm.t_rrri_rf` | `stm.t` | `rrri` | `fp` |
| `stm.w_rrri_rd` | `stm.w` | `rrri` | `m1` |
| `sub.o_orrr_bbd` | `sub.o` | `orrr` | `m1` |
| `sub.ub_orrr_rd` | `sub.ub` | `orrr` | `m1` |
| `sub.ut_orrr_rd` | `sub.ut` | `orrr` | `m1` |
| `sub.uw_orrr_rd` | `sub.uw` | `orrr` | `m1` |
| `ut2fo_orri_rf` | `ut2fo` | `orri` | `fp` |
| `ut2ft_orri_rf` | `ut2ft` | `orri` | `fp` |

### 3.2 真缺口·汇编层/特权族（5 条）

| id | mnemonic | format | scope |
|---|---|---|---|
| `cfx2rc_crrr_cfx` | `cfx2rc` | `crrr` | `m1` |
| `cfx2rd_crrr_cfx` | `cfx2rd` | `crrr` | `m1` |
| `escape_ciii_cfx` | `escape` | `ciii` | `m1` |
| `swym_oiii_imm` | `swym` | `oiii` | `m1` |
| `trap_ciii_cfx` | `trap` | `ciii` | `m1` |

### 3.3 仅 post-ISel 引用（23 条）

| id | mnemonic | format | scope |
|---|---|---|---|
| `add.si_riii_rb` | `add.si` | `riii` | `m1` |
| `add.si_riii_rd` | `add.si` | `riii` | `m1` |
| `add.uo_rrrr_rd` | `add.uo` | `rrrr` | `m1` |
| `aip.si_riii_rb` | `aip.si` | `riii` | `m1` |
| `andn.w_rwii_rd` | `andn.w` | `rwii` | `m1` |
| `clmul.o_rrrr_rd` | `clmul.o` | `rrrr` | `m9` |
| `fo2fo_orri_rf` | `fo2fo` | `orri` | `fp` |
| `ldm.o_rrri_rb` | `ldm.o` | `rrri` | `m1` |
| `ldm.o_rrri_rd` | `ldm.o` | `rrri` | `m1` |
| `mul.so_rrrr_rd` | `mul.so` | `rrrr` | `m1` |
| `mul.uo_rrrr_rd` | `mul.uo` | `rrrr` | `m1` |
| `or.w_rwii_rb` | `or.w` | `rwii` | `m1` |
| `or.w_rwii_rd` | `or.w` | `rwii` | `m1` |
| `rb2rb_orri_rb` | `rb2rb` | `orri` | `m1` |
| `rd2rb_orri_rb` | `rd2rb` | `orri` | `m1` |
| `rd2rd_orri_rd` | `rd2rd` | `orri` | `m1` |
| `ret_riii_ra` | `ret` | `riii` | `m1` |
| `set.ow_rwii_rd` | `set.ow` | `rwii` | `m1` |
| `set.zw_rwii_rb` | `set.zw` | `rwii` | `m1` |
| `set.zw_rwii_rd` | `set.zw` | `rwii` | `m1` |
| `st.o_rrii_rb` | `st.o` | `rrii` | `m1` |
| `sub.so_rrrr_rd` | `sub.so` | `rrrr` | `m1` |
| `sub.uo_rrrr_rd` | `sub.uo` | `rrrr` | `m1` |

### 3.4 scope: excluded（未实现）（22 条）

| id | mnemonic | format | scope |
|---|---|---|---|
| `cfxld_crii_cfx` | `cfxld` | `crii` | `excluded` |
| `cfxst_crii_cfx` | `cfxst` | `crii` | `excluded` |
| `fomax_orrr_rf` | `fomax` | `orrr` | `excluded` |
| `fomin_orrr_rf` | `fomin` | `orrr` | `excluded` |
| `ftmax_orrr_rf` | `ftmax` | `orrr` | `excluded` |
| `ftmin_orrr_rf` | `ftmin` | `orrr` | `excluded` |
| `lr.b.ar_orrr_rd` | `lr.b.ar` | `orrr` | `excluded` |
| `lr.b.nn_orrr_rd` | `lr.b.nn` | `orrr` | `excluded` |
| `lr.o.ar_orrr_rd` | `lr.o.ar` | `orrr` | `excluded` |
| `lr.o.nn_orrr_rd` | `lr.o.nn` | `orrr` | `excluded` |
| `lr.t.ar_orrr_rd` | `lr.t.ar` | `orrr` | `excluded` |
| `lr.t.nn_orrr_rd` | `lr.t.nn` | `orrr` | `excluded` |
| `lr.w.ar_orrr_rd` | `lr.w.ar` | `orrr` | `excluded` |
| `lr.w.nn_orrr_rd` | `lr.w.nn` | `orrr` | `excluded` |
| `sc.b.nn_orrr_rd` | `sc.b.nn` | `orrr` | `excluded` |
| `sc.b.nr_orrr_rd` | `sc.b.nr` | `orrr` | `excluded` |
| `sc.o.nn_orrr_rd` | `sc.o.nn` | `orrr` | `excluded` |
| `sc.o.nr_orrr_rd` | `sc.o.nr` | `orrr` | `excluded` |
| `sc.t.nn_orrr_rd` | `sc.t.nn` | `orrr` | `excluded` |
| `sc.t.nr_orrr_rd` | `sc.t.nr` | `orrr` | `excluded` |
| `sc.w.nn_orrr_rd` | `sc.w.nn` | `orrr` | `excluded` |
| `sc.w.nr_orrr_rd` | `sc.w.nr` | `orrr` | `excluded` |

