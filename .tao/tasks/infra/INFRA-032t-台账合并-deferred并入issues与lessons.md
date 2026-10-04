# INFRA-032t: 台账合并——deferred.md 并入 issues.yaml（结构化）与 lessons.md（教训）

**模块**：infra
**项目里程碑**：M1→M2
**依赖**：无（纯台账 / 文档 / 门控整理；不依赖组件构建）
**状态**：已验证

## 背景与动机

`.tao/knowledge/deferred.md`（散文遗留台账，约 245 行）与 `.tao/knowledge/issues.yaml`（结构化 issue 注册表，74 条）**内容重叠**——issues.yaml 最初（`INFRA-010t`，2026-09-21）即**从 deferred.md 编撰**。二者分居两处、职责重叠，维护成本高。

用户裁定（2026-10-04）：

- **合并**：方向 = **issues.yaml（结构化）胜出**，吸收 deferred.md 的 issue 部分；deferred.md 的**教训 / 方法论 / 过程记录**独立成文。
- 教训文件命名 = **`.tao/knowledge/lessons.md`**（英文名）。
- **`deferred.md` 删除**（不留指针 stub）。

关联前置：`docs/issues.yaml` 已由归档工作移至 `.tao/knowledge/issues.yaml`（本轮已 `git mv`）。

## 目标与交付物

1. **`.tao/knowledge/issues.yaml`（唯一结构化台账）**
   - 保留现有 74 条（63 open + 11 closed），schema 不变（`id/title/status/scope/blocks/resolved_by/notes`）。
   - **吸收** deferred.md 的 **issue-like** 项；与现有条目**去重**（不得重复登记）；新增项 `id` 续 **`ISS-075`** 起。
   - 头注释：`status`/`scope`/`blocks`/`resolved_by` 字段约束保持不变。
2. **`.tao/knowledge/lessons.md`（新建）**
   - 承载 deferred.md 的**非 issue**内容：教训（教训/经验）、方法论（验收分层等）、过程记录（子代理异常事件、任务书模板改进建议、反例注入教训等），**按主题组织**。
   - **不得丢失信息**：deferred.md 每一条的实质内容须可在此或 issues.yaml 中找到。
3. **`.tao/knowledge/deferred.md`：删除**（`git rm`）。
4. **引用更新**（仅**活引用**；历史任务书 / `.tao/archive/**` 不动）：
   - `tools/spec/check_scope.py` 的 `HISTORY_PREFIXES`：`.tao/knowledge/deferred.md` → `.tao/knowledge/lessons.md`
   - `tools/spec/check_asm_prose.py` 的排除表：`deferred.md` → `lessons.md`（若 `lessons.md` 含同类非 simrisc 围栏块；须实测确认 `make check` 与语义一致）
   - `spec/Process-04-里程碑归档规范.md` 的「遗留台账」行：`deferred.md` → `lessons.md`
   - 全仓 `grep -rn deferred.md`（**排除** `.tao/archive/`、`.tao/tasks/`、`.git/`）确认无遗漏活引用。
5. **`make check` EXIT=0**（含 `check-scope` / `check-asm-prose` / `check-issues`）。
6. **一键证据脚本** `.work/evidence/INFRA-032t/`（见验收）。

## 分类判据（engineer 须**逐条**执行，可追溯）

对 deferred.md 的**每个 bullet** 判定归宿：

| 类别 | 判据（示例关键词） | 归宿 |
|---|---|---|
| issue-like | 待决 / 遗留 / 缺陷 / 缺口 / 后续候选 / 「仅登记，不动手」/ 已消解记录（含 `resolved_by` 信息） | `issues.yaml`（新 id；已消解的 `status: closed` + `resolved_by`） |
| 教训 / 方法论 / 过程记录 | 「教训」/「方法论」/ 子代理异常事件 / 任务书模板改进 / 反例注入教训 / 工具陷阱 | `lessons.md` |
| 已被现有 74 条覆盖 | 与现有 issue 同指一事 | **去重**（不新增；必要时把 deferred 的细节补进该条 `notes`） |

**每个 bullet 的归宿须在完成区逐条列出**（deferred.md 行号 → `issues.yaml:<id>` / `lessons.md:<小节>` / `去重:<id>`），供 reviewer 抽查。

## 约束

- **不得**改 `.tao/archive/**`（历史快照）、**不得**改历史任务书 / 已验收记录。
- **不得**丢失信息（issues.yaml + lessons.md 须完整承载 deferred.md 全部内容）。
- `tools/spec/check_scope.py` **仅改 `HISTORY_PREFIXES` 一行**，**不得**动其断言逻辑（该文件刚由 `SPEC-089t` 改过，勿冲突）。
- **不得**改 `contracts/`、`components/`、`tests/`、`spec/SimRISC-*`。
- 临时目录 `/tmp/opencode/INFRA-032t/`；**不提交 git**；失败即停、禁自动重试。
- 完成区与真实输出逐条对齐；复杂命令输出留存 `.work/log/infra/INFRA-032t-*.log`。

## 验收标准

