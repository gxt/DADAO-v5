# m15-idl-007: `SimRISC-07`（浮点运算）逐条 operation

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-spec-001`（语法基线、寄存器模型、语义库、`idl/render.py` 已就绪）
**可并行分片**：可与其它 `m15-idl-0xx` 并行（**各册独立文件**）；`idl/README.md §4` 语义库**不得自行动手**（缺函数 ⇒ 待裁定）
**预估**：5–7 天
**档位**：中改
**状态**：待验收

## 目标

把 `spec/SimRISC-07-浮点运算.md` 里**每条指令**写成一段 operation，落到 **`idl/SimRISC-07.idl`**，再由 `idl/render.py` 生成 spec 内的 `<!-- IDL:<id> BEGIN/END -->` 块。

> 本册若已有 `m15-spec-001` 留下的样板 operation（01/04/06/11/12 各 1 条），按**同一风格**补齐其余指令，不重写已有样板。

## 用户裁定（2026-11-19，必须遵守）

1. **不修改原来的散文内容**——`spec/` 里只允许 `render.py` 写标记块，散文一字不动；
2. **发现散文不对、或与其它册/`spec` 冲突 ⇒ 停下来问用户**：写进任务书「待裁定」（问题 + 依据 + 候选解释），**不得自行改散文、不得自行改语义库**；
3. 正常情况下**每条指令一个 operation**（一 `# id:` 一段）；确需合并/拆分时同样记「待裁定」。

## 指令清单（本册 50 条，以 `contracts/opcodes.yaml` 的 `spec_cite` 为准）

- `fo2ft_orri_rf`
- `fo2io_orri_rf`
- `fo2it_orri_rf`
- `fo2uo_orri_rf`
- `fo2ut_orri_rf`
- `foadd_orrr_rf`
- `focls_orri_rf`
- `fodiv_orrr_rf`
- `fofma_rrrr_rf`
- `fomax_orrr_rf`
- `fomin_orrr_rf`
- `fomul_orrr_rf`
- `foqcmp_orrr_rf`
- `forem_orrr_rf`
- `fornd_orri_rf`
- `foroot_orri_rf`
- `fosclb_orrr_rf`
- `foscmp_orrr_rf`
- `fosgnj_orrr_rf`
- `fosgnn_orrr_rf`
- `fosub_orrr_rf`
- `ft2fo_orri_rf`
- `ft2io_orri_rf`
- `ft2it_orri_rf`
- `ft2uo_orri_rf`
- `ft2ut_orri_rf`
- `ftadd_orrr_rf`
- `ftcls_orri_rf`
- `ftdiv_orrr_rf`
- `ftfma_rrrr_rf`
- `ftmax_orrr_rf`
- `ftmin_orrr_rf`
- `ftmul_orrr_rf`
- `ftqcmp_orrr_rf`
- `ftrem_orrr_rf`
- `ftrnd_orri_rf`
- `ftroot_orri_rf`
- `ftsclb_orrr_rf`
- `ftscmp_orrr_rf`
- `ftsgnj_orrr_rf`
- `ftsgnn_orrr_rf`
- `ftsub_orrr_rf`
- `io2fo_orri_rf`
- `io2ft_orri_rf`
- `it2fo_orri_rf`
- `it2ft_orri_rf`
- `uo2fo_orri_rf`
- `uo2ft_orri_rf`
- `ut2fo_orri_rf`
- `ut2ft_orri_rf`

## 批次（每批 ≤4 h；做完一批返回，由主会话续派下一批）

> 任务号不拆（整册一起验收）；**同一个 `.idl` 文件，同册串行**。每批只做列出的节，做完即返回，不提交。全册 50 条 ⇒ 分 5 批。

- **批 1**：§1.1 舍入方向六档 + §1.2 精确转换（SBZ） + §1.3 异常与标志
- **批 2**：§1.4 合法性 + §2.1 S2D1 + §2.2 S1D1
- **批 3**：§2.3 取整（roundToIntegral） + §2.4 最小最大值（minimumNumber / maximumNumber）
- **批 4**：§2.5 融合乘加（fusedMultiplyAdd） + §3. 浮点符号位操作指令
- **批 5**：§4. 浮点比较指令 + §5. 浮点分类指令

## 交付

1. `idl/SimRISC-07.idl`：上述每条一个 `# id: <id>` + operation；
2. spec 内对应块由 `render.py` 生成（不得手写块内容）；
3. 若某条指令的语义在散文中缺失/矛盾 ⇒ 该条**不写 operation**，记「待裁定」。

## 验收（逐条贴真实 rc）

1. **覆盖率**：`.idl` 的 id 集合 == 本册 `opcodes.yaml` 的 id 集合（脚本比对，零缺零多；「待裁定」的条目单独列出并说明为何不计入）。
2. `python3 idl/render.py --check` rc=0（spec 块与 `.idl` 逐字节一致）。
3. `idlc` 两段式：库 `compile --root isa` rc=0；本册每条 operation `compile --root instruction_operation` 全 rc=0。
4. **语义抽查 ≥3 条**：把 operation 的每条语句与散文逐句对应（贴对照），不得出现散文没说而 operation 自行发明的前提。
5. 「待裁定」逐条列出（问题 + 依据 + 建议），**不得自行处置**。
6. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**；**不改版本号**。
2. 只动 `idl/SimRISC-07.idl` + spec 本册的标记块 + 本任务书；**不动其它册**。
3. **不改 `idl/README.md`**（语义库）——缺函数就记「待裁定」。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

1. **【已解除｜浮点库三批落地，全册转换/算术/取整/最小最大/乘加/符号位均用库】** 015（ft 族 53 函数）→ 016（fo 族 + `ft_rem`/`fo_rem`）→ 017（`fo_scale`/`fo_muladd` 等）之后：批 1/2 的 ft 侧、批 2 遗留的 8 条、批 3 的取整/最小最大、本轮的 FMA/符号位**全部直接调用库函数**；仅 `ftsclb` 仍用批 2 的临时写法（指数加 `rdHD` + `normRoundPackF32`，按派单要求不动，待 017 之后另议是否改调 `ft_scale`）。**未往 `idl/lib/fp.idl` 加任何函数。**

2. **【散文未写｜fp→int32 结果的 64 位写宽】** `ft2it`/`ft2ut`/`fo2it`/`fo2ut` 的目的是 64 位 `rdHB`，但散文（§1.1 字段表、§1.3）只规定**值**（饱和值），**未写** 32 位结果如何写满 64 位。临时处置按 SimRISC 既有约定：`it`（32 位有符号）⇒ **符号扩展**、`ut`（32 位无符号）⇒ **零扩展**（同 `SimRISC-08 add.st/add.ut` 的高位规则）。请确认后由 spec 任务补一句；本任务书不改散文。

3. **【撤回｜上一轮「`rf0` 读 qNaN 位型」的疑点】** 经 reviewer 复核：`rf0[31:22]` 按 **ft 视图**恰是 ft 的 qNaN（sign=0、exp=0xFF、frac MSB=1），`rf0[63:51]` 是 fo 的 qNaN ⇒ 散文 §1.4 无误；上一轮疑点是我把 10 位字段读成 `0x3FF`（实为 `0x1FF` ⇒ 低 32 位 `0x7FC0_0000`）。**不改散文、不据此作任何实现假设。**

4. **【已解除｜全册 50 条全部写完】** 批 2 遗留 8 条（`ftrem`/`fo*` 五条/`fosclb`/`foroot`）在批 4 补齐；本轮补齐 §4 比较 4 条 + §5 分类 2 条 ⇒ **50/50**，覆盖率脚本机械核对「零缺零多」（`cover.py --batch 5`）。

