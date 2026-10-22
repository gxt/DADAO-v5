# ADR-0032: ISA 编码再分配（`ext` 迁出 / `shl` 迁入并去 `u`）与新增 `rol`（原 `ror`）

**状态**：Accepted（2026-10-19；`D1`–`D6` 已逐条确认 ⇒ 可进入执行，执行仍按 `D5` 串行 + `D6` 验证面）
**日期**：2026-10-19
**修订**：2026-10-19 —— `D4` 就地修订：新增指令由 `ror`（循环右移）改为 **`rol`（循环左移）**，**编码槽不变**（见文末 `## 修订`）
**决策者**：用户（`D1`–`D6` 2026-10-19 逐条确认，原话见 `## 状态说明`）
**关联**：`ADR-0012`（`D4` `spec/` 只读策略、`D10`/`D11` 新增指令先例）、`ADR-0029`（改名 + `spec/` 授权 + 只读锁重算先例）、`SPEC-141t`（`ror` 预研：候选 A 形态/收益/六环代价）、`SPEC-142t`/`SPEC-143t`（OPC-octa 子表改格先例）、`spec/SimRISC-00 §4.2` / `SimRISC-04 §2.2` / `SimRISC-08/09/10 §2.2`、`contracts/opcodes.yaml`、`.tao/contracts/contract-isa.md`、`manifests/spec-readonly.lock.toml`；落点三册 = `SPEC-152t` / `LLVM-116t` / `QEMU-064t`；issue = `ISS-291`

> **边界（本笔）**：**未改** `spec/` ✗、**未改** `contracts/**` 或 `.tao/contracts/**` ✗、**未改** `components/**` / 任何实现 ✗、**未改**任何任务书 `**状态**` ✗。本 ADR 只记**决策 / 理由 / 被否 / 落点**（`docs/Process-03`「ADR 不承载规范正文」）。**`spec/` 改动须用户原话授权**（`docs/Process-06`）；本 ADR 起草时为 `Proposed`（2026-10-19 已转 `Accepted`），**确认后才动**。

## Context（背景）

### 用户裁定（原话，**逐字引录**；渠道 = 经主会话问答，2026-10-19）

> 「**增加两件事情：第一件事：修改ext的编码，ext.uo的opx改为100-000/101-000；ext.so的opx改为100-001/101-001；核实是否可行，然后我说第二件事**」

> 「**是的，腾出编码**」

> 「**第二件事：把四个子表中的shl.ux的opx改为010-000/011-000，即刚才ext.uo腾出来的位置；然后增加ror.ux指令，其opx为010-001/011-001，即刚才ext.so腾出来的位置；ror指令的格式分别为orrr/orri，针对的都是rd寄存器**」

> 「**ror不区分有符号数还是无符号数，是否有必要在后缀里带u**」→（主会话答：不必要，按 `rev.o` 先例）→「**可以去掉u；同理，shl有必要带后缀u吗？**」→（主会话答：不必要，`shl` 无 `shl.s*` 变体）→「**确认立项**」

**裁定范围（如实界定）**：用户已定向**两件事**（`ext` 迁编码、`shl` 迁编码并去 `u`、新增单向 `ror`），并授权**立项**；`D1`–`D6` 的**细化口径**（窄位宽的旋转量取模/越界规则、`ror` 目的 `rd0` 的非法口径、排序约束、验证面）属本 ADR 的**提案**，**须逐条确认**后方可执行。

### 现场事实（主会话 2026-10-19 已核；本 ADR 引录，执行册仍须现场复核）

