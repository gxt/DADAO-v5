> **升格指针**（INFRA-058t，用户 2026-10-11 裁定「被引用材料不得只放 `.work/`」）：本文档由 `.work/log/integ/` 下同名文件升格至 `.tao/knowledge/`（原 `.work/` 副本已移出，该目录 gitignored、不再保留）。
# Embench-IoT → DADAO 接入分析

> 分析对象：`.cache/embench-iot/`（浅克隆，只读；HEAD = `09c2ed8 "Remove CPU_MHZ references"`，分支 `master`，工作树干净）。
> 分析者：subagent（只读分析）。全程未修改 `.cache/embench-iot/`；临时产物在 `/tmp/opencode/embench-analysis/`；未提交 git。
> 结论证据：文件+行号 / 命令输出。事实与推测分开标注（"实测"= 本次跑出；"推理"= 未在本环境跑出）。

---

## 0. 结论摘要

| 维度 | 结论 | 关键证据 |
|------|------|----------|
| **平台接入面** | 极窄：平台只需实现 **3 个函数**（`initialise_board`/`start_trigger`/`stop_trigger`）；无 `uart_*`/`timer_*`/`power_*`/`exit` 要求 | `support/support.h:35-37`；`doc/README.md:277-284,686-690` |
| **端序** | 仅 **`md5sum` 1 个**基准有端序假设（`uint32_t*` 重解释），大端下会 **verify 失败**；其余 18 个与端序无关 | `src/md5sum/md5.c:101`（仅此一处重解释，全仓 `grep` 仅此命中）；实测见 §4 |
| **varargs / printf** | **不需要**。所有 `printf/puts` 均在 `DEBUG`/`ROUNDS`/`SLRE_DEBUG`/`DO_TRACING` 宏内，默认不编译 | `md5.c:103,121`；`nsichneu:43-46`；`slre:34-38` |
| **malloc** | **不用 libc malloc**；BEEBS 自带 bump 分配器（`beebsc.c`），堆是**静态数组** ≤ **8 KiB** | `support/beebsc.c:93-181`；`sglib/huff/qrduino HEAP_SIZE=8192` |
| **浮点** | 基准集**纯整数**（`statemate #define float int`、`depthconv` 的 `float` 字段未被使用）；但 **`wikisort` 调 `sqrt()`** ⇒ 需一个 double `sqrt`（libm 或自备） | `statemate:54`；`depthconv:66-67`；`wikisort:386` |
| **最小运行时** | `memcpy/memset/memmove/memcmp/strlen/strchr` + ctype(`tolower/isspace/isdigit/isxdigit`) + `sqrt` + 可能 `abort` | §3 逐基准 `nm -u` 实测 |
| **(B) 内存** | 单最大基准 ≈ **43 KB** 静态（xgboost）+ 栈 ≤ **~13 KB** + 堆 ≤ 8 KB ⇒ **≈ 64 KB**；全量 19 个**一次性常驻**合计 **267.7 KB** 静态。**当前 16 MiB RAM 远远够用（≥ 250× 余量）** | §5 |
| **最大缺口（工具链）** | **无 C 前端可用的 clang**：`.work/build/llvm/bin/` 只有 `llc/llvm-mc/ld.lld/llvm-objcopy`，**无 clang**；且 `components/llvm-project/patches/` **无任何 clang 侧补丁**（无 DADAO `TargetInfo`） | §6① |
| **OS/syscall** | **不需要 OS**。Embench 是 freestanding；停机/输出由 crt0 走 semihosting `SYS_EXIT` 完成 | `codegen_crt0.s`；`contract-semihosting.md §3/§5` |

> **重要澄清（与任务描述的目标用语）**：Embench 框架**不打印 "correct" 字符串**——`support/main.c` 完全不输出，正确性由 **进程退出码** 表达（`main` 返回 `!correct` ⇒ exit code 0 = 正确）。`"correct"` 字样属 **Dhrystone**（Embench `src/` 里**没有** Dhrystone，见 §1 末）。所以"在 QEMU 打出 correct"是 Dhrystone 的说法；对 Embench，等价判据是 **exit code == 0**。

---

## 1. 仓库结构与构建方式

### 1.1 官方推荐的新平台接入流程

事实（`doc/README.md`「Adding a new board to Embench」，行 667-723）：

1. 在 `examples/<arch>/<board>/` 下建 **两个文件**：`boardsupport.h`（可为空）+ `boardsupport.c`（行 674-679）。
2. `boardsupport.c` **只需实现 3 个 `void` 函数**（行 686-690）：
   - `void initialise_board (void)` — 板级初始化；
   - `void start_trigger (void)` — 计时开始；
   - `void stop_trigger (void)` — 计时结束。
