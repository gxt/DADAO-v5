# SPEC-040t: 浮点分类指令（cls）改为多寄存器

**模块**：spec
**项目里程碑**：M2
**依赖**：无
**状态**：已验证

## 问题描述

`spec/SimRISC-07-浮点运算.md` §浮点分类指令 当前写：

```
ftcls   rdhb, rfhc, 1      ← 第三操作数固定为 1
focls   rdhb, rfhc, 1
```

即把 `focls`/`ftcls` 当作**单寄存器**分类（`immu6` 写死为 1）。但同章「格式转换」（`ft2fo` 等 20 条）是**多寄存器**：`immu6` = **连续寄存器个数（1–63）**，汇编形式用**组记法** `{...:...}`。`cls` 应与之对齐。

**用户裁定（2026-09-29）**：
1. `immu6` = **连续寄存器个数（1–63）**
2. 汇编（规范示例）用**组记法** `{rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}`
3. 目的 rd 连续 `immu6` 个、源 rf 连续 `immu6` 个
4. **只修改 `spec/`**（不改生成器/`opcodes.yaml`/`assembly-list.md`/`assembly-language.md`）

## 修改内容（仅 `spec/SimRISC-07-浮点运算.md`）

§浮点分类指令：

1. 代码块改为：
   ```
   ftcls   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}
   focls   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}
   ```
2. 补 `immu6` 语义说明（连续个数 1–63 + 示例，**对照 §格式转换 的表述风格**）：
   - 例：`focls rd4, rf8, 3` 对 rf8/rf9/rf10 分类，结果写入 rd4/rd5/rd6
   - 源和目的范围可重叠；按序号递增逐对处理，先读后写
3. 分类结果位定义（[63..10] 清零、位 0–9 类别）**保持不变**
4. 补限制（对照 §格式转换）：
   - `immu6` = 0 时触发 ILLI 异常
   - 任一起始寄存器 + immu6 > 64 时触发 ILLI 异常

## 约束

- **只改 `spec/SimRISC-07-浮点运算.md`**；不改其他任何文件（生成器/合约/assembly-list 均不动）
- 保持 0.5.3 语义（除用户裁定的多寄存器化）
- 逐条核对，禁止正则批量替换

## 验收标准

1. `spec/SimRISC-07-浮点运算.md` §浮点分类指令 为**多寄存器**：组记法 + `immu6` 连续个数（1–63）+ 示例
2. `immu6` 限制（=0 → ILLI；越界 → ILLI）已补
3. 类别位定义不变（位 0–9、[63..10] 清零）
4. **未改其他文件**（`git status` 仅该文件）
5. 反例验证（语义检查）

## 完成区
**测试结果**：语义检查通过（修改后 §浮点分类指令 全文见下方）
**修改文件**：`spec/SimRISC-07-浮点运算.md`
**验收结果**：修改后的 §浮点分类指令 全文：

```
## 浮点分类指令

浮点分类指令对浮点数进行判断分类，并将分类结果写入数据寄存器，操作数类型为 `orri`，指令如下：

```simrisc
ftcls   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}
focls   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}
```

其中 `immu6` 指定连续分类的寄存器数量（1–63），目的寄存器为 rd，源寄存器为 rf。例如 `focls rd4, rf8, 3` 对 rf8、rf9、rf10 分类，结果分别写入 rd4、rd5、rd6。源和目的寄存器范围可以重叠，分类按序号递增逐对进行，先读后写。

对每个源寄存器的浮点数据，指令设置对应目的寄存器中的相应位，并将其他位清零：[63..10] 全部清零，分类结果仅使用 [9..0]。

| 类别位 | 含义 |
| ---   | ---               |
| 0     | negativeInfinity  |
| 1     | negativeNormal    |
| 2     | negativeSubnormal |
| 3     | negativeZero      |
| 4     | positiveZero      |
| 5     | positiveSubnormal |
| 6     | positiveNormal    |
| 7     | positiveInfinity  |
| 8     | signalingNaN      |
| 9     | quietNaN          |

限制如下：

- `immu6` = 0 时触发 ILLI 异常
- 任一起始寄存器 + immu6 > 64 时触发 ILLI 异常
```

`git status --short`：
```
 M "spec/SimRISC-07-\346\265\256\347\202\271\350\277\220\347\256\227.md"
```

仅 `spec/SimRISC-07-浮点运算.md` 一个文件被修改。

**新发现/坑**：汇编指令速查表（`<!-- ASSEMBLY_LIST_START -->` 区域）中 `focls`/`ftcls` 的汇编形式仍为旧格式 `focls rdHB, rfHC, immu6`，与规范组记法不一致。此表由外部维护（约束要求不改），后续如需对齐应单独处理。
**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 代码块最初用 `rdhb, rfhc, immu6` 而非组记法 | ✅已修 | 改为 `{rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | 读取文件第 204–206 行确认 |

自审结论：所有 finding 已修，标「待验收」。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（独立重跑，不采信完成区）
**审查对象**：`spec/SimRISC-07-浮点运算.md` 工作树 vs `HEAD`（`ef75d1e`）+ 任务文件完成区

##### 一、重跑记录（真实输出/退出码）

1）改动范围（`git status --porcelain`）：
```
 M ".tao/tasks/spec/SPEC-040t-浮点分类指令多寄存器.md"
 M "spec/SimRISC-07-浮点运算.md"
