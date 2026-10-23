# ISA↔后端覆盖矩阵（生成式，两层分列）

> **生成器**：`tools/llvm/gen_isa_coverage.py`（生成物，勿手工编辑；改生成器或真源后重跑）
> **真源**：`contracts/opcodes.yaml`（**266** 条 = `m1` 156 + `fp` 66 + `excluded` 2 + `m3` 1 + `m8` 7 + `m9` 34；计数由脚本现场统计，不写死）
> **重跑**：`python3 tools/llvm/gen_isa_coverage.py`　**门控（反例可失败）**：`python3 tools/llvm/gen_isa_coverage.py --check`
> **机器可读**：`tools/llvm/llvm-isa-backend-matrix.tsv`（同源同批生成）

## 1. 两层口径

### 第①层「汇编器可受理」

逐条记录取**规范操作数形态**（每记录一个合法 shape）喂 `llvm-mc (--triple=dadao-unknown-elf -filetype=obj)`，记 `accept`/`reject`。

- 形态来源：`tools/testcases/generate_lit_vectors.py` 的 `build_case()`（与现有 lit 全量档 `tests/llvm/lit/MC/DADAO-gen/gen-*.s` **同一口径、同一行文本**；本工具不另立操作数拼装逻辑）。
- 受理后**另做编码复核**：由对象 `.text` 取 4 字节大端字，要求「按真源 `(word & mask) == value` 唯一命中本记录」且等于真源派生编码（`L1_encoding = ok / mismatch`）。这一列把第①层钉在真源上，而非只看 `llvm-mc` 自洽。
- 现场统计：`accept` **264** / `reject` **2**；编码复核不符 **0**。
- `scope: excluded` 且后端未实现者（`cfxld`/`cfxst`，现场派生）由汇编器**显式拒绝**（`reject`）；其余 `scope: excluded` 记录（MC 层已受理、执行侧仍 ILLI）与 `tests/llvm/lit/MC/DADAO-gen/gen-excluded.s` 的反例同口径。

### 第②层「ISel 用得上」（机械提取，非人工判读）

对每条记录，取其 `.td` def（由 `(mnemonic, format, op, ha)` 显式 join 真源），在后端补丁树中机械收集引用：

| 证据类型 | 含义 | 采集点 |
|---|---|---|
| `pat` | TableGen `Pat<...>` DAG 体内出现的指令 def 名（自动生成的 ISel 选入表） | `DADAOCodeGen.td.patch` 等 |
| `pat-args` | `def`/`defm` 的 Pat 类实参（含 `multiclass` 经 `defm` 传入的指令） | `DADAOCodeGen.td.patch` |
| `isel-cpp` | `DADAO::<def>` 显式引用（自定义选择器 / lowering 发射） | `DADAOISelDAGToDAG.cpp.patch`、`DADAOISelLowering.cpp.patch` |
| `pseudo` | 伪指令（`*_PSEUDO`）的 TableGen 选择模式 / 展开体（`expandPostRAPseudo`）解析到的**实际发射指令**（ISS-327 ①） | `DADAOCodeGen.td.patch`、`DADAOInstrInfo.cpp.patch` |
| `buildmi` | 任意后端 C++ 补丁中 `BuildMI(...)` 调用里的 `DADAO::<def>` 常量（含帧处理/寄存器分配等 post-ISel 发射，ISS-327 ③） | `DADAO*.cpp.patch` |
| `synonym` | `.td` def 与记录**编码身份相同但助记符不同**时按编码身份互认（ISS-327 ②） | 全 `.td` 补丁 |

现场统计：证据条数 = buildmi 53 + isel-cpp 56 + pat 254 + pat-args 8 + pseudo 19；判「用得上」的记录 **189** 条。

### 提取方法的局限（盲区披露）

- **纯静态**：只读已入库补丁源码，不看构建产物（`.inc`）与运行期；`multiclass`/类继承经人工写了机械展开规则（`Pat<` 体 + 实例化实参），若日后新增其它间接引用形式，须同步扩充提取规则。
- **post-ISel 发射计入 `buildmi`/`pseudo`（ISS-327）**：伪指令展开、帧处理、寄存器分配等 `BuildMI` 常量也证明「后端确实发射该指令」；辅助列 `backend_post_isel` 仅保留 `DADAO::<def>` 的普通引用背景，不再作为排除条件。
- **伪指令展开体共享**：`ADD_PSEUDO`/`SUB_PSEUDO`/`MUL_PSEUDO` 等多条 case 共享一个展开体（fall-through + 运行期 `Opc` 三元选择），静态提取无法逐条区分 ⇒ 同一展开体覆盖的指令**都**记 `pseudo` 证据（保守：宁多认，不假报「未用」）。
- **同义名（`synonym`）**：仅当 `.td` def 与记录 `(format, op, ha)` 编码身份相同、助记符不同时才互认；当前后端未出现此类改名（现场为 0 组，属正常）。
- **间接引用已覆盖**：`DAG.getNode(DADAOISD::…)` 自定义节点本身不是指令名，其落地指令由 `Pat` 覆盖（如 `cs.*` / `br.*`）；若某自定义节点的落地指令**只在 C++ 里 `BuildMI`**，则由 `isel-cpp` 捕获。
- **`.td` def 无真源记录者不入选**：CodeGen-only 伪指令（`*_PSEUDO`/`GLOBAL_ADDR`/`JT_ADDR`/`tailjmp_*`）不是 ISA 记录；其证据经 `pseudo`/`synonym` 解析到实际指令；`tailjmp_*` 与 `jump` 同编码，归入 `jump` 记录的证据。
- **MC-only 指令**：`fence` 汇编可得但无 ISel 模式 ⇒ 第②层 `no`（属正常，非缺陷）。

## 2. 矩阵（全量 266 条，按 id 排序）

列：`id` ｜ `mnemonic` ｜ `format` ｜ `scope` ｜ **①汇编器** ｜ **②ISel** ｜ 证据
（证据格式 `kind:文件:补丁物理行号:def名[:伪指令名]`，可直接 `sed -n '<行号>p' <文件>` 复核；完整形态行见 TSV 的 `L1_asm` 列）

