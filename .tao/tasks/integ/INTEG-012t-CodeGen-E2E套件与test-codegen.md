# INTEG-012t: CodeGen E2E 套件 + `make test-codegen`

**模块**：integ
**项目里程碑**：M3
**依赖**：`LLVM-041t`、`TESTCASES-026t`、`INFRA-035t`、`QEMU-040t`（**新增指令 `sub.o rd,rb,rb` 的 QEMU trans；E2E 执行前置**）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`LLVM-041t` 的 llc/`.s`/obj/flat-binary 通路；`TESTCASES-026t` 的 `tests/codegen/*.ll` + `expected.yaml`；`tests/scripts/trampoline.bin`（`gen_trampoline.py`，`ADR-0004` 双镜像启动：`-bios trampoline -kernel test.bin`、RAM 基址 `0xffff_0000_0000`、退出码 = exit port 写入值）。
- **输出**：
  - `tests/scripts/codegen_crt0.s`（或等价）：最小启动桩 `_start`——建立/沿用 SP，`call main`，将返回值（`rd31`）写入 exit port（`0xffff_8000_0000`，地址用 `set.zw`/`or.w` 构造），`swym` 停机。**注意**：无链接器，故桩与 `llc` 产物必须合并为**单一 `.s`（单 TU 自包含）**再汇编。
  - `tools/integ/run_codegen_e2e.py`：fail-closed 驱动的 E2E 门（**非 lit 退出码**，直接比较 guest 退出码 vs `expected.yaml`）。
  - `Makefile`：新增 `test-codegen` 目标（复用 `LIT_BIN`/构建目录约定；前置 `build-mc`+`build-qemu`；任何用例不符即非零退出）。
  - `.work/log/integ/INTEG-012t-*.log`（完整命令输出）。
- **约束**：
  - **单 TU 自包含**（`ADR-0003 §D5`）：`llc` 产物 `.s` + `codegen_crt0.s` 拼接为一个 `.s`；段内标签就地解析，无跨 object 链接、无 LLD。
  - **链路固定**：`llc -march=dadao <prog.ll>` → `.s`；`cat crt0.s prog.s` → `.s`；`llvm-mc -triple=dadao -filetype=obj` → `.o`；`llvm-objcopy -O binary --only-section=.text`（+按需多段拼接）→ `.bin`；`timeout N qemu-system-dadao -M dadao-m1 -bios <trampoline> -kernel <bin> -display none -nographic` → **进程退出码 = guest 退出码**。
  - **判据**：每用例 guest 退出码 == `expected.yaml` 期望值 ⇒ PASS；不等/超时/负例（fault 码 `0x80|cause`）⇒ FAIL。逐用例打印「名字 + 期望 + 实际 + 退出码」。
  - **门槛**：`make test-codegen` 全绿；**≥1 算术 + ≥1 访存 + ≥1 分支 + ≥1 调用**函数端到端（与 `TESTCASES-026t` 覆盖矩阵一致）；并覆盖**大端窄访存**（C13/`ADR-0018（C13）`，显式核对字节偏移）、**指针算术**（C14/`ADR-0018（C14）`，`add.o`（orrr，rb 目的）base+offset / `cmp.uo`（orrr `dbb`））与 **`ptr−ptr` 指针差**（后端选出 `sub.o_orrr_dbb`，QEMU 由 `QEMU-040t` 支持执行）各 ≥1。
  - **反例门控**（强制）：驱动内置 `--inject` 或测试脚本注入反例（改一条期望值 / 把一个函数的操作数改错 → 预期 FAIL，再还原 → 回绿），完成区给出真实输出；**注入后须验证 `git diff --name-only` 非空且还原含重建**。
  - **不引入** LLD、不实现完整重定位；**不**扩 `contract-elf.md §2–§4`。
  - 不改 `components/**`；`Makefile` 改动与 `INFRA-035t` 串行（同改共享文件）。
  - 留证禁 `tee` 吞退出码（用 `cmd > log 2>&1; rc=$?`）；**不提交 git**。

## 验收标准

1. `make test-codegen` 退出 0；输出逐用例「名字/期望/实际/退出码」；四类函数各 ≥1 通过。
2. 至少一个用例的链路每一步真实执行（`llc`/`llvm-mc`/`llvm-objcopy`/`qemu` 均退出 0），完整命令与输出留存 `.work/log/integ/`。
3. 反例门控：注入 → 预期 FAIL（非零退出）→ 还原 → 回绿；给出真实输出与 `git` 还原证据（含重建）。
4. 不回归 `make check-lit`（MC+E2E 31/31）。
5. `make check-no-residue` / `git status --untracked-files=all` 干净（除本任务应有改动）。

