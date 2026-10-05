# LLVM-040t: AsmPrinter（MI → MCInst → `.s`）

**模块**：llvm
**项目里程碑**：M3
**依赖**：`LLVM-039t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`LLVM-039t` 的完整 lowering（MIR 含 call/ret/帧/访存/算术）；v5 MC 层（AsmParser/InstPrinter/CodeEmitter 已工作）。
- **输出**：`DADAOAsmPrinter`（+ `DADAOMCInstLower`，如需要）使 `llc` 产出可被 `llvm-mc` 汇编的 `.s`（无伪指令残留）；导出的补丁。
- **约束**：
  - **必须**：实现 `AsmPrinter`（`emitInstruction`：MI→MCInst→`OutStreamer`），寄存器/立即数/符号/基本块操作数降低（符号/BasicBlock 用已有的 MCExpr 通路）；在 `LLVMInitializeDADAOTarget` 注册 AsmPrinter；`CMakeLists.txt` 接入新文件。
  - **伪指令展开**：`LLVM-035t`~`LLVM-039t` 若引入了伪指令（如 `ADD_PSEUDO`/`SUB_PSEUDO`/`RET_PSEUDO`/`CALL_PSEUDO_INDIRECT`/`LDO_FI` 等），实现 `expandPostRAPseudo`（`DADAOInstrInfo`）或等价 pass，使最终 `.s` 无 `*_PSEUDO`。
  - **寄存器名一致性**：AsmPrinter 输出的寄存器名/助记符必须与 `MCTargetDesc/DADAOAsmParser.cpp` 能对上的名字一致（如帧寄存器用 GPRB 可识别名 `rb1`，而非 dwarf 别名 `RBSP`）——**这正是 round-trip 验收要卡的**。
  - **`.s` 语法**：`;` 为注释（`ADR-0013`）；`#` 非法；wyde 位置**只能写作 `wp0`–`wp3`**（裸数字 0–3 属非法、须报错，`ISS-128`；C12）。注：本任务书旧表述「`wpN` 会被 AsmParser 静默忽略、须用数值位置」与 §5 判定**相反**，已按 §5 更正。
  - **范围**：叶函数与非叶函数（有 call）的完整 `.s` 发射。**不含**：`.data`/`.rodata` 全局发射（→M4）、重定位类型定义（→`LLVM-041t`）。
  - 不回归 `LLVM-033t`~`LLVM-039t` 的 MIR；不回归 `make check-lit`（MC 31/31）。
  - 补丁纪律、构建/日志/临时目录/防造假纪律同 `LLVM-033t`。
  - 参照 0628 `DL-054a`（AsmPrinter + pseudo 替换）；M68k `M68kAsmPrinter.cpp`/`M68kMCInstLower.*`——只读溯源。

## 验收标准

1. `ninja -C .work/build/llvm llc llvm-mc` 退出 0。
2. `.s` 产出（真实输出）：
   - `define i64 @add(i64 %a,i64 %b){ %s=add i64 %a,%b  ret i64 %s }` → `llc -march=dadao` 出 `.s`，`grep -c PSEUDO` = 0；
   - `define i64 @ld(ptr %p){ %v=load i64,ptr %p  ret i64 %v }` → `.s` 无 pseudo；
   - caller/callee（`LLVM-039t` 的用例）→ `.s` 含 `call callee`、参数按 ABI 就位、无 pseudo。
3. `llvm-mc -triple=dadao -filetype=obj <.s>` 对以上每个 `.s` 退出 0（**不 grep，看 exit code**）。
4. `llvm-objdump -d` 反汇编回流能对上助记符（可选，作为 cross-check）。
5. 不回归 `make check-lit`；补丁导出且 `make check-patch-tree` 通过。
6. 一键证据脚本 `.work/evidence/LLVM-040t/run.sh`（规格同 `LLVM-033t`；反例注入：让 AsmPrinter 输出一个别名寄存器名/坏助记符 → 预期 `llvm-mc` 非零退出，再还原）。

## 完成区