| id | mnemonic | format | scope | ①汇编器 | ②ISel | 证据 |
|---|---|---|---|---|---|---|
| `add.o_orrr_bbd` | `add.o` | `orrr` | `m1` | accept | yes | buildmi:DADAORegisterInfo.cpp.patch:191:add_o_bbd;isel-cpp:DADAOISelDAGToDAG.cpp.patch:167:add_o_bbd;isel-cpp:DADAOISelDAGToDAG.cpp.patch:203:add_o_bbd;isel-cpp:DADAOISelDAGToDAG.cpp.patch:514:add_o_bbd;isel-cpp:DADAOISelDAGToDAG.cpp.patch:541:add_o_bbd;isel-cpp:DADAOISelDAGToDAG.cpp.patch:595:add_o_bbd |
| `add.sb_orrr_rd` | `add.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:565:add_sb |
| `add.si_riii_rb` | `add.si` | `riii` | `m1` | accept | yes | buildmi:DADAOFrameLowering.cpp.patch:192:add_si_rb;buildmi:DADAOFrameLowering.cpp.patch:369:add_si_rb;buildmi:DADAOFrameLowering.cpp.patch:494:add_si_rb;buildmi:DADAORegisterInfo.cpp.patch:210:add_si_rb;buildmi:DADAORegisterInfo.cpp.patch:260:add_si_rb |
| `add.si_riii_rd` | `add.si` | `riii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:314:add_si_rd;pseudo:DADAOCodeGen.td.patch:360:add_si_rd:ADD_IMM_PSEUDO |
| `add.so_rrrr_rd` | `add.so` | `rrrr` | `m1` | accept | no | — |
| `add.st_orrr_rd` | `add.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:563:add_st |
| `add.sw_orrr_rd` | `add.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:564:add_sw |
| `add.ub_orrr_rd` | `add.ub` | `orrr` | `m1` | accept | no | — |
| `add.uo_rrrr_rd` | `add.uo` | `rrrr` | `m1` | accept | yes | pseudo:DADAOCodeGen.td.patch:252:add_uo_rd:ADD_PSEUDO;pseudo:DADAOCodeGen.td.patch:254:add_uo_rd:SUB_PSEUDO;pseudo:DADAOCodeGen.td.patch:263:add_uo_rd:MUL_PSEUDO |
| `add.ut_orrr_rd` | `add.ut` | `orrr` | `m1` | accept | no | — |
| `add.uw_orrr_rd` | `add.uw` | `orrr` | `m1` | accept | no | — |
| `aip.si_riii_rb` | `aip.si` | `riii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:481:aip_si_rb |
| `and.o_orrr_rd` | `and.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:450:and_o;pat:DADAOCodeGen.td.patch:1107:and_o |
| `andn.w_rwii_rb` | `andn.w` | `rwii` | `m1` | accept | no | — |
| `andn.w_rwii_rd` | `andn.w` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:364:andn_w_rd |
| `br.eq_rrii_rd` | `br.eq` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:867:br_eq_rd |
| `br.n_riii_rd` | `br.n` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:861:br_n_rd |
| `br.ne_rrii_rd` | `br.ne` | `rrii` | `m1` | accept | yes | buildmi:DADAOISelLowering.cpp.patch:2993:br_ne_rd;isel-cpp:DADAOISelLowering.cpp.patch:2993:br_ne_rd;pat:DADAOCodeGen.td.patch:868:br_ne_rd |
| `br.nn_riii_rd` | `br.nn` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:862:br_nn_rd |
| `br.np_riii_rd` | `br.np` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:864:br_np_rd |
| `br.nz_riii_rb` | `br.nz` | `riii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:784:br_nz_rb |
| `br.nz_riii_rd` | `br.nz` | `riii` | `m1` | accept | yes | buildmi:DADAOISelLowering.cpp.patch:3004:br_nz_rd;isel-cpp:DADAOISelLowering.cpp.patch:3004:br_nz_rd;pat:DADAOCodeGen.td.patch:860:br_nz_rd |
| `br.p_riii_rd` | `br.p` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:863:br_p_rd |
| `br.z_riii_rb` | `br.z` | `riii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:783:br_z_rb |
| `br.z_riii_rd` | `br.z` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:859:br_z_rd |
| `call_iiii_ra` | `call` | `iiii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:671:call_iiii |
| `call_rrii_ra` | `call` | `rrii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:671:call_rrii |
| `cfx2rc_crrr_cfx` | `cfx2rc` | `crrr` | `m1` | accept | no | — |
| `cfx2rd_crrr_cfx` | `cfx2rd` | `crrr` | `m1` | accept | no | — |
| `cfxld_crii_cfx` | `cfxld` | `crii` | `excluded` | reject | no | — |
| `cfxst_crii_cfx` | `cfxst` | `crii` | `excluded` | reject | no | — |
| `clmul.o_rrrr_rd` | `clmul.o` | `rrrr` | `m9` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:253:clmul_o_rd;buildmi:DADAOInstrInfo.cpp.patch:267:clmul_o_rd;buildmi:DADAOInstrInfo.cpp.patch:283:clmul_o_rd;pseudo:DADAOCodeGen.td.patch:328:clmul_o_rd:CLMUL_PSEUDO;pseudo:DADAOCodeGen.td.patch:330:clmul_o_rd:CLMULHI_PSEUDO |
| `cmp.sb_orrr_rd` | `cmp.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:850:cmp_sb |
| `cmp.si_rrii_rd` | `cmp.si` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:829:cmp_si_rd;pat:DADAOCodeGen.td.patch:1103:cmp_si_rd;pat:DADAOCodeGen.td.patch:1105:cmp_si_rd;pat:DADAOCodeGen.td.patch:1107:cmp_si_rd;pat:DADAOCodeGen.td.patch:1111:cmp_si_rd |
| `cmp.so_orrr_rd` | `cmp.so` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:827:cmp_so |
| `cmp.st_orrr_rd` | `cmp.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:846:cmp_st |
| `cmp.sw_orrr_rd` | `cmp.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:848:cmp_sw |
| `cmp.ub_orrr_rd` | `cmp.ub` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:856:cmp_ub |
| `cmp.ui_rrii_rd` | `cmp.ui` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:839:cmp_ui_rd |
| `cmp.uo_orrr_dbb` | `cmp.uo` | `orrr` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:769:cmp_uo_dbb |
| `cmp.uo_orrr_rd` | `cmp.uo` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:837:cmp_uo |
| `cmp.ut_orrr_rd` | `cmp.ut` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:852:cmp_ut |
| `cmp.uw_orrr_rd` | `cmp.uw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:854:cmp_uw |
| `cs.eq_rrrr_rd` | `cs.eq` | `rrrr` | `m1` | accept | no | — |
| `cs.n_rrrr_rd` | `cs.n` | `rrrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:874:cs_n_rd;pat:DADAOCodeGen.td.patch:882:cs_n_rd;pat:DADAOCodeGen.td.patch:888:cs_n_rd;pat:DADAOCodeGen.td.patch:894:cs_n_rd |
| `cs.n_rrrr_rf` | `cs.n` | `rrrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:906:cs_n_rrrr_rf;pat:DADAOCodeGen.td.patch:912:cs_n_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1117:cs_n_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1120:cs_n_rrrr_rf |
| `cs.ne_rrrr_rd` | `cs.ne` | `rrrr` | `m1` | accept | no | — |
| `cs.p_rrrr_rd` | `cs.p` | `rrrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:876:cs_p_rd;pat:DADAOCodeGen.td.patch:886:cs_p_rd;pat:DADAOCodeGen.td.patch:892:cs_p_rd;pat:DADAOCodeGen.td.patch:898:cs_p_rd;pat:DADAOCodeGen.td.patch:1107:cs_p_rd;pat:DADAOCodeGen.td.patch:1111:cs_p_rd |
| `cs.p_rrrr_rf` | `cs.p` | `rrrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:910:cs_p_rrrr_rf;pat:DADAOCodeGen.td.patch:916:cs_p_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1118:cs_p_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1121:cs_p_rrrr_rf |
| `cs.z_rrrr_rd` | `cs.z` | `rrrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:875:cs_z_rd;pat:DADAOCodeGen.td.patch:884:cs_z_rd;pat:DADAOCodeGen.td.patch:890:cs_z_rd;pat:DADAOCodeGen.td.patch:896:cs_z_rd;pat:DADAOCodeGen.td.patch:1108:cs_z_rd;pat:DADAOCodeGen.td.patch:1112:cs_z_rd |
| `cs.z_rrrr_rf` | `cs.z` | `rrrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:908:cs_z_rrrr_rf;pat:DADAOCodeGen.td.patch:914:cs_z_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1117:cs_z_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1120:cs_z_rrrr_rf |
| `ctlz_orri_rd` | `ctlz` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:506:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:507:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:515:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:516:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:517:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:519:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:521:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:523:ctlz_orri_rd |
| `ctpop_orri_rd` | `ctpop` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:510:ctpop_orri_rd;pat:DADAOCodeGen.td.patch:533:ctpop_orri_rd;pat:DADAOCodeGen.td.patch:534:ctpop_orri_rd;pat:DADAOCodeGen.td.patch:535:ctpop_orri_rd |
| `cttz_orri_rd` | `cttz` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:508:cttz_orri_rd;pat:DADAOCodeGen.td.patch:509:cttz_orri_rd;pat:DADAOCodeGen.td.patch:524:cttz_orri_rd;pat:DADAOCodeGen.td.patch:525:cttz_orri_rd;pat:DADAOCodeGen.td.patch:526:cttz_orri_rd;pat:DADAOCodeGen.td.patch:528:cttz_orri_rd;pat:DADAOCodeGen.td.patch:530:cttz_orri_rd;pat:DADAOCodeGen.td.patch:532:cttz_orri_rd |
| `div.sb_orrr_rd` | `div.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:578:div_sb |
| `div.so_orrr_rd` | `div.so` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:547:div_so |
| `div.st_orrr_rd` | `div.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:576:div_st |
| `div.sw_orrr_rd` | `div.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:577:div_sw |
| `div.ub_orrr_rd` | `div.ub` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:575:div_ub |
| `div.uo_orrr_rd` | `div.uo` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:546:div_uo |
| `div.ut_orrr_rd` | `div.ut` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:573:div_ut |
| `div.uw_orrr_rd` | `div.uw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:574:div_uw |
| `escape_ciii_cfx` | `escape` | `ciii` | `m1` | accept | no | — |
| `ext.so_orri_rd` | `ext.so` | `orri` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:637:ext_so_orri;pat:DADAOCodeGen.td.patch:638:ext_so_orri;pat:DADAOCodeGen.td.patch:639:ext_so_orri;pat:DADAOCodeGen.td.patch:640:ext_so_orri;pat:DADAOCodeGen.td.patch:641:ext_so_orri;pat:DADAOCodeGen.td.patch:642:ext_so_orri;pat:DADAOCodeGen.td.patch:684:ext_so_orri;pat:DADAOCodeGen.td.patch:685:ext_so_orri;pat:DADAOCodeGen.td.patch:686:ext_so_orri;pat:DADAOCodeGen.td.patch:691:ext_so_orri;pat:DADAOCodeGen.td.patch:695:ext_so_orri;pat:DADAOCodeGen.td.patch:697:ext_so_orri;pat:DADAOCodeGen.td.patch:699:ext_so_orri;pat:DADAOCodeGen.td.patch:705:ext_so_orri;pat:DADAOCodeGen.td.patch:707:ext_so_orri;pat:DADAOCodeGen.td.patch:709:ext_so_orri |
| `ext.so_orrr_rd` | `ext.so` | `orrr` | `m1` | accept | no | — |
| `ext.uo_orri_rd` | `ext.uo` | `orri` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:623:ext_uo_orri;pat:DADAOCodeGen.td.patch:624:ext_uo_orri;pat:DADAOCodeGen.td.patch:625:ext_uo_orri;pat:DADAOCodeGen.td.patch:626:ext_uo_orri;pat:DADAOCodeGen.td.patch:627:ext_uo_orri;pat:DADAOCodeGen.td.patch:628:ext_uo_orri;pat:DADAOCodeGen.td.patch:630:ext_uo_orri;pat:DADAOCodeGen.td.patch:631:ext_uo_orri;pat:DADAOCodeGen.td.patch:632:ext_uo_orri;pat:DADAOCodeGen.td.patch:633:ext_uo_orri;pat:DADAOCodeGen.td.patch:634:ext_uo_orri;pat:DADAOCodeGen.td.patch:635:ext_uo_orri;pat:DADAOCodeGen.td.patch:646:ext_uo_orri;pat:DADAOCodeGen.td.patch:647:ext_uo_orri;pat:DADAOCodeGen.td.patch:648:ext_uo_orri;pat:DADAOCodeGen.td.patch:649:ext_uo_orri;pat:DADAOCodeGen.td.patch:650:ext_uo_orri;pat:DADAOCodeGen.td.patch:651:ext_uo_orri;pat:DADAOCodeGen.td.patch:657:ext_uo_orri;pat:DADAOCodeGen.td.patch:659:ext_uo_orri;pat:DADAOCodeGen.td.patch:661:ext_uo_orri |
| `ext.uo_orrr_rd` | `ext.uo` | `orrr` | `m1` | accept | no | — |
| `fence_oiii_imm` | `fence` | `oiii` | `m9` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:728:fence |
| `fo2fo_orri_rf` | `fo2fo` | `orri` | `fp` | accept | no | — |
| `fo2ft_orri_rf` | `fo2ft` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1136:fo2ft_orri_rf |
| `fo2io_orri_rf` | `fo2io` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:817:fo2io_orri_rf;pat:DADAOCodeGen.td.patch:1142:fo2io_orri_rf |
| `fo2it_orri_rf` | `fo2it` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:817:fo2it_orri_rf |
| `fo2uo_orri_rf` | `fo2uo` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:817:fo2uo_orri_rf;pat:DADAOCodeGen.td.patch:1144:fo2uo_orri_rf |
| `fo2ut_orri_rf` | `fo2ut` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:818:fo2ut_orri_rf |
| `foadd_orrr_rf` | `foadd` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:931:foadd_orrr_rf |
| `focls_orri_rf` | `focls` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1045:focls_orri_rf |
| `fodiv_orrr_rf` | `fodiv` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:945:fodiv_orrr_rf |
| `fofma_rrrr_rf` | `fofma` | `rrrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:944:fofma_rrrr_rf |
| `fomax_orrr_rf` | `fomax` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:994:fomax_orrr_rf;pat:DADAOCodeGen.td.patch:996:fomax_orrr_rf |
| `fomin_orrr_rf` | `fomin` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:993:fomin_orrr_rf;pat:DADAOCodeGen.td.patch:995:fomin_orrr_rf |
| `fomul_orrr_rf` | `fomul` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:933:fomul_orrr_rf |
| `foqcmp_orrr_rf` | `foqcmp` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1038:foqcmp_orrr_rf;pat-args:DADAOCodeGen.td.patch:1117:foqcmp_orrr_rf |
| `forem_orrr_rf` | `forem` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1060:forem_orrr_rf |
| `fornd_orri_rf` | `fornd` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1022:fornd_orri_rf;pat:DADAOCodeGen.td.patch:1023:fornd_orri_rf;pat:DADAOCodeGen.td.patch:1024:fornd_orri_rf;pat:DADAOCodeGen.td.patch:1025:fornd_orri_rf;pat:DADAOCodeGen.td.patch:1026:fornd_orri_rf;pat:DADAOCodeGen.td.patch:1027:fornd_orri_rf;pat:DADAOCodeGen.td.patch:1028:fornd_orri_rf |
| `foroot_orri_rf` | `foroot` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:947:foroot_orri_rf |
| `fosclb_orrr_rf` | `fosclb` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1051:fosclb_orrr_rf |
| `foscmp_orrr_rf` | `foscmp` | `orrr` | `fp` | accept | no | — |
| `fosgnj_orrr_rf` | `fosgnj` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:958:fosgnj_orrr_rf;pat:DADAOCodeGen.td.patch:960:fosgnj_orrr_rf |
| `fosgnn_orrr_rf` | `fosgnn` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:949:fosgnn_orrr_rf |
| `fosub_orrr_rf` | `fosub` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:932:fosub_orrr_rf |
| `ft2fo_orri_rf` | `ft2fo` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1135:ft2fo_orri_rf |
| `ft2ft_orri_rf` | `ft2ft` | `orri` | `fp` | accept | no | — |
| `ft2io_orri_rf` | `ft2io` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:818:ft2io_orri_rf;pat:DADAOCodeGen.td.patch:1143:ft2io_orri_rf |
| `ft2it_orri_rf` | `ft2it` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:819:ft2it_orri_rf |
| `ft2uo_orri_rf` | `ft2uo` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:818:ft2uo_orri_rf;pat:DADAOCodeGen.td.patch:1145:ft2uo_orri_rf |
| `ft2ut_orri_rf` | `ft2ut` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:819:ft2ut_orri_rf |
| `ftadd_orrr_rf` | `ftadd` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:963:ftadd_orrr_rf |
| `ftcls_orri_rf` | `ftcls` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1046:ftcls_orri_rf |
| `ftdiv_orrr_rf` | `ftdiv` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:968:ftdiv_orrr_rf |
| `ftfma_rrrr_rf` | `ftfma` | `rrrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:967:ftfma_rrrr_rf |
| `ftmax_orrr_rf` | `ftmax` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:998:ftmax_orrr_rf;pat:DADAOCodeGen.td.patch:1000:ftmax_orrr_rf |
| `ftmin_orrr_rf` | `ftmin` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:997:ftmin_orrr_rf;pat:DADAOCodeGen.td.patch:999:ftmin_orrr_rf |
| `ftmul_orrr_rf` | `ftmul` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:965:ftmul_orrr_rf |
| `ftqcmp_orrr_rf` | `ftqcmp` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1039:ftqcmp_orrr_rf;pat-args:DADAOCodeGen.td.patch:1120:ftqcmp_orrr_rf |
| `ftrem_orrr_rf` | `ftrem` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1062:ftrem_orrr_rf |
| `ftrnd_orri_rf` | `ftrnd` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1029:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:1030:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:1031:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:1032:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:1033:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:1034:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:1035:ftrnd_orri_rf |
| `ftroot_orri_rf` | `ftroot` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:969:ftroot_orri_rf |
| `ftsclb_orrr_rf` | `ftsclb` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1052:ftsclb_orrr_rf |
| `ftscmp_orrr_rf` | `ftscmp` | `orrr` | `fp` | accept | no | — |
| `ftsgnj_orrr_rf` | `ftsgnj` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:974:ftsgnj_orrr_rf;pat:DADAOCodeGen.td.patch:976:ftsgnj_orrr_rf |
| `ftsgnn_orrr_rf` | `ftsgnn` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:970:ftsgnn_orrr_rf |
| `ftsub_orrr_rf` | `ftsub` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:964:ftsub_orrr_rf |
| `io2fo_orri_rf` | `io2fo` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1149:io2fo_orri_rf |
| `io2ft_orri_rf` | `io2ft` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1150:io2ft_orri_rf |
| `it2fo_orri_rf` | `it2fo` | `orri` | `fp` | accept | no | — |
| `it2ft_orri_rf` | `it2ft` | `orri` | `fp` | accept | no | — |
| `jump_iiii_rb` | `jump` | `iiii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:733:jump_iiii;buildmi:DADAOInstrInfo.cpp.patch:753:jump_iiii;isel-cpp:DADAOISelDAGToDAG.cpp.patch:716:tailjmp_iiii;pat:DADAOCodeGen.td.patch:919:jump_iiii |
| `jump_rrii_rb` | `jump` | `rrii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:604:jump_rrii;isel-cpp:DADAOISelDAGToDAG.cpp.patch:626:jump_rrii;isel-cpp:DADAOISelDAGToDAG.cpp.patch:716:tailjmp_rrii |
| `ld.o_rrii_ra` | `ld.o` | `rrii` | `m1` | accept | no | — |
| `ld.o_rrii_rb` | `ld.o` | `rrii` | `m1` | accept | yes | buildmi:DADAOFrameLowering.cpp.patch:462:ld_o_rb;buildmi:DADAOInstrInfo.cpp.patch:483:ld_o_rb;isel-cpp:DADAOISelDAGToDAG.cpp.patch:175:ld_o_rb;isel-cpp:DADAOISelDAGToDAG.cpp.patch:597:ld_o_rb |
| `ld.o_rrii_rd` | `ld.o` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:755:ld_o_rd |
| `ld.o_rrii_rf` | `ld.o` | `rrii` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1125:ld_o_rrii_rf |
| `ld.sb_rrii_rd` | `ld.sb` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:762:ld_sb_rd;pat:DADAOCodeGen.td.patch:799:ld_sb_rd;pat:DADAOCodeGen.td.patch:800:ld_sb_rd |
| `ld.st_rrii_rd` | `ld.st` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:777:ld_st_rd |
| `ld.sw_rrii_rd` | `ld.sw` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:770:ld_sw_rd;pat:DADAOCodeGen.td.patch:804:ld_sw_rd |
| `ld.t_rrii_rf` | `ld.t` | `rrii` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1129:ld_t_rrii_rf |
| `ld.ub_rrii_rd` | `ld.ub` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:760:ld_ub_rd;pat:DADAOCodeGen.td.patch:761:ld_ub_rd;pat:DADAOCodeGen.td.patch:788:ld_ub_rd;pat:DADAOCodeGen.td.patch:795:ld_ub_rd;pat:DADAOCodeGen.td.patch:796:ld_ub_rd;pat:DADAOCodeGen.td.patch:797:ld_ub_rd;pat:DADAOCodeGen.td.patch:798:ld_ub_rd |
| `ld.ut_rrii_rd` | `ld.ut` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:775:ld_ut_rd;pat:DADAOCodeGen.td.patch:776:ld_ut_rd;pat:DADAOCodeGen.td.patch:790:ld_ut_rd |
| `ld.uw_rrii_rd` | `ld.uw` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:768:ld_uw_rd;pat:DADAOCodeGen.td.patch:769:ld_uw_rd;pat:DADAOCodeGen.td.patch:789:ld_uw_rd;pat:DADAOCodeGen.td.patch:802:ld_uw_rd;pat:DADAOCodeGen.td.patch:803:ld_uw_rd |
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
| `lr.b.an_orrr_rd` | `lr.b.an` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2926:lr_b_an |
| `lr.b.ar_orrr_rd` | `lr.b.ar` | `orrr` | `m9` | accept | no | — |
| `lr.b.nn_orrr_rd` | `lr.b.nn` | `orrr` | `m9` | accept | no | — |
| `lr.o.an_orrr_rd` | `lr.o.an` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2938:lr_o_an |
| `lr.o.ar_orrr_rd` | `lr.o.ar` | `orrr` | `m9` | accept | no | — |
| `lr.o.nn_orrr_rd` | `lr.o.nn` | `orrr` | `m9` | accept | no | — |
| `lr.t.an_orrr_rd` | `lr.t.an` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2934:lr_t_an |
| `lr.t.ar_orrr_rd` | `lr.t.ar` | `orrr` | `m9` | accept | no | — |
| `lr.t.nn_orrr_rd` | `lr.t.nn` | `orrr` | `m9` | accept | no | — |
| `lr.w.an_orrr_rd` | `lr.w.an` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2930:lr_w_an |
| `lr.w.ar_orrr_rd` | `lr.w.ar` | `orrr` | `m9` | accept | no | — |
| `lr.w.nn_orrr_rd` | `lr.w.nn` | `orrr` | `m9` | accept | no | — |
| `mul.sb_orrr_rd` | `mul.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:571:mul_sb |
| `mul.so_rrrr_rd` | `mul.so` | `rrrr` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:222:mul_so_rd;buildmi:DADAOInstrInfo.cpp.patch:238:mul_so_rd;pseudo:DADAOCodeGen.td.patch:298:mul_so_rd:MULHS_PSEUDO;pseudo:DADAOCodeGen.td.patch:307:mul_so_rd:SMUL_LOHI_PSEUDO |
| `mul.st_orrr_rd` | `mul.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:569:mul_st |
| `mul.sw_orrr_rd` | `mul.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:570:mul_sw |
| `mul.ub_orrr_rd` | `mul.ub` | `orrr` | `m1` | accept | no | — |
| `mul.uo_rrrr_rd` | `mul.uo` | `rrrr` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:190:mul_uo_rd;buildmi:DADAOInstrInfo.cpp.patch:206:mul_uo_rd;pseudo:DADAOCodeGen.td.patch:252:mul_uo_rd:ADD_PSEUDO;pseudo:DADAOCodeGen.td.patch:254:mul_uo_rd:SUB_PSEUDO;pseudo:DADAOCodeGen.td.patch:263:mul_uo_rd:MUL_PSEUDO;pseudo:DADAOCodeGen.td.patch:275:mul_uo_rd:MULHU_PSEUDO;pseudo:DADAOCodeGen.td.patch:284:mul_uo_rd:UMUL_LOHI_PSEUDO |
| `mul.ut_orrr_rd` | `mul.ut` | `orrr` | `m1` | accept | no | — |
| `mul.uw_orrr_rd` | `mul.uw` | `orrr` | `m1` | accept | no | — |
| `or.o_orrr_rd` | `or.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:451:or_o;pat:DADAOCodeGen.td.patch:1111:or_o |
| `or.w_rwii_rb` | `or.w` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:391:or_w_rb;buildmi:DADAOInstrInfo.cpp.patch:392:or_w_rb;buildmi:DADAOInstrInfo.cpp.patch:429:or_w_rb;buildmi:DADAOInstrInfo.cpp.patch:430:or_w_rb;buildmi:DADAOInstrInfo.cpp.patch:448:or_w_rb;buildmi:DADAOInstrInfo.cpp.patch:449:or_w_rb |
| `or.w_rwii_rd` | `or.w` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:131:or_w_rd;buildmi:DADAOInstrInfo.cpp.patch:370:or_w_rd;buildmi:DADAOInstrInfo.cpp.patch:410:or_w_rd;buildmi:DADAOInstrInfo.cpp.patch:411:or_w_rd |
| `ra2rd_orri_ra` | `ra2rd` | `orri` | `m1` | accept | no | — |
| `rb2rb_orri_rb` | `rb2rb` | `orri` | `m1` | accept | yes | buildmi:DADAOFrameLowering.cpp.patch:365:rb2rb;buildmi:DADAOFrameLowering.cpp.patch:427:rb2rb;buildmi:DADAOFrameLowering.cpp.patch:458:rb2rb;buildmi:DADAORegisterInfo.cpp.patch:206:rb2rb;buildmi:DADAORegisterInfo.cpp.patch:215:rb2rb;buildmi:DADAORegisterInfo.cpp.patch:257:rb2rb |
| `rb2rd_orri_rb` | `rb2rd` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:538:rb2rd |
| `rd2ra_orri_ra` | `rd2ra` | `orri` | `m1` | accept | no | — |
| `rd2rb_orri_rb` | `rd2rb` | `orri` | `m1` | accept | no | — |
| `rd2rd_orri_rd` | `rd2rd` | `orri` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:313:rd2rd;pseudo:DADAOCodeGen.td.patch:360:rd2rd:ADD_IMM_PSEUDO |
| `rd2rf_orri_rf` | `rd2rf` | `orri` | `fp` | accept | yes | buildmi:DADAOISelLowering.cpp.patch:2908:rd2rf_orri_rf;isel-cpp:DADAOISelDAGToDAG.cpp.patch:333:rd2rf_orri_rf;isel-cpp:DADAOISelLowering.cpp.patch:2908:rd2rf_orri_rf;pat:DADAOCodeGen.td.patch:666:rd2rf_orri_rf;pat:DADAOCodeGen.td.patch:960:rd2rf_orri_rf;pat:DADAOCodeGen.td.patch:976:rd2rf_orri_rf;pat:DADAOCodeGen.td.patch:1160:rd2rf_orri_rf |
| `rem.sb_orrr_rd` | `rem.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:584:rem_sb |
| `rem.so_orrr_rd` | `rem.so` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:549:rem_so |
| `rem.st_orrr_rd` | `rem.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:582:rem_st |
| `rem.sw_orrr_rd` | `rem.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:583:rem_sw |
| `rem.ub_orrr_rd` | `rem.ub` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:581:rem_ub |
| `rem.uo_orrr_rd` | `rem.uo` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:548:rem_uo |
| `rem.ut_orrr_rd` | `rem.ut` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:579:rem_ut |
| `rem.uw_orrr_rd` | `rem.uw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:580:rem_uw |
| `ret_riii_ra` | `ret` | `riii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:153:ret_riii;pseudo:DADAOCodeGen.td.patch:222:ret_riii:RET_PSEUDO |
| `rev.b_orri_rd` | `rev.b` | `orri` | `m8` | accept | no | — |
| `rev.o_orri_rd` | `rev.o` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:540:rev_o_orri_rd;pat:DADAOCodeGen.td.patch:541:rev_o_orri_rd |
| `rev.t_orri_rd` | `rev.t` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:605:rev_t_orri_rd |
| `rev.w_orri_rd` | `rev.w` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:606:rev_w_orri_rd |
| `rf2rd_orri_rf` | `rf2rd` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:667:rf2rd_orri_rf;pat:DADAOCodeGen.td.patch:1161:rf2rd_orri_rf |
| `rol.b_orri_rd` | `rol.b` | `orri` | `m9` | accept | no | — |
| `rol.b_orrr_rd` | `rol.b` | `orrr` | `m9` | accept | no | — |
| `rol.o_orri_rd` | `rol.o` | `orri` | `m9` | accept | yes | pat:DADAOCodeGen.td.patch:489:rol_o_orri |
| `rol.o_orrr_rd` | `rol.o` | `orrr` | `m9` | accept | yes | pat:DADAOCodeGen.td.patch:490:rol_o_orrr |
| `rol.t_orri_rd` | `rol.t` | `orri` | `m9` | accept | no | — |
| `rol.t_orrr_rd` | `rol.t` | `orrr` | `m9` | accept | no | — |
| `rol.w_orri_rd` | `rol.w` | `orri` | `m9` | accept | no | — |
| `rol.w_orrr_rd` | `rol.w` | `orrr` | `m9` | accept | no | — |
| `sc.b.ar_orrr_rd` | `sc.b.ar` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2927:sc_b_ar |
| `sc.b.nn_orrr_rd` | `sc.b.nn` | `orrr` | `m9` | accept | no | — |
| `sc.b.nr_orrr_rd` | `sc.b.nr` | `orrr` | `m9` | accept | no | — |
| `sc.o.ar_orrr_rd` | `sc.o.ar` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2939:sc_o_ar |
| `sc.o.nn_orrr_rd` | `sc.o.nn` | `orrr` | `m9` | accept | no | — |
| `sc.o.nr_orrr_rd` | `sc.o.nr` | `orrr` | `m9` | accept | no | — |
| `sc.t.ar_orrr_rd` | `sc.t.ar` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2935:sc_t_ar |
| `sc.t.nn_orrr_rd` | `sc.t.nn` | `orrr` | `m9` | accept | no | — |
| `sc.t.nr_orrr_rd` | `sc.t.nr` | `orrr` | `m9` | accept | no | — |
| `sc.w.ar_orrr_rd` | `sc.w.ar` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2931:sc_w_ar |
| `sc.w.nn_orrr_rd` | `sc.w.nn` | `orrr` | `m9` | accept | no | — |
| `sc.w.nr_orrr_rd` | `sc.w.nr` | `orrr` | `m9` | accept | no | — |
| `set.ow_rwii_rd` | `set.ow` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:346:set_ow_rd;buildmi:DADAOInstrInfo.cpp.patch:354:set_ow_rd |
| `set.w_rwii_rf` | `set.w` | `rwii` | `fp` | accept | yes | buildmi:DADAOISelLowering.cpp.patch:2904:set_w_rwii_rf;isel-cpp:DADAOISelLowering.cpp.patch:2904:set_w_rwii_rf |
| `set.zw_rwii_rb` | `set.zw` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:390:set_zw_rb;buildmi:DADAOInstrInfo.cpp.patch:428:set_zw_rb;buildmi:DADAOInstrInfo.cpp.patch:447:set_zw_rb |
| `set.zw_rwii_rd` | `set.zw` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:131:set_zw_rd;buildmi:DADAOInstrInfo.cpp.patch:349:set_zw_rd;buildmi:DADAOInstrInfo.cpp.patch:354:set_zw_rd;buildmi:DADAOInstrInfo.cpp.patch:409:set_zw_rd |
| `shl.b_orri_rd` | `shl.b` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:427:shl_b_orri |
| `shl.b_orrr_rd` | `shl.b` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:596:shl_b_orrr |
| `shl.o_orri_rd` | `shl.o` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:593:shl_o_orri |
| `shl.o_orrr_rd` | `shl.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:479:shl_o_orrr |
| `shl.t_orri_rd` | `shl.t` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:427:shl_t_orri |
| `shl.t_orrr_rd` | `shl.t` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:594:shl_t_orrr |
| `shl.w_orri_rd` | `shl.w` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:427:shl_w_orri |
| `shl.w_orrr_rd` | `shl.w` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:595:shl_w_orrr |
| `shr.sb_orri_rd` | `shr.sb` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:433:shr_sb_orri |
| `shr.sb_orrr_rd` | `shr.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:602:shr_sb_orrr |
| `shr.so_orri_rd` | `shr.so` | `orri` | `m1` | accept | no | — |
| `shr.so_orrr_rd` | `shr.so` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:481:shr_so_orrr |
| `shr.st_orri_rd` | `shr.st` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:433:shr_st_orri |
| `shr.st_orrr_rd` | `shr.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:600:shr_st_orrr |
| `shr.sw_orri_rd` | `shr.sw` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:433:shr_sw_orri |
| `shr.sw_orrr_rd` | `shr.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:601:shr_sw_orrr |
| `shr.ub_orri_rd` | `shr.ub` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:430:shr_ub_orri |
| `shr.ub_orrr_rd` | `shr.ub` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:599:shr_ub_orrr |
| `shr.uo_orri_rd` | `shr.uo` | `orri` | `m1` | accept | no | — |
| `shr.uo_orrr_rd` | `shr.uo` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:480:shr_uo_orrr |
| `shr.ut_orri_rd` | `shr.ut` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:430:shr_ut_orri |
| `shr.ut_orrr_rd` | `shr.ut` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:597:shr_ut_orrr |
| `shr.uw_orri_rd` | `shr.uw` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:430:shr_uw_orri |
| `shr.uw_orrr_rd` | `shr.uw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:598:shr_uw_orrr |
| `st.b_rrii_rd` | `st.b` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:763:st_b_rd;pat:DADAOCodeGen.td.patch:764:st_b_rd;pat:DADAOCodeGen.td.patch:765:st_b_rd;pat:DADAOCodeGen.td.patch:791:st_b_rd |
| `st.o_rrii_ra` | `st.o` | `rrii` | `m1` | accept | no | — |
| `st.o_rrii_rb` | `st.o` | `rrii` | `m1` | accept | yes | buildmi:DADAOFrameLowering.cpp.patch:414:st_o_rb |
| `st.o_rrii_rd` | `st.o` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:756:st_o_rd |
| `st.o_rrii_rf` | `st.o` | `rrii` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1127:st_o_rrii_rf |
| `st.t_rrii_rd` | `st.t` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:778:st_t_rd;pat:DADAOCodeGen.td.patch:793:st_t_rd |
| `st.t_rrii_rf` | `st.t` | `rrii` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1131:st_t_rrii_rf |
| `st.w_rrii_rd` | `st.w` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:771:st_w_rd;pat:DADAOCodeGen.td.patch:772:st_w_rd;pat:DADAOCodeGen.td.patch:792:st_w_rd |
| `stm.b_rrri_rd` | `stm.b` | `rrri` | `m1` | accept | no | — |
| `stm.o_rrri_ra` | `stm.o` | `rrri` | `m1` | accept | no | — |
| `stm.o_rrri_rb` | `stm.o` | `rrri` | `m1` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:1258:stm_o_rb |
| `stm.o_rrri_rd` | `stm.o` | `rrri` | `m1` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:1256:stm_o_rd |
| `stm.o_rrri_rf` | `stm.o` | `rrri` | `fp` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:1260:stm_o_rrri_rf |
| `stm.t_rrri_rd` | `stm.t` | `rrri` | `m1` | accept | no | — |
| `stm.t_rrri_rf` | `stm.t` | `rrri` | `fp` | accept | no | — |
| `stm.w_rrri_rd` | `stm.w` | `rrri` | `m1` | accept | no | — |
| `sub.o_orrr_bbd` | `sub.o` | `orrr` | `m1` | accept | no | — |
| `sub.o_orrr_dbb` | `sub.o` | `orrr` | `m3` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:211:sub_o_dbb |
| `sub.sb_orrr_rd` | `sub.sb` | `orrr` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:481:sub_sb;pat:DADAOCodeGen.td.patch:470:sub_sb;pat:DADAOCodeGen.td.patch:568:sub_sb |
| `sub.so_rrrr_rd` | `sub.so` | `rrrr` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:297:sub_so_rd;pseudo:DADAOCodeGen.td.patch:469:sub_so_rd:NEG_PSEUDO |
| `sub.st_orrr_rd` | `sub.st` | `orrr` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:479:sub_st;pat:DADAOCodeGen.td.patch:472:sub_st;pat:DADAOCodeGen.td.patch:566:sub_st |
| `sub.sw_orrr_rd` | `sub.sw` | `orrr` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:480:sub_sw;pat:DADAOCodeGen.td.patch:471:sub_sw;pat:DADAOCodeGen.td.patch:567:sub_sw |
| `sub.ub_orrr_rd` | `sub.ub` | `orrr` | `m1` | accept | no | — |
| `sub.uo_rrrr_rd` | `sub.uo` | `rrrr` | `m1` | accept | yes | pseudo:DADAOCodeGen.td.patch:252:sub_uo_rd:ADD_PSEUDO;pseudo:DADAOCodeGen.td.patch:254:sub_uo_rd:SUB_PSEUDO;pseudo:DADAOCodeGen.td.patch:263:sub_uo_rd:MUL_PSEUDO |
| `sub.ut_orrr_rd` | `sub.ut` | `orrr` | `m1` | accept | no | — |
| `sub.uw_orrr_rd` | `sub.uw` | `orrr` | `m1` | accept | no | — |
| `swym_oiii_imm` | `swym` | `oiii` | `m1` | accept | no | — |
| `trap_ciii_cfx` | `trap` | `ciii` | `m1` | accept | no | — |
| `uo2fo_orri_rf` | `uo2fo` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1151:uo2fo_orri_rf |
| `uo2ft_orri_rf` | `uo2ft` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1152:uo2ft_orri_rf |
| `ut2fo_orri_rf` | `ut2fo` | `orri` | `fp` | accept | no | — |
| `ut2ft_orri_rf` | `ut2ft` | `orri` | `fp` | accept | no | — |
| `xnor.o_orrr_rd` | `xnor.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:461:xnor_o |
| `xor.o_orrr_rd` | `xor.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:452:xor_o |

