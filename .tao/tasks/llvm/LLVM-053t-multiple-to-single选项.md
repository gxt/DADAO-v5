# LLVM-053t: `-multiple-to-single` 汇编器选项

**模块**：llvm
**项目里程碑**：M4
**依赖**：`LLVM-051t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `spec/DADAO-11-AEE-应用程序运行环境.md` §汇编兼容性 §汇编器选项：`-multiple-to-single`——「将多寄存器指令转换为一系列的单寄存器指令；转换过程**保持助记符（opcode）不变**」；`.tao/knowledge/contract-asm.md §8`（当前 v5 报 `Unknown command line argument`）。
  - 现有 AsmParser（`AsmParser/DADAOAsmParser.cpp`）与多寄存器指令编码：`ldm.*`/`stm.*`（`rrri`，`{start:end}` 组）、块赋值/格式转换（`orri`，`immu6`=连续个数，共 8+20 条）。
- **输出**（组件源码改在 `.work/source/llvm-project`；导出补丁）：
  - 为 `llvm-mc` 注册 CL 选项 **`-multiple-to-single`**；启用时把多寄存器指令展开为一串**单寄存器**指令（同助记符，例如 `ldm.o {rd8:rd10}, [rb0, rd1]` → 3 条单寄存器 `ldm.o` 各自偏移）；未启用（默认）行为**不变**。
- **约束**：
  - **保持助记符**；转换后**语义等价**（各寄存器/各元素按序）。
  - 只影响多寄存器指令；单寄存器指令与其它指令不变。
  - **reloc/fixup 坑预防（5 条，同 `LLVM-050t`）**：展开后的每条仍需正确发/解析 fixup。
  - **补丁纪律（`spec/Process-01`）**；`commit --amend` 收敛 base+1 → `make_patch.py` → `check-patch-tree`；不手改补丁。
  - 构建/串行/临时目录/留证纪律同 `LLVM-050t`；`ninja -j8`；失败即停。
  - 临时目录 `/tmp/opencode/LLVM-053t/`；**不提交 git**。

## 验收标准

1. 构建 EXIT=0。
2. **选项生效**：`llvm-mc -triple=dadao -multiple-to-single -filetype=obj` EXIT=0；对 `ldm.*`/`stm.*`/块赋值/格式转换各 ≥1 例，反汇编显示**展开为单寄存器序列**（给出真实 `llvm-objdump -d` 输出），且**助记符不变**。
3. **默认不变**：不加该选项时，多寄存器指令编码与 `LLVM-051t` 前一致（逐字节比对，给出 before/after）。
4. **选项可识别**：`llvm-mc --help` 含 `-multiple-to-single`；未知选项仍报错。
5. **lit 向量**：`tests/llvm/lit/MC/DADAO/` 新增用例（选项开/关对照）；`make check-lit` EXIT=0 不回归；`make check` EXIT=0。
6. 一键证据脚本 `.work/evidence/LLVM-053t/run.sh`（含 `--inject`：把展开逻辑改错/漏一条单寄存器 → 期望 FAIL → 还原+重建 → 回绿）；完成区贴真实输出。

## 完成区

**测试结果**：通过 32/32（一键证据 `.work/evidence/LLVM-053t/run.sh` 正常模式 32 项全 PASS，EXIT=0）+ 反例注入 16/16（`--inject` 2 轮：ldm.o 宽度 8→4 / orri 源未推进 → FAIL → 还原+重建 → 回绿，EXIT=0）。`make check` EXIT=0；`make check-lit` 49/49（46→49，新增 3，无回归）；`make test-codegen` 15/15；`check-patch-tree` 85 patches OK；`check-source-state` llvm-project clean+count=1。失败原因：无。

**修改文件**：
- 组件源码（`.work/source/llvm-project`，已 amend 收敛为 base+1：`6dfe1677a..15c8bd3f8`，worktree clean）：
  - `llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp`（+`expandMultiRegisterInstruction` + 匹配判定助手 `isMultiToSingleOrriMnemonic`/`ldmStmElemWidth` + `matchAndEmitInstruction` 内 hook）
  - `llvm/include/llvm/MC/MCTargetOptions.h`（+`bool DADAOMultipleToSingle = false;`，沿用既有 `X86*`/`PPC*` 目标专属字段先例）
  - `llvm/tools/llvm-mc/llvm-mc.cpp`（+可见 `cl::opt -multiple-to-single`（`cl::cat(MCCategory)`）+ 写入 `MCOptions.DADAOMultipleToSingle`）
- 补丁集：`components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`（更新）+ **新增** `.../llvm/include/llvm/MC/MCTargetOptions.h.patch`、`.../llvm/tools/llvm-mc/llvm-mc.cpp.patch`（`make_patch.py` 导出；`series` 51→**53**，未手改）。
- 台账：`components/llvm-project/changelog.md`（+LLVM-053t 一条）。
- 测试向量（新增 3）：`tests/llvm/lit/MC/DADAO/multiple-to-single-ldm.s`、`-orri.s`、`-reject.s`。
- 证据脚本：`.work/evidence/LLVM-053t/run.sh`（新增）；日志 `.work/log/llvm/LLVM-053t-*.log`。
- 本任务书（完成区/自审/状态）。

**验收结果**（真实输出，`cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，无 `tee`）：

