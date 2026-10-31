# INFRA-112t: `check-knowledge-dir` 回 L1（同时从 `check-milestone` 去重）

**模块**：infra
**项目里程碑**：M10
**依赖**：无（`SPEC-176t` / `INFRA-109t` 只作历史背景，非执行依赖）
**状态**：待开始

## 执行环境
**执行环境**：本地（纯 `Makefile` + 文档；不重建组件、不跑 L3/夜跑）

## 问题根源（背景）

1. `check-knowledge-dir` 由 `INFRA-070t` 建立，判据真源 = `tools/infra/check_knowledge_dir.py`：`.tao/knowledge/` **顶层**只允许显式白名单文件（台账集合）与任意子目录；白名单外文件 / 目录缺失 / 顶层空（vacuous）⇒ 非零退出。
2. 2026-10-26 `SPEC-176t` 执行期，`e64168cf` 引入的 `.tao/knowledge/cfx-audit-2026-10-26.md` 落在白名单外 ⇒ 当时 `make check` 红。用户裁定「**从L1摘除，放到里程碑check里**」⇒ 该门控被挪进 `check-milestone`，`docs/Process-07` 登记为「里程碑收尾专项」（用户原话与经过见 `SPEC-176t` 任务书「本任务新增用户裁定」第 2 条）。
3. **挪走的理由已消失**：该越界文件已被删除（删除提交 `09ef4ce4`）。现场核验（2026-10-31 22:42）：
   - `python3 tools/infra/check_knowledge_dir.py` ⇒ **rc=0**（顶层 8 条目 = 7 个白名单文件 + `refs/` 子目录，白名单命中 7）。
4. **挪到里程碑层的副作用**（本次要修的点）：
   - L1 的「仓库完整性」不再覆盖 `.tao/knowledge/` 顶层混入文档 ⇒ 日常 `make check` 查不出，要等里程碑收尾才暴露；
   - `check-milestone` 的前置包含夜跑报告 / L3 报告，日常基本不跑 ⇒ 该门控实际处于「没人跑」状态；
   - 门控归属与判据错位：它是**纯静态目录检查**，按 `docs/Process-07 §3` 判据 1 本就属 L1（`INFRA-109t` 把归档门控移出 L1 是因为「归档只在发布边界变化」，本门控没有该性质）。

## 目的

1. **回 L1**：`make check` 必须**实际执行** `check-knowledge-dir`（进 `_locked-check` 依赖）。
2. **去重**：从 `check-milestone` 依赖中移除，避免同一检查在两层直接列出（`docs/Process-07 §4`）。
3. **登记同步**：`docs/Process-07` 的层归属表 / 触发点叙述与 `Makefile` 一致。
4. **判据不变**：只改「触发层 + 登记」，不改 `check_knowledge_dir.py` 的判据、不放宽/收紧白名单内容。

## 接口规范

### 输入（立任务书时现场核过的事实）

- `Makefile` `_locked-check` 依赖列表 = **L1 真源**，当前**不含** `check-knowledge-dir`。
- `Makefile` `check-milestone:` 依赖当前含 `check-knowledge-dir`（同时 PASS 文案也列了「knowledge 顶层白名单」）。
- `Makefile` help 中 `make check-milestone` 行把 knowledge whitelist 列为该目标组成；无 `make check-knowledge-dir` 独立 help 行。
- `Makefile` `.PHONY` 列表当前**不含** `check-knowledge-dir`（`INFRA-070t` 起就缺，非本次引入）。
- `docs/Process-07-门控分层规范.md` §1.1：`make check-knowledge-dir` 行 = 「里程碑收尾专项」；`make check-milestone` 行组成含 knowledge；§2「里程碑 / `/complete`」触发点叙述提到 `check-milestone` 组成。
- `AGENTS.md`「门控分层与触发点」只写层名与触发点、不列单目标 ⇒ **不需要改**。
- 基线：`make check` ⇒ **rc=0**（2026-10-31 22:42，尾行 `repository checks (L1): PASS`）。
- 干跑基线：`make -n check` 中 `check_knowledge_dir.py` 出现 **0** 次；`make -n check-milestone` 中出现 **1** 次。

> 行号会随编辑漂移，一律按**目标名/依赖行**定位，不按行号硬编码。

### 输出（改动清单，逐条）

1. **`Makefile`**
   - `_locked-check` 依赖列表**加入** `check-knowledge-dir`（建议紧邻 `check-contracts-dir`，两者同属目录白名单门控）。
   - `check-milestone:` 依赖**去掉** `check-knowledge-dir`；其 `PASS` echo 文案去掉「knowledge 顶层白名单」。
   - `check-knowledge-dir` 目标上方注释改为「**L1 成员**（`INFRA-070t` 建立；`SPEC-176t` 2026-10-26 临时挪到 `check-milestone`，`INFRA-112t` 2026-10-31 回 L1）」；判据描述保留。
   - help：`make check-milestone` 行去掉 knowledge whitelist；新增 `make check-knowledge-dir` 行，标 `(L1; INFRA-070t/INFRA-112t)`。
   - `.PHONY` 增补 `check-knowledge-dir`。
   - `check-milestone` 上方长注释块中 ⑤ 条目（knowledge 白名单）删除，保持条目编号连续（若重编号，同步 PROCESS-07 若有引用）。
