# LLVM-053t: `-multiple-to-single` 汇编器选项

**模块**：llvm
**项目里程碑**：M4
**依赖**：`LLVM-051t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `spec/DADAO-11-AEE-应用程序运行环境.md` §汇编兼容性 §汇编器选项：`-multiple-to-single`——「将多寄存器指令转换为一系列的单寄存器指令；转换过程**保持助记符（opcode）不变**」；`.tao/knowledge/contract-asm.md §8`（当前 v5 报 `Unknown command line argument`）。
  - 现有 AsmParser（`AsmParser/DADAOAsmParser.cpp`）与多寄存器指令编码：`ldm.*`/`stm.*`（`rrri`，`{start:end}` 组）、块赋值/格式转换（`orri`，`immu6`=连续个数，共 8+20 条）。
- **输出**（组件源码改在 `.work/source/llvm-project`；导出补丁）：
  - 为 `llvm-mc` 注册 CL 选项 **`-multiple-to-single`**；启用时把多寄存器指令展开为一串**单寄存器**指令（同助记符，例如 `ldm.o {rd8:rd10}, [rb0, rd1]` → 3 条单寄存器 `ldm.o` 各自偏移）；未启用（默认）行为**不变**。
- **约束**：
  - **保持助记符**；转换后**语义等价**（各寄存器/各元素按序）。
  - 只影响多寄存器指令；单寄存器指令与其它指令不变。
  - **reloc/fixup 坑预防（5 条，同 `LLVM-050t`）**：展开后的每条仍需正确发/解析 fixup。
  - **补丁纪律（`spec/Process-01`）**；`commit --amend` 收敛 base+1 → `make_patch.py` → `check-patch-tree`；不手改补丁。
  - 构建/串行/临时目录/留证纪律同 `LLVM-050t`；`ninja -j8`；失败即停。
  - 临时目录 `/tmp/opencode/LLVM-053t/`；**不提交 git**。

## 验收标准

1. 构建 EXIT=0。
2. **选项生效**：`llvm-mc -triple=dadao -multiple-to-single -filetype=obj` EXIT=0；对 `ldm.*`/`stm.*`/块赋值/格式转换各 ≥1 例，反汇编显示**展开为单寄存器序列**（给出真实 `llvm-objdump -d` 输出），且**助记符不变**。
3. **默认不变**：不加该选项时，多寄存器指令编码与 `LLVM-051t` 前一致（逐字节比对，给出 before/after）。
4. **选项可识别**：`llvm-mc --help` 含 `-multiple-to-single`；未知选项仍报错。
5. **lit 向量**：`tests/llvm/lit/MC/DADAO/` 新增用例（选项开/关对照）；`make check-lit` EXIT=0 不回归；`make check` EXIT=0。
6. 一键证据脚本 `.work/evidence/LLVM-053t/run.sh`（含 `--inject`：把展开逻辑改错/漏一条单寄存器 → 期望 FAIL → 还原+重建 → 回绿）；完成区贴真实输出。

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
（审查者独立验证的重跑记录、约束核验、判决）
