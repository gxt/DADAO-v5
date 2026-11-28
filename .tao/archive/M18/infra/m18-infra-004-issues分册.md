# m18-infra-004: `issues.yaml` 按里程碑分册（`issues-left` + `issues-m16…m19`）

**模块**：infra
**项目里程碑**：M18
**依赖**：无
**可并行分片**：否（`issues*` 为全仓共享文件，单写者）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（用户 2026-11-25 裁定）

多会话（每里程碑一个会话）并行派单后，全局单文件 `issues.yaml` 出现 **6 对重复编号**（`ISS-518/530/536/537/538/539`），且跨册读写互相踩。用户裁定：

1. 拆成 **`issues-left` + `issues-m16/m17/m18/m19`** 五个文件（`milestone: M20`、`M14`/`M15`、`milestone: null` 的都落 `issues-left`）；
2. 每个里程碑**创建之初**把该里程碑应解决的 issue 移入自己的文件；
3. 里程碑进行中**新增/关闭**的 issue 都写自己文件；**跨文件修改需用户同意**；
4. 里程碑收尾时清空自己文件，未解决条目汇总到 `issues-left`；
5. **现有 193 条保留旧号**（`ISS-<数字>` 冻结，不再改号）；**仅新增条目**用 `ISS-<file>-NNN`（如 `ISS-m16-045`、`ISS-left-001`）；`.tao/archive` 的 6206 处历史引用**不动**。

## 目标

1. 按 `milestone` 拆分 `issues.yaml` → `.tao/knowledge/issues-{left,m16,m17,m18,m19}.yaml`（条目顺序保持原文件顺序），删除原 `issues.yaml`；每文件头写明「ID 规则：存量旧号冻结、新增用 `ISS-<file>-NNN`；本文件由对应里程碑会话独占写」。
2. 新增 `tools/infra/issues_store.py`：`load_all()`（glob `issues-*.yaml` 合并）、`path_for(milestone)`、`sort_key(id)`（**兼容旧号与 `ISS-<file>-NNN` 两种格式**）。
3. 消费方改造：`check_issues.py`（多文件 + 断言 **全局 ID 唯一** + ID 格式校验两条并存）、`archive_issues.py`（多文件 + 排序兼容）、`tools/spec/check_scope.py` 的 `HISTORY_PREFIXES`（`issues.yaml` → `issues-`）。
4. 文档指针同步：`.tao/knowledge/MEMORY.md`、`docs/Process-04-里程碑归档规范.md`、`AGENTS.md`（若提到 `issues.yaml`）、相关工具注释；旧→新文件映射无需（未改号）。
5. **重复编号如实处理**：拆分后 6 对重复仍在，须在完成区列出「哪一对落在同一文件、哪一对跨文件」，并建议「后续按用户同意后去重」——本任务**不改号**。

## 验收（逐条贴真实 rc）

1. `python3 tools/infra/check_issues.py`（改造后）rc=0：五文件合并 193 条；**全局 ID 唯一性断言**可失败（构造一条重复 ⇒ 红、还原 ⇒ 绿）。
2. `python3 tools/infra/archive_issues.py --milestone M14 --check <快照>` 仍 PASS（归档取集不回归）；`make check-knowledge-refs`、`make check-milestones-fresh`、`make check-tasks`、`make validate-vectors` rc=0。
3. 五文件条数之和 = 193，且各文件条数 = 拆分前按 `milestone` 统计值（M16 44 / M17 18 / M18 20 / M19 4 / left 107）。
4. `grep -rn "issues\.yaml" --include="*.py" tools tests | grep -v __pycache__` 只剩「历史/说明」类命中，运行时路径全部改为多文件。
5. 全仓 `ISS-<file>-NNN` 新格式样例可用：`issues_store.load_all()` 能读；`sort_key` 对两种格式都有序。

## 约束

不提交 git（由主会话合并）；只改 `.tao/knowledge/issues*`、`tools/infra/{check_issues,archive_issues,issues_store}.py`、`tools/spec/check_scope.py`、上述文档与本任务书；**不改任何 issue 的编号、状态、字段内容**；不动 `.tao/archive/**`；术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 完成区

