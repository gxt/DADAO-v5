# m20-gem5-002: gem5 SE futex 三处细节对齐（ISS-345）

**模块**：gem5
**项目里程碑**：M20
**依赖**：`m16-gem5-026` 完成后再派（同组件写者）
**可并行分片**：否（单组件补丁）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（M20 分诊，2026-11-25）

`ISS-345` 记录 gem5 SE futex 实现与 Linux/QEMU 不完全一致；当前语料不可达，
但不能把已知缺陷留给后续。现场确认三处仍在 `se_workload.cc`：

1. `parkOnFutex` 在 `futexDeadline` 返回错误或已过期时直接返回，
   `new FutexWaiter()` 泄漏；超时分支也没有把 waiter 放回队列。
2. `FUTEX_UNLOCK_PI` 未校验调用者是否为 owner；Linux 对非 owner 返回 `EPERM`。
3. `FUTEX_REQUEUE`/`FUTEX_CMP_REQUEUE` 的返回值语义（唤醒数与改挂数之和）
   需要与内核/QEMU 对齐，且失败路径的计数不得虚增。

## 目标

1. 三处按 Linux 语义修正；不改 gem5 SE 的其它 syscall 行为。
2. 修正后 `FUTEX_UNLOCK_PI` 非 owner ⇒ `EPERM`；`FUTEX_REQUEUE` 返回值与
   Linux man page/内核实现一致；超时/错误分支无 `FutexWaiter` 泄漏。
3. 增加可执行验证：优先在 `tests/unit/gem5/` 或现有 SE 驱动中构造最小 futex
   序列（wait 超时、非 owner unlock、requeue 计数）；若当前 SE 语料确实不可达，
   须在完成区给出不可达证据与定向调试记录，并登记遗留，不得只写代码不验证。
4. 不改 `spec/` 与契约；futex 是 SE syscall 实现，不是 ISA 语义。

## 验收（逐条贴真实 rc）

1. 新增/扩展的 futex 探针：修改前至少 2 条 FAIL（非 owner unlock、timeout 泄漏
   或 requeue 返回值），修改后全 PASS；`cp` + md5 还原可分别回红/回绿。
2. `check-gem5-decode` rc=0；gem5 SE 代表集不回归（至少 `check-se-*` 现有目标
   或等价直跑）。
3. `check-patch-tree` gem5 段 0 problem；总 rc 受在途任务影响时按分段披露。
4. 完成区记录改动文件、探针命令、日志路径与 md5；不写具体构建/临时路径。

## 约束

独立 `git worktree`（分支 = `m20-gem5-002`）；不提交 git；只改
`components/gem5/**`、必要 unit/探针与本任务书；不改 `spec/`、契约、`Makefile`。
证据落在「运行期证据目录内的 `run.sh`」。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
