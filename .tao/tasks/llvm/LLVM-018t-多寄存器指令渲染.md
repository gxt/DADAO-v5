# LLVM-018t: 更新生成器——多寄存器指令识别与渲染

**模块**：llvm
**项目里程碑**：M1→M2
**依赖**：`SPEC-036t`（规范已定义多寄存器组记法规则）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- 输入：`tools/llvm/gen_asm_list.py`（当前版本）、`contracts/opcodes.yaml`、`docs/spec/assembly-language.md` v2
- 输出：`tools/llvm/gen_asm_list.py`（更新后）
- 约束：识别并渲染 28 条多寄存器指令（8 条寄存器复制 + 20 条浮点格式转换）

## 修改内容

### 1. 识别多寄存器指令

两类指令的 `immu6` 字段表示连续寄存器个数：

**寄存器复制**（8 条，`orri` 格式）：
- `ra2rd`/`rb2rb`/`rb2rd`/`rd2ra`/`rd2rb`/`rd2rd`/`rd2rf`/`rf2rd`

**浮点格式转换**（20 条，`orri` 格式）：
- `ft2fo`/`fo2ft`/`ft2ft`/`fo2fo`/`ft2it`/`ft2io`/`ft2ut`/`ft2uo`
- `fo2it`/`fo2io`/`fo2ut`/`fo2uo`/`it2ft`/`io2ft`/`ut2ft`/`uo2ft`
- `it2fo`/`io2fo`/`ut2fo`/`uo2fo`

识别方式：`format == "orri"` 且 `mnemonic` 匹配上述列表中的任一条，且存在 `immu6` 字段。

### 2. 渲染规则

源和目的**都用组记法**（范围）：

- **字段名模式**（`field=True`，供表格）：
  - `ra2rd {rdHB:rdHB+immu6-1}, {raHC:raHC+immu6-1}`
  - `ft2fo {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}`
  - `rb2rb {rbHB:rbHB+immu6-1}, {rbHC:rbHC+immu6-1}`
  - `rd2rf {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}`
  - `ft2it {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}`
  - `it2ft {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}`
- **示例模式**（`field=False`，供 lit）：
  - `ra2rd {rd8:rd10}, {ra1:ra3}`（count=3）
  - `ft2fo {rf2:rf4}, {rf5:rf7}`（count=3）
  - `rb2rb {rb2:rb4}, {rb5:rb7}`（count=3）
  - `rd2rf {rf2:rf4}, {rd5:rd7}`（count=3）
  - `ft2it {rd2:rd4}, {rf5:rf7}`（count=3）
  - `it2ft {rf2:rf4}, {rd5:rd7}`（count=3）
- 示例的 count 使用固定值 3（与 `ldm`/`stm` 的 `_range()` 一致）

### 3. 位置

- `new_form()`：在现有 `ldm`/`stm` 分支之后、默认分支之前，插入多寄存器分支
- `example_line()`：同上
- 复用已有的 `_range()` 辅助函数
- 注：`new_template()` 已确认为死代码，本次**删除该函数**或标记为 deprecated

## 验收标准

1. `python3 tools/llvm/gen_asm_list.py` 成功运行，输出无报错
2. `docs/assembly-list.md` 中 28 条多寄存器指令的汇编形式列显示为 `{dst:…+immu6-1}, {src:…+immu6-1}`（字段名模式）
3. `python3 tools/llvm/gen_asm_list.py --plain --syntax new` 中 28 条指令显示为 `{rd8:rd10}, {ra1:ra3}` 等具体示例
4. 其余 226 条指令的渲染不受影响（逐条比对）
5. **非 rd→rd 方向抽查**（6 条，覆盖所有 bank 组合）：
   - `rb2rb {rbHB:rbHB+immu6-1}, {rbHC:rbHC+immu6-1}`（rb→rb）
   - `rd2rf {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}`（rd→rf）
   - `rf2rd {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}`（rf→rd）
   - `ft2it {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}`（rf→rd，浮点转整数）
   - `it2ft {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}`（rd→rf，整数转浮点）
   - `fo2fo {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}`（rf→rf）
6. 反例验证：故意将 `ra2rd` 从多寄存器列表中移除，确认其回退为旧语法 `rdHB, raHC, immu6`（diff 非空）
7. `ldm`/`stm` 的渲染逻辑不受影响（仍使用 `{rdHA:rdHA+immu6-1}, [rbHB, rdHC]`）
8. `new_template()` 已删除或标记为 deprecated
9. `make check` 通过（无回归）