1. **拆分**：`issues.yaml`（193 条）→ `issues-{left,m16,m17,m18,m19}.yaml`（107/44/18/20/4），多重集逐条比对与拆分前**完全相等**；原文件删除。
2. **ID 口径**：存量旧号**冻结**（用户裁定，不重编）；新增用 `ISS-<file>-NNN`；`check_issues` 增「ID 形状 / 新增重复必败 / 文件与 milestone 一致」三条断言，6 对存量重复登记在 `KNOWN_LEGACY_DUPLICATES`（新增重复即失败，去重后必须删登记，否则判陈旧）。
3. **用户追加 1–3（收尾清理）**：`issues-left` 中 M12–M15 的 **55 条 closed 全部核对在对应 `archive/M*/issues-closed.md` 后删除**（M12 27 / M13 17 / M14 10 / M15 1，missing=0）；`issues-left` 现只剩 **52 条 open**；`issues-m16/m17/m18` 的 closed 保留到各自收尾。
4. **`archive_issues.py`**：新增 `--verify PATH`（离线自检：行数 / ID 唯一 / 计数行一致）；`--check` 明确为「删除前一次性核对」；M12–M15 `--verify` 全 PASS（27/17/10/1）。
5. **文档**：`Process-04 §4` 增加「先 check 后删除、再用 verify」的清理顺序；`MEMORY.md` 的「活台账保留全部条目供 --check」改为「收尾后不保留已归档 closed」。
6. **门控**：`check_issues` 101 open / 38 closed（139 条 5 册）rc=0；`check-knowledge-refs`、`check-milestones-fresh`、`check-manifests-guard` 全 PASS。
7. **遗留**：`ISS-476`（M17 册里 `closed_in: M15`）为账目错位——未在本次清理内处理（它不在 left），处置口径待 M17 会话/用户裁定。

## 审阅记录

### 第 1 轮 reviewer 验收（2026-11-26，船后补验；**合并先于验收**：`797dc1c3` + 收尾 `86b6b3bf` 已在 master）

**重跑记录（本人在仓库根执行；证据脚本在运行期证据目录内的 `split_check.py`/`cleanup_check.py`/`inject*.sh`）**
1. 拆分：读 `797dc1c3^` 的 `issues.yaml` 与 `797dc1c3` 五册 → parent 193；left 107 / m16 44 / m17 18 / m18 20 / m19 4；`multiset equal: True`、五册 `order preserved: True`、`bad placements: 0`、rc=0（旧号冻结由此可证：编号/字段零改动）。
2. 收尾：`86b6b3bf^→86b6b3bf` 的 `issues-left` 差分 → before 107 / after 52 / deleted 55（closed_in = M12 27、M13 17、M14 10、M15 1，status 全 closed）、added 0；55 条逐条命中对应 `archive/M*/issues-closed.md` 表行 `missing: 0`；left 现 `{'open': 52}`、rc=0。
3. `python3 tools/infra/archive_issues.py --milestone M12/M13/M14/M15 --verify .tao/archive/<M>/issues-closed.md` → 全 `PASS verify (27/17/10/2 rows…)` rc=0；M16/M17 现场 `--write→--check→--verify` round-trip PASS（54/19 rows）；M14 `--check` 现 `FAIL … (0 rows)`＝收尾删除后的既定口径（改用 `--verify`）。
4. 门控：`python3 tools/infra/check_issues.py` rc=0（49 open/100 closed、149 条 6 册——第 6 册 `issues-m20` 是后续他人新增）；`check-knowledge-refs` rc=0、`check-manifests-guard` rc=0、`check-scope` rc=0、`check-tasks` rc=0、`validate-vectors` rc=0；`check-milestones-fresh` **rc=2**（9 项，见归因）；`make check` **rc=2**（`make -k check` 10 目标红，见归因）；`check-dead-refs` 无 Makefile 目标（按用户裁定未接入），直接跑脚本 rc=1（`tools/include` 死引用，出自 m18-infra-002 的 `tools/linux`，与本任务无关）。
5. 注入（`cp`+md5 备份/还原，还原后 md5 与注入前逐字相等；`git status --porcelain -uall` 审前/审后均 0 行）：A 复制 `ISS-429` 追加 ⇒ `DUPLICATE id` FAIL rc=1；D 某条 `milestone` 改 M16 ⇒ `LEDGER MISMATCH` FAIL rc=1；E id 改 `ISS-foo` ⇒ `BAD id shape` FAIL rc=1；C M14 归档计数行 10→9 ⇒ `计数行 9 != 实际行 10` FAIL rc=1；各还原后均回绿 rc=0。

