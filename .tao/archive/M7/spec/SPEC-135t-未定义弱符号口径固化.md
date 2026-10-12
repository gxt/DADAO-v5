# SPEC-135t: 未定义弱符号口径固化（`ADR-0019 D9` + `contract-elf §3.2` 正文）

**模块**：spec
**项目里程碑**：M7
**依赖**：`LLVM-085t`（`已验证`，口径来源实现）
**状态**：已验证

> 立项来源：用户 2026-10-12 裁定「**全按建议办（推荐）**」⇒ 其中「未定义弱符号口径立项固化」；**落法**经 2026-10-12 复核后由用户改判为 **(C)**（见下）。

## 用户裁定（2026-10-12，**原话/选项标签**）

- **议题**：`LLVM-085t` 把"未定义弱符号的 PC 相对引用"解析为**本位自循环**（`call-iiii`→`jump-iiii` 改写）——该口径如何固化？
- 首轮建议为"新立 `adr-0024`"；主会话复核现场后提出修正（`ADR-0019` 现有 **D1–D8**，其中 **D6 = 溢出策略** ⇒ 对口位置已存在；而 ADR **不载正文** ⇒ 正文仍应进 `contract-elf`）⇒
- **用户选择 = 「（C）`ADR-0019` 加 D9 + `contract-elf` 正文（推荐）」** ⇒ **不新开 ADR**；`ADR-0019` **就地追加 `D9`**（决策/理由/被否方案）+ **口径正文写 `contract-elf §3.2`（溢出策略）下新增小节**。
- 该选择**视为对 `D9` 内容的逐条确认**（选项描述含 5 个要点）✓；取得渠道：**经主会话问答**取得（2026-10-12）。

## 事实（实测）

- `.tao/knowledge/contract-elf.md`：**无**「弱符号/未定义」条款（`grep` 空）✗；已有 **§3.2 溢出策略**（"越界 ⇒ link-time error"）⇒ 新小节落其下最自然 ✓。
- `.tao/adr/adr-0019-dadao-relocation-types.md`：**D1–D8**（D2 类型集 / D3 公式 / D4 ABS48 片数 / D5 挂载粒度 / **D6 溢出策略** / D7 禁用 relaxation / D8 不做 `ABS32`）⇒ **无「未定义弱」** ✗。
- `LLVM-085t` 实测口径（供 D9/正文引用）：未定义**弱** ⇒ PC 相对分支/call **解析为本位自循环**；`call-iiii`(0x74) ⇒ **改写 `jump-iiii`(0x70)**（免 RegRAS 失衡）；未定义**强** / 已定义**远距强**仍**失败/越界报错**（不放宽）；**`--noinhibit-exec`** 下未定义强同族；**`REL12` 暂不纳入**、保持严格；解锁 `pass 152→174`（22 条）。

## 接口规范

- **输出**：
  1. **`ADR-0019` 就地追加 `D9`**（**决策层**；`docs/Process-03` 体例，**不载正文**）：
     - **D9 — 未定义弱符号（PC 相对分支/call）**：① 解析为**本位自循环**；② **`call-iiii`(0x74) ⇒ 改写 `jump-iiii`(0x70)**（免 RegRAS 失衡）；③ 未定义**强** / 已定义**远距强** 仍 失败/越界报错（**不放宽**）；④ **`--noinhibit-exec`** 下未定义强同族处理（写明）；⑤ **`R_DADAO_REL12`（PC 相对访存）暂不纳入**，保持严格报错；
     - **理由**：picolibc 的**可选平台钩子**（`_user_strerror`/`gettimeofday`/`arc4random_*`，调用处有 `&sym == 0` 守卫）需要链接成功；RISC-V 同类惯例；
     - **被否方案**：(a) 报错不动（阻塞上述钩子）；(b) 解析为 0 但**不改 `call`**（压 RegRAS 无弹 ⇒ 失衡）；(c) 前端改语义（全局生效 ✗）；
     - **确认记录**：用户 2026-10-12「（C）ADR-0019 加 D9 + contract-elf 正文（推荐）」（原话/标签）✓。
  2. **`contract-elf §3.2`（溢出策略）下新增小节**（**正文**——"应当是什么"）：写上述 ①②③④⑤ 五要点（简短规范语，不写理由/复盘 ✗）；**与 `ADR-0019 D9` 互指**（正文引 ADR；ADR 引正文 ✓）。
  3. `.tao/knowledge/milestones.md` 流水更新 `SPEC-135t` 行（状态 `待验收`，`完成时间` `—`）。
