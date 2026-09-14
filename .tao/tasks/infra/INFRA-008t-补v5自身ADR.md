# INFRA-008t: 补 v5 自身 ADR（0001 greenfield / 0002 构建编排）

**模块**：infra
**项目里程碑**：M1
**依赖**：无
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`.tao/knowledge/adr-authoring.md`（ADR 格式与模板）、DADAO-0628 `docs/adr/0001-greenfield-rebuild.md` 与 `docs/adr/0002-build-orchestration.md`（内容溯源）、各 infra 任务书的「设计理由 / 关键概念」
- 输出：`.tao/knowledge/adr-0001-greenfield-rebuild.md`、`.tao/knowledge/adr-0002-build-orchestration.md`
- 约束：按 `adr-authoring.md` 格式（Status/Context/Decision/Rationale/Consequences，中文，Status 先 `Candidate`）；采纳 0628 决策为 **v5 自己的决策**并写成 v5 版本（0.5.3、`.work/`、`.cache/`、`manifests/` 等 v5 约定）；**不照抄 0628 正文**（内容溯源）；不写行号

## 背景（完整）

### 目标

v5 多处文档（`INFRA-002t`/`003t`/`004t`/`006t`、`docs/repository-layout.md`）引用 **ADR-0002（构建编排）**，但 v5 自身并无 `adr-0002-*.md`（`.tao/knowledge/` 只有 `adr-authoring.md` 模板）；且编号上 ADR-0001/0002 无人创建（spec 产出 0003/0004、llvm/qemu 产出 0005/0006）。本任务补 v5 自身的 ADR-0001/0002，并把这些引用改指向 v5 版本。

### 设计理由

- **任务自包含**（项目 `AGENTS.md`「参考来源与任务自包含」）：v5 文档不得把 0628 的 ADR 当权威；模板/格式以 v5 自身知识为准。
- ADR-0002 的决策（Make 用户接口 + Python 标准库处理 manifest、一次性数据在 `.work/`、按完整 commit 获取 + 单一有序补丁序列）已在 v5 infra 任务中落地（`INFRA-003t`~`006t`），需固化为 v5 的 ADR。
- ADR-0001（greenfield 重建）是项目定位决策，v5 沿用。
- **v5 新增**：`INFRA-004t` 引入 `.cache/` 持久 bare mirror + `.work/` 可再生工作树，避免重下大仓库（LLVM/QEMU/gem5）；这是对 0628 构建编排的扩展，须写入 v5 的 ADR-0002。

### 关键概念 / 数据

- ADR 格式：见 `.tao/knowledge/adr-authoring.md`。
- 0628 `docs/adr/0002-build-orchestration.md` 决策：Make 稳定接口 + Python 标准库；一次性数据在 `.work/`；每组件按完整 commit + 单一有序补丁序列；否决环境相关 URL 重写、按可变分支选版本、未审查 fixups、把上游仓库拷进 meta-repo、把脏生成树当权威实现。
- 0628 `docs/adr/0001-greenfield-rebuild.md`：greenfield 重建定位（内容溯源）。
- v5 约定：`.work/`（一次性工作区，可整体清理）、`.cache/`（持久 bare mirror：组件 `.cache/<name>.git`、参考 `.cache/refs/<id>.git`）、`manifests/`（锁）、`components/`（有序补丁序列）。
- **v5 新增决策（须写入 adr-0002）**：**持久 mirror + 可再生工作树**——上游组件/参考仓库先做 bare mirror 到 `.cache/`（只增量 `fetch`），工作树从本地 mirror 建到 `.work/`（硬链接，可随 `.work` 清空重建、**不重下大仓库**）；`clean_work` 只清 `.work/`、不碰 `.cache/`。

### 上游引用

- DADAO-0628 `docs/adr/0001-greenfield-rebuild.md`、`docs/adr/0002-build-orchestration.md`（内容溯源，非执行必需）。
- 本项目：`.tao/knowledge/adr-authoring.md`、`docs/repository-layout.md`、`.tao/tasks/infra/INFRA-00{2,3,4,6}t-*.md`。

## 交付物

