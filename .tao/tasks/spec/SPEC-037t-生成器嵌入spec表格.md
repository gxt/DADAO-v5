# SPEC-037t: 重构生成器——按类别输出汇编表格到 spec 文件

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`LLVM-017t` + `LLVM-018t`（生成器渲染逻辑已更新，表格内容由渲染决定）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- 输入：`tools/llvm/gen_asm_list.py`（已支持双目的/多寄存器渲染）、`contracts/opcodes.yaml`、`spec/SimRISC-XX-*.md`（12 个文件）
- 输出：12 个 `spec/SimRISC-XX-*.md` 文件（嵌入汇编表格）、`docs/assembly-list.md`（保持不变）
- 约束：
  - 生成器按类别自动输出到对应 spec 文件，不手动复制
  - `spec/` 目录可由 spec 模块任务修改（ADR-0012 D4）
  - 依赖 `LLVM-017t`+`LLVM-018t` 的理由：表格的「汇编形式」列由渲染逻辑决定（双目的 `{...}`、多寄存器 `{start:end}`），渲染变更后必须重跑 `--embed-spec`

## 修改内容

### 1. `tools/llvm/gen_asm_list.py` 新增功能

- 新增 `--embed-spec` 模式：按分类（12 个类别）将表格输出到对应的 `spec/SimRISC-XX-*.md` 文件
- 分类到文件的映射（**12 个文件，01–12**）：

| 分类 | 文件 |
|------|------|
| 取数存数 | `spec/SimRISC-01-取数存数.md` |
| 寄存器复制 | `spec/SimRISC-02-寄存器复制.md` |
| 16位立即数操作 | `spec/SimRISC-03-16位立即数操作.md` |
| 64位数据运算 | `spec/SimRISC-04-64位数据运算.md` |
| 64位地址运算 | `spec/SimRISC-05-64位地址运算.md` |
| 控制流 | `spec/SimRISC-06-控制流.md` |
| 浮点运算 | `spec/SimRISC-07-浮点运算.md` |
| 32位数据运算 | `spec/SimRISC-08-32位数据运算.md` |
| 16位数据运算 | `spec/SimRISC-09-16位数据运算.md` |
| 8位数据运算 | `spec/SimRISC-10-8位数据运算.md` |
| 其它 | `spec/SimRISC-11-其它.md` |
| 待定 | `spec/SimRISC-12-待定.md` |

- 表格插入位置：紧接在 spec 文件的 `> **版本/分类**` 头部之后、正文之前
- 表格节标题：`## 汇编指令速查`
- 表格格式：保留全部列（助记符 | format | feature | 汇编形式 | id），与 `assembly-list.md` 一致
- 使用标记注释（`<!-- ASSEMBLY_LIST_START -->` / `<!-- ASSEMBLY_LIST_END -->`）界定生成区域，便于幂等更新
- 幂等性：重跑不改变非生成区域的内容
- 生成区域包含 `### <类>（N 条）` 标题行（与 `assembly-list.md` 章节标题一致）

### 2. deferred 章节处理

浮点运算（SimRISC-07）和待定（SimRISC-12）的表格仍嵌入（格式已定义），但加 `**deferred**` 标注。

### 3. 新增一致性 checker（建议）

新增 `tools/spec/check_asm_list_consistency.py`：
- 比对 `spec/SimRISC-XX-*.md` 中 `<!-- ASSEMBLY_LIST_START/END -->` 区域的内容与 `gen_asm_list.py --embed-spec` 的输出
- 不一致则 exit 1
- 接入 `make check`

## 验收标准

1. 运行 `python3 tools/llvm/gen_asm_list.py --embed-spec` 后，**12 个** spec 文件（01–12）各包含对应类别的汇编表格
2. 表格位于 `> **版本/分类**` 头部之后、正文之前，节标题为 `## 汇编指令速查`
3. 表格前后有 `<!-- ASSEMBLY_LIST_START -->` / `<!-- ASSEMBLY_LIST_END -->` 标记
4. 表格内容与 `docs/assembly-list.md` 对应章节逐字节一致（含 `### <类>（N 条）` 标题行）
5. 重跑 `--embed-spec` 不改变非生成区域（幂等性验证：重跑前后 `git diff` 仅含时间戳变化）
6. `docs/assembly-list.md` 的默认输出不受影响（`-o` 行为不变）
7. deferred 章节（07/12）的表格有 `**deferred**` 标注
8. 生成器无 `--embed-spec` 时行为与修改前完全一致（向后兼容）
9. `make check` 通过（无回归）
10. 若实现了一致性 checker：`python3 tools/spec/check_asm_list_consistency.py` exit 0

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
