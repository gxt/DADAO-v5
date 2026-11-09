# m12-chipyard-014: T0 冒烟（inst 全量非 cfx + tset 子集，三平台比对）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-013`
**可并行分片**：否（单核实现，单写者）
**状态**：待开始

## 背景

001–013 已完成全部整数与 FP 指令（全部非 cfx）。

## 目标

1. **T0 冒烟**：`tests/inst` 中**全部非 cfx 指令**用例，在 chipyard 上与 QEMU `dadao-tiny`、gem5 FS Tiny 三平台比对（状态/退出码；不比时序）。
2. **tset 已验证子集**：`libc-test`/`llvm-ts`/`embench` 中已被 qemu/gem5 验证的子集，在 chipyard 上跑通（Tiny 阶段不涉及 syscall，用 semihosting）。
3. **差异归因**：任何不一致逐条列名并归因（spec/实现/测试资产）。

## 验收标准

1. inst 全量非 cfx 用例三平台一致；计数按 `--list` 现场统计
2. tset 子集在 chipyard 上跑通并给出 pass/fail 计数
3. 差异逐条归因，无未归因项
4. 报告落 `.tao/knowledge/refs/m12-014-t0-smoke.{json,md}`
5. Verilator 构建 rc=0；门控同前
6. 一键证据脚本（含可达 FAIL 注入）
7. 完成区 ≤30 行、无运行期路径

## 非范围

T1 适配集与 M12 验收（`015`）

## 说明

- 参考实现 `.cache/refs/DADAO/SOC-chipyard/` 可作结构参考（**只读溯源，非执行依赖**）。
- 构建/运行在节点（**单任务单机，不迁移**）；仓库修改在主控机。

## 硬约束

1. 临时目录 `/tmp/opencode/m12-chipyard-014/`；禁仓库内临时文件（**此前有任务留过 `scratch/`、`pico-math/`**）。
2. **不提交 git**；不改共享台账；**收尾用显式 `git add <path>`，禁 `git add -A`**。
3. 完成区与真实输出逐条对齐；只动任务书范围。
4. 失败保留现场并继续推进；只在需用户语义裁定时留问。
5. 复杂命令输出留存 `.work/log/chipyard/`；命令在 worktree 根内、相对路径。
6. **组件单写者**：chipyard 源树独占；发现其它任务在改先停下报告。
7. 长构建先申报耗时，落 PID/日志/`*_EXIT`；构建期间同机不得跑基线。
8. **单任务单机**：整个任务固定在一台节点做完，不跨机迁移。
9. 节点构建/运行后 `DADAO_NODES='gxt@100.79.255.16,gxt@100.81.9.54' make sync-node-repo` 并记录。
10. 不要删除其它任务的临时目录。