- `.tao/knowledge/adr-0001-greenfield-rebuild.md`：v5 greenfield 重建定位（Status 先 Candidate）。
- `.tao/knowledge/adr-0002-build-orchestration.md`：v5 构建编排决策（Make + Python 标准库、`.work/` 一次性数据、按完整 commit + 单一有序补丁序列、否决项），**并记录 v5 新增的 `.cache/` 持久 bare mirror + `.work/` 可再生工作树决策**（避免重下大仓库）。
- **引用更新**：把 `INFRA-002t`/`003t`/`004t`/`006t` 与 `docs/repository-layout.md` 中对「ADR-0002」的引用指向 v5 `.tao/knowledge/adr-0002-build-orchestration.md`（原文只写 "ADR-0002" 处补明 v5 路径）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- 无 ISA 相关差异。
- v5 新增 `.cache/`（持久 bare mirror）+ `.work/` 可再生工作树，ADR-0002 须体现（0628 无；0628 直接 clone 到 `.work/source`，无持久 mirror）。
- ADR 落点：v5 在 `.tao/knowledge/`（0628 在 `docs/adr/`）。

## 已知坑 / 结论

- 不要把 0628 的 ADR 正文照抄进来；只采纳决策并写成 v5 版本。
- Status 先 `Candidate`，评审后 `Accepted`（见 `adr-authoring.md` 流程）。
- 引用更新是最小改动：不改任务书实质内容，只让 ADR 引用可定位。

## 参考

- DADAO-0628：`.work/DADAO-0628/docs/adr/0001-greenfield-rebuild.md`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0002-build-orchestration.md`
- 本项目：`.tao/knowledge/adr-authoring.md`、`docs/repository-layout.md`

## 验收标准

1. `.tao/knowledge/adr-0001-greenfield-rebuild.md`、`adr-0002-build-orchestration.md` 存在，按 `adr-authoring.md` 格式（含 Status/Context/Decision/Rationale/Consequences），Status 先 `Candidate`
2. `adr-0002` 含 v5 决策：Make + Python 标准库、`.work/` 一次性数据、按完整 commit + 单一有序补丁序列、否决项，以及 v5 新增的 `.cache/` 持久 bare mirror + `.work/` 可再生工作树
3. `INFRA-002t`/`003t`/`004t`/`006t`、`docs/repository-layout.md` 的 ADR-0002 引用指向 v5 `.tao/knowledge/adr-0002-build-orchestration.md`
4. 未照抄 0628 ADR 正文（内容溯源）

## 完成区

> **注（2026-09-13 修订）**：ADR-0001/0002 后续经用户重判修订并置 `Accepted`——ADR-0001 D3 补边界说明（spec 无依据的机器/ABI 约定不属「行为期望」）；ADR-0002 D2 措辞澄清（「日志」→「构建/组件日志」+ agent 日志在 `.tao/logs/`）。二者均为追加/澄清，未推翻既有决策，本任务验收结论不受影响；当前值以 `.tao/knowledge/adr-0001-greenfield-rebuild.md`、`.tao/knowledge/adr-0002-build-orchestration.md` 为准。

**测试结果**：通过 4/4（对应「验收标准」1–4）；失败原因：无。验证脚本 `/tmp/opencode/INFRA-008t/verify.sh`，完整输出 `.tao/logs/INFRA-008t-verify.log`，`RESULT=PASS`、`PIPELINE_EXIT=0`。

**修改文件**：
- `.tao/knowledge/adr-0001-greenfield-rebuild.md`（新建）
- `.tao/knowledge/adr-0002-build-orchestration.md`（新建）
- `docs/repository-layout.md`（修改：ADR-0002 引用补明 v5 路径）
- `.tao/tasks/infra/INFRA-002t-仓库与构建骨架.md`（修改：同上）
- `.tao/tasks/infra/INFRA-003t-manifest与锁系统.md`（修改：同上）
- `.tao/tasks/infra/INFRA-004t-组件获取与打补丁工具.md`（修改：同上）
- `.tao/tasks/infra/INFRA-006t-Makefile编排.md`（修改：同上，含历史审阅记录内 1 处引用）

**验收结果**（真实终端输出，日志 `.tao/logs/INFRA-008t-verify.log`）：

```bash
$ bash /tmp/opencode/INFRA-008t/verify.sh 2>&1 | tee .tao/logs/INFRA-008t-verify.log; echo "PIPELINE_EXIT=${PIPESTATUS[0]}"

