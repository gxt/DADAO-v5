# SPEC-116t: `Toolchain-01` 修订（`§2.1` 大小写敏感 + `§1` M1 格式类口径同步）+ 投影/锁

**模块**：spec
**项目里程碑**：M5
**依赖**：`SPEC-115t`（**已验证**——`§1` 格式类口径须与 re-scope 后的 `scope` 事实一致）、`SPEC-119t`（哈希锁门控；与 `SPEC-113t`~`115t`/`117t` 同改 `spec/` ⇒ **串行**）
**状态**：待开始

> **⚠️ 前置（硬约束；用户授权原话并列落盘，2026-10-08）**：本任务将修改**上游只读册** `spec/Toolchain-01-汇编语言.md`。按新规则「**所有针对 spec 目录的修改，都应该经过我的允许，不能擅自进行**」（`spec/Process-06`；机制见 `SPEC-119t`）——**下发前必须取得用户明确允许，并将授权原话落盘；否则 BLOCKED**。落地时须**在同一变更内更新 `manifests/spec-readonly.lock.toml` 中 `spec/Toolchain-01-汇编语言.md` 的 `sha256` 锁**并在完成区记录用户授权原话；未更新锁 ⇒ `make check-spec-readonly` **FAIL**（`make check` 红）。
>
> **本任务已取得的用户授权（原话，逐字）**：
> - ① 「**允许（撤销不敏感条款）**」——对应 **`§2.1` 撤销「大小写不敏感」**；
> - ② 「**1、并入SPEC-116t**」——对应把「**同步 `spec/Toolchain-01 §1` 的 M1 格式类口径**」**并入本任务**（`SPEC-115t` 遗留事项；见 `milestones.md` M5 段 + `SPEC-115t` 完成区「新发现 1」/「遗留 3」）。
>
> **授权范围（严格遵守，超出即 BLOCKED）** = `spec/Toolchain-01-汇编语言.md` 的 **① `§2.1` 撤销「大小写不敏感」** + **② `§1` 格式类口径同步（9 种 → 11 类）** 两处；**该册其它节（`§2.2`~`§14`）不得改**；`spec/` 下**其它册**（`SimRISC-*`/`DADAO-*`/`Process-*`/`README.md`）一律不改。

## 执行环境
**执行环境**：本地

## 接口规范

- **背景**：`spec/Toolchain-01-汇编语言.md §2.1` 与 `.tao/knowledge/contract-asm.md §2.1` 现规定「助记符与寄存器名**大小写不敏感**（`ADD.SI` ≡ `add.si`）」，但 **LLVM MC 实现为大小写敏感**（`ADD.UO {RD8…}` 报错；`ISS-157`；`TESTCASES-029t` F3/`新发现`）。**用户裁定（`INTEG-019k D16`）：改为大小写敏感，撤销「不敏感」条款** ⇒ `ISS-157` 以「**条款撤销**」结案（**不是**"实现缺口"）。
- **输入（自包含）**：
  - `spec/Toolchain-01-汇编语言.md §2.1`（现行「大小写不敏感」句）。
  - **`spec/Toolchain-01-汇编语言.md §1`**（现行句：「**格式类（format）**：`contract-isa.md §2.3` 定义的 **9 种** M1 格式——`rrrr` `rrri` `rrii` `riii` `iiii` `rwii` `orrr` `orri` `oiii`（`crrr`/`crii`/`ciii` 属特权 cfx，`scope: excluded`）」——**待同步**）。
  - **`§1` 口径的事实源**：`contracts/opcodes.yaml`（**生成物**，由 `tools/spec/generate_opcodes.py` 产出）——各 `format` 的 `scope` 事实。**实测**（`python3` 读 yaml，逐 `format` 统计 `scope`）：`m1` 格式类 = **11** 个（`rrrr`/`rrri`/`rrii`/`riii`/`iiii`/`rwii`/`orrr`/`orri`/`oiii` + **`crrr`** + **`ciii`**）；**`crii` = `excluded`×2**（`cfxld_crii_cfx`/`cfxst_crii_cfx`）。**执行时须重测确认**（以实测为准）。
  - `.tao/knowledge/contract-asm.md §2.1`（同款投影句，含 `[Toolchain-01 §2.1]` 引用）。
  - `.tao/knowledge/contract-asm.md §1`（L18–L19，含「9 种 M1 格式类（`Toolchain-01 §1` 定义）」+「`SPEC-115t` re-scope 后 `m1` 另含 `crrr`/`ciii`」缓冲注记——**本任务须收敛为与 `§1` 一致的 11 类口径**）、`§5`（L168）、末尾表（L234）。
  - `.tao/knowledge/contract-isa.md §2.3`（L187 注）——格式类定义处，如含「9 种」/excluded 口径须同步（语言层无需改则不改）。
  - `.tao/knowledge/contract-asm-list.md`（**生成投影**，`tools/llvm/gen_asm_list.py`；助记符列/格式列——**仅在受影响时随生成器重跑**，**不得手改**）。
  - `.tao/knowledge/issues.yaml` 的 `ISS-157`（`scope: [llvm, spec]`）。
  - 门控：`tools/spec/check_asm_prose.py`、`check_asm_list_consistency.py`、`check_asm_list_drift.py`；`make check-spec-refs`；`make check-spec-readonly`（`tools/infra/check_spec_readonly.py`）。
