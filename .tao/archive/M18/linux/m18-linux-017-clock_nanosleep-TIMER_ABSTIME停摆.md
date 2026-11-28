# m18-linux-017: clock_nanosleep(TIMER_ABSTIME) 停摆（作废：已不复现；归因待定）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-005`
**可并行分片**：否
**预估**：3–4 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务涉及时钟/定时器阻塞路径，取 2–3× 中位）
**档位**：中改（time/hrtimer）
**状态**：已验证
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`m18-linux-005` 分诊的 `timers-nanosleep`（`KERNEL_BUG`）：程序打出 TAP header/plan（`1..12`）后**完全无输出**——没有内核日志、没有 guest alarm、没有 case end；第一条子测试调用 `clock_nanosleep(CLOCK_REALTIME, TIMER_ABSTIME, now+10ns)` 后机器停止推进。因此该用例被标 `stall: true` 单独 boot，宿主无进展看门狗是唯一兜底（`HOST_TIMEOUT`）。证据行见 `tests/unit/linux/suite/triage.yaml`。

## 目标

1. 定位 `TIMER_ABSTIME` 绝对时间路径的停摆根因（时间基准、deadline 换算、hrtimer/时钟事件编程、到期中断投递、返回用户路径）。
2. 修复；不得用「把测试改成相对时间」或加宿主超时掩盖。
3. 修后该用例能跑完全部 12 条子测试并给出明确 verdict。

## 验收（逐条贴真实 rc）

1. 修前停摆签名与 `HOST_TIMEOUT` 落盘；修后 `run_suite.py --only timers-nanosleep` 连续 5 次无停摆、verdict 一致。
2. 覆盖：绝对/相对 `clock_nanosleep`、过去时间立即返回、被信号打断返回 `EINTR`、`clock_gettime(CLOCK_MONOTONIC/REALTIME)` 与 `cfx_time` 基准一致（`ADR-0058`：guest 时间只用 `cfx_time`/内核 tick）。
3. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退修复 ⇒ 停摆复现；② 破坏 deadline 换算 ⇒ 超时子测试红或停摆。
4. 不回归：`check-linux-k2`（时间边界）、`check-linux-k5`（T 组 34/34）、`check-linux-k6` rc=0；`check-patch-tree` linux 段 0 problem；`check-config-pins`/`check-component-changelog`/`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
5. 更新 `triage.yaml` 行；`check_suite.py --latest` rc=0。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`（最小，time/clock/hrtimer）、`components/linux/changelog.md`、`tests/unit/linux/suite/**`、`tools/linux/suite/**`（仅必要）、本任务书。不改 `Makefile`/`spec/`/`.tao/contracts/`/其它组件。
3. 时间口径按 `ADR-0058`；期望值以 `contract-syscall` 与 Linux clock 语义为准；DADAO 64 KiB 页/大端口径按 `MEMORY.md`。
4. 组件补丁经 `make_patch.py linux` 重导；不改版本号；术语「bank = 寄存器组」。
5. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。
6. 停摆类证据必须含「宿主无进展」判定方法与时间窗，不得只写「超时」。

## 待裁定

**2026-11-25 复评结论（无需裁定，仅记录口径订正）**：本任务按「先复评、不写修复」执行，结论为**不复现**（详见完成区），任务作废。标题后缀采用「已不复现；归因待定」而非派单时预写的「已被 m18-linux-024 修复」：实测时间线显示 022 合入后 11-25 05:59 的首个样本已不再停摆（改为快速 `SIGSEGV rc=139`）、024 合入后残余 `va=0x208` 窗口不再出现，**时间的先后一致，但样本不足以归因 ⇒ 归因待定**；5/5 PASS 是 022/023/024 叠加的结果，不宜只归给 024。若主会话要求沿用派单措辞，改回即可，完成区结论不变。

## 完成区

**测试结果**：运行期证据目录 `run.sh` 全量 **47/47 检查 PASS、`RESULT: PASS` rc=0（flake 0）**；`run_suite.py --only timers-nanosleep` **5/5 PASS**（均第 1/3 次即绿，`m18-linux-024` 族 flake **0** 次、无重试掩盖；每轮 `PASS timers-nanosleep rc=0 status=exit`、`stop_reason=guest-done`、`Totals pass:4 fail:0 skip:8 error:0`、`ok` 12/12、`not ok` 0）；契约探针 **10/10**；`--inject` 负控 **12/12 PASS**（rc=0）。

**修改文件**：仅本任务书。运行期证据目录内 `run.sh`、`check_round.py`、`probe/{p_timers_contract.c,run_probe.py,initramfs-probe.cpio,console.log}`、`prefix/`（4 份历史署名件）、`logs/`（`run-full.log`、5 轮、各门控、`run-inject.log`，含 2 份失败尝试留档 `*-attempt{1,2}.log`）。**无内核/QEMU/spec/契约/Makefile/版本号改动**。

