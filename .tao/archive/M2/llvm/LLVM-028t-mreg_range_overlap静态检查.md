# LLVM-028t: `mreg_range_overlap` M1 汇编期静态检查（`rd2rd`/`rb2rb`）

**模块**：llvm
**项目里程碑**：M2
**依赖**：`SPEC-088t`（规范/合约层修复，**须先 `已验证`**）。相关：`contracts/legality_rules.yaml`（`mreg_range_overlap`，`active`/`static`）、`components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`、`tests/lit/MC/Dadao/ret-rd0-legality.s`（同类先例）。
**状态**：已验证

> 本任务书是**架构师规划产物**，尚未经用户确认、未下发。执行前须按 `AGENTS.md`「任务分解与执行确认」由用户逐条确认。

---

## 0. 背景与用户裁定

- 用户裁定：`mreg_range_overlap`（`active`/`static`）当前是「纸面规则」——**LLVM 无静态检查**、QEMU 无运行期检查、无探针/门控。
- 本任务只做 **LLVM 汇编期静态检查**：`rd2rd`/`rb2rb` 的源/目的范围有交集（含完全重合）⇒ `Error` 级硬报错（`llvm-mc` 非零退出），与 `SPEC-083t`/`LLVM-027t`（`dst_rd0_nonzero` 汇编期半边）体例一致。
- QEMU 运行期半边归 `QEMU-033t`；向量/生成器修正归 `TESTCASES-023t`。

### 为何 LLVM 侧需要静态检查（架构师判断，供用户确认）

1. 规则 `kind: static`，且 `rd2rd {rd3:rd4}, {rd2:rd3}` 的**重叠可由汇编语法显式表达**（与 `mreg_range_overflow` 不同——后者因 `{start:end}` 隐含 `start+count≤64` 而**无法**经语法表达，只能由手写编码触达）。
2. 项目已有先例：`dst_rd0_nonzero`（同为 static）由 `LLVM-027t` 做汇编期硬报错、`QEMU-032t` 做运行期 ILLI，两侧齐备；且 `dst_rd0`/`dst_rb0` 现亦经操作数约束在汇编期拦截（实测 `add.uo rd0,…` → `error: invalid operand for instruction`）。
3. 不检查的后果：汇编器**静默接受**非法程序（实测 `rd2rd {rd3:rd4}, {rd2:rd3}` 现输出 `encoding: [0x40,0xb0,0x30,0x82]`），只能到 QEMU 运行期才报错，工具链 UX 与「静态规则汇编期报错」原则不符。
4. 结论：**建议实现 LLVM 静态检查**（若用户倾向与「仅 QEMU 实现」的既有部分规则一致而拒绝，则本任务取消，须在 `deferred.md` 登记「`mreg_range_overlap` 无汇编期检查」）。

---

## 1. 事实核实（本轮 architect 实测；执行时以重跑为准）

1. `components/llvm-project/patches/.../DADAOAsmParser.cpp.patch`：
   - `matchAndEmitInstruction`（L851 起）：先做 rrrr 旧语法拒绝与复杂操作数展开（L880–945），再对 `ret` 做静态合法性检查（L1068–1088，判据 `Flat[1]->isReg()` + `Flat[2]` 常量 0），最后 `MatchInstructionImpl`。
   - `parseRegGroup`（L439–539）：`{start:end}` ⇒ `createRegGroup(Regs, Count)`，`Count = end-start+1`；`DADAOOperand` 暴露 `getRegList()`（首个即起始寄存器）与 `getGroupCount()`（L910 使用）。
   - 展开阶段 L907–915 只把 `kRegGroup` 的**首寄存器**压入 `Flat`，并把 `Count` 存进**单个** `SavedGroupCount`（后出现的组会覆盖前者）⇒ 检查宜在**展开前**直接读 `Operands[]` 的 `kRegGroup`，不要依赖 `Flat`/`SavedGroupCount`。
