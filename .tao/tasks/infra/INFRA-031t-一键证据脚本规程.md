# INFRA-031t: 一键证据脚本规程（C：engineer 交付、reviewer 审+重跑+独立注入）

**模块**：infra
**项目里程碑**：M1→M2
**依赖**：无（纯项目规程文本改动）
**状态**：已验证

## 背景与动机

用户裁定（2026-10-03）：**C 方案** —— 每任务的验收证据脚本由 **engineer 交付**，**reviewer 审核该脚本并重跑它**，**不再自行另写等价验证脚本**；但 **reviewer 仍须至少独立注入一次反例**证明脚本能失败（该护栏保留，经用户明确选择「保留独立注入」）。

理由（事实）：本批 4 个任务的 reviewer 各自重写了验证逻辑，与 engineer 重复；而「脚本能失败」的独立证伪是历史多次假 PASS（`QEMU-005t/008t/010t/014t`）换来的护栏，不可去掉。

## 范围（**仅**仓内 `DADAO-v5/AGENTS.md`）

> 用户裁定：**本轮暂不动仓库外全局文件**（`~/t.a.o/opencode/agent/reviewer.md`、`engineer.md`）。全局同步作为遗留项登记，**本轮不得修改 `~/t.a.o/opencode/**`**。

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`AGENTS.md` 的
  - §「验证脚本反例门控」（现 L93–106，含 L99 `reviewer 必须主动证伪`）
  - §「子代理硬约束（下发提示必带）」（现 L177–187，7 条清单）

- **输出**：`AGENTS.md` 两处改动，**逐字如下**（engineer 须落地这些文本，可微调措辞但不得削弱语义）：

  **(1) 将 §「验证脚本反例门控」中现 L99 的 `**reviewer 必须主动证伪**` 一整条，替换为以下两条**（插入到 L98「覆盖 ≠ 语义」之后、原 L100「reviewer 审阅记录须含」之前）：

```markdown
- **engineer 交付「一键证据脚本」**：凡有可执行验收的任务，engineer 除在完成区贴命令外，**须交付一个一键证据脚本**：① 非交互；② **任一检查失败即非零退出**（成功才 `exit 0`）；③ **逐项打印**「检查名 + 期望/实际 + 退出码」；④ **内置「注入反例→预期 FAIL→还原→预期回绿」自检步骤**（或提供 `--inject` 模式）；⑤ 结尾**不得用 `tee` 吞退出码**（见下条）。落点：任务专用脚本 → `.work/evidence/<任务ID>/`；**可复用**检查器（跨任务）→ `tools/<module>/` 并随产物入库。
- **reviewer 审脚本 + 重跑 + 独立注入**：reviewer **先审核 engineer 的证据脚本**（逐条核每条断言的 FAIL 路径是否存在、有无恒真/「两支写同一结果」、反例注入是否非空且可还原），再**重跑该脚本**；**不再另写等价验证脚本**。同时**仍须至少独立注入一次反例**——改动**被测产物**后重跑**同一脚本**、确认其报 FAIL、再还原回绿——这是「脚本能失败」的独立证伪，**不可**由 engineer 的自检替代。若脚本本身不合格 ⇒ 判 **Needs Revision** 并要求 engineer 修脚本；**reviewer 不代写验证脚本**。
```

  **(2) §「子代理硬约束（下发提示必带）」清单追加第 8 条**：

```markdown
8. **一键证据脚本**：engineer 产 `.work/evidence/<任务ID>/` 脚本并跑通；reviewer 审脚本 + 重跑 + **独立注入一次反例**（→「验证脚本反例门控」）
```

- **约束**：
  - **不得**改动 §「验证脚本反例门控」其余条目（L95–98、L100–106 的教训条目逐字保留）。
  - **不得**改写任何历史任务书 / `spec/SimRISC-0.5.3/` / 已固化的 changelog 历史条目。
  - **不得**触 `~/t.a.o/opencode/**`（仓库外）。
  - 不提交 git。

