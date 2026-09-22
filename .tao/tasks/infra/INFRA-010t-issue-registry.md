# INFRA-010t: issue registry（M1-gate）

**模块**：infra
**项目里程碑**：M1
**依赖**：无（可与其它 infra 任务并行）
**状态**：待开始

## 预检订正（2026-09-21，下发前，含用户裁定）

> 本节优先级高于下文旧文本；冲突时以本节为准。

**P1 — 输入源不存在，内容来源改为 `deferred.md`**：
- 实测 `docs/open-spec-issues.md` **不存在**；`docs/` 无 issue 清单；`spec/` 无 `[OPEN]` 标记 ⇒ **registry 内容须另行编撰**（用户裁定：**从 `.tao/knowledge/deferred.md` 编撰**）
- `.tao/knowledge/deferred.md` 现有 **40+ 条**待决/遗留项 ⇒ 逐条编为 `docs/issues.yaml` 的 issue（定 `id`/`title`/`status`/`scope`/`blocks`/`resolved_by`）
- `id` 命名建议沿用既有代号（如 `C-27`）或 `INFRA-<n>`；**须与 `deferred.md` 条目可双向溯源**（每条 issue 的 `title`/`notes` 指向其 `deferred.md` 条目）

**P2 — `M1-gate` 概念须先定义（全仓此前无定义）**：
- 实测 `.tao/knowledge/`、`docs/`、`ADR-0004` **均无 `M1-gate` 定义** ⇒ 本任务须**显式定义**并写入任务书/`issues.yaml` 头注释
- **用户裁定口径**：`blocks: [M1-gate]` = **直接阻断「任一模块 M1 里程碑」**的项
  - 例：**`fence` 实现缺失** → 阻断 `QEMU-021m` ⇒ **`blocks: [M1-gate]`** ✓
  - 反例：**C-27**（`cs.*` 条件赋值快照）→ 已由 `TESTCASES-012m` 以 `deferred` 处置接受（里程碑已置）⇒ **不阻断 M1-gate** ✗（`blocks: []`，`status: open` 仍可）
  - 判据须**机械可查**：若某 issue 阻断某模块里程碑（该模块里程碑因它未置），则计入 M1-gate；否则不计。**逐条**给出判据依据（引用对应任务/里程碑）

**P3 — `make check` 允许变红（用户裁定）**：
- 接入 `make check` 后，若存在 `status: open` + `blocks: [M1-gate]` 的项 ⇒ `check_issues.py` **exit 1** ⇒ **`make check` 会红**。
- **用户裁定：允许变红**（诚实反映 M1 未完成）。**不得**为保持绿而把阻断项错误分类为不阻断 ✗。
- 但须在完成区**显式列出**当前「阻断 M1-gate」的 open 项清单与由此导致的 `make check` 状态（红/绿 + 原因），使读者明确这不是回归 ✗。

**P4 — 其余**：`tools/infra/` 存在 ✓；`make check` 现为 `manifest-check validate-vectors` + `compileall` ✓（本任务追加 issue gate）；`check_issues.py` 的 fail-closed（`docs/issues.yaml` 缺失 → exit 1）✓ 保留。

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`docs/open-spec-issues.md` 等开放问题清单（若存在）
- 输出：
  - `docs/issues.yaml`：机器可读 issue registry
  - `tools/infra/check_issues.py`：M1-gate 阻断检查（CI gate，有阻断则 exit 1）
- 约束：
  - `check_issues.py` 只对 `status: open` 且 `blocks` 含 `M1-gate` 的条目阻断
  - `docs/issues.yaml` 不存在 → fail-closed（exit 1）
  - 接入 `make check`（issue gate 生效）

## 背景（完整）

### 目标

把 Markdown 开放问题表迁移为机器可读 `docs/issues.yaml`，并让 CI 自动检测「哪些 open 问题阻断 M1 gate」。

### 设计理由

「开放问题」此前靠人眼检查，容易漏。机械化为 registry + gate，才能让 M1 gate 可自动判定。

### 关键概念 / 数据

**`docs/issues.yaml` 格式**：顶层列表，每条 issue：

```yaml
- id: C-27
  title: "..."
  status: open          # open | closed
  scope: [M1]           # M1 | post-M1 | system | SBI | kernel
  blocks: [M1-gate]     # M1-gate 表示直接阻断 M1 里程碑
  resolved_by: null     # null 或 "commit SHA / ADR ref / PR"
```

字段约束：`status` ∈ {open, closed}；`scope` 非空列表；`blocks` 可空列表；`resolved_by` closed 时必填、open 时 null。

**`check_issues.py` 逻辑**：

1. 读 `docs/issues.yaml`
2. 每条 issue：若 `status == 'open'` 且 `'M1-gate' in blocks` → 报错
3. 有报错 → stderr + `sys.exit(1)`
4. `docs/issues.yaml` 不存在 → `sys.exit(1)`（fail-closed）
5. 成功输出：`check_issues: N open, M closed (K blocking M1-gate: 0)`

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-023a-issue-registry-trans-lint.md`（issue registry 部分）
- DADAO-0628：`scripts/check_issues.py`、`docs/issues.yaml`（形态参考，禁止复制正文）

## 交付物

- `docs/issues.yaml`：迁移后的 issue registry
- `tools/infra/check_issues.py`：M1-gate 阻断 gate
- 完成区附真实 stdout

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **issue 清单内容**：v5 的开放问题来自自身 spec/合约与模块记录，不照抄 0.4.1 的 C-xx 条目。
2. **脚本目录**：`scripts/` → `tools/infra/`。
3. **`check` target 接入**：v5 从一开始把 issue gate 接入 `check`（Makefile 由 `INFRA-006t` 提供，本任务只提需求）。

## 已知坑 / 结论

1. **P0 — issue gate 必须接入 `check`**：否则 `make check` 对 M1-gate blocker 无感知。
2. **P1 — M1-gate blocker 必须 `exit(1)`**：仅 print 到 stderr 不算阻断。
3. **`resolved_by` 校验**：closed 必须填、open 必须 null。
4. **`docs/issues.yaml` 与人类可读视图并存**：保留 Markdown 视图（若有），yaml 作为机械源。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-023a-issue-registry-trans-lint.md`
- DADAO-0628：`.work/DADAO-0628/scripts/check_issues.py`、`docs/issues.yaml`
- 本项目：`tools/infra/manifest_check.py`、`Makefile`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `python3 -c "import yaml; print(len(yaml.safe_load(open('docs/issues.yaml'))))"` 输出 ≥ 1，格式合法
2. `python3 tools/infra/check_issues.py`：无 M1-gate blocker 时 exit 0；有则报错并 exit 1（fail-closed）
3. `check_issues.py` 接入 `make check`（issue gate 生效）
4. 缺 `docs/issues.yaml` 时 fail-closed（exit 1）
5. 完成区粘贴真实 stdout

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
