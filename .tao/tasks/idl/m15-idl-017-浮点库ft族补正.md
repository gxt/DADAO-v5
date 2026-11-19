# m15-idl-017: 浮点库 ft 族补正（tininess 口径 / 两处类型缺陷 / i32·u32→fo）

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-idl-015`（ft 族 53 函数）、`m15-idl-016`（fo 族；批 1 已交付）
**可并行分片**：否（与 `m15-idl-007`/`016` 同改 `idl/lib/fp.idl`，串行）
**预估**：3–4 h
**档位**：中改
**状态**：待开始

## 背景（`m15-idl-016` 批 1 交付时发现的 015 遗留缺陷）

1. **tininess 口径缺陷（语义类）**：`softfloat_roundPackToF32` 的「下溢预判」在边界上错——
   精确值 = `min_normal − ulp/2`、按 RUP/RNE/RNA **恰好舍入到 `min_normal`** 时，它**多置 `UF`**。
   `SimRISC-07 §1.3` 要求 tininess **取舍入之后**（IEEE 754-2019 §7.5）⇒ 该情形**不应置 UF**。
   现状：`fo2ft` 已绕开（用 `no_flag` 原语 + 自判 OF/NX/UF），**新写的 f64 原语已正确**；
   但 **ft 算术仍受影响**（`ft_add`/`ft_sub`/`ft_mul`/`ft_div`/`ft_sqrt`/`ft_muladd`）。
2. **两处类型层缺陷（实现类）**：
   - `ft_sqrt` 用 `S`/`E` 作变量名，首字母大写被 idlc 当**常量** ⇒ `Cannot assign to a const`；
   - `round_ft_to_integral` 里 `Bits<8>` 与 `16'sd150` **不可比较**。
   现状：`check_op.rb` 把它们设为「已知例外」（fail-closed），等于**类型检查被绕过**。
3. **缺 `i32_to_fo` / `ui32_to_fo`**：`it2fo`/`ut2fo`（§1.2 三条精确转换）需要它们，库中暂无。

## 要做

1. **修 tininess**：`softfloat_roundPackToF32`（及其 `_no_flag` 变体）改为「**先舍入、后判 tininess**」，与 f64 侧同口径；**不要**为了省事把 ft 算术一律改走 `no_flag` + 手判（那会让 6 个函数重复逻辑）。
2. **修两处类型缺陷**：`ft_sqrt` 的 `S`/`E` 改名（小写或语义名）；`round_ft_to_integral` 的比较改为同宽（`Bits<8>` ↔ `Bits<8>`，或显式类型求解确认）。
3. **补 `i32_to_fo` / `ui32_to_fo`**（与 `i32_to_ft`/`ui32_to_ft` 同构，精确转换、不置标志），供 `it2fo`/`ut2fo` 使用。
4. **撤掉 `check_op.rb` 的两条「已知例外」**，让 107 个函数体**全部**通过 type_check（撤掉后应 0 例外）。

## 验收（逐条贴真实 rc）

1. `idlc compile --root isa` rc=0；**107 个函数体逐条 `type_check` 全 PASS、例外数 0**（现场统计，不写死）；
2. **tininess 定向用例**：构造「舍入后正好 = `min_normal`」的三档（RUP/RNE/RNA）与「舍入后仍 < `min_normal`」三档，各断言 `UF` 的有无；**修前红、修后绿**（给前后对照）；
3. **oracle 回归**：重跑 ft 算术 5 个函数的 oracle（≥1000 例/函数，`Fraction` + IEEE 规则），失配 0；并确认「修 tininess」**没有**改变正常区间的结果（对比修前修后全量输出，差异只应出现在边界档）；
4. `render.py --check`、`check-idl-sync`、`check-manifests-guard`、`check-fp-contract` rc=0；合并态（`Process-07 §5a`）再跑一次；
5. 可达 FAIL ≥2 路（① 把 tininess 改回预判 ⇒ 定向用例红；② 把 `i32_to_fo` 的舍入档写死 ⇒ oracle 红），`cp`+md5 还原。

## 待裁定

（无。三项缺陷均有明确真源：IEEE 754-2019 §7.5 + `SimRISC-07 §1.3` + idlc 类型系统报错。）

## 完成区

（待填）