1. **构建 EXIT=0**（`.work/log/llvm/LLVM-053t-build.log`、`-build2.log`）：`ninja -j8 -C .work/build/llvm llvm-mc llvm-objdump llvm-readobj llc` → `EXIT=0`（`MCTargetOptions.h` 共享头变更触发约 380 TU 重编，符合预期）。
2. **选项生效**（`llvm-mc -triple=dadao -multiple-to-single -filetype=obj` EXIT=0，真实 `llvm-objdump -d`，**助记符不变**）：
   ```
   ldm.o {rd8:rd10}, [rb2, rd1]   → 38 20 20 41  ldm.o {rd8}, [rb2, rd1]
                                     59 04 00 08  add.si rd1, 8
                                     38 24 20 41  ldm.o {rd9}, [rb2, rd1]
                                     59 04 00 08  add.si rd1, 8
                                     38 28 20 41  ldm.o {rd10}, [rb2, rd1]
                                     59 07 ff f0  add.si rd1, -16
   stm.b {rd8:rd9}, [rb3, rd2]    → stm.b {rd8}, [rb3, rd2] / add.si rd2, 1 / stm.b {rd9}, [rb3, rd2] / add.si rd2, -1
   ldm.ub {rd8:rd10}, [rb2, rd1]  → add.si rd1, 1（宽度 1）… 末尾 add.si rd1, -2
   ldm.o {rb8:rb10}, [rb2, rd1]   → RB 目的：add.si rd1, 8 … 末尾 add.si rd1, -16
   ra2rd {rd8:rd10}, {ra1:ra3}    → ra2rd {rd8}, {ra1} / {rd9},{ra2} / {rd10},{ra3}
   rd2rd {rd8:rd10}, {rd2:rd4}    → 3× rd2rd {rdi}, {rd(2+i)}
   ft2fo {rf4:rf6}, {rf8:rf10}    → 3× ft2fo {rfi}, {rf(8+i)}
   ```
   （另测 RB/RA/RF 目的 `ldm.o/stm.o/ldm.t/stm.t`、`ut2ft`/`ft2it`/`rf2rd`/`rd2ra` 等混合 bank 均正确；证据脚本逐条精确比对序列。）
3. **默认不变**（不加选项）：多寄存器探测 `ldm.o {rd8:rd10},[rb0,rd1] / ldm.ub {rd8:rd10},[rb0,rd1] / ra2rd {rd8:rd10},{ra1:ra3} / ft2fo {rf4:rf6},{rf8:rf10}` 的 `.text` 字节 = `382000432820004340b8804344044203`——与本任务**改动前**同源预探测（任务开始时真实运行旧二进制）逐字节一致，且与**手算编码** `word=(op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd` 独立吻合。`count=1` 时即使开启选项也保持原样（`ldm.o {rd8}, [rb2, rd1]` → `38 20 20 41`）。
4. **选项可识别**：`llvm-mc --help` 含 `--multiple-to-single`（`...  - DADAO: convert multi-register instructions to a series of single-register instructions (same mnemonic)`）；未知选项仍 `Unknown command line argument`（EXIT=1）。
5. **lit**：新增 3 文件 `llvm-lit` → `Passed: 3 (100.00%)`；`make check-lit` → `Passed: 49 (100.00%)`（46→49，无回归）；`make check` → `repository checks: PASS` EXIT=0；`make test-codegen` → `Results: 15/15 passed, 0 failed`。
6. **一键证据**：`.work/log/llvm/LLVM-053t-evidence-run.log` → `RESULT: PASS (0 failures)` EXIT=0（32 项）；`-evidence-inject.log` → `RESULT: PASS (0 failures)` EXIT=0（16 项）：
   - 注入①：`ldmStmElemWidth` 的 `return 8;` → `return 4;`（ldm.o 宽度错）→ `git diff` 非空 → `ninja` 重建 → `inject-ldm-o-width8to4-FAIL`（序列变 `add.si rd1, 4`/`-8`）→ `git checkout` 还原（diff 空、md5 一致）+ 重建 → `restore-green`。
   - 注入②：orri 源寄存器不推进（`SrcFirst.id() + I` → `SrcFirst.id()`）→ 序列变全 `{ra1}` → `FAIL` → 还原+重建 → 回绿。
