# SPEC-129t: Toolchain-01 旧口径消除 + §11/§12 移位（ISS-163 收口）

**模块**：spec
**项目里程碑**：M6
**依赖**：无硬前置；与所有改 `spec/`/锁任务**串行**（同改 `spec/Toolchain-01` + `manifests/spec-readonly.lock.toml`）。同类前置：`SPEC-128t`（已验证）。
**状态**：已验证

## 执行环境
**执行环境**：本地

## 用户裁定（原话留痕，2026-10-09；`lessons §7.3`）

> 1. `ISS-163`：「**消除写死**」。
> 2. 追问「§11/§12 是否该放 `ADR-0013`」后：「**台账 + 门控清单，ADR 只指向（推荐）**」。
> 3. `ISS-167`：「**现在和异常退出流程没有关系，需要的时候，提出问题，我来判定**」⇒ **挂账**（本任务**不**处理）。
> 4. （**追加 2026-10-09，用户裁定 8**）`spec/DADAO-22`（SBI）示例中 **5 处 `rb3` 当 scratch**（改布局后 `rb3`=TP）：**「改 + 同步锁」** ⇒ **并入本任务**（同一类「册旧口径同步」）——改示例为**真临时寄存器**（`rb8`/`rb9`）+ 同步 `DADAO-22` 的 `sha256` 锁。

> **授权（`Process-06 §2`）**：`spec/Toolchain-01-汇编语言.md` 为**只读册**，改册须用户**事先**明确授权。上列裁定 1/2 即授权：**消除写死 + §11/§12 移出（台账 + 门控清单）+ `ADR-0013` 只加指向**；改册**同一变更**内**必须**同步 `spec-readonly.lock.toml` 的 `sha256`（`Process-06 §5`）。

## 背景：`ISS-163` = 三处旧口径（实测事实，主会话已核；**勿改结论**）

| 位置 | 旧口径 | 事实（`contracts/opcodes.yaml` 实测） |
|---|---|---|
| `Toolchain-01 §5`（约 L151/152） | 「`scope: excluded` 的格式（`crrr`/`crii`/`ciii`）」 | `crrr`/`ciii` 已 → `m1`；**仅 `crii` 仍 `excluded`** |
| `Toolchain-01 §11`（约 L260） | 「**9 个** M1 格式类与 **152 条** M1 指令」 | **11 个格式类 / 155 条**（`scope: m1`）；全表 227 = `m1`155 + `fp`60 + `excluded`11 + `m3`1；12 format |
| `Toolchain-01 §13`（约 L285） | 「cfx 属 `scope: excluded`」 | cfx 4 条（`cfx2rd`/`cfx2rc`/`trap`/`escape`）已 → `m1` |

> 明细：`crii` = `cfxld`/`cfxst`（仍 `excluded`）；`crrr` = `cfx2rd`/`cfx2rc`、`ciii` = `trap`/`escape`（均 `m1`）。m1 格式类 = `rrrr`/`rrri`/`rrii`/`riii`/`iiii`/`rwii`/`orrr`/`orri`/`oiii`/`crrr`/`ciii`。

## 目标与落点（**移位**定型）

- **`§11`（实现状态与缺口）→ 台账/投影**：唯一 home = 既有投影 `.tao/knowledge/contract-asm.md §11`（该表即 §11 的归一化投影，**已存在**）；**缺口** = 既有台账 `.tao/knowledge/issues.yaml`。**不新建文档**（`AGENTS.md`「新增文档三问」）。
- **`§12`（机器检查）→ 门控清单**：**收敛为门控名**，落**既有门控说明**——`spec/README.md` 投影表 `Toolchain-01` 行 ③ 列（已列 `check_asm_prose.py`/`check_asm_list_consistency.py`/`check_asm_list_drift.py`）；如需补门控名可改 `spec/README.md`（v5 自定册，本次授权句已覆盖「落既有门控说明」）或 `AGENTS.md`（门控名清单）。**不新增长叙述**。
- **`ADR-0013`（决策册）**：**只加指向**（如「实现状态见 `contract-asm.md §11`；机器检查见 `spec/README.md` 投影表」）——**不把状态/门禁搬进 ADR**。
- `Toolchain-01` 内 §11/§12 **内容移除**；**保留标题 + 一行指针**（**不重编号**——全库以 `§13`/`§附` 为引用锚，重编号会破坏既有引用）。

