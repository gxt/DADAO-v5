# LLVM-115t: picolibc `ld128` 数学引擎（`__*_engine`）接入 —— `math_test` 链接解阻

**模块**：llvm
**项目里程碑**：M8
**依赖**：`LLVM-113t`（i128 ↔ f128 四转换 libcall：`__floatuntitf` 等；`atold_engine.c` 的 `_u128_to_ld` 直用）、`LLVM-114t`（f128 math libcall：`__multf3` 之外的 `floorl`/`rintl`… 已注册，`build-picolibc` 已回 rc=0）、`LLVM-106t` + `INFRA-090t`（`long double` = binary128，`ADR-0030`/`ADR-0031`）、`LLVM-109t`（现场暴露者；本册 = 其「遗留问题」落点）、`ISS-193`（(f) 类登记源）
**状态**：待开始

> **立册口径（2026-10-19，architect）**：这是 binary128 落地后的**消费侧链接缺口**（picolibc 自身源码未接进构建），不是新决策；不改 ADR、不改契约、**不扩过滤表**。归属（picolibc 自身源 vs 另一来源）**先诊断、后定落点**，禁止预设。

## 执行环境
**执行环境**：本地

## 问题根源

### 现场（逐字，2026-10-19）

`make check-picolibc-tests`：`build-picolibc` **PASS**（`libc.a` 2,025,904 B），逐例
`total=20 pass=17 fail=0 excluded=2 blocked=1` ⇒ **make rc=2**（`.work/log/testcases/LLVM-109t-leftover-picolibc.log`）。唯一 blocked：

```
math_test  newlib.math  blocked  undefined symbol: __atold_engine
           (source excluded by the backend-gap filter; see meson.build / ISS-193)
```

`nm -A .dadao/dadao-unknown-elf/lib/libc.a`（现场）：

```
libc_stdio_strtold.c.o:  U __atold_engine
libc_stdio_wcstold.c.o:  U __atold_engine
```

同 archive 内其余引擎符号均为 `T`：`__atod_engine` / `__atof_engine` / `__dtoa_engine` / `__dtox_engine` / `__ftoa_engine` / `__ftox_engine` / `__ldtoa_engine` / `__ldtox_engine` ⇒ **唯一缺 `__atold_engine`**。

### 根因链（本笔实读源码，`file:line`）

1. `long double` 由 `double` 改为 **IEEE binary128**（`ADR-0030`；`__SIZEOF_LONG_DOUBLE__ = 16`）。
2. `libc/stdio/strtold.c:67` `#include "conv_flt.c"`；`conv_flt.c:87-92` 对 `STRTOLD` 定义 `_NEED_IO_LONG_DOUBLE`。
3. `libc/stdio/dtoa.h:60-77`：`_NEED_IO_LONG_DOUBLE` 且 `__SIZEOF_LONG_DOUBLE__ > 8` ⇒ 定义 `_NEED_IO_FLOAT_LARGE`。
4. `libc/stdio/conv_flt.c:579-584`：`_NEED_IO_FLOAT_LARGE` 且 `CHECK_LONG_LONG() && __SIZEOF_LONG_DOUBLE__ > 8` ⇒ `flt = (FLOAT)__atold_engine(...)`；即 **`strtold` 的十进制→long double 路径**依赖该符号。
5. 定义在本树**唯一一处**：`libc/stdio/atold_engine.c:108`（`git grep` 全树核对；`local-stdio.h:409` / `atold_engine.c:110` 的 `_u128_to_ld` = `(long double)u128`，另有多条 `long double` 乘）。
6. 该 TU 被**我方 meson 补丁排除**：`components/picolibc/patches/meson.build.patch` 的 `_dadao_backend_blocked` 列表含
   `'atold_engine.c'`，注释 = `long-double strtod engine libcall unsupported; ISS-193 (f)`。
   历史上（`long double` = 64 位时）该源编译失败，签名 = `error in backend: unsupported library call operation`（`LLVM-088t`/`LLVM-089t` 现场复跑，见 `.tao/archive/M7/`）。

### 归属待现场判定（**不许预设**）

先对 `atold_engine.c` 做**单源重编诊断**（用安装根/构建树 clang，`-O2 -c`，输出落 `.work/log/llvm/LLVM-115t-*`），按结果三选一：

- **A（picolibc 自身源、过滤已陈旧）**：现在能编译 ⇒ 最小修法 = **只从 `_dadao_backend_blocked` 删 `atold_engine.c` 这一条**（同步注释/计数），`series` 条目数不变；picolibc 上游源零改动。
- **B（picolibc 自身源、仍缺后端能力）**：仍 `unsupported library call operation` / `Cannot select` ⇒ 记录**逐字签名 + DAG 节点/目标 libcall**；若缺的是 RTLIB 注册（如某 f128 运算），按 `LLVM-113t`/`LLVM-114t` 同法**只补该一条**（后端补丁 + 单跑 `install-host`），不得改过滤表扩面。
- **C（另一来源）**：若现场证明符号应由 musl / compiler-rt / 其它组件提供（例如 picolibc 本树定义不可用）⇒ **保留现场证据**并在完成区给「为什么不能用 picolibc 自身源 + 拟接入来源/落点」，交主会话裁定；**不得**在未证实前改组件边界或加 stub。

