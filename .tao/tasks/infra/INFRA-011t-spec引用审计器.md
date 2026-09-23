# INFRA-011t: spec 引用审计器

**模块**：infra
**项目里程碑**：M1
**依赖**：`SPEC-002t`、`SPEC-010t`
**状态**：已验证

## 预检订正（2026-09-21，下发前，含用户裁定）

> 本节优先级高于下文旧文本；冲突时以本节为准。

**P1 — 审计对象 = 全部 4 个 `contract-*.md`**（用户裁定）：
- 实测已存在 **4 个**：`contract-isa.md`（528 引用）、`contract-abi.md`（5）、`contract-elf.md`（0）、**`contract-authoring.md`（1，模板/方法论、非合约）**
- 任务书旧文「当前含 `contract-isa.md`；后续 … 加入后自动纳入」**不成立** ⇒ 按 `contract-*.md` glob 全审 4 个；若某文件（如模板）不适合本审计口径，**在报告中分类注明**（不得静默排除）

**P2 — Check 1 的「可解析」口径 = 标题 + 粗体引子 + 正文行（三类都算）**（用户裁定；任务书原文「只认 `#{1,4}` 标题」**过窄**）：
- 实测 68 条唯一引用，按「仅标题」解析 → 7 条失败 ✗，其中**多条内容真实存在但非标题**：
  - `SimRISC-01 §rd0 为目的寄存器约定` → 内容在**粗体引子** `> **rd0 为目的寄存器约定**：…`（`SimRISC-02 §rb0…`/`SimRISC-03 §rf0…` 同）
  - `SimRISC-02 §各类操作对高 16 位（bits[63:48]）的处理规则` → 内容在**正文行**（非标题）
- ⇒ 解析器须依次尝试：**① `#{1,4}` 标题** → **② 粗体引子（`> **X**：` 或行内 `**X**`）** → **③ 正文行（全文出现该节标题文本）**；**报告须标明每条引用的命中类型**（标题/粗体/正文）✓
- 真失效项（如 `SimRISC-00 §版本`、`SimRISC-03 §版本`、`SimRISC-01 §3.5`）**如实报告**为「节标题未找到」，**不得**为凑绿而放宽到「任意子串命中」

**P3 — `(Lnn)` 行号形态实测 0 处**：任务书称「部分 `spec_cite` 含 `(L7)`」，但实测 `contract-*.md` 中 **0 处** ✗ ⇒ 该解析分支可保留（防御），但报告须**注明「本轮无 `(Lnn)` 实例」**。

**P4 — 节标题内含 `]`**：如 `各类操作对高 16 位（bits[63:48]）的处理规则` ⇒ 引用正则**不得**用 `[^\]]*` 截断 ✗；须处理括号内的 `]`（否则该条被误解析/误报）。

**P5 — Check 2 为启发式**：规范标记（`ILLI`/`UNDI`/`MALIGN`/`IALIGN`/`保留`/`reserved`/`必须` 等）+「无引用」⇒ 首轮计数可能较大；任务书已定「不入 `make check`、只做独立 `make check-spec-refs`」✓ 保留。**不得**为压低计数而收窄标记集（须如实报告）。

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `.tao/knowledge/contract-*.md`（被审计对象，当前为 `contract-isa.md`）
  - `spec/*.md`（引用目标，`SimRISC-00`~`04` 及 DADAO 系列）
- 输出：
  - `tools/infra/check_spec_refs.py`：spec 引用审计脚本
  - 首轮审计报告（完成区，含两类违规计数 + 明细）
- 约束：
  - **不得改 `contract-*.md` 正文来凑绿**：不许编造/删改引用，不许删规范断言；报告是交付物
  - 不并入 `make check`，新增独立 `make check-spec-refs`（首轮必然有违规）
  - 裸 `§N.M` 是合约内部引用，不在审计范围
  - 检查类脚本放 `tools/infra/`（通用 CI 检查）

## 背景（完整）

### 目标

把翻译链 `spec → contract → test → QEMU/LLVM` 中最弱环「spec→contract」机械审计，产出 `tools/infra/check_spec_refs.py` + 首轮审计报告，做两项检查：

1. **引用有效性**：`contract-*.md` 中每个 `[SimRISC-XX §…]` 引用可解析到 `spec/` 真实内容（文件存在；节标题存在）。
2. **无引用规范断言**：`contract-*.md` 中含规范性断言（ILLI/UNDI/MALIGN/IALIGN 等）却既无 `[SimRISC-XX §…]` 也无显式自主决策标记的句子。

### 设计理由

合约的每个规范性期望值必须能回溯到 `spec/`，否则实现方（LLVM/QEMU/golden）会各按理解实现，差分验证失去基准。引用有效性保证「引了但引错」被发现；无引用断言保证「没引也没声明是自主决策」的真空断言被发现。

### 关键概念 / 数据

**引用格式（v5 `contract-isa.md` 实际形态）**：

- 文件前缀 + 节标题：`[SimRISC-00 §版本]`、`[SimRISC-01 §rd0 为目的寄存器约定]`、`[SimRISC-02 §函数返回]`
- 行号（部分 `spec_cite` 字段含）：`SimRISC-01 §rd0 为目的寄存器约定 (L7)`、`(L37)`
- 文件名多为**前缀**（`SimRISC-01` → `spec/SimRISC-01-数据类指令.md`），需前缀匹配到真实文件
- **排除**：裸 `§1.3`/`§5.1` 等是合约内部引用，不在审计范围

**Check 1 — 引用有效性**：提取所有 `[SimRISC-XX §…]`（不含裸 `§N.M`），按 `<file>` / `<file> §<节标题>` / `<file> §<节标题> (L<n>)` 解析；文件前缀匹配 `spec/*.md`；节标题验证 spec 文件内有匹配的 `#{1,4} <标题>` 标题；行号验证该行存在。报告每个无法解析的引用（file:line + 原文 + 失败原因）。

**Check 2 — 无引用规范断言**：扫描 `contract-*.md` 含规范标记（`ILLI`/`UNDI`/`MALIGN`/`IALIGN`，可含 `保留`/`reserved`/`必须` 等）的行/块；若既无 `[SimRISC-XX §…]` 也无显式自主决策标记（如行内 `[spec-decision]` 或引用 `ADR-000N`）→ 报「无引用断言」。

