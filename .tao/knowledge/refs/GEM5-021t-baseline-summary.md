# GEM5-021t gem5 SE tset 基线（static）

生成：2026-11-09T00:30:55Z（计数全部由本脚本从两份驱动 JSON 现场统计）

> **快照说明**：数字为运行时刻的快照（见 generated_utc）；随 SE 能力落地，同一命令会得到不同计数。timeout 为预算到期，单列，不计入能力缺口。

范围：static link mode only (ADR-0048 D4 static first); dynamic linking/TLS/threads are outside this round

## 总览

- QEMU user 通过：587
- gem5 SE 通过：474
- 两侧都通过（both_pass）：474
- gem5 SE blocked（能力缺口，**不含 timeout**）：8（其中 QEMU 通过 = 7）
- gem5 SE timeout（预算到期，**非能力缺口**、非判决）：97（其中 QEMU 通过 = 97；blocked_all 含 timeout = 105）
- gem5_only_fail（QEMU 通过、gem5 非通过且未 blocked）：9
- qemu_only_fail（gem5 通过、QEMU 未通过，ADR-0048 D5 需定位）：0
- 超预算重测另计（不计入上表）：**通过 23、转 fail 2、仍超时 72**（原 97 例超时在 1200 s 下重跑，见下节）

## 分套件

### libc-test

- 发现/执行：QEMU discovered=367 total=337；gem5 discovered=367 total=337
- QEMU 计数：{'pass': 335, 'fail': 0, 'known-fail': 2, 'blocked': 0}
- gem5 计数：{'pass': 321, 'fail': 4, 'known-fail': 1, 'blocked': 11}（SE 超时 300s/例）
- 交叉：both_pass=321 gem5_blocked（不含 timeout）=6 (QEMU 通过 5) gem5_timeout=5 (QEMU 通过 5) gem5_blocked_all=11 gem5_only_fail=4 qemu_only_fail=0 both_non_pass=1

### llvm-ts

- 发现/执行：QEMU discovered=222 total=214；gem5 discovered=222 total=214
- QEMU 计数：{'pass': 214, 'fail': 0, 'known-fail': 0, 'blocked': 0, 'excluded': 8, 'total': 214, 'pass_recorded': 211, 'pass_exit_only': 3}
- gem5 计数：{'pass': 115, 'fail': 5, 'known-fail': 0, 'blocked': 94, 'excluded': 8, 'total': 214, 'pass_recorded': 112, 'pass_exit_only': 3}（SE 超时 600s/例）
- 交叉：both_pass=115 gem5_blocked（不含 timeout）=2 (QEMU 通过 2) gem5_timeout=92 (QEMU 通过 92) gem5_blocked_all=94 gem5_only_fail=5 qemu_only_fail=0 both_non_pass=0

### embench

- 发现/执行：QEMU discovered=19 total=38；gem5 discovered=19 total=38
- QEMU 计数：{'pass': 38, 'fail': 0, 'known-fail': 0, 'excluded': 0, 'blocked': 0}
- gem5 计数：{'pass': 38, 'fail': 0, 'known-fail': 0, 'excluded': 0, 'blocked': 0}（SE 超时 300s/例）
- 交叉：both_pass=38 gem5_blocked（不含 timeout）=0 (QEMU 通过 0) gem5_timeout=0 (QEMU 通过 0) gem5_blocked_all=0 gem5_only_fail=0 qemu_only_fail=0 both_non_pass=0

## gem5_only_fail（QEMU 通过、gem5 未通过）

