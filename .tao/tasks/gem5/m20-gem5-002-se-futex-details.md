# m20-gem5-002: gem5 SE futex 三处细节对齐（ISS-345）

**模块**：gem5
**项目里程碑**：M20
**依赖**：`m16-gem5-026` 完成后再派（同组件写者）
**可并行分片**：否（单组件补丁）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（M20 分诊，2026-11-25）

`ISS-345` 记录 gem5 SE futex 实现与 Linux/QEMU 不完全一致；当前语料不可达，
但不能把已知缺陷留给后续。现场确认三处仍在 `se_workload.cc`：

1. `parkOnFutex` 在 `futexDeadline` 返回错误或已过期时直接返回，
   `new FutexWaiter()` 泄漏；超时分支也没有把 waiter 放回队列。
2. `FUTEX_UNLOCK_PI` 未校验调用者是否为 owner；Linux 对非 owner 返回 `EPERM`。
3. `FUTEX_REQUEUE`/`FUTEX_CMP_REQUEUE` 的返回值语义（唤醒数与改挂数之和）
   需要与内核/QEMU 对齐，且失败路径的计数不得虚增。

## 目标

1. 三处按 Linux 语义修正；不改 gem5 SE 的其它 syscall 行为。
2. 修正后 `FUTEX_UNLOCK_PI` 非 owner ⇒ `EPERM`；`FUTEX_REQUEUE` 返回值与
   Linux man page/内核实现一致；超时/错误分支无 `FutexWaiter` 泄漏。
3. 增加可执行验证：优先在 `tests/unit/gem5/` 或现有 SE 驱动中构造最小 futex
   序列（wait 超时、非 owner unlock、requeue 计数）；若当前 SE 语料确实不可达，
   须在完成区给出不可达证据与定向调试记录，并登记遗留，不得只写代码不验证。
4. 不改 `spec/` 与契约；futex 是 SE syscall 实现，不是 ISA 语义。

## 验收（逐条贴真实 rc）

1. 新增/扩展的 futex 探针：修改前至少 2 条 FAIL（非 owner unlock、timeout 泄漏
   或 requeue 返回值），修改后全 PASS；`cp` + md5 还原可分别回红/回绿。
2. `check-gem5-decode` rc=0；gem5 SE 代表集不回归（至少 `check-se-*` 现有目标
   或等价直跑）。
3. `check-patch-tree` gem5 段 0 problem；总 rc 受在途任务影响时按分段披露。
4. 完成区记录改动文件、探针命令、日志路径与 md5；不写具体构建/临时路径。

## 约束

独立 `git worktree`（分支 = `m20-gem5-002`）；不提交 git；只改
`components/gem5/**`、必要 unit/探针与本任务书；不改 `spec/`、契约、`Makefile`。
证据落在「运行期证据目录内的 `run.sh`」。

## 完成区

