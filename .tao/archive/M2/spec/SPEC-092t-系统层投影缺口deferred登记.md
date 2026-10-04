# SPEC-092t: 系统层投影缺口显式 deferred 登记（清缺口②③④）

**模块**：spec
**项目里程碑**：M2
**依赖**：`SPEC-091t`（同改 `spec/README.md`/`Process-02`，串行）
**状态**：已验证

## 目标

对 `spec/README.md` 投影表 / `Process-02` 合约清单中登记的 **3 个系统层缺口**——`contract-sbi.md`（DADAO-12/22）、`contract-exception.md`（DADAO-13/23）、`contract-mmu.md`（DADAO-12 地址转换）——按 M2 门槛②「**缺口清零或显式 deferred**」做成**显式 deferred 登记**：写明 deferred 结论、理由、归属里程碑与触发条件，使投影表不再存在**裸 `缺口`**。

## 背景与现状（实测）

- `spec/README.md` 投影表中，`DADAO-12`（SEE）行为 `缺口（contract-sbi.md；地址转换 → contract-mmu.md）`、`DADAO-13`（HEE）行为 `缺口（contract-exception.md）`、`DADAO-22`（SBI）/ `DADAO-23`（HBI）行为 `缺口`/据实；「登记缺口」表列 `contract-sbi.md`/`contract-exception.md`/`contract-mmu.md` 三行。
- `spec/Process-02` 合约清单：`contract-sbi.md`/`contract-exception.md`/`contract-mmu.md` 状态 = **缺口**（其中 exception/mmu 已括注「可标记 deferred」）。
- 相关上游：`spec/DADAO-12`（SEE，§2 地址空间/§5 异常进入退出）、`spec/DADAO-22`（SBI 功能）、`spec/DADAO-13`/`DADAO-23`（HEE/HBI）。
- **M3 范围**（`milestones.md`）：Basic CodeGen = 标量整数/指针函数（LLVM IR）→ DADAO 汇编 → MC → obj → 链接 → QEMU 执行；**freestanding、same-TU**，不含变参/聚合；**无系统调用、无异常向量、无地址转换（MMU-off）**。故三者在 M3 之前**无消费方**。

## 交付物

1. **`spec/README.md`**：
   - 投影表中 `DADAO-12`/`DADAO-13`/`DADAO-22`/`DADAO-23` 行的 ①叙述合约列，由 `缺口（…）` 改为 **`deferred`（`contract-xxx.md`，归属 M3+ / 触发条件）**；
   - 「登记缺口」表三行更新：`缺口类型` 列由「…缺失」改为 **deferred**，并补 `deferred 理由` 与 `归属/触发`（归属里程碑 + 何时必须补齐）。
2. **`spec/Process-02-合约编写规范.md`**：合约清单中三者状态由 **缺口** 改为 **deferred**（并一句话理由 / 归属）。
3. **deferred 结论与理由**（写入上述两处，文字一致）：
   - **无 M2/M3 消费方**：M2（规范冻结）不实现 SEE/SBI/HEE/MMU；M3 codegen 为 freestanding 单 TU、无 syscall/异常/MMU。
   - **未冻结的后果可控**：M3 生成的代码不依赖 SBI 功能号、异常进入协议、地址转换；
   - **触发条件**：当出现「跨模块/内核/系统态」目标（如 OS→LFS 路线、`SEE/SBI` 消费方落地）时，须先补齐对应 contract 再实现；
   - **上游依据可回溯**：`spec/DADAO-12/13/22/23` 已存在，补齐时按 `Process-02` 归一化，不需新造规范正文。

## 约束