1. **基表（OPC-octa，`op = 0x40`）现状**：`010-000` = `ext.uo`（orrr）、`010-001` = `ext.so`（orrr）、`010-010/011` = `shr.uo/so`（orrr）、`010-100` = `shl.uo`（orrr）；`011-000/001` = `ext.uo/so`（orri）、`011-010/011` = `shr.uo/so`（orri）、`011-100` = `shl.uo`（orri）。
2. **三个宽度子表（`SimRISC-08/09/10`，`op = 0x41/0x42/0x43`）现状**：`010-000/001` **空**；`010-010/011` = `shr.u*/s*`；`010-100` = `shl.u*`；`011-000/001` **空**；`011-010/011` = `shr.u*/s*`；`011-100` = `shl.u*`。
3. **目标格位空闲**：基表 `100-000` / `100-001` / `101-000` / `101-001` **全空** ⇒ `ext` 可整体迁入；宽度子表的 `010-000/001`、`011-000/001` **空** ⇒ `shl`/`ror` 可放入。
4. **`shl` 只有 `u` 变体**：`spec/` 内 `shl.s*` 命中 **0**；`shr.s*` 命中 **8**（`shr` 确实分 `u/s`）⇒ `shl` 的 `u` 后缀不承载信息。
5. **`shl.u*` 引用面很广**：主会话核全仓约 **170 处**（含语料/向量/工具/后端/模拟器与生成物）；执行册须**现场重数**，**计数不写死**。
6. **后端/模拟器现状（编码与 id 绑定）**：LLVM `.td` 以 `ha` 硬编码（`shl_uo` orrr `ha=0x14`、orri `ha=0x1C`）；QEMU `insn.decode` 与 `trans_shl_uo_*` 由 `id` 派生 ⇒ 改名会同时改 `trans_*` 函数名；`contracts/opcodes.yaml` 由 `tools/spec/generate_opcodes.py` 生成，`check_scope.py` 的 scope 白名单与计数为硬编码。
7. **`rotl`/`rotr` 现状 = 通用展开**：`LLVM-099t` 把 `ISD::ROTL`/`ISD::ROTR` 置 `Expand`（`DADAOISelLowering.cpp` 注释明写「ISA has no rotate instruction」）⇒ 新增 `ror` 后该口径需要重新判定（属 `LLVM-116t` 现场判，见 `D6`）。

### 命中 ADR 判据（`docs/Process-03`）

**高代价**（ISA 编码迁移 + 助记符改名，波及规范/合约/生成器/后端/模拟器/语料）、**跨模块 / 需一致**（spec / llvm / qemu / testcases）、**多方案且需记录取舍**（`ext` 迁往何处、`shl` 是否保留 `u`、`ror` 的窄位宽口径）、**外部契约**（汇编语言与机器码契约，旧汇编源/旧二进制不兼容）⇒ 立本 ADR。

## Decision（决策）

### D1 — `ext.uo`/`ext.so` 迁到 `100-000`/`100-001`（orrr）与 `101-000`/`101-001`（orri）

**决定**：

| 指令 | orrr（行 `100-xxx`） | orri（行 `101-xxx`） |
| --- | --- | --- |
| `ext.uo` | `100-000` | `101-000` |
| `ext.so` | `100-001` | `101-001` |

- **只改编码，不改助记符**：`ext.uo`/`ext.so` 确实分零扩展/符号扩展，**保留 `u`/`s`**（与 `D3` 的命名规则一致）。
- 语义、操作数形态（`orrr`/`orri`）、`hd ≤ 63`、目的 `rd0` ⇒ ILLI **全部不变**。

**理由**：用户原话「**是的，腾出编码**」；基表 `100-000/001`、`101-000/001` 现场为空（事实 3），迁移后**恰好腾出** `010-000/001` 与 `011-000/001` 四个格位给 `shl`/`ror`，且保持 `ext` 两种格式的相邻性。

**被否**：

- **保留 `ext` 原位、把 `shl`/`ror` 放到 `100/101` 行**：宽度子表的 `100` 行已被 `add.u*/s*` 占用（事实 2），`shl` 四宽度无法整体迁入；且会把移位族拆散。
- **只与 `shl` 交换（`ext`→`010-100`）**：`ror` 仍无格位，且 `010-100` 与 `shr` 族不连续。
- **借 `scope: excluded` 的格位**：语义上不是同一类，且会污染 excl 范围。

### D2 — `shl.*` 迁到 `010-000`/`011-000`（四个位宽）

**决定**：`shl.o`/`shl.t`/`shl.w`/`shl.b` 的 orrr 形态统一在 `010-000`，orri 形态统一在 `011-000`（基表 + 三个宽度子表**同一 opx 规则**）。

