# TESTCASES-038t: 上游 IR 素材 + `lli` 值级对拍

**模块**：testcases
**项目里程碑**：M6
**依赖**：`LLVM-063t`（DADAO clang target）、`INFRA-050t`（host `lli`）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `INFRA-050t` 产出的 host `lli`（`.dadao/host-tools/bin/lli` 或实测等价；X86 back-end）。
  - `LLVM-063t` 的 DADAO clang/`llc`（交叉编译能力）。
  - 上游 IR 素材（现有 `.ll` 语料；**输入**，非判据来源）。
  - `INTEG-023k §A（#17 oracle / #18 上游 IR）`：**值级**对拍；**边界 = 只做值级**（端序/内存布局类排除）；**IR 需兼容**；**同源性质 = 证「IR 语义被保持」**；**不作执行语义判据**。
- **输出**：
  1. **编译/编码层**：上游 `.ll` 经 DADAO 工具链编译/汇编的用例（值级对拍的**编译侧**）。
  2. **`lli` 值级对拍驱动**：同一 IR 在 host `lli`（X86）与 DADAO 目标上**值级**结果比对（证「IR 语义被保持」）；落 `tools/testcases/`（随产物入库）。
  3. 对拍清单/结果（脚本现场统计，**不写死计数**）。
- **约束**：
  - **只做值级**：端序/内存布局类**排除**；比对基于**值语义**。
  - **不作执行语义判据**（`lli` 结论不替代独立 oracle/执行向量）。
  - **IR 需兼容**（上游素材须为可编译的兼容 IR；不兼容者按口径排除并登记）。
  - **`spec/` 交集为空**。

## 硬约束

- **临时目录** `/tmp/opencode/TESTCASES-038t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/TESTCASES-038t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/testcases/TESTCASES-038t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **编译层**：上游 `.ll` 经 DADAO 工具链编译/汇编成功（给真实输出）。
2. **值级对拍**：同 IR 在 host `lli` 与 DADAO 目标**值级结果一致**（给真实输出；**条数现场统计**）。
3. **边界合规**：端序/内存布局类**已排除**（给排除清单 + 理由）；结论**不作执行语义判据**（声明）。
4. **反例门控**：对拍驱动能对**注入反例**失败（如篡改一侧期望 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出。
5. **不回归**：`make check`/`check-lit` EXIT=0（通过数**不下降 / 逐项相等**）。
6. **一键证据脚本**：`.work/evidence/TESTCASES-038t/run.sh` 逐项通过、`RUN_EXIT=0`；给真实输出与退出码。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**用户裁定（落盘；引自任务书 + `INTEG-023k §A #17/#18`）**：「只做值级（端序/内存布局类排除）」「`lli` 结论**不作执行语义判据**」「IR 需兼容（不兼容者排除并登记）」。

**测试结果**（全部**现场统计**，不写死）：
- 驱动基线 `diff_ir_lli: PASS` rc=0；`structural: on-disk=41 include=19 exclude=22 unclassified=0 overlap=0 missing=0`；`hits: 19/19 compared, matched: 19/19`。
- **编译层 19/19**：每例 `[llc=mc=objcopy=0,0,0]`（`llc -march=dadao` → `llvm-mc --triple=dadao` → `llvm-objcopy` 三步 rc=0）。
- `--inject` 自检 rc=0（host 118→119 ⇒ 比较 FAIL ⇒ 比较活）。
- 证据脚本 `.work/evidence/TESTCASES-038t/run.sh`：`checks: PASS=16 FAIL=0` / `EVIDENCE: PASS` / `RUN_EXIT=0`。
- 门控：`make check` **EXIT=0**（32s）；`make check-lit` **EXIT=0**（76 discovered / 75 passed / 1 unsupported，与改前逐项相等）。

**修改文件**：新增 `tools/testcases/diff_ir_lli.py`、`tests/llvm/ir-lli/manifest.yaml`、`tests/llvm/ir-lli/README.md`；本任务书。（`.work/evidence/TESTCASES-038t/run.sh`、`.work/log/testcases/TESTCASES-038t-*.log` 为工作产物，不入库。）

