# m18-linux-007: pthread create/join 闭环（K6 缺口）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-003`（K6 门控）、`m18-infra-001`（musl 基线）、`m18-linux-026`（0.8.1-rc 内核）、`m18-infra-002`（动态链接，已交付）
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测 31/62/86/124/182 min，中位 86 min；本任务以既有 clone/futex 为前提，取 1.5–2× 中位）
**档位**：中改（用户态线程 + 内核 futex/clone 验证）
**状态**：已验证
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

> **重派基线（2026-11-27）**：在 **0.8.1-rc 内核**（`cg15`/`cg16` + ack + 模式上限 + 出口帧，`m18-linux-026`）与**本 worktree 自建 QEMU**（记 md5，不覆盖共享安装根）上做；`m18-linux-025` 已闭合 `ISS-m18-001`，但 `ISS-m18-005`（随机 `HOST_TIMEOUT`）/`ISS-m18-006`（`handle_softirqs die`）/`ISS-m18-007`（无 syscall 重启）仍是已知低频/语义缺口：命中即单独计数记签名，每轮 ≤3 次重跑，**不得**当作本任务失败、也不得用重试掩盖；每次跑次单独目录留日志。

## 背景

- `m14-linux-029` 判 pthread create/join 属 K6 范围；用户 2026-11-20 定「建册时再定」，至今无任务书 ⇒ 本任务补立。
- musl 侧 `src/thread/dadao/clone.s` 已是真实现（`INFRA-095t`），内核 K4/K5 已有 `clone`/`futex`/信号；但**没有 create/join 的端到端证据**，K6 只到 busybox 前台执行。
- 本任务不引入新 ABI；期望值按 `contract-syscall.md`（`clone`/`futex`/`set_tid_address`/`exit`）与 `contract-abi.md` 的线程/TLS 口径。

## 目标

1. **验证**：静态 musl 程序完成 `pthread_create` × N + `pthread_join`（含返回值与 `void *` 回传）、`pthread_self`、每线程 TLS（`__thread` 计数）、`pthread_detach`、`pthread_exit`。
2. **定位**：任一项失败，定位到层（内核 syscall/futex、musl clone/TLS、调度/信号），给出证据；修复只做最小必要改动。
3. **门控素材**：交付一个可复跑脚本与探针（运行期证据目录 `run.sh`），结论可被后续 `check-linux-suite`/K6 扩展复用。
4. **动态边界**：动态链接版 pthread 依赖 `m18-infra-002`，本任务先静态；动态版作为遗留项记录并注明复跑入口，不得用静态结果替代动态结论。

## 验收（逐条贴真实 rc）

