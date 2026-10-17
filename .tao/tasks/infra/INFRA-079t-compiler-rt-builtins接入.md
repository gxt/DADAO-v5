# INFRA-079t: compiler-rt builtins 接入（独立库 + 后端接入点 + 端序敏感验证）

**模块**：infra
**项目里程碑**：M8
**依赖**：`ADR-0027`（compiler-rt builtins 支持口径，`Accepted`，`D1`–`D5` = 本任务**唯一真源**）；`INFRA-078t`（compiler-rt 支持预研：缺口 / 符号差 / 接入点来源，**只读**）；`LLVM-091t`（`llvm-project 23.1.3` 已落地 = 补丁面基线）；`INFRA-067t`（picolibc vendored `__mulsc3`/`__muldc3` 的来源，本任务**移除**该 vendor）；消费方 = M8 `P1`（musl 静态）及其后各段
**状态**：待验收

## 执行环境
**执行环境**：本地

## 立项来源 / 用户裁定

- 来源 = `INFRA-078t §5` ADR 草案 + 用户 2026-10-14 **逐条确认**（**渠道 = 经主会话问答**；原话 / 选项标签与逐条确认记录见 `ADR-0027 §状态说明`）。本任务 = `ADR-0027` 的**执行落点**。
- **范围口径（`ADR-0027 D1`）**：**只 `builtins`**；**sanitizer / profiling / unwind / `libatomic` 暂不做**（按需单独立项）。
- **本任务不做**：**hw 特化**（`bswap`/`clz` 等，`D3` 后置、须数据支撑）；**ISA 指令扩展**（另立 `SPEC-141t`）；**不预设**其结论。
- **登记在册的边界**：`SPEC-140t` 已证实 **musl 硬依赖 TP + TCB/TLS 区**（`ADR-0025 D5`）——该面**不属本任务**（属 musl 移植），本任务只保证 `builtins` **可编、可链、可跑**。

### 追加裁定（2026-10-17，architect 落纸）

> **用户原话（逐字引录；渠道 = 经主会话问答）**：「**由于compiler-rt已经在llvm中实现了，picolibc中的对应内容可以删除；该任务可以放到整个动态链接测试之后**」

- **落纸三条**：
  1. **picolibc vendored 副本可删** ✓ —— 依据 = compiler-rt 已在 `llvm-project` 内实现（本任务即其接入落点，`ADR-0027 D2`：`components/llvm-project/patches/compiler-rt/**`）；删除面仍以「§输出 4 连带清理」为准（`libm/common/{muldc3.c,mulsc3.c,compiler_rt_builtins.h}` 三件 `.patch` + 现场判 `meson.build.patch`/`series`）。
  2. **排期 = 整个动态链接测试之后** ✓ —— 即本任务（及其连带清理）**后移**到「动态链接（`P2`）**及其测试**（`P3` 的动态档跑）」之后 ⇒ 现**不排入**当前队列（本行即排期口径的落纸处）。
  3. **删副本的依赖（硬）** ✓ —— 删 vendored 副本须与本任务（builtins 接入）**同批或在其后**；**先删而后接** ⇒ picolibc 在 `_Complex` 乘/除上失去提供方（`__mulsc3`/`__muldc3` 现由该 vendored 副本 = `INFRA-067t` 提供）⇒ **picolibc 编不过** ✗。**现场依据** = `INFRA-078t §4.4`（**后端 5 个接入点** #1–#5：i128 除法/取模 libcall 注册 / FP↔i128 / `SHL`·`SRL`·`SRA_PARTS` / `bswap` / 原子）+ `§4.5`（「**人力主要在 5 个后端改动点**」）⇒ 独立 builtins 库在 5 个接入点落地**前**不具备替代能力。
- **本任务其余范围/口径不动** ✗（`ADR-0027 D1`–`D5` 仍为唯一真源）；`**状态**` 仍 `待开始`（仅排期后移，**不**另置新状态）。

### 范围窄化（2026-10-17，主会话决定，待用户追认）

> **〔撤销（2026-10-17，用户裁定；本笔落纸）〕本窄化作废 ✗** —— 用户原话（**逐字**，渠道 = 经主会话问答）：「**既然要做，就做好；所以，要做，就把compiler-rt都做完，该调整任务链就调整任务链**」⇒ 恢复**全量**范围：① **7 类接入点全做**（i128 除法/取模注册 / FP↔i128 8 种 / `SHL`·`SRL`·`SRA_PARTS` / `bswap` / 原子 / f16 / `CMakeLists` arch 分支；其中 `bswap` 已由 `LLVM-097t` 收口的部分**不重复做**）；② **独立「DADAO compiler-rt builtins」库**（`ADR-0027 D2`）；③ **移除 picolibc vendored 副本**（同批或其后，见「§追加裁定 3」）；④ **driver 自动接线 + `-print-libgcc-file-name` 安装落点**（`ADR-0027 D5`）。
> **排期随之调整**：本任务 **先于 `M8` 收尾**（撤销「整个动态链接测试之后」的后移）；「§实现」的 `__muldc3`/`__mulsc3` archive 仍作**过渡证据**保留，**不再是范围上限**。
> 以下「主会话决定」原文**保留不改**（历史记录），但**其效力已作废** ✗。

> **性质标注（不得删改）**：本节 = **主会话决定**（2026-10-17，架构侧落纸），**非用户裁定**；**供用户追认**。追认前**不**得当作用户授权引用。

- **背景**：`P2` 阶段 A1 的**唯一剩余阻塞** = `__muldc3`/`__mulsc3`（现场 = `cpow.lo`/`cpowf.lo`；其余 `llvm` 面阻塞已由 `LLVM-096t`/`LLVM-097t`/`LLVM-098t`/`LLVM-099t` 处置），而本任务原排期 = 「**整个动态链接测试之后**」（用户 2026-10-17 原话，见上「§追加裁定」）。
- **窄化内容（只动一项）**：
  1. **提前项** = `builtins` 中 `complex` 的 **`__muldc3`/`__mulsc3`** 两个符号（`compiler-rt` 侧接入；**最小集**，仅此二符号）。
  2. **其余 6 类接入点仍按原排期** = 本册「§接口规范 → 输出 2」原「7 项接入点」中除已由 `LLVM-097t` 收口的 `bswap`〔④〕外的 6 项（i128 除法/取模、FP↔i128、`SHL`·`SRL`·`SRA_PARTS`、原子、f16、`CMakeLists` arch 分支）——「**动态链接测试之后**」对其**继续有效** ✗。
  3. **连带清理**（picolibc vendored 副本移除）**不**随提前项单独前置；仍按原排期与本任务主体同批（理由 = 先删后接 ⇒ picolibc 编不过，见「§追加裁定 3」）。
- **理由**：① **最小原则**（只提前堵点符号，不整体前移）；② 该二符号**当前堵着 `libc.so`**（`P2`/A1 主判据 `make build-musl-shared` rc=0）。
- **落地口径**：本节**仅**记录主会话决定，**不**改写 `ADR-0027 D1`–`D5`、**不**改 `**状态**`、**不**改用户 2026-10-17 原裁定的其余部分；追认结果由主会话追加到本节（未追认前**不**视为用户裁定）。

