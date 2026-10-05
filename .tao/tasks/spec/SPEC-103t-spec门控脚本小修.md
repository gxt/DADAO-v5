# SPEC-103t: spec 门控脚本小修（--verify 退出码、gate2 死分支、正文代码块门控、root n=2 门控）

**模块**：spec
**项目里程碑**：M3
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地

## 目标与 resolved_by

合并 4 条无依赖的 spec 门控 issue（纯 Python，无组件重建）。完成后应关闭：

| ISS | 改动点 |
| --- | --- |
| ISS-122 | `tools/spec/gen_legality_list.py --verify` 检出 MISMATCH 时须非零退出 |
| ISS-123 | `tools/spec/check_rule_refs.py` 的 `gate2_fail` 分支不可达 |
| ISS-077 | spec 正文代码块正确性接入永久门控（现仅任务级 reviewer 脚本） |
| ISS-079 | `ftroot`/`foroot` n=2 约束与规则改名缺机械门控 |

`resolved_by`：本任务 `SPEC-103t`。

## 接口规范

- **输入**（脚本现状，已核实）：
  - `gen_legality_list.py:329-336`：`--verify` 分支打印 `OK/MISMATCH` 后**恒 `return 0`**（MISMATCH 也返回 0）。
  - `check_rule_refs.py:63-94`：`gate2_fail` 置位后由 `if gate1_fail or gate2_fail:` 统一失败；但存在「豁免自检先行退出」路径使 `gate2_fail` 不可达。
  - `check_asm_prose.py`：仅检**旧格式**违规（ADR-0013），**不**逐行比对生成表 ⇒ 新格式正文块无永久门控。
  - `gen_legality_list.py:51/80`：`encode_fp_root_n = "ftroot/foroot n≠2 → ILLI"` 为 `RULE_SUMMARY` 文案；`SPEC-067t` F4 的 n=2 约束与规则改名无独立机械门控。
- **输出**：修订后的 4 个 checker（含新增/抽取的公共检查），并接入 `make check`（若尚未接入）。
- **约束**：
  - ISS-122：仅改 `--verify` 退出行为；**不得**改变 `--apply`/默认渲染输出。
  - ISS-123：要么**删除**不可达分支（精简），要么**使其可达**；不得留下无断言价值的死代码。
  - ISS-077：新增门控须以 `contracts/opcodes.yaml`（经 `tools/llvm/gen_asm_list.py` / 生成表）为唯一真源；伪指令行需**例外表**（用户/规范确认的伪指令 `return` 等），不得硬编码全表。**若评估后认为成本高于收益，须给出评估结论并登记 deferred（不静默跳过）。**
  - ISS-079：门控须覆盖「`ftroot`/`foroot` 的 `immu6 != 2 ⇒ ILLI`」与「规则改名（新 id 生效、旧 id 0 命中）」，来源 `contracts/legality_rules.yaml` + `opcodes.yaml`。
  - 一切检查器须**可失败**（见验收 5）。
  - 若新增脚本，落 `tools/spec/` 并随产物入库；同时更新 `spec/README.md` 或对应 Makefile 目标（按最小改动）。

## 验收标准

1. **ISS-122**：构造 LEGALITY 区与期望不符的临时 fixture，`gen_legality_list.py --verify` → **EXIT≠0** 且 stdout/stderr 含 `MISMATCH`；一致时 EXIT=0。还原。
2. **ISS-123**：`check_rule_refs.py` 对孤儿 `rule_refs`（引用不存在的规则）报 FAIL（EXIT≠0）；对合法输入 EXIT=0。若选择删除死分支，须在完成区给出「删除前不可达」的证据（逐行说明）。
3. **ISS-077**：新门控对「正文 ```simrisc 块某行汇编格式/助记符错误」报 FAIL（EXIT≠0）；对当前仓库正文 EXIT=0。给出**至少 1 条可失败断言**的真实注入输出。
4. **ISS-079**：注入「`ftroot` 的 `immu6` 由 2 改为 3 且未标 ILLI」或「规则旧 id 复活」→ 门控 FAIL；还原 → 全绿。
5. **反例门控（逐脚本）**：每个新增/修改的 checker 都须有可达 FAIL 路径；不得出现「两支写同一结果」「断言恒真」。给出注入→FAIL→还原→PASS 的真实输出。
6. `make check` EXIT=0（新增 checker 接入后）；`make check-rule-refs`、`make check-legality-drift` 仍全绿。

## 硬约束

- 临时目录 `/tmp/opencode/SPEC-103t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件，越界须披露。
- 复杂命令输出留存 `.work/log/spec/SPEC-103t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/SPEC-103t/`，可复用检查器落 `tools/spec/`。

