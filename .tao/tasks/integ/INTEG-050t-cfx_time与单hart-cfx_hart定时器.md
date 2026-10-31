# INTEG-050t: cfx_time 与单 hart cfx_hart 定时器跑通（含 spec rc 收口）

**模块**：integ
**项目里程碑**：M10
**依赖**：`INTEG-047t`（cfx_pmem DMA 的异步 QEMUTimer + `cfx_enter(async)` 框架，已验证）、`INTEG-044t`（两轴权限与 `CFXPERM`，已验证）、`INTEG-048t`（`cg_reg_deleg`，已验证）、`INTEG-049t`（cfx 探针/bootstrap/证据脚本范式，已验证）、`SPEC-175t`（`cfx_timer→cfx_time` 别名改名，已验证）
**状态**：已验证

## 执行环境

**执行环境**：本地（仓库 `/mnt/tao/DADAO-v5`，分支 `INTEG-050t`；`.work/source/qemu` 与 `.work/build/qemu` 均在场，安装根二进制与构建树 md5 同为 `3541c06cd36c02f4de6e4482195c19f2`）。

## 目标（范围）

1. **spec rc 收口（并入本任务，不另立 SPEC 任务）**：
   - `spec/DADAO-12` §4.7 `cfx_hart` 表：`rc2 = cycle`（64 位）、`rc3 = insn`（64 位）、`rc4 = timer_cmp`、`rc5 = timer_ctrl`、`rc6`/`rc7` 保留；删除 `cycle_lo/hi`、`insn_lo/hi` 四行（128 位降 64 位）。
   - `spec/DADAO-12` §4.10 `cfx_time` 表：`cg10 rc0 = time_freq`、`rc1 = time_value`（64 位）、`rc2–rc63` 保留。
   - `spec/DADAO-22` §7/§10：`SBI_HART_SET_TIMER` 的 `timeout` 与 `SBI_TIME_GET` 的返回值明确为 **64 位**（语义不变）。
   - 两册附录 `### 0.7.3-rc（未发布）` 各追加 1 条（**不带任务号/ADR 号**，`check-spec-changelog` 机械断言）；册头版本 **不动**（仍 `0.7.3-rc`，`see-sbi` 互锁组两册一致）。
   - `manifests/spec-readonly.lock.toml`：同笔重算这两册 `sha256` + 追加一段注释（含授权原话摘要）；`make check-spec-readonly` 必须绿。
2. **别名/契约重生成（禁手改）**：`python3 tools/spec/gen_cfx_aliases.py`（产 `.tao/contracts/contract-cfx-aliases.md`）、`python3 tools/llvm/gen_cfx_alias_table.py`（产 `contracts/cfx-aliases.txt`）、`make install-cfx-aliases`（构建树 + 安装根副本）。
3. **LLVM lit/向量同步**（旧名/旧号引用清单见「接口规范 §2」）：`cfx-alias-runtime.s`、`cfx2-trap-escape.s`（`cfx_time_value` 由 `(18,10,8)` 变 `(18,10,1)`，`@enc` 须重派生）。
4. **QEMU 实现 `cfx_time`（cfxha 18）**：`cg10 rc0 = freq`（RO，常量 `1_000_000_000`）、`cg10 rc1 = value`（RO，64 位自由运行）；`SBI_TIME_GET` 读到该值。
5. **QEMU 实现单 hart `cfx_hart`（cfxha 15）**：`cg8 rc0 = hart_id`（RO 0）、`rc1` 保留、`rc2 = cycle`（RO，**64 位**）、`rc3 = insn`（RO，**64 位**）、`rc4 = timer_cmp`（RW，64 位绝对时间）、`rc5 = timer_ctrl`（RW：bit0 ENABLE、bit1 IMASK、bit2 ISTATUS 只读）、`rc6/rc7` 保留 ⇒ `CFXREG`；到期触发 `TIMER`（`1 << 10`）异步中断，`cause_info=0`；支持 IMASK 屏蔽 → pending → 解除后投递。**cycle/insn 本任务实现（64 位）**，测试机模型见「已确认口径 7」。
   - 异步投递**只复用**既有单来源路径（`pmem_dma_irq` 同型：per-source `bool` + `CPU_INTERRUPT_HARD` + `exec_interrupt` 独立分支 + `cfx_enter(async)`）；**不做**跨源统一 pending 位图/仲裁（见「已确认口径 9」）。
6. **测试专用 SBI provider + 新探针**：探针内嵌 ROM provider 实现 `SBI_TIME_GET`（FID 0）、`SBI_HART_GET_ID`（FID 0）、`SBI_HART_SET_TIMER`（FID 1）；新增 `min_rom_probe_integ050t.py`。
7. **回归收口**：既有 11 个 cfx 探针零回退；`tests/arch/umon/m5_perm_unimpl_cfxreg.s` 的「未实现 cfx」样本由 `cfx_hart`（本任务后已实现）改为 `cfx_llc`（cfxha 16），断言仍 `CFXREG`/`0x52`。
8. **契约与登记**：`contract-see.md` 补 cfx_time/cfx_hart 口径（含新 rc）与测试机范围；QEMU `changelog` 1 条；`Makefile`/arch `README.md` 登记新探针。

**明确不做**：不做跨源统一异步仲裁（PMEM_DMA + TIMER 各自复用单源路径；统一 pending 位图/优先级/合并投递登记「Linux 开发前」独立项）；不改 `cg5`/异常帧/escape 栈；不做嵌套异步；不实现 IPI/多 hart/多 hart 同步；不做生产 SBI provider；不跑夜跑；**不新建 SPEC 任务**；不改其它 spec 册（`DADAO-11/13/21/23`、`SimRISC-*`、`Toolchain-01`、`Machine-01`、`spec/README.md`）。

## 问题根源

1. **spec 现状与「64 位单寄存器」口径不符**：`DADAO-12 §4.7` 现为 `rc2–rc5 = cycle_lo/cycle_hi/insn_lo/insn_hi`（128 位拼装）、`rc6/rc7 = timer_cmp/timer_ctrl`；`§4.10` 现为 `cg10 rc7/rc8 = time_freq/time_value`。测试机（QEMU）按 64 位实现 count/时间，拼装式 128 位无实现价值，且 `time_freq/value` 落后的 `rc7/rc8` 与 cg8 的 `rc6/7` 语义并列易误读。⇒ 先在 spec 收口布局，再实现；`cycle`/`insn` 收口后**必须由测试机实现**（用户 2026-10-31 裁定：64 位，不得再留 `CFXREG`）。
2. **规范改动会机械级联**：`cg/rc` 是别名表生成器的唯一真源 ⇒ `.tao/contracts/contract-cfx-aliases.md`（含 `DADAO-12:<行号>` 来源列）与 `contracts/cfx-aliases.txt`（LLVM 运行时表）必须重生成；LLVM lit 里按旧名/旧号写的向量（`cfx_hart_cycle_lo`、`cfx_time_value (18,10,8)`）随之失效。三处任一漏改 ⇒ `check-cfx-aliases`/`check-cfx-alias-table`/`check-lit`/`check-cfx-vectors` 红。
3. **规范已定义、QEMU 未实现**：QEMU 现状（实测 `.work/source/qemu`）：
   - `target/dadao/helper.c:1482` `dadao_cfxha_map = {0,1,2,3,4,17,63}` ⇒ cfxha 15/18 走 `cfx_idx<0 ⇒ CFXREG`（`cpu.h:163` `DADAO_NUM_CFX 7`）；
   - `helper.c:1574 cfx_reg_ptr()` 无 cg8/cg10 分支，`cfx2rd/cfx2rc` 对 cfx15/18 一律 `CFXREG`；
   - 已有异步框架可复用：`helper.c:1784` PMEM DMA `QEMUTimer`、`helper.c:1669 cfx_enter(..., sync=false)`、`cpu.c:473 dadao_cpu_exec_interrupt()`、`cpu.c:279 dadao_pmem_dma_init()`；但没有通用定时器，也没有 `TIMER` cause。
   - `insn` 无现成计数可用：非 `-icount` 下 `icount_get_raw()` 恒 0（`accel/tcg/translator.c` 的 `CF_USE_ICOUNT` 门控）；`dadao_cpu_synchronize_from_tb()` 只在 `TB_EXIT_IDX1` 退出路径被调用、**不是**每 TB 执行钩子。⇒ 计数点只能放 `dadao_tr_tb_stop()`（`translate.c:598`；`dcbase->num_insns` 在 `tb_stop` 时已定型），须新增 `translate.c.patch`。
4. **测试面为零**：`grep cfx_time/cfx_hart tools/testcases/arch` 仅命中本任务要改的 m5 向量说明，无任何执行覆盖；`contract-see.md` 的测试机 cfx 范围只写到 cfx0/1/2/3/63 + cfx4/17。
5. **既有反向断言会被打破**：`tests/arch/umon/m5_perm_unimpl_cfxreg.s` 用 `trap cfx_hart, 0` 证明「已分配未实现 ⇒ CFXREG」；cfx_hart 落地后该 trap 会进入 cfx_hart（默认向量 `(15<<42)+0x3FFFFFF0000`，不可取指），期望必须换样本，否则 `check-arch-smoke` 红。
6. **SBI provider 现状**：仓库无生产 SBI provider（`.tao/knowledge/discussing.md`「SBI 生产 provider / W1C」= 后置）；现有范式是探针内嵌测试专用 provider（`min_rom_probe_integ047t.py:235-289`）。

## 已确认口径（用户给定，逐条落纸）

**用户授权原话（派单原话原样落纸，`docs/Process-06 §2/§5` 要求）**：

> “在 /mnt/tao/DADAO-v5，分支 `INTEG-050t`（任务书 `09b050e3`，未实现）。用户已确认把 rc 设计现在收干净，并把 spec 变更并入本任务，不另立 SPEC。”
> “已确认布局：`cfx_hart` cg8：rc0 hart_id；rc1 reserved；rc2 cycle（64）；rc3 insn（64）；rc4 timer_cmp（64）；rc5 timer_ctrl；rc6–7 reserved。`cfx_time` cg10：rc0 time_freq；rc1 time_value（64）；rc2–63 reserved。cycle/insn 由 128 位降为 64 位，删除 hi；timer_cmp/ctrl 前移；time_freq/value 前移。”
> “语义不变：TIMER 1<<10、ENABLE/IMASK/ISTATUS、SBI_HART_SET_TIMER 绝对时间、SBI_TIME_GET 64 位；`cfx_time_freq=1_000_000_000`；单 hart；不做 IPI/多 hart。”

