# m12-chipyard-017: 引擎 parity 报告生成器入仓（可复现）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-016`（已合 `3924a248`）
**可并行分片**：否
**预估**：1–1.5 h
**状态**：待开始

## 背景（AGENTS 硬规则缺口）

`m12-chipyard-016` 把**报告产物**入库（`.tao/knowledge/refs/m12-016-embench-picolibc.{json,md}`），但**生成器没入库**：`make_report.py` / `pending.py` / `collect.sh` / `run.sh` 只存在于运行期证据目录（`.work/evidence/m12-chipyard-016/`）。

违反 AGENTS「生成器/脚本随产物保留：凡产出**被提交（入 git）**的生成器/脚本，必须随产物留**非易失位置**（优先 `tools/<module>/`）」⇒ 现在 fresh clone 上**无法复现**已提交的报告，`m12-integ-002` 的「证据可复跑」判据也就落不了地。

## 范围

1. **搬家不改逻辑**：把四个脚本落到 `tools/testcases/parity/`（与 `fp_diff.py` 同族，具备 `--check` 可复现约定的目录），保持文件名语义：
   - `make_report.py` → `tools/testcases/parity/engine_parity_report.py`
   - `pending.py` → `tools/testcases/parity/engine_parity_pending.py`
   - `collect.sh` → `tools/testcases/parity/engine_parity_collect.sh`
   - `run.sh` → `tools/testcases/parity/engine_parity_run.sh`
2. **接口去运行期耦合**：默认输入目录从「脚本自身所在的 `../..`」改为 `--repo <根>`（默认 = 该脚本相对仓库根）+ `--log-dir`（默认 `<repo>/.work/log/chipyard`）；节点名保留但可 `--node-map` 覆盖（保持原有默认值，行为不变）。
3. **可复现校核**：`python3 tools/testcases/parity/engine_parity_report.py --check` 在**当前**数据上重生成，与已提交的 `.tao/knowledge/refs/m12-016-embench-picolibc.{json,md}` **逐字节一致**（打印 sha256 对账）；不一致就说明有未入库的输入，必须查清再报。
4. **不重复造轮子**：报告口径（`CRITERION`/`QEMU_BASELINE_GAPS`/union 规则/budget 单列/`cases_seen`）一律**照搬 016**，不得改写判据；只允许改路径解析与入口形态。

## 验收（逐条贴真实 rc/现场值）

1. 四个文件已入 git（`git ls-files` 现场），`grep` 证明运行期证据目录不再是唯一副本；
2. `engine_parity_report.py --check` ⇒ **rc=0**、逐字节一致（贴两个 sha256）；**重跑两次**结果相同（确定性）；
3. `engine_parity_pending.py` 能列出当前 pending（现场值：embench `cases_seen` 与 pending 数）；
4. **1 路可达 FAIL 注入**（`cp`+md5 还原）：把报告里 `parity.differing` 的一条状态改坏 ⇒ `--check` rc≠0 且指出差异位置；
5. `check-knowledge-refs` rc=0（脚本内注释/文档里**不得**出现具体 `.work/**` 路径）；`check-no-residue` rc=0；`check-dirs` rc=0；
6. `python3 tools/infra/check_script_hygiene.py`（若存在该门控）或等价 `py_compile` + `bash -n` 全通过；
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；只在本任务 worktree 内改动。

## 明确的「不做」

- **不动**报告数值与判据（32/38、budget 81 等是数据未收完，属 `m12-integ-002` 前的数据补齐，不归本任务）；
- 不改 `tools/testcases/lib/chipyard_engine.py`、`picolibc_tests.py`、`run_embench_e2e.py`；
- 不重建、不重跑 embench/picolibc 全量（节点上 `-O0` 夜跑仍在进行，**禁抢节点**）；
- 不改 016 的任务书与审阅记录（其「遗留问题」里的旧路径由 `m12-integ-002` 报告指认新位置）。

## 待裁定

（实现中写）

## 审阅记录

（待填）