- **输出**：
  1. **`spec/Toolchain-01 §2.1`**：把「助记符与寄存器名大小写不敏感（`ADD.SI` ≡ `add.si`）」**撤销/改写为大小写敏感**（明确措辞：助记符、寄存器名、伪指令、指导符等**区分大小写**；规范书写范式为**小写**；仅规范文档在**叙述**中大写属示例，不构成等价形式）。**撤销**须显式（非新增），保留变更痕迹（rev 说明/变更记录节）。
  2. **`spec/Toolchain-01 §1`（M1 格式类口径同步，用户授权 ②）**：把「格式类（format）：… 定义的 **9 种** M1 格式 …（`crrr`/`crii`/`ciii` 属特权 cfx，`scope: excluded`）」改写为**事实口径**——**11 类** M1 格式（9 种 + `crrr` + `ciii`；`cfx2rd`/`cfx2rc` = `crrr`、`trap`/`escape` = `ciii` 已 re-scope 为 `m1`）；`crrr`/`ciii` **不再**写 `scope: excluded`；**`crii` 据实写为仍 `scope: excluded`**（`cfxld`/`cfxst`，属 `SimRISC-12` deferred）。**事实源 = `contracts/opcodes.yaml` 的 `scope`（执行时实测）**；**不得臆断 `crii` 口径**——若实测与上述不符，**以实测为准**并在完成区记明。
  3. **`contract-asm.md` 投影刷新**（不含上游册）：§1（去掉「9 种 … `Toolchain-01 §1` 定义」+「`SPEC-115t` re-scope 后 …」的缓冲注记，改为与 `§1` 同步的 **11 类** 口径）、§2.1（大小写撤销）、§5（L168）/末尾表（L234）如引 `§1` 计数；`.tao/knowledge/contract-isa.md §2.3`（L187 注）相关叙述同步为 11 类（**语言层无需改则不改**）；`contract-asm-list.md` 为生成投影，**仅在受影响时随生成器重跑**（不得手改）。
  4. **只读锁同步**：改后**重算并写入** `manifests/spec-readonly.lock.toml` 中 `spec/Toolchain-01-汇编语言.md` 的 `sha256`（**仅该册一段**；其余 19 册不得变）。
  5. **门控对齐**：`check-asm-prose`/`check-asm-list*`/`check-spec-refs`/`check-spec-readonly` 全绿；`make check` EXIT=0。
  6. **`ISS-157` 结案**：`.tao/knowledge/issues.yaml` `ISS-157` → `status: closed`、`resolved_by: SPEC-116t`、`notes` 记「**以「条款撤销」结案**（撤销「大小写不敏感」条款，非实现缺口）」。
