# TESTCASES-014t: 向量 spec_cite 按新文档编号修正

**模块**：testcases
**项目里程碑**：M2
**依赖**：无
**状态**：已验证

> **处置（2026-10-04，`SPEC-090k` 核验）：改范围（继续执行，范围收窄）。**
> 原「位宽主引用」部分**已完成**（向量 `spec_cite` 已用 `SimRISC-08/09/10`；`swym` 已指 `SimRISC-11 §占位指令`）；**残留**为生成器 `tools/testcases/generate_isa_vectors.py` 的 `_ILLI_RULES`（**L974/976/978**）三条**规则引用**陈旧，与 `contracts/legality_rules.yaml` 权威值不一致：
> | `_ILLI_RULES` 键 | 现值（陈旧） | `legality_rules.yaml` 权威值 |
> |---|---|---|
> | `dst_rd0` | `SimRISC-01 §rd0 为目的寄存器约定` | `SimRISC-00 §数据寄存器` |
> | `dst_dual_same` | `SimRISC-01 §加减操作` | `SimRISC-04 §加减操作` |
> | `dst_rb0` | `SimRISC-02 §rb0 为目的寄存器约定` | `SimRISC-00 §基址寄存器` |
> **本任务收窄为**：修 `_ILLI_RULES` 三条规则引用（对齐 `legality_rules.yaml`）+ 重生成受影响向量；位宽主引用部分作废，不重复。

## 问题描述（G3）

`tests/vectors/isa/*.yaml` 的 `spec_cite` 仍用**旧文档编号**（重组前 SimRISC-01~04 的语义），共约 **589 条** 指向的文档不含该指令。例如：

- `SimRISC-01 §加减操作`（SimRISC-01 现为「取数存数」）→ 应按位宽指向 SimRISC-04/08/09/10
- `SimRISC-01 §rd0 为目的寄存器约定` → 已迁至 SimRISC-00
- `misc.yaml` 的 swym `SimRISC-04 §占位指令` → SimRISC-11

## 修改内容（收窄后）

### 1. 规则引用对齐（`tools/testcases/generate_isa_vectors.py`）

把 `_ILLI_RULES`（L974/976/978）三条规则引用的 `spec_cite` 改为与 `contracts/legality_rules.yaml` **权威值一致**：

| 键 | 现值（陈旧，删） | 新值（对齐 `legality_rules.yaml`） |
|---|---|---|
| `dst_rd0` | `SimRISC-01 §rd0 为目的寄存器约定` | `SimRISC-00 §数据寄存器` |
| `dst_dual_same` | `SimRISC-01 §加减操作` | `SimRISC-04 §加减操作` |
| `dst_rb0` | `SimRISC-02 §rb0 为目的寄存器约定` | `SimRISC-00 §基址寄存器` |

> 建议：改为**从 `contracts/legality_rules.yaml` 读取**（或与之一致），避免硬编码再次漂移；如保留常量，须加注释指向权威文件。

### 2. 重生成受影响向量

按生成器既有 `scoped` 用法重生成受影响文件（`reg-arith.yaml` / `reg-compare.yaml` / `reg-cond-assign.yaml` / `reg-imm-block.yaml` / `reg-logic.yaml` / `reg-shift-extend.yaml` 中含规则引用的用例），产物与仓库一致；**不得**全量重跑破坏既有预存漂移（见 `issues.yaml ISS-125`）。

（原「位宽主引用」「`swym` 指向 `SimRISC-11`」部分已完成，见头部「处置」，不重复。）

## 约束

- **改生成器，不改产物**
- 逐条核对，禁止正则批量替换
- 不改动向量的 word/input_state/expected 等语义字段

## 验收标准

