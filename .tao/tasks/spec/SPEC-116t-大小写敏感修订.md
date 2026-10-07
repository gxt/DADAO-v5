# SPEC-116t: `Toolchain-01` 修订（`§2.1` 大小写敏感 + `§1` M1 格式类口径同步）+ 投影/锁

**模块**：spec
**项目里程碑**：M5
**依赖**：`SPEC-115t`（**已验证**——`§1` 格式类口径须与 re-scope 后的 `scope` 事实一致）、`SPEC-119t`（哈希锁门控；与 `SPEC-113t`~`115t`/`117t` 同改 `spec/` ⇒ **串行**）
**状态**：已验证

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

**测试结果**：通过 8/8（验收 1–8 全部可跑且绿；`make check` **EXIT=0**）。失败原因：无。

**修改文件**（与 `git -c core.quotePath=false status --porcelain -uall` 逐一致；`spec/` 改动**仅** `Toolchain-01`，且仅 §1/§2.1 两处）：

| 文件 | 改动 |
|---|---|
| `spec/Toolchain-01-汇编语言.md` | §1「9 种 → 11 类」格式类口径同步 + §2.1 撤销「大小写不敏感」→ 大小写敏感（含显式「撤销」痕迹）；**仅此两处**，§2.2~§14 未动 |
| `manifests/spec-readonly.lock.toml` | `spec/Toolchain-01` 一段 `sha256` 更新（`d00c0925…` → `3f53c89c…`）；其余 19 册零变动 |
| `.tao/knowledge/contract-asm.md` | 投影：§1（L18–19，11 类口径，去「SPEC-115t re-scope 后 …」缓冲）、§2.1（撤销「不敏感」）、§11 表（L234，9 个 → 11 类） |
| `.tao/knowledge/issues.yaml` | `ISS-157` 结案（`status: closed`、`resolved_by: SPEC-116t`、`notes` 记「条款撤销」；title 追加结案标记） |
| `.tao/tasks/spec/SPEC-116t-大小写敏感修订.md` | 本任务书（完成区/自审/状态） |
| `.work/evidence/SPEC-116t/run.sh`（**gitignore**） | 一键证据脚本（新增） |
| `.work/log/spec/SPEC-116t-*.log`（**gitignore**） | 复杂命令输出留存 |

（**未改**：`contract-isa.md §2.3`〔注无格式类计数、无缓冲落差 ⇒ 语言层无需改则不改〕、`contract-asm-list.md`〔生成投影，未受影响，`check-asm-list-drift` byte-identical 已证〕、`contracts/opcodes.yaml`、`spec/` 其它册、`components/**`。）

**验收结果**（真实输出；完整日志 `.work/log/spec/SPEC-116t-*.log`；证据脚本全量输出 `.work/log/spec/SPEC-116t-evidence.log`）：

**验收 1（`§2.1` 条款撤销）** — `grep -n "大小写" spec/Toolchain-01-汇编语言.md .tao/knowledge/contract-asm.md`：
```
spec/Toolchain-01-汇编语言.md:22:### 2.1 空白与大小写
spec/Toolchain-01-汇编语言.md:24:- 助记符、寄存器名、伪指令、指导符等记号**区分大小写**（**大小写敏感**，`add.si` ≠ `ADD.SI`）；规范书写范式为**小写**。规范文档在**叙述**中出现的 `ADD.UO` 等大写**仅为示例**，**不构成**与对应小写形式等价的书写形式。
spec/Toolchain-01-汇编语言.md:25:- **（2026-10-08 修订）** 上一条的**大小写敏感**为本条现行口径；原「`ADD.SI` ≡ `add.si`」的**等价**规定经用户授权**撤销**（依据：`INTEG-019k D16` 裁定；关联 `ISS-157`——以「条款撤销」结案，非实现缺口）。
.tao/knowledge/contract-asm.md:26:### §2.1 空白与大小写
.tao/knowledge/contract-asm.md:29:- 助记符、寄存器名、伪指令、指导符等记号**区分大小写**（**大小写敏感**，`add.si` ≠ `ADD.SI`）；规范书写范式为**小写**。规范文档在**叙述**中出现的 `ADD.UO` 等大写**仅为示例**，**不构成**与对应小写形式等价的书写形式；原「`ADD.SI` ≡ `add.si`」的**等价**规定经用户授权**撤销**（2026-10-08，`INTEG-019k D16`）。[Toolchain-01 §2.1]
```
两文件 `grep -n 不敏感` = **0 命中**（「不敏感」句已撤；全仓 `不敏感` 仅存于 `.tao/knowledge/issues.yaml` 的结案 `notes` 与 `milestones.md` 的 `SPEC-115t` 历史台账——**均非本验收 1 的文件范围**，见「新发现」1）。

