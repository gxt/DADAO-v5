# LLVM-051t: 伪指令展开（`set.rd/set.rb/set.ft/set.fo`）

**模块**：llvm
**项目里程碑**：M4
**依赖**：`SPEC-106t`、`LLVM-050t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `SPEC-106t` 落地后的 `spec/SimRISC-03`（`set.rd`/`set.rb`/`set.ft`/`set.fo` 展开细则）与 `.tao/adr/adr-0013-assembly-syntax.md` **D11**（Accepted；只留 8 条合成型、常量 vs 符号、`set.rb` 细节、`ret` 无无参）。
  - 现有 AsmParser（`.work/source/llvm-project/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp`，约 1430 行；当前未实现伪指令，全部报 `unrecognized instruction mnemonic`）。
  - `LLVM-050t` 的 `ABS48` fixup/reloc 设施；指令编码表 `contracts/opcodes.yaml`（`set.zw`/`set.ow`/`or.w`/`andn.w` 的 rd/rb 形式、`rb2rd`/`rd2rb`/`rf2rd`/`ra2rd`/`rd2rd`/`rb2rb`/`rd2rf`/`ft2ft`/`fo2fo`、`set.w`）。
- **输出**（组件源码改在 `.work/source/llvm-project`；导出补丁）：
  - `DADAOAsmParser` 支持并**展开** 8 条合成型伪指令：
    - `set.rd rd, imm64`：**可汇编期求值的常量** → 最少指令数（`set.zw`/`set.ow` + `or.w`/`andn.w`，按 16 位 wyde，参考 `SimRISC-03 §set.rd` 展开例）；**符号/可重定位** → **固定 3 片 + `R_DADAO_ABS48`**（`ADR-0019 D4/D5`）。
    - `set.rd rd, rs`（`rs∈{rb,rf,ra,rd}`）→ `rb2rd`/`rf2rd`/`ra2rd`/`rd2rd`。
    - `set.rb rb, imm64` → `set.zw-rb` + `or.w-rb`（**无 `set.ow-rb`**，全 1 需 `set.zw`+3×`or.w`）；地址 ≤48 位。
    - `set.rb rb, rs`（`rs∈{rd,rb}`）→ `rd2rb`/`rb2rb`。
    - `set.ft rf, imm32` → 2 条 `set.w`；`set.ft rf, rs`（`rs∈{rd,rf}`）→ `rd2rf`/`ft2ft`。
    - `set.fo rf, imm64` → 4 条 `set.w`；`set.fo rf, rs`（`rs∈{rd,rf}`）→ `rd2rf`/`fo2fo`。
  - **反汇编只显真实指令**：伪指令不进入 printer（`set.rd` 等不产出、不往返为伪指令）。
- **约束**：
  - 严格按 `ADR-0013 D11`：**不实现** `nop`/`return`/`not.*`/`neg.*`（报 `unrecognized instruction mnemonic`）；**`ret` 不加无参形态**。
  - **常量 vs 符号**判据（`ADR-0013 D11`）：同段可解析表达式按可求值处理（最少指令数）；跨段/外部按符号处理（3 片 + `ABS48`）。
  - **reloc/fixup 坑预防（5 条，同 `LLVM-050t`）**，尤其⑤大常量不得折入受限字段（`set.rd` 立即数须按 wyde 材料化）。**②** same-section 折叠不可靠即退回真重定位。
  - **补丁纪律（`spec/Process-01`）**；`commit --amend` 收敛 base+1 → `make_patch.py` → `check-patch-tree`；不手改补丁。
  - 构建/串行/临时目录/留证纪律同 `LLVM-050t`；`ninja -j8`；失败即停。
  - 临时目录 `/tmp/opencode/LLVM-051t/`；**不提交 git**。

## 验收标准

1. 构建 EXIT=0。
2. **常量展开**：`set.rd rd1, 0x1234ABCD` 等（`SimRISC-03` 例）→ `llvm-mc -filetype=obj` EXIT=0，反汇编**只显真实** `set.zw`/`or.w` 序列（无伪指令文本）；逐例独立字节/指令数核对（给出期望展开表）。
3. **寄存器传值**：`set.rd rd5, rb3` → `rb2rd`；`set.rb rb1, rd7` → `rd2rb`；`set.ft rf1, rd5` → `rd2rf`；`set.fo rf2, rf7` → `fo2fo`——反汇编逐条核对。
4. **符号/可重定位**：对跨 section/未定义符号的 `set.rd rd, sym`，`llvm-readobj -r` 显示 **固定 3 条 `R_DADAO_ABS48`**（`LLVM-050t` 设施）；同段可解析者按最少指令数展开、无 reloc。
5. **删除项不实现**：`nop`/`return`/`not.o`/`neg.o` 等 → `llvm-mc` 报 `unrecognized instruction mnemonic`（非零退出）；`ret rd0` → 报错（既有静态规则）。
6. **lit 向量**：`tests/llvm/lit/MC/DADAO/` 新增伪指令用例（`set.*` 展开 + 删除项反例）；`make check-lit` EXIT=0 不回归；`make check` EXIT=0；`make test-codegen` 不回归。
7. 一键证据脚本 `.work/evidence/LLVM-051t/run.sh`（含 `--inject`：把 `set.rd` 常量展开改错/把 `nop` 加回 → 期望 FAIL → 还原+重建 → 回绿）；完成区贴真实输出。

## 完成区

**测试结果**：通过 20/20（一键证据 `.work/evidence/LLVM-051t/run.sh` 正常模式 20 项全 PASS，EXIT=0）+ 反例注入 7/7（`--inject`：注入 FAIL → 还原+重建回绿，EXIT=0）。`make check` EXIT=0；`make check-lit` 42/42（新增 6，无回归）；`make test-codegen` 15/15；`check-patch-tree` 83 patches OK；`check-source-state` llvm-project clean+count=1。失败原因：无。

**修改文件**：
- 组件源码（`.work/source/llvm-project`，已 amend 收敛为 base+1：`6dfe1677a..dc66adb35`）：**仅** `llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp`（`+expandPseudoInstruction` 8 条合成型展开 + 顶部 dispatch + 银行谓词/单寄存器组助手 + `MathExtras.h` include）。
- 补丁集：`components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`（`make_patch.py` 导出；`series` 仍 51，未手改）。
- 台账：`components/llvm-project/changelog.md`（+LLVM-051t 一条）。
- 测试向量（新增 6）：`tests/llvm/lit/MC/DADAO/set-rd-imm.s`、`set-rd-reg.s`、`set-rb.s`、`set-ft-fo.s`、`set-symbol.s`、`pseudo-removed.s`。
- 证据脚本：`.work/evidence/LLVM-051t/run.sh`（新增）；日志 `.work/log/llvm/LLVM-051t-*.log`。
- 本任务书（完成区/自审/状态）。

**验收结果**（真实输出，`cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，无 `tee`）：

