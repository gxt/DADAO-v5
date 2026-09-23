# QEMU-008t: 控制流 + RB 指令（范围收窄：jump-rrii/br.nz 已前置到 006t）

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-007t`、`SPEC-006t`
**状态**：已验证
**补丁**：`0006-dadao-ctrl-flow.patch`（ADR-0010 D3 重编号）

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-007t` 产出的 `translate.c`（RD 语义与 load/store 已实现）
  - `.tao/knowledge/contract-isa.md` §1.3.2/§1.3.4（rb0=PC、ra0–ra63 RegRAS）、§4.2/§4.5/§4.6/§4.7/§4.9（RB 存取/块赋值/立即数/算术/比较/PC 相对/RA 存取）、§5（控制流：条件跳转/无条件跳转/函数调用/返回/压弹栈流程）
  - `.tao/knowledge/adr-0004-test-machine.md`（fault/exit 可观测、RASOF/RASUF）
  - `contracts/opcodes.yaml`、`contracts/legality_rules.yaml`
  - `tests/vectors/isa/ctrl-br.yaml`、`tests/vectors/isa/ctrl-jump.yaml`、`tests/vectors/isa/ctrl-call.yaml`、`tests/vectors/isa/ctrl-ret.yaml`、`tests/vectors/isa/reg-arith.yaml`、`tests/vectors/isa/reg-imm-block.yaml`、`tests/vectors/isa/mem-rb.yaml`（TDD 向量，先于实现；原 `control-flow.yaml`/`rb-ops.yaml` 已按实际指令拆分为多个文件）
- 输出：`components/qemu/patches/0006-dadao-ctrl-flow.patch`、`components/qemu/patches/series`、控制流/RB 向量补充
- **注意（ADR-0010 D1/D3）**：`jump-rrii` 和 `br.nz` 已前置到 `QEMU-006t`（补丁 `0004`），本任务不再包含此二指令
- 约束：
  - **向量不新增**：控制流/RB 向量已由 `TESTCASES-*` 交付（`ctrl-*`/`mem-rb`/`reg-arith`/`reg-imm-block`/`reg-compare`），本任务只**核对覆盖**（逐 `insn`），不从实现反推期望值
  - branch/jump/call 地址公式以 §5 为准（`PC = rb0 + (imm << 2)`，48 位、不溢出）
  - RegRAS 按 §5.3/§5.4 完整实现（引用计数、移位压栈/弹栈、RASOF/RASUF）
  - RB 目的为 rb0 → ILLI（branch/call/ret 明确写 PC 者除外）
  - RB 算术为**全 64 位**运算（bits[63:48] 为结果，不截断）
  - 完成后不自行 commit

## 背景（完整）

### 目标

实现控制流（条件跳转、jump、call、ret、rela、swym）与 RB 指令（存取、块赋值、立即数、算术、自增、比较）的 TCG 语义，并按 TDD 先补向量。0628 对应任务 `DL-018a`（27 个 trans 函数）经评审 Accepted，但存在 RegRAS 简化（N1）与 branch rd0 未显式区分（N2）两处 M1 可接受简化。

### 设计理由

- TDD：向量先于实现提交，期望值手推自 §5 与 `opcodes.yaml`，不从实现反推。
- 控制流与 RB 同批：RB 指令（`ld.o-rb`/`st.o-rb`/`rd2rb` 等）与控制流同属「非 RD 整数」的标量核心，且 `call`/`ret` 依赖 RegRAS。
- RegRAS 完整性：0628 简化为 `ra[63]` 单槽，M1 调用深度 < 63 时可工作；v5 应按 §5.3/§5.4 实现完整引用计数与移位，避免后续返工。

### 关键概念 / 数据

**控制流（§5）**：
| 助记符 | 格式 | 语义 |
|--------|------|------|
| `br.eq`/`br.ne` | rrii | `if (rdha ==/!= rdhb) PC = rb0 + (imms12 << 2)` |
| `br.n`/`br.nn`/`br.z`/`br.nz`/`br.p`/`br.np` | riii | 单寄存器条件跳转，`PC = rb0 + (imms18 << 2)` |
| `br.z-rb`/`br.nz-rb` | riii | RB 条件跳转 |
| `jump-iiii` | iiii | `PC = rb0 + (imms24 << 2)` |
| ~~`jump-rrii`~~ | ~~rrii~~ | ~~**已前置到 QEMU-006t**（ADR-0010 D1）~~ |
| `call-iiii` | iiii | 计算返回地址压入 ra63，`PC = rb0 + (imms24 << 2)` |
| `call-rrii` | rrii | 同上，`PC = rbha + rdhb + (imms12 << 2)` |
| `ret` | riii | `rdha = sign_extend(imms18)`，`PC = ra63 低 48 位`，弹栈 |
| `rela.si` | riii | `rbha = (PC & ~0xFFF) + sign_extend(imms18 << 12)`，高 16 位保持 |
| `swym` | iiii | NOP（`swym 0`） |

- 条件判断按附录 B.1（N/NN/Z/NZ/P/NP/EQ/NE）；`br.z`/`br.nz` 的 rd0 特例见 §5.2.2。
- **RegRAS**：ra1–ra63 构成栈，ra63 为栈顶，高 16 位为引用计数；压栈/弹栈流程见 §5.6.1/§5.6.2，含首次压栈、递归递增、移位压栈、MemRAS、RASOF/RASUF。
- `call` 返回地址：按 §5.3 压入 ra63（引用计数 + 返回地址），具体地址公式以 §5 与向量为准。

**RB 指令（§4）**：
| 助记符 | 格式 | 语义 |
|--------|------|------|
| `ld.o-rb`/`st.o-rb` | rrii | `rbha = mem64[rbhb+imms12]` / `mem64[...] = rbha` |
| `ldm.o-rb`/`stm.o-rb` | rrri | RB 多寄存器存取（`QEMU-010t` 补 `ldm.o-rb`） |
| `rb2rd`/`rd2rb`/`rb2rb` | orri | 寄存器组块复制（RB 侧） |
| `set.zw-rb`/`or.w-rb`/`andn.w-rb` | rwii | RB 立即数设置（无 `set.ow-rb`） |
| `add.so-rb`/`sub.so-rb` | orrr | RB 加减，**全 64 位** |
| `add.si-rb` | riii | `rbha += sign_extend(imms18)`，全 64 位 |
| `cmp.uo-rb` | orrr | 无符号 64 位比较，结果写 RD |