3. 用时序无关（GDB 设断点计时）时，`start/stop_trigger` 可为空体（行 700-712）。
4. 可选放链接脚本等板级文件（行 721-723）。
5. 用 **SCons** 构建（行 312-315），关键命令行变量（行 288-306）：`cc`、`ld`、`cflags`、`ldflags`、`user_libs`、`gsf`、`warmup_heat`；选项 `--build-dir`、`--config-dir`（**必须**）。

### 1.2 构建系统：SCons 为主，`examples/` 无手写 Makefile

- `sconstruct.py` **是唯一的构建脚本**（行 1-97）。它：
  - 收集 `src/*/` 下每个基准目录（行 16-18）；
  - 编译支持对象 `support/main.c`、`support/beebsc.c`、`<config>/boardsupport.c`（行 59-65）；
  - 每个基准 `Glob(src/<bench>/*.c)`（行 89）并 `Program()` 链接（行 96）。
  - 变量：`cc`（默认 `$CC`）、`cflags`（默认 `$CCFLAGS`）、`ld`（默认 `$LINK`）、`ldflags`（默认 `$LINKFLAGS`）、`user_libs`、`warmup_heat`、`gsf`（行 30-38）。
  - 预处理宏：`WARMUP_HEAT`、`GLOBAL_SCALE_FACTOR`（行 49-50）；`CPPPATH=['support', config_dir]`（行 51）。
  - **不使用 `OBJCOPY`**；`ld` 默认 = `cc`。
- 实测：`examples/**` 下**没有任何构建用 Makefile**（唯一的 `doc/Makefile` 用于文档）；每个 `examples/<board>/README.md` 只给一行 `scons ...` 命令。例：
  - `examples/native/speed/README.md:6`：
    `scons --config-dir=examples/native/speed/ cflags="-O2 -fdata-sections -ffunction-sections" ldflags="-O2 -Wl,-gc-sections" user_libs=-lm`
  - `examples/riscv32/rv32wallyverilog/README.md:7-9`：
    `scons --config-dir=... user_libs=-lm cc=riscv32-unknown-none-elf-gcc cflags='-fdata-sections -ffunction-sections -mabi=ilp32d' ldflags='-Wl,-gc-sections -mabi=ilp32d -nostartfiles -T${CONFIG_DIR}/link.ld'`
  - `doc/README.md:336-351` 给出同一 RISC-V 例子逐项解释（`-nostartfiles -T${CONFIG_DIR}/link.ld`，`-ffunction-sections/-fdata-sections` + `-Wl,-gc-sections`，`user_libs=-lm`）。

**结论**：接入 DADAO 有两条路——(a) 用 SCons + `--config-dir=examples/dadao/<board>/`（最省事，但要提供 `cc`=dadao clang、`ld`=ld.lld、`ldflags=-T dadao.lds -nostdlib`、`user_libs` 含最小运行时与 `-lm`）；(b) 手写一个 `Makefile`（仓库**未**提供，需自建），逐基准 `cc -c` + `ld`。SCons 的路更贴合官方，但需要`cc` 可执行；由于我们**没有可用 clang**（§6），任一路都先卡在工具链。

### 1.3 19 个基准与"有没有 Dhrystone"

`src/` 下 19 个（实测 `ls`）：`aha-mont64, crc32, depthconv, edn, huffbench, matmult-int, md5sum, nettle-aes, nettle-sha256, nsichneu, picojpeg, qrduino, sglib-combined, slre, statemate, tarfind, ud, wikisort, xgboost`。**没有 Dhrystone**——Dhrystone 需另行准备（属另一条链，不在本仓库）。每个基准一个目录，源文件数 1–3 个（如 `picojpeg`=3、`qrduino`=5）。

---

## 2. `support/` 接口面

### 2.1 逐文件职责

| 文件 | 职责 | 关键行 |
|------|------|--------|
| `support/support.h` | 框架接口声明（平台 + 基准两侧）+ 引入 `beebsc.h` | 31,35-59,63 |
| `support/board.c` | **只是包装**：`#include "boardsupport.c"`（scons **不编译**它） | 14 |
| `support/chip.c` | 芯片相关包装：`#include "config.h"`；`HAVE_CHIPSUPPORT_H` 时含 `chipsupport.c`；否则空 TU | 14-25 |
| `support/main.c` | 基准驱动 `main()`（调用序列，见 2.3） | 17-39 |
| `support/beebsc.c` | BEEBS 本地库：`rand_beebs/srand_beebs`、bump 堆 `init/check/malloc/calloc/realloc/free_beebs` | 42-181 |
| `support/beebsc.h` | 上述声明 + `RAND_MAX=2^15-1`、`assert_beebs`、浮点比较宏 | 22,39,41-44,48-56 |
| `support/dummy-benchmark/dummy.c` | 基准桩（返回值 `0xBE`），供构建冒烟 | 11-35 |