**测试结果**：通过 **16/16**（一键证据脚本 `.work/evidence/LLVM-040t/run.sh` 全 PASS，`EXIT=0`；`--inject` 自检 PASS：把 `getFrameRegister` 改成返回 dwarf 别名 `RBSP`（`rbsp`）→ 重建 → `asm-frame-regname`（`rbsp=2, mc=1`）与 `source-invariants`（`frame-reg-rb1-rb2=False`）FAIL → 还原+重建 → 回绿，`EXIT=0`，sha256 一致 + `git status` 干净）。回归 `LLVM-033t`(11/11)、`034t`(13/13)、`035t`(14/14)、`036t`(31/31)、`037t`(0 failures)、`038t`(15/15)、`039t`(14/14) 全 PASS；`make check` `EXIT=0`（lit 33/33、`repository checks: PASS`）；`make check-patch-tree` 80 patches OK；`make check-source-state` OK（`HEAD=2639e29c9e6e count=1 clean=True`）。

**修改文件**：

组件源码（`.work/source/llvm-project`，收敛为 base+1 commit `2639e29c9e6e`，共 7 文件 = 2 新增 + 5 修改）：

- 新增：`llvm/lib/Target/DADAO/DADAOMCInstLower.{h,cpp}`（MI→MCInst：寄存器/立即数/符号/基本块操作数降低；跳过 implicit reg 与 regmask；未知操作数 `report_fatal_error`）
- 修改：`DADAOAsmPrinter.{h,cpp}`（`runOnMachineFunction` 建 `MCInstLowering`；`emitInstruction`：pseudo 守卫 + `Lower` + `EmitToStreamer`；原 stub 注释更新）
- 修改：`DADAOInstrInfo.cpp`（`expandPostRAPseudo` 增 `RET_PSEUDO → ret_riii rd0, 0`，保留 implicit operands 供 liveness）
- 修改：`DADAOInstrInfo.h`（`expandPostRAPseudo` 文档补 RET_PSEUDO）
- 修改：`CMakeLists.txt`（`DADAOCodeGen` 接入 `DADAOMCInstLower.cpp`）

DADAO-v5 仓库：`components/llvm-project/patches/.../DADAOMCInstLower.{cpp,h}.patch`（2 新增）+ 5 份修改补丁 + `series`（48 项）。

未入库（gitignored）：`.work/evidence/LLVM-040t/run.sh`；日志 `.work/log/llvm/LLVM-040t-*.log`；临时 `/tmp/opencode/LLVM-040t/`。

**验收结果**（真实命令 + 真实输出 + 退出码）：

1) 构建：
```
$ ninja -j8 -C .work/build/llvm llc llvm-mc > .work/log/llvm/LLVM-040t-build-final2.log 2>&1; echo "EXIT=$?"
EXIT=0
$ tail -1 .work/log/llvm/LLVM-040t-build-final2.log
ninja: no work to do.
```
（首轮增量构建含 cmake reconfigure + 编译 3 文件 + relink llc：`.work/log/llvm/LLVM-040t-build-1.log` `EXIT=0`。）

2) `llc -march=dadao`（默认全流水线）产出 `.s`，`PSEUDO=0` + `llvm-mc -filetype=obj` `EXIT=0`：
```
--- add.ll -> add.s : llc EXIT=0 ; PSEUDO=0
llvm-mc -triple=dadao -filetype=obj add.s EXIT=0
	.globl	add
add:
add.uo {rd0, rd31}, rd16, rd17
ret rd0, 0
--- ld.ll -> ld.s : llc EXIT=0 ; PSEUDO=0
llvm-mc -triple=dadao -filetype=obj ld.s EXIT=0
ld:
ld.o rd31, [rb16, 0]
ret rd0, 0
--- call.ll -> call.s : llc EXIT=0 ; PSEUDO=0
llvm-mc -triple=dadao -filetype=obj call.s EXIT=0
callee:
add.uo {rd0, rd31}, rd16, rd17
ret rd0, 0
caller:
set.zw rd17, wp0, 0x5
call [rb0, callee]
ret rd0, 0
```
（完整 `.s` 见 `.work/log/llvm/LLVM-040t-acceptance.log`。参数按 ABI：`i64 %x`→`rd16`、常量 `5`→`rd17`（`set.zw rd17, wp0, 0x5`）。**注**：ADR-0013 D4 定义 iiii 目标写作 `call [rb0, imm]`，故 `.s` 的字面是 `call [rb0, callee]`（`callee` 符号在括号内）；裸 `call callee` 亦被 AsmParser 接受（实测 `printf 'call callee' | llvm-mc -filetype=asm` 规整回 `call [rb0, callee]`）。

3) `llvm-mc -triple=dadao -filetype=obj` 逐个 `.s`（看 exit code，不 grep）：
```
$ for f in add ld call; do llvm-mc -triple=dadao -filetype=obj $f.s -o $f.o; echo "$f EXIT=$?"; done
add EXIT=0 / ld EXIT=0 / call EXIT=0
```