=== [1] deliverable files exist ===
OK  exists: .tao/knowledge/adr-0001-greenfield-rebuild.md (2005 bytes)
OK  exists: .tao/knowledge/adr-0002-build-orchestration.md (4324 bytes)

=== [2] ADR format fields (per adr-authoring.md) ===
--- .tao/knowledge/adr-0001-greenfield-rebuild.md ---
# ADR-0001: Greenfield 重建
**状态**：Candidate
**日期**：2026-09-12
OK   field: ^# ADR-[0-9][0-9][0-9][0-9]: 
OK   field: ^\*\*状态\*\*：Candidate$
OK   field: ^\*\*日期\*\*：
OK   field: ^\*\*关联\*\*：
OK   field: ^## Context（背景）$
OK   field: ^## Decision（决策）$
OK   field: ^## Rationale（理由）$
OK   field: ^## Consequences（影响）$
OK   field: ^## 状态说明$
--- .tao/knowledge/adr-0002-build-orchestration.md ---
# ADR-0002: Manifest 驱动的构建编排
**状态**：Candidate
**日期**：2026-09-12
（Context/Decision/Rationale/Consequences/状态说明 全部 OK）

=== [3] ADR-0002 required v5 decisions ===
OK   contains: Make
OK   contains: Python 标准库
OK   contains: `.work/`
OK   contains: 完整 40 位 commit
OK   contains: 单一有序补丁序列
OK   contains: `.cache/<name>.git`
OK   contains: `.cache/refs/<id>.git`
OK   contains: clean_work
OK   contains: 可再生工作树
OK   contains: 离线重建
OK   contains: 否决
--- rejected behaviours (D6) ---
OK   rejected listed: URL 重写
OK   rejected listed: 可变分支
OK   rejected listed: fixups
OK   rejected listed: 拷贝进 meta-repository
OK   rejected listed: 脏的生成源码树

=== [4] references point to v5 adr-0002 path ===
--- docs/repository-layout.md ---
ADR-0002 occurrences: 1
OK   all ADR-0002 refs carry v5 path
--- .tao/tasks/infra/INFRA-002t-仓库与构建骨架.md ---
ADR-0002 occurrences: 1
OK   all ADR-0002 refs carry v5 path
--- .tao/tasks/infra/INFRA-003t-manifest与锁系统.md ---
ADR-0002 occurrences: 1
OK   all ADR-0002 refs carry v5 path
--- .tao/tasks/infra/INFRA-004t-组件获取与打补丁工具.md ---
ADR-0002 occurrences: 1
OK   all ADR-0002 refs carry v5 path
--- .tao/tasks/infra/INFRA-006t-Makefile编排.md ---
ADR-0002 occurrences: 2
OK   all ADR-0002 refs carry v5 path

=== [5] anti-verbatim check vs DADAO-0628 ADRs ===
（两个 v5 ADR 对 0628 的 5 条英文决策句全部 OK not copied）

=== [6] working tree changes (informational) ===
 M .tao/tasks/infra/INFRA-002t-仓库与构建骨架.md
 M .tao/tasks/infra/INFRA-003t-manifest与锁系统.md
 M .tao/tasks/infra/INFRA-004t-组件获取与打补丁工具.md
 M .tao/tasks/infra/INFRA-006t-Makefile编排.md
 M docs/repository-layout.md
?? .tao/knowledge/adr-0001-greenfield-rebuild.md
?? .tao/knowledge/adr-0002-build-orchestration.md