- **不臆造合约内容**：本任务**只登记 deferred**，不写 `contract-sbi/exception/mmu.md` 正文；若判定应直接补齐，须另立任务（不在本任务范围）。
- 只改文档：`spec/README.md`、`spec/Process-02-合约编写规范.md`。不改 `spec/DADAO-*` 正文、不改 `contracts/`、`tests/`、`components/`、`tools/`。
- 「显式 deferred」须**机械可搜**：投影表三格文字含 `deferred`（与 `SPEC-091t` 完成后的 `contract-asm.md`=已清零区分开）。
- ADR 提醒：登记 deferred 属过程取向（可逆、无外部契约），**不立 ADR**；若用户裁定改为「直接补齐合约」，则按新结论走，不沿用本任务。
- 与 `SPEC-091t` 串行（同改两文件）。

## 验收标准

1. `spec/README.md` 投影表中 `DADAO-12`/`DADAO-13`/`DADAO-22`/`DADAO-23` 行的 ① 叙述合约列**不再出现裸 `缺口`**，均为 `deferred`（含归属/触发）。
2. `spec/README.md`「登记缺口」表：`contract-sbi.md`/`contract-exception.md`/`contract-mmu.md` 三行均标 **deferred** + 理由 + 归属。
3. `spec/Process-02` 合约清单三者状态 = **deferred**。
4. 全 `spec/README.md` 与 `Process-02` 中，指向三缺口的字面 `缺口`（表示「未处置」者）= 0（`deferred` 字样除外）。
5. `make check` **EXIT=0**（纯文档改动，如不在门控覆盖内则以 `git status` 目视 + `check-no-residue` 为准）。
6. **反例门控**：一键证据脚本内置「注入反例→预期 FAIL→还原→预期回绿」（如把三行之一改回裸 `缺口` → 自检 FAIL），并在完成区给出真实输出与退出码。

## 完成区

**测试结果**：全部通过。
- `make check` **EXIT=0**（31/31 lit PASS，`repository checks: PASS`），日志 `.work/log/spec/SPEC-092t-make-check.log`。
- 一键证据脚本 `.work/evidence/SPEC-092t/run.sh`：C1–C5 全 PASS，反例 INJ-A/INJ-B「注入→FAIL→还原→回绿」，`SPEC-092t evidence: PASS`、`EVIDENCE_EXIT=0`，日志 `.work/log/spec/SPEC-092t-evidence.log`。

**修改文件**：
- `spec/README.md`：投影表 `DADAO-12`/`DADAO-13`/`DADAO-22`/`DADAO-23` 行 ①叙述合约列 由 `缺口（…）` 改为 **`deferred`（`contract-xxx.md`；归属 M3+，触发条件）**；「登记缺口」表三行：`缺口类型` 列 → **状态 = `deferred`**，新增 `deferred 理由` 与 `归属/触发` 两列；表题与脚注同步为「显式 deferred」。
- `spec/Process-02-合约编写规范.md`：合约清单 `contract-sbi.md`/`contract-exception.md`/`contract-mmu.md` 状态 `缺口` → **`deferred`**（附一句话理由/归属）；清单脚注同步。
- 非入库证据/日志（`.gitignore` 覆盖）：`.work/evidence/SPEC-092t/check.py`、`run.sh`；`.work/log/spec/SPEC-092t-{make-check,evidence}.log`。

