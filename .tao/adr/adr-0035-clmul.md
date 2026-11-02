# ADR-0035: `clmul.o` 无进位乘（GF(2) 乘法）指令形态与编码

**状态**：Accepted（2026-10-21；`D1`–`D7` 由用户裁定原话定向，见 `## 状态说明`）
**日期**：2026-10-21
**决策者**：用户（2026-10-21 裁定，原话见 `## Context`）
**关联**：`ADR-0012 D10`（新增 ISA 指令不绑定里程碑）、`ADR-0032`（ISA 编码再分配先例）、`spec/SimRISC-00 §4`（QFC 主表 `0101-0xxx`）、`spec/SimRISC-04 §3`（64 位数据运算）、`contracts/opcodes.yaml`、`manifests/spec-readonly.lock.toml`；issue = `ISS-317`

> **边界（本笔）**：本 ADR 只定**指令形态、语义与编码**（`docs/Process-03`「ADR 不承载规范正文」）。
> `clmul.o` 的 `scope` = **`excluded`**（执行 ⇒ ILLI），**未实现**任何执行语义；
> **未改** `components/llvm-project/**` 的 `.td` ✗、**未改** `components/qemu/**` 补丁集 ✗。

## Context（背景）

### 用户裁定（原话，**逐字引录**；渠道 = 经主会话派发，2026-10-21）

> 「可以，添加 clmul.o rrrr 格式，编码放在 mul.so 后面」

**同批前置共识（2026-10-21，经主会话问答；同日逐条确认）**：只需 **64 位**（`rrrr`）、**不区分符号**、**不要 `clmulh`**（`rrrr` 双目的已覆盖）、**不要 `clmulr`**（用 `rev` 组合）、助记符取 **`clmul`**。

### 用途（目标应用域能力需求）

- **GCM / GHASH**（AES-GCM、IPsec/TLS 记录层）：GHASH 的核心就是 GF(2^128) 上的 carry-less 乘 + 归约，单块 128 位乘可拆成 2–4 条 `clmul.o` 组合。
- **CRC 加速**：CRC（含 CRC-32C）可用「无进位乘 + 折叠加掩码」做长块并行（x86 `PCLMULQDQ` 的经典用法）。
- **Reed-Solomon / 纠错编码**：GF(2^m) 乘法与矩阵求逆。
- **GF(2^k) / 有限域通用运算**：位串多项式乘，是上面各族的公共原语。

### 各 ISA 对照

- **x86**：`PCLMULQDQ`（64×64 → 128 的无进位乘，SSE/AVX）。
- **ARM**：`PMULL` / `PMULL2`（AArch64 加密扩展，64×64 → 128；`PMULL` 另有 8 位形式）。
- **RISC-V**：Zbc 扩展的 `clmul`（XLEN×XLEN → 2·XLEN，`clmulh` 取高半、`clmulr` 取「反向」半）。
- **POWER**：`vpmsumd`（向量多项式乘，GF(2) 无进位乘的向量形态）。
- **共同形态**：都是「两个 64 位源 → 128 位结果」，即本项目 `rrrr` 双目的（`rdHA` 高 / `rdHB` 低）正好覆盖。

### 现场事实（2026-10-21 核）

1. **QFC 主表 `0101-0xxx` 现状**：`add.uo`=0x50、`add.so`=0x51、`sub.uo`=0x52、`sub.so`=0x53、`mul.uo`=0x54、`mul.so`=0x55（均 `rrrr`，双目的）；第 7 格（`xxx=110` ⇒ **op `0x56`**）与第 8 格（`0x57`）为空（reserved）。
2. **`rrrr` 双目的语义已定**（`SimRISC-04 §1.1`/`§3.4`）：`rdHA` 存结果高 64 位、`rdHB` 存低 64 位；`rdHA`/`rdHB` 可单侧为 `rd0`（丢弃该半），**不得同时为 `rd0`**、**不得为同一非 `rd0` 寄存器** ⇒ 违者 ILLI（规则 `dst_dual_same`）。
3. **`opcodes.yaml` 现 259 条**（`excluded` 27 条）；`scope: excluded` ⇔ `decode: ILLI`，与「编码已定、尚未实现」口径一致（`ADR-0034` 同型）。

### 命中 ADR 判据（`docs/Process-03`）

**外部契约**（汇编语言与机器码契约）、**跨模块**（spec / contracts / 生成物 / 后续 LLVM/QEMU/向量册）、**多方案且需记录取舍**（位宽集 / 符号变体 / 高半与反向半的取舍）⇒ 立本 ADR。