**理由**：用户原话「**把四个子表中的 `shl.ux` 的 opx 改为 `010-000/011-000`**」；迁移后移位族排列为 `shl`(000) / `rol`(001) / `shr.u`(010) / `shr.s`(011)，**同族连续**，便于阅读与人工编码。

**被否**：

- **`shl` 放 `100-000`**：见 `D1` 被否（宽度表冲突）。
- **不同位宽用不同 opx**：违背 MISC 子表「同名指令跨位宽同位」的既有惯例。

### D3 — `shl` 去掉 `u` 后缀（`shl.uo→shl.o` 等）

**决定**：`shl.uo`/`shl.ut`/`shl.uw`/`shl.ub` → **`shl.o`/`shl.t`/`shl.w`/`shl.b`**；id 同步为 `shl.o_orrr_rd` / `shl.o_orri_rd` / …。**语义不变**。

**命名规则（成文）**：**只有真正分「零扩展/符号扩展」的指令才带 `u`/`s`**——`shr`/`add`/`sub`/`cmp`；**符号无关的指令不带**——`shl`/`rol`/`rev`/`ctpop`/`ctlz`/`cttz`。

**理由**：用户原话「**可以去掉u；同理，shl有必要带后缀u吗？**」；`spec/` 内 `shl.s*` **0 命中**（事实 4）⇒ `u` 不承载区分信息；先例 = `rev.o`/`ctpop` 等无位宽后缀的符号无关指令。

**被否**：

- **保留 `.uo` 兼容旧汇编源**：与「符号无关不带后缀」的规则冲突，且 `shl` 永远不会出现 `s` 变体，`.u` 是永久噪声。
- **保留 `.uo` 并新增 `shl.o` 别名**：同一语义两条助记符，增加汇编器/反汇编器/覆盖率矩阵的重复面，无收益。

### D4 — 新增 `rol.o`/`rol.t`/`rol.w`/`rol.b`（单向逻辑循环左移）

**决定**：

| 位宽 | orrr（`010-001`） | orri（`011-001`） |
| --- | --- | --- |
| `rol.o` | `rol.o rdHB, rdHC, rdHD` | `rol.o rdHB, rdHC, immu6` |
| `rol.t` | `rol.t rdHB, rdHC, rdHD` | `rol.t rdHB, rdHC, immu6` |
| `rol.w` | `rol.w rdHB, rdHC, rdHD` | `rol.w rdHB, rdHC, immu6` |
| `rol.b` | `rol.b rdHB, rdHC, rdHD` | `rol.b rdHB, rdHC, immu6` |

- **语义**：**逻辑循环左移**（无符号概念，位串旋转）：`rdHB[W-1:0] = rol(rdHC[W-1:0], amount)`；`W` = **位宽**（`o/t/w/b` = 64/32/16/8）；**高位于结果写满**（沿用 `SPEC-069t` 值语义：`o` 写满 64 位；`t/w/b` 按各自位宽扩展规则）。
- **不分有符号/无符号**：**只有一个方向**（左），**不带 `u`/`s`**（落到 `D3` 命名规则）。
- **旋转量**：orrr 取 `rdHD` 的低 `log2(W)` 位（即 **mod W**）；orri 的 `immu6` 有效范围 **`0..W-1`**，越界 ⇒ **ILLI**（与既有窄位宽 `shl.u*` 的 `immu6 <= N` 约束同口径）。`o` 为 `0..63`。
- **目的 `rd0` ⇒ ILLI**：沿用 `dst_rd0` 规则；三者均 `rd` 银行（用户原话「**针对的都是rd寄存器**」）。
- **`rol` 与 `ror`**：`ror(x,n) = rol(x, (W-n) mod W)` ⇒ **一个方向足以表达双向**，不另设 `ror`。

