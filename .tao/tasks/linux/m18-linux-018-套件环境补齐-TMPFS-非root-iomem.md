# m18-linux-018: 套件环境补齐（TMPFS/MEMFD、非 root uid、/proc/iomem）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-005`、`m18-linux-006`（LTP 两轮基线：0.8.1-rc 内核 + 自建 QEMU）
**可并行分片**：是（三个环境项互不重叠）；执行仍受 linux 组件写者互斥约束
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务三个环境项，取 1.5–2× 中位）
**档位**：中改（内核配置/镜像/权限）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`m18-linux-005` 首轮分诊有 3 条 `SUITE_ENV`（证据行见 `tests/unit/linux/suite/triage.yaml`）：

- `mm-mremap-dontunmap`：`memfd_create` 返回 ENOENT，因套件内核 `CONFIG_TMPFS=n`（无 shmem）；`mremap(MREMAP_DONTUNMAP)` 的匿名映射子测试本身已通过。
- `mm-pfnmap`：`/proc/iomem` 没有 RAM region，整例 SKIP。
- `mm-on-fault-limit`：套件以 PID 1（uid 0）运行，测试要求普通用户，整例 SKIP。
- **`m18-linux-006` 第三轮新增（2026-11-27，LTP 子集两轮）**：
  - `fcntl07`：套件镜像内 `PATH` 为空/不含 `/bin`，用例判 `SUITE_ENV`；
  - `mlockall02`：缺 `/etc/passwd`，`die-no-vma va=0x10` 后被 LTP 捕获为 SIGSEGV，判 `SUITE_ENV`——**须先确认该 `die-no-vma` 不是内核缺陷**（若属实，改写分诊并另立内核任务，不许用环境项盖掉）。

## 目标

1. **TMPFS/MEMFD**：在套件镜像的内核配置中启用 `CONFIG_TMPFS`（及 `CONFIG_MEMFD_CREATE` 所需项），使 `memfd_create` 可用；评估对 K6 镜像与 config pins 的影响，不得改 K6 判据。
2. **/proc/iomem**：让内核导出 RAM region（按 `spec/Kaiwu` 的内存映射，不改硬件语义）；若确属客观不支持，记录原因/证据/复评条件。
3. **非 root uid**：套件 supervisor 在跑用例前降权到非 root uid（需要 `setuid`/`setgid` 与镜像文件属主支持）；不得用「测试改成允许 root」绕过。
4. **套件基础环境**：给套件镜像补 `PATH`（`fcntl07`）与最小 `/etc/passwd`（`mlockall02`），使这两条不再因环境判 `SUITE_ENV`；`mlockall02` 若仍 `die-no-vma`，按内核缺陷改写分诊并停下写「待裁定」。
5. 每项修后重跑对应用例，更新 `triage.yaml`。

## 验收（逐条贴真实 rc）

1. `memfd_create`：套件内直接验证返回有效 fd（`run_suite.py --only mm-mremap-dontunmap`；该例的 memfd 子测试不再 ENOENT）。
2. `/proc/iomem`：`cat /proc/iomem`（套件内）含 RAM region，`mm-pfnmap` 不再因该原因 SKIP；若客观不支持，给出证据与「SKIP 原因」更新，不得静默。
3. 非 root：`mm-on-fault-limit` 不再因 root 拒绝运行；至少一条用例在非 root uid 下完成并有 verdict。
4. `fcntl07`/`mlockall02` 不再因 `PATH`/`/etc/passwd` 判 `SUITE_ENV`（前者应有 verdict；后者若转为内核缺陷，须有 `die-no-vma` 签名与复评条件）。
5. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退 TMPFS 配置 ⇒ memfd 用例回 ENOENT；② 回退 uid 降权 ⇒ 用例回 root SKIP。
6. 不回归：`make check-linux-k6` rc=0；`check-config-pins` 更新的钉子与实况一致；`check-patch-tree` linux 段 0 problem；`check-component-changelog`/`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
7. `check_suite.py --latest` rc=0；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`（配置/必要内核代码）、`components/linux/changelog.md`、`tests/unit/linux/suite/**`（含镜像配置/用例配置/triage）、`tools/linux/suite/**`、`tests/unit/linux/check_config_pins.py` 的钉子（仅随配置变更同步）、本任务书。不改 `Makefile`/`spec/`/`.tao/contracts/`/其它组件。
3. 不改 K6 镜像与 `check-linux-k6` 判据；不改版本号；术语「bank = 寄存器组」。
4. 客观不支持的项：记录原因、证据、影响、复评条件；禁静默跳过。
5. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。

## 待裁定

无（若某项需改 `spec/Kaiwu` 的内存映射语义，停下写「待裁定」）。

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