- **约束**：**不新开 ADR**；**不改**上游只读册（`SimRISC-*`/`DADAO-*`）；**不改**实现；`contract-elf`/`adr-0019` 均**不在只读锁**内 ✓（仍按 `Process-02`/`Process-03` 体例）；**计数不写死**。

## 验收标准

1. **`D9` 存在且合规**：`adr-0019` 含 `D9`，体例合 `docs/Process-03`（决策/理由/被否方案齐）；**含用户确认记录**（原话/标签 + 日期 + 渠道）；**未新开 ADR**（`ls .tao/adr/ | grep 0024` 为空）。
2. **正文落位**：`contract-elf §3.2` 下新小节含**五要点**（`grep` 真实输出）；**不含**理由/复盘（正文纪律）。
3. **互指**：`ADR-0019 D9` ↔ `contract-elf` 新小节 **双向引用**（`grep` 证据）。
4. **与实现一致**：抽 ≥3 条（自循环 / `call→jump` / 强符号不放宽）与 `LLVM-085t` 的**证据文件**对照，逐条吻合。
5. **门控**：`make check`、`check-spec-refs`、`check-no-residue`、`check-knowledge-refs` 各 EXIT=0。
6. **完成区**（≤30 行）与真实输出逐条对齐。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/SPEC-135t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；显式 staging（禁 `git add -A`）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. 只动任务范围（`.tao/adr/adr-0019-*.md`、`.tao/knowledge/contract-elf.md`、任务书、`milestones.md` 行）；越界须披露。
5. **ADR decision 逐条确认**：**不得**因"任务书/选项里已写该内容"就默认通过 ✗ —— **本任务的 `D9` 已由用户经选项确认** ✓（原话已落纸）；**若你要改 D9 措辞/增删要点 ⇒ 停下报告**（禁自拟自答，`lessons §3.17`）。
6. 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位）。
7. 一键证据脚本落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
8. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
9. **计数不写死**。

## 完成区

