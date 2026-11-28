# m20-llvm-005: swym immu18[17:12] SBZ 的汇编/反汇编同步

**模块**：llvm
**项目里程碑**：M20
**依赖**：无（spec/契约已新；实现先例参考 `m18-spec-007` escape SBZ、`ADR-0044` fence immu18[17:12] SBZ，均已合入，非阻塞）
**可并行分片**：否（LLVM 单写者）
**预估**：2–4 h（含删源树→fetch→apply_series→rebuild 一次；口径：同类 LLVM 组件件含一次全量重建）
**档位**：中改（复核 ≤40 min）
**状态**：已验证
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

**测试结果**：`test-codegen` rc=0（19/19）；`check-lit` rc=2（183/187；红 4 项为基线 `DADAO-E2E::smoke_{arith,add,fp,jump}.test`，见遗留问题；MC+CodeGen 子集 165/165 rc=0）；`check-patch-tree` llvm-project 99 patch/0 problem（整库 rc=1，92 problem 全在其它组件在途项）；`check-case-ledger` rc=0（5882 条）；`check-component-changelog` rc=0；`check-knowledge-refs` rc=0。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/{AsmParser/DADAOAsmParser.cpp,Disassembler/DADAODisassembler.cpp}.patch`（源树经 `make_patch.py` 重导出，2 written/97 unchanged）；`components/llvm-project/changelog.md`；`tests/unit/llvm/lit/MC/DADAO/oiii.s`（+`swym 4095`）、`swym-sbz.s`（新增）、`imm-range.s`（原正例 `swym 262143` 改为 `swym 4095`，语义变更的必然同步）；`tests/case-ledger.tsv`（`--write`）；本任务书。
**验收结果**：
1. pre-fix 快照（md5 `609b72a8…`）：`swym 4096` rc=0 编码 `47 88 10 00`、`262143` rc=0 编码 `47 8b ff ff`；`0x47881000` 反汇编 `swym 4096`。
2. 修复后：`swym 0`→`0x47880000`、`swym 4095`→`0x47880FFF` 均 rc=0；`swym 4096`/`262143` rc=1、诊断含 `swym: reserved encoding (immu18[17:12] is SBZ … at most 4095 …)`、不产 `.o`；`262144`/`-1` 仍 `immediate out of range`；`0x47881000`/`0x478BFFFF` 反汇编 `<unknown>`，`0x47880FFF`/`0x47880000` 正常解码。
3. 重建按 Process-01：删源树→fetch（llvm 到 base）→`apply_series --component llvm-project`（99 applied）→`build-mc` rc=0→`install-host` rc=0；安装根与构建树 `llvm-mc` md5 同 `227e2f8c…`、`llvm-objdump` 同 `e10f32b3…`。
4. 可达 FAIL（运行期证据目录 `run.sh --inject` rc=0）：注入 A 关掉 SBZ 判据、注入 B 上限放宽到 4096 ⇒ `build-mc-lite` rc=0 且 `swym-sbz.s` lit rc=1；`cp`+md5 还原（md5 相等、源树 `git diff` 空）重建后 rc=0；pre-fix 快照跑同 lit rc=1。
**新发现/坑**：① 新 worktree `.cache` 未软链主仓，`make fetch` 会重建 13 个组件 bare 镜像（含联网 chipyard/gem5），单组件任务宜在 llvm 源树就绪后中断或先软链；② SBZ 判据须在 `matchAndEmitInstruction`（匹配前）：`checkImmediateRanges` 的 `UImm18` 与 fence/trap 共用 `[0,262143]`，改范围会误伤；③ 按条件文本注入会先命中 fence 同形条件，须以 swym 诊断串锚定并 assert 命中 1 次。
**遗留问题**：`check-lit` 的 4 项 `smoke_*` e2e 为基线红：其 raw 仍用旧几何（`+0x100` 前缀、旧 `EXIT_BLOCK`），M19 新几何（raw entry 0x2000、EXIT_BLOCK 0x30）合入后未迁移；pre-fix 工具链跑同 4 例同样全红，与本次改动无关（需另立 testcases 任务）。`check-patch-tree` 整库 rc=1 的 92 problem 属其它组件在途/KNOWN-RED。

## 审阅记录

#### 第 1 轮 engineer 自审

**结论**：逻辑与边界逐行核对无新 finding；所有改动已验证，可置「待验收」。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `imm-range.s` 把 `swym 262143` 当合法上界，语义变更后 check-lit 红 | ✅已修 | 该正例改 `swym 4095`（编码 `0x47880FFF`），保留 `swym 262144` 的 immu18 越界负例 | MC+CodeGen lit 165/165 rc=0；`swym-sbz.s` 负例覆盖 4096/262143 |
| F2 首版注入按条件文本替换，先命中 fence 的同形条件 ⇒ 假绿（lit 未红） | ✅已修 | 注入改为以 `"swym: reserved encoding"` 位置锚定并 `assert` 该段命中 1 次；两条注入各自独立 | `run.sh --inject` rc=0：A/B 均 build=0、lit=1，还原 md5 相等、lit=0 |
| F3 证据脚本 grep 把 `immu18[17:12]` 当正则致两项误红 | ✅已修 | 改 `grep -Fq` 固定串 | 默认模式 `RESULT: PASS (fails=0)` |
| F4 `check-lit` 4 项 e2e 红是否本次引入 | ❌非本次 | 未改（范围外：旧 raw 几何/EXIT_BLOCK，M19 新几何迁移缺口） | pre-fix 快照跑同 4 例同样 4 红；`smoke_*` 自 M14 未更新 |


#### 第 1 轮 reviewer 验收

**判决：Accepted**（中改档；下述结论全部基于 reviewer 自己重跑，不采信完成区转述）

**重跑记录**（workdir=仓库根；rc 取被检命令自身退出码）：
- 汇编（安装根 `llvm-mc`，`-show-encoding`）：`swym 4096`/`262143` rc=1，诊断 `swym: reserved encoding (immu18[17:12] is SBZ … at most 4095 …)`；`swym 0` rc=0 `[0x47,0x88,0x00,0x00]`、`swym 4095` rc=0 `[0x47,0x88,0x0f,0xff]`；`swym -1`/`swym 262144` rc=1 仍为 `immediate out of range`（原诊断未被新检查吞掉）。
- **重点一（符号/常量表达式，实测非推测）**：`.set N,4096;swym N`、`.set N,4095+1`、`.set N,4096+4096`、`.equ N,4096`、`swym (4096)`、`swym 4095+1`、`swym 0x1000` **全部 rc=1** 且命中同一 SBZ 诊断；同输入 pre-fix 快照 rc=0 编码 `47 88 10 00` ⇒ **`.set`/常量表达式路径无漏网**，任务书提示的「rc=0 并编码 `0x47881000`」情形实测不成立（不需登记漏网）。
- 符号操作数（`swym L` 前向/后向、`swym extsym`）rc=134 `LLVM ERROR: DADAO: no PC-relative fixup kind`，**pre-fix 同 rc=134** ⇒ 既有缺陷，发生在 fixup 阶段、不产出 SBZ 字；记 finding（建议另立 issue），非本次阻断。
- **重点二（反汇编）**：`0x47881000`/`0x478BFFFF` → `<unknown>`；`0x47880FFF` → `swym 4095`；`0x47880000` → `swym 0`。源码确认 `hasInvalidSwymImm` 判 `MI.getOperand(0)`（swym 单操作数 `immu18:$imm18`），非照抄 escape 的 `operand(1)`。
- **门控**：`test-codegen` rc=0（19/19）；`check-lit` rc=2 → 183/187，4 红 = `DADAO-E2E::smoke_{add,arith,fp,jump}`；`check-case-ledger` rc=0（5882 条）；`check-knowledge-refs` rc=0；`check-component-changelog` rc=0；`check-patch-tree` llvm-project 段 0 problem（92 problem 分布 chipyard14/gem518/linux50/musl4/picolibc4/qemu2，无一在 llvm）。
- **重建**：`make build-mc` rc=0、`make install-host` rc=0；安装根与构建树 `llvm-mc`/`llvm-objdump` md5 前后均相同（`227e2f8c…`/`e10f32b3…`）。
- **证据脚本**：仓库根执行运行期证据目录内的 `run.sh` 默认 rc=0（`RESULT: PASS (fails=0)`）；`run.sh --inject` rc=0（A/B 均 build=0、lit=1，还原 md5 相等、lit=0）。
- **独立注入（reviewer，不可由 engineer 自检替代）**：删 Disassembler 的 `hasInvalidSwymImm(MI)` 调用点 → `build-mc-lite` rc=0 → `swym-sbz.s` lit **rc=1**（`47 88 10 00 swym 4096` 未判 `<unknown>`）→ `cp` 还原（源文件 md5 `503340a9…` 相等、源树 `git diff` 空）→ 重建 rc=0 → lit **rc=0**，`llvm-mc` md5 回 `227e2f8c…`。
- **基线红独立判定**：重建有效 pre-fix 工具链（补齐 objcopy 与 cfx-alias 表布局）复跑 4 例 ⇒ 同样 4 红、同 Exit Code 124（qemu `timeout 30` signal 15）；失败块归一化（工具路径/pid/dd 吞吐）后与本轮 `check-lit` 输出 **逐行完全相同（4/4 identical）** ⇒ 判「与基线逐行相同」，非本次引入。佐证：4 例各仅含 `swym 0`（合法，不受新检查影响），无 `4096/262143`，改动面不触及其输入/编码。
- **约束逐条**：范围 = 8 文件与完成区「修改文件」逐条对齐，无 `spec/`/契约/`Makefile`/`DADAO-gen` 改动；`series` 99 未变；patch 逐 hunk 仅新增 swym 判据段；完成区 9 行 ≤30、无具体运行期路径；注入前后 `git status -uall` 与 8 文件 md5 **逐行/逐值相同**。

**findings（均不阻断）**：① engineer 的 `baseline-e2e-prefix.log` 为假红（rc=127 `llvm-objcopy: command not found`，根本未跑到 qemu），不能作基线证据；reviewer 已独立给出有效基线，原结论未被推翻。② 符号操作数 rc=134 为既有缺陷，建议另立 issue。③ 日志中 `check-hex: FAIL` 属 build-bootrom 自检的注入损坏测试（随后 `injected hex corruption rejected PASS`、`build-bootrom: PASS`），非问题。
