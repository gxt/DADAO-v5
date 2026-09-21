# QEMU-022t: TB 续接缺陷修复（dadao_tr_tb_stop 缺 gen_update_pc）+ exit-port 可靠 halt

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-007t`（`translate.c` 拆分后的最终形态）；验收 #7 另需 `QEMU-014t`、`QEMU-008t`（harness `--dump` 路径）
**状态**：待返工
> **第 1 轮 reviewer 判 Needs Revision（2026-09-21）**：`0008` 的 TB 修复正确，但暴露 **exit-port 退出码竞态**（`cpu_exit()`+`EXCP_INTERRUPT` 不能可靠停止外层 `cpu_exec`；最小复现 40 次中 5 次不一致）。经 architect 规划 + 用户逐条确认，范围扩展为「TB 续接修复 + exit-port 可靠 halt」，依据 **`ADR-0011`（Accepted，D1–D4 用户逐条确认）**。

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-007t` 重构后的 `target/dadao/translate.c`（主翻译器）与 `insn_trans/trans_ctrl.c.inc`
  - QEMU v11.1.1 上游 `target/riscv/tcg/translate.c`（`gen_goto_tb`/`gen_update_pc`/`riscv_tr_tb_stop` 作对照参考）
  - `target/dadao/cpu.h`（`CPUDADAOState.pc` 定义）
  - `target/dadao/cpu.c`（`cpu_get_tb_cpu_state` 返回 `{.pc = env->pc}`）
- 输出：`components/qemu/patches/0008-dadao-tb-chain-fix.patch`（**修订为 3 文件**：`target/dadao/translate.c` + `hw/dadao/dadao-machine.c` + `target/dadao/helper.c`）+ 更新 `components/qemu/patches/series`
- 约束：
  - **Spec-first**：TB 续接行为以 QEMU 标准 TB 语义（`env->pc` 在 TB 退出前必须反映下一条待执行指令地址）为规范来源；exit-port halt 以 **`ADR-0011` D1/D2** 为准（`cpu_loop_exit` + fault 不覆盖），不从 dadao 实现反推
  - **修改范围**（按 `ADR-0011` D3 修订）：`translate.c` 的 `dadao_tr_tb_stop` + `hw/dadao/dadao-machine.c` 的 exit-port handler + `target/dadao/helper.c` 的 `dadao_cpu_do_interrupt`；不改 `trans_*` 指令语义
  - **修复后不得改变已通过验证的指令行为**（`QEMU-005t`~`QEMU-013t` 全部回归），且须**确定**（不得出现不确定假失败）
  - 补丁 `0001`~`0007` 不修订；`0008` 为**单一原子补丁**（`ADR-0011` D3：TB 修复与 exit-port halt 不可分离）

## 背景（完整）

### 问题根源

`target/dadao/translate.c` 的 `dadao_tr_tb_stop` 函数（`translate.c:409-421`）在 `DISAS_NEXT` 和 `DISAS_TOO_MANY` 分支中：

```c
case DISAS_TOO_MANY:
case DISAS_NEXT:
    tcg_gen_goto_tb(1);
    tcg_gen_exit_tb(NULL, 0);
    break;
```

**缺失 `gen_update_pc`（即把 `ctx->base.pc_next` 写入 `env->pc`）**。

对照 QEMU 上游 riscv target（`target/riscv/tcg/translate.c:1424-1437`）：

```c
static void riscv_tr_tb_stop(DisasContextBase *dcbase, CPUState *cpu)
{
    DisasContext *ctx = container_of(dcbase, DisasContext, base);
    switch (ctx->base.is_jmp) {
    case DISAS_TOO_MANY:
        gen_goto_tb(ctx, 0, 0);  // → gen_update_pc(ctx, 0) + goto_tb + exit_tb
        break;
    case DISAS_NORETURN:
        break;
    default:
        g_assert_not_reached();
    }
}
```

其中 `gen_goto_tb` 内部执行 `gen_update_pc(ctx, diff)`（`tcg_gen_st_i64` 把 `ctx->base.pc_next + diff` 写入 `env->pc`）+ `tcg_gen_goto_tb(n)` + `tcg_gen_exit_tb(tb, n)`。

