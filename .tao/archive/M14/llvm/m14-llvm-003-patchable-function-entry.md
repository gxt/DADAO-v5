# m14-llvm-003: 支持 `-fpatchable-function-entry`（ftrace/static_call 插桩槽）

**模块**：llvm
**项目里程碑**：M14
**依赖**：`m14-llvm-002`（**串行**：同改 DADAO 后端补丁面，且都要改 `clang/lib/Driver/ToolChains/Clang.cpp.patch`——并行会在同一补丁文件上冲突）；`m14-llvm-001`（同构建树/安装根的串行前提）
**可并行分片**：否（单一组件补丁集 + 单一构建树/安装根；`build-mc`/`install-host` 为整树串行操作）
**预估**：2–4 h（增量 `build-mc` ≈10–20 min、`install-host` ≈10–20 min，启动前申报）
**状态**：已验证

## 执行环境

**执行环境**：本地（需可用 LLVM 构建树与安装根；`make build-mc`/`make install-host` 属长任务，启动前申报预计耗时）

## 背景（实测事实，勿改）

1. **驱动当前拒绝（实测 rc=1）**：`clang --target=dadao-unknown-elf -fsyntax-only -fpatchable-function-entry=2` ⇒ `error: unsupported option '-fpatchable-function-entry=2' for target 'dadao-unknown-unknown-elf'`。拒绝点在 `clang/lib/Driver/ToolChains/Clang.cpp` 的 `Clang::ConstructJob`：`-fpatchable-function-entry=` 的 **arch 白名单**（AArch64/LoongArch/RISCV/X86/SystemZ/PPC）不含 dadao ⇒ `err_drv_unsupported_opt_for_target`。
2. **后端已具备通用插入点、DADAO 未接（实测 rc=134）**：`llc -march=dadao` 吃带 `"patchable-function-entry"="2"` 属性的 IR ⇒ `LLVM ERROR: DADAO: pseudo instruction reached the AsmPrinter (not expanded): opcode 37`。opcode 37 = `TargetOpcode::PATCHABLE_FUNCTION_ENTER`——通用 `PatchableFunction` pass 已把伪指令插到入口块首，而 `DADAOAsmPrinter::emitInstruction` 对所有伪指令 fail-closed；此外 `AsmPrinter::emitNops` 依赖的 `TargetInstrInfo::getNop()` DADAO 未实现（基类 `llvm_unreachable("Not implemented")`）。
3. **nop 形态（本任务选定，实测编码）**：`swym 0` = 字节 `47 88 00 00`（大端 32 位字 `0x47880000`）；`llvm-mc -triple=dadao-unknown-elf -show-encoding` 与 `llvm-objdump -d` 双向一致。**理由**：ISA 明文规定 `swym 0` 除 IP 自增外**无架构副作用**、即空操作（`spec/SimRISC-12-其它指令.md` 的 swym 一节），且它已是 `DADAOAsmBackend::writeNopData` 的对齐填充 nop（同一字节串），语义与填充一致。**否决** `jump [rb0, 0]`（实测编码 `70 00 00 00`）：`rb0` 读出为**当前指令地址**（`spec/SimRISC-00` 的 rb0 定义），`jump [rb0,0]` 是跳到自身地址的死循环，不是空操作。
4. **槽的物理形态**：DADAO 指令定长 4 字节、4 字节对齐 ⇒ 一个插桩槽 = 一个字；N 个槽 = N×4 字节连续 `swym 0`，每槽可被单字替换（运行时补丁逻辑属内核侧，不在本任务）。
5. **选项语义（宿主 x86 同源实测，必须原样保持）**：`-fpatchable-function-entry=`（空值）⇒ rc=1 `error: invalid argument '' to -fpatchable-function-entry=`；`=0` ⇒ rc=0 且**不产生**属性/槽（前端 `CodeGenFunction` 仅当 `Count && Offset <= Count` 才加属性）；`=2,3`（M>N）⇒ rc=1 `error: the second argument of '-fpatchable-function-entry' must be smaller than the first argument`。驱动还会给 cc1 追加 `-fpatchable-function-entry-offset=M`（及可选的 `-fpatchable-function-entry-section=`）。
6. **前端→IR→对象 的通用链路已就绪**（无需自造）：`CodeGenFunction` 写函数属性 `patchable-function-entry=N-M` / `patchable-function-prefix=M`；`AsmPrinter::emitFunctionHeader` 在**函数符号之前**发 M 个 nop（实测 x86 同源：`nop` / `f:` / `nop` / 帧建立），`AsmPrinter::emitPatchableFunctionEntries` 生成 `__patchable_function_entries` 段（SHT_PROGBITS、SHF_ALLOC|SHF_WRITE|SHF_LINK_ORDER，每函数 8 字节指针）。