**追加裁定（2026-10-31，本任务书修订依据）**：

> “在 /mnt/tao/DADAO-v5，分支 `INTEG-050t`。用户已定：050 不做统一异步仲裁；统一仲裁放到 Linux 开发前。另 cycle/insn 必须 64 位实现。”

1. **cfx_time**：per-system 全局、64 位、只读、无中断；`cfx_time_freq = 1_000_000_000`（测试机 1 GHz 十进制）；`SBI_TIME_GET` 返回 `cfx_time_value`；QEMU 用 `QEMU_CLOCK_VIRTUAL` ns，**1 count = 1 ns**。
2. **cfx_hart**：per-hart；**仅单 hart（hart0）**；`SBI_HART_GET_ID`、`SBI_HART_SET_TIMER`；`timer_cmp` 为 64 位绝对时间（单位同 `cfx_time_value`）；`timer_ctrl` 的 ENABLE/IMASK/ISTATUS；到期触发 TIMER 中断；支持 mask/pending；**不实现** IPI/多 hart/多 hart 同步。
3. **定时器为 one-shot**：每次写 `timer_cmp` 取消旧 deadline 并清除本次匹配条件；`timer_cmp = 0xFFFF_FFFF_FFFF_FFFF` 视为「关闭」（永不匹配）；重新 arm 必须再写 cmp（或 cmp 后写 ctrl）。
4. **ISTATUS 为计算结果**：`ISTATUS = ENABLE && cmp != all-ones && cfx_time_value >= timer_cmp`；写 ctrl 的 bit2 被忽略。
5. **IMASK 语义**：到期时 `IMASK=1` ⇒ 置 ISTATUS 并把 `1<<10` 置入**既有** `cfx_hart cg5 rc5` 的 pending 字段（`env->cfx[hart_ci].pending`，不是新位图），不投递；软件写 ctrl 使 `IMASK=0` 且 ISTATUS=1 ⇒ 清该位并经 `cfx_enter(async)` 投递 TIMER 中断。
6. **单 hart 时间基准**：`cfx_time_value` 复位后从 0 起算（记录 `time_base_ns = qemu_clock_get_ns(QEMU_CLOCK_VIRTUAL)`，读值 = 当前时钟 − base）；单 hart 下 per-hart 状态等价 per-system；多 hart 前须把 base 上移为 machine 级（本任务只登记遗留）。
7. **cycle/insn 实现（64 位，用户 2026-10-31：「cycle/insn 必须 64 位实现」）**：`cg8 rc2 = cycle`、`rc3 = insn` 均 RO、64 位、单调不减、写 ⇒ `CFXREG`。测试机模型（**测试机约定，非 spec 语义**；登记 `contract-see`）：
   - `cycle` = 自复位起的虚拟时钟周期数 = `qemu_clock_get_ns(QEMU_CLOCK_VIRTUAL) - time_base_ns`；测试机 1 GHz ⇒ 1 count = 1 ns，与 `cfx_time_value` 同基准（单 hart 下二者读数相等，属建模选择；**不另加状态**）。
   - `insn` = 已执行指令数：`dadao_tr_tb_stop()` 在 TB 收尾处把 `dcbase->num_insns` 累加进 `env->hart_insn`（64 位自然回绕）；**TB 粒度近似**（TB 内异常提前退出时该 TB 仍计满、不会少计），**不依赖 `-icount`**。
   - 两寄存器均无中断副作用；`rc1`、`rc6`、`rc7`、`cg10 rc2–rc63` 仍保留 ⇒ `CFXREG`。
8. **spec 改动范围与授权**：仅 `spec/DADAO-12`、`spec/DADAO-22` 两册按「目标 1」收口 + 附录条目；`manifests/spec-readonly.lock.toml` 同笔重算两册 sha256。**除此之外任何 spec 册零改动**；若执行中发现 spec 定义缺口/自相矛盾（超出上述布局）⇒ 停手登记 BLOCKED，不得自行扩范围。
9. **异步边界（用户 2026-10-31 裁定）**：TIMER **只复用现有单来源异步路径**（与 `pmem_dma_irq` 同型：per-source `bool` 标志 + `cpu_interrupt(CPU_INTERRUPT_HARD)` + `dadao_cpu_exec_interrupt()` 独立分支 + `cfx_enter(async)` 投递）。**不引入** per-hart 统一 pending 位图、跨源优先级、合并/去重；IMASK 的 pending 只写既有 `cfx[hart].pending`（即 `cfx_hart cg5 rc5` 的 bit10，既有 per-cfx 现场，不是新位图）。**统一 PMEM_DMA+TIMER 仲裁登记为「Linux 开发前」独立项**（见「后置独立项」），不在本任务实现。

## 接口规范

### 1. spec 变更（逐册逐条，`DADAO-12`/`DADAO-22`）

`spec/DADAO-12-SEE-主管系统运行环境.md` §4.7（`cfx_hart` 专有寄存器表，当前 8 行 `569–576`）：

- 保留 `| 8 | 0 | hart id | cfx_hart_hart_id | …`、`| 8 | 1 | — | — | … | 保留 |` 两行不动；
- 删除 `cycle lo`/`cycle hi`/`insn lo`/`insn hi` 四行，替换为：
  - `| 8 | 2 | cycle | cfx_hart_cycle | 0 | RO | 本地周期数（64 位） |`
  - `| 8 | 3 | insn | cfx_hart_insn | 0 | RO | 退休指令数（64 位） |`
- `timer cmp` 行 `rc 6 → 4`、`timer ctrl` 行 `rc 7 → 5`（名称/属性/说明文字与现文一致，仅 rc 前移）；
- 表末补两行保留：`| 8 | 6 | — | — | — | — | 保留 |`、`| 8 | 7 | — | — | — | — | 保留 |`；
- 表下说明段（`cfx_time_value >= cfx_hart_timer_cmp` …）语义不变，不动。

`spec/DADAO-12` §4.10（`cfx_time` 专有寄存器表，当前 `676–677`）：

- `| 10 | 0 | time freq | cfx_time_freq | — | RO | 计数频率（Hz），硬件设置 |`
- `| 10 | 1 | time value | cfx_time_value | 0 | RO | 64 位全局时间计数值，自由运行 |`
- 追加一行保留（`regname` 为 `—`，生成器按 `—` 跳过，不产别名）：`| 10 | 2-63 | — | — | — | — | 保留 |`。

`spec/DADAO-12` 附录 `### 0.7.3-rc（未发布）`：追加 1 条 bullet（**不写任务号/ADR 号**）：

> - `cfx_hart` 计数寄存器由 128 位 `cycle_lo`/`cycle_hi`/`insn_lo`/`insn_hi`（`cg8 rc2`–`rc5`）收为 64 位单寄存器 `cycle`/`insn`（`rc2`/`rc3`）；定时器比较/控制前移至 `rc4`/`rc5`，`rc6`/`rc7` 保留。`cfx_time` 的 `time_freq`/`time_value` 前移至 `cg10 rc0`/`rc1`，`rc2`–`rc63` 保留。

`spec/DADAO-22-SBI-主管系统二进制接口.md` §7 表第 1 行说明改 `设置本 hart 的定时器比较值（绝对时间）` → `设置本 hart 的定时器比较值（64 位绝对时间，单位同 cfx_time_value）`；§10 表第 1 行说明改 `返回全局时间计数值` → `返回全局时间计数值（64 位）`。**代码块不动**（`check-spec-codeblocks` 依赖）。

`spec/DADAO-22` 附录 `### 0.7.3-rc（未发布）`：追加 1 条（**不写任务号**）：

> - `SBI_HART_SET_TIMER` 的 `timeout` 与 `SBI_TIME_GET` 的返回值明确为 64 位绝对时间（单位同 `cfx_time_value`），语义不变。

两册册头版本**不动**（仍 `0.7.3-rc`；`see-sbi` 互锁组要求组内一致）。

`manifests/spec-readonly.lock.toml`：顶部注释区追加一段（含授权原话摘要：「把 rc 设计现在收干净，并把 spec 变更并入本任务」）说明只改 DADAO-12/22，并**同笔重算**这两册 `sha256`（其余 19 册不变）。

### 2. 别名/契约重生成 与 LLVM lit 同步（引用审计结论）

**审计范围与结论（本轮全仓 grep：`cycle_lo|cycle_hi|insn_lo|insn_hi|cfx_time_freq|cfx_time_value`，排除 `.git`、`.work`、`.cache`、`build` 目录）**：

| 位置 | 现状 | 处置 |
|------|------|------|
| `spec/DADAO-12:569-576,676-677` | 旧 rc/旧名真源 | 按 §1 改 |
| `.tao/contracts/contract-cfx-aliases.md:120-125,137-138` | 生成物（含 `DADAO-12:<行号>`） | `tools/spec/gen_cfx_aliases.py` 重生成，**禁手改** |
| `contracts/cfx-aliases.txt:848-853,1213-1214` | 生成物（LLVM 运行时表） | `tools/llvm/gen_cfx_alias_table.py` 重生成，**禁手改** |
| `tests/unit/llvm/lit/MC/DADAO/cfx-alias-runtime.s`（RUN/CHECK 共 6 处） | 以 `cfx_hart_cycle_lo` 作默认表样本 + 改名表基名 | 改 `cfx_hart_cycle`；改名表行 `reg cfx_renamed_hart_cycle 15 8 2 1 canonical`；2c「旧名不被接受」断言改为断言 `cfx_hart_cycle` 在改名表下报错（`cfx_hart_cycle_lo` 全文件移除） |
| `tests/unit/llvm/lit/MC/DADAO/cfx2-trap-escape.s:77-80` | `cfx_time_value` 标 `(18,10,8)`、`@enc 7a48a202` | 改 `(18,10,1)`；`@enc` **由 `validate_cfx_vectors.py` 独立派生**（预计 `0x7a48a042`，以脚本输出为准），`@@ OBJ:` 4 字节同步 |
| `tests/unit/llvm/lit/MC/DADAO/README-m5.md:54` | m5 行说明 `trap cfx_hart` | 按「§6 m5 改造」改为 `cfx_llc` |
| `tests/arch/umon/*`、`tools/**`、`tools/testcases/**` | 无旧名引用（已 grep） | 不动 |
| `docs/DDLN/C-资源管理/{DD,TT}-C008-*.md:35-36` | 讨论稿提到 `cycle_lo/hi` | **不改**（该稿整体停留旧 `timer` cfx 8 计数器设计，属既有过时讨论稿，非规格投影；登记遗留） |
| 历史审计快照（已删除）、`.tao/archive/**` | 历史层 | 不改 |

