# INFRA-078t: compiler-rt 支持预研（builtins 缺口 / 符号差 / 接入点 / ADR 草案）

**模块**：infra
**项目里程碑**：M8
**依赖**：无（**只读预研**；`compiler-rt` 源已在 `.work/source/<组件>/compiler-rt/lib/builtins/`，本任务**不下载**新仓库）
**状态**：待验收

> **立项来源**：用户 2026-10-14 裁定「**先预研 + 立 ADR（推荐）**」——即先做本轮机械缺口调查、**只出预研报告 + ADR decision 草案**；**ADR 文件由 architect 另立**（且须用户逐条确认）。
> **本任务为一次调研 spike**：产出「正向/反向缺口 + 符号差 + 接入点 + 策略建议 + ADR 草案」，**不改任何上游/组件/规范文件**（只读 `components/**`、`spec/`、`contracts/`、`manifests/`；只写本任务书与 `.work/**`）。

## 1. 用户裁定（原话，2026-10-14）

- 选项「**先预研 + 立 ADR（推荐）**」✓。
- **范围口径（本任务）**：**只 `builtins`**（不含 sanitizer / profiling / unwind / atomic / crt 独立库）；**ADR 由 architect 另立**。

## 2. 已查证事实（引用，勿重复查证）

- `compiler-rt/lib/builtins/` 顶层 = **182 源**（**181 `.c`** + `addtf3.cpp`）；子目录 `aarch64/ arm/ avr/ hexagon/ i386/ loongarch/ ppc/ riscv/ ve/ x86_64/ cpu_model/` 为各 arch 专属。
- **上游不认识 `dadao`**：`int_lib.h`/`int_types.h`/`int_endianness.h` 无 `__dadao__`/`__DADAO__` 分支（`grep` 0 命中）。
- **字节序已内建、无需改**：`int_endianness.h` 走 `__BYTE_ORDER__ == __ORDER_BIG_ENDIAN__` 双路；我们的 clang `-target dadao-unknown-elf` 定义 `__BIG_ENDIAN__`/`__BYTE_ORDER__=__ORDER_BIG_ENDIAN__` ⇒ `_YUGA_BIG_ENDIAN=1` 正确。
- **long double = 64 bit**：`__SIZEOF_LONG_DOUBLE__=8`、`__LDBL_MANT_DIG__=53` ⇒ `int_types.h` 的 `HAS_80_BIT_LONG_DOUBLE=0`、无 `tf_float`（`CRT_HAS_F128`/`CRT_HAS_TF_MODE` 未定义）⇒ **xf 源不适用、tf 源被预处理掉**（对上游而言**无需改**，只需按 arch 口径排除/保留）。
- **`_Float16`/`__bf16` 前端不支持**：`_Float16`/`__bf16` ⇒ `error: ... is not supported on this target`；无 `__FLT16_*` 宏。
- **`__int128` 支持**：`__SIZEOF_INT128__=16`。
- **已内建大端分支**✓、**我们的工具链不提供 libgcc/compiler-rt builtins**：sysroot `.dadao/dadao-unknown-elf/lib/{libc.a,libm.a,...}` 中**仅**手工移植的 `__mulsc3`/`__muldc3`（`ISS-196`；`INFRA-067t`）——其余编译器内建符号**全无**。
- 已知撞点：`__mulsc3`/`__muldc3`（`ISS-196`，已移植）、i64 `bswap`（`ISS-193`(c)，**open**）、`long double` strtod（`ISS-193`(f)，**open**）。

## 3. 方法（**机械求缺口，禁人肉猜清单**）

| 步骤 | 方法 | 产物（`.work/evidence/<任务ID>/`） |
| --- | --- | --- |
| §4.1 正向 | 12 个覆盖面探针 C（`probes/*.c`）→ `clang -target dadao-unknown-elf -O2 -c` → **链接** sysroot 三库（`ld.lld --unresolved-symbols=report-all`）⇒ 收集 `undefined symbol:` / 编译失败签名 | `lib/probe_gap.py` → `probe-gap.json` |
| §4.2 反向 | **全量**编译 182 源（`-O2 -c`）；**scope 从上游 `CMakeLists.txt` 现场解析**（`GENERIC_SOURCES ∪ GENERIC_TF_SOURCES`）⇒ 区分 core / 非 core | `lib/scan_builtins.py` → `builtins-scan.tsv` / `builtins-summary.json` / `builtins-files.json` |
| §4.3 符号差 | provider = 编出的 `.o` 全局定义符号（`nm --extern-only --defined-only`）；sysroot = `.a` 全局定义符号；`missing = provider \ sysroot`；另与**源级 `COMPILER_RT_ABI` 解析**交叉（区分「源在但编不过」） | `lib/symbol_diff.py` → `symbols-*.txt/json` |
| 证据脚本 | `.work/evidence/<任务ID>/run.sh`（非交互、任一失败非零退出、`--inject` 反例自检） | `run.sh` |

