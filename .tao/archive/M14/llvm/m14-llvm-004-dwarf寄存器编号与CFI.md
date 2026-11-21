# m14-llvm-004: DADAO DWARF 寄存器编号表与 CFI（`.cfi_*` 不崩溃）

**模块**：llvm
**项目里程碑**：M14
**依赖**：`m14-llvm-003`（**串行**：同为 DADAO 后端补丁面，且共用同一构建树/安装根；003 的 E2E 夹具也刻意不写 `.cfi_*`，本任务补齐后再考虑 CFI 夹具）
**可并行分片**：否（单一组件补丁集 + 单一构建树/安装根；`build-mc`/`install-host` 为整树串行操作）
**预估**：4–8 h（含 1–2 轮 `build-mc` ≈10–20 min/轮、`install-host` ≈10–20 min，启动前申报）
**状态**：已验证

## 执行环境

**执行环境**：本地（需可用 LLVM 构建树与安装根；`make build-mc`/`make install-host` 属长任务，启动前申报预计耗时）

## 背景（实测事实，勿改）

1. **崩溃（实测，core dumped）**：`llvm-mc -triple=dadao-unknown-elf -filetype=obj` 汇编配对 `.cfi_startproc/.cfi_endproc` ⇒ `llvm/lib/MC/MCDwarf.cpp:1947: Assertion 'RAReg <= 255 && "DWARF 2 encodes return_address_register in one byte"' failed`（rc=134）。
2. **根因链**：`FrameEmitterImpl::EmitCIE` 取 `RAReg = MRI->getDwarfRegNum(MRI->getRARegister(), IsEH)`；DADAO 的 `MCRegisterInfo` **没有 DWARF 编号表**（`DADAORegisterInfo.td` 只有 `def RBSP : ..., DwarfRegAlias<rb1>`，而 `rb1` 自身没有 `DwarfRegNum`）⇒ `getDwarfRegNum` 返回 `-1` ⇒ `unsigned RAReg` = `0xFFFFFFFF` ⇒ 断言失败。
3. **与「64 位 DWARF」无关（实测）**：断言在 `if (CIEVersion == 1)` 分支；`getCIEVersion(IsEH, DwarfVersion)` 对 **`.eh_frame`（IsEH=true）恒返回 1**，与 DWARF64 默认、`-dwarf-version=4` 都无关（实测加 `-dwarf-version=4` 仍 abort，退出码 134）。**不要**把原因归到地址宽度。
4. **RA 寄存器当前被设成 SP**：`createDadaoMCRegInfo` 调 `InitDADAOMCRegisterInfo(X, DADAO::RBSP /* RA = SP */)`。`MCRegisterInfo::getRARegister()` 在 LLVM 里**唯一消费者**就是上述 CIE 代码（`llvm/lib/{CodeGen,MC}` 与 `include/llvm/CodeGen` 全量 grep 仅 `MCDwarf.cpp`）⇒ 改成 `RA63`（RegRAS 栈顶，`spec/SimRISC-00 §2.4`）不影响代码生成，只改 CIE 的 RA 列。engineer 仍须现场复核该唯一性。
5. **「不崩溃」≠「正确」**：绕开断言（例：`-g` 下显式 `.cfi_sections .debug_frame` 走 DWARF64）能产出对象，但 `llvm-dwarfdump --debug-frame` 显示 **`Return address column: -1`**、且 `.cfi_offset rb2, -8` 被打印成 **`DW_CFA_offset_extended: reg4294967295 -8`** ⇒ 缺编号表产出的是**非法 CFI**（不是"没崩溃就算过"）。任何"只压断言/跳过 CFI"的改法一律不接受。
6. **`.eh_frame` 的 FDE 地址编码也是缺口**：`MCObjectFileInfo::initELFMCObjectFileInfo` 对未知 arch 默认 `FDECFIEncoding = DW_EH_PE_pcrel | DW_EH_PE_sdata4`（4 字节 PC 相对）；DADAO **没有 32 位 PC 相对数据重定位通道**（`DADAO.def` 只有指令域 REL26/20/14 与 8 字节 `R_DADAO_ABS48`）。对照实测：`.debug_frame` 走 `DW_EH_PE_absptr`（8 字节）时在 `-g` 下可产出对象，只有 dwarfdump 对 `R_DADAO_ABS48` 的"无法反算地址"告警；而不带 `-g`（DWARF32，4 字节字段）时 `.debug_frame` 直接报 `relocatable operand in a 1/2/4-byte data field ... use '.dd.o64'`。⇒ `.eh_frame` 必须把 DADAO 的 FDE 编码定为 `DW_EH_PE_absptr`。
7. **现状边界**：`clang -g`/`-funwind-tables` 编 DADAO C 源当前**不发射** `.cfi_*`（实测 `-S` 中 `cfi` 计数 0）⇒ 本缺口目前只咬**手写汇编**（内核 entry/上下文切换）与将来打开 unwind 表的时候。

## 目标

