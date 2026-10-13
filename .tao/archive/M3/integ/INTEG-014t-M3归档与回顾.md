# INTEG-014t: M3 归档与回顾

**模块**：integ
**项目里程碑**：M3
**依赖**：`milestones.md` M3 达成（2026-10-05）、`INFRA-042t`（归档前置台账梳理，已完成）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`spec/Process-04-里程碑归档规范.md`（§3 判据 / §4 落点 / §5 README 模板 / §6 原台账处理 / §7 验收纪律）；`milestones.md`（M3 = ✅ 达成，达成日 **2026-10-05**）；先例 `.tao/archive/M1/`、`.tao/archive/M2/`（`INTEG-010t`）。
- **输出**（M3 归档）：
  - `.tao/archive/M3/<模块>/…`：`项目里程碑` 字段 = `M3` 且终态（`已验证`/`里程碑`）的任务书，**用 `git mv` 移动**（保留 rename 历史）。
  - `.tao/archive/M3/README.md`（按 §5 模板；含任务清单/`changelog` 摘录/`MEMORY` 摘录/指针）。
  - `.tao/archive/M3/m3-retrospective.md`（**M3 回顾**：目标/门槛/关键决策 `ADR-0018`+`adr-0012 D9`/落地链/坑与教训/遗留 `M4`）。
  - `.tao/archive/M3/issues-closed.md`（§3.4/§6：`resolved_by` 提交日 ≤ **2026-10-05** 的 `closed` 项快照）。
  - `changelog.md`：移除归档条目（≤ 2026-10-05，**行首正则分组**，多行 cell 勿切）+ 在**表头之上**加归档指针（§6/§8.5）。
  - `MEMORY.md`：移除归档行（纯 M3 行）+ 在「当前进度」表**内**加归档指针（合法表行）。
  - `issues.yaml`：移除已归档 `closed` 项 + 文件头注释加指针。
  - `milestones.md`：里程碑表下方加归档注。
- **判据（§3，机械可判）**：
  1. 任务书 `**项目里程碑**` **恰好 = M3** 且终态；**不归档**下一里程碑/过渡期任务。
  2. `changelog.md` 行首 `| YYYY-MM-DD |` **日期 ≤ 2026-10-05** 的表行。
  3. `MEMORY.md` **纯 M3** 行（混合行只归档纯 M3 部分，必要时人工拆分，不机械切行）。
  4. `issues.yaml` `closed` 项：`resolved_by` 对应任务**提交日 ≤ 2026-10-05**（`git log --grep <taskID>` 实测，**不得凭印象**）。
- **纪律（§7/§8）**：
  - 提交**只 `git add` 归档相关文件**；并行任务书/补丁一律不动；**不得**与其它任务同树并发。
  - 生成/改动的 `README.md`/`changelog.md`/`MEMORY.md`：**无表内空行、无连续空行**；blockquote **不得**插在 `|---|` 与数据行之间；文件尾无空行。
  - 指向 `changelog.md`/`MEMORY.md` 中 M3 条目的历史引用**不回溯更新**（§5 指针说明）。
  - **提交必须经用户确认**（AGENTS）。

## 验收标准

1. `.tao/archive/M3/` 含 `README.md` + `m3-retrospective.md` + `issues-closed.md` + 各模块子目录（任务书数 = `项目里程碑=M3` 且终态者，**逐条登录**）；`git status` 显示 **`R`（rename）** 而非 `A`+`D`。
2. `README.md` 按 §5 模板：任务清单/`changelog` 摘录（C 条）/`MEMORY` 摘录（M 行）/指针 齐全；`issues-closed.md` 条数与判据一致（逐条可核）。
3. `changelog.md`/`MEMORY.md`/`issues.yaml`/`milestones.md` 按 §6 处理（移除 + 指针，无断表/空行）。
4. `make check` **EXIT=0**；`check_issues.py` EXIT=0；无仓库残留。
5. 生成物 `README.md` 无表断行/连续空行（§7）；提交**待用户确认**。
6. 一键证据 `.work/evidence/INTEG-014t/run.sh`（对可机械检查者含反例注入）。

