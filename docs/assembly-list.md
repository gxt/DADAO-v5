# DADAO 汇编指令表（新语法）

> **生成器**：`tools/llvm/gen_asm_list.py`（生成物，勿手工编辑；改生成器后重跑）
> **源**：`contracts/opcodes.yaml`（256 条 = M1 178 + `excluded_m1` 78）
> **语法**：`docs/spec/assembly-language.md`（**v1 生效，待实现**）
> **分章**：**8位数据运算** / **16位数据运算** / **32位数据运算** / **64位数据运算** / **64位地址运算** / 浮点 / 存储 / 控制流 / **寄存器复制**（`cs.*` 与寄存器组→寄存器组） / **16位立即数操作**（rwii 格式） / 其它 / **待定**（暂不归类：`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*`/`rela*`/`f*madd`）
> **deferred**（用户裁定 2026-09-25）：**浮点**（46 条，待浮点专门任务）与**待定**（14 条，暂不归类，待必须启用时）**整章 deferred**；其余 196 条为当前有效书写形式
> **注（非 deferred 的 rf 条目）**：浮点寄存器的**读写**——`ld.*`/`st.*`/`ldm.*`/`stm.*` 的 `rf` 形式（8 条）、`cs.*-rf` 与 `rd2rf`/`rf2rd`（7 条）、`set.w-rf`（1 条）——**不**属 deferred：浮点寄存器默认存在，这些只读写寄存器、不涉浮点运算（用户裁定 2026-09-25）
> **注（`ldm.*`/`stm.*` 的组记法）**：汇编形式列的 `{rdHA:rdHA+immu6-1}` 表示「以 `rdHA` 为起点、个数由 `immu6` 字段决定的连续寄存器组」（字面语法见 `docs/spec/assembly-language.md` §4.2）
> **列**：助记符 ｜ format ｜ feature ｜ 汇编形式（字段名，如 `rdHA`） ｜ id（= 助记符_format_feature）

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
| `wpN` | wyde 位置 0..3 |

### 8位数据运算（26 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `add.sb` | `orrr` | `rd` | `add.sb rdHB, rdHC, rdHD` | `add.sb_orrr_rd` |
| `add.ub` | `orrr` | `rd` | `add.ub rdHB, rdHC, rdHD` | `add.ub_orrr_rd` |
| `and.b` | `orrr` | `rd` | `and.b rdHB, rdHC, rdHD` | `and.b_orrr_rd` |
| `cmp.sb` | `orrr` | `rd` | `cmp.sb rdHB, rdHC, rdHD` | `cmp.sb_orrr_rd` |
| `cmp.ub` | `orrr` | `rd` | `cmp.ub rdHB, rdHC, rdHD` | `cmp.ub_orrr_rd` |
| `div.sb` | `orrr` | `rd` | `div.sb rdHB, rdHC, rdHD` | `div.sb_orrr_rd` |
| `div.ub` | `orrr` | `rd` | `div.ub rdHB, rdHC, rdHD` | `div.ub_orrr_rd` |
| `ext.sb` | `orri` | `rd` | `ext.sb rdHB, rdHC, immu6` | `ext.sb_orri_rd` |
| `ext.sb` | `orrr` | `rd` | `ext.sb rdHB, rdHC, rdHD` | `ext.sb_orrr_rd` |
| `ext.ub` | `orri` | `rd` | `ext.ub rdHB, rdHC, immu6` | `ext.ub_orri_rd` |
| `ext.ub` | `orrr` | `rd` | `ext.ub rdHB, rdHC, rdHD` | `ext.ub_orrr_rd` |
| `mul.sb` | `orrr` | `rd` | `mul.sb rdHB, rdHC, rdHD` | `mul.sb_orrr_rd` |
| `mul.ub` | `orrr` | `rd` | `mul.ub rdHB, rdHC, rdHD` | `mul.ub_orrr_rd` |
| `or.b` | `orrr` | `rd` | `or.b rdHB, rdHC, rdHD` | `or.b_orrr_rd` |
| `rem.sb` | `orrr` | `rd` | `rem.sb rdHB, rdHC, rdHD` | `rem.sb_orrr_rd` |
| `rem.ub` | `orrr` | `rd` | `rem.ub rdHB, rdHC, rdHD` | `rem.ub_orrr_rd` |
| `shl.ub` | `orri` | `rd` | `shl.ub rdHB, rdHC, immu6` | `shl.ub_orri_rd` |
| `shl.ub` | `orrr` | `rd` | `shl.ub rdHB, rdHC, rdHD` | `shl.ub_orrr_rd` |
| `shr.sb` | `orri` | `rd` | `shr.sb rdHB, rdHC, immu6` | `shr.sb_orri_rd` |
| `shr.sb` | `orrr` | `rd` | `shr.sb rdHB, rdHC, rdHD` | `shr.sb_orrr_rd` |
| `shr.ub` | `orri` | `rd` | `shr.ub rdHB, rdHC, immu6` | `shr.ub_orri_rd` |
| `shr.ub` | `orrr` | `rd` | `shr.ub rdHB, rdHC, rdHD` | `shr.ub_orrr_rd` |
| `sub.sb` | `orrr` | `rd` | `sub.sb rdHB, rdHC, rdHD` | `sub.sb_orrr_rd` |
| `sub.ub` | `orrr` | `rd` | `sub.ub rdHB, rdHC, rdHD` | `sub.ub_orrr_rd` |
| `xnor.b` | `orrr` | `rd` | `xnor.b rdHB, rdHC, rdHD` | `xnor.b_orrr_rd` |
| `xor.b` | `orrr` | `rd` | `xor.b rdHB, rdHC, rdHD` | `xor.b_orrr_rd` |