5. **【散文措辞可更精确｜§2.3 的「结果 ≠ 输入 ⇒ NX」与 NaN】** §2.3 表把 `0x20` 档写成「**结果 ≠ 输入时置 NX**」。对 qNaN 输入，结果按 §1.3 做 **canonical 化**（位型改变）但 IEEE 754-2019 §5.9 把 NaN 的处理归入 quiet 计算、**不置 inexact** ⇒ 字面读法会把 canonical 化误算成 inexact。本批实现按 IEEE 排除 NaN（`if (immu6 == 6'h20 && r != a && !is_nan(a))`），散文未改；建议 spec 任务把该行改成「结果 ≠ 输入**且输入非 NaN** 时置 NX」。

6. **【已消解｜signaling compare 的 payload 不再传播】** 原疑点是「两操作数皆 NaN 时取哪个 payload」；`spec/SimRISC-07 §4` 已由用户授权改为「**四种比较一律返回 canonical quiet NaN**」（§1.3 的「signaling compare 例外条」同时删除）⇒ 不存在 payload 选择问题，本项撤销。**原 `m15-idl-018`（scmp 改 canonical）因同文件双写冲突已并入本任务返工；其任务书与台账行已撤。**

## 语义抽查（批 1–3 全部 30 条，逐句对照；机器版见 `.work/evidence/m15-idl-007/check_semantics.py` 的 `[ok]` 明细）

**§1.1 六档的公共开头**：15 条均以 `RoundingMode mode = rm_to_mode(immu6);` 起 ⇔ §1.1「`immu6` 必须是六值之一；其他取值（含 `0x00`）⇒ ILLI」+「只有 `0x20` 读 `rf0[33:32]`」（解析与 ILLI 都在库函数内，op 不直接读写 `rf0[33:32]`）。

- `ft2it`/`ft2ut`：`ft_to_i32(ft[rfHC], mode)` / `ft_to_ui32(ft[rfHC], mode)` ⇔ §1.3 的浮点→整数（NaN/±Inf/越界 ⇒ NV + 饱和、不置 NX；有限 inexact ⇒ NX）在库内；`{{32{r[31]}}, r}` / `{32'd0, r}` ⇔ 32 位结果按符号/零扩展写满（待裁定 2）。
- `ft2io`/`ft2uo`：`16'hBE - {8'd0, exp}` 与 `sig` 的加宽左移 40 位 ⇔ softfloat `f32_to_i64` 的整数对齐（0xBE = 127+63）；`softfloat_roundToI64/UI64(sign, whole, extra, mode)` ⇔ §1.3 的 NV/NX 口径；`I64_POS_OVERFLOW`/`UI64_POS_OVERFLOW` ⇔ NaN/+Inf ⇒ 最大正值 / 最大无符号值。
- `it2ft`/`ut2ft`：`rd[rdHC][31:0]` ⇔ §1「it/ut = 32 位整数」；`i32_to_ft`/`ui32_to_ft` ⇔ §1.3「精度损失 ⇒ NX（±0、−2^31 精确）」；`rf[rfHB][31:0] = …` ⇔ 册首「ft 结果只写低 32 位、高 32 位保持」。
- `io2ft`/`uo2ft`：`ft_clz64(·) - 8'd40` ⇔ softfloat `i64_to_f32` 的「24 位可精确表示」判据；精确档 `packToF32UI` 不置标志、非精确档 `softfloat_roundPackToF32` 单次舍入置 NX ⇔ §1.3；符号位恒 0（`uo2ft`）。
- `fo2it`/`fo2ut`：`a[63]`/`a[62:52]`/`a[51:0]` ⇔ IEEE 754-2019 §3.3 binary64 字段；`16'd1063 - {5'd0, exp}` ⇔ 值×2^12 的对齐（`roundToI32` 的低 12 位舍入口径）；`softfloat_roundToI32/UI32` ⇔ §1.3 的饱和与 NV/NX；`64'hFFFF_FFFF_8000_0000` / `64'h0000_0000_FFFF_FFFF` ⇔ 饱和值表。
- `fo2io`/`fo2uo`：`16'd1075 - {5'd0, exp}` ⇔ 整数部分 = `sig >> (1075−exp)`；`if (left > 16'd11)` ⇔ |值| ≥ 2^64 ⇒ NV + 饱和；`softfloat_roundToI64/UI64` ⇔ 64 位舍入与 NV/NX。
- `fo2ft`：`32'h7FC0_0000` + `frac[51] == 1'b0 ⇒ NV` ⇔ §1.3「NaN ⇒ canonical qNaN」「sNaN ⇒ NV」；`{sign, 8'hFF, 23'd0}` ⇔ ±Inf 保留符号；`{sign, 31'd0}` ⇔ ±0 保留符号（IEEE §6.3）；次正规 `16'd156 - 16'd1052 - sh`、正规 `exp − 897` ⇔ 53→24 位的对齐（库口径 `0x9C + k`）；`softfloat_roundPackToF32` ⇔ §1.3 的溢出四象限 + tininess-after-rounding 的 UF/NX。
- `io2fo`/`uo2fo`：`8'd63 - ft_clz64(·)` ⇔ 最高位序号；`p <= 8'd52` 分支 ⇔ 精确（不置标志）；`d = p − 52` + `guard`/`sticky` + 五个方向分支（含**静态 RNA**） ⇔ §1.1 六档；`kept == 2^53 ⇒ 尾数归零、指数 +1` ⇔ 进位；`set_fp_flag(FpFlag::NX)` ⇔ §1.3「精度损失 ⇒ NX」（int64 值域 ≪ f64 范围 ⇒ 无 OF/UF）。
- `ft2fo`/`it2fo`/`ut2fo`（§1.2，未改动）：SBZ 判定 + binary32/64 字段直译 + canonical qNaN/sNaN ⇒ NV；全程无舍入、无标志。

**§1.4 合法性（18 条已写转换全部落位）**：`rd` 目的 8 条（`ft2it`/`ft2io`/`ft2ut`/`ft2uo`/`fo2it`/`fo2io`/`fo2ut`/`fo2uo`）首条语句 = `if (rdHB == 6'd0) { raise(Illegal…) }` ⇔ §1.4 第 1 条（`dst_rd0`）；`rf` 目的 10 条（`ft2fo`/`it2fo`/`ut2fo`/`fo2ft`/`it2ft`/`io2ft`/`ut2ft`/`uo2ft`/`io2fo`/`uo2fo`）首条语句 = `if (rfHB == 6'd0) { … }` ⇔ §1.4 第 2 条（`dst_rf0`）。两条判定**先于**任何源读/舍入解析；`rf0` 作**源**不作限制（§1.4 明文）。§1.4 第 3 条是「不存在 `immu6` 块转换三项限制」的**否定性**条款 ⇒ operation 里**不出现**这些检查即为符合（`immu6` 只作六档/ SBZ 的语义值）。

**§2.1 已写 5 条（S2D1，ft 侧）**：`ftadd`/`ftsub`/`ftmul`/`ftdiv` 各为「`dst_rf0` 判定 → `RoundingMode mode = rm_to_mode(6'h20)`（无 `immu6` 域 ⇒ 舍入方向取 `rf0[33:32]`，§2.1 末段）→ 先读两个源 `ft[rfHC]`/`ft[rfHD]` → 一行库调用（`ft_add`/`ft_sub`/`ft_mul`/`ft_div`，值/标志/canonical qNaN/NV/DZ/OF/UF 全在库内）→ 只写目的低 32 位」。`ftsclb`：`Bits<64> n = rd[rdHD]` ⇔ 「第三操作数为 `rd` 组有符号 64 位整数指数，`rdHD = rd0` 表示指数 0」；`e64 = n + 7`（次正规）/`exp + n + 6`（正规）⇔ 库 `normRoundPackToF32` 的 `0x9C + k` 口径（`k` 为乘 2^n 后的 2 的幂次）；指数先饱和到 ±2000 再交 `softfloat_normRoundPackToF32` ⇔ 溢出/下溢按 §1.3 四象限与 UF/NX。**未写 6 条**（`ftrem` + `fo*` 五条）见「待裁定 4」。