**验收 2（`§1` 格式类口径同步）** — `spec/Toolchain-01 §1` 句（`sed -n '15p'`）：
```
- **格式类（format）**：`contract-isa.md §2.3` 定义的 **11 类** M1 格式——`rrrr` `rrri` `rrii` `riii` `iiii` `rwii` `orrr` `orri` `oiii` `crrr` `ciii`。其中 `crrr`（`cfx2rd`/`cfx2rc`）与 `ciii`（`trap`/`escape`）属特权 cfx、已纳入 M1（`scope: m1`）；`crii`（`cfxld`/`cfxst`）仍属 `scope: excluded`（`SimRISC-12` deferred）。
```
取值对照（`python3` 逐 `format` 统计 `contracts/opcodes.yaml` 的 `scope`）：
```
ciii   m1=2
crii   excluded=2
crrr   m1=2
iiii   m1=2
oiii   excluded=1 m1=1
orri   fp=26 m1=20
orrr   excluded=8 fp=20 m1=63 m3=1
riii   m1=11
rrii   fp=4 m1=21
rrri   fp=4 m1=15
rrrr   fp=5 m1=11
rwii   fp=1 m1=7
m1 formats: ['ciii', 'crrr', 'iiii', 'oiii', 'orri', 'orrr', 'riii', 'rrii', 'rrri', 'rrrr', 'rwii']
excluded formats: ['crii', 'oiii', 'orrr']
```
逐条对齐：`§1` 的 11 个 `format` 记号集 **==** yaml 的 `scope==m1` 集（脚本断言 `SET_MATCH=yes`，COUNT=11）；`crrr`/`ciii` 各 `m1=2`（不再 `excluded`）；`crii = excluded×2`（`cfxld`/`cfxst`，据实写入）。另核：`9 种` 字样在 `spec/` **0 命中**；旧句「`属特权 cfx，`scope: excluded``」**已不存在**（`(old sentence absent)`）。
> **实测更正一处口径**：任务书「事实源」段写 `crii` 为唯一 `excluded` 格式；实测 `scope==excluded` 的格式共 **3** 个（`crii`×2 / `oiii`×1=`fence` / `orrr`×8=`lr_*`+`sc_*`）。`§1` 的 cfx 子句仅涉 `crrr`/`crii`/`ciii`，**口径以实测为准**（未把 `oiii`/`orrr` 的非-cfx excluded 混入 cfx 子句，避免臆断）。

**验收 3（投影一致）** — `contract-asm.md` §1（`11 类 …` + `crrr`/`ciii`，去缓冲注记）、§2.1（撤销）、§11 表（`11 类`）；`contract-isa.md §2.3` 注无格式类计数/无 `9 种`（语言层无需改，未动）。门控：`check-asm-list`/`check-asm-list-drift`/`check-spec-codeblocks` 均 **EXIT=0**；`contract-asm-list.md` 未受影响，`check-asm-list-drift: PASS (byte-identical)`（无需重跑生成器）。

**验收 4（只读锁同步）** — `sha256sum spec/Toolchain-01-汇编语言.md` = `3f53c89c007e52d43c9c7a15bc35eeec89071f9e0a840db31b6eff11714672ae` **==** lock 值；`python3 tools/infra/check_spec_readonly.py` **EXIT=0**（`20 upstream read-only spec volume(s) OK`）；`git diff -- manifests/spec-readonly.lock.toml` **仅** `Toolchain-01` 一段 `sha256` 变更：
```
-sha256 = "d00c0925a0e2cf8d1a3bbbf2cbd46d380a8ce97a0ae77176d7449b0c012e1085"
+sha256 = "3f53c89c007e52d43c9c7a15bc35eeec89071f9e0a840db31b6eff11714672ae"
```
（`git diff -- <lock> | grep -c '^[+-]sha256'` = **2**；脚本另断言 lock 未出现 `SimRISC`/`DADAO-*` 变更行。）

**验收 5（投影/门控）** — `make check` **EXIT=0**（`JOBS=8`）：
```
manifest validation: PASS
validate_vectors: 155/155 M1 identities covered OK (inventory sync OK; 15 data files, 693 cases; data coverage gaps: 0)
spec drift check: PASS
check-asm-list-consistency: 12 spec files OK
check-asm-list-drift: PASS (byte-identical)
check-asm-prose: PASS (0 violations)
check-spec-codeblocks: PASS (623 instruction line(s) checked against contracts/opcodes.yaml)
check_legality-drift: 12 chapters OK
check_interface: 总计 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
check_issues: 34 open, 1 closed (0 blocking M1-gate: 0)
Total Discovered Tests: 62
  Passed: 62 (100.00%)
repository checks: PASS
```
（`check-spec-refs` **EXIT=0**：`结果: PASS (0 violations)`；`check-scope` **EXIT=0**。）

