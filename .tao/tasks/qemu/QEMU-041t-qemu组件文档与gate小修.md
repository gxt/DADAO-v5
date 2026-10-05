# QEMU-041t: QEMU 组件文档与 gate 小修（semantics gate 目录前置校验、changelog 补记）

**模块**：qemu
**项目里程碑**：M3
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地

## 目标与 resolved_by

合并 2 条无依赖的 qemu 文档/gate issue（无组件重建）。完成后应关闭：

| ISS | 改动点 |
| --- | --- |
| ISS-089 | `check-qemu-semantics` 的 gate 目录为瞬态，`ln -sf` 静默失败致假失败 |
| ISS-090 | `components/qemu/changelog.md` 缺任务级记录（自 2026-09-23 起未按任务追加） |

`resolved_by`：本任务 `QEMU-041t`。

## 接口规范

- **输入**（已核实）：
  - `Makefile:337-351`（`check-qemu-semantics`）：`ln -sf ... 2>/dev/null` 掩盖失败；gate 目录 `$(TEST_ARTIFACTS_DIR)/harness/gate` 为瞬态，失败时 `rm -rf` 后无显式诊断。
  - `components/qemu/changelog.md`：末条为 `QEMU-038t`（2026-10-04）；缺 `QEMU-040t`（`sub.o_orrr_dbb` trans，`.tao/tasks/qemu/QEMU-040t-sub-rb-rb-trans.md`）等 2026-10-04 之后的条目。规范依据 `spec/Process-01 §10`（按任务一条）。
- **输出**：`Makefile`（gate 前置校验）+ `components/qemu/changelog.md`（补记）。
- **约束**：
  - ISS-089：在 `check-qemu-semantics` 中**显式校验** gate 目录存在与两个 symlink 指向正确（`ln -sf` 去掉 `2>/dev/null` 或改为先 `test -e` 再建）；symlink 失败须**非零退出并打印明确原因**，不得静默。
  - ISS-090：补记须**逐任务一条**、日期/任务号/变更摘要真实；只补**尚未记录**的 qemu 任务（先 `git log --grep QEMU-` 对照现有条目，避免重复）。历史条目不改写。

## 验收标准

1. **ISS-089**：在 gate 目录/symlink 被人为破坏（如预先占用同名路径）时，`make check-qemu-semantics` **非零退出**且打印明确诊断（非静默）；正常时 EXIT=0 并保留原日志行为（`.work/log/qemu/check-qemu-semantics.log`）。给出注入→FAIL→还原→PASS 的真实输出。
2. **ISS-090**：`git log --oneline --grep 'QEMU-0' -- components/qemu/patches`（或按任务提交）列出的 2026-10-04 后 qemu 任务，在 `changelog.md` 中**逐条有记录**；给出「任务清单 ↔ changelog 行」逐条对照。当前至少需补 `QEMU-040t`。
3. **反例门控**：删除 changelog 中刚补的 `QEMU-040t` 行（临时副本）⇒ 验收 2 的对照 FAIL；还原。gate 目录注入见验收 1。
4. `make check-qemu-semantics` 正常路径 EXIT=0；`Makefile` 改动后 `make check` 的相关门控不回归（文档改动豁免）。

## 硬约束

- 临时目录 `/tmp/opencode/QEMU-041t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件，越界须披露。
- 复杂命令输出留存 `.work/log/qemu/QEMU-041t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/QEMU-041t/`。

## 完成区

> 说明：本任务实现（Makefile ISS-089 前置校验 + changelog ISS-090 补记 QEMU-040t 行 + 证据脚本）已由前次执行落盘，本次为收尾复核与验证，未重做/覆盖已有改动。

**测试结果**：通过。一键证据脚本 EXIT=0；`make check-qemu-semantics` EXIT=0；`make check` EXIT=0。

**修改文件**（工作树 `git status --short` 仅这两项）：
- `Makefile`（`check-qemu-semantics` gate 目录/symlink 前置校验，ISS-089）
- `components/qemu/changelog.md`（补记 `QEMU-040t` 行，ISS-090）
- 非入库产物：`.work/evidence/QEMU-041t/run.sh`（证据脚本）、`.work/log/qemu/QEMU-041t-*.log`（日志）——`.work/` 已被 gitignore。

**验收结果**：

1) 一键证据脚本（含 ISS-089/ISS-090 两项反例注入自检）：
```
$ .work/evidence/QEMU-041t/run.sh > .work/log/qemu/QEMU-041t-evidence.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
== QEMU-041t evidence ==
PASS [0] changelog exists
PASS [0] Makefile: explicit gate setup, no swallowed ln errors
PASS [0] ISS-089 normal: make check-qemu-semantics EXIT=0
PASS [0] ISS-089 normal: log /mnt/tao/DADAO-v5/.work/log/qemu/check-qemu-semantics.log written (0 failed)
PASS [2] ISS-089 inject(occupied symlink name): non-zero exit
PASS [0] ISS-089 inject: explicit diagnostic printed
check-qemu-semantics: ERROR: /mnt/tao/DADAO-v5/.dadao/tests/harness/gate/reg-shift-extend.yaml is not a symlink (stale/occupied path?)
PASS [0] ISS-089 restore: EXIT=0 (green)
PASS [0] ISS-090 task list: QEMU-038t QEMU-040t
PASS [0] ISS-090 baseline: all post-2026-10-04 qemu tasks recorded
PASS [0] ISS-090: all HEAD changelog rows preserved verbatim (no rewrite)
  missing: QEMU-040t