1. `python3 -c "import yaml,sys; d=yaml.safe_load(open('.tao/knowledge/issues.yaml')); print(len(d))"` 输出 = 74 + 新增数；schema 合法。
2. `lessons.md` 存在；完成区逐条映射证明 deferred.md 全部 bullet 有归宿（无遗漏、无重复）。
3. `deferred.md` 已删除；`grep -rn deferred.md` 无活引用（仅历史/归档命中）。
4. `make check` EXIT=0。
5. **一键证据脚本**（`.work/evidence/INFRA-032t/`）：非交互；任一检查失败即非零退出；逐项打印「检查名 + 期望/实际 + 退出码」；**内置反例自检** = 「从 issues.yaml / lessons.md 删掉一条 deferred 映射 → 覆盖/映射检查预期 FAIL → 还原 → 回绿」；结尾不得用 `tee` 吞退出码。

## 风险

- **逐条分类易漏同类**（AGENTS.md「修复须修一类」）：完成区逐条映射 + reviewer 独立抽查「随机抽 5 条 deferred bullet 追归宿」。
- **已消解 + 仍 open 混排 bullet**：须拆——issue 部分入 issues.yaml（含 `resolved_by`）、教训部分入 lessons.md。
- **`check_asm_prose` 对新 `lessons.md` 的处置**：若 `lessons.md` 含围栏代码块，须实测其对 `check-asm-prose` 的影响并作正确处置（排除或如实修正），不得为保绿而掩盖。

## 参考

- `spec/Process-04-里程碑归档规范.md`（同类台账处理先例：搬内容 + 留指针；本任务为**合并**，故删除原文件）
- `.tao/archive/M1/README.md`（M1 归档时对 changelog/MEMORY 的处理先例）

## 完成区

**测试结果**：通过 5/5 验收项。① `issues.yaml` 条目 **127**（74 既有 + 新增 53，`ISS-075`–`ISS-127`），schema 合法；② `lessons.md` 新建（7 章 18 小节），deferred.md 全部 **201 个 bullet**（155 顶层 + 28 无序子项 + 18 有序子项）**逐条有归宿**（见下方映射）；③ `deferred.md` 已 `git rm`；④ `make check` **EXIT=0**；⑤ 一键证据脚本默认 **EXIT=0**、`--inject` **EXIT=0**（3 类反例均 FAIL→还原→回绿）。

**修改文件**：

engineer 本轮所改：
- `.tao/knowledge/issues.yaml`：追加 `ISS-075`–`ISS-127`（53 条）；既有 `ISS-016`/`ISS-057`/`ISS-065` 依 deferred.md 的「已消解/已关闭」标注由 `open` 改为 `closed`（+`resolved_by`/`notes`）；头注增合并说明；`ISS-074` 前注释措辞「deferred.md」→「原 backlog」。
- `.tao/knowledge/lessons.md`：**新建**（教训/方法论/过程记录，18 小节）。
- `.tao/knowledge/deferred.md`：**`git rm` 删除（不留 stub）**。
- `tools/spec/check_scope.py`：仅 `HISTORY_PREFIXES` 一行 `deferred.md`→`lessons.md`（断言逻辑未动）。
- `tools/spec/check_asm_prose.py`：docstring 扫描范围说明 + `_EXCLUDE_FILES` 条目（`deferred.md`→`lessons.md`）。
- `spec/Process-04-里程碑归档规范.md`：L66「遗留台账」行改为 `issues.yaml`（issue）+ `lessons.md`（教训/方法论/过程记录）。

越界（**用户 2026-10-04 裁定「更新所有非禁改活引用并披露」**）：
- `.tao/knowledge/contract-isa.md`（L828/L1142 指针→`issues.yaml`）
- `.tao/knowledge/milestones.md`（L56「见 deferred.md」→`issues.yaml`）
- `.tao/knowledge/MEMORY.md`（「关键目录速查」live 行 `deferred.md`→`issues.yaml`+`lessons.md`；历史任务行保留）
- `AGENTS.md`（L131「须在 deferred.md 登记」→`.tao/knowledge/issues.yaml`）
- `docs/impact-matrix.md`（L204 引用来源列→`issues.yaml`）
- `tools/testcases/generate_isa_vectors.py`（L1073/1090/1501 注释→`issues.yaml`）
- `.tao/adr/adr-0010-qemu-task-restructure.md`（追加 `## 修订` 指针；D1–D4 未动）

本任务**未改**（`tests/` 属硬约束 7 禁改，仅披露）：
- `tests/vectors/schema.md`：L228 仍指 `.tao/knowledge/deferred.md`（活引用但禁改）。

本轮前置归档改动（**非**本任务所改，工作树中已存在）：`docs/issues.yaml → .tao/knowledge/issues.yaml`（`git mv`）、`docs/README.md`、`spec/Toolchain-01-汇编语言.md`、`tools/infra/check_issues.py`。

证据/日志（`.work/`，不入库）：`.work/evidence/INFRA-032t/{run.sh,check.py,mapping.tsv,deferred-bullets.txt}`、`.work/log/infra/INFRA-032t-make-check.log`。

**验收结果**（真实输出）：