- libc-test:functional/popen gem5=fail exit=1 — guest exit 1, expected 0: libc-test/src/functional/popen.c:32: f = popen("echo hello", "r") failed (errno = 8)
- libc-test:functional/spawn gem5=fail exit=1 — guest exit 1, expected 0: libc-test/src/functional/spawn.c:35: posix_spawnp(&pid, "echo", &fa, 0, (char *[]){"echo","hello",0}, 0) failed, got 8 want 0
- libc-test:functional/vfork gem5=fail exit=1 — guest exit 1, expected 0: libc-test/src/functional/vfork.c:44: execl failed: Exec format error
- libc-test:regression/execle-env gem5=fail exit=1 — guest exit 1, expected 0: libc-test/src/regression/execle-env.c:16: execle failed: Exec format error
- llvm-ts:MultiSource/Benchmarks/FreeBench/analyzer gem5=fail exit=0 — oracle mismatch (MultiSource/Benchmarks/FreeBench/analyzer/analyzer.reference_output): output differs (462 B vs 462 B, sha256 b4ca213549650bd8); first output: Num_epochs: 576
- llvm-ts:MultiSource/Benchmarks/FreeBench/distray gem5=fail exit=0 — oracle mismatch (MultiSource/Benchmarks/FreeBench/distray/distray.reference_output): md5(output+exit)=6f7dd8639d67c7c26cfd9f2b0c8187a1 expected 78a70b660bcdf47a8dc16ba0db75ba2a, exit 0 (the exit code is inside the hashed document)
- llvm-ts:MultiSource/Benchmarks/FreeBench/pifft gem5=fail exit=0 — oracle mismatch (MultiSource/Benchmarks/FreeBench/pifft/pifft.reference_output): output differs (82339 B vs 82339 B, sha256 11fd9c6772d49f37); first output: PI calculation to estimate the FFT benchmarks
- llvm-ts:MultiSource/Benchmarks/Prolangs-C/bison gem5=fail exit=0 — oracle mismatch (MultiSource/Benchmarks/Prolangs-C/bison/mybison.reference_output): output differs (85401 B vs 85401 B, sha256 ffbffd589d4ecad5); first output: /* A Bison parser, made from parse.y.in */
- llvm-ts:MultiSource/Benchmarks/Prolangs-C/unix-smail gem5=fail exit=69 — oracle mismatch (MultiSource/Benchmarks/Prolangs-C/unix-smail/unix-smail.reference_output): output differs (43 B vs 42 B, sha256 590dfe1569b3f892); exit 69 != 0; first output: resolve 'ALL' = 'ALL' @ '' (LOCAL)

## qemu_only_fail（gem5 通过、QEMU 未通过；ADR-0048 D5 单列）

（无）

## gem5 SE 缺口分类（能力缺口；timeout 不在本表）

| 能力 | blocked 案例数 | 代表案例 | 所需改动面 |
| --- | --- | --- | --- |
| SysV IPC | 3 | libc-test:functional/ipc_msg、libc-test:functional/ipc_sem、libc-test:functional/ipc_shm | syscall: SysV IPC (msg/sem/shm) + guest kernel objects |
| other | 2 | libc-test:functional/sem_open、libc-test:regression/sem_close-unmap | syscall: number not in the capability buckets -- inspect evidence |
| simulator/loader | 2 | libc-test:regression/flockfile-list、llvm-ts:MultiSource/Applications/lemon | simulator: SE loader/exit modelling |
| file I/O | 1 | llvm-ts:MultiSource/Applications/ClamAV | syscall: file syscalls + guest fd table |

## 超时（预算到期；非能力缺口）

