# SPEC-111t: 归档 SimRISC-0.5.3 历史基线至 `.tao/archive/`

**模块**：spec
**项目里程碑**：M3
**依赖**：无
**状态**：待开始

> **来源（用户裁定 2026-10-06）**：`spec/SimRISC-0.5.3/` 与现行 `spec/SimRISC-0.*` 混放，用户裁定将其移入 `.tao/archive/`（与 M1/M2 归档体例一致）。**本任务书由另一会话（非当前并发推进 M3 的会话）建立，只建不执行；实际移动须在串行空档执行**（见「并发约束」）。

---

## 背景

`spec/SimRISC-0.5.3/`（5 个文件：`SimRISC-00-指令系统设计.md`/`01-数据类指令`/`02-地址类指令`/`03-浮点类指令`/`04-系统类指令`，0.5.3 基线、只读、仅供对照）由 `SPEC-013t` 建立。现状它在 `spec/` 下，被 3 个门控脚本**按路径排除**。

## 目标

把 `spec/SimRISC-0.5.3/` 移至 **`.tao/archive/SimRISC-0.5.3/`**，并**同步全部引用**——消除指向不存在路径的「死排除/死链」。

## 改动清单（执行时逐项核对）

1. **移动**：`git mv spec/SimRISC-0.5.3 .tao/archive/SimRISC-0.5.3`（保留历史；`.tao/archive/` 下与 `M1/`、`M2/` 平级）。
2. **门控/工具（3 处硬编码该路径为"排除项"，移动后成死代码）**：
   - `tools/spec/check_asm_prose.py`：docstring L34 + L66 `ROOT / "spec" / "SimRISC-0.5.3"`；
   - `tools/spec/check_spec_codeblocks.py`：docstring L30/79 + L60 `HISTORICAL_DIR`；
   - `tools/spec/check_scope.py`：`HISTORY_PREFIXES`（L43/51）。
   - **处置**：删除该路径排除（因历史目录已不在 `spec/` 扫描面内），或在确有需要时改指 `.tao/archive/SimRISC-0.5.3/`。二者择一，须在完成区说明理由。
3. **`spec/README.md`**：删除/更新 `SimRISC-0.5.3/` 索引行（现 L34「历史基线（只读）」）；在 `.tao/archive/`（或 `spec/README.md`）保留一句指针说明归档去向。
4. **`Makefile`**：L302 注释「`spec/**/*.md` (excl. historical SimRISC-0.5.3)」更新。
5. **台账叙述（不改写历史行）**：`.tao/knowledge/MEMORY.md` L67/L74、`.tao/knowledge/lessons.md` L133 中的 `spec/SimRISC-0.5.3/` 路径引用——按需订正为归档路径，或保留为历史引用（须在完成区说明）。

## 明确不改

- **归档任务书**（`.tao/archive/M2/spec/SPEC-013t-存档0.5.3文档.md` 等）：历史快照，引用将悬空，**可接受**（同 `adr-0015` 引用已移走的 `docs/02-大道至简.md` 之先例）。
- `adr-0015`（与本次无关）。
- `spec/SimRISC-0*`（现行 12 章）、`contracts/**`、`tests/vectors/**`、`components/**`。
- `tools/spec/check_qfc_coverage.py` / `validate_encoding.py` 中的「SimRISC 0.5.3」——**仅是来源概念表述，非路径**，不改。

## 验收标准（可执行、可失败）

1. **移动结果**：`.tao/archive/SimRISC-0.5.3/` 恰含 5 个文件；`spec/SimRISC-0.5.3/` **不存在**。
2. **引用清零**：全仓 `grep -rn 'spec/SimRISC-0\.5\.3'`（**排除** `.tao/archive/**` 历史任务书）**0 命中**。（给真实 grep 输出与退出码。）
3. **门控**：3 个脚本不再含指向不存在路径的排除；`make check` **EXIT=0**（重点 `check-asm-prose`、`check-spec-codeblocks`、`check-scope` 仍 PASS）。
4. **反例门控（证明门控仍有效）**：临时把历史目录**放回 `spec/`**（或构造对应用例）⇒ 说明门控的排除若已删则应被扫描到（如触发 `check-asm-prose`/`check-spec-codeblocks` 的扫描）→ 复原。给出「注入→FAIL/命中→还原→回绿」的真实输出。
5. **不变量**：现行 `spec/SimRISC-0*`、`contracts/**`、`tests/vectors/**`、`components/**` **零改动**；`check-patch-tree` 计数不变。
6. 完成区与真实输出**逐条对齐**；证据脚本按 `AGENTS.md`「子代理硬约束」第 8 条产出。

## ⚠️ 并发约束（必须遵守）

本任务触碰 **`Makefile`**、**`spec/README.md`**、**`tools/spec/*.py`**、**`.tao/knowledge/MEMORY.md`**——**均为多会话共享文件**。⇒ **必须与其它 session 串行**：
- 执行**前**确认无并发构建/`make check`（另一会话高频推进 M3，每任务跑 `make build-mc` + `make check`）；
- **不得**与其它任务同时改上述共享文件；
- 建议在另一会话**任务间歇/收口空档**执行。

## 完成区

（待填）

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