## 接口规范

- **输入**：
  - `spec/Toolchain-01-汇编语言.md`（只读册；§5 L151-152、§11 L258-270、§12 L274-281、§13 L287；册内 `见 §11` 交叉引用在 §2.4/§2.5/§6.2/§9）。
  - `spec/DADAO-22-SBI-主管系统二进制接口.md`（只读册；**5 处 `rb3` 当 scratch** 的代码示例，位于 L190/206/223/256/273 附近，形如 `set.rb rb3, rd3` + `jump [rb3, rd0, 0]`）。（**追加 2026-10-09，用户裁定 8**）
  - `manifests/spec-readonly.lock.toml` 的 `DADAO-22` 段 `sha256`（现值 `e439d62d602fad8f89132545b4d555c1db045ab0994a67dc7a62f5125cd988a6`）。（**追加 2026-10-09**）
  - `contracts/opcodes.yaml`（`scope`/`format` **真源**）。
  - `.tao/knowledge/contract-asm.md`（投影；§11 状态表 + §12 机器检查；§5/§13 已对齐新口径——**作对照**）。
  - `.tao/knowledge/contract-asm-list.md`（生成投影，**真源之一**；其头部含「227 = …」等**派生**计数）。
  - `manifests/spec-readonly.lock.toml`（`Toolchain-01` 段 `sha256` 现值 `9d6164bc9fed20039a6a1e1558ccd5a604cbae118f38fe88706b7ea2abe7ee92`）。
  - `.tao/adr/adr-0013-assembly-syntax.md`（`Accepted`，D1–D11）。
  - `spec/README.md` 投影表（`Toolchain-01` 行 ③ 列）。
  - **用户授权原话**（上方）。
- **输出**：
  1. `spec/Toolchain-01-汇编语言.md`：
     - §5（约 L151-152）：把 `scope: excluded` 的格式列表改为**仅 `crii`**；`crrr`/`ciii` 注明 `scope: m1`（对齐 `contract-asm.md §5` 口径）。
     - §11：**内容移除**（标题 + 一行指针 → `contract-asm.md §11` / `issues.yaml`）；旧计数**不保留为数字**。
     - §13（约 L287）：「cfx 属 `scope: excluded`」改为「`cfx2rd`/`cfx2rc`/`trap`/`escape` = `scope: m1`；`cfxld`/`cfxst` = `scope: excluded`」（对齐 `contract-asm.md §13` 口径）。
     - §12：**内容移除**（标题 + 一行指针 → 门控名清单）。
     - 册内 `见 §11` 交叉引用（§2.4/§2.5/§6.2/§9）改指 `contract-asm.md §11`。
  2. `.tao/knowledge/contract-asm.md`：§11 为**唯一 home**（去写死计数 → 指向真源）；§12 收敛为门控名/指针（与册同落点）；§5/§13 核对（如已一致则不改）。
  3. `manifests/spec-readonly.lock.toml`：`Toolchain-01` 段 `sha256` **同步**（改毕 `sha256sum` 实测 + 追加授权说明注释）。
  4. `.tao/adr/adr-0013-assembly-syntax.md`：**只追加指向句**（+ 用户原话留痕），**不搬状态/门禁**。
  5. （**追加 2026-10-09，用户裁定 8**）`spec/DADAO-22-SBI-主管系统二进制接口.md`：把 **5 处**示例中当 scratch 的 `rb3` 改为**真临时寄存器**（`rb8`/`rb9`；`rb3`=TP，不可当通用临时）；改毕 `sha256sum` 实测并**同步** `manifests/spec-readonly.lock.toml` 的 `DADAO-22` 段 `sha256`（追加授权说明注释）。**只改示例寄存器选择，不动其余口径**。
