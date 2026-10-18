# LLVM-105t: clang 崩溃 2 例（lencod/obsequi）与 `wchar_t` 符号性（`ISS-253`）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`ISS-267 ①`（clang 崩溃 2 例，`open`；源 = `TESTCASES-048t` 第 2 步全量两档）、`ISS-253`（`wchar_t` 符号性冲突，`open`；源 = `TESTCASES-047t` 静态档）、`ISS-266`/`QEMU-063t`（宿主信号，**不同面**，不属本册）、`TESTCASES-048t`/`TESTCASES-047t`（现场与复跑载体）；用户 2026-10-18 裁定 **M8**（逐字「1、可以；2、M8内修」，渠道 = 经主会话问答）。
**状态**：待验收

> **编号说明**：本册编号由主会话 2026-10-18 指定（`LLVM-105t`/`107t` 同批立册）。本册把**两个独立缺口**放在一册，因为二者都需「先诊断、后定性」且共用一次 `install-host` 窗口；**诊断与处置须分节各自留证**，不得互相顶替。

## 执行环境
**执行环境**：本地

## 问题根源

### A. clang 崩溃 2 例（`ISS-267 ①`）

两档（静态/动态）**一致**：driver 记 `compile error rc=-6`，`first_error` 逐字 = `clang: error: clang frontend command failed due to signal (use -v to see invocation)`。

现场单 TU 命令（`TESTCASES-048t` JSON 的 `compile_cmd`，逐字；`<ROOT>` = 仓库根，执行时用相对路径）：

- `lencod`：`.dadao/cross-toolchain/bin/clang -target dadao-unknown-elf -nostdinc -I .work/source/musl/arch/dadao -I .work/source/musl/arch/generic -I .work/source/musl/obj/include -I .work/source/musl/include -O2 -DNDEBUG -w -DSMALL_PROBLEM_SIZE -fcommon -D__USE_LARGEFILE64 -D_FILE_OFFSET_BITS=64 -c .work/source/llvm-test-suite/MultiSource/Applications/JM/lencod/explicit_gop.c -o /tmp/opencode/LLVM-105t/explicit_gop.o`
- `obsequi`：`.dadao/cross-toolchain/bin/clang -target dadao-unknown-elf -nostdinc -I .work/source/musl/arch/dadao -I .work/source/musl/arch/generic -I .work/source/musl/obj/include -I .work/source/musl/include -O2 -DNDEBUG -w -DSMALL_PROBLEM_SIZE -Wno-implicit-int -DCOUNTBITS16 -DLASTBIT16 -DCOUNTMOVES_TABLE -DTWO_STAGE_GENERATION -DHASHCODEBITS=15 -c .work/source/llvm-test-suite/MultiSource/Applications/obsequi/negamax.c -o /tmp/opencode/LLVM-105t/negamax.o`

现场**未**保留崩溃栈（driver 只记 `rc=-6`）⇒ 本册第一件事是**补齐崩溃现场**。**不预设**「上游 bug」或「我方后端崩」中的任一方。

### B. `ISS-253`：`wchar_t` 符号性冲突

- 现场（`TESTCASES-047t` 静态档）：`functional/mbsrtowcs-overflow` 以**编译期类型冲突**记 `blocked`。
- 根因（两侧定义，现场）：
  - musl 端口：`.work/source/musl/arch/dadao/bits/alltypes.h.in:29` = `TYPEDEF int wchar_t;`（**有符号**）。
  - clang 目标：`components/llvm-project/patches/clang/lib/Basic/Targets/DADAO.h.patch:55` = `WCharType = UnsignedInt;`（**无符号**）⇒ `__WCHAR_TYPE__ = unsigned int`。
- `spec/` 与 `.tao/contracts/` **均无 `wchar_t` 明文**（现场 grep 0 命中）。**判据** = `spec`/契约优先；**spec 无明文时以被移植的 libc（musl 端口）为唯一真源**（本 target 的 C 库就是 musl；`wchar_t` 是 ABI/类型口径，不能两处各说一套）。**若**诊断发现 spec/契约另有明文且与 musl 相反 ⇒ **停下留问**（不擅改 musl，也不擅改契约）。

## 诊断要求（先诊断，后处置）

### A 段（clang 崩溃）