RESULT=PASS
PIPELINE_EXIT=0
```

补充：`git log --oneline -1` = `dbe2b48 docs: INFRA-008t 纳入 .cache mirror 决策`（未产生新提交）；`git status` 仅显示上列 5 改 + 2 新增，未触碰其它文件。

**验收标准逐条自审**：
1. 两个 ADR 存在，按 `adr-authoring.md` 格式（`# ADR-<nnnn>: <标题>` + `**状态**`/`**日期**`/`**关联**` + Context/Decision/Rationale/Consequences/状态说明），Status 均为 `Candidate` —— ✅ 通过（verify [1][2]）
2. `adr-0002` 含 Make + Python 标准库、`.work/` 一次性数据、完整 40 位 commit + 单一有序补丁序列、五项否决项，以及 v5 新增的 `.cache/<name>.git` / `.cache/refs/<id>.git` 持久 bare mirror + `.work/` 可再生工作树（离线重建、`clean_work` 不删 `.cache/`）—— ✅ 通过（verify [3]）
3. `INFRA-002t`/`003t`/`004t`/`006t`、`docs/repository-layout.md` 的全部 ADR-0002 引用均携带 v5 路径 `.tao/knowledge/adr-0002-build-orchestration.md`（006t 含历史审阅记录 1 处，共 2 处）—— ✅ 通过（verify [4]）
4. 未照抄 0628 ADR 正文（5 条英文决策句逐句比对均未出现；v5 版为中文重写并加入 v5 约定）—— ✅ 通过（verify [5]）

**新发现/坑**：
- **内容溯源而非照抄**：0628 两份 ADR 极短且为英文，v5 版以中文重写并显式补入 v5 约定（0.5.3、`.cache/`、`clean_work`、`reference-only` 锁），未逐字复制任何句子（verify [5] 逐句核对）。
- **v5 与 0628 的实质差异**：0628 无持久 mirror（直接 clone 到 `.work/source`）；v5 新增 `.cache/` 持久 bare mirror + 可再生工作树，已在 ADR-0002 D5 单列。
- **`INFRA-006t` 历史审阅记录（第 570 行附近）也含 1 处 ADR-0002 引用**，本次一并补明 v5 路径（仅引用措辞，未改实质内容），故该文件 `ADR-0002` 出现 2 次。
- **越界引用（未处置，非本任务范围）**：`INFRA-001k-模块启动与任务分解.md` 第 18 行仍有裸引用「ADR-0001（greenfield 重建）、ADR-0002（manifest 驱动编排）」。该文件不在任务「交付物/引用更新」列出的文件内，按约束「不得修改任务文档未列出的文件」**未改动**；如需补明可另开任务。
- **`SPEC-006t` 引用 `adr-0001` 风格**：`SPEC-006t-Test-Machine-ADR.md` 第 25 行有「格式遵循 `adr-0001` 风格」，同样不在本任务范围内，未改动。
- **`.cache/` 与 `.work/` 清理职责**是易错点，ADR-0002 在 D5 与 Consequences 两处强调 `clean_work` 不碰 `.cache/`，避免误删导致重下大仓库。
- 两个 ADR 的 Status 仍为 `Candidate`，需评审后由主会话置 `Accepted`（`adr-authoring.md` 流程）。

**遗留问题**：无（`INFRA-001k`/`SPEC-006t` 的裸引用属任务明确范围之外，已在「新发现/坑」记录）。

## 审阅记录

### 第 1 轮 engineer 自审（自主自审，嵌套受限）

**自审者**：engineer
**时间**：2026-09-12
**方式**：尝试开 `general` subagent 做代码级 review，返回 `Subagent depth limit reached (1)`，按规则降级为**自主自审（嵌套受限）**：逐行审查新增/修改文件、独立重跑验证脚本、核对 diff 与 git 状态。

#### 逐项审查

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 格式合规（字段/Status/日期） | ✅通过 | 无 | verify [2] 全部字段命中，Status=Candidate |
| F2 ADR-0002 决策完整性 | ✅通过 | 无 | verify [3] 关键词与五项否决全部命中 |
| F3 引用全部指向 v5 路径 | ✅通过 | 无 | verify [4] 5 文件 6 处引用全带 v5 路径，无裸引用 |
| F4 未照抄 0628 正文 | ✅通过 | 无 | verify [5] 5 条英文句逐句未出现 |
| F5 改动范围仅限列出文件 | ✅通过 | 无 | `git status` 仅 5 改 + 2 新增；未碰 `INFRA-001k`/其它 knowledge 文件 |
| F6 历史段落仅改引用措辞 | ✅通过 | 无 | `git diff` 显示 006t 历史段仅插入 v5 路径，无其它改动 |
| F7 未执行 git commit | ✅通过 | 无 | `git log -1` 仍为 `dbe2b48`，无新提交 |
| F8 无行号写入 ADR | ✅通过 | 无 | 两个 ADR 正文无行号引用 |