## 完成区

> **已完成：`make test-codegen` 全绿（15/15）。** 上一轮被一处**既有 MC AsmParser 缺陷**阻塞（`branch_ptr.ll` expected 25、actual 23）；该缺陷已由 **`LLVM-049t`** 修复并验证。本轮确认工具最新（ninja 增量、`no work to do`）后重跑，**15/15 PASS**。三件交付物（`tests/scripts/codegen_crt0.s`、`tools/integ/run_codegen_e2e.py`、`Makefile::test-codegen`）与一键证据脚本均落地并真实运行。

**测试结果**（全绿）：
- `ninja -j8 -C .work/build/llvm llc llvm-mc llvm-objcopy` → **EXIT=0**（`no work to do`，工具已是最新；LLVM-049t 的修复已在二进制内）。
- `make test-codegen` → **EXIT=0**；逐用例「名字/期望/实际/退出码」：
```
  PASS  arith_add_sub_neg.ll  expected=246 actual=246 exit=246  (match)
  PASS  arith_const_hi_wyde.ll  expected=238 actual=238 exit=238  (match)
  PASS  mem_store_load_offset.ll  expected=77 actual=77 exit=77  (match)
  PASS  mem_narrow_be_bytes.ll  expected=41 actual=41 exit=41  (match)
  PASS  mem_narrow_be_wide.ll  expected=236 actual=236 exit=236  (match)
  PASS  branch_loop_sum.ll  expected=45 actual=45 exit=45  (match)
  PASS  branch_eq_ne.ll  expected=16 actual=16 exit=16  (match)
  PASS  branch_ptr.ll  expected=25 actual=25 exit=25  (match)
  PASS  call_direct_ret.ll  expected=9 actual=9 exit=9  (match)
  PASS  call_multiarg_stack.ll  expected=171 actual=171 exit=171  (match)
  PASS  call_narrow_args.ll  expected=137 actual=137 exit=137  (match)
  PASS  call_ptr_bank.ll  expected=42 actual=42 exit=42  (match)
  PASS  ptr_add_offset.ll  expected=171 actual=171 exit=171  (match)
  PASS  ptr_diff_pos.ll  expected=7 actual=7 exit=7  (match)
  PASS  ptr_diff_neg.ll  expected=249 actual=249 exit=249  (match)

Results: 15/15 passed, 0 failed
run_codegen_e2e: PASS
test-codegen: PASS
```
- `bash .work/evidence/INTEG-012t/run.sh` → **EXIT=0**（全 PASS，含文件级注入→FAIL→还原→回绿 + 驱动 `--inject` 自检）。
- `make check-lit` → **EXIT=0**（`Passed: 34 (100.00%)`）；`make check` → **EXIT=0**（`repository checks: PASS`）；`make check-no-residue` → **EXIT=0**。
- 覆盖点核对（E2E 实测，逐条）：四类算术（`arith_*`）/访存（`mem_*`）/分支（`branch_*`）/调用（`call_*`）各 ≥1 ✓；**大端窄访存** `mem_narrow_be_bytes`=41、`mem_narrow_be_wide`=236 ✓；**C14 `add.o` base+offset** `ptr_add_offset`=171（实测 `add.o rb8, rb8, rd8`）✓；**`cmp.uo` dbb** `branch_ptr`=25（修复后实测 `73 40 00 02  br.nz {rb16}?, [rb0, 8]` → `cmp.uo`，QEMU=25）✓；**`ptr−ptr` `sub.o_orrr_dbb`** `ptr_diff_pos`=7 / `ptr_diff_neg`=249（实测 `sub.o rd31, rb16, rb17`）✓。

**修改文件**（均在白名单内；未改 `components/**`、`tests/codegen/**`、`contracts/**`、`spec/**`）：
- 新建 `tests/scripts/codegen_crt0.s`（最小启动桩 `_start`：设/沿用 SP → `call [rb0, main]` → **call 之后**构造 exit port `0xffff_8000_0000` → `st.o rd31` → `swym`）
- 新建 `tools/integ/run_codegen_e2e.py`（fail-closed 驱动：llc→cat crt0→llvm-mc→llvm-objcopy→qemu，直接比较 guest 退出码 vs `expected.yaml`；`--inject` 自检）
- 修改 `Makefile`（**仅新增** `test-codegen` 目标 + 对应 `.PHONY` 条目 + 1 行 help；前置 `build-mc`+`build-qemu`；无 `tee`）
- 证据（gitignored）：`.work/evidence/INTEG-012t/run.sh`；日志 `.work/log/integ/INTEG-012t-*.log`（`confirm-build`/`make-test-codegen`/`run_codegen_e2e`/`run_codegen_e2e-inject`/`evidence`/`inject-manual`/`pipeline-steps`/`check-lit`/`make-check`）

