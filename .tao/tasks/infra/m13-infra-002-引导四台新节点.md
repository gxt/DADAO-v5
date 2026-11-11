# m13-infra-002: 引导 ics150–ics180 四台新节点

**模块**：infra
**项目里程碑**：M13
**依赖**：无
**可并行分片**：是（四台独立，互不干扰；主控机只做编排）
**状态**：待开始

## 用户授权（2026-11-12，原话）

> 「新的四台节点机，根目录和/home目录是两个磁盘，应该有300G可用，请确认；可以开展apt安装和长构建」

## 实测现状（2026-11-12）

- SSH 别名 `ics150`/`ics160`/`ics170`/`ics180`（`~/.ssh/config`，`HostName localhost` + 端口 22150/22160/22170/22180，用户 `ubuntu`，`sudo` 免密）
- 主机名 `ics150`–`ics180`，Ubuntu 24.04.5，**40 vCPU**、**125 GiB** 内存
- **磁盘确认（用户口径核对）**：`/` = 98 GB（可用 83 GB）、**`/home` = 338 GB（可用 320 GB）**，同一 VG（`sda3` 443.6 GB 拆两个 LV）⇒ 合计可用 **约 403 GB**，与用户「约 300 GB」一致且更宽裕
- **仓库不存在**（`~/DADAO-v5` 缺失）；`git`/`python3` 有；**`gcc`/`make`/`cc`/`ld` 全缺**

## 目标

1. **装包**：`nodes.md §4.2` 那份列表（`build-essential cmake ninja-build scons ccache` 等），四台并行，逐台留 `dpkg -s` 抽查证据。
2. **同步仓库**：用主控机 bundle（不走 GitHub），落到 `~/DADAO-v5`（在 `/home` 大盘上）。
3. **引导**：`tools/infra/bootstrap_node.sh`（`make fetch` → `apply-series` → `build-mc build-lld` → `install-host` → `make check`）。
4. **就绪判据**（`nodes.md §5`）：同一 commit 下 `make check` + `make check-inst` 与主控机一致。

## 参数

- `JOBS=16`（40 vCPU 留一半余量；**不沿用 207/208 的 32**）
- ccache 用节点本地默认目录、`max_size=50G`（不复制主控机配置）
- 每台日志落主控机 `.work/log/infra/m13-infra-001/<host>/`，逐台留 `*_EXIT`

## 验收标准

1. 四台 `dpkg -s build-essential make gcc` 均 installed
2. 四台 `~/DADAO-v5` 存在且 HEAD 与主控机一致
3. 四台 `make check` rc=0、`make check-inst` 与主控机同结果
4. 四台 `df -h /home` 有 ≥200 GB 余量（构建后）
5. 文档：`nodes.md` 的状态列改「就绪」，补实测口径（vCPU/磁盘/JOBS）

## 说明

- 长构建（LLVM 13 GB）**归主会话**监督：逐台留 PID/日志/EXIT，不 `setsid` 后失联。
- 磁盘余量：`/` 83 GB 给系统与 `/tmp`；构建主体在 `/home`（320 GB），够两套组件树。
- 失败处置：单台失败不阻塞其余三台；失败留现场并在本册记录原因后继续。

## 硬约束

1. 只动节点侧；仓库修改在主控机（本任务不改代码）。
2. 不 commit 节点侧改动；节点不装 OpenCode。
3. 计数与结论从命令现场输出直接抄（`ISS-388` 教训）。
4. 不放 `/tmp` 做跨机中转（`AGENTS.md`）；bundle 走 `.work/`。

## 审阅记录

（待填）
