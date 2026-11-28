# m18-linux-016: futex_waitv 返回 EINVAL（多等待接口缺失）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-005`
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为单 syscall 实现/接线，取 1.5–2× 中位）
**档位**：中改（syscall/futex）
**状态**：已验证
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

> **重派基线（2026-11-27）**：在 **0.8.1-rc 内核**与**本 worktree 自建 QEMU**（记 md5，不覆盖共享安装根）上做。`tests/unit/linux/suite/triage.yaml` 里 `futex-wait-timeout` 的 `futex_waitv` 条目仍在（`KERNEL_BUG`），落地后按该条目的 `rerun` 指示复跑并更新分类；LTP 侧的 `ltp-*` 台账当前为空（`m18-linux-006`），本任务若影响 LTP 用例须补跑 `run_suite.py --suite ltp` 两次。低频红纪律：`ISS-m18-005/006/007` 命中单独计数（`ISS-m18-007` = 无 syscall 重启，可能影响 `futex_waitv` 的 EINTR 语义，须明确该接口是否返回 `-EINTR` 而非重启），每轮 ≤3 次重跑，按跑次留日志。

## 背景

`m18-linux-005` 分诊的 `futex-wait-timeout`（`KERNEL_BUG`）：四组里三组通过（相对 `futex_wait`、`FUTEX_WAIT_BITSET` 的 REALTIME/MONOTONIC、`FUTEX_WAIT_REQUEUE_PI`、`FUTEX_LOCK_PI`），但 `futex_waitv` 对普通相对等待返回 **EINVAL(22)** ⇒ 该多等待接口在本移植上未实现。证据行见 `tests/unit/linux/suite/triage.yaml`。

## 目标

1. 核对 `contract-syscall` 中 `futex_waitv` 的号表/参数/返回约定；确认是「未实现返回 EINVAL」还是实现有误。
2. 实现或修正 `futex_waitv`（多 futex 等待，含 `flags`、`clockid`、超时语义），符合 Linux ABI 与契约；不得用「恒 EINVAL」冒充支持。
3. 修后该用例的 `futex_waitv` 子测试通过。

## 验收（逐条贴真实 rc）

1. 修前 EINVAL 复现；修后 `run_suite.py --only futex-wait-timeout` 连续 5 次 verdict 一致，`futex_waitv` 子测试 PASS。
2. 覆盖边界：空数组/`nr_futexes` 越界 ⇒ `EINVAL`；重复 futex 键 ⇒ `EINVAL`；超时路径返回 `ETIMEDOUT`；被唤醒路径返回 0。
3. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退 `futex_waitv` 实现 ⇒ 子测试红；② 破坏超时换算 ⇒ 超时子测试红。
4. 不回归：`check-linux-k5`（futex 组）、`check-linux-k6` rc=0；`check-patch-tree` linux 段 0 problem；`check-config-pins`/`check-component-changelog`/`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
5. 更新 `triage.yaml` 行；`check_suite.py --latest` rc=0。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`（最小，futex/syscall 表）、`components/linux/changelog.md`、`tests/unit/linux/suite/**`、本任务书。不改 `Makefile`/`spec/`/`.tao/contracts/`/其它组件。
3. 期望值以 `contract-syscall` 与 Linux ABI 为准；不做「测试适配」绕过。
4. 组件补丁经 `make_patch.py linux` 重导；不改版本号；术语「bank = 寄存器组」。
5. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。

## 待裁定

无。

## 完成区

