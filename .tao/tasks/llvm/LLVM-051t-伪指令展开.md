# LLVM-051t: 伪指令展开（`set.rd/set.rb/set.ft/set.fo`）

**模块**：llvm
**项目里程碑**：M4
**依赖**：`SPEC-106t`、`LLVM-050t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `SPEC-106t` 落地后的 `spec/SimRISC-03`（`set.rd`/`set.rb`/`set.ft`/`set.fo` 展开细则）与 `.tao/adr/adr-0013-assembly-syntax.md` **D11**（Accepted；只留 8 条合成型、常量 vs 符号、`set.rb` 细节、`ret` 无无参）。
  - 现有 AsmParser（`.work/source/llvm-project/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp`，约 1430 行；当前未实现伪指令，全部报 `unrecognized instruction mnemonic`）。
  - `LLVM-050t` 的 `ABS48` fixup/reloc 设施；指令编码表 `contracts/opcodes.yaml`（`set.zw`/`set.ow`/`or.w`/`andn.w` 的 rd/rb 形式、`rb2rd`/`rd2rb`/`rf2rd`/`ra2rd`/`rd2rd`/`rb2rb`/`rd2rf`/`ft2ft`/`fo2fo`、`set.w`）。
- **输出**（组件源码改在 `.work/source/llvm-project`；导出补丁）：
  - `DADAOAsmParser` 支持并**展开** 8 条合成型伪指令：
    - `set.rd rd, imm64`：**可汇编期求值的常量** → 最少指令数（`set.zw`/`set.ow` + `or.w`/`andn.w`，按 16 位 wyde，参考 `SimRISC-03 §set.rd` 展开例）；**符号/可重定位** → **固定 3 片 + `R_DADAO_ABS48`**（`ADR-0019 D4/D5`）。
    - `set.rd rd, rs`（`rs∈{rb,rf,ra,rd}`）→ `rb2rd`/`rf2rd`/`ra2rd`/`rd2rd`。
    - `set.rb rb, imm64` → `set.zw-rb` + `or.w-rb`（**无 `set.ow-rb`**，全 1 需 `set.zw`+3×`or.w`）；地址 ≤48 位。
    - `set.rb rb, rs`（`rs∈{rd,rb}`）→ `rd2rb`/`rb2rb`。
    - `set.ft rf, imm32` → 2 条 `set.w`；`set.ft rf, rs`（`rs∈{rd,rf}`）→ `rd2rf`/`ft2ft`。
    - `set.fo rf, imm64` → 4 条 `set.w`；`set.fo rf, rs`（`rs∈{rd,rf}`）→ `rd2rf`/`fo2fo`。
  - **反汇编只显真实指令**：伪指令不进入 printer（`set.rd` 等不产出、不往返为伪指令）。
- **约束**：
  - 严格按 `ADR-0013 D11`：**不实现** `nop`/`return`/`not.*`/`neg.*`（报 `unrecognized instruction mnemonic`）；**`ret` 不加无参形态**。
  - **常量 vs 符号**判据（`ADR-0013 D11`）：同段可解析表达式按可求值处理（最少指令数）；跨段/外部按符号处理（3 片 + `ABS48`）。
  - **reloc/fixup 坑预防（5 条，同 `LLVM-050t`）**，尤其⑤大常量不得折入受限字段（`set.rd` 立即数须按 wyde 材料化）。**②** same-section 折叠不可靠即退回真重定位。
  - **补丁纪律（`spec/Process-01`）**；`commit --amend` 收敛 base+1 → `make_patch.py` → `check-patch-tree`；不手改补丁。
  - 构建/串行/临时目录/留证纪律同 `LLVM-050t`；`ninja -j8`；失败即停。
  - 临时目录 `/tmp/opencode/LLVM-051t/`；**不提交 git**。

## 验收标准

1. 构建 EXIT=0。
2. **常量展开**：`set.rd rd1, 0x1234ABCD` 等（`SimRISC-03` 例）→ `llvm-mc -filetype=obj` EXIT=0，反汇编**只显真实** `set.zw`/`or.w` 序列（无伪指令文本）；逐例独立字节/指令数核对（给出期望展开表）。
3. **寄存器传值**：`set.rd rd5, rb3` → `rb2rd`；`set.rb rb1, rd7` → `rd2rb`；`set.ft rf1, rd5` → `rd2rf`；`set.fo rf2, rf7` → `fo2fo`——反汇编逐条核对。
4. **符号/可重定位**：对跨 section/未定义符号的 `set.rd rd, sym`，`llvm-readobj -r` 显示 **固定 3 条 `R_DADAO_ABS48`**（`LLVM-050t` 设施）；同段可解析者按最少指令数展开、无 reloc。
5. **删除项不实现**：`nop`/`return`/`not.o`/`neg.o` 等 → `llvm-mc` 报 `unrecognized instruction mnemonic`（非零退出）；`ret rd0` → 报错（既有静态规则）。
6. **lit 向量**：`tests/lit/MC/Dadao/` 新增伪指令用例（`set.*` 展开 + 删除项反例）；`make check-lit` EXIT=0 不回归；`make check` EXIT=0；`make test-codegen` 不回归。
7. 一键证据脚本 `.work/evidence/LLVM-051t/run.sh`（含 `--inject`：把 `set.rd` 常量展开改错/把 `nop` 加回 → 期望 FAIL → 还原+重建 → 回绿）；完成区贴真实输出。

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
