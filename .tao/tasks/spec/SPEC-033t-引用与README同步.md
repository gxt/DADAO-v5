# SPEC-033t: contract-abi 引用修正 + docs/README 同步

**模块**：spec
**项目里程碑**：M2
**依赖**：无
**状态**：已验证

> **处置（2026-10-04，`SPEC-090k` 核验）：改范围（继续执行，范围收窄）。**
> 原两项中 **G5（`docs/README.md:17` 同步）已完成**（现为当前口径 `227 = M1 152 + scope fp 60 + scope excluded 15`）；**G4（`contract-abi.md` 引用陈旧）仍有效**——实测 `.tao/knowledge/contract-abi.md:209` 仍写 `SimRISC-02 §函数调用`/`§函数返回`，而 `SimRISC-02` 现为「寄存器复制」（无此二节），`SimRISC-06-控制流.md` 有「### 函数调用」「### 函数返回」（L107/L130）。**本任务收窄为仅修 `contract-abi.md` 的 2 处**；下文 G5 及 `docs/README.md` 相关项作废，不执行。

## 问题描述

### G4. contract-abi.md 引用陈旧（2 处）

- `.tao/knowledge/contract-abi.md:142`：`[SimRISC-02 §函数调用]`、`[SimRISC-02 §函数返回]`
- `.tao/knowledge/contract-abi.md:143`：`[SimRISC-02 §函数调用]`

`SimRISC-02` 现为「寄存器复制」；`§函数调用`/`§函数返回` 已迁至 `SimRISC-06-控制流.md`。**应改为 `SimRISC-06`**。

### G5. docs/README.md:17 陈旧

第17行 assembly-list 描述仍为旧顺序/旧名/旧计数：
```
| `assembly-list.md` | ...256 条，按 8位数据运算/16位数据运算/32位数据运算/64位数据运算/64位地址运算/浮点/存储/控制流/寄存器复制/16位立即数操作/其它/待定 分章...；浮点（46）与待定（14）两章整章 deferred... |
```
应为：
```
| `assembly-list.md` | ...254 条，按 取数存数/寄存器复制/16位立即数操作/64位数据运算/64位地址运算/控制流/浮点运算/32位数据运算/16位数据运算/8位数据运算/其它/待定 分章...；浮点运算（46）与待定（12）两章整章 deferred... |
```

## 修改内容

1. `contract-abi.md` 的 `SimRISC-02 §函数调用`/`§函数返回` → `SimRISC-06`

（原第 2 项 `docs/README.md` 已于 2026-10-03/04 完成，见头部「处置」，不再执行。）

## 约束

- 逐条精确替换，**禁止正则批量替换**
- 不改动其他内容

## 验收标准

1. `contract-abi.md` 中无 `SimRISC-02 §函数调用`/`§函数返回`（改为 `SimRISC-06`）
2. `docs/README.md` 与其它文件未改动（`git diff` 只含 `contract-abi.md`）
3. 一键证据脚本：逐项打印「检查名 + 期望/实际 + 退出码」；任一失败即非零退出；内置注入反例自检（如把改好的引用还原为 `SimRISC-02` → 自检 FAIL）。落点 `.work/evidence/SPEC-033t/`。