```
$ python3 -c "import yaml,sys; d=yaml.safe_load(open('.tao/knowledge/issues.yaml')); print(len(d))"
127
$ python3 -c "...(count/open/closed/unique)..."
count= 127
open= 100 closed= 27
unique ids OK; max= ISS-127
$ python3 tools/infra/check_issues.py
check_issues: 100 open, 27 closed (0 blocking M1-gate: 0)     # rc=0
$ JOBS=8 make check                                            # EXIT=0
check-asm-prose: PASS (0 violations)
check-scope: PASS
check_issues: 100 open, 27 closed (0 blocking M1-gate: 0)
repository checks: PASS
（lit 29/29、semantics 149/149、interface 80/80）
$ .work/evidence/INFRA-032t/run.sh
[PASS] issues_parse_count: expected='127' actual='127' rc=0
[PASS] issues_ids_unique: expected='unique' actual='127 ids / 127 unique' rc=0
[PASS] deferred_deleted: expected='absent' actual='absent' rc=0
[PASS] lessons_anchors: expected='all 18 anchors' actual='all present' rc=0
[PASS] coverage_bullets_mapped: expected='201 bullets' actual='unmapped=[] extra=[212, 213]' rc=0
[PASS] mapping_issue_dests_exist: expected='all issue dests in issues.yaml' actual='all exist' rc=0
[PASS] mapping_lesson_dests_exist: expected='all lesson anchors in lessons.md' actual='all exist' rc=0
[PASS] new_issues_referenced: expected='ISS-075..ISS-127 all referenced' actual='all referenced' rc=0
[PASS] live_refs_only_allowlisted: expected='only historical/forbidden-file hits' actual='ok (historical + tests/vectors/schema.md)' rc=0
EVIDENCE: PASS EXIT=0
$ .work/evidence/INFRA-032t/run.sh --inject                     # EXIT=0
[PASS] inject__delete_mapping_row: coverage expected FAIL then PASS actual=[True, True] rc=0
[PASS] inject__delete_issues_entry(ISS-100): dests expected FAIL then PASS actual=[True, True] rc=0
[PASS] inject__delete_lessons_section(2.2): anchors expected FAIL then PASS actual=[True, True] rc=0
$ git grep -n 'deferred\.md' -- . ':(exclude).tao/archive/**' ':(exclude).tao/tasks/**'
（仅 .tao/knowledge/{changelog,MEMORY}.md（历史台账）、.tao/adr/adr-0010-*.md（历史关联+修订）、tests/vectors/schema.md（禁改）命中）
```

**新发现/坑**：

1. **任务书内部张力**：验收标准 3（全仓 grep 无活引用）与硬约束 4（只动 3 文件+台账）/7（禁改 `tests/`）冲突——实测另有 8 处活引用（contract-isa/milestones/AGENTS/impact-matrix/generate_isa_vectors/adr-0010/MEMORY/schema.md）。经**用户裁定「更新所有非禁改活引用并披露」**处理；`tests/vectors/schema.md` 因禁改保留并披露。
2. **既有台账状态漂移**：`ISS-016`/`ISS-057`/`ISS-065` 在 issues.yaml 为 `open`，而 deferred.md 已标「✅已消解/已关闭」；合并后按 deferred 关闭 ⇒ 既有 74 条由 **63 open/11 closed → 60 open/14 closed**（总条目数不变，验收 1 仍为 74+新增）。若审查者认为应冻结既有 status，请指出，将回退为仅补 `notes`。
3. **历史台账保留 `deferred.md` 字样（by design）**：`MEMORY.md`/`changelog.md` 在 `check_scope` 的 `HISTORY_PREFIXES` 内，其历史任务行按体例不回溯（见 `lessons.md §5.3`）；仅修 MEMORY「关键目录速查」live 行。
4. **`lessons.md` 无围栏代码块**，且 `check_asm_prose` 默认只扫 `.tao/knowledge/contract-*.md`（不扫 `lessons.md`）；排除表改指 `lessons.md` 是为 `--root` 模式一致性（`deferred.md` 原亦仅 `--root` 模式生效）。
5. `check_scope.py` 的 `HISTORY_PREFIXES` 中 `.tao/knowledge/*` 项实际不被默认扫描（`SCAN_DIRS` 不含 `.tao/knowledge`），但按任务要求仍同步为 `lessons.md`。

**遗留问题**：无。唯一未消解的活引用 `tests/vectors/schema.md:228` 属硬约束 7 禁改 `tests/`，仅披露（若需消解须另立可改 `tests/` 的任务）。

**deferred.md 逐条归宿映射**（201 行 bullet + 2 个 markdown 表格内容行；行号取自删除前版本）：

