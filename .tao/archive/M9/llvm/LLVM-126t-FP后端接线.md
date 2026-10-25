# LLVM-126t: FP 后端接线补齐（`ISS-188` 剩余项：比较/符号/取余/分类/位转/缩放/舍入模式/饱和转换）

**模块**：llvm
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-156t`、`LLVM-124t`（min/max）、`LLVM-125t`（取整）、`SPEC-158t`（`fp 66 / 15 族`，已收）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 为什么单独立一本

- `ISS-188`（FP 完备性缺口）把 **硬件已有** 的能力与 **真 ISA 缺口**混在一起列。
- 本轮已把真缺口补齐：`fma`（`SPEC-157t`…）、`min/max`（`SPEC-159t`…）、取整（`SPEC-161t`…）、`fcls` 位序（`SPEC-156t`）。
- **剩下全部是"硬件有指令、后端没接"**：本册一次性收口，不动 ISA、不改 `spec/`。

### 现场事实（2026-10-21 核，执行前须复核）

- `DADAOISelLowering.cpp` 的 `Expand` 列表中仍包含：`FABS`、`FREM`、`FCOPYSIGN`、`FMINNUM/FMAXNUM/FMINIMUM/FMAXIMUM`（后四者由 `LLVM-124t` 处理）、`FCANONICALIZE`、`FLDEXP`、`FFREXP`、`FGETSIGN`、`FP_TO_SINT_SAT`/`FP_TO_UINT_SAT`、以及数学函数族（走 libm，属预期）。
- 硬件已具备（**均无需新指令**）：
  - `fosgnj`/`fosgnn`（copySign / negate-sign）⇒ `fabs`（`sgnj(x, rf0)`）、`fneg`（`sgnn(x, rf0)`）、`copysign`（`sgnj`）
  - `forem`/`ftrem` = **IEEE remainder**（商取最近、平局取偶）⇒ **与 LLVM `frem`（= libm `fmod`，余数符号随被除数）语义不同**，**本册不接**（见 §E）
  - `foqcmp`/`foscmp` ⇒ 全部 `fcmp` 条件（结果在 rd 里是 FP 格式的 1/0/−1/NaN，需按符号与零判定）
  - `focls`/`ftcls` ⇒ `is.fpclass`（10 位 one-hot；`SPEC-156t` 后位序与 LLVM `FPClassTest` 一致 ⇒ 掩码可直接 `and`）
  - `rd2rf`/`rf2rd` ⇒ `bitcast double↔i64`
  - `fosclb` ⇒ `ldexp`（指数是 FP 寄存器里的整数值，需 `io2fo` 一次）
  - `rf0[33:32]` 读写 ⇒ `llvm.get.rounding`/`set.rounding`
  - `fo2io`/`ft2it` 等 ⇒ `fptosi.sat`/`fptoui.sat`（规范：越界 ⇒ 饱和 + NV）
  - `FCANONICALIZE` ⇒ 恒等（无扩展精度）
- **`bitcast` 现状**：`bitcast double→i64` 缺模式（`ISS-188` 原文列出）；`rd2rf`/`rf2rd` 已实现。

## 目标

1. 上表 8 类（比较/符号/分类/位转/缩放/舍入模式/饱和/恒等）全部**有线可落**：每类 **1–3 条**指令，**零 libcall**；`FREM` 不接（`fmod` 语义），但 **`forem` 经 `__builtin_dadao_remainder` 接硬件**（见 §E）；
2. `fcmp` 全部 12 种条件（quiet/signaling）行为正确；
3. `is_fpclass`/`fpclassify` 直接由 `fcls` + 掩码实现（零重排）；
4. `get/set.rounding` 读写 `rf0[33:32]`；
5. `ISS-188` 可关闭（或收窄为"仅剩 f16/bf16 等已裁定不做项"）。

## 接口规范

- **输入**：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（`DADAOISelLowering.cpp`、`DADAOInstrInfoFP.td`、`DADAOCodeGen.td`）、`tests/llvm/lit/**`。
- **输出**：各节点的 Legal/Custom 设置与 pattern/伪指令；lit 覆盖每类；证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`、不动 ISA 编码；不改门控判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. `fcmp` 取值（最容易出错）

- `foqcmp a,b` 输出 **FP 格式**：`>0 ⇒ 1`、`==0 ⇒ 0`、`<0 ⇒ −1`、`unordered ⇒ qNaN`；
- 实现 `SETOEQ/OGT/OGE/OLT/OLE/ONE/ORD/UNO` 与 `SETUEQ/UGT/...` 全部条件，**用符号/零/NaN 判定**（NaN 的位模式为正数 ⇒ 需 `focls` 或比较自身判别）；
- 必须覆盖：`x != x`（UNO）、`x == x`（ORD）、`±0` 相等、`sNaN` 置 NV（signaling 比较）、`qNaN` 不置 NV（quiet 比较）。

### B. `fabs`/`fneg`/`copysign`

- `fabs(x)` = `fosgnj(x, rf0)`（`rfHD = rf0` 即 abs，`SimRISC-07 §5` 明写）；
- `fneg(x)` = `fosgnn(x, rf0)`；`copysign(x,y)` = `fosgnj(x,y)`；
- 断言：**1 条**指令，且不产生 FP 异常。

### C. `is_fpclass` / `fpclassify`

- `focls rd, {rf}`（标量 `immu6=1`）返回 10 位 one-hot；
- `is_fpclass(x, M)` = `focls` + `and mask` + `!=0`（单类掩码可省 `and`：直接与 one-hot 常量比较）；
- `fpclassify`（C 5 类）= `fcls` + 常量映射（编译期可折叠成 1 次 `and`/比较）；
- **位序依赖 `SPEC-156t`**：若其未落地，本册 BLOCKED。

### D. `bitcast` / `ldexp` / `rounding` / `sat`

- `bitcast double↔i64`：`rf2rd`/`rd2rf`（1 条，无 FP 异常）；
- `ldexp(x, n)`：`io2fo(n)` + `fosclb`（2 条）；`frexp` 不接（保持 libm）；
- `get.rounding`/`set.rounding`/`flt.rounds`：读/写 `rf0[33:32]`（写需只改该字段，用 `set.w` + 掩码）；
- `fptosi.sat`/`fptoui.sat`：`fo2io`/`ft2it` 等（硬件已饱和 + NV）。

### E. `frem` 不接（已核对，**不是缺口**）

- **LLVM `frem` = libm `fmod`**（LangRef：「same output as libm `fmod` … remainder has the same sign as the dividend」；`TargetLowering` 的 `FREM` 展开走 `RTLIB::REM_*` = `fmod`）；
- **我们的 `forem`/`ftrem` = IEEE remainder**（`SimRISC-07 §4.1`：`rfHC − n × rfHD`，n 取最近整数、平局取偶）；
- **数值反例**：`fmod(5,3)=2` vs `remainder(5,3)=−1`；`fmod(−5,3)=−2` vs `remainder(−5,3)=1`；
- LLVM **无** `llvm.remainder` intrinsic（`grep int_remainder` = 0）⇒ `frem` **保持 `Expand`**（落 musl `fmod`），**禁止**接 `forem`；
- **用户 2026-10-22 裁定：「`forem` 接硬件」**。但 `remainder()` 在 LLVM 没有 intrinsic（Clang 直接发 libcall）⇒ 落地方式定为：新增 **`__builtin_dadao_remainder`**（`double`/`float` 两形态）→ 直接选 `forem`/`ftrem`（**1 条、零 libcall**），先例 = `__builtin_dadao_clmul`（`LLVM-122t`）。`FREM` 仍保持 `Expand`（= `fmod`），**两者语义不同，禁止互接**。
- `ISS-188` 中"`frem` 缺 ISel 模式"一条按此改为**"不接（语义不一致）"**，不是补 pattern。

## 验收标准

1. lit：9 类各至少 1 例，断言**指令计数**与**无 libcall**（`FileCheck` + `llvm-nm`/反汇编）。
2. `fcmp` 12 种条件全覆盖（含 `UNO`/`ORD` 与 `±0`）。
3. `is_fpclass`/`fpclassify`：`fcls` 后掩码**零重排**（掩码常量与 `FPClassTest` 一致）。
4. C 层抽查：`fabs/fabsf`、`copysign`、`fmin`、`rint/nearbyint`（已由 `LLVM-125t`）、`isnan/isinf/isfinite/fpclassify`、`ldexp`、`bit cast`（`union`/`memcpy` 不适用时用 `__builtin_bit_cast`）。
5. **`FREM` 不接**（保持 `Expand`，libcall `fmod`）；**`forem`/`ftrem` 经 `__builtin_dadao_remainder` 各 1 条**（C 层实测）；完成区须粘 `git grep` 证据证明 `FREM` 未被映射到 `forem`。
6. `check-instrinfo` 0 errors；`check-lit`/`check-lit-full` 绿。
7. 改 `.td` 后 `make install-host` + `build-builtins` + `build-musl-shared`。
8. `make check`（L1）rc=0；`make check-modules`（L2）rc=0。
9. **可达 FAIL ≥ 2**：① 把 `fabs` 错接成 `fosgnn`（取反）⇒ 值用例红；② `is_fpclass` 掩码不重排（用旧位序）⇒ 分类用例红。
10. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行；`ISS-188` 关闭或收窄（写明剩余项与理由）。

## 做（阶段）

1. 现场复核（各节点当前 action、`rd2rf`/`rf2rd` 的 `.td`、`forem` 与 `frem` 语义差异）。
2. `fabs/fneg/copysign` → `fcmp` → `fpclass` → `bitcast` → `ldexp` → `rounding` → `sat`（每步加 lit）。
3. `frem` 语义核对并定接法。
4. `install-host` + builtins/musl + L1/L2 + 反例注入。
5. 完成区 + `ISS-188` 收口。

## 可达 FAIL（**≥2**）

- `fabs` 误接 `fosgnn` ⇒ 值红；还原 ⇒ 绿。
- `is_fpclass` 用旧位序掩码 ⇒ 分类红；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不接 `frexp`、数学函数族（libm）；不做 f16/bf16（已裁定）。
- 不做 constrained FP（`llvm.experimental.constrained.*`）。
- `frem` 保持 libm（`fmod`）；`forem` 不接（语义不同，已核）。若要让 `remainder()` 用上硬件，另立 `INFRA` 册改 musl。

## 完成区

**测试结果**：证据 `run.sh` default **34/34 PASS**、`--inject` **20/20 PASS**（3 类注入均「红→还原→绿」）。`check-lit` 145/145、`check-lit-full` 12/12、CodeGen/DADAO 58 例；L1 rc=0、L2 rc=0。C 层 spot probe（musl 静态 + `qemu-dadao`）guest rc=0。
**修改文件**：补丁 8 份（7 改 1 新）：`llvm/lib/Target/DADAO/{DADAOISelLowering.cpp,.h,DADAOCodeGen.td,DADAOISelDAGToDAG.cpp}`、`llvm/include/llvm/IR/IntrinsicsDADAO.td`、`clang/include/clang/Basic/BuiltinsDADAO.def`、`clang/lib/CodeGen/Targets/DADAO.cpp`、`clang/lib/Sema/SemaChecking.cpp`（新）；`components/llvm-project/{series,changelog.md}`；`tools/llvm/llvm-isa-backend-matrix.{tsv,md}`；lit 新增 7（`fp-{fcmp,classify,ldexp,rounding-mode,sat,canonicalize,remainder}.ll`）+ 改 2（`p1-fp-sign.ll` 扩 f32、`tests/llvm/ir-lli/manifest.yaml` 登记）+ 删 0；`.tao/knowledge/{milestones.md,issues.yaml}`；本任务书；`.work/evidence/LLVM-126t/{run.sh,cspot.c}`。
**验收结果**（真实输出）：`check-instrinfo` 0 errors；`check-scope` PASS；`check_qemu_trans --strict` **266/266**；`check-isa-coverage` yes **177→189**（12 条 FP 指令转「用得上」）。`llc -O2`：fabs f64/f32=2（rd2rf+sgnj）、copysign f32=1、fneg f32=1；is.fpclass=1 `focls`+掩码（单类 0 条 `and`）；ldexp=3（ext.so+io2fo+fosclb）/i64 指数=2；get.rounding=4、set.rounding 常量=1 `set.w rf0, wp2, hw`、动态=读改写；sat i64=1 `fo2io`+NaN 修正、i32=`fo2it`、f32=`ft2io`；canonicalize 恒等；`llvm.dadao.remainder.{f64,f32}`=`forem`/`ftrem` 各 1。C 层各函数预期指令 + `call` 0；运行期 `remainder(5,3)=-1`、`remainder(-5,3)=1`、`fmod(5,3)=2`、`(long long)1e300`→INT64_MAX 且 `rf0[0]=1`、`get.rounding` 读 rf0[33:32]。**FREM 未接证据**：`git grep -nE '\(frem[^)]*\)\.*\((fo|ft)rem'` = 0；`frem` 的 asm 无 `forem`/`ftrem`；注入 FREM→forem 后值差分 host=2/dadao=-1 红。
**新发现/坑**：① 本 LLVM 的 `ISD::FREM` Expand 是**内联 fmod 算法**（无 libcall），非册子写的「落 musl fmod」；语义仍=fmod，禁止接 `forem`。② `is.fpclass` 的 i1 结果被类型合法化提升到 **i8**（非 i64），lowering 需按 SETCC 结果类型构造再 TRUNCATE。③ 写 `rf0` 无法用 DAG pattern 绑目的（同 `rd0` 先例）⇒ 隐式 rf0 def 伪指令 + 自定义展开；`set.w` wp2 由 FCSR 写掩码只改 `[33:32]`、不动 `[4:0]`。④ 注入还原必须 `touch`：`cp -p` 旧 mtime 会让 ninja/make 判「无需重建」⇒ 假绿。⑤ QEMU 侧 NV 注入需重建 build 树 `qemu-dadao` 并 `install-host` 回装，否则 install root 漂移。
**遗留问题**：① `fptosi.sat`/`fptoui.sat` 的 **i8/i16** 结果无硬件饱和宽度 ⇒ 保留通用展开（正确、无 libcall；未走硬件 1 条）② 动态 `set.rounding` 对 FLT=4..7 仅取低 2 位（硬件无 nearest-away），常量 4 显式 `emitError`；C 层无 `llvm.set.rounding` 入口（本目标无 `__builtin_set_flt_rounds`），仅 IR 可达 ③ `f16`/`bf16`、constrained FP 按裁定不做。

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

### 第 1 轮 reviewer 验收（2026-10-24，结论：**Accepted**）

**重跑记录（全部本人执行，输出/退出码为本人终端真值）**
- 门控：`check-instrinfo` → `Result: 0 errors`；`check-scope` → PASS；`check-lit` 145/145；`check-lit-full` 12/12；`check_qemu_trans --strict` 266/266；`make check`(L1) rc=0（含 `check-isa-coverage` **yes 189**，与完成区 177→189 一致）；`make check-modules`(L2) rc=0。证据脚本 `run.sh` 重跑 **34/34 PASS rc=0**；`run.sh --inject` **20/20 PASS**（A 掩码删除→guest rc≠0；B frem→forem→值差分 rc≠0 且 `llc` 出 `forem`；C QEMU 丢 NV→rc≠0；三处还原 md5 = 我开工快照）。
- `fcmp`：本人自写 IR（期望值由 CPython IEEE-754 独立算出；host `lli` rc=0 证明该 oracle ≡ LLVM 语义），16 谓词 × 64 对（含 qNaN/±0/±Inf）`qemu-dadao` **rc=0**。指令数：每谓词 `foqcmp`×1；`one/ord/uno/ueq` 另 +`cmp.si`；`true/false` 常量折叠 0 条（正确）。
- 9 类（本人 `llc`/`clang -O2` 实测）：`is.fpclass` 单类=`focls`+`cmp.ui`、多类(504)=`focls`+`and.o`(掩码常量 0x1f8=FPClassTest，零重排)；运行期 10 类 ×(one-hot+8 多类掩码)=90 项 **rc=0**；`bitcast` d2i/i2d 各 1 `rf2rd`/`rd2rf` + 往返 rc=0；`ldexp`= `io2fo`+`fosclb`（i64 指数 2 条、i32 3 条）+ 2^1000/2^1024/2^-1074/2^-1075 实跑正确；`get.rounding`= rf2rd+shr+and+xor（4 逻辑 +3 `set.zw`）；`set.rounding` 常量=1 `set.w rf0, wp2, 0x2`（FLT 3=RDN→hw 2 ✓）、动态=读改写（`set.ow …0xfffc` = ~(3<<32) 掩码）且 **4 种模式 tie 用例实跑舍入方向真变**、accrued flags 存活；`sat`= `fo2io/fo2uo/fo2it/fo2ut`(+NaN→0)，i8 通用展开 0 libcall；`canonicalize`= 1 条 `rf2rd` 恒等（sNaN/−0.0 位级不变）。
- 饱和/NV（独立构造值，核 `rf0[4:0]`）：+1e300→INT64_MAX+NV；−1e300→INT64_MIN+NV；NaN→0+NV；fptoui(−1)→0+NV；fptoui(1e300)→UINT64_MAX+NV；范围内 42 **无 NV**；C 强转同路径。
- `forem` builtin 实跑：remainder(5,3)=−1、(−5,3)=1、(5.5,2)=−0.5、remainderf=−0.5；`fmod(5,3)=2`，C 层 `fmod` 出 `jump [rb0, fmod]`、`forem/ftrem`=0；`git grep '\(frem…(fo|ft)rem'`（patches）=0。
- 注入（本人独立一次，非采信脚本）：把 `ISD::FREM` 移出 Expand + 加 `(frem f64)→forem` → 我自己的 `frem` 值探针 **rc=1**（fmod(5,3) 变 −1）、`@fr` asm 出 1 条 `forem`；`cp -p`+`touch` 还原 → md5 与快照一致、探针回 **rc=0**；`git status` 全程 0 行、三文件 md5 复原。
- 覆盖披露：`git diff 3bc17530~1..3bc17530 -- tests/` = 新增 7、改 2、删 0；`p1-fp-sign.ll` 仅收紧（`CHECK`→`CHECK-COUNT-1` + f32/fneg 例），`manifest.yaml` 只为新文件加 exclude 条目，未放宽既有断言。

**非阻断观察（供 architect 定夺）** ① `fabs` f64/f32 = 2 条（`rd2rf`+`sgnj`），而 SimRISC-07 §3/contract-fp.md §7 明写 `sgnj(rfHC, rf0)=abs`，1 条形态在 ISA 上成立；目标 1（每类 1–3 条）满足但设计要点 B 的「1 条」未达成（我用手写 asm 验证该形态未得结论，未见其坏的证据）。② `run.sh` 的 `frem_proof()` 对 `.work/source/**` 的 `git grep` 恒为 0（该树未被 git 跟踪），该半边是死断言；活证据来自值差分与 `llc` asm。③ QEMU `fosclb` 溢出/下溢不置 OF/UF（contract-fp.md §5 要求按 IEEE754），属 QEMU/SPEC 范围，建议另登记。

### 第 1 轮 engineer 自审（2026-10-24，自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| GET_ROUNDING 的 `rf2rd` 由 chain 节点选出但指令本身纯：理论上可被调度到前一条 `set.rounding` 之前 | ⏸延后 | 不改（strict FP 不在本册；非 strict 下 LLVM 假定默认舍入，set/get 仅提示语义）；代码注释已写明 | `roundtrip` lit（set→get）实测顺序正确、结果 2 |
| `is.fpclass` 多类掩码路径多一条 `cmp.ui`（可直连 `CS_Z` 省 1 条） | ❌不修 | 保留统一 `SETCC` 路径（与整型比较一致、可读性优先）；lit `CHECK-COUNT` 钉住实际条数 | `fp-classify.ll` PASS |
| 动态 `set.rounding` 对 FLT=4..7 静默取低 2 位；常量 4 已显式报错 | ⏸延后 | 动态档加掩码 `&3`（硬件无 nearest-away）；C 层不可达，披露在完成区 | `set_dynamic` lit PASS；常量 4 实测 `llc` rc=1 + 明确诊断 |
| 注入 A 若用常量实参会被 -O2 常量折叠，掩盖分类错误 | ✅已修 | `cspot.c` 全部输入改 `volatile`（含 fabs/copysign/classify/ldexp/bitcast） | 注入 A 实测 guest rc=6（isinf(1.0) 误真）→ 还原 rc=0 |
| 注入还原用 `cp -p` 保留旧 mtime ⇒ 构建判「无工作」⇒ 假绿 | ✅已修 | `restore()` 增加 `touch`；C 档还原后追加 `install-host` 回装 | `--inject` 20/20（A/B 重建生效、C 回装后 rc=0） |
| `fptosi.sat` i8/i16 无硬件宽度，Custom 返回空 ⇒ 回退通用展开，是否符合「不支持显式失败」 | ✅已修（改为显式 Expand 动作） | 构造函数对 i8/i16 显式 `Expand`（不再依赖 Custom→空） | `fp-sat.ll` 的 i8 例 PASS、无 `call` |
| Sema 侧新 builtin 只允许同型两参（float+double 混用报错） | ❌不修 | 明确诊断优于静默提升；任务要求 double/float 两形态 | `__builtin_dadao_remainder(x, 2.0f)` 编译报 `err_builtin_invalid_arg_type` |