## 完成区
**测试结果**：一键证据脚本默认模式 **12/12 PASS，EXIT=0**；反例自检模式（`--inject`）**17/17 PASS，EXIT=0**（含注入→FAIL→还原→回绿 5 项）。`make check` **EXIT=0**（lit 31/31、repository checks PASS）。
**修改文件**：`.tao/knowledge/contract-abi.md`（1 行：§2.3 引用 `SimRISC-02 §函数调用`/`§函数返回` → `SimRISC-06`）；新增一键证据脚本 `.work/evidence/SPEC-033t/run.sh`（`.work/` 不入库）。**无其它归属本任务的改动**。
**验收结果**：
- `.tao/knowledge/contract-abi.md` 中 `SimRISC-02` 残留 = **0**；§2.3 行现为 `SimRISC-06 §函数调用`、`§函数返回`（第 209 行）。
- 目标依据核验：`spec/SimRISC-06-控制流.md` 含 `### 函数调用`(L107)/`### 函数返回`(L130)；`spec/SimRISC-02-寄存器复制.md` 无此二节（`grep -cE '^### (函数调用|函数返回)'` = 0）。
- 本任务 diff 精确为 contract-abi.md 的 1 行替换（证据脚本 check 7：`git diff -- contract-abi.md` 恰 1 add / 1 del，增行含 `SimRISC-06 §函数调用`、删行含 `SimRISC-02 §函数调用`）。
- `docs/README.md` 未改动；`spec/` 下无改动。
- `make check`：`EXIT=0`（日志 `.work/log/spec/SPEC-033t-make_check.log`）；证据脚本输出 `.work/log/spec/SPEC-033t-evidence-{default,inject}.log`。
**新发现/坑**：
1. 任务书 G4 正文引用的 `contract-abi.md:142/143` 在 HEAD 中**已为 `SimRISC-06`**（`git log` 显示 `93ba173 SPEC-084t` 已处理）；实际残留仅 **209 行**一处，与任务书头部「处置」块一致——以头部处置为准。
2. 反例自检还原**不可用 `git checkout -- <file>`**：目标文件本就有未提交改动（本次修复），`git checkout` 会把修复一并丢弃，导致「还原 sha 不匹配」假 FAIL。须用**工作副本备份/还原**（本脚本已改）。
3. **执行期间工作树存在并发外部改动**（非本任务）：`.tao/knowledge/contract-isa.md`、`tools/testcases/generate_isa_vectors.py`、`tests/vectors/isa/*.yaml`（6 个）、`.tao/tasks/spec/SPEC-030t-文档收尾同步.md`，其 mtime 在本任务执行中持续推进（属其它会话的并行任务）。
**遗留问题**：
- 验收标准 #2「`git diff` 只含 `contract-abi.md`」在**当前工作树不成立**——原因是上述并发外部改动（本任务执行期间由其它会话写入，mtime 持续推进，且与本任务引用修正无关）。本任务**可归属**改动已由证据脚本 check 7 证明仅为 `contract-abi.md` 的 1 行替换；**未触碰**任何越界文件。建议：待并发会话提交后复核 `git diff`（届时应只剩本任务改动）。**本条不影响本任务自身交付正确性**，但需主会话知悉。
- 任务书原 G5（`docs/README.md:17`）按头部处置**已作废**，未执行。

## 审阅记录

#### 第 1 轮 engineer 自审
逐行审查范围：`.tao/knowledge/contract-abi.md`（diff 单行）、`.work/evidence/SPEC-033t/run.sh`（全文件）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 任务书 G4 所述 142/143 行已在 HEAD 修复，实际仅 209 行残留 | ✅已核 | 不改文件；以头部「处置」为准仅改 209 行 | `git log -- contract-abi.md` 显示 `93ba173 SPEC-084t`；`grep -n SimRISC-02` 修复前仅命中 209 |
| F2 证据脚本 `report` 签名 5 参 vs 调用 4 参 → `unbound variable` | ✅已修 | `report()` 改为 4 参（rc 驱动 pass/fail）并统一各调用 | 默认模式 12/12、inject 17/17 均 EXIT=0 |
| F3 反例还原用 `git checkout` 会丢弃未提交的本次修复 → 假 FAIL | ✅已修 | 改为 `cp` 工作副本备份 + `cp` 还原 | inject 轮 `restore sha256 matches pre-injection` PASS（sha `345ff177…` 前后一致） |
| F4 check 7 用「全工作树 changed 集合 == {contract-abi.md}」会因并发外部改动假 FAIL | ✅已修（并披露） | 改为精确校验 contract-abi.md 的 1+/1− 行 + `docs/README.md` 未改 + `spec/` 未改，并 NOTE 披露全部 changed 文件 | 默认/inject 均 PASS；NOTE 列出外部文件（contract-isa.md、generate_isa_vectors.py、vectors、SPEC-030t） |
| F5 每条断言 FAIL 路径核验 | ✅已核 | 逐条确认：check1（残留计数≠0 即 FAIL）、check2/3（grep 不命中即 FAIL）、check4/5（SimRISC-06 缺节即 FAIL）、check6（SimRISC-02 有节即 FAIL）、check7 四条（增/删行数≠1、增/删行不含预期串即 FAIL）、check8（docs/README 被改即 FAIL）、check9（spec/ 有改动即 FAIL）；inject 轮注入后核心谓词必须 FAIL | `--inject` 真实输出：`core predicate FAILs under injection` PASS（实际 FAIL）、还原后 `green after restore` PASS |
| F6 无恒真/两支同写 | ✅已核 | `abi_ref_ok()` 为唯一核心谓词，默认与 inject 复用；inject 的 PASS/FAIL 由实际谓词返回值决定 | inject 轮注入时实测谓词返回非零（FAIL），未注入时为零（PASS） |