| deferred 行号 | 归宿 |
|---|---|
| L9 | parent（见其子条目） |
| L10 | ISS-075 |
| L11 | ISS-075 |
| L12 | lessons.md §5.1 |
| L13 | lessons.md §5.2 |
| L14 | lessons.md §5.3 |
| L15 | parent（见其子条目） |
| L16 | ISS-075 |
| L17 | ISS-075 |
| L18 | ISS-075 |
| L19 | ISS-075 |
| L20 | parent（见其子条目） |
| L21 | ISS-075 |
| L22 | ISS-075 |
| L23 | parent（见其子条目） |
| L24 | ISS-075 |
| L25 | ISS-075 |
| L26 | ISS-075 |
| L27 | ISS-075 |
| L28 | ISS-075 |
| L29 | ISS-075 |
| L30 | ISS-075 |
| L31 | ISS-001 |
| L32 | ISS-002 |
| L33 | ISS-003 |
| L34 | ISS-004 |
| L35 | ISS-005 |
| L36 | ISS-006 |
| L37 | ISS-007 |
| L38 | ISS-008 |
| L39 | ISS-009 |
| L40 | ISS-010 |
| L41 | ISS-011 |
| L42 | ISS-076 |
| L43 | ISS-012 |
| L45 | ISS-077 |
| L46 | lessons.md §3.1 |
| L47 | ISS-078 |
| L48 | lessons.md §6.1 |
| L49 | ISS-079 |
| L50 | ISS-080 |
| L52 | lessons.md §4.1 |
| L53 | ISS-081 |
| L55 | ISS-084 |
| L56 | ISS-085 |
| L57 | ISS-081 |
| L58 | ISS-086 |
| L60 | ISS-083 |
| L61 | ISS-083 |
| L62 | ISS-081 |
| L63 | ISS-082 |
| L64 | lessons.md §4.2 |
| L68 | ISS-087 |
| L69 | lessons.md §6.4 |
| L70 | ISS-088 |
| L71 | ISS-089 |
| L72 | ISS-090 |
| L74 | ISS-091 |
| L76 | ISS-092 |
| L78 | ISS-013 |
| L79 | ISS-014 |
| L80 | ISS-015 |
| L81 | ISS-016 |
| L82 | ISS-093 |
| L83 | ISS-095 |
| L84 | ISS-095 |
| L85 | ISS-094 |
| L89 | ISS-096 |
| L90 | ISS-096 |
| L91 | ISS-097 |
| L92 | ISS-098 |
| L93 | ISS-099 |
| L95 | ISS-100 |
| L99 | ISS-017 |
| L100 | ISS-018 |
| L101 | ISS-019 |
| L102 | ISS-020 |
| L103 | ISS-021 |
| L104 | ISS-022 |
| L105 | ISS-023 |
| L106 | ISS-024 |
| L107 | ISS-025 |
| L108 | ISS-026 |
| L109 | ISS-027 |
| L110 | ISS-028 |
| L111 | ISS-029 |
| L112 | ISS-030 |
| L113 | ISS-031 |
| L114 | ISS-032 |
| L115 | ISS-033 |
| L116 | ISS-034 |
| L117 | ISS-033 |
| L118 | ISS-035 |
| L119 | ISS-036 |
| L120 | ISS-037 |
| L121 | ISS-037 |
| L122 | ISS-037 |
| L123 | ISS-037 |
| L124 | ISS-037 |
| L125 | ISS-101 |
| L126 | ISS-102 |
| L130 | ISS-103 |
| L131 | ISS-104 |
| L132 | ISS-105 |
| L133 | lessons.md §4.3 |
| L134 | ISS-106 |
| L135 | lessons.md §4.4 |
| L136 | ISS-107 |
| L138 | ISS-081 |
| L140 | parent（见其子条目） |
| L141 | lessons.md §4.5 |
| L142 | ISS-111 |
| L143 | ISS-090 |
| L145 | ISS-108 |
| L147 | ISS-038 |
| L148 | ISS-039 |
| L149 | ISS-040 |
| L150 | ISS-041 |
| L151 | ISS-042 |
| L152 | ISS-043 |
| L153 | ISS-044 |
| L154 | ISS-045 |
| L155 | ISS-046 |
| L156 | ISS-047 |
| L157 | ISS-048 |
| L158 | ISS-049 |
| L159 | ISS-050 |
| L160 | ISS-051 |
| L161 | ISS-052 |
| L162 | ISS-053 |
| L163 | ISS-054 |
| L164 | ISS-055 |
| L165 | ISS-057 |
| L166 | ISS-058 |
| L167 | ISS-059 |
| L168 | ISS-060 |
| L169 | ISS-061 |
| L170 | ISS-062 |
| L171 | ISS-063 |
| L172 | ISS-064 |
| L173 | ISS-065 |
| L174 | ISS-056 |
| L175 | ISS-056 |
| L176 | ISS-056 |
| L177 | ISS-056 |
| L178 | ISS-056 |
| L179 | ISS-056 |
| L180 | ISS-056 |
| L181 | ISS-056 |
| L182 | ISS-056 |
| L183 | ISS-056 |
| L184 | ISS-056 |
| L186 | ISS-066 |
| L187 | ISS-066 |
| L188 | ISS-066 |
| L189 | ISS-066 |
| L191 | ISS-067 |
| L192 | ISS-068 |
| L193 | ISS-069 |
| L194 | ISS-069 |
| L195 | ISS-112 |
| L196 | ISS-070 |
| L197 | ISS-103 |
| L198 | ISS-071 |
| L199 | ISS-072 |
| L200 | ISS-073 |
| L201 | ISS-073 |
| L202 | ISS-073 |
| L203 | ISS-114 |
| L204 | ISS-113 |
| L205 | ISS-112 |
| L206 | lessons.md §2.1 |
| L207 | ISS-115 |
| L208 | ISS-116 |
| L212 | ISS-117 |
| L213 | ISS-118 |
| L215 | ISS-120 |
| L216 | ISS-120 |
| L222 | ISS-121 |
| L223 | ISS-122 |
| L224 | ISS-123 |
| L225 | ISS-124 |
| L226 | ISS-125 |
| L227 | ISS-125 |
| L228 | lessons.md §6.3 |
| L231 | ISS-120 |
| L232 | ISS-119 |
| L233 | ISS-079 |
| L234 | ISS-054 |
| L236 | ISS-109 |
| L237 | ISS-110 |
| L239 | ISS-081 |
| L240 | ISS-106 |
| L242 | lessons.md §2.2 |
| L243 | lessons.md §2.3 |
| L244 | ISS-126 |
| L245 | ISS-126 |
| L246 | ISS-127 |
| L247 | ISS-127 |
| L248 | lessons.md §1.1 |
| L249 | ISS-081 |
| L250 | ISS-126 |
| L251 | lessons.md §7.1 |

