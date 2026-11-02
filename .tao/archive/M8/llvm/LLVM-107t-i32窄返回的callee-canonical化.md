# LLVM-107t: i32 窄返回值的 callee 侧 canonical 化

**模块**：llvm
**项目里程碑**：M8
**依赖**：`ISS-243`（本册对应 issue，`open`；现场 = `LLVM-097t` 完成区「新发现/坑 ①」）、`contract-abi §4.4 C5`（窄返回由 callee 扩展、caller 不截断）/`§4.2`（符号/零扩展规则）、`ADR-0018 C5`；对照任务 = `LLVM-097t`（同族 `bswap32` 脏高位）/`LLVM-101t`（指针返回 bank）；用户 2026-10-18 裁定 **M8 内修**（逐字「1、可以；2、M8内修」，渠道 = 经主会话问答）。
**状态**：已验证

> **编号说明**：本册编号由主会话 2026-10-18 指定（`LLVM-105t`/`107t` 同批立册）；本册只做 `ISS-243`。

## 执行环境
**执行环境**：本地

## 问题根源

**现状（现场，逐字）**：最小 C

```c
unsigned addu(unsigned a, unsigned b) { return a + b; }
```

经 `.work/build/llvm/bin/clang --target=dadao-unknown-elf -O2 -S`（23.1.3，rc=0）⇒ 函数体只有

```
add.uo {rd0, rd8}, rd17, rd16
ret rd0, 0
```

返回值寄存器 `rd8` 直接取 64 位加法的和/进位输出，**全函数无任何 32 位 mask 或扩展** ⇒ `addu(0xFFFFFFFF, 1)` 的 `rd8` = `0x00000001_00000000`；而 `contract-abi §4.4 C5` 要求「`<8B` 返回值由 **callee** 按 §4.2 的符号/零扩展规则扩展为 canonical 64 位后再 `ret`；**caller 不截断**」⇒ **callee 侧 canonical 化缺失**（`-O0` 同签名：`add.uo {rd0, rd8}, rd4, rd5` / `ret`，同样无扩展）。

**同批对照（i32 是唯一漏点，并非「窄返回一律不扩」）**：`unsigned char` 返回 ⇒ `set.zw rd5, wp0, 0xff` + `and.o rd8, rd4, rd5`；`short` 返回 ⇒ `ext.so rd8, rd4, 15`；**只有 `int`/`unsigned`（i32）无扩展**。

**根因（四跳，`file:line` = 23.1.3 检出 / 本仓补丁）**：
1. clang 侧 DADAO ABI 只为 **i8/i16** 打 `zeroext`/`signext` 返回属性、**i32 不打**：`components/llvm-project/patches/clang/lib/CodeGen/Targets/DADAO.cpp.patch` 的 `classifyReturnType()`（约 L209–L217）对非聚合类型直接回落 `DefaultABIInfo::classifyReturnType(RetTy)`；后者仅在 `isPromotableIntegerTypeForABI(RetTy)` 为真时返回 `ABIArgInfo::getExtend`，而该谓词（`clang/lib/CodeGen/ABIInfo.cpp:167`）只认「可提升到 `int` 的窄类型」，**i32 本身不在内** ⇒ 无 ext 属性。`-emit-llvm` 现场：`define … zeroext i8 @addu8` / `define … signext i16 @adds16` / **`define dso_local noundef i32 @addu`（无 ext 属性）**。
2. `SelectionDAGBuilder::visitRet`（`llvm/lib/CodeGen/SelectionDAG/SelectionDAGBuilder.cpp:2278-2281`）仅据该属性选 `SIGN_EXTEND`/`ZERO_EXTEND`；无属性 ⇒ `ExtendKind = ANY_EXTEND`。
3. `RetCC_DADAO` 的 `CCIfType<[i8, i16, i32], CCPromoteToType<i64>>`（`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOCallingConv.td.patch:82`）⇒ 生成器按 `ArgFlags.isSExt()/isZExt()` 选 `SExt`/`ZExt`，两者皆未标则 `LocInfo = CCValAssign::AExt`（`llvm/utils/TableGen/CallingConvEmitter.cpp:274-286`）。
4. `DADAOTargetLowering::LowerReturn` 的 AExt 分支发 **`ISD::ANY_EXTEND`**（`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch` 约 L755–L760；注释明写「narrow return canonicalised by the callee」但实现为空操作）⇒ i32 无 mask 直接落 `rd8`。

