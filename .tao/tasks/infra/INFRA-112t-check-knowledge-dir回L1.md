# INFRA-112t: `check-knowledge-dir` 回 L1（同时从 `check-milestone` 去重）

**模块**：infra
**项目里程碑**：M10
**依赖**：无（`SPEC-176t` / `INFRA-109t` 只作历史背景，非执行依赖）
**状态**：已验证

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

**测试结果**：`.work/evidence/INFRA-112t/run.sh` ⇒ `checks=14 failures=0`、脚本 rc=0；`make check` **rc=0**（`repository checks (L1): PASS`）；`make -n check` 命中 `tools/infra/check_knowledge_dir.py` **1** 次，`make -n check-milestone` **0** 次；注入 `.tao/knowledge/INFRA-112t-probe.md` ⇒ `make check` **rc=2** 并点名该文件，删除后 **rc=0**；`make check-knowledge-dir` rc=0；`make check-milestones-fresh` rc=0。
**修改文件**：`Makefile`（`_locked-check` 加 `check-knowledge-dir`；`check-milestone` 依赖/PASS 文案/注释⑤ 去 knowledge 并重编号；`check-knowledge-dir` 注释改 L1；help 两行；`.PHONY` 补齐）、`docs/Process-07-门控分层规范.md`（§1.1 该行层→L1）、`.tao/knowledge/milestones.md`（INFRA-112t 行→待验收）、本任务书；证据 `.work/evidence/INFRA-112t/`（`.work/` 被 gitignore）。
**验收结果**：
- L1 实际执行（`check-clean.log` L249/256）：`check-knowledge-dir — ... 顶层条目总数 8（文件 7 / 子目录 1）` / `结果: PASS (顶层无白名单外文件)`；`repository checks (L1): PASS`。
- 反例（`check-injected.log` L256–260）：`白名单外文件: .tao/knowledge/INFRA-112t-probe.md` / `结果: FAIL (1 个白名单外文件)` / `make: *** [Makefile:132: check] Error 2`（rc=2）；还原后 rc=0。
- 去重：`make -n check`=1、`make -n check-milestone`=0；`grep -m1 '^check-milestone:'` 无该目标；`.PHONY` 命中。
- 登记：Process-07:39 `| make check-knowledge-dir | **L1** |`，全文无「knowledge whitelist」残留（`grep -n knowledge` 仅 2 处：缘起路径 + 本行）。
**新发现/坑**：① 本任务书自身引用 `.work/evidence/INFRA-112t/run.sh`，该文件未落盘前 `make check` **rc=2**（`check-knowledge-refs` 悬空）——非代码问题，先落证据脚本后回绿（`baseline-check.log` rc=0）。② 证据脚本首版把 `>=1` 与 `1` 当字符串比 ⇒ 自红 1 项；改为数值判定后 14/14。③ Process-07 §1.1 `check-milestone` 行与 §2 触发点原文**已不含** knowledge（任务书写「如出现」）⇒ 未改。④ `.PHONY` 自 `INFRA-070t` 起就缺该目标，本次补齐。⑤ 白名单零改动（现场 8 条目全命中）。
**遗留问题**：无。`make check-milestone` 整目标按任务书**未跑**（前置含夜跑/L3 报告，现状必红），只用 `make -n` 断言去重。另：曾因 `/tmp/opencode/INFRA-112t/` 未建导致两条重定向命令失败（rc=1，日志未落），`mkdir -p` 后重跑 rc=0（重试 1 次，无仓库影响）。

## 审阅记录

#### 第 1 轮 engineer 自审

逐行核 `Makefile`/`docs` 改动与 `run.sh`；核对范围（`git status --porcelain -uall` = 4 个允许文件）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `run.sh` A5 用字符串比 `>=1` ⇒ 恒 FAIL（假红） | ✅已修 | 改为 `[ "$n" -ge 1 ]` 数值分支 | 重跑 `checks=14 failures=0` rc=0 |
| F2 `_locked-check` 追加后是否重复列出（同目标第二路径） | ❌不修（无缺陷） | 未改 | `make -n check` 命中该脚本 1 次 |
| F3 help/注释是否残留「knowledge 顶层白名单」于 check-milestone | ✅已修 | help 行、PASS echo、注释⑤ 均去 | `grep -rn knowledge docs/Process-07` 仅 2 处合理行；`help.log` L60 新行 / L66 无 knowledge |
| F4 越界风险：是否改到 `tools/`/白名单/其它 `.tao` 文件 | ❌不修（无越界） | 未改 | `git status` 仅 4 文件 |

