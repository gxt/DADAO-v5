# m13-spec-011: 伪指令迁入 `SimRISC-00 §5`；`SimRISC-03` 按 rd/rb/rf 拆三章；`set.ft` 写宽对照

**模块**：spec
**项目里程碑**：M13
**依赖**：`m13-spec-010`（已合 `cb8ca30d`，`rf2rf` 已入 `SimRISC-02`）
**可并行分片**：否（spec 结构重排，牵动全仓引用）
**预估**：3–4 h
**档位**：大改（结构重排 + 锁 + 全仓引用；≥4 路注入 + 独立重算）
**状态**：已验证

## 用户裁定（2026-11-15，原话）

> 「同意A，两个补充也可以。SimRISC-03 中的伪指令应该移动到 SimRISC-00的第5章，SimRISC-03的第一章，按rd/rb/rf分开三章；此外，在tests/inst/00 目录下，新增这7种伪指令的专门的汇编测试」

（本任务只做**spec 侧**两件；`tests/inst` 的载体另立任务。A 的第二条补充「lit 对照用例」在 llvm 面，另立任务。）

## 任务

1. **迁入 `SimRISC-00 §5 伪指令`**：把 `SimRISC-03` 现有的 `## 2. set.rd`、`## 3. set.rb`、`## 4. set.ft / set.fo` **正文整体迁到** `SimRISC-00 §5`（保持内容不变，只搬 + 调整交叉引用），使 §5 从"一行指针"变成**规范正文**；`SimRISC-03` 侧删除这三章并在册首/相关处留指针「伪指令见 `SimRISC-00 §5`」。
2. **`SimRISC-03` 第一章按 rd/rb/rf 拆三章**：现 `## 1. 立即数常数赋值` 拆为 **rd 组 / rb 组 / rf 组** 三章（原顺序保持：rd → rb → rf），后续章节与附录随之顺延编号；**内容不改**（仅拆章、补章首一句导语）。
3. **A 的补充之一（写宽对照表）**：在 `SimRISC-00 §5`（`set.ft` 段）增加一张两行对照表：`set.ft rf, imm32` ⇒ **只写低 32、高 32 不动**；`set.ft rf, rf` ⇒ **整 64 位**（并注明后者是 `m13-spec-010` 删 `ft2ft` 后的语义，属可观察变化）。
4. **全仓引用同步**：`grep -rn "SimRISC-03"`（现 257 处）里凡指向"章号/小节"的引用，按新编号更新；`.tao/contracts/*`、`contracts/*`、`docs/DDLN/*`、`docs/Process-*` 同步；`SimRISC-00 §5` 的旧指针句删改。
5. **锁与门控**：`manifests/spec-readonly.lock.toml` 同笔重算改动册 sha256；changelog 各册补条目（版本号按现有规则）。

## 验收（逐条贴真实 rc/现场值）

1. 结构：`SimRISC-00 §5` 含四类伪指令正文（`set.rd`/`set.rb`/`set.ft`/`set.fo`，含立即数/寄存器两形式与展开示例）；`SimRISC-03` 不再有伪指令章、且第 1–3 章分别是 rd/rb/rf 组；
2. **写宽对照表**在位（`set.ft` imm 窄 / reg 整 64 位）；
3. 全仓引用：`grep -rn "SimRISC-03 §"` 无失效章号（`check-spec-cite-targets`/`check-spec-refs`/`check-rule-refs` rc=0，贴改动前后引用计数）；
4. 门控：`check-spec-readonly`（锁重算）、`check-spec-changelog`、`check-spec-purity`、`check-spec-refs`、`check-spec-cite-targets`、`check-spec-numbering`、`check-rule-refs`、`check-asm-list`、`check-asm-prose`、`check-isa-coverage`、`check-knowledge-refs` 全 rc=0；
5. **≥4 路可达 FAIL 注入**（`cp`+md5 还原）：① 把 `SimRISC-03` 某章号引用改错 ⇒ cite-targets 红；② 删写宽对照表一行 ⇒ 你自设的断言红；③ 锁不重算 ⇒ `check-spec-readonly` 红；④ 伪指令章残留旧编号 ⇒ `check-spec-numbering` 红；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **不改语义**（除写宽对照表这一处用户已裁定的补充）：不动 `rf2rf` 定义/限制、不动其它指令语义；
- 只改 `spec/**`、`.tao/contracts/**`、`contracts/**`、`docs/**`、`manifests/spec-readonly.lock.toml`、本任务书；**不改** `tests/**`、`components/**`、`tools/**`；
- 禁 `install-host`/`check-modules`/`build-*`；不 sync/reset 节点；不提交 git；注入还原 `cp`+md5。

