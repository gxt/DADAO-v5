# m18-linux-009: K4 探针稳定性修复（ISS-493 F5 挂死 / ISS-494 kthread 时序）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-003`（K6 门控基线）
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测 31/62/86/124/182 min，中位 86 min；本任务为既有探针的根因修复，取 1.5–2× 中位）
**档位**：中改（内核自测入口 + 探针判定）
**状态**：已验证
**执行环境**：本地（QEMU system；K4/K5 镜像）

> **重派基线（2026-11-27）**：在 **0.8.1-rc 内核**（`cg15`/`cg16` + ack + 模式上限 + 出口帧）与**本 worktree 自建 QEMU**（记 md5，不覆盖共享安装根）上做。注意 `m18-linux-025` 已在 umon 返回路径加 `DADAO_CLOSE_SUPV_ASYNC`（restore 用户 SP 前关 supv 异步门），K4 的 `dadao_enter_user()`/`task_pt_regs(current)` 路径若仍复现 F5，须确认是否落在该窗口之外。低频红纪律：命中 `ISS-m18-005`（随机 `HOST_TIMEOUT`）/`ISS-m18-006`（`handle_softirqs die`）时单独计数记签名，每轮 ≤3 次重跑，**不得**当作探针失败、也不得用重试判绿；每次跑次单独目录留日志。

## 背景