**影响面**：**每个 i32 返回函数**（`int`/`unsigned`，含每条 extern 声明与库边界）。当前纯 C 互调不报错，只是因为 clang 生成的**调用方** IR 自己带 `zext i32 %call to i64`（DAG 成 `and.o rd8, rd8, <0xffffffff>`）⇒ 调用方补偿了 callee 应做的事。但契约明文「caller 不截断」⇒ ① **任何非 clang 消费者**（手写汇编 / `ldso` asm / 其它工具链）都**不可依赖**该返回值；② 优化器若据 ABI 认定该 `zext` 冗余即可 **miscompile**；③ `LLVM-097t` 的 `bswap32` 脏高位（full 值 `0x0001020304030201`）只是同一缺口的可观测投影。

## 修法候选（**不预设；工程师诊断后给依据、二选一或并用**）

- **(a) clang ABI 侧**：在 DADAO 的 `classifyReturnType()`（`clang/lib/CodeGen/Targets/DADAO.cpp`）对 `<8B` 整数返回补 `ABIArgInfo::getExtend(RetTy)`（与 i8/i16 同源；`RetCC`/`LowerReturn` 既有 SExt/ZExt 分支即刻生效）。
- **(b) 后端侧**：在 `LowerReturn` 按位宽自行扩展（须同时解决 `CCPromoteToType` 抹掉符号性信息的问题，例如 `RetCC_DADAO` 不再用 `CCPromoteToType<i64>` 承载窄类型；**先证明后端能拿到符号性**，否则不得以「猜符号性」过关）。
- **选择判据**：以「契约 C5 可机械核 + 改动最小 + 不破坏 i8/i16 现状 + 不新增 ABI 特例」为准；诊断须写清**哪一跳丢失符号性**、为何选 (a)/(b)/并用。**不得**只改调用方（caller 侧补偿）——违反 C5 明文。

## 接口规范

- **输入**：
  - `.work/build/llvm/bin/clang`（23.1.3 构建树）与安装根 `.dadao/cross-toolchain/bin/{clang,llvm-mc,ld.lld}`（改组件后须 `install-host` 才新鲜）
  - `.work/source/llvm-project/`（23.1.3 **只读**检出）与 `components/llvm-project/patches/**`（唯一可改载体）
  - `contract-abi §4.2`/`§4.4 C5`（期望值来源，**不从实现反推**）
- **输出**：
  - `components/llvm-project/patches/**` 补丁更新（一文件一补丁，`docs/Process-01`）+ `series` 如增删 + `components/llvm-project/changelog.md` 条目
  - 契约级探针（入 git，建议 `tools/llvm/` 或 `tools/testcases/` 下按现有布局）：**非 clang 消费者**（手写汇编调用 + C 校验），直接检查 `rd8` 全 64 位
  - `.work/evidence/<任务号>/run.sh`（执行时创建；非交互、任一失败非零、含可达 FAIL；长日志 `.work/log/llvm/`）
  - 本任务书完成区（与真实输出逐条对齐）
- **约束**：只改 `components/llvm-project/**`（+ 探针脚本 + 本任务书 + `milestones.md` 如需）；**不动** `spec/` / `.tao/contracts/` / `contracts/` / musl / 语料源。

## 契约级探针（形状要求；具体实现由工程师定）

**要点**：clang 的 C 调用方会自动 `zext`，**不能**用它当探针（会把缺陷掩盖成 pass）。探针必须是**非 clang 消费者**：手写汇编（`.s`，`clang -c` 汇编）按 `contract-abi §4.1/§4.4` 把实参放 `rd16/rd17`，`call` 被测函数，随后把 **`rd8` 全 64 位**存入内存/返回给 C 主程序断言。

