# m18-linux-019: k5_syscall_selftest 锁外 find_vma 触发 rwsem 警告

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-014`（同组件写者串行；014 修 `fault.c` 的 VM_FAULT_COMPLETED 路径）
**可并行分片**：否
**预估**：1–2 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为单点锁外调用，取 1–1.5× 中位）
**档位**：小改（单点语义）
**状态**：待开始
**执行环境**：本地（QEMU system；K5 镜像）

## 背景

`m18-linux-014` 复核时发现（与本任务修前修后一致）：`arch/dadao/kernel/k5_syscall_selftest.c:472` 在**锁外**调用 `find_vma()`，K5 S 组日志出现 `include/linux/rwsem.h:81` 的 WARN；当前未 corrupt、`check-linux-k5` 仍 280/280，但属内核自测代码违反 mmap 锁约定，且会污染后续 K5/套件日志。证据见 `m18-linux-014` 运行期证据的 `logs/check-linux-k5.log`。

## 目标

1. 把该处改为在 mmap 读锁内调用，或使用已有 `dadao_pf_find_vma()`（按 `m18-linux-014` 同类写法）；不得无锁读 VMA。
2. 补一条可达 FAIL 的断言：锁外调用注入 ⇒ 探针/门控判红（或 `lockdep`/`mmap_assert_locked` 命中）。
3. 不改变 K5 代表集语义与 280/280 判据。

## 验收（逐条贴真实 rc）

1. `check-linux-k5` 280/280 rc=0，且 S 组日志 `rwsem.h:81` 出现 0 次。
2. 源码级断言：`k5_syscall_selftest.c` 的 `find_vma`/`dadao_pf_find_vma` 调用点位于锁内（静态检查或探针断言）；注入「移出锁」⇒ 判红，`cp`+md5 还原后回绿。
3. 不回归：`check-linux-k6` rc=0；`check-patch-tree` linux 段 0 problem；`check-config-pins`/`check-component-changelog`/`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
4. 组件补丁经 `make_patch.py linux` 重导；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/arch/dadao/kernel/k5_syscall_selftest.c.patch`（及必要时最小 mm 代码）、`components/linux/changelog.md`、`tests/unit/linux/**`、本任务书。不改 `Makefile`/`spec/`/`.tao/contracts/`/其它组件。
3. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。
4. 不改版本号；术语「bank = 寄存器组」。

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