## 完成区
**测试结果**：`make check` **EXIT=0**；一键证据 `bash .work/evidence/SPEC-103t/run.sh` **EXIT=0**（**EVIDENCE: PASS (28 checks)**）；四个 checker 逐脚本「注入→FAIL→还原→PASS」均实测通过。基线四门控全绿：`check-rule-refs`、`check-legality-drift`、`check-spec-codeblocks`（619 指令行）、`check-legality-invariants`。

**修改文件**（6 tracked + 1 gitignored 证据脚本）：
- `tools/spec/gen_legality_list.py`（ISS-122：`--verify` 检出 MISMATCH → 非零退出）
- `tools/spec/check_rule_refs.py`（ISS-123：删除恒不可达的 gate2 + 文档/注释同步）
- `tools/spec/check_asm_prose.py`（ISS-077 辅助：`_FORMAT_OP_COUNTS` 补 `crrr/crii/ciii`，消除 cfx 家族操作数检查静默跳过）
- `tools/spec/check_spec_codeblocks.py`（**新建**，ISS-077）
- `tools/spec/check_legality_invariants.py`（**新建**，ISS-079）
- `Makefile`（新增 `check-spec-codeblocks`/`check-legality-invariants` target，接入 `make check`，`.PHONY` + help）
- `.work/evidence/SPEC-103t/run.sh`（**新建**，一键证据脚本；`.work/` 被 gitignore，不入 git）

**验收结果**（真实输出/退出码；日志 `.work/log/spec/SPEC-103t-*.log`；全部命令用 `> log 2>&1; rc=$?`，无 `tee`）：
1. **ISS-122**：注入 drift（`spec/SimRISC-01-取数存数.md` LEGALITY 块内插行）→ `python3 tools/spec/gen_legality_list.py --verify` `EXIT=1`、stdout 含 `MISMATCH`；`cp` 还原 → `EXIT=0`；`git diff --quiet` → `EXIT=0`（干净）。
2. **ISS-123**：注入 `__bogus_rule__` → `EXIT=1` 打印 `FAIL [Gate 1] … rule_ref '__bogus_rule__'`；追加孤儿 `active` 规则 → `EXIT=1` 打印 `FAIL: 孤儿豁免清单自检失败`；还原 → `EXIT=0`、git 干净。**删除前不可达逐行证据**见「自审」。
3. **ISS-077**：对仓库正文 `check-spec-codeblocks: PASS (619 instruction line(s) checked against contracts/opcodes.yaml)` `EXIT=0`；fixture「未知助记符 `foobar.baz rd1, rd2`」→ `EXIT=1`（`未知助记符`）；fixture「`add.so rd1, rd2`（计数 2∉{3,4}）」→ `EXIT=1`（`操作数个数`）；fixture「`cfx2rd cfx_umon, rd2, rd3`（计数 3∉{2,4}）」→ `EXIT=1`。
4. **ISS-079**：`contracts/opcodes.yaml` 中 `ftroot` 的 `- immu6 == 2` → `== 3` → `EXIT=1`（`legality 缺 'immu6 == 2'`，ftroot+foroot 各 1 条）；旧 id `fp_root_invalid_n` 复活（legality_rules.yaml）→ `EXIT=1`；新旧 id 全量反注（opcodes rule_refs + 规则 id）→ `EXIT=1`（8 条 FAIL，覆盖 `新 id 缺失`/`旧 id 复活`/`仍引用旧 id`/`raw 命中`）；还原 → `EXIT=0`、git 干净。
5. **反例门控**：`run.sh` 28/28 PASS（逐 checker 注入→FAIL→还原→PASS + restore `git diff --quiet` 干净）。
6. **`make check` EXIT=0**；`make check-rule-refs` / `make check-legality-drift` / `make check-spec-codeblocks` / `make check-legality-invariants` 全 `EXIT=0`。