PASS [1] ISS-090 inject: stripped QEMU-040t -> check FAIL (expect FAIL)
PASS [0] gate dir cleaned (transient)

QEMU-041t evidence: PASS
```
反例注入逐项对应：ISS-089（用目录占用 gate 内 `reg-shift-extend.yaml` 同名路径）⇒ `make` 非零退出（rc=2）并打印 `is not a symlink` 诊断；随后 `rm -rf` 还原 ⇒ 再跑 EXIT=0。ISS-090（临时副本 `grep -v` 删 `QEMU-040t` 行）⇒ 同一对照检查返回 FAIL（`missing: QEMU-040t`）；原文件未被改动（注入在临时副本）。

2) 独立跑 gate（非证据脚本内）：
```
$ make check-qemu-semantics > .work/log/qemu/QEMU-041t-check-qemu-semantics.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
... Results: 149 total, 149 passed, 0 failed, 0 deferred, 0 errors
check-qemu-semantics: PASS
```
正常路径日志行为保留：`.work/log/qemu/check-qemu-semantics.log` 正常写入（末行 `0 failed`）。

3) 全量检查不回归（Makefile 属门控范围）：
```
$ make check > .work/log/qemu/QEMU-041t-make-check.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
... Total Discovered Tests: 33 / Passed: 33 (100.00%)
check_issues: 69 open, 11 closed (0 blocking M1-gate: 0)
repository checks: PASS
```

4) ISS-090 验收 2 对照表（`git log --grep 'QEMU-0' -- components/qemu/patches`，取 2026-10-04 后）：
| 任务 | changelog 行 |
|---|---|
| `QEMU-038t` | RECORDED（2026-10-04 行） |
| `QEMU-040t` | RECORDED（本次补记 2026-10-05 行） |
无 MISSING。历史行未被改写（证据脚本已断言 HEAD 版 changelog 每行逐字保留）。

5) `QEMU-040t` 行内容真实性抽查（对照 `components/qemu/patches/`）：
- `insn.decode.patch`: `+sub_o_orrr_dbb  01000000110011..................  @misc`（14 位 = op `0x40` + ha `0x33` ⇒ value `0x40CC0000` / mask `0xFFFC0000`，已逐位核算）。
- `trans_arith.c.inc.patch`: `trans_sub_o_orrr_dbb`：`a->hb == 0` ⇒ `gen_exception_illegal`；否则 `load_rb(a->hc) − load_rb(a->hd)` 全 64 位补码 → `store_rd(a->hb)`。
- 计数：`components/qemu/patches` 文件数 = 32；全仓 patch 文件数在 `QEMU-040t` 提交 `0dcaf1f` = 69（HEAD 为 77，系其后 LLVM 任务新增，行内数字为当时记录，准确）。

**新发现/坑**：
- ISS-090 范围不一致：issue 标题/备注为「自 2026-09-23 起未按任务追加」（备注点名 `QEMU-032t/033t`），但本任务验收 2 明确限定「2026-10-04 后」。二者口径不同，见「遗留问题」。
- `check-qemu-semantics` 的 gate 目录为瞬态；新校验在**失败分支**不清理 gate 目录（只在测试 rc≠0 与成功分支 `rm -rf`）。本次注入自检显示失败会保留现场，符合「保留失败现场」的可恢复原则，且再次运行会重建/复检，无持久副作用。

**遗留问题**：
- ISS-090 更早任务仍未补记：`git log --grep 'QEMU-0' -- components/qemu/patches` 中 2026-09-23 之后、`QEMU-034t` 之前修改补丁的任务（`QEMU-025t`…`QEMU-033t`，含 issue 备注点名的 `QEMU-032t`/`QEMU-033t`）在 `changelog.md` 中无行。本任务验收口径为「2026-10-04 后」，故**未越界补记**。若以「关闭 ISS-090」为准，需架构师裁定是否追加该批历史补记（属独立范围，建议另立任务或就地裁定）。

## 审阅记录

#### 第 1 轮 engineer 自审
自审对象：`Makefile`（`check-qemu-semantics`）、`components/qemu/changelog.md`、`.work/evidence/QEMU-041t/run.sh`。逐行复核 + 真实命令复验。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 ISS-089 四层校验（log/gate 目录创建失败、源向量缺失、`ln -sf` 失败、非 symlink、`readlink -f` 指向不一致）均以 `|| { echo ...; exit 1; }` 非零退出 | ✅ 通过（既有实现已完整，无需改） | — | 证据脚本 `PASS [2] ISS-089 inject ... non-zero exit` + `is not a symlink` 诊断；`EXIT=0` 正常路径 |
| F2 失败分支不清理瞬态 gate 目录 | ❌ 不修 | — | 验收仅要求非零退出+明确诊断；保留现场符合「可恢复/保留失败现场」原则；重跑会重建并经 `mkdir -p`/`ln -sf`/`-L` 复检，无持久副作用（证据脚本末 `gate dir cleaned` 通过） |
| F3 `ln -sf` 的 `2>/dev/null` 已移除 | ✅ 通过 | — | `grep -n '2>/dev/null' Makefile` ⇒ 无匹配；证据脚本 `no swallowed ln errors` PASS |
| F4 正常路径日志行为保留 | ✅ 通过 | — | 证据脚本 `log ... written (0 failed)` PASS |
| F5 evidence 脚本每条断言 FAIL 路径可达、含两项注入且 ISS-089 有「注入→FAIL→还原→回绿」 | ✅ 通过 | — | 全量输出见验收结果 1；抽查无「两支写同一结果/恒真」结构 |
| F6 `QEMU-040t` changelog 行摘要/日期/编码/计数真实 | ✅ 通过 | — | 对照补丁核验（验收结果 5）；`0dcaf1f` 全仓 patch 数 = 69 |
| F7 ISS-090 更早任务缺行（口径冲突） | ⏸ 延后 | — | 超出本任务验收口径（post-2026-10-04），已在「遗留问题」披露，交架构师/协调者裁定 |

判决：本任务验收范围内 finding 全部通过或已合理处置；状态置 **待验收**。

#### 第 1 轮 reviewer 验收

**审查范围**：`Makefile`（ISS-089）、`components/qemu/changelog.md`（ISS-090）、`.work/evidence/QEMU-041t/run.sh`（证据脚本）。纯文档/Makefile 改动，无组件重建。

**1. 证据脚本审阅**（不代写，逐条核）

| 断言 | FAIL 路径 | 结论 |
|---|---|---|
| changelog exists | `fail 1` if missing | ✅ |
| Makefile: QEMU_SEM_VEC_DIR present + no `2>/dev/null` | `fail 1` | ✅（`grep` 确认 Makefile 无 `2>/dev/null`） |
| ISS-089 normal EXIT=0 | `fail` if rc≠0 | ✅ |
| ISS-089 normal log "0 failed" | `fail 1` | ✅ |
| ISS-089 inject (directory occupies symlink) → non-zero exit | `fail` if rc=0 | ✅（`mkdir -p` 占用 → `ln -sf` 在目录内创建嵌套 symlink → `[ -L ]` 失败 → exit 1） |
| ISS-089 inject: diagnostic "is not a symlink" | `fail 1` | ✅ |
| ISS-089 restore → EXIT=0 | `fail` if rc≠0 | ✅ |
| ISS-090 task list non-empty | `fail 1` | ✅ |
| ISS-090 baseline: all post-10-04 tasks recorded | `fail 1` | ✅ |
| ISS-090 HEAD rows preserved verbatim | `fail 1` | ✅ |
| ISS-090 inject: strip QEMU-040t → check FAIL | `fail 0` if still passes (injection ineffective) | ✅（注入无效时 `fail 0`，检测到时 `pass 1`——脚本打印 "PASS [1]" 即表示检测成功） |
| gate dir cleaned | `fail 1` | ✅ |
| Final exit | `exit "$FAILED"` | ✅（非 `tee`，非恒真） |

脚本结构合格：非交互、13 条断言均有可达 FAIL 路径、两项注入（ISS-089 目录占用 + ISS-090 删行）、结尾 `exit "$FAILED"` 不吞退出码。通过。

**2. 重跑证据脚本**

```
$ bash .work/evidence/QEMU-041t/run.sh > /tmp/.../evidence-run.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
== QEMU-041t evidence ==
PASS [0] changelog exists
PASS [0] Makefile: explicit gate setup, no swallowed ln errors
PASS [0] ISS-089 normal: make check-qemu-semantics EXIT=0
PASS [0] ISS-089 normal: log .../check-qemu-semantics.log written (0 failed)
PASS [2] ISS-089 inject(occupied symlink name): non-zero exit
PASS [0] ISS-089 inject: explicit diagnostic printed
check-qemu-semantics: ERROR: .../gate/reg-shift-extend.yaml is not a symlink (stale/occupied path?)
PASS [0] ISS-089 restore: EXIT=0 (green)
PASS [0] ISS-090 task list: QEMU-038t QEMU-040t
PASS [0] ISS-090 baseline: all post-2026-10-04 qemu tasks recorded
PASS [0] ISS-090: all HEAD changelog rows preserved verbatim (no rewrite)
  missing: QEMU-040t