> 注意：`scons` 编译的是 `<config>/boardsupport.c`，**不是** `support/board.c`（`sconstruct.py:63`）。`board.c`/`chip.c` 是给别的构建流/芯片层用的包装。

### 2.2 必须由"平台"实现的函数清单（原型 + 行号）

来源 `support/support.h`：

```
void initialise_board (void);      // 行 35  —— 平台实现
void start_trigger   (void);       // 行 36  —— 平台实现
void stop_trigger    (void);       // 行 37  —— 平台实现
```

仅这 3 个。**不存在** `uart_*` / `timer_*` / `power_*` / `exit` 等平台钩子（全仓 `grep` 无）。计时/打印是**平台自选项**，不是框架要求。

**由基准实现**（行 31,43,49,54,59）：`initialise_benchmark`、`warm_caches(int)`、`benchmark()`、`verify_benchmark(int)`。

**由支持库实现**（`beebsc.c/h`）：`rand_beebs`、`srand_beebs`、`init_heap_beebs`、`check_heap_beebs`、`malloc_beebs`、`calloc_beebs`、`realloc_beebs`、`free_beebs`（行 48-56）。

### 2.3 `main()` 调用序列（`support/main.c:25-37`，实测逐行）

```
initialise_board();          // 25  平台
initialise_benchmark();      // 26  基准
warm_caches(WARMUP_HEAT);    // 27  基准
start_trigger();             // 29  平台
result  = benchmark();       // 30  基准
stop_trigger();              // 31  平台
correct = verify_benchmark(result);  // 35  基准（返回 -1=不做校验；否则非 0=正确）
return (!correct);           // 37  ⇒ 正确时返回 0
```

`result` 声明为 `volatile int`（行 22），防优化。`verify_benchmark` 语义见 `support.h:28-31`（返回 -1 表示"未做校验"）。

---

## 3. 需要哪些 libc / 运行时

### 3.1 实测方法

用宿主 `gcc -Os -ffreestanding -fno-builtin -c` 逐基准编译（含 `support/main.c`+`support/beebsc.c`），再 `nm -u` 列**未定义符号**（脚本 `/tmp/opencode/embench-analysis/free_syms.sh`）。去掉基准内部/框架符号后，**真正的外部运行时符号**如下：

| 基准 | 需要的外部运行时符号 |
|------|----------------------|
| aha-mont64, depthconv, netttle-aes, nettle-sha256, nsichneu, statemate | （无）|
| crc32, tarfind | `rand_beebs`,`srand_beebs`（beebsc 提供）|
| edn, matmult-int, ud | `memcmp` |
| huffbench | `malloc_beebs`,`free_beebs`,`init_heap_beebs`,`memcmp` |
| md5sum | `malloc_beebs`,`calloc_beebs`,`free_beebs`,`init_heap_beebs` |
| picojpeg | `memcmp` |
| qrduino | `malloc_beebs`,`calloc_beebs`,`free_beebs`,`check_heap_beebs`,`init_heap_beebs`,`memcmp`,`memmove`,`strlen` |
| sglib-combined | `malloc_beebs`,`check_heap_beebs`,`init_heap_beebs`,`memcmp` |
| slre | `memcmp`,`memmove`?,`strchr`,`strlen`,`tolower`（+ctype 内建 `isspace/isdigit/isxdigit`）|
| wikisort | `memcmp`,`memmove`,`sqrt`,`rand_beebs`,`srand_beebs` |
| xgboost | （无外部，仅内部 `predict` 等）|

（说明：`memcpy/memset` 在 gcc 下被内联/展开而未出现在未定义表；**clang 会发出对 `memcpy/memset/memmove` 的调用**，必须自备——见下。）

### 3.2 最小运行时清单（freestanding libc 子集）

