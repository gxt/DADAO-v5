# SPEC-044t: SimRISC-04（64位数据运算）正文改为新汇编格式

**模块**：spec
**项目里程碑**：M2
**依赖**：`ADR-0013`、`docs/spec/assembly-language.md` v1.1、`tools/llvm/gen_asm_list.py`、内嵌速查表（生成区）；前置 `SPEC-041t`/`042t`/`043t`
**状态**：已验证

## 修改范围（仅 `spec/SimRISC-04-64位数据运算.md`）

### A. 代码块

| 位置 | 旧 | 新（以生成表为准） |
|---|---|---|
| 61 | `add.uo  rdha, rdhb, rdhc, rdhd` | `add.uo  {rdHA, rdHB}, rdHC, rdHD` |
| 62 | `add.so  rdha, rdhb, rdhc, rdhd` | `add.so  {rdHA, rdHB}, rdHC, rdHD` |
| 63 | `sub.uo  rdha, rdhb, rdhc, rdhd` | `sub.uo  {rdHA, rdHB}, rdHC, rdHD` |
| 64 | `sub.so  rdha, rdhb, rdhc, rdhd` | `sub.so  {rdHA, rdHB}, rdHC, rdHD` |
| 77 | `add.si  rdha, imms18` | `add.si  rdHA, imms18` |
| 92 | `cmp.si  rdha, rdhb, imms12` | `cmp.si  rdHA, rdHB, imms12` |
| 93 | `cmp.ui  rdha, rdhb, immu12` | `cmp.ui  rdHA, rdHB, immu12` |
| 99 | `cmp.uo  rdhb, rdhc, rdhd` | `cmp.uo  rdHB, rdHC, rdHD` |
| 100 | `cmp.so  rdhb, rdhc, rdhd` | `cmp.so  rdHB, rdHC, rdHD` |
| 112 | `mul.so  rdha, rdhb, rdhc, rdhd` | `mul.so  {rdHA, rdHB}, rdHC, rdHD` |
| 113 | `mul.uo  rdha, rdhb, rdhc, rdhd` | `mul.uo  {rdHA, rdHB}, rdHC, rdHD` |
| 121 | `div.uo  rdhb, rdhc, rdhd` | `div.uo  rdHB, rdHC, rdHD` |
| 122 | `div.so  rdhb, rdhc, rdhd` | `div.so  rdHB, rdHC, rdHD` |
| 123 | `rem.uo  rdhb, rdhc, rdhd` | `rem.uo  rdHB, rdHC, rdHD` |
| 124 | `rem.so  rdhb, rdhc, rdhd` | `rem.so  rdHB, rdHC, rdHD` |
| 216–221 | `shl.uo/shr.uo/shr.so rdhb, rdhc, rdhd` / `..., immu6` | `... rdHB, rdHC, rdHD` / `... rdHB, rdHC, immu6`（`orri` **不是**组记法：`immu6`=移位量） |
| 223–226 | `ext.uo/ext.so rdhb, rdhc, rdhd` / `..., immu6` | `... rdHB, rdHC, rdHD` / `... rdHB, rdHC, immu6` |
| 228–231 | `and.o/or.o/xor.o/xnor.o rdhb, rdhc, rdhd` | `... rdHB, rdHC, rdHD` |

> **注意**：`add.uo`/`add.so`/`sub.uo`/`sub.so`/`mul.uo`/`mul.so` 是**双目的**（`rdha`、`rdhb` 均为 dst）→ `{rdHA, rdHB}, rdHC, rdHD`（无 `?`）。其余 `orrr` 三操作数**不加**花括号。

### B. 普通 Markdown 表格中的指令书写

| 位置 | 旧 | 新 |
|---|---|---|
| 144 | `and.o rdhb, rdhc, rdhd` | `and.o rdHB, rdHC, rdHD` |
| 159 | `xnor.o rdhb, rdhc, rd0` | `xnor.o rdHB, rdHC, rd0` |
| 169 | `sub.so rd0, rdhb, rd0, rdhc` | `sub.so {rd0, rdHB}, rd0, rdHC`（双目的）**逐条核对生成表** |
| 211 | `ext.uo rdhb, rdhc, rdhd` 或 `ext.uo rdhb, rdhc, immu6` | `ext.uo rdHB, rdHC, rdHD` / `ext.uo rdHB, rdHC, immu6` |

### C. 正文散文与伪代码中的字段名引用