**自审判决**：所有 finding 已修/已核；无未决项。状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer subagent
**审查时间**：2026-10-04

##### 1. 文件内容核验

`contract-abi.md` 第 209 行（`grep -n '函数调用\|函数返回'`）：
```
209: | §2.3 | `call`/`ret` 与 RegRAS | `SimRISC-06 §函数调用`、`§函数返回`；`contract-isa.md §5.4–§5.6` |
```
✅ `SimRISC-02` 残留 = 0（`grep -c 'SimRISC-02'` = 0）；`SimRISC-06 §函数调用` 和 `§函数返回` 均存在。

`spec/SimRISC-06-控制流.md` 核验（独立确认目标引用有效）：
```
107:### 函数调用
130:### 函数返回
```
✅ 目标章节存在。

`git diff --numstat -- .tao/knowledge/contract-abi.md`：
```
1	1	.tao/knowledge/contract-abi.md
```
✅ 恰 1 行增、1 行删，范围精确。

##### 2. 证据脚本审阅

审阅 `.work/evidence/SPEC-033t/run.sh`（147 行）：
- **FAIL 路径**：check 1（残留计数≠0 → FAIL）、check 2/3（grep 不命中 → FAIL）、check 4/5（SimRISC-06 缺节 → FAIL）、check 6（SimRISC-02 有节 → FAIL）、check 7 四条（增/删行数≠1 或内容不含预期串 → FAIL）、check 8（docs/README 被改 → FAIL）、check 9（spec/ 有改动 → FAIL）。inject 轮 5 条（sha 不变→FAIL、注入后无 SimRISC-02→FAIL、谓词不 FAIL→FAIL、还原后 sha 不匹配→FAIL、还原后谓词不绿→FAIL）。
- **恒真断言**：无。每条 `report` 调用均由真实谓词返回值驱动 `rc`。
- **注入可还原**：inject 轮用 `cp` 备份 + `cp` 还原（非 `git checkout`），sha 前后一致。
- **结论**：脚本合格。

##### 3. 重跑记录

**默认模式**（`bash .work/evidence/SPEC-033t/run.sh`）：
```
checks=12 failures=0
RESULT: PASS
EXIT=0
```
12/12 PASS。

**inject 模式**（`bash .work/evidence/SPEC-033t/run.sh --inject`）：
```
checks=17 failures=0
RESULT: PASS
EXIT=0
```
17/17 PASS。注入→FAIL→还原→回绿全部通过。

##### 4. 独立注入反例

```
# 备份 sha = 345ff177b7373e173db2064c0c153035eef349d330fbfc6ec7c8dcdd8d8c550b
# 注入: sed 's/SimRISC-06/SimRISC-02/' contract-abi.md
# 验证注入生效: grep 'SimRISC-02' contract-abi.md → 命中 §2.3 行
# 重跑脚本:
  [FAIL] contract-abi.md no 'SimRISC-02' left    expected=0  actual=1   rc=1
  [FAIL] contract-abi.md diff is exactly 1 line added   expected=1  actual=0  rc=1
  [FAIL] contract-abi.md diff is exactly 1 line removed expected=1  actual=0  rc=1
  [FAIL] added line contains 'SimRISC-06 §函数调用'  expected=present  actual=absent  rc=1
  [FAIL] removed line contains 'SimRISC-02 §函数调用' expected=present  actual=absent  rc=1
  checks=12 failures=5
  RESULT: FAIL
  EXIT=1
```
✅ 注入后脚本正确报 FAIL（5 项失败，EXIT=1）。

