# LLVM-027t: ret rd0 静态检查 — 汇编期报错

**模块**：llvm
**项目里程碑**：M2
**依赖**：`LLVM-026t`、`SPEC-083t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `components/llvm-project/patches/.../DADAOAsmParser.cpp.patch`（**由 LLVM-026t 完成后提供基线，本任务在其之上叠加**）
  - `contracts/opcodes.yaml`（`ret_riii_ra` 条目，SPEC-083t 完成后含 legality）
  - `contracts/legality_rules.yaml`（SPEC-083t 完成后含新增规则）
  - 已有 lit 测试模式（参考 `tests/lit/` 下现有 `.s` 文件格式）

- **输出**：
  1. `components/llvm-project/patches/.../DADAOAsmParser.cpp.patch`：在 `parseInstruction` 或 matchAndEmitInstruction 阶段对 `ret` 指令做静态检查：当 `rdha == rd0`（寄存器编号 0）且 `imms18 != 0` 时，报**硬错误**（`Error` 级：汇编失败、非零退出码；**不得**降为 warning）
  2. 新增 lit 测试文件（建议 `tests/lit/MC/Dadao/ret-rd0-legality.s`）：
     - **正例**：`ret rd0, 0` 必须成功汇编（`# CHECK-NOT: error`）
     - **反例**：`ret rd0, 1` 必须报错（`# CHECK: error:`）
     - **边界**：`ret rd0, -1` 必须报错
     - **非 rd0 正例**：`ret rd1, 0` 和 `ret rd1, 42` 均成功（无此约束）
  3. 补丁按 **`spec/Process-01-组件补丁组织与构建编排.md`**（E1–E8）流程：在 `.work/source/llvm-project` 修改 → **收敛为「上游 base + 恰好 1 commit」且 worktree 干净** → 用 `tools/infra/make_patch.py` 导出（该工具**校验 E1 不变量**，脏树**拒绝导出**）；`make check-patch-tree`（断言 ①–⑨）须绿

- **约束**：
  - **前置已完成**：`LLVM-026t`（汇编立即数字节化）与 `SPEC-083t`（合法性规则 `dst_rd0_nonzero`）**均已 `已验证`**。本任务**在其成果之上叠加**：先读 `LLVM-026t` 的完成区与其补丁、以及 `SPEC-083t` 的规则口径，确认 `ret` 解析/匹配的**合并点**（改了哪些行/函数）再动手；窗口内 `.work/source/llvm-project` 应满足 E1 不变量（clean + base+1）
  - 需**增量重建 llvm-mc**（`JOBS=8`，预计 10–20 分钟），一次只跑一个长构建
  - 不提交 git
  - 全程中文

## 验收标准

1. **正例通过**：`ret rd0, 0` 在 llvm-mc 下成功汇编，无 error/warning。
2. **反例失败**：`ret rd0, 1` 在 llvm-mc 下报错，退出码非零，错误信息包含相关提示。
3. **反例失败**：`ret rd0, -1` 在 llvm-mc 下报错。
4. **非 rd0 不受影响**：`ret rd1, 0` 和 `ret rd1, 42` 均成功汇编。
5. **lit 测试**：`llvm-lit tests/lit/MC/Dadao/ret-rd0-legality.s` 全部 PASS。
6. **回归**：已有 lit 测试不受影响（`llvm-lit tests/lit/MC/` 全绿）。
7. **反例门控**：将检查逻辑临时注释掉后，反例用例应 PASS（证明检查逻辑确实生效）。
8. **补丁规范**：补丁文件符合树形补丁集规范，`make check-patch-tree` 通过。

## 完成区

**测试结果**：验收 8/8 通过。MC/Dadao **23/23**；`make check-lit` **26/26**（MC 23 + E2E 3）；`make check` **全绿**（`repository checks: PASS`，`check-patch-tree: 67 patches OK`）。反例门控：注入禁用检查 ⇒ 反例转 rc=0 且新 lit FAIL；还原**并重建** ⇒ 源码/二进制 sha256 逐字节回到注入前、反例 rc=1、lit PASS（全程留证 `.work/log/llvm/LLVM-027t-counterexample-gate.log`）。