必须提供（**至少**）：
- `memcpy`、`memset`、`memmove`、`memcmp`（编译器生成 + 基准显式调用；`-ffunction-sections -Wl,--gc-sections` 可裁掉未用者）
- `strlen`、`strchr`（`qrduino`/`slre`）
- ctype：`tolower`（`slre:184,213,214`），及其依赖的 `isspace`(`:143,148`)、`isdigit`(`:153`)、`isxdigit`(`:499`)；注意 `slre` 用 `<ctype.h>`，宿主 glibc 用表宏 `__ctype_b_loc`/`__ctype_tolower_loc`（**非可移植**，需自备一组简单 ctype）
- `sqrt`（**double**，`wikisort:386`）——需 libm 或自备 double `sqrt`
- （条件）`abort`（`nettle-sha256:152` 的不可达 `default` 分支；开 `--gc-sections` 时通常被丢弃，否则需桩）

### 3.3 三项关键判定（任务重点）

**(a) 是否依赖变参 `printf`？→ 不需要。**
逐一核对所有 `printf/puts/fprintf` 出现点，**全部在调试宏内**，默认构建**不编译**：
- `md5.c`：`:103` 在 `#ifdef DEBUG`、`:121` 在 `#ifdef ROUNDS`、`:161/224` 在 `#ifdef DEBUG/ROUNDS`（`md5.c:103,121,155,161,224`）。
- `nsichneu/libnsichneu.c`：`:51` 在 `#ifdef DO_TRACING`，且 `:35` 该宏被注释掉。
- `slre/libslre.c`：`:35` `#define DBG(x) printf x` 仅在 `#ifdef SLRE_DEBUG` 下（`:34-38`）。
- `aha-mont64:189/205/208`、`huffbench:341-342` 均为注释。
- 其余基准无 `stdio.h` 使用（`tarfind.c` 含 `stdio.h` 但无 printf 调用，实测 `grep` 无命中）。

⇒ 框架与基准集**不需要 varargs 调用约定**。这对 DADAO 尤其重要，因为 `contract-abi.md` 明确 **`varargs` 属 `Excluded from M3`**（§开头 "Excluded" 清单）。**唯一需要 varargs 的场景**是"你想让 board shim 打印诊断字符串"——那也**不必**用 `printf`，用 semihosting `SYS_WRITE0` 直接写串即可（见 §6②）。

**(b) 是否用 `malloc`？→ 不用 libc malloc，但用 BEEBS 自带堆。**
- 使用方（实测 `grep malloc_beebs`）：`sglib-combined`、`md5sum`、`huffbench`、`qrduino`、`tarfind`；调用者共 5 个基准。
- 实现：`beebsc.c:93-125` `malloc_beebs` = 单调 bump 指针（`heap_ptr += size`，不 free）；`free_beebs` 空实现（`:178-181`）；`calloc_beebs`=`malloc_beebs`+`memset`（`:132-144`）。
- 堆**不是从 libc 拿**，而是一个**静态数组**，由各基准用 `init_heap_beebs((void*)heap, HEAP_SIZE)` 注册：
  - `sglib-combined/combined.c:24-25` `HEAP_SIZE 8192`
  - `huffbench/libhuffbench.c:59-60` `HEAP_SIZE 8192`
  - `qrduino/qrtest.c:27-28` `HEAP_SIZE 8192`
  - `md5sum/md5.c:22,30` `HEAP_SIZE (2000+1016+64)=3080`
  - `tarfind/tarfind.c:40-41` `HEAP_SIZE roundup(sizeof(tar_header_t)*ARCHIVE_FILES, sizeof(void*))`
- ⇒ **无需 libc 的 `malloc/free`，也无需 OS `brk`**；只需一块 ≤ 8 KiB 的静态 RAM（已计入 §5 的 `.bss`）。

**(c) 是否需要浮点？→ 基准集是纯整数；但有 1 处 `sqrt`。**
- `statemate`：源码里 `#define float int`（`libstatemate.c:35-54`），注释明说 "so we don't need a floating point library"。
- `depthconv`：结构体里有 `float float_activation_min/max`（`:66-67`），但**全文件无对它们的读写**（实测 `grep` 仅声明）——量化 int8 路径。
- `ud`：`fabs` 在注释中（`:101,191`）。
- `wikisort`：`:386` `long block_size = sqrt (decimal_step);` **非注释、会编译**，且 `#include <math.h>`（`:29`）。⇒ 需要 `sqrt`（double）。
- `support/beebsc.h:41-44` 提供 `float_eq_beebs/double_eq_beebs`，但**无任何基准使用**（实测 grep 仅声明）。
⇒ **不需要 FP 指令/FP ABI**；只需链接一个 double `sqrt`（或改 `wikisort` 用整数 sqrt——但那是改基准，不建议）。

---

## 4. 端序 / 类型假设