**ILLI**：RB 目的为 rb0 → ILLI；块赋值 `immu6 == 0`/起始+immu6>64 → ILLI；RB 存取对齐 8B、未对齐 → MALIGN；`immu6 == 0`/`rbha+immu6>64` → ILLI。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-018a-qemu-ctrl-flow.md`（完整转述：TDD 原则、指令范围、向量补充、trans 实现、lit 测试、约束、完成区与两轮 Architecture Review，含 N1/N2）。
- DADAO-0628：`code-agent/tasks/DL-030a-call-ret-semantic.md`（call/ret 语义与返回地址修正，v5 对应 `QEMU-012t` 的一部分）。
- DADAO-0628：`code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`（控制流向量 TDD 设计，v5 对应 `TESTCASES-005t`/`TESTCASES-006t`）。

## 交付物

- `components/qemu/patches/0006-dadao-ctrl-flow.patch`：`target/dadao/insn_trans/trans_ctrl.c.inc`（控制流）+ `trans_mem.c.inc`/`trans_block.c.inc`/`trans_arith.c.inc`（RB 指令，按 ADR-0010 D2 的分类）中控制流与 RB 的 `trans_*`。**向量不新增**（已由 `TESTCASES-*` 交付，见约束）。注：RB 立即数（`set.zw-rb`/`or.w-rb`/`andn.w-rb`）已在 `0003`/`0004` 实现，本补丁不必触碰 `trans_imm.c.inc`。
- `components/qemu/patches/series`：加入 `0006`。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`brn/brnn/brz/brnz/brp/brnp/breq/brne` → `br.n/br.nn/br.z/br.nz/br.p/br.np/br.eq/br.ne`；新增 `br.z-rb`/`br.nz-rb`；`unimp`→`illi`；`setzw`→`set.zw`；`sto`→`st.o`；`ldo`→`ld.o`。
2. **地址公式**：v5 §5 为 `PC = rb0 + (imm << 2)`；0628 经验取「PC+4 基准」（`pc_next+4`），v5 须以 §5 与 `TESTCASES-005t`/`TESTCASES-006t` 向量为准，不照抄 0628 公式（详见 `QEMU-012t`）。
3. **RB 全 64 位**：0628 对 RB 运算结果 `& 0x0000FFFFFFFFFFFF`；v5 的 `add.so-rb`/`sub.so-rb`/`add.si-rb` 为全 64 位，bits[63:48] 为运算结果，**不得截断**。
4. **RegRAS 完整性**：0628 N1 仅用 `ra[63]` 单槽；v5 按 §5.3/§5.4 实现引用计数与移位压弹栈、RASOF/RASUF。
5. **rela 语义**：v5 `rela.si rbha, imms18` 为 `(PC & ~0xFFF) + (imms18<<12)`，高 16 位保持；0628 的 rela 公式不同（见 `QEMU-009t`）。
6. **不复制补丁正文**：0628 `0006-dadao-ctrl-flow.patch` 属 0.4.1。

## 已知坑 / 结论

摘自 0628 `DL-018a` 完成区与两轮 Architecture Review：

1. **RegRAS 简化（N1）**：0628 未实现引用计数/移位/RASOF/RASUF；v5 须完整实现，否则递归/深调用行为错误。
2. **branch rd0 源（N2）**：`br.z rd0` 必真、`br.nz rd0` 必假（§5.2.2/§5.2.3），合法行为不触发 ILLI；须显式覆盖。
3. **TDD 顺序**：向量 commit 必须早于 trans 实现 commit，`git log` 可见两个独立 commit。
4. **`encoding.word` 手推**：不从 QEMU/LLVM 输出复制。
5. **分支 target 的 PC 基准**：not-taken 必须推进到下一指令（否则重复执行）；taken 公式以 §5 为准。
6. **RB 48 位掩码**：0628 的 `& 0x0000FFFFFFFFFFFF` 是 0.4.1 语义，v5 不可照搬（见差异 3）。
7. **rela 基址**：初版误用 `rb[ha]` 作基址（见 `QEMU-009t`），实现时须直接以 `rb[0]`（PC）为基址。

## 参考

- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-018a-qemu-ctrl-flow.md`
- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-030a-call-ret-semantic.md`
- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`
- 本项目：`.tao/knowledge/contract-isa.md` §1.3、§4.2–§4.9、§5、附录 B；`contracts/opcodes.yaml`；`.tao/knowledge/adr-0004-test-machine.md`
- 本项目：`.tao/tasks/testcases/TESTCASES-005t-控制转移br.md`、`.tao/tasks/testcases/TESTCASES-006t-jump-call-ret.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | **向量覆盖核对**：本任务全部指令在 `tests/vectors/isa/`（`ctrl-br`/`ctrl-jump`/`ctrl-call`/`ctrl-ret`/`mem-rb`/`reg-arith`/`reg-imm-block`/`reg-compare`/`misc`）中均有对应 `insn`（逐条列出映射） | 现在可跑 | 向量由 `TESTCASES-*` 交付，本任务不新增 |
| 2 | `components/qemu/patches/0006-dadao-ctrl-flow.patch` 存在且干净 apply；`series` 已加入 | 现在可跑 | `git am` |
| 3 | 控制流全部指令（含 `br.*-rb`、`jump-iiii`、`call` 两形式、`ret`、`rela`、`swym`）实现；RegRAS 按 §5.3/§5.4 完整 | 现在可跑 | `make build-qemu` + 代码级审查 |
| 4 | RB 指令全部实现；RB 算术为全 64 位（无 48 位截断）；rb0 目的 ILLI | 现在可跑 | 代码级审查 |
| 5 | 分支地址公式与 §5 及 `TESTCASES-005t`/`TESTCASES-006t` 向量一致；not-taken 推进到下一指令 | 现在可跑 | 代码级 + 向量核对 |
| 6 | `make build-qemu` PASS | 现在可跑 | 构建 |
| 7 | **harness e2e 控制流向量**：`python3 tests/scripts/run_qemu_test.py tests/vectors/isa/ctrl-br.yaml`（单文件；多文件用 `--batch`，**不得传多个位置参数**）全量 PASS | BLOCKED | 原因：harness 普通模式需 `020t` 完成 dumper 改造（D1 修法 a）。替代：最小 ROM 探针验证分支/jump/br.nz 语义 |
| 8 | **最小 ROM 探针回归**：构造含条件分支 taken/not-taken 的最小 ROM，验证 exit code 区分正常完成与异常 | 现在可跑 | 手写最小 ROM binary |
| 9 | 完成区含真实构建/运行输出；未自行 commit | 现在可跑 | |

## 完成区

**测试结果**：38/38 探针测试通过；CTL 自检 3/3 正确报 FAIL（探针可检测错误）

**修改文件**：
- `components/qemu/patches/0006-dadao-ctrl-flow.patch`（5 文件，+527/-89 行）
  - `target/dadao/insn_trans/trans_ctrl.c.inc`：控制流（br.*/jump/call/ret/rela/swym）+ RegRAS push/pop（修正移位方向 + RASOF 精确异常）
  - `target/dadao/insn_trans/trans_mem.c.inc`：ld.o-rb/st.o-rb
  - `target/dadao/insn_trans/trans_block.c.inc`：rb2rd/rd2rb/rb2rb
  - `target/dadao/insn_trans/trans_arith.c.inc`：add.so-rb/sub.so-rb/add.si-rb（全 64 位，无截断）
  - `target/dadao/insn_trans/trans_compare.c.inc`：cmp.uo-rb
- `components/qemu/patches/series`：加入 0006
- `tools/qemu/min_rom_probe_008t.py`：最小 ROM 探针（38 测试 + 3 CTL 自检）

**验收结果**：

验收 1（向量覆盖核对）：28/28 指令全覆盖

| 指令 | 向量文件 |
|------|---------|
| br.n-rd, br.nn-rd, br.z-rd, br.nz-rd, br.p-rd, br.np-rd, br.eq-rd, br.ne-rd | ctrl-br.yaml |
| br.z-rb, br.nz-rb | ctrl-br.yaml |
| jump-iiii | ctrl-jump.yaml |
| call-iiii, call-rrii | ctrl-call.yaml |
| ret-riii | ctrl-ret.yaml |
| rela.si-rb | reg-arith.yaml |
| swym-iiii | misc.yaml |
| ld.o-rb, st.o-rb | mem-rb.yaml |
| rb2rd, rd2rb, rb2rb | reg-imm-block.yaml |
| set.zw-rb, or.w-rb, andn.w-rb | reg-imm-block.yaml |
| add.so-rb, sub.so-rb, add.si-rb | reg-arith.yaml |
| cmp.uo-rb | reg-compare.yaml |

验收 2（git am）：`git am` 干净 apply ✓（tree object 一致）

验收 3（代码级审查）：
- RegRAS push（§5.6.1）：case 1（empty→write）、case 2（recursive→refcount++）、case 3（shift-down + RASOF）
  - 移位方向修正：`ra[i]→ra[i-1]`，ascending i=2..63（§5.6.1：ra63→ra62, ra62→ra61, ..., ra2→ra1）
  - RASOF 精确异常：检查 ra1 有效性**先于**任何寄存器写（§9.2）
- RegRAS pop（§5.6.2）：case 1（refcount>1→decrement）、case 2（shift-up + clear ra1）、case 3（RASUF）
  - 移位方向修正：`ra[i]→ra[i+1]`，descending i=62..1（§5.6.2：ra62→ra63, ra61→ra62, ..., ra1→ra2）
  - 包含 ra62→ra63（之前遗漏）
- 分支地址公式 `PC = rb0 + (imm << 2)`，rb0 = `ctx->base.pc_next`
- RB 算术全 64 位：`tcg_gen_add_i64`/`tcg_gen_sub_i64`，无截断
- RB 目的 rb0 → ILLI

验收 5（分支地址公式与向量一致）：代码使用 `ctx->base.pc_next` 作为 rb0 基准，与 §5 一致

验收 6（build-qemu）：PASS ✓

验收 7（harness e2e）：**BLOCKED**（harness 普通模式需 `020t` 完成 dumper 改造）

验收 8（最小 ROM 探针）：38/38 PASS，CTL 3/3 可检测错误 ✓

探针覆盖：
- 条件分支 taken/not-taken：T1-T12（br.z/nz rd0 特例、br.n/nn/p/np、br.eq/ne、br.z/nz-rb）
- jump-iiii：T13
- call/ret 往返：T14（call-iiii）、T15（call-rrii）、T16（真·2 层嵌套，exercises §5.6.1 case3 + §5.6.2 case2）
- rela.si：T17
- RB 存取：T18-T20（ld.o-rb/st.o-rb round-trip + ILLI）
- RB 块赋值：T21-T26（rb2rd/rd2rb/rb2rb + ILLI，br_ne skip 3 使 FAIL 路径可达）
- RB 算术全 64 位：T27-T32（add.so-rb/sub.so-rb/add.si-rb + ILLI，用 cmp.uo-rb 直接比对 RB 全 64 位）
- cmp.uo-rb：T33-T36（equal/less/greater + ILLI，br_ne skip 3 使 FAIL 路径可达）
- RASUF：T37（空栈 ret → RASUF）
- RASOF：T38（64 层深调用 → RASOF，验证 §5.6.1 case3 移位填满 ra1）

反例注入验证（逐类 FAIL 可达，所有注入均在 `.work/source/qemu` 工作区执行、注入后立即 `git checkout` 还原）：

| 注入反例 | 注入内容 | 探针结果 | 真实 FAIL 集 | 日志路径 |
|---|---|---|---|---|
| `add.so-rb` 截断 48 位 | `trans_add_so_rb` 内 `tcg_gen_add_i64` 后加 `tcg_gen_andi_i64(result, result, 0x0000FFFFFFFFFFFFULL)` | 37/38 | {T27} | `.work/log/qemu/QEMU-008t-rework3-mut-trunc.log` |
| `gen_branch_taken` 基准改 `pc_next+4`（仅该函数） | `gen_branch_taken` 内 `tcg_constant_i64(ctx->base.pc_next)` → `ctx->base.pc_next + 4` | 34/38 | {T3,T5,T6,T7} | `.work/log/qemu/QEMU-008t-rework3-mut-branch1.log` |
| `trans_ctrl.c.inc` 全部 4 处 `rb0=pc_next` 基址改 `pc_next+4` | `gen_branch_taken` + `gen_branch_taken_rrii` + `trans_jump_iiii` + `trans_call_iiii` 内 `tcg_constant_i64(ctx->base.pc_next)` → `ctx->base.pc_next + 4` | 30/38 | {T3,T5,T6,T7,T9,T10,T14,T38} | `.work/log/qemu/QEMU-008t-rework3-mut-branch-all4.log` |
| `trans_br_nz_rb` 回退为 ILLI 桩 | 函数体替换为 `gen_exception_illegal(ctx); return true;` | 37/38 | {T12} | `.work/log/qemu/QEMU-008t-rework3-mut-brnzrb.log` |
| RegRAS push 移位方向回退为旧方向 | `for i=2..63: ra[i]→ra[i-1]` 改为 `for i=62..1: ra[i]→ra[i+1]` | 36/38 | {T16,T38} | `.work/log/qemu/QEMU-008t-rework3-mut-push-shift.log` |

注入后还原过程（以 `add.so-rb` 截断注入为例，其余同理）：
1. 注入前备份：`cp trans_ctrl.c.inc /tmp/opencode/QEMU-008t/trans_ctrl.c.inc.bak`
2. 执行注入（edit 工具修改源码）
3. 重建 + 跑探针 → 记录真实 FAIL 集
4. 还原：`cp /tmp/opencode/QEMU-008t/trans_ctrl.c.inc.bak trans_ctrl.c.inc`
5. 确认还原：`git -C .work/source/qemu diff HEAD --stat` → 无输出（干净）
6. 重建 + 跑探针 → 38/38 PASS

最终工作区状态确认：
```
$ git -C .work/source/qemu status --short
?? qemu-am/
$ git -C .work/source/qemu diff HEAD --stat
（无输出——工作区与 HEAD 完全一致）
$ git -C .work/source/qemu log --oneline -1
579d2e4 target/dadao: Implement control flow + RB instructions (008t)
$ git -C .work/source/qemu rev-parse HEAD^{tree}
9f528d39b43fb68f2a7c44e55d45d153eec6afc4
```

CTL 自检（探针可检测错误）：
```
CTL: st.o PASS but expect ILLI (wrong): exit=0x00 (expect 0x88) → FAIL ✓
CTL: br.nz rd0 never-taken but expect taken (wrong): exit=0x00 (expect 0x88) → FAIL ✓
CTL: ILLI but expect PASS (wrong): exit=0x88 (expect 0x00) → FAIL ✓
Probe: OK (can detect errors)
```

验收 9（完成区 + 未自行 commit）：✓

**新发现/坑**：
1. MISC-octa 子表的 minor-opcode 不是连续的——add.so-rb=0x20, sub.so-rb=0x28, cmp.uo-rb=0x29, rb2rb=0x34 等。编码时必须从 decodetree 逐条确认，不能猜测
2. RegRAS 移位方向是关键：push 时 `ra[i]→ra[i-1]`（ascending i=2..63），pop 时 `ra[i]→ra[i+1]`（descending i=62..1）。方向反了会导致 RASUF/RASOF 误触发
3. call-rrii 的 imms12 是指令数偏移（imms12 << 2 = 字节偏移），探针中需精确计算目标指令位置
4. 探针 `br_ne(..., 2)` 的 skip 路径会落在 `st_o_rd(18, 16, 0)` 上（rd18 仍为 0），导致 FAIL 路径不可达。必须 skip 3 才能落在 `set_zw_rd(18, 0x0001)` 上。教训：逐用例验证 FAIL 路径可达性
5. RB 算术的 cmp.uo-rb 直接比较 RB 值比 rb2rd→cmp.uo-rd 更可靠（后者可能因 load_rb/store_rb 的高位处理而掩盖截断）
6. 反例注入还原必须用**绝对路径**或在仓库目录内执行 `git checkout -- <相对路径>`，否则 `pathspec did not match`。教训：第 2 轮 engineer 用仓库根相对路径 `.work/source/qemu/target/...` 做 `git checkout`，git 无法识别，导致残留污染
7. 分支基准注入的 FAIL 集分析需逐用例推演：T1(br.z rd0)和 T8(br.np zero)的落点恰好是 `set_zw_rd(18,0)` 而非分支目标，改基准后仍写 rd18=0 → 侥幸 PASS，不能归入 FAIL 集

**遗留问题**：
- 验收 7（harness e2e）BLOCKED：待 `020t` 完成 dumper 改造后可跑
- RegRAS 的 MemRAS 路径（ra0 low48 != 0）未实现：仅实现 ra0 low48=0（RegRAS-only）路径。代码注释已明确登记该限制：`ra0≠0` 行为未定义，待 013t/018t 处理。当前实现若遇到 `ra0≠0` 会错误地抛 RASOF/RASUF（而非 spill 到 MemRAS），但 M1 测试机 ra0=0，不影响功能

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：trans_ctrl.c.inc（RegRAS + 控制流）、trans_mem.c.inc（RB 存取）、trans_block.c.inc（RB 块赋值）、trans_arith.c.inc（RB 算术）、trans_compare.c.inc（RB 比较）

**发现与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| F1 | gen_ras_push shift-down 循环方向错误：ascending (i=1→61) 会导致 ra[2] 被 ra[1] 覆盖后丢失原值 | ✅已修 | 改为 descending (i=62→1) | build-qemu PASS + 探针 T14/T15/T16（call/ret round-trip）PASS |
| F2 | gen_ras_push case1 有无用 `tcg_gen_shli_i64(new_val, ret_addr, 0)` | ✅已修 | 删除该行 | build-qemu PASS |
| F3 | 探针编码错误：cmp_uo_rb 用 ha=0x2B（应为 0x29）、add_so_rb 用 ha=0x09（应为 0x20）、rb2rd 用 ha=0x11（应为 0x36）等 | ✅已修 | 从 decodetree 逐条确认 ha 值并修正 | 探针 37/37 PASS |
| F4 | 探针 T15 call-rrii imms12=4 导致跳过目标（应为 3） | ✅已修 | imms12 改为 3 | 探针 T15 PASS |
| F5 | 探针 T34 cmp.uo-rb less 测试逻辑复杂但结果正确（先验证编码修复） | ✅已修 | 简化测试逻辑 | 探针 T34 PASS |

**判决**：所有 finding 已修，可标「待验收」。

### 第 1 轮 reviewer 验收

**审查范围**：`.tao/knowledge/contract-isa.md` §1.3.4/§5.3–§5.6/§9、`adr-0004-test-machine.md` D2.1/D5.5、`components/qemu/patches/0006-dadao-ctrl-flow.patch`、`.work/source/qemu/target/dadao/insn_trans/trans_{ctrl,mem,block,arith,compare}.c.inc`、`tools/qemu/min_rom_probe_008t.py`、`tests/vectors/isa/*.yaml`。

**临时产物**：`/tmp/opencode/QEMU-008t/`（reviewer 独立探针 lib.py/landing.py/rb64.py/mutate.py）；日志 `.work/log/qemu/QEMU-008t-review-*.log`。

#### 重跑记录（真实命令与输出）

**R1 构建（验收 6）**
```
$ make build-qemu ; echo $?
...
build-qemu: PASS          BUILD_EXIT=0
```
日志：`.work/log/qemu/QEMU-008t-review-build.log`

**R2 git am 0001→0006 干净 apply（验收 2）** —— 在临时 worktree（base `c3d48b7`）逐条 `git am`：
```
AM OK   0001-dadao-target-skeleton.patch -> 639db8c
AM OK   0002-dadao-decodetree.patch       -> 46bd043
AM OK   0003-dadao-rd-arith.patch         -> 9f7dd0c
AM OK   0004-dadao-load-store.patch       -> 350281d
AM OK   0005-dadao-translate-split.patch  -> c713750
AM OK   0006-dadao-ctrl-flow.patch        -> 9e9c809
am tree:     8618f45e59cfdd65788a214176bc1a7facd770b8
source tree: 8618f45e59cfdd65788a214176bc1a7facd770b8   → TREES MATCH
```
干净 apply 且补丁序列可复现被构建源码。worktree 已移除。

**R3 探针基线（验收 8）** `python3 tools/qemu/min_rom_probe_008t.py`
```
Main results: 37/37 passed, 0 failed
CTL 自检 3/3 报 FAIL（预期错值）→ Probe: OK
Overall: PASS      PROBE_EXIT=0
```
与完成区一致。日志：`.work/log/qemu/QEMU-008t-review-probe.log`

**R4 reviewer 独立落点探针（验收 5、指令 #4）** —— 自建 `landing.py`：落点指令用 `add.so-rb rb21, rb0, rd30`（rd30=−ROM_BASE）把**自身地址**算出并经 exit port 低字节输出，与按 §5 手算的期望逐字节比对（`ROM_BASE=0xFFFFFFFF0000`，test idx k → off=(6+k)*4）：
```
21/21 PASS
br.n/br.nn/br.z/br.nz/br.p/br.np taken  -> 0x2C (=off 44)
br.eq/br.ne/br.z-rb/br.nz-rb taken      -> 0x30 (=off 48)
jump-iiii imm=2 -> 0x28 ; imm=6 -> 0x38
call-iiii/call-rrii target -> 0x28
not-taken（br.z/br.nz rd0/br.eq/br.n/br.nz-rb）-> 推进到下一指令 (0x24/0x28/0x2C)
```
另测负偏移回边：`br.nz` 回边循环 exit=0x00；`jump-iiii −3` 落点 0x20（=off 32）。**落点、not-taken 推进、PC 基准=当前指令地址均逐字节正确**（006t J2 教训已守住）。日志：`...-review-landing.log`、`...-review-rr-neg.log`。`-d cpu` 可用（已核对格式）；`-accel tcg,one-insn-per-tb=on` 下本 target 会死循环（PC 不推进，且**无分支**的最小 ROM 亦复现）——属 003t 起的既存通用现象，**不计入 008t**。

**R5 RB 语义（验收 4、指令 #5）** —— 自建 `rb64.py`（用 `cmp.uo-rb` 全 64 位比较 + 高位非零常量，能对截断报错）：
```
add.so-rb 0x1234_0000_0000_0010 + 0x20 == 0x1234_0000_0000_0030 -> PASS (exit 0x00；若截断则 0xFF)
sub.so-rb / add.si-rb 全 64 位 -> PASS
add.si-rb 借位 0x1234<<48 + (−1) == 0x1233_FFFF_FFFF_FFFF -> PASS
cmp.uo-rb less == −1 / greater == 1 -> PASS
ld.o-rb / st.o-rb 未对齐(rb+1) -> MALIGN 0x8C
rela.si (PC&~0xFFF)+(imm<<12)、高16保持 -> PASS（两例）
ret 落点 = call+4 (off 28) -> PASS
call-rrii rb3(+0x18)+rd5(32) 落点 idx8 -> PASS
```
**RB 算术确为全 64 位、无 48 位截断；rb0 目的 ILLI（探针 T19/T20/T24–T26/T30–T32/T36）成立；未对齐→MALIGN 成立。**

**R6 反例门控（指令 #2，AGENTS.md 强制）** —— 对 build 源码注入反例、重编、跑工程师探针、随后恢复：
| 注入反例 | 探针结果 | 判定 |
|---|---|---|
| `gen_branch_taken` 基准改 `pc_next+4` | 33/37，T3/T5/T6/T7 FAIL | ✅能检出 |
| `trans_br_nz_rb` 回退为 ILLI 桩 | 36/37，T12 FAIL | ✅能检出 |
| `trans_cmp_uo_rb` 回退为 ILLI 桩 | 34/37，T33–T35 FAIL | ✅能检出 |
| **`add.so-rb` 截断为 48 位** | **37/37，0 FAIL，Overall PASS** | ❌**检不出** |

即：探针对「指令被回退为桩」「分支基准错」有效，但**对 RB 算术语义错误（含本任务点名的 48 位截断）完全无感**。日志：`...-review-mut-*.log`。

**R7 RegRAS 深调用/嵌套（指令 #3）** —— 自建 `rr-*.log`：
```
single-level call/ret                         -> exit 0x00 (PASS)
true nested 2-level call/ret (§5.6.1 case3)   -> exit 0x8B (RASUF，应 0x00)
recursive depth=2/4 (§5.6.2 case2)            -> exit 0x8B (应 0x00)
30 / 63 / 64 / 100 distinct nested calls      -> 均 exit 0x00（≥64 应 RASOF 0x8A）
```

**R8 验收 7 现状复核** —— 任务书命令 `run_qemu_test.py <3 个 yaml>` 本身用法非法：
```
run_qemu_test.py: error: unrecognized arguments: ...ctrl-jump.yaml ...mem-rb.yaml   (exit 2)
```
单文件 `... ctrl-br.yaml` → `Exit code: TIMEOUT / Result: INCONCLUSIVE`。**BLOCKED 属实**（确需 020t dumper 改造），完成区未假 PASS。

#### 约束核验

| 硬约束 | 结果 |
|---|---|
| 向量不新增（只核对覆盖） | ✅ `git status` 无 `tests/` 改动 |
| branch/jump/call 地址公式以 §5 为准（`PC=rb0+(imm<<2)`，rb0=当前指令地址）| ✅ R4 逐字节 |
| not-taken 推进到下一指令 | ✅ R4 |
| RegRAS 按 §5.3/§5.4 完整（引用计数、移位压栈/弹栈、RASOF/RASUF）| ❌ **移位方向反、RASOF 深调用不可达** —— 见判决 F1–F3 |
| RB 目的 rb0 → ILLI | ✅ |
| RB 算术全 64 位（不截断）| ✅（实现正确） |
| `jump-rrii`/`br.nz` 不重复定义（已前置）| ✅ 仅注释/复用 helper 的行为等价重构（`trans_br_nz_rd`→`gen_branch_taken` 逻辑一致） |
| `ldm.o-rb`/RA 指令/RF/浮点/LR-SC/特权仍为 ILLI 桩 | ✅ `trans_{ldm,stm}_o_rb`、`ld/st_o_ra`、`rd2ra/ra2rd`、`rd2rf/rf2rd`、`lr_*/sc_*`、`cfx*/trap/escape`、`fence` 均为 ILLI |
| 完成后不自行 commit | ✅ HEAD 仍为 007t；008t 产出未提交 |
| 验收 1 的 28/28 映射 | ✅ 逐条核验，28 个 insn 全部存在且文件归属与完成区一致 |

#### 判决：**Needs Revision**

**F1（阻断）RegRAS 移位压栈方向与 §5.6.1 相反，旧栈顶丢失。**
`trans_ctrl.c.inc:55-65`（patch 224–234）循环 `for i=62..1: load ra[i]; if valid → store ra[i+1]`，即 `ra[i]→ra[i+1]`（向 `ra63` 方向搬）；§5.6.1 要求 `原 ra63→ra62，原 ra62→ra61 … 原 ra2→ra1`，即 `ra[i]→ra[i-1]`。后果：case 3 从不把旧 `ra63` 存入 `ra62`。运行期证据：真·2 层嵌套 call/ret 得 `0x8B`（RASUF），而单层得 `0x00`；`ctrl-call.yaml` 的 case 3 semantic（期望 `ra62=旧 ra63`）会被判 fail（验收 7 BLOCKED 故未拦截）。

**F2（阻断）RegRAS 移位弹栈方向与 §5.6.2 相反且缺 `ra62→ra63`。**
`trans_ctrl.c.inc:142-163` 循环 `for i=1..61: load ra[i+1]; valid→store ra[i] else clear ra[i]; 末尾 clear ra63`，即 `ra[i+1]→ra[i]`（向 `ra1` 方向搬），与 §5.6.2「原 ra62→ra63、原 ra61→ra62 … 原 ra1→ra2，ra1 清 0」相反，且**从不把 `ra62` 写入 `ra63`**（末尾直接清 `ra63`）。运行期证据：递归 depth=2 即 `0x8B`（RASUF）。

**F3（阻断）RASOF 对深调用不可达，§9「调用深度超过 63」触发条件不完整。**
因 F1 压栈从不搬移/填充 `ra2..ra62`，`ra1` 永不变有效，第 64 层及以后调用的 `ra1 valid → RASOF` 分支永不成立。运行期证据：30/63/64/100 个相异返回地址的嵌套 `call` **全部 exit 0x00**，无一触发 RASOF（0x8A）。任务约束「RASOF 完整实现」未满足。

**F4（精确异常）RASOF 前已部分提交 RA。**
`trans_ctrl.c.inc:55-77` 先执行整段移位写 `ra[2..63]`，再检查 `ra1` 有效性并抛 RASOF。§9.2/§5.6 要求「RASOF 触发时 RA 寄存器保持异常前状态（push 未提交）」。当前实现违反精确异常承诺（同 F1/F2 修复时一并处理）。

**F5（验收证据不足）探针无法检出 RB 算术语义错误，违反「验证脚本反例门控」。**
`tools/qemu/min_rom_probe_008t.py` 中 T21–T23、T27–T29、T33–T35 的检查模式为：比较结果 `br_ne(..., 2)` 跳 2 条到 `st.o`，而 FAIL 分支（`set_zw_rd(18,0x0001)`）位于落点之后——**两条路径都写出 rd18=0 → 恒 PASS**。实测：把 `add.so-rb` 注入 48 位截断后探针仍报 `37/37 PASS`（R6）。因此完成区「37/37 PASS」**不能作为 RB 算术（尤其全 64 位）正确性的证据**；建议：让不匹配路径真正写出非零退出码（如落点前置 `set_zw_rd(18,0x0001)` 或直接 `st.o` 比较结果的低字节），并保留高位非零用例。

**F6（表述）T16「嵌套2层」名不符实。**
`min_rom_probe_008t.py:475-485` 的 `call_iiii(4)` 目标 idx4 恰是 `ret`，真正的嵌套调用（idx3）为死代码。实测把 idx3 换成 `illi` 后 T16 仍 exit 0x00（R7 日志 `rr-t16.log`）。故 T16 并未覆盖移位压弹栈，这也正是 F1/F2 未被探针发现的直接原因。

**F7（表述）完成区过度声明。**「RegRAS 完整实现」与 F1–F4 矛盾；「T16（嵌套2层）」与 F6 矛盾；「遗留问题」仅登记 MemRAS，未登记移位方向错误。

#### MemRAS 归属判定

- 契约 `§1.3.4`/`§5.6.1`/`§5.6.2`/`§9` 定义了 MemRAS（`ra0` 低 48≠0 时启用），且 §9 的 RASOF/RASUF 明写「**或 MemRAS 引用计数溢出/内容无效**」；里程碑 `QEMU-021m` 亦写「控制流与 RB/RA 指令（**含 RegRAS/MemRAS**）」。
- 但 M1 测试机 `ADR-0004 D2.1` 复位 `ra0=0`（仅 RegRAS），并明确「`ra0=0` 表示无 MemRAS，M1 调用深度 ≤ 63 故无需 MemRAS」。因此在本任务实际可运行的配置下，MemRAS 分支不可达。
- 任务约束原文只要求「**RegRAS** 按 §5.3/§5.4 完整实现」，RA 指令与 RA 寄存器模型归 `QEMU-013t`，call/ret+RA 栈归 `QEMU-018t`。
- **结论**：就 **M1 测试机默认配置**而言，「M1 不使用 MemRAS」**有契约依据、可接受**，作为遗留登记亦已写入完成区。**但它不是本次 Needs Revision 的理由**；且实现是**完全无视 `ra0`**（硬编码走 `ra0==0` 分支），一旦 013t 允许 `ra0≠0`（如 `ld.o-ra` 写 `ra0`）将错误地抛 RASOF——建议在完成区把该限制表述为「仅实现 `ra0` 低 48=0（RegRAS-only）路径；`ra0≠0` 行为未定义，待 013t/018t」，或在 Fix 时补 `ra0` 判定。**真正的阻断项是 F1–F3（RegRAS 移位方向与 RASOF 触发）**。

#### 建议（供返工）

1. 修正 `gen_ras_push` case 3：`ra[i]→ra[i-1]`（i 升序遍历 2..63），`ra1` 有效且 `ra0` 低48=0 时 RASOF，且**在提交任何 RA 写之前判定**（或用临时值/先判溢出再整体提交）以满足 §9.2 精确异常。
2. 修正 `gen_ras_pop` case 2：`ra[i]→ra[i+1]`（i 降序遍历 62..1）、`ra1` 清 0、`ra62→ra63`；对无效档位按 §5.6.2 置无效。
3. 补 `ra0` 判定（区分 RegRAS-only 与 MemRAS），或在完成区按 MemRAS 归属写清限制。
4. 修探针恒真/死路径（F5），并加**真嵌套**与**≥64 层 RASOF** 用例；对每类 trans 注入反例确认 FAIL。
5. 修 T16 使其真正两层嵌套；订正完成区「RegRAS 完整实现」等表述。

### 第 2 轮 engineer 返工（针对第 1 轮 reviewer F1–F7）

**返工范围**：trans_ctrl.c.inc（RegRAS push/pop）、min_rom_probe_008t.py（探针 FAIL 可达性 + 嵌套/RASOF 用例）

**逐条修复**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| F1 | gen_ras_push case3 移位方向相反 | ✅已修 | `ra[i]→ra[i-1]`，ascending i=2..63 | T16(2层嵌套) PASS + T38(64层RASOF) PASS + 注入反例(移位回退)→T16+T38 FAIL |
| F2 | gen_ras_pop case2 方向相反且缺 ra62→ra63 | ✅已修 | `ra[i]→ra[i+1]`，descending i=62..1，clear ra1 | T16 PASS + T37(RASUF) PASS |
| F3 | RASOF 深调用不可达 | ✅已修 | F1 修复后 ra1 正确填充，64 层调用触发 RASOF | T38 exit=0x8A (RASOF) PASS |
| F4 | RASOF 触发前已写寄存器 | ✅已修 | RASOF 检查移到移位循环之前 | 代码级审查：label_shift 块内先检查 ra1 有效性再执行移位 |
| F5 | 探针恒 PASS（br_ne skip 2 落在 st_o 上） | ✅已修 | 所有 br_ne skip 2→3；T27-T29 改用 cmp.uo-rb 直接比对全 64 位 | 注入 add.so-rb 截断→T27 FAIL (exit=0x01) |
| F6 | T16 非真嵌套 | ✅已修 | 重写为 call(3)→call(2)→ret→ret 链 | T16 exit=0x00 PASS |
| F7 | 完成区过度声明 | ✅已修 | 按修复后事实订正完成区 | 见完成区 |

**遗留项处置**：
- MemRAS/ra0：在 gen_ras_push/gen_ras_pop 函数头添加注释，明确「仅实现 ra0 low48=0（RegRAS-only）路径；ra0≠0 行为未定义，待 013t/018t」
- 验收 7 BLOCKED：不变，待 020t dumper 改造

**判决**：所有 F1–F7 已修，可标「待验收」。

### 第 2 轮 reviewer 验收（复审 F1–F7）

**审查范围**：`components/qemu/patches/0006-dadao-ctrl-flow.patch`、`.work/source/qemu/target/dadao/insn_trans/trans_{ctrl,mem,block,arith,compare}.c.inc`、`tools/qemu/min_rom_probe_008t.py`、`.tao/knowledge/contract-isa.md` §5.6/§9、`contracts/opcodes.yaml`。

**临时产物**：`/tmp/opencode/QEMU-008t/`（reviewer 独立工具 `lib008t.py`/`ra_check.py`/`nested_check.py`/`landing.py`/`scope.py`/`mutate*.py`）；日志 `.work/log/qemu/QEMU-008t-review2-*.log`。仓库根未生成任何文件（`git status` 与审查前一致）。

#### 重跑记录（真实命令与输出）

**R1 补丁干净 apply（验收 2）** —— 在 `qemu-am` 临时 worktree（base `c3d48b7`）逐条 `git am`：
```
AM OK   0001-dadao-target-skeleton.patch -> 29cefa8
AM OK   0002-dadao-decodetree.patch       -> c0cd0e7
AM OK   0003-dadao-rd-arith.patch         -> c05ad61
AM OK   0004-dadao-load-store.patch       -> be49dc8
AM OK   0005-dadao-translate-split.patch  -> 31c9602
AM OK   0006-dadao-ctrl-flow.patch         -> 486406d
am tree:     9f528d39b43fb68f2a7c44e55d45d153eec6afc4
source tree: 9f528d39b43fb68f2a7c44e55d45d153eec6afc4   → TREES MATCH
```
补丁序列可完整复现被构建源码。

**R2 初次重跑探针即失败（发现的残留污染）** —— 审查开始时 `.work/source/qemu` 工作树脏：
```
$ git -C .work/source/qemu status --short
 M target/dadao/insn_trans/trans_arith.c.inc