7. **补丁/源态**：`check-patch-tree` → `85 patches OK`；`check-source-state` → `llvm-project: OK HEAD=15c8bd3f8151 count=1 clean=True`。
8. **reloc/fixup 坑预防（5 条）**：本展开只产生寄存器操作数与小型立即数（`ldm/stm` 的 `immu6`、`add.si` 的 `imms18`），**不涉及符号/重定位**——不发任何 fixup；`W≤8`、`W*(N-1)≤496`，恒在 `imms18` 范围内（坑⑤「大常量折入受限字段」不适用）。展开的每条真实指令经 `matchAndEmitInstruction` 回灌，复用既有匹配/fixup 设施。

**新发现/坑**：
- **目标库里的 `cl::opt` 在 `llvm-mc --help` 中不可见**：`llvm-mc.cpp` 调 `cl::HideUnrelatedOptions({&MCCategory, &getColorCategory()})`，凡类别不在白名单者（含无类别、乃至 `lib/MC` 的 `-mc-relax-all`）都被置 `ReallyHidden`，`--help`/`--help-hidden` 均不显示。故 `-multiple-to-single` **必须**注册在 `llvm-mc.cpp` 且 `cl::cat(MCCategory)`；AsmParser 侧经 `MCTargetAsmParser::getTargetOptions()`（→`MCContext`→`MCAsmInfo`，由 `createMCAsmInfo` 收到 llvm-mc 的 `MCOptions`）读取 `MCTargetOptions::DADAOMultipleToSingle`。`MCTargetOptions` 本就有 `X86*`/`PPC*` 目标专属字段，属既有范式。
- **展开范式溯源**：与参考实现 GAS `tc-dadao.c`（`-multiple-to-single`）一致——`ldm/stm` 用「推进偏移寄存器 + 末尾还原」逐元素展开；v5 用真实指令 **`add.si rd, imms18`**（riii，64 位自增）做推进/还原（旧 GAS 用 `add.ird` 一类旧码）。**元素宽度按助记符后缀**取（b/ub/sb=1、w/uw/sw=2、t/ut/st=4、o=8）；GAS 的 `1<<(op&3)` 对 `.sb`/`.o` 会取错宽度，未照搬。
- **orri 展开范围**：`-multiple-to-single` 覆盖 8 条寄存器复制（`ra2rd`/`rb2rb`/`rb2rd`/`rd2ra`/`rd2rb`/`rd2rd`/`rd2rf`/`rf2rd`）+ 20 条 FP 格式转换 = 28 条（任务书 8+20）。`ftcls`/`focls`（classify，亦 orri 两组）**有意排除**（不在 8+20 内）；`ftroot`/`foroot` 不在内（其 immu6 是根阶 n 而非元素个数）。
- **自审发现的第 4 类不可安全展开情形**：`ldm.*` 的**基址落在被写入的目的区间内**时（仅 `ldm.o-rb` 可能，ISA 允许该写法且规定按原始基址算地址），逐元素写入会覆盖后续元素要读的基址 → 已**报错拒绝**（`stm.*` 源只读，不受限，仍放行）。此外原型还有「`rb0` 基址」「偏移寄存器 `rd0`」「偏移寄存器落在被访问区间内」三类拒绝（用户裁定）。
- **语义代价（既有范式固有）**：推进/还原是对偏移寄存器的**临时改写**，非原子——若某条展开指令中途 fault（如 MALIGN），偏移寄存器会停留在被改写的值且末尾还原不执行。此为 GAS 同款范式的固有性质，经用户认可采用。
- **用户裁定原文**（`AGENTS.md` 子代理硬约束 #9）：
  - 问 `ldm.*`/`stm.*` 展开方式（A 用 add.si 推进+还原）：**「可以用add.si推进并恢复，但是要注意，基址不能是rb0，否则需要每次重新计算偏移」**。
  - 问 `rb0` 基址如何处理：**「报错拒绝 rb0 基址 (推荐)」**。
  - 问偏移寄存器 `rd0` / 落在被访问区间如何处理：**「一并报错拒绝 (推荐)」**。