- **约束**：
  - **只动授权范围**：`spec/` 仅允许 `spec/Toolchain-01-汇编语言.md`（+ 若确需 `spec/README.md`）；其它只读册**一字不改**。
  - （**追加 2026-10-09，用户裁定 8**）**授权范围扩至 `spec/DADAO-22-SBI-主管系统二进制接口.md`**：**仅**改 5 处示例的 scratch 寄存器（`rb3`→`rb8`/`rb9`）+ 同步其 `sha256` 锁；`DADAO-22` 其余内容**一字不改**。
  - **不改实现**：`components/**`/`tools/**`/`tests/**` **不碰**（`tools/spec/*` 现有 3 个门控已覆盖本规范，**无需改门控脚本**）；`contracts/**` **不碰**。
  - **不新建文档**（`AGENTS.md`「新增文档三问」）；**不新增长叙述**。
  - **消除写死 = 修一类**（`AGENTS.md`「修复须修一类」）：`Toolchain-01` 与 `contract-asm.md` 内**凡以数字陈述** M1 格式类数 / 指令条数者（含 §1 的「11 类」、§11 的「9 个/152 条」、引言/§12 的「227 条」等），改为**指向真源**（`contracts/opcodes.yaml` / 生成投影 `contract-asm-list.md`）或**去数字**；**唯一允许保留数字处** = 生成投影 `contract-asm-list.md`（其计数由生成器派生自真源）。
  - **不重编号** `Toolchain-01` 章节（保留 §11/§12 标题，避免破坏 `§13`/`§附` 引用）。
  - 只读册改动**同一变更**内同步 `sha256` 锁（`Process-06 §5`）。
  - 与所有改 `spec/`/锁任务**串行**。

## 硬约束

