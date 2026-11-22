# m18-linux-014: mm-map-populate COW 路径 rwsem 警告与整机停摆

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-005`（套件骨架与首轮分诊）
**可并行分片**：否（与其它 linux 任务串行，同写 linux 组件）
**预估**：3–4 h（标定：同档最近 5 件派单→合入实测 31/62/86/124/182 min，中位 86 min；本任务为 COW/rwsem 根因定位，取 2–3× 中位）
**档位**：中改（mm 路径）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`m18-linux-005` 首轮分诊的 `mm-map-populate`（`KERNEL_BUG`）：

- 应用 64 KiB 适配（`0001`）与 pipe handshake（`0002`）后，用例越过 `tmpfile/ftruncate/mmap/msync/fork`，进入子进程 `MAP_POPULATE` 的 COW fault；
- 内核在 `include/linux/rwsem.h:81` 打出 WARNING，`Comm: map_populate/16`，随后整机不再输出任何内容（guest 侧 alarm 也无法触发，宿主只能判 `HOST_TIMEOUT`）。
- 去掉 `0001` 时更早在同子进程的 4 KiB 子页映射处卡住 ⇒ 适配把「测试假设问题」推进成了真实内核缺陷。

逐字证据与复评条件见 `tests/unit/linux/suite/triage.yaml` 的 `mm-map-populate` 行（`m18-linux-005` 交付）。

## 目标

1. 定位 `rwsem.h:81` 警告的根因（谁持有/释放 rwsem、COW `MAP_POPULATE` 路径上的 mmap_lock 或 anon_vma 锁状态），给出调用栈/现场证据。
2. 修复根因；不得以「测试加超时/重试」或关警告掩盖。
3. 修后该用例在套件中不再停摆：`run_suite.py --only mm-map-populate` 有明确 verdict（PASS 或它自己的断言 FAIL），且整机继续运行后续用例。

## 验收（逐条贴真实 rc）

1. 修前证据：警告调用栈/`rwsem` 状态、停摆点、`HOST_TIMEOUT` 记录；修后同命令连续 5 次无 `rwsem.h:81`、无停摆。
2. `python3 tools/linux/suite/run_suite.py --only mm-map-populate` 连续 5 次：verdict 一致（PASS 或稳定的断言 FAIL），每次有 `SUITE CASE END`；若仍 FAIL，必须是该用例自身断言，不是机器停摆。
3. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退修复 ⇒ 警告/停摆复现；② 破坏 COW 的页表/锁路径注入 ⇒ 用例判红或具名崩溃。
4. 不回归：`make check-linux-k5` rc=0（280/280）、`check-linux-k6` rc=0；`check-patch-tree` linux 段 0 problem；`check-config-pins`、`check-component-changelog`、`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
5. 任务完成后更新 `triage.yaml` 该行（verdict/证据/复评）并跑 `check_suite.py --latest` rc=0。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`（最小，mm/锁相关）、`components/linux/changelog.md`、`tests/unit/linux/suite/**`（triage/必要用例配置）、`tools/linux/suite/**`（仅必要）、本任务书。不改 `Makefile`、`spec/`、`.tao/contracts/`、其它组件。
3. 期望值以 `contract-syscall`/`contract-see` 与 Linux mm 语义为准，不从实现反推；DADAO 64 KiB 页/大端口径按 `MEMORY.md`。
4. 组件补丁经 `make_patch.py linux` 重导；不改版本号；术语「bank = 寄存器组」。
5. 源码还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。
6. 不得用重试掩盖偶发；停摆频率与样本必须落盘。

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