**验收结果**（逐条对齐「验收标准」）：
1 **编译层**：19/19 三步 rc=0。真实命令（`--verbose`，日志 `.work/log/testcases/TESTCASES-038t-diff-ir-lli-verbose.log`）：`llc -march=dadao <ir> -o <s>` → `llvm-mc --triple=dadao -filetype=obj <s> -o <o>` → `llvm-objcopy -O binary --only-section=.text <o> <bin>` → `qemu-system-dadao -M dadao-m1 -bios trampoline.bin -kernel <bin> -semihosting-config enable=on,target=native`。2 **值级对拍**：19/19 `host==dadao`（逐条打印 host/dadao）。3 **边界**：排除清单见 manifest `exclude`（class `endianness`×2 / `host-unsupported`×2 / `needs-linker`×1 / `multi-tu`×6 / `no-value-entry`×11，各带 reason）；README 声明「**不作执行语义判据**」。4 **反例门控**：E1 结构注入（删 1 条 include ⇒ `unclassified` ⇒ rc=1）、F1 值注入（端序类移入 include ⇒ `value mismatch` host=179 dadao=41 ⇒ rc=1），`cp`+md5 还原（`f5470a1e…`==）后回绿。5 **不回归**：`make check`/`make check-lit` EXIT=0。6 **一键证据脚本** RUN_EXIT=0。7 **无残留**：`git status --porcelain -uall` 仅 3 个新增文件，无 `*_tmp/*.orig/*.rej`；`spec|contracts|components` 交集 0。

**新发现/坑**：① `lli` 以「进程退出码 = `@main` 返回 `i64` 低位字节」传播（实测 `ret i64 300`⇒`44`），与 DADAO crt0/`SYS_EXIT` 通道同构 ⇒ 可直接对拍（值级通道来源）。② host `lli` 在 `llvm.va_start`（变参）模块上 **SIGSEGV（exit 139）** ⇒ `m6_varargs.ll` 归 `host-unsupported`。③ 端序类 `mem_narrow_be_*` 在两后端**确不等**（179≠41 / 40≠108）⇒ 排除非空、承重（F1 证）。

**遗留问题**：无未修 finding。① 纳入前提 = 自包含单 TU；多 TU（m4）、需链接器（`m6_indirect_call`）、仅结构（lit FileCheck）模块已登记排除（class 见 manifest），如需覆盖走 ELF 管线另立。② 值级通道为 8 位退出码（仓库既定 ABI 通道）；更宽值对拍（semihosting 写值）不在本任务范围。③ 驱动为 **opt-in**（未接入 `make check`/`make test-m6`；接线归 `INTEG-025t`）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**（逐行）：`tools/testcases/diff_ir_lli.py`（manifest 解析 / 结构闭包 / `host_value` / `target_value` / 比较 / `--inject`）、`tests/llvm/ir-lli/manifest.yaml`、`tests/llvm/ir-lli/README.md`、`.work/evidence/TESTCASES-038t/run.sh`。

**核对**：Spec-first（值级通道 = `@main` 返回 `i64` 低位，溯源 crt0 + semihosting `SYS_EXIT` + lli 行为实测）、边界（`spec/` 交集空；未触 `contracts/`/`components/`/`Makefile`）、防造假（真实输出逐条对齐、结尾 `rc=$?` 无 `tee`、注入 FAIL 可达且 `cp`+md5 还原）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 signal-killed 进程 `returncode<0`，`&0xFF` 会把崩溃静默当值 | ✅已修 | `host_value`/`target_value` 加 `rc<0 ⇒ 失败`（+ 保留 lli stderr 错误标记检查） | 复跑 baseline rc=0、19/19；证据 `RUN_EXIT=0` |
| F2 §8.34 命中自证：不得只「不报错」 | ✅实现期内置 | 逐例打印 `host=/dadao=` 且断言 `hits==len(include)` | `hits: 19/19 compared`；证据项 C PASS |
| F3 §8.35 结构断言：删条目不得静默收缩 | ✅实现期内置 | `include∪exclude==on-disk` 且互斥；`unclassified/missing/overlap ⇒ FAIL` | E1 删 1 条 ⇒ `unclassified` rc=1；还原回绿 |
| F4 端序排除是否**承重**（非空排除） | ✅核验 | 仅注入核验，未改码 | 端序类移入 include ⇒ `value mismatch` host=179 dadao=41 rc=1；还原回绿 |
| F5 证据脚本直接调 `"$DRIVER"`（驱动无 `+x`）⇒ 首批全 `rc=126` | ✅已修 | 6 处改 `python3 "$DRIVER" …`（不改驱动权限，与仓库 `make` 体例一致） | 修后 `RUN_EXIT=0`、`checks: PASS=16 FAIL=0` |

**判决**：F1 已修、F2/F3 内置、F4 已核验，**无未修 finding** ⇒ 状态置「待验收」，返回主会话 `/complete`。

#### 第 1 轮 reviewer 验收