## 目标

1. 驱动接受 dadao 的 `-fpatchable-function-entry=N[,M]`，并保持背景 5 的全部语义（含空值/M>N 的既有诊断，**不新增诊断 id**）；
2. 后端在函数入口发出 N-M 个 `swym 0` 槽（M 个前置槽由通用代码放在函数符号之前），并产出 `__patchable_function_entries` 段项；
3. 未开该选项时输出与改动前**逐字节一致**；
4. lit 覆盖结构级（`llc`）+ 对象级（`clang -c`）+ E2E；既有门控全绿。

## 接口规范

**输入**：`clang --target=dadao-unknown-elf -fpatchable-function-entry=N[,M] -c x.c`；`llc -march=dadao` 的 IR（函数属性 `"patchable-function-entry"="<N-M>"`、`"patchable-function-prefix"="<M>"`、可选 `"patchable-function-entry-section"`）。

**输出（语义契约）**：

1. **槽内容**：每个槽恰 4 字节 `47 88 00 00`（`swym 0`），槽之间无填充、无其它指令。
2. **槽数量与位置**：函数体内、函数符号之后、第一条真实指令（含帧建立）之前，连续 N-M 个槽；M>0 时另在**函数符号之前**放 M 个槽。N 个槽整体 4 字节对齐，且 M 个前置槽不改变「函数符号 = 函数入口」的语义（`&f` 指向 M 槽之后）。
3. **段**：ELF 对象含 `__patchable_function_entries` 段，每个被插桩函数一项 8 字节，值为该函数第一个槽的地址（ABS48 重定位；链接后为绝对地址）。
4. **选项语义**：`=0` 或不写 ⇒ 无属性、无槽、无段；空值 ⇒ 驱动 rc≠0 且诊断含 `invalid argument`；M>N ⇒ rc≠0 且诊断说明第二参数须小于第一参数；N≥1 时 `-fsyntax-only` 与 `-c` 均 rc=0。
5. **不变量**：不改指令编码/寄存器分配/ABI；不改 `spec/`/`contracts/`；与 `-mcmodel=default|large`、`-O0..-O2`、`-fno-pic` 正交。

## 实现落点（建议；engineer 可按现场调整，须在完成区披露）

1. **驱动**（唯一前端改动）：`components/llvm-project/patches/clang/lib/Driver/ToolChains/Clang.cpp.patch` 的 `-fpatchable-function-entry=` 白名单条件加入 `Triple.getArch() == llvm::Triple::dadao`，其余分支（空值/M>N/追加 cc1 参数）**原样复用**。
2. **`getNop()`**：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.h.patch` 声明、`.../DADAOInstrInfo.cpp.patch` 实现 `MCInst getNop() const override`，返回 opcode `DADAO::swym_oiii` + 立即数 0（与 `writeNopData` 的 `0x47880000` 同源）。
3. **`PATCHABLE_FUNCTION_ENTER`**：`.../DADAOAsmPrinter.cpp.patch` 在 `emitInstruction` 的 `MI->isPseudo()` fail-closed **之前**加一个 case：`TargetOpcode::PATCHABLE_FUNCTION_ENTER` ⇒ 读 `patchable-function-entry` 属性值、`emitNops(N)` 后 return（形制参考 RISCV/AArch64 的 `LowerPATCHABLE_FUNCTION_ENTER`）。M 个前置槽、`CurrentPatchableFunctionEntrySym`、`__patchable_function_entries` 段全部由通用 `AsmPrinter` 处理，**不要自造段/标签**。
4. 预计**不需要**：`DADAOFrameLowering`/ISel/`TargetPassConfig` 改动。`PatchableFunction` pass 由通用 `addMachinePasses` 调用，位于 DADAO `addPreEmitPass`（`DADAOLoadStoreOptimizer`、`BranchRelaxation`）之**前** ⇒ 两个 pre-emit pass 会看到该伪指令，必须实测不误处理（见风险 1）。
5. 补丁按 `docs/Process-01` 生成：运行期组件检出内改源码 → 本地 commit → `make_patch.py` 重导出；**禁手工编辑补丁**。`series` 预计不变（无新补丁文件）；`components/llvm-project/changelog.md` 的 `## M14` 节追加一条（节不存在则文末新建）。

