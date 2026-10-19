# LLVM-113t: i128 ↔ f128 的 libcall 补齐（`__floattitf`/`__floatuntitf`/`__fixtfti`/`__fixunstfti`）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`LLVM-106t`（f128 算术/比较/转换 libcall 注册块；本册在其后补 i128 四型）、`LLVM-110t`（现场暴露 + 基线日志 `.work/log/llvm/LLVM-110t-picolibc.log`）、`LLVM-112t`（16 B 栈对齐后的安装根基线；其 `install-host` 提供本册开工前工具链）、`ISS-283`（登记源；本册 = 落点）
**状态**：待开始

> **立册口径（2026-10-19，architect）**：这是 `ADR-0027`（compiler-rt builtins 接入）与 `ADR-0030`/`ADR-0031`（`long double` = binary128、f128 为合法类型）之后的**接线缺口补齐**，不是新决策、不改 ADR、不改契约。

## 执行环境
**执行环境**：本地

## 问题根源

**现场（逐字）**：`make build-picolibc` rc=2（`PICOLIBC_EXIT=2`），失败于 `libc.a.p/libc_stdio_strtold.c.o`：

```
fatal error: error in backend: unsupported library call operation
```

证据：`.work/log/llvm/LLVM-110t-picolibc.log`（562–564 行）、`.work/log/llvm/LLVM-110t-picolibc-exit.txt`。同一签名亦见 `INFRA-094t` 的 L2 残余红 ⇒ **既有缺口，非某册引入**（`ISS-283`）。

**根因（本笔实读源码）**：

- `DADAOSubtarget::initLibcallLoweringInfo()`（`.work/source/llvm-project/llvm/lib/Target/DADAO/DADAOSubtarget.cpp` 现 L140–177）已注册 f128 的算术/比较与 **i32/i64 ↔ f128** 转换，**没有 i128 四型**。
- `LegalizeIntegerTypes.cpp`：`ExpandIntRes_FP_TO_XINT`（L4492 起）用 `RTLIB::getFPTOSINT/getFPTOUINT`；`ExpandIntOp_XINT_TO_FP`（L6121 起）用 `RTLIB::getSINTTOFP/getUINTTOFP`。`TargetLoweringBase.cpp` 把 `f128 ↔ i128` 映射到 `FPTOSINT_F128_I128`/`FPTOUINT_F128_I128`/`SINTTOFP_I128_F128`/`UINTTOFP_I128_F128`（L379/428/481/529）。
- 非表架构（dadao）的 `RTLIB` 默认 `Unsupported`，未注册时 `makeLibCall` 直接报上述 fatal（同 `LLVM-103t` 机制）。
- `ADR-0030` + `ADR-0031` 之后 `i128 ↔ f128` 转换**实际可达**：picolibc `strtold.c` 的 `uint_to_fp` 路径即触发。

**需要的符号（现场 `llvm-nm --defined-only` 核 archive，非猜测）**：

- 安装根 `.dadao/cross-toolchain/lib/clang/23/lib/dadao-unknown-unknown-elf/libclang_rt.builtins.a`：`T __floattitf`、`T __floatuntitf`、`T __fixtfti`、`T __fixunstfti` **均已存在**。
- 构建树 `.work/build/compiler-rt-builtins/lib/dadao-unknown-unknown-elf/libclang_rt.builtins.a`：同四符号均为 `T`。
- **两个陈旧副本（不得用作符号证据）**：`.work/build/llvm/lib/clang/23/lib/dadao-unknown-unknown-elf/libclang_rt.builtins.a`（四个对应 `.o` 为空）、`.work/build/compiler-rt-builtins/lib/linux/libclang_rt.builtins-dadao.a`（仅 2 个符号）。
- `__trunctfxf2` / `__extendxftf2` 属 **f80/x87** 路径；本 target 无 f80（`LongDoubleWidth=128`）⇒ **不涉及、不添加**。

