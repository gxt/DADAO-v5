# LLVM-018t: 更新生成器——多寄存器指令识别与渲染

**模块**：llvm
**项目里程碑**：M1→M2
**依赖**：`SPEC-036t`（规范已定义多寄存器组记法规则）
**状态**：待开始

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
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