> 说明：`parent` 行（L9/L15/L20/L23/L140）的实质内容由其子条目行承载；L212/L213 为 markdown 表格内容行（非 `-` bullet），一并登记。完整机器可读映射见 `.work/evidence/INFRA-032t/mapping.tsv`。

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-04）

逐行审查了 `issues.yaml` 新增 53 条、`lessons.md` 18 小节、7 处引用更新、证据脚本 3 类注入。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `lessons.md` 初稿含 6 个与 issue 重复的小节（1.2/2.4/3.2/3.3/5.4/5.5），与「每 bullet 一个归宿」不符 | ✅已修 | 删除这 6 节，保留 18 个与映射一一对应的小节 | `run.sh` → `lessons_anchors: all 18 anchors / all present`；`grep -c '```' lessons.md` = 0 |
| F2 证据脚本覆盖检查最初把「非 bullet 的映射行」（L212/L213）判为 extra-FAIL，致 ISS-117/118 报孤儿 | ✅已修 | 覆盖检查改为「bullets ⊆ mapping」（extra 仅报告）；补 mapping 行 L212/L213 | `run.sh` → `new_issues_referenced: ISS-075..ISS-127 all referenced`；`EVIDENCE: PASS` |
| F3 反例自检 C 的替换文本 `### 2.2 REMOVED` 仍匹配锚点正则，注入未生效（恒绿） | ✅已修 | 替换为无标题标记的 `REMOVED` | `--inject` → `inject__delete_lessons_section(2.2): actual=[True, True]`（先 FAIL 后 PASS） |
| F4 `check_asm_prose.py` 若只改 `_EXCLUDE_FILES` 而 docstring 留 `deferred.md`，语义不一致 | ✅已修 | 同步 docstring 扫描范围说明 | `make check` → `check-asm-prose: PASS (0 violations)` |
| F5 `issues.yaml` 既有 3 条（ISS-016/057/065）状态与 deferred.md 漂移（yaml open / deferred 已消解） | ✅已修 | 按 deferred 标 `closed` + `resolved_by`/`notes` | `check_issues: 100 open, 27 closed`；open/closed 计数变化已在完成区披露 |
| F6 任务书范围外的 8 处活引用 | ✅已修（经用户批准「更新所有非禁改活引用」） | 更新 7 处；`tests/vectors/schema.md` 禁改保留并披露 | `run.sh` → `live_refs_only_allowlisted: PASS` |
| F7 新增条目 schema（scope 非空 / resolved_by 规则 / id 唯一） | ✅已修 | — | `issues_parse_count`（127）/`issues_ids_unique`（127 unique）/`resolved_by rule OK` 均 PASS |

**判决**：所有 finding 已修，**建议「待验收」**（证据脚本默认 `EXIT=0`、`--inject` `EXIT=0`）。

### 第 1 轮 reviewer 验收（2026-10-04）

**逐项核验（独立重跑，真实命令 + 输出 + 退出码）**：

#### 1. issues.yaml 条数/schema/ID

```
$ python3 -c "import yaml,sys; d=yaml.safe_load(open('.tao/knowledge/issues.yaml')); print(len(d))"
127
EXIT=0
```

- count=127 ✅
- schema 合法（id/title/status/scope/blocks/resolved_by 必填、notes 可选；status∈{open,closed}；scope 非空；closed→resolved_by 非空、open→resolved_by=null）✅
- ID 唯一连续 ISS-001..ISS-127 ✅
- open=100 closed=27 ✅

#### 2. lessons.md + 映射表

- `lessons.md` 存在 ✅
- 18 个锚点（1.1/2.1/2.2/2.3/3.1/4.1/4.2/4.3/4.4/4.5/5.1/5.2/5.3/6.1/6.2/6.3/6.4/7.1）全部存在 ✅
- `grep -c '```' lessons.md` = 0（无围栏代码块，不影响 check_asm_prose）✅
- `mapping.tsv`（203 行）与任务书映射表**逐行一致**（Python 比对脚本输出 `MAPPING MATCH`）✅
- 抽查 5 条映射：
  - L46 → lessons.md §3.1（子代理异常返回须逐项扫描残留）✅
  - L47 → ISS-078（浮点指令未复核，open）✅
  - L48 → lessons.md §6.1（历史记录不改写正文）✅
  - L81 → ISS-016（make prepare 非幂等，closed，deferred.md 标 ✅已消解）✅
  - L165 → ISS-057（MemRAS 路径未实现，closed，deferred.md 标「已关闭」）✅

