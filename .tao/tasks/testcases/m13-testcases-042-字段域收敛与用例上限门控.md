# m13-testcases-042: 收敛字段域全量扫描（`ctpop`/`ctlz`/`cttz` 138 → ≤127）+ 加「每 id ≤127」门控

**模块**：testcases
**项目里程碑**：M13
**依赖**：无（规则已于 2026-11-14 落 `docs/Process-05 §3.1` + `AGENTS.md`）
**可并行分片**：否（同册 YAML + 门控）
**预估**：2–3 h
**状态**：待开始

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

（实现中写）

## 审阅记录

（待填）
