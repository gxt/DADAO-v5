<!-- 人读结论；逐条原始表见运行期目录（未归档）；生成器 = tools/spec/check_fp_ieee_audit.py -->
# M13 FP 语义 IEEE 754-2019 对齐审计（`scope: fp` 全量 66 条）

- **生成时间**：2026-11-13（本地 `Asia/Shanghai`）
- **口径依据**：用户 2026-11-12 裁定「浮点差分一律以 IEEE 754-2019 裁决；`SimRISC` 与各模拟器须据此修订」（`.tao/knowledge/MEMORY.md`「DADAO 反套用清单」末条）
- **数据来源**：`contracts/fp_semantics.yaml`（`scope: fp`，现场统计 66 条）、`spec/SimRISC-07` 附录 A（现场解析 52 行）、三实现已应用补丁树（chipyard `WumingFP.scala`、QEMU `trans_fp.c.inc`/`helper.c`、gem5 `fp_soft.cc`/`b7.cc`）、gem5 B7 探针（`tools/gem5/check_b7.py --vectors`）
- **机器指纹**：主控机 AMD EPYC 7773X；chipyard 补丁集 = `m12-chipyard-027` 后、QEMU = `m13-qemu-008` 后、gem5 = `m13-gem5-009` 后
- **复现**：`python3 tools/spec/check_fp_ieee_audit.py [--raw <运行期路径>]`；一键证据 = 运行期证据脚本（`run.sh`，含注入反例自检）
- **证据强度**：gem5 = 运行期实测（探针逐例打印 FCSR/结果）；QEMU / chipyard = 静态读码（无 FP 三平台运行时差分：`m13-integ-002` 暂未进行）

## 1. 计数口径（现场统计，不写死）

| 口径 | 现场值 | 来源 |
| --- | --- | --- |
| `scope: fp` 指令 | **66** | `contracts/fp_semantics.yaml` ∩ `contracts/opcodes.yaml`（双向一致） |
| 其中 `spec/SimRISC-07` 附录 A 覆盖 | **52** | 附录 A `ASSEMBLY_LIST` 段解析 |
| 其余（RF 存取/块搬移/条件赋值/立即数） | **14** | 66 − 52 |
| 本次审计行数 | **66**（表 A 52 + 表 B 14） | 本册表格 |

「47」在任何机器可读源都复现不出（`ISS-409`），本册不再使用。

## 2. 结论摘要

- **一致 48 行**：IEEE 强制部分三实现同值同标志（NaN 结果的 payload/符号属 IEEE 未规定项，单列 D3，不计入偏离；含 `fo2ft` 四档溢出——原 `ISS-397①` 已由 `m13-spec-002`/`m12-chipyard-025`/`m13-qemu-005`/`m13-gem5-007`/`m13-testcases-011` 关闭）。
- **IEEE 未规定 14 行**：RF 存取/搬移/条件赋值/立即数（架构约定，IEEE 无对应概念）。
- **偏离 4 行**：`ftqcmp`/`foqcmp`（D1）、`ftroot`/`foroot`（D2）。

### D1 gem5 quiet compare 遇 sNaN 不置 `NV`（偏离）

IEEE 754-2019 §5.11（quiet 比较：仅 sNaN 操作数 ⇒ invalid）+ §6.2；用户 2026-11-12 已裁定「quiet 遇 sNaN 置 NV」，`tests/inst/fp/arith.yaml` 四个用例已按此写期望。

- RTL ✅（`WumingCompareRecFN`：`signaling ? unordered : (isSigNaN(a) || isSigNaN(b))`，`m12-chipyard-024`）；QEMU ✅（`FP_CMP_NV_SNAN` → `is_snan(a)||is_snan(b)`，`m13-qemu-004`）；**gem5 ❌**（`b7.cc:runCompare` 只在 signaling 分支置 `NV`）。
- 实测（gem5 B7 探针，两个操作数方向）：`ftqcmp(sNaN,1.0)` 与 `ftqcmp(1.0,sNaN)` ⇒ `FCSR=0x7ff800007fc00000`（低 5 位 `=0`，应为 `0x1`）。
- 动作：**改实现（gem5）+ 改 spec 措辞**（`SimRISC-07 §4` 与 `contract-fp §8` 均无 `NV` 条款 ⇒ 文档缺口与实现缺陷同源）+ **需立册**（建议 `m13-gem5-010`，M13）。

