# m18-linux-025: 用户态异步投递在负载下自旋停摆（LTP ≈70%）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-024`（异步窗口修复，已合入）；阻塞 `m18-linux-006` 的验收 6
**可并行分片**：否（改 `components/linux`）
**预估**：3–5 h（标定：同档 linux-024 3–5 h；本任务为复现+根因+修复+长跑，取 1–1.5×）
**档位**：大改（异步入口/返回）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`m18-linux-006` 返工实测：LTP 多例负载下 **17 次完整跑只有 5 clean、12 flake（≈70%）**。停摆点随机（`mmap01`/`munmap03`/`read01`/`lseek01`/`clock_gettime01`/`open01`/`getpagesize01`），无 die、无 `SUITE CASE END`；QEMU vCPU 线程 100% CPU、主线程 `poll` 睡眠 ⇒ **guest 内核自旋**。单例跑与 kselftest 8 例可通过，说明与并发/多例负载相关。

`m18-linux-024` 已修掉空载 1.3% 的 `va=0x208` 窗口（0/4800），但**没有覆盖本负载场景**；`ISS-m18-001` 记录了 3/4800 的非窗口红（`handle_softirqs` + `va=0x10`/`0x204002130f4`），与本现象可能同族。

## 目标

1. **可复现**：把“LTP 负载下随机自旋”做成定向、可重复触发的最小用例（≥1/5），并给出停摆现场：
   - PC 采样（反复同一小段 ⇒ 循环；落在 async/smon 桩 ⇒ 重复进入）；
   - `cfx_hart cg4 rc4 excp_async_num` 是否暴涨；
   - `cfx_hart cg9 rc4 src_pending`、当前模式 monitor 的 `cg8 rc1` 掩码；
   - `dadao_ticks` 是否推进、`timer_cmp` 是否重装；
   - 当前 cfx/mode/PTBR。
2. **定位根因并修复**：优先判定是否为“异步入口重复进入”或“等待硬件状态”——**不得用重试/看门狗掩盖**，不得放宽任何 K2/K5/K6/LTP 判据。
3. **回归**：修后同负载（LTP 两轮逐例一致）不再停摆；`check-linux-k2` 170/170、K5 285/285、K6 82/82；`m18-linux-024` 的窗口探针仍 0/≥2000 启。
4. **与规范演进的兼容**：`m18-spec-007` 已把出口改为 `cg5 rc8–rc11` + 异步 `escape`；本任务在**现行 R2 内核 + 旧版 QEMU** 上修（QEMU 新布局落地会改内核，见依赖），修复点要能在后续内核移植中保留/复用。

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
4. **QEMU 配对**：`m18-qemu-008` 落地后共享安装根是新布局，旧内核会 `CFXREG`；本任务须用**私有/旧版 QEMU**（记录 md5）或在共享根切回旧版前确认无人使用，**不得**改别人的 QEMU。
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
