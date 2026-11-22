<!-- 由 tools/infra/archive_issues.py 按 closed_in == M15 生成，勿手改 -->

# M15 阶段已关闭 Issue

> **判据**：`status: closed` 且 `closed_in == M15`（关闭时写定，归档直接取集）。
> **计数**：**1 条**。

| id | scope | resolved_by | title |
| --- | --- | --- | --- |
| ISS-502 | [picolibc, testcases] | m15-infra-010（times() 按 tickfreq 缩放） | 【P2】picolibc 的 `clock()` 在 dadao/qemu 上单位错 1000×：`clock()` → `times()`（`libos/semihost/common/times.c` 直接返回 `sys_semihost_elapsed()`，未按 tick 频率缩放）→ `SYS_ELAPSED`（0x30）；QEMU 的 `TARGET_SYS_ELAPSED` 返回**纳秒**、`SYS_TICKFREQ`=1e9（`semihosting/arm-compat-semi.c`），而 picolibc `time.h` 的 `CLOCKS_PER_SEC` 写死 **1,000,000**（µs）⇒ `clock()/CLOCKS_PER_SEC` 报出的秒数大 1000×。`gettimeofday` 正确按 `SYS_TICKFREQ` 缩放，可用作计时。处置：ansibench 计时改用 `gettimeofday` 或提供 `clock()` shim（按 tickfreq 缩放）；若修 picolibc，应在 `times()` 里按 `sys_semihost_tickfreq()/CLOCKS_PER_SEC` 缩放并同步 `_CLOCKS_PER_SEC_` 口径。 |
