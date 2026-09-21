# TESTCASES-010t: 数据级覆盖率缺口消解（154 缺口）

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-009t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `tests/vectors/isa/` 下 **15 个目标文件**（`reg-arith`/`reg-logic`/`reg-shift-extend`/`reg-compare`/`reg-cond-assign`/`reg-imm-block`/`mem-rd`/`mem-rb`/`mem-ra`/`ctrl-br`/`ctrl-jump`/`ctrl-call`/`ctrl-ret`/`misc`/`reserved`）
  - `tests/vectors/inventory.md`（M1 覆盖矩阵，178 行）
  - `contracts/legality_rules.yaml`（316 行，24 条规则：18 active + 6 deferred）
  - `contracts/opcodes.yaml`（178 M1 身份）
  - `tools/testcases/generate_isa_vectors.py`（生成 `reg-*` 6 文件）
  - `tools/testcases/generate_ctrl_br.py`（生成 `ctrl-br.yaml`）
  - `tools/testcases/generate_ctrl_jump_call_ret.py`（生成 `ctrl-jump`/`ctrl-call`/`ctrl-ret`）
  - `tools/testcases/validate_vectors.py`（数据级覆盖门控，现 exit 0 / gap 154）
  - `.tao/knowledge/contract-isa.md`（ISA 合约，§3/§4/§5/§7/§9）
  - `.tao/knowledge/adr-0004-test-machine.md`（测试机地址图）
- 输出：
  - 修改后的生成器（`generate_isa_vectors.py`、`generate_ctrl_br.py`、`generate_ctrl_jump_call_ret.py`）
  - 重新生成的向量文件（`tests/vectors/isa/*.yaml`，增量新增 legality/boundary/overlap case）
  - 更新后的 `tests/vectors/inventory.md`（降级 `✓` → `deferred <reason>` 的行）
  - `tools/testcases/validate_vectors.py` 门控转严（gap = 0 ⇒ 可选改为阻断）
- 约束：
  - **不改** `contracts/`（`legality_rules.yaml`/`opcodes.yaml`）与 `spec/`
  - **不改** harness/QEMU/LLVM
  - 向量数据必须由**生成器**产出（不得手写 YAML 后不更新生成器）
  - 生成器已入 `tools/testcases/`（遵守「生成器随产物保留」）
  - 期望值必须**独立派生**自 `spec/` 与 `contract-isa.md`（Independent oracle 原则）
  - 不改 `tests/scripts/`、`components/`
  - 完成后不自行 commit

## 背景

### 问题根源

`TESTCASES-009t` 建立了数据级覆盖率门控（`validate_vectors.py`），按 `inventory.md` 每行 `✓` 声明逐 `(insn, format, class)` 校验 active case 存在性。当前 `inventory.md` 对 177 个 M1 身份声明了 `legality` ✓（`swym-iiii` 为 `—`），但 `tests/vectors/isa/*.yaml` 中**仅 36 个身份有 active legality case**（88 条）。此外还有 2 个 `boundary` 和 11 个 `overlap` 缺口。

缺口根因：`003t`~`008t` 生成数据时，各任务只覆盖了本任务的重点族的 legality case（如 `mem-rd` 的 ILLI/MALIGN/UNMAPPED、`ctrl-br` 的 encoding/semantic），**未对每个 `(insn, format)` 生成 legality case**。`009t` 审计时发现此缺口并登记为 154 gap，但作为兜底任务不补数据。

### 目的

逐条消解 154 个数据级覆盖率缺口——二选一：**(a) 补 active case**（legality/boundary/overlap），或 **(b) 把 `inventory.md` 的对应 `✓` 降为 `deferred <reason>`**。消解后 `validate_vectors.py` 的 gap 计数应为 **0**（或全部有 `deferred` 理由）。

### 缺口精确构成（来自 `validate_vectors.py` stderr，2026-09-21 实测）

