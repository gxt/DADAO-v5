# GEM5-026t: gem5 SE 线程/futex 与 TLS

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-025t`（IPC/多进程；同改 gem5 补丁，须先合并）
**状态**：待开始

## 背景与事实

- 基线 `GEM5-021t` 中 threads/futex 4 例：`futex`(98)（`functional/pthread_mutex_pi`）、`get_robust_list`(100)（`pthread_robust`、`pthread-robust-detach`）、`clone`(220)（`functional/vfork`）
- 大量 `libc-test` 的 `tls_*` 与部分 `pthread_*` 用例在信号/内存面补齐后会转而依赖 **TLS**；static 语料当前由 `rt_sigprocmask`/`mmap` 先挡住，需在本任务验证
- `GEM5-014t` 的 SE 只做了单线程、最小启动 syscall 面；未实现 `clone`/`futex`/per-thread TLS
- TP（线程指针）寄存器/`set_tid_address` 语义须先按 `spec/` + `contract-abi`/`contract-syscall` 核对；规范未明确处**不猜**，提交用户裁定

## 目标

1. **线程**：`clone`（`CLONE_VM|CLONE_THREAD|CLONE_SETTLS|CLONE_PARENT_SETTID|CLONE_CHILD_CLEARTID` 等按语料）、每线程栈、线程退出与 join；`set_tid_address` 的 clear-tid 语义。
2. **futex**：`FUTEX_WAIT`/`WAKE`/`REQUEUE`/`WAIT_BITSET`（按语料）；与 gem5 事件队列/多 CPU 上下文配合，不得忙等。
3. **robust list**：`get_robust_list`/`set_robust_list`。
4. **TLS**：每线程 TLS block 的分配与 TP 设置；musl static TLS（`__aeabi`/`tls_*`）验证；与信号/`clone` 的交互。
5. 不改测试用例/期望；不改 QEMU。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.*,process.*,isa.*,...}`、`components/gem5/changelog.md`、`components/gem5/README.md`、本任务书、`milestones.md`。

**不在范围**：动态链接（`GEM5-027t`）、IPC/多进程（`GEM5-025t`）、QEMU、测试用例与期望、spec 语义（未明确处先问）。

## 验收标准

1. 基线复跑：threads/futex 桶 blocked 归零；TLS 相关用例（`functional/tls_*`、`tls_local_exec` 等）实测通过或给出真实失败归因；`qemu_only_fail` 0。
2. 抽测：两线程 `pthread_create` + `join`、mutex 争用、`futex` 等待/唤醒、TLS 变量每线程独立、`pthread_exit` 清理。
3. `build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1/L2 rc=0。
4. 反例：把 `clone` 改回未实现 ⇒ 线程用例回 blocked；`cp`+`md5sum -c` 还原重建回绿（禁 git 还原）。
5. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 若 `spec/` 未定义 TP 寄存器/线程模型，先提交问题并停在该点；不得用 RISC-V 经验补全。
- 与 `GEM5-024t` 的信号帧、`GEM5-025t` 的多进程共享 `Process` 状态，注意回归。