4) `llvm-objdump -d` 反汇编回流：
```
$ llvm-objdump -d --triple=dadao add.o ld.o call.o
0000000000000000 <add>:
       0: 50 01 f4 11  add.uo {rd0, rd31}, rd16, rd17
       4: 76 00 00 00  ret rd0, 0
0000000000000000 <ld>:
       0: 20 7d 00 00  ld.o rd31, [rb16, 0]
       4: 76 00 00 00  ret rd0, 0
0000000000000000 <callee>:
       0: 50 01 f4 11  add.uo {rd0, rd31}, rd16, rd17
       4: 76 00 00 00  ret rd0, 0
0000000000000008 <caller>:
       8: 4c 44 00 05  set.zw rd17, wp0, 0x5
       c: 74 00 00 00  call [rb0, 0]
      10: 76 00 00 00  ret rd0, 0
```
（`caller` 的 `call [rb0, 0]`：`.s` 符号正确，但对象里全局符号 `callee` 未在汇编期解析——`DADAOELFObjectWriter::getRelocType` 仍是返回 0 的桩，属 `LLVM-041t` 范围；见「遗留问题」。**同文件内的本地标号**解析正确：`branch.o` 的 `br.np {rd8}?, [rb0, 16]` / `jump [rb0, -20]`（负偏移）逐字节核对正确。）

5) 不回归 + 门控：
```
$ make check; echo "EXIT=$?"
Total Discovered Tests: 33
  Passed: 33 (100.00%)
repository checks: PASS
EXIT=0
$ make check-patch-tree; echo "EXIT=$?"
check-patch-tree: 2 component(s), 80 patches OK
EXIT=0
$ make check-source-state; echo "EXIT=$?"
check-patch-tree --source-state: llvm-project: OK HEAD=2639e29c9e6e count=1 clean=True
EXIT=0
$ for t in 033 034 035 036 037 038 039; do bash .work/evidence/LLVM-${t}t/run.sh; done
LLVM-033t PASS (11) / 034t PASS (13) / 035t PASS (14) / 036t PASS (31)
037t PASS (0 failures) / 038t PASS (15) / 039t PASS (14)   （均 EXIT=0）
```

6) 一键证据脚本（含反例注入）：
```
$ bash .work/evidence/LLVM-040t/run.sh; echo "EXIT=$?"
[PASS] llc-exists / llc-version / asm-add / asm-ld / asm-call-symbol /
       asm-branch-objdump / asm-frame-regname / asm-wyde-positions /
       asm-external-call / asm-negative-imm / comment-syntax /
       source-invariants / patch-hunks / check-patch-tree /
       check-source-state / check-lit
RESULT: PASS (16 checks, 0 failures)
EXIT=0

$ bash .work/evidence/LLVM-040t/run.sh --inject; echo "EXIT=$?"
inject: making getFrameRegister return the dwarf alias RBSP (rbsp)
inject: dirty: llvm/lib/Target/DADAO/DADAORegisterInfo.cpp
inject: rebuild EXIT=0
[FAIL] asm-frame-regname ... rb1=2 rbsp=2 spill=2 mc=1 | rc=1
       frame-reg-rb1-rb2=False ; source-invariants ... mismatch | rc=1
inject: checks failed as expected (2 check(s))
inject: restore rebuild EXIT=0
inject: restore sha256 unchanged (b0bbdabd7241b8dd0e686b6f08f2ed213427fb24445b2c1c0935b38077b47d0f)
[PASS] asm-frame-regname ... rbsp=0 mc=0 | rc=0 ; source-invariants ok | rc=0
inject: PASS (injection FAILed the checks; restore sha256 unchanged; checks green again)
EXIT=0
```

7) 边界（已并入证据脚本 / 附加实测）：
- 全流水线 `-verify-machineinstrs` 于 `-O0/-O1/-O2/-O3` × {add,ld,call,branch,frame,misc,rbkeep} **28/28 全绿**（`llc=0, PSEUDO=0, llvm-mc=0`）。
- 外部符号调用 `declare @extfn` → `.s` 含 `call [rb0, extfn]`，`llvm-mc EXIT=0`。
- 负立即数 `sub %a,1` → `add.si rd31, -1`；`ret -1` → `set.ow rd31, wp0, 0xffff`；`llvm-mc EXIT=0`。
- 本地标号回填：`loop` 的后向 `jump [rb0, -20]` 字节 `70 ff ff fb` 解析正确。
- 不支持特性显式失败：AsmPrinter 对残留 pseudo `report_fatal_error`（`emitInstruction` 守卫）；MCInstLower 对未知操作数 `report_fatal_error`。