## 待裁定

（无：实现中未遇到需用户裁定的新决策；`Toolchain-01 §6` 的「唯一权威定义」措辞按「§5 已成规范正文」同步收叙，见审阅记录 F1。

**范围扩展（用户 2026-11-15 追加，原话）**：「补一项（**扩范围，一件小事**）：把 `tools/spec/generate_opcodes.py` 的 `S03_IMM` 常量改成新节名（现在仍写旧标题，重生成会让 `opcodes.yaml` 的 `spec_cite` 悬空）。」——据此允许集增加 `tools/spec/generate_opcodes.py` 的该常量（+紧随注释）。）

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-15）

逐行审查 9 个文件改动；搬迁/拆章「零语义漂移」用程序化比对独立复核（原文切片 vs 新文切片逐行相等）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `Toolchain-01 §6` 仍自称「唯一权威定义」，与 §5 成为规范正文形成两处「唯一」 | ✅已修 | §6 引导句改「汇编层语法与展开表」并指 `SimRISC-00 §5`；示例指针同步改指 §5 | 门控 rc=0；契约引用解析到 §5.1–§5.3 |
| F2 `set.ft rf, rf` 行只写 `rf2rf`，`rd` 源（`rd2rf`）同为整 64 位，易被读成窄写 | ✅已修 | 该单元格补「（`rd` 源展开的 `rd2rf` 同为整 64 位）」（§2.3 既有语义，非新增口径） | 自设断言「写宽对照表 2 行在位」rc=0 |
| F3 注入脚本初版含恒真断言（`or True`）且硬编码旧哈希，注入会静默失效 | ✅已修 | 改为长度断言 + 现场解析锁的 `sha256` 行改写前 12 位 | inject3 注入后 rc=2、还原后 rc=0 |
| F4 锁文件注记块引入双空行（与既有格式不一致） | ✅已修 | 删多余空行 | `check-spec-readonly` rc=0、`tomllib` 解析 21 条 |
| F5 ADR / `tests/**` 仍指旧章号或旧行号 | ⏸延后 | 不在本任务允许改动集（硬约束仅允许 spec/.tao-contracts/contracts/docs/锁/任务书） | 已在完成区「遗留问题」逐项登记 |
| F6（扩范围）`tools/spec/generate_opcodes.py` 的 `S03_IMM` 仍是旧节标题 | ✅已修 | 改为三章公共前缀 `SimRISC-03: 立即数常数赋值` + 注释注明分组；经核实 `rec()` 只取「手册」段做断言、输出恒为「手册: 助记符」，故改常量不改变生成结果 | 生成器重放与入库 `contracts/opcodes.yaml` **逐字节一致**（diff rc=0，7124 行）；四条门控 rc=0 |

判决：无未修 finding（F5 已登记并说明越界原因）⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-15，大改档；下列 rc 均为 reviewer 本人重跑所得，非采信完成区）

