# LLVM-052t: `.dd.{b08,w16,t32,o64}` 指导符发射

**模块**：llvm
**项目里程碑**：M4
**依赖**：`LLVM-050t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `spec/DADAO-11-AEE-应用程序运行环境.md` §汇编兼容性 §指导符（`.dd.b08`=1B、`.dd.w16`=2B、`.dd.t32`=4B、`.dd.o64`=8B；**DADAO octa = 8 字节**，与 GAS `.octa`=16B 不同）；`.tao/knowledge/contract-asm.md §7`（当前 v5 汇编器未实现、报 `unknown directive`；`.word` 被拒）。
  - 现有 AsmParser（`AsmParser/DADAOAsmParser.cpp`）与 MC 流式发射设施；`DADAOMCAsmInfo`（大端、`CommentString=";"`）。
- **输出**（组件源码改在 `.work/source/llvm-project`；导出补丁）：
  - `DADAOAsmParser` 实现 `parseDirective`（或等价）接受 **`.dd.b08` / `.dd.w16` / `.dd.t32` / `.dd.o64`**，按大端序发射对应宽度数据（表达式可含常量与符号；符号/可重定位引用按需发数据 reloc）。
  - 保持 `.word`/`.octa` 等的既有拒绝/未识别行为（与 `contract-asm §7` 一致）。
- **约束**：
  - **大端序**（`contract-elf §1.1`：`ELFDATA2MSB`）；字节序逐例核对（如 `.dd.w16 0x1234` → `12 34`）。
  - **octa=8B**（非 GAS 16B）；**不得**把 `.dd.o64` 实现为 16 字节。
  - **reloc/fixup 坑预防（5 条，同 `LLVM-050t`）**，尤其⑤大常量/大地址不得折入受限字段；数据符号引用须发对应 reloc（数据 reloc 类型若超出 `ADR-0019` 4 类，须**停下报告**，不得自行新增类型）。
  - **补丁纪律（`spec/Process-01`）**；`commit --amend` 收敛 base+1 → `make_patch.py` → `check-patch-tree`；不手改补丁。
  - 构建/串行/临时目录/留证纪律同 `LLVM-050t`；`ninja -j8`；失败即停。
  - 临时目录 `/tmp/opencode/LLVM-052t/`；**不提交 git**。

## 验收标准

1. 构建 EXIT=0。
2. **宽度/字节序**：`.dd.b08 0x12`→`12`；`.dd.w16 0x1234`→`12 34`；`.dd.t32 0x11223344`→`11 22 33 44`；`.dd.o64 0x1122334455667788`→`11 22 33 44 55 66 77 88`——用 `llvm-mc -filetype=obj` + `llvm-objdump -s`/hexdump 逐条真实核对（给出 hexdump 输出）。
3. **表达式/符号**：`.dd.o64 sym` / 含表达式的数据项可汇编；符号/可重定位引用在 `llvm-readobj -r` 可见对应数据 reloc（若需新类型则**停并报告**）。
4. **拒绝一致性**：GAS `.word`/`.octa` 仍不被接受（非零退出或明确报错），与 `contract-asm §7` 一致。
5. **lit 向量**：`tests/lit/MC/Dadao/` 新增 `.dd.*` 用例（宽度/字节序 + 反例）；`make check-lit` EXIT=0 不回归；`make check` EXIT=0。
6. 一键证据脚本 `.work/evidence/LLVM-052t/run.sh`（含 `--inject`：把 `.dd.w16` 改小端/把 `.dd.o64` 改成 16B → 期望 FAIL → 还原+重建 → 回绿）；完成区贴真实输出。

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
