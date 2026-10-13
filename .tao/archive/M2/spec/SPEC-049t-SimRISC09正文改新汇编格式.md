# SPEC-049t: SimRISC-09（16位数据运算）正文改为新汇编格式

**模块**：spec
**项目里程碑**：M2
**依赖**：`ADR-0013`、`assembly-language.md` v1.1、`tools/llvm/gen_asm_list.py`、内嵌速查表；前置 `SPEC-041t`…`048t`
**状态**：已验证

## 修改范围（仅 `spec/SimRISC-09-16位数据运算.md`）

### A. 块 57–84（26 条，**全部平铺**）

旧：`add.uw  rdhb, rdhc, rdhd` 之类；新：`add.uw  rdHB, rdHC, rdHD`。

- `orrr`（18 条）：`add/sub/cmp/mul/div/rem.{uw,sw}`、`and/or/xor/xnor.w`（注意 `or.w` 行 71 为 `orrr` 三寄存器形式）
- `orri`（8 条，移位/扩展；`immu6`=移位量/起始位，**不加组记法**）：`shl/shr.{uw,sw} rdHB, rdHC, immu6`、`ext.{uw,sw} rdHB, rdHC, immu6`
- 说明：`shl.uw/shr.uw/shr.sw/ext.uw/ext.sw` 各有 `orrr`（`rdHB, rdHC, rdHD`）与 `orri`（`rdHB, rdHC, immu6`）两行，**逐条查生成表**核对

### B. 块 95–97

`neg.w   rd1, rd2        ; rd1 = -rd2（低 16 位取负，符号扩展）` —— 伪指令/具体示例，**保持**。

### C. 正文散文引用

`rdhb`/`rdhc`/`rdhd` → `rdHB`/`rdHC`/`rdHD`；具体寄存器保持。

## 约束

- **只改 `spec/SimRISC-09-16位数据运算.md`**；不改生成器 / `contracts/` / `docs/`
- **不改生成区**（本文件行 6–40）
- **语义零变化**；逐条核对；命令缺失 → 停下报告

## 验收标准

1. A 段 26 条全部平铺；`orri` 移位/扩展**不加**组记法
2. B 段 `neg.w rd1, rd2` 未被误改
3. C 段引用大写；具体寄存器未误改
4. **语义零变化**（逐 hunk）
5. **不改生成区**（命中行号 > 40）
6. 26 条与生成表「汇编形式」列**逐条相符**（独立复算）
7. 反例验证：注入一处回退 → 检查可检出；复原后无残留
8. `make check` EXIT=0

## 完成区
**测试结果**：`make check` EXIT=0（真实输出 `/tmp/opencode/SPEC-049t-make-check.log`）
**修改文件**：`spec/SimRISC-09-16位数据运算.md`（仅此 1 文件，6 处正文残留修改）
**验收结果**：
- grep 零残留：`grep -n 'rdhd\|rdhb\|rdhc'` case-sensitive 扫描 → 零匹配
- 逐条对表：正文表格行 55（`add.uw rdHB,rdHC,rdHD`）、105（`cmp.uw`）、115（`mul.uw`）、132（`and.w`）、160（`ext.uw`）均与速查表汇编形式列一致
- 散文行 146：`rdhd` → `rdHD`（移位量说明），与上下文一致
- 未触生成区：`git diff` 所有改动行号 >40（生成区行 6–40 未触碰）
- `neg.w rd1, rd2`（行 96）保持不变（具体寄存器未误改）
- 语义零变化：仅大小写替换（`rdhd`→`rdHD`、`rdhb`→`rdHB`、`rdhc`→`rdHC`），汇编语义不变
- 反例验证：行 55 改回 `rdhd` 后 `grep -n 'rdhd'` 命中 1 行，复原后零命中 ✅

**新发现/坑**：上一次执行中断时代码块（行 57–84）已全部改完，仅剩正文表格/散文 6 处残留；中断恢复时必须先 `grep` 扫描确认残留范围再动手。
**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：本次 6 处正文残留修改（行 55, 105, 115, 132, 146, 160）+ 上次中断已落盘的代码块 57–84

**逐行审查**：

