# m20-llvm-005: swym immu18[17:12] SBZ 的汇编/反汇编同步

**模块**：llvm
**项目里程碑**：M20
**依赖**：无（spec/契约已新；实现先例参考 `m18-spec-007` escape SBZ、`ADR-0044` fence immu18[17:12] SBZ，均已合入，非阻塞）
**可并行分片**：否（LLVM 单写者）
**预估**：2–4 h（含删源树→fetch→apply_series→rebuild 一次；口径：同类 LLVM 组件件含一次全量重建）
**档位**：中改（复核 ≤40 min）
**状态**：待开始
**执行环境**：本地（build-mc / install-host；lit）

## 背景（问题根源 + 已核实事实，自包含）

`swym` 语义已调整：`immu18` 高 6 位为 SBZ，非 0 ⇒ ILLI，LLVM 侧未跟上。当前 `swym 4096`/`swym 262143` 会被汇编器接受并编码出 `immu18[17:12] != 0` 的指令字，该字按 spec 是 ILLI。

**已核实真源（落地前可复验，勿再猜）**：

1. `spec/SimRISC-12-其它指令.md` §2「空转指令」：`swym immu18`，`N = immu18[11:0]`（12 位时延，`0 ≤ N ≤ 4095`，总时延 `1+N` 拍）；`immu18[17:12]` 为 **SBZ，必须为 0，非 0 ⇒ ILLI**。附录 B 合法性表：`encode_sbz` 规则覆盖 `swym_oiii_imm`（SBZ 非零 → ILLI，13 条之一）。
2. `contracts/opcodes.yaml` `swym_oiii_imm`：`opc 0x47`、`ha 0x22`、`mask 0xFFFC0000`、`value 0x47880000`、`fields: immu18 [17:0]`、`legality: immu18[17:12] == 0`、`rule_refs: [encode_sbz]`。**契约/spec 已新，本任务不改**。
3. LLVM 现状（证据，`components/llvm-project/patches/` 真源）：
   - `llvm/lib/Target/DADAO/DADAOInstrInfo.td.patch`：`def swym_oiii : DADAOOiii<"swym">`（约 L1676）`InOperandList = (ins immu18:$imm18)`，**单操作数 immu18（operand 0）**，无谓词/无 SBZ。
   - `llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`：`getImmediateFieldKind` 的 `case 8: // oiii → UImm18`（约 L2043）；`getImmediateFieldRange` 的 `UImm18 = {0, 262143}`（约 L2061），**无** `immu18[17:12]==0` 检查；`checkImmediateRanges` 对 `Op->getImmExpr()` 非空**直接 return false**（符号/可重定位操作数跳过，约 L2084 段）。
   - 同文件**已有 fence 先例**（约 L2417–2430）：`matchAndEmitInstruction` 内 `if (Mnemonic == "fence" && Flat.size() == 3 && Flat[2]->isImm())`，带 `if (!DOp->getImmExpr())` guard，`if (Imm >= 0 && Imm <= 0x3FFFF && (Imm & 0x3F000) != 0)` 报错 `fence: reserved encoding (hb = immu18[17:12] must be zero; see SimRISC-11)`。
   - `llvm/lib/Target/DADAO/Disassembler/DADAODisassembler.cpp.patch`：已有 `hasInvalidEscapeImm`（`escape_ciii` operand 1 `!= 0` ⇒ Fail，`m18-spec-007` 先例，约 L353–362），在 `getInstruction` 中调用返回 Fail 以打印 `<unknown>`；**swym 无对应检查**。
   - `llvm/lib/Target/DADAO/DADAOInstrInfo.cpp.patch`：`getNop()`（约 L793–800）`Nop.setOpcode(DADAO::swym_oiii)` + `addOperand(createImm(0))` = `swym 0`（`0x47880000`），`writeNopData` 亦以该字填充；`immu18[17:12]==0`，**不受影响**。
   - `tests/unit/llvm/lit/MC/DADAO/oiii.s`：正例 `swym 0`、`swym 42`；`tests/unit/llvm/lit/MC/DADAO-gen/gen-oiii.s`：生成物（`generate_lit_vectors.py`，**DO NOT EDIT**）只有 `swym 8`；未见 `swym 4096`/`262143` 负例与反汇编 ILLI 字用例。

**后果**：`swym 4096`（= `0x47881000`，bit12=1）与 `swym 262143`（= `0x478BFFFF`，`immu18[17:12]=0x3F`）当前被接受并编码出 ILLI 字。

## 目标（分条，可验收）