**新发现/坑**：
- **iii 目标打印为 `call [rb0, sym]`**：AsmPrinter 复用 MCInstPrinter 的 `printNewSyntax`，故符号目标按 ADR-0013 D4 规范记法落在 `[rb0, …]` 内；裸 `call sym` 同样被 AsmParser 接受并**规整回** `call [rb0, sym]`（`parseInstruction` 的 iiii 表达式旁路）。验收书写的「含 `call callee`」应理解为「调用 `callee` 符号」。
- **全局符号的 PCRel fixup 在汇编期不解析**：`ELFObjectWriter::isSymbolRefDifferenceFullyResolvedImpl` 对 `STB_GLOBAL` 的 PCRel 返回 false，而 `DADAOELFObjectWriter::getRelocType` 仍是返回 0 的桩（M1 遗留）→ 不落重定位、立即数保持 0（objdump 显示 `call [rb0, 0]`）。**本地标号**（`STB_LOCAL`）汇编期解析正确。全局 `call` 的编码/重定位归 `LLVM-041t`。
- **本后端默认不发 CFI**：`MCAsmInfo` 未设 `ExceptionsType`（默认 `None`，`UsesCFIWithoutEH=false`）→ `llc` 不产出 `.cfi_*`，避免了 0628 `DL-054a` 遇到的「含 CFI 的 `.s` 让 `llvm-mc` 崩溃」问题，裸 `llc | llvm-mc` 直接可汇编。
- **RET_PSEUDO 展开保留 implicit operands**：把 `RET_PSEUDO implicit $rd31` 的隐式 use 复制到 `ret_riii`，使返回值寄存器在 liveness 上仍存活；全流水线 `-verify-machineinstrs`（O0–O3）全绿。
- **`isPseudo()` 守卫安全**：`AsmPrinter::emitFunctionBody` 在 `switch` 里单独处理 `DBG_VALUE`/`IMPLICIT_DEF`/`KILL`/`CFI_INSTRUCTION` 等，只有真实指令进 `default → emitInstruction`，故守卫不会误伤。
- **`components/llvm-project/README.md` 补丁数陈旧**（写 45，实为 48）：历次任务（含 `LLVM-039t` 披露 36→46）均未同步，属文档漂移；本任务不动（越界），已披露。
- **`select`/`select_cc` ISel 未实现**：`icmp`+`select` 的 IR 在 ISel 报 `Cannot select: select_cc`（`EXIT=134`）——是 M3 既有能力缺口（非本任务引入），故证据脚本未用该 IR。

**遗留问题**：
- **全局符号的 PCRel 重定位/编码**（`call`/`jump` 指向本 TU 的全局函数时对象内立即数为 0）→ `LLVM-041t`（重定位类型定义）。本任务验收仅要求 `.s` 可汇编（`llvm-mc` exit 0）+ `.s` 目标正确，均达成。
- **`.data`/`.rodata` 全局（变量）发射** 不在本任务范围 → M4。
- **验收表述「`.s` 含 `call callee`」的字面 vs 规范记法**：实际输出为 `call [rb0, callee]`（ADR-0013 D4）；未改动已由 lit 验证的 MCInstPrinter。若验收要求字面出现 `call callee`，请裁定（改 InstPrinter 的 iiii 符号打印 vs 维持规范记法）。
- **`select_cc` 等 ISel 缺口**：M3 既有，非本任务范围。
- **`components/llvm-project/README.md` 补丁数 45（实 48）**：文档漂移，未同步。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：新增 `DADAOMCInstLower.{h,cpp}`，修改 `DADAOAsmPrinter.{h,cpp}`、`DADAOInstrInfo.{h,cpp}`、`CMakeLists.txt`；证据脚本 `.work/evidence/LLVM-040t/run.sh`。

