# m15-infra-010: 修 picolibc `times()`/`clock()` 的 tick 频率缩放（ISS-502）

**模块**：infra
**项目里程碑**：M15
**依赖**：`ADR-0058`（时间测量口径，Candidate；本任务只落地 D2 第 2 条）
**可并行分片**：否
**预估**：1–2 h
**档位**：中改（picolibc 补丁 + 回归）
**状态**：已验证

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

## 审阅记录

### 第 1 轮 engineer 自审

**逐行核过**：`times.c` 的缩放/错误分支（`freq` 取值、`__int128` 中间量、`clock_t` 上限、`tms` 形状）、补丁导出与 `series` 计数、`picolibc.ld.in` 的 `.text` 首段、证据脚本每条断言的可达 FAIL 与还原路径（`cp`+md5，未用 checkout/restore/stash）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `CLOCKS_PER_SEC` 未声明（`<sys/times.h>` 不带它）⇒ 编译错 | ✅已修 | `times.c` 增 `#include <time.h>` | `make build-picolibc` rc=0 |
| `clock_t` 上限检查假定 64 位无符号 | ❌不修 | 核 `libc/include/sys/_types.h:179`：本端口 `__clock_t = __uint64_t`，注释已写明 | 源码核对 + 构建 |
| 新增 `__udivti3`（i128 除法）依赖 | ❌不修 | `libclang_rt.builtins.a` 有 `T __udivti3`；picolibc 自测/冒烟按需链 builtins | `llvm-nm` + 冒烟 rc=0 |
| `freq == (uintptr_t)-1` 也判错（任务书只写 `freq==0`） | ❌不修 | 依 `contract-semihosting.md §3`：`SYS_TICKFREQ` 以 `-1` 表示不可用，静默算 0 更糟 | 契约口径 |
| 证据脚本 `local tag=$1 out="$WORK/..."` ⇒ `set -u` 下 `tag` 未绑定 | ✅已修 | 拆成两条 `local` | 重跑 21/21 PASS、rc=0 |
| 安装版 lds 无 `.text.start` 段 ⇒ `.text.unlikely.*` 抢段首、`e_entry` 偏移、18/20 测试加载期红（**009 迁移漏项，非本笔引入**） | ✅已修（越原任务语义，已披露） | `picolibc.ld.in` 的 `.text` 首段加 `KEEP (*(.text.start))`；证据加 `e_entry` 断言 | `e_entry=0xffffff010100`；fast `pass=18 fail=0` |
| 自测 harness 的 `.done` 复用缓存（qemu 时 `sim_md5` 恒 null）会掩盖上一条 | ✅已修（证据侧） | 证据脚本跑 harness 前删 `run/`（运行期目录） | 21/21 PASS 为真跑 |

**判决**：所有 finding 已处置（修或附证据不修），状态 → `待验收`。

### 第 1 轮主会话验收（2026-11-22，独立复跑）

**重跑（本人执行，输出与退出码现场取，不采信完成区）**

| 项 | 命令/入口 | 实测 | rc |
|---|---|---|---|
| 探针（修后） | 运行期证据目录 `build_run.sh`，`SPIN=4000000` | `clock_us=3572779 vs tod_us=3572260`（ratio_milli=1000，差 519 µs，limit 178613）；`e_entry=0xffffff010100` | 0 |
| 探针（第二次） | 同上 | `clock_us=3579438 vs tod_us=3578914`（差 524 µs） | 0 |
| picolibc 自测 | 删 `picolibc-tests-run` 后 `--stage fast --jobs 30` | `total=20 pass=18 fail=0 excluded=2 blocked=0` | 0 |
| smoke | `make test-picolibc-smoke` | `libm: qemu rc=0 output='libm 0'` / `PASS` | 0 |
| 补丁树 | `make check-patch-tree` | `picolibc: 17 patch(es)`、picolibc 段 0 problem/assertion | 0（picolibc 段） |
| 三门控 | changelog / config-pins / knowledge-refs | `PASS` / `89 项 0 失败` / `PASS` | 0 |

**注入（本人做 2 路；`cp` 备份 + md5，禁 `git checkout/restore`）**

1. `times()` 去缩放（`ticks = elapsed`）→ 重建 → 探针 `ratio_milli=1000021`、`MISMATCH`、**rc=1**；`cp` 还原后 `times.c` md5 `9d73203e…` 与注入前相同 → 重建 → 探针 `ratio_milli=1000`、`rc=0`。
2. 安装版 lds 删 `KEEP (*(.text.start))` 两行 → 跑 4 例（`test-acos`/`test-ffs`/`semihost-argv`/`math_test`）→ **3 fail rc=1**、`picolibc-tests: FAIL`；`cp` 还原后 lds md5 `895e7cfa…` 相同 → 同 4 例 **4/4 pass rc=0**。

**约束核验**

