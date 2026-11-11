# m13-qemu-004: quiet compare 遇 sNaN 置 `NV`（跟 IEEE）

**模块**：qemu
**项目里程碑**：M13
**依赖**：`m13-qemu-003`（已合入，signaling 口径）+ `m12-chipyard-014`（合入后再派，避免改差分参照，见 `ISS-395`）
**可并行分片**：否（单组件单写者）
**状态**：待开始

## 用户裁定（2026-11-12，原话）

> 「改为置 NV（跟 IEEE）」

落盘：`.tao/knowledge/discussing.md`「已裁定：quiet compare 遇 sNaN 也置 `NV`」。

## 背景

`m13-qemu-003` 已实现：signaling compare（`ftscmp`/`foscmp`）任何无序 ⇒ `NV`；quiet compare（`ftqcmp`/`foqcmp`）恒不置。

IEEE 754-2019 §5.11 要求 **quiet 谓词遇 sNaN 仍置 invalid**（hardfloat 同）。用户裁定跟 IEEE。

**两条裁定不冲突**：
- signaling：任何无序（含 qNaN 操作数）都置
- quiet：**仅 sNaN** 置（qNaN 输入不置）

## 目标

1. `ftqcmp`/`foqcmp`：任一操作数为 **sNaN** ⇒ 置 `NV`；qNaN 输入**不置**。
2. 结果值不变（无序 ⇒ q 版回 qNaN）。
3. 不得顺带改其它标志路径。

## 验收标准

1. 四组例 × ft/fo 逐条给输出（`rd6` = `rf0[4:0]`）：
   - `ftqcmp(sNaN, 1.0)` ⇒ **`0x1`**
   - `ftqcmp(qNaN, 1.0)` ⇒ **`0x0`**
   - `ftscmp(qNaN, 1.0)` ⇒ `0x1`（保持 003 的口径）
   - `ftqcmp(1.0, 2.0)` ⇒ `0x0`
2. `check-inst`（Vast 991/996、Tiny 44/44）rc=0；273 例 md5 不变。
3. **可达 FAIL 注入**：把 quiet 的 NV 条件去掉 ⇒ 新例红；`cp`+md5 还原回绿。
4. 一键证据脚本；完成区 ≤30 行、无运行期路径；**「修改文件」与 `git status` 对账**（`ISS-377`）。

## 说明

- 本任务是 `m12-chipyard-024` 的**前置**（QEMU 先对齐，chipyard 才有可信参照）。
- 与 `m12-chipyard-014` 串行（避免 `ISS-395` 的并发参照漂移）。
- `.work` 必须软链（`ISS-389`）；重建 QEMU 前申报耗时，`JOBS=8`。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树（`ISS-368`）；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账；计数从脚本现场输出直接抄（`ISS-388`/`ISS-391`）。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
8. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

（待填）
