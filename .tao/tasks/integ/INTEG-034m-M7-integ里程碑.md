# INTEG-034m: M7 integ 模块里程碑核验（整体收敛点）

**模块**：integ
**项目里程碑**：M7
**依赖**：各模块 `m`（`INFRA-072m` / `SPEC-136m` / `LLVM-090m` / `QEMU-059m` / `TESTCASES-043m`）；`INTEG-033k`（M7 开启）
**状态**：里程碑

## 执行环境
**执行环境**：本地

## 目的
核验 **M7 整体收敛**（`Process-04 §1`：**INTEG 结束** = 集成门槛）。**M7 口径（来源 = `milestones.md` M7 段落 + `INTEG-033k`，逐条引用）**：

1. **M7 主题达成** = picolibc 移植（自带 test 现场 `total 235 / pass 213 / fail 0 / excluded 22 / blocked 0`，用户 2026-10-12 裁定「记为达成（推荐）」）+ FP 后端完备（P0/P1）+ ISA↔后端覆盖矩阵 + 过渡 oracle。
2. **各模块 `m` 均 `里程碑`**（`INFRA-072m`/`SPEC-136m`/`LLVM-090m`/`QEMU-059m`/`TESTCASES-043m`）⇒ 满足后由主会话置**项目里程碑 M7 = 达成**（`Process-04 §1`）。
3. **L3 门控**（`docs/Process-07 §1/§2` 触发点「里程碑 / `/complete` 跑 L3」）= `make check-full`（`check-qemu-semantics` 全量 + `test-m6` = `check-lit-full` + `lli` 值级对拍 + Embench）全绿。

## 核验内容（可执行步骤）
1. **L3 全量**（长任务规则）：`make check-full`（= `check-qemu-semantics` + `test-m6`）——`setsid nohup` 脱离 + 落盘完成标记 `XXX_EXIT=$rc`、`JOBS=8`、`timeout` 的 `124` 判 FAIL、**申报预计耗时**（几百~几千秒）、**禁**会话内等待器；另跑 L1 `make check` rc=0。
2. **汇总各模块 `m` 结论**：逐个 `grep` 5 本 `m` 的 `**状态**` = `里程碑`；核各 `m` 的核验表结论与「跨模块影响」判定。
3. **跨模块交互核**（`AGENTS.md`「模块里程碑与跨模块交互」）：汇总各 `m` 的未处置项（若有）——点名 `ISS-198`（2-NaN 无 oracle）、`ISS-199`（权限 fail-fast 待复验）、`ISS-200`（changelog 缺条目）、`ISS-201`（弱符号防御分支待裁定）、`ISS-202`（contract 迁移待授权）、`ISS-193`（剩余面）。**存在未处置跨模块影响 ⇒ 本 `m` 不得置里程碑、且**不得**置项目里程碑 M7 为达成**。
4. **M7 范围内 issue 处置**：核对 M7 期 issue 的最终动作（关闭 / 转遗留 / 指明编号）已由各模块 `m` 逐条给出；`open` 者逐条有依据。
5. **门控**：`make check-no-residue` rc=0 + `git status --untracked-files=all` 干净（无临时残留）。

## 验收标准
1. **L3 证据**：`make check-full` 真实退出码 = 0（落盘 `XXX_EXIT` 标记；`124` 判 FAIL）+ `make check`（L1）rc=0。
2. **5 模块 `m` 均 `里程碑`**：逐个现场 `grep` 取证。
3. **跨模块判定**：明列未处置项（若有）⇒ 明确写「**不置里程碑**」；无未处置项 ⇒ 置 `里程碑` 并由主会话置 **项目里程碑 M7 = 达成**。
4. **状态机**：核验通过 ⇒ 主会话将本 `m` `**状态**` 置 `里程碑`；随后**项目里程碑 M7** 置 `达成`。
5. **角色**：本任务**无实现**（核验类）——由 **reviewer 独立执行核验**，**architect** 记录 / 回填完成区 / 提交；**不得**要求 engineer 写无意义实现。

