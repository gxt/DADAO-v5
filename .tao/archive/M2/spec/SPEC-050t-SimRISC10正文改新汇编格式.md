# SPEC-050t: SimRISC-10（8位数据运算）正文改为新汇编格式

**模块**：spec
**项目里程碑**：M2
**依赖**：`ADR-0013`、`assembly-language.md` v1.1、`tools/llvm/gen_asm_list.py`、内嵌速查表；前置 `SPEC-041t`…`049t`
**状态**：已验证

## 修改范围（仅 `spec/SimRISC-10-8位数据运算.md`）

### A. 块 57–84（26 条，**全部平铺**）

旧：`add.ub  rdhb, rdhc, rdhd` 之类；新：`add.ub  rdHB, rdHC, rdHD`。

- `orrr`（18 条）：`add/sub/cmp/mul/div/rem.{ub,sb}`、`and/or/xor/xnor.b`
- `orri`（8 条，移位/扩展；`immu6`=移位量/起始位，**不加组记法**）：`shl/shr.{ub,sb} rdHB, rdHC, immu6`、`ext.{ub,sb} rdHB, rdHC, immu6`
- 说明：`shl.ub/shr.ub/shr.sb/ext.ub/ext.sb` 各有 `orrr`（`rdHB, rdHC, rdHD`）与 `orri`（`rdHB, rdHC, immu6`）两行，**逐条查生成表**核对

### B. 块 95–97

`neg.b   rd1, rd2        ; rd1 = -rd2（低 8 位取负，符号扩展）` —— 伪指令/具体示例，**保持**。

### C. 正文散文引用

`rdhb`/`rdhc`/`rdhd` → `rdHB`/`rdHC`/`rdHD`；具体寄存器保持。

## 约束

- **只改 `spec/SimRISC-10-8位数据运算.md`**；不改生成器 / `contracts/` / `docs/`
- **不改生成区**（本文件行 6–40）
- **语义零变化**；逐条核对；命令缺失 → 停下报告

## 验收标准

1. A 段 26 条全部平铺；`orri` 移位/扩展**不加**组记法
2. B 段 `neg.b rd1, rd2` 未被误改
3. C 段引用大写；具体寄存器未误改
4. **语义零变化**（逐 hunk）
5. **不改生成区**（命中行号 > 40）
6. 26 条与生成表「汇编形式」列**逐条相符**（独立复算）
7. 反例验证：注入一处回退 → 检查可检出；复原后无残留
8. `make check` EXIT=0

## 完成区
**测试结果**：`make check` EXIT=0
**修改文件**：`spec/SimRISC-10-8位数据运算.md`（仅此一文件）
**验收结果**：

### 逐条对表（26 条 vs 生成表「汇编形式」列）

