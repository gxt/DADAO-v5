# INFRA-041t: M3 收官前 issue 清扫（关闭已修 + 顺带小修 + 边界重定）

**模块**：infra
**项目里程碑**：M3
**依赖**：`LLVM-033t`~`LLVM-049t`、`SPEC-097t`/`099t`/`100t`/`101t`/`102t`、`TESTCASES-026t`、`INTEG-012t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`.tao/knowledge/issues.yaml`（48 open）；M3 执行链全部已完成并验证。
- **输出**：一次**查缺补漏**——（A）关闭「已修未关」；（B）顺带修小问题并关闭；（C）把 M3 已交付/顺延项**边界重定**；（D）其余保持 open。全部改动落 `issues.yaml` + 各小修目标文件。
- **范围与事项（用户 2026-10-05 确认）**：

### A. 已修未关（核实 → `closed` + `resolved_by`）
- **`ISS-040`**：`DADAOFrameLowering` 未覆写 `hasFPImpl` → **已由 `LLVM-038t` 实现**（`DADAOFrameLowering.cpp:63`）。
- **`ISS-130`**：新增指令 `sub rd, rb, rb`（ptr−ptr）→ **已由 `SPEC-100t`/`QEMU-040t`/`LLVM-043t` 落地**（`DADAOInstrInfo.td` `sub_o_dbb` + `opcodes.yaml` `sub.o_orrr_dbb`）。

### B. 顺带小修（修 + 验证 + 关闭）
- **`ISS-135`**：`Makefile` help 文本奇数反引号致 dash `EOF in backquote substitution`（`make help` 非零退出）→ 修至 `make help` EXIT=0。
- **`ISS-136`**：计数残留——`contracts/legality_rules.yaml:18`（`227`→`228`）、`tools/spec/check_scope.py:15`（`227`→`228`）、`tools/spec/gen_legality_list.py:7`（`190`→`191`）。目标值以 `grep -c '^- id:' contracts/opcodes.yaml`（=228）与 `rule_refs` 实测为准。
- **`ISS-140`**：`README.md` 中 LLVM 补丁数陈旧 → 刷新到实际补丁数。
- **`ISS-144`**：`components/llvm-project/changelog.md` 缺 `LLVM-040t`/`LLVM-041t` 两行 → 补录（措辞从对应任务书/提交摘）。
- **`ISS-145`**：`.work/evidence/LLVM-043t/run.sh`、`.work/evidence/LLVM-045t/run.sh` 硬编码 MC 计数陈旧 → 改为**非硬编码**（模式/下限）断言；重跑回绿。
- **`ISS-134`**：`tools/llvm/gen_m1_asm.py`/`test_m1_asm.py` 用旧 `i` 后缀语法（实测 148/152）→ 更新至新语法；`test_m1_asm.py` 全绿。

### C. 边界重定（M3→M4；**不修实现**，更新 `notes` 标注剩余部分归 M4）
- `ISS-005`（完整调用约定：变参/聚合/多返回/sret）、`ISS-006`（ABI 其余 `[OPEN]`）、`ISS-008`（完整 ELF 重定位）、`ISS-019`（FP golden）、`ISS-026`（imm 语义 oracle）、`ISS-074`（`cs.*` 条件赋值）、`ISS-081`（FP 后续）、`ISS-110`（MC cfx 别名）。
- 每条 `notes` 补：「M3 已交付部分 = …；剩余归 M4」。

### D. 保持 open（不动）
其余（`ISS-003`/`038`/`039`/`043`/`044`/`045`/`047`/`050`/`054`/`058`/`064`/`078`/`087`/`088`/`090`/`093`/`098`/`102`/`108`/`117`/`118`/`120`/`125`/`126`/`138`/`139`/`142`/`146`/`147` 等）。

- **约束**：
  - 只做上述 A–D；**不**顺手扩范围。小修须**最小外科**（不改无关代码）。
  - `contracts/`/`tools/`/`Makefile` 属门控覆盖 ⇒ `make check` 必须过。
  - `README.md`/`components/llvm-project/changelog.md`/`.work/**` 非门控。
  - 生成物勿落仓库测试目录（`ISS-146`）。
  - 不改 `spec/SimRISC-0x` 正文、不改 `opcodes.yaml` 编码值。

## 验收标准

1. `issues.yaml` 合法（`yaml.safe_load` EXIT=0）；`ISS-040`/`130`/`134`/`135`/`136`/`140`/`144`/`145` 均 `closed` 且 `resolved_by` 明确；`ISS-005/006/008/019/026/074/081/110` `notes` 含 M3/M4 边界。
2. 各小修**逐条真实验证**：
   - `make help` EXIT=0；计数 == 实测（228 / 191）；`README.md` 补丁数 == 实际；组件 changelog 含 040t/041t 两行；`043t`/`045t` 证据脚本重跑回绿；`tools/llvm/test_m1_asm.py` 全绿。
3. `make check` EXIT=0；`make check-issues`（若存在）EXIT=0。
4. **反例门控**：对可机械检查项（计数、`make help`、组件 changelog 行）给「注入→FAIL→还原→回绿」真实输出。
5. 无仓库残留；一键证据 `.work/evidence/INFRA-041t/run.sh`（规格同 `LLVM-033t`）。

## 完成区

**测试结果**：全部通过。
- 一键证据 `.work/evidence/INFRA-041t/run.sh`：**9/9 PASS，EXIT=0**（日志 `.work/log/infra/INFRA-041t-evidence.log`）。
- 反例自检 `run.sh --inject`：**6/6 注入→FAIL→还原→回绿，EXIT=0**（日志 `.work/log/infra/INFRA-041t-evidence-inject.log`）。
- `make check`：**EXIT=0**，`repository checks: PASS`，lit **34/34**（日志 `.work/log/infra/INFRA-041t-make-check.log`）。
- `tools/llvm/test_m1_asm.py`：**152 passed, 0 failed（152/152）**。
- `LLVM-043t` 证据脚本：**11/11 PASS**；`LLVM-045t` 证据脚本：**19/19 PASS**（重跑回绿）。
- `issues.yaml`：`yaml.safe_load` EXIT=0；92 条。

**修改文件**（仓库内，git 可追踪；均未提交）：
- `.tao/knowledge/issues.yaml`：A/B 共 8 条 `status: open→closed` + `resolved_by`；C 共 8 条 `notes` 补 M3/M4 边界；余项不动。
- `Makefile`：help 行内三反引号加反斜杠转义（ISS-135）。
- `contracts/legality_rules.yaml`：L18 `227→228`（ISS-136）；L19 分解注记同步补 `+ 1 条 scope: m3`（见「遗留问题」说明）。
- `tools/spec/check_scope.py`：L15 docstring `152/60/15/227→228`（ISS-136）。
- `tools/spec/gen_legality_list.py`：L7 `190→191 with rule_refs`（ISS-136）。
- `components/llvm-project/README.md`：补丁规模 `45→48`（新增 44 + 修改 4）（ISS-140）。
- `components/llvm-project/changelog.md`：补录 `LLVM-040t`（AsmPrinter）与 `LLVM-041t`（最小重定位）两行（ISS-144）。
- `tools/llvm/gen_m1_asm.py`：旧 `i` 后缀语法 → LLVM-026t 新语法字节偏移（`2i→8`、`4i→16`、`24i→96`）（ISS-134）。

未入库（`.work/**`，gitignored）：
- `.work/evidence/LLVM-043t/run.sh`、`.work/evidence/LLVM-045t/run.sh`：lit-mc / lit-bytes / oracle 断言改为「解析计数 + 下限」（ISS-145）。
- `.work/evidence/INFRA-041t/run.sh`（本任务一键证据，含 `--inject`）；日志 `.work/log/infra/INFRA-041t-*.log`。

**验收结果**（真实命令 + 输出 + 退出码；完整输出见上述日志）：

1) A/B/C/D 机械核验（`run.sh` 逐项，见 `.work/log/infra/INFRA-041t-evidence.log`）：
```
[PASS] issues-yaml | actual: ok: 8 closed+resolved_by; 8 open with M3/M4 notes | rc=0
[PASS] make-help | actual: rc=0, 43 lines | rc=0
[PASS] counts | actual: op=228 rr=191, docs=consistent | rc=0
[PASS] readme-patch-count | actual: total=48 new=44 mod=4 | rc=0
[PASS] changelog-rows | actual: match=yes | rc=0
[PASS] m1-asm | actual: Results: 152 passed, 0 failed | rc=0
[PASS] evidence-043t | actual: RESULT: PASS (11 checks, 0 failures) | rc=0
[PASS] evidence-045t | actual: RESULT: PASS (19 checks, 0 failures) | rc=0
[PASS] make-check | actual: rc=0, repository checks: PASS | rc=0
RESULT: PASS (9 checks, 0 failures)
EXIT=0
```

2) 反例门控（`run.sh --inject` 6 例，见 `.work/log/infra/INFRA-041t-evidence-inject.log`）：
```
inject[make-help]:    [FAIL] make-help rc=2 -> 还原 [PASS] rc=0           ; PASS
inject[counts-doc]:   [FAIL] counts docs=inconsistent -> 还原 [PASS]     ; PASS
inject[changelog]:    [FAIL] changelog-rows match=no -> 还原 [PASS]      ; PASS
inject[readme-count]: [FAIL] readme-patch-count README stale -> 还原 [PASS]; PASS
inject[issues-closed]: [FAIL] AssertionError ('ISS-130','open') -> [PASS] ; PASS
inject[m1-asm]:       [FAIL] Results: 150 passed, 2 failed -> 还原 [PASS]; PASS
INJECT RESULT: PASS (6/6 injections FAIL then green)
EXIT=0
```

3) `make check`（`.work/log/infra/INFRA-041t-make-check.log`）：
```
$ make check > log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
Total Discovered Tests: 34
  Passed: 34 (100.00%)
check_issues: 40 open, 52 closed (0 blocking M1-gate: 0)
repository checks: PASS
```

4) A 项独立核实：
```
$ grep -n 'hasFPImpl' .../DADAOFrameLowering.cpp.patch       # L69: +bool DADAOFrameLowering::hasFPImpl
$ grep -n 'sub.o_orrr_dbb' contracts/opcodes.yaml            # L3077
$ grep -n 'sub_o_dbb' .../DADAOInstrInfo.td.patch            # L816: +def sub_o_dbb
$ grep -H '^\*\*状态\*\*' LLVM-038t/043t、SPEC-100t、QEMU-040t  # 均「已验证」
```

5) 仓库无残留：`git status --untracked-files=all` 仅 8 个应改文件 + 本任务书；`make check-no-residue` EXIT=0；`.work/source/llvm-project` `git status --porcelain` 空。

**新发现/坑**：
- `tools/llvm/gen_m1_asm.py`/`test_m1_asm.py` 的 docstring 仍写「177 M1」（实为 152）——陈旧计数，**不在 ISS-134 范围**，未改（建议另立小任务或登记）。
- `ISS-140` 的 `README.md` 实指 `components/llvm-project/README.md`（唯一含 LLVM 补丁数的 README；仓库根 `README.md` 无该计数；`LLVM-040t` 完成区亦点名此文件）。
- `legality_rules.yaml` L18 改 228 后，L19 分解行（152+60+15=227）不再自洽 → 同步补 `+ 1 条 scope: m3`（否则文档自相矛盾）。
- `issues.yaml` 的 `scope` 枚举不含 `M4`，故 C 项「边界重定」只能改 `notes`、不能改 `scope`（改 scope 会越界枚举）；`check_issues.py` 不校验 scope/resolved_by，机械门控由本任务一键脚本承担。
- 证据脚本（043t/045t）原硬编码计数（lit-bytes 114、lit-mc 27/28、oracle 122）已全部陈旧（现 118/30/126）；改「解析计数 + 下限」后不再随用例增长产生假回归。

**遗留问题**：
- ISS-134 附属的 docstring `177` 未改（超任务所列范围）→ 已在「新发现/坑」登记，交主会话决定是否另立 issue。
- `legality_rules.yaml` L19 一行越出任务书字面所指（L18）的一行改动，属为消除「228 vs 152+60+15=227」自相矛盾的**必要**同步；已如实披露。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：`issues.yaml`（A/B/C/D）、`Makefile`、`contracts/legality_rules.yaml`、`tools/spec/check_scope.py`、`tools/spec/gen_legality_list.py`、`components/llvm-project/{README.md,changelog.md}`、`tools/llvm/gen_m1_asm.py`、`.work/evidence/{LLVM-043t,LLVM-045t,INFRA-041t}/run.sh`。

**审查要点（逐行）**：
- **逻辑正确性**：
  - `issues.yaml` A/B 8 条 `closed` 且 `resolved_by` 非空，C 8 条 `open` 且 notes 含 M3/M4；D 未动（diff 仅 16 条）。`yaml.safe_load` EXIT=0。
  - `Makefile`：三反引号加 `\`` 后 `make help` EXIT=0 且文本仍打印 ` ```simrisc `；未破坏其它 recipe。
  - 计数：`opcodes=228`、非空 `rule_refs=191`（228−37）；三处 doc 均嵌入实测值。
  - `gen_m1_asm.py`：`Ni`=N×4 字节（对齐 LLVM-026t `1i→4`、`4i→16` 的 lit 迁移）→ `2i→8`、`4i→16`、`24i→96`；`test_m1_asm.py` 152/152，无残留 `i]`。
  - 证据脚本：lit-mc/lit-bytes/oracle 改「`sed` 解析计数 + 下限」；无可达 FAIL 恒真断言（计数缺失 → `-n` 守卫判 FAIL；rc≠0 判 FAIL；低于下限判 FAIL）。
- **设计/惯用法**：证据脚本沿用 043t/045t 的 `record()`/`run_all()`/`--inject` 结构；`inject_run` 统一「备份→改→sha 断言非空→期望 FAIL→还原→sha 断言一致→回绿」；无 `tee`，结尾 `echo "EXIT=$rc"; exit "$rc"`。
- **防造假**：所有命令 `cmd > log 2>&1; rc=$?`；注入均验证 `sha256` 变化（非空注入）与还原一致；完成区结论逐条对齐真实输出。
- **门控可达性**：`--inject` 6 例各自使目标检查 FAIL（见 §2 输出），非恒真。
- **约束**：临时目录 `/tmp/opencode/INFRA-041t/`；未提交 git；只改所列项（含 1 处必要披露）；未改 `spec/SimRISC-0x` 正文、未改 `opcodes.yaml` 编码值。

**findings 与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `legality_rules.yaml` L18 改 228 后 L19 分解行不自洽（152+60+15=227） | ✅已修（必要） | L19 补 `+ 1 条 scope: m3` | `make check` EXIT=0；`counts` PASS |
| 2 | ISS-140 的 `README.md` 指代二义 | ⏸说明（不修） | 无（改 `components/llvm-project/README.md`，唯一含补丁数者） | `readme-patch-count` PASS：total=48 new=44 mod=4 |
| 3 | `gen_m1_asm.py`/`test_m1_asm.py` docstring `177` 陈旧（实 152） | ⏸延后 | 无（超任务所列范围） | 已登记「新发现/坑」 |
| 4 | 043t/045t 证据脚本硬编码计数陈旧致假回归 | ✅已修 | 改「解析计数 + 下限」 | 043t 11/11、045t 19/19，EXIT=0 |
| 5 | 组件 changelog `LLVM-040t` 行「series 48（2 新增+5 修改）」易误读 | ✅已修 | 拆分表述为「本任务 7 文件 = 2 新增 + 5 修改；series 48 项」 | `changelog-rows` PASS |

**自审判决**：无未修 finding（#2/#3 为有依据的说明/延后）。9/9 证据 + 6/6 注入全绿，`make check` EXIT=0，仓库无残留。任务状态置 **待验收**。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（mimo-v2.5-pro）
**审查时间**：2026-10-05

---

##### 一、证据脚本审核

`.work/evidence/INFRA-041t/run.sh` 逐行审核：
- `record()` 函数：`rc` 非零即 FAIL（`$?` 捕获），FAIL 路径可达 ✓
- 9 项 `check_*` 函数：每项基于真实命令退出码/解析值判定，非恒真 ✓
- `inject_run()` 函数：sha256 前后比对 → 修改 → 期望 FAIL → 还原 → sha256 一致 → 回绿；无 `tee` 吞退出码；结尾 `echo "EXIT=$rc"; exit "$rc"` ✓
- 6 个注入各自靶向不同文件/检查函数，非空且可还原 ✓
- **结论：脚本合格，不需修改。**

---

##### 二、独立重跑

```
$ cd /mnt/tao/DADAO-v5 && bash .work/evidence/INFRA-041t/run.sh > /tmp/opencode/INFRA-041t-review/evidence.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0

[PASS] issues-yaml | expected: yaml.safe_load ok; A/B closed; C open+M3/M4 | actual: ok: 8 closed+resolved_by; 8 open with M3/M4 notes | rc=0
[PASS] make-help | expected: make help rc=0 and lists check-spec-codeblocks | actual: rc=0, 43 lines | rc=0
[PASS] counts | expected: opcodes==228, rule_refs==191, doc spots embed them | actual: op=228 rr=191, docs=consistent | rc=0
[PASS] readme-patch-count | expected: README count == actual | actual: total=48 new=44 mod=4 | rc=0
[PASS] changelog-rows | expected: changelog has LLVM-040t and LLVM-041t rows | actual: match=yes | rc=0
[PASS] m1-asm | expected: rc=0, 0 failed, >=152 passed | actual: Results: 152 passed, 0 failed | rc=0
[PASS] evidence-043t | expected: 043t evidence script rc=0 | actual: RESULT: PASS (11 checks, 0 failures) | rc=0
[PASS] evidence-045t | expected: 045t evidence script rc=0 | actual: RESULT: PASS (19 checks, 0 failures) | rc=0
[PASS] make-check | expected: make check rc=0 | actual: rc=0, repository checks: PASS | rc=0
RESULT: PASS (9 checks, 0 failures)
EXIT=0
```

工程师 `--inject` 重跑：
```
$ bash .work/evidence/INFRA-041t/run.sh --inject > /tmp/opencode/INFRA-041t-review/inject.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0

inject[make-help]:    [FAIL] rc=2 → 还原 [PASS] rc=0           ; PASS
inject[counts-doc]:   [FAIL] docs=inconsistent → 还原 [PASS]    ; PASS
inject[changelog]:    [FAIL] match=no → 还原 [PASS]             ; PASS
inject[readme-count]: [FAIL] README stale → 还原 [PASS]         ; PASS
inject[issues-closed]:[FAIL] AssertionError ('ISS-130','open') → 还原 [PASS]; PASS
inject[m1-asm]:       [FAIL] 150 passed, 2 failed → 还原 [PASS] ; PASS
INJECT RESULT: PASS (6/6 injections FAIL then green)
EXIT=0
```

---

##### 三、独立注入（与工程师 6 项不同）

**靶点**：ISS-005 notes 中删除所有 `M4` 字眼（靶向 `check_issues` 中 C 项断言 `assert 'M3' in n and 'M4' in n`）。

```
# 注入前 sha
before=ed0389117557521ba7bb21ea5a8a2ecdcdf189a7b9a92571008a26a1611d1a66

# 注入：python3 -c "remove all 'M4' from ISS-005 block"
after=adb95178b266b2af592e813a226ccec81d3777b3ae659619552a10541685e9d0
INJECT: CHANGED OK

# 检查断言 FAIL
ASSERT FAIL: ISS-005 notes lack M3/M4
CHECK_EXIT=1

# 还原
restored sha=ed0389117557521ba7bb21ea5a8a2ecdcdf189a7b9a92571008a26a1611d1a66
RESTORE GREEN: all C items have M3/M4 boundary
EXIT=0
```

**结论**：注入→FAIL→还原→回绿，sha256 前后一致。独立证伪通过。

---

##### 四、A–D 独立复核

**A. 已修未关**
- `ISS-040`：`status=closed, resolved_by=LLVM-038t`。核验：`grep -n 'hasFPImpl'` 在 LLVM-038t 的 DADAOFrameLowering.cpp.patch L69 确有 `+bool DADAOFrameLowering::hasFPImpl`。关闭**有据** ✓
- `ISS-130`：`status=closed, resolved_by=SPEC-100t/QEMU-040t/LLVM-043t`。核验：`contracts/opcodes.yaml` L3077 有 `sub.o_orrr_dbb`；LLVM-043t 的 DADAOInstrInfo.td.patch L816 有 `+def sub_o_dbb`；对应任务书均「已验证」。关闭**有据** ✓

**B. 顺带小修（逐条独立验证）**
| 项目 | 验证方法 | 结果 |
|------|---------|------|
| ISS-135 `make help` | `make help > log 2>&1; echo $?` | EXIT=0, 45 lines ✓ |
| ISS-136 计数 | `grep -c '^- id:' contracts/opcodes.yaml` = 228；`rule_refs: []` = 37 → 非空 = 191 | 228/191 ✓ |
| ISS-136 doc 嵌入 | `legality_rules.yaml` L18: `（228 条：`；`check_scope.py` L15: `152/60/15/228`；`gen_legality_list.py` L7: `191 with rule_refs` | 3 处一致 ✓ |
| ISS-140 README | `find patches -name '*.patch' | wc -l` = 48；`grep -rl 'new file mode' | wc -l` = 44；mod = 4 | README 写 `**48 份** = 新增 44 + 修改 4` ✓ |
| ISS-144 changelog | `grep 'LLVM-040t\|LLVM-041t' changelog.md` | 两行均在 ✓ |
| ISS-145 043t 证据 | `bash .work/evidence/LLVM-043t/run.sh` | 11/11 PASS, EXIT=0 ✓ |
| ISS-145 045t 证据 | `bash .work/evidence/LLVM-045t/run.sh` | 19/19 PASS, EXIT=0 ✓ |
| ISS-145 非硬编码 | grep 043t/045t 脚本：`sed -nE` 解析计数 + 下限（>=29 lit-mc, >=122 oracle） | 模式/下限断言 ✓ |
| ISS-134 m1-asm | `python3 tools/llvm/test_m1_asm.py` | 152 passed, 0 failed, EXIT=0 ✓ |
| ISS-134 生成器改动 | `git diff tools/llvm/gen_m1_asm.py`：`24i→96`、`4i→16`、`2i→8`；`test_m1_asm.py` 未改动 | 改生成器非 test 放宽 ✓ |

**C. 边界重定**
| ISS | status | M3 in notes | M4 in notes |
|-----|--------|-------------|-------------|
| ISS-005 | open | ✓ | ✓ |
| ISS-006 | open | ✓ | ✓ |
| ISS-008 | open | ✓ | ✓ |
| ISS-019 | open | ✓ | ✓ |
| ISS-026 | open | ✓ | ✓ |
| ISS-074 | open | ✓ | ✓ |
| ISS-081 | open | ✓ | ✓ |
| ISS-110 | open | ✓ | ✓ |

- 8 条均 `open`，notes 含 M3/M4 边界，未被误关 ✓
- `scope` 枚举不含 M4（仅 m1/fp/excluded/m3）→ 只改 notes 不改 scope，**可接受**（机械约束）

**D. 保持 open**
- 29 条 D 项全部 `status=open`，`git diff` 未触及 ✓

---

##### 五、3 条披露判定

1. **`legality_rules.yaml` L19 分解行**：L18 改 228 后，L19 分解（152+60+15=227）与总和不自洽。新增 `+ 1 条 scope: m3` 使 152+60+15+1=228。独立验证 `opcodes.yaml` scope 分布：m1=152, fp=60, excluded=15, m3=1, total=228。**必要且正确** ✓

2. **`gen_m1_asm.py`/`test_m1_asm.py` docstring 仍写「177」**：实际152。ISS-134 范围是「旧 `i` 后缀语法→新语法」，docstring 计数陈旧属不同问题。**建议另立小 issue**（不在本任务范围内，已如实登记「新发现/坑」）✓

3. **ISS-140 的 README 实为 `components/llvm-project/README.md`**：仓库根 `README.md` 无 LLVM 补丁数；唯一含该计数的确实是 `components/llvm-project/README.md`。**与 issue 描述一致**（ISS-140 原文：「README.md 中 LLVM 补丁数陈旧」，上下文即该文件）✓

---

##### 六、门控

| 检查项 | 结果 |
|--------|------|
| `make check` | EXIT=0, 34/34 passed, repository checks: PASS ✓ |
| `make check-no-residue` | EXIT=0, PASS ✓ |
| `git status` | 8 个应改文件 + 1 个新任务书；无 tests/ 残留 ✓ |
| `test_m1_asm.py` | 152/152 passed, EXIT=0 ✓ |

---

##### 判决

**Accepted**

全部 9 项证据检查通过（独立重跑确认）。工程师 6 项自检注入 + reviewer 1 项独立注入均 FAIL→还原→回绿。A/B/C/D 逐条独立验证无误。3 条披露均有据。门控全绿，仓库无残留。
