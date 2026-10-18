# LLVM-106t: `long double` = binary128 全链（clang target + ABI 双槽 + 后端 f128 + builtins TF）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`ADR-0030`（`Accepted`：`long double` = binary128 / RF 双槽 / builtins 全量 / 排 `M9`）、`ADR-0031`（`Accepted`：16 B 值高半在偶号、不拆半、16 B 栈对齐）、`ADR-0027`（builtins 全量 + 独立库）、`INFRA-079t`（`已验证`：compiler-rt builtins 接入）、`INFRA-088t`（driver 默认接 builtins；验收前须 `已验证`）、`INFRA-090t`（musl `bits/float.h` 常量块；**联动**）、`ISS-250`（`libc-test` 5 例 `_l` 偏移）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 问题根源

`long double` 在本 target 上现状 = `double`（8 B / 53 位），与 `ADR-0030 D1` 的 binary128 定案不符；binary128 的四条链（前端类型、ABI 传参/返回、后端 `f128`、软浮点库）**均未接通**，逐条现场：

1. **前端类型 = 64 位**：`components/llvm-project/patches/clang/lib/Basic/Targets/DADAO.h.patch` 的 `LongDoubleWidth = LongDoubleAlign = 64`（`LongDoubleFormat` 未覆写 ⇒ 取默认 binary64）⇒ `__SIZEOF_LONG_DOUBLE__=8` / `__LDBL_MANT_DIG__=53`。
2. **`_Float128` 未开**：`DADAO.h` 未设 `HasFloat128` / `Float128Format` ⇒ `_Float128` 不可用。`ADR-0030` 的库侧（musl `_l`、compiler-rt TF 源）都以 `_Float128`/`__float128` 与 `long double` 同宽为前提。
3. **ABI = RF 偶-奇双槽**：`ADR-0030 D2`（`(a)`）+ `ADR-0031 D6`（**高半在偶号**，`rf16`=高 / `rf17`=低；返回 `rf8`=高 / `rf9`=低；配对自偶号起，不足整值退栈、不拆半）。现状 clang `DADAOABIInfo` / 后端调用约定无 `f128` 载体（RF 只有 64 位槽）。
4. **后端 `f128` 未合法化**：`llvm/lib/Target/DADAO/**` 无 `f128` 类型/运算的 legalize 与 libcall lowering；`DataLayout` 已含默认 `f128:128:128`（`ADR-0030` 事实基线 11），存储面无需改串。
5. **builtins TF 源是空对象**：安装根 `libclang_rt.builtins.a` 有 24 个 `*tf*.o` 成员，但 **0 个 TF 符号**（`__addtf3`/`__multf3`/… 全无；`addtf3.c.o` 的 `.text` size = 0）——根因 = `CRT_HAS_TF_MODE` 在无 f128 的 target 上为假，`#if defined(CRT_HAS_TF_MODE)` 整段被预处理器丢掉。**顺序硬约束**：必须先把前端/后端 `f128` 接通、再重建 builtins，TF 源才会真正产出符号。
6. **musl 常量块仍是 binary64**：`.work/source/musl/arch/dadao/bits/float.h` 写死 `__SIZEOF_LONG_DOUBLE__ == 8`（归 `INFRA-090t`，本册不改 musl）。

## 接口规范

- **输入**：
  - `.work/source/llvm-project/`（组件源码检出，`git` 干净基线）
  - `components/llvm-project/patches/**`（树形补丁集，一文件一补丁）+ `series` + `changelog.md`
  - 契约 / 决策：`ADR-0030`（`D1` 格式与尺寸、`D2` RF 双槽、`D3` 软浮点、`D4` 常量）、`ADR-0031`（`D6` 半字顺序、`D7` 栈对齐）、`spec/DADAO-21-ABI §2.1`/`§2.2`/`§3.2.2`/`§3.2.3`/`§3.2.4`/`§3.4`（只读引用）、`contract-abi §4.2`/`§4.3`/`§4.4`（16 B 值与返回对）
  - `compiler-rt/lib/builtins/**`（`GENERIC_TF_SOURCES` 现成，`addtf3.c` 等）+ 安装根 `.dadao/cross-toolchain/`（改 `components/**` ⇒ 必须 `install-host` 后才新鲜）
- **输出**：
  - `clang/lib/Basic/Targets/DADAO.h`：`LongDoubleWidth/Align = 128`、`LongDoubleFormat = IEEEquad`、`HasFloat128 = true` / `Float128Format = IEEEquad`、`SuitableAlign` 评估（现 64；16 B 标量下按需调 128，须给理由）
  - `clang/lib/CodeGen/Targets/DADAO.cpp`：`classifyArgumentType` 的 `f128` = RF 偶-奇对（高半在偶号）、`EmitVAArg` 按 `ADR-0031 D4` 步进、返回 `rf8`+`rf9`
  - `llvm/lib/Target/DADAO/**`：`f128` 合法类型 / libcall lowering（`__addtf3`/`__subtf3`/`__multf3`/`__divtf3`/比较/转换）、2×64 位 load/store、`.td`（若新增载体）与 `DADAOISelLowering.cpp`
  - `series` 计数 + `changelog.md` 一条；lit 向量 `llvm/test/CodeGen/DADAO/`（f128 传参/返回/常量/库调用）
  - 证据：`.work/evidence/<任务号>/run.sh`（default + `--inject`）、`clang -dM -E` 宏断言、`llvm-objdump` 片段、`nm` 符号计数
  - 本任务书完成区
