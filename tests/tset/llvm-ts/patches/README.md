# `tests/tset/llvm-ts/patches/` — 测试胶水（llvm-test-suite）

上游语料 **保持 patchless**（`manifests/components.lock.toml` 锁定、只读）。本目录
只放**逐例声明**、由驱动 `tools/testcases/tset/llvm-ts/run_llvm_ts_user.py` 施加到
**per-case run 副本 / 链接行**的胶水，用来把「上游参考与目标平台的固有差异」变成
可复现、可审计的输入/链接适配。**不改语料、不改目标语义（字节序 / ABI）、不放宽
任何比较**。

驱动侧的两张声明表（同文件 `CASE_PRNG_GLUE` / `CASE_LE32_INPUTS`）是唯一入口：
表里没有的用例不会拿到任何胶水。

## `glue/glibc_prng.c`（`obsequi`、`ft`，TESTCASES-080t）

**问题**：两例的整份输出由 `random()` 生成 —— `obsequi` `init.c:63`
`srandom(1)`、`init.c:66` 用 `random()` 播种 Zobrist 表；`ft` `graph.c:43`
`GET_WEIGHT = (random() + 1) % MAX_WEIGHT`，且其 `RUN_OPTIONS` 只有两个参数、
永远走不到 `ft.c:86` 的 `srandom()`（即**默认态**）。C 未规定 `random()` 算法，
上游参考钉死的是 glibc 的序列，musl 的实现不同。

**判据**：参考不是陈旧的 —— 未改语料的宿主 `gcc -O2` 构建可**逐字节**复现两份参考
（`obsequi` 4445 B sha256 `daaf7e2c…`；`ft` md5 `63acb35e…`，日志
`.work/log/testcases/TESTCASES-080t-host-*.log`）。

**做法**：`glibc_prng.c` 实现 glibc 的算法（degree 31 / separation 3 的 TYPE_3
加性反馈、Schrage 播种、播种后 **310 次**预热丢弃、未播种态 = `srandom(1)`），以
用例自身的编译行编译，并**排在 `libc.a` 之前**链接 ⇒ musl 的 `random.o` 不会被拉入
（胶水缺失/失配会在链接期或 oracle 处**显式失败**，不会静默退回 musl 的生成器）。

**独立核对**：`glue/verify_glibc_prng.py` 把同一探针分别链接宿主 glibc 与本胶水，
要求默认态 + 种子 `{0,1,2,7,12345,2147483647,4294967295}` × 100 抽**逐字节相同**
（当前 8/8 通过）。任一差异即非零退出。

## `glue/le32_to_be32.py`（`8b10b`，TESTCASES-080t）

**问题**：语料 `input.txt` 是**小端 u32 词流**，`testbench.c:59` 用
`fread(theInputArray, numberOfWords, sizeof(unsigned int), inputFile)` 按**主机序**
读入；目标为**大端**（ADR-0003 D1）⇒ 每个词被字节交换，`calc.c:170-173` 的
`index5 = ((w>>3)&0x1f)|(k<<5)`、`index3 = (w&7)|(k<<3)`（`k = w>>8`）越出
`lookupTable5B[64]`/`lookupTable3B[16]`，guest `SIGSEGV`（原 ISS-266）。

**做法**：脚本对 run 副本按**逐词 4 字节交换**重写（词值不变），打印转换前后
sha256，并回读校验。驱动随后复读转换后文件、用 `calc.c` 的索引式对**全部 65536
词**校验在界内（当前 worst `index5=63 < 64`、`index3=15 < 16`），任一越界即
`blocked`，不会带病跑。

**反例**：把语料原始（未转换）文件放回 run 副本后直接跑同一 ELF，guest 以
`SIGSEGV`（rc=139）退出 —— 证明转换是承重的（见
`.work/evidence/TESTCASES-080t/run.sh` 的 `inject.endian.8b10b`）。

## 使用与证据

- 驱动入口：`tests/tset/llvm-ts/README.md`「入口」；胶水随驱动自动施加，无需手工步骤。
- 一键证据：`.work/evidence/TESTCASES-080t/run.sh`（含注入 → FAIL → `cp`+md5 还原 → PASS）。