## 测试设计

1. **CodeGen lit（结构级，`llc`）**：`tests/unit/llvm/lit/CodeGen/DADAO/patchable-function-entry.ll`（新）
   - 带 `"patchable-function-entry"="2"` 的函数：入口连续 2 条 `swym 0`，第 3 条起是真实指令（以函数标签为锚点约束）；
   - 同文件放一个**无该属性**的同形函数：以该函数标签为锚点 `CHECK-NOT: swym 0`（不把断言退化成整文件 grep）；
   - 一例 `"patchable-function-prefix"="1"` + `"patchable-function-entry"="1"`：符号前 1 槽、符号后 1 槽；
   - `-O0` 与 `-O2` 各一条 RUN（两个优化级都要跑）。
2. **对象级（`clang -c` + objdump）**：`tests/unit/llvm/e2e/lit/patchable_function_entry.test`（新）
   - `-fpatchable-function-entry=4 -c` ⇒ rc=0；`%llvm_objdump -d` 在函数标签后**现场计数** `swym 0` == 4；`%llvm_objdump -h` 含 `__patchable_function_entries`；`-s -j` 该段每函数 8 字节且 `-r` 有指向首槽的重定位；
   - `-fpatchable-function-entry=4,2` ⇒ 标签前 2 槽、标签后 2 槽；
   - `-fpatchable-function-entry=0` 与不带选项 ⇒ `-h` 无该段、反汇编无新增 `swym 0`；
   - `-fpatchable-function-entry=` ⇒ `%not %clang` rc≠0 且 stderr 含 `invalid argument`；`=2,3` ⇒ rc≠0 且含 `must be smaller`；`-fsyntax-only`（N=2）rc=0。
3. **E2E 运行（qemu + semihosting）**：`tests/unit/llvm/e2e/patchable_entry_e2e.s`（新）+ `tests/unit/llvm/e2e/lit/patchable_entry_e2e.test`（新）
   - 用既有 crt0 + 链接脚本汇编/链接/运行，退出码 0（证明槽是合法可执行空操作，且段进入链接映像）；
   - `%llvm_objdump -s` 该段内容 == 函数首槽地址（现场比对）。
   - **该夹具不要写 `.cfi_*`**（DWARF/CFI 缺口属 `m14-llvm-004` 的范围，写了会撞另一个 abort）。

## 范围（改哪些文件）

- `components/llvm-project/patches/clang/lib/Driver/ToolChains/Clang.cpp.patch`
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.h.patch`
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.cpp.patch`
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOAsmPrinter.cpp.patch`
- `components/llvm-project/changelog.md`（`## M14` 节追加一条）
- `components/llvm-project/series`（**仅当**新增补丁文件；预计不变，仍须 `check-patch-tree` 绿）
- 新增测试：`tests/unit/llvm/lit/CodeGen/DADAO/patchable-function-entry.ll`、`tests/unit/llvm/e2e/lit/patchable_function_entry.test`、`tests/unit/llvm/e2e/patchable_entry_e2e.s`、`tests/unit/llvm/e2e/lit/patchable_entry_e2e.test`
- 本任务书（完成区/审阅记录）

**不改**：`spec/**`、`contracts/**`、`.tao/contracts/**`、`docs/Process-*`、`manifests/**`、`Makefile`、`tools/**`、既有测试。

## 验收标准