**机制解释**：QEMU TCG 的 TB（Translation Block）是 guest 指令的 host 机器码翻译单元。当一个 TB 因 TCG op buffer 满（store-heavy 指令约 100 条即触发）或 `max_insns`（默认 512）被切断时，`is_jmp = DISAS_NEXT/DISAS_TOO_MANY`，`tb_stop` 负责：(1) 更新 `env->pc` 到下一条 guest 指令地址；(2) 跳转到下一个 TB（通过 `goto_tb` 直接链接或 `exit_tb` 回到主循环重新查找）。dadao 的 `tb_stop` 只做了 (2)，没做 (1)，导致 TB 被切后 `env->pc` 仍为旧值 → `cpu_get_tb_cpu_state` 返回旧 PC → 下一个 TB 从同一地址重新执行 → **执行期死循环**。

### 影响面

**任意 TB 超限的 guest 程序**——不限于 harness/dumper。触发条件：
- TCG op buffer 满（store-heavy 指令 ≈100 条，`-d in_asm` 显示 TB 被切）：合成程序 96 条 `st.o-rd` → exit=0，**100 条 → exit=124**（死循环超时）
- `TCG_MAX_INSNS=512` 边界：500 条 `set.zw` → exit=0，**510 条 → exit=124**
- `-d exec` 证据：base TB 6s 内被执行 **46185 次**，PC 恒 `0xFFFF00000000`
- 直接后果：harness 的 `--dump` 模式（full dumper 131 条指令）触发死循环 → `rb[1..63]` 全 0、`pc=0`

**为何此前未被发现**：触发取决于 **TCG op-count**（而非 guest 指令条数）——已有探针/向量均未达 op-buffer 上限故未触发；注意 `ctrl-call[3]`（196 条指令）亦未触发，因其 op-count 未满。

### 目的

修复 `dadao_tr_tb_stop` 使其符合 QEMU 标准 TB 语义：TB 退出前必须更新 `env->pc`。修复后：
1. 任意长度 guest 程序不再死循环
2. harness `--dump` 模式的 full dumper 正常工作（`rb`/`pc` 正确）
3. 未来涉及长 TB 的 guest 程序（如 benchmark、内核引导）不会因此缺陷失败

### 对照关系

| 对照项 | QEMU riscv target（v11.1.1） | dadao target（当前） | dadao target（修复后） |
|--------|------------------------------|---------------------|----------------------|
| `tb_stop` 更新 PC | `gen_update_pc(ctx, 0)` 写 `env->pc` | ❌ 无 | ✅ 写 `env->pc = ctx->base.pc_next` |
| `tb_stop` goto_tb | `tcg_gen_goto_tb(n)` + `tcg_gen_exit_tb(tb, n)` | `tcg_gen_goto_tb(1)` + `tcg_gen_exit_tb(NULL, 0)` | `tcg_gen_goto_tb(0)` + `tcg_gen_exit_tb(ctx->base.tb, 0)` |
| TB 传参 | `exit_tb(ctx->base.tb, n)`（支持 TB 链接） | `exit_tb(NULL, 0)`（不支持链接） | `exit_tb(ctx->base.tb, 0)`（支持链接） |
| `translator_use_goto_tb` | 使用（检查 dest 是否在同一页） | 不使用 | **必须按上游模式处理**（守卫 `goto_tb`；跨页 TB 无守卫可能引入新错） |

**关键差异**：dadao 的 `tcg_gen_exit_tb(NULL, 0)` 传 NULL 给第一个参数（`tb`），这意味着不建立 TB 链接——每次 TB 退出都回到主循环重新查找。这本身不是 bug（只是性能差），但结合缺 `gen_update_pc` 就变成死循环。修复时应一并传入 `ctx->base.tb` 以启用 TB 链接优化。

### 修复方案

在 `dadao_tr_tb_stop` 的 `DISAS_NEXT`/`DISAS_TOO_MANY` 分支中，在 `goto_tb`/`exit_tb` 之前插入 PC 更新：