| # | 助记符 | format | 生成表汇编形式 | 正文代码块 | 匹配 |
|---|--------|--------|---------------|-----------|------|
| 1 | add.sb | orrr | `add.sb rdHB, rdHC, rdHD` | `add.sb rdHB, rdHC, rdHD` | ✓ |
| 2 | add.ub | orrr | `add.ub rdHB, rdHC, rdHD` | `add.ub rdHB, rdHC, rdHD` | ✓ |
| 3 | sub.ub | orrr | `sub.ub rdHB, rdHC, rdHD` | `sub.ub rdHB, rdHC, rdHD` | ✓ |
| 4 | sub.sb | orrr | `sub.sb rdHB, rdHC, rdHD` | `sub.sb rdHB, rdHC, rdHD` | ✓ |
| 5 | cmp.ub | orrr | `cmp.ub rdHB, rdHC, rdHD` | `cmp.ub rdHB, rdHC, rdHD` | ✓ |
| 6 | cmp.sb | orrr | `cmp.sb rdHB, rdHC, rdHD` | `cmp.sb rdHB, rdHC, rdHD` | ✓ |
| 7 | mul.ub | orrr | `mul.ub rdHB, rdHC, rdHD` | `mul.ub rdHB, rdHC, rdHD` | ✓ |
| 8 | mul.sb | orrr | `mul.sb rdHB, rdHC, rdHD` | `mul.sb rdHB, rdHC, rdHD` | ✓ |
| 9 | div.ub | orrr | `div.ub rdHB, rdHC, rdHD` | `div.ub rdHB, rdHC, rdHD` | ✓ |
| 10 | div.sb | orrr | `div.sb rdHB, rdHC, rdHD` | `div.sb rdHB, rdHC, rdHD` | ✓ |
| 11 | rem.ub | orrr | `rem.ub rdHB, rdHC, rdHD` | `rem.ub rdHB, rdHC, rdHD` | ✓ |
| 12 | rem.sb | orrr | `rem.sb rdHB, rdHC, rdHD` | `rem.sb rdHB, rdHC, rdHD` | ✓ |
| 13 | and.b | orrr | `and.b rdHB, rdHC, rdHD` | `and.b rdHB, rdHC, rdHD` | ✓ |
| 14 | or.b | orrr | `or.b rdHB, rdHC, rdHD` | `or.b rdHB, rdHC, rdHD` | ✓ |
| 15 | xor.b | orrr | `xor.b rdHB, rdHC, rdHD` | `xor.b rdHB, rdHC, rdHD` | ✓ |
| 16 | xnor.b | orrr | `xnor.b rdHB, rdHC, rdHD` | `xnor.b rdHB, rdHC, rdHD` | ✓ |
| 17 | shl.ub | orri | `shl.ub rdHB, rdHC, immu6` | `shl.ub rdHB, rdHC, immu6` | ✓ |
| 18 | shl.ub | orrr | `shl.ub rdHB, rdHC, rdHD` | `shl.ub rdHB, rdHC, rdHD` | ✓ |
| 19 | shr.ub | orri | `shr.ub rdHB, rdHC, immu6` | `shr.ub rdHB, rdHC, immu6` | ✓ |
| 20 | shr.ub | orrr | `shr.ub rdHB, rdHC, rdHD` | `shr.ub rdHB, rdHC, rdHD` | ✓ |
| 21 | shr.sb | orri | `shr.sb rdHB, rdHC, immu6` | `shr.sb rdHB, rdHC, immu6` | ✓ |
| 22 | shr.sb | orrr | `shr.sb rdHB, rdHC, rdHD` | `shr.sb rdHB, rdHC, rdHD` | ✓ |
| 23 | ext.ub | orri | `ext.ub rdHB, rdHC, immu6` | `ext.ub rdHB, rdHC, immu6` | ✓ |
| 24 | ext.ub | orrr | `ext.ub rdHB, rdHC, rdHD` | `ext.ub rdHB, rdHC, rdHD` | ✓ |
| 25 | ext.sb | orri | `ext.sb rdHB, rdHC, immu6` | `ext.sb rdHB, rdHC, immu6` | ✓ |
| 26 | ext.sb | orrr | `ext.sb rdHB, rdHC, rdHD` | `ext.sb rdHB, rdHC, rdHD` | ✓ |

### Grep 零残留证据
```
$ grep -nE "\br[bdr]h[a-z]\b" spec/SimRISC-10-8位数据运算.md
(no output, EXIT=1)
```
所有 `rdhb`/`rdhc`/`rdhd` 已改为 `rdHB`/`rdHC`/`rdHD`，无残留。

### 未触生成区证据
生成区为行 6–40（`<!-- ASSEMBLY_LIST_START -->` 到 `<!-- ASSEMBLY_LIST_END -->`）。所有改动均在行 41+。

### 语义零变化
- 所有改动仅为大小写变换（`rdhb`→`rdHB` 等），不涉及指令助记符、操作数格式、位宽描述、异常规则等语义内容。
- 具体寄存器（`rd0`/`rd1`/`rd2`/`rd3`）全部保持原样未动。

