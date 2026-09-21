# QEMU-020t: harness dumper 改造（TB 安全分段 + `--dump` 端到端验收）

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-015t`、`QEMU-008t`、`QEMU-022t`
**状态**：待开始

> **2026-09-21 重划（architect 规划）**：原任务书交付物 #1「harness 普通模式不 emit dumper」已由 `QEMU-015t` 落地（`build_test_binary.py` 的 `if dump_mode:` 条件化），**重叠已消除**。本任务缩窄为：(1) TB 安全分段 dumper（使 `--dump` 在 TB 续接缺陷未修或已修两种场景下均可工作）；(2) `--dump` 端到端验收（`rb`/`pc` 正确）。验收 #4「`--dump` 行为不变」已修订为「`--dump` 输出正确」。

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-015t` 交付的 `tests/scripts/build_test_binary.py`（含 `build_dumper_section`、`build_exit_section`、`emit_state_compare`）
  - `QEMU-015t` 交付的 `tests/scripts/run_qemu_test.py`（含 `QMPClient`、`--dump` 模式、CLI fail-closed）
  - `QEMU-008t` 实现的 `rb2rd`/`st.o-rb` 语义（dumper 可用）
  - `QEMU-022t` 修复的 TB 续接（若已修复，dumper 不需分段即可工作；若未修复，dumper 需分段）
- 输出：修改后的 `tests/scripts/build_test_binary.py`（分段 dumper + 完整 dump 通道验证）
- 约束：
  - 不改 harness 的 loader/exit/比较逻辑
  - 不改 QEMU 补丁（QEMU 侧 TB 缺陷由 `QEMU-022t` 修复）
  - 普通模式不 emit dumper（已由 `015t` 实现，本任务不改）
  - 完成后不自行 commit

## 背景（完整）

### 目标

使 harness 的 `--dump` 模式能正确导出全部寄存器（`rd[1..63]`、`rb[1..63]`）和 PC，解决 `015t` 验收 #6（BLOCKED）的问题。

### 设计理由

`QEMU-015t` 已实现普通模式不 emit dumper（ADR-0010 D1 修法 a 落地），但 `--dump` 诊断模式的 full dumper 仍不可用——`rb[1..63]` 全 0、`pc=0`。

**根因有两层**：
1. **QEMU TB 续接缺陷**（`QEMU-022t` 修复）：full dumper（131 条 store 指令）超过 TCG op buffer 上限 → TB 被切 → `env->pc` 未更新 → 死循环。这是 QEMU 实现缺陷。
2. **dumper 未做分段防护**：即使 TB 缺陷存在，如果 dumper 每段指令数低于 op-buffer 阈值（store-heavy 实测 ≈40 条安全），段间插入显式控制流（如 `jump`，会写 `env->pc`），即可绕过缺陷。

**本任务的定位**：
- **若 `022t` 先完成**：TB 缺陷已修，dumper 不需分段即可工作。本任务简化为「验证 `--dump` 输出正确」。
- **若本任务先完成**：dumper 采用分段策略（防御性设计），即使 TB 缺陷未修也能正确 dump。`022t` 完成后可移除分段逻辑（简化代码）。
- **交付关系**：分段是 workaround（绕过缺陷），`022t` 是根治。**本任务依赖 `022t`**（见文件头 `**依赖**`）——若 `022t` 已修，分段默认关闭、直接验证 `--dump` 输出；若 `022t` 未修（并行场景），分段生效以保证 `--dump` 仍可用。

### 关键概念 / 数据

**TB 安全分段 dumper 方案**：

dumper 段负责把 `rd[1..63]`、`rb[1..63]`、PC 写入 dump region（基址 `DUMP_BASE = 0xFFFF_00FE_0000`，见 `build_test_binary.py:32`；`rd[i]@+0x008+(i-1)*8`、`rb[i]@+0x208+(i-1)*8`、`pc@+0x400`）。

当前 dumper 为单段 emit：约 131 条 `st.o-rd`/`st.o-rb` + `rb2rd` 指令。在 TB 续接缺陷下，这 131 条被切 → 死循环。

分段策略：
```
段 1: st.o rd1..rd40 → dump region     (40 条 store)
段间: jump rb0, rd0, 1                  (1 条显式控制流，写 env->pc)
段 2: st.o rd41..rd63 + rb2rd rd63,rb0 + st.o rd63 → PC slot  (约 25 条)
段间: jump rb0, rd0, 1
段 3: st.o-rb rb1..rb40 → dump region  (40 条 store)
段间: jump rb0, rd0, 1
段 4: st.o-rb rb41..rb63 → dump region (约 23 条)
```