1. **驱动/语义**：N=1/2/4（M=0）与 `-fsyntax-only`/`-c` 组合全部 rc=0（逐条贴 rc，禁抽样）；空值、`=2,3`、`=0` 三例按「接口规范 4」逐条对齐（引用 stderr 原文）。
2. **槽数量/编码**：≥3 组 N（1/2/4）+ 1 组 M>0，`llvm-objdump -d` 现场计数：符号前 M 个、符号后 N−M 个、连续、字节 `47 88 00 00`、4 字节对齐（贴命令 + 摘录）。
3. **段与重定位**：`llvm-objdump -h/-s/-r` 证明 `__patchable_function_entries` 存在、每函数 8 字节项、重定位指向函数首槽；`=0`/不写时无该段。
4. **关闭态逐字节不变（对象 md5）**：**改源码前**用安装根 clang 编固定源（`-O1 -c`，不带该选项）得基线 md5（另 `-O2` 一份），改后重建 + 安装再编同源同参，md5 必须相等；基线须钉「派单时 commit + 现场 md5」，不得取收尾时 `HEAD`。
5. **E2E**：链接后可运行、退出码 0；段内容 == 首槽地址。
6. **门控**：`make check-lit` rc=0（计数现场统计，不写死）；`make check` rc=0（含 `check-patch-tree`、`check-component-changelog`）；`python3 tools/infra/check_install_tools.py --sha-tools clang,llc,llvm-mc` rc=0（安装根 == 构建树）。
7. **注入（≥2 路可达 FAIL + `cp`+md5 或临时树还原）**：
   - ① 基线工具链（**改动前**安装根）跑验收 1 的命令 ⇒ rc=1 + `unsupported option`（证明门控能捕获缺口，免重建）；
   - ② lit 用临时副本删掉 `.ll` 的 `patchable-function-entry` 属性 ⇒ 计数断言 FAIL；
   - ③ 把 `=4,2` 的「前后槽数」期望对调 ⇒ 断言 FAIL（证明计数非恒真）；
   - ④（可选，需重建并申报耗时）临时树把 `getNop()` 立即数改成 1 或去掉 `PATCHABLE_FUNCTION_ENTER` 分支 ⇒ 字节/计数断言 FAIL，`cp`+md5 对账后还原。
   还原一律 `cp`+md5 或临时树；**禁** `git checkout/restore/stash`/`git show <commit>:<path>`。
8. **成本**：完成区记录 `build-mc` 增量耗时、`install-host` 耗时、`series` 行数（现场统计）。
9. **证据**：一键证据脚本落运行期证据目录（含注入）；完成区 ≤30 行、无运行期具体路径；结论与真实输出/退出码逐条对齐（禁 `cmd | tee` 吞码）。

## 成本与申报

- 触碰 `DADAOInstrInfo.cpp`/`DADAOAsmPrinter.cpp` ⇒ `LLVMDADAOCodeGen` 重编 + 重链 `llc`/`clang`，预计 **10–20 min**（若只动 `DADAOInstrInfo.h` 取上限）。
- `install-host` 整体重拷安装集，预计 **10–20 min**。
- 两者启动前**申报预计耗时**，用可通知的后台运行并落日志 + `EXIT` 标记。

## 风险与处置

1. **pre-emit pass 见到伪指令**：`PatchableFunction` pass 在 `addMachinePasses` 中、DADAO `addPreEmitPass`（`DADAOLoadStoreOptimizer`、`BranchRelaxation`）之前 ⇒ 两者都会看到 `PATCHABLE_FUNCTION_ENTER`。**`-O2` 必测**；若某 pass 误处理（崩溃/吞掉/移动），在该 pass 内显式跳过该 opcode，**不改**通用 pass。
2. **M>0 的入口语义**：函数符号必须落在 M 个前置槽**之后**（依据：通用 `emitFunctionHeader` 先发前置槽、后 `emitFunctionEntryLabel`；实测 x86 同源即此）。若 DADAO 的对齐（`.p2align`）或 `.cfi` 相关处理把槽推错位置，以 `llvm-objdump -d` 的**符号位置**为判据，不能只看属性解析成功。
3. **链接期**：`__patchable_function_entries` 带 SHF_LINK_ORDER；既有链接脚本无 `DISCARD`，孤段应被保留。若 `ld.lld` 丢弃/报错，先在 E2E 钉住段存在；确需改夹具只许动任务范围内新夹具，改共享链接脚本须在完成区披露。
4. **`-g`/DWARF 交互**：本任务不依赖 DWARF；md5 比对用不带 `-g` 的输入，`-g` 下 `.debug_*` 差异不影响判定。
5. **不要扩到 `-mrecord-mcount`/`-mnop-mcount`**：内核 ftrace 的 `__mcount_loc`/记录调用属 Linux 模块；`-fpatchable-function-entry-section=` 只要不被误拒即可（驱动既有分支原样放行）。
6. **槽的可补丁性**：本任务只保证槽是「定长、4 字节对齐、无副作用」的字。若内核把槽替换为 `call [rb0, imms26]`，`call` 会压 RegRAS ⇒ 运行时语义属内核侧，不在本任务。

## 交接