**验收结果**（真实输出节选）：
```
# 一键证据（.work/log/spec/SPEC-092t-evidence.log）
[PASS] C1 `DADAO-12`（SEE） ① deferred  实际=`deferred`（`contract-sbi.md`、`contract-mmu.md`；归属 M3+，触发：SBI/地址转换消费方落地）
[PASS] C1 `DADAO-13`（HEE） ① deferred  实际=`deferred`（`contract-exception.md`；归属 M3+，触发：系统态异常消费方落地）
[PASS] C1 `DADAO-22`（SBI） ① deferred  实际=`deferred`（`contract-sbi.md`；归属 M3+，触发：SBI 消费方落地）
[PASS] C1 `DADAO-23`（HBI） ① deferred  实际=`deferred`（`contract-exception.md`；归属 M3+，触发：HBI 消费方落地）
[PASS] C2 contract-sbi/exception/mmu.md deferred+理由+归属  实际=状态=**deferred**; 理由含「无 M2/M3 消费方」; 归属=归属 M3+；触发…
[PASS] C3 contract-sbi/exception/mmu.md Process-02 deferred  实际=**deferred**（无 M2/M3 消费方…）
[PASS] C4 登记缺口表三行无「缺口」  实际=0 []
[PASS] C5 make check  实际=EXIT=0        # 31/31 lit PASS，repository checks: PASS
[PASS] INJ-A README DADAO-22 ①→缺口：期望 C1 FAIL，实际 FAIL={C1 `DADAO-22`（SBI） ① deferred}
[PASS] INJ-A 还原：期望全绿，实际 全绿
[PASS] INJ-B P02 contract-mmu 状态→缺口：期望 C3 FAIL，实际 FAIL={C3 contract-mmu.md Process-02 deferred}
[PASS] INJ-B 还原：期望全绿，实际 全绿
[INFO] 注入非空：INJ-A=True  INJ-B=True
SPEC-092t evidence: PASS
EVIDENCE_EXIT=0

# make check（.work/log/spec/SPEC-092t-make-check.log）
Total Discovered Tests: 31 / Passed: 31 (100.00%)
check_issues: 100 open, 19 closed (0 blocking M1-gate: 0)
repository checks: PASS
MAKE_CHECK_EXIT=0
```
逐条对账：验收 1（四行 ① 无裸缺口、均 deferred 含归属/触发）= C1；验收 2（登记缺口表三行 deferred+理由+归属）= C2/C4；验收 3（Process-02 三者 deferred）= C3；验收 4（指向三缺口的字面缺口=0）= C1/C4；验收 5（make check EXIT=0）= C5；验收 6（反例门控）= INJ-A/B。全部 PASS。

**新发现/坑**：
1. **`make check` 不解析 `spec/README.md`/`Process-02`**（两文件不在任何 checker 输入内）→ 本次为**纯文档改动**，门控豁免；仍按要求跑 `make check` EXIT=0 作为回归证据。
2. **并发写者（SPEC-094t 同树运行）**：执行期间检测到**其它会话**正在改动 `tools/infra/check_spec_refs.py`、`.tao/knowledge/contract-{isa,abi,elf}.md`、`contracts/abi.yaml`（内容属 `SPEC-094t` 的「历史违规消解」范围）。本任务声明的两文件（`spec/README.md`/`Process-02`）**未出现第三方写入**——`git diff` 对本任务两文件仅含本任务改动，故**无本任务侧的写入冲突**。影响提示：`contract-*.md` 是 `make check` 的 `check-spec-drift` 输入，若 reviewer 重跑 `make check` 时 `SPEC-094t` 恰好处于半改动态，可能出现**并发瞬态**（非本任务）；本任务证据的 `make check EXIT=0` 为本会话运行时点的真实输出（`.work/log/spec/SPEC-092t-make-check.log`）。按 AGENTS「同改共享文件串行 / 避免同树并发 make check」建议主会话串行化。
3. **范围外残留 `缺口`（已披露）**：`spec/README.md` `DADAO-12` 行 **②/④ 列**的 `缺口`（据实）与 `SimRISC-07` 行 **④ 列**的 `缺口`（oracle/向量待建）属**其它投影类型**，**不指向** contract-sbi/exception/mmu 三个叙述合约缺口，且不在 M2 门槛②的 4 项清单（`SPEC-090k`）内，故**未改**（越界）。验收 4「指向三缺口的字面 `缺口`=0」按「指向三缺口的具体单元格」口径判定（见证据脚本头部注释）。
4. **理由文字一致性**：两文件采用同一句核心理由「无 M2/M3 消费方：M3 codegen 为 freestanding 单 TU，无 syscall/异常/MMU，未冻结后果可控；上游 `spec/DADAO-12/13/22/23` 已存在，补齐不需新造正文。」+ 同一「归属 M3+」；触发条件按各合约具体化。