**遗留问题**：
- **临时改写偏移寄存器的 fault 原子性**：展开中途异常会使偏移寄存器停在中间值（见上「语义代价」）；属经用户认可的范式固有性质，非缺陷，登记备查。
- **选项对所有 target 可见**：`-multiple-to-single` 注册在 `llvm-mc` 工具层，非 DADAO triple 下被静默忽略（其它 target 不读该字段）；无害，登记备查。
- 其余：无；无未修 finding。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：对本任务增量（3 文件：`DADAOAsmParser.cpp` 的 `expandMultiRegisterInstruction`/`isMultiToSingleOrriMnemonic`/`ldmStmElemWidth`/hook；`MCTargetOptions.h` 新字段；`llvm-mc.cpp` 选项注册与传值）逐行审查；3 个 lit 文件逐条核 FAIL 路径；证据脚本逐条核断言可失败性与 `--inject` 有效性；对照 `spec/DADAO-11 §汇编器选项`、`contract-asm §8`、`contract-isa §3.1.2/§3.2/§4`、`ADR-0015`（rb0 基址语义）与验收 1–6。

**判决**：实现完成，验收 1–6 均有真实输出支撑；自审发现并修复 1 处正确性缺陷（F1）；无未修阻断项 → 状态置 `待验收`。

**逐行审查要点**：
- **展开语义**：`ldm.*`/`stm.*` 取组首寄存器 + `GroupCount`，逐元素发单寄存器同助记符指令，元素间 `add.si rc, +W`、末尾 `add.si rc, -(N-1)*W`；宽度取自助记符后缀（与 `AD9` 元素宽度一致）；`orri`（8+20）逐元素 `{dst+i},{src+i}`（count=1）。展开指令全部回灌 `matchAndEmitInstruction`，复用既有合法性检查（实测 counts-differ/overlap/overflow/FP-overlap 在开选项时**仍先于展开报错**，与关选项逐条一致）。
- **边界/未覆盖输入**：`count==1` 不展开（原样）；非白名单助记符不展开；未知 `ldm.zz` 经 matcher 报 `unrecognized`；跨 bank 畸形范围（如 `{rd63:rb0}`）在 `parseRegGroup` 即被拒（`register range too large`/`end < start`），展开不可达；`W==0` 仅未知后缀可触发且失败于 `unrecognized`。
- **寄存器安全**：`add.si` 目的必为 GPRD（`rc` 由 rrri 的 `GPRD:$rc` 保证）；拒绝 4 类不安全改写（rb0 基址 / rd0 偏移 / 偏移∈被访问区间 / `ldm.*` 基址∈被写目的区间）。
- **防造假**：留证命令一律 `cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`；脚本无 `tee`；默认字节表由编码式手算（非从 llvm-mc 反推）并与**改动前**真实运行输出比对；`--inject` 校验 `git diff --name-only` 非空 + md5 还原 + 重建后回绿。
- **范围/纪律**：仅改 3 个组件源文件；未手改 `components/**/patches/**`（`make_patch.py` 导出，新增 2 份、`series` 51→53）；临时目录 `/tmp/opencode/LLVM-053t/`；未提交 git；未改既有函数签名、未引入外部依赖。`MCTargetOptions.h` 属共享头（重编面大）但为**最小可行接线**（选项须在 llvm-mc 工具层可见、并传至 target AsmParser），沿用既有目标专属字段范式。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `ldm.o {rb8:rb10}, [rb9, rd1]`（基址∈被写目的区间）展开会导致后续元素读到被覆盖的基址——语义不等价 | ✅已修 | `expandMultiRegisterInstruction` 的 `ldm.*` 分支新增「基址∈目的区间」`Error` 拒绝（`stm.*` 源只读，仍放行） | `-multiple-to-single`：`ldm.o {rb8:rb10}, [rb9, rd1]` → EXIT=1 + `base register is inside the written destination register range`；默认（关选项）EXIT=0；`stm.o {rb8:rb10}, [rb9, rd1]` 开选项 EXIT=0 且展开正确（`3b 20 90 41 / add.si …`）；lit `multiple-to-single-reject.s` 新增 `BASEINRANGE` RUN；证据 `reject-ldm-base-in-dest`/`stm-base-in-source-allowed` PASS |
| F2 函数注释写「Three cases」却列举四条拒绝 | ✅已修 | 注释 `Three` → `Four` 并补第 4 条说明 | `grep` 注释一致；重编 EXIT=0 |
| F3 跨 bank 畸形范围（`{rd63:rb0}`）在展开时可能混出 RD/RB 变体 | ❌不修（既有、不可达） | 无（`parseRegGroup` 已拒） | `ldm.o {rd63:rb0}, [rb2, rd1]` → `error: register range too large`（开/关选项一致）；`{rb63:ra0}`/`{ra63:rf0}` → `end < start` |
| F4 `ldmStmElemWidth` 对未知后缀返回 0（潜在静默 no-op） | ❌不修（安全失败） | 无 | `ldm.zz {rd8:rd10}, [rb2, rd1]` → `error: unrecognized instruction mnemonic`（EXIT=1） |

