# LLVM-010t: 系统指令助记符与 smoke 修正

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-008t`、`LLVM-005t`、`SPEC-006t`、`SPEC-003t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`LLVM-008t` 的 MC 闭环（全量 lit + 字节级 CHECK）、`LLVM-005t` 的指令 def（含系统指令）、`.tao/knowledge/contract-isa.md` §7（系统指令）、`.tao/knowledge/adr-0004-test-machine.md`（SPEC-006t，exit port/复位/加载协议）、`contracts/opcodes.yaml`（SPEC-003t）
- 输出：确认 M1 系统指令（`swym`/`illi`/`fence`）已可汇编（若 `LLVM-005t` 未覆盖则补齐 def）、修正后的 smoke `.s`（`tests/e2e/` 或 `tests/lit/` 对应位置）、lit E2E 用例
- 约束：只改 LLVM 端与 smoke 汇编；不改 QEMU 文件；助记符与 ISA 1:1（不加 alias）；`make build-mc` PASS；`.s → .o` 字节与独立 golden 一致

## 背景（完整）

### 目标

确保 M1 系统指令在 `llvm-mc` 中可汇编，并把 smoke `.s` 修正为 0.5.3 命名，使 LLVM 端产物与独立 golden 字节一致。M1 端到端测试需要 `llvm-mc` 汇编完整测试程序（含退出路径），任何缺失助记符都会阻断 `.s → .o → .bin` 流水线。

### 设计理由

- M1 系统指令（`contract-isa.md` §7）：**`swym`**（iiii，占位/nop）、**`illi`**（oiii，非法指令→ILLI 异常）、**`fence`**（oiii，内存序屏障）。这三条属 M1 范围，须在 `llvm-mc` 中可汇编。
- **`escape`/`trap`**（ciii）属特权 cfx 系统指令，**Excluded from M1**（`contract-isa.md` §7.5），本任务不处理。
- 测试机 pass/fail 由 `adr-0004-test-machine.md`（SPEC-006t）冻结的 **exit port MMIO**（8B 对齐，用 `st.o` 写）承载，v5 无 `halt` 指令。
- 助记符必须与 ISA 1:1，不引入 alias，避免汇编文本与规范脱节。

### 关键概念 / 数据

- **v5 M1 系统指令**（`contract-isa.md` §7）：
  - `swym N`（iiii）：占位/nop，后 24 位为时延参数。§7.1
  - `illi N`（oiii）：非法指令，引发 ILLI 异常。§7.2
  - `fence immu18`（oiii）：内存序屏障，低 4 位编码屏障类型。§7.3
- **Excluded from M1**：`escape`/`trap`（ciii，特权 cfx）、`cfx2rd`/`cfx2rc`（crrr）、`cfxld`/`cfxst`（crii）。§7.5
- **smoke `.s` 助记符映射**（0.4.1 → 0.5.3，按需修正）：`jump_i`→`jump`、`call_i`→`call`、`setzw`→`set.zw`、`sto`→`st.o`、`ldo`→`ld.o`、`brnz`→`br.nz`、`unimp`→`illi`、`addi`→`add.si`。
- **验证**：`llvm-mc -filetype=obj` → `llvm-objcopy -O binary --only-section=.text` → 与独立 golden 字节 `diff`。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-035a-llvm-halt-asmparser.md`（**仅参考** 0628 smoke 修正思路；v5 无 `halt`）。
- 本项目：`contract-isa.md` §7、`adr-0004-test-machine.md`、`contracts/opcodes.yaml`。

## 交付物

- 确认 M1 系统指令（`swym`/`illi`/`fence`）在 `llvm-mc` 中可汇编；若 `LLVM-005t` 已覆盖则给出验证证据（`llvm-mc -filetype=asm` 回显 + `-filetype=obj` 字节正确）；若缺失则补齐 TableGen def。
- 修正后的 smoke `.s`：助记符改为 0.5.3 命名（`jump`/`call`/`set.zw`/`st.o`/`ld.o`/`br.nz`/`illi`/`fence` 等）。
- 对应的 lit 用例（E2E pipeline：`llvm-mc` → `llvm-objcopy`）。
- 完成区记录：系统指令助记符注册验证、smoke 汇编成功、与独立 golden 字节 `diff MATCH`。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **v5 无 `halt`**：`contract-isa.md`（0.5.3）无 `halt` 助记符。0.4.1 的 `halt`（op=0x00，riii）在 v5 中 op=0x00 为 MISC-AMO/LR-SC 子表，**不得照搬**。退出机制为 ADR-0004 exit port MMIO（`st.o` 写）。
- **M1 系统指令集不同**：v5 M1 = `swym`/`illi`/`fence`（§7.1–7.3）；`escape`/`trap`/`cfx*` 为 Excluded（§7.5）。0628 的 `halt` 定义（0007-dadao-control-flow.patch）不适用。
- **smoke 退出路径**：0.4.1 用 `halt rd1`；v5 用 `st.o` 写 exit port（地址/宽度/语义见 `adr-0004-test-machine.md`），smoke `.s` 须按 ADR-0004 重写。
- **E2E 验证**：0628 用 QEMU 执行验证 exit=42/0；v5 的 QEMU 执行属 qemu 模块，本任务只保证 LLVM 端可汇编且与独立 golden 字节一致，QEMU 交叉验证作为后续依赖。
- **不复制 0.4.1 补丁正文/编码数据**。

## 已知坑 / 结论

- **系统指令缺失风险**：若 `LLVM-005t` 遗漏 `swym`/`illi`/`fence` 中任一条，`llvm-mc` 会报 `Unrecognized instruction mnemonic`。本任务须验证并补齐。
- **smoke 助记符错配**：0628 `jump_i`/`call_i` 与 LLVM AsmString 不符；v5 smoke 必须用 `contracts/opcodes.yaml` 中的精确助记符。
- **字节一致性**：`.s` 汇编字节必须与独立 golden（`contracts/opcodes.yaml` 手推）`diff` 一致，不得用 LLVM 输出自举 golden。
- **助记符 1:1**：不加 LLVM alias。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-035a-llvm-halt-asmparser.md`（仅参考 smoke 修正思路）
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/knowledge/contract-isa.md`（§7.1–§7.3）、`.tao/knowledge/adr-0004-test-machine.md`、`contracts/opcodes.yaml`

## 验收标准

1. M1 系统指令（`swym`/`illi`/`fence`）在 `llvm-mc` 中可汇编且编码字节正确；若 `LLVM-005t` 已覆盖则给出验证证据
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