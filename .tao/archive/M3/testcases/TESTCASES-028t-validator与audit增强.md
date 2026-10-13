# TESTCASES-028t: validator/audit 增强（br 双路径守卫、overlap 语义门控、009t-audit id 修正）

**模块**：testcases
**项目里程碑**：M3
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地

## 目标与 resolved_by

合并 3 条无依赖的 testcases 门控 issue（纯 Python，无组件重建）。完成后应关闭：

| ISS | 改动点 |
| --- | --- |
| ISS-025 | `br.*` 双路径（taken + not-taken）覆盖无结构性守卫 |
| ISS-097 | `class: overlap` 同组用例缺语义门控（覆盖≠语义再现） |
| ISS-099 | `tools/testcases/009t-audit.py` 对 `ctrl-ret` 全部 skip（旧 id `ret-riii` 应为 `ret_riii_ra`） |

`resolved_by`：本任务 `TESTCASES-028t`。

## 接口规范

- **输入**（已核实）：
  - `tools/testcases/validate_vectors.py`：`ctrl-br` 仅在注释中提及 taken/not-taken（L387-388），无结构性守卫；`cls in ("boundary","overlap")` 分支（L425-431）未对 overlap 组重算区间交集。
  - `tools/testcases/009t-audit.py:880`：`insn == "ret-riii"`，而 `contracts/opcodes.yaml` 中 `ret` 的 id 为 `ret_riii_ra` ⇒ ctrl-ret 全部 skip。
  - 向量真源：`tests/vectors/isa/*.yaml`、`tests/vectors/inventory.md`、`contracts/opcodes.yaml`。
- **输出**：`validate_vectors.py` 增强 + `009t-audit.py` id 修正。
- **约束**：
  - ISS-025：守卫须为**结构性**（如：同一 `br.*` 指令须同时存在 taken 与非 taken 两类用例；删任一条 ⇒ 报错），不得依赖注释或文本。
  - ISS-097：按 word 的 `hb/hc/immu6`（`{start:end}` 区间）**重算交集**；有交集且 `expected_fault != ILLI` ⇒ 报错（纯结构、可机械执行）。区间语义以 `contract-isa.md` / `contracts/legality_rules.yaml::mreg_range_overlap` 为准。
  - ISS-099：只改 id 匹配（或为 `ctrl-ret` 加专用重算），**不得**降低 audit 覆盖。
  - 期望值来源必须独立（Spec-first），不得从 LLVM/QEMU 反推。

## 验收标准

1. **ISS-025**：从 `tests/vectors/isa/` 副本删除某 `br.*` 的 taken（或 not-taken）用例 → `validate_vectors.py` **EXIT≠0** 且报该指令双路径缺失；还原 → EXIT=0。
2. **ISS-097**：在副本构造一条 `class: overlap` 且区间相交但 `expected_fault: null` 的用例 → 报错（EXIT≠0）；改回 `expected_fault: ILLI`（或不交叠）→ EXIT=0。给出真实输出。
3. **ISS-099**：修后 `009t-audit.py` 对 `ctrl-ret` 的 `ret_riii_ra` 用例**不再全 skip**（报告实际核算条数 > 0）；修正运行 `git grep "ret-riii"` → 0 命中。
4. **反例门控**：以上每条断言均须给出「注入→FAIL→还原→PASS」的真实输出；不得有恒真/`check(name, True)` 式断言。
5. `validate_vectors` 全量 EXIT=0（含 0 gaps）；`make check` EXIT=0。改动若触及 `tests/vectors/`（新增用例），须同时满足数据类任务的**独立全量重算**要求（不抽样）。

## 硬约束

