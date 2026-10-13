# INFRA-037t: infra/integ 工具与文档小修（asm-prose stdout、build-mc help、LLVM 补丁计数）

**模块**：infra
**项目里程碑**：M3
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地

## 目标与 resolved_by

合并 3 条无依赖的工具/文档小修 issue（纯 Python/文本，无组件重建）。完成后应关闭：

| ISS | 改动点 |
| --- | --- |
| ISS-094 | `tools/spec/check_asm_prose.py` 域外场景 stdout 仍打 PASS（rc=1 但 stdout 语义不一致） |
| ISS-132 | `Makefile` 的 `build-mc` help 文本仍写 "LLVM MC tools"，未提 `llc` |
| ISS-133 | `components/llvm-project/README.md` 补丁数 36 陈旧（LLVM-033t 后实为 45） |

`resolved_by`：本任务 `INFRA-037t`。

## 接口规范

- **输入**（已核实）：
  - `tools/spec/check_asm_prose.py:734-771`：`--files` 有域外文件时 `had_out_of_scope=True`，但 `report()`（L682）在 0 violations 时先打印 `check-asm-prose: PASS (0 violations)`，随后才 `sys.exit(1)` ⇒ stdout 与退出码语义不一致。
  - `Makefile:65/67`：`make build-mc` / `build-mc-reconfig` 的 help 文案。
  - `components/llvm-project/README.md:9`：`规模（2026-09-23 M1 重整后）：**36 份** = 新增 32 + 修改 4。`
- **输出**：修正后的 `check_asm_prose.py`、`Makefile`、`components/llvm-project/README.md`。
- **约束**：
  - ISS-094：`had_out_of_scope` 时 stdout 须打 `FAIL (out-of-scope --files)`，不得再打 `PASS`；正常 0 violations 仍打 PASS。
  - ISS-132：help 文案须与 `LLVM_MC_FULL_TARGETS`（已含 `llc`，见 `INFRA-035t`）一致，最小改动。
  - ISS-133：README 补丁数**由命令推导、不得手写猜测**：总数 = `find components/llvm-project/patches -name '*.patch' | wc -l`；`新增/修改` = 按各 patch 是否含 `new file mode` 统计（或在 README 中改为「总数」单一表述，避免易腐化）。**保留** `2026-09-23 M1 重整后` 语义的历史数字时可另起一行注明最新值，不得抹掉历史。

## 验收标准

1. **ISS-094**：构造域外 `--files` 输入 → **EXIT≠0 且 stdout 不含 `PASS`**、含 `out-of-scope`/`FAIL`；正常扫描 0 violations → EXIT=0 且 stdout 含 PASS。给出真实输出。
2. **ISS-132**：`grep -n "LLVM MC tools" Makefile` → 0 命中；`make help`（或对应 echo）输出含 `llc`。
3. **ISS-133**：README 补丁数 == `find components/llvm-project/patches -name '*.patch' | wc -l`（当前 45），且 `新增`/`修改` 之和等于总数（给出统计命令与输出）。
4. **反例门控**：把 README 数字改回 36（临时副本）⇒ 验收 3 的比对 FAIL；还原。把 `check_asm_prose` 的域外分支改回打 PASS ⇒ 验收 1 FAIL；还原。
5. 改动落在门控覆盖范围（`Makefile`、`tools/**`）时 `make check` EXIT=0；`components/llvm-project/README.md` 属文档，不作为门控阻断项。

## 硬约束

- 临时目录 `/tmp/opencode/INFRA-037t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件，越界须披露。
- 复杂命令输出留存 `.work/log/infra/INFRA-037t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/INFRA-037t/`，可复用检查器落 `tools/infra/`。

## 完成区
**测试结果**：通过 **6/6**（一键脚本 `.work/evidence/INFRA-037t/run.sh` EXIT=0）；`run.sh --inject` 反例门控 EXIT=0（2 组「注入→预期 FAIL→还原→回绿」全 PASS）。`make check` EXIT=0（lit 33/33、`repository checks: PASS`）；`make check-asm-prose` EXIT=0；`make check-patch-tree` EXIT=0（77 OK）；`python3 -m compileall` EXIT=0。
**修改文件**：
- `tools/spec/check_asm_prose.py`（ISS-094；+10/-1 行附近，仅 main() 输出分支）
- `Makefile`（ISS-132；help 中 build-mc / build-mc-reconfig 各 1 行）
- `components/llvm-project/README.md`（ISS-133；新增「（当前）45 份」1 行，历史行原样保留）
- 新增（gitignored，不入库）：`.work/evidence/INFRA-037t/run.sh`；日志 `.work/log/infra/INFRA-037t-*.log`

**验收结果**：

1. **ISS-094**（`cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，日志 `.work/log/infra/INFRA-037t-asm-outofscope.log` / `-asm-normal.log`）：
```
$ python3 tools/spec/check_asm_prose.py --files README.md   # 域外文件
EXIT=1
ERROR: --files argument outside scan scope: /mnt/tao/DADAO-v5/README.md      # stderr
check-asm-prose: FAIL (out-of-scope --files)                                  # stdout

$ python3 tools/spec/check_asm_prose.py                     # 正常扫描
EXIT=0
check-asm-prose: PASS (0 violations)
```
- 域外场景 **stdout 不含 `PASS`**（单独捕获 stdout 确认），含 `FAIL`/`out-of-scope`；正常 0 violations EXIT=0 含 PASS。
- 边界（自审补充）：域外文件 + 域内违规文件混用 → stdout 打 `FAIL (out-of-scope --files)` 后列违规，**无 PASS**，EXIT=1（真实输出见审阅记录）。

