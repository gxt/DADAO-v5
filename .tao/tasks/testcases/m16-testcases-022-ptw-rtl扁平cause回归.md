# m16-testcases-022: PTW 测试的 RTL 面在扁平 cause 对齐后修复/回归

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m17-chipyard-001`（RTL `excp_cause_id` 扁平位图对齐，ADR-0062）合入
**可并行分片**：否（共享 `tests/arch/ptw/`）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（用户 2026-11-25 裁定 B）

`m17-spec-002`（ADR-0062）把 `excp_cause_id` 改为**扁平位图**（PTW 故障只置高位、低位 cause 全 0），RTL 仍按 ADR-0056 两级 wyde ⇒ RTL 上凡拿 `CAUSE_*` 做 guest 断言的用例必红（`arch-ptw-009` rc=47、`arch-ptw-011` rc=54、`arch-ptw-013` rc=3）。用户裁定：**保留这些 signature，接受 RTL known-red**，并单独立本任务在 `m17-chipyard-001` 之后修复/回归。

`m16-testcases-019` 已把 `arch-ptw-013` 升为 signature 并保留静态接线；本任务只做 RTL 面收尾，不改 QEMU/gem5 面。

## 要做

1. **前置确认**：`m17-chipyard-001` 已合入且 RTL 的 `excp_cause_id` 为扁平位图（跑一条最小 `CAUSE_*` 探针确认）。
2. **RTL 回归**：`arch-ptw-009/011/013` 在 `run_arch --platforms chipyard`（H/S/U 或声明的模式）下转绿；`arch-ptw-002/007`（DIV-14）不回归；`check_ptw_rtl --selfcheck` 的 signature/guest/gap 集合与本任务后的登记一致。
3. **登记收尾**：删除/收窄 `ISS-m16-006` 的 RTL known-red 说明；若 `m16-testcases-019` 的 BLOCKED/EXPECTED-RED 文案需要更新，一并改为"已闭合"。
4. **不回归**：`tests/arch/ptw/` 的 QEMU/gem5 面不变；`DIV-14` 保持；`check-tests-index`/`check-tasks`/`check-knowledge-refs`（基线悬空见当时状态）。

## 不做

- 不改 RTL/spec（属 `m17-chipyard-001`）；
- 不改 PTW 的 QEMU/gem5 期望；
- 不新增 cfx4 的 S/U RTL 面（仍按 `DIV-09`）。

## 约束

- 独立 `git worktree`；**不提交 git**；只动 `tests/arch/ptw/**`、`tests/arch.yaml`、`tests/arch/modes.yaml`、`expected-divergences.yaml`、本任务书；
- 不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. `arch-ptw-009/011/013` 的 RTL 面转绿（或按声明模式）；`002/007` 不回归；
2. `run_arch --platforms chipyard` 对 cfx4 的 `signature` 集合无 FAIL（gap 只剩 014/015）；
3. **可达 FAIL ≥2**：注入"把 cause 期望改回旧两级编码"、"把 013 退回 gap" ⇒ 红；`cp`+md5 还原回绿；
4. `check-tests-index`、`check-tasks`、`check-knowledge-refs`、`run_arch --self-test` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
