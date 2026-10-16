# SPEC-145t: 恢复 `rela.si rbHA, imms18`（`riii` / `0x5A` / `auipc` 式 PC 相对）—— `spec/` ISA 恢复 + 编码冻结

**模块**：spec
**项目里程碑**：M8
**依赖**：`ADR-0029`（**`Accepted`**，2026-10-16 用户逐条确认；本册 = `D1` / `D2`（命名编号面）/ `D7①` / `D8` 的**执行落点**）、`ADR-0012 D5`（**被本册回退**的删除项：`rela.si` → UNDI、`254 → 253`、M1 `177 → 176`）、`ADR-0003`（`rela.si` **旧口径**：PC 低 12 位清零 / 4 KB 页对齐 —— **本册不回退该口径** ✗，见「接口规范」）、`SPEC-057t`（历史删除任务）、`SPEC-142t`/`SPEC-143t`（同改 `contracts/opcodes.yaml` / 生成区 / 向量的**近例**，各自与前置串行）；**串行链**：本册 → `LLVM-095t`（前置 = 本册编码冻结）→ `QEMU-061t`（`AGENTS.md`「同改共享文件一律串行」）；`ISS-230`（本册 = 其缺口的**编码面**起点）；纪律 = `docs/Process-06`（`spec/` 只读册哈希锁）、`docs/Process-05`（L1 编码向量）、`docs/Process-01`（补丁树，本册**不涉**）
**状态**：待开始

> **本册边界** ✗：只做 **`spec/` + 机器可读编码数据（`contracts/`）+ 生成器 + L1 编码向量 + 哈希锁**；**不含** LLVM / lld / CodeGen 改动（归 `LLVM-095t`）✗、**不含** QEMU 解码 / 语义（归 `QEMU-061t`）✗、**不建**重定位类型（`PCREL_HI`/`PCREL_LO` 归 `LLVM-095t`，本册只冻结**汇编/编码面**）✗。

## 执行环境
**执行环境**：本地

## 用户授权（原话，**逐字**，先读）
- 用户裁定（2026-10-16，渠道 = 经主会话问答）：
  > 「**现在就换！rela.si rbHA, imms18，含义参照risc-v的auipc，编码0x5A；刚才所作的任务回退**」
- **授权范围** = **`rela.si` 这一条指令的恢复**（助记符 / `riii` 格式 / 语义「含义参照 `auipc`」/ 编码 `0x5A`）✓；**不含**其它 ISA 改动 ✗（`ADR-0029 D8`）。
- 依据链：`ADR-0029 D8`（只引录授权、**实际改动归 `D7①` 任务阶段**）⇒ **本册即该任务阶段** ✓。
- `docs/Process-06 §2`：**`spec/` 授权原话须原样写入完成区**（含本册所改只读册清单）⇒ 完成区须复录上句原话。

## 接口规范

- **输入**：`ADR-0029 D1`（编码 / 语义）、`D8`（授权）；现状 `spec/`（`0x5A` = QFC 主表空白单元格 ⇒ UNDI）；`ADR-0012 D5`（删除口径：`0x5A` 保留但不再指派、`254 → 253`、M1 `177 → 176`）。
- **输出（本册冻结的编码/语义契约）**：
  - 助记符 / 格式：**`rela.si rbHA, imms18`**、**`riii`**（`op8 = 0x5A` + `ha[23:18]` + `imms18[17:0]` = 8 + 6 + 18 = 32 位，字段位与 `add.si` 同族）。
  - 编码：**`op = 0x5A`**（`ADR-0012 D5` 的保留位 ⇒ **不占新编码位** ✓）、`mask = 0xFF000000`、`value = 0x5A000000`（判据 = `add.si` 两形态的**同族现成**写法：`add.si_riii_rd` = `0x59` / `add.si_riii_rb` = `0x5B`）。
  - 语义：**`rbHA = PC + (sign_extend(imms18) << 12)`**（`<< 12` = 4 KB 块、**无 `<< 2`**）；**`PC` = `rela.si` 指令自身地址**（= `rb0` 读出值，**非下一条**；`ADR-0019 D3` / `contract-isa.md §1.3.2`）；**PC 低位不清零** ✓（**明确取代** `ADR-0003`/`ADR-0012 D5` 前身的「PC 低 12 位清零 / 4 KB 页对齐」口径 ✗）；`imms18` **有符号**。
  - 合法性：目的 `ha` 为 `rb0` ⇒ **ILLI**（= 既有 `dst_rb0` 规则；同形先例 = `add.si_riii_rb`、`ld.o`/`ldm.o` 的 `rbHA`）。
  - `scope` = **`m1`**（`rela.si` 删除前为 M1 身份集成员；`ADR-0012 D5` 的 `177 → 176` 随之回退）。
