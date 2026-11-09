# m13-testcases-001：dynamic 长尾 93 例 gem5/qemu 运行时间比

生成：2026-11-09T19:41:41Z（数值全部由驱动 JSON 现场统计，无估算）

范围：dynamic long-tail: the cases that timed out at the TESTCASES-104t dynamic baseline (timeout_inventory.<suite>.cases), re-run with the per-case budget below on gem5 SE and qemu-user; times measured by the tset drivers' own run_seconds

## 执行环境指纹

- 节点：`server208`；CPU：Intel(R) Xeon(R) CPU E7- 4820  @ 2.00GHz；nproc=64
- 并发：48（两引擎同值）；engines=qemu,gem5-se；link-mode=dynamic
- 预算：gem5 3600s / qemu 3600s（每例）
- gem5：`gem5.opt` md5=`4719101d5cf4aea7b05ac388f490d98c` 版本：25.1.0.1（编译于 Nov 10 2026 00:19:12）
- qemu：`qemu-dadao` md5=`8a2f3e6cd44b448f872b14f95d9c3509` 版本：qemu-dadao version 11.1.1 (v11.1.1-1-g7b71f51)
- musl HEAD：`f69857074830469865a35ae7f9d2006185789ff0`（dirty=False）
- 统计时 loadavg：[15.11, 27.77, 33.41]

## 总览

- 选中案例：93（libc-test 4、llvm-ts 89）
- 两引擎都有测量：93/93；缺失测量条目：0
- 比值分布（两引擎都未截断，n=12）：min=172.124 median=289.3425 P90=687.6516 max=1942.124
- 截断（timeout）已单列、未计入分布：77 例

## 比值分布（按类别）

| 类别 | n | min | median | P90 | max |
| --- | --- | --- | --- | --- | --- |
| MultiSource/Applications | 1 | 197.539 | 197.539 | 197.539 | 197.539 |
| MultiSource/Benchmarks/ASCI_Purple | 1 | 362.658 | 362.658 | 362.658 | 362.658 |
| MultiSource/Benchmarks/FreeBench | 1 | 229.719 | 229.719 | 229.719 | 229.719 |
| MultiSource/Benchmarks/McCat | 2 | 172.124 | 210.249 | 240.749 | 248.374 |
| MultiSource/Benchmarks/NPB-serial | 1 | 319.07 | 319.07 | 319.07 | 319.07 |
| MultiSource/Benchmarks/Trimaran | 1 | 1942.124 | 1942.124 | 1942.124 | 1942.124 |
| SingleSource/Benchmarks | 5 | 208.336 | 323.078 | 576.4408 | 723.762 |

## 离群（超出中位数 1/3–3 倍）

- llvm-ts:MultiSource/Benchmarks/Trimaran/enc-md5 ratio=1942.124

## 逐例

