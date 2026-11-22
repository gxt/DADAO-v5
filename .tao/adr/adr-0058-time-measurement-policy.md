# ADR-0058: 时间测量口径（guest 性能只用全局时间，semihosting 时间不得作判据）

**状态**：Candidate
**日期**：2026-11-22
**关联**：`DD-E008 §9`、`DD-C008 §7`、`DD-D002 §7`；`ISS-502`；`m15-testcases-023`（ansibench 计时语料）；`contract-see §3`（`cfx_time`：1 GHz、1 count = 1 ns）；`spec/DADAO-12 §4.10`

## Context（背景）

`m15-testcases-023` 把 ansibench 四件（coremark/dhrystone/linpack/whetstone）接到 Tiny + picolibc 时，暴露出时间口径问题：

- picolibc 的 `clock()` 链路是 `clock()` → `times()`（`libos/semihost/common/times.c`，直接返回 `sys_semihost_elapsed()`，**不按 tick 频率缩放**）→ `SYS_ELAPSED`（0x30）；
- QEMU 的 `TARGET_SYS_ELAPSED` 返回**宿主单调时钟的纳秒**（`semihosting/arm-compat-semi.c`，`get_clock() - clock_start`），`SYS_TICKFREQ` = 1e9；
- picolibc `libc/include/time.h` 的 `CLOCKS_PER_SEC` 写死 **1,000,000**（µs）；
- ⇒ `clock()/CLOCKS_PER_SEC` 在 qemu-dadao 上报出的秒数**大 1000×**（`ISS-502`）。`gettimeofday` 按 `SYS_TICKFREQ` 正确缩放。

影响面不止 ansibench：任何用 `clock()`/`times()` 的库代码、基准的「按时间自停 / iterations-per-sec」、以及未来真机上的计时，都会得到不可比甚至错误数字；而 semihosting 时间本质上随宿主负载变化，不能作为 guest 性能判据。

ADR 判据：高代价（跨库/测试/真机）× 跨模块（picolibc、tests、DDLN）× 多方案（shim / 修库 / 改 `CLOCKS_PER_SEC` / 真机 `cfx_time`）× 结论固化（判据口径）——**四项全中**。

## Decision（决策）

- **D1 判据口径**：**guest 侧的性能与超时判据只用全局时间 `cfx_time`**（1 count = 1 ns，`contract-see §3`）或 gem5 的周期模型；**semihosting 的 `SYS_ELAPSED`/`gettimeofday` 只用于宿主侧 liveness、看门狗与日志时间戳，不得进入任何性能/超时判据**。
  - 依据：semihosting 时间由宿主实现，随宿主负载、TCG 翻译缓存变化；`cfx_time` 是 guest 自有时基，与宿主无关。
- **D2 `clock()` 缺陷定性与修复顺序**：`ISS-502` 是 **picolibc `times()` 未按 `SYS_TICKFREQ` 缩放**（不是 QEMU 的错，也不是 `cfx_time` 的错）。修复顺序：
  1. **短期（项目侧，不改进语料/库）**：测试与基准使用 `gettimeofday`，或链接一个 `clock()` shim（按 `SYS_TICKFREQ/CLOCKS_PER_SEC` 缩放；shim 放项目侧，覆盖 `libc.a` 前）；
  2. **中期（picolibc 补丁，上游可接受）**：`libos/semihost/common/times.c` 按 `sys_semihost_tickfreq()` 做溢出安全缩放（`elapsed * CLOCKS_PER_SEC / tickfreq` 的 muldiv 形式），`sysconf(_SC_CLK_TCK)` 与 `CLOCKS_PER_SEC` 同步；
  3. **真机（无宿主）**：由 DADAO 的 machine port 提供 `clock()`，读 `cfx_time` 并换算为 `CLOCKS_PER_SEC` 单位。
  - **禁止**：改 `CLOCKS_PER_SEC` 去迁就 `SYS_ELAPSED` 的 ns 单位（会破坏 POSIX/ANSI 惯例与其它平台的可比性）。
