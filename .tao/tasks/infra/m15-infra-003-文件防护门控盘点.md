# m15-infra-003: 文件防护门控盘点（防新增 / 防修改）

**模块**：infra
**项目里程碑**：M15
**依赖**：无
**可并行分片**：否（跨全部门控与目录）
**预估**：2–3 h
**档位**：小改（只调研与文档，不改门控实现）
**状态**：待验收

## 背景（用户 2026-11-18）

现有 `make check` 体系里有 60+ 个 `check-*` 目标，但**没有一张表说明「哪些门控在防止文件被新增或被修改」**。结果是：新增一个目录/文件时，没人知道会不会被门控挡住；改动一个受保护文件时，也不知道哪一层会红。

本任务只做**盘点与缺口分析**，**不新增、不修改任何门控**。

## 目标

产出一张**文件防护门控清单**，覆盖 `Makefile` 里全部 `^check-*:` 目标（现场 `grep` 计数，不写死），每条回答三个问题：

1. **是否扫描文件系统**（目录/文件），扫描面是什么（逐条写具体路径或 glob）。
2. **是否防新增**：白名单 / 许可集 / 新文件命名规则 / 覆盖要求。
3. **是否防修改**：sha256 锁 / git blob index / 内容逐字节比对 / 生成物一致性。

## 覆盖范围（必须逐条过，不得抽样）

`Makefile` 全部 `^check-[a-z0-9-]*:` 目标（当前 64 个，现场统计），以及它们调用的 `tools/**` 检查脚本。至少覆盖以下已知相关项并**核准其真实判据**（不得照抄本文措辞）：

- 白名单/防新增类：`check-dirs`、`check-contracts-dir`、`check-knowledge-dir`、`check-run-artifacts`、`check-no-residue`、`check-temp-dirs`、`check-test-reports`、`check-archive`
- 锁/防修改类：`check-spec-readonly`、`check-index-blobs`、`check-patch-tree`、`check-source-state`、`check-spec-drift`、`check-contracts-pending`、`check-musl-freshness`、`check-builtins-freshness`
- 命名/结构类：`check-asm-list`、`check-asm-list-drift`、`check-tests-index`、`check-tasks`、`check-milestones-fresh`、`check-writer-guards`
- 生成物一致性类：`check-wuming-cycles`、`check-decodetree-repro`、`check-instrinfo`、`check-interface`

输出表格列（每行一个门控）：

```
门控名 | 层级(L1/L2/L3) | 扫描面 | 防新增 | 防修改 | 判据出处(文件:行) | 缺口
```

## 缺口分析（本任务的核心产出）

1. **哪些目录没有白名单**：`tests/`、`tools/`、`docs/`、`.tao/`、`components/`、`manifests/`、`contracts/` 各自是否被某个门控约束「只能放什么」；列出无约束的目录与后果（如随手新建文件不会被拦）。
2. **哪些受保护文件只靠「人不改」**：没有 sha256 / blob 校验的规范类或配置类文件清单。
3. **重复与空白**：同一防护被两个门控覆盖（冗余）或某类防护完全没有（如「新增 `.py` 必须有 README 登记」目前只在 `tools/` 有？）。
4. **结论只给事实与缺口**，**不提改造方案**（改造另立任务）。

## 落点

- 主产出写入 `docs/Process-07-门控分层规范.md` 新增一节（`§N 文件防护门控清单`），或若该文件已过长，写入 `.tao/knowledge/` 并在 `Process-07` 留一行指针。
- 需给出「层级」时以 `Process-07` 现有分层表为准，**不自行改分层**。

## 验收（逐条贴真实 rc）

1. `grep -c "^check-[a-z0-9-]*:" Makefile` 的现场值与清单行数**相等**（差额必须逐条解释，不得静默略过）。
2. 表格每行的「判据出处」给 `文件:行`，抽查 10 行由 reviewer 现场核对存在且语义一致。
3. 缺口分析至少给出：无白名单目录清单、无哈希保护文件清单、冗余/空白各 ≥1 例（若确实没有，写「经核无」并给核验方法）。
4. 文档门控：`make check-knowledge-refs`、`check-dirs`、`check-test-reports` rc=0。
5. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**。
2. **只写文档**：不改任何 `check-*` 目标、不改 `tools/**` 脚本、不改版本号。
3. 引用门控判据必须**读源码/读 `Process-07`**，不得凭门控名猜。
4. 临时文件放 `/tmp/opencode/m15-infra-003/`；`cp`+md5 还原。

