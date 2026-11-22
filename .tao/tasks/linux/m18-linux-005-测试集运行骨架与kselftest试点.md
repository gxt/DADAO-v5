# m18-linux-005: 测试集运行骨架与 kselftest 试点（首轮分诊）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-003`、`m18-linux-004`（K6 启动与命令闭环，均已验证）
**可并行分片**：否（套件骨架单点；与 `m18-infra-002` 文件集不重叠，可并行）
**预估**：2–3 天
**档位**：大改（新骨架 + 交叉构建 + 首轮分诊）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`；chipyard RTL 无 MMU/TLB，不纳入）

## 背景

- M18 主体是**套件级回归**：M14/M15 只有 `check-linux-k5` 的代表例，K6 只到 busybox 命令；没有套件就说不清「Linux 在 DADAO 上可用」。
- 用户 2026-11-22 裁定：**开发阶段用测试驱动内核完善，不迁就现状**——缺 `ldso` 就补（`m18-infra-002`）、4 KiB 页假设的用例改成 64 KiB 页、客观无法完成的用例记录原因/证据/复评条件，禁静默跳过。本任务只做**骨架 + kselftest 试点 + 首轮分诊**，不追求通过率。
- kselftest 与内核同源（`linux-stable v7.2.10`，commit 锁在 `manifests/components.lock.toml`），避免第二个版本轴；LTP 子集留后续任务。

## 目标

1. **构建**：从锁定内核树的 `tools/testing/selftests` 交叉构建**白名单目标**（`TARGETS=`），不改内核源码树工作副本；记录构建命令、日志、每个目标的成功/失败。
2. **镜像**：新增**独立 suite initramfs**，不改 K6 的 `/init`、`APPLETS` 与 `check-linux-k6` 判据。镜像至少含：试点测试二进制、`/proc` 挂载、可写 `/tmp`、`/dev/console`、`/dev/null`；构建保持确定性（`SOURCE_DATE_EPOCH`、mtime/uid/gid 固定）。
3. **运行**：QEMU `-M kaiwu-vast` 启动，逐例执行并采集 stdout/stderr/退出码。每例必须有**可独立归属**的输出标记与退出码；每例可独立超时——guest 侧优先（基于内核 tick 的 `alarm`/`setitimer`），宿主超时只作 liveness 兜底并标注 `HOST_TIMEOUT`（`ADR-0058`：guest 时间只用 `cfx_time` 或内核 tick）。
4. **结果**：机器可读 JSON + 人读摘要 + **在库分诊台账**；每条非 PASS 必归入 `KERNEL_BUG` / `TEST_ADAPT` / `UNSUPPORTED` / `SUITE_ENV` 之一，并附证据（用例、退出码、关键输出、日志路径）与复评条件。分类计数**现场派生**，禁写死。
5. **适配机制**：64 KiB 页 / 大端等测试假设的修改，以**可审计补丁**承载在 `tests/unit/linux/suite/patches/kselftest/`（运行时应用到套件副本，不改上游树）；补丁须有 manifest（上游 commit + 目标文件哈希）与「可干净应用」校验入口。**不得运行时手改源树，也不得把测试改动混进内核补丁集**。
6. **动态链接**：需要动态链接的用例不得用静态替代静默绕过；依赖 `m18-infra-002` 的记 `SUITE_ENV`（写明依赖），待其完成后重跑。
7. **文档**：`tests/unit/linux/suite/README.md` 写清：如何新增套件/用例、如何分诊、如何区分「内核红」与「测试假设红」、如何复现。

## 试点范围

- 至少 3 个 kselftest 目标/用例，优先 `timers`、`futex`、`mm` 中**可构建**的最小集（具体集合由实测决定并记录取舍）。
- 覆盖三类实况（若实况不成立，按实况报告，**不得编造**）：至少 1 个真实 PASS；至少 1 个需要适配（4 KiB 页/大端/环境假设）；至少 1 个客观不支持或环境不满足，且有记录。

## 验收（逐条贴真实 rc）

1. **一条命令**完成「构建 → 生成镜像 → 启动 → 采集 → 写台账」，输出 JSON 路径与摘要；脚本自身错误才非零（PASS/FAIL 不决定 rc）；连跑 2 次，PASS/FAIL 集合一致（时间戳除外）。
2. 至少 1 个 kselftest 用例真实 PASS，能在 guest 输出中逐字定位到该用例与判据；至少 1 条非 PASS 有台账记录并附证据；分类计数与台账行数一致。
3. 至少 1 条 **64 KiB 适配补丁**：应用到套件副本后该用例从错误失败变为正确判据（FAIL→PASS 或错误判据→正确判据）；适配校验入口在补丁不适用时判红。
4. **可达 FAIL ≥2 路**（`cp`+md5 还原）：① 篡改用例期望值/判据 ⇒ 骨架判红；② 删除一条台账记录 ⇒ 台账校验红；还原后回绿。
5. **不回归**：`make check-linux-k6` rc=0；`check-patch-tree` 的 linux 段 0 problem；`check-config-pins`、`check-component-changelog`、`check-knowledge-refs` rc=0；`make check` 与基线**逐行相同**（基线红按 `AGENTS.md §4` 判据）。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内的 `run.sh`。
2. 只动：`tools/linux/**`、`tests/unit/linux/**`、本任务书。**不改** `components/linux/patches/**`、`components/linux/changelog.md`、`components/busybox/**`、`components/musl/**`、`components/qemu/**`、`Makefile`、`check-linux-k6` 及其判据。
3. 套件源只用锁定内核树，不新增外部下载；工具链用既有交叉工具链（`.dadao/cross-toolchain`，由 `make install-host` 提供）。
4. 不写运行期路径进任务书/文档；术语「bank = 寄存器组」；大端、64 KiB 页、IP=当前指令地址口径按 `MEMORY.md` 反套用清单。
5. 客观无法完成项：记录原因、证据、影响面、复评条件；**禁静默跳过**，禁恒真断言，禁两支写同一结果。
6. 源码还原一律 `cp`+md5 对账；禁 `git checkout`/`restore`/`stash`；源码还原后须重建。

## 待裁定

无（口径已由用户 2026-11-22 裁定；若试点暴露 `Makefile` 门控接线需求，留给收口任务）。

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
