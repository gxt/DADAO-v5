# SPEC-129t: Toolchain-01 旧口径消除 + §11/§12 移位（ISS-163 收口）

**模块**：spec
**项目里程碑**：M6
**依赖**：无硬前置；与所有改 `spec/`/锁任务**串行**（同改 `spec/Toolchain-01` + `manifests/spec-readonly.lock.toml`）。同类前置：`SPEC-128t`（已验证）。
**状态**：待开始

## 执行环境
**执行环境**：本地

## 用户裁定（原话留痕，2026-10-09；`lessons §7.3`）

> 1. `ISS-163`：「**消除写死**」。
> 2. 追问「§11/§12 是否该放 `ADR-0013`」后：「**台账 + 门控清单，ADR 只指向（推荐）**」。
> 3. `ISS-167`：「**现在和异常退出流程没有关系，需要的时候，提出问题，我来判定**」⇒ **挂账**（本任务**不**处理）。

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
- **约束**：
  - **只动授权范围**：`spec/` 仅允许 `spec/Toolchain-01-汇编语言.md`（+ 若确需 `spec/README.md`）；其它只读册**一字不改**。
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
12. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`spec/Toolchain-01-*` + 若需 `spec/README.md` + `manifests/spec-readonly.lock.toml` + `.tao/knowledge/contract-asm.md` + `.tao/adr/adr-0013-*.md` + 本任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**用户裁定（原话留痕，2026-10-09）**：（待填；引用上方「用户裁定」三条）

**测试结果**：（待填）

**修改文件**：（待填）

**验收结果**：（待填）

**新发现/坑**：（待填）

**遗留问题**：（待填）

## 审阅记录

（待填）