**遗留问题**：
- 无（任务范围内全部完成）。
- 说明（非本任务范围）：①`DADAO-12` ②/④ 与 `SimRISC-07` ④ 的 `缺口` 未纳入（见「新发现/坑」3），若 M2 门槛② 或后续要求「投影表全表无 `缺口`」，须另立任务；② 本任务**只登记 deferred，未落盘三合约正文**（按约束），补齐须另立任务；③ 建议 `SPEC-094t` 与本任务避免同树并发（见「新发现/坑」2）。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查两文件 diff、证据脚本 `check.py`/`run.sh`、以及脚本真实输出与完成区结论的逐条一致性。

**审查范围与判决**：逻辑正确性（deferred 归属映射：DADAO-12→sbi+mmu、DADAO-13/23→exception、DADAO-22→sbi）、机械可搜（四格含 `deferred`）、表格完整性（无空行、列数一致）、防造假（真实执行输出）、脚本可失败性。判决：**通过（所有 finding 已修）**。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 C4 初稿按「行内含 `缺口` 且含三 contract 名」判定 → 误报 `DADAO-12` 行 ②/④ 的 `缺口`（据实）（该行 ① 含 contract-sbi/mmu） | ✅已修 | C4 改为**单元格口径**（登记缺口表三行任一单元格）；`缺口` 的「指向三缺口」判定落到 C1（投影 ① 列）+ C4（登记表三行） | 证据 C1×4、C4 全 PASS；`TEXT_ONLY_ALL_OK=True` |
| F2 C1 初稿首列标签写成 `` `DADAO-12（SEE）` ``（反引号位置错）→ `row not found` 假 FAIL | ✅已修 | 标签改为实际首列 `` `DADAO-12`（SEE） `` 等 | 证据 C1×4 PASS |
| F3 INJ-B 初稿 regex 仅 1 个捕获组却用 `m.start(2)` → `IndexError` | ✅已修 | 改用 `m.group(1)`+`m.start(0)`/`m.end(0)` | INJ-B PASS（注入非空=True） |
| F4 残留 `缺口`（DADAO-12 ②/④、SimRISC-07 ④）是否应改 | ❌不修（附证据） | 未改（越界） | 二者非三叙述合约缺口、不在 M2 门槛② 4 项清单（`SPEC-090k` 行 25）；已在完成区「新发现/坑」3 与证据 INFO 披露 |

**反例门控自检**：INJ-A（README DADAO-22 ①→`缺口`）与 INJ-B（Process-02 contract-mmu 状态→`缺口`）均「注入→C1/C3 FAIL→还原→全绿」，注入 diff 非空（`INJ-A=True INJ-B=True`）；注入在内存字符串上进行，仓库零污染。

#### 第 1 轮 reviewer 验收

**重跑记录**（全部独立执行，不采信 engineer 完成区转述）：

##### 1. 证据脚本重跑（`.work/evidence/SPEC-092t/run.sh`）

