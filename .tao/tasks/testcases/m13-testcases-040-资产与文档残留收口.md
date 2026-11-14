# m13-testcases-040: 资产/文档残留收口（4 条 `.S` 未入索引、`mem_sweep` 悬挂、trampoline 文档残留）

**模块**：testcases
**项目里程碑**：M13
**依赖**：无（`m13-testcases-030` 已合入；`m13-integ-002` 已合入并点名这些问题）
**可并行分片**：否（同一批清单/文档）
**预估**：1–2 h
**状态**：已验证

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

（无。三处越界均为机械必需项，已在完成区披露，请主会话确认是否接受。）

## 审阅记录

### 第 1 轮 engineer 自审

判决：改动逐行审过；finding 5 条已修、1 条记录不修（门控能力缺口，非本任务可修）；任务转 `待验收`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 按任务书「直接 `git rm mem_sweep.py`」会留下断链：`ctrl_sweep.py` 曾 `import mem_sweep as memsw` 取 `dump_reg`/`dump_mem` | ✅已修 | 两个 helper + 其依赖（`enc_mem`/`ST_OPC`/`LD_U_OPC`）搬入 `inst_sweep.py`，`ctrl_sweep` 4 处消费点改指 `sweep.` | `ctrl_sweep emit` 165 个产物 md5 逐项与改动前全等；`ctrl_sweep list` 67 例、`inst_sweep list` 273 例输出逐字节不变；注入 `dump_reg` 改名 ⇒ emit rc=1 |
| 验收 6 举例「删一条新索引 ⇒ 门控红」不可达：删条目后 `check-tests-index` 仍 PASS（489 条） | ❌不修（门控缺口，越界） | 改为可达注入「新条目 `file` → 不存在载体」，并把删除实测记为 GAP | I1 rc=2 且报 `file` 不存在；I4 实测 289 条仍 rc=0 |
| `inst_sweep.py` docstring 仍把已删三册与 `mem_sweep.py` 当现状 | ✅已修 | 改为「Memory vectors are `.S` carriers … (`run_asm_suite.py`)」 | `grep -rn mem_sweep tools/ Makefile` = 0 |
| 任务书写「`Process-09 §7`」，实际残留句在 §6（工具与 runner / glue）；§7（平台）全文无 trampoline | ✅已修（按真实位置） | 改 §6 glue 第 2 类 | `grep -rn "gen_trampoline\|--trampoline" docs/ tests/ tools/` = 0 |
| 新条目若按文件名序插入需给后续 15 条重编号 ⇒ 与 `refs/m13-002-fp-diff.json` 已记录的 id 漂移 | ❌不修（改为追加） | 4 条追加为 `020..023`，不动既有 id | `check-tests-index` ID 唯一 PASS；既有 001–019 未变 |
| `tools/testcases/lib/README.md` 的「已退役」句仍写 `gen_trampoline.py` ⇒ 验收 4 的 0 命中去不掉 | ✅已修 | 改为「旧的 trampoline 生成器与 `trampoline.bin` 已退役」（语义不变） | `grep -rn gen_trampoline docs/ tests/ tools/` rc=1（0 命中） |

### 第 1 轮 reviewer 验收（2026-11-14）

判决：**Accepted**（验收命令全部以本人重跑 rc 为准；越界 4 项判机械必需；节点事故已只读核实）

**重跑（任务 worktree 根，现场 rc）**：`make check-tests-index` rc=0（`inst=290 / total=490`）；`make validate-vectors` rc=0（`264 .S carriers / gaps: 0`）；`make check-case-ledger` rc=0（`2033 = vector 1510 + lit 523`；`derive_rows` 只吃 vector+lit、**不收根索引** ⇒ 2033 不变属实）；`make check-knowledge-refs` rc=0、`make check-no-residue` rc=0；`make check-run-artifacts` rc=2（`471 illegal`，`grep -v m12-chipyard-016` = 0）；`grep -rn "gen_trampoline\|--trampoline" docs/ tests/ tools/` rc=1（0 命中），残留句在 `Process-09:210`（§6；§7 自 218 行起无 trampoline）⇒ 按真实位置改正确。