**理由**：用户原话「**增加ror.ux指令**…**格式分别为orrr/orri，针对的都是rd寄存器**」（2026-10-19 修订为 `rol`，原话见文末 `## 修订`）；`SPEC-141t §追加候选 A` 已量化收益（常量 rotate 5→1、变量 ~9→1；SHA-512 每轮 6 次旋转）与主流先例（RISC-V 只有 `ror`/`rori`、ARM32 仅 `ROR`；本设计取 `rol` 因 `ROTL` 直连，见 `## 修订`）。窄位宽取模/越界口径沿用既有移位规则，避免 `rol.b` 出现「旋转 8 位 = 恒等」的歧义特例。

**被否**：

- **同时加 `ror`**：冗余（可由 `rol` 表达），编码面翻倍。
- **加 `fshl`/`fshr`（漏斗移位）**：`SPEC-141t` 已裁定本轮不取（编码面翻倍 + ISel 复杂）。
- **带 `u`/`s` 变体**：循环移位与符号性无关，两个变体语义相同 ⇒ 纯冗余。
- **`rol.b` 旋转量任意 `immu6` 并对 8 取模**：与既有窄移位「`immu6 > N` ⇒ ILLI」规则不一致，会让同一族的越界行为分裂；**取模仅用于寄存器形态的低位截取**。
- **旋转量取 RB 银行**：用户明确「针对的都是 rd 寄存器」；且 `rd` 银行恒 64 位，避免 RB 地址语义混入。

### D5 — 排序约束：先 `ext` 迁出 → 再 `shl` 迁入 → 再放 `rol`

**决定**：三册（`SPEC-152t` → `LLVM-116t` → `QEMU-064t`）**串行**；`spec/` 内的表格改写按「`ext` 先离开 `010/011`、`shl` 再进入、`rol` 最后占位」的语义顺序进行（**允许同一提交内完成**，但审查/证据按此顺序呈现）。

**理由**：`010-000/001` 与 `011-000/001` 在 `ext` 迁出前不是空闲格位；先迁出可保证任何中间态都**没有两指令同格**。跨册串行则保证 `opcodes.yaml` 的 id 变化与 `trans_*`/`.td` 的改名同步，避免把「门控红」误当缺陷。

**被否**：

- **三册并行**：共享 `contracts/opcodes.yaml`/生成物，且 `install-host` 与构建树单写者约束（`ISS-229`/`ISS-210`）⇒ 必串行。
- **先放 `rol` 再迁 `ext`**：中间态编码冲突，验证证据不可解释。

### D6 — 落点与验证面

**决定**：

- **规范面（`SPEC-152t`）**：`spec/SimRISC-00` 四张表（基表 + `08/09/10` 三宽度表）；`SimRISC-04 §2.2` 语义/逐条表 + 生成区（汇编速查）；`SimRISC-08/09/10 §2.2` 同步；`Toolchain-01` 现场核（若出现 `shl.u*`/编码示例则改，否则不改并留证据）；`contracts/opcodes.yaml` 重生成；`.tao/contracts/contract-isa.md`（`§2.8`/附录 A、`§6.4.1`、`§6.4.5`）与 `contract-asm-list.md` 重生成；`tools/spec/generate_opcodes.py`（`ha`/助记符/`scope: m9`）、`tools/spec/check_scope.py`（白名单 + 计数）、语料/向量的**机械改名**；`manifests/spec-readonly.lock.toml` 仅对改动册重算 `sha256`。
- **后端面（`LLVM-116t`）**：`.td` 编码/助记符/id、MC/AsmParser、`ISD::ROTL` 直配 `rol.o`（`ROTR` 以 `rol(x, W-n)` 表达）；**`ISD::ROTL`/`ROTR` 的 `Expand` 口径重新判定**（`LLVM-099t` 的注释与动作以「无 rotate 指令」为前提，现已失效）——**现场判并给依据**（合法/自定义/展开三选一，含常量/变量两条路径的指令数证据）；`make install-host`。
- **模拟器面（`QEMU-064t`）**：`insn.decode` 重生成 + `trans_*` 改名/新增 + L3 语义向量（**独立 oracle**：期望值按 `rol` 定义手算，不从 QEMU/LLVM 反推）+ `build-qemu`/`install-host`。
- **验证面**：`validate-encoding` / `check-scope` / `check-rule-refs` / `check-legality-invariants` / `check-spec-*` / `check-asm-list*` / `check-lit-gen` / `validate-vectors`（规范面）；`check-instrinfo` / `check-isa-coverage` / `check-lit`（后端面）；`check-interface` / `check-qemu-smoke` / `check-qemu-semantics` / L1·L2·L3（模拟器面收口）。**每条断言须有可达 FAIL 路径**（`--self-test` 或注入）。