1. **复现并保留现场**：上述两条命令逐条跑，捕**被检命令自身** rc（预期非 0，形如 `134`/`-6`）；stdout+stderr 全量落 `.work/log/llvm/LLVM-105t-*.log`，**禁** `| tail`/`| head` 截断。用 `-fcrash-diagnostics-dir=/tmp/opencode/LLVM-105t/crash-<case>` 让 clang 产出 preprocessed 源 + 复现脚本。
2. **定位阶段**（逐级缩小）：`-fsyntax-only` → `-emit-llvm -S` → `-S` → `-c`。落点结论写成「崩溃发生在：前端 Sema / clang CodeGen / 后端 DAG·ISel / 汇编·发射」。
3. **栈与最小化**：
   - 用崩溃诊断目录里的复现脚本重跑，取栈（`llvm-symbolizer`；或 `gdb --batch -ex run -ex bt`），**栈顶帧的源码路径**是定性关键。若现场/构建树存在 sanitizer 版 clang（ASan/UBSan 构建），优先用其复现以取确定性栈；**不存在则不自行重建/安装**，如实登记后用上述符号化手段。
   - 最小化到「几行 C」：优先 `.work/build/llvm/bin/llvm-reduce`（若不存在 ⇒ 如实登记，**不自行安装**；改用 `clang -E` 预处理 + 手工 delta 缩减）。最小复现 + 命令写入完成区。
4. **判定（二分，须给证据）**：
   - **上游 clang bug**：最小复现去掉 DADAO 专有依赖后，用通用 target（如 `-target x86_64-unknown-linux-gnu`）同法编译**同样崩溃**；或栈顶落在与 DADAO 无关的通用前端代码且可用上游行为解释。
     ⇒ 处置 = **`excluded` + 依据**：在 `tools/testcases/run_llvm_ts_user.py` 按既有 `excluded` 机制收编这 2 例（逐例 `reason` 含「upstream clang crash」+ 崩溃签名 + 依据指针），**不改语料、不造桩、不在我方补丁里绕过上游 bug**；同步在完成区写清「为何不是 DADAO 缺陷」。
   - **我方后端/目标侧崩溃**：仅 DADAO target 复现，或栈顶落在 `llvm/lib/Target/DADAO/**` / `clang/lib/CodeGen/Targets/DADAO.cpp` / DADAO ABI 补丁。
     ⇒ 处置 = **修**：改 `components/llvm-project/patches/**`（一文件一补丁）+ 加**最小 lit 回归**（崩溃复现器，放现有 DADAO lit 目录；须能在修复前红、修复后绿）+ `install-host` 后复跑 2 例。
   - **无法归类**（既非通用 target 复现，也非 DADAO 栈）：**保留 `blocked`、留问**（需用户语义裁定）；**不得**为凑结论静默 `excluded`。
5. **跨模块披露**：A 段若改 `tools/testcases/**`（`excluded` 收编），属 `testcases` 模块面 ⇒ 完成区显式披露「跨模块改动 + 原因」，并与 `TESTCASES-048t` 的计数复跑同批。

### B 段（`ISS-253`）

1. **最小复现**：一个 TU 同时 `#include` musl 的 `wchar.h`/`stddef` 相关头并声明/使用 `wchar_t`，证明「clang 内建 `wchar_t`（无符号）与 musl `typedef int wchar_t` 冲突」；另用 `clang -dM -E -x c /dev/null | grep WCHAR` 记录 `__WCHAR_TYPE__`/`__WCHAR_WIDTH__` 现场。
2. **判据落纸**：`spec/`/契约无明文 ⇒ 以 musl 端口 `arch/dadao/bits/alltypes.h.in:29` 为真源；给出「为何改 clang 而不是改 musl」的依据（musl 是消费方、其 `wchar_t` 参与全部宽字符原型；改 musl 会扩散到上游源，且与宿主/主流 64 位 ABI 的 `wchar_t` 有符号口径相悖）。
3. **候选修法（诊断后定，不预设）**：clang DADAO target `WCharType = SignedInt`（并核 `__WCHAR_TYPE__`、`__WCHAR_WIDTH__`、`WCHAR_MIN/MAX` 自动跟随）；若同时发现 `WIntType`/`char16_t`/`char32_t` 有同类偏差，**逐项列证据**、只改有证据者。
4. **若判据指向改 musl** ⇒ **停下留问**（改 musl 属端口口径变更，需用户裁定）；本册不擅自动 musl。

## 接口规范

- **输入**：
  - `.dadao/cross-toolchain/`（安装根；改 `components/**` 后须 `install-host` 才新鲜）
  - `.work/build/llvm/bin/`（23.1.3 构建树；`llvm-reduce`/`llvm-symbolizer` 如存在）
  - `.work/source/llvm-project/`（**只读**检出）、`components/llvm-project/patches/**`（唯一可改载体）
  - 语料：`.work/source/llvm-test-suite/.../{explicit_gop.c,negamax.c}`、`.work/source/libc-test/`（**均只读**）