`rdha`/`rdhb`/`rdhc`/`rdhd` → `rdHA`/`rdHB`/`rdHC`/`rdHD`（含行 51–52、67、103、109、116、127、140–151、182、199、207 等；**伪代码块**行 185–188、202–205 中的 `rdhb[N:0]`→`rdHB[N:0]`、`rdhc[N:0]`→`rdHC[N:0]` 同步）。

- 具体寄存器（`rd0`、`rd3`、`rd4`）**保持**。
- 行 173 `neg.o rd3, rd4` 为具体示例，**保持**（`neg.o` 为伪指令，调用写法不改）。

## 约束

- **只改 `spec/SimRISC-04-64位数据运算.md`**；不改生成器 / `contracts/` / `docs/`
- **不改生成区**（`<!-- ASSEMBLY_LIST_START/END -->`，本文件行 6–43）
- **语义零变化**：数值/位宽/公式/限制条文一字不动（只改记法与大小写）
- 逐条核对；命令缺失 → 停下报告，禁止自行安装

## 验收标准

1. A 段 17 条代码块行全部为新格式（双目的 `{…, …},`、`orri` 移位量不加花括号）
2. B 段 4 处表格指令书写转换正确（尤其行 169 的双目的形式）
3. C 段引用一致大写；具体寄存器未误改
4. **语义零变化**（逐 hunk；公式/数值逐字未动）
5. **不改生成区**（证据：命中行号 > 43）
6. 每条新形式与生成表「汇编形式」列**逐条相符**（独立复算；双目的/`orri` 分类正确）
7. 反例验证：注入一处回退（如双目的去掉 `{}`、或 `orri` 移位量误加组记法）→ 检查可检出；复原后无残留
8. `make check` EXIT=0

## 完成区
**测试结果**：`make check` EXIT=0；全文 grep `rdha|rdhb|rdhc|rdhd` 0 匹配
**修改文件**：`spec/SimRISC-04-64位数据运算.md`（唯一改动文件，`git diff --name-only` 确认）
**验收结果**：

### A 段 17 条代码块逐条对照生成表

| 行 | 正文新格式 | 生成表行 | 生成表「汇编形式」 | 一致 |
|---|---|---|---|---|
| 61 | `add.uo {rdHA, rdHB}, rdHC, rdHD` | 15 | `add.uo {rdHA, rdHB}, rdHC, rdHD` | ✓ |
| 62 | `add.so {rdHA, rdHB}, rdHC, rdHD` | 14 | `add.so {rdHA, rdHB}, rdHC, rdHD` | ✓ |
| 63 | `sub.uo {rdHA, rdHB}, rdHC, rdHD` | 39 | `sub.uo {rdHA, rdHB}, rdHC, rdHD` | ✓ |
| 64 | `sub.so {rdHA, rdHB}, rdHC, rdHD` | 38 | `sub.so {rdHA, rdHB}, rdHC, rdHD` | ✓ |
| 77 | `add.si rdHA, imms18` | 13 | `add.si rdHA, imms18` | ✓ |
| 92 | `cmp.si rdHA, rdHB, imms12` | 17 | `cmp.si rdHA, rdHB, imms12` | ✓ |
| 93 | `cmp.ui rdHA, rdHB, immu12` | 19 | `cmp.ui rdHA, rdHB, immu12` | ✓ |
| 99 | `cmp.uo rdHB, rdHC, rdHD` | 20 | `cmp.uo rdHB, rdHC, rdHD` | ✓ |
| 100 | `cmp.so rdHB, rdHC, rdHD` | 18 | `cmp.so rdHB, rdHC, rdHD` | ✓ |
| 112 | `mul.so {rdHA, rdHB}, rdHC, rdHD` | 27 | `mul.so {rdHA, rdHB}, rdHC, rdHD` | ✓ |
| 113 | `mul.uo {rdHA, rdHB}, rdHC, rdHD` | 28 | `mul.uo {rdHA, rdHB}, rdHC, rdHD` | ✓ |
| 121 | `div.uo rdHB, rdHC, rdHD` | 22 | `div.uo rdHB, rdHC, rdHD` | ✓ |
| 122 | `div.so rdHB, rdHC, rdHD` | 21 | `div.so rdHB, rdHC, rdHD` | ✓ |
| 123 | `rem.uo rdHB, rdHC, rdHD` | 31 | `rem.uo rdHB, rdHC, rdHD` | ✓ |
| 124 | `rem.so rdHB, rdHC, rdHD` | 30 | `rem.so rdHB, rdHC, rdHD` | ✓ |
| 216 | `shl.uo rdHB, rdHC, rdHD` | 33 | `shl.uo rdHB, rdHC, rdHD` | ✓ |
| 217 | `shl.uo rdHB, rdHC, immu6` | 32 | `shl.uo rdHB, rdHC, immu6` | ✓ |
| 218 | `shr.uo rdHB, rdHC, rdHD` | 37 | `shr.uo rdHB, rdHC, rdHD` | ✓ |
| 219 | `shr.uo rdHB, rdHC, immu6` | 36 | `shr.uo rdHB, rdHC, immu6` | ✓ |
| 220 | `shr.so rdHB, rdHC, rdHD` | 35 | `shr.so rdHB, rdHC, rdHD` | ✓ |
| 221 | `shr.so rdHB, rdHC, immu6` | 34 | `shr.so rdHB, rdHC, immu6` | ✓ |
| 223 | `ext.uo rdHB, rdHC, rdHD` | 26 | `ext.uo rdHB, rdHC, rdHD` | ✓ |
| 224 | `ext.uo rdHB, rdHC, immu6` | 25 | `ext.uo rdHB, rdHC, immu6` | ✓ |
| 225 | `ext.so rdHB, rdHC, rdHD` | 24 | `ext.so rdHB, rdHC, rdHD` | ✓ |
| 226 | `ext.so rdHB, rdHC, immu6` | 23 | `ext.so rdHB, rdHC, immu6` | ✓ |
| 228 | `and.o rdHB, rdHC, rdHD` | 16 | `and.o rdHB, rdHC, rdHD` | ✓ |
| 229 | `or.o rdHB, rdHC, rdHD` | 29 | `or.o rdHB, rdHC, rdHD` | ✓ |
| 230 | `xor.o rdHB, rdHC, rdHD` | 41 | `xor.o rdHB, rdHC, rdHD` | ✓ |
| 231 | `xnor.o rdHB, rdHC, rdHD` | 40 | `xnor.o rdHB, rdHC, rdHD` | ✓ |

