# SPEC-137t: 未定义弱符号边界补入 `ADR-0019 D9` ⑥ + `contract-elf §3.3`

**模块**：spec
**项目里程碑**：M7
**依赖**：`SPEC-135t`（`已验证`，`D9` ①–⑤ 落地来源）；`INTEG-034m`（M7 整体收敛复核）
**状态**：待验收

> 立项来源：`ISS-201`（源 `SPEC-135t` 完成区「新发现/坑①」+「第 1 轮 reviewer 验收」非阻断遗留处置；`INTEG-034m` 复核点名）。**执行方式**：architect 自办（小文档增量）。

## 用户裁定（2026-10-13，**原话**）

- **议题**：`ADR-0019 D9` 第 ⑥ 条 + `contract-elf §3.3` bullet 文本确认。
- **用户原话**：「**确认，照此写入（推荐）**」。
- **取得渠道**：经主会话问答取得（2026-10-13）。
- 该确认**视为对下述「确认的确切文本」的逐条确认** ✓。

## 确认的确切文本（**逐字**，不得改写）

**① `ADR-0019 D9` 追加第 ⑥ 条**：

> **边界（防御分支）**：`R_DADAO_REL26` 落点指令**既非 `call-iiii`（`0x74`）也非 `jump-iiii`（`0x70`）**时 ⇒ **link-time error（显式报错）**——**不放行、不自循环**。**理由**：该落点组合不在本决策语义覆盖内（"自循环"仅对分支/call 有意义）；显式失败优于静默产出错误控制流；本批 **0 例**暴露。**被否**：(a) 一律按自循环处理（对非分支落点语义无意义）；(b) 静默放行（不可接受）。

**② `contract-elf §3.3` 追加 bullet**：

> **边界**：`REL26` 落点**非 `call-iiii`/`jump-iiii`** ⇒ **link-time error**（不放行、不自循环）。[ADR-0019 §D9]

## 接口规范
- 输入：`ADR-0019`（`D9` 现有 ①–⑤）、`contract-elf.md §3.3`（现有 4 bullet）、`ISS-201`。
- 输出：`D9` 内追加第 ⑥ 条（体例与 ①–⑤ 一致）+ `✅` 清单 `D9` 行同步（**只追加**）；文末"逐条确认"段追加一行；`contract-elf §3.3` 追加该 bullet（正文、无理由、尾缀 `[ADR-0019 §D9]` 指向）；`ISS-201` ⇒ `closed`。
- 约束：**不改** `D9` ①–⑤；**不改** `§3.3` 既有 bullet；**不改写**历史记录（只追加）；双向互指保持。

## 验收标准
1. `ADR-0019 D9` 含第 ⑥ 条，文本与「确认的确切文本①」**逐字**一致；体例与 ①–⑤ 一致。
2. `ADR-0019` `✅` 清单 `D9` 行同步（**只追加**，不改既有文字）；文末"逐条确认"段新增 `2026-10-13` 行（含用户原话「确认，照此写入（推荐）」+ 渠道）。
3. `contract-elf §3.3` 含「确认的确切文本②」bullet，尾缀 `[ADR-0019 §D9]`；正文仅规范语、无理由/被否。
4. 双向互指：`D9` → `contract-elf.md §3.3`；`§3.3` → `[ADR-0019 §D9]`（`grep -c` 均 ≥1）。
5. `ISS-201` = `closed` + `resolved_by: SPEC-137t` + notes 追加（用户原话 + 落点）。
6. 门控：`make check` / `check-spec-refs` / `check-knowledge-refs` / `check-no-residue` / `check_issues.py` 各 rc=0。

## 完成区

**测试结果**：
- 门控（均现场直捕退出码）：`make check` rc=0、`make check-spec-refs` rc=0（0 violations）、`make check-knowledge-refs` rc=0、`make check-no-residue` rc=0、`python3 tools/infra/check_issues.py` rc=0。
- `check_issues` 计数：由 **25 open / 0 closed** ⇒ **24 open / 1 closed**（0 blocking M1-gate）。
**修改文件**（仅任务范围）：
- `.tao/adr/adr-0019-dadao-relocation-types.md`：`D9` 段内追加第 ⑥ 条（防御分支）；`## 状态说明` `✅` 清单 `D9` 行追加；文末追加 `2026-10-13` 确认行。
- `.tao/knowledge/contract-elf.md`：`§3.3` 追加「边界」bullet（尾缀 `[ADR-0019 §D9]`）。
- `.tao/knowledge/issues.yaml`：`ISS-201` 置 `closed` + `resolved_by: SPEC-137t` + notes 追加关闭说明。
- `.tao/knowledge/milestones.md`：`任务流水` 追加 `SPEC-137t` 行（`待验收`）。
- 本任务书（`.tao/tasks/spec/SPEC-137t-…md`）。
**验收结果**（逐条与真实输出对齐）：
1. 见「审阅记录 §实施」grep 证据：`D9` 含第 ⑥ 条且逐字一致 ✓。
2. `✅` 清单 `D9` 行追加 + 文末 `2026-10-13` 行（含原话/渠道）✓。
3. `§3.3` 新 bullet 尾缀 `[ADR-0019 §D9]`、无理由词 ✓。
4. 双向 `grep -c` 均 ≥1 ✓。
5. `ISS-201` closed + `resolved_by: SPEC-137t` + notes 追加 ✓。
6. 门控各 rc=0 ✓。
**新发现/坑**：无（纯文档增量；未触实现）。
**遗留问题**：无（本任务范围内）。

## 审阅记录

#### architect 规划 / 实施（2026-10-13）

- **编号依据**：spec 模块现场最大编号 = `SPEC-136m`（`find .tao -name 'SPEC-*'`；`grep -rn 'SPEC-137' .tao` rc=1）⇒ 下一个空位 = **`SPEC-137t`** ✓。
- **用户原话落纸**：本任务书「用户裁定（2026-10-13，原话）」段 + `ADR-0019` 文末确认行 + `issues.yaml` `ISS-201` notes ✓。
- **实施**：`D9` 于第 ⑤ 点（`REL12` 暂不纳入）后、"规范正文"指针前，追加第 ⑥ 条（`**边界（防御分支）**：…`，体例同 ①–⑤）；`✅` 清单 `D9` 行**追加**（不改既有）+ 文末追加 `2026-10-13` 行；`contract-elf §3.3` 末尾追加「边界」bullet；`ISS-201` 关闭；`milestones.md` 追加行。**未改** `D9` ①–⑤ 与 `§3.3` 既有 bullet ✗。
- **状态**：architect 自办 ⇒ 置 `待验收`（待 reviewer 独立验收后由主会话/后续置 `已验证`）。