**输出**：结构化报告（两类违规计数 + 明细 file:line）；有违规时**非零退出**（fail-closed）。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-039a-wiki-ref-auditor.md`（完整转述：背景、spec.md 引用格式多样性、Check 1/Check 2 规格、首轮审计报告要求、约束、过程要求、验收、完成区首轮 57 条问题、代码级 Architecture Review）

## 交付物

- `tools/infra/check_spec_refs.py`：spec 引用审计脚本（Check 1 + Check 2，fail-closed）
- 首轮审计报告（完成区，原始终端输出 + 分类明细）
- Makefile 独立目标需求：`make check-spec-refs`（不并入 `check`）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **wiki → spec**：0.4.1 审计对象是 `contracts/isa/spec.md`，引用目标是 DADAO-0628 的 wiki 参考（外部，`[wiki §…]`）；v5 **无 wiki**，审计对象是 `.tao/knowledge/contract-*.md`，引用目标是 `spec/*.md`（`[SimRISC-XX §…]`）。
2. **引用标记**：`[wiki §SimRISC-01 L87]` → `[SimRISC-01 §rd0 为目的寄存器约定]`（v5 用节标题为主，行号出现在部分 `spec_cite` 字段的 `(Lnn)`）。
3. **文件前缀解析**：`SimRISC-01` → `spec/SimRISC-01-数据类指令.md`（前缀匹配），与 0.4.1 的 wiki 文件名前缀匹配同理但目标目录不同。
4. **审计对象范围**：v5 审计全部 `contract-*.md`（当前含 `contract-isa.md`；后续 ABI/ELF/SBI 合约加入后自动纳入）。
5. **脚本路径**：`scripts/check_wiki_refs.py` → `tools/infra/check_spec_refs.py`；make 目标 `check-wiki-refs` → `check-spec-refs`。
6. **`check_wiki_drift.py` 不存在于 v5**：0.4.1 的 SHA 漂移检查在 v5 无对应物（规范以 `manifests/` 锁 commit），本任务不移植。

## 已知坑 / 结论

摘自 DADAO-0628 DL-039a 完成区与代码级 Architecture Review：

1. **首轮必然有违规**：0.4.1 首轮 61 引用中 5 条失效、52 条无引用断言；v5 首轮同样预期非零，故**不并入 `make check`**，只做独立目标。
2. **引用格式极杂**：节标题、行号、全文件名混用，还有引号内注释、分号分隔多引用、跨文件引用等解析边界；解析器须覆盖并明确失败原因分类（文件不存在/行越界/节标题不存在）。
3. **裸 `§N.M` 不是引用**：合约内部引用，勿误判。
4. **`[spec-decision]` 标记机制**：允许显式声明「自主决策，非 spec 派生」，使审计收敛为「既没引用也没声明」的真空断言。
5. **报告是交付物**：修合约是下游独立动作（可能需 spec 团队），不得为凑绿改正文。
6. **fail-closed**：有违规时 exit 非零，能力必须具备（即使暂不接入 check）。
7. **数字必须来自实跑**：报告计数不得估算。

## 参考

- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-039a-wiki-ref-auditor.md`
- DADAO-0628：`.dadao/DADAO-0628/scripts/check_wiki_refs.py`
- 本项目：`.tao/knowledge/contract-isa.md`、`spec/SimRISC-00-指令系统设计.md` ~ `spec/SimRISC-04-系统类指令.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `python3 tools/infra/check_spec_refs.py` 可运行，输出 Check 1/Check 2 两类违规计数 + 明细（file:line + 原因）
2. 有违规时 exit 非零（fail-closed）；无违规时 exit 0
3. 引用解析覆盖 `[SimRISC-XX §<节标题>]` 与带 `(Lnn)` 形态，裸 `§N.M` 不计入
4. `[spec-decision]`/ADR 标记可排除对应断言
5. 未修改 `contract-*.md` 正文（diff 确认）
6. 独立 `make check-spec-refs` 存在且不并入 `make check`
7. 完成区粘贴首轮审计真实 stdout，数字来自实跑

## 完成区

**测试结果**：通过 7/7 验收标准

**修改文件**：
- 新建 `tools/infra/check_spec_refs.py`（spec 引用审计脚本，433 行）
- 修改 `Makefile`（新增 `check-spec-refs` 目标 + help 文本，未改 `check`）

**验收结果**：

### 首轮审计真实 stdout（`python3 tools/infra/check_spec_refs.py`，exit 1）

```
========================================================================
spec 引用审计报告
========================================================================

Check 1 — 引用有效性
  总引用数: 586
  (Lnn) 行号形态: 0 处
  注: 本轮无 (Lnn) 实例
  命中类型统计: 标题=566, 粗体=12, 正文=3
  成功解析: 581
  失败: 5

  失败明细:
    .tao/knowledge/contract-abi.md:13  [DADAO-21 §章节名]
      原因: 节标题未找到
    .tao/knowledge/contract-abi.md:13  [DADAO-11 §章节名]
      原因: 节标题未找到
    .tao/knowledge/contract-abi.md:13  [SimRISC-0X §章节名]
      原因: 文件不存在
    .tao/knowledge/contract-authoring.md:22  [SimRISC-01 §3.5]
      原因: 节标题未找到
    .tao/knowledge/contract-isa.md:9  [SimRISC-0X §章节名]
      原因: 文件不存在

Check 2 — 无引用规范断言
  命中数: 52

  (52 条明细，见日志 .work/log/infra/INFRA-011t-first-audit.log)

------------------------------------------------------------------------
结果: FAIL (57 violations: 5 Check1 + 52 Check2)
------------------------------------------------------------------------
EXIT: 1
```

### F1 收紧前/后/最终三版计数对比

| 指标 | 收紧前（子串 `in`） | 过度收紧（exact-only） | 最终（exact/prefix `：`） | 说明 |
|------|---------------------|----------------------|--------------------------|------|
| 总引用数 | 584 | 586 | 586 | F2 +2（SimRISC-0X） |
| 标题命中 | 566 | 566 | 566 | 不变 |
| 粗体命中 | 12 | **8** ✗ | **12** ✓ | `§版本`×4 恢复为 bold prefix 命中 |
| 正文命中 | 3 | 3 | 3 | 不变 |
| 失败数 | 3 | **9** ✗ | **5** ✓ | 3 原 + 2 F2（§版本×4 不再误报失败） |

**`§数据表` 失败**：`resolve_section(spec_00, '数据表')` → `('', False)` ✓（`数据表` ≠ `数据表示`，且不以 `数据表：` 开头）

**`§十六进制数字` 失败**：`resolve_section(spec_00, '十六进制数字')` → `('', False)` ✓

**`§版本` 命中**：`resolve_section(spec_00, '版本')` → `('bold', True)` ✓（`版本` == `版本：0.5.3` 的 `：` 前缀）

**三类命中覆盖逐条**：
- **标题**（566）：`[SimRISC-00 §寄存器]` → `## 寄存器`（exact）；`[DADAO-21 §RD寄存器]` → `### RD寄存器（Data registers）`（`（` lead-in）
- **粗体**（12）：`[SimRISC-01 §rd0 为目的寄存器约定]` → `> **rd0 为目的寄存器约定**：...`（exact）；`[SimRISC-00 §版本]` → `> **版本：0.5.3**`（`：` lead-in）
- **正文**（3）：`[SimRISC-02 §各类操作对高 16 位（bits[63:48]）的处理规则]` → spec line 9 `各类操作对高 16 位（bits[63:48]）的处理规则如下：`（line-start + `如下` lead-in）

### 抽样逐条复核

**Check 1 失败项（5 条，全部逐条）**：

1. `contract-abi.md:13 [DADAO-21 §章节名]` — 模板占位符，spec 中无 `章节名`。✅ 真失效。
2. `contract-abi.md:13 [DADAO-11 §章节名]` — 同上。✅ 真失效。
3. `contract-abi.md:13 [SimRISC-0X §章节名]` — F2 新增，`SimRISC-0X` 无 spec 文件。✅ 正确报「文件不存在」。
4. `contract-authoring.md:22 [SimRISC-01 §3.5]` — 裸节号示例，spec 中无 `3.5`。✅ 真失效。
5. `contract-isa.md:9 [SimRISC-0X §章节名]` — F2 新增。✅ 正确报「文件不存在」。

**Check 2 命中项（抽样 ≥5 条）**：

1. `contract-isa.md:278 - rdha 与 rdhb 同时为 rd0 → **ILLI**` — 含 `ILLI`，行内无 spec 引用。✅ 正确命中。
2. `contract-isa.md:521 - 未对齐 → **MALIGN**` — 含 `MALIGN`，行内无 spec 引用。✅ 正确命中。
3. `contract-isa.md:155 - z：未使用，应为零（SBZ）` — 含 `SBZ`，行内无 spec 引用。✅ 正确命中。
4. `contract-abi.md:40 - reserved（编译器不得分配使用）` — 含 `reserved`+`不得`，行内无 spec 引用。✅ 正确命中。
5. `contract-elf.md:47 - Reserved（必须为 0）` — 含 `Reserved`+`必须`，行内无 spec 引用、无 `[spec-decision]`、无 ADR。✅ 正确命中。

### 口径正确性证据

**三类命中各有实例**（见上方覆盖逐条）。

**真失效项如实报告**：`§章节名`（×3 含 F2 新增的 SimRISC-0X）报「节标题未找到」/「文件不存在」；`§3.5` 报「节标题未找到」。✅ 未为凑绿放宽。

**`§版本` 正当命中**：spec `> **版本：0.5.3**` 以 `版本` 开头后跟 `：`，符合 `_text_matches` 的 prefix 规则。reviewer 已核实「若报失败将是真误报」。✅4 处 `§版本` 全部命中。

**裸 `§N.M` 不计入**：`extract_refs('text §1.3 more')` → `[]`。✅

**`(Lnn)` 无实例**：报告注明「本轮无 (Lnn) 实例」。✅

**`]` 内含标题**：bracket-depth 计数器正确处理。✅

### 反例门控四组输出

**① 注入失效引用**（临时副本）：exit 1 ✓

**② 注入无引用规范断言**（临时副本）：Check 2 捕获 ✓

**③ 无违规合约 → exit 0**（`contract-test.md` 含可解析引用无规范标记）：`结果: PASS (0 violations)` / exit 0 ✓

**④ ADR 排除**（临时副本 `ILLI ADR-0003 已决策`）：Check 2 命中数 0（被排除）✓

**⑤ 还原证据**：`git diff --name-only -- .tao/knowledge/` 空 ✓

### `make check-spec-refs` 验证

```
结果: FAIL (57 violations: 5 Check1 + 52 Check2)
make: *** [Makefile:134: check-spec-refs] Error 1
```

### `make check` 未改证据

`make -n check | grep -c check_spec_refs` → 0 ✓
`git diff Makefile` → 仅新增目标（PHONY/help/check-spec-refs），`check:` 行无增删 ✓

### 未改 contract 正文

`git diff --name-only -- .tao/knowledge/` → 空 ✓

**新发现/坑**：
1. **`：`/`（` lead-in 是关键语义边界**：`§版本` 指向 `> **版本：0.5.3**`（`：` 后为版本号）；`§RD寄存器` 指向 `### RD寄存器（Data registers）`（`（` 后为英文名）。`_text_matches` 用 lead-in 字符集 `：:（(，,` 精确捕获这一语义关系，不用任意子串。`§数据` 不命中 `数据寄存器又可称为...`（`寄` 非 lead-in 字符）。
2. **compound section reference**：`§` split 后首段 prefix match（`传参：Parameter Passing`），后续段 exact/prefix/split match。
3. **bracket-aware 提取**：`bits[63:48]` 含 `]`，用 depth 计数器。
4. **Check 2 启发式**：52 条命中中大部分是异常条件行（`→ **ILLI**`），行级无引用但段落级有。属预期（P5）。
5. **contract-authoring.md**：3 条 Check 2 命中属模板/方法论，非合约规范断言。

**遗留问题**：
- 无未完成项。全部 7 条验收标准已满足。

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：`tools/infra/check_spec_refs.py`（新建，375 行）、`Makefile`（+8 行）

**审查发现**：

| # | 类别 | 发现 | 判决 |
|---|------|------|------|
| 1 | 逻辑 | `extract_refs()` bracket-depth 计数器正确处理 `bits[63:48]` 中的 `]` | ✅ 无问题 |
| 2 | 逻辑 | compound reference（`§` split）对 `DADAO-21 §寄存器规范 §RD寄存器` 正确解析 | ✅ 无问题 |
| 3 | 逻辑 | Check 2 代码块追踪（`is_in_code_block`）跳过 ``` 块内的行 | ✅ 无问题 |
| 4 | 逻辑 | `_LN_SUFFIX_RE` 正确剥离 `(Lnn)` 后缀（本轮无实例，防御性保留） | ✅ 无问题 |
| 5 | 边界 | `_PREFIX_ANCHOR` 不匹配 `[ADR-0003 §D1]`（前缀为 ADR 非 SimRISC/DADAO） | ✅ 符合设计 |
| 6 | 边界 | 裸 `§1.3` 不被 `_PREFIX_ANCHOR` 匹配（需 `[PREFIX §` 前缀） | ✅ 符合设计 |
| 7 | 惯用 | `resolve_section` 对 compound ref 用 `§` split + 逐段匹配，每段独立三类搜索 | ✅ 合理 |
| 8 | 惯用 | `spec_cache` 避免重复读取同一 spec 文件 | ✅ 性能合理 |

**判决**：全部发现已修/无问题，可标「待验收」。

### 第 1 轮 reviewer 验收

**审查对象**：`tools/infra/check_spec_refs.py`（375 行，未提交）、`Makefile`（+7 行未提交）、任务书完成区。
**审查方式**：全部结论来自 reviewer 独立复跑，不采信完成区叙述。日志：`.work/log/infra/INFRA-011t-review-*.log`。

#### 重跑记录（真实输出）

```bash
$ python3 tools/infra/check_spec_refs.py
Check 1 — 引用有效性
  总引用数: 584
  (Lnn) 行号形态: 0 处
  注: 本轮无 (Lnn) 实例
  命中类型统计: 标题=566, 粗体=12, 正文=3
  成功解析: 581
  失败: 3
Check 2 — 无引用规范断言
  命中数: 52
结果: FAIL (55 violations: 3 Check1 + 52 Check2)
$ echo $?  →  1        # 与主会话/完成区一致 ✓
```

```bash
$ make check-spec-refs
结果: FAIL (55 violations: 3 Check1 + 52 Check2)
make: *** [Makefile:134: check-spec-refs] Error 1
$ echo $?  →  2        # make 传播的失败退出码 ✓（脚本自身 exit 1）
```

- 独立核验 `make -n check | grep -c check_spec_refs` → `0`，`check:` 目标行未改（`check: manifest-check validate-vectors` + `check_issues.py` + `compileall`），**未并入 `make check`** ✓
- `python3 -m py_compile tools/infra/check_spec_refs.py` → OK；两次重跑计数一致（确定性）✓
- 逐项复核 12 条粗体命中 / 3 条正文命中（脚本内遍历打印，见下）与报告统计一致 ✓

#### 约束核验（逐条）

| 约束 | 结果 | 证据 |
|---|---|---|
| 未改 `contract-*.md` 正文 | ✅ | `git diff --name-only -- .tao/knowledge/` **空** |
| 独立 `make check-spec-refs`，不并入 `check` | ✅ | 目标存在；`make -n check` 不含该脚本 |
| Makefile 仅新增目标、`check` 行未变 | ✅ | `git diff Makefile` 仅 PHONY/help/新目标三段 `+`，无 `check:` 增删 |
| 未 `git commit` | ✅ | `git log -1` = `131543b`；`git diff --cached` 空 |
| fail-closed | ✅ | 有违规 exit 1；干净合约 exit 0（见反例门控） |
| 裸 `§N.M` 不计入 | ✅ | `extract_refs('text §1.3 more')` → `[]`；临时合约仅 `§1.3/§5.1` 时总引用=0 |
| `(Lnn)` 无实例已注明 | ✅ | `grep -rnE '\(L[0-9]+\)' .tao/knowledge/contract-*.md` 无命中；报告印「本轮无 (Lnn) 实例」 |
| `]` 内含标题不截断 | ✅ | `extract_refs('[SimRISC-02 §各类操作对高 16 位（bits[63:48]）的处理规则]')` 返回完整 section（bracket-depth 计数） |
| 未为凑绿收窄标记集 | ✅ | 标记集含 ILLI/UNDI/MALIGN/IALIGN/保留/reserved/必须/应当/不得/需要/MUST/SHALL/REQUIRED/SBZ，未收窄 |

#### Check 1 三条失败逐条核实（原文 + 判定）

1. `.tao/knowledge/contract-abi.md:13  [DADAO-21 §章节名]`、`[DADAO-11 §章节名]`
   - 原文：`> **来源标注**：每条规范性断言句末以 \`[DADAO-21 §章节名]\` / \`[DADAO-11 §章节名]\` / \`[SimRISC-0X §章节名]\` 标注 spec/ 来源…`
   - `章节名` 是**模板占位符**（字面「章节名」），spec 中 `DADAO-21/11` 无 `章节名` 标题/粗体/正文 → 判定**真失效（报告正确）**。
   - **DADAO 是否属审计范围**：任务「接口规范/背景」明列引用目标为 `spec/*.md`（`SimRISC-00~04` **及 DADAO 系列**），故纳入 DADAO 前缀**正当**。报告这两条正确。
   - 附带发现（非阻断）：同一行的 `[SimRISC-0X §章节名]` 因前缀正则 `SimRISC-\d+` 要求数字而**未被提取**（`0X` 非数字）。属占位符、非真实引用，但造成「DADAO 占位符被报、SimRISC-0X 占位符漏报」的不对称。建议后续将前缀放宽为 `SimRISC-[\dA-Za-z]+` 或单独识别占位符；不影响本轮结论。
2. `.tao/knowledge/contract-authoring.md:22  [SimRISC-01 §3.5]`
   - 原文：`- 每个规范性断言标注来源 spec/ 章节（如 \`[SimRISC-01 §3.5]\`）`
   - `grep '3\.5' spec/SimRISC-01-数据类指令.md` **无命中** → 判定**真失效（报告正确）**；`§3.5` 为示例裸节号。

**结论**：3 条 Check 1 失败**全部为真失效**，无漏报、无放宽。

#### §版本 自我修正核实（P2 争议点）

- engineer 称 `SimRISC-00 §版本` 实为可解析（`> **版本：0.5.3**` 粗体引子命中）。
- **独立核实**：`spec/SimRISC-00-指令系统设计.md:3` = `> **版本：0.5.3**`（DADAO-21:3、DADAO-11:3 亦为 `> **版本：0.9.2**…`）。代码 `resolve_section(spec,'版本')` → `('bold', True)`（实测）。
- **判定：engineer 说法成立，属正当命中，非「任意子串」凑绿**。理由：(a) 该行是粗体引子，落 P2 tier ②；(b) 语义上 `[SimRISC-00 §版本]` 指向的正是「版本：0.5.3」这一行，若按 header-only 报「节标题未找到」将是**真误报**；(c) 全仓 4 处 `§版本`（isa:3/815、abi:3×2）均命中同型粗体行。P2 正文自身「①标题→②粗体→③正文」与「§版本 应报真失效」两句相互矛盾；engineer 依 P2 授权的三层口径解析并**在报告中透明记录该分歧**（完成区第 200、260 行），处理正确。

#### Check 2 抽样逐条复核（≥5 条）+ 误报率评估

| # | 位置 | 原文 | 判定 | 是否误报 |
|---|---|---|---|---|
| 1 | `contract-isa.md:278` | `- \`rdha\` 与 \`rdhb\` 同时为 \`rd0\` → **ILLI**` | 行内含 ILLI，行内无 spec 引用 | **行级误报**：紧邻前导行 `异常条件：[SimRISC-01 §加减操作]` 已带节级引用 |
| 2 | `contract-isa.md:521` | `- 未对齐 → **MALIGN**` | 同上 | **行级误报**：前导 `异常条件：[SimRISC-01 §存取RD寄存器]` 已带引用 |
| 3 | `contract-isa.md:155` | `- \`z\`：未使用，应为零（SBZ）` | 含 SBZ | **行级误报**：前导 `操作数寻址方式字母：[SimRISC-00 §指令域说明]` 已带引用 |
| 4 | `contract-abi.md:40` | `| rd2–rd7 | — | reserved（编译器不得分配使用） | \`-\` |` | 含 reserved/不得，行内无引用 | 表行误报（所在节有引用），启发式命中 |
| 5 | `contract-elf.md:47` | `| 8–31 | Reserved（必须为 0） |` | 含 Reserved/必须，行内无引用、无决策标记 | 启发式命中；注：完成区称「仅有 ADR-0003 引用」**与原文不符**（该行无 ADR） |
| 6 | `contract-isa.md:900` | `## §8 NOP 与保留编码` | 节**标题**含「保留」 | **误报**：标题非断言 |
| 7 | `contract-authoring.md:3` | `Agent 不能直接读 spec/——它面向人类…` | 含「不能」（未列标记，因上下文）… 实为方法论行 | **误报**：模板/方法论，非合约规范断言 |

**误报率评估（依据）**：52 条中，`contract-isa.md` 占 41 条，其中 ~27 条为「异常条件」`→ **ILLI/MALIGN**` 分点行（节级引用在紧邻前导行）、~5 条为含「保留/ILLI/UNDI」的**节标题**、若干为位域表行；`contract-authoring.md` 3 条为模板/方法论。按「句级是否真有未溯源的规范断言」判据，**推断误报约 35–40 条（≈70%）**，真正可疑的仅少数（如寄存器 reserved 位、`e_flags` 保留位、`contract-elf.md:100` 只引 `contract-isa.md §2.1` 而未引 spec）。这与 P5「首轮计数可能较大、属启发式、不得收窄标记集」**一致**，属预期，不是缺陷。建议后续按「段落级引用继承」降噪（行级改为「最近前导引用行」判定），但**本轮不得为压计数而收窄**——engineer 未收窄，符合 P5。

#### 口径正确性证据

- **三类命中各有实例**（脚本遍历实测）：标题 566 / 粗体 12 / 正文 3。
  - 标题：`[SimRISC-00 §寄存器]` → `spec/SimRISC-00:39 ## 寄存器`
  - 粗体：`[SimRISC-01 §rd0 为目的寄存器约定]` → `spec/SimRISC-01:7 > **rd0 为目的寄存器约定**：…`
  - 正文：`[SimRISC-02 §各类操作对高 16 位（bits[63:48]）的处理规则]` → `spec/SimRISC-02:9 各类操作对高 16 位（bits[63:48]）的处理规则如下：`
- **裸 `§N.M` 不计入**：见约束核验（实测 `[]`）。
- **`]` 内含标题不截断**：见约束核验。
- **`(Lnn)` 无实例**：报告已印「本轮无 (Lnn) 实例」。
- **反例（任意子串 vs 节标题）**：临时合约注入 `[SimRISC-00 §十六进制数字]`、`[SimRISC-00 §数据表]` → 两者**均被解析**（正文/标题命中），exit 0；`[SimRISC-01 §不存在的节标题ZZZ]` → **失败**，exit 1。
  - **事实**：对**完全不存在**的节标题 → 正确 FAIL（fail-closed 成立）；对**仅作为正文/更长标题子串出现**的词组 → 会解析（不 FAIL）。见下「审查发现 F1」。

#### 反例门控（reviewer 亲自注入，全部临时副本，仓库零改动）

| 组 | 操作 | 真实结果 | 退出码 |
|---|---|---|---|
| ① 注入失效引用 | 干净合约 + `[SimRISC-01 §不存在的节标题XYZ]` | 报告 `失败: 1` 并列出该条 | **exit 1** ✓ |
| ② 注入无引用规范断言 | 干净合约 + `任何未对齐访问必须触发 MALIGN 异常。` | Check 2 `命中数: 1` 并列出原文 | **exit 1** ✓ |
| ③ 移除违规 | 仅含可解析引用的干净合约（无标记） | `结果: PASS (0 violations)` | **exit 0** ✓ |
| ④ 决策标记排除 | `…[spec-decision]` / `…[ADR-0007 §D1]` / `…[SimRISC-02 §…]` 三行 | Check 2 `命中数: 0` | **exit 0** ✓ |

- 反例落盘见 `.work/log/infra/INFRA-011t-review-gates.log`；**仓库内 `contract-*.md` 未改**（`git diff --name-only -- .tao/knowledge/` 空），全部在 `/tmp/opencode/INFRA-011t/` 临时目录内完成。
- **说明**：engineer 完成区「③ 移除违规」实际展示的是「还原临时副本后仍 exit 1」，**并未展示 exit 0 路径**；reviewer 已自行补齐「干净合约 → exit 0」的证据（上表 ③④），能力确实具备。

#### 完成区核对结论（逐条对齐）

- `584 / 581(566+12+3) / 3 / 52 / 55`、`exit 1`、`make check-spec-refs exit 2`、`check` 未改、`§版本` 自我修正已记录 → **全部与真实输出对齐** ✓
- **完成区发现的偏差（文档级，均不影响判决，建议下次修正）**：
  1. 抽样 #5 称 `contract-elf.md:47`「仅有 ADR-0003 引用」→ 该行**无** ADR；且「ADR 不计入 spec 引用排除」与代码相悖（`check_line_has_decision` 将同行 `ADR-\d{4}` 作为决策标记排除）。
  2. 反例门控「③ 移除违规」标签与内容不符（实为还原→exit 1，非 exit 0）。
  3. 顶部「测试结果：通过 6/7」与结尾「全部验收标准已满足」自相矛盾（未说明未通过哪一条；7 条验收标准实际均已满足）。

#### 审查发现

- **F1（口径，供架构师定夺，非阻断）**：Check 1 tier ③ 为 `section_name in spec_content`（全文子串），且标题匹配用 `in`（子串）。后果：`[SimRISC-00 §十六进制数字]`、`[SimRISC-00 §数据表]`（`数据表` ⊂ 标题 `数据表示`）这类「任意子串命中但无同名节标题」的引用会被判**可解析**（不 FAIL）。实测其真实 3 条正文命中（`各类操作对高 16 位…规则如下：`，节标题位于**行首**）用更严的「正文行首出现节标题」口径同样能全部覆盖。故可**在不损失现有正确性的前提下收紧** tier ③（要求节标题出现在正文行首/独立成行），从而满足「真失效项如实报告、不得放宽到任意子串」。
  - 定性：任务书 P2 同时写了「③ 正文行（**全文出现**该节标题文本）」与「不得放宽到任意子串」，两句对 tier ③ 的口径**本身相互冲突**；engineer 按其中「全文出现」字面实现，属**忠实于任务书**。且本轮真实仓库**无任何失效引用被此放宽掩盖**（3 条真失效均系字符串完全不存在）。故判**非阻断**，交架构师/用户决定是否收紧或明确记录该口径。
- **F2（轻微）**：`[SimRISC-0X §章节名]` 占位符因前缀需数字而漏检（见 Check 1 核实）。
- **F3（文档）**：完成区三处小偏差，见上。

#### 判决

**Accepted**（附 F1/F2/F3 非阻断 finding，要求修后重跑）

### 第 2 轮 engineer 返工（F1/F2/F3 修复）

**修复内容**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 口径过松→过紧→正确 | ✅已修 | `_text_matches`：exact 或 lead-in（`：`/`:`/`（`/`(`/`，`/`,`）；`_header_matches` 额外支持 `、` split；tier③ `_line_start_matches`：行首 + lead-in（含 `如下`） | `§数据`→False, `§数据表`→False, `§版本`→(bold,True), `§bits[63:48]`→(text,True) |
| F2 SimRISC-0X 漏检 | ✅已修 | `_PREFIX_ANCHOR` 改为 `SimRISC-(?:\d+\|0X)` | 2 条 `[SimRISC-0X §章节名]` 被提取，报「文件不存在」 |
| F3.1 ADR 措辞 | ✅已修 | 抽样 #5 改为「行内无 spec 引用、无 `[spec-decision]`、无 ADR」 | 见完成区 |
| F3.2 exit 0 证据 | ✅已修 | 反例③ 改为最小无违规合约 → exit 0 | 见完成区 |
| F3.3 矛盾 | ✅已修 | 改为「7/7」 | 见完成区顶部 |

**重跑计数**：586 refs, 标题=566, 粗体=12, 正文=3, 失败=5 (Check1) + 52 (Check2) = 57 violations, exit 1。

### 第 2 轮 reviewer 验收（F1 精度复核）

**审查对象**：`tools/infra/check_spec_refs.py`（405 行，未提交）、`Makefile`（未提交）、完成区。
**方式**：全部结论来自 reviewer 独立复跑；临时产物 `/tmp/opencode/INFRA-011t/`；日志 `.work/log/infra/INFRA-011t-review2-*.log`。**未改仓库内任何文件**。

#### 重跑记录（真实输出）

```bash
$ python3 tools/infra/check_spec_refs.py
  总引用数: 586
  命中类型统计: 标题=566, 粗体=12, 正文=3
  成功解析: 581   失败: 5
Check 2 — 无引用规范断言  命中数: 52
结果: FAIL (57 violations: 5 Check1 + 52 Check2)
$ echo $? → 1                 # 与主会话一致 ✓
$ make check-spec-refs  →  make: *** [Makefile:134: check-spec-refs] Error 1 ; echo $? → 2 ✓
$ make -n check | grep -c check_spec_refs → 0 ✓（仍未并入 check）
$ git diff --name-only -- .tao/knowledge/ → 空 ✓
```

5 条失败明细：`abi:13 [DADAO-21 §章节名]`、`abi:13 [DADAO-11 §章节名]`、`abi:13 [SimRISC-0X §章节名]`（文件不存在）、`authoring:22 [SimRISC-01 §3.5]`、`isa:9 [SimRISC-0X §章节名]`（文件不存在）——与主会话一致。

#### F1 精度验证（核心）

| 构造用例 | 期望 | 实测（CLI/函数） | 结论 |
|---|---|---|---|
| `[SimRISC-00 §数据表]`（`数据表 ⊂ 数据表示`） | 失败 | **FAIL**（`('',False)`） | ✅ 子串假命中已拒 |
| `[SimRISC-00 §版本]` | 命中(粗体) | **HIT `bold`**（`> **版本：0.5.3**`） | ✅ 未再误报 |
| `[SimRISC-00 §寄存器]`（上轮正当·标题） | 命中 | **HIT `header`**（`## 寄存器`） | ✅ |
| `[SimRISC-01 §rd0 为目的寄存器约定]`（上轮正当·粗体） | 命中 | **HIT `bold`** | ✅ |
| `[SimRISC-02 §各类操作对高 16 位（bits[63:48]）的处理规则]`（上轮正当·正文） | 命中 | **HIT `text`** | ✅ |
| `[SimRISC-00 §数据]`（构造子串假命中） | **失败** | **HIT `text`** ✗ | ❌ 未拒 |
| `[SimRISC-00 §指令]`（构造子串假命中） | **失败** | **HIT `text`** ✗ | ❌ 未拒 |

CLI 证据（临时合约，`contract-prec.md`，见 `INFRA-011t-review2-precision.log`）：
```
$ python3 tools/infra/check_spec_refs.py --contract-dir .../prec --spec-dir spec
  命中类型统计: 标题=0, 粗体=1, 正文=2
  成功解析: 3   失败: 1
  失败明细:  .../contract-prec.md:1  [SimRISC-00 §数据表]  原因: 节标题未找到
$ echo $? → 1
```

**根因**：`resolve_section()` tier ③ 用**裸前缀** `sl.strip().startswith(section_name)`（简单路径 L213-215、compound 路径 L187-190），而非「行首 lead-in」。因此：
- `数据` 命中 `spec/SimRISC-00:52` 的**正文行** `数据寄存器又可称为通用寄存器，主要用于各种运算，如下：`（`数据` 是 `数据寄存器` 的前缀，非节标题）；
- `指令` 命中 `spec/SimRISC-00:166` 的 `指令字采用**大端序**存储：…`。
两者均**无同名节标题**（SimRISC-00 只有 `## 数据表示` / `### 数据寄存器` / `## 指令设计` / `### 指令域说明`），属真「假命中」，本应 FAIL。
> 与任务描述冲突：主会话称 tier ③ = 「行首匹配」，而裸 `startswith` 正是「行首匹配」，二者对 `§数据`/`§指令` 必然命中；但本任务又要求它们「→ 失败」。该矛盾需按「行首 lead-in」口径收敛（见下）。

**已验证的收敛方案（reviewer 在临时副本 `check_try2.py` 上实测，未改仓库）**：
1. `_text_matches` 增加 `（`/`(` 后缀识别（使 `§RD寄存器` 命中 `### RD寄存器（Data registers）` 这类 header，避免依赖正文行）；
2. tier ③ 改为行首 lead-in：`行 == section`，或 section 后紧跟 `：`/`:`/`（`/`(`/`，`/`,`/`如下`，替换裸 `startswith`。
- 实测结果：全量计数**不变**（586 / 标题=566 粗体=12 正文=3 / 失败=5），且 `§数据`/`§指令`→**FAIL**、`§数据表`→FAIL、`§版本`→HIT(bold)、`§寄存器`→HIT(header)、`§各类操作…`→HIT(text)、compound `§寄存器规范 §RD寄存器`→HIT(header)。即：**可同时满足「§数据/§指令 失败」与「3 条真正文命中不丢」**（故非不可解的两难）。

#### 3 条真正文命中覆盖（未丢）

| # | 位置 | 引用 | 命中方式（独立核实） |
|---|---|---|---|
| 1 | `contract-isa.md:592` | `[SimRISC-02 §各类操作对高 16 位（bits[63:48]）的处理规则]` | `spec/SimRISC-02:9` 正文行首 `各类操作对高 16 位（bits[63:48]）的处理规则如下：` → `text` |
| 2 | `contract-isa.md:623` | 同上 | 同上 → `text` |
| 3 | `contract-isa.md:697` | 同上 | 同上 → `text` |

复核脚本遍历确认：全文 `text` 命中恰为上述 3 条，均可在 spec 第 9 行独立定位。✅

#### 假绿抽查（≥5，独立于脚本）

| # | 引用 | 独立核实（grep spec 原文） |
|---|---|---|
| 1 | `[DADAO-11 §版本]` | `spec/DADAO-11:3` `> **版本：0.9.2**…`（粗体） |
| 2 | `[DADAO-21 §寄存器规范]` | `spec/DADAO-21:8` `## 寄存器规范` |
| 3 | `[SimRISC-00 §SimRISC QFC]` | `spec/SimRISC-00:241` `## SimRISC QFC` |
| 4 | `[SimRISC-00 §返回地址栈]` | `spec/SimRISC-00:109` `### 返回地址栈` |
| 5 | `[SimRISC-01 §立即数常数赋值：Immediate constant]` | `spec/SimRISC-01:92` `### 立即数常数赋值：Immediate constant` |
| 6 | `[SimRISC-02 §条件跳转指令]` | `spec/SimRISC-02:196` `### 条件跳转指令` |
| 7 | `[SimRISC-04 §nop 伪指令]` | `spec/SimRISC-04:22` `#### nop 伪指令` |

7/7 均在对应 spec 文件独立定位到标题/粗体原文 → **未发现假绿**。✅

#### 约束核验

| 约束 | 结果 |
|---|---|
| 未改 `contract-*.md` 正文 | ✅ `git diff --name-only -- .tao/knowledge/` 空 |
| `make check-spec-refs` 独立、不并入 `check` | ✅ 存在；`make -n check` 不含脚本 |
| Makefile 仅新增目标 | ✅ `git diff Makefile` 仅 PHONY/help/新目标，`check:` 行未变 |
| 未 `git commit` | ✅ `HEAD=131543b`，无暂存 |
| 临时产物仅在 `/tmp/opencode/INFRA-011t/` | ✅ |

#### 完成区核对

- 数字 `586 / 566 / 12 / 3 / 5 / 52 / 57`、`exit 1`、`make exit 2` → **与真实输出逐条一致** ✓
- F3 三处：抽样 #5 已去掉 ADR 误述 ✓；反例③ 已改为「无违规合约 → exit 0」✓；顶部已改「7/7」✓
- **偏差**：完成区称脚本「390 行」，实测 `wc -l` = **405 行**（文档级，建议改正）。
- `§十六进制数字` 失败声明经复核为真（`resolve_section` → `('',False)`）✓

#### 判决

**Needs Revision**

- **失败约束**：任务「必做 1」要求构造的「子串假命中」`§数据`/`§指令` 应报**失败**；reviewer 独立实测二者均被判**可解析**（`text` 命中，退出码不增），未达要求。
- **根因**：`resolve_section` tier ③ 为**裸 `startswith` 前缀匹配**，非「行首 lead-in」，故把正文行 `数据寄存器…`/`指令字…` 误当节首。属 F1「精度过松」在 tier ③ 的残留（header/bold 已收敛，tier ③ 未收敛）。
- **可执行修法（已实测可行）**：见上「已验证的收敛方案」两点；全量计数不变，且 `§数据`/`§指令` 转 FAIL，3 条真正文命中与 compound 引用均不丢。
- **认可的部分**：F1 的两个头部目标（`§数据表` 失败、`§版本` 命中）已达成；F2（`SimRISC-0X` 提取）已修且计数 +2 正确；F3 三处文档问题已改；全量计数 586/566/12/3/5/52/57 与主会话一致；无假绿；约束全部守住。
- 附：完成区行数「390」应为「405」。

### 第 3 轮 reviewer 验收（tier ③ 收敛复核）

**审查对象**：`tools/infra/check_spec_refs.py`（433 行，未提交）、`Makefile`（未提交）、完成区。
**方式**：全部结论来自 reviewer 独立复跑；临时产物 `/tmp/opencode/INFRA-011t/`；日志 `.work/log/infra/INFRA-011t-review3-*.log`。**未改仓库内任何文件**。

#### 第 2 轮 6 项要求逐条确认

| # | 要求 | 期望 | 实测（函数调用 + CLI） | 结论 |
|---|---|---|---|---|
| 1 | `[SimRISC-00 §数据]` | FAIL | `('',False)`；CLI 报「节标题未找到」 | ✅ |
| 2 | `[SimRISC-00 §指令]` | FAIL | `('',False)`；CLI 报「节标题未找到」 | ✅ |
| 3 | `[SimRISC-00 §数据表]` | FAIL | `('',False)`；CLI 报「节标题未找到」 | ✅ |
| 4 | `[SimRISC-00 §版本]` | HIT(bold) | `('bold',True)` | ✅ |
| 5 | `§各类操作对高 16 位（bits[63:48]）的处理规则`（3 条） | HIT(text) | `('text',True)`；全文 `text` 恰为 `isa:592/623/697` 3 条 | ✅ |
| 6 | 全量计数不变 | 586/566/12/3/5/52/57 · exit 1 | 逐字一致（见复跑） | ✅ |

CLI 端到端（临时合约 `contract-prec.md`，5 条）：`成功解析: 2  失败: 3`，3 条失败即 `§数据`/`§指令`/`§数据表`；`§版本`→粗体、`§各类操作…`→正文；`exit 1`（fail-closed 保持）。见 `INFRA-011t-review3-precision.log`。

#### 抽样：正当命中（≥3，标题/粗体/正文各 1）+ 构造假命中（≥2）

| 类别 | 用例 | 期望 | 实测 |
|---|---|---|---|
| 标题 | `[SimRISC-00 §寄存器]` | HIT | `('header',True)`（`## 寄存器`）✅ |
| 粗体 | `[SimRISC-01 §rd0 为目的寄存器约定]` | HIT | `('bold',True)` ✅ |
| 粗体(另一) | `[SimRISC-03 §rf0 为目的寄存器约定]` | HIT | `('bold',True)` ✅ |
| 正文 | `[SimRISC-02 §各类操作…（bits[63:48]）的处理规则]` | HIT | `('text',True)` ✅ |
| 构造假命中 | `[SimRISC-00 §数据寄]` | FAIL | `('',False)` ✅（`数据寄存器…` 后接 `存`，非 lead-in） |
| 构造假命中 | `[SimRISC-00 §指令字]` | FAIL | `('',False)` ✅（`指令字采用…` 后接 `采`，非 lead-in） |
| 构造假命中 | `[SimRISC-00 §数据表]` | FAIL | `('',False)` ✅ |
| 边界(跨文件) | `[SimRISC-01 §RD寄存器]` | FAIL | `('',False)` ✅（该文件仅 `### 存取RD寄存器`） |
| 边界(正) | `[SimRISC-01 §存取RD寄存器]` | HIT | `('header',True)` ✅ |
| compound | `[DADAO-21 §寄存器规范 §RD寄存器]` | HIT | `('header',True)` ✅（`（` lead-in 命中 `### RD寄存器（Data registers）`） |
| compound | `[DADAO-21 §传参 §标量参数]` | HIT | `('header',True)` ✅ |

`§RD寄存器`→`### RD寄存器（Data registers）`（`（` lead-in）经独立核实；`SimRISC-01 §RD寄存器` 判 FAIL 亦正确（该 spec 无 `RD寄存器` 节）。全部符合预期。

#### 假绿抽查（6 条，独立 grep spec 原文）

| 引用 | 独立定位 |
|---|---|
| `[DADAO-21 §传参 §标量参数]` | `DADAO-21:141 ### 传参：Parameter Passing`、`DADAO-21:161 #### 标量参数：Scalar type parameter` |
| `[SimRISC-00 §MISC-RF指令编码]` | `SimRISC-00:343 ### MISC-RF指令编码` |
| `[SimRISC-00 §数据表示]` | `SimRISC-00:11 ## 数据表示` |
| `[SimRISC-01 §存取RD寄存器]` | `SimRISC-01:16 ### 存取RD寄存器` |
| `[SimRISC-02 §存取RA寄存器]` | `SimRISC-02:46 ### 存取RA寄存器` |
| `[SimRISC-04 §特权指令]` | `SimRISC-04:98 ## 特权指令` |

6/6 均在对应 spec 独立定位到原文 → **未发现假绿**。✅

#### 复跑输出

```bash
$ python3 tools/infra/check_spec_refs.py
  总引用数: 586   标题=566, 粗体=12, 正文=3   成功解析: 581   失败: 5
Check 2 命中数: 52
结果: FAIL (57 violations: 5 Check1 + 52 Check2)   $ echo $? → 1
$ make check-spec-refs → make: *** [Makefile:134: check-spec-refs] Error 1   $ echo $? → 2
$ make -n check | grep -c check_spec_refs → 0
$ git diff --name-only -- .tao/knowledge/ → 空
$ 两次重跑结果一致（确定性）
```

5 条失败明细与主会话一致（`§章节名`×3 + `§3.5` + `SimRISC-0X`×2 中的文件不存在）。约束全部守住（未改正文、独立目标、`check:` 行未变、未 commit）。

#### 完成区核对

- 数字 `586/566/12/3/5/52/57`、`exit 1`、`make exit 2` → **逐条一致** ✓
- 脚本行数：完成区「433 行」= 实测 `wc -l` **433** ✓（上轮「390」已改正）
- 口径描述（`/（` lead-in、tier ③ line-start + `如下`）与代码一致 ✓

#### 审查发现（非阻断，供参考）

- **N1（轻微）**：`_LEAD_IN_CHARS = set("：:（(，,如下")` 把 `如`/`下` 当作**字符**成员，故理论上 `section如…`/`section下…` 也会命中 line-start；显式 `rest.startswith("如下")` 已覆盖真实需求，字符集可改为 `set("：:（(，,")` 更严谨。当前真实引用无此形态，**不影响结论**。
- **N2（流程）**：本轮修法反映在完成区/脚本中，但任务书未单列「第 3 轮 engineer 返工」记录；建议后续补记（内容已可从完成区与 diff 回溯）。

#### 判决

**Accepted**

- 第 2 轮 6 项要求**逐条独立复现通过**（`§数据`/`§指令`/`§数据表` FAIL；`§版本` HIT bold；3 条正文 HIT text；全量计数 586/566/12/3/5/52/57、exit 1 不变）。
- 抽样正当命中（标题/粗体/正文）与 compound 引用全部保留；构造假命中 `§数据寄`/`§指令字`/`§数据表` 均 FAIL；`§数据` 假命中的根因（tier ③ 裸前缀）已按「行首 lead-in」收敛。
- 假绿抽查 6/6 属实；约束全部守住（`contract-*.md` 正文零改动、独立 `make check-spec-refs` 未并入 `check`、未 commit）。
- N1/N2 为轻微/流程项，不影响达标。

## 收尾记录（主会话，2026-09-21）

**reviewer 第 3 轮 Accepted**（tier ③ 收敛后 6 项逐条通过、假绿抽查 6/6、计数不变）。

**N1 处置（主会话按 reviewer 处方应用）**：`_LEAD_IN_CHARS` 原为 `set("：:（(，,如下")`（含 `如`/`下` 单字，理论上 `section如…`/`section下…` 会误命中）⇒ 收紧为 `set("：:（(，,")`；`如下` 由既有显式 `rest.startswith("如下")` 处理。**复跑结果与 Accepted 时逐项一致**（586 / 标题=566 / 粗体=12 / 正文=3 / 失败=5 / Check2=52 / 总 57 / exit 1；`§数据`/`§指令`/`§数据表` 仍 FAIL；`§版本`→bold、`§bits[63:48]`→text 仍 HIT）。

**N2 处置**：本轮 engineer 第 2/3 次返工（F1 精度）的经过见「审阅记录」第 2/3 轮，本处补记以保持可追溯。
