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

现场统计：证据条数 = buildmi 63 + isel-cpp 64 + pat 293 + pat-args 8 + pseudo 19；判「用得上」的记录 **202** 条。

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
| `add.o_orrr_bbd` | `add.o` | `orrr` | `m1` | accept | yes | buildmi:DADAORegisterInfo.cpp.patch:191:add_o_bbd;isel-cpp:DADAOISelDAGToDAG.cpp.patch:167:add_o_bbd;isel-cpp:DADAOISelDAGToDAG.cpp.patch:203:add_o_bbd;isel-cpp:DADAOISelDAGToDAG.cpp.patch:556:add_o_bbd;isel-cpp:DADAOISelDAGToDAG.cpp.patch:583:add_o_bbd;isel-cpp:DADAOISelDAGToDAG.cpp.patch:637:add_o_bbd |
| `add.sb_orrr_rd` | `add.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:565:add_sb;pat:DADAOCodeGen.td.patch:612:add_sb |
| `add.si_riii_rb` | `add.si` | `riii` | `m1` | accept | yes | buildmi:DADAOFrameLowering.cpp.patch:193:add_si_rb;buildmi:DADAOFrameLowering.cpp.patch:372:add_si_rb;buildmi:DADAOFrameLowering.cpp.patch:497:add_si_rb;buildmi:DADAOLoadStoreOptimizer.cpp.patch:273:add_si_rb;buildmi:DADAORegisterInfo.cpp.patch:210:add_si_rb;buildmi:DADAORegisterInfo.cpp.patch:260:add_si_rb |
| `add.si_riii_rd` | `add.si` | `riii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:314:add_si_rd;pseudo:DADAOCodeGen.td.patch:360:add_si_rd:ADD_IMM_PSEUDO |
| `add.so_rrrr_rd` | `add.so` | `rrrr` | `m1` | accept | no | — |
| `add.st_orrr_rd` | `add.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:563:add_st;pat:DADAOCodeGen.td.patch:592:add_st |
| `add.sw_orrr_rd` | `add.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:564:add_sw;pat:DADAOCodeGen.td.patch:602:add_sw |
| `add.ub_orrr_rd` | `add.ub` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:613:add_ub |
| `add.uo_rrrr_rd` | `add.uo` | `rrrr` | `m1` | accept | yes | pseudo:DADAOCodeGen.td.patch:252:add_uo_rd:ADD_PSEUDO;pseudo:DADAOCodeGen.td.patch:254:add_uo_rd:SUB_PSEUDO;pseudo:DADAOCodeGen.td.patch:263:add_uo_rd:MUL_PSEUDO |
| `add.ut_orrr_rd` | `add.ut` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:593:add_ut |
| `add.uw_orrr_rd` | `add.uw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:603:add_uw |
| `aip.si_riii_rb` | `aip.si` | `riii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:489:aip_si_rb |
| `and.o_orrr_rd` | `and.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:450:and_o;pat:DADAOCodeGen.td.patch:1152:and_o |
| `andn.w_rwii_rb` | `andn.w` | `rwii` | `m1` | accept | no | — |
| `andn.w_rwii_rd` | `andn.w` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:364:andn_w_rd;buildmi:DADAOPointerPHIBank.cpp.patch:165:andn_w_rd:CONST_WYDE |
| `br.eq_rrii_rd` | `br.eq` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:912:br_eq_rd |
| `br.n_riii_rd` | `br.n` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:906:br_n_rd |
| `br.ne_rrii_rd` | `br.ne` | `rrii` | `m1` | accept | yes | buildmi:DADAOISelLowering.cpp.patch:3095:br_ne_rd;isel-cpp:DADAOISelLowering.cpp.patch:3095:br_ne_rd;pat:DADAOCodeGen.td.patch:913:br_ne_rd |
| `br.nn_riii_rd` | `br.nn` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:907:br_nn_rd |
| `br.np_riii_rd` | `br.np` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:909:br_np_rd |
| `br.nz_riii_rb` | `br.nz` | `riii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:826:br_nz_rb |
| `br.nz_riii_rd` | `br.nz` | `riii` | `m1` | accept | yes | buildmi:DADAOISelLowering.cpp.patch:3106:br_nz_rd;isel-cpp:DADAOISelLowering.cpp.patch:3106:br_nz_rd;pat:DADAOCodeGen.td.patch:905:br_nz_rd |
| `br.p_riii_rd` | `br.p` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:908:br_p_rd |
| `br.z_riii_rb` | `br.z` | `riii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:825:br_z_rb |
| `br.z_riii_rd` | `br.z` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:904:br_z_rd |
| `call_iiii_ra` | `call` | `iiii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:713:call_iiii |
| `call_rrii_ra` | `call` | `rrii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:713:call_rrii |
| `cfx2rc_crrr_cfx` | `cfx2rc` | `crrr` | `m1` | accept | no | — |
| `cfx2rd_crrr_cfx` | `cfx2rd` | `crrr` | `m1` | accept | no | — |
| `cfxld_crii_cfx` | `cfxld` | `crii` | `excluded` | reject | no | — |
| `cfxst_crii_cfx` | `cfxst` | `crii` | `excluded` | reject | no | — |
| `clmul.o_rrrr_rd` | `clmul.o` | `rrrr` | `m9` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:253:clmul_o_rd;buildmi:DADAOInstrInfo.cpp.patch:267:clmul_o_rd;buildmi:DADAOInstrInfo.cpp.patch:283:clmul_o_rd;pseudo:DADAOCodeGen.td.patch:328:clmul_o_rd:CLMUL_PSEUDO;pseudo:DADAOCodeGen.td.patch:330:clmul_o_rd:CLMULHI_PSEUDO |
| `cmp.sb_orrr_rd` | `cmp.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:895:cmp_sb |
| `cmp.si_rrii_rd` | `cmp.si` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:874:cmp_si_rd;pat:DADAOCodeGen.td.patch:1148:cmp_si_rd;pat:DADAOCodeGen.td.patch:1150:cmp_si_rd;pat:DADAOCodeGen.td.patch:1152:cmp_si_rd;pat:DADAOCodeGen.td.patch:1156:cmp_si_rd |
| `cmp.so_orrr_rd` | `cmp.so` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:872:cmp_so |
| `cmp.st_orrr_rd` | `cmp.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:891:cmp_st |
| `cmp.sw_orrr_rd` | `cmp.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:893:cmp_sw |
| `cmp.ub_orrr_rd` | `cmp.ub` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:901:cmp_ub |
| `cmp.ui_rrii_rd` | `cmp.ui` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:884:cmp_ui_rd |
| `cmp.uo_orrr_dbb` | `cmp.uo` | `orrr` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:811:cmp_uo_dbb |
| `cmp.uo_orrr_rd` | `cmp.uo` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:882:cmp_uo |
| `cmp.ut_orrr_rd` | `cmp.ut` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:897:cmp_ut |
| `cmp.uw_orrr_rd` | `cmp.uw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:899:cmp_uw |
| `cs.eq_rrrr_rd` | `cs.eq` | `rrrr` | `m1` | accept | no | — |
| `cs.n_rrrr_rd` | `cs.n` | `rrrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:919:cs_n_rd;pat:DADAOCodeGen.td.patch:927:cs_n_rd;pat:DADAOCodeGen.td.patch:933:cs_n_rd;pat:DADAOCodeGen.td.patch:939:cs_n_rd |
| `cs.n_rrrr_rf` | `cs.n` | `rrrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:951:cs_n_rrrr_rf;pat:DADAOCodeGen.td.patch:957:cs_n_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1162:cs_n_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1165:cs_n_rrrr_rf |
| `cs.ne_rrrr_rd` | `cs.ne` | `rrrr` | `m1` | accept | no | — |
| `cs.p_rrrr_rd` | `cs.p` | `rrrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:921:cs_p_rd;pat:DADAOCodeGen.td.patch:931:cs_p_rd;pat:DADAOCodeGen.td.patch:937:cs_p_rd;pat:DADAOCodeGen.td.patch:943:cs_p_rd;pat:DADAOCodeGen.td.patch:1152:cs_p_rd;pat:DADAOCodeGen.td.patch:1156:cs_p_rd |
| `cs.p_rrrr_rf` | `cs.p` | `rrrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:955:cs_p_rrrr_rf;pat:DADAOCodeGen.td.patch:961:cs_p_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1163:cs_p_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1166:cs_p_rrrr_rf |
| `cs.z_rrrr_rd` | `cs.z` | `rrrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:920:cs_z_rd;pat:DADAOCodeGen.td.patch:929:cs_z_rd;pat:DADAOCodeGen.td.patch:935:cs_z_rd;pat:DADAOCodeGen.td.patch:941:cs_z_rd;pat:DADAOCodeGen.td.patch:1153:cs_z_rd;pat:DADAOCodeGen.td.patch:1157:cs_z_rd |
| `cs.z_rrrr_rf` | `cs.z` | `rrrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:953:cs_z_rrrr_rf;pat:DADAOCodeGen.td.patch:959:cs_z_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1162:cs_z_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1165:cs_z_rrrr_rf |
| `ctlz_orri_rd` | `ctlz` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:506:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:507:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:515:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:516:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:517:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:519:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:521:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:523:ctlz_orri_rd |
| `ctpop_orri_rd` | `ctpop` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:510:ctpop_orri_rd;pat:DADAOCodeGen.td.patch:533:ctpop_orri_rd;pat:DADAOCodeGen.td.patch:534:ctpop_orri_rd;pat:DADAOCodeGen.td.patch:535:ctpop_orri_rd |
| `cttz_orri_rd` | `cttz` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:508:cttz_orri_rd;pat:DADAOCodeGen.td.patch:509:cttz_orri_rd;pat:DADAOCodeGen.td.patch:524:cttz_orri_rd;pat:DADAOCodeGen.td.patch:525:cttz_orri_rd;pat:DADAOCodeGen.td.patch:526:cttz_orri_rd;pat:DADAOCodeGen.td.patch:528:cttz_orri_rd;pat:DADAOCodeGen.td.patch:530:cttz_orri_rd;pat:DADAOCodeGen.td.patch:532:cttz_orri_rd |
| `div.sb_orrr_rd` | `div.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:578:div_sb;pat:DADAOCodeGen.td.patch:620:div_sb |
| `div.so_orrr_rd` | `div.so` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:547:div_so |
| `div.st_orrr_rd` | `div.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:576:div_st;pat:DADAOCodeGen.td.patch:600:div_st |
| `div.sw_orrr_rd` | `div.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:577:div_sw;pat:DADAOCodeGen.td.patch:610:div_sw |
| `div.ub_orrr_rd` | `div.ub` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:575:div_ub;pat:DADAOCodeGen.td.patch:618:div_ub |
| `div.uo_orrr_rd` | `div.uo` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:546:div_uo |
| `div.ut_orrr_rd` | `div.ut` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:573:div_ut;pat:DADAOCodeGen.td.patch:598:div_ut |
| `div.uw_orrr_rd` | `div.uw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:574:div_uw;pat:DADAOCodeGen.td.patch:608:div_uw |
| `escape_ciii_cfx` | `escape` | `ciii` | `m1` | accept | no | — |
| `ext.so_orri_rd` | `ext.so` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:326:ext_so_orri;pat:DADAOCodeGen.td.patch:682:ext_so_orri;pat:DADAOCodeGen.td.patch:683:ext_so_orri;pat:DADAOCodeGen.td.patch:684:ext_so_orri;pat:DADAOCodeGen.td.patch:685:ext_so_orri;pat:DADAOCodeGen.td.patch:686:ext_so_orri;pat:DADAOCodeGen.td.patch:687:ext_so_orri;pat:DADAOCodeGen.td.patch:729:ext_so_orri;pat:DADAOCodeGen.td.patch:730:ext_so_orri;pat:DADAOCodeGen.td.patch:731:ext_so_orri;pat:DADAOCodeGen.td.patch:736:ext_so_orri;pat:DADAOCodeGen.td.patch:740:ext_so_orri;pat:DADAOCodeGen.td.patch:742:ext_so_orri;pat:DADAOCodeGen.td.patch:744:ext_so_orri;pat:DADAOCodeGen.td.patch:750:ext_so_orri;pat:DADAOCodeGen.td.patch:752:ext_so_orri;pat:DADAOCodeGen.td.patch:754:ext_so_orri |
| `ext.so_orrr_rd` | `ext.so` | `orrr` | `m1` | accept | no | — |
| `ext.uo_orri_rd` | `ext.uo` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:327:ext_uo_orri;pat:DADAOCodeGen.td.patch:668:ext_uo_orri;pat:DADAOCodeGen.td.patch:669:ext_uo_orri;pat:DADAOCodeGen.td.patch:670:ext_uo_orri;pat:DADAOCodeGen.td.patch:671:ext_uo_orri;pat:DADAOCodeGen.td.patch:672:ext_uo_orri;pat:DADAOCodeGen.td.patch:673:ext_uo_orri;pat:DADAOCodeGen.td.patch:675:ext_uo_orri;pat:DADAOCodeGen.td.patch:676:ext_uo_orri;pat:DADAOCodeGen.td.patch:677:ext_uo_orri;pat:DADAOCodeGen.td.patch:678:ext_uo_orri;pat:DADAOCodeGen.td.patch:679:ext_uo_orri;pat:DADAOCodeGen.td.patch:680:ext_uo_orri;pat:DADAOCodeGen.td.patch:691:ext_uo_orri;pat:DADAOCodeGen.td.patch:692:ext_uo_orri;pat:DADAOCodeGen.td.patch:693:ext_uo_orri;pat:DADAOCodeGen.td.patch:694:ext_uo_orri;pat:DADAOCodeGen.td.patch:695:ext_uo_orri;pat:DADAOCodeGen.td.patch:696:ext_uo_orri;pat:DADAOCodeGen.td.patch:702:ext_uo_orri;pat:DADAOCodeGen.td.patch:704:ext_uo_orri;pat:DADAOCodeGen.td.patch:706:ext_uo_orri |
| `ext.uo_orrr_rd` | `ext.uo` | `orrr` | `m1` | accept | no | — |
| `fence_oiii_imm` | `fence` | `oiii` | `m9` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:770:fence |
| `fo2fo_orri_rf` | `fo2fo` | `orri` | `fp` | accept | no | — |
| `fo2ft_orri_rf` | `fo2ft` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1181:fo2ft_orri_rf |
| `fo2io_orri_rf` | `fo2io` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:859:fo2io_orri_rf;pat:DADAOCodeGen.td.patch:1187:fo2io_orri_rf |
| `fo2it_orri_rf` | `fo2it` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:859:fo2it_orri_rf |
| `fo2uo_orri_rf` | `fo2uo` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:859:fo2uo_orri_rf;pat:DADAOCodeGen.td.patch:1189:fo2uo_orri_rf |
| `fo2ut_orri_rf` | `fo2ut` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:860:fo2ut_orri_rf |
| `foadd_orrr_rf` | `foadd` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:976:foadd_orrr_rf |
| `focls_orri_rf` | `focls` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1090:focls_orri_rf |
| `fodiv_orrr_rf` | `fodiv` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:990:fodiv_orrr_rf |
| `fofma_rrrr_rf` | `fofma` | `rrrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:989:fofma_rrrr_rf |
| `fomax_orrr_rf` | `fomax` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1039:fomax_orrr_rf;pat:DADAOCodeGen.td.patch:1041:fomax_orrr_rf |
| `fomin_orrr_rf` | `fomin` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1038:fomin_orrr_rf;pat:DADAOCodeGen.td.patch:1040:fomin_orrr_rf |
| `fomul_orrr_rf` | `fomul` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:978:fomul_orrr_rf |
| `foqcmp_orrr_rf` | `foqcmp` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1083:foqcmp_orrr_rf;pat-args:DADAOCodeGen.td.patch:1162:foqcmp_orrr_rf |
| `forem_orrr_rf` | `forem` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1105:forem_orrr_rf |
| `fornd_orri_rf` | `fornd` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1067:fornd_orri_rf;pat:DADAOCodeGen.td.patch:1068:fornd_orri_rf;pat:DADAOCodeGen.td.patch:1069:fornd_orri_rf;pat:DADAOCodeGen.td.patch:1070:fornd_orri_rf;pat:DADAOCodeGen.td.patch:1071:fornd_orri_rf;pat:DADAOCodeGen.td.patch:1072:fornd_orri_rf;pat:DADAOCodeGen.td.patch:1073:fornd_orri_rf |
| `foroot_orri_rf` | `foroot` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:992:foroot_orri_rf |
| `fosclb_orrr_rf` | `fosclb` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1096:fosclb_orrr_rf |
| `foscmp_orrr_rf` | `foscmp` | `orrr` | `fp` | accept | no | — |
| `fosgnj_orrr_rf` | `fosgnj` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1003:fosgnj_orrr_rf;pat:DADAOCodeGen.td.patch:1005:fosgnj_orrr_rf |
| `fosgnn_orrr_rf` | `fosgnn` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:994:fosgnn_orrr_rf |
| `fosub_orrr_rf` | `fosub` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:977:fosub_orrr_rf |
| `ft2fo_orri_rf` | `ft2fo` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1180:ft2fo_orri_rf |
| `ft2ft_orri_rf` | `ft2ft` | `orri` | `fp` | accept | no | — |
| `ft2io_orri_rf` | `ft2io` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:860:ft2io_orri_rf;pat:DADAOCodeGen.td.patch:1188:ft2io_orri_rf |
| `ft2it_orri_rf` | `ft2it` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:861:ft2it_orri_rf |
| `ft2uo_orri_rf` | `ft2uo` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:860:ft2uo_orri_rf;pat:DADAOCodeGen.td.patch:1190:ft2uo_orri_rf |
| `ft2ut_orri_rf` | `ft2ut` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:861:ft2ut_orri_rf |
| `ftadd_orrr_rf` | `ftadd` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1008:ftadd_orrr_rf |
| `ftcls_orri_rf` | `ftcls` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1091:ftcls_orri_rf |
| `ftdiv_orrr_rf` | `ftdiv` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1013:ftdiv_orrr_rf |
| `ftfma_rrrr_rf` | `ftfma` | `rrrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1012:ftfma_rrrr_rf |
| `ftmax_orrr_rf` | `ftmax` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1043:ftmax_orrr_rf;pat:DADAOCodeGen.td.patch:1045:ftmax_orrr_rf |
| `ftmin_orrr_rf` | `ftmin` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1042:ftmin_orrr_rf;pat:DADAOCodeGen.td.patch:1044:ftmin_orrr_rf |
| `ftmul_orrr_rf` | `ftmul` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1010:ftmul_orrr_rf |
| `ftqcmp_orrr_rf` | `ftqcmp` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1084:ftqcmp_orrr_rf;pat-args:DADAOCodeGen.td.patch:1165:ftqcmp_orrr_rf |
| `ftrem_orrr_rf` | `ftrem` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1107:ftrem_orrr_rf |
| `ftrnd_orri_rf` | `ftrnd` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1074:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:1075:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:1076:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:1077:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:1078:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:1079:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:1080:ftrnd_orri_rf |
| `ftroot_orri_rf` | `ftroot` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1014:ftroot_orri_rf |
| `ftsclb_orrr_rf` | `ftsclb` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1097:ftsclb_orrr_rf |
| `ftscmp_orrr_rf` | `ftscmp` | `orrr` | `fp` | accept | no | — |
| `ftsgnj_orrr_rf` | `ftsgnj` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1019:ftsgnj_orrr_rf;pat:DADAOCodeGen.td.patch:1021:ftsgnj_orrr_rf |
| `ftsgnn_orrr_rf` | `ftsgnn` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1015:ftsgnn_orrr_rf |
| `ftsub_orrr_rf` | `ftsub` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1009:ftsub_orrr_rf |
| `io2fo_orri_rf` | `io2fo` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1194:io2fo_orri_rf |
| `io2ft_orri_rf` | `io2ft` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1195:io2ft_orri_rf |
| `it2fo_orri_rf` | `it2fo` | `orri` | `fp` | accept | no | — |
| `it2ft_orri_rf` | `it2ft` | `orri` | `fp` | accept | no | — |
| `jump_iiii_rb` | `jump` | `iiii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:741:jump_iiii;buildmi:DADAOInstrInfo.cpp.patch:761:jump_iiii;isel-cpp:DADAOISelDAGToDAG.cpp.patch:758:tailjmp_iiii;pat:DADAOCodeGen.td.patch:964:jump_iiii |
| `jump_rrii_rb` | `jump` | `rrii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:646:jump_rrii;isel-cpp:DADAOISelDAGToDAG.cpp.patch:668:jump_rrii;isel-cpp:DADAOISelDAGToDAG.cpp.patch:758:tailjmp_rrii |
| `ld.o_rrii_ra` | `ld.o` | `rrii` | `m1` | accept | no | — |
| `ld.o_rrii_rb` | `ld.o` | `rrii` | `m1` | accept | yes | buildmi:DADAOFrameLowering.cpp.patch:465:ld_o_rb;buildmi:DADAOInstrInfo.cpp.patch:491:ld_o_rb;isel-cpp:DADAOISelDAGToDAG.cpp.patch:175:ld_o_rb;isel-cpp:DADAOISelDAGToDAG.cpp.patch:639:ld_o_rb |
| `ld.o_rrii_rd` | `ld.o` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:800:ld_o_rd |
| `ld.o_rrii_rf` | `ld.o` | `rrii` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1170:ld_o_rrii_rf |
| `ld.sb_rrii_rd` | `ld.sb` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:807:ld_sb_rd;pat:DADAOCodeGen.td.patch:844:ld_sb_rd;pat:DADAOCodeGen.td.patch:845:ld_sb_rd |
| `ld.st_rrii_rd` | `ld.st` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:822:ld_st_rd |
| `ld.sw_rrii_rd` | `ld.sw` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:815:ld_sw_rd;pat:DADAOCodeGen.td.patch:849:ld_sw_rd |
| `ld.t_rrii_rf` | `ld.t` | `rrii` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1174:ld_t_rrii_rf |
| `ld.ub_rrii_rd` | `ld.ub` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:805:ld_ub_rd;pat:DADAOCodeGen.td.patch:806:ld_ub_rd;pat:DADAOCodeGen.td.patch:833:ld_ub_rd;pat:DADAOCodeGen.td.patch:840:ld_ub_rd;pat:DADAOCodeGen.td.patch:841:ld_ub_rd;pat:DADAOCodeGen.td.patch:842:ld_ub_rd;pat:DADAOCodeGen.td.patch:843:ld_ub_rd |
| `ld.ut_rrii_rd` | `ld.ut` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:820:ld_ut_rd;pat:DADAOCodeGen.td.patch:821:ld_ut_rd;pat:DADAOCodeGen.td.patch:835:ld_ut_rd |
| `ld.uw_rrii_rd` | `ld.uw` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:813:ld_uw_rd;pat:DADAOCodeGen.td.patch:814:ld_uw_rd;pat:DADAOCodeGen.td.patch:834:ld_uw_rd;pat:DADAOCodeGen.td.patch:847:ld_uw_rd;pat:DADAOCodeGen.td.patch:848:ld_uw_rd |
| `ldm.o_rrri_ra` | `ldm.o` | `rrri` | `m1` | accept | no | — |
| `ldm.o_rrri_rb` | `ldm.o` | `rrri` | `m1` | accept | yes | buildmi:DADAOLoadStoreOptimizer.cpp.patch:284:ldm_o_rb |
| `ldm.o_rrri_rd` | `ldm.o` | `rrri` | `m1` | accept | yes | buildmi:DADAOLoadStoreOptimizer.cpp.patch:283:ldm_o_rd |
| `ldm.o_rrri_rf` | `ldm.o` | `rrri` | `fp` | accept | no | — |
| `ldm.sb_rrri_rd` | `ldm.sb` | `rrri` | `m1` | accept | no | — |
| `ldm.st_rrri_rd` | `ldm.st` | `rrri` | `m1` | accept | no | — |
| `ldm.sw_rrri_rd` | `ldm.sw` | `rrri` | `m1` | accept | no | — |
| `ldm.t_rrri_rf` | `ldm.t` | `rrri` | `fp` | accept | no | — |
| `ldm.ub_rrri_rd` | `ldm.ub` | `rrri` | `m1` | accept | no | — |
| `ldm.ut_rrri_rd` | `ldm.ut` | `rrri` | `m1` | accept | no | — |
| `ldm.uw_rrri_rd` | `ldm.uw` | `rrri` | `m1` | accept | no | — |
| `lr.b.an_orrr_rd` | `lr.b.an` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:3028:lr_b_an |
| `lr.b.ar_orrr_rd` | `lr.b.ar` | `orrr` | `m9` | accept | no | — |
| `lr.b.nn_orrr_rd` | `lr.b.nn` | `orrr` | `m9` | accept | no | — |
| `lr.o.an_orrr_rd` | `lr.o.an` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:3040:lr_o_an |
| `lr.o.ar_orrr_rd` | `lr.o.ar` | `orrr` | `m9` | accept | no | — |
| `lr.o.nn_orrr_rd` | `lr.o.nn` | `orrr` | `m9` | accept | no | — |
| `lr.t.an_orrr_rd` | `lr.t.an` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:3036:lr_t_an |
| `lr.t.ar_orrr_rd` | `lr.t.ar` | `orrr` | `m9` | accept | no | — |
| `lr.t.nn_orrr_rd` | `lr.t.nn` | `orrr` | `m9` | accept | no | — |
| `lr.w.an_orrr_rd` | `lr.w.an` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:3032:lr_w_an |
| `lr.w.ar_orrr_rd` | `lr.w.ar` | `orrr` | `m9` | accept | no | — |
| `lr.w.nn_orrr_rd` | `lr.w.nn` | `orrr` | `m9` | accept | no | — |
| `mul.sb_orrr_rd` | `mul.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:571:mul_sb;pat:DADAOCodeGen.td.patch:616:mul_sb |
| `mul.so_rrrr_rd` | `mul.so` | `rrrr` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:222:mul_so_rd;buildmi:DADAOInstrInfo.cpp.patch:238:mul_so_rd;pseudo:DADAOCodeGen.td.patch:298:mul_so_rd:MULHS_PSEUDO;pseudo:DADAOCodeGen.td.patch:307:mul_so_rd:SMUL_LOHI_PSEUDO |
| `mul.st_orrr_rd` | `mul.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:569:mul_st;pat:DADAOCodeGen.td.patch:596:mul_st |
| `mul.sw_orrr_rd` | `mul.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:570:mul_sw;pat:DADAOCodeGen.td.patch:606:mul_sw |
| `mul.ub_orrr_rd` | `mul.ub` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:617:mul_ub |
| `mul.uo_rrrr_rd` | `mul.uo` | `rrrr` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:190:mul_uo_rd;buildmi:DADAOInstrInfo.cpp.patch:206:mul_uo_rd;pseudo:DADAOCodeGen.td.patch:252:mul_uo_rd:ADD_PSEUDO;pseudo:DADAOCodeGen.td.patch:254:mul_uo_rd:SUB_PSEUDO;pseudo:DADAOCodeGen.td.patch:263:mul_uo_rd:MUL_PSEUDO;pseudo:DADAOCodeGen.td.patch:275:mul_uo_rd:MULHU_PSEUDO;pseudo:DADAOCodeGen.td.patch:284:mul_uo_rd:UMUL_LOHI_PSEUDO |
| `mul.ut_orrr_rd` | `mul.ut` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:597:mul_ut |
| `mul.uw_orrr_rd` | `mul.uw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:607:mul_uw |
| `or.o_orrr_rd` | `or.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:451:or_o;pat:DADAOCodeGen.td.patch:1156:or_o |
| `or.w_rwii_rb` | `or.w` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:399:or_w_rb;buildmi:DADAOInstrInfo.cpp.patch:400:or_w_rb;buildmi:DADAOInstrInfo.cpp.patch:437:or_w_rb;buildmi:DADAOInstrInfo.cpp.patch:438:or_w_rb;buildmi:DADAOInstrInfo.cpp.patch:456:or_w_rb;buildmi:DADAOInstrInfo.cpp.patch:457:or_w_rb |
| `or.w_rwii_rd` | `or.w` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:131:or_w_rd;buildmi:DADAOInstrInfo.cpp.patch:370:or_w_rd;buildmi:DADAOInstrInfo.cpp.patch:418:or_w_rd;buildmi:DADAOInstrInfo.cpp.patch:419:or_w_rd;buildmi:DADAOPointerPHIBank.cpp.patch:165:or_w_rd:CONST_WYDE |
| `ra2rd_orri_ra` | `ra2rd` | `orri` | `m1` | accept | no | — |
| `rb2rb_orri_rb` | `rb2rb` | `orri` | `m1` | accept | yes | buildmi:DADAOFrameLowering.cpp.patch:368:rb2rb;buildmi:DADAOFrameLowering.cpp.patch:430:rb2rb;buildmi:DADAOFrameLowering.cpp.patch:461:rb2rb;buildmi:DADAOLoadStoreOptimizer.cpp.patch:270:rb2rb;buildmi:DADAORegisterInfo.cpp.patch:206:rb2rb;buildmi:DADAORegisterInfo.cpp.patch:215:rb2rb;buildmi:DADAORegisterInfo.cpp.patch:257:rb2rb |
| `rb2rd_orri_rb` | `rb2rd` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:580:rb2rd |
| `rd2ra_orri_ra` | `rd2ra` | `orri` | `m1` | accept | no | — |
| `rd2rb_orri_rb` | `rd2rb` | `orri` | `m1` | accept | no | — |
| `rd2rd_orri_rd` | `rd2rd` | `orri` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:313:rd2rd;pseudo:DADAOCodeGen.td.patch:360:rd2rd:ADD_IMM_PSEUDO |
| `rd2rf_orri_rf` | `rd2rf` | `orri` | `fp` | accept | yes | buildmi:DADAOISelLowering.cpp.patch:3010:rd2rf_orri_rf;isel-cpp:DADAOISelDAGToDAG.cpp.patch:367:rd2rf_orri_rf;isel-cpp:DADAOISelLowering.cpp.patch:3010:rd2rf_orri_rf;pat:DADAOCodeGen.td.patch:711:rd2rf_orri_rf;pat:DADAOCodeGen.td.patch:1005:rd2rf_orri_rf;pat:DADAOCodeGen.td.patch:1021:rd2rf_orri_rf;pat:DADAOCodeGen.td.patch:1205:rd2rf_orri_rf |
| `rem.sb_orrr_rd` | `rem.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:584:rem_sb;pat:DADAOCodeGen.td.patch:621:rem_sb |
| `rem.so_orrr_rd` | `rem.so` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:549:rem_so |
| `rem.st_orrr_rd` | `rem.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:582:rem_st;pat:DADAOCodeGen.td.patch:601:rem_st |
| `rem.sw_orrr_rd` | `rem.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:583:rem_sw;pat:DADAOCodeGen.td.patch:611:rem_sw |
| `rem.ub_orrr_rd` | `rem.ub` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:581:rem_ub;pat:DADAOCodeGen.td.patch:619:rem_ub |
| `rem.uo_orrr_rd` | `rem.uo` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:548:rem_uo |
| `rem.ut_orrr_rd` | `rem.ut` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:579:rem_ut;pat:DADAOCodeGen.td.patch:599:rem_ut |
| `rem.uw_orrr_rd` | `rem.uw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:580:rem_uw;pat:DADAOCodeGen.td.patch:609:rem_uw |
| `ret_riii_ra` | `ret` | `riii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:153:ret_riii;pseudo:DADAOCodeGen.td.patch:222:ret_riii:RET_PSEUDO |
| `rev.b_orri_rd` | `rev.b` | `orri` | `m8` | accept | no | — |
| `rev.o_orri_rd` | `rev.o` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:540:rev_o_orri_rd;pat:DADAOCodeGen.td.patch:541:rev_o_orri_rd |
| `rev.t_orri_rd` | `rev.t` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:650:rev_t_orri_rd |
| `rev.w_orri_rd` | `rev.w` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:651:rev_w_orri_rd |
| `rf2rd_orri_rf` | `rf2rd` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:712:rf2rd_orri_rf;pat:DADAOCodeGen.td.patch:1206:rf2rd_orri_rf |
| `rol.b_orri_rd` | `rol.b` | `orri` | `m9` | accept | no | — |
| `rol.b_orrr_rd` | `rol.b` | `orrr` | `m9` | accept | no | — |
| `rol.o_orri_rd` | `rol.o` | `orri` | `m9` | accept | yes | pat:DADAOCodeGen.td.patch:489:rol_o_orri |
| `rol.o_orrr_rd` | `rol.o` | `orrr` | `m9` | accept | yes | pat:DADAOCodeGen.td.patch:490:rol_o_orrr |
| `rol.t_orri_rd` | `rol.t` | `orri` | `m9` | accept | no | — |
| `rol.t_orrr_rd` | `rol.t` | `orrr` | `m9` | accept | no | — |
| `rol.w_orri_rd` | `rol.w` | `orri` | `m9` | accept | no | — |
| `rol.w_orrr_rd` | `rol.w` | `orrr` | `m9` | accept | no | — |
| `sc.b.ar_orrr_rd` | `sc.b.ar` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:3029:sc_b_ar |
| `sc.b.nn_orrr_rd` | `sc.b.nn` | `orrr` | `m9` | accept | no | — |
| `sc.b.nr_orrr_rd` | `sc.b.nr` | `orrr` | `m9` | accept | no | — |
| `sc.o.ar_orrr_rd` | `sc.o.ar` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:3041:sc_o_ar |
| `sc.o.nn_orrr_rd` | `sc.o.nn` | `orrr` | `m9` | accept | no | — |
| `sc.o.nr_orrr_rd` | `sc.o.nr` | `orrr` | `m9` | accept | no | — |
| `sc.t.ar_orrr_rd` | `sc.t.ar` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:3037:sc_t_ar |
| `sc.t.nn_orrr_rd` | `sc.t.nn` | `orrr` | `m9` | accept | no | — |
| `sc.t.nr_orrr_rd` | `sc.t.nr` | `orrr` | `m9` | accept | no | — |
| `sc.w.ar_orrr_rd` | `sc.w.ar` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:3033:sc_w_ar |
| `sc.w.nn_orrr_rd` | `sc.w.nn` | `orrr` | `m9` | accept | no | — |
| `sc.w.nr_orrr_rd` | `sc.w.nr` | `orrr` | `m9` | accept | no | — |
| `set.ow_rwii_rd` | `set.ow` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:346:set_ow_rd;buildmi:DADAOInstrInfo.cpp.patch:354:set_ow_rd;buildmi:DADAOPointerPHIBank.cpp.patch:165:set_ow_rd:CONST_WYDE |
| `set.w_rwii_rf` | `set.w` | `rwii` | `fp` | accept | yes | buildmi:DADAOISelLowering.cpp.patch:3006:set_w_rwii_rf;isel-cpp:DADAOISelLowering.cpp.patch:3006:set_w_rwii_rf |
| `set.zw_rwii_rb` | `set.zw` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:398:set_zw_rb;buildmi:DADAOInstrInfo.cpp.patch:436:set_zw_rb;buildmi:DADAOInstrInfo.cpp.patch:455:set_zw_rb |
| `set.zw_rwii_rd` | `set.zw` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:131:set_zw_rd;buildmi:DADAOInstrInfo.cpp.patch:349:set_zw_rd;buildmi:DADAOInstrInfo.cpp.patch:354:set_zw_rd;buildmi:DADAOInstrInfo.cpp.patch:417:set_zw_rd;buildmi:DADAOPointerPHIBank.cpp.patch:165:set_zw_rd:CONST_WYDE |
| `shl.b_orri_rd` | `shl.b` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:465:shl_b_orri |
| `shl.b_orrr_rd` | `shl.b` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:628:shl_b_orrr;pat:DADAOCodeGen.td.patch:641:shl_b_orrr |
| `shl.o_orri_rd` | `shl.o` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:463:shl_o_orri;isel-cpp:DADAOISelDAGToDAG.cpp.patch:635:shl_o_orri |
| `shl.o_orrr_rd` | `shl.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:479:shl_o_orrr |
| `shl.t_orri_rd` | `shl.t` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:464:shl_t_orri |
| `shl.t_orrr_rd` | `shl.t` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:622:shl_t_orrr;pat:DADAOCodeGen.td.patch:639:shl_t_orrr |
| `shl.w_orri_rd` | `shl.w` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:465:shl_w_orri |
| `shl.w_orrr_rd` | `shl.w` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:625:shl_w_orrr;pat:DADAOCodeGen.td.patch:640:shl_w_orrr |
| `shr.sb_orri_rd` | `shr.sb` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:475:shr_sb_orri |
| `shr.sb_orrr_rd` | `shr.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:630:shr_sb_orrr;pat:DADAOCodeGen.td.patch:647:shr_sb_orrr |
| `shr.so_orri_rd` | `shr.so` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:473:shr_so_orri |
| `shr.so_orrr_rd` | `shr.so` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:481:shr_so_orrr |
| `shr.st_orri_rd` | `shr.st` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:474:shr_st_orri |
| `shr.st_orrr_rd` | `shr.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:624:shr_st_orrr;pat:DADAOCodeGen.td.patch:645:shr_st_orrr |
| `shr.sw_orri_rd` | `shr.sw` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:475:shr_sw_orri |
| `shr.sw_orrr_rd` | `shr.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:627:shr_sw_orrr;pat:DADAOCodeGen.td.patch:646:shr_sw_orrr |
| `shr.ub_orri_rd` | `shr.ub` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:470:shr_ub_orri |
| `shr.ub_orrr_rd` | `shr.ub` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:629:shr_ub_orrr;pat:DADAOCodeGen.td.patch:644:shr_ub_orrr |
| `shr.uo_orri_rd` | `shr.uo` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:468:shr_uo_orri |
| `shr.uo_orrr_rd` | `shr.uo` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:480:shr_uo_orrr |
| `shr.ut_orri_rd` | `shr.ut` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:469:shr_ut_orri |
| `shr.ut_orrr_rd` | `shr.ut` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:623:shr_ut_orrr;pat:DADAOCodeGen.td.patch:642:shr_ut_orrr |
| `shr.uw_orri_rd` | `shr.uw` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:470:shr_uw_orri |
| `shr.uw_orrr_rd` | `shr.uw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:626:shr_uw_orrr;pat:DADAOCodeGen.td.patch:643:shr_uw_orrr |
| `st.b_rrii_rd` | `st.b` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:808:st_b_rd;pat:DADAOCodeGen.td.patch:809:st_b_rd;pat:DADAOCodeGen.td.patch:810:st_b_rd;pat:DADAOCodeGen.td.patch:836:st_b_rd |
| `st.o_rrii_ra` | `st.o` | `rrii` | `m1` | accept | no | — |
| `st.o_rrii_rb` | `st.o` | `rrii` | `m1` | accept | yes | buildmi:DADAOFrameLowering.cpp.patch:417:st_o_rb |
| `st.o_rrii_rd` | `st.o` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:801:st_o_rd |
| `st.o_rrii_rf` | `st.o` | `rrii` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1172:st_o_rrii_rf |
| `st.t_rrii_rd` | `st.t` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:823:st_t_rd;pat:DADAOCodeGen.td.patch:838:st_t_rd |
| `st.t_rrii_rf` | `st.t` | `rrii` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1176:st_t_rrii_rf |
| `st.w_rrii_rd` | `st.w` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:816:st_w_rd;pat:DADAOCodeGen.td.patch:817:st_w_rd;pat:DADAOCodeGen.td.patch:837:st_w_rd |
| `stm.b_rrri_rd` | `stm.b` | `rrri` | `m1` | accept | no | — |
| `stm.o_rrri_ra` | `stm.o` | `rrri` | `m1` | accept | no | — |
| `stm.o_rrri_rb` | `stm.o` | `rrri` | `m1` | accept | yes | buildmi:DADAOLoadStoreOptimizer.cpp.patch:287:stm_o_rb;isel-cpp:DADAOISelLowering.cpp.patch:1259:stm_o_rb |
| `stm.o_rrri_rd` | `stm.o` | `rrri` | `m1` | accept | yes | buildmi:DADAOLoadStoreOptimizer.cpp.patch:286:stm_o_rd;isel-cpp:DADAOISelLowering.cpp.patch:1257:stm_o_rd |
| `stm.o_rrri_rf` | `stm.o` | `rrri` | `fp` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:1261:stm_o_rrri_rf |
| `stm.t_rrri_rd` | `stm.t` | `rrri` | `m1` | accept | no | — |
| `stm.t_rrri_rf` | `stm.t` | `rrri` | `fp` | accept | no | — |
| `stm.w_rrri_rd` | `stm.w` | `rrri` | `m1` | accept | no | — |
| `sub.o_orrr_bbd` | `sub.o` | `orrr` | `m1` | accept | no | — |
| `sub.o_orrr_dbb` | `sub.o` | `orrr` | `m3` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:211:sub_o_dbb |
| `sub.sb_orrr_rd` | `sub.sb` | `orrr` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:324:sub_sb;isel-cpp:DADAOISelDAGToDAG.cpp.patch:523:sub_sb;pat:DADAOCodeGen.td.patch:470:sub_sb;pat:DADAOCodeGen.td.patch:568:sub_sb;pat:DADAOCodeGen.td.patch:614:sub_sb |
| `sub.so_rrrr_rd` | `sub.so` | `rrrr` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:297:sub_so_rd;pseudo:DADAOCodeGen.td.patch:469:sub_so_rd:NEG_PSEUDO |
| `sub.st_orrr_rd` | `sub.st` | `orrr` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:323:sub_st;isel-cpp:DADAOISelDAGToDAG.cpp.patch:521:sub_st;pat:DADAOCodeGen.td.patch:472:sub_st;pat:DADAOCodeGen.td.patch:566:sub_st;pat:DADAOCodeGen.td.patch:594:sub_st |
| `sub.sw_orrr_rd` | `sub.sw` | `orrr` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:324:sub_sw;isel-cpp:DADAOISelDAGToDAG.cpp.patch:522:sub_sw;pat:DADAOCodeGen.td.patch:471:sub_sw;pat:DADAOCodeGen.td.patch:567:sub_sw;pat:DADAOCodeGen.td.patch:604:sub_sw |
| `sub.ub_orrr_rd` | `sub.ub` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:615:sub_ub |
| `sub.uo_rrrr_rd` | `sub.uo` | `rrrr` | `m1` | accept | yes | pseudo:DADAOCodeGen.td.patch:252:sub_uo_rd:ADD_PSEUDO;pseudo:DADAOCodeGen.td.patch:254:sub_uo_rd:SUB_PSEUDO;pseudo:DADAOCodeGen.td.patch:263:sub_uo_rd:MUL_PSEUDO |
| `sub.ut_orrr_rd` | `sub.ut` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:595:sub_ut |
| `sub.uw_orrr_rd` | `sub.uw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:605:sub_uw |
| `swym_oiii_imm` | `swym` | `oiii` | `m1` | accept | no | — |
| `trap_ciii_cfx` | `trap` | `ciii` | `m1` | accept | no | — |
| `uo2fo_orri_rf` | `uo2fo` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1196:uo2fo_orri_rf |
| `uo2ft_orri_rf` | `uo2ft` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1197:uo2ft_orri_rf |
| `ut2fo_orri_rf` | `ut2fo` | `orri` | `fp` | accept | no | — |
| `ut2ft_orri_rf` | `ut2ft` | `orri` | `fp` | accept | no | — |
| `xnor.o_orrr_rd` | `xnor.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:461:xnor_o |
| `xor.o_orrr_rd` | `xor.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:452:xor_o |

## 3. 缺口汇总（未被 ISel 使用，64 条）

候选优化面（供后续里程碑参考）。按性质分四类（现场统计）：

1. **真缺口·候补优化面**（`scope != excluded`，且后端 ISel/post-ISel 均未引用，且非汇编层/特权族）：**55** 条 —— ISA 有、后端一次都没发射，最有价值。
2. **真缺口·汇编层/特权族**（同上但 `format ∈ {crrr, ciii, crii}` 或助记符 ∈ {fence, swym}，机械判据）：**5** 条 —— 经 cfx 访问/内联汇编/占位语义使用，不经 ISel 选入属预期。
3. **仅 post-ISel 引用**（伪指令展开/帧/寄存器分配会发射，非 ISel 选入）：**2** 条。
4. **`scope: excluded` 未实现**（汇编器拒绝、执行 ILLI）：**2** 条 —— 不在本期范围。

### 3.1 真缺口·候补优化面（55 条）

| id | mnemonic | format | scope |
|---|---|---|---|
| `add.so_rrrr_rd` | `add.so` | `rrrr` | `m1` |
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
| `st.o_rrii_ra` | `st.o` | `rrii` | `m1` |
| `stm.b_rrri_rd` | `stm.b` | `rrri` | `m1` |
| `stm.o_rrri_ra` | `stm.o` | `rrri` | `m1` |
| `stm.t_rrri_rd` | `stm.t` | `rrri` | `m1` |
| `stm.t_rrri_rf` | `stm.t` | `rrri` | `fp` |
| `stm.w_rrri_rd` | `stm.w` | `rrri` | `m1` |
| `sub.o_orrr_bbd` | `sub.o` | `orrr` | `m1` |
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

### 3.3 仅 post-ISel 引用（2 条）

| id | mnemonic | format | scope |
|---|---|---|---|
| `fo2fo_orri_rf` | `fo2fo` | `orri` | `fp` |
| `rd2rb_orri_rb` | `rd2rb` | `orri` | `m1` |

### 3.4 scope: excluded（未实现）（2 条）

| id | mnemonic | format | scope |
|---|---|---|---|
| `cfxld_crii_cfx` | `cfxld` | `crii` | `excluded` |
| `cfxst_crii_cfx` | `cfxst` | `crii` | `excluded` |

