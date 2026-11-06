# ADR-0050: 转换指令的舍入方向编码（六档 / SBZ / 计数三分）

**状态**：Proposed（D1–D7 待用户逐条确认；确认后置 Accepted）
**日期**：2026-11-06
**关联**：`contract-fp §3/§12`、`SimRISC-07 §格式转换指令`、`GEM5-021t`（差异发现）、`GEM5-022t`（SE 基线）

## Context（背景）

`convert_f2i`（8 条）、`convert_i2f`（8 条）、`convert_ff`（`ft2fo`/`fo2ft`）与 4 条复制（`ft2ft`/`fo2fo`/`rd2rf`/`rf2rd`）共用 `orri` 的低 6 位 `immu6`，当前语义是「连续处理的寄存器个数（1–63）」。

实测差异（`GEM5-021t`）：C 的 `(long long)2.7` 在 QEMU 得 `2`、gem5 得 `3`。根因是三方不一致：

- SPEC：转换舍入「由 `rf0[33:32]` 控制」（默认 RNE）
- 工具链：对 C cast 只发裸 `fo2io`，不写 `rf0`
- QEMU：硬编码 `*_round_to_zero`

同时，ISA 设计层面需要回答：转换的舍入方向应当由隐藏状态（`rf0`）决定，还是由指令显式携带。

## Decision（决策）

- **D1 分类（按结果是否依赖舍入）**：18 条格式转换分三类 ——
  - **六档（15 条）**：8 条 `f2i` + `fo2ft` + 6 条不精确 `i2f`（`io2fo`、`uo2fo`、`it2ft`、`ut2ft`、`io2ft`、`uo2ft`）
  - **SBZ（3 条，精确）**：`ft2fo`（f32→f64）、`it2fo`（int32→f64）、`ut2fo`（uint32→f64）
  - **计数（4 条，纯复制）**：`ft2ft`、`fo2fo`、`rd2rf`、`rf2rd` 保留 1–63 与原合法性
- **D2 六档定义**：低 6 位为 one-hot —— `0x01` RNE、`0x02` RNA、`0x04` RTZ、`0x08` RUP、`0x10` RDN、`0x20` dynamic（读 `rf0[33:32]`）；其他值 ⇒ ILLI。
- **D3 精确转换**：低 6 位 SBZ（必须为 0，非 0 ⇒ ILLI）；不产生舍入，不置 NX。
- **D4 复制类**：保留 1–63 计数与 `mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap` 规则，不改。
- **D5 NX/NV 口径**：转换 inexact ⇒ 置 NX（只实现 IEEE「Exact 族」，与 RISC-V `fcvt` 同口径）；NaN/Inf/超出目标范围 ⇒ 饱和（最大/最小）+ 置 NV，不置 NX。
- **D6 工具链映射**：C 的浮点→整数 cast 发 `0x04`；C 的整→浮与 `(float)d` 发 `0x20`（跟随 `rf0`）；方向固定的语言（如要求 RNE）发 `0x01`。
- **D7 实现与兼容**：QEMU/gem5 都按字段方向实现，`0x20` 才读 `rf0`；不新增方向变体、不改复制类。旧「`immu6` = 个数」编码作废，属不兼容的 ISA 版本变更，工具链/向量/两引擎须同步重生成。

## Rationale（理由）

- **方向是运算属性**：结果依赖舍入的转换应能表达任意方向，不应由隐藏状态决定；显式档让指令成为纯函数，编译/重排/向量化不必证明「中间没有改 `rf0`」。
- **多语言共存**：C 的 f2i cast 要求恒截断（与 `fesetround` 无关），必须能覆盖环境默认；Rust/Java/Go 等要求固定方向且无 fenv，`0x20` 让 C/Ada/Fortran 继续「跟随环境」，静态档让固定方向语言不受同进程 `fesetround` 影响。
- **与既有体系一致**：`roundint`（`ftrnd`/`fornd`）已用六档 one-hot，转换族沿用同一编码习惯；`0x20` 的 dynamic 语义与 `roundint` 的 `0x20` 对齐。
- **精确/SBZ 与复制/计数的划分**：避免为无舍入语义的指令保留无意义字段，同时不牺牲块复制（ABI 保存/恢复需要）。

## Consequences（影响）

- `SPEC/SimRISC-07` 与 `contract-fp §3/§12`、`contracts/opcodes.yaml` 的合法性规则需更新（`encode_onehot` / SBZ / 计数三套并存，按指令允许集校验）。
- LLVM：f2i cast 发 `0x04`、i2f/`fo2ft` 发 `0x20`，删除 rf0 保存/恢复的需求；汇编/反汇编与 MC 同步。
- QEMU：8 条 f2i 与 6 条 i2f、`fo2ft` 改为按字段方向（`0x20` 读 `rf0`）。
- gem5：由「总读 `rf0`」改为「按字段」（`0x20` 才读 `rf0`）。
- 测试：转换向量按新编码重生成；补各方向与 NX/OF/UF 断言；`GEM5-021t` 基线的 10 个 `convert_f2i` 差异应转绿。
- 所有既有 `immu6=count` 的转换编码失效（工具链当前只发 `count=1`，重生成即可）。

## 待确认

D1–D7 逐条确认后置 `Accepted`；任何一条调整都需回到讨论再冻结。