**§2.2 已写 1 条（S1D1）**：`ftroot` = `dst_rf0` 判定 + `if (immu6 != 6'd2) raise(Illegal…)`（⇔ §2.2「仅支持 n = 2」，附录 B `encode_fp_root_n`）+ `rm_to_mode(6'h20)`（平方根的舍入属性 = 当前方向）+ 一行 `ft_sqrt`（负数 ⇒ NV + canonical qNaN、`rootn(±0,2) = +0`、`+Inf` 原样，均已在库内按 §2.2 实现）。`foroot` 见「待裁定 4」。

**§2.3 已写 2 条（取整）**：`ftrnd`/`fornd` = `dst_rf0` 判定 + `RoundingMode mode = rm_to_mode(immu6)`（`immu6` 是**取整模式**六档 one-hot；非六值 ⇒ ILLI，`0x20` 读 `rf0[33:32]`）+ 一行库调用（`round_ft_to_integral`/`round_fo_to_integral`：NaN ⇒ canonical qNaN 且 sNaN ⇒ NV、±Inf/±0 原样、`|x| ≥ 2^p` 原样、取整为 0 时沿用符号、**不置 NX**）+ `if ((immu6 == 6'h20) && (r != a) && (!is_*_nan?(a))) set NX` ⇔ §2.3「只有 `0x20` 置 NX 且仅当结果 ≠ 输入」（NaN 例外见「待裁定 5」）。写宽：`ftrnd` 只写低 32 位、`fornd` 整 64 位。

**§2.4 已写 4 条（最小最大）**：`ftmin`/`ftmax`/`fomin`/`fomax` = `dst_rf0` 判定 + **不解析舍入档**（本族不涉舍入）+ 四条 NaN 分支（双 NaN ⇒ canonical qNaN；单 NaN ⇒ **返回那个数**，不传播）+ 数值序（异号 ⇒ 负者更小，含 `−0 < +0`；同负 ⇒ 量值大者更小；同非负 ⇒ 量值小者更小；`returnMag`/`returnMagF64` 给量值）+ `sNaN ⇒ NV`（即使结果为数）。`ft`/`fo` 两族只差符号位（bit31 / bit63）与 canonical 常量（`SP_CANONICAL_NAN` / `DP_CANONICAL_NAN`）。

**§2.1 fo 侧补齐 6 条 + 余数 2 条**：`foadd`/`fosub`/`fomul`/`fodiv` = `dst_rf0` 判定 + `rm_to_mode(6'h20)`（舍入方向取 `rf0[33:32]`）+ 先读两个源 + 一行库调用（`fo_add`/`fo_sub`/`fo_mul`/`fo_div`）；`forem`/`ftrem` = **不解析舍入档** + `fo_rem`/`ft_rem`（精确余数：n = 最近整数、平局取偶；`y = ±0`/`x = ±Inf` ⇒ NV 而非 DZ；`y = ±Inf` ⇒ 返回 x；零余数取 x 的符号）；`fosclb` = `Bits<64> n = rd[rdHD]`（rd 组有符号 64 位指数）+ `fo_scale`（指数饱和/UF/OF 在库内）。

**§2.5 已写 2 条（融合乘加）**：`ftfma`/`fofma` = `dst_rf0` 判定（**目的在 `rfHA`**，`rrrr` 形态）+ `rm_to_mode(6'h20)` + 先读三个源 `rfHB`/`rfHC`/`rfHD` + `ft_muladd`/`fo_muladd(…, MulAddOp::AddC, mode)`（§2.5 只有 `(a×b)+c` 一种形态）+ 写宽（`ft` 只写低 32 位、`fo` 整 64 位）。`0 × ±Inf` 即使加数为 qNaN 也 NV、`Inf + (−Inf)` ⇒ NV、精确和为零时 RDN ⇒ −0，都在库内；**单次舍入**即 §2.5 的核心要求，oracle 用规范反例 `a×b−1 = −2^-46`（先乘后加会得 `+0`）钉住。

**§3 已写 4 条（符号位操作）**：`ftsgnj`/`fosgnj` = `(a & ~signbit) | (b & signbit)`（`copySign`），`ftsgnn`/`fosgnn` 把 `b` 的符号位取反；`ft` 用 bit31 且只写低 32 位、`fo` 用 bit63 整 64 位写；**逐位操作 ⇒ 不解析舍入档、不置任何标志**（含 NaN 位型原样搬运、`−0` 符号照抄）。

**§4 已写 4 条（比较）**：`ftqcmp`/`ftscmp`/`foqcmp`/`foscmp` = `dst_rd0` 判定 + 先读两源 + 分支链：
① **无序**：**四种比较一律 canonical quiet NaN**（`ft` 用 `0x0000_0000_7FC0_0000`／`fo` 用 `DP_CANONICAL_NAN`，§4 现行条文）——quiet 与 signaling 的差别**只**体现在 NV：quiet（`*qcmp`）仅 sNaN 置 NV，signaling（`*scmp`）只要无序（含 qNaN）即置 NV。**不再传播输入 NaN 的 payload**。
② **两者皆为 0 ⇒ 0**（`(a | b)` 的指数+尾数全 0 判定）：`+0 = −0`（IEEE 754-2019 §5.10 / §4「= ⇒ 0」），**必须先于**「异号 ⇒ 负者小」分支，否则 `(±0, ∓0)` 会被判成 ±1（返工 §I1 的原 bug）。
③ **有序**：异号（且不同时为零）⇒ 负者小；同负 ⇒ 量值大者小；同非负 ⇒ 量值小者小。结果写整 64 位：`−1 ⇒ 0xFFFF_FFFF_FFFF_FFFF`、`0`、`+1 ⇒ 1`（与 `SimRISC-08` 的 `cmp` 高位规则一致）。
本族**只可能置 NV**（不置 DZ/OF/UF/NX），不涉舍入 ⇒ 不解析 `rf0`。

**§5 已写 2 条（分类）**：`ftcls`/`focls` = 起始 `rdHB == 0` ⇒ ILLI（范围自起始升序 ⇒ 含 `rd0`） + `immu6 == 0` ⇒ ILLI + 「目的/源起始 + immu6 > 64」⇒ ILLI（`Bits<7>` 防溢出） + `for (k = 0; k < immu6; k++)` 逐对分类。分类结果 = 10 位 one-hot **零扩展**写满 64 位（`[63..10]` 全 0，散文明写），位序 = 表：`bit0` sNaN / `bit1` qNaN / `bit2` −Inf / `bit3` −normal / `bit4` −subnormal / `bit5` −0 / `bit6` +0 / `bit7` +subnormal / `bit8` +normal / `bit9` +Inf；十条 `else-if` 链穷尽（`else` 落 `+Inf`）。源视图：`ftcls` 取 `rf[rfHC+k]` 的**低 32 位**（ft）、`focls` 取整 64 位（fo）；目的 `rd`、源 `rf` 分属不同寄存器组 ⇒ 结构性无重叠，按序号递增先读后写。

## 审阅记录

### 第 1 轮 reviewer 验收（2026-11-19）