### 16位数据运算（26 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `add.sw` | `orrr` | `rd` | `add.sw rdHB, rdHC, rdHD` | `add.sw_orrr_rd` |
| `add.uw` | `orrr` | `rd` | `add.uw rdHB, rdHC, rdHD` | `add.uw_orrr_rd` |
| `and.w` | `orrr` | `rd` | `and.w rdHB, rdHC, rdHD` | `and.w_orrr_rd` |
| `cmp.sw` | `orrr` | `rd` | `cmp.sw rdHB, rdHC, rdHD` | `cmp.sw_orrr_rd` |
| `cmp.uw` | `orrr` | `rd` | `cmp.uw rdHB, rdHC, rdHD` | `cmp.uw_orrr_rd` |
| `div.sw` | `orrr` | `rd` | `div.sw rdHB, rdHC, rdHD` | `div.sw_orrr_rd` |
| `div.uw` | `orrr` | `rd` | `div.uw rdHB, rdHC, rdHD` | `div.uw_orrr_rd` |
| `ext.sw` | `orri` | `rd` | `ext.sw rdHB, rdHC, immu6` | `ext.sw_orri_rd` |
| `ext.sw` | `orrr` | `rd` | `ext.sw rdHB, rdHC, rdHD` | `ext.sw_orrr_rd` |
| `ext.uw` | `orri` | `rd` | `ext.uw rdHB, rdHC, immu6` | `ext.uw_orri_rd` |
| `ext.uw` | `orrr` | `rd` | `ext.uw rdHB, rdHC, rdHD` | `ext.uw_orrr_rd` |
| `mul.sw` | `orrr` | `rd` | `mul.sw rdHB, rdHC, rdHD` | `mul.sw_orrr_rd` |
| `mul.uw` | `orrr` | `rd` | `mul.uw rdHB, rdHC, rdHD` | `mul.uw_orrr_rd` |
| `or.w` | `orrr` | `rd` | `or.w rdHB, rdHC, rdHD` | `or.w_orrr_rd` |
| `rem.sw` | `orrr` | `rd` | `rem.sw rdHB, rdHC, rdHD` | `rem.sw_orrr_rd` |
| `rem.uw` | `orrr` | `rd` | `rem.uw rdHB, rdHC, rdHD` | `rem.uw_orrr_rd` |
| `shl.uw` | `orri` | `rd` | `shl.uw rdHB, rdHC, immu6` | `shl.uw_orri_rd` |
| `shl.uw` | `orrr` | `rd` | `shl.uw rdHB, rdHC, rdHD` | `shl.uw_orrr_rd` |
| `shr.sw` | `orri` | `rd` | `shr.sw rdHB, rdHC, immu6` | `shr.sw_orri_rd` |
| `shr.sw` | `orrr` | `rd` | `shr.sw rdHB, rdHC, rdHD` | `shr.sw_orrr_rd` |
| `shr.uw` | `orri` | `rd` | `shr.uw rdHB, rdHC, immu6` | `shr.uw_orri_rd` |
| `shr.uw` | `orrr` | `rd` | `shr.uw rdHB, rdHC, rdHD` | `shr.uw_orrr_rd` |
| `sub.sw` | `orrr` | `rd` | `sub.sw rdHB, rdHC, rdHD` | `sub.sw_orrr_rd` |
| `sub.uw` | `orrr` | `rd` | `sub.uw rdHB, rdHC, rdHD` | `sub.uw_orrr_rd` |
| `xnor.w` | `orrr` | `rd` | `xnor.w rdHB, rdHC, rdHD` | `xnor.w_orrr_rd` |
| `xor.w` | `orrr` | `rd` | `xor.w rdHB, rdHC, rdHD` | `xor.w_orrr_rd` |