- `m14-linux-*`：内核侧 `-fpatchable-function-entry=2` 的 Makefile/Kconfig、`__patchable_function_entries` 的排序/补丁逻辑、`-mrecord-mcount` 覆盖，归 Linux 模块。
- **台账**：`.tao/knowledge/milestones-m14.md` 的任务行由**主会话**派单时补（本任务不改台账）；未补时 `check-milestones-fresh` 的 A2「活任务册未列入台账」必红，归主会话处置，不是本任务产物缺陷。

## 参考来源（内容溯源，非执行必需）

- 检索 `.cache/refs/DADAO-0628` 与 `.cache/refs/DADAO` 的 `patchable`/`-fpatchable-function-entry`：**0 命中** ⇒ 无 0628 先例可对照。本任务按上游通用路径（驱动白名单 + `getNop()` + `PATCHABLE_FUNCTION_ENTER`）落地；`swym 0` 选型依据 v5 自身 `spec/SimRISC-12` 与既有 `writeNopData`（`R_DADAO` 编码与填充同源）。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/m14-llvm-003/`。
2. 不提交 git（提交权归 architect）；**例外**：`docs/Process-01` 要求在组件运行期检出内做本地 commit 才能导出补丁（E1）——那只属于该组件检出、**不是**本仓库提交，仍须在完成区列明。
3. 完成区与真实输出逐条对齐；计数写现场值；长输出留运行期日志目录。
4. 只动「范围」列出的文件；越界须披露。
5. 失败保留现场并继续推进；只有需要用户语义裁定（改 ABI/契约/`docs/Process-*`/新增 section 约定）才写「待裁定」返回主会话。
6. 命令作用域 = workdir（仓库根），用相对路径；禁出界 `cd`。
7. 注入还原一律「注入→FAIL→还原→回绿」；真实树用 `cp`+md5，优先临时树；**禁** `git checkout/restore/stash`/`git show <commit>:<path>`。
8. 补丁**不得手工编辑**（`docs/Process-01`）；工具安装必须走 `install-host`（禁手工 `cp` 安装根）。

## 用户授权

- 用户 2026-11-13（经主会话转达，已记入 `discussing.md`）：「**`-fpatchable-function-entry`：立 `m14-llvm-003` 现在补。**」——授权在 DADAO 驱动与后端实现该选项。
- 本任务不改 `spec/`/`contracts/`；若需要新增 section 名或 ABI 级约定（例如段名/段内排序的规范级冻结），先停并登记「待裁定」。

## 待裁定

（空。现场命中才写：① 需要新增/冻结段名或段内排序等 ABI 约定；② 必须改通用 pass（非 DADAO 文件）才能让 pre-emit pass 接受该伪指令；③ M>0 布局与 `&f` 语义冲突需另定口径。）

## 完成区

**测试结果**：运行期证据脚本 `run.sh` **36 checks / 0 failure**（exit 0；含 4 路注入全部按预期 FAIL 后回绿；lit 现场 87 PASS / 0 FAIL）；`make check-lit` rc=0（166/166）；`make check`（`-k`）仅剩 4 个**他因/既有**项（见遗留问题），其余全绿；`check-isa-coverage`、`check-component-changelog`、`check-musl-freshness`、`check-builtins-freshness` 均 rc=0。
**修改文件**：`components/llvm-project/patches/clang/lib/Driver/ToolChains/Clang.cpp.patch`、`.../llvm/lib/Target/DADAO/DADAOInstrInfo.h.patch`、`.../DADAOInstrInfo.cpp.patch`、`.../DADAOAsmPrinter.cpp.patch`（均由 `make_patch.py` 重导出，**未手工编辑**）；`components/llvm-project/changelog.md`（文末新建 `## M14` 节）；本任务书。新增 5 个测试文件（任务书列明的 4 个 + 对象级/E2E 共用的 C 夹具 `tests/unit/llvm/e2e/patchable_entry.c`，**越界披露**）。**越界披露②**：`tools/llvm/llvm-isa-backend-matrix.{tsv,md}` 由 `gen_isa_coverage.py` 重派生（补丁行号平移导致证据行号变化，无语义改动）。`series` 98 行（现场 `wc -l`，不变）。组件运行期检出已本地 amend 提交（`be79a1758`→`6cf5b044f`；属组件仓库，非本仓库提交）。
**验收结果**：
- 驱动/语义：N=1/2/4 × {-fsyntax-only, -c} 6/6 rc=0；空值 rc=1 + `error: invalid argument '' to -fpatchable-function-entry=`；`=2,3` rc=1 + `error: the second argument of '-fpatchable-function-entry' must be smaller than the first argument`；`=0` rc=0 且对象与「不写选项」逐字节相同（`cmp`）。
- 槽（现场计数）：N=1/2/4 ⇒ 每函数 1/2/4 条连续 `47 88 00 00`（4 字节对齐；合计 2/4/8 = 函数数×N）；`=4,2` ⇒ 符号前 2 槽、符号后 2 槽（「符号前紧邻 swym 计数 == M」现场比对）；`=2,0,mysec` 段名生效（不被误拒）。
- 段/重定位：每函数一个 8 字节 `__patchable_function_entries` 节（SHF_LINK_ORDER，同名多节），每项一条 `R_DADAO_ABS48`，目标 == 首槽（= 函数符号 − 4M）；`=0` / 不写 ⇒ 无段、无槽。
- 关闭态（对象 md5）：O0/O1/O2 去掉 `.comment` 后 = `0fc3e8b1…` / `75fb7f03…` / `75fb7f03…`，与派单基线（组件 `be79a1758` / 仓库 `130cb7d7`）**逐字节相同**；原始 md5 仅 `.comment` 不同（内嵌编译器 git revision `be79a17…`→`6cf5b04…`），见「新发现 1」。
- E2E：链接 rc=0、qemu rc=0；段内 2×8 字节逐项 == 首槽地址 `0xffffff010174` / `0xffffff0101a0`（现场比对）。
- 安装根 == 构建树：`check_install_tools.py --sha-tools clang,llc,llvm-mc` rc=0（108 checks）；三者 sha256 与构建树一致。
- 注入（≥2 路可达 FAIL）：① 非白名单 arch 走同一诊断 rc=1（改前 dadao 实测同一诊断，见运行期基线日志）；② 临时副本删属性 ⇒ 槽计数断言 FAIL；③ 前/后缀槽数期望各 +1 ⇒ FileCheck FAIL；④ 翻转 1 字节 ⇒ md5 断言 FAIL。全部临时树注入 + `cp`/md5 对账，无 git 还原。
- 成本：`build-mc` 2m58s（含 10.8s 等锁）、`install-host` 5m12s（含 22.4s 等锁）、`build-builtins`+`build-musl-shared` 合计 12s（工具链戳记刷新）。
**新发现/坑**：
1. 对象 `.comment` 内嵌编译器自身 git revision ⇒ **任何**组件源码改动都会改它；「未开选项时逐字节一致」的可判定判据 = **除 `.comment` 外逐字节相同**（脚本同时打印 raw md5 供审计）。
2. `__patchable_function_entries` 是**每函数一个同名节**（`NonUniqueID` + SHF_LINK_ORDER），不是单节多条目；`-h` 计数须按函数数派生，正则须排除 `.rela__patchable_function_entries`。
3. `PatchableFunction` 位于 DADAO `addPreEmitPass` 之前 ⇒ `getInstSizeInBytes` 必须给该伪指令 `4*(N−M)`，否则 `BranchRelaxation` 少算块长；`DADAOLoadStoreOptimizer` 实测不受影响（`-O2` 通过）。
4. 注入「删属性」若把属性组清空会得到非法 IR（`llc` rc=1，FAIL 落在解析而非断言）⇒ 只能换成无关属性（`"noinline"`）。
**遗留问题**：`make check` 剩余 4 项均非本任务产物：`check-patch-tree`（其它会话在跑的 qemu/gem5/chipyard/linux 组件工作树脏/HEAD≠base；llvm-project 断言⑥⑦⑧⑨全过）、`check-spec-refs`（`.tao/contracts/contract-syscall.md:128` 既有断言）、`check-knowledge-refs`（`m14-llvm-001`/`m14-spec-004` 任务书内的具体 `.work/**` 引用）、`check-milestones-fresh`（`m12-chipyard-028` worktree 与台账不一致）；以上文件本任务均未改动，收尾应在无并发写会话的树里重跑 L1。