| 缺口类 | 计数 | 来源文件分布 |
|--------|------|-------------|
| legality | 141 | reg-shift-extend(40) + reg-arith(45) + reg-logic(16) + reg-imm-block(13) + reg-compare(11) + ctrl-br(10) + reg-cond-assign(5) + ctrl-jump(1) |
| boundary | 2 | reg-arith: `add.si-rd`(riii) + `add.si-rb`(riii) |
| overlap | 11 | reg-imm-block(6): rd2rd/rd2ra/ra2rd/rb2rb/rd2rb/rb2rd + reg-cond-assign(5): cs.n/cs.z/cs.p/cs.eq/cs.ne |
| **合计** | **154** | 全部在 `reg-*` 和 `ctrl-*` 文件中，由 3 个生成器覆盖 |

**注意**：`mem-*`（rd/rb/ra）文件**无缺口**（`004t` 已为每个身份生成 legality case）；`misc.yaml` **无缺口**（`illi` legality + `fence` legality + `swym` encoding/semantic 已覆盖）；`reserved.yaml` **无缺口**（2 条 UNDI legality 已覆盖）。

## 逐条判据（机械形式）

对每个 `(insn, format)` 缺口，按以下**机械流程**判定应补 active case 还是降级为 deferred：

### 判据 L（legality 缺口）

对每个有 `legality` ✓ 但无 active legality case 的 `(insn, format)`：

1. **查 `contracts/legality_rules.yaml`**：逐条扫描 `status: active` 的规则，检查该 `(insn, format)` 是否**受该规则约束**（判据：规则 `description` 中提及的指令/格式/字段是否覆盖该 insn）。
2. **判定**：
   - 若存在 ≥1 条 `status: active` 的规则适用于该 insn → **必须补 active legality case**（触发 fault 的最小构造）
   - 若**仅** `status: deferred` 的规则适用，或**无任何规则**适用 → **降为 `deferred <reason>`**（引用规则 id 或说明）
3. **已知分类**（按规则适用性预分，engineer 须逐条复核）：

   | 规则 id | fault | 适用指令族 | 说明 |
   |---------|-------|-----------|------|
   | `rd_dest_rd0` | ILLI | 所有 rd 目的指令（orrr/orri/rrii/riii/rwii/rrrr） | 单目的 `rdha` 或双目的 `rdhb` 为 rd0 |
   | `store_src_rd0` | ILLI | `st.*`/`stm.*`（RD store） | `rdha` 为源数据，rd0 → ILLI |
   | `dual_dest_both_rd0` | ILLI | `add.uo/so`、`sub.uo/so`、`mul.uo/so`（rrrr） | `rdha == rd0 && rdhb == rd0` |
   | `dual_dest_same_reg` | ILLI | 同上 rrrr 双目的 | `rdha == rdhb != rd0` |
   | `rb_dest_rb0` | ILLI | `add.so-rb`、`sub.so-rb`（orrr）、`add.si-rb`、`rela.si-rb`（riii）、`set.zw-rb`、`or.w-rb`、`andn.w-rb`（rwii）、`rb2rb`/`rd2rb`（orri）、`ld.o-rb`/`ldm.o-rb`（rrii/rrri） | rb 目的为 rb0 |
   | `multi_immu6_zero` | ILLI | `rd2rd`/`rb2rd`/`rd2rb`/`rb2rb`/`ra2rd`/`rd2ra`（orri）、`ldm.*`/`stm.*`（rrri） | `immu6 == 0` |
   | `multi_range_overflow` | ILLI | 同上块赋值 + 多寄存器 | `start + immu6 > 64` |
   | `ra_multi_immu6_zero` | ILLI | `ra2rd`/`rd2ra`（orri）、`ldm.o-ra`/`stm.o-ra`（rrri） | `immu6 == 0` |
   | `ra_multi_range_overflow` | ILLI | 同上 | `start + immu6 > 64` |
   | `ra2rd_dest_rd0` | ILLI | `ra2rd`（orri） | 目的 `rdhb == rd0` |
   | `shamt_overflow` | ILLI | `shl.*`/`shr.*`（orrr/orri） | `shamt > N`（N=7/15/31/63） |
   | `ext_bit_overflow` | ILLI | `ext.*`（orrr/orri） | `hd > N` |
   | `div_by_zero` | ILLI | `div.*`/`rem.*`（orrr） | 除数为零 |
   | `div_overflow` | ILLI | `div.s*`（orrr） | `INT_MIN ÷ (−1)` |
   | `sbz_nonzero` | ILLI | `fence`（oiii） | `immu18` bits[17:4] ≠ 0 |
   | `data_malign` | MALIGN | 访存指令 | 未对齐 EA |
   | `instruction_align` | IALIGN | `jump-rrii`（rrii） | `rbha + rdhb + (imms12<<2)` 低 2 位 ≠ 0 |
   | `ras_of` | RASOF | `call-*`（iiii/rrii） | RA 栈满 |
   | `ras_uf` | RASUF | `ret-*`（riii） | RA 栈空 |