```
$ bash .work/evidence/SPEC-092t/run.sh 2>&1; echo "SCRIPT_EXIT=$?"
================================================================
真实检查
[PASS] rc=0  C1 `DADAO-12`（SEE） ① deferred
     期望=deferred, no 缺口
     实际=`deferred`（`contract-sbi.md`、`contract-mmu.md`；归属 M3+，触发：SBI/地址转换消费方落地）
[PASS] rc=0  C1 `DADAO-13`（HEE） ① deferred
     期望=deferred, no 缺口
     实际=`deferred`（`contract-exception.md`；归属 M3+，触发：系统态异常消费方落地）
[PASS] rc=0  C1 `DADAO-22`（SBI） ① deferred
     期望=deferred, no 缺口
     实际=`deferred`（`contract-sbi.md`；归属 M3+，触发：SBI 消费方落地）
[PASS] rc=0  C1 `DADAO-23`（HBI） ① deferred
     期望=deferred, no 缺口
     实际=`deferred`（`contract-exception.md`；归属 M3+，触发：HBI 消费方落地）
[PASS] rc=0  C2 contract-sbi.md deferred+理由+归属
[PASS] rc=0  C2 contract-exception.md deferred+理由+归属
[PASS] rc=0  C2 contract-mmu.md deferred+理由+归属
[PASS] rc=0  C3 contract-sbi.md Process-02 deferred
[PASS] rc=0  C3 contract-exception.md Process-02 deferred
[PASS] rc=0  C3 contract-mmu.md Process-02 deferred
[PASS] rc=0  C4 登记缺口表三行无「缺口」
[PASS] rc=0  C5 make check
     期望=EXIT=0
     实际=EXIT=0 (31/31 lit PASS, repository checks: PASS)
[PASS] INJ-A README DADAO-22 ①→缺口：期望 C1 FAIL，实际 FAIL={C1 `DADAO-22`（SBI） ① deferred}
[PASS] INJ-A 还原：期望全绿，实际 全绿
[PASS] INJ-B P02 contract-mmu 状态→缺口：期望 C3 FAIL，实际 FAIL={C3 contract-mmu.md Process-02 deferred}
[PASS] INJ-B 还原：期望全绿，实际 全绿
[INFO] 注入非空：INJ-A=True  INJ-B=True
SPEC-092t evidence: PASS
EVIDENCE_EXIT=0
SCRIPT_EXIT=0
```

##### 2. 独立 `make check` 重跑

```
$ make check 2>&1 | tail -5; echo "MAKE_CHECK_EXIT=${PIPESTATUS[0]}"
Total Discovered Tests: 31
  Passed: 31 (100.00%)
check_issues: 100 open, 19 closed (0 blocking M1-gate: 0)
repository checks: PASS
MAKE_CHECK_EXIT=0
```

##### 3. 独立注入反例（自制脚本，沙盒内存操作，不碰仓库）

```python
# INJ-1: README DADAO-12 ①列 deferred→缺口（contract-sbi.md）
needle = '`deferred`（`contract-sbi.md`、`contract-mmu.md`；归属 M3+，触发：SBI/地址转换消费方落地）'
inj1_readme = readme.replace(needle, '`缺口`（`contract-sbi.md`）', 1)
# → C1 `DADAO-12`（SEE） ① deferred  FAIL ✓
# 还原后全绿 ✓

# INJ-2: Process-02 contract-sbi 状态→缺口
inj2_p02 = p02[:m.start(1)] + m.group(1) + "**缺口**" + p02[m.end(1):]
# → C3 contract-sbi.md Process-02 deferred  FAIL ✓
# 还原后全绿 ✓
```

```
$ python3 /tmp/opencode/SPEC-092t-review/independent_inject.py 2>&1; echo "INJECT_EXIT=$?"
[BASE] fails=∅
[INJ-1] README DADAO-12 ①→缺口: FAIL=['C1 `DADAO-12`（SEE） ① deferred']
[RESTORE-1] 全绿 ✓
[INJ-2] P02 contract-sbi→缺口: FAIL=['C3 contract-sbi.md Process-02 deferred']
[RESTORE-2] 全绿 ✓
========================================
独立注入验证: PASS
INJECT_EXIT=0
```

**约束核验**：

