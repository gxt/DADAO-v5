# INTEG-002t: MC↔QEMU 端到端冒烟

**模块**：integ
**项目里程碑**：M1
**依赖**：`LLVM-015m`、`QEMU-021m`、`SPEC-006t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `LLVM-015m` 交付的 `llvm-mc`（DADAO target，能汇编 M1 指令）
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
set.zw rbX, 2, 0xffff       # rbX = 0x0000_ffff_0000_0000（wyde 位置用**数字** 0/1/2/3）
or.w   rbX, 1, 0x8000       # rbX = 0x0000_ffff_8000_0000（exit port）
st.o   rdY, rbX, 0          # 写 8B → 立即 halt，退出码 = rdY 低字节
```
`rd` 初值**不得假定为 0**（ADR-0009 教训）⇒ 须用 `set.zw` 显式初始化。

⚠️ **`wpN` 记法不是合法汇编语法**：`llvm-mc` 对 `wp2`/`wp1`/`wp3` 这类 token **不报错但静默编码为 `wp0`**（实测 `set.zw rb1, wp2, 0xffff` → `4e04ffff`，正确应为 `4e06ffff`；用数字 `2` 则正确）。**必须用数字 0/1/2/3**。该缺陷已由 engineer 在 `INTEG-002t` 发现并报告（见本任务完成区），影响面为零（现有 lit/生成器均未用 `wpN`），处置待用户裁定。

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

1. **核心差异 — 必须真正走 MC 路径**：0.4.1 完成区遗留「`llvm-mc` DADAO skeleton 无 `halt`/`add`/`addi`/`jump_i` 定义，绕道 `gen_e2e_binary.py` 手编 raw binary」；v5 依赖 `LLVM-015m` 已交付可汇编 M1 指令的 `llvm-mc`，**本任务以 .s→.o→.bin→QEMU 真实链路为验收**，raw 生成器仅可作过渡并在完成区标注。
2. **助记符**：`addi`→`add.si`（0.5.3 立即数自增/设置语义变化）、`add`→`add.uo`/`add.so`（rrrr）、`jump_i`→`jump-iiii`、**无 `halt` 指令**（`contract-isa.md` §7.5 是「特权 cfx 系统指令 — Excluded from M1」，与停机无关）：退出 = 向 exit port 写 8B `st.o`（ADR-0004 D3），写入后 QEMU 立即 halt（ADR-0011 D1）。
3. **编码**：0.4.1 手推 `0x1904002A` 等；v5 全部由 `llvm-mc` 产生，不手编、不复制。
4. **机器名/路径**：`-M dadao-m1` 等以 `SPEC-006t` ADR 与 `QEMU-021m` 实际为准；QEMU 路径 `.work/qemu/build/`。
5. **lit 变量**：`%qemu`/`%trampoline`/`%objcopy` 以 v5 `INFRA`/`LLVM` 的构建布局配置。
6. **退出码**：以 `SPEC-006t` ADR 的 exit port 协议为准。

## 已知坑 / 结论

摘自 DADAO-0628 DL-033a 完成区与代码级 Architecture Review：

1. **0.4.1 绕道 raw binary**：因 llvm-mc skeleton 无指令定义，用 `gen_e2e_binary.py` 手编。v5 若 `LLVM-015m` 就绪应走真实 MC 路径；若仍不能汇编，须显式记录为遗留，不能假装走了 MC。
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

**测试结果**：3/3 全 PASS（lit），3/3 反例注入全 FAIL（lit 级 + QEMU 级）