4. **`br.*`（10 个缺口）的特殊判定**：
   - `br.cond`（riii/rrii）的分支目标 = `rb0 + (imm << 2)`，低 2 位**恒为零**（编码保证），**不触发 IALIGN**
   - 分支指令不写寄存器、不访存，不触发 `rd_dest_rd0`/`data_malign` 等
   - **无任何 `status: active` 的 legality 规则适用于 `br.*`**
   - **判定：降为 `deferred`（`deferred_reason: br.* 指令不产生 fault（目标地址低 2 位恒零、不写寄存器/不访存）`）**

5. **`cs.*`（5 个 legality 缺口）的特殊判定**：
   - `cs.n/z/p/eq/ne`（rrrr）受 `rd_dest_rd0`（`rdhb` 为 rd0 → ILLI）和 `dual_dest_same_reg` 约束
   - **判定：补 active legality case**（`rdhb=rd0` → ILLI）

### 判据 B（boundary 缺口）

对每个有 `boundary` ✓ 但无 active boundary case 的 `(insn, format)`：

1. **`add.si-rd`（riii）**：`rdha = rdha + sign_extend(imms18)`。boundary case = 溢出边界（如 `rdha = INT64_MAX, imms18 = 1`）或零值边界。**判定：补 active boundary case**。
2. **`add.si-rb`（riii）**：`rbha = rbha + sign_extend(imms18)`。同理。**判定：补 active boundary case**。

### 判据 O（overlap 缺口）

对每个有 `overlap` ✓ 但无 active overlap case 的 `(insn, format)`：

1. **6 个块赋值**（`rd2rd`/`rd2ra`/`ra2rd`/`rb2rb`/`rd2rb`/`rb2rd`，orri）：
   - 块赋值写入连续寄存器范围。overlap case = 两条块赋值的范围有重叠（如 `rd2rd rd1, rd3, 4` 后跟 `rd2rd rd3, rd5, 4` → `rd3`/`rd4` 被覆盖两次）。
   - **判定：补 active overlap case**（验证重叠写入的最终值 = 最后一次写入）。
2. **5 个 `cs.*`**（`cs.n/cs.z/cs.p/cs.eq/cs.ne`，rrrr）：
   - **实测事实（主会话 2026-09-21 核验，非推测）**：inventory 中这 5 行的 `overlap` 列**已是** `deferred C-27`（见 `tests/vectors/inventory.md:175-179`），但 `validate_vectors.py` **仍把它们报为 gap**（实测 11 条 overlap gap = 这 5 条 + 6 条块赋值）。
   - ⇒ **`validate_vectors.py` 的 gap 检测逻辑把 `deferred <reason>` 声明也计为缺口**，与 `deferred.md` 的消解定义（「降为 `deferred <reason>` 即消解」）**矛盾** ⇒ **这是 validator 的逻辑缺陷，须在本任务修正**（gap 检测应仅对**声明为 `✓` 而无 active case** 者计 gap；`deferred <reason>` / `—` 不计）。
   - **判定**：这 5 条**保持 `deferred C-27`**（不补 case），**修 validator 的 gap 检测逻辑**使其不再计入；修后须验证「gap 计数不含这 5 条」且「既有 597 条零破坏」。
   - ⚠️ 同理须复核：`inventory.md` 中**其它** `deferred <reason>` / `—` 声明是否也被误计（**逐列**核对，不得只改 `cs.*` 一处）。