两条既有缺陷已分诊到 M18（`.tao/knowledge/issues-m18.yaml`）：

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
4. 不回归：`check-linux-k5` rc=0（**285/285**）、`check-linux-k6` rc=0；`check-patch-tree` linux 段 0 problem；`check-config-pins`、`check-component-changelog`、`check-knowledge-refs` rc=0。
5. 两条 issue 在 `.tao/knowledge/issues-m18.yaml` 关闭（`closed_in: M18`、`resolved_by` 指向本任务）。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`（仅 `k4_selftest.c` 及必要探针）、`tools/linux/k4_*.py`、`tests/unit/linux/**`、`components/linux/changelog.md`、`.tao/knowledge/issues-m18.yaml`、本任务书。不改 `Makefile`、`components/musl/**`、`components/qemu/**`。
3. 组件补丁经 `make_patch.py linux` 重导；不改版本号；术语「bank = 寄存器组」。
4. 源码还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。
5. 禁「重试直到绿」；连跑计数与失败样本必须落盘。

## 待裁定

无。

## 完成区

**测试结果**：`k4_fork_probe` 20/20 全绿（每次 rc=0、113/113；F1=16/F3=3/F5=43；low-freq 0/20）；`k4_kthread_probe` 20/20 全绿（rc=0、116/116；K1=10/K2=43/K3=24；low-freq 0/20）。修前对照：F5 本地帧+子任务未停靠 20/20 红（`ip=0xbef0`→`die-no-vma`；probe 3 跑 2 红 1 绿）；kthread 立即读 3/20 红（`state=0 on_rq=1`，rc=81）。两探针 `--selfcheck` PASS；3 路注入（`cp`+md5 还原+重建）先红后绿。
**修改文件**：`components/linux/patches/arch/dadao/kernel/{k4_selftest,k4_kthread_selftest}.c.patch`、`tests/unit/linux/{k4_fork_probe,k4_kthread_probe}.py`、`components/linux/changelog.md`、`.tao/knowledge/issues-m18.yaml`、本任务书。
**验收结果**：`REPO=<worktree> bash <运行期证据目录>/run.sh --runs 1` PASS（20 次全量见同目录 `final-k4b/`/`final-kthreadb/`）；`make check-linux-k5` rc=0 **285/285**；`check-linux-k6` rc=0 **82/82**；`check-patch-tree` 本工作树整体 rc=2（musl 2 problem，非本任务变更集）；**linux 段 105 patch、0 problem**（验收判据）；`check-config-pins` **101/101** rc=0；`check-component-changelog`/`check-knowledge-refs` rc=0。QEMU 本 worktree 自建 md5 `f89d533b5c2dc5be23aea1fb4ae982d4`；linux replay HEAD `12a010a87`（E1：base+1，`make_patch.py linux` 重导 2 改 103 不变）。
**新发现/坑**：① `0xbef0` 实测是 F1 子任务在 `vm_mmap()` 调度点被切到、以父帧 `ip=0xbeef` 进用户态（+4，硬件按 4B 对齐报 0xbef0），本地帧是第二隐患；F5 代码页只映射 `init_mm`，一次上下文切换后丢失（IGPTRAP→generic 零页→UNDI），故改任务表+`dadao_switch_mm()`。② F2 自 `m18-linux-001`（K6 eager fork stack）起在共享树上本已红（ISS-493 的 A/B 基线早于 001）：只读私有页不参与 eager 复制、仍在 generic COW 路径。③ `kthread_stop()` 只等 `kthread_exit()` 的 `exited`（在 `do_exit()` 完成前），事件须为 `TASK_DEAD && !on_rq`；`sched_yield()` 在本内核不可用，改用 `yield()`。④ K4 镜像会继承共享树的 `K6_SHELL`/initramfs（K5/K6 跑过之后），已钉 `K6_SHELL=n` 并在构建期临时清空 `CONFIG_INITRAMFS_SOURCE`（构建后恢复）。⑤ 主仓 `.work/source/linux` 停在 11-25（缺 025/028），按 base+series 重建 replay 才是本任务基线。
**遗留问题**：无（ISS-m18-005/006/011/012 本轮 0/40 未命中）。既有 `--skip-build` 分支为 raise（非本任务范围，未改）。

## 审阅记录

### 第 1 轮 engineer 自审
- finding 1：ISS-493 按「本地帧」单独回退只能偶发复现；实测主要触发点是 F1 子任务被调度。处置 ✅ 已修：子帧改内核停靠帧（`k4_park_child`），并保留 `task_pt_regs(current)` 入口帧；注入 `local-f5-frame` 使 S7 可达红，替代判据 `--selfcheck` 绿。
- finding 2：F5 代码页只映射 `init_mm`，有调度后 PTBR 指向任务 mm 即失效。处置 ✅ 已修：`k4_map_va(k4_mm,…)` + `dadao_switch_mm()`；20 次连跑验证。
- finding 3：F2 在当前基线因 K6 eager fork stack 变红（`pa_same=0/count=1`）。处置 ✅ 已修：F2 的 VMA 改 `PROT_READ`（只读私有页不参与 eager 复制，仍 `is_cow_mapping`）。
- finding 4：ISS-494 的等待若用裸 `schedule()` 不会让出（无 `sched_clock`）。处置 ✅ 已修：有界事件等待 + `cond_resched()`+`yield()`；`no-dead-wait` 注入使 S7 红。
- finding 5：K4 镜像会继承 K6 shell/initramfs，导致跑 `/init`。处置 ✅ 已修：`K6_SHELL_OFF` 钉 n + 构建期清空 initramfs 并恢复；`run.sh` 在 K6 之后连跑验证。
- finding 6：未使用的 `spins` 变量、注释错位。处置 ✅ 已修：删除/移动。
- finding 7：探针 `--skip-build` 设置 `snap=None` 后 raise（既有缺陷）。处置 ⏸ 延后：不在本任务范围（未改）。
- 判决：以上除 finding 7 外全部已修并有复验；任务状态 → `待验收`。

### 第 1 轮 reviewer 验收
**重跑记录（本人执行；分支 m18-linux-009 @ 2dbaa37d；QEMU md5 `f89d533b…`、linux replay `12a010a87`）**
- `k4_fork_probe` 20/20 rc=0、113/113；现场计数 F1=16/F2=14/F3=3/F4=11/F5=43（S=27）；低频 005/006/011/012 = **0/20**。
- `k4_kthread_probe` 20/20 rc=0、116/116；K1=10/K2=43/K3=24（S=34）；低频 = **0/20**；40 跑 `[FAIL]` 行合计 0。
- 两探针 `--selfcheck` rc=0（F1/F2/F4/F5、K1/K2/K3 各 mutation 全 caught）。
- 运行期证据目录内 `run.sh`（参数 `--runs 1`）**rc=0 PASS**：S7 7/7、两探针 1/1 绿、selfcheck 2、三注入 red/md5/green 全达标。
- 注入（本人重跑，`cp`+md5）：`local-f5-frame` S7 red=2、`no-dead-wait` S7 red=1、`no-stop-bit` K2 red=4（rc=81）；三次 md5 相等、`back to green rc=0 failures=0`。
- **本人另注入**：F2 VMA 退回 `PROT_READ|PROT_WRITE` ⇒ 62/74、12 FAIL，`cow-pa-shared 1→0`、`cow-parent/child-readonly 0→1`、`cow-two-references 2→1`（内核自报 `K4 FAIL: cow-pa-shared code=0x38`）；还原 md5 `a7c36f2e…` 相等、回绿 113/113 ⇒ **F2 五断言非恒真**（4/5 实测可达红；`private-content-equal` 是活值比对、非写死）。
- 门控：`check-linux-k5` **285/285** rc=0；`check-linux-k6` **82/82** rc=0；`check-config-pins` **101/101** rc=0；`check-component-changelog`、`check-knowledge-refs`、`check_issues` rc=0（493/494 closed，005/006/011/012 open）。
- `check-patch-tree` 本工作树 rc=2：2 problem **全在 musl**（`bits/signal.h` ⑨/⑥），**linux 段 105 patch、0 problem**（判据满足）；主仓整体 70 problem（其 linux 段亦红，源树停 11-25）＝别人在途。musl 不在本任务变更集（`git diff 9f4c9b42..2dbaa37d` 0 个 musl 文件）⇒ 非本任务引入。

**源码核验**
- F5 入口帧 `struct pt_regs *frame = task_pt_regs(current); … dadao_enter_user(frame)`（k4_selftest.c:638/653），无本地帧；子帧停靠 `cregs->ip=dadao_ret_from_fork; rb[1]=0; rb[3]=0; rd[16]=k4_park_child; rd[17]=0`（:525-529）+ `k4_park_child()` 无限 `TASK_INTERRUPTIBLE/schedule()`（:339-345）。
- F5 代码页 `k4_map_va(k4_mm, K4_F5_CODE_VA,…)` → `dadao_switch_mm(NULL, k4_mm, current)`（:613-615）；`dadao_switch_mm` 写 ASID + `dadao_ptbr_write(__pa(pgd))` + TLB flush（mmu.c:101-128），运行日志 `ptbr=0x20120000`。
- **`0xbef0` 解释成立**：`K4_PARENT_IP=0xbeef`（:79）→ F1 写进 `task_pt_regs(current)->ip`（:468）→ `copy_thread` 复制给子（process.c:250-252，实测 `parent_ip=0xbeef child_ip=0xbeef`）→ `dadao_ret_from_fork` 子臂 `regs->ip += 4`（process.c:375）=0xbef3 → `cfx_umon` supv `excp_vector` 写**忽略低 2 位**（QEMU helper `rc==15 … & ~0x3`；spec/DADAO-12 §3.4「写入忽略低 2 位」）→ **0xbef0** → 取指 IGPTRAP；修前样本 20/20 `ip=0xbef0 … die-no-vma` 逐条吻合。
- kthread：`k4kt_wait_dead()` 上限 `K4KT_SPINS=20000`、事件 `TASK_DEAD && !on_rq`、循环内 `cond_resched(); yield();`、超时具名 `k2-task-dead-wait` FAIL（k4_kthread_selftest.c:221-233/301-303）＝**有界 + 让出**，未把无界忙等换成另一种忙等。
- 修前对照独立复核：直接启动样本 20/20 红、完整探针 3 跑 2 红 1 绿、kthread 3/20 红 `state=0 on_rq=1` `code=0x51`（=81）。

**约束核验**：7 文件与「修改文件」逐一对上；两补丁正文与源码 replay 树 `awk|diff` 全等；无 `Makefile`/musl/qemu/manifests 改动、无「银行」、版本号未升；**未 push**（仅本地分支含 HEAD）；工作树与源码树 `git status` 干净、7 文件 md5 与验收前快照逐项相同（还原纪律：本人注入全部 `cp`+md5 回还原）。

**finding（非阻断）**：① 完成区「`check-patch-tree` rc=0、全局 464 OK」在本工作树重跑为 rc=2（musl 2 problem，非本任务变更集），linux 段判据满足，建议收尾按 linux 段口径表述。② ISS-493 title 前半仍写「escape 的目标取自 `task_pt_regs(current)->ip`」，实测红来自子任务**入口向量**路径（上链），同条「已修」段与任务书①已纠正，属文档级。

**判决：Accepted**（验收命令块在本人重跑下全过、硬约束无违反；`resolved_by: m18-linux-009` 对 493/494 成立：20/20 + 修前对照 + 源码级根因三者齐备）
