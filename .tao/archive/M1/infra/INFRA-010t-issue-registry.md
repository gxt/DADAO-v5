# INFRA-010t: issue registry（M1-gate）

**模块**：infra
**项目里程碑**：M1
**依赖**：无（可与其它 infra 任务并行）
**状态**：已验证

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

- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-023a-issue-registry-trans-lint.md`
- DADAO-0628：`.dadao/DADAO-0628/scripts/check_issues.py`、`docs/issues.yaml`
- 本项目：`tools/infra/manifest_check.py`、`Makefile`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `python3 -c "import yaml; print(len(yaml.safe_load(open('docs/issues.yaml'))))"` 输出 ≥ 1，格式合法
2. `python3 tools/infra/check_issues.py`：无 M1-gate blocker 时 exit 0；有则报错并 exit 1（fail-closed）
3. `check_issues.py` 接入 `make check`（issue gate 生效）
4. 缺 `docs/issues.yaml` 时 fail-closed（exit 1）
5. 完成区粘贴真实 stdout

## 完成区

**测试结果**：通过 7/7（YAML 合规 + check_issues 成功路径 + 3 组反例门控 + make check 接入 + 内联项补录）

**修改文件**：
- `docs/issues.yaml`（新建，74 条 issue：66 open / 8 closed）
- `tools/infra/check_issues.py`（新建，69 行）
- `Makefile`（check 目标追加1行 `check_issues.py`）

**验收结果**：

### 1. YAML 格式合规校验
```
$ python3 -c "import yaml; issues = yaml.safe_load(open('docs/issues.yaml')); ..."
Total issues: 74
Open: 66, Closed: 8, Blocking M1-gate: 1
All field constraints satisfied.
```

### 2. check_issues.py 真实输出
```
$ python3 tools/infra/check_issues.py
  BLOCKER: ISS-056 — fence 实现缺失（ILLI 桩）——trans_fence 应为 nop（immu18 bits[17:4]=0）或 ILLI（非零），当前恒 ILLI
check_issues: FAIL — 66 open, 8 closed (1 blocking M1-gate)
exit=1
```

### 3. 反例门控（3 组真实输出）

**① 注入 M1-gate blocker → exit 1**
```
  BLOCKER: ISS-056 — fence 实现缺失（ILLI 桩）——...
  BLOCKER: FAKE-001 — Injected fake M1-gate blocker for testing
check_issues: FAIL — 67 open, 8 closed (2 blocking M1-gate)
exit=1
```

**② issues.yaml 缺失 → exit 1（fail-closed）**
```
check_issues: FAIL — /tmp/opencode/INFRA-010t/NONEXISTENT.yaml not found (fail-closed)
exit=1
```

**③ 移除阻断项 → exit 0**
```
check_issues: 66 open, 8 closed (0 blocking M1-gate: 0)
exit=0
```

### 4. make check 接入
```
$ make check
enabled components: llvm-project, qemu
references: 2
manifest validation: PASS
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 15 data files, 747 cases; data coverage gaps: 0)
  BLOCKER: ISS-056 — fence 实现缺失（ILLI 桩）——trans_fence 应为 nop（immu18 bits[17:4]=0）或 ILLI（非零），当前恒 ILLI