## 实现方式

### 生成器修改方案

| 生成器 | 覆盖文件 | 当前缺 | 改动 |
|--------|---------|--------|------|
| `tools/testcases/generate_isa_vectors.py` | reg-arith(47)、reg-logic(16)、reg-shift-extend(40)、reg-compare(11)、reg-cond-assign(10)、reg-imm-block(19) | 合计 143 gap | 为每个 `(insn, format)` 追加 legality case（构造触发 fault 的最小 encoding + input_state）；为 `add.si-rd`/`add.si-rb` 追加 boundary case；为 6 个块赋值追加 overlap case |
| `tools/testcases/generate_ctrl_br.py` | ctrl-br(10) | 10 gap | 为每个 `br.*` 追加合法性标注：inventory 降级 ✓ → `deferred <reason>`（不改生成器——br 无 fault） |
| `tools/testcases/generate_ctrl_jump_call_ret.py` | ctrl-jump(1) | 1 gap | 为 `jump-iiii` 追加 legality case（IALIGN/UNMAPPED fault） |

### Legality case 构造规范

每个 legality case 必须包含：
- `class: legality`
- `status: active`
- `expected_fault: <具体 fault 类型>`（ILLI/MALIGN/IALIGN/RASOF/RASUF/UNDI）
- `encoding.word`: 触发该 fault 的**最小有效编码**（可正常解码到该 insn，但操作数违规）
- `input_state`: 使 fault 条件成立的最小预置（如 `rd0` 作为目的不需要预置；除零需要 `rdhd=0`）
- `expected_state: null`（legality 类不产生期望状态）
- `spec_cite`: 引用 `legality_rules.yaml` 对应规则的 `spec_cite`
- `notes`: 说明触发条件（如「rdhb=rd0 → ILLI (rd_dest_rd0)」）

**构造原则**：每条 legality case 只验证**一条** fault 规则（单一职责）。若某 `(insn, format)` 受多条规则约束，可选最**代表性**的一条（如 `rd_dest_rd0` 最通用），或为每条规则各建一条 case。**建议**：优先覆盖最通用的规则（`rd_dest_rd0`），不穷举每条规则——同一文件内相同格式的 insn 共享规则适用性，可用同一 fault 类型。

### 降级操作规范

对判定为「降级」的 `(insn, format)`：
1. 修改 `tests/vectors/inventory.md`：把该行的 `legality` 列从 `✓` 改为 `deferred <reason>`（reason 引用规则 id 或说明）
2. **不改生成器**（无 active case 需要生成）
3. 确保 `validate_vectors.py` 在降级后**不再报该 gap**（`deferred` 声明不计入 gap）

### 门控转严

`010t` 完成后的目标状态：
- `validate_vectors.py` 的 gap 计数 = **0**
- **是否改为阻断**（exit 1）：建议**是**——gap = 0 后，新增的 `✓` 声明必须有对应 active case，否则 exit 1。但此改动需与用户确认（可能影响其它模块的 `make check` 行为）。
- **若保持只报**：gap = 0 时输出 `data coverage gaps: 0`，仍 exit 0——机制到位但不阻断。

## 验收标准

1. **`validate_vectors.py` gap = 0**：`python3 tools/testcases/validate_vectors.py` 输出 `data coverage gaps: 0`（或全部有 `deferred` 理由，给出计数与清单）。**现在可跑。**

2. **独立全量重算**：新增 legality/boundary/overlap case 的期望值（`expected_fault`）须**独立重算**并与产出比对——**不得以 validator 绿灯为唯一判据**：
   - legality case 的 `expected_fault` 是否与 `legality_rules.yaml` 对应规则的 `fault` 字段一致
   - boundary case 的 `expected_state` 是否与 `contract-isa.md` 公式一致
   - overlap case 的 `expected_state` 是否与「最后一次写入为准」一致
   - 方法：可复用/扩展 `009t-audit.py`，或编写新的验证脚本
   - **现在可跑**（有 `contract-isa.md` + `legality_rules.yaml` 作为 oracle）