**重生成与生效顺序**（须按序，缺一则门控/实测读旧表）：

1. 改 spec（§1）→ `python3 tools/spec/gen_cfx_aliases.py`（期望输出：`寄存器别名` 由 1430 降为 1428，即 hart −2 条；实际以脚本输出为准）→ `python3 tools/spec/gen_cfx_aliases.py --verify` rc=0；
2. `python3 tools/llvm/gen_cfx_alias_table.py`（写 `contracts/cfx-aliases.txt`）→ `make check-cfx-alias-table` rc=0；
3. `make install-cfx-aliases`（构建树 + 安装根副本）→ `make check-cfx-alias-install` rc=0；
4. 改 lit 两文件 → `make check-cfx-vectors`、`make check-lit` rc=0。

### 3. 寄存器与值（改后真源：`DADAO-12 §4.7/§4.10`、`DADAO-22 §7/§10`）

`cfx_time`（cfxha 18，per-system）：

- `cg10 rc0 cfx_time_freq`：RO，恒 `1_000_000_000`；写 ⇒ `CFXREG`。
- `cg10 rc1 cfx_time_value`：RO，64 位；读为 `qemu_clock_get_ns(QEMU_CLOCK_VIRTUAL) - time_base_ns`（饱和到 0），单调不减；写 ⇒ `CFXREG`。
- `cg10` 的 `rc2–rc63`、以及 cfx_time 的其它 cg（cg0–3 共有寄存器除外）按未实现 ⇒ `CFXREG`。

`cfx_hart`（cfxha 15，per-hart，单 hart）：

- `cg8 rc0 hart_id`：RO，恒 0；写 ⇒ `CFXREG`。
- `cg8 rc1`：保留 ⇒ 读写均 `CFXREG`。
- `cg8 rc2 cycle`：RO，64 位；读 = `qemu_clock_get_ns(QEMU_CLOCK_VIRTUAL) - time_base_ns`（饱和到 0），单调不减；测试机 1 GHz ⇒ 1 count = 1 ns（与 `cfx_time_value` 同基准，单 hart 下读数相等）；写 ⇒ `CFXREG`。
- `cg8 rc3 insn`：RO，64 位；读 = `env->hart_insn`（`dadao_tr_tb_stop()` 按 `dcbase->num_insns` 累加，64 位回绕），单调不减；写 ⇒ `CFXREG`。
- `cg8 rc4 timer_cmp`：RW，64 位绝对时间；写新值取消旧 timer、清 ISTATUS/pending/irq；all-ones = 关闭。
- `cg8 rc5 timer_ctrl`：RW；写只接受 bit0 ENABLE、bit1 IMASK（bit2 忽略、其余位读回 0）；读回 = `ctrl[1:0] | (ISTATUS << 2)`。
- `cg8 rc6/rc7`：保留 ⇒ 读写均 `CFXREG`；`cg8` 其它 rc ⇒ `CFXREG`；cfx_hart 的 cg0–3 共有寄存器按既有通用实现。
- **`cg5 rc5 pending`（既有 per-cfx 现场）**：TIMER 的 IMASK pending 只置 bit10，不新建位图；写 `timer_cmp` 清 bit10。

`TIMER` 异常：cause id `1 << 10`、可屏蔽、`cause_info = 0`；cfx_hart 的 `cg5 rc63 cause_nonmaskable` 必须**只含** `CFXTRAP|CFXMEM|CFXREG|CFXESC`（bit10 可屏蔽；不得沿用 monitor 基集里的 `RASOF(1<<10)`）。

### 4. QEMU 改动（`components/qemu/patches/target/dadao/{cpu.h,cpu.c,helper.c,translate.c}.patch`）

1. **`cpu.h`**
   - `DADAO_NUM_CFX` 7 → **9**；`dadao_cfxha_map` 改为 `{0,1,2,3,4,15,17,18,63}`（数值升序）；同步结构注释与 `DADAO_CFX_IS_RESERVED` 说明（15/16/18 为已分配、非保留）。
   - 新常量：`DADAO_CFXHA_HART 15`、`DADAO_CFXHA_TIME 18`、`DADAO_CAUSE_TIMER (1ULL<<10)`、`DADAO_TIME_FREQ 1000000000ULL`、`DADAO_HART_TIMER_ENABLE (1<<0)` / `IMASK (1<<1)` / `ISTATUS (1<<2)`。
   - `CPUDADAOState` 新字段（沿用 PMEM 风格）：`uint64_t time_base_ns`、`uint64_t hart_insn`、`uint64_t hart_timer_cmp`、`uint8_t hart_timer_ctrl`、`bool hart_irq`、`QEMUTimer *hart_timer`。**`cycle` 不设状态**（由时钟派生）；`insn` 只用 `hart_insn`，**不新增**任何跨源 pending 位图/仲裁字段。
2. **`cpu.c`**
   - `dadao_cpu_reset_hold()`：`time_base_ns = qemu_clock_get_ns(QEMU_CLOCK_VIRTUAL)`；`hart_insn=0`、`hart_timer_cmp=0`、`hart_timer_ctrl=0`、`hart_irq=false`、`timer_del(hart_timer)`。
   - reset 的 `cause_nonmaskable` 覆盖：`cfxha==15` 与 `cfxha==18` 都置 `CFXTRAP|CFXMEM|CFXREG|CFXESC`（cfx_time 的异常表也只有这四项；cfx_hart 的 IPI/TIMER 均为可屏蔽，未实现的 IPI 不投递）。
   - `dadao_cpu_realizefn()`：调 `dadao_hart_timer_init(cs)`（`timer_new_ns(QEMU_CLOCK_VIRTUAL, ...)`）。
   - `dadao_cpu_exec_interrupt()`：PMEM 分支之后追加**独立的** TIMER 分支（`env->hart_irq` → `dadao_hart_timer_deliver(env)` → 另一源标志未置位时才 `cpu_reset_interrupt(cs, CPU_INTERRUPT_HARD)` → `return true`）；**两源各有自己的 bool 标志与分支，不建立统一 pending 位图、不比较优先级、不合并/去重**。唯一交互：某分支投递后若另一源标志仍置位，则**不清** `CPU_INTERRUPT_HARD`，由下一轮再次进入（保证不丢，属最小实现；真正的统一仲裁不在本任务）。PMEM 分支同法对称处理。
3. **`helper.c`**
   - map 改 9 项（与 `cpu.h` 一致）。
   - 新增 `dadao_time_reg_read(env, rc, &v)`：rc0→`DADAO_TIME_FREQ`；rc1→时间值；否则 false。
   - 新增 `dadao_hart_reg_read(env, rc, &v)`（rc0=0、rc2=cycle、rc3=insn、rc4=cmp、rc5=ctrl|ISTATUS；rc1/rc6/rc7/其它 false）与 `dadao_hart_reg_write(env, rc, v)`（仅 rc4/rc5 接受；rc2/rc3 及其它 false ⇒ `CFXREG`）。
   - 新增 `dadao_hart_timer_arm/expire/deliver`：
     - `arm`：`!ENABLE || cmp==all-ones` ⇒ `timer_del`；`now>=cmp` ⇒ `expire`；否则 `timer_mod(now + (cmp-now))`（deadline 直接用 cmp，因 1 count=1 ns）。
     - `expire`：`IMASK` ⇒ `env->cfx[hart_ci].pending |= DADAO_CAUSE_TIMER`（既有 per-cfx 现场，**不是**新位图）；否则 `hart_irq=true; cpu_interrupt(cs, CPU_INTERRUPT_HARD)`；不重装（one-shot）。
     - `deliver`：`hart_irq=false`；`cfx_enter(env, DADAO_CAUSE_TIMER, 15, env->pc, 0, false, &entered)`，entered 时 `env->pc=vec; env->rb[0]=vec`；被其它掩码挡住时 `cfx_enter` 自会置 pending（不轮询、不伪造）。
   - `helper_cfx2rd()`/`helper_cfx2rc()`：在既有 `cg==15 && pmem` 特例**之后**、`cg==7` 分支**之前**插入 cfx_time / cfx_hart 分支（保持 reserved → `cfx_idx<0` → `cfx_perm_denied` → `cfx_deleg_denied` 的权限门序；读无副作用；写按上表拒绝/接受）。用 `dadao_cfxha_map[ci]` 判别，不按 cfxha 硬编码。
   - `cfx_reg_ptr()` **不加** cg8/cg10 分支（由上面的显式分支承担；其余 cg 仍 NULL ⇒ `CFXREG`）。
   - user-mode 构建（`CONFIG_USER_ONLY`）：QEMUTimer/中断相关函数整体 `#ifndef`；`cfx_time`/`cfx_hart` 的定时器寄存器在 user-mode 返回 `CFXREG`（不得引用未定义字段），与 pmem 的既有做法一致；两种 target 都必须编译通过。`insn`/`cycle` 不依赖 QEMUTimer，user-mode 可正常读。
4. **`translate.c`（新增补丁，仅为 `insn` 计数）**
   - `dadao_tr_tb_stop()` 函数体首部（`switch (ctx->base.is_jmp)` **之前**）发 TCG 序列：`ld_i64(tmp, tcg_env, offsetof(CPUDADAOState, hart_insn))` → `addi_i64(tmp, tmp, dcbase->num_insns)` → `st_i64(tmp, tcg_env, …)`；**纯 TCG op，不加 helper、不改 `helper.h`**，64 位自然回绕。
   - 仅此一处；**不改** decode、`tb_start`、`tb_stop` 的既有跳转/`rb[0]` 逻辑，不改 `dadao_cpu_synchronize_from_tb()`。
