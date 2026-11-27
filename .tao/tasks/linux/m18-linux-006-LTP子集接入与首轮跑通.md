# m18-linux-006: LTP 子集接入与首轮跑通（组件锁 + 静态构建 + 分诊）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-005`（运行骨架）、`m18-infra-002`（动态链接）、`m18-infra-003`（musl 补丁集/信号帧，已验证）、`m18-linux-022`（内核新异步模型，合入后重跑 K5/K6）
**可并行分片**：否
**预估**：3–5 h（标定：同档最近 5 件派单→合入实测 31/62/86/124/182 min，中位 86 min；本任务新增组件与构建链，取 2–4× 中位）
**档位**：大改（新组件 + 交叉构建 + 首轮分诊）
**状态**：待开始

## 重派基线（2026-11-27，第三轮）

原阻塞已全部消除：`m18-linux-023`（内核解码扁平位图）、`m18-linux-024`（异步返程）、`m18-linux-026`（内核迁 0.8.1-rc：`cg15`/`cg16` + ack + 模式上限 + 出口帧）、`m18-qemu-007`（移除 jmon）、**`m18-linux-025`（`ISS-m18-001` 自旋根因闭合：umon 返回路径 restore 用户 SP 前关 supv 异步门）** 均已合入。

本轮要求：

- **配对**：用本 worktree 构建的 0.8.1 QEMU（记 md5）；内核用 master 的 0.8.1-rc 补丁集。**不得**覆盖共享安装根。
- **两轮一致是硬判据**：`run_suite.py --suite ltp` 连跑 2 次，逐例 verdict 必须一致（时间戳/序号除外）；不一致即红，不得挑一轮当结论。
- **低频红单列**：命中 `ISS-m18-005`（随机 case `HOST_TIMEOUT`，已见 `mm-pfnmap`/`mm-map-populate`/`futex-wait-timeout`）或 `ISS-m18-006`（`handle_softirqs die=0xe4`/`pf-va=0x10`）时，**单独计数并记签名**，不算该 case 的判定；每轮 ≤3 次重跑，超了如实记红。
- **证据留存**：每次跑次单独目录，日志不得被后续跑覆盖（025 第 3 跑已被覆盖，教训）。
- 历史返工成果（`TEST_ADAPT` 三项、64 KiB 判据、`suite.yaml` 期望、`mlockall02` 改 TBROK）保留，不重做。

**执行环境**：本地（QEMU system `-M kaiwu-vast`）

> **返工说明（2026-11-24）**：`m18-infra-003` 已证明 `sigaction01`/`open01` 可直接 PASS（原 UNSUPPORTED 是 musl 源树未打补丁集，非无信号帧 ABI）。返工时：`suite.yaml` 改 expect PASS、删两行 UNSUPPORTED、`mlockall02` verdict 改 TBROK；补 `TEST_ADAPT`（64 KiB 候选 `mmap01`/`brk01`/`munmap01` 现在可跑）；`run.sh` 的按类豁免改为基线逐行 diff；待 `m18-linux-022` 合入后用安装根新 QEMU/新内核重跑 K5/K6。

## 背景

- M18 口径（`milestones-m18.md`，用户 2026-11-22）：**两套件都跑**，`kselftest` 先、`LTP` 子集后，共用运行骨架；不以开发阶段现状为边界，4 KiB 页/大端假设的用例改成 64 KiB/大端正确判据；客观无法完成的记录原因、证据、复评条件。
- LTP 提供系统调用/ABI 广度，是「Linux 在 DADAO 上可用」的对外证据；其 `TBROK/TCONF` 分诊语义适合逐例归类。
- `m18-linux-005` 交付运行骨架（suite initramfs、逐例超时/采集、分诊台账）；本任务复用，不另建第二套。
- LTP 是独立上游仓库，需按 `docs/Process-01` 作为受补丁组件接入；语料不入库。

## 目标

1. **组件接入**：在 `manifests/components.lock.toml` 锁 LTP 基线（commit，不以 tag/分支作身份），新增 `components/ltp/`（`series` + `patches/`，首态可空），走 `make fetch` / `apply_series.py --component ltp`。
   - **已定（用户 2026-11-22）**：源 = `https://github.com/linux-test-project/ltp`；版本 = tag **`20260930`**（annotated tag object `a6bade7fde883afac61429197a28a643de239f6b`，peel commit **`2279d708c817db657611a30c427c7d06c4360049`**，锁 commit 不锁 tag）；浅克隆（`--depth 1 --branch 20260930`），不另测镜像。