**重跑记录（reviewer 亲自执行；命令均在本 worktree / 合并态副本内）**
- 合并态：`git merge-tree --write-tree master HEAD` rc=0 无冲突；在「本分支 + 当前 master」克隆副本上 `python3 idl/render.py --check` → `idl-render: PASS（源 operation=263 条 / 落点 12 册 / 标记块 263 个，逐字节一致）` rc=0；`make check-idl-sync` rc=0；`make check-manifests-guard` → `结果: PASS（双向文件/子目录集合一致、sha256 全符）` rc=0；`make check-fp-contract` → `check-fp-contract: PASS` rc=0。
- 改动集：`git diff master...HEAD --stat` = 本任务书 / `idl/SimRISC-07.idl` / `idl/.manifests.toml`（登记本册，门控双向集合必需）/ `spec/SimRISC-07-浮点运算.md` / `spec/.manifests.toml`（仅本册 sha256），与完成区「修改文件」一致（两态 diff 另含 master 近 6 个提交的文件，非本任务改动）。
- 覆盖：自 `contracts/opcodes.yaml` 按 `spec_cite: SimRISC-07` 现场派生 50 个 id，与 `.idl` 的 50 个 `# id:` 双向 `diff` rc=0，零缺零多、两侧无重复。
- 散文：剥 50 对标记块后与 merge-base **逐字节相同**（两种剥法均 IDENTICAL）；`git diff master -- spec/SimRISC-07` 删除行 = **0**；`spec/.manifests.toml` sha256 与现场 `sha256sum` 相符。
- 独立注入 3 路（**均不在其 34 路内**）：A `ftqcmp` 无序结果 canonical → sNaN；B `ftmin` 异号分支取值互换；C `ftcls` 源去掉 `[31:0]` ⇒ 各 **rc=1** 并报出对应 `[FAIL]`；`cp` 还原后 md5 与注入前相同、回 **rc=0**。
- 独立 oracle（自写参考 + 自行逐句转写 4 条 operation，**未用其 6 个 oracle**）：`ftqcmp`/`ftscmp`/`foqcmp`/`foscmp` 各 **1250 对**（±0/±Inf/qNaN/sNaN/次正规/平局/随机），值+标志逐位 ⇒ **每条 2 处不一致、共 8 处**，全部是 `(±0, ∓0)`（参考 0、模型 ±1），其余 4992 对一致。
- 定点执行（自写 idlc 求值驱动）：`ft_muladd(0x3f800001,0x3f7ffffe,0xbf800000,AddC,RNE)` = `0xA880_0000`（规范反例命中，先乘后加为 `+0`）；`ft_sqrt(4.0)`=`0x40000000`、`ft_rem(5,2)`=`0x3f800000`、`ft_add(1,−1,RDN)`=`0x80000000` 均正确。
- 语义抽查 ≥6 条：§4 比较（见 finding 1）、§5 `ftcls` 源取 ft 低 32 位 + 十类 one-hot 零扩展写满 64 位（谓词链穷尽、`else`=+Inf）✓、§2.4 `ftmin/ftmax` 的 `−0 < +0` 与单 NaN 返数字 ✓、§2.5 单次舍入反例 ✓、§2.3 NX 排除 NaN ✓、§1.4 三条 ILLI 为首条语句 ✓。

**阻断 finding**
1. **四条比较指令对 `(±0, ∓0)` 返回 ±1 而非 0**（「异号 ⇒ 负者小」分支对零生效）。违反 `contract-fp.md §8`「`=` → 0」、`SimRISC-02 §450`「`0` = 等于」与 IEEE 754-2019 §5.10；operation 注释自称「IEEE §5.10 … 含 `−0 < +0`」与所引条款相反（§5.10 中 `compareQuietLess(−0,+0)` = false）。⇒ 改四条异号分支，使两操作数均为零（含异号）时返回 0。
2. **`oracle_b5.py` 的 ±0 判据不可达 FAIL**：定值表 ±0 行只与**参考侧**互证；模型↔参考的随机对只取 `randrange(1, top)` ⇒ ±0/±Inf/次正规从不进入模型比对 ⇒ finding 1 抓不到。⇒ 补「模型↔参考」的 ±0/±Inf/次正规对并纳入注入。

**披露**：3. idlc 表达式求值器不可靠（void 函数 `value_error`、`ft_div` 恒 `ZeroDivisionError`、同表达式重复调用结果漂移）⇒ 我**未**完成 6 个算术族各 ≥200 例的独立逐位比对，该部分**采信 engineer 的 oracle**（只做定点执行 + 阅读核对）。4. `ftscmp`/`foscmp` 两操作数皆 qNaN 时返回 qNaN 位型，与 §4「结果为 sNaN」字面不符（并入待裁定 6）。

**三个待裁定独立判定（不改散文）**：待裁定 2 **属实**（册首只写「ft 只写低 32 位」，§1.1/§1.3 未写 `rd` 的 64 位填法；建议补「`it` 符号扩展 / `ut` 零扩展」）；待裁定 5 **属实**（§2.3 表与共同规则两处均写「结果 ≠ 输入时置 NX」、无 NaN 例外，实现按 IEEE §5.9 排除 NaN 更正确；建议改「且输入非 NaN」）；待裁定 6 **属实**（§1.3 例外条与 §4 只写「保持 signaling NaN 位型、符号位 0」，未定两操作数皆 NaN 取谁；建议写死「优先 `rfHC`」或「优先 sNaN」并澄清全 qNaN 措辞）。

**约束核验**：独立 worktree ✓；未改主工作树 ✓；未提交 git ✓；未改版本号 ✓；未动其它册与 `idl/README.md` ✓；验收前后 `git status --porcelain -uall` 快照一致且干净 ✓；术语 `bank` 一律作「寄存器组」、无误译 ✓；完成区 ≤30 行 ✓。
**脚本结论**：`bash 运行期证据目录内的 run.sh` → `PASS=91 FAIL=0`、`ALL GREEN`、`RUNSH_EXIT=0`。
**判决：Needs Revision**（finding 1 = 语义/合约不一致；finding 2 = 验证脚本不可达 FAIL）。

### 第 2 轮 reviewer 验收（2026-11-19，小改返工）

**重跑记录（reviewer 亲自执行，提交态 HEAD=`6abbf48a`）**
- 四门控：`python3 idl/render.py --check` → `idl-render: PASS（源 operation=263 条 / 落点 12 册 / 标记块 263 个，逐字节一致）` rc=0；`make check-idl-sync` rc=0；`make check-manifests-guard` → `结果: PASS（双向文件/子目录集合一致、sha256 全符）` rc=0；`make check-fp-contract` → `check-fp-contract: PASS` rc=0。
- 覆盖：我自 `contracts/opcodes.yaml` 按 `spec_cite: SimRISC-07` 现场派生 50 个 id 与 `.idl` 50 个 `# id:` 比对 `相同: True`；覆盖率脚本 `--batch 5` → `累计: 50/50（batch 5）` rc=0。
- 散文：剥块后与固定基线 `783b6a9e` **逐字节相同**（465 行 == 465 行）；`git diff 783b6a9e HEAD -- spec/SimRISC-07-浮点运算.md` 删除行 = **0**；`spec/.manifests.toml` 仅本册 sha256。