## 完成区
**测试结果**：
- `grep -c "^check-[a-z0-9-]*:" Makefile` = 64（现场）；新增表格行 `grep -c '^| `check-'` = 64，相等。
- `python3 tools/infra/check_knowledge_refs.py` rc=0（0 具体 `.work/**` 引用；0 悬空互指）。
- `python3 tools/infra/check_dirs.py` rc=0（`check-dirs: PASS`）。
- `python3 tools/infra/check_test_reports.py` rc=0（10 report(s), 5 snapshot(s)）。
**修改文件**：
- `docs/Process-07-门控分层规范.md`（新增 §7 + §7.1，+111 行）。
**验收结果**：待验收（未提交 git；未改 Makefile / tools/** / 版本号）。
**新发现/坑**：
- 门控判据读源码，未凭名猜；白名单/锁/命名/生成物一致性四组均已核准真实判据。
- 清单覆盖全部 64 个 `^check-*:` 目标；`check`/`check-modules`/`check-full` 等 `_locked-*` 包装目标不匹配 `^check-*:`，故不列（本节已说明）。
**遗留问题**：
- 无（缺口仅记录，不改造）。

## 待裁定

（无）

## 审阅记录

### 第 1 轮 reviewer 验收（2026-11-18，小改档）

**自证**：worktree `/tmp/opencode/m15-infra-003/wt`、分支 `m15-infra-003`、HEAD `6ee6d470`；开工 `git status --porcelain -uall` 空（rc=0）；主工作树 `/mnt/tao/DADAO-v5` 在 `master` 且 status 空（只读未碰）。以下全部为 reviewer 本人执行的命令输出，非采信完成区。

**重跑记录（禁 `| tee`；无 timeout 124）**
1. 计数对账：`grep -c "^check-[a-z0-9-]*:" Makefile` = **64**（rc=0）；`grep -c '^| \`check-' docs/Process-07-门控分层规范.md` = **64**；两侧集合 `comm -23`/`comm -13` **均空**、`uniq -d` 无重复 ⇒ 完全相等，**无差额需解释**。
2. 判据出处：脚本核 64 行 `文件:行` ⇒ **0 文件缺失、0 行号越界**；语义抽查 **19 行**（白名单/锁/命名结构/生成物四组全覆盖）：`check_patch_tree.py:7-35,379-431`（断言（断言①②⑤⑥）、`check_knowledge_dir.py:40-56`、`check_contracts_dir.py:41-50`+`:73-75`（只看顶层、子目录不限）、`check_spec_purity.py:38-45`、`check_tests_index`、`check_archive`、`check_spec_readonly.py:4-12,30-39`、`check_index_blobs.py:124-132`（`hash-object`）、`check_musl_freshness.py:16-36,159`、`check_builtins_freshness.py:27-48`、`check_syscall_abi.py:6-40`、`gen_spec_archive.py:430-487`（逐文件 + 组合 sha）、`check_run_artifacts.py:6-25,299-347`、`check_test_reports.py:44-47`（`NAME_RE`）、`check_dirs.py:4-16,38-46`、`check_dirs.py:186-238`、`check_milestones_fresh.py:36-64`、`check_tasks.py:11-31`（报告型默认 rc=0）、`gen_wuming_cycles.py:22-24`、`validate_instrinfo.py:26-39`、`check_decodetree_repro.py:2-19`、`check_interface_alignment.py:4-14`、`gen_cfx_alias_table.py:37-41` —— 逐条打开确认**存在且语义与表内描述一致**。
3. 层级列不改分层：`_locked-check:`（`Makefile:1171`）成员 52、非成员 12；表内 `层级=='L1'` ↔ 实际在 L1 **逐行不一致 0 条**；`GATE_LOCKED_TARGETS` 内 24 个 `check-*` **全部无字面定义**（纯 `_locked-*` 包装）⇒ 表外排除说明属实。
4. 文档门控：`check_knowledge_refs.py` **rc=0**（0 具体 `.work/**`；0 悬空）、`check_dirs.py` **rc=0**（`check-dirs: PASS`）、`check_test_reports.py` **rc=0**（`10 report(s), 5 snapshot(s)`）—— 与完成区逐字一致。
5. 越界：`git diff --stat 59cba1d1..HEAD` = **仅**任务书 + `docs/Process-07`（2 文件，+127/−1）；`grep -E "^(Makefile|tools/|spec/|contracts/)"` 命中 **rc=1（零改动）**；版本号零改动；`git status --porcelain -uall` 空。

**缺口独立复核（3 条必核，均属实）**
- ① 无白名单目录：全仓 `grep` 无任何门控枚举 `tools/`（仅 `check_dirs.py:40` 扫 symlink 前缀）、`docs/`（零命中）、`manifests/*.toml`（零命中）、`components/` 顶层（零命中）；`.tao/adr/` 仅被 `check_knowledge_refs` 解析悬空引用、`check_spec_drift.py:5-11` 只核版本头/ADR 状态；`.tao/tasks/` 仅 `check-tasks` 报告型 + `check-milestones-fresh` A2 覆盖 ⇒ 表内 6 目录判定**全部属实**。
- ② `grep -rn "reference-snapshots" Makefile tools/` **零命中（rc=1）**；`manifest_check.py` 只 `load()` 具名文件、`:45`/`:110` 仅验 40-hex ⇒「sha256 全仓无门控核对、改了也不红」属实；`opcodes.yaml` 不在任何 lock 条目（仅注释提及）属实。
- ③ `check_spec_readonly.py:117` `for path, literal, _group in entries:` **只遍历锁内条目**，全文 `grep "glob|subset|unlocked|not in lock"` 零命中 ⇒ **无「`spec/*.md` 全集 ⊆ 锁」反向断言**，「新增册逃锁」属实（最关键一条）。

**独立反例注入（2 路，均 `cp`+md5，日志留 `/tmp/opencode/m15-infra-003/`）**
- 临时树 `--root`：`check-spec-readonly` 基线 **rc=0**（`21 read-only spec volume(s) OK`）→ 改 `spec/SimRISC-00-*.md` → **rc=1**（`MISMATCH … FAIL (1/21)`）→ `cp` 还原、md5 与基线相等 → **rc=0**（`21 … OK`）。
- 真实树：新建 `.tao/knowledge/zz-review-inject.md` → `check-knowledge-dir` **rc=1**（`白名单外文件 … FAIL (1 个白名单外文件)`）→ 删除 → **rc=0**；`.tao/knowledge` 清单 md5 前后同为 `f93847d0…`、`git status` 空；日志 `k0.log==k2.log`、`s0.log==s2.log`（md5 相等）。

**约束核验**：独立 worktree ✓｜主工作树未碰 ✓｜禁提交（本轮 0 commit）✓｜只写文档、`$BASE..HEAD` 仅 2 文件 ✓｜未改 `check-*`/`tools/**`/`spec/`/`contracts/`/版本号 ✓｜临时文件在 `/tmp/opencode/m15-infra-003/`、还原用 cp+md5 ✓｜无 `| tee`、无 rc=124 ✓

**判决：Accepted**（小改档、仅文档；代码行为/门控退出码/断言计数/spec·合约语义四类阻断面均无命中）。

**未闭合项（文档级 finding，交 architect 收尾时顺手改，不返工）**：① `check-spec-purity` 行「防新增=白名单」实为**禁用词黑名单**（不拦新增册；其缺口列已自纠「只拦禁用词」）；② `check-milestone` 层级写「里程碑」而 §1.1 原文为「L2 层 / 里程碑收尾专项」、`check-tasks` 写「报告（默认 rc=0）」（实为 `check-milestone --strict` 与 `check-full` 成员）；③ `.tao/tasks/` 归「无白名单」宜补一句「但 `check-milestones-fresh` A2 覆盖会拦未入台账的新任务书」，以免误读为「新建完全不被拦」。