- **D3 计时语料判据**：ansibench 等计时语料在测试门控里**只断言「跑通 + 结果正确性」**（exit 0、关键输出/自校验），**耗时不设阈值**；参数用**固定迭代/固定 N**，不得依赖「按时间自停」。
- **D4 报告口径**：任何耗时数字必须标注来源（`cfx_time` / gem5 cycles / semihosting host time），**禁止跨来源比较**；semihosting 时间数字不得写进性能结论。与真机/其它引擎的比值只作记录，不设阈值（除非另立 ADR）。
- **D5 修复验收**：picolibc 侧修复或 shim 须同时满足：① 同一段忙等，`clock()/CLOCKS_PER_SEC` 与 `gettimeofday` 的秒数在 5% 内一致；② 宿主负载变化时 `cfx_time` 稳定，而 semihosting 时间明显漂移（对照记录）。

## Rationale（理由）

- **为什么不能把 semihosting 时间当判据**：它测的是「宿主跑了多久」，不是「guest 执行了多久」；在 TCG 下没有固定指令吞吐率（`1e9` 是纳秒/秒，不是指令/秒），把它写进阈值会把宿主负载变成红灯来源。
- **为什么修 `times()` 而不是改 `CLOCKS_PER_SEC`**：`CLOCKS_PER_SEC` 是 ANSI/POSIX 的库常量，跨平台工具/测试按 1e6 假设；改它会让同一份代码在不同平台语义分叉。按 `SYS_TICKFREQ` 缩放才是 semihosting 规范的正确口径。
- **为什么保留 `gettimeofday`**：它已经按 tick 频率缩放，是「墙上时间」的正确接口；性能测量仍应使用 `cfx_time`，二者职责不同。

**被否方案**：

- ① 把 `CLOCKS_PER_SEC` 改成 1e9（等于把纳秒当 tick）；② 让 QEMU 的 `SYS_ELAPSED` 改成 1e6 单位（改宿主语义、影响其它 guest）；③ 在 ansibench 里按 `clock()` 自停（把宿主负载引入测试时长）；④ 只用 `gettimeofday` 做性能判据（仍是宿主时间，只是单位对）。

## Consequences（影响）

- **正面**：测试与基准的时间判据与宿主解耦；`ISS-502` 有明确修复路径；真机计时口径提前定死。
- **负面/约束**：短期需要项目侧 `clock()` shim 或改用 `gettimeofday`；中期要给 picolibc 打补丁并重跑 `check-picolibc-tests`；ansibench 的耗时数字只能作相对参考且必须标注来源。
- **不变**：`cfx_time` 的寄存器语义与 `contract-see §3`；QEMU/宿主 semihosting 实现（除另有任务）。
- **后续**：真机（M19）上若 semihosting 无服务端，`clock()`/`gettimeofday` 全部由 `cfx_time` shim 提供；若将来需要跨平台性能对比，另立 ADR 定义周期/频率口径。

## 状态说明

2026-11-22 由主会话起草（触发：用户「时钟的事情是真实、影响面很大的问题」并要求更新 DDLN 后立 ADR）。逐条确认进度：

- **D1 判据口径（只用 `cfx_time`）** —— ⏳ 待确认
- **D2 `clock()` 修复顺序（shim → picolibc → 真机）** —— ⏳ 待确认
- **D3 计时语料只断言跑通/正确性** —— ⏳ 待确认
- **D4 报告须标注时间来源、禁跨来源比较** —— ⏳ 待确认
- **D5 修复验收（5% 一致 + 负载漂移对照）** —— ⏳ 待确认

未确认前保持 `Candidate`，相关任务不得据此扩大范围（`m15-testcases-023` 的短期 shim 属 D2 第 1 条，可先行）。