**自验命令退出码**：`run.sh`（正常）EXIT=0（32/32）；`run.sh --inject` EXIT=0（16/16）；`make check` EXIT=0；`make check-lit` EXIT=0（49/49）；`make test-codegen` EXIT=0（15/15）；`check-patch-tree` EXIT=0（85 patches OK）；`check-source-state` EXIT=0（clean, count=1）。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理
**审查时间**：2026-10-06
**审查范围**：证据脚本 `.work/evidence/LLVM-053t/run.sh` 审核、独立重跑全部验收项、独立注入测试、独立复核（`llvm-mc`/`llvm-objdump` 真实输出）、门控全量验证。

---

##### 一、证据脚本审核

| 检查项 | 结果 | 说明 |
|---|---|---|
| FAIL 路径可达 | ✅ | `check()` 在 `$4 -ne 0` 时打印 `[FAIL]` 并 `FAILS++`；`seq_check` 用 `[ "$got" = "$exp" ]` 字符串比对；`reject_msg` 用 `grep -q` 匹配错误信息——均有真实 FAIL 路径 |
| 恒真断言 | ✅ 无 | 每条 check 的 rc 来自真实命令退出码或条件表达式，无 `check(name, True)` 等恒真结构 |
| `tee` 吞退出码 | ✅ 无 | 脚本用 `> log 2>&1` + `rc=$?` 捕获退出码，末尾 `[ "$FAILS" -eq 0 ]` 直接退出，无管道 |
| 注入非空 | ✅ | 两轮注入（`ldmStmElemWidth` `return 8→4`；orri `SrcFirst.id()+I→SrcFirst.id()`）均用 `sed -i` 改动源码 + `git diff --name-only` 验证非空 |
| 注入可还原 | ✅ | `git checkout -- $PARSER` + md5 比对 + 重建 + 回绿 |
| 结尾无 tee | ✅ | `[ "$FAILS" -eq 0 ]` 直接退出 |

**结论**：证据脚本合格，不代写。

---

##### 二、独立重跑（正常模式）

命令：`bash .work/evidence/LLVM-053t/run.sh > evidence-run.log 2>&1; echo "EXIT=$?"`