3. **反例门控**：新增的验证脚本/门控须能对**注入反例**失败：
   - 修改某条新增 legality case 的 `expected_fault` 为错误值 → 验证脚本报 FAIL
   - 修改某条 boundary case 的期望值 → 验证脚本报 FAIL
   - 删除某条新增 active case → `validate_vectors.py` gap 计数增加
   - **现在可跑**

4. **回归：既有 597+ 条向量零破坏**：
   - `git diff tests/vectors/isa/` 核对：既有 case 的内容未被修改（只新增、不改旧）
   - `python3 tools/testcases/validate_vectors.py` 零错误（schema + 覆盖率 + inventory 同步 + mask/value）
   - `python3 tools/testcases/009t-audit.py` 仍 exit 0（Mismatches: 0）
   - **现在可跑**

5. **`inventory.md` 降级有 `deferred <reason>`**：
   - 每处降级（`✓` → `deferred`）都有明确理由，引用规则 id 或既有理由（如 `br.* 无 fault 规则`）
   - 理由可溯源到 `legality_rules.yaml` 或 `contract-isa.md`
   - **现在可跑**

6. **生成器一致性**：修改后的生成器能**完整重新生成**所有向量文件，且重新生成的文件与手动新增的 case 一致（不得出现「手动改了 YAML 但生成器不知道」的情况）。验证方法：运行生成器 → `git diff` 确认产出与任务修改一致。
   - **现在可跑**

7. **`make check` PASS**：`make check` 全绿（含 `validate-vectors`）。
   - **现在可跑**

8. **未自行 commit**。
   - **现在可跑**

## 已知坑 / 教训

1. **`mnemonic` vs `insn`**：向量 YAML 的 `mnemonic` 是基础助记符（如 `add.si`），`insn` 是含 bank 后缀的完整标识（如 `add.si-rd`）。生成器条件须用 `insn` 区分 bank 变体。
2. **legality case 不得有 `expected_state`**：validator F9② 强制 `legality.expected_state == null`。
3. **`br.*` 无 fault**：分支目标 `rb0 + (imm << 2)` 低 2 位恒零（编码保证），不触发 IALIGN。此结论来自 spec `contract-isa.md §5.2`，非实现推断。
4. **`jump-rrii` 可触发 IALIGN**：`rbha + rdhb + (imms12 << 2)` 的低 2 位**不恒零**（取决于寄存器值），可构造 misaligned target。
5. **overlap case 的 `expected_fault` 可为 null 或 ILLI**：validator 允许 `overlap.expected_fault ∈ {null, ILLI}`。
6. **块赋值 overlap 的语义**：重叠写入的最终值 = 最后一次写入（地址高者覆盖低者），`expected_state` 反映最终状态。
7. **`cs.*` overlap (C-27)**：已有 5 条 deferred overlap case。若 validator 仍报 gap，需检查 `deferred` 声明是否被误计入 gap 检测。
8. **生成器重新生成会覆盖既有 case**：修改生成器后重跑会**覆盖**整个 YAML 文件。须确保生成器**包含全部既有 case + 新增 case**，不得丢失 003t~009t 的数据。
9. **F10 守卫**：新增访存 legality case 若涉及 encoding class，须满足 F10（base 非 rb0/rb1/rb2、base 预置且落 RAM）。但 legality case 通常不需要 encoding 级别的构造——重点是 `expected_fault`。

## 参考

- 本项目：`contracts/legality_rules.yaml`（规则目录）、`contracts/opcodes.yaml`（编码表）、`.tao/knowledge/contract-isa.md`（ISA 合约）、`.tao/knowledge/adr-0004-test-machine.md`（测试机地址图）
- 审计记录：`.tao/knowledge/testcases-009t-audit.md`（逐族重推导公式与结论）
- 工具：`tools/testcases/validate_vectors.py`（数据级覆盖门控）、`tools/testcases/009t-audit.py`（独立重推导审计脚本）
- 知识库：`.tao/knowledge/MEMORY.md`、`.tao/knowledge/deferred.md`（第 49–51 行缺口登记）

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（按轮次追加，每次返工新增一轮）
