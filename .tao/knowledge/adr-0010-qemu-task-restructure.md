# ADR-0010: QEMU 模块任务重构（harness 依赖 + translate.c 拆分 + 任务粒度）

**状态**：Accepted
**日期**：2026-09-19
**关联**：ADR-0004（Test Machine）、ADR-0009（Harness Methodology）、`QEMU-014t`（harness 实现）、`QEMU-005t`（4 轮返工教训）、`deferred.md`（harness 依赖条目）

> **D1–D4 已由用户逐条确认（2026-09-19）。** 以下正文为确认后的最终版本。

## Context（背景）

QEMU 模块在 `QEMU-005t`（4 轮返工）和 `QEMU-014t`（5 轮返工）中暴露了系统性问题，根因已定位为四类：

1. **harness 依赖被积攒到最后**：harness 的 trusted 指令集跨越 `005t`（`set.zw`/`or.w`/`xor.o`/`or.o`）、`006t`（`st.o`）、`008t`（`jump`/`br.nz`/`rb2rd`）→ 只能等到 `008t` 后才能端到端跑。`014t` 的依赖声明（`QEMU-004t`）与真实 e2e 依赖（`005t`+`006t`+`008t`）不符，导致 TDD 假设不成立。
2. **任务粒度过大**：`005t` 覆盖 12 指令族/97 条 insn，4 轮返工中 B1-B5/N1-N2 涉及 div UB、ext orrr 寄存器号、定宽符号扩展、ext 高位填充、NORETURN 崩溃——每类都需独立修复+验证。
3. **`translate.c` 单文件膨胀**：`005t` 后约 2000 行，后续 `006t`（22 条 load/store）+ `007t`（MALIGN）+ `008t`（控制流+RB）+ `013t`（RA）将继续膨胀，review 难度与冲突风险递增。
4. **验收未核实「现在能不能跑」**：多份任务书的验收标准声称可用 harness 验证，实际 harness e2e 链不完整。

上游 riscv target 在 v11.x 已采用 `target/riscv/tcg/` 子目录 + `insn_trans/trans_*.c.inc` 按类别拆分的模式（`translate.c` + `trans_rvi.c.inc` / `trans_rvm.c.inc` / `trans_rvv.c.inc` 等），QEMU 官方推荐此模式。

## Decision（决策）

### D1 harness 最小可用集与前置交付

**决策**：将 harness e2e 所需的最小指令集从 3 个任务（`005t`+`006t`+`008t`）收拢到 2 个任务（`005t`+`006t`），使 harness 在 `006t` 完成后即可端到端跑通。

**修法 (a)**：harness 仅在 `--dump` 时 emit dumper 段（普通模式不 emit）。原因：dumper 段用到 `st.o-rb`/`rb2rd`，属 `008t` 范围；普通模式（D2）pass/fail 判定只看 `$?`，不需要 dumper。使 harness 在 `006t` 后可端到端跑 RD-only 向量。

**最小可用集**（6 条指令，覆盖 trampoline + loader + exit；dumper 按需由 `--dump` 触发）：

| 指令 | 编码来源 | 用途 | 当前归属 → 新归属 |
|------|---------|------|------------------|
| `set.zw rd/rb` | op=0x4C/0x4E, rwii | loader: 构造 64 位立即数 | 005t → 不变 |
| `or.w rd/rb` | op=0x48/0x4A, rwii | loader: 合并 wyde | 005t → 不变 |
| `xor.o` | op=0x40, ha=0x0C, orrr | exit: XOR 比较 | 005t → 不变 |
| `or.o` | op=0x40, ha=0x08, orrr | exit: ORR 累加 | 005t → 不变 |
| `st.o rd` | op=0x21, rrii | exit: 写 exit port | **006t → 不变** |
| `jump-rrii` | op=0x71, rrii | trampoline: ROM→RAM 绝对跳转; exit: 跳过 FAIL 段 | **008t → 前置到 006t** |
| `br.nz rd` | op=0x6B, riii | exit: PASS/FAIL 分支 | **008t → 前置到 006t** |

**rb2rd**（dumper dump rb0/PC）：留在 `008t`，但 harness 在 `006t` 完成后即可用普通模式（无 dumper）跑通 RD-only 向量（`reg-arith.yaml`、`reg-logic.yaml` 等）。`008t` 完成后解锁 RB/RA 比较 + `--dump` dumper。

**理由**：`jump-rrii` 和 `br.nz` 各仅 1 条 `trans_*`，实现简单（`jump-rrii` = `PC = rbha + rdhb + (imms12<<2)`，48 位；`br.nz` = `if (rdha!=0) PC = rb0 + (imms18<<2)`），前置到 `006t` 不显著增加任务复杂度，但能将 harness e2e 提前 2 个任务。

### D2 `translate.c` 拆分方案

**决策**：在 `006t` 完成后（load/store 已实现、文件约 2500-3000 行），新增 `QEMU-007t`（原 `007t` MALIGN 并入 `006t`），执行 `translate.c` 按指令类别拆分为 **10 个 `.c.inc` 文件**（用户否决了 4 文件方案，要求更细粒度）。