- **约束（硬）**：
  - **授权范围内改动**：`spec/Toolchain-01-汇编语言.md` **仅** §2.1（大小写撤销）+ §1（格式类口径同步）**两处**；**该册其它节（`§2.2`~`§14`）不得改**；`spec/` 其它册（含 `README.md`）一律不改。
  - **只改大小写条款、`§1` 格式类口径及其投影/结案**；不动其它语法条款语义。
  - **`crii` 不臆断**：`§1` 中 `crii` 的 `scope` 口径**以 `contracts/opcodes.yaml` 实测为准**（当前 = `excluded`）；不得照抄旧文「9 种」也不得臆测为 `m1`。
  - **撤销**措辞明确（撤销 ≠ 新增）；**不引入**大小写不敏感的实现工作（`LLVM` 侧不因此改；`ISS-157` 以条款撤销结案，**不是**留作实现缺口）。
  - **只读锁须同变更更新**（仅 `Toolchain-01` 一段 `sha256`；其余 19 册零变动）。
  - `spec/`/`.tao/knowledge/` 为共享文件，与 `SPEC-113t`~`115t`/`117t` **串行**。
  - `make check`（含 `check-asm-prose`/`check-asm-list-*`/`check-spec-refs`/`check-spec-readonly`）EXIT=0。
  - 失败即停、**禁自动重试**；临时目录 `/tmp/opencode/SPEC-116t/`；**不提交 git**；复杂命令输出留存 `.work/log/spec/`（**禁 `tee`**）。
  - **重建成本申报**：不触发组件重建。

## 验收标准