### 反例注入+复原
1. 注入：`sed -i '58s/rdHB/rdhb/; 58s/rdHC/rdhc/; 58s/rdHD/rdhd/'` → grep 检出 `58:add.ub  rdhb, rdhc, rdhd`（反例有效）
2. 复原：`sed -i '58s/rdhb/rdHB/; 58s/rdhc/rdHC/; 58s/rdhd/rdHD/'` → grep 无匹配（EXIT=1），已还原

### 散文/表格行逐条检查
| 行号 | 原文 | 改后 | 寄存器保护 |
|------|------|------|-----------|
| 51 | `rdhb` 不能为 `rd0` | `rdHB` 不能为 `rd0` | rd0 ✓ |
| 55 | `add.ub rdhb, rdhc, rdhd` | `add.ub rdHB, rdHC, rdHD` | — |
| 92 | `neg.b rdhb, rdhc` / `sub.sb rdhb, rd0, rdhc` | `neg.b rdHB, rdHC` / `sub.sb rdHB, rd0, rdHC` | rd0 ✓ |
| 96 | `neg.b   rd1, rd2` | 未改 | rd1,rd2 ✓ |
| 101 | `rdhb` 不能为 `rd0` | `rdHB` 不能为 `rd0` | rd0 ✓ |
| 105 | `cmp.ub rdhb, rdhc, rdhd` | `cmp.ub rdHB, rdHC, rdHD` | — |
| 107 | `cmp.sb rd1, rd2, rd3` | 未改 | rd1,rd2,rd3 ✓ |
| 111 | `rdhb` 不能为 `rd0` | `rdHB` 不能为 `rd0` | rd0 ✓ |
| 115 | `mul.ub rdhb, rdhc, rdhd` | `mul.ub rdHB, rdHC, rdHD` | — |
| 132 | `and.b rdhb, rdhc, rdhd` | `and.b rdHB, rdHC, rdHD` | — |
| 140 | `not.b rdhb, rdhc` / `xnor.b rdhb, rdhc, rd0` | `not.b rdHB, rdHC` / `xnor.b rdHB, rdHC, rd0` | rd0 ✓ |
| 146 | `rdhd` 的低位 | `rdHD` 的低位 | — |
| 160 | `ext.ub rdhb, rdhc, rdhd` / `ext.ub rdhb, rdhc, immu6` | `ext.ub rdHB, rdHC, rdHD` / `ext.ub rdHB, rdHC, immu6` | — |

### `make check` 真实退出码
```
$ make check > /tmp/opencode/SPEC-050t-make-check.log 2>&1; echo "EXIT=$?"
EXIT=0
```

**新发现/坑**：无特殊情况。此任务为纯格式替换，对照 SimRISC-09（SPEC-049t）模式执行。
**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审阅范围**：`spec/SimRISC-10-8位数据运算.md` 全文 162 行，重点审查行 41+（非生成区）。

**逐行审查结论**：

1. **代码块（行 57–84）**：26 条全部从 `rdhb/rdhc/rdhd` 改为 `rdHB/rdHC/rdHD`，`immu6` 保持不变。与生成表（行 6–40）逐条对齐，无遗漏。✅
2. **伪指令表格**：`neg.b`（行 92）和 `not.b`（行 140）的字段名均已大写，展开形式中的 `rd0` 保持不变。✅
3. **具体寄存器示例**：行 96 `neg.b rd1, rd2`、行 107 `cmp.sb rd1, rd2, rd3` 均未动。✅
4. **散文引用**：行 51/101/111 的 `rdHB` 不能为 `rd0`、行 146 的 `rdHD` 的低位，均已大写。✅
5. **生成区（行 6–40）**：未触碰，`head -40` 确认无变化。✅
6. **grep 零残留**：`grep -nE "\br[bdr]h[a-z]\b"` 返回 EXIT=1（无匹配）。✅
7. **反例注入+复原**：注入后 grep 检出 1 条（行 58），复原后 grep 无匹配。✅
8. **`make check`**：EXIT=0。✅