**三项返工逐条独立验**
1. **`(±0,∓0) ⇒ 0`**：四条比较的 `else if` 链序 = NaN → **两者量值全 0 ⇒ `res = 64'd0`** → 异号 → 同号量值；掩码 ft `32'h7FFF_FFFF`、fo `64'h7FFF_FFFF_FFFF_FFFF`，NaN 判定在前（NaN 量值非 0，不会误入）。我自建 8 组（`(+0,−0)`/`(−0,+0)` × ft/fo × quiet/signaling）**全部 `→ 0x0`**；普通异号/同号断言（`−1.0 vs +2.0`、`+2.0 vs −1.0`、`+2.0 vs +1.0`、`−1.0 vs −1.0` × 4 条）**符号全对**；自写参考全池两两扫描 **16384 对 0 差**。
2. **`scmp` 改 canonical**：`grep -c nanpat idl/SimRISC-07.idl` = **0**；`ftscmp` ⇒ `64'h0000_0000_7FC0_0000`、`foscmp` ⇒ `DP_CANONICAL_NAN`；`NV` 仍「signaling 无序即置 / quiet 仅 sNaN」——与 spec §4「四种比较一律 canonical quiet NaN」、`SimRISC-00 §420`（授权变更、例外条已删）一致。
3. **oracle 假绿口子**：证据脚本的 oracle 把 `±0/±Inf/±min_subnormal/max_finite/±min_normal` 放进 specials 并**两两全组合进 model↔ref 比对**（1696 例比较）；`--no-specials` → `池覆盖…缺 [±0, ±Inf, ±min_subnormal, max_finite, ±min_normal] ⇒ 判据不可达` **rc=1**（我独立跑的）；`--inject`（模拟返工前无 ±0 分支）→ **8 处不一致**。
4. **散文基线 §5b**：`BASE=${M15_IDL_007_BASE:-783b6a9ef0bda1cba483c0fe87545596a4780153}`（**字面固定 commit**，非 `HEAD`/`HEAD^`/`git log -1`）并显式 `git rev-parse --verify`；我自证守卫 `M15_IDL_007_BASE=HEAD bash 运行期证据目录内的 run.sh` → `基线 = HEAD（禁止；散文判据会退化）` **rc=1**；**提交态**跑 run.sh 仍绿 ⇒ 满足 §5b「提交后仍须回绿」。

**我的独立注入**：临时副本里**删掉四条比较的「±0 相等」分支**（删 4 段、`grep -c "7FFF_FFFF) == 0"` = 0）⇒ 语义检查器 **rc=1**、4 条 `[FAIL] ±0 相等（先于异号分支）`；`cp` 还原后 md5 `9fce29f8…` == 注入前、回 **rc=0**（507 `[ok]` / 0 `[FAIL]`）。

**范围外·需架构师处置（不改本任务文件）**：`.tao/contracts/contract-fp.md §8` 仍写「Signaling Compare 返回 sNaN（符号位为 0、payload 不限）」，与 spec §4/§1.3、`SimRISC-00 §420` 的 canonical 口径**冲突**（授权变更 `a6f11e23` 漏同步契约；`check-fp-contract` 不校验该措辞）⇒ 请契约/规格任务补一句。

**文档级小错（记账、不阻断，architect 收尾时改）**：① 完成区写「散文基线 = 固定 commit `6d510edf`」，脚本实际是 `783b6a9e`；② 完成区写「特殊值两两组合 12×12×2」，现场是 **10×10×2**（`specials` 10 条）；③ 证据脚本内散文段标题仍写「基线 = merge-base $BASE」。

**约束核验**：独立 worktree ✓；未改主工作树 ✓；未提交 git ✓；未改版本号 ✓；未动其它册与 `idl/README.md` ✓；`git status --porcelain -uall` 干净 ✓；术语无误译 ✓；`**状态**` = `待验收` ✓。
**脚本结论**：`bash 运行期证据目录内的 run.sh` → `PASS=93 FAIL=0`、`ALL GREEN`、`RUNSH_EXIT=0`。
**判决：Accepted**（三项返工成立 + 我的注入能红 + 提交态全绿；两处文档级小错与一处范围外契约漂移已单列）。

### 第 1 轮 engineer 自审（2026-11-19）

**方式**：自主逐行审查 `idl/SimRISC-07.idl`（3 条 operation）、spec 标记插入、证据脚本与 oracle。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 次正规/整数尾数若写 `frac << sh`，非加宽移位只保留 23 位 ⇒ 高位静默丢失且 idlc 不报错 | ✅确认已防（实现即用「先拼接加宽再移」） | `Bits<64> wide = {41'd0, frac}` / `{32'd0, mag}` 后再 `<< sh`；取 `[51:0]` | `type_solve.rb`：`{41'd0, frac}=64`、`wide << sh=64`；反例 `frac << sh=64` rc=1；oracle 0 差 |
| F2 `it2fo` 用 `-v` 表示量值时 `v = 0x8000_0000`（−2^31）在 32 位下不可表示 | ✅确认已防（用补码取负） | `mag = (~v) + 32'd1`（0x8000_0000 自映射） | oracle 覆盖 −2^31 与全部 ±2^k 边界，0 差 |
| F3 `check_semantics.py` 负向断言被注释文字「不读 rf0[33:32]」误伤 ⇒ 假 FAIL | ✅已修 | 负向断言只匹配去注释后的代码行 | 真实树 rc=0；注入④⑤⑥⑦ 各 rc=1 |
| F4 注入② 删「待裁定」登记时先命中了上面的指令清单同名 id ⇒ 判据假绿 | ✅已修 | 注入只作用于 `## 待裁定` 之后 | 注入② rc=1；还原 rc=0 |
| F5 注入⑪「参数个数错」缺 `immu6` 解码变量 ⇒ 失败原因是缺符号、不是元数（假 FAIL 路径） | ✅已修 | 补齐 `rfHB/rfHC/rdHC/immu6` 四个变量 | 失败信息 `Wrong number of arguments to 'raise' … Expecting 3, got 4`，rc=1 |
| F6 `oracle.py` 的 `s32` 对负数误加 2^32 ⇒ 6 处假不一致 | ✅已修 | 先 `& 0xFFFF_FFFF` 再判符号位 | oracle PASS（200000/100069/100037 向量 0 差） |
| F7 §1.1 的 15 条是否要「先写合法性、结果留空」 | ❌不修（按规则记待裁定，不写静默桩） | 一条都不写；覆盖脚本机械核对「未写 ⇒ 必须登记待裁定」 | `cover.py` 注入② rc=1；待裁定 1 列出 15 个 id |
| F8 已写 3 条缺 §1.4 的 `rfhb != rf0 ⇒ ILLI` | ⏸延后（批 2 补） | 无（派单批次 = §1.1+§1.2+§1.3；§1.4 属批 2） | 完成区「遗留问题」+ 本节 F8 |

**判决**：无未修 finding ⇒ 批 1 可交付（状态按派单要求保持 `待开始`，待批 2–5 续做）。

### 第 2 轮 engineer 自审（2026-11-19，批 1 剩余 15 条）