#### 3. deferred.md 删除 + git grep

```
$ test -f .tao/knowledge/deferred.md && echo "EXISTS" || echo "DELETED"
DELETED
EXIT=0
```

```
$ git grep -n 'deferred\.md' -- . ':(exclude).tao/archive/**' ':(exclude).tao/tasks/**'
（仅 changelog.md 多行历史条目、MEMORY.md 历史行、adr-0010 修订指针、tests/vectors/schema.md:228 禁改命中）
EXIT=0
```

逐类判定：
- changelog.md / MEMORY.md：历史台账条目，`HISTORY_PREFIXES` 覆盖，应留 ✅
- adr-0010：`## 修订` 指针 + D1–D4 未动，应留 ✅
- tests/vectors/schema.md：硬约束禁改 `tests/`，仅披露 ✅

#### 4. 证据脚本审查 + 重跑

**脚本审查**（`.work/evidence/INFRA-032t/check.py`）：
- 8 条检查项，每条均有明确 FAIL 条件（非恒真）✅
- 3 类注入（A 删 mapping 行 / B 删 issues 条目 / C 删 lessons 锚点），均在临时目录操作、不影响原文件 ✅
- 注入后通过 `run_checks(原文件)` 还原验证 ✅
- 结尾用 `sys.exit(main())` 传递退出码，未用 `tee` 吞退出码 ✅

**默认重跑**：
```
$ bash .work/evidence/INFRA-032t/run.sh
[PASS] issues_parse_count: expected='127' actual='127' rc=0
[PASS] issues_ids_unique: expected='unique' actual='127 ids / 127 unique' rc=0
[PASS] deferred_deleted: expected='absent' actual='absent' rc=0
[PASS] lessons_anchors: expected='all 18 anchors' actual='all present' rc=0
[PASS] coverage_bullets_mapped: expected='201 bullets' actual='unmapped=[] extra=[212, 213]' rc=0
[PASS] mapping_issue_dests_exist: expected='all issue dests in issues.yaml' actual='all exist' rc=0
[PASS] mapping_lesson_dests_exist: expected='all lesson anchors in lessons.md' actual='all exist' rc=0
[PASS] new_issues_referenced: expected='ISS-075..ISS-127 all referenced' actual='all referenced' rc=0
[PASS] live_refs_only_allowlisted: expected='only historical/forbidden-file hits' actual='ok (historical + tests/vectors/schema.md)' rc=0
EVIDENCE: PASS EXIT=0
run.sh EXIT=0
EXIT=0
```

**--inject 重跑**：
```
$ bash .work/evidence/INFRA-032t/run.sh --inject
[PASS] inject__delete_mapping_row: coverage expected FAIL then PASS actual=[True, True] rc=0
[PASS] inject__delete_issues_entry(ISS-100): dests expected FAIL then PASS actual=[True, True] rc=0
[PASS] inject__delete_lessons_section(2.2): anchors expected FAIL then PASS actual=[True, True] rc=0
run.sh EXIT=0
EXIT=0
```

**独立反例注入**（reviewer 自行注入，改 issues.yaml 删 ISS-050）：
```
$ python3 inject_script.py
ORIGINAL sha256: 5e72590fdc0e0c48dd0ff76d27211dd5d87710d3d3457e779d3c7c6c4708ab10
INJECTED: removed ISS-050, file sha256: 877eaffd23b288aee208679a41c11bfbf9d80097828573f39d251413c7d2f990
[FAIL] mapping_issue_dests_exist: expected='all issue dests in issues.yaml' actual="missing=['ISS-050']" rc=1
EVIDENCE: FAIL EXIT=1
RESTORED sha256: 5e72590fdc0e0c48dd0ff76d27211dd5d87710d3d3457e779d3c7c6c4708ab10
SHA MATCH: OK
EVIDENCE: PASS EXIT=0
```
注入→FAIL EXIT=1 → SHA 还原 → PASS EXIT=0 ✅

#### 5. make check

```
$ JOBS=8 make check
（lit 29/29、check_issues: 100 open 27 closed、repository checks: PASS）
EXIT=0
```

#### 6. 越界判定

| 文件 | 改动 | 判定 |
|---|---|---|
| contract-isa.md | L828/L1142 `deferred.md` → `issues.yaml` | 必要活引用更新 ✅ |
| milestones.md | L56 `deferred.md` → `issues.yaml` | 必要活引用更新 ✅ |
| MEMORY.md | 关键目录速查行 `deferred.md` → `issues.yaml`+`lessons.md` | 必要活引用更新 ✅ |
| AGENTS.md | L131 `deferred.md` → `.tao/knowledge/issues.yaml` | 必要活引用更新 ✅ |
| docs/impact-matrix.md | L204 引用列 → `issues.yaml` | 必要活引用更新 ✅ |
| generate_isa_vectors.py | L1073/1090/1501 注释 → `issues.yaml` | 必要活引用更新 ✅ |
| adr-0010 | 仅追加 `## 修订` 段（+4 行），D1–D4 未动 | 必要活引用更新 ✅ |