## 硬约束
- 临时目录 `/tmp/opencode/<任务ID>/`；**禁**仓库内临时文件。
- **不提交 git**（提交权归 architect，核验后在本任务分支内提交）；**不 push**。
- 长任务（L3）：`setsid nohup <cmd> >log 2>&1 &` 脱离 + 落盘 `XXX_EXIT=$rc`、`JOBS=8`、`timeout` 的 `124` 判 FAIL、**申报耗时**、**禁**会话内等待器。
- 命令须捕退出码：`cmd; echo rc=$?`（**禁** `cmd | tail`/`| tee` 吞码）。
- 任务书文本**不写** `.work/<具体路径>` 字面（用 `<>` 占位）。
- 反例注入还原：**禁** `git checkout`/`git restore`/`git stash`；一律 `cp` 备份 + md5 对账或临时树。
- 计数不写死：一律现场统计，或写「不下降 / 逐项相等」。

## 完成区
**测试结果**：L1 `make check` rc=0 ✓；L2 `make check-modules` rc=0 ✓；L3 `make check-full` **rc=1 ✗**（`check-qemu-semantics` 149/149 PASS + `test-m6: [1/3] check-lit-full` 12/12 PASS + `test-m6: [2/3] diff_ir_lli` **FAIL**——13 个 M7 新增 `.ll` 未入 manifest）；`check-no-residue` rc=0 ✓；`check_issues.py` rc=0 ✓。
**修改文件**：无（reviewer 核验类任务，不改仓库文件）；`.work/evidence/INTEG-034m/` 为证据产出。
**验收结果**：L3 失败（diff_ir_lli 结构性）+ SPEC-136m 未通过（ISS-201 待用户确认）⇒ **项目里程碑 M7 不可置达成**。
**新发现/坑**：`tests/llvm/ir-lli/manifest.yaml` 需补 13 条 M7 新增 `.ll`（P0/P1/FP-谓词/cttz/inline-asm-r/fp-sign）到 include 或 exclude。
**遗留问题**：① L3 diff_ir_lli 需返工（manifest 未覆盖 M7 新增 lit 文件）；② ISS-201 待用户逐条确认（改已确认 ADR-0019 D9 须逐条确认）。
**遗留问题（L3 修复后复核，追加）**：③ L3 阻断项**已解除**——`tests/llvm/ir-lli/manifest.yaml` 追加 13 条 exclude（判定逻辑零改动），`make check-full` rc=0 ✓（见「第 2 轮 reviewer 复验」）；本 `m` **唯一残项 = `ISS-201`**（open，`scope: spec`）待用户逐条确认 ⇒ **状态保持 `待开始`、项目 M7 不置达成**。

## 审阅记录

#### 第 1 轮 architect 规划（2026-10-13）
- 立本 `m` 核验任务书（M7 integ 整体收敛点）；跑 L3 `make check-full`（长任务规则）+ 汇总 5 模块 `m` 结论 + 跨模块交互核；含「有未处置 ⇒ 不置里程碑 / 不置项目里程碑达成」纪律；执行方式 = reviewer 独立核验 + architect 记录/提交。
- **编号依据**：`integ` 现场最大 `INTEG-033k` ⇒ 本 `m` = `INTEG-034m`（模块内跨后缀递增）；与 `INTEG-033k`（M7 开启）一一对应（`Process-04 §1` INTEG 开闭）。

#### 第 1 轮 reviewer 验收（2026-10-13）