### 4.1 端序

实测全仓搜索 `__BYTE_ORDER__|_LITTLE_ENDIAN|__CHAR_UNSIGNED__|htonl|bswap`：`src/` 与 `support/` **零命中**（`examples/arm/...` 的 CMSIS 头有，但**不参与**构建）。

- `nettle-sha256`：用**逐字节**宏 `READ_UINT32/WRITE_UINT32`（大端，`nettle-sha256.c:112-129`）与 `_nettle_write_be32`（`:131`）——**端序无关**。
- `nettle-aes`：用**逐字节** `LE_READ_UINT32/LE_WRITE_UINT32`（`nettle-aes.c:27-40`）——**端序无关**。
- **唯一风险点 `md5sum`**：`md5.c:101`
  ```c
  uint32_t *w = (uint32_t *) (msg + offset);
  ```
  这是**唯一**一处 `char*`→`uint32_t*` 重解释（全仓 `grep` 仅此命中，实测）。MD5 规范要求**小端**字序；在大端机上该读入会产生不同的字，且 `md5.c:93` 的长度写入 `memcpy(...,&bits_len,4)` 也是本机字序。此外 `verify_benchmark` 硬编码 `RESULT 0x33f673b4`（`:28,247`）——该值在 x86（小端）上得出。
- **实测反证（临时树，不改仓库）**：把 `md5.c` 的 `uint32_t*` 读改写为**显式大端**读（`/tmp/opencode/embench-analysis/be/md5.c`），宿主 gcc 重编运行：
  ```
  大端字序模拟 exit=1  (0=正确, 非零=verify 失败)
  ```
  ⇒ 证实 **md5sum 的正确性依赖小端**。**大端 DADAO 上 md5sum 会 FAIL**（推理：DADAO 为 `ELFDATA2MSB`/`E` DataLayout，见 §6；未在大端实机跑，属高置信推理）。

### 4.2 类型宽度（32 位 vs 64 位）

- `crc32/crc_32.c:44` `typedef unsigned long DWORD;`、`huffbench:64` `typedef unsigned long bits32;` —— 在 LP64 / DADAO(64 位)下 `unsigned long` = 64 位。
- **实测**：以宿主 `gcc`（x86-64 **LP64**，`long`=64）链接并运行**全部 19 个基准**，**19/19 exit=0（PASS）**（命令见 §5.1）。
  - `crc32` 之所以 64 位安全：`crc32pseudo` 返回 `~oldcrc32`，但 `benchmark_body` 取 `(int)(r % 32768)`（`:203`），`32768=2^15` 取模只保留低 15 位，高位垃圾不影响结果（`crc32:160-163,203,210`）。
  - ⇒ **`long`=64 位不会破坏基准集**（有实测）。端序才是唯一坑。
- `__CHAR_UNSIGNED__`：无依赖。

---

## 5. (B) 内存需求（实测估算）

### 5.1 静态 footprint（宿主 `gcc -Os`，每基准 + 框架，单位字节）

命令：`gcc -Os -DWARMUP_HEAT=1 -DGLOBAL_SCALE_FACTOR=1 -I support -I src/<b> -I . support/main.c support/beebsc.c examples/native/speed/boardsupport.c src/<b>/*.c -lm -o out` 然后 `size out`（脚本 `/tmp/opencode/embench-analysis/build_size.sh`）。

| 基准 | .text | .data | .bss | 合计 |
|------|------:|------:|-----:|-----:|
| aha-mont64 | 3062 | 600 | 64 | 3726 |
| crc32 | 4377 | 544 | 40 | 4961 |
| depthconv | 2754 | 1200 | 224 | 4178 |
| edn | 6962 | 608 | 2512 | 10082 |
| huffbench | 5027 | 608 | 8768 | 14403 |
| matmult-int | 6256 | 608 | 16072 | 22936 |
| md5sum | 3548 | 600 | 3176 | 7324 |
| nettle-aes | 15242 | 1104 | 1088 | 17434 |
| nettle-sha256 | 8159 | 752 | 96 | 9007 |
| nsichneu | 24034 | 608 | 200 | 24842 |
| picojpeg | 13514 | 608 | 2560 | 16682 |
| qrduino | 11490 | 624 | 8320 | 20434 |
| sglib-combined | 13012 | 608 | 8848 | 22468 |
| slre | 6430 | 760 | 40 | 7230 |
| statemate | 7549 | 600 | 384 | 8533 |
| tarfind | 2462 | 544 | 9040 | 12046 |
| ud | 3284 | 608 | 3616 | 7508 |
| wikisort | 13179 | 736 | 3264 | 17179 |
| **xgboost** | **42460** | **600** | **40** | **43100 ← 最大** |
| **合计（全 19）** | 192801 | 12920 | 68352 | **274073 (267.7 KiB)** |

