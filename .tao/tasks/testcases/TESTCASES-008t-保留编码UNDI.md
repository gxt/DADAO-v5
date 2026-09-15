# TESTCASES-008t: 保留编码 → UNDI 的向量层表达（F5）

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-002t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `.tao/knowledge/contract-isa.md` §2.9（保留编码）、§8.2（UNDI）、§8.3（全零字 → ILLI）、§9（fault 枚举）、附录 QFC 表
  - `spec/SimRISC-00`（QFC 主表 + MISC-byte/wyde/tetra/octa 子表的空白单元格 = reserved）、`spec/SimRISC-04`（非法指令）
  - `contracts/opcodes.yaml`（仅含**已定义**编码；保留编码**不在其中**，无 `(insn, format)` 身份）
  - `tests/vectors/schema.md`、`tests/vectors/inventory.md`（`TESTCASES-002t` 返工后版本，schema 契约）
  - `tools/testcases/validate_vectors.py`（`TESTCASES-002t` 返工后版本；检查 7/8 要求 `(insn, format)` 存在且 `(word & mask) == value`）
- 输出（**本任务拥有的文件**）：
  - `tests/vectors/schema.md`：保留编码 case 的表达规范（字段/约束/枚举）
  - `tools/testcases/validate_vectors.py`：保留编码 case 的校验分支（豁免检查 7/8，改为校验「确属保留编码 + `expected_fault: UNDI`」）
  - `tests/vectors/isa/reserved.yaml`（文件名由本任务确定）：≥1 条 active 的「保留编码 → UNDI」向量
  - `tests/vectors/inventory.md`：记录 UNDI 覆盖方式
- 约束：
  - **不得**把保留编码塞进 `contracts/opcodes.yaml`（该文件是已定义编码 oracle，**不改**）
  - **不得**伪造 `(insn, format)` 身份使检查 7/8 假通过
  - `expected_fault` 必须为 `UNDI`；`word` **不得**为 `0x00000000`（全零字 → `illi` → ILLI，见 §8.3）
  - 设计须能表达「该 word 在 QFC/MISC 子表中为空白单元格」
  - 完成后不自行 commit

## 问题根源

`TESTCASES-002t` 复核（F5）确认：**`UNDI` 在向量层不可表达**。

- taxonomy 要求 `legality` 覆盖全部动态/静态 fault，含 `UNDI`；
- 但 `UNDI` 的触发条件是「执行**保留编码**（QFC/MISC 子表空白单元格）」（`contract-isa.md` §2.9/§8.2）；
- `contracts/opcodes.yaml` 只含**已定义**编码，保留编码**没有** `(insn, format)` 身份；
- 而 validator 检查 7（`(insn, format)` 必须在 `opcodes.yaml` 中）与检查 8（`(word & mask) == value`）对该类 case **无法满足**——保留编码的 word 必然不匹配任何已定义记录的 mask/value。
- 结果：`UNDI` 无任何向量可挂靠，`002t` 只能将其登记为遗留，taxonomy 的 fault 覆盖出现缺口。

## 目的

为「保留编码 → UNDI」建立**可表达的向量层契约**并落地实现，使 `UNDI` 成为可 `make check` 门控的一等 fault 类，消除 F5 缺口。

## 对照关系

- **借鉴**：0628 的向量 taxonomy 同样以 `legality` 承载 fault；但 0628 未处理「保留编码无身份」问题。
- **差异**：v5 明确「`UNDI` = QFC/子表空白单元格」（§2.9/§8.2），与 `ILLI`（全零字、SBZ 违规、非法操作数）严格区分（§8.3、ADR-0004 Rationale「SBZ → ILLI 而非 UNDI」）。故表达必须**显式标记 reserved**，不能靠 word 碰巧不匹配来推断。
- **拒绝的做法**：把保留编码 word 当作「不匹配任何 mask/value」的普通 case（会被检查 8 判错）；给保留编码编造 `insn`；把 `UNDI` 归入 `ILLI`。

## 设计方案（已定，轻量记录，不立 ADR）

> **方案取舍（已裁定）**：两条路线——**(a) 扩展 schema/validator 支持保留编码** vs **(b) 不扩展，交 harness 直接覆盖**。
> - **(b) 否决**：`UNDI` 是 taxonomy 明列的 spec fault（`contract-isa.md` §8.2/§9），若不在向量层表达，则 `make check` 门控对 UNDI **零覆盖**，与「taxonomy 覆盖全部 fault」目标冲突；且 harness 侧覆盖不可由 validator 机械校验，缺口不可见。
> - **(a) 选定**：在 schema/validator 内显式表达「保留编码 → UNDI」，使其成为可 `make check` 门控的一等 fault 类。改动限定在 `tests/vectors/` 与 `tools/testcases/`（v5 内部模块间格式约定），非外部契约、非不可逆 → 按 `adr-authoring.md` **不立 ADR**，以本任务书记录为准。
> - **(a) 的子方案**：采用**主选方案 A**（复用 `class: legality` + 显式 `encoding.reserved: true` 标记）；否决 B（新增 `class: reserved`，扩 taxonomy、影响下游消费者）与 C（哨兵 `insn: "<reserved>"`，引入假身份，违反「不得伪造身份」）。