#### 防造假核对

- verify [1]–[6] 均为 `verify.sh` 真实终端输出，`tee` 落盘 `.tao/logs/INFRA-008t-verify.log`，`PIPELINE_EXIT=0`。
- `git diff`/`git status`/`git log` 均真实执行，改动文件与声称一致。
- 未执行 `git commit`；未修改任务书实质内容（仅补明 ADR 引用路径）。

#### 判决

**自主自审通过**：无未修 finding，4/4 验收标准满足，改动范围与约束一致。任务状态置 `待验收`，交主会话 `/complete` 由 reviewer 独立验收。

---

### 第 2 轮 reviewer 独立验收

**审查者**：reviewer（独立）
**时间**：2026-09-12
**方式**：独立读取所有交付物、独立运行验证命令、与 0628 ADR 逐段对比、全仓搜索引用

#### 一、文件存在性与格式

**验证命令**：
```bash
$ ls -la .tao/knowledge/adr-000{1,2}-*.md
-rw-rw-r-- 1 ubuntu docker 2005 Sep 12 11:40 .tao/knowledge/adr-0001-greenfield-rebuild.md
-rw-rw-r-- 1 ubuntu docker 4324 Sep 12 11:40 .tao/knowledge/adr-0002-build-orchestration.md
```

**格式逐字段核对**（对照 `adr-authoring.md` 模板）：

| 字段 | ADR-0001 | ADR-0002 | 模板要求 |
|------|----------|----------|---------|
| `# ADR-<nnnn>: <标题>` | `# ADR-0001: Greenfield 重建` ✅ | `# ADR-0002: Manifest 驱动的构建编排` ✅ | 四位编号 |
| `**状态**` | `Candidate` ✅ | `Candidate` ✅ | 先 Candidate |
| `**日期**` | `2026-09-12` ✅ | `2026-09-12` ✅ | YYYY-MM-DD |
| `**关联**` | ADR-0002/README.md/AGENTS.md/INFRA-008t ✅ | ADR-0001/manifests/docs/repository-layout.md/INFRA-002t~008t ✅ | 相关 ADR/任务 |
| `## Context（背景）` | ✅ | ✅ | 必需 |
| `## Decision（决策）` | D1-D3 ✅ | D1-D6 ✅ | 必需 |
| `## Rationale（理由）` | ✅ | ✅ | 必需 |
| `## Consequences（影响）` | ✅ | ✅ | 必需 |
| `## 状态说明` | ✅ | ✅ | 必需 |

**结论**：两个 ADR 格式完全符合 `adr-authoring.md` 模板，Status 均为 `Candidate`。✅ 通过

#### 二、ADR-0002 决策完整性

**验证命令**：`rg` 搜索关键内容

| 要求 | 命中 | 出处 |
|------|------|------|
| Make | ✅ | D1「Make 作为统一入口」 |
| Python 标准库 | ✅ | D1「Python 标准库脚本；不引入第三方 Python 依赖」 |
| `.work/` 一次性数据 | ✅ | D2「一次性数据集中在 `.work/`」 |
| 完整 40 位 commit | ✅ | D3「完整 40 位 commit」 |
| 单一有序补丁序列 | ✅ | D4「单一有序补丁序列」 |
| `.cache/<name>.git` | ✅ | D5「上游组件 bare mirror 落在 `.cache/<name>.git`」 |
| `.cache/refs/<id>.git` | ✅ | D5「参考仓库 bare mirror 落在 `.cache/refs/<id>.git`」 |
| clean_work | ✅ | D5「`clean_work` 只清 `.work/`，不删除 `.cache/`」 |
| 可再生工作树 | ✅ | D5「可再生工作树」 |
| 离线重建 | ✅ | D5「可随 `.work` 清空重建、离线重建」 |
| 否决项（5 条） | ✅ | D6 列出全部 5 条 |

**结论**：v5 新增决策（`.cache/` 持久 bare mirror + 可再生工作树）在 D5 单列，与 0628 的实质差异（0628 直接 clone 到 `.work/source`、无持久 mirror）已体现。✅ 通过