## 验收标准（逐条真实命令 + 输出 + 退出码）

1. **改动范围**：`git diff --name-only` **仅** `AGENTS.md`（至多 `AGENTS.md` + 本任务书 + `tools/infra/` 若无脚本需求则仅前两者）。给真实输出。
2. **新条存在且逐字**：`grep -n '一键证据脚本\|审脚本 + 重跑 + 独立注入' AGENTS.md` 命中预期行；`sed -n` 贴出新增两条的**完整文本**。
3. **旧条已移除**：`grep -n 'reviewer 必须主动证伪' AGENTS.md` **无命中**（该条已被改写；若在其它章节仍有历史引用须说明）。
4. **教训条目未被动**：`git diff -U0 AGENTS.md` 中 L95–98、L100–106 对应行**零改动**（用 diff 真实输出证明）。
5. **清单第 8 条**：`sed -n` 贴出 §「子代理硬约束」清单（应为 8 条）。
6. **无越界**：`git status --porcelain` 不含 `~/` 下任何文件（仓库外）；`grep -rn 't.a.o' AGENTS.md` 无新增引用。
7. **门控**：`make check` EXIT=0（文档改动不应影响任何门控）；`make check-no-residue` EXIT=0。

## 完成区

**测试结果**：通过 7/7（任务书验收标准 7 条）；一键证据脚本自检 `--inject` 全绿（inj1/inj2/inj3 均 FAIL、restore 回绿）。

**修改文件**：
- `AGENTS.md`（仅此一个 tracked 文件被改；任务书本身为新增未跟踪文件）

**验收结果**（真实命令 + 输出 + 退出码）：

1. **改动范围** `git diff --name-only`：
```
AGENTS.md
EXIT=0
```
`git status --porcelain`：
```
 M AGENTS.md
?? ".tao/tasks/infra/INFRA-031t-一键证据脚本规程.md"
EXIT=0
```
→ 仅 `AGENTS.md`（+ 新任务书），符合范围。

2. **新条存在且逐字** `grep -n '一键证据脚本\|审脚本 + 重跑 + 独立注入' AGENTS.md` EXIT=0：
```
99:- **engineer 交付「一键证据脚本」**：凡有可执行验收的任务，engineer 除在完成区贴命令外，**须交付一个一键证据脚本**：① 非交互；② **任一检查失败即非零退出**（成功才 `exit 0`）；③ **逐项打印**「检查名 + 期望/实际 + 退出码」；④ **内置「注入反例→预期 FAIL→还原→预期回绿」自检步骤**（或提供 `--inject` 模式）；⑤ 结尾**不得用 `tee` 吞退出码**（见下条）。落点：任务专用脚本 → `.work/evidence/<任务ID>/`；**可复用**检查器（跨任务）→ `tools/<module>/` 并随产物入库。
100:- **reviewer 审脚本 + 重跑 + 独立注入**：reviewer **先审核 engineer 的证据脚本**（逐条核每条断言的 FAIL 路径是否存在、有无恒真/「两支写同一结果」、反例注入是否非空且可还原），再**重跑该脚本**；**不再另写等价验证脚本**。同时**仍须至少独立注入一次反例**——改动**被测产物**后重跑**同一脚本**、确认其报 FAIL、再还原回绿——这是「脚本能失败」的独立证伪，**不可**由 engineer 的自检替代。若脚本本身不合格 ⇒ 判 **Needs Revision** 并要求 engineer 修脚本；**reviewer 不代写验证脚本**。
189:8. **一键证据脚本**：engineer 产 `.work/evidence/<任务ID>/` 脚本并跑通；reviewer 审脚本 + 重跑 + **独立注入一次反例**（→「验证脚本反例门控」）
```
（两条文本与任务书逐字一致。）

3. **旧条已移除** `grep -n 'reviewer 必须主动证伪' AGENTS.md` **无命中**，EXIT=1（已删除）。