2. 实测当前行为（`.work/build/llvm/bin/llvm-mc`，本机已构建）：
   - `rd2rd {rd3:rd4}, {rd2:rd3}`（重叠）→ 静默汇编为 `[0x40,0xb0,0x30,0x82]`。
   - `rd2rd {rd4:rd5}, {rd2:rd3}`（非重叠）→ `[0x40,0xb0,0x40,0x82]`。
   - `rb2rb {rb3:rb4}, {rb2:rb3}`（重叠）→ `[0x40,0xd0,0x30,0x82]`。
   - `add.uo rd0, …` → `error: invalid operand for instruction`（说明部分 static 规则已在汇编期拦截）。
3. `tests/lit/MC/Dadao/ret-rd0-legality.s` 为同类先例（`%llvm_mc` + `%not` + `FileCheck --check-prefix=ERR`）。
4. `make check` 含 `check-lit`（lit 26 条）；本任务预计 lit 26→27。

---

## 2. 设计

### 2.1 代码改动（`DADAOAsmParser.cpp.patch`）

在 `matchAndEmitInstruction` 中、复杂操作数展开**之前**，增加 `rd2rd`/`rb2rb` 的重叠静态检查：

```cpp
  // Static legality check for mreg_range_overlap (SimRISC-02 §寄存器组之间块赋值):
  // `rd2rd`/`rb2rb` 的源范围与目的范围有任何交集（含完全重合）⇒ 硬报错（Error，
  // 非 warning）。语法分别为 {rdHB:rdHB+immu6-1}, {rdHC:rdHC+immu6-1} / rb 同构。
  // 仅同一寄存器组；跨组指令（ra2rd/rd2ra/rd2rb/rb2rd/rd2rf/rf2rd）结构性不可能重叠。
  if (Operands.size() == 3) {
    auto *Tok = static_cast<DADAOOperand *>(Operands[0].get());
    auto *Dst = static_cast<DADAOOperand *>(Operands[1].get());
    auto *Src = static_cast<DADAOOperand *>(Operands[2].get());
    if (Tok && Tok->isToken() && Dst && Src &&
        Dst->Kind == DADAOOperand::kRegGroup &&
        Src->Kind == DADAOOperand::kRegGroup) {
      StringRef Mnem = Tok->getToken();
      if (Mnem == "rd2rd" || Mnem == "rb2rb") {
        MCRegister D = Dst->getRegList()[0];
        MCRegister S = Src->getRegList()[0];
        unsigned Hd = Dst->getGroupCount();   // == Src->getGroupCount()
        unsigned Hb = D.id(), Hc = S.id();     // 同组，基准相消
        if (!(Hb + Hd <= Hc || Hc + Hd <= Hb))
          return Error(Dst->getStartLoc(),
                       "invalid '" + Mnem.str() + "': source and destination "
                       "register ranges overlap (mreg_range_overlap); source and "
                       "destination must be disjoint");
      }
    }
  }
```

- 条件 `!(Hb+Hd<=Hc || Hc+Hd<=Hb)` 即「有交集（含完全重合）」。
- 起始寄存器取 `getRegList()[0]`；`immu6` 取 `getGroupCount()`（语法由 `{start:end}` 唯一确定）。
- 报错为 `Error(...)`（非 warning），保证 `llvm-mc` 非零退出。
- **不改** TableGen、`CodeEmitter`、其它指令；不改 `dst_rd0_nonzero` 既有检查。

### 2.2 lit 测试（新建 `tests/lit/MC/Dadao/overlap-legality.s`）

- 正例（必须干净汇编）：`rd2rd {rd4:rd5}, {rd2:rd3}`、`rd2rd {rd8}, {rd1}`、`rb2rb {rb4:rb5}, {rb2:rb3}`、`rb2rb {rb8}, {rb1}`。
- 负例（`%not %llvm_mc` + `--check-prefix=ERR`）：`rd2rd {rd3:rd4}, {rd2:rd3}`（部分重叠）、`rd2rd {rd3:rd3}, {rd3:rd3}`（完全重合）、`rd2rd {rd2:rd3}, {rd3:rd4}`（目的在前）、`rb2rb {rb3:rb4}, {rb2:rb3}`、`rb2rb {rb3:rb3}, {rb3:rb3}`。
- 体例照 `ret-rd0-legality.s`；ERR 串匹配实际报错文本。