5. **不改**：`cfx_enter()` 流程、`tlb_fill`、两轴权限、`cg7` 表、PMEM DMA、`-d cpu` dump 格式、`helper.h`。

### 5. 新探针 `tools/testcases/arch/min_rom_probe_integ050t.py`

布局沿用 `min_rom_probe_integ047t.py`（编码器/`Asm`/`run()`/`observe()`/`bootstrap_rom()` 就地复制，不 import、不改 047t）。默认 QEMU = `.work/build/qemu/qemu-system-dadao`；`--qemu/--only/--list/--doc`。期望值**手推自 `DADAO-12 §4.7/§4.10`、`DADAO-22 §7/§10`、`contract-see`**，不读 QEMU 实现。

**bootstrap（定时器用例必需，逐条落纸）**：

1. 复位在 power/hypv；进入 hmon 前把 `cfx_hmon hypv_switch_cfx_mask`（cfx3 cg3 rc9）的 bit15 清 0——它决定进入 hmon 后的 `inner_cfx_mask`，是 TIMER 投递的 step-3 门。
2. `trap cfx_hmon, 0` 进入 hmon；body 中再清：`cfx_hmon hypv_cfx_intr_mask`（cfx3 cg3 rc4）bit15、`cfx_hmon_global_cfx_intr_mask`（cfx3 cg8 rc1）bit15、`cfx_hart hypv_excp_cause_mask`（cfx15 cg3 rc11）bit10。
3. 设 `cfx_hart hypv_excp_vector`（cfx15 cg3 rc10）= 本 probe 的 TIMER handler 绝对地址；handler 记 `cause_id/cause_info` 与计数后 `escape cfx_hart, [excp_cause_ip, 0]`（定时器中断返回被中断指令边界）。
4. 沿用 047t 的 stage：清 `cfx_power` 四个 mode 的 `cfxmem/cfxexe` 源 mask，保证 handler（BootROM/power）在 `inner_cfx_code=15` 时可取指。
5. 定时器用例统一 `-icount shift=0`（1 ns/指令 ⇒ deadline 可数）；该模式无 `-d cpu` dump，一律**程序内自检 + `SYS_EXIT` 退出码**（同 047t `start_busy_returns_busy` 的做法），不得以 dump 缺失为由跳过。

**用例（17 条，每条须有可达 FAIL 路径；rc 全为改后新布局）**：

1. `doc_shape`（离线）：解析 `DADAO-12 §4.7/§4.10`、`DADAO-22 §7/§10` 表，断言 cfxha 15/18、`(cg,rc)`（8:0/1/2/3/4/5/6/7、10:0/1）、寄存器名（`cfx_hart_cycle`/`insn`/`timer_cmp`/`timer_ctrl`、`cfx_time_freq`/`value`）、访问属性、`cycle`/`insn` 为 **64 位**表述、FID 名/入参/出参与本任务接口一致；并断言旧名 `cycle_lo/hi`、`insn_lo/hi` 与旧 rc（8:4/5/6/7 旧布局、10:7/8）**已不存在**。
2. `time_freq_value`（默认时钟 + dump）：`cfx2rd(18,10,0,rd5)=1_000_000_000`；`cfx2rd(18,10,1,rd6)`、再读一次 `rd7` ⇒ `rd7 >= rd6`（单调不减，允许相等）。
3. `time_ro_cfxreg`（dump）：写 `rc0`/`rc1` 各 ⇒ `CFXREG`；读 `rc2`/`rc63` ⇒ `CFXREG`；逐条断言 `cid/cip`（当前 cfx 为 hmon）。
4. `hart_id_zero`（dump）：`cfx2rd(15,8,0,rd5)=0`；`SBI_HART_GET_ID` ⇒ `rd8=0`。
5. `hart_reserved_unimpl`（dump）：读 `cg8 rc1/rc6/rc7` 各 ⇒ `CFXREG`（3 次独立 fault，逐条 `cid/cip`）；写 `rc0`/`rc2`/`rc3` 各 ⇒ `CFXREG`（`rc2`/`rc3` 只读）。
6. `cycle_insn_read`（默认时钟 + dump）：`cfx2rd(15,8,2,rd5)`、`cfx2rd(15,8,3,rd6)` 均成功（不 fault）；两寄存器各连读两次 ⇒ `c2>=c1`、`i2>=i1`（单调不减，允许相等）；读数 `< 2^63`（非负）；**`insn` 读数 > 0**（bootstrap 已执行若干指令 ⇒ 证明计数不依赖 `-icount`）；`cfx2rc(15,8,2/3)` ⇒ `CFXREG`。
7. `cycle_insn_monotonic`（icount shift=0，自检）：读 `cycle`/`insn` 各一次 → 执行 `N=100000` 条延时环 → 再读 ⇒ `Δcycle >= N-4096`、`Δinsn >= N-4096` 且两者均严格增大（`-4096` = TB 结算粒度余量，任务书注明；计数器冻结或不计数 ⇒ Δ≈0 ⇒ FAIL）。
8. `timer_ctrl_rw`（dump）：`cmp=all-ones` 下写 ctrl=0、1、3，读回 bit0/bit1 与写入一致、bit2=0；写 ctrl=5（bit2=1）读回不为 5（bit2 不锁存）。
9. `timer_istatus`（icount，自检）：写 `cmp=now`（或 now−1）+ ctrl=1 ⇒ 读 ctrl 的 ISTATUS=1；写 `cmp=~0` ⇒ ISTATUS=0。
10. `timer_cmp_clears`（icount，自检）：到期后写新 `cmp=now+1_000_000` ⇒ ISTATUS=0，且不投递。
11. `timer_ones_disable`（icount，自检）：`cmp=~0`、ctrl=1，跑过 loop ⇒ ISTATUS=0、handler 计数 0。
12. `timer_interrupt`（icount，自检）：`cmp=now+2000`、ctrl=1，循环 >4000 条 ⇒ handler 恰 1 次，`cause_id=0x400`、`cause_info=0`、ISTATUS=1。
13. `timer_imask_pending`（icount，自检）：`cmp=now+1000`、ctrl=3，循环 >3000 条 ⇒ handler 0 次、ISTATUS=1、`cfx_hart cg5 rc5` 的 bit10=1；再写 ctrl=1 ⇒ handler 1 次、pending bit10=0。
14. `timer_retrigger`（icount，自检）：首次到期后再写 `cmp=now+1000` ⇒ handler 共 2 次（one-shot 可重装）。
15. `sbi_time_monotonic`（icount，自检）：`SBI_TIME_GET` 两次，中间执行 N 条指令的延时环 ⇒ `t2-t1 >= N`（1 ns/指令），且 `cfx_time_freq=1e9`。
16. `sbi_hart_set_timer`（icount，自检）：`SBI_HART_SET_TIMER(now+2000)` ⇒ 返回 0、handler 1 次、`cause_id=0x400`。
17. `regress_unimpl_cfx`（dump）：cfx5（cache）与 cfx16（llc）读 `cg0 rc0` 仍 ⇒ `CFXREG`（确认仅新增 15/18 两项）。

**观测**：寄存器类用 `-d cpu` 最后一块；定时器类用 icount + 自检退出码（`0x00` 通过；每例独立 FAIL 退出码，便于定位）。

### 6. 既有 m5 向量改造（不删用例、不放宽断言）

- `tests/arch/umon/m5_perm_unimpl_cfxreg.s`：`trap cfx_hart, 0` → **`trap cfx_llc, 0`**（cfxha 16，仍已分配未实现）；文件头/行内注释同步（含「测试机实现 cfx0/1/2/3/63 + cfx_ptw + cfx_time/cfx_hart」的现状说明）；断言 `cause == CFXREG`、pass token `0x52` 不变。
- `tests/arch/umon/expected.yaml`：该条 `derivation` 的 cfx_hart/15 改为 cfx_llc/16，仍 `expected_cause: CFXREG`、`expected_exit_code: 0x52`；name/coverage 不变。
- `tests/unit/llvm/lit/MC/DADAO/README-m5.md`：该行说明同步为 `trap cfx_llc`。
- **不改** `tests/arch.yaml`（按文件名引用）、`tools/testcases/validate_m5_vectors.py`（按 name 固定退出码）。

### 7. 契约 / 登记

- `.tao/contracts/contract-see.md`：
  - §3 的测试机 cfx 范围条扩为「cfx0/1/2/3/63 + cfx4 PTW/TLB + cfx17 SRAM/DMA + **cfx15 单 hart 定时器 + cfx18 全局时间**」；
  - 新增一条：`cfx_time`（cfxha 18）per-system、`cg10 rc0 = cfx_time_freq = 1 GHz`、`cg10 rc1 = cfx_time_value` 64 位只读自由运行、1 count=1 ns、不产生中断、`rc2–rc63` 保留；`cfx_hart`（cfxha 15）单 hart、`cg8 rc0 = hart_id=0`、`rc2 = cycle`（64 位 RO，测试机 = 虚拟时钟 ns、1 count=1 ns，与 `cfx_time_value` 同基准）、`rc3 = insn`（64 位 RO，测试机 = 已执行指令数，TB 粒度累加、64 位回绕）、`rc4 = timer_cmp`（64 位绝对时间）、`rc5 = timer_ctrl`（ENABLE/IMASK/ISTATUS）、到期 `TIMER (1<<10)` 可屏蔽、`cause_info=0`、写新 cmp 清条件、all-ones 关闭、`rc1`/`rc6`/`rc7` 保留；来源标 `DADAO-12 §4.7/§4.10`、`DADAO-22 §7/§10`。
  - 再补一条**异步边界**（测试机约定）：TIMER 与 PMEM_DMA 各用独立 per-source 标志经 `CPU_INTERRUPT_HARD` 投递、`cfx_enter(async)` 进入；**未定义**两源同时到达的优先级/合并/统一 pending 位图（属「Linux 开发前」独立项）；TIMER 的 IMASK pending 记录在 `cfx_hart cg5 rc5` 的 bit10。
  - 附录 A `§3` 行来源补 `§4.7`/`§4.10`；版本行不动。