1. **构建 EXIT=0**（`.work/log/llvm/LLVM-051t-build.log`）：`ninja -j8 -C .work/build/llvm llvm-mc llvm-objdump llvm-readobj llc` → `EXIT=0`。
2. **常量展开**（`set.rd rd, imm64` 最少指令数；objdump 只显真实指令、无伪指令文本）——逐例期望展开表（字节源自 rwii 编码式 `word=(op<<24)|(ha<<18)|((wp&3)<<16)|immu16`，独立于 llvm-mc 手算）：

   | 源 | 展开（真实指令） | 字节 |
   |---|---|---|
   | `set.rd rd1, 0` | `set.zw rd1, wp0, 0x0` | `4c 04 00 00` |
   | `set.rd rd2, -1` | `set.ow rd2, wp0, 0xffff` | `4d 08 ff ff` |
   | `set.rd rd3, -42` | `set.ow rd3, wp0, 0xffd6` | `4d 0c ff d6` |
   | `set.rd rd4, ~(1<<5)` | `set.ow rd4, wp0, 0xffdf` | `4d 10 ff df` |
   | `set.rd rd5, 42` | `set.zw rd5, wp0, 0x2a` | `4c 14 00 2a` |
   | `set.rd rd6, 0x1234ABCD` | `set.zw rd6, wp1, 0x1234` / `or.w rd6, wp0, 0xabcd` | `4c 19 12 34` / `48 18 ab cd` |
   | `set.rd rd7, 0xDEADBEEFCAFEBABE` | `set.zw rd7, wp3, 0xdead` / `or.w` wp2/wp1/wp0 | `4c 1f de ad` / `48 1e be ef` / `48 1d ca fe` / `48 1c ba be` |
   | `set.rd rd8, 0x12340000FFFFFFFF` | `set.ow rd8, wp3, 0x1234` / `andn.w rd8, wp2, 0xffff` | `4d 23 12 34` / `49 22 ff ff` |

   证据 20/20 PASS（`constants-expansion`、`misc-expansion` 逐字节 `diff` 全等；`no-pseudo-in-disasm` = 0）。