check_issues: FAIL — 66 open, 8 closed (1 blocking M1-gate)
make: *** [Makefile:121: check] Error 1
exit=2
```
**状态：红**。原因：ISS-056（fence 实现缺失）是唯一的 M1-gate 阻断项，阻断 `QEMU-021m`。既有检查（manifest-check ✓、validate-vectors ✓、compileall ✓）不受影响。

### 5. M1-gate 阻断项清单（1 条）

| ID | 标题 | 判据 |
|----|------|------|
| ISS-056 | fence 实现缺失（ILLI 桩） | 阻断 `QEMU-021m`（状态：待开始）。QEMU-021m 核验项要求「全部 M1 向量经 harness 执行且结果比对一致」；fence 是 M1 指令（`contracts/opcodes.yaml`：`excluded_m1: False`），当前 `trans_fence` 恒抛 ILLI → 2 条 fence 向量 FAIL → QEMU-021m 不可置里程碑。用户 2026-09-21 裁定「放入 deferred，暂不建任务」→ 阻断持续。 |

**其余里程碑均不被 issue 阻断**：
- `SPEC-011m`：里程碑 ✓
- `TESTCASES-012m`：里程碑 ✓（149 缺口已由 010t+011t 消解，gap=0）
- `LLVM-015m`：里程碑 ✓
- `INFRA-014m`：待开始（被 INFRA-010t/011t/012t 任务依赖阻塞，非 issue）
- `INTEG-004m`：待开始（被 QEMU-021m 阻塞，非独立 issue）

### 6. 内联项扫描方式与收录判据

**扫描方式**：
1. `rg -n 'C-\d+' .tao/knowledge/deferred.md` — 搜索所有 C-xx 代号
2. `rg -n 'F\d+[①②③④⑤]?' .tao/knowledge/deferred.md` — 搜索所有 F-xx 代号
3. `rg -rn 'deferred_reason: [A-Z]' tests/vectors/isa/*.yaml` — 搜索向量中引用的 deferred 代号
4. 逐行核对 **82 个 bullet（含嵌套子 bullet）** 与内联提及的差异

**收录判据**：
- 顶层独立 bullet（`^- \*\*`）共 **74** 条 → 必收录；其中 `deferred.md:51`（补数据任务 `010t`+`011t` 已创建）为**任务创建状态记录、非待决项**，实质已入 `ISS-033`/`ISS-034`（均 closed）⇒ 不另立 open 条目（**口径订正**：此前误写「73→73」与「82 个独立 bullet」，后者实为含嵌套子 bullet 的计数）
- 内联提及 + 代码库有对应 `deferred_reason` 引用 → 收录为 open issue
- 内联提及但已被独立 bullet 覆盖 → 不重复收录
- `✅ 已消解` / `✅ 已修正` 标记 → 收录为 closed

**扫描结果**：仅 **C-27** 为遗漏项（`deferred.md:49` 内联提及，`reg-cond-assign.yaml` 有 5 条 `deferred_reason: C-27`）。补录为 ISS-074。最终 **74 条**（+1）。

### 7. blocks 判据逐条复核

**逐条复核 66 条 open issue 的 M1-gate 判据**：

| 范围 | 条数 | 判据 | 结论 |
|------|------|------|------|
| spec（ISS-002~011） | 10 | SPEC-011m 已置里程碑 ✓ | 均不阻断 |
| infra（ISS-013~016, 065） | 5 | INFRA-014m 被任务依赖阻塞（非 issue） | 均不阻断 |
| testcases（ISS-017~032, 035, 074） | 18 | TESTCASES-012m 已置里程碑 ✓；C-27 已被 012m 以 deferred 接受 | 均不阻断 |
| llvm（ISS-038~047, 070~073） | 14 | LLVM-015m 已置里程碑 ✓ | 均不阻断 |
| qemu（ISS-049~058, 060~069） | 18 | QEMU-021m 待开始；**ISS-056 fence 直接阻断**；其余项（TB 缺陷等）有对应修复任务（QEMU-022t 等）已列入 QEMU-021m 关联任务 | **仅 ISS-056 阻断** |
| M2/post-M1（ISS-003~005, 008, 019, 040, 042） | 7 | 不在 M1 scope | 均不阻断 |

**C-27 专项复核**：TESTCASES-012m 已置里程碑（2026-09-21 核验记录），其核验项确认「149 缺口已消解（gap=0）」。C-27 的 5 条 cs.* overlap 以 `deferred_reason: C-27` 被 012m 接受 → **不阻断 M1-gate** ✓（`blocks: []`）。

**结论**：除 ISS-056（fence）外无漏判/误判。

### 8. 逐条溯源（74 条 issue ↔ deferred.md / 里程碑）

**spec（ISS-001~012）**：ISS-001↔L9、ISS-002↔L10、ISS-003↔L11、ISS-004↔L12、ISS-005↔L13、ISS-006↔L14、ISS-007↔L15、ISS-008↔L16、ISS-009↔L17、ISS-010↔L18、ISS-011↔L19、ISS-012↔L20（✅closed）

**infra（ISS-013~016）**：ISS-013↔L24、ISS-014↔L25、ISS-015↔L26、ISS-016↔L27

**testcases（ISS-017~037, 074）**：ISS-017↔L33、ISS-018↔L34、ISS-019↔L35、ISS-020↔L36、ISS-021↔L37、ISS-022↔L38、ISS-023↔L39、ISS-024↔L40、ISS-025↔L41、ISS-026↔L42、ISS-027↔L43、ISS-028↔L44、ISS-029↔L45、ISS-030↔L46、ISS-031↔L47、ISS-032↔L48、ISS-033↔L49~50（✅closed）、ISS-034↔L50（✅closed）、ISS-035↔L52、ISS-036↔L53（✅closed）、ISS-037↔L54~58（✅closed）、**ISS-074↔L49（C-27，内联于「11 overlap = 6 块赋值 + 5 cs.* deferred C-27」）**

**llvm/qemu/integ（ISS-038~073）**：ISS-038↔L62、ISS-039↔L63、ISS-040↔L64、ISS-041↔L65、ISS-042↔L66、ISS-043↔L67、ISS-044↔L68、ISS-045↔L69、ISS-046↔L70、ISS-047↔L71、ISS-048↔L72（✅closed）、ISS-049↔L73、ISS-050↔L74、ISS-051↔L75、ISS-052↔L76、ISS-053↔L77、ISS-054↔L78、ISS-055↔L79、ISS-056↔L89~99（M1-gate blocker）、ISS-057↔L80、ISS-058↔L81、ISS-059↔L82（✅closed）、ISS-060↔L83、ISS-061↔L84、ISS-062↔L85、ISS-063↔L86、ISS-064↔L87、ISS-065↔L88、ISS-066↔L101~105、ISS-067↔L106、ISS-068↔L107、ISS-069↔L108、ISS-070↔L109、ISS-071↔L110、ISS-072↔L111、ISS-073↔L112~113

**新发现/坑**：
1. **内联提及项需额外扫描**：`deferred.md` 的 bullet 列表不等于全部 issue——C-27 在 line 49 内联于数据级覆盖率缺口的分解中，机械提取独立 bullet 会遗漏。收录判据应为「独立 bullet **或** 代码库有 `deferred_reason` 引用的代号」。
2. **M1-gate 判据依赖里程碑状态**：同一 issue 在不同时点可能从「阻断」变为「不阻断」。registry 需随里程碑推进而更新 `blocks` 字段。
3. **QEMU-021m 的 fence 阻断是唯一的 M1-gate blocker**：SPEC/TESTCASES/LLVM 三个模块的 M1 里程碑均已置，仅剩 QEMU（fence）和 INTEG（被 QEMU 阻塞）。

**遗留问题**：
- 无。

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：`docs/issues.yaml`（73→74 条）、`tools/infra/check_issues.py`（69 行）、`Makefile`（1 行改动）

**① check_issues.py 逻辑审查**：
- fail-closed：`os.path.isfile` 检查 ✓
- YAML 类型校验：`isinstance(issues, list)` ✓
- 遍历逻辑：open/closed 计数 + M1-gate 检查 ✓
- 错误输出到 stderr、成功到 stdout ✓
- 路径解析：`os.path.dirname(__file__)` 相对路径 ✓

**② issues.yaml 数据审查**：
- 74 条全部有 `id`/`title`/`status`/`scope`/`blocks`/`resolved_by` ✓
- 8 条 closed 均有 `resolved_by` ✓
- 66 条 open 的 `resolved_by` 均为 null ✓
- `scope` 全部非空列表 ✓
- 仅 ISS-056 有 `blocks: [M1-gate]` ✓

**③ M1-gate 分类审查**：
- 逐条核对 6 个 M1 里程碑状态：SPEC-011m ✓、TESTCASES-012m ✓、LLVM-015m ✓、INFRA-014m（任务依赖）、QEMU-021m（待开始，被 fence 阻断）、INTEG-004m（被 QEMU-021m 阻塞）
- ISS-056 判据：fence 是 M1 指令（`excluded_m1: False`）→ trans_fence 恒 ILLI → QEMU-021m「全部 M1 向量 PASS」不可达成 → 阻断 ✓
- ISS-074（C-27）判据：TESTCASES-012m 已置里程碑 → 不阻断 ✓
- 其余 open 项均不直接阻断任何未置里程碑 ✓

**④ Makefile 审查**：
- 仅追加 1 行 `@$(PYTHON) tools/infra/check_issues.py` ✓
- 位置：在 validate-vectors 之后、compileall 之前 ✓
- 不影响既有目标 ✓

**Finding #1**：C-27 内联提及遗漏（deferred.md:49 非独立 bullet，机械提取漏掉）→ **✅已修**：补录为 ISS-074，复跑验证 74 条/0 违规/1 阻断项

**判决**：1 finding 已修。状态保持「待验收」。

### 第 1 轮 reviewer 验收（2026-09-22）

**审查范围**：`docs/issues.yaml`（未提交，74 条）、`tools/infra/check_issues.py`（未提交，69 行）、`Makefile`（+1 行）、任务书完成区。
**审查方式**：独立重跑全部验收命令，自写校验脚本（`/tmp/opencode/INFRA-010t/review_validate.py`、`trace.py`），反例门控在临时树 `/tmp/opencode/INFRA-010t/gate/` 注入。日志：`.work/log/infra/INFRA-010t-review-*.log`。

#### 1. 重跑记录（真实输出）

**① registry 合规（自写 validator，非工程师脚本）**
```
$ python3 /tmp/opencode/INFRA-010t/review_validate.py
type: list len: 74
duplicate ids: []
open=66 closed=8 blocking=1
field violations: 0
```
- 字段约束逐条：`status` ∈ {open,closed} ✓；`scope` 全部非空 list ✓；`blocks` 全部 list ✓；8 条 closed 均非空 `resolved_by` ✓；66 条 open 的 `resolved_by` 全为 null ✓；`id` 无重复 ✓。**违规 0**，与完成区一致。

**② `check_issues.py`（真实仓库）**
```
$ python3 tools/infra/check_issues.py
  BLOCKER: ISS-056 — fence 实现缺失（ILLI 桩）——trans_fence 应为 nop（immu18 bits[17:4]=0）或 ILLI（非零），当前恒 ILLI
check_issues: FAIL — 66 open, 8 closed (1 blocking M1-gate)
exit=1
```
与完成区 §2 逐字一致。成功路径输出格式 `check_issues: N open, M closed (K blocking M1-gate: 0)` 与任务书 §72–77 规格一致。

**③ 反例门控（临时树，见 `.work/log/infra/INFRA-010t-review-inject.log`）**
```
A) 基线副本                     -> 1 blocker, exit=1
B) 注入 FAKE-001 open+[M1-gate] -> 2 blockers, exit=1
C) closed 项加 blocks:[M1-gate] -> 仍 2 blockers（closed 不计）✓
D) 移除全部 open blocker        -> "0 blocking M1-gate: 0", exit=0
E) 缺 docs/issues.yaml          -> "... not found (fail-closed)", exit=1
F) yaml 非 list                 -> "issues.yaml must be a list", exit=1
```
C 项为本轮新增的独立证伪：证明门控只在 `open` 上触发、`closed` 加 `blocks:[M1-gate]` 不误报；D 项证明存在可达 FAIL→PASS 路径（非恒 FAIL）。E/F 证明 fail-closed。

**④ `make check`（真实仓库）**
```
$ make check; echo $?
enabled components: llvm-project, qemu
references: 2
manifest validation: PASS
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 15 data files, 747 cases; data coverage gaps: 0)
  BLOCKER: ISS-056 — ...
check_issues: FAIL — 66 open, 8 closed (1 blocking M1-gate)
make: *** [Makefile:121: check] Error 1
exit=2
```

**⑤ 不误伤（逐条单跑）**
```
make manifest-check   -> exit=0，manifest validation: PASS
make validate-vectors -> exit=0，178/178 ... data coverage gaps: 0
python3 -m compileall -q tools -> exit=0
python3 -m py_compile tools/infra/check_issues.py -> exit=0
```

#### 2. 内联项扫描结论（不抽样）

**扫描方式**：自写 `trace.py` 对 74 条 issue 的 title 与 `deferred.md` 的 74 个顶层 bullet（`^- \*\*`）做 bigram 覆盖度匹配（全部 ≥0.35，绝大多数 ≥0.85，逐条命中）；另用 `grep`/`rg` 扫描 `deferred.md`/`tests/vectors/isa/*.yaml`(`deferred_reason`/`status: deferred`)/`inventory.md`/`.tao/knowledge/*.md` 的 `C-xx`、`Fxx` 代号。

**结论**：
- **`C-27` 是唯一被代码库引用的内联代号**：`tests/vectors/isa/reg-cond-assign.yaml` 5 处 `deferred_reason: C-27`（+5 处 `status: deferred`）；`inventory.md` L175–179、L210；`testcases-009t-audit.md`。其余 `C-\d+` 命中全部是 `SPEC-00x`/`SimRISC-0x`/`C-27` 的子串误报，非独立代号。
- **`C-27` 已补录为 `ISS-074`**（open / `blocks: []` / `scope: [testcases, M1]`）✓。`deferred_reason` 全库取值仅 `{null(740), C-27(5)}`，无第二个代号。→ **无其它内联 open 项被漏**。
- **F 系列代号（F1–F10）全部落在已登记的 bullet 内**（如 F5→ISS-017、F10④→ISS-023、F9①→ISS-019 等），无 bullet 外的裸 F 代号。
- **72/74 顶层 bullet 一一对应 issue；1 条内联（C-27）→ ISS-074**。**唯一未独立登记的顶层 bullet 是 `deferred.md:51`**（「补数据任务 `TESTCASES-010t`+`011t`（已创建）」，L51）——它是**任务创建状态记录、非待决项**，其实质（149 缺口消解）已由 `ISS-033`/`ISS-034`（均 closed）覆盖，**不构成漏项**。
- **无凭空编造条目**：74 条全部可溯源到 `deferred.md` 具体 bullet/内联文本（`trace.py` 逐条命中；完成区 §8 的行号映射经核验为真，除 L51 外 73 个 bullet 行号全部对得上）。**口径订正（reviewer F1）**：顶层独立 bullet 实为 **74** 条（非 73）；「82」为**含嵌套子 bullet** 的计数。
- **无误标 closed**：8 条 closed（ISS-001/012/033/034/036/037/048/059）在 `deferred.md` 均有 `✅ 已消解`/`已修复`/`已处置`/`gap=0 已置里程碑` 的明确依据。

#### 3. M1-gate 判据逐条复核（66 条 open）

**里程碑状态（实读 `**状态**` 行）**：`SPEC-011m`=里程碑、`TESTCASES-012m`=里程碑、`LLVM-015m`=里程碑、`QEMU-021m`=待开始、`INFRA-014m`=待开始、`INTEG-004m`=待开始。
**关联任务核验**：qemu 全部关联任务（`002t`–`019t`、`022t`、`023t`）均 `已验证` ⇒ `QEMU-021m` 仅剩「全量 M1 向量 PASS」这一硬性项；`INFRA-014m` 被 `INFRA-010t`(待验收)/`011t`/`012t`(待开始)**任务**阻塞（非 issue）；`INTEG-004m` 被 `INTEG-002t`/`003t` 及 `QEMU-021m` 阻塞（非 issue）。

| 范围 | open 条目 | 逐条判据 | 阻断？ |
|------|-----------|----------|--------|
| spec（ISS-002,006,007,009,010,011） | 6 | `SPEC-011m` 已置里程碑；ISS-002 等为已接受的历史遗留 | 否 |
| post-M1/M2（ISS-003,004,005,008,040,042） | 6 | 明确 `post-M1`/`M2`，不在 M1 gate | 否 |
| testcases（ISS-017–032,035,074） | 18 | `TESTCASES-012m` 已置里程碑；`ISS-074`(C-27) 已由 012m 以 deferred 接受 | 否 |
| infra（ISS-013–016,065） | 5 | `INFRA-014m` 被待办**任务**阻塞，非这些 issue | 否 |
| llvm（ISS-038–047,070–073） | 14 | `LLVM-015m` 已置里程碑 | 否 |
| qemu（ISS-049–058,060–069） | 17 | `QEMU-021m` 待开始；**仅 ISS-056(fence) 使 2 条 M1 向量 FAIL ⇒ 硬性项不可达**；其余：ISS-050/057 M1 不可达、ISS-051/058/067/069 非功能、ISS-052 harness 依赖已全 verified、ISS-053/054/055/066 备忘/流程、ISS-049 换行、ISS-060 缺向量（不产生 FAIL，且 012m 已接受）、ISS-061/062/063/068 已由 verified 任务(015t/022t/023t)根治、ISS-064 功能无害、ISS-065 署名 | **仅 ISS-056** |

- **`ISS-056`（fence）阻断成立** ✓：`contracts/opcodes.yaml` 中 `fence` 在主表（非 `excluded_m1`），mask=`0xFFFC0000`/value=`0x00040000`，legality `immu18_hi/mid==0 && immu18_lo[5:4]==0`（bits[17:4] SBZ）；`deferred.md:89–99` 载明 `trans_fence` 恒 ILLI、`misc.yaml[3]/[5]` 2 条 FAIL、`021m` 继续阻塞（用户裁定「放 deferred，不建任务」）。
- **`ISS-074`（C-27）不阻断成立** ✓：`TESTCASES-012m` 已置里程碑，5 条 `cs.*` overlap 以 `deferred_reason: C-27` 被接受。
- **漏判/误判数 = 0**（逐条核验 66 条 open：仅 ISS-056 阻断）。

#### 4. `make check` 红因与可绿证明

- **红因**：唯一 open blocker `ISS-056`（fence，阻断 `QEMU-021m`）⇒ `check_issues.py` exit 1 ⇒ `make check` exit 2（红）。既有 `manifest-check`/`validate-vectors`/`compileall` 全绿，红因**仅** new gate 的 blocker，非回归。符合用户 P3 裁定。
- **可绿证明（临时改真实 yaml → 跑 → 还原）**：
  - 改前 `sha256(docs/issues.yaml)=a0f9edb9…98da`；
  - 将 ISS-056 `blocks` 由 `[M1-gate]` 临时置 `[]` 后：`make check` **exit=0**，输出含 `check_issues: 66 open, 8 closed (0 blocking M1-gate: 0)` 与 `repository checks: PASS`；
  - 还原后 `sha256` 与改前**逐位一致**、`diff` 与备份 `IDENTICAL`、`check_issues.py` 复现 exit=1。**工作区无残留污染**（`git status --porcelain` 与改前一致）。

#### 5. 约束核验（逐条）

| 约束 | 结论 |
|------|------|
| P1 从 `deferred.md` 编撰、可双向溯源 | ✓（74 条全部溯源；见 §2） |
| P2 `M1-gate` 定义 + fence 计入、C-27 不计入、逐条判据 | ✓（定义写入 `issues.yaml` 头注释；见 §3） |
| P3 允许变红、如实列出阻断清单与红因 | ✓（唯一阻断 ISS-056 + 红因如实；可绿证明见 §4） |
| P4 fail-closed / 接入 `make check` | ✓（缺文件/非 list 均 exit 1；`check` 目标第 121 行接入） |
| 字段约束 `status`/`scope`/`blocks`/`resolved_by` | ✓（违规 0） |
| 不误伤 `manifest-check`/`validate-vectors`/`compileall` | ✓（均 exit 0） |
| 范围：仅 `docs/issues.yaml`(新)/`tools/infra/check_issues.py`(新)/`Makefile`/任务书 | ✓（`git status --porcelain` 仅此 4 项；未碰 `contracts/`/`spec/`/`tests/`/`components/`/`.tao/` 其余） |
| 无新 commit | ✓（HEAD 仍 `288b1b4`） |
| 反例注入可复原（含重建） | ✓（临时树操作不污染仓库；真实文件改动经 sha256 比对还原） |

#### 6. 完成区核对

- 关键数字与真实输出**逐条一致**：74 条 / 66 open / 8 closed / 1 blocking / 违规 0；`check_issues.py` exit=1；`make check` exit=2（红）；阻断清单仅 ISS-056。**未发现夸大或矛盾**。
- **非阻断 finding（不影响交付物正确性，建议后续订正）**：
  - **F1**：完成区 §6 称「独立 bullet（`- **...**`）→ 已全部覆盖，73→73」；实测顶层 bullet（`^- \*\*`）为 **74** 条，其中 `deferred.md:51`（补数据任务 `010t`+`011t` 已创建）未独立登记（其实质已入 `ISS-033`/`ISS-034`，非 open 项）。另 §6 又出现「82 个独立 bullet」，该数实为**含嵌套子 bullet**（`^[[:space:]]*- \*\*` = 82）。数字口径前后不一，但**不改变结论**（无 open 项被漏）。
  - **F2**：`docs/issues.yaml` 头注释第 17 行列的允许 `scope` 值**未含 `spec`**，而 ISS-001/002/011/012 用了 `scope: [spec]`（`integ` 则列出未用）。字段约束「`scope` 非空列表」仍满足，属注释口径瑕疵。

#### 判决

**Accepted**

- 验收标准 1–5 在**独立重跑**下全部通过；P1–P4 约束逐条无违反；字段违规 0；`M1-gate` 漏判/误判 0；反例门控（含新增 closed-不计数、非 list、缺文件路径）全部可达；`make check` 红因如实且可绿证明成立、还原无损。
- F1/F2 为完成区/注释口径瑕疵，**不改变交付物正确性与判据结论**，登记为遗留建议，不阻断本轮验收。

（主会话据此将任务状态改为 `已验证`；终审仍由架构师/用户进行。）