> 口径说明：宿主 64 位 LP64 + glibc，`-Os`。链接结果可能含少量 glibc/启动代码（如 `sqrt`/`abort`），使 `.text` 略偏大；DADAO 的实际值会有差异，但**量级与"≤ 64 KB/基准"结论稳健**。DADAO 为 64 位（指针 8B），与宿主一致，故可比性较好。

### 5.2 栈深度（`-fstack-usage` 单帧最大值，宿主 gcc）

| 基准 | 最大单帧 | 函数 |
|------|--------:|------|
| **huffbench** | **12896** | `compdecomp`（`freq[512]/heap[256]/link[512]/code[256]/clen[256]` 全在栈上） |
| wikisort | 4496 | `WikiSort`（非递归，见下） |
| slre | 4112 | `slre_match`（对 regex 列表逐项调用，深度小） |
| matmult-int | 3216 | `verify_benchmark`（期望值常量数组） |
| sglib-combined | 1824 | `benchmark_body` |
| edn | 1616 | `verify_benchmark` |
| 其余 | ≤ 744 | — |

- 递归核对：`wikisort` 的 `WikiSort` 定义在 `:332`，**无自递归**（`:1105` 是外层调用）；`slre_match`（`:605`）对子 regex 递归，深度受 regex 数量限制（小）；`sglib` 明说"handle recursive calls without recursion"（`sglib.h:131-133`，显式数组栈）。
- ⇒ **栈高水位 ≈ 13 KiB**（huffbench）。为安全建议**预留 ≥ 64 KiB 栈**（考虑中断/实现差异与 slre/wikisort 的有限递归）。

### 5.3 堆需求

- BEEBS bump 堆 = 静态 `heap[]`，`HEAP_SIZE` 最大 **8192 B**（sglib/huffbench/qrduino），已计入上表 `.bss`；`md5=3080`、`tarfind≈9040`（起 `.bss` 中）。
- `check_heap_beebs` 会校验是否溢出（`beebsc.c:77-81`）——若 RAM 配置过小导致堆溢出，基准会返回错误，故堆**必须**完整放下。

### 5.4 (B) 结论

| 情形 | RAM 需求（代码 + 数据 + 栈 + 堆） | 说明 |
|------|-----------------------------------|------|
| **单个最大基准** | **≈ 64 KiB**（43 KB 静态 + ≤13 KB 栈 + ≤8 KB 堆；且栈/堆多在 `.bss` 内已计） | 峰值来自 **xgboost**（静态 43 KB）；huffbench 栈最高但静态仅 14 KB |
| **全量 19 个"逐个跑"** | **≈ 64 KiB**（一次只驻留一个） | 顺序执行，各基准独立加载 |
| **全量 19 个"一次性常驻"** | **≈ 268 KiB** 静态 + 每任务各自栈/堆（若并发） | 合计 274073 B |

**当前 16 MiB RAM@0 是否够？→ 远远够（余量 ≥ 250 倍）。**
- 事实：RAM@0 = `[0, 16 MiB)`，另一段旧 RAM = `0xffff_0000_0000`（16 MiB）（`components/qemu/patches/target/dadao/cpu.h.patch:66-72`；`dadao-machine.c.patch:485-495`）。
- 即使用户要求的 1 GiB 也"远超"（与 `INTEG-023k §D.0 实测①` 的结论一致：现最大单程序 `.o` 仅 1128 B）。**16 MiB 对 Embench 绰绰有余**。

---

## 6. 对 DADAO 的接入点清单

### ① 工具链需要什么

**事实（实测 `.work/build/llvm/bin/` 与补丁集）**：
- 已有：`llc`（`llc --version` 列出 `dadao - DADAO SimRISC`）、`llvm-mc`、`ld.lld`、`llvm-objcopy`、`llvm-objdump`。
- **缺失且关键：没有可用的 C 前端 `clang`**（`.work/build/llvm/bin/` 无 `clang*`；`command -v clang` 只命中宿主 `/usr/bin/clang 18.1.3`，**非 dadao target**）。
- **更关键：`components/llvm-project/patches/` 58 个补丁里，`grep clang` 零命中**——**没有** clang 侧 DADAO `TargetInfo`（`clang/lib/Basic/Targets/DADAO.*`）、没有 driver/triple 接入。仅 `Triple.cpp/Triple.h`（LLVM 层）认识 `dadao`。