**新发现/坑**：
- spec 正文 ```simrisc 块中的非 opcodes 助记符**恰为 18 条伪指令**（`nop`、`return`、`not.{b,w,t,o}`、`neg.{b,w,t,o}`、`set.{rd,rb,ft,fo}`，来源 SimRISC-00 §伪指令 / `spec/Toolchain-01` §6）；`check_asm_prose` 的 R6 对**未知助记符不报错**（不在 opcodes 即静默跳过）——这正是 ISS-077 的实际缺口。
- `check_asm_prose._FORMAT_OP_COUNTS` 原先缺 `crrr/crii/ciii`（覆盖 `cfx2rd/cfx2rc/cfxld/cfxst/escape/trap`）⇒ 这些指令的操作数个数检查**静默跳过**；补齐后全 `check_asm_prose` 作用域 0 新增违规。
- `check_rule_refs.py` gate2 恒不可达的根因：孤儿自检（`actual_exempt != EXPECTED_ORPHAN_EXEMPTIONS` → `exit(1)`）先于 gate2 且更严格（断言豁免清单恰为 4 条），任何「active 且 0 引用且非豁免」规则都会先落入自检退出。删除 gate2 后孤儿检测语义不变（注入验证 `EXIT=1`）。
- 建议沉淀：新增两个 spec 门控的「真源 + 例外表」口径（ISS-077 伪指令例外表；ISS-079 rename registry 来源 SPEC-067t/070t）。

**遗留问题**：
- **ISS-079 门控仅覆盖 `contracts/` 层**（`opcodes.yaml` 的 `legality`/`rule_refs` + `legality_rules.yaml` 的 id/status/fault/description），**不**覆盖 `spec/SimRISC-07` 正文字面措辞——任务书明确来源为 `legality_rules.yaml` + `opcodes.yaml`，故 F4 原文的正文注入（把正文写回「支持 n=2 与 n=3」）本任务不 FAIL。若要闭合正文侧，需另立任务（可由 `check_spec_codeblocks` 加一条根指令正文断言或新 checker）。已登记，供架构师/用户裁定。
- 其余无未完成项；所有验收 1–6 均实测通过。

**逐行不可达证据（ISS-123，删除前）**：
- 原 `check_rule_refs.py` L41–61：`actual_exempt = {active 规则且其 id 不被任何 opcodes rule_refs 引用}`；若 `actual_exempt != EXPECTED_ORPHAN_EXEMPTIONS` 则 L61 `sys.exit(1)`。
- 原 L71–90：gate2 遍历 `active`、非豁免规则，若 `ref_count.get(rid,0)==0` 置 `gate2_fail=True`。
- 反证：对任一条「active、非豁免、0 引用」的规则 `r`，有 `r ∈ actual_exempt` 且 `r ∉ EXPECTED_ORPHAN_EXEMPTIONS` ⇒ `actual_exempt ≠ EXPECTED` ⇒ 在到达 gate2 之前已于 L61 退出 ⇒ `gate2_fail` 恒为 `False`，`if gate1_fail or gate2_fail` 中 gate2 分支不可达。
- 删除后由该自检承担孤儿检测（注入孤儿规则实测 `EXIT=1`），语义不变、无假 PASS。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`gen_legality_list.py`、`check_rule_refs.py`、`check_asm_prose.py`、`check_spec_codeblocks.py`（新）、`check_legality_invariants.py`（新）、`Makefile`、`.work/evidence/SPEC-103t/run.sh`（逐行审查）。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `check_spec_codeblocks` 在 main 与 scan 中重复 `_load_opcode_formats()` | ✅已修 | `scan()` 改为接收 `opcode_formats` 参数 | 复跑 `check-spec-codeblocks` EXIT=0 |
| 2 | `scanned` 把 label/注释行计入「checked」，口径不实 | ✅已修 | `check_line` 返回 `(violations, is_instruction)`，仅计指令行 | 计数 820→619 |
| 3 | `_FORMAT_OP_COUNTS` 缺 `crrr/crii/ciii` ⇒ cfx 家族操作数检查静默跳过 | ✅已修 | `check_asm_prose` 补 3 格式；新 checker 复用同一表 | `make check-asm-prose` EXIT=0；`cfx2rd` 3-操作数 fixture EXIT=1 |
| 4 | ISS-079 `description` 的 n=2 检查对空格敏感 | ✅已修 | 改用 `re.search(r"n\s*=\s*2", …)` | 基线 `check-legality-invariants` EXIT=0 |
| 5 | 删除 gate2 后孤儿检测是否仍可达（不得留下无断言路径） | ✅已验 | 未改 | 注入孤儿 active 规则 → EXIT=1（`孤儿豁免清单自检失败`） |
| 6 | `--dry-run`/`--apply` 是否受 ISS-122 改动影响 | ✅已验 | 未改 | `verify_failed` 仅在 `--verify` 分支置位，其余路径 return 0 |
| 7 | ISS-079 是否覆盖「旧 id 出现在 opcodes rule_refs」回归路径 | ✅已验 | 未改 | 新旧 id 全量反注 → EXIT=1（8 条 FAIL） |
| 8 | `check_spec_codeblocks` 是否会漏检「label 与指令同行」的行 | ✅已验 | 未改 | 全 spec 扫描该模式 0 命中（无需处理） |
| 9 | 检查器是否可失败（无恒真/两支写同一结果） | ✅已验 | 未改 | 逐 checker 注入→FAIL→还原→PASS，`run.sh` 28/28；含 `make check` 全量 EXIT=0 |

**判决**：所有 finding 已修/已验，无遗留。任务可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查范围**：证据脚本 `.work/evidence/SPEC-103t/run.sh` 逐行审查 + 全部 7 个交付物文件 + 独立注入验证。

##### 1. 证据脚本审查

脚本质量合格：
- 每条断言有可达 FAIL 路径（`expect=nonzero` / `expect=0` / `expect=yes`），无恒真 / 「两支写同一结果」
- 结尾用 `exit 0` / `exit 1`（基于 `$FAILED`），未用 `tee` 吞退出码
- `run_rc` 用 `"$@" >"$log" 2>&1; return $?` 捕获真实退出码
- 备份 + `restore()` + `trap restore EXIT` 确保还原
- 4 个 checker 各有注入→FAIL→还原→PASS 自检（非空可还原）

##### 2. 重跑证据脚本

```
bash .work/evidence/SPEC-103t/run.sh > /tmp/opencode/SPEC-103t-review/run.log 2>&1; rc=$?; echo "EXIT=$rc"
```

**EXIT=0**，28/28 全 PASS：

```
PASS  make check-rule-refs                                     expect=0    actual=0
PASS  make check-legality-drift                                expect=0    actual=0
PASS  make check-spec-codeblocks                               expect=0    actual=0
PASS  make check-legality-invariants                           expect=0    actual=0
PASS  gen_legality_list --verify (baseline)                    expect=0    actual=0
PASS  make check (full)                                        expect=0    actual=0
PASS  ISS-122 --verify (injected drift) rc!=0                  expect=nonzero actual=nonzero rc=1
PASS  ISS-122 --verify prints MISMATCH                         expect=yes  actual=yes
PASS  ISS-122 --verify (restored) rc=0                         expect=0    actual=0
PASS  ISS-122 restore git-clean                                expect=0    actual=0
PASS  ISS-123 bogus rule_ref rc!=0                             expect=nonzero actual=nonzero rc=1
PASS  ISS-123 bogus prints Gate 1                              expect=yes  actual=yes
PASS  ISS-123 orphan rule rc!=0                                expect=nonzero actual=nonzero rc=1
PASS  ISS-123 orphan prints 豁免自检                           expect=yes  actual=yes
PASS  ISS-123 restored rc=0                                    expect=0    actual=0
PASS  ISS-123 restore git-clean                                expect=0    actual=0
PASS  ISS-077 fixture valid rc=0                               expect=0    actual=0
PASS  ISS-077 bad mnemonic rc!=0                               expect=nonzero actual=nonzero rc=1
PASS  ISS-077 bad mnemonic prints 未知助记符                   expect=yes  actual=yes
PASS  ISS-077 bad operand count rc!=0                          expect=nonzero actual=nonzero rc=1
PASS  ISS-077 bad count prints 操作数个数                      expect=yes  actual=yes
PASS  ISS-077 repo baseline rc=0                               expect=0    actual=0
PASS  ISS-079 ftroot n=2->3 rc!=0                              expect=nonzero actual=nonzero rc=1
PASS  ISS-079 n3 prints immu6 == 2                             expect=yes  actual=yes
PASS  ISS-079 old id resurrect rc!=0                           expect=nonzero actual=nonzero rc=1
PASS  ISS-079 old id prints 复活                               expect=yes  actual=yes
PASS  ISS-079 restored rc=0                                    expect=0    actual=0
PASS  ISS-079 restore git-clean                                expect=0    actual=0
EVIDENCE: PASS (28 checks)
```

##### 3. 独立注入验证（reviewer 自行注入，非复用 engineer 的）

**注入 1：`check_spec_codeblocks.py`** — 修改真实 spec 文件 `spec/SimRISC-10-8位数据运算.md` 第 58 行 `add.ub rdHB, rdHC, rdHD` → `add.ub rdHB`（1 操作数，合法集合 {2,3}）：

```
EXIT=1
FAIL: spec/SimRISC-10-8位数据运算.md:58: 'add.ub' 操作数个数 1 不在合法集合 [2, 3]（format ['orrr']）
check-spec-codeblocks: FAIL (1 violation(s) in 619 instruction line(s))
```

还原 → EXIT=0，`git diff --quiet` → CLEAN=0 ✓

**注入 2：`check_legality_invariants.py`** — 从 `contracts/opcodes.yaml` 的 `ftroot_orri_rf` 删除 `encode_fp_root_n`（与 engineer 改 immu6 值不同角度）：

```
EXIT=1
FAIL: opcodes.yaml: 'ftroot_orri_rf' rule_refs 缺 'encode_fp_root_n' (实际 ['dst_rf0'])
check-legality-invariants: FAIL (1 violation(s))
```

还原 → EXIT=0，`git diff --quiet` → CLEAN=0 ✓

##### 4. 约束核验

| 约束 | 结果 | 证据 |
|------|------|------|
| ISS-122: `--verify` 检出 MISMATCH 须非零退出 | ✅ | 证据脚本 check 8-9: `rc=1` + `MISMATCH` 输出 |
| ISS-122: `--dry-run`/`--apply` 不受影响 | ✅ | `verify_failed` 仅在 `--verify` 分支置位（L336），其余路径 return 0 |
| ISS-123: 删除不可达分支 | ✅ | 逐行反证成立：`actual_exempt ≠ EXPECTED` ⇒ L61 exit(1) 先于 gate2 |
| ISS-123: 孤儿检测语义不变 | ✅ | 独立注入 `__inject_orphan__` → EXIT=1（`孤儿豁免清单自检失败`） |
| ISS-077: 伪指令例外表有据 | ✅ | 14 条（18 行去重）与 `SimRISC-00 §伪指令` + `Toolchain-01 §6` 一致 |
| ISS-077: 正文基线 EXIT=0 | ✅ | `check-spec-codeblocks: PASS (619 instruction line(s))` |
| ISS-079: ftroot/foroot n=2 门控 | ✅ | 注入 immu6 改 / rule_refs 删 → EXIT=1 |
| ISS-079: 旧 id 复活检测 | ✅ | 证据脚本 check 26: `fp_root_invalid_n` 复活 → EXIT=1 |
| `make check` EXIT=0 | ✅ | 证据脚本 check 6 + 独立重跑 |
| 新 checker 接入 `make check` | ✅ | Makefile L227 含 `check-spec-codeblocks` + `check-legality-invariants` |
| `_FORMAT_OP_COUNTS` 补齐 crrr/crii/ciii | ✅ | `check_asm_prose.py` L304-306 |
| 证据脚本不吞退出码 | ✅ | `run_rc` 用 `return $?`，结尾 `exit 0/1` |

##### 5. ISS-123 逐行不可达反证复核

原 `check_rule_refs.py` 逻辑链：
1. L42-47: `actual_exempt` = {active 规则 id ∉ 任何 opcodes rule_refs}
2. L51: 若 `actual_exempt ≠ EXPECTED_ORPHAN_EXEMPTIONS` → L61 `sys.exit(1)`
3. 原 gate2: 遍历 active、非豁免规则，`ref_count == 0` → `gate2_fail = True`

反证：对任一条「active、非豁免、0 引用」规则 r：
- r ∈ actual_exempt（因 0 引用）
- r ∉ EXPECTED_ORPHAN_EXEMPTIONS（因非豁免）
- ⇒ actual_exempt ≠ EXPECTED ⇒ L61 exit(1)
- gate2 恒不可达 ✓

删除后孤儿检测由自检承担（注入孤儿 → EXIT=1），语义不变 ✓

##### 6. ISS-079 门控覆盖披露

`check_legality_invariants.py` 仅覆盖 `contracts/` 层（`opcodes.yaml` 的 legality/rule_refs + `legality_rules.yaml` 的 id/status/fault/description），**不覆盖** `spec/SimRISC-07` 正文字面。任务书来源明确为 `legality_rules.yaml + opcodes.yaml`，此为已知限制，**非阻塞**——需另立任务闭合正文侧。工程师已在「遗留问题」中登记。

##### 7. 判决

**Accepted**。验收命令块全部通过（28/28 + `make check` EXIT=0）；两个新 checker 各有独立注入验证（与 engineer 不同注入点）；ISS-123 逐行反证成立；伪指令例外表有据；ISS-079 覆盖披露非阻塞已登记。
