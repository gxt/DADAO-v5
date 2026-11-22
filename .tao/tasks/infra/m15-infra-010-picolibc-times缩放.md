# m15-infra-010: 修 picolibc `times()`/`clock()` 的 tick 频率缩放（ISS-502）

**模块**：infra
**项目里程碑**：M15
**依赖**：`ADR-0058`（时间测量口径，Candidate；本任务只落地 D2 第 2 条）
**可并行分片**：否
**预估**：1–2 h
**档位**：中改（picolibc 补丁 + 回归）
**状态**：待开始

## 背景（`ISS-502`）

picolibc `clock()` 的单位错 1000×：

```
clock() → times()                     libos/semihost/common/times.c
        → sys_semihost_elapsed()      libos/semihost/common/sys_elapsed.c
        → SYS_ELAPSED (0x30)          QEMU: 宿主单调时钟「纳秒」，SYS_TICKFREQ=1e9
```

`times()` 直接把 elapsed 当 `clock_t` 返回，**未按 `SYS_TICKFREQ` 缩放**；而 `CLOCKS_PER_SEC` 固定 1e6（µs）⇒ `clock()/CLOCKS_PER_SEC` 在 qemu-dadao 上大 1000×。`gettimeofday` 已正确按 `SYS_TICKFREQ` 缩放。

## 要做

1. 改 `components/picolibc/patches/libos/semihost/common/times.c.patch`（经 `.work/source/picolibc` 编辑 → 单个本地 commit → `make_patch.py picolibc` 重导）：
   - `times()` 把 `sys_semihost_elapsed()` 从 tick 换算到 `CLOCKS_PER_SEC` 单位：`ticks = elapsed * CLOCKS_PER_SEC / freq`，用 **muldiv/`__int128` 防溢出**；`freq` 取 `sys_semihost_tickfreq()`；
   - `freq == 0` 或换算结果溢出 `clock_t` 时返回 `(clock_t)-1`（POSIX 语义），不静默；
   - `tms_stime/cstime/cutime = 0`、`tms_utime = ticks` 的既有形状不变；
   - `gettimeofday` 不动；`CLOCKS_PER_SEC` 不改（禁止用改常量迁就 ns）。
2. 同步 `components/picolibc/changelog.md`（M15 条目），`series` 由 `make_patch` 维护。
3. 证据：一个探针程序（picolibc 链接，Tiny lds + `crt0_tiny_picolibc.S`），同一段忙等分别用 `clock()/CLOCKS_PER_SEC` 与 `gettimeofday` 计时，二者秒数在 **5% 内一致**。

## 验收（真实 rc）

1. **修前复现**：同一探针在修前 `clock()` 秒数 ≈ 1000× `gettimeofday`（记录实测）；**修后 5% 内一致**。
2. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退缩放（直接返回 elapsed）⇒ 5% 断言红；② 把 `freq` 换成 1e6 ⇒ 红。
3. `make check-picolibc-tests`（fast）rc=0；`test-picolibc-smoke` rc=0；
4. 门控：`check-patch-tree` picolibc 段 0 问题、`check-component-changelog`、`check-config-pins`、`check-knowledge-refs` rc=0；
5. 完成区 ≤30 行；状态 → `待验收`。

## 约束

独立 worktree；不提交 git；只动 `components/picolibc/**` + 必要证据脚本与任务书；不改 `spec/`/契约；不改 `CLOCKS_PER_SEC`；组件补丁经 `make_patch.py picolibc` 重导；术语「寄存器组」。
