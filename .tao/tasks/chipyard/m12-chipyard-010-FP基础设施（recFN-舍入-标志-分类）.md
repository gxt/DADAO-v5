# m12-chipyard-010: FP 基础设施（recFN/舍入/标志/分类）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-009`
**可并行分片**：否（单核实现，单写者）
**状态**：待开始

## 背景

用户 2026-11-08 确认 FP 全做 5 组，参考 berkeley-hardfloat 的原语边界。

## 目标

1. **recFN 编解码**：`recFNFromFN` / `fNFromRecFN` / `rawFloatFromFN` 等价实现（硬float 语义）。
2. **六档舍入**：`RoundAnyRawFNToRecFN` 等价；舍入方向读 `rf0[33:32]`（dynamic）或立即数（按 `ADR-0050`）。
3. **异常标志**：NV/DZ/OF/UF/NX 的设置与 `rf0[4:0]` 读回。
4. **分类与符号**：`classifyRecFN`、符号位操作（`fosgnj` 等）。

## 验收标准

1. 与 hardfloat 的 `RoundAnyRawFNToRecFN` 在六档舍入下逐例一致（可用 `tools` 的 FP 测试向量）
2. 异常标志五类各有至少 2 例
3. 分类（NaN/Inf/subnormal/zero）全覆盖
4. Verilator 构建 rc=0；`apply-series`/`check-source-state`/`check-patch-tree`/L1/L2 rc=0
5. 一键证据脚本（含可达 FAIL 注入）
6. 完成区 ≤30 行、无运行期路径

## 非范围

转换/算术/除开方/取整（`010`–`013`）

## 说明

- **FP 实现方式（用户 2026-11-09）**：**参考** berkeley-hardfloat 的 recFN 语义，**自写**组合逻辑；**不引入 `hardfloat` 子模块依赖**。任务书/代码注释须**逐处注明来源**（`berkeley-hardfloat` 的哪个原语、对应的语义点）。
- **wuming 不是「单周期指令」而是「无流水线」**（用户 2026-11-09）：多寄存器/ldm/stm 等指令本就多周期；FP 除法/开方等长延迟操作允许走**多周期状态机**。
- 参考实现 `.cache/refs/DADAO/SOC-chipyard/` 可作结构参考（**只读溯源，非执行依赖**）。
- 构建/运行在节点（**单任务单机，不迁移**）；仓库修改在主控机。

## 硬约束

1. 临时目录 `/tmp/opencode/m12-chipyard-009/`；禁仓库内临时文件（**此前有任务留过 `scratch/`、`pico-math/`**）。
2. **不提交 git**；不改共享台账；**收尾用显式 `git add <path>`，禁 `git add -A`**。
3. 完成区与真实输出逐条对齐；只动任务书范围。
4. 失败保留现场并继续推进；只在需用户语义裁定时留问。
5. 复杂命令输出留存 运行期日志目录；命令在 worktree 根内、相对路径。
6. **组件单写者**：chipyard 源树独占；发现其它任务在改先停下报告。
7. 长构建先申报耗时，落 PID/日志/`*_EXIT`；构建期间同机不得跑基线。
8. **单任务单机**：整个任务固定在一台节点做完，不跨机迁移。
9. 节点构建/运行后 `DADAO_NODES='gxt@100.79.255.16,gxt@100.81.9.54' make sync-node-repo` 并记录。
10. 不要删除其它任务的临时目录。