所有越界改动均为 `deferred.md` → `issues.yaml`/`lessons.md` 的指针更新，无过度改动。

#### 7. ISS-016/057/065 状态变更

| ID | deferred.md 标记 | issues.yaml 变更 | 判定 |
|---|---|---|---|
| ISS-016 | L81: ✅已消解（2026-09-23，补丁集重整） | open→closed + resolved_by | 依据充分 ✅ |
| ISS-057 | L165: 已关闭（2026-09-30 核实，QEMU-013t 实现） | open→closed + resolved_by | 依据充分 ✅ |
| ISS-065 | L173: ✅已消解（2026-09-23，补丁集重整） | open→closed + resolved_by | 依据充分 ✅ |

#### 约束核验

| 约束 | 结果 |
|---|---|
| 不改 `.tao/archive/**` | ✅ 未改 |
| 不丢失信息 | ✅ issues.yaml + lessons.md 完整承载 |
| `check_scope.py` 仅改 HISTORY_PREFIXES 一行 | ✅ 仅 `-`/`+` 各 1 行 |
| 不改 `contracts/`、`components/`、`tests/`、`spec/SimRISC-*` | ✅ 未改 |
| 临时目录 `/tmp/opencode/INFRA-032t/` | ✅ review 用 `/tmp/opencode/INFRA-032t-review/` |
| 不提交 git | ✅ 未提交 |
| 复杂命令输出留存 `.work/log/` | ✅ engineer 已留 |

#### 判决

**Accepted**。全部 7 项验收标准通过、约束无违反、独立反例注入证实脚本可失败。

遗留（供主会话知晓，不阻断）：
- `tests/vectors/schema.md:228` 仍指 `deferred.md`（硬约束禁改 `tests/`，仅披露，需另立可改 `tests/` 的任务消解）。

### 第 1 轮 architect 交叉复核（2026-10-04，双模型互验）

**复核范围**：对照任务书目标/约束/验收，独立重跑并抽查 reviewer 验收有无遗漏/过严/过松。临时目录 `/tmp/opencode/INFRA-032t-xcheck/`；未改任何产物；未提交 git。

#### 1. 信息不丢失（最关键）——独立抽查 18 条 bullet（覆盖 spec/infra/testcases/llvm-qemu-integ/2026-10-02）

以 `git show HEAD:.tao/knowledge/deferred.md` 取回原文（251 行），以映射键重算：`bullets(regex)=201`、`unmapped=[]`、`extra=[212,213]`。逐条内容对照（原文要点 → 新位置）：

| L | 原文要点 | 归宿（真实内容核对） |
|---|---|---|
| L34 | 浮点 soft-float libcall 路线 | `ISS-004` open，title 保留「以 soft-float libcall 接入」✅ |
| L40 | 编码表下游影响 / legality 规则仍 active | `ISS-010` open，title 一致 ✅ |
| L46 | 子代理异常返回须逐项扫描残留 | `lessons.md §3.1` 全文一致 ✅ |
| L71 | check-qemu-semantics gate 目录瞬态 | `ISS-089` open + notes「原 backlog L71」✅ |
| L81 | make prepare 非幂等「✅已消解」 | `ISS-016` **closed** + resolved_by + notes「原 backlog L81 标 ✅已消解」✅ |
| L82 | 行内 code span 检测 deferred | `ISS-093` open + notes ✅ |
| L90 | reg-imm-block 重叠已消解 | `ISS-096` **closed** + resolved_by TESTCASES-023t ✅ |
| L131 | M1 rd2rd/rb2rb 不等 count 静默取末组 | `ISS-104` open + notes ✅ |
| **L132** | **FP 汇编期静态检查 ✅ 已完成 + 「余下 FP 衔接点」** | `ISS-105` **closed**（已完成部分）✅；仍 open 的余下衔接点由 `ISS-081`/`ISS-084` 承载（见下方发现 C） |
| L165 | MemRAS 路径「已关闭」 | `ISS-057` **closed** + notes/reason ✅ |
| L174–184 | fence 已由 ADR-0014/SPEC-039t 处置 | `ISS-056` **closed** + notes「不再是缺陷」✅ |
| L204 | check_interface_alignment 非递归 glob 已消解 | `ISS-113` **closed** ✅ |
| L212/L213 | e_flags 注释误命中 / lit 粒度限制 | `ISS-117`/`ISS-118` open ✅ |
| L222 | excp_rasof/rasuf 旧 MemRAS 模型 | `ISS-121` open + notes ✅ |
| L226 | 生成器↔向量预存漂移 | `ISS-125` open + notes「L226/L227」✅ |
| L228 | 合法性渲染格式确认门 ② | `lessons.md §6.3` 全文一致 ✅ |
| L242 | 合并反例注入互相抵消 | `lessons.md §2.2` ✅ |
| L251 | softfloat default_nan_pattern | `lessons.md §7.1` ✅ |