1. 向量中不再出现陈旧规则引用：`SimRISC-01 §rd0 为目的寄存器约定` / `SimRISC-01 §加减操作` / `SimRISC-02 §rb0 为目的寄存器约定` 条数 = **0**（实测当前分别为 **87 / 6 / 6** 条：`§rd0` 分布 reg-arith 35 + reg-compare 11 + reg-cond-assign 5 + reg-imm-block 4 + reg-logic 4 + reg-shift-extend 28；`§加减操作` 在 reg-arith 6；`§rb0` 分布 reg-arith 3 + reg-imm-block 3）。
2. 受影响向量中的规则引用与 `contracts/legality_rules.yaml` 的 `dst_rd0`/`dst_dual_same`/`dst_rb0` 逐条一致（独立复算，非抽样）。
3. `python3 tools/testcases/validate_vectors.py` EXIT=0（**152/152**，gaps 0）。
4. `make check` **EXIT=0**；`check-legality-drift` 不回归。
5. 向量的语义字段（`word`/`input_state`/`expected_state`）**逐字节未改**（`git diff` 只含 `spec_cite` 行）。
6. `git diff --name-only` 只含 `tools/testcases/generate_isa_vectors.py` 与受影响向量文件（**不误伤** 4 个预存漂移文件，见 `ISS-125`）。
7. 一键证据脚本：非交互、任一失败即非零退出、逐项打印「检查名 + 期望/实际 + 退出码」+ 注入反例自检（如把 `dst_rd0` 改回陈旧值 → 自检 FAIL）。落点 `.work/evidence/TESTCASES-014t/`。

## 完成区
**测试结果**：全部通过。
- 一键证据脚本 `.work/evidence/TESTCASES-014t/run.sh` **EXIT=0**（`ALL CHECKS PASS`，E0–E7 逐项 PASS）；输出留 `.work/log/testcases/TESTCASES-014t-run_sh.log`。
- E0 生成器权威对齐：`_ILLI_RULES` 的 `dst_rd0`/`dst_dual_same`/`dst_rb0` 与 `contracts/legality_rules.yaml` 逐条相等（3/3）。
- E1 独立核验 `check_spec_cite.py` **EXIT=0**：C1 陈旧引用 **0**（原 87/6/6）；C2 **逐条**独立复算 **99 条 0 mismatch**；C3 各文件目标用例数 = 期望（44/11/5/7/4/28）；C4 与修正后生成器输出按 `(id,class,word,input_state)` 交叉比对 **99/99 命中同 cite**。
- E2 反例自检：注入「`dst_rd0` 改回陈旧值」→ C1/C3 **FAIL**（`check_spec_cite: FAILED (2)`）→ 还原 `restored=YES` → 回绿（`--inject` 内含）；另手动证明 C2 可达 FAIL：把一条 `dst_dual_same` 规则引用错改为 `dst_rd0` 值 → `C2 ... rule=dst_dual_same expected='SimRISC-04 §加减操作' got='SimRISC-00 §数据寄存器'` FAIL → 还原 EXIT=0。
- E3 `python3 tools/testcases/validate_vectors.py` **EXIT=0**：`152/152 M1 identities covered OK (inventory sync OK; 15 data files, 694 cases; data coverage gaps: 0)`。
- E4 `make check` **EXIT=0**：`repository checks: PASS`（lit 31/31；`check-legality-drift` 等随之全绿）。日志 `.work/log/testcases/TESTCASES-014t-make_check.log`。
- E5 `git diff`（`tests/vectors/isa/*.yaml`）非 `spec_cite` 变更行 = **0**（spec_cite 改 198 行 = 99 删 + 99 增）。
- E7 `reg-cond-assign.yaml`/`reg-imm-block.yaml` 与「修正后生成器 scoped 输出」**逐字节相同**（`cmp`）。