| 行 | 改动内容 | 判定 |
|---|---|---|
| 55 | `add.uw rdHB, rdHC, rdhd` → `rdHD` | ✅与速查表行14一致 |
| 105 | `cmp.uw rdHB, rdHC, rdhd` → `rdHD` | ✅与速查表行17一致 |
| 115 | `mul.uw rdHB, rdHC, rdhd` → `rdHD` | ✅与速查表行25一致 |
| 132 | `and.w rdHB, rdHC, rdhd` → `rdHD` | ✅与速查表行15一致 |
| 146 | 散文 `rdhd` → `rdHD`（移位量说明） | ✅上下文一致（orrr形式取rdHD低位） |
| 160 | `ext.uw rdHB, rdHC, rdhd` → `rdHD` | ✅与速查表行23一致 |

**边界/反例检查**：
- `neg.w rd1, rd2`（行96）：具体寄存器示例，未被误改 ✅
- 生成区（行6–40）：`git diff` 所有改动行号 >40 ✅
- `make check` EXIT=0 ✅
- grep 反例注入：行55改回 `rdhd` → `grep -n 'rdhd'` 命中1行；复原后零命中 ✅

**Finding 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 无 | — | — | — |

**判决**：全部通过，无遗留 finding。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（独立于 engineer，未采信两次完成区叙述，全部命令自跑）
**审查对象（工作区最终状态）**：`spec/SimRISC-09-16位数据运算.md` + 本任务文件（`git status --porcelain` 恰为这 2 个 `M`，无新增/未跟踪文件）

**审查脚本**（自写，置于 /tmp，不入库）：`/tmp/opencode/SPEC-049t/verify.py`（含 git diff 行号核验）、`/tmp/opencode/SPEC-049t/audit.py`（内容核验，可用于 /tmp 副本注入）。

##### 一、重跑记录（真实输出）

**1. 改动范围与生成区（`git diff -U0` + 脚本）**
```
$ git status --porcelain
 M ".tao/tasks/spec/SPEC-049t-SimRISC09正文改新汇编格式.md"
 M "spec/SimRISC-09-16位数据运算.md"

$ git diff -U0 -- spec/SimRISC-09-16位数据运算.md | grep '^@@'
@@ -51 +51 @@        @@ -55 +55 @@        @@ -58,26 +58,26 @@
@@ -92 +92 @@        @@ -101 +101 @@      @@ -105 +105 @@
@@ -111 +111 @@      @@ -115 +115 @@      @@ -132 +132 @@
@@ -140 +140 @@      @@ -146 +146 @@      @@ -160 +160 @@
```
判定：全部 hunk 起始行 ≥ 51 > 40；生成区行 6–40 逐字节未动（脚本比对 `HEAD:file` 与工作区行 6–40 → identical: True）。

**2. 零残留（重点项）**
```
$ grep -nE "\br[bdr]h[a-z]\b" spec/SimRISC-09-16位数据运算.md ; echo EXIT=$?
EXIT=1        # 无输出、无匹配
```
脚本计数 `lowercase rd?h[a-z]: 0`。全文 `rd?` 词元扫描（`grep -noE "rd[hH][a-z]"`）零命中；所有字段引用均为 `rdHB/rdHC/rdHD` 大写；具体寄存器 `rd0/rd1/rd2` 保留（行 96、107 等）。

**3. A 段 26 条 ↔ 生成表逐条（脚本 [4]）**
```
[4] generated rows: 26
    code lines: 26
    code_set == table_set: True
```
A 段代码块（行 57–84，26 行）与生成表「汇编形式」列构成的集合**完全相等**（26=26，无缺、无多、无错）；代码块无 `{}`/`...`/`|`，**全部平铺**；`orri` 立即数形式为 `rdHB, rdHC, immu6`（行 75/77/79/81/83），**未加组记法**。

**4. 表格行/散文（脚本 [9]）**
```
[9] line 55 exact: True    [9] line 92 exact: True    [9] line 105 exact: True
[9] line 115 exact: True   [9] line 132 exact: True   [9] line 140 exact: True
[9] line 160 exact: True   [9] line 146 prose ok: True
```
行 55/105/115/132/160（表格）与 146（散文）小写已改净、形式正确；行 160 两形式并存 `rdHB, rdHC, rdHD` 或 `rdHB, rdHC, immu6`，未误加组记法；行 92/140（`neg`/`not` 伪指令表，首次落盘部分）亦精确。