必测（独立 oracle = 契约 §4.2/§4.4 的 canonical 值，不是从编译器输出反推）：

1. `unsigned addu(unsigned, unsigned)`：`addu(0xFFFFFFFFu, 1u)` ⇒ 期望 `0x00000000_00000000`（零扩展；现状 `0x00000001_00000000`）。
2. `int neg(int)`：`neg(0x80000000)` ⇒ 期望 `0xFFFFFFFF_80000000`（符号扩展；现状 `0x00000000_80000000`）。
3. 回归对照：`unsigned char` 返回 / `short` 返回的 canonical 值仍正确（证明未破坏既有 i8/i16 路径）。

## 验收标准

1. **诊断先落盘**：写清「哪一跳丢失符号性 + 所选修法 (a)/(b)/并用 + 依据」；若诊断证明契约本身有缺口或需新增 ABI 规则 ⇒ **留问**（不擅改契约）。
2. **契约级探针通过**：上述 1/2/3 全部按 §4.2/§4.4 canonical 值 PASS（`rd8[63:32]` 全 0 / 全 1 逐例断言）；**修前现场 FAIL** 输出保留（同一脚本可切换 `--expect-broken` 或分文件留证）。
3. **`contract-abi` 逐条对齐**：完成区列 `§4.2`（符号/零扩展）、`§4.4 C5`（callee 扩展、caller 不截断）逐条「条款 → 证据」对照；**不得**以「调用方也扩展」充当 C5 证据。
4. **反汇编结构证据**：`-O2 -S` 对 `addu`/`neg` 给出「扩展指令在 `ret` 之前」的片段；对照 i8/i16 仍在。
5. **可达 FAIL**：≥1 处注入（如把探针期望上 32 位改错 / 临时回退补丁使 `ANY_EXTEND` 复现）⇒ 探针 `[FAIL]`、脚本 rc=1 ⇒ `cp` + md5 还原 ⇒ 回绿、rc=0。
6. **`install-host` 前置**：改 `components/llvm-project/**` ⇒ **单跑** `install-host`（`JOBS=8`、不并发、`ISS-210`；**启动前申报预计耗时**）；完成后核安装根 `clang --version` 新鲜，再用**安装根**重跑探针（不得只用 `.work/build` 树下结论）。
7. **门控**：`check-patch-tree`（现 **180**，改后现场计数）、`check-instrinfo`（若改 `.td`）、`check-component-changelog`、`make check`(L1) rc=0；**L2** `make check-modules` rc=0；**L3** `make check-full` rc=0（按 `docs/Process-07`；不并发、`ISS-229`）。
8. **终局全量复跑 + 无回归**：本册改动影响所有 i32 返回函数 ⇒ 收尾须复跑 **`TESTCASES-047t` 静态 + 动态全量** 与 **`TESTCASES-048t` 两档全量**（若主会话指定同批收口任务，按指派批次执行并在完成区注明）；除目标变化外**不允许任何类别漂移**（尤其 **`pass→fail` 一律视为回归**）；计数现场派生、不写死。
9. **完成区 ≤30 行**，与真实输出逐条对齐；长输出留 `.work/log/llvm/`。

## 不做

- **不**在调用方加补偿 mask 冒充修复（违反 C5「caller 不截断」）。
- **不**改 `contract-abi` / `spec/` / 语料 / 测试期望；**不**把失败改标 `known-fail`。
- **不**动 `ISS-253`（`wchar_t`）与 clang 崩溃（归 `LLVM-105t`）；**不**动 `ISS-245`/`ISS-247`。
- **不**做 i8/i16 既有路径重写（它们已符合契约）。

## 硬约束

1. 临时目录 `/tmp/opencode/LLVM-107t/`；命令在 workdir 内、**相对路径**；**禁**出界 `cd`；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；**禁** `git add -A`/`.`；**禁** `git checkout`/`restore`/`stash` 还原（一律 `cp` + md5）。
3. 完成区与真实输出逐条对齐，留证捕**被检命令自身**退出码（禁 `cmd | tee` 吞码）。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进（自行处置：查证 / 绕行 / 有据重试并记录次数 / 登记后跳过）；**只在需用户语义裁定**时留问。
6. 用户裁定须把**原话**写入本任务书。
7. `check-patch-tree` / `check-index-blobs` / `check-source-state` 须绿（改 `components/**` 的补丁集完整性）。