**结论：抽查 18 条（含 ≥1 条已消解+仍 open 混排 L132）均无信息丢失**；`ISS-016/057/065` 的状态漂移闭合与 deferred 的「✅已消解/已关闭」标注一致，依据充分。

#### 2. 约束遵守

```
$ git diff --name-only HEAD -- .tao/archive contracts components tests 'spec/SimRISC-*' .tao/tasks
（空）
$ git diff HEAD -- tools/spec/check_scope.py
-    ".tao/knowledge/deferred.md",
+    ".tao/knowledge/lessons.md",
（仅 HISTORY_PREFIXES 一行，断言逻辑未动）
```
✅ 禁改路径全零改动；`check_scope.py` 仅改一行。`contracts/`、`components/`、`tests/`、`spec/SimRISC-*` 均未动。

#### 3. 越界判定（逐条核）

| 文件 | diff 实质 | 判定 |
|---|---|---|
| contract-isa.md | 仅 L828/L1142 `deferred.md`→`issues.yaml` 指针 | 必要 ✅ |
| milestones.md | 仅 L56 指针 | 必要 ✅ |
| MEMORY.md | 仅「关键目录速查」live 行 + 2 行（`deferred.md`→`issues.yaml`+`lessons.md`） | 必要 ✅ |
| AGENTS.md | 仅 L131 指针 | 必要 ✅ |
| docs/impact-matrix.md | 仅 L204 引用列指针 | 必要 ✅ |
| generate_isa_vectors.py | 仅 3 处注释指针（L1073/1090/1501） | 必要 ✅ |
| adr-0010 | **仅追加 `## 修订`（+4 行）**，`grep '^[-+]'` 无 D1–D4 改动 | 必要 ✅ |
| check_asm_prose.py | docstring 扫描范围说明 + `_EXCLUDE_FILES` 条目各 1 处 | 必要 ✅ |
| spec/Process-04 | L66「遗留台账」行 | 必要 ✅ |

✅ 无过度改动；`tools/infra/check_issues.py`/`docs/README.md`/`spec/Toolchain-01` 属本轮归档前置改动（`git mv` 路径同步），非本任务过度越界（已在完成区披露）。

#### 4. `make check` 独立重跑

```
$ JOBS=8 make check                       # 独立重跑
  Passed: 29 (100.00%)                    # lit 29/29
check_issues: 100 open, 27 closed (0 blocking M1-gate: 0)
repository checks: PASS
EXIT=0
```

#### 5. 证据脚本独立重跑

```
$ bash .work/evidence/INFRA-032t/run.sh            → EVIDENCE: PASS EXIT=0（9/9 PASS）
$ bash .work/evidence/INFRA-032t/run.sh --inject   → 3 类注入均「预期 FAIL→还原→回绿」EXIT=0
```
独立复算：新条目 `ISS-075..ISS-127` **全部被映射引用**、全部 issue 目的地存在、18 个 lesson 锚点存在、`mapping.tsv`（203 数据行）与任务书映射表**逐行一致**。reviewer 已做的独立注入（删 `ISS-050` → FAIL EXIT=1 → sha 还原 → PASS）记录与真实一致，未重复。

#### 补充发现（均**不阻断**，判为可接受）

- **发现 A（追溯性小瑕）**：原 deferred 的「2026-10-02」表共 **3 个内容行（L212/L213/L214）**，完成区记为「2 个 markdown 表格内容行」。`L214`（`new file mode` 补丁 index 失配）未进入 `mapping.tsv`（也无 214 行），但其内容已由 `ISS-119` 承载（`notes: 原 backlog L214/L232`）——**无信息丢失**，仅机器映射少一行。
- **发现 B（追溯性小瑕）**：`L97`（`>` 引用的 TESTCASES 最终裁决）非 bullet，未列入映射，但内容已完整落在 `lessons.md §6.2`。**无信息丢失**。
- **发现 C（混排 bullet 的映射粒度）**：`L132` 同时含「已完成（LLVM-030t）」与「仍 open 的 FP 衔接点」；映射仅记 `ISS-105`（closed），其 open 部分未在该单元格标注，而由 `ISS-081`/`ISS-084`（另经 `L53/L138/L239/L249` 映射）承载。**内容不丢**，但 L132 的「拆」在映射表上未显式体现。
- **发现 D（口径交叉）**：`ISS-004` 保留 deferred L34 的「soft-float libcall」措辞（现已被用户 2026-10-03 的「原生浮点」裁定取代，后者见 `ISS-081`）。两者并存、**无冲突丢失**；如需可择机在 ISS-004 补一句 superseded 指向（非本任务必需）。

#### 判决

**确认 Accepted**。7 项验收标准逐条通过、约束无违反、`make check` EXIT=0、证据脚本默认/注入均 EXIT=0、18 条 bullet 独立抽查无信息丢失、`check_scope.py` 仅改一行、adr-0010 D1–D4 未动。补充发现 A–D 均为**追溯性/表述层面**小瑕，不影响「信息不丢失」与门控结论，不构成返工理由。