1. **`§2.1` 条款撤销**：`grep -n "大小写" spec/Toolchain-01-汇编语言.md .tao/knowledge/contract-asm.md` 显示二处均为**大小写敏感**口径，「不敏感」句已撤（给真实输出）。
2. **`§1` 格式类口径同步（用户授权 ②）**：`spec/Toolchain-01-汇编语言.md §1` 的 M1 格式类与 `contracts/opcodes.yaml` **事实一致**——**11 类**（9 种 + `crrr` + `ciii`），`crrr`/`ciii` **不再**写 `scope: excluded`；**`crii` 据实写为仍 `scope: excluded`**（`cfxld`/`cfxst`）。给**真实 `grep`（`Toolchain-01 §1` 句）+ 取值对照**（`python3` 逐 `format` 统计 `opcodes.yaml` 的 `scope`；两份口径逐条对齐），并核「`9 种`」字样已消失、「`crrr`/`crii`/`ciii` 属 … `scope: excluded`」旧句已改。
3. **投影一致**：`contract-asm.md`（§1/§2.1/§5/末尾表）与 `contract-isa.md §2.3` 叙述与 `§1` 口径一致（去除「9 种」与「`SPEC-115t` re-scope 后 …」缓冲落差）；`contract-asm-list.md` 若受影响则随生成器重跑（**byte-identical / 幂等**，给真实 `md5sum`）。
4. **只读锁同步（机械核验）**：改后 `sha256sum spec/Toolchain-01-汇编语言.md` == `manifests/spec-readonly.lock.toml` 中该册 `sha256`（逐位相等）；**`make check-spec-readonly` EXIT=0**（给真实输出+退出码，**禁 `tee`**）；`git diff manifests/spec-readonly.lock.toml` **仅 `Toolchain-01` 一段 `sha256` 变更**（其余 19 册零变动）——给真实 `git diff`。
5. **投影/门控**：`make check` **EXIT=0**（`check-asm-prose`/`check-asm-list-*`/`check-spec-refs`/`check-spec-readonly` 均绿）；给真实输出。
6. **结案**：`issues.yaml` `ISS-157` `status: closed`、`resolved_by: SPEC-116t`、`notes` 含「条款撤销」（给真实片段）。
7. **一键证据脚本**：`.work/evidence/SPEC-116t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（① 把 `§2.1` 条款改回「不敏感」；② 把 `§1` 格式类改回「9 种」或把 `crrr`/`ciii` 写回 `excluded`；③ 把锁 `sha256` 改错 ⇒ 对应断言 **FAIL** ⇒ **`cp`+md5 还原** ⇒ 回绿），结尾**禁 `tee`**；给真实输出。
8. **无残留**：`git status --untracked-files=all` 仅 `spec/Toolchain-01-汇编语言.md` + `manifests/spec-readonly.lock.toml` + `.tao/knowledge/contract-asm.md`（+ 必要的 `contract-asm-list.md`/`contract-isa.md`）+ `.tao/knowledge/issues.yaml` + 本任务书。

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
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例** + 核「撤销」措辞与结案 + 判决）

#### 规划修订（architect，2026-10-08，用户授权并入；**只增不改**）

**用户授权原话（逐字落盘）**：
> 「**1、并入SPEC-116t**」——对应：把「**同步 `spec/Toolchain-01 §1` 的 M1 格式类口径**」**并入本任务**。

（本任务改上游只读册的另一项授权原话「**允许（撤销不敏感条款）**」〔`§2.1`〕已见文件头「⚠️ 前置」；两项授权在本轮**并列落盘**。）

**背景（决定性事实）**：`SPEC-115t` re-scope 后 `m1` 实含 **11 类格式**（`check-interface` 报 `11/11 族有 lit 覆盖`），实测 `contracts/opcodes.yaml`：`crrr` = `m1`×2、`ciii` = `m1`×2、`crii` = `excluded`×2；但 `spec/Toolchain-01-汇编语言.md §1`（L15）仍写「**9 种** M1 格式类 / `crrr`/`crii`/`ciii` 属 `scope: excluded`」⇒ 与事实不符。该册属上游只读册（哈希锁内），须用户授权方能改——用户现已授权**并入 `SPEC-116t`**。

**本任务边界修订（要点）**：
1. **范围增补**：输出 += `spec/Toolchain-01 §1` 格式类口径同步（**9 → 11 类**；`crrr`/`ciii` 不再 `excluded`；**`crii` 据实**——现仍 `scope: excluded`）+ **只读锁同步**（`manifests/spec-readonly.lock.toml`，**仅 `Toolchain-01` 一段 `sha256`**）+ 投影刷新（`contract-asm.md`/`contract-isa.md §2.3`）。
2. **`crii` 事实口径**：`§1` 中 `crii` **以 `contracts/opcodes.yaml` 实测为准**（当前 = `excluded`；`cfxld`/`cfxst` 属 `SimRISC-12` deferred）；**不臆断**。
3. **前置**：两项授权原话**并列**（①「允许（撤销不敏感条款）」§2.1；②「1、并入SPEC-116t」§1）；授权范围 = `§2.1` + `§1` **两处**；**该册其它节不得改**；`spec/` 其它册不改。
4. **验收增补**：`§1` 与 `contracts/opcodes.yaml` 的 M1 格式类**一致**（真实 `grep`/取值对照）、`§2.1` 已改、`make check-spec-readonly` EXIT=0、**锁 diff 仅 `Toolchain-01` 一段**、`make check` EXIT=0；原验收（撤销措辞/投影/`ISS-157` 结案/证据脚本/无残留）保留并顺延为 1–8。
5. **消解 `SPEC-115t` 遗留**：`SPEC-115t` 完成区「新发现 1」/「遗留 3」与 `milestones.md` M5 段登记的 `Toolchain-01 §1` 偏差事项 ⇒ **并入本任务**（已在 `milestones.md`/`INTEG-019k` 标注）。

**判决**：本任务范围已扩展并落纸；`**状态**` 保持 `待开始`，待下发执行。

#### 第 1 轮 architect 提交（正常）

**档位**：**正常提交**（规划修订：用户授权「1、并入SPEC-116t」⇒ 本任务范围并入 `Toolchain-01 §1` 口径同步；非 `WIP:`）。

**文件集对账**（**显式 staging**，禁 `git add -A`；`git diff --cached --name-only` vs 本次改动声明 + 范围）：
- 声明 = **3 个规划文件**：`.tao/tasks/spec/SPEC-116t-大小写敏感修订.md`、`.tao/tasks/integ/INTEG-019k-m5启动与分解.md`、`.tao/knowledge/milestones.md`。
- `git diff --cached --name-only` 实测 = **3 个**，逐项一致；**漏提：无 / 多提：无 / 越界：无**。
- **`spec/` 授权范围核对**（`git diff --cached --name-only -- spec/`）：**空**（本次**不改任何 `spec/` 文件**；`spec/Toolchain-01` 的实际改动在 `SPEC-116t` 执行阶段落地）。

**提交**：**正常提交**（信息 `SPEC-116t 并入 Toolchain-01 §1 口径同步（用户授权）`）；**只 `commit`、绝不 `push`**（push 由主会话在 `/complete` 收尾后统一处置）。