- 改动 5 项（新 `times.c.patch`、`picolibc.ld.in.patch`、`series`、`changelog`、任务书），与完成区「修改文件」逐项一致；`git diff -- components/` 之外为空。
- 未提交 git、未改版本号、未动 `spec/`/契约；还原全程 `cp`+md5，未用 `git checkout/restore/stash`。

**越界认定（接受，不拆分）**

`picolibc.ld.in.patch` 的 `KEEP (*(.text.start))` 超出「times() 缩放」语义，但：同属 `components/picolibc/**`、同一补丁文件；修的是 `m15-infra-009` 删旧 lds 副本时漏带的段，属该补丁的完整性；无此修复则本任务的回归在干净树上 18/20 红，无法验收。已在 changelog 与本记录披露，并登记 `ISS-505`（009 的 `pass=6` 系 `.done` 复用假绿）。

**发现（非阻断，已登记）**

- `.done` 复用键在 qemu 引擎下 `sim_md5` 恒为 `None` ⇒ 换库/换 lds 仍复用旧判决；须把 `libc.a`+lds 指纹纳入 key 或加 `--force`（`ISS-504`）。
- `sysconf(_SC_CLK_TCK)` 仍返回 tickfreq，与修后 `times()` 的 `CLOCKS_PER_SEC` 单位不一致（`ISS-502` 残项，ADR-0058 D2 后半）。

**判决**：核心改动、两条断言注入可达 FAIL、回归全绿、越界有据 ⇒ **Accepted**。

## 完成区

**测试结果**：
1. **修前复现**（基线库、同一忙等探针：picolibc + Tiny lds + `crt0_tiny_picolibc.S`）：`clock_us=1073617554` vs `tod_us=1073599` ⇒ `clock()/CLOCKS_PER_SEC` = **1000.017×** `gettimeofday`。
2. **修后**：`clock_us=3565354` vs `tod_us=3564836`（3.565 s，差 518 µs / 0.015%）⇒ 5% 断言通过；`e_entry=0xffffff010100`。
3. **注入 ①（回退成 pre-fix 一行）**：rc=1、`ratio_milli=1000027`；`cp`+md5 还原+重建 ⇒ 回绿（`ratio_milli=1000`）。**注入 ②（`freq = CLOCKS_PER_SEC`）**：rc=1、`ratio_milli=1000003`；还原+重建 ⇒ 回绿。
4. `make check-picolibc-tests`（fast，先清 `/run` 缓存）：`total=20 pass=18 fail=0 excluded=2 blocked=0 skipped=0`，rc=0。
5. `make test-picolibc-smoke`：PASS，rc=0。
6. `check-patch-tree`：picolibc 段 **0 问题**、17 patch == `series` 17 行（全局 rc=1 仅因其它组件源树未 fetch）；`check-component-changelog`/`check-config-pins`/`check-knowledge-refs` rc=0。
7. 运行期证据目录内 `run.sh`：**21/21 PASS、rc=0**（含注入→FAIL→还原→回绿自检）。

**修改文件**：新增 `components/picolibc/patches/libos/semihost/common/times.c.patch`；改 `components/picolibc/patches/picolibc.ld.in.patch`、`components/picolibc/{series,changelog.md}`；证据脚本（运行期目录，不入库）；本任务书。

**验收结果**：同「测试结果」1–7 条，均为真实命令输出/退出码（日志在运行期证据目录）。

**新发现/坑**：
- **009 的 lds 迁移漏 `.text.start`**：旧仓库 lds 副本有 `KEEP(*(.text.start))`，安装版 `picolibc_noflash.ld` 没有 ⇒ `.text.unlikely.*`（assert）抢段首、`e_entry` 从 `0xffffff010100` 偏到 `+0x40`，QEMU 加载期直接拒（干净 worktree 实测 fast 18/20 红）。009 报的 `pass=6` 是 `.done` 缓存复用（main 仓仍留有 11-14 旧 lds 产物的判决），非真跑。本任务已补 lds 并加 `e_entry` 断言。
- **harness `.done` 复用键不含库指纹**：qemu 引擎下 `sim_md5` 恒 null，换库/换 lds 仍复用旧判决；证据与复核前须删 `.picolibc-tests-run/run`，建议给 harness 加 `--force` 或把 `libc.a` md5 纳入 key。
- **`sysconf(_SC_CLK_TCK)` 未同步**：仍返回 tickfreq（1e9），而修复后 `times()` 以 `CLOCKS_PER_SEC` 为单位（ADR-0058 D2 第 2 条后半未落地）；本任务范围只含 `times()`，未改。

**遗留问题**：① `sysconf(_SC_CLK_TCK)` 与 `times()` 单位不一致（见新发现，建议另立任务/登记 `ISS-502` 残项）；② lds `.text.start` 修复超出原任务语义（同为 `components/picolibc/**`），如需独立任务请拆分。