## Decision（决策）

### D1 — 判据：目标应用域能力需求 + 软硬件代价比

ISA 候选的取舍判据 = **目标应用域的能力需求 + 软硬件代价比**；**语料频次只用于回答「今天能否验证」，不作否决依据** ✗。

**理由**：用户 2026-10-21 原话（同批裁定，已落纸于 `milestones.md`「ISA 扩展预研遗留」段）——「选择指令的原则不是当前几个测试集；而且我们以后肯定要支持加解密和网络的」。

### D2 — 指令形态：`clmul.o {rdHA, rdHB}, rdHC, rdHD`（`rrrr` 双目的）

- 语义：**GF(2) carry-less 乘**。把 `rdHC`、`rdHD` 各视为 64 位系数多项式（bit *i* = x^*i* 的系数），做系数在 GF(2) 上的多项式乘 ⇒ 127 次多项式 ⇒ **128 位结果**；等价于「逐位与 + 异或累加、无跨位进位」。
- 结果：`rdHA` = 结果**高 64 位**、`rdHB` = 结果**低 64 位**（与 `mul.uo`/`mul.so` 同型）。
- **仅 `.o`**：carry-less 无跨字节进位 ⇒ 窄宽度结果只是 64 位结果的**掩码子集**（`.t`/`.w`/`.b` 由结果掩码取得），**不设 `.t`/`.w`/`.b`** 变体。

**理由**：用户原话「添加 clmul.o rrrr 格式」+ 前置共识「只需 64 位」。

**被否**：为窄宽度各设一条（`clmul.t/.w/.b`）—— 无进位 ⇒ 窄宽度不产生新语义，只是同一结果取低位，属冗余编码。

### D3 — 不分符号

纯位运算，**无符号概念** ⇒ 只有 `clmul.o`，不设 `clmul.u*`/`clmul.s*`。

**理由**：carry-less 乘对位串定义，符号扩展会改变操作数位模式（不再是被乘多项式的系数串）⇒ 有符号变体无意义。

### D4 — 不设 `clmulh` / `clmulr`

- **`clmulh` 不设**：`rrrr` 双目的已同时给出高/低 128 位；只要高低单半时写 `{rdH, rd0}` / `{rd0, rdL}`（与 `mul.uo` 取 `mulhu` 同型，`mulhu ≡ mul.uo {rdH, rd0}`）。
- **`clmulr` 不设**：`clmulr(a, b) = rev(clmul(rev(a), rev(b)))`，可用 `rev.o` 组合表达（`rev.o` 已实现，`ADR-0012 D10`）。

**理由**：前置共识「不要 `clmulh`（rrrr 双目的已覆盖）/ 不要 `clmulr`（用 `rev` 组合）」。

### D5 — 编码：`op = 0x56`，`format = rrrr`，`value = 0x56000000`，`mask = 0xFF000000`

- **落位**：QFC 主表 `0101-0xxx` 行第 7 格（`xxx = 110` ⇒ `op = 0x56`），**紧跟 `mul.so`（`0x55`）**。
- **选格方式**：该行以**整字节 `op`** 选格，**无 `ha`**（非 MISC 子表）⇒ `mask = 0xFF000000`、`value = 0x56000000`（与 `add.*`/`sub.*`/`mul.*` 同族一致）。
- `id = clmul.o_rrrr_rd`；字段同 `mul.uo`：`rdha[23:18]`(dst) / `rdhb[17:12]`(dst) / `rdhc[11:6]`(src) / `rdhd[5:0]`(src)，bank 均 `rd`。

**理由**：用户原话「编码放在 mul.so 后面」；`0x56` 是 `mul.so` 之后的首个空格，且 `0x57` 仍留空（不预占）。

**被否**：放 `0x57` 或另开一行 —— 与「紧跟 mul.so 后面」不符，且制造无谓空洞。

### D6 — `rd0` 规则：与 `mul.uo` 同

`rdHA`/`rdHB` **允许单侧为 `rd0`**（丢弃对应半结果）；**不得同时为 `rd0`**、**不得为同一非 `rd0` 寄存器** ⇒ 违者 **ILLI**（规则 `dst_dual_same`，`SimRISC-04 §1.1` 同口径）。

**理由**：`rrrr` 双目的的既有合法性契约对本条同样适用（`contracts/opcodes.yaml` 的 `dst_dual_same` 表达式复用）。
生成器侧 `scope: excluded` 默认清空 `rule_refs`，本条以**显式例外**保留该引用（`EXCLUDED_KEEP_RULE_REFS`），
以便 `SimRISC-04 附录 B` 的 `dst_dual_same` 清单（由 `rule_refs` 派生）列明 `clmul.o`。