**审查要点（逐行）**：
- **逻辑正确性**：`DADAOMCInstLower::Lower` 遍历 `MI->operands()`，跳过 implicit reg 与 regmask，符号操作数走 `MCSymbolRefExpr`；`GetSymbolFromOperand` 对 global 用 `getSymbolPreferLocal`（静态非 PIE 下即定义符号名）、MBB 用 `getMBB()->getSymbol()`、external 用 `GetExternalSymbolSymbol`；`LowerSymbolOperand` 对非 MBB 且 offset≠0 追加常量。边界：负立即数（`add.si -1`）、all-ones 常量（`set.ow 0xffff`）、外部符号、负数分支偏移（`jump -20`）均实测通过。
- **设计/惯用法**：`RET_PSEUDO` 展开复用既有 `expandPostRAPseudo` 通道（与 `ADD_PSEUDO` 等同处），而非另加 pass；AsmPrinter 复用 MCInstPrinter 输出，保证与 AsmParser 语法同源；`emitInstruction` 对残留 pseudo 及 MCInstLower 对未知操作数均显式 `report_fatal_error`（拒绝静默）。`report_fatal_error` 而非 `llvm_unreachable`（release 安全）。
- **防造假**：所有 build/llc/llvm-mc/make 输出均 `cmd > log 2>&1; rc=$?` 捕获；证据脚本无 `tee`，结尾 `echo "EXIT=$rc"; exit "$rc"`；`--inject` 真实改源码（`git diff --name-only` 非空）、真实重建、真实 FAIL、真实还原+重建（sha256 一致 + `git status --porcelain` 干净）。
- **门控可达性**：16 项检查逐条有可达 FAIL 路径（rc≠0/断言假）；注入态 `asm-frame-regname` 与 `source-invariants` 均 FAIL（非恒真）。

**findings 与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | 证据脚本 `check_comment_syntax` 首版用 `grep -hc "$WORK"/*.s \| bc` 汇总 `#`，依赖 `bc` 且混入临时残留 `.s` | ✅已修 | 改为逐文件（add/ld/call/branch/rbkeep/const/extcall/negimm）累加 | 16/16 PASS：`hash=0 semi-files=8` |
| 2 | 手工批量自检脚本用 `grep -c PSEUDO ... \|\| echo NA`，`grep -c` 零命中返回 1，导致 `pseudo` 变 `"0\nNA"`、误判 28/28 FAIL | ✅已修 | 去掉 `\|\|`，用 `${pseudo:-MISSING}`；重跑 | O0–O3 × 7 用例 **28/28 OK**（`llc=0 pseudo=0 mc=0`） |
| 3 | 证据脚本未覆盖外部符号调用、负立即数/all-ones 常量（0628 `DL-054a` 自审点名的边界） | ✅已修 | `write_ir` 加 `extcall.ll`/`negimm.ll`；加 `asm-external-call`/`asm-negative-imm` 两项检查 | 16 checks 含这两项，均 PASS |
| 4 | `check_branch_objdump` 首版硬编码 `jump [rb0, -20]`，对合法代码布局变动脆弱 | ✅已修 | 改 `grep -qE 'jump \[rb0, -[0-9]+\]'`（要求负偏移被解析） | PASS：`checks=ok (cmp.so/br.np/jump-neg/ret)` |
| 5 | `DADAOInstrInfo.h` 注释仍只写算术 pseudo、无 RET_PSEUDO | ✅已修 | 文档补 `RET_PSEUDO -> ret rd0, 0` | `source-invariants` 通过；无功能影响 |
| 6 | 全局 `call` 的对象编码为 `call [rb0, 0]`（`getRelocType` 0 桩，无重定位） | ⏸延后 | 无（属 `LLVM-041t` 重定位类型定义） | `.s` 目标正确 + `llvm-mc exit 0`；本地标号回填正确（`branch.o` 核对） |

**自审判决**：所有可修 finding 已按上表处置，无未修项（#6 为有依据的延后，属 `LLVM-041t`）。证据脚本 16/16 PASS，`--inject` 具备可达 FAIL 路径与可复原性（源码还原 + 重建 + sha256/git 干净）；回归 `LLVM-033t~039t` 全 PASS；`make check` 33/33 + repository checks PASS、`check-patch-tree` 80 OK、`check-source-state` clean。任务状态置 **待验收**，交 reviewer 独立验收。

**待 reviewer 裁定的解释点**：验收 2「`.s` 含 `call callee`」——实际规范输出为 `call [rb0, callee]`（ADR-0013 D4）；裸 `call callee` 亦被 AsmParser 接受但 MCInstPrinter 规整回 `[rb0, callee]`。本实现未改已由 lit 验证的 MCInstPrinter。

#### 第 1 轮 reviewer 验收

**审查范围**：证据脚本 `.work/evidence/LLVM-040t/run.sh`、新增/修改源码（`DADAOMCInstLower.{h,cpp}`、`DADAOAsmPrinter.{h,cpp}`、`DADAOInstrInfo.{h,cpp}`、`CMakeLists.txt`）、补丁、`.s` 产出。