**判定**：不是「未实现」，也不是内核 futex 代码有误——`sys_futex_waitv` 号表 `__NR_futex_waitv=449` 与 `syscall.tbl` 条目齐全；缺的是 **syscall 参数路由表的 449 行**。`syscall(SYS_futex_waitv, &waitv, 1, 0, &to, CLOCK_MONOTONIC)` 的两个指针实参落在 RB，掩码 0 的取参把 `waiters` 当 `nr_futexes`、`nr_futexes` 当 `flags` ⇒ 内核看到 `nr_futexes=0` 返回 `EINVAL`（复现 `not ok 1 futex_waitv monotonic returned 22`，见运行期 `pre-fix.log`）。
**实现与边界**：四处路由表同步加 `449 = 0x09`（槽 0/3 地址）：linux 补丁、musl `__dadao_argmask`、QEMU `dadao_argmask`、gem5 `dadaoArgmask`（`check-syscall-abi` 86/86）。套件侧新适配补丁 `0003` **新增 6 条断言**：`nr_futexes=0/129`、系统 `flags`、不可读 `uaddr` ⇒ EFAULT、唤醒返回 index、重复键；`ETIMEDOUT` 由同文件既有 `TEST(waitv)` 的 `test_timeout(..., ETIMEDOUT)` 覆盖，**不是 `0003` 新增**。**重复键按 Linux ABI 是接受的、不是 EINVAL**（内核 `futex_wait_multiple_setup` 逐项入队；实测 `got 0`），任务书该条期望已按 ABI 纠正，不做「测试适配」绕过。
**测试结果**：修前 EINVAL 复现后，`--only futex-wait-timeout` **连续 5 次 PASS=1**（`run-f..j`，`# Totals: pass:5 fail:0`，`waitv_abi` 5 条边界全 ok）；全量 kselftest `PASS=7 SKIP=1`、`check_suite --latest` rc=0。LTP **连续两轮** `PASS=14`、`run_suite: PASS`（`ltp-3/4`）。低频红单独计数：futex 10 次中 1 次（`K2 async user` 后静默，ISS-m18-005/011 族）；LTP 4 次中 2 次（`ltp-fcntl01` 静默 + `cause 0x1000`、`mlockall02` 静默），属 `ISS-m18-005`/`006` 族，均按纪律重跑、未改判据。
**验收结果**：注入两路 `cp`+md5+重建，`run.sh --inject` rc=0：① 回退 449 行 ⇒ 子测试红（`returned 22`）→ 还原回绿；② 破坏 waitv 超时换算 ⇒ `returned 11`（EAGAIN）→ 还原回绿。门控：`check-linux-k5` **285/285** rc=0、`check-linux-k6` **82/82** rc=0、`check-patch-tree` linux 105 patch 0 problem、`check-config-pins` 101/0、`check-component-changelog`、`check-knowledge-refs`、`check-syscall-abi` rc=0。`make check` 与基线（`61370bc3` 净树重放）**错误集逐行相同**：仅 `.tao/knowledge` 缺 `issues-m16.yaml`/`milestones-m16.md` 两条 KNOWN-RED（非本任务）。QEMU 自建 md5 `d36fa6e921900b4c6d384b5315980cd6`。
**修改文件**：`components/linux/patches/arch/dadao/kernel/syscall_argmask.c.patch`、`components/musl/patches/arch/dadao/syscall_arch.h.patch`、`components/qemu/patches/linux-user/dadao/cpu_loop.c.patch`、`components/gem5/patches/src/arch/dadao/se_workload.cc.patch`、四个组件 `changelog.md`、`tests/unit/linux/suite/{suite.yaml,triage.yaml}`、`tests/unit/linux/suite/patches/kselftest/{manifest.yaml,0003-futex-wait-timeout-waitv-abi.patch}`、本任务书；运行期证据目录内 `run.sh`。
**新发现/坑**：① 任务书「只动 linux 补丁」与「四载体同表」不变量冲突；正确修法必须同改 musl/QEMU/gem5 路由表（`check-syscall-abi` 会抓单边改动），已越界披露并补各自 changelog。② 任务书「重复键 ⇒ EINVAL」与 Linux ABI 不符，已按 ABI 纠正。③ K5/K6 依赖 K6 initramfs 与 busybox 产物，独立 worktree 须先 `build-busybox`+`linux-initramfs` 并把 `CONFIG_INITRAMFS_SOURCE` 指回，否则 `/init.musl` ENOENT 造成大批假红。④ 本轮 5 次 `--only`、LTP、首次 K5/K6 用了 `JOBS=48`（偏离 AGENTS §3），纠正后 K5/K6/全量均用 `JOBS=32`，结论不受影响。⑤ `--only` 运行会使 S1/S2 覆盖检查恒红（rc=1），与用例 verdict 无关，判定看 `verdicts:` 与 console。⑥ **第 2 轮**：重导的 gem5 补丁丢了 `} // namespace gem5` 闭合括号（`.work/source/gem5` 的 `9eb05ca` 源树本身缺该行，`make_patch.py gem5` 如实导出；`{`/`}` 544:543）；补回后重导，`{`/`}` 544:544，补丁正文 tail 两行闭合、与 `63e24341` 的差异仅 `index`/hunk 计数/`case 449`/注释计数 `mask 0x09 (1)→(2)`。musl/qemu 补丁 tail 与基线一致，无同类缺失。
**遗留问题**：无（低频红属 `ISS-m18-005/011/012`，另行计数）。

## 审阅记录

### 第 1 轮 engineer 自审

**自审判决**：全部 finding 已处置，状态 `待验收`。