```
[PASS] build | expected: ninja EXIT=0 | actual: see LLVM-053t-evidence-build.log | rc=0
[PASS] help-shows-option | expected: >=1 occurrence of -multiple-to-single | actual: 1 | rc=0
[PASS] unknown-option-rejected | expected: non-zero + Unknown command line argument | actual: rc=1 llvm-mc: Unknown command line argument '-no-such-option-053t'. | rc=0
[PASS] ldm-o-assemble | expected: llvm-mc -multiple-to-single EXIT=0 | actual: rc=0 | rc=0
[PASS] ldm-o-expanded | expected: exact single-register sequence | actual: ldm.o {rd8}, [rb2, rd1] / add.si rd1, 8 / ldm.o {rd9}, [rb2, rd1] / add.si rd1, 8 / ldm.o {rd10}, [rb2, rd1] / add.si rd1, -16 | rc=0
[PASS] stm-b-assemble | rc=0
[PASS] stm-b-expanded | actual: stm.b {rd8}, [rb3, rd2] / add.si rd2, 1 / stm.b {rd9}, [rb3, rd2] / add.si rd2, -1 | rc=0
[PASS] ldm-ub-w1-assemble | rc=0
[PASS] ldm-ub-w1-expanded | actual: ldm.ub {rd8}, [rb2, rd1] / add.si rd1, 1 / ldm.ub {rd9}, [rb2, rd1] / add.si rd1, 1 / ldm.ub {rd10}, [rb2, rd1] / add.si rd1, -2 | rc=0
[PASS] ldm-o-rb-assemble | rc=0
[PASS] ldm-o-rb-expanded | actual: ldm.o {rb8}, [rb2, rd1] / add.si rd1, 8 / ldm.o {rb9}, [rb2, rd1] / add.si rd1, 8 / ldm.o {rb10}, [rb2, rd1] / add.si rd1, -16 | rc=0
[PASS] orri-ra2rd-expanded | actual: ra2rd {rd8}, {ra1} / ra2rd {rd9}, {ra2} / ra2rd {rd10}, {ra3} | rc=0
[PASS] orri-rd2rd-expanded | actual: rd2rd {rd8}, {rd2} / rd2rd {rd9}, {rd3} / rd2rd {rd10}, {rd4} | rc=0
[PASS] fp-ft2fo-expanded | actual: ft2fo {rf4}, {rf8} / ft2fo {rf5}, {rf9} / ft2fo {rf6}, {rf10} | rc=0
[PASS] default-unchanged | expected: 382000432820004340b8804344044203 (hand-derived) | actual: 382000432820004340b8804344044203 | rc=0
[PASS] count1-unchanged | expected: ldm.o {rd8}, [rb2, rd1] | actual: ldm.o {rd8}, [rb2, rd1] | rc=0
[PASS] reject-rb0-base | actual: rc=1 error: base register rb0 is PC-relative | rc=0
[PASS] reject-rd0-offset | actual: rc=1 error: offset register rd0 cannot be advanced | rc=0
[PASS] reject-offset-in-range | actual: rc=1 error: offset register is inside the accessed register range | rc=0
[PASS] reject-stm-offset-in-src | actual: rc=1 error: offset register is inside the accessed register range | rc=0
[PASS] reject-ldm-base-in-dest | actual: rc=1 error: base register is inside the written destination register range | rc=0
[PASS] stm-base-in-source-allowed | actual: rc=0 | rc=0
[PASS] default-accepts-rb0-base | actual: rc=0 | rc=0
[PASS] lit-new | 3/3 passed | rc=0
[PASS] check-lit | 49/49 passed | rc=0
[PASS] test-codegen | 15/15 passed | rc=0
[PASS] check-patch-tree | 85 patches OK | rc=0
[PASS] check-source-state | llvm-project OK HEAD=15c8bd3f8151 count=1 clean=True | rc=0
RESULT: PASS (0 failures)
EXIT=0
```

**32 项全 PASS，EXIT=0。** 与 engineer 完成区一致。

---

##### 三、独立注入测试

**注入方式**（与 engineer 的两轮不同）：
- engineer 注入①：`ldmStmElemWidth` `return 8` → `return 4`（宽度错）
- engineer 注入①：orri `SrcFirst.id()+I` → `SrcFirst.id()`（源不推进）
- **reviewer 注入**：还原 `add.si` 的符号翻转——`-static_cast<int64_t>(W)` → `static_cast<int64_t>(W)`（restore 值从 `-(N-1)*W` 变为 `+(N-1)*W`，使 rd1 多加 2×W 而非恢复原值）

