# m18-linux-025: 用户态异步投递在负载下自旋停摆（LTP ≈70%）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-024`（异步窗口修复，已合入）+ **`m18-linux-026`（0.8.1-rc：`cg15`/`cg16` + ack + 模式上限）**；026 复核结束即基于其分支 stacked 开工；阻塞 `m18-linux-006` 的验收 6
**派发时机（用户 2026-11-26 裁定 B）**：**等 `m18-qemu-008`（QEMU 新布局）与内核 async-escape 移植（`m18-linux-026`）落地后**，在新模型上修，避免在即将重写的返程路径上返工。
**可并行分片**：否（改 `components/linux`）
**预估**：3–5 h（标定：同档 linux-024 3–5 h；本任务为复现+根因+修复+长跑，取 1–1.5×）
**档位**：大改（异步入口/返回）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`m18-linux-006` 返工实测：LTP 多例负载下 **17 次完整跑只有 5 clean、12 flake（≈70%）**。停摆点随机（`mmap01`/`munmap03`/`read01`/`lseek01`/`clock_gettime01`/`open01`/`getpagesize01`），无 die、无 `SUITE CASE END`；QEMU vCPU 线程 100% CPU、主线程 `poll` 睡眠 ⇒ **guest 内核自旋**。单例跑与 kselftest 8 例可通过，说明与并发/多例负载相关。

**`m18-linux-026` 重启轮实测（0.8.1-rc，2026-11-27）**：soak 2000 启窗口签名 0、**非窗口红 410（≈20%）**；kselftest 两轮共 **19 次自旋尝试**（轮 1 10 attempts/9 spins、轮 2 6/5）；K6 attempts=2/spin=1、K5 attempts=1。即：自旋频率随负载显著上升（空载 ~0.1–1%，kselftest/LTP 负载 17–20%），入口未清的 pending 与 mask 关窗时序是首要嫌疑。

`m18-linux-024` 已修掉空载 1.3% 的 `va=0x208` 窗口（0/4800），但**没有覆盖本负载场景**；`ISS-m18-001` 记录了 3/4800 的非窗口红（`handle_softirqs` + `va=0x10`/`0x204002130f4`），与本现象可能同族。

## 目标

1. **可复现**：把“LTP 负载下随机自旋”做成定向、可重复触发的最小用例（≥1/5），并给出停摆现场：
   - PC 采样（反复同一小段 ⇒ 循环；落在 async/smon 桩 ⇒ 重复进入）；
   - `cfx_hart cg4 rc4 excp_async_num` / `cg4 rc5 escape_num` 是否暴涨；
   - `cfx_hart cg15 rc5`（原始 pending 汇总）/ `rc4`（本次进入的源集合）、目标 monitor 的 `cg15 rc3` 掩码、逐源 `cfx_hart|cfx_pmem cg16 rc17 pending` / `rc16 mask` / `rc18 ack`；
   - `dadao_ticks` 是否推进、`timer_cmp` 是否重装；
   - 当前 cfx/mode/PTBR。
2. **定位根因并修复**：优先判定是否为“异步入口重复进入”或“等待硬件状态”——**不得用重试/看门狗掩盖**，不得放宽任何 K2/K5/K6/LTP 判据。
3. **回归**：修后同负载（LTP 两轮逐例一致）不再停摆；`check-linux-k2` 170/170、K5 285/285、K6 82/82；`m18-linux-024` 的窗口探针仍 0/≥2000 启。
4. **基线口径**：本任务在 **`m18-linux-026` 分支的 0.8.1-rc 内核**（`cg5 rc8–rc11` 出口、`cg15` 捕获、`cg16` 逐源 mask/pending/ack、模式上限）上修，**不再回退到 0.8.0/R2**；修复点须与 `m18-qemu-009/010`、`m18-chipyard-003`、`m18-gem5-005` 的同口径一致。

## 验收（逐条贴真实 rc）

1. 最小复现：修前 ≥1/5 触发、修后 0（同一脚本、同一镜像、固定 seed/轮数）；两侧命令与日志完整。
2. 现场证据：上述 5 组观测量各一组修前/修后对照（`excp_async_num`、`src_pending`、mask、ticks、PC 采样）。
3. `m18-linux-006` 的 `run_suite.py --suite ltp` **连跑 2 次逐例 verdict 一致**（用其私有 QEMU/镜像，配对现行内核），024 族 flake 单独计数。
4. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退修复 ⇒ 复现停摆；② 去掉某个保护/断言 ⇒ 探针红。
5. 不回归：K2/K5/K6、`check-patch-tree` linux 段 0 problem、`check-config-pins`/`check-component-changelog`/`check-knowledge-refs`；`make check` 与基线逐行相同（跨实现红按既有 KNOWN-RED 归因）。
6. 更新 `ISS-m18-001`（闭合或补证据）；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`、`components/linux/changelog.md`、必要探针（`tests/unit/linux/**`）、本任务书。
3. 不改 QEMU/spec/契约/Makefile/musl/busybox/gem5/RTL；不改版本号。
4. **QEMU 配对**：用 026 分支构建的**私有 0.8.1-rc QEMU**（记录 md5），或先确认共享安装根已是 0.8.1 布局且无人使用；**不得**改别人的 QEMU、不得覆盖共享安装根。
5. 组件补丁经 `make_patch.py linux` 重导；还原 `cp`+md5；还原后重建；**同一时刻只允许一个长跑批**。
6. 术语「bank = 寄存器组」；完成区不写具体运行期路径。

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