**验收结果**（逐条）：
1. **不复现 ⇒ A 判定（任务作废）**。修前署名：`prefix/console-timers-stall.log`（11-22 跑，末行 `1..12`，其后仅宿主 `terminating on signal 15`）、`prefix/results-20261122T192445.json`（`stop_reason=idle`、`qemu_rc=124`、`host_timeout=660`、`idle_timeout=120`、case `HOST_TIMEOUT/not-finished`）、`prefix/m18-linux-005-evidence.out`（两行 `timers-nanosleep=HOST_TIMEOUT`）、`triage.yaml` 旧行（`git log -S` 命中 005 加/015 删两提交）。时间线：11-22（022 前）该用例 **17 次 `HOST_TIMEOUT`**（其中 14 次含新版 boot 记录：`stop_reason=idle` + `qemu_rc=124`，另 3 次为旧版 results 无 boot 字段；同批另有 2 次 `MISSING` 未归因、不计）；11-25 05:59（022 已合、023/024 未合）首个样本**不停摆**，改 `SIGSEGV rc=139`（`stop_reason=guest-done`）；024 合入后 15:26 起该用例累计 **27 次 PASS**（015 工作树 11 + 本轮 16：热身 1 + 三轮 5 连跑），含本轮最终 5/5。⇒ **时间的先后一致，但样本不足以归因；归因待定**（022 后仅 1 个样本、与末次停摆相隔 274 提交；024 的 13/1000 来自 024 自身任务）；023（QEMU/内核扁平位图配对）同期落地，05:59 的 `SIGSEGV` 单样本未做回退对照、不归给单一补丁。
2. **契约覆盖（`ADR-0058`）**：探针 10 项逐条 PASS（`probe/console.log`）：绝对 sleep REALTIME 迟 3.06 ms / MONOTONIC 迟 9.55 ms（均 ≥ deadline）；相对 100 ms 实测 106.8 ms 无早退；过去 1 s deadline 立即返回 0.31/0.27 ms；零时长 0.21 ms；`EINTR` `rc=4` + signal 1 + `rem=174.6 ms`；REALTIME/MONOTONIC/gettimeofday 同区间 107.2/107.1/107.0 ms（偏差 0.11/0.25 ms）；`/proc/uptime` 与 MONOTONIC 同源前进；内核 clocksource **`dadao_cfx_time`**（`contract-see §3`：1 GHz、1 count = 1 ns）。
3. **可达 FAIL**：本任务无内核修复可回退，验收 3① 不适用（回退 022 属模型级改造，需撤 105 系列中 5 份补丁并重建；单回退 024 只恢复 `va=0x208` 罕见 die——024 已测 13/1000——不是静默停摆）。脚本负控证明断言可失败：① 改坏探针 clocksource 期望 ⇒ `FAIL clocksource_is_cfx_time`、探针 rc≠0，且 guest 已启动、仅此 1 项红；② 把真实 run 的 verdict 改 `FAIL` ⇒ `check_round.py` 判红；两者 `cp`+md5 还原后回绿（`--inject` 12/12）。
4. **不回归**：`check-patch-tree` linux **105/0**（全局 rc=2 仅 musl 段既有 2 problem）；`check-linux-k2` **170/170**、`k5` **285/285**（S44/C41/F40/T34/G29/P35/R62）、`k6` **82/82**（S14/C30/E4/R34）；`check-config-pins`/`check-component-changelog`/`check-knowledge-refs`/`check-tasks`/`check-tests-index` rc=0；`check_suite --latest` **23/23** rc=0、`--patches-only` rc=0；`make check` 与开工基线**逐行 diff 0 行**（rc=2，唯一红 `check-patch-tree` musl 2 problem）；共享 `.config` 复原到 K6 镜像。
5. `timers-nanosleep` 基线与 triage 行（expect=PASS、无行）已由 `m18-linux-015`（`6d451638`）改为交付态并验收；本轮不改这两文件，`check_suite --latest` rc=0 证明台账自洽。
6. 本区 18 行；状态 → `已验证`（按派单 A 判定），标题加「作废」后缀。

