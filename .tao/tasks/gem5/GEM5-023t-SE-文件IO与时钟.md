# GEM5-023t: gem5 SE 文件 I/O 与时钟

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-022t`（已验证：brk/mmap 已落地）、`INTEG-058t`（转换编码迁移；同改 gem5 补丁，须先合并）
**状态**：待开始

## 背景与事实（`GEM5-022t` 后基线）

- gem5 SE static tset：pass 361 / blocked 217；`heap/VMA` 桶已清零
- 剩余缺口排序：**time budget 80**（非能力）、**文件 I/O 66**、**时钟 29**、信号 22、resource limits 7、IPC 6、threads 4、进程创建/信息各 1
- 代表案例（来自 `GEM5-021t` 基线）：`libc-test:functional/{fopen,fread,fdopen,openat,...}`、`stdio/*`、`printf` 家族；时钟类 `time()`/`clock()`/`clock_gettime`
- 当前 SE syscall 表已含 `brk/mmap/munmap/mremap/mprotect`（`GEM5-022t`）

## 目标

1. **文件 I/O**：实现 static tset 实际需要的 syscall 面（以基线 `reason` 里的 syscall 名为准），至少覆盖：
   - `openat`、`close`、`read`、`write`（既有）、`pread64`、`lseek`、`fstat`/`newfstatat`、`getdents64`、`dup`/`dup3`、`fcntl`（仅 tset 用到的命令）、`statfs`、`utimensat`、`readlinkat`、`unlinkat`、`mkdirat`（按需要）；
   - guest fd 表与宿主 fd 转发；`O_*` 标志、`EACCES/ENOENT/EBADF/EISDIR/ENOTDIR` 等错误码与 Linux 一致；
   - 目录遍历（`getdents64`）与 `stat` 结构体布局按 `contract-syscall`（大端、64 KiB 页）。
2. **时钟**：`clock_gettime`（CLOCK_REALTIME/MONOTONIC/PROCESS_CPUTIME_ID）、`gettimeofday`、`time`、`nanosleep`、`clock_getres`；时间源与 `TICKFREQ=1e9` 口径一致（`GEM5-019t`），不得与既有 `m5` 时钟冲突。
3. 不改测试用例与期望；不改 QEMU 语义。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.cc,se_workload.hh,process.*,...}`（按现场）、`components/gem5/changelog.md`、`components/gem5/README.md`（能力边界）、本任务书、`milestones.md`。

**不在范围**：信号、线程/futex、IPC（后续任务）；`convert_f2i`（`INTEG-058t`）；QEMU；测试用例与期望；`tests/parity/matrix-M11.md`。

## 验收标准

1. 基线复跑（`GEM5-021t` 驱动，static）：文件 I/O 与时钟两桶 blocked 归零（或转真实失败并给最小复现与归属）；`qemu_only_fail` 仍 0；`gem5_only_fail` 不新增（除已登记的 f2i 类）。
2. 代表案例（`functional/fopen`、`stdio/*`、`time` 类）各跑 ≥3 次结果一致。
3. `check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、`build-gem5`、L1 rc=0。
4. 反例：把 `openat` 改回未实现 ⇒ 代表案例回 blocked；`cp`+`md5sum -c` 还原重建后回绿（禁 git 还原）。
5. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 先按基线 `reason` 统计真正用到的 syscall，再实现；不做「全 syscall 表」。
- 文件系统侧只做 SE 需要的最小语义（无权限模型时按宿主权限透传），限制写进 README。
- 与 `INTEG-058t` 串行：两者都改 `components/gem5`，必须等其合并后再开。