| 约束 | 结果 | 证据 |
|------|------|------|
| 只改 `spec/README.md` + `Process-02` | ✅ 守住 | `git diff --stat` 仅两文件含本任务改动；其余 7 文件为并发 SPEC-094t（`contract-{abi,elf,isa}.md`、`contracts/abi.yaml`、`check_spec_refs.py`、两任务书） |
| 投影表①列四行无裸 `缺口`、均 `deferred` 含归属/触发 | ✅ 守住 | grep 行 77-81 全为 `deferred`（…）；C1×4 PASS |
| 登记缺口表三行 `deferred` + 理由 + 归属/触发 | ✅ 守住 | grep 行 91-93 全为 `**deferred**`；C2×3 PASS |
| Process-02 三行状态 = `deferred` | ✅ 守住 | grep 行 16-18 全为 `**deferred**`；C3×3 PASS |
| 表内无空行/连续空行 | ✅ 守住 | README 71-95 行间空行 = 表间/节间分隔（非连续）；Process-02 7-20 仅 1 空行（表→脚注） |
| 未触碰禁改区 | ✅ 守住 | `spec/DADAO-*`、`contracts/`、`tests/`、`components/`、`tools/` 无本任务 diff |
| `make check` EXIT=0 | ✅ 守住 | 独立重跑 EXIT=0，31/31 PASS，repository checks: PASS |
| 反例门控：注入→FAIL→还原→回绿 | ✅ 守住 | 脚本内置 INJ-A/B + reviewer 独立 INJ-1/2，均确认 FAIL 路径可达、还原后回绿 |
| 范围外残留 `缺口` 不属 M2 门槛② | ✅ 核实 | README:69 规则定义、README:75 SimRISC-07④浮点 oracle、README:105 流程用语——均非三叙述合约缺口 |
| 并发瞬态（SPEC-094t）未影响本任务 | ✅ 核实 | 本任务两文件 `git diff` 仅含本任务改动；`make check` EXIT=0 |

**证据脚本审核**：
- **FAIL 路径**：C1–C4 每条断言有独立 FAIL 路径（`ok=False`），无恒真/两支同结果结构 ✓
- **注入可还原**：INJ-A/B 在内存字符串上操作，`assert inj != real` 验证注入非空，还原后重跑 `run_text_checks(real, real)` 确认全绿 ✓
- **不吞退出码**：`run.sh` 用 `rc=$?; exit "$rc"` 而非 `tee` 管道 ✓
- **C5 make check**：直接 `subprocess.run(["make", "check"])` 取 `proc.returncode` ✓

**判决**：**Accepted**

全部验收标准通过：① 投影表四行①列均 deferred ② 登记缺口表三行 deferred+理由+归属 ③ Process-02 三者 deferred ④ 指向三缺口的字面缺口=0 ⑤ make check EXIT=0 ⑥ 反例门控通过。约束无违反。

#### 第 1 轮 架构师复核（独立交叉，双模型互验）

**复核方式**：不采信完成区/reviewer 转述，独立读取两文件 + 独立重跑证据脚本 + **自写独立注入**（不 import 任务自带 `check.py`）+ 独立 `make check`；全程内存/沙盒操作，**未改任何受审文件、未提交 git**。临时目录 `/tmp/opencode/SPEC-092t-xcheck/`。

**独立核验（真实命令 + 输出）**：

1. 投影表四行 ① 列 —— `grep` 实测：

   ```
   spec/README.md:77: | `DADAO-12`（SEE） | `deferred`（`contract-sbi.md`、`contract-mmu.md`；归属 M3+，触发：SBI/地址转换消费方落地） | ...
   spec/README.md:78: | `DADAO-13`（HEE） | `deferred`（`contract-exception.md`；归属 M3+，触发：系统态异常消费方落地） | ...
   spec/README.md:80: | `DADAO-22`（SBI） | `deferred`（`contract-sbi.md`；归属 M3+，触发：SBI 消费方落地） | ...
   spec/README.md:81: | `DADAO-23`（HBI） | `deferred`（`contract-exception.md`；归属 M3+，触发：HBI 消费方落地） | ...
   ```

   → 四行 ① 列均 `deferred`，含 `contract-sbi`/`exception`/`mmu`；「登记缺口」表 91/92/93 三行 = **deferred** + 理由（含「无 M2/M3 消费方」）+「归属 M3+；触发：…」。PASS。

