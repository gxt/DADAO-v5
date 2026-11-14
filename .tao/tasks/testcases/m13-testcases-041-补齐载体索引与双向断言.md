# m13-testcases-041: 补齐 `.S` 载体索引（剩 15 条）+ 加「载体集 == 索引集」双向断言

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-040`（已补 4 条；本任务补余下 15 条并加断言，**须在 040 合入后派**，避免同改 `tests/inst.yaml`）
**可并行分片**：否（同一索引文件 + 门控）
**预估**：1–2 h
**状态**：待开始

## 背景（`m13-testcases-040` 实测发现）

- 现场：`tests/inst/**` 共 **264 个 `.S` 载体**，`tests/inst.yaml` 仅索引 **245** 条（040 补 4 后余 **15** 条缺口）；
- 缺口全在 `01-load-store`：`ldm.{o,t,ub,ut,uw,st,sw,sb}_rrri_*` 与 `stm.{o,t,w,b}_rrri_*` 中的 15 条（`040` 已补 `ldm.o/t_rrri_rf`、`stm.o/t_rrri_rf` 4 条）；
- `check-inst-asm` 能跑到它们（按目录派生载体），但 `check-tests-index`/`validate-vectors` 的**索引/数据面**看不见 ⇒ 索引与执行面不一致；
- 另：`040` 实测「删掉一条新索引后 `check-tests-index` 仍 PASS」⇒ **该门控缺少「载体集 ↔ 索引集」双向断言**，这才是根因。

## 目标

1. 补齐余下 **15** 条 `tests/inst.yaml` 条目（与同册同构：`platforms:[system]`、`level: full`、`requires: []`；`file` 指向实际 `.S`）。
2. **加双向断言**（二选一，优先 ①）：
   - ① 在 `check-tests-index`（或 `tools/testcases/` 的检查器）里加：`tests/inst/**/*.S` 的 `(册, stem)` 集合 == `tests/inst.yaml` 里 `file:` 指向的 `.S` 集合；不等 ⇒ 报出**缺哪条/多哪条**并 rc≠0；
   - ② 独立新门控 `check-inst-index-bijection` 并接入 L1（同时更新 `docs/Process-07` 分层表）。
3. `check_case_ledger` 若受影响则 `--write` 重生成（本次预期零 diff，需贴证据）。

## 验收（逐条贴真实 rc）

1. 覆盖等式：现场派生「载体 264 == 索引 264」，并贴**独立脚本**（不 import 被测检查器）的两集合差集为空。
2. `check-tests-index` rc=0 且计数 490 → **505**（现场核，别写死：补 15 条后按现场值报）。
3. **新断言可达 FAIL**：① 删一条索引 ⇒ 应报「缺 `X`」rc≠0（证明补上了 `040` 发现的缺口）；② 造一条指向不存在 `.S` 的索引 ⇒ 应报「多/缺」rc≠0；两路 `cp`+md5 还原。
4. `validate-vectors` rc=0（264 载体、缺口 0）；`check-inst-asm` 264 id/897 镜像不变；273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变。
5. `check-knowledge-refs`/`check-no-residue`/`check-run-artifacts`（若红，核是否全属在途 `m12-chipyard-016`）。
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host`/`check-modules`/`build-*`**。
3. 只改 `tests/inst.yaml`、`tests/case-ledger.tsv`（如需）、`tools/testcases/**`（检查器）、`Makefile`（若走新门控）、`docs/Process-07`（若分层需记）、任务书；**不改** `spec/`、`contracts/`、`components/**`、`tests/inst/*.S`。
4. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
5. **不要 sync/reset 任何节点仓库**（`040` 已因此丢过节点侧未提交改动）；测试派节点时只用 bundle/临时 worktree。
6. 测试派节点、**有空位就发**；`--jobs` = 目标节点核数−2 **减去该节点已有占用**；派前 `remote.py status`；禁边构建边测试。

## 待裁定

（实现中写）

## 审阅记录

（待填）