2. **ISS-132**（日志 `INFRA-037t-grep-mc.log` / `-make-help.log`）：
```
$ grep -n "LLVM MC tools" Makefile
EXIT=1        # 0 命中

$ sed -n '/^help:/,/^$/p' Makefile | grep -E 'make (build-mc|build-mc-reconfig) '
	@echo "  make build-mc        Build LLVM MC + CodeGen tools incl. llc (skips cmake if build.ninja exists)"
	@echo "  make build-mc-reconfig  Force cmake re-run then build LLVM MC + CodeGen tools incl. llc"
```
- 文案与 `LLVM_MC_FULL_TARGETS = ... FileCheck not LLVMDADAOCodeGen llc` 一致（含 `llc`），符合 `build-mc-lite` 仍标注 `no ... CodeGen` 的对照。
- **注意**：`make help` 本身 EXIT=2，但为**预先存在**的 `Makefile:83` 反引号 bug（HEAD 即有，与本改动无关，见「新发现/坑」）；故按验收 2 允许的「对应 echo」路径验证。

3. **ISS-133**（日志 `INFRA-037t-readme-count.log`）：
```
$ find components/llvm-project/patches -name '*.patch' | wc -l
45
$ grep -rl 'new file mode' components/llvm-project/patches --include='*.patch' | wc -l
41
$ grep -rL 'new file mode' components/llvm-project/patches --include='*.patch' | wc -l
4
$ grep -n '规模（当前）' components/llvm-project/README.md
9:- 规模（当前）：**45 份** = 新增 41 + 修改 4（总数：`find ... | wc -l`；新增/修改：按各 patch 是否含 `new file mode` 统计）。
```
- README 当前值 45 == 命令推导 45；41 + 4 == 45。4 个「修改」补丁与 README line 10 所列 4 个上游文件一致；45 个 patch 均为单文件（各含 1 行 `diff --git`）。
- 历史行 `- 规模（2026-09-23 M1 重整后）：**36 份** = 新增 32 + 修改 4。` **原样保留**，未抹掉历史。

4. **反例门控**（`.work/log/infra/INFRA-037t-evidence-inject.log`，`run.sh --inject` EXIT=0）：
```
      [FAIL] 133-patch-count | ... actual readme=36 total=45 ... | check-rc=1   # README 改回 36 → 预期 FAIL
[PASS] inject-readme         | ... observed 1 injected FAIL
      [PASS] 133-patch-count | ... actual readme=45 total=45 ...                # 还原后回绿
[PASS] recover-readme        | ... 0 new FAIL
      [FAIL] 094-outofscope  | ... stdout=check-asm-prose: PASS (0 violations)  # 域外分支改回打 PASS → 预期 FAIL
[PASS] inject-asm-prose      | ... observed 1 injected FAIL
      [PASS] 094-outofscope  | ... stdout=check-asm-prose: FAIL (out-of-scope)  # 还原后回绿
[PASS] recover-asm-prose     | ... 0 new FAIL
```
- 注入后 `git diff --name-only` 仍仅 Makefile / README / check_asm_prose.py（已还原，且脚本内 `cmp` 逐字节校验）。

5. **门控**：`make check` EXIT=0；`git status --untracked-files=all` 仅 3 个预期改动文件。