---

## 3. 交付物

| # | 文件 | 动作 |
|---|---|---|
| 1 | `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch` | 加静态检查 |
| 2 | `tests/lit/MC/Dadao/overlap-legality.s` | 新建 lit |
| 3 | `.work/evidence/LLVM-028t/run.sh` | 一键证据脚本（含注入自检） |
| 4 | `.work/log/llvm/LLVM-028t-*.log` | 构建/lit 完整输出 |

**明确不改**：`contracts/**`、`spec/**`、`tools/{spec,qemu,testcases}/**`、`components/qemu/**`、其它 lit。

---

## 4. 执行环境
**执行环境**：本地

## 5. 接口规范

### 输入
- `components/llvm-project/patches/.../DADAOAsmParser.cpp.patch`
- `contracts/legality_rules.yaml`（`mreg_range_overlap`）、`contracts/opcodes.yaml`（`rd2rd_orri_rd`/`rb2rb_orri_rb`）
- `tests/lit/MC/Dadao/ret-rd0-legality.s`（体例）、`tests/lit/MC/Dadao/lit.cfg.py`（`%llvm_mc`/`%not`）

### 输出
见 §3。

### 约束
- 中文；**不提交 git**；只动任务书范围；**失败即停，禁自动重试**。
- **重建成本申报**：改补丁 ⇒ `make prepare` + `make build-mc`（增量，预计 **5–15 分钟**）。构建受 `JOBS`（默认 8）限制，禁全核并行。
- 临时目录 `/tmp/opencode/LLVM-028t/`；日志 `.work/log/llvm/`；证据 `.work/evidence/LLVM-028t/`。

---

## 6. 验收标准（可执行、可失败，含反例注入）

1. **构建**：`make prepare && make build-mc` EXIT 0（留 `.work/log/llvm/LLVM-028t-build.log`）。
2. **lit**：`make check-lit`（或 `%llvm_mc` 直跑）→ `overlap-legality.s` PASS、总数 **27/27**；负例确实使 `llvm-mc` **非零退出**且 stderr 含 `overlap`。
3. **正例不误伤**：非重叠 `rd2rd`/`rb2rb` 与既有 `rb_ops.s`/`orri.s` 等仍 PASS。
4. **反例可失败（承重证明）**：注入「移除静态检查」⇒ 负例 PASS（`not` 失败、lit FAIL）；还原源码**并重建** ⇒ 回绿。注入用 `git diff --name-only` 证非空；还原用 `git status`/`git diff` + 重建后重跑证明。另注入「只判部分重叠、漏完全重合」的错误条件 ⇒ 完全重合负例 FAIL，证「含完全重合」承重。
5. **`make check` 全绿**：`repository checks: PASS`（重点：`check-lit`、`check-patch-tree` 67 patches OK、`check-interface` 80/80）。
6. **残留与越界**：`git status --untracked-files=all` 干净（除应改文件 + 本任务书）；`check-no-residue` PASS；`git diff --name-only` 与 §3 对齐。

---

## 7. 硬约束清单（下发提示必带）

1. 临时目录 `/tmp/opencode/LLVM-028t/`，禁仓库内临时文件。
2. 不提交 git。
3. 完成区结论与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败即停，禁自动重试。
6. 补丁导出纪律：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥。
7. 复杂命令输出留存 `.work/log/llvm/`。
8. 一键证据脚本：`engineer` 产 `.work/evidence/LLVM-028t/run.sh` 并跑通；`reviewer` 审脚本 + 重跑 + **独立注入一次反例**。

---

## 8. 风险与需用户拍板的点

