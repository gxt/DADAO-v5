# SPEC-041t: SimRISC-01（取数存数）正文改为新汇编格式

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`ADR-0013`（语法冻结）、`docs/spec/assembly-language.md` v1.1、`tools/llvm/gen_asm_list.py`、内嵌速查表（生成区）
**状态**：已验证

## 背景与目标

`spec/SimRISC-XX-*.md` 正文里的指令书写仍是**旧字段级小写记法**（如 `ld.sb rdha, rbhb, imms12`），与文件内**生成区速查表**（`ld.sb rdHA, [rbHB, imms12]`）不一致。

**用户裁定（2026-09-29）**：已有的指令书写内容**全部改为新汇编格式**（`ADR-0013` D1–D7 / `assembly-language.md` v1.1），**按指令类别逐章**推进。本任务是**第 1 章：取数存数**。

## 权威来源（转换目标）

每条指令的「新汇编形式」= `tools/llvm/gen_asm_list.py::new_form(entry, ops, field=True)` 的输出，即**同文件内嵌速查表「汇编形式」列**（生成区）。**逐条以生成表为准**，不得自行发明。

## 修改范围（仅 `spec/SimRISC-01-取数存数.md`）

### 规则

1. **寄存器字段名小写 → 大写占位**：`rdha→rdHA`、`rbhb→rbHB`、`rdhc→rdHC`、`rbha→rbHA`、`raha→raHA`、`rfha→rfHA`
2. **访存地址 → `[...]`**：`ld.sb rdha, rbhb, imms12` → `ld.sb rdHA, [rbHB, imms12]`
3. **多寄存器（`ldm`/`stm`，`rrri`）→ 组记法**：`ldm.sb rdha, rbhb, rdhc, immu6` → `ldm.sb {rdHA:rdHA+immu6-1}, [rbHB, rdHC]`；`stm.b ...` 同款（组为**源**寄存器范围）
4. **立即数原样**：`imms12`（访存偏移，单位字节，**无 `i` 后缀**）、`immu6` 原样
5. **正文中的内联指令示例**同步转换：`stm.b rd16, rb2, rd0, 8` → `stm.b {rd16:rd23}, [rb2, rd0]`
6. **正文中的字段名引用**同步大写：`rdha`→`rdHA`、`rbhb+rdhc`→`[rbHB, rdHC]` 等（保持前后一致）

### 5 个代码块（` ```simrisc `）逐块转换

| 块（行） | 段 | 转换 |
|---|---|---|
| 67–80 | 存取RD-单 | `ld.*/st.* rdha, rbhb, imms12` → `... rdHA, [rbHB, imms12]` |
| 88–101 | 存取RD-多 | `ldm.*/stm.* rdha, rbhb, rdhc, immu6` → `{rdHA:rdHA+immu6-1}, [rbHB, rdHC]` |
| 121–127 | 存取RB | `rbha` → `rbHA`；余同上 |
| 142–148 | 存取RA | `raha` → `raHA`；余同上 |
| 161–171 | 存取RF | `rfha` → `rfHA`；余同上 |

### 正文引用（行 82–181）

`rdha`/`rbha`/`raha`/`rfha`/`rbhb`/`rdhc` 等在「限制」列表与说明中的引用 → 大写；行 106 的 `stm.b rd16, rb2, rd0, 8` → `stm.b {rd16:rd23}, [rb2, rd0]`。

## 约束

- **只改 `spec/SimRISC-01-取数存数.md`**；不改生成器 / `contracts/` / `docs/` 其它文件
- **不改语义**：仅记法/标点（`[...]`/`{...}`/大小写）；数值、寄存器范围、限制条文一字不动
- **不改生成区**（`<!-- ASSEMBLY_LIST_START/END -->` 之间）；只改正文
- 逐条核对，禁止正则批量替换后不复查

## 验收标准