**验收结果**（真实命令 + 输出 + 退出码；制式 `cmd > log 2>&1; rc=$?`，**无 `tee`**）：

1. **§验收 1 — `make test-codegen` 退出 0、逐用例四字段、四类各 ≥1**：见上「测试结果」；EXIT=0，15/15。

2. **§验收 2 — 单用例链路每步真实执行**（`.work/log/integ/INTEG-012t-pipeline-steps.log`）：
```
$ .work/build/llvm/bin/llc -march=dadao tests/codegen/call_direct_ret.ll -o .../prog.s        EXIT=0
$ cat tests/scripts/codegen_crt0.s .../prog.s > .../combined.s                                 EXIT=0
$ .work/build/llvm/bin/llvm-mc --triple=dadao -filetype=obj .../combined.s -o .../combined.o   EXIT=0
$ .work/build/llvm/bin/llvm-objcopy -O binary --only-section=.text .../combined.o .../combined.bin  EXIT=0
$ timeout 30 .work/build/qemu/qemu-system-dadao -M dadao-m1 -bios tests/scripts/trampoline.bin \
      -kernel .../combined.bin -display none -nographic                                        EXIT=9 (== guest code, expected 9)
```
同日志另附上一轮被阻塞向量的复核：`branch_ptr.ll` 中 `br.nz {rb16}` 现编为 **`0x73`**（RB 变体），QEMU=**25**（=expected）。

3. **§验收 3 — 反例门控**（文件级注入，`.work/log/integ/INTEG-012t-inject-manual.log` + `-evidence.log`）：
```
注入前 sha256: e5d2494188eb5d3455581bc7bf8c116668dfab834ebdecbe756a768bbf2a6b96
$ sed -i '0,/expected_exit_code: 7$/s//expected_exit_code: 8/' tests/codegen/expected.yaml   # ptr_diff_pos 7->8
$ git diff --name-only                                   # 非空
  .tao/tasks/.../INTEG-012t-...md
  Makefile
  tests/codegen/expected.yaml
$ git diff --name-only -- tests/codegen/expected.yaml    # 确认注入命中目标文件
  tests/codegen/expected.yaml
$ python3 tools/integ/run_codegen_e2e.py                 # EXIT=1
  FAIL  ptr_diff_pos.ll  expected=8 actual=7 exit=7  (exit code mismatch)
  Results: 14/15 passed, 1 failed
$ cp <bak> tests/codegen/expected.yaml                   # 还原
还原后 sha256 == 注入前（一致）；$ git diff --name-only -- tests/codegen/expected.yaml → 空
$ python3 tools/integ/run_codegen_e2e.py                 # 还原后重跑全链路（=重建）→ EXIT=0
  PASS  ptr_diff_pos.ll  expected=7 actual=7 exit=7  (match)
  Results: 15/15 passed, 0 failed
```
证据脚本内置同构检查全 PASS（`.work/log/integ/INTEG-012t-evidence.log`）：
```
[PASS] inject-expected-value | expected: file changed
[PASS] inject-expected-value -> git diff (expected.yaml) non-empty | tests/codegen/expected.yaml
[PASS] inject-expected-value -> gate FAIL | expected_rc!=0 actual_rc=1
[PASS] inject-expected-value -> injected case reported FAIL | found 'FAIL  ptr_diff_pos.ll'
[PASS] restore-expected-value | expected: sha256 unchanged
[PASS] restore-expected-value -> gate PASS | expected_rc=0 actual_rc=0
[PASS] driver --inject self-test | expected_rc=0 actual_rc=0   # 246->247 → gate 报 FAIL
```
说明：注入对象为 `expected.yaml`（驱动运行时读取的数据，非编译输入）；按 AGENTS 成本控制无需重编译，**「重建」体现为还原后重跑完整链路**（llc/llvm-mc/llvm-objcopy/qemu 全部重执行）并回绿。

4. **§验收 4 — 不回归**：`make check-lit` → EXIT=0，`Passed: 34 (100.00%)`（任务书写「31/31」，实际 lit 套件已增长到 34，含 `LLVM-049t` 新增用例）；`make check` → EXIT=0。

