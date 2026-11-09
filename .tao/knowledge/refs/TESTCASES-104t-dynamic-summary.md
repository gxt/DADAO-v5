# TESTCASES-104t：三套件 dynamic 汇总（gem5 SE vs QEMU）

> 数据来源与口径（2026-11-09）：
> - **libc-test**：redirect 修复后的全量（同一主控机，gem5 + QEMU 两侧，340 例）。修复前该轮有 11 例 `/dev`、`/tmp` 假失败（`gem5_only_fail=15`），修复后为 `0`。
> - **llvm-ts + embench**：主控机全量（214 + 38 例）。
> - **server208 的 QEMU-only 对照不并入**：其 qemu/musl 构建与主控机不同（md5/源 HEAD 均不同），数据不可比；其中的 `regression/malloc-brk-fail` fail 已隔离到该构建差异（见文末归因）。
> - 全部计数由 `run_gem5_se_baseline.py --aggregate-only --link-mode dynamic` 从 6 份驱动 JSON 现场统计；timeout 单列，不计能力缺口。

# GEM5-021t gem5 SE tset 基线（dynamic）

生成：2026-11-09T03:16:31Z（计数全部由本脚本从两份驱动 JSON 现场统计）

> **快照说明**：数字为运行时刻的快照（见 generated_utc）；随 SE 能力落地，同一命令会得到不同计数。timeout 为预算到期，单列，不计入能力缺口。

范围：dynamic link mode (ET_EXEC + PT_INTERP through the guest root; ADR-0048 D4 static first, dynamic fills in the same cases)

## 总览

- QEMU user 通过：590
- gem5 SE 通过：451
- 两侧都通过（both_pass）：451
- gem5 SE blocked（能力缺口，**不含 timeout**）：43（其中 QEMU 通过 = 42）
- gem5 SE timeout（预算到期，**非能力缺口**、非判决）：93（其中 QEMU 通过 = 93；blocked_all 含 timeout = 136）
- gem5_only_fail（QEMU 通过、gem5 非通过且未 blocked）：4
- qemu_only_fail（gem5 通过、QEMU 未通过，ADR-0048 D5 需定位）：0

## 分套件

### libc-test

- 发现/执行：QEMU discovered=367 total=340；gem5 discovered=367 total=340
- QEMU 计数：{'pass': 338, 'fail': 0, 'known-fail': 2, 'blocked': 0}
- gem5 计数：{'pass': 301, 'fail': 0, 'known-fail': 1, 'blocked': 38}（SE 超时 300s/例）
- 交叉：both_pass=301 gem5_blocked（不含 timeout）=34 (QEMU 通过 33) gem5_timeout=4 (QEMU 通过 4) gem5_blocked_all=38 gem5_only_fail=0 qemu_only_fail=0 both_non_pass=1

### llvm-ts

- 发现/执行：QEMU discovered=222 total=214；gem5 discovered=222 total=214
- QEMU 计数：{'pass': 214, 'fail': 0, 'known-fail': 0, 'blocked': 0, 'excluded': 8, 'total': 214, 'pass_recorded': 211, 'pass_exit_only': 3}
- gem5 计数：{'pass': 112, 'fail': 4, 'known-fail': 0, 'blocked': 98, 'excluded': 8, 'total': 214, 'pass_recorded': 109, 'pass_exit_only': 3}（SE 超时 600s/例）
- 交叉：both_pass=112 gem5_blocked（不含 timeout）=9 (QEMU 通过 9) gem5_timeout=89 (QEMU 通过 89) gem5_blocked_all=98 gem5_only_fail=4 qemu_only_fail=0 both_non_pass=0

### embench

- 发现/执行：QEMU discovered=19 total=38；gem5 discovered=19 total=38
- QEMU 计数：{'pass': 38, 'fail': 0, 'known-fail': 0, 'excluded': 0, 'blocked': 0}
- gem5 计数：{'pass': 38, 'fail': 0, 'known-fail': 0, 'excluded': 0, 'blocked': 0}（SE 超时 300s/例）
- 交叉：both_pass=38 gem5_blocked（不含 timeout）=0 (QEMU 通过 0) gem5_timeout=0 (QEMU 通过 0) gem5_blocked_all=0 gem5_only_fail=0 qemu_only_fail=0 both_non_pass=0

## gem5_only_fail（QEMU 通过、gem5 未通过）