**修改文件**：
- `tools/testcases/generate_isa_vectors.py`：`_ILLI_RULES` 三条规则引用改为 `contracts/legality_rules.yaml` 权威值（`dst_rd0 → SimRISC-00 §数据寄存器`、`dst_dual_same → SimRISC-04 §加减操作`、`dst_rb0 → SimRISC-00 §基址寄存器`），并加注释指向权威文件；`mreg_zero` 维持不变（其权威值含 5 段、生成器有意只取 RD 锚点，改之会越界动 reg-imm-block）。
- 6 个向量文件（**仅** `spec_cite` 规则后缀行，共 99 行）：`reg-arith.yaml` 44（rd0 35 + dual 6 + rb0 3）、`reg-compare.yaml` 11、`reg-cond-assign.yaml` 5、`reg-imm-block.yaml` 7（rd0 4 + rb0 3）、`reg-logic.yaml` 4、`reg-shift-extend.yaml` 28。
- `.work/evidence/TESTCASES-014t/`：`run.sh`（一键证据）、`check_spec_cite.py`（独立 oracle + `--inject`）、`update_spec_cite.py`（规则引用对齐工具）。`.work/log/testcases/TESTCASES-014t-*.log` 留证。

**验收结果**（真实命令 + 退出码；每项「期望/实际」）：
1. 陈旧引用条数 = 0 / 实测 0（87/6/6 → 0/0/0）—— `run.sh` E1 C1 PASS。
2. 规则引用与 `legality_rules.yaml` 逐条一致 —— E1 C2 99/99 0 mismatch + C4 99/99 生成器交叉 PASS。
3. `validate_vectors.py` EXIT=0 / 152/152、gaps 0 —— E3 PASS。
4. `make check` EXIT=0、`check-legality-drift` 不回归 —— E4 PASS。
5. 语义字段逐字节未改、`git diff` 只含 `spec_cite` 行 —— E5 非 spec_cite 变更行 = 0；与改前备份逐文件 `grep -v spec_cite` diff 行数 = 0，行数不变（4272/617/359/813/296/2067）。
6. `git diff --name-only`（限定 `tools/testcases/generate_isa_vectors.py` + `tests/vectors/isa`）= 预期 7 文件；**未误伤** 4 个预存漂移文件的非 `spec_cite` 内容 —— E6 PASS。
7. 一键证据脚本非交互、任一失败即非零退出、逐项打印「检查名+期望/实际+退出码」、内置注入自检、结尾不 `tee` 吞退出码 —— `run.sh` 结构核查（见自审）。

**新发现/坑**：
1. **ISS-125 预存漂移使「全量/scoped 重生成」对 4 文件不可用**：修正后生成器全量跑 `reg-arith.yaml` 会删 **837 行**（SPEC-066t div/rem 定值块）、`reg-compare.yaml` 117 行、`reg-shift-extend.yaml` 40 行、`reg-logic.yaml` 10 行（含各缺头注 + 手补用例/值）。故 4 文件采用**逐条 spec_cite 后缀替换**（非正则、非全量），以 `check_spec_cite.py` 逐条独立复算 + C4 与生成器输出交叉坐实；`reg-cond-assign`/`reg-imm-block`（无漂移）经验证与生成器 scoped 输出逐字节相同。
2. **任务书内部矛盾**：约束「**改生成器，不改产物**」与 §2「重生成受影响向量」及验收 1/2/5/6（要求产物变更）冲突；按验收标准与 §2 执行（产物仅 `spec_cite` 变更），此点披露备裁。
3. **HEAD 已有 3 条 `SimRISC-00 §数据寄存器`（`ctrl-ret.yaml` `ret_riii_ra`）**，非本次新增；本次变更后 `SimRISC-00 §数据寄存器` 规则引用共 90 条（87 迁移 + 3 既有）。
4. **工作区存在本任务以外的并发脏改**（另会话正在进行）：`.tao/knowledge/{contract-abi.md,contract-isa.md,changelog.md}`、`.tao/tasks/spec/SPEC-030t-*.md`、`.tao/tasks/spec/SPEC-033t-*.md`；本任务均未触碰（仅在 E6 中如实打印，未纳入 scoped 范围）。
5. **建议沉淀**：`_ILLI_RULES` 为**硬编码副本**、易与 `legality_rules.yaml` 漂移；作者已加「AUTHORITY」注释，但理想方案是生成期直接读合约（受 `mreg_zero` 有意收窄所限，未在本任务实施）。

