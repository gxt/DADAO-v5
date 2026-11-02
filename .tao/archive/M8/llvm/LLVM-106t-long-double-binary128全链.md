# LLVM-106t: `long double` = binary128 全链（clang target + ABI 双槽 + 后端 f128 + builtins TF）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`ADR-0030`（`Accepted`：`long double` = binary128 / RF 双槽 / builtins 全量 / 排 `M9`）、`ADR-0031`（`Accepted`：16 B 值高半在偶号、不拆半、16 B 栈对齐）、`ADR-0027`（builtins 全量 + 独立库）、`INFRA-079t`（`已验证`：compiler-rt builtins 接入）、`INFRA-088t`（driver 默认接 builtins；验收前须 `已验证`）、`INFRA-090t`（musl `bits/float.h` 常量块；**联动**）、`ISS-250`（`libc-test` 5 例 `_l` 偏移）
**状态**：已验证

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
**测试结果**：通过 38/38（`bash .work/evidence/LLVM-106t/run.sh` rc=0；`--inject` 3 注入全红→`cp`+md5 还原→回绿，rc=0）。① `clang -dM`：`__SIZEOF_LONG_DOUBLE__=16`、`__LDBL_MANT_DIG__=113`、`__LDBL_MAX_EXP__=16384`、`__LDBL_MIN_EXP__=(-16381)`、`__SIZEOF_FLOAT128__=16`；`sizeof/alignof(long double)==16`、`sizeof(__float128)==16` 静态断言编译 rc=0。② 实际发出 TF libcall **21 条**（`nm -u` 于 ops 探针现场统计）：`__addtf3 __subtf3 __multf3 __divtf3 __extendsftf2 __extenddftf2 __trunctfsf2 __trunctfdf2 __floatsitf __floatditf __floatunsitf __floatunditf __fixtfdi __fixunstfdi __eqtf2 __netf2 __getf2 __lttf2 __letf2 __gttf2 __unordtf2`，**21/21 在 archive 有定义**；FNEG 走整数 XOR（不发 `__negtf2`）。③ builtins TF 符号 **0 → 29**（`nm -g --defined-only` 现场统计；24 个 `*tf*` 成员由空对象变为有定义；修前安装根 archive 对照 = 0）。④ 端到端（构建树 clang + crt0 + 本 archive + QEMU `dadao-m1`）18 项独立 oracle 检查全过，`-O0/-O1/-O2/-Os/-O3` 退出码均 0；含大端半字双向判别（`rf16`=高半落低地址、`st.o` 偏移 0/8、返回 `rf8/9`、`A-2^-100` 保低位、`double` 占 `rf16` 时跳过 `rf17`、9 个 `long double` 第 9 个整值退栈、`va_arg` 三对求和）。⑤ ABI 结构：`st`=`rf2rd rf17→[p,8]`/`rf16→[p,0]`；`ld`=`[p,0]→rf8`/`[p,8]→rf9`；`add(fp128,fp128)` 直通 `call [rb0,__addtf3]`（参数已在 rf16..19、结果 rf8/9）。⑥ lit：新增 `f128-codegen.ll`，CodeGen 目录 **34/34 PASS**（构建树 tools）。⑦ 无回归：33 个既有 lit 全绿；`make check`(L1) rc=0。
**修改文件**：`components/llvm-project/patches/{clang/lib/Basic/Targets/DADAO.{h,cpp},clang/lib/CodeGen/Targets/DADAO.cpp,llvm/lib/Target/DADAO/{DADAOCallingConv.td,DADAOISelLowering.cpp,DADAOSubtarget.cpp}}.patch`（6 份改，`series` 仍 81）；`components/llvm-project/changelog.md`（+1 条）；`tests/llvm/lit/CodeGen/DADAO/f128-codegen.ll`（新增）；`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（**生成物**刷新：补丁行号 594/596/598→714/716/718，`gen_isa_coverage` 再生成）；`.work/evidence/LLVM-106t/{run.sh,gen_f128_vectors.py,f128_e2e.c}`（非跟踪证据）；本任务书。
**验收结果**：门控 rc 全 0：`check-patch-tree`（180 patches OK）、`check-index-blobs`、`check-source-state`（E1：clean + base+1）、`check-no-residue`、`check-instrinfo`、`check-component-changelog`、`check-lit_gen`（64/64）、`check-knowledge-refs`（0 悬空）、`check_tasks`（报告型）、`check_issues.py`（`make check-issues` **无此目标**，直跑脚本 67 open/27 closed rc=0）、`make check`(L1) rc=0。源树：`.work/source/llvm-project` HEAD=`2364895f2`（base+1，`commit --amend`），`git status` 干净。
**新发现/坑**：① **va_arg 16 B 奇偶判据不能看保存区地址 bit3**：保存区只保证 8 B 对齐（`contract-abi §2.2` SP 8 B），SP≡8(mod16) 时地址判据误判奇号并跳槽（现场：变参求和取到低半）；改用「剩余槽数」`left&1`（槽号 = 32-left），对任意 SP 对齐成立，同时修正 LLVM-102t 的 16 B 聚合同类隐患。② f128 无 128 位寄存器 ⇒ 合法化路径 = `TypeSoftenFloat`（f128→i128→2×i64）+ libcall；CC 层用「marker VT=f128」识别两半，`OrigTy->isFP128Ty()` 是唯一可用判别（`CCCustomFn` 拿不到 OrigTy 之外的标记；`f128` 不可作单寄存器）。③ `_Float128` **不是** clang 23 关键字（只有 `__float128`）；`HasFloat128` + `__SIZEOF_FLOAT128__` 即满足 compiler-rt `CRT_HAS_*` 门控。④ 局部 f128 常量按两条 64 位立即数物化（本后端无常量池）；全局 `long double` 常量才是 `.p2align 4` + `.dd.o64`×2（高半在前）。⑤ `__fixtfsi`/`__fixunstfsi` 在 clang 侧不可达（i32 结果先提升为 i64 ⇒ `__fixtfdi`/`__fixunstfdi`），archive 仍备有。⑥ 改 `int_types.h` 关 `CRT_HAS_TF_MODE` 会连带 multc3/divtc3 编译失败（archive 不重链接，假绿），注入须改 `addtf3.c` 的 `#if` 门控。
**遗留问题**：① `INFRA-090t`（musl `bits/float.h`）**BLOCKED**（另册，未做）；其 `_l` 转正与 `ISS-250` 5 例复验须待该册 + `install-host`。② **绝对 16 B 栈对齐**：`ADR-0031 D7` 要求 16 B 槽，但 `contract-abi §2.2` 只保证 SP 8 B 对齐且 `DADAOFrameLowering` `StackAlignment=8`；当前实现栈槽**相对 SP** 16 B 对齐、访问全部为 8 B `ld.o`/`st.o`（无 16 B 指令），功能无碍，绝对对齐须 ABI/框架层另议（未在本册擅改）。③ `install-host`/L2/L3 未跑（主会话执行）；安装根 clang/archive 仍为旧（TF 0 符号），验收第 1–5 条须安装后复跑。

