# m16-chipyard-004: `stm` 的 store 偏置 N 扫描实测

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-001`（已有 C/D 类实测方法与 sim 基线）
**可并行分片**：否（单 sim 单写者）
**预估**：1.5–2 h
**档位**：小改（只测量与报告，不改交付代码/表）
**状态**：待开始

## 背景（用户 2026-11-18）

`m16-chipyard-001` 遗留 3：`st`/`stm` 的 +1 拍未进 gem5 模型。现有两个数据点（`st.o` N=1 = 10 vs `ld.o` 9；`stm.o` N=8 = 73 vs 模型 72；`stm.b` N=8 = 17 vs 16）都表现为「+1」，但**只覆盖 N=1 与 N=8**，不足以排除「每元素 +1/8」这类巧合。

用户裁定方向（2026-11-18）：表格按 ld/st/ldm/stm **分行给值、不加列**；`stm` 的常数项要先**实测确认**再定。

## 目标

实测 chipyard `WumingTinyConfig` 上 `stm`（并以 `ldm` 作对照）在 **N = 1 / 2 / 3 / 4 / 8 / 16** 的拍数，判定 store 偏置是「每指令固定 +1」还是与 N 相关。

## 方法（沿用 `m16-chipyard-001` 口径）

1. sim 二进制：`.work/source/chipyard/sims/verilator/simulator-chipyard.harness-WumingTinyConfig`（已有，先记 md5）。
2. 探针来源：优先复用 `tests/inst/01-load-store/stm.o_rrri_rd.S`（同一镜像内含 N=2/3/8/16 多条 `stm.o`）；N=1/4 若缺，另建**最小探针**（`stm` + `ldm` 各 N 一条，跑完 `SYS_EXIT`），放 `/tmp/opencode/m16-chipyard-004/`，**不入仓**。
3. 拍数口径：trace 中相邻指令**进入 EXEC** 的 `cycle=` 差值（与 `m16-chipyard-001` 同一算法）；同一 N 至少 **2 个样本**（不同基址/对齐/宽度）。
4. 独立性：真值只取 chipyard trace；**不得**用 gem5/QEMU 反推，也不得用周期模型的输出作期望。

## 验收（逐条贴真实 rc / 原始输出）

1. 表格：`N / 指令 / 宽度 / 实测拍 / 模型拍（per_element×N + per_beat×beats）/ 差值`，每个 N 至少 2 样本。
2. 给出**判定**：差值序列是否恒为 1；若是，结论为「固定偏置」；若不是，给出实测规律（如 `1 + ceil(N/k)`）并说明与哪些 N 相关。
3. `ldm` 同表对照（用于确认 load 侧无偏置）。
4. sim md5、探针源码、解析脚本路径全部记录（运行期证据目录）。
5. 结论一句话可直接写进 `docs/core-wuming-cycle-model.md` §5 的表行形式。
6. **不改** `tools/gem5/wuming_cycles.yaml`、不改 gem5 补丁、不改周期模型文档（回填由后续任务做）。
7. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**。
2. 只动本任务书；探针/脚本/日志放 `/tmp/opencode/m16-chipyard-004/` 与运行期证据目录。
3. 不改版本号；不动 `components/`（只运行已有 sim）。
4. 主控机可能有其它长任务在跑（`m14-linux-017`）⇒ 单例串行跑，不要并行占满核。

## 待裁定

（无）

## 审阅记录

（待填）
