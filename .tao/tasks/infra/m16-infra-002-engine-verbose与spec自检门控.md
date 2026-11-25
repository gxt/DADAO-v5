# m16-infra-002: `chipyard_engine` 可选 `+verbose` + spec 自检门控

**模块**：infra
**项目里程碑**：M16
**依赖**：无（`m16-chipyard-018`/`m18-spec-005` 已合入）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景

- `ISS-529`：`chipyard_engine` 默认不传 `+verbose`，`ptw_walk`/`ptw_tlb` 的日志事件读不到；当前以记录面为判据（已覆盖验收）。
- `ISS-m16-002`：spec 措辞改动连续两次打断 `tests/arch` 自检（`power_vast.py` 用 `### 3.9` 当边界、`check_cfx15.py` 两处文案断言），根因是 spec 任务收尾没跑下游解析器自检。

## 要做

1. **引擎选项**：`tools/testcases/arch` 的 `chipyard_engine` 增加可选 `verbose` 参数（默认关闭，行为不变），把 `+verbose` 传给 sim；`ptw_walk`/`ptw_tlb` 可选择启用并按日志断言（至少提供开关，不改现有判据）。
2. **spec 自检门控**：在 spec/契约任务的收尾检查清单或 `Makefile` 门控中，加入 `python3 tests/arch/run_arch.py --self-test`（或等效的"下游解析器自检"目标），并在 `docs/Process-0x`/任务书模板中写明。
3. **不回归**：现有 `run_arch --self-test` 12 PASS；PTW/PTW-TLB 记录面判据不变。

## 不做

- 不修 `power_vast.py`/`check_cfx15.py`（已由 024/025 修复）；
- 不改 spec 正文。

## 约束

- 独立 `git worktree`；**不提交 git**；变更集限 `tools/testcases/arch/**`、`Makefile`、`docs/Process-0x`、本任务书；不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. `chipyard_engine` 默认不带 `+verbose`、显式开启后 sim 收到该 plusarg（用日志/命令行证据）；
2. 新门控目标可独立运行并 rc=0；故意破坏一个解析器断言 ⇒ 该门控红（可达 FAIL）；
3. `check-tasks`、`check-knowledge-refs`、`run_arch --self-test` 记录 rc。

## 完成区

**测试结果**：通过 33/33（运行期证据目录内的 `run.sh` 一次跑完：33 项 PASS、0 项 FAIL）；失败原因：无。

**修改文件**：
- `tools/testcases/lib/chipyard_engine.py`（任务书写 `tools/testcases/arch`，全仓唯一的 `chipyard_engine` 实际在 `lib/`，此处披露路径偏差）
- `Makefile`：新目标 `check-arch-self-test`（+`.PHONY` / `help` / 并入 L1 `_locked-check` 依赖）
- `docs/Process-07-门控分层规范.md`：§1.1 登记（L1）+ §2 触发点一行
- `docs/Process-06-spec目录保护规范.md`：§10 一行要求
- 本任务书；运行期证据目录内的 `run.sh` / `engine_checks.py`（不入库）

**验收结果**：
1. 默认行为不变：stub 仿真器回读 argv，默认命令 == 文档化 7 项（`+permissive` … `+permissive-off none`），无 `+verbose`；`obs["verbose"] is False`。
2. 开关生效：`run(verbose=True)` / `evaluate(verbose=True)` / `DADAO_CHIPYARD_VERBOSE=1` 时 sim argv 含 `+verbose`，index=2（`+permissive` 之后、`+permissive-off` 之前）；`DADAO_CHIPYARD_VERBOSE=0` 时不出现。
3. `make help` 列出 `check-arch-self-test`（rc=0）；`make check-arch-self-test` 独立 rc=0，尾部 `self-test: PASS` / `check-arch-self-test: PASS (downstream arch parsers)`。
4. 可达 FAIL：把 `tests/arch/hart/check_cfx15.py` 的 `cfx_hart_async_prev_run_mode` 期望 rc 0→1 ⇒ 门控 rc≠0（`self-test: FAIL（1 项）`、`check-arch-self-test: FAIL`）；`cp` 还原后 md5 `f068ef58…` 一致、该文件 `git diff` 为空 ⇒ 门控 rc=0 回绿。
5. 不回归：`run_arch --self-test` rc=0（20 PASS / 0 FAIL，现场统计）；`check-tasks` rc=0；`check-knowledge-refs` rc=1 但输出与 HEAD 基线 `diff` 逐行相同（唯一悬空 `milestones-m17.md:36` 的 `ADR-0063`，未动）。
6. PTW 记录面不变：`check_ptw_walk --self-test` rc=0（19 条断言全可达 FAIL）、`check_ptw_tlb --self-test` rc=0（27 条）；`git status -- tests/arch` 0 行改动。