### 32位数据运算（26 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `add.st` | `orrr` | `rd` | `add.st rdHB, rdHC, rdHD` | `add.st_orrr_rd` |
| `add.ut` | `orrr` | `rd` | `add.ut rdHB, rdHC, rdHD` | `add.ut_orrr_rd` |
| `and.t` | `orrr` | `rd` | `and.t rdHB, rdHC, rdHD` | `and.t_orrr_rd` |
| `cmp.st` | `orrr` | `rd` | `cmp.st rdHB, rdHC, rdHD` | `cmp.st_orrr_rd` |
| `cmp.ut` | `orrr` | `rd` | `cmp.ut rdHB, rdHC, rdHD` | `cmp.ut_orrr_rd` |
| `div.st` | `orrr` | `rd` | `div.st rdHB, rdHC, rdHD` | `div.st_orrr_rd` |
| `div.ut` | `orrr` | `rd` | `div.ut rdHB, rdHC, rdHD` | `div.ut_orrr_rd` |
| `ext.st` | `orri` | `rd` | `ext.st rdHB, rdHC, immu6` | `ext.st_orri_rd` |
| `ext.st` | `orrr` | `rd` | `ext.st rdHB, rdHC, rdHD` | `ext.st_orrr_rd` |
| `ext.ut` | `orri` | `rd` | `ext.ut rdHB, rdHC, immu6` | `ext.ut_orri_rd` |
| `ext.ut` | `orrr` | `rd` | `ext.ut rdHB, rdHC, rdHD` | `ext.ut_orrr_rd` |
| `mul.st` | `orrr` | `rd` | `mul.st rdHB, rdHC, rdHD` | `mul.st_orrr_rd` |
| `mul.ut` | `orrr` | `rd` | `mul.ut rdHB, rdHC, rdHD` | `mul.ut_orrr_rd` |
| `or.t` | `orrr` | `rd` | `or.t rdHB, rdHC, rdHD` | `or.t_orrr_rd` |
| `rem.st` | `orrr` | `rd` | `rem.st rdHB, rdHC, rdHD` | `rem.st_orrr_rd` |
| `rem.ut` | `orrr` | `rd` | `rem.ut rdHB, rdHC, rdHD` | `rem.ut_orrr_rd` |
| `shl.ut` | `orri` | `rd` | `shl.ut rdHB, rdHC, immu6` | `shl.ut_orri_rd` |
| `shl.ut` | `orrr` | `rd` | `shl.ut rdHB, rdHC, rdHD` | `shl.ut_orrr_rd` |
| `shr.st` | `orri` | `rd` | `shr.st rdHB, rdHC, immu6` | `shr.st_orri_rd` |
| `shr.st` | `orrr` | `rd` | `shr.st rdHB, rdHC, rdHD` | `shr.st_orrr_rd` |
| `shr.ut` | `orri` | `rd` | `shr.ut rdHB, rdHC, immu6` | `shr.ut_orri_rd` |
| `shr.ut` | `orrr` | `rd` | `shr.ut rdHB, rdHC, rdHD` | `shr.ut_orrr_rd` |
| `sub.st` | `orrr` | `rd` | `sub.st rdHB, rdHC, rdHD` | `sub.st_orrr_rd` |
| `sub.ut` | `orrr` | `rd` | `sub.ut rdHB, rdHC, rdHD` | `sub.ut_orrr_rd` |
| `xnor.t` | `orrr` | `rd` | `xnor.t rdHB, rdHC, rdHD` | `xnor.t_orrr_rd` |
| `xor.t` | `orrr` | `rd` | `xor.t rdHB, rdHC, rdHD` | `xor.t_orrr_rd` |

