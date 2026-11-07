# GEM5-021t 基线结论与缺口排序（static）

> 计数以 `GEM5-021t-baseline-summary.md`（同目录，脚本现场统计）为准；本文件只写**结论、根因和下一步**，不重抄数字。

## 1. 结论

- **SE 路径可用**：三个 tset 驱动均可 `--engine gem5-se` 跑同一份 static 产物；embench 全量通过（QEMU 与 SE 一致），libc-test 与 llvm-ts 有明确能力缺口。
- **`qemu_only_fail` = 0**：没有「gem5 通过而 QEMU 未通过」的案例，ADR-0048 D5 的方向无异常。
- **`BLOCKED` 集中在 syscall 面**，按修复顺序：`brk` → `mmap` → 文件 I/O → 时钟 → 信号 → 线程/futex。缺口表见 summary。
- **9 个 libc-test `math/*` + 1 个 llvm-ts `pi`（超预算重测）源于 float→int 转换的舍入口径不一致**，不是 SE 能力缺口；语义归属**待用户裁定**（`discussing.md` 的 A/D/B/C 方案未定）——见 §2。

## 2. 关键差异：float→int 转换舍入（SPEC / 工具链 / QEMU 不一致，语义归属待裁定）

**事实**（`.tao/knowledge/discussing.md` 2026-11-06「convert_f2i 舍入语义」）：

- `SPEC/SimRISC-07` + `contract-fp §3` 写「浮点→整数转换的舍入由 `rf0[33:32]` 控制」（默认 RNE）；
- 编译器对 `(long long)x` 只发**裸 `fo2io`**，不写 `rf0`；
- QEMU **截断**（`2.7 → 2`），gem5 **按 rf0 舍入**（`2.7 → 3`）。

最小复现（`-O0` 静态链接，同一 ELF 两引擎）：

```c
volatile double a = 2.7, b = -2.7;
printf("a=%lld b=%lld\n", (long long)a, (long long)b);
```

- `qemu-dadao`：`a=2 b=-2`；gem5 SE：`a=3 b=-3`。

**9 个 `math/*` 的具体 cast 位点**（musl 源码，三处，不是单一 `__rem_pio2_large`）：

1. `src/math/__rem_pio2_large.c:303/304/311`（以及 `:378/379`）：`(int32_t)z`、`(int32_t)(z - 0x1p24*fw)` 用于 Payne-Hanek 分片 ⇒ `sin` / `cos` / `tan`（大参数 |x| 达 2^300–2^700，舍入使约化参数偏移，1 ulp 到上万 ulp 并被放大成符号翻转）。
2. `src/math/expm1.c:153`：`k = invln2*x ± 0.5`（`int k` 的隐式 double→int）⇒ `expm1` / `sinh` / `tanh`（差 1–2 ulp，`X` 为异常标志）。
3. `src/math/lgamma_r.c:156`（`sin_pi`：`n = (int)(x*4.0)`）与 `:255`（`i = (int)x`）⇒ `lgamma` / `lgamma_r` / `tgamma`。

`llvm-ts` 的 `SingleSource/Benchmarks/Misc/pi` 同一根因：`pi.c` 的 `(long int)(iprod/74383)`、`(long int)(prod/ymod)` 依赖截断做线性同余。

**归属**：**不判「gem5 单方缺陷」**。三方口径不一致（SPEC 写 rf0 控制、工具链不写 rf0、QEMU 截断），修哪一侧属**待用户裁定**（`discussing.md` 的 A 固定 RTZ / D 编译器发 `fornd(0x04)+convert` / B 每条 cast 写恢复 rf0 / C 新增静态 RTZ 变体；2026-11-06 用户「先做别的」）。裁定前：这 10 行保持 `gem5_only_fail`，**不得**当作 SE 能力缺口，也不得为对齐而改 QEMU/gem5/工具链。

## 3. 缺口排序（作为后续实现任务的输入）

1. **`brk`（最大单一缺口）**：malloc 家族一进入堆就 fatal。改动面：`SEWorkload::syscall` 的 `brk` + `Process` 的 heap VMA 映射（`brk_point` 已存在）。
2. **`mmap`/`munmap`**：TLS、`malloc-oom`、`setenv-oom`、`pthread_create-oom` 等。改动面：匿名 VMA 分配 + 与 `SETranslatingPortProxy` 的 map 路径。
3. **文件 I/O**（`openat/read/pread64/lseek/fstat/newfstatat/getdents64/dup/statfs/utimensat` 等）：`stdio` 的文件后端、`stat` 家族。改动面：guest fd 表（`Process::fds` 已有）+ 宿主 fd 转发。
4. **时钟**（`clock_gettime`/`nanosleep`/`times`）：`time()`/`clock()` 依赖。改动面：SE 时钟源（与 TICKFREQ 口径一致，避免与 `GEM5-019t` 冲突）。
5. **信号**（`rt_sigaction`/`rt_sigprocmask`/`rt_sigreturn`/`sigaltstack`）：pthread 取消/条件变量/测试框架用。改动面：信号投递 + 用户栈帧（SE 单进程也要有 self-signal 路径）。
6. **线程/futex**（`clone`/`clone3`/`futex`）：`GEM5-014t` 已注明属后续；需 TLS block per thread。
7. **`execve`/`fork`/`pipe2`/`socket`/`prlimit64`**：多进程与 IPC，最后做。
8. **动态链接（`ET_DYN`/`PT_INTERP`）** 与 **TLS**：按 ADR-0048 D4 「后补但不得降级」，本轮只登记，不计入基线。

## 4. 时间预算（不是能力缺口）

120 s/例 对原子 CPU 偏紧：超预算重测（600 s）有 7 例转 PASS、22 例仍 blocked（纯计算量），libc-test 也有 1 例转 PASS。**结论**：M11 的 tset 门控若纳入 llvm-ts，需要按套件给预算（例如 600 s 起），不能把「超时」当作能力结论；summary 里 `time budget` 一行只代表「120 s 内没跑完」。

## 5. 口径与边界

- 只测 **static**；dynamic/TLS/线程未验证（non-scope）。
- llvm-ts 只覆盖驱动声明的 scope A（214 例），scope B/C 未运行（驱动原有口径）。
- SE 的 guest fd1/fd2 是两个宿主文件，llvm-ts 的比较文档 = stdout 后接 stderr（QEMU 轮是 `2>&1` 交错）；JSON 记录该口径。本轮没有案例因此产生差异（gem5_only_fail 均为数值/输出差异，非顺序差异）。
- **快照时点**：本轮数字早于 `GEM5-022t`；该任务落地 `brk` 后，指向同一子集的回归复跑里 `functional/memstream` 已由 blocked 转 pass（embench full 仍 38/38）。summary 首行已注明快照属性。
- 复跑与反例见 GEM5-021t 运行期证据脚本（未归档；`INJECT=1` 自带两处注入；`RUN_L1=1` 附带 `make check`）。
