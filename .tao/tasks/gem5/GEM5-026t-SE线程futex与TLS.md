# GEM5-026t: gem5 SE 线程/futex 与 TLS

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-025t`（IPC/多进程；同改 gem5 补丁，须先合并）
**状态**：待开始

## 背景与事实

- 基线 `GEM5-021t` 中 threads/futex 4 例：`futex`(98)（`functional/pthread_mutex_pi`）、`get_robust_list`(100)（`pthread_robust`、`pthread-robust-detach`）、`clone`(220)（`functional/vfork`）
- 大量 `libc-test` 的 `tls_*` 与部分 `pthread_*` 用例在信号/内存面补齐后会转而依赖 **TLS**；static 语料当前由 `rt_sigprocmask`/`mmap` 先挡住，需在本任务验证
- `GEM5-014t` 的 SE 只做了单线程、最小启动 syscall 面；未实现 `clone`/`futex`/per-thread TLS
- **TP 已明确定义**：`spec/DADAO-21 ABI` 规定 `rb3 = rbtp`；TLS 变体/TP 偏置由 `contract-dynlink §2.4/§7` 下放给 musl arch 宏（`TLS_ABOVE_TP`、`TP_OFFSET 0`、`DTP_OFFSET 0`），线程模型已在 musl 实现、QEMU 已验证 ⇒ **无需裁定，按既有定义实现**

## 目标

1. **线程**：`clone`（`CLONE_VM|CLONE_THREAD|CLONE_SETTLS|CLONE_PARENT_SETTID|CLONE_CHILD_CLEARTID` 等按语料）、每线程栈、线程退出与 join；`set_tid_address` 的 clear-tid 语义。
2. **futex**：`FUTEX_WAIT`/`WAKE`/`REQUEUE`/`WAIT_BITSET`（按语料）；与 gem5 事件队列/多 CPU 上下文配合，不得忙等。
3. **robust list**：`get_robust_list`/`set_robust_list`。
4. **TLS（验收切片，不做 TLS 模型）**：事实是 TLS block 分配与 TP 初值都在 musl 用户态完成（`__init_tls`/`__set_thread_area` 写 `rb3`），spec 只定义 `rb3=rbtp`、TLS 变体由 `contract-dynlink §2.4/§7` 下放给 musl arch 宏 ⇒ **gem5 只在 `clone` 的 `CLONE_SETTLS` 路径把 `tls` 参数写入子线程 `rb3`**，不另造 TLS 模型、不分配 TLS block。验收切片：静态单线程 `functional/tls_align`（现基线已 pass）回归；每线程 `functional/tls_init`、`functional/tls_local_exec` 通过；两线程 `__get_tp()` 不同且各自 `TP+TPOFF` 落盘。
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

- **规范前提已核实**：`spec/DADAO-21 ABI` 只定义 `rb3=rbtp`；TLS 变体/TP 偏置归 `contract-dynlink §2.4/§7`，musl 端口已定值（`TLS_ABOVE_TP`、`TP_OFFSET 0`、`DTP_OFFSET 0`）并在 QEMU 验证 ⇒ **无需新 spec、无需新裁定**；若实现中发现 spec 未覆盖的新语义，再停下提交。
- gem5 缺 OS 常量层（`OS::TGT_CLONE_*`/`archClone`）：按最小实现手写 clone 分支，或在 DADAO 侧补最小 `linux.hh`，二选一在完成区说明理由。
- 与 `GEM5-024t` 的信号帧、`GEM5-025t` 的多进程共享 `Process` 状态，注意回归。
