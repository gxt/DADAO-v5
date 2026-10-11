> **升格指针**（INFRA-058t，用户 2026-10-11 裁定「被引用材料不得只放 `.work/`」）：本文档由 `.work/log/integ/` 下同名文件升格至 `.tao/knowledge/`（原 `.work/` 副本已移出，该目录 gitignored、不再保留）。
# 门控分层设计（**用户 2026-10-09 裁定：推到 M7**）

> 用途：M7 规划时落地。**本轮不改 `Makefile`**。事实来源 = `Makefile` 现文 + `TESTCASES-037t` 现场数据。

## 一、用户提出的划分（原话要点）

- **最低层**：仓库完整性 + 各部分可用性；**几秒 ~ 几十秒**。
- **中层**：各模块功能；**不必过于全面，但各种类别都有**；**几十秒 ~ 几百秒**。
- **顶层**：较完整的检查；**几百秒 ~ 几千秒**。
- **每模块完整测试**：需要时单独调用。

**主会话评估**：划分**合适**，且与现状天然吻合（现 `make check` 已是"静态完整性 + 部分功能"混合体，只是没分层）。

## 二、现状事实（`Makefile`，2026-10-09 取得）

`check:`（`Makefile:348`）= 23 项，其中：

- **静态（不看执行行为）**：`manifest-check`、`check-patch-tree`、`check-index-blobs`、`check-spec-drift`、`check-spec-readonly`、`validate-encoding`、`validate-vectors`、`check-asm-list`/`-drift`/`-prose`、`check-spec-codeblocks`、`check-legality-drift`/`-invariants`、`check-scope`、`check-rule-refs`、`check-fp-contract`、`check-instrinfo`、`check-cfx-aliases`、`check-dirs`、`check-no-residue` + `check_issues.py` + `compileall tools`
- **功能**：`check-qemu-semantics`（**149 用例，跑 QEMU**）、`check-lit`（76 用例，≈1 s）
- **不在 `check` 里**：`test-codegen`(15)/`test-elf`(5)/`test-semihost`(10)/`check-lit-full`(227，**已 opt-in 雏形**)

**⚠️ 部分实测**：`TESTCASES-038t` 现场记录 **`make check` ≈ 32 s**（含 `check-qemu-semantics` 149 + `check-lit` 76 + 23 项静态）⇒ **现规模已在用户 L1 目标带（几秒~几十秒）边缘**；"庞大"是**增长趋势**问题（`check-lit-full` 227 / Embench / `test-m6` 待接入）。**M7 落地第 0 步仍须逐门控计时**（定位最重的那个，判断是否值得拆）。

## 三、建议映射（用现有真实目标名；M7 定稿时再调）

| 层 | 目标 | 内容 | 目标耗时 |
|---|---|---|---|
| L1 完整性/可用性 | **`make check`**（默认） | 上列**全部静态检查** + **组件可用性冒烟**（`llc`/`clang --print-targets`/`qemu` 可执行且含 `dadao`；**不跑被测语义**） | 秒 ~ 几十秒 |
| L2 模块功能代表集 | **`make check-modules`**（新） | `check-lit`(76) + `check-interface` + **`check-qemu-smoke`**（149 条**按语义类别各抽 1–2 条**）+ `test-codegen`/`test-elf`/`test-semihost`（现各 15/5/10） | 几十 ~ 几百秒 |
| L3 较完整 | **`make check-full`**（新） | `check-qemu-semantics` **全量** + `check-lit-full`(227) + Embench(`test-m6`) + 全量向量回放 | 几百 ~ 几千秒 |
| 按需（模块完整） | 各 `test-*`/`check-*` 单独调 | 模块全量、profiling | 不定 |

## 四、四条必须同时定的规则（否则分层会退化）

1. **默认 `make check` 只留 L1**（把 `check-qemu-semantics` 移出、新增 `check-qemu-smoke`）——这是让默认门控变快的**唯一**实质动作。
2. **每层都要"能失败 + 有结构断言"**（引 `lessons §8.34`（正则须证"确有命中"）、`§8.35`（须断言"结构"：成对/条数））——层越多，"空转绿灯"越多。
3. **L2 的"各类别都有"必须由类别清单机械派生**（按 `contracts/` 格式类/指令 `scope`、QEMU 语义类别），**不许手工挑**；**层间不重复**（同一检查只在一层跑）。
4. **触发点写进 `AGENTS.md`（≤2 行 + 门控名）**：任务收尾跑 **L2**、里程碑/`/complete` 跑 **L3**；否则"按需层"**必腐烂**。
   **风险**：分层后"L1 绿、L2/L3 红"会成常态 ⇒ 第 4 条是**前提**，非可选项。

## 五、待办（M7）

- [ ] 第 0 步：**逐门控计时**（`make -n` 不适用；逐目标 `time`），据实测确定 L1/L2/L3 边界与是否值得拆。
- [ ] 新增 `check-qemu-smoke`（类别代表子集，**机械派生**）。
- [ ] 新增 `check-modules` / `check-full`；`check` 收缩为 L1。
- [ ] `AGENTS.md` 写触发点（≤2 行 + 门控名）。
- [ ] 关联遗留（`TESTCASES-037t` reviewer 标注）：`MC/DADAO-gen`（227 条全量档）**仅 opt-in 校验** ⇒ `contracts/` 漂移在 `make check` 中**不报警**；M7 分层时决定它进 L2 还是 L3。