```
# 还原: cp backup → contract-abi.md
# 还原后 sha = 345ff177b7373e173db2064c0c153035eef349d330fbfc6ec7c8dcdd8d8c550b ✓
# 重跑脚本:
  checks=12 failures=0
  RESULT: PASS
  EXIT=0
```
✅ 还原后回绿（12/12 PASS，EXIT=0）。`git diff --numstat` 仍为 `1	1	.tao/knowledge/contract-abi.md`，工作树未被污染。

##### 5. `make check` 独立重跑

```
lit: 31/31 PASS
INTEG: 80/80 PASS
validate_encoding: 227 条 OK
check-qemu-semantics: 149/149 PASS
repository checks: PASS
EXIT=0
```
✅ 全绿。

##### 6. 约束核验

| 约束 | 结果 |
|------|------|
| 只动 `contract-abi.md`（本任务可归属改动） | ✅ `git diff --numstat -- .tao/knowledge/contract-abi.md` = 1+/1− |
| 未触碰禁改区（spec/、contracts/、tests/） | ✅ `git diff --name-only -- spec/` = 空 |
| `docs/README.md` 未改 | ✅ 脚本 check 8 PASS |
| 并发改动非本任务所为 | ✅ NOTE 列出的外部文件（contract-isa.md、generate_isa_vectors.py、6 个 isa vectors、SPEC-030t）均属并发会话，非本任务修改 |

##### 判决

**Accepted**。

验收命令块在独立重跑下全部通过；约束无违反；证据脚本合格（FAIL 路径完备、无恒真断言、注入可还原）；独立注入反例验证通过（注入→FAIL→还原→回绿）。

#### 第 1 轮 architect 交叉复核（双模型互验）

**复核者**：architect subagent
**复核时间**：2026-10-04
**复核范围**：对照任务书目标/约束/验收，核验 reviewer 判决有无遗漏关键项、约束违反、过严/过松。临时目录 `/tmp/opencode/SPEC-033t-xcheck/`；仅临时注入后即时还原（sha 核对），未改写任何被提交内容。

##### 1. 独立重跑（真实输出）

证据脚本默认模式（`bash .work/evidence/SPEC-033t/run.sh`）：
```
checks=12 failures=0
RESULT: PASS
EXIT=0
```
证据脚本 `--inject`（`bash .work/evidence/SPEC-033t/run.sh --inject`）：
```
checks=17 failures=0
RESULT: PASS
EXIT=0
```
`make check` 独立重跑：`EXIT=0`（`lit 31/31 PASS`、`check-qemu-semantics 149/149 PASS`、`repository checks: PASS`；日志 `/tmp/opencode/SPEC-033t-xcheck/make_check.log`）。

`contract-abi.md`：`grep -c 'SimRISC-02'` = **0**；`git diff --numstat -- .tao/knowledge/contract-abi.md` = **`1	1`**（恰 1 增 1 删）。第 209 行现为 `| §2.3 | `call`/`ret` 与 RegRAS | `SimRISC-06 §函数调用`、`§函数返回`；`contract-isa.md §5.4–§5.6` |`。

##### 2. 独立注入一次反例（与 reviewer 各自独立）