- llvm-ts:MultiSource/Benchmarks/FreeBench/analyzer gem5=fail exit=0 — oracle mismatch (MultiSource/Benchmarks/FreeBench/analyzer/analyzer.reference_output): output differs (462 B vs 462 B, sha256 b4ca213549650bd8); first output: Num_epochs: 576
- llvm-ts:MultiSource/Benchmarks/FreeBench/distray gem5=fail exit=0 — oracle mismatch (MultiSource/Benchmarks/FreeBench/distray/distray.reference_output): md5(output+exit)=6f7dd8639d67c7c26cfd9f2b0c8187a1 expected 78a70b660bcdf47a8dc16ba0db75ba2a, exit 0 (the exit code is inside the hashed document)
- llvm-ts:MultiSource/Benchmarks/FreeBench/pifft gem5=fail exit=0 — oracle mismatch (MultiSource/Benchmarks/FreeBench/pifft/pifft.reference_output): output differs (82339 B vs 82339 B, sha256 11fd9c6772d49f37); first output: PI calculation to estimate the FFT benchmarks
- llvm-ts:MultiSource/Benchmarks/Prolangs-C/bison gem5=fail exit=0 — oracle mismatch (MultiSource/Benchmarks/Prolangs-C/bison/mybison.reference_output): output differs (85401 B vs 85401 B, sha256 ffbffd589d4ecad5); first output: /* A Bison parser, made from parse.y.in */

## qemu_only_fail（gem5 通过、QEMU 未通过；ADR-0048 D5 单列）

（无）

## gem5 SE 缺口分类（能力缺口；timeout 不在本表）

| 能力 | blocked 案例数 | 代表案例 | 所需改动面 |
| --- | --- | --- | --- |
| other | 25 | libc-test:functional/pthread_cancel、libc-test:functional/pthread_cancel-points、libc-test:functional/pthread_cond、libc-test:functional/pthread_mutex、libc-test:functional/pthread_mutex_pi | syscall: number not in the capability buckets -- inspect evidence |
| simulator/loader | 13 | libc-test:functional/popen、libc-test:functional/spawn、libc-test:functional/vfork、libc-test:regression/execle-env、libc-test:regression/flockfile-list | simulator: SE loader/exit modelling |
| SysV IPC | 3 | libc-test:functional/ipc_msg、libc-test:functional/ipc_sem、libc-test:functional/ipc_shm | syscall: SysV IPC (msg/sem/shm) + guest kernel objects |
| dynamic loader (ldso) | 1 | libc-test:functional/tls_align | loader: ldso $ORIGIN needs /proc/self/exe, and the SE ls/search path must reach DT_NEEDED objects |
| file I/O | 1 | llvm-ts:MultiSource/Applications/ClamAV | syscall: file syscalls + guest fd table |

## 超时（预算到期；非能力缺口）