- `components/qemu/changelog.md`：`## M10` 节文末追加 1 条（`- **2026-10-31 \`INTEG-050t\`**` + 摘要 + 执行者 engineer）。
- `Makefile`：`ARCH_CFX_PROBES` 末尾追加 `integ050t`，注释区补一行说明。
- `tools/testcases/arch/README.md`：表格补 `min_rom_probe_integ050t.py` 一行；`--qemu` 名单补 `integ050t`。

## 修改文件范围

**必改（21 项）**：

1. `spec/DADAO-12-SEE-主管系统运行环境.md`（§4.7/§4.10 表 + 附录 1 条）
2. `spec/DADAO-22-SBI-主管系统二进制接口.md`（§7/§10 说明列「64 位」+ 附录 1 条）
3. `manifests/spec-readonly.lock.toml`（两册 sha256 + 注释）
4. `contracts/cfx-aliases.txt`（重生成）
5. `.tao/contracts/contract-cfx-aliases.md`（重生成）
6. `components/qemu/patches/target/dadao/cpu.h.patch`
7. `components/qemu/patches/target/dadao/cpu.c.patch`
8. `components/qemu/patches/target/dadao/helper.c.patch`
9. `components/qemu/patches/target/dadao/translate.c.patch`（新增：`tb_stop` 累加 `hart_insn`）
10. `tools/testcases/arch/min_rom_probe_integ050t.py`（新增）
11. `tools/testcases/arch/README.md`
12. `Makefile`
13. `components/qemu/changelog.md`
14. `.tao/contracts/contract-see.md`
15. `tests/arch/umon/m5_perm_unimpl_cfxreg.s`
16. `tests/arch/umon/expected.yaml`
17. `tests/unit/llvm/lit/MC/DADAO/README-m5.md`
18. `tests/unit/llvm/lit/MC/DADAO/cfx-alias-runtime.s`
19. `tests/unit/llvm/lit/MC/DADAO/cfx2-trap-escape.s`
20. 本任务书（完成区 + 状态）
21. `.tao/knowledge/milestones.md`（仅本任务流水行状态）

**明确不动**：其它 `spec/**` 册与 `spec/README.md`；`.tao/adr/**`；`.tao/knowledge/discussing.md`（「Linux 开发前」后置项登记在**本任务书**「后置独立项」节，是否另立台账条目由用户决定）；`components/llvm-project/**`（别名是运行时表，**不重建 LLVM**）；`tests/arch.yaml`；`tests/inst/**`；`tests/shared/bootrom/**`；`docs/**`（含 `docs/DDLN/**` 过时讨论稿）；`.tao/archive/**`、历史审计目录（已删除）；`tools/spec/gen_cfx_aliases.py`、`tools/llvm/gen_cfx_alias_table.py`（生成器本身不改）；`target/dadao/helper.h`（不加 helper）。

## 约束

1. **不复用错误路径**：定时器投递必须走既有 §5 `cfx_enter(async)`；不新增第二套异常入口、不轮询伪造、不写死退出码。
2. **不做统一异步仲裁**（用户 2026-10-31 裁定）：TIMER 与 PMEM_DMA 各用独立 per-source 标志 + `exec_interrupt` 独立分支；**禁**新增 per-hart 统一 pending 位图、跨源优先级表、合并/去重逻辑；两源同时到达的语义未定义，登记「Linux 开发前」独立项，不在此处"顺手"实现。
3. **spec 改动严守授权范围**：只改 `DADAO-12`/`DADAO-22` 两册 + 锁文件；超出「§1 spec 变更」的改动 ⇒ 停手登记、交用户裁定。别名/契约两文件**只由生成器写**（`禁手改`，`check-cfx-aliases`/`check-cfx-alias-table` 机械校验）。
4. **单 hart**：`hart_id` 恒 0；`max_cpus=1` 不变；不实现 IPI 与多 hart 时间同步；`time_base_ns` 的 per-hart 局限登记遗留。
5. **补丁唯一来源**：改 `.work/source/qemu` → 收敛为 base+1 → `python3 tools/infra/make_patch.py qemu` 导出（含新增的 `translate.c.patch`，按 `series` 顺序）；**禁手改补丁**；`make check-patch-tree` + `make check-source-state` 必须绿。
6. **门控互斥**：构建/安装/门控一律经 `make`（自动 `flock`）；禁手工 `ninja`、禁手工 `cp` 二进制（`ISS-300`）、禁 kill 夜跑；若需 `build-qemu-reconfig` 或全量构建 ⇒ 停手上报。
7. **构建成本**：改 `.c/.h` 不动 meson ⇒ `make build-qemu` 增量（估算 1–3 min，`translate.c` 只影响 target 对象）；`install-host` 其余组件应 no-op；安装根与构建树 `qemu-system-dadao` md5 必须相同；**必须补跑 `make install-host`**（改 target 代码后门控读安装根，`ISS-210`）。LLVM **不重建**（别名表是数据）。
8. **证据**：`.work/evidence/<INTEG-050t>/run.sh` 一键复跑（`--default`/`--inject`/`--full`）；至少 1 项「注入 → FAIL → 还原 → 绿」，还原用 `cp`+`md5`，**禁** `git checkout/restore/stash/show`。
9. **临时目录** `/tmp/opencode/INTEG-050t/`；长日志落 `.work/log/integ/`；仓库内不得留 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`*.bak`。
10. **完成区与真实输出逐条对齐**；**不提交、不 push**（提交权归 architect）。完成区须含「spec 授权原话」与两册 `sha256`（旧/新）。

## 验收标准

1. **文件集精确（21 项）**：实现阶段 `git status --porcelain -uall` / 提交后 `git diff --name-only master...HEAD` 仅含上列 21 项；`spec/**` 仅 `DADAO-12`/`DADAO-22` 两册有 diff，其余 spec 册、`spec/README.md`、`.tao/adr/**`、`.tao/knowledge/discussing.md`、`components/llvm-project/**`、`tests/arch.yaml`、`tests/inst/**`、`docs/**` **零改动**；越界即 FAIL。
2. **spec 收口**：`DADAO-12` §4.7 表含 `8|2 cycle/cfx_hart_cycle`、`8|3 insn/cfx_hart_insn`、`8|4 timer_cmp`、`8|5 timer_ctrl`，且**不再含** `cycle_lo/cycle_hi/insn_lo/insn_hi`；§4.10 表为 `10|0 time_freq`、`10|1 time_value`，且不再含 `10|7`/`10|8`；两册附录各新增 1 条且**不含任务号**；册头版本仍 `0.7.3-rc`；`make check-spec-readonly` rc=0（两册 sha256 与锁一致）；`make check-spec-changelog`、`make check-spec-cite-targets` rc=0。
3. **别名/契约重生成**：两生成物与 spec 逐字节一致（`make check-cfx-aliases`、`make check-cfx-alias-table` rc=0）；`gen_cfx_aliases.py --verify` rc=0；条目数由 1430 降为 1428（贴脚本实际输出）；`make install-cfx-aliases` 后 `make check-cfx-alias-install` rc=0。
4. **LLVM lit/向量同步**：`cfx-alias-runtime.s` 全文无 `cycle_lo`（`grep` 零命中）、默认表/改名表/旧名三态仍全绿；`cfx2-trap-escape.s` 的 `cfx_time_value` 期望编码由 `validate_cfx_vectors.py` 独立派生一致（预计 `0x7a48a042`）；`make check-cfx-vectors`（16 条 0 错）、`make check-lit`（159/159）rc=0。
5. **cfxha 映射**：`DADAO_NUM_CFX=9`、map 含 15/18 且数值升序；`grep` 断言 `{0,1,2,3,4,15,17,18,63}`；cfx16 仍 `CFXREG`；且**无**新增跨源 pending 位图/仲裁字段（`grep` 断言 `hart_irq` 为单源 `bool`、无 `async_pending`/优先级表）。
6. **cfx_time**：`cg10 rc0 = 1_000_000_000`；`rc1` 两次读单调不减；写 `rc0`/`rc1` ⇒ `CFXREG`；`SBI_TIME_GET` 返回同一口径的值；icount 下两次读数差 ≥ 延时环指令数。
7. **cycle/insn（64 位实现）**：`cg8 rc2/rc3` 读到成功值（不 fault）、两次读单调不减、默认时钟与 `-icount shift=0` 两种模式下均成立；icount 下 `Δcycle >= N-4096`、`Δinsn >= N-4096`（N=100000）；写 `rc2`/`rc3` ⇒ `CFXREG`；`cycle` 与 `cfx_time_value` 同基准（单 hart 下相等，贴实测）；默认时钟下 `insn` 读到非 0 值（证明未依赖 `icount_get_raw`）。
8. **cfx_hart 寄存器**：`rc0=0`；`rc1`/`rc6`/`rc7` 读写 ⇒ `CFXREG`；`rc4`/`rc5` RW 回读符合位定义；ISTATUS 按 `ENABLE && cmp!=~0 && time>=cmp` 计算；all-ones 关闭。
9. **定时器中断**：到期 handler 观测到 `cause_id=0x400`、`cause_info=0`、ISTATUS=1；IMASK=1 时 handler 0 次、`cfx_hart cg5 rc5` bit10=1，解除后 handler 1 次且 pending 清零；重装后 handler 2 次；全程无轮询/伪造。
10. **异步边界（不引入统一仲裁）**：`dadao_cpu_exec_interrupt()` 中 PMEM 与 TIMER 为各自独立分支（贴代码片段）；无跨源择一/优先级/合并代码；`cfx[hart].pending` 是唯一 TIMER pending 记录；任务书「后置独立项」节含「统一 PMEM_DMA+TIMER 仲裁 = Linux 开发前」条目。
11. **m5 向量**：`m5_perm_unimpl_cfxreg` 改用 cfx_llc 后仍通过（`CFXREG`/`0x52`），`make check-arch-smoke` rc=0。
12. **既有探针零回退**：`044t/045t/049t/integ039t/integ040t/integ042t/integ044t/integ046t/integ047t/integ048t/integ049t` 全部 rc=0（逐项贴 `[PASS]`/计数）；新探针 rc=0 且 ≥17 例。
13. **组件闭环**：`check-patch-tree` rc=0（含 `translate.c.patch`，series 顺序正确）；`make build-qemu` rc=0（增量，贴耗时）；`make install-host` rc=0；安装根与构建树 `md5sum` 相同；`make check-source-state` rc=0（qemu base+1 clean）。
14. **门控**：L1 `make check`、L2 `make check-modules`、L3 `make check-full` 全绿；若 L3 有既有红项，必须 A/B（改前二进制同例同红）证明 pre-existing 并登记，**不得**改 tests 掩盖。
15. **契约/登记**：`contract-see.md` 含 cfx15/18 条目（含 cycle/insn 64 位与新 rc）与异步边界条、来源；`make check-contracts-dir` rc=0；changelog 恰 1 条且 `make check-component-changelog` rc=0；`Makefile` 与 arch `README.md` 登记就位。
16. **证据脚本**：`bash .work/evidence/<INTEG-050t>/run.sh` rc=0；`--inject` rc=0 且含可达 FAIL（建议：freq 改 `1e6` ⇒ `time_freq_value` FAIL；或删 `hart_insn` 累加 ⇒ `cycle_insn_monotonic` FAIL；或忽略 IMASK ⇒ `timer_imask_pending` FAIL；或删 `cpu_interrupt` ⇒ `timer_interrupt` FAIL），`cp`+md5 还原后回绿。
17. **收尾**：完成区 ≤30 行、`**状态**`=`待验收`、`milestones.md` 流水行同步；仓库无临时残留。