## 完成区

**测试结果**：`make check` **EXIT=0**（`repository checks: PASS`；lit 34/34）；`tools/infra/check_issues.py` **EXIT=0**（`35 open, 0 closed`）；一键证据 `.work/evidence/INTEG-014t/run.sh` 全量 **EXIT=0**、`--inject` **EXIT=0**（3 注入 → 预期 FAIL → 还原 sha256 一致 → 回绿）；`--no-make` 结构检查 84/84 PASS。

**修改文件**（只动归档相关；**未提交**）：
- **`git mv`（39，`git status` 显示 `R`/`RM`）**：`.tao/tasks/{infra,spec,testcases,llvm,qemu,integ}/*.md`（`项目里程碑=M3` 且终态）→ `.tao/archive/M3/<module>/`；计数 **infra 8 / spec 7 / testcases 3 / llvm 17 / qemu 2 / integ 2 = 39**。
- **新建**：`.tao/archive/M3/README.md`（§5 模板；判据 **39/34/1/56**）、`.tao/archive/M3/m3-retrospective.md`、`.tao/archive/M3/issues-closed.md`（56 条）。
- **改**：`.tao/knowledge/changelog.md`（移除 34 条 + 表头之上加 M3 指针）、`.tao/knowledge/MEMORY.md`（移除 1 行 `M3 进行中` + 表内加 M3 归档指针；`M1/M2`→`M1/M2/M3`）、`.tao/knowledge/issues.yaml`（移除 56 条 closed + 头部加指针）、`.tao/knowledge/milestones.md`（表下加 M3 归档注 + 订正「归档前置待执行」）。
- **状态字段改**：`SPEC-096k-M3启动与分解.md` `待开始`→`已验证`（**用户裁定**，随 M3 归档；git 记为 `RM`）。
- **交付（.work，不入库）**：`.work/evidence/INTEG-014t/run.sh`；日志 `.work/log/integ/INTEG-014t-*.log`、`.work/log/m3-closure/`（既有）。

**验收结果**（真实输出，逐条对齐；日志见 `.work/log/integ/INTEG-014t-*.log`）：
```
$ make check > .work/log/integ/INTEG-014t-make-check.log 2>&1; echo EXIT=$?
EXIT=0        # 末行 repository checks: PASS；lit Total 34 / Passed 34；check_issues 35 open, 0 closed
$ make check-patch-tree
check-patch-tree: 2 component(s), 80 patches OK
$ git status --short | awk '{print $1}' | sort | uniq -c
      4 ??
      4 M
     38 R
      1 RM
$ python3 tools/infra/check_issues.py; echo EXIT=$?
check_issues: 35 open, 0 closed (0 blocking M1-gate: 0)
EXIT=0
$ bash .work/evidence/INTEG-014t/run.sh; echo EXIT=$?            # full
STRUCTURAL CHECKS: ALL PASS ; make check EXIT=0 ; check_issues EXIT=0 ; EVIDENCE: PASS (mode=full)
EXIT=0
$ bash .work/evidence/INTEG-014t/run.sh --inject; echo EXIT=$?   # 反例注入自检
FAIL: changelog has 0 dated entries got 1   → PASS: 注入后如预期 FAIL
FAIL: MEMORY has M3 archive row             → PASS: 注入后如预期 FAIL
FAIL: issues-closed rows == 56 got 57       → PASS: 注入后如预期 FAIL
PASS: 还原 sha256 一致（changelog/MEMORY/issues-closed）
PASS: 还原后结构检查全绿
EVIDENCE: PASS (mode=--inject)
EXIT=0
$ make check-no-residue; echo EXIT=$?
check-no-residue: PASS
EXIT=0
```