**遗留问题**：
- **ISS-125 生成器↔向量预存漂移仍未清偿**（4 文件），本任务仅以最小 `spec_cite` 改动规避，未做全量重生成；建议后续 testcases 专任务（先修生成器忠实复现，再全量重生成）。
- `_ILLI_RULES` 硬编码副本与合约的双源问题未根除（仅注释约束）。
- 本任务的规则引用覆盖**不含** `mreg_zero`（其陈旧性不在本任务范围；reg-imm-block 的 RA 引用为既有手工订正）。
- 工作区并发脏改非本任务产出，未处置。

## 审阅记录

#### 第 1 轮 engineer 自审

**自主逐行审查**（改动源码 + 产物 + 证据脚本，不依赖 reviewer）：

- `tools/testcases/generate_isa_vectors.py`：仅改 `_ILLI_RULES` 3 个字符串常量 + 加注释；未改函数签名/控制流；`dst_rd0`/`dst_dual_same`/`dst_rb0` 使用点（L1006/1105/1119/1457）随之取新值。`mreg_zero` 有意不动（权威值含 5 段，生成器仅 RD 锚点）——改之会连带改 reg-imm-block 中 `mreg_zero` 引用，越界。✅
- 向量产物：99 处替换均为 `spec_cite` 行**行尾** `; <old>` 精确后缀替换；`grep -v spec_cite` 与改前备份逐文件 diff = 0、行数不变；`expected_fault`/`word`/`input_state`/`expected_state` 未动。✅
- 路由正确性：`_get_illi_rule_id`（rrrr→dual、非 rrrr 按 dst bank）与 `check_spec_cite.py::route_rule` 独立实现一致；`cs.*` rrrr 归 `dst_rd0`（rrrr 特例）已单独处理。✅
- 独立 oracle（`check_spec_cite.py`）：C1/C2/C3/C4 均非恒真；C2 按 opcodes 独立复算（99 条）而非读生成器常量；C4 以 `(id,class,word,input_state)` 匹配生成器输出。已用两种注入分别证明 C1/C3 与 C2 的 FAIL 路径可达、且可还原。✅
- 证据脚本（`run.sh`）：非交互；各命令直接 `$?` 捕获、未用 `tee`；E5/E6/E7 有独立失败判据；E7 建临时树不改仓库。✅
- 防造假：所有结论来自真实重跑；`git diff --name-only` 非空校验；注入还原以 `restored=YES` + 回绿确认。✅

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| ISS-125 漂移致 4 文件无法全量/scoped 重生成 | ✅已修（限本任务范围） | 4 文件用逐条 `spec_cite` 后缀替换；2 无漂移文件经生成器 scoped 输出 cmp 证实 | `run.sh` E5（非 spec_cite 变更 0）、E7 cmp 逐字节同、C4 99/99 |
| 任务书约束「不改产物」与验收冲突 | ✅已披露 | 按 §2/验收 1/2/5/6 执行（仅 `spec_cite` 变更） | 完成区「新发现/坑」2 |
| `_ILLI_RULES` 硬编码双源 | ⏸延后 | 仅加 AUTHORITY 注释（读合约会因 `mreg_zero` 收窄而越界） | 完成区「遗留问题」 |
| 工作区并发脏改（`.tao/**` 非本任务） | ❌不修 | 未触碰 | `git diff --name-only` 如实打印，scoped 范围不含 |
| 其余 4 文件生成器漂移未清偿 | ⏸延后 | 越界；仅登记 | 建议后续 testcases 专任务 |

**判决**：本任务范围内所有 finding 已修/已证；无未修 finding。可标「待验收」。

#### 第 1 轮 reviewer 验收

**独立重跑记录**（所有命令由 reviewer 在 `/tmp/opencode/TESTCASES-014t-review/` 下执行，不依赖 engineer 产出）：