**新发现/坑**：① 三段时间线是本类问题的判据：**静默停摆（100%）**与**罕见 die（~1/475）**签名不同、不可互证，但时间的先后一致而样本不足以归因（022 后仅 1 个样本、与末次停摆相隔 274 提交）⇒ 归因待定；② 022-only 期出现 1 次 `SIGSEGV rc=139`（无 die 行、机器未停）——「不再停摆但用例仍红」的中间态要留样本，不能当停摆复现；③ 停摆证据必须落 `stop_reason=idle` + `qemu_rc=124` + `IDLE_TIMEOUT=120`/`host_timeout=660` 三个数字，只写「超时」不可审；④ 契约探针须同时断言「内核 logs 的 clocksource 名」与「三源实测速率」，只测 sleep 时长排除不了另一时基；⑤ K5（285 项）/K6 全量在本机约 9–10 min，排 `run.sh` 按此估时；⑥ **探针不得继承共享 `.config`**：`make linux-defconfig` 后 `CONFIG_DADAO_K6_SHELL=n`，内核在 K4 boundary 就 `SYS_EXIT`（无 `/init`），此时「期望字符串不出现」型负控会**假绿**（本轮 `--inject` 第 1 次即命中：guest 未跑而 clocksource 负控"通过"）。修法＝探针先跑生成器 `make_defconfig.py` 再套 `CONFIG_PINS + K6_SHELL + INITRAMFS` 切片，负控另断言「guest 已启动 + 仅 1 项红」（attempt1 日志保留在 `logs/*-attempt1.log`）；⑦ `check_round.py` 的 kernel-sha 断言只对「刚跑完的 run」成立——后续门控按各自 initramfs 重链 vmlinux，历史 run 的 sha 必然不同，复评/负控调用不要传 vmlinux 参数（本轮 inject 第 1 次因此误报 1 红）。

**遗留问题**：无（任务作废）。022-only 期的 `SIGSEGV` 单样本未归因，若再现同签名另立任务。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：无仓库代码改动（仅本任务书 + 运行期证据脚本）。自审对象＝`run.sh` / `check_round.py` / `probe/*` 的断言是否可失败、结论是否有可达反例。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| S1 flake 判定可能掩盖真实红（凡含 024 签名即重试） | ✅已收敛 | 仅当 `check_round.py` 报告含 `flake-signature` 才重试并单独计数，且打印「第 n/3」；`flakes` 末尾显式输出 | 5 轮均第 1 次即绿，`flakes=0`；`others=0` 断言 |
| S2 5 连跑可能复用旧内核（假绿） | ✅已查 | 轮 1 前删 `kernel-image.json`；断言轮 1 日志有 `make_vmlinux: PASS` 且无 `kernel: unchanged`；`results.kernel.sha256 == sha256(vmlinux)` 每轮校验 | `logs/run-full.log` A/C 段；`check_round.py` kernel 项 |
| S3 探针容差可能掩盖速率错误 | ✅已查 | 速率由 REALTIME/MONOTONIC/gettimeofday **三源交叉**（偏差 0.11/0.25 ms）；`uptime` 50 ms 与「无早退」90 ms 容差按 10 ms tick 粒度取值 | `probe/console.log` 各项量值 |
| S4 `make check` 基线可能被我改动污染 | ✅已查 | 基线在开工未改树时落盘，最终树仅本任务书；两侧按首条 `make: ***` 截断后 `diff` | `logs/make-check.diff` **0 行**；两侧 rc=2 |
| S5 标题归因与派单措辞不一致（派单写「已被 024 修复」） | ✅已查（记录） | 标题按实测写 022/024，并在「待裁定」段写明时间线与偏差理由，不改结论 | 上述时间线三样本 |
| S6 探针继承共享 `.config` ⇒ 负控假绿（第 1 次 `--inject` 命中：guest 未跑、clocksource 负控"通过"） | ✅已修 | `run_probe.py` 先跑 `make_defconfig.py` 再套 `CONFIG_PINS + K6_SHELL + INITRAMFS` 切片；负控加「`PROBE START` 出现 + 仅 1 项红 + `PROBE RESULT: FAIL (1 check(s) failed)`」 | 修前日志 `logs/inject-probe-attempt1.log`（K4 boundary、无 guest）；修后 `--inject` 12/12 PASS、mutated 9 项绿 1 项红、restored 10/10 |
| S7 `check_round.py` 的 kernel-sha 对历史 run 误报（门控已按别的 initramfs 重链） | ✅已修 | `--inject` 的两个调用去掉 vmlinux 参数（kernel 身份仍在 5 连跑段每轮校验） | `--inject` 第 1 次 `kernel-sha-mismatch` → 修后 `control: clean` |

**判决**：无未修 finding。证据链：修前署名（三源）→ 5/5 PASS（看门狗 armed）→ 契约 10/10 → 静态/门控全绿 → 负控可红可回绿（12/12）。按派单 A 判定置 `已验证`。

### 第 1 轮 reviewer 验收