### D2 `rootn(±0, 2)`：三实现给 `−0`，IEEE 给 `+0`（偏离，spec 明文放开）

IEEE 754-2019 §9.2.1：`rootn(±0, n)` 对偶数 `n>0` 为 **`+0`**（与 §5.4.1 的 `squareRoot(−0) = −0` 不同，`spec §2.2` 亦引述了这一点）。三实现均直接落 `squareRoot` ⇒ `foroot(−0,2)=−0`（gem5 实测 `0x8000000000000000`）。`spec §2.2` 写「不做具体要求」但**未标注为有意偏离、未给理由**，按用户规则属待收口项。

- 动作：改 spec 措辞 —— 二选一（**待裁定**）：① 收严为 IEEE `+0`（同时改三实现 + 向量）；② 保留 `−0` 并在 spec 明文写「有意偏离 + 理由」。

### D3（IEEE 未规定，但三实现互不一致）NaN 结果 payload / 符号位

IEEE 754-2019 §6.2.3 只**推荐**传播规则，payload 选择与符号位**不作规定** ⇒ 各实现自由，但三平台必须统一（否则差分恒红）。

- 算术/scaleB：RTL 传**首个** NaN 的 payload、符号位清 0；QEMU 传首个 NaN 的 payload **与符号位**（`float_2nan_prop_ab`）；gem5 一律 canonical qNaN（payload 全零、符号 0）。实测 gem5：`ftadd(0x7FC12345,1.0) = 0x7FC00000`、`ftsclb(0x7FC12345,3) = 0x7FC00000`。
- 格式转换：RTL **清符号位**、并把截断位 OR 进 payload 末位；QEMU / gem5 **保留符号位**、payload 低位移出（若移空则置 quiet 位）。实测 gem5：`fo2ft(0xFFF8000000000123) = 0xFFC00000`（符号保留、payload 丢弃）。
- FMA / rnd / minmax：三方均 canonical（`contract-fp §20/§18/§19` 已写明）⇒ 无分歧。
- 动作：**改 spec 措辞**（`SimRISC-07 §1.4` 与 `contract-fp` 写明「结果 NaN 的 payload 与符号位」取值，建议 canonical qNaN：符号 0、payload 全零）+ **需立册**（三平台对齐，建议 `m13-integ-010`，M13）。

### 文档级发现（F1–F3，不改语义）

- **F1**：`spec/SimRISC-07 §4`（比较族）与 `contract-fp §8` 缺 `NV` 条款（与 D1 同源，随 D1 一并补）。
- **F2**：`contracts/fp_semantics.yaml` 注释写 `cs_rf（5）`，实际 3 条（`cs.n/z/p_rrrr_rf`）；`components/qemu/.../trans_fp.c.inc.patch` 头注释写「60 scope:fp」与「cs_rf (5): cs.n/z/p/eq/ne」，实际 66 / 3。计数注释漂移，随相关任务顺手修。
- **F3**：`WumingFP.scala` 的 `WumingFpScale` 注释把 scaleB 记为「IEEE 754-2019 §9.2」，实为 **§5.3.3**（§9.2 是推荐函数表，`rootn` 在那里）。

## 3. 行为模式（表 A/B 的「行为」列引用）

> 三引擎的族级实现位置：chipyard `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingFP.scala.patch`；QEMU `components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch` + `.../helper.c.patch`；gem5 `components/gem5/patches/src/arch/dadao/exec/{fp_soft.cc,b7.cc}.patch`。