> 探针覆盖：i64 除法/取模、`__int128`（加/减/乘/除/模/常量与变量移位/比较/溢出）、位操作（`clz`/`ctz`/`popcount`/`parity`/`ffs`/`clrsb`）、`bswap16/32/64`、`_Float16`、`_Complex`（乘/除）、`long double`、f32/f64 算术与整数转换、**FP↔i128 转换**、原子/`__sync_*`。

## 4. 产出

### 4.1 正向缺口（我们缺哪些符号 / 哪些操作编不过）

**(a) 编译器已发出、sysroot 缺**（链接期 undefined）：
- **`__divsc3` / `__divdc3`**（`_Complex` **除法**）——**本探针覆盖范围内**唯一「已发出且缺」的内建符号（`__mulsc3`/`__muldc3` 已在 sysroot）。

**(b) 后端连调用都发不出（fatal codegen，`unsupported library call operation` / `Cannot select`）**：
- **i128 除法/取模**（含除常量）：`error in backend: unsupported library call operation` ⇒ 需 `__divti3`/`__udivti3`/`__modti3`/`__umodti3` **且后端须注册**。
- **FP↔i128 转换（8 种）**：同签名 ⇒ 需 `__fixdfti`/`__fixsfti`/`__fixunsdfti`/`__fixunssfti`/`__floattidf`/`__floattisf`/`__floatuntidf`/`__floatuntisf`。
- **`bswap`**：`Cannot select: ... = bswap` ⇒ 需 `__bswapdi2`/`__bswapsi2` 或 `ISD::BSWAP` Expand。
- **i128 变址移位**：`Cannot select: ... shl_parts` ⇒ 需 `ISD::SHL_PARTS`/`SRL_PARTS`/`SRA_PARTS` lowering。
- **原子操作**：`Cannot select: AtomicLoad/AtomicStore/AtomicLoadAdd/AtomicFence` ⇒ 后端无原子支持（**可能超出 builtins 范围**）。
- **`_Float16`/`__bf16`**：**前端拒绝**（f16 builtins 源可编、但在 C 层不可达）。

**(c) 无缺口**：i64 除法/取模（**原生 `div.uo`**，`p01` 无 libcall）、i128 加/减/乘/比较/常量移位、位操作（clz/ctz/popcount/ffs）、`long double`（算术/转换；`ISS-193`(f) 的 strtod 属另一构造、未在本探针覆盖）、f32/f64 算术与整数转换、`_Complex` 乘法（已在 sysroot）。

### 4.2 反向缺口（compiler-rt 哪些编不过）

- scope（`GENERIC_SOURCES ∪ GENERIC_TF_SOURCES`）**现场统计 = 146**：**OK 133 / FAIL 13**。
- **13 个 core FAIL 全部归 3 类**（无未分类）：
  - `bswap`（2）：`bswapdi2.c`、`bswapsi2.c`
  - `shl_parts`（9）：`fixdfti.c`、`fixsfti.c`、`fixunsdfti.c`、`fixunssfti.c`、`floattidf.c`、`floattisf.c`、`floatuntidf.c`、`floatuntisf.c`、`udivmodti4.c`
  - `unsupported library call operation`（2）：`muloti4.c`、`mulvti3.c`（内含 i128 除法）
- **非 core FAIL = 26** = **xf（14） + atomic（7） + bfloat16（2） + `crtbegin.c` + `emutls.c` + `addtf3.cpp`**（前者按上游 arch/平台口径排除或属独立库；`addtf3.cpp` 的 FAIL **仅因 scan 未带 `lib/shared` include 路径，非真实缺口**）。
- **freestanding 抽查（10 个 `__builtin`/hw 相关 OK 源）**：`adddf3.c`/`clzdi2.c`/`udivmoddi4.c`/`truncdfsf2.c`/`extendhfsf2.c`/`negti2.c`/`popcountti2.c`/`fp_mode.c`/`mulsf3.c`/`cmpdi2.c` ⇒ **undefined 全在 builtins provider 集合内**（唯一跨文件依赖 = `adddf3.c` → 库内 `fp_mode.c` 的 `__fe_getround`/`__fe_raise_inexact`）；**唯三引 libc 的源**（`enable_execute_stack.c`→`mprotect`/`sysconf`、`eprintf.c`→`fprintf`/`fflush`/`stderr`、`int_util.c`→`abort`）**均非 core**。