```c
static void dadao_tr_tb_stop(DisasContextBase *dcbase, CPUState *cs)
{
    DisasContext *ctx = container_of(dcbase, DisasContext, base);
    switch (ctx->base.is_jmp) {
    case DISAS_NORETURN:
        break;
    case DISAS_TOO_MANY:
    case DISAS_NEXT:
        /* 新增：更新 env->pc 到下一条指令地址 */
        tcg_gen_st_i64(tcg_constant_i64(ctx->base.pc_next),
                       tcg_env, offsetof(CPUDADAOState, pc));
        tcg_gen_goto_tb(0);
        tcg_gen_exit_tb(ctx->base.tb, 0);
        break;
    default:
        g_assert_not_reached();
    }
}
```

**注**：
- `tcg_gen_movi_i64` 签名是 **2 参**（`(TCGv, int64_t)`），**不能**用于写内存；必须用 `tcg_gen_st_i64(tcg_constant_i64(ctx->base.pc_next), tcg_env, offsetof(CPUDADAOState, pc))`（见上片段）。
- riscv 的 `gen_update_pc` 还维护一个 `ctx->pc_save` 缓存，dadao 无此字段可省略。
- `goto_tb(0)` 替换原来的 `goto_tb(1)`——slot 编号无语义差异，但 riscv 用 0。
- `exit_tb(ctx->base.tb, 0)` 启用 TB 链接（原来传 NULL 禁用）。
- **必须**按上游模式处理跨页 TB：用 `translator_use_goto_tb(&ctx->base, dest)` 守卫 `goto_tb`（不满足则退回 `exit_tb`/`lookup_and_goto_ptr`），否则可能引入新的跨页跳转错误（现有单页验收抓不到）。

### 修复方案 ②：exit-port 可靠 halt（`ADR-0011` D1/D2）

**问题**：exit-port handler 写退出码后仅 `qemu_system_shutdown_request_with_code()`，**不停止 vCPU**；后续 guest 指令（FAIL store / UNDI 终止符）会覆盖退出码（最小复现 40 次中 5 次不一致）。

**修法**（`ADR-0011` D1）：
- `hw/dadao/dadao-machine.c` 的 `dadao_exit_port_write()`：写入退出码并请求 shutdown 后，调用 **`cpu_loop_exit(env_cpu(env))`**（`longjmp` 立即回 `cpu_exec` 的 `setjmp` 点），保证**不再执行任何后续 guest 指令**。
- `target/dadao/helper.c` 的 `dadao_cpu_do_interrupt()`（`ADR-0011` D2）：开头加守卫 `if (qemu_shutdown_requested_get() != SHUTDOWN_CAUSE_NONE) return;`——shutdown 已请求时**不覆盖**已锁定的退出码。

**契约**：**首次写 exit port 即锁定退出码**（确定性）。

**禁止**：靠修改探针/向量掩盖竞态。

### 补丁归属建议

**建议：新建 `0008-dadao-tb-chain-fix.patch`**（不修订 `0001`）。

| 方案 | 优点 | 缺点 |
|------|------|------|
| **A：新 `0008`（推荐）** | 不改动已验证的 `0001`；补丁语义单一（只修 TB 续接）；可独立 revert | 补丁数量 +1 |
| B：修订 `0001` | 补丁数量不变 | 需重生成 `0001` 并重走 `003t` 验收（补丁 hash 变）；与「补丁已锁定」约定冲突 |

**判据**：(1) `0001` 已由 `QEMU-003t` 验证并 Accepted，修订它需要重走验收——成本高；(2) TB 缺陷是独立的代码错误，应由独立补丁承载（审计清晰）；(3) `0008` 的依赖仅为 `007t`（translate.c 拆分后的最终形态），不影响 `0001`~`0007` 的任何内容。

### 验证方式

**最小可复现测试（合成 ROM）**：