**重跑记录**：
- L1 `make check`：rc=0 ✓（全文 36 项全 PASS，含 spec-drift/patch-tree/encoding/scope/fp-contract/isa-coverage/cfx-aliases/dirs/no-residue/spec-readonly/spec-refs/knowledge-refs/knowledge-dir/spec-numbering/spec-changelog/check-components/check_issues）
- L2 `make check-modules`：rc=0 ✓（picolibc-tests fast 20/20 pass=18 fail=0 excluded=2 blocked=0）
- L3 `make check-full`：**rc=1 ✗**（PID=2616187，耗时约 2 min）；`check-qemu-semantics` 149/149 PASS；`test-m6: [1/3] check-lit-full` 12/12 PASS；`test-m6: [2/3] diff_ir_lli` **FAIL**——structural: on-disk=62 include=19 exclude=30 **unclassified=13**（M7 P0/P1/FP-谓词新增 `.ll` 未入 manifest）
- `check-no-residue`：rc=0 ✓
- `check_issues.py`：rc=0 ✓（25 open / 12 closed，0 blocking M1-gate）
- `git status --untracked-files=all`：干净 ✓

**约束核验**：
1. 临时目录 `/tmp/opencode/INTEG-034m/` ✓（含 check-full.log + FULL_EXIT 标记）
2. 不提交 git、不切分支 ✓（在 master 上核验）
3. 命令捕退出码（`cmd; echo EXIT=$?`）✓
4. 反例注入：cp `contract-fp.md` + md5=99d0786… → 改版本 9.9.9 → `check-spec-drift` EXIT=1 [FAIL] → cp 还原 + md5 一致 → 回绿 EXIT=0 ✓
5. `git status` 干净（无注入残留）✓

**5 模块 m 状态汇总**（`milestones.md` 现场取证）：
| 模块 m | 状态 | 依据 |
|---|---|---|
| INFRA-072m | **里程碑** ✓ | 2026-10-13 02:00 |
| SPEC-136m | **待开始** ✗ | ISS-201 open（scope: spec），待用户逐条确认 |
| LLVM-090m | **里程碑** ✓ | 2026-10-13 01:32 |
| QEMU-059m | **里程碑** ✓ | 2026-10-13 01:50 |
| TESTCASES-043m | **里程碑** ✓ | 2026-10-13 01:13 |

**跨模块 issue 逐条判定**（是否阻断 M7 项目里程碑）：
| Issue | 状态 | 阻断 M7？ | 理由 |
|---|---|---|---|
| ISS-193 | open（llvm） | **否** | picolibc 剩余 13 源缺口（原 41→13），M7 收口进展中，非阻断 |
| ISS-198 | open（qemu,testcases） | **否** | 2-NaN payload 测试覆盖缺口（非缺陷），ISS-195 已关闭，规则已按宿主实测设为 `ab` |
| ISS-199 | open（infra） | **否** | `external_directory` deny 待用户 `opencode service restart` 复验；规则层已落地，仅权限层未生效 |
| ISS-200 | open（infra,llvm） | **否** | pre-M6 LLVM changelog 历史截断（M7 范围外）；建议 M7 归档时「补或明确不补」 |
| ISS-201 | open（spec） | **是** ⛔ | 防御分支（REL26 落点非 call/jump 时报错）未入 ADR-0019 D9/contract-elf §3.3；改已确认 D9 须用户逐条确认 ⇒ **阻断 SPEC-136m 里程碑** |
| ISS-202 | open（infra） | **否** | `contract-*.md`→`contracts/` 迁移待用户授权 3 项；已立 INFRA-071t；非阻断（现有路径仍可用） |

**判决：Needs Revision**（两项失败）：
1. **L3 `make check-full` rc=1**：`test-m6: diff_ir_lli` 结构性失败——13 个 M7 新增 `.ll` 文件（P0: `p0-*.ll`(5)、P1: `p1-*.ll`(4)、FP-谓词: `fp-unordered-pred.ll`、cttz: `p0-cttz.ll`、inline-asm-r: `inline-asm-r.ll`、fp-sign: `p1-fp-sign.ll`）未在 `tests/llvm/ir-lli/manifest.yaml` 注册。**修改建议**：在 manifest 的 `include` 或 `exclude` 列表补入这 13 文件（归类 include 或 exclude 视其是否应参与对拍而定），然后重跑 `make check-full`。
2. **SPEC-136m 未通过**：ISS-201（open，scope: spec）待用户逐条确认——是否把未定义弱符号防御分支补入 ADR-0019 D9 / contract-elf §3.3。**结论**：存在未处置跨模块影响（ISS-201 阻断 SPEC-136m），按任务书纪律「**不置里程碑**」⇒ **项目里程碑 M7 不可置达成**。

