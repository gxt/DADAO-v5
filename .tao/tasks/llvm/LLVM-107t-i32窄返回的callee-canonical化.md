# LLVM-107t: i32 窄返回值的 callee 侧 canonical 化

**模块**：llvm
**项目里程碑**：M8
**依赖**：`ISS-243`（本册对应 issue，`open`；现场 = `LLVM-097t` 完成区「新发现/坑 ①」）、`contract-abi §4.4 C5`（窄返回由 callee 扩展、caller 不截断）/`§4.2`（符号/零扩展规则）、`ADR-0018 C5`；对照任务 = `LLVM-097t`（同族 `bswap32` 脏高位）/`LLVM-101t`（指针返回 bank）；用户 2026-10-18 裁定 **M8 内修**（逐字「1、可以；2、M8内修」，渠道 = 经主会话问答）。
**状态**：待开始

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
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
