# `tests/tset/llvm-ts/` — llvm-test-suite（外部套件，user 成品系统）

上游语料 **不入库**：由 `manifests/components.lock.toml` 锁定，`make fetch` 后位于
`.work/source/llvm-test-suite/`。

## 入口

| 用途 | 命令 |
|---|---|
| L2 代表集 | `make check-tset-llvm-smoke` |
| 套件全量（按需/夜跑） | `python3 tools/testcases/tset/llvm-ts/run_llvm_ts_user.py --link-mode static --jobs 4 --json-out /tmp/.../llvm.json` |
| 代表集规则（不跑 guest） | `python3 tools/testcases/tset/llvm-ts/run_smoke.py --list` |

- 驱动实现：`tools/testcases/tset/llvm-ts/run_llvm_ts_user.py`
  （`TESTCASES-075t` 从 `tools/testcases/` 迁入；旧路径 = 薄 wrapper，命令行等价）。
- 运行目录 / 三件套：`<test-artifacts>/llvm-ts-user/<UTC>-llvm-ts-user-<档>/`
  （`docs/Process-08`；目录名**未改**）。

## 代表集（L2）

`run_smoke.py` 用驱动自身的 `discover()` 现场枚举，**类别 = 上游三棵树**
（`MultiSource/Applications`、`MultiSource/Benchmarks`、
`SingleSource/Benchmarks`），每棵取**源码字节数最小**的用例（ties 按 case id）。
套件含 mafft/nbench 等分钟级基准，整树不能进 L2；该规则既保证每棵树有代表，
又把耗时压在受控范围。计数与选中项每次现场打印，不写死；结构断言 = 树全覆盖 /
无重复 / 驱动 census 自洽。

## 口径

- 期望值来自上游 `*.reference_output*`（byte-exact / md5）或 exit 0，驱动内
  分类器（`pass` / `fail` / `known-fail` / `blocked`）**未改**。
- **测试胶水**（TESTCASES-080t，`patches/glue/`，见该目录 `README.md`；TESTCASES-078t
  增加源码补丁类）：只对 **run 副本 / 链接行**生效的**逐例声明**适配，语料保持
  `patchless`、目标语义（字节序 / ABI）不变、比较不放宽：
  - `glibc_prng.c` → `obsequi`、`ft`：上游参考钉死的是 **glibc** 的
    `random()`（宿主 gcc 重编译不改语料即复现两份参考：obsequi 4445 B
    sha256 `daaf7e2c…`、ft md5 `63acb35e…`），而 C 未规定该算法；胶水按 glibc
    算法（31 阶 TYPE_3 + 310 次预热 + 未播种态 = `srandom(1)`）实现
    `random()`/`srandom()`，由 `patches/glue/verify_glibc_prng.py` 对宿主 glibc
    独立核对（默认态 + 7 个种子 × 100 抽，逐字节相同）。
  - `le32_to_be32.py` → `8b10b`：`input.txt` 是**小端 u32 词流**
    （`testbench.c:59` 用 `fread(..., sizeof(unsigned int), ...)` 按主机序读），
    目标为**大端**（ADR-0003 D1）；脚本把 run 副本按**逐词 4 字节交换**写成
    同样词值的大端流（打印 sha256 前后 + 回读校验），驱动随后复读转换后文件、
    按 `calc.c` 的索引式对**全部 65536 词**校验在界内（worst index5=63<64、
    index3=15<16）。
  - 源码补丁 → `SPASS`、`lemon`（TESTCASES-078t）：两例语料含真实 UB
    （函数指针强转 / 无原型调用传 `0`），x86-64 恰好可用、bank 分离 ABI 暴露；
    补丁在 **run 副本**上恢复源码本来要表达的原型（dry-run + 逐文件 sha256
    前后断言，空补丁 ⇒ `blocked`），随后**编译 run 副本**。两例上游参考
    （SPASS `b0b56c51…`、lemon `8c485439…`）**不必重定**：宿主 gcc 与修 UB 后
    目标构建均逐字节复现（TESTCASES-069t 的 `74365d61…` 经查 = 同一构建多传
    `-DocProof`，非上游 `RUN_OPTIONS`）。
- 由此 `obsequi`/`ft`/`8b10b` 三例 **static+dynamic 均 byte-exact / md5-exact
  `pass`**；`SPASS`/`lemon`（TESTCASES-078t）两档同样 **md5-exact `pass`**。
  `ClamAV`（TESTCASES-081t）经 `glue/glibc_stdio_buffer.c`（把 stdout 缓冲设为
  参考所用的 glibc `st_blksize`=4096）后同样 **byte-exact `pass`**：参考里
  `Initializing the engine` 的位置是 glibc stdio 缓冲造成的，不是程序行为；
  `ISS265_ADMISSION` 因此清空（`known-fail` 准入表为空）。
- **逐例排除**（`excluded`，理由含源码 文件:行）：上游自身不为本目标构建的单元
  ——`siod`/`office-ispell`（缺平台 API）、
  `archie-client`/`plot2fig`（TESTCASES-081t：上游 `CMakeLists.txt` 用
  `check_function_exists(re_comp)` 守卫整个 target；musl 无 BSD
  `re_comp`/`re_exec`，故上游配置不为本 libc 构建）、
  `MallocBench/{gawk,make,p2c}`（TESTCASES-081t 用户裁定「选 1」：上游
  `MallocBench/CMakeLists.txt:1-4` 只 `add_subdirectory(espresso/gs/cfrac)`，
  这三个目录从不进入构建）与
  `SingleSource/Benchmarks/Misc/aarch64-init-cpu-features`（上游只在
  `ARCH STREQUAL "AArch64"` 下构建；符号 `__aarch64_cpu_features`/`RUNTIME_INIT`
  仅 AArch64 libc 提供）。
- **guest 信号判据**（QEMU-075t / TESTCASES-081t）：宿主信号死亡用 `-strace`
  复探；`--- SIG... {si_signo, si_code, si_addr} ---` 投递行（`si_addr` 可为
  `0x...` 或 `NULL`）且无 `QEMU internal` ⇒ 真实 guest 故障 = `fail`；否则
  `blocked`。判据自带可达 FAIL 自检（`signal_delivery_selfcheck`，轮内执行、
  失败即 `classification_ok=False` ⇒ rc=1）。
- **逐例编译方言**（`CASE_CFLAGS`）：C89 时代语料按其上游声明的方言编译
  （`-std=gnu90`/`gnu89`，仅 `Burg`/`cdecl`/`OptimizerEval` 三例），**不全局放宽**，
  其它用例编译命令逐字节不变。
- **逐例超时**（`CASE_TIMEOUTS`）：`mafft` 于 TESTCASES-077t 重测（旧 1620 s 已不足），
  其余维持实测值；`DEFAULT_TIMEOUT` 不放大。
- 子集跑（`--only` / `--limit`）不写 `authoritative/`（`docs/Process-08 §1.2`）。
