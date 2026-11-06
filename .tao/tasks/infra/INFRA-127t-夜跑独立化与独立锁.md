# INFRA-127t: 夜跑独立化（`night-run` 目标 + 独立锁 + meta 机器信息）

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-126t`（夜跑退出里程碑收口门控；同改 `Makefile`，须先合并）
**状态**：已验证

## 用户裁定（2026-11-06）

> 「夜跑本身，应该做成独立可运行的；现在资源多了，以后还会增加新机器；不能让夜跑成为依赖的节点」
>
> 追问后选：**先做第 2 层**；「**无需保留别名**；报告可以仍然放在原位置；关键是解耦，独立锁」。

## 现状

- 夜跑入口是 `make check-night`，挂在共享 `GATE_LOCKED_TARGETS` 里，与 L1/L2/L3 共用 `.dadao/gate.lock`：夜跑一跑一小时，开发门控全被挡
- 夜跑成员（`check-tset-*-full`、`check-arch`）自身也是 gate-locked ⇒ 即使外层换锁，成员仍会去抢共享锁
- `night_run.py` 的 `meta.json` 只有 `command`/`started_utc`/`finished_utc`/`members`，不记机器、commit、工具链 ⇒ 以后多机结果不可比
- 报告落 `.dadao/tests/night/<本地日期>/`（本次**保持原位置**）

## 目标

1. **改名**：目标 `check-night` → `night-run`，**不保留别名**（`make check-night` 应无此目标）。
2. **独立锁**：夜跑用 `.dadao/night.lock`（`NIGHT_LOCK ?=`），与 `.dadao/gate.lock` 分离：
   - `night-run` 外层由 `night.lock` 串行化；
   - 夜跑成员通过 **`GATE_LOCK=$(NIGHT_LOCK)`** 继承到子 make，借助 `gate_lock.py` 的 ancestor 嵌套检测直接放行 ⇒ **不再触碰共享 `gate.lock`**；
   - `NIGHT_LOCK_WAIT` 可配（默认与 `GATE_LOCK_WAIT` 一致）。
3. **meta 补机器信息**：`meta.json` 增加 `host`（hostname）、`machine_id`（可用 env 覆盖，默认 hostname）、`git_commit`、`toolchain_id`（安装根可执行文件版本/路径摘要）；保持既有字段与报告格式兼容。
4. **可选择性跑成员**：`night-run` 支持 `NIGHT_MEMBERS='scope:suite=cmd'` 传入单个成员（便于自测与以后分片），不传则用默认 4 成员。
5. **文档同步**：所有活文档里的 `make check-night` 改为 `make night-run`（`Makefile` 帮助/注释、`docs/Process-07`、`docs/Process-09`、`README.md`、`tools/testcases/parity/README.md`、`docs/DDLN` 如命中）；说明「夜跑=观测、独立锁、不阻断门控」。
6. `check-night-report` 保持原样（按需诊断）。

## 范围 / 非范围

**在范围内**：`Makefile`、`tools/testcases/night_run.py`（meta 字段 + `--machine` 可选）、`tools/testcases/check_night_report.py`（仅报告字段兼容说明，如需要）、`docs/Process-07`、`docs/Process-09`、`README.md`、`tools/testcases/parity/README.md`、`docs/DDLN/**` 命中处、本任务书、`milestones.md`。

**不在范围**：多机分片清单/汇总器、报告根外置、`check-night-report` 判据、夜跑成员集合与用例期望、QEMU/gem5/LLVM。

## 验收标准

1. `make -n night-run` 可解析并含 `night_run.py`；`make check-night` **不再是目标**（`make -n check-night` 返回非零）。
2. 独立锁可证：跑一个快成员（如 `NIGHT_MEMBERS='tset:embench=make check-tset-embench-smoke'`）时，`DADAO_GATE_LOCK_VERBOSE=1` 显示锁路径为 `night.lock`；**不出现** `gate.lock`；运行期间另起一个 gate-locked 目标不被阻塞（或 `gate.lock` 的持有者不是夜跑）。
3. `meta.json` 含 `host`/`machine_id`/`git_commit`/`toolchain_id`，旧字段仍在；`check-night-report --self-test` rc=0。
4. 活文档 `make check-night` 命中数 = 0（`grep` 现场统计，排除归档/任务书/discussing）。
5. `make check`（L1）rc=0；`make check-milestone` 不再依赖夜跑（`INFRA-126t` 已做，复核）。
6. 反例：把 `night-run` 改回共享 `GATE_LOCK` ⇒ 你的「锁路径 = night.lock」断言 FAIL；`cp`+`md5sum -c` 还原回绿（禁 git 还原）。
7. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 独立锁的语义：夜跑只**读**构建产物、写自己的报告目录；不与构建/其它门控互斥。同工作树并发构建时可能读瞬态产物，属已知取舍；多机/专用 checkout 是后续分层。
- 不保留 `check-night` 别名是用户明确要求；改完后任何旧脚本调用都会显式失败，正好暴露待迁移处。

## 完成区

**测试结果**：运行期证据脚本 14/14 PASS、rc=0（含注入）；`make check`（L1）rc=0；`night_run --self-test` 6/6；`check-night-report --self-test` 8/8。
**修改文件**：`Makefile`、`tools/testcases/night_run.py`、`tools/testcases/check_night_report.py`（仅提示语/自测 fixture 文案）、`docs/Process-07`、`docs/Process-09`、`README.md`、`tests/README.md`、`tests/INVENTORY.md`、`docs/DDLN/F-{001,005,007}`、本任务书、`milestones.md`。
**验收结果**：
- `make -n night-run` rc=0 且含 `night_run.py`；`make -n check-night` rc=2（No rule，无别名）。
- 快成员实跑：`night.lock` holder `target=night-run`；成员日志 `nested: .../night.lock`；日志中 `gate.lock` 命中 0；期间 `make -n check-inst-smoke` rc=0、约 1.1 s（未被阻塞）。
- `meta.json` 旧字段 + `host`/`machine_id`/`git_commit`/`toolchain_id` 齐全；`NIGHT_MACHINE_ID=node-42` 覆盖生效；报告目录布局未变。
- 活文档 `make check-night` 命中数现场统计 = 0；F1 `tests/README.md`「里程碑层」改按需诊断，F2 DD-F001/005/007 的「夜跑次日由里程碑消费」改观测/按需。
- 反例：外层改回共享 `GATE_LOCK` ⇒「night.lock 属 night-run」断言 FAIL（`gate.lock` holder=night-run）；`cp`+`md5sum -c` 还原后 14/14 回绿（未用 git 还原）。
**新发现/坑**：任务 worktree 的 `.dadao`/`.work` 是共享软链，锁/报告按逻辑工作树路径解析；证据脚本判「无 gate.lock」须 `grep -F`（`gate_lock.py`/`gate-lock:` 会被 `.` 正则误命中）。
**遗留问题**：无。

## 审阅记录

### 第 1 轮 engineer 自审
- `Makefile`：`night-run` 不在 `GATE_LOCKED_TARGETS`；外层持 `NIGHT_LOCK`，子 make 显式 `GATE_LOCK=$(NIGHT_LOCK)`，recipe 再导出同名环境变量，成员经 ancestor 嵌套放行——实跑日志已证。
- `night_run.py`：新字段均来自真实来源（hostname / env+`--machine` / `git rev-parse` / 安装根 build-id）；工具缺失记 `absent`，不伪造；旧字段与目录布局未动。
- 证据脚本发现 1：`grep "gate.lock"` 被 `gate_lock.py`/`gate-lock:` 误命中 ⇒ 改 `grep -F`，复验 0 命中。
- 证据脚本发现 2：`set -u` 下 `local ... dir="$TMP/$label"` 顺序展开报 unbound ⇒ 拆行赋值，复验 14/14。
- 说明：控制台前缀与成员日志文件名保留 `check-night-*`，为满足「报告目录布局不变」；目标名已无别名。
- 判决：无未修 finding；状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录（reviewer 亲自执行，workdir=任务 worktree）**
- `make -n night-run` rc=0，含 `gate_lock.py run --lock "<wt>/.dadao/night.lock" … GATE_LOCK=<night.lock> _locked-night-run`；`make -n check-night` rc=2（`No rule to make target`）。`.PHONY`(L71)/help(L218)/注释均已 `night-run`；`GATE_LOCKED_TARGETS` 与 `_locked-check-night` 无残留。
- 快成员实跑（`NIGHT_MEMBERS='…embench=make -n …&& sleep 15'`，`DADAO_GATE_LOCK_VERBOSE=1`）：`night.lock` holder `target=night-run`；成员日志 `gate-lock: nested: …/.dadao/night.lock already held by an ancestor (… target=night-run)`；合并日志 `gate.lock` 字面命中 **0**；夜跑期间 `gate.lock` 无 holder；并发 `GATE_LOCK_FAILFAST=1 make -n check-inst-smoke` **rc=0 / 985ms**（脚本内 996ms、1029ms）。
- `meta.json`：旧字段 `command/started_utc/finished_utc/members` 在 + `host`、`machine_id`、`git_commit=28a09a78…`、`toolchain_id=clang=build-id:…;ld.lld=build-id:…`；优先级实测 `--machine` > `NIGHT_MACHINE_ID` > hostname ✓。
- `night_run.py --self-test` **rc=0（6/6）**；`check_night_report.py --self-test` **rc=0（8/8）**。
- 活文件 `make check-night` 目标引用 **命中 0**（排除台账/运行期目录）；剩余 `check-night` 均为 `check-night-report` 或 night_run 控制台前缀（见 F3）。
- `make -n check-milestone | grep night` **命中 0**（INFRA-126t 不回归）；`check-milestone:` 依赖含 `check-l3-report` ⇒ L3 仍是收口门控。
- `check_night_report.py` vs HEAD：4 处纯字符串（3 提示语 + 1 self-test fixture `command`），**判据/断言逻辑零改动**。
- 证据脚本重跑：首跑 **14/14 PASS rc=0**；reviewer 独立注入（外层 `--lock "$(NIGHT_LOCK)"→"$(GATE_LOCK)"`，`cp`+md5 备份）后重跑同一脚本 **rc=1（10/14，4 FAIL：night.lock 无 holder / nested 缺失 / probe rc=2）**；`cp`+`md5sum -c` 还原（md5 `33b510db…` 与注入前一致，未用 git 还原）后断言回绿 `night.lock holder=night-run`。

**约束核验**：改名无别名 ✓；独立锁且成员不碰 `gate.lock` ✓；meta 四字段 + 旧字段 + 报告布局未变 ✓；文档口径（夜跑=观测/独立锁/不阻断，L3 收口）一致 ✓；完成区 12 行 ≤30、无绝对运行期路径 ✓；修改文件 13 项与 `git status` 逐项一致、越界 0 ✓。

**finding（均非阻断）**：
- F1（环境）：`make check` 我方 rc=0 ×2、rc=2 ×2，红项恒为 `check-run-artifacts` 报并发任务在共享运行期日志目录留下的非法命名文件（归 TESTCASES-102t 收尾清理）；本任务 diff 未触及该门控、非其产物 ⇒ 判环境干扰，有据重试 2 次根因持续，交 architect 令该任务收尾清理。
- F2（文档）：`tests/README`/`INVENTORY` 把 `check-night-report 由 check-milestone 消费` 改为「按需诊断」，是 INFRA-126t 口径同步而非"仅文案"；方向一致、无判据变化（披露措辞欠精确）。
- F3（说明）：night_run 控制台前缀与成员日志名仍为 `check-night-*`（engineer 已披露，为保报告布局/日志指针兼容）。

**判决：Accepted**（验收项 1–8 全部在 reviewer 重跑下通过；唯一 rc≠0 的 `make check` 已定位为并发任务残留、与交付物无因果）。

#### 收尾（architect，2026-11-06）

- F1：`check-run-artifacts` 红由并发任务在共享日志目录产生的非法命名文件导致，归 `TESTCASES-102t` 收尾清理；非本任务交付物。
- F2：`tests/README`/`INVENTORY` 的改动属 `INFRA-126t` 口径同步，方向一致、无判据变化。
- F3：`night_run` 控制台前缀/成员日志名保留 `check-night-*` 以兼容报告布局与日志指针；目标层面无别名。
- 判决 Accepted，状态置 `已验证`。