**新发现/坑**：① `+verbose` 位置受 harness 约束（`+permissive` 之后、`+permissive-off` 之前，`m16-gem5-005` finding ③）；② 新门控读安装根工具链：worktree 未按惯例把共享构建树/安装根软链到主树时，`check_hart`/`check_pmem_dma` 的 `--selfcheck` 会因缺 `llvm-mc` 红（本次先按惯例软链再跑，软链属运行期不入库）；③ 注入后必须验 `git diff --name-only -- <file>` 非空（防空注入），还原一律 `cp`+md5；④ `make` 对 recipe 失败的退出码是 2（不是子命令的 1），证据按"非零"判；⑤ 真实 RTL trace 未纳入证据：实测期间共享构建树的 `WumingTinyConfig` 正被其它会话重建（取二进制时已消失），且 `ptw_walk`/`ptw_tlb` 全镜像为分钟级——证据以「仿真进程实际收到的 argv」为准（任务口径「命令行证据」）。
**遗留问题**：无（`check-knowledge-refs` 的 `ADR-0063` 悬空为本任务基线红，非本任务引入，未改）。

## 审阅记录

### 第 1 轮 reviewer 验收（2026-11-25，小改；独立重跑，未提交）

**判决**：Accepted —— 下列各项均为本人现场重跑的真实输出/退出码；命令一律在 worktree 内用相对路径执行，未采信完成区转述。

