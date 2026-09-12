# VERIF-011t: spec 引用审计器

**模块**：verif
**项目里程碑**：M1
**依赖**：`SPEC-002t`、`SPEC-008t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `.tao/knowledge/contract-*.md`（被审计对象，当前为 `contract-isa.md`）
  - `spec/*.md`（引用目标，`SimRISC-00`~`04` 及 DADAO 系列）
- 输出：
  - `verif/check_spec_refs.py`：spec 引用审计脚本
  - 首轮审计报告（完成区，含两类违规计数 + 明细）
- 约束：
  - **不得改 `contract-*.md` 正文来凑绿**：不许编造/删改引用，不许删规范断言；报告是交付物
  - 不并入 `make check`，新增独立 `make check-spec-refs`（首轮必然有违规）
  - 裸 `§N.M` 是合约内部引用，不在审计范围
  - 检查类脚本放 `verif/`（与 `validate_encoding.py` 一致）

## 背景（完整）

### 目标

把翻译链 `spec → contract → test → QEMU/LLVM` 中最弱环「spec→contract」机械审计，产出 `verif/check_spec_refs.py` + 首轮审计报告，做两项检查：

1. **引用有效性**：`contract-*.md` 中每个 `[SimRISC-XX §…]` 引用可解析到 `spec/` 真实内容（文件存在；节标题存在）。
2. **无引用规范断言**：`contract-*.md` 中含规范性断言（ILLI/UNDI/MALIGN/IALIGN 等）却既无 `[SimRISC-XX §…]` 也无显式自主决策标记的句子。

### 设计理由

合约的每个规范性期望值必须能回溯到 `spec/`，否则实现方（LLVM/QEMU/golden）会各按理解实现，差分验证失去基准。引用有效性保证「引了但引错」被发现；无引用断言保证「没引也没声明是自主决策」的真空断言被发现。

### 关键概念 / 数据

**引用格式（v5 `contract-isa.md` 实际形态）**：

- 文件前缀 + 节标题：`[SimRISC-00 §版本]`、`[SimRISC-01 §rd0 为目的寄存器约定]`、`[SimRISC-02 §函数返回]`
- 行号（部分 `wiki_cite` 字段含）：`SimRISC-01 §rd0 为目的寄存器约定 (L7)`、`(L37)`
- 文件名多为**前缀**（`SimRISC-01` → `spec/SimRISC-01-数据类指令.md`），需前缀匹配到真实文件
- **排除**：裸 `§1.3`/`§5.1` 等是合约内部引用，不在审计范围

**Check 1 — 引用有效性**：提取所有 `[SimRISC-XX §…]`（不含裸 `§N.M`），按 `<file>` / `<file> §<节标题>` / `<file> §<节标题> (L<n>)` 解析；文件前缀匹配 `spec/*.md`；节标题验证 spec 文件内有匹配的 `#{1,4} <标题>` 标题；行号验证该行存在。报告每个无法解析的引用（file:line + 原文 + 失败原因）。

**Check 2 — 无引用规范断言**：扫描 `contract-*.md` 含规范标记（`ILLI`/`UNDI`/`MALIGN`/`IALIGN`，可含 `保留`/`reserved`/`必须` 等）的行/块；若既无 `[SimRISC-XX §…]` 也无显式自主决策标记（如行内 `[spec-decision]` 或引用 `ADR-000N`）→ 报「无引用断言」。

**输出**：结构化报告（两类违规计数 + 明细 file:line）；有违规时**非零退出**（fail-closed）。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-039a-wiki-ref-auditor.md`（完整转述：背景、spec.md 引用格式多样性、Check 1/Check 2 规格、首轮审计报告要求、约束、过程要求、验收、完成区首轮 57 条问题、代码级 Architecture Review）

## 交付物

- `verif/check_spec_refs.py`：spec 引用审计脚本（Check 1 + Check 2，fail-closed）
- 首轮审计报告（完成区，原始终端输出 + 分类明细）
- Makefile 独立目标需求：`make check-spec-refs`（不并入 `check`）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **wiki → spec**：0.4.1 审计对象是 `contracts/isa/spec.md`，引用目标是 DADAO-0628 的 wiki 参考（外部，`[wiki §…]`）；v5 **无 wiki**，审计对象是 `.tao/knowledge/contract-*.md`，引用目标是 `spec/*.md`（`[SimRISC-XX §…]`）。
2. **引用标记**：`[wiki §SimRISC-01 L87]` → `[SimRISC-01 §rd0 为目的寄存器约定]`（v5 用节标题为主，行号出现在部分 `wiki_cite` 字段的 `(Lnn)`）。
3. **文件前缀解析**：`SimRISC-01` → `spec/SimRISC-01-数据类指令.md`（前缀匹配），与 0.4.1 的 wiki 文件名前缀匹配同理但目标目录不同。
4. **审计对象范围**：v5 审计全部 `contract-*.md`（当前含 `contract-isa.md`；后续 ABI/ELF/SBI 合约加入后自动纳入）。
5. **脚本路径**：`scripts/check_wiki_refs.py` → `verif/check_spec_refs.py`；make 目标 `check-wiki-refs` → `check-spec-refs`。
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

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-039a-wiki-ref-auditor.md`
- DADAO-0628：`.work/DADAO-0628/scripts/check_wiki_refs.py`
- 本项目：`.tao/knowledge/contract-isa.md`、`spec/SimRISC-00-指令系统设计.md` ~ `spec/SimRISC-04-系统类指令.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `python3 verif/check_spec_refs.py` 可运行，输出 Check 1/Check 2 两类违规计数 + 明细（file:line + 原因）
2. 有违规时 exit 非零（fail-closed）；无违规时 exit 0
3. 引用解析覆盖 `[SimRISC-XX §<节标题>]` 与带 `(Lnn)` 形态，裸 `§N.M` 不计入
4. `[spec-decision]`/ADR 标记可排除对应断言
5. 未修改 `contract-*.md` 正文（diff 确认）
6. 独立 `make check-spec-refs` 存在且不并入 `make check`
7. 完成区粘贴首轮审计真实 stdout，数字来自实跑

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