- **是否需要 LLVM 侧检查**（§0 判断，建议实现）；若用户裁定「只在 QEMU 侧」，本任务取消并登记遗留。
- 与 `QEMU-033t` 并行时**共享** `components/`（不同子树）但**不建议并行重建**（`AGENTS.md`：长构建一次只跑一个）；两者可在 A 完成后串行。
- 报错文本/位置须与 lit `ERR` 串一致；`getRegList()` 对单寄存器组（`{rd8}`，count=1）亦成立。

## 完成区

**测试结果**：通过 15/15（证据脚本默认检查项）；失败原因：无。
- `make build-mc` EXIT=0（增量重建 18.75s）。
- `make check-lit` EXIT=0：**27/27 PASS**（26→27，新 `overlap-legality.s` 27/27）。
- 正例（不重叠，两序）`llvm-mc` rc=0；负例（部分重叠/完全重合，rd/rb 双序）rc=1 且 stderr 含
  `error: invalid 'rd2rd'|'rb2rb': source and destination register ranges overlap (mreg_range_overlap); ...`。
- `make check-patch-tree` EXIT=0：`2 component(s), 67 patches OK`。
- `make check` EXIT=0：`check_issues: ... 0 blocking`、`repository checks: PASS`。
- 反例注入自检（`.work/evidence/LLVM-028t/run.sh --inject`）EXIT=0：A（移除检查）负例静默汇编 rc=0、lit FAIL；
  B（只判部分重叠、漏完全重合）完全重合负例 rc=0、部分重叠仍 rc=1；两次还原重建后源/二进制 sha256 与注入前一致
  （源 `2c403ef6…`、二进制 `a3db9e7e…`）。

**修改文件**：
1. `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`（M，补丁文件净 **+36/−2**）
   —— 补丁内 `DADAOAsmParser.cpp` 相对 base 为整文件新增，源码 1113→1147 行（**+34 行**，本任务改动）。
2. `tests/lit/MC/Dadao/overlap-legality.s`（新增，47 行）。
3. `.work/evidence/LLVM-028t/run.sh`（新增，一键证据脚本，含 `--inject`）。
4. `.work/log/llvm/LLVM-028t-*.log`（构建/lit/check/注入完整输出）。
明确未改：`contracts/**`、`spec/**`、`tools/{spec,qemu,testcases}/**`、`components/qemu/**`、其它 lit、
`tests/vectors/isa/*.yaml`。

**验收结果**（真实输出见 `.work/log/llvm/`）：
- `make build-mc` → `build-mc: PASS`，`real 0m18.753s`。
- 负例实测：
  ```
  <stdin>:1:7: error: invalid 'rd2rd': source and destination register ranges overlap (mreg_range_overlap); source and destination must be disjoint
  rc=1
  ```
- `make check-lit`：`Total Discovered Tests: 27  Passed: 27 (100.00%)`，`PASS: DADAO-MC :: overlap-legality.s (27 of 27)`。
- `make check`：`repository checks: PASS`，EXIT=0。
- `git status --untracked-files=all`：仅 `M` 补丁 + `M` 本任务书 + `?? tests/lit/.../overlap-legality.s`（`check-no-residue: PASS`）。

**新发现/坑**：
- **同一指令的两个 `{start:end}` 组共享单个 immu6**：`parseRegGroup` 的 range 只把 `[start,end]` 存入 `RegList`
  且 `GroupCount=end-start+1`；展开阶段 `SavedGroupCount` 被**后出现的组覆盖**（rd2rd/rb2rb 中即源组）。
  故静态检查放在**展开前**直接读 `Operands[]` 的 `kRegGroup` 是正确选择。
- **不等 count 的畸形输入**：`rd2rd {rd5:rd6}, {rd2:rd6}` 当前会被静默编码为 immu6=**源组 count**（=5），
  即两范围实际都按 5 展开（`{rd5:rd9}`）。本实现用**各自组 count** 判交集（对合法等 count 输入与任务书公式等价，
  且对畸形输入更保守），此为有意偏离，已在自审记录说明。
- 寄存器 id 连续（`parseRegGroup` L472 注释亦确认），故 `start/count` 的整数区间运算成立。