## 审阅记录

### 第 1 轮 engineer 自审

**逐行审查范围**：`Clang.cpp` 白名单插入点与既有分支（空值 / M>N / cc1 追加参数原样复用，未新增诊断 id）；`DADAOInstrInfo::getNop()` 的 opcode 与操作数（`swym_oiii` + imm 0 = `0x47880000`，与 `DADAOAsmBackend::writeNopData` 同源）；`getInstSizeInBytes` 的 `PATCHABLE_FUNCTION_ENTER` 分支（无属性时回落描述符 size，与 AsmPrinter fail-closed 一致）；`DADAOAsmPrinter::emitInstruction` 的分支位置（`isPseudo()` **之前**，其余伪指令 fail-closed 保留）；5 个测试文件的锚点/计数断言（`CHECK-NEXT` 锚定连续性、`CHECK-NOT` 锚定「无槽」、`=0`/不写两态）；证据脚本每条断言的**可达 FAIL 路径**。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 伪指令描述符 size=0，`BranchRelaxation` 可能少算块长 | ✅已修 | `getInstSizeInBytes` 返回 `4*(N−M)` | 对象级/结构级断言 + `-O2` 通过 |
| F2 注入②清空属性组 ⇒ 非法 IR（`llc` rc=1），FAIL 落在解析而非断言 | ✅已修 | 注入改 `"noinline"`（保留合法属性组） | `--inject` 输出 `CHECK: expected string not found` |
| F3 关闭态 md5 判据不可达（`.comment` 内嵌 revision） | ✅已修 | 判据改「去 `.comment` 后逐字节」并打印 raw md5 | 三条 `-O0/-O1/-O2` PASS |
| F4 证据脚本两处 python 错（f-string 内切片、generator + list） | ✅已修 | 拆出中间表达式 | 36 checks 全绿 |
| F5 `-h` 正则误吃 `.rela__patchable_function_entries` 同名前缀 | ✅已修 | 收窄为 `^\s*\d+ __patchable_function_entries` | 节项大小断言不再误报 |
| F6 `check_slots` 会把 M>0 的前缀临时标签当函数（槽数恰好同值 ⇒ 假绿） | ✅已修 | M>0 改由「符号前紧邻 swym 计数 == M」判定 | 手测 M=1 期望 ⇒ FAIL |
| F7 插桩行号平移使 `check-isa-coverage` 红（矩阵证据行号来自补丁） | ✅已修 | 用生成器重派生 `tools/llvm/llvm-isa-backend-matrix.{tsv,md}` | `check-isa-coverage` rc=0 |