1. pthread 用例在 QEMU vast 上 **5/5 次连续通过**（同一镜像；每次输出逐字判定），日志含线程数、TLS 计数、join 返回值。
2. 失败路径/边界有断言：`pthread_create` 资源不足或 join 自身、detach 后 join 的错误码符合 `contract-syscall.md`（至少 1 条负向用例）。
3. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 破坏 `clone` 的 TLS/栈参数 ⇒ 用例红；② 破坏 join 唤醒（futex 源）⇒ 用例红；还原后回绿。
4. 不回归：`check-linux-k6` rc=0；`check-linux-k5` rc=0；`check-config-pins`、`check-patch-tree`（linux 与 musl 段与基线逐行相同）、`check-component-changelog` rc=0。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/musl/**`（最小）、`components/linux/patches/**`（最小，仅线程/调度/futex 相关）、`tests/unit/linux/**`、`tools/linux/**`、对应 changelog、本任务书。**不改** `Makefile`、`components/qemu/**`、`components/busybox/**`、`check-linux-k6` 判据。
3. 组件补丁按 `docs/Process-01` 重导；不改版本号；术语「bank = 寄存器组」。
4. 源码还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。
5. 不得以重试掩盖偶发；偶发红必须给频率与根因证据。

## 待裁定

无。

## 完成区

**测试结果**：探针用例 18/18 断言 × **5/5 连续通过**（静态 ELF 8/8：ET_EXEC/EM_DADAO/无 PT_INTERP/PT_DYNAMIC/1×PT_TLS）；负向 `RLIMIT_AS=4096 ⇒ pthread_create EAGAIN=11`（值取自镜像 `bits/errno.h`，落在 §9 的 `-4095..-1`）；ISS-m18-005 命中按纪律单列（判据 = **存在 `K2 async user` 行且无 `PTHREAD end` 行**；async 行在绿轮也出现，区分度靠 no-end），以最多 3 次重跑跨过，未计入失败。
**修改文件**：`tests/unit/linux/m18_pthread_probe.py`（新增，镜像/用例/判据）；本任务书；运行期证据目录内 `run.sh`（未入库）。**无组件补丁改动**（无需 changelog 条目）。
**验收结果**：最终版 `run.sh` 全量**连续两次 RC=0、`[FAIL]=0`**（每次 40 PASS/0 FAIL，末行 `run.sh: PASS`）。关键行：`assertion self-test: log rc=0|9999 and empty sha turn red … red`；`static /init sha256 == image manifest`；`pthread probe 5/5 consecutive PASS`；`RLIMIT_AS=4096: pthread_create returns EAGAIN 期望=11 实际=11`、`§9 期望=-4095..-1 实际=-11`（N 现场取自末份绿日志，非字面量）；注入①`clone.s` 红→还原（md5 `468e73f4…` 同）→`libc.a 2fe1c802…` 同→回绿；注入②`waitwake.c` 红→还原（`4f3bc847…` 同）→回绿；`check-config-pins rc=0`（97）、`check-patch-tree rc=0`（linux 105/musl 26，0 problem）、`check-component-changelog rc=0`、`check-linux-k6 rc=0`（**82/82**）、`check-linux-k5 rc=0`（**285/285**）。
**失败定位**：create/join/TLS/detach/负向均无内核/musl 缺陷；唯一红为已知 `ISS-m18-005`（用户态异步捕获返回路径），签名 = **存在 `K2 async user` 行且无 `PTHREAD end` 行**（非“末行”；async 行在绿轮也出现）；忙等复现器 `probe/pthread_busywait.c` 8/8 次 ISS-RED（同一 `frame_ip=0x22510`，每轮独立证据目录），证明属调度/异步入口层、非 pthread 逻辑。本任务**不做**该修复（非 create/join 层，已有 ISS 归属），仅按纪律计数。
**新发现/坑**：① musl 1.2.6 的 `pthread_join` 对“join 自身/已 detach 线程”是 UB（自等或 `a_crash()`），不返回 POSIX 错误码，故负向用例取 clone 资源不足→`EAGAIN`；② 首次版本在 join 前用 `usleep(20000)` 曾整机挂死（同 async 签名），最终版删除所有定时器等待；③ 用例的 barrier 只用于让 TLS 复读确定化，`pthread_join` 的 futex 唤醒由注入②单独证明可达红。
**遗留问题**：动态链接版 pthread 对照未跑（静态结果不替代动态结论）；复跑入口 = `python3 tools/linux/make_ldso_image.py --case probes`（`m18-infra-002` 记录 PASS）。`ISS-m18-005` 未修，建议后续批次按签名（`K2 async user` + 任务丢失）归因；`m18-linux-028` 可直接复用运行期证据目录 `probe/pthread_busywait.c` + `probe/run_busywait.py`（每轮独立目录，8/8 ISS-RED 已存档）。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 `tests/unit/linux/m18_pthread_probe.py` 与 `run.sh`，对每条 finding 的处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 首版 join 前 `usleep(20000)` 整机挂死（末行 `K2 async user`） | ✅已修 | 删除一切定时器等待；detach 线程以 barrier 收尾 | 5/5 连续 PASS |
| 判据 `PTHREAD .*fail` 误命中 `end fails=0`，导致假红 | ✅已修 | 改为精确 `create-fail / barrier-init fail / end fails=[1-9]` | 18/18 断言通过 |
| 纯用户态忙等版本把 ISS-m18-005 暴露到 8/8 红 | ❌不修 | 保留 barrier 形态（用户态窗口小）；红单列计数 | 忙等版 8/8 红、末行 `K2 async user`；barrier 版 5/5 绿 |
| clone 注入把 6 参 TLS bank 换成 `rb19`（ptid） | ✅已修（方式） | 注入作用于运行期 `clone.s`，`cp`+md5 还原 | 注入红 rc=1，还原 libc.a md5 不变、回绿 |
| futex 注入 marker 在两函数各命中一次（futex_wake/futex_wake_op） | ✅已修 | 按 `int futex_wake(...)` 函数起点定位插入 `return 0;` | 注入红 rc=1（无 join 行），还原回绿 |
| K5 需要运行期 qemu 源树的 `linux-user/riscv/syscall.tbl`；整树符号链接使 patch-tree 对他人未提交 qemu 工作树假红 | ✅已修（环境） | 改为运行期仅拷该 tbl，qemu 段按“source worktree absent”跳过 | `check-patch-tree rc=0`、`check-linux-k5 rc=0` |
| `CONFIG_PINS` 出现重复键 | ✅已修 | 去重；`py_compile` + config-pins C2/C3/C4 | `check-config-pins rc=0`（97 项） |
| `pthread_join` 自身 / detach 后 join 在 musl 1.2.6 为 UB（自等或 `a_crash`），无 POSIX 错误码 | ❌不修 | 负向改用 `RLIMIT_AS=4096 ⇒ EAGAIN`；在完成区记录边界 | 负向行 `neg-eagain rc=11` 逐字命中 |
| 每轮探针日志 `run-1.log` 互相覆盖，ISS 命中现场丢失 | ✅已修 | 增加 `--tag`，run.sh 每 attempt 独立 tag/日志 | 命中日志按 `bootN-aM-1.log` 独立保留 |


### 第 1 轮 reviewer 验收

**重跑记录（本人执行，仓库根，两次完整 `run.sh`）**
- 第 1 次：末行 `run.sh: PASS (… hits: 0)`，`[PASS]=38 [FAIL]=0`；boot1–boot5 各 **1 次 attempt** 全绿，逐次 `qemu rc=0; 18/18 checks passed`。
- 第 2 次（取真实退出码）：`RC=0`，`[PASS]=38 [FAIL]=0`；`ISS-m18-005 hits=4`（boot3/4/5-a1、restoreFutex-a1；签名 `last K2 async frame_ip=0x2d174 / 0x285dc / 0x2a660 …; no end line`），均按 ≤3 次纪律重试后绿，`5/5` 达成。
- 注入① `clone.s rb20→rb19`：源 md5 变 → 重建 → 探针红 `rc=1, no end line` → `cp`+md5 还原（`468e73f4…` 前后同）→ 重建 → `libc.a` `2fe1c802…` 前后同 → 回绿 rc=0。
- 注入② `futex_wake` 插 `return 0;`：源 md5 变 → 探针红 `rc=1`（begin 在、无 join 行）→ 还原（`4f3bc847…` 同）→ 回绿 rc=0。
- 门控（本人重跑）：`check-linux-k6 rc=0`（82/82）、`check-linux-k5 rc=0`（285/285）、`check-config-pins rc=0`（97 项）、`check-patch-tree rc=0`（linux 105 / musl 26，0 problem）、`check-component-changelog rc=0`、`check-knowledge-refs rc=0`。
- `llvm-readelf`（`/init` ELF）：`EXEC`、`Machine da0`、无 `PT_INTERP`/`PT_DYNAMIC`、1×`PT_TLS(.tbss)`。
- 快照对账：`git status --porcelain -uall` 空；clone.s / waitwake.c / libc.a / 探针 / 任务书 md5 与开跑前逐一相同。

**断言可达性**：18 条均有 FAIL 路径；当前版日志实测红 14 条；余 4 条（`kernel ran /init`、`begin n=4`、`detach rc=0`、`no failure text`）为行存在/坏文本判据，缺席即红（其中 2 条早期轮已实测红）；注入两路断言可达。

**约束核验**：改动 = 2 文件（与完成区一致）；无组件补丁/Makefile/spec/契约；未 push；状态 `待验收`；完成区 10 行；`run.sh` 无 `git checkout/restore/stash/reset`，还原全 `cp`+md5；负向 `RLIMIT_AS=4096 ⇒ EAGAIN=11` 的值由 musl `bits/errno.h` 现场派生，musl「join 自身 / detach 后 join」为 UB（自等、`a_crash()`）已如实记入完成区、未改测试迎合。

**finding**
1. **[阻断]** `run.sh` 两处恒真 PASS：L134 `ok "… fresh musl build" … "${INIT_SHA:-missing}"` 无条件打绿；L165–169 的 §9 范围判断写死 `[ $((-11)) -ge -4095 ]`，ok/bad 两支均输出 `-11`（禁恒真、禁两支写同一结果，AGENTS §4）。改：从末份绿日志现场取 `neg-eagain rc=N` 再判 `-N∈[-4095,-1]`；`INIT_SHA` 加非空分支。
2. **[阻断]** 8/8 忙等证据不完整：module log 存档 8/8 红（`end fails=0` 8 次 FAIL），guest 日志仅 5/8 留存（末行 `K2 async user frame_ip=0x22510`、无 `PTHREAD end`），另 3 份被后续同名默认 tag 轮覆盖；忙等版探针源码未留存 ⇒ 028 无法直接复用复现器。改：按 `--tag` 重跑忙等轮并把忙等版源码落证据目录，或把完成区改写为「5/8 签名存档 + 8/8 红 module log，复现器由 028 重建」。
3. **[记录]** `iss_hit` 实为「存在 async 且无 end」，非完成区所写「末行 async」；async 行在通过轮也出现，区分度全靠 no-end。

**判决**：Needs Revision（finding 1、2）。

### 第 2 轮 engineer 自审

| reviewer finding | 处置 | 改了什么 / 证据 |
|------------------|------|----------------|
| F1 `INIT_SHA` 恒真 | ✅已修 | `emit_sha` 要求 12–64 hex（空/`missing`/非 hex 红），并新增 `/init sha256 == image manifest` 等值断言；`assertion self-test` 用**实际日志取值路径**喂空 SHA、rc=0、rc=9999，三支均实测红 |
| F1 §9 范围恒真 | ✅已修 | `NEG_RC` 用 `sed` 从末份绿 guest 日志现场取，`emit_errno` 判 `-N∈[-4095,-1]`；自检对日志 rc=0/9999/-11 均判红（子 shell 丢弃 FAIL 行，不污染计数）；运行输出 `期望=-4095..-1 实际=-11` |
| F2 忙等证据不全 | ✅已修 | 复现器 `probe/pthread_busywait.c` + `probe/run_busywait.py`（用法见 `probe/README.md`）落证据目录；8 轮独立目录 `logs/busywait/run-N/`，结果 **8/8 ISS-RED**、`frame_ip=0x22510`、无 end，`summary.txt` 齐全；未凑数（首轮同名覆盖的 3 份不再冒充） |
| F3 签名口径 | ✅已修 | `run.sh` 注释与完成区统一为「存在 `K2 async user` 行且无 `PTHREAD end` 行」；明确 async 行绿轮也出现，区分度靠 no-end |
| 复验 | ✅ | 同版 `run.sh` 连续两次 **RC=0 / `[FAIL]=0`**；K6 82/82、K5 285/285；patch-tree linux 105/musl 26、0 problem；config-pins 97；两路注入仍红且 `cp`+md5 还原回绿 |

约束对账：未提交 git；仅动 `tests/unit/linux/m18_pthread_probe.py`、本任务书、运行期证据目录；无组件补丁/Makefile/spec/契约改动；还原一律 `cp`+md5。

### 第 2 轮 reviewer 验收

**F1 闭环（本人核）**：逐字抽取 `run.sh` 的 `ok/bad/sha_ok/errno_pos_ok/emit_*` 跑合成日志 —— `rc=0` / `rc=9999` / `-11` / 空 SHA **四支全红（rc=1）**，对照 `rc=11`、12-hex 绿；子 shell 调用后外层 `FAILS` 不变、直接调用则 `FAILS=4`（计数器有效、自检隔离正确）。`NEG_RC` 由 `sed` 从 `$LASTPASS`（末份绿 guest 日志，实含 `PTHREAD neg-eagain rc=11`）现场取值，非字面量；`INIT_SHA` 走 `sha_ok`（12–64 hex，空/`missing` 必红）并新增 `sha256 == image manifest` 等值断言（本人跑：`期望=a84acdf12801 实际=a84acdf12801`）；`assertion self-test … red` PASS。

**F2 闭环（本人核）**：`logs/busywait/run-1..8` 8 份齐全（各 `guest.log`+`verdict.txt`），逐份 `K2 async user: frame_ip=0x22510`、`PTHREAD end` 计数 0、`PTHREAD begin` 在、末行即 async 行，`summary.txt` 8/8 `ISS-RED`；复现器 `probe/pthread_busywait.c`（worker `hold()` 自旋 2e6、无 barrier）+ `probe/run_busywait.py`（仅改内存 `probe.PTHREAD_C`，不碰仓库探针）+ `probe/README.md` 的命令依赖（仓库探针模块、工具链、musl、内核树、自建 qemu）本机齐全，`m18-linux-028` 可直接复跑。

**F3**：`run.sh` 的 `iss_hit` 注释与完成区均为「存在 `K2 async user` 行且无 `PTHREAD end` 行」，一致（脚本另有 `begin` 前置，只收窄命中，不改口径）。

**复跑（本人 1 次全量）**：`RC=0`、`[PASS]=40 [FAIL]=0`、末行 `run.sh: PASS (… hits: 1)`；boot1-a1 命中 ISS（`async frame_ip=0x2a35c … no end line`，我复核该 guest 日志 async=2 / begin=1 / end=0）→ a2 绿，boot2–5 a1 绿，`5/5`；注入① `rb20→rb19` 红 `rc=1`（4 条 join 全缺、无 end，TP 破坏致 join 不返回）→ 还原 `468e73f4…` 同、`libc.a 2fe1c802…` 同 → 回绿；注入② 红 `rc=1`（begin 在、无 join 行、worker 0 行）→ 还原 `4f3bc847…` 同 → 回绿；`check-linux-k6 rc=0`（82/82）、`check-linux-k5 rc=0`（285/285）、`check-config-pins rc=0`（97）、`check-patch-tree rc=0`（linux 105 / musl 26，0 problem）、`check-component-changelog rc=0`、`check-knowledge-refs rc=0`。

**范围/快照**：`git status` 仅任务书 1 处；探针 md5 `c2afa5a7…` 与上轮相同（本轮未动）；未 push；状态 `待验收`；完成区 10 行；任务书 0 处运行期目录引用与宿主绝对路径；跑后 `clone.s` / `waitwake.c` / `libc.a` md5 与跑前逐一相同。

**判决**：Accepted。

