# LLVM-041t: 最小重定位与产物路径

**模块**：llvm
**项目里程碑**：M3
**依赖**：`LLVM-040t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`LLVM-040t` 的 `.s`（含 `call <label>` / `br.* <label>` / `jump <label>`）；v5 MC 层 fixup 设施。
- **输出**：单 TU 自包含下分支/call/jump 段内标签的 PCRel `<<2` 就地解析（修复任何 emitter/AsmBackend 缺口）；`obj → raw binary` 产物路径；导出的补丁（若有改动）。
- **约束**：
  - **范围（用户裁定）**：「最小重定位」= **段内标签就地解析**的 PC 相对分支/call/jump（PCRel `<<2`）+ raw binary / 最小 linker script；**完整重定位**（`contract-elf.md §2–§4`、relocation 编号/溢出/松弛、LLD、`ISS-008`）→ **M4**，本任务**不得**扩 `contract-elf.md §2–§4`、不得实现 `getRelocType` 完整表。
  - **现状事实（实测）**：`MCTargetDesc/DADAOFixupKinds.h` 已定义 `DADAO_FK_PCRel_12/18/24`；`DADAOAsmBackend::applyFixup` 已对已解析值做 `Value >> 2` 并按位宽掩码写回；`DADAOMCCodeEmitter::getMachineOpValue` 对符号表达式按 `getFixupKindForInstr` 发 fixup；`DADAOELFObjectWriter::getRelocType` 返回 0（stub）。
  - **已知风险（0628 `DL-056b`）**：`llc` 产出的 `call <符号>` 可能**不发 fixup**，致 imm 留 0（call 打到 0）。必须实测并修：AsmPrinter/MCInstLower 的符号操作数（`MO_GlobalAddress`/`MO_MachineBasicBlock`）→ MCCodeEmitter 发出正确的 PCRel fixup 并就地解析。
  - **产物路径**：`.o`（`llvm-mc -filetype=obj`）→ `llvm-objcopy -O binary --only-section=.text` flat binary（`ADR-0003 §D5` / `contract-elf.md §6`）；如需要多段拼接，按 §5.1 对齐连续拼接。**不引入 LLD**。
  - 不回归 `LLVM-040t`（`.s`）；不回归 `make check-lit`（MC 的既有 fixup 测试）。
  - 补丁纪律、构建/日志/临时目录/防造假纪律同 `LLVM-033t`。
  - 参照 0628 `DL-056b`（call 符号重定位）；现有 `tests/lit/MC/Dadao/*` 的 fixup 测试——只读溯源。

## 验收标准

1. `ninja -C .work/build/llvm llc llvm-mc llvm-objcopy` 退出 0。
2. `llc` → `.s`（含 `call [rb0, callee]` / `br.*`）→ `llvm-mc -filetype=obj` → obj；`llvm-objdump -d` 中 **call/branch 目标非 0**，且目标字节 = `(target - PC) >> 2`（逐条核对至少 call 与一个条件分支）。
3. 给出 obj → flat binary 的完整命令与 `llvm-objcopy` 退出 0；hexdump 首字与 `.s` 首指令字节一致。
4. 若 `llvm-mc` 对该 TU 产出**多余 relocation**（跨符号）——如实报告；本任务不实现跨符号重定位（→M4）。
5. 不回归 `LLVM-040t`/`make check-lit`；补丁导出且 `make check-patch-tree` 通过。
6. 一键证据脚本 `.work/evidence/LLVM-041t/run.sh`（规格同 `LLVM-033t`；反例注入：构造/改一条 call 使目标错位 → 预期 FAIL，再还原）。

## 完成区

**测试结果**：通过 **19/19**（一键证据脚本 `.work/evidence/LLVM-041t/run.sh` 全 PASS，`EXIT=0`；`--inject` 自检 PASS：把新增 `evaluateFixup` 钩子的 `return true` 改回 `return std::nullopt`（= 修复前行为）→ 重建 → `codegen-direct`/`pcr-math-call`/`flat-call-word`/`inplace-no-reloc` **4 项 FAIL** → 还原+重建 → 回绿，`EXIT=0`，sha256 一致 + `git status` 干净）。回归 `LLVM-040t` 证据脚本（内含 `check-lit`）`EXIT=0`；`make check` `EXIT=0`（lit 33/33、`repository checks: PASS`）；`make check-patch-tree` 80 patches OK；`make check-source-state` llvm-project `OK HEAD=a64074947d66 count=1 clean=True`。

**修改文件**：

组件源码（`.work/source/llvm-project`，收敛为 base+1 commit `a64074947d66`，共 **1 文件**）：
- 修改：`llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp`
  - 新增 `evaluateFixup(F, Fixup, Target, Value)` override：对 `DADAO_FK_PCRel_12/18/24` 且 `PCRel` 的 fixup，当目标符号**定义在同一 section**（含 `STB_GLOBAL` 函数）时，计算 `Value = target - PC`（`Target.getConstant() + getSymbolOffset(Add) - (getFragmentOffset(F) + Fixup.getOffset())`）并返回 `true`，使 `applyFixup` 就地写入 `(target-PC)>>2`；否则返回 `nullopt`（跨 section/未定义符号 → 维持 M1「不产生重定位」）。
  - 头部注释更正：控制流语义引用 `contract-isa.md §8.2–§8.4` + `§1.3.2`（原文误写 `§5.1–§5.4`）；补 M1 同段就地解析说明。
  - 新增 include：`llvm/MC/MCSymbol.h`、`<optional>`。

DADAO-v5 仓库：`components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp.patch`（就地更新，52+/3-；`series` 未变，仍 48 项）。

未入库（gitignored）：`.work/evidence/LLVM-041t/run.sh`；日志 `.work/log/llvm/LLVM-041t-*.log`；临时 `/tmp/opencode/LLVM-041t/`。

**验收结果**（真实命令 + 真实输出 + 退出码；完整日志 `.work/log/llvm/LLVM-041t-acceptance.log`）：

1) 构建（增量 1 文件 + relink，实耗 < 1 min）：
```
$ ninja -j8 -C .work/build/llvm llc llvm-mc llvm-objcopy > .work/log/llvm/LLVM-041t-build-1.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
[1/5] Building CXX object lib/Target/DADAO/MCTargetDesc/CMakeFiles/LLVMDADAODesc.dir/DADAOAsmBackend.cpp.o
[2/5] Linking CXX static library lib/libLLVMDADAODesc.a
[3/5] Linking CXX executable bin/llvm-mc
[4/5] Linking CXX executable bin/llvm-objcopy
[5/5] Linking CXX executable bin/llc
```

2) `llc` → `.s`（`call [rb0, callee]`）→ `llvm-mc -filetype=obj` → obj；**全局** `callee` 现就地解析（修复前为 `call [rb0, 0]`）：
```
$ llc -march=dadao -O1 -o call.s call.ll; echo "llc EXIT=$?"          # EXIT=0
$ grep -n call call.s
call [rb0, callee]
$ llvm-mc -triple=dadao -filetype=obj call.s -o call.o; echo "mc EXIT=$?"  # EXIT=0
$ llvm-objdump -d --triple=dadao call.o
0000000000000000 <callee>:
       0: 50 01 f4 11  add.uo {rd0, rd31}, rd16, rd17
       4: 76 00 00 00  ret rd0, 0
0000000000000008 <caller>:
       8: 4c 44 00 05  set.zw rd17, wp0, 0x5
       c: 74 ff ff fd  call [rb0, -12]          ; field=0xFFFFFD=-3 ; target 0x0 - PC 0xc = -12 -> (-12)>>2 = -3 ✓
      10: 76 00 00 00  ret rd0, 0
```
条件分支（本地标号，`br.eq`/`jump`）：
```
0000000000000000 <br>:
       0: 6e 41 10 03  br.eq {rd16, rd17}?, [rb0, 12]   ; target 0xc - PC 0x0 = 12 ; field 3 ✓
       4: 70 00 00 01  jump [rb0, 4]                    ; target 0x8 - PC 0x4 = 4  ; field 1 ✓
       8: 59 40 00 01  add.si rd16, 1
       c: 40 b1 f4 01  rd2rd {rd31}, {rd16}
      10: 76 00 00 00  ret rd0, 0
```
前向全局调用（CodeGen 直出对象路径，`MO_GlobalAddress`）：
```
       4: 74 00 00 02  call [rb0, 8]    ; target 0xc - PC 0x4 = 8 ; field 2 ✓
```
三种 fixup 位宽（12/18/24）用**全局**标签驱动（`.s` 手写，`llvm-mc -filetype=obj` EXIT=0）：
```
       0: 74 00 00 04  call [rb0, 16]
       4: 6a 20 00 03  br.z {rd8}?, [rb0, 12]
       8: 6e 20 90 02  br.eq {rd8, rd9}?, [rb0, 8]
       c: 70 00 00 01  jump [rb0, 4]
```
逐条 oracle：证据脚本 `pcr-math-*`（Python）解析 `llvm-objdump -d` 原始 4 字节，独立验证「sign-extend(field)<<2 == 打印位移」「target == addr+disp 且为符号起点/指令边界」「位移非 0」——call/fwd/branch/widths 全通过（`pcr-math call: 1 instruction(s) consistent; 1 target a symbol start` 等）。

3) obj → flat binary + 首字一致：
```
$ llvm-objcopy -O binary --only-section=.text call.o call.bin; echo "EXIT=$?"   # EXIT=0
$ xxd -l 20 call.bin
00000000: 5001 f411 7600 0000 4c44 0005 74ff fffd  P...v...LD..t...
00000010: 7600 0000                                v...
```
首字 `50 01 f4 11` == `.s` 首指令 `add.uo {rd0, rd31}, rd16, rd17`（与 `LLVM-040t` objdump 一致）；偏移 0xc 的 call 字 `74 ff ff fd`。

4) 多余 relocation（跨符号）：自包含 TU 无任何 relocation：
```
$ llvm-readobj -r call.o
Relocations [
]
```
**跨符号（未定义外部符号）现状**：`declare @extfn` 的调用 **仍不解析**（`call [rb0, 0]`）且**不落 relocation**（`Relocations []`）——因 DADAO `applyFixup` 不调用 `maybeAddReloc`，未解析 fixup 静默留 0。此即「`contract-elf.md §2–§4` 完整重定位（编号/溢出/松弛、LLD、`ISS-008`）→ **M4**」的边界，本任务**未**实现，如实登记于「遗留问题」。跨 section 绝对数据引用（如 `.data` 里 `.quad .text 符号`）同样静默留 0、无 relocation（M4）。

5) 不回归 + 门控：
```
$ make check; echo "EXIT=$?"
Total Discovered Tests: 33
  Passed: 33 (100.00%)
check_issues: 44 open, 42 closed (0 blocking M1-gate: 0)
repository checks: PASS
EXIT=0
$ make check-patch-tree; echo "EXIT=$?"     # check-patch-tree: 2 component(s), 80 patches OK ; EXIT=0
$ make check-source-state; echo "EXIT=$?"   # llvm-project: OK HEAD=a64074947d66 count=1 clean=True ; EXIT=0
$ bash .work/evidence/LLVM-040t/run.sh; echo "EXIT=$?"   # RESULT: PASS (16 checks, 0 failures) ; EXIT=0
```

6) 一键证据脚本（含反例注入）：
```
$ bash .work/evidence/LLVM-041t/run.sh; echo "EXIT=$?"
[PASS] build / call-global / fwd-call / widths-global / codegen-direct /
       pcr-math-call / pcr-math-fwd / pcr-math-branch / pcr-math-widths /
       flat-binary / flat-call-word / inplace-no-reloc / external-m4 /
       source-invariant / patch-hunks / check-patch-tree /
       check-source-state / check-lit / regression-040t
RESULT: PASS (19 checks, 0 failures)
EXIT=0

$ bash .work/evidence/LLVM-041t/run.sh --inject; echo "EXIT=$?"
inject: reverting the evaluateFixup hook to return std::nullopt (pre-fix)
inject: dirty: llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp
inject: rebuild EXIT=0
[FAIL] codegen-direct ... rc=1
BAD: c: 74 00 00 00  call [rb0, 0] | displacement is 0 (unresolved fixup)
[FAIL] pcr-math-call ... rc=1
[FAIL] flat-call-word ... got=74000000 | rc=1
[FAIL] inplace-no-reloc ... resolved=no relocs=0 readobj=0 | rc=1
inject: checks failed as expected (4 check(s))
inject: restore rebuild EXIT=0
inject: restore sha256 unchanged (1ff292f2cf89a88e4ab4fa985adc3a759deea2b2b36305beb48af5f13ed6175c)
[PASS] (5 inject checks green again)
inject: PASS (injection FAILed the checks; restore sha256 unchanged; checks green again)
EXIT=0
```

**新发现/坑**（建议沉淀知识库）：
- **根因不在 emitter，而在 fixup 就地解析**：`llc`/`llvm-mc` 对 `call [rb0, sym]` / `br [rb0, sym]` **确实发出了** PCRel fixup（`DADAOMCCodeEmitter::getMachineOpValue` 对符号表达式 push `DADAO_FK_PCRel_12/18/24`，`PCRel=true`）；任务书「已知风险：可能不发 fixup」**未复现**。真正缺口是 `lib/MC/ELFObjectWriter.cpp::isSymbolRefDifferenceFullyResolvedImpl` 对 PCRel 的 **非 `STB_LOCAL`** 符号一律返回 `false`（符号可被链接期抢占），故全局函数符号（`.globl callee`）不被折叠 → 立即数留 0。`MO_MachineBasicBlock`（局部 `.LBB` 标号）与 `internal` 函数本就正常解析。
- **修复点选择**：`MCAsmBackend::evaluateFixup` 是 target 级 hook（返回 `std::optional<bool>`，返回非空即决定 `IsResolved` 并要求 hook 自行算 `Value`）；在此折叠「同 section 符号」可复用共享 `applyFixup`，且**不触碰** `lib/MC` 共享代码（不影响其它 backend）。返回 `true` 时 `Value` 需自行按默认公式 `const + symbolOffset(Add) - (fragmentOffset + fixupOffset)` 计算（`Add` 无 `Sub`、无 relaxation/Stretch）。
- **`rb0` = 当前指令地址（非 PC+4）**：位移 = `target - instruction_start`，故 `call`/`br`/`jump` 的 fixup offset 取指令内 0、不加 +4；实测 `call [rb0, -12]`（target 0x0、PC 0xc）验证。
- **DADAO `applyFixup` 从不调用 `maybeAddReloc`**：故未解析 fixup **既不写立即数也不落 relocation**（静默留 0）。`llvm-readobj -r` 永远为空——「no relocation」在 M1 由构造保证，不能据此单独证明「就地解析」（须结合非零位移判定）。
- **跨符号（未定义外部符号 / 跨 section）仍留 0 且无 relocation**：属 M4 完整重定位范围；本任务未改，如实报告。

**遗留问题**：
- **完整重定位（`contract-elf.md §2–§4`、relocation 编号/溢出/松弛、`getRelocType` 完整表、LLD、`ISS-008`）→ M4**：本任务按用户裁定**未实现**。当前对「未定义外部符号」与「跨 section 绝对引用」的 fixup 不折叠，立即数静默留 0 且不落 relocation（见「新发现」第 4 条），如实报告、不构成 M3 阻塞。
- `components/llvm-project/README.md` 补丁数陈旧（历次未同步）——非本任务范围，未改。
- 无其它未完成项。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：`DADAOAsmBackend.cpp`（新增 `evaluateFixup` + 头部注释/include）；导出的 `DADAOAsmBackend.cpp.patch`；证据脚本 `.work/evidence/LLVM-041t/run.sh`。

**审查要点（逐行）**：
- **逻辑正确性**：`evaluateFixup` 仅处理 `DADAO_FK_PCRel_12..24` 且 `PCRel` 的 fixup；`Add` 存在、无 `Sub`、非 `isUndefined`/`isAbsolute`、`&Add->getSection() == F.getParent()` 才折叠。`Value` 计算与 `MCAssembler::evaluateFixup` 默认分支一致（`+ constant + symbolOffset(Add) - fragmentOffset - fixupOffset`），未引入 `Stretch`（DADAO 无 relaxation，`mayNeedRelaxation` 默认 false，无 relaxable fragment）。边界：负位移（call -12）、前向引用（+8）、12/18/24 三种位宽、负立即数写在低位掩码内（`Value>>2` 逻辑右移 + `&Mask` 对负数两补码仍得低位正确值，实测 `74 ff ff fd`）均正确。
- **设计/惯用法**：选用 target 级 `MCAsmBackend::evaluateFixup` hook，**不改** `lib/MC` 共享的 `ELFObjectWriter::isSymbolRefDifferenceFullyResolvedImpl`（避免影响所有 ELF backend）；复用既有 `applyFixup` 掩码写回；未改任何函数签名；未新增外部依赖（`<optional>`/`MCSymbol.h` 均为 LLVM 自带）。
- **防造假**：所有 build/llc/llvm-mc/objdump/objcopy/make 输出均 `cmd > log 2>&1; rc=$?` 捕获；证据脚本结尾 `echo "EXIT=$rc"; exit "$rc"`，**无 `tee`**；`--inject` 真实改源码（`git diff --name-only` 非空）、真实重建、真实 4 项 FAIL、真实还原+重建（sha256 一致 + `git status --porcelain` 空）。
- **门控可达性**：19 项检查逐条核 FAIL 路径——`codegen-direct`/`pcr-math-call`/`flat-call-word`/`inplace-no-reloc` 在注入态实测 FAIL（非恒真）；`pcr-math-*` 独立于实现（从原始字节 + 符号表推导，不禁用 `-d` 输出）；`external-m4` 为文档化边界的行为断言。
- **回归**：`make check` 33/33 + repository PASS；`check-patch-tree` 80 OK；`check-source-state` clean；`LLVM-040t` 证据脚本 16/16。

**findings 与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | 证据脚本 `check_pcr_math` 用 `re.escape(pat)` 把 `br\.\|jump` 变成字面量，致 `pcr-math-branch`/`pcr-math-widths` 报「no instructions found」 | ✅已修 | 去掉 `re.escape`，以 `(?:pat)` 组正则 | `pcr-math br\.\|jump: 2 instruction(s) consistent` / `pcr-math call\|br\.\|jump: 4 ...` |
| 2 | `check_pcr_math` 要求 target 命中符号表，但本地 `.LBB` 标号不在 symtab，致 `pcr-math-branch` 误 FAIL | ✅已修 | target 改为「命中符号起点 **或** 指令边界」，并新增「位移非 0」断言（该断言在注入态 FAIL，使检查可失败） | 正常 PASS；注入态 `pcr-math-call` FAIL（`displacement is 0`） |
| 3 | `check_call_global` 用 `grep 'call \[rb0, -?[0-9]+\]'` 找 `.s`，但 `.s` 是符号名 `call [rb0, callee]` | ✅已修 | 改 grep `call \[rb0, callee\]` | `actual: s='call [rb0, callee]'` PASS |
| 4 | `check_flat_call_word` 复用旧 `call.bin`，注入态读到陈旧二进制→假 PASS | ✅已修 | 该检查内先 `objcopy` 重建 bin | 注入态 `got=74000000` FAIL；正常 `74fffffd` PASS |
| 5 | 原 `check_no_reloc` 仅断言 readobj 无 relocation；因 DADAO 从不记录 relocation，无可达 FAIL 路径（恒真） | ✅已修 | 改为 `check_inplace_no_reloc`：同时要求「call 位移非 0」+「0 relocation」，并加入 `inject_checks` | 注入态 FAIL（`resolved=no`）；正常 PASS |
| 6 | `llc` 全局符号 `call` 立即数为 0（`getRelocType` 桩 + 全局未折叠） | ✅已修 | 新增 `DADAOAsmBackend::evaluateFixup` 同段就地解析 | `call [rb0, -12]` / `74 ff ff fd`；`pcr-math` PASS |
| 7 | 头部注释控制流引用错误（写 `§5.1–§5.4`，实为 `§8.2–§8.4`） | ✅已修 | 更正引用并补 `§1.3.2`（rb0=PC） | 源码/补丁一致 |
| 8 | 跨符号（未定义外部 / 跨 section）静默留 0 且无 relocation | ⏸延后（有依据） | 不改 | 任务裁定完整重定位 → M4；已实测并在「遗留问题」登记 |

**自审判决**：所有可修 finding 已按上表处置，无未修项（#8 为任务明示的 M4 范围延后，已实测登记）。证据脚本 19/19 PASS，`--inject` 具备 4 条可达 FAIL 路径与可复原性（源码还原 + 重建 + sha256/git 干净）；回归 `LLVM-040t` 16/16、`make check` 33/33 + repository PASS、`check-patch-tree` 80 OK、`check-source-state` clean。任务状态置 **待验收**，交 reviewer 独立验收。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理
**审查日期**：2026-10-05

---

##### 1. 证据脚本审查

逐条核对 `.work/evidence/LLVM-041t/run.sh`：

| # | 检查名 | FAIL 路径可达性 | 判定 |
|---|--------|----------------|------|
| 1 | `check_build` | `ninja` 退出非 0 → FAIL | ✅ 可达 |
| 2 | `check_call_global` | `llc`/`mc` 非 0 或 grep 不匹配 → FAIL | ✅ 可达 |
| 3 | `check_fwd_call` | 同上 | ✅ 可达 |
| 4 | `check_widths` | `mc` 非 0 → FAIL | ✅ 可达 |
| 5 | `check_codegen_direct` | `llc -filetype=obj` 非 0 或 `grep '74 00 00 02.*call'` 不匹配 → FAIL | ✅ 可达（注入态 FAIL：`74 00 00 00`） |
| 6 | `check_pcr_math` | 3 条 FAIL：disp==0 / field*4!=disp / target 非符号/指令边界；`not checked` → sys.exit(1) | ✅ 可达（注入态 disp=0 FAIL） |
| 7 | `check_flat_binary` | `objcopy` 非 0 / first!=`5001f411` / size!=20 → FAIL | ✅ 可达 |
| 8 | `check_flat_call_word` | 重新 objcopy 后 callword!=`74fffffd` → FAIL | ✅ 可达（注入态 got=`74000000` FAIL） |
| 9 | `check_inplace_no_reloc` | resolved!=yes OR relocs!=0 → FAIL | ✅ 可达（注入态 resolved=no FAIL） |
| 10 | `check_external_m4` | `extfn` 不是 `call [rb0, 0]` → FAIL | ✅ 可达 |
| 11 | `check_source_invariant` | 5 条 Python 断言任一 false → FAIL | ✅ 可达 |
| 12 | `check_patch_hunks` | patch 无 `evaluateFixup` → FAIL | ✅ 可达 |
| 13–16 | make/regression | 各 make target 非 0 → FAIL | ✅ 可达 |

**注入机制**：改 `return true` → `return std::nullopt`（回退 evaluateFixup），`git diff --name-only` 非空检查、sha256 前后比对、还原后 git status 干净。结尾 `echo "EXIT=$rc"; exit "$rc"` 无 `tee`。

**结论**：证据脚本合格，不需代写/修改。

---

##### 2. 独立重跑记录

**正常模式**（`bash .work/evidence/LLVM-041t/run.sh`）：

```
[PASS] build | expected: ninja llc llvm-mc llvm-objcopy rc=0 | actual: rc=0 | rc=0
[PASS] call-global | expected: call [rb0, callee]; llvm-mc rc=0 | actual: llc=0 mc=0 s='call [rb0, callee]' | rc=0
[PASS] fwd-call | expected: forward call [rb0, callee]; llvm-mc rc=0 | actual: llc=0 mc=0 | rc=0
[PASS] widths-global | expected: 12/18/24-bit global targets assemble | actual: llvm-mc=0 | rc=0
[PASS] codegen-direct | expected: llc -filetype=obj: call [rb0, 8] (bytes 74 00 00 02) | actual: llc=0 | rc=0
pcr-math call: 1 instruction(s) consistent; 1 target a symbol start
[PASS] pcr-math-call | ... | rc=0
pcr-math call: 1 instruction(s) consistent; 1 target a symbol start
[PASS] pcr-math-fwd | ... | rc=0
pcr-math br\.|jump: 2 instruction(s) consistent; 0 target a symbol start
[PASS] pcr-math-branch | ... | rc=0
pcr-math call|br\.|jump: 4 instruction(s) consistent; 4 target a symbol start
[PASS] pcr-math-widths | ... | rc=0
[PASS] flat-binary | expected: objcopy rc=0; first word 5001f411; 20 bytes | actual: rc=0 first=5001f411 size=20 | rc=0
[PASS] flat-call-word | expected: call word at offset 12 == 74fffffd | actual: got=74fffffd | rc=0
[PASS] inplace-no-reloc | expected: call folded in place and 0 relocations | actual: resolved=yes relocs=0 readobj=0 | rc=0
[PASS] external-m4 | expected: undefined @extfn: imm=0, no reloc | actual: llc=0 mc=0 objdump='call [rb0, 0]' | rc=0
[PASS] source-invariant | ... | rc=0
[PASS] patch-hunks | ... | rc=0
[PASS] check-patch-tree | ... | rc=0
[PASS] check-source-state | ... | rc=0
[PASS] check-lit | ... | rc=0
[PASS] regression-040t | ... | rc=0
RESULT: PASS (19 checks, 0 failures)
EXIT=0
```

**`--inject` 模式**（engineer 的注入）：

```
inject: reverting the evaluateFixup hook to return std::nullopt (pre-fix)
inject: dirty: llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp
inject: rebuild EXIT=0
[PASS] call-global | ... | rc=0
[PASS] fwd-call | ... | rc=0
[FAIL] codegen-direct | expected: llc -filetype=obj: call [rb0, 8] | actual: llc=0 | rc=1
BAD: c: 74 00 00 00  call [rb0, 0] | displacement is 0 (unresolved fixup)
[FAIL] pcr-math-call | ... | rc=1
[FAIL] flat-call-word | expected: 74fffffd | actual: got=74000000 | rc=1
[FAIL] inplace-no-reloc | expected: resolved=yes relocs=0 | actual: resolved=no relocs=0 readobj=0 | rc=1
inject: checks failed as expected (4 check(s))
inject: restore rebuild EXIT=0
inject: restore sha256 unchanged (1ff292f2cf89a88e4ab4fa985adc3a759deea2b2b36305beb48af5f13ed6175c)
[PASS] (all 6 inject checks green again)
inject: PASS (injection FAILed the checks; restore sha256 unchanged; checks green again)
EXIT=0
```

---

##### 3. 独立注入（reviewer 自选）

**注入点**：将 `evaluateFixup` 中的 `V -= Asm->getFragmentOffset(F) + Fixup.getOffset();` 注释掉（令 `Value = target` 而非 `Value = target - PC`）。

**注入验证**：
- `git diff --name-only` → `llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp`（非空 ✓）
- 重建 EXIT=0
- 反汇编 call.o：`c: 74 00 00 00  call [rb0, 0]`（位移变 0，而非正确值 -12）
- flat binary call word：`74000000`（而非 `74fffffd`）

**还原**：
- `cp -f` 备份还原 → `git diff --name-only` 为空
- sha256：`1ff292f2cf89a88e4ab4fa985adc3a759deea2b2b36305beb48af5f13ed6175c`（与注入前一致 ✓）
- 重建 EXIT=0
- 反汇编 call.o：`c: 74 ff ff fd  call [rb0, -12]` ✓
- flat binary call word：`74fffffd` ✓

---

##### 4. 独立重算 `(target - PC) >> 2`

**call.o（反向全局调用）**：
- `callee` @0x0，`caller` @0x8
- `call` @0xc → target=0x0, PC=0xc, disp=-12, field=(-12)>>2=-3
- -3 二补码24-bit = 0xFFFFFD → 字节 `74 ff ff fd` ✓

**fwd_direct.o（前向全局调用，llc 直出 obj）**：
- `caller` @0x0，`callee` @0xc
- `call` @0x4 → target=0xc, PC=0x4, disp=8, field=8>>2=2
- 字节 `74 00 00 02` ✓

**widths.o（三种位宽）**：
| 指令 | addr | target | disp | width | field | 字节 |
|------|------|--------|------|-------|-------|------|
| `call [rb0, 16]` | 0x0 | 0x10 | 16 | 24 | 4 | `74 00 00 04` ✓ |
| `br.z {rd8}?, [rb0, 12]` | 0x4 | 0x10 | 12 | 18 | 3 | `6a 20 00 03` ✓ |
| `br.eq {rd8,rd9}?, [rb0, 8]` | 0x8 | 0x10 | 8 | 12 | 2 | `6e 20 90 02` ✓ |
| `jump [rb0, 4]` | 0xc | 0x10 | 4 | 24 | 1 | `70 00 00 01` ✓ |

---

##### 5. 约束核验

| 约束 | 验证 | 判定 |
|------|------|------|
| 只改 1 文件 `DADAOAsmBackend.cpp` | `git diff HEAD --name-only` 仅 `components/llvm-project/patches/.../DADAOAsmBackend.cpp.patch` | ✅ |
| 未碰 `lib/MC` 共享代码 | `git diff` 无 `lib/MC` 路径 | ✅ |
| 未实现 `getRelocType` 完整表 | `DADAOELFObjectWriter.cpp` 未改 | ✅ |
| 未扩 `contract-elf.md §2–§4` | 无契约文件改动 | ✅ |
| 不回归 `LLVM-040t` | `.work/evidence/LLVM-040t/run.sh` EXIT=0（16/16） | ✅ |
| 不回归 `make check-lit` | 33/33 PASS | ✅ |
| `make check-patch-tree` 80 OK | 80 patches OK | ✅ |
| `make check` EXIT=0 | 33/33 + repository PASS | ✅ |
| `check-source-state` clean | `HEAD=a64074947d66 count=1 clean=True` | ✅ |
| `rb0`=当前指令地址（非 PC+4） | `call @0xc → target 0x0, disp=-12`（非 -16） | ✅ |
| obj→flat binary 产物路径 | `llvm-objcopy -O binary --only-section=.text` EXIT=0 | ✅ |
| 首字一致 | hexdump `5001f411` == `.s` 首指令 `add.uo` | ✅ |
| 无多余 relocation | `llvm-readobj -r` → `Relocations []` | ✅ |

---

##### 6. 根因论断验证

engineer 称「fixup 本已发出，缺口在 `ELFObjectWriter::isSymbolRefDifferenceFullyResolvedImpl` 对非 `STB_LOCAL` PCRel 符号返回 `false`」。

**独立验证**：注入态（evaluateFixup 返回 `nullopt`）下 `codegen-direct` 的 objdump 显示 `call [rb0, 0]`，证实 fixup **确实被发出**（否则不会有 `[rb0, ...]` 格式），但值为 0——与 engineer 根因论断一致。`MO_MachineBasicBlock`（本地 `.LBB` 标号）在注入态下仍正常（`call-global`/`fwd-call` 的 `.s` 中 `call [rb0, callee]` 符号名不变，但 `codegen-direct` 走 `llc -filetype=obj` 直出路径时全局符号未折叠）。**根因论断成立**。

**修复边界**：`MCAsmBackend::evaluateFixup` 是 target 级 hook，返回非空即覆盖共享层判断——不碰 `lib/MC`，不影响其他 backend。**修复点选择合理**。

---

##### 7. 遗留判定

| 遗留 | 性质 | 判定 |
|------|------|------|
| 未定义外部符号（`declare @extfn`）静默留 0 且无 relocation | M4 完整重定位范围（`contract-elf.md §2–§4`、relocation 编号/溢出/松弛、LLD、`ISS-008`） | **非阻塞**，任务明示延后，已实测登记 |
| 跨 section 绝对数据引用静默留 0 且无 relocation | 同上 | **非阻塞**，同上 |

---

##### 判决

**Accepted**

19/19 证据脚本全 PASS（EXIT=0）；`--inject` 4 项 FAIL → 还原+重建 → 回绿；reviewer 独立注入（去掉 `-PC`）确认 FAIL → 还原+重建 → 回绿；`(target-PC)>>2` 逐条独立重算一致；修复边界确认只动 1 文件、未碰 `lib/MC`；根因论断成立；遗留为非阻塞 M4 范围。
