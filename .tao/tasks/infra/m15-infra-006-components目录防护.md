# m15-infra-006: `components/` 目录防护（`.manifests.toml` 第二波）

**模块**：infra
**项目里程碑**：M15
**依赖**：`m15-infra-005`（guard 脚本与注册表机制已就位）
**可并行分片**：否
**预估**：1–1.5 h
**档位**：小改
**状态**：待开始

## 背景（用户 2026-11-18）

第一波已覆盖 `spec/`、`.tao/`、`.tao/knowledge`。第二波加 `components/`：**新增目录须经用户同意**（机械上 = 清单 diff 即审批点），每个目录的 `owner` 为对应模块，**唯一例外是 `busybox`**。

## 目标

1. 新建 `components/.manifests.toml`：
   - `subdirs` = 现场 `ls -d components/*/` 的 8 个（`busybox`、`chipyard`、`gem5`、`linux`、`llvm-project`、`musl`、`picolibc`、`qemu`），以现场为准；
   - `recursive = false`（子目录内部不受本清单约束，由各组件自己的 `patches/` 结构管）；
   - `files` = 现场直接子文件（若有；无则空 map）。
2. 在 `manifests/dir-guard-roots.toml` 的 `roots` 加 `"components"`。
3. `owner` 归属（写进清单条目，声明性）：
   - `llvm-project` → `llvm`；`qemu` → `qemu`；`gem5` → `gem5`；`linux` → `linux`；`musl` → `llvm`；`picolibc` → `testcases`；`chipyard` → `chipyard`；**`busybox` → `linux`（用户指定例外）**。
4. `components/README.md` 若存在则补一行说明「busybox 由 linux 模块维护」；不存在则不新建（保持现状）。
5. `AGENTS.md` 加一条：**`components/` 新增子目录须经用户同意**（机械判据 = `components/.manifests.toml` 的 `subdirs` 变更）。

## 验收（逐条贴真实 rc）

1. `make check-manifests-guard` rc=0；`grep -c "^\[\[component\]\]\|^name" manifests/components.lock.toml` 与清单无关（lock 是独立数据，不要求一一对应；只核 `components/` 目录）。
2. **新建 `components/zztest/` ⇒ guard rc≠0「多出子目录」**；`cp`/`rmdir` 还原 ⇒ rc=0。
3. **删 `components/busybox` ⇒ rc≠0「缺失子目录」**（用临时树或 `mv` + 还原，勿真删）。
4. 删 `components/.manifests.toml` ⇒ rc≠0（注册表机制生效）。
5. 一并回归：`check-patch-tree`、`manifest-check`、`check-component-changelog`、`check-dirs` 仍 rc=0（新增清单不得干扰它们）。
6. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**；不改版本号。
2. 只动：`components/.manifests.toml`（新）、`manifests/dir-guard-roots.toml`（一行）、`AGENTS.md`（一条）、`components/README.md`（若存在，一行）、本任务书。
3. **不碰任何组件源/补丁/`series`**（`components/linux` 有在途任务）。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

（无）

## 审阅记录

（待填）
