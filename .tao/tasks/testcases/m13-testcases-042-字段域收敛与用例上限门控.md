# m13-testcases-042: 收敛字段域全量扫描（`ctpop`/`ctlz`/`cttz` 138 → ≤127）+ 加「每 id ≤127」门控

**模块**：testcases
**项目里程碑**：M13
**依赖**：无（规则已于 2026-11-14 落 `docs/Process-05 §3.1` + `AGENTS.md`）
**可并行分片**：否（同册 YAML + 门控）
**预估**：2–3 h
**状态**：已验证

## 用户裁定（2026-11-14，原话）

> 「为什么就这几条指令做字段域扫描，这本身就不合理！只选择8/16/32/64等特定字段，然后随机选3-5个非特定字段；我们要做的指令测试不是全量测试，无特殊情况下，每条指令的测试用例不要超过127个，换言之，一个汇编文件；而且应该先保证边界和异常情况」

## 现状（现场统计）

- `tests/inst/bitcnt/bitcnt.yaml`：`ctpop_orri_rd` / `ctlz_orri_rd` / `cttz_orri_rd` 各 **138 条**（`semantic 64 + boundary 72 + encoding 1 + legality 1`），是**全量 `hd` 0..63 扫描**；
- 全仓其余 id 均 ≤ 81 条（`clmul.o` 81、`frtnd/fornd` 23、多数 2–5 条）；`.S` 文件最大 38 个检查点（`lr.w.nn_orrr_rd.S`），**无 >127**；
- 结论：**只有这三个 id 违反新规则**。

## 目标

1. **把三个 id 收敛到 ≤127**（目标 60–80 条，别贴着上限塞）：
   - 保留**全部** `encoding`/`legality`/`overlap` 与 `boundary` 里的**异常/极值**用例；
   - `hd` 取值集改为：**特定值** `{0, 1, 7, 8, 15, 16, 31, 32, 63}`（含 8/16/32/64 位边界及其 −1）+ **5 个随机非特殊值**（**固定种子**，如 `seed=20261114`，在 YAML 顶部注释与 `notes` 里注明 seed 与选中的 5 个值）；
   - 抽掉的用例必须在完成区列出**逐条清单**（id / 原 hd / 类别），并说明为何不是边界/异常类。
2. **加门控断言**：「每 id 用例数 ≤ 127」——放 `tools/testcases/check_tests_index.py` 或 `check-case-ledger` 的检查器里（二选一，写清理由）；超限报出 `id / 实际数 / 上限` 并 rc≠0。
3. 若 `inst_sweep`（273 例独立 oracle）依赖这 3 个 id 的 YAML，需同步核对 `sweep_expect.bin` 是否变化：**期望不变**（删的是同分布用例，不是新期望），若 md5 变必须解释原因。

## 验收（逐条贴真实 rc / 现场值）