### B 段 4 处表格转换

| 行 | 旧 | 新 | 与生成表一致 |
|---|---|---|---|
| 144 | `and.o rdhb, rdhc, rdhd` | `and.o rdHB, rdHC, rdHD` | ✓（生成表行 16） |
| 159 | `xnor.o rdhb, rdhc, rd0` | `xnor.o rdHB, rdHC, rd0` | ✓（`rd0` 为具体寄存器，保持小写） |
| 169 | `sub.so rd0, rdhb, rd0, rdhc` | `sub.so {rd0, rdHB}, rd0, rdHC` | ✓（双目的，`rd0` 保持小写，生成表行 38） |
| 211 | `ext.uo rdhb, rdhc, rdhd` | `ext.uo rdHB, rdHC, rdHD` / `ext.uo rdHB, rdHC, immu6` | ✓（生成表行 25-26） |

### C 段引用一致性

- 行 51-52: `rdHC`/`rdHD`/`rdHA`/`rdHB` ✓
- 行 57: `rdHA` ✓
- 行 67: `rdHA`/`rdHB` ✓
- 行 103: `rdHB` ✓
- 行 109: `rdHC`/`rdHD`/`rdHA`/`rdHB` ✓
- 行 116: `rdHA`/`rdHB` ✓
- 行 127: `rdHB` ✓
- 行 140-151: `rdHC`/`rdHD`（行 151 散文中 `rdhc`→`rdHC`、`rdhd`→`rdHD`） ✓
- 行 182: `rdHD` ✓
- 行 185-188: `rdHB[N:0]`/`rdHC[N:0]`/`rdHB[63:N+1]` ✓
- 行 199: 散文无 rdha-字段名，无变化
- 行 202-204: `rdHB[hd:0]`/`rdHC[hd:0]`/`rdHB[N:hd+1]`/`rdHB[63:N+1]` ✓
- 行 207: 无 rdha-字段名，无变化
- 具体寄存器 `rd0`（行 67, 116, 127, 159, 169）、`rd3`/`rd4`（行 173）均保持小写 ✓

### 生成区未触碰证据

`git diff` 所有 hunk 起始行号：`@@ -48,`、`@@ -74,`、`@@ -89,`、`@@ -141,`、`@@ -156,`、`@@ -166,`、`@@ -179,`、`@@ -199,`——**全部 > 43**（ASSEMBLY_LIST_END 在行 43） ✓