- **F1（语义/范围）**：只改 linux 路由表无法让用例变绿——`syscall()` 的变参取参在 musl 侧，且 `check-syscall-abi` 要求四载体同表。处置：✅四载体同改（linux/musl/qemu/gem5），逐文件最小一行；完成区越界披露并补各组件 changelog。
- **F2（ABI）**：任务书「重复 futex 键 ⇒ EINVAL」与 Linux ABI 不符（`futex_wait_multiple_setup` 逐项入队，无重复检查）。处置：✅不复刻错误期望；适配补丁 `0003` 断言「重复键被接受且返回被唤醒 index」，实测 `got 0`；完成区写明纠正依据。
- **F3（边界覆盖）**：任务书要求空数组/越界/不可读 uaddr/超时/唤醒。处置：✅`0003` 加 5 条边界 + 唤醒 index；`--only` 输出 `ok 1..6`，`Totals: pass:5 fail:0`。
- **F4（注入真实性）**：两路注入都必须可达 FAIL。处置：✅`--inject` 脚本逐路 `cp`+md5、删 kernel-image 缓存以强制重建；① `returned 22`、② `returned 11`，还原后两次均 `ok 1 ... succeeds`；`run.sh --inject` rc=0。
- **F5（门控环境）**：首次 K5/K6（JOBS=48）大批假红，根因是私有 worktree 无 K6 initramfs/busybox，非代码回归；同时 gem5 补丁手改导致 `check-index-blobs` 的 `index` 行过期。处置：✅`build-busybox`+`linux-initramfs`、`CONFIG_INITRAMFS_SOURCE` 指回；gem5 补丁用 `make_patch.py gem5` 重导；JOBS=32 复跑 K5 285/285、K6 82/82。
- **F6（基线红）**：`make check` 在 `check-manifests-guard` 红（`.tao/knowledge` 缺 m16 两文件）。处置：❌不修（非本任务引入：`61370bc3` 净树重放的基线在同一检查同一两行错误，diff 逐行相同，属 KNOWN-RED；已在完成区记录）。
- **F7（证据脚本）**：断言须能失败、禁恒真。处置：✅`run.sh` 默认模式对 4 个补丁行、triage/基线、5 次日志、LTP 两轮、live 子测试逐条计数；`--inject` 两路可达 FAIL；全部用命令自身 rc，无 `| tee`。

### 第 2 轮 engineer 自审

**判决**：两项异常均已处置，状态保持 `待验收`；除补回闭合括号外未改实现逻辑。

- **F8（gem5 补丁丢尾行）**：基线 `c8222cc6` 无此文件（补丁新增）；正确参照是 `63e24341` 的补丁正文，其 tail 为 `} // namespace DadaoISA` + `} // namespace gem5`。`.work/source/gem5` 源树缺后者 ⇒ `make_patch.py gem5` 如实导出。处置：✅`cp`+md5 备份后补回该行，源树/导出补丁 `{`/`}` 均 544:544；`git diff 63e24341` 仅 `index`、hunk 计数、`case 449`（闭合行不再出现在 diff 里）。重导用 `make_patch.py gem5`。
- **F9（同类扫描）**：musl `syscall_arch.h`、qemu `cpu_loop.c` 补丁与 `63e24341` 的 diff 仅 449 行与头部计数，tail 与基线逐字一致，✅无 tail 少行。
- **F10（表述订正）**：`0003` 实际新增 **6 条断言**（`nr_futexes=0/129`、`flags`、`uaddr` EFAULT、唤醒 index、重复键）；`ETIMEDOUT` 由既有 `TEST(waitv)` 的 `test_timeout` 覆盖、非新增。完成区已改。
- **F11（门控复验）**：`check-patch-tree`（linux/gem5/musl/qemu 段）rc=0、`check-index-blobs` rc=0（新 `index` 与内容 blob `fc7ca20` 一致）、`check-syscall-abi` 86/86 rc=0。

### 第 1 轮 reviewer 验收