- **输出**：
  - A 段：崩溃现场日志 + 最小复现 + 定性证据；若修 ⇒ 补丁 + lit 回归 + 复跑；若上游 ⇒ `tools/testcases/run_llvm_ts_user.py` 的 `excluded` 收编 + 依据
  - B 段：`WCharType` 补丁（若判 clang 侧）+ `mbsrtowcs-overflow` 复跑证据
  - `.work/evidence/<任务号>/run.sh`（执行时创建；非交互、任一失败非零、含可达 FAIL；长日志 `.work/log/llvm/`）
  - 本任务书完成区（与真实输出逐条对齐）
- **约束**：只改 `components/llvm-project/**`、必要时 `tools/testcases/run_llvm_ts_user.py`（A 段 `excluded`）+ 本任务书 + `milestones.md`（如需）；**不动** `spec/` / `.tao/contracts/` / `contracts/` / musl 源 / 语料源。

## 验收标准

1. **诊断先行**：A 段两例各自的「复现命令 + rc + 阶段定位 + 栈顶帧 + 最小复现 + 定性（上游/我方/未定）」逐条入完成区；B 段有「冲突最小复现 + `__WCHAR_TYPE__` 现场 + 判据」；**未完成诊断不得进入修/排除**。
2. **A 段处置与定性一致**：上游 ⇒ 2 例 `excluded` 且逐例 `reason` 可复核（含崩溃签名与依据）；我方 ⇒ 修复 + lit 回归（修复前红） + 两例复跑结果（`pass` 或如实的新分类，**不得**宣称 pass 若仍 blocked）。**未定 ⇒ 留问**，保留 `blocked`。
3. **B 段**：`mbsrtowcs-overflow` 由 `blocked` 转为 `pass`（或给出「判据指向改 musl」的留问）；`__WCHAR_TYPE__` 与 musl `typedef` 一致；`__WCHAR_WIDTH__`/`WCHAR_MIN/MAX` 自洽。
4. **可达 FAIL**：≥2 处注入（形状自选，须与判据绑定；例如：把 `excluded` 依据表临时改错 ⇒ 驱动审计 FAIL；把 `WCharType` 临时改回 `UnsignedInt` ⇒ B 段最小复现 FAIL）⇒ 脚本 rc=1 ⇒ `cp` + md5 还原 ⇒ 回绿、rc=0。
5. **`install-host` 前置**：改 `components/llvm-project/**` ⇒ **单跑** `install-host`（`JOBS=8`、不并发、`ISS-210`；**启动前申报预计耗时**）；完成后核安装根 `clang --version` 新鲜并复跑 A/B。
6. **门控**：`check-patch-tree`（现 **180**，改后现场计数）、`check-instrinfo`（若改 `.td`）、`check-component-changelog`、`make check`(L1) rc=0、`make check-modules`(L2) rc=0；`check-lit` 全绿。
7. **复跑与无回归**：A 段若改驱动 `excluded` 或后端 ⇒ 复跑 `TESTCASES-048t` **两档全量**（或主会话指派批次），逐例类别 diff 仅允许目标 2 例变化；B 段 ⇒ 复跑 `TESTCASES-047t` **静态 + 动态全量**（或指定批次），逐例 diff 仅允许 `mbsrtowcs-overflow` 变化；计数现场派生、不写死。
8. **完成区 ≤30 行**，与真实输出逐条对齐；长输出留 `.work/log/llvm/`。

## 不做

- **不**把「clang 崩」直接归 `blocked` 了事（必须先诊断）；**不**在上游 bug 上做本地绕过（可 `excluded` + 依据）。
- **不**改语料 / 期望值 / `known-fail` 标签；**不**为通过而放宽判据。
- **不**动 qemu 宿主信号 4 例（`ISS-266` → `QEMU-063t`）、`brind`/varargs（`LLVM-102t`）、`flog`（`LLVM-103t`）、`RUNTIME_INIT`（AArch64 专有）、`re_comp`（上游不构建）。
- **不**动 `ISS-243`（i32 窄返回，归 `LLVM-107t`）。
- **不**改 `spec/` / `.tao/contracts/` / `contracts/` / musl 源。

## 硬约束