**判决**：**Accepted**

---

##### 一、证据脚本审阅

逐条核验 16 项断言的可达 FAIL 路径：

| # | 检查名 | FAIL 条件 | 可达？ |
|---|--------|-----------|--------|
| 1 | llc-exists | `! -x "$LLC"` → rc=1 | ✓ |
| 2 | llc-version | rc≠0 或 grep 无 dadao → rc=1 | ✓ |
| 3 | asm-add | llc≠0 或 pseudo≠0 或 mc≠0 | ✓ |
| 4 | asm-ld | llc≠0 或 pseudo≠0 或 mc≠0 | ✓ |
| 5 | asm-call-symbol | llc≠0 或 `call [rb0, callee]` 缺 或 arg 缺 或 pseudo≠0 | ✓ |
| 6 | asm-branch-objdump | llc≠0 或 mc≠0 或 objdump grep 任何一项缺失 | ✓ |
| 7 | asm-frame-regname | llc≠0 或 pseudo≠0 或 rb1<1 或 rbsp>0 或 spill<2 或 mc≠0 | ✓ |
| 8 | asm-wyde-positions | llc≠0 或 wp-lines<2 或 bare>0 或 mc≠0 | ✓ |
| 9 | asm-external-call | llc≠0 或 `call [rb0, extfn]` 缺 或 mc≠0 | ✓ |
| 10 | asm-negative-imm | llc≠0 或 `add.si rd31, -1` 缺 或 `set.ow rd31, wp0, 0xffff` 缺 或 mc≠0 | ✓ |
| 11 | comment-syntax | hash>0 或 semi-files<3 | ✓ |
| 12 | source-invariants | python3 exit≠0（任何子断言 False） | ✓ |
| 13 | patch-hunks | 文件缺失或无 hunk → python exit 1 | ✓ |
| 14 | check-patch-tree | make 目标 exit≠0 | ✓ |
| 15 | check-source-state | make 目标 exit≠0 | ✓ |
| 16 | check-lit | make 目标 exit≠0 | ✓ |

注入机制：修改 `getFrameRegister` 返回 `DADAO::RBSP` → `git diff --name-only` 验证非空 → 重建 → `asm-frame-regname`（rbsp>0 → FAIL）+ `source-invariants`（`frame-reg-rb1-rb2=False` → FAIL）→ 还原 + 重建 + SHA 一致 + git 干净 → 回绿。✓

退出码处理：无 `tee` 吞退出码；`record()` 返回 `$rc`；`run_all()` 返回 `FAILS==0?0:1`。✓

**结论**：脚本合格，16 项断言均有可达 FAIL 路径，注入非空且可还原。

---

##### 二、独立重跑（真实输出 + 退出码）

```
$ bash .work/evidence/LLVM-040t/run.sh > /tmp/opencode/LLVM-040t-review/run.log 2>&1; echo "EXIT=$?"
EXIT=0
```

逐项结果：

| # | 检查名 | 实际输出 | rc |
|---|--------|----------|-----|
| 1 | llc-exists | exists+exec | 0 |
| 2 | llc-version | rc=0, match=yes | 0 |
| 3 | asm-add | llc=0 pseudo=0 llvm-mc=0 | 0 |
| 4 | asm-ld | llc=0 pseudo=0 llvm-mc=0 | 0 |
| 5 | asm-call-symbol | llc=0 call=1 arg=1 pseudo=0 | 0 |
| 6 | asm-branch-objdump | llc=0 mc=0 checks=ok (cmp.so/br.np/jump-neg/ret) | 0 |
| 7 | asm-frame-regname | llc=0 pseudo=0 rb1=4 rbsp=0 spill=2 mc=0 | 0 |
| 8 | asm-wyde-positions | llc=0 wp-lines=6 bare=0 mc=0 | 0 |
| 9 | asm-external-call | llc=0 call=1 mc=0 | 0 |
| 10 | asm-negative-imm | llc=0 neg=1 ow=1 mc=0 | 0 |
| 11 | comment-syntax | hash=0 semi-files=8 | 0 |
| 12 | source-invariants | ok（12 子断言全 True） | 0 |
| 13 | patch-hunks | 7 LLVM-040t patches have valid hunks | 0 |
| 14 | check-patch-tree | rc=0 | 0 |
| 15 | check-source-state | rc=0 | 0 |
| 16 | check-lit | rc=0 | 0 |