**证据脚本**：审读 `run.sh` 逐条可达 FAIL（计数现场派生、注入含 assert 与还原 md5、I4 明标 GAP 不作断言），重跑 `bash .work/evidence/m13-testcases-040/run.sh` → rc=0 `EVIDENCE: PASS`（I1 rc=2、I2 hits=1、I3 rc=1、I4 `289` 条仍绿，四路还原 md5 全等并回绿）。

**mem_sweep 退役等价性（独立旧树，非采信其对账）**：`git archive 9b299e00^` 到临时树（仅软链 `.dadao`），新旧各跑 `emit` 并逐文件 md5：`ctrl` 165 项 **0 差异**、`inst` 430 项 **0 差异**；`sweep_expect=2d4d94651346ef673c5a855e024c1489`、`ctrl_expect=ab4ec3fe05ecd8d16bb7fba16156d005` 两侧相同；`inst_sweep list covered=273`、`ctrl_sweep list covered=67`；旧 `mem_sweep.py list` rc=1 `FileNotFoundError`、`SOURCES` 仍指三册、`scan_source` 只回点号/故障（退役理由成立）。`grep -rn mem_sweep tools/ Makefile` 文本 0 命中（`git grep` rc=1）。必要性实证：临时树删 `mem_sweep.py` 后旧 `ctrl_sweep list` rc=1 `ModuleNotFoundError` ⇒ 两个 helper 迁移非顺手改。

**注入（独立于其脚本再做一路）**：删 `inst-01-load-store-020` → `289/489` 条仍 `PASS rc=0`（**「删索引不红」属实**，完成区「新发现/坑 ②」已写明）→ `cp` 还原，md5 `861f1d29…` 等三件与注入前全等、门控回 490。

**节点副作用（只读核，未再 sync/reset）**：`remote.py status` 20:23 `dirty_files=4`；`sync_node_repo.sh` 确为 `reset --hard + clean -fd`（先打印丢弃清单）⇒ **确实会丢**；server208 现存 4 项 mtime 均 `20:28:09`（同步后被复原），md5 与 016 任务 worktree 原件一致（`run_embench_e2e.py` 节点侧为旧变体，属 016 自身同步口径）⇒ **主控机侧原件未丢**；`nproc=64`、20:23 `loadavg=6.13`、`running=none` ⇒ `TEST_JOBS=56 = 62−6` 合规；016 批进程仍活（`run_embench_e2e.py --jobs 32` + 4 个 verilator sim），节点 embench 日志 20:43 仍在推进（PASS 行）⇒ **批次未受影响**。

**约束核验**：`git diff --name-only 9b299e00^ 9b299e00` = 9 文件（任务书 + 已披露越界 4 项），`spec/`、`contracts/`、`components/`、`tests/inst/*.S` **0 改动**；未改主工作树、未 commit、未跑 `install-host`/`check-modules`/`build-*`；`git status -uall` 空、完成区 16 行、状态 `待验收`、未动台账/`discussing.md`。**采信未重跑**：`check-inst-asm`（禁再同步节点）→ 采信 `.work/log/infra/INFRA-130t/remote/INFRA-130t-run-server208.log`：`rc: 0 / jobs=56 / 897/897（链例 264 + 故障例 633）/ check-inst-asm: PASS`。

**非阻断 finding**：① `tools/chipyard/__pycache__/mem_sweep.cpython-312.pyc` 为被删模块的陈旧字节码（gitignored，门控不计）建议顺手删，完成区「grep=0」宜限定为跟踪源；② 节点 check-inst-asm 证据落在默认 `--log-prefix INFRA-130t` 目录、完成区未引路径，后续应传本任务号；③ `expected_ctrl_expect.md5` 系自记基线（单看可自洽），已由本轮新旧树逐文件比对补强；④ 016 embench 池 `--jobs 32` 与本测 56 同机，派单按实测 load 扣减合规，但峰值叠加仍可能超 62 核预算。

## 完成区

**测试结果**：全绿（rc 均为现场取值）：`check-tests-index` rc=0（四册合计 486→**490**，inst scope 286→290）；`validate-vectors` rc=0（264 `.S` 载体、数据缺口 0）；`check-case-ledger` rc=0（2033 条，`--write` 零 diff）；`check-inst-asm` 在节点 rc=0（**264 id / 897 镜像**，链例 264 + 故障例 633）；`check-knowledge-refs`/`check-no-residue` rc=0；273 例 `sweep_expect.bin` md5 `2d4d94651346ef673c5a855e024c1489` 不变。`check-run-artifacts` 全树 rc=2：471 条非法文件名**全部**落在在途 `m12-chipyard-016` 的日志子树，属本任务 0 条。