**修改文件**（产出已随 commit `6905930` 提交；返工修改 `lit.cfg.py` 和3个 `.test`，`.s` 不变）：
```
 M tests/lit/E2E/lit.cfg.py          # 返工：加 %e2e_dir 替换变量
 M tests/lit/E2E/smoke_add.test      # 返工：RUN 行引用 .s + timeout
 M tests/lit/E2E/smoke_arith.test    # 返工：RUN 行引用 .s + timeout
 M tests/lit/E2E/smoke_jump.test     # 返工：RUN 行引用 .s + timeout
```
新建文件（已在 `6905930`）：
- `tests/e2e/smoke_arith.s` — 场景 A：add.si 算术
- `tests/e2e/smoke_add.s` — 场景 B：RD 算术+XOR+ORR 比较
- `tests/e2e/smoke_jump.s` — 场景 C：jump-iiii 跳过错误路径
- `tests/lit/E2E/lit.cfg.py` — lit 配置（含 `%e2e_dir`）
- `tests/lit/E2E/smoke_arith.test` — 场景 A lit 测试（引用 `.s`）
- `tests/lit/E2E/smoke_add.test` — 场景 B lit 测试（引用 `.s`）
- `tests/lit/E2E/smoke_jump.test` — 场景 C lit 测试（引用 `.s`）

**验收结果**：

1. **场景 A 全链路**（add.si 算术→cmp.so 比较→退出码 0x00）：
```
$ .work/build/llvm/bin/llvm-mc --triple=dadao-unknown-elf -filetype=obj tests/e2e/smoke_arith.s -o /tmp/smoke_arith.o
$ .work/build/llvm/bin/llvm-objcopy -O binary --only-section=.text /tmp/smoke_arith.o /tmp/smoke_arith.bin
$ .work/build/qemu/qemu-system-dadao -M dadao-m1 -bios tests/scripts/trampoline.bin -kernel /tmp/smoke_arith.bin -display none -nographic
QEMU 11.1.1 monitor - type 'help' for more information
(qemu)
qemu-system-dadao: warning: Blocked re-entrant IO on MemoryRegion: dadao-exit-port at addr: 0x0
$ echo $?
0
```

2. **场景 B 全链路**（set.zw×2 + add.si + xor.o + or.o + br.nz→退出码 0x00）：
```
$ .work/build/qemu/qemu-system-dadao -M dadao-m1 -bios tests/scripts/trampoline.bin -kernel /tmp/smoke_add.bin -display none -nographic
QEMU 11.1.1 monitor - type 'help' for more information
(qemu)
qemu-system-dadao: warning: Blocked re-entrant IO on MemoryRegion: dadao-exit-port at addr: 0x0
$ echo $?
0
```

3. **场景 C 全链路**（jump-iiii 跳过错误路径→退出码 0x00）：
```
$ .work/build/qemu/qemu-system-dadao -M dadao-m1 -bios tests/scripts/trampoline.bin -kernel /tmp/smoke_jump.bin -display none -nographic
QEMU 11.1.1 monitor - type 'help' for more information
(qemu)
qemu-system-dadao: warning: Blocked re-entrant IO on MemoryRegion: dadao-exit-port at addr: 0x0
$ echo $?
0
```

4. **llvm-lit 全 PASS**（`.test` 消费 `.s` 文件）：
```
$ .work/build/llvm/bin/llvm-lit tests/lit/E2E/ -v
-- Testing: 3 tests, 3 workers --
PASS: DADAO-E2E :: smoke_jump.test (1 of 3)
PASS: DADAO-E2E :: smoke_arith.test (2 of 3)
PASS: DADAO-E2E :: smoke_add.test (3 of 3)
Testing Time: 0.05s
Total Discovered Tests: 3
  Passed: 3 (100.00%)
```

5. **未修改 `tests/vectors/isa/*.yaml`**（`git diff --name-only tests/vectors/` 为空）

6. **反例门控**（3 组注入到 `tests/e2e/*.s`，lit 级验证）：

**CE-A**：`tests/e2e/smoke_arith.s` 的 `add.si rd1, 7`→`add.si rd1, 8`（算术结果错→比较失败）：
```
$ sed -i 's/add.si  rd1, 7/add.si  rd1, 8/' tests/e2e/smoke_arith.s
$ .work/build/llvm/bin/llvm-lit tests/lit/E2E/smoke_arith.test -v
FAIL: DADAO-E2E :: smoke_arith.test (1 of 1)
Exit Code: 1
error: command failed with exit status: 1
lit exit: 1
```