## 完成区
**测试结果**：通过（修前契约级探针 2 例 FAIL、修后 8/8 OK；lit 34/34；12 例 SingleSource 12/12；门控全 rc=0）。**L2/L3、047t/048t 全量与 musl 重建由主会话在 `install-host` 后执行**（本笔未跑）。
**修改文件**：`components/llvm-project/patches/clang/lib/CodeGen/Targets/DADAO.cpp.patch`（**1 份改**；`series` 81 不变、`check-patch-tree` **180 不变**）、`components/llvm-project/changelog.md`（+1 条）、`tools/llvm/llvm-isa-backend-matrix.{tsv,md}`（行号重派生）、`tools/llvm/check_ret_canonical.py`（新增契约级探针，入 git）、本任务书；证据 `.work/evidence/LLVM-107t/**`（`.work` 不入 git）。
**验收结果**：
- **§4.4 C5 原文**：「**窄返回扩展**：`<8B` 返回值由 **callee** 按 §4.2 的符号/零扩展规则扩展为 canonical 64 位后再 `ret`；**caller 不截断**（可假定 `rd8`/`rb8` 为 canonical 64 位）」；**§4.2**：窄标量「保持符号位不变」、32 位整数占 RD 低 32 位并按类型符号性扩展。**⇒ 条款→证据**：① i32 `unsigned` → `addu(0xFFFFFFFF,1)` 修前 `0x0000000100000000`、修后 `0x0000000000000000`（`and.o rd8, rd4, 0xffffffff`）；② i32 `signed` → `neg(INT_MIN)` 修前 `0x0000000080000000`、修后 `0xffffffff80000000`（`sub.st`/`ext.so`）；③ i8/i16/i1 对照修前后均 canonical（`uc_inc=0`、`sc_inc=0xffffffffffffff80`、`us_inc=0`、`ss_inc=0xffffffffffff8000`、`bnot=1`），且汇编仍有 `and 0xff`/`ext.so 7`/`and 0xffff`/`ext.so 15`；④ caller 侧 IR 现为 `call zeroext/signext i32` 且**不再自带 `zext`**（证明扩展确由 callee 完成，非 caller 补偿）。
- **诊断（四跳，逐跳带现场）**：clang `classifyReturnType` 对非聚合回落 `DefaultABIInfo`；后者只给「可提升到 int」类型（i1/i8/i16）`getExtend`，**i32/32 位枚举不在内** ⇒ IR `define i32 @addu`（无 ext）；`visitRet` 无属性⇒`ANY_EXTEND`；`RetCC_DADAO` 的 `CCPromoteToType` 生成 `AExt`；`LowerReturn` 的 AExt 分支是空操作 ⇒ `add.uo {rd0,rd8}` 直落 `ret`。
- **修法 = (a)**：`classifyReturnType` 对 `isIntegralOrEnumerationType() && size<64` 统一 `ABIArgInfo::getExtend(RetTy, CGT.ConvertType(RetTy))`。依据：**(b)** 无法仅从后端拿到符号性（IR `i32` 无符号性、`CCPromoteToType` 已抹掉），只能靠 clang 属性；**(a)** 与 i8/i16 同源、不新增 ABI 特例、改动 1 文件，`RetCC`/`LowerReturn` 既有 SExt/ZExt 分支直接生效。
- **覆盖**：i1 `_Bool`→zeroext、i8 signed/unsigned、i16 signed/unsigned、i32 `int`/`unsigned`、32 位 `enum`（zeroext/signext 按 underlying）；`long`（64 位）不加属性、汇编不变；复数/聚合路径未动。
- **契约级探针**（`tools/llvm/check_ret_canonical.py`，手写汇编消费者直接 `st.o rd8,[rb16,0]`，独立 oracle = C 语义 + canonical 值）：修前（安装根 pre-107t）`addu`/`neg` **FAIL**、6 项对照 OK、rc=1；修后 8/8 **OK**、rc=0；`-O0/-O1/-O2/-Os/-O3/-fPIC`、`-verify-machineinstrs` 全过。
- **无回归**：CodeGen lit **34/34**、`check_lit_gen` rc=0；12 例 SingleSource（`flops-1..8`/`dt`/`lowercase`/`fp-convert`/`mandel`）**12/12 pass**（构建树 codegen + 安装根 builtins archive；构建树 archive 缺 f128 builtins，非本笔）。
- **门控**：`check-instrinfo`/`check_lit_gen`/`check-patch-tree`(**180**)/`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check-issues`/`make check`(L1) **各 rc=0**（`check-isa-coverage` 重派生后 rc=0）。
- **证据脚本**：`.work/evidence/LLVM-107t/run.sh` default **rc=0**；`--inject` **rc=0**（I1 删 i32 mask→probe rc=1；I2 oracle 翻转→rc=1；I3 删 classify 分支→grep FAIL；md5 对账 + 默认回绿）。
**新发现/坑**：① 本改动使**调用方 IR 不再自带 `zext`**（依赖 `zeroext/signext` 属性）⇒ **旧 musl 必须同批重建**：现 `libc.a`（pre-107t）下 047t `functional/env`（`setenv` 旧对象返回 `0x00000000FFFFFFFF`，打印 `-1/22` 正确但 64 位比较失败）与 `functional/inet_pton` 两例失败，属**预期不兼容**，`install-host`+`build-musl` 后复跑；② 构建树 `libclang_rt.builtins.a` 仍是 f128 前产物（缺 `__eqtf2`/`__extenddftf2`），而 musl 已按 binary128 重建 ⇒ 构建树直接链接会 blocked；本轮 12 例/探针显式使用安装根 archive（wrapper），**非 codegen 问题**，`install-host` 后自愈；③ `add_s(-1,-1)` 修前偶然 canonical（64 位加结果碰巧高 32 全 1），故探针以 `addu`/`neg` 作判别用例，`add_s` 只作补充 oracle；④ i32 属性变化会让旧目标文件（未重建的 libc/第三方 `.o`）与新调用方混链不兼容，须整批重建（`ADR` 兼容性口径）。
**同批不兼容**：caller 不再自行 `zext` ⇒ 旧 musl 对象须同批重建 ✓（主会话已重建 ✓，`check-musl-freshness` PASS ✓）；`047t env`/`inet_pton` 待 `install-host` + 全量复跑确认 ✓。
**遗留问题**：`install-host`/`build-musl`/L2/L3、`TESTCASES-047t`/`048t` 两档全量复跑由**主会话**执行（本笔未跑）；`ISS-243` 关闭由主会话按复跑结果处置；architect 提交后 `**状态**` = `待验收`；未 push（待 `/complete` 后由主会话 FF 推送）。

