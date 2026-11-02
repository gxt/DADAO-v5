# INFRA-078t: compiler-rt 支持预研（builtins 缺口 / 符号差 / 接入点 / ADR 草案）

**模块**：infra
**项目里程碑**：M8
**依赖**：无（**只读预研**；`compiler-rt` 源已在 `.work/source/<组件>/compiler-rt/lib/builtins/`，本任务**不下载**新仓库）
**状态**：已验证

> **立项来源**：用户 2026-10-14 裁定「**先预研 + 立 ADR（推荐）**」——即先做本轮机械缺口调查、**只出预研报告 + ADR decision 草案**；**ADR 文件由 architect 另立**（且须用户逐条确认）。
> **本任务为一次调研 spike**：产出「正向/反向缺口 + 符号差 + 接入点 + 策略建议 + ADR 草案」，**不改任何上游/组件/规范文件**（只读 `components/**`、`spec/`、`contracts/`、`manifests/`；只写本任务书与 `.work/**`）。

## 1. 用户裁定（原话，2026-10-14）

- 选项「**先预研 + 立 ADR（推荐）**」✓。
- **范围口径（本任务）**：**只 `builtins`**（不含 sanitizer / profiling / unwind / atomic / crt 独立库）；**ADR 由 architect 另立**。

## 2. 已查证事实（引用，勿重复查证）

- `compiler-rt/lib/builtins/` 顶层 = **182 源**（**181 `.c`** + `addtf3.cpp`）；子目录 `aarch64/ arm/ avr/ hexagon/ i386/ loongarch/ ppc/ riscv/ ve/ x86_64/ cpu_model/` 为各 arch 专属。
- **上游不认识 `dadao`**：`int_lib.h`/`int_types.h`/`int_endianness.h` 无 `__dadao__`/`__DADAO__` 分支（`grep` 0 命中）。
- **字节序已内建、无需改**：`int_endianness.h` 走 `__BYTE_ORDER__ == __ORDER_BIG_ENDIAN__` 双路；我们的 clang `-target dadao-unknown-elf` 定义 `__BIG_ENDIAN__`/`__BYTE_ORDER__=__ORDER_BIG_ENDIAN__` ⇒ `_YUGA_BIG_ENDIAN=1` 正确。
- **long double = 64 bit**：`__SIZEOF_LONG_DOUBLE__=8`、`__LDBL_MANT_DIG__=53` ⇒ `int_types.h` 的 `HAS_80_BIT_LONG_DOUBLE=0`、无 `tf_float`（`CRT_HAS_F128`/`CRT_HAS_TF_MODE` 未定义）⇒ **xf 源不适用；tf `.c` 源被预处理掉**（`CRT_HAS_TF_MODE` 未定义，函数体不参与编译；唯 `addtf3.cpp` 例外，见 §4.2）（对上游而言**无需改**，只需按 arch 口径排除/保留）。
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
- **原子操作**：`Cannot select: AtomicStore/AtomicSwap/AtomicLoadAdd/AtomicFence` ⇒ 后端无原子 RMW/fence lowering（**可能超出 builtins 范围**）；简单原子 load 可正常 lower（`_Atomic` load 编译 rc=0），故失败例中**无** `AtomicLoad`。
- **`_Float16`/`__bf16`**：**前端拒绝**（f16 builtins 源可编、但在 C 层不可达）。

**(c) 无缺口**：i64 除法/取模（**原生 `div.uo`**，`p01` 无 libcall）、i128 加/减/乘/比较/常量移位、位操作（clz/ctz/popcount/ffs）、`long double`（算术/转换；`ISS-193`(f) 的 strtod 属另一构造、未在本探针覆盖）、f32/f64 算术与整数转换、`_Complex` 乘法（已在 sysroot）。

### 4.2 反向缺口（compiler-rt 哪些编不过）

- scope（`GENERIC_SOURCES ∪ GENERIC_TF_SOURCES`）**现场统计 = 146**：**OK 133 / FAIL 13**。
- **13 个 core FAIL 全部归 3 类**（无未分类）：
  - `bswap`（2）：`bswapdi2.c`、`bswapsi2.c`
  - `shl_parts`（9）：`fixdfti.c`、`fixsfti.c`、`fixunsdfti.c`、`fixunssfti.c`、`floattidf.c`、`floattisf.c`、`floatuntidf.c`、`floatuntisf.c`、`udivmodti4.c`
  - `unsupported library call operation`（2）：`muloti4.c`、`mulvti3.c`（内含 i128 除法）