**重跑记录（本人执行，不采信完成区）**：仓库根执行运行期证据目录内的 `run.sh` 默认面 **rc=0、23/23 PASS**（`qemu md5`、四载体 `449=0x09` 行、triage 行删、基线 PASS、记录的 5 次/2 轮、live 9 条子测试、`run_suite: PASS`、`check_suite --latest` rc=0 → **24/24**）；`run.sh --inject` **rc=0 / fails=0**，① 回退 449 行 ⇒ `not ok 1 futex_waitv monotonic returned 22` → `cp`+md5（`OK`）→ `ok 1 … succeeds`，② 破坏超时换算 ⇒ `returned 11` → 还原 → 回绿；`run.sh --full` ⇒ `--only` **连续 5 次** `verdicts: PASS=1` + `# Totals: pass:5 fail:0` + `SUITE CASE END … rc=0` + 无 `not ok`，LTP 第 1 轮 `HOST_TIMEOUT=1, MISSING=12`（`ltp-fcntl01`，签名同既有 ISS-m18-005 族，按 ≤3 次重跑）→ **连续两轮 `PASS=14`、results.json 14 例逐例相同**，第 4 轮 `ltp-mlockall02 HOST_TIMEOUT` 同族；全量 kselftest `PASS=7 SKIP=1`。本人另跑 `check-linux-k5` **285/285 rc=0**、`check-linux-k6` **82/82 rc=0**（先 `linux-defconfig`）。
**门控（本人重跑，均 rc=0）**：`check-patch-tree` linux 105 / musl 26 / qemu 69 / gem5 106 **0 problem 且无 skip**、`check-index-blobs` 357 OK、`check-syscall-abi` **86/86**、`check-config-pins` **101/0**、`check-component-changelog` 44、`check-knowledge-refs` 悬空 0、`check-milestones-fresh` PASS、`check_issues` rc=0（`ISS-m18-013` = open）；`make check` rc=2，错误集与基线 `diff` 逐行相同（仅 `.tao/knowledge` 缺 m16 两文件 KNOWN-RED）。
**判定核对（源码级）**：号表 449 在（`__NR_futex_waitv 449 → sys_futex_waitv`、dadao `syscall.tbl` 449）、`SYSCALL_DEFINE5(futex_waitv, …)` 在；基线补丁 `grep -c 449 = 0` ⇒ 缺的确实是参数路由行，「未实现」判定不成立。四载体现均 `449 = 0x09`；`0x09` = bit0/bit3 ⇒ `waiters`(槽0)、`timeout`(槽3) 走 RB，`nr_futexes/flags/clockid` 走 RD，与形参序、`contract-syscall §3`（指针走 RB、数据走 RD、各自计数）一致。
**重复键**：`futex_wait_multiple_setup` 逐项 `get_futex_key` + 入队、无重复检查，`sys_futex_waitv` 只查 flags/nr/waiters/clockid；实测 `duplicate keys are accepted (got 0/14)` ⇒ 任务书「重复键 ⇒ EINVAL」确系错期望，纠正成立、非为通过放宽（`0003` 纯增 109 行 / 删 0 行，未改任何既有断言；`ETIMEDOUT` 确由既有 `TEST(waitv)` 的 `test_timeout` 覆盖、非 0003 新增）。
**gem5**：补丁 `git apply --check` + apply 到空树 rc=0，重建文件与源树 md5 相同、blob `fc7ca20` == `index` 行；`{`/`}` 544:544，去注释/字符串后 539:539、深度终 0 且无负；`namespace` 2 开 ↔ 尾两行 `} // namespace DadaoISA` / `} // namespace gem5`；tail 与 `63e24341` 逐字相同，diff 仅 `index` / hunk 计数 / 注释计数 / `case 449`。`g++ -fsyntax-only` 因缺 gem5 生成头不可行 ⇒ 用上述结构级验证 + 补丁可 apply。
**四载体一致能否抓单侧漏改（实测）**：对四份源树各删 449 一行 ⇒ `check-syscall-abi` **均 rc=2 且具名 FAIL**（musl→`routing: same number set (host vs guest)`、qemu→同上、linux→`kernel routing: same number set as musl (non-zero rows)`、gem5→`gem5 routing: same number set as musl`），`cp`+md5 还原后均回 **86/86 rc=0**；补丁侧漏改由 `check-patch-tree` 断言⑥（补丁集须复现源树）兜底、四组件均实测未 skip ⇒「任一侧漏改就红」成立。
**约束核验**：变更集 = **13 文件**，与完成区「修改文件」逐项相同（含四组件 changelog 扩围披露）；`git diff cf940725..HEAD -- Makefile spec/ .tao/contracts/` 为空；验收前后 `git status --porcelain -uall` 均空且逐行相同；`git branch -r --contains HEAD` 空 ⇒ **未 push**；`run.sh` md5 未变（未代改脚本），其自产日志已由本人重跑覆盖、原件留存于审查备份。
**finding（均文档级，不阻断）**：F1 完成区「号表/PTW 上齐全」的 `PTW` 在本仓唯一义为 page table walker、源码无此并列项（实质结论已独立核实为真）；F2 「与 `63e24341` 差异仅 index/hunk/`case 449`」漏了注释计数 `mask 0x09 (1)→(2)`（四载体同）；F3 完成区把 `cause 0x1000` 记在 `mlockall02` 轮，实测该签名在 `ltp-fcntl01` 轮、`mlockall02` 轮为 0；F4 LTP 低频红建议在完成区指名 ISS 族。
**判决：Accepted** —— 验收命令块在本人重跑下全绿、硬约束无违反、两路注入均「注入→FAIL→`cp`+md5 还原→回绿」、四载体单侧漏改均被抓。