**测试结果**：新增跨引擎探针（`tools/testcases/se/{futex_probe.c,check_se_futex.py}`）：宿主 Linux（oracle）/ gem5 SE / qemu-user 三侧 **27 条断言逐行一致、`SUMMARY fails=0`**。修前（以 rebase 后的补丁集为基线、未加三处修正）gem5 侧 **6 条断言 FAIL**（`unlock_pi.nonowner-rc/-word`、`requeue.neg-wake-rc/-still-a`、`requeue.neg-count-rc/-still-a`），`leak 100k` vs `wake 100k` 峰值差 **4096 KiB（41.94 B/迭代）**；修后全 PASS，`leak 200k` vs `wake 200k` 峰值差 **0 KiB（0.00 B/迭代）**（<4 MiB 判据 PASS）。SE 代表集（libc-test static，`functional/(pthread|sem_|tls_)`）：`total=12 pass=11 fail=0 known-fail=0 blocked=1`（blocked = `functional/sem_open`，缺 `linkat`，M11 已登记缺口，非本任务引入）。
**修改文件**：`components/gem5/patches/src/arch/dadao/se_workload.cc.patch`（补丁 1 份改写）、`components/gem5/README.md`、`components/gem5/changelog.md`、`tools/testcases/se/futex_probe.c`（新增）、`tools/testcases/se/check_se_futex.py`（新增）、本任务书。
**验收结果**：运行期证据目录内 `run.sh` **19/19 checks passed、rc=0**：build rc=0；补丁集 106 份应用到 base 成功、结构与镜像一致、`se_workload.cc.patch` 与验证树逐字节一致（`patch-set-reproduces`）；`check-gem5-decode` rc=0（263 rows）；探针 rc=0 且 27/27；SE 代表集 fail=0。框架 `check-patch-tree` 的 gem5 段 rc=1（28 条 ⑥/⑨），但**全部落在「共享源树领先补丁集」的 14 个在途 `m16-gem5-027` 文件**，按分段披露并以 `patch-tree-gem5-problems-accounted` 断言归属；本任务文件 0 problem。`run.sh --inject` **11/11、rc=0**：（删 REQUEUE 负计数守卫）注入后 `git diff` 非空、探针 **rc=1 且 4 条 FAIL**（`requeue.neg-*` 的 rc 与 waiter 未动断言），`cp`+md5 还原（`aa0e68ec…` 与注入前一致）重建后探针回绿（20/20、0 FAIL）。补丁 md5 `e0703afc…`。
**新发现/坑**：① futex 探针必须按 `__dadao_argmask` 的逐位类型传参——futex mask `0x19` 把第 4 槽（REQUEUE 的 nr_requeue）标为地址槽，`syscall()` 变参按 `void*` 取；传 `long` 会让 op 落到错 bank（gem5 实测 `futex operation -66496`、qemu `ENOSYS`）。② `check_patch_tree` 的 ⑥⑦⑧⑨ 绑在 `.work/source/<c>`；并发写者窗口可复制 `tools/infra`+`manifests`+`components` 到临时 root、以验证树作 `source/gem5` 复算同组断言（不冒充全局绿灯）。③ 泄漏判据用**同 N** 的 leak vs wake 峰值差；`leak 2N − leak N` 斜率受 ~1 MiB 页级噪声影响（修后复测 0~8 B/迭代）。④ 并发写者会先把 WIP 提交进共享源树（本次 `m16-gem5-027` 在 00:18 以 `dadao: gem5 patch series` 提交了它的 15 个文件）；本补丁已 rebase 到该状态，因此 `se_workload.cc.patch` 同时包含其 RegRAS 改动——**若只交未 rebase 的全文件补丁，`apply_series` 的 `--reverse` 预检会把它当「已应用」静默跳过**。
**遗留问题**：① 派单时共享 `.work/source/gem5` 被在途 `m16-gem5-027` 占用；本任务在私有源树完成构建/取证，且补丁已 rebase 到共享树当前提交（含 027 的 RegRAS 改动）。architect 合入顺序应让 027 的 `components/gem5/**` 先落地（或同批解决 `se_workload.cc.patch` 冲突时取本补丁的版本），再跑 `make apply-series` 并以共享源树复跑 run.sh（脚本自动优先共享源树）取得全局一致的 `check-patch-tree` 绿灯；若 027 之后又改 `se_workload.cc`，只需把本补丁的 3 个 hunk（`parkOnFutex`/`REQUEUE`/`UNLOCK_PI`，与其 RegRAS 区域不重叠）文本 rebase。② repo-wide `check-patch-tree` 当前 rc=1：gem5 段的 ⑥/⑨ 全部来自 027 已提交进共享源树、但尚未导出/合入 master 补丁集的 14 个文件；另含 llvm/musl 两个在途写者的 ⑥⑨ 问题。本任务文件本身由 scratch tree 复算（`patch-set-reproduces-verified-tree`=0、`se_workload-patch-reproduces`=ok、28 条问题逐条归属在途文件）为 0 problem。③ `FUTEX_WAKE`/`REQUEUE` 对未映射 `uaddr`/`uaddr2` 仍不返回 `EFAULT`（Linux `get_futex_key` 会）——超出 ISS-345 三项范围，未改，建议另立 issue。④ 语料侧 `WAIT_BITSET`/`CMP_REQUEUE` 仍无调用点，本任务以跨引擎探针覆盖。

## 审阅记录

#### 第 1 轮 engineer 自审