### 64位数据运算（29 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `add.si` | `riii` | `rd` | `add.si rdHA, imms18` | `add.si_riii_rd` |
| `add.so` | `rrrr` | `rd` | `add.so rdHA, rdHB, rdHC, rdHD` | `add.so_rrrr_rd` |
| `add.uo` | `rrrr` | `rd` | `add.uo rdHA, rdHB, rdHC, rdHD` | `add.uo_rrrr_rd` |
| `and.o` | `orrr` | `rd` | `and.o rdHB, rdHC, rdHD` | `and.o_orrr_rd` |
| `cmp.si` | `rrii` | `rd` | `cmp.si rdHA, rdHB, imms12` | `cmp.si_rrii_rd` |
| `cmp.so` | `orrr` | `rd` | `cmp.so rdHB, rdHC, rdHD` | `cmp.so_orrr_rd` |
| `cmp.ui` | `rrii` | `rd` | `cmp.ui rdHA, rdHB, immu12` | `cmp.ui_rrii_rd` |
| `cmp.uo` | `orrr` | `rd` | `cmp.uo rdHB, rdHC, rdHD` | `cmp.uo_orrr_rd` |
| `div.so` | `orrr` | `rd` | `div.so rdHB, rdHC, rdHD` | `div.so_orrr_rd` |
| `div.uo` | `orrr` | `rd` | `div.uo rdHB, rdHC, rdHD` | `div.uo_orrr_rd` |
| `ext.so` | `orri` | `rd` | `ext.so rdHB, rdHC, immu6` | `ext.so_orri_rd` |
| `ext.so` | `orrr` | `rd` | `ext.so rdHB, rdHC, rdHD` | `ext.so_orrr_rd` |
| `ext.uo` | `orri` | `rd` | `ext.uo rdHB, rdHC, immu6` | `ext.uo_orri_rd` |
| `ext.uo` | `orrr` | `rd` | `ext.uo rdHB, rdHC, rdHD` | `ext.uo_orrr_rd` |
| `mul.so` | `rrrr` | `rd` | `mul.so rdHA, rdHB, rdHC, rdHD` | `mul.so_rrrr_rd` |
| `mul.uo` | `rrrr` | `rd` | `mul.uo rdHA, rdHB, rdHC, rdHD` | `mul.uo_rrrr_rd` |
| `or.o` | `orrr` | `rd` | `or.o rdHB, rdHC, rdHD` | `or.o_orrr_rd` |
| `rem.so` | `orrr` | `rd` | `rem.so rdHB, rdHC, rdHD` | `rem.so_orrr_rd` |
| `rem.uo` | `orrr` | `rd` | `rem.uo rdHB, rdHC, rdHD` | `rem.uo_orrr_rd` |
| `shl.uo` | `orri` | `rd` | `shl.uo rdHB, rdHC, immu6` | `shl.uo_orri_rd` |
| `shl.uo` | `orrr` | `rd` | `shl.uo rdHB, rdHC, rdHD` | `shl.uo_orrr_rd` |
| `shr.so` | `orri` | `rd` | `shr.so rdHB, rdHC, immu6` | `shr.so_orri_rd` |
| `shr.so` | `orrr` | `rd` | `shr.so rdHB, rdHC, rdHD` | `shr.so_orrr_rd` |
| `shr.uo` | `orri` | `rd` | `shr.uo rdHB, rdHC, immu6` | `shr.uo_orri_rd` |
| `shr.uo` | `orrr` | `rd` | `shr.uo rdHB, rdHC, rdHD` | `shr.uo_orrr_rd` |
| `sub.so` | `rrrr` | `rd` | `sub.so rdHA, rdHB, rdHC, rdHD` | `sub.so_rrrr_rd` |
| `sub.uo` | `rrrr` | `rd` | `sub.uo rdHA, rdHB, rdHC, rdHD` | `sub.uo_rrrr_rd` |
| `xnor.o` | `orrr` | `rd` | `xnor.o rdHB, rdHC, rdHD` | `xnor.o_orrr_rd` |
| `xor.o` | `orrr` | `rd` | `xor.o rdHB, rdHC, rdHD` | `xor.o_orrr_rd` |

### 64位地址运算（4 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `add.si` | `riii` | `rb` | `add.si rbHA, imms18` | `add.si_riii_rb` |
| `add.so` | `orrr` | `rb` | `add.so rbHB, rbHC, rdHD` | `add.so_orrr_rb` |
| `cmp.uo` | `orrr` | `rb` | `cmp.uo rdHB, rbHC, rbHD` | `cmp.uo_orrr_rb` |
| `sub.so` | `orrr` | `rb` | `sub.so rbHB, rbHC, rdHD` | `sub.so_orrr_rb` |