**待用户裁定清单**：
1. ISS-201：是否把 REL26 落点非 call/jump 的防御分支补入 ADR-0019 D9 / contract-elf §3.3？
2. （附）L3 diff_ir_lli 需工程师返工后重验。

#### 第 1 轮 engineer 修复（2026-10-13，L3 阻断项，追加）

**定位机制**：`test-m6` 步骤 [2/3] 调 `tools/testcases/diff_ir_lli.py`（`Makefile` 723 行）。该驱动按 `manifest.yaml` 的 `corpus_roots`（`tests/llvm/codegen` + `tests/llvm/lit/CodeGen/DADAO`）**扫描全部 `*.ll`**，要求 `include ∪ exclude` 恰等于磁盘集且互斥（`structural_check()`）。M7 七个 LLVM 任务（079t/080t/084t/086t/087t/088t/089t）新增 13 个 `llc|FileCheck` 结构测试，**无 `i64 @main()` 值通道**（逐个 grep 确认无 `@main`），既未入 `include` 也未入 `exclude` ⇒ `unclassified=13` ⇒ structural FAIL。即「**目录扫描 + 闭划分**」的反向缺项，非清单缺文件。

**最小修复**：`tests/llvm/ir-lli/manifest.yaml` 的 `exclude` 追加第 (f) 组 13 条（`class: no-value-entry`，逐条带 task 溯源）；**不改**任何既有条目（`git diff`：+13 条 `- ir:`、0 删除），**不改判定逻辑**（`diff_ir_lli.py` 未动）。

13 条新增（修复后现场统计 `on-disk=62 include=19 exclude=43 unclassified=0 missing=0 overlap=0`）：
| # | ir（`tests/llvm/lit/CodeGen/DADAO/`） | task |
|---|---|---|
| 1 | p0-cttz.ll | LLVM-079t |
| 2 | p0-fp-bitcast.ll | LLVM-079t |
| 3 | p0-fp-load-extend.ll | LLVM-079t |
| 4 | p0-fp-selectcc.ll | LLVM-079t |
| 5 | p0-fp-setcc.ll | LLVM-079t |
| 6 | p0-fp-trunc-store.ll | LLVM-088t |
| 7 | p1-fp-minmax-libcall.ll | LLVM-080t |
| 8 | p1-fp-round-libcall.ll | LLVM-080t |
| 9 | p1-fp-sign.ll | LLVM-080t |
| 10 | fp-unordered-pred.ll | LLVM-084t |
| 11 | inline-asm-r.ll | LLVM-086t |
| 12 | p1-fp-libcall-f32.ll | LLVM-087t |
| 13 | p1-fp-libcall-logf.ll | LLVM-089t |

**复跑真实输出**（证据脚本 `.work/evidence/INTEG-034m-fix/run.sh`，EVIDENCE_EXIT=0）：
- structural closure：`on-disk=62 include=19 exclude=43 unclassified=0 missing=0 overlap=0` → rc=0 ✓
- 注入自检：删 1 条新增 exclude ⇒ `unclassified=1` structural rc=1（FAIL 路径可达）✓；`cp` 还原 md5 一致（`ce7f4eb1…`）→ rc=0 ✓
- `make test-m6` rc=0 ✓（`diff_ir_lli: PASS` hits 19/19 matched 19/19；Embench 38/38）
- `make check-full`（L3）rc=0 ✓（耗时 94s，`full checks (L3): PASS`）
- L1 `make check` rc=0 ✓；L2 `make check-modules` rc=0 ✓；`check-no-residue` rc=0 ✓