- llvm-ts：89 例，预算 600s/例 — MultiSource/Applications/JM/lencod、MultiSource/Applications/SIBsim4、MultiSource/Applications/SPASS、MultiSource/Applications/aha、MultiSource/Applications/lua、MultiSource/Applications/oggenc、MultiSource/Applications/viterbi、MultiSource/Benchmarks/ASCI_Purple/SMG2000、MultiSource/Benchmarks/ASC_Sequoia/AMGmk、MultiSource/Benchmarks/ASC_Sequoia/CrystalMk、MultiSource/Benchmarks/ASC_Sequoia/IRSmk、MultiSource/Benchmarks/BitBench/drop3、MultiSource/Benchmarks/BitBench/five11、MultiSource/Benchmarks/BitBench/uudecode、MultiSource/Benchmarks/DOE-ProxyApps-C/CoMD、MultiSource/Benchmarks/DOE-ProxyApps-C/Pathfinder、MultiSource/Benchmarks/DOE-ProxyApps-C/RSBench、MultiSource/Benchmarks/DOE-ProxyApps-C/SimpleMOC、MultiSource/Benchmarks/DOE-ProxyApps-C/XSBench、MultiSource/Benchmarks/DOE-ProxyApps-C/miniAMR、MultiSource/Benchmarks/DOE-ProxyApps-C/miniGMG、MultiSource/Benchmarks/Fhourstones、MultiSource/Benchmarks/Fhourstones-3.1、MultiSource/Benchmarks/FreeBench/fourinarow、MultiSource/Benchmarks/FreeBench/mason、MultiSource/Benchmarks/FreeBench/neural、MultiSource/Benchmarks/FreeBench/pcompress2、MultiSource/Benchmarks/MallocBench/cfrac、MultiSource/Benchmarks/McCat/01-qbsort、MultiSource/Benchmarks/McCat/08-main、MultiSource/Benchmarks/McCat/12-IOtest、MultiSource/Benchmarks/MiBench/automotive-basicmath、MultiSource/Benchmarks/MiBench/consumer-lame、MultiSource/Benchmarks/MiBench/consumer-typeset、MultiSource/Benchmarks/MiBench/network-patricia、MultiSource/Benchmarks/MiBench/telecomm-CRC32、MultiSource/Benchmarks/MiBench/telecomm-adpcm、MultiSource/Benchmarks/NPB-serial/is、MultiSource/Benchmarks/Olden/bisort、MultiSource/Benchmarks/Ptrdist/ft、MultiSource/Benchmarks/Ptrdist/ks、MultiSource/Benchmarks/Ptrdist/yacr2、MultiSource/Benchmarks/Rodinia/backprop、MultiSource/Benchmarks/Rodinia/hotspot、MultiSource/Benchmarks/Rodinia/pathfinder、MultiSource/Benchmarks/Rodinia/srad、MultiSource/Benchmarks/SciMark2-C、MultiSource/Benchmarks/Trimaran/enc-3des、MultiSource/Benchmarks/Trimaran/enc-md5、MultiSource/Benchmarks/Trimaran/netbench-url、MultiSource/Benchmarks/VersaBench/beamformer、MultiSource/Benchmarks/VersaBench/dbms、MultiSource/Benchmarks/llubenchmark、MultiSource/Benchmarks/nbench、SingleSource/Benchmarks/BenchmarkGame/Large/fasta、SingleSource/Benchmarks/BenchmarkGame/fannkuch、SingleSource/Benchmarks/BenchmarkGame/n-body、SingleSource/Benchmarks/BenchmarkGame/nsieve-bits、SingleSource/Benchmarks/BenchmarkGame/partialsums、SingleSource/Benchmarks/BenchmarkGame/puzzle、SingleSource/Benchmarks/BenchmarkGame/recursive、SingleSource/Benchmarks/BenchmarkGame/spectral-norm、SingleSource/Benchmarks/CoyoteBench/huffbench、SingleSource/Benchmarks/Linpack/linpack-pc、SingleSource/Benchmarks/McGill/chomp、SingleSource/Benchmarks/McGill/queens、SingleSource/Benchmarks/Misc/ReedSolomon、SingleSource/Benchmarks/Misc/dt、SingleSource/Benchmarks/Misc/evalloop、SingleSource/Benchmarks/Misc/fbench、SingleSource/Benchmarks/Misc/ffbench、SingleSource/Benchmarks/Misc/fp-convert、SingleSource/Benchmarks/Misc/himenobmtxpa、SingleSource/Benchmarks/Misc/mandel-2、SingleSource/Benchmarks/Misc/oourafft、SingleSource/Benchmarks/Misc/perlin、SingleSource/Benchmarks/Misc/revertBits、SingleSource/Benchmarks/Misc/richards_benchmark、SingleSource/Benchmarks/Misc/salsa20、SingleSource/Benchmarks/Shootout/ary3、SingleSource/Benchmarks/Shootout/fib2、SingleSource/Benchmarks/Shootout/hash、SingleSource/Benchmarks/Shootout/lists、SingleSource/Benchmarks/Shootout/matrix、SingleSource/Benchmarks/Shootout/methcall、SingleSource/Benchmarks/Shootout/sieve、SingleSource/Benchmarks/Shootout/strcat、SingleSource/Benchmarks/Stanford/FloatMM、SingleSource/Benchmarks/Stanford/Puzzle
- libc-test：4 例，预算 300s/例 — functional/clocale_mbfuncs、functional/crypt、functional/sscanf_long、functional/string_memset

口径：超时说明「预算不足 / SE 引擎慢」，不是能力缺口，也不是判决；给更大 `--gem5-timeout` 复测后才能判定（见下节重测与各任务结论）。

## 超预算重测（原超时案例在更长预算下重跑）

（未重测）

## 引擎与快照

- gem5 组件锁定 commit：`c8222cc67a399bfc01e8658dd14b30d5bfd634f9`
- 分支补丁集：`components/gem5/series` 97 条
- 快照引擎：gem5 `25.1.0.1`，编译于 `Nov  9 2026 02:32:59`（banner 取自运行期 sim 日志）
- gem5.opt sha256：不可复原（共享构建树在快照后被并行任务重建覆盖）；同一 `commit`+`series` 可由 `make build-gem5` 复现