**Finding 处置表**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 无 | — | — | — |

**判决**：所有检查项通过，无遗留 finding。可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查范围**：`spec/SimRISC-10-8位数据运算.md`（161 行）+ 任务文件；所有核验命令均独立重跑，未采信完成区转述。脚本置于 `/tmp/opencode/SPEC-050t/`（不入库）。

**重跑记录（我自己的真实输出/退出码）**

1. 改动范围（约束 1）：
   ```
   $ git status --short
    M .tao/tasks/spec/SPEC-050t-SimRISC10正文改新汇编格式.md
    M spec/SimRISC-10-8位数据运算.md
   ```
   仅这两个文件。✅

2. 未触生成区（约束 2）：
   ```
   $ grep -n "ASSEMBLY_LIST_START\|ASSEMBLY_LIST_END" spec/SimRISC-10-8位数据运算.md
   6:<!-- ASSEMBLY_LIST_START -->
   40:<!-- ASSEMBLY_LIST_END -->
   $ git diff -U0 -- spec/SimRISC-10-8位数据运算.md | grep -E "^@@"
   @@ -51 +51 @@ ...   @@ -55 +55 @@ ...   @@ -58,26 +58,26 @@ ...
   @@ -92 +92 @@ ...    @@ -101 +101 @@ ...  @@ -105 +105 @@ ...
   @@ -111 +111 @@ ...  @@ -115 +115 @@ ...  @@ -132 +132 @@ ...
   @@ -140 +140 @@ ...  @@ -146 +146 @@ ...  @@ -160 +160 @@ ...
   $ diff <(sed -n '1,40p' HEAD版本) <(sed -n '1,40p' 工作区)   # 逐字节
   （无输出）GEN_DIFF_EXIT=0
   ```
   全部命中行号 ≥51 > 40；生成区行 6–40 逐字节未变。✅

3. 零残留（约束 3，重点）：
   ```
   $ grep -nE "\br[bdr]h[a-z]\b" spec/SimRISC-10-8位数据运算.md
   （无输出）grep_EXIT=1
   $ grep -nE "rdh[a-zA-Z]" spec/SimRISC-10-8位数据运算.md | grep -E "rdh[a-z]"
   （无输出）EXIT=1
   ```
   无任何小写 `rdhb/rdhc/rdhd` 残留；`rd0/rd1/rd2/rd3` 未被波及。✅

4. A 段 26 条 vs 生成表（约束/验收 4、6）——自写 `check_file.py` 独立解析生成表（行 6–40，26 行）与 A 段代码块（行 58–83，26 行），逐条比对助记符+format+汇编形式：
   ```
   [CHECK2] START=6 END=40
   [CHECK4] A-section code lines = 26
     [ok] 58: add.ub rdHB, rdHC, rdHD
     ...（26 条逐条 ok）...
     [ok] 83: ext.sb rdHB, rdHC, immu6
     [ok] 26/26 exact 1:1 match
   [CHECK4] RESULT: PASS   SCRIPT_EXIT=0
   ```
   26/26 精确 1:1；`shl.ub/shr.ub/shr.sb/ext.ub/ext.sb` 的 `orri`（`immu6`）与 `orrr`（`rdHD`）两行均正确区分，`orri` 无组记法（无 `{}`）。✅

5. 表格行/散文引用（验收 5）——`sed -n` 逐行核对 55/92/101/105/111/115/132/140/146/160：
   - 行 92 `| \`neg.b rdHB, rdHC\` | \`sub.sb rdHB, rd0, rdHC\` | ...`：展开为 `orrr` **平铺**三操作数，`rd0` 保留。✅
   - 行 140 `| \`not.b rdHB, rdHC\` | \`xnor.b rdHB, rdHC, rd0\` | ...`：`xnor.b` **平铺**，`rd0` 保留。✅
   - 行 55/105/115/132/160 表格、行 101/111/146 散文引用均已大写且无小写残留。✅