**方式**：自主逐行审查 18 条 operation（新增 15 条）+ 用 **独立 Fraction 参考**的 `oracle_b1b.py` 交叉验证（每类 ≥240 例，共 4900 例）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| G1（oracle 发现）`fo2it`/`fo2ut` 原用 `sig53 << 11` 对齐：\|值\| 大时 `sig + 0x800` 溢出 64 位 ⇒ `roundToI32` 误判成 0/NX 而不是 NV | ✅已修 | 改用**原始 53 位尾数** + 移位量 `1063 − exp`；`$signed(sd) <= 0`（值 ≥ 2^40）直接 NV + 饱和 | `oracle_b1b` 340 例/方向 0 差；注入⑫ rc=1 |
| G2（oracle 发现）`fo2io`/`fo2uo` 原用 `1086 − exp` 且 `sd < 0` 一律判溢出 ⇒ 把 2^63…2^64−1 的合法值误判 | ✅已修 | 改 `1075 − exp`；`sd < 0` 时左移 `−sd` 位，`> 11` 位才判 ≥ 2^64 | oracle 覆盖 2^63/2^64 边界 0 差 |
| G3（oracle 自身）参考侧三处错：RNA 负平局方向、量值舍入未按符号翻转 RUP/RDN、`−0` 丢符号 | ✅已修（参考侧） | `round_frac_to_int` 的 RNA 分正负；`round_to_quantum` 对负值交换 RUP/RDN；`f64_to_f32_ref` 显式处理 ±0 | 修后 §1.2 三条 oracle 仍 PASS（40 万例）、§1.1 全绿 |
| G4（oracle 发现）`io2ft`/`uo2ft` 的 `d = sd + 7` 是 `Bits<8>`，`0x9C − d` 必须符号扩展 | ✅确认已防 | `{{8{d[7]}}, d}`；模型侧同类错误一并修 | 大 \|v\| 用例（2^40…2^63）0 差 |
| G5 `check-spec-purity` 判红：渲染块注释写了「用户裁定」 | ✅已修 | 改为纯语义措辞（spec 块内不得出现决策记录用语） | `make check-spec-purity` rc=0 |
| G6 我的一次重排脚本把 `idl/SimRISC-07.idl` 正文写丢（只留 `# id:` 行） | ✅已修（从 spec 渲染块逐块恢复） | 按 spec 的 18 个块重建 `.idl`；`render.py` 报「更新 0 册」⇒ 与 spec 逐字节一致 | `render.py --check` PASS |
| G7 `check_semantics` 的「不自行 raise」对 §1.2 三条不成立（SBZ 正当 raise ILLI） | ✅已修 | 按 `EXACT` 集合豁免，改为「只有 SBZ 一处 raise」 | 真实树 rc=0 |
| G8 证据脚本的库装配漏 `idl/lib/*.idl` ⇒ `rm_to_mode` 找不到（3/18） | ✅已修 | 装配 = §4 代码块 + `idl/lib/*.idl`（`%version` 只留首行） | typecheck 18/18 |
| G9 15 条缺 §1.4 的 `dst_rd0`/`dst_rf0` 判定 | ⏸延后（批 2） | 无（派单批次 = §1.1+§1.2+§1.3） | 完成区「遗留问题」 |

**判决**：无未修 finding ⇒ 批 1（18/18）可交付；状态按派单要求保持 `待开始`。

### 第 3 轮 engineer 自审（2026-11-19，批 2：§1.4 + §2.1 ft 侧 + §2.2 ftroot）

**方式**：自主逐行审查新增 6 条 + 18 条合法性改动、spec 标记插入、证据脚本与 `oracle_b2.py`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| H1 插入 §2.2 标记时脚本 off-by-one，把 `### 2.3 取整（roundToIntegral）` 标题行**删掉** ⇒ `check-spec-numbering`/`check-spec-refs`/`check-spec-cite-targets` 三红 | ✅已修 | 按 merge-base 原文恢复该标题；`git diff \| grep '^-'` 现为 0 行删除 | 三门控 rc=0；`prose_unchanged` PASS |
| H2 `ftroot` 块前多一个空行 ⇒ `prose_unchanged`（删块+1 空行 规则）判红 | ✅已修 | 删多余空行，恢复「块前恰一空行」约定 | `prose_unchanged.py` PASS（新增标记 48 行 == 期望） |
| H3 `ftsclb` 初稿用 `roundPackToF32` + 尾数 `<<7`，且次正规指数基写成 `n−60` —— 手算 `1.0×2^n`、`3.0×2^n` 两例即错（库的 `normRoundPack` 期望 **24 位**有效数） | ✅已修 | 改用 `softfloat_normRoundPackToF32` + 24 位有效数：正规 `exp+n+6`、次正规 `n+7`，指数先饱和到 ±2000 | `oracle_b2` ftsclb 936 例 0 差；注入⑰ rc=1 |
| H4 `oracle_b2` 参考侧两处错：`−0/1.0` 丢符号、`Inf−Inf` 判据拿原符号比（应比翻号后的次操作数） | ✅已修（参考侧） | `ref_binop` 的 div 补 `va == 0` 分支；add/sub 先算 `sr`（减法翻号）再判 NV | 定值表 70 行 + 936 例全 PASS |
| H5 类型检查缺 `rfHD`/`rdHD` 解码变量 ⇒ 19/24（假 FAIL 路径） | ✅已修 | `VARS` 补齐 7 个解码变量 | typecheck 24/24 |
| H6 8 条 fo 侧（+`ftrem`）按「位级又过长」不写 | ⏸延后（待裁定 4） | 一条不写（不产静默桩）；覆盖脚本机械核对「未写 ⇒ 必须登记待裁定」 | `cover.py --batch 2` 判「8 条全部已登记」PASS |
| H7 18 条合法性放在**首条语句**（先于源读/舍入解析） | ✅确认正确 | 与 `SimRISC-08`/`SimRISC-10` 的 `dst_*` 写法一致 | `check_semantics` 的「首条语句 = dst 判定」断言 PASS |

**判决**：无未修 finding ⇒ 批 2（累计 24/32）可交付；状态按派单要求保持 `待开始`。

### 第 4 轮 engineer 自审（2026-11-19，批 3：§2.3 取整 + §2.4 最小最大）

**方式**：自主逐行审查新增 6 条、spec 标记插入、`oracle_b3.py`（定值表 39 行 + 1760 例）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| I1 `0x20` 档的 NX 若按「结果 ≠ 输入」字面判，qNaN 的 canonical 化会误置 NX（IEEE 754-2019 §5.9：NaN 属 quiet 计算、不置 inexact） | ✅已修 | `if ((immu6 == 6'h20) && (r != a) && (!is_*_nan?(a)))`；散文未改（记「待裁定 5」） | `oracle_b3` 720+720 例 0 差；注入⑳ rc=1 |
| I2 `ftmin`/`fomin` 的「同为负 ⇒ 量值大者更小」方向写反过一次（模型侧先反，oracle 抓出） | ✅已修 | 按 `returnMag` 比较取大；`max` 取小 | `oracle_b3` minmax 320 例 0 差；`--inject` 12 处不一致 |
| I3 `oracle_b3` 参考侧 `_less` 把**带符号值**当量值比（负数序反了）、且未处理 Inf 的 `None` 值 | ✅已修（参考侧） | 新增 `_mag_cmp`（Inf 单独定序）+ 取 `abs(va)` | 定值表 39 行 + 1760 例全 PASS |
| I4 定值表里 `trunc(−1.5)` 曾写成占位表达式（`ONE5N & ~0`） | ✅已修 | 改成显式 `0xBF80_0000`（= −1） | 表-参考互证 PASS |
| I5 `check_semantics` 把「解析舍入档」强加给最小最大族（本族不涉舍入） | ✅已修 | 新增 `NO_MODE` 豁免，并反向断言「不含 `rm_to_mode`」 | 真实树 rc=0 |
| I6 批 2 的 8 条（`ftrem`/`fo*`）在 016 落地后**不再缺库**，但本轮批次不含 ⇒ 未写 | ⏸延后（待派单，非缺口） | 无（保持范围） | `cover.py --batch 3` 判「8 条已登记」PASS；「待裁定 4」改写 |
| I7 §2.3 的 `|x| ≥ 2^p` 原样返回、`±0` 符号保留由库保证（不经整型转换） | ✅确认正确 | 无（库里已按 `exp >= 150/1075` 早退） | `oracle_b3` 覆盖 `MAXF`/`NMAXF`/`±0` 边界 |
| I8 证据脚本的临时目录固定为 `evidence-tmp`：与上一次被超时中断的残留实例并发时互相 `rm -rf` ⇒ `lib.idl` 被截断、`ops/` 消失（6 项假 FAIL） | ✅已修 | 临时目录改为按 PID 独立（`evidence-tmp-$$`），并在运行前清残留 | 重跑 `PASS=79 FAIL=0` |