**5. B 段**
```
[7] line 96: 'neg.w   rd1, rd2        ; rd1 = -rd2（低 16 位取负，符号扩展）'
```
与任务书要求逐字一致，未被误改。

**6. 语义零变化（最强证据）**
```
[6] lower(old)==lower(new): True
```
`HEAD:file` 全文 `.lower()` 与工作区全文 `.lower()` **完全相同** ⇒ 全文件差异**仅有大小写**，位宽/数值/限制条文/注释逐字未动，`git diff` 无任何非大小写改动。

**7. 反例注入（在 /tmp 副本进行，未污染工作区）**
```
基准副本 base.md = 工作区当前文件
inj1: sed '55s/rdHB, rdHC, rdHD/rdHB, rdHC, rdhd/'   → 表格行还原小写
inj2: sed '160s/...immu6/...{immu6}/'                → orri 误加组记法
inj3: sed '58s/rdHB, rdHC, rdHD/rdhb, rdHC, rdHD/'   → 代码块还原小写
每个注入经 diff 确认非空（git/工作区无关文件不变）
```
结果（各自 `python3 audit.py <inj>.md base.md`）：
```
inj1 → RESULT: FAIL  EXIT=1   (line 55: lowercase 'rdhd'; line 55 != expected)
inj2 → RESULT: FAIL  EXIT=1   (line 160 brace introduced; semantic change; != expected)
inj3 → RESULT: FAIL  EXIT=1   (line 58: lowercase 'rdhb'; code_set != table_set)
```
反例可被检出、脚本能 FAIL；工作区 `git status` 注入前后一致（仅 2 个 `M`），**无污染**。

**8. `make check`（真实退出码，非管道）**
```
$ make check > /tmp/opencode/SPEC-049t/make-check-reviewer.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
...（尾部）
check-asm-list-consistency: 12 spec files OK
check_issues: 64 open, 10 closed (0 blocking M1-gate: 0)
repository checks: PASS
```
日志 `grep -niE "fail|error|traceback"` → 无。另外单跑 `make check-asm-list`：`EXIT=0`，`12 spec files OK`（内嵌表与 contract 一致，证明生成区未被改坏）。

##### 二、约束核验（逐条）

| # | 任务约束 / 验收点 | 结果 | 证据 |
|---|---|---|---|
| 1 | 只改 spec 文件（+任务文件） | ✅ | `git status` 仅 2 个 `M`；任务书正文仅状态/完成区/审阅记录变更，验收标准未弱化 |
| 2 | 未触生成区，`END`=40，命中行 >40 | ✅ | hunk 起始均 ≥51；行 6–40 与 HEAD 逐字节相同；END=40 |
| 3 | 全文零小写字段引用（重点） | ✅ | `grep -nE "\br[bdr]h[a-z]\b"` 空，EXIT=1；脚本计数 0 |
| 4 | A 段 26 条与生成表逐条相符、全平铺、orri 不加组记法 | ✅ | code_set==table_set=True；26=26；orri 均 `immu6` |
| 5 | 表格 55/105/115/132/160 + 散文 146 改净且形式正确 | ✅ | 逐行 exact=True |
| 6 | B 段 `neg.w rd1, rd2` 未被误改 | ✅ | 行 96 逐字一致 |
| 7 | 语义零变化（逐 hunk） | ✅ | 全文 lower() 全等 ⇒ 仅大小写差异 |
| 8 | 反例注入可检出 | ✅ | inj1/inj2/inj3 均 FAIL EXIT=1；注入在 /tmp，工作区无污染 |
| 9 | `make check` EXIT=0 | ✅ | 真实 `$?`=0；check-asm-list 12 files OK |

##### 三、观察（非阻断）

- 完成区「6 处正文残留修改」指**本次补完批次**（行 55/105/115/132/146/160），与实际一致；首次中断批次另含行 51/92/101/111/140 的大小写改动，二者合并即当前 `git diff`（单行 hunk 11 处 + 代码块 26 行）。表述无矛盾，仅需知悉总改动范围。
- 行 51/101/111 由 `rdhb`→`rdHB` 属任务书 C 段「正文散文引用」，未越界。

##### 四、判决

**Accepted** —— 9 项验收点在我方独立重跑下全部通过，无硬约束违反；语义零变化以「全文仅大小写差异」强证据成立；反例注入可被检出且未污染工作区。工程师达标，无 Needs Revision 项。