**R0. `_ILLI_RULES` 三条规则引用核实**

人工读取 `tools/testcases/generate_isa_vectors.py` L972-985 与 `contracts/legality_rules.yaml` L26-73：
| 键 | 生成器值 | legality_rules.yaml 权威值 | 一致 |
|---|---|---|---|
| `dst_rd0` | `SimRISC-00 §数据寄存器` | `SimRISC-00 §数据寄存器` (L29) | ✅ |
| `dst_dual_same` | `SimRISC-04 §加减操作` | `SimRISC-04 §加减操作` (L60) | ✅ |
| `dst_rb0` | `SimRISC-00 §基址寄存器` | `SimRISC-00 §基址寄存器` (L69) | ✅ |
| `mreg_zero` | `SimRISC-01 §存取RD寄存器`（未改） | 5 段权威值 (L104)，生成器有意只取 RD 锚点 | ✅ 未动 |

`git diff tools/testcases/generate_isa_vectors.py` 确认：仅改 3 条值 + 加 4 行 AUTHORITY 注释，未改函数签名/控制流。✅

**R1. 陈旧引用清零 + 向量 diff 核实**

```bash
$ grep -r 'SimRISC-01 §rd0 为目的寄存器约定' tests/vectors/isa/ | wc -l
0
$ grep -r 'SimRISC-01 §加减操作' tests/vectors/isa/ | wc -l
0
$ grep -r 'SimRISC-02 §rb0 为目的寄存器约定' tests/vectors/isa/ | wc -l
0
```
三种陈旧引用 = 0/0/0。✅

```bash
$ git diff tests/vectors/isa/ | grep '^[+-]' | grep -v '^[+-][+-][+-]\|spec_cite' | wc -l
0
$ git diff tests/vectors/isa/ | grep '^[+-]' | grep -v '^[+-][+-][+-]' | wc -l
198
```
非 `spec_cite` 变更行 = 0；总变更行 = 198（99 删 + 99 增）。✅

**R2. 独立 oracle `check_spec_cite.py`**

```bash
$ python3 .work/evidence/TESTCASES-014t/check_spec_cite.py
C1 stale rule citations: 0 (expect 0) PASS
C2 per-case recompute: 99 cases checked, 0 mismatch PASS
C3 reg-arith.yaml           target-cases=44 expect=44 PASS
C3 reg-compare.yaml         target-cases=11 expect=11 PASS
C3 reg-cond-assign.yaml     target-cases=5 expect=5 PASS
C3 reg-imm-block.yaml       target-cases=7 expect=7 PASS
C3 reg-logic.yaml           target-cases=4 expect=4 PASS
C3 reg-shift-extend.yaml    target-cases=28 expect=28 PASS
C3 per-file counts: PASS
check_spec_cite: PASS
EXIT=0
```
C1 陈旧引用=0，C2 99 条 0 mismatch，C3 各文件计数全对。✅

**R3. 一键证据脚本 `run.sh` 独立重跑**

```bash
$ bash .work/evidence/TESTCASES-014t/run.sh
E0: dst_rd0/dst_dual_same/dst_rb0 全 OK
E1: check_spec_cite PASS (C1=0, C2=99/99, C3 全 PASS)
E2: inject → C1 stale=1 FAIL + C3 43≠44 FAIL → restored=YES → PASS
E3: validate_vectors 152/152 EXIT=0
E4: make check EXIT=0 (lit 31/31, repository checks: PASS)
E5: spec_cite=198, non-spec_cite=0
E6: scoped 7 文件，未误伤
E7: reg-cond-assign/reg-imm-block cmp 逐字节同 + C4 99/99
ALL CHECKS PASS
EXIT=0
```
✅

**R4. 独立注入反例**