### 语义零变化证据

所有改动仅将 `rdha`/`rdhb`/`rdhc`/`rdhd` 改为 `rdHA`/`rdHB`/`rdHC`/`rdHD`（含花括号组记法），公式（如 `rdHB[N:0] = (rdHC[N:0] << shamt)`）、数值（如 `63`、`0-63`）、限制条文（如「不能**同时**为 `rd0`」）、注释内容（如 `; ZX，rdHA = 进位`）逐字未动 ✓

### 反例注入验证

- **注入**：将行 61 `add.uo {rdHA, rdHB}, rdHC, rdHD` 回退为 `add.uo rdHA, rdHB, rdHC, rdHD`（去掉双目的花括号）
- **可检出**：注入后该行与生成表行 15 `add.uo {rdHA, rdHB}, rdHC, rdHD` 不一致，逐条比对脚本可检出
- **还原**：`git diff --name-only` 确认改动文件非空（注入生效），还原后全文 `grep 'rdHA, rdHB, rdHC, rdHD'` 无匹配（无花括号的旧形式已消失）
- **还原后 `make check`**：EXIT=0 ✓

### `make check` 真实退出码

```
$ cd /home/ubuntu/DADAO-v5 && make check > /tmp/opencode/SPEC-044t/make-check-final.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
```

**新发现/坑**：无
**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`spec/SimRISC-04-64位数据运算.md` 全部改动（A 段 17 条代码块、B 段 4 处表格、C 段散文/伪代码）

**逐条 finding**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | 双目的 6 条（add.uo/add.so/sub.uo/sub.so/mul.uo/mul.so）均正确添加 `{rdHA, rdHB},` 花括号，无 `?` | ✅已修 | — | 生成表行 14-15, 27-28, 38-39 逐条一致 |
| 2 | orrr 三操作数（cmp.uo/cmp.so/div.uo/div.so/rem.uo/rem.so/and.o/or.o/xor.o/xnor.o）均正确改为 `rdHB, rdHC, rdHD`，无花括号 | ✅已修 | — | 生成表行 16, 18, 20-22, 29-31, 40-41 逐条一致 |
| 3 | orri 移位/扩展（shl.uo/shr.uo/shr.so/ext.uo/ext.so 的立即数形式）正确改为 `rdHB, rdHC, immu6`，`immu6` 非组记法 | ✅已修 | — | 生成表行 23, 25, 32, 34, 36 逐条一致 |
| 4 | riii（add.si）正确改为 `rdHA, imms18` | ✅已修 | — | 生成表行 13 一致 |
| 5 | rrii（cmp.si/cmp.ui）正确改为 `rdHA, rdHB, imms12/immu12` | ✅已修 | — | 生成表行 17, 19 一致 |
| 6 | 行 169 neg.o 展开 `sub.so {rd0, rdHB}, rd0, rdHC` 双目的形式正确，`rd0` 保持小写 | ✅已修 | — | 生成表行 38 `sub.so {rdHA, rdHB}, rdHC, rdHD` 模式一致 |
| 7 | 具体寄存器 `rd0`/`rd3`/`rd4` 均保持小写，未误改 | ✅已修 | — | 行 67, 116, 127, 159, 169, 173 逐行确认 |
| 8 | 行 173 `neg.o rd3, rd4` 示例保持不变 | ✅已修 | — | 逐字确认 |
| 9 | ASSEMBLY_LIST 区（行 6-43）未触碰 | ✅已修 | — | `git diff` 所有 hunk 起始行 > 43 |
| 10 | 语义零变化：公式/数值/限制条文逐字未动 | ✅已修 | — | 逐 hunk 对照，仅大小写/花括号变化 |

**判决**：全部 finding 已修（✅已修），无遗留。状态标为「待验收」。

#### 第 1 轮 reviewer 验收

**审查范围**：`spec/SimRISC-04-64位数据运算.md` 全部改动 + 任务文件本身。独立脚本 `/tmp/opencode/SPEC-044t/verify.py`（审查者自写，未复用 engineer 任何脚本），对照文件内嵌生成表逐条核验。

**重跑记录（审查者本人执行的真实输出/退出码）**

1. 改动范围
```
$ git diff --name-only
".tao/tasks/spec/SPEC-044t-SimRISC04正文改新汇编格式.md"
"spec/SimRISC-04-64位数据运算.md"
$ git diff --name-only -- tools contracts docs   # 空输出
$ git status --porcelain --untracked-files=all | grep '^??'  # (none)
```

