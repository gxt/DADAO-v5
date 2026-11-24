# m16-testcases-019: PTW S/U 覆盖 + `arch-ptw-013` 提升为 signature

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-chipyard-018`、`m16-chipyard-020`（U/S 路由）已合入；`m16-chipyard-027`（cfx5/PTW 模式面）按需
**可并行分片**：否（共享 `tests/arch/ptw/`）
**预估**：3–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

- `ISS-528`：`tests/arch` 的 cfx4 PTW/TLB 用例只跑 `[hmon]`，S/U 运行模式与 PTE 的 S/U 轴未覆盖（QEMU/gem5 载体固定 `cfx_hmon`/hypv、RTL step5 只交付 hmon）；对应用户 2026-11-22"每个 cfx 三模式各跑一次"。
- `ISS-532`：`arch-ptw-013` 的 RTL GAP 理由（pmem SRAM 不可达）已被 `m16-chipyard-022` 消除，可提升为 signature 用例。

## 要做

1. **S/U 运行模式**：把 cfx4 的 15 条用例迁到 `common/env-{smon,umon}` 可跑（按需最小改动，不改 PTW 实现）；H/S/U 各跑一次，不允许的模式显式 `modes` 排除并给原因（排除理由必须实测，不得沿用旧措辞）。
2. **PTE 的 S/U 轴**：补 `H`/`S`/`U` 与 `R/W/X` 组合的 S/U 向量（H 轴已由 case 011 覆盖；J 不测）。
3. **`arch-ptw-013` 提升**：`tests/arch/ptw/ptw_sig.S` 的 `PTW_CASE=13` 改为 signature 用例（用 `cfx_pmem` SRAM 窗口），更新 `rtl-coverage.yaml` 与 `tests/arch.yaml` 状态，删对应 GAP 条目（`expected-divergences.yaml`/`rtl-coverage.yaml`）。
4. **不回归**：`arch-ptw-012` 等既有 12 signature + 2 GAP 不回归；`DIV-14` 保持；QEMU/gem5/RTL 三方逐槽。

## 不做

- 不改 PTW/TLB 实现语义；
- 不改 `m16-chipyard-027` 的 RTL 面（若需要，先等它合入）。

## 约束

- 独立 `git worktree`；**不提交 git**；用例/期望集中 `tests/arch/ptw/`；不写运行期路径；术语"寄存器组"；
- 失败路径短 timeout、禁长时间 `-d cpu` dump（ISS-522）。

## 验证

运行期证据目录内的 `run.sh`：

1. cfx4 15 条在 H/S/U 的模式覆盖（或显式排除原因）与三方逐槽；
2. `PTW_CASE=13` 变为 signature 且三方一致，GAP 条目删除；
3. **可达 FAIL ≥2**：注入"把 013 退回 GAP"、"S/U 掩码错行" ⇒ 红；`cp`+md5 还原回绿；
4. `check-tests-index`、`check-tasks`、`check-knowledge-refs`、`run_arch --self-test` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
