# m16-chipyard-028: RTL `cg9 rc6`（switch_run_mode）对齐：RW、复位 2、异步进入取该值

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m18-spec-006`（已合入：spec/契约改为「RW、复位 2 = supv；异步进入取该值」）；登记 `ISS-540`
**可并行分片**：否（同 `components/chipyard` 写者；须等 M16 当前 chipyard 批次收口）
**预估**：2–3 h（标定：同档最近 5 件 RTL 任务派单→合入实测中位约 3.7 h（024 3h42、025 11h37、026 2h23、027 3h07、023 4h02）；本任务为单寄存器 2 位字段，取 0.5–0.8×）
**档位**：中改（RTL 单寄存器面）
**状态**：待开始
**执行环境**：本地（chipyard `WumingTiny/Vast` 构建与 sim）

## 背景

`m18-spec-006` 已按用户裁定①把 `cg9 rc6`（`async_switch_run_mode`）口径定为：**RW、复位值 2（supv）、异步进入取该寄存器当前值**；QEMU 与 IDL 已是该行为。

RTL（`components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch`）实测仍是“恒 supv”：

- 读 rc6：`Mux(rows.isAsyncSwitch, 2.U, …)`（≈:1352）——恒 2；
- 写 rc6：注释「accepted, ignored, reads return 2」（≈:1586）——写不落地；
- 异步进入：`runMode := 2.U`（≈:2000）——不取 rc6。

⇒ RTL 与 spec/QEMU/IDL 不一致（`ISS-540` 已登记），需补齐。

## 目标

1. RTL：`cg9 rc6` 改为 **RW 2 位、复位 2**；异步进入用该值作为 `runMode`，不再硬编码 2；写侧落地；`cg9` 仍是只读捕获缓冲的其它槽不变。
2. 探针：覆盖「写 rc6=0/1/3 后读回」「异步进入按 rc6 切换」「复位值 = 2」；Tiny/Vast 各跑通（如适用）。
3. 与 QEMU/IDL 同场景逐字节签名一致；不一致登记 `tests/arch/expected-divergences.yaml` 并说明。
4. 不回归：既有 M16 cfx/cache 代表集、Tiny 基线；`check-patch-tree` chipyard 段 0 problem。

## 验收（逐条贴真实 rc）

1. chipyard `make verilog` + sim 构建 rc=0、`%Error`=0；sim md5 记录并注明环境。
2. 探针三组：复位 2、写 0/1/3 读回同值、异步进入 `runMode == rc6`；RTL 与 QEMU 同 ELF 签名一致。
3. **可达 FAIL ≥2 路**：① 读侧恢复 `Mux(isAsyncSwitch, 2.U, …)` ⇒ 写后读红；② 异步进入硬编码 `2.U` ⇒ rc6≠2 的进入用例红；`cp`+md5 还原并重建回绿。
4. 不回归：M16 cfx/cache 代表集、Tiny 基线；`check-patch-tree` chipyard 段 0 problem；`check-component-changelog` rc=0。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/chipyard/patches/**`（`GewuFile.scala.patch` 等 rc6 面）、`components/chipyard/changelog.md`、`tests/arch/**`（探针）、本任务书。
3. 不改 QEMU/gem5/LLVM/内核/spec/contracts；不改版本号；术语「bank = 寄存器组」。
4. 组件补丁经 `make_patch.py chipyard` 重导；生成断言用仓库生成器；还原 `cp`+md5；还原后重建。
5. 须等 M16 当前 chipyard 批次收口，避免同组件并发写；本任务由 M16 会话派单。

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