1. **96 条 `st.o-rd`（应 PASS）**：构造 ROM（**沿用 `tools/qemu/min_rom_probe_*.py` 的 `build_rom`/trampoline 模式**，ROM 落 `0xFFFFFFFF0000`）——**先装载 `rb17 = DUMP_BASE`（`0xFFFF_00FE_0000`）**，再 96 条 `st.o rdN, rb17, N*8`；写 exit port 用**非 rd0** 目的（如 `st.o rd18, rb_exit, 0`，rd18 预置 0）。期望 `exit=0`。**注意**：`st.o rdN, rb0, …` 会以 PC 为 base 写 ROM → ILLI；`st.o rd0, …` 命中 `store_src_rd0` 合法性 → ILLI。
2. **100 条 `st.o-rd`（修复前 TIMEOUT，修复后 PASS）**：同上但 100 条。修复前 `exit=124`（死循环超时），修复后 `exit=0`。
3. **510 条 `set.zw`（修复前 TIMEOUT，修复后 PASS）**：构造 ROM，510 条 `set.zw rdN, imm` 后写 exit port。修复前 `exit=124`，修复后 `exit=0`。
4. **`-d exec` 验证**：修复后跑 100 条 `st.o-rd`，`-d exec` 输出应显示 PC 递增（非恒 `0xFFFF00000000`），且 TB 执行次数正常（非 46185 次）。

这些测试独立于 harness，**沿用 `tools/qemu/min_rom_probe_*.py` 的模式**（自建 ROM 于 `0xFFFFFFFF0000`）构造二进制；运行须 **`-bios <rom> -kernel <kernel>`**（`dadao-m1` 机器强制两者，见 `hw/dadao/dadao-machine.c`）。注意仓库**无** `tools/qemu/build_rom.py`。

## 交付物

- `components/qemu/patches/0008-dadao-tb-chain-fix.patch`：修改 `target/dadao/translate.c` 的 `dadao_tr_tb_stop`
- `components/qemu/patches/series`：追加 `0008`
- `tools/qemu/min_rom_probe_022t.py`：最小 ROM 探针（96 vs 100 条 `st.o-rd`、510 条 `set.zw`）
- `tools/qemu/min_rom_probe_022t.sh`：`-d exec` PC 递增验证脚本

## 已知坑 / 结论

1. **`exit_tb(NULL, 0)` vs `exit_tb(tb, n)`**：原代码传 NULL 禁用 TB 链接（性能差但不致死循环）。修复时改为 `exit_tb(ctx->base.tb, 0)` 可启用链接优化，但需确认 dadao 的 `cpu_get_tb_cpu_state` 返回的 `.flags` 与 TB flags 一致（当前 flags=0，应无问题）。
2. **`goto_tb` slot 编号**：原用 `goto_tb(1)`，改为 `goto_tb(0)`。slot 编号在 QEMU 中仅用于 profile/debug 区分，无语义差异。
3. **translate.c 拆分影响**：`dadao_tr_tb_stop` 位于 `translate.c` 主文件（非 `insn_trans/*.c.inc`），`0005` 拆分只移动了 `trans_*` 函数，未动 `tb_stop`。故 `0008` 基于 `0005` 后的 `translate.c` 即可。
4. **store-heavy 触发阈值**：TCG op buffer 大小非固定值（取决于指令 mix），但 store-heavy 实测约 100 条即触发。修复后阈值不再有意义——任何长度的 guest 程序都能正确执行。

## 参考

- QEMU 上游 riscv target：`target/riscv/tcg/translate.c`（`gen_goto_tb`、`gen_update_pc`、`riscv_tr_tb_stop`）
- 本项目 `.tao/knowledge/deferred.md`「QEMU dadao target 的 TB 续接缺陷」条目（证据/影响面/修法）
- 本项目 `QEMU-015t` 审阅记录 C 节（reviewer 根因证伪实验）
- QEMU TCG 文档：`tcg/README`（TB lifecycle、`goto_tb`/`exit_tb` 语义）

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | `0008` 补丁（修订版，3 文件）干净 apply（`0001`–`0008` 全部应用） | 现在可跑 | `git am 0001→0008` + `make build-qemu` PASS |
| 2 | 96 条 `st.o-rd` 合成 ROM → `exit=0` | 现在可跑 | `min_rom_probe_022t.py` T1 |
| 3 | 100 条 `st.o-rd` → `exit=0`（修复前 TIMEOUT `exit=124`） | 现在可跑 | T2 |
| 4 | 510 条 `set.zw` → `exit=0`（修复前 TIMEOUT） | 现在可跑 | T3 |
| 5 | `-d exec`：100 条 `st.o-rd` 后 PC 递增（非恒 `0xFFFF00000000`） | 现在可跑 | `min_rom_probe_022t.sh` |
| 6 | **确定性**：最小复现（纯 fallthrough `st.o…0` 后 `st.o…1`）**40 次全部一致** | 现在可跑 | 修复前/仅方案 A 缺失时为 35/5 不确定（`/tmp/opencode/QEMU-022t/race_repro.py` 模式） |
| 7 | **`005t`~`013t` 各 ≥3 次回归全绿且确定** | 现在可跑 | 重点：`008t`/`009t`/`010t`/`013t` 不得出现 `exit=0x01` 假失败（第 1 轮实测 3/10、7/10、2/3、2/3） |
| 8 | harness `--dump` 的 `state.bin` 中 `rb[1..63]` 非全 0、`pc` 非 0 | 现在可跑 | `run_qemu_test.py tests/vectors/isa/reg-arith.yaml --dump` 后检查（dump 模式设计上自旋，恒报 `INCONCLUSIVE - Timeout`，**不可**作判据） |
| 9 | 反例：注释 `gen_update_pc` → 100 条 `st.o-rd` → TIMEOUT；还原+重建 → PASS | 现在可跑 | 注入 → 重 build → 验证 → 还原 → 重 build |
| 10 | 反例：注释 `cpu_loop_exit` → 确定性复现 40 次**不确定**；还原+重建 → 40 次全一致 | 现在可跑 | 证明 `cpu_loop_exit` 是确定性的必要条件（`ADR-0011` D1） |

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 reviewer 验收（2026-09-21）

