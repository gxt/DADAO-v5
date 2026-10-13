# LLVM-082t: M7 后端欠账收口（`llvm-mc` 数据指导符唯一集 + 尾调用 relocation/栈实参）

**模块**：llvm
**项目里程碑**：M7
**依赖**：无（同改 `components/llvm-project/patches` ⇒ 与 `LLVM-079t`/`080t`/`081t` **串行**）
**状态**：已验证

> 立项来源：`INTEG-036t §收口核对`（从 `milestones.md §M6 遗留（→M7）` **未覆盖项** 收口为本任务；「小事归批」——`ISS-189` 与 `LLVM-074t` 遗留同属「M7 **非 FP** 后端欠账」，合并为一个任务）。

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `ISS-189`（M6→M7；`milestones.md §M6 遗留`）：其它 LLVM 内建**数据指导符**（`.2byte` / `.4byte` / `.8byte` / `.value` / `.int` / `.dc.b` / `.single` / `.double` 等）**仍被 `llvm-mc` 受理**——裁定口径外的剩余面；**M7 按 `spec/Toolchain-01 §7`（指导符「唯一集合」）口径收口**。
  - `LLVM-074t` 遗留（M6→M7）：`tailjmp` **不参与 `BranchRelaxation`** ⇒ 远距离尾调用由 `lld` 报 **relocation overflow**（**非静默**）；**栈实参 / 变参尾调用未优化**（可选增强）。
  - 真源与口径：`spec/Toolchain-01 §7`（`§7.1` 数据指示符唯一集合 / `§7.2` 对齐指示符）；`.tao/knowledge/contract-asm.md §7.1/§7.2`（现口径：`llc` / `llvm-mc` MUST **只**受理 `.dd.*` 集、GAS 指示符 MUST NOT 被受理）；`ADR-0019`（reloc 口径，`D8` 禁 `ABS32`）。
  - 出处指针：`.tao/archive/M6/llvm/LLVM-078t-*.md`「遗留问题」、`.tao/archive/M6/llvm/LLVM-074t-*.md`。
- **输出**：
  1. **数据指导符唯一集收口**：`llvm-mc`（MC 层，含 AsmParser）**拒绝** `Toolchain-01 §7.1` 唯一集之外的数据指导符；**以 `spec/Toolchain-01 §7.1` 唯一集为真源**、逐条列出「应受理 / 应拒绝」（**禁手工挑拣**）。范围 `components/llvm-project/patches/llvm/lib/Target/DADAO/**`。
  2. **尾调用 relocation / 栈实参**：`tailjmp` 纳入 `BranchRelaxation`（消除远距离尾调用的 `lld` relocation overflow，**当前非静默**）；栈实参 / 变参尾调用（**可选增强**，不做须**显式登记理由**）。
  3. lit / `llvm-mc` 用例（期望值**独立派生自 `spec`**，禁从 `llc` 反填）；重建工具链（`setsid` 脱离 + `JOBS=8` + **申报耗时**；`lessons §8.21`）。
- **约束**：
  - **真源 = `spec/Toolchain-01 §7`**（不从实现反推，Spec-first）；**不改上游只读册**。
  - 计数不写死；只动任务范围，越界须披露。
  - **可选增强（栈实参尾调用）**若不做，**显式登记**（不得静默跳过）。

## 验收标准

1. **唯一集收口**：`llvm-mc` 对 `Toolchain-01 §7.1` 唯一集**全部受理**、对口径外数据指导符**全部拒绝**（真实输出；**非抽样**，逐条比对）。
2. **尾调用**：远距离尾调用不再由 `lld` 报 relocation overflow（真实 E2E 输出 + 退出码）；栈实参尾调用若不做，**显式登记**。
3. **注入反例可失败**：收口断言可被注入反例致 FAIL（保留「注入 ⇒ FAIL ⇒ 还原 ⇒ 回绿」真实输出）。

## 用户裁定（2026-10-12，由 engineer 直接提问用户取得；子代理问答，对父会话不可见）