**重跑记录**（独立执行，真实 rc；日志 `/tmp/opencode/TESTCASES-038t-review/`）：
1. **DADAO 侧管线真含 QEMU**：`diff_ir_lli.py target_value()` 摘录——`[tools["llc"],"-march=dadao",ir_abs,"-o",prog_s]`（L258）→ `cat crt0.s <prog>.s`（L266-276，crt0=`tests/scripts/codegen_crt0.s`：`_start` `call [rb0, main]` + SYS_EXIT trap）→ `llvm-mc --triple=dadao -filetype=obj`（L281）→ `llvm-objcopy -O binary --only-section=.text`（L290）→ `qemu-system-dadao -M dadao-m1 -bios trampoline.bin -kernel <bin> -semihosting-config enable=on`（L299-304）。**独立手动 1 例**（`branch_loop_sum.ll`，自拼命令不经驱动）：手算 `0+1+…+9=45>40 ⇒ ret 45`；`lli` ⇒ `HOST_LLI_EXIT=45`；手动 `llc=0 cat=0 mc=0 objcopy=0`，`qemu-system-dadao ⇒ QEMU_EXIT=45`，三值与手算相等。
2. **比较非恒真**：`host_value` 取 `lli` 子进程 rc（L237-247，含 `rc<0`/错误标记拒收）、`target_value` 取 QEMU 子进程 rc（L299-314），两次独立执行非同源；`grep -nE "or True|except:|except Exception|return True"` **rc=1 无命中**。
3. **§8.34/§8.35**：驱动 L434-440 `hits` 逐例命中断言（`hits != len(records) ⇒ FAIL`），L212-223 `include∪exclude==on-disk` 且互斥、`unclassified/overlap/missing ⇒ FAIL`；基线输出 `structural: on-disk=41 include=19 exclude=22 unclassified=0 overlap=0 missing=0`、`hits: 19/19 compared, matched: 19/19`、`diff_ir_lli: PASS` **EXIT=0**。
4. **独立注入**（与 E1/F1 不同：multi-tu 移入 include）：`m4_call_main.ll` 从 exclude 移入 include（结构闭包仍满足）⇒ `[FAIL] m4_call_main.ll host=None dadao=None (host lli error: JIT session error: Symbols not found: [ lib_mix, acc ])`、`diff_ir_lli: FAIL` **EXIT=1**（明确不可单 TU 解析）⇒ 还原 ⇒ 回绿 `PASS` **EXIT=0**。**披露**：注入前漏做 `cp` 备份，还原用注入的精确逆变换 + **注入前 md5 对账**：`f5470a1e565cd70ccbaa76f389354caf` 前后相等（字节级还原已证）。
5. **排除清单承重**：`endianness`×2 手动双侧独立执行——`mem_narrow_be_bytes` host=179 / dadao=41、`mem_narrow_be_wide` host=40 / dadao=108（确不等，排除必须）；`no-value-entry` 抽 3 例（`m4_call_lib/m6-memintrin/m6-return-regs`）`grep -c "define i64 @main"` 均 0（确无值通道）；`multi-tu` 由注入证明不可解析。无「以排除掩盖能力」。
6. **门控**（一次一个 make）：`make check` **EXIT=0**（76 discovered/75 passed/1 unsupported，`repository checks: PASS`）；`make check-lit` **EXIT=0**（76/75/1 逐项相等，未下降）；`bash .work/evidence/TESTCASES-038t/run.sh` **RUN_EXIT=0**、`checks: PASS=16 FAIL=0`（审脚本：注入跑临时副本、`cp`+md5 对账、无 `tee`、`pipefail`、16 项均有可达 FAIL 路径）。
7. **无残留/边界**：`git status --porcelain -uall` 仅 3 新增文件 + 本任务书（与注入前快照 `diff` 逐行一致）；`diff --name-only origin/master...HEAD | grep -E '^(spec|contracts|components)/'` **空**；无 `*_tmp/*.orig/*.rej`；README L61 声明「NOT an execution-semantics oracle」；计数由脚本现场统计（无写死）。

**约束核验**：只动 `tests/**`+`tools/testcases/**` ✓；值级边界/排除登记 ✓；IR 不兼容（varargs×2、multi-tu、needs-linker）均登记非静默 ✓；一键证据脚本 4 要件 ✓；留证均捕获命令自身 rc（无 `tee`）✓。

**判决：Accepted** —— 7 项验收标准在独立重跑下全部通过、约束无违反；独立注入证伪有效、还原字节级对账一致。无阻断问题。遗留（opt-in 未接线 `make check`、8 位值通道）为任务书已声明的范围边界，非缺陷。