逐行复核三处改动与新增探针/驱动；处置如下。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| ① 探针用 `long` 传 futex 第 4 槽：DADAO 按 argmask 的逐位类型分 bank，`syscall()` 变参按 `void*` 取该槽，使 `op` 读成指针（gem5 `futex operation -66496`、qemu `ENOSYS`） | ✅已修 | 第 4 槽改以指针宽度传入（`(void *)(uintptr_t)`）：WAIT 传 timespec 指针、REQUEUE 传计数 | 三引擎 27/27 断言逐行一致 |
| ② `parkOnFutex` 把 `futexDeadline` 提前后，无 timeout 时 `when` 不得被读取 | ✅已修 | `when` 只在 `timeoutAddr != 0` 分支使用，无 timeout 不建事件 | 源码逐行；无超时 WAIT 由 SE 代表集（pthread_mutex/cond/robust）实测 pass |
| ③ REQUEUE 负计数校验须在内核同位置（`get_futex_key`/CMP 之前） | ✅已修 | 校验放在 CMP 读字与任何唤醒之前，被拒调用零唤醒/零改挂 | `requeue.neg-*` 断言（rc=EINVAL 且 waiter 未动） |
| ④ `UNLOCK_PI` 非 owner 须 `EPERM` 且不改写用户字 | ✅已修 | 先读字判 owner，`EPERM` 在扫描 waiter 与写回之前返回 | `unlock_pi.nonowner-rc/-word` 断言 |
| ⑤ 泄漏检查用 `leak 2N − leak N` 斜率有页级噪声（修后仍 8 B/迭代且与重复测量不一致） | ✅已修 | 改为同 N 的 `leak` vs `wake` 峰值差，阈值 4 MiB（修前约 14 MB） | 修前判据 FAIL、修后 PASS；150k 两次复测 79872/80384 KiB |
| ⑥ `run.sh` 首版计数/解析 bug（`gem5: 106 patch(es)` 被当 problem、`27/27` 解析含尾串、BLOCKED 使 runner rc=1） | ✅已修 | 只数 `gem5: assertion`、summary 去尾串、SE 子集以 fail/known-fail/记账为判据、runner rc 仅 INFO | 最终 `run.sh` 19/19、`--inject` 11/11 |
| ⑦ 共享源树被在途任务占用，无法按 E1 在共享 `.work/source/gem5` 开工 | ✅已修 | 私有源树（base+1、clean）；补丁集在 `/tmp/opencode/<task>/` 的 scratch tree 复算（避免 `git apply` 在主仓内解析路径） | `patch-set-reproduces-verified-tree`=0、`se_workload-patch-reproduces`=ok |
| ⑧ `--inject` 首版把「注入后探针应红」也按 rc=0 计 | ✅已修 | 注入阶段改用负向判定（rc=1 且 FAIL 行数>0），还原阶段按正常判定 | `--inject` rc=0，注入红/还原绿的两段输出 |

#### 第 1 轮 reviewer 验收

**判决：Accepted**。以下均为 reviewer 亲自重跑的真实输出与退出码；全程未用 `git checkout/restore`，未改实现，只写本记录（改动前 5 个交付文件 md5 与审后逐一对账：`e0703afc…`/`f7eee0af…`/`7b43e5c3…`/`89228a5f…`/`7c5bf6cc…` 全部不变，`git status` 前后快照逐行相同）。

**重跑 rc**：仓库根执行运行期证据目录内的 `run.sh` → `== 19/19 checks passed`、rc=0（build rc=0；`patch-set-applies-to-base`=0、`patch-set-reproduces-verified-tree`=0、`se_workload-patch-reproduces`=ok、`patch-tree-gem5-problems-accounted`=0；`check-gem5-decode` rc=0 / 263 rows；探针 27/27；SE 代表集 `total=12 pass=11 fail=0 known-fail=0 blocked=1`，blocked = `functional/sem_open` 缺 `linkat`，M11 既有缺口）；`run.sh --inject` → `== 11/11`、rc=0（注入后探针 rc=1、4 条 `requeue.neg-*` FAIL，`cp`+md5 还原 `aa0e68ec…` 一致、重建回绿 20/20）。

**跨引擎 27 条**：reviewer 自行 `cc` 直跑宿主 oracle 27/27 rc=0；用驱动产物 guest ELF 直跑 `qemu-dadao` 27/27 rc=0；host/gem5/qemu 的 PASS 行两两 `diff` 为空；`floor` 由驱动现场统计 `check("` = 27，三引擎各 27 条唯一断言名。