- 临时目录 `/tmp/opencode/TESTCASES-028t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件，越界须披露。
- 复杂命令输出留存 `.work/log/testcases/TESTCASES-028t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/TESTCASES-028t/`，可复用检查器落 `tools/testcases/`。

## 完成区
**测试结果**：
- `python3 tools/testcases/validate_vectors.py` → **EXIT=0**（`152/152 M1 identities covered OK; 15 data files, 694 cases; data coverage gaps: 0`）。
- 一键证据 `bash .work/evidence/TESTCASES-028t/run.sh` → **EXIT=0，ALL CHECKS PASSED（18/18）**，含 ISS-025/ISS-097 注入→FAIL→还原→PASS 自检。
- `make check` → **EXIT=0**（lit 33/33、`repository checks: PASS`、`check_issues: 47 open, 33 closed`）。
- `python3 tools/testcases/009t-audit.py`（全量）→ EXIT=1，但 **mismatch 集合与改动前基线逐字节一致（18 条，均为 pre-existing，位于 ctrl-br/mem-*/reg-*）**；其中 **`ctrl-ret` mismatch = 0**。任务未要求全量 audit EXIT=0。
- `ctrl-ret`（隔离 temp 仓库，仅含 ctrl-ret.yaml）审计 → **EXIT=0**，`SBO active: 5, Recomputed: 3`（改前为 Recomputed: 0，即全 skip）。

**修改文件**：
- `tools/testcases/validate_vectors.py`（+ ISS-025 br.* 双路径结构性守卫；+ ISS-097 overlap 同组块赋值区间交集语义门控；+ 辅助 `_field_val` 与常量 `RB0_PC`/`BR_NOT_TAKEN_PC`）
- `tools/testcases/009t-audit.py`（`ret` 分支 id 判据 `ret-riii` → `ret_riii_ra`，一行 + 注释）
- （非 git，随任务保留）`.work/evidence/TESTCASES-028t/run.sh`、`.work/log/testcases/TESTCASES-028t-*.log`

**验收结果**（真实命令输出；`cmd > log 2>&1; rc=$?` 留证）：
- 验收 1（ISS-025）：副本删除 `br.eq_rrii_rd` 的 taken semantic 用例 → `validate_vectors` **EXIT=1**，报
  `BR DUAL-PATH GAP: id='br.eq_rrii_rd' missing taken active semantic case(s) ...`；还原 → **EXIT=0**。
- 验收 2（ISS-097）：副本将 `rd2rd_orri_rd` overlap 用例 `expected_fault` 由 `ILLI` 改为 `null` → **EXIT=1**，报
  `... same-bank ranges [3..4] ∩ [2..3] ≠ ∅ but expected_fault=None (must be ILLI per mreg_range_overlap)`；还原（fault=ILLI）→ **EXIT=0**；另证「同组、区间不交叠（dst[5..6]∩src[2..3]=∅）+ fault=null」→ **EXIT=0**（门控非「凡 overlap 必 ILLI」）。
- 验收 3（ISS-099）：修后 ctrl-ret `Recomputed: 3`（>0）；`git grep -n "ret-riii" -- tools/testcases/009t-audit.py | wc -l` → **0**。
- 验收 4：真实仓库 `validate_vectors` EXIT=0（0 gaps）；`make check` EXIT=0。
- 验收 5：`run.sh` 非交互、任一检查失败即 `exit 1`、逐项打印「检查名/期望/实际/退出码」、内置注入自检；输出见 `.work/log/testcases/TESTCASES-028t-evidence.log`。

**新发现/坑**：
- **ISS-099 grep 口径经用户确认**：`git grep "ret-riii"` **限定到 `tools/testcases/009t-audit.py`**（全局命中含只读 `spec/`、`.tao/archive/`、本模块生成器/schema/docs，超出「只动 validate_vectors.py + 009t-audit.py」范围）。
- ISS-025 taken/not-taken 分类仅依赖 `expected_pc`（结构字段）：`expected_pc == rb0+4` 判 not-taken，否则 taken（rb0=0xFFFF00000000，ADR-0004 D2.2 + ctrl-br.yaml 头约定）。**局限**：若未来出现「taken 且目标恰为 rb0+4（imms=1）」的用例会被误分类（当前数据无此情形）。
- ISS-097 门控不硬编码指令名，直接从 `opcodes.yaml` 记录取 dst/src（`role`）+ `immu6` 字段，按 `bank` 相等判同组 ⇒ `rd2rd`/`rb2rb`（及 scope fp `convert_ff`）自动纳入，`ra2rd/rd2ra/rd2rb/rb2rd` 与 rrrr 类（`add.uo`/`cs.*`，无 immu6）自动排除，符合 `mreg_range_overlap`。
- `009t-audit.py` **仍有 pre-existing 缺陷（本任务范围外）**：`br.*` 分支 `cond_map` 用 `insn.split("-")[0]` 匹配旧连字符名，而实际 id 为下划线名（如 `br.n_riii_rd`）⇒ riii br 全部按 not-taken 计算，产生 10 条假 mismatch；`ldm.o`/`cmp.*`/`shl.ut` 另有 8 条 pre-existing mismatch。均非本任务引入，未改。

**遗留问题**：无（本任务 3 条 ISS 均已处置并有真实证据）。上述 `009t-audit.py` 其它 pre-existing mismatch 为**范围外**，供主会话判断是否另立任务。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审方式**：自主逐行审查改动源码（`validate_vectors.py` 全部新增块、`009t-audit.py` 一行）+ 独立重跑全部验收命令 + 反例注入。

**逻辑/边界审查**：
- ISS-025：守卫遍历 `m1_keys` 的 `br.*`（10 条），以 active semantic 用例的 `expected_pc` 分类；删任一路径即 `missing` 非空 → 报错。无注释/文本依赖。现有 10 条 br.* 均 taken+not-taken 齐备 → 真实仓库 EXIT=0（无假阳性）。
- ISS-097：仅对 `class: overlap` 且 `key ∈ by_key`、word 合法 hex 生效；取 dst/src 字段（`role`）与 `immu6`，仅当二者 `bank` 相同且 ∈{rd,rb,rf} 时重算 `[start, start+cnt-1]` 交集；`cnt>0` 才判；交集判据 `not (dst_hi < src_lo or src_hi < dst_lo)` 覆盖部分/完全重合。跨组自动排除。现有 overlap 用例（rd2rd/rb2rb 相交=ILLI；rd2ra/ra2rd/rd2rb/rb2rd 跨组=null；add/cs rrrr 无 immu6）全部通过 → 无假阳性。
- `_field_val` 参数为整数字而非全局 word，避免与已有 `word` 变量混淆。

**防造假核对**：所有结论均来自真实命令输出（日志留 `.work/log/testcases/TESTCASES-028t-*`）；mismatch 集合与基线做了 `diff` 对比（IDENTICAL）；反例注入确认 `removed=1`/`patched=2`/`disjoint-patched=1`（非空注入），还原采用「从真仓库重新 cp」保证 byte 级还原。

**finding 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1（自审发现）：证据脚本 3b 用 `grep -c 'ctrl-ret'` 统计 mismatch，误把 `SKIPPED CASES` 中的 `ctrl-ret.yaml[2]/[3]` 计入（actual=3 假 FAIL） | ✅已修 | `run.sh` 3b 改为只在 `ALL MISMATCHES:` 段内 `grep -c ctrl-ret` | 重跑 run.sh → `3b full audit ctrl-ret mismatch count expected=0 actual=0`；整体 `ALL CHECKS PASSED`（EXIT=0） |
| F2（自审发现）：初次 `009t-audit.py` 注释中含字面量 `ret-riii`，致 `git grep ret-riii -- 该文件` 非 0 命中 | ✅已修 | 注释改写为「旧的连字符判据」，不留字面量 | `git grep -n "ret-riii" -- tools/testcases/009t-audit.py \| wc -l` → `0` |

**判决**：全部 finding 已修，无未修项；`validate_vectors` EXIT=0、`make check` EXIT=0、证据脚本 18/18 全绿。状态置 **待验收**。

#### 第 1 轮 reviewer 验收

**审查方式**：独立审阅证据脚本结构 → 重跑 `run.sh`（18/18 全绿）→ 独立注入反例（ISS-025 选不同注入点、ISS-097 选不同注入点）→ 独立核实真实仓库 validate_vectors/009t-audit/make check。

---

**一、证据脚本结构审阅**（`.work/evidence/TESTCASES-028t/run.sh`）

- `set -u`（未设 `set -e`），但每条关键命令的退出码均通过 `chk_rc`/`chk_eq`/`chk_contains` 显式检查，`fail()` 设置 `FAILED=1`，末尾 `exit 0`/`exit 1` 由 `$FAILED` 决定 → **不吞退出码** ✓
- ISS-025 注入：删 `br.eq_rrii_rd` taken 用例（`expected_pc=0xFFFF00000008`），验证 `removed=1`、EXIT=1、grep 包含 `BR DUAL-PATH GAP`、还原后 EXIT=0 → **可达 FAIL 路径** ✓
- ISS-097 注入：改 `rd2rd_orri_rd` ILLI→null，验证 EXIT=1、grep 包含 `must be ILLI per mreg_range_overlap`、还原后 EXIT=0；另证不交叠+null→EXIT=0 → **可达 FAIL 路径** ✓
- ISS-099：隔离 ctrl-ret 审计 EXIT=0 + Recomputed>0；全量审计 ctrl-ret mismatch=0；`git grep "ret-riii"` = 0 ✓
- 恢复采用 `cp` 从真仓库复制（非 git），工作区未提交 → 还原可信 ✓
- **结论：证据脚本合格，不代写/不改。**

---

**二、重跑 `run.sh`**（`bash .work/evidence/TESTCASES-028t/run.sh > /tmp/opencode/TESTCASES-028t-review/evidence-run.log 2>&1; echo EXIT=$?`）

真实输出（逐项）：

```
[PASS] 4a real validate_vectors EXIT | expected=0 actual=0 rc=0
[PASS] 4a real validate_vectors 0 gaps | expected=contains:[data coverage gaps: 0] actual=found rc=-
[PASS] 1 baseline (copy) validate EXIT | expected=0 actual=0 rc=0
[PASS] 1 injection applied (removed 1 taken case) | expected=0 actual=0 rc=0
[PASS] 1 inject -> validate FAIL(EXIT!=0) | expected=!=0 actual=1 rc=1
[PASS] 1 inject -> reports missing taken | expected=contains:[BR DUAL-PATH GAP: id='br.eq_rrii_rd' missing taken] actual=found rc=-
[PASS] 1 restore -> validate PASS(EXIT=0) | expected=0 actual=0 rc=0
[PASS] 2 injection applied (overlap ILLI->null) | expected=0 actual=0 rc=0
[PASS] 2 inject -> validate FAIL(EXIT!=0) | expected=!=0 actual=1 rc=1
[PASS] 2 inject -> reports intersection/mreg_range_overlap | expected=contains:[must be ILLI per mreg_range_overlap] actual=found rc=-
[PASS] 2 restore(fault=ILLI) -> validate PASS | expected=0 actual=0 rc=0
[PASS] 2b disjoint injection applied | expected=0 actual=0 rc=0
[PASS] 2b disjoint+null -> validate PASS | expected=0 actual=0 rc=0
[PASS] 3a isolated ctrl-ret audit EXIT | expected=0 actual=0 rc=0
[PASS] 3a ctrl-ret recomputed > 0 | expected=yes actual=yes rc=-
[PASS] 3b full audit ctrl-ret mismatch count | expected=0 actual=0 rc=-
[PASS] 3c git grep ret-riii in 009t-audit.py | expected=0 actual=0 rc=-
[PASS] 4b make check EXIT | expected=0 actual=0 rc=0
RESULT: ALL CHECKS PASSED
```

**EXIT=0，18/18 全绿** ✓

---

**三、独立注入反例**（与 engineer 不同的注入点）

**ISS-025**：删 `br.n_riii_rd` 的 not-taken 用例（`expected_pc=0xFFFF00000004`）
- 注入：`removed=1` ✓
- 运行：`EXIT=1`，输出 `BR DUAL-PATH GAP: id='br.n_riii_rd' missing not-taken active semantic case(s) ...` ✓
- 还原：`cp` 从真仓库 → `EXIT=0` ✓

**ISS-097**：改 `rb2rb_orri_rb` 的 ILLI→null（2 条）
- 注入：`patched=2` ✓
- 运行：`EXIT=1`，输出两条：
  - `case[38]: overlap rb2rb_orri_rb same-bank ranges [3..4] ∩ [2..3] ≠ ∅ but expected_fault=None (must be ILLI per mreg_range_overlap)`
  - `case[39]: overlap rb2rb_orri_rb same-bank ranges [3..3] ∩ [3..3] ≠ ∅ but expected_fault=None (must be ILLI per mreg_range_overlap)`
  ✓
- 还原：`cp` 从真仓库 → `EXIT=0` ✓

注入后 `git diff --name-only` 为空（未在真仓库改动）；临时目录 `/tmp/opencode/TESTCASES-028t-review/` 内操作，还原干净。

---

**四、独立复核真实仓库**

| 检查项 | 命令 | 实际输出 | 退出码 |
|--------|------|---------|--------|
| validate_vectors 全量 | `python3 tools/testcases/validate_vectors.py` | `152/152 M1 identities covered OK; 15 data files, 694 cases; data coverage gaps: 0` | **EXIT=0** ✓ |
| make check | `make check` | `Passed: 33 (100.00%)`、`repository checks: PASS`、`check_issues: 47 open, 33 closed` | **EXIT=0** ✓ |
| git grep ret-riii | `git grep -n "ret-riii" -- tools/testcases/009t-audit.py \| wc -l` | `0` | **0 命中** ✓ |
| 009t-audit 全量 | `python3 tools/testcases/009t-audit.py` | `EXIT=1`，18 条 mismatch（见下） | **EXIT=1** |
| ctrl-ret 隔离审计 | 工程师日志 `.work/log/testcases/TESTCASES-028t-audit-ctrlret.log` | `SBO active: 5, Recomputed: 3`、`Mismatches: 0` | **EXIT=0** ✓ |

---

**五、pre-existing mismatch 独立核实**

009t-audit EXIT=1 的 18 条 mismatch 分布：

| 来源 | 数量 | 类别 |
|------|------|------|
| ctrl-br.yaml | 10 | expected_pc mismatch（`cond_map` 用旧连字符名匹配，pre-existing 已知缺陷） |
| mem-ra.yaml | 2 | ldm.o missing rd1 |
| mem-rb.yaml | 2 | ldm.o missing rd1 |
| reg-compare.yaml | 3 | cmp.ut/cmp.uw/cmp.ub rd1 mismatch |
| reg-shift-extend.yaml | 1 | shl.ut rd1 mismatch |

**判定**：
- **ctrl-ret mismatch = 0** ✓（18 条全在 ctrl-br/mem-*/reg-*，与基线逐字节一致）
- 本次改动仅涉及 `validate_vectors.py`（加守卫）和 `009t-audit.py`（改一行 id 匹配），不会引入上述 mismatch → **确认为 pre-existing，非本次引入** ✓
- 工程师完成区称「18 条 pre-existing，ctrl-ret mismatch = 0」与独立核实一致 ✓

---

**六、门控「结构性/可失败」复核**

**ISS-025**：守卫分类仅依赖 `expected_pc`（结构字段）：`expected_pc == BR_NOT_TAKEN_PC(0xFFFF00000004)` → not-taken，否则 → taken。不读 notes/文本/注释。验证：真实仓库 10 条 br.* 均 taken+not-taken 齐备 → EXIT=0（无假阳性）；删任一条 → EXIT=1（假阳性=0，可失败性已证）✓

**ISS-097**：门控条件——`class: overlap` + `key ∈ by_key` + 合法 hex word + 同 bank（`dst.bank == src.bank ∈ {rd,rb,rf}`）+ 有 `immu6` 字段。机械验证：
- 同 bank 指令：`rd2rd_orri_rd`(dst=rd,src=rd)、`rb2rb_orri_rb`(dst=rb,src=rb) → **纳入** ✓
- 跨组指令：`rd2ra_orri_ra`(dst=ra,src=rd)、`ra2rd_orri_ra`(dst=rd,src=ra)、`rd2rb_orri_rb`(dst=rb,src=rd) → **自动排除**（bank 不等）✓
- rrrr 类（`add.so`/`cs.*`）→ **无 immu6 字段，自动排除** ✓
- 现有 overlap 用例全部通过 → **无假阳性** ✓
- 有交集且 fault=null → **报错**（已注入验证）✓
- 不交叠且 fault=null → **不报错**（证据脚本 2b 已证）✓

---

**判决：Accepted**

验收命令块在 reviewer 独立重跑下全部通过（18/18 EXIT=0）；独立注入反例（ISS-025 删 `br.n_riii_rd` not-taken、ISS-097 改 `rb2rb_orri_rb` ILLI→null）均正确 FAIL，还原后回绿；真实仓库 validate_vectors EXIT=0（152/152、694 cases、0 gaps）、make check EXIT=0、git grep ret-riii=0、ctrl-ret mismatch=0；pre-existing mismatch 18 条经独立核实确认非本次引入。任务状态置 **已验证**。
