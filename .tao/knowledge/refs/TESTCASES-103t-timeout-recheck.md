# TESTCASES-103t 超时案例 1200 s 复测结论（GEM5-021t 基线快照）

> 配套快照：`GEM5-021t-baseline-summary.{json,md}`（其 `timeout_recheck` 字段即本文件的数据源）。
> 两轮运行：第一轮默认预算（libc-test 300 s / llvm-ts 600 s / embench 300 s）；第二轮把第一轮的 **timeout 用例**按套件在 1200 s 下全量重跑。
> 计数由 `run_gem5_se_baseline.py` 从驱动 JSON 现场统计，本文件只写名单与结论。

## 总览

- 第一轮：`gem5_pass=474`、`blocked=8`（真实能力缺口）、`timeout=97`、`gem5_only_fail=9`。
- 1200 s 全量：`gem5_pass=497`、`blocked=8`、`timeout=72`、`gem5_only_fail=11`。
- 原 97 例 timeout 的去向：**23 转 PASS、72 仍 timeout、2 转 fail**（23+72+2=97）。
  即 `gem5_pass` 的 +23 全部来自转 PASS；真实 `blocked` 8 例两轮不变（与预算无关）。

## 一、转 PASS（23 例）

### libc-test（3）

- `functional/crypt`
- `functional/sscanf_long`
- `functional/string_memset`

### llvm-ts（20）

- `MultiSource/Applications/oggenc`
- `MultiSource/Benchmarks/ASCI_Purple/SMG2000`
- `MultiSource/Benchmarks/ASC_Sequoia/IRSmk`
- `MultiSource/Benchmarks/BitBench/five11`
- `MultiSource/Benchmarks/BitBench/uudecode`
- `MultiSource/Benchmarks/McCat/01-qbsort`
- `MultiSource/Benchmarks/MiBench/consumer-typeset`
- `MultiSource/Benchmarks/MiBench/telecomm-CRC32`
- `MultiSource/Benchmarks/MiBench/telecomm-adpcm`
- `MultiSource/Benchmarks/NPB-serial/is`
- `MultiSource/Benchmarks/Trimaran/enc-3des`
- `MultiSource/Benchmarks/Trimaran/enc-md5`
- `SingleSource/Benchmarks/McGill/chomp`
- `SingleSource/Benchmarks/McGill/queens`
- `SingleSource/Benchmarks/Misc/oourafft`
- `SingleSource/Benchmarks/Misc/perlin`
- `SingleSource/Benchmarks/Misc/richards_benchmark`
- `SingleSource/Benchmarks/Misc/salsa20`
- `SingleSource/Benchmarks/Shootout/strcat`
- `SingleSource/Benchmarks/Stanford/Puzzle`

## 二、仍 timeout（72 例，1200 s 仍不足）

结论：纯计算量 / SE 引擎速度，**不是能力缺口**；继续留在 timeout 口径，不进 `blocked`。

### libc-test（2）

- `functional/clocale_mbfuncs`
- `regression/raise-race`

### llvm-ts（70）