- **约束**：**不得**触碰 `rela.si` 之外的 ISA 条目 ✗；**不得**改 `ADR-0003` / `ADR-0012 D5` 的**已写正文** ✗（以**新增变更记录条目 / 本 ADR 指向**承载，`docs/Process-03`）；本册**不涉**寄存器模型 / opcode 空间 / 其它指令 ✓。

## spec/ 待改文件清单（**architect 只读现场核过**，2026-10-16；执行时逐条复核）

| # | 文件 | 改动（现场核过的落点） |
|---|---|---|
| 1 | `spec/SimRISC-00-指令系统设计.md` | **QFC 主表**：行 `0101-1xxx` × 列 `xxxx-x010`（= `op 0x5A`）现为**空白**（UNDI）⇒ 填 **`rela.si_riii_rb`**（现场佐证：同行列 `xxxx-x001` = `add.si_riii_rd`(`0x59`)、`xxxx-x011` = `add.si_riii_rb`(`0x5B`)）+ **附录「版本与变更记录」**`0.5.5-rc` 段追加条目（**不改**既有「全量删除 `rela.si`」行 ✗） |
| 2 | 归册正文（**分类由生成器机械派生**，见 #8） | `rela.si` 应归 **`64位地址运算`**（`SimRISC-05`）⇒ `spec/SimRISC-05-64位地址运算.md`：册头分类计数「（**5** 条）」→ **6 条**、`§3` 地址加减正文补一条（语义 / `PC` 基准 / 目的 `rb0` ⇒ ILLI）、`ASSEMBLY_LIST` + `LEGALITY` 生成区重生成、附录追加条目。**注意**：若**不改** #8 的分类规则，生成器会把 `rela.si` 归 **「其它」**（`SimRISC-11`）⇒ 与手写正文**冲突**、`check-asm-list` **FAIL** ⇒ **归册与 #8 必须同一变更内对齐** ✓ |
| 3 | `spec/Toolchain-01-汇编语言.md` | 汇编语法：`riii` 形态表（`§` 格式类语法）补 `rela.si rbHA, imms18`（`§` 现表已含 `riii` 的 `助记符 dst, imm` 形，**现场核** 是否需单列立即数单位 = 4 KB）+ 变更记录追加条目（**不改**既有「全量删除 `rela.si`」历史条目 ✗）；该册**在哈希锁内** ⇒ 同变更重算 `sha256` |
| 4 | `spec/SimRISC-06-控制流.md` / `spec/SimRISC-12-待定.md` | 两册**变更记录**含「删 `rela.si`」行（现场核：`SimRISC-06:167`、`SimRISC-12:130`）⇒ **不改历史行** ✗，仅在未发布段（`0.5.5-rc`）**追加**回退条目（**现场判断**是否必要；若正文/生成区无 `rela.si` 相关内容则**不动**该册） |
| 5 | `spec/README.md` | 索引 / 投影表：现场核是否有需同步处（本册**非哈希锁内**，但 `docs/Process-06 §2` 仍要求事先授权 ✓ —— 授权原话见上）；**无实质需改则不动** ✗ |
| 6 | `contracts/opcodes.yaml`（**机器可读，生成物**） | 由 `python3 tools/spec/generate_opcodes.py` **重生成**：新增 `rela.si_riii_rb` 记录（`mnemonic` / `format: riii` / `op` / `mask` / `value` / `fields`（`rbha` dst bank rb + `imms18` imm signed）/ `legality: rbha != rb0` / `spec_cite: SimRISC-05 §…` / `scope: m1` / `rule_refs: [dst_rb0]`）；**头部计数自动派生**：「共 **234** 条：M1 **155** …」→「共 **235** 条：M1 **156** …」 |
| 7 | `.tao/contracts/contract-isa.md`（**叙述合约**） | QFC 主表投影 / 指令表 / `dst_rb0` 清单同步（现场核 `§2.x` 与附录 A 的对应节）—— 与 `ADR-0019 D10` 的「叙述合约随 spec 同步」口径一致 |
| 8 | `tools/llvm/gen_asm_list.py`（**分类真源**，被 `tools/spec/gen_legality_list.py` **复用**） | **`classify()`** 现对 `rela.si` 会落到 `其它`（现场核：判据链无 `rela` 分支）⇒ 须**显式归 `64位地址运算`**（与 `add.si` 同族处理，如 `m == "rela.si"` 分支）；改动后**重生成**各册 `ASSEMBLY_LIST` / `LEGALITY` 嵌入区 |
| 9 | `tools/spec/gen_legality_list.py` | 文件头计数文案「`opcodes.yaml` -- **234** entries, **198** with `rule_refs`」（现场核：docstring 写死）⇒ 随 #6 更新为 **235** / **199** |
| 10 | `manifests/spec-readonly.lock.toml` | **同一变更内**重算**所改只读册**的 `sha256`（`docs/Process-06 §5`；至少含 `SimRISC-00`、`SimRISC-05`、`Toolchain-01`，按实际所改册逐一）+ 追加一行变更说明注释（体例照既有条目） |
| 11 | `tests/vectors/isa/reserved.yaml` | **Case 2**（`tests/vectors/isa/reserved.yaml:37-51`）现断言 **`0x5A` ⇒ UNDI**（`word: "0x5A040001"`）⇒ 该编码**已成为合法指令** ⇒ 改指向**另一个仍为空白**的 QFC 单元格（**现场派生**保留编码，禁按记忆挑） |
| 12 | `tests/vectors/isa/reg-imm-block.yaml`（**或**新向量文件，**现场定**） | 新增 **L1 编码向量**：`op 0x5A` 的**编码往返**（`value`/`mask`/`ha`/`imms18` 逐字段）+ **目的 `rb0` ⇒ ILLI**（`dst_rb0`）+ **`imms18` 有符号**（正 / 负各 ≥1 例）+ 4 KB 单位（`<<12`）记录；`tests/vectors/inventory.md` 同步 |
| 13 | 门控（**一般无需改代码**，须现场跑通） | `check-asm-list` / `check-asm-list-drift` / `check-legality-drift` / `validate-encoding` / `check-qfc-coverage` / `check-spec-readonly` / `check-spec-changelog` / `check-spec-numbering` / `validate-vectors` 全绿 |