| 模式 | 语义与三实现现状 |
| --- | --- |
| P1 | 四则 `add/sub/mul/div`：三方单次舍入、四档 `rf0`、tininess 取「舍入后」、`§6.3` 零符号、`∞−∞`/`0×∞` ⇒ `NV`+qNaN。值/标志一致；NaN payload/符号见 **D3** |
| P2 | 余数 `rem`：三方 IEEE `remainder`（n 取最近整数、平局取偶、结果恒精确、不置 `NX/OF/UF`、除数为 `±0`/被除 `±Inf` ⇒ `NV`、NaN 优先于该无效条件） |
| P3 | `scaleB`：三方「指数搬移 + 单次舍入」（非先造 `2^n` 再乘）；`|n|` 极大时 clamp 只在不影响结果处生效；NaN 见 **D3** |
| P4 | `rootn(x,2)`：三方=`squareRoot`（`x<0` ⇒ `NV`+qNaN；`±Inf`/`±0` 按 sqrt）；`rootn(−0,2)` 三方 `−0` ⇒ **D2** |
| P5 | 符号注入：三方纯位操作（只改格式符号位）、不置任何标志 |
| P6 | 比较：结果 `1/0/−1`，无序返回 qNaN（quiet）/sNaN（signaling，符号 0）；`NV`：RTL/QEMU quiet 遇 sNaN 置、**gem5 不置** ⇒ **D1** |
| P7 | 分类：三方 10 类位一致（`[9:0]`，其余位清零；位序为本 ISA 约定） |
| P8 | `f2f`：`fo2ft` 窄化按 `§4` 舍入、溢出按方向（RNE/RNA⇒`±Inf`、RTZ⇒`±max`、RUP 正/RDN 负 ⇒ `±Inf`）+`OF|NX`；`ft2fo` 恒精确（不置 `NX/OF/UF`）；**两者 sNaN 入参均置 `NV`**；NaN payload/符号见 **D3** |
| P9 | `f2i`：三方六档方向、越界/NaN/Inf ⇒ 饱和 + `NV`**不置** `NX`、有限 inexact ⇒ `NX` |
| P10 | `i2f`：三方按方向标准舍入 + `NX`；`it2fo`/`ut2fo` 精确（SBZ）恒不置标志 |
| P11 | `rnd`：三方六档一致（仅 `0x20` 置 `NX` 且仅当值改变；静态档不置 `NX`；NaN⇒canonical；`±0` 保号；`|x|≥2^p` 原样返回） |
| P12 | `minmax`：三方 `§9.6` 严格版（`−0<+0`；单 NaN 返回数；双 NaN ⇒ canonical qNaN；仅 sNaN 置 `NV`；不置 `NX/OF/UF`） |
| P13 | `fma`：三方单次舍入、`0×∞` 优先 `NV`、`Inf+(−Inf)` ⇒ `NV`、结果 NaN canonical；溢出按 `§7.4`（QEMU/gem5 已验 `m13-qemu-008`/`m13-gem5-009`；RTL 待 `m12-chipyard-029` 实测确认，不据他平台推定） |
| P14 | RF 写入/搬移/条件赋值（`cs.*-rf`、`rd2rf`/`rf2rd`、`set.w-rf`）：架构约定，IEEE 无对应 |
| P15 | RF 存取（`ld/st/ldm/stm`）：架构约定；`rf0` 作目的为测试机约定（`ld.t` 写低 32 保高 32、`ld.o` 走写掩码），与 `m13-qemu-007` 同源 |
| P16 | 复制类（`ft2ft`/`fo2fo`）：纯 64 位二进制搬移 = `§5.5.1 copy`（不改符号、不置异常；与「同格式 convertFormat 会 canonical 化」不同） |

## 4. 表 A：`spec/SimRISC-07` 附录 A 的 52 行（按附录 A 顺序）

