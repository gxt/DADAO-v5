# INFRA-116t: Process-04 归档规范修订 + 归档结构门控

**模块**：infra
**项目里程碑**：M10 后（维护）
**状态**：待开始

## 用户授权与背景

用户 2026-11-01 确认（原话摘要）：

> 不补各模块的 m；需要时单独加。任务流水搬到各里程碑归档 README，并清理 `milestones.md`。归档目录只有 `README.md`、`m<i>-retrospective.md`、`issues-closed.md` 和按模块组织的已验收任务书；任务书必须与 README 任务流水对应且已验收。m 文件多了少了不纠结。缺状态补状态；状态非精确 `已验证` 的规范化。模板统一为：任务清单 / 任务流水 / 终局证据 / MEMORY 摘录 / 指针。

M1–M10 扫描发现：M8–M10 无模块 m（不补）；M9/M10 README 无任务流水；M7 有 `notes/`、M6 `INTEG-023k` 无状态、M2 两个状态非精确；M1–M8 模板不完全一致。归档内容迁移归 `INFRA-117t`。

## 目标（本任务只做规范与门控，不改 archive 内容）

1. 修订 `docs/Process-04-里程碑归档规范.md`：
   - 删除「每个模块必须有 m」的强制；改为「模块 m 可选，用户认为某模块需要单独验收时添加」。
   - 明确任务流水**冻结到各归档 `README.md`**，并由 `milestones.md` 清理历史行。
   - 明确归档目录结构：只允许 `README.md`、`m<i>-retrospective.md`、`issues-closed.md`，以及按模块组织的已验收任务书；`notes/` 等补充记录不得留在归档目录（M7 notes 由 117 并入 retrospective）。
   - README 模板统一为：任务清单 / 任务流水（冻结）/ 终局证据 / MEMORY 摘录 / 指针。
   - 任务书必须 `**项目里程碑**：M<i>` 且状态终态（`已验证`/`里程碑`）；任务书必须与 README 任务流水对应。
   - 状态写法规范化：字段只允许 `已验证`/`里程碑`；括号补充移到审阅/注记，不放进状态字段。
2. 新增 `tools/infra/check_archive.py`：
   - 扫 `.tao/archive/M1`–`M10`：必需三文件；模块目录（infra/spec/llvm/qemu/testcases/integ）只放 `.md`；任务状态/里程碑字段；README 任务流水与任务文件一一对应；禁止 `notes/`/多余根文件。
   - m 文件**不强制**（数量不校验）；允许根/模块 m 存在。
   - 支持 `--self-test`：至少 3 类反例（缺 README、任务状态非终态、README 流水与文件不符）可达 FAIL。
   - 由于 M7 notes 尚未迁移，本任务期间允许**显式临时例外**（`--allow-m7-notes` 或白名单）并在 117 移除；禁止默认静默跳过。
3. 接入门控：`check-archive` 进 L1（或按现场定 L1；若 M7 notes 例外只允许到 117），`docs/Process-07` 登记，`Makefile` 加目标/.PHONY/help。
4. 跑现有 M1–M10：checker 在 M7 例外下 rc=0；`--self-test` rc=0；`make check` rc=0。

## 文件范围

- `docs/Process-04-里程碑归档规范.md`
- `docs/Process-07-门控分层规范.md`
- `tools/infra/check_archive.py`（新）
- `Makefile`（仅新目标/挂载/help/.PHONY）
- 本任务书、`.tao/knowledge/milestones.md`

**不改**：`.tao/archive/**` 内容（117 做）、M7 notes、M9/M10 README、任务书状态、spec/contracts/代码。

## 验收

1. Process-04 规则逐条可 grep（m 可选、流水落 README、三文件+模块任务、模板、状态精确）。
2. `check_archive.py` 扫 M1–M10：M7 notes 例外下 PASS；`--self-test` PASS；反例可达 FAIL。
3. `check-archive` 在 L1 成员内；`docs/Process-07` 登记。
4. `make check` rc=0；无 archive 内容改动。
5. 证据脚本/日志；不跑夜跑；完成区 ≤30 行。

## 5 项预检（待执行前复核）

1. 任务书内部一致；2. checker 前置可用；3. 验收可跑；4. 与 archive 现状一致（M7 例外）；5. 拟改文件不触 `spec/`。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