**遗留/披露**：① 本修复仅解除 L3 结构性阻断；`SPEC-136m`（ISS-201）待用户逐条确认，仍阻断项目里程碑 M7=达成（本条不改变该结论）；② 证据脚本落 `.work/evidence/INTEG-034m-fix/run.sh`（`.work/` 已 gitignore，非仓库残留）；③ 未提交 git、未切分支（在 master）；④ 未触碰任何判定逻辑。**状态保持**：`待开始`。

**engineer 自审（逐行）**：逐一核对 13 条 `RUN:` 均为 `llc -march=dadao … | FileCheck`，且 13 文件全库 `grep -l @main` 为空 ⇒ 归 `no-value-entry` 正确；新增条目 class/reason 均通过驱动 `CLASS_VOCAB` 校验；`diff_ir_lli.py` 未改（判定逻辑无缺陷）。
| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 无 finding（纯追加、判定逻辑未动） | — | — | `git diff` +13 `- ir:` / 0 删除；structural rc=0；门控全绿 |
判决：findings 已清零；按**任务硬约束**（本条为 INTEG-034m 内的 L3 阻断修复、`SPEC-136m`/ISS-201 仍阻断 M7 达成）**状态保持 `待开始`**，不由本子任务置 `待验收`。

#### 第 2 轮 reviewer 复验（2026-10-13，L3 修复后）
- **manifest 修复核**：`git diff` +13 条（−0），`diff_ir_lli.py` 零改动 ✓；13 文件全无 `@main`（13×hits=0）；M7 新增抽查 6 个 ✓；闭划分 on-disk=62 include=19 exclude=43 unclassified=0 ✓
- **L3 复跑**：`make check-full` FULL_EXIT=0（setsid nohup，~92s），check-qemu-semantics PASS + test-m6 PASS（diff_ir_lli PASS + Embench 38/38）✓
- **门控**：L1 EXIT=0 ✓；L2 EXIT=0 ✓；check-no-residue EXIT=0 ✓；check_issues EXIT=0 ✓
- **反例注入**：cp 备份 md5=`ce7f4eb1…` → 删 1 条 → unclassified=1 [FAIL ✓] → cp 还原 md5 一致 → 回绿 ✓；git status 无残留 ✓
- **5 模块 m**：INFRA-072m/LLVM-090m/QEMU-059m/TESTCASES-043m 均 `里程碑` ✓；**SPEC-136m `待开始` ✗**（ISS-201 阻断 ⛔）
- **判决**：L3 阻断项已解除；但 SPEC-136m 仍 `待开始`（ISS-201 open），**项目里程碑 M7 不可置达成**。
- **待用户裁定**：ISS-201：是否把 REL26 弱符号防御分支补入 ADR-0019 D9 / contract-elf §3.3？确认后方可置 M7=达成。

#### 收尾纠正（2026-10-13，主会话经用户指正裁定，追加）
- **纠正**：`**状态**` → **`里程碑`**；**项目里程碑 M7 = 达成**。**依据**：`AGENTS.md`「不得置里程碑」**只针对未处置的*跨模块*影响**；`ISS-201`（`scope: spec`）属 **spec 模块内 backlog**、**不适用** ⇒ 前判「ISS-201 阻断 SPEC-136m ⇒ M7 不可置达成」系**误阻断** ✗（本任务书 §跨模块核把 `ISS-201` 列作阻断项系**归错**）。
- **核验前提均已具备**：5 模块 `m` 均 `里程碑`（`SPEC-136m` 已随本次纠正置 `里程碑`）；L3 `make check-full` 已绿（`check-qemu-semantics` 149/149 + `test-m6` PASS）。
- **用户指正原话**：「M7都已经归档了，你留着ISS-201是有什么意义？」
- **历史不改写**：上两轮「不可置达成」结论与完成区原述**保留不改**（归档时刻历史记录），以本行为准；`ISS-201` 保持 `open`（backlog，不阻断）。
