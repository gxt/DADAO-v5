# ADR-0055: 测试机命名 = `Kaiwu`（开物）

**状态**：Candidate
**日期**：2026-11-16
**关联**：`ADR-0053`（cfx 独立为 `dadao-gewu`，机器名不占用 `Gewu`）、`ADR-0004`（测试机对象与双 profile：`tiny`/`vast`）、`ADR-0020`（semihosting）、`ADR-0047`/`ADR-0048`（gem5/qemu 基线）；`spec/Machine-v5-测试机运行环境.md`；`.tao/knowledge/discussing.md` §「待定：机器/版本命名」

## Context（背景）

v5 的测试机（含 `tiny`/`vast` 两机型）长期以占位名 `Machine-v5` 出现（临时名 `DADAO-v5` 曾短暂使用）。用户口径（2026-11-14）：**机器名既不应是 `Machine-v5` 也不应是 `DADAO-v5`**；`tiny`/`vast` 作机型名保留；`v5` 不进机器名。

现有名字已形成三层：

- 项目/ISA：`DADAO`（大道）——三元组 `dadao-unknown-elf`、pass 名、上游册 `DADAO-11..23`；
- 核芯：`Wuming`（无名）——chipyard generator `dadao-wuming`；
- cfx 寄存器堆：`Gewu`（格物）——`ADR-0053`、generator `dadao-gewu`。

缺的是**整机**一层的名字。用户 2026-11-16 裁定：整机名 = **`Kaiwu`（开物）**，取《天工开物》与《易》「开物成务」；`Gewu` 仍归 cfx（不互换）。

改名规模（现场统计，2026-11-16）：`Machine-v5` **557 文件 / 1,542 处**（tests 309、`.tao` 120、components 60、tools 54、docs 7、spec 2、contracts 2、manifest 1、根 README 1、Makefile 1）；QEMU 机器串 `dadao-tiny`/`dadao-vast` **152 文件 / 437 处**。

## Decision（决策）

- **D1 名字**：整机名 = **`Kaiwu`**（拼音 `kaiwu`，标识一律小写 `kaiwu`）；机型名保持 `tiny`/`vast`；版本号不进名字（版本走 manifest 与 git）。
- **D2 改名范围**：`Machine-v5` → `Kaiwu`（spec 册名与正文、文档、任务书、注释、工具默认值、manifest 路径）；`DADAO`（ISA/项目）、`Wuming`（核）、`Gewu`（cfx）**均不改**；三元组 `dadao-unknown-elf` 与 ELF 机器常量不动。
- **D3 QEMU 机器串**：`dadao-tiny`/`dadao-vast` → **`kaiwu-tiny`/`kaiwu-vast`**，**不保留旧名别名**（直接切换；旧名一律失效）。
- **D4 迁移方式**：单独立**一件机械改名任务**（不改语义、不散改），任务内含：① 全仓改名 + 三处门控（`check-interface`/`check-spec-refs`/`check-knowledge-refs` 等）回绿；② `spec/` 册改名 ⇒ `manifests/spec-readonly.lock.toml` 的 path 与 sha256 同笔重算；③ 完成后更新 `MEMORY.md` 的命名段；④ `docs/DDLN/**` 一并改（`.tao/archive/**` 不动）。

## Rationale（理由）

- **语义层级**：`Kaiwu`（造物之术，《天工开物》）指向**被造出来运转的整机**；`Gewu`（穷究物理）指向**被观测/管理的状态面**（cfx 寄存器堆）；`Wuming` 指向核芯。三层各就各位，不互相顶替。
- **语域一致**：`DADAO`/`Wuming`/`Gewu`/`Kaiwu` 全是古典语域的概念，拼音化后作标识一致；先前被否决的 `gegewu`/`gargamel`（角色名，含 IP 关联）与 `caotai`（口语自贬、与语域不符）都不满足这一条。
- **无占用**：`kaiwu` 在仓内 **0 命中**，不与既有标识冲突。

## Consequences（影响）

- 改名涉及 ≈ **557 文件（含 QEMU 串 152 文件）**，但全部是**机械替换**；语义、契约值、编码一律不变；
- `machine-profiles.yaml` 的 profile 名（`tiny`/`vast`）不变 ⇒ 只改前缀；
- QEMU 机器名变更影响 `tests/`/`tools/` 的 `-M` 调用共 ~437 处，须与 `D3` 的别名一起落，避免中途断链；
- `spec/` 册改名必须与锁文件同笔重算（`docs/Process-06 §5`），否则 `check-spec-readonly` 会红；
- `.tao/archive/**` 的历史文本上**不改**（归档是事实记录，用户 2026-11-16 裁定）；`docs/DDLN/**` 的正文**要改**（用户同日裁定：「DDLN中的改」），因为 DDLN 是长期给别人看的讲义，不是历史快照。

## 状态说明

2026-11-16 由主会话起草。用户已裁定：名字 = `Kaiwu`（原话「好的，我决定就是kaiwu了」）；**删除原 D4（`Gewu` 不互换）**（原话「D4不需要，这是讨论过程，与ADR无关」）；**D3 不保留旧名别名**（原话「旧名不需要保留一个版本做别名」）；**`.tao/archive/` 不动、`docs/DDLN/` 要改**（原话「.tao/archive中的不需要动；DDLN中的改」）。**D1/D2/D4 尚待逐条确认**，确认后置 `Accepted` 并按 D4 立实施任务（不得先动文件）。