1. 临时目录 `/tmp/opencode/LLVM-105t/`；命令在 workdir 内、**相对路径**；**禁**出界 `cd`；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；**禁** `git add -A`/`.`；**禁** `git checkout`/`restore`/`stash` 还原（一律 `cp` + md5）。
3. 完成区与真实输出逐条对齐，留证捕**被检命令自身**退出码（禁 `cmd | tee` 吞码）。
4. 只动任务书范围，越界须披露（尤其 A 段动 `tools/testcases/**`）。
5. 失败保留现场并继续推进（自行处置：查证 / 绕行 / 有据重试并记录次数 / 登记后跳过）；**只在需用户语义裁定**时留问。
6. 用户裁定须把**原话**写入本任务书。
7. `check-patch-tree` / `check-index-blobs` / `check-source-state` 须绿（改 `components/**` 的补丁集完整性）。
8. 崩溃诊断产物（preprocessed 源/复现脚本）体积大 ⇒ 落 `/tmp/opencode/LLVM-105t/`，**不入库**；最小复现器（几行 C）入库到 lit 目录（若修）。

## 完成区

**测试结果**：A 段（rc 实测）：两例 `-fsyntax-only`/`-emit-llvm -S` 均 rc=0，`-S`/`-c` 均 rc=134（`Aborted`）；栈顶 `TargetLoweringBase::getSetCCResultType`（assert `No default SetCC type for vectors!`）← `DAGTypeLegalizer::WidenVecRes_LOAD`（`LegalizeVectorTypes.cpp:6851`），DAG 节点 `v6i32 load %arrayidx126`（lencod `create_hierarchy`）/`v3i32 load %arrayidx828`（obsequi `search_for_move`）。三方对照：同份最小 C 用 `x86_64-unknown-linux-gnu` rc=0（同一 clang）；riscv64 未注册（本构建仅 dadao/x86），如实登记。最小复现 = 8 行 C（24 B 聚合 swap，SROA 出 `load <6 x i32>`）：dadao rc=134 / x86 rc=0（日志 `.work/log/llvm/LLVM-105t-*`）。**定性 = 我方**（DADAO 未覆盖 `getSetCCResultType`）⇒ **修**：向量→`changeVectorElementTypeToInteger()`、标量→`getPointerTy`。修后两例 `-O2 -c` rc=0、corpus `blocked=0`、v6/v3 语义探针 qemu rc=0。B：修前 `__WCHAR_TYPE__=unsigned int`/`__WCHAR_MAX__=4294967295U`，修后 `int`/`2147483647`、`__WCHAR_MIN__=(-__WCHAR_MAX__-1)`；probe（sizeof/符号/WEOF/`_Generic`）编译 rc=0、qemu rc=0；`regression/mbsrtowcs-overflow` static/dynamic 均 pass（t_status=0）。**无回归**：lit **103/103**（新增 `vec-load-widen.ll`：安装根旧 llc FAIL、构建树 PASS）、12 例 **12/12**。
**修改文件**：`components/llvm-project/patches/{clang/lib/Basic/Targets/DADAO.h,llvm/lib/Target/DADAO/DADAOISelLowering.h,llvm/lib/Target/DADAO/DADAOISelLowering.cpp}.patch`；`components/llvm-project/changelog.md`；`tests/llvm/lit/CodeGen/DADAO/vec-load-widen.ll`（新增）；`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（patch 行号 +11 重派生）；`.work/evidence/LLVM-105t/{run.sh,probe_wchar.c,probe_vec_v6_sem.c,probe_vec_v3_sem.c,repro_vec_load.c,run.log,inject.log}`；本任务书。组件源 `.work/source/llvm-project`：`commit --amend` 收敛为单 commit（E1 保持，HEAD `cbade8ffb`）。
**验收结果**：`check-patch-tree` **180 patches OK**（series 81 不变）；`--source-state`/`check-index-blobs`/`check-instrinfo`/`check_lit_gen`(64)/`check-component-changelog`/`check-no-residue`/`check-isa-coverage`/`check-issues`/`check-knowledge-refs` 全 rc=0；`make check`(L1) rc=0。证据 `.work/evidence/LLVM-105t/run.sh` default **46 checks rc=0**、`--inject` **61 checks rc=0**（I1 后端源码注入→llc rc=134→`cp`+md5 还原重编→rc=0；I2 musl 头改 `unsigned wchar_t`→probe rc=1→回绿；I3 oracle 翻转→rc=1→回绿；原文件 md5 前后一致）。
**新发现/坑**：① `obsequi` 运行 oracle 差异根因 = `srandom(1)` 后 musl `random()` 序列 ≠ glibc（首值 262836907 vs 1804289383；`init.c:66` 用它种 Zobrist 表）⇒ 节点/cutoff 统计不同而 `Winner found: 5000` 一致，-O1/-O2 相同 ⇒ 非 DADAO 缺陷；② `lencod` 运行 FAIL = 驱动 run 目录无 `Output/`（`encoder_small.cfg:18` `ReconFile=Output/test_rec.yuv`），补建后产物与 oracle 逐行一致 ⇒ testcases 驱动缺口；③ 构建树 compiler-rt archive 旧（无 `__eqtf2`），证据改用安装根 builtins + 构建树 clang（wrapper）；④ patch 内行号 +11 会触发 `check-isa-coverage` 漂移，须 `gen_isa_coverage.py` 重派生（已做）。
**遗留问题**：① 按派单未跑 `install-host`/`build-musl`/L2/L3；安装根 clang/llc 仍为旧（证据用构建树 + 安装根 builtins），两例与 B 的安装根复跑留给主会话安装窗口；② 两例运行时仍被驱动记 `fail`（`unclassified failure`）：lencod 属驱动目录缺口、obsequi 属 libc random 序列，未改 known-fail/期望值/语料，建议另立 testcases/ISS 处置；③ riscv64 对照不可用（未注册）。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查方式**：自主逐行（`subagent_depth=1`，不嵌套）；对象 = `DADAOISelLowering.{h,cpp}` 两处新增、`DADAO.h` 一行、lit 新用例、证据脚本。

**逐行结论**：
1. `getSetCCResultType`：向量分支返回 `changeVectorElementTypeToInteger()`（与 Sparc 同法，RISCV 非 RVV 分支同义），标量分支 `getPointerTy(DL)` 与原基类返回 i64 一致 ⇒ 不改变既有标量 SETCC 行为（lit `setcc-select.ll` 等 103 例 + 12 例复跑佐证）。
2. `WCharType=SignedInt`：`WIntType` 未动，依据 musl `include/alltypes.h.in:37` `unsigned wint_t`；`__WCHAR_WIDTH__` 仍 32、`WCHAR_MIN/MAX` 自动跟随（`-dM` 实测）。
3. lit 用例：`CHECK-COUNT-6/3` 对应实测 6/3 条 `ld.ut`/`st.t`；修前红/修后绿均实跑（安装根 llc rc=-6）。
4. 证据脚本首轮 default 因 libc JSON 取键、lencod 子 shell `$(pwd)`、obsequi grep 目标三处缺陷 rc=1；已修并重跑（见下表）。
5. 注入还原：I1 `cp` 备份 + `sed` 注入 + `ninja llc` + md5 对账；`git -C .work/source/llvm-project status` 干净、HEAD 仍单 commit。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| (a) `case_counts` 取 `counts.total`（libc JSON 在顶层） | ✅已修 | 改 `c.get('total', d.get('total'))` | `B-mbsrtowcs-{static,dynamic} total=1 pass=1` |
| (b) lencod 重跑子 shell 内 `$(pwd)` 指向 run 目录 | ✅已修 | 子 shell 外取 `QEMU_ABS` | `A-lencod-run rc=0`、`A-lencod-oracle rc=0` |
| (c) obsequi 结论 grep 打在主日志（应读 `combined.out`） | ✅已修 | grep 目标改为 work-dir 的 `combined.out` | `A-obsequi-verdict rc=0` |
| (d) 构建树 builtins 旧（无 `__eqtf2`）致 2 例链接失败 | ✅已修 | 证据 wrapper 追加 `-resource-dir` 指向安装根 | `A-corpus-compile total=2 blocked=0` |
| (e) patch 行号 +11 使 isa-coverage 漂移 | ✅已修 | `gen_isa_coverage.py` 重派生 `md/tsv` | `check-isa-coverage rc=0`；`make check` rc=0 |

**判决**：无未修 finding；按派单**不改**任务状态（保持 `待开始`，由主会话处置）。**未做**：`install-host`/L2/L3（派单明确不跑）。

#### 第 1 轮 reviewer 验收
（待填）

#### architect 提交留痕（2026-10-19）
档位：**WIP**（`**状态**` = `待验收`，未获 reviewer 判决）；开工分支 `LLVM-105t` 提交 `b73d968`（本留痕与台账 3 册随 amend 并入；**未 push**）。文件集 8 项对账：3 份 patch（`series` 81 不变）/ `changelog.md` / 新增 lit `vec-load-widen.ll` / `llvm-isa-backend-matrix.{md,tsv}` / 本册 —— 与完成区「修改文件」一致（`.work/evidence/**` 由 `.gitignore` 排除、不入库）；另 `milestones.md` / `issues.yaml` / `INTEG-036m` 3 册为 architect 账面更新（状态、`ISS-253`/`ISS-265` notes、`ISS-276` 登记、里程碑行）。`check-patch-tree` **180** ✓、`make check`(L1) rc=0 ✓。