| 指令 | IEEE 条文（章节 + 结论） | 行为 | 结论 | 动作 | 影响面 |
| --- | --- | --- | --- | --- | --- |
| `fo2fo` | §5.5.1 copy：只搬位、不置异常 | P16 | 一致 | 不改 | 三平台·`tests/inst/fp` |
| `fo2ft` | §5.4.2 窄化按 §4 舍入；§7.4 溢出按方向；§7.5 tiny∧inexact | P8 | 一致 | 不改（NaN 见 D3） | 三平台·`convert.yaml`；`ISS-397①` 已修 |
| `fo2io` | §5.8 float→int：按方向、越界 invalid | P9 | 一致 | 不改 | 三平台·`convert.yaml` |
| `fo2it` | §5.8 float→int：按方向、越界 invalid | P9 | 一致 | 不改 | 三平台·`convert.yaml` |
| `fo2uo` | §5.8 float→uint：按方向、负值 invalid | P9 | 一致 | 不改 | 三平台·`convert.yaml` |
| `fo2ut` | §5.8 float→uint：按方向、负值 invalid | P9 | 一致 | 不改 | 三平台·`convert.yaml` |
| `foadd` | §5.4.1 加法 + §7.4/§7.5 | P1 | 一致 | 不改（NaN 见 D3） | 三平台·`arith.yaml` |
| `focls` | §5.7.2 class：10 个类别 | P7 | 一致 | 不改 | 三平台·`arith.yaml` |
| `fodiv` | §5.4.1 除法 + §7.3 除零 | P1 | 一致 | 不改（NaN 见 D3） | 三平台·`arith.yaml` |
| `fofma` | §5.4.1 单次舍入 + §7.4 溢出 | P13 | 一致 | 不改 | 三平台·`tests/inst/fma`；RTL 待 `m12-chipyard-029` 实测 |
| `fomax` | §9.6 maximumNumber（严格版） | P12 | 一致 | 不改 | 三平台·`arith.yaml` |
| `fomin` | §9.6 minimumNumber（严格版） | P12 | 一致 | 不改 | 三平台·`arith.yaml` |
| `fomul` | §5.4.1 乘法 + §6.3 零符号 | P1 | 一致 | 不改（NaN 见 D3） | 三平台·`arith.yaml` |
| `foqcmp` | §5.11 quiet 比较：仅 sNaN ⇒ invalid | P6 | 偏离 | 改实现（gem5）+ 改 spec 措辞；需立册（建议 `m13-gem5-010`） | 三平台·`arith.yaml`；`ISS-397②` 同类 |
| `forem` | §5.3.1 remainder：精确、平局取偶；§7.2f 无效条件 | P2 | 一致 | 不改 | 三平台·`divrem.yaml` |
| `fornd` | §5.3.1/§5.9 roundToIntegral 六档 | P11 | 一致 | 不改 | 三平台·`roundint.yaml` |
| `foroot` | §9.2.1 rootn(±0,偶数)= +0 | P4 | 偏离 | 改 spec 措辞 + 需立册（待裁定，见 D2） | 三平台·`arith.yaml` |
| `fosclb` | §5.3.3 scaleB：按精确积舍入一次 | P3 | 一致 | 不改（NaN 见 D3） | 三平台·`scaleb.yaml` |
| `foscmp` | §5.6.1 signaling 比较：无序即 invalid | P6 | 一致 | 不改 | 三平台·`arith.yaml` |
| `fosgnj` | §5.5.1 copySign：只改符号位、不置异常 | P5 | 一致 | 不改 | 三平台·`sign.yaml` |
| `fosgnn` | §5.5.1 negate/copySign：只改符号位 | P5 | 一致 | 不改 | 三平台·`sign.yaml` |
| `fosub` | §5.4.1 减法 + §6.3 零符号 | P1 | 一致 | 不改（NaN 见 D3） | 三平台·`arith.yaml` |
| `ft2fo` | §5.4.2 加宽恒精确（不置 NX/OF/UF）；sNaN ⇒ invalid | P8 | 一致 | 不改（NaN 见 D3） | 三平台·`convert.yaml` |
| `ft2ft` | §5.5.1 copy：只搬位、不置异常 | P16 | 一致 | 不改 | 三平台·`convert.yaml` |
| `ft2io` | §5.8 float→int：按方向、越界 invalid | P9 | 一致 | 不改 | 三平台·`convert.yaml` |
| `ft2it` | §5.8 float→int32：按方向、越界 invalid | P9 | 一致 | 不改 | 三平台·`convert.yaml` |
| `ft2uo` | §5.8 float→uint64：按方向、负值 invalid | P9 | 一致 | 不改 | 三平台·`convert.yaml` |
| `ft2ut` | §5.8 float→uint32：按方向、负值 invalid | P9 | 一致 | 不改 | 三平台·`convert.yaml` |
| `ftadd` | §5.4.1 加法 + §7.4/§7.5 | P1 | 一致 | 不改（NaN 见 D3） | 三平台·`arith.yaml` |
| `ftcls` | §5.7.2 class：10 个类别 | P7 | 一致 | 不改 | 三平台·`arith.yaml` |
| `ftdiv` | §5.4.1 除法 + §7.3 除零 | P1 | 一致 | 不改（NaN 见 D3） | 三平台·`arith.yaml` |
| `ftfma` | §5.4.1 单次舍入 + §7.4 溢出 | P13 | 一致 | 不改 | 三平台·`tests/inst/fma`；RTL 待 `m12-chipyard-029` 实测 |
| `ftmax` | §9.6 maximumNumber（严格版） | P12 | 一致 | 不改 | 三平台·`arith.yaml` |
| `ftmin` | §9.6 minimumNumber（严格版） | P12 | 一致 | 不改 | 三平台·`arith.yaml` |
| `ftmul` | §5.4.1 乘法 + §6.3 零符号 | P1 | 一致 | 不改（NaN 见 D3） | 三平台·`arith.yaml` |
| `ftqcmp` | §5.11 quiet 比较：仅 sNaN ⇒ invalid | P6 | 偏离 | 改实现（gem5）+ 改 spec 措辞；需立册（建议 `m13-gem5-010`） | 三平台·`arith.yaml`；`ISS-397②` 同类 |
| `ftrem` | §5.3.1 remainder：精确、平局取偶；§7.2f 无效条件 | P2 | 一致 | 不改 | 三平台·`divrem.yaml`；`m13-spec-003` |
| `ftrnd` | §5.3.1/§5.9 roundToIntegral 六档 | P11 | 一致 | 不改 | 三平台·`roundint.yaml` |
| `ftroot` | §9.2.1 rootn(±0,偶数)= +0 | P4 | 偏离 | 改 spec 措辞 + 需立册（待裁定，见 D2） | 三平台·`arith.yaml` |
| `ftsclb` | §5.3.3 scaleB：按精确积舍入一次 | P3 | 一致 | 不改（NaN 见 D3） | 三平台·`scaleb.yaml` |
| `ftscmp` | §5.6.1 signaling 比较：无序即 invalid | P6 | 一致 | 不改 | 三平台·`arith.yaml` |
| `ftsgnj` | §5.5.1 copySign：只改符号位、不置异常 | P5 | 一致 | 不改 | 三平台·`sign.yaml` |
| `ftsgnn` | §5.5.1 negate/copySign：只改符号位 | P5 | 一致 | 不改 | 三平台·`sign.yaml` |
| `ftsub` | §5.4.1 减法 + §6.3 零符号 | P1 | 一致 | 不改（NaN 见 D3） | 三平台·`arith.yaml` |
| `io2fo` | §5.4.1 int→float：按方向舍入 | P10 | 一致 | 不改 | 三平台·`convert.yaml` |
| `io2ft` | §5.4.1 int→float：按方向、精度损失 ⇒ `NX` | P10 | 一致 | 不改 | 三平台·`convert.yaml` |
| `it2fo` | §5.4.1 int32→f64 恒精确、不置异常 | P10 | 一致 | 不改 | 三平台·`convert.yaml` |
| `it2ft` | §5.4.1 int→float：精度损失 ⇒ `NX` | P10 | 一致 | 不改 | 三平台·`convert.yaml` |
| `uo2fo` | §5.4.1 int→float：按方向舍入 | P10 | 一致 | 不改 | 三平台·`convert.yaml` |
| `uo2ft` | §5.4.1 int→float：按方向、精度损失 ⇒ `NX` | P10 | 一致 | 不改 | 三平台·`convert.yaml` |
| `ut2fo` | §5.4.1 uint32→f64 恒精确、不置异常 | P10 | 一致 | 不改 | 三平台·`convert.yaml` |
| `ut2ft` | §5.4.1 int→float：精度损失 ⇒ `NX` | P10 | 一致 | 不改 | 三平台·`convert.yaml` |