6. B 段（验收 2）：
   ```
   $ diff <(sed -n '96p' HEAD) <(sed -n '96p' 工作区)   # 行 96 neg.b   rd1, rd2
   （无输出）LINE96_EXIT=0
   ```
   `neg.b   rd1, rd2` 未被误改。✅

7. 语义零变化（验收 4，强判据）：
   ```
   $ tr 'A-Z' 'a-z' < HEAD版本 > head.lower;  tr 'A-Z' 'a-z' < 工作区 > work.lower
   $ diff head.lower work.lower
   （无输出）LOWERCASE_DIFF_EXIT=0
   $ md5sum head.lower work.lower
   f1451e152ecf98bec6296bf9f563830c  head.lower
   f1451e152ecf98bec6296bf9f563830c  work.lower
   ```
   忽略大小写后与 HEAD **逐字节相同** ⇒ 差异仅有大小写，语义零变化。✅

8. 反例注入（验收 7，在 `/tmp/opencode/SPEC-050t/` 副本进行，未污染工作区）——4 种注入全部被我的脚本报 FAIL：
   ```
   inj1 行55 表格行还原 rdhd           → RESULT: FAIL (residue base line55)   EXIT=1
   inj2 行81 ext.ub immu6 误加组记法   → RESULT: FAIL (group notation line81 + 26比对不符) EXIT=1
   inj3 行92 sub.sb 写成双目的         → RESULT: FAIL (neg.b expansion not flat + 2-operand) EXIT=1
   inj4 行83 ext.sb orri 误改 rdHD     → RESULT: FAIL (coverage mismatch ext.sb/orri) EXIT=1
   ```
   同时 `` `check_file.py 原文件` `` → `RESULT: PASS`（EXIT=0），证明脚本可失败、非恒真。✅

9. `make check` 真实退出码（验收 8）：
   ```
   $ timeout 600 make check > /tmp/opencode/SPEC-050t/make-check.log 2>&1; rc=$?; echo "EXIT=$rc"
   EXIT=0
   $ tail -3 make-check.log
   check-asm-list-consistency: 12 spec files OK
   check_issues: 64 open, 10 closed (0 blocking M1-gate: 0)
   repository checks: PASS
   ```
   ✅

**约束逐条核验**

| # | 约束 | 结论 |
|---|------|------|
| 1 | 只改 `spec/SimRISC-10-…md`（+任务文件） | ✅ 仅 2 文件 |
| 2 | 未触生成区（END=40，命中行 >40） | ✅ 全部 ≥51；行 6–40 逐字节未变 |
| 3 | 零残留（`rdhb/rdhc/rdhd`，`rd0/1/2` 除外） | ✅ grep EXIT=1 |
| 4 | A 段 26 条与生成表逐条相符，`immu6` 不加组记法 | ✅ 26/26 精确匹配 |
| 5 | 表格行 55/92/101/105/111/115/132/140/146/160 改净且形式正确 | ✅ 92/140 展开均平铺 |
| 6 | B 段 `neg.b rd1, rd2` 未被误改 | ✅ 行 96 逐字节未变 |
| 7 | 语义零变化 | ✅ lower(HEAD)==lower(工作区) |
| 8 | 反例可检出、复原无残留 | ✅ 4 种注入均 FAIL；工作区无污染 |
| 9 | `make check` EXIT=0 | ✅ EXIT=0 |

**判决**：Accepted。验收命令块在我的独立重跑下全部通过，硬约束无违反，反例注入可被检出且工作区未被污染（`git status` 仅 2 个受审文件）。此项为「工程师达标」证据，最终接受仍由架构师终审。
