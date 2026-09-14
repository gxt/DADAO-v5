# INFRA-010t: issue registry（M1-gate）

**模块**：infra
**项目里程碑**：M1
**依赖**：无（可与其它 infra 任务并行）
**状态**：待开始

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