### 浮点（46 条）｜ **deferred** — 待浮点专门任务

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `fo2fo` | `orri` | `rf` | `fo2fo rfHB, rfHC, immu6` | `fo2fo_orri_rf` |
| `fo2ft` | `orri` | `rf` | `fo2ft rfHB, rfHC, immu6` | `fo2ft_orri_rf` |
| `fo2io` | `orri` | `rf` | `fo2io rdHB, rfHC, immu6` | `fo2io_orri_rf` |
| `fo2it` | `orri` | `rf` | `fo2it rdHB, rfHC, immu6` | `fo2it_orri_rf` |
| `fo2uo` | `orri` | `rf` | `fo2uo rdHB, rfHC, immu6` | `fo2uo_orri_rf` |
| `fo2ut` | `orri` | `rf` | `fo2ut rdHB, rfHC, immu6` | `fo2ut_orri_rf` |
| `foadd` | `orrr` | `rf` | `foadd rfHB, rfHC, rfHD` | `foadd_orrr_rf` |
| `focls` | `orri` | `rf` | `focls rdHB, rfHC, immu6` | `focls_orri_rf` |
| `fodiv` | `orrr` | `rf` | `fodiv rfHB, rfHC, rfHD` | `fodiv_orrr_rf` |
| `folog` | `orri` | `rf` | `folog rfHB, rfHC, immu6` | `folog_orri_rf` |
| `fomul` | `orrr` | `rf` | `fomul rfHB, rfHC, rfHD` | `fomul_orrr_rf` |
| `foqcmp` | `orrr` | `rf` | `foqcmp rdHB, rfHC, rfHD` | `foqcmp_orrr_rf` |
| `forem` | `orrr` | `rf` | `forem rfHB, rfHC, rfHD` | `forem_orrr_rf` |
| `foroot` | `orri` | `rf` | `foroot rfHB, rfHC, immu6` | `foroot_orri_rf` |
| `fosclb` | `orrr` | `rf` | `fosclb rfHB, rfHC, rfHD` | `fosclb_orrr_rf` |
| `foscmp` | `orrr` | `rf` | `foscmp rdHB, rfHC, rfHD` | `foscmp_orrr_rf` |
| `fosgnj` | `orrr` | `rf` | `fosgnj rfHB, rfHC, rfHD` | `fosgnj_orrr_rf` |
| `fosgnn` | `orrr` | `rf` | `fosgnn rfHB, rfHC, rfHD` | `fosgnn_orrr_rf` |
| `fosub` | `orrr` | `rf` | `fosub rfHB, rfHC, rfHD` | `fosub_orrr_rf` |
| `ft2fo` | `orri` | `rf` | `ft2fo rfHB, rfHC, immu6` | `ft2fo_orri_rf` |
| `ft2ft` | `orri` | `rf` | `ft2ft rfHB, rfHC, immu6` | `ft2ft_orri_rf` |
| `ft2io` | `orri` | `rf` | `ft2io rdHB, rfHC, immu6` | `ft2io_orri_rf` |
| `ft2it` | `orri` | `rf` | `ft2it rdHB, rfHC, immu6` | `ft2it_orri_rf` |
| `ft2uo` | `orri` | `rf` | `ft2uo rdHB, rfHC, immu6` | `ft2uo_orri_rf` |
| `ft2ut` | `orri` | `rf` | `ft2ut rdHB, rfHC, immu6` | `ft2ut_orri_rf` |
| `ftadd` | `orrr` | `rf` | `ftadd rfHB, rfHC, rfHD` | `ftadd_orrr_rf` |
| `ftcls` | `orri` | `rf` | `ftcls rdHB, rfHC, immu6` | `ftcls_orri_rf` |
| `ftdiv` | `orrr` | `rf` | `ftdiv rfHB, rfHC, rfHD` | `ftdiv_orrr_rf` |
| `ftlog` | `orri` | `rf` | `ftlog rfHB, rfHC, immu6` | `ftlog_orri_rf` |
| `ftmul` | `orrr` | `rf` | `ftmul rfHB, rfHC, rfHD` | `ftmul_orrr_rf` |
| `ftqcmp` | `orrr` | `rf` | `ftqcmp rdHB, rfHC, rfHD` | `ftqcmp_orrr_rf` |
| `ftrem` | `orrr` | `rf` | `ftrem rfHB, rfHC, rfHD` | `ftrem_orrr_rf` |
| `ftroot` | `orri` | `rf` | `ftroot rfHB, rfHC, immu6` | `ftroot_orri_rf` |
| `ftsclb` | `orrr` | `rf` | `ftsclb rfHB, rfHC, rfHD` | `ftsclb_orrr_rf` |
| `ftscmp` | `orrr` | `rf` | `ftscmp rdHB, rfHC, rfHD` | `ftscmp_orrr_rf` |
| `ftsgnj` | `orrr` | `rf` | `ftsgnj rfHB, rfHC, rfHD` | `ftsgnj_orrr_rf` |
| `ftsgnn` | `orrr` | `rf` | `ftsgnn rfHB, rfHC, rfHD` | `ftsgnn_orrr_rf` |
| `ftsub` | `orrr` | `rf` | `ftsub rfHB, rfHC, rfHD` | `ftsub_orrr_rf` |
| `io2fo` | `orri` | `rf` | `io2fo rfHB, rdHC, immu6` | `io2fo_orri_rf` |
| `io2ft` | `orri` | `rf` | `io2ft rfHB, rdHC, immu6` | `io2ft_orri_rf` |
| `it2fo` | `orri` | `rf` | `it2fo rfHB, rdHC, immu6` | `it2fo_orri_rf` |
| `it2ft` | `orri` | `rf` | `it2ft rfHB, rdHC, immu6` | `it2ft_orri_rf` |
| `uo2fo` | `orri` | `rf` | `uo2fo rfHB, rdHC, immu6` | `uo2fo_orri_rf` |
| `uo2ft` | `orri` | `rf` | `uo2ft rfHB, rdHC, immu6` | `uo2ft_orri_rf` |
| `ut2fo` | `orri` | `rf` | `ut2fo rfHB, rdHC, immu6` | `ut2fo_orri_rf` |
| `ut2ft` | `orri` | `rf` | `ut2ft rfHB, rdHC, immu6` | `ut2ft_orri_rf` |

