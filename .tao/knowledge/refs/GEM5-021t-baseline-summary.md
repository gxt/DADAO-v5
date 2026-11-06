# GEM5-021t gem5 SE tset 基线（static）

生成：2026-11-06T04:23:42Z（计数全部由本脚本从两份驱动 JSON 现场统计）

> **快照说明**：数字为 2026-11-06 的快照；随 GEM5-022t（brk/mmap 等 SE 能力）与后续任务落地，同一命令会得到不同计数。

范围：static link mode only (ADR-0048 D4 static first); dynamic linking/TLS/threads are outside this round

## 总览

- QEMU user 通过：587
- gem5 SE 通过：310
- 两侧都通过（both_pass）：310
- gem5 SE blocked：270（其中 QEMU 通过 = 268）
- gem5_only_fail（QEMU 通过、gem5 非通过且未 blocked）：9
- qemu_only_fail（gem5 通过、QEMU 未通过，ADR-0048 D5 需定位）：0
- 超预算重测另计（不计入上表）：通过 7、非通过 1（超时案例在更长预算下重跑，见下节）

## 分套件

### libc-test

- 发现/执行：QEMU discovered=367 total=337；gem5 discovered=367 total=337
- QEMU 计数：{'pass': 335, 'fail': 0, 'known-fail': 2, 'blocked': 0}
- gem5 计数：{'pass': 245, 'fail': 9, 'known-fail': 0, 'blocked': 83}（SE 超时 120s/例）
- 交叉：both_pass=245 gem5_blocked=83 (QEMU 通过 81) gem5_only_fail=9 qemu_only_fail=0 both_non_pass=0

### llvm-ts

- 发现/执行：QEMU discovered=222 total=214；gem5 discovered=222 total=214
- QEMU 计数：{'pass': 214, 'fail': 0, 'known-fail': 0, 'blocked': 0, 'excluded': 8, 'total': 214, 'pass_recorded': 211, 'pass_exit_only': 3}
- gem5 计数：{'pass': 27, 'fail': 0, 'known-fail': 0, 'blocked': 187, 'excluded': 8, 'total': 214, 'pass_recorded': 27, 'pass_exit_only': 0}（SE 超时 120s/例）
- 交叉：both_pass=27 gem5_blocked=187 (QEMU 通过 187) gem5_only_fail=0 qemu_only_fail=0 both_non_pass=0

### embench

- 发现/执行：QEMU discovered=19 total=38；gem5 discovered=19 total=38
- QEMU 计数：{'pass': 38, 'fail': 0, 'known-fail': 0, 'excluded': 0, 'blocked': 0}
- gem5 计数：{'pass': 38, 'fail': 0, 'known-fail': 0, 'excluded': 0, 'blocked': 0}（SE 超时 120s/例）
- 交叉：both_pass=38 gem5_blocked=0 (QEMU 通过 0) gem5_only_fail=0 qemu_only_fail=0 both_non_pass=0

## gem5_only_fail（QEMU 通过、gem5 未通过）