PASS [1] ISS-090 inject: stripped QEMU-040t -> check FAIL (expect FAIL)
PASS [0] gate dir cleaned (transient)
QEMU-041t evidence: PASS
```

13/13 PASS，EXIT=0。与完成区逐条一致。

**3. 独立注入（与 engineer 不同）**

| 注入点 | 操作 | 预期 | 实际 | 还原 |
|---|---|---|---|---|
| ISS-090 changelog | 直接删 `components/qemu/changelog.md` 中 `QEMU-040t` 行（非临时副本，改真实文件） | task list 对照检测到 `MISSING: QEMU-040t` | `MISSING: QEMU-040t` ✅ | `cp backup changelog.md` → grep 确认 QEMU-040t 恢复 → `git diff --name-only` 不变（注入前后相同 3 文件） |

注入→FAIL→还原完整。`git diff --name-only` 还原前后一致（`Makefile`、`changelog.md`、任务书）。

**4. 独立复核**

| 命令 | 期望 | 实际 | 日志 |
|---|---|---|---|
| `make check-qemu-semantics` | EXIT=0, 149/149 | EXIT=0, 149 total/149 passed/0 failed | `.work/log/qemu/QEMU-041t-reviewer-check-qemu-semantics.log` |
| `make check` | EXIT=0, 33/33 | EXIT=0, 33/33 (100.00%) + repository checks: PASS | `.work/log/qemu/QEMU-041t-reviewer-make-check.log` |
| `git log --grep 'QEMU-0'` post-10-04 | QEMU-038t + QEMU-040t 均在 changelog | QEMU-038t: IN, QEMU-040t: IN ✅ | — |

**5. 越界核验**

`git diff --name-only` 仅 3 文件：`Makefile`、`components/qemu/changelog.md`、任务书。全部在本任务范围内。无越界。

**6. ISS-090 口径判定**（关键）

| 口径 | 来源 | 范围 | 本任务是否覆盖 |
|---|---|---|---|
| 验收 2 | 任务书明文 | post-2026-10-04（QEMU-038t, QEMU-040t） | ✅ 全覆盖 |
| ISS-090 原文 | issue 标题/备注 | 自 2026-09-23 起（含 QEMU-025t~033t 等 9 条） | ❌ 未覆盖 |

**事实**：
- `git show HEAD:components/qemu/changelog.md` 已有 QEMU-034t~038t（5 条，非本任务添加）。
- 工作树新增 QEMU-040t（1 条，本任务添加）。
- QEMU-025t~033t（9 条）在 changelog 中无行，不在验收 2 范围内。

**判定**：
1. **本任务验收范围内 → Accepted**：验收 2 明确限定 post-2026-10-04，QEMU-038t + QEMU-040t 均已记录，无遗漏。
2. **ISS-090 不能完整关闭**：issue 原文要求「自 2026-09-23 起未按任务追加」，QEMU-025t~033t（9 条）仍缺失。若以 ISS-090 原文为准，仅部分解决。
3. **建议另立任务**：补记 QEMU-025t~033t（2026-09-23 ~ 2026-10-03）的 9 条历史条目，作为 ISS-090 的完整关闭条件。此为独立范围，不阻塞本任务。

**判决：Accepted**

本任务（ISS-089 Makefile gate 前置校验 + ISS-090 post-10-04 changelog 补记）验收范围内全部通过。ISS-090 历史缺口（025t~033t）需另立任务处理，不阻塞本任务验证。
