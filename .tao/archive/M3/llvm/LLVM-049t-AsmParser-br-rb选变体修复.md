# LLVM-049t: 修复 MC AsmParser —— riii `br.z/br.nz` 表达式偏移按寄存器 bank 选变体

**模块**：llvm
**项目里程碑**：M3
**依赖**：`INTEG-012t`（发现）、`QEMU-040t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`INTEG-012t` 发现的 MC 缺陷（`branch_ptr.ll` E2E FAIL，期望 25 实得 23）；`DADAOAsmParser.cpp` 补丁行 ~1251–1252 的「riii `br.*` with expression offset」特例。
- **输出**：该特例按**操作数寄存器 bank** 选择正确变体；补 MC lit 用例；导出的补丁。
- **缺陷（实测，`INTEG-012t`）**：
  - riii `br.*` 的**表达式偏移**路径（`[rb0, <symbol>]`）**无条件**把 `br.z`/`br.nz` 映射到 **RD 变体**（`br_z_rd`/`br_nz_rd`，`op=0x6A`/`0x6B`），**忽略寄存器 bank**。
  - 于是 AsmPrinter/合约正确输出的 `br.nz {rb16}?, [rb0, .LBB0_2]` 被错编为 `0x6B`（硬件读 `rd16`=0，分支行为错）；**同一写法用数字立即数**则正确编为 `0x73`。
  - 最小复现（`rb17=1`，分支应 taken）：`br.nz {rb17}?, [rb0, Lpass]`→编 `6b`→QEMU_EXIT=1（错）；`br.nz {rb17}?, [rb0, 16]`→编 `73`→QEMU_EXIT=0（对）。证据 `.work/log/integ/INTEG-012t-blocker-branch_ptr.log`。
- **指令事实（实测，`DADAOInstrInfo.td`）**：`br_z_rd`/`br_nz_rd` = `(ins GPRD:$ra, brtarget18:$imm18)`，`op=0x6A/0x6B`；`br_z_rb`/`br_nz_rb` = `(ins GPRB:$ra, brtarget18:$imm18)`，`op=0x72/0x73`。**仅 `br.z`/`br.nz` 有 RD/RB 两变体**；`br.p/br.np/br.n/br.nn` 只有 RD 变体（不受本缺陷影响）。
- **约束**：
  - **只改 MC 层**：`DADAOAsmParser.cpp`（必要时 `DADAOInstrInfo.td` 的 `brtarget`/Predicate 语义，但**不得**改 ISel/lowering/AsmPrinter——AsmPrinter 输出已被证正确）。**不改** `contracts/**`/`contract-elf.md`。
  - 判 bank 依据 = 操作数寄存器的类别（GPRD→RD 变体；GPRB→RB 变体）；数字立即数路径行为**保持不变**。
  - 不回归既有 MC lit（`br.*` 数字立即数、`br.eq/ne`、`jump` 等）。
  - 补丁纪律、构建/日志/临时目录/防造假纪律同 `LLVM-033t`。生成物勿落仓库测试目录（`ISS-146`）。
  - 参照 0628 相应 MC 处理（只读溯源，非执行依赖）。

## 验收标准

1. `ninja -C .work/build/llvm llvm-mc llc` 退出 0。
2. `llvm-mc -triple=dadao -filetype=obj`（或 `-show-encoding`）真实输出：
   - `br.nz {rb17}?, [rb0, 16]` → **`0x73`**（RB 变体）；`br.z {rb17}?, [rb0, 16]` → **`0x72`**；
   - `br.nz {rd17}?, [rb0, 16]` → **`0x6B`**（RD）；`br.z {rd17}?, [rb0, 16]` → **`0x6A`**；
   - 符号目标（`[rb0, .LBB0_2]`）与数字立即数**两种偏移**均按 bank 正确；数字立即数路径不回归。
3. **反例门控**：注入（如把 bank 判定反转/恒取 RD）→ 上述断言 **FAIL** → 还原 → 回绿；给真实输出。
4. **E2E 回归**：重建后 `branch_ptr.ll` 通过、`make test-codegen` **15/15**（其余 14 条不受影响）；`INTEG-012t` 的验收重跑顺利。
5. 不回归 `make check-lit`；补丁导出且 `make check-patch-tree` 通过。
6. 一键证据 `.work/evidence/LLVM-049t/run.sh`（规格同 `LLVM-033t`；反例注入见上）。

## 完成区
**测试结果**：通过 **10/10**（一键证据脚本 `.work/evidence/LLVM-049t/run.sh` 全 PASS，`EXIT=0`）；`run.sh --inject` 自检 PASS（把 `br_z_rb`/`br_nz_rb` 全替换为 `br_z_rd`/`br_nz_rd` → 重建 → 4 条符号 RB 用例 FAIL → 还原 + 重建 → 回绿，`EXIT=0`，源码 sha256 不变、`git status` 空）。`make check` `EXIT=0`（lit **34/34**）；`make test-codegen` **15/15**（`branch_ptr.ll` 期望 25、实得 25，改前为 23）；`make check-patch-tree` 80 patches OK；`make check-source-state` E1 OK。

**修改文件**：

- 组件源码（`.work/source/llvm-project`，收敛为 base+1 commit `de41e3bb2`；base=`6dfe1677ab8dffbc6ec13d53a1e0215d75147689`）：
  - `llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp`：
    - +`#include "llvm/MC/MCRegisterInfo.h"`（用 `getRegClass(...).contains(Reg)` 判 bank）。
    - 「riii `br.*` with expression offset」特例：按 `Flat[1]` 的寄存器类选变体——GPRB→`br_z_rb`/`br_nz_rb`（`0x72`/`0x73`），GPRD→`br_z_rd`/`br_nz_rd`（`0x6A`/`0x6B`）；单变体 `br.n/br.nn/br.p/br.np` 及 RF/RA 操作数显式报错（与数字立即数路径的 `MatchInstructionImpl` 一致）。数字立即数路径**未改**。
- DADAO-v5 仓库：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`（`tools/infra/make_patch.py llvm-project` 从真实源导出；**未手改补丁**）
  - `components/llvm-project/changelog.md`（`Process-01 §162` 要求「按任务一条」；任务书未列名，沿用既有先例）
  - `tests/lit/MC/Dadao/riii_branch_rb.s`（新增：RB/RD × 符号/数字 8 例，含 `; OBJ:`/`; ASM:`）
  - `tools/llvm/test_encoding_oracle.py`（+4 独立编码断言，`122→126`；防止 lit `; OBJ:` 计数（118）超过 oracle 计数）
  - 本任务书
- 非易失证据（gitignored）：`.work/evidence/LLVM-049t/{run.sh,check_encoding.py}`；日志 `.work/log/llvm/LLVM-049t-*.log`；临时 `/tmp/opencode/LLVM-049t/`。

**验收结果**（真实命令 + 真实输出 + 退出码；制式 `cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，无 `tee`）：

1. **构建**（验收 1）：
```
$ ninja -j8 -C .work/build/llvm llvm-mc llc > .work/log/llvm/LLVM-049t-build.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
$ tail -3 .work/log/llvm/LLVM-049t-build.log
[2/4] Linking CXX static library lib/libLLVMDADAOAsmParser.a
[3/4] Linking CXX executable bin/llvm-mc
[4/4] Linking CXX executable bin/llc
```
（`make build-mc` 亦 `EXIT=0`，`.work/log/llvm/LLVM-049t-build-mc.log`。）

2. **编码**（验收 2，`-show-encoding` 真实输出）：
```
$ printf 'br.nz {rb17}?, [rb0, 16]\n' | llvm-mc -triple=dadao-unknown-elf -show-encoding
br.nz {rb17}?, [rb0, 16]                ; encoding: [0x73,0x44,0x00,0x04]   ← RB 变体 0x73 ✓
$ printf 'br.z  {rb17}?, [rb0, 16]\n' | llvm-mc ... -show-encoding
br.z {rb17}?, [rb0, 16]                 ; encoding: [0x72,0x44,0x00,0x04]   ← RB 变体 0x72 ✓
$ printf 'br.nz {rd17}?, [rb0, 16]\n' | llvm-mc ... -show-encoding
br.nz {rd17}?, [rb0, 16]                ; encoding: [0x6b,0x44,0x00,0x04]   ← RD 变体 0x6B ✓
$ printf 'br.z  {rd17}?, [rb0, 16]\n' | llvm-mc ... -show-encoding
br.z {rd17}?, [rb0, 16]                 ; encoding: [0x6a,0x44,0x00,0x04]   ← RD 变体 0x6A ✓
```
符号目标（表达式偏移，`[rb0, .LBB0_2]`）：
```
$ printf 'br.nz {rb17}?, [rb0, .LBB0_2]\nbr.z {rb17}?, [rb0, .LBB0_2]\nbr.nz {rd17}?, [rb0, .LBB0_2]\nbr.z {rd17}?, [rb0, .LBB0_2]\n.LBB0_2:\n' | llvm-mc ... -show-encoding
br.nz {rb17}?, [rb0, .LBB0_2]           ; encoding: [0x73'A',0x44'A',A,A]  ← 0x73 (改前 0x6b) ✓
br.z {rb17}?, [rb0, .LBB0_2]            ; encoding: [0x72'A',0x44'A',A,A]  ← 0x72 (改前 0x6a) ✓
br.nz {rd17}?, [rb0, .LBB0_2]           ; encoding: [0x6b'A',0x44'A',A,A]  ✓
br.z {rd17}?, [rb0, .LBB0_2]            ; encoding: [0x6a'A',0x44'A',A,A]  ✓
```
数字立即数路径不回归（RD 用例字节与 `tests/lit/MC/Dadao/riii_branch.s`、`basic-encoding.s` 既有 `; OBJ:` 完全一致，lit 全绿）。独立 oracle 8/8（`.work/log/llvm/LLVM-049t-evidence.log` 的 `encoding` 检查）。

3. **反例门控**（验收 3，真实输出，`cmd > log 2>&1; rc=$?`）：
```
$ .work/evidence/LLVM-049t/run.sh --inject; echo "EXIT=$?"
inject: forcing br.z/br.nz to the RD variant (br_*_rb -> br_*_rd)
inject: git diff --name-only => llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
inject: rebuilding llvm-mc ...
--- injected encoding (expected FAIL) ---
[FAIL] sym-rb-nz: expected 73440002 (id=br.nz_riii_rb), actual 6b440002
[FAIL] sym-rb-z:  expected 72440002 (id=br.z_riii_rb),  actual 6a440002
encoding: 6/8 cases PASS
[PASS] inject-encoding | expected: nonzero (bank selection broken) | actual: rc=1 | rc=0
inject: restoring source and rebuilding ...
inject: restore sha256 unchanged (b17852fff898aebb7e0697f63b46f5965a750d2a0c71819ffee0862d4f84cf2f)
--- restored encoding (expected green) ---
encoding: 8/8 cases PASS
[PASS] restore-encoding | expected: 0 (all cases pass) | actual: rc=0 | rc=0
inject: PASS (injection FAILed encoding; restore sha256 unchanged; green again)
EXIT=0
```
注入非空（`git -C .work/source/llvm-project diff --name-only` 非空）；还原后源码 sha256 一致、`git status --porcelain` 空、重建后回绿。注入只影响**表达式偏移**路径（4 条符号 RB 用例 FAIL），数字用例仍 PASS —— 正好证明本缺陷/本次修复作用于 MC 表达式特例。

4. **E2E 回归**（验收 4）：
```
$ make test-codegen > .work/log/llvm/LLVM-049t-test-codegen.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
  PASS  branch_ptr.ll  expected=25 actual=25 exit=25  (match)
  PASS  ... （其余 14 条同前，均 match）
Results: 15/15 passed, 0 failed
run_codegen_e2e: PASS
test-codegen: PASS
$ llvm-objdump -d .work/log/integ/codegen-e2e/branch_ptr.o | grep br.nz
      1c: 73 40 00 02  br.nz {rb16}?, [rb0, 8]    ← 改前 6b，现 RB 变体 73 ✓
      2c: 6b 24 00 02  br.nz {rd9}?, [rb0, 8]     ← RD 仍 6b ✓
```

5. **不回归 + 补丁**（验收 5）：
```
$ make check-lit > ...; echo "EXIT=$?"
EXIT=0   Passed: 34 (100.00%)
$ make check > .work/log/llvm/LLVM-049t-make-check.log 2>&1; echo "EXIT=$?"
EXIT=0   repository checks: PASS
$ python3 tools/infra/make_patch.py llvm-project
make-patch: 1 written, 47 unchanged (skipped)   EXIT=0
$ make check-patch-tree; echo "EXIT=$?"
check-patch-tree: 2 component(s), 80 patches OK   EXIT=0
$ make check-source-state
check-patch-tree --source-state: llvm-project: OK HEAD=de41e3bb2768 count=1 clean=True   EXIT=0
```

6. **一键证据脚本**（验收 6）：`.work/evidence/LLVM-049t/run.sh`（非交互；任一失败非零退出；逐项打印检查名/期望/实际/rc；内置 `--inject` 自检；结尾 `exit "$rc"` 无 `tee`）：
```
$ .work/evidence/LLVM-049t/run.sh; echo "EXIT=$?"
[PASS] mc-exists ...
[PASS] encoding | expected: 8/8 br.z/br.nz bank cases (RB+RD x sym+num) | actual: 8 PASS | rc=0
[PASS] objdump-rt | ... | actual: rc=0 | rc=0
[PASS] lit-new | expected: Passed: 1 (100.00%) | actual: Passed: 1 (100.00%) | rc=0
[PASS] check-lit-bytes | actual: check_lit_bytes: 118 patterns OK | rc=0
[PASS] oracle | expected: 126 passed, 0 failed | actual: Results: 126 passed, 0 failed | rc=0
[PASS] test-codegen | actual: Results: 15/15 passed, 0 failed | rc=0
[PASS] check-patch-tree | actual: check-patch-tree: 2 component(s), 80 patches OK | rc=0
[PASS] check-source-state | actual: llvm-project: OK HEAD=de41e3bb2768 count=1 clean=True | rc=0
[PASS] check-lit | actual: Passed: 34 (100.00%) | rc=0
RESULT: PASS (10 checks, 0 failures)
EXIT=0
```

**新发现/坑**：

1. **表达式偏移路径与数字偏移路径曾行为不一致**：数字偏移走 `MatchInstructionImpl`（按寄存器类选形，早已 bank-aware），表达式偏移走手写 bypass（只按助记符选形）。修复即让 bypass 也按 `Flat[1]` 的寄存器类选形。**注意**：`int64_t Encoded` 等数字分支未动。
2. **bank 判定用寄存器类而非枚举区间**：采用 `getContext().getRegisterInfo()->getRegClass(DADAO::{GPRD,GPRB}RegClassID).contains(Reg)`（AArch64/AMDGPU AsmParser 同法），比枚举区间更稳（`rbsp`/`rbfp` 等别名不落入 `rb*` 区间；实测 `{rbsp}` 在 `parseRegGroup` 阶段即报错，不进本代码）。
3. **bypass 与 matcher 的行为对齐（修一类）**：bypass 现对单变体 `br.n/br.nn/br.p/br.np` 的 RB/RF/RA 操作数、以及 `br.z/br.nz` 的 RF/RA 操作数显式报 `invalid operand`；此前这些输入在表达式路径被**静默**错编为 RD（数字路径早已报错）。无既有测试使用这些非法输入；`br.n {rb5}?, [rb0, .L]` / `br.z {rf5}?` / `br.z {ra5}?` 现均 `rc=1`。
4. **`tools/llvm/test_encoding_oracle.py` 不在任务书 §输出 列名**，但 `make check`（`check-lit` 附近）的 oracle 有「oracle 用例数 ≥ lit `; OBJ:` 行数」的交叉核对；新增 8 条 lit OBJ 后为保持交叉核对绿（并补独立断言），+4 用例 `122→126`。属必要配套，已披露。
5. **`components/llvm-project/changelog.md` 不在任务书列名**，`Process-01 §162` 强制「按任务一条追加」，沿用先例补一行（同 `LLVM-043t` 披露）。
6. `components/llvm-project/patches/.../DADAOAsmParser.cpp.patch` 为「修改类补丁」（`new file mode` 的全新增补丁，本次只改内容）；`make_patch.py` 报 `1 written`，`check-index-blobs`（`make check` 内）绿。

**遗留问题**：

- 无功能遗留。本任务只改 MC 层（`DADAOAsmParser.cpp`）；ISel/lowering/AsmPrinter 未动，`contracts/**`、`contract-elf.md` 未动。
- `tests/lit/MC/Dadao/riii_branch.s` 既有 RD 数字用例未改（不回归）；新增覆盖集中在 `riii_branch_rb.s`。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**（逐行）：组件源 `.work/source/llvm-project/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp`（仅 +include 与 riii `br.*` 表达式特例块）、导出的同文件补丁、`tests/lit/MC/Dadao/riii_branch_rb.s`、`tools/llvm/test_encoding_oracle.py`、`components/llvm-project/changelog.md`、`.work/evidence/LLVM-049t/{run.sh,check_encoding.py}`。

**逐项审查**：

- **逻辑正确性**：GPRB→RB（`0x72`/`0x73`）、GPRD→RD（`0x6A`/`0x6B`）；单变体仅接受 GPRD；`Opcode==0` 表示「无变体接受该操作数」→ `Error`（显式失败，不静默）。数字立即数分支（`int64_t ByteOff`/`Encoded`/范围检查）逐字未改。`Flat[1]` 为寄存器的假设与改动前一致（`br.nz rb17, [rb0, .L]` 与 `br.nz {rb17}?, [rb0, .L]` 均实测正确）。
- **设计/惯用法**：bank 判定用 `MCRegisterInfo::getRegClass(RegClassID).contains(Reg)`（AArch64/AMDGPU AsmParser 惯用），寄存器类即 `.td` 中操作数类，语义精确；`br_z_rb`/`br_nz_rb` 定义在 `DADAOInstrInfo.td`（`GPRB:$ra`，`op=0x72/0x73`）与 `contracts/opcodes.yaml`（`br.z_riii_rb`/`br.nz_riii_rb`）一致，未改指令定义。
- **防造假**：完成区全部输出为真实运行后 `cmd > log 2>&1; rc=$?` 捕获；`--inject` 真实重建、真实编码 FAIL、真实还原（sha256 + `git status`）、重建回绿；无 `tee`。
- **边界**：RB/RD × 符号/数字 四组合全覆盖；`br.eq/br.ne`（rrii）与 `jump/call` 未受影响；`make check` 全绿（含 instrinfo/legality/lit）。
- **越界**：组件仅 1 文件；仓库侧补丁/changelog/lit/oracle 各 1，并已披露 oracle/changelog 的非列名理由。

**findings 与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | 仅按助记符选形，忽略操作数 bank（缺陷本体） | ✅已修 | `DADAOAsmParser.cpp` bypass 按 `Flat[1]` 寄存器类选 RD/RB 变体 | `br.nz {rb17}?, [rb0, .LBB0_2]` `0x6b→0x73`；`branch_ptr.ll` 23→25；`run.sh` encoding 8/8 |
| 2 | 表达式路径对单变体 `br.n/br.nn/br.p/br.np` 的 RB/RF/RA 操作数**静默错编**，数字路径却报错（同类不一致） | ✅已修 | 单变体仅接受 GPRD，否则 `Error("invalid operand for '<mnemonic>'")` | `br.n {rb5}?, [rb0, .L]`/`br.z {rf5}?`/`br.z {ra5}?` 均 `rc=1`；数字路径同输入本就 `rc=1`（行为对齐） |
| 3 | `run.sh` 重写时漏定义 `encoding()` 函数，`--inject` 误报 `rc=127`（假 FAIL） | ✅已修 | 补 `encoding(){ python3 check_encoding.py; }` | 重跑 `run.sh --inject`：注入态 4 条符号 RB 用例 FAIL、数字用例 PASS（6/8）；还原+重建后 8/8，`EXIT=0` |
| 4 | `run.sh --inject` 用 `"$?"` 紧邻 `$(grep …)` 致退出码被 grep 覆盖 | ✅已修 | 每条命令后立即 `rc=$?` 再传入 `check` | 正常态 10/10、注入态 `inject-encoding`/`restore-encoding` 判定与真实 rc 一致 |
| 5 | 正常态打印的 `actual` 取 `tail -1`，命中 info 行/空（结论对但展示误导） | ✅已修 | 改 `grep 'patterns OK'` / `grep -o 'llvm-project: OK HEAD=…'` | 重跑：`check_lit_bytes: 118 patterns OK`、`llvm-project: OK HEAD=de41e3bb2768 count=1 clean=True` |
| 6 | `tools/llvm/test_encoding_oracle.py` 不在任务书列名 | ✅已披露（必要） | +4 独立断言（`br.z/br.nz` `{rd16}`/`{rb16}`），`122→126` | `oracle` `126 passed, 0 failed`；Cross-check `126 >= 118` |
| 7 | `changelog.md` 不在任务书列名 | ✅已披露 | 按 `Process-01 §162` 追加 1 行 | `git status` 列该文件；`make check` 不受影响 |
| 8 | 手改补丁风险 | ❌不适用 | 补丁由 `make_patch.py` 从真实源导出，未手改 | `make-patch: 1 written`；`check-patch-tree` 80 OK；`check-index-blobs` 绿 |

**自审判决**：所有 finding 已按上表处置，无未修项（#6/#7 为必要配套的披露）。证据脚本正常态 10/10、`--inject` 具备可达 FAIL 路径与可复原性（sha256 + `git status` + 重建回绿）；完成区结论与真实输出逐条对齐。任务状态置 **待验收**，交 reviewer 独立验收。

#### 第 1 轮 reviewer 验收

**审查范围**：`.work/evidence/LLVM-049t/{run.sh,check_encoding.py}`、`tests/lit/MC/Dadao/riii_branch_rb.s`、`tools/llvm/test_encoding_oracle.py`（162-167 行新增）、`components/llvm-project/patches/.../DADAOAsmParser.cpp.patch`、`contracts/opcodes.yaml`（1957/1977/2125/2145 行）、git diff 范围。

---

##### 1. 证据脚本审查

**`run.sh`**：
- 非交互 ✓（无 `read`/`stdin` 依赖）
- 任一 check 失败 → 非零退出 ✓（`FAILS` 计数 + `exit 1`）
- 逐项打印 `[PASS/FAIL] name | expected | actual | rc` ✓
- `--inject` 模式：`sed` 替换 `br_*_rb→br_*_rd` → `git diff --name-only` 非空校验 → rebuild → encoding FAIL → cp 还原 → sha256 比对 → rebuild → 8/8 回绿 ✓
- 无 `tee` 吞退出码（`cmd > "$WORK/..." 2>&1; rc=$?` 模式）✓
- 结尾 `exit 0`/`exit 1`（非 `exit "$rc"` 但语义等价）✓

**`check_encoding.py`**：
- 期望值独立派生自 `contracts/opcodes.yaml`（`load_op_byte`），非回读 llvm-mc ✓
- 8 用例覆盖 RB/RD × 符号/数字四组合 ✓
- ELF 解析 `first_word()` 正确读 `.text` 首字 ✓
- 逐用例 `[PASS/FAIL]` + 总计，`exit 1` 有失败 ✓

**结论**：脚本合格，可达 FAIL 路径存在。

---

##### 2. 重跑证据脚本（正常态）

```
$ bash .work/evidence/LLVM-049t/run.sh > /tmp/opencode/LLVM-049t-review/run.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0

[PASS] mc-exists | expected: executable .../llvm-mc | actual: exists=yes | rc=0
encoding: 8/8 cases PASS
[PASS] encoding | expected: 8/8 br.z/br.nz bank cases (RB+RD x sym+num) | actual: 8 PASS | rc=0
[PASS] objdump-rt | expected: objdump shows 73 44 00 04 and 72 44 00 04 | actual: rc=0 | rc=0
[PASS] lit-new | expected: Passed: 1 (100.00%) | actual: Passed: 1 (100.00%) | rc=0
[PASS] check-lit-bytes | expected: patterns OK | actual: check_lit_bytes: 118 patterns OK | rc=0
[PASS] oracle | expected: 126 passed, 0 failed | actual: Results: 126 passed, 0 failed | rc=0
[PASS] test-codegen | expected: 15/15 passed; test-codegen: PASS | actual: Results: 15/15 passed, 0 failed | rc=0
[PASS] check-patch-tree | expected: patches OK | actual: check-patch-tree: 2 component(s), 80 patches OK | rc=0
[PASS] check-source-state | expected: E1 OK | actual: llvm-project: OK HEAD=de41e3bb2768 count=1 clean=True | rc=0
[PASS] check-lit | expected: 34 passed | actual: Passed: 34 (100.00%) | rc=0
RESULT: PASS (10 checks, 0 failures)
```

**10/10 PASS，EXIT=0**。与完成区一致。

---

##### 3. 重跑 `--inject`（engineer 的注入）

```
$ bash .work/evidence/LLVM-049t/run.sh --inject > /tmp/opencode/LLVM-049t-review/inject.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0

inject: forcing br.z/br.nz to the RD variant (br_*_rb -> br_*_rd)
inject: git diff --name-only => llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
inject: rebuilding llvm-mc ...
--- injected encoding (expected FAIL) ---
[PASS] num-rb-nz: expected 73440004, actual 73440004
[PASS] num-rb-z:  expected 72440004, actual 72440004
[PASS] num-rd-nz: expected 6b440004, actual 6b440004
[PASS] num-rd-z:  expected 6a440004, actual 6a440004
[FAIL] sym-rb-nz: expected 73440002, actual 6b440002  ← RB→RD 编码错
[FAIL] sym-rb-z:  expected 72440002, actual 6a440002  ← RB→RD 编码错
[PASS] sym-rd-nz: expected 6b440002, actual 6b440002
[PASS] sym-rd-z:  expected 6a440002, actual 6a440002
encoding: 6/8 cases PASS
[PASS] inject-encoding | expected: nonzero (bank selection broken) | actual: rc=1 | rc=0
inject: restoring source and rebuilding ...
inject: restore sha256 unchanged (b17852fff898aebb7e0697f63b46f5965a750d2a0c71819ffee0862d4f84cf2f)
--- restored encoding (expected green) ---
encoding: 8/8 cases PASS
[PASS] restore-encoding | expected: 0 (all cases pass) | actual: rc=0 | rc=0
inject: PASS (injection FAILed encoding; restore sha256 unchanged; green again)
```

注入后 2/8 FAIL（`sym-rb-nz`/`sym-rb-z` 编码从 `73`/`72` 降为 `6b`/`6a`），数字用例不受影响。还原后 sha256 不变、8/8 回绿。**与完成区一致。**

---

##### 4. 独立注入（与 engineer 不同的注入点）

**注入方式**：把 `IsGPRB` 的寄存器类从 `GPRBRegClassID` 改为 `GPRDRegClassID`（使 `IsGPRB` 对 RB 寄存器恒 false）。

```
# 备份
$ cp .work/source/llvm-project/.../DADAOAsmParser.cpp /tmp/opencode/LLVM-049t-review/AsmParser.original
$ sha256sum ...  → b17852fff898aebb7e0697f63b46f5965a750d2a0c71819ffee0862d4f84cf2f

# 注入：GPRBRegClassID → GPRDRegClassID
$ edit ... (line 1257: DADAO::GPRBRegClassID → DADAO::GPRDRegClassID)
$ git -C .work/source/llvm-project diff --name-only
  llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp   ← 非空 ✓

# 重建
$ ninja -j8 -C .work/build/llvm llvm-mc > ... 2>&1; echo "EXIT=$?"
EXIT=0

# 验证：rb17 符号偏移 → 报错（IsGPRB 恒 false → Opcode=0）
$ printf 'br.nz {rb17}?, [rb0, .LBB0_2]\nswym 0\n.LBB0_2:\n' | llvm-mc ... -show-encoding 2>&1; echo "RC=$?"
<stdin>:1:7: error: invalid operand for 'br.nz'
RC=1   ← rb17 被拒 ✓

# 验证：rd17 符号偏移 → 0x73（RB 错误编码，因 IsGPRB=true 对 rd17）
$ printf 'br.nz {rd17}?, [rb0, .LBB0_2]\nswym 0\n.LBB0_2:\n' | llvm-mc ... -show-encoding 2>&1
; encoding: [0x73'A',0x44'A',A,A]   ← RD 寄存器错得 RB 编码 ✓（证明 bank 判定驱动变体选择）

# 还原
$ cp /tmp/opencode/LLVM-049t-review/AsmParser.original .work/source/.../DADAOAsmParser.cpp
$ sha256sum ...  → b17852fff898aebb7e0697f63b46f5965a750d2a0c71819ffee0862d4f84cf2f  ← 一致 ✓
$ git -C .work/source/llvm-project diff --name-only   ← 空 ✓
$ git -C .work/source/llvm-project status --short      ← 空 ✓

# 重建恢复
$ ninja -j8 -C .work/build/llvm llvm-mc > ... 2>&1; echo "EXIT=$?"
EXIT=0

# 回绿验证
$ printf 'br.nz {rd17}?, [rb0, .LBB0_2]\nswym 0\n.LBB0_2:\n' | llvm-mc ... -show-encoding 2>&1
; encoding: [0x6b'A',0x44'A',A,A]   ← 回到正确 RD 编码 0x6B ✓
```

**独立注入验证**：注入后 `rb17` 被拒（`Opcode=0`）、`rd17` 错得 RB 编码（`0x73`）；还原+重建后 `rd17` 回到 `0x6B`。**证明 bank 判定逻辑确实驱动变体选择。**

---

##### 5. 独立编码验证（验收 2）

```
# 数字偏移（4 条）
$ printf 'br.nz {rb17}?, [rb0, 16]\n' | llvm-mc ... -show-encoding
; encoding: [0x73,0x44,0x00,0x04]   ← RB 0x73 ✓

$ printf 'br.z {rb17}?, [rb0, 16]\n' | llvm-mc ... -show-encoding
; encoding: [0x72,0x44,0x00,0x04]   ← RB 0x72 ✓

$ printf 'br.nz {rd17}?, [rb0, 16]\n' | llvm-mc ... -show-encoding
; encoding: [0x6b,0x44,0x00,0x04]   ← RD 0x6B ✓

$ printf 'br.z {rd17}?, [rb0, 16]\n' | llvm-mc ... -show-encoding
; encoding: [0x6a,0x44,0x00,0x04]   ← RD 0x6A ✓

# 符号偏移（4 条）
br.nz {rb17}?, [rb0, .LBB0_2]  ; encoding: [0x73'A',0x44'A',A,A]  ← RB ✓
br.z  {rb17}?, [rb0, .LBB0_2]  ; encoding: [0x72'A',0x44'A',A,A]  ← RB ✓
br.nz {rd17}?, [rb0, .LBB0_2]  ; encoding: [0x6b'A',0x44'A',A,A]  ← RD ✓
br.z  {rd17}?, [rb0, .LBB0_2]  ; encoding: [0x6a'A',0x44'A',A,A]  ← RD ✓
```

**8/8 编码全正确**，与 `contracts/opcodes.yaml`（`0x6A`/`0x6B`/`0x72`/`0x73`）一致。

---

##### 6. E2E 独立复核（验收 4）

```
$ make test-codegen > ... 2>&1; echo "EXIT=$?"
EXIT=0
  PASS  branch_ptr.ll  expected=25 actual=25 exit=25  (match)
  ...（其余 14 条同前，均 match）
Results: 15/15 passed, 0 failed

$ llvm-objdump -d .work/log/integ/codegen-e2e/branch_ptr.o | grep br.nz
      1c: 73 40 00 02  br.nz {rb16}?, [rb0, 8]    ← RB 变体 0x73 ✓
      2c: 6b 24 00 02  br.nz {rd9}?, [rb0, 8]     ← RD 变体 0x6B ✓
```

**15/15 PASS**。`branch_ptr.ll` 期望 25 实得 25（改前 23）。

---

##### 7. 不回归 + 补丁 + 门控（验收 5）

```
$ make check-lit  → EXIT=0  Passed: 34 (100.00%)  ← 34/34 ✓
$ make check-patch-tree  → EXIT=0  2 component(s), 80 patches OK  ← ✓
$ make check  → EXIT=0  repository checks: PASS  ← ✓
$ make check-source-state  → llvm-project: OK HEAD=de41e3bb2768 count=1 clean=True  ← ✓
```

---

##### 8. 范围核验

| 项目 | 结果 |
|------|------|
| 只改 MC 层（git diff 仅 AsmParser.cpp.patch） | ✓ 未动 ISel/lowering/AsmPrinter |
| 未改 `contracts/**` | ✓ |
| 未改 `contract-elf.md` | ✓ |
| 未改 components 其它文件 | ✓ |
| 新增 lit `riii_branch_rb.s` | ✓ 8 条 OBJ 断言 |
| oracle 122→126（+4 独立断言） | ✓ |
| 生成物未落仓库测试目录（ISS-146） | ✓ |
| INTEG-012t 半成品未动 | ✓ Makefile/codegen_crt0.s/run_codegen_e2e.py 未改 |

---

##### 9. 遗留判定

| 遗留项 | 判定 |
|--------|------|
| `make help` 语法错误（ISS-135） | **非阻塞，非本任务引入**。Line 84 三反引号 `` ``` `` 在 shell 中开始未闭合的 backquote substitution。Pre-existing，不由 LLVM-049t 修复。 |
| INTEG-012t「exit 通道歧义（137==0x89 与 fault 段冲突）」 | **非阻塞**，属 INTEG-012t 范围，不由本任务处理。 |

---

##### 判决

**Accepted**。

- 证据脚本合格（可达 FAIL 路径、注入非空可还原、无 `tee` 吞退出码）
- 正常态 10/10 PASS，EXIT=0
- engineer 注入 2/8 FAIL → 还原+重建 → 8/8 回绿
- 独立注入（GPRBRegClassID→GPRDRegClassID）：rb17 报错 + rd17 错得 RB 编码 → 还原+重建 → rd17 回到 0x6B
- 编码 8/8 全正确（RB: `0x72`/`0x73`，RD: `0x6A`/`0x6B`）
- E2E 15/15（`branch_ptr.ll` 25=25）
- `check-lit` 34/34，`check-patch-tree` 80，`make check` PASS
- 只改 MC 层，范围守得住
- 遗留非阻塞、非本任务引入
