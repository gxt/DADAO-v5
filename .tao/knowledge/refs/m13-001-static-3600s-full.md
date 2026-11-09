# m13-testcases-001：static 长尾 72 例 gem5/qemu 运行时间比

生成：2026-11-09T19:07:04Z（数值全部由驱动 JSON 现场统计，无估算）

范围：static long-tail: the cases that still timed out at the GEM5-021t 1200 s recheck, re-run with the per-case budget below on gem5 SE and qemu-user; times measured by the tset drivers' own run_seconds

## 执行环境指纹

- 节点：`server207`；CPU：Intel(R) Xeon(R) CPU E7- 4820  @ 2.00GHz；nproc=64
- 并发：48（两引擎同值）；engines=qemu,gem5-se
- 预算：gem5 3600s / qemu 3600s（每例）
- gem5：`gem5.opt` md5=`53466b8206a56ab3a008f4cc7302a553` 版本：25.1.0.1（编译于 Nov  9 2026 18:45:54）
- qemu：`qemu-dadao` md5=`3c4660d295bf1f1da70f3d4c8185a5b4` 版本：qemu-dadao version 11.1.1 (v11.1.1-1-gcbf0e67)
- musl HEAD：`61bd50e54e1034c24e7af219fe9ff1ad56833671`（dirty=False）
- 统计时 loadavg：[10.91, 19.06, 21.48]

## 总览

- 选中案例：72（libc-test 2、llvm-ts 70）
- 两引擎都有测量：72/72；缺失测量条目：0
- 比值分布（两引擎都未截断，n=0）：min=None median=None P90=None max=None
- 截断（timeout）已单列、未计入分布：70 例

## 比值分布（按类别）

（无可比样本）

## 离群（超出中位数 1/3–3 倍）

（无）

## 逐例