**验收 6（结案）** — `.tao/knowledge/issues.yaml` 片段：
```
- id: ISS-157
  title: "汇编助记符大小写不敏感（spec 要求）当前未实现且未测——→ SPEC-116t 以「条款撤销」结案"
  status: closed
  scope: [llvm, spec]
  blocks: []
  resolved_by: SPEC-116t
  notes: "SPEC-116t 以「条款撤销」结案（非实现缺口）：经用户授权撤销 `Toolchain-01 §2.1` / `contract-asm §2.1` 的「大小写不敏感」条款，改为大小写敏感（用户裁定 INTEG-019k D16）。LLVM MC 侧大小写敏感行为与修订后规范一致，无需改动实现；TESTCASES-029t 的 norm 向量只测空白规范化，不受影响。"
```

**验收 7（一键证据脚本）** — `.work/evidence/SPEC-116t/run.sh` → **`EVIDENCE EXIT=0` / `ALL CHECKS PASS` / `summary: failures=0`**（含 I1/I2/I3 注入自检，全文见 `.work/log/spec/SPEC-116t-evidence.log`）：
```
I1 §2.1 改回「不敏感」        => 检查1 断言 FAIL [expected] (md5 改动确认) → cp+md5 还原 → 回绿
I2 §1 改回「9 种」            => 检查2 断言 FAIL [expected] (md5 改动确认) → cp+md5 还原 → 回绿
I3 lock sha256 改错           => check_spec_readonly FAIL (EXIT=1) [expected] → cp+md5 还原 → 回绿
```

**验收 8（无残留）** — `git -c core.quotePath=false status --porcelain -uall`：
```
 M .tao/knowledge/contract-asm.md
 M .tao/knowledge/issues.yaml
 M manifests/spec-readonly.lock.toml
 M spec/Toolchain-01-汇编语言.md
```
（+ 本任务书；`.work/**` 为 gitignore。无 `*_tmp*`/`*.orig`/`*.rej` 残留。）

**新发现/坑**：
1. **「不敏感 / 9 种」字样仍存在于授权范围外的台账**：`.tao/knowledge/milestones.md` 的 `SPEC-115t` 历史行仍写「`Toolchain-01 §1` 仍写「9 种 M1 格式 …」旧口径」（该行本身即记录此偏差的历史），`.tao/knowledge/issues.yaml` 的 `ISS-157` 结案 `notes` 含「大小写不敏感」字样（描述被撤销的条款）。二者**均非 `§1`/`§2.1` 文件**、**非本任务授权范围**，未改；验收 1/2 的 `grep` 仅覆盖 `spec/Toolchain-01` 与 `contract-asm.md`，与该范围一致。
2. **撤销痕迹落在 `§2.1` 内（未改文件头 rev 行）**：`Toolchain-01` 无「变更记录」节，文件头 L3 的「…（修订：双目的/多寄存器语法，2026-09-28）」属 §1/§2.1 **之外**的第三个位置。为严格遵守「授权范围 = §1 + §2.1 **两处**」，撤销痕迹（`**（2026-10-08 修订）** … 撤销`）写在 `§2.1` 条款内，**未**改文件头。如需文件级 rev 行，请另行授权。
3. **`crii` 口径以实测为准**：`scope==excluded` 的格式实为 3 个（`crii`/`oiii`/`orrr`），非任务书事实源段所写的「`crii` 唯一」。`§1` 的 cfx 子句只写 `crrr`/`crii`/`ciii`（未扩展），`crii` 据实 = `excluded`——已在验收 2 记明。
4. **ADR 提示（待用户裁定，未擅自创建）**：本任务为规范条款修订（撤销大小写不敏感 + §1 口径同步），对外部契约（LLVM/QEMU 对助记符大小写的期望）有影响，且存在「改实现 vs 改规范」的多方案否决记录（`INTEG-019k D16`）。**是否需立 ADR 记录该条款撤销决策，请用户裁定**（本任务书未要求创建，工程师不擅自建）。

