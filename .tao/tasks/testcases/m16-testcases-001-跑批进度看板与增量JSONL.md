# m16-testcases-001: 跑批进度看板 + 增量 JSONL（可见性）

**模块**：testcases
**项目里程碑**：M16
**依赖**：无（`run_embench_e2e.py` / `picolibc_tests.py` 均已在仓）
**可并行分片**：否
**预估**：1–1.5 h
**状态**：待开始

## 背景（用户 2026-11-15 直接提出）

> 「我问的不是为什么这么慢，而是为什么看不见中间状态？」

现场三个具体缺陷（都有证据）：

1. **JSON 只在批次末尾写一次**：`run_embench_e2e.py` 的 `write_json()` 在 `run_suite()` **之后**调用 ⇒ 报表与 `engine_parity_pending.py` 读到的永远是**上一批**；跑到一半时"看不见"是结构性的，不是偶然。
2. **主控机看不到节点实时日志**：跑批的逐例完成行（`PASS bench (-O0) cycles=… 秒`，每例 `flush`）只在**节点**的日志里；主控机那份副本长期 0 字节 ⇒ 主会话据此误报过"还要等 6 例"（实际当时已完成 34/38）。
3. **单例内部无进度**：chipyard sim 只在退出时打印 `cycles=`，跑到一半既无周期数也无 ETA；`ics170` 曾有 6 个 picolibc sim 跑满 **11 h 25 m** 却毫无进度可观测。

## 目标

**A. 进度看板（`tools/testcases/tset/embench/progress.py`，共享工具，入仓并登记索引）**

- 输入：`--hosts <csv>`、每节点 `<repo>`、日志名（embench / picolibc 两套自动识别）；
- 解析节点日志的逐例完成行（`status bench (-opt) cycles=… Ns` / picolibc 的 `PASS/FAIL/BLOCKED`），**并从 `ps -eo etime` + `/proc/<pid>/cmdline` 的 `+loadmem=` 识别正在跑的用例**；
- 输出一张表：**已完成（含 cycles 与墙钟）/ 在跑（已跑时长 + 按历史 cycles 估 ETA）/ 未开始**，并给汇总（`done/total`、吞吐 cycles/s）；
- **只读**：不写节点、不 kill、不改仓库。

**B. 增量落盘（改 `run_embench_e2e.py`，加 `--jsonl-out`）**

- 每完成一例**立即追加一行 JSON 并 `flush`**（字段与末尾 JSON 的 `cases[]` 一致 + `ts`）；
- 末尾的 `--json-out` 保持不变（向后兼容）；
- 报表侧（`engine_parity_report.py`）可选读 JSONL 做增量 union —— **若改动会破坏 `--check` 逐字节复现，则本项只加 JSONL、不改报表**（在完成区写明选择）。

**C. 纪律（写进 `docs/Process-07` 或对应跑批文档 1–2 行）**

- 跑批日志**必须定期从节点取回**再报进度；报进度**禁止引用入库报告的旧值**（本任务背景里的误报就是反例）。

## 验收（逐条贴真实 rc/现场值）

1. `progress.py --hosts …` 在**当前**在跑的批次上给出：已完成的例名 + cycles、在跑的例名 + 已跑时长 + ETA 估算、未开始例数；**与节点日志/`ps` 现场逐条对得上**（贴两侧证据）；
2. `--jsonl-out`：跑一个**小用例**（如 `crc32-O2`，禁止动正在跑的批次）验证每完成一例即出现一行、且与最终 JSON 的对应条目一致；
3. **可达 FAIL 注入 ≥2 路**（`cp`+md5 还原）：① 看板把"已完成"少算一例 ⇒ 汇总与日志不符时报红；② JSONL 写入失败（路径不可写）⇒ 非零退出且不静默；
4. `check-knowledge-refs`、`check-no-residue`、`check-dirs`、`check-tools-index`（若已存在）、`py_compile`、`bash -n` 全 rc=0；
5. `tools/testcases/README.md` 按新规则登记（路径/用途/入口/调用者四要素）；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`/`issues.yaml`。

## 硬约束

- **不动正在跑的批次**：`server208` 上 4 个 `-O0` 例、`ics170` 上 6 个 picolibc 例正在跑（100% CPU 各占一核），**禁 kill、禁重建 sim、禁 sync/reset 节点仓库**；
- 只改 `tools/testcases/tset/embench/**`、`tools/testcases/parity/engine_parity_report.py`（**仅当**不破坏 `--check`）、`tools/testcases/README.md`、`docs/Process-07*`、本任务书；
- 禁 `install-host`/`check-modules`/`build-*`；不提交 git；注入还原用 `cp`+md5。

## 待裁定

（实现中写）

## 审阅记录

（待填）
