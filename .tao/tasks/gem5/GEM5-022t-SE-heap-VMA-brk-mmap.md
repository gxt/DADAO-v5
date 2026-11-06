# GEM5-022t: gem5 SE heap/VMA（brk + mmap/munmap/mprotect）

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-021t`（已验证基线：SE 能跑 tset，缺 syscall 面）
**状态**：待开始

## 执行环境
本地；只扩展 gem5 SE 的 guest 内存管理 syscall，不改 QEMU、不改测试用例/期望。

## 背景与事实（`GEM5-021t` 基线）

- gem5 SE 现有 syscall 面只有 `ioctl/write/writev/exit/exit_group/set_tid_address`
- static tset 基线（QEMU 587 pass / gem5 310 pass / blocked 270）中，**`brk` 是最大单一缺口：114 例**，`mmap` 21 例；代表：`libc-test:functional/{env,mbc,memstream,search_hsearch,search_insque}`、`libc-test:malloc-oom` 等
- 失败形态：malloc 一进入堆就 `fatal: syscall 214 not implemented (brk)`（或 mmap 号）
- SE 侧已有 `Process` 的 `brk_point` 与初始栈/映像布局，缺 syscall 表项与 VMA 映射路径

## 目标

1. **`brk`（214）**：实现 grow/shrink；缩小到 `brk_point` 以下按现场允许值处理；超出可映射范围 ⇒ 返回原 brk（Linux 语义）或 `ENOMEM`（按 `contract-syscall` 口径，先查契约再定）；新增/拆除匿名 VMA，页大小 64 KiB、大端。
2. **`mmap`（222）/`munmap`（215）/`mprotect`（226）**：至少支持 `MAP_PRIVATE|MAP_ANONYMOUS` 与 `MAP_FIXED` 语义；文件映射若 tset 静态用例需要再做（`MAP_SHARED`/`MAP_ANONYMOUS` 视现场）；
3. **VMA 管理**：地址区间注册/查找/拆除，与 `SETranslatingPortProxy`/页表一致；`munmap` 后访问按 fault 处理；
4. **不改测试**：`tests/tset/**`、`tests/**` 的用例与期望不动。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.cc,se_workload.hh,process.cc,process.hh,...}`（按现场）、`components/gem5/changelog.md`、本任务书、`milestones.md`。

**不在范围**：文件 I/O、时钟、信号、线程/futex（后续任务）、`convert_f2i` 语义（用户待裁定）、QEMU 实现、测试用例与期望、`tests/parity/matrix-M11.md`。

## 验收标准

1. 两引擎同一 static 产物：`brk`/`mmap` 相关 blocked 案例（基线 114 + 21）全部**不再 blocked**；转为 PASS 或真实 FAIL（失败须给最小复现与归属，不得回填 BLOCKED）。
2. 重跑 `GEM5-021t` 基线驱动（static）：`qemu_only_fail` 仍为 0；`gem5_only_fail` 只剩已知 `convert_f2i` 相关 9 例（用户裁定前不修）；其余套件数逐项记录。
3. 稳定性：受影响的代表案例各跑 ≥3 次，结果一致。
4. `make check-inst`、`make check-arch`、`make check`（L1）rc=0；gem5 源树 base+1 clean、`check-patch-tree` rc=0。
5. 反例：把 `brk` 改回未实现（或返回 0）⇒ 代表案例回到 blocked/fail；`cp`+`md5sum -c` 还原重建后回绿（禁 git 还原）。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 优先做 `brk`（114 例）再做 `mmap`（21 例）；每完成一项即用基线驱动复测，别攒到最后。
- `mmap` 的 `MAP_SHARED`/文件映射先测量再决定是否本轮做；若 tset 静态用例不需要，登记为后续。
- 页大小固定 64 KiB；地址范围与 `machine-profiles.yaml` 的 SE 布局一致。
