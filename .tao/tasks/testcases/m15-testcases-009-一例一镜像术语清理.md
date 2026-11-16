# m15-testcases-009: 「一例一镜像」术语清理 + `__PRINT` 零长硬化

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m15-testcases-007`（**已交付**：故障例链式合并，镜像 904→272）**必须先合入**（同改 `tests/inst/**` 与相关文档）
**可并行分片**：否（跨册文档统一改）
**预估**：1–1.5 h
**档位**：小改（纯文档/注释 + 一处宏硬化；复核 diff + 1 路注入 + 受影响门控 ≤15 min）
**状态**：待开始

## 背景（`m15-testcases-007` 交付时登记的残留）

`m15-testcases-007` 把故障例链式合并后（**904 → 272 镜像**），仓内仍有多处描述"**一例一镜像** / 两种镜像形态"，与现行为矛盾：

- **248 处 `.S` 注释**（分布在 **209 个文件**）仍写「一例一镜像」；
- `tests/inst/MIGRATION.md §2`、`tests/inst/inventory.md`、`docs/Process-07-门控分层规范.md` 仍按旧模型描述；
- 另有硬化项：`__PRINT` 是 do-while，**`len=0` 会死循环**（0 链例文件会撞到），`007` 已在收尾处用 `.if __NCHECK > 0` 兜住 —— 应把预判**收进宏本身**。

## 目标

1. **术语统一**：全部改为「**镜像 = 每 `.S` 一个**（链例 + 该文件的全部故障例顺序跑）」；`CASE_N=<pt>` 的**单例调试模式**仍保留，描述为「调试用单例模式」；
2. **`__PRINT` 硬化**：`len == 0` 时**直接返回**（不进入 do-while），并保留 `007` 收尾处的 `.if` 兜底（双保险）；加注释说明；
3. **文档三处同步**：`tests/inst/MIGRATION.md §2`、`tests/inst/inventory.md`、`docs/Process-07`（若有镜像计数，改成指向 `check-inst-asm` 现场值）；
4. 不改变任何用例、检查点、镜像数、退出码。

## 验收（真实 rc + 输出）

1. `grep -rc "一例一镜像" tests/inst docs` = **0**（历史归档 `.tao/archive/**` 不计；任务书本身的引用须显式排除并说明）；
2. `check-inst-asm` **272/272**（镜像数不变）、`check-case-ledger`、`check-tests-index`(472)、`check-inst-macro-scope`（含 S9）、`check-dirs`、`check-no-residue`；
3. **`__PRINT` 硬化可达 FAIL**：造一个 `len=0` 的宏调用（临时 `.S`，注入后必须**不死循环**且行为与 `.if` 兜底一致），`cp`+md5 还原；
4. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

只动 `tests/inst/**`（注释与 `__PRINT` 宏）、`tests/inst/MIGRATION.md`、`tests/inst/inventory.md`、`docs/Process-07-门控分层规范.md`、本任务书；**不动** `spec/`、`contracts/`、`components/**`、`tools/**`、测试期望；不提交 git；`cp`+md5 还原（禁 `git checkout/restore`）。

## 审阅记录

（待填）