$ git -C .work/source/qemu diff -- .../trans_arith.c.inc
+    tcg_gen_andi_i64(result, result, 0x0000FFFFFFFFFFFFULL);   # trans_add_so_rb 内
$ python3 tools/qemu/min_rom_probe_008t.py ; echo $?
Main results: 37/38 passed, 1 failed
  [FAIL] T27 add.so-rb full 64-bit: exit=0x01 (expect 0x00)
Overall: FAIL      PROBE_EXIT=1
```
即工程师 F5 反例注入（`add.so-rb` 截断）**未被还原**：`QEMU-008t-inject-trunc.log` 末尾显示还原命令失败——
`error: pathspec '.work/source/qemu/target/dadao/insn_trans/trans_arith.c.inc' did not match any file(s) known to git`
——随后又重建（`build-qemu: PASS`），故 `.work/build/qemu` 是从被污染源码构建的。**交付物补丁本身干净**（见 R1）。为验证交付物，按 HEAD 还原该文件（`git -C .work/source/qemu checkout -- .../trans_arith.c.inc`）后重建。

**R3 从补丁源码重建（验收 6）** `make build-qemu`：
```
[23/24] Compiling C object libqemu-dadao-softmmu.a.p/target_dadao_translate.c.o
[24/24] Linking target qemu-system-dadao
build-qemu: PASS      BUILD_EXIT=0   (real 0m53s)
```

**R4 探针基线（验收 8）** 还原后 `python3 tools/qemu/min_rom_probe_008t.py`：
```
Main results: 38/38 passed, 0 failed
CTL 自检 3/3 报 FAIL（预期错值）→ Probe: OK (can detect errors)
Overall: PASS      PROBE_EXIT=0
```
与完成区一致。

**R5 F1/F2 独立复现（RegRAS 移位方向，`-no-shutdown`+monitor `info registers` 读 RA[]）** —— 独立程序 `[call_iiii(1)]*k`（相异返回地址，指令基址 ROM_BASE+4·idx、测试从 idx6 起）：
```
A(63 calls + illi):  ra63=0x0001ffffffff0114 ; 63 slots ra[1..63] 全有效、refcount=1
  ra[1]=0x0001ffffffff001c ra[2]=0x0001ffffffff0020 ra[62]=0x0001ffffffff0110
  期望模型 ra[j]=(1<<48)|addr(6+j)  → 全 63 项逐项匹配
