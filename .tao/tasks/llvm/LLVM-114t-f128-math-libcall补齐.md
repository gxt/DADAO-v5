# LLVM-114t: f128 math libcall 补齐（`libm/ld/*.c` 的 12 个 TU）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`LLVM-113t`（同一缺陷面的前一笔：i128↔f128 四型已注册、`strtold.c` 已通；本册续补 libm 面，同分支同法）、`LLVM-106t`（f128 算术/比较/转换 libcall 注册块；本册在其后补 math 面）、`ADR-0030`/`ADR-0031`（`long double` = binary128；f128 为合法类型）、`ISS-283`（登记源；本册 = 余项落点）
**状态**：待开始

> **立册口径（2026-10-19，architect）**：这是 `LLVM-113t` **范围披露**的余项（12 个 `libm/ld/*.c` 同类缺 libcall），属**接线缺口补齐**，不改 ADR、不改契约、不改 `spec/`。

## 执行环境
**执行环境**：本地

## 问题根源

**现场（逐字）**：`LLVM-113t` 修复后 `make build-picolibc` 仍 rc=2。`ninja -k 0` 的**全部 12 个**编译失败 TU（`.work/log/llvm/LLVM-113t-picolibc-keepgoing.log`，`grep -c "unsupported library call operation"` = **12**）：

```
libc.a.p/libm_ld_e_tgammal.c.o     libc.a.p/libm_ld_e_expl.c.o
libc.a.p/libm_ld_e_lgammal_r.c.o   libc.a.p/libm_ld_s_expm1l.c.o
libc.a.p/libm_ld_e_powl.c.o        libc.a.p/libm_ld_s_lrintl.c.o
libc.a.p/libm_ld_s_llrintl.c.o     libc.a.p/libm_ld_s_lroundl.c.o
libc.a.p/libm_ld_s_llroundl.c.o    libc.a.p/libm_ld_s_rintl.c.o
libc.a.p/libm_ld_s_roundl.c.o      libc.a.p/libm_ld_s_scalbl.c.o
```

每条均为 `fatal error: error in backend: unsupported library call operation`（栈 `LegalizeTypes` → `makeLibCall`）。

**根因**：`DADAOSubtarget::initLibcallLoweringInfo()`（`.work/source/llvm-project/llvm/lib/Target/DADAO/DADAOSubtarget.cpp`）的 f128 块只注册了算术（add/sub/mul/div）、扩展/收缩、i32/i64/i128 转换与 7 条比较；**math 面（floor/rint/round/trunc/log…）未注册**。非表架构（dadao）的 `RTLIB` 默认 `Unsupported`，`TargetLowering::makeLibCall`（`TargetLowering.cpp:160`）遇 `Unsupported` 直接 fatal（同 `LLVM-103t`/`LLVM-113t` 机制）。

### 现场全枚举（architect 只读诊断，2026-10-19；未改任何文件）

方法：对 `libm/ld/` **全部 79 个 TU** 用构建树 clang 取 `-O2 -S -emit-llvm`（仅前端、不经 ISel），扫描 f128 intrinsic；再对每个候选 intrinsic 用最小 `.ll` 跑构建树 `llc -march=dadao -O2` 复现 fatal。

| TU | f128 intrinsic（需 libcall） |
|---|---|
| `e_expl.c` / `e_lgammal_r.c` / `e_powl.c` / `s_expm1l.c` / `s_roundl.c` | `llvm.floor.f128` |
| `e_tgammal.c` / `s_rintl.c` / `s_lrintl.c` / `s_llrintl.c` | `llvm.rint.f128` |
| `s_lroundl.c` / `s_llroundl.c` | `llvm.round.f128` |
| `e_powl.c` / `s_scalbl.c` | `llvm.trunc.f128` |
| `e_lgammal_r.c` | `llvm.log.f128` |

- **不需注册**（已实证 rc=0）：`llvm.copysign.f128`（`e_sinhl.c`/`s_nextafterl.c`，位操作展开）；`llvm.fmuladd.f128`（`e_expl.c`/`e_lgammal_r.c`/`e_powl.c`/`s_expm1l.c`，展开为 `__multf3` + `fadd`，**不走 `FMA_F128`**）；`llvm.fabs.f128`（位操作）。
- **最小 IR 复现**（构建树 `llc`，`-O2`）：`floor`/`rint`/`round`/`trunc`/`log` 各 **rc=134**（`unsupported library call operation`）；`sqrt`（`llvm.sqrt.f128`）**rc=134**、严格 `fma`（`llvm.fma.f128`）**rc=134** ⇒ 二者为**latent**（12 个 TU 未触及，但用户证词 + 最小 IR 均证明缺口真实）。

### 注册目标（`.work/build/llvm/include/llvm/IR/RuntimeLibcalls.inc` 现场核对）