## 下发前预检（5 项，architect 本轮实测）

1. **任务书内部一致**：目标（8 项）/接口规范（spec 逐条 + 别名重生成与 lit 同步审计表 + 寄存器表 + QEMU **5 组**改动（`cpu.h`/`cpu.c`/`helper.c`/`translate.c` + 不改清单）+ 探针 bootstrap 5 步 + **17 例** + m5 改造 + 契约登记）/文件集（**21 项**）/验收（**17 条**）逐条对应；用户给定布局（hart rc0/1/2/3/4/5/6-7、time rc0/1/2-63、64 位、语义不变）与 2026-10-31 追加裁定（**cycle/insn 必须 64 位实现**、**不做统一异步仲裁、仲裁后置到 Linux 开发前**）逐条落纸。结论：**PASS**。
2. **验证手段前置实际可用（本轮实测，2026-10-31）**：
   - spec/契约链：`make check-spec-readonly`（21 册 OK）、`python3 tools/spec/gen_cfx_aliases.py --verify`（byte-identical）、`python3 tools/llvm/gen_cfx_alias_table.py --check`（12 scalars, 1430 regs，in sync）、`make check-spec-changelog`（互锁一致）、`make check-spec-cite-targets`（1823 条 0 unresolved）——全 rc=0；
   - 向量/lit：`make check-cfx-vectors`（16 条 0 错，1.7 s）、`make check-lit`（159/159，0.6 s）、`make check-cfx-alias-install`（6 checks）——全 rc=0；
   - 组件：`make check-patch-tree`（5 component(s), 205 patches OK）、`make check-source-state`（qemu `HEAD=7eedbc1b6dd5 count=1 clean=True`）——全 rc=0；
   - 既有探针：11 个 cfx 探针日志在 `.work/log/integ/INTEG-050t-precheck-probe-*.log`（末行 `RESULT: PASS`）；构建树与安装根 md5 同为 `7b7dc4291c3d0ef56227f14e444707ee`；`.dadao/gate.lock` 0 字节（未持有）、无在跑夜跑。
   结论：**PASS**。
3. **验收逐条可跑性**：验收 1–17 **现在可跑**；无 BLOCKED。定时器用例的 `-icount shift=0` + 自检通道已在 `integ047t::start_busy_returns_busy` 实测可用（rc=0）；`QEMU 11.1.1` 的 `accel/tcg/cpu-exec.c:842` 无条件调用 `cpu_exec_interrupt`（不经 `cpu_interrupts_enabled`），PMEM 已有的 `CPU_INTERRUPT_HARD` 路径是同一入口。**cycle/insn 计数点本轮实测核对**：`dadao_tr_tb_stop()` 见 `translate.c:598`、`dcbase->num_insns` 在 `tb_stop` 时已定型（`accel/tcg/translator.c:160/208`）；`dadao_cpu_synchronize_from_tb()` 只在 `TB_EXIT_IDX1` 退出路径调用（`accel/tcg/cpu-exec.c:466`），不可作计数钩子；非 `-icount` 下 `icount_get_raw()` 无推进（`CF_USE_ICOUNT` 门控）⇒ 选 `tb_stop` 累加 `hart_insn` 成立；`cycle` 由 `QEMU_CLOCK_VIRTUAL` 派生，无新状态。结论：**PASS（无 BLOCKED；`-icount` 下 timer 投递与 `tb_stop` 计数须在实现期以真实输出确认）**。
4. **与 `contracts/`、`tests/` 一致**：`contracts/cfx-aliases.txt` 与 `.tao/contracts/contract-cfx-aliases.md` 现为**旧 rc**，本任务同笔重生成（文件集 4/5）；LLVM 旧名/旧号引用已审计到具体行（§2 表）；`tests/inst/**` 无 cfx_time/hart 引用；既有反向断言 `m5_perm_unimpl_cfxreg.s` 以 cfx_hart 为未实现样本 ⇒ 已列入文件集 14–16；`contract-see.md` 范围过期 ⇒ 已列入 13。结论：**PASS（级联改造已全部纳入范围）**。
5. **拟改文件 × `spec/` 清单**：命中 **2 册**（`DADAO-12`、`DADAO-22`），**有用户授权原话**（见「已确认口径」引文：把 spec 变更并入本任务、已确认布局）⇒ **不构成 BLOCKED**；其余 spec 册零命中。ADR：不新建——cfx_time/cfx_hart 语义仍由 spec 定义，本任务只做「rc 布局收口 + 测试机实现 + `contract-see` 投影」；**cycle/insn 的测试机建模**（`cycle` = 虚拟时钟 ns、`insn` = TB 粒度累加）落 `.tao/contracts/contract-see.md` 的**测试机约定**，不改 spec 语义、不构成外部契约变更；异步边界同为测试机约定（`ADR-0046 D2` 方法依据，状态仍 Proposed，不因本任务改状态）。若 reviewer/用户认为需要 ADR，按「ADR 提醒」停手征询，不自行新建。

## 风险与已知缺口

1. **级联顺序**：spec → 别名（两生成物）→ `make install-cfx-aliases` → lit/向量。缺一即门控或实测读旧表（`ISS-210` 同类：门控与旧生成物自洽而假绿）。验收 3/4 已各设独立证据。
2. **cycle/insn 是模型近似**：`cycle` 与 `cfx_time_value` 同基准（单 hart 下读数相等），`insn` 为 TB 粒度累加（TB 内异常提前退出时该 TB 仍计满，只多不少），**不是**真实 CPI/流水线周期；`-icount shift=0` 下两者均按 1 ns/指令推进，默认时钟下 `cycle` 可能在同一 TB 内两次读到相同值（测试只要求单调不减）。若后续性能/内核代码需要精确周期模型，另立任务。
3. **中断投递首次实测**：既有 PMEM DMA 只测了轮询，未测 `CPU_INTERRUPT_HARD` 投递；`cpu_interrupts_enabled()` 恒 0 但当前 QEMU 版本不据此拦截（已核对源码）。若 timer 不投递，排查 `cpu_interrupt`/主循环，**不得**改为轮询或伪造。
4. **`-icount` 与 QEMUTimer**：`shift=0` 下 deadline 按指令数推进；实现期先用 `timer_interrupt` 单例确认，若主循环不触发则改用默认虚拟时钟 + 1 ms deadline 并记录依据（不改判据）。
5. **bit10 冲突**：`DADAO_CAUSE_RASOF`/`NSPERM` 也是 `1<<10`（不同 cfx 独立编址）；cfx_hart 的 `cause_nonmaskable` 必须显式覆盖，否则 TIMER 永不投递。
6. **per-system 时间落点**：`time_base_ns` 暂放 `CPUArchState`（单 hart 等价）；多 hart 前须上移 machine 级，登记遗留。
7. **IMASK pending 清除时机**：spec 未明写 `excp_pending` 的清除责任；本任务按「解除 IMASK 且 ISTATUS=1 时清 pending 并投递」实现；若 reviewer/用户认为应由软件写 pending 清除，停手裁定，不静默改。
8. **m5 向量连带**：不改文件集 14–16 则 `check-arch-smoke` 必红（cfx_hart trap 进入不可取指向量）；改造不得放宽断言（仍 `CFXREG`/`0x52`）。
9. **spec 锁与 `spec/README.md`**：只重算两册 sha256，其余 19 册不得漂移；`spec/README.md` 的版本表不动（未升版本号）。若 `check-spec-drift` 报口径不一致 ⇒ 停手上报，不自行改 README。
10. **`-d cpu` 多两行 dump**：既有探针按 `CFX%02d` 精确取名，不受新增行影响（已 grep 核实 044t/045t/046t/integ044t/integ048t/integ049t 的解析方式）；仍以全量探针复跑为准。
11. **user-mode 构建**：`dadao-linux-user` 同源编译，QEMUTimer 字段/函数须 `#ifndef CONFIG_USER_ONLY`，否则 linux-user 目标编译失败。
12. **构建/门锁**：若 `build-qemu` 触发 reconfig 或全量构建（10–30 min）⇒ 停手上报；L3 若遇既有红项，A/B 归因、不掩盖。
13. **两源不仲裁的已知空洞**：PMEM_DMA 与 TIMER 各有独立标志，`exec_interrupt` 按代码顺序逐个投递（PMEM 先）；同轮都置位时第二个源靠 `CPU_INTERRUPT_HARD` 未被清而在下一轮投递。**真正的统一仲裁**（per-hart 统一 pending 位图、优先级、合并/去重、多源扩展）登记为「Linux 开发前」独立项；**不得**在本任务顺手实现，也不写测试固化投递顺序（会挡住后续仲裁改造）。

## 后置独立项（「Linux 开发前」，本任务不实现）

1. **统一异步源仲裁（PMEM_DMA + TIMER，后续含 IPI）**（来源：用户 2026-10-31 裁定「050 不做统一异步仲裁；统一仲裁放到 Linux 开发前」）：
   - 内容：per-hart 统一 pending 位图 + 源优先级 + 合并/去重 + 与 `CPU_INTERRUPT_HARD` 单标志的正确复用；定义两源同时到达时的投递顺序、重复投递与丢失边界；配套测试（同时 arm DMA 与 TIMER）。
   - 现状（本任务）：两源各用独立 `bool`（`pmem_dma_irq`/`hart_irq`）+ 独立分支 + `cfx_enter(async)`；无位图、无优先级；语义在 `contract-see` 标「未定义」。
   - 时点：Linux 内核开发前的独立任务（不在 M10 通路内）。