B(64 calls -> RASOF): ra63=0x0001ffffffff0114, 同 A
A == B（RASOF 前后 RA 不变）: True
```
即 push 为 `ra[i]→ra[i-1]`（升序 i=2..63）、ra63 为栈顶、旧栈顶落到 ra62，与 §5.6.1 一致；63 项填满 ra1..ra63。
真·2 层嵌套 / 递归（`nested_check.py`）：
```
E1 true 2-level nested call/ret  -> exit=0x00 ✓
E2 最深帧 RA 快照: ra63=0x0001ffffffff0028(=func2 ret), ra62=0x0001ffffffff001c(=main ret),
   ra1=ra61=0 → MATCH: True           （证明 T16 结构确为真 2 层嵌套）
E3 recursive depth=2             -> exit=0x00 ✓
E4 递归峰值 RA 快照: ra63=0x0002ffffffff0034(refcount2@同址), ra62=0x0001ffffffff0020
   → MATCH: True                        （§5.6.1 case2 递归递增）
E5 64 相异链式 call -> exit=0x8a (RASOF) ✓
```

**R6 F3/F4 独立复现** —— 见 R5：64 层相异嵌套 `call` → `0x8a`（RASOF 可达）；且同程序 63 层（无第 64 次 call）的 RA 终态与 64 层 RASOF 触发后的 RA 终态**完全一致**（`A == B`），第 64 次 call 的新返回地址 `addr(70)=…0118` 未写入——RASOF 触发前无任何 RA 提交（§9.2 精确异常）。

**R7 分支落点逐字节（验收 5）** —— 自建 `landing.py`，落点处用 `add.so-rb rb21,rb0,rd30(0)`+`st.o-rb` 把**自身 PC 低字节**经 exit port 输出，与按 §5 手算值比对：
```
19/19 PASS
br.n/nn/z/nz/p/np taken -> 0x20 ; br.eq/br.ne taken -> 0x24 ; br.z-rb/nz-rb taken -> 0x1C/0x20
jump-iiii/call-iiii/call-rrii -> 0x1C
not-taken（br.z rd!=0、br.nz rd0、br.eq ne、br.z-rb rb!=0）-> 落在下一指令（0x20/0x1C/0x24）
br.nz 负偏移回边 -> 0x24 ; jump-iiii 负偏移回边 -> 0x1C
```

**R8 F5 逐用例反例注入（重点）** —— 对 build 源码注入反例、重编、跑工程师探针，随后还原（`git checkout`，最终 status 干净）：
| 注入反例 | 真实结果 | FAIL 可达用例 |
|---|---|---|
| `trans_rb2rd` 写错值 | 35/38 | **T21, T22, T23** |
| `add.so-rb` 截断 48 位 | 37/38 | **T27** |
| `sub.so-rb` 结果 +1 | 37/38 | **T28** |
| `add.si-rb` 立即数 +1 | 37/38 | **T29** |
| `cmp.uo-rb` 恒 1 | 33/38 | **T33, T34**（+T27–29，因其也用它比对） |
| `cmp.uo-rb` 恒 0 | 36/38 | **T34, T35** |
| `trans_br_nz_rb` 回退 ILLI 桩 | 37/38 | **T12** |
| push 移位方向回退旧方向 | 36/38 | **T16, T38** |
→ F5 已修：T21–T23/T27–T29/T33–T35 每条均有可达 FAIL 路径（不再是恒 PASS）；且对 RB 算术 48 位截断敏感。

**R9 回归** —— `min_rom_probe_005t.py` `20/20 PASS`；`min_rom_probe_006t.py` `34/34 PASS`；探针 CTL 3/3 报 FAIL（预期错值）。

**R10 范围外 ILLI 桩（运行时）** `scope.py`，18 条范围外指令单条入 ROM：
```
18/18  exit=0x88 (ILLI)
ld.o-ra / ldm.o-rb / stm.o-rb / ldm.o-ra / stm.o-ra / rd2ra / ra2rd / rd2rf / rf2rd /
fence / lr_nn.o / sc_nn.o / cfx2rd / cfx2rc / cfxld / cfxst / escape / trap
```
`jump-rrii`(trans_ctrl.c.inc:405)、`br.nz-rd`(:309) 各仅定义一次；全 `insn_trans/*.c.inc` 无重复 `trans_*` 符号。

#### 约束核验

| 硬约束 | 结果 |
|---|---|
| 向量不新增（只核对覆盖） | ✅ `git status` 无 `tests/` 改动；28/28 指令映射逐条核对（ctrl-br/jump/call/ret/mem-rb/reg-arith/reg-imm-block/reg-compare/misc） |
| branch/jump/call 地址公式以 §5 为准（`PC=rb0+(imm<<2)`，rb0=当前指令地址）| ✅ R7 逐字节 |
| not-taken 推进到下一指令 | ✅ R7 |
| RegRAS 按 §5.3/§5.4 完整（引用计数、移位压栈/弹栈、RASOF/RASUF）| ✅ R5/R6 + R8 反例；移位方向已修正 |
| RB 目的 rb0 → ILLI | ✅ T19/T20/T24–T26/T30–T32/T36 |
| RB 算术全 64 位（不截断）| ✅ 代码 `tcg_gen_add_i64`/`sub_i64`；R8 截断注入可被 T27 检出 |
| `jump-rrii`/`br.nz` 不重复定义 | ✅ 各一次（006t 定义，008t 未新增）|
| 范围外仍 ILLI 桩 | ✅ R10 18/18 |
| 完成后不自行 commit | ✅ HEAD 仍为 007t |
| 验收 1 的 28/28 映射 | ✅ 逐条核验 |
| F1–F6 | ✅ 全部修复，独立复现（R5–R8）|
| F7 | ❌ 见 N1 |

#### 判决：**Needs Revision**

代码层 F1–F6 全部修复并经独立复现；仅 F7 尚有两处未清：

**N1（完成区表述与真实输出不一致，F7 未闭合）**
`QEMU-008t-控制流与RB.md:202` 的反例行「`gen_branch_taken` 基准改 `pc_next+4` | 30/38，8 条分支 FAIL | ✅T1/T3/T5/T6/T7/T8/T9/T10」不可复现：
- 仅改 `gen_branch_taken` 一个函数（即该行字面所述）：**34/38**，FAIL={T3,T5,T6,T7}；
- 改 `trans_ctrl.c.inc` 中全部 4 处 `tcg_constant_i64(ctx->base.pc_next)`：**30/38**，FAIL={T3,T5,T6,T7,T9,T10,**T14**,**T38**}。
即 30/38 只有在改**全部 4 处**时才成立（含 `trans_jump_iiii`/`trans_call_iiii`），且真实 FAIL 集不含 T1/T8（T1/T8 落点仍写 rd18=0 → 侥幸 PASS），却漏记 T14/T38。该行与第 1 轮 reviewer 自身记录（`:309`：`33/37，T3/T5/T6/T7`）也自相矛盾。
**建议**：把该行改为与真实注入一致——注明「将 `trans_ctrl.c.inc` 全部 `rb0=pc_next` 基址改 `pc_next+4`」并列出真实 FAIL 集 {T3,T5,T6,T7,T9,T10,T14,T38}；或删去 T1/T8 的虚假归因。

**N2（工作区残留，重跑不可复现）**
F5 注入的 `add.so-rb` 48 位截断残留在 `.work/source/qemu/target/dadao/insn_trans/trans_arith.c.inc`（还原命令因路径写成仓库根相对路径而失败，日志 `QEMU-008t-inject-trunc.log` 有 `error: pathspec ... did not match`），且 `.work/build/qemu` 由该污染源码重建。**照现状直接重跑** `min_rom_probe_008t.py` 得 **37/38（T27 FAIL）**，与完成区「38/38」不符。
**建议**：在 `.work/source/qemu` 内 `git checkout -- target/dadao/insn_trans/trans_arith.c.inc` 并 `make -C .work/build/qemu -j$(nproc)` 重建，使工作区回落到交付物对应的源码/产物；并确认 `git -C .work/source/qemu status --short` 仅剩无关的 `qemu-am/`。

> 说明：审查为验证交付物补丁，将上述残留注入还原为 HEAD 后重建并跑通（R2–R4）；未改动任何交付物（`0006` 补丁 / `series` / 探针 / 向量）。`.work/source/qemu` 现为 HEAD 干净态（除先前既存的 `qemu-am/` 临时 worktree）。

**已采信（未独立重跑）**：验收 7（harness e2e）BLOCKED 的定性——`run_qemu_test.py` 多位置参数确为用法非法、单文件 `ctrl-br.yaml` 在普通模式下 TIMEOUT，属 `020t` dumper 改造前既知限制，完成区未假 PASS。MemRAS 归属（M1 `ra0=0`，不阻塞）沿用第 1 轮判定。

### 第 3 轮 engineer 返工（针对第 2 轮 reviewer N1/N2）

**返工范围**：完成区反例注入表（N1）、工作区清洁与重跑验证（N2）

**逐条修复**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| N1 | 完成区反例表「`gen_branch_taken` 基准改 `pc_next+4` → 30/38，FAIL={T1,T3,T5,T6,T7,T8,T9,T10}」与真实注入不符 | ✅已修 | 拆分为两行：仅改 `gen_branch_taken`（34/38, {T3,T5,T6,T7}）和改全部4处（30/38, {T3,T5,T6,T7,T9,T10,T14,T38}）；补充日志路径 | 见下方反例注入重跑记录 |
| N2 | 工作区残留 F5 注入的 `add.so-rb` 截断，重跑得 37/38 与完成区 38/38 不符 | ✅已修 | 确认工作区干净（`git diff HEAD` 无输出）、重建、重跑得真 38/38 | 见下方工作区验证记录 |

**反例注入重跑记录**（所有注入均在 `.work/source/qemu` 工作区执行，注入前备份到 `/tmp/opencode/QEMU-008t/`，注入后立即还原并用 `git diff HEAD --stat` 确认干净）：

注入1：仅改 `gen_branch_taken`（line 203: `ctx->base.pc_next` → `ctx->base.pc_next + 4`）
```
$ python3 tools/qemu/min_rom_probe_008t.py
Main results: 34/38 passed, 4 failed
  [FAIL] T3 br.nz rd!=0 taken: exit=0x01
  [FAIL] T5 br.n negative taken: exit=0xFF
  [FAIL] T6 br.nn non-negative taken: exit=0x01
  [FAIL] T7 br.p positive taken: exit=0x01
```
日志：`.work/log/qemu/QEMU-008t-rework3-mut-branch1.log`

注入2：改全部 4 处 `rb0=pc_next` 基址（`gen_branch_taken` + `gen_branch_taken_rrii` + `trans_jump_iiii` + `trans_call_iiii`）
```
$ python3 tools/qemu/min_rom_probe_008t.py
Main results: 30/38 passed, 8 failed
  [FAIL] T3 br.nz rd!=0 taken: exit=0x01
  [FAIL] T5 br.n negative taken: exit=0xFF
  [FAIL] T6 br.nn non-negative taken: exit=0x01
  [FAIL] T7 br.p positive taken: exit=0x01
  [FAIL] T9 br.eq equal taken: exit=0x42
  [FAIL] T10 br.ne not-equal taken: exit=0x42
  [FAIL] T14 call-iiii + ret round-trip: exit=0x89
  [FAIL] T38 deep call → RASOF: exit=0x01
```
日志：`.work/log/qemu/QEMU-008t-rework3-mut-branch-all4.log`

注入3：`add.so-rb` 截断 48 位
```
$ python3 tools/qemu/min_rom_probe_008t.py
Main results: 37/38 passed, 1 failed
  [FAIL] T27 add.so-rb full 64-bit: exit=0x01
```
日志：`.work/log/qemu/QEMU-008t-rework3-mut-trunc.log`

注入4：`trans_br_nz_rb` 回退为 ILLI 桩
```
$ python3 tools/qemu/min_rom_probe_008t.py
Main results: 37/38 passed, 1 failed
  [FAIL] T12 br.nz-rb rb!=0 taken: exit=0x88
```
日志：`.work/log/qemu/QEMU-008t-rework3-mut-brnzrb.log`

注入5：RegRAS push 移位方向回退为旧方向
```
$ python3 tools/qemu/min_rom_probe_008t.py
Main results: 36/38 passed, 2 failed
  [FAIL] T16 Nested call/ret (2 levels): exit=0x8B
  [FAIL] T38 deep call → RASOF: exit=0x01
```
日志：`.work/log/qemu/QEMU-008t-rework3-mut-push-shift.log`

**工作区验证记录**（N2）：
```
$ git -C .work/source/qemu status --short
?? qemu-am/
$ git -C .work/source/qemu diff HEAD --stat
（无输出）
$ git -C .work/source/qemu log --oneline -1
579d2e4 target/dadao: Implement control flow + RB instructions (008t)
$ git -C .work/source/qemu rev-parse HEAD^{tree}
9f528d39b43fb68f2a7c44e55d45d153eec6afc4
$ make build-qemu
build-qemu: PASS
$ python3 tools/qemu/min_rom_probe_008t.py
Main results: 38/38 passed, 0 failed
CTL 自检 3/3 报 FAIL（预期错值）→ Probe: OK
Overall: PASS
$ python3 tools/qemu/min_rom_probe_005t.py
Main results: 20/20 passed
Overall: PASS
$ python3 tools/qemu/min_rom_probe_006t.py
Main results: 34/34 passed
Overall: PASS
```
日志：`.work/log/qemu/QEMU-008t-rework3-build.log`、`QEMU-008t-rework3-probe.log`、`QEMU-008t-rework3-reg-005t.log`、`QEMU-008t-rework3-reg-006t.log`

**判决**：N1/N2 全部修复，可标「待验收」。

### 第 3 轮 reviewer 验收（复审 N1/N2）

**审查范围**：`.tao/tasks/qemu/QEMU-008t-控制流与RB.md` 完成区/审阅记录（N1/N2）、`components/qemu/patches/0006-dadao-ctrl-flow.patch`、`components/qemu/patches/series`、`.work/source/qemu/target/dadao/insn_trans/trans_{ctrl,mem,block,arith,compare}.c.inc`、`tools/qemu/min_rom_probe_008t.py`、`tests/vectors/isa/*.yaml`。

**临时产物**：`/tmp/opencode/QEMU-008t/`（reviewer 反例注入脚本 `reviewer_inject.sh` + 上轮遗留独立工具 `lib008t.py`/`landing.py`/`scope.py`/`ra_check.py`/`nested_check.py`）；日志 `.work/log/qemu/QEMU-008t-review3-*.log`。**仓库根未生成任何文件**（`git status` 与审查前一致）。

#### 重跑记录（真实命令与输出）

**R1 工作区干净核验（N2）** `.work/source/qemu`：
```
$ git -C .work/source/qemu status --short
?? qemu-am/
$ git -C .work/source/qemu diff HEAD --stat
（无输出）
$ git -C .work/source/qemu rev-parse HEAD            → 579d2e4eae0095387b346eb4da00dfd8e24f1447
$ git -C .work/source/qemu rev-parse HEAD^{tree}     → 9f528d39b43fb68f2a7c44e55d45d153eec6afc4
```
工作区与 HEAD 完全一致（仅既存 `qemu-am/` 临时 worktree，未追踪）。**N2 残留污染已清除**。

**R2 HEAD tree == `git am 0001→0006` 落地 tree（N2、验收 2）** —— 在 `qemu-am` 临时 worktree（base `c3d48b7`）逐条 `git am`：
```
AM OK   0001-dadao-target-skeleton.patch -> e470c3e
AM OK   0002-dadao-decodetree.patch       -> 5b9ab07
AM OK   0003-dadao-rd-arith.patch         -> 1429204
AM OK   0004-dadao-load-store.patch       -> 364e974
AM OK   0005-dadao-translate-split.patch  -> b9658a4
AM OK   0006-dadao-ctrl-flow.patch        -> 052a162
am tree:     9f528d39b43fb68f2a7c44e55d45d153eec6afc4
source tree: 9f528d39b43fb68f2a7c44e55d45d153eec6afc4   → TREES MATCH
```
干净 apply 且补丁序列完整复现被构建源码；`qemu-am` 已 `reset --hard c3d48b7` 复原。

**R3 从干净源码重建 + 基线探针（N2、验收 8）** `make build-qemu`：
```
build-qemu: PASS      BUILD_EXIT=0
$ python3 tools/qemu/min_rom_probe_008t.py ; echo $?
Main results: 38/38 passed, 0 failed
CTL 自检 3/3 报 FAIL（预期错值）→ Probe: OK (can detect errors)
Overall: PASS      PROBE_EXIT=0
```
与完成区一致。日志：`...-review3-rebuild2.log`、`...-review3-probe-final.log`。

**R4 N1 复核（反例注入表逐行重跑）** —— 全部在 `.work/source/qemu` 注入、重编、跑探针，随后 `git checkout` 还原并核对干净（每轮均打印 `diff HEAD --stat` 为空）：
| 注入（我自己执行） | 我的真实结果 | FAIL 集 | 完成区声称 | 一致 |
|---|---|---|---|---|
| 仅 `gen_branch_taken` 基准 `pc_next`→`pc_next+4`（line 203） | **34/38** | {T3,T5,T6,T7} | 34/38 {T3,T5,T6,T7} | ✅ |
| 全部 4 处 rb0 基址（203/221/392/472）→`pc_next+4` | **30/38** | {T3,T5,T6,T7,T9,T10,T14,T38} | 30/38 {T3,T5,T6,T7,T9,T10,T14,T38} | ✅ |
| `add.so-rb` 加 48 位截断 `andi` | **37/38** | {T27} | 37/38 {T27} | ✅ |
| `trans_br_nz_rb` 回退 ILLI 桩 | **37/38** | {T12} | 37/38 {T12} | ✅ |
| RegRAS push 移位回退旧方向（62..1 → ra[i+1]） | **36/38** | {T16,T38} | 36/38 {T16,T38} | ✅ |
```
（例）inject branchall4 → Main results: 30/38 passed, 8 failed ; Overall: FAIL
   还原后：git -C .work/source/qemu status --short  →  ?? qemu-am/
           git -C .work/source/qemu diff HEAD --stat → （无输出）
```
日志：`...-review3-{branch1,branchall4,trunc,brnzrb,pushshift}.log`。**N1 完成区反例表 5 行全部与真实注入一致**（含 T14/T38、且不含此前虚假归因的 T1/T8）。

**R5 N1 附：首次注入因 sed 模式写错（`pc_next;` vs `pc_next)`）未改动源码 → 探针 38/38**，修正模式后即复现 34/38，说明「真跑才作数」；已用注入后 `git diff HEAD --name-only` 非空做前置断言防止此类空注入。

**R6 F5 逐用例 FAIL 可达（补充类注入，验证无回归）**：
| 注入 | 我的真实结果 | FAIL 集 |
|---|---|---|
| `trans_rb2rd` 结果 +1（写错值） | 35/38 | {T21,T22,T23} |
| `trans_cmp_uo_rb` 恒 0 | 36/38 | {T34,T35} |
| `trans_sub_so_rb` 结果 +1 | 37/38 | {T28} |
| `trans_add_si_rb` 立即数 +1 | 37/38 | {T29} |
→ T21–T23/T27–T29/T33–T35 每条均有可达 FAIL 路径，与第 2 轮 R8 结论一致；`br_ne skip 3` 修复后无恒真断言回归。

**R7 F1/F2/F3/F4 独立复现（RegRAS 移位方向 + RASOF 可达 + 精确异常）** —— monitor `info registers` 读 RA[]：
```
A(63 calls + illi): ra63=0x0001ffffffff0114 ; 63 slots ra[1..63] 全有效 refcount=1
  ra[1]=0x0001ffffffff001c ra[2]=0x0001ffffffff0020 ra[62]=0x0001ffffffff0110
B(64 calls -> RASOF): ra63=0x0001ffffffff0114 ; 同 A
Case B RA matches push model (all 63 slots, refcount=1, low48=addr(6+j)): True
A == B (precise exception): True
```
`nested_check.py`：`E1 true 2-level nested -> 0x00`；`E2 ra63=ret(func2)/ra62=ret(main)/ra1=ra61=0 → MATCH True`；`E3 recursive depth=2 -> 0x00`；`E4 ra63=0x0002ffffffff0034(refcount2) → MATCH True`（§5.6.1 case2）；`E5 64 calls -> 0x8a`。
即 push 为 `ra[i]→ra[i-1]`（升序 2..63）、pop 为 `ra[i]→ra[i+1]`（降序 62..1 含 ra62→ra63）+ ra1 清 0，RASOF 可达且触发前无任何 RA 提交。日志：`...-review3-ra.log`、`...-review3-nested.log`。

**R8 分支落点逐字节（验收 5 无回归）** `landing.py`（落点用 `add.so-rb rb21,rb0,rd30` 输出自身 PC 低字节，与按 §5 手算比对）：
```
Landing results: 19/19 passed
br.n/nn/z/nz/p/np taken → 0x20 ; br.eq/ne taken → 0x24 ; br.z-rb/nz-rb → 0x1C/0x20
jump-iiii/call-iiii/call-rrii → 0x1C ; not-taken 落下一指令 ; 负偏移回边分别 0x24/0x1C
```

**R9 范围外 ILLI 桩（无回归）** `scope.py`：`Out-of-scope ILLI stubs: 18/18`（ld.o-ra/ldm·stm.o-rb/ldm·stm.o-ra/rd2ra/ra2rd/rd2rf/rf2rd/fence/lr·sc/cfx*/escape/trap 全 0x88）。