**用户裁定（原话，2026-10-05）**：问题 =「M3 归档任务书数量对不上：`项目里程碑：M3` 共 40 个，终态 38 个；非终态 2 个 = `SPEC-096k`（待开始）、`INTEG-014t`（本任务，待开始）；派发提示写『39 个』。请问 `SPEC-096k` 如何处理？」——**用户原话**：**「归档 SPEC-096k，任务数记 39」**（选项含「将 `SPEC-096k` 状态置 `已验证`」，用户选定该选项）。据此：`SPEC-096k` 状态由 `待开始` 置 `已验证` 并随 M3 归档，M3 任务数 = **39**。

**新发现/坑**：
1. **派发「39」与实测终态「38」差 1**：差异项 = `SPEC-096k`（M3 `k` 规划任务，状态 `待开始`；M1/M2 的 `k` 均为 `已验证`）。已由用户裁定归档并置 `已验证`（见上）。
2. **`changelog.md` 归档后为空表（表头保留）**：34 条全部 ≤ 2026-10-05，移除后无数据行；本任务自身条目由 `/complete` 追加（与 M2 归档时 `INTEG-010t` 条目同机制）。**非断表**（表头+分隔完整，仅暂无数据行；证据脚本 `README tables not broken` 覆盖 README，changelog 空表不触发）。
3. **`INTEG-010t`（2026-10-04，M2 归档）条目按 §3.2 日期判据纳入 M3 快照**：该条于 M2 快照后写入、M2 未收，`≤ 2026-10-05` 故归 M3（README §2 已注明）。
4. **`MEMORY.md` 纯 M3 行仅 1 行**（`M3 进行中`），非 M2 的 45 行量级——M3 状态集中在单行内更新。
5. **台账基数**：M3 达成时 `41 open/52 closed`（`.work/log/m3-closure/check.log`）；经 `INFRA-041t`/`INFRA-042t` 后归档前 = **35 open/56 closed**；归档后 = **35 open/0 closed**。`resolved_by` 提交日实测（`git log --grep`，39 个去重任务全部 ≤ 2026-10-05，0 违规）见 `.work/log/integ/INTEG-014t-resolved-by-dates.log`。
6. **`git mv` 全部为 `R`/`RM`**（无 `A`+`D`）；evidence 脚本「无 M3 残留」检查须只查**终态**任务书，否则会误报归档任务自身（已修）。

**遗留问题**：
- **提交待用户确认**（AGENTS：归档提交须经用户确认；本任务只落盘、未 commit）。
- `/complete` 收尾时须：① 置本任务书 `已验证`；② 向 `changelog.md` 追加 `INTEG-014t` 条目（补足空表首行）。
- 归档保留 `SPEC-096k` 状态由 `待开始`→`已验证`（用户裁定）；`git status` 记 `RM`（改名+改状态），非纯 `R`。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：39 个改名 + 3 新建 + 4 台账改动 + 1 状态字段 + 1 evidence 脚本；逐项核对真实输出与判据。