**遗留问题**：无。`scope: fp` 的 `convert_ff`（ft2fo/fo2ft/ft2ft/fo2fo）重叠属 M1 范围外，任务书 §2.1 明确
本任务只做 `rd2rd`/`rb2rb`，FP 侧未实现（非本任务缺口）。

## 审阅记录

#### 第 1 轮 engineer 自审

改动源码自主逐行审查（`DADAOAsmParser.cpp` 插入块 + `overlap-legality.s` + `run.sh`）：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1：实现用**各自组 count** 的半开区间 `[s,s+c)` 判交集，任务书设计稿用单一 `Hd`（默认等 count）。对合法等 count 输入两者等价；对不等 count 畸形输入前者更保守（仍报错） | ❌不修（有意偏离，更正确） | 未改 | 全部验收项 + 注入 B 通过；`run.sh` 断言 `DstStart < SrcEnd && SrcStart < DstEnd` |
| F2：`scope: fp` 的 convert_ff 重叠未做静态检查 | ⏸延后（任务范围外） | 未改 | 任务书 §2.1/§3 明确只做 rd2rd/rb2rb；FP 属 M1 范围外 |
| F3：检查置于旧语法拒绝之后、展开之前，仅 `Operands.size()==3` 且两个 `kRegGroup` 时触发 | ✅已修（即本实现） | 插入块 | 负例 rc=1、正例 rc=0、`make check` PASS |
| F4：报错为 `Error(...)`（非 warning），位置取目的操作数 `getStartLoc()` | ✅已修 | 同上 | 负例 rc=1 且 stderr `error:` 前缀 |
| F5：`getRegList()[0]` 对 range（`[start,end]`）与 single（`[reg]`）均有效非空 | ✅已证 | — | lit 覆盖 `{rd8}`/`{rb1}` single 用例，rc=0 |

判决：**通过自审**，所有 finding 已处置（F1 为有意且更正确的偏离，F2 属任务范围外），可标「待验收」。

#### 第 1 轮 reviewer 验收

**判决：Accepted**

---

##### 1. 脚本审计（`.work/evidence/LLVM-028t/run.sh`）

| 审计项 | 结论 |
|--------|------|
| 恒真断言 | **无**。所有 `check()` 调用的 expected/actual 均可不等（如注入 A 的 `positive rd2rd disjoint rc` expected=rc=0 actual=rc=1） |
| FAIL 路径 | **存在**。每个 check 失败时调 `bad()` 设 `FAIL=1`，脚本末尾 `exit 1` |
| 注入 A 非空 | `if (false && DstStart < SrcEnd && ...)` — 确认 `assert s.count(old) == 1` 通过 |
| 注入 B 非空 | `if (DstStart != SrcStart && DstStart < SrcEnd && ...)` — 同上 |
| 还原含重建 | `restore_and_rebuild()` 做 `git checkout` + `make build-mc` ✓ |
| `git diff --name-only` 非空检查 | 注入后均 check `$SRC_REL` = `$changed` ✓ |
| 退出码 | FAIL→`exit 1`，PASS→`exit 0`，无 `tee` 吞退出码 ✓ |

**结论：脚本合格。**

---

##### 2. 重跑记录

