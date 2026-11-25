# m18-infra-004: `issues.yaml` 按里程碑分册（`issues-left` + `issues-m16…m19`）

**模块**：infra
**项目里程碑**：M18
**依赖**：无
**可并行分片**：否（`issues*` 为全仓共享文件，单写者）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待验收

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

1. `make check_issues`（改造后）rc=0：五文件合并 193 条；**全局 ID 唯一性断言**可失败（构造一条重复 ⇒ 红、还原 ⇒ 绿）。
2. `python3 tools/infra/archive_issues.py --milestone M14 --check <快照>` 仍 PASS（归档取集不回归）；`make check-knowledge-refs`、`make check-milestones-fresh`、`make check-tasks`、`make validate-vectors` rc=0。
3. 五文件条数之和 = 193，且各文件条数 = 拆分前按 `milestone` 统计值（M16 44 / M17 18 / M18 20 / M19 4 / left 107）。
4. `grep -rn "issues\.yaml" --include="*.py" tools tests | grep -v __pycache__` 只剩「历史/说明」类命中，运行时路径全部改为多文件。
5. 全仓 `ISS-<file>-NNN` 新格式样例可用：`issues_store.load_all()` 能读；`sort_key` 对两种格式都有序。

## 约束

不提交 git（由主会话合并）；只改 `.tao/knowledge/issues*`、`tools/infra/{check_issues,archive_issues,issues_store}.py`、`tools/spec/check_scope.py`、上述文档与本任务书；**不改任何 issue 的编号、状态、字段内容**；不动 `.tao/archive/**`；术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 完成区（2026-11-25，第一轮落地 + 用户追加 1–3）

1. **拆分**：`issues.yaml`（193 条）→ `issues-{left,m16,m17,m18,m19}.yaml`（107/44/18/20/4），多重集逐条比对与拆分前**完全相等**；原文件删除。
2. **ID 口径**：存量旧号**冻结**（用户裁定，不重编）；新增用 `ISS-<file>-NNN`；`check_issues` 增「ID 形状 / 新增重复必败 / 文件与 milestone 一致」三条断言，6 对存量重复登记在 `KNOWN_LEGACY_DUPLICATES`（新增重复即失败，去重后必须删登记，否则判陈旧）。
3. **用户追加 1–3（收尾清理）**：`issues-left` 中 M12–M15 的 **55 条 closed 全部核对在对应 `archive/M*/issues-closed.md` 后删除**（M12 27 / M13 17 / M14 10 / M15 1，missing=0）；`issues-left` 现只剩 **52 条 open**；`issues-m16/m17/m18` 的 closed 保留到各自收尾。
4. **`archive_issues.py`**：新增 `--verify PATH`（离线自检：行数 / ID 唯一 / 计数行一致）；`--check` 明确为「删除前一次性核对」；M12–M15 `--verify` 全 PASS（27/17/10/1）。
5. **文档**：`Process-04 §4` 增加「先 check 后删除、再用 verify」的清理顺序；`MEMORY.md` 的「活台账保留全部条目供 --check」改为「收尾后不保留已归档 closed」。
6. **门控**：`check_issues` 101 open / 38 closed（139 条 5 册）rc=0；`check-knowledge-refs`、`check-milestones-fresh`、`check-manifests-guard` 全 PASS。
7. **遗留**：`ISS-476`（M17 册里 `closed_in: M15`）为账目错位——未在本次清理内处理（它不在 left），处置口径待 M17 会话/用户裁定。