**判决**：所有 finding 均已处置，无未修项；证据脚本 `--inject` 具备可达 FAIL 路径与可还原性；完成区结论与真实输出逐条对齐。任务状态置 **待验收**。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 派发「39」vs 实测终态 38（`SPEC-096k` 非终态） | ✅已修（**用户裁定**） | `SPEC-096k` 状态 `待开始`→`已验证`，随 M3 归档；README 注记 | `git status` 该文件 `RM`；`archive total == 39` PASS |
| F2 evidence 脚本 `--inject` 段 `CHANGELOG`/`MEMORY`/`ISSCL` 作 bash 变量未定义（`set -u` 报错） | ✅已修 | 顶部定义 `CHANGELOG_PATH`/`MEMORY_PATH`/`ISSCL_PATH`，注入段改用 | `--inject` EXIT=0（此前 `unbound variable` EXIT=1） |
| F3 evidence 脚本「无 M3 残留」把归档任务 `INTEG-014t` 自身误报为残留 | ✅已修 | 判据加「**终态**（已验证/里程碑）」限定 | `--no-make` 84/84 PASS（此前 1 FAIL） |
| F4 `--inject` 中断可能残留注入态 | ✅已修 | `trap cleanup` 用备份还原 ledger + 清 TMP | 注入中途风险解除；还原 sha256 一致 |
| F5 回顾 §8.2 误引 `ISS-140` 为「间接调用」（实为 README 补丁数小修，已 closed） | ✅已修 | 改为 `ISS-005`/`ISS-142`/`ISS-147`/`ISS-110`/`ISS-074`（均 open） | 逐一比对 `issues.yaml`（backup）状态 |
| F6 回顾 §1.3 台账基数写 `41 open/52 closed`（系 M3 达成时快照） | ✅已修 | 改为归档前 `35 open/56 closed`→归档后 `35 open/0 closed` | 复算 `issues.yaml`（backup）= 35 open/56 closed |
| F7 `milestones.md` M3 达成注「归档前置待执行」在归档后失真 | ✅已修 | 改为「由 `INFRA-042t` 执行（已验证）」 | `grep 待执行` 无残留 |
| F8 `MEMORY.md`「重要决策：项目里程碑：M1/M2」未含 M3 | ✅已修（一致性） | `M1/M2`→`M1/M2/M3` | `grep '项目里程碑：M1/M2/M3'` 命中 |
| F9 changelog 归档后空表 | ⏸延后（非缺陷） | 保留表头；`/complete` 追加自身条目 | README §2 已注明；`make check` 不受影响 |
| F10 表格纪律（README/台账无连续空行、README 无断表、文件尾单换行） | ❌不修（已合规） | 无需改 | 证据脚本 7 文件 `no consecutive blanks` + `README tables not broken` + `tail single newline` 全 PASS |

#### 第 1 轮 reviewer 验收

**审阅范围**：39 rename + 3 新建 + 4 台账改动 + 1 状态字段 + 1 evidence 脚本；§3–§7 全量核验。

**判决**：**Accepted**

---

**1. 证据脚本审查**

逐条审 `.work/evidence/INTEG-014t/run.sh`：
- 84 条 `ck()` 断言均有独立 FAIL 路径（`fails.append` → `sys.exit(1)`）；无恒真断言
- `set -u` + `set -o pipefail`；exit 码显式捕获（`rc=$?`）；无 `tee` 吞退出码
- `trap cleanup EXIT` 保护 `--inject` 中断态
- 注入3 项（changelog 追加 / MEMORY 删除指针 / issues-closed 追加）均非空且可还原（sha256 校验）
- 结论：**脚本合格**，不需修改

---

**2. 重跑记录**

| 检查 | 真实输出 | EXIT |
|---|---|---|
| `bash .work/evidence/INTEG-014t/run.sh`（full） | STRUCTURAL CHECKS: ALL PASS; make check EXIT=0; check_issues EXIT=0; EVIDENCE: PASS (mode=full) | **0** |
| `bash .work/evidence/INTEG-014t/run.sh --inject` | 3 注入→预期 FAIL→还原 sha256 一致→回绿; EVIDENCE: PASS (mode=--inject) | **0** |
| `make check-no-residue` | check-no-residue: PASS | **0** |
| `python3 tools/infra/check_issues.py` | check_issues: 35 open, 0 closed (0 blocking M1-gate: 0) | **0** |
| `git status --porcelain | awk '{print $1}' | sort | uniq -c` | 4 ?? / 4 M / 38 R / 1 RM | — |

重跑全量84 条 PASS + make check + check_issues + no-residue，退出码与完成区一致。

---

**3. 独立注入与还原证据**

3 项注入均**不同于** engineer 的3 项（changelog/MEMORY/issues-closed）：

| # | 注入内容 | 预期 | 实际 | 还原 |
|---|---|---|---|---|
| A | `README.md` 计数 `39 个`→`38 个`（sed） | 2 FAIL | `FAIL: README section '## 1. M3 任务清单（39 个，按模块）'` + `FAIL: README 判据含 （39 个）`; EXIT=1 ✓ | cp 备份还原，sha256 一致 |
| B | `milestones.md` 删除 M3 归档注行（sed -i /归档（2026-10-05）/d） | 1 FAIL | `FAIL: milestones M3 archive note`; EXIT=1 ✓ | cp 备份还原，sha256 一致 |
| C | 复活 `INFRA-035t` 到 `.tao/tasks/infra/`（cp） | 1 FAIL | `FAIL: no terminal M3 task left in .tao/tasks ['.tao/tasks/infra/INFRA-035t-llc构建目标.md']`; EXIT=1 ✓ | rm 还原 |

