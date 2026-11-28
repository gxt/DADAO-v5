# m18-linux-031: supv 返回路径的出口意图重写（ISS-m18-014，029 的对称缺口）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-029`（umon 侧已修，`ISS-m18-011` 闭合）
**可并行分片**：否（改 `components/linux`）
**预估**：1–2 h（同档单点修复中位 86 min；本任务只加与 029 同口径的四字重写 + 回归）
**档位**：中改（trap 出口意图）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`，本 worktree 自建）

## 背景

`m18-linux-029` 查明：`cfx_umon cg5` 是**单帧**共享出口意图，umon 返回路径只重写 `rc10`；C 半睡眠时另一任务的 `dadao_enter_user()`（supv→user）会把 `rc8/rc9/rc11` 覆盖成 supv/smon 掩码，恢复的任务 `escape cfx_umon` 便回到 **supv** 执行用户代码、并用陈旧向量进用户（`ISS-m18-011`）。修法是 `DADAO_UMON_USER_EXIT_INTENT` 在 `escape` 前重写全部四字。

`cfx_smon cg5` 的 supv 返回路径（`DADAO_TRAP_RESTORE_AND_ESCAPE` + `escape cfx_smon`）结构相同、同样只重写 `rc10` ⇒ 存在**同类覆盖**风险（`ISS-m18-014`）。本轮未观测到签名，不等于不存在。

## 目标

1. 按 029 的口径，在 supv 返回路径 `escape` 前重写 `rc8=supv`、`rc9=cfx_smon`、`rc10=任务帧 ip`、`rc11=现场 smon 掩码`（掩码取值须与进入时语义一致，不得放宽屏蔽）。
2. **不得**改变同步异常语义（`escape cfx_smon` 的返回点、`rc11` 整字写目标行）。
3. 若发现 smon 侧另有独立缺陷 ⇒ 记录并停下写「待裁定」，不顺手扩围。

## 验收（逐条贴真实 rc）

1. 静态：`trap.S` 的 supv 返回路径 `escape` 前四字重写齐全；补丁与源树逐行一致。
2. **可达 FAIL**：① 回退该重写 ⇒ 构造「C 半睡眠 + 另一任务 enter_user」场景下必须红（可用 029 的探针思路构造；若无签名则须给“为何不可达”的论证与频率上界）；② 只删 `rc8` 写 ⇒ 红。
3. 不回归：K2 170/170、K5 285/285、K6 82/82、`run_suite.py --suite ltp` 两轮逐例一致、`amb_window_probe` 14/14、`--soak 300 --soak-strict` 窗口 0；`m18-linux-029` 的忙等探针 0/≥20。
4. 门控：`check-patch-tree` linux 段 0、`check-config-pins`、`check-component-changelog`、`check-knowledge-refs`。
5. 闭合 `ISS-m18-014`（`resolved_by` 指本任务）；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`；每次跑次独立目录。
2. 只动：`components/linux/patches/**`、`components/linux/changelog.md`、`tests/unit/linux/**`、`tools/linux/**`、`.tao/knowledge/issues-m18.yaml`、本任务书。
3. 构建 `JOBS=32`；QEMU 本 worktree 自建（记 md5）；不覆盖共享安装根；低频签名单独计数（`ISS-m18-005/006`）。
4. 组件补丁经 `make_patch.py linux` 重导；还原 `cp`+md5；还原后重建。

## 待裁定

无。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