**修改文件**（`git status --untracked-files=all` 仅以下 4 项，无残留）：
| 文件 | 改动 | 范围归属 |
|---|---|---|
| `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch` | 1119 行（相对 LLVM-026t 基线（1097 行）**净 +22 行**，`git diff --numstat` = +24/−2）：`matchAndEmitInstruction` 新增 `ret` 静态检查 | **本任务** |
| `tests/lit/MC/Dadao/ret-rd0-legality.s` | 新增 lit（5 条 RUN：正例 obj 汇编 + `show-encoding` 内容校验 + 3 反例 `%not`） | **本任务** |
| `components/llvm-project/changelog.md` | 追加 LLVM-027t 条目（`Process-01 §10`，按任务一条） | **本任务** |
| `components/llvm-project/.work/source` 工作树 | 收敛为 base+1 且干净：HEAD=`ee4a1d7cbea0`，`rev-list --count base..HEAD = 1` | **本任务** |

**验收结果**（真实命令 + 输出 + 退出码；复杂命令日志见 `.work/log/llvm/LLVM-027t-*.log`）：

| # | 验收项 | 真实命令/输出 | RC | 日志 |
|---|---|---|---|---|
| 1 | 正例通过 | `echo 'ret rd0, 0' \| llvm-mc --triple=dadao-unknown-elf -show-encoding` → `; encoding: [0x76,0x00,0x00,0x00]`（无 error/warning） | 0 | `LLVM-027t-counterexample-gate.log` |
| 2 | 反例失败 | `echo 'ret rd0, 1' \| llvm-mc ... -filetype=obj -o /dev/null` → `error: invalid 'ret': rdHA is rd0, so imms18 must be the constant 0 (use 'ret rd0, 0')` | **1** | 同上 |
| 3 | 反例失败 | `echo 'ret rd0, -1' \| llvm-mc ... -filetype=obj` → 同 #2 错误信息 | **1** | 同上 |
| 4 | 非 rd0 不受影响 | `ret rd1, 0` → `[0x76,0x04,0x00,0x00]`；`ret rd1, 42` → `[0x76,0x04,0x00,0x2a]` | 0/0 | 同上 |
| 5 | lit（新文件） | `llvm-lit tests/lit/MC/Dadao/ret-rd0-legality.s` → `PASS ... 1/1 (100.00%)` | 0 | `LLVM-027t-lit-newfile-v3.log` |
| 6 | 回归 | `llvm-lit tests/lit/MC/Dadao` → **23/23**；`make check-lit` → **26/26**。⚠️任务书字面命令 `llvm-lit tests/lit/MC/` **EXIT=2**（无 `lit.cfg.py`，lit 报 `did not discover any tests`，见坑#2） | 0 | `LLVM-027t-lit-MC-Dadao-final.log` / `LLVM-027t-check-lit-final.log` / `LLVM-027t-lit-MC-root.log` |
| 7 | **反例门控** | 注入 `if (!IsZero)`→`if (false && !IsZero)`（源码 sha `47f29bfb…`→`7dc060b2…`；`git diff --name-only` 非空）→ 重建 → `ret rd0,{1,-1,foo}` 均 **rc=0**、新 lit **FAIL**；`cp` 还原 → 重建 → 源码 sha 回 `47f29bfb…`、二进制 sha 回 `aa2483bc…`（逐字节一致）、反例 rc=1、lit PASS、worktree 干净 | 1→0→0 | `LLVM-027t-counterexample-gate.log` |
| 8 | 补丁规范 | `make check-patch-tree` → `2 component(s), 67 patches OK`；`make check-source-state` → `llvm-project: OK HEAD=ee4a1d7cbea0 count=1 clean=True`；补丁 1119 行、含 `constant 0`、`grep -c e69de29`=0 | 0 | `LLVM-027t-check-patch-tree-v3.log` |
| 附 | 符号操作数（本任务扩展） | `echo 'ret rd0, foo'` → 同 #2 错误信息（非良构，见坑#1） | **1** | `LLVM-027t-counterexample-gate.log` |
| 附 | 全量门控 | `make check` → `repository checks: PASS`、lit `26/26` | 0 | `LLVM-027t-check-final.log` |

**新发现/坑**：
1. **`DADAOOperand` 常量与符号表达式共用 `kImmediate`**：`createImmExpr` 设 `Kind=kImmediate`、`ImmExpr=E`、`ImmVal=0`，故 `isImm()` 对符号也为真、`getImm()` 恒返回 0。**仅用 `isImm()`+`getImm()!=0` 会漏掉 `ret rd0, foo`**（首版实现即如此，实测 rc=0 静默放行，并生成 `DADAO_FK_PCRel_18` 重定位）。须以 `getImmExpr()==nullptr` 判定常量。教训：**判断"是否为常量立即数"不能只看 Kind，要查 `ImmExpr` 指针**。
2. **`llvm-lit tests/lit/MC/` 不可作为套件入口**：`tests/lit/MC/` 目录层级**无** `lit.cfg.py`（配置在 `tests/lit/MC/Dadao/lit.cfg.py`），lit 对目录 `MC/` 报 `unable to find test suite` / `contained no tests`，EXIT=2。仓库既有入口是 `tests/lit/MC/Dadao` 与 `make check-lit`。任务书验收 6 的字面路径因而不可执行。
3. **增量重建远快于申报**：仅改 1 个 parser `.cpp`，`make build-mc JOBS=8` 增量 **约 19s**（编译 1 个 .o + 重链 5 个可执行），非 10–20 分钟。