还原后回跑 `--no-make` EXIT=0，全绿确认。

---

**4. §3–§6 独立复核**

| 条款 | 判定 | 证据 |
|---|---|---|
| **§3.1** 任务书 | ✅ | `git status` 38 R + 1 RM = 39 rename，全部目标为 `archive/M3/`；逐条 `项目里程碑=M3` + 终态（证据脚本39/39 PASS）；非 M3 任务零误伤（grep 验证） |
| **§3.2** changelog | ✅ | 34 条全部日期 ≤ 2026-10-05（含 INTEG-010t 2026-10-04 条目，按 §3.2 判据归 M3）；归档后0 条 dated 条目；M3 指针在表头之上（line9 < line11） |
| **§3.3** MEMORY | ✅ | 纯 M3 行仅1 行（`M3 进行中`）；归档后无该行；M3 归档指针为合法表行（line13，在 `|---|` 之后）；`M1/M2`→`M1/M2/M3` 已更新（line45） |
| **§3.4** issues-closed | ✅ | 56 条；抽样4 条 `git log --grep` 验证提交日 ≤ 2026-10-05：SPEC-097t(2026-10-05)、INFRA-017t(2026-09-29)、INFRA-041t(2026-10-05)、LLVM-047t(2026-10-05) |
| **§5** README | ✅ | §1 任务清单(39)/§2 changelog(34)/§3 MEMORY(1)/§4 指针(56) 齐全；表不断（`---` 后紧跟数据行）；无连续空行；文件尾单换行 |
| **§6** 台账处理 | ✅ | changelog: 指针在表头之上 ✓；MEMORY: 指针为合法表行 ✓；issues.yaml: 头指针(line46) + 0 closed ✓；milestones: 归档注(line25) ✓ |

---

**5. SPEC-096k 处置**

- 状态：`待开始`→`已验证` ✓（已核实 `.tao/archive/M3/spec/SPEC-096k-M3启动与分解.md` line6: `状态：已验证`）
- 归档：随 M3 归档（`git status` 显示 `RM`，rename + modify） ✓
- 与用户原话「归档 SPEC-096k，任务数记 39」一致 ✓

---

**6. 门控**

| 命令 | EXIT | 备注 |
|---|---|---|
| `make check` | 0 | repository checks: PASS; lit 34/34 |
| `check_issues.py` | 0 | 35 open, 0 closed |
| `check-no-residue` | 0 | PASS |

---

**7. 表格纪律核**

- 7 文件无连续空行：PASS（证据脚本逐文件检查）
- README 表不断（`|---|` 后紧跟数据行）：PASS
- 文件尾单换行（README/changelog/MEMORY/issues.yaml/milestones）：PASS
- changelog 指针在表头之上（非 `|---|` 与数据行之间）：PASS
- MEMORY 指针为合法表行（在 `|---|` 之后）：PASS

---

**8. 遗留判定**

| 遗留 | 判定 | 理由 |
|---|---|---|
| changelog 归档后空表 | ✅合规 | 34 条全部 ≤ 达成日，归档后表头+分隔保留、无数据行；`/complete` 追加 INTEG-014t 条目后恢复非空——与 M2 归档时 `INTEG-010t` 条目同机制，属正常 append-only 行为 |
| INTEG-010t（M2 归档，2026-10-04）纳入 M3 快照 | ✅合规 | §3.2 判据为「日期 ≤ 达成日」，2026-10-04 ≤ 2026-10-05；该条于 M2 快照后写入，M2 未收，归 M3 正确 |
| 提交待用户确认 | ✅已知 | AGENTS 约束；本任务只落盘未 commit |