- `MultiSource/Applications/JM/lencod`
- `MultiSource/Applications/SIBsim4`
- `MultiSource/Applications/SPASS`
- `MultiSource/Applications/aha`
- `MultiSource/Applications/lua`
- `MultiSource/Applications/obsequi`
- `MultiSource/Applications/sqlite3`
- `MultiSource/Applications/viterbi`
- `MultiSource/Benchmarks/ASC_Sequoia/AMGmk`
- `MultiSource/Benchmarks/ASC_Sequoia/CrystalMk`
- `MultiSource/Benchmarks/BitBench/drop3`
- `MultiSource/Benchmarks/DOE-ProxyApps-C/CoMD`
- `MultiSource/Benchmarks/DOE-ProxyApps-C/Pathfinder`
- `MultiSource/Benchmarks/DOE-ProxyApps-C/RSBench`
- `MultiSource/Benchmarks/DOE-ProxyApps-C/SimpleMOC`
- `MultiSource/Benchmarks/DOE-ProxyApps-C/XSBench`
- `MultiSource/Benchmarks/DOE-ProxyApps-C/miniAMR`
- `MultiSource/Benchmarks/DOE-ProxyApps-C/miniGMG`
- `MultiSource/Benchmarks/Fhourstones`
- `MultiSource/Benchmarks/Fhourstones-3.1`
- `MultiSource/Benchmarks/FreeBench/fourinarow`
- `MultiSource/Benchmarks/FreeBench/pcompress2`
- `MultiSource/Benchmarks/MallocBench/cfrac`
- `MultiSource/Benchmarks/McCat/12-IOtest`
- `MultiSource/Benchmarks/MiBench/automotive-basicmath`
- `MultiSource/Benchmarks/MiBench/consumer-lame`
- `MultiSource/Benchmarks/MiBench/network-patricia`
- `MultiSource/Benchmarks/Olden/bisort`
- `MultiSource/Benchmarks/Ptrdist/bc`
- `MultiSource/Benchmarks/Ptrdist/ft`
- `MultiSource/Benchmarks/Ptrdist/ks`
- `MultiSource/Benchmarks/Ptrdist/yacr2`
- `MultiSource/Benchmarks/Rodinia/backprop`
- `MultiSource/Benchmarks/Rodinia/hotspot`
- `MultiSource/Benchmarks/Rodinia/pathfinder`
- `MultiSource/Benchmarks/Rodinia/srad`
- `MultiSource/Benchmarks/SciMark2-C`
- `MultiSource/Benchmarks/Trimaran/netbench-url`
- `MultiSource/Benchmarks/VersaBench/beamformer`
- `MultiSource/Benchmarks/VersaBench/dbms`
- `MultiSource/Benchmarks/llubenchmark`
- `MultiSource/Benchmarks/mafft`
- `MultiSource/Benchmarks/nbench`
- `SingleSource/Benchmarks/BenchmarkGame/Large/fasta`
- `SingleSource/Benchmarks/BenchmarkGame/fannkuch`
- `SingleSource/Benchmarks/BenchmarkGame/n-body`
- `SingleSource/Benchmarks/BenchmarkGame/nsieve-bits`
- `SingleSource/Benchmarks/BenchmarkGame/partialsums`
- `SingleSource/Benchmarks/BenchmarkGame/puzzle`
- `SingleSource/Benchmarks/BenchmarkGame/recursive`
- `SingleSource/Benchmarks/BenchmarkGame/spectral-norm`
- `SingleSource/Benchmarks/CoyoteBench/huffbench`
- `SingleSource/Benchmarks/Linpack/linpack-pc`
- `SingleSource/Benchmarks/Misc/ReedSolomon`
- `SingleSource/Benchmarks/Misc/dt`
- `SingleSource/Benchmarks/Misc/evalloop`
- `SingleSource/Benchmarks/Misc/fbench`
- `SingleSource/Benchmarks/Misc/ffbench`
- `SingleSource/Benchmarks/Misc/fp-convert`
- `SingleSource/Benchmarks/Misc/himenobmtxpa`
- `SingleSource/Benchmarks/Misc/mandel-2`
- `SingleSource/Benchmarks/Misc/revertBits`
- `SingleSource/Benchmarks/Shootout/ary3`
- `SingleSource/Benchmarks/Shootout/fib2`
- `SingleSource/Benchmarks/Shootout/hash`
- `SingleSource/Benchmarks/Shootout/lists`
- `SingleSource/Benchmarks/Shootout/matrix`
- `SingleSource/Benchmarks/Shootout/methcall`
- `SingleSource/Benchmarks/Shootout/sieve`
- `SingleSource/Benchmarks/Stanford/FloatMM`

## 三、转 fail（2 例）：FreeBench mason / neural

两例均 `gem5_exit=0`，`oracle mismatch`，实际/参考文档长度相同（mason 233 B/233 B、neural 358 B/358 B）而内容不同；它们是 `gem5_only_fail` 9→11 的全部差值。

**根因（本轮实测，非推测）**：gem5 SE 路径把 guest 的 fd1/fd2 分开落盘，驱动按 `stdout + stderr + "exit N\n"` 拼成对比文档；这两例程序先把两行前导（`Compile date: today` / `Compiler switches: `）写到 **stderr**，其余写 stdout。上游参考用 `2>&1` 合并，前导在最前。用 `stderr + stdout + "exit 0\n"` 重组后与参考**逐字节相等**（233/233、358/358，sha256 与参考一致）；而 `stdout + stderr + exit` 的 sha256 正是驱动报告的 `0719653c…`（mason）/ `03d6202a…`（neural）。

因此：**不是 FP 数值差异**（任务分派时的「疑似 FP」初判已被本轮证据否定），也不是 guest 判决差异，而是 SE 输出捕获的 **stdout/stderr 顺序**问题（qemu 轮 `2>&1` 交错，gem5 SE 两路分开后串接）。影响面（reviewer 复核修正）：**至少 4 例**的 `stderr+stdout+"exit 0\n"` 与参考逐字节相等——`FreeBench/analyzer`、`pifft`、`mason`、`neural`（前两例本就在第一轮 9 个 fail 内）。注意**不可全局交换拼接顺序**：另有 1 例需要 `stdout+stderr` 才对，31 例 pass 走非逐字节比对。

修复方向：另立任务在 SE 驱动层保留 fd1/fd2 的写出顺序（或仅对参考含 stderr 前导的用例按序重组），不改用例与期望值；修复前这两例按「平台输出捕获顺序」记 fail，不计能力缺口。已登记 `ISS-357`。

## 四、结论

- `blocked` 8 例在两轮中稳定，`timeout` 97→72 的差全部是预算，口径分离成立。
- 主口径仍是第一轮默认预算（300/600 s）：`blocked=8`、`timeout=97`；1200 s 复测单列于 `timeout_recheck`，不改写主计数。
- 2 例 FreeBench fail 是输出捕获顺序缺陷（驱动/引擎层），不是能力缺口、不是 FP；登记 issue 跟踪。