**默认走方案 1（正面支持）**：补齐 DWARF 寄存器编号表 + 把 RA 寄存器改为 `ra63` + 修正 `.eh_frame` 的 FDE 编码 ⇒ `.cfi_*` 可汇编、CIE/FDE 合法可解析、RA 编号 ≤255，且**不崩溃**。只有当出现"编号方案不可行"的实证时才退回方案 2（显式诊断 rc≠0、文档写明不支持 CFI），并把证据与理由写进完成区。

**「不崩溃」是硬要求，无论选哪条**：不得 abort/core dump，不得静默产出非法 CFI。

## 方案与判据

**方案 1（默认，推荐）**：完整编号表——4 个 bank × 64 = 256 个寄存器，编号唯一且落 0..255：

- `rd0–rd63 → 0–63`、`rb0–rb63 → 64–127`、`rf0–rf63 → 128–191`、`ra0–ra63 → 192–255`（⇒ `RA63` = **255**，恰在"一字节"上限内，断言取 `<=255`）；
- `RBSP` 保留 `DwarfRegAlias<rb1>`（沿用 65，别名不重复占号）。

**理由**：4×64 恰好填满 0..255、无重叠；v5 的 RF bank 在 M6 已实现，必须给 rf 留号段（若照搬"ra→128+i"的参考写法会与 rf 段**撞号**，今后 `.cfi_offset rfN`/DWARF 变量位置会解析到错误寄存器）。**另一条硬约束**：EH frame 的 CIE 版本恒为 1 ⇒ RA 列只能是一字节（背景 3），所以 255 是上限而不是"够用就好"。

**方案 2（备选，仅当 1 被证伪）**：在 MC 层对 DADAO 的 `.cfi_*` 给明确错误（诊断 + rc≠0），文档写明"不支持 CFI"；**不得**用跳过/忽略 CFI 的静默降级实现。

**判据**：方案 1 的最小可行集（编号表 + `RA63` + `.eh_frame` FDE 编码）三项都在既有补丁面内，且各有实测支撑（背景 2/4/6）⇒ 优先做 1。若 `.eh_frame` 的 ABS48 编码在 `ld.lld`/dwarfdump 侧不可行，可**收窄**为「`.debug_frame` 支持 + `.eh_frame` 明确诊断」，但必须在完成区贴实测并说明为何不能声明 `.eh_frame`。

## 接口规范

**输入**：`llvm-mc --triple=dadao-unknown-elf` 的汇编；`clang --target=dadao-unknown-elf -c x.s`（cc1as 路径）；`llc -march=dadao`（若 `.ll` 侧触发）。

**输出（语义契约）**：

1. **编号表**：`MCRegisterInfo::getDwarfRegNum(r)` 对 4 个 bank 的**本体寄存器**（`rd/rb/rf/ra` 各 64，计数以 `.td` 现场派生）返回唯一值且 ∈[0,255]；寄存器别名（`RBSP`）与本体**同号**（`getDwarfRegNum(RBSP) == 65`，不计入唯一性冲突）；`getLLVMRegNum(n)` 为上述映射的逆（逐号自洽）。
2. **RA 列**：CIE 的 `return_address_register` = **255**（= `ra63`），`.eh_frame` 与 `.debug_frame` 两条路径一致；`llvm-dwarfdump --debug-frame` 不再出现 `-1`。
3. **CFI 指令面**：`.cfi_startproc/.cfi_endproc`、`.cfi_def_cfa`/`.cfi_def_cfa_offset`/`.cfi_def_cfa_register`、`.cfi_offset <reg>, <off>`（rb/rf/ra 各取代表）全部可汇编 rc=0；未登记/非法寄存器名 ⇒ **既有解析错误**（rc≠0，非 abort）。
4. **FDE 编码**：DADAO 的 `.eh_frame` FDE 地址字段用 `DW_EH_PE_absptr`（8 字节，`R_DADAO_ABS48`），不再用 4 字节 `pcrel|sdata4`；`.debug_frame` 沿用 `absptr`。
5. **不变量**：不改 ABI/寄存器分配；不改 `spec/`/`contracts/`；不带 `-g`/不带 CFI 的 `-O1 -c` 对象 `.text` 与改动前逐字节一致（反汇编 md5）。
6. **语义边界（必须在完成区写清）**：本任务只保证 CFI **结构合法、可解析**。DADAO 的返回地址在 RegRAS 硬件栈（`ra63[47:0]` + `[63:48]` 递归计数，`spec/SimRISC-00 §2.4`），**DWARF 展开语义未定义**；不宣称 unwinder 可正确回溯。

## 实现落点（建议；engineer 可按现场调整，须在完成区披露）

1. **编号表**：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAORegisterInfo.td.patch`：4 个 `foreach` 循环各加 `DwarfRegNum<[...]>`——`rd#i` → `DwarfRegNum<[i]>`、`rb#i` → `DwarfRegNum<[!add(i, 64)]>`、`rf#i` → `DwarfRegNum<[!add(i, 128)]>`、`ra#i` → `DwarfRegNum<[!add(i, 192)]>`；单独定义的 `rd0`（`let isConstant = true`）也要加 `DwarfRegNum<[0]>`；`RBSP : ..., DwarfRegAlias<rb1>` **保留**。
2. **RA 寄存器**：`.../MCTargetDesc/DADAOMCTargetDesc.cpp.patch`：`InitDADAOMCRegisterInfo(X, DADAO::RA63)`（原 `RBSP`），并写注释「RA = RegRAS 栈顶；`getRARegister()` 仅被 CIE 使用」。**改前**先复核 `getRARegister()` 的唯一消费者结论（背景 4）；若消费者变多，重新评估并披露。
3. **`.eh_frame` FDE 编码**：**新建**补丁 `components/llvm-project/patches/llvm/lib/MC/MCObjectFileInfo.cpp.patch` + `series` 增一行（按字典序插在 `llvm/lib/MC/MCParser/ELFAsmParser.cpp.patch` **之前**）：`initELFMCObjectFileInfo` 的 arch switch 增 `case Triple::dadao: FDECFIEncoding = dwarf::DW_EH_PE_absptr; break;`（注释：无 32 位 PC 相对数据重定位通道，用 8 字节 ABS48）。
4. 预计**不需要**：`llvm/lib/MC/MCDwarf.cpp`（通用文件，**禁**为过断言改它）、`DADAOAsmPrinter`/`DADAOFrameLowering`（当前 clang 不发射 CFI，见背景 7）。
5. 补丁按 `docs/Process-01` 生成：运行期组件检出内改源码 → 本地 commit → `make_patch.py` 重导出；**禁手工编辑补丁**。`components/llvm-project/changelog.md` 的 `## M14` 节追加一条（节内按日期升序；节已由 00x 任务建好则追加）。

## 测试设计

1. **MC lit（新）**：`tests/unit/llvm/lit/MC/DADAO/cfi-dwarf-regs.s`（沿用本目录 `@@` 注释风格）
   - `.cfi_startproc` + `swym 0` + `.cfi_endproc`（默认 `.eh_frame`）⇒ `-filetype=obj` rc=0，**不再 abort**，产物存在；
   - `%llvm_dwarfdump --debug-frame`（先捕获 `|| true` 再 FileCheck，写法参考本目录 `dwarf64-default.s`）：`Version: 1`、`Return address column: 255`、FDE 存在且 `pc=` 覆盖函数；
   - `.cfi_def_cfa_offset`、`.cfi_offset rb2, -8`、`.cfi_offset rf8, -8`、`.cfi_offset ra63, -8` 各一条 ⇒ rc=0；
   - 反例：`.cfi_offset nosuchreg, -8` ⇒ `%not` rc≠0（解析错误，非 abort）；
   - 一例 `-g`（DWARF64）+ `.cfi_sections .debug_frame` ⇒ rc=0 且 RA 列同为 255（防"只修 EH 一路"）。
2. **对象级**：`.eh_frame` 必须存在（默认路径，`%llvm_readobj -S` / `%llvm_objdump -h`）；`.debug_frame` 在 `-g` 或显式 `.cfi_sections .debug_frame` 时校验；`.eh_frame` 内 FDE 地址字段为 8 字节、重定位类型为 `R_DADAO_ABS48`（`-r` 为判据）。
3. **E2E（链接 + 运行）**：`tests/unit/llvm/e2e/cfi_e2e.s`（新）+ `tests/unit/llvm/e2e/lit/cfi_e2e.test`（新）
   - 汇编含 `.cfi_startproc/.cfi_endproc` + `.cfi_def_cfa_offset`，用既有 crt0 + 链接脚本链接 ⇒ `ld.lld` rc=0，链接产物 `%llvm_objdump -h` 含 `.eh_frame`；
   - 运行 ⇒ 退出码 0（CFI 指令不改变代码语义）；无 `DISCARD` 时孤段应被保留，若被丢弃则按「风险 3」处置。
4. **回归**：`tests/unit/llvm/lit/MC/DADAO/dwarf64-default.s` 仍绿；`make check-lit` 全绿（计数现场统计）。

## 范围（改哪些文件）

- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAORegisterInfo.td.patch`
- `components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCTargetDesc.cpp.patch`
- `components/llvm-project/patches/llvm/lib/MC/MCObjectFileInfo.cpp.patch`（**新建**）
- `components/llvm-project/series`（新增 1 行，保持字典序）
- `components/llvm-project/changelog.md`（`## M14` 节追加一条）
- `tests/unit/llvm/lit/MC/DADAO/cfi-dwarf-regs.s`（新）
- `tests/unit/llvm/e2e/cfi_e2e.s`（新）、`tests/unit/llvm/e2e/lit/cfi_e2e.test`（新）
- 本任务书（完成区/审阅记录）

**不改**：`spec/**`、`contracts/**`、`.tao/contracts/**`、`docs/Process-*`、`manifests/**`、`Makefile`、`tools/**`、`llvm/lib/MC/MCDwarf.cpp`、既有测试。

## 验收标准

1. **不崩溃**：`.cfi_startproc/.cfi_endproc` 配对输入在**默认路径**下 rc=0（贴命令 + rc + 产物存在性），stderr 无 `Assertion`/`PLEASE submit a bug report`；若最终选方案 2，则 rc≠0、诊断含 `CFI`（或 `unsupported`）且**无 core dump**，并贴证据说明为何不能正面支持。
2. **RA 编号**：`llvm-dwarfdump --debug-frame` 的 CIE `Return address column: 255`（≤255 且 != -1），`.eh_frame` 与 `.debug_frame` 一致。
3. **编号表自洽（黑盒可验，无需写 C++）**：对 `.td` 现场派生的本体寄存器清单（`rd/rb/rf/ra` 各 64），用「`.cfi_offset <reg>, -8` 逐寄存器一条 → `llvm-dwarfdump --debug-frame -v` 读回 `DW_CFA_offset_extended: reg<N>`」的方式现场统计：编号唯一 ∧ ∈[0,255] ∧ 与期望映射一致；别名 `RBSP` 与本体同号（65）且不参与唯一性冲突。计数写现场值，不写死（基线对照：当前同一路径打印 `reg4294967295`）。
4. **CFI 指令面**：`.cfi_def_cfa`/`.cfi_def_cfa_offset`/`.cfi_def_cfa_register`/`.cfi_offset`（rb/rf/ra 各一）全 rc=0；非法寄存器名 rc≠0 且非 abort。
5. **`.eh_frame` 可链接**：E2E 链接（既有 crt0 + 链接脚本）不因 `.eh_frame` 报错/丢段，`%llvm_objdump -h` 在链接产物里能看到 `.eh_frame`。
6. **关闭态不变**：不带 `-g`/不带 CFI 的汇编与 `-O1 -c` C 源，反汇编 md5 与改动前一致（基线钉派单时 commit + 现场 md5，不得取收尾时 `HEAD`）。
7. **门控**：`make check-lit` rc=0、`make check` rc=0（含 `check-patch-tree`（新补丁必须在 `series` 且字典序正确）、`check-component-changelog`）、`python3 tools/infra/check_install_tools.py --sha-tools clang,llc,llvm-mc` rc=0（安装根 == 构建树）。
8. **注入（≥2 路可达 FAIL + `cp`+md5 或临时树还原）**：
   - ① 基线工具链（**改动前**安装根）跑验收 1 的命令 ⇒ abort（rc=134 + 断言原文，证明门控能捕获缺口，免重建）；
   - ② lit 期望值注入：临时副本把 `Return address column: 255` 改成 `254` ⇒ FAIL（证明断言非恒真）；
   - ③（可选，需重建并申报耗时）临时树把 `RA63` 改回 `RBSP` ⇒ `255` 断言 FAIL；
   - ④（可选，需重建并申报耗时）临时树把 FDE 编码改回默认 `pcrel|sdata4` ⇒ `.eh_frame` 汇编 rc≠0（4 字节字段无法承载 ABS48）⇒ 断言 FAIL。
   还原一律 `cp`+md5 或临时树；**禁** `git checkout/restore/stash`/`git show <commit>:<path>`。
9. **成本**：完成区记录 `build-mc` 增量耗时（改了 `.td` ⇒ TableGen 全量重生成，取上限）、`install-host` 耗时、`series` 行数变化（现场统计）。
10. **证据**：一键证据脚本落运行期证据目录（含注入）；完成区 ≤30 行、无运行期具体路径；结论与真实输出/退出码逐条对齐（禁 `cmd | tee` 吞码）。

## 成本与申报

- 改 `.td` ⇒ TableGen 全量重生成 + `LLVMDADAOCodeGen`/`LLVMDADAODesc` 重编 + 重链 `llc`/`clang`/`llvm-mc`，预计 **10–30 min**（取上限）。
- `install-host` 整体重拷安装集，预计 **10–20 min**。
- 两者启动前**申报预计耗时**，用可通知的后台运行并落日志 + `EXIT` 标记。

## 风险与处置