**遗留问题**：
- **任务书验收 6 字面命令 `llvm-lit tests/lit/MC/` 不可用**（坑#2）：已用 `tests/lit/MC/Dadao`（23/23）+ `make check-lit`（26/26）等价替代；**未**改动 `Makefile`/测试布局（越界）。
- **符号/重定位操作数的拒绝属本任务对规则完整性的扩展**：任务书验收仅列举字面量，但「rd0 ⇒ imms18 MUST 为 0」的静态规则对**无法证明为 0 的符号**亦应拒绝（否则非法编码静默到达链接器）。若架构师判定应保持更窄范围（仅字面量），请指示回退。
- `DADAOAsmParser.cpp` 现 **1105 行**（口径 A >1000，已在 `INFRA-028t` 登记提醒，非本任务新增的违规）。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：AsmParser 改动逐行 + 新 lit 逐条 RUN + 补丁/源码一致性 + 反例门控（注入/还原含重建）+ 边界探针。

**逻辑正确性核对**：
- 检查位置：`matchAndEmitInstruction` 中 `ret` 进入 `MatchInstructionImpl` 之前；`ret`（riii）分解后 `Flat = [Token, rdHA(reg), imms18]`，`Flat.size()==3` 成立。
- 常量判定：`Flat[2]->isImm() && getImmExpr()==nullptr && getImm()==0` ⇒ `IsZero`。常量 0 ⇒ 放行；常量非 0 / 符号表达式 / 非立即数 ⇒ 报错。`ret rd0, foo` 实测 rc=1（修复首版漏洞）。
- 硬错误：用 `Error(...)`（返回 `true` ⇒ 汇编失败、非零退出码），未用 warning；实测 rc=1，lit `%not` 门控通过。
- 作用域：仅 `Mnemonic == "ret"` 且 `RdHA == DADAO::rd0`；`ret rd1, 0/42/foo`、`ret rd63, 0` 均 rc=0，非 rd0 不受影响。
- 边界：`ret rd0, 0x1`/`0x10` 报错；`ret rd0, 0` 通过；未改动 `ret` 编码（`imms18` 名与编码语义不变）。

| # | finding / 检查项 | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| 1 | 首版用 `isImm()`+`getImm()!=0` 漏掉符号操作数（`ret rd0, foo` rc=0 静默放行） | ✅已修 | 改判据为 `getImmExpr()==nullptr`（区分常量/表达式） | `ret rd0, foo` rc=1；`ret rd0, 0` rc=0；重新导出补丁 1119 行、`check-patch-tree` 67 OK |
| 2 | 错误信息含明确提示且不降 warning | ✅已验 | 信息含 `rdHA is rd0, so imms18 must be the constant 0 (use 'ret rd0, 0')` | 反例 rc=1（`Error` 级） |
| 3 | lit 用例可达 FAIL（每条 RUN 独立可失败） | ✅已验 | 3 条反例 RUN 用 `%not` + FileCheck | 门控注入后新 lit FAIL（`LLVM-027t-counterexample-gate.log`） |
| 4 | 反例注入须改到目标文件、可复原且含重建 | ✅已验 | sed 注入 `false &&`；`cp` 还原 | 源码/二进制 sha 注入前后逐字节一致；注入态 rc=0/FAIL，还原态 rc=1/PASS；`git status` 空 |
| 5 | 补丁须为 base+1 干净、断言①–⑨绿 | ✅已验 | 收敛 commit；`make_patch.py` 导出 | `HEAD=ee4a1d7cbea0 count=1 clean=True`；`67 patches OK` |
| 6 | 任务书字面命令 `llvm-lit tests/lit/MC/` 不可发现套件 | ⏸已披露（非代码缺陷） | 不改仓库布局；用 `MC/Dadao` + `make check-lit` 替代 | `LLVM-027t-lit-MC-root.log`（EXIT=2）；`MC/Dadao` 23/23、`check-lit` 26/26 |

**防造假确认**：本完成区所有数字均来自真实命令输出，逐条与 `.work/log/llvm/LLVM-027t-*.log` 对齐；反例门控含"注入→转 PASS/FAIL→还原→重建→回绿"全过程留证，未采信任何未执行结论。