## 5. 表 B：其余 14 条（IEEE 未规定，架构约定）

| 指令 | IEEE 条文（章节 + 结论） | 行为 | 结论 | 动作 | 影响面 |
| --- | --- | --- | --- | --- | --- |
| `cs.n_rrrr_rf` | IEEE 无对应（条件搬移） | P14 | IEEE 未规定 | 不改 | 三平台·`02-reg-copy` |
| `cs.z_rrrr_rf` | IEEE 无对应（条件搬移） | P14 | IEEE 未规定 | 不改 | 三平台·`02-reg-copy` |
| `cs.p_rrrr_rf` | IEEE 无对应（条件搬移） | P14 | IEEE 未规定 | 不改 | 三平台·`02-reg-copy` |
| `ld.t_rrii_rf` | IEEE 无对应；`rf0` 目的为测试机约定 | P15 | IEEE 未规定 | 不改 | 三平台·`m13-qemu-007` |
| `ld.o_rrii_rf` | IEEE 无对应；`rf0` 走 FCSR 写掩码 | P15 | IEEE 未规定 | 不改 | 三平台 |
| `ldm.t_rrri_rf` | IEEE 无对应（多寄存器块取） | P15 | IEEE 未规定 | 不改 | 三平台 |
| `ldm.o_rrri_rf` | IEEE 无对应（多寄存器块取） | P15 | IEEE 未规定 | 不改 | 三平台 |
| `st.t_rrii_rf` | IEEE 无对应（32 位存） | P15 | IEEE 未规定 | 不改 | 三平台 |
| `st.o_rrii_rf` | IEEE 无对应（64 位存） | P15 | IEEE 未规定 | 不改 | 三平台 |
| `stm.t_rrri_rf` | IEEE 无对应（多寄存器块存） | P15 | IEEE 未规定 | 不改 | 三平台 |
| `stm.o_rrri_rf` | IEEE 无对应（多寄存器块存） | P15 | IEEE 未规定 | 不改 | 三平台 |
| `rd2rf_orri_rf` | IEEE 无对应（RD→RF 块搬移） | P14 | IEEE 未规定 | 不改 | 三平台·`02-reg-copy` |
| `rf2rd_orri_rf` | IEEE 无对应（RF→RD 块搬移） | P14 | IEEE 未规定 | 不改 | 三平台·`02-reg-copy` |
| `set.w_rwii_rf` | IEEE 无对应（立即数写 RF；`rf0` 写掩码） | P14 | IEEE 未规定 | 不改 | 三平台·`03-wyde-imm` |

