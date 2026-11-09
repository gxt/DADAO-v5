# m12-chipyard-010: 位操作 + 原子 + 杂项（含 fence）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-009`
**可并行分片**：否（单核实现，单写者）
**状态**：待开始

## 背景

用户 2026-11-08 确认：`lr`/`sc`/`swym` 与 `fence` 纳入 M12；M12 指令覆盖 = 全部非 cfx 指令。

## 目标

1. **位操作**：`SimRISC-04/08/09/10` 中的位操作（`ctpop`/`ctlz`/`cttz`/`rol`/`clmul` 等）与整数补齐。
2. **原子**：`lr`/`sc` 的 24 条形式（`<lr|sc>.<b|w|t|o>.<nn|an|ar|nr>`）、`swym`（`SimRISC-12`）；`sc` 的 `rdHB=rd0 ⇒ ILLI`。
3. **`fence`**：`SimRISC-11 §5`——`hb!=0` 或保留 `cfxha` ⇒ ILLI；`pred==succ==0` 合法 no-op；非零掩码在单周期核上天然满足（顺序执行）。
4. **合法性**：全部保留编码 ⇒ ILLI（按 `contracts/legality_rules.yaml`）。

## 验收标准

1. `tests/inst` 的 `atomics/` 与位操作用例在 chipyard 上与 QEMU 逐例一致
2. `fence` 的 ILLI 与 no-op 两条路径各有至少 3 例
3. `sc` 的 `rd0` 合法性规则有专门断言
4. `swym` 合法 no-op、保留编码 ILLI
5. Verilator 构建 rc=0（主控机）；`apply-series`/`check-source-state`/`check-patch-tree`/L1/L2 rc=0
6. 一键证据脚本（含可达 FAIL 注入）
7. 完成区 ≤30 行、无运行期路径

## 非范围

FP（`009`–`013`）、cfx 本身（`trap`/`escape`/`cfx2rd`/`cfx2rc` 不实现）

## 说明

- 参考实现 `.cache/refs/DADAO/SOC-chipyard/` 可作结构参考（**只读溯源，非执行依赖**）。
- 构建/运行在节点（**单任务单机，不迁移**）；仓库修改在主控机。

## 硬约束

1. 临时目录 `/tmp/opencode/m12-chipyard-008/`；禁仓库内临时文件（**此前有任务留过 `scratch/`、`pico-math/`**）。
2. **不提交 git**；不改共享台账；**收尾用显式 `git add <path>`，禁 `git add -A`**。
3. 完成区与真实输出逐条对齐；只动任务书范围。
4. 失败保留现场并继续推进；只在需用户语义裁定时留问。
5. 复杂命令输出留存 运行期日志目录；命令在 worktree 根内、相对路径。
6. **组件单写者**：chipyard 源树独占；发现其它任务在改先停下报告。
7. 长构建先申报耗时，落 PID/日志/`*_EXIT`；构建期间同机不得跑基线。
8. **单任务单机**：整个任务固定在一台节点做完，不跨机迁移。
9. 节点构建/运行后 `DADAO_NODES='gxt@100.79.255.16,gxt@100.81.9.54' make sync-node-repo` 并记录。
10. 不要删除其它任务的临时目录。