**判决**：finding #1 已修并复验，其余为已验/已披露；无未修 finding。可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理
**审查时间**：2026-10-03
**审查范围**：正/反例验证、符号操作数判定、lit 回归、反例门控（独立注入/还原/重建）、补丁规范与行数、全量门控、完成区一致性。

---

##### 1. 正/反例验证（验收 1–4）

| # | 命令 | 真实输出 | RC |
|---|---|---|---|
| 1 | `echo 'ret rd0, 0' \| llvm-mc --triple=dadao-unknown-elf -show-encoding` | `; encoding: [0x76,0x00,0x00,0x00]`（无 error/warning） | **0** |
| 2 | `echo 'ret rd0, 1' \| llvm-mc ... -filetype=obj -o /dev/null` | `error: invalid 'ret': rdHA is rd0, so imms18 must be the constant 0 (use 'ret rd0, 0')` | **1** |
| 3 | `echo 'ret rd0, -1' \| llvm-mc ... -filetype=obj -o /dev/null` | 同 #2 错误信息 | **1** |
| 4a | `echo 'ret rd1, 0' \| llvm-mc ... -show-encoding` | `; encoding: [0x76,0x04,0x00,0x00]` | **0** |
| 4b | `echo 'ret rd1, 42' \| llvm-mc ... -show-encoding` | `; encoding: [0x76,0x04,0x00,0x2a]` | **0** |

**结论**：验收 1–4 全部通过，与完成区一致。

---

##### 2. 符号操作数 `ret rd0, foo`（验收附项）

| 命令 | 真实输出 | RC |
|---|---|---|
| `echo 'ret rd0, foo' \| llvm-mc ... -filetype=obj -o /dev/null` | `error: invalid 'ret': rdHA is rd0, so imms18 must be the constant 0 (use 'ret rd0, 0')` | **1** |

**源码逻辑核对**：
- `createImmExpr`（第126–134行）：对符号表达式设 `Kind=kImmediate`、`ImmExpr=E`（非 null）、`ImmVal=0`
- `createImm`（常量立即数）：设 `Kind=kImmediate`、`ImmExpr=nullptr`、`ImmVal=value`
- 检查逻辑（第1075–1076行）：`isImm() && getImmExpr() == nullptr && getImm() == 0`

**判定**：
- 工程师所述 "`createImmExpr` 会置 `ImmVal=0` ⇒ 仅 `isImm()`+`getImm()!=0` 会漏检" **属实**。源码确认 `createImmExpr` 将 `ImmExpr` 设为非 null 指针、`ImmVal` 设为0，而 `createImm` 将 `ImmExpr` 设为 `nullptr`。仅用 `isImm()+getImm()!=0` 无法区分符号与常量 0。
- `ret rd0, foo` 被拒绝（rc=1）**合理**：汇编期无法证明符号为 0，拒绝是保守正确做法（否则非法编码静默到达链接器）。非过窄，属规则完整性扩展，已在遗留问题中披露。

---

##### 3. lit 测试（验收 5–6）

| 命令 | 真实输出 | RC |
|---|---|---|
| `llvm-lit tests/lit/MC/Dadao/ret-rd0-legality.s -v` | `PASS: DADAO-MC :: ret-rd0-legality.s (1 of 1)`，1/1 (100.00%) | **0** |
| `llvm-lit tests/lit/MC/Dadao/ -v` | 23/23 PASS | **0** |
| `make check-lit` | 26/26 PASS（MC 23 + E2E 3） | **0** |
| `llvm-lit tests/lit/MC/` | `warning: unable to find test suite` / `error: did not discover any tests` | **2** |

**验收 6 字面路径不可用**：`tests/lit/MC/` 无 `lit.cfg.py`（配置在 `tests/lit/MC/Dadao/lit.cfg.py`），lit 报 `did not discover any tests`，EXIT=2。工程师声称属实。替代方案（`MC/Dadao` 23/23 + `make check-lit` 26/26）充分覆盖所有 MC 测试。

---

##### 4. 反例门控（独立注入/还原/重建）

**前状态**：
- 源码 sha256: `47f29bfbd9d9d951f841acd88daa06dc5feef6da349c9748096e138de408c8d9`
- 二进制 sha256: `aa2483bc242f2d483f09ef4649b90615e252a9b4d44a3cd9fd340e4531092c4a`
- 反例 rc=1: `ret rd0, 1` ✓ / `ret rd0, -1` ✓ / `ret rd0, foo` ✓