reviewer 自行执行注入（不依赖 engineer 的 `--inject`）：
```bash
# 注入：将 reg-arith.yaml 中第一条 SimRISC-00 §数据寄存器 替换回陈旧值
$ python3 -c "
text = open('tests/vectors/isa/reg-arith.yaml').read()
injected = text.replace('; SimRISC-00 §数据寄存器', '; SimRISC-01 §rd0 为目的寄存器约定', 1)
open('tests/vectors/isa/reg-arith.yaml', 'w').write(injected)
print('injected 1 stale reference')
"
injected 1 stale reference

$ python3 .work/evidence/TESTCASES-014t/check_spec_cite.py
C1 stale rule citations: 1 (expect 0) FAIL
C2 per-case recompute: 98 cases checked, 0 mismatch PASS
C3 reg-arith.yaml           target-cases=43 expect=44 FAIL
check_spec_cite: FAILED (2)
EXIT=1
```
注入后 C1 stale=1 + C3 43≠44 → FAIL（EXIT=1）。✅ checker 可失败。

```bash
# 还原
$ cp /tmp/opencode/TESTCASES-014t-review/reg-arith.yaml.bak tests/vectors/isa/reg-arith.yaml
$ python3 -c "orig=open('/tmp/opencode/TESTCASES-014t-review/reg-arith.yaml.bak').read(); curr=open('tests/vectors/isa/reg-arith.yaml').read(); print('restored:', 'YES' if orig==curr else 'NO')"
restored: YES

$ python3 .work/evidence/TESTCASES-014t/check_spec_cite.py
C1 stale rule citations: 0 (expect 0) PASS
C2 per-case recompute: 99 cases checked, 0 mismatch PASS
C3 全 PASS
check_spec_cite: PASS
EXIT=0
```
还原后回绿（EXIT=0）。✅

**R5. `validate_vectors.py` 独立重跑**

```bash
$ python3 tools/testcases/validate_vectors.py
validate_vectors: 152/152 M1 identities covered OK (inventory sync OK; 15 data files, 694 cases; data coverage gaps: 0)
EXIT=0
```
✅

**R6. `make check` 独立重跑**

```bash
$ make check
lit 31/31 PASS
check-legality-drift: PASS
repository checks: PASS
EXIT=0
```
✅

**R7. 文件范围核实**

```bash
$ git diff --name-only -- tools/testcases/generate_isa_vectors.py tests/vectors/isa
tests/vectors/isa/reg-arith.yaml
tests/vectors/isa/reg-compare.yaml
tests/vectors/isa/reg-cond-assign.yaml
tests/vectors/isa/reg-imm-block.yaml
tests/vectors/isa/reg-logic.yaml
tests/vectors/isa/reg-shift-extend.yaml
tools/testcases/generate_isa_vectors.py
```
7 文件，未误伤 4 个预存漂移文件的非 spec_cite 内容。✅

**约束核验**：

| 约束 | 核实结果 |
|---|---|
| ① 未做全量重生成（ISS-125 预存漂移） | ✅ 仅 spec_cite 替换，4 漂移文件未误伤；2 无漂移文件经 cmp 证实与生成器输出一致 |
| ② 任务书内部矛盾（「改生成器不改产物」vs 验收） | ✅ engineer 按验收标准执行（产物仅 spec_cite 变更），已披露 |
| ③ 工作区并发他任务改动非本任务所为 | ✅ `.tao/knowledge/`、`.tao/tasks/spec/` 改动非本任务范围，scoped diff 不含 |

**证据脚本审查**：
- `run.sh`：非交互（`set -uo pipefail`）；`verdict()` 函数任一 FAIL 置 `FAIL=1`；结尾不 `tee` 吞退出码；E2 inject 含 FAIL→restore→回绿自检。✅
- `check_spec_cite.py`：C1/C2/C3 非恒真；C2 按 `opcodes.yaml` 独立路由（`route_rule()`），不读生成器常量；inject 函数实际替换→FAIL→还原→回绿。✅