**CE-B**：`tests/e2e/smoke_jump.s` 的 `jump 2`→`jump 1`（偏移错→落在 Lfail）：
```
$ sed -i 's/jump    2/jump    1/' tests/e2e/smoke_jump.s
$ .work/build/llvm/bin/llvm-lit tests/lit/E2E/smoke_jump.test -v
FAIL: DADAO-E2E :: smoke_jump.test (1 of 1)
Exit Code: 1
error: command failed with exit status: 1
lit exit: 1
```

**CE-C**：`tests/e2e/smoke_add.s` 的 `set.zw rd2, 0, 55`→`56`（XOR 非零→FAIL）：
```
$ sed -i 's/set.zw  rd2, 0, 55/set.zw  rd2, 0, 56/' tests/e2e/smoke_add.s
$ .work/build/llvm/bin/llvm-lit tests/lit/E2E/smoke_add.test -v
FAIL: DADAO-E2E :: smoke_add.test (1 of 1)
Exit Code: 1
error: command failed with exit status: 1
lit exit: 1
```

**还原证据**：注入后 `cp` 还原备份，验证：
```
$ git diff tests/e2e/   # 空 = .s 已还原
$ .work/build/llvm/bin/llvm-lit tests/lit/E2E/ -v   # 3/3 PASS
```

7. **timeout 生效验证**：死循环 `.s`（`jump 0` 自环）→ `timeout 3` 杀 QEMU → exit=124：
```
$ timeout 3 .work/build/qemu/qemu-system-dadao -M dadao-m1 -bios tests/scripts/trampoline.bin -kernel /tmp/opencode/INTEG-002t/deadloop.bin -display none -nographic
QEMU 11.1.1 monitor - type 'help' for more information
(qemu)
$ echo $?
124
```
→ timeout 生效，lit 不会无限挂起。

**新发现/坑**：

1. **`st.o rd0, rbX, 0` 触发 ILLI**：contract-isa §4.1.1 legality 规定 `rdha != rd0`，QEMU `trans_st_o_rd()` 对 ha==0 调用 `gen_exception_illegal()`。**不能用 rd0 作为 st.o 的源寄存器写 0 到 exit port**。必须用其他寄存器（如 cmp/xor 结果寄存器，其值为 0）。
2. **llvm-mc AsmParser wpN 命名常量 bug**：`set.zw rbX, wp2, imm` 中 `wp2`/`wp1`/`wp3` 均被静默忽略，实际编码为 wp0。必须使用**数字**（`set.zw rb3, 2, 0xffff`）。已发现并记录，不影响本任务（已用数字绕过）。
3. **jump-iiii 偏移计算**：`jump 2` 从当前指令地址 +8，跳过紧跟1条指令。需仔细计算布局确保跳转目标正确。
4. **QEMU exit port "Blocked re-entrant IO" 警告**：exit port 写触发 `cpu_loop_exit()` 后 QEMU stderr 输出 `warning: Blocked re-entrant IO on MemoryRegion: dadao-exit-port at addr: 0x0`，但退出码仍正确（0x00）。不影响功能。

**遗留问题**：

1. **llvm-mc wpN 命名常量 bug**（新发现 #2）：需报告给 LLVM 模块并修复 AsmParser。本任务已用数字值绕过。
2. 无其他遗留。

## 审阅记录

### 第 1 轮 reviewer 验收（2026-09-22，reviewer 子代理）

**审查对象**：commit `6905930` 中的 `tests/e2e/*.s`（3）、`tests/lit/E2E/{lit.cfg.py,*_*.test}`（4）。
**工作树状态**：`git status` 干净（产出已提交；非「未提交工作区」）。

#### 一、重跑记录（全部为 reviewer 亲自执行）

**(1) 全链路（3 场景，`$?` 为 `timeout` 传递的真实退出码）**