> 本记录全部结论基于 reviewer 亲自重跑；日志见 `.work/log/qemu/QEMU-022t-review-*.log`，临时产物 `/tmp/opencode/QEMU-022t/`。

**判决：Needs Revision**（回归不确定失败 + 越界改动违反约束且未达目的）

#### A. 重跑记录（真实命令与输出）

**A1. 补丁完整性 —— PASS**
- 临时 worktree `c3d48b7`；`git am 0001→0008` **8/8 干净应用**（无 3-way、无 reject）。
- landing tree `e471ddd38fbc1a918caaf917cbbbc0d4b3fde96c` == 源树 HEAD (f769cc7) tree（**逐字节相同**）；8 个中间 commit tree 与源树逐一对 **MATCH**（`6590572b/ed041002/4a14648f/9e7eb733/8e28cda1/9e2c9376/5f8cd927`）。
- `git status --porcelain components/qemu/patches/` 仅 `M series` + `?? 0008`；**0001–0007 未被改动**；`series` 追加 0008 顺序正确。无手工拼接 hunk（tree 等价即证）。

**A2. build + 022t 探针（交付态 = 全 0008，记 S0）—— PASS**
- `make -C .work/build/qemu -j16` 无错误。
- `python3 tools/qemu/min_rom_probe_022t.py` → `T1/T2/T3 exit=0x00`，`Overall: PASS`，exit 0。
- `bash tools/qemu/min_rom_probe_022t.sh` → exit 0；`5 TB executions`，`Distinct PC values: 4`，`First PC: 0000ffffffff0000  Last PC: 0000ffffffff01b0`。

**A3. 回归（S0，多次重跑）—— 失败**
| 探针 | 运行 | 结果 |
|---|---|---|
| 005t | ×3 | 20/20 全绿 |
| 006t | ×3 | 34/34 全绿 |
| **008t** | **×10** | **仅 7 次全绿**；3 次失败（36/38、37/38、37/38），失败项 `T18 st.o-rb/ld.o-rb`、`T28 sub.so-rb`，均 `exit=0x01` |
| **009t** | **×10** | **仅 3 次全绿**；7 次失败（9–11/12），失败项 `T2/T5/T8 rela.si`，均 `exit=0x01` |
| **010t** | **×3** | **1 绿 / 2 失败**（27/28），失败项 `T7/T19/T25/T27/T28`，`exit=0x01` |
| 011t | ×3 | 28/28 全绿 |
| 012t | ×3 | 13/13 全绿 |
| **013t** | **×3** | **1 绿 / 2 失败**（21/22），失败项 `M1/M3/B2/B3/B9`，`exit=0x01`（每次失败的用例集合随机变化） |
| harness `reg-arith.yaml --case 1`（普通模式） | ×10 | 10/10 PASS |
| `make check` | ×1 | exit 0（178/178 identities OK；154 data gap 为既有） |