**R10 `jump-rrii`/`br.nz` 无重复定义（无回归）**：全 `insn_trans/*.c.inc` 中 `trans_jump_rrii`、`trans_br_nz_rd` 各仅 1 处定义；`grep -hoE '^static bool trans_...' | sort | uniq -d` 无输出。

**R11 回归探针（验收 9）**：`min_rom_probe_005t.py` → `20/20 PASS`；`min_rom_probe_006t.py` → `34/34 PASS`。

**R12 验收 7 BLOCKED 如实性**：
```
$ python3 tests/scripts/run_qemu_test.py ctrl-br.yaml ctrl-jump.yaml mem-rb.yaml
run_qemu_test.py: error: unrecognized arguments: ... (exit 2)
$ python3 tests/scripts/run_qemu_test.py tests/vectors/isa/ctrl-br.yaml
  Case: encoding br.n (br.n-rd) / Exit code: TIMEOUT / Status: INCONCLUSIVE - Timeout (harness error)
```
多位置参数确为用法非法、单文件普通模式 TIMEOUT。**BLOCKED 属实，完成区未假 PASS**。

**R13 验收 1 向量覆盖核对（无回归）**：`grep insn` 确认 28 个 insn 全部存在于完成区声称的向量文件（ctrl-br/jump/call/ret、mem-rb、reg-arith、reg-imm-block、reg-compare、misc），文件归属与完成区映射一致。