```
########## smoke_arith ##########   mc exit=0  objcopy exit=0  bin=44B  qemu exit=0
########## smoke_add   ##########   mc exit=0  objcopy exit=0  bin=48B  qemu exit=0
########## smoke_jump  ##########   mc exit=0  objcopy exit=0  bin=32B  qemu exit=0
（三场景 stderr 均出现：qemu-system-dadao: warning: Blocked re-entrant IO on MemoryRegion: dadao-exit-port at addr: 0x0）
```
→ 三场景 `$?` 均为 `0x00`，**与 engineer 自报一致**。

**(2) objdump 反汇编核对（`--triple=dadao-unknown-elf`）**

```
smoke_arith.o: 0:set.zw rb3,2,0xffff  4:or.w rb3,1,0x8000  8:set.zw rd1,0,42  c:add.si rd1,7
              10:set.zw rd2,0,49  14:cmp.so rd3,rd1,rd2  18:br.nz rd3,2→(0x18+8=0x20=Lfail)
              1c:st.o rd3,rb3,0  20:Lfail: set.zw rd4,0,1  24:st.o rd4,rb3,0  28:swym 0
smoke_add.o  : 10:add.si rd1,-45  14:xor.o rd3,rd1,rd2  18:or.o rd3,rd3,rd0
              1c:br.nz rd3,2→(0x1c+8=0x24=Lfail)  20:st.o rd3,rb3,0  24:Lfail ...
smoke_jump.o : 10:jump 2→(0x10+8=0x18=Lpass)  14:Lfail: st.o rd4,rb3,0  18:Lpass: st.o rd5,rb3,0
```
→ 所有 `br.nz`/`jump` 偏移 2 的落点与标签一致；`jump` 基址确认为**当前指令地址**（反例 CE-B 证伪了「下一条基址」）。

**(3) `llvm-lit tests/lit/E2E/ -v`**

```
-- Testing: 3 tests, 3 workers --
PASS: DADAO-E2E :: smoke_arith.test (1 of 3)
PASS: DADAO-E2E :: smoke_add.test (2 of 3)
PASS: DADAO-E2E :: smoke_jump.test (3 of 3)
  Passed: 3 (100.00%)      lit exit=0
```
→ 3/3 PASS，退出码 0。lit 输出确认 `test_exec_root = .work/build/llvm/test-output/DADAO-E2E`（在构建树、`.work/` 已 gitignore，未污染源码树）。

**(4) 退出码传播机制（独立再验）**：写 `0x00/0x01/0x02/0x7F/0xFF` → `rc=0/1/2/127/255`，忠实传播。与 ADR-0004 D3/D5 一致。
> 注：reviewer 首次用 `echo "... $(printf %02x $v) ... $?"` 取值被命令替换覆盖成假 0，已改为先 `rc=$?` 再打印；此处为纠错后的真实值。

**(5) 回归**：
- `make check` → `manifest validation: PASS` / `validate_vectors: 178/178 ... cases 747` / `spec drift check: PASS` / `repository checks: PASS`，**exit=0**。
- `llvm-lit tests/lit/MC/Dadao/` → **17/17 PASS**，exit=0。
→ 本任务未引入回归。

#### 二、反例门控（reviewer 亲自注入，共 4 组；仓库内注入后 `git checkout` 还原）

| # | 注入内容 | 真实 FAIL 输出 | 还原 |
|---|---|---|---|
| CE-A | `tests/lit/E2E/smoke_arith.test`：期望 `49`→`50` | `FAIL: DADAO-E2E :: smoke_arith.test`，`Exit Code: 1`，`error: command failed with exit status: 1`；`Passed: 2 (66.67%) Failed: 1`，`lit exit=1` | `git checkout` 后 `md5sum -c` = OK |
| CE-B | `tests/lit/E2E/smoke_jump.test`：`jump 2`→`jump 1` | `FAIL: DADAO-E2E :: smoke_jump.test`，`Exit Code: 1`，`lit exit=1` | `git checkout` 后 OK |
| CE-C | 临时副本 `smoke_arith.s`：`add.si rd1, 7`→`8` | 原始 QEMU `qemu exit=1` | 仅 `/tmp` 副本 |
| CE-D | 临时副本 `smoke_add.s`：`add.si rd1, -45`→`-44` | 原始 QEMU `qemu exit=1` | 仅 `/tmp` 副本 |