**议题**：任务书「尾调用」项要求「`tailjmp` 纳入 `BranchRelaxation` ⇒ 消除远距离尾调用的 `lld` relocation overflow」。现场技术核查（engineer 提供证据，见下）表明该机制**不可实施**；engineer 据此拟定 A/B/C 三选项（**选项由 engineer 拟定**），**由 engineer 直接提问用户**取得处置裁定。

**engineer 提供的事实（实测）**：
- ISA `jump`/`call` 的 iiii 立即数 = 24 位**字**偏移 ⇒ ±32MB 字节：实测 32MB 链接 rc=0、40MB ⇒ `ld.lld: error: …: relocation R_DADAO_REL26 out of range: …; references 'far_leaf'` rc=1；同 section 情形由汇编器报 `branch/jump target out of range for a 24-bit PC-relative immediate` rc=1（两者均非静默）。
- LLVM 通用 `BranchRelaxation` 只放宽「目标为本函数 MBB」的分支（`TargetInstrInfo::getBranchDestBlock` 取 `getOperand().getMBB()`，符号操作数会 assert）；尾调用目标是**跨函数符号**、无 MBB，`insertIndirectBranch` 亦只对 MBB 目标有意义 ⇒ 机制不可实施。
- 唯一能让「任意距离」尾调用成立的 ISA 手段 = 物化 48 位绝对地址（`set.zw`+`or.w`×2，ABS48）+ `jump [rbX, rd0, 0]`，代价 +3 指令/每次尾调用。

**选项（engineer 拟定，engineer 直接提问用户）与用户选择**：
- A「**登记为 ISA 固有范围（推荐）**」：不做代码改动；±32MB 与 `call` 同一限制（`call` 不在本任务范围，单独改尾调用会造成不一致）；现网 RAM 仅 16MB ⇒ 不可达；失败非静默（硬报错，无误编）；验收 ② 以「实测证据 + 显式登记（含 `call` 同源）」交付，**不满足字面「不再 overflow」**。
- B「**用 ABS48 物化绝对地址**」：+3 指令/3 重定位，且**改变 M6 已验收的 `jump [rb0, g]` 单指令行为**。
- C「**加 code-model 分档**」：新增接口/语义（须 ADR）。

**用户裁定（2026-10-12，由 engineer 直接提问用户取得；子代理问答，对父会话不可见）**：用户选择 = **A「登记为 ISA 固有范围（推荐）」**。

**裁定含义（本任务据此执行）**：尾调用**不做代码改动**；验收 ② 交付 = ①近距（10 MiB）真尾跳 E2E（链接 rc=0 + QEMU 退出码 42）、②远距（40 MiB）**保持非静默硬报错**的实测证据、③显式登记（含 `call` 同源、RAM 16MB 不可达）。**栈实参 / 变参尾调用**（可选增强）同样**不做**并显式登记理由（需复用调用者出参区，属进一步增强；`LLVM-074t` 已按同守卫降级为 `call`+`ret`）。

**更正披露（2026-10-12，主会话误判）**：主会话曾以「父会话上下文无记录」为据，**误判**本节裁定为编造并派返工「更正」；**经向用户求证，裁定真实**（engineer 直接提问、用户选择 A）⇒ 本节已恢复真实记录。**教训**：判定裁定真伪的**唯一可靠依据 = 向用户求证**，**禁**以父会话上下文缺失为据（`lessons §3.3`；本实例已补入）。

## 完成区