**禁止**：扩 `_dadao_backend_blocked`、加空实现/弱符号掩盖、改 picolibc 上游源（`.work/source/picolibc` 只读，改动一律走 `components/picolibc/patches/**`）。

## 接口规范

- **输入**：
  - `components/picolibc/patches/meson.build.patch`（过滤表现场为 2 条：`hash_page.c`= `ISS-193` (c)、`atold_engine.c`= (f)）、`components/picolibc/{series,changelog.md,README.md}`
  - `.work/source/picolibc/`（**只读**；诊断对象 `libc/stdio/atold_engine.c`）
  - 安装根 `.dadao/dadao-unknown-elf/`（`libc.a` 与头文件）+ `.dadao/cross-toolchain/`（clang；本册若动后端须先单跑 `make install-host`）
  - `tools/testcases/picolibc_tests.py`（`make check-picolibc-tests` = `--stage fast`）与 `tools/infra/build_picolibc.py`
  - `tests/scripts/{codegen_crt0.s,dadao.lds}`（harness 链接载体，现状可跑）
  - `TESTCASES-047t` 驱动 + 权威跑基线（只读参照）：静态 `.work/tests/authoritative/20261019T063001Z-libc-test-user-static/run.json`（`pass 309 / fail 0 / known-fail 4 / blocked 24`）、动态 `20261019T063847Z-libc-test-user-dynamic/run.json`（`312 / 0 / 4 / 21`）
- **输出**（按诊断结论取实际分支需要的）：
  - `components/picolibc/patches/meson.build.patch`（A：删 1 条 + 注释；B/C 不删）
  - 可能的 `components/llvm-project/patches/**` + `series` + `changelog.md`（仅 B）
  - `components/picolibc/changelog.md` 一条（M8；仅当改了 picolibc 补丁）
  - `.work/evidence/<任务ID>/run.sh`（`default` + `--inject`）+ `probe.*` + 独立 oracle 生成器 + 期望文件 + 日志
  - 本任务书完成区
- **约束**：只改与本缺陷直接相关的文件；**不动** `spec/`、`.tao/contracts/`、`contracts/`、picolibc 上游源、`ISS-193` 的 (c) 条目；`check-patch-tree` 计数须与改动一致（A 分支应仍为 **181**）。

## 验收标准

1. **`make check-picolibc-tests` rc=0**：`math_test` 由 `blocked` 转 **`pass`**，且 `blocked=0`、`fail=0`（预期 `total=20 pass=18 excluded=2`；计数若因 harness 枚举变化而不同，须现场派生并逐条解释）。若 C 分支证明不能修，须给出**有据**说明（逐字链接错误 + 归属 + 为何不能接入），且**不得**把 `blocked` 静默改成 `excluded`。
2. **`047t` 5 个 `long double` 例两档仍 `pass`**：`math/{acoshl,asinhl,erfcl,lgammal,tgammal}`（基线见上；两档各 5/5 `pass`、各自 `fail=0`；带 `--json-out` 留档）。
3. **探针（独立 oracle，禁从被测实现反推）**：
   - `strtold`：至少 4 组十进制串（>53 位有效数字、恰半值 tie、极小/极大边界各 1），用 Python **精确有理数 + binary128 就近偶数舍入**（或等价可复算实现）算出 16 B 期望，与 guest 内 `long double` 的 `memcpy` 原始字节**逐字节**比对；
   - `long double` 数学：至少 2 个函数（如 `sqrtl`/`logl`/`powl`）用精确值或明确容差做独立 oracle（说明容差来源；libm 非正确舍入，禁伪称 bit-exact）；
   - 探针必须真实经过 `__atold_engine` 路径（`strtold` 入口），并给出改前/改后或断言的**可达 FAIL**。
4. **可达 FAIL**：证据脚本 `default` 全绿；`--inject` 至少 3 处注入（如临时恢复过滤条目 / 错误期望字节 / 错误计数）各自能转红，`cp` 备份 + md5 对账还原（**禁** `git checkout/restore/stash`）。
5. **`install-host` 前置**：若改后端补丁，单跑 `make install-host` 并用安装根复验；若仅改 picolibc 补丁，记录安装根 `clang --version` / 时间戳证明未用陈旧工具链。**不与其它 build/任务并发**。
6. **L2 由主会话复跑**（engineer 不跑 `check-modules`/`check-full`；本册只跑 `check-picolibc-tests` + L1 + 047t 子集）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