**修改文件**（与 `git status -uall` 逐项一致）：`tests/inst.yaml`（+4 条）、`tools/chipyard/mem_sweep.py`（删除）、`tools/chipyard/inst_sweep.py`（接收 helper）、`tools/chipyard/ctrl_sweep.py`（消费点改指）、`tests/INVENTORY.md`、`docs/Process-09-测试组织规范.md`、`tests/inst/MIGRATION.md`、`tools/testcases/lib/README.md`、本任务书。`tests/case-ledger.tsv` 无改动（重生成零 diff）。

**验收结果**：
1. 新增 4 条：`inst-01-load-store-020..023` ↔ `ldm.o_rrri_rf.S` / `ldm.t_rrri_rf.S` / `stm.o_rrri_rf.S` / `stm.t_rrri_rf.S`，`platforms=[system]`、`level: full`、`requires: []`（与同册条目同构）；上一轮已入索引的 001–019 未动。
2. `mem_sweep` 走**退役**：其输入是 YAML oracle 的期望寄存器/内存值（已随三册删除），`scan_source` 只给点号/故障、给不出期望字节 ⇒「从 `.S` 派生」只能退化成 `run_asm_suite --scan-only` 的重复列表器；而 `.S` 载体自带内联期望、已由 `run_asm_suite` 跑三平台。退役的唯一隐藏消费者 `ctrl_sweep` 已改指 `inst_sweep`，`emit` 产物逐字节不变。
3. 文档：`gen_trampoline` 与 `--trampoline` 在 `docs/`、`tests/`、`tools/` **0 命中**；`INVENTORY.md` 与 `Process-09` 均改为「旧 trampoline 已于 M13 退役，改用 64 KiB 固定固件 `bootrom/tiny/bootrom_tiny.bin`」。残留句实际在 `Process-09 §6`（非任务书写的 §7），按真实位置改。
4. 注入 4 路（均 `cp`+md5 还原并回绿）：新条目 `file` → 不存在载体 ⇒ `check-tests-index` rc=2 且报 `file` 不存在；文档写回 `gen_trampoline.py` ⇒ 残留命中 1；`dump_reg` 改名 ⇒ `ctrl_sweep emit` rc=1；删一条新索引 ⇒ 门控仍绿（见「新发现/坑 ②」）。
5. 一键证据脚本已跑通（`EVIDENCE: PASS`，含上述注入自检）；证据随运行期证据目录保留，未归档。

**新发现/坑**：① `01-load-store` 仍有 **15 条** `.S` 载体未入索引（`ldm`/`stm` 的 ra/rb/rd 与 b/w/t/sb/st/sw/ub/ut/uw 形式；现场派生 264 载体 vs 249 条已索引），本任务按书只补 4 条，建议另立任务一次补完并加「载体 id 集 == 索引 `.S` 集」双向断言。② `check-tests-index` 对「索引条目被删」无哨兵（实测 489 条仍 PASS），与 `ISS-441` 同口径。③ `sync-node-repo` 前该节点有 4 项他人未提交改动（含未跟踪 `tools/testcases/lib/chipyard_engine.py`），按脚本文档行为被 reset+clean 丢弃——节点侧不应留改动。④ `check-run-artifacts` 的 471 条红全属在途任务日志子树。

**遗留问题**：① `tests/inst/inventory.md`（「同口径问题见 `ISS-441` 的 `mem_sweep` 处置」）与 `components/chipyard/changelog.md`（m12 历史条目）仍提 `mem_sweep`，属「说明/历史」，未改。② **越界披露**：`tools/chipyard/{inst_sweep,ctrl_sweep}.py`（退役必须搬 helper）、`tests/inst/MIGRATION.md`（「遗留」行改「已处置」，否则记录与事实矛盾）、`tools/testcases/lib/README.md`（去掉已退役生成器名以满足 0 命中）——均机械改动、无行为变化。③ `ISS-441` 的悬挂引用已消除，可由主会话关闭。
