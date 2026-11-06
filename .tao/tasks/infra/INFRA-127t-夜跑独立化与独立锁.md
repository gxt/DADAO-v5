# INFRA-127t: 夜跑独立化（`night-run` 目标 + 独立锁 + meta 机器信息）

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-126t`（夜跑退出里程碑收口门控；同改 `Makefile`，须先合并）
**状态**：待开始

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