| RTLIB 枚举 | impl | 符号 | 归属 |
|---|---|---|---|
| `FLOOR_F128` | `impl_floorl_f128`（:16069） | `floorl` | libm（非 builtins） |
| `RINT_F128` | `impl_rintl_f128`（:16335） | `rintl` | libm |
| `ROUND_F128` | `impl_roundl_f128`（:16348） | `roundl` | libm |
| `TRUNC_F128` | `impl_truncl_f128`（:16461） | `truncl` | libm |
| `LOG_F128` | `impl_logl_f128`（:16208） | `logl` | libm |
| `SQRT_F128` | `impl_sqrtl_f128`（:16395） | `sqrtl` | libm |
| `FMA_F128` | `impl_fmal_f128`（:16078） | `fmal` | libm |

**符号归属（现场 `nm` 实证）**：上述 7 个符号在 musl `libc.a` 与 `libc.so` 均为 `T`（`.dadao/dadao-unknown-elf/lib/`）；安装根 compiler-rt `libclang_rt.builtins.a` **均无**（⇒ 不是 builtins，`ADR-0027` 不涉及）；`libm.a` 是**空 archive**（picolibc/musl 合并 libc+libm），**不得**用 `-lm` 或 `libm.a` 判符号存在性。picolibc 自身构建这 7 个 TU（`libm/ld/s_floorl.c` 等），其实现**不**再触发同名 libcall（IR 扫描无自调用）⇒ 无递归风险。

## 接口规范

- **输入**：
  - `.work/source/llvm-project/`（组件检出）+ `components/llvm-project/patches/**` + `series` + `changelog.md`
  - 安装根 `.dadao/cross-toolchain/`（本册须先单跑 `install-host` 刷新）+ picolibc 源 `.work/source/picolibc/`（**只读**，不改）
  - `ADR-0027` / `ADR-0030` / `ADR-0031`（均 `Accepted`）