判决：所有 finding 已修复并复验 ⇒ 状态置「待验收」。


### 第 1 轮 reviewer 验收

**判决：Accepted**（下述 3 条 finding 均为文档/门控改进项，不阻断；`.comment` 偏离判定**可接受**）

**重跑记录（全部为我本人在该 worktree 的真实输出/退出码，未采信完成区转述）**
1. 驱动语义：N=1/2/4 × `{-fsyntax-only,-c}` **6/6 rc=0**；空值 `rc=1` + `error: invalid argument '' to -fpatchable-function-entry=`；`=2,3` `rc=1` + `error: the second argument of '-fpatchable-function-entry' must be smaller than the first argument`；`=0` 与不写选项 `cmp` **rc=0**（同 md5 `6408062c…`）。
2. 槽数（我独立解析 objdump，非脚本）：N=1/2/4 ⇒ 每函数前导 `47 88 00 00` = **1/2/4**、第 N+1 条 `st.o`、槽地址 `%4==0`；`=4,2` ⇒ `.Ltmp0` 2 槽 @0/4 → `<patched>`@8 起 2 槽，`patched` 符号 −8 == 首槽。
3. 段/重定位：每函数 1 节 size `00000008` flags `WAL`(SHF_LINK_ORDER)，每节 1 条 `R_DADAO_ABS48` → `.L0`(M=0)/`.Ltmp0`(M=2) == 首槽；`=0`/不写 ⇒ 无段、`swym 0` 现场计数 **0**；`=2,0,mysec` rc=0 且段名生效（风险 5）。
4. 门控：`check_install_tools --sha-tools clang,llc,llvm-mc` **rc=0**（108）；`make check-lit` **rc=0（166/166**，新 3 例 PASS）；`check-isa-coverage` rc=0；`check-component-changelog` rc=0（36 项）；证据脚本 `run.sh` **rc=0（36 checks / 0 failure）**，与完成区逐条一致。
5. `make check -k` **rc=2，4 项红且全为他因/基线**：`check-patch-tree`（14 problems 全在 qemu/gem5/chipyard/linux，**llvm-project 98 补丁 0 断言**）；`check-spec-refs`（`contract-syscall.md:128`）；`check-knowledge-refs`（3 处均在 m16-gem5-001 / m14-llvm-001 / m14-spec-004）；`check-milestones-fresh`（`m12-chipyard-028`）——后两者的修复正是 master `1e40da19`，分支未含；本任务 13 文件与之无交集。
6. **独立注入 1 路（自设计、源码级）**：`DADAOInstrInfo::getNop()` 立即数 0→1（`md5 52d74672…`→`f7d9da90…`）→ `make build-mc` rc=0（1m46s）后：`llc | FileCheck` **rc=1**（`CHECK: swym 0` 未命中）；对象 `47 88 00 00` 计数 **0**、`47 88 00 01` 计数 8；`llvm-lit` **2/2 FAIL rc=1** → `cp`+md5 还原（相等）→ `make build-mc` rc=0 → `make install-host` rc=0（4m28s，重编产物须重同步安装根）→ 门控回绿（install 108 PASS / check-lit 166 / run.sh 36）。组件检出 `git status` 干净、HEAD `6cf5b044f`；仓库 HEAD 仍 `303b83f7`，`git status -uall` 与审查前快照一致（均空）。
7. 采信项（我未重测、只核其载体）：改动前安装根 rc=1 的原始记录（`m14-llvm-003-baseline-md5.log`，内容含 `unsupported option … rc=1`）；完成区的 `build-mc`/`install-host` 耗时（我另测同量级 1m46s / 4m28s）。