**遗留问题**：
1. **跨模块影响（非本任务范围）**：`Toolchain-01 §2.1` 改为大小写敏感后，LLVM MC 现行大小写敏感行为与规范一致 ⇒ **无实现改动**；`TESTCASES-029t` norm 向量只测空白不受影响。但 `ISS-157` 结案后，若后续有模块依赖「大小写不敏感」语义，需复核（当前无）。
2. **`Toolchain-01` 其它节仍含旧口径（授权范围外，未改）**：`§5`（L151「`scope: excluded` 的格式（`crrr`/`crii`/`ciii`）」）、`§11`（L260「9 个 M1 格式类与 152 条 M1 指令」）、`§13`（L285「cfx 属 `scope: excluded`」）与现行 `scope` 事实仍有偏差。**授权范围严格限 §1 + §2.1**，故**未动**；建议后续经用户授权另立任务（含锁同步）一并收口。
3. 上述第 2 项若成立，`contract-asm.md` §5（L168，无计数、语义已正确）与 §13 的口径可一并复核（本任务未改 §5/§13，因其不引 `§1` 计数）。

## 审阅记录

#### 第 1 轮 engineer 自审

**结论：实现完成，无未决 finding ⇒ 置 `待验收`。** 逐行核对如下。

**自审范围（逐行核对改动）**：

| # | 审查点 | 结论 |
|---|---|---|
| R1 | `Toolchain-01` **仅** §1（L15）+ §2.1（L24 附近）改动；`git diff -- spec/` 仅该册、3 insertions/2 deletions；§2.2~§14 零改动 | ✅ `git diff` 逐 hunk 核对 |
| R2 | §2.1 撤销**显式**（含「（2026-10-08 修订）… 撤销」），措辞为「大小写敏感/区分大小写/规范范式小写/叙述中大写仅示例不构成等价」——与用户裁定 `INTEG-019k D16` 一致 | ✅ 见验收 1 |
| R3 | §1 = **11 类**（9 + `crrr` + `ciii`）；`crrr`/`ciii` 不再写 `excluded`；`crii` 据实测仍 `excluded` | ✅ 脚本 `SET_MATCH=yes`，逐条对照见验收 2 |
| R4 | 授权范围遵守：**未**改 `spec/` 其它册、未改 `Toolchain-01` 其它节、未改文件头 rev 行 | ✅ `git diff -- spec/` 仅 1 文件；`重放 §1/§2.1` grep 确认 |
| R5 | 锁同步：**仅** `Toolchain-01` 一段 `sha256`；逐位相等；`check-spec-readonly` EXIT=0 | ✅ 见验收 4 |
| R6 | 投影：`contract-asm.md` 与 `§1` 口径一致（11 类）、无「9 种」/无缓冲注记；`contract-isa §2.3` 无需改；`contract-asm-list.md` 未受影响（drift byte-identical） | ✅ 见验收 3 |
| R7 | `ISS-157` 结案字段完整（closed/SPEC-116t/notes 含「条款撤销」）；`check_issues` EXIT=0 | ✅ 见验收 6 |
| R8 | 还原纪律：证据脚本 3 处注入均 `cp`+`md5` 对账还原，**未用** `git checkout/restore/stash`；还原后 md5 一致 | ✅ I1/I2/I3 均 `已还原 (md5 match)` |
| R9 | 防造假：`make check`/各门控 rc 均**真实捕获**（`cmd > log; rc=$?`），证据脚本结尾 `rc=$?`，**无 `tee`** | ✅ 日志留 `.work/log/spec/` |
| R10 | 越界检查：`git status -uall` 仅 4 个已改文件（+ 本任务书）；无残留 | ✅ 见验收 8 |

**finding 处置表**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| （自审发现）证据脚本 §1 格式集比较曾用**有序串**比对致假 FAIL | ✅已修 | `s1_fmts` 改为 `sorted(set(...))` 排序后比对 | 重跑 `EVIDENCE EXIT=0`（`summary: failures=0`）；此前 `failures=1` |
| 无其它 finding | — | — | — |

**判决**：finding 全部已修 ⇒ 状态回 `**状态**：待验收`，返回主会话。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（mimo-v2.5-pro）
**审查时间**：2026-10-08
**审查范围**：证据脚本审核 + 重跑 + 独立注入反例 + 验收 1–8 逐条独立复核 + 授权范围/越界核验

##### 1. 证据脚本 `.work/evidence/SPEC-116t/run.sh` 审核

**结构**：检查 1-7 + 注入自检 I1/I2/I3，`set -u`，结尾 `exit $FAILURES`（非 `tee`）。✓

**逐条可达 FAIL 路径核对**：