- **非 core FAIL = 26** = **xf（14） + atomic（7） + bfloat16（2） + `crtbegin.c` + `emutls.c` + `addtf3.cpp`**（前者按上游 arch/平台口径排除或属独立库；`addtf3.cpp` 的 FAIL **是否真实缺口未定**：include 根应为 `llvm-project/libc/`（上游**无** `lib/shared` 目录），补上后**仍 rc=1**，尚需 `LIBC_NAMESPACE`/`COMPILER_RT_USE_LIBC_MATH` 构建上下文——该源**非 core**（tf 的 **`.c`** 源因 `CRT_HAS_TF_MODE` 未定义被预处理掉、不参与编译；但 `addtf3.cpp` **本身不被预处理掉**：其函数体存活、参与编译并 rc≠0，见第 3 轮 F-R3）⇒ **不计入 core 缺口**）。
- **freestanding 抽查（10 个 `__builtin`/hw 相关 OK 源）**：`adddf3.c`/`clzdi2.c`/`udivmoddi4.c`/`truncdfsf2.c`/`extendhfsf2.c`/`negti2.c`/`popcountti2.c`/`fp_mode.c`/`mulsf3.c`/`cmpdi2.c` ⇒ **undefined 全在 builtins provider 集合内**（唯一跨文件依赖 = `adddf3.c` → 库内 `fp_mode.c` 的 `__fe_getround`/`__fe_raise_inexact`）；**唯三引 libc 的源**：`enable_execute_stack.c`（→`mprotect`/`sysconf`）与 `eprintf.c`（→`fprintf`/`fflush`/`stderr`）**非 core**（上游仅在 `NOT FUCHSIA AND NOT COMPILER_RT_BAREMETAL_BUILD AND NOT COMPILER_RT_GPU_BUILD` 条件下追加进 `GENERIC_SOURCES`）；而 **`int_util.c` 属 `GENERIC_SOURCES`（core）**，其 `__compilerrt_abort_impl`（weak）引 **`abort`** ⇒ **core 源引 libc，接入时该符号须由环境提供**（影响 `INFRA-079t` freestanding 预期）。

### 4.3 符号表求差

- **provider（编得出现今）= 129**；**sysroot 提供 = 1306**；**`missing = provider \ sysroot` = 126**；**`source_only`（源级解析但编不出）= 66**。
- 交叉验证（与 §4.1 一致）：`source_only` 含 `__bswapdi2`/`__bswapsi2`/`__muloti4`/`__mulvti3`/`__udivmodti4`（**源在、编不过**）；`__divsc3`/`__divdc3`/`__divti3`/`__udivti3`/`__modti3`/`__umodti3`/`__multi3` 在 `missing`；`__mulsc3`/`__muldc3` **不在** `missing`（已由 sysroot 提供）。
- **结论**：即使只补 builtins 库、不动后端，**今天可编出的那 129 个符号里仍有 126 个 sysroot 缺**；其中真正被编译器「按需发出」的是 §4.1(a)/(b) 所列（**限本探针覆盖范围**）。

### 4.4 接入需改的上游点（逐条）

1. **`DADAOSubtarget::initLibcallLoweringInfo`（后端）**：注册 i128 除法/取模 libcall（`RTLIB::SDIV_I128`/`UDIV_I128`/`SREM_I128`/`UREM_I128` ⇒ `impl___divti3` 等）。**根因**：`LibcallLoweringInfo` 默认全 `Unsupported`，只有 `Subtarget.initLibcallLoweringInfo` 注册过的才可用；而 `setTargetRuntimeLibcallSets` **无 `else` 分支**，非表内 arch（dadao）可用集为空。
2. **同上**：注册 FP↔i128 转换 libcall（8 个 `RTLIB::*_I128`）。
3. **`DADAOISelLowering`（后端）**：实现 `ISD::SHL_PARTS`/`SRL_PARTS`/`SRA_PARTS`（i128 变址移位 / i128↔FP 与 `udivmodti4` 的公共根因）。
4. **bswap（后端）**：`setOperationAction(ISD::BSWAP, MVT::i64/i32, Expand)`（通用展开）**或**注册 `__bswapdi2`/`__bswapsi2` libcall。
5. **原子（后端，可能超范围）**：Atomic RMW/Fence 的 libcall 或原生 lowering（简单原子 load 已可 lower）。
6. **compiler-rt 构建**：`CMakeLists.txt` 增 **`dadao` arch 分支**（源 = `GENERIC_SOURCES` + `GENERIC_TF_SOURCES`（通用 `fp_mode.c` 已在 `GENERIC_SOURCES`，dadao 无需 arch `fp_mode`）；补 `-DCRT_HAS_INITFINI_ARRAY` 供 `crtbegin.c`）；`emutls.c`（需 `pthread.h`）按需排除。
7. **无需改**：`int_endianness.h`（BE 已覆盖）；`int_types.h` 的 `HAS_80_BIT_LONG_DOUBLE`（对我们的 target 天然 0，xf 源按 arch 排除即可）。

### 4.5 范围与成本（**建议 / 估算**）

- **范围（建议）**：只纳入 **builtins**（`GENERIC_SOURCES ∪ GENERIC_TF_SOURCES`，本机 **133/146 已可编**）；xf / bfloat16 / atomic / crt / emutls **排除**（前者不适用，后者属独立库）。
- **策略（建议）**：**先全走通用 C 实现（正确优先）**——上游 builtins 几乎全为 C（182 顶层源中 181 `.c`，余 1 为 `addtf3.cpp`），**库外依赖仅一处**（core 源 `int_util.c`→`abort`；本机 `-ffreestanding` 下亦仍引 `abort`，见 §4.2）；**hw 特化（`bswap`/`clz` 等）后置**，待通用路径跑通且有收益再议。
- **成本（估算，未实测）**：库本身 = 146 源一次性编译（本机全量 < 1 min）；**人力主要在 5 个后端改动点**（§4.4 #1–#5），其中 #1/#2 属「一次改动即解锁一批符号」。