- **临时目录** `/tmp/opencode/SPEC-129t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/SPEC-129t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee` 吞退出码。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**（`INTEG-023k §E-4`）：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**或指向真源。
- 复杂命令输出留 `.work/log/spec/SPEC-129t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **§5 改对**：册内 §5 段不再把 `crrr`/`ciii` 归为 `scope: excluded`；明确 **`crii` 为唯一仍 `excluded`**（与 `contracts/opcodes.yaml` 实测一致）。
2. **§13 改对**：册内不再出现「cfx 属 `scope: excluded`」旧口径；给出 `crrr`/`ciii`=`m1`、`crii`=`excluded` 之分。
3. **无写死计数残留（`grep` 判据）**：`spec/Toolchain-01-汇编语言.md` 内 `grep -nE '152|9 个 M1 格式类'` **无命中**；且册内以数字陈述 M1 格式类数/指令条数者**改为指向真源或去数字**（`grep` 佐证 + 逐处列出）。`contract-asm.md §11` 计数同样指向真源。
4. **§11 移位到位**：`Toolchain-01` 无 `## 11. 实现状态与缺口` 的**状态内容**（仅留标题 + 一行指针）；**新落点** `contract-asm.md §11` 含状态表且**不写死计数**；缺口在 `issues.yaml` 有指针/对应条目标注。
5. **§12 移位到位**：`Toolchain-01` 无 `## 12. 机器检查` 的**内容**（仅留标题 + 一行指针）；**门控名**（`check_asm_prose`/`check_asm_list_consistency`/`check_asm_list_drift`）在**既有门控说明**（`spec/README.md` 投影表 `Toolchain-01` 行 ③ 列）确实存在（`grep` 佐证）。
6. **交叉引用**：册内 `见 §11`（§2.4/§2.5/§6.2/§9）均改指 `contract-asm.md §11`；`grep` 无指向已移出内容的悬空引用。
7. **`ADR-0013` 只加指向**：`git diff` ADR-0013 **仅新增指向句**（+ 用户原话留痕），**无**状态表/门禁表搬入。
8. **锁同步**：`Toolchain-01` 段 `sha256` == 实测；`make check-spec-readonly` **EXIT=0**；**未改册** `sha256` 行**逐条未变**（`git diff` 中既有 `sha256` 行 `-`/`+` 仅 1/1）。
9. **授权范围**：`git -c core.quotepath=false diff --name-only | grep '^spec/'` 仅 `spec/Toolchain-01-汇编语言.md`（如确改 `spec/README.md` 则一并列出并在完成区说明理由）。
10. **门控全绿**：`make check` **EXIT=0**（改动落在 `spec/`/锁/`contract-asm.md`，均在门控覆盖内，**不得**以「纯文档豁免」为由跳过）。
11. **一键证据脚本**：`.work/evidence/SPEC-129t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如把 §11 旧计数 `152` 注回 ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
12. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`spec/Toolchain-01-*` + `spec/DADAO-22-*` + 若需 `spec/README.md` + `manifests/spec-readonly.lock.toml` + `.tao/knowledge/contract-asm.md` + `.tao/adr/adr-0013-*.md` + 本任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。
13. （**追加 2026-10-09，用户裁定 8**）**`DADAO-22` 示例 scratch 改对 + 锁同步**：`spec/DADAO-22-SBI-主管系统二进制接口.md` 内**不再有** `rb3` 充当 scratch 的示例（`grep -nE 'rb3' ` 无「当临时寄存器」用法；`set.rb rb3`/`jump [rb3,…]` 已改 `rb8`/`rb9`）；`DADAO-22` 段 `sha256` == 实测（`make check-spec-readonly` **EXIT=0**）；**未改册** `sha256` 行**逐条未变**；`make check` **EXIT=0**。

## 完成区

**用户裁定（原话留痕，2026-10-09）**：1「**消除写死**」。2「**台账 + 门控清单，ADR 只指向（推荐）**」。3 `ISS-167`「现在和异常退出流程没有关系，需要的时候，提出问题，我来判定」⇒ **挂账**（本任务不处理）。4（追加）`DADAO-22` 示例 5 处 `rb3` 当 scratch：「**改 + 同步锁**」⇒ 改真临时寄存器。

**测试结果 / 验收结果**：证据脚本 `.work/evidence/SPEC-129t/run.sh` **41/41**，`RUN_EXIT=0`（含 **2 例注入自检**：回灌 §11 计数 / `rb8→rb3` ⇒ 目标断言 FAIL ⇒ `cp`+md5 还原 == 注入前 ⇒ 回绿；全程文件 md5 一致）；门控各 **EXIT=0**：`make check`、`make check-patch-tree`、`make check-spec-readonly`、`make check-spec-refs`、`make check-spec-drift`（日志 `.work/log/spec/SPEC-129t-*.log`）。

**三处旧口径改法**：`§5`→「特权 cfx 格式（`crrr`/`crii`/`ciii`）…；`crrr`/`ciii`=`scope: m1`、`crii`=`scope: excluded`」；`§13`→「`cfx2rd`/`cfx2rc`/`trap`/`escape`=`m1`；`cfxld`/`cfxst`=`excluded`」；`§11`→内容移除 + 指针。

**写死计数判定表**（可机械核对→去数字/指向真源；示例性→保留；完整表 `.work/log/spec/SPEC-129t-count-table.md`）：

| 处 | 旧值 | 判定 |
|---|---|---|
| TC 引言 / contract-asm 全表 | 228/227 条 | 改→去数字+指向真源 |
| TC §1 / contract-asm §1 | 11 类 | 改→去数字+指向 `opcodes.yaml` |
| TC §4.2 / contract-asm §4.2 | 6/8/20 条 | 改→去数字（留助记符枚举） |
| TC §11 | 9 个/152 条 | 移除（内容移出） |
| contract-asm §11 | 11/155 条、8/4 条 | 改→去数字（唯一 home） |
| 两册 §6/§7/展开长度（伪指令/指导符/`≤4 条`/`3 片`/`恰好 2 个`） | — | 保留（示例性/非 M1 条数，冻结 `ADR-0013 D11`） |

**§11/§12 新落点**：`§11`→`.tao/knowledge/contract-asm.md §11`（状态表，去数字）+ `issues.yaml`（缺口指针）；`§12`→`spec/README.md` 投影表 `Toolchain-01` 行 ③（`check_asm_prose`/`check_asm_list_consistency`/`check_asm_list_drift`）。册内 `§2.4/§2.5/§6.2/§9` 的「见 §11」均改指 `contract-asm.md §11`。

**`DADAO-22` 改动**：5 处 `set.rb rb3`+`jump [rb3, rd0, 0]` → `rb8`（真临时寄存器；`rb3`=TP）。

**两册锁**：`Toolchain-01`/`DADAO-22` 段 `sha256` == 实测（含授权注释）；其余 `sha256` 行未变（`git diff` 仅 2 `-`/2 `+`）。

**修改文件**：`spec/Toolchain-01-汇编语言.md`、`spec/DADAO-22-SBI-主管系统二进制接口.md`、`manifests/spec-readonly.lock.toml`、`.tao/knowledge/contract-asm.md`、`.tao/adr/adr-0013-assembly-syntax.md`、本任务书。**未改** `spec/README.md`（③ 门控列已存在，无需改）。

**新发现/坑**：`contract-asm.md §11` 状态表（新记法/伪指令/`.dd.*`/`-multiple-to-single` 标「待实现」）**疑似已由 M4「汇编器遗留收口」实现**（lit 有 `m4-directive-dd.s`/`m4-pseudo-set.s`/`multiple-to-single-*.s` 等）；任务范围要求 §11 内容原样移出，**未改状态结论**，建议后续 spec 任务核对并对齐。

**遗留问题**：① §11 状态表疑似陈旧（见「新发现」）——建议另立任务核对；② §11 缺口项（新记法/伪指令/`.dd.*`/选项/ABI 别名）在 `issues.yaml` **无逐条条目**，本次以**指针**（§11 → `issues.yaml`）满足可追溯，如需逐条 ISS 编号另立任务；③ `ISS-167` 按裁定**挂账**（未处理）。

## 审阅记录

#### 提交留痕（architect，2026-10-09）

- **档位**：architect 规划产出（立项新任务 + 联动台账），内容完整、无未决 ⇒ **正常提交**（无 `WIP:` 前缀）。
- **提交号**：`f1e32e4`（`M6: 立项 Toolchain-01 旧口径消除 + §11/§12 移位（ISS-163 收口；ISS-167 挂账）`）；**只 commit、未 push**。
- **文件集对账**（显式 staging，逐个路径，**禁** `git add -A`）：`git diff --cached --name-only` = `.tao/knowledge/milestones.md` / `.tao/tasks/integ/INTEG-023k-M6启动与分解.md` / `.tao/tasks/spec/SPEC-129t-Toolchain-01旧口径消除与移位.md`（新）——与本轮立项范围**逐条相等**（**无漏提 / 无多提 / 无越界**）。

#### 第 1 轮 engineer 自审（2026-10-09）

**审查范围**：改动源码级逐行审查——`spec/Toolchain-01`（§1/§2.4/§2.5/§4.2/§5/§6.2/§9/§11/§12/§13）、`contract-asm.md`（§1/§4.2/§11/§12/投影头）、`DADAO-22`（§4 5 处）、`spec-readonly.lock.toml`、`adr-0013`；证据脚本 `run.sh`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `contract-asm §11` 首版仅去数字首行，「伪指令 8 条/`.dd.*` 4 条」仍写死，与验收 4「§11 不写死计数」有张力 | ✅已修 | §11 两行去数字 | 证据 B11/B12 PASS + `grep` |
| F2 证据脚本初版 `check` 的 rc 恒为默认 0（未捕获真实退出码） | ✅已修 | 重构 `chk_f`/`chk_re`/`chk_sha`，捕获真实 rc | 日志 `rc=1`（0 命中）/`rc=0`（有命中）属实 |
| F3 证据脚本初版 baseline 期望值误判（部分字符串出现 2 次） | ✅已修 | 修正 C2b/C8 期望值 | baseline 41/41 PASS |
| F4 注入自检只断言「FAILS>0」，可能只因**锁**检查失败而非目标断言 | ✅已修 | 加「目标断言确已 FAIL」断言 | INJ「目标断言(B1/D1)确已 FAIL」PASS |
| F5 交叉引用：册内 §2.4/§2.5/§6.2/§9 的「见 §11」是否全部改指、有无悬空 | ✅已核 | 4 处均改指 `contract-asm.md §11` | `grep -nE '见 §|§11'` 无「见 §11」残留 |
| F6 只读册改动是否同变更同步 `sha256`；既有 `sha256` 行是否误改 | ✅已核 | 2 册锁同步 + 授权注释 | `check-spec-readonly` EXIT=0；diff 仅 2 `-`/2 `+` |
| F7 还原纪律：脚本是否用 `git checkout/restore/stash/show` | ✅已核 | 全程 `cp`+`md5`，无 git 还原 | 脚本无 git 还原命令；`md5sum -c` OK |
| F8 `contract-asm §11` 状态表「待实现」疑似陈旧（M4 已实现）——但本任务未授权改状态 | ⏸延后 | 未改（范围外） | 登记「新发现/坑」+ 遗留 ① |
| F9 §11 缺口项在 `issues.yaml` 无逐条 ISS 条目 | ⏸延后 | 以指针（§11→`issues.yaml`）满足可追溯 | 登记遗留 ② |

**判决**：F1–F7 已修/已核；F8/F9 属**任务范围外**（改状态结论/建 ISS 条目均未获授权），如实登记遗留，**不标「遗留:无」**。任务状态置「待验收」。

#### 第 1 轮 reviewer 验收（2026-10-09）

**重跑证据脚本**：`bash .work/evidence/SPEC-129t/run.sh` → **41/41 baseline PASS, 0 inj FAIL, EXIT=0**。完整日志 `/tmp/opencode/SPEC-129t-review/run.log`。

**门控**：`make check` EXIT=0；`make check-spec-readonly` EXIT=0；`make check-spec-refs` EXIT=0；`make check-spec-drift` EXIT=0；`make check-patch-tree` EXIT=0（日志 `/tmp/opencode/SPEC-129t-review/*.log`）。

**独立注入反例**（与 engineer 不同）：注入 `contract-asm.md` L19 `crii` 从 `excluded` → `m1`（语义错误）→ md5 从 `10e02c…` → `65a78d…`；重跑脚本 EXIT=0（脚本未覆盖 `contract-asm.md §5` 的 `crii` scope 校验——**已知脚本盲区**，不阻塞，因 `opcodes.yaml` 实测 `crii` scope=`excluded` 且 Toolchain-01 已正确改写）。另注入 TC L15 `11 个 M1 格式类`（回灌写死计数）→ md5 变化 → 重跑脚本 EXIT=1（E1 sha256 不匹配即 FAIL）→ `cp` 还原 → md5=`31a3e5…` == 注入前 → 重跑 EXIT=0。全程 `cp`+md5 对账，无 `git checkout/restore/stash`。

**① 三处旧口径**（`opcodes.yaml` 实测：m1=155, excluded=11, total=227; crrr/ciii→m1, crii→excluded; cfx2rd/cfx2rc/trap/escape→m1, cfxld/cfxst→excluded）：
- §5：「`crrr`/`ciii` 现为 `scope: m1`，`crii` 仍为 `scope: excluded`」✓
- §13：「`cfx2rd`/`cfx2rc`（`crrr`）与 `trap`/`escape`（`ciii`）为 `scope: m1`；`cfxld`/`cfxst`（`crii`）为 `scope: excluded`」✓
- §11：内容移除 + 指针 → `contract-asm.md §11` ✓

**② 写死计数残留扫描**（`grep -nE '[0-9]+ ?条|[0-9]+ ?个'` 两册共 30+ 命中，逐条判定）：

| 行 | 文本 | 判定 |
|---|---|---|
| TC L92/127 | `恰好 2 个`（寄存器对语法） | 保留（结构描述，非 M1 计数） |
| TC L168 | `18 条`（SimRISC 上游伪指令） | 保留（上游引用，非 M1 计数） |
| TC L172 | `8 条合成型`（§6.1 伪指令） | 保留（`ADR-0013 D11` 冻结，非 M1 指令） |
| TC L176 | `≤4 条`/`3 片`（`set.rd` 展开） | 保留（展开细节，非 M1 计数） |
| TC L192 | `10 条`（§6.2 删除伪指令） | 保留（删除清单枚举） |
| TC L180/188 | `2 条`/`4 条`/`1 条`（伪指令展开） | 保留（展开细节） |
| TC L217 | `4 条`（数据指导符） | 保留（§7 指导符枚举） |
| CASM L143 | `恰好 2 个`（寄存器对） | 保留（同 TC L92） |
| CASM L187-190 | `8 条`/`10 条`（伪指令） | 保留（`ADR-0013 D11` 冻结） |
| CASM L197 | `4 条`（数据指导符） | 保留（§7 枚举） |

**无写死 M1 格式类数/指令条数残留**（`228`/`227`/`152`/`155`/`11 类` 均无命中）✓

**③ 移位**：§11/§12 内容已移除（标题 + 一行指针）；`contract-asm.md §11` 含状态表（去数字指向 `opcodes.yaml`）；`spec/README.md` ③ 列含三门控名。册内 `见 §11` 交叉引用 4 处（§2.4/§2.5/§6.2/§9）均改指 `contract-asm.md §11`（`grep` 无「见 §11」残留）✓

**④ ADR-0013**：diff 仅新增 1 行指向句 + 用户裁定留痕，未搬状态/门禁正文 ✓

**⑤ DADAO-22**：5 处 `set.rb rb3`+`jump [rb3,rd0,0]` → `rb8`；`sha256` = `c0dea2…` == 实测 ✓

**⑥ git status**：仅 6 个预期文件（TC、DADAO-22、lock、contract-asm、ADR-0013、任务书）；无 `components/`/`tools/`/`tests/`；无 `_tmp/_orig/_rej/_preinject` ✓

**⑦ 遗留①**：`contract-asm.md §11` 状态表 L235-238 仍有 `待实现` 条目（新记法/伪指令/`.dd.*`）——engineer 如实登记为「新发现/坑」+ 遗留①，**未擅自改结论** ✓

**⑧ 不改上游册**：`git diff spec/` 仅含 `Toolchain-01` + `DADAO-22` 两册 ✓

**判决**：**Accepted**。41/41 证据脚本全绿 + 门控全绿 + 三处旧口径实测正确 + 写死计数无残留 + 移位到位 + 锁同步 + 授权范围未越界 + 注入自检 FAIL→还原→回绿 闭环。遗留①/②/③ 按裁定挂账。

#### 提交留痕（architect，2026-10-09）

- **档位**：reviewer 判 **Accepted** ⇒ **正常提交**（无 `WIP:` 前缀）。
- **提交号**：`82280d9`（`SPEC-129t: Toolchain-01 旧口径消除（§5/§13 改对、§11 去写死）+ §11→contract-asm/issues、§12→README 门控列、ADR-0013 只加指向 + DADAO-22 示例 rb3→rb8 + 两册锁同步`）；**只 commit、未 push**。
- **文件集对账**（显式 staging，逐个路径，**禁** `git add -A`）：`git diff --cached --name-only` = `spec/Toolchain-01-汇编语言.md` / `spec/DADAO-22-SBI-主管系统二进制接口.md` / `manifests/spec-readonly.lock.toml` / `.tao/knowledge/contract-asm.md` / `.tao/adr/adr-0013-assembly-syntax.md` / `.tao/tasks/spec/SPEC-129t-*.md`（本任务书）——与完成区「修改文件」声明**逐条相等**（**无漏提 / 多提 / 越界**）。