| 断言 | FAIL 路径 | 恒真？ |
|---|---|---|
| 检查1 `不敏感` | `grep -q '不敏感' "$f"` ⇒ found ⇒ fail | 否 ✓ |
| 检查1 `大小写敏感` | `grep -q '大小写敏感' "$f"` ⇒ not found ⇒ fail | 否 ✓ |
| 检查1 `撤销` | both files must contain `撤销` | 否 ✓ |
| 检查2 `SET_MATCH` | `set(fmts) == set(m1)` ⇒ no ⇒ fail（Python 断言） | 否 ✓ |
| 检查2 `11 类` | `grep -q '11 类'` ⇒ not found ⇒ fail | 否 ✓ |
| 检查2 `9 种` | `grep -q '9 种'` in SPEC/CASM ⇒ found ⇒ fail | 否 ✓ |
| 检查2 `旧句` | `grep -q '属特权 cfx，`scope: excluded`'` ⇒ found ⇒ fail | 否 ✓ |
| 检查2 `crii excluded` | `grep -q 'crii.*仍属'` ⇒ not found ⇒ fail | 否 ✓ |
| 检查3 投影 | 各 `grep` 条件，found/not found 两种走向 | 否 ✓ |
| 检查4 sha256 | `$file_sha = $lock_sha` ⇒ 不等 ⇒ fail | 否 ✓ |
| 检查4 check_ro | `rc_ro -eq 0` ⇒ 非零 ⇒ fail | 否 ✓ |
| 检查4 lock diff | `n_sha -eq 2` ⇒ 不等 ⇒ fail | 否 ✓ |
| 检查5 门控 | `rc -eq 0` ⇒ 非零 ⇒ fail | 否 ✓ |
| 检查6 ISS-157 | status/resolved_by/notes 三条件 | 否 ✓ |
| 检查7 无残留 | `bad` 非空 ⇒ fail | 否 ✓ |
| I1 注入 | md5 differs + `grep '不敏感'` found ⇒ 两个 PASS 路径 | 否 ✓ |
| I2 注入 | md5 differs + `grep '9 种'` found + `grep '11 类'` not found | 否 ✓ |
| I3 注入 | md5 differs + `check_ro EXIT≠0` | 否 ✓ |

**结论**：无恒真断言，每条断言均有可达 FAIL 路径。脚本**合格**。

##### 2. 重跑证据脚本（真实输出）

```
=== SPEC-116t evidence (repo=/mnt/tao/DADAO-v5) ===
--- 1 §2.1 大小写敏感 ---
[PASS] 1 spec/Toolchain-01-汇编语言.md 无「不敏感」
[PASS] 1 spec/Toolchain-01-汇编语言.md 含「大小写敏感」
[PASS] 1 .tao/knowledge/contract-asm.md 无「不敏感」
[PASS] 1 .tao/knowledge/contract-asm.md 含「大小写敏感」
[PASS] 1 两文件均含显式「撤销」痕迹
--- 2 §1 格式类口径 == opcodes.yaml scope 事实 ---
S1_FORMATS=rrrr,rrri,rrii,riii,iiii,rwii,orrr,orri,oiii,crrr,ciii
OPCODES_M1=ciii,crrr,iiii,oiii,orri,orrr,riii,rrii,rrri,rrrr,rwii
COUNT=11
HAS_11=yes / HAS_9ZHONG=no / HAS_OLD_PAREN=no
CRII_EXCLUDED=yes / CRRR_M1=yes / CIII_M1=yes / SET_MATCH=yes
[PASS] 2 §1 格式集 == opcodes m1 集 (ciii,crrr,iiii,oiii,orri,orrr,riii,rrii,rrri,rrrr,rwii)
[PASS] 2 §1 标「11 类」 / [PASS] 2 无「9 种」 / [PASS] 2 旧 §1 句已改 / [PASS] 2 crii 据实写为 excluded
--- 3 投影一致 --- (6/6 PASS)
--- 4 只读锁同步 --- (4/4 PASS; sha256=3f53c89c…==lock; check_ro EXIT=0)
--- 5 门控 --- (6/6 PASS)
--- 6 ISS-157 结案 --- (3/3 PASS; status=closed, resolved_by=SPEC-116t, notes含「条款撤销」)
--- 7 无残留 --- (1/1 PASS)
--- 注入自检 --- (I1/I2/I3 各 4 步 = 12/12 PASS)
=== summary: failures=0 ===
ALL CHECKS PASS
EXIT=0
```

**EXIT=0，40/40 PASS。**

##### 3. 独立注入反例（reviewer 自行执行）

**注入方式**：`cp` 备份 → 改 `spec/Toolchain-01-汇编语言.md` §2.1 回「大小写不敏感」→ 重跑**同一脚本** → 确认 FAIL → `cp` 还原 → 重跑确认回绿。**未用** `git checkout/restore/stash`。

**注入前 md5**：`7c82357b5777eb6fdc1ec245deb61e4f`

**注入**：python3 regex 替换 §2.1 行 → `不敏感`；git diff 确认非空。