### D7 — 实现状态：本轮只定编码与语义，`scope = excluded`

`clmul.o` 的 `scope` = **`excluded`**（`decode: ILLI`，执行即非法指令）；**执行语义实现**（LLVM 选择/`ISel`、QEMU `trans_*` 语义、L3 向量）归**后续任务册**，本笔不实现、不重建后端。

**理由**：用户原话只涉及指令形态与编码；与 `ADR-0034 D7` 同一纪律（编码先定、实现后落），避免「半实现」状态。

## Rationale（理由）

1. **能力域优先**：GCM/GHASH、CRC、Reed-Solomon 都在目标域（加解密 / 网络 / 存储）内，`clmul.o` 是这些算法的公共原语；按 `D1` 判据，语料「今天没有命中」不构成否决。
2. **代价低**：64×64 GF(2) 乘法器 = 64 个 64 位「与 + 异或树」，是常规组合逻辑；相对软件实现（50–200× 慢）收益明确。
3. **与既有形态零冲突**：`rrrr` 双目的、`rd0` 规则、`op` 选格方式全部复用 `mul.*` 的既有契约；新增面只有 1 个空格 + 1 条助记符。
4. **不留半成品变体**：不设 `clmulh`/`clmulr`/窄宽度/符号变体，避免为同一语义制造多条编码与多条合法性规则。

## Consequences（影响）

1. **汇编/机器码契约新增一项**：`clmul.o {rdHA, rdHB}, rdHC, rdHD` ↔ `0x56`；`excluded` ⇒ 汇编器当前拒绝、执行 ILLI（与 `fence`/`lr/sc` 同处置）。
2. **`opcodes.yaml` 计数**：259 → **260**（`excluded` 27 → 28；`rule_refs` 计数 207 → 208）。
3. **生成物**：`tools/llvm/gen_asm_list.py --embed-spec`（`SimRISC-04 §1.1`）、`tools/spec/gen_legality_list.py`（`dst_dual_same` 条目 + `scope: excluded` 区块）、`tools/testcases/generate_lit_vectors.py`（`gen-excluded.s`）、`tools/llvm/gen_isa_coverage.py`（矩阵）、`.tao/contracts/contract-asm-list.md` 已重生成。
4. **组件面未动**：LLVM `.td` 与 QEMU `insn.decode`/`trans_*` **未加**（`D7`）⇒ `check-instrinfo` 不涉（excluded 不要求 `.td` def）；QEMU 侧解码/桩随实现册同批落。
5. **只读锁**：`spec/SimRISC-00`/`SimRISC-04` 在**用户授权**下重算 `sha256`（`manifests/spec-readonly.lock.toml`）。

## 状态说明

- **逐条定向（2026-10-21）**：用户以裁定原话「可以，添加 clmul.o rrrr 格式，编码放在 mul.so 后面」定向 `D2`/`D5`；前置共识定向 `D3`/`D4`（不分符号、不设 `clmulh`/`clmulr`）；`D1` 为用户同批判据原话；`D6` 为既有 `rrrr` 双目的契约的直接适用；`D7` 为「本轮只定规范面」的直接推论。**`**状态**` = Accepted**。
- **`spec/` 授权**：本笔 `spec/SimRISC-00 §4` 主表格位与 `spec/SimRISC-04 §1.1`/`§3.5` 的改动由用户 2026-10-21 裁定原话（见上）直接授权（`docs/Process-06 §2`）。
- **已核事实的时效**：`Context` 的 3 条现场事实来自 2026-10-21 现场；执行册须现场复核。

## 修订（2026-10-22，用户裁定 A）

- **`D7` 的实施状态描述已过期**：`D7` 原写「本轮只定编码与语义，`scope = excluded`」。`clmul.o` 已经 `QEMU-068t`（执行语义）与 `LLVM-122t`（后端 + `__builtin_dadao_clmul`）落地，并由 `SPEC-155t` 将 `scope: excluded → m9` 翻转 ⇒ **"仅定规范面、不实现"不再成立**。
- **决策正文不变**：`D1`–`D6`（指令形态 `rrrr`、编码 `mul.so` 之后、不分符号、不设 `clmulh`/`clmulr`、双目的契约）与 `D7` 的"编码先定"顺序纪律仍有效；本注记只更正实施状态，撤销需另立 ADR。