### 安装根复验（2026-10-19，`verify-102t-106t`）

**环境**：安装根 clang md5 `738387826812e316314920f2e7de6129` = 构建树；安装根 `libclang_rt.builtins.a` TF 定义符号**现场 29**（`nm -g --defined-only`，与完成区一致）；`qemu-system-dadao -M dadao-m1`。
**前端**：`clang -dM` = `__SIZEOF_LONG_DOUBLE__ 16` / `__LDBL_MANT_DIG__ 113` / `__SIZEOF_FLOAT128__ 16` / `__LDBL_MAX_EXP__ 16384`；`sizeof/alignof(long double)==16`、`sizeof(__float128)==16` 静态断言 rc=0。
**后端**：`f128_ops.o` 现场发出 **21** 条 TF libcall（21/21 在安装根 archive 有定义；FNEG 走整数 XOR）；安装根 `llc` 下 `rf16→[p,0]`、`rf17→[p,8]`，`[p,0]→rf8`、`[p,8]→rf9`，`fadd` 直通 `call [rb0, __addtf3]`、返回 `ret rd0,0`（大端双向可判别）。
**端到端（独立 oracle）**：`gen_f128_vectors.py`（`fractions` 精确有理数）+ 18 项检查，`-O2` 与 `-O0` **均 rc=0**；含 `A-2^-100` 低位保持、`double→long double→double`、9 个 `long double` 第 9 个整值退栈。
**栈上 16 B `%16==0`**：`LLVM-112t` 的 `P1`（f128 变参栈槽）、`P2agg`（S16/S12 变参栈组）在 `-O0`/`-O2` **4/4 rc=0**（`p0%16==0`、`p1==p0+16`、`p2==p0+32`、值回读一致）⇒ SP 16 后**无条件成立**，不再依赖钉基址（`LLVM-112t` 已把 `StackAlignment` 提到 16，上文遗留②已解）。
**`047t` 5 例**：`math/{acoshl,asinhl,erfcl,lgammal,tgammal}` **静态 5/5、动态 5/5 pass**（权威基线中已是 pass）。
**门控**：`check_musl_freshness`/`check_patch_tree`（181）/`check_milestones_fresh`/`check_issues` 各 rc=0。
**结论**：与完成区基线逐项一致，**未暴露缺陷**；默认 112/112、`--inject` 11/11 rc=0。
**复验坑**：取 by-value 形参地址得到的是 callee 本地副本（struct 对齐 8），不能判 incoming 栈槽对齐；栈上 16 B 须用 `va_arg` 游标（P1/P2agg）判定。
**验收依据**：安装根复验由**独立会话**（`verify-102t-106t`）完成 ✓ —— 112/112 证据 + 11/11 注入 ✓、与权威基线一致 ✓、无缺陷 ✓