**注入**：`sed -i 's/if (!IsZero)/if (false \&\& !IsZero)/'`
- `grep -c 'false && !IsZero'` = 1 ✓
- `git diff --name-only` = `llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp`（非空）✓
- 源码 sha256: `7dc060b2d7898f387a4edc5077eab4d8e93c4819aa283a02e89a81ad02653ee5`（与前不同）✓
- 增量重建 `make build-mc JOBS=8` → BUILD_EXIT=0

**注入态验证**：
| 命令 | RC | 预期 |
|---|---|---|
| `ret rd0, 1` | **0** | 检查已禁用，应为 0 ✓ |
| `ret rd0, -1` | **0** | ✓ |
| `ret rd0, foo` | **0** | ✓ |
| `llvm-lit ret-rd0-legality.s` | **FAIL** (1/1 failed) | 反例不再报错，`%not` 门控失败 ✓ |

**还原**：`sed -i 's/if (false \&\& !IsZero)/if (!IsZero)/'`
- 源码 sha256: `47f29bfbd9d9d951f841acd88daa06dc5feef6da349c9748096e138de408c8d9`（与前一致）✓
- `git diff --name-only` 空 / `git status --porcelain` 空 ✓
- 增量重建 `make build-mc JOBS=8` → BUILD_EXIT=0
- 二进制 sha256: `aa2483bc242f2d483f09ef4649b90615e252a9b4d44a3cd9fd340e4531092c4a`（与前一致）✓

**还原态验证**：
| 命令 | RC | 预期 |
|---|---|---|
| `ret rd0, 1` | **1** | 检查已恢复，应为 1 ✓ |
| `ret rd0, 0` | **0** | 正例 ✓ |
| `llvm-lit ret-rd0-legality.s` | **PASS** (1/1) | ✓ |

**结论**：反例门控完整通过，注入→FAIL→还原→重建→PASS 全过程独立复现。源码/二进制 sha 逐字节回原，`git status` 干净。

---

##### 5. 补丁与不变量（验收 8）

| 检查项 | 命令/输出 | RC |
|---|---|---|
| 源码 base+1 | `git rev-list --count HEAD~1..HEAD` = 1 | 0 |
| 源码 clean | `git status --porcelain` = 空 | 0 |
| 源码 HEAD | `ee4a1d7cbea0` | — |
| `make check-patch-tree` | `2 component(s), 67 patches OK` | **0** |
| `make check-source-state` | `llvm-project: OK HEAD=ee4a1d7cbea0 count=1 clean=True` | **0** |

**补丁行数核对**：
- `git diff DADAOAsmParser.cpp.patch`：`@@ -1065,6 +1065,28 @@`，新增代码行 = 28 - 6 = **+22 行**
- 工程师声称 **+16 行**，实际 **+22 行**。差异 = 6 行。
- 实际新增内容（第1062–1082行）：注释 8 行 + 代码 14 行 = 22 行。

**⚠️ 差异**：工程师声称「相对 LLVM-026t 基线 **+16 行**」，实际 diff 为 **+22 行**。这是完成区数据错误，但不影响功能正确性（补丁内容正确、单 hunk、检查逻辑完整）。

---

##### 6. 全量门控

| 命令 | 真实输出 | RC |
|---|---|---|
| `make check` | `repository checks: PASS`；lit 26/26；check-patch-tree 67 OK；INTEG-003t 80/80 PASS；check-no-residue: PASS | **0** |

---

##### 7. 范围/越界 + 完成区一致性

- **越界**：仅改 `DADAOAsmParser.cpp.patch` + 新增 lit 文件 + `changelog.md`。未改 `Makefile`/测试布局/其他模块。无越界。
- **完成区一致性**：
  - 验收 1–4 数字（rc=0/0/1/1/0/0）与我的独立重跑一致 ✓
  - lit 23/23 + 26/26 一致 ✓
  - 反例门控 sha256 值一致 ✓
  - `llvm-lit tests/lit/MC/` EXIT=2 一致 ✓
  - **补丁行数不一致**：工程师写 +16 行，实际 +22 行 ⚠️

---

##### 判决：**Accepted**（附注）

**验收命令块在独立重跑下全部通过**：验收 1–8 均 PASS，反例门控独立复现，`make check` 全绿。

**附注**：
1. 完成区声称补丁 "+16 行"，实际 diff 为 **+22 行**。这是数据记录错误，不影响功能判定，建议工程师修正完成区描述。
2. `llvm-lit tests/lit/MC/` EXIT=2（非工程师首次声称的 EXIT=0，后更正为2），已用 `MC/Dadao` + `make check-lit` 充分替代。
3. 符号操作数 `ret rd0, foo` 的拒绝属规则完整性扩展（汇编期无法证明符号为 0），已在遗留问题中披露，供架构师定夺。