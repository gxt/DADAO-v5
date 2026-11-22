# m18-linux-011: ISS-496 applet 计数派生式订正

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-003`（K6 门控）
**可并行分片**：否
**预估**：30 min（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为单点判据订正，按 1/3 中位）
**档位**：小改（单点语义）
**状态**：待开始
**执行环境**：本地

## 背景

`ISS-496`【P3】（`m18-linux-001` 复核）：`check_k6.py` 的 applet 计数派生式 `enabled - infra` 依赖 `SH_IS_ASH` 与「`sh` 无独立符号」恰好抵消；未来新增非 applet `CONFIG_*` 会使期望虚高而假红（方向安全）。处置：随下次触碰 busybox 计数判据时改为按 applet 白名单/符号表派生。

## 目标

把期望 applet 数改为直接从 `components/busybox/config.min` 的 applet 白名单（或 `applets.txt` 符号表）派生，去掉 `enabled - infra` 的抵消假设；不放宽任何 K6 判据。

## 验收（逐条贴真实 rc）

1. 计数派生式不再依赖 `SH_IS_ASH` 或「`sh` 无独立符号」假设；改后 `check-linux-k6` 计数不变（现场打印）。
2. **可达 FAIL**：在 `config.min` 注入一个非 applet 的 `CONFIG_*`（如调试符号）⇒ 旧式会假红/新式仍绿；再注入少一个 applet ⇒ 新式判红；`cp`+md5 还原后回绿。
3. `check-linux-k6` rc=0；`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
4. `ISS-496` 在 `issues.yaml` 关闭（`closed_in: M18`）。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`tests/unit/linux/check_k6.py`、`components/busybox/config.min`（仅注入证据时临时改，还原）、`.tao/knowledge/issues.yaml`、本任务书。不改内核/其它组件。
3. 不改版本号；术语「bank = 寄存器组」。
4. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`。

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
