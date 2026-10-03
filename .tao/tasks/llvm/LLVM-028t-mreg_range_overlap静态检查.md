# LLVM-028t: `mreg_range_overlap` M1 汇编期静态检查（`rd2rd`/`rb2rb`）

**模块**：llvm
**项目里程碑**：M1→M2
**依赖**：`SPEC-088t`（规范/合约层修复，**须先 `已验证`**）。相关：`contracts/legality_rules.yaml`（`mreg_range_overlap`，`active`/`static`）、`components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`、`tests/lit/MC/Dadao/ret-rd0-legality.s`（同类先例）。
**状态**：待开始

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

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