**新发现/坑**：
- **`make help` 预先存在故障（非本任务引入）**：`Makefile:83` 的 `@echo "  make check-spec-codeblocks  Check spec prose ```simrisc blocks vs opcodes.yaml (ISS-077)"` 含三反引号，`/bin/sh`（dash）将其解释为命令替换 → `Syntax error: EOF in backquote substitution`，`make help` EXIT=2。`git show HEAD:Makefile | sed -n '83p'` 确认 HEAD 即如此。**建议登记新 issue**：将该 echo 中的反引号改为单引号包裹或转义（`\``）。本任务范围外，未改。
- README 采用双行计数：历史行原样保留，新增「（当前）」行；证据脚本按标签 `规模（当前）` 精确解析，避免历史/当前混淆，且解析失败时 fail-closed（不会假 PASS）。
- 补丁分类稳定：45 = 41（含 `new file mode`）+ 4（修改），4 个修改补丁与 README 所列一致；每个 patch 单文件（各 1 个 `diff --git`）。

**遗留问题**：3 项 issue（ISS-094 / ISS-132 / ISS-133）全部修复，无遗留。附带发现 `make help` 预存在反引号故障（见「新发现/坑」），属独立 issue，未在本任务修复（越界，已披露）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审方式**：全局 `subagent_depth=1`，无法起嵌套子代理，采用自主逐行审查 + 真实命令复验（边界用例）。**当时无 reviewer 记录**（首轮）。

**逐行审查**：

- `tools/spec/check_asm_prose.py` main()：新增 `if had_out_of_scope: print(FAIL...)`，并把 `report()` 调用改为 `if violations or not had_out_of_scope:`。四种组合逐条核实：

  | had_out_of_scope | violations | stdout | rc | 结论 |
  | --- | --- | --- | --- | --- |
  | True | 空 | `FAIL (out-of-scope --files)` | 1 | ✓ 验收 1 |
  | True | 非空 | `FAIL...` + 违规列表（**无 PASS**） | 1 | ✓ 边界（真实输出见下） |
  | False | 空 | `PASS (0 violations)` | 0 | ✓ 验收 1 |
  | False | 非空 | 违规列表（原行为，未改） | strict?1:0 | ✓ |

- `Makefile` help：两处 `LLVM MC tools` → `LLVM MC + CodeGen tools incl. llc`，与 `LLVM_MC_FULL_TARGETS`（含 `LLVMDADAOCodeGen`、`llc`）一致；`build-mc-lite` 的 `no ... CodeGen` 描述未动，对照关系仍成立。
- `README.md`：新增「（当前）」行置前，历史行原样在后；证据脚本按标签 `规模（当前）` 解析当前值，解析为空则判 FAIL（fail-closed，不会假 PASS）。

**边界真实输出**（域外 `notes.txt` + 域内含违规 `spec/doc.md` 混用）：
```
$ python3 tools/spec/check_asm_prose.py --root /tmp/opencode/INFRA-037t/mixroot --files spec/doc.md notes.txt
EXIT=1
check-asm-prose: FAIL (out-of-scope --files)
check-asm-prose: 1 violation(s) found
--- violation list ---
spec/doc.md:
  L4: [R1(访存缺[])] ld.w rb1, 0
（stdout 无 PASS；stderr：ERROR: --files argument outside scan scope: .../notes.txt）
```

**findings 与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- | --- |
| 1 | 证据脚本 `--inject` 把**预期注入 FAIL** 计入退出码，注入成功反而 EXIT=1 | ✅已修 | 注入检查改在子 shell 单独计数（`run_check_sub`），不污染顶层 `FAILS` | `run.sh --inject` EXIT=0，`summary: 0 FAIL` |
| 2 | 注入期间若被中断会残留被改文件（违反「可复原」） | ✅已修 | EXIT trap 还原 + 启动清理陈旧备份 + `cmp` 逐字节校验 | 注入后 `git diff --name-only` 仅 3 个预期文件 |
| 3 | 验收仅覆盖「纯域外」「纯正常」，未覆盖「域外 + 域内违规」混合 | ✅已修 | 证据脚本新增 `094-mixed`（临时 root fixture） | `[PASS] 094-mixed`（见上）；green 6/6 |
| 4 | `check_133` 依赖 `grep -oP`（GNU PCRE） | ❌不修 | — | 本环境 `grep -P` 可用（readme=45）；无 `-P` 时解析为空 → check FAIL，**fail-closed 不假 PASS** |
| 5 | `make help` EXIT=2 | ❌不修（范围外） | — | 预先存在：`git show HEAD:Makefile \| sed -n '83p'` 含反引号 echo；已入「新发现/坑」并建议登记独立 issue |
| 6 | README 双行数字可能被朴素解析取到历史值 36 | ❌不修 | — | 当前行置前 + 标签 `规模（当前）`；证据脚本按标签解析，消除歧义 |