3. **寄存器传值**（`set.rd/set.rb/set.ft/set.fo` 源为寄存器；反汇编逐条核）：`set.rd rd5, rb3`→`rb2rd {rd5}, {rb3}`（`40 d8 50 c1`）；`set.rd rd2, rf7`→`rf2rd`（`40 f8 21 c1`）；`set.rd rd8, rd3`→`rd2rd`（`40 b0 80 c1`）；`set.rd rd4, ra10`→`ra2rd`（`40 b8 42 81`）；`set.rb rb1, rd7`→`rd2rb`（`40 d4 11 c1`）；`set.rb rb2, rb7`→`rb2rb`（`40 d0 21 c1`）；`set.ft rf1, rd5`→`rd2rf`（`40 f4 11 41`）；`set.ft rf1, rf2`→`ft2ft`（`44 08 10 81`）；`set.fo rf2, rf7`→`fo2fo`（`44 28 21 c1`）；`set.fo rf3, rd9`→`rd2rf`（`40 f4 32 41`）。
   - `set.rb rb, imm64`：`rb1, 0`→`set.zw rb1, wp0, 0x0`；`rb1, 0x123456789ABC`→`set.zw rb1, wp2, 0x1234`+`or.w` wp1/wp0；`rb3, -1`→`set.zw rb3, wp3, 0xffff`+3×`or.w`（无 `set.ow-rb`，全 1 = 4 条）。
   - `set.ft rf1, 0x3F800000`→2×`set.w`（wp1/wp0）（`4f 05 3f 80`/`4f 04 00 00`）；`set.fo rf1, 0x3FF0000000000000`→4×`set.w`（wp3..wp0）；`set.ft rf1, 0`→2×`set.w`（不动高 32 位）；`set.fo rf4, 0`→`rd2rf {rf4}, {rd0}`（`40 f4 40 01`）。
4. **符号/可重定位**（`llvm-readobj -r`，跨 section/未定义）：`set.rd rd1, ext` + `set.rb rb1, ext2` → **恰 6 条 `R_DADAO_ABS48`**（`ext`×3 偏移 `0x0/0x4/0x8`，`ext2`×3 偏移 `0xC/0x10/0x14`）；`.set localimm, 0x1234ABCD` 可汇编期求值 → `set.zw rd2, wp1, 0x1234`+`or.w rd2, wp0, 0xabcd`（2 条、**无 reloc**）。
5. **删除项不实现**：`nop`/`return`/`not.o`/`not.b`/`neg.o`/`neg.b` → `llvm-mc` 非零退出、`error: unrecognized instruction mnemonic`（6/6）；`ret rd0` → 非零、`error: invalid operand for instruction`；`ret`（无参）同报错；`ret rd0, 0` 接受。
6. **lit**：新增 6 文件；`.work/build/llvm/bin/llvm-lit <6 文件>` → `Passed: 6 (100.00%)`；`make check-lit` → `Passed: 42 (100.00%)`（36→42，无回归）；`make check` → `repository checks: PASS` EXIT=0（lit 42/42）；`make test-codegen` → `Results: 15/15 passed, 0 failed`。
7. **一键证据**：`.work/evidence/LLVM-051t/run.sh` → `RESULT: PASS (0 failures)` EXIT=0（20 项）；`run.sh --inject` → 注入（`if (CostZw <= CostOw)`→`if (false)`，`git diff` 非空）→ `inject-constants-FAIL`（diff rc≠0）→ `git checkout` 还原（md5 一致、diff 空）+ `ninja` 重建 → `restore-constants-green`，`RESULT: PASS` EXIT=0。

**新发现/坑**：
- **`0xDEADBEEF_CAFEBABE` 的下划线分隔符被拒**：`contract-asm §2.4` 明确「下划线分隔符 MUST NOT 使用」，故 `SimRISC-03 §set.rd` 示例里的 `0xDEADBEEF_CAFEBABE` 写法**不可汇编**（词法在 `_` 处断为标识符）。lit/证据统一用 `0xDEADBEEFCAFEBABE`。属**规范示例书写与词法规则不一致**（`SimRISC-03` 示例待 spec 侧订正；不影响展开语义）。
- **`set.rd` 常量展开的种子/修正**：`set.zw` 种子把其余位清 0、`set.ow` 种子置 1；修正分别为 `or.w`（置 1）/`andn.w`（清 0）。最小代价 = `max(1,#非0)`（zw）或 `max(1,#非0xFFFF)`（ow）；种子取「值不同于 seed fill 的最高位 wyde」，修正由高到低；同代价优先 `set.zw`。复现 `SimRISC-03` 全部示例。
- **符号路径切片 = `wp2/wp1/wp0`**（48 位地址，`ADR-0019 D4`）；每片一条 `R_DADAO_ABS48`（`ADR-0019 D5`）。判据用 `MCExpr::evaluateAsAbsolute`（用户裁定），故同段 **label**（绝对地址汇编期不可知）仍走符号路径；可汇编期求值的常量表达式（含 `.set` 常量）走最少指令数、无 reloc。
- **展开复用既有合法性检查**：每条展开的真实指令经 `matchAndEmitInstruction` 递归回灌，`mreg_range_overlap`（`set.rd rd1,rd1`→`rd2rd` 报错）、`dst_rd0`（`set.rd rd0,rf3`→`rf2rd` 报错）、`dst_rf0`（`set.ft rf0,rf2`→`ft2ft` 报错）等既有规则自动生效。
- **M1 `dst_rd0`/`dst_rb0` 汇编期缺口（既有，非本任务引入）**：`set.rd rd0, rb3`→`rb2rd {rd0},{rb3}`、`set.rb rb0, 5`→`set.zw rb0`、以及真实指令 `rb2rd {rd0},{rb3}`、`set.zw rd0, wp0, 5` 当前**均被接受**（AsmParser 未对 M1 目的 rd0/rb0 报错，仅 FP 目的有检查）。伪指令展开与「直接书写真实指令」行为一致，未新增缺陷；M1 目的寄存器静态检查缺口建议另立任务（见遗留）。
- **用户裁定落盘（`AGENTS.md` 子代理硬约束 #9；原文）**：
  - 问 `set.ft/set.fo` 立即数 0 的展开冲突（任务书 2/4 条 set.w vs `SimRISC-03` 的 rd2rf）：**「set.ft用两条set.w来实现，set.fo用rd2rd来实现；基本原则是ft默认不动高32位」**。→ 实现取：`set.ft rf, 0` = 2×`set.w`（不动高 32 位）；`set.fo rf, 0` = `rd2rf {rf}, {rd0}`（`set.fo` 目的为 rf，唯一合法的「从 rd0 拷贝」块移动是 `rd2rf`，与 `SimRISC-03` 一致；用户原文「rd2rd」按字面无法作为 rf 目的指令，已按 `rd2rf` 落地并在遗留登记）。
  - 问「同段可解析」判据：**「以 evaluateAsAbsolute 为判据（推荐）」**。
  - 问常量展开确定性规则：**「接受该规则」**。