1. 5 个代码块全部为新汇编格式（`[...]` 地址、`{start:start+immu6-1}` 组）
2. 正文内联指令示例/字段名引用一致大写
3. **语义零变化**（数值/限制/寄存器范围逐条比对，与 HEAD 版一致）
4. **不改生成区**：`git diff` 命中行全部在 `ASSEMBLY_LIST` 区之外（给出证据）
5. 每个新形式与**内嵌速查表「汇编形式」列**（或 `docs/assembly-list.md`）**逐条相符**（给出对照证据）
6. 反例验证：注入一处回退（如把某行改回 `rdha`）→ 检查可检出；复原后无残留
7. `make check` EXIT=0

## 完成区
**测试结果**：make check EXIT=0（通过）
**修改文件**：`spec/SimRISC-01-取数存数.md`（1 文件，53 insertions / 53 deletions）
**验收结果**：
- 5 个代码块全部转换为新汇编格式（见下方转换后全文）
- 正文内联指令示例（`stm.b {rd16:rd23}, [rb2, rd0]`）和字段名引用（`rdHA`/`rbHB`/`rdHC`/`rbHA`/`raHA`/`rfHA`）均已大写
- `git diff` 命中行全部从 `@@ -65` 起（`ASSEMBLY_LIST` 区结束于行 52），未触及生成区
- 38 条指令逐条与生成表「汇编形式」列对照一致（见下方对照表）
- 反例注入：将 `ld.sb rdHA, [rbHB, imms12]` 回退为 `ld.sb rdha, rbhb, imms12` → `git diff | grep '^+' | grep 'rdha'` 可检出；复原后 `git status` 干净（仅合法修改）
- make check EXIT=0

**新发现/坑**：无
**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`spec/SimRISC-01-取数存数.md` 全文（行 67–181），聚焦 5 个代码块 + 正文引用

**逐块审查**：