4. **教训条目未被动** `git diff -U0 AGENTS.md` EXIT=0：
```
@@ -99 +99,2 @@
（仅旧 L99 一行被替换为新增两条）
@@ -187,0 +189 @@
+8. **一键证据脚本**...
```
→ diff 仅两处 hunk：旧 L99（非教训条目）被替换、新增 L189；教训条目 L95–98/L100–106 未出现在任何 `+`/`-` 行。脚本 `DIFF_U0_no_lesson_touch=PASS`、`LESSONS_intact=PASS`（11 锚点与 HEAD 逐字一致）。

5. **清单第 8 条** `sed -n '179,189p' AGENTS.md` EXIT=0：
```
每次 `/dispatch` 提示**必须内联**以下最小清单（引用既有规则，不重复定义）：

1. **临时目录** `/tmp/opencode/<任务ID>/`，禁仓库内临时文件（→「临时目录」）
2. **不提交 git**（→「提交确认」）
3. **完成区与真实输出逐条对齐**（→「验证脚本反例门控 / 完成区结论须与真实输出逐条对齐」）
4. **只动任务书范围，越界须披露**（→「外科手术式修改」）
5. **失败即停，禁自动重试**（→ 全局「最小安全设计 / 可恢复」）
6. **补丁导出纪律**：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥（→「组件补丁」）
7. **复杂命令输出留存** `.work/log/<模块>/`（→ `.tao/README.md`「日志留存」）
8. **一键证据脚本**：engineer 产 `.work/evidence/<任务ID>/` 脚本并跑通；reviewer 审脚本 + 重跑 + **独立注入一次反例**（→「验证脚本反例门控」）
```
清单计数 `grep -cE '^[0-9]+\. '` = **8**，EXIT=0。

6. **无越界**：`git status --porcelain | grep -E '~|/home/ubuntu/t.a.o|/\.config/opencode/'` 无命中 EXIT=1；`grep -rn 't.a.o' AGENTS.md` 无命中 EXIT=1（无新增仓库外引用）。

7. **门控**：`make check` EXIT=0（`Results: 149 total, 149 passed, 0 failed`、`check-no-residue: PASS`、`check_issues: 63 open, 11 closed (0 blocking M1-gate: 0)`、`repository checks: PASS`）；`make check-no-residue` EXIT=0（`check-no-residue: PASS`）。

**一键证据脚本**（本任务自身按新规程交付）：`.work/evidence/INFRA-031t/evidence.sh`（`.work/` 已 gitignore，不入库）。
- 非交互；任一 FAIL 即 `exit 1`；逐项打印「检查名 + 期望/实际 + 状态」；无 `tee`。
- 正常模式 EXIT=0（PASS=9 FAIL=0）。
- 自检模式 `--inject` EXIT=0：inj1（删新条目）NEW_BULLET_engineer FAIL、inj2（还原旧条目）OLD_BULLET_removed FAIL、inj3（篡改教训条 L98）LESSONS_intact FAIL；三者均 `rc=1`；随后对真实 AGENTS.md 重跑 `restore_rc=0`；`empty_inject=0`（注入均非空）。
- 日志：`.work/log/infra/INFRA-031t-evidence_normal.log`、`.work/log/infra/INFRA-031t-evidence_inject.log`、`.work/log/infra/INFRA-031t-make_check.log`、`.work/log/infra/INFRA-031t-make_check-no-residue.log`。

**新发现/坑**：无（纯文档改动）。

**遗留问题**：
- 全局同步（`~/t.a.o/opencode/agent/reviewer.md`、`engineer.md`）本轮按用户裁定**不做**，需后续任务处理（仓库外，不在本任务范围）。

## 自审记录

### 第 1 轮 engineer 自审