## 6. IEEE 754-2019 条文索引（本册引用）

| 条款 | 一句话结论 |
| --- | --- |
| §4.3 | 舍入方向属性：`roundTiesToEven`/`roundTiesToAway`/`roundTowardZero`/`roundTowardPositive`/`roundTowardNegative` |
| §5.3.1 | 一般运算：`roundToIntegral*`（细则见 §5.9）、`nextUp/nextDown`、`remainder`（n 取最近整数、平局取偶、结果恒精确、`r=0` 取 x 的符号） |
| §5.3.3 | `scaleB(x,N) = x×2^N`，按精确积舍入一次；`scaleB(±0,N)=±0`、`scaleB(±∞,N)=±∞`、`N=0` 返回 x |
| §5.4.1 | 同格式算术：加/减/乘/除/`squareRoot`/`fusedMultiplyAdd`（单次舍入）、`convertFromInt` |
| §5.4.2 | 浮点格式间转换：窄化按 §4 舍入、同进制加宽恒精确；同格式属 canonical 化（sNaN ⇒ invalid），与 `copy` 不同 |
| §5.5.1 | 符号位运算 `copy`/`negate`/`abs`/`copySign`：只改符号位、不置异常、对 NaN 同样生效 |
| §5.6.1 | signaling 比较：任一无序 ⇒ invalid |
| §5.7.2 | `class(x)`：10 个类别（sNaN/qNaN/±Inf/±Normal/±Subnormal/±Zero） |
| §5.8 | float→int：按方向舍入；NaN/Inf/越界 ⇒ invalid；inexact 是否置位由变体（`...Exact...`）决定 |
| §5.9 | `roundToIntegral` 细则：结果同格式、`±0` 保号、不置 OF/UF |
| §5.11 | quiet 比较谓词：**仅** sNaN 操作数 ⇒ invalid（qNaN 不置） |
| §6.2 / §6.2.3 | NaN：qNaN 输入不置异常；结果 NaN 的 payload 与符号位不作规定 |
| §6.3 | 零的符号：精确和为零时由舍入方向决定（`RDN` ⇒ `−0`） |
| §7.2 | invalid 条件（sNaN、`0×∞`、`∞−∞`、`0/0`、`rem` 除数为 0 等） |
| §7.3 | divideByZero：仅「有限非零 ÷ `±0`」 |
| §7.4 | overflow：按方向得到 `±Inf` 或 `±最大有限值`，置 `OF`+`NX`；「轻微溢出」只置 `NX` |
| §7.5 | underflow/inexact：tininess 可在舍入前或后检测（本 ISA 取舍入后）；`UF` ⇔ tiny 且 inexact |
| §9.2 / §9.2.1 | 推荐运算 `rootn`：`n=2` 即平方根；`rootn(±0, 偶数 n>0) = +0` |
| §9.6 | `minimumNumber`/`maximumNumber`：`−0<+0`；单 NaN 返回数；sNaN 置 invalid；双 NaN 返回 qNaN |

