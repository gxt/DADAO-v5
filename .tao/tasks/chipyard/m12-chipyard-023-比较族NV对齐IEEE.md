# m12-chipyard-023: signaling compare 对齐 IEEE（RTL + 模型 + 向量 + spec 补写）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-013`（已合入）+ `m13-qemu-003`（QEMU 先行对齐，本任务的差分参照）
**可并行分片**：否（单核实现，单写者）
**状态**：待开始

## 用户裁定（2026-11-11，原话）

> 「按 IEEE/hardfloat：任何无序都置」

落盘位置：`.tao/knowledge/discussing.md`「已裁定：signaling compare 遇 qNaN 置 `NV`」。

## 背景

`m12-chipyard-013` 实现比较族时按**任务书原口径**：`NV` 只由 sNaN 输入抬起，qNaN 操作数不置。任务书同时登记了「待裁定」——因为 IEEE 754 / hardfloat 要求 signaling compare 对**任何无序**都置 invalid。

用户已裁定按 IEEE/hardfloat。本任务把 RTL、模型、向量、spec 四处一起对齐。

## 目标

1. **RTL**：`ftscmp`/`foscmp` 的 `NV` 条件改为「任一操作数为 NaN（sNaN 或 qNaN）即置」；`ftqcmp`/`foqcmp` 保持「不置」。比较结果（无序 ⇒ q 版回 qNaN / s 版回 sNaN）不变。
2. **独立模型**：`tools/chipyard/fp_ref.py` 的比较实现同步（`NV` 判据），确保模型与 spec 一致而非与 RTL 一致。
3. **向量**：`tests/inst/fp/arith.yaml` 的 `cmp_snan` 组由 **model-only** 转为**三方对照**（chipyard == QEMU == model），并新增 qNaN 例：
   - `ftscmp(qNaN, x)` ⇒ `NV=1`
   - `foqcmp(qNaN, x)` ⇒ `NV=0`
   - 每种 `qNaN/sNaN × 单/双 NaN` 各 ≥1 例
4. **spec 补写**：`spec/SimRISC-07` 比较一节补一段——signaling compare 对任何无序（含 qNaN 操作数）置 `NV`；quiet compare 不置。措辞由本任务起草、**由 architect 校**（spec 正文改动按 `Process-03` 走版本与附录）。
5. **文档**：`components/chipyard/{README,changelog}.md` 同步。

## 非范围

- QEMU 侧（`m13-qemu-003` 先行完成）
- 其它 FP 标志语义（`NV/NX/OF/UF/DZ` 的算术族）
- sNaN payload 传播（沿用 011/012 已定口径）

## 验收标准

1. 四组例在 chipyard 上逐条给输出：`ftscmp(qNaN,x)`⇒NV=1、`ftscmp(sNaN,x)`⇒NV=1、`ftscmp(1.0,2.0)`⇒NV=0、`ftqcmp(qNaN,x)`⇒NV=0；`fo` 同理。
2. **三方一致**：chipyard == QEMU（`m13-qemu-003` 后的版本）== 模型，逐字节；`cmp_*` 组不再标 model-only。
3. **可达 FAIL 注入**：把 RTL 的 NV 条件改回「仅 sNaN」⇒ 新例必须红；`cp`+md5 还原回绿。
4. 273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变；`check-inst`/`check-tests-index` rc=0；L2 rc=0；`check-patch-tree` rc=0。
5. 一键证据脚本；完成区 ≤30 行、无运行期路径；**「修改文件」与 `git status` 对账**（`ISS-377`）。

## 说明

- `.work` 必须软链到主工作树（`ISS-389`）。
- 本任务与 `014`/`015` **串行**（同组件单写者）；建议在 `013` 合入后立即做，因为它是 `013` 的语义收尾。
- spec 正文改动需按 `docs/Process-03` 记版本与附录条目；本任务只起草，**architect 校后入账**。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树（`ISS-368`）；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账；**计数从脚本现场输出直接抄**（`ISS-388`/`ISS-391`）。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
8. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

（待填）