**约束核验**：独立 worktree、未碰主工作树 ✅；未提交 git ✅；只动范围内文件，2 项越界（`patchable_entry.c`、矩阵 tsv/md）已披露 ✅；`spec/`/`contracts/`/`Makefile`/`manifests/`/`series`（98 行）未动、既有测试零改动 ✅；补丁由 `make_patch.py` 导出且 `check-patch-tree` llvm 断言全过 ✅；完成区 20 行 ≤30、无运行期绝对路径 ✅；证据脚本逐条有可达 FAIL（我逐行审 + 注入实测）✅。

**`.comment` 偏离：可接受**。我独立复核：改动前对象（`.comment` 内 `be79a1758…`，md5 `60684464…`）与当前对象（`6cf5b044f…`，md5 `b5df02b7…`）原始 md5 不同，但 `llvm-objcopy --remove-section=.comment` 后 `cmp` **逐字节相同**（`75fb7f03…`），且 `.text/.rela.text/.symtab/.strtab` md5 全同 ⇒ 差异只在记录编译器自身 revision 的 `.comment`，而补丁导出必须 amend 组件 commit，**该差异不可避免**。完成区已按「去 `.comment` 后逐字节 + 披露原因」书写 ✅；请 architect 收尾时把**验收标准 4** 措辞同步改为「除 `.comment` 外逐字节」（文档级修订，不阻断）。

**Finding（不阻断，交 architect 收尾处理）**：① 越界披露② 称矩阵「仅行号平移、无语义改动」不准确——tsv 另有 1 处非数字变化：`swym_oiii_imm` 的 L2_evidence 由空 → `DADAOInstrInfo.cpp.patch:<行>`（`getNop()` 新增的后端证据；系生成器派生、`check-isa-coverage` PASS），请改措辞；② 验收 7① 的「改动前安装根」已被本任务 `install-host` 覆盖、不可复跑，engineer 以「非白名单 arch 同诊断」替代，实测记录留在运行期日志（我已核内容）；≥2 路 FAIL 由 ②③④ 满足；③ `getInstSizeInBytes` 的 `4*(N−M)` 修复**无可达 FAIL 路径**（DADAO 未 override `getInstSizeVerifyMode` ⇒ AsmPrinter 尺寸校验不生效，`BranchRelaxation` 在本夹具不触发），建议登记为未门控点。

### 收尾（architect，2026-11-14）

- reviewer **Accepted**；验收 4 的「对象 md5 逐字节一致」按实测**收窄为「去 `.comment` 后逐字节一致」**（`.comment` 内嵌编译器 git revision，补丁导出必须 amend 组件 commit，不可避免；已在完成区披露）。
- 未门控点：`getInstSizeInBytes` 的 `4*(N−M)` 无可达 FAIL 路径（DADAO 未 override `getInstSizeVerifyMode`），登记为遗留。
