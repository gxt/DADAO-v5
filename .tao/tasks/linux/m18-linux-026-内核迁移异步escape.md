# m18-linux-026: 内核迁移到异步 escape（去 jmon、cg5 rc8–rc11 出口）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-spec-007`（已合入）、`m18-qemu-008`（QEMU 新布局，合入后本任务才可跑）、`m18-linux-024`（jmon 方案基线）
**可并行分片**：否（同改 `components/linux`）
**预估**：4–6 h（标定：`m18-linux-024` 3–5 h；本任务改入口/返程/同步桩/探针且要求 LTP 复跑，取 1.2–1.5×）
**档位**：大改（异步入口与返回、同步桩）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

**追加（m18-spec-009）**：异步进入判定加 `当前模式 ≤ cg15 rc14`；默认 supv 下 hypv 不被异步打断（内核当前不跑 hypv，此项为规范一致性）。

## 背景

`m18-spec-007` 已把出口改为 `cg5 rc8`–`rc11` + `escape cfxHA`，`cg9` 重排（`rc0`–`rc3` 记录、`rc4` 源集合、`rc5` pending、`rc14` switch、`rc15` vector）。`m18-qemu-008` 实现该模型。

内核当前仍是 R2 + jmon 方案（`m18-linux-024`）：异步入口抄 `cg9` 旧槽位（`rc0`/`rc1`/`rc2`/`rc3`），内核返程借 `trap cfx_jmon` + 软件跳板。新模型下 **jmon 不再需要**：异步进入把出口意图写进 hart 自己的 `cg5 rc8`–`rc11`，内核恢复 GPR 后直接 `escape cfx_hart`；`rc11` 在 `escape` 内整字恢复 mask，024 的“重开 mask → 返回”窗口问题从结构上消失。

## 目标

1. **入口桩**（`async_trap.S`）：按新 `cg9` 布局抄 `rc0`–`rc4`；出口意图从 hart `cg5 rc8`–`rc11` 读取并保存到每任务/每 CPU 现场；关中断窗口与 024 的现场保护原则保持。
2. **内核态返回**：恢复 GPR 后写回 `cg5 rc8`–`rc11`，`escape cfx_hart` 直接返回（**删除 jmon 跳板**、`trap cfx_jmon`、jmon 的 supv 行配置与权限、`dadao_async_kernel_resume` 的 jmon 语义）；不再需要“帧外 resume 区”那套幂等逻辑，除非新实现仍需（须给证据）。
3. **用户态返回**：保留 smon handoff + `irqentry_exit_to_user_mode_prepare` + `dadao_enter_user()` 的既有工作循环（信号/`need_resched`/task_work）；入口按新布局取 `cg9 rc0`（prev mode）判断 from_user。
4. **同步桩**（`trap.S` / `umon`）：`cg5 rc0`–`rc3` 只读后，所有“改写返回点”迁到 `rc10`（syscall 返回、跳过错、信号、execve 后不再 +4 的逻辑保持）；同步 `escape` 用 `escape cfxHA`（`imms18=0`），返回地址只认 `rc10`；`init_IRQ()` 写 `cg9 rc14/rc15`。
5. **探针/自检**：`tests/unit/linux/**` 中所有写 `cg5 rc0/1/3`、断言旧槽位、依赖 jmon 的代码改到新布局（K2 自检 0x16/0x17 改为对 hart `cg9 rc14/rc15` 与 `cg5 rc8–rc11` 的检查）；`amb_window_probe.py` 的窗口定义按新模型重做（`rc11` 原子恢复后窗口应不存在，改用“恢复→escape”是否有可乘之机做反例）。
6. **不回归**：K2 170/170、K5 285/285、K6 82/82；`m18-linux-024` 的窗口签名 0/≥2000 启；`m18-linux-006` 的 LTP 两轮逐例一致（解锁 006）；`ISS-m18-001` 的负载自旋按 `m18-linux-025` 处理（不在本任务）。

## 验收（逐条贴真实 rc）

1. 入口/返回：内核态异步返回不经过任何第二 monitor；`cg5 rc8`–`rc11` 正确写回；`escape cfx_hart` 后 mode/cfx/ip/mask 四者正确；`excp_async_num` 每次进入 +1、`escape_num` 每次返回 +1。
2. 同步桩：syscall 返回、跳过错、信号、execve 四类路径的 `rc10` 语义正确（沿用 024 的用例）；`cg5 rc0`–`rc3` 无任何软件写。
3. 回归：K2/K5/K6、`amb_window_probe`、`check-linux-toolchain`、`check-config-pins`、`check-patch-tree` linux 105/0。
4. **LTP 复跑**：与 `m18-linux-006` 的套件镜像配对，`run_suite.py --suite ltp` **连跑 2 次逐例一致**；024 族 flake 单独计数。
5. **可达 FAIL ≥2 路**：① 把 `rc11` 改成增量写/或返回后再开 mask ⇒ 窗口探针红；② 恢复 `trap cfx_jmon` 路径 ⇒ 探针/门控红；`cp`+md5 还原重建回绿。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`、`components/linux/changelog.md`、`tests/unit/linux/**`、本任务书。
3. 不改 QEMU/spec/契约/Makefile/musl/busybox/gem5/RTL/IDL/LLVM；不改版本号。
4. **配对**：必须用 `m18-qemu-008` 合入后的 QEMU（新布局）；若共享安装根未更新，先在任务证据里记录 QEMU md5 并用工作树内构建，禁止改别人的 QEMU。
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