```
sha_before = 345ff177b7373e173db2064c0c153035eef349d330fbfc6ec7c8dcdd8d8c550b
sed 注入（SimRISC-06 → SimRISC-02）后 grep -n 'SimRISC-02' → 命中 L209（注入生效）
重跑脚本：checks=12 failures=5   RESULT: FAIL   EXIT=1
  5 项 FAIL：残留计数=1、1 add=0、1 del=0、增行不含 'SimRISC-06 §函数调用'、删行不含 'SimRISC-02 §函数调用'
cp 还原后 sha_after = 345ff177b7373e173db2064c0c153035eef349d330fbfc6ec7c8dcdd8d8c550b（与 sha_before 一致）
还原后重跑：checks=12 failures=0   RESULT: PASS   EXIT=0；numstat 恢复 `1	1`
```
✅ 注入有效（sha 变化 + grep 命中）→ 脚本正确报 FAIL（5 项、EXIT=1）→ 还原后 sha 逐字节复原且回绿。

##### 3. 目标引用有效性

```
spec/SimRISC-06-控制流.md:   107:### 函数调用     130:### 函数返回
spec/SimRISC-02-寄存器复制.md: grep -cE '^### (函数调用|函数返回)' = 0（标题为「SimRISC寄存器复制指令」）
```

##### 4. 约束核验

- 本任务可归属改动**仅** `contract-abi.md`（1+/1−）；`docs/README.md` 未改；`git diff --name-only -- spec/` = 空。
- 工作树并发外部改动（`contract-isa.md`、`generate_isa_vectors.py`、6 个 `isa/*.yaml`、`SPEC-030t` 任务书）经 diff 内容核对，其 `spec_cite` 命中均为 `SimRISC-02 §条件赋值`/`§寄存器组之间块赋值`，与本任务的 `§函数调用`/`§函数返回` **语义无关**，确非本任务所为——与 engineer/reviewer 披露一致。
- `.work/` 被 `.gitignore:2` 忽略（`git check-ignore -v` 命中），证据脚本不入库。

##### 5. 补充发现（不影响本任务判决）

**F-x1（范围外的孪生陈旧引用，建议另立任务）**：`contracts/abi.yaml:46` 仍写
```
spec_cite: "SimRISC-02 §函数调用; SimRISC-02 §函数返回"
```
该文件头自述为「归一化合约：`.tao/knowledge/contract-abi.md`」的**机器可读形式**，故其 `call_ret.spec_cite` 正是本次所修 `contract-abi.md` §2.3 行的**同一语义孪生引用**，同属陈旧（`SimRISC-02` 现无此二节，应为 `SimRISC-06`）。
- 该文件**不在本任务验收标准 1/2 的范围内**（任务书头部「处置」明确「收窄为仅修 `contract-abi.md` 的 2 处」），故**不构成 reviewer 遗漏，不判 Needs Revision**；
- 但 `make check-spec-refs`（standalone）经查**只审计 `contract-*.md`**（`tools/infra/check_spec_refs.py`），不覆盖 `contracts/*.yaml`；且无任何工具引用 `contracts/abi.yaml`——该陈旧引用既不在 `ISS-086` 的 76 条内，也无门控拦截 → **当前无人覆盖**；
- 建议：由主会话评估后另立 follow-up（`contracts/abi.yaml:46` → `SimRISC-06 §函数调用; SimRISC-06 §函数返回`），或纳入 `SPEC-094t` 的覆盖范围。此项为**规划层新发现**，与 SPEC-033t 交付正确性无关。

**F-x2（轻微，不阻塞）**：`run.sh` 的 `--inject` 自检用 `mktemp` 备份（默认落 `/tmp`，而非 `/tmp/opencode/<任务ID>/`）；脚本结束 `rm -f` 已清理、无残留，仅与临时目录约定轻微不符。

##### 6. 判决

**确认 reviewer 的 Accepted 判决**。reviewer 的验收**无遗漏关键项、无约束违反、判决不过严亦不过松**：其文件核验、证据脚本审阅、默认/`--inject` 重跑、独立注入与还原、`make check` 各项结论在本次双模型复核下**逐项复现**。补充发现 F-x1（`contracts/abi.yaml:46` 孪生陈旧引用）属**任务范围外**的规划层新发现，需另立任务处置，**不影响 SPEC-033t 自身交付正确性**。