### 4.6 验证策略（**建议**）

- **代表集 + 独立 oracle**：对每个纳入的 builtin 用**独立派生**的期望值（如整数内建的位级真值、FP 的半精度舍入真值），**禁从自身实现反推**；可复用现有 `tests/vectors/` + lit 向量模式与 ISA 编码 oracle。
- 可复用 `tools/testcases/picolibc_tests.py` 的「编译 + 运行 + 断言」范式做端到端冒烟。

## 5. ADR decision 草案（**只提案，不写 ADR 文件**；architect 落地且**须用户逐条确认**）

| # | 决策（建议） | 理由 | 被否方案（及原因） |
| --- | --- | --- | --- |
| **D1** | **范围 = 只 `builtins`**（不含 sanitizer / profiling / unwind / atomic / crt） | 编译器内建是本轮实际撞点；其余库各自独立、当前无消费方 | 全 compiler-rt 一次接入 ⇒ 超需、验证面爆炸 |
| **D2** | **上游形态 = llvm-project 补丁**（`components/llvm-project/patches/compiler-rt/**`） | 与既有 A 类补丁面（`INFRA-067t` 已移植 `mulsc3`/`muldc3`）同源同版本锁；`LLVM-091t` 刚验证过补丁面可控 | 独立组件 ⇒ 需新锁源/新版本对齐，且与 llvm-project 版本易漂移 |
| **D3** | **实现策略 = 通用 C 优先、hw 特化后置** | 上游 builtins 几乎全为 C（含 1 个 `addtf3.cpp`）、正确性优先（库外依赖仅 core 源 `int_util.c`→`abort`，接入须环境提供）；hw 收益未量化 | 直接上 hw 特化 ⇒ 先付出验证成本而无数据支撑（避免过度设计） |
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

**测试结果**：证据脚本 `./.work/evidence/<任务ID>/run.sh` **全绿 rc=0**（A1–A6）；`--inject` 亦 **rc=0**（**5 条注入均触发可达 FAIL**、2 处 `cp`+md5 还原一致）。编译耗时：182 源全量 **约 12 s**；证据脚本（无注入）**实测 50 s**、含注入 **实测 105 s**（未触发长任务阈值）。（第 3 轮为**文本订正**、**未重跑** `run.sh`；门控三连见下。）
**修改文件**：`.tao/tasks/infra/INFRA-078t-compiler-rt支持预研.md`（新增）；`.work/evidence/<任务ID>/**`（新增：`run.sh` + `lib/*.py` + `probes/*.c` + `baseline/*`）；`.work/log/<模块>/INFRA-078t-*.log`。
**验收结果**：门控——`make check` **rc=0**、`check-knowledge-refs` **rc=0**、`check-no-residue` **rc=0**（日志 `.work/log/<模块>/INFRA-078t-<目标>.log`）；A1–A6 逐项 PASS（现场实测值见 `run.sh` 输出，非写死）。
**新发现/坑**：① **`LibcallLoweringInfo` 默认全 `Unsupported`**，且 `setTargetRuntimeLibcallSets` **无 `else` 分支** ⇒ 非表内 arch（dadao）可用 libcall 集为空，**任何** backend libcall 都须在 `initLibcallLoweringInfo` 显式注册（解释 i128 除法/FP↔i128 的 fatal codegen）。② `int_endianness.h` **已由 `__BYTE_ORDER__` 覆盖大端、无需改**（订正「需改 `__BYTE_ORDER__`」的初步假设）。③ `long double`=64bit ⇒ xf 源不适用、tf **`.c`** 源被预处理掉（`addtf3.cpp` **例外**：非 core 但函数体存活、参与编译）；`_Float16`/`__bf16` 前端不支持。④ `shl_parts`（`ISD::SHL_PARTS`）= i128 变址移位 / i128↔FP / `udivmodti4` 的**公共根因**。⑤ 上游 builtins **133/146 已可编**；freestanding 例外 = **core 源 `int_util.c` 的 `__compilerrt_abort_impl` 引 `abort`**（`-ffreestanding` 下 `__builtin_trap()` 本机亦 lower 成 `abort` 调用、依赖仍在 ⇒ **接入时须由环境提供**），另 `enable_execute_stack.c`/`eprintf.c` 引 libc 但**非 core**、`gcc_personality_v0.c` 引 `_Unwind_*`（属 unwind，非 builtins provider）。
**遗留问题**：① **ADR（compiler-rt 上游纳入方式）由 architect 另立、须用户逐条确认**（§5 仅提案）。② §4.5 成本为**估算**（未实测后端改动量）。③ §4.4 #5（atomic）**是否纳入范围**待用户裁定。④ `addtf3.cpp` 的 FAIL **是否真实缺口未定**：include 根应为 `llvm-project/libc/`（上游**无** `lib/shared`），补上后**仍 rc=1**（`use of undeclared identifier '__llvm_libc_rt'`，需 `LIBC_NAMESPACE`/`COMPILER_RT_USE_LIBC_MATH` 构建上下文）；该源**非 core**（tf 的 `.c` 源被预处理掉，但 `addtf3.cpp` 本身不被预处理掉——函数体存活、参与编译）；如实登记，**不作「非真实缺口」定性**。

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