## 审阅记录

#### 第 1 轮 engineer 自审
**范围**：6 个组件源文件（前端 2 + clang ABI 1 + 后端 3）+ 导出补丁 + 证据脚本；逐行审查 + 三类注入实测。判决：**可交付**（按主会话下发要求本册**不改 `**状态**`**，留给主会话/architect 置 `待验收`）；F6/F7/F8 为实现事实/环境限制，已按实披露并给证据，非代码缺陷。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `Type::isFloat128Ty()` 不存在（编译失败） | ✅已修 | `markF128Halves` 改 `isFP128Ty()` | `ninja clang llc` rc=0 |
| F2 `va_arg` 16 B 奇偶用保存区地址 bit3，SP≡8(mod16) 时误跳槽（e2e 求和不符） | ✅已修 | 改用 `left & 1`（槽号=32-left） | e2e `-O0/-O1/-O2/-Os/-O3` rc=0；18 项全过 |
| F3 证据探针缺 int→f128，`__floatsitf/__floatunsitf` 假红 | ✅已修 | 探针补 `(long double)i/u` | 21 条 libcall 全绿 |
| F4 builtins 注入用 `int_types.h` 关宏 ⇒ multc3/divtc3 编译失败、archive 未重链接（假绿） | ✅已修 | 注入改 `addtf3.c` 的 `#if` 门控（与原 bug 同机制） | `--inject` rc=0，`__addtf3` 0→1 |
| F5 `check-isa-coverage` 因补丁行号漂移失败 | ✅已修 | 重新生成 `tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（仅 3 行行号） | `gen_isa_coverage --check` PASS；L1 rc=0 |
| F6 `make check-issues` 无此目标（rc=2） | ⏸按实披露 | 直跑 `tools/infra/check_issues.py` | rc=0（67 open/27 closed） |
| F7 `_Float128` 非 clang 23 关键字 | ⏸不修（前端事实） | 以 `HasFloat128`/`__float128`/`__SIZEOF_FLOAT128__` 实现「开 _Float128」 | `sizeof(__float128)==16` 静态断言 + compiler-rt 29 符号 |
| F8 局部 f128 常量为立即数而非 `.dd.o64`×2 | ❌不修（后端无常量池；全局常量满足该条） | 仅披露 | 全局 `vA`：`.p2align 4` + `.dd.o64`×2 高半在前（asm 现场） |

**独立可达 FAIL（`--inject`，全绿）**：① `LongDoubleWidth=64` ⇒ 宏断言红；② 偶/奇槽交换 ⇒ `st.o` 偏移断言红；③ `addtf3.c` `#if 0` ⇒ `__addtf3` 符号断言红。三例均 `cp` 备份 + md5 对账还原 + 重建回绿，未用 `git checkout/restore/stash`。

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