- llvm-ts：92 例，预算 600s/例 — MultiSource/Applications/JM/lencod、MultiSource/Applications/SIBsim4、MultiSource/Applications/SPASS、MultiSource/Applications/aha、MultiSource/Applications/lua、MultiSource/Applications/obsequi、MultiSource/Applications/oggenc、MultiSource/Applications/sqlite3、MultiSource/Applications/viterbi、MultiSource/Benchmarks/ASCI_Purple/SMG2000、MultiSource/Benchmarks/ASC_Sequoia/AMGmk、MultiSource/Benchmarks/ASC_Sequoia/CrystalMk、MultiSource/Benchmarks/ASC_Sequoia/IRSmk、MultiSource/Benchmarks/BitBench/drop3、MultiSource/Benchmarks/BitBench/five11、MultiSource/Benchmarks/BitBench/uudecode、MultiSource/Benchmarks/DOE-ProxyApps-C/CoMD、MultiSource/Benchmarks/DOE-ProxyApps-C/Pathfinder、MultiSource/Benchmarks/DOE-ProxyApps-C/RSBench、MultiSource/Benchmarks/DOE-ProxyApps-C/SimpleMOC、MultiSource/Benchmarks/DOE-ProxyApps-C/XSBench、MultiSource/Benchmarks/DOE-ProxyApps-C/miniAMR、MultiSource/Benchmarks/DOE-ProxyApps-C/miniGMG、MultiSource/Benchmarks/Fhourstones、MultiSource/Benchmarks/Fhourstones-3.1、MultiSource/Benchmarks/FreeBench/fourinarow、MultiSource/Benchmarks/FreeBench/mason、MultiSource/Benchmarks/FreeBench/neural、MultiSource/Benchmarks/FreeBench/pcompress2、MultiSource/Benchmarks/MallocBench/cfrac、MultiSource/Benchmarks/McCat/01-qbsort、MultiSource/Benchmarks/McCat/12-IOtest、MultiSource/Benchmarks/MiBench/automotive-basicmath、MultiSource/Benchmarks/MiBench/consumer-lame、MultiSource/Benchmarks/MiBench/consumer-typeset、MultiSource/Benchmarks/MiBench/network-patricia、MultiSource/Benchmarks/MiBench/telecomm-CRC32、MultiSource/Benchmarks/MiBench/telecomm-adpcm、MultiSource/Benchmarks/NPB-serial/is、MultiSource/Benchmarks/Olden/bisort、MultiSource/Benchmarks/Ptrdist/bc、MultiSource/Benchmarks/Ptrdist/ft、MultiSource/Benchmarks/Ptrdist/ks、MultiSource/Benchmarks/Ptrdist/yacr2、MultiSource/Benchmarks/Rodinia/backprop、MultiSource/Benchmarks/Rodinia/hotspot、MultiSource/Benchmarks/Rodinia/pathfinder、MultiSource/Benchmarks/Rodinia/srad、MultiSource/Benchmarks/SciMark2-C、MultiSource/Benchmarks/Trimaran/enc-3des、MultiSource/Benchmarks/Trimaran/enc-md5、MultiSource/Benchmarks/Trimaran/netbench-url、MultiSource/Benchmarks/VersaBench/beamformer、MultiSource/Benchmarks/VersaBench/dbms、MultiSource/Benchmarks/llubenchmark、MultiSource/Benchmarks/mafft、MultiSource/Benchmarks/nbench、SingleSource/Benchmarks/BenchmarkGame/Large/fasta、SingleSource/Benchmarks/BenchmarkGame/fannkuch、SingleSource/Benchmarks/BenchmarkGame/n-body、SingleSource/Benchmarks/BenchmarkGame/nsieve-bits、SingleSource/Benchmarks/BenchmarkGame/partialsums、SingleSource/Benchmarks/BenchmarkGame/puzzle、SingleSource/Benchmarks/BenchmarkGame/recursive、SingleSource/Benchmarks/BenchmarkGame/spectral-norm、SingleSource/Benchmarks/CoyoteBench/huffbench、SingleSource/Benchmarks/Linpack/linpack-pc、SingleSource/Benchmarks/McGill/chomp、SingleSource/Benchmarks/McGill/queens、SingleSource/Benchmarks/Misc/ReedSolomon、SingleSource/Benchmarks/Misc/dt、SingleSource/Benchmarks/Misc/evalloop、SingleSource/Benchmarks/Misc/fbench、SingleSource/Benchmarks/Misc/ffbench、SingleSource/Benchmarks/Misc/fp-convert、SingleSource/Benchmarks/Misc/himenobmtxpa、SingleSource/Benchmarks/Misc/mandel-2、SingleSource/Benchmarks/Misc/oourafft、SingleSource/Benchmarks/Misc/perlin、SingleSource/Benchmarks/Misc/revertBits、SingleSource/Benchmarks/Misc/richards_benchmark、SingleSource/Benchmarks/Misc/salsa20、SingleSource/Benchmarks/Shootout/ary3、SingleSource/Benchmarks/Shootout/fib2、SingleSource/Benchmarks/Shootout/hash、SingleSource/Benchmarks/Shootout/lists、SingleSource/Benchmarks/Shootout/matrix、SingleSource/Benchmarks/Shootout/methcall、SingleSource/Benchmarks/Shootout/sieve、SingleSource/Benchmarks/Shootout/strcat、SingleSource/Benchmarks/Stanford/FloatMM、SingleSource/Benchmarks/Stanford/Puzzle
- libc-test：5 例，预算 300s/例 — functional/clocale_mbfuncs、functional/crypt、functional/sscanf_long、functional/string_memset、regression/raise-race