**结论**：缺的是**注册**，不是 builtins 实现；四处 `Info.setLibcallImpl(...)` 即可（见「改动清单」）。

## 接口规范

- **输入**：
  - `.work/source/llvm-project/`（组件检出）+ `components/llvm-project/patches/**` + `series` + `changelog.md`
  - 安装根 `.dadao/cross-toolchain/`（`install-host` 后新鲜）+ picolibc 源 `.work/source/picolibc/`（`patchless`，**只读**）
  - `ADR-0027` / `ADR-0030` / `ADR-0031`（均 `Accepted`）
- **输出**：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOSubtarget.cpp.patch`（四行注册 + 注释；`series` 条目数不变）
  - `components/llvm-project/changelog.md` 一条（M8）
  - 新增 lit：`tests/llvm/lit/CodeGen/DADAO/m8-i128-f128-libcall.ll`
  - 探针与独立 oracle：`.work/evidence/LLVM-113t/*`（`run.sh` default + `--inject`、`probe.c`、`gen_expected.py`、期望文件、运行日志）
  - 本任务书完成区
- **约束**：只改 `components/llvm-project/**` + `tests/llvm/lit/**` + 任务书；**不动** `spec/`、`.tao/contracts/`、`contracts/`、picolibc 源、`ISS-193` 排除表；**只补四个 i128↔f128 条目**，不得顺手铺开其它 libcall。

## 改动清单（写死）

`DADAOSubtarget.cpp` 在 f128 转换块末尾（现 L166–168 之后）加且只加：

```cpp
  // i128 <-> binary128 (LLVM-113t; ISS-283).  The i32/i64 forms above do not
  // cover the 128-bit integer conversions: with `long double` = binary128
  // (ADR-0030), picolibc's strtold.c reaches `uint_to_fp (i128 -> f128)` and
  // aborts with "unsupported library call operation" unless each is
  // registered.  Entry points are compiler-rt's GENERIC_TF_SOURCES.
  Info.setLibcallImpl(RTLIB::SINTTOFP_I128_F128, RTLIB::impl___floattitf_f128);
  Info.setLibcallImpl(RTLIB::UINTTOFP_I128_F128, RTLIB::impl___floatuntitf_f128);
  Info.setLibcallImpl(RTLIB::FPTOSINT_F128_I128, RTLIB::impl___fixtfti_f128);
  Info.setLibcallImpl(RTLIB::FPTOUINT_F128_I128, RTLIB::impl___fixunstfti_f128);
```

- 枚举与 impl 名以生成物 `.work/build/llvm/include/llvm/IR/RuntimeLibcalls.inc` 现场核对为准（`impl___*_f128`，**不是** `_ppcf128`）。
- 编辑必须在 `.work/source/llvm-project` 内进行，随后 `python3 tools/infra/make_patch.py llvm-project` 导出（禁手工编辑 `.patch`）。

## 探针（必做；独立 oracle）

`probe.c`（C，`long double` = f128）四组，覆盖**四种转换**：

1. `sitofp i128 -> f128`：`(__int128)` 值转 `long double`。
2. `uitofp i128 -> f128`：`(unsigned __int128)` 值转 `long double`。
3. `fptosi f128 -> i128`：`long double` 转 `__int128`（含小数截断向零）。
4. `fptoui f128 -> u128`：`long double` 转 `unsigned __int128`。

**取值（全部 ≤113 位有效位，binary128 可精确表示；避免 UB）**：

- `2^100 + 2^40`、`2^127 - 2^64`（u128/i128 正例）
- `-(2^100 + 2^40)`（i128 负数）
- `3.75` / `-3.75`（fptosi 截断到 `3` / `-3`）
- `2^127`（fptoui 上界）
- 负值不参与 `fptoui`（UB）；超范围不参与。
- 输入用 `volatile` 防常量折叠；输出按 128 位整数的**高 64 / 低 64 半**打印。

**独立 oracle**：`gen_expected.py` 只用 Python 标准库 `int` / `fractions.Fraction`，从同一组数学定义算出期望（同样拆高/低半），生成 `expected.h`；**不得**调用 clang/llvm 或从编译器输出反推。`run.sh` 逐行 diff 实际与期望，并断言 `llc -O2` 汇编中出现 `call [rb0, __floattitf]` 等四个符号。

- 编链口径 = `TESTCASES-047t` 静态档（安装根 clang + musl `libc.a` + compiler-rt builtins），`qemu-dadao` 运行；退出码 0。

## 验收标准

1. **修前基线 + 修后构建**：修前复现 `make build-picolibc` 同一 fatal（原文落盘）；修后**同批重编 `clang` 与 `llc`（防旧注册表假绿）** + **单跑 `install-host`** + `make build-picolibc` **rc=0**（`PICOLIBC_EXIT=0`）；日志中 `Compiling C object libc.a.p/libc_stdio_strtold.c.o` 为**本轮真实编译**（非增量跳过），且无 `unsupported library call operation`。
2. **四转换探针**：四种转换全部通过；`run.sh` default rc=0；每个值逐条对独立 Python oracle 一致；`llc` 汇编四个符号各至少 1 次。若构建继续暴露**同类** i128↔f128 缺口，可按证据最小补并记录；若暴露其它类缺口（f80/其它 libcall/非 libcall），**停下报告**，不扩大范围。
3. **lit**：新增 `m8-i128-f128-libcall.ll` PASS（四函数、`CHECK` 四个符号），且对**修前**后端可达 FAIL（报错原文或旧 `.s`）；`make check-lit` rc=0、无回归（报总数）。
4. **无回归（抽样）**：`TESTCASES-047t` 两档 `--filter 'functional/(strtold|strtod|strtod_long)$'`（`--json-out` + `--work-dir` 显式，`INFRA-093t`）；与**同一轮改前基线**逐例一致（无新增 `fail`/`blocked`；计数如实报告）。本册只改 libcall 注册，期望计数不变。
5. **可达 FAIL（≥3）**：① 删一条新增注册 ⇒ 构建/探针失败；② 把 `impl___floattitf_f128` 改成错误 impl ⇒ 汇编符号断言失败；③ 篡改期望值一个字节 ⇒ 探针 diff 失败。注入均用 `cp` 备份 + md5 对账还原，**禁** `git checkout/restore/stash`。
6. **门控（各留自身 rc）**：`check-patch-tree`、`check-component-changelog`、`make check`(L1)、`make check-tasks`、`check-knowledge-refs`、`check-no-residue`、`check-milestones-fresh`、`check_issues`。
7. **L2 交接**：`make check-modules`（L2）**由主会话另跑**（本册工程师只到构建树 + L1）；主会话判据 = rc=0（`build-picolibc` 红转绿）。

## 不做

- 不补其它 i128/f128 libcall（`__trunctfxf2`/`__extendxftf2` 属 f80，本 target 无此类型）、不铺开数学 family。
- 不改 `ISS-193` 的 picolibc 排除表、不改 picolibc 源、不改 `spec/` / 契约。
- 不做 `LLVM-102t` / `LLVM-108t` / `ISS-267` 等其它挂账。

## 硬约束

1. 临时目录 `/tmp/opencode/LLVM-113t/`；workdir = 仓库根、相对路径；禁出界 `cd`；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；留证捕被检命令自身退出码（禁 `cmd | tee`）；长输出落 `.work/log/llvm/`。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（范围变化/新决策）时留问。
6. 用户裁定须把**原话**写入本任务书。
7. 补丁导出纪律：`/tmp` 写入、行数下限/非空 blob、`check-patch-tree` 全绿。
8. **重建申报**：改 `components/llvm-project` ⇒ 重建 `clang`+`llc` 并单跑 `install-host`（`ISS-210`，串行、不并发）；启动前申报预计耗时。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填写）

#### 第 1 轮 reviewer 验收
（待填写）