**判决**：finding 1–3 已修、4–6 判不修（均附证据，其中 5 为范围外预存在缺陷、已转 issue 候选）；证据脚本 green **6/6** + `--inject` EXIT=0；`make check` EXIT=0。状态 → `待验收`。

#### 第 1 轮 reviewer 验收

**审查方式**：独立重跑证据脚本 + 独立注入反例 + 逐项核验。

---

**一、证据脚本审阅**

逐条核对 `.work/evidence/INFRA-037t/run.sh`：

| 项目 | 判定 |
| --- | --- |
| 每个 check 函数有 PASS/FAIL 两分支 | ✓ 无恒真 |
| `run_check_sub` 子 shell 隔离注入 FAILs | ✓ 注入不污染顶层退出码 |
| EXIT trap `restore_all()` 还原 | ✓ 启动时 `rm -f` 陈旧备份 |
| `cmp -s` 逐字节校验注入/还原 | ✓ 注入后验证文件变了，还原后验证一致 |
| 无 `tee` 吞退出码 | ✓ 结尾 `exit $FAILS`（0/1） |
| `--inject` 路径验证注入非空 | ✓ `inject_readme`/`inject_asm_prose` 均有 `cmp -s` 检查 |

**结论**：证据脚本合格，不代写/不改。

---

**二、重跑 `run.sh`（常规模式）**

```
$ bash .work/evidence/INFRA-037t/run.sh > /tmp/opencode/INFRA-037t-review/run.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
```

逐项：

| # | 检查名 | 期望 | 实际 | check-rc |
| --- | --- | --- | --- | --- |
| 1 | 094-outofscope | rc!=0, FAIL+out-of-scope, no PASS | rc=1; stdout=check-asm-prose: FAIL (out-of-scope --files) | 0 |
| 2 | 094-normal | rc=0 and stdout has PASS | rc=0; stdout=check-asm-prose: PASS (0 violations) | 0 |
| 3 | 094-mixed | rc!=0, FAIL+violation, no PASS | rc=1; stdout 含 FAIL+violation, 无 PASS | 0 |
| 4 | 132-no-old-phrase | 0 matches of 'LLVM MC tools' | matches=0 | 0 |
| 5 | 132-help-llc | both build-mc lines mention llc | count=2 | 0 |
| 6 | 133-patch-count | readme==total and new+mod==total | readme=45 total=45 new=41(actual 41) mod=4(actual 4) sum=45 | 0 |

**summary: 0 FAIL**，6/6 全绿。

---

**三、重跑 `run.sh --inject`（反例注入模式）**

```
$ bash .work/evidence/INFRA-037t/run.sh --inject > /tmp/opencode/INFRA-037t-review/run-inject.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
```

注入日志：

| 阶段 | 检查 | 结果 | 说明 |
| --- | --- | --- | --- |
| 注入 README=36 | 133-patch-count | **[FAIL]** readme=36 total=45 | 注入有效，预期 FAIL |
| inject-readme | — | [PASS] observed 1 injected FAIL | — |
| 还原 README | 133-patch-count | [PASS] readme=45 total=45 | 回绿 |
| recover-readme | — | [PASS] 0 new FAIL | — |
| 注入 asm-prose→PASS | 094-outofscope | **[FAIL]** stdout=check-asm-prose: PASS (0 violations) | 注入有效，预期 FAIL |
| inject-asm-prose | — | [PASS] observed 1 injected FAIL | — |
| 还原 asm-prose | 094-outofscope | [PASS] stdout=FAIL (out-of-scope) | 回绿 |
| recover-asm-prose | — | [PASS] 0 new FAIL | — |

**summary: 0 FAIL**。2 组注入→FAIL→还原→回绿全 PASS。

---

**四、独立注入（与 engineer 不同的注入点）**

**注入点**：`components/llvm-project/README.md` `新增 41` → `新增 42`（改变新增数使 42+4≠45，与 engineer 改总分为 36 的注入不同）。

```
# 注入前备份
$ cp components/llvm-project/README.md /tmp/opencode/INFRA-037t-review/README.md.bak

# 注入：新增 41 → 新增 42
$ sed -i 's/新增 41/新增 42/' components/llvm-project/README.md
$ git diff --name-only components/llvm-project/README.md
components/llvm-project/README.md                          ← 非空，注入有效

# 运行 check_133 逻辑
readme_num=45 total=45 new_c=42 mod_c=4 fresh_new=41 fresh_mod=4
OK=0                                                        ← FAIL（42≠41）

# 还原
$ cp /tmp/opencode/INFRA-037t-review/README.md.bak components/llvm-project/README.md
$ cmp /tmp/opencode/INFRA-037t-review/README.md.bak components/llvm-project/README.md
BYTE-IDENTICAL                                              ← 还原干净

# 还原后重跑证据脚本
$ bash .work/evidence/INFRA-037t/run.sh
EXIT=0                                                      ← 全绿回绿
```

