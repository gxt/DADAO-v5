# INTEG-027t: agent 配置与规则重构（30 条审计收口 + 复数目录迁移 + instructions 并入 + opencode.jsonc + AGENTS.md 精简）

**模块**：integ
**项目里程碑**：M6（进程/工具类，**不计入** M6 交付任务流水）
**依赖**：无（用户 2026-10-10 逐条裁定；对账清单 `.work/log/integ/agent-config-audit.md`，A01–F02 共 30 条）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `.work/log/integ/agent-config-audit.md`（只读体检：过时 7 / 冲突 5 / 缺失 8 / 重复 4 / 措辞 4 / 元问题 2 = 30 条）。
  - 旧配置 `.opencode/{agent,command,instructions}/`（单数目录 + `instructions/` 5 文件，均未跟踪）。
  - `AGENTS.md`、`.tao/README.md`、`.tao/knowledge/lessons.md`。
- **背景**：项目本地 agent 配置（`.opencode/**`）此前随全局迁移落入本仓库，存在过时指针、与 `AGENTS.md` 冲突、关键约定缺失、单一真源重复、措辞（单数目录名/全量权限）及「`instructions/` 是否被加载 / `.opencode` 是否入库」两项元问题。**用户 2026-10-10 逐条裁定**：30 条全改、复数化、`instructions/` 并入后删除、`.opencode/**` 入库。
- **范围**：
  1. **30 条审计收口**（A01–A07 / B01–B05 / C01–C08 / D01–D04 / E01–E04 / F01–F02，逐条落实，改 30 / 不改 0）。
  2. **E01 复数化**：`.opencode/agent/`→`agents/`、`command/`→`commands/`，全部引用同步。
  3. **A07**：删 `.tao/README.md` 中 `/translate` 行（`.opencode/` 无实现文件）。
  4. **F01**：`instructions/` 通用必需项并入 `AGENTS.md`「命令与任务执行纪律」后删除 `instructions/`（E02 其它项目内容 bazel/Vivado/fpga/coralnpu/CTAO 随之消失）。
  5. **F02**：`.opencode/**` 入库（未跟踪且未被忽略 ⇒ **无需改 `.gitignore`**）；一并删 `AGENTS.md`/`README` 中「工作仓库不含 agent 文件」表述。
  6. **`opencode.jsonc`**：`watcher.ignore = [.work/**, .cache/**, .dadao/**]`。
  7. **`AGENTS.md`**：新增「长任务（长构建/长命令）」节；全文精简 **216→172 行**（规则不丢，落点对账）。
- **输出**：
  - 新增 `.opencode/opencode.jsonc` + `.opencode/agents/{architect,engineer,reviewer}.md` + `.opencode/commands/{plan,dispatch,complete,status}.md`（**8 文件，首次入库**）。
  - 改 `AGENTS.md`、`.tao/README.md`；删 `.opencode/{agent,command,instructions}/`。
  - 证据 `.work/evidence/INTEG-027t/run.sh`；报告 `.work/log/integ/INTEG-027t-{report,slim-map}.md`。
- **约束**：
  - 纯文档/配置改动 ⇒ `make check` 按项目规则**豁免**；跑 `make check-no-residue`。
  - **规则不丢**：`AGENTS.md`/`README` 压缩项须逐条有落点（`slim-map` 逐文件逐条对账）。
  - `spec/`/`contracts/`/`components/` 交集为空。

## 验收标准

1. **结构**：`.opencode/` 恰 8 文件、无 `agent/`/`command/`/`instructions/` 旧目录。
2. **`opencode.jsonc` 合法**：`json.load` rc=0，含 3 条 `watcher.ignore`。
3. **无悬空引用**：全仓文件引用扫描 `悬空=0`（脚本现场统计，不写死计数）。
4. **规则不丢**：`lessons` §引用缺失=0；命名章节引用全中；过时 token（`translate`/`feedback_`/`reset --soft`/`--amend`）命中=0。
5. **一键证据脚本**：`.work/evidence/INTEG-027t/run.sh` 逐项 PASS、`RUN_EXIT=0`，含「悬空引用注入→FAIL→`cp`+md5 还原→回绿」自检（可达 FAIL）。
6. **无残留**：`make check-no-residue` EXIT=0。

## 完成区