**主选方案 A（选定）**：复用 `class: legality`，新增显式标记字段。

```yaml
- class: legality
  encoding:
    word: "0x????????"     # 非全零；QFC/子表空白单元格对应的 32-bit word
    reserved: true         # 显式声明：该 word 是保留编码（非 opcodes.yaml 记录）
  mnemonic: null           # 无已定义助记符
  insn: null               # 无身份
  format: "<子表所在格式>" # 或 null；用于定位该空白单元格
  input_state: {}
  expected_state: null
  expected_pc: null
  expected_fault: UNDI
  status: active
  spec_cite: "SimRISC-00 §SimRISC QFC / SimRISC-04 §非法指令"
  notes: "<该编码在 QFC/子表中的位置 + 判定为 reserved 的依据>"
```

- validator 分支：当 `encoding.reserved == true` 时——① 跳过检查 7/8；② 强制 `expected_fault == "UNDI"`、`class == "legality"`、`status == "active"`；③ 强制 `word != 0x00000000`；④ 要求 `notes`/`spec_cite` 给出 reserved 依据。
- 覆盖率：该 case **不**参与 `(insn, format)` 覆盖率门控（无身份），但 `UNDI` 覆盖须由 inventory 显式登记。

**备选方案 B（否决）**：新增 `class: reserved`（taxonomy 扩展），字段同上。
**备选方案 C（否决）**：哨兵身份 `insn: "<reserved>"` + 真实 `format`，validator 白名单该哨兵。

方案取舍（已裁定）：**选 A**——改动最小、复用 `legality` 语义；B 语义最清晰但扩 taxonomy、影响下游 schema 消费者；C 最省 validator 改动但引入「假身份」，与「不得伪造身份」冲突。

## 任务分解

- 任务清单：`TESTCASES-008t`（本任务，含 schema/validator/向量落地）
- 分解理由：F5 是单一契约缺口，设计 + 实现耦合紧密，不宜再拆，一次实现。
- 依赖关系：依赖 `TESTCASES-002t`（需其返工后的 schema 与 validator 基线）；与 `003t`~`007t` 无文件冲突，可并行；但须在 `009t`（全量审计）之前完成。

## 已知坑 / 结论

1. **全零字不是 UNDI**：`0x00000000` 是 `illi` → **ILLI**（§8.3）；UNDI 用例必须避开全零字。
2. **不得伪造身份**：用 `(insn, format)` 假身份绕过检查 7/8 会破坏 `opcodes.yaml` 作为唯一编码真相的原则。
3. **QFC 空白单元格定位**：须给出该 word 在 QFC 主表/子表中的具体位置（行/列或 minor-op 区间）作为 reserved 证据，不得凭「不匹配」推断。
4. **下游同步**：若采用方案 A/B，须同步 `llvm`/`qemu`/`integ` 对向量 schema 的消费（登记跨模块影响）。

## 参考

- 本项目：`.tao/knowledge/contract-isa.md` §2.9/§8.2/§8.3/§9、`spec/SimRISC-00`（QFC）、`spec/SimRISC-04`（非法指令）、`tests/vectors/schema.md`、`tools/testcases/validate_vectors.py`
- 知识库：`.tao/knowledge/MEMORY.md`、`.tao/knowledge/deferred.md`

## 验收标准

1. 保留编码的表达规范写入 `tests/vectors/schema.md`（字段、约束、`UNDI` 枚举用法、与 `ILLI` 的区分）
2. `tools/testcases/validate_vectors.py` 支持保留编码 case：豁免检查 7/8，强制 `class=legality`/`expected_fault=UNDI`/`status=active`/`word != 0`；对违反者报错并 exit 1
3. `tests/vectors/isa/reserved.yaml` 含 ≥1 条 active「保留编码 → UNDI」向量，`notes`/`spec_cite` 给出 QFC/子表位置依据
4. `tests/vectors/inventory.md` 登记 UNDI 覆盖方式（无身份，显式说明）
5. `contracts/opcodes.yaml` 未被修改
6. 反造假：在 `/tmp/opencode/TESTCASES-008t/` 副本注入错误（保留 case 的 fault 改为 null/ILLI、`reserved: true` 但 word 匹配已定义记录、word=0），validator 全部捕获并 exit 1
7. `python3 tools/testcases/validate_vectors.py` 零错误；`make check` PASS
8. 方案 A 的取舍已在本任务书记录（不立 ADR）；未新增 `.tao/knowledge/adr-*.md`
9. 未自行 commit

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（待填写）

### 第 1 轮 reviewer 验收
（待填写）
