# m18-infra-001: musl mallocng 堆一致性崩溃（ISS-497 / ISS-499）

**模块**：infra
**项目里程碑**：M18
**依赖**：`m18-linux-001`/`002`（K6 启动与回归）
**可并行分片**：否
**预估**：4–6 h
**档位**：大改（musl 堆/free 路径或 ash 交互）
**状态**：待开始

## 背景（`m18-linux-004` 定位）

- `ISS-497`：单次启动约 17 条命令后 shell 被杀；内核记 `die-no-vma va=0x0`。定位到 **musl mallocng 内部一致性断言**（`glue.h::assert → a_crash()` 写 NULL，落在 `alloc_slot`/`free`）。
- `ISS-499`：guest `grep` 每次 SIGSEGV，落在同一断言 ⇒ **两个 issue 同一根因**。
- 触发面是**堆布局**：去掉 ash 的 `setvar0("_", lastarg)` 即消失（3/3）；同命令序列经脚本文件/管道喂子 shell 不崩，控制台逐行喂则崩；行缓冲/去回显/非 tty/屏蔽 tick 都不消除。
- 内核侧 `cp` 级探针全绿（fork+exec 12 轮堆校验、64 个 mmap 区间别名+churn、console 逐字节读+堆校验）⇒ 初步判**非内核改写用户内存**。

## 目标

1. **坐实归属**（先做）：最小复现（ash `_` 赋值 + 堆布局）逐层缩小到 musl `mallocng` 的分配/释放路径；给出「内核未改写」的独立证据（或推翻，转回 linux）。
2. **修复**：
   - 若 musl 缺陷 ⇒ 修 `components/musl`（补丁集，`docs/Process-01` 重导）；
   - 若是 ash 触发了 musl 未定义的用法 ⇒ 在 busybox 侧做最小适配并说明为何符合 musl ABI；
   - **不得**只删 `_` 赋值或改堆参数来掩盖。
3. 修后 `ISS-497`/`ISS-499` 填 `resolved_by`（`closed_in: M18`）。

## 验收（真实 rc）

1. **复现与归属**：最小用例（脚本化 stdin）在修前红、修后绿；给出 musl 侧断言的调用栈（`gdb`/`llvm-symbolizer` 或日志）。
2. **K6 回归**：`m18-linux-002` 的 17 条命令**单次启动**跑通（不再拆段）；`m18-linux-001` 28/28；`m18-linux-004` 的 200/200 启动 + 27 条长脚本仍绿。
3. **grep**：guest `grep` 正常（有匹配/无匹配 `-q` 各一例），rc 不再是 139。
4. **可达 FAIL ≥2 路**：回退 musl 修复 ⇒ 复现红；回退 busybox 适配（若走该路）⇒ grep/长脚本红。
5. 门控：`check-musl-freshness`、`check-patch-tree` musl/busybox 段 0 问题、`check-component-changelog`、`check-config-pins`、`check-linux-k5` 280/280、K0 146/146。
6. 完成区 ≤30 行；状态 → `待验收`。

## 约束

独立 worktree；不提交 git；只动 `components/musl/**`、`components/busybox/**`、必要证据脚本与任务书；不改 `spec/`/契约；术语「寄存器组」；组件补丁经 `make_patch.py` 重导。