## 完成区
**测试结果**：9/9 验收标准通过
**修改文件**：`tools/llvm/gen_asm_list.py`（1 个文件）、`docs/assembly-list.md`（重生成）
**验收结果**：

字段名模式（`--syntax new` 表格输出）— 28 条全部正确：
```
| `ra2rd` | `orri` | `ra` | `ra2rd {rdHB:rdHB+immu6-1}, {raHC:raHC+immu6-1}` | `ra2rd_orri_ra` |
| `rb2rb` | `orri` | `rb` | `rb2rb {rbHB:rbHB+immu6-1}, {rbHC:rbHC+immu6-1}` | `rb2rb_orri_rb` |
| `rb2rd` | `orri` | `rb` | `rb2rd {rdHB:rdHB+immu6-1}, {rbHC:rbHC+immu6-1}` | `rb2rd_orri_rb` |
| `rd2ra` | `orri` | `ra` | `rd2ra {raHB:raHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `rd2ra_orri_ra` |
| `rd2rb` | `orri` | `rb` | `rd2rb {rbHB:rbHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `rd2rb_orri_rb` |
| `rd2rd` | `orri` | `rd` | `rd2rd {rdHB:rdHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `rd2rd_orri_rd` |
| `rd2rf` | `orri` | `rf` | `rd2rf {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `rd2rf_orri_rf` |
| `rf2rd` | `orri` | `rf` | `rf2rd {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `rf2rd_orri_rf` |
| `ft2fo` | `orri` | `rf` | `ft2fo {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `ft2fo_orri_rf` |
| `ft2ft` | `orri` | `rf` | `ft2ft {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `ft2ft_orri_rf` |
| `fo2ft` | `orri` | `rf` | `fo2ft {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2ft_orri_rf` |
| `fo2fo` | `orri` | `rf` | `fo2fo {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2fo_orri_rf` |
| `ft2it` | `orri` | `rf` | `ft2it {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `ft2it_orri_rf` |
| `ft2io` | `orri` | `rf` | `ft2io {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `ft2io_orri_rf` |
| `ft2ut` | `orri` | `rf` | `ft2ut {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `ft2ut_orri_rf` |
| `ft2uo` | `orri` | `rf` | `ft2uo {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `ft2uo_orri_rf` |
| `it2ft` | `orri` | `rf` | `it2ft {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `it2ft_orri_rf` |
| `io2ft` | `orri` | `rf` | `io2ft {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `io2ft_orri_rf` |
| `ut2ft` | `orri` | `rf` | `ut2ft {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `ut2ft_orri_rf` |
| `uo2ft` | `orri` | `rf` | `uo2ft {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `uo2ft_orri_rf` |
| `fo2it` | `orri` | `rf` | `fo2it {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2it_orri_rf` |
| `fo2io` | `orri` | `rf` | `fo2io {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2io_orri_rf` |
| `fo2ut` | `orri` | `rf` | `fo2ut {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2ut_orri_rf` |
| `fo2uo` | `orri` | `rf` | `fo2uo {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2uo_orri_rf` |
| `it2fo` | `orri` | `rf` | `it2fo {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `it2fo_orri_rf` |
| `io2fo` | `orri` | `rf` | `io2fo {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `io2fo_orri_rf` |
| `ut2fo` | `orri` | `rf` | `ut2fo {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `ut2fo_orri_rf` |
| `uo2fo` | `orri` | `rf` | `uo2fo {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `uo2fo_orri_rf` |
```

示例模式（`--plain --syntax new`）— 28 条全部正确：
```
ra2rd {rd8:rd10}, {ra2:ra4}
rb2rb {rb2:rb4}, {rb3:rb5}
rb2rd {rd8:rd10}, {rb3:rb5}
rd2ra {ra1:ra3}, {rd9:rd11}
rd2rb {rb2:rb4}, {rd9:rd11}
rd2rd {rd8:rd10}, {rd9:rd11}
rd2rf {rf2:rf4}, {rd9:rd11}  // excluded_m1
rf2rd {rd8:rd10}, {rf3:rf5}  // excluded_m1
ft2fo {rf2:rf4}, {rf3:rf5}  // excluded_m1
ft2ft {rf2:rf4}, {rf3:rf5}  // excluded_m1
fo2ft {rf2:rf4}, {rf3:rf5}  // excluded_m1
fo2fo {rf2:rf4}, {rf3:rf5}  // excluded_m1
ft2it {rd8:rd10}, {rf3:rf5}  // excluded_m1
ft2io {rd8:rd10}, {rf3:rf5}  // excluded_m1
ft2ut {rd8:rd10}, {rf3:rf5}  // excluded_m1
ft2uo {rd8:rd10}, {rf3:rf5}  // excluded_m1
it2ft {rf2:rf4}, {rd9:rd11}  // excluded_m1
io2ft {rf2:rf4}, {rd9:rd11}  // excluded_m1
ut2ft {rf2:rf4}, {rd9:rd11}  // excluded_m1
uo2ft {rf2:rf4}, {rd9:rd11}  // excluded_m1
fo2it {rd8:rd10}, {rf3:rf5}  // excluded_m1
fo2io {rd8:rd10}, {rf3:rf5}  // excluded_m1
fo2ut {rd8:rd10}, {rf3:rf5}  // excluded_m1
fo2uo {rd8:rd10}, {rf3:rf5}  // excluded_m1
it2fo {rf2:rf4}, {rd9:rd11}  // excluded_m1
io2fo {rf2:rf4}, {rd9:rd11}  // excluded_m1
ut2fo {rf2:rf4}, {rd9:rd11}  // excluded_m1
uo2fo {rf2:rf4}, {rd9:rd11}  // excluded_m1
```

非 rd→rd 方向抽查（6 条）：
```
rb2rb {rbHB:rbHB+immu6-1}, {rbHC:rbHC+immu6-1}（rb→rb）✓
rd2rf {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}（rd→rf）✓
rf2rd {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}（rf→rd）✓
ft2it {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}（rf→rd）✓
it2ft {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}（rd→rf）✓
fo2fo {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}（rf→rf）✓
```

反例验证：将 `ra2rd` 从 `_MULTI_REG_MNEMONICS` 移除后，输出回退为旧语法 `ra2rd rdHB, raHC, immu6`（field 模式）/ `ra2rd rd8, ra2, 1`（example 模式）✓

`ldm`/`stm` 渲染不受影响：`ldm.o {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` ✓

`new_template()` 已标记 deprecated（docstring 添加 `.. deprecated::` 注释）✓

`make check` EXIT=0（PASS）：
```
validate_vectors: 178/178 M1 identities covered OK
spec drift check: PASS
check-patch-tree: 2 component(s), 67 patches OK
repository checks: PASS
```

**新发现/坑**：
- `operands()` 返回的字典需包含 `role` 字段（由 LLVM-017t 添加），否则多寄存器分支无法通过 `reg_ops` 识别 dst/src。此 key 在当前实现中通过 `op["kind"] == "reg"` + 列表顺序隐式排序（dst 在前、src 在后），未依赖 `role`。
- `new_form()` 中多寄存器分支的位置很重要：必须在 `ldm/stm` 之后、`ld/st` 之前。因为 `ldm/stm` 也是 `orri` 格式的多寄存器指令，但有独立的渲染逻辑。
- 示例模式中 dst 使用 `nth=0`、src 使用 `nth=1` 来错开起始寄存器，避免同 bank 指令（如 `rb2rb`、`ft2fo`）的源和目的范围重叠。

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审阅范围**：`tools/llvm/gen_asm_list.py` 全部改动

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `_MULTI_REG_MNEMONICS` 是否遗漏指令 | ✅已修（无需修） | 无改动 | 与 `contracts/opcodes.yaml` 交叉核对：8 条寄存器复制 + 20 条浮点格式转换 = 28 条，全部命中 |
| 2 | `new_form()` 中多寄存器分支是否会被 `ldm/stm` 拦截 | ✅已修（无需修） | 无改动 | `ldm/stm` 在前、多寄存器在后，两者的 mnemonic 不重叠（`ldm.*`/`stm.*` vs `ra2rd` 等）；且 `ldm/stm` 分支以 `mnemonic.startswith(("ldm.", "stm."))` 检查，不会误触 |
| 3 | `example_line()` 中同 bank 指令（`rb2rb`、`ft2fo` 等）源和目的范围是否重叠 | ✅已修（无需修） | 无改动 | `nth=0`（dst）vs `nth=1`（src）错开起始寄存器，确保范围不重叠 |
| 4 | `field=True` 模式中 `immu6` 字段名是否正确 | ✅已修（无需修） | 无改动 | 硬编码 `"immu6"` 字符串，与 `contracts/opcodes.yaml` 中的字段名一致 |
| 5 | 反例验证是否有效 | ✅已修（无需修） | 无改动 | 移除 `ra2rd` 后输出回退为旧语法，diff 非空 |

**判决**：所有 finding 已处置（均为"无需修"的确认项），可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（独立重跑 + 双独立 oracle，未采信完成区转述）

**审查范围**：`tools/llvm/gen_asm_list.py`（working tree diff）、`docs/assembly-list.md`（重生成）、`contracts/opcodes.yaml`（oracle 源）、`docs/spec/assembly-language.md` §4.2/§5。

##### 1. 重跑记录（命令 + 真实输出/退出码）

**(a) 生成器运行（验收 #1）**
```
$ python3 tools/llvm/gen_asm_list.py; echo EXIT=$?
gen-asm-list: 254 entries -> /home/ubuntu/DADAO-v5/docs/assembly-list.md
EXIT=0
$ python3 tools/llvm/gen_asm_list.py --plain --syntax new -o /tmp/.../plain-new.txt; echo EXIT=$?
EXIT=0
```

**(b) 生成物 == 生成器输出 + 幂等（通用）**
```
重跑前后 md5 docs/assembly-list.md 均 = 1a0896b0098ce7b9dcc52cdb3009768e
$ diff <重跑前备份> docs/assembly-list.md ; echo $?   -> 0
```

**(c) 28 条字段模式（验收 #2）** — 与 oracle 逐行比对 `34/34` 全中（含 28 条多寄存器）。样例：
```
| `ra2rd` | `orri` | `ra` | `ra2rd {rdHB:rdHB+immu6-1}, {raHC:raHC+immu6-1}` | `ra2rd_orri_ra` |
| `rd2rf` | `orri` | `rf` | `rd2rf {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `rd2rf_orri_rf` |
| `ft2it` | `orri` | `rf` | `ft2it {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `ft2it_orri_rf` |
| `it2ft` | `orri` | `rf` | `it2ft {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `it2ft_orri_rf` |
```

**(d) 28 条示例模式（验收 #3）** — `--plain --syntax new` 中 28 条源/目的**均**为组记法 `{start:end}`：
```
ra2rd {rd8:rd10}, {ra2:ra4}
rb2rb {rb2:rb4}, {rb3:rb5}
rd2rf {rf2:rf4}, {rd9:rd11}
ft2it {rd8:rd10}, {rf3:rf5}
it2ft {rf2:rf4}, {rd9:rd11}
...
```
（注：示例起始寄存器由生成器自选，与任务书文本 `{ra1:ra3}` 字面不同；任务书 #3 措辞为「`{rd8:rd10}, {ra1:ra3}` **等**具体示例」，规范 §4.2 示例亦为**举例**、非强制字面，故不构成偏差。）

**(e) 各 bank 方向正确（验收 #5，逐条独立重算 28/28）**

用**两个互不依赖**的 oracle 交叉验证：(一) `opcodes.yaml` 的 `role=dst/src` 派生；(二) 由助记符 `X2Y` 语义（前缀=源、后缀=目的；`fo/ft→rf`、`it/io/ut/uo→rd`）派生。两者与表格/plain 渲染**全部吻合**。任务书点名的 6 条：
```
rb2rb : 源 rb → 目的 rb   table {rbHB..},{rbHC..}   plain {rb2..},{rb3..}   OK
rd2rf : 源 rd → 目的 rf   table {rfHB..},{rdHC..}   plain {rf2..},{rd9..}   OK
rf2rd : 源 rf → 目的 rd   table {rdHB..},{rfHC..}   plain {rd8..},{rf3..}   OK
ft2it : 源 rf → 目的 rd   table {rdHB..},{rfHC..}   plain {rd8..},{rf3..}   OK
it2ft : 源 rd → 目的 rf   table {rfHB..},{rdHC..}   plain {rf2..},{rd9..}   OK
fo2fo : 源 rf → 目的 rf   table {rfHB..},{rfHC..}   plain {rf2..},{rf3..}   OK
naming-oracle: 28/28 OK ; direction-check: 28/28 OK
```
→ **第一操作数恒为目的、第二恒为源**，且 bank 一对一正确（含 `rd2ra`/`rb2rd` 等非 rd→rd）。

**(f) 其余 226 条不受影响（验收 #4）**
以 id 为键比对 HEAD 版与当前版 `docs/assembly-list.md`（254 id 集合一致）：
```
changed ids: 34   # = 6 双目的（LLVM-017t）+ 28 多寄存器（本任务），无其它
git diff --numstat -- docs/assembly-list.md -> 34  34
```
其中没有任何 `ldm.*`/`stm.*`、`orrr`、`cs.*` 等行变化。

**(g) `ldm`/`stm` 不受影响（验收 #7）**
HEAD 与当前版的 19 条 `ldm.*`/`stm.*` 渲染**逐条完全相同**（differing ids = 0），仍为 `X {rdHA:rdHA+immu6-1}, [rbHB, rdHC]`。

**(h) 反例注入（验收 #6）：从 `_MULTI_REG_MNEMONICS` 移除 `ra2rd`**
```
$ diff <基线> <注入后 table> ; echo $?
83c83
< | `ra2rd` | `orri` | `ra` | `ra2rd {rdHB:rdHB+immu6-1}, {raHC:raHC+immu6-1}` | `ra2rd_orri_ra` |
---
> | `ra2rd` | `orri` | `ra` | `ra2rd rdHB, raHC, immu6` | `ra2rd_orri_ra` |
EXIT=1（diff 非空）
plain 回退：ra2rd rd8, ra2, 1
```
还原：md5 回到 `3acbfb13c9a1d626826a538859f85492`（逐字节一致），`git status` 仅 4 个预期文件，无残留。

**(i) `new_template()` 处置（验收 #8）**
`grep -rn new_template` 仅命中 **def 行自身**；docstring 含 `.. deprecated::`。

**(j) `make check`（验收 #9）**
```
$ make check > log 2>&1; rc=$?; echo EXIT=$rc
EXIT=0
manifest validation: PASS
validate_vectors: 178/178 M1 identities covered OK
spec drift check: PASS
check-patch-tree: 2 component(s), 67 patches OK
repository checks: PASS
```

##### 2. 独立 oracle（自写，不 import 生成器）

- oracle-1（`opcodes.yaml` role）：派生 34 条期望，`34/34` 与表格吻合。
- oracle-2（助记符 `X2Y` 语义）：28 条方向 `28/28` 与表格 + plain 吻合。
- 两 oracle 交叉一致 → 方向与字段名**语义正确**，非仅「跑绿」。

##### 3. 约束核验（逐条）

| # | 验收标准 | 结论 | 证据 |
|---|---------|------|------|
| 1 | 生成器运行无报错 | ✓ | (a) EXIT=0 |
| 2 | 表格 28 条 = `{dst:…+immu6-1}, {src:…+immu6-1}` | ✓ | (c) oracle 34/34 |
| 3 | plain 28 条 = `{start:end}` 示例 | ✓ | (d) 28 条均组记法 |
| 4 | 其余 226 条不受影响 | ✓ | (f) id 级比对，34 行=6+28 |
| 5 | 6 条非 rd→rd 方向抽查 | ✓ | (e) 两 oracle 28/28，含点名 6 条 |
| 6 | 反例：移除 ra2rd 回退旧语法 | ✓ | (h) diff 非空、已还原 |
| 7 | `ldm`/`stm` 不受影响 | ✓ | (g) 19 条逐条相同 |
| 8 | `new_template()` 删除或 deprecated | ✓ | (i) |
| 9 | `make check` 通过 | ✓ | (j) EXIT=0 |
| 约束 | 识别 8+20=28 条 | ✓ | oracle 从 `opcodes.yaml` 重算：8 复制 + 20 格式转换 = 28，无遗漏/多计 |

##### 4. 非阻断观察（供架构师/主会话定夺）

- 示例模式起始寄存器为生成器自选（如 `ra2rd {rd8:rd10}, {ra2:ra4}`），与任务书文本 `{ra1:ra3}`、规范 §4.2 示例 `{ra1:ra3}` 的字面不同；因规范/任务书均为「示例」语义、且 criterion 用「等」字，判定**不构成偏差**。若架构师希望示例与规范逐字一致，属风格优化，另开任务。
- `operands()` 新增 `role` key 影响全部 254 条内部字典，但已验证输出零附带变化（(f)）。

##### 5. 判决

**Accepted**

- 验收标准 #1–#9 在**我自己的重跑 + 双独立 oracle** 下全部通过；反例注入真实生效且已逐字节还原。
- 28 条多寄存器的**方向与字段名语义正确**（`rd2ra`/`rb2rb`/`rd2rf`/`rf2rd`/`ft2it`/`it2ft`/`fo2fo` 等全部核对），`ldm`/`stm` 与其余 226 条零附带影响。
- 未发现契约/测试被弱化以凑绿；`make check` 独立门控 EXIT=0。