## 指令计数（`ADR-0029 D7①` 口径 + **architect 现场核**）

- `ADR-0012 D5` 的 **`254 → 253`** 须回退为 **`253 → 254`**（M1 `176 → 177`）。**落点现场核**（`ADR-0029 D7①` 明示「实际计数落点以任务阶段的现状为准」）：
  - `spec/` 内**无** `253` / `254` 字面量（现场 `grep` 已核）；`254 条` 的现存字面量只在 `components/llvm-project/changelog.md`（**历史记录**、**不改** ✗）。
  - **机械可核的现行计数** = QFC 表条目数 **234**（`python3 tools/spec/check_qfc_coverage.py` 现场派生：`QFC 指令数: 234` / `YAML 指令数: 234`）⇒ 恢复 `rela.si` 后 = **235**（= `contracts/opcodes.yaml` 头部计数 + `SimRISC-05` 册头分类计数 5 → 6 之和的口径一致）。
  - ⇒ **完成区**须同时给出：`234 → 235`（机械派生，命令 + 输出）与「`ADR-0012` 的 `254 → 253` 回退为 `253 → 254`」的制度性说明（后者无字面量落点，只作口径交代；**不回改** `ADR-0012` ✗）。

## 验收标准

1. **编码冻结可核（L1，独立 oracle = 编码表，不从实现反推）**：`rela.si` 在 `contracts/opcodes.yaml` 中 `op = 0x5A` / `mask = 0xFF000000` / `value = 0x5A000000` / `format = riii` / `legality: rbha != rb0` / `scope: m1`；`python3 tools/spec/validate_encoding.py` rc=0；**逐字段**可核（`ha` = `[23:18]`、`imms18` = `[17:0]` signed）。
2. **规范 ↔ 数据双向一致**：`python3 tools/spec/check_qfc_coverage.py` ⇒ `QFC 指令数: 235` / `YAML 指令数: 235` / `差异总数: 0`（**现场输出**贴完成区）。
3. **生成区零漂移**：`check-asm-list` / `check-asm-list-drift` / `check-legality-drift` **rc=0**（判据 = 生成器产物与 `spec/` 嵌入块**逐字节**一致；`rela.si` 出现在 `SimRISC-05` 而非 `SimRISC-11`）。
4. **只读册哈希锁同步**：`make check-spec-readonly` rc=0；锁内**仅所改册** `sha256` 变化（`git diff manifests/spec-readonly.lock.toml` 与所改册清单**逐条对齐**）。
5. **向量**：`tests/vectors/isa/reserved.yaml` 中原 `0x5A ⇒ UNDI` 用例已改指向（**新目标现场派生**）；新增 `rela.si` 编码向量通过 `make validate-vectors`；**目的 `rb0` ⇒ ILLI** 与 **负立即数** 用例各 ≥1（**可达 FAIL**）。
6. **变更记录齐备**：所改各册「附录：版本与变更记录」`0.5.5-rc` 段有对应条目；`check-spec-changelog` / `check-spec-numbering` rc=0。
7. **一键证据**：`.work/evidence/<任务ID>/run.sh` 跑通并留 `.work/log/spec/SPEC-145t-*.log`；含**反例注入**（如把 `op` 改成 `0x58` ⇒ `check_qfc_coverage` / `validate-encoding` 应 **FAIL** ⇒ 还原 ⇒ 回绿；还原用 `cp` 备份 + md5 对账，**禁** `git checkout`/`restore`/`stash`）。
8. **L1 全绿**：`make check` rc=0；`check-patch-tree` / `check-index-blobs` / `check-knowledge-refs` / `check-no-residue` rc=0。

