# m16-testcases-003: `lr`/`sc` 保留语义三平台对齐

**模块**：testcases
**项目里程碑**：M16
**依赖**：无（`m15-qemu-002`/`m15-gem5-002` 已合入）
**可并行分片**：否
**预估**：3–4 天
**档位**：中改
**状态**：待开始

## 背景（issues 三条同源）

- `ISS-443`【P1】`sc` 的「**异常/中断进入 ⇒ 清保留**」三平台均不实现（`spec/SimRISC-12 §1` 明列为清除事件）：四条路径实测 `MALIGN`/`CFXMEM`/`ILLI` 后 `sc` = chipyard `1` / qemu `1` / **gem5 `0`**；`CFXTRAP` = `1` / **`0`** / **`0`**（spec 全为 1 = 清除）。后果：该清除事件写不成正式向量（写 1 挡 L2、写 0 = 以实现反推，任务书明禁）。
- `ISS-435`【P2】`sc` 保留**粒度**：`spec/SimRISC-12 §1` / `ADR-0034 D6` = **精确地址 + 宽度**；实测 QEMU 按 8 B 整字判成功、chipyard 按整字值比较，均与 spec 相反/不符；gem5 与 spec 一致。
- `ISS-440`【P2】「另一 hart 对同址同宽 store ⇒ 清保留」三平台无实现路径；单 hart 无观测载体。

## 目标

1. **实现对齐 spec**（不是改 spec）：三平台补「异常/中断进入 ⇒ 清保留」；QEMU 与 chipyard 改「精确地址 + 宽度」匹配；
2. `ISS-440` 记 **GAP**（多 hart 前必须补），不硬造单 hart 载体；
3. 向量：`tests/inst/12-misc/sc.*` 补两类点——「异常进入后 `sc` 失败」与「同字异址写不清保留」。

## 验收（逐条贴真实 rc）

1. 三平台同一 ELF 的 `sc` 结果**逐字节相等**（含 4 条异常路径）；
2. **可达 FAIL ≥3 路**：三平台各注入一次（去掉清除动作 / 改回整字粒度 / 异常路径漏清），各自回红，`cp`+md5 还原后回绿；
3. `check-inst-asm` 272/272；`check-patch-tree` qemu/gem5/chipyard 三段各自 0 问题；
4. 完成后在 `issues.yaml` 给 `ISS-443`/`ISS-435` 填 `resolved_by`（`ISS-440` 保持 open 并记 GAP 理由）。

## 约束

独立 `git worktree`；**不提交 git**；**不改 spec**（要改须用户授权）；改三平台源码时按组件补丁树（`docs/Process-01`）导出；术语「寄存器组」；完成区不写具体 `.work/**` 路径。
