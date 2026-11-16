# m14-qemu-003: 异步源轴 mask 查询改按「当前运行模式 monitor」（`ISS-455`）

**模块**：qemu
**项目里程碑**：M14
**依赖**：`m14-linux-009`（K2 收口门控，在跑）**之后**；`m14-linux-008`（已验证，内核侧两行旋钮）
**可并行分片**：否（qemu 组件单写者）
**预估**：1.5–2 h
**档位**：中改（单点语义 + 门控断言；复核 ≥2 路注入）
**状态**：待开始

## 背景（用户 2026-11-16 裁定「ISS-455：查 mode monitor」）

`spec/DADAO-12 §5.2（三）步骤 3` 明确：异步中断来源过滤查「**当前运行模式 monitor** 的 `cfx_<monitor>_<mode>_cfx_intr_mask`（cg0–3 rc4）」与 `cfx_<monitor>_global_cfx_intr_mask`（cg8 rc1）。

现状三处口径不一致：

- **spec**：查 **mode monitor** 的行（supv ⇒ `cfx_smon` 的 supv 行 = `cfx_smon cg2 rc4`）；
- **QEMU**：查**当前 cfx**（`inner_cfx_code`）的行 —— `m14-linux-007` 实测：首投后当前 cfx = 15（`escape` 不恢复 `inner_cfx_code`），只开 `cfx_smon` 一行时**仅 1 个 tick**；
- **`contract-see §6.4`**：同 QEMU 读法（且写了「当前 cfx = `cfx_smon`」的实例句，首投后不成立 —— `ISS-454`）。

用户裁定：**按 spec 字面，查 mode monitor** ⇒ QEMU 与契约都要改；内核侧（`m14-linux-008` 的"两行都写"）随之收敛为只写 `cfx_smon cg2 rc4`（另立 `m14-linux-010`）。

## 目标

1. **QEMU**：异步源轴过滤由「当前 cfx 的行」改为「**当前运行模式 monitor** 的 `<mode>_cfx_intr_mask`」（supv ⇒ `cfx_smon` 的 `cg2 rc4`）；全局轴 `cfx_<monitor>_global_cfx_intr_mask`（cg8 rc1）保持不变；
2. **门控断言**：`k2_time_probe`/`k2_irq_probe` 增（或改）一条 —— **首投后只开 `cfx_smon cg2 rc4` 一行**仍能持续 tick（改前必红、改后必绿，即"先红后绿"）；
3. 其它 target 行为**不变**（只改 dadao 侧逻辑）。

## 验收（真实 rc + 输出）

1. **先红后绿**：改前跑新断言 ⇒ **FAIL**（贴真实输出：只开一行时 tick 数停在 1）；改后 **PASS**；
2. `make build-qemu` + **`make install-host`** rc=0，贴 `qemu-system-dadao` 新 md5（**源树干净时**取，`ISS-451`）；
3. `check-linux-k0` 119/119、`check-linux-k1` 108/108、`k2_trap_probe` 85/85、`k2_time_probe` 151/151、`k2_irq_probe` 95/95 全绿；`check-qemu-forms` rc=0；
4. **≥2 路注入**（`cp`+md5 还原 + 重建）：① 把查询改回"当前 cfx 的行" ⇒ 新断言红；② 把位索引从"目标 cfxha"改成"cause 位索引" ⇒ tick 消失/断言红；
5. 补丁纪律：`apply_series --component qemu`、`check-source-state`、`check-patch-tree`（qemu 0 problem）、`make_patch qemu` 幂等；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只改 `components/qemu/**` + `tools/linux/**`（探针断言）+ 本任务书；不改 `spec/`、`.tao/contracts/`（契约修订归 `m14-linux-010`）；
- 不提交 git；注入还原 `cp`+md5；构建与跑批不同时；`JOBS=32`。

## 审阅记录

（待填）