> **验收前预检（`AGENTS.md`「下发前预检（强制）」）**：本册逐项标注「现在可跑」；**唯一 BLOCKED 项 = 无**（`spec/` 授权原话已在手 ✓、编码齐备 ✓、计数口径已现场核 ✓）；**须主会话在 `/dispatch` 前把「拟改文件 × `spec/` 清单」逐条对照授权原话**（命中 `spec/` 而有授权即放行）。

## 前置申报
- **不涉**组件重建 ✗（**不改** `components/**`）⇒ **不跑** `install-host` / `build-*`；`ISS-229`（重建串行）本册**不适用**；若执行中与其它会话的 L2/L3 撞车，按 `ISS-229` 纪律**串行**。
- **改 `spec/` ⇒ 授权先行** ✓（原话见上「用户授权」；授权原话须落完成区）。
- **本册触 `tools/llvm/gen_asm_list.py`**（`llvm` 模块目录下的 **spec 侧投影生成器**）⇒ 与 `LLVM-095t` **串行**（本册在前 ✓，见「依赖」）；改动为**单一分类分支**、**不涉** MC/`.td` ⇒ **无需** `install-host` ✓。
- 长任务（>10 min）由**主会话** `setsid nohup` 脱离 + 落 `XXX_EXIT=$rc`；本册预期**无**长任务（全为静态生成 + 向量校验）。

## 不做项（显式）
1. **LLVM / lld / CodeGen / MC** 任何改动 ✗（归 `LLVM-095t`）；**重定位类型**（`PCREL_HI`/`PCREL_LO`）✗（归 `LLVM-095t`）。
2. **QEMU** 解码 / 语义 ✗（归 `QEMU-061t`）。
3. **改 `ADR-0003` / `ADR-0012 D5` / `ADR-0019` / `ADR-0026` / `ADR-0028` 的已写正文** ✗（回退留痕以**新增条目 / 注记 / 指向**承载）。
4. **回退旧「PC 低 12 位清零 / 4 KB 页对齐」语义** ✗（用户裁定「参照 `auipc`」= **PC 不清低位**）。
5. 其它 ISA 条目 / 寄存器模型 / opcode 空间改动 ✗；`rela.si` 之外的 `0x5A` 邻位（`0x58`/`0x5C`…）改动 ✗。
6. `ISS-222` / `ISS-223` 收口 ✗（撞上即登记 + 转出，**不得**静默跳过）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