### 4.3 符号表求差

- **provider（编得出现今）= 129**；**sysroot 提供 = 1306**；**`missing = provider \ sysroot` = 126**；**`source_only`（源级解析但编不出）= 66**。
- 交叉验证（与 §4.1 一致）：`source_only` 含 `__bswapdi2`/`__bswapsi2`/`__muloti4`/`__mulvti3`/`__udivmodti4`（**源在、编不过**）；`__divsc3`/`__divdc3`/`__divti3`/`__udivti3`/`__modti3`/`__umodti3`/`__multi3` 在 `missing`；`__mulsc3`/`__muldc3` **不在** `missing`（已由 sysroot 提供）。
- **结论**：即使只补 builtins 库、不动后端，**今天可编出的那 129 个符号里仍有 126 个 sysroot 缺**；其中真正被编译器「按需发出」的是 §4.1(a)/(b) 所列。

### 4.4 接入需改的上游点（逐条）

1. **`DADAOSubtarget::initLibcallLoweringInfo`（后端）**：注册 i128 除法/取模 libcall（`RTLIB::SDIV_I128`/`UDIV_I128`/`SREM_I128`/`UREM_I128` ⇒ `impl___divti3` 等）。**根因**：`LibcallLoweringInfo` 默认全 `Unsupported`，只有 `Subtarget.initLibcallLoweringInfo` 注册过的才可用；而 `setTargetRuntimeLibcallSets` **无 `else` 分支**，非表内 arch（dadao）可用集为空。
2. **同上**：注册 FP↔i128 转换 libcall（8 个 `RTLIB::*_I128`）。
3. **`DADAOISelLowering`（后端）**：实现 `ISD::SHL_PARTS`/`SRL_PARTS`/`SRA_PARTS`（i128 变址移位 / i128↔FP 与 `udivmodti4` 的公共根因）。
4. **bswap（后端）**：`setOperationAction(ISD::BSWAP, MVT::i64/i32, Expand)`（通用展开）**或**注册 `__bswapdi2`/`__bswapsi2` libcall。
5. **原子（后端，可能超范围）**：AtomicLoad/Store/RMW/Fence 的 libcall 或原生 lowering。
6. **compiler-rt 构建**：`CMakeLists.txt` 增 **`dadao` arch 分支**（源 = `GENERIC_SOURCES` + `GENERIC_TF_SOURCES` + arch `fp_mode`；补 `-DCRT_HAS_INITFINI_ARRAY` 供 `crtbegin.c`）；`emutls.c`（需 `pthread.h`）按需排除。
7. **无需改**：`int_endianness.h`（BE 已覆盖）；`int_types.h` 的 `HAS_80_BIT_LONG_DOUBLE`（对我们的 target 天然 0，xf 源按 arch 排除即可）。

### 4.5 范围与成本（**建议 / 估算**）

- **范围（建议）**：只纳入 **builtins**（`GENERIC_SOURCES ∪ GENERIC_TF_SOURCES`，本机 **133/146 已可编**）；xf / bfloat16 / atomic / crt / emutls **排除**（前者不适用，后者属独立库）。
- **策略（建议）**：**先全走通用 C 实现（正确优先）**——上游 builtins 即纯 C、已 freestanding；**hw 特化（`bswap`/`clz` 等）后置**，待通用路径跑通且有收益再议。
- **成本（估算，未实测）**：库本身 = 146 源一次性编译（本机全量 < 1 min）；**人力主要在 5 个后端改动点**（§4.4 #1–#5），其中 #1/#2 属「一次改动即解锁一批符号」。

### 4.6 验证策略（**建议**）

- **代表集 + 独立 oracle**：对每个纳入的 builtin 用**独立派生**的期望值（如整数内建的位级真值、FP 的半精度舍入真值），**禁从自身实现反推**；可复用现有 `tests/vectors/` + lit 向量模式与 ISA 编码 oracle。
- 可复用 `tools/testcases/picolibc_tests.py` 的「编译 + 运行 + 断言」范式做端到端冒烟。