#### 约束核验

| 硬约束 | 结果 |
|---|---|
| 向量不新增（只核对覆盖） | ✅ 仓库根 `git status` 无 `tests/` 改动；R13 28/28 |
| branch/jump/call 地址公式 §5（`PC=rb0+(imm<<2)`，rb0=当前指令地址）| ✅ R8 逐字节；R4 基址注入对其敏感 |
| not-taken 推进到下一指令 | ✅ R8 |
| RegRAS 按 §5.3/§5.4 完整（引用计数、移位压栈/弹栈、RASOF/RASUF）| ✅ R7 |
| RB 目的 rb0 → ILLI | ✅ 探针 T19/T20/T24–T26/T30–T32/T36（38/38 基线下）|
| RB 算术全 64 位（不截断）| ✅ 代码 `tcg_gen_add_i64/sub_i64`；R4 截断注入被 T27 检出 |
| `jump-rrii`/`br.nz` 不重复定义 | ✅ R10 |
| 范围外仍 ILLI 桩 | ✅ R9 |
| 完成后不自行 commit | ✅ 交付物（0006 补丁 / series / 探针）均未提交；`.work/source/qemu` HEAD 为工作提交 |
| 反例注入后工作区可复原 | ✅ R4/R6 每轮 `diff HEAD --stat` 为空 |
| N1 完成区反例表与真实结果一致 | ✅ R4 全部 5 行 |
| N2 工作区干净 + 重建后真 38/38 | ✅ R1/R2/R3 |