**理由**：编码是**跨模块单一真源**（`contracts/opcodes.yaml` 由 spec 生成，LLVM/QEMU/语料消费）；只在 `spec/` 改会让门控红、只在 `opcodes.yaml` 改会造成规范漂移。`LLVM-099t` 的 rotate 展开是**基于「无指令」的临时口径**，新增指令后必须重判，否则会把「有指令仍展开」固化。

**被否**：

- **只改 `contracts/opcodes.yaml`**：`spec/` 与契约漂移（`check-spec-drift`/`check-spec-codeblocks` 红），且违背 Spec-first。
- **只改 `spec/`**：实现/门控全部红，且无法交付能力。
- **保留 `LLVM-099t` 的 `Expand` 不动**：`rol` 指令永远不被选中，等于只做编码不做能力。

## Consequences（影响）

1. **旧汇编源不兼容**：`shl.uo` 等写法将不再被受理（**不做别名**，`D3` 被否）；引用面约 170 处须机械改名并逐条留证。
2. **旧二进制不兼容**：`ext` 与 `shl` 的编码都变化 ⇒ 旧对象/旧 `.so`/旧测试二进制**必须重建**；`QEMU` 对旧编码按新表解码（落在 `rol`/保留格）。
3. **`scope` 扩展**：新增 `scope: m9`（8 条 `rol`），`tools/spec/check_scope.py` 的白名单与计数须同步；总数 235 → **243**（现场派生，不写死）。
4. **QEMU `trans_*` 改名**：`trans_shl_uo_*` → `trans_shl_o_*`，并新增 `trans_rol_*`；`insn.decode` 由 `opcodes.yaml` 重生成。
5. **LLVM 后端**：`shl_uo_*` → `shl_o_*` 的 def 名 ripple 到 `DADAOInstrInfo.h` 枚举、`DADAOCodeGen.td`、`DADAOISelDAGToDAG.cpp`；`rol` 需要 ISel 真指令；`rotl/rotr` 的 `Expand` 注释与动作重判。
6. **只读锁**：`SimRISC-00/04/08/09/10`（以及若改动的 `Toolchain-01`）需在**用户授权**后重算 `sha256`，同变更内更新 `manifests/spec-readonly.lock.toml`。
7. **文档/矩阵**：`tools/llvm/llvm-isa-backend-matrix.*`、`tests/vectors/inventory.md`、`tests/llvm/lit/MC/DADAO-gen/*` 等生成物须重生成；`check-isa-coverage` 的「isel 是否用得上」列预计 `rol` 从 `no` 变 `yes`。

## decision 逐条确认表（`D1`–`D6`）

| 条目 | 内容摘要 | 用户是否已定向 | 待确认点 | 确认结果（2026-10-19） |
| --- | --- | --- | --- | --- |
| `D1` | `ext.uo/so` → `100/101` 的 `000/001` | ✅（原话「腾出编码」） | 助记符不变、`hd`/`dst_rd0` 不变 | **已确认** |
| `D2` | `shl.*` → `010/011` 的 `000`（四宽度） | ✅（原话「四个子表…改为010-000/011-000」） | 四宽度同一 opx | **已确认** |
| `D3` | `shl` 去 `u`；命名规则成文 | ✅（原话「可以去掉u」） | 不做旧助记符别名 | **已确认** |
| `D4` | 新增 `rol.{o,t,w,b}`，orrr/orri | ✅（原话「增加ror.ux…orrr/orri…rd」；2026-10-19 修订为 rol） | **窄位宽取模/越界口径**、`dst_rd0` ILLI、单向不设 `ror` | **已确认（含 2026-10-19 修订）** |
| `D5` | 先 `ext` 出 → `shl` 入 → `rol` 放 | 流程提案 | 三册串行、同提交内允许 | **已确认** |
| `D6` | 落点与验证面；`ROTL/ROTR` 重判 | 方法提案 | 是否需要 `LLVM-116t` 的「改走 `rol`」判据与证据格式 | **已确认** |

