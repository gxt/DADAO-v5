# m14-qemu-006: `Kaiwu-Vast` 同步异常路由对齐 spec（删 staged 模型 + 修正编码了偏差的 oracle）

**模块**：qemu
**项目里程碑**：M14
**依赖**：`ISS-460`；`DADAO-12 §5.2`（步骤 1–7，MUST）；`m14-testcases-005`（在跑：其 ⑨a/⑫ 反例因本缺口 FAIL）**必须晚于本任务重跑**
**可并行分片**：否（qemu 组件单写者；且要盘点 `tests/arch` 的 oracle）
**预估**：4–6 h（含 28 个 oracle 逐个判定）
**档位**：大改（组件语义修正 + oracle 修正；复核 ≥4 路注入 + 独立重跑全部 arch/K 门控）
**状态**：待开始

## 背景（用户 2026-11-16 裁定「同意」：改实现，不把偏差写进规范）

`DADAO-12 §5.2` 的步骤 1–7 是规范正文：**执行期同步异常**（非仅页表类）→ 确定 cause 与目标（当前运行模式 monitor）→ **保存现场**（`excp_prev_run_mode` / `excp_cause_ip` / `excp_cause_id` / `excp_cause_info`）→ 切换 → **跳转至目标 cfx 的 `<mode>_excp_vector`**。`§7.1` 的退出码只规定"如何把结果编码给宿主"，**不授权绕过异常投递**。

现状（`target/dadao/`）：

- `cpu.c`：`dadao_profile_vast.sync_exc_monitor_entry = false`（注释自称 staged direct-fault mapping）；Tiny 为 `true`；
- `helper.c`：该标志为 false 时，非 PTW、非 `CFXPERM` 的同步异常走 `dadao_excp_to_exit_code()` + `qemu_system_shutdown_request_with_code(..., GUEST_PANIC, code)` ⇒ **guest 收不到异常、无帧、仿真结束**；
- 后果（可观察语义差异，不是实现自由度）：同一段 guest 代码 Tiny/Vast 行为不同；K3 的内核 fault handler 在 Vast 上拿不到帧；`m14-testcases-005` 的 ⑨a（`ptw_enable=0`）与 ⑫（保留 cfx）反例只能看到 `0xF1`。

## 目标

1. **两 profile 统一进 monitor**：`dadao_profile_vast.sync_exc_monitor_entry = true`；**删除 `helper.c` 的 staged 分支**（`dadao_excp_to_exit_code` + shutdown 那条路），统一走 `dadao_sync_enter()`；
   - `CFXPERM` 的 `cfx_perm_info`（`cause_info`）必须**保留传递**（统一后不得丢失）；
   - 保持"已在关停流程中就不再进 monitor/覆盖退出码"的既有短路。
2. **盘点并修正 oracle**：`git grep '0xF1|0xE1|0xD1|monitor 段'` 现行命中 **28 个文件**（`tests/arch` 与 `tools/testcases/arch` 为主）。逐个判定：
   - **Tiny 相关**（hmon 已进 monitor）⇒ **不动**，写清理由；
   - **Vast 相关且编码了 staged 行为** ⇒ 改为**按 spec 的帧级期望**：`cause_id`（含 `cause_info` 语义）、`excp_cause_ip`、`excp_prev_run_mode`，以及"handler 收到帧后如何 `escape`（0/+4）"；
   - 每个改动必须写「**原期望 → 新期望 + 依据（`DADAO-12 §5.2` 步骤 N）**」；
   - **不得**因为"实现改了"而放宽断言；改的是**错误期望**。
3. **回归**：K0/K1/K2 与 arch 门控必须回绿（Vast 是 K1/K2 的平台）。

## 验收（真实 rc + 输出）

1. **代码证据**：`cpu.c` 两 profile 均 `sync_exc_monitor_entry = true`；`helper.c` 里 `dadao_excp_to_exit_code` + `qemu_system_shutdown_request_with_code` 的那条 staged 路径**已删**（贴 diff/grep）；
2. **先红后绿**：改前用一条 Vast 探针证明"无帧、直接 `0xF1` 退出"（贴真实输出）；改后**同一条**看到 monitor 帧（`cause_id`/`cause_ip`/`cause_info`/`prev_mode` 四项逐个打印并核对）；
3. **28 文件判定表**：逐文件给「Tiny/Vast / 改或不改 / 理由 / 原期望→新期望」；
4. **门控全绿**：`check-linux-k0` 119/119、`check-linux-k1` 108/108、`check-linux-k2` 104/104、`k2_trap_probe` 85/85、`k2_time_probe` 151/151、`k2_irq_probe` 97/97、`check-arch`、`check-arch-smoke`、`check-inst-asm` **904/904**、`check-qemu-forms`；
5. **≥4 路注入**（`cp`+md5 还原 + 重建）：① 把 Vast 的 flag 改回 `false` ⇒ 改过的 oracle/探针红；② 丢掉 `CFXPERM` 的 `cfx_perm_info` 传递 ⇒ 该条红；③ 把 `excp_prev_run_mode` 写入改成常量 ⇒ 红；④ 某个改过的 oracle 新期望写错一位 ⇒ 红；
6. 补丁纪律：`apply_series --component qemu`、`make_patch qemu` 幂等、`check-source-state`、`check-patch-tree`（qemu 0 problem）、`check-component-changelog`；
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **语义以 spec 为准**：只把实现改到 spec，不改 spec/契约（若发现 spec 真有空白，停下报告，不自行扩写）；
- `cause_id` 子原因编码（`ADR-0056`）不在本任务范围（归 `m14-qemu-005`，本任务只需让**帧可达**）；
- 只动 `components/qemu/**`、`tools/testcases/arch/**`、`tests/arch/**`（oracle 与探针期望）+ 本任务书；不动 `spec/`、`contracts/`、`components/linux`；
- 不提交 git；注入还原 `cp`+md5；构建与跑批不同时；`JOBS=32`；脚本按 `git rev-parse --show-toplevel` 推根（`ISS-456`）。

## 审阅记录

（待填）
