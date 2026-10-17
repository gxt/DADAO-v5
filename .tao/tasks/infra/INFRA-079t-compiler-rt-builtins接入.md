# INFRA-079t: compiler-rt builtins 接入（独立库 + 后端接入点 + 端序敏感验证）

**模块**：infra
**项目里程碑**：M8
**依赖**：`ADR-0027`（compiler-rt builtins 支持口径，`Accepted`，`D1`–`D5` = 本任务**唯一真源**）；`INFRA-078t`（compiler-rt 支持预研：缺口 / 符号差 / 接入点来源，**只读**）；`LLVM-091t`（`llvm-project 23.1.3` 已落地 = 补丁面基线）；`INFRA-067t`（picolibc vendored `__mulsc3`/`__muldc3` 的来源，本任务**移除**该 vendor）；消费方 = M8 `P1`（musl 静态）及其后各段
**状态**：待开始

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