2. **子集选型**：给出首轮子集清单（按文件/用例），覆盖系统调用 ABI 广度：文件 I/O、`mmap/mprotect/munmap`、`brk`、`clone/futex`、`execve/wait4`、基本信号、`clock_*`/`timerfd`。每条注明选它的理由与预期 `TCONF` 条件。
3. **构建**：用既有交叉工具链静态构建首轮子集（musl `-static`），产物逐项记录 `readelf`（`ELF64/MSB/EM_DADAO/静态`）；构建失败项逐条记录原因（缺头文件/依赖/工具）。
4. **运行**：接入 `m18-linux-005` 的 runner，在 QEMU `-M kaiwu-vast` 上逐例执行，采集 stdout/退出码/用例判定（PASS/FAIL/TCONF/TBROK），每例可独立超时。
5. **分诊**：所有非 PASS 归入 `KERNEL_BUG` / `TEST_ADAPT` / `UNSUPPORTED` / `SUITE_ENV`，附证据与复评条件；64 KiB 页/大端适配以可审计补丁落在 `components/ltp/patches/`（LTP 自身补丁集）。
6. **文档**：`tests/unit/linux/suite/ltp/README.md` 写清子集清单、构建命令、如何扩子集、`TCONF` 与真红的区分。

## 验收（逐条贴真实 rc）

1. `make fetch` + `apply_series.py --component ltp` rc=0；`check-patch-tree` 的 ltp 段 0 problem；`check-component-changelog` 覆盖新增改动。
2. 首轮子集构建 rc=0（允许个别目标失败，但每条失败必须在台账，不得静默）；产物静态 ELF 属性逐项成立。
3. 子集在 QEMU vast 上跑完，产出逐例结果；至少 1 个真实 PASS、至少 1 条 `TEST_ADAPT` 适配（64 KiB/大端，补丁生效前后判据可对照）、至少 1 条 `UNSUPPORTED` 或 `SUITE_ENV` 记录（按实况，不编造）。
4. 分诊计数现场派生且与台账一致；每例有独立超时标记；`HOST_TIMEOUT` 单独计数。
5. **可达 FAIL ≥2 路**（`cp`+md5 还原）：① 改一条期望值 ⇒ 该例判红；② 删除一条台账 ⇒ 台账校验红；还原后回绿。
6. 连跑 2 次 PASS/FAIL 集合一致（时间戳除外）。
7. 不回归：`check-linux-k6` rc=0；`check-config-pins`、`check-knowledge-refs`、`check-components` rc=0；`make check` 与基线逐行相同。
8. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内的 `run.sh`。
2. 只动：`manifests/components.lock.toml`、`components/ltp/**`、`tests/unit/linux/suite/**`、`tools/linux/**`、本任务书。**不改** `Makefile`、`components/linux/**`、`components/musl/**`、`components/qemu/**`、`components/busybox/**`、`check-linux-k6` 判据。
3. 内核缺陷只记录（证据 + 复现），不在本任务修——由主会话据此拆修复任务；**禁**把测试改为迎合内核现状。
4. 不新增未锁定的外部依赖；LTP 语料只在运行期构建目录，不入库。
5. 版本号不动；术语「bank = 寄存器组」；64 KiB 页/大端口径按 `MEMORY.md` 反套用清单。
6. 源码还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。

## 待裁定

无。

## Kirk 评估（用户 2026-11-22 要求核查）

- 上游：`https://github.com/linux-test-project/kirk`（LTP 官方测试执行器，`runltp-ng` 的 fork；本机浅克隆 HEAD `fc28d0b5`，`libkirk.__version__ = 4.2.0`；GPL-2.0-or-later）。
- 能力：SSH / QEMU / LTX 通道、suite 选择、并行 worker、shard、JSON/HTML 结果导出、插件式 ComChannel。
- **结论：不直接采用**。其 QEMU 通道要求 `qemu-system-<arch>` + 串口 console 上的登录/`#` 提示符，并执行 `stty`/`dmesg -D`/`export PS1=''`；我们的 guest 是 semihosting console、无 login、无 `stty`/`dmesg`，且 LTP 以静态 musl 进 initramfs，不是 qcow2 镜像。直接接 Kirk 需要新写 DADAO ComChannel + 在 guest 补工具，收益不抵成本。
- **可借用的是方法，不是代码**（GPL 不复制进本仓）：LTP suite/用例目录的选取方式、结果分类（pass/fail/broken/skip）、worker/shard 的组织、JSON 导出字段。首轮由 `m18-linux-005` 的 `run_suite.py` 扩展即可；若后续要跨机并行，再评估自写轻量调度器。
- 不在本任务引入 `kirk` 依赖；若未来要用，另立任务并先解决 GPL/许可与 ComChannel 适配。

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
