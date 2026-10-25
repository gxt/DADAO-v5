# QEMU-075t: qemu-user 宿主信号族诊断（ISS-255/257/266，时盒，只诊断）

**模块**：qemu
**项目里程碑**：M10
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地（只读诊断 + 证据脚本；不改 qemu 语义）

## 接口规范

### 背景
三条 open issue 都与「`qemu-dadao` 上以**宿主信号**终止」有关：

- **ISS-255**：`libc-test` 的 `regression/flockfile-list`、`regression/setenv-oom` 以宿主 `SIGBUS`/`SIGTRAP` 结束（非 guest 退出码）；
- **ISS-257**：`regression/pthread_create-oom` 抖动：一次 `pass`，其后 5/5 pilot + 8/8 单跑全 `BLOCKED`（宿主信号 5）；疑因 guest `setrlimit(RLIMIT_AS)` 直通宿主 qemu 进程；
- **ISS-266**：`llvm-test-suite` 的 SPASS / consumer-typeset / 8b10b / dbms 在 `qemu-dadao` 上以宿主 `SIGSEGV` 终止（静态/动态一致）。

### 目标（**只诊断，不改语义**）
1. 逐例**可复现**：给出最小命令、宿主信号编号、guest 侧最后状态、日志路径；
2. **根因归类**：判定三组是否同源（`setrlimit` 直通 / 内存映射 / 信号投递 / 指令语义 / 栈溢出），给出证据（strace/`/proc`/`gdb` 宿主侧、guest 寄存器/PC、`qemu` 日志）；
3. **修法建议**：每类给出「最小修法 + 影响面 + 预估工作量」，**不实施**（语义/ABI 改动留待用户裁定）；
4. 若发现是测试侧（如 `setrlimit` 用例在 qemu-user 下本就不可判定）⇒ 明确「应记 blocked 还是可判失败」，给判据。

### 约束
- **时盒 ≤ 2 小时**；到时无论是否定根因都停下报告（保留现场）。
- **不改** `components/qemu/**`、`spec/`、`contracts/`、测试期望；只允许新增 `.work/` 证据脚本与日志。
- 若必须改 qemu 才能继续（例如加日志），先停下报告，不擅自改。

## 验收标准
1. 三条 issue 各有：最小复现命令 + 宿主信号/退出码 + 现场日志路径。
2. 同源/异源判定有证据（对照表：触发条件、信号、`setrlimit` 行为、映射差异）。
3. 每类给「最小修法 + 影响面 + 工作量」；不改任何代码。
4. 完成区贴真实命令、输出、退出码；未决项单列。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