**判决**：无未修 finding ⇒ 批 3（累计 30/38 本批口径、30/50 全册）可交付；状态按派单要求保持 `待开始`。

### 第 5 轮 engineer 自审（2026-11-19，批 4：§2.1 补齐 8 条 + §2.5 + §3）

**方式**：自主逐行审查新增 14 条、`.idl` 重排、spec 标记插入、`oracle_b4.py`（27 行定值表 + 2267 例）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| J1 重排 `.idl` 时用「id 行 + 其后文本」拼接，先写成 `\n\n` 造成每块多一空行；且验证脚本比较的是"构造后的块"，掩盖了它 | ✅已修 | 块正文改为 `id 行 + 原 chunk`，写完再从 `git show HEAD:` 逐块对账 30 条老块**逐字节不变** | 重排后 `git diff --stat` = 纯增 188 行；`render --check` PASS |
| J2 §2.1 的 12 对标记替换后，最后一对后面多一空行 ⇒ `prose_unchanged` 判红 | ✅已修 | 删掉多余空行（保持「块后恰一空行」） | `prose_unchanged` PASS（新增 88 行 == 期望）；spec 纯增 |
| J3 `cover.py` 的 §2.5 无 ```simrisc 块（只有行内汇编形式）⇒ 派生失败 | ✅已修 | 新增回退口径：扫「反引号内含 `<助记符> <操作数>` 且助记符在本册 opcodes 里」 | `cover.py --batch 4`：§2.5 2 条、§3 4 条、累计 44/44 PASS |
| J4 `check_semantics` 把 `rrrr` 的目的当成 `rfHB`（实际在 `rfHA`） | ✅已修 | 新增 `RFA_DST` 集合与「首条语句 = `rfHA` 判定」断言 | 44 条全 PASS；注入㉔ rc=1 |
| J5 余数/符号位操作被误套「必须解析舍入档」断言（二者都不涉舍入） | ✅已修 | 加进 `NO_MODE`，反向断言「不含 `rm_to_mode`」 | 真实树 PASS |
| J6 `oracle_b4` 的 fma 注入只比随机三元组 ⇒ 差异率 0（假绿风险） | ✅已修 | 注入路径另在**规范反例**上比「先舍入积 vs 单次舍入」 | `--inject` 报 49 例差异（rc=0 且非空） |
| J7 `oracle_b4` 的注入分支对非有限积 `decode` 返回 `None` 会崩 | ✅已修 | 只在积为有限值时替换 | 正常/注入两路均 PASS |
| J8 §4/§5 的 6 条（比较/分类）未写 | ⏸延后（批 5 范围） | 无 | `cover.py --batch 4` 累计 44/44；待裁定 4 记明剩余 6 条 |

**判决**：无未修 finding ⇒ 批 4（44/50）可交付；状态按派单要求保持 `待开始`。

### 第 6 轮 engineer 自审（2026-11-19，批 5：§4 比较 + §5 分类 ⇒ 全册 50/50）

**方式**：自主逐行审查新增 6 条、spec 标记插入、`oracle_b5.py`（22 行定值表 + 1736 例）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| K1 quiet compare 对 sNaN 的**结果**易被误写成「保持 sNaN 位型」——散文明确 quiet compare 的无序结果一律 **canonical qNaN**（signaling 才是保持位型） | ✅确认已按散文实现 | `ftqcmp`/`foqcmp` 无序分支统一写 canonical；只有 `ftscmp`/`foscmp` 才 `nanpat & ~signbit` | `oracle_b5` 定值表 2 行（qNaN/sNaN × quiet）+ 1296 例 0 差 |
| K2 signaling compare 在**只含 qNaN** 时也无序 ⇒ 必须置 NV；若照抄 quiet 的「仅 sNaN」会漏 NV | ✅已修（实现按散文「只要无序即 NV」） | `ftscmp`/`foscmp` 的 NaN 分支无条件 `set_fp_flag(NV)` | 定值表 `(qNaN, 1.0, signaling) ⇒ {NV}`；注入㉕ rc=1 |
| K3 `ftcls` 的源若用整 64 位判 ft 类会错（高半是脏数据） | ✅已修（实现即取低 32 位） | `Bits<32> v = rf[rfHC + k][31:0];` | 注入㉗ rc=1；oracle cls 440 例 0 差 |
| K4 分类块操作的三条 ILLI（dst 起始 0 / `immu6 = 0` / 起始+immu6 > 64）漏一条就少一类非法；`rdHB + immu6` 在 6 位下会回绕 ⇒ 必须 7 位 | ✅已修（按 §5 三条全写 + `Bits<7>` 宽算） | `Bits<7> dst_end = rdHB \`+ immu6;` 等 | 注入㉖ rc=1；`check_semantics` 断言 raise 次数 = 3（dst + zero + range） |
| K5 「+0 与 −0 同号分支」在比较里必须落到「相等 ⇒ 0」：`−0`/`+0` 符号不同 ⇒ 走「异号 ⇒ 负者小」，于是 `+0 < −0` 判 false、`−0 < +0` 判 true ⇒ 两者比较为 0 ✓ | ✅确认正确 | 无（用符号优先 + 量值比较） | 定值表 `(±0, ±0) ⇒ 0`；oracle 1296 例 0 差 |
| K6 本轮 6 条完成后覆盖率与 oracle 口径要「零缺」 | ✅已修（无缺口） | `cover.py --batch 5` 50/50；`check_semantics` 50 条 | 见完成区 |

**判决**：无未修 finding ⇒ **全册 50/50 可交付**；按派单要求状态改为 `待验收`。

### 第 7 轮 engineer 自审（2026-11-19，**reviewer Needs Revision 返工**：`(±0,∓0)` + scmp canonical）

