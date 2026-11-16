# m14-linux-010: IE 旋钮收敛为「当前运行模式 monitor」单行 + 契约 §6.4 口径修订（`ISS-455`/`ISS-454`）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-qemu-003`（QEMU 源轴改按 mode monitor）**必须先合入**；`m14-linux-008`（已验证：两行旋钮）
**可并行分片**：否（linux 组件单写者）
**预估**：2–3 h
**档位**：中改（实现收敛 + 契约文字 + 探针断言；复核 ≥2 路注入）
**状态**：待开始

## 背景

用户 2026-11-16 裁定：

- **`ISS-455`**：「查 mode monitor」—— 异步源轴 mask 按 `spec/DADAO-12 §5.2（三）步骤 3`，查**当前运行模式 monitor** 的 `<mode>_cfx_intr_mask`（supv ⇒ `cfx_smon` 的 `cg2 rc4`），**与 `inner_cfx_code` 无关**；
- **`ISS-454`**（解释）：`escape` 不恢复 `inner_cfx_code`，所以"当前 cfx = `cfx_smon`"这个**理由**在首投后不成立；但**寄存器选择本来就该由"运行模式 → monitor"决定**，所以按 455 的口径，`cfx_smon cg2 rc4` 依然正确，只是**理由**要改。两条一次改完。

现状：`m14-linux-008` 为兼容两种读法，**每次写两行**（`cfx_smon` + `cfx_hart`）。按 455 裁定，`cfx_hart` 那一行**不再需要**（多余的写会让"源轴按 monitor"读法更难看清），应收敛为单行。

## 目标

1. **实现收敛**：`arch/dadao/include/asm/irqflags.h` 的 `save/restore/disable/enable` 由"两行"改为**只写 `cfx_smon` 的 supv 行（`cg2 rc4`）**；注释写明依据 = 运行模式 → monitor（`cfx_smon`），并引用 `ISS-454` 说明"当前 cfx"不是选择依据；
2. **契约修订**：`.tao/contracts/contract-see.md §6.4` 改为「IE 旋钮 = **当前运行模式 monitor** 的 `<mode>_cfx_intr_mask`（supv ⇒ `cfx_smon cg2 rc4`）；`global_cfx_intr_mask` 只作模式级放行（被异步帧借用）」——**删掉**「当前 cfx = `cfx_smon`」的实例表述（`ISS-454`）；接口版本按 `docs/Process-02` 处理（`contract-see` 为 ADR-sourced，版本头保持 `0.7.3-rc`）；
3. **探针**：`k2_irq_probe` 的"两行"断言改为**单行**断言（`save` 后只 `cfx_smon cg2 rc4` 的源位置位、`restore` 后逐位复原），并保留**首投后仍能 tick**这类跨阶段证据（若 QEMU 侧已由 `m14-qemu-003` 覆盖，则此处只核内核侧读写）。

## 增补要求（`m14-qemu-003` 复核 finding 1，2026-11-16）

**本任务删掉 `cfx_hart` 行写入后，`tools/linux/k2_time_probe.py` 的 `SINGLE_ROW_PATCHES` 注入点会消失**（三处 old 串 count=0 ⇒ 现有代码 `SystemExit("注入点不唯一 (0 处)")` 会把整个探针跑红）。

必须在**本任务内**同步改，判据不得因此变弱：

- `SINGLE_ROW_PATCHES` 退化为**空表**，`single_row_run()` 直接用**未注入的内核**跑 C10（此时内核天然只写 `cfx_smon` 行，C10 由"注入式先红后绿"转为**常驻断言**）；
- **保留可失败性**：另加一路反向注入——临时**加回** `cfx_hart` 行写入 ⇒ C10 **必红**（证明判据仍能抓"写了两行"）；
- 验收里写明这两条（常驻断言 + 反向注入）的实测输出。

## 验收（真实 rc + 输出）

1. `k2_irq_probe` 全绿（条数现场统计，不低于改前 95）、`--selfcheck`/`--inject` 可跑；`k2_trap_probe` 85/85、`k2_time_probe` 151/151、`check-linux-k0` 119/119、`check-linux-k1` 108/108；
2. **≥2 路注入**（`cp`+md5+重建）：① `restore` 只写低 32 位 ⇒ 逐位复原断言红；② `enable` 全清 0 ⇒ 粒度断言红（若原判据抓不到，先补断言再注入，见 `ISS-457`）；
3. 契约门控：`check-contracts-dir`、`check-contracts-pending`、`check-contract-relocs`、`check-rule-refs`、`check-spec-refs`、`check-interface` 全 rc=0；
4. 补丁纪律：`apply_series --component linux`、`check-source-state`、`check-patch-tree`（linux 0 problem）、`make_patch linux` 幂等；
5. L1 `make check` rc=0；完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只改 `components/linux/**`、`tools/linux/**`、`.tao/contracts/contract-see.md`、本任务书；不改 `spec/`（spec 已是 mode-monitor 口径，无需改）、不改 QEMU；
- 语义不变：`flags` 仍整条 64 位、`enable` 仍只清内核关心源位；
- 不提交 git；注入还原 `cp`+md5。

## 审阅记录

（待填）
