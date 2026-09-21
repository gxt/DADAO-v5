# QEMU-022t: TB 续接缺陷修复（dadao_tr_tb_stop 缺 gen_update_pc）

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-007t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-007t` 重构后的 `target/dadao/translate.c`（主翻译器）与 `insn_trans/trans_ctrl.c.inc`
  - QEMU v11.1.1 上游 `target/riscv/tcg/translate.c`（`gen_goto_tb`/`gen_update_pc`/`riscv_tr_tb_stop` 作对照参考）
  - `target/dadao/cpu.h`（`CPUDADAOState.pc` 定义）
  - `target/dadao/cpu.c`（`cpu_get_tb_cpu_state` 返回 `{.pc = env->pc}`）
- 输出：`components/qemu/patches/0008-dadao-tb-chain-fix.patch`（修改 `target/dadao/translate.c`）+ 更新 `components/qemu/patches/series`
- 约束：
  - **Spec-first**：TB 续接行为以 QEMU 标准 TB 语义（`env->pc` 在 TB 退出前必须反映下一条待执行指令地址）为规范来源，不从 dadao 实现反推
  - 修改范围仅限 `dadao_tr_tb_stop` 函数；不改 `trans_*` 指令语义
  - 修复后不得改变已通过验证的指令行为（`QEMU-005t`~`QEMU-013t` 全部回归）
  - 补丁 `0001`~`0007` 不修订；新缺陷修复以独立补丁 `0008` 承载

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

此前所有探针/向量因 TB 短（<100 条）而未触发。

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
| `translator_use_goto_tb` | 使用（检查 dest 是否在同一页） | 不使用 | 建议使用（对齐上游模式） |

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
        tcg_gen_movi_i64(tcg_constant_i64(ctx->base.pc_next),
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
- `tcg_gen_movi_i64` 把立即数写入 TCG temp，再 `tcg_gen_st_i64` 写入 `env->pc`。实际需用 `tcg_gen_st_i64(tcg_constant_i64(ctx->base.pc_next), tcg_env, offsetof(CPUDADAOState, pc))`。
- riscv 的 `gen_update_pc` 还维护一个 `ctx->pc_save` 缓存，dadao 无此字段可省略。
- `goto_tb(0)` 替换原来的 `goto_tb(1)`——slot 编号无语义差异，但 riscv 用 0。
- `exit_tb(ctx->base.tb, 0)` 启用 TB 链接（原来传 NULL 禁用）。
- 可选：加入 `translator_use_goto_tb` 检查（对齐 riscv 的 `gen_goto_tb` 模式），但 dadao 无 `itrigger`/`CF_PCREL` 复杂性，简化版本即可。

### 补丁归属建议

**建议：新建 `0008-dadao-tb-chain-fix.patch`**（不修订 `0001`）。

| 方案 | 优点 | 缺点 |
|------|------|------|
| **A：新 `0008`（推荐）** | 不改动已验证的 `0001`；补丁语义单一（只修 TB 续接）；可独立 revert | 补丁数量 +1 |
| B：修订 `0001` | 补丁数量不变 | 需重生成 `0001` 并重走 `003t` 验收（补丁 hash 变）；与「补丁已锁定」约定冲突 |

**判据**：(1) `0001` 已由 `QEMU-003t` 验证并 Accepted，修订它需要重走验收——成本高；(2) TB 缺陷是独立的代码错误，应由独立补丁承载（审计清晰）；(3) `0008` 的依赖仅为 `007t`（translate.c 拆分后的最终形态），不影响 `0001`~`0007` 的任何内容。

### 验证方式

**最小可复现测试（合成 ROM）**：

1. **96 条 `st.o-rd`（应 PASS）**：构造 ROM，96 条 `st.o rdN, rb0, N*8`（写 DUMP region）后 `st.o rd0, rb_exit, 0`（写 exit port）。期望 `exit=0`。
2. **100 条 `st.o-rd`（修复前 TIMEOUT，修复后 PASS）**：同上但 100 条。修复前 `exit=124`（死循环超时），修复后 `exit=0`。
3. **510 条 `set.zw`（修复前 TIMEOUT，修复后 PASS）**：构造 ROM，510 条 `set.zw rdN, imm` 后写 exit port。修复前 `exit=124`，修复后 `exit=0`。
4. **`-d exec` 验证**：修复后跑 100 条 `st.o-rd`，`-d exec` 输出应显示 PC 递增（非恒 `0xFFFF00000000`），且 TB 执行次数正常（非 46185 次）。

这些测试独立于 harness，可直接用 `tools/qemu/build_rom.py`（或等价脚本）构造二进制并以 `qemu-system-dadao -bios <rom>` 运行。

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
| 1 | `0008` 补丁存在且干净 apply 到 `0005` 后的 QEMU 源码 | 现在可跑 | `git am` + `make build-qemu` PASS |
| 2 | 96 条 `st.o-rd` 合成 ROM → `exit=0`（基线，修复前后均应 PASS） | 现在可跑 | 探针 `min_rom_probe_022t.py` |
| 3 | 100 条 `st.o-rd` 合成 ROM → `exit=0`（修复前 TIMEOUT `exit=124`） | 现在可跑 | 同上；修复前行为由 `QEMU-015t` reviewer C.3 证伪实验确认 |
| 4 | 510 条 `set.zw` 合成 ROM → `exit=0`（修复前 TIMEOUT `exit=124`） | 现在可跑 | 同上 |
| 5 | `-d exec` 验证：100 条 `st.o-rd` 执行后 PC 递增（非恒 `0xFFFF00000000`） | 现在可跑 | 探针 `min_rom_probe_022t.sh`；grep PC 值确认递增 |
| 6 | `QEMU-005t`~`QEMU-013t` 全部回归不退化（已有探针重跑） | 现在可跑 | `make build-qemu` + `min_rom_probe_005t.py`~`013t.py` + harness `reg-arith.yaml --case 1` |
| 7 | harness `--dump` 模式（full dumper）不再 TIMEOUT，`rb[1..63]` 非全 0、`pc` 非 0 | 现在可跑 | `run_qemu_test.py tests/vectors/isa/reg-arith.yaml --dump`；检查 `state.bin` 的 `rb`/`pc` |
| 8 | 反例验证：注释掉 `gen_update_pc` 行后 100 条 `st.o-rd` → `exit=124`（确认修复有效） | 现在可跑 | 注入反例 → 重 build → 验证 TIMEOUT → 还原 → 重 build → 验证 PASS |

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