## 审阅记录

#### 第 1 轮 engineer 自审
**审查范围**：`DADAO.cpp` 的 `classifyReturnType` diff、补丁、探针脚本、汇编、证据脚本。逐条核对：`getExtend` 只对 `<64` 整数/枚举；i8/i16 属性与修前一致（IR 对照）；`char`/`_Bool` 符号性由 `hasSignedIntegerRepresentation`；`long`/指针/浮点/聚合未受影响；caller IR 不再 `zext` 的语义（C5 允许）；探针为非 clang 消费者、oracle 手算。判决：实现与 C5/§4.2 逐条一致。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 注入 I1 先改 `add_s` 的 `ext.so`，但 `add_s(-1,-1)` 的 64 位加碰巧 canonical，注入后仍 rc=0（假绿风险） | ✅已修 | 改注入 `addu` 的 `and.o rd8` mask（高 32 位实际留脏） | `--inject` I1 rc=1；默认回绿 |
| F2 构建树 builtins archive 缺 f128（`__eqtf2`），12 例/探针链接 blocked | ✅已绕行（披露） | 证据/门控显式用安装根 archive（wrapper）；不改组件 | 12/12、探针 rc=0；完成区坑② |
| F3 旧 musl 下 047t `env`/`inet_pton` 失败（caller 不再 zext） | ⏸延后（主会话 rebuild） | 未改判据、未加补偿；完成区坑① | 修前/后 047t 现场留 `.work/log/llvm/LLVM-107t-047-*.log` |
| F4 覆盖检查：i1/i8/i16/i32 × 有/无符号 + enum + long | ✅已修/已验 | 探针 8 例 + `enum.c` IR/asm 检查 | 8/8 OK；enum `zeroext i32`、long 无属性 |