2. 生成区未触碰（`-U0` 精确命中行）
```
$ git diff -U0 -- spec/SimRISC-04-...md | grep '^@@'
@@ -51,2 +51,2 @@   @@ -57 +57 @@   @@ -61,4 +61,4 @@   @@ -67 +67 @@
@@ -77 +77 @@   @@ -92,2 +92,2 @@   @@ -99,2 +99,2 @@   @@ -103 +103 @@
@@ -109 +109 @@  @@ -112,2 +112,2 @@  @@ -116 +116 @@  @@ -121,4 +121,4 @@
@@ -127 +127 @@  @@ -144 +144 @@  @@ -151 +151 @@  @@ -159 +159 @@  @@ -169 +169 @@
@@ -182 +182 @@  @@ -185,4 +185,4 @@  @@ -202,3 +202,3 @@  @@ -211 +211 @@  @@ -216,16 +216,16 @@
```
最小 hunk 起始行 = **51 > 43**。另 `diff <(git show HEAD:...|sed -n 6,43p) <(sed -n 6,43p ...)` → **无差异**，生成区（行 6–43，含 `ASSEMBLY_LIST_END`=行 43）逐字与 HEAD 相同。

3. 正文 34 处指令与生成表「汇编形式」逐条精确比对（脚本输出，折叠空白后逐条 `PASS`；含表格单元行 144/159/169/211）
```
PASS L61/L62/L63/L64  add.uo/add.so/sub.uo/sub.so {rdHA, rdHB}, rdHC, rdHD
PASS L77 add.si rdHA, imms18   PASS L92 cmp.si rdHA, rdHB, imms12   PASS L93 cmp.ui rdHA, rdHB, immu12
PASS L99/L100 cmp.uo/cmp.so rdHB, rdHC, rdHD
PASS L112/L113 mul.so/mul.uo {rdHA, rdHB}, rdHC, rdHD
PASS L121-124 div.uo/div.so/rem.uo/rem.so rdHB, rdHC, rdHD
PASS L144 and.o rdHB, rdHC, rdHD
PASS L159 xnor.o rdHB, rdHC, rd0
PASS L169 sub.so {rd0, rdHB}, rd0, rdHC
PASS L211 ext.uo rdHB, rdHC, rdHD / ext.uo rdHB, rdHC, immu6
PASS L216-221 shl.uo/shr.uo/shr.so 各寄存器/立即数形式
PASS L223-226 ext.uo/ext.so 各寄存器/立即数形式
PASS L228-231 and.o/or.o/xor.o/xnor.o rdHB, rdHC, rdHD
checked 34 FAILS []
```
（L173 `neg.o rd3, rd4` 为伪指令示例，不在生成表，按约束保持原样，未计入。）

4. 分类正确性（脚本独立判定，非读 engineer 结论）
- **双目的**（`add.uo/add.so/sub.uo/sub.so/mul.uo/mul.so`）命中行 61/62/63/64/112/113/169：均含 `{...}`、组内**恰好 2 个 dst**、全文无 `?`（`grep '?'` 空）。
- **orrr 平铺**（`cmp.uo/cmp.so/div.*/rem.*/and.o/or.o/xor.o/xnor.o`）命中行 99/100/121-124/144/159/228-231：均**无花括号**。
- **orri 移位/扩展**（`shl.uo/shr.uo/shr.so/ext.uo/ext.so` 立即数形式）命中行 217/219/221/224/226/211：均 `rdHB, rdHC, immu6` 平铺，无花括号。

5. 行 169 双目的字段位序（对照生成表 `sub.so {rdHA, rdHB}, rdHC, rdHD`）
新记法字段序 = `{dst_hi, dst_lo}, src1, src2`。`neg.o x, y`（y = −x）展开：dst_hi=`rd0`（丢弃高位/借位）、dst_lo=`rdHB`（结果）、src1=`rd0`（0）、src2=`rdHC`（被取负源）→ `sub.so {rd0, rdHB}, rd0, rdHC`。与旧式 `sub.so rd0, rdhb, rd0, rdhc` 的位置映射（rdha=rd0 → dst_hi；rdhb=dst_lo；rdhc=src1=rd0；rdhd=src2）**逐位一致**。✅