**注入后脚本输出（关键行）**：
```
[FAIL] 1 spec/Toolchain-01-汇编语言.md 仍含「不敏感」(期望=无)
[FAIL] 4 spec sha256 != lock
[FAIL] 4 check-spec-readonly EXIT=1
=== summary: failures=6 ===
EVIDENCE FAILED (6)
EXIT=1
```
**预期 FAIL 命中**：检查 1（`不敏感` 被检出）+ 检查 4（sha256 不匹配 + check_ro 失败）。脚本能失败。✓

**还原**：`cp /tmp/opencode/SPEC-116t-review/Toolchain-01.preinject.md spec/Toolchain-01-汇编语言.md`
**还原后 md5**：`7c82357b5777eb6fdc1ec245deb61e4f`（== 注入前）。✓

**还原后脚本输出**：`ALL CHECKS PASS` / `EXIT=0` / `failures=0`（40/40 PASS）。✓

##### 4. 验收 1–8 逐条独立复核

| # | 验收项 | 独立复核结果 | 结论 |
|---|---|---|---|
| 1 | §2.1 撤销「不敏感」 | `grep -n 不敏感 spec/Toolchain-01-汇编语言.md .tao/knowledge/contract-asm.md` = **0 命中**（EXIT=1）；两文件均含「大小写敏感」+「撤销」 | ✅ |
| 2 | §1 口径 = 11 类 | 独立 `python3` 统计 `contracts/opcodes.yaml`：m1 格式 = `['ciii','crrr','iiii','oiii','orri','orrr','riii','rrii','rrri','rrrr','rwii']`（11 个）；§1 句列出**完全相同 11 个**；`crrr`/`ciii` 在 m1 不在 excluded；`crii` 在 excluded；`9 种` = 0 命中 | ✅ |
| 3 | 投影一致 | `contract-asm.md` §1 = 11 类 + 列出 crrr/ciii + 无 re-scope 缓冲注记；§11 表 = 11 类；`contract-isa §2.3` 无 `9 种`（语言层无需改）| ✅ |
| 4 | 锁同步 | `sha256sum` = `3f53c89c…` == lock 值；`check_spec_readonly.py` EXIT=0；`git diff` 仅 Toolchain-01 一段 sha256（2 行）| ✅ |
| 5 | `make check` | EXIT=0（62/62 lit tests PASS，80/80 check_interface PASS，所有门控 PASS）| ✅ |
| 6 | ISS-157 结案 | `status: closed`、`resolved_by: SPEC-116t`、`notes` 含「条款撤销」| ✅ |
| 7 | 证据脚本 | 见上方 §1-3 | ✅ |
| 8 | 无残留 | `git status --porcelain -uall` = 5 文件（4 已改 + 本任务书），无 `*_tmp*`/`*.orig`/`*.rej` | ✅ |

##### 5. 授权范围核验

**`spec/` 改动范围**：`git diff 15c208b..HEAD -- spec/` = **仅 1 册** `spec/Toolchain-01-汇编语言.md`，**仅 2 处 hunk**：
- `@@ -12,7 +12,7 @@`（§1 格式类口径：9 种 → 11 类）
- `@@ -21,7 +21,8 @@`（§2.1 大小写不敏感 → 大小写敏感 + 撤销痕迹）

**无其它 `spec/` 册改动。** ✓

**全部文件 diff**：`git diff --name-only 15c208b..HEAD` = 5 文件：
1. `.tao/knowledge/contract-asm.md`
2. `.tao/knowledge/issues.yaml`
3. `.tao/tasks/spec/SPEC-116t-大小写敏感修订.md`
4. `manifests/spec-readonly.lock.toml`
5. `spec/Toolchain-01-汇编语言.md`

与完成区声明一致。✓

##### 6. 遗留确认

**`Toolchain-01` §5/§11/§13 仍含与 `scope` 不符的旧口径**（reviewer 独立读取确认）：
- **§5**（L153）：仍写「`scope: excluded` 的格式（`crrr`/`crii`/`ciii`）」—— `crrr`/`ciii` 已 re-scope 为 `m1`，仅 `crii` 仍 excluded
- **§11**（L260）：仍写「9 个 M1 格式类与 152 条 M1 指令」—— 应为 11 类 / 155 条
- **§13**（L285）：仍写「cfx 属 `scope: excluded`」—— `crrr`/`ciii` 已 re-scope 为 `m1`

**授权范围严格限 §1 + §2.1 两处，故未动。须另立任务（含锁同步）经用户授权后一并收口。**

##### 判决

**Accepted** —— 验收 1–8 全部通过（独立重跑 + 独立注入反例确认脚本能失败 + 还原回绿）；授权范围守（仅 §1 + §2.1 两处 hunk）；遗留 §5/§11/§13 已如实记录，需另立任务。

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