**注意**：reviewer 首次运行 `check_spec_cite.py`（不带 `--inject`）时曾出现 EXIT=1（C1 stale=1, C3 43≠44），但紧接着运行 `--inject` 后还原，后续连续 2 次重跑均 EXIT=0。推测首次运行时文件处于 inject 测试的中间状态（可能上一次 engineer 测试未完全还原），但无法复现。当前状态已确认干净。

**判决：Accepted**

验收命令块在 reviewer 独立重跑下全部通过（EXIT=0），约束无违反。`_ILLI_RULES` 三条规则引用已对齐 `legality_rules.yaml`，向量 99 条 spec_cite 修正正确且无语义字段变更，oracle 可失败（注入→FAIL→还原→回绿已独立证实）。

#### 架构师复核（第 1 轮，双模型互验；本复核模型：DeepSeek V4.1 Flash）

> 独立核验：全部命令在 `/tmp/opencode/TESTCASES-014t-xcheck/` 下执行，**未复用** engineer/reviewer 的脚本逻辑（自写 oracle），**未改任何交付产物、未提交 git**。

**A1. `_ILLI_RULES` 三条规则引用 vs 权威值（逐条）**
AST 解析生成器常量 + 读 `contracts/legality_rules.yaml`：
```
dst_rd0:       EQUAL  gen='SimRISC-00 §数据寄存器' auth='SimRISC-00 §数据寄存器'
dst_dual_same: EQUAL  gen='SimRISC-04 §加减操作'   auth='SimRISC-04 §加减操作'
dst_rb0:       EQUAL  gen='SimRISC-00 §基址寄存器' auth='SimRISC-00 §基址寄存器'
ALL3 EQUAL: True
```
`git diff` 中 `mreg_zero` 值行仅为上下文（未改）；向量侧含 `存取RD寄存器` 的变更行 = 0。✅

**A2. 非 spec_cite 变更 = 0 / 语义字段逐字节未改（独立复算，非抽样）**
- 陈旧引用 `SimRISC-01 §rd0 为目的寄存器约定` / `SimRISC-01 §加减操作` / `SimRISC-02 §rb0 为目的寄存器约定` → **0/0/0**；HEAD 侧分别为 **87/6/6**。
- 向量 `git diff` 总 +/- 行 = **198**（99 删 + 99 增），非 spec_cite 变更行 = **0**。
- **逐行配对**（99 对）核验：每对 `old→new` 均为「base cite 不变、仅尾部规则引用后缀替换」，映射全部命中 `OLD2NEW`；`bad=0`。
- **语义字段**：6 文件以「剥离尾部规则引用后缀」后与 HEAD 逐行比对，**逐字节相同**、行数不变（4272/617/359/813/296/2067）。✅

**A3. 独立 oracle（自写，仅从 `contracts/` 派生，不读生成器常量）**
扫描**全部** isa 文件（不止 EXPECT 6 文件）：
```
stale count: 0
checked: 102 mismatch: 0
per-file target counts: ctrl-ret=3, reg-arith=44, reg-compare=11, reg-cond-assign=5, reg-imm-block=7, reg-logic=4, reg-shift-extend=28
distinct target-value counts: {'SimRISC-00 §数据寄存器':90, 'SimRISC-04 §加减操作':6, 'SimRISC-00 §基址寄存器':6}
```
102 条（含 `ctrl-ret.yaml` 既有 3 条）0 mismatch；90=87 迁移+3 既有，与完成区一致。✅

**A4. 证据脚本重跑 + 独立注入（异于 engineer/reviewer 的 FAIL 路径）**
- `bash .work/evidence/TESTCASES-014t/run.sh` → `ALL CHECKS PASS`、**EXIT=0**（E0–E7 全 PASS）。
- 复核者独立注入（**更强判别力**）：将 `reg-imm-block.yaml` 一条 `dst_rb0`（`§基址寄存器`）改为 `dst_rd0` 值（`§数据寄存器`）——后缀仍 ∈ new_vals，**C1/C3 计数不受影响**，仅 `C2` 应触发：
```
C1 stale rule citations: 0 PASS
C2 per-case recompute: 99 cases checked, 1 mismatch FAIL
  FAIL: C2 reg-imm-block.yaml id=or.w_rwii_rb word=0x4A000000 rule=dst_rb0 expected='SimRISC-00 §基址寄存器' got='SimRISC-00 §数据寄存器'
check_spec_cite: FAILED (1)   EXIT=1
```
还原后 `EXIT=0`、向量 diff 恢复 198/0。**证明 C2 非「成员性」恒真断言，具真实路由判别力**（reviewer 的注入仅触 C1/C3；本条为复核者独立重做）。✅