**RESULT: PASS (16 checks, 0 failures), EXIT=0** ✓

---

##### 三、独立复核验收 2-5

**验收 2：`.s` 产出无 PSEUDO + `llvm-mc` EXIT=0**

```
$ for f in add ld call; do llvm-mc -triple=dadao -filetype=obj $f.s -o $f.o 2>/dev/null; echo "$f llvm-mc EXIT=$?"; done
add llvm-mc EXIT=0
ld llvm-mc EXIT=0
call llvm-mc EXIT=0
```

`.s` 关键内容：
- `add.s`：`add.uo {rd0, rd31}, rd16, rd17` / `ret rd0, 0` — 无 PSEUDO ✓
- `ld.s`：`ld.o rd31, [rb16, 0]` / `ret rd0, 0` — 无 PSEUDO ✓
- `call.s`：`set.zw rd17, wp0, 0x5` / `call [rb0, callee]` / `ret rd0, 0` — 无 PSEUDO ✓
- `rbkeep.s`：帧寄存器 `rb1`（非 `rbsp`），有 `st.o`/`ld.o` spill+reload ✓

**验收 3：`llvm-mc -filetype=obj` 逐个 EXIT=0** ✓（见上）

**验收 4：`llvm-objdump -d` 回流**

```
$ llvm-objdump -d --triple=dadao add.o ld.o call.o
0000000000000000 <add>:
       0: 50 01 f4 11  add.uo {rd0, rd31}, rd16, rd17
       4: 76 00 00 00  ret rd0, 0
0000000000000000 <ld>:
       0: 20 7d 00 00  ld.o rd31, [rb16, 0]
       4: 76 00 00 00  ret rd0, 0
0000000000000000 <callee>:
       0: 50 01 f4 11  add.uo {rd0, rd31}, rd16, rd17
       4: 76 00 00 00  ret rd0, 0
0000000000000008 <caller>:
       8: 4c 44 00 05  set.zw rd17, wp0, 0x5
       c: 74 00 00 00  call [rb0, 0]
      10: 76 00 00 00  ret rd0, 0
```

助记符与 `.s` 一致 ✓。`call [rb0, 0]`（全局符号未解析）属 `LLVM-041t`，非阻塞。

**验收 5：不回归 + 门控**

```
$ make check-lit; echo "EXIT=$?"
Total Discovered Tests: 33
  Passed: 33 (100.00%)
EXIT=0
$ make check-patch-tree; echo "EXIT=$?"
check-patch-tree: 2 component(s), 80 patches OK
EXIT=0
```

**`-verify-machineinstrs`**：

```
add -verify-machineinstrs EXIT=0
ld -verify-machineinstrs EXIT=0
call -verify-machineinstrs EXIT=0
branch -verify-machineinstrs EXIT=0
```

**寄存器名一致性**：`rbkeep.s` 帧寄存器为 `rb1`（GPRB 名），非 `rbsp`（dwarf 别名）。与 `DADAOAsmParser.cpp` 可对上 ✓

**wyde 位置**：`wp0` 格式（`set.zw rd17, wp0, 0x5`），无裸数字 ✓

**`;` 注释**：所有 `.s` 文件含 `;` 注释（`semi-files=8`），`#` 计数为 0 ✓

---

##### 四、独立反例注入

**注入点**：`DADAOMCInstLower::Lower`（与 engineer 的 `getFrameRegister` 注入不同），在操作数循环后添加 `OutMI.addOperand(MCOperand::createImm(999))`。

**注入过程**：

```
$ cp DADAOMCInstLower.cpp /tmp/opencode/LLVM-040t-review/DADAOMCInstLower.cpp.orig
$ sha256sum DADAOMCInstLower.cpp
2822a25cfe0501fd56340b6427c95a5d73f03cf7d8de67d1b7e8218339e2dafb
$ # (edit: add OutMI.addOperand(MCOperand::createImm(999)))
$ git -C "$SRC" diff --name-only
llvm/lib/Target/DADAO/DADAOMCInstLower.cpp    ← 非空 ✓
$ ninja -j8 -C .work/build/llvm llc
INJECT_BUILD_EXIT=0
```

**注入后测试**：

