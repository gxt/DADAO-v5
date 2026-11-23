# m17-testcases-005: 测试向量去除内存实现术语（`beat`/`拍`/字节通道）一次性统一

**模块**：testcases
**项目里程碑**：M17
**依赖**：`m17-testcases-004`（同改 `tests/inst/**` 共享文件，必须串行；004 合并后再开工）
**可并行分片**：否（`tests/inst/**` 全族一次性替换，任何并行都会互相踩）
**预估**：2–3 h
**档位**：中改
**状态**：待开始

## 背景（用户 2026-11-23 裁定）

用户原话：**「不要把 beat 和拍这类的实现用的术语带入到测试向量中，统一调整一次」**。

现场盘点（2026-11-23，`tests/inst/**`）：

| 术语 | 涉及 | 规模 |
| --- | --- | --- |
| `beat`（英文注释 + 宏参数名） | `.S` 注释、`macros/inst_test.inc`、`01-load-store.inc`、`12-misc.inc`、`MIGRATION.md`、`schema.md` 表格 | 41 个 `.S` + 4 个非 `.S`；注释行型 30+ 种，另有宏参数 `\beat` / `\beats` |
| `拍`（= beat 的中文说法） | `.S` 注释（`8 B 拍`、`多拍`、`末拍`、`尾拍`、`拍内`、`跨多拍`、`一拍`…） | 50 个文件、约 130 处 |
| `字节通道` | `st.*` 语义行（004 已改）与 `schema.md`/`MIGRATION.md` 表格 | 10 处 |
| `总线` / `流水` | 零散注释 | 2 / 1 处 |

这些是**内存流水/颗粒/总线**的实现术语，不属于 ISA 语义；测试向量的注释应只用 ISA 侧说法（字节、元素、寄存器、地址、对齐）与测试框架自身概念（用例、检查点、镜像、槽）。

## 目标

1. **注释与文档**：`tests/inst/**` 下 `.S` / `.inc` / `.md` 中
   - `beat`、`拍` → **「数据单元」**；首次出现或易混处标宽度「**8 字节数据单元**」；
   - 按语境的短语映射（其余可类推，须保持原意）：
     `多拍` → `多个元素`（块指令语境）/ `多个数据单元`；`末拍`/`尾拍` → `末个数据单元` / `尾部数据单元`；`一拍` → `一个数据单元`；`拍内` → `数据单元内`；`跨多拍` → `跨多个数据单元`；`全 0 拍`/`全 1 源/拍` → `全 0 数据单元`/`全 1 源或数据单元`；`整 beat 比` → `整 8 字节比`；`现有 beat` → `现有 8 字节数据单元`；
   - `字节通道` → 窄写句用显式字节数（004 已做）；其余改为「字节」；`总线`/`流水` 改为 ISA 侧说法。
2. **代码标识符**：宏参数 `\beat` → `\unit`、`\beats` → `\units`（`inst_test.inc` 定义 + 全部调用点实参），使 `tests/case-ledger.tsv` 的源行文本里也不再出现 `beat`。
3. 一条命令可验证的终态：`grep -rniE "beat|拍|字节通道" tests/inst` **零命中**（含 `.S`/`.inc`/`.md`）。

## 验收（逐条贴真实 rc）

1. **语义零漂移**：全部 272 个镜像的 `.text` **md5 与改前逐个相同**（注释/参数名不改代码）。做法：改前从 `git show HEAD:<file>` 取基线副本，用同一 `clang`/`ld.lld` 与同一 `.lds` 汇编、链接，逐镜像比对；给出「比对 N 个、不一致 0 个」与脚本路径。
2. **术语清零**：`grep -rniE "beat|拍|字节通道" tests/inst` rc=1（无输出）；`grep -rn "beat" tests/` 全仓零命中（`tests/data/**`、`tools/testcases/**` 也查，若命中一并处理并说明）。
3. **数据与台账**：`make inst-signature-data` 后 `tests/data/inst-signature/{expected.tsv,inputs.sha256}` **零变化**（纯注释/标识符，不改槽内容）；`make check-case-ledger --write` 重生成 `tests/case-ledger.tsv`，`git diff` 只含源行文本变化（用例数、点号、镜像数不变）。
4. **门控**：`make check-inst-asm`（镜像数同改前）、`make check-inst-sig`、`make check-case-ledger`、`make check-tests-index`、`make check-inst-macro-scope`、`make validate-vectors`、`make check-asm-prose`、`make check-knowledge-refs` 真实 rc；若某门控基线即红，按「与基线逐行相同」记 KNOWN-RED。
5. **抽样人工复核**：随机抽 10 个文件（含 `stm.*`、`ldm.*`、`12-misc`、两个 `.inc`、`MIGRATION.md`），逐条确认替换后句子仍与 spec 语义一致（贴 diff 片段）。
6. 完成区列出：改动文件数、替换处数（按术语分列）、`.text` 比对计数、以及**未改动**的说明（若有个别处故意保留，必须逐条给理由）。

## 约束

独立 `git worktree`（分支 = `m17-testcases-005`）；**不提交 git**；只改 `tests/inst/**`、`tests/case-ledger.tsv`（重生成）与本任务书；**不动** `spec/`/`.tao/contracts/`/`contracts/`/门控脚本；不改任何用例的点号、期望值、镜像数；术语「寄存器组」；完成区不写具体 `.work/**` 路径。