**A4. 决定性实验：越界改动是否必要 —— 结论「必要但不足」**
- **S1**（回退 `dadao-machine.c`+`helper.c`，保留 `translate.c`）→ 重 build：
  - 022t：`T1/T2/T3 全部 exit=0x89`（0/3，`Overall FAIL`）；
  - 008t ×5：`19/38、16/38、17/38、17/38、20/38`。
  - ⇒ **变红**。去掉这两处改动后 022t 直接失败 ⇒ 两处改动与 TB 修复**确有耦合、是 022t 通过的必要条件**；不是无理由的 scope creep。
- **S2**（回退 `translate.c`，即 0007 全量）→ 重 build：
  - 008t ×6 全 38/38、009t ×6 全 12/12、010t ×6 全 28/28、013t ×6 全 22/22 ⇒ **全绿且确定**。
- ⇒ 耦合由 `translate.c` 的 `gen_update_pc` 暴露：PC 前移后 CPU 会继续执行 exit-port 写之后的指令；`machine.c` 的 `cpu_exit()` + `helper.c` 的 shutdown 检查**只部分缓解**，未消除竞态（见 A5）。

**A5. 最小复现：exit-code 竞态（决定性证据）**
`/tmp/opencode/QEMU-022t/race_repro.py`，纯 fallthrough 序列 `set.zw rd18,0; st.o rd18,rb16,0; set.zw rd18,1; st.o rd18,rb16,0`：
```
S0（全 0008）   40 次 → exit=0x00: 35 / exit=0x01: 5
S2（pre-0008）  40 次 → exit=0x00: 40 / exit=0x01: 0
```
机制：第一次写 exit-port 后 vCPU 未被可靠停止，继续执行到 FAIL store（写 1）覆盖退出码；是否被停止取决于与主循环 shutdown 的竞态。这正是 008t/009t/010t/013t 失败项（`exit=0x01`，仅 FAIL 分支产生该值）的根因。engineer 坑 #2/#4 已描述该机制，但方案**未消除**它。

**A6. 验收 #7 —— PASS（engineer 标「⏸未执行」不成立）**
`python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml --case 1 --dump`（harness 自旋 → `INCONCLUSIVE`，属设计行为）后检查 `state.bin`（×3 完全一致）：
- `rb[1..63]` 非全 0：`rb_nonzero=3`（`rb1=0xffff00ff0000`、`rb2=0xffff00000000`、`rb62=0xffff00fe0000`）；
- `pc @ +0x400 = 0xffff00000210` ≠ 0。
按 #7 字面判据 **达标**；TB 修复已生效，不需要等 020t。（注：该判据偏弱，仅要求非全 0。）

**A7. 反例门控 #8 —— PASS**
- 注释 `gen_update_pc(ctx, dest)`（2 处）→ `git diff --name-only` = `target/dadao/translate.c`（**非空**）→ 重 build → 022t：`T1 PASS`、`T2/T3 [TIMEOUT] exit=0x7C`。
- 还原 `git checkout HEAD -- target/dadao/translate.c` → `git diff --name-only` **空** → **重 build** → 022t `3/3 PASS`。

**A8. 同类排查 —— engineer 说法属实**
- `target/dadao` 内所有 `exit_tb` 均在 `insn_trans/trans_ctrl.c.inc`，共 7 处（`gen_branch_taken` L348、`gen_branch_taken_rrii` L366、`trans_jump_iiii` L537、`trans_jump_rrii` L560、`trans_call_iiii` L617、`trans_call_rrii` L644、`trans_ret_riii` L669），**逐条**确认均在 `exit_tb` 前写 `env->pc` 与 `rb[0]`；jump/call/ret 均置 `DISAS_NORETURN`。
- `tb_stop` 的 `DISAS_NORETURN` 分支不写 pc 亦正确（该路径经 `raise_exception`/`cpu_loop_exit` 退出）。
- 偏离：`translate.c:431` 用 `exit_tb(NULL,0)`，**非**任务书规定的 `exit_tb(ctx->base.tb,0)`；跨页分支用 `lookup_and_goto_ptr`。属对任务书修复方案的偏离（engineer 坑 #1 有说明）。

#### B. 约束核验（逐条）