- **可达 FAIL 路径**：3 个 `.s`/`.test` **全文件逐条**核对——PASS 支写的值 ≠ FAIL 支写的值（arith：PASS `st.o rd3`(=0) vs FAIL `st.o rd4`(=1)；add 同构；jump：PASS `rd5`(0) vs FAIL `rd4`(1)），**无「两支写同一结果」/「断言恒真」结构**。
- **分支极性/偏移**：`br.nz` 目标标签指向 FAIL 支、`jump 2` 落点为 PASS 支，均由 objdump + CE-A/CE-B 双向验证。
- **还原证据**：审查后 `git status --porcelain` 空、`git diff --name-only` 空、`md5sum -c baseline` 全部 OK；所有临时产物在 `/tmp/opencode/INTEG-002t-review/`，未污染仓库。

#### 三、`wpN` 缺陷独立验证（engineer 发现 #2）

```
set.zw rb1, wp0, 0xffff → 4e04ffff     set.zw rb1, 0, 0xffff → 4e04ffff
set.zw rb1, wp1, 0xffff → 4e04ffff     set.zw rb1, wp2, 0xffff → 4e04ffff
set.zw rb1, wp3, 0xffff → 4e04ffff     set.zw rb1, 2, 0xffff → 4e06ffff
```
→ **属实**：`wp0/wp1/wp2/wp3` 全部静默编码为 wyde0（`4e04ffff`），无 warning；数字 `2` 正确（`4e06ffff`）。
- 产出文件仅用数字 wyde 位置（`set.zw rb3, 2, ...` / `or.w rb3, 1, ...` / `rwii 0`），未依赖 `wpN`。
- engineer「影响面为零」经核对**基本成立**：仓库内 `wpN` 仅出现在注释/README，实际生成器（`gen_trampoline.py`/`build_test_binary.py`/`min_rom_probe_*.py`）均传数字。

#### 四、engineer 发现 #1 独立验证

`st.o rd0, rb3, 0`：llvm-mc 不报错（mc exit=0），运行期 QEMU **exit=136（0x88=ILLI）**；对照 `st.o rd5`(rd5=0) exit=0。→ **属实**。

#### 五、逐条验收核验

| # | 验收项 | 结论 | 证据 |
|---|---|---|---|
| 1 | 3 `.s` 经 llvm-mc（非 raw）汇编 + objcopy 提取 `.text` | ✅ | mc exit=0；objdump 反汇编出合法助记符；bin 44/48/32 B |
| 2 | QEMU 退出码符合期望（成功 `0x00`） | ✅ | 三场景 `$?`=0；退出码传播 0x00/01/02/7F/FF→0/1/2/127/255 |
| 3 | `llvm-lit tests/lit/E2E/` 全 PASS | ✅ | 3/3 PASS，exit=0 |
| 4 | 全链路命令与真实输出记录在完成区 | ✅（轻微保真问题） | 记录存在且退出码正确；但转录为 stdout-only，省略了 stderr 的「Blocked re-entrant IO」警告（该警告已在「新发现/坑 #4」记录，非隐瞒） |
| 5 | 未修改 `tests/vectors/isa/*.yaml` | ✅ | `git status` 空；commit 6905930 stat 不含 vectors |
| 6 | （条件性）raw 过渡标注 | ✅ N/A | llvm-mc 可汇编，无 raw 过渡 |
| 7 | 反例门控 + 还原证据 | ✅ | CE-A/B/C/D 全 FAIL（见二）；还原后工作树干净 |

#### 六、非阻断观察（不影响本轮判决）