**A5. 门控独立重跑（退出码）**
```
python3 tools/testcases/validate_vectors.py
  validate_vectors: 152/152 M1 identities covered OK (15 data files, 694 cases; data coverage gaps: 0)
  VALIDATE_EXIT=0
make check
  check-legality-drift: 12 chapters OK ; lit 31/31 ; check_issues: 100 open, 19 closed (0 blocking)
  repository checks: PASS
  MAKE_CHECK_EXIT=0
```
`check-legality-drift` 不回归。✅

**A6. 披露项核实**
- ① **ISS-125**（`open`）确证：标题「生成器↔向量预存漂移（全量重跑会破坏 5 文件）」、notes「余 4 文件（reg-arith/reg-compare/reg-logic/reg-shift-extend）债务未清」；本任务未全量重生成属实，且未误伤 4 文件。✅
- ② **任务书内部矛盾**属实：L47 约束「改生成器，不改产物」与 L15 处置「+ 重生成受影响向量」、§2、验收 1/2/5/6 直接冲突，二者不可同时满足；**处置头部（最新、权威）**与验收标准一致要求产物变更，engineer 取验收/§2 的读法是**唯一自洽**选择，reviewer 接受正确。建议后续架构师**修订任务书消除该矛盾**（非阻断）。✅
- ③ **并发脏改**确证非本任务：`.tao/knowledge/{changelog,contract-abi,contract-isa}.md`、`SPEC-030t`/`SPEC-033t` 均属 `.tao/` 且非 testcases，scoped diff 不含。✅

**A7. reviewer 记录的「瞬态 EXIT=1」核实**
- 证据：reviewer 工作区 `/tmp/opencode/TESTCASES-014t-review/check_spec_cite.log`（11:04:36）确存 `stale=1 / C3 43≠44`——与 `--inject` 注入窗口**签名完全一致**；同刻 `check_spec_cite_inject.log` 亦为同签名（正常注入输出）。
- 机理：`run.sh` E2 与 `check_spec_cite.py --inject` **就地改写仓库工作树文件** `tests/vectors/isa/reg-arith.yaml`（非临时副本），任何并发读取都会命中该窗口 → 伪 FAIL。属**证据脚本并发不安全性**，非交付产物缺陷。
- 当前状态确证干净：`check_spec_cite.py` 多次重跑 EXIT=0；A2 尾缀剥离比对与 HEAD 逐字节一致；reviewer 的 `reg-arith.yaml.bak`（11:06:27，晚于瞬态）与当前工作文件 `diff` 完全相同且 `stale=0`。**瞬态已消除、不可复现，结论不受影响。**
- 建议（非阻断）：`--inject`/E2 改为在临时副本（或经 `REPO`/`VEC` env 覆盖指向 temp tree）上执行，避免污染共享工作树与并发竞态。

**复核判决：Accepted（确认 reviewer 判决）**

独立核验的 6 类硬证据（生成器↔权威逐条相等、非 spec_cite 变更 0 且语义字段逐字节未改、独立 oracle 102 条 0 mismatch、证据脚本重跑 + 更强独立注入可失败、`validate_vectors`/`make check` EXIT=0）全部通过；披露项属实；无遗漏关键项、无约束违反，reviewer 判决**不过严也不过松**。两条非阻断改进建议（证据脚本并发安全、任务书矛盾消解）供后续处置。