```
仅 spec 正文 + 本任务文件（完成区）被改；`git status --porcelain -- contracts/ docs/ tools/` **输出为空**（生成器/合约/`assembly-list.md`/`assembly-language.md` 均未动）。

2）分类位表**逐行不变**（改前 `HEAD` vs 改后工作树，取 `| 类别位` 行到 `| 9` 行）：
```
$ diff <(git show HEAD:spec/SimRISC-07-浮点运算.md | sed -n '/^| 类别位/,/^| 9 /p') \
       <(sed -n '/^| 类别位/,/^| 9 /p' spec/SimRISC-07-浮点运算.md)
（无输出）  table_diff_exit=0
```
表 10 行（位 0–9 含义）逐行一致，**未误改**。

3）内嵌速查表区（`ASSEMBLY_LIST_START`→`END`）**未改动**：
```
$ diff <(git show HEAD:... | sed -n '/ASSEMBLY_LIST_START/,/ASSEMBLY_LIST_END/p') \
       <(sed -n '/ASSEMBLY_LIST_START/,/ASSEMBLY_LIST_END/p' ...)
（无输出）  asm_diff_exit=0
```
该区 `focls`/`ftcls` 仍为 `focls rdHB, rfHC, immu6` / `ftcls rdHB, rfHC, immu6`（工作树第 20、39 行）——按约束**保持旧格式**。

4）`make check-asm-list`（生成表一致性门控，回归检查）：
```
$ make check-asm-list
check-asm-list-consistency: 12 spec files OK
EXIT=0
```
内嵌表与生成器输出仍一致，本改动**未引入 `make check` 回归**。

5）**反例注入（证明检查可失败 + 可复原）**：临时把工作树速查表 `focls` 行改为组记法，跑 `make check-asm-list`：
```
FAIL: 浮点运算: content mismatch in SimRISC-07-浮点运算.md
  expected 52 lines, got 52 lines
1 inconsistency(ies) found, 11 OK
make: *** [Makefile:148: check-asm-list] Error 1
CHECK_EXIT=2
```
随后用备份还原，`sha256sum` 改前/改后一致：
```
a7729791f6934d0ad5031a03143042c3cb4b1fc70999e7c120ad55af6637aaba  （注入前）
a7729791f6934d0ad5031a03143042c3cb4b1fc70999e7c120ad55af6637aaba  （还原后）
```
→ 检查器灵敏、还原彻底，工作树无污染。

##### 二、约束核验（逐条）

| # | 约束/验收点 | 结论 | 证据 |
|---|---|---|---|
| 1 | 仅改 `spec/SimRISC-07-浮点运算.md`（不动生成器/contracts/docs） | ✅ | `git status --porcelain -- contracts/ docs/ tools/` 空；`git diff --stat` 仅 spec + 任务文件 |
| 2a | 组记法 `{rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | ✅ | 工作树 205–206 行，与任务 D2 逐字一致 |
| 2b | `immu6`=连续个数 1–63 + 示例 | ✅ | 209 行：「数量（1–63）」+ 例 `focls rd4, rf8, 3` → rf8/9/10 → rd4/5/6，与任务给的示例一致 |
| 2c | 源目的可重叠 / 递增逐对 / 先读后写 | ✅ | 209 行末句 |
| 3 | 类别位定义不变（[63..10] 清零、位 0–9） | ✅ | 211 行保留「[63..10] 全部清零，[9..0]」；表 diff exit=0 |
| 4 | 限制已补（=0→ILLI、越界→ILLI） | ✅ | 226–229 行两条 limitation，措辞与 §格式转换（100–103 行）一致 |
| 5 | 与 §格式转换 表述风格一致 | ✅ | 「其中 `immu6` 指定连续…数量（1–63）…例如…源和目的寄存器范围可以重叠，…按序号递增逐对进行，先读后写」+「限制如下：- `immu6` = 0 …- 任一起始寄存器 + immu6 > 64 …」结构与 §格式转换 同型 |
| 6 | 速查表区未被改动 + 登记遗留 | ✅（遗留已登记） | asm 区 diff 空；见下「遗留登记」 |

##### 三、说明与遗留登记

- 完成区「`git status --short` 仅一个文件」表述略不完整（任务文件本身也处于 M 状态，属完成区编辑，正常）；约束真正针对的生成器/合约/文档类文件确实零改动，**不构成违反**。
- **遗留（本任务登记，非阻断）**：`spec/SimRISC-07-浮点运算.md` 内嵌速查表（`ASSEMBLY_LIST_START/END`，即 `focls rdHB, rfHC, immu6` / `ftcls rdHB, rfHC, immu6`）与 `docs/assembly-list.md`（第 179、198 行）仍为**旧单寄存器格式**，与 §浮点分类指令 正文的组记法**暂不一致**。该表由 `tools/llvm/gen_asm_list.py` 从 `contracts/opcodes.yaml` 生成，本次约束明令不改生成区/生成器 ⇒ 留待后续「cls 多寄存器化」的下游任务一并处理。已同步登记至 `.tao/knowledge/deferred.md` → `## spec`。

##### 四、判决

**Accepted**

- 验收命令/检查（`make check-asm-list`、表区 diff、速查表区 diff、改动范围检查）在审查者独立重跑下全部通过，硬约束逐条守住，类别位表与速查表区零改动且经反例注入证伪证明检查灵敏。
- 本 Accepted 仅代表「engineer 本次产出达标」，最终接受仍由架构师终审。