1. **编号撞号/别名**：`RBSP` 是 `rb1` 的别名（同 HW 编码），只能靠 `DwarfRegAlias` 继承编号；若 TableGen 对 `DwarfRegNum` + `DwarfRegAlias` 并存报重复，保留别名、把 `DwarfRegNum` 只挂在真实 `def` 上，并在完成区说明。
2. **`RA63` 语义**：`ra63[63:48]` 是递归计数、`[47:0]` 才是返回地址（`spec/SimRISC-00 §2.4`）；CIE 只记"哪个寄存器持有返回地址"，本任务不表达这个复合结构 ⇒ 语义边界写进完成区（接口规范 6），**不要**顺手改 RA bank 语义。
3. **`.eh_frame` 非标准编码**：`DW_EH_PE_absptr` 让 `.eh_frame` 变成绝对地址（静态链接/裸机足够；动态/共享库的 load-bias 语义未覆盖，若需要记「待裁定」）。若 `ld.lld` 对 `.eh_frame` 里的 `R_DADAO_ABS48` 报错或丢段 ⇒ 按「方案与判据」的**收窄**处置（`.debug_frame` 支持 + `.eh_frame` 明确诊断，不静默产出非法 CFI），并在完成区贴实测。
4. **`.debug_frame` 的 4 字节字段**：不带 `-g`（DWARF32 默认）且显式 `.cfi_sections .debug_frame` 时仍会报 `relocatable operand in a 1/2/4-byte data field`——这是 **DWARF64 默认口径**问题（cc1as 路径已在既有补丁里默认 `-gdwarf64`），**不要**在本任务扩大范围去改 llvm-mc 的 DWARF 格式默认；记录在完成区/遗留问题。
5. **改通用文件 `MCObjectFileInfo.cpp`**：只加 `case Triple::dadao`，不得动其它 arch 分支；`check-patch-tree` 会校验新补丁与 `series` 一一对应，补丁只能用 `make_patch.py` 重导出。
6. **dwarfdump 对 `R_DADAO_ABS48` 的告警**：`.o` 上 dwarfdump 可能打印"failed to compute relocation"（既有已知，见 `dwarf64-default.s` 注释）⇒ 断言用"捕获后 FileCheck"，不要用 dwarfdump 的退出码作判据；链接后产物才是可靠判据。
7. **`llvm-dwarfdump` 对新编号的解读**：`ra` bank 编号 192–255 没有外部约定，dwarfdump 只按编号显示 → 断言只钉编号数值，不钉寄存器名。

## 交接

- **CFI 的发射侧**：让 `clang`/`llc` 真的**发射** `.cfi_*`（`-fasynchronous-unwind-tables`/EH 开关、`DADAOAsmPrinter` 的 CFI handler）不在本任务（现状不发射，见背景 7）；若内核需要 unwind 表，另立任务。
- **深一层语义**：RegRAS 的 DWARF 展开语义（硬件栈 + 递归计数）若要冻结成规范/ABI，须用户授权改 `spec/`，本任务只做工具链侧合法化。
- **台账**：`.tao/knowledge/milestones-m14.md` 的任务行由**主会话**派单时补（本任务不改台账）；未补时 `check-milestones-fresh` 的 A2 必红，归主会话处置，不是本任务产物缺陷。

## 参考来源（内容溯源，非执行必需）