#### 三、未照抄 0628

**比对方法**：逐段对比 0628 `docs/adr/0001-greenfield-rebuild.md`（20 行英文）与 `0002-build-orchestration.md`（17 行英文）与 v5 版本。

**ADR-0001 对比**：
- 0628：20 行，英文，四段（Context/Decision/Consequences），无 Rationale、无日期/关联
- v5：32 行，中文，完整六段（含 Rationale/状态说明），有日期/关联，引用 SimRISC 0.5.3/manifests/contract-*.md
- 逐句核对：v5 未出现 0628 的任何英文原文句（`Legacy implementations contain assumptions...` 等均未出现）

**ADR-0002 对比**：
- 0628：17 行，英文，两段（Decision/Rejected Legacy Behavior），极简
- v5：45 行，中文，六段完整，D1-D6 逐条展开，含 Rationale/Consequences/状态说明，D5 为 v5 新增
- 0628 Decision 五条英文句：`Use Make as...`、`Keep all disposable...`、`Fetch each component...`、`Environment-specific...`、`Version selection...` — v5 ADR-0002 正文中均未出现

**结论**：v5 版本为中文重写，结构完整，引入 v5 约定（0.5.3、`.cache/`、`manifests/`、`contract-*.md`），未逐字复制 0628。✅ 通过

#### 四、引用更新

**验证命令**：
```bash
$ rg -rn 'ADR-0002' .tao/tasks/ --no-heading | grep -v INFRA-008t
.tao/tasks/infra/INFRA-004t-组件获取与打补丁工具.md:...（v5：`.tao/knowledge/adr-0002-build-orchestration.md`）...
.tao/tasks/infra/INFRA-003t-manifest与锁系统.md:...（v5：`.tao/knowledge/adr-0002-build-orchestration.md`）...
.tao/tasks/infra/INFRA-006t-Makefile编排.md:...（v5：`.tao/knowledge/adr-0002-build-orchestration.md`）...  (2 处)
.tao/tasks/infra/INFRA-002t-仓库与构建骨架.md:...（v5：`.tao/knowledge/adr-0002-build-orchestration.md`）...
```

```bash
$ rg -n 'ADR-0002' docs/repository-layout.md --no-heading
6:加有序补丁序列完全复现（参考 v5 ADR-0002 `.tao/knowledge/adr-0002-build-orchestration.md`：一次性数据集中在 `.work/`）。
```

**git diff 确认**：所有 5 个文件的改动均为插入 `（v5：`.tao/knowledge/adr-0002-build-orchestration.md`）`，未改实质内容。

**结论**：任务列出的 5 个文件的全部 ADR-0002 引用均携带 v5 路径，006t 含历史审阅记录共 2 处。✅ 通过

#### 五、改动范围与越界检查

**git diff --stat HEAD**：
```
 6 files changed, 144 insertions(+), 10 deletions(-)
```

- 5 个引用更新文件（各 +1 行/1 处改动）
- INFRA-008t 任务文件自身（+142 行，完成区/审阅记录内容）
- 2 个新文件（adr-0001/0002）为 `??` 状态

**git log**：
```
dbe2b48 docs: INFRA-008t 纳入 .cache mirror 决策
```
未产生新提交。✅

**结论**：改动范围严格限于任务列出的文件 + 任务文件自身的完成区填写，未触碰其它文件，未执行 git commit。✅ 通过

#### 六、额外核查：全仓 ADR-0002 裸引用

**全仓搜索**：
```bash
$ rg -n 'ADR-0002' --no-heading
docs/repository-layout.md:6:...（v5 路径）...
Makefile:3:# Make is the stable user interface (ADR-0002); the actual manifest/fetch/patch

$ rg -rn 'ADR-0002' .tao/tasks/ --no-heading | grep -v '\.tao/knowledge/adr-0002'
.tao/tasks/infra/INFRA-001k-模块启动与任务分解.md:18:...ADR-0001（greenfield 重建）、ADR-0002（manifest 驱动编排）。
```

**发现的裸引用（未指向 v5 路径）**：