1. **汇编器**：`swym` 立即数在 `[0, 4095]` 内接受；`4096..262143` 报错并给出可理解诊断（指出 `immu18[17:12]` 是 SBZ / 最大 4095），**不得静默截断或掩码**（不得 `& 0xFFF` 吞掉高 6 位）；符号/可重定位操作数路径**不得误伤**——`checkImmediateRanges` 对 `getImmExpr()` 直接 return（跳过），新加的 swym SBZ 检查须与 fence 先例一致地带 `if (!DOp->getImmExpr())` guard，符号操作数留给链接器（swym 立即数本就不可能是符号，但 guard 须与既有风格一致以绝回归）。
2. **反汇编器**：`immu18[17:12] != 0` 的 `0x47..` 字按 `escape` 先例处理——新增 `hasInvalidSwymImm`（`MI.getOpcode()==DADAO::swym_oiii` 且 `operand(0)` 的 `(imm >> 12) != 0` ⇒ Fail），在 `getInstruction` 中 `hasInvalidEscapeImm` 之后调用，返回 `MCDisassembler::Fail` 使上层打印 `<unknown>`；`swym 4095`（`0x47880FFF`）与 `swym 0`（`0x47880000`）仍正常解码。
3. **CodeGen/NOP**：`swym 0`（`0x47880000`）行为不变——`getNop()`/`writeNopData` 生成的 `swym 0` 因 `immu18[17:12]==0` 同时通过新的汇编/反汇编检查；`make test-codegen`、p2align（`p2align-degrees.s`/`p2align-text.s`/`p2align-rodata.s`）相关 lit 不回归。
4. **lit**：新增正例 `swym 0`、`swym 4095`（编码 `0x47880000`/`0x47880FFF`，obj/asm 往返）；负例 `swym 4096`、`swym 262143` 汇编拒绝、`0x47881000` 反汇编 `<unknown>`；负例断言**诊断文本关键片段**（如 `swym: reserved encoding` + `immu18[17:12]`），**不写死行号**。正例建议并入 `tests/unit/llvm/lit/MC/DADAO/oiii.s`（已有 `swym 0`）；负例（汇编拒绝 + `.dd.t32 0x47881000` 反汇编 `<unknown>`）建议新建 `tests/unit/llvm/lit/MC/DADAO/swym-sbz.s`，风格对照 `atomics-fence-imm.s`（echo|%not 负例）与 `cfx2-trap-escape.s`（`.dd.t32` 原始字 → `<unknown>`）。**禁手改** `DADAO-gen/gen-oiii.s`（生成物）。

## 范围（真源与落点）

- **真源** `components/llvm-project/patches/llvm/lib/Target/DADAO/{AsmParser/DADAOAsmParser.cpp,Disassembler/DADAODisassembler.cpp}.patch`（改 patch 源，**不直接改工作源码树**）；`DADAOInstrInfo.td.patch` 仅当确需加谓词/操作数说明时动，否则不动。
- `tests/unit/llvm/lit/MC/DADAO/{oiii.s,swym-sbz.s}`（新/改）。
- `components/llvm-project/changelog.md`（按 M20 追加一条，体例 `check-component-changelog`）。
- 本任务书。

## 约束（硬约束）

1. 独立 worktree（分支 = `m20-llvm-005`）；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`；完成区 ≤30 行、**无运行期路径**（禁 `.work/**`/绝对路径/构建树/安装根/家目录）。
2. 只动上节「范围」列出的文件；**不改** `spec/`、`.tao/contracts/`、`Makefile`、其它任务书、QEMU/RTL/gem5/内核、`DADAO-gen/gen-oiii.s`。**不升版本号**。
3. 组件补丁按 `docs/Process-01` 走重建：删源树 → `make fetch` → `apply_series.py --component llvm-project`（或 `make apply-series`）→ `make build-mc` → `make install-host`；判据 `check-patch-tree` 该组件段 0 problem。
4. 期望值以 `spec/SimRISC-12 §2` + `contracts/opcodes.yaml`（`swym_oiii_imm` / `encode_sbz`）为准，不从现有实现反推。
5. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；源码还原后重建。
6. 术语红线：`bank` = 寄存器组（本任务不涉寄存器组，仅提醒诊断/注释措辞）。

## 验收（逐条贴真实 rc）

1. **修复前复现**：用现成 `llvm-mc`（`echo 'swym 4096' | llvm-mc --triple=dadao-unknown-elf -filetype=obj`）记录 `rc=0` 且编码 `0x47881000`、`swym 262143` 同理；反汇编 `0x47881000` 被误判为合法 `swym`——留真实输出作对照。
2. 修复后：`swym 0`/`swym 4095` 汇编 rc=0 且编码正确；`swym 4096`/`262143` rc≠0 且诊断含 `immu18[17:12]`（SBZ/最大 4095）；`0x47881000` 反汇编为 `<unknown>`。
3. `make check-lit` rc=0；`make test-codegen` rc=0；`make check-patch-tree` 的 `llvm-project` 段 0 problem（整体 rc 可能因并行会话漂移非零，需逐行比基线）；`make check-knowledge-refs` rc=0。
4. **可达 FAIL ≥1 路**：回退（去掉 swym SBZ 检查 ⇒ `swym 4096` 汇编 rc=0 / `0x47881000` 反汇编非 `<unknown>`）注入红，`cp`+md5 还原后回绿——留真实输出。
5. 新增 lit 用例全绿；`check-case-ledger`（若新增 `@@ OBJ:` 身份行）需 `--write` 重生成；`check-component-changelog` rc=0。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
