# LLVM-055t: 全局数据 lower（`.data`/`.rodata`）+ `ABS48`/RELA fixup

**模块**：llvm
**项目里程碑**：M4
**依赖**：`LLVM-050t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `LLVM-050t` 的 `ABS48`/RELA fixup 与 `getRelocType` 设施；`contract-elf.md §1/§2/§5`（段对齐、`SHT_RELA`、`ABS48` 公式/3 片）。
  - M3 CodeGen（`DADAOTargetMachine` 已用 `TargetLoweringObjectFileELF`；`DADAOAsmPrinter`/`DADAOMCInstLower`）；`ADR-0018`（C9 DataLayout `E-m:e-p:64:64-i64:64-i128:128-n32:64-S128`；C2 指针 i64 通吃）。
  - `DADAO-0628 DL-061c`（globals 经标准 `ld.lld` + 链接脚本；`ML-003e` Gap 2 数据段函数指针）+ `ML-030a`（大常量折入 relocation 越界）——**只读对照**。
- **输出**（组件源码改在 `.work/source/llvm-project`；导出补丁）：
  - `llc` 对含**全局变量/静态数据**的模块发射正确的 `.data`/`.rodata`/`.bss` 段（对齐依 `contract-elf §5`：`.rodata`/`.data`/`.bss` 8B；大端）。
  - `GlobalAddress` 的地址材料化：跨 section/未定义符号 → `set.zw`/`or.w` 序列 + **`R_DADAO_ABS48`**（固定 3 片，`ADR-0019` D4/D5）；同 section 可解析者就地解析（不虚假发 reloc）。
  - 数据段中的符号引用（如函数指针初始化 `.quad sym`）按需发对应数据 reloc；**若需 `ADR-0019` 4 类之外的数据 reloc 类型，须停下报告**（不得自行扩类型集）。
- **约束**：
  - **reloc/fixup 坑预防（M4 硬约束）**：① 尊重 `IsResolved`；② same-section 快速路径不可靠则退回真重定位（`ML-003e`：判断「是否需重定位」须比较「目标符号 section vs fixup section」，**不是** `isUndefined()`）；③ `rb0` 禁作基址/零；④ 跳转表目标标签显式发射；⑤ **大常量/大地址先材料化，不得折入受限立即数/relocation 字段**（`ML-030a`：`GlobalAddress + 大常量偏移` 不得塞进 `imms18`/`imms12`，须寄存器算术）。
  - **不做**：完整调用约定、varargs/聚合/sret、FP/RF、clang 前端（均 M5+）。
  - **补丁纪律（`spec/Process-01`）**；`commit --amend` 收敛 base+1 → `make_patch.py` → `check-patch-tree`；不手改补丁。
  - 构建/串行/临时目录/留证纪律同 `LLVM-050t`；`ninja -j8`；失败即停。
  - 临时目录 `/tmp/opencode/LLVM-055t/`；**不提交 git**。

## 验收标准

1. 构建 EXIT=0。
2. **段发射**：对一个含 `@g = global i64 42` / `@arr = global [4 x i64]` / 只读常量的 `.ll`，`llc -march=dadao -filetype=obj` EXIT=0；`llvm-readobj -h --sections` 显示 `.data`/`.rodata` 节存在、8B 对齐、内容按大端（给真实输出）。
3. **地址材料化 + RELA**：对跨 section/外部符号的 `GlobalAddress` 引用，`llvm-readobj -r` 显示 **`R_DADAO_ABS48`**，`--expand-relocs` 显示 `Addend`；反汇编显示 `set.zw`/`or.w` 序列（≤3 片）；逐例独立核对地址分片（wyde-position）。
4. **同段就地解析**：同 section（如 `.text` 内函数地址）不虚假发 reloc（`llvm-readobj -r` 无多余项）。
5. **数据段符号引用**：`.quad sym`（函数指针/全局地址）非零且带对应 reloc（`ML-003e` Gap 2）；若该类型不在 `ADR-0019` 集内，**停并报告**。
6. **不回归**：`make test-codegen`（M3 15/15）EXIT=0；`make check-lit`/`make check` EXIT=0；`check-patch-tree` OK。
7. 一键证据脚本 `.work/evidence/LLVM-055t/run.sh`（含 `--inject`：把 `ABS48` 片数改为 1 / 让跨段符号不发 reloc → 期望 FAIL → 还原+**重建** → 回绿）；完成区贴真实输出。

## 完成区

**测试结果**：通过 31/31（一键证据 `.work/evidence/LLVM-055t/run.sh` 正常模式 31 项全 PASS，EXIT=0）+ 反例注入 12/12（`--inject` 两轮：ABS48 片数改 1 / 让 ABS48 不发 reloc → FAIL → 还原+**重建** → 回绿，EXIT=0）。`make check` EXIT=0；`make test-codegen` 15/15；`make check-lit` 50/50；`make check-patch-tree` 85 patches OK；`make check-source-state` llvm-project clean+count=1。失败原因：无。

**修改文件**：
- 组件源码（`.work/source/llvm-project`，已 `commit --amend` 收敛为 base+1：`6dfe1677a..c9b87ba1ad11`，worktree clean）：
  - `llvm/lib/Target/DADAO/DADAOCodeGen.td`（+`GLOBAL_ADDR` 伪指令：`outs GPRB:$dst, ins unknown:$sym`）
  - `llvm/lib/Target/DADAO/DADAOISelDAGToDAG.cpp`（+`ISD::GlobalAddress` → `TargetGlobalAddress`（偏移作 GA addend）→ `GLOBAL_ADDR`；`isPointerBankValue` 计入 `ISD::GlobalAddress`）
  - `llvm/lib/Target/DADAO/DADAOInstrInfo.cpp`（`expandPostRAPseudo` +`GLOBAL_ADDR`：固定 3 片 `set.zw_rb wp0` + `or.w_rb wp1` + `or.w_rb wp2`）
  - `llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCInstPrinter.cpp`（`FK_rwii` 分支支持符号表达式操作数，修 `-filetype=asm` 对 expr 调 `getImm()` 的断言崩溃）
- 补丁集：`components/llvm-project/series`（仍 53）与 `components/llvm-project/patches/**`（`make_patch.py` 导出，4 份更新：`DADAOCodeGen.td` / `DADAOISelDAGToDAG.cpp` / `DADAOInstrInfo.cpp` / `MCTargetDesc/DADAOMCInstPrinter.cpp`）；**未手改**。
- 台账：`components/llvm-project/changelog.md`（+LLVM-055t 一条）。
- 证据脚本：`.work/evidence/LLVM-055t/run.sh`（新增）；日志 `.work/log/llvm/LLVM-055t-*.log`。
- 本任务书（完成区/自审/状态）。

**验收结果**（真实输出，`cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，无 `tee`）：

1. **构建 EXIT=0**（`.work/log/llvm/LLVM-055t-build.log` / `-build2.log`）：`ninja -j8 -C .work/build/llvm llc llvm-mc llvm-objdump llvm-readobj` → `EXIT=0`。
2. **段发射**（`llvm-readobj --sections` / `llvm-objdump -s`，证据 `section-data`…`be-rodata`）：`@g=global i64 42`/`@arr=[4 x i64]`/`@ro=constant i64 7`/`@bssv=global i64 0` → `.data`（SHT_PROGBITS，`AddressAlignment: 16`）、`.rodata`（`Alignment: 8`）、`.bss`（SHT_NOBITS，`Alignment: 8`）；大端字节 `.data` 首 8 字节 = `000000000000002a`（42）、`.rodata` = `0000000000000007`（7）。
3. **地址材料化 + RELA**（证据 `abs48-count`/`rel26-count`/`slice-wp`/`instr-addend`）：跨 section/外部 `GlobalAddress` 反汇编为
   ```
   set.zw rb8, wp0, arr
   or.w   rb8, wp1, arr
   or.w   rb8, wp2, arr
   ```
   `llvm-readobj -r --expand-relocs` → 每个 GA **3 片** `R_DADAO_ABS48`（`.rela.text`/SHT_RELA，无 SHT_REL；`addr.ll` 共 9 条 = 3 处 × 3 片，另 1 条 `R_DADAO_REL26`=未定义 `extfn` 调用）；`--expand-relocs` 显示 `Addend`。片位手核：`.text` 字节 `4e 20 00 00 / 4a 21 00 00 / 4a 22 00 00` → `hb[5:4]` = wp0/wp1/wp2（`contract-elf §2.3`）。**非零 Addend**：`internal` 全局的 GEP 常量偏移折入 GA → `set.zw rb31, wp0, iarr+24` + 3×`Addend: 0x18`（24，恰一次，无双重偏移）。
4. **同段就地解析**（证据 `same-section-no-reloc`）：`.text` 内 `call_same` 调同段 `sibling` → 反汇编 `call [rb0, 8]`，**无** reloc 注解（pc-rel 同段就地解析，判据「目标符号 section vs fixup section」，非 `isUndefined()`）；`call_ext`（未定义）→ 1×`R_DADAO_REL26`。
   - 对照：同段**绝对**地址（`.text` 内取 `.text` 函数 `@f` 地址，`sameabs.ll`）→ 仍发 3×`R_DADAO_ABS48`（绝对地址 section base link 期才知；`ADR-0019 D4/D7`「ABS48 永不就地解析」，**非**虚假 reloc）。
5. **数据段符号引用**（证据 `rela-data-section`/`data-fp-reloc`/`data-addend`/`rela-rodata-section`）：`.quad @sibling`（函数指针）→ `.rela.data`/`.rela.rodata` 各 `R_DADAO_ABS48`→`sibling`；`.quad @arr+16` → `Addend: 0x10`。类型 = `R_DADAO_ABS48`，**在 `ADR-0019` 4 类集内，未扩类型**（无需停报）。**注**：RELA 语义下 `.o` 内该 8 字节字段为 0、由 reloc 承载符号（link 后填非零绝对地址，链接归 `LLVM-056t`）；`ML-003e Gap 2` 的「静默清零」缺陷指**无 reloc** 的静默 0 —— 已消除。
   - 探针 `-verify-machineinstrs`（`g.ll`/`var.ll`/`opt.ll` `-O0`/`-O2`）EXIT=0；`-O2` 下 GEP 偏移折入 `ld.o [rb8, 8/16/24]`、GA 只物化一次（CSE）。
6. **不回归**：`make test-codegen` → `Results: 15/15 passed, 0 failed` EXIT=0（`.work/log/llvm/LLVM-055t-test-codegen.log`）；`make check-lit` → `Passed: 50 (100.00%)` EXIT=0；`make check` → `repository checks: PASS` EXIT=0（`.work/log/llvm/LLVM-055t-make-check.log`）；`make check-patch-tree` → `85 patches OK` EXIT=0；`make check-source-state` → `llvm-project: OK HEAD=c9b87ba1ad11 count=1 clean=True`。
7. **一键证据**：`.work/evidence/LLVM-055t/run.sh` → `RESULT: PASS (0 failures)` EXIT=0（31 项）；`run.sh --inject` → 两轮（① `GLOBAL_ADDR` 只发 1 片 → ABS48 计数 3≠9 → `break-slices-FAIL`；② `applyFixup` 对未解析 ABS48 直接 return → 计数 0≠9 → `no-abs48-reloc-FAIL`），`git checkout` 还原 + `ninja` 重建 → 计数回 9 → `restore-green`，`RESULT: PASS` EXIT=0（12 项）。

**新发现/坑**：
- **`llc -filetype=asm` 的 `FK_rwii` 打印对符号表达式操作数会断言**：`DADAOMCInstPrinter::printNewSyntax` 的 `FK_rwii` 分支无条件 `getImm()`；`GlobalAddress` 物化后 rwii 的 `immu16` 是符号 expr → `MCOperand::getImm() assertion` 崩溃（`-filetype=obj` 不经 printer 故不暴露）。已按 `FK_rrii`/`FK_riii` 同构改为 `isImm()/isExpr()` 分支（expr 走 `MAI.printExpr`）。**教训**：新增“可重定位立即数”codegen 时，printer 与 emitter 都要并行支持 expr。
- **ELF（非 COFF/MachO）下 `isOffsetFoldingLegal` 恒 false**：`TargetMachine::shouldAssumeDSOLocal` 对 ELF 默认 `return false`（除非 `GV->isDSOLocal()`），故**外部**全局的 GEP 常量偏移**不会**折入 GA（由 `add.o`+`CONST_WYDE` 单独物化，正确）；**`internal`/`local`** 全局因 `isDSOLocal()==true` 才会折入 GA addend。验证 GA addend 路径须用 `internal` 全局。
- **`GLOBAL_ADDR` 用 `unknown` 操作数承载 `MO_GlobalAddress`，`-verify-machineinstrs` 干净**；`expandPostRAPseudo` 里 `addGlobalAddress(Sym.getGlobal(), Sym.getOffset(), ...)` 只应用偏移一次（经 `LowerSymbolOperand` 的 `MO.getOffset()`），无双计。
- **ABS48 与 PC 相对的分工**：ABS48（绝对，含数据 8B 字段）恒发 reloc、永不就地解析（同段亦然，section base link 期才知）；PC 相对（call/jump/br）才做同段就地解析。二者判据不可混用（`ML-003e`：禁 `isUndefined()`）。
- **`.data` 里 `[4 x i64]` 段对齐为 16**（非 8）：generic ELF TLOF 取全局/段首选对齐，≥8 满足 `contract-elf §5`。

**遗留问题**：
- **`.quad sym` 的“非零”为 link-time 属性**：RELA 下 `.o` 字段占位 0、符号由 reloc 承载（本任务已保证 reloc 存在、非静默清零）；真正的非零绝对地址在 `LD` 写回后可见 —— 归 `LLVM-056t`（DADAO LLD）。属**能力缺口**（非错值）。
- **未加 `.ll` codegen lit 向量**：`tests/llvm/lit/CodeGen/DADAO/` 为占位 suite、未接入 `make check-lit`；接线需改 `lit.cfg.py` + `Makefile`（超本任务书范围）。本任务以一键证据脚本 `run.sh`（31 项，含反例注入）作为门控。属**范围决策**（可另立任务补 L2 向量）。
- `set.ow`/`FK_Data_1/2/4` 的既有缺口（`LLVM-050t`/`052t` 遗留）与本任务无关，未触及。
- 其余：无；无未修 finding。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：对改动源码逐行审查（`GLOBAL_ADDR` 伪指令定义、`DADAOISelDAGToDAG::Select` 的 `ISD::GlobalAddress` 分支与 `isPointerBankValue`、`DADAOInstrInfo::expandPostRAPseudo` 的 `GLOBAL_ADDR` 分支、`DADAOMCInstPrinter` 的 `FK_rwii` 分支）+ 证据脚本逐条核 FAIL 路径与自注入。
**判决**：**通过**（无未修 finding；均已在下方表格处置）。验收 1–7 均有真实输出支撑 → 状态置 `待验收`。

**逐行审查要点**：
- `GLOBAL_ADDR`：`outs GPRB:$dst`（地址须落指针 bank，C1/C2）+ `ins unknown:$sym`（承载 `TargetGlobalAddress` SDNode → `MO_GlobalAddress`）。`-verify-machineinstrs` 干净。
- `Select` 的 `ISD::GlobalAddress`：把 `GA->getGlobal()` + `GA->getOffset()` 传 `getTargetGlobalAddress`（偏移作 `r_addend`），非间接/非 `ExternalSymbol`；非法情形（如 `ExternalSymbol` 取址）仍走 `SelectCode` 失败路径（显式 `Cannot select`，不静默）。
- `isPointerBankValue` 增 `ISD::GlobalAddress`：使 `gep`（`add(GA, idx)`）走 `add.o rb,rb,rd`（GPRB），链式 GEP 亦正确；与既有 `FrameIndex`/`FRAME_ADDR`/`add_o_bbd` 判定一致。
- `expandPostRAPseudo` 的 `GLOBAL_ADDR`：固定 3 片、顺序 wp0→wp1→wp2（`set.zw` 先清零、`or.w` 补中/高 wyde，正对应 48 位地址切片）；`addGlobalAddress` 携带 `getOffset()/getTargetFlags()`；用 `MachineInstrBuilder` 而非手改 operand 列表；无 `rb0` 作目的（Dst 由 RA 分配的可分配 GPRB）。
- `FK_rwii` printer：`isImm()`→`0x…`、`isExpr()`→`MAI.printExpr`，不再对 expr 断言；对既有立即数输出逐字节不变（`check-lit` 50/50 无回归）。
- 范围/纪律：仅改 4 个组件源文件；未手改 `components/**/patches/**`（`make_patch.py` 导出）；临时目录 `/tmp/opencode/LLVM-055t/`；未提交 DADAO-v5 git；未改函数签名、未引依赖。
- 防造假：所有留证 `cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`；脚本无 `tee`；期望字节/计数手算自 spec/IR（非从 llc 反推），由精确相等/计数判定；`--inject` 校验 `git diff --name-only` 非空、`git checkout` 还原 + `ninja` 重建后回绿。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `-filetype=asm` 崩溃：`FK_rwii` printer 对符号 expr 调 `getImm()` 断言 | ✅已修 | `DADAOMCInstPrinter` `FK_rwii` 分支改 `isImm()/isExpr()` | `llc -filetype=asm g.ll` EXIT=0（证据 `slice-wp`）；`make check-lit` 50/50 |
| F2 证据脚本 `"$NINJA"` 引号致命令名含空格，rc=127 | ✅已修 | 改 `ninja_build()` 函数 | 证据 `build` PASS rc=0 |
| F3 证据字节解析把 objdump ASCII 列并入 hex | ✅已修 | 改 `llvm-objcopy -O binary` + `od -tx1` | `be-data-g`/`be-rodata` 精确相等 |
| F4 证据硬编码 `.rela.data`/`.rela.rodata` 段索引 (6)/(8) | ✅已修 | 改按 section 名 grep | `rela-data-section`/`rela-rodata-section` PASS |
| F5 证据 `inject_round` 调 `fn` 未展开函数名（`command not found`） | ✅已修 | 改 `"$fn"` | `--inject` 两轮全 PASS |
| F6 证据 `check` 参数中早出现的 `$(...)` 会改写 `$?` | ✅已修 | 全部命令先 `rc=$?` 再传 `$rc` | 正常/注入模式 EXIT=0 |
| F7 证据 `instr-addend-disasm` 正则用空格、实际为 `\t` | ✅已修 | 改按 `iarr+0x18` + `R_DADAO_ABS48` 计数各=3 | `instr-addend-disasm` PASS（n=3 m=3） |
| F8 `.quad sym` 字段在 `.o` 中为 0（RELA 占位） | ❌不修（语义正确，披露） | 无 | 证据：RELA（`SHT_RELA`）下符号由 reloc 承载、link 期填非零（`LLVM-056t`）；`ML-003e Gap 2` 指无 reloc 的静默 0，已消除 → 验收 5 的真实输出 |
| F9 未加 `.ll` codegen lit 向量 | ⏸延后（超范围） | 无 | 证据：`CodeGen/DADAO` 为占位 suite、未接 `make check-lit`；接线需改 `lit.cfg.py`+`Makefile`，超任务书范围；本任务以 `run.sh` 31 项门控 |

**自验命令退出码**：`run.sh`（正常 31/31）EXIT=0；`run.sh --inject`（12/12）EXIT=0；`make check` EXIT=0；`make test-codegen` EXIT=0（15/15）；`make check-lit` EXIT=0（50/50）；`make check-patch-tree` EXIT=0（85 patches OK）；`make check-source-state` EXIT=0（clean, count=1）。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer subagent
**日期**：2026-10-06
**范围**：证据脚本审阅 + 正常模式重跑 + 独立注入第三轮 + 源码复核 + 同段判据 + 4 条沉淀判定

---

##### 1. 证据脚本审阅

- **FAIL 路径**：`check()` 函数用 `$rc` 判定（非恒真）；每条 `check` 调用前均 `rc=$?` 直接捕获退出码，无 `tee`、无内联 `$(...)` 吞退出码。✅
- **注入非空可还原**：`inject_break_slices` 删除 `or_w_rb` 两行（锚点实存 line 210–211）；`inject_no_abs48_reloc` 在 `!IsResolved` 块前插 ABS48 early return（锚点实存 line 144–147,151–152）。两者均 `git checkout` 还原 + `ninja` 重建。✅
- **结尾无 `tee`**：全脚本无 `tee`。✅
- **无恒真断言**：逐条核对 `check` 调用，每条的 `$rc` 来自真实退出码或计数比较，不存在 `check name, True` 或"两支同结果"结构。✅
- **`rela-not-rel` 逻辑**：`grep -q 'SHT_REL '`（带尾空格）不匹配 `SHT_RELA`；无 SHT_REL 时 `relrc=0` → `check rc=0` → PASS；有则 `relrc=1` → `check rc=1` → FAIL。✅

**脚本判决**：合格，可作为验收门控。

---

##### 2. 正常模式重跑（独立执行）

```
$ bash .work/evidence/LLVM-055t/run.sh > /tmp/opencode/LLVM-055t-review/normal.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0

RESULT: PASS (0 failures)

31/31 逐项输出：
[PASS] build                      | rc=0
[PASS] llc-obj-data-sections      | rc=0
[PASS] section-data               | 1 | rc=0
[PASS] section-rodata             | 1 | rc=0
[PASS] section-bss                | 1 | rc=0
[PASS] section-bss-nobits         | SHT_NOBITS | rc=0
[PASS] align-data                 | 16 | rc=0
[PASS] align-rodata               | 8 | rc=0
[PASS] align-bss                  | 8 | rc=0
[PASS] be-data-g                  | 000000000000002a | rc=0
[PASS] be-rodata                  | 0000000000000007 | rc=0
[PASS] llc-obj-addr               | rc=0
[PASS] abs48-count                | 9 | rc=0
[PASS] rel26-count                | 1 | rc=0
[PASS] abs48-arr-6                | 6 | rc=0
[PASS] rela-present               | 1 | rc=0
[PASS] rela-not-rel               | rel_found=0 | rc=0
[PASS] slice-wp                   | seq_ok=1 | rc=0
[PASS] same-section-no-reloc      | rc=0 | rc=0
[PASS] llc-obj-internal           | rc=0
[PASS] instr-addend               | 3 | rc=0
[PASS] instr-addend-disasm        | n=3 m=3 | rc=0
[PASS] llc-obj-data-reloc         | rc=0
[PASS] rela-data-section          | 1 | rc=0
[PASS] data-fp-reloc              | 2 | rc=0
[PASS] data-addend                | 1 | rc=0
[PASS] rela-rodata-section        | 1 | rc=0
[PASS] make-check-lit             | Passed: 50 (100.00%) | rc=0
[PASS] make-test-codegen          | 15/15 passed | rc=0
[PASS] make-check                 | repository checks: PASS | rc=0
[PASS] check-patch-tree           | 85 patches OK | rc=0
```

---

##### 3. 独立复核（真实输出）

**反汇编 addr.o**（跨 section + 同段 call）：
```
<addr_arr>:     set.zw rb31, wp0, 0x0  + R_DADAO_ABS48 arr
                or.w rb31, wp1, 0x0    + R_DADAO_ABS48 arr
                or.w rb31, wp2, 0x0    + R_DADAO_ABS48 arr
<addr_ext>:     set.zw rb31, wp0, 0x0  + R_DADAO_ABS48 ext
                or.w rb31, wp1, 0x0    + R_DADAO_ABS48 ext
                or.w rb31, wp2, 0x0    + R_DADAO_ABS48 ext
<addr_off>:     set.zw rd8, wp0, 0x10  (addend offset)
                set.zw rb8, wp0, 0x0   + R_DADAO_ABS48 arr
                or.w rb8, wp1, 0x0     + R_DADAO_ABS48 arr
                or.w rb8, wp2, 0x0     + R_DADAO_ABS48 arr
                add.o rb31, rb8, rd8
<call_same>:    call [rb0, 8]          ← 无 reloc（同段 PC-rel 就地解析）
<sibling>:      ...
<call_ext>:     call [rb0, 0]          + R_DADAO_REL26 extfn
```

**片位核对**：`4e 7c 00 00` → hb[5:4]=0 (wp0)；`4a 7d 00 00` → hb[5:4]=1 (wp1)；`4a 7e 00 00` → hb[5:4]=2 (wp2)。✅

**内部 addend**：`iarr+0x18`，3×ABS48 各 `Addend: 0x18`，反汇编注释一致。✅

**数据段**：`.rela.data` + `.rela.rodata` 各 `sibling` ABS48；`Addend: 0x10`（arr+16）。✅

**make check-patch-tree**：`85 patches OK`，EXIT=0。✅
**make check-source-state**：`llvm-project: OK HEAD=c9b87ba1ad11 count=1 clean=True`，EXIT=0。✅

---

##### 4. 独立注入第三轮（与 engineer 两轮不同方向）

**注入方向**：禁用同段就地解析（`DADAOAsmBackend.cpp` 的 `evaluateFixup` 中 `&Add->getSection() != F.getParent()` 改为 `if (true)`），强制所有 PC-rel 也发 reloc。

**注入文件**：`llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp`
**改动**：line 103 `if (&Add->getSection() != F.getParent())` → `if (true)`

```
$ git -C .work/source/llvm-project diff --name-only
llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp   ← 非空，注入有效

$ ninja -j8 -C .work/build/llvm llc
BUILD=0

# 注入状态：call_same 现在发 reloc
$ llvm-objdump -dr inj3-addr.o | grep -A2 'call \[rb0'
      38: 74 00 00 00  call [rb0, 0]
		0000000000000038:  R_DADAO_REL26	sibling     ← 原无 reloc，注入后有了

$ llvm-readobj -r inj3-addr.o | grep -c 'R_DADAO_REL26'
2   ← 原为1（仅 extfn），注入后 +1（sibling），rel26-count 检查 2≠1 → FAIL
```

**还原 + 重建**：
```
$ git -C .work/source/llvm-project checkout -- llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp
$ git -C .work/source/llvm-project diff --name-only
（空）

$ ninja -j8 -C .work/build/llvm llc
BUILD=0

# 还原后：call_same 回到无 reloc
$ llvm-objdump -dr restore-addr.o | grep -A2 'call \[rb0'
      38: 74 00 00 02  call [rb0, 8]                   ← 无 reloc 注解
$ llvm-readobj -r restore-addr.o | grep -c 'R_DADAO_REL26'
1   ← 回到正确值
$ llvm-readobj -r restore-addr.o | grep -c 'R_DADAO_ABS48'
9   ← ABS48 不受影响
```

**结论**：注入 → FAIL（REL26=2≠1，同段 call 出现多余 reloc）→ 还原+重建 → 回绿（REL26=1，ABS48=9）。✅

---

##### 5. 约束核验

| 约束 | 判定 |
|---|---|
| 尊重 `IsResolved` | ✅ `applyFixup` 先判 `!IsResolved` → `maybeAddReloc`；ABS48 resolved 时 early return |
| same-section 快速路径不用 `isUndefined()` 判跨段 | ✅ 用 `&Add->getSection() != F.getParent()` 比较 section；`isUndefined()` 仅用于「未定义符号→不解析」的前置 guard（line 98），**非**跨段判据 |
| `rb0` 禁作基址/零 | ✅ GLOBAL_ADDR 伪指令 Dst 为 GPRB（RA 分配），展开后 `set.zw/or.w` 目的寄存器由 RA 决定 |
| 大常量/大地址不折入受限立即数 | ✅ GlobalAddress 偏移折入 GA addend（RELA r_addend），不塞 imms18/imms12；`add.o` 加法独立物化 |
| 不改函数签名/不引依赖 | ✅ 仅扩4文件，无新外部依赖 |
| 补丁纪律 | ✅ `make_patch.py` 导出，`check-patch-tree` 85 OK |
| 构建串行/ninja -j8 | ✅ |
| 临时目录 `/tmp/opencode/LLVM-055t/` | ✅ |
| 不提交 git | ✅ DADAO-v5 仓库无未提交改动 |

---

##### 6. 同段就地解析判据复核

**实现**（`DADAOAsmBackend.cpp` evaluateFixup，line 93–113）：

```cpp
if (!Fixup.isPCRel()) return std::nullopt;          // 非 PC-rel → 不在此路径
const MCSymbol *Add = Target.getAddSym();
const MCSymbol *Sub = Target.getSubSym();
if (!Add || Sub || Add->isUndefined() || Add->isAbsolute())
  return std::nullopt;                               // 无定义/有减/未定义/绝对 → reloc
if (&Add->getSection() != F.getParent())
  return std::nullopt;                               // 跨 section → reloc
// 同 section：计算 PC 相对值，就地解析
```

**判据核对**：
- ✅ PC 相对：Add 已定义 + 非 absolute + 无 Sub + 同 section ⇒ 就地
- ✅ 否则（跨 section/未定义/有 Sub）⇒ reloc
- ✅ 绝对(ABS48)恒 reloc（不走此路径，applyFixup 中 ABS48 early return）
- ✅ 未用 `isUndefined()` 作跨段判据（跨段用 section 比较；`isUndefined()` 仅作未定义 guard）
- ✅ fast path section 平移不变（`V = Target.getConstant() + SymbolOffset - FragmentOffset`，section 整体平移时差值不变）
- ✅ 尊重 `IsResolved`（`applyFixup` 先判 `!IsResolved` → `maybeAddReloc`）

**判定**：同段就地解析实现严格满足任务约束。✅

---

##### 7. 4 条知识沉淀判定

| # | 内容 | 判定 |
|---|---|---|
| ① | `isOffsetFoldingLegal` 恒 false（ELF 下 `shouldAssumeDSOLocal` 默认 false，仅 internal 才折入 GA addend） | **属实**，ELF TLOF 默认行为正确。验证 GA addend 路径须用 `internal` 全局。✅ |
| ② | `.quad sym` 的 `.o` 字段=0（RELA 下符号由 reloc 承载，link 期填非零） | **属实**，RELA 语义正确。`ML-003e Gap 2` 的「静默清零」缺陷指无 reloc 的静默 0——已消除。**非阻塞**。✅ |
| ③ | `FK_rwii` printer 须并行支持 expr | **属实**，已实现 `isImm()/isExpr()` 分支（line 304–318）。`check-lit` 50/50 无回归。✅ |
| ④ | 未加 `.ll` codegen lit 向量（`CodeGen/DADAO` 占位 suite 未接 `check-lit`，以 `run.sh` 31 项作门控） | **属实**，`llvm/test/CodeGen/DADAO/` 目录不存在。本任务以 `run.sh` 31 项（含反例注入）作门控，足够。**需登记为遗留**：建议另立任务补 L2 向量（改 `lit.cfg.py` + `Makefile` 接入 `check-lit`）。✅ |

---

##### 8. 判决

**Accepted**

理由：
1. 正常模式 31/31 全绿，EXIT=0（reviewer 独立重跑）
2. 独立注入第三轮（禁用同段解析）→ FAIL（REL26=2≠1）→ 还原+重建 → 回绿（REL26=1，ABS48=9）
3. 段发射/地址材料化/数据段符号引用/不回归均独立验证通过
4. 同段就地解析判据严格满足约束（section 比较，非 isUndefined()）
5. 4 条沉淀均属实，④ 需登记但非阻塞
6. 补丁纪律/临时目录/不提交 git 均守
7. 证据脚本合格（FAIL 路径可达、注入非空可还原、无恒真、无 tee）