**测试结果**：一键证据 `<证据目录>/run.sh` 基线 **rc=0**（26 项全绿）、`--inject` **rc=0**（**11 组配对变异**各「原文件 PASS + 变异 MUST FAIL」、**3 组单向 MUST FAIL**（1 结构 `fake-dir` + 2 行为 B1/B2）、末段回绿 + repo md5 对账未变）；总项 = 26 + 11×2 + 3 + 3 = **54**。门控：`make check` / `check-spec-refs` / `check-knowledge-refs` / `check-no-residue` / `check_issues` / `check-tasks` 各 rc=0。计数均现场统计（脚本内不写死）。
**修改文件**（仅任务范围）：
- `.tao/adr/adr-0019-dadao-relocation-types.md`：`## Decision` 于 D8 后追加 `D9`；`## Rationale` 与 `## 被否方案（记录）` 各补 1 条；`## 状态说明` 的 `✅` 清单补 `- **D9** … ✅` + 追加 2026-10-12「就地追加 `D9`」历史行（含**用户原话/选项标签 + 日期 + 渠道**）。
- `.tao/knowledge/contract-elf.md`：新增 `### §3.3 未定义弱符号（PC 相对分支/call）`（五要点 + 逐条 `[ADR-0019 §D9]`）；**同文件一致性同步**：文件头 2 处、附录 A §3 行、文末注记（`D1–D8` → `D1–D8 + D9`、`§3.3` 来源 = `D9`）【披露】。
- `.tao/knowledge/milestones.md`：新增 `SPEC-135t` 流水行（`待验收` / `—`）。
- 本任务书；证据/日志（非 git）：`<证据目录>/`、`<日志目录>/`。
**验收结果**（逐条与真实输出对齐）：
1. **`D9` 合规**：`grep -cE '^\*\*D9 — '` = 1 且行号 > D8；五要点齐（`本位自循环` / `0x74` / `0x70` / `边界（不放宽）` / `--noinhibit-exec` / `REL12…不适用本决策`）；Rationale 含 `（D9）`、被否方案含 `未定义弱（D9）`；`✅` 清单含 `- **D9** … ✅`；确认记录含「（C）`ADR-0019` 加 D9」+「经主会话问答」+ `2026-10-12`；`ls .tao/adr | grep 0024` **空**（rc=1，**未新开 ADR**）。
2. **正文落位**：`### §3.3` 在 `### §3.2` 之后；含五要点（`grep` 全中）；4 条 bullets **每条**带 `[ADR-0019 §D9]`；§3.3 **无**「理由/被否/为什么/原因/因为」。
3. **双向互指**：`ADR D9` → `` `contract-elf.md §3.3` ``；`contract §3.3` → `[ADR-0019 §D9]`（`grep -c` 均 ≥1）。
4. **与实现一致**（真实 `llvm-mc` + `ld.lld` + `llvm-objdump`，非抽样）：① 未定义弱 `call` → 链接 rc=0，编码 `70 00 00 00  jump [rb0, 0]`（原 `74 … call [rb0, weak_fn]`）；② 未定义**强** → rc=1 `undefined symbol: strong_fn`；③ `--defsym=strong_fn=0xFC0010000000` → rc=1 `R_DADAO_REL26 out of range`；④ `ld.o rd8,[rb0,weak_ld]` → rc=1 `R_DADAO_REL12 out of range`。与 `LLVM-085t` 完成区三条（`call`→`jump` / 本位自循环 / 强符号不放宽）**逐条吻合**。
5. **门控**：见「测试结果」各 `rc=0`；`check-spec-refs`/`check-knowledge-refs` 未因新增 §3.3 / 引用而报错。
**新发现/坑**：
- **实现有 1 处防御分支未入正文**：`LLVM-085t` 对「`REL26` 落点既非 `call-iiii`(0x74) 也非 `jump-iiii`(0x70) ⇒ 显式报错」加了校验（该批 0 例）；本任务五要点未含此点 ⇒ **未写入 D9/§3.3**（未自拟口径），如需另立。
- `--noinhibit-exec` 下 LLD **自身**把未定义符号降为 warning（该 flag 口径）⇒ 未定义**强**亦落自循环；本次按五要点写成「同族处理（该 flag 自身口径未改）」。
- 判据细节 `isUndefined()`（而非 `isUndefWeak()`，hidden 未定义弱 binding 被 LLD 降为 local）仍只在实现注释/`LLVM-085t` 审阅记录中，**正文只写行为不写实现判据**（符合「ADR/正文不承载实现细节」）。
**遗留问题**：无（本任务范围内）。`D9` 严格按用户选项五要点落字，**未改写/增删要点**；未触及 `REL12` 语义、未改实现、未新开 ADR。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐条审查改动（`ADR D9` / `contract §3.3` / 头部同步 / 证据脚本），finding 处置如下：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 是否越出用户五要点、自拟口径 | ❌不修（核定） | 未增删要点；仅按 ①–⑤ 落字 + 出处/理由/被否方案 | `run.sh` A3/A11 五要点**逐字**命中 |
| §3.3 是否夹带理由/复盘（正文纪律） | ✅已修 | §3.3 只留规范语 + 来源标注 | A13（`理由/被否/为什么/原因/因为` 0 命中）+ INJ「混入理由」MUST FAIL |
| 双向互指是否齐 | ✅已修 | ADR D9 引 `§3.3`；§3.3 每条引 `[ADR-0019 §D9]` | A4 / A12 / A14（`grep -c`） |
| 头部/附录 `D1–D8` 与新增 D9 悬空不一致 | ✅已修（同文件最小同步，已披露） | 文件头 2 处 + 附录 A §3 行 + 文末注记 | A2 + scope C1/C2；`grep -c '就地追加'` = 1 |
| `--noinhibit-exec` 措辞与实测一致 | ❌不修（依据 `LLVM-085t` reviewer ④） | 写「LLD 本把未定义降 warning ⇒ 未定义强同族」 | `LLVM-085t` 完成区 + reviewer ④ 原文 |
| 证据脚本断言恒真 / 计数写死 | ✅已修 | 11 组配对变异 + 3 组单向 MUST FAIL（1 结构 + 2 行为）；自循环数=现场 reloc 数 | `--inject` rc=0（54 项），每组「变异 MUST FAIL」 |
| 反例注入是否污染仓库 | ✅已修 | 一律**临时副本**注入（repo 文件零改动）+ 打印 repo md5 | R3 md5 before==after；`git status` 仅本任务文件 |
| 任务书含字面 `.work/<具体路径>` | ✅已修 | 用 `<证据目录>/` 占位（保留 `<>`） | A16 + INJ「混入字面路径」MUST FAIL |