**默认模式**（`bash run.sh`）：
```
PASS | positive rd2rd disjoint rc | expected=rc=0 actual=rc=0
PASS | positive rd2rd singles rc | expected=rc=0 actual=rc=0
PASS | positive rb2rb disjoint rc | expected=rc=0 actual=rc=0
PASS | positive rb2rb singles rc | expected=rc=0 actual=rc=0
PASS | negative rd2rd partial-overlap rc!=0 | expected=rc=1 actual=rc=1
PASS | negative rd2rd partial-overlap msg | expected=contains 'overlap' actual=contains 'overlap'
PASS | negative rd2rd partial-overlap (dst first) rc!=0 | expected=rc=1 actual=rc=1
PASS | negative rd2rd complete-coincidence rc!=0 | expected=rc=1 actual=rc=1
PASS | negative rb2rb partial-overlap rc!=0 | expected=rc=1 actual=rc=1
PASS | negative rb2rb partial-overlap (dst first) rc!=0 | expected=rc=1 actual=rc=1
PASS | negative rb2rb complete-coincidence rc!=0 | expected=rc=1 actual=rc=1
PASS | lit overlap-legality.s | expected=PASS actual=PASS
PASS | make check-lit | expected=PASS actual=PASS
PASS | make check-patch-tree | expected=PASS actual=PASS
PASS | source tree clean (no injection residue) | expected=clean actual=clean
source sha256: 2c403ef65f53f140667f2c787b49ad43be9fb97e2218277867d8083bdd4a64f1
binary sha256: a3db9e7e0ef1a0cd13dc2adad6a7e2d05e76ff7cbb485cd2fb19c46d25d9a6e3
RESULT: PASS
EXIT=0
```

**`--inject` 模式**（`bash run.sh --inject`）：
```
=== injection A ===
PASS | inject A changed source | ... = llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
PASS | rebuild llvm-mc
PASS | inject A: partial-overlap now assembles (rc=0)
PASS | inject A: lit FAILs (check was load-bearing)
PASS | restore source (git diff empty)
PASS | rebuild llvm-mc
PASS | after A restore: partial-overlap errors again (rc=1)
=== injection B ===
PASS | inject B changed source | ... = llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
PASS | rebuild llvm-mc
PASS | inject B: complete coincidence assembles (rc=0)
PASS | inject B: rb complete coincidence assembles (rc=0)
PASS | inject B: partial overlap still errors (rc=1)
PASS | restore source (git diff empty)
PASS | rebuild llvm-mc
PASS | after B restore: complete coincidence errors again (rc=1)
=== default checks === (15/15 PASS)
source sha256: 2c403ef65f53f140667f2c787b49ad43be9fb97e2218277867d8083bdd4a64f1
binary sha256: a3db9e7e0ef1a0cd13dc2adad6a7e2d05e76ff7cbb485cd2fb19c46d25d9a6e3
RESULT: PASS
EXIT=0
```

---

##### 3. 语义验证（reviewer 独立执行）

| 测试 | 指令 | 期望 | 实际 | 结论 |
|------|------|------|------|------|
| 不重叠 rd2rd | `{rd4:rd5},{rd2:rd3}` | rc=0 | rc=0 | ✓ |
| 不重叠 rb2rb | `{rb4:rb5},{rb2:rb3}` | rc=0 | rc=0 | ✓ |
| 部分重叠 | `{rd3:rd4},{rd2:rd3}` | rc=1 | rc=1 | ✓ |
| 完全重合 | `{rd3:rd3},{rd3:rd3}` | rc=1 | rc=1 | ✓ |
| 目的在前 | `{rd2:rd3},{rd3:rd4}` | rc=1 | rc=1 | ✓ |
| 边界相邻不重叠 | `{rd3:rd4},{rd5:rd6}` | rc=0 | rc=0 | ✓ |
| 边界相邻反序 | `{rd5:rd6},{rd3:rd4}` | rc=0 | rc=0 | ✓ |
| 单元素重叠 | `{rd3},{rd3}` | rc=1 | rc=1 | ✓ |
| 单元素不重叠 | `{rd3},{rd4}` | rc=0 | rc=0 | ✓ |
| 不等 count 重叠 | `{rd5:rd6},{rd2:rd6}` | rc=1 | rc=1 | ✓ |
| 等 count 不重叠 | `{rd5:rd6},{rd2:rd3}` | rc=0 | rc=0 | ✓ |

错误信息均含 `overlap (mreg_range_overlap)`。

---

##### 4. lit 回归

- `llvm-lit tests/lit/MC/Dadao/overlap-legality.s`：PASS ✓
- `make check-lit`：**27/27 PASS**（26→27）✓
- `make check`：`repository checks: PASS`，EXIT=0 ✓
- `make check-patch-tree`：`2 component(s), 67 patches OK` ✓