**来源**：reviewer 独立 oracle 实测两条阻断 + 一处规范变更（`spec §4` 已由用户授权改 canonical，含原 `m15-idl-018` 并入）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1（阻断）四条比较在 `(±0, ∓0)` 返回 ±1，应返回 **0**（IEEE 754-2019 §5.10：`+0 = −0`；`contract-fp §8`；`SimRISC-02`） | ✅已修 | 四条均在「异号 ⇒ 负者小」**之前**加「`(a \| b)` 的量值全 0 ⇒ 结果 0」分支（ft 用 `0x7FFF_FFFF`、fo 用 `0x7FFF_FFFF_FFFF_FFFF` 掩码；用库谓词写会多两次调用，掩码更直观），并把原注释里「含 −0 < +0」的错述删掉 | 定值表 `(±0,∓0)` 正反各 3 行；oracle 特值对 1696 例 0 差；注入㉘（删该分支）rc=1；`--inject`（模型去掉该分支）报 8 处不一致 |
| R2（阻断）`scmp` 无序结果应是 **canonical quiet NaN**（§4 已改），原实现传播输入 NaN 位型 | ✅已修 | `ftscmp`：`res = 64'h0000_0000_7FC0_0000;`；`foscmp`：`res = DP_CANONICAL_NAN;`；删掉 `nanpat` 与相关注释 | 定值表 4 行（qNaN/sNaN/负 sNaN × signaling）全 canonical；注入㉙（改回 sNaN 位型）rc=1 |
| R3（判据假绿）`oracle_b5` 的随机对只取 `randrange(1, top)` ⇒ ±0/±Inf/次正规不进比对，故 R1 抓不到 | ✅已修 | 随机池显式加入 `±0`/`±Inf`/`±min_subnormal`/`max_finite`/`±min_normal`，两两全组合 × 两种 compare 语义；并加**池覆盖断言**（缺特殊值即红）与 `--no-specials` 路径 | `--no-specials` rc=1（缺 5 类）；正常 1696 例 0 差 |
| R4 返工涉及的证据脚本同步（`check_semantics` 的旧 `nanpat` 断言、oracle 的 sNaN 期望、`spec` sha256） | ✅已修 | `check_semantics`：`scmp` 断言改 canonical、四条都加「±0 相等」断言；`oracle_b5` 参考/模型改 canonical；`render.py` 重渲染后重算本册 sha256 | `check_semantics` 50 条 PASS；`check-manifests-guard` rc=0 |
| R5 散文基线必须锚**固定 commit**、禁 `HEAD` | ✅已修 | `run.sh` 的 `BASE` 固定为 `6d510edf`（含 §4 canonical 的 master tip，即本次返工的分叉点），并断言「BASE ≠ HEAD」；散文判据改用该显式基线 | `prose_unchanged` 三路（显式基线 + 两反例）全 PASS |
| R6 注入㉕（把 `ftscmp` 改回 quiet）依赖的旧文本已不存在 | ✅已删（由注入㉙ 覆盖） | 删 ㉕，保留 ㉖㉗ 与新增 ㉘㉙ | 93 项全 PASS |
| R7 `m15-idl-018` 并入本任务、其任务书/台账已撤 | ✅已同步 | 待裁定 6 标注「已消解 + 018 已并入」；本轮返工覆盖其全部改法 | 台账/任务书由主会话收口 |

**判决**：无未修 finding ⇒ **返工完成，全册 50/50 仍成立**；状态回 `待验收`。

## 完成区

**测试结果（返工后，全册）**：证据脚本 `.work/evidence/m15-idl-007/run.sh` → `PASS=93 FAIL=0`、`ALL GREEN`、rc=0。可达 FAIL 注入 **36 路**（覆盖 3 / 散文 3 / 语义 22 / 渲染 2 / idlc 2 / 位宽求解 2 / 清单 2）+ **7 个 oracle 注入跑**（6 个 `--inject` + `oracle_b5 --no-specials`），逐路「注入 ⇒ FAIL → 从真实树重拷 ⇒ 回绿」；真实文件 md5 前后不变。
**本轮返工（reviewer Needs Revision）三项**
1. **`(±0, ∓0)` ⇒ 0**：四条比较在「异号 ⇒ 负者小」之前加「两者量值全 0 ⇒ 结果 0」（ft `0x7FFF_FFFF` / fo `0x7FFF_FFFF_FFFF_FFFF` 掩码），散文出处 IEEE 754-2019 §5.10 / `§4`「= ⇒ 0」/ `contract-fp §8`。
2. **`scmp` 无序结果改 canonical**（`spec §4` 已授权变更为「四种比较一律 canonical」）：`ftscmp` ⇒ `64'h0000_0000_7FC0_0000`、`foscmp` ⇒ `DP_CANONICAL_NAN`，删掉 `nanpat` 位型传播；`NV` 规则不变（quiet 仅 sNaN、signaling 无序即置）。
3. **oracle 假绿口子**：随机池显式加入 `±0`/`±Inf`/`±min_subnormal`/`max_finite`/`±min_normal` 并两两全组合，另加**池覆盖断言**与 `--no-specials` 路径 ⇒ 该判据现在可达（缺特殊值即红）。
**全册 50/50**：§1 18 + §2.1 12 + §2.2 2 + §2.3 2 + §2.4 4 + §2.5 2 + §3 4 + §4 4 + §5 2；覆盖率脚本现场派生 50/50、零缺零多。
**修改文件**：`idl/SimRISC-07.idl`（四条比较修复，共 50 条）、`spec/SimRISC-07-浮点运算.md`（重渲染 §4 的 4 个块）、`spec/.manifests.toml`（重算本册 sha256）、本任务书（待裁定 6 消解、语义抽查 §4 段、第 7 轮自审、完成区）。合并态：`git merge master`（含 `spec §1.3/§4` 的 canonical 变更与 `m15-idl-018` 撤销），冲突仅 `spec/.manifests.toml`（已按重算值解）。
**验收结果**（真实输出，合并态）
- `python3 idl/render.py --check` → `PASS（源 operation=263 条 / 落点 12 册 / 标记块 263 个，逐字节一致）` rc=0；`make check-idl-sync` rc=0
- L1：`check-manifests-guard` / `check-fp-contract` / `check-rule-refs` / `check-config-pins` / `check-spec-purity` / `check-spec-codeblocks` / `check-spec-drift` / `check-asm-prose` / `check-asm-list` / `check-asm-list-drift` / `check-legality-drift` / `check-spec-numbering` / `check-spec-changelog` / `check-spec-refs` / `check-spec-cite-targets` 全 rc=0
- idlc 两段式：库（§4 + `idl/lib/fp.idl`）`compile --root isa` rc=0；**50/50** operation 解析 rc=0、运行期类型检查 **50/50**
- **oracle 总账（独立参考）**：约 **41.2 万例 + 定值表 161 行**（`oracle_b5` 由 22 → 25 行）全 0 差；`oracle_b5` 现 **1696 例比较 + 440 例分类 + 25 行表**，其中特殊值两两组合 12×12×2 全进比对
- 覆盖率（现场派生）：**50/50**
- 散文零改动：基线 = **固定 commit** `6d510edf`（禁 HEAD，脚本内断言 BASE ≠ HEAD），删块后逐字节相同（新增标记 100 行 == 期望）
**新发现/坑**
1. **「异号 ⇒ 负者小」不能替代符号比较**：对普通数成立，但 `+0`/`−0` 异号却相等 ⇒ 必须先有「两者皆 0 ⇒ 0」分支（R1）。
2. **signaling compare 的无序结果口径已变**（canonical，不再传播 payload）⇒ `SimRISC-00` 的例外条同步删除；本册实现与 §4 对齐（R2）。
3. **oracle 的随机池若不显式放特殊值，±0/±Inf/次正规 永远不进比对** ⇒ 「0 差」是假绿；池覆盖要写成**断言**（R3）。
4. 返工的散文基线必须锚**固定 commit**：merge 后 `merge-base` 会漂移，取 `merge-base HEAD master` 会把 master 的 spec 变更算成「散文被改」。
**遗留问题**
1. **「待裁定 2」**：`ft2it`/`ft2ut`/`fo2it`/`fo2ut` 的 32 位结果写宽（`it`⇒符号扩展、`ut`⇒零扩展）——散文未写，等用户统一裁。
2. **「待裁定 5」**：§2.3「结果 ≠ 输入 ⇒ NX」对 qNaN 的措辞（实现按 IEEE 排除 NaN）——等用户统一裁。
3. 「待裁定 6」**已消解**（canonical 不传播 payload；原 `m15-idl-018` 已并入本任务）。
4. `ftsclb` 仍是批 2 的临时写法（指数加 `rdHD` + `normRoundPackF32`）；如后续 `ft_scale` 入库可改调（oracle 936 例覆盖其语义）。
**落盘自证**：`git rev-parse --show-toplevel` = 本 worktree；`git status -uall` = 本任务书 + `idl/SimRISC-07.idl` + `spec/.manifests.toml` + spec 本册（均属允许集）。