判决：finding 均 ✅已修 / ❌已核定，无未处置项 ⇒ 状态 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑记录**（本人独立执行，均相对路径）：
- 门控：`make check` EXIT=0（含 `check_issues`：26 open/9 closed/0 blocking）；`make check-spec-refs` EXIT=0（0 violations）；`make check-knowledge-refs` EXIT=0（0 悬空）；`make check-no-residue` EXIT=0；`python3 tools/infra/check_issues.py` EXIT=0。
- `<证据目录>/run.sh` 基线 EXIT=0（26 项全绿）；`--inject` EXIT=0（54 项）。
- grep 证据：ADR D9 块含 `` `contract-elf.md §3.3` `` ✓；§3.3 内 `[ADR-0019 §D9]` **现场计数=5** ✓；§3.3 理由词（理由|被否|为什么|原因|因为）**空（EXIT=1）** ✓；`ls .tao/adr | grep 0024` 空（EXIT=1，未新开 ADR）✓。
- **独立行为复核**（自写源 + 直跑工具链，非证据脚本）：① 未定义弱 `call [rb0,rv_weak_fn]`+`.weak` ⇒ `ld.lld` rc=0，`objdump` 见 **`70 00 00 00  jump [rb0, 0]`**（自循环 + `0x74`→`0x70` 改写）；② 未定义强 ⇒ rc=1 `error: undefined symbol: rv_strong_fn`；③ `--defsym=rv_strong_fn=0xFC0010000000` ⇒ rc=1 `R_DADAO_REL26 out of range`。与 `LLVM-085t` 完成区（①②③+`--noinhibit-exec`+`REL12` 五点）逐条吻合。

**约束核验**：
- `D9` 体例：决策/理由/被否方案(a)(b)(c)/指向正文引用（正文归 §3.3，ADR 不载正文）齐 ✓；确认记录 = 用户原话/选项标签「（C）`ADR-0019` 加 D9 + `contract-elf` 正文（推荐）」+ 2026-10-12 + 渠道「经主会话问答」✓（非以任务书代确认）。
- 五要点逐点对照任务书①–⑤：本位自循环 / `call-iiii`(0x74)→`jump-iiii`(0x70)（RegRAS）/ 未定义强+已定义远距强**不放宽** / `--noinhibit-exec` 同族 / `REL12` 暂不纳入——**齐且无增删** ✓；§3.3 同五要点（引导句+4 bullets 各缀 `[ADR-0019 §D9]`）✓。
- 同步最小性：contract-elf diff 仅文件头 2 处 + 附录 A §3 行 + 文末注记，无顺手改动 ✓；`git diff --stat` = adr-0019 / contract-elf / milestones 3 文件（+ 任务书 untracked），**无** `spec/`、`contracts/`、`tests/vectors/` ✓；untracked `.tao/tasks/infra/INFRA-070t-…`（mtime 10-12 13:55，早于本任务，非本任务残留，非阻断）。
- **独立反例**（不与 engineer 11 组重复）：删 §3.3「**不放宽**」bullet ⇒ 同一脚本 EXIT=**1**、`A11 contract §3.3 五要点齐` FAIL（25/26）⇒ `cp` 还原、md5 `9eadb7fc…`==`9eadb7fc…` ⇒ 重跑 EXIT=0（26 全绿）✓。
- 快照对账：验收前后 `git status --porcelain -uall` 逐行相同、4 目标文件 md5 相同（注入零残留）。

