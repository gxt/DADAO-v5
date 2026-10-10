# TESTCASES-041t: 返回寄存器 `rd8` 收口——受影响向量/期望值重派生重验

**模块**：testcases
**项目里程碑**：M6
**依赖**：`SPEC-124t`（函数返回域契约）、`SPEC-126t`（系统调用/半托管返回域契约）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 用户裁定（原话）

> **「统一为 rd8」**（系统调用与函数 ABI 统一；此前 `rd31`）。**不立 ADR**（用户既定）。

## 变更边界（两个独立变更，**分别验收**）

本任务含**两个域**的向量/期望值收口，须**分段、分别验收**：

- **域 A「函数返回」**（依据 `SPEC-124t`）：函数返回寄存器 `rd31/rb31 → rd8/rb8`。
- **域 B「半托管返回」**（依据 `SPEC-126t`）：半托管服务返回寄存器 `rd31 → rd8`。**【已移出：用户 2026-10-09 裁定「域 B 并入 `QEMU-055t`」——半托管返回实现与向量耦合，须同批落地以保 `test-semihost` 绿；本任务收窄为域 A + 其余。】**

**不得**以某一域已改充另一域，**不得**以旧期望值充数。

## 接口规范

- **输入**：
  - `contract-abi.md §4.4/§4.6`（返回区 `rd8–rd15`，`SPEC-124t`）；`contract-semihosting.md §2/§4`（`SPEC-126t`）。
  - `tests/scripts/codegen_crt0.s` + `tools/integ/run_codegen_e2e.py`（注释/桩：函数返回 `rd31`）。
  - `tests/llvm/codegen/**`（`expected.yaml`/`README.md`/`*.ll` 注释中的函数返回 `rd31`/`rb31`）。
  - `tests/llvm/lit/CodeGen/DADAO/branch-fold-two-way.mir`（`RET_PSEUDO implicit $rd31`、`call_iiii` 返回 `$rd31`）。
  - `tests/llvm/codegen/m5/**`（`m5_semi_write.s`/`expected.yaml`：半托管 `SYS_WRITE` 返回 `rd31`）。
- **输出**：
  1. **域 A**：`codegen_crt0.s`（桩读取的返回寄存器 `rd31 → rd8`；`st.o` 存回位置随之）、`run_codegen_e2e.py` 注释、`tests/llvm/codegen/**`（期望/说明）与 `.mir` 中**函数返回**处 → `rd8`/`rb8`。
  2. **域 B**：`tests/llvm/codegen/m5/**` 中**半托管服务返回** `rd31 → rd8`（含「返回落 `rd8`」语义）。**【已移出：用户 2026-10-09 裁定归 `QEMU-055t`（随其收口）——本任务不再承担域 B。】**
  3. 受影响向量**重派生期望值并重验**（给真实输出与退出码）。
  4. **逐条分类表**（改 / 不改 + 理由）入完成区；计数脚本现场统计（**不写死**）。
- **约束**：
  - **只改返回用途**：**不改**参数区 `rd16–rd31`（如 `call_multiarg_stack.ll` 的参数注释）、`rd31` 作通用暂存处、寄存器角色表。
  - **期望值独立派生**：**禁**从 `llc`/QEMU 结果反填（`Process-05` / 独立 oracle）。
  - **两层分明**：域 A/域 B 的验收证据须**分开列出**（分别给真实输出）。
  - **不改 `spec/`**（`git diff --name-only | grep -E '^spec/'` 无输出）；**不改** `components/**`。
  - `.mir`/codegen 用例若因 `LLVM-062t` 未就绪而**暂不可跑**，须按 `Process-05` 用 `UNSUPPORTED:` 暂缓并**登记遗留**（不得以暂缓掩盖缺口），完成区披露。
  - **门控保持全绿**，不回归。

## 硬约束