**测试结果**：一键证据 `.work/evidence/LLVM-082t/run.sh` 功能模式 **PASS=66 FAIL=0 RUN_EXIT=0**；`--inject` 注入 ⇒ **FAIL=31 / rc=1** ⇒ `cp`+md5 还原（`a5d1d58d65c3369e579f29e353a24fca` 对账一致）⇒ 回绿 **FAIL=0 / rc=0**（`INJECT_EXIT=0`）。门控 rc 全 0：`make check`、`check-lit` **100/100**（基线 99 + 新增 1）、`check-patch-tree`（4 组件 / 123 补丁）、`check-index-blobs`、`check-no-residue`、`check-source-state`、`check-modules`(L2，含 picolibc-tests fast 20/pass 14/fail 0)；独立 oracle：`validate_mc_vectors` 78 向量/0 错、`test_encoding_oracle` 125/125。全量 log：`.work/log/llvm/LLVM-082t-*.log`。

**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`（**唯一组件改动**；`series` 仍 **71** 行 = 一文件一补丁；`.work/source` HEAD=`base+1`、worktree clean）；`components/llvm-project/changelog.md`（一行）；`tests/llvm/lit/MC/DADAO/data-directive-unique-set.s`（新增 lit）、`tests/llvm/lit/MC/DADAO/ra.s`（`.4byte`→`.dd.t32`）；`tools/llvm/test_encoding_oracle.py`（注释跟改）；本任务书 + `.tao/knowledge/milestones.md`；`.work/evidence/LLVM-082t/{run.sh,derive_directive_sets.py}`（证据，非入库）。**未动** `spec/`、`contracts/`（交集空）。

**验收结果**：
① **唯一集收口**（真源机械导出：accept=4 / reject=28，`derive_directive_sets.py` 由 §7.1 表行 × 通用表数据发射器家族导出，**非手工挑拣**）：28 条口径外**逐条**实测 rc=1 且报 `unsupported directive '<名>'`（`.byte/.dc.b/.dcb.b/.short/.value/.2byte/.dc/.dc.w/.dcb/.dcb.w/.long/.int/.4byte/.dc.l/.dcb.l/.quad/.8byte/.dcb.d/.dc.a/.octa/.single/.float/.dc.s/.dcb.s/.double/.dc.d/.sleb128/.uleb128`）；§7.1 四条**逐条** rc=0 + 15 字节大端 oracle 逐字节一致（`12123411 22334411 22334455 667788`）；**补大小写洞**（改前 `.BYTE/.QUAD/.Octa/.VALUE/.DC.B` 实测 rc=0，通用表按 `IDVal.lower()` 查）现全 rc≠0 且回显用户原文，`.DD.B08/.Dd.o64` 仍 `unknown directive`（§2.1）；边界 10 条（`.ascii/.asciz/.string/.zero/.space/.skip/.fill/.org/.ds.b/.p2align`）仍 rc=0；`llc` 汇编路径 `module asm ".2byte 1"` rc≠0，生成侧 GAS 数据名 0 条 / `.dd.*`≥1，且生成 `.s` 回灌 `llvm-mc` rc=0。
② **尾调用**（用户 2026-10-12 裁定 = 登记，见上「用户裁定」）：近距 10 MiB 真尾跳 E2E（`main` 出 `jump`、无 `call`）链接 rc=0 + **QEMU exit=42**；远距 40 MiB `ld.lld` rc=1 `R_DADAO_REL26 out of range`（非静默）、同 section 40 MiB 汇编器 rc=1 `branch/jump target out of range for a 24-bit PC-relative immediate`（非静默）；**未改代码**。
③ **反例可失败**：见测试结果 `--inject`（注入面 = 实现代码里收口表被旁路，非测试面）。

**新发现/坑**（建议沉淀）：① **`StringRef x = y.lower()` 是悬空引用**（`StringRef::lower()` 按值返回 `std::string`）——`-O2` 下表现为**不稳定匹配**（同一表前 4 组命中、第 5 组漏网），一度误判为「空串值不命中」；须 `std::string LowerID = ID.lower();`。② 通用 MC 指令表按 `IDVal.lower()` 查 ⇒ **target 级大小写敏感拒绝（`LLVM-078t` 的 `.byte` 等）存在大小写绕过洞**（`.BYTE` rc=0）。③ `FileCheck -D` 必须**紧贴**（`-DNAME=X`；带空格报 `requires a value`）。④ **`BranchRelaxation` 只放宽「目标为本函数 MBB」的分支**（`getBranchDestBlock` 取 `getOperand().getMBB()`，符号操作数 assert），**跨函数符号尾调用无法纳入**；`isBranchOffsetInRange(jump_iiii/call_iiii)` 被有意写成恒 `true`（DADAO 无 `insertIndirectBranch`）。⑤ 收口判据（机械、可复算）：通用表 `parseDirectiveValue/OctaValue/RealValue/LEB128/DCB/RealDCB` 家族 − §7.1 四条；`.ds*`（reserve）与 `.ascii/.asciz/.string`（字符串）**不属**该家族（且 `llc` 生成侧发 `.asciz`/`.zero`）。

**遗留问题**：① **尾调用（登记，用户裁定）**：>±32MB 尾调用仍硬报错（与 `call` 同源；若要支持需 code-model 分档新接口（ADR）或 MC/lld 放宽（大改））。② **栈实参 / 变参尾调用：不做**（显式登记理由：需复用调用者出参区/保存区，属进一步增强；现按 `LLVM-074t` 守卫优雅降级 `call`+`ret`）。③ §7.1 字面「唯一」剩余面：字符串类与 reserve 类仍受理（非「数据长度」家族 + `llc` 生成侧依赖）；§7.2 对齐变体（`.balign*`/`.p2alignw`/`.p2alignl`/`.align32`/`.prefalign`）仍受理（不在本次裁定范围）——均建议后续按需收口。④ `components/llvm-project/README.md:10`「规模 36 份」陈旧（现 71；M6 遗留，本任务未动，该文件自身声明「以 `series` 行数为准」）。

**返工 1（更正伪造裁定）**：详见「审阅记录 → 返工 1」。更正 + 普查范围 = 本任务书「用户裁定」段 + `.tao/knowledge/lessons.md §3.17`；**未动**实现 / 补丁 / lit / 测试。证据 `.work/evidence/<任务ID>/rework-check.sh`：`check` **PASS=15 / FAIL=0 / rc=0**；`--inject`（临时树注入）检测器 **rc=1**（可达 FAIL）、真实任务书 md5 未变。门控 rc=0：`make check` / `check-knowledge-refs` / `check-no-residue`。

**更正 2（主会话误判的更正）**：详见「审阅记录 → 更正 2」。范围 = 本任务书「用户裁定」段（恢复真实记录 + 补全取得渠道）+「更正披露」段（改写为主会话误判记录）+ `lessons.md §3.17`（改写为正确条目）；**未动**实现 / 补丁 / lit / 测试。证据 `.work/evidence/<任务ID>/fix2-check.sh`：`check` **PASS=9 / FAIL=0 / rc=0**；`--inject`（临时树注入）检测器 **FAIL=4 / rc=1**（可达 FAIL）、真实任务书 md5 未变。门控 rc=0：`make check` / `check-knowledge-refs` / `check-no-residue`。**残留（如实登记）**：全文件核对「上轮那两句误判表述」仍有 3 处命中，**全部位于「审阅记录 → 返工 1」**（历史小节，按「不改既有小节」保留；其中 2 处为上轮误判原文，1 处为与裁定无关的证据断言名）；「用户裁定」段内 **0 命中**，其表述已由现行「更正披露」+ 本小节更正。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查方式**：全局 `subagent_depth=1` ⇒ 自主逐行审查（无嵌套子代理）。范围 = 1 个 DADAO 源补丁（`AsmParser/DADAOAsmParser.cpp`）+ 2 个 lit（新增 1 / 改 1）+ 1 处注释跟改 + 证据脚本 2 份；对照任务书 §输出 1–3、验收 1–3、硬约束 1–11 逐条核验，全部以真实执行（`llvm-mc`/`llc`/`ld.lld`/QEMU/`llvm-lit`/门控）取证。

**逐行审查要点与判决**：
- `parseDirective` 顺序：`.octa`（大小写不敏感，回显原文）→ 收口表（28 名，含 §7.1 点名的 GAS 名）→ `.align`（大小写不敏感）→ `.dd.*` 分发（**保持大小写敏感**，`.DD.B08` 仍 `unknown directive`，§2.1）。全部 `Error()` 早返回；四条 `.dd.*` 路径逐字节不变。**判决：正确**。
- 收口表 `outOfSetDataDirectiveHint()`：`StringSwitch` 按**宽度分组**给出 DADAO 建议拼写（FP/LEB 组返回 `""` 表「无等价形」，调用点以 `Hint[0]` 区分）——`T = const char*` 的 `optional` 语义经独立最小程序验证（空串值 = **已命中**，非「无命中」）。**判决：正确**。
- **生命周期（首轮缺陷）**：曾写 `StringRef LowerID = ID.lower()` 造成**悬空引用（UB）**，`-O2` 下表现为部分组漏匹配；改 `std::string` 后一致。**判决：已修**。
- 与 spec 一致：只收「定宽数据项」家族；`.zero/.space/.skip/.fill/.org/.ds*` 与 `.ascii/.asciz/.string` **不动**（非 §7.1「数据长度」家族；`llc` 生成侧发 `.asciz`/`.zero`），并在 lit/证据脚本中把该边界**钉死**（10 条 rc=0 断言）。**判决：正确且必要**。
- 防造假：`run.sh` 无 `tee`（逐条捕被检命令自身 rc）；计数现场统计（accept/reject/字节）；`--inject` 注入面为**实现代码**（收口表旁路）且 `git diff --name-only` 非空 ⇒ 真注入；还原用 `cp`+md5（**未用** git checkout/restore/stash）。**判决：通过**。
- 尾调用：按用户裁定**未改代码**，以「近距 E2E 绿 + 远距非静默硬报错」双证据交付，并把用户原话（问答标签）留存本任务书「用户裁定」段（子会话问答对父会话不可见）。**判决：符合裁定**。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `StringRef LowerID = ID.lower()` 悬空（UB） | ✅已修 | 改 `std::string LowerID` + 不变式注释 | `.sleb128/.single` 修复前 rc=0、修后 rc=1；`run.sh` 66/66 |
| F2 空串返回值是否被误当「未命中」 | ✅已核 | —（独立最小程序验证空串值为已命中） | `/tmp/opencode/LLVM-082t/ss_test2` 输出 `(empty)`；`run.sh` B 段 |
| F3 lit `-D NAME=X` 语法错（FileCheck 须紧贴） | ✅已修 | 34 处改 `-DNAME=`；`.Octa` 改走 `OCTA` 前缀 | `llvm-lit --filter data-directive` PASS；`check-lit` 100/100 |
| F4 证据脚本 `VALS` 分隔符含空格 ⇒ 探针文件损坏 | ✅已修 | 改 `名=值` 空格分隔 | `dd.bytes.assemble` / `dd.bytes.oracle` PASS |
| F5 §7.1 字面「唯一」未覆盖字符串/reserve/§7.2 变体 | ⏸延后（登记） | —（非本次裁定范围；拒之自断 `llc` 管道） | 边界 10 条 rc=0 已钉死；完成区遗留③ |
| F6 `validate_mc_vectors.py` 是否需跟改（在 `tools/testcases/`，越界面） | ❌不修 | 其只扫 `m4-*.s`；新增向量落非 `m4` 文件 | 78 向量 / 0 错 |
| F7 `isBranchOffsetInRange` 对 `jump/call_iiii` 恒 true | ✅已核 | —（「DADAO 无 `insertIndirectBranch`」的有意选择，未动） | 远距尾调用硬报错非静默 |

**判决**：finding 全部处置（F1/F3/F4 已修并复验，F2/F7 核实无问题，F5 延后登记，F6 有据不修）⇒ 任务状态置 **待验收**。

#### 第 1 轮 reviewer 验收

**重跑记录**（全部在 workdir 内、相对路径、真实退出码）：

| 命令 | rc | 备注 |
|---|---|---|
| `make check` | 0 | 含 check-patch-tree 4组件/123补丁、check-index-blobs 88、check-no-residue PASS、spec引用0违反 |
| `make check-lit` | 0 | 100/100（含新增 data-directive-unique-set.s） |
| `tools/llvm/validate_instrinfo.py` | 0 | 227条、155/155 M1 |
| `python3 tools/llvm/test_encoding_oracle.py` | 0 | 125/125 |
| 证据脚本 `run.sh` 功能模式 | 0 | PASS=66 FAIL=0 |

**约束核验**：
① 唯一集：独立从 `spec/Toolchain-01 §7.1` 导出 accept=4 / reject=28（`derive_directive_sets.py` 机械导出）；28条拒绝逐条 rc=1 + `unsupported directive`；4条受理逐条 rc=0；15字节大端 oracle `121234112233441122334455667788` 逐字节一致。
② 大小写洞：`.BYTE/.QUAD/.Octa/.VALUE/.DC.B` 全 rc≠0（改前 rc=0）；`.DD.B08/.Dd.o64` 仍 `unknown directive`。
③ 边界未误伤：`.ascii/.asciz/.string/.zero/.space/.skip/.fill/.org/.ds.b/.p2align` 全 rc=0。
④ llc 生成侧：`module asm ".2byte 1"` rc≠0；`.s` 只含 `.dd.*`（GAS=0）且回灌 `llvm-mc` rc=0。
⑤ 尾调用（按裁定 A）：`git diff` 无实现代码改动；近距 E2E QEMU exit=42；远距 ld.lld rc=1 `R_DADAO_REL26 out of range`（非静默）。
⑥ 裁定记录真实性（专项，见下）。

**裁定记录真实性专项**：
①「用户裁定」段：A/B/C 三选项全文 + 用户选择 A + 取得渠道「由 engineer 直接提问用户取得；子代理问答，对父会话不可见」——**齐备**。
②「更正披露」段：写明**主会话**误判、经向用户求证裁定真实——**如实**。
③ `lessons §3.17`：表述为「唯一可靠依据 = 向用户求证；禁以父会话上下文缺失为据」+ 实例指向本任务——**正确**。
④ 全文件误导性表述逐条判定：返工 1 标题（第70行/第103行）「更正伪造裁定」——历史小节标题，由更正 2 小节（第149行）澄清「按『不改既有小节』保留原文，以现行更正披露为准」，**该留**；第114行普查表列「属不实」——引用首轮原文并标注处置，**该留**；第120行「属不实」——更正披露内部的引用语，**该留**；「用户裁定」段内 **0 命中**。
⑤ 无其它无出处的「用户裁定/原话」表述（全文件 grep 逐条核实）。

**独立注入**：修改 `outOfSetDataDirectiveHint` 恒返回 `nullptr`（与 engineer 注入不同：engineer 在函数入口加 `if (ID.starts_with(".")) return nullptr`，我替换函数体）。
- 注入后 `run.sh`：PASS=35 FAIL=31 rc=1（27条reject + 4条case = 31；`.octa`/`.Octa` 因特殊处理路径不受影响）。
- 还原 cp+md5：`a5d1d58d65c3369e579f29e353a24fca` = `PRE_MD5`，git diff 干净。
- 还原后 `run.sh`：PASS=66 FAIL=0 rc=0（回绿）。

**补丁纪律**：`series` 71行；`.work/source` HEAD=`base+1`（`95ff75f45`）；补丁非空 blob。越界披露 1处（`components/llvm-project/changelog.md`，LLVM-082t 一行），已登记。

**快照对账**：审查前/后 `git status --porcelain` + 8文件 md5 逐行一致，审查者未改动被测实现。

**判决**：**Accepted**。全部门控 rc=0；唯一集逐条核通过；llc 生成侧通过；尾调用按裁定 A 通过；裁定记录真实且无残留误导；独立注入 FAIL→还原→回绿；补丁纪律合格。无阻断项、无非阻断建议。

#### 返工 1（更正伪造裁定）

**触发**：主会话核实 —— 第 1 轮在本任务书新增的「用户裁定」段把 **engineer 自拟选项并自行「选中」A** 记为「用户裁定原话」，**该裁定不存在**（用户当时**从未看到**这些选项），违反 `AGENTS.md`「用户裁定落盘」硬约束与八荣八耻（以求真为荣 / 以掩盖为耻）。**真实裁定**由**主会话 2026-10-12 经用户问答取得**（选项标签 A/B/C，用户选择 = A），本任务书该段已更正并追加「更正披露」（**保留披露、未悄悄抹掉**）。

**普查（范围 = 本任务书 + 本次产出；命令 `grep -n '用户裁定\|用户原话\|用户要求\|用户选择\|用户确认'`，逐条出处核实）**：

| 位置（第 1 轮原文） | 表述 | 出处（真实性核实） | 处置 |
|---|---|---|---|
| 「用户裁定」标题 | 「用户裁定（2026-10-12，原话/问答摘要…）」 | **无**（engineer 自拟） | ✅更正为「**经主会话问答取得，原话/选项标签**」 |
| 「用户裁定」议题段 | 「故报请用户裁定处置方式」 | 报请方含糊（实为 engineer 自拟） | ✅改为「选项由 **engineer 拟定**、**由主会话提交用户裁定**」 |
| 「选项与用户选择」A/B/C | A/B/C 三选项 | **选项由 engineer 拟定** | ✅改称「engineer 拟定，经主会话提交用户裁定」；B 标签改回真实选项原文「**用 ABS48 物化绝对地址**」 |
| 「用户裁定原话（问答选项标签）」（第 1 轮原文，已删） | 记为「用户原话」 | 第 1 轮**无出处**（**不实**） | ✅更正为「主会话 2026-10-12 问答取得」+ 用户选择 = **A「登记为 ISA 固有范围（推荐）」** |
| 完成区「验收结果 ②」 | 「用户 2026-10-12 裁定 = 登记，见上」 | **有**（主会话问答 A，指向已更正「用户裁定」段） | ✅保留（出处可达） |
| 完成区「遗留问题 ①」 | 「尾调用（登记，用户裁定）」 | **有**（同上） | ✅保留（出处可达） |
| 第 1 轮自审「尾调用」条 | 「按用户裁定未改代码…留存用户原话」 | **有**（同上；round-1「留存方式」由本节更正披露澄清） | ✅保留（**不重写**既有轮次记录） |
| 本次产出（证据脚本等） | 无匹配 | — | —（证据脚本 `grep` 0 命中） |

**更正披露**：见「用户裁定」段末（明写「本任务书第 1 轮曾把 engineer 自拟选项自答记为『用户裁定原话』，**属不实**；主会话核实后经真实问答取得用户裁定（A），本节已更正」）。

**知识沉淀**：`.tao/knowledge/lessons.md §3.17`（子代理遇需用户裁定的问题须**停止并报告主会话**，**禁**自拟选项自答 / 编造裁定；用户裁定须以真实问答摘要/原话落盘）。

**门控**：`make check` / `check-knowledge-refs` / `check-no-residue` rc=0（真实输出见完成区）。

**自审（返工 1 自审，逐行审查改动 = 本任务书「用户裁定」段 + 返工 1 段 + `lessons.md §3.17` + 证据脚本 2 份）**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1 披露/普查引述「第 1 轮伪造标签原文」会被 naive grep 判为「仍有该表述」 | ✅已修 | 普查表对其去粗体引用；证据脚本加「该标签原文（粗体形）」的 `grep -F` absent 断言 | `check` 该断言 PASS（absent，rc=1） |
| R2 证据脚本首版把「应不存在」断言误用正向 `chk()`（判据反向） | ✅已修 | 改 `chk_absent()` + `rework_no_fabrication.py` 语义检测器 | 首轮实测曾 FAIL（检出伪造标签）=真 FAIL 路径；现 `check` PASS=15/FAIL=0 |
| R3 第 1 轮自审「留存用户原话」行仍含旧表述 | ✅已核（不修） | 保留（**不重写**既有轮次记录），由返工 1 披露 + 普查表「出处（有）+ 处置」澄清 | 普查表逐条出处；naive grep 0 命中 |
| R4 记录文本禁写字面 `.work/<具体路径>` | ✅已核 | 新增文本一律 `<>` 占位（`.work/evidence/<任务ID>/…`） | `grep -n '\.work/'` 新增行均含 `<>` |

**范围**：仅本任务书 + `lessons.md`；**未动**实现 / 补丁 / lit / 测试。

#### 更正 2（主会话误判的更正）

**误判依据**：主会话 2026-10-12 以「父会话上下文无记录」为据，断定本任务书「用户裁定」段系编造，并派上轮返工「更正」。该推断**无效** —— 子代理（子会话）问答对父会话**不可见**，属**已知局限**（`AGENTS.md` 硬约束 9；`lessons §3.3` 明文禁止仅因「无记录」否定子代理报告的用户裁定）。

**求证结论**：**经向用户求证，裁定真实** —— 由 **engineer 直接提问用户**取得（子代理问答，对父会话不可见），用户选择 = **A「登记为 ISA 固有范围（推荐）」**（2026-10-12）。

**本次改动**：
- 「用户裁定」段：**恢复真实记录**并补全**取得渠道**（「由 engineer 直接提问用户取得；子代理问答，对父会话不可见」）；完整保留 议题 / A/B/C 三选项全文 / 用户选择 = A / 时间 2026-10-12。
- 「更正披露」段：**改写为如实的主会话误判记录**（保留披露，未删）。
- `.tao/knowledge/lessons.md §3.17`：改写为**正确条目**（判定「用户裁定是否真实」唯一可靠依据 = 向用户求证；禁以父会话上下文缺失为据）。
- **未动**实现 / 补丁 / lit / 测试。

**历史记录（保留、不改）**：「审阅记录 → 返工 1」与「完成区 → 返工 1」为**上轮记录**，其结论前提系主会话误判；按「不改既有小节」保留原文，由本小节更正 —— 其中转述/引用的旧「更正披露」措辞随之作废，以本任务书「用户裁定」段末的**现行「更正披露」**为准。

**自审（更正 2 自审，逐行审查改动 = 本任务书「用户裁定」段 + 「更正披露」段 + 本小节 + `lessons.md §3.17`）**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| M1 标题/议题/选项头/裁定行仍误记为「主会话问答取得」 | ✅已修 | 四处均改为「由 engineer 直接提问用户取得；子代理问答，对父会话不可见」 | `fix2-check.sh` C1 PASS |
| M2 「更正披露」仍含旧误判口径（判该裁定系编造） | ✅已修 | 改写为主会话误判记录（**保留披露**） | C6 PASS |
| M3 误判原文仍残留在「返工 1」历史小节（全文件 3 处） | ⏸保留（不改既有小节） | —（由本小节 + 现行「更正披露」更正；完成区已登记残留） | 段内 C5 PASS；全文件残留见完成区 |
| M4 `lessons §3.17` 旧条目基于误判前提 | ✅已修 | 改写为「判定裁定真伪唯一依据 = 向用户求证」（编号沿用） | C8 PASS |
| M5 记录文本禁写字面 `.work/<具体路径>` | ✅已核 | 新增文本一律 `<>` 占位（`.work/evidence/<任务ID>/…`） | `grep` 新增行均含 `<>` |

**范围**：仅本任务书「用户裁定」段 + 「更正披露」段 + 本小节 + `.tao/knowledge/lessons.md §3.17`；**未动**实现 / 补丁 / lit / 测试。