#### 第 1 轮 reviewer 审阅

**重跑记录**（workdir=仓库根，全部本人实测）：
- `./.work/evidence/INFRA-078t/run.sh` ⇒ **rc=0**：A1 `['__divdc3','__divsc3'] subset of 同集`、A2 `all 5 classes present`、A3 `core_total=146 core_ok=133 core_fail=13 unknown_sigs=[] missing_reps=[]`、A4 `missing=126 provider=129 sysroot=1306 source_only=66 not_anywhere=[]`、A5 `sampled 10 offending={}`、A6 三门控 `PASS(rc=0)`。
- `--inject` ⇒ **rc=0**：5 条注入均 `PASS (FAILed, reachable path proven)`，2 处 `cp`+md5 还原 `42768bc8…/9b97d025…` 与注入前一致。
- **新反例注入（不在原 5 条内）**：`cp` 备份 `p05_f16.c`（md5 `610161f2…`）→ 换成无 `_Float16` 体 ⇒ run.sh **rc=1**、`A2 FAIL (missing ['float16-unsupported'])` ⇒ `cp` 还原、md5 相等 `RESTORE-MD5-MATCH` ⇒ 重跑 **rc=0 全绿**。
- **独立重算（不沿用 baseline/lib）**：自建 `/tmp/opencode/INFRA-078t/review/indep_scan.sh` 全量编 182 源 ⇒ `core=146 OK=133 FAIL=13 noncore_FAIL=26`（=xf14+atomic7+bfloat16 2+crtbegin+emutls+addtf3.cpp ✓）；13 core FAIL 签名独立分类 = `bswap 2 / shl_parts 9 / unsupported library call operation 2`、无未分类 ✓。自跑 `nm`：`provider=129 sysroot=1306 missing=126 source_only=66` ✓；`__divsc3/__divdc3/__divti3/__udivti3/__modti3/__umodti3/__multi3 ∈ missing`、`__mulsc3/__muldc3 ∈ sysroot` ✓。自编探针：cdiv ⇒ `U __divsc3/__divdc3`；i128 div/FP↔i128 ⇒ `unsupported library call operation`；bswap ⇒ `Cannot select … bswap`；i128 变址移位 ⇒ `shl_parts`；i64 div ⇒ 无 libcall ✓（§4.1/§4.2/§4.3 结论一致）。
- 门控独立跑：`make check/check-knowledge-refs/check-no-residue` 各 **rc=0**；`git status --porcelain -uall` **空**（`.work/` ignored，无残留）。
- 脚本质量：断言 A1–A5 均有可达 FAIL（A1/A2/A3/A4/A5 实测可红）；无 `cmd | tee` 吞码（A6 用 `make >log 2>&1; rc=$?`）；收尾按 `FAILED` 显式 `exit 0/1`，无 echo 假绿。计数均现场统计。

| finding | 判据 | 真实证据 |
| --- | --- | --- |
| F-R1 §4.2「唯三引 libc 的源…**均非 core**」与完成区⑤ 同句**不实**：`int_util.c` **是 core** | 描述须与真实数据一致（硬约束 3/5） | `CMakeLists.txt:152 int_util.c ∈ GENERIC_SOURCES`；engineer 自产 `builtins-files.json`：`int_util.c in_core=True undefined=['abort']`；本人 `nm -u` 复核 `U abort` ⇒ core 源引 libc `abort`，影响 INFRA-079t freestanding 预期 |
| F-R2 遗留④「addtf3.cpp FAIL 仅因 scan 未带 `lib/shared` include 路径、非真实缺口」**定性证据不足** | 事实与推测分开（硬约束 5） | 实测：include 根应为 `llvm-project/libc/`（头在 `libc/shared/builtins/addtf3.h`，**无** `lib/shared`）；补 `-I …/libc` 后**仍 rc=1**（`use of undeclared identifier '__llvm_libc_rt'`，还需 `LIBC_NAMESPACE` 构建上下文）⇒ 「非真实缺口」未被证明 |
| 其余 | — | §1/§4.1/§4.2 核数/§4.3/§4.4/§4.5-4.6「建议/估算」标注/§5 只提案、逐条理由+被否方案：**核对通过**；与 `adr-0027 D1–D5` **一致**（ADR 为用户逐条确认后的细化：D4 补端序用例、ISA→SPEC-141t，无偏差） |

