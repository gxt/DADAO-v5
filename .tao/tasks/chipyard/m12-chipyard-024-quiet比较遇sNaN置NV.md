# m12-chipyard-024: quiet compare 遇 sNaN 置 `NV`（RTL + 模型 + 向量 + spec）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m13-qemu-004`（QEMU 先行对齐）+ `m12-chipyard-014`（已合入）
**可并行分片**：否（单核实现，单写者）
**状态**：待开始

## 用户裁定（2026-11-12，原话）

> 「改为置 NV（跟 IEEE）」

落盘：`.tao/knowledge/discussing.md`「已裁定：quiet compare 遇 sNaN 也置 `NV`」。

## 背景

现行实现（`013` 定、`m13-qemu-003` 同步）：signaling compare 任何无序 ⇒ `NV`；quiet compare **恒不置**。

IEEE 754-2019 §5.11：quiet 谓词遇 **sNaN** 仍置 invalid（hardfloat 同）。用户裁定跟 IEEE。

**两条裁定并存**：
- signaling（`ftscmp`/`foscmp`）：任何无序（含 qNaN）都置
- quiet（`ftqcmp`/`foqcmp`）：**仅 sNaN** 置；qNaN 不置

## 目标

1. **RTL**：`WumingFP.scala` 比较的 `NV` 条件改为
   `NV = Mux(io.signaling, unordered, rawA.isNaN_s || rawB.isNaN_s)`（quiet 仅在 sNaN 输入时置）。
2. **模型** `tools/chipyard/fp_ref.py` 同步（与 spec 一致，不是与 RTL 一致）。
3. **向量**：`cmp_nan` 组补「quiet + sNaN ⇒ NV=1」「quiet + qNaN ⇒ NV=0」四组，并保留 003 的 signaling 例；`divrem`/`arith` 相关期望同步。
4. **spec 补写**：`spec/SimRISC-07 §4` 比较一节，按 `ISS-396` 的三点修正后入册：
   - 条号用 `§5.6.1` / `§5.11`（不用 `§5.7.1`）
   - 明确 signaling 与 quiet 两条规则（signaling 任何无序、quiet 仅 sNaN）
   - 写明「本核 signaling 对 qNaN 也置 invalid 是 IEEE 一致行为；quiet 对 sNaN 置 invalid 为 IEEE 754-2019 §5.11 行为」
   - 版本按 `Process-03` 记 `Machine-v5`/`SimRISC-07` 附录条目

## 验收标准

1. 四组例 × ft/fo 逐条给输出：`ftqcmp(sNaN,1.0)⇒NV=1`、`ftqcmp(qNaN,1.0)⇒NV=0`、`ftscmp(qNaN,1.0)⇒NV=1`、`ftscmp(1.0,2.0)⇒NV=0`。
2. 三方一致：chipyard == QEMU（`m13-qemu-004` 后）== 模型，逐字节；`cmp_nan` 不再有 model-only 子组（sNaN payload 差异除外，需单列说明）。
3. **可达 FAIL 注入**：把 quiet 的 NV 条件去掉 ⇒ 新例红 ⇒ `cp`+md5 还原回绿。
4. 273 例 md5 不变；`check-inst`/L2/`check-patch-tree` rc=0。
5. spec 门控：`check-spec-*` 全绿，版本与附录按 `Process-03`。
6. 一键证据脚本；完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账。

## 说明

- `.work` 必须软链（`ISS-389`）；`JOBS=8`。
- 与 `015` 串行（同组件单写者）。
- spec 正文改动需 architect 校后入账（本任务起草 + 跑门控，不自行定稿）。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树（`ISS-368`）；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账；计数从脚本现场输出直接抄。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
8. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

（待填）