5. **§验收 5 — 无残留**：`make check-no-residue` → EXIT=0；`git status --untracked-files=all --short` 仅列本任务应有改动：
```
 M Makefile
?? tests/scripts/codegen_crt0.s
?? tools/integ/run_codegen_e2e.py
```
（`.tao/tasks/.../INTEG-012t-....md` 的状态/完成区更新亦为本任务应有一并披露。）

6. **§验收 6 — 一键证据脚本**：`.work/evidence/INTEG-012t/run.sh` → **EXIT=0**（非交互；任一检查失败累加 `FAILS` 并最终 `exit 1`；逐项打印「检查名/期望/实际/rc」；内置文件级注入 + 驱动 `--inject` 两路反例自检；无 `tee`）。

**新发现/坑**：
1. **crt0 必须在 `call main` 之后构造 exit-port 地址**：`rb16` 是 caller-saved 参数寄存器（C4/C16），在 call 前构造会被 callee 的指针参数覆盖；初版在 call 前构造，导致 `ptr_diff_pos/neg`、`call_ptr_bank` 报 MALIGN `0x8C` / 错值。改到 call 后构造即全绿。
2. **既有 MC AsmParser 缺陷（上一轮阻塞，已由 `LLVM-049t` 修复）**：`DADAOAsmParser.cpp` 的「riii `br.*` with expression offset」特例曾**无条件**把 `br.z`/`br.nz` 映射到 **RD 变体**（`br_z_rd`/`br_nz_rd`，op `0x6A`/`0x6B`），忽略寄存器 bank，使 `br.nz {rb16}?, [rb0, .LBB0_2]` 被错编为 `0x6B`（读 `rd16`=0）。修复后实测编为 `0x73`（RB 变体），`branch_ptr.ll` 由 23 → **25**。历史最小复现：`.work/log/integ/INTEG-012t-blocker-branch_ptr.log`。
3. **exit 通道歧义**：`tests/codegen/expected.yaml` 的期望值 137/236/238/246/249 落在 ADR-0004 D3 保留给机器 fault 的 `0x80–0xFF`；其中 **137 == `0x89` == UNDI**，故原始 status 无法区分「guest 写 137」与「UNDI fault」。驱动因此以「精确比较期望值」为主判据、仅在**不等**时归类 fault。（自审中曾试「任何 fault 码无条件 FAIL」→ `call_narrow_args.ll` 期望 137 被误判 UNDI，实测降为 13/15，故回退。）
4. `make help` 在本任务前**已坏**：`Makefile` help 文本含奇数个反引号（```` ```simrisc ````）→ `/bin/sh: Syntax error: EOF in backquote substitution`。已用 `git show HEAD:Makefile` 复现为**既有**问题，**未触碰**（只加目标）。
5. QEMU 每次 exit-port 写入打印 `warning: Blocked re-entrant IO on MemoryRegion: dadao-exit-port` 属既有噪声（stderr），不影响退出码（ADR-0011 首次写即锁定）；驱动不解析 stderr。

**遗留问题**（如实登记；均**非本任务范围**，不修）：
1. **【非阻塞，建议另立 TESTCASES 任务】exit 通道歧义**（新发现 3）：CodeGen 向量期望值有 5 条落在 ADR-0004 D3 的机器 fault 区 `0x80–0xFF`，其中 `137 == 0x89 == UNDI` 与 fault 码**不可区分**（真实 fault 若恰为 `0x89` 会被误判 PASS）。建议把向量返回值约束到 `0x00–0x7F`（或改用 fault 段之外/寄存器级通道），恢复 ADR-0004 D3 分区无歧义。本任务不改 `tests/codegen/**`。
2. **【非阻塞】`make help` 既有语法错误**（新发现 4）：`Makefile` help 文本的奇数反引号导致 `make help` 恒失败（`git show HEAD:Makefile` 可复现为既有）；非本任务引入，未修。
3. **【已消解，登记备查】** 上一轮遗留「`branch_ptr.ll` E2E 被 MC AsmParser 缺陷阻塞」已由 **`LLVM-049t`** 修复，本轮重跑 **15/15**，转为「新发现 2」。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**（逐行）：`tests/scripts/codegen_crt0.s`、`tools/integ/run_codegen_e2e.py`、`Makefile` 的 `test-codegen` 增量、`.work/evidence/INTEG-012t/run.sh`；并独立复核全部 15 条期望值的 E2E 实际值。

**审查要点**：
- **逻辑正确性**：驱动逐步检查返回码（llc/mc/objcopy 非 0 → FAIL）、qemu 超时 → FAIL、精确比较退出码；“crt0 寄存器时序”（exit-port 地址在 call 后构造）；`_start` 位于合并 `.s` 段首（flat 入口=基址）；`swym` 停机。
- **设计/惯用法**：复用 `LLVM_BUILD`/`QEMU_BUILD` 构建目录与 `tests/scripts/trampoline.bin`；链路为单 TU 自包含、无 LLD（ADR-0003 D5）；`Makefile` 增量最小（目标+PHONY+help）。
- **防造假**：所有验证命令 `cmd > log 2>&1; rc=$?`，**无 `tee`**；证据脚本用 `cmp`+`sha256sum` 证明「确已改」与「确已还原」，`git diff -- tests/codegen/expected.yaml` 证明注入非空；日志均落 `.work/log/integ/`。
- **边界/反例**：`--inject` 与文件级注入两路均能使 gate 变红并还原；缺文件/缺工具/零用例 → exit 2。
- **越界**：仅动上述 3 个白名单文件；未改 `components/**`/`tests/codegen/**`/`contracts/**`/`spec/**`。

**findings 与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | crt0 初版在 `call main` 前构造 exit-port 地址 → 被 callee 参数覆盖（`ptr_diff_pos/neg`、`call_ptr_bank` MALIGN `0x8C` / 错值） | ✅已修 | exit-port 地址构造移到 `call` 之后 | 三用例 PASS；最终 15/15 |
| 2 | `--inject` 模式因基线含已知红而返回 1，自检无法单独表达 | ✅已修 | inject 模式以自检为判据返回 0；基线判据仅普通模式 | `--inject` → EXIT=0，日志含 `INJECT: PASS` |
| 3 | 试「任何 `0x80–0xFF` 均判 fault」→ `call_narrow_args`（期望 137==0x89 UNDI）被误判 FAIL | ❌不修（该规则在本数据集下不可行） | 回退为「精确比较为主、不等才归类 fault」；注释+完成区登记歧义 | 撤回后 15/15；`call_narrow_args` PASS；登记「新发现 3 / 遗留 1」 |
| 4 | 证据脚本 `git diff --name-only` 因本任务自身的 Makefile 改动恒非空（恒真断言） | ✅已修 | 改为 scoped `git diff --name-only -- tests/codegen/expected.yaml` | 注入后该检查 PASS（非空），还原后 expected.yaml 干净 |
| 5 | `branch_ptr.ll` E2E FAIL（expected 25, actual 23）——既有 MC AsmParser 忽略 bank | ✅已修（由 **`LLVM-049t`** 修复组件；本任务不改 `components/**`） | 未改组件；本轮确认工具最新后重跑 | `br.nz {rb16}` 实测编为 `0x73`，`branch_ptr` QEMU=25；`make test-codegen` 15/15（`.work/log/integ/INTEG-012t-pipeline-steps.log`、`-blocker-branch_ptr.log`） |
| 6 | `make help` 报 shell 语法错误 | ❌不修（既有，非本任务） | 未触碰 help 文本 | `git show HEAD:Makefile` + 临时文件复现为既有（PRISTINE_HELP_EXIT=2） |

**自审判决**：三件交付物全部落地并经真实运行；findings 1/2/4/5 已修且有复验证据（finding 5 由 `LLVM-049t` 消解）；findings 3/6 为不可行/既有项（已说明并登记遗留）。**§验收 1–5 全部达成**：`make test-codegen` **EXIT=0（15/15）**、链路每步 EXIT=0、反例注入→FAIL→还原→回绿、`make check-lit` 34/34、`check-no-residue` 干净。任务状态置 **`待验收`**，交 reviewer 独立验收。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（mimo-v2.5-pro）
**审查日期**：2026-10-05

##### 1. 证据脚本审查

**`.work/evidence/INTEG-012t/run.sh`** 审查结论：**合格**。

- **可达 FAIL 路径**：每条断言均有 `expect_zero`/`expect_nonzero` 分支，失败时 `FAILS+=1` 并打印 `[FAIL]`。非恒真断言——注入后确报 FAIL（见 §3）。
- **注入非空且可还原**：文件级注入用 `sed -i '0,/expected_exit_code: 7$/s//expected_exit_code: 8/'` 改 `expected.yaml`；`cmp -s` 验证文件已改；`cp` 还原后 `sha256sum` 验证还原。注入范围 `git diff --name-only -- tests/codegen/expected.yaml` 非空。
- **结尾不吞退出码**：`set -u`、无 `tee`、`exit 1`/`exit 0` 直接退出，`FAILS` 计数器控制。
- **驱动 `--inject` 自检**：`run_driver "$TMP/inject-selftest.log" --inject` 后 `expect_zero` 验证。

**`tools/integ/run_codegen_e2e.py`** 审查结论：**合格**。

- **精确比较 guest 退出码 vs `expected.yaml`**（非 lit）：`build_and_run()` 第 222 行 `if rc == prog["expected"]: res.passed = True`。逐用例打印四字段。
- **fail-closed**：llc/mc/objcopy 任一非零 → `res.reason = ...`、`res.passed` 保持 `False`；qemu 超时 → `timed_out`。
- **`--inject` 自检**：基线 PASS 后取首条 PASS 用例、改 expected 为 `(original+1)%256`、重跑、断言 `not inject_res.passed`；不通过时 return 1。
- **无 `tee`**：所有 `_run()` 调用 `subprocess.run`，stdout/stderr 管道直捕。

##### 2. 重跑记录

**`make test-codegen`**：
```
run_codegen_e2e: 15 programs, work dir /mnt/tao/DADAO-v5/.work/log/integ/codegen-e2e
  PASS  arith_add_sub_neg.ll  expected=246 actual=246 exit=246  (match)
  PASS  arith_const_hi_wyde.ll  expected=238 actual=238 exit=238  (match)
  PASS  mem_store_load_offset.ll  expected=77 actual=77 exit=77  (match)
  PASS  mem_narrow_be_bytes.ll  expected=41 actual=41 exit=41  (match)
  PASS  mem_narrow_be_wide.ll  expected=236 actual=236 exit=236  (match)
  PASS  branch_loop_sum.ll  expected=45 actual=45 exit=45  (match)
  PASS  branch_eq_ne.ll  expected=16 actual=16 exit=16  (match)
  PASS  branch_ptr.ll  expected=25 actual=25 exit=25  (match)
  PASS  call_direct_ret.ll  expected=9 actual=9 exit=9  (match)
  PASS  call_multiarg_stack.ll  expected=171 actual=171 exit=171  (match)
  PASS  call_narrow_args.ll  expected=137 actual=137 exit=137  (match)
  PASS  call_ptr_bank.ll  expected=42 actual=42 exit=42  (match)
  PASS  ptr_add_offset.ll  expected=171 actual=171 exit=171  (match)
  PASS  ptr_diff_pos.ll  expected=7 actual=7 exit=7  (match)
  PASS  ptr_diff_neg.ll  expected=249 actual=249 exit=249  (match)
Results: 15/15 passed, 0 failed
run_codegen_e2e: PASS
test-codegen: PASS
EXIT=0
```

**`bash .work/evidence/INTEG-012t/run.sh`**：
```
== INTEG-012t evidence ==
[PASS] files-present | expected: driver+crt0+expected+trampoline+tools | expected_rc=0 actual_rc=0
[PASS] test-codegen baseline | expected_rc=0 | expected_rc=0 actual_rc=0
[PASS] inject-expected-value | expected: file changed
[PASS] inject-expected-value -> git diff (expected.yaml) non-empty | tests/codegen/expected.yaml
[PASS] inject-expected-value -> gate FAIL | expected_rc!=0 | expected_rc!=0 actual_rc=1
[PASS] inject-expected-value -> injected case reported FAIL | found 'FAIL  ptr_diff_pos.ll'
[PASS] restore-expected-value | expected: sha256 unchanged
[PASS] restore-expected-value -> gate PASS | expected_rc=0 actual_rc=0
[PASS] driver --inject self-test | expected_rc=0 actual_rc=0
[PASS] make check-lit | expected_rc=0 actual_rc=0
[PASS] make check-no-residue | expected_rc=0 actual_rc=0
INTEG-012t evidence: PASS
EXIT=0
```

**`make check-lit`**：EXIT=0，`Passed: 34 (100.00%)`
**`make check-no-residue`**：EXIT=0

##### 3. 独立注入证据

**注入方式**：改 `call_direct_ret.ll` 的期望值 9→10（与 engineer 的 7→8 不同）。

```bash
# 注入前备份
cp tests/codegen/expected.yaml /tmp/opencode/INTEG-012t-review/expected.yaml.bak
# SHA_BEFORE = e5d2494188eb5d3455581bc7bf8c116668dfab834ebdecbe756a768bbf2a6b96

# 注入：call_direct_ret 期望值 9→10
sed -i '0,/expected_exit_code: 9$/s//expected_exit_code: 10/' tests/codegen/expected.yaml
git diff --name-only -- tests/codegen/expected.yaml
# → tests/codegen/expected.yaml  (非空 ✓)

# 运行驱动 → 期望 FAIL
python3 tools/integ/run_codegen_e2e.py
#   FAIL  call_direct_ret.ll  expected=10 actual=9 exit=9  (exit code mismatch)
#   Results: 14/15 passed, 1 failed
# EXIT=1 ✓

# 还原
cp /tmp/opencode/INTEG-012t-review/expected.yaml.bak tests/codegen/expected.yaml
# SHA_AFTER = e5d2494188eb5d3455581bc7bf8c116668dfab834ebdecbe756a768bbf2a6b96
# git diff --name-only -- tests/codegen/expected.yaml → 空 ✓

# 还原后重跑 → 期望 PASS
python3 tools/integ/run_codegen_e2e.py
#   PASS  call_direct_ret.ll  expected=9 actual=9 exit=9  (match)
#   Results: 15/15 passed, 0 failed
# EXIT=0 ✓
```

注入后 `git diff --name-only` **非空**（命中 `tests/codegen/expected.yaml`）；还原后 SHA 一致且 `git diff` 干净。**注：注入改的是 `expected.yaml`（运行时数据，非编译输入），按 AGENTS 成本控制无需重建；「重建」体现为还原后重跑完整链路（llc/mc/objcopy/qemu 全部重执行）。**

##### 4. Exit 通道歧义 / false-PASS 风险判决

**ADR-0004 D3 退出码分区**（独立从 spec 核对）：

| 范围 | 来源 | 含义 |
|------|------|------|
| `0x00` | exit port | PASS |
| `0x01`–`0x7F` | exit port | FAIL（测试自定义码） |
| `0x80`–`0xFF` | 机器 fault | Reserved（`0x87`=UNMAPPED, `0x88`=ILLI, `0x89`=UNDI, `0x8A`=RASOF, `0x8B`=RASUF, `0x8C`=MALIGN, `0x8D`=IALIGN） |

ADR-0004 D3 明确规定：「测试程序**不得**向 exit port 写入 `0x80`–`0xFF`，以保持该分区无歧义。」D5.7 进一步规定：「`$? ≥ 0x80` 视为 fault/协议外。」

**实际冲突点**：`expected.yaml` 中 5 条期望值落入 fault 区：

| 用例 | 期望值 | 十六进制 | 对应 fault 码 |
|------|--------|---------|-------------|
| `call_narrow_args.ll` | 137 | `0x89` | **UNDI** |
| `mem_narrow_be_wide.ll` | 236 | `0xEC` | Reserved |
| `arith_const_hi_wyde.ll` | 238 | `0xEE` | Reserved |
| `arith_add_sub_neg.ll` | 246 | `0xF6` | Reserved |
| `ptr_diff_neg.ll` | 249 | `0xF9` | Reserved |

**false-PASS 场景分析**：

- **最严重**：`call_narrow_args.ll` 期望 `137 == 0x89 == UNDI`。若 guest 执行到任何未定义指令（如因 crt0/call 时序错误触发 UNDI），QEMU 以 `0x89` 退出 → 驱动发现 `rc == 137 == expected` → **误判 PASS**。这是一个**真实可触发的 false-PASS**：该用例测试的是窄参数 `zext` 调用，如果后端 codegen 产生了一条 UNDI 编码的指令，测试会静默通过。
- **其余 4 条**（`0xEC`/`0xEE`/`0xF6`/`0xF9`）：对应 ADR-0004 D5.8 的 Reserved 段（`0x8E`–`0xFF`），当前 M1 QEMU 不会主动产生这些 fault 码（已定义的 fault 码最大为 `0x8D`）。理论上 false-PASS 风险**极低**（需要 QEMU 以恰好该值退出），但违反了 ADR-0004 D3「测试程序不得写 `0x80`–`0xFF`」的协议约束。

**判决：可接受为遗留（非阻塞），建议另立 TESTCASES 任务。**

理由：
1. 工程师已在完成区如实登记该歧义，并建议「把向量返回值约束到 `0x00`–`0x7F`」。
2. 驱动实现正确采用「精确比较为主」策略（`rc == expected` 优先），这是在当前数据集下唯一可行的方案——如果改为「任何 `0x80`–`0xFF` 无条件判 fault」，`call_narrow_args` 会被误判 FAIL（已实测，降为 13/15）。
3. `call_narrow_args.ll` 的 UNDI false-PASS 场景需要后端同时产生 UNDI 编码，概率较低但理论上存在。
4. 本任务范围是 CodeGen E2E 套件基础设施，**不改 `tests/codegen/**`**（向量由 TESTCASES-026t 维护）。修改期望值约束属于 TESTCASES 模块职责。

**建议后续动作**：另立 TESTCASES 任务，将 `call_narrow_args` 等 5 条用例的返回值约束到 `0x00`–`0x7F`（如修改 IR 使返回值自然落在该区间，或增加 `& 0x7F` 掩码），恢复 ADR-0004 D3 分区无歧义性。

##### 5. 覆盖点独立复核

| 覆盖点 | 用例 | reviewer 验证 |
|--------|------|--------------|
| 四类各 ≥1 | 算术：`arith_*`(2)；访存：`mem_*`(3)；分支：`branch_*`(3)；调用：`call_*`(4) | ✅ 每类 ≥1 |
| 大端窄访存 C13 | `mem_narrow_be_bytes`=41（ld.ub/ld.sb @explicit byte offsets）；`mem_narrow_be_wide`=236（ld.uw/ld.sw/ld.ut/ld.st） | ✅ 显式字节偏移，大端布局核对 |
| `add.o` base+offset C14 | `ptr_add_offset`=171（`&buf[0]+20`，volatile offset → runtime `add.o`） | ✅ |
| `cmp.uo` dbb C14 | `branch_ptr`=25（指针比较 `p==null`/`p==q` → `cmp.uo`） | ✅ |
| `ptr−ptr` `sub.o_orrr_dbb` | `ptr_diff_pos`=7 / `ptr_diff_neg`=249（两个 GPRB 指针参数相减 → `sub.o rd31, rb16, rb17`） | ✅ |
| crt0 `call [rb0, main]` | `codegen_crt0.s` 第 33 行：`call [rb0, main]` | ✅ |
| crt0 exit-port | 第 36-37 行：`set.zw rb16, wp2, 0xffff` + `or.w rb16, wp1, 0x8000` = `0xffff_8000_0000`；第 40 行：`st.o rd31, [rb16, 0]` | ✅ 构造在 call 之后（避免 callee 覆盖 rb16） |
| crt0 `swym` | 第 43 行：`swym 0` | ✅ |

##### 6. 仓库卫生

- `make check-no-residue`：EXIT=0 ✅
- `git status --untracked-files=all`：仅本任务应有改动：
  ```
   M ".tao/tasks/integ/INTEG-012t-CodeGen-E2E套件与test-codegen.md"
   M Makefile
  ?? tests/scripts/codegen_crt0.s
  ?? tools/integ/run_codegen_e2e.py
  ```
  无 `tests/codegen/` 下生成物残留 ✅（ISS-146）
- `make check-lit`：34/34 PASS，不回归 ✅
- 未改 `components/**`、`contracts/**`、`spec/**` ✅

##### 7. `make help` 语法错误

`make help` EXIT=2（`/bin/sh: Syntax error: EOF in backquote substitution`）。**与本任务无关**——`git stash` 后 `git show HEAD:Makefile` 的 pristine 版本同样 EXIT=2（奇数个反引号）。本任务只新增了一行 `@echo`，未触碰 help 文本其余部分。工程师已登记为既有问题。**登记备查，不阻塞。**

##### 8. 文件正确性分析

| 文件 | 审查结论 |
|------|---------|
| `tests/scripts/codegen_crt0.s` | 正确：`_start` 设 SP → `call [rb0, main]` → call 后构造 exit port → `st.o rd31` → `swym`。单 TU 自包含（ADR-0003 D5），无外部符号。exit port 地址 `0xffff_8000_0000` 与 ADR-0004 D3 一致。 |
| `tools/integ/run_codegen_e2e.py` | 正确：fail-closed、精确比较 guest 退出码 vs expected.yaml、逐用例四字段、`--inject` 自检、无 tee。FAULT_NAMES 字典与 ADR-0004 D5.8 一致。 |
| `Makefile` | 正确：仅新增 `test-codegen` 目标 + PHONY + help 行 + 变量定义 + 注释。前置 `build-mc`+`build-qemu`。无 tee、无管道吞退出码。 |
| `.work/evidence/INTEG-012t/run.sh` | 正确：非交互、FAILS 计数器、文件级注入 + `--inject` 两路自检、`sha256sum`/`cmp` 验证还原、结尾 `exit 1`/`exit 0`。 |

##### 判决

**Accepted**。

验收命令块全部通过（`make test-codegen` 15/15 EXIT=0、证据脚本 EXIT=0、`check-lit` 34/34、`check-no-residue` EXIT=0）。独立注入（`call_direct_ret` 9→10）确认驱动 FAIL 能力。覆盖点逐条核对。exit 通道歧义为**已知遗留风险**（137==UNDI false-PASS），已在任务书登记，建议另立 TESTCASES 任务修复——不阻塞本任务。仓库卫生干净。