**判决**：**Needs Revision** —— 验收标准 1–6 与门控均通过、脚本/注入/独立重算全对；但 §4.2/完成区⑤/遗留④ 含**与真实数据矛盾的定性结论**（F-R1）与**未经证明的定性**（F-R2）。
**必须修（仅文本，不改脚本/数据）**：① §4.2 与完成区⑤：删/改「均非 core」——改为「`enable_execute_stack.c`/`eprintf.c` 非 core；**`int_util.c` 为 core 且 `__compilerrt_abort_impl` 引 `abort`**（接入时须由环境提供）」；② 遗留④：改为「include 根为 `libc/` 且还需 `LIBC_NAMESPACE` 构建上下文，**是否真实缺口未定**（addtf3.cpp 非 core、tf 对本 target 预处理掉）」。
**状态 = 待返工**（本轮核验证据：`/tmp/opencode/INFRA-078t/review/`，日志 `run1/run2-inject/run3-newinject/run4-backgreen/indep.log`）。

#### 第 2 轮 engineer 返工

**对象**：F-R1（§4.2/完成区⑤「均非 core」不实）、F-R2（遗留④「非真实缺口」未证）。**独立复核（workdir=仓库根，本人实测）**：

**F-R1 复核**（`<B>` = `compiler-rt/lib/builtins`）：
- `grep -n int_util <B>/CMakeLists.txt` ⇒ `152: int_util.c`，落在 `set(GENERIC_SOURCES`(L85)…`)`(L206) **区间内** ⇒ **core**。
- 独立编译：`.dadao/cross-toolchain/bin/clang -target dadao-unknown-elf -O2 -I <B> -c int_util.c` ⇒ **rc=0**；`nm --extern-only --defined-only` ⇒ `W __compilerrt_abort_impl`；`nm -u` ⇒ `U abort`；`llvm-objdump -r` ⇒ `R_DADAO_REL26 abort`。
- 追加：加 `-ffreestanding`（`__STDC_HOSTED__=0`）的产物与不加**字节相同**（md5 皆 `ef660f38…`）且**仍引 `abort`** ⇒ core 源对 `abort` 的依赖**与 freestanding 无关**（该 target 的 trap 亦 lower 成 `abort` 调用）。
- 同源扫描产物：`int_util.c in_core=True undefined=['abort']`；`enable_execute_stack.c`/`eprintf.c` `in_core=False`（上游仅 `NOT FUCHSIA AND NOT COMPILER_RT_BAREMETAL_BUILD AND NOT COMPILER_RT_GPU_BUILD` 时追加，L278–283）。
- **改动**：§4.2 该句 ⇒ 「`enable_execute_stack.c`/`eprintf.c` **非 core**；**`int_util.c` 属 `GENERIC_SOURCES`（core）**，其 `__compilerrt_abort_impl`（weak）引 `abort` ⇒ 接入时须由环境提供」；完成区⑤ 同步。

**F-R2 复现**：
- `addtf3.h` 实位于 `<llvm-project>/libc/shared/builtins/addtf3.h`；`<llvm-project>/lib/shared` **不存在**（`ls` = No such file or directory）。
- `clang -target dadao-unknown-elf -O2 -I <B> -c addtf3.cpp` ⇒ **rc=1**（`fatal error: 'shared/builtins/addtf3.h' file not found`）。
- 补 `-I <llvm-project>/libc` ⇒ **仍 rc=1**：`error: use of undeclared identifier '__llvm_libc_rt'`（`fp_libc_config.h:21 #define LIBC_NAMESPACE __llvm_libc_rt`）⇒ 需 `LIBC_NAMESPACE`/`COMPILER_RT_USE_LIBC_MATH` 构建上下文。
- **改动**：§4.2 与遗留④ 删「非真实缺口」定性 ⇒ 「**是否真实缺口未定**（include 根应为 `libc/`；补后仍 rc=1，尚需 `LIBC_NAMESPACE` 上下文）」。

**顺带（同类定性，已一并订正）**：§4.5 / §5 D3「上游 builtins 即纯 C、**已 freestanding**」同被 F-R1 数据反驳 ⇒ 改为「库外依赖仅 core 源 `int_util.c`→`abort`」。其余（§4.1/§4.3 数值、§4.2 计数与失败分类）经复核与实测一致，**未改**。

**未动**：实测数值、`run.sh`、`lib/*.py`、`probes/*.c`、`baseline/*` 一律未改（本次改动仅本任务书）。复核现场 `/tmp/opencode/INFRA-078t/rework/`（`int_util.{hosted,free}.o`、`addtf3.{base,libcinc}.err`）。

**判决**：F-R1/F-R2 均 ✅已修（附复核命令+真实输出）；同类定性已一并订正；**无未修项**。**状态 = 待验收**。

#### 第 2 轮 reviewer 审阅

