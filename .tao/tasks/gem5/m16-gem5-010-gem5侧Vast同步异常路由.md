# m16-gem5-010: gem5 侧 `Kaiwu-Vast` 同步异常路由对齐 `DADAO-12 §5.2`

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m14-qemu-006`（**已验证**：QEMU 侧同一改动的实现与 28 个 oracle 复推，可作行为对照）
**可并行分片**：否（改 `components/gem5` 单一组件树）
**预估**：3–5 h
**档位**：中改（删一条路由 + oracle 对齐；复核 ≥2 路注入 + 探针全量）
**状态**：待开始

## 背景

`DADAO-12 §5.2` 要求**执行过程中的同步异常一律先进对应运行模式的 monitor 向量**（MUST）。QEMU 侧的 `Kaiwu-Vast` 曾把 5 类同步异常做成 **staged 机器 fault**（不进向量），已由 `m14-qemu-006` 删除 staged 模型、两 profile 统一进 monitor。

`.tao/knowledge/discussing.md` 记有同一条未闭环（`spec-004` 候选）：「Vast 的同步异常仍是 staged 机器 fault（`DADAO-12 §5.2(一)` 要求进向量），5 个 arch 探针 oracle 依赖旧口径；**统一需同步改 qemu/gem5 + 探针**」—— QEMU 侧已完成，**gem5 侧无任务**。

## 执行前必须先复现（不得凭推断改）

用现成探针在 gem5 上跑 `Kaiwu-Vast`（`-M kaiwu-vast`）的同步异常例，确认当前行为落在哪一类：

- `tests/arch/**` 的 `049t`（`old_ram_unmapped` / `oob_fetch_cfxmem`）、`integ042t`、`integ048t`（`power_bootrom_store` / `closed_power_bootrom`）；
- 期望（改后）：两 profile 的 `sync_exc_monitor_entry = true`，异常进 monitor 向量、由向量决定去向；不存在第二条"机器 fault 直接退出"的路由（`Kaiwu §7.1` 的 `fault` 兜底**仅**用于「向量不可达」）。

现场结论写进完成区（**未复现成功不得开改**）。

## 目标

1. **单路由**：`Kaiwu-Vast` 的同步异常只走 monitor 向量；删除/禁用 staged 机器 fault 路径（与 `m14-qemu-006` 的裁决一致：**真删，不是 `if (0)`**）；
2. **保留唯一兜底**：仅当「向量不可达」时按 `Kaiwu §7.1` 走机器 fault（该路径有用例覆盖，不得一并删）；
3. **帧四项**对齐：`prev_run_mode`、`cause_id`（含子原因，若 `m16-gem5-009` 已落地）、`cause_ip`（触发指令地址；取指异常时 = 非法 IP）、`cause_info`（数据 `CFXMEM` = 访存地址；`ILLI` = 指令编码）；
4. **oracle 按 spec 复推**：受影响探针的期望值由 `DADAO-12 §5.2` 步骤逐字段推出，**不得**照实现输出改期望。

## 验收（真实 rc + 输出）

1. **与 QEMU 一致**：`m14-qemu-006` 覆盖的同一批探针在 gem5 上全部 PASS，且帧四项与 QEMU **逐字段相同**；
2. **反例可达**：注入「让某同步异常走 staged 路径」⇒ 该探针红（证明 staged 确实被移除而不是被绕过）；
3. **兜底仍在**：`integ040t/ptwerr_monitor_cfxmem_exit`（向量不可达 ⇒ `§7.1` 机器 fault）仍绿；
4. **≥2 路注入**（`cp`+md5 还原）：① 上面那路 staged；② `prev_run_mode` 改成读切换后的值 ⇒ `prevm` 断言红；
5. 门控：`check-gem5-decode`、`check-arch`（14 探针）、`check-patch-tree`（gem5 段 0 problem）、`make_patch` 幂等；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只动 `components/gem5/**` + 必要的 `tools/gem5/**` + 本任务书；**不动** `spec/`、`contracts/`、`tests/**`、`components/{qemu,linux,chipyard}`；
- 不得为"让探针变绿"改期望值；**spec 是唯一真源**；
- 不提交 git；注入还原 `cp`+md5（禁 `git checkout/restore`）；基线钉死 commit（`ISS-458`）。

## 审阅记录

（待填）