## 7. 影响面汇总与立册建议

- **D1（gem5 quiet compare NV）**：影响 `ftqcmp`/`foqcmp` 的 `NV`、`cs.*` 条件链与 `tests/inst/fp/arith.yaml` 四个用例；建议立 `m13-gem5-010`（模块 gem5，M13，2 h）；同批改 `spec/SimRISC-07 §4` 与 `contract-fp §8`（建议挂 `m13-spec-007`，M13，1 h）。
- **D2（`rootn(−0,2)`）**：影响 `ftroot`/`foroot` 的 `−0` 结果；若收严则 RTL/QEMU/gem5 + 向量各一处；建议随 D1 的 spec 任务一并裁定，不单独立册。
- **D3（NaN payload/符号）**：影响全部算术/scaleB/f2f/转换类（约 30 条）的位级结果与 `tests/inst/fp` 期望；建议立 `m13-integ-010`（跨模块，M13，3–4 h）：先定 spec 取值（建议 canonical qNaN），再对齐三实现，最后补位级向量。
- **F1–F3**：文档注释级，随上述任务顺手修，不单独立册。

## 8. 未决 / 待裁定

- D2 的取向（收严为 IEEE `+0` vs 保留 `−0` 并写明有意偏离）需用户裁定。
- D3 的统一取值（canonical qNaN vs 传播首 NaN）需用户裁定（涉及 `contract-fp` 语义冻结段落，属契约变更）。
- 本册的「当前实现」列：gem5 为运行期实测，QEMU/chipyard 为静态读码；三平台 FP 运行时差分待 `m13-integ-002`（用户 2026-11-11 暂缓）恢复后复核。
