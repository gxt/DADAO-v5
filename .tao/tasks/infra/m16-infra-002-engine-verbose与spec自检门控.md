# m16-infra-002: `chipyard_engine` 可选 `+verbose` + spec 自检门控

**模块**：infra
**项目里程碑**：M16
**依赖**：无（`m16-chipyard-018`/`m18-spec-005` 已合入）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景

- `ISS-529`：`chipyard_engine` 默认不传 `+verbose`，`ptw_walk`/`ptw_tlb` 的日志事件读不到；当前以记录面为判据（已覆盖验收）。
- `ISS-530`：spec 措辞改动连续两次打断 `tests/arch` 自检（`power_vast.py` 用 `### 3.9` 当边界、`check_cfx15.py` 两处文案断言），根因是 spec 任务收尾没跑下游解析器自检。

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

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