1. **lit RUN 行无 `timeout`**：`smoke_*.test` 第 3 条 RUN 直接调 `%qemu`；若 guest hang（如跳转错误落入死循环），lit 会**无限挂起**而非 FAIL。建议加 `timeout 10`（前置 `%timeout` 替换或直接写 `timeout 10`）。
2. **`tests/e2e/*.s` 未被任何测试引用**：lit `.test` 内联了等价汇编（`%s` = `.test` 自身），与 `.s` 是重复副本。经逐指令比对二者指令序列一致，但 `.s` 若被改动不会被门控捕获。建议 RUN 行改为汇编 `tests/e2e/<scene>.s`，或加一致性检查。
3. **完成区 git 证据过期**：完成区写 `?? tests/e2e/`，但产出已随 6905930 提交；另 CE1/CE2/CE3 命令以 `| ...` 省略，可复现性弱于实际注入记录。属记录保真，非实现缺陷。

#### 判决

**Accepted** —— 验收 1–7 在 reviewer 独立重跑下**全部通过**；4 组反例注入均产生真实 FAIL，无恒真断言/极性偏移错误；`wpN` 与 `st.o rd0` 两条发现经独立复现属实；`make check` 与 MC lit 无回归；仓库无污染。上述六节为非阻断改进建议，可留作后续（如接入 `make check`、补 `timeout`、去重 `.s`）。

### 第 2 轮 reviewer 验收（2026-09-22，reviewer 子代理）— 针对返工（`%e2e_dir` + `timeout`）

**审查对象**：工作区未提交改动 `M tests/lit/E2E/lit.cfg.py`、`M tests/lit/E2E/smoke_{arith,add,jump}.test`；`.s` 与 vectors 未动。
**工作树状态（real）**：`M` 4 个（lit 配置/`.test`）+ 任务书 md；`tests/e2e/*.s` md5 与第 1 轮完全一致（`f498d4b…`/`cfaadb1…`/`3b8121e…`）。

#### 一、`.test` 是否真正消费 `.s`（因果链验证）

- `grep -rn "e2e_dir" tests/lit/E2E/*.test` → 3 个 `.test` 第 1 行均命中 `%e2e_dir/smoke_*.s`。
- 3 个 `.test` 去注释后**无任何汇编体**（`awk 'NF&&$1!="#"'` 输出为空）。
- `llvm-lit tests/lit/E2E/smoke_arith.test -a` 的 executed command 证实真实消费仓库 `.s`：
```
/mnt/tao/DADAO-v5/.work/build/llvm/bin/llvm-mc ... /mnt/tao/DADAO-v5/tests/e2e/smoke_arith.s -o ...
# executed command: timeout 30 /mnt/tao/DADAO-v5/.work/build/qemu/qemu-system-dadao -M dadao-m1 ...
```
- **因果链成立**：改坏 `.s` → lit FAIL（见二，CE-1/2/3 均在 `.s` 级注入并 FAIL）。

#### 二、重跑与反例注入（reviewer 亲自执行）

**(1) `llvm-lit tests/lit/E2E/ -v`**
```
-- Testing: 3 tests, 3 workers --
PASS: DADAO-E2E :: smoke_arith.test (1 of 3)
PASS: DADAO-E2E :: smoke_jump.test (2 of 3)
PASS: DADAO-E2E :: smoke_add.test (3 of 3)
  Passed: 3 (100.00%)      lit exit=0
```

**(2) 反例注入（全部注入 `tests/e2e/*.s`，注入后 `git checkout` 还原）**

| # | 注入 | 真实 FAIL 输出 | 还原 |
|---|---|---|---|
| CE-1 | `smoke_arith.s`：`add.si rd1, 7`→`8` | `FAIL: DADAO-E2E :: smoke_arith.test`，`Exit Code: 1`，`error: command failed with exit status: 1`；`Passed 2 / Failed 1`，`lit exit=1` | `git checkout` 后 md5 OK |
| CE-2 | `smoke_jump.s`：`jump 2`→`jump 1` | `FAIL: DADAO-E2E :: smoke_jump.test`，`Exit Code: 1`，`lit exit=1` | 同上 |
| CE-3 | `smoke_add.s`：比较目标 `set.zw rd2, 0, 55`→`56` | `FAIL: DADAO-E2E :: smoke_add.test`，`Exit Code: 1`，`lit exit=1` | 同上 |