- `.cache/refs/DADAO/TCH-llvm/.../DadaoRegisterInfo.td`：`rd#i → i`、`rb#i → 64+i`、`ra#i → 128+i`（**无 rf 段**）——本项目的差异：v5 的 RF bank 已实现，必须给 rf 留段，故 ra 后移到 192–255。
- `.cache/refs/DADAO-0628/components/llvm/patches/0013-dadao-globals-lowering.patch`：四个 bank 一律 `DwarfRegNum<[i]>`（**rd/rb/rf/ra 全部撞号**）——不可照搬；本任务按"bank 内序号 + bank 基址"唯一化。
- `.cache/refs/DADAO-0628/code-agent/tasks/DL-054a-codegen-asmprinter.md`：记录了同一断言与「配 `DwarfRegNum` 映射 / 关掉 CFI 发射」两条路——本任务选前者，并把"只关发射"排除为不合格（会静默丢信息）；仅作对照，不复制其补丁/命令。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/m14-llvm-004/`。
2. 不提交 git（提交权归 architect）；**例外**：`docs/Process-01` 要求在组件运行期检出内做本地 commit 才能导出补丁（E1）——那只属于该组件检出、**不是**本仓库提交，仍须在完成区列明。
3. 完成区与真实输出逐条对齐；计数写现场值；长输出留运行期日志目录。
4. 只动「范围」列出的文件；越界须披露。
5. 失败保留现场并继续推进；只有需要用户语义裁定（改 ABI/契约/`spec/`、冻结 DWARF 编号为规范）才写「待裁定」返回主会话。
6. 命令作用域 = workdir（仓库根），用相对路径；禁出界 `cd`。
7. 注入还原一律「注入→FAIL→还原→回绿」；真实树用 `cp`+md5，优先临时树；**禁** `git checkout/restore/stash`/`git show <commit>:<path>`。
8. 补丁**不得手工编辑**（`docs/Process-01`）；工具安装必须走 `install-host`（禁手工 `cp` 安装根）。
9. 断言不得以"压掉断言/跳过 CFI"为通过条件；`llvm/lib/MC/MCDwarf.cpp` 属通用文件，**禁改**。

## 用户授权

- 用户 2026-11-13（经主会话转达，已记入 `discussing.md`）：「**CFI 崩溃（`llvm-mc` 断言 `RAReg <= 255`）：与"64 位 DWARF"无关，是 DADAO 缺 DWARF 寄存器编号、return-address 寄存器编号 >255；先立任务（正面支持编号表，或至少改报错不 abort）。**」——授权在 DADAO 侧补齐编号表/CFI 合法化。
- 本任务不改 `spec/`/`contracts/`；若要冻结 DWARF 编号表为规范级/ABI 级约定，先停并登记「待裁定」。

## 待裁定

（空。现场命中才写：① 编号表需冻结进 `spec/`（调试 ABI 级约定）；② `.eh_frame` 的 ABS48 编码要求动态/共享库场景另行设计；③ RegRAS 的 DWARF 展开语义需定义；④ 方案 1 被证伪、需转方案 2 并在文档声明"不支持 CFI"。）

## 完成区

**测试结果**：`make check-lit` rc=0（168/168 现场统计，含新增 2 例）；`make check` rc=2（**唯一红点是 `check-patch-tree`：llvm-project 99 补丁 0 问题**；该次全仓 14 项问题全在 qemu/gem5/chipyard/linux 且随他任务在建波动，同项二次跑为 20 项；`make` 因此在其后中止）；`make -k check` rc=2（5 项红逐条归因：`check-patch-tree` 全仓问题均落在 qemu/gem5/chipyard/linux；`check-knowledge-refs` 1 条在 m16-gem5-002 任务书；`check-musl-freshness` 2 条建议 `make build-musl-shared`；`check-milestones-fresh` R1 命中 m13-qemu-010 与**本 worktree 基线早于派单提交**导致的 m14-llvm-004（主工作树该行已在「进行中」）；`check-temp-dirs` 命中非本任务的旧临时目录；均非本任务产物）（全项归因见下）；`make check-gem5-decode` rc=0（264/264+388/388，与本任务无关的旁证）；`check_install_tools.py --sha-tools clang,llc,llvm-mc` rc=0；`check_component_changelog` rc=0；`check_patch_tree --source-state`：llvm-project OK（HEAD=12ed4deeecea，count=1，clean=True），FAIL 仅 gem5（dirty）/linux（expected=0 实 1）。一键证据脚本（落运行期证据目录 `.work/evidence/<任务ID>/run.sh` 形）44 检查 0 失败（rc=0）；`--inject` 15 检查 0 失败（rc=0）。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAORegisterInfo.td.patch`（改）、`.../MCTargetDesc/DADAOMCTargetDesc.cpp.patch`（改）、`.../llvm/lib/MC/MCObjectFileInfo.cpp.patch`（新）、`components/llvm-project/series`（+1 行，98→99）、`components/llvm-project/changelog.md`（M14 追加 1 条）、`tests/unit/llvm/lit/MC/DADAO/cfi-dwarf-regs.s`（新）、`tests/unit/llvm/e2e/cfi_e2e.s`（新）、`tests/unit/llvm/e2e/lit/cfi_e2e.test`（新）、本任务书。组件检出内本地 commit `12ed4deee`（仅用于导出补丁，Process-01 E1；未推送）。
**验收结果**：
- ①不崩溃：配对 `.cfi_startproc/.cfi_endproc` 默认路径 rc=0、产物存在、stderr 无 `Assertion`/`PLEASE submit`；基线工具同命令 rc=134 + `RAReg <= 255` 原文。
- ②RA 编号：`.eh_frame` CIE `Version: 1` + `Return address column: 255`；`.debug_frame`（`-g`，DWARF64 `Version: 4`）亦 255；原始 `.eh_frame` 字节解码 RA 字段=255、FDE 地址域 8+8=16 字节、FDE 编码字节 0x00(absptr)、`.rela.eh_frame` 为 `R_DADAO_ABS48`。
- ③编号表：`.td` 现场派生 256 个本体寄存器（四 bank 各 64，现场计数），逐寄存器「名字 vs 期望号」目标文件 md5 全等（0 处不符）、号唯一且 ∈[0,255]；生成表两 flavour 均 RBSP/rb1→65，逆表 256 号一一对应。
- ④指令面：`.cfi_def_cfa`/`_offset`/`_register`、`.cfi_offset rb2|rf8|ra63` rc=0；`nosuchreg` rc=1（既有解析错误，非 abort）。
- ⑤可链接：crt0+Tiny 脚本 `ld.lld` rc=0，链接产物含 `.eh_frame`，qemu 退出码 0，ELF 内 FDE `pc=ffffff010168...ffffff010170` 已解析为绝对区间。
- ⑥关闭态不变：无 CFI 汇编与 `-O1 -c` C 源反汇编 md5 与派单前一致（`9b868621…` / `d2661a62…`）；安装根 == 构建树（clang/llc/llvm-mc 三件 md5 双侧相同）。
- ⑦成本：`build-mc` 增量 ≈4 min（TableGen 全量重生成）；`install-host` 502 s；`series` 98→99 行。
**新发现/坑**：① `.cfi_*` 的寄存器操作数走 **EH flavour**（`AsmParser::parseRegisterOrRegisterNumber` 用 `getDwarfRegNum(…, isEH=true)`），CIE 的 RA 列按段取 `IsEH` ⇒ 必须用单值 `DwarfRegNum` 让两 flavour 同号（双值写法会让 EH 侧落 -1、断言照旧）。② `ra63=255` 是**恰好上限**（`.eh_frame` CIE 恒 v1、RA 列只一字节），再扩 bank 即破。③ ABI 别名在汇编器不可见（`DADAOAsmParser::matchRegisterName` 只认 `rd/rb/rf/ra`+序号）⇒ `.cfi_offset rbsp` 不能当验证路径，别名改用 `.td` 的 `DwarfRegAlias<rb1>` + 生成表核对。④ 有编号表后 `llvm-dwarfdump` 按**寄存器名**打印 CFI 操作数（`rb1/rf8/ra63`，非 `reg<N>`），期望值须兼容两形态。⑤ `-g -O1` 对象 `dwarfdump --debug-info` 段错误（`DWARFListTableHeader::getOffsetEntry`，loclist 表在 ABS48 未解析时畸形）；旧 dwarfdump 同输入同 139，非本任务引入。
**遗留问题**：① 全仓 `check-patch-tree` / `--source-state` 红在 qemu/gem5/chipyard/linux（他任务在建，未代改）；`check-milestones-fresh` 的 R1 在本 worktree 命中 m14-llvm-004（本分支基线早于派单提交 c3e1b6d9，主工作树该行已在「进行中」）与其它任务行，归主会话/基线处置。② `.o` 上 `R_DADAO_ABS48` 的 dwarfdump 缺口（含 `-g` loclist 段错误）建议另立任务。③ `.eh_frame` 用绝对地址：静态/裸机够用，动态/共享库 load-bias 未覆盖。④ RegRAS 的 DWARF 展开语义（硬件栈+递归计数）未定义，本任务只保证 CFI 结构合法可解析。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-14，engineer 自主逐行审查）