**归因（红项均非本任务）**
- `check-milestones-fresh` 9 项全是 m16-* 任务「表=已验证 / 册=待验收」；`git log -1` 显示这 9 册与 `milestones-m16.md` 最近改动属 11-25 14:24 → 11-26 03:35 的他人合入（晚于 `86b6b3bf` 12:43），两提交未碰这些文件；本任务台账行一致（不在违例表）。
- `make -k check` 红 10 项：patch-tree(8: llvm6/musl2)、isa-coverage(`escape_ciii_cfx`/矩阵)、cfx-vectors(1)、case-ledger(缺 10 行)、arch-self-test(2)、musl-freshness(2)、milestones-fresh(9)、run-artifacts(651)、interface(N 289≠299)、temp-dirs(6：他人陈旧临时目录 + 盘 85%)。两提交 `--name-only` 文件集只含分册/工具/文档/任务书，与上述输入全不相交；输入侧最近改动属 m18-llvm-002/spec-007、m18-infra-001/002、m18-linux-010、m20-llvm-* 等他人任务。
- 验收①写的 `python3 tools/infra/check_issues.py` 无此目标（`No rule` rc=2）；真实门控为 `python3 tools/infra/check_issues.py`（`make check` 末尾同一条），已按后者执行。

**约束核验**：两提交无 `components/`、`spec/`、`.tao/contracts/`、`Makefile` 改动 ✓；`check_scope.HISTORY_PREFIXES` 已 `issues.yaml → issues-` ✓；6 对重复（518/530/536/537/538/539，均跨 m16↔m17/m18）交付时只登记在 `KNOWN_LEGACY_DUPLICATES`（全仓 grep 仅 `check_issues.py` 一处），现由他人 `a0d85963` 去重并清空登记、无重复无陈旧项 ✓；`ISS-476` 两提交未改条目、仅完成区第 7 条如实登记（后续 `6425fdba` 另案处置）✓；验收③ 193 条本轮以多集重建复核通过 ✓；验收④ `grep issues.yaml` 仅注释/消息串命中、无运行时路径 ✓；验收⑤ `load_all`（18 条新格式）、`sort_key` 双格式有序、`path_for` 正确 ✓。

**Finding（均文档级/流程级，不阻断）**
- F1：`## 完成区（2026-11-25，…）` 是全仓唯一非标准标题 ⇒ `check-tasks` 漏收尾主表抓不到本任务，正是本次队列漏检的机械成因；建议改回 `## 完成区`、日期并入正文。
- F2：验收①命令名应写 `python3 tools/infra/check_issues.py`（仓库内无 `check_issues` 目标）。
- F3：`86b6b3bf` 混入他人改动（`m16-qemu-006`、`m16-testcases-021` 状态 待验收→已验证；`milestones-m18` 的 `m18-chipyard-001` 行措辞修剪），请 architect 收尾确认归属。
- F4：删一条 open 分册条目无任何常驻门控变红（`check_issues`/`check-knowledge-refs`/`check-archive` 均 rc=0）——条数是拆分时一次性判据；是否补常驻计数门控由架构师定。

**判决：Accepted** —— 验收命令在本人重跑下按上述口径全过；红项逐项归因他人（证据见上）；三条分册断言与归档计数断言均实测可达 FAIL 并还原回绿。合并先于验收（既定事实，不追究流程）。