口径：超时说明「预算不足 / SE 引擎慢」，不是能力缺口，也不是判决；给更大 `--gem5-timeout` 复测后才能判定（见下节重测与各任务结论）。

## 超预算重测（原超时案例在更长预算下重跑）

- libc-test：重测 5 例（预算 1200s）→ 通过 3、仍 blocked 2、其他 0
  - 通过：functional/crypt, functional/sscanf_long, functional/string_memset
  - 仍 blocked：functional/clocale_mbfuncs, regression/raise-race
- llvm-ts：重测 92 例（预算 1200s）→ 通过 20、仍 blocked 70、其他 2
  - 通过：MultiSource/Applications/oggenc, MultiSource/Benchmarks/ASCI_Purple/SMG2000, MultiSource/Benchmarks/ASC_Sequoia/IRSmk, MultiSource/Benchmarks/BitBench/five11, MultiSource/Benchmarks/BitBench/uudecode, MultiSource/Benchmarks/McCat/01-qbsort, MultiSource/Benchmarks/MiBench/consumer-typeset, MultiSource/Benchmarks/MiBench/telecomm-CRC32, MultiSource/Benchmarks/MiBench/telecomm-adpcm, MultiSource/Benchmarks/NPB-serial/is, MultiSource/Benchmarks/Trimaran/enc-3des, MultiSource/Benchmarks/Trimaran/enc-md5, SingleSource/Benchmarks/McGill/chomp, SingleSource/Benchmarks/McGill/queens, SingleSource/Benchmarks/Misc/oourafft, SingleSource/Benchmarks/Misc/perlin, SingleSource/Benchmarks/Misc/richards_benchmark, SingleSource/Benchmarks/Misc/salsa20, SingleSource/Benchmarks/Shootout/strcat, SingleSource/Benchmarks/Stanford/Puzzle
  - 仍 blocked：MultiSource/Applications/JM/lencod, MultiSource/Applications/SIBsim4, MultiSource/Applications/SPASS, MultiSource/Applications/aha, MultiSource/Applications/lua, MultiSource/Applications/obsequi, MultiSource/Applications/sqlite3, MultiSource/Applications/viterbi, MultiSource/Benchmarks/ASC_Sequoia/AMGmk, MultiSource/Benchmarks/ASC_Sequoia/CrystalMk, MultiSource/Benchmarks/BitBench/drop3, MultiSource/Benchmarks/DOE-ProxyApps-C/CoMD, MultiSource/Benchmarks/DOE-ProxyApps-C/Pathfinder, MultiSource/Benchmarks/DOE-ProxyApps-C/RSBench, MultiSource/Benchmarks/DOE-ProxyApps-C/SimpleMOC, MultiSource/Benchmarks/DOE-ProxyApps-C/XSBench, MultiSource/Benchmarks/DOE-ProxyApps-C/miniAMR, MultiSource/Benchmarks/DOE-ProxyApps-C/miniGMG, MultiSource/Benchmarks/Fhourstones, MultiSource/Benchmarks/Fhourstones-3.1, MultiSource/Benchmarks/FreeBench/fourinarow, MultiSource/Benchmarks/FreeBench/pcompress2, MultiSource/Benchmarks/MallocBench/cfrac, MultiSource/Benchmarks/McCat/12-IOtest, MultiSource/Benchmarks/MiBench/automotive-basicmath, MultiSource/Benchmarks/MiBench/consumer-lame, MultiSource/Benchmarks/MiBench/network-patricia, MultiSource/Benchmarks/Olden/bisort, MultiSource/Benchmarks/Ptrdist/bc, MultiSource/Benchmarks/Ptrdist/ft, MultiSource/Benchmarks/Ptrdist/ks, MultiSource/Benchmarks/Ptrdist/yacr2, MultiSource/Benchmarks/Rodinia/backprop, MultiSource/Benchmarks/Rodinia/hotspot, MultiSource/Benchmarks/Rodinia/pathfinder, MultiSource/Benchmarks/Rodinia/srad, MultiSource/Benchmarks/SciMark2-C, MultiSource/Benchmarks/Trimaran/netbench-url, MultiSource/Benchmarks/VersaBench/beamformer, MultiSource/Benchmarks/VersaBench/dbms, MultiSource/Benchmarks/llubenchmark, MultiSource/Benchmarks/mafft, MultiSource/Benchmarks/nbench, SingleSource/Benchmarks/BenchmarkGame/Large/fasta, SingleSource/Benchmarks/BenchmarkGame/fannkuch, SingleSource/Benchmarks/BenchmarkGame/n-body, SingleSource/Benchmarks/BenchmarkGame/nsieve-bits, SingleSource/Benchmarks/BenchmarkGame/partialsums, SingleSource/Benchmarks/BenchmarkGame/puzzle, SingleSource/Benchmarks/BenchmarkGame/recursive, SingleSource/Benchmarks/BenchmarkGame/spectral-norm, SingleSource/Benchmarks/CoyoteBench/huffbench, SingleSource/Benchmarks/Linpack/linpack-pc, SingleSource/Benchmarks/Misc/ReedSolomon, SingleSource/Benchmarks/Misc/dt, SingleSource/Benchmarks/Misc/evalloop, SingleSource/Benchmarks/Misc/fbench, SingleSource/Benchmarks/Misc/ffbench, SingleSource/Benchmarks/Misc/fp-convert, SingleSource/Benchmarks/Misc/himenobmtxpa, SingleSource/Benchmarks/Misc/mandel-2, SingleSource/Benchmarks/Misc/revertBits, SingleSource/Benchmarks/Shootout/ary3, SingleSource/Benchmarks/Shootout/fib2, SingleSource/Benchmarks/Shootout/hash, SingleSource/Benchmarks/Shootout/lists, SingleSource/Benchmarks/Shootout/matrix, SingleSource/Benchmarks/Shootout/methcall, SingleSource/Benchmarks/Shootout/sieve, SingleSource/Benchmarks/Stanford/FloatMM
  - 非通过 MultiSource/Benchmarks/FreeBench/mason（fail）：oracle mismatch (MultiSource/Benchmarks/FreeBench/mason/mason.reference_output): output differs (233 B vs 233 B, sha256 0719653c859e3ea5); first output: Trying 2
  - 非通过 MultiSource/Benchmarks/FreeBench/neural（fail）：oracle mismatch (MultiSource/Benchmarks/FreeBench/neural/neural.reference_output): output differs (358 B vs 358 B, sha256 03d6202ad104bc54); first output: Matrix size is 20x28