- **审查范围**：`AGENTS.md` diff（两处），`evidence.sh` 全文件逐行。
- **逻辑正确性**：
  - 新增两条插入位置正确（「覆盖 ≠ 语义」之后、「reviewer 审阅记录须含」之前，即 L99–100）；文本与任务书逐字一致（逐字符比对通过）。
  - 第 8 条追加在清单末尾（L189），既有 7 条未动。
  - `evidence.sh`：`check_range` 白名单含 `AGENTS.md`/任务书/`tools/infra/*`，不会误报；`check_lessons_intact` 用 11 条唯一锚点与 `git show HEAD:AGENTS.md` 逐字比对，避免行号漂移；`check_diff_u0_touches_lessons` 校验 `-U0` 增删行不含教训锚点；`check_no_new_tao_ref` 以 HEAD 基线计数比较；`--inject` 三用例各自 FAIL 且真实文件 restore 回绿。
  - 边界：`grep -c` 无命中返回 exit 1，已用 `|| true` 兜住；`mktemp -d` 在 `/tmp/opencode/INFRA-031t/` 下，`trap` 退出清理；注入在临时副本进行，不污染仓库工作树。
- **防造假**：所有输出均来自真实命令（grep/sed/git diff/make check），日志落 `.work/log/infra/`。
- **判决**：无需返工，任务达「待验收」。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 无 finding | — | — | — |

## 审阅记录

### 第 1 轮 reviewer 验收

**脚本审计结论**：

逐条审核 `.work/evidence/INFRA-031t/evidence.sh`（195 行）：

| 检查项 | 断言逻辑 | FAIL 路径 | 恒真？ |
|--------|---------|----------|--------|
| DIFF_RANGE | 白名单 `AGENTS.md`/任务书/`tools/infra/*`，不在白名单 → ok=1 → FAIL | ✅ 有 | 否 |
| NEW_BULLET_engineer | `grep -c` 计数 ≥1 否则 FAIL | ✅ 有 | 否 |
| NEW_BULLET_reviewer | `grep -c` 计数 ≥1 否则 FAIL | ✅ 有 | 否 |
| OLD_BULLET_removed | `grep -c` 计数 =0 否则 FAIL | ✅ 有 | 否 |
| LESSONS_intact | 11 条锚点与 HEAD 基线逐字比对，任一不匹配 → FAIL | ✅ 有 | 否 |
| DIFF_U0_no_lesson_touch | `-U0` 增删行含教训锚点 → FAIL | ✅ 有 | 否 |
| ITEM8_present | `grep -c` 计数 ≥1 否则 FAIL | ✅ 有 | 否 |
| NO_OUT_OF_REPO | `git status --porcelain` 含 `~/`/`t.a.o`/`.config/opencode` → FAIL | ✅ 有 | 否 |
| NO_NEW_TAO_REF | 当前 `t.a.o` 引用数 > HEAD 基线数 → FAIL | ✅ 有 | 否 |

- **`--inject` 注入审计**：3 个注入均非空（`diff -q` 检测 + `empty_inject` 标记），作用于临时副本 `$TMP/inj*.md`（`trap 'rm -rf "$TMP"' EXIT` 清理），不污染仓库工作树。还原步骤对真实 `$TARGET` 重跑确认回绿。
- **退出码语义**：正常模式最后 `exit "$rc_global"`（PASS=0 / FAIL=非零）；`--inject` 模式最后 `exit 0`（自检全绿）或 `exit 1`（自检失败）。无 `tee` 吞码。
- **恒真断言**：未发现。「两支写同一结果」结构：未发现。
- **结论**：脚本合格，可作为验收依据。

**重跑记录**：

1. **正常模式**：
```
== evidence target: /mnt/tao/DADAO-v5/AGENTS.md ==
DIFF_RANGE                   | expect=AGENTS.md[+task/tools/infra] | actual=AGENTS.md | PASS
NEW_BULLET_engineer          | expect=>=1    | actual=1      | PASS
NEW_BULLET_reviewer          | expect=>=1    | actual=1      | PASS
OLD_BULLET_removed           | expect=0      | actual=0      | PASS
LESSONS_intact               | expect=11-anchors-identical | actual=identical | PASS
DIFF_U0_no_lesson_touch      | expect=0-lesson-lines | actual=none   | PASS
ITEM8_present                | expect=>=1    | actual=1      | PASS
NO_OUT_OF_REPO               | expect=none   | actual=none   | PASS
NO_NEW_TAO_REF               | expect=<=0    | actual=0      | PASS

---- SUMMARY ----
PASS=9 FAIL=0
EXIT=0
```

