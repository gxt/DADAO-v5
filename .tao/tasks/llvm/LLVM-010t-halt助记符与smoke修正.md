# LLVM-010t: halt 助记符 + smoke .s 修正

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-009t`、`SPEC-006t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`LLVM-009t` 的 MC 闭环、`.tao/knowledge/contract-isa.md` §7（系统指令）、`.tao/knowledge/adr-0004-test-machine.md`（SPEC-006t，exit port/复位/加载协议）、`verif/opcodes.yaml`
- 输出：系统/退出相关指令助记符定义（若 `LLVM-005t` 未覆盖则补齐）、修正后的 smoke `.s`（`tests/e2e/` 或 `tests/lit/` 对应位置）、lit E2E 用例
- 约束：只改 LLVM 端与 smoke 汇编；不改 QEMU 文件；助记符与 ISA 1:1（不加 alias）；`make build-mc` PASS；`.s → .o` 字节与独立 golden 一致

## 背景（完整）

### 目标

0628 `DL-035a` 的背景：`llvm-mc -triple=dadao -filetype=obj` 汇编 `halt rd1` 时报 `Unrecognized instruction mnemonic`，根因是 `halt` 在 `DADAOInstrInfo.td` 中缺失；同时 smoke 测试用了错误助记符（`jump_i 1` 应为 `jump 1`，`call_i N` 应为 `call N`）。目标是在 `.td` 中补 `halt`、修正 smoke `.s`、重建 LLVM、验证 `.s → .o → .bin` 与独立 golden 字节一致。

本任务把上述背景适配到 v5：确保系统/退出相关助记符在 `llvm-mc` 中可汇编，并把 smoke `.s` 修正为 0.5.3 命名，使 LLVM 端产物与独立 golden 字节一致。

### 设计理由

- M1 端到端测试需要 `llvm-mc` 汇编完整测试程序（含退出路径），任何缺失助记符都会阻断 `.s → .o → .bin` 流水线。
- 助记符必须与 ISA 1:1，不引入 alias，避免汇编文本与规范脱节。

### 关键概念 / 数据

- **0.4.1 的 `halt`**（0628 约定）：op=0x00、format riii、ha=rd 源寄存器（exit code）、imm18=0；编码 `(0x00 << 24) | (ha << 18)`；作为测试机退出/观测约定，非 SimRISC 规范指令。
- **v5（0.5.3）的对应机制**：
  - `contract-isa.md` §7 系统指令的退出/陷入为 `escape cfxname, imms18`（ciii，退出当前特权态）与 `trap cfxname, immu18`（ciii）；占位为 `swym N`（iiii）；非法为 `illi immu18`（oiii）。
  - 测试机 pass/fail 由 `adr-0004-test-machine.md`（SPEC-006t）冻结的 **exit port MMIO**（8B 对齐，用 `st.o` 写）承载，而非 `halt`。
- **smoke `.s` 助记符映射**（0.4.1 → 0.5.3，按需修正）：`jump_i`→`jump`、`call_i`→`call`、`setzw`→`set.zw`、`sto`→`st.o`、`ldo`→`ld.o`、`brnz`→`br.nz`、`unimp`→`illi`、`addi`→`add.si`。
- **验证**：`llvm-mc -filetype=obj` → `llvm-objcopy -O binary --only-section=.text` → 与独立 golden 字节 `diff`。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-035a-llvm-halt-asmparser.md`（完整转述：背景、目标、halt 定义、smoke 修正、重建、E2E 验证、约束、验收、Architecture Review）。
- DADAO-0628：`components/llvm/patches/0007-dadao-control-flow.patch`（halt 定义所在，**仅参考**）。
- DADAO-0628：`components/gem5/patches/0003-dadao-halt-regdump.patch`（halt 语义参考，**仅参考**）。

## 交付物

- 系统/退出相关指令 `def`（若 `LLVM-005t` 已覆盖 `escape`/`trap`/`illi`/`swym` 则本任务只做验证；缺则补齐）。
- 修正后的 smoke `.s`：助记符改为 0.5.3 命名（`jump`/`call`/`set.zw`/`st.o`/`ld.o`/`br.nz`/`illi` 等）。
- 对应的 lit 用例（E2E pipeline：`llvm-mc` → `llvm-objcopy`）。
- 完成区记录：助记符注册验证、smoke 汇编成功、与独立 golden 字节 `diff MATCH`。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **`halt` 在 v5 不存在**：`contract-isa.md`（0.5.3）无 `halt` 助记符；退出特权态为 `escape`、陷入为 `trap`、测试机 exit 为 ADR-0004 的 exit port。因此本任务标题沿用 0628 的 `halt` 命名，但**实际交付是补齐 0.5.3 系统指令助记符 + 修正 smoke 命名**。
- **op=0x00 冲突**：0.4.1 `halt` 用 op=0x00（riii）；0.5.3 op=0x00 为 MISC-AMO/LR-SC 子表（ha 为 minor-op），**不得照搬 0.4.1 的 halt 编码**。
- **smoke 退出路径**：0.4.1 用 `halt rd1`；v5 用 `st.o` 写 exit port（地址/宽度/语义见 `adr-0004-test-machine.md`），smoke `.s` 须按 ADR-0004 重写。
- **E2E 验证**：0628 用 QEMU 执行验证 exit=42/0；v5 的 QEMU 执行属 qemu 模块，本任务只保证 LLVM 端可汇编且与独立 golden 字节一致，QEMU 交叉验证作为后续依赖。
- **不复制 0.4.1 补丁正文/编码数据**。

## 已知坑 / 结论

- **0628 根因**：`halt` 缺失导致 `Unrecognized instruction mnemonic`；v5 须在 `LLVM-005t` 阶段就确认系统指令（`escape`/`trap`/`illi`/`swym`）已在 M1 范围并被定义，避免同类缺口。
- **smoke 助记符错配**：0628 `jump_i`/`call_i` 与 LLVM AsmString 不符；v5 smoke 必须用 `verif/opcodes.yaml` 中的精确助记符。
- **字节一致性**：`.s` 汇编字节必须与独立 golden（`verif/opcodes.yaml` 手推）`diff` 一致，不得用 LLVM 输出自举 golden。
- **助记符 1:1**：不加 LLVM alias。
- **待确认**：若 v5 测试机仍需要一条专用退出助记符（而非纯 MMIO），须由 `adr-0004-test-machine.md` 明确；本任务以 ADR-0004 为准。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-035a-llvm-halt-asmparser.md`
- DADAO-0628：`.work/DADAO-0628/components/llvm/patches/0007-dadao-control-flow.patch`
- DADAO-0628：`.work/DADAO-0628/components/gem5/patches/0003-dadao-halt-regdump.patch`
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/knowledge/contract-isa.md`（§7）、`.tao/knowledge/adr-0004-test-machine.md`（SPEC-006t 产出后）、`verif/opcodes.yaml`

## 验收标准

1. 系统/退出相关助记符（`escape`/`trap`/`illi`/`swym` 中 M1 所需者）在 `llvm-mc` 中可汇编；若 `LLVM-005t` 已覆盖则给出验证证据
2. smoke `.s` 助记符全部为 0.5.3 命名，`llvm-mc -filetype=obj` 汇编成功
3. `.s → .o → .bin` 字节与独立 golden 一致（`diff MATCH`）
4. `make build-mc` PASS；相关 lit 用例 PASS
5. 未改 QEMU 文件；未加 LLVM alias
6. 完成区注明 v5 无 `halt`、退出机制为 ADR-0004 exit port

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