2. `Process-02` 行 16/17/18 三行状态 = **deferred**（附理由/归属/触发）。PASS。

3. 证据脚本独立重跑：`bash .work/evidence/SPEC-092t/run.sh` → 全 PASS，`EVIDENCE_EXIT=0`，`SCRIPT_EXIT=0`（C1×4/C2×3/C3×3/C4/C5 全绿，含 make check EXIT=0）。

4. **独立注入（自写 `/tmp/opencode/SPEC-092t-xcheck/indep_inject.py`，不 import `check.py`）**：

   ```
   [BASE] fails=∅
   [INJ-1] README DADAO-22 ①→缺口: fails=['A1:`DADAO-22`（SBI）']
   [RESTORE-1] fails=∅
   [INJ-2] P02 contract-mmu 状态→缺口: fails=['A3:contract-mmu.md']
   [RESTORE-2] fails=∅
   [INJ-3] README 登记表 contract-exception 状态→缺口: fails=['A2:contract-exception.md', 'A4:contract-exception.md']
   独立注入验证: PASS
   INJECT_EXIT=0
   ```

   → 三条反例均「注入→FAIL→还原→回绿」，注入后 `git status` 受审两文件无额外污染（仍为任务本身改动）。PASS。

5. 独立 `make check`：`MAKE_CHECK_EXIT=0`（31/31 lit PASS，`repository checks: PASS`）。PASS。

6. 约束核验：

   | 约束 | 结果 | 证据 |
   |------|------|------|
   | 只动 2 文件 | ✅ 守住 | `git diff` 中本任务源改动仅 `spec/README.md`+`Process-02`；余 5 源文件（`contract-{abi,elf,isa}.md`、`contracts/abi.yaml`、`check_spec_refs.py`）属并发 `SPEC-094t`，已在完成区披露 |
   | 表内无空行 | ✅ 守住 | 表块连续：README 71-85/89-93（列数各 5）、Process-02 7-18（列数 3），无嵌入空行 |
   | 未触碰禁改区 | ✅ 守住 | `git diff --stat` 对 `spec/DADAO-12/13/22/23`、`tests/`、`components/` 为空 |
   | 不臆造合约正文 | ✅ 守住 | `.tao/knowledge/contract-{sbi,exception,mmu}.md` 均不存在（`ls` No such file） |
   | 不立 ADR | ✅ 守住 | `.tao/adr/` 无本任务新增 |
   | 反例门控可失败 | ✅ 守住 | 内置 INJ-A/B + 架构师独立 INJ-1/2/3 均 FAIL→还原→回绿 |

7. 披露项核实：残余裸 `缺口` = `README:69`（投影规则定义）、`README:75`（`SimRISC-07` ④ 浮点 oracle/向量待建）、`README:77`（`DADAO-12` ②/④「据实」）、`README:89`（表头列名「缺口（①叙述合约）」）、`README:105`（流程步骤「缺口登记」）。对照 M2 门槛② 原文（`SPEC-090k` 行 25）：「投影表『缺口』清零或显式 deferred（`spec/README.md` **4 项：`contract-asm`/`contract-sbi`/`contract-exception`/`contract-mmu`**）」——上述残余**均非**这 4 项叙述合约缺口，披露成立。

**发现**：无遗漏关键项、无约束违反；reviewer 判 **Accepted 无过严/过松**（六条验收均经独立复现，反例路径可达且可还原）。

**备注（非阻断，供后续任务参考）**：投影表仍保留 `DADAO-12` ②/④ 与 `SimRISC-07` ④ 的裸 `缺口`，属**其它投影类型**、已经任务书与证据 `[INFO]` 显式披露，且不在 M2 门槛② 清单内；若后续按「全表清零」口径收紧，须另立任务（与完成区「遗留问题」①、engineer F4 一致）。并发 `SPEC-094t` 同树改动不影响本任务两文件。

**结论**：确认 **Accepted**。