**结论**：独立注入确认 check_133 对"新增数错误"场景能正确报 FAIL，还原后回绿。

---

**五、逐项独立复核**

**ISS-094**：
- `check_asm_prose.py` diff：仅 main() 输出分支新增 `had_out_of_scope` 判断，打印 `FAIL (out-of-scope --files)` 后条件调用 `report()`——域外+无违规时不调 `report()`（避免打 PASS），域外+有违规时仍调 `report()` 列违规。
- 逻辑正确：四种组合（域外×有无违规）均验证通过。

**ISS-132**：
```
$ grep -n "LLVM MC tools" Makefile
EXIT=1        # 0 命中 ✓

$ sed -n '/^help:/,/^$/p' Makefile | grep -E 'make (build-mc|build-mc-reconfig) '
	@echo "  make build-mc        Build LLVM MC + CodeGen tools incl. llc (skips cmake if build.ninja exists)"
	@echo "  make build-mc-reconfig  Force cmake re-run then build LLVM MC + CodeGen tools incl. llc"
```
- 两行均含 `llc`，与 `LLVM_MC_FULL_TARGETS` 一致。

**ISS-133**：
```
$ find components/llvm-project/patches -name '*.patch' | wc -l
45
$ grep -rl 'new file mode' components/llvm-project/patches --include='*.patch' | wc -l
41
$ grep -rL 'new file mode' components/llvm-project/patches --include='*.patch' | wc -l
4
```
- README 当前行 `45 份 = 新增 41 + 修改 4`，与命令推导一致。
- 口径独立核对：`new file mode` 判「新增」= 新文件补丁（41），无 `new file mode` = 修改既有文件补丁（4）。4 个修改补丁为 `llvm/CMakeLists.txt.patch`、`llvm/include/llvm/TargetParser/Triple.h.patch`、`llvm/lib/TargetParser/Triple.cpp.patch`、`llvm/lib/TargetParser/TargetDataLayout.cpp.patch`，与 README line 11 所列 `llvm/CMakeLists.txt`、`TargetParser/{Triple.h,Triple.cpp,TargetDataLayout.cpp}` **精确一致**。口径成立。
- 历史行 `- 规模（2026-09-23 M1 重整后）：**36 份** = 新增 32 + 修改 4。` 原样保留。✓

**`make check`**：
```
$ make check > /tmp/opencode/INFRA-037t-review/make-check.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
```
- lit 33/33 PASS，repository checks: PASS。门控全绿。✓

---

**六、`make help` 预存故障判定**

```
$ git show HEAD:Makefile | sed -n '83p'
	@echo "  make check-spec-codeblocks  Check spec prose ```simrisc blocks vs opcodes.yaml (ISS-077)"

$ make help > /tmp/opencode/INFRA-037t-review/make-help.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=2
```

- **确认为 HEAD 既有**：`git show HEAD:Makefile` line 83 即含三反引号，dash 将其解释为命令替换 → `Syntax error: EOF in backquote substitution`。非本任务引入。
- **判定**：属独立缺陷，建议另立 issue。本任务验收 2 按任务书允许的「对应 echo」路径验证（`sed -n` 提取 help 段 + grep），路径合理，验收 2 **可接受**。

---

**七、越界核验**

```
$ git diff --name-only
.tao/tasks/infra/INFRA-037t-...md    ← 任务书本身（含审阅记录）
Makefile
components/llvm-project/README.md
tools/spec/check_asm_prose.py
```

仅 3 个目标文件 + 任务书，无越界。`git status` 无临时残留。✓

---

**判决：Accepted**

- 验收 1（ISS-094）：域外→EXIT=1 且 stdout 无 PASS 含 FAIL/out-of-scope；正常→EXIT=0 含 PASS；混合边界→正确。✓
- 验收 2（ISS-132）：`LLVM MC tools` 0 命中；echo 含 llc；`make help` EXIT=2 为 HEAD 预存故障，不影响验收。✓
- 验收 3（ISS-133）：README 45 == 命令 45；41+4=45；`new file mode` 口径与 README 所列文件精确一致。✓
- 反例门控：engineer 的 `--inject`（改总分/改输出）+ reviewer 独立注入（改新增数）均确认 FAIL 路径可达，还原后回绿。✓
- `make check` EXIT=0。✓
- 无越界、无临时残留。✓