**还原证据**：注入全部经 `git checkout -- tests/e2e/<f>.s`；随后 `git status --porcelain -- tests/e2e/` 空、`md5sum -c baseline-r2` 中 `smoke_*.s` 全 OK。反例期间**未触碰** `.test`/`.s` 之外的文件。

**(3) `timeout` 真生效（防挂起）**
```
(a) raw: 死循环 jump 0 → $ timeout 3 qemu ... ; rc=124   elapsed=3s
(b) lit 级: 仓库内 smoke_jump.s jump 2→0，$ llvm-lit tests/lit/E2E/smoke_jump.test -v
    FAIL: DADAO-E2E :: smoke_jump.test
    Exit Code: 124
    # | qemu-system-dadao: terminating on signal 15 from pid ... (timeout)
    # error: command failed with exit status: 124   lit exit=1  elapsed=30s
```
→ lit 级 `timeout 30` 在 30s 后以 **FAIL(124)** 结束，**不再无限挂起**；死循环仅存在于注入期间，已 `git checkout` 还原（md5 OK）。

**(4) 回归**：`llvm-lit tests/lit/MC/Dadao/` **17/17 PASS**（exit=0）；`make check` → manifest/vectors(178/178)/spec-drift/repository 全 PASS，**exit=0**；`git diff --name-only -- tests/vectors/isa/` 空。

#### 三、完成区与真实输出一致性核对（逐条）

| 完成区条目 | 核对结论 |
|---|---|
| 「3/3 lit PASS」「3/3 反例全 FAIL」 | ✅ 与 reviewer 重跑一致 |
| 「修改文件 `M lit.cfg.py` + 3 `.test`，`.s` 不变」 | ✅ 与真实 `git status --porcelain` 一致（另含任务书 md，属预期） |
| 全链路记录**含 stderr 警告原文**（`warning: Blocked re-entrant IO on MemoryRegion: dadao-exit-port at addr: 0x0`） | ✅ 三场景均已内含，与 reviewer 实测 stderr 逐字一致（第 1 轮该缺口已修复） |
| `llvm-lit` 输出块 | ✅ 计数/百分比一致（worker 顺序与 reviewer 不同属正常非确定性） |
| 未修改 vectors | ✅ |
| CE-A/B/C 注入命令与 FAIL 输出（`.s` 级） | ✅ 与 reviewer 独立注入（CE-1/2/3）逐条一致 |
| CE 还原证据 | ✅ 方向正确（`cp` 备份还原 + `git diff` 空 + 3/3 PASS）；本项 reviewer 已独立复核 |
| timeout 生效（raw `timeout 3`→124） | ✅ reviewer 另补 lit 级 124 证据 |

#### 四、逐条验收核验（1–7）

| # | 验收项 | 结论 | 证据 |
|---|---|---|---|
| 1 | 3 `.s` 经 llvm-mc（非 raw）+ objcopy 提取 `.text` | ✅ | `-a` 显示 RUN 行汇编仓库 `.s`；bin 44/48/32 B |
| 2 | QEMU 退出码符合期望（成功 `0x00`） | ✅ | 三场景 `$?`=0（第 1 轮已验；`.s` 未变，md5 一致） |
| 3 | `llvm-lit tests/lit/E2E/` 全 PASS | ✅ | 3/3 PASS，exit=0 |
| 4 | 全链路命令与真实输出记录在完成区 | ✅ | 含 stderr 警告原文；退出码正确 |
| 5 | 未修改 `tests/vectors/isa/*.yaml` | ✅ | `git diff --name-only` 空 |
| 6 | （条件性）raw 过渡标注 | ✅ N/A | llvm-mc 可汇编 |
| 7 | 反例门控 + 还原证据 | ✅ | CE-1/2/3（`.s` 级）全 FAIL；timeout 生效；还原后工作树干净 |