- **临时目录** `/tmp/opencode/TESTCASES-041t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/TESTCASES-041t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/testcases/TESTCASES-041t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **域 A（函数返回）**：`codegen_crt0.s`/`run_codegen_e2e.py`/`tests/llvm/codegen/**`/`.mir` 中函数返回处 == `rd8`（给 grep/摘录真实输出）；参数区 `rd16–rd31` **逐条未变**。
2. **域 B（半托管返回）**：`tests/llvm/codegen/m5/**` 中服务返回处 == `rd8`（给真实输出）。**【已移出：用户 2026-10-09 裁定归 `QEMU-055t`（随其收口）——本任务不再验收域 B。】**
3. **重派生重验**：受影响向量**重跑通过**（或按 `Process-05` `UNSUPPORTED:` 暂缓并登记遗留），给真实输出与退出码；**无旧期望值残留**充数。
4. **逐条分类表**：完成区给「改 / 不改」逐条分类（`文件:行 + 用途 + 理由`），计数脚本现场统计。
5. **不回归**：`make check`/`check-lit` EXIT=0（通过数与改前**逐项相等 / 不下降**）。
6. **一键证据脚本**：`.work/evidence/TESTCASES-041t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检，给真实输出与退出码。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：改前/改后 `make check` EXIT=0（lit 77 passed / 1 unsupported，逐项相等）；`test-codegen` 15/15 rc=0；`test-elf` 5/5 rc=0；`test-semihost` 10/10 + 25-service rc=0；`check-qemu-semantics` 149/149 rc=0；证据脚本 `run.sh` RUN_EXIT=0。日志 `.work/log/testcases/TESTCASES-041t-*.log`。

**逐条分类表**（`文件:行` + 用途 + 改/不改+理由）：

| 文件:行 | 用途 | 判决 |
|---|---|---|
| tests/scripts/codegen_crt0.s:55 | 桩 `st.o` 存回函数返回（`st.o rd8,[rb16,8]`） | 不改（实测已 rd8，LLVM-062t 落地） |
| tests/llvm/lit/CodeGen/DADAO/branch-fold-two-way.mir:123,139,145 | call_iiii 返回 / RET_PSEUDO | 不改（实测已 `$rd8`，LLVM-062t） |
| tools/integ/run_codegen_e2e.py:17 | 注释「返回 rd31」 | 改→rd8 |
| tests/llvm/codegen/expected.yaml:6 | 注释 crt0 读回值 | 改→rd8 |
| tests/llvm/codegen/expected.yaml:147 | `pointer return, rb31` | 改→rb8 |
| tests/llvm/codegen/expected.yaml:126 | 参数区 `rd16..rd31` | 不改（参数区） |
| tests/llvm/codegen/README.md:12 | crt0 读回值 | 改→rd8 |
| tests/llvm/codegen/README.md:45 | `integer return in rd31` | 改→rd8 |
| tests/llvm/codegen/README.md:48 | `pointer return (rb31)` | 改→rb8 |
| tests/llvm/codegen/call_direct_ret.ll:3 | 注释返回寄存器 | 改→rd8 |
| tests/llvm/codegen/call_multiarg_stack.ll:2 | 参数区 `rd16..rd31` | 不改（参数区） |
| tests/llvm/codegen/call_ptr_bank.ll:2 | `returns a pointer (rb31)` | 改→rb8 |
| tests/llvm/codegen/call_ptr_bank.ll:3 | `returns an integer (rd31)` | 改→rd8 |
| tests/llvm/codegen/m5/m5_semi_write.s:11 | `rd31 ... not return`（暂存声明） | 不改（暂存；域B归 QEMU-055t） |
| tests/llvm/lit/CodeGen/DADAO/fp-codegen.ll:5 | 参数区 `rf16..rf31` | 不改（参数区） |

**计数（现场统计，不写死）**：checker 分区 `total=4 return=0 keep_param=3 keep_scratch=1`；改动**处数 N** 与涉及**文件数 M** 均由命令现场得出——`git diff -U0 -- tests/ tools/` 的删/增行数（`grep '^-'|grep -vc '^---'` / `grep '^+'|grep -vc '^+++'`）与分类表标「改」行数**逐项相等**（三者同值 N），M 由 `git diff --name-only -- tests/ tools/` 现场统计。

**修改文件**：`tools/integ/run_codegen_e2e.py`、`tests/llvm/codegen/{expected.yaml,README.md,call_direct_ret.ll,call_ptr_bank.ll}`。
**验收结果**：域A 返回处全为 rd8/rb8；`spec/contracts/components` 交集空（`git diff --name-only|grep -E '^(spec|contracts|components)/'` rc=1）；独立 oracle `validate_codegen_vectors.py`（host IR 模型，**不调 llc/QEMU**）rc=0；期望值语义与返回寄存器名无关 ⇒ 未改任何 `expected_exit_code`（**禁反填**）。域B（半托管返回）归 `QEMU-055t`，本任务不验收；`m5/m5_semi_write.s`/`m5/expected.yaml` 实测已 rd8，未动。
**新发现/坑**：任务书所述基线（crt0 读 `rd31`、`.mir` `$rd31`）与 HEAD 不符——二者已由 `LLVM-062t`(d367bf6) 改为 `rd8`（代码侧），本任务实为**文档/注释旧口径收口**。`AGENTS.md`/`.tao/README.md` 由主会话并发修改（非本任务改动）。
**遗留问题**：无（**无 UNSUPPORTED**：`LLVM-062t` 已就绪，`.mir` lit 用例随 `check-lit` 实跑）。**返工处置**（reviewer 第 1 轮 Needs Revision 的 D1/D2，均文档级）：**D1** 完成区「改 8 处」既不符现场统计又违反「计数不写死」⇒ ✅已修，改为现场统计（处数/文件数由 `git diff` 现得，删/增/表「改」行逐项相等）；**D2** 分类表 `codegen_crt0.s:64` 行号不存在（文件仅 62 行）⇒ ✅已修，`grep -n` 实测改为 `:55`（`st.o rd8,[rb16,8]`）。


## 审阅记录

#### 第 1 轮 engineer 自审
**范围**：逐行审查 5 个改动文件（仅注释/文档字串：8 处）与证据脚本。改动**不含可执行语义**（`.ll`/`.yaml`/`.md`/`.py` 注释），无寄存器/编码/期望值变更。
**逻辑正确性**：`rd31/rb31` 仅出现在「返回用途」处被改；参数区（`rd16..rd31`/`rf16..rf31`）与暂存声明未动。checker part1 分区统计确认 `return=0`。
**防造假**：证据脚本三条注入（A 返回处注入 rd31→§8.34 正则命中；B `.mir` RET_PSEUDO `$rd8→$rd9`→§8.35 结构；C 误改 in-scope 文件→文件集结构），均实测 FAIL 且 `cp`+md5 还原后回绿；`RUN_EXIT=0`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 任务书基线（crt0 读 rd31、.mir `$rd31`）与 HEAD 不符 | ❌不修（非缺陷） | 无 | `git show d367bf6` 显示 LLVM-062t 已改 rd8；checker `p3-crt0-st.o-rd8 count=1`、`p3-mir-ret-all-rd8=['$rd8']` |
| F2 checker crt0 明细用另一正则，打印 `count=0` 与断言不一致（§8.34 隐患） | ✅已修 | 明细与条件同一正则 | 重跑：`p3-crt0-st.o-rd8: count=1` |
| F3 run.sh check[7] 用整集相等，对主会话并发改 `AGENTS.md`/`.tao/README.md` 脆弱，且无 FAIL 路径演示 | ✅已修 | 改为「所需文件齐 + tests/`tools/` 无越界」；加注入 C | 注入 C：`injectC-expect-fail rc=1` → 还原 md5 相等 → `restoreC-green rc=0`；`final-file-set rc=0` |
| F4 run.sh `"$PY" "$CHECK" | tail` 后 `rc=$?` 会取 tail 的 rc（§8.23） | ✅已修 | 顶部 `set -o pipefail` | 基线行 `baseline-checker expected rc=0 actual rc=0` |
| F5 未单列 `make check-lit` rc | ❌不修 | 无 | `check-lit` 是 `make check` prerequisite；`make check` EXIT=0 内含 lit 77/1 |
| F6 域B（半托管返回）文件是否需动 | ❌不修（范围外） | 无 | `m5_semi_write.s`/`m5/expected.yaml` 实测已 rd8（QEMU-055t），本任务未动 |

**判决**：全部 finding 已处置（✅2 / ❌4，无未修阻塞项）⇒ 状态置 `待验收`。


#### 第 1 轮 reviewer 验收
**重跑记录**（全部 reviewer 亲跑，`/tmp/opencode/TESTCASES-041t-review/`）：
- 改动面 `git diff --name-only` rc=0 ⇒ 恰 5 代码文件 + 本任务书；`git diff -U0 -- tests/ tools/ | grep '^-'|grep -vc '^---'` = **9**、`'^+'` = **9**（现场计数）。
- `make test-codegen` RC=0 `Results: 15/15 passed`；`make test-elf` RC=0 `5/5`；`make test-semihost` RC=0 `10/10`+`service coverage: all 25 service ids exercised`；`make check-qemu-semantics` RC=0 `149 total, 149 passed`；`make check` RC=0 `Total Discovered 78 / Passed 77 / Unsupported 1`（与改前 `.work/log/.../make-check-pre.log` 逐项相等）。
- 证据脚本重跑 `bash .work/evidence/TESTCASES-041t/run.sh` ⇒ `RUN_EXIT=0`（25 PASS/0 FAIL；injectA/B/C 均 `expected rc=1 actual rc=1`，`*-restored-md5` 相等，`final-file-set`/`no-residue` rc=0）。
- **reviewer 独立注入 2 条**（与 engineer 三条不同文件/不同手法）：① `call_direct_ret.ll:3` 返回注释 `rd8→rd31` ⇒ run.sh `RUN_EXIT=1`，`failing: p1-no-return-rd31 / p2-present 'Return value travels in rd8' / p2-absent 'rd31'`；② `README.md:48` `pointer return (\`rb8\`)→rb31` ⇒ `RUN_EXIT=1`，`failing: p1-no-return-rd31 / p2-present / p2-absent`。均 `cp` 备份还原，md5 回到注入前（`f976d674…`/`c1fa73ba…`，`MD5_MATCH=YES`）后再跑 ⇒ `RUN_EXIT=0`。
- 快照对账：注入前后 `git status --porcelain -uall` 同 6 文件；5 代码文件 md5 与注入前逐项相等（未改动工程师产物）。

**约束核验**：① 只改返回用途 ✅——diff 逐行均为返回寄存器注释/文档（README 12/45/48、call_direct_ret.ll:3、call_ptr_bank.ll:2-3、expected.yaml 6/147、run_codegen_e2e.py:17）；4 处「不改」独立核实未动：`expected.yaml:126` 与 `call_multiarg_stack.ll:2` `rd16..rd31`、`fp-codegen.ll:5` `rf16..rf31`、`m5_semi_write.s:11` `rd31 ... scratch`，且全库 `grep -rn 'rd31|rb31'` 残留恰此 3 处 + `rf31` 1 处；② 期望值未改正当 ✅——`expected.yaml` diff 仅注释/derivation 文本，无 `expected_exit_code` 行；返回寄存器名与退出码值无关，且 `test-codegen` 15/15 用原期望值通过、`validate_codegen_vectors.py`（host IR oracle，不调 llc/QEMU）rc=0；③ 不回归 ✅（上列计数逐项相等）；④ `git diff --name-only | grep -E '^(spec|contracts|components)/'` rc=1（空）、`origin/master...HEAD` 0 文件、无 `_tmp/_orig/_rej` ✅。

**第 2 条核实（engineer 关键声明独立证伪）**：`tests/scripts/codegen_crt0.s` 实测 `13: value arrives in rd8`、`43: the result returns in rd8`、`55: st.o rd8, [rb16, 8]`（全文件无 `rd31`）；`branch-fold-two-way.mir` 实测 `123: call_iiii ... implicit-def $rd8`、`139/145: RET_PSEUDO implicit $rd8`（无 `$rd31`）⇒ **声明属实**（LLVM-062t 已落代码侧，本任务退化为文档/注释收口）；完成区「新发现/坑」如实记录了「任务书基线与 HEAD 不符」，与事实一致 ✅。

**问题（2 项，均文档级、不涉语义）**：
- **D1 计数不符 + 硬编码**：完成区「改 8 处（5 文件）」——现场统计 `git diff -U0` 删/增各 **9** 行，且分类表自身列 **9** 行标「改」；硬编码计数亦违反硬约束「计数不写死」。应改为脚本现场统计（如 `git diff --numstat`）或「9 处（5 文件）」并与表逐条对齐。
- **D2 行号失效**：分类表 `tests/scripts/codegen_crt0.s:64`——该文件仅 62 行，`:64` 不存在；实际返回读回在 `:55`（`st.o rd8,[rb16,8]`，注释 `:13/:43`）。须更正行号。

**判决：Needs Revision**（仅 D1/D2 两处文档准确性问题；命令块/约束/证据脚本/反例注入/边界全部通过，返工只需改任务书完成区两处文字，勿动代码产物）。

#### 第 2 轮 reviewer 验收（轻量）

**重跑记录**（`/tmp/opencode/TESTCASES-041t-review2/`）：

1. **D1 独立重算**：`git diff -U0 -- tests/ tools/` 删=`9`、增=`9`；`git diff --numstat` 合计=`3+1+2+2+1=9`；分类表标「改」=`9` 行（py:17, yaml:6,147, md:12,45,48, ll:3, ll:2, ll:3）。三者同值 9，与完成区「处数 N…删/增/表逐项相等」表述一致。完成区无残留硬编码数字（`grep -P '\b[0-9]\b 处' .tao/tasks/.../TESTCASES-041t*.md` 仅匹配分类表行号，非计数）。✅
2. **D2 独立核**：`grep -n 'st\.o.*rd8' tests/scripts/codegen_crt0.s` → `55: st.o rd8, [rb16, 8]`；`wc -l` = `62` 行；完成区 `:55` 正确，`:64` 已不存在。✅
3. **产物未被返工触碰**：`git diff --stat -- tools/integ/run_codegen_e2e.py tests/llvm/codegen/{expected.yaml,README.md,call_direct_ret.ll,call_ptr_bank.ll}` → `5 files changed, 9 insertions(+), 9 deletions(-)`，与第 1 轮审阅记录一致。✅
4. **重跑**：`bash .work/evidence/TESTCASES-041t/run.sh` ⇒ `RUN_EXIT=0`（25 PASS/0 FAIL；inject A/B/C 均 expected=1 actual=1，md5 还原后回绿）。`make check` ⇒ `MAKE_CHECK_RC=0`（Total Discovered 78 / Passed 77 / Unsupported 1），逐项与改前相等。✅
5. **边界**：`git status --porcelain -uall` 仅 6 文件（任务书 + 5 代码产物）；无 `_tmp/_orig/_rej`；`git diff --name-only | grep -E '^(spec|contracts|components)/'` 无输出。✅

**判决：Accepted** — D1 计数改为现场统计、D2 行号更正为 `:55`，均与独立重算一致；产物未动；证据脚本/门控/注入/边界全部通过。
