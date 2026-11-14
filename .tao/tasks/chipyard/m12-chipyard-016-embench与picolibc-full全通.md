# m12-chipyard-016: embench / picolibc-full 在 chipyard Tiny 上全通

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-015`（已完成）
**可并行分片**：否（chipyard 组件单写者；跑批可分节点）
**预估**：6–8 h（runner 改动 2–4 h + 跑批 15–30 min + 报告/注入 1–2 h + 余量）
**状态**：待开始

## 背景与口径（用户 2026-11-14 裁定）

- **M12 不依赖 M13**；**三平台差分是 M13 的事**，本任务**不做**三平台比对。
- **跑在 chipyard Tiny（`WumingTinyConfig` Verilator）上**，不是 qemu-user、不是 qemu-system、也不是 gem5。
- **不收 `tests/inst`**（其迁移归 M13）、**不收 llvm-ts**。
- chipyard Tiny 的 semihosting 由 hmon 的 cfx0 服务提供（`immu18[17:8]==0x3FF`）：`SYS_EXIT` 给出退出码、`SYS_WRITE` 给出输出/markers；`tests/inst` 的 `.S` 套件已长期用它。

## 现状（实测，勿重新推导）

- `tools/testcases/tset/embench/run_embench_e2e.py`：**已能**把 19 个 benchmark（× `-O0/-O2` = 38 例）以 freestanding 方式编到 `dadao-tiny-app.lds`、链接 crt0 + 板级 shim，判据 = **guest 退出码 0**（`main` 返回 `!correct`）；但它**只驱动 `qemu-system-dadao -M dadao-tiny`**（`grep -c chipyard` = 0）。
- `tools/testcases/picolibc_tests.py`：同样**只驱动 qemu-system `dadao-tiny`**（`grep -c chipyard` = 0）。
- `tools/testcases/inst/run_asm_suite.py` 已有 chipyard 调用范式可直接复用：
  `simulator-chipyard.harness-WumingTinyConfig +permissive +loadmem=<elf> +semiout=<out> +max-cycles=<N> +permissive-off none`。

## 目标

1. 给两个 runner 加 **chipyard 引擎**（`--engine chipyard` 或等价开关，复用上述范式；markers/退出码从 `+semiout` 与 semihosting 读）。
2. **embench 全量全通**：19 benchmark × `-O0/-O2` = **38/38**，判据 = guest 退出码 0（+ markers）。
3. **picolibc full 全通**：`picolibc_tests.py --stage full` 在 chipyard 上全绿（现场统计例数，不写死）；对**确实依赖 qemu 专有行为**的用例，逐条记 BLOCKED 并说明，不得静默跳过。
4. 不改 benchmark/测试语义，只加引擎与判据；qemu 通路保持可用（回归）。

## 验收

1. embench **38/38**、picolibc full 全绿（计数现场统计），两者均给出**运行时实际执行的指令/周期量级**（`+max-cycles` 触顶即 FAIL，防"跑不完也绿"）。
2. qemu 通路回归：`check-tset-embench-smoke` 与 `check-picolibc-tests` 仍 rc=0（证明加引擎未破坏旧路径）。
3. 报告落 `.tao/knowledge/refs/m12-016-embench-picolibc.{json,md}`（含每例退出码、markers、墙钟、所用 sim md5）。
4. **≥2 路可达 FAIL 注入**（例：把某 benchmark 的 `verify_benchmark` 改坏 ⇒ 退出码非 0 ⇒ 判红；把 `+max-cycles` 调到极小 ⇒ 触顶红）+ `cp`+md5 还原。
5. Verilator 构建 rc=0；`check-patch-tree` chipyard 段 0 问题。
6. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；chipyard 组件补丁按 `docs/Process-01` 导出。
3. 跑批在**节点**（`--jobs` 用默认 = 核数/2）；跑批前用 `tools/infra/sync_node_artifacts.sh <host>` 核对 sim 与主控机 md5 一致（`ISS-429`）。
4. 构建后必须删 `.classpath_cache/chipyard.jar` 与 `generated-src/<cfg>` 再 `make verilog`（否则静默沿用旧 RTL）。
5. 禁 `git checkout/restore/stash`/`git show <commit>:<path>` 还原；注入还原用 `cp`+md5。
6. 大文件落 `/tmp/opencode/m12-chipyard-016/` 并测完即删；日志 `.work/log/chipyard/<任务ID>-<用途>.log`。

## 待裁定

（实现中写）

## 审阅记录

（待填）