⇒ 要把 Embench（C 源码）编成 DADAO 目标码，**必须新增 clang 前端支持**（`clang -target dadao-unknown-elf` 的 `TargetInfo`：端序=big、指针=64、`long`=64、`char` 默认 signed/unsigned、对齐等），或采用等价的 C→LLVM-IR 通道。**仅构建 clang 二进制还不够**——需补 clang TargetInfo 补丁。这与 `INTEG-023k §D.1 #5`（clang 建议不纳入 M6）冲突：**Embench 目标事实上要求 C 前端**。
- 其它工具用途：`llc -march=dadao`（IR→asm）、`llvm-mc --triple=dadao -filetype=obj`（asm→obj）、`ld.lld -T tests/scripts/dadao.lds`（链接，产出 `ET_EXEC`/`EM_DADAO`/`ELFDATA2MSB`/`e_flags=1`）、`llvm-objcopy`（raw-bin 路径 `--only-section=.text -O binary`）、`llvm-size/llvm-objdump`（量 footprint）。
- DataLayout（后端已定）：`E-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128`（`components/.../TargetDataLayout.cpp.patch:11`）——**大端 `E`、指针 64**。clang TargetInfo 需与此一致。

### ② board shim 需实现哪些函数（映射到 semihosting）

只需 `examples/dadao/<board>/boardsupport.{c,h}` 里的 3 个函数：

| 函数 | 建议实现 | 映射的 semihosting 服务（`contract-semihosting.md §3`） |
|------|----------|--------------------------------------------------------|
| `initialise_board(void)` | 空（或做一次性板级初始化） | 无（可选 `SYS_HEAPINFO 0x16`） |
| `start_trigger(void)` | 计时开始：记录 tick | `SYS_ELAPSED 0x30`（64 位 target ticks）或 `SYS_CLOCK 0x10`（百分秒，太粗） |
| `stop_trigger(void)` | 计时结束：读回 tick | 同上 |
| （可选）打印诊断 | 直接写串，**无需 printf/varargs** | `SYS_WRITE0 0x04`（0 结尾串）/ `SYS_WRITEC 0x03`（单字符） |
| （停机） | 由 crt0 完成，**基准/板级不实现** | `SYS_EXIT 0x18`（或 `SYS_EXIT_EXTENDED 0x20`）|

调用约定：`rd16`=服务号、`rb16`=参数块指针、`rd31`=返回值；`trap cfx_umon, 0x30000`（`immu18[17:16]==2'b11`）触发（`contract-semihosting.md §1-§2`；`common-semi-target.c.patch`）。

**仅做正确性（不测速）时**，`start/stop_trigger` 可照搬官方样板（volatile asm clobber memory，`doc/README.md:700-712`）。exit code = `main` 返回值低字节（`codegen_crt0.s` 注释；`contract-semihosting.md §5`），故 Embench 的 pass 判据 = **QEMU 进程退出码 0**。

### ③ crt0 / 链接脚本需满足什么

**已有**：`tests/scripts/codegen_crt0.s`、`tests/scripts/dadao.lds`。
- `dadao.lds`：`ENTRY(_start)`；`MEMORY{RAM 0xffff00000000 LEN 16M; ROM 0xffffffff0000 LEN 64K}`；段序 `.text→.rodata→.data→.bss`；`ASSERT` 防超界（脚本行见文件）。**段布局已满足 Embench 需求**（read-only 常量进 `.rodata`，可变数据进 `.data`/`.bss`）。
- `codegen_crt0.s`：`_start` 设 `SP=rb1=0xffff_00ff_0000`、`call main`、把 `rd31` 经 `SYS_EXIT` 传给宿主。
- **`.bss` 清零**：crt0 **不做**；由 **QEMU 加载器**完成——`dadao_load_elf` 对每个 `PT_LOAD` 做"`p_filesz` 数据 + `p_memsz-p_filesz` 零填充"（`dadao-machine.c.patch:398-422`）。⇒ Embench 的静态零初始化（各 `heap[]`、`.bss` 数组）由加载器保证。**前提**：`.bss` 必须与 `.data` 处于同一 `PT_LOAD` 且 `p_memsz>p_filesz`（`dadao.lds` 正是如此）。
- **不需要** `__attribute__((constructor))` / `.init_array`：Embench 无 C++ 全局构造、无 `__libc_init`。只要 `_start→main` 即可。
- **栈**：`SP` 上方到 RAM 顶（`0xffff_0100_0000`）约 **64 KiB** 可用；下方到 `_end` 也充裕，对 §5.2 的 ~13 KiB 高水位足够。