**重跑记录**（workdir=仓库根，本人实测；现场 `/tmp/opencode/INFRA-078t/review2/`）：
- **F-R1 独立复核**：① `sed -n '85,206p' …/builtins/CMakeLists.txt | grep int_util` ⇒ `68: int_util.c`（=L152，在 `set(GENERIC_SOURCES`(L85)…`)`(L206) 内）；`enable_execute_stack.c`/`eprintf.c` core 区间 grep **0 命中**、仅 L278–283 条件块追加 ⇒ 新表述成立。② `clang -target dadao-unknown-elf -O2 -I <builtins> -c int_util.c` ⇒ **rc=0**；`nm -u` ⇒ `U abort`；`nm --extern-only --defined-only` ⇒ `W __compilerrt_abort_impl`；`llvm-objdump -r` ⇒ `R_DADAO_REL26 abort`。③ `-ffreestanding` 产物 md5 与不加**同为 `ef660f38c609…`**、仍 `U abort` ✓；另编 `trap_probe.c`（`__builtin_trap()`+`-ffreestanding`）⇒ `U abort` ⇒ 完成区⑤「trap lower 成 abort」实证成立。
- **F-R2 独立复现**：`ls …/llvm-project/lib/shared` ⇒ No such file or directory；`-I <builtins>` 编 `addtf3.cpp` ⇒ **rc=1**（`'shared/builtins/addtf3.h' file not found`）；补 `-I …/libc` ⇒ **仍 rc=1**（`use of undeclared identifier '__llvm_libc_rt'`，note=`fp_libc_config.h:21`）⇒ **无任何路径 rc=0**、「是否真实缺口未定」准确 ✓；`CMakeLists.txt:251/267 use_libc_builtin(… addtf3)` 挂 `COMPILER_RT_USE_LIBC_MATH` ⇒「尚需构建上下文」有据 ✓。
- **加强核查（库外依赖，全量 182 独立编译）**：OK=143 FAIL=39（=13+26，与 baseline 一致）；`nm` 交叉 ⇒ provider=129；库外未解仅 `int_util.c→abort`（core）、`enable_execute_stack.c→mprotect/sysconf`、`eprintf.c→fflush/fprintf/stderr`（非 core）、`gcc_personality_v0.c→_Unwind_*`（非 core，L316）、`__udivmodti4`（库内但源编不过）⇒ §4.2/D3/完成区⑤ 相关表述与实测一致 ✓。
- **数值未改核**：§4.2 `146/133/13` = `baseline/builtins-summary.json`、§4.3 `129/1306/126/66` = `baseline/symbols-summary.json`，逐数一致 ✓；`run.sh`/`lib/`/`baseline/` 未见改动需求（本轮只核文本）。
- **门控**：`make check` **rc=0**、`check-knowledge-refs` **rc=0**（0 悬空引用）、`check-no-residue` **rc=0**（日志 `review2/gate-*.log`）；验收前后 `git status --porcelain -uall` 均**空**（改动仅本审阅记录）。

| finding | 判据 | 真实证据 |
| --- | --- | --- |
| F-R1 ✅已闭合 | — | 上列独立复核全数支持新表述 |
| F-R2 ✅已闭合 | — | 无路径复现 rc=0，「未定」措辞准确 |
| **F-R3（新）** §4.2 与遗留④「（addtf3.cpp）…**对本 target 预处理掉**」**不实** | 描述须与真实数据一致（硬约束 3/5） | `clang -E`（补 `-I …/libc`）输出**保留** `extern "C" fp_t __addtf3(fp_t a, fp_t b){ return __llvm_libc_rt::shared::addtf3(a,b); }` ⇒ 体**参与编译**（补 include 后进语义期报 line 21）；被预处理掉的是 tf **`.c`** 源（`addtf3.c`/`divtf3.c` 的 `#if defined(CRT_HAS_TF_MODE)`，`grep -c "__divtf3"`=0）；且 `addtf3.cpp` 不在 `GENERIC_TF_SOURCES`（L218=`addtf3.c`）。**披露**：该措辞源自第 1 轮 reviewer 处方原话，非 engineer 擅加 |
| remark（不阻断） | — | §4.5/D3「builtins 即纯 C」严格说含 1 个 `.cpp`（addtf3.cpp）；第 1 轮已有、非本轮新引入 |

**判决**：**Needs Revision** —— F-R1/F-R2 完全闭合、数值/脚本未动、门控三连 rc=0；仅剩 F-R3 **一处文本不实**（§4.2 该句 + 遗留④ 共 2 个位置）。
**必须修（仅文本）**：删「对本 target 预处理掉」，或改为「该源**非 core**（tf 的 `.c` 源对本 target 预处理掉，但 `addtf3.cpp` 本身**不**被预处理掉）⇒ 不计入 core 缺口」。
**状态 = 待返工**（核验证据 `/tmp/opencode/INFRA-078t/review2/`：`int_util.{hosted,free}.o`、`addtf3.{base,libcinc}.err`、`trap_probe.o`、`indep/`、`gate-*.log`）。

#### 第 3 轮 engineer 返工

**对象**：F-R3 + 全报告定性陈述全扫。复核（workdir=仓库根，本人实测；现场 `/tmp/opencode/INFRA-078t/rework3/`）；`<B>`=`compiler-rt/lib/builtins`。