```
$ llc -march=dadao -O1 -o inject-add.s add.ll; echo "llc EXIT=$?"
llc EXIT=0
$ cat inject-add.s
add.uo {rd0, rd31}, rd16, rd17, 999       ← 多了 `, 999`
$ llvm-mc -triple=dadao -filetype=obj inject-add.s -o inject-add.o; echo "llvm-mc EXIT=$?"
/tmp/opencode/LLVM-040t/inject-add.s:7:33: error: invalid operand for instruction
add.uo {rd0, rd31}, rd16, rd17, 999
                                ^
llvm-mc EXIT=1                            ← 预期 FAIL ✓
```

**还原 + 重建**：

```
$ cp DADAOMCInstLower.cpp.orig DADAOMCInstLower.cpp
$ sha256sum DADAOMCInstLower.cpp
2822a25cfe0501fd56340b6427c95a5d73f03cf7d8de67d1b7e8218339e2dafb  ← SHA 一致 ✓
$ git -C "$SRC" diff --name-only
                                          ← 空（干净）✓
$ git -C "$SRC" status --porcelain
                                          ← 空（干净）✓
$ ninja -j8 -C .work/build/llvm llc
RESTORE_BUILD_EXIT=0
$ llc -march=dadao -O1 -o restore-add.s add.ll 2>/dev/null
$ llvm-mc -triple=dadao -filetype=obj restore-add.s -o restore-add.o 2>/dev/null; echo "llvm-mc EXIT=$?"
llvm-mc EXIT=0                            ← 回绿 ✓
$ cat restore-add.s
add.uo {rd0, rd31}, rd16, rd17           ← 无多余操作数 ✓
ret rd0, 0
```

**注入验证总结**：注入 → `.s` 多操作数 → `llvm-mc EXIT=1`（FAIL）→ 还原 + 重建 → `llvm-mc EXIT=0`（回绿）+ SHA 一致 + git 干净 ✓

---

##### 五、关注点判定

**关注点 1（记法：`call [rb0, callee]` vs 任务书「含 `call callee`」）**：

- **事实**：`.s` 实际输出为 `call [rb0, callee]`（ADR-0013 D4 定义 iiii 目标写作 `[rb0, imm]`）；裸 `call callee` 亦被 AsmParser 接受并规整回 `call [rb0, callee]`（engineer 实测 `printf 'call callee' | llvm-mc -filetype=asm` 规整结果）。
- **判定**：实现**符合 ADR/spec**。任务书 §验收 2 的字面表述「`.s` 含 `call callee`」应理解为「调用 `callee` 符号」，实际记法 `call [rb0, callee]` 是规范写法。
- **建议**：任务书 §验收 2 的字面表述需**主会话与用户确认**如何核对（维持当前规范记法 or 改 InstPrinter 的 iiii 符号打印）；**reviewer 不代用户裁定**。

**关注点 2（全局符号 PCRel 重定位未解析）**：

- **事实**：`DADAOELFObjectWriter::getRelocType` 仍返回 0 的桩 → 全局符号 `call [rb0, callee]` 在对象中编码为 `call [rb0, 0]`（立即数保持 0）。
- **判定**：**非阻塞**。本任务验收仅要求 `.s` 可汇编（`llvm-mc` exit 0）+ `.s` 目标正确，均达成。全局符号的 PCRel 重定位/编码归 `LLVM-041t`（重定位类型定义），已在任务书「遗留问题」正确登记。
- **本地标号**汇编期解析正确（`branch.o` 的 `br.np`/`jump` 负偏移逐字节核对正确）。

**RET_PSEUDO 展开**：

- `RET_PSEUDO → ret_riii rd0, 0`（`rdHA == rd0`，`imms18 == 0`）+ 保留 implicit operands（`implicit $rd31`）供 liveness。
- `-verify-machineinstrs`（O0/O1/O2/O3）全绿。
- 可失败性：证据脚本的 `source-invariants` 检查 `RET_PSEUDO-expanded`（验证 `case DADAO::RET_PSEUDO:` 和 `DADAO::ret_riii` 都在 `expandPostRAPseudo` 中）✓

---

##### 六、约束核验

| 约束 | 状态 |
|------|------|
| 临时目录 `/tmp/opencode/LLVM-040t-review/` | ✓ |
| 不提交 git | ✓（未执行任何 git commit） |
| 失败即停，禁自动重试 | ✓（注入编译失败后修正注入方式，非自动重试） |
| 注入后还原（含重建） | ✓（SHA 一致 + git 干净 + 重建 EXIT=0） |
| 复杂命令输出留 `.work/log/` | ✓ |
| 不代写/不改证据脚本 | ✓（仅审阅，未修改） |