- **约束**：只改 `components/llvm-project/**` + 本任务书（+ 台账按裁决）；**不改** `spec/`、`.tao/contracts/`、`contracts/`、`components/musl/**`（musl 侧 = `INFRA-090t`）；不改 `DataLayout` 串（`f128:128:128` 已默认）；不改已 `Accepted` 的 decision 正文。

## 验收标准

1. **前端宏**：`clang -target dadao-unknown-elf -dM -E -x c /dev/null` 得 `__SIZEOF_LONG_DOUBLE__=16` / `__LDBL_MANT_DIG__=113` / `__LDBL_MAX_EXP__=16384` / `__SIZEOF_FLOAT128__=16`；`sizeof(long double)==16`、`alignof==16` 静态断言编译通过。
2. **ABI 双槽**：`long double` 参数 `rf16`=高半、`rf17`=低半（大端：高半字对应内存低地址，可由 `stm.o`/`ldm.o` 直通验证）；返回 `rf8`=高、`rf9`=低；配对自偶号起、槽位不足整值退栈（不拆半）——逐条给 `-S`/反汇编 + 反例（注入奇号起点或拆半 ⇒ 对应断言 FAIL）。
3. **后端 f128**：`f128` 的加/减/乘/除/比较/转换生成 libcall（或 `f128` legal type 路径），不出现 `Cannot select`/`no libcall available`；`f128` 常量按 `.dd.o64` ×2（高半在前）+ `.p2align 4`。
4. **builtins TF 真正入库（顺序硬约束）**：在 `f128` 接通后重建 compiler-rt，`nm -g --defined-only libclang_rt.builtins.a` 的 `__addtf3`/`__subtf3`/`__multf3`/`__divtf3`/`__extenddftf2`/`__trunctf2` 等 **≥1 且逐条列出**（修前 = 0，留修前输出作对照）；TF 成员数现场统计（不写死）。
5. **端到端 + 独立 oracle**：最小程序用 `long double` 做 2–3 组运算（含 `double → long double → double` 往返、`LDBL_EPSILON` 级差），`qemu-dadao` 退出码 0；期望值**手算/独立派生**（不从 LLVM/QEMU 反推），并给大端半字顺序的双向可判别证据（内存 dump / 反汇编）。
6. **联动 `INFRA-090t`**：musl `bits/float.h` 换 binary128 常量块后，`libc-test` 静态档 `ISS-250` 的 5 例（`math/{acoshl,asinhl,erfcl,lgammal,tgammal}`）转 `pass`；**本册不代改 musl**，若该册未就绪则完成区如实标 `BLOCKED` 并给替代证据（前端/ABI/后端/符号面）。
7. **可达 FAIL**：≥2 处注入（例如：`LongDoubleWidth` 改回 64、`f128` 对序改回低半在偶号、TF 源 `#if` 门控关掉）⇒ 对应断言 `[FAIL]`、脚本 rc=1 ⇒ `cp` + md5 还原 ⇒ 回绿、rc=0（**禁** `git checkout`/`restore`/`stash`）。
8. **门控（各留自身 rc）**：`check-patch-tree`、`check-instrinfo`（若改 `.td`）、`check-component-changelog`、`check-lit_gen`、`make check`(L1)；改 `components/**` ⇒ **单跑** `install-host`（`JOBS=8`、不并发、`ISS-210`；启动前申报预计耗时），完成后核安装根 `clang --version` 新鲜并用安装根复跑第 1–5 条。

## 不做

- **不改** `spec/`、`.tao/contracts/`、`contracts/`（决策已 `Accepted`，正文已落册）。
- **不改** musl（`bits/float.h` = `INFRA-090t`）；不改 `libm`/`_l` 源码（`ADR-0030 D5`：`_l` 自然转正）。
- **不改** `DataLayout` 串、不新增 `.dd.128` 数据指示符（`ADR-0030 D4`）。
- **不做** `f80`/x87、四精度硬件指令、`__int128` 解禁（`contract-abi §6.3` 不变）。
- **不做** 变参 `va_list` 形态改造（`LLVM-102t`）；本册只保证 `f128` 在既有变参路径中按 16 B 值规则可取（若 `LLVM-102t` 未落地，变参面按 `BLOCKED` 如实标注）。

## 硬约束

1. 临时目录 `/tmp/opencode/LLVM-106t/`；workdir = 仓库根、相对路径；禁出界 `cd`；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；留证捕**被检命令自身**退出码（禁 `cmd | tee` 吞码）；复杂输出落 `.work/log/llvm/`。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（新决策 / 需授权）时留问。
6. 用户裁定须把**原话**写入本任务书。
7. 补丁导出纪律：`/tmp` 写入、非空 blob、`check-patch-tree` 断言全绿。
8. **顺序**：前端 → ABI → 后端 → 重建 builtins → 端到端；**不得**先改 builtins 再等 f128（TF 源会继续产出空对象）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