| suite | case | qemu_s | gem5_s | ratio | gem5_klass | exit | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| libc-test | functional/clocale_mbfuncs | 0.0 | 3600.01 | None | blocked | None | gem5 截断; gap=time budget; ratio 未定义 |
| libc-test | functional/crypt | 0.0 | 2356.85 | None | pass | 0 | ratio 未定义 |
| libc-test | functional/sscanf_long | 0.0 | 1391.81 | None | pass | 0 | ratio 未定义 |
| libc-test | functional/string_memset | 0.0 | 928.44 | None | pass | 0 | ratio 未定义 |
| llvm-ts | MultiSource/Applications/JM/lencod | 22.36 | 3600.02 | 161.003 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Applications/SIBsim4 | 54.94 | 3600.02 | 65.526 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Applications/SPASS | 14.39 | 3600.01 | 250.174 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Applications/aha | 118.55 | 3600.03 | 30.367 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Applications/lua | 952.68 | 3600.01 | 3.779 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Applications/oggenc | 12.49 | 2467.26 | 197.539 | pass | 0 | - |
| llvm-ts | MultiSource/Applications/viterbi | 12.78 | 3600.03 | 281.692 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/ASCI_Purple/SMG2000 | 5.41 | 1961.98 | 362.658 | pass | 0 | - |
| llvm-ts | MultiSource/Benchmarks/ASC_Sequoia/AMGmk | 36.58 | 3600.02 | 98.415 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/ASC_Sequoia/CrystalMk | 38.88 | 3600.02 | 92.593 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/ASC_Sequoia/IRSmk | 12.71 | 3600.04 | 283.245 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/BitBench/drop3 | 22.63 | 3600.17 | 159.088 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/BitBench/five11 | 13.65 | 3600.14 | 263.747 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/BitBench/uudecode | 3.4 | 3600.15 | 1058.868 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/DOE-ProxyApps-C/CoMD | 137.83 | 3600.02 | 26.119 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/DOE-ProxyApps-C/Pathfinder | 114.27 | 3600.01 | 31.504 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/DOE-ProxyApps-C/RSBench | 47.8 | 3600.16 | 75.317 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/DOE-ProxyApps-C/SimpleMOC | 256.07 | 3600.02 | 14.059 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/DOE-ProxyApps-C/XSBench | 255.04 | 3600.43 | 14.117 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/DOE-ProxyApps-C/miniAMR | 48.8 | 3600.06 | 73.772 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/DOE-ProxyApps-C/miniGMG | 116.39 | 3600.02 | 30.931 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Fhourstones | 40.54 | 3600.02 | 88.802 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Fhourstones-3.1 | 29.15 | 3600.04 | 123.501 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/FreeBench/fourinarow | 37.66 | 3600.58 | 95.608 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/FreeBench/mason | 7.89 | 3600.05 | 456.28 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/FreeBench/neural | 12.94 | 2972.56 | 229.719 | fail | 0 | - |
| llvm-ts | MultiSource/Benchmarks/FreeBench/pcompress2 | 18.05 | 3600.47 | 199.472 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/MallocBench/cfrac | 90.65 | 3600.02 | 39.713 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/McCat/01-qbsort | 7.79 | 1934.83 | 248.374 | pass | 0 | - |
| llvm-ts | MultiSource/Benchmarks/McCat/08-main | 5.18 | 891.6 | 172.124 | pass | 0 | - |
| llvm-ts | MultiSource/Benchmarks/McCat/12-IOtest | 37.63 | 3600.03 | 95.669 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/MiBench/automotive-basicmath | 32.69 | 3600.85 | 110.151 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/MiBench/consumer-lame | 18.0 | 3600.02 | 200.001 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/MiBench/consumer-typeset | 9.94 | 3600.02 | 362.175 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/MiBench/network-patricia | 11.33 | 3600.03 | 317.743 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/MiBench/telecomm-CRC32 | 9.52 | 3600.04 | 378.155 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/MiBench/telecomm-adpcm | 2.97 | 3600.07 | 1212.145 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/NPB-serial/is | 11.08 | 3535.3 | 319.07 | pass | 0 | - |
| llvm-ts | MultiSource/Benchmarks/Olden/bisort | 14.5 | 3600.03 | 248.278 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Ptrdist/ft | 21.34 | 3600.51 | 168.721 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Ptrdist/ks | 82.13 | 3600.84 | 43.843 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Ptrdist/yacr2 | 48.43 | 3600.01 | 74.334 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Rodinia/backprop | 41.59 | 3600.03 | 86.56 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Rodinia/hotspot | 58.19 | 3600.05 | 61.867 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Rodinia/pathfinder | 31.0 | 3600.38 | 116.141 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Rodinia/srad | 57.54 | 3600.04 | 62.566 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/SciMark2-C | 126.15 | 3600.02 | 28.538 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Trimaran/enc-3des | 3.84 | 3600.13 | 937.534 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/Trimaran/enc-md5 | 1.77 | 3437.56 | 1942.124 | pass | 0 | - |
| llvm-ts | MultiSource/Benchmarks/Trimaran/netbench-url | 11.04 | 3600.01 | 326.088 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/VersaBench/beamformer | 21.39 | 3600.01 | 168.303 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/VersaBench/dbms | 15.87 | 3600.01 | 226.844 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/llubenchmark | 33.39 | 3600.01 | 107.817 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | MultiSource/Benchmarks/nbench | 209.84 | 3600.01 | 17.156 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/BenchmarkGame/Large/fasta | 16.67 | 3600.07 | 215.961 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/BenchmarkGame/fannkuch | 85.27 | 3600.27 | 42.222 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/BenchmarkGame/n-body | 87.89 | 3600.22 | 40.963 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/BenchmarkGame/nsieve-bits | 52.76 | 3600.26 | 68.238 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/BenchmarkGame/partialsums | 56.26 | 3600.24 | 63.993 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/BenchmarkGame/puzzle | 42.17 | 3600.12 | 85.372 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/BenchmarkGame/recursive | 88.95 | 3600.15 | 40.474 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/BenchmarkGame/spectral-norm | 49.26 | 3600.01 | 73.082 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/CoyoteBench/huffbench | 34.99 | 3600.02 | 102.887 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Linpack/linpack-pc | 100.83 | 3600.03 | 35.704 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/McGill/chomp | 6.39 | 2271.38 | 355.459 | pass | 0 | - |
| llvm-ts | SingleSource/Benchmarks/McGill/queens | 10.15 | 3279.24 | 323.078 | pass | 0 | - |
| llvm-ts | SingleSource/Benchmarks/Misc/ReedSolomon | 26.02 | 3600.02 | 138.356 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/dt | 42.09 | 3600.01 | 85.531 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/evalloop | 54.85 | 3600.01 | 65.634 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/fbench | 119.39 | 3600.03 | 30.154 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/ffbench | 23.9 | 3600.03 | 150.629 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/fp-convert | 63.32 | 3600.01 | 56.854 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/himenobmtxpa | 47.18 | 3600.02 | 76.304 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/mandel-2 | 92.05 | 3600.01 | 39.109 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/oourafft | 25.44 | 3600.01 | 141.51 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/perlin | 15.43 | 3214.63 | 208.336 | pass | 0 | - |
| llvm-ts | SingleSource/Benchmarks/Misc/revertBits | 9.16 | 3600.01 | 393.014 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/richards_benchmark | 8.08 | 3600.04 | 445.55 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Misc/salsa20 | 3.83 | 2772.01 | 723.762 | pass | 0 | - |
| llvm-ts | SingleSource/Benchmarks/Shootout/ary3 | 12.89 | 3600.02 | 279.288 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Shootout/fib2 | 33.73 | 3600.01 | 106.73 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Shootout/hash | 13.09 | 3600.02 | 275.021 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Shootout/lists | 22.66 | 3600.01 | 158.871 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Shootout/matrix | 6.43 | 3600.01 | 559.877 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Shootout/methcall | 40.94 | 3600.01 | 87.934 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Shootout/sieve | 29.47 | 3600.01 | 122.158 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Shootout/strcat | 7.93 | 3600.02 | 453.975 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Stanford/FloatMM | 46.95 | 3600.01 | 76.678 | blocked | None | gem5 截断; gap=time budget |
| llvm-ts | SingleSource/Benchmarks/Stanford/Puzzle | 12.54 | 3255.57 | 259.615 | pass | 0 | - |

## 方法与口径

- 两引擎跑**同一个**已构建 ELF（驱动各自编译同一源，链接模式 dynamic）；`*_seconds` 取驱动的 `run_seconds`（仅 guest 运行墙钟，不含编译）。
- `ratio = gem5_seconds / qemu_seconds`；仅在两引擎都未截断时纳入分布。
- 两引擎同 `--jobs`，调度压力一致；比值是 wall-clock 之比，不是指令数之比。
- 未改动任何源码、用例、期望或门控；本文件只记录观察，不做裁定。