### 实现（2026-10-17，窄化范围）

**测试结果**：证据 `.work/evidence/INFRA-079t/run.sh` default **15 PASS / 0 FAIL（rc=0）**；`--inject` I1/I2/I3 **全部转红**（oracle 翻期望 ⇒ qemu rc=1；移走补丁 ⇒ patch-wiring 红；archive 去 `muldc3.c.o` ⇒ link rc=1），`cp`+md5 还原后重跑**回绿**（rc=0，"INJECT OK"）。
**修改文件**：① 新 `components/llvm-project/patches/compiler-rt/cmake/builtin-config-ix.cmake.patch`（`set(DADAO dadao)` + `ALL_BUILTIN_SUPPORTED_ARCH` 并入 `${DADAO}`，共 2 行）；② 新 `components/llvm-project/patches/compiler-rt/lib/builtins/CMakeLists.txt.patch`（`set(dadao_SOURCES muldc3.c mulsc3.c)` + 5 行注释）；③ `components/llvm-project/series` 76→**78**；④ `components/llvm-project/changelog.md` +1 条（M8）；⑤ 本块 + `第 1 轮 engineer 自审`。**头文件零改动**：`int_lib.h`/`int_types.h` 无需 arch 分支（`COMPILER_RT_ABI` 非 ARM 为空；`_Complex`/`double` 由前端定），`int_endianness.h` 走 `__BYTE_ORDER__` 分支已正确（现场探针 `_YUGA_BIG_ENDIAN=1`，host 对照被 `#error` 拒）。
**验收结果**：① **符号可得**：`nm libclang_rt.builtins-dadao.a` = `T __muldc3` / `T __mulsc3`，成员 **2**（最小集），`nm -u` **空**；目标程序用该 archive 链接 rc=0。② **数学 oracle（独立派生）**：25 例（double 15 = 6 精确 + 9 特殊；float 10 = 4 精确 + 6 特殊），覆盖正常值 / 溢出到 `inf` / NaN / 带符号零；期望源 = 自写 IEEE-754 模型（`Fraction` 精确值 + 逐操作 RN-even 舍入）+ 重算路径取上游 `muldc3_test.c` 分类表；QEMU（大端）**rc=0**；host gcc 同源交叉 **rc=200**（表全过 + BE 检查正确判为小端）；BE 内存映像检查（π 的 BE 字节 ↔ 反向字节）双向可判别。③ **B 类消失**：`ld.lld -shared --no-undefined --error-limit=0` 对 `cpow.lo`/`cpowf.lo`，**对照 2 条 undefined（`__muldc3`/`__mulsc3`）⇒ 加 archive 后 0 条**；全 `.lo`（**1351**）全量链接 `--error-limit=0` **rc=0**（B 类为唯一剩余；1 个对象替换见「坑①」）。④ **静态不回归**：按派单**未跑** `make build-musl*` ⇒ 以「工具链二进制未被本笔触碰（`clang`/`ld.lld` size+mtime+ctime 前后同）+ 静态 ELF 探针 `ET_EXEC`/`BigEndian`/无 `PT_INTERP` 且可跑 rc=0 + 改动面不涉 clang/llvm/lld/musl」为据（**非**全量静态重建，如实标注）。
**门控（各留自身 rc）**：`check-patch-tree` **rc=0（154 补丁，原 152；llvm-project 78，原 76）**、`check-index-blobs`/`check-source-state`（llvm-project `HEAD=a297528f2 count=1 clean=True`）/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check_issues.py`/`make check`(L1) 全 **rc=0**。
**新发现/坑**：① **对象树污染**：`.work/source/musl/obj/src/crypt/crypt_sha512.lo` 与其 `.o` **逐字节相同**（非 PIC 对象冒充 `.lo`，`.rela.text` 11 条 `ABS48`）⇒ 全量 `-shared` 链接报 `ABS48 … recompile with -fPIC` 假 FAIL；用 build-tree clang 重编 `-fPIC`（改走 GOT/`PCREL_*`）后 rc=0。该 `.lo` 比源新 ⇒ `make build-musl-shared` 不会重编它，建议主会话先 `make -C .work/source/musl clean`。② **`-rtlib=compiler-rt` 未被 DADAO driver 消费**（`warning: argument unused during compilation`；driver 不加 builtins archive）⇒ 当前「链接期找到」只能走**显式 archive**（派单允许的「等价路径」）；driver 自动接线 + 安装落点属本任务主体（`D5`）。③ 命名差：`-print-libgcc-file-name` = `…/dadao-unknown-unknown-elf/libclang_rt.builtins.a`，而构建产物为 `libclang_rt.builtins-dadao.a` ⇒ 安装接线须 `LLVM_ENABLE_PER_TARGET_RUNTIME_DIR=ON` 或补 arch 名，勿在 install 时踩。④ standalone 配置须同时给 `CMAKE_CXX_COMPILER_TARGET`（`clang++` 默认 triple `unknown`，`project(... CXX)` 会失败），与产物无关。
**遗留问题**：按派单**未跑** `install-host`/L2/L3/`build-musl*`，**未** commit/push，**未**改 `**状态**`；原 7 项接入点中除本二符号外的 6 项、`D2` 安装落点、picolibc vendored 副本移除、`ISS-243`/`ISS-245`、`B1/C1/D1` **均未做**（按原排期）。

## 已查证事实（源 `INFRA-078t`，**引用勿重复查证**）

1. **上游不认识 `dadao`**：`int_lib.h`/`int_types.h`/`int_endianness.h` **无** `__dadao__`/`__DADAO__` 分支（`grep` 0 命中）。
2. **大端已内建**：`int_endianness.h` 走 `__BYTE_ORDER__ == __ORDER_BIG_ENDIAN__` 双路；我们的 clang `-target dadao-unknown-elf` 定义 `__BIG_ENDIAN__` / `__BYTE_ORDER__=__ORDER_BIG_ENDIAN__` ⇒ `_YUGA_BIG_ENDIAN=1` 正确（**订正**早前「须改 `__BYTE_ORDER__`」的假设）。
3. **`long double` = 64 bit**：`__SIZEOF_LONG_DOUBLE__=8` / `__LDBL_MANT_DIG__=53` ⇒ `HAS_80_BIT_LONG_DOUBLE=0`、无 `tf_float` ⇒ **xf 源不适用、tf 源被预处理掉**（对上游**无需改**，只需按 arch 口径排除 / 保留）。
4. **`_Float16`/`__bf16` 前端不支持**：`_Float16`/`__bf16` ⇒ `error: ... is not supported on this target`；无 `__FLT16_*` 宏。
5. **`__int128` 支持**（`__SIZEOF_INT128__=16`）；**工具链不提供 libgcc / compiler-rt builtins**；sysroot 中**仅**手工 vendor 的 `__mulsc3`/`__muldc3`。
6. **scope 现场统计**（上游 `CMakeLists.txt` 解析，`GENERIC_SOURCES ∪ GENERIC_TF_SOURCES`）= **146**：**OK 133 / FAIL 13**；13 个 core FAIL 全归 3 类：`bswap`（2：`bswapdi2.c`/`bswapsi2.c`）、`shl_parts`（9：`fixdfti.c`/`fixsfti.c`/`fixunsdfti.c`/`fixunssfti.c`/`floattidf.c`/`floattisf.c`/`floatuntidf.c`/`floatuntisf.c`/`udivmodti4.c`）、`unsupported library call operation`（2：`muloti4.c`/`mulvti3.c`）。
7. **符号差**（`missing = provider \ sysroot` = **126** / `source_only`（源在、编不出）= **66**）——即使只补库、不动后端，**今天可编出的 129 个符号里仍有 126 个 sysroot 缺**。
8. **`LibcallLoweringInfo` 根因**：默认全 `Unsupported`，且 `setTargetRuntimeLibcallSets` **无 `else` 分支** ⇒ 非表内 arch（dadao）可用集为空 ⇒ **任何** backend libcall 都须在 `initLibcallLoweringInfo` **显式注册**（解释 i128 除法 / FP↔i128 的 fatal codegen）。
9. **`shl_parts`（`ISD::SHL_PARTS`）= 公共根因**（i128 变址移位 / i128↔FP / `udivmodti4`）。
10. **引 libc 的源**：`enable_execute_stack.c`（→`mprotect`/`sysconf`）、`eprintf.c`（→`fprintf`/`fflush`/`stderr`）**均非 core**；`int_util.c`（→`abort`）**属 core**（见 #11）。
11. **`int_util.c` 属 `GENERIC_SOURCES`（core）且引 `abort`**（`-ffreestanding` 下亦然）⇒ 接入时须由环境提供（影响 freestanding 预期）（源 `INFRA-078t`）。
12. **简单原子 load 亦 lower 成 `__atomic_load` libcall**（链接期 `undefined symbol`）⇒ 原子依赖不止读改写；`ADR-0027 D1` 已把原子排除在范围外（源 `INFRA-078t`）。

## 接口规范

- **输入**：`ADR-0027` `D1`–`D5`（口径真源）；`INFRA-078t §4.4`（接入点清单）；上游源码 `.work/source/<组件>/compiler-rt/lib/builtins/`（**只读**）；`.dadao/` 工具链 + sysroot（**只读**）；`manifests/components.lock.toml`（版本锁）；`contracts/opcodes.yaml`（只读，供反查 libcall 名）。
- **输出**：
  1. **补丁集**（`ADR-0027 D2`）：`components/llvm-project/patches/compiler-rt/**`（**一文件一补丁**，镜像上游仓内路径）+ `components/llvm-project/series` 追加；含 `int_lib.h` / `int_types.h` 的 **`dadao` 分支** + **BE 处理**（事实 #2：`int_endianness.h` 可能**无需改**，**现场核实并如实记录**）+ `compiler-rt/lib/builtins/CMakeLists.txt` 的 **`dadao` arch 分支** + 补 **`-DCRT_HAS_INITFINI_ARRAY`**（供 `crtbegin.c`）。
  2. **后端接入点**（`ADR-0027 D3`/`Consequences`，**7 项，逐条处置**）：
     - ① **i128 除法 / 取模 libcall 注册**（`DADAOSubtarget::initLibcallLoweringInfo`：`RTLIB::SDIV_I128`/`UDIV_I128`/`SREM_I128`/`UREM_I128` ⇒ `__divti3`/`__udivti3`/`__modti3`/`__umodti3`）；
     - ② **FP↔i128 转换**（8 种 `RTLIB::*_I128` ⇒ `__fixdfti`/`__fixsfti`/`__fixunsdfti`/`__fixunssfti`/`__floattidf`/`__floattisf`/`__floatuntidf`/`__floatuntisf`）；
     - ③ **`ISD::SHL_PARTS`/`SRL_PARTS`/`SRA_PARTS`**（i128 变址移位 = 事实 #9 的公共根因）；
     - ④ **`bswap`**（`setOperationAction(ISD::BSWAP, MVT::i64/i32, Expand)` **或** 注册 `__bswapdi2`/`__bswapsi2` libcall）；
     - ⑤ **原子**（AtomicLoad/Store/RMW/Fence 的 libcall 或原生 lowering；**可能超范围** ⇒ 现场判 / 提请用户，见「遗留」）；
     - ⑥ **f16**（`_Float16`/`__bf16` 当前**前端拒绝** ⇒ 是否可达待判）；
     - ⑦ **`compiler-rt` `CMakeLists.txt` `dadao` arch 分支**（同输出 1；`emutls.c` 需 `pthread.h` ⇒ **按需排除**）。
     **每条须给「做 / 不做 + 证据或理由」**——不得静默跳过。
  3. **独立库**（`ADR-0027 D5`）：构建并 install 为**独立「DADAO compiler-rt builtins」库**（**不属任何 libc**），落点按 `ADR-0016`（host prefix `.dadao/cross-toolchain/**`、target sysroot 根、只装所需）；**picolibc 与 musl 共用**。
  4. **连带清理**（`ADR-0027 Consequences 1`）：移除 `components/picolibc/patches/libm/common/{muldc3.c,mulsc3.c,compiler_rt_builtins.h}`（对应 `.patch` 三件）⇒ 改链接独立库；**现场判**同目录 `meson.build.patch`（只含 `srcs_common` 两源插入，随源移除**须同步撤回**）与 `components/picolibc/series` 删行；重建 picolibc 并给 **before/after 全量四分类**（**计数现场统计、不写死**）。
  5. 证据（`.work/evidence/<任务ID>/run.sh` + 原始产物）与 `.work/log/<模块>/**`；本任务书完成区 + `milestones.md` 流水行。
- **约束**：**最小改动**、只碰任务范围；**不得**改 `spec/`（`ADR-0012 D4` / `docs/Process-06` **须用户事先授权**）、`contracts/` 机器数据；**不得**做 hw 特化（`D3`）；改动须以 `manifests/components.lock.toml` 锁定 commit 为基线（`ADR-0005`）；**计数不写死**。

## 验收标准

1. **范围核对**：改动面**只在** `builtins`（`ADR-0027 D1`）；未纳入 sanitizer / profiling / unwind / `libatomic`（列出改动文件清单佐证）。
2. **库存在且可链接**：`nm` 在**建成产物**中证明**代表符号有定义**（真实输出）；`__divsc3`/`__divdc3` 等「编译器已发出」的符号**不再 `undefined`**（真跑链接 + QEMU，rc 与输出留证）。
3. **7 项接入点逐条处置**：每项给「做 / 不做 + 证据或理由」；「做」者给实测输出（后端改动 ⇒ 探针 `Cannot select` / `unsupported library call operation` 消失，**前后对账**）；「不做」者给事实依据（如 f16 前端拒绝的**现场复现**）。
4. **验证（`ADR-0027 D4`）**：
   - **代表集 + 独立 oracle**：上游 `compiler-rt/test/builtins` 作**现成 oracle** + **算法定义 / Python 大整数独立算期望**（≥ **2 个独立源**，**禁**从 v5 自身实现反推）；
   - **端序敏感用例**（**我们是大端**、上游多 LE）**已补**且可跑；
   - 接 `tests/vectors/` / lit 既有模式；**新增向量独立全量重算**（非抽样）。
5. **独立库 install 落点**符合 `ADR-0016`（现场输出证明落点，**不新增**安装根）。
6. **连带清理完成**：picolibc vendored 副本已移除 + 重建后**全量四分类 before/after**（`fail` 不升、`newly_blocked=∅` 或已归因）；`ADR-0019 D10` / `ISS-206` 若涉及 `builtins` 的 libcall 名 ⇒ **已现场判**并记录。
7. **门控**：`make check`(L1) / `check-modules`(L2) / `check-no-residue` / `check-knowledge-refs` / `tools/infra/check_issues.py` 各 **rc=0**；补丁纪律：`check-patch-tree` / `check-index-blobs` / `check-patch-tree --source-state` rc=0。
8. **反例可失败**：注入（移除某符号 / 改错期望）⇒ 断言 **FAIL** ⇒ `cp` + md5 还原 ⇒ 回绿（**禁** `git checkout`/`restore`/`stash`）；每断言有**可达 FAIL** 路径。
9. 完成区（**≤30 行**）与真实输出**逐条对齐**；`milestones.md` 流水行已更新。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-079t/`；命令一律在 **workdir（= 仓库根）** 内、**相对路径**；**禁** `cd` 出界；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；**禁** `cmd | tee` 吞码；复杂命令输出留 `.work/log/<模块>/**`。
4. **只动任务范围**；越界须披露；**不改** `spec/` / `contracts/`（`docs/Process-06`）。
5. **失败保留现场并继续推进**（自行处置：派修 / 绕行 / 有据重试并记录次数 / 登记后跳过）；**只在需用户语义裁定**（新决策 / 需授权）时留问，**禁**自拟自答。
6. 一键证据脚本（`.work/evidence/<任务ID>/run.sh`）：非交互、任一失败非零退出、逐项打印「检查名 + 期望/实际 + rc」、含**可达 FAIL** 自检。
7. **计数不写死**（scope / 缺口 / 符号数一律**现场统计**）。
8. 补丁导出纪律：写 `/tmp`、行数下限、**非空 blob**、`check-patch-tree` 断言⑥、`.work/source/<组件>` = `base+N`、`series` 一致。
9. 文本**不写**字面 `.work/<具体路径>`（用 `<>` 占位）；任务书**自包含**（不依赖外部仓库内容）。
10. 本任务**规模大、含构建**：启动前**申报预计耗时**；长构建按 `AGENTS.md`「长任务」脱离生命周期（`setsid nohup` + 落退出码），**禁**会话内等待器、**禁**全核。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

### A 部分（2026-10-17，后端 3 类接入点；本笔只做 A、不跑 `install-host`）

**测试结果**：证据 `.work/evidence/INFRA-079t-A/run.sh` default **14 PASS / 0 FAIL（rc=0）**；`--inject` **4 条注入全部转红**（I1 探针少一 libcall ⇒ div/rem=3/4；I2 oracle 期望翻 1 位 ⇒ qemu rc=3；I3 archive 去 `divti3.o` ⇒ link rc=1 `undefined symbol: __divti3`；I4 移走补丁 ⇒ patch-content 红），`cp`+md5 还原各自一致、收尾复跑 rc=0（"INJECT OK"）。端到端 189 项（`-O0`/`-O2` 各一轮）+ host gcc 交叉全 rc=0。
**修改文件**：① `.work/source/llvm-project/llvm/lib/Target/DADAO/DADAOSubtarget.cpp`（+28 行：4 个 i128 除法/取模 + 8 个 FP↔i128 注册）；② 同目录 `DADAOISelLowering.cpp`（+27 行：`*_PARTS` Custom、`FSHL/FSHR` Expand、`LowerOperation` 3 个 case）；③ `components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOSubtarget.cpp.patch,DADAOISelLowering.cpp.patch}`（`make_patch` 重导出：2 写 / 76 未变，`series` 仍 78）；④ `components/llvm-project/changelog.md` +1 条（M8）；⑤ `.work/evidence/INFRA-079t-A/{run.sh,gen_oracle.py,before/*}`（新增）。
**验收结果**（逐条）：
- **7 项**：①✅ i128 除法/取模已注册（探针 4/4 发 `call [rb0, __divti3|__udivti3|__modti3|__umodti3]`）；②✅ 8 种 FP↔i128 全注册（探针 8/8，含 `__floatuntidf/isf`）；③✅ `SHL/SRL/SRA_PARTS` Custom + `expandShiftParts`（变量移位 21 例语义经 oracle；`*_parts` Cannot select 消失、0 shift libcall）；④ 仅核对：`setOperationAction(ISD::BSWAP, MVT::i64, Expand)` 在位、`__builtin_bswap64` 无 `__bswapdi2`（`LLVM-097t` 收口，不重复做）；⑤ 不做：`ADR-0027 D1` 排除 —— 现场 `__atomic_load/__atomic_store` 调用 + `AtomicLoadAdd` `Cannot select`（事实 #12）；⑥ 不做：前端拒绝 `_Float16`/`__bf16`（原文 `is not supported on this target`）；⑦ 核对：`dadao_SOURCES muldc3.c mulsc3.c` 在位（窄化批）。
- **前后对账**：修前原文留 `.work/evidence/INFRA-079t-A/before/` = `fatal error: error in backend: unsupported library call operation`（p1/p2）、`fatal error: ... Cannot select: t23: i64,i64 = shl_parts t4, t2, t22`（p3）；修后三类 `clang -S` 全 rc=0 且 libcall 名逐一出现。
- **原 FAIL 源解阻**：`INFRA-078t` 事实 #6 的 **13/13** core 源现全部 `rc=0`（8 个 FP↔i128 + `udivmodti4` + `bswapdi2/bswapsi2` + `muloti4/mulvti3`）——B 部分只需把它们接入 `dadao_SOURCES`。
- **符号对账**：探针 `.o` 的 `nm -u` = **12/12**，临时 archive 定义 **12/12**；**仓库 archive（窄化）0/12** ⇒ 12 个全缺，归 **B 部分（`dadao_SOURCES`）**（如实报，不在本笔补）。
- **实跑**：`oracle.c` **189** 检查（i128 除/模、`i128↔f64/f32` 双向、`u128` 同面、变量移位 0…127）= 显式 archive + `ld.lld` + qemu 大端 **rc=0**（`-O0`/`-O2`）；**独立 oracle 两源** = Python 大整数 + 显式 IEEE-754 RN-even 模型（`gen_oracle.py`，不从实现反推）+ host gcc/libgcc 同源 **rc=0**。
- **无回归**：CodeGen lit **31/31**（`LLVM_TOOLS_DIR=.work/build/llvm/bin`，未用安装根）、`check_lit_gen` **64/0**、`ninja -C .work/build/llvm clang` **rc=0**（实测 3m23s，开工申报 ≈4 min）。
- **补丁**：`check-patch-tree` **rc=0（177 补丁；修前 177，不变）**、`check-index-blobs`/`check-source-state`（llvm-project `HEAD=base+1`、clean）/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check_issues`/`check-instrinfo`/`make check`(L1) 各 **rc=0**（日志 `.work/log/infra/INFRA-079t-A-*.log`）。
**新发现/坑**：① `expandShiftParts` 以 `ISD::FSHL/FSHR` 表达，二者默认 `Legal` 且本后端无 pattern ⇒ 只设 `*_PARTS` Custom 会在下一轮以 `Cannot select: fshl` 失败，须同批设 `Expand`。② `-O2` 下 i128 常量会被折叠；oracle 用 `volatile` 装载操作数才能保证 libcall 真被执行（否则全绿是假绿）。③ 无符号转换名拼写是 `__float`+`un`+`ti`+`[sd]f`（按 `unt` 写正则会漏计 2 个）。④ 仓库 archive 仍只 2 成员 ⇒ 端到端只能显式链 `/tmp` 临时 archive（B 部分落地后消失）。
**遗留问题**：**未跑** `install-host`/L2/L3/`build-musl*`/`build-picolibc*`（派单）；**未** commit/push；**未改** 任务 `**状态**`。**B 部分待做**：`dadao_SOURCES` 源集（`GENERIC_SOURCES ∪ GENERIC_TF_SOURCES` + `CRT_HAS_INITFINI_ARRAY`，`emutls.c` 按需排除）⇒ 12 符号入 archive；`-print-libgcc-file-name`/driver 自动接线 + 安装落点（`D5`）；picolibc vendored 副本移除 + 重建四分类 before/after。

### B1 部分（2026-10-17，全量源集 + driver 自动接线 + 安装规则；未跑 `install-host`）

**测试结果**：证据 `.work/evidence/INFRA-079t-B1/run.sh` default **8 PASS / 0 FAIL（rc=0）**；`--inject` **4 条注入全部转红**（I1 archive 去 `divti3.c.o` ⇒ 覆盖/符号红；I2 oracle 翻 1 位 ⇒ qemu rc=3；I3 移走 build-tree resource-dir 的 archive ⇒ driver 路径 `exists=no` + 链接 `cannot open …`；I4 去补丁锚点 ⇒ `driver-anchor=0`），`cp`+md5 还原各自一致、收尾复跑 rc=0（INJECT OK）。`ninja -C .work/build/llvm clang` **rc=0**（实测 3m43s，申报 ≈4 min）。
**修改文件**：① `.work/source/llvm-project/compiler-rt/lib/builtins/CMakeLists.txt`（`dadao_SOURCES` 由窄化 2 源扩为 `${GENERIC_SOURCES} ${GENERIC_TF_SOURCES}`；5 项显式排除；补 `-DCRT_HAS_INITFINI_ARRAY`）；② 同仓 `clang/lib/Driver/ToolChains/DADAO.cpp`（+13 行：`-rtlib=compiler-rt` 消费并追加 builtins archive）；③ `components/llvm-project/patches/compiler-rt/lib/builtins/CMakeLists.txt.patch`、`.../clang/lib/Driver/ToolChains/DADAO.cpp.patch`（`make_patch` 重导出：2 写 / 76 未变，`series` 仍 **78**）；④ `components/llvm-project/changelog.md` +1 条（B1）；⑤ `Makefile`（+23 行，最小 diff：`install-host` 增加 builtins archive 安装规则；**单独改**）；⑥ `.work/evidence/INFRA-079t-B1/{run.sh,gen_oracle.py}`（新增；`gen_oracle.py` 取自 A 段同一独立 oracle）。
**验收结果**（逐条）：
- **源集**：现场解析 `GENERIC_SOURCES ∪ GENERIC_TF_SOURCES` = **146**；archive 成员 **147**（多出 `clear_cache.c` —— `NOT FUCHSIA` 追加的通用 builtin，仅引 archive 内 `__compilerrt_abort_impl`）。排除 5 项且**均不在 archive**，现场依据：`emutls.c` ⇒ `fatal error: 'stdlib.h' file not found`（还需 `<pthread.h>`）；`enable_execute_stack.c` ⇒ `'sys/mman.h' not found`；`eprintf.c` ⇒ `'stdio.h' not found`；`atomic.c` ⇒ `_Static_assert` 无 lock-free pointer-size cmpxchg + `ADR-0027 D1` 排除 libatomic；`gcc_personality_v0.c` ⇒ `nm -u` 出 `_Unwind_GetIP/…`（unwind 超出 `D1`，只因 configure 在 clang 自带头里找到 `<unwind.h>` 才进表）。
- **符号/未定义**：A 段 12 libcall + `__muldc3`/`__mulsc3` **14/14** 有定义；`nm -u` 解析 archive 内互引用后**仅剩 `abort`（`int_util.c`，事实 #11，预期）**。
- **driver 自动接线**：`-rtlib=compiler-rt -print-libgcc-file-name` = `…/lib/clang/23/lib/dadao-unknown-unknown-elf/libclang_rt.builtins.a`（真实存在）；`-###` 的链接行含同一路径；`unused-command-line-argument` 计数 **0**。坑③ 的命名差用 `LLVM_ENABLE_PER_TARGET_RUNTIME_DIR=ON` 消解（产物即无 arch 后缀）。
- **端到端（自动接线的唯一有效证据）**：`-rtlib=compiler-rt` 且**不带显式 archive** 链接 A 段 189 项独立 oracle，`-O0`/`-O2` 均 link rc=0、QEMU 大端 **rc=0**；复数探针 `(1+2i)(3+4i)` 两个 libcall 均发出并被 driver 供给的 archive 解析，link+qemu rc=0。
- **默认不回归**：不带 `-rtlib` 的链接**不**加 archive（`-###` 中 `libclang_rt` 计数 0），libcall 仍按原样未解析 ⇒ 接线是 opt-in。
- **安装规则**：`make -n install-host` 解析出的目标 = `…/cross-toolchain/lib/clang/23/lib/dadao-unknown-unknown-elf/libclang_rt.builtins.a`，与 build-tree clang 的 `-print-libgcc-file-name` 去掉 resource-dir 前缀后**逐字一致**；两次 dry-run 稳定一致；动作为 `atomic-install`（temp+`rename`）⇒ 幂等；落点在 `ADR-0016 D3` 的 host prefix 内，**不新增安装根**。
- **门控（各留自身 rc）**：`check-patch-tree` **rc=0（177 补丁；llvm-project 78）**、`check-index-blobs`/`check-source-state`（llvm-project `HEAD=base+1`、clean）/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check_issues`/`check-instrinfo`/`check_lit_gen`/`make check`(L1) 各 **rc=0**（日志 `.work/log/infra/INFRA-079t-B1-*.log`）。
**新发现/坑**：① 「146 源」只是两条基线列表的并集；`GENERIC_SOURCES` 在 arch 分支前还会被 `NOT FUCHSIA`（`clear_cache.c`）与 `HAVE_UNWIND_H`（`gcc_personality_v0.c`）追加 ⇒ 必须对追加项逐条判（本笔留前者、排后者），否则会把 unwind 依赖带进库。② 组件树 `git commit --amend` 会改 `VCSRevision` ⇒ build-tree clang 立刻"不新鲜"、`ninja -n clang` 不再 `no work to do`；须在**最后一次**组件提交后重建（本笔重建 2 次：3m55s、3m43s）。③ standalone 配置改用 build-tree clang（默认 triple = `unknown`）时，`CMAKE_C_COMPILER_TARGET` **不足以**过 `project()` 的编译器探测，须同时给 `CMAKE_{C,CXX,ASM}_FLAGS=--target=…`（坑④ 的更深一层）。④ `-print-libgcc-file-name` 在 archive 尚不存在时也会返回"将要安装的位置"（`getCompilerRT` 的 fallback），故安装落点可由它稳定推导；但它与 `-rtlib=compiler-rt` 必须成对（默认 RTL=libgcc 时打印 `libgcc.a`）。⑤ `Makefile` 里探针变量必须用**递归展开**（`=` 而非 `:=`），否则 clean tree 上 parse 期 clang 尚未构建 ⇒ 空值误报。
**遗留问题**：按派单**未跑** `install-host`/L2/L3/`build-musl*`/`build-picolibc*`（主会话 / B2），**未** commit/push，**未**改 `spec/`/`contracts/`，**未**越界（`Makefile` 单独改、最小 diff）。**B2 待做**：picolibc vendored 副本移除（3 件 `.patch` + `meson.build.patch` + `series` 删行）与重建后四分类 before/after；`install-host` 落点由主会话执行后复核。

## 审阅记录

#### 第 1 轮 engineer 自审
自主逐行审查（无嵌套子代理）；判决 = **窄化范围可交付**（外部阻塞与剩余类均已如实披露）。按派单**未改** `**状态**`（主会话统一口径）。

| finding（自审发现） | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `gen_oracle.py::bits()` 的 inf 分支三元运算优先级错（sign 掩码会被整体条件表达式吞掉）⇒ 负数 inf 期望值错 | ✅已修 | 拆成显式 `if/else` 返回 64/32 位掩码 | `run.sh S4` qemu rc=0；`neg-inf-finite` 期望 `0xfff0…`/`0x7ff0…` 与模型一致（gen 日志逐例打印） |
| F2 初版对 NaN 结果做**位精确**比较（NaN 符号/payload 未规定）⇒ gcc 交叉首跑 rc=8（gcc 给 `0xfff8…`，模型给 `0x7ff8…`） | ✅已修 | 期望编码改为「精确位 / NaN / ±inf」三态：NaN 比类别、inf 比符号，仅有限值比位 | host 交叉 `rc=200`（25 例全过 + BE 检查判别成功），target `rc=0` |
| F3 证据脚本 S5 的 `-fPIC` 单文件编译用了相对仓库根的 `-Iarch/…` ⇒ `ctype.h` not found（假 FAIL） | ✅已修 | 改为 `( cd .work/source/musl && … )` 内编译 | `run.sh S5-full-shared-link` rc=0 |
| F4 S6 工具链快照用 `>>` 追加 ⇒ 跨次运行累加，第二次起恒 FAIL | ✅已修 | 快照前 `: > "$after"` 截断 | 连续两次 default 均 `S6 PASS` |
| F5 全量 `-shared` 链接出现 11 条 `ABS48` 报错，初判为「新类」 | ✅已修（定性） | 查证 `crypt_sha512.lo` 与 `.o` **逐字节相同**（非 PIC 冒充 `.lo`）；替换为 `-fPIC` 重编对象后 rc=0，并写入「坑①」 | `cmp` rc=0（o≡lo）；替换后全量链接 rc=0、DSO 内 `t __muldc3`/`t __mulsc3` |
| F6 派单提示的 `clang -rtlib=compiler-rt` 路径实测被 driver 忽略（`-Wunused-command-line-argument`） | ✅已修（口径） | 改用派单允许的「等价路径」= 显式 archive；driver 接线登记为遗留/坑② | `run.sh S4` 链接 rc=0；driver 警告原文见 `/tmp/opencode/INFRA-079t/probe*` 记录 |
| F7 standalone `cmake` 因 `clang++` 默认 triple `unknown` 在 `project(... CXX)` 失败 | ✅已修（命令侧，不入仓） | 配置补 `-DCMAKE_CXX_COMPILER_TARGET=dadao-unknown-elf` | `run.sh S2` configure rc=0、ninja rc=0 |

**未修 finding**：无（F1–F7 均处置；外部阻塞项见本册「遗留问题」，非本笔缺陷）。

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

#### architect 提交留痕（2026-10-17，窄化批）
- **档位**：本册**无 reviewer `Accepted` 判决**（「第 1 轮 reviewer 验收」仍为占位）⇒ 流程档位本应 **WIP**；本笔按派单给定文案**逐字提交**（无 `WIP:` 前缀）⇒ **如实披露** ✗。
- **提交**：`038f974`（5 文件 = 2 新补丁 + `series` 76→**78** + `changelog.md` + 本册「§实现 + 第 1 轮 engineer 自审」）；`git diff --cached --name-only` 与完成区「修改文件」**逐条一致** ⇒ **漏提 0 / 多提 0 / 越界 0**（**未触** `spec/`·`contracts/`·`.tao/contracts/**`·`components/musl/**`·`Makefile`）。
- **门控（各留自身真实 rc）**：`make check`(L1) **rc=0**；`check-patch-tree` **rc=0（154 补丁；llvm-project 78）**、`check-index-blobs`、`check-source-state`、`check-no-residue`、`check-tasks`、`check-knowledge-refs`、`check-component-changelog`、`python3 tools/infra/check_issues.py` 各 **rc=0**（日志 `.work/log/architect/INFRA-079t-085t-commit/`）。**未跑**（`ISS-229` 并发禁令；本笔纯提交/文档）：`install-host` / `build-*` / L2 / L3。
- **边界**：**未改**本册 `**状态**`（仍 `待开始`）✗、**未 push** ✗。**结构披露**：本笔实现记录位于「§范围窄化」下的 `### 实现（2026-10-17，窄化范围）`，而 `## 完成区` 模板**仍为空**；内容如实、但位置偏离模板（按派单「不改内容」**未搬动**）。
- **分支披露**：本笔**无独立任务分支** —— 开工时改动已在 `master` 工作树，`AGENTS.md` 禁脏树 `switch -c` ⇒ 直接提交在 `master`（无 `merge`/分支可删）。

#### 第 2 轮 engineer 自审（A 部分，2026-10-17）

自主逐行审查（无嵌套子代理）；对象 = `DADAOSubtarget.cpp` / `DADAOISelLowering.cpp` 的 +55 行、`run.sh`、`gen_oracle.py`。判决 = **可交付**（A 部分范围内无未修项；B 部分项已在完成区列清）。

| finding（自审发现） | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 初版 oracle 的无符号期望把 `3.0e38` 当成 `3×2^126`，且 128 位常量用有符号左移拼接（UB 风险）；host gcc 与 target 同时 `rc=8`（两边一致、模型错） | ✅已修 | 期望改由「实际 double/float 位型的精确值」派生；常量统一走无符号表达式再转 `i128`；`ieee_bits` 补 `e > emax ⇒ inf` 早退 | host gcc `rc=0`、target `-O0/-O2` `rc=0`（189 项）；I2 注入（翻 1 位期望）仍能转红（qemu rc=3） |
| F2 `run.sh` 的正则写成 `__float(unt)?ti`，漏计 `__floatuntidf/isf` ⇒ S1 假红（float=2/4） | ✅已修 | 改 `__float(un)?ti[sd]f`（拼写 = `float`+`un`+`ti`+`df`） | 首跑 `float=4/4` 转绿；I1 注入少一 libcall 仍红（div/rem=3/4） |
| F3 `llvm-lit -q` 不打印 `Passed:` 行 ⇒ S4 解析空值假红 | ✅已修 | 以 `Total Discovered Tests` 取通过数、`Failed:` 缺省 0；仍以 `lit rc` 为红判据 | S4 `pass=31 fail=0 rc=0`；日志 `.work/log/infra/INFRA-079t-A-lit-codegen.log` |
| F4 S6 用 `git diff base -- llvm/lib/Target/DADAO` 统计改动文件数 ⇒ 把补丁集新增的 48 个文件全算进来（假红） | ✅已修 | 改为仅统计本笔两文件相对 base 的差异（期望 2） | S6 `dadao_changed=2`、`patches=78 series=78`、`HEAD=base+1`、clean |
| F5 原计划的「改后端源码」注入对**已编译**的 clang 无效（不重建就不变）⇒ 注入会假绿 | ✅已修（方案） | 注入改为落在**检查实际读取的产物**上：探针源（I1）、oracle 副本（I2）、archive 副本（I3）、补丁文件（I4） | `--inject` 全绿：4 条均检出 + `cp`+md5 还原 + 收尾复跑 rc=0 |
| F6 后端改动面复核：`*_PARTS` 只设 Custom 会残留 `fshl`（`expandShiftParts` 的实现依赖） | ✅已修 | 同批 `setOperationAction({ISD::FSHL, ISD::FSHR}, MVT::i64, Expand)` | 变量移位 0/1/31/32/63/64/65/127 等 21 例过 oracle；CodeGen lit 31/31 |
| F7 库调用语义边界：`s=0`（`FSHR(...,0)`）、`s=64`（条件支取符号）易错 | ✅不修（已验） | — | 移位用例含 `s=0/63/64/65/127` 与 `INT128_MIN`，target/host 均过；`shl128` 反汇编逐条核对（`shr.uo/or.o/cs.z`） |

**未修 finding**：无（F1–F5 已修、F6 已修、F7 验证通过；外部项见完成区「遗留问题」，非本笔缺陷）。

#### 第 3 轮 engineer 自审（B1 部分，2026-10-17）

自主逐行审查（无嵌套子代理）；对象 = `builtins/CMakeLists.txt` 的 arch 分支、`DADAO.cpp` 的链接路径、`Makefile` 的新规则、`run.sh`。判决 = **可交付**（B1 范围内无未修项；B2 / `install-host` 按派单留给后续）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 证据脚本 S3/S4 引用 `$W/crt0.o` 却从未汇编 ⇒ 首跑两条假红（`no such file or directory`） | ✅已修 | 新增 `make_crt0` 助手，两个检查各自在自己的目录汇编 crt0 | 复跑 S3 `checks=189 … rc=0`、S4 `libcalls-emitted=2/2 link+qemu rc=0` |
| F2 `ninja -n clang` 显示 14 步待做 ⇒ S7 红：组件 `commit --amend` 改了 `VCSRevision` | ✅已修 | 在**最后一次**组件提交后重建 build-tree clang（3m43s） | S7 `ninja -n clang: no work to do`；`ninja` 实跑 rc=0 |
| F3 排除项注释只写 `emutls.c` 需 `pthread.h`，而现场首个报错是 `stdlib.h` | ✅已修 | 注释按现场证据逐条改写（`stdlib.h`/`pthread.h`、`sys/mman.h`、`stdio.h`、`_Static_assert`、`_Unwind_*`） | 完成区「源集」逐条引用原文；S1 `excluded_leak=''` 复绿 |
| F4 `Makefile` 旧注释称 resource-dir `lib/`「no consumer / deliberately not installed」，与本笔事实矛盾 | ✅已修 | 改写该段：`lib/` 只放 builtins archive，且仍属 host prefix（D3） | 阅读核对 + `make -n install-host` 正常 |
| F5 `BUILTINS_*` 用 `:=` 在 parse 期展开：clean tree 上 clang/archive 尚未构建 ⇒ 变量为空、`install-host` 会误报 | ✅已修 | 改递归展开（`=`），求值推迟到 recipe 期（晚于 `build-mc`） | `make -n install-host` 仍解析出同一目标；S5 绿（两次 dry-run 稳定） |
| F6 `gcc_personality_v0.c` 因 `HAVE_UNWIND_H`（clang 自带 `<unwind.h>`）混入源集，而 unwind 超出 `D1` | ✅已修 | 加入 `REMOVE_ITEM` 并在注释写明依据 | archive 成员列表无该目标；I1 注入仍能显示 archive 内 `__divti3` 互引用 |
| F7 仅编译（`clang -c`）时 `-rtlib=` 仍会 `unused` | ❌不修（上游语义：`-rtlib` 是链接选项） | — | 本任务判据为链接期（S2 的 0 告警、S3 的 driver-only 链接），与上游 clang 行为一致 |

**未修 finding**：无（F7 非本笔缺陷，属上游语义）。

### B2 部分（2026-10-17，安装根复核 + 默认 rtlib 取证 + 移除 vendored 副本 + 四分类）

**测试结果**：证据 `.work/evidence/INFRA-079t-B2/run.sh` default **7 PASS / 0 FAIL（rc=0）**；`--inject` **I1–I5 全部转红**（程序退出码 42→43 ⇒ qemu 43；archive 去 `divti3.c.o` ⇒ `__divti3` 缺失；series 副本加陈旧项 ⇒ 14/15；archive 去 `muldc3/mulsc3.c.o` ⇒ link rc=1；四分类 JSON 翻 fail ⇒ pass 212/fail 1），`cp`+md5 还原各自一致、收尾复跑 rc=0（INJECT OK）。picolibc 全量四分类 **before 235/213/0/22/0**、**after 235/213/0/22/0**（逐例无转移；各 ~6m14s）；`build-picolibc` 全量重建 16 s（申报 5–10 min）。
**修改文件**：① 删 `components/picolibc/patches/libm/common/{muldc3.c,mulsc3.c,compiler_rt_builtins.h,meson.build}.patch`、`components/picolibc/series` 18→**14**；② `.work/source/picolibc/libm/common/` 删三源 + `meson.build` 恢复上游 `['signgam.c']`（组件检出 `commit --amend` ⇒ base+1 clean）；③ `components/picolibc/{README.md,changelog.md}`；④ `tools/testcases/picolibc_tests.py`（`link_target` 显式追加独立 archive，路径取自 `-print-libgcc-file-name -rtlib=compiler-rt`）；⑤ `.work/evidence/INFRA-079t-B2/{run.sh,prog.c,rtlib-sim-records.txt}`（新增）；⑥ `.tao/knowledge/issues.yaml`（`ISS-261`/`ISS-262`）。
**验收结果**：
- **安装根端到端**：真实 `_start`（`tests/scripts/codegen_crt0.s`）+ `prog.c`（14 libcall 全发出）→ `clang -rtlib=compiler-rt` **不带显式 archive** 链接（`-###` 链接行含安装根 archive）→ QEMU **rc=42**；安装根 archive `llvm-nm` **14/14** 符号 `T`（defs 134）。**工具缺失披露**：安装根 `bin/` 无 `llvm-nm` ⇒ 现场 `ninja -C .work/build/llvm llvm-nm`（rc=0，28 s）后用构建树 `llvm-nm`，未静默换命令（登记 `ISS-261`）。
- **默认 rtlib 结论 = 维持 opt-in（①）**：默认打开模拟（link-only wrapper，**不污染**编译器探测）实跑 —— `build-picolibc` 的 `libc.a` 与正常构建**逐字节相同**（md5 `f0a982a0…`；日志中目标链接命令 0 条）、`build-musl-shared` 的 `libc.so` **逐字节相同**（sha256 `d5fa2da3…`），无重复符号/undefined；链接行可同时含显式+driver archive 两次且 rc=0。**理由**：`ADR-0027 D5` 只规定归属/共用，未规定 driver 默认；D5 已由「同一独立 archive、musl 经 `LIBCC`、picolibc harness 显式链接」满足；默认切换是全局语义变化、无消费方需求 ⇒ 最小改动。**与 D5 的关系**：**不**声称满足「自动接线」；措辞差异登记 `ISS-262`（`status: open`，待用户/架构裁定，**未**自判 D5 失效）。
- **vendored 副本移除**：三件源 `.patch` + `meson.build.patch`（唯一 hunk = `srcs_common` 两源插入 ⇒ 撤回后整份无 diff）+ series 4 行全部撤回；source 侧 0 提及、0 文件；`libc.a` 无 `T __muldc3/__mulsc3`（1,802,402 → 1,798,824 B）。
- **独立库链接证据**：`libc.a` 0 定义 / archive 2 定义；picolibc 复乘程序**不带 archive → link rc=1**（`undefined symbol: __muldc3/__mulsc3`），**带 archive → rc=0、QEMU rc=42**；全量 harness 的 `test-complex-funcs`/`test-cpow` 等仍 pass。
- **门控（各留自身 rc）**：`check-patch-tree` **rc=0（173 补丁；改前 177，picolibc 18→14）**、`check-index-blobs`/`check-source-state`（picolibc base+1 clean）/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check_issues`（62 open）/`check-musl-freshness`/`check-syscall-abi`（69/69）/`make check`(L1) 全 **rc=0**。
**新发现/坑**：① `CCC_OVERRIDE_OPTIONS='+-rtlib=compiler-rt'` **不是有效模拟**：其诊断行污染 Meson `-Werror` 能力探测（YES→NO）⇒ picolibc `libc.a` 变 1,681,144 B 的**假结果**；改用「仅 link 命令追加」wrapper 后与正常构建逐字节一致。② `llvm-nm` 安装根与构建树都缺（`ninja llvm-nm` 28 s 补建）⇒ `ISS-261`。③ `libm/common/meson.build.patch` 唯一 hunk 即两源插入，撤回后整份 patch 被移除（合计删 4 件而非 3 件）。④ picolibc harness 直调 `ld.lld`、不经 driver ⇒ 独立 archive 必须显式命名（driver `-rtlib` 在此路径不参与）。
**遗留问题**：默认 rtlib **未接线**（结论 ①，`ISS-262` 待裁定；若改默认需 driver 改动 + `install-host`，本笔未做）；**未跑** `install-host`/L2/L3/`047t`/`046t` 复跑；**未** commit/push；**未改** 本册 `**状态**` 与 `milestones.md`；未越界改 `spec/`/`contracts/`。

#### 第 4 轮 engineer 自审（B2 部分，2026-10-17）

自主逐行审查（无嵌套子代理）；对象 = `tools/testcases/picolibc_tests.py` 的链接路径、picolibc 组件检出/补丁集、B2 证据脚本。判决 = **可交付**（B2 范围内无未修项）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 首版「默认打开」用 `CCC_OVERRIDE_OPTIONS` 模拟，诊断行污染 Meson 能力探测（`-Werror` YES→NO），`libc.a` 变小 117 KB（**假结果**） | ✅已修（方法） | 改为 link-only wrapper（仅无 `-c/-E/-S/-print-*` 时追加 `-rtlib`），重跑两消费方 | sim 与正常 `libc.a` md5 相同、`libc.so` sha256 相同；`-Werror` 探测 YES |
| F2 证据脚本 I1/I3/I5 先改后备份 ⇒ 还原成「注入后」内容，注入判据假红 | ✅已修 | 备份顺序改为「复制后立即备份」，还原自 `.bak` | `--inject` I1/I3/I5 均 `restore md5 OK`，rc=0 |
| F3 S6 的 `! grep '(^\|[^a-z])error:'` 把 `-Werror:` 当错误（大写 W 属 `[^a-z]`）⇒ 假红 | ✅已修 | 字符类改 `[^A-Za-z]` | S6 转绿；sim 日志无真实 `error:` |
| F4 `builtins_archive()` 在 `-print-libgcc-file-name` 空输出时会 `IndexError` | ✅已修 | 先取 `lines`，空则 `path=None` 并显式失败（rc=2） | 全量四分类复跑 rc=0；picolibc 用例仍 pass |
| F5 证据脚本曾把「双 archive」中间日志指向仓库内临时路径（`check-no-residue` 风险） | ✅已修 | 改为在 `/tmp/opencode/INFRA-079t-B2/` 现场生成 | `check-no-residue` rc=0；S6 双 archive 计数 2、rc=0 |
| F6 组件 README/changelog 仍描述「vendored 编入 `libc.a`」 | ✅已修 | README 改为独立库 + 链接方式；changelog 追加 M8 条目 | `check-component-changelog` rc=0；`make check` rc=0 |
| F7 默认 rtlib 若直接改 driver 默认，会使 B1 证据 S8（默认无 archive）失效，且需 `install-host`（本批禁止） | ✅不修（范围/裁定） | 仅取证 + 登记 `ISS-262`，未改 driver | 默认模拟与正常产物逐字节相同；本册「遗留问题」已披露 |

**未修 finding**：无（F7 属范围裁定，已登记 `ISS-262`，非本笔缺陷）。
