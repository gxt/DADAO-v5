# LLVM-017t: 更新生成器——双目的指令渲染

**模块**：llvm
**项目里程碑**：M1→M2
**依赖**：`SPEC-036t`（规范已定义双目的语法）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- 输入：`tools/llvm/gen_asm_list.py`（当前版本）、`contracts/opcodes.yaml`、`docs/spec/assembly-language.md` v2
- 输出：`tools/llvm/gen_asm_list.py`（更新后）
- 约束：只改双目的指令的渲染逻辑，不改其它指令

## 修改内容

### 1. 识别双目的指令

在 `new_form()` 中识别 6 条双目的指令：
- `add.uo`/`add.so`/`sub.uo`/`sub.so`/`mul.uo`/`mul.so`
- 识别方式：`format == "rrrr"` 且 `mnemonic` 在上述列表中，且 `rdha` 和 `rdhb` 的 `role` 均为 `dst`

### 2. 渲染规则

- **字段名模式**（`field=True`，供表格）：`add.uo {rdHA, rdHB}, rdHC, rdHD`
- **示例模式**（`field=False`，供 lit）：`add.uo {rd8, rd9}, rd10, rd11`
- 花括号内逗号后加空格

### 3. 位置

- `new_form()`：在 `br.*`/`cs.*`/`jump`/`call`/`ldm`/`stm` 等分支之后、默认分支之前，插入双目的分支
- `example_line()`：同上
- 注：`new_template()` 已确认为死代码（无调用点），本次**删除该函数**或标记为 deprecated

## 验收标准

1. `python3 tools/llvm/gen_asm_list.py` 成功运行，输出无报错
2. `docs/assembly-list.md` 中 6 条双目的指令的汇编形式列显示为 `{rdHA, rdHB}, rdHC, rdHD`（字段名模式）
3. `python3 tools/llvm/gen_asm_list.py --plain --syntax new` 中 6 条双目的指令显示为 `{rd8, rd9}, rd10, rd11`（示例模式）
4. 其余 248 条指令的渲染不受影响（逐条比对：重跑前后 `diff` 仅涉及 6 条双目的指令）
5. 6 条双目的指令在 `--plain` 输出中的汇编形式与 `assembly-list.md` 表格一致
6. 反例验证：故意将 `add.uo` 从双目的列表中移除，确认其回退为旧语法 `rdHA, rdHB, rdHC, rdHD`（diff 非空）
7. `new_template()` 已删除或标记为 deprecated（无调用点）
8. `make check` 通过（无回归）

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