**目录/文件组织**（对齐 v11.1.1 riscv 的 `tcg/` 子目录模式）：

```
target/dadao/
├── translate.c              # 主翻译器：gen_intermediate_code, helpers, decodetree 集成, 寄存器访问宏
├── insn.decode              # decodetree 定义（不变）
├── insn_trans/
│   ├── trans_arith.c.inc        # §3.1 算术（add/sub/mul/div/rem 及固定位宽变体）
│   ├── trans_compare.c.inc      # §3.2 比较（cmp.*）
│   ├── trans_logic.c.inc        # §3.3 逻辑（and/or/xor/xnor/andn 及固定位宽变体）
│   ├── trans_shift.c.inc        # §3.4.1 移位（shr/shl 及固定位宽变体）
│   ├── trans_extend.c.inc       # §3.4.2 扩展（ext.*）
│   ├── trans_cond_assign.c.inc  # §3.5 条件赋值（cs.*）
│   ├── trans_imm.c.inc          # §3.6 立即数（set.zw/or.w/andn.w 及 RB 变体）
│   ├── trans_block.c.inc        # §3.7/§4 块赋值（rd2rd/rd2rb/rb2rd/rb2rb/rd2ra/ra2rd）
│   ├── trans_mem.c.inc          # §3.8/§4/§4.9 存取（ld/st/ldm/stm 含 RD/RB/RA 变体）
│   └── trans_ctrl.c.inc         # §5/§2.8 控制流（br/jump/call/ret/rela/swym/illi/fence）
```

**实施方式**：
- `translate.c` 保留：decodetree `#include`、helper 函数（`store_rd`/`load_rd`/`gen_exception_illegal`/`gen_raise_exception_illi` 等）、寄存器访问宏
- 各 `trans_*.c.inc` 用 `#include` 从 `translate.c` 末尾引入（与 riscv 一致）
- 每个 `.c.inc` 文件以 `/* SPDX-License-Identifier: ... */` 开头，不含 `#include` 保护符（非独立编译单元）

**与现有补丁的衔接**：
- `0003-dadao-rd-arith.patch`（`005t`）的 RD 整数 `trans_*` 按类别移入 `trans_arith.c.inc`/`trans_compare.c.inc`/`trans_logic.c.inc`/`trans_shift.c.inc`/`trans_extend.c.inc`/`trans_cond_assign.c.inc`/`trans_imm.c.inc`
- `0004-dadao-load-store.patch`（`006t`，含 MALIGN + jump/br.nz）的 load/store `trans_*` 移入 `trans_mem.c.inc`；`jump`/`br.nz` 移入 `trans_ctrl.c.inc`
- 后续 `0006-dadao-ctrl-flow.patch`（`008t`）直接在 `trans_ctrl.c.inc` 中实现
- `0007-dadao-ra-semantics.patch`（`013t`）的 RA 指令移入 `trans_mem.c.inc`（ld.o-ra/st.o-ra/ldm.o-ra/stm.o-ra）和 `trans_block.c.inc`（rd2ra/ra2rd）

**补丁策略**：新补丁 `0005-dadao-translate-split.patch`（纯重构，不改变语义），不修订已有 `0003`/`0004`。

**decodetree 影响**：`insn.decode` 不变（decodetree 生成的 `decode-insn.c.inc` 仍被 `translate.c` 的 `#include` 引入）。拆分只影响 `trans_*` 函数的物理位置，不影响解码逻辑。

**review/构建门禁**：
- `make build-qemu` 必须 PASS（拆分是纯重构，不改变语义）
- `tools/qemu/check_qemu_trans.py`（`019t`）须适配新路径（grep `insn_trans/trans_*.c.inc`）
- 拆分后每个 `.c.inc` 的 `trans_*` 数量可用 `grep -c` 验证与拆分前一致

### D3 任务重排与粒度调整

**决策**：合并 `006t`（load/store）+ `007t`（MALIGN）为一个任务，新增 `translate.c` 拆分任务，调整验证任务位置，补丁重编号。

**修订后的任务顺序与依赖图**：

```
002t → 003t → 004t → 005t → 006t(合并) → 007t(拆分) → 008t → {009t(rela验证), 013t(RA)} → 010t(ldmo-rb) → 011t(验证) → 012t(验证)
                                                        014t(harness骨架, 依赖 004t+006t) → 015t(语义验证) → {016t(内存), 017t(分支)} → 018t(call/ret) → 020t(dumper改造)
                                                        019t(trans lint, 依赖 013t)
                                                        021m(里程碑)
```

**详细变更**：

