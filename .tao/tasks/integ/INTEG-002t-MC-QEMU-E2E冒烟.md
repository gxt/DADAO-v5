# INTEG-002t: MC↔QEMU 端到端冒烟

**模块**：integ
**项目里程碑**：M1
**依赖**：`LLVM-013m`、`QEMU-021m`、`SPEC-006t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `LLVM-013m` 交付的 `llvm-mc`（DADAO target，能汇编 M1 指令）
  - `QEMU-021m` 交付的 `qemu-system-dadao`
  - `QEMU-014t` 的 ROM trampoline
  - `SPEC-006t` 的 Test Machine ADR（机器名、BINARY_BASE、exit port）
- 输出：
  - `tests/e2e/*.s`：3 条冒烟汇编（算术 / 算术+比较 / 控制流）
  - `tests/lit/E2E/*.test` + `tests/lit/E2E/lit.cfg.py`：lit 固化
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

- 场景 A（算术）：`add.si` 设置立即数 → 退出码 **0x00**（PASS）
- 场景 B（RD 算术+比较）：两条立即数 + 一条 RD 运算 → **guest 内比较**结果 → 退出码 **0x00**（PASS）
- 场景 C（无条件跳转）：`jump-iiii` 跳过错误路径 → 退出码 **0x00**（PASS）

**退出码约定（甲，用户裁定）**：所有场景**成功 = `0x00`**，失败 = 非零（`0x01`–`0x7F`）。这与 ADR-0004 D5 的退出码分区一致（`0x00`=PASS / `0x01`–`0x7F`=FAIL / `0x80`–`0xFF`=fault）。
**不得**用「退出码 = 运算结果」的字面比对方式（那会落入 D5 的 FAIL 段）。运算结果须由 guest **内部比较**（XOR+ORR，形态同 ADR-0009 D2）后归约为 0x00/非零。

**退出机制（重要）**：`tests/scripts/trampoline.bin` **只做 SP/RAM 设置 + 跳转**（`gen_trampoline.py`），**不提供退出路径** ⇒ 每条 smoke `.s` **必须自己写 exit port**。可复用序列：
```
set.zw rbX, wp2, 0xffff     # rbX = 0x0000_ffff_0000_0000
or.w   rbX, wp1, 0x8000     # rbX = 0x0000_ffff_8000_0000（exit port）
st.o   rdY, rbX, 0          # 写 8B → 立即 halt，退出码 = rdY 低字节
```
`rd` 初值**不得假定为 0**（ADR-0009 教训）⇒ 须用 `set.zw` 显式初始化。

**llvm-mc 汇编命令**：

```bash
LLVM_MC=.work/build/llvm/bin/llvm-mc
$LLVM_MC --triple=dadao-unknown-elf -filetype=obj -o smoke.o tests/e2e/smoke.s
.work/build/llvm/bin/llvm-objcopy -O binary --only-section=.text smoke.o smoke.bin
```

**QEMU 运行命令**：

```bash
QEMU=.work/build/qemu/qemu-system-dadao
$QEMU -M dadao-m1 -bios tests/scripts/trampoline.bin -kernel smoke.bin \
      -display none -nographic
echo "exit: $?"
```

**lit 固化**：`tests/lit/E2E/` 下每场景一个 `.test`，RUN 行串起 llvm-mc → objcopy → QEMU → 退出码断言；`lit.cfg.py` 配置 `%llvm_mc`/`%llvm_objcopy`/`%qemu`/`%trampoline` 替换变量（形态对齐 `tests/lit/MC/Dadao/lit.cfg.py`）。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-033a-phase4-e2e-smoke.md`（完整转述：背景、3 场景汇编、llvm-mc/objcopy 命令、QEMU 命令、lit 固化、调试指引、约束、验收、完成区、代码级 Architecture Review 的逐指令编码验证）
- DADAO-0628：`tests/scripts/gen_e2e_binary.py`、`tests/scripts/run_e2e.py`、`tests/lit/E2E/`（形态参考，禁止复制正文）
- DADAO-0628：`docs/adr/0004-test-machine.md`（BINARY_BASE、机器内存映射）

## 交付物

- `tests/e2e/smoke_arith.s`、`tests/e2e/smoke_add.s`、`tests/e2e/smoke_jump.s`（v5 助记符重写）
- `tests/lit/E2E/lit.cfg.py` + `tests/lit/E2E/*.test`
- （仅当 `llvm-mc` 尚不能汇编时）临时 raw binary 生成器 + QEMU 运行器作为过渡，并在完成区明确标注为过渡方案
- 完成区附全链路真实输出

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **核心差异 — 必须真正走 MC 路径**：0.4.1 完成区遗留「`llvm-mc` DADAO skeleton 无 `halt`/`add`/`addi`/`jump_i` 定义，绕道 `gen_e2e_binary.py` 手编 raw binary」；v5 依赖 `LLVM-013m` 已交付可汇编 M1 指令的 `llvm-mc`，**本任务以 .s→.o→.bin→QEMU 真实链路为验收**，raw 生成器仅可作过渡并在完成区标注。
2. **助记符**：`addi`→`add.si`（0.5.3 立即数自增/设置语义变化）、`add`→`add.uo`/`add.so`（rrrr）、`jump_i`→`jump-iiii`、**无 `halt` 指令**（`contract-isa.md` §7.5 是「特权 cfx 系统指令 — Excluded from M1」，与停机无关）：退出 = 向 exit port 写 8B `st.o`（ADR-0004 D3），写入后 QEMU 立即 halt（ADR-0011 D1）。
3. **编码**：0.4.1 手推 `0x1904002A` 等；v5 全部由 `llvm-mc` 产生，不手编、不复制。
4. **机器名/路径**：`-M dadao-m1` 等以 `SPEC-006t` ADR 与 `QEMU-021m` 实际为准；QEMU 路径 `.work/qemu/build/`。
5. **lit 变量**：`%qemu`/`%trampoline`/`%objcopy` 以 v5 `INFRA`/`LLVM` 的构建布局配置。
6. **退出码**：以 `SPEC-006t` ADR 的 exit port 协议为准。

## 已知坑 / 结论

摘自 DADAO-0628 DL-033a 完成区与代码级 Architecture Review：

1. **0.4.1 绕道 raw binary**：因 llvm-mc skeleton 无指令定义，用 `gen_e2e_binary.py` 手编。v5 若 `LLVM-013m` 就绪应走真实 MC 路径；若仍不能汇编，须显式记录为遗留，不能假装走了 MC。
2. **逐指令编码验证**：0.4.1 审查手推 addi/add/halt/jump 编码；v5 这些由 `llvm-mc` 产生，验证方式改为「objdump 反汇编回助记符 + QEMU 退出码」。
3. **`jump-iiii` offset 单位**：word（4 bytes），跳转目标 = **当前指令地址** + imm*4（`contract-isa.md` §5.3：`Addr = rb0 + (imms24 << 2)`，`rb0` = 当前指令地址；ADR-0009 补注）。⇒ 跳过紧跟的一条指令用 `jump 2`。**注意**：DADAO-0628 写作「下一条 + imm*4」是**错的**（0628 的 `+1` 偏移不适用 v5）。
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
2. QEMU 执行后退出码符合各场景期望（**成功均为 `0x00`**；按 ADR-0004 D5 分区判定）
3. `llvm-lit tests/lit/E2E/` 全 PASS
4. 全链路命令与真实输出记录在完成区（llvm-mc → objcopy → QEMU → exit code）
5. 未修改 `tests/vectors/isa/*.yaml`
6. 若 `llvm-mc` 无法汇编，完成区必须显式标注遗留并说明过渡方案，不得声称走通 MC 路径
7. **反例门控**（AGENTS.md 强制）：对每条用于验收的断言给出**可达 FAIL 路径**——须亲自注入反例（如把某场景期望退出码由 `0x00` 改为非零、或把 `jump` 偏移改错使其不跳过错误路径、或回退某条指令为 `illi`）并给出**真实 FAIL 输出**；完成区须附反例注入与**还原**证据（`git status`/`git diff` 核对，还原含重建）

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

---

## 下发前预检（2026-09-22，主会话；四项）

**1. 内部一致性** — 发现并订正 4 处（3 处事实错误，均继承自 DADAO-0628）：

| # | 原（错） | 订正 | 依据 |
|---|---|---|---|
| 1 | `QEMU=.work/qemu/build/qemu-system-dadao` | `.work/build/qemu/qemu-system-dadao` | 实测路径（`.work/qemu/build/` 不存在） |
| 2 | 「`halt`→按 §7.5 确定」 | **无 halt 指令**；退出 = 写 exit port 8B `st.o` → 立即 halt | §7.5 = cfx（Excluded）；ADR-0004 D3、ADR-0011 D1 |
| 3 | 「`jump` 目标 = 下一条 + imm*4」 | 「**当前**指令地址 + imm*4」 | §5.3 `rb0` = 当前指令地址；ADR-0009 补注 |
| 4 | 「退出码 = 运算结果」 | **成功 = `0x00`**（guest 内比较后归约） | 用户裁定「甲」；ADR-0004 D5 分区 |

次要订正：`lit.cfg`→`lit.cfg.py`（对齐现有形态）、`llvm-objcopy` 补全路径、`-M <machine>`→`-M dadao-m1`；验收新增第 7 条（反例门控）。

**2. 依赖链实际可用性** — 全部就绪：`LLVM-013m`/`QEMU-021m` 均里程碑；`SPEC-006t` 存在；`llvm-mc` 实测可汇编 M1 指令、`llvm-objcopy`/`qemu-system-dadao` 已构建。**关键发现**：`trampoline.bin` 不提供退出路径 ⇒ smoke `.s` 须自写 exit port（已在任务书给出可复用序列）。

**3. 验收可执行性** — 1–7 条**全部「现在可跑」**，无 BLOCKED。验收 6 为条件性（`llvm-mc` 已可汇编 ⇒ 不需 raw 过渡）。

**4. 与 spec/vectors 一致** — 助记符（`add.si`/`jump`/`st.o`）、§5.3、ADR-0004 D3/D5、ADR-0009 D2/D3 均一致（订正 #2/#3 后）。