| suite | case | qemu_s | gem5_s | ratio | gem5_klass | exit | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| libc-test | functional/clocale_mbfuncs | 0.0 | 3600.01 | None | blocked | None | gem5 截断; gap=time budget; ratio 未定义 |
| libc-test | regression/raise-race | 0.0 | 3600.01 | None | blocked | None | gem5 截断; gap=time budget; ratio 未定义 |
| llvm-ts | MultiSource/Applications/JM/lencod | 22.96 | 3600.01 | 156.795 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Applications/SIBsim4 | 34.39 | 3600.01 | 104.682 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Applications/SPASS | 15.66 | 3600.01 | 229.886 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Applications/aha | 105.68 | 3600.03 | 34.065 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Applications/lua | 956.14 | 3600.01 | 3.765 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Applications/obsequi | 92.28 | 3600.03 | 39.012 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Applications/sqlite3 | 12.19 | 3600.01 | 295.325 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Applications/viterbi | 10.29 | 3600.03 | 349.857 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/ASC_Sequoia/AMGmk | 43.93 | 3600.02 | 81.949 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/ASC_Sequoia/CrystalMk | 45.33 | 3600.02 | 79.418 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/BitBench/drop3 | 22.61 | 3600.07 | 159.225 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/DOE-ProxyApps-C/CoMD | 143.51 | 3600.01 | 25.085 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/DOE-ProxyApps-C/Pathfinder | 106.34 | 3600.01 | 33.854 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/DOE-ProxyApps-C/RSBench | 33.0 | 3600.01 | 109.091 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/DOE-ProxyApps-C/SimpleMOC | 240.57 | 3600.01 | 14.965 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/DOE-ProxyApps-C/XSBench | 252.84 | 3600.01 | 14.238 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/DOE-ProxyApps-C/miniAMR | 32.63 | 3600.04 | 110.329 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/DOE-ProxyApps-C/miniGMG | 96.9 | 3600.02 | 37.152 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Fhourstones | 49.0 | 3600.02 | 73.47 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Fhourstones-3.1 | 23.96 | 3600.09 | 150.254 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/FreeBench/fourinarow | 64.21 | 3600.01 | 56.066 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/FreeBench/pcompress2 | 13.35 | 3600.01 | 269.664 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/MallocBench/cfrac | 83.76 | 3600.01 | 42.98 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/McCat/12-IOtest | 36.66 | 3600.16 | 98.204 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/MiBench/automotive-basicmath | 46.57 | 3600.03 | 77.304 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/MiBench/consumer-lame | 28.98 | 3600.01 | 124.224 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/MiBench/network-patricia | 14.41 | 3600.07 | 249.831 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Olden/bisort | 17.88 | 3600.04 | 201.345 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Ptrdist/bc | 47.64 | 3600.02 | 75.567 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Ptrdist/ft | 25.85 | 3600.02 | 139.266 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Ptrdist/ks | 80.27 | 3600.02 | 44.849 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Ptrdist/yacr2 | 61.05 | 3600.02 | 58.968 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Rodinia/backprop | 29.55 | 3600.13 | 121.832 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Rodinia/hotspot | 45.36 | 3600.19 | 79.369 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Rodinia/pathfinder | 17.3 | 3600.04 | 208.095 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Rodinia/srad | 81.08 | 3600.04 | 44.401 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/SciMark2-C | 116.62 | 3600.01 | 30.87 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Trimaran/netbench-url | 9.73 | 3600.02 | 369.992 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/VersaBench/beamformer | 28.79 | 3600.04 | 125.045 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/VersaBench/dbms | 15.0 | 3600.01 | 240.001 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/llubenchmark | 25.07 | 3600.03 | 143.599 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/mafft | 1103.25 | 3600.03 | 3.263 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/nbench | 221.55 | 3600.02 | 16.249 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/BenchmarkGame/Large/fasta | 25.34 | 3600.08 | 142.071 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/BenchmarkGame/fannkuch | 71.2 | 3600.05 | 50.562 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/BenchmarkGame/n-body | 94.63 | 3600.03 | 38.043 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/BenchmarkGame/nsieve-bits | 52.75 | 3600.05 | 68.247 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/BenchmarkGame/partialsums | 60.47 | 3600.02 | 59.534 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/BenchmarkGame/puzzle | 47.52 | 3600.01 | 75.758 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/BenchmarkGame/recursive | 93.44 | 3600.01 | 38.528 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/BenchmarkGame/spectral-norm | 47.0 | 3600.02 | 76.596 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/CoyoteBench/huffbench | 30.8 | 3600.04 | 116.884 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Linpack/linpack-pc | 87.79 | 3600.02 | 41.007 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/ReedSolomon | 33.23 | 3600.01 | 108.336 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/dt | 46.02 | 3600.01 | 78.227 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/evalloop | 64.88 | 3600.01 | 55.487 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/fbench | 130.38 | 3600.01 | 27.612 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/ffbench | 25.35 | 3600.01 | 142.012 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/fp-convert | 70.5 | 3600.01 | 51.064 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/himenobmtxpa | 47.34 | 3600.02 | 76.046 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/mandel-2 | 90.38 | 3600.01 | 39.832 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/revertBits | 15.95 | 3600.01 | 225.706 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Shootout/ary3 | 10.34 | 3600.02 | 348.164 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Shootout/fib2 | 39.41 | 3600.02 | 91.348 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Shootout/hash | 11.32 | 3600.02 | 318.023 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Shootout/lists | 44.55 | 3600.01 | 80.808 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Shootout/matrix | 3.47 | 3600.01 | 1037.467 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Shootout/methcall | 37.68 | 3600.01 | 95.542 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Shootout/sieve | 24.01 | 3600.01 | 149.938 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Stanford/FloatMM | 38.64 | 3600.01 | 93.168 | blocked | None | gem5 截断; gap=time budget |

## 方法与口径

- 两引擎跑**同一个**已构建 ELF（驱动各自编译同一源，链接模式 static）；`*_seconds` 取驱动的 `run_seconds`（仅 guest 运行墙钟，不含编译）。
- `ratio = gem5_seconds / qemu_seconds`；仅在两引擎都未截断时纳入分布。
- 两引擎同 `--jobs`，调度压力一致；比值是 wall-clock 之比，不是指令数之比。
- 未改动任何源码、用例、期望或门控；本文件只记录观察，不做裁定。