**F-R3 复现**（`clang -E`，补 `-I <llvm-project>/libc`）：
- `clang -target dadao-unknown-elf -O2 -I <B> -I …/libc -E <B>/addtf3.cpp` ⇒ rc=0，末 3 行**保留** `extern "C" fp_t __addtf3(fp_t a, fp_t b) {` / `return __llvm_libc_rt::shared::addtf3(a, b); }` ⇒ 函数体**存活、参与编译**；不带 `-I libc` 时 `-E` rc=1（`'shared/builtins/addtf3.h' file not found`）。
- `clang … -E <B>/addtf3.c`（`divtf3.c` 同）⇒ `grep -c __addtf3`=0（`__divtf3`=0）⇒ **tf `.c` 源**被 `#if defined(CRT_HAS_TF_MODE)` 预处理排除。**两者不同、不得混述**。
- 改前→后：§4.2「且其属 tf 口径、对本 target 预处理掉」→「该源**非 core**（tf 的 `.c` 源被预处理掉；但 `addtf3.cpp` 本身**不被预处理掉**：函数体存活、参与编译并 rc≠0）」；遗留④ 同改；**同句还出现在完成区③** ⇒ 一并订正。

**全扫清单**（核 ~20 处陈述、改 6 项/10 个文本点；依据均本轮实测）：
| # | 位置·陈述 | 判据 → 结论 | 改 |
| --- | --- | --- | --- |
| 1 | §4.2 / 遗留④ / 完成区③ `addtf3.cpp`「对本 target 预处理掉」 | `clang -E` 体存活 ⇒ 不实 | ✅ |
| 2 | §4.1(b)+§4.4#5 原子失败例含 `AtomicLoad` | 182 源 scan 日志 `AtomicLoad` **0** 命中；`_Atomic` load `-O0/-O2/-ffreestanding` 均 rc=0 ⇒ 未观测 | ✅ |
| 3 | §4.4#6「源 = … + arch `fp_mode`」 | `fp_mode.c`(L151) ∈ `GENERIC_SOURCES`(L85–206) ⇒ 通用已在、无需 arch | ✅ |
| 4 | §4.5 / §5 D3 / remark①「builtins 即纯 C」 | 顶层 181 `.c` + 1 `.cpp` ⇒ 不严 | ✅ |
| 5 | §4.3 结论「真正被发出的是 §4.1(a)/(b) 所列」 | 探针覆盖有限 ⇒ 加「**限本探针覆盖范围**」 | ✅ |
| 6 | §2「tf 源被预处理掉」 | 同 #1（`.c` 真、`.cpp` 例外） | ✅ |
| 7 | §4.1(a) `__divsc3/__divdc3`；§4.1(b) f16 源可编·i128「含除常量」；§4.4#3 SHL/SRL/SRA_PARTS；§4.1(c) 原生 `div.uo` | 探针重跑 `compiler_emitted_missing=['__divdc3','__divsc3']`；`extendhfsf2.c` OK；`a/7`,`a/10` rc=141；`srl_parts`/`sra_parts`/`shl_parts` rc=141；`llvm-objdump` 见 `div.uo/rem.uo`、无 libcall | ✓未改 |
| 8 | §4.2 146/133/13、26=xf14+atomic7+bf16 2+crtbegin+emutls+addtf3.cpp；§4.3 129/1306/126/66 + 交叉成员 | 独立全量 182 编译+分组、独立 `symbol_diff` 重算，逐数/逐员一致 | ✓未改 |
| 9 | §4.2「唯三引 libc」·`adddf3.c`→`fp_mode.c`；§4.4#1·#2 root cause 与 RTLIB 名；§2 事实（182/`__SIZEOF_INT128__`/long double/端序/`__dadao__`/sysroot） | 全量 undefined 交叉（仅 `int_util.c→abort`、`enable_execute_stack.c`、`eprintf.c` 引 libc；`gcc_personality_v0.c→_Unwind_*`）；`RuntimeLibcalls.{h,td}`（默认空 bitset、无 `else`、dadao∉`isDefaultLibcallArch`）；`-dM -E`/`nm`/`grep` ⇒ 一致 | ✓未改 |

**未动**：实测数值、`run.sh`、`lib/*.py`、`probes/*.c`、`baseline/*`（本轮仅改本任务书文本）；**未重跑** `run.sh`（仅抽样/定点复核）。**判决**：F-R3 及全扫 6 项均 ✅已修；#7–#9 经复核与真实数据一致、未改。**状态 = 待验收**。

#### 第 3 轮 reviewer 审阅