**重跑**（均在仓库根执行运行期证据目录内的 `run.sh`；判决只依我的输出）
1. 全量 `run.sh` 第 1 次：`[INFO] checks=47 failed=0 flakes=0` + `RESULT: PASS`；第 2 次重跑取真退出码：**`RC=0`**，同样 `checks=47 failed=0 flakes=0`、`RESULT: PASS`。
2. **5 连跑**（两轮各 5 次，共 10 次）：`round 1–5 第 1/3 次: clean PASS`、`five consecutive PASS expected=5 actual=5`、`no non-flake failure=0`、`m18-linux-024 flakes counted apart: 0`；我另独立解析 5 份 `results.json`+console：`verdict=PASS rc=0 status=exit`、`stop=guest-done qemu_rc=0`、`1..12` / `ok=12 not ok=0`、`Totals: pass:4 fail:0 skip:8 error:0`，flake 签名 0。强制重建：脚本 C 段 `rm -f kernel-image.json`，`round1 make_vmlinux: PASS=1`、`kernel: unchanged=0`。
3. **探针**（我两轮各跑一次）：`PROBE SUMMARY: 10/10 passed`、`PROBE RESULT: PASS (0 check(s) failed)`、`clocksource: Switched to clocksource dadao_cfx_time`；抽 2 项量值核对：`abs_realtime after_ns=2540410898 ≥ target_ns=2537334300`（迟 3.08 ms ≥ 0）、`eintr rc=4 signals=1 rem_ns=173535861`（0 < rem ≤ 200 ms）；另 `rel_no_early=106.83 ms ≥ 90 ms`、`past_abs=0.31/0.28 ms < 500 ms`、三源 `|dr-dm|=72 µs`、`|dg-dm|=192 µs`。
4. **负控 `run.sh --inject`**：**`RC=0`**，12/12 PASS；变异探针 `PROBE START` 出现且仅 `FAIL clocksource_is_cfx_time` 一项、`PROBE RESULT: FAIL (1 check(s) failed)`；`cp`+md5 还原后 `PROBE SUMMARY: 10/10`、`PROBE RESULT: PASS`。
5. **我的独立注入**（不经脚本内注入）：`cp`+md5 备份真实 run 的 `results.json` → verdict 改 `FAIL` → `check_round.py` 输出 `verdict[FAIL rc=1 status=exit]` **rc=1** → `cp` 还原、md5 `840f513740595127418388cd7e578c38` 相等 → `clean` **rc=0**。

**归因（我独立点数）**：套件运行记录中 `timers-nanosleep` —— 11-22 = **17 次 `HOST_TIMEOUT`**（14 条带 `stop_reason=idle`+`qemu_rc=124`，3 条旧版无 boot 字段）+ 2 次 `MISSING`；11-23/24 **零样本**；022 合入（11-25 04:21:07）后唯一样本 05:59 = `SUITE CASE END timers-nanosleep rc=139 status=signal`、`guest-done`、无 `va=0x208`/die 行（不再停摆但用例仍红）；024 合入（15:18:44）后 15:26 起 **27 次 PASS**（015 树 11 + 本树 16，逐条吻合，不含本轮 10 次）。
⇒ **「已不复现」有据**（我两轮 5/5）；**「静默停摆由 022 消除、残余窗口由 024 消除」证据不足 ⇒ 归因降级为「归因待定」**：022-only 窗口仅 1 个样本、无回退对照，末次停摆样本与 022 之间相隔 **274 个提交**（含 `m18-qemu-001`、`m18-linux-011/012`），024 的 `va=0x208` 窗口数据来自 024 任务自身（13/1000）而非本任务实测。**不影响作废结论**（作废依据＝不复现）。

**约束核验**：分支仅 1 个提交 `122a0318`（`git log master..HEAD`），`git show --stat` 与 `git diff <merge-base>..HEAD` 均**仅本任务书 `+32/−9`**（审查开始时 `git diff master..HEAD` 亦仅本任务书；期间 master 被并行会话推进，故以 merge-base 口径复核）；无内核/QEMU/spec/契约/`Makefile`/`suite.yaml`/`triage.yaml` 改动；`git status` 干净；状态 `已验证`、标题含「作废」；完成区 18 行 ≤30；任务书无具体运行期/宿主绝对路径；`suite.yaml` 的 `expect: PASS`+`stall: true` 与 `triage.yaml` 无行均系 `m18-linux-015`（`6d451638`/`96b5bcd2`）所改，本轮未动。
**门控（我重跑，rc 均为 0）**：`check-knowledge-refs`、`check-tasks`、`check-tests-index`、`check-config-pins`、`check-component-changelog`、`check_suite.py --latest`（23/23）与 `--patches-only`；`check-patch-tree` linux **105/0**（全局 rc=2 仅 musl 2 problem，与开工基线同）；`check-linux-k2` 170/170、`check-linux-k5` 285/285、`check-linux-k6` 82/82；`make check` rc=2 且与基线 `diff` **0 行**。

**判决**：**Accepted**（工程师达标；作废结论成立）。finding（非阻断、文档级）：标题与「待裁定」段把停摆消除归给 022/024，按上文降级为**归因待定**，由 architect 收尾订正措辞即可，不需返工。