#### 五、残留缺陷 / 可疑点

- **无阻断项。** 第 1 轮 3 条非阻断观察中，#1（缺 `timeout`）、#2（`.s` 未被消费）、#3（完成区 git 证据过期）**均已修复并独立复核通过**。
- 极轻微（不影响判决，酌情后续）：完成区第 2/3 场景的全链路仅列 QEMU 命令（未重列 mc/objcopy，场景 A 已示全链）；`timeout 30` 的 lit 级证据由 reviewer 补齐（完成区仅列 raw 证据）。`timeout` 为 coreutils 外部命令，属常规依赖。

#### 判决

**Accepted** —— 返工完整有效：`.test` 已真正消费 `tests/e2e/*.s`（因果链经注入证伪成立），`timeout 30` 在 lit 级确认生效（FAIL 124，不挂起），3 组 `.s` 级反例全 FAIL 且已还原，完成区与真实输出逐条对齐，`make check`/MC lit/vectors 无回归，工作区无污染。

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

**2. 依赖链实际可用性** — 全部就绪：`LLVM-015m`/`QEMU-021m` 均里程碑；`SPEC-006t` 存在；`llvm-mc` 实测可汇编 M1 指令、`llvm-objcopy`/`qemu-system-dadao` 已构建。**关键发现**：`trampoline.bin` 不提供退出路径 ⇒ smoke `.s` 须自写 exit port（已在任务书给出可复用序列）。

**3. 验收可执行性** — 1–7 条**全部「现在可跑」**，无 BLOCKED。验收 6 为条件性（`llvm-mc` 已可汇编 ⇒ 不需 raw 过渡）。

**4. 与 spec/vectors 一致** — 助记符（`add.si`/`jump`/`st.o`）、§5.3、ADR-0004 D3/D5、ADR-0009 D2/D3 均一致（订正 #2/#3 后）。

---

## 验收结论（2026-09-22，主会话；reviewer 两轮独立验收）

**判决**：**Accepted**（第 1 轮 Accepted 但主会话指出 2 项 → 返工 → 第 2 轮 Accepted）。

**全链路（reviewer 亲自重跑）**：3 场景 `.s` → `llvm-mc --triple=dadao-unknown-elf -filetype=obj` → `llvm-objcopy -O binary --only-section=.text` → `qemu-system-dadao -M dadao-m1 -bios trampoline.bin -kernel <bin>` → 退出码均 **`0x00`** ✓（成功 = `0x00`，按 ADR-0004 D5 分区）。

**返工项（主会话发现）**：
1. `.test` 原**自行内联汇编**，`tests/e2e/*.s` 未被任何测试引用（死文件）⇒ 改为 RUN 行汇编 `%e2e_dir/smoke_*.s`（`lit.cfg.py` 加 `%e2e_dir`）✓；
2. RUN 行缺 `timeout` ⇒ 加 `timeout 30`（reviewer 实测死循环 → lit 级 `Exit Code: 124`，30s FAIL 而非挂起）✓。

**反例门控（reviewer 亲自注入 `.s`）**：CE-1（`smoke_arith.s` `add.si 7→8`）/CE-2（`smoke_jump.s` `jump 2→1`）/CE-3（`smoke_add.s` 比较目标 `55→56`）均 `Exit Code: 1`、`lit exit=1`；还原证据（`git status --porcelain` 空 + `md5sum -c`）✓。

**命令核验**：`llvm-lit tests/lit/E2E/` **3/3**；`llvm-lit tests/lit/MC/Dadao/` 17/17（无回归）；`make check` PASS；`tests/vectors/isa/*.yaml` 未改 ✓。

**engineer 发现（另行处置）**：`llvm-mc` 把 `wpN` 静默编码为 `wp0` ⇒ 已新建 **`LLVM-013t`** 修复（已 `已验证`）；`st.o rd0` → ILLI（符合 §4.1.1 legality，预期）。

**结论**：置 `已验证`。