---

##### 5. 补丁与不变量

- 补丁统计：**+36/−2**（`git diff --stat` 确认）✓
- `git diff --name-only`：仅 `DADAOAsmParser.cpp.patch` + 任务书 ✓
- `components/qemu/**`、`tests/vectors/**` 未动 ✓
- `git status --untracked-files=all`：仅预期的 3 项（patch + 任务书 + overlap-legality.s）✓

---

##### 6. 独立注入（reviewer 自选，非脚本 A/B）

**注入策略**：将 `DstStart < SrcEnd && SrcStart < DstEnd` 改为 `DstStart <= SrcEnd && SrcStart <= DstEnd`——对边界相邻不重叠 case 产生假阳性。

```
# 注入后
$ git -C .work/source/llvm-project diff --name-only
llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
（diff 非空 ✓）

# 重建后测试
$ printf 'rd2rd {rd3:rd4}, {rd5:rd6}\n' | llvm-mc ...
error: invalid 'rd2rd': source and destination register ranges overlap ...
rc=1  ← 假阳性！应为 rc=0

# 脚本重跑
$ bash .work/evidence/LLVM-028t/run.sh
FAIL | positive rd2rd disjoint rc | expected=rc=0 actual=rc=1
...
RESULT: FAIL
EXIT=1  ← 脚本正确检测到 FAIL ✓

# 还原 + 重建
$ git -C .work/source/llvm-project checkout -- llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
$ make build-mc  → PASS

# SHA 复原
source sha256: 2c403ef65f53f140667f2c787b49ad43be9fb97e2218277867d8083bdd4a64f1 ✓（与注入前一致）
binary sha256: a3db9e7e0ef1a0cd13dc2adad6a7e2d05e76ff7cbb485cd2fb19c46d25d9a6e3 ✓（与注入前一致）

# 还原后脚本重跑
$ bash .work/evidence/LLVM-028t/run.sh
RESULT: PASS
EXIT=0  ✓
```

**结论：独立注入成功证伪，脚本能失败，还原含重建，SHA 一致。**

---

##### 7. 实现偏离核实

任务书设计稿用 `Hb + Hd <= Hc || Hc + Hd <= Hb`（单一 `Hd`），实现用 `DstStart < SrcEnd && SrcStart < DstEnd`（各自组 count 的半开区间交集）。

- **等 count 输入**（合法情况，如 `{rd3:rd4},{rd5:rd6}`）：两者数学等价 ✓
- **不等 count 畸形输入**（如 `{rd5:rd6},{rd2:rd6}`）：实现仍正确报错（rc=1），因 `[5,7) ∩ [2,7)` 有交集 ✓
- **结论**：偏离**更正确**且不破坏合法等 count 输入 ✓

---

##### 8. 完成区一致性

| 完成区声明 | reviewer 核验 | 结论 |
|-----------|--------------|------|
| `make build-mc` EXIT=0 | 重跑确认 ✓ | 一致 |
| 27/27 PASS | `make check-lit` 确认 ✓ | 一致 |
| 负例 rc=1 且 stderr 含 `overlap` | 独立测试确认 ✓ | 一致 |
| `check-patch-tree` 67 patches OK | 重跑确认 ✓ | 一致 |
| `make check` EXIT=0 | 重跑确认 ✓ | 一致 |
| 注入 A/B 通过 + 还原回绿 | 脚本 `--inject` 重跑确认 ✓ | 一致 |
| 补丁净 +36/−2 | `git diff --stat` 确认 ✓ | 一致 |
| 源码 sha `2c403ef6…` | 重跑确认 ✓ | 一致 |
| 二进制 sha `a3db9e7e…` | 重跑确认 ✓ | 一致 |
| `git status` 仅预期改动 | 重跑确认 ✓ | 一致 |

**无不实/夸大。**

---

**最终判决：Accepted** — 所有验收命令在 reviewer 独立重跑下全部通过，约束无违反，脚本合格且独立注入证伪成功。