2. **多 hart 前 `time_base_ns` 上移 machine 级**（现有遗留，随多 hart 任务处理）。
3. **cycle/insn 精确周期模型**（若性能分析需要真实 CPI/流水线周期，另行任务；当前为虚拟时钟 + TB 计数近似）。

## 完成区

**测试结果**：新探针 `min_rom_probe_integ050t.py` doc 0 failed + runtime 16/16（`--list` 17 条）；`check-arch` 12 个 cfx 探针全绿（含既有 11 个零回退）；`check-arch-smoke` 10/10 + 25-service PASS；L1 `make check` rc=0（`.work/log/integ/INTEG-050t-L1-final.log`）、L2 `make check-modules` rc=0（`…-L2.log`，`L2_EXIT=0`）、L3 `make check-full` rc=0（`…-L3.log`，`L3_EXIT=0`）；证据脚本 default 15 checks / 0 failed，`--inject` 5 checks / 0 failed（TIME_FREQ 1e9→1e6 ⇒ `time_freq_value` rc=1 ⇒ cp+md5 还原（`633565cd…`）⇒ 回绿）。
**修改文件**：21 项任务书清单全部落地（spec 两册 + 锁、两生成物、QEMU 4 补丁、探针、Makefile/README/changelog/contract-see、m5 三件、lit 两件、任务书、milestones）；**另 1 项计划外必需**：`tests/case-ledger.tsv`（L1 `check-case-ledger` 由 lit `@@ OBJ:` 现派生，`cfx2-trap-escape` 的 `7a48a202→7a48a042` 必须同步重生成，否则 L1 红；`--write` 后 diff 仅该 1 行）。合计 `git status -uall` = 22 文件（21 项清单 + 计划外 case-ledger；新增探针即清单第 10 项）；证据脚本在 `.work/evidence/INTEG-050t/run.sh`（非入库）。
**验收结果**：spec 授权原话（任务书已落纸）「把 rc 设计现在收干净，并把 spec 变更并入本任务」；`DADAO-12` sha256 旧 `d55fff183b178cfaf9bbdcc0ab85e565a979c8ccf532e3c79e3b1f12e248fa05` → 新 `556d1e5c8809194afdc84d0d6a7e9ce59de6d5bae50108a7684a97f0fb861dd6`，`DADAO-22` 旧 `7541b6e498706e14c3fd8811a43751a9f65c4359b9a60b284ffea54f8d58f5ac` → 新 `13893303056fdeb05fbfb57675de0c9932289f91cbce97a18de40f226e4c80ac`；`check-spec-readonly` 21 册 OK、`check-spec-changelog`/`check-spec-cite-targets` rc=0；别名 1430→**1428**（生成器现场输出）；`check-cfx-alias-{table,install}`、`check-lit` 159/159、`check-cfx-vectors` 16/0 全绿；`check-patch-tree` 205 patches、`check-source-state` qemu base+1 clean；构建树与安装根 `qemu-system-dadao` md5 同为 `3ff7ebe4db7470eb5005a95f10e070b0`（已跑 `make install-host`）。
**新发现/坑**：① **偏差（已披露）**：`tb_stop` 累加 `hart_insn` 在本 QEMU 不可达——helper/branch translation 已在 `translate_insn` 内 `exit_tb`，且 `goto_tb` 链式入口从首条指令体起跳、不走 TB 前言，置于 `tb_stop` 的 3 条 op 成为死码（实测环内 `Δinsn≈0`）。改为 `dadao_tr_insn_start` 每指令累加（`ld/add 1/st`，纯 TCG、无 helper），可观测契约不变且更准（64 位回绕、不依赖 `-icount`）；`contract-see` 已同步为「每指令派发时累加」。② `cpu_interrupt` 断言 `bql_locked()`：从 `cfx2rc` helper 同步触发到期时 BQL 未持有 ⇒ 用 `bql_locked()` 分支，未持有时 `cpu_set_interrupt`。③ 既有模型缺口：`helper_cfx_escape` 不恢复 `inner_cfx_code`（帧无 prev code），trap 返回后跨 cfx 访问会 `CFXPERM`；探针按测试机约定清 hmon/cfx15/cfx18 hypv 源 mask 的 bit15/18 规避，未改 escape 流程（任务禁改），建议另立任务。④ 探针 handler slot 起初重叠（hart provider 31 词越界覆盖 time provider）⇒ 分开 0x800/0x880。
**遗留问题**：`inner_cfx_code` 未随 escape 恢复（见 ③，跨模块/既有语义，需用户裁定是否另立任务）；`time_base_ns` 仍在 `CPUArchState`（多 hart 前须上移 machine 级，任务书后置项 2）；统一 PMEM_DMA+TIMER 仲裁按用户裁定后置「Linux 开发前」；`docs/DDLN/C-资源管理/{DD,TT}-C008` 旧 `cycle_lo/hi` 讨论稿未改（任务书明确不动）。

## 审阅记录

#### 第 0 轮 architect 规划（提交留痕）

- **档位**：WIP（任务状态仍 `待开始`、未实现）；提交信息 `docs: INTEG-050t 收口 time/hart rc 与 64 位`。
- **文件集对账**：`git diff --cached --name-only` = 1 项 = 本任务书（对应「修改文件」第 19 项）；无漏提/多提/越界；未 `push`。
- **本轮实测**：L1 `make check` rc=0（`.work/log/integ/INTEG-050t-architect-L1.log`）；`check-knowledge-refs` 悬空 0（改前该门控因证据路径未落盘而红，已改占位写法）。

#### 第 0 轮 architect 修订（2026-10-31，第二次提交留痕）

- **依据**：用户 2026-10-31 追加裁定（原话见「已确认口径」追加段）：`cycle/insn` 必须 64 位实现；050 不做统一异步仲裁，仲裁后置到 Linux 开发前。
- **改动段**：目标 5（+异步边界子条）/「明确不做」/问题根源 1、3/已确认口径 7、9（新增 9）+ 追加原话/接口规范 §3（rc2/rc3 实现）/§4（新增 `translate.c`；`cpu.h` 加 `hart_insn`；`exec_interrupt` 独立分支）/§5（15→17 例；rc1/rc6/rc7 保留）/§7（契约含 cycle/insn 与异步边界）/文件集（20→21 项）/约束（2 条新增：不做仲裁、`ISS-210` 安装根）/验收（15→17 条）/预检 1、3、5/风险 2、13 + 新增「后置独立项」节。
- **档位**：WIP（任务状态仍 `待开始`、未实现）；提交信息 `docs: INTEG-050t 明确 64 位计数与异步仲裁边界`。
- **文件集对账**：`git diff --cached --name-only` = 2 项（本任务书 + `.tao/knowledge/milestones.md` 流水行摘要）= 「修改文件」第 20、21 项范围；无漏提/多提/越界；未 `push`、未实现、未跑夜跑。

#### 第 1 轮 engineer 自审

**范围**：`cpu.h`/`cpu.c`/`helper.c`/`translate.c`（qemu 源 + 4 补丁）、新探针 17 例、spec/锁、两生成物、lit/m5、Makefile/README/changelog/contract-see。逐行核对「目标→实现→证据」；证据 = 本任务完成区与 `.work/log/integ/INTEG-050t-*.log`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `tb_stop` 累加 `hart_insn` 在 goto_tb 链式 TB 下不可达（`Δinsn≈0`，环内冻结） | ✅已修 | 移到 `dadao_tr_insn_start`（insn_start 之后、每指令 `ld/add 1/st` 纯 TCG）；`contract-see`/探针注释同步为「每指令派发时累加」 | `cycle_insn_monotonic` PASS；`Δinsn = N+1`（200/1000 swym 实测线性） |
| F2 helper 内 `cpu_interrupt` 断言 `bql_locked()`（超时/abort） | ✅已修 | 新增 `dadao_hart_notify()`：BQL 持有用 `cpu_interrupt`，否则 `cpu_set_interrupt`；只在 cfx_hart 路径使用，PMEM 路径未动 | `timer_istatus`/`timer_interrupt`/`timer_imask_pending` PASS |
| F3 探针 handler slot 重叠（hart provider 31 词压到 0x840 的 time provider，escape 落到错误 cfx） | ✅已修 | time provider 0x840→0x880；hart 0x800 保持 | `sbi_time_monotonic`/全部 icount 例 PASS |
| F4 阶段 mask 常量写成 `…FA_7FFF`（bit15 清但 bit3 被置 1）⇒ 一切 cfx15 源访问 `CFXPERM` 自旋 | ✅已修 | 改为 `…FB_7FF7`；hmon 用 `7FFF_…_FB_7FF7` | 全部 runtime 例 PASS；`cfx_perm_denied` 调试打印已移除（`grep DENY`=0） |
| F5 `add.si 1_000_000` 溢出 imms18（实际 −48576）导致新 cmp 落在过去 | ✅已修 | 改 `add.si 100000`（正值、仍远大于 4000 条观测窗） | `timer_cmp_clears` PASS |
| F6 `tests/case-ledger.tsv` 未在 21 项清单内，但 lit OBJ 字变更使 L1 必红 | ✅已修（披露） | 生成器 `--write` 重生成；diff 仅 `7a48a202→7a48a042` 1 行 | L1 `check-case-ledger` PASS（L1 终跑 rc=0） |
| F7 `ctrl=5` 读回期望写错（bit2 不锁存但 bit0 保留 ⇒ 读回 1） | ✅已修 | 期望改 `rd8 = CTRL_ENABLE` | `timer_ctrl_rw` PASS |
| F8 escape 不恢复 `inner_cfx_code`（既有模型缺口，跨 cfx 访问会 `CFXPERM`） | ⏸延后 | 未改 escape/cfx_enter（任务禁改）；探针按测试机约定清 hmon/cfx15/cfx18 hypv 源 mask bit15/18 规避 | 例：`trap cfx15 → cfx2rd cfx18` 由自旋改 PASS；遗留已登记 |