## 5. ADR decision 草案（**只提案，不写 ADR 文件**；architect 落地且**须用户逐条确认**）

| # | 决策（建议） | 理由 | 被否方案（及原因） |
| --- | --- | --- | --- |
| **D1** | **范围 = 只 `builtins`**（不含 sanitizer / profiling / unwind / atomic / crt） | 编译器内建是本轮实际撞点；其余库各自独立、当前无消费方 | 全 compiler-rt 一次接入 ⇒ 超需、验证面爆炸 |
| **D2** | **上游形态 = llvm-project 补丁**（`components/llvm-project/patches/compiler-rt/**`） | 与既有 A 类补丁面（`INFRA-067t` 已移植 `mulsc3`/`muldc3`）同源同版本锁；`LLVM-091t` 刚验证过补丁面可控 | 独立组件 ⇒ 需新锁源/新版本对齐，且与 llvm-project 版本易漂移 |
| **D3** | **实现策略 = 通用 C 优先、hw 特化后置** | 上游 builtins 即纯 C、freestanding、正确性优先；hw 收益未量化 | 直接上 hw 特化 ⇒ 先付出验证成本而无数据支撑（避免过度设计） |
| **D4** | **验证口径 = 代表集 + 独立 oracle** | `GENERIC` 全集 146 源逐一手测不现实；内建语义须**独立派生**（nonzero 判据 = 真值表/位级真值），防止从自身实现反推 | 全量逐源人工核对 ⇒ 成本不可接受；直接信上游 ⇒ 违反 independent-oracle |
| **D5** | **与 libc 的分工 = builtins 独立、picolibc/musl 共用** | builtins 为编译器内建、语义与 libc 无关；`picolibc`（当前）/`musl`（M8 主线）应共用同一份，避免重复移植（正是 `INFRA-067t` 手工 vendor 不可持续的反面） | 每个 libc 各自 vendor ⇒ 重复且漂移（既有痛点） |

> **备注（需用户裁定）**：D2 若选「独立组件」，D5 的「共用」实现方式亦变；D1 是否把 **atomic**（本机 7 源全编不过、`ISS-193` 未涵盖）纳入，须用户裁定。

## 6. 任务书自包含说明

本任务书**自包含**：含**用户原话**（§1）、上游/工具链**事实**（§2）、**方法**与产物路径（§3）、**产出**（§4）、**ADR 草案**（§5）；执行不需依赖外部仓库内容。**范围只 builtins；ADR 由 architect 另立**。

## 接口规范

- **输入**：用户裁定（§1）；`.work/source/<组件>/compiler-rt/lib/builtins/`（只读）；`.dadao/` 工具链 + sysroot（只读）；`contracts/opcodes.yaml`（只读）。
- **输出**：本预研报告（§2–§5，**落本任务书**）+ 证据脚本与原始产物（`.work/evidence/<任务ID>/`）+ 日志（`.work/log/<模块>/`，一次性过程）。
- **越界声明**：**未改** `components/**`、`spec/`、`contracts/`、`manifests/`、`.tao/adr/`；只新增本任务书 + `.work/**`。

## 验收标准