- **重跑 11 条验收门控**：readonly/changelog/purity/refs/cite-targets/numbering/rule-refs/asm-list/asm-prose/isa-coverage/knowledge-refs 逐条 `make -s <t>; echo $?` ⇒ **全 rc=0**；另 6 条相关（codeblocks/spec-drift/fp-contract/legality-drift/scope/asm-list-drift）亦 rc=0。
- **证据脚本**：审运行期证据目录的一键脚本 `run.sh`（未入库；4 断言 + 11 门控；无 `tee` 吞码、断言均有可达 FAIL、注入含长度断言 + 现场解析锁哈希 + md5 对账，无恒真）；本人在本任务 worktree 内重跑 ⇒ rc=0（ALL PASS）；`--inject 1..4` 各「注入 rc≠0 → cp+md5 还原 → rc=0」。
- **搬迁逐行核**（本人 difflib 程序化比对）：03 伪指令块 115 行（3 标题 + 112 正文），与 00 §5 正文 **111 行逐行相同、差异恰 1 行**（册内互指 `SimRISC-00 §2.3`→`§2.3`）；00 §5 另新增导语 2 行 + 3 小节标题 + 写宽对照 9 行 ⇒ 无语义漂移。
- **三章结构**：03 正文 = `## 1. 立即数常数赋值：RD 组`/`## 2. …RB 组`/`## 3. …RF 组`，原 §1 正文原样保留（仅加 3 句章首导语），`set.zw/set.ow/or.w/andn.w` 总述在 §1；伪指令仅余册首指针、正文 0 残留。
- **写宽对照表**：位于 §5.3 末（`## 6.` 之前）；imm32 行「只写低 32 位、高 32 保持原值、只触及 `wp1/wp0`」、rf 行「整 64 位、展开 `rf2rf`（`rd` 源 `rd2rf` 同宽）」与 §2.3 写宽总则一致；注记写明属**可观察变化**、**无任务号**（purity rc=0）。
- **引用**：`SimRISC-03 §`（spec + .tao/contracts + contracts + docs 范围）**28→15 与完成区一致**，残留 15 处全部指向现存节（RD/RB/RF 组）；`SimRISC-00 §5.1/5.2/5.3` 共 13 处标题与三个小节标题逐字相符。
- **锁**：tomllib 解析 21 条，本人逐册 sha256 重算 **21/21 相等**（4 改动册 `5f4c80…`/`6c6de5…`/`52cdb5…`/`eebb34…` 与锁一致）。
- **生成器扩范围**：本人复制子树到运行期临时目录（已清理）后重放 `generate_opcodes.py` ⇒ 与入库 `contracts/opcodes.yaml` md5 相同、`diff` rc=0（7124 行）；`S03_IMM` 仅进 `rec()` 的册名断言、输出恒为「册: 助记符」（重放产物 grep「立即数常数赋值」0 命中）⇒ 改常量不改输出。
- **本人 4 路注入（不复用 engineer 的 4 路，均 cp+md5 还原）**：① `### 5.1`→`## 2.` ⇒ numbering **rc=2**（编号重复/不连续 4 处）；② 写宽表 rf 行改「只写低 32 位」⇒ 自设断言 **rc=1**；③ `legality_rules.yaml` cite 改回 `…：Immediate constant` ⇒ cite-targets **rc=2**（dangling 1）；④ 锁 Toolchain-01 sha 改脏 ⇒ readonly **rc=2**（mismatch 1/21）——四者还原后同检查均回 rc=0、md5 与 HEAD 相等。
- **越界核**：`git show 2cd90aee --name-only` = 11 文件（10 交付文件 + 本任务书）；`tests/**`、`components/**` **0 改动**；`tools/**` 仅 `generate_opcodes.py` 的 `S03_IMM` + 紧随注释（用户扩范围原话已落盘 §待裁定）。
- **快照对账**：验收前后 `git status --porcelain -uall` 均 **0 行**；所有注入文件还原后 md5 与 `HEAD:file` 逐个相等。
- **遗留（采信完成区登记，均在允许集外）**：`components/llvm-project/changelog.md`（`SimRISC-03 §set.rd`）、`.tao/adr/adr-0013/0028/0031`（旧章号/旧行号）仍指旧位置。
- **非阻断 finding**：① 完成区「`SimRISC-00 §5` 引用 8→30」我实测同范围 0→17、全仓非 archive 6→27（`SimRISC-03 §` 28→15 属实）；② 「搬迁 114 行」我测为 115 行块 / 111 行相同（计数口径差，实质一致）；③ 任务 §任务 5「changelog 各册补条目」仅落 SimRISC-00（02/03 被 numbering 门控禁设变更记录附录；Toolchain-01 未补、与 m13-spec-010 先例一致）⇒ 是否补 Toolchain-01 条目请 architect 裁定；④ 我把 `contract-isa` 的 `[SimRISC-00 §5.1 …]` 改成 `[SimRISC-00 §9.9 …]` ⇒ `check-spec-refs` 仍 rc=0（标题型引用剥前导章号后比对、**章号部分不校验**；门控既有局限、非本任务引入）；⑤ 完成区「修改文件（10）」未含任务书本身（提交实为 11 文件）。
- **判决：Accepted** —— 验收 6 条在我本人重跑下全部达成、硬约束无违反；上述 finding 属文档级数字/口径与门控既有局限，按「文档级小错不阻断」记录，交 architect 终审。

## 完成区