## 3. 缺口汇总（未被 ISel 使用，77 条）

候选优化面（供后续里程碑参考）。按性质分四类（现场统计）：

1. **真缺口·候补优化面**（`scope != excluded`，且后端 ISel/post-ISel 均未引用，且非汇编层/特权族）：**66** 条 —— ISA 有、后端一次都没发射，最有价值。
2. **真缺口·汇编层/特权族**（同上但 `format ∈ {crrr, ciii, crii}` 或助记符 ∈ {fence, swym}，机械判据）：**5** 条 —— 经 cfx 访问/内联汇编/占位语义使用，不经 ISel 选入属预期。
3. **仅 post-ISel 引用**（伪指令展开/帧/寄存器分配会发射，非 ISel 选入）：**4** 条。
4. **`scope: excluded` 未实现**（汇编器拒绝、执行 ILLI）：**2** 条 —— 不在本期范围。

### 3.1 真缺口·候补优化面（66 条）

| id | mnemonic | format | scope |
|---|---|---|---|
| `add.so_rrrr_rd` | `add.so` | `rrrr` | `m1` |
| `add.ub_orrr_rd` | `add.ub` | `orrr` | `m1` |
| `add.ut_orrr_rd` | `add.ut` | `orrr` | `m1` |
| `add.uw_orrr_rd` | `add.uw` | `orrr` | `m1` |
| `andn.w_rwii_rb` | `andn.w` | `rwii` | `m1` |
| `cs.eq_rrrr_rd` | `cs.eq` | `rrrr` | `m1` |
| `cs.ne_rrrr_rd` | `cs.ne` | `rrrr` | `m1` |
| `ext.so_orrr_rd` | `ext.so` | `orrr` | `m1` |
| `ext.uo_orrr_rd` | `ext.uo` | `orrr` | `m1` |
| `foscmp_orrr_rf` | `foscmp` | `orrr` | `fp` |
| `ft2ft_orri_rf` | `ft2ft` | `orri` | `fp` |
| `ftscmp_orrr_rf` | `ftscmp` | `orrr` | `fp` |
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
| `lr.b.ar_orrr_rd` | `lr.b.ar` | `orrr` | `m9` |
| `lr.b.nn_orrr_rd` | `lr.b.nn` | `orrr` | `m9` |
| `lr.o.ar_orrr_rd` | `lr.o.ar` | `orrr` | `m9` |
| `lr.o.nn_orrr_rd` | `lr.o.nn` | `orrr` | `m9` |
| `lr.t.ar_orrr_rd` | `lr.t.ar` | `orrr` | `m9` |
| `lr.t.nn_orrr_rd` | `lr.t.nn` | `orrr` | `m9` |
| `lr.w.ar_orrr_rd` | `lr.w.ar` | `orrr` | `m9` |
| `lr.w.nn_orrr_rd` | `lr.w.nn` | `orrr` | `m9` |
| `mul.ub_orrr_rd` | `mul.ub` | `orrr` | `m1` |
| `mul.ut_orrr_rd` | `mul.ut` | `orrr` | `m1` |
| `mul.uw_orrr_rd` | `mul.uw` | `orrr` | `m1` |
| `ra2rd_orri_ra` | `ra2rd` | `orri` | `m1` |
| `rd2ra_orri_ra` | `rd2ra` | `orri` | `m1` |
| `rev.b_orri_rd` | `rev.b` | `orri` | `m8` |
| `rol.b_orri_rd` | `rol.b` | `orri` | `m9` |
| `rol.b_orrr_rd` | `rol.b` | `orrr` | `m9` |
| `rol.t_orri_rd` | `rol.t` | `orri` | `m9` |
| `rol.t_orrr_rd` | `rol.t` | `orrr` | `m9` |
| `rol.w_orri_rd` | `rol.w` | `orri` | `m9` |
| `rol.w_orrr_rd` | `rol.w` | `orrr` | `m9` |
| `sc.b.nn_orrr_rd` | `sc.b.nn` | `orrr` | `m9` |
| `sc.b.nr_orrr_rd` | `sc.b.nr` | `orrr` | `m9` |
| `sc.o.nn_orrr_rd` | `sc.o.nn` | `orrr` | `m9` |
| `sc.o.nr_orrr_rd` | `sc.o.nr` | `orrr` | `m9` |
| `sc.t.nn_orrr_rd` | `sc.t.nn` | `orrr` | `m9` |
| `sc.t.nr_orrr_rd` | `sc.t.nr` | `orrr` | `m9` |
| `sc.w.nn_orrr_rd` | `sc.w.nn` | `orrr` | `m9` |
| `sc.w.nr_orrr_rd` | `sc.w.nr` | `orrr` | `m9` |
| `shr.so_orri_rd` | `shr.so` | `orri` | `m1` |
| `shr.uo_orri_rd` | `shr.uo` | `orri` | `m1` |
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

### 3.3 仅 post-ISel 引用（4 条）

| id | mnemonic | format | scope |
|---|---|---|---|
| `fo2fo_orri_rf` | `fo2fo` | `orri` | `fp` |
| `ldm.o_rrri_rb` | `ldm.o` | `rrri` | `m1` |
| `ldm.o_rrri_rd` | `ldm.o` | `rrri` | `m1` |
| `rd2rb_orri_rb` | `rd2rb` | `orri` | `m1` |

### 3.4 scope: excluded（未实现）（2 条）

| id | mnemonic | format | scope |
|---|---|---|---|
| `cfxld_crii_cfx` | `cfxld` | `crii` | `excluded` |
| `cfxst_crii_cfx` | `cfxst` | `crii` | `excluded` |