### 存储（38 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `ld.o` | `rrii` | `ra` | `ld.o raHA, [rbHB, imms12]` | `ld.o_rrii_ra` |
| `ld.o` | `rrii` | `rb` | `ld.o rbHA, [rbHB, imms12]` | `ld.o_rrii_rb` |
| `ld.o` | `rrii` | `rd` | `ld.o rdHA, [rbHB, imms12]` | `ld.o_rrii_rd` |
| `ld.o` | `rrii` | `rf` | `ld.o rfHA, [rbHB, imms12]` | `ld.o_rrii_rf` |
| `ld.sb` | `rrii` | `rd` | `ld.sb rdHA, [rbHB, imms12]` | `ld.sb_rrii_rd` |
| `ld.st` | `rrii` | `rd` | `ld.st rdHA, [rbHB, imms12]` | `ld.st_rrii_rd` |
| `ld.sw` | `rrii` | `rd` | `ld.sw rdHA, [rbHB, imms12]` | `ld.sw_rrii_rd` |
| `ld.t` | `rrii` | `rf` | `ld.t rfHA, [rbHB, imms12]` | `ld.t_rrii_rf` |
| `ld.ub` | `rrii` | `rd` | `ld.ub rdHA, [rbHB, imms12]` | `ld.ub_rrii_rd` |
| `ld.ut` | `rrii` | `rd` | `ld.ut rdHA, [rbHB, imms12]` | `ld.ut_rrii_rd` |
| `ld.uw` | `rrii` | `rd` | `ld.uw rdHA, [rbHB, imms12]` | `ld.uw_rrii_rd` |
| `ldm.o` | `rrri` | `ra` | `ldm.o {raHA:raHA+immu6-1}, [rbHB, rdHC]` | `ldm.o_rrri_ra` |
| `ldm.o` | `rrri` | `rb` | `ldm.o {rbHA:rbHA+immu6-1}, [rbHB, rdHC]` | `ldm.o_rrri_rb` |
| `ldm.o` | `rrri` | `rd` | `ldm.o {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.o_rrri_rd` |
| `ldm.o` | `rrri` | `rf` | `ldm.o {rfHA:rfHA+immu6-1}, [rbHB, rdHC]` | `ldm.o_rrri_rf` |
| `ldm.sb` | `rrri` | `rd` | `ldm.sb {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.sb_rrri_rd` |
| `ldm.st` | `rrri` | `rd` | `ldm.st {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.st_rrri_rd` |
| `ldm.sw` | `rrri` | `rd` | `ldm.sw {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.sw_rrri_rd` |
| `ldm.t` | `rrri` | `rf` | `ldm.t {rfHA:rfHA+immu6-1}, [rbHB, rdHC]` | `ldm.t_rrri_rf` |
| `ldm.ub` | `rrri` | `rd` | `ldm.ub {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.ub_rrri_rd` |
| `ldm.ut` | `rrri` | `rd` | `ldm.ut {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.ut_rrri_rd` |
| `ldm.uw` | `rrri` | `rd` | `ldm.uw {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.uw_rrri_rd` |
| `st.b` | `rrii` | `rd` | `st.b rdHA, [rbHB, imms12]` | `st.b_rrii_rd` |
| `st.o` | `rrii` | `ra` | `st.o raHA, [rbHB, imms12]` | `st.o_rrii_ra` |
| `st.o` | `rrii` | `rb` | `st.o rbHA, [rbHB, imms12]` | `st.o_rrii_rb` |
| `st.o` | `rrii` | `rd` | `st.o rdHA, [rbHB, imms12]` | `st.o_rrii_rd` |
| `st.o` | `rrii` | `rf` | `st.o rfHA, [rbHB, imms12]` | `st.o_rrii_rf` |
| `st.t` | `rrii` | `rd` | `st.t rdHA, [rbHB, imms12]` | `st.t_rrii_rd` |
| `st.t` | `rrii` | `rf` | `st.t rfHA, [rbHB, imms12]` | `st.t_rrii_rf` |
| `st.w` | `rrii` | `rd` | `st.w rdHA, [rbHB, imms12]` | `st.w_rrii_rd` |
| `stm.b` | `rrri` | `rd` | `stm.b {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `stm.b_rrri_rd` |
| `stm.o` | `rrri` | `ra` | `stm.o {raHA:raHA+immu6-1}, [rbHB, rdHC]` | `stm.o_rrri_ra` |
| `stm.o` | `rrri` | `rb` | `stm.o {rbHA:rbHA+immu6-1}, [rbHB, rdHC]` | `stm.o_rrri_rb` |
| `stm.o` | `rrri` | `rd` | `stm.o {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `stm.o_rrri_rd` |
| `stm.o` | `rrri` | `rf` | `stm.o {rfHA:rfHA+immu6-1}, [rbHB, rdHC]` | `stm.o_rrri_rf` |
| `stm.t` | `rrri` | `rd` | `stm.t {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `stm.t_rrri_rd` |
| `stm.t` | `rrri` | `rf` | `stm.t {rfHA:rfHA+immu6-1}, [rbHB, rdHC]` | `stm.t_rrri_rf` |
| `stm.w` | `rrri` | `rd` | `stm.w {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `stm.w_rrri_rd` |

### 控制流（15 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `br.eq` | `rrii` | `rd` | `br.eq {rdHA, rdHB}?, [rb0, imms12i]` | `br.eq_rrii_rd` |
| `br.n` | `riii` | `rd` | `br.n {rdHA}?, [rb0, imms18i]` | `br.n_riii_rd` |
| `br.ne` | `rrii` | `rd` | `br.ne {rdHA, rdHB}?, [rb0, imms12i]` | `br.ne_rrii_rd` |
| `br.nn` | `riii` | `rd` | `br.nn {rdHA}?, [rb0, imms18i]` | `br.nn_riii_rd` |
| `br.np` | `riii` | `rd` | `br.np {rdHA}?, [rb0, imms18i]` | `br.np_riii_rd` |
| `br.nz` | `riii` | `rb` | `br.nz {rbHA}?, [rb0, imms18i]` | `br.nz_riii_rb` |
| `br.nz` | `riii` | `rd` | `br.nz {rdHA}?, [rb0, imms18i]` | `br.nz_riii_rd` |
| `br.p` | `riii` | `rd` | `br.p {rdHA}?, [rb0, imms18i]` | `br.p_riii_rd` |
| `br.z` | `riii` | `rb` | `br.z {rbHA}?, [rb0, imms18i]` | `br.z_riii_rb` |
| `br.z` | `riii` | `rd` | `br.z {rdHA}?, [rb0, imms18i]` | `br.z_riii_rd` |
| `call` | `iiii` | `ra` | `call [rb0, imms24i]` | `call_iiii_ra` |
| `call` | `rrii` | `ra` | `call [rbHA, rdHB, imms12i]` | `call_rrii_ra` |
| `jump` | `iiii` | `rb` | `jump [rb0, imms24i]` | `jump_iiii_rb` |
| `jump` | `rrii` | `rb` | `jump [rbHA, rdHB, imms12i]` | `jump_rrii_rb` |
| `ret` | `riii` | `ra` | `ret rdHA, imms18` | `ret_riii_ra` |

### 寄存器复制（18 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `cs.eq` | `rrrr` | `rd` | `cs.eq {rdHA, rdHB}?, rdHC, rdHD` | `cs.eq_rrrr_rd` |
| `cs.eq` | `rrrr` | `rf` | `cs.eq {rdHA, rdHB}?, rfHC, rfHD` | `cs.eq_rrrr_rf` |
| `cs.n` | `rrrr` | `rd` | `cs.n {rdHA}?, rdHB, rdHC, rdHD` | `cs.n_rrrr_rd` |
| `cs.n` | `rrrr` | `rf` | `cs.n {rdHA}?, rfHB, rfHC, rfHD` | `cs.n_rrrr_rf` |
| `cs.ne` | `rrrr` | `rd` | `cs.ne {rdHA, rdHB}?, rdHC, rdHD` | `cs.ne_rrrr_rd` |
| `cs.ne` | `rrrr` | `rf` | `cs.ne {rdHA, rdHB}?, rfHC, rfHD` | `cs.ne_rrrr_rf` |
| `cs.p` | `rrrr` | `rd` | `cs.p {rdHA}?, rdHB, rdHC, rdHD` | `cs.p_rrrr_rd` |
| `cs.p` | `rrrr` | `rf` | `cs.p {rdHA}?, rfHB, rfHC, rfHD` | `cs.p_rrrr_rf` |
| `cs.z` | `rrrr` | `rd` | `cs.z {rdHA}?, rdHB, rdHC, rdHD` | `cs.z_rrrr_rd` |
| `cs.z` | `rrrr` | `rf` | `cs.z {rdHA}?, rfHB, rfHC, rfHD` | `cs.z_rrrr_rf` |
| `ra2rd` | `orri` | `ra` | `ra2rd rdHB, raHC, immu6` | `ra2rd_orri_ra` |
| `rb2rb` | `orri` | `rb` | `rb2rb rbHB, rbHC, immu6` | `rb2rb_orri_rb` |
| `rb2rd` | `orri` | `rb` | `rb2rd rdHB, rbHC, immu6` | `rb2rd_orri_rb` |
| `rd2ra` | `orri` | `ra` | `rd2ra raHB, rdHC, immu6` | `rd2ra_orri_ra` |
| `rd2rb` | `orri` | `rb` | `rd2rb rbHB, rdHC, immu6` | `rd2rb_orri_rb` |
| `rd2rd` | `orri` | `rd` | `rd2rd rdHB, rdHC, immu6` | `rd2rd_orri_rd` |
| `rd2rf` | `orri` | `rf` | `rd2rf rfHB, rdHC, immu6` | `rd2rf_orri_rf` |
| `rf2rd` | `orri` | `rf` | `rf2rd rdHB, rfHC, immu6` | `rf2rd_orri_rf` |

### 16位立即数操作（8 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `andn.w` | `rwii` | `rb` | `andn.w rbHA, wpN, immu16` | `andn.w_rwii_rb` |
| `andn.w` | `rwii` | `rd` | `andn.w rdHA, wpN, immu16` | `andn.w_rwii_rd` |
| `or.w` | `rwii` | `rb` | `or.w rbHA, wpN, immu16` | `or.w_rwii_rb` |
| `or.w` | `rwii` | `rd` | `or.w rdHA, wpN, immu16` | `or.w_rwii_rd` |
| `set.ow` | `rwii` | `rd` | `set.ow rdHA, wpN, immu16` | `set.ow_rwii_rd` |
| `set.w` | `rwii` | `rf` | `set.w rfHA, wpN, immu16` | `set.w_rwii_rf` |
| `set.zw` | `rwii` | `rb` | `set.zw rbHA, wpN, immu16` | `set.zw_rwii_rb` |
| `set.zw` | `rwii` | `rd` | `set.zw rdHA, wpN, immu16` | `set.zw_rwii_rd` |

### 其它（6 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `cfx2rc` | `crrr` | `cfx` | `cfx2rc cfxcode, cgHB, rcHC, rdHD` | `cfx2rc_crrr_cfx` |
| `cfx2rd` | `crrr` | `cfx` | `cfx2rd cfxcode, cgHB, rcHC, rdHD` | `cfx2rd_crrr_cfx` |
| `escape` | `ciii` | `cfx` | `escape cfxcode, [excp_cause_ip, imms18i]` | `escape_ciii_cfx` |
| `illi` | `oiii` | `imm` | `illi immu18` | `illi_oiii_imm` |
| `swym` | `iiii` | `imm` | `swym immu24` | `swym_iiii_imm` |
| `trap` | `ciii` | `cfx` | `trap cfxcode, immu18` | `trap_ciii_cfx` |

### 待定（14 条）｜ **deferred** — 暂不归类，待必须启用时

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `cfxld` | `crii` | `cfx` | `cfxld cfxcode, [rbHB, immu12]` | `cfxld_crii_cfx` |
| `cfxst` | `crii` | `cfx` | `cfxst cfxcode, [rbHB, immu12]` | `cfxst_crii_cfx` |
| `fence` | `oiii` | `imm` | `fence immu18` | `fence_oiii_imm` |
| `fomadd` | `rrrr` | `rf` | `fomadd rfHA, rfHB, rfHC, rfHD` | `fomadd_rrrr_rf` |
| `ftmadd` | `rrrr` | `rf` | `ftmadd rfHA, rfHB, rfHC, rfHD` | `ftmadd_rrrr_rf` |
| `lr_an.o` | `orrr` | `rd` | `lr_an.o rdHC, [rbHD]` | `lr_an.o_orrr_rd` |
| `lr_ar.o` | `orrr` | `rd` | `lr_ar.o rdHC, [rbHD]` | `lr_ar.o_orrr_rd` |
| `lr_nn.o` | `orrr` | `rd` | `lr_nn.o rdHC, [rbHD]` | `lr_nn.o_orrr_rd` |
| `lr_nr.o` | `orrr` | `rd` | `lr_nr.o rdHC, [rbHD]` | `lr_nr.o_orrr_rd` |
| `rela.si` | `riii` | `rb` | `rela.si rbHA, imms18` | `rela.si_riii_rb` |
| `sc_an.o` | `orrr` | `rd` | `sc_an.o rdHB, rdHC, [rbHD]` | `sc_an.o_orrr_rd` |
| `sc_ar.o` | `orrr` | `rd` | `sc_ar.o rdHB, rdHC, [rbHD]` | `sc_ar.o_orrr_rd` |
| `sc_nn.o` | `orrr` | `rd` | `sc_nn.o rdHB, rdHC, [rbHD]` | `sc_nn.o_orrr_rd` |
| `sc_nr.o` | `orrr` | `rd` | `sc_nr.o rdHB, rdHC, [rbHD]` | `sc_nr.o_orrr_rd` |