**测试结果**：通过 15/15（4 条自设断言：结构、写宽表、旧引用清零、生成器重放 + 11 条门控）；失败原因：无。一键证据脚本 `run.sh`（运行期证据目录，未入库）含断言 + 11 门控 + 4 路注入自检，全部 rc=0。
**修改文件**（10）：`spec/SimRISC-00-指令系统设计.md`、`spec/SimRISC-03-16位立即数操作.md`、`spec/SimRISC-02-寄存器复制.md`、`spec/Toolchain-01-汇编语言.md`、`.tao/contracts/contract-isa.md`、`.tao/contracts/contract-fp.md`、`contracts/fp_semantics.yaml`、`contracts/legality_rules.yaml`、`manifests/spec-readonly.lock.toml`、`tools/spec/generate_opcodes.py`（仅 `S03_IMM` 常量 + 紧随注释）。

**验收结果**
1. 章节目录对照（旧→新）：`SimRISC-03 §2 set.rd`→`SimRISC-00 §5.1`；`§3 set.rb`→`§5.2`；`§4 set.ft/set.fo`→`§5.3`；`SimRISC-03 §1`→`§1 RD 组`/`§2 RB 组`/`§3 RF 组`（各补一句章首导语）；`SimRISC-03 附录 A/B` 不变。搬迁 114 行与原文**逐行相同**（仅 3 个标题行 + 1 处册内互指改写），§5.3 新增 9 行（写宽对照表 + 注）。
2. 写宽对照表：位于 `SimRISC-00 §5.3` 末——`set.ft rf, imm32`⇒只写低 32 位、高 32 位不动；`set.ft rf, rf`⇒整 64 位（注明属删同格式纯复制后的**可观察变化**）。
3. 引用统计：`SimRISC-03 §` 行数 28→15（13 处改指 `SimRISC-00 §5.x` 或新组名），`SimRISC-00 §5` 引用 8→30；迁移后 `check-spec-refs` 一度 27 处失配，同步后 0。
4. 11 条门控全 rc=0：readonly / changelog / purity / refs / cite-targets / numbering / rule-refs / asm-list / asm-prose / isa-coverage / knowledge-refs（另 codeblocks、spec-drift、asm-list-drift、fp-contract 亦 rc=0）。
5. 4 路注入（`cp`+md5 还原）：① 契约改回旧节名 ⇒ cite-targets rc=2；② 删 `imm32` 对照行 ⇒ 自设断言 rc=1；③ 锁哈希改脏 ⇒ readonly rc=2；④ §5.3 改回旧章号 `## 4.` ⇒ numbering rc=2（编号重复 4）。四者还原后均回 rc=0，md5 对账一致。
6. 锁：SimRISC-00/02/03 + Toolchain-01 四册 sha256 同笔重算并加条目注记；changelog：`SimRISC-00` 附录 `0.5.7-rc` 追加 1 条（版本不变）。
7. `S03_IMM` 改新节名（`SimRISC-03: 立即数常数赋值`，三章公共前缀）；生成器无 `--check`，故生成到运行期临时路径后 `diff` 入库 `contracts/opcodes.yaml`：**逐字节一致**（rc=0，7124 行）；`check-spec-refs` / `check-spec-cite-targets` / `check-rule-refs` / `check-isa-coverage` 四条 rc=0。

**新发现/坑**：① `check-spec-refs` 只校 `.tao/contracts/*.md`、`cite-targets` 只校 `contracts|tests` 的 yaml，**spec 册内互指无门控**（本次靠自设断言兜底）；② `generate_opcodes.rec()` 的入参 `spec_cite` **只取「手册」段做断言**、输出恒为「手册: 助记符」⇒ 该常量的节名不会进入 `opcodes.yaml`；③ 生成器无 `--check`，可重放性须「生成到临时路径 + `diff`」自证。
**遗留问题**：① `.tao/adr/adr-0013/0028/0031`、`tests/inst/**`、`tests/unit/llvm/lit/**`、`components/llvm-project/changelog.md` 仍指旧章号/旧行号——ADR 与 `components/` 不在允许改动集，`tests/inst` 载体另立任务（建议主会话并单）；② `generate_opcodes.py` 的 `S03_IMM` 旧标题 **已在本次处置**（改新节名，生成器重放与入库 `opcodes.yaml` 逐字节一致）；③ 无其它未完成项。