| # | 块/引用 | 生成表行 | 新形式 | 旧形式 | 判定 |
|---|---------|---------|--------|--------|------|
| 1 | 块1 ld.sb (行68) | 17 | `ld.sb rdHA, [rbHB, imms12]` | `ld.sb rdha, rbhb, imms12` | ✅ |
| 2 | 块1 ld.ub (行69) | 21 | `ld.ub rdHA, [rbHB, imms12]` | `ld.ub rdha, rbhb, imms12` | ✅ |
| 3 | 块1 ld.sw (行70) | 19 | `ld.sw rdHA, [rbHB, imms12]` | `ld.sw rdha, rbhb, imms12` | ✅ |
| 4 | 块1 ld.uw (行71) | 23 | `ld.uw rdHA, [rbHB, imms12]` | `ld.uw rdha, rbhb, imms12` | ✅ |
| 5 | 块1 ld.st (行72) | 18 | `ld.st rdHA, [rbHB, imms12]` | `ld.st rdha, rbhb, imms12` | ✅ |
| 6 | 块1 ld.ut (行73) | 22 | `ld.ut rdHA, [rbHB, imms12]` | `ld.ut rdha, rbhb, imms12` | ✅ |
| 7 | 块1 ld.o (行74) | 15 | `ld.o rdHA, [rbHB, imms12]` | `ld.o rdha, rbhb, imms12` | ✅ |
| 8 | 块1 st.b (行76) | 35 | `st.b rdHA, [rbHB, imms12]` | `st.b rdha, rbhb, imms12` | ✅ |
| 9 | 块1 st.w (行77) | 42 | `st.w rdHA, [rbHB, imms12]` | `st.w rdha, rbhb, imms12` | ✅ |
| 10 | 块1 st.t (行78) | 40 | `st.t rdHA, [rbHB, imms12]` | `st.t rdha, rbhb, imms12` | ✅ |
| 11 | 块1 st.o (行79) | 38 | `st.o rdHA, [rbHB, imms12]` | `st.o rdha, rbhb, imms12` | ✅ |
| 12 | 块2 ldm.sb (行89) | 28 | `ldm.sb {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.sb rdha, rbhb, rdhc, immu6` | ✅ |
| 13 | 块2 ldm.ub (行90) | 32 | `ldm.ub {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.ub rdha, rbhb, rdhc, immu6` | ✅ |
| 14 | 块2 ldm.sw (行91) | 30 | `ldm.sw {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.sw rdha, rbhb, rdhc, immu6` | ✅ |
| 15 | 块2 ldm.uw (行92) | 34 | `ldm.uw {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.uw rdha, rbhb, rdhc, immu6` | ✅ |
| 16 | 块2 ldm.st (行93) | 29 | `ldm.st {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.st rdha, rbhb, rdhc, immu6` | ✅ |
| 17 | 块2 ldm.ut (行94) | 33 | `ldm.ut {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.ut rdha, rbhb, rdhc, immu6` | ✅ |
| 18 | 块2 ldm.o (行95) | 26 | `ldm.o {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.o rdha, rbhb, rdhc, immu6` | ✅ |
| 19 | 块2 stm.b (行97) | 43 | `stm.b {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `stm.b rdha, rbhb, rdhc, immu6` | ✅ |
| 20 | 块2 stm.w (行98) | 50 | `stm.w {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `stm.w rdha, rbhb, rdhc, immu6` | ✅ |
| 21 | 块2 stm.t (行99) | 48 | `stm.t {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `stm.t rdha, rbhb, rdhc, immu6` | ✅ |
| 22 | 块2 stm.o (行100) | 46 | `stm.o {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `stm.o rdha, rbhb, rdhc, immu6` | ✅ |
| 23 | 块3 ld.o rb (行122) | 14 | `ld.o rbHA, [rbHB, imms12]` | `ld.o rbha, rbhb, imms12` | ✅ |
| 24 | 块3 st.o rb (行123) | 37 | `st.o rbHA, [rbHB, imms12]` | `st.o rbha, rbhb, imms12` | ✅ |
| 25 | 块3 ldm.o rb (行125) | 25 | `ldm.o {rbHA:rbHA+immu6-1}, [rbHB, rdHC]` | `ldm.o rbha, rbhb, rdhc, immu6` | ✅ |
| 26 | 块3 stm.o rb (行126) | 45 | `stm.o {rbHA:rbHA+immu6-1}, [rbHB, rdHC]` | `stm.o rbha, rbhb, rdhc, immu6` | ✅ |
| 27 | 块4 ld.o ra (行143) | 13 | `ld.o raHA, [rbHB, imms12]` | `ld.o raha, rbhb, imms12` | ✅ |
| 28 | 块4 st.o ra (行144) | 36 | `st.o raHA, [rbHB, imms12]` | `st.o raha, rbhb, imms12` | ✅ |
| 29 | 块4 ldm.o ra (行146) | 24 | `ldm.o {raHA:raHA+immu6-1}, [rbHB, rdHC]` | `ldm.o raha, rbhb, rdhc, immu6` | ✅ |
| 30 | 块4 stm.o ra (行147) | 44 | `stm.o {raHA:raHA+immu6-1}, [rbHB, rdHC]` | `stm.o raha, rbhb, rdhc, immu6` | ✅ |
| 31 | 块5 ld.t rf (行162) | 20 | `ld.t rfHA, [rbHB, imms12]` | `ld.t rfha, rbhb, imms12` | ✅ |
| 32 | 块5 st.t rf (行163) | 41 | `st.t rfHA, [rbHB, imms12]` | `st.t rfha, rbhb, imms12` | ✅ |
| 33 | 块5 ld.o rf (行164) | 16 | `ld.o rfHA, [rbHB, imms12]` | `ld.o rfha, rbhb, imms12` | ✅ |
| 34 | 块5 st.o rf (行165) | 39 | `st.o rfHA, [rbHB, imms12]` | `st.o rfha, rbhb, imms12` | ✅ |
| 35 | 块5 ldm.t rf (行167) | 31 | `ldm.t {rfHA:rfHA+immu6-1}, [rbHB, rdHC]` | `ldm.t rfha, rbhb, rdhc, immu6` | ✅ |
| 36 | 块5 stm.t rf (行168) | 49 | `stm.t {rfHA:rfHA+immu6-1}, [rbHB, rdHC]` | `stm.t rfha, rbhb, rdhc, immu6` | ✅ |
| 37 | 块5 ldm.o rf (行169) | 27 | `ldm.o {rfHA:rfHA+immu6-1}, [rbHB, rdHC]` | `ldm.o rfha, rbhb, rdhc, immu6` | ✅ |
| 38 | 块5 stm.o rf (行170) | 47 | `stm.o {rfHA:rfHA+immu6-1}, [rbHB, rdHC]` | `stm.o rfha, rbhb, rdhc, immu6` | ✅ |

**正文引用审查**：

| # | 行 | 旧 | 新 | 判定 |
|---|---|---|---|------|
| 1 | 84 | `rdha` ×2 | `rdHA` ×2 | ✅ |
| 2 | 104 | `rdha`、`rbhb+rdhc` | `rdHA`、`[rbHB, rdHC]` | ✅ |
| 3 | 106 | `stm.b rd16, rb2, rd0, 8` | `stm.b {rd16:rd23}, [rb2, rd0]` | ✅ |
| 4 | 110 | `rdha` ×2 | `rdHA` ×2 | ✅ |
| 5 | 112 | `rdha` | `rdHA` | ✅ |
| 6 | 114 | `rdhc` ×2 | `rdHC` ×2 | ✅ |
| 7 | 132 | `rbha` ×2 | `rbHA` ×2 | ✅ |
| 8 | 134 | `rbha` | `rbHA` | ✅ |
| 9 | 136 | `rbhb` ×2 | `rbHB` ×2 | ✅ |
| 10 | 153 | `raha` | `raHA` | ✅ |
| 11 | 155 | `raha` | `raHA` | ✅ |
| 12 | 179 | `rfha` | `rfHA` | ✅ |

**约束核验**：
- ✅ 只改了 `spec/SimRISC-01-取数存数.md`
- ✅ 未改生成区（ASSEMBLY_LIST 区行 6–52）
- ✅ 语义零变化：数值/限制/寄存器范围一字不动（对齐要求、异常条件、范围描述均原样保留）
- ✅ 立即数原样：`imms12`、`immu6` 未变

**判决**：所有 38 条指令代码 + 12 处正文引用均已正确转换，无 finding。提交待验收。

#### 第 1 轮 reviewer 验收

> 审查者独立复核，所有结论均来自本人的命令执行（脚本自建，不复用 engineer 结论）。审查脚本位于 `/tmp/opencode/SPEC-041t/`。基线 sha256：`spec/SimRISC-01-取数存数.md = d403de170f2649de58500ba818c60485bffecbb3a8c0007926d7975f0c068297`。

**重跑记录**

1. `git status --porcelain=v1`（重跑）：

   ```
    M ".tao/tasks/spec/SPEC-041t-...md"
    M "spec/SimRISC-01-取数存数.md"
   ```

   仅 2 个文件被改，无未跟踪残留。`git diff --numstat` 对 spec 文件为 `53  53`（53 增 / 53 删）。

2. 边界定位（自建脚本 `verify_reviewer.py`）：`ASSEMBLY_LIST_START=6`、`ASSEMBLY_LIST_END=52`。`git diff --unified=0` 命中的**全部 53 个新文件行号 = [68..79, 84, 89..100, 104, 106, 110, 112, 114, 122, 123, 125, 126, 132, 134, 136, 143, 144, 146, 147, 153, 155, 162..170, 179]**，最小值 68 > 52。另将 HEAD 与工作树的 `行 6–52` 生成区各自导出后 `diff`：**逐字节相同**，sha256 均为 `1715b751...c56389b`。

3. 独立对照生成表（`verify_reviewer.py`，空白规范化后）：

   ```
   [blocks] 代码块数 = 5 (每块行数: [11, 11, 4, 4, 8])
   PASS  共 5 个 simrisc 代码块
   PASS  代码块指令行合计 38 条 (实际 38)
   PASS  全部 38 条符合 <mnem> <regHA>, [rbHB, imms12] / {<regHA>:<regHA>+immu6-1}, [rbHB, rdHC]
   PASS  正文内联示例 stm.b {rd16:rd23}, [rb2, rd0] 存在
   [table] 取数存数表条目 = 38
   PASS  代码块每条都能命中生成表汇编形式列 (未命中 0)
   PASS  生成表每条都在代码块中出现 (缺 0)
   RESULT: PASS   EXIT=0
   ```

   （双向集合相等：代码块 38 条 = `docs/assembly-list.md` 取数存数表 38 条，无一缺失/多余；非仅单向包含。）

4. 语义零变化 — 独立 oracle（`verify_transform_oracle.py`）：按任务书规则（字段名大写、rrii 加 `[...]`、rrri 转组记法）从 **HEAD 旧行**机械推导新行，与**真实 diff 的增行**逐条比对：

   ```
   pairs=53 oracle-ok=53 mismatch=0
   RESULT: PASS
   ```

   即全部 53 处改动都恰好是「记法变换」的机械结果，未夹杂任何数值/条文改动（`imms12`/`immu6`/`64`/`rd63`/`rb63`/`ra63`/`rf63` 等均在 oracle 输入中固定，若被改动必 mismatch）。另 grep 正文（行 >52）已无任何小写字段名 `rdha|rbhb|rdhc|rbha|raha|rfha` 残留。

5. 自审表真实性核对（`verify_selfreview_table.py`）：解析 engineer 自审表 38 行，逐行校验「生成表行」指向的助记符/形式、spec 行号内容、判定：`自审表指令行数 = 38，不一致 = 0，RESULT: PASS`。

6. 反例注入（均先 `cp` 备份，注入后 `sha256sum` 确认字节已变，再跑检查器）：

   - 注入 A：行 68 回退为 `ld.sb    rdha, rbhb, imms12`（sha 由 `d403de…` → `d851db…`）→ 检查器 `FAILS: 4`，`RESULT: FAIL`，`CHECKER_EXIT=1`（命中行数 53→52、38 条格式检查失败、生成表双向对照各缺 1）。
   - 注入 B：行 122 去掉 `[...]` 为 `ld.o     rbHA, rbHB, imms12`（sha → `476bd1…`）→ 检查器 `FAILS: 3`，`RESULT: FAIL`，`CHECKER_EXIT=1`。
   - 复原：`cp` 回备份，sha 恢复为 `d403de…`（与基线一致），`git status` 仅剩 2 个预期文件，未污染工作区。

7. `make check` 真实退出码（`cmd > log 2>&1; rc=$?; echo EXIT=$rc`，未用管道取 `$?`）：

   ```
   EXIT=0
   check-asm-list-consistency: 12 spec files OK
   repository checks: PASS
   ```

**约束核验**

- 只改 `spec/SimRISC-01-取数存数.md` + 本任务文件：✅（`git status` 仅此 2 文件；未触 `tools/`、`contracts/`、`docs/`）
- 未触生成区：✅（53 处命中行号 ≥68 > 52；生成区 6–52 与 HEAD 逐字节相同）
- 5 个代码块格式正确：✅（38 条全部符合 `rdHA, [rbHB, imms12]` / `{rdHA:rdHA+immu6-1}, [rbHB, rdHC]`）
- 内联示例 `stm.b {rd16:rd23}, [rb2, rd0]`：✅
- 与生成表逐条相符：✅（双向 38/38，独立复算）
- 语义零变化：✅（53/53 对称，oracle 0 mismatch；数值/限制条文/寄存器范围未动）
- 反例可检出、复原无残留：✅
- `make check` EXIT=0：✅
- 未改契约/测试/生成器来凑绿：✅（任务文件仅填状态/完成区/自审，未弱化任何验收标准）

**判决：Accepted**

独立重跑下：`make check` EXIT=0；53 处改动全在生成区外且与 HEAD 生成区逐字节一致；38 条代码块指令与 `docs/assembly-list.md`「汇编形式」列双向逐条命中；独立 oracle 证明 53 处均为纯记法变换、语义零变化；两处反例注入均被检查器捕获、复原后 sha 与基线一致、工作区干净。无 finding，提交架构师终审。