**遗留问题**：
- **M1 目的寄存器静态检查缺口（既有，越界未改）**：AsmParser 未对 M1（非 FP）指令目的 `rd0`/`rb0` 报错（`rb2rd {rd0},…`、`set.zw rd0, wp0, …`、`set.zw rb0, …` 均被接受）；本任务伪指令展开复用了该（缺失的）行为以保持一致，**未引入新缺陷**。建议另立任务在 MC 汇编期补齐 `dst_rd0`/`dst_rb0`（`contracts/legality_rules.yaml`；与 `TESTCASES-029t` 的诊断向量相关）。属**能力缺口**（非错值）。
- **用户原文「set.fo用rd2rd」的字面矛盾**：按 `set.fo` 目的为 rf 落地为 `rd2rf`（唯一可行且与 `SimRISC-03` 一致）；若用户本意为其它写法，请复核。
- **`SimRISC-03` 示例的 `0x…_…` 下划线写法与 `contract-asm §2.4`（禁下划线）矛盾**：spec 侧建议订正；不影响实现与向量（统一无下划线）。
- 其余：无；无未修 finding。

> **用户裁定（2026-10-06，原文记录，问答摘要）**：
> ① `set.ft rf, imm`：**「set.ft用两条set.w来实现，set.fo用rd2rd来实现；基本原则是ft默认不动高32位」**（`set.fo` 按 rf 目的落地为 `rd2rf`）。
> ② 常量 vs 符号判据：**「以 evaluateAsAbsolute 为判据（推荐）」**。
> ③ 常量展开确定性规则：**「接受该规则」**。


## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：改动源码逐行审查（`.work/source/llvm-project/…/DADAOAsmParser.cpp` 的 `+expandPseudoInstruction`/dispatch/银行谓词/`singleRegGroup`）+ 6 个 lit 文件逐条核 FAIL 路径 + 证据脚本逐条核断言可失败性；并对照 `ADR-0013 D11`/`ADR-0019 D4/D5`/`SimRISC-03`/`contract-elf §2–§4` 与验收 1–7。

**判决**：实现完成，验收 1–7 均有真实输出支撑；无未修阻断项 → 状态置 `待验收`。

