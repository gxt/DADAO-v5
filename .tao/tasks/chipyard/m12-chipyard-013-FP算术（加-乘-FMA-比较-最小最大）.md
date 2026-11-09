# m12-chipyard-013: FP 算术（加/乘/FMA/比较/最小最大）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-012`
**可并行分片**：否（单核实现，单写者）
**状态**：待开始

## 背景

010 已完成 FP 转换。

## 目标

1. **加法/乘法**：`foadd`/`fomul`（`AddRecFN`/`MulRecFN` 等价）。
2. **FMA**：`fofma`（`MulAddRecFN` 等价，单次舍入）。
3. **比较**：`foqcmp`/`foscmp`（`CompareRecFN` 等价，quiet/signaling 语义按 spec）。
4. **最小/最大**：`fomin`/`fomax`（NaN 传播按 spec）。

## 验收标准

1. 对应指令族在 chipyard 上与 QEMU/gem5 逐例一致
2. FMA 的单次舍入有专门向量（与「先乘后加」区分）
3. quiet/signaling NaN 的比较语义各至少 2 例
4. Verilator 构建 rc=0（主控机）；门控同前
5. 一键证据脚本（含可达 FAIL 注入）
6. 完成区 ≤30 行、无运行期路径

## 非范围

除/开方/余（`012`）、取整/缩放（`013`）

## 说明

- 参考实现 `.cache/refs/DADAO/SOC-chipyard/` 可作结构参考（**只读溯源，非执行依赖**）。
- 构建/运行在节点（**单任务单机，不迁移**）；仓库修改在主控机。

## 硬约束

1. 临时目录 `/tmp/opencode/m12-chipyard-011/`；禁仓库内临时文件（**此前有任务留过 `scratch/`、`pico-math/`**）。
2. **不提交 git**；不改共享台账；**收尾用显式 `git add <path>`，禁 `git add -A`**。
3. 完成区与真实输出逐条对齐；只动任务书范围。
4. 失败保留现场并继续推进；只在需用户语义裁定时留问。
5. 复杂命令输出留存 运行期日志目录；命令在 worktree 根内、相对路径。
6. **组件单写者**：chipyard 源树独占；发现其它任务在改先停下报告。
7. 长构建先申报耗时，落 PID/日志/`*_EXIT`；构建期间同机不得跑基线。
8. **单任务单机**：整个任务固定在一台节点做完，不跨机迁移。
9. 节点构建/运行后 `DADAO_NODES='gxt@100.79.255.16,gxt@100.81.9.54' make sync-node-repo` 并记录。
10. 不要删除其它任务的临时目录。