2. **`docs/Process-07-门控分层规范.md`**
   - §1.1 `make check-knowledge-dir` 行：层改为 **L1**，判据列保留原描述，末尾注「判据未改，仅改触发层（`INFRA-112t`；2026-10-26 曾随 `SPEC-176t` 临移到 `check-milestone`）」。
   - §1.1 `make check-milestone` 行：组成列表去掉 knowledge whitelist。
   - §2「里程碑 / `/complete`」触发点：`check-milestone` 括号内组成同步去掉 knowledge（如出现）。
   - 不新开章节、不复制判据正文。
3. **`.tao/knowledge/milestones.md`**：任务流水只加 `INFRA-112t` 一行（`待开始` + `（登记）` + 一句改动 ≤120 字符，置于表首）。
4. **本任务书**（状态 / 完成区 / 审阅记录）。

## 约束

- **只改**：`Makefile`、`docs/Process-07-门控分层规范.md`、`.tao/knowledge/milestones.md`、本任务书；证据脚本落 `.work/evidence/INFRA-112t/`（`gitignore`，不入 git）。
- **禁改**：`tools/infra/check_knowledge_dir.py`（判据真源）、`.tao/knowledge/` 其余文件（含 `_ALLOWED_FILES` 对应白名单内容）、`AGENTS.md`、`spec/`、`contracts/`、`components/`、`tests/`。
- **白名单例外**：若发现白名单与当前目录**不一致**（现场：一致，rc=0），**先报告主会话/用户**，不得自行放宽名单；本任务默认**零白名单改动**。
- 不跑 `make check-full`、不跑 `make check-night`、不重建任何组件；`make check` 为基线验证（秒级）。
- 临时目录 `/tmp/opencode/INFRA-112t/`；仓库内不得留探针/临时文件。
- 反例注入**禁** `git checkout`/`restore`/`stash` 还原；用单文件创建/删除（或 `cp` 备份 + md5 对账）。

## 验收标准

1. **回 L1 且真实执行**：`make check` ⇒ rc=0；且 `make -n check | grep -c tools/infra/check_knowledge_dir.py` **≥1**；真实 `make check` 输出含该门控的 `结果: PASS (顶层无白名单外文件)`（贴原始输出片段）。
2. **反例可达 FAIL（L1 路径）**：在 `.tao/knowledge/` 造一个白名单外文件（如 `INFRA-112t-probe.md`）⇒ `make check` **rc≠0** 且输出点名该文件；删除后 `make check` 回 rc=0。贴两次 rc（用 `; echo rc=$?` 或分行取码，禁 `| tee` 吞码）。
3. **`check-milestone` 去重**：`grep -A1 '^check-milestone:' Makefile` 依赖行**不含** `check-knowledge-dir`；`make -n check-milestone | grep -c tools/infra/check_knowledge_dir.py` **= 0**；`make -n check` 中该目标直接出现次数 = 1（不重复）。
4. **单跑绿**：`make check-knowledge-dir` ⇒ rc=0；`make check-milestones-fresh` ⇒ rc=0（新增流水行体例/状态一致）。
5. **登记一致**：`docs/Process-07` 中 `check-knowledge-dir` 行层 = **L1**、`check-milestone` 行不含 knowledge；与 `Makefile` 逐条 grep 对齐（贴输出）。
6. **证据脚本**：`.work/evidence/INFRA-112t/run.sh` 一键跑通（`checks=N failures=0`，脚本自身 rc 落证据），含「注入 → FAIL → 还原 → 回绿」真实输出；断言均可失败（禁恒真）。
7. 完成区 ≤30 行，与真实输出逐条对齐；不跑夜跑、不重建。

## 文件范围（摘要）

- 允许：`Makefile`、`docs/Process-07-门控分层规范.md`、`.tao/knowledge/milestones.md`、`.tao/tasks/infra/INFRA-112t-*.md`、`.work/evidence/INFRA-112t/`。
- 禁止：其余一切（尤其 `tools/`、`spec/`、`components/`、`.tao/knowledge/` 其它文件）。

## 用户授权原话

> 「建立一个任务，把check-knowledge-dir移回L1」

（2026-10-31，用户会话；本任务书按此原话立项。历史裁定原话见 `SPEC-176t`：「从L1摘除，放到里程碑check里」。）

## 下发前预检（5 项，结论均为现场核）

1. **任务书内部一致**：改动清单 ⊆ 文件范围；验收 1–7 均机械可执行；状态 `待开始`；背景事实（rc=0、干跑 0/1 次）均来自现场命令。
2. **验证前置可用**：`python3` 可用；`tools/infra/check_knowledge_dir.py` 现场 rc=0；`make check` 现场 rc=0（秒级，已实测）；`make -n` 可用；`.tao/knowledge/` 顶层 8 条目全在白名单口径内。
3. **验收逐条可跑性**：①–⑥ 现在可跑；`make check-milestone` **整目标**不可作为绿判据（前置含夜跑/L3 报告与 `m` 册，现状大概率红）⇒ 本任务只用 `make -n check-milestone` 干跑断言（验收 3 已按此写）。
4. **与 `contracts/`、`tests/inst/` 一致**：本任务不触碰二者，`check-contracts-dir` / `check-tests-index` 不受影响。
5. **拟改文件 × `spec/` 清单**：`Makefile`/`docs/`/`.tao/` 均不在 `spec/`，无命中 ⇒ 无 BLOCKED；`check-spec-readonly` 因 `spec/` 未改必绿。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
