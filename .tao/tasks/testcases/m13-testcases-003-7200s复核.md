# m13-testcases-003: 3600s 仍超时的例 × 7200s 复核

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-001` + `m13-testcases-002`（取「3600s 仍超时」的名单）
**可并行分片**：否（单机 48 并发跑批；测时间要求进程独占核）
**状态**：待开始

## 用户裁定（原话）

「跑3600s，甚至7200s……不修改源码，不做调试，只记录结果；我来对结果进行分析和裁定。」

## 用户裁定（2026-11-10，本任务执行口径）

- 「207/208，**各自可安排 48 个测试用例**，先把 **static** 全跑，然后再把 **dynamic** 全跑。」
- 同意**追加 120 s 采样**：每例先跑 120 s 后 `SIGINT`，读 gem5 `stats.txt` 的 `simInsts`（**只读自带 stats，不调试、不改源码**），用于区分「挂死 vs 纯计算量」。
- 同意**输出落点改按新规**：人读结论 → `docs/TestReports/`；原始 JSON **不入库**（留运行期证据目录）。
- 安排任务前先查磁盘：主控机 `make check-disk`、节点 `remote.py status` 的 `disk_alert`；**> 90% 报警**。

## 目标

1. 从 001/002 的结果里取「3600s 仍超时」的例（static 72 + dynamic 78），**先 static 全部、再 dynamic 全部**；两节点各 ≤48 并发。
2. 每例先做 **120 s 采样**（`SIGINT` 后读 `simInsts`），再做 **gem5 SE 7200s** 重跑；同例 QEMU 计时。
3. 输出每例：`case` / `simInsts_120s` / `gem5_seconds` / `qemu_seconds` / `ratio` / `klass` / `exit`。
4. 统计：有多少例在 7200s 下转 PASS；结合 `simInsts_120s` 判「挂死（120 s 内已跑海量指令）vs 纯计算量」——**只给数据与观察**。

## 验收标准

1. 名单与 001/002 的「仍超时」集合**逐个对应**（不遗漏、不新增）
2. 输出：人读结论落 `docs/TestReports/M13-长尾7200s.md`；原始 JSON 留运行期证据目录（**不入库**），仅把必要摘要（逐例表 + 三类计数）写进结论册
3. 报告含：逐例表、转 PASS/仍超时/异常三类计数、执行环境指纹
4. **不改** gem5/QEMU/测试资产/用例与期望
5. 采样只用 gem5 自带 `stats.txt`（`--outdir` + `SIGINT`），不引入调试构建
6. 执行前：主控机 `make check-disk` rc=0、两节点 `disk_alert=ok`；否则先报警再处置
5. 完成区 ≤30 行、无运行期路径

## 执行方式

- 两节点并行，各 ≤48 并发；**先 static（72 例）后 dynamic（78 例）**；主会话启动 background
- 预计：static 36/36 单波 ≈ 2 h，dynamic 39/39 单波 ≈ 2 h，合计 **≈ 4 h**（采样另加约 2–3 min/节点）
- 用例名单从 `refs/m13-001-static-3600s-full.json`（blocked 72）与 `refs/m13-002-dynamic-3600s-full.json`（blocked 78）派生，逐个对应、不增不减

## 非范围

- 不做根因分析、不调试、不改源码