**判决**：F1–F7 已修并逐项复验；F8 属既有语义、超出本任务授权（禁改 escape 栈），已登记遗留并交用户裁定；无未修却影响本任务验收的 finding ⇒ 状态 `待验收`。

#### 第 1 轮 architect 提交审核（engineer 交付）

- **档位**：正常提交（engineer 置 `待验收`、自审 F1–F7 已修、F8 登记遗留）；提交信息 `feat(integ): INTEG-050t cfx_time 与单 hart cfx_hart`。
- **文件集对账**：`git status -uall` = 22 项；显式 staging 22 项 = 任务书 21 项清单（含新增 `tools/testcases/arch/min_rom_probe_integ050t.py`）+ 计划外 `tests/case-ledger.tsv`（仅 `7a48a202→7a48a042` 1 行）；无漏提/多提/越界；`spec/**` 仅 DADAO-12/22；无 `discussing.md`、`.tao/adr/**`、`tests/inst/**`、`components/llvm-project/**`；未 `push`。
- **本轮 architect 独立重跑**：`check-spec-readonly`/`check-spec-changelog`/`check-cfx-aliases`/`check-cfx-alias-table`/`check-cfx-alias-install`/`check-cfx-vectors`/`check-lit`/`check-case-ledger`/`check-contracts-dir`/`check-component-changelog`/`check-patch-tree`/`check-source-state` 全 rc=0；L1 `make check` rc=0；`check-arch-smoke` rc=0（`m5_perm_unimpl_cfxreg` exit=82 cause=CFXREG）；探针 `--list` 17 条、doc 0 failed + runtime 16/16 rc=0；证据 `--inject` 5/0（注入 ⇒ FAIL ⇒ cp+md5 还原 ⇒ 回绿，探针 md5 `66b73db2…` 不变）。
- **关键点核验**：64 位 `cycle`/`insn`（`uint64_t` + `ld/add/st i64`）、rc 布局 8:0/1/2/3/4/5/6/7 与 10:0/1/2-63、`DADAO_TIME_FREQ=1000000000`、单 hart、`TIMER=(1<<10)`、cfx15/18 `cause_nonmaskable` 覆盖、无 `async_enable`/统一仲裁（仅 `hart_irq`/`pmem_dma_irq` 两个 per-source bool + 独立分支）；别名 1428；安装根与构建树 qemu md5 均 `3ff7ebe4db7470eb5005a95f10e070b0`；`tb_stop`→`tr_insn_start` 偏差已在完成区「新发现/坑①」与 `contract-see` 披露。
- **结论**：可进 reviewer。

#### 第 1 轮 reviewer 验收

**重跑记录（reviewer 亲自执行，workdir=仓库根）**：

- 分支/树：`git branch`=INTEG-050t、HEAD=`d0cc9973`、`git status -uall`=0 行（干净）；`git diff master...HEAD --stat`=**22 文件**，逐项对账 = 任务书 21 项清单 + 计划外披露的 `tests/case-ledger.tsv`（1 行 `7a48a202→7a48a042`）；无 `discussing.md`、无 `.tao/adr/**`、spec 仅 DADAO-12/22 两册、无越界。
- 门控（全部亲跑）：L1 `make check` **rc=0**（`.work/log` 外留 reviewer 日志 `/tmp/opencode/INTEG-050t-review/L1.log`，FAIL=0）；L2 `make check-modules` **rc=0**（含 check-arch-smoke PASS + 25-service PASS）；`make check-arch` **rc=0**（12 探针全绿：044t/045t/049t/integ039t/040t/042t/044t/046t/047t/048t/049t/integ050t）；`check-spec-readonly` **rc=0**（21 册 OK）；`check-cfx-aliases` **rc=0**（byte-identical）；`check-lit` **rc=0**（159/159）；补跑 `check-cfx-alias-table`（**1428 regs**，in sync）、`check-cfx-alias-install`（6 checks PASS）、`check-cfx-vectors`（16 条 0 错）、`check-source-state` **rc=0**（qemu base+1 clean）、L3 `make check-full` **rc=0**（8/8 green）。
- 新探针：`--list`=**17 条**；`--doc` rc=0（doc 0 failed，逐行输出取自真实 spec 表）；runtime **16/16** rc=0（`timer_interrupt` 观测 cause_id=0x400、`timer_imask_pending`/`timer_retrigger`/`sbi_hart_set_timer` 均 PASS）。
- 关键点：`DADAO_NUM_CFX=9`、map `{0,1,2,3,4,15,17,18,63}`、`DADAO_CAUSE_TIMER (1ULL<<10)`、`DADAO_TIME_FREQ 1000000000ULL`（cpu.h.patch）；helper 分支次序 pmem→time→hart→cg7，`cfx_reg_ptr` 无 cg8/10（保留 ⇒ CFXREG）；cfx15/18 `cause_nonmaskable` 覆盖为 CFXTRAP|CFXMEM|CFXREG|CFXESC（cpu.c.patch）；`exec_interrupt` 两源独立 bool（`pmem_dma_irq`/`hart_irq`）独立分支，grep 无 `async_enable`/统一仲裁/优先级代码；cycle/insn = `uint64_t` + i64 TCG；安装根与构建树 `qemu-system-dadao` md5 同为 `3ff7ebe4db7470eb5005a95f10e070b0`；两册 sha256 现场实测 `556d1e5c…`/`13893303…` 与锁及完成区一致；`gen_cfx_aliases` 条数 1428（`grep -c "^reg "`=1428）。
- 证据脚本：审阅 `run.sh`（每条 `run_check` 捕获被检命令自身退出码、report 有 FAIL 路径、inject 用 cp+md5 非 git checkout）；亲跑 default **rc=0**（15 checks/0 failed）、`--inject` **rc=0**（注入 ⇒ `time_freq_value` rc=1 ⇒ md5 复原 ⇒ 回绿）。
- **reviewer 独立注入（产品侧，非 engineer 注入点）**：`cp` 备份 `.work/source/qemu/target/dadao/cpu.h`（md5 `9d795e69…`）→ sed `DADAO_TIME_FREQ 1e9→1e6` → `make build-qemu` rc=0 → 探针 `--only time_freq_value` **FAIL rc=1**（`rd5 exp=1000000000 got=0xf4240`）→ `cp` 还原 + md5 相等 → `make build-qemu` rc=0 → 构建树 md5 复原 `3ff7ebe4…`==安装根 → 探针 **rc=0** 回绿。
- 披露核验：`tb_stop→tr_insn_start` 偏差在完成区「新发现/坑①」披露且 `contract-see` 同步为「每指令派发时累加」（更贴 spec「退休指令数」语义，可观测契约不变，`cycle_insn_monotonic` PASS 实证）；`inner_cfx_code`（坑③）、`time_base_ns` 均登记遗留；后置独立项含统一仲裁。
- 长度/残留：完成区 8 行（≤30）、审阅记录各轮 ≤40 行；`git status -uall`=0、无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`*.bak`；`cfx-alias-runtime.s` 无 `cycle_lo`；m5 断言未放宽（仍 CFXREG/0x52）。

**非阻塞 finding（文档级，architect 收尾时顺带修）**：① cpu.h.patch 注释「`hart_insn` is accumulated at TB granularity」已过时（实为每指令累加）；② 完成区「22 文件（21 清单 + case-ledger）+ 新增探针」措辞冗余（探针已在 21 项内）；③ 任务书「执行环境」行仍写预检期 md5 `7b7dc429…`（终值以完成区 `3ff7ebe4…` 为准）。

**判决：Accepted**——验收命令块在我方重跑下全绿（含 L3）、22 项文件集精确、独立注入闭环成立、约束 1–10 无违反；可进入 `/complete`。

#### 第 1 轮 architect 交叉复核（`/complete`）

- **判决**：确认 **Accepted**；与 reviewer 判决一致，无遗漏关键验收项、无过松（约束 1–10 逐条无违反）。
- **文件集**：`git diff --name-only master...HEAD` = **22 项**，逐项 = 21 项清单 + 计划外 `tests/case-ledger.tsv`（1 行）；`spec/**` 仅 DADAO-12/22；无 `docs/**`、`.tao/adr/**`、`tests/inst/**`、`components/llvm-project/**` 越界。
- **关键点亲测**：`DADAO_NUM_CFX=9`、map `{0,1,2,3,4,15,17,18,63}`、`DADAO_TIME_FREQ 1000000000ULL`、`DADAO_CAUSE_TIMER (1ULL<<10)`、`uint64_t hart_insn` + `ld/add/st i64`；spec §4.7 `rc0/1/2/3/4/5/6/7`、§4.10 `rc0/1/2–63`；单 hart `hart_id=0`；`exec_interrupt` 为 `pmem_dma_irq`/`hart_irq` 两源独立 bool + 独立分支，全仓无 `async_enable`/统一 pending 位图/优先级代码；`contract-see` §56–58 含 cfx15/18 与异步边界条。
- **门控（最终树亲跑）**：L1 rc=0（`.work/log/integ/INTEG-050t-architect-L1.log`）、L2 rc=0（`…-L2.log`）、L3 rc=0（`…-L3.log`，8/8，report `20261031T142048Z`）；证据 default 15/0、`--inject` 5/0（注入 FAIL → cp+md5 还原 → 回绿）；探针 `--list`=17、runtime 16/16；`check-patch-tree`/`check-source-state`/`check-index-blobs` rc=0。
- **非阻断 finding 处置（文字级，不改实现）**：① `cpu.h` 注释改「`hart_insn` counts instructions in `dadao_tr_insn_start()`」→ 源 amend + `make_patch.py` 重导出（仅 `cpu.h.patch` 变）+ `make build-qemu`/`install-host`，md5 `3ff7ebe4…`→`3541c06c…`（构建树=安装根），探针/L1/L2/L3 复跑仍全绿；② 完成区措辞改「21 项清单 + 计划外 case-ledger（新增探针即第 10 项）」；③ 执行环境 md5 更新为 `3541c06c…`。
- **档位/提交**：正常（Accepted）；本提交 3 文件（本任务书 + `cpu.h.patch` 注释修正 + `milestones.md` 流水行）；未 push；统一报告落 `knowledge/` 由主会话执行。
