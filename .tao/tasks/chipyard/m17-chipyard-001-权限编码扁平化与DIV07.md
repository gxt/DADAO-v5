# m17-chipyard-001: RTL 权限编码扁平化 + 关闭 `DIV-07`（hypv/Tiny 判权）

**模块**：chipyard
**项目里程碑**：M17
**依赖**：`m17-spec-001`（ADR-0062 定稿）；`DIV-07` 的 `close_when` 需用户确认
**可并行分片**：否
**预估**：1–2 天（依据 `m16-chipyard-020` 实测：RTL + 探针 + 双 profile 重建）
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景

`m17-idl-020` 的 2 个 `CFXPERM` 载体在 chipyard 上不成立，原因是 `WumingTinyConfig` 在 **hypv** 下**不强制** cfx 来源掩码判权——这不是漏做，而是登记在 `tests/arch/expected-divergences.yaml` 的 **`DIV-07`（temporary）**，`close_when` = 「RTL 交付链改为 `cfx_hmon` 源」，**待用户确认**（`m16-chipyard-020` 遗留①）。

另按用户 2026-11-24 裁定改扁平位图：删除 `[39] NCFXPERM`、`[57] NONPTW`；PTW 权限/缺失只置高位位图（Vast）；`CFXPERM`/`CFXMEM` 各只保留单一含义。当前 RTL 按 `ADR-0056`（一 cause 一 wyde），`m16-chipyard-003`/`020` 的实现需返工。

## 要做

1. **关闭 `DIV-07`**（需先获得用户对 `close_when` 的确认）：在 hypv/Tiny 下启用两轴判权（`cfx2rd`/`cfx2rc`/`trap`/`escape` 的来源掩码与 `cg3 rc12` 委托），并解决 `m16-chipyard-020` 指出的「BootROM 以 `cfx_power` 跑、复位掩码只允许 hmon ⇒ 既有探针不可达」——改交付链（按 `DIV-07` 的 `close_when`）或改探针入口，二者择一并在任务书说明；
2. 掩码拒绝：`cause_info` = 触发指令地址；删除 `PERM_NCFXPERM` 的置位；
3. 删除 `MEM_NONPTW` 的置位（`CFXMEM` 不再带子原因）；
4. Vast PTW 故障按 ADR 改高位位图（父 `CFXPERM`/`CFXMEM`=0）；路由/退出码按 ADR「未定」标注；
5. 更新 `tests/arch` 的 `expected-divergences.yaml`（`DIV-07` 关闭或改写）与相关探针期望；
6. 双 profile 重建（Tiny/Vast）并跑既有 arch/11-cfx 回归。

## 不做

- 不改 QEMU/gem5/Linux/spec；不改 `tests/inst` 语义（`m17-idl-020` 负责）；
- 不自行决定 Vast 路由/退出码。

## 约束

- 独立 `git worktree`；组件补丁按 `docs/Process-01`（`make_patch` 幂等）；不提交 git；
- 只动 `components/chipyard/patches/generators/dadao-wuming/**`、`components/chipyard/{README.md,changelog.md}`、`tests/arch/expected-divergences.yaml`、必要探针、本任务书；
- 完成区 ≤30 行、不写运行期路径。

## 跨里程碑依赖与冲突（2026-11-24 核对）

- **同组件串行**：`m16-chipyard-021`/`022`（**待验收**）、`m16-chipyard-023`（**进行中**）同改 `WumingCore`/PTW/异步；本任务必须等它们合入后再 rebase，且 `DIV-07` 关闭会改变它们探针的 hypv 前提。
- **返工已验证任务**：`m16-chipyard-003`（cause-id 子原因）、`m16-chipyard-020`（两轴判权）的部分判据与期望需按扁平模型返工；`tests/arch/expected-divergences.yaml` 的 `DIV-07` 要按用户确认的 `close_when` 关闭/改写。
- **既有探针风险**：Tiny 以 `cfx_power` 跑测试体，复位掩码只允许 hmon；打开 hypv 判权会让现有 `11-cfx`/`01-load-store`/arch 探针失败 ⇒ 必须同任务改交付链或探针入口。

## 验证

运行期证据目录内的 `run.sh`：

1. Tiny：`cfxreg`/`cfxtrap` 掩码拒绝各一次 ⇒ `CFXPERM` + `cause_info=指令地址`；`cause_id` 无 `[39]`；
2. Vast：PTW 权限/缺失故障按高位位图（父 cause=0），与 QEMU/gem5 新口径逐位一致；
3. **可达 FAIL ≥3 路**：去掉 hypv 判权 / `cause_info` 写编码 / 加回子原因；各红后 `cp`+md5 还原并重建回绿；
4. 既有 `11-cfx` 5 例、`01-load-store` 38 例字节流不回归；`DIV-07` 关闭后 arch 回归通过；
5. `check-patch-tree` chipyard 段 0 problem；`check-index-blobs`/`check-tests-index` rc=0。

## 待裁定/阻塞

- `DIV-07` 的 `close_when`（交付链 vs 探针入口）需用户确认；
- Vast 路由/退出码按 ADR 未定处理。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
