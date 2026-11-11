# m13-qemu-003: 比较族标志对齐 IEEE（signaling compare 无序即置 `NV`）

**模块**：qemu
**项目里程碑**：M13
**依赖**：无（QEMU 组件单写者空闲）
**可并行分片**：否（单组件单写者）
**状态**：待开始

## 用户裁定（2026-11-11，原话）

> 「按 IEEE/hardfloat：任何无序都置」

落盘位置：`.tao/knowledge/discussing.md`「已裁定：signaling compare 遇 qNaN 置 `NV`」。

## 背景

`m12-chipyard-013` 报「待裁定」：`ftscmp`/`foscmp`（signaling compare）遇 **qNaN** 操作数是否置 `NV`。

- `spec/SimRISC-07` / `contract-fp` **未写这一条**
- 原口径（任务书 + QEMU）：只有 sNaN 输入置 `NV`，qNaN 不置
- IEEE 754 / hardfloat：signaling compare 对**任何无序**（含 qNaN 操作数）都置 invalid

用户**已裁定按 IEEE/hardfloat**。

## 目标（只做 QEMU 侧）

1. **`ftscmp`/`foscmp`**：操作数中有**任一 NaN**（sNaN 或 qNaN）⇒ 置 `NV`。
2. **`ftqcmp`/`foqcmp`**（quiet compare）：任何 NaN **不置** `NV`（保持不变）。
3. 比较结果本身不变：无序 ⇒ 按 spec 返回 NaN（quiet 版回 qNaN、signaling 版回 sNaN），有序时按 `</=/>` 返回。
4. **不得**顺手改其它 FP 标志路径（`NV`/`NX`/`OF`/`UF`/`DZ` 的算术族语义不在本任务范围）。

## 非范围

- chipyard RTL / 模型 / 向量（`m12-chipyard-018`）
- `spec/SimRISC-07` 正文补写（归 `m12-chipyard-018`，避免两处漂移）
- 其它 FP 指令的标志语义

## 验收标准

1. 构造四组例并逐条给输出：
   - `ftscmp(qNaN, 1.0)` ⇒ `NV=1`，结果 NaN
   - `ftscmp(sNaN, 1.0)` ⇒ `NV=1`，结果 NaN
   - `ftscmp(1.0, 2.0)` ⇒ `NV=0`，结果 `−1`
   - `ftqcmp(qNaN, 1.0)` ⇒ `NV=0`，结果 NaN
2. `fo` 格式同样四组。
3. 既有回归不破：`check-inst`（Tiny 44/44）、273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变、`check-arch-smoke` rc=0。
4. **可达 FAIL 注入**：把 `NV` 条件改回「仅 sNaN」⇒ 新例必须红；`cp`+md5 还原回绿。
5. 一键证据脚本；完成区 ≤30 行、无运行期路径；**「修改文件」与 `git status` 对账**（`ISS-377`）。

## 说明

- 本任务是 `m12-chipyard-018` 的**前置**：QEMU 先对齐，chipyard 才有可信的差分参照。
- QEMU 组件单写者：本任务期间不要有其它任务重建 QEMU。
- 若发现 QEMU 当前**完全不为比较族置任何标志**（`013` 报告如此），需先补上 sNaN 路径再补 qNaN 路径，两步都要有证据。
- `.work` 必须软链到主工作树（`ISS-389`）。

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