**重跑记录**（workdir=仓库根，本人实测；现场 `/tmp/opencode/INFRA-078t/review3/`；`<B>`=`compiler-rt/lib/builtins`）：
- **F-R3 复核（`clang -E` 二分）**：`clang -target dadao-unknown-elf -O2 -I <B> -I <llvm-project>/libc -E addtf3.cpp` ⇒ **rc=0**、输出末尾保留 `extern "C" fp_t __addtf3(fp_t a, fp_t b) { return __llvm_libc_rt::shared::addtf3(a, b); }`（`grep -c __addtf3`=1）⇒ **函数体存活**；不带 `-I libc` ⇒ **rc=1**（`'shared/builtins/addtf3.h' file not found`）；`-E addtf3.c`/`divtf3.c` ⇒ rc=0 且 `grep -c __addtf3`/`__divtf3`=**0**（守卫 `addtf3.c:16`/`divtf3.c:17 #if defined(CRT_HAS_TF_MODE)`）⇒ **tf `.c` 被预处理排除**。二分成立；§2/§4.2/遗留④/完成区③ 4 处新表述与实测相符 ✓。
- **第 2 项**：独立全量编 182 顶层源（本人循环、不沿用 scan）⇒ OK=143 FAIL=39、`AtomicLoad` 在 182 份日志 **0 命中**；`_Atomic` load 探针 `-O0`/`-O2`/`-O2 -ffreestanding` **rc=0×3** ⇒「失败例中无 AtomicLoad」成立；`AtomicLoadAdd` 独立复现（`__atomic_fetch_add` 全局 long 探针 ⇒ `Cannot select: t6: i64,ch = AtomicLoadAdd`）⇒ §4.1(b) 四签名（Store/Swap/LoadAdd/Fence）均实证 ✓。
- **第 3 项**：`CMakeLists.txt` `set(GENERIC_SOURCES`=L85…`)`=L206、`fp_mode.c` **L151 ∈ 区间**；通用 `fp_mode.c` 为默认 stub（`__fe_getround`/`__fe_raise_inexact`，我编产物 `nm` 均定义、编译 OK）⇒「dadao 无需 arch `fp_mode`」有据 ✓。
- **第 4 项**：顶层计数 = **181 `.c` + 1 `.cpp`（addtf3.cpp）**；§4.5/§5 D3 新句一致 ✓。
- **第 5 项**：§4.3 已含「**限本探针覆盖范围**」，与 §3 探针清单一致（`probes/*.c` 无 `_Atomic` 用法）✓。
- **第 6 项**：§2「tf `.c` 源被预处理掉（唯 `addtf3.cpp` 例外）」与 `-E` 实测相符 ✓。
- **未改数值抽查**：§4.2 `146/133/13` = `baseline/builtins-summary.json`；本人现场解析 scope（L86–205∪L218–243）=146、core_ok=133、core_fail=13、core_fail 文件集 `diff` 一致、13 FAIL 独立分类 = bswap 2/shl_parts 9/unsupported 2 无未分类 ✓。§4.3 `129/1306/126/66` = `baseline/symbols-summary.json`；独立 `nm` 重算 provider=129（集合与 baseline `diff` 一致）/sysroot=1306/missing=126 ✓；交叉成员逐一核对（`__divsc3/__divdc3/__divti3/__udivti3/__modti3/__umodti3/__multi3` ∈ missing、`__mulsc3/__muldc3` ∉ missing、`__bswapdi2/__bswapsi2/__muloti4/__mulvti3/__udivmodti4` 源在 ∉ provider）✓。
- **完成区 ③④**：③（tf `.c` 预处理掉 / `addtf3.cpp` 例外 / `_Float16` 不支持）与 ④（shl_parts 公共根因，9 FAIL 含 i128↔FP 与 `udivmodti4`）与实测一致 ✓。
- **证据脚本**：`./.work/evidence/<任务ID>/run.sh` ⇒ **rc=0** 全绿（A1–A6）；`--inject` ⇒ **rc=0**（5 注入均可达 FAIL、`cp`+md5 `42768bc8…/9b97d025…` 还原一致）。**本人独立注入**（不在原 5 条内）：`cp` 备份 `p09_misc.c`（md5 `12a994cc…`）→ 去原子用法 ⇒ run.sh **rc=1**、`A2 FAIL (missing ['atomic-no-isel'])` ⇒ `cp` 还原、md5 相等 ⇒ 重跑 **rc=0 全绿**。
- **门控**：`make check`/`check-knowledge-refs`/`check-no-residue` 各 **rc=0**（日志 `review3/gate-*.log`）；验收前后 `git status --porcelain -uall` 均**空**、任务书 md5 前后同为 `c8ebd26d…`（未动完成区）。

| finding | 判据 | 真实证据 |
| --- | --- | --- |
| F-R3 ✅已闭合 | — | `-E` 二分复核成立，§2/§4.2/遗留④/完成区③ 新表述与实测相符 |
| 第 2–6 项 ✅全部成立 | — | 逐项独立取证如上；**无新引入未证定性** |
| remark（不阻断） | 「简单原子 load 可正常 lower」披露不全 | 实测 `_Atomic` load 编译 rc=0 但 lower 成 **`__atomic_load` libcall**（`R_DADAO_REL26`），该符号 ∉ sysroot(1306)/∉ provider(129)/∉ source_only 清单；`ld.lld --unresolved-symbols=report-all` ⇒ `undefined symbol: __atomic_load`（rc=1）。「可正常 lower」在『无 fatal codegen』意义上属实、§4.1(a)「唯一」因「限本探针覆盖范围」仍成立；建议后续补一句 libcall 归属（原子库，D1 已排除）以免误读为链路无缺口 |

**判决**：**Accepted** —— F-R3 闭合、第 2–6 项全成立、未改数值与 baseline 及独立重算逐数一致、完成区 ③④ 对齐、无新引入未证定性；`run.sh`/`--inject`/独立注入/门控三连全绿。仅 1 条 remark（不阻断）。
**状态 = 待验收**（证据 `/tmp/opencode/INFRA-078t/review3/`：`run1.log`/`run2-inject.log`/`run3-indep-inject.log`/`run4-backgreen.log`/`gate-*.log`/`indep/`）。
