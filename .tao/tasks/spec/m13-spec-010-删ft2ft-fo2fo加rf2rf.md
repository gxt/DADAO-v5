# m13-spec-010: 删除 `ft2ft`/`fo2fo`、新增 `rf2rf`（OPC-octa / opx `111-100`）；「单精写入宽度」归位

**模块**：spec
**项目里程碑**：M13
**依赖**：**等 M12 收尾**（`m12-integ-002` 验证通过）后再开工——用户 2026-11-14 明示「影响面比较大，等 M12 收尾后再进行」
**可并行分片**：否（ISA 变更，spec/契约/实现/测试须同批次对齐）
**预估**：spec 侧 3–5 h（实现/测试另立任务）
**状态**：待开始（**挂起**，见「依赖」）

## 用户裁定（2026-11-14，原话）

> 「M13增加：删除ft2ft和fo2fo，增加rf2rf，opc为OPC-octa，opx为111-100；该指令描述放到SimRISC-02中，和rf2rd/rd2rf在一起；注意：该指令不能用rf0做目的操作数，否则ILLI，其它限制参考 寄存器组之间块赋值 的其它指令。此外，**单精（ft）结果的写入宽度** 这部分说明需要保留，应该放在SimRISC-00的2.3，以及SimRISC-07的最头上。这部分改动，影响面比较大，等M12收尾后再进行」

## 目标（spec 侧）

1. **删除** `ft2ft`、`fo2fo` 两条指令（ID、编码、语义段、汇编助记符），其 `opx` 槽位处置见「待裁定」。
2. **新增** `rf2rf`：
   - 编码：`opc = OPC-octa`、`opx = 111-100`（`ha = 0x3C`）；操作数形式与 `rf2rd`/`rd2rf` 同族（`orri`，`rf` 组）；
   - 语义：**rf 组内块复制** `rf2rf {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}`（源 `rfHC` 起、目的 `rfHB` 起，各 `immu6` 个）；
   - 限制（沿用 §1 寄存器组块复制族）：`immu6` = 0 ⇒ ILLI；起始 + `immu6` > 64 ⇒ ILLI；源/目的范围**任何重叠** ⇒ ILLI；**目的含 `rf0` ⇒ ILLI**（用户显式，注意与 `rd2rf` 允许 `rf0` 作目的不同）；`rf0` 作**源**按现有规则（读出完整 64 位，`rd2rf`/`rf2rd` 的注已写）。
   - 位置：`spec/SimRISC-02-寄存器复制.md`，紧跟 `rf2rd`/`rd2rf`；同步其 §1 分类计数、§表格、合法性清单（`dst_rf0`/`mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap` 等规则覆盖）。
3. **「单精（ft）结果写入宽度」保留并归位**：
   - 全文搬入 `spec/SimRISC-00` **§2.3 浮点寄存器**（作为 rf 组写语义的一部分）；
   - `spec/SimRISC-07` **最头上**（§1 之前、规范性引用之后）保留一份**同等效力**的说明（或明确指针 + 关键句），因为它是浮点册的写宽总则；
   - 判据不变（ft 结果族只写低 32、高半保持；例外：`rd2rf`/`rf2rd` 整 64 位、`cs.*` 整 64 位），但**删掉对 `ft2ft`/`fo2fo` 的引用**（它们已删除），改为「rf 组块复制 `rf2rf` 整 64 位逐位复制」。

## 影响面清单（现场 grep，非全部逐条核）

- **spec**：`SimRISC-07`（复制类、写宽段、编码表、NaN 不适用清单）、`SimRISC-02`（分类、语法、限制、表格、合法性清单）、`SimRISC-00`（§2.3、编码主表/子表、附录变更记录）、`SimRISC-03`/`Toolchain-01`/`DADAO-12`（提及处）。
- **契约**：`.tao/contracts/contract-fp.md`、`contract-isa.md`、`contract-asm.md`、`contract-asm-list.md`；`contracts/opcodes.yaml`（`ft2ft_orri_rf`/`fo2fo_orri_rf` 删除、新增 `rf2rf` 条目）、`legality_rules.yaml`（`dst_rf0` 等规则覆盖新 id、删旧 id）、`fp_semantics.yaml`。
- **讲义**：`docs/DDLN/A-指令系统/DD-A009`（浮点运算）、`DD-A002`（指令编码）。
- **实现**（另立任务，逐组件）：LLVM `.td`/MC（编码 + 助记符）、QEMU（`insn.decode`/`trans_*`）、gem5（解码表 + exec）、chipyard RTL（译码/执行）。
- **测试**：`tests/inst/07-floating-point/`（`ft2ft_orri_rf.S`/`fo2fo_orri_rf.S` 删除或改指 `rf2rf`）、`tests/inst.yaml`、`case-ledger`、`tests/inst/inventory.md`、`MIGRATION.md`；`check-inst-asm` 264 id → 263 id（删 2 加 1）。
- **矩阵/工具**：`tools/testcases/generate_lit_vectors.py`、`validate_mc_vectors`、`min_rom_probe_036t.py` 等提到 `ft2ft`/`fo2fo` 的地方。

## 验收（spec 侧；实现/测试任务另立后各自验收）

1. 旧指令归零：`grep -rn "ft2ft\|fo2fo"` 在 `spec/`、`.tao/contracts/`、`contracts/`、`docs/DDLN/` 内 0 命中（`.tao/adr/`、`.tao/archive/` 历史保留）。
2. 新指令在位：`SimRISC-02` 有 `rf2rf` 语法/语义/限制/表格行；`contracts/opcodes.yaml` 有 `rf2rf` 条目（`opc=OPC-octa`、`ha=0x3C`、`orri`/`rf`、`dst_rf0 ⇒ ILLI`）；`legality_rules.yaml` 的规则覆盖新 id。
3. 单精写宽说明在 `SimRISC-00 §2.3` 与 `SimRISC-07` 开头各一份（或一处正文 + 一处指针），判据与今天一致；不再引用已删指令。
4. 编码不冲突：`opcodes.yaml` 全量 id 的 `mask/value` 两两不重叠（机械核）；`check-isa-coverage` 计数一致。
5. 门控 rc=0：`check-spec-readonly`（锁同笔重算改动册）、`check-spec-changelog`、`check-spec-purity`、`check-spec-refs`、`check-asm-list`、`check-asm-prose`、`check-rule-refs`、`check-legality-drift`、`check-legality-invariants`、`check-spec-cite-targets`、`check-spec-numbering`、`check-knowledge-refs`、`check-isa-coverage`。
6. ≥2 路可达 FAIL 注入（`cp`+md5 还原）。
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 待裁定（开工前需用户确认）

1. **`ft2ft`/`fo2fo` 的两个 `opx` 槽位如何处置**：保持空置（⇒ reserved 编码，执行 `UNDI`）？还是留给后续指令？
2. **`rf2rf` 语义确认**：rf→rf 块复制、源可为 `rf0`、目的含 `rf0` ⇒ ILLI、`immu6` 1..63、禁源/目的重叠——是否如上？
3. **实现与测试是否同批**：本次是否只落 spec/契约（实现与测试另立任务、随后跟进），还是要求一次性全绿（4 个实现 + 测试都要改，工期显著变长）。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host`/`check-modules`/`build-*`**（spec 侧不需要构建）。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. `spec/` 正文禁止任务号/ADR/ISS 号；变更记录只写判据句。
5. 大文件落 `/tmp/opencode/m13-spec-010/` 并测完即删。

## 审阅记录

（待填）