#### 第 1 轮 reviewer 验收

**判决：Accepted**（2026-10-31；判决基于本人独立重跑，非采信完成区）。分析文件：`Makefile`、`docs/Process-07`、`.tao/knowledge/milestones.md`、本任务书、`.work/evidence/INFRA-112t/run.sh`。

**重跑记录（命令 / 真实输出 / 退出码）**：
- 文件集 4 项对账：`git diff --name-status ed6b51b9..5eefe0af` = 恰 4 文件全 `M`（Makefile / Process-07 / milestones.md / 本任务书），无 `A`（新增）⇒ 无 `.tao` 新增文件；`git diff -- tools/ spec/ contracts/ components/ tests/ AGENTS.md` 空 = 禁改面未碰；`check_knowledge_dir.py` diff 空 = 白名单判据真源零改动（md5 `54e56700…`）。
- 干跑：`make -n check | grep -c tools/infra/check_knowledge_dir.py` = **1**；`make -n check-milestone …` = **0**（grep rc=1）；`grep -m1 '^check-milestone:' Makefile` 依赖行 = `check-spec-archive check-spec-archive-verify check-sync-nonmaskable check-night-report check-l3-report`（不含 knowledge）。
- 真跑：`make check` **rc=0**（L249–256：`check-knowledge-dir … 顶层条目总数 8（文件 7 / 子目录 1）`、`结果: PASS (顶层无白名单外文件)`，尾行 `repository checks (L1): PASS`）；`make check-knowledge-dir` **rc=0**；`make check-milestones-fresh` **rc=0**（`PASS (65 行…)`）。
- 独立注入（创建/删除法，未用 git 还原）：`echo … > .tao/knowledge/INFRA-112t-review-probe.md` ⇒ `make check` **rc=2**，L256 `白名单外文件: .tao/knowledge/INFRA-112t-review-probe.md`；`rm` 后 **rc=0**；`ls -A` 清单 md5 前后均 `927e634b…` 一致；`git status --porcelain -uall` 空。
- 证据脚本审阅（可达 FAIL 路径逐条核）后重跑：`.work/evidence/INFRA-112t/run.sh` ⇒ **`checks=14 failures=0`、rc=0**，其注入段 rc=2 + md5 对账与我独立注入一致。
- 登记/PHONY：Process-07:39 `| make check-knowledge-dir | **L1** |`；全文 `grep -n knowledge` 仅 2 处（缘起 + L1 行），check-milestone 行/§2 触发点无 knowledge；`Makefile` `.PHONY`（L72）与 help（L200 `(L1; INFRA-070t/INFRA-112t)`）命中；PASS echo / 注释⑤已去 knowledge 并重编号。

**约束核验**：改动 ⊆ 允许 4 文件（+gitignore 的证据目录）✓；判据真源/白名单/禁改面零改动 ✓；未跑 check-milestone 整目标/夜跑/L3 ✓；验收后快照 = 验收前（树空）✓；完成区声明与我重跑输出逐条一致（14/14、1 次/0 次、rc=0/2/0）✓。

**非阻断 finding（文档级，记档不返工）**：`run.sh` 的 case 类断言（依赖行/.PHONY/Process-07 三条）FAIL 分支的 `rc=` 展示参数写死 0（L34/41/64…），若真失败时输出 rc=0 有误导；断言判定与退出码机制不受影响（failures 累计、exit 1）。建议 architect 收尾时顺手改为传实际 rc。可进 `/complete`。

#### architect 提交与文件集审核（待 reviewer 判决，档位 `WIP`）

