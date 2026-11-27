# m18-linux-030: hart 全局 `trap_busy` 跨睡眠误报递归（ISS-m18-012）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-028`（异步返回主因已修）、`m18-linux-007`（忙等复现器）
**可并行分片**：否（改 `components/linux`）
**预估**：2–3 h（标定：同档单点修复中位 86 min；本任务需复现 1/20 + 改守卫语义，取 1.5–2× 中位）
**档位**：中改（trap 守卫 + 缺页通道）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`，本 worktree 自建）

## 背景

`ISS-m18-012`（P1）：`traps.c:256 static volatile int dadao_trap_busy` 是**hart 全局**单标志。`dadao_trap_handler` 在 `:484` 置位后，`FROM_USER` 分支在**位仍为 1** 时调 `dadao_user_fault_from_umon` → `dadao_do_page_fault`（`mm/fault.c` 取 `mmap_read_lock`，**可睡眠**）；期间另一个任务以 `trap cfx_smon, FROM_USER` 到达，`:481` 判为递归 ⇒ `K2_FAIL_RECURSIVE` → `die mode=2 code=0xe`。

实测：`m18-linux-028` 的 20 启样本 **1/20**；签名 `ip=dadao_umon_excp+0x224`、`info=0x7f0802f5`，前一行是 `K4 umon->smon … ip=0x22110 info=0x8eb90`（缺页处理中）。与 `ISS-m18-011`（异步精确点残余）**不同源**。

## 目标

1. **复现**：用 `m18-linux-028` 的忙等探针（20 启级）取得 `1/20` 级样本，日志与现场落盘。
2. **修法**（只做最小、且**不得削弱递归检测**）：
   - 方向 A：把守卫改成**任务级**（`current` 上或 `thread_info`），hart 全局只保留“确实不可重入”的极小窗口；
   - 方向 B：进入可睡眠路径（分配/mmap 锁）前**显式清位/降级**，返回后恢复，并保证异步入口在该窗口仍安全；
   - 方向 C：二者结合。
   选择需给出依据（哪种能同时防真递归与跨任务误报），并在补丁注释写明。
3. **不得**用「遇到递归就 die 前加 retry」或「把 `K2_FAIL_RECURSIVE` 降级为 warn」掩盖。

## 验收（逐条贴真实 rc）

1. 修前：20 启 ≥1 次该签名（记录频率区间）；修后：20 启 **0 次**、且 100 启追加样本 0 次（样本数不足则写明）。
2. 现场证据：递归判定点、`dadao_trap_busy` 状态、睡眠点（`mmap_read_lock` 前后）的修前/修后对照。
3. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退修复 ⇒ 复现；② 构造**真递归**（例如在 `dadao_trap_handler` 内人为再触发一次同 hart 同步异常）⇒ 仍须被判定为递归（证明未削弱守卫）。
4. 不回归：K2 170/170、K5 285/285、K6 82/82、`run_suite.py --suite ltp` 两轮逐例一致、`amb_window_probe` 14/14、`--soak 300 --soak-strict` 窗口 0 且静默自旋 0。
5. 闭合 `ISS-m18-012`（`resolved_by` 指向本任务）；与 `ISS-m18-011` 的关系写明（不同源、各自独立）。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`；每跑次独立目录。
2. 只动：`components/linux/patches/**`、`components/linux/changelog.md`、`tests/unit/linux/**`、`tools/linux/**`、`.tao/knowledge/issues-m18.yaml`、本任务书。不改 `Makefile`/`spec/`/`.tao/contracts/`/其它组件。
3. QEMU 用本 worktree 自建（记 md5）；不覆盖共享安装根。
4. 组件补丁经 `make_patch.py linux` 重导；还原 `cp`+md5；还原后重建；同一时刻一个长跑批。
5. 禁「重试直到绿」；命中 `ISS-m18-005/006` 时单独计数记签名。

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