| 编号 | 原任务 | 变更 | 理由 |
|------|--------|------|------|
| `006t` | RD Load/Store | **合并 007t**：实现 RD load/store + MALIGN 精确异常 + TEMP_EBB + `jump-rrii`/`br.nz` 前置 | load/store 与 MALIGN 天然耦合（MALIGN 由 load/store 触发）；`jump`/`br.nz` 前置解锁 harness e2e |
| `007t` | MALIGN 精确异常 | **删除**（并入 006t） | 消除不必要的拆分 |
| `007t` (新) | translate.c 拆分 | **新增**：纯重构，将 `translate.c` 拆入 `insn_trans/` 子目录（10 个 `.c.inc`） | 为后续任务降低 review 难度；在文件膨胀前执行 |
| `008t` | 控制流+RB | **范围收窄**：移除 `jump-rrii`/`br.nz`（已前置到 006t） | 任务复杂度降低 |
| `009t` | rela 验证 | 不变 | 验证任务 |
| `010t` | ldm.o-rb | 不变 | |
| `011t` | div label 验证 | 不变 | 验证任务 |
| `012t` | 分支/call 验证 | 不变 | 验证任务 |
| `013t` | RA 指令 | 不变 | |
| `014t` | harness 骨架 | **依赖修正**：`QEMU-004t, QEMU-006t`（原为 `QEMU-004t, TESTCASES-003t, SPEC-006t`）；dumper 行为将由新任务 `020t` 改造 | `006t` 完成后 harness 可端到端跑 RD-only 向量（D1 修法 a：普通模式不 emit dumper） |
| `015t`–`018t` | harness 增强 | 不变 | |
| `019t` | trans lint | **路径适配**：grep `insn_trans/trans_*.c.inc`（拆分后） | 对齐 D2 拆分后的文件结构 |
| `021m` | 里程碑 | 补丁清单更新（0001–0007） | 反映合并后的实际补丁结构 |
| `020t` | (新增) | **harness dumper 改造**：将 `--dump` 的 dumper emit 从 harness 主路径分离，实现普通模式不 emit dumper | D1(a) 的具体实施载体 |

**修订后的补丁序列**：

| 补丁 | 任务 | 内容 |
|------|------|------|
| `0001` | 003t | Target Skeleton |
| `0002` | 004t | Decodetree |
| `0003` | 005t | RD 整数语义 |
| `0004` | 006t (合并) | Load/Store + MALIGN + jump-rrii/br.nz |
| `0005` | 007t (新) | translate.c 拆分（纯重构） |
| `0006` | 008t, 010t | 控制流 + RB（含 ldm.o-rb） |
| `0007` | 013t | RA 语义 |

### D4 验收标准规范化

**决策**：所有任务书的验收标准必须逐条标注「现在可跑」或「BLOCKED（原因 + 替代验证方式）」。涉及 harness e2e 的验收项，在 harness 链不完整时必须提供最小 ROM 探针作为替代。

**具体规则**：
- harness e2e 验收项：标注 BLOCKED + 列出缺失的指令/任务
- 最小 ROM 探针：reset PC=ROM base → 构造 exit port → 执行被测指令 → 写 exit port → 检查 `$?`
- 探针必须能区分「正常完成」vs「运行时异常」（用 UNDI 终止符或 exit port 写不同值）
- 覆盖脚本只证明「实现存在」，不得作为语义正确性证据

## Rationale（理由）

- **harness 前置**：`jump-rrii`/`br.nz` 各仅 1 条 `trans_*`，实现简单（条件判断 + PC 赋值），前置到 `006t` 不显著增加复杂度，但将 harness e2e 从 `008t`（第 8 个任务）提前到 `006t`（第 6 个任务），缩短反馈环。
- **D1 修法 a**：普通模式不 emit dumper，绕开 `st.o-rb`/`rb2rd`（008t）依赖，使 006t 后即可端到端跑 RD-only 向量。
- **load/store + MALIGN 合并**：MALIGN 由 load/store 触发（`MO_ALIGN_N`），两者在同一个 `trans_*` 函数中实现；拆分为两个任务导致 `007t` 必须修订 `006t` 的补丁，增加不必要的补丁管理开销。
- **translate.c 10 文件拆分**：对齐 v11.1.1 riscv 的官方模式（`tcg/` 子目录 + `trans_*.c.inc`）；10 文件比 4 文件粒度更细，每个文件对应 spec 一个章节，review 边界更清晰。
- **补丁重编号**：修正草案 `0004b` 与正文的矛盾，采用连续编号 `0004`–`0007`。
- **验证任务保留**：`009t`/`011t`/`012t` 为纯验证任务（不改补丁），提供定向回归证据，保留不删除。

## Consequences（影响）

- **正面**：harness e2e 提前 2 个任务可用；`translate.c` review 难度降低；补丁数量减少；验收标准更诚实。
- **负面**：`006t` 任务范围扩大（load/store + MALIGN + jump/br.nz），但 MALIGN 与 load/store 天然耦合，jump/br.nz 实现简单，净增复杂度可控。
- **下游约束**：`014t` 依赖从 `004t+TESTCASES-003t` 改为 `004t+006t`；`021m` 补丁清单更新；`019t` 的 trans lint 需适配 `insn_trans/` 路径；新增 `020t`（harness dumper 改造）。
- **向后兼容**：已验证的任务（`002t`–`005t`）不受影响；`014t`（已验证）的 harness 代码不需修改，只是依赖声明更准确。