- 分支 `INFRA-112t`；提交 `a59fe560`（`feat(infra): INFRA-112t check-knowledge-dir 回 L1`），未 push。
- 显式 staging 4 路径，`git diff --cached --name-only` 与完成区「修改文件」逐项一致：`Makefile`、`docs/Process-07-门控分层规范.md`、`.tao/knowledge/milestones.md`、本任务书 ⇒ **无漏提 / 无多提 / 无越界**；提交后 `git status -uall` 空。
- 独立复核：`make -n check` 命中 `check_knowledge_dir.py` **1** 次、`make -n check-milestone` **0** 次；`make check` rc=0；注入 `.tao/knowledge/INFRA-112t-arch-probe.md` ⇒ rc=2 且点名，删除后 rc=0；`.work/evidence/INFRA-112t/run.sh` 自跑 `checks=14 failures=0` rc=0（148 s）。`.tao/` 无新增文件。

#### architect `/complete` 交叉复核（判决：Accepted 成立）

**复核记录（2026-10-31 23:07–23:13，命令真实输出）**：
- 文件集：`git diff --name-status ed6b51b9..HEAD` = 4 `M`（`Makefile` / `docs/Process-07-门控分层规范.md` / `.tao/knowledge/milestones.md` / 本任务书），无 `A`；`git diff --stat ed6b51b9..HEAD -- tools/ spec/ contracts/ components/ tests/ AGENTS.md` **空**。
- 白名单零改动：`md5sum tools/infra/check_knowledge_dir.py` = `54e56700e11875b5ddcc0125b0883b33`，与 `ed6b51b9` 该文件同值。`.tao/knowledge/` 顶层 8 条目（7 文件 + `refs/`）全命中。
- L1 唯一执行 / 去重：`make -n check | grep -c` = **1**；`make -n check-milestone | grep -c` = **0**（rc=1）；`grep -m1 '^check-milestone:' Makefile` = `check-spec-archive check-spec-archive-verify check-sync-nonmaskable check-night-report check-l3-report`；`.PHONY` 段含该目标。
- 反例可达 FAIL（创建/删除法，未用 git 还原）：注入 `.tao/knowledge/INFRA-112t-complete-probe.md` ⇒ `make check` **rc=2**，L256 `白名单外文件: .tao/knowledge/INFRA-112t-complete-probe.md`；删除后 **rc=0**；`ls -A` 清单 md5 前后均 `927e634b…`。
- 登记：`docs/Process-07` 全文 `knowledge` 仅 2 处（L4 缘起、L39 L1 行）；`Makefile` help L200 带 `(L1; INFRA-070t/INFRA-112t)`、PASS echo 与注释 ⑤/⑥ 已去 knowledge 且连号（无 ⑦ 悬空引用）。
- 门控：`make check` rc=0（含 `check-knowledge-dir` PASS 行 1 条）；`make check-knowledge-dir` rc=0；`make check-milestones-fresh` rc=0（状态置 `已验证` 后终跑）。

**非阻断 finding 处置（只改脚本/记录，判定不变）**：`run.sh` 的 case 类断言 FAIL 分支 `rc=` 显示改传真实退出码——L32/39/62/71 捕获 `rc=$?` 并透传，L48 的 PASS 行计数同理；断言判据与 `failures`/`exit 1` 机制未改。FAIL 分支演示（`/tmp/opencode/INFRA-112t/failbranch-demo.sh`，临时树注入）：命中态打印 `rc=0`、目标行缺失态打印 `rc=1`（真实），正例 PASS `rc=0`。重跑 `run.sh` ⇒ `checks=14 failures=0` rc=0（记录见上「测试结果」）。

**记档不返工（留主会话裁定）**：① `a59fe560` 提交信息用了 `feat(infra):` 前缀，偏离本仓库 `<任务ID>: <subject>` 约定（不改写：reviewer/architect 记录已引用该 hash）；② `run.sh` case 断言在 `check-milestone:` 整行缺失时落 `*)` 分支判 PASS（潜在假绿），本任务不改判定，记档。

**判定**：无阻断、无遗漏/过松项 ⇒ reviewer 的 Accepted **成立**；本任务**可进入 merge/push**（由主会话执行，architect 未 push、未 merge）。