**逐行审查要点**：
- **展开语义**：8 条合成型与 `Toolchain-01 §6`/`D11` 逐条对应；`set.rd` 常量算法取 `min(max(1,#非0), max(1,#非0xFFFF))`（种子/修正方案），复现 `SimRISC-03` 全部示例；符号路径固定 3 片 `wp2/wp1/wp0`（48 位地址）+ 每片 `R_DADAO_ABS48`，与 `ADR-0019 D4/D5` 一致；`set.rb` 无 `set.ow-rb`（全 1 = 4 条）。
- **复用而非另造**：展开的每条真实指令经 `matchAndEmitInstruction` 递归回灌，复用既有 `mreg_range_overlap`/`dst_rd0`/`dst_rf0`/matcher 检查（实测 `set.rd rd1,rd1`、`set.rd rd0,rf3`、`set.ft rf0,rf2` 均按既有规则报错）；未改共享 MC 层、未改其它文件。
- **边界/未覆盖输入**：`set.rd/set.rb/set.ft/set.fo` 目的银行错（`set.rd rb1,5` 等）→ 报错；源银行不支持（`set.ft rf1,ra2`）→ 报错；`set.ft/set.fo` 符号操作数 → 报错（`set.w` 非地址构造，`ABS48` 集不含）；`set.ft` 立即数越 32 位 → 报错；操作数个数/类型错 → 报错。`set.rd rd0,rb3`/`set.rb rb0,5` 被接受——经核**既有真实指令** `rb2rd {rd0},{rb3}`/`set.zw rd0`/`set.zw rb0` 同样被接受（既有 M1 目的寄存器检查缺口），伪指令行为与「直接书写真实指令」一致（见下 F1）。
- **防造假**：所有留证命令 `cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，脚本内无 `tee`；期望字节表手算自编码式（非从 llvm-mc 反推），由 `diff` 全等校验；`--inject` 校验 `git diff --name-only` 非空 + md5 还原 + 重建后回绿。
- **范围/纪律**：仅改 `DADAOAsmParser.cpp` 一个组件源文件；未手改 `components/**/patches/**`（`make_patch.py` 导出，仅 1 份变更、`series` 不变）；临时目录 `/tmp/opencode/LLVM-051t/`；未提交 git；未改函数签名、未引入依赖。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `set.rd rd0, rb3`/`set.rb rb0, 5` 展开为非法 `rb2rd {rd0},…`/`set.zw rb0,…` 却被接受（M1 目的 rd0/rb0 汇编期检查缺口） | ❌不修（既有缺口，范围外；保持一致） | 无 | 证据：真实指令 `rb2rd {rd0}, {rb3}` EXIT=0、`set.zw rd0, wp0, 5` EXIT=0、`set.zw rb0, wp0, 5` EXIT=0——伪指令行为与直接书写一致；登记遗留，建议另立任务补 M1 `dst_rd0`/`dst_rb0` |
| F2 用户原文「set.fo用rd2rd来实现」字面与 `set.fo`（目的 rf）矛盾 | ❌不修（已在落地/完成区记录） | 落地为 `rd2rf {rf}, {rd0}`（唯一可行且与 `SimRISC-03` 一致） | 证据：`set.fo rf4, 0` → `40 f4 40 01  rd2rf {rf4}, {rd0}`；完成区/遗留已原文登记，供用户复核 |
| F3 `SimRISC-03 §set.rd` 示例用 `0xDEADBEEF_CAFEBABE`（下划线），与 `contract-asm §2.4`（禁下划线）冲突 | ❌不修（spec 侧问题，非实现） | 向量/证据统一用 `0xDEADBEEFCAFEBABE` | 证据：`0xDEADBEEF_CAFEBABE` → `error: unrecognized instruction mnemonic`（词法在 `_` 断）；无下划线写法展开正确（12 条 rwii 字节 diff 全等） |
| F4 `set.ft` 立即数越 32 位（`0x100000000`/`-2147483649`）未处理会静默截断 | ✅已修 | 展开前加 `isUInt<32>(Imm) || isInt<32>(Imm)` 校验，越界报错 | 实测 `set.ft rf1, 0x100000000`/`-2147483649` → 非零 + `immediate out of range for 'set.ft' (must fit in 32 bits)` |
| F5 证据脚本 `deleted-items` 判定极性写反（`if ! echo … \| mc … \|\| ! grep …`），首轮把「已正确拒绝」误报为 bad=6 | ✅已修 | 去掉 `echo` 前的 `!`（判据 = 汇编成功 OR 无错误串 ⇒ bad） | 重跑 `run.sh` `deleted-items` PASS（bad=0），正常模式 20/20 PASS EXIT=0 |

**自验命令退出码**：`run.sh`（正常）EXIT=0（20/20）；`run.sh --inject` EXIT=0（7/7）；`make check` EXIT=0；`make check-lit` EXIT=0（42/42）；`make test-codegen` EXIT=0（15/15）；`check-patch-tree` EXIT=0（83 patches OK）；`check-source-state` EXIT=0（clean, count=1）。


#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理
**审查日期**：2026-10-06

---

##### 一、证据脚本审查

**脚本**：`.work/evidence/LLVM-051t/run.sh`（340 行）

| 检查项 | 结果 |
|---|---|
| `check()` 函数 FAIL 路径存在且非恒真 | ✅ `if [ "$4" -eq 0 ]` → PASS/FAIL 两分支输出不同，FAILS 递增 |
| 脚本内无 `tee` | ✅ 所有输出用 `>`/`2>&1` 重定向 |
| `--inject` 模式注入非空可还原 | ✅ `sed -i 's/if (CostZw <= CostOw) {/if (false) {/'` + `git checkout` + md5 比对 + 重建 |
| 结尾退出码非 `tee` 吞 | ✅ `[ "$FAILS" -eq 0 ]` 直接退出 |
| 每条断言有可达 FAIL 路径 | ✅ 常量 diff 非零 / reloc 计数≠6 / deleted-item 不拒绝 / lit 失败均可触发 |

**脚本合格，不代写。**

---

##### 二、正常模式重跑

**命令**：`bash .work/evidence/LLVM-051t/run.sh > log 2>&1; echo "EXIT=$?"`

```
[PASS] build | expected: ninja EXIT=0 | actual: see .../LLVM-051t-evidence-build.log | rc=0
[PASS] constants-assemble | expected: llvm-mc EXIT=0 | actual: rc=0 | rc=0
[PASS] constants-expansion | expected: exact minimal sequence | actual: exact | rc=0
[PASS] moves-assemble | expected: llvm-mc EXIT=0 | actual: rc=0 | rc=0
[PASS] moves-blockmove | expected: 9 block moves ... | actual: exact | rc=0
[PASS] misc-assemble | expected: llvm-mc EXIT=0 | actual: rc=0 | rc=0
[PASS] misc-expansion | expected: set.rb + set.ft/set.fo incl. zero | actual: exact | rc=0
[PASS] symbol-assemble | expected: llvm-mc EXIT=0 | actual: rc=0 | rc=0
[PASS] symbol-relocs | expected: 6 x R_DADAO_ABS48 (ext x3, ext2 x3) | actual: exact | rc=0
[PASS] symbol-reloc-count | expected: 6 | actual: 6 | rc=0
[PASS] symbol-no-reloc-for-constant | expected: 0 relocs for localimm | actual: 0 | rc=0
[PASS] symbol-constant-minimal | expected: rd2 localimm -> 2 real insns, no reloc | actual: found | rc=0
[PASS] no-pseudo-in-disasm | expected: 0 pseudo mnemonics | actual: 0 | rc=0
[PASS] deleted-items | expected: 6 x unrecognized instruction mnemonic | actual: bad=0 | rc=0
[PASS] ret-rd0-rejected | expected: non-zero + invalid operand | actual: ... invalid operand ... | rc=0
[PASS] lit-new | expected: 6/6 passed | actual: Passed: 6 (100.00%) | rc=0
[PASS] check-lit | expected: 42/42 passed | actual: Passed: 42 (100.00%) | rc=0
[PASS] test-codegen | expected: 15/15 passed | actual: Results: 15/15 passed, 0 failed | rc=0
[PASS] check-patch-tree | expected: 83 patches OK | actual: 83 patches OK | rc=0
[PASS] check-source-state | expected: llvm-project OK count=1 clean=True | actual: ... OK HEAD=dc66adb35160 count=1 clean=True | rc=0
RESULT: PASS (0 failures)
EXIT=0
```

**20/20 PASS，EXIT=0。**

---

##### 三、独立注入测试（与 engineer 不同的注入点）

**注入选择**：符号路径 3 片→2 片（删除 `emitWiiExpr("or.w", 0, SymExpr)`），不同于 engineer 的 `CostZw<=CostOw→false`。

**步骤与真实输出**：

1. **注入前确认干净**：`git diff --name-only` → 空
2. **编辑**：删除 `if (emitWiiExpr("or.w", 0, SymExpr)) return true;` + `return false;` 替换为注释+return
3. **注入后 diff 非空**：`git diff --name-only` → `llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp`
4. **重建**：`ninja -j8 -C .work/build/llvm llvm-mc llvm-objdump llvm-readobj` → `EXIT=0`
5. **验证注入效果**：
   - `llvm-readobj -r` 显示 **4 条 R_DADAO_ABS48**（ext×2 + ext2×2），预期 6 条
   - 反汇编符号路径仅 2 条指令（wp2+wp1），缺 wp0
6. **证据脚本重跑** → `EXIT=1`，6 项 FAIL：
   ```
   [FAIL] symbol-relocs | expected: 6 x R_DADAO_ABS48 | actual: diff see symbol.rel.diff | rc=1
   [FAIL] symbol-reloc-count | expected: 6 | actual: 4 | rc=1
   [FAIL] lit-new | expected: 6/6 passed | actual: Passed: 5 (83.33%) | rc=1
   [FAIL] check-lit | expected: 42/42 passed | actual: Passed: 41 (97.62%) | rc=2
   [FAIL] check-patch-tree | expected: 83 patches OK | actual:  | rc=2
   [FAIL] check-source-state | expected: ... clean=True | actual: ... clean=False | rc=2
   ```
7. **还原**：`git checkout -- DADAOAsmParser.cpp` → `git diff --name-only` 空
8. **md5 比对**：`4e7974aa427ee877aaf9672a480472ee`（与注入前一致）
9. **重建**：`ninja -j8` → `EXIT=0`
10. **回绿验证**：`run.sh` → 20/20 PASS，`EXIT=0`

**注入→FAIL→还原+重建→回绿 循环完整。**

---

##### 四、独立语义核对（不照抄完成区）

###### 4.1 常量展开字节（Python 独立手算 rwii 编码式）

用 `word = (op<<24) | (rdha<<18) | (wp<<16) | immu16` 独立计算全部 28 条字节：

| 指令 | 期望字节 | 独立计算 | 匹配 |
|---|---|---|---|
| `set.zw rd1, wp0, 0x0` | `4c 04 00 00` | `4c 04 00 00` | ✅ |
| `set.ow rd2, wp0, 0xffff` | `4d 08 ff ff` | `4d 08 ff ff` | ✅ |
| `set.ow rd3, wp0, 0xffd6` | `4d 0c ff d6` | `4d 0c ff d6` | ✅ |
| `set.ow rd4, wp0, 0xffdf` | `4d 10 ff df` | `4d 10 ff df` | ✅ |
| `set.zw rd5, wp0, 0x2a` | `4c 14 00 2a` | `4c 14 00 2a` | ✅ |
| `set.zw rd6, wp1, 0x1234` | `4c 19 12 34` | `4c 19 12 34` | ✅ |
| `or.w rd6, wp0, 0xabcd` | `48 18 ab cd` | `48 18 ab cd` | ✅ |
| `set.zw rd7, wp3, 0xdead` | `4c 1f de ad` | `4c 1f de ad` | ✅ |
| `or.w rd7, wp2, 0xbeef` | `48 1e be ef` | `48 1e be ef` | ✅ |
| `or.w rd7, wp1, 0xcafe` | `48 1d ca fe` | `48 1d ca fe` | ✅ |
| `or.w rd7, wp0, 0xbabe` | `48 1c ba be` | `48 1c ba be` | ✅ |
| `set.ow rd8, wp3, 0x1234` | `4d 23 12 34` | `4d 23 12 34` | ✅ |
| `andn.w rd8, wp2, 0xffff` | `49 22 ff ff` | `49 22 ff ff` | ✅ |
| `set.zw rb1, wp0, 0x0` | `4e 04 00 00` | `4e 04 00 00` | ✅ |
| `set.zw rb1, wp2, 0x1234` | `4e 06 12 34` | `4e 06 12 34` | ✅ |
| `or.w rb1, wp1, 0x5678` | `4a 05 56 78` | `4a 05 56 78` | ✅ |
| `or.w rb1, wp0, 0x9abc` | `4a 04 9a bc` | `4a 04 9a bc` | ✅ |
| `set.zw rb3, wp3, 0xffff` | `4e 0f ff ff` | `4e 0f ff ff` | ✅ |
| `or.w rb3, wp2, 0xffff` | `4a 0e ff ff` | `4a 0e ff ff` | ✅ |
| `or.w rb3, wp1, 0xffff` | `4a 0d ff ff` | `4a 0d ff ff` | ✅ |
| `or.w rb3, wp0, 0xffff` | `4a 0c ff ff` | `4a 0c ff ff` | ✅ |
| `set.w rf1, wp1, 0x3f80` | `4f 05 3f 80` | `4f 05 3f 80` | ✅ |
| `set.w rf1, wp0, 0x0` | `4f 04 00 00` | `4f 04 00 00` | ✅ |
| `set.w rf1, wp3, 0x3ff0` | `4f 07 3f f0` | `4f 07 3f f0` | ✅ |
| `set.w rf1, wp2, 0x0` | `4f 06 00 00` | `4f 06 00 00` | ✅ |
| `set.w rf1, wp1, 0x0` | `4f 05 00 00` | `4f 05 00 00` | ✅ |
| `set.w rf1, wp0, 0x0` | `4f 04 00 00` | `4f 04 00 00` | ✅ |
| `rd2rf rf4, rd0` | `40 f4 40 01` | 由脚本 diff 验证 | ✅ |

**全部 28 条字节独立核对通过。**

###### 4.2 寄存器传值（独立 llvm-objdump 输出）

```
set.rd rd5, rb3  →  rb2rd {rd5}, {rb3}     ✅
set.rd rd2, rf7  →  rf2rd {rd2}, {rf7}     ✅
set.rd rd8, rd3  →  rd2rd {rd8}, {rd3}     ✅
set.rd rd4, ra10 →  ra2rd {rd4}, {ra10}    ✅
set.rb rb1, rd7  →  rd2rb {rb1}, {rd7}     ✅
set.rb rb2, rb7  →  rb2rb {rb2}, {rb7}     ✅
set.ft rf1, rd5  →  rd2rf {rf1}, {rd5}     ✅
set.ft rf1, rf2  →  ft2ft {rf1}, {rf2}     ✅
set.fo rf2, rf7  →  fo2fo {rf2}, {rf7}     ✅
set.fo rf3, rd9  →  rd2rf {rf3}, {rd9}     ✅
```

###### 4.3 set.ft/set.fo 特殊值（独立 objdump）

```
set.ft rf1, 0       →  2×set.w (wp1+wp0)   ✅（不动高32位，不走rd2rf）
set.fo rf4, 0       →  rd2rf {rf4}, {rd0}   ✅（从rd0拷贝零值）
set.fo rf3, rd9     →  rd2rf {rf3}, {rd9}   ✅（rd源→rd2rf，非fo2fo）
```

###### 4.4 符号/可重定位（独立 readobj 输出）

- `set.rd rd1, ext` + `set.rb rb1, ext2` → **恰 6 条 `R_DADAO_ABS48`**（ext×3 偏移 0x0/0x4/0x8, ext2×3 偏移 0xC/0x10/0x14）✅
- `.set localimm, 0x1234ABCD` → `set.zw rd2, wp1, 0x1234` + `or.w rd2, wp0, 0xabcd`（2 条，**无 reloc**）✅

###### 4.5 删除项（独立 llvm-mc 输出）

```
nop                     → error: unrecognized instruction mnemonic, rc=1  ✅
return                  → error: unrecognized instruction mnemonic, rc=1  ✅
not.o rd1, rd2          → error: unrecognized instruction mnemonic, rc=1  ✅
neg.o rd1, rd2          → error: unrecognized instruction mnemonic, rc=1  ✅
ret rd0                 → error: invalid operand for instruction, rc=1    ✅
ret (no operand)        → error: invalid operand for instruction, rc=1    ✅
```

###### 4.6 反汇编无伪指令

全部 4 个 obj 文件的反汇编中 `grep -cE 'set\.(rd|rb|ft|fo)'` = **0** ✅

---

##### 五、约束核验

| 约束 | 状态 |
|---|---|
| 不实现 `nop`/`return`/`not.*`/`neg.*`（报 unrecognized） | ✅ 6/6 拒绝 |
| `ret` 不加无参形态 | ✅ `ret` 无参报错 |
| 常量 vs 符号判据用 `evaluateAsAbsolute` | ✅ 代码 L1094 `if (SymExpr)` + L1089 `Src->getImm()` |
| 符号路径固定 3 片 `wp2/wp1/wp0` + `R_DADAO_ABS48` | ✅ readobj 验证 6 条 |
| 同段可解析 → 最少指令数、无 reloc | ✅ `.set localimm` 2 条无 reloc |
| `set.rb` 无 `set.ow-rb` | ✅ 代码 L1144 仅 set.zw 路径 |
| `set.ft` 不动高 32 位 | ✅ `set.ft rf,0` → 2×`set.w`（非 rd2rf） |
| `set.fo rf,0` → `rd2rf {rf},{rd0}` | ✅ 代码 L1125 |
| 反汇编只显真实指令 | ✅ 0 pseudo mnemonics in disasm |
| 只改 `DADAOAsmParser.cpp` 一个组件源文件 | ✅ |
| 补丁由 `make_patch.py` 导出、未手改 series | ✅ |
| 临时目录 `/tmp/opencode/LLVM-051t/` | ✅ |
| 未提交 git | ✅ `git status` 未见 commit |
| `make check` EXIT=0 | ✅ |
| `make check-lit` 42/42 | ✅ |
| `make test-codegen` 15/15 | ✅ |
| `check-patch-tree` 83 patches OK | ✅ |
| `check-source-state` clean, count=1 | ✅ |

---

##### 六、裁定判定

| 裁定 | engineer 处置 | reviewer 判定 |
|---|---|---|
| 用户原文「set.fo用rd2rd来实现」 | 落地为 `rd2rf {rf},{rd0}`（字面 rd2rd 对 rf 目的不可行） | ✅ **正确**。`rd2rd` 目的必为 rd（`contracts/opcodes.yaml` 价值=0x40B00000，rdhb 字段），对 rf 目的无法编码；`rd2rf` 是唯一可行且与 `SimRISC-03` 一致的选择。用户原文疑为口误（rd→rd 拷零 vs rd→rf 拷零），engineer 的修正合理。 |
| M1 目的 rd0/rb0 汇编期检查缺口 | 标记为既有、非本任务引入 | ✅ **确认既有**。独立验证：真实指令 `rb2rd {rd0},{rb3}` EXIT=0、`set.zw rd0,wp0,5` EXIT=0、`set.zw rb0,wp0,5` EXIT=0，均为既有行为；FP 目的 `ft2ft {rf0},{rf2}` → 报错（rc=1），说明 FP 有检查而 M1 无。伪指令展开复用既有行为，未新增缺陷。 |
| `SimRISC-03` 示例下划线写法 | 标记为 spec 侧问题 | ✅ 同意，不影响实现。 |

---

##### 七、判决

**Accepted**

证据脚本合格（FAIL 路径完整、注入有效、无 tee/恒真）；正常模式 20/20 PASS EXIT=0；独立注入（符号 3→2 片）→ FAIL → 还原+重建 → 回绿循环完整；全部常量字节独立手算核对通过；寄存器传值/符号/删除项/反汇编独立验证通过；裁定判定合理；约束全部守住。