> 确认方式（`AGENTS.md`「ADR decision 逐条确认」）：用户逐条答复；**2026-10-19 已逐条确认**（`D1`–`D6` 全「已确认」），状态转 `Accepted`，用户原话见 `## 状态说明`。

## 状态说明

- **逐条确认完毕（`D1`–`D6`，2026-10-19）**：用户全部确认（原话「**没异议**」，渠道 = 经主会话问答）；前序原话（两件事定向 + 「确认立项」）见 `## Context`。`**状态**` Proposed → **Accepted**；本笔**仍不执行** `D1`–`D6`（执行归三册，`spec/` 改动授权随执行册另行落纸）。
- **本笔 = 起草笔**（2026-10-19）：只落 `Proposed` + 三册 + 台账；**未执行** `D1`–`D6`。
- **`spec/` 授权**：用户 2026-10-19 的「**确认立项**」是**立项授权**，**不是**逐条 decision 确认，也**不是**对具体 `spec/` 文本的改动授权（`docs/Process-06`）。逐条确认已另行完成（本笔 ↑）；执行册开工前仍须取得 **`spec/` 改动授权原话落纸**。
- **已核事实的时效**：本文 `Context` 的 7 条事实来自主会话 2026-10-19 现场；执行册**必须现场复核**（`grep`/生成器/表格逐格），不复核不得作为验收依据。

## 修订

### 2026-10-19 — `D4` 就地修订：`ror` → `rol`（编码槽不变）

**用户原话（逐字引录，渠道 = 经主会话问答）**：

> 「保持ILLI；我在思考的一个问题是：是不是改为rol更合适？本质上ror/rol只需要实现一个即可，而从编码上看，该指令前面是shl，后面是两个shr，如果改为rol，再和shl换个位置，是不是更规整」

> 「确认：ror 改为 rol」

**修订内容（仅 `D4` 的方向/助记符；`D5`/`D6` 等处的 `ror` 字样同步为 `rol`）**：

- `D4` 的 `ror.o`/`ror.t`/`ror.w`/`ror.b` → **`rol.o`/`rol.t`/`rol.w`/`rol.b`**；语义 = **逻辑循环左移**（`rdHB[W-1:0] = rol(rdHC[W-1:0], amount)`）。
- **编码槽不动**：orrr `010-001`、orri `011-001`；`D1`/`D2` 的 `ext`/`shl` 编码不变。
- **其余口径不变**：orrr/orri 格式、操作数全为 `rd` 银行、旋转量 `mod W`/`immu6` 越界 ILLI、目的 `rd0` ⇒ ILLI、不分有/无符号、仅一个方向；`D3` 命名规则中的 `ror` 同步为 `rol`（符号无关、不带 `u`/`s`）。
- **不换位（主会话判断）**：`shl`(000) 与 `rol`(001) 已构成「左、左」，`shr.u`(010)/`shr.s`(011) 为「右、右」，原排列已规整；换位会动 `shl`/`rol` 的编码槽，收益为零，故**不换**。
- **理由**：`ROTL` 可直连 `rol`（无需 `W−n` 反向）；`rol`/`ror` 语义等价（`ror(x,n) = rol(x,(W−n) mod W)`），只需实现一个；编码槽保持不变 ⇒ 不影响 `D1`/`D2` 的再分配结果。
- **历史层不改**：`## Context` 中用户既往原话（含「增加ror.ux指令」）与 `## 状态说明` 为历史记录，保持原样；`SPEC-141t` 的 `ror` 预研记录亦不改。本次同步落点 = `spec/SimRISC-00/04/08/09/10`、`.tao/contracts/contract-isa.md`、`contracts/{opcodes,legality_rules}.yaml`、`manifests/spec-readonly.lock.toml`。
- `**状态**` 保持 **Accepted**。