| 文件 | 引用内容 | 任务范围 | 判断 |
|------|---------|---------|------|
| `Makefile` 第 3 行 | `ADR-0002`（代码注释） | 未列出 | 超出范围 |
| `INFRA-001k` 第 18 行 | `ADR-0002（manifest 驱动编排）` | 未列出 | 超出范围 |

**SPEC-006t** 第 25 行有 `adr-0001` 引用（小写，格式风格引用），与 ADR-0002 无关。

**reviewer 意见**：

1. **`INFRA-001k` 裸引用**：该文件第 18 行 `ADR-0001（greenfield 重建）、ADR-0002（manifest 驱动编排）` 为裸引用，无 v5 路径。任务书「交付物/引用更新」范围未列此文件，工程师按约束未改，**判断合理**。建议后续补充一个轻量任务统一处置这些遗留引用。

2. **`Makefile` 裸引用**：代码注释中的 `ADR-0002`（第 3 行），同样不在任务范围。该注释为 Makefile 内部的设计说明，对开发者可读性影响较小，**优先级低于** `INFRA-001k`。

3. **结论**：两处裸引用均为**任务范围外的遗漏**，不构成本任务的阻塞项，但应排入后续清理。

#### 七、判决

**Accepted**

**4/4 验收标准全部通过**（基于 reviewer 独立验证）：

| 标准 | 验证方式 | 结果 |
|------|---------|------|
| 1. ADR 文件存在、格式合规、Status=Candidate | 独立读取文件 + 逐字段比对 adr-authoring.md 模板 | ✅ |
| 2. adr-0002 含 v5 决策（D1-D6 含 .cache/ + 可再生工作树） | 独立 rg 搜索 11 项关键词 | ✅ |
| 3. 5 个文件 ADR-0002 引用指向 v5 路径 | 独立 rg + git diff 逐文件核实 | ✅ |
| 4. 未照抄 0628 | 独立读取 0628 ADR 逐段对比 | ✅ |

**约束核验**：
- Status 先 Candidate ✅
- 不照抄 0628 正文 ✅
- 不写行号 ✅
- 未执行 git commit ✅
- 改动范围仅限列出文件 ✅

**与 engineer 自审结论的差异**：无实质性差异。engineer 的 verify.sh 输出与 reviewer 独立验证结果一致。engineer 正确识别了 INFRA-001k/SPEC-006t 的范围外裸引用。

**建议项**（非阻塞）：
- `INFRA-001k` 第 18 行和 `Makefile` 第 3 行有裸 ADR-0002 引用未补明 v5 路径，建议后续开轻量任务统一清理。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-12
**结论**：确认 reviewer 的 **Accepted**（4/4 无遗漏）；并补核 ADR 内容与实现的一致性。

**独立核对**：逐份读取两 ADR，对照 0628 原文（8 条英文句 `grep -F` 均 absent）与 v5 实现（`fetch.py`/`fetch_refs.py` 的 `.cache/`、`clean_work.py` 不碰 `.cache/`、`.gitignore` 忽略 `.work/`+`.cache/`、`Makefile` targets、`manifest_check.py`）；确认 D1–D6 准确、无事实错误、无遗漏。

**补充发现（非阻塞）**：

1. reviewer 的范围外发现不完整：`INFRA-001k:18` 同时含 **ADR-0001** 裸引用（reviewer 只点了 ADR-0002）。
2. reviewer 证据命令 `rg -rn` 的 `-r` 在 ripgrep 是**替换**语义（证据保真瑕疵；结论经复核仍成立）——后续审阅记录避免 `-r`。
3. `SPEC-006t`「格式遵循 `adr-0001` 风格」在新 ADR 引入后有**指向歧义**（v5 已有自己的 `adr-0001`；格式依据实为 `adr-authoring.md`）——属 spec 模块，不在本任务范围。

**范围外裸引用处置建议**：

- `INFRA-001k` 第 18 行（ADR-0001+0002 双裸引用）：**须在 `INFRA-013m` 置 `里程碑` 前处置**（新开轻量 infra 任务，或并入 `INFRA-013m` 核验前检查项）。
- `Makefile` 第 3 行（注释）：并入同一轻量任务，优先级最低。
- `SPEC-006t`：spec 模块后续任务澄清（改指 `adr-authoring.md`），infra 不跨界改。

**统一判决**：**Accepted**。
