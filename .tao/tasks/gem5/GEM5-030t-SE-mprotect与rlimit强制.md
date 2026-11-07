# GEM5-030t: gem5 SE mprotect 真权限与 RLIMIT 强制

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-029t`（syscall 语义对齐；同改 gem5 补丁，须先合并）
**状态**：待开始

## 背景与用户口径（2026-11-07）

> 「除非是 qemu-user 自己实现了某个系统调用，而 gem5 内部没有这个实现；否则都应该是一致的。」

已核对：QEMU 的 `mprotect` 走 `target_mprotect` 真正改页权限；`QEMU-084t` 在模拟器内按 guest 记账并强制 `RLIMIT_AS`/`RLIMIT_DATA`，`STACK` 默认读回宿主值。gem5 目前：

- `mprotect` 只校验不建模（`PROT_NONE`/只读不强制）
- `RLIMIT_DATA` 只在 `brk` 强制；`RLIMIT_AS` 不强制；`STACK` 默认读回 `RLIM_INFINITY`
- 这些在 `GEM5-022t`/`GEM5-024t` 被登记为「已知限制」，按新口径应改为**需对齐的差异**

## 目标

1. **`mprotect` 真权限**：在 SE 的 VMA/TLB 路径上记录每页权限；写只读页、访问 `PROT_NONE` 页、执行不可执行页必须触发 guest 可见 fault（按既有平台边界处理，至少不得静默成功）。`PROT_GROWSDOWN` 的栈特例按 Linux。
2. **`RLIMIT_AS` 强制**：`mmap`/`brk`/`mremap` 增长时按 guest 当前 AS 限额检查，超限 `ENOMEM`；`cur=0` 的 Valgrind workaround 与内核/QEMU 一致。
3. **`RLIMIT_STACK`**：未设时读回与 QEMU 一致（宿主值或实际映射值，按 `GEM5-030t` 落地时核对）；设置后对 `MAP_GROWSDOWN` 生效。
4. **`RLIMIT_DATA` 保持**并补 `munmap` 后的记账正确性（不得只在 brk 处看）。
5. 不改测试用例/期望、不改 QEMU。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.*,process.*,tlb.*,isa.*}`、`components/gem5/{README.md,changelog.md}`、本任务书、`milestones.md`。

**不在范围**：线程/动态/信号（前序任务）、QEMU、测试用例与期望、`spec/contracts`。

## 验收标准

1. **mprotect 双引擎探针**：`mprotect(PROT_READ)` 后写 ⇒ fault；`PROT_NONE` 后读写 ⇒ fault；恢复 `PROT_WRITE` 后可写；`PROT_GROWSDOWN` 栈特例与 Linux 一致。
2. **rlimit 双引擎探针**：`RLIMIT_AS={4MB,4MB}` 后 16MB `mmap` ⇒ `ENOMEM`；`RLIMIT_DATA` 超限 ⇒ `ENOMEM`；`RLIMIT_STACK` 未设时读回与 QEMU 相同；升硬限行为按 Linux。
3. 基线复跑：`gem5_only_fail` 不新增；`qemu_only_fail` 0；静态全量不退化（`vmfill`/`memfill`/`malloc-*` 等）。
4. `build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1/L2 rc=0。
5. 反例：把 `mprotect` 改回只校验（或去掉 AS 检查）⇒ 探针 FAIL；`cp`+`md5sum -c` 还原重建回绿。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是**高回归风险**改动：`vmfill` 依赖大量 `PROT_NONE` 映射，`mprotect` 真权限后必须确认静态语料不退化；必要时先做最小权限模型（页级读/写/执行位）再全量回归。
- 若发现 QEMU 的 `mprotect` 对某些边界与 Linux 不同，先记录并以 QEMU 实际行为为准（同模式对照）。