#### 第 1 轮 architect 提交（WIP）

**档位**：**`WIP:` 提交**（engineer 已完成实现、`**状态**：待验收`，reviewer 尚未验收 ⇒ WIP）。

**文件集对账**（**显式 staging**，禁 `git add -A`；`git diff --cached --name-only` vs engineer 声明 + 任务范围）：
- engineer 声明 = **5 项**：`spec/Toolchain-01-汇编语言.md`、`manifests/spec-readonly.lock.toml`、`.tao/knowledge/contract-asm.md`、`.tao/knowledge/issues.yaml`、本任务书。
- `git diff --cached --name-only` 实测 = **5 个**，逐项一致；**漏提：无 / 多提：无 / 越界：无**。

**`spec/` 授权范围核对**：
- `git diff --cached --name-only -- spec/` 实测 = **仅 1 册** `spec/Toolchain-01-汇编语言.md`（无其它 `spec/` 册）。
- 该册改动 **仅 2 处 hunk**：`@@ -12,7 +12,7 @@`（§1 格式类口径）、`@@ -21,7 +21,8 @@`（§2.1 空白与大小写）——**未触及该册其它节**。

**提交**：**`WIP:` 提交**（信息 `WIP: SPEC-116t Toolchain-01 §2.1 大小写敏感 + §1 格式类口径同步（+锁/投影/ISS-157）（待 reviewer 验收）`）；**只 `commit`、绝不 `push`**（push 由主会话在 `/complete` 收尾后统一处置）。

#### 第 1 轮 architect 提交（正常）

**档位**：**正常提交**（reviewer 判 `Accepted` ⇒ 验收完成；非 `WIP:`）。

**交叉复核结论**：architect 独立复核通过（重跑/实测，非采信叙述）——① 独立实测 `contracts/opcodes.yaml` 的 `m1` `format` 集（11 个：`ciii`/`crrr`/`iiii`/`oiii`/`orri`/`orrr`/`riii`/`rrii`/`rrri`/`rrrr`/`rwii`）与 `§1` 所列**逐项相等**（`SET_MATCH=True`）；② `grep -n 不敏感 spec/Toolchain-01*` = **0 命中**（EXIT=1）；③ 锁 `sha256` == 文件实测 `3f53c89c…`、`check_spec_readonly.py` **EXIT=0**、锁 diff **仅 `Toolchain-01` 一段**（`^[+-]sha256` 行 = 2）；④ `ISS-157` 结案字段完整（`status: closed`/`resolved_by: SPEC-116t`/`notes` 含「条款撤销」）；⑤ `git diff 15c208b..HEAD -- spec/` **仅 1 册 `Toolchain-01`**、**仅 2 处 hunk**（`@@ -12,7 +12,7 @@` §1、`@@ -21,7 +21,8 @@` §2.1）；⑥ reviewer 独立注入（`§2.1`→「不敏感」）**有鉴别力**（6 断言 FAIL ⇒ `cp`+md5 还原回绿；还原后 md5 `7c82357b…` == 现行文件 md5）。

**文件集对账**（**显式 staging**，禁 `git add -A`；`git diff --cached --name-only` vs 本次改动声明 + 范围）：
- 声明 = **5 项**：`.tao/tasks/spec/SPEC-116t-大小写敏感修订.md`（审阅记录 + `**状态**`）+ `.tao/knowledge/lessons.md`（§7.14/§8.8）+ `.tao/knowledge/changelog.md`（+1 行）+ `.tao/knowledge/milestones.md`（M5 ✅ 行）+ `.tao/knowledge/MEMORY.md`（M5 行）。
- `git diff --cached --name-only` 实测 = **5 个**，逐项一致；**漏提：无 / 多提：无 / 越界：无**。
- **`spec/` 授权范围核对**（`git diff --cached --name-only -- spec/`）：**空**（本收尾提交**不改任何 `spec/` 文件**；`spec/Toolchain-01` 的实际改动已在前序 `WIP` 提交内，且仅该册 2 处 hunk）。

**提交**：**正常提交**（信息 `SPEC-116t Toolchain-01 §2.1 大小写敏感 + §1 格式类口径同步（reviewer Accepted）`，**不加 `WIP:`**）；**只 `commit`、绝不 `push`**（push 由主会话在 `/complete` 收尾后统一处置）。

#### 主会话统一验收报告（`/complete`，2026-10-08）