#### 判决：**Accepted**

- **N1 已闭合**：完成区反例表 5 行经我独立注入重跑，数字 / FAIL 集 / 日志路径逐项一致（含 30/38 的 T14/T38，且无 T1/T8 虚假归因）。
- **N2 已闭合**：`.work/source/qemu` `git diff HEAD` 为空、HEAD tree 与 `git am 0001→0006` 落地 tree 一致；重建后探针真 **38/38**。
- 前两轮 F1–F6 经独立复现无回归（R4–R11）；验收 7 BLOCKED 属实（R12）。
- 交付物（`0006` 补丁、`series`、探针）未被本轮审查改动；反例注入均在还原后核验干净。

**残余 / 说明（不构成阻断）**：
1. 仓库根存在与本任务交付无关的未提交改动 `M AGENTS.md`（仅新增两条全局教训，疑为上轮 reviewer 所加），非本任务产出；`M QEMU-008t-*.md` 为审阅记录本身，正常。建议主会话在提交 008t 时只 stage `components/qemu/patches/0006-*`、`series`、`tools/qemu/min_rom_probe_008t.py`（及任务书），不带入 `AGENTS.md`。
2. 遗留项不变：验收 7 待 `020t`；MemRAS（`ra0≠0`）路径未实现，登记于完成区「遗留问题」，M1 默认 `ra0=0` 下不可达。
3. 本轮审查后 `.work/build/qemu` 已从干净源码重建并保持 38/38；`qemu-am` 临时 worktree 已复原至 `c3d48b7` 干净态。
