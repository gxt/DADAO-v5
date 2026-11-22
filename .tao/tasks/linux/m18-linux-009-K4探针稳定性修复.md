# m18-linux-009: K4 探针稳定性修复（ISS-493 F5 挂死 / ISS-494 kthread 时序）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-003`（K6 门控基线）
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测 31/62/86/124/182 min，中位 86 min；本任务为既有探针的根因修复，取 1.5–2× 中位）
**档位**：中改（内核自测入口 + 探针判定）
**状态**：待开始
**执行环境**：本地（QEMU system；K4/K5 镜像）

## 背景

两条既有缺陷已分诊到 M18（`issues.yaml`）：

- `ISS-493`【P1】：`k4_fork_probe` 的 F5 用户段偶发挂死。`arch/dadao/kernel/k4_selftest.c` 用**本地** `struct pt_regs` 调 `dadao_enter_user()`，第一次 umon `SKIP` 后 `escape` 目标取自 `task_pt_regs(current)->ip`（垃圾地址，实测恒为 `0xbef0`）⇒ `IGPTRAP` → `die-no-vma` → `panic: Attempted to kill init`。A/B 实测属既有偶发，与 `m14-linux-029` 无因果。
- `ISS-494`【P2】：`k4_kthread_probe` 的 `k2-task-dead` 在 `kthread_stop()` 后立即读任务态，偶见 `state=0 on_rq=1 frozen=1`；同镜像连跑可复绿 ⇒ 探针轮询与调度交接竞态。同类脆弱性也见 F5。

## 目标

1. **F5 根因修复**：改用 `task_pt_regs(current)` 作为入口帧（与 `k5_syscall_selftest` 同类调用一致），补「F5 用户段必到 `SYS_EXIT(0)`」的稳定复现判据。
2. **kthread 探针**：完成判据改为「事件 + 有界等待」，补 `sched_yield`/`cond_resched` 让出点；禁止用无界忙等或无依据 retry 掩盖竞态。
3. **证据**：修前签名可复现、修后连续多次全绿；失败时保留现场。
4. 不放宽既有 K5 判据；不改 K5 代表集语义。

## 验收（逐条贴真实 rc）

1. `ISS-493` 修复后，`k4_fork_probe` F5 同镜像**连跑 20 次全绿**（每次记录 F1/F3/F5 计数与退出码）；修前签名（`got=124` 或对应红）作为对照证据落盘。
2. `ISS-494` 修复后，`k4_kthread_probe` 同镜像**连跑 20 次全绿**；若仍偶发，给出频率、根因与剩余风险，不得以重试判绿。
3. F5 入口帧有静态断言（源码级：调用形态为 `task_pt_regs(current)`，禁本地帧），且注入回退后探针判红。
4. 不回归：`check-linux-k5` rc=0（280/280）、`check-linux-k6` rc=0；`check-patch-tree` linux 段 0 problem；`check-config-pins`、`check-component-changelog`、`check-knowledge-refs` rc=0。
5. 两条 issue 在 `issues.yaml` 关闭（`closed_in: M18`、`resolved_by` 指向本任务）。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`（仅 `k4_selftest.c` 及必要探针）、`tools/linux/k4_*.py`、`tests/unit/linux/**`、`components/linux/changelog.md`、`.tao/knowledge/issues.yaml`、本任务书。不改 `Makefile`、`components/musl/**`、`components/qemu/**`。
3. 组件补丁经 `make_patch.py linux` 重导；不改版本号；术语「bank = 寄存器组」。
4. 源码还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。
5. 禁「重试直到绿」；连跑计数与失败样本必须落盘。

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