**注入证据**：
```
$ sed -i 's/-static_cast<int64_t>(W)/static_cast<int64_t>(W)/' DADAOAsmParser.cpp
$ git diff --stat
 llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

**注入后构建**：`ninja -j8` EXIT=0 ✅

**注入后反汇编**（`ldm.o {rd8:rd10}, [rb2, rd1]`）：
```
0000000000000000: 38 20 20 41  ldm.o {rd8}, [rb2, rd1]
0000000000000004: 59 04 00 08  add.si rd1, 8
0000000000000008: 38 24 20 41  ldm.o {rd9}, [rb2, rd1]
000000000000000c: 59 04 00 08  add.si rd1, 8
0000000000000010: 38 28 20 41  ldm.o {rd10}, [rb2, rd1]
0000000000000014: 59 04 00 10  add.si rd1, 16      ← 应为 -16，注入有效
```

**注入后证据脚本**：`EXIT=1`（4 个 FAIL：`ldm-o-expanded`、`stm-b-expanded`、`ldm-ub-w1-expanded`、`ldm-o-rb-expanded`；另有 `lit-new` 2/3 FAIL、`check-lit` 48/49 FAIL、`check-patch-tree` FAIL、`check-source-state` FAIL）

**还原**：
```
$ git checkout -- llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
$ git diff --stat          # 空
$ md5sum DADAOAsmParser.cpp  # c263f10ea4a9b8a79632fb32dd90357a（与注入前一致）
```

**还原后重建**：`ninja -j8` EXIT=0 ✅

**还原后证据脚本**：`EXIT=0`，33 PASS / 0 FAIL ✅

---

##### 四、独立复核

| 验收项 | 真实输出 | 判定 |
|---|---|---|
| **选项可识别** | `llvm-mc --help` 含 `--multiple-to-single  - DADAO: convert multi-register instructions to a series of single-register instructions (same mnemonic)` | ✅ |
| **未知选项拒绝** | `llvm-mc -triple=dadao -bogus-opt-xyz` → EXIT=1 + `Unknown command line argument` | ✅ |
| **选项生效** | `ldm.o/stm.b/ldm.ub/ldm.o-rb` 展开为单寄存器序列 + `add.si` 推进/还原；`ra2rd/rd2rd/ft2fo` 逐元素展开；助记符均不变 | ✅ |
| **默认不变** | 不加选项时 `.text` hex = `382000432820004340b8804344044203`（与手算编码一致） | ✅ |
| **count=1 不展开** | `ldm.o {rd8}, [rb2, rd1]` 保持原样 | ✅ |
| **4 类拒绝** | `rb0` 基址 / `rd0` 偏移 / 偏移∈区间 / `ldm.*` 基址∈目的区间 → EXIT=1 + 对应错误信息 | ✅ |
| **stm 基址在源内放行** | `stm.o {rb8:rb10}, [rb9, rd1]` EXIT=0 + 正确展开 | ✅ |
| **默认接受 rb0** | 不加选项时 `ldm.o {rd8:rd10}, [rb0, rd1]` EXIT=0 | ✅ |
| **共享文件最小** | `MCTargetOptions.h` +5 行（`bool DADAOMultipleToSingle = false;`，沿用 `X86*`/`PPC*` 范式）；`llvm-mc.cpp` +10 行（`cl::opt` 注册 + 赋值）；默认 `false` 不影响其它 target | ✅ |
| **check-lit** | 49/49 passed（含 3 个新增） | ✅ |
| **test-codegen** | 15/15 passed | ✅ |
| **check-patch-tree** | 85 patches OK | ✅ |
| **check-source-state** | llvm-project OK HEAD=15c8bd3f8151 count=1 clean=True | ✅ |
| **make check** | 全部 PASS（80 项接口核对 + 门控） | ✅ |

---

##### 五、发现/遗留判定

| 项目 | 判定 | 理由 |
|---|---|---|
| **4 类拒绝（尤其 `base∈dest` 的 `ldm.o {rb8:rb10}, [rb9, rd1]`）** | ✅ 正确必要 | ISA 规定按原始基址算地址，但逐元素展开时基址被后续写入覆盖→语义不等价；`stm.*` 源只读不受限，放行正确 |
| **临时改写偏移寄存器的 fault 原子性** | ⚠️ 非阻塞 | GAS 同款范式的固有性质；展开中途 fault 时偏移寄存器停在中间值——经用户认可采用，属设计权衡非缺陷 |
| **选项对所有 target 可见、非 DADAO 静默忽略** | ⚠️ 非阻塞 | `cl::opt` 注册在 `llvm-mc` 工具层（因 `HideUnrelatedOptions` 白名单机制必须如此），默认 `false`，其它 target 不读 `DADAOMultipleToSingle` 字段，无害 |

---

##### 六、判决

**Accepted**

验收命令块在 reviewer 独立重跑下全部通过（32/32 EXIT=0）；独立注入确认脚本能检测还原逻辑错误（`add.si` 符号翻转→4 个展开 FAIL + lit/门控回归→还原+重建→回绿）；共享文件改动最小且默认关闭；`make check` / `check-lit`(49/49) / `test-codegen`(15/15) / `check-patch-tree`(85) / `check-source-state`(clean) 全绿。无阻断项。
