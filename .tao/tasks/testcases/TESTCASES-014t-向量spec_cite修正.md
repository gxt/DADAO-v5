# TESTCASES-014t: 向量 spec_cite 按新文档编号修正

**模块**：testcases
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题描述（G3）

`tests/vectors/isa/*.yaml` 的 `spec_cite` 仍用**旧文档编号**（重组前 SimRISC-01~04 的语义），共约 **589 条** 指向的文档不含该指令。例如：

- `SimRISC-01 §加减操作`（SimRISC-01 现为「取数存数」）→ 应按位宽指向 SimRISC-04/08/09/10
- `SimRISC-01 §rd0 为目的寄存器约定` → 已迁至 SimRISC-00
- `misc.yaml` 的 swym `SimRISC-04 §占位指令` → SimRISC-11

## 修改内容

### 1. 向量生成器

- `tools/testcases/generate_isa_vectors.py`
- `tools/testcases/generate_mem_vectors.py`
- `tools/testcases/generate_ctrl_br.py`
- `tools/testcases/generate_ctrl_jump_call_ret.py`
- `tools/testcases/generate_misc.py`

修正各生成器的 `spec_cite`，按**指令类别与位宽**指向正确的新文档：
- 8/16/32/64 位数据运算 → SimRISC-10/09/08/04
- 存储（取数存数）→ SimRISC-01
- 寄存器复制 → SimRISC-02
- 16位立即数 → SimRISC-03
- 64位地址运算 → SimRISC-05
- 控制流 → SimRISC-06
- 浮点运算 → SimRISC-07
- 其它 → SimRISC-11
- 待定 → SimRISC-12
- 通用约定（rd0/rb0/rf0 等）→ SimRISC-00

### 2. 重生成向量

各生成器重跑，产物与仓库一致。

### 3. misc.yaml / generate_misc.py

swym 的 `spec_cite` 从 `SimRISC-04 §占位指令` → `SimRISC-11 §占位指令`。

## 约束

- **改生成器，不改产物**
- 逐条核对，禁止正则批量替换
- 不改动向量的 word/input_state/expected 等语义字段

## 验收标准

1. 向量中「spec_cite 指向文档不含该指令」条数 = 0（原 589）
2. 各生成器重跑输出与仓库文件一致
3. `python3 tools/testcases/validate_vectors.py` EXIT=0（178/178）
4. `make check` EXIT=0
5. 向量的语义字段（word/input_state/expected_state）未被误改

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