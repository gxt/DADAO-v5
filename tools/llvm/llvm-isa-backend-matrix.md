# ISA↔后端覆盖矩阵（生成式，两层分列）

> **生成器**：`tools/llvm/gen_isa_coverage.py`（生成物，勿手工编辑；改生成器或真源后重跑）
> **真源**：`contracts/opcodes.yaml`（**266** 条 = `m1` 156 + `fp` 64 + `excluded` 4 + `m3` 1 + `m8` 7 + `m9` 34；计数由脚本现场统计，不写死）
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

现场统计：证据条数 = buildmi 51 + isel-cpp 46 + pat 245 + pat-args 8 + pseudo 19；判「用得上」的记录 **177** 条。

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
| `add.sb_orrr_rd` | `add.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:535:add_sb |
| `add.si_riii_rb` | `add.si` | `riii` | `m1` | accept | yes | buildmi:DADAOFrameLowering.cpp.patch:192:add_si_rb;buildmi:DADAOFrameLowering.cpp.patch:369:add_si_rb;buildmi:DADAOFrameLowering.cpp.patch:494:add_si_rb;buildmi:DADAORegisterInfo.cpp.patch:210:add_si_rb;buildmi:DADAORegisterInfo.cpp.patch:260:add_si_rb |
| `add.si_riii_rd` | `add.si` | `riii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:314:add_si_rd;pseudo:DADAOCodeGen.td.patch:330:add_si_rd:ADD_IMM_PSEUDO |
| `add.so_rrrr_rd` | `add.so` | `rrrr` | `m1` | accept | no | — |
| `add.st_orrr_rd` | `add.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:533:add_st |
| `add.sw_orrr_rd` | `add.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:534:add_sw |
| `add.ub_orrr_rd` | `add.ub` | `orrr` | `m1` | accept | no | — |
| `add.uo_rrrr_rd` | `add.uo` | `rrrr` | `m1` | accept | yes | pseudo:DADAOCodeGen.td.patch:241:add_uo_rd:ADD_PSEUDO;pseudo:DADAOCodeGen.td.patch:243:add_uo_rd:SUB_PSEUDO;pseudo:DADAOCodeGen.td.patch:252:add_uo_rd:MUL_PSEUDO |
| `add.ut_orrr_rd` | `add.ut` | `orrr` | `m1` | accept | no | — |
| `add.uw_orrr_rd` | `add.uw` | `orrr` | `m1` | accept | no | — |
| `aip.si_riii_rb` | `aip.si` | `riii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:481:aip_si_rb |
| `and.o_orrr_rd` | `and.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:420:and_o;pat:DADAOCodeGen.td.patch:1048:and_o |
| `andn.w_rwii_rb` | `andn.w` | `rwii` | `m1` | accept | no | — |
| `andn.w_rwii_rd` | `andn.w` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:364:andn_w_rd |
| `br.eq_rrii_rd` | `br.eq` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:837:br_eq_rd |
| `br.n_riii_rd` | `br.n` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:831:br_n_rd |
| `br.ne_rrii_rd` | `br.ne` | `rrii` | `m1` | accept | yes | buildmi:DADAOISelLowering.cpp.patch:2750:br_ne_rd;isel-cpp:DADAOISelLowering.cpp.patch:2750:br_ne_rd;pat:DADAOCodeGen.td.patch:838:br_ne_rd |
| `br.nn_riii_rd` | `br.nn` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:832:br_nn_rd |
| `br.np_riii_rd` | `br.np` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:834:br_np_rd |
| `br.nz_riii_rb` | `br.nz` | `riii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:784:br_nz_rb |
| `br.nz_riii_rd` | `br.nz` | `riii` | `m1` | accept | yes | buildmi:DADAOISelLowering.cpp.patch:2761:br_nz_rd;isel-cpp:DADAOISelLowering.cpp.patch:2761:br_nz_rd;pat:DADAOCodeGen.td.patch:830:br_nz_rd |
| `br.p_riii_rd` | `br.p` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:833:br_p_rd |
| `br.z_riii_rb` | `br.z` | `riii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:783:br_z_rb |
| `br.z_riii_rd` | `br.z` | `riii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:829:br_z_rd |
| `call_iiii_ra` | `call` | `iiii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:671:call_iiii |
| `call_rrii_ra` | `call` | `rrii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:671:call_rrii |
| `cfx2rc_crrr_cfx` | `cfx2rc` | `crrr` | `m1` | accept | no | — |
| `cfx2rd_crrr_cfx` | `cfx2rd` | `crrr` | `m1` | accept | no | — |
| `cfxld_crii_cfx` | `cfxld` | `crii` | `excluded` | reject | no | — |
| `cfxst_crii_cfx` | `cfxst` | `crii` | `excluded` | reject | no | — |
| `clmul.o_rrrr_rd` | `clmul.o` | `rrrr` | `m9` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:253:clmul_o_rd;buildmi:DADAOInstrInfo.cpp.patch:267:clmul_o_rd;buildmi:DADAOInstrInfo.cpp.patch:283:clmul_o_rd;pseudo:DADAOCodeGen.td.patch:317:clmul_o_rd:CLMUL_PSEUDO;pseudo:DADAOCodeGen.td.patch:319:clmul_o_rd:CLMULHI_PSEUDO |
| `cmp.sb_orrr_rd` | `cmp.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:820:cmp_sb |
| `cmp.si_rrii_rd` | `cmp.si` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:799:cmp_si_rd;pat:DADAOCodeGen.td.patch:1044:cmp_si_rd;pat:DADAOCodeGen.td.patch:1046:cmp_si_rd;pat:DADAOCodeGen.td.patch:1048:cmp_si_rd;pat:DADAOCodeGen.td.patch:1052:cmp_si_rd |
| `cmp.so_orrr_rd` | `cmp.so` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:797:cmp_so |
| `cmp.st_orrr_rd` | `cmp.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:816:cmp_st |
| `cmp.sw_orrr_rd` | `cmp.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:818:cmp_sw |
| `cmp.ub_orrr_rd` | `cmp.ub` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:826:cmp_ub |
| `cmp.ui_rrii_rd` | `cmp.ui` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:809:cmp_ui_rd |
| `cmp.uo_orrr_dbb` | `cmp.uo` | `orrr` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:769:cmp_uo_dbb |
| `cmp.uo_orrr_rd` | `cmp.uo` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:807:cmp_uo |
| `cmp.ut_orrr_rd` | `cmp.ut` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:822:cmp_ut |
| `cmp.uw_orrr_rd` | `cmp.uw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:824:cmp_uw |
| `cs.eq_rrrr_rd` | `cs.eq` | `rrrr` | `m1` | accept | no | — |
| `cs.n_rrrr_rd` | `cs.n` | `rrrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:844:cs_n_rd;pat:DADAOCodeGen.td.patch:852:cs_n_rd;pat:DADAOCodeGen.td.patch:858:cs_n_rd;pat:DADAOCodeGen.td.patch:864:cs_n_rd |
| `cs.n_rrrr_rf` | `cs.n` | `rrrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:876:cs_n_rrrr_rf;pat:DADAOCodeGen.td.patch:882:cs_n_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1058:cs_n_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1061:cs_n_rrrr_rf |
| `cs.ne_rrrr_rd` | `cs.ne` | `rrrr` | `m1` | accept | no | — |
| `cs.p_rrrr_rd` | `cs.p` | `rrrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:846:cs_p_rd;pat:DADAOCodeGen.td.patch:856:cs_p_rd;pat:DADAOCodeGen.td.patch:862:cs_p_rd;pat:DADAOCodeGen.td.patch:868:cs_p_rd;pat:DADAOCodeGen.td.patch:1048:cs_p_rd;pat:DADAOCodeGen.td.patch:1052:cs_p_rd |
| `cs.p_rrrr_rf` | `cs.p` | `rrrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:880:cs_p_rrrr_rf;pat:DADAOCodeGen.td.patch:886:cs_p_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1059:cs_p_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1062:cs_p_rrrr_rf |
| `cs.z_rrrr_rd` | `cs.z` | `rrrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:845:cs_z_rd;pat:DADAOCodeGen.td.patch:854:cs_z_rd;pat:DADAOCodeGen.td.patch:860:cs_z_rd;pat:DADAOCodeGen.td.patch:866:cs_z_rd;pat:DADAOCodeGen.td.patch:1049:cs_z_rd;pat:DADAOCodeGen.td.patch:1053:cs_z_rd |
| `cs.z_rrrr_rf` | `cs.z` | `rrrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:878:cs_z_rrrr_rf;pat:DADAOCodeGen.td.patch:884:cs_z_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1058:cs_z_rrrr_rf;pat-args:DADAOCodeGen.td.patch:1061:cs_z_rrrr_rf |
| `ctlz_orri_rd` | `ctlz` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:476:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:477:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:485:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:486:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:487:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:489:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:491:ctlz_orri_rd;pat:DADAOCodeGen.td.patch:493:ctlz_orri_rd |
| `ctpop_orri_rd` | `ctpop` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:480:ctpop_orri_rd;pat:DADAOCodeGen.td.patch:503:ctpop_orri_rd;pat:DADAOCodeGen.td.patch:504:ctpop_orri_rd;pat:DADAOCodeGen.td.patch:505:ctpop_orri_rd |
| `cttz_orri_rd` | `cttz` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:478:cttz_orri_rd;pat:DADAOCodeGen.td.patch:479:cttz_orri_rd;pat:DADAOCodeGen.td.patch:494:cttz_orri_rd;pat:DADAOCodeGen.td.patch:495:cttz_orri_rd;pat:DADAOCodeGen.td.patch:496:cttz_orri_rd;pat:DADAOCodeGen.td.patch:498:cttz_orri_rd;pat:DADAOCodeGen.td.patch:500:cttz_orri_rd;pat:DADAOCodeGen.td.patch:502:cttz_orri_rd |
| `div.sb_orrr_rd` | `div.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:548:div_sb |
| `div.so_orrr_rd` | `div.so` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:517:div_so |
| `div.st_orrr_rd` | `div.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:546:div_st |
| `div.sw_orrr_rd` | `div.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:547:div_sw |
| `div.ub_orrr_rd` | `div.ub` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:545:div_ub |
| `div.uo_orrr_rd` | `div.uo` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:516:div_uo |
| `div.ut_orrr_rd` | `div.ut` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:543:div_ut |
| `div.uw_orrr_rd` | `div.uw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:544:div_uw |
| `escape_ciii_cfx` | `escape` | `ciii` | `m1` | accept | no | — |
| `ext.so_orri_rd` | `ext.so` | `orri` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:607:ext_so_orri;pat:DADAOCodeGen.td.patch:608:ext_so_orri;pat:DADAOCodeGen.td.patch:609:ext_so_orri;pat:DADAOCodeGen.td.patch:610:ext_so_orri;pat:DADAOCodeGen.td.patch:611:ext_so_orri;pat:DADAOCodeGen.td.patch:612:ext_so_orri;pat:DADAOCodeGen.td.patch:654:ext_so_orri;pat:DADAOCodeGen.td.patch:655:ext_so_orri;pat:DADAOCodeGen.td.patch:656:ext_so_orri;pat:DADAOCodeGen.td.patch:661:ext_so_orri;pat:DADAOCodeGen.td.patch:665:ext_so_orri;pat:DADAOCodeGen.td.patch:667:ext_so_orri;pat:DADAOCodeGen.td.patch:669:ext_so_orri;pat:DADAOCodeGen.td.patch:675:ext_so_orri;pat:DADAOCodeGen.td.patch:677:ext_so_orri;pat:DADAOCodeGen.td.patch:679:ext_so_orri |
| `ext.so_orrr_rd` | `ext.so` | `orrr` | `m1` | accept | no | — |
| `ext.uo_orri_rd` | `ext.uo` | `orri` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:593:ext_uo_orri;pat:DADAOCodeGen.td.patch:594:ext_uo_orri;pat:DADAOCodeGen.td.patch:595:ext_uo_orri;pat:DADAOCodeGen.td.patch:596:ext_uo_orri;pat:DADAOCodeGen.td.patch:597:ext_uo_orri;pat:DADAOCodeGen.td.patch:598:ext_uo_orri;pat:DADAOCodeGen.td.patch:600:ext_uo_orri;pat:DADAOCodeGen.td.patch:601:ext_uo_orri;pat:DADAOCodeGen.td.patch:602:ext_uo_orri;pat:DADAOCodeGen.td.patch:603:ext_uo_orri;pat:DADAOCodeGen.td.patch:604:ext_uo_orri;pat:DADAOCodeGen.td.patch:605:ext_uo_orri;pat:DADAOCodeGen.td.patch:616:ext_uo_orri;pat:DADAOCodeGen.td.patch:617:ext_uo_orri;pat:DADAOCodeGen.td.patch:618:ext_uo_orri;pat:DADAOCodeGen.td.patch:619:ext_uo_orri;pat:DADAOCodeGen.td.patch:620:ext_uo_orri;pat:DADAOCodeGen.td.patch:621:ext_uo_orri;pat:DADAOCodeGen.td.patch:627:ext_uo_orri;pat:DADAOCodeGen.td.patch:629:ext_uo_orri;pat:DADAOCodeGen.td.patch:631:ext_uo_orri |
| `ext.uo_orrr_rd` | `ext.uo` | `orrr` | `m1` | accept | no | — |
| `fence_oiii_imm` | `fence` | `oiii` | `m9` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:728:fence |
| `fo2fo_orri_rf` | `fo2fo` | `orri` | `fp` | accept | no | — |
| `fo2ft_orri_rf` | `fo2ft` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1077:fo2ft_orri_rf |
| `fo2io_orri_rf` | `fo2io` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1083:fo2io_orri_rf |
| `fo2it_orri_rf` | `fo2it` | `orri` | `fp` | accept | no | — |
| `fo2uo_orri_rf` | `fo2uo` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1085:fo2uo_orri_rf |
| `fo2ut_orri_rf` | `fo2ut` | `orri` | `fp` | accept | no | — |
| `foadd_orrr_rf` | `foadd` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:901:foadd_orrr_rf |
| `focls_orri_rf` | `focls` | `orri` | `fp` | accept | no | — |
| `fodiv_orrr_rf` | `fodiv` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:915:fodiv_orrr_rf |
| `fofma_rrrr_rf` | `fofma` | `rrrr` | `excluded` | accept | yes | pat:DADAOCodeGen.td.patch:914:fofma_rrrr_rf |
| `fomax_orrr_rf` | `fomax` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:958:fomax_orrr_rf;pat:DADAOCodeGen.td.patch:960:fomax_orrr_rf |
| `fomin_orrr_rf` | `fomin` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:957:fomin_orrr_rf;pat:DADAOCodeGen.td.patch:959:fomin_orrr_rf |
| `fomul_orrr_rf` | `fomul` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:903:fomul_orrr_rf |
| `foqcmp_orrr_rf` | `foqcmp` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1002:foqcmp_orrr_rf;pat-args:DADAOCodeGen.td.patch:1058:foqcmp_orrr_rf |
| `forem_orrr_rf` | `forem` | `orrr` | `fp` | accept | no | — |
| `fornd_orri_rf` | `fornd` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:986:fornd_orri_rf;pat:DADAOCodeGen.td.patch:987:fornd_orri_rf;pat:DADAOCodeGen.td.patch:988:fornd_orri_rf;pat:DADAOCodeGen.td.patch:989:fornd_orri_rf;pat:DADAOCodeGen.td.patch:990:fornd_orri_rf;pat:DADAOCodeGen.td.patch:991:fornd_orri_rf;pat:DADAOCodeGen.td.patch:992:fornd_orri_rf |
| `foroot_orri_rf` | `foroot` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:917:foroot_orri_rf |
| `fosclb_orrr_rf` | `fosclb` | `orrr` | `fp` | accept | no | — |
| `foscmp_orrr_rf` | `foscmp` | `orrr` | `fp` | accept | no | — |
| `fosgnj_orrr_rf` | `fosgnj` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:928:fosgnj_orrr_rf;pat:DADAOCodeGen.td.patch:930:fosgnj_orrr_rf |
| `fosgnn_orrr_rf` | `fosgnn` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:919:fosgnn_orrr_rf |
| `fosub_orrr_rf` | `fosub` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:902:fosub_orrr_rf |
| `ft2fo_orri_rf` | `ft2fo` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1076:ft2fo_orri_rf |
| `ft2ft_orri_rf` | `ft2ft` | `orri` | `fp` | accept | no | — |
| `ft2io_orri_rf` | `ft2io` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1084:ft2io_orri_rf |
| `ft2it_orri_rf` | `ft2it` | `orri` | `fp` | accept | no | — |
| `ft2uo_orri_rf` | `ft2uo` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1086:ft2uo_orri_rf |
| `ft2ut_orri_rf` | `ft2ut` | `orri` | `fp` | accept | no | — |
| `ftadd_orrr_rf` | `ftadd` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:933:ftadd_orrr_rf |
| `ftcls_orri_rf` | `ftcls` | `orri` | `fp` | accept | no | — |
| `ftdiv_orrr_rf` | `ftdiv` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:938:ftdiv_orrr_rf |
| `ftfma_rrrr_rf` | `ftfma` | `rrrr` | `excluded` | accept | yes | pat:DADAOCodeGen.td.patch:937:ftfma_rrrr_rf |
| `ftmax_orrr_rf` | `ftmax` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:962:ftmax_orrr_rf;pat:DADAOCodeGen.td.patch:964:ftmax_orrr_rf |
| `ftmin_orrr_rf` | `ftmin` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:961:ftmin_orrr_rf;pat:DADAOCodeGen.td.patch:963:ftmin_orrr_rf |
| `ftmul_orrr_rf` | `ftmul` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:935:ftmul_orrr_rf |
| `ftqcmp_orrr_rf` | `ftqcmp` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1003:ftqcmp_orrr_rf;pat-args:DADAOCodeGen.td.patch:1061:ftqcmp_orrr_rf |
| `ftrem_orrr_rf` | `ftrem` | `orrr` | `fp` | accept | no | — |
| `ftrnd_orri_rf` | `ftrnd` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:993:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:994:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:995:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:996:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:997:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:998:ftrnd_orri_rf;pat:DADAOCodeGen.td.patch:999:ftrnd_orri_rf |
| `ftroot_orri_rf` | `ftroot` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:939:ftroot_orri_rf |
| `ftsclb_orrr_rf` | `ftsclb` | `orrr` | `fp` | accept | no | — |
| `ftscmp_orrr_rf` | `ftscmp` | `orrr` | `fp` | accept | no | — |
| `ftsgnj_orrr_rf` | `ftsgnj` | `orrr` | `fp` | accept | no | — |
| `ftsgnn_orrr_rf` | `ftsgnn` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:940:ftsgnn_orrr_rf |
| `ftsub_orrr_rf` | `ftsub` | `orrr` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:934:ftsub_orrr_rf |
| `io2fo_orri_rf` | `io2fo` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1090:io2fo_orri_rf |
| `io2ft_orri_rf` | `io2ft` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1091:io2ft_orri_rf |
| `it2fo_orri_rf` | `it2fo` | `orri` | `fp` | accept | no | — |
| `it2ft_orri_rf` | `it2ft` | `orri` | `fp` | accept | no | — |
| `jump_iiii_rb` | `jump` | `iiii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:733:jump_iiii;buildmi:DADAOInstrInfo.cpp.patch:753:jump_iiii;isel-cpp:DADAOISelDAGToDAG.cpp.patch:716:tailjmp_iiii;pat:DADAOCodeGen.td.patch:889:jump_iiii |
| `jump_rrii_rb` | `jump` | `rrii` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:604:jump_rrii;isel-cpp:DADAOISelDAGToDAG.cpp.patch:626:jump_rrii;isel-cpp:DADAOISelDAGToDAG.cpp.patch:716:tailjmp_rrii |
| `ld.o_rrii_ra` | `ld.o` | `rrii` | `m1` | accept | no | — |
| `ld.o_rrii_rb` | `ld.o` | `rrii` | `m1` | accept | yes | buildmi:DADAOFrameLowering.cpp.patch:462:ld_o_rb;buildmi:DADAOInstrInfo.cpp.patch:483:ld_o_rb;isel-cpp:DADAOISelDAGToDAG.cpp.patch:175:ld_o_rb;isel-cpp:DADAOISelDAGToDAG.cpp.patch:597:ld_o_rb |
| `ld.o_rrii_rd` | `ld.o` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:725:ld_o_rd |
| `ld.o_rrii_rf` | `ld.o` | `rrii` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1066:ld_o_rrii_rf |
| `ld.sb_rrii_rd` | `ld.sb` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:732:ld_sb_rd;pat:DADAOCodeGen.td.patch:769:ld_sb_rd;pat:DADAOCodeGen.td.patch:770:ld_sb_rd |
| `ld.st_rrii_rd` | `ld.st` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:747:ld_st_rd |
| `ld.sw_rrii_rd` | `ld.sw` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:740:ld_sw_rd;pat:DADAOCodeGen.td.patch:774:ld_sw_rd |
| `ld.t_rrii_rf` | `ld.t` | `rrii` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1070:ld_t_rrii_rf |
| `ld.ub_rrii_rd` | `ld.ub` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:730:ld_ub_rd;pat:DADAOCodeGen.td.patch:731:ld_ub_rd;pat:DADAOCodeGen.td.patch:758:ld_ub_rd;pat:DADAOCodeGen.td.patch:765:ld_ub_rd;pat:DADAOCodeGen.td.patch:766:ld_ub_rd;pat:DADAOCodeGen.td.patch:767:ld_ub_rd;pat:DADAOCodeGen.td.patch:768:ld_ub_rd |
| `ld.ut_rrii_rd` | `ld.ut` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:745:ld_ut_rd;pat:DADAOCodeGen.td.patch:746:ld_ut_rd;pat:DADAOCodeGen.td.patch:760:ld_ut_rd |
| `ld.uw_rrii_rd` | `ld.uw` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:738:ld_uw_rd;pat:DADAOCodeGen.td.patch:739:ld_uw_rd;pat:DADAOCodeGen.td.patch:759:ld_uw_rd;pat:DADAOCodeGen.td.patch:772:ld_uw_rd;pat:DADAOCodeGen.td.patch:773:ld_uw_rd |
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
| `lr.b.an_orrr_rd` | `lr.b.an` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2683:lr_b_an |
| `lr.b.ar_orrr_rd` | `lr.b.ar` | `orrr` | `m9` | accept | no | — |
| `lr.b.nn_orrr_rd` | `lr.b.nn` | `orrr` | `m9` | accept | no | — |
| `lr.o.an_orrr_rd` | `lr.o.an` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2695:lr_o_an |
| `lr.o.ar_orrr_rd` | `lr.o.ar` | `orrr` | `m9` | accept | no | — |
| `lr.o.nn_orrr_rd` | `lr.o.nn` | `orrr` | `m9` | accept | no | — |
| `lr.t.an_orrr_rd` | `lr.t.an` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2691:lr_t_an |
| `lr.t.ar_orrr_rd` | `lr.t.ar` | `orrr` | `m9` | accept | no | — |
| `lr.t.nn_orrr_rd` | `lr.t.nn` | `orrr` | `m9` | accept | no | — |
| `lr.w.an_orrr_rd` | `lr.w.an` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2687:lr_w_an |
| `lr.w.ar_orrr_rd` | `lr.w.ar` | `orrr` | `m9` | accept | no | — |
| `lr.w.nn_orrr_rd` | `lr.w.nn` | `orrr` | `m9` | accept | no | — |
| `mul.sb_orrr_rd` | `mul.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:541:mul_sb |
| `mul.so_rrrr_rd` | `mul.so` | `rrrr` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:222:mul_so_rd;buildmi:DADAOInstrInfo.cpp.patch:238:mul_so_rd;pseudo:DADAOCodeGen.td.patch:287:mul_so_rd:MULHS_PSEUDO;pseudo:DADAOCodeGen.td.patch:296:mul_so_rd:SMUL_LOHI_PSEUDO |
| `mul.st_orrr_rd` | `mul.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:539:mul_st |
| `mul.sw_orrr_rd` | `mul.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:540:mul_sw |
| `mul.ub_orrr_rd` | `mul.ub` | `orrr` | `m1` | accept | no | — |
| `mul.uo_rrrr_rd` | `mul.uo` | `rrrr` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:190:mul_uo_rd;buildmi:DADAOInstrInfo.cpp.patch:206:mul_uo_rd;pseudo:DADAOCodeGen.td.patch:241:mul_uo_rd:ADD_PSEUDO;pseudo:DADAOCodeGen.td.patch:243:mul_uo_rd:SUB_PSEUDO;pseudo:DADAOCodeGen.td.patch:252:mul_uo_rd:MUL_PSEUDO;pseudo:DADAOCodeGen.td.patch:264:mul_uo_rd:MULHU_PSEUDO;pseudo:DADAOCodeGen.td.patch:273:mul_uo_rd:UMUL_LOHI_PSEUDO |
| `mul.ut_orrr_rd` | `mul.ut` | `orrr` | `m1` | accept | no | — |
| `mul.uw_orrr_rd` | `mul.uw` | `orrr` | `m1` | accept | no | — |
| `or.o_orrr_rd` | `or.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:421:or_o;pat:DADAOCodeGen.td.patch:1052:or_o |
| `or.w_rwii_rb` | `or.w` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:391:or_w_rb;buildmi:DADAOInstrInfo.cpp.patch:392:or_w_rb;buildmi:DADAOInstrInfo.cpp.patch:429:or_w_rb;buildmi:DADAOInstrInfo.cpp.patch:430:or_w_rb;buildmi:DADAOInstrInfo.cpp.patch:448:or_w_rb;buildmi:DADAOInstrInfo.cpp.patch:449:or_w_rb |
| `or.w_rwii_rd` | `or.w` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:131:or_w_rd;buildmi:DADAOInstrInfo.cpp.patch:370:or_w_rd;buildmi:DADAOInstrInfo.cpp.patch:410:or_w_rd;buildmi:DADAOInstrInfo.cpp.patch:411:or_w_rd |
| `ra2rd_orri_ra` | `ra2rd` | `orri` | `m1` | accept | no | — |
| `rb2rb_orri_rb` | `rb2rb` | `orri` | `m1` | accept | yes | buildmi:DADAOFrameLowering.cpp.patch:365:rb2rb;buildmi:DADAOFrameLowering.cpp.patch:427:rb2rb;buildmi:DADAOFrameLowering.cpp.patch:458:rb2rb;buildmi:DADAORegisterInfo.cpp.patch:206:rb2rb;buildmi:DADAORegisterInfo.cpp.patch:215:rb2rb;buildmi:DADAORegisterInfo.cpp.patch:257:rb2rb |
| `rb2rd_orri_rb` | `rb2rd` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:538:rb2rd |
| `rd2ra_orri_ra` | `rd2ra` | `orri` | `m1` | accept | no | — |
| `rd2rb_orri_rb` | `rd2rb` | `orri` | `m1` | accept | no | — |
| `rd2rd_orri_rd` | `rd2rd` | `orri` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:313:rd2rd;pseudo:DADAOCodeGen.td.patch:330:rd2rd:ADD_IMM_PSEUDO |
| `rd2rf_orri_rf` | `rd2rf` | `orri` | `fp` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:333:rd2rf_orri_rf;pat:DADAOCodeGen.td.patch:636:rd2rf_orri_rf;pat:DADAOCodeGen.td.patch:930:rd2rf_orri_rf;pat:DADAOCodeGen.td.patch:1101:rd2rf_orri_rf |
| `rem.sb_orrr_rd` | `rem.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:554:rem_sb |
| `rem.so_orrr_rd` | `rem.so` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:519:rem_so |
| `rem.st_orrr_rd` | `rem.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:552:rem_st |
| `rem.sw_orrr_rd` | `rem.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:553:rem_sw |
| `rem.ub_orrr_rd` | `rem.ub` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:551:rem_ub |
| `rem.uo_orrr_rd` | `rem.uo` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:518:rem_uo |
| `rem.ut_orrr_rd` | `rem.ut` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:549:rem_ut |
| `rem.uw_orrr_rd` | `rem.uw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:550:rem_uw |
| `ret_riii_ra` | `ret` | `riii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:153:ret_riii;pseudo:DADAOCodeGen.td.patch:211:ret_riii:RET_PSEUDO |
| `rev.b_orri_rd` | `rev.b` | `orri` | `m8` | accept | no | — |
| `rev.o_orri_rd` | `rev.o` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:510:rev_o_orri_rd;pat:DADAOCodeGen.td.patch:511:rev_o_orri_rd |
| `rev.t_orri_rd` | `rev.t` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:575:rev_t_orri_rd |
| `rev.w_orri_rd` | `rev.w` | `orri` | `m8` | accept | yes | pat:DADAOCodeGen.td.patch:576:rev_w_orri_rd |
| `rf2rd_orri_rf` | `rf2rd` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:637:rf2rd_orri_rf;pat:DADAOCodeGen.td.patch:1102:rf2rd_orri_rf |
| `rol.b_orri_rd` | `rol.b` | `orri` | `m9` | accept | no | — |
| `rol.b_orrr_rd` | `rol.b` | `orrr` | `m9` | accept | no | — |
| `rol.o_orri_rd` | `rol.o` | `orri` | `m9` | accept | yes | pat:DADAOCodeGen.td.patch:459:rol_o_orri |
| `rol.o_orrr_rd` | `rol.o` | `orrr` | `m9` | accept | yes | pat:DADAOCodeGen.td.patch:460:rol_o_orrr |
| `rol.t_orri_rd` | `rol.t` | `orri` | `m9` | accept | no | — |
| `rol.t_orrr_rd` | `rol.t` | `orrr` | `m9` | accept | no | — |
| `rol.w_orri_rd` | `rol.w` | `orri` | `m9` | accept | no | — |
| `rol.w_orrr_rd` | `rol.w` | `orrr` | `m9` | accept | no | — |
| `sc.b.ar_orrr_rd` | `sc.b.ar` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2684:sc_b_ar |
| `sc.b.nn_orrr_rd` | `sc.b.nn` | `orrr` | `m9` | accept | no | — |
| `sc.b.nr_orrr_rd` | `sc.b.nr` | `orrr` | `m9` | accept | no | — |
| `sc.o.ar_orrr_rd` | `sc.o.ar` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2696:sc_o_ar |
| `sc.o.nn_orrr_rd` | `sc.o.nn` | `orrr` | `m9` | accept | no | — |
| `sc.o.nr_orrr_rd` | `sc.o.nr` | `orrr` | `m9` | accept | no | — |
| `sc.t.ar_orrr_rd` | `sc.t.ar` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2692:sc_t_ar |
| `sc.t.nn_orrr_rd` | `sc.t.nn` | `orrr` | `m9` | accept | no | — |
| `sc.t.nr_orrr_rd` | `sc.t.nr` | `orrr` | `m9` | accept | no | — |
| `sc.w.ar_orrr_rd` | `sc.w.ar` | `orrr` | `m9` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:2688:sc_w_ar |
| `sc.w.nn_orrr_rd` | `sc.w.nn` | `orrr` | `m9` | accept | no | — |
| `sc.w.nr_orrr_rd` | `sc.w.nr` | `orrr` | `m9` | accept | no | — |
| `set.ow_rwii_rd` | `set.ow` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:346:set_ow_rd;buildmi:DADAOInstrInfo.cpp.patch:354:set_ow_rd |
| `set.w_rwii_rf` | `set.w` | `rwii` | `fp` | accept | no | — |
| `set.zw_rwii_rb` | `set.zw` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:390:set_zw_rb;buildmi:DADAOInstrInfo.cpp.patch:428:set_zw_rb;buildmi:DADAOInstrInfo.cpp.patch:447:set_zw_rb |
| `set.zw_rwii_rd` | `set.zw` | `rwii` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:131:set_zw_rd;buildmi:DADAOInstrInfo.cpp.patch:349:set_zw_rd;buildmi:DADAOInstrInfo.cpp.patch:354:set_zw_rd;buildmi:DADAOInstrInfo.cpp.patch:409:set_zw_rd |
| `shl.b_orri_rd` | `shl.b` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:427:shl_b_orri |
| `shl.b_orrr_rd` | `shl.b` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:566:shl_b_orrr |
| `shl.o_orri_rd` | `shl.o` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:593:shl_o_orri |
| `shl.o_orrr_rd` | `shl.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:449:shl_o_orrr |
| `shl.t_orri_rd` | `shl.t` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:427:shl_t_orri |
| `shl.t_orrr_rd` | `shl.t` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:564:shl_t_orrr |
| `shl.w_orri_rd` | `shl.w` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:427:shl_w_orri |
| `shl.w_orrr_rd` | `shl.w` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:565:shl_w_orrr |
| `shr.sb_orri_rd` | `shr.sb` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:433:shr_sb_orri |
| `shr.sb_orrr_rd` | `shr.sb` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:572:shr_sb_orrr |
| `shr.so_orri_rd` | `shr.so` | `orri` | `m1` | accept | no | — |
| `shr.so_orrr_rd` | `shr.so` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:451:shr_so_orrr |
| `shr.st_orri_rd` | `shr.st` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:433:shr_st_orri |
| `shr.st_orrr_rd` | `shr.st` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:570:shr_st_orrr |
| `shr.sw_orri_rd` | `shr.sw` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:433:shr_sw_orri |
| `shr.sw_orrr_rd` | `shr.sw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:571:shr_sw_orrr |
| `shr.ub_orri_rd` | `shr.ub` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:430:shr_ub_orri |
| `shr.ub_orrr_rd` | `shr.ub` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:569:shr_ub_orrr |
| `shr.uo_orri_rd` | `shr.uo` | `orri` | `m1` | accept | no | — |
| `shr.uo_orrr_rd` | `shr.uo` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:450:shr_uo_orrr |
| `shr.ut_orri_rd` | `shr.ut` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:430:shr_ut_orri |
| `shr.ut_orrr_rd` | `shr.ut` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:567:shr_ut_orrr |
| `shr.uw_orri_rd` | `shr.uw` | `orri` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:430:shr_uw_orri |
| `shr.uw_orrr_rd` | `shr.uw` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:568:shr_uw_orrr |
| `st.b_rrii_rd` | `st.b` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:733:st_b_rd;pat:DADAOCodeGen.td.patch:734:st_b_rd;pat:DADAOCodeGen.td.patch:735:st_b_rd;pat:DADAOCodeGen.td.patch:761:st_b_rd |
| `st.o_rrii_ra` | `st.o` | `rrii` | `m1` | accept | no | — |
| `st.o_rrii_rb` | `st.o` | `rrii` | `m1` | accept | yes | buildmi:DADAOFrameLowering.cpp.patch:414:st_o_rb |
| `st.o_rrii_rd` | `st.o` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:726:st_o_rd |
| `st.o_rrii_rf` | `st.o` | `rrii` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1068:st_o_rrii_rf |
| `st.t_rrii_rd` | `st.t` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:748:st_t_rd;pat:DADAOCodeGen.td.patch:763:st_t_rd |
| `st.t_rrii_rf` | `st.t` | `rrii` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1072:st_t_rrii_rf |
| `st.w_rrii_rd` | `st.w` | `rrii` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:741:st_w_rd;pat:DADAOCodeGen.td.patch:742:st_w_rd;pat:DADAOCodeGen.td.patch:762:st_w_rd |
| `stm.b_rrri_rd` | `stm.b` | `rrri` | `m1` | accept | no | — |
| `stm.o_rrri_ra` | `stm.o` | `rrri` | `m1` | accept | no | — |
| `stm.o_rrri_rb` | `stm.o` | `rrri` | `m1` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:1214:stm_o_rb |
| `stm.o_rrri_rd` | `stm.o` | `rrri` | `m1` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:1212:stm_o_rd |
| `stm.o_rrri_rf` | `stm.o` | `rrri` | `fp` | accept | yes | isel-cpp:DADAOISelLowering.cpp.patch:1216:stm_o_rrri_rf |
| `stm.t_rrri_rd` | `stm.t` | `rrri` | `m1` | accept | no | — |
| `stm.t_rrri_rf` | `stm.t` | `rrri` | `fp` | accept | no | — |
| `stm.w_rrri_rd` | `stm.w` | `rrri` | `m1` | accept | no | — |
| `sub.o_orrr_bbd` | `sub.o` | `orrr` | `m1` | accept | no | — |
| `sub.o_orrr_dbb` | `sub.o` | `orrr` | `m3` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:211:sub_o_dbb |
| `sub.sb_orrr_rd` | `sub.sb` | `orrr` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:481:sub_sb;pat:DADAOCodeGen.td.patch:440:sub_sb;pat:DADAOCodeGen.td.patch:538:sub_sb |
| `sub.so_rrrr_rd` | `sub.so` | `rrrr` | `m1` | accept | yes | buildmi:DADAOInstrInfo.cpp.patch:297:sub_so_rd;pseudo:DADAOCodeGen.td.patch:439:sub_so_rd:NEG_PSEUDO |
| `sub.st_orrr_rd` | `sub.st` | `orrr` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:479:sub_st;pat:DADAOCodeGen.td.patch:442:sub_st;pat:DADAOCodeGen.td.patch:536:sub_st |
| `sub.sw_orrr_rd` | `sub.sw` | `orrr` | `m1` | accept | yes | isel-cpp:DADAOISelDAGToDAG.cpp.patch:480:sub_sw;pat:DADAOCodeGen.td.patch:441:sub_sw;pat:DADAOCodeGen.td.patch:537:sub_sw |
| `sub.ub_orrr_rd` | `sub.ub` | `orrr` | `m1` | accept | no | — |
| `sub.uo_rrrr_rd` | `sub.uo` | `rrrr` | `m1` | accept | yes | pseudo:DADAOCodeGen.td.patch:241:sub_uo_rd:ADD_PSEUDO;pseudo:DADAOCodeGen.td.patch:243:sub_uo_rd:SUB_PSEUDO;pseudo:DADAOCodeGen.td.patch:252:sub_uo_rd:MUL_PSEUDO |
| `sub.ut_orrr_rd` | `sub.ut` | `orrr` | `m1` | accept | no | — |
| `sub.uw_orrr_rd` | `sub.uw` | `orrr` | `m1` | accept | no | — |
| `swym_oiii_imm` | `swym` | `oiii` | `m1` | accept | no | — |
| `trap_ciii_cfx` | `trap` | `ciii` | `m1` | accept | no | — |
| `uo2fo_orri_rf` | `uo2fo` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1092:uo2fo_orri_rf |
| `uo2ft_orri_rf` | `uo2ft` | `orri` | `fp` | accept | yes | pat:DADAOCodeGen.td.patch:1093:uo2ft_orri_rf |
| `ut2fo_orri_rf` | `ut2fo` | `orri` | `fp` | accept | no | — |
| `ut2ft_orri_rf` | `ut2ft` | `orri` | `fp` | accept | no | — |
| `xnor.o_orrr_rd` | `xnor.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:431:xnor_o |
| `xor.o_orrr_rd` | `xor.o` | `orrr` | `m1` | accept | yes | pat:DADAOCodeGen.td.patch:422:xor_o |

## 3. 缺口汇总（未被 ISel 使用，89 条）

候选优化面（供后续里程碑参考）。按性质分四类（现场统计）：

1. **真缺口·候补优化面**（`scope != excluded`，且后端 ISel/post-ISel 均未引用，且非汇编层/特权族）：**78** 条 —— ISA 有、后端一次都没发射，最有价值。
2. **真缺口·汇编层/特权族**（同上但 `format ∈ {crrr, ciii, crii}` 或助记符 ∈ {fence, swym}，机械判据）：**5** 条 —— 经 cfx 访问/内联汇编/占位语义使用，不经 ISel 选入属预期。
3. **仅 post-ISel 引用**（伪指令展开/帧/寄存器分配会发射，非 ISel 选入）：**4** 条。
4. **`scope: excluded` 未实现**（汇编器拒绝、执行 ILLI）：**2** 条 —— 不在本期范围。

### 3.1 真缺口·候补优化面（78 条）

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
| `set.w_rwii_rf` | `set.w` | `rwii` | `fp` |
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