**状态**：已验证
**测试结果**：`.work/evidence/INTEG-027t/run.sh` **10/10 PASS、EXIT=0**（含注入自检）；`make check-no-residue` EXIT=0。
**修改文件**：新增 `.opencode/opencode.jsonc`、`.opencode/agents/{architect,engineer,reviewer}.md`、`.opencode/commands/{plan,dispatch,complete,status}.md`（8 文件）；删 `.opencode/{agent,command,instructions}/`；改 `AGENTS.md`（216→172 行）、`.tao/README.md`；知识 `lessons.md` §7.32 + `changelog.md` 一行；本任务书。
**验收结果**：悬空=0（引用总数 34）；`lessons` §引用缺失=0；命名章节引用 10/10；过时 token 命中=0；`AGENTS.md`=172 行。
**新发现/坑**：原 `instructions/` 的 3 条探针细则（回读校验／双向验证／注入非空）在 `lessons.md` 无对应条目 ⇒ 显式落 `.opencode/agents/engineer.md` 免丢规则；`.opencode/**` 未被任何 `.gitignore`/exclude 忽略 ⇒ F02「入库」无需改 `.gitignore`。
**遗留问题**：无（本包）。工作树另含 **`TESTCASES-041t` 既存未提交改动**（`tests/llvm/codegen/*`、`tools/integ/run_codegen_e2e.py`），非本包、未触碰。

> 报告（30 条对账 + 精简对账 + 证据 + 两级 engineer 自审 + 两轮 reviewer 判决全文）：`.work/log/integ/INTEG-027t-report.md`；审查证据：`.work/log/integ/INTEG-027t-review-evidence.log`。

## 审阅记录

#### 第 1 轮 engineer 自审
自主逐行，6 条 finding（F1 嵌套粗体、F2 失效指针名、F3 悬空子条目指针、F4 `§` 置于反引号内、F5 探针细则丢失风险、F6 扫描假阳性）**全部已修**，判决 → 状态置 `待验收`。详见报告 §四。

#### 第 1 轮 reviewer 验收
**判决：Needs Revision**（2026-10-10，独立重跑）。重跑 `run.sh` `RUN_EXIT=0`（9/9 PASS）、独立 `refscan.py` 真悬空=0、`json.load` rc=0、`check-no-residue` EXIT=0；独立注入→FAIL→`cp`+md5 还原→回绿；规则不丢抽查 12 条全中；约束核验全过。**唯一阻断 F01**：删 `instructions/` 后 4 份通用细则（git-commit/git-push/remote-tasks/discipline）全仓 + 全局 + `spec/` 检索零命中 = **静默丢规则**；修法二选一（补回落点 / 报「有意删除+理由」）。详见 `.work/log/integ/INTEG-027t-review-evidence.log`、报告「审阅记录 → 第 1 轮」。

#### 第 1 轮 engineer 返工自审
仅修 F01：14 条细则**补回 10 / 显式不适用 4**（1a/1b/1d/2e 由 submodule 或 `<任务ID>:` 约定决定），零静默丢弃；`AGENTS.md` 169→172 行；`run.sh` 增 C9 并自证可达 FAIL（注入→FAIL→`cp`+md5 还原→回绿）。4 条 finding（R1 typo、R2 C9 可达 FAIL、R3 不修附证据、R4 行数受控）处置毕，判决 → 维持 `待验收`。详见报告「返工段」。

#### 第 2 轮 reviewer 验收
**判决：Accepted**（2026-10-10，独立重跑）。`run.sh` `RUN_EXIT=0`（**10/10 PASS**，C9 通过，`AGENTS.md`=172）；独立 `refscan.py` 真悬空=0；`git show` 取回 4 份 `instructions` 原文逐条核验：git-commit/git-push/remote-tasks/discipline 四组**补回逐条 grep 命中、不适用项附理由**，`slim-map` 已由「1 行覆盖 5 文件」改为逐文件逐条，**零丢弃确认**；独立注入（坏 `§` 指针）→FAIL→`cp`+md5 还原→回绿；约束核验全过（`spec/`/`contracts/`/`components/` 交集空、无残留、未切分支、未提交）。详见 `/tmp/opencode/INTEG-027t-review2/`、报告「审阅记录 → 第 2 轮」。