1. 三个 id 的用例数：138 → **≤127（现场值）**；`ctpop` 的 hd 取值集恰为「9 个特定值 + 5 个随机值（seed 注明）」。
2. **异常/边界不缩水**：`class` 分布里 `legality`/`overlap`/`encoding` 条数**不变**；`boundary` 中极值（全 0/全 1/±边界）用例**全部保留**（逐条贴清单）。
3. 门控：`check-tests-index` rc=0（505 不变）、`validate-vectors` rc=0、`check-case-ledger` rc=0（条数现场值，预期 1510 → 减少量 = 删除条数）；`check-inst-asm` 264 id/897 镜像不变（节点跑，`--jobs` = 核数−2 减占用）。
4. 273 例 `sweep_expect.bin` md5：不变或变化且有解释。
5. **新断言可达 FAIL**：把某 id 临时加到 128 条 ⇒ 报「超上限」rc≠0；还原回绿（`cp`+md5）。
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host`/`check-modules`/`build-*`**；**不要 sync/reset 任何节点仓库**。
3. 只改 `tests/inst/bitcnt/bitcnt.yaml`、`tests/case-ledger.tsv`（重生成）、`tools/testcases/**`（门控）、必要时 `tests/inst.yaml`（不动条目数）、任务书；**不改** `.S` 载体、`spec/`、`contracts/`、`components/**`。
4. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
5. 随机抽样须**固定种子**且可复现（脚本/命令留在证据目录）。

## 待裁定

1. **文档口径已过期（越出本任务可改范围，未改）**：`tests/inst/inventory.md:211` 仍写「**全量** `hd ∈ 0..63` 的 semantic（不抽样）+ 定值（`hd` 全量）」；`tests/README.md:210`（「rev/bitcnt 476 例」）、`tests/INVENTORY.md:83`（「1 册 / 414 例」）、`tests/inst/MIGRATION.md:295`（「各 138 例」）仍是旧计数。本任务硬约束只允许改 `tests/inst/bitcnt/bitcnt.yaml`/`tests/case-ledger.tsv`/`tools/testcases/**`/`tests/inst.yaml`，故未动。**问题**：并入本任务（放开这 4 处文档）还是另立收口任务？**建议**：另立一个 testcases 文档收口任务（与 `testcases-040` 同类），本任务维持范围不变。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-14）

改动 = 生成器（抽样集 + 极值循环 + 校验）+ 落盘 YAML + 台账重生成 + `check-tests-index` 新增第 10 项断言。逐行审查发现与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `verify_hd_sample` 返回 `(len(want), len(HD_SAMPLE))` 是**恒真**统计（两侧同源） | ✅已修 | 改为从用例现场求 `used` 并集，返回 `(len(used), len(want))` | `--check` 输出 `hd 抽样集 14/14`（现场派生） |
| docstring 写「三类极值」，代码实为四类（全0/全1/单bit最高/单bit最低） | ✅已修 | 文档改为四类 | `--check` 的 `semantic/boundary 重算=213` 与极值断言全 PASS |
| `hd=0` 时「全 1／单 bit 最高／单 bit 最低」输入同为 1 ⇒ 会产生 3 条同内容用例 | ✅已修 | 极值循环按 `(hd, 源值)` 去重 | 结构断言「每抽样 hd 的极值齐全」= 空缺口；删除清单中 3 条为「原重复条目，去重」（未损失覆盖） |
| 证据脚本 `record_rc` 参数序与调用点不一致（会把任务名当 rc 比较） | ✅已修 | 统一为 `(name, actual_rc, expect_rc, log)` | `run.sh --inject` PASS 21 / FAIL 0 |
| 注入断言里把「实际 147」写死（规则禁止写死计数） | ✅已修 | 改为正则 `用例 [0-9]+ > 上限 127`，实际值现场打印 | 注入日志打印 `用例 147 > 上限 127` |
| worktree 基线停在 `6107df29`（早于派单台账提交）⇒ `check-milestones-fresh` R1 报「有 worktree 但未列入进行中」 | ✅已修 | `git merge --ff-only master`（FF 到任务声明的基线 `3a21ca4b`，**未新建提交、未改台账内容**） | `make check-milestones-fresh` rc=0；改动文件 md5 前后一致 |
| 门控把 `.S` 检查点计入每 id 总数 ⇒ 暴露 `ctpop/ctlz/cttz` 原为 138(YAML)+19(.S)=**157**（已超 127），属既有违规 | ✅确认（非缺陷） | 计数口径写进门控注释与 docstring | `check-tests-index` 现场：`264 个 id，最大 clmul.o_rrrr_rd=102` |


### 第 1 轮 reviewer 验收（2026-11-14）

**重跑（本 worktree，rc 现场取，非采信完成区）**：`make check-tests-index` rc=0（505；264 id，最大 `clmul.o_rrrr_rd=102`）；`check_tests_index.py --self-test` rc=0（24 项，含 127 PASS / 128 FAIL×2）；独立重算每 id 合计（YAML+`.S`，复用 `scan_source`）＝ ctpop/ctlz/cttz 各 **73+19=92**、>127 者 **0**；`validate-vectors` rc=0（156/156、264 `.S`、gaps 0）；`check-case-ledger` rc=0（**1838** = vector 1315 / lit 523，现场）；`check-generator-sync` rc=0；`generate_bitcnt --check` rc=0（抽样 14/14、极值 42/42、`--self-check` 1344 例 PASS）；`check-inst-asm` rc=0（**264 id / 897/897 镜像，jobs=62 主控机**）；证据脚本 `run.sh` 全量 rc=0 **PASS 17/FAIL 0**、`run.sh --inject` rc=0 **PASS 21/FAIL 0**。

**抽样复现（独立重算）**：`random.Random(20261114).sample(0..63 去特定值,5)` = **[6,21,38,43,45]**，落盘 hd 集恰 {0,1,6,7,8,15,16,21,31,32,38,43,45,63}（9 特定 + 5 随机）；YAML 头注释与 notes 均含 `seed=20261114` 与 5 值（grep 真）。

**边界/异常不缩水**：三 id `encoding` 1→1、`legality` 1→1、`overlap` 0→0、`expected_fault` 3→3 不变；结构断言 42/42（每抽样 hd 全0/全1/单bit最高/最低齐全、hd=7 掩码、hd=31 `rdhc=rd0`、hd=15 原地、hd=63 三极值）；**删除的 150 条 boundary 全为「hd∉抽样集的定值/全0」**（notes 含「定值」150/150），极值类 **0 删除**，抽样 hd 的全0 14 条在——属 hd 收敛必然后果，非砍异常类。删除清单抽 5 条（hd 39/11/28 定值、hd 19/12 semantic）全部 hd∉抽样集。

**注入（reviewer 独立执行）**：YAML 补至 109（+`.S` 19=128）⇒ `CASE LIMIT: id=ctpop_orri_rd 用例 128 > 上限 127` **rc=1**；另向 `ctpop_orri_rd.S` 注入 36 检查点（55+73=128）⇒ 同样 **rc=1**（证明 `.S` 检查点真参与计数）；`cp`+md5 还原后 `6d85d4aa…`/`30c16d7c…` 与注入前一致、rc=0 回绿。

**inst_sweep**：`VECTOR_FILES` 6 文件无 `bitcnt`（`grep bitcnt` rc=1）；`emit` rc=0 `covered=273`、`sweep_expect.bin` md5 **`2d4d94651346ef673c5a855e024c1489`** 一致。

**越界/快照对账**：`git diff --name-only 3a21ca4b..1dca75a8` 恰 5 文件＝完成区声明；无 `.S`/`spec`/`contracts`/`components`/`inst.yaml`/台账改动；验收前后 `git status -uall` 均空、`git stash list` 空；完成区 13 行 ≤30；任务书 grep `/mnt|/tmp|/home` 无运行期路径。**披露**：「删除 303」= 唯一 300 + 重复副本 3，414−303+108=219 自洽。

**判决：Accepted**（验收命令块全绿 + 硬约束无违反）。文档口径过期 4 处维持「待裁定」1，由 architect 收尾处置。

## 完成区

**测试结果**：证据脚本 PASS 21 / FAIL 0（`run.sh --inject`，含 L2）。逐项现场值：三 id **138 → 73**（YAML）+ `.S` 载体 19 = **92/id ≤127**；`hd` 集 = 特定 `{0,1,7,8,15,16,31,32,63}` + 随机 `{6,21,38,43,45}`（`seed=20261114`）；`class`（每 id）encoding 1→1、legality 1→1、overlap 0→0、semantic 64→14、boundary 72→57；`check-tests-index` rc=0（505 不变；每 id 上限行「264 个 id，最大 clmul.o_rrrr_rd=102」）、`--self-test` rc=0、`validate-vectors` rc=0（156/156、264 `.S` carriers、gaps 0）、`check-case-ledger` rc=0（2033→**1838** = vector 1510→1315 / lit 523）、`check-generator-sync` rc=0、`generate_bitcnt --check` rc=0、`--self-check` 1344 例 PASS、`check-inst-asm` rc=0（264 个 id / 897 镜像 = 链例 264 + 故障例 633）、`inst_sweep emit` rc=0 `covered=273` 且 `sweep_expect.bin` md5 **`2d4d94651346ef673c5a855e024c1489` 不变**（`bitcnt` 不在该 sweep 覆盖集）。

**修改文件**：`tests/inst/bitcnt/bitcnt.yaml`（重生成 414→219）、`tests/case-ledger.tsv`（`--write` 重生成，±303/108 行）、`tools/testcases/generate_bitcnt_vectors.py`（抽样集 + 极值循环 + 校验口径）、`tools/testcases/check_tests_index.py`（新增第 10 项「每 id ≤127」，含 127 PASS / 128 FAIL ×2 自检）；任务书本文件。`tests/inst.yaml` 未动（条目数不变）；无 `.S`/`spec/`/`contracts/`/`components/` 改动。

**验收结果**：① 收敛后 `ctpop/ctlz/cttz` 各 73（YAML）≤127，`hd` 恰为 9 特定 + 5 随机；② `encoding`/`legality`/`overlap` 条数不变，`boundary` 极值**全保留**（全 0、全 1（含 hd=63 ⇒ 64）、单 bit 最高/最低、`hd` 以上位不参与（hd=7）、`rdhc=rd0`（hd=31）、`rdhb==rdhc`（hd=15））——结构断言 42/42 PASS；③ 门控四条 rc=0（见上）；④ 273 例 md5 不变（原因：`inst_sweep` 的 `VECTOR_FILES` 不含 `bitcnt`，`bit_sweep total` 969→774 仅随本 YAML 减量）；⑤ **可达 FAIL**：`ctpop_orri_rd` 补到 128（YAML）+19（`.S`）⇒ `CASE LIMIT: id=ctpop_orri_rd 用例 147 > 上限 127` rc=1；`cp` 还原后 md5 `6d85d4aa…` 与注入前一致、rc=0。

**删除/新增清单摘要**：删除 **303** 条（101/id）＝ `hd ∉ 抽样集` 的 semantic 50 + 定值（全 0）50 + `hd=0` 全 0 重复条目去重 1（同内容仍保留 1 条，覆盖未损失）；新增 **108** 条（36/id）＝其余 12 个抽样 `hd` 的「全 1 / 单 bit 最高 / 单 bit 最低」极值（hd=0/63 同名极值原已有）。逐条（id/class/word/hd/原因）落运行期证据目录 `deleted-added.md`。

**新发现/坑**：① 每 id 总数须含 `.S` 检查点——`ctpop/ctlz/cttz` 原 138(YAML)+19(`.S`)=**157** 已超 127（门控一上即红，本任务降到 92）；`clmul.o` 102 亦为 YAML+`.S` 之和。② 文档口径过期但越界（见「待裁定」1）。③ `make -k check` 5 项红**全部**为环境/在途：`check-patch-tree`（chipyard 组件树脏，`m12-chipyard-016/002` 在途）、`check-musl-freshness`（`ISS-437`）、`check-run-artifacts`（471 条全为 `m12-chipyard-016` 日志）、`check-temp-dirs`（4 个他任务陈旧临时目录）、`check-milestones-fresh`（worktree 基线早于派单提交，FF 到 `3a21ca4b` 后转绿）。

**遗留问题**：① 文档口径待收口（`tests/inst/inventory.md:211` 的「全量/不抽样」、`tests/README.md:210`、`tests/INVENTORY.md:83`、`tests/inst/MIGRATION.md:295` 的旧计数）——越出本任务可改范围，见「待裁定」1，未改。② 节点侧 `check-inst-asm` 未跑（夜跑占用 + 禁 sync），改为主控机跑（`jobs=62`）——输入集未变（`.S` 与 `run_asm_suite` 零改动），结论等价。