1. 任务书含**用户裁定原话**（§1）、`**状态**` = `待验收`、`**项目里程碑**` = `M8`。
2. §4.1 正向缺口**逐符号**给出（含来源证据：探针 → `nm -u` / 链接器 `undefined symbol` / 后端失败签名）；§4.2 给出**编不过文件数 + 失败签名分类**；§4.3 给出**符号差**并与 §4.1/§4.2 交叉。
3. 计数**现场统计、不写死**（scope 从上游 CMakeLists 现场解析）。
4. §4.4 接入点**逐条**、§4.5/§4.6 **标「建议/估算」**；§5 ADR 草案**逐条给理由 + 被否方案**、**只提案**。
5. 门控：`make check`、`check-knowledge-refs`、`check-no-residue` **各 rc=0**（`check_issues.py` 含于 `make check`）。
6. 证据脚本 `.work/evidence/<任务ID>/run.sh`：非交互、**任一失败非零退出**、逐项打印「检查名 + 期望/实际 + rc」、**含注入反例→FAIL→还原→回绿**自检。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-078t/`；命令一律在 workdir（= 仓库根）内、相对路径；**禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. **只读预研**：不改上游/组件/规范（§接口规范「越界声明」）。
5. **事实与推测分开**；**计数不写死**；文本不写 `.work/<具体路径>` 字面（用 `<>` 占位）。
6. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。

## 完成区

**测试结果**：证据脚本 `./.work/evidence/<任务ID>/run.sh` **全绿 rc=0**（A1–A6）；`--inject` 亦 **rc=0**（**5 条注入均触发可达 FAIL**、2 处 `cp`+md5 还原一致）。编译耗时：182 源全量 **约 12 s**；证据脚本（无注入）**实测 50 s**、含注入 **实测 105 s**（未触发长任务阈值）。
**修改文件**：`.tao/tasks/infra/INFRA-078t-compiler-rt支持预研.md`（新增）；`.work/evidence/<任务ID>/**`（新增：`run.sh` + `lib/*.py` + `probes/*.c` + `baseline/*`）；`.work/log/<模块>/INFRA-078t-*.log`。
**验收结果**：门控——`make check` **rc=0**、`check-knowledge-refs` **rc=0**、`check-no-residue` **rc=0**（日志 `.work/log/<模块>/INFRA-078t-<目标>.log`）；A1–A6 逐项 PASS（现场实测值见 `run.sh` 输出，非写死）。
**新发现/坑**：① **`LibcallLoweringInfo` 默认全 `Unsupported`**，且 `setTargetRuntimeLibcallSets` **无 `else` 分支** ⇒ 非表内 arch（dadao）可用 libcall 集为空，**任何** backend libcall 都须在 `initLibcallLoweringInfo` 显式注册（解释 i128 除法/FP↔i128 的 fatal codegen）。② `int_endianness.h` **已由 `__BYTE_ORDER__` 覆盖大端、无需改**（订正「需改 `__BYTE_ORDER__`」的初步假设）。③ `long double`=64bit ⇒ xf 源不适用、tf 源被预处理掉；`_Float16`/`__bf16` 前端不支持。④ `shl_parts`（`ISD::SHL_PARTS`）= i128 变址移位 / i128↔FP / `udivmodti4` 的**公共根因**。⑤ 上游 builtins **133/146 已可编**且 freestanding（唯三引 libc 的源均非 core）。
**遗留问题**：① **ADR（compiler-rt 上游纳入方式）由 architect 另立、须用户逐条确认**（§5 仅提案）。② §4.5 成本为**估算**（未实测后端改动量）。③ §4.4 #5（atomic）**是否纳入范围**待用户裁定。④ `addtf3.cpp` 的 FAIL 系 scan 未带 `lib/shared` include 路径（**非真实缺口**，如实登记）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：`run.sh` + `lib/{scan_builtins,symbol_diff,probe_gap}.py` + `probes/*.c` + 本任务书。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 `probe_gap.py` 调 `nm` 未定义 | ✅已修 | 新增 `nm()` 包装 | `run.sh` A1/A2 PASS（rc=0） |
| F2 `symbol_diff.py` 未 `mkdir` 输出目录 | ✅已修 | 加 `out.mkdir(parents=True)` | A4 PASS |
| F3 源级符号解析误纳 `__CTOR_LIST_END__` 等（跨行匹配） | ✅已修 | 正则收紧为 `[^;{()]*?` + 去注释 | provider=129（原 215 含伪符号） |
| F4 A4 预期值误把「源在但编不过」的 `__bswapdi2` 当作「sysroot 缺」 | ✅已修 | A4 拆「buildable-now missing」与「source-only」两集 | A4 PASS（`not_anywhere=[]`） |
| F5 A5 原为恒真（未真查 undefined） | ✅已修 | 改为「抽样 10 源、每源 undefined ⊆ provider」 | A5 PASS；注入「`adddf3.c` 引 `printf`」⇒ A5 **FAIL**（可达路径已证） |
| F6 `p05_f16.c` 用 `#ifdef __FLT16_MANT_DIG__` 使探针空跑 | ✅已修 | 改为无守卫显式 `_Float16`（前端拒绝可测） | A2 `float16-unsupported` 类命中 |
| F7 run.sh 内联的 A3 注入误读非注入产物 | ✅已修 | `assert_scan` 接受路径参数、指向 `scan-inj` | `I[bswapdi2.c-removed]` PASS |
| F8 A4/A5 缺可达 FAIL 路径证明 | ✅已修 | 二者加路径参数 + `--inject` 输入级注入 | `I[drop-__divsc3-from-missing]`、`I[adddf3-uses-printf]` 均 PASS（断言 FAIL 可复现） |

**判决**：全部 finding 已修；**无未修项**。**状态 = 待验收**。
