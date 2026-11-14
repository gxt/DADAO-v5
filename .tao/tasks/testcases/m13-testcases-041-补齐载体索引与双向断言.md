# m13-testcases-041: 补齐 `.S` 载体索引（剩 15 条）+ 加「载体集 == 索引集」双向断言

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-040`（已补 4 条；本任务补余下 15 条并加断言，**须在 040 合入后派**，避免同改 `tests/inst.yaml`）
**可并行分片**：否（同一索引文件 + 门控）
**预估**：1–2 h
**状态**：已验证

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

### 第 1 轮 engineer 自审（自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 只判「集合相等」时，同一载体被两条索引引用仍 PASS（条数不等、集合相等），「多」路不可达 | ✅已修 | `check_carrier_bijection` 增 `idx_list` 重复引用检测；self-test 增「注入·同一载体重复引用」 | self-test case6 rc=1 marker 命中；运行时 `索引 264 条` 与集合同值 |
| F2 证据脚本首版把节点期望 PASS 数写成 `CARRIERS*2+369` | ✅已修 | 改用本机 `run_asm_suite --scan-only` 现场派生 id/镜像数，与节点日志逐项对比 | `scan_ids_eq_carriers`、`node_asm_passes` 均 PASS（264/897） |
| F3 证据脚本基线曾由工作树 `inst.yaml` 派生 ⇒ delta 恒 0（恒真绿） | ✅已修 | 基线 ref 按「未提交=HEAD / 已提交=HEAD^」选取（提交前后判同一件事）；基线 total = 基线 inst 条目 + 当前非 inst 三册 | `total_delta_vs_baseline`/`inst_delta_vs_baseline` 期望 15 实际 15（基线 290/249） |
| F4 `sed` 提取 `baseline missing` 把右括号带进比较值 | ✅已修 | 改为捕获数字组 | `baseline_missing_derived` 期望 15 实际 15 |
| F5 证据输出误用 `.out` 扩展名，触发 `check-run-artifacts` A3 新增 1 条非法名 | ✅已修 | 改名 `.log` | 重跑后 471 条非法名全属在途 `m12-chipyard-016`，本任务 0 条 |
| F6 `_carrier_files` 用 `rglob("*"+suffix)`；若后缀含 glob 元字符会误配 | ⏸延后 | 暂不改：`CARRIER_SUFFIXES` 是常量且各值均为纯后缀，注释已写明扩表前置 | 当前仅 `inst: (".S",)`；扩到 arch/unit 前须改后缀比较（已记遗留） |
| F7 self-test 新用例插在基线之后，使后续 case 编号整体后移 | ❌不修 | 用例号由 `case_no` 自增、不参与判定，输出仅供人读 | 全 22 用例 `[PASS]`，`self_test: PASS` |

判决：finding 全部处置（无未修阻断项）⇒ 状态 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-14，全部命令由 reviewer 独立重跑，rc 现场取值）

**重跑记录**
- 差集独立核算（reviewer 自写脚本，**不 import 被测检查器**）：`carriers=264 / index .S=264 / missing=0 / extra=0 / dup=0`；`inst=305 arch=11 unit=186 tset=3 total=505`，rc=0。
- 15 条清单独立比对（`git show HEAD^:tests/inst.yaml` 差集）：恰 15 条、全在 `01-load-store`（`ldm.o_rrri_{ra,rb,rd}`、`ldm.{sb,st,sw,ub,ut,uw}_rrri_rd`、`stm.b/t/w_rrri_rd`、`stm.o_rrri_{ra,rb,rd}`），`removed=0`，字段形状/`platforms:[system]`/`level:full`/`requires:[]` 与相邻 023 条同构；抽 5 个 `.S`（`ldm.o_rrri_ra`/`ldm.sb_rrri_rd`/`stm.b_rrri_rd`/`stm.o_rrri_rb`/`stm.w_rrri_rd`）均存在。
- `make check-tests-index` → **rc=0**，`条目计数 … total=505`、`载体↔索引（inst .S）: 载体 264 个 / 索引 264 条 / 缺 0 / 多 0`；`--self-test` → **rc=0**，22 用例全 PASS（含 3 条新注入 + 1 条成对正例）。
- 三路独立注入（`cp` 备份 + md5 `d05dfd78…` 还原、还原后回绿 rc=0）：① 删 `ldm.o_rrri_ra.S` 索引 → make **rc=2**，`载体未入索引（缺）` **恰 1 行**且只该条；② 加幽灵 `ghost_reviewer_probe.S` → rc=2，`索引指向非载体（多）` 1 行；③ 同一 `.S` 写两条索引 → rc=2，`重复引用（多）` 1 行。
- 防恒真（`--root` 合成树，两侧各推空一侧）：载体空/索引 264 → rc=1、`多 264`；索引空/载体 264 → rc=1、`缺 264`；两侧皆空 → 双向行 `0/0/0/0` 但整体仍 rc=1（其它检查红）⇒ 任一侧都能独立驱动红，正例不恒真。
- 门控：`validate-vectors` rc=0（`264 .S carriers`、`gaps: 0`）；`check-case-ledger` rc=0（`现场身份 2033 条（vector 1510 / lit 523）`）；`inst_sweep emit` md5 `2d4d94651346ef673c5a855e024c1489`；`check-knowledge-refs` rc=0（悬空 0）、`check-no-residue` rc=0；`check-run-artifacts` make **rc=2**、471 条非法名**全部**含 `m12-chipyard-016`（其它 0 条）。
- `check-inst-asm` **reviewer 本机复跑**（qemu/bootrom 已存在，未重建、未动节点）：`jobs=62`、`264 个 id / 897 个镜像 / 897/897 通过 / 0 FAIL`，make **rc=0**（21:17:31→21:17:43）；节点日志 `jobs=31`、`897/897`、`EXIT=0` 与之一致。
- 证据脚本：逐条审毕原样重跑 `bash .work/evidence/m13-testcases-041/run.sh` → `EVIDENCE: PASS` **rc=0**；**独立注入**（删 `stm.w_rrri_rd.S` 索引）后重跑**同一脚本** → `EVIDENCE: FAIL（10 项不符）` **rc=1**；`cp`+md5 还原 → `EVIDENCE: PASS` **rc=0**。

**约束核验**
- 改动面 = `tests/inst.yaml` / `tools/testcases/check_tests_index.py` / `Makefile` / 本任务书，共 4 文件；禁区（`spec/`、`contracts/`、`components/`、`tests/inst/*.S`）**0 命中**；`Makefile` 仅 4 行注释改动（recipe `@$(PYTHON) …` 为上下文未动），`make check-tests-index` rc=0。
- 前/后两次 `git status --porcelain -uall` 均为空；注入前后 4 文件 md5 逐一相等（`d05dfd78…` / `0c26ffb1…` / `f62362f7…` / `f426daf2…`）；全程未跑 `install-host`/`check-modules`/`build-*`，未 sync/reset 任何节点（仅只读 `remote.py status`/`run`）。
- 完成区 17 行 ≤30、无运行期路径；`**状态**：待验收`；台账/`discussing.md` 未改。

**未决判定**：① `docs/Process-09 §5` 未记「载体集==索引集」——**不在本任务白名单**（硬约束 3 未列该文件），门控 docstring 与 Makefile 注释已同步 ⇒ **合理**，建议主会话补一行或另立小任务；② `arch`/`unit` 的 `.S/.s/.ll` 未纳入——任务目标 2① 明确限定 `tests/inst/**/*.S`，且 `unit` 的 `.s` 多由 `.ll` 派生、`arch` 有辅助 `.S` 头 ⇒ **合理**，扩 scope 前须先定义各 scope「载体」。

**非阻断 finding**：F1 完成区写 `check-run-artifacts rc=1`，`make` 层实测 rc=2（python 层 1）；F2 证据脚本临时目录落 `/tmp/opencode/m13-testcases-041-ev.*`（约定 `/tmp/opencode/<任务ID>/`，用后已删）；F3 节点 ics180 仓有 2 个脏文件（`tools/testcases/tset/embench/run_embench_e2e.py`、`tools/testcases/lib/chipyard_engine.py`），路径与本任务无关、非本任务可产生，`~/*041*` staging 无残留。

**判决：Accepted** —— 验收命令块在 reviewer 自己的重跑下全部通过、双向断言三路独立可达 FAIL 且防恒真成立、硬约束无违反。

## 完成区

**测试结果**：全绿（rc 均为现场取值）：`check-tests-index` rc=0（四册合计 490→**505**，inst 290→**305**；`载体↔索引（inst .S）: 载体 264 / 索引 264 / 缺 0 / 多 0`）；`--self-test` rc=0（22 用例全 PASS、0 FAIL）；`validate-vectors` rc=0（264 `.S` 载体、gaps 0）；`check-case-ledger` rc=0（2033 条，无需 `--write`）；`check-inst-asm` 节点 rc=0（**264 id / 897 镜像** = 链例 264 + 故障例 633，逐条 PASS）；273 例 `sweep_expect.bin` md5 `2d4d94651346ef673c5a855e024c1489` 不变；`check-knowledge-refs`/`check-no-residue` rc=0；`check-run-artifacts` rc=1：471 条非法名**全部**落在在途 `m12-chipyard-016` 日志子树，本任务 0 条。

**修改文件**：`tests/inst.yaml`（+15 条 `inst-01-load-store-024..038`）、`tools/testcases/check_tests_index.py`（`CARRIER_SUFFIXES`/`_carrier_files`/`check_carrier_bijection` + 3 条 self-test 用例 + docstring 第 9 项）、`Makefile`（门控注释改按现场派生、去掉写死的「13 类注入」）、本任务书。`tests/case-ledger.tsv` 无改动（rc=0 已证零 diff 需求不存在）。

**验收结果**：
1. **15 条清单**（独立脚本 `carriers_vs_index.py` 派生，不 import 被测检查器；对 HEAD 索引差集 = 15，全在 `01-load-store`）：`ldm.o_rrri_{ra,rb,rd}`、`ldm.{sb,st,sw,ub,ut,uw}_rrri_rd`、`stm.b_rrri_rd`、`stm.o_rrri_{ra,rb,rd}`、`stm.t_rrri_rd`、`stm.w_rrri_rd`（`.S`）；补后 `carriers 264 == index .S 264`、`missing 0 / extra 0`。
2. **双向断言落点**：改 `check-tests-index` 本体（方案①，不新增门控/不改 `Process-07` 分层表）。判据是**集合相等 + 重复引用检查**：缺 ⇒ `载体未入索引（缺）: <rel>`；多 ⇒ `索引指向非载体（多）: <rel>`；同一载体两条索引 ⇒ `重复引用（多）: <rel>`，任一即 rc=1。载体由文件系统 `rglob` 现场派生、索引由 YAML 现场派生，两侧逐条报出。
3. **可达 FAIL 二路（cp+md5 还原并回绿）**：① 删 `inst/01-load-store/ld.o_rrii_ra.S` 索引 ⇒ rc=2 且报「缺」该文件，还原 md5 相等后 rc=0；② 追加一条 `inst/01-load-store/ghost_041_probe.S`（盘上无此文件）⇒ rc=2 且报「多」该文件，还原 rc=0。`--self-test` 另含三条同类注入（缺 / 幽灵 / 重复引用）与一条「载体↔索引成对」正例（防恒真红）。
4. **check-inst-asm**：派前 `remote.py status` 全节点 rc=0，选 loadavg 7.37 的 40 核节点，`--jobs=31 = 40−2−7`（未用满、未与构建并行）；节点仅拉取任务树副本（载体内容按 `LC_ALL=C` 排序的 md5 清单与本地**同值**），**未 sync/reset 节点仓库**，跑完删除节点 staging；结果为 264 id / 897 镜像 / 全 PASS（与本地 `--scan-only` 派生 264/897 逐项一致）。
5. **其余**：273 例 md5 不变；`check-run-artifacts` 红集全属在途 016（本任务 0）；一键证据脚本 rc=0 `EVIDENCE: PASS`（含两路注入自检与还原 md5 对账），随运行期证据目录保留、未归档。

**新发现/坑**：① 「集合相等」不足以守索引：重复引用会让集合不变而条数膨胀，必须同时比条数与去重集（否则「多」的 FAIL 路不可达）。② `arch`/`unit` 的载体模型与 `inst` 不同（`unit` 的 `.s` 多由 `.ll` 派生、`arch` 有辅助 `.S` 头），按后缀无脑套用会假红 ⇒ `CARRIER_SUFFIXES` 只纳入「一载体一索引」的 scope。③ 节点上未装/未建产物时不要凭「有 repo 就能跑」假设：先核 bootrom 与工具链存在性，且用任务树副本 + 指向节点安装根的软链跑，避免动节点仓库。

**遗留问题**：① `docs/Process-09 §5` 对 `check-*-index` 的描述仍只有「ID 唯一/文件存在/字段合法/scope/平台合法/计数现场派生」，未写「载体集 == 索引集」（该文件不在本任务改动白名单，建议主会话补一行）。② 按书只覆盖 `inst`：`arch` 有 1 个 `.S`（`hmon_min.S`）、`unit` 有 20 个 `.s` 与 11 个 `.ll` 仍未入索引；若要把双向断言扩到 arch/unit，须先给各 scope 定「载体」定义（另立任务）。③ `_carrier_files` 的 `rglob("*"+suffix)` 在扩表时须改为后缀精确比较（见 F6）。④ 节点 staging 已删、无未提交改动遗留。