- libc-test:math/cos gem5=fail exit=1 — guest exit 1, expected 0: libc-test/src/math/crlibm/cos.h:375: RN cos(0x1.629c124f9167cp+695) want -0x1.d15000b496342p-3 got 0x1.d15000b496342p-3 ulperr 16371728137584640.000 = 0x1.d15p+53 + -0x1.ffa78ap-2
- libc-test:math/expm1 gem5=fail exit=1 — guest exit 1, expected 0: libc-test/src/math/crlibm/expm1.h:423: RN expm1(0x1.80345fb9bf501p+0) want 0x1.be1d656d0ed3cp+1 got 0x1.be1d656d0ed32p+1 ulperr -10.500 = -0x1.4p+3 + -0x1p-1
- libc-test:math/lgamma gem5=fail exit=1 — guest exit 1, expected 0: libc-test/src/math/sanity/lgamma.h:4: RN lgamma(-0x1.a206f0a19dcc4p+2) want -0x1.9c91f19ac48c5p+2,-1 got -0x1.9c91f19ac45bcp+2,-1 ulperr 777.440 = 0x1.848p+9 + 0x1.c2a38cp-2
- libc-test:math/lgamma_r gem5=fail exit=1 — guest exit 1, expected 0: libc-test/src/math/sanity/lgamma_r.h:4: RN lgamma_r(-0x1.a206f0a19dcc4p+2) want -0x1.9c91f19ac48c5p+2,-1 got -0x1.9c91f19ac45bcp+2,-1 ulperr 777.440 = 0x1.848p+9 + 0x1.c2a38cp-2
- libc-test:math/sin gem5=fail exit=1 — guest exit 1, expected 0: libc-test/src/math/crlibm/sin.h:400: RN sin(-0x1.b02f04875d125p+335) want -0x1.8bd0aba93469bp-2 got 0x1.8bd0aba93469ap-2 ulperr 13926506619207680.000 = 0x1.8bd0acp+53 + -0x1.fffff8p-2
- libc-test:math/sinh gem5=fail exit=1 — guest exit 1, expected 0: X libc-test/src/math/crlibm/sinh.h:84: RN sinh(0x1.d3e0d2f5d98d6p-2) want 0x1.e45428082fb8cp-2 got 0x1.e45428082fb8ap-2 ulperr -1.500 = -0x1p+1 + 0x1p-1
- libc-test:math/tan gem5=fail exit=1 — guest exit 1, expected 0: libc-test/src/math/crlibm/tan.h:277: RN tan(-0x1.f9347b8aefc11p+455) want -0x1.65e5cc95e64b7p+5 got 0x1.65e5cc95e64b6p+5 ulperr 12592403877724160.000 = 0x1.65e5ccp+53 + -0x1.ff3fap-2
- libc-test:math/tanh gem5=fail exit=1 — guest exit 1, expected 0: libc-test/src/math/ucb/tanh.h:57: RN tanh(-0x1.38148e27084ddp+1) want -0x1.f84024aed09edp-1 got -0x1.f84024aed09ebp-1 ulperr 1.873 = 0x1p+1 + -0x1.03eefep-3
- libc-test:math/tgamma gem5=fail exit=1 — guest exit 1, expected 0: X libc-test/src/math/sanity/tgamma.h:4: RN tgamma(-0x1.a206f0a19dcc4p+2) want -0x1.9fd0c1ce12f14p-10 got -0x1.9fd0c1ce12f12p-10 ulperr 1.597 = 0x1p+1 + -0x1.9c637p-2

## qemu_only_fail（gem5 通过、QEMU 未通过；ADR-0048 D5 单列）

（无）

## gem5 SE 缺口分类

| 能力 | blocked 案例数 | 代表案例 | 所需改动面 |
| --- | --- | --- | --- |
| heap/VMA (brk) | 114 | libc-test:functional/env、libc-test:functional/mbc、libc-test:functional/memstream、libc-test:functional/search_hsearch、libc-test:functional/search_insque | syscall: brk (SEWorkload syscall table + VMA/heap map) |
| file I/O | 40 | libc-test:functional/stat、libc-test:functional/utime、libc-test:regression/getpwnam_r-crash、libc-test:regression/getpwnam_r-errno、libc-test:regression/rewind-clear-error | syscall: file syscalls + guest fd table |
| time budget | 32 | libc-test:functional/clocale_mbfuncs、libc-test:functional/crypt、libc-test:functional/string_memset、llvm-ts:MultiSource/Applications/aha、llvm-ts:MultiSource/Benchmarks/MiBench/automotive-basicmath | simulator: per-case budget / engine speed (not a capability) |
| time/clocks | 28 | libc-test:functional/clock_gettime、libc-test:functional/fcntl、libc-test:functional/fdopen、libc-test:functional/fwscanf、libc-test:functional/ipc_msg | syscall: clock_gettime/nanosleep (+ SE clock source) |
| heap/VMA (mmap) | 21 | libc-test:functional/sscanf_long、libc-test:functional/tls_local_exec、libc-test:regression/malloc-oom、libc-test:regression/pthread_create-oom、libc-test:regression/setenv-oom | syscall: mmap + anonymous VMA allocation |
| signals | 21 | libc-test:functional/pthread_cancel、libc-test:functional/pthread_cancel-points、libc-test:functional/pthread_cond、libc-test:functional/pthread_mutex、libc-test:functional/pthread_tsd | syscall: rt_sigaction/rt_sigprocmask + signal frame |
| IPC/socket/pipe | 6 | libc-test:functional/fscanf、libc-test:functional/popen、libc-test:functional/socket、libc-test:functional/spawn、libc-test:regression/daemon-failure | syscall: pipe2/socket family + guest pipe/socket objects |
| threads/futex | 4 | libc-test:functional/pthread_mutex_pi、libc-test:functional/pthread_robust、libc-test:functional/vfork、libc-test:regression/pthread-robust-detach | syscall: clone/clone3/futex + TLS block per thread |
| resource limits | 2 | libc-test:regression/pthread_atfork-errno-clobber、libc-test:regression/rlimit-open-files | syscall: prlimit64/getrlimit (+ per-process limit state) |
| process creation/exec | 1 | libc-test:regression/execle-env | syscall: execve/fork/wait4 + multi-process SE support |
| process info | 1 | llvm-ts:MultiSource/Benchmarks/Prolangs-C/unix-smail | syscall: getpid/uname/getuid family |