### ④ 是否需要 OS / syscall

**不需要。** Embench 是 freestanding、无 OS 假设（`README.md:3-6`：assumes "no OS, minimal C library support, no output stream"）；唯一"系统"交互是**停机**（`return` 出 `main`），由 crt0 用 semihosting `SYS_EXIT` 完成。无 `open/read/write/brk/sbrk` 需求（输出流本就不需要；BEEBS 堆自带）。

---

## 7. 不确定项 / 未验证事项（诚实列出）

1. **大端实机未跑**：本环境**无**大端交叉编译器/`qemu-user`（`command -v qemu-s390x powerpc-linux-gnu-gcc ...` 全空）。`md5sum` 在大端失败由"临时树显式大端字序模拟"反证（exit=1）＋代码事实推出，**未在 DADAO/QEMU 上实跑**。
2. **DADAO 侧真实 footprint 未知**：§5 表为**宿主 gcc x86-64** 值，非 DADAO clang 值。二者指针宽度一致（64 位），但指令编码/对齐/libcall 差异会使数值变化；**量级结论稳健，精确值待 clang 就位后重测**。
3. **clang TargetInfo 缺失的确切后果未实测**：因无 clang 二进制，未实际执行 `clang -target dadao-unknown-elf`（预期报 unknown target triple）。"构建 clang 后仍不能编 dadao C"是基于"补丁集无 clang 侧改动"的推理。
4. **`abort` 是否真被链接**：取决于 `--gc-sections` 与 nettle-sha256 的不可达分支；未在 DADAO 链接层验证。
5. **`sqrt` 的来源未定**：可用 DADAO 版 libm（不存在）或自备 double `sqrt`（编译器内建 `__builtin_sqrt` 仍需 runtime）；具体落点未决。
6. **Embench `scons` 全套脚本**（`benchmark_speed.py` 需一个 `pylib/run_dadao.py` target 模块）未深究——若走官方测速脚本，需自建 target 模块解析 QEMU 输出/退出码。
7. **Dhrystone 不在本仓库**：任务"先 Dhrystone 打出 correct"的 Dhrystone 来源未在本次分析范围内（`.cache/embench-iot/src/` 无 Dhrystone）。
8. **RAM@0 vs 旧 RAM 的最终链接地址**：`dadao.lds` 链到旧 RAM `0xffff_0000_0000`（在加载白名单内）；若 M6 改为"RAM 从 0 起"，则 `dadao_load_regions[]` 需扩 `RAM@0`（`dadao-machine.c.patch:184-187` 现**不含** RAM@0）——本分析按**现状 16 MiB 够用**给结论，不预判 M6 地址迁移。

---

## 附录 A：证据脚本与临时产物

均在 `/tmp/opencode/embench-analysis/`（非易失证据按需再留 `.work/log/`）：

- `build_size.sh` / `footprint.txt`：逐基准 `gcc -Os` 链接 + `size`（§5.1 表）。
- `free_syms.sh` / `free/`：`-ffreestanding -fno-builtin` 逐基准 + `nm -u`（§3）。
- `be/md5.c`：md5 大端字序模拟（§4.1 反证）。
- 栈：`gcc -fstack-usage`（§5.2）。

## 附录 B：关键文件索引

| 主题 | 文件:行 |
|------|--------|
| 三平台函数 | `support/support.h:35-37`；`doc/README.md:686-690` |
| main 调用序列 | `support/main.c:25-37` |
| 变参 printf 均被宏屏蔽 | `md5.c:103,121`；`nsichneu:43-46`；`slre:34-38` |
| BEEBS 堆 | `support/beebsc.c:93-181`；`sglib:24-25`；`huff:59-60`；`qrduino:27-28` |
| 端序唯一坑 | `md5.c:101` |
| sqrt | `wikisort/libwikisort.c:386` |
| ctype | `slre/libslre.c:24,143,153,184` |
| SCons 变量 | `sconstruct.py:30-38,49-51,59-65,89,96` |
| 加载器零填 .bss / 白名单 | `components/qemu/patches/hw/dadao/dadao-machine.c.patch:184-187,398-422` |
| RAM 尺寸 | `components/qemu/patches/target/dadao/cpu.h.patch:66-72` |
| semihosting 服务表/停机 | `.tao/knowledge/contract-semihosting.md §1-§3,§5` |
| DataLayout | `components/llvm-project/patches/llvm/lib/TargetParser/TargetDataLayout.cpp.patch:11` |