每段 ≤40 条 store-heavy 指令，低于 op-buffer 阈值。段间的 `jump` 是显式控制流指令（非 store），会触发 TB 切断并正确写 `env->pc`（因为 `trans_jump` 内部设置了 `is_jmp = DISAS_BRANCH`，走 `DISAS_NORETURN` 路径而非 `DISAS_NEXT`）。

**reviewer 实验证据**（`QEMU-015t` 第 2 轮审阅 E 节）：
- 100 条 `st.o-rd` 不分段 → `exit=124`（死循环）
- 每 40 条插入一条 `jump rb0, rd0, 1` → **`exit=0`**
- 每 20 条插入 → 亦 `exit=0`

**阈值选择**：store-heavy ≈40 条安全。保守值取 32 条（留余量）。

## 交付物

- 修改后的 `tests/scripts/build_test_binary.py`：
  - `build_dumper_section()` 改为分段 emit（每段 ≤N 条 store，段间插入 `jump`）
  - 段长 N 可配置（默认 32）
- `--dump` 端到端验证：`reg-arith.yaml --dump` 的 `state.bin` 中 `rd[1..63]`、`rb[1..63]`、`pc` 全部正确

## 已知坑 / 结论

1. **分段不影响普通模式**：普通模式不 emit dumper（`015t` 已实现），分段逻辑只在 `dump_mode=True` 时生效。
2. **段间 `jump` 需要合法操作数**：`jump rb0, rd0, 1` 跳转到 `rb0 + rd0 + (1<<2)`。由于 rb0 在 dumper 中可能被修改（`rb2rd`），段间 `jump` 的目标地址需确保安全（跳到下一段第一条指令）。最简方案：段间用 `swym`（NOP）+ 依赖 TB 切断自然发生（不显式 `jump`）。但 `swym` 不会触发 `DISAS_BRANCH`，TB 可能仍被 op-buffer 切断而不更新 `env->pc`。**结论：必须用显式控制流指令（`jump`/`br.nz`）作为段间分隔**。
3. **`022t` 先完成时的简化**：若 `022t` 在本任务之前完成，TB 缺陷已修，分段逻辑可省略——`build_dumper_section` 保持单段 emit 即可。此时本任务退化为纯验收（验证 `--dump` 输出正确）。
4. **`015t` 与本任务的边界**：`015t` 已交付 `if dump_mode:` 条件化（交付物 #1），本任务不再重复。本任务只管 `--dump` 路径内部的分段逻辑与输出验证。

## 参考

- 本项目：`.tao/knowledge/adr-0010-qemu-task-restructure.md` D1
- 本项目：`QEMU-015t` 审阅记录 E 节（reviewer 分段实验：40 条分段 → exit=0）
- 本项目：`QEMU-015t` 审阅记录 F 节（020t 重叠判定）
- 本项目：`.tao/knowledge/deferred.md`「QEMU dadao target 的 TB 续接缺陷」条目
- 本项目：`QEMU-022t`（TB 缺陷根治）

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | `build_dumper_section()` 实现分段 emit（diff 确认每段 ≤N 条 store + 段间显式控制流） | 现在可跑 | 代码审查 |
| 2 | `--dump` 模式 `reg-arith.yaml --case 1` 后 `state.bin` 内容正确 | 现在可跑 | `008t` 已验证（`rb2rd`/`st.o-rb` 可用）。**注意**：dump 模式设计上自旋，harness 恒报 `INCONCLUSIVE - Timeout`，**不可**把「不再 TIMEOUT」作判据 |
| 3 | `--dump` 的 `state.bin` 中 `rd[1..63]` 非全 0 | 现在可跑 | `008t` 已验证；替代：最小 ROM 探针（自建 dumper 段） |
| 4 | `--dump` 的 `state.bin` 中 `rb[1..63]` 非全 0 | 现在可跑 | `008t` 已验证；TB 缺陷未修时靠分段绕过，已修（`022t`）时直接可用 |
| 5 | `--dump` 的 `state.bin` 中 `pc(+0x400)` 反映真实 PC（非 0） | 现在可跑 | 同上 |
| 6 | 普通模式（无 `--dump`）行为不变（不 emit dumper，全量 PASS） | 现在可跑 | `run_qemu_test.py tests/vectors/isa/reg-arith.yaml` exit 0 |
| 7 | `make build-qemu` 不受影响 | 现在可跑 | |
| 8 | 完成区含真实运行输出；未自行 commit | 现在可跑 | |

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