1. **verbose**：仓库根执行「运行期证据目录内的 `run.sh`」⇒ `33 PASS / 0 FAIL`、`rc=0`；stub 仿真器回读**真实 argv**：默认命令 == 文档化 7 项且无 `+verbose`（`obs.verbose=False`）、`run(verbose=True)` 时 `+verbose` index=2（`+permissive` 后、`+permissive-off` 前）、`DADAO_CHIPYARD_VERBOSE=1` 有 / `=0` 消失、`evaluate(verbose=…)` 双向透传；`git ls-files '*chipyard_engine*'` 全仓仅 1 个（在 `tools/testcases/lib/`），路径偏差已在完成区披露。
2. **独立注入被测产物**（不走脚本内置分支）：`cp` 备份 md5 `b97cba80…` → 把 `verbose_requested` 的 `if verbose:` 改成 `if True:` ⇒ 同一 `run.sh` `rc=1`、7 项 FAIL；`cp` 还原 md5 一致 ⇒ 重跑回 `33/33 rc=0`，注入残留 grep 为空。
3. **门控**：`make help` 列出该目标（rc=0）；`make check-arch-self-test` 独立 `rc=0`、实测 29.8 s、尾行 `self-test: PASS` / `check-arch-self-test: PASS`；并入 L1 = `Makefile` 中 `_locked-check` 前置（+`.PHONY` + help），按 `Process-07 §3` 判据 1（不启模拟器、不跑被测语义）归 L1，全仓无第二个 `run_arch --self-test` 调用点。
4. **可达 FAIL（我自己的注入）**：`cp`+md5 备份 `tests/arch/power/power_vast.py`（`0f479cb9…`）→ 改坏 `§3.8` 起点串 ⇒ 门控 `rc=2`、`self-test: FAIL（1 项）`、`check-arch-self-test: FAIL`；`cp` 还原 md5 相同、`git diff -- tests/arch` 为空 ⇒ 回 `rc=0`（防空注入：注入后 `git diff --name-only` 非空已核）。
5. **不回归**：`run_arch --self-test` `rc=0`、现场计数 `20 PASS / 0 FAIL`；`check-tasks` `rc=0`；`check-knowledge-refs` 工作树与 `git archive HEAD` 基线两侧均 `rc=1` 且输出 `diff` 逐行相同（唯一悬空 `milestones-m17.md:36 ADR-0063`，未动）；`check_ptw_walk --self-test` `rc=0`（19 条断言）、`check_ptw_tlb --self-test` `rc=0`（27 条）；`git status -- tests/arch` 0 行。
6. **12 → 20 的差异来源**：任务书「12 PASS」是 ISS-529 登记期（`3d87cb55` = m16-chipyard-018）的口径，当时 = 5 条固定 + 3 个 `expected.yaml` + 4 个 driver = 12；其后 5 次合入把两者增到 7 / 8 ⇒ 20（`run_arch.py` 自检结构未变，7 类打印点逐条核过）。本任务 `git diff -- tests/arch` 为空 ⇒ 属基线数字过时，非回归。
7. **文档**：`Process-07 §1.1` 登记行（L1 + 机械判据）与 `§2` 触发点一行、`Process-06 §10`（MUST，编号紧接 §9）均与实际一致；任务书 grep 无 `.work`/`/tmp`/家目录等运行期路径。
8. **快照对账**：验收前后 `git status --porcelain -uall` 同为 5 行、4 个交付文件 md5 全同（本审阅记录写入前测得），与完成区「修改文件」逐行一致；`git diff --name-only` 仅该 5 文件。

**Finding（非阻断，交 architect 收尾）**：F-a 任务书「现有 `run_arch --self-test` 12 PASS」已过时（现场 20，`run.sh` 下限仍写 12），属文档级数字口径；F-b `make check` 在 `check-patch-tree` 即红（17 problem，共享组件源树被并发会话改脏），与本任务变更集无关（未触 `components/`/`manifests/`），故本轮未观察到 `check-arch-self-test` 在整条 L1 内的端到端执行，成员关系以 Makefile 前置行为准。

### 第 1 轮 engineer 自审（2026-11-25，自主逐行审查）

**判决**：可交验收；4 个交付文件逐行读过，1 条路径偏差显式披露，0 条未修 finding。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 证据脚本把 `argv[0]`（stub 路径）算进 sim argv，误报 FAIL | ✅已修 | `engine_checks.py` 改比 `obs["cmd"][1:]` | 重跑 engine 检查 0 failure |
| F2 `run.sh` 有未使用的 `found` 变量 | ✅已修 | 删除该判断，直接用 `grep -cF` | `bash run.sh` 33/33 PASS |
| F3 `evaluate` docstring 未提 `verbose` | ✅已修 | 补一行说明 | `py_compile` rc=0；`evaluate(verbose=True)` 的 cmd 含 `+verbose` |
| F4 任务书写的 `tools/testcases/arch` 与实体路径不符 | ❌不修（披露） | 改的是全仓唯一 `tools/testcases/lib/chipyard_engine.py` | `git ls-files '*chipyard_engine.py'` 仅 1 个 |
| F5 门控是否该入 L1 | ✅确认 | 不启动模拟器、只解析 + 驱动自检 ⇒ Process-07 §3 判据 1 | `make -p` 中 `_locked-check` 第 26 项；`check-arch-self-test` 仅 1 处定义 |
| F6 「默认行为不变」是否真证到 | ✅确认 | golden 命令 + stub 回读 argv 双路 | default 无 `+verbose`、命令与文档逐项相等 |
| F7 注入是否「空注入」 | ✅确认 | 断言注入后 `git diff --name-only -- <file>` 非空 | 注入门控红、还原 md5 一致、回绿 |