- **输出**：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOSubtarget.cpp.patch`（7 行注册 + 注释；`series` 条目数不变）
  - `components/llvm-project/changelog.md` 一条（M8）
  - 新增 lit：`tests/llvm/lit/CodeGen/DADAO/m8-f128-math-libcall.ll`
  - 探针与独立 oracle：`.work/evidence/LLVM-114t/*`（`run.sh` default + `--inject`、`probe.c`、`gen_expected.py`、期望文件、运行日志）
  - 本任务书完成区
- **约束**：只改 `components/llvm-project/**` + `tests/llvm/lit/**` + 本任务书；**不动** `spec/`、`.tao/contracts/`、`contracts/`、picolibc 源、`ISS-193` 排除表。

## 改动清单（写死）

`DADAOSubtarget.cpp` 在 `LLVM-113t` 的四行 i128 注册之后加且只加：

```cpp
  // f128 math libcalls (LLVM-114t; ISS-283 remainder).  The 12 remaining
  // picolibc libm/ld TUs lower floor/rint/round/trunc/log (and latent sqrt/fma)
  // to out-of-line calls; without registration makeLibCall aborts with
  // "unsupported library call operation".  These are libm entry points
  // (musl/picolibc `libc.a`), not compiler-rt builtins.
  Info.setLibcallImpl(RTLIB::FLOOR_F128, RTLIB::impl_floorl_f128);
  Info.setLibcallImpl(RTLIB::RINT_F128, RTLIB::impl_rintl_f128);
  Info.setLibcallImpl(RTLIB::ROUND_F128, RTLIB::impl_roundl_f128);
  Info.setLibcallImpl(RTLIB::TRUNC_F128, RTLIB::impl_truncl_f128);
  Info.setLibcallImpl(RTLIB::LOG_F128, RTLIB::impl_logl_f128);
  Info.setLibcallImpl(RTLIB::SQRT_F128, RTLIB::impl_sqrtl_f128);
  Info.setLibcallImpl(RTLIB::FMA_F128, RTLIB::impl_fmal_f128);
```

- 前 5 行 = **构建必需**；后 2 行 = **latent 闭合**（用户已证 + 最小 IR rc=134；一条注册即闭合，避免下一轮挤牙膏）。
- 枚举/impl 名以生成物 `RuntimeLibcalls.inc` 现场核对为准（**不是** `_ppcf128`）。
- 编辑必须在 `.work/source/llvm-project` 内进行，随后 `python3 tools/infra/make_patch.py llvm-project` 导出（禁手工编辑 `.patch`）。

## 探针（必做；独立 oracle）

`probe.c`（C，`long double` = f128）逐项覆盖 **7 条**，输入 `volatile` 防常量折叠；输出按 f128 的**高 64 / 低 64 半**与整数结果打印：

1. `floorl`：`±3.75`、`±0.5`、`-0.0` ⇒ `3`/`-4`/`0`/`-1`。
2. `rintl`：`0.5`/`1.5`/`2.5`/`-2.5`（默认 round-to-nearest-even）⇒ `0`/`2`/`2`/`-2`。
3. `roundl`：`0.5`/`1.5`/`2.5`/`-2.5`（half away from zero）⇒ `1`/`2`/`3`/`-3`。
4. `truncl`：`3.75`/`-3.75` ⇒ `3`/`-3`。
5. `logl`：取 2 的幂（`1`/`2`/`0.5`/`8`）⇒ `0`/`1`/`-1`/`3`（binary128 精确，避免 `e` 类无理数需要舍入 oracle）。
6. `sqrtl`：`1.5625`（=1.25²）/`4`/`0.25` ⇒ `1.25`/`2`/`0.5`（精确）。
7. `fmal`：`a*b+c` 取**积与和均可精确表示**的组合（如 `1.5*2 + 0.25`、`2^60*2^-60 + 3`、`-1.5*-2 + -0.5`），exact `Fraction` 即可，无需实现 binary128 舍入。

**独立 oracle**：`gen_expected.py` 只用 Python 标准库 `int` / `fractions.Fraction`（必要时 `decimal`），按**同一组数学定义**算期望（floor/trunc/half-even/half-away/log 以 2 的幂取精确值/sqrt 以完全平方取精确值/fma 以可精确表示组合），生成 `expected.h`；**不得**调用 clang/llvm 或从编译器输出反推。`run.sh` 逐行 diff 实际与期望，并断言 `llc -O2` 汇编中出现 `call [rb0, floorl]`/`rintl`/`roundl`/`truncl`/`logl`/`sqrtl`/`fmal` **各至少 1 次**。

- 编链口径 = `TESTCASES-047t` 静态档（安装根 clang + musl `libc.a` + compiler-rt builtins），`qemu-dadao` 运行；退出码 0。

## 验收标准

1. **修前基线 + 修后构建**：修前复现 12 TU 的同一 fatal（原文落盘；可复用 `LLVM-113t` 日志并**本轮再跑一次**确认）；修后**同批重编 `clang` 与 `llc`** + **单跑 `install-host`**（串行，申报耗时），再 `make build-picolibc` **rc=0**（`PICOLIBC_EXIT=0`）。日志须证明：① `build_picolibc.py` 的 toolchain stamp 判**过期并 wipe**（`install-host` 后必然，见 `ISS-248`），12 个 TU 与 `strtold.c` 均为**本轮真实编译**（非增量跳过）；② 全文无 `unsupported library call operation`。
2. **七项探针**：7 条全部通过；`run.sh` default rc=0；逐值对独立 Python oracle 一致；汇编七符号各 ≥1 次。若构建又暴露**同类 f128 math libcall**（本册 7 条之外），按「先全枚举、再一次补齐」处理并记录；若暴露**其它类**缺口（非 libcall / f80 / 非 math），**停下报告**，不扩大范围。
3. **lit**：新增 `m8-f128-math-libcall.ll` PASS（7 个函数、`CHECK` 七个符号），且对**修前**后端可达 FAIL（abort 或旧 `.s`）；`make check-lit` rc=0、无回归（报总数）。
4. **无回归（抽样）**：`TESTCASES-047t` 两档 `--filter 'functional/(strtold|strtod|strtod_long)$'`（`--json-out` + `--work-dir` 显式，`INFRA-093t`）；与**同轮改前基线**逐例一致（无新增 `fail`/`blocked`；计数如实报告）。
5. **可达 FAIL（≥3）**：① 删一条构建必需注册（如 `FLOOR_F128`）⇒ 构建/探针失败；② 把 `impl_logl_f128` 改成错误 impl ⇒ 汇编符号断言失败；③ 篡改期望值一个字节 ⇒ 探针 diff 失败。注入用 `cp` 备份 + md5 对账还原，**禁** `git checkout/restore/stash`。
6. **门控（各留自身 rc）**：`check-patch-tree`（**181** 不变）、`check-component-changelog`、`make check`(L1)、`make check-tasks`、`check-knowledge-refs`、`check-no-residue`、`check-milestones-fresh`、`check_issues`。
7. **L2 交接**：`make check-modules`（L2）**由主会话另跑**（本册工程师只到构建树 + L1）；判据 = rc=0（`build-picolibc` 红转绿）。

## 不做

- 不补本册 7 条之外的 f128 math（`exp`/`exp2`/`pow`/`sin`/`cos`/`tan`/`rem`/`remainder`/`ldexp`/`scalbn`/`lrint`/`llrint`/`lround`/`llround`/`ceil`/`nearbyint` 等）——**无现场证据**；如需另立。
- 不补 f80/x87（本 target `LongDoubleWidth=128`）、不改 `ISS-193` 排除表、不改 picolibc 源、不改 `spec/` / 契约 / ADR。
- 不做 `LLVM-102t` / `LLVM-108t` / `ISS-267` 等其它挂账。

## 硬约束

1. 临时目录 `/tmp/opencode/LLVM-114t/`；workdir = 仓库根、相对路径；禁出界 `cd`；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；留证捕被检命令自身退出码（禁 `cmd | tee`）；长输出落 `.work/log/llvm/`。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（范围变化/新决策）时留问。
6. 用户裁定须把**原话**写入本任务书。
7. 补丁导出纪律：`/tmp` 写入、行数下限/非空 blob、`check-patch-tree` 全绿。
8. **重建申报**：改 `components/llvm-project` ⇒ 重建 `clang`+`llc` 并单跑 `install-host`（`ISS-210`，串行、不并发）；启动前申报预计耗时（参考：`LLVM-113t` 的 `ninja clang llc -j8` = 242.9 s）。

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