## 复跑

```
JOBS=32 python3 tools/testcases/tset/gem5-se-baseline/run_gem5_se_baseline.py \
    --link-mode dynamic --work-dir <runtime dir> \
    --json-out <runtime dir>/gem5-se-baseline.json
```

默认预算：libc-test 300s, llvm-ts 600s, embench 300s（`timeout` 单列，不计能力缺口）。`--gem5-timeout` 全局覆盖，`--gem5-timeout-by-suite libc-test=300,llvm-ts=900` 单套件覆盖。

试点（少量案例）：`--suites <suite> --driver-arg '<驱动自身的选择参数>'`（如 libc-test 的 `--filter`、llvm-ts 的 `--only`）；参数原样转发给所选套件的驱动，全量运行不要带。

驱动层单套件：给三个 tset 驱动加 `--engine qemu|gem5-se`；gem5 SE 走 `configs/dadao/se.py --binary <elf>`，接受静态 `ET_EXEC` 与动态 `ET_EXEC + PT_INTERP`（后者由驱动经 `--interp-dir`/`--redirect` 传入guest root）；`ET_DYN` 主程序仍为 BLOCKED。

## 归因（人工核对，2026-11-09）

4 例 `gem5_only_fail` 全部是 **ISS-357**：SE 驱动层把 fd1/fd2 分开捕获、再按 `stdout+stderr` 串接，丢失程序真实的写出顺序；而参考是 RunSafely 的 `2>&1` 交错流 + `exit N\n` 尾。逐例用该实例的 `guest.stdout`/`guest.stderr` 与参考做字节比对：

- `FreeBench/analyzer`、`FreeBench/pifft`：`stderr + stdout + "exit 0\n"` 与参考**逐字节相等**（sha256 `d6f203b3…`、`4e999ac3…`，两侧同值）。
- `FreeBench/distray`：参考是 md5 形式；`md5(stderr + stdout + "exit 0\n") = 78a70b660bcdf47a8dc16ba0db75ba2a`，与参考**完全相同**（驱动侧按 `stdout+stderr` 得到 `6f7dd863…`）。
- `Prolangs-C/bison`：参考去掉唯一一行 stderr（`parse.y.in contains 1 shift/reduce conflict.`，位于参考第 1092 行）后，与 `stdout` **逐字节相等**（85349 B，sha256 `3c3b6bef…`）；stderr 在输出流**中段**，任何 `stdout`/`stderr` 串接顺序都无法匹配 —— 仍属写序丢失（ISS-357），不是 FP、未初始化或参考含路径/时间戳。
- 结论：**无新增缺陷**，不为 `distray`/`bison` 立新 issue。ISS-357 的修复必须保留 fd1/fd2 的**写出顺序**（不能只交换两侧）；修复前这 4 例按 `fail` 记录、不按能力缺口计。

### `regression/malloc-brk-fail` 的 QEMU fail（仅 server208 对照数据）

- 该 fail **只出现在 server208 的 QEMU-only 对照**（`malloc(10000) succeeded after memory is filled`）；主控机 QEMU 全量两次独立运行均 **pass**，本汇总中即为 pass。
- 隔离实验：把 208 构建的用例 ELF + 208 的 `libc.so` 拿到主控机、用主控机 qemu 运行 ⇒ **复现 rc=1 同一报错**；主控机构建的 ELF + libc.so 用主控机与 208 两个 qemu 二进制运行 ⇒ **均 pass**。⇒ 根因是 **208 的 musl/libc.so 构建不同**（ldso 捐赠堆的 gap 布局不同，`TESTCASES-100t` 的 6 槽 priming 未 drain 到该布局），不是 QEMU rlimit。
- 与 ISS-343 的关系：台账原文已写明「该缺口不是 libc-test malloc-brk-fail dynamic 的直接原因（该次 malloc 无系统调用）」；且 208 的 qemu（md5 `415c…`）与 musl 源 HEAD（`0fbef28`）均与主控机（`77ec…`、`24c1fd2`）不同，**分片前提「同二进制」不成立**。
- 处置：**不登记 known-fail**（那会把跨机构建不一致伪装成能力缺口，并掩盖 TESTCASES-100t 移植补丁的构建敏感性）；208 数据不并入本报告。建议 208 执行 `make sync-node-repo` + `make install-host`/`make build-musl`，校验 qemu/libc.so md5 与主控机一致后重跑。