审查范围：3 份组件补丁（`.td` 编号表 / `MCTargetDesc` 的 RA / `MCObjectFileInfo` 的 FDE 编码）+ 3 个测试文件 + `series`/changelog。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 四个 bank 若按「bank 内序号」编号会撞号（rd8/rb8/rf8/ra8 同为 8） | ✅已修（设计即此） | 每 bank 独占 64 号段（基址 0/64/128/192） | 生成表 256 号唯一；dwarfdump 读回 rb2/rf8/ra63 |
| F2 `.eh_frame` CIE 恒 v1 ⇒ RA 列只一字节，RA 号必须 ≤255 | ✅已修 | RA 由 `RBSP`(65) 改 `ra63`(255) | CIE `Return address column: 255`；原始字节 RA 字段=255 |
| F3 `DwarfRegNum<[N]>` 是否同时喂 EH flavour（CFI 指令走 isEH=true） | ✅已修（实证确认，未改代码） | 注释写明单值形式两 flavour 同号 | 两个 flavour 生成表均 256 项 + RBSP/rb1→65 |
| F4 `.eh_frame` 默认 `pcrel|sdata4` 在 DADAO 无重定位通道 | ✅已修 | 新增 `case Triple::dadao` → `DW_EH_PE_absptr` | `.rela.eh_frame`=`R_DADAO_ABS48`；raw 解码地址域 16 字节；链接后 FDE `pc=` 为绝对区间 |
| F5 断言若写死 dwarfdump 打印形态（名字 vs `reg<N>`）会脆 | ✅已修 | CFA 断言改 `{{(rb2|reg66)}}` 交替式 | lit 复跑 PASS |
| F6 我最初手写的测试夹具用了不存在的助记符（`ld.ri`/`cmp.rrr`） | ✅已修 | 改用既有语料中的合法指令（`add.si`/`swym`/`br.n`） | 全部 rc=0 |
| F7 `rbsp` 别名无法用 `.cfi_offset rbsp` 验（汇编器不认别名，既有行为） | ✅已修（改验证路径） | 别名改由「`.td` 有 `DwarfRegAlias<rb1>` + 生成表两 flavour RBSP→65」核对 | 证据脚本 alias 两项 PASS，并披露该边界 |
| F8 `-g -O1` 对象 `dwarfdump --debug-info` 段错误 | ⏸延后（非本任务引入，另立任务） | 未改 | 旧 dwarfdump 同输入同 139；栈在 `DWARFListTableHeader::getOffsetEntry`（ABS48 未解析→loclist 表畸形） |
| F9 `--inject` 模式曾因缺 `cfi-min.o` 假红 | ✅已修 | 第 10 节自行按需生成夹具 | `--inject` 复跑 15/0 rc=0 |
| F10 证据脚本两处 `objdump | tail` 会吞 objdump 退出码 | ✅已修 | 拆成「落盘 → 校验 rc → tail」 | 新增 2 条 `*-objdump-rc` PASS |

判决：全部 finding 已处置（F8 属既有缺口、已登记遗留），任务产物与验收证据一致。

### 第 1 轮 reviewer 验收（2026-11-14，reviewer 独立重跑）

