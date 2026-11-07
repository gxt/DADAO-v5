# GEM5-029t: gem5 SE syscall 语义对齐（QEMU 已实现项）

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-026t`（线程/TLS；同改 gem5 补丁，须先合并）
**状态**：待开始

## 背景与用户口径（2026-11-07）

> 「除非是 qemu-user 自己实现了某个系统调用，而 gem5 内部没有这个实现；否则都应该是一致的。而 qemu-user 自己实现的系统调用，原理上也可以在 gem5 中实现一份，如果有这种情况出现，一定要和我说一声。」

已核对 QEMU 源码确有 handler（非透传）而 gem5 目前不等价的项：

- `nanosleep`：QEMU 真正睡眠并回写 `rem`；gem5 立即成功
- `wait4`：QEMU/Linux 在目标非子进程（但存在其它子进程）时返回 `ECHILD`；gem5 继续阻塞
- `execve`：QEMU 对存在但不可读的 ELF 返回 `EACCES`；gem5 经 loader 直接中止
- `pipe2`/`socket` 读：QEMU 先校验 guest 缓冲；gem5 在 `EFAULT` 前已消费数据
- `kill`/`tgkill`：QEMU 按进程组/全部进程；gem5 把 `pid∈{0,-1,-pid}` 当 self
- `sigaltstack`：QEMU/Linux 支持 `SS_AUTODISARM`；gem5 返回 `EINVAL`
- `faccessat`：QEMU/Linux 的 `AT_EMPTY_PATH` 返回 0；gem5 返回 `EINVAL`

## 目标

逐项对齐到 QEMU/Linux 语义（单进程/单线程范围内可实现的）：

1. `nanosleep`：按 guest 时钟推进（事件唤醒，不阻塞宿主），到期返回 0；被信号打断返回 `EINTR` 并回写 `rem`；`rem==NULL` 合法。
2. `wait4`：目标非子进程且有其它子进程 ⇒ `ECHILD`；pid 回收/复用按 Linux 基本规则（至少不无限增长）。
3. `execve`：不可读 ELF ⇒ `EACCES`；其它加载错误按 errno 返回，不 panic。
4. `pipe2`/`socket` 读：先验证 guest 缓冲可写，再消费；`EFAULT` 时数据不丢。
5. `kill`/`tgkill`：`pid>0` 查进程表；`pid==0` 发给同进程组；`pid==-1` 发给所有可发进程（含 self）；`tgkill` 校验 tgid。
6. `sigaltstack`：接受 `SS_AUTODISARM` 并按 Linux 语义处理；非法 flags 才 `EINVAL`。
7. `faccessat`：支持 `AT_EMPTY_PATH`（fd 有效时返回 0/`EACCES`），其余 flags 按 Linux。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.*,process.*,inst.cc}`、`components/gem5/{README.md,changelog.md}`、本任务书、`milestones.md`。

**不在范围**：`mprotect` 真权限与 `RLIMIT_AS/STACK` 强制（`GEM5-030t`）、线程/futex（`GEM5-026t`）、动态链接（027/028）、QEMU、测试用例与期望。

## 验收标准

1. 逐项双引擎探针（同 ELF 在 QEMU 与 gem5 SE 上）：7 项行为一致；每项至少含「正常路径 + 错误路径」两条断言。
2. 基线复跑：`gem5_only_fail` 不新增；`qemu_only_fail` 仍 0；相关 blocked 不退化。
3. `build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1/L2 rc=0。
4. 反例：任一项改回旧行为 ⇒ 对应探针 FAIL；`cp`+`md5sum -c` 还原重建后回绿（禁 git 还原）。
5. 完成区 ≤30 行；状态 `待验收`。

## 说明

- `nanosleep` 在 SE 中用事件队列推进 guest 时钟，不阻塞宿主；与「立即返回」相比这是语义对齐，不是性能优化。
- 每项改动前先写双引擎探针，确认 QEMU 侧行为作为 oracle（不反推 gem5）。