## 引擎与快照

- gem5 组件锁定 commit：`c8222cc67a399bfc01e8658dd14b30d5bfd634f9`
- 分支补丁集：`components/gem5/series` 97 条
- 快照引擎：gem5 `25.1.0.1`，编译于 `Nov  9 2026 02:32:59`（banner 取自运行期 sim 日志）
- gem5.opt sha256：不可复原（共享构建树在快照后被并行任务重建覆盖）；同一 `commit`+`series` 可由 `make build-gem5` 复现

## 复跑

```
JOBS=32 python3 tools/testcases/tset/gem5-se-baseline/run_gem5_se_baseline.py \
    --work-dir <runtime dir> --json-out <runtime dir>/gem5-se-baseline.json
```

默认预算：libc-test 300s, llvm-ts 600s, embench 300s（`timeout` 单列，不计能力缺口）。`--gem5-timeout` 全局覆盖，`--gem5-timeout-by-suite libc-test=300,llvm-ts=900` 单套件覆盖。

试点（少量案例）：`--suites <suite> --driver-arg '<驱动自身的选择参数>'`（如 libc-test 的 `--filter`、llvm-ts 的 `--only`）；参数原样转发给所选套件的驱动，全量运行不要带。

驱动层单套件：给三个 tset 驱动加 `--engine qemu|gem5-se`；gem5 SE 走 `configs/dadao/se.py --binary <elf>`，只接受静态 `ET_EXEC`。