**阻断项（1）**：
- **完成区注入计数与真实输出不符**：完成区称「**13 组**变异各「原文件 PASS + 变异 MUST FAIL」、3 组行为反例」；我重跑 `--inject` 现场计数 = **11 组**配对（`原文件 PASS`=11、`变异 MUST FAIL`=11）+ **3 组单向 MUST FAIL**（fake ADR dir 结构反例 1 + B1/B2 行为反例 2），不存在 13 组配对（自审表「13 组变异」同病）。违反「完成区与真实输出逐条对齐 / 说 N 跑 M ⇒ 打回」。**修法**：仅改完成区（及自审表同行）计数措辞为「11 组配对变异 + 3 组单向 MUST FAIL（1 结构 + 2 行为）」，改后重跑 `<证据目录>/run.sh`（预期仍 26/54）即可，其余无需返工。

**非阻断建议 / 遗留处置**：§⑨ 防御分支（`REL26` 落点非 `0x74`/`0x70` ⇒ 显式报错，本批 0 例）**赞同不写入** `D9`/§3.3（写入即改已确认 `D9` ⇒ 须用户逐条确认）；建议**登记 issue 待用户裁定**（是否入规范/另立任务），不由 engineer/reviewer 自拟。

**判决：Needs Revision**（阻断项 1 = 完成区计数措辞，修法如上；`D9` 体例/确认记录/五要点、§3.3 正文纪律、双向互指、实现一致、门控、独立反例均通过 ⇒ 修后复审可快速转 Accepted）。

#### 第 2 轮 engineer 自审

reviewer 阻断项（计数措辞与真实输出不符）处置：现场重跑 `run.sh` 核数 —— `mut` 定义 **11** 处 × 2 行 = **11 组配对**（`原文件 PASS` 11 / `变异 MUST FAIL` 11），单向 MUST FAIL **3 组**（`no_adr0024` `fake-dir` 结构 1 + B1/B2 行为 2）⇒ 仅订正**完成区**与**第 1 轮自审表**的计数措辞为「11 组配对 + 3 组单向 MUST FAIL（1 结构 + 2 行为）」，**未动**实现/门控/证据脚本逻辑。
复跑：`run.sh` 基线 **rc=0（26 项）**、`--inject` **rc=0（54 项）**（总项 = 26 + 11×2 + 3 + 3 = 54，现场统计）。
门控：`make check` / `check-knowledge-refs` / `check-no-residue` 各 **rc=0**。判决：阻断项已修、无未处置项 ⇒ 状态 `待验收`。

#### 复判轮 reviewer 验收（第 2 轮，最小范围）

- **计数一致性 ✓**：自跑 `<证据目录>/run.sh` 基线 rc=0（26 项）、`--inject` rc=0（54 项），现场计数 = **11 组配对**（`原文件 PASS` 11 / `变异 MUST FAIL` 11）+ **3 组单向 MUST FAIL**（`fake-dir` 结构 1 + B1/B2 行为 2），总项 26+11×2+3+3=**54** ⇒ 与订正后完成区/自审表措辞**逐条一致**；`grep '13 组'` 仅命中本审阅记录上轮 finding 历史引用（记录不改），完成区/自审表旧表述**已清** ✓。
- **门控 ✓**：`make check` / `check-knowledge-refs` / `check-no-residue` 各 **rc=0**（禁 tee，直捕退出码）。
- **未动实现 ✓**：`adr-0019` md5 `87211e24…`、`contract-elf` md5 `9eadb7fc…`、`milestones` md5 `6f3a77af…` 与上轮验收快照**逐行相同**（`diff` 空）；上轮 reviewer 记录未被改写、完成区 17 行（≤30）。
- **判决：Accepted**（阻断项 0）——上轮唯一阻断项（完成区计数措辞）已订正且与真实输出逐条一致，其余核验沿用上轮全通过结论。