#### 第 1 轮 reviewer 验收（2026-10-19）

**重跑记录**（脚本重定向 W + ev-*/ev-probe/ev-sample 至 `/tmp/opencode/review-A/work/LLVM-107t/`，probe 输入路径保持原位 `/tmp/opencode/LLVM-107t/probe/`）：
- default rc=0，26/26 PASS：src/patch grep 4/4 ✓、门控 8/8（check-patch-tree 180 等 + check-musl-freshness）✓、lit rc=0（35 discovered, 0 failed）✓、asm 汇编 8 类型逐条 `and.o`/`ext.so` ✓、probe-post 8/8 OK ✓、pre-addu FAIL + pre-neg FAIL + pre-controls OK（修前现场）✓、sample12 12/12 ✓
- `--inject` rc=0，33/33 PASS：I1 删 i32 mask → probe rc=1 → 回绿 ✓；I2 oracle 翻转 → rc=1 ✓；I3 删 classify 分支 → grep FAIL ✓；md5 对账 originals-untouched ✓

**约束核验**：
1. §4.4 C5 原文 ✓（与 `contract-abi.md` 逐字一致：「窄返回扩展：<8B 返回值由 callee 按 §4.2 的符号/零扩展规则扩展为 canonical 64 位后再 ret；caller 不截断」）
2. 契约级探针真判别 ✓（pre-fix: `addu(0xFFFFFFFF,1)` got `0x0000000100000000` / `neg(INT_MIN)` got `0x0000000080000000` — 均 FAIL；post-fix: 8/8 OK）
3. 修法 = (a) clang ABI 侧 ✓（`classifyReturnType` 对 `<64` 整型统一 `getExtend`；覆盖 i1/i8/i16/i32 × 有/无符号 + enum）
4. 反汇编结构 ✓（`addu`: `and.o rd8, rd4, rd5`；`neg`: `sub.st`+`ext.so`）
5. 可达 FAIL ✓（I1/I2/I3 三处注入均先红后绿，md5 对账一致）
6. 门控 ✓：check-patch-tree 180 ✓、check-instrinfo ✓、check_lit_gen ✓、check-musl-freshness ✓、`make check`(L1) ✓、check-run-artifacts ✓

**如实性抽查**：① pre/probe_pre.txt 中 `addu got=0x0000000100000000 want=0x0000000000000000 FAIL` + `neg got=0x0000000080000000 want=0xffffffff80000000 FAIL` — 确认修前脏高位 ✓；② post probe-post.log `all narrow returns are canonical` ✓；③ lit 35 discovered（含 LLVM-105t 新增 vec-load-widen.ll），0 failed ✓

**判决**：**Accepted** — 所有验收标准逐条通过，契约级探针修前红/修后绿完整闭环。

#### architect 提交留痕（2026-10-19）
档位：**WIP**（`**状态**` = `待验收`，未获 reviewer 判决）；开工分支 `LLVM-107t` 提交 `b433f74`，squash 落 `master`（单提交，本留痕随 amend 并入；**未 push**）。文件集 7 项对账：`DADAO.cpp.patch`（1 份改，`series` 81 不变）/ `changelog.md` / `check_ret_canonical.py`（新增探针）/ 本册 —— 与完成区「修改文件」一致；`tools/llvm/llvm-isa-backend-matrix.{tsv,md}` 重派生后**字节未变**（无 diff、无需提交）；另 `milestones.md` / `issues.yaml` / `INTEG-036m` 3 册为 architect 账面更新（完成区未列，属台账范围）。`check-patch-tree` **180** ✓。