**审阅对象**：3 份组件补丁 + `series`/`changelog` + 3 个新测试 + `run.sh`（逐条审 FAIL 路径，无 `tee` 吞码、计数现场派生）+ 任务书完成区。

**重跑（任务树内，均本人执行）**
- `make _locked-check-lit` rc=0、`make check-lit` rc=0 ⇒ **168/168 现场统计**（含新 `cfi-dwarf-regs.s`、`cfi_e2e.test`）。注：本人前两次 `make check-lit` 误在主工作树执行得 166（主树无本任务新测试），已在任务树重跑纠正，主树 `git status` 仍干净。
- 证据脚本：`run.sh` rc=0 **44 检查 0 失败**；`run.sh --inject` rc=0 **15 检查 0 失败**（与完成区逐字一致）。
- 验收1/2 独立验证：当前 `llvm-mc` 配对 `.cfi_startproc/.cfi_endproc` rc=0、stderr 无 `Assertion`；`llvm-dwarfdump --debug-frame -v` ⇒ `Version: 1`、`Return address column: 255`；**基线** `baseline-llvm-mc`（md5 3ffcfd0058…）同输入 **rc=134 + `RAReg <= 255` 断言原文**。
- 门控：`check_install_tools --sha-tools clang,llc,llvm-mc` rc=0（108 PASS，sha256 双侧相等）；`check_patch_tree` rc=1 但 **llvm-project 99 补丁 0 问题**（红全在 gem5/chipyard/linux 他任务）；`--source-state` **llvm OK**（HEAD=12ed4deeecea clean=True；FAIL 仅 qemu/linux）；`check_component_changelog` rc=0。
- `make check` rc=2（首红 check-patch-tree）、`make -k check` rc=2：红=patch-tree / knowledge-refs（m16-gem5-002 任务书）/ musl-freshness（2，建议 build-musl-shared）/ milestones-fresh（R1=m13-testcases-020，**m14-llvm-004 已不在违规内**；temp-dirs 本轮 PASS）——与完成区归因一致项均复核，差异属台账/临时目录状态漂移，逐项均非本任务产物。

**独立注入（本人自设计，`cp`+md5，未用 git checkout/restore）**
- ① 改**真实** lit 文件 `Return address column: 255→254`（md5 4bed44b2→88e70aad）⇒ `llvm-lit` **rc=1 FAIL**、`run.sh` **rc=1 `FAIL [inject-lit-restored-green]`**；`cp` 还原 md5=4bed44b2 相等 ⇒ lit rc=0、`run.sh` 44/0 rc=0。
- ② 改 `MCObjectFileInfo.cpp.patch`（`absptr→pcrel`，md5 d6cf2bed→2a25ee3f）⇒ `check_patch_tree` 出现 **llvm 断言⑨+⑥**（23→25 项）；还原 md5=d6cf2bed 相等 ⇒ llvm 段回 0 问题。

**约束核验**：`git show --stat f3261b9d` = 9 文件全在「范围」，未碰 spec/contracts/Makefile/tools/`MCDwarf.cpp`；补丁与 E1 commit 12ed4deee 机械一致（⑥/⑨ 绿，未手工编辑痕迹）；RA=ra63 与 spec「ra63 恒为 RegRAS 栈顶」一致，`getRARegister()` 全量 grep 仅 MCDwarf CIE 消费（DADAO/通用 CodeGen 无其它调用）；关闭态基线核真：**基线 llvm-mc 现场产 plain 对象反汇编 md5=9b868621… == run.sh 常数**，归档 `plain-base-c.dis` 尾部 md5=d2661a62… == C 常数（01:07 派单时捕获）；完成区 16 行 ≤30；审阅前后 `git status -uall` 快照均空、目标文件 md5 不变（对账 diff 空）。

**遗留/未决判定**：① `.o` ABS48 `--debug-info` 段错误：**本人复现 rc=139**（含 `.debug_loclists` 的 `-g -O1` 对象），触发为 `.rela.debug_info/addr` 的 ABS48 地址重定位不可解（`dwarf64-default.s` 记为既有），该对象**无任何 frame 段**、任务三改不触及 ⇒ **判既有缺口、接受，建议另立任务**（注：完成区「旧 dwarfdump 同 139」无留档原输出、系统内旧二进制已不存在，以本人复现+机制分析支撑结论）。② `.eh_frame` absptr 动态/共享库 load-bias 未覆盖 ⇒ 静态/裸机范围外且已披露，**接受为遗留**。非阻塞发现（交 architect 收口酌处）：`DADAORegisterInfo.cpp:38` CodeGen 侧仍 `DADAOGenRegisterInfo(DADAO::RBSP /* RA=SP */)` 与 MC 侧不一致（现无消费者）；`run.sh` 内 per-bank 计数/越界 FAIL 仅打印未进退出码（映射/唯一性/生成表均已门控）。

**判决：Accepted** —— 验收 1–10 在本人重跑下全部通过，无约束违反；遗留①②可接受。
