# INTEG-002t: MC↔QEMU 端到端冒烟

**模块**：integ
**项目里程碑**：M1
**依赖**：`LLVM-013m`、`QEMU-020m`、`SPEC-006t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `LLVM-013m` 交付的 `llvm-mc`（DADAO target，能汇编 M1 指令）
  - `QEMU-020m` 交付的 `qemu-system-dadao`
  - `QEMU-014t` 的 ROM trampoline
  - `SPEC-006t` 的 Test Machine ADR（机器名、BINARY_BASE、exit port）
- 输出：
  - `tests/e2e/*.s`：3 条冒烟汇编（算术 / 算术+比较 / 控制流）
  - `tests/lit/E2E/*.test` + `tests/lit/E2E/lit.cfg`：lit 固化
  - 完成区附 llvm-mc → obj → bin → QEMU exit code 全链路记录
- 约束：
  - 优先最小测试（能 PASS 即达成里程碑），不要求覆盖全部指令
  - 不改 `tests/vectors/isa/*.yaml`（QEMU 单元测试维持独立）
  - `tests/e2e/`、`tests/lit/E2E/` 为本任务新建目录

## 背景（完整）

### 目标

验证 `llvm-mc` 汇编的 DADAO 二进制能在 `qemu-system-dadao` 上正确执行，形成 M1 的 MC↔QEMU 集成闭环：

1. 编写 3 条 DADAO 汇编冒烟测试（算术、load/store 或算术+比较、控制流各一）。
2. 用 `llvm-mc` 汇编 → 生成 raw binary。
3. QEMU 运行 → 验证正确退出码。
4. 写入 lit 测试固化为门控。

### 设计理由

`llvm-mc`（MC 层）与 QEMU（执行层）此前各自独立验证；只有把「同一份 .s 经 MC 汇编、在 QEMU 执行得到期望退出码」串起来，才能证明两条链的编码/语义一致。这是 M1 集成的关键门控。

### 关键概念 / 数据

**测试场景（0.4.1 形态，v5 按 0.5.3 助记符重写）**

- 场景 A（算术）：`add.si` 设置立即数 → 退出码为该值
- 场景 B（RD 算术+比较）：两条立即数 + 一条 RD 运算 → 退出码为运算结果
- 场景 C（无条件跳转）：`jump-iiii` 跳过错误路径 → 退出码 0

**llvm-mc 汇编命令**：

```bash
LLVM_MC=.work/build/llvm/bin/llvm-mc
$LLVM_MC -triple=dadao -filetype=obj -o smoke.o tests/e2e/smoke.s
llvm-objcopy -O binary --only-section=.text smoke.o smoke.bin
```

**QEMU 运行命令**：

```bash
QEMU=.work/qemu/build/qemu-system-dadao
$QEMU -M <machine> -bios tests/scripts/trampoline.bin -kernel smoke.bin \
      -display none -nographic
echo "exit: $?"
```

**lit 固化**：`tests/lit/E2E/` 下每场景一个 `.test`，RUN 行串起 llvm-mc → objcopy → QEMU → 退出码断言；`lit.cfg` 配置 `%llvm-mc`/`%qemu`/`%trampoline`/`%objcopy` 替换变量。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-033a-phase4-e2e-smoke.md`（完整转述：背景、3 场景汇编、llvm-mc/objcopy 命令、QEMU 命令、lit 固化、调试指引、约束、验收、完成区、代码级 Architecture Review 的逐指令编码验证）
- DADAO-0628：`tests/scripts/gen_e2e_binary.py`、`tests/scripts/run_e2e.py`、`tests/lit/E2E/`（形态参考，禁止复制正文）
- DADAO-0628：`docs/adr/0004-test-machine.md`（BINARY_BASE、机器内存映射）

## 交付物

- `tests/e2e/smoke_arith.s`、`tests/e2e/smoke_add.s`、`tests/e2e/smoke_jump.s`（v5 助记符重写）
- `tests/lit/E2E/lit.cfg` + `tests/lit/E2E/*.test`
- （仅当 `llvm-mc` 尚不能汇编时）临时 raw binary 生成器 + QEMU 运行器作为过渡，并在完成区明确标注为过渡方案
- 完成区附全链路真实输出

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **核心差异 — 必须真正走 MC 路径**：0.4.1 完成区遗留「`llvm-mc` DADAO skeleton 无 `halt`/`add`/`addi`/`jump_i` 定义，绕道 `gen_e2e_binary.py` 手编 raw binary」；v5 依赖 `LLVM-013m` 已交付可汇编 M1 指令的 `llvm-mc`，**本任务以 .s→.o→.bin→QEMU 真实链路为验收**，raw 生成器仅可作过渡并在完成区标注。
2. **助记符**：`addi`→`add.si`（0.5.3 立即数自增/设置语义变化）、`add`→`add.uo`/`add.so`（rrrr）、`jump_i`→`jump-iiii`、`halt`→退出/停机指令按 `contract-isa.md` §7.5 确定。
3. **编码**：0.4.1 手推 `0x1904002A` 等；v5 全部由 `llvm-mc` 产生，不手编、不复制。
4. **机器名/路径**：`-M dadao-m1` 等以 `SPEC-006t` ADR 与 `QEMU-020m` 实际为准；QEMU 路径 `.work/qemu/build/`。
5. **lit 变量**：`%qemu`/`%trampoline`/`%objcopy` 以 v5 `INFRA`/`LLVM` 的构建布局配置。
6. **退出码**：以 `SPEC-006t` ADR 的 exit port 协议为准。

## 已知坑 / 结论

摘自 DADAO-0628 DL-033a 完成区与代码级 Architecture Review：

1. **0.4.1 绕道 raw binary**：因 llvm-mc skeleton 无指令定义，用 `gen_e2e_binary.py` 手编。v5 若 `LLVM-013m` 就绪应走真实 MC 路径；若仍不能汇编，须显式记录为遗留，不能假装走了 MC。
2. **逐指令编码验证**：0.4.1 审查手推 addi/add/halt/jump 编码；v5 这些由 `llvm-mc` 产生，验证方式改为「objdump 反汇编回助记符 + QEMU 退出码」。
3. **`jump-iiii` offset 单位**：word（4 bytes），跳转目标 = 下一条 + imm*4（v5 以 `contract-isa.md` §5.2 为准）。
4. **调试指引**：llvm-mc 报 unknown target → 确认 LLVM build 含 DADAO target；QEMU 得 0x88（ILLI）→ 编码与解码不匹配，用 `llvm-objdump -d` 核对；无输出/hang → trampoline 未跳转或 binary 格式不对，用 `-d in_asm` 看 TCG trace。
5. **最小化原则**：能 PASS 即里程碑，不追求指令全覆盖。
6. **不污染单元测试**：不改 `tests/vectors/isa/*.yaml`，E2E 与 QEMU 单元测试两条独立路径。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-033a-phase4-e2e-smoke.md`
- DADAO-0628：`.work/DADAO-0628/tests/scripts/gen_e2e_binary.py`
- DADAO-0628：`.work/DADAO-0628/tests/scripts/run_e2e.py`
- DADAO-0628：`.work/DADAO-0628/tests/lit/E2E/`
- 本项目：`.tao/knowledge/adr-0004-test-machine.md`、`contracts/opcodes.yaml`、`.tao/knowledge/contract-isa.md` §5/§7.5
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. 3 条 `.s` 经 `llvm-mc` 汇编成功（非 raw 手编），objcopy 提取 `.text`
2. QEMU 执行后退出码符合各场景期望（算术=运算结果、跳转=0）
3. `llvm-lit tests/lit/E2E/` 全 PASS
4. 全链路命令与真实输出记录在完成区（llvm-mc → objcopy → QEMU → exit code）
5. 未修改 `tests/vectors/isa/*.yaml`
6. 若 `llvm-mc` 无法汇编，完成区必须显式标注遗留并说明过渡方案，不得声称走通 MC 路径

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