**合入安全性**：`git diff master` 显示 `se_workload.cc.patch` 相对 master **只含三处 futex 修正**，027 的 RegRAS 内容与 master 逐字节一致（`ras::phys/setRasBase` 命中数同为 5）；027 的 16 个组件文件 overlay 只动该补丁与 `changelog.md`，其余 14 份补丁 `cmp` 全 same；`changelog` 3-way 合并后 027 条目与 M20 条目各 1 条（唯一冲突在补丁文件头 `index`/`@@` 行数两行，取本任务版本即得 `e0703afc…`，不丢 027 任何改动）。

**重放核验（scratch 树 = master + 本任务 5 文件）**：`apply_series.py --component gem5` rc=0「106 applied, 0 skipped」；`check_patch_tree.py` rc=0、**gem5 段 0 assertion**；重放结果 vs 私有验证树 `src/` 无差异，vs 共享 027 树只差 `se_workload.cc` 一个文件 ⇒ 三处修正之外零回归、027 的 15 份补丁未回退。

**基线红归属**：master 主仓 `check-patch-tree` rc=1 但 **gem5 段 0 问题**（红全在 chipyard 4 / llvm 2 / musl 2 的在途写者）；任务树 rc=1 的 gem5 30 条 = 14 个 027 未导出文件 ×2 + `se_workload`（共享源树尚无本修正）×2，与完成区 28 条口径（run.sh 以私有树作 source）同源，属在途/未合入，非本任务缺陷。

**语义独立查证（内核源，非实现反推）**：`kernel/futex/requeue.c:400 if (nr_wake<0||nr_requeue<0) return -EINVAL` 是函数首句，先于 key/CMP；`kernel/futex/pi.c:1211 (uval&FUTEX_TID_MASK)!=vpid ⇒ -EPERM` 位于 `get_user` 之后、waiter 扫描与写回之前；返回值 `ret ? ret : task_count` = 唤醒+改挂 —— 与三处实现逐条一致。

**独立注入（`cp`+md5 还原，未用 checkout）**：① 非 owner `UNLOCK_PI` 改返回 0 → md5 `9d99c2d0…`、`git diff` 非空、重建 rc=0 → 探针 rc=1、`FAIL unlock_pi.nonowner-rc want=-1 got=0`；还原 `aa0e68ec…` 重建 → 20/20 rc=0。② 早退分支经 `volatile` 静态槽泄漏 `FutexWaiter` → 重建 rc=0 → `gem5 peak RSS: leak 200000=88576 / wake 200000=78156`、`[FAIL] gem5-waiter-leak-peak-delta`、26/27、rc=1；还原重建 → delta 672 KiB、27/27 rc=0 ⇒ **泄漏判据有可达 FAIL**（坑：裸 `new FutexWaiter()` 结果未用会被 GCC 消除，必须挂 volatile 槽）。③ engineer 的 REQUEUE 守卫注入由 reviewer 重跑确认同样红/绿。

**范围核验**：`git status` 仅 4 改 + 2 新（README / changelog / `se_workload.cc.patch` / 本任务书 + 两个新探针），与完成区「修改文件」逐条一致；无 chipyard、无 `spec/`、无契约、无 `Makefile`；新探针与既有 `chmod_probe.c`/`check_se_chmod.py` 同落点同模式；`check-component-changelog` 两处 rc=0；`check-knowledge-refs` rc=0（本记录写入后已复跑）。

**遗留（不阻断本任务）**：① `FUTEX_WAKE`/`REQUEUE` 对未映射地址不返 EFAULT 已披露，**建议另立 issue**（超出 ISS-345 三项范围，本任务不改）。② 探针 `requeue.neg-wake-woken` 依赖 100 ms 停靠窗，高负载下 reviewer 实测到一次偶发 FAIL（`qemu want=2 got=1`），空载复跑 5/5 全绿 —— 只会假红、不会假绿，记 finding 供后续收紧。③ 完成区「峰值差 0 KiB」与 reviewer 复测的 −1652/−676/+1660 KiB 不一致（判据 <4 MiB 两侧均 PASS），属记录数值不精确，不改判。
