# VERIF-007t: issue registry + QEMU trans lint

**模块**：verif
**项目里程碑**：M1
**依赖**：`SPEC-003t`、`QEMU-013m`

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `docs/open-spec-issues.md` 等开放问题清单（若存在）
  - `verif/opcodes.yaml`（M1 mnemonic 列表）
  - `components/qemu/patches/*.patch`（QEMU trans 函数来源）
- 输出：
  - `docs/issues.yaml`：机器可读 issue registry
  - `verif/check_issues.py`：M1-gate 阻断检查（CI gate，有阻断则 exit 1）
  - `verif/check_qemu_trans.py`：每个 M1 opcode 是否有 `trans_<mnemonic>`（lint，默认 exit 0）
- 约束：
  - `check_issues.py` 只对 `status: open` 且 `blocks` 含 `M1-gate` 的条目阻断
  - `check_qemu_trans.py` 是 lint 不是 gate，默认 exit 0；可提供 `--strict` 使其 exit 1
  - mnemonic 标准化：`-` → `_`、全小写；同 mnemonic 多 opcode 只需一个匹配
  - 只读 `opcodes.yaml` 与 patch，不改组件源码

## 背景（完整）

### 目标

- **issue registry**：把 Markdown 开放问题表迁移为机器可读 `docs/issues.yaml`，并让 CI 能自动检测「哪些 open 问题阻断 M1 gate」。
- **trans lint**：验证 `components/qemu/patches/` 中每条 M1 opcode 都有 `trans_<mnemonic>` 实现——缺失会走 ILLI stub 导致测试静默失败，目前只能人工逐个检查。

### 设计理由

翻译链里「开放问题」与「QEMU trans 覆盖」此前都是人眼检查，容易漏。把它们机械化为 registry + lint，才能让 M1 gate 可自动判定、让 trans 缺失可见。

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

**`check_qemu_trans.py` 逻辑**：

1. 读 `verif/opcodes.yaml`，收集 M1 mnemonic（排除 M1 scope 外项）
2. 每个 mnemonic：grep `components/qemu/patches/*.patch` 是否含 `trans_<normalized>`（`-`→`_`）
3. 收集缺失项输出警告
4. 打印 `check_qemu_trans: N/M mnemonics have trans impl`
5. 默认 exit 0；`--strict` 时 exit 1

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-023a-issue-registry-trans-lint.md`（完整转述：背景 O-2/O-3、issues.yaml 格式与字段约束、迁移内容、check_issues 规范、check_qemu_trans 规范、Makefile 集成、约束、验收、完成区、代码级 Architecture Review 与 P0/P1）
- DADAO-0628：`scripts/check_issues.py`、`scripts/check_qemu_trans.py`、`docs/issues.yaml`（形态参考，禁止复制正文）

## 交付物

- `docs/issues.yaml`：迁移后的 issue registry（open/closed、scope、blocks、resolved_by）
- `verif/check_issues.py`：M1-gate 阻断 gate
- `verif/check_qemu_trans.py`：trans 函数存在性 lint
- 完成区附两脚本真实 stdout 与 trans 覆盖统计

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **MISC 映射表重建**：0.4.1 的 `check_qemu_trans.py` 硬编码 `_MISC_HA`（25 项，op=0x10 MISC-Norm）、`_RB_BANK`（8 项）、`_CMP_IMM`、`_CTL_FORMAT`；0.5.3 没有 `MISC-Norm`，改为主表 + octa/tetra/wyde/byte/RF/AMO 子表体系，映射表必须按 v5 结构重建。
2. **助记符全面变化**：`unimp`→`illi`、`setzw`→`set.zw`、`orw`→`or.w`、`brn`→`br.n`、`muls`→`mul.so` 等；trans 函数命名需以 `QEMU-013m` 实际实现为准核对。
3. **trans 源码路径**：0.4.1 查 `.work/qemu/target/dadao/translate.c` 或 patch；v5 以 `components/qemu/patches/*.patch` 与 `.work/` 构建树为准。
4. **issue 清单内容**：v5 的开放问题来自自身 spec/合约与 `SPEC`/`TESTSUITE` 模块记录，不照抄 0.4.1 的 C-xx 条目。
5. **脚本目录**：0.4.1 放 `scripts/`；v5 放 `verif/`（与 `validate_encoding.py` 一致）。
6. **`check` target 接入**：0.4.1 的 P0 是 `check-issues` 被误放 `lint` 未接入 `check`；v5 须从一开始把 issue gate 接入 `check`（Makefile 由 `INFRA-006t` 提供，本任务只提需求）。

## 已知坑 / 结论

摘自 DADAO-0628 DL-023a 完成区与代码级 Architecture Review：

1. **P0 — issue gate 必须接入 `check`**：否则 `make check` 对 M1-gate blocker 无感知。0.4.1 靠架构师直修（Makefile 追加 `check-issues`）。
2. **P1 — M1-gate blocker 必须 `exit(1)`**：仅 print 到 stderr 不算阻断；须在 M1-gate blocking 分支内 `sys.exit(1)`。
3. **trans lint 非阻断**：默认 exit 0，仅 lint 警告；`--strict` 才 exit 1。MISC 特殊指令（`swym`/`illi` 等）可能无独立 trans，属预期缺失。
4. **mnemonic 标准化**：`-`→`_`；同 mnemonic 多 opcode（如 `add.si` 的 RD/RB 变体）只需一个 trans 匹配。
5. **硬编码映射表易漂移**：0.4.1 的 `_MISC_HA`/`_RB_BANK` 等表与 `translate.c` 实际函数名需对齐；v5 重建时须以 `QEMU-013m` 实际函数名为准，并考虑直接从 `opcodes.yaml` + 命名约定推导以减少硬编码。
6. **`resolved_by` 校验**：closed 必须填、open 必须 null，否则 registry 失去审计意义。
7. **`docs/issues.yaml` 与人类可读视图并存**：保留 Markdown 视图（若有），yaml 作为机械源。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-023a-issue-registry-trans-lint.md`
- DADAO-0628：`.work/DADAO-0628/scripts/check_issues.py`
- DADAO-0628：`.work/DADAO-0628/scripts/check_qemu_trans.py`
- DADAO-0628：`.work/DADAO-0628/docs/issues.yaml`
- 本项目：`verif/opcodes.yaml`、`components/qemu/patches/`、`.tao/knowledge/contract-isa.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `python3 -c "import yaml; print(len(yaml.safe_load(open('docs/issues.yaml'))))"` 输出 ≥ 1，格式合法
2. `python3 verif/check_issues.py`：无 M1-gate blocker 时 exit 0；有则报错并 exit 1（fail-closed）
3. `python3 verif/check_qemu_trans.py` 输出 `N/M mnemonics have trans impl` 与 MISSING 明细，默认 exit 0
4. `check_issues.py` 接入 `make check`（issue gate 生效），`check_qemu_trans.py` 不阻断 `make check`
5. 缺 `docs/issues.yaml` 时 `check_issues.py` fail-closed（exit 1）
6. 完成区粘贴真实 stdout

## 完成区

**状态**：待开始
**Commit**：
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