| 约束 | 结果 |
|---|---|
| 修改范围仅限 `dadao_tr_tb_stop` 函数 | **违反**：改 3 文件（`translate.c` + `hw/dadao/dadao-machine.c` + `target/dadao/helper.c`）。经 A4 证明耦合必要，属**设计层问题**，须架构师裁决，reviewer 不放行 |
| 修复后不得改变已通过验证的指令行为（005t~013t 全部回归） | **违反**：008t/009t/010t/013t 出现不确定失败（A3） |
| 退出码协议（ADR-0004）不被后续指令覆盖 | **违反**：A5 最小复现证明 exit code 可被覆盖 |
| `0001`~`0007` 不修订；独立 `0008` | 守住（A1） |
| 补丁 `series` 正确、干净 apply | 守住（A1） |
| Spec-first（以 QEMU 标准 TB 语义为准） | 部分：`tb_stop` 更新 pc 符合；但 `exit_tb(NULL,0)` 偏离任务书规定，且未达成「TB 退出后语义正确」的最终目标 |

#### C. 判决依据与修改建议

**Needs Revision**，具体失败命令/约束：
1. **回归不确定失败**：`min_rom_probe_008t/009t/010t/013t.py` 在交付态多次运行出现 `exit=0x01` 假失败（008t 3/10、009t 7/10、010t 2/3、013t 2/3 次运行有失败）。完成区「008t 38/38、009t 12/12（多次运行确认）」**不可复现**，违反「至少重跑一次为真」与「回归不退化」约束。
2. **越界改动 + 未达目的**：`hw/dadao/dadao-machine.c`、`target/dadao/helper.c` 超出任务书范围；A4 证明其必要、A5 证明其不足。属阻断性设计问题，须架构师定夺路线（重新划定范围并设计可靠的 vCPU halt，或改造 exit-port 语义）。
3. **验收 #7 未执行**：任务书标注「现在可跑」，engineer 推迟到 020t；reviewer 实测可达标（A6）。

**根因与修复方向（供返工/架构师参考）**：
- `cpu_exit()` 置 `exit_request` 后，`cpu_handle_interrupt` 将其转为 `EXCP_INTERRUPT`，而 `cpu_handle_exception` 对 `EXCP_INTERRUPT` 返回 false（engineer 坑#4），故外层 `cpu_exec` 不停；exit-port 写后仍有指令执行窗口 → 覆盖退出码。
- 需在 exit-port handler 采用**可靠 halt**（使写 exit-port 后不再执行任何 guest 指令，例如令 vCPU 以 `EXCP_HLT`/等价语义退出循环），而不是仅 `qemu_system_shutdown_request + cpu_exit`。
- 建议将 `0008` 拆为「`tb_stop` pc 修复」+「exit-port 可靠 halt」两个补丁（各自可独立验收）；单独 `tb_stop` 修复已被 S1 证明会破坏退出码，必须与可靠 halt 同交付。
- 不建议通过「让探针的 exit 写之后不可 fall-through」来掩盖——那是 §「不许凑绿」禁止的规避，且真实 guest/harness 同样可能受影响。

#### D. 附带记录（只报告）

- 源树提交作者 `Reviewer <reviewer@example.com>`（`0006`/`0007`/`0008` 均然，`git config user.name=Reviewer`）——影响补丁可审计性/署名真实性；建议登记 `deferred.md`（由主会话决定）。
- 完成区 #5 所列 PC「0x0000→0x00d8→0x01ac→0x01b0」与真实输出不符（真实为 `0xffffffff0000→…→0xffffffff01b0`，仅截断）；机理结论不受影响。
- `tools/qemu/min_rom_probe_022t.sh` 未 `mkdir -p /tmp/opencode/QEMU-022t`，依赖外部预建目录（本次由 reviewer 预建才通过）；属健壮性缺陷，非阻断。
- 交付态工作区：`git status` 仅 `M .tao/tasks/...022t.md`、`M components/qemu/patches/series`、`?? 0008 patch`、`?? tools/qemu/min_rom_probe_022t.{py,sh}`；**无仓库根新文件**；`.work/source/qemu` 工作区干净（reviewer 注入的反例已还原并重建；临时 worktree 已移除）。
