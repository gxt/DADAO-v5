# m13-testcases-040: 资产/文档残留收口（4 条 `.S` 未入索引、`mem_sweep` 悬挂、trampoline 文档残留）

**模块**：testcases
**项目里程碑**：M13
**依赖**：无（`m13-testcases-030` 已合入；`m13-integ-002` 已合入并点名这些问题）
**可并行分片**：否（同一批清单/文档）
**预估**：1–2 h
**状态**：待开始

## 背景（三处均由 reviewer 在已完成任务里查出，未当场改）

1. **4 条 `.S` 载体未进索引**（`m13-integ-002` 报告 §1 列为 `not_indexed`）：`ldm.o_rrri_rf`、`ldm.t_rrri_rf`、`stm.o_rrri_rf`、`stm.t_rrri_rf` —— 文件在 `tests/inst/01-load-store/` 且有 `check-inst-asm` 覆盖，但 `tests/inst.yaml` 无条目。
2. **`tools/chipyard/mem_sweep.py` 的 `SOURCES` 仍指已删三册 YAML**（`m13-testcases-030` 的 `ISS-441`）：实跑 `mem_sweep.py list` ⇒ `rc=1 FileNotFoundError`（响亮失败，不在门控里，暂未伤人）。
3. **trampoline 文档残留**（`030`/`036` 收尾项）：`tests/INVENTORY.md`、`docs/Process-09 §7` 仍把 `gen_trampoline`/`trampoline.bin` 当现状描述，而资产已删。

## 目标

1. `tests/inst.yaml` 补 4 条（`id/file/platforms/level/requires` 与同册其它条目同构）；`check_case_ledger --write` 重生成；`check-tests-index` 与 `validate-vectors` 仍绿。
2. `mem_sweep.py`：`SOURCES` 改为**从 `.S` 派生**（复用 `run_asm_suite.scan_source` 或等价，**不要新写第二套扫描**）；若判断该工具已无用途 ⇒ 走「退役」路线（`git rm` + 检查无 Makefile/门控引用），二选一并在完成区写清理由。改后 `mem_sweep.py list` 必须 rc=0 且输出非空（或工具已被删除、`grep` 无引用）。
3. `tests/INVENTORY.md`、`docs/Process-09 §7`：把 `gen_trampoline`/`trampoline.bin`/`--trampoline` 的描述改成「已于 M13 退役，改用 64 KiB 固定固件 `bootrom/tiny/bootrom_tiny.bin`」；`grep -rn "gen_trampoline\|--trampoline"` 在 `docs/`、`tests/` 只允许出现在历史归档或"已退役"说明里。

## 验收（逐条贴真实 rc）

1. `tests/inst.yaml` 从 486 → **490** 条（现场核）；`check-tests-index` rc=0；`check-case-ledger` rc=0（条数现场值）。
2. `validate-vectors` rc=0、`check-inst-asm` **264 id / 897 镜像**不变（补索引不改载体）。
3. `mem_sweep.py` 二选一的证据：派生路线 ⇒ `list` rc=0 且条数非零；退役路线 ⇒ `git rm` + `grep -rn mem_sweep` 只余归档/说明。
4. 文档残留：`grep -rn "gen_trampoline"` 在 `docs/`、`tests/`、`tools/` 0 命中（归档除外）；`INVENTORY.md` 与 `Process-09 §7` 改后语义与 `030`/`036` 一致。
5. 273 例 `sweep_expect.bin` md5 `2d4d94651346ef673c5a855e024c1489` 不变；`check-knowledge-refs`/`check-run-artifacts`/`check-no-residue` rc=0。
6. ≥2 路可达 FAIL 注入 + `cp`+md5 还原（例：删一条新索引 ⇒ `check-tests-index` 红；把 `mem_sweep` 指回已删册 ⇒ `list` 红）。
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host`/`check-modules`/`build-*`**。
3. 只改：`tests/inst.yaml`、`tests/case-ledger.tsv`、`tools/chipyard/mem_sweep.py`（或删除它）、`tests/INVENTORY.md`、`docs/Process-09-*.md`、本任务书；**不改** `spec/`、`contracts/`、`components/**`、`tests/inst/*.S`。
4. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
5. 测试派节点、有空位就发（`ics170` 或 `server207`；`--jobs` = 核数−2 减去该节点已占的并行度）；派前 `remote.py status`；禁边构建边测试。

## 待裁定

（实现中写）

## 审阅记录

（待填）