6. 语义零变化（逐 hunk、逐行独立比对）
- 硬判据：对所有变更行，`strict(s)=` 去 `{}` + 大小写敏感的 `rdha|rdhb|rdhc|rdhd→@`，要求 old≡new。结果 **changed-line count=50，strict drift count=0**。
- 位宽/数值/公式抽查：`[63:0]`（行 144/159）、`N=63`（行 195/203/207）、`0-63`（行 195）、`-128/-32768/-2147483648/-9223372036854775808`（行 133）、`rdHB[N:0] = (rdHC[N:0] << shamt)`（行 185）、`rdHB[63:N+1] = rdHB[63:N+1]`（行 188/204）**逐字未动**（strict 比对已覆盖，无一处命中）。
- 具体寄存器：`rd0`（行 67/103/116/127/159/169）、`rd3`/`rd4`（行 173）保持小写，`grep '\brd[0-9]+\b'` 与旧版一致。

7. 反例注入（**在 /tmp 副本上注入，未触碰仓库**；脚本对每一处均报 FAIL，退出码 1）
```
inj1 cmp.uo 加花括号          → FAIL: orrr 平铺 / 结构不匹配   exit=1
inj2 shl.uo immu6 改组记法     → FAIL: orri 平铺 / 结构不匹配   exit=1
inj3 add.uo 双目的只留 1 个 dst → FAIL: 组内 dst≠2 + 结构 + 语义漂移  exit=1
inj4 mul.so 去掉双目的花括号    → FAIL: 双目的未用 braces + 结构   exit=1
inj5 0-63 → 0-62（语义漂移）   → FAIL: semantic zero-change     exit=1
inj6 add.si rdHA → rdha        → FAIL: 结构 + 小写残留          exit=1
```
注入全部作用于 `/tmp/opencode/SPEC-044t/inj*.md`；仓库 `git status --porcelain` 仍为上述 2 文件，spec md5=`795a869f205178a41af8744283ae486c`，无残留。

8. `make check` 真实退出码（无管道误判）
```
$ make check > /tmp/opencode/SPEC-044t/make-check-reviewer.log 2>&1; rc=$?; echo EXIT=$rc
EXIT=0
repository checks: PASS   （check-asm-list-consistency: 12 spec files OK）
```
另独立单跑 `python3 tools/spec/check_asm_list_consistency.py; rc=$?` → `EXIT=0`。

**约束核验（逐条）**
| # | 约束 | 结果 |
|---|------|------|
| 1 | 只改 spec 正文 + 任务文件 | ✅ 仅 2 文件；`tools/contracts/docs` 无 diff，无新增未跟踪文件 |
| 2 | 不改生成区（行 6–43） | ✅ 所有 hunk 起始 >43；行 6–43 与 HEAD 逐字相同；`ASSEMBLY_LIST_END`=43 |
| 3 | 双目的判定正确（2 dst、无 `?`） | ✅ 7 处命中，脚本断言通过 |
| 4 | orrr 平铺不加花括号 | ✅ 12 处命中 |
| 5 | orri 立即数形式（immu6 非组记法） | ✅ 6 处命中 |
| 6 | 行 169 双目的字段位序正确 | ✅ 与生成表 `sub.so {rdHA,rdHB},rdHC,rdHD` 位序一致 |
| 7 | 语义零变化 | ✅ 50 变更行 strict 比对零漂移 |
| 8 | 具体寄存器未误改 | ✅ rd0/rd3/rd4 保持 |
| 9 | 反例可检出、复原无残留 | ✅ 6 类注入全 FAIL；仓库 md5 不变 |
| 10 | `make check` EXIT=0 | ✅ |

**关于任务「完成区」的真实性**：完成区声称的「A 段 17 条」「8 个 hunk」「EXIT=0」经复核基本属实。其中「所有 hunk 起始行 `@@ -48,`…`@@ -199,`」是默认上下文 diff 的 8 个 hunk，与 `-U0` 的 23 个细粒度 hunk 系同一改动，非虚假陈述；`make check` 退出码重跑一致。完成区的验收结论与我的独立重跑逐条对齐。

**判决：Accepted**

理由：`make check` EXIT=0；正文 34 处指令全部与生成表精确相符；双目的/orrr/orri 分类、行 169 位序、语义零变化、生成区不可触碰、具体寄存器保持等全部硬约束经独立重跑与 6 类反例注入验证成立；无任何规避或弱化检查迹象。任务状态可由主会话改为「已验证」（最终接受仍由架构师/用户终审）。