- **reviewer**：`Accepted`。证据脚本重跑 **40/40 PASS, EXIT=0**（含 `make check` EXIT=0）；**独立注入**（`§2.1` 改回「不敏感」）⇒ 断言 FAIL（含 `check-spec-readonly` EXIT=1）⇒ `cp`+`md5` 还原 ⇒ 回绿。
- **architect 交叉复核**：**确认 `Accepted`**。独立核：`grep 不敏感` = 0；**自行统计** `opcodes.yaml` 的 `m1` `format` 集合 = `{ciii,crrr,iiii,oiii,orri,orrr,riii,rrii,rrri,rrrr,rwii}`（11）与 `§1` 枚举**逐项相等**；`sha256sum` == 锁值、`check-spec-readonly` EXIT=0、**仅该册一段 sha256 变**；`ISS-157` 已结案；`spec/` 改动**仅 `Toolchain-01` 且仅 §1+§2.1 两处 hunk**。
- **授权范围**：两项授权原话（「允许（撤销不敏感条款）」+「1、并入SPEC-116t」）已逐字落盘；`spec/` 净改动 = 该册 §1+§2.1 + 其锁一段。
- **遗留（须另请授权）**：`spec/Toolchain-01` 的 **`§5`(L152) / `§11`(L260) / `§13`(L285)** 仍含与 `scope` 不符的旧口径（「`crrr`/`crii`/`ciii` 属 excluded」「9 个 M1 格式类」「cfx 属 excluded」）⇒ **授权限 §1+§2.1，未动**，须另立任务（含锁同步）收口。
- **ADR 提醒（按 `AGENTS.md` 义务，待用户裁定）**：本任务为**规范条款撤销**、涉**外部契约**（LLVM/QEMU 对助记符大小写的期望）且**存在被否方案**（`INTEG-019k D16`：改实现 vs 改规范）⇒ **命中 ADR 判据**；architect 建议**立 ADR**（记录「以条款撤销结案、非实现缺口」及理由，指向 `Toolchain-01 §2.1`/`ISS-157`）——**未擅自创建**。
- **知识沉淀**（按项目新规统一落 `lessons.md`）：新增 **§7.14**（任务书「唯一/仅」类断言须下发前全量实测）+ **§8.8**（对应操作规范）；`changelog`/`milestones`/`MEMORY` 同步。
- **收尾检查**：`make check` EXIT=0；`git status --porcelain -uall` 干净；证据留 `.work/evidence/SPEC-116t/`、`.work/log/spec/`。
- **最终判决**：**`Accepted`** ⇒ 任务书 `**状态**` 置 `已验证`。

#### 收尾裁定落纸（architect，2026-10-08，**只追加**）

**背景**：`SPEC-116t` 收尾时主干提有下列两项待裁事项（见本审阅记录「主会话统一验收报告」末两条：「ADR 提醒…待用户裁定」+「遗留…须另请授权」）。用户已裁定，**原话逐字落盘**如下（**user 原话，逐字**）。

**裁定 1（ADR）** — 用户原话（逐字）：
> 「**不立 ADR**」

- **依据**：本任务确**命中 ADR 判据**（规范条款**撤销**、涉**外部契约**〔LLVM/QEMU 对助记符大小写的期望〕、且存在**被否方案**〔`INTEG-019k D16`：改实现 vs 改规范〕，判据见 `spec/Process-03`），architect 曾建议立 ADR；**用户裁定不立**。据此**不创建** ADR。
- **落纸**：仅在本任务书「审阅记录」记录（不改其它文件）。

**裁定 2（`Toolchain-01 §5`/`§11`/`§13` 旧口径）** — 用户原话（逐字）：
> 「**暂登记遗留**」

- **依据（实测）**：上游只读册 `spec/Toolchain-01-汇编语言.md` 仍有三处旧口径与 `contracts/opcodes.yaml` 的 `scope` 不符——`§5`（L152）「**`scope: excluded` 的格式（`crrr`/`crii`/`ciii`）**」、`§11`（L261）「**9 个 M1 格式类与 152 条 M1 指令**」、`§13`（L286）「**cfx 属 `scope: excluded`**」。本任务**授权范围严格限 `§1` + `§2.1`**，故**未动**。用户裁定**暂登记遗留**、**待后续授权**收口。
- **落纸**：登记 `.tao/knowledge/issues.yaml` **`ISS-163`**（`status: open`、`scope: [spec, M5]`、`resolved_by: null`〔open 时按字段约束留空 = 待定〕、`notes` 写明用户裁定「暂登记遗留」+ 收口须另行授权〔含该册 `sha256` 锁同步〕）；`.tao/knowledge/milestones.md` M5 段 `SPEC-116t` 条「遗留」同步为 **`ISS-163`** 引用（最小改动）。

**判决**：两项裁定已落纸；本任务书 `**状态**` 保持 `已验证`（不因裁定回退）。
