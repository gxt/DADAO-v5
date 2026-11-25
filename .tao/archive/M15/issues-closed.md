<!-- 由 tools/infra/archive_issues.py 按 closed_in == M15 生成，勿手改 -->

# M15 阶段已关闭 Issue

> **判据**：`status: closed` 且 `closed_in == M15`（关闭时写定，归档直接取集）。
> **计数**：**2 条**。
> **补记（2026-11-25）**：`ISS-476`（`m15-idl-019` 关闭）原先误置于 `issues-m17.yaml`（`milestone: M17`、`closed_in: M15`）；按其 `closed_in` 归 M15 补入本快照，并从活台账删除。

| id | scope | resolved_by | title |
| --- | --- | --- | --- |
| ISS-502 | [picolibc, testcases] | m15-infra-010（times() 按 tickfreq 缩放） | 【P2】picolibc 的 `clock()` 在 dadao/qemu 上单位错 1000×：`clock()` → `times()`（`libos/semihost/common/times.c` 直接返回 `sys_semihost_elapsed()`，未按 tick 频率缩放）→ `SYS_ELAPSED`（0x30）；QEMU 的 `TARGET_SYS_ELAPSED` 返回**纳秒**、`SYS_TICKFREQ`=1e9（`semihosting/arm-compat-semi.c`），而 picolibc `time.h` 的 `CLOCKS_PER_SEC` 写死 **1,000,000**（µs）⇒ `clock()/CLOCKS_PER_SEC` 报出的秒数大 1000×。`gettimeofday` 正确按 `SYS_TICKFREQ` 缩放，可用作计时。处置：ansibench 计时改用 `gettimeofday` 或提供 `clock()` shim（按 tickfreq 缩放）；若修 picolibc，应在 `times()` 里按 `sys_semihost_tickfreq()/CLOCKS_PER_SEC` 缩放并同步 `_CLOCKS_PER_SEC_` 口径。 |
| ISS-476 | [idl] | m15-idl-019（裁定 A：改调 ft_scale） | 【P2】`ftsclb_orrr_rf` 的临时写法在指数极值处会下溢（合 §2.1/IEEE 应为溢出）：`e64 = off + n` 以 64 位有符号视图越过 2^63 变负 ⇒ 命中 `< -2000` 饱和。分叉区间 = `n ∈ [2^63-260, 2^63-1]`（src 有限非零、5 档舍入全中）：临时写法给 `±0`/`±1` + `UF|NX`，库 `ft_scale` 给 `±Inf`/`±最大有限` + `OF|NX`。仓内 spec-exact oracle `tools/chipyard/fp_ref.py::sclb_exact` 与库侧 0 失配、与临时写法全反；f64 兄弟 `fosclb` 早已直调 `fo_scale` ⇒ f32/f64 口径不一致。修法见 `m15-idl-019`（待裁定 A/B）。 |