## 超预算重测（120s 超时案例在更长预算下重跑）

- libc-test：重测 3 例（预算 600s）→ 通过 1、仍 blocked 2、其他 0
  - 通过：functional/string_memset
  - 仍 blocked：functional/clocale_mbfuncs, functional/crypt
- llvm-ts：重测 29 例（预算 600s）→ 通过 6、仍 blocked 22、其他 1
  - 通过：MultiSource/Benchmarks/MiBench/automotive-bitcount, SingleSource/Benchmarks/CoyoteBench/almabench, SingleSource/Benchmarks/Misc/matmul_f64_4x4, SingleSource/Benchmarks/Shootout/random, SingleSource/Benchmarks/Stanford/Perm, SingleSource/Benchmarks/Stanford/Towers
  - 仍 blocked：MultiSource/Applications/aha, MultiSource/Benchmarks/MiBench/automotive-basicmath, MultiSource/Benchmarks/NPB-serial/is, MultiSource/Benchmarks/Trimaran/enc-3des, MultiSource/Benchmarks/Trimaran/enc-md5, SingleSource/Benchmarks/BenchmarkGame/n-body, SingleSource/Benchmarks/BenchmarkGame/partialsums, SingleSource/Benchmarks/BenchmarkGame/recursive, SingleSource/Benchmarks/BenchmarkGame/spectral-norm, SingleSource/Benchmarks/McGill/queens, SingleSource/Benchmarks/Misc/ReedSolomon, SingleSource/Benchmarks/Misc/evalloop, SingleSource/Benchmarks/Misc/fbench, SingleSource/Benchmarks/Misc/fp-convert, SingleSource/Benchmarks/Misc/mandel-2, SingleSource/Benchmarks/Misc/perlin, SingleSource/Benchmarks/Misc/revertBits, SingleSource/Benchmarks/Misc/salsa20, SingleSource/Benchmarks/Shootout/fib2, SingleSource/Benchmarks/Shootout/sieve, SingleSource/Benchmarks/Stanford/FloatMM, SingleSource/Benchmarks/Stanford/Puzzle
  - 非通过 SingleSource/Benchmarks/Misc/pi（fail）：oracle mismatch (SingleSource/Benchmarks/Misc/pi.reference_output.small): fpcmp reported a difference (tolerance=0.001 abstol=- ignore-ws=False); first output: Starting PI...

## 引擎与快照

- gem5 组件锁定 commit：`c8222cc67a399bfc01e8658dd14b30d5bfd634f9`
- 分支补丁集：`components/gem5/series` 97 条
- 快照引擎：gem5 `25.1.0.1`，编译于 `Nov  6 2026 01:17:05`（banner 取自运行期 sim 日志）
- gem5.opt sha256：不可复原（共享构建树在快照后被并行任务重建覆盖）；同一 `commit`+`series` 可由 `make build-gem5` 复现

## 复跑

```
JOBS=32 python3 tools/testcases/tset/gem5-se-baseline/run_gem5_se_baseline.py \
    --work-dir <runtime dir> --json-out <runtime dir>/gem5-se-baseline.json
```

驱动层单套件：给三个 tset 驱动加 `--engine qemu|gem5-se`；gem5 SE 走 `configs/dadao/se.py --binary <elf>`，只接受静态 `ET_EXEC`。