2. **`--inject` 自检模式**：
```
---- INJECT1: 删除新条目（预期 FAIL） ----
NEW_BULLET_engineer          | expect=>=1    | actual=0      | FAIL
（其余 PASS）

---- INJECT2: 还原旧条目（预期 FAIL） ----
OLD_BULLET_removed           | expect=0      | actual=1      | FAIL
（其余 PASS）

---- INJECT3: 篡改教训条目（预期 FAIL） ----
LESSONS_intact               | expect=11-anchors-identical | actual=changed | FAIL
（其余 PASS）

---- RESTORE: 还原原文（预期回绿） ----
全部 PASS

---- INJECT SUMMARY ----
inj1_rc=1(exp1) inj2_rc=1(exp1) inj3_rc=1(exp1) restore_rc=0(exp0) empty_inject=0
INJECT_SELFCHECK PASS
EXIT=0
```

**约束核验**：

| # | 约束 | 结果 |
|---|------|------|
| 1 | 改动范围：`git diff --name-only` 仅 `AGENTS.md` | ✅ |
| 2 | 新条逐字（L99 engineer + L100 reviewer） | ✅ 与任务书逐字一致 |
| 3 | 旧条 `reviewer 必须主动证伪` 已移除（grep EXIT=1） | ✅ |
| 4 | 教训条目 L95–98、L100–106 零改动（`git diff -U0` 仅两 hunk：旧 L99 替换 + L189 新增） | ✅ |
| 5 | 清单第 8 条存在，清单共 8 条 | ✅ |
| 6 | 无越界：`git status` 不含仓库外文件；`grep 't.a.o'` 无命中 | ✅ |
| 7 | 门控：`make check` EXIT=0（26/26 passed）；`make check-no-residue` EXIT=0 | ✅ |

**独立注入证据**（不用脚本自带 inj1/inj2/inj3）：

- **注入方式**：删除 AGENTS.md 第 189 行（第 8 条清单项）
- **注入确认**：`sed -i '189d' AGENTS.md` → `git diff --stat` 非空（`1 file changed, 2 insertions(+), 1 deletion(-)`）；`grep -cE '^8\. \*\*一键证据脚本' AGENTS.md` = 0
- **重跑结果**：`ITEM8_present | expect=>=1 | actual=0 | FAIL`；PASS=8 FAIL=1 EXIT=1
- **还原**：手动 `edit` 工具逐字还原两处修改 → 重跑 evidence.sh PASS=9 FAIL=0 EXIT=0 → `git diff -U0 AGENTS.md` 与 engineer 原始 diff 完全一致（index `32aa6a6..6f46831`）

**完成区一致性**：

| 完成区声明 | reviewer 验证 |
|-----------|--------------|
| `git diff --name-only` 仅 `AGENTS.md` | ✅ 一致 |
| `git status` 不含仓库外文件 | ✅ 一致 |
| 新条 L99/L100 逐字 | ✅ 一致 |
| 旧条已移除 EXIT=1 | ✅ 一致 |
| `git diff -U0` 仅两 hunk | ✅ 一致 |
| 清单 8 条 | ✅ 一致 |
| 门控 `make check` EXIT=0 | ✅ 一致 |
| `make check-no-residue` EXIT=0 | ✅ 一致 |
| evidence.sh 正常 EXIT=0 / `--inject` EXIT=0 | ✅ 一致 |

**判决**：**Accepted** —— 验收命令块全部通过、约束无违反、脚本审计合格、独立注入证伪成功且还原回绿。
