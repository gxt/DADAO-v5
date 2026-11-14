# m13-testcases-045: riscv-tests 语料精选迁移 + 退役（保留借鉴清单）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-044`（同改 `tests/inst/**/*.S` 与 `.S` 点数，须串行）
**可并行分片**：否
**预估**：3–4 h
**状态**：待开始

## 用户裁定（2026-11-14，原话）

> 「tests/riscv-tests/ 还有必要存在吗？有没有需要借鉴的测试用例？」→ 选「**迁移精选值后退役**」：把有语义价值、且现有 `.S` 未覆盖的常量并入对应 `.S`；`inventory.yaml` 转成借鉴清单存档；然后删语料与脚本。

## 现状（`m13-integ-004` 已验证，2026-11-11）

- `tests/riscv-tests/`：114 个上游文件分类（**35 port / 57 rewrite / 22 na**）、474 条值用例、裸机框架 `framework/dadao_test.inc`、`inventory.yaml`、`upstream-index.yaml`（含 sha256）；
- `tools/testcases/riscv_tests/`：`extract.py`（刷新）、`verify_cases.py`（独立 oracle）、`run_riscv_tests.py`（qemu+gem5 差分）；
- **不在任何门控里**（`Makefile` 无 riscv-tests 目标）；
- 常量对比（现场）：port 用例 **147 个唯一常量，91 个在现有 `.S` 中不出现**，例：`0x7fc0`/`0x7e00`（NaN 位型）、`0xff7f`、`0x1fefe`、`0x2fe7d`、`0xf000f0`、`0xff00ff`、`0xff07ff`、`0x424242`、`0xffffffff80000000`（32↔64 符号边界）。

## 阶段 A：映射与筛选（只读）

1. 建立 **riscv op → DADAO id** 映射表（如 `add`→`add.uo_rrrr_rd`、`addw`→`add.st_orrr_rd`/tetra 族、`sll`→`shl.o_orrr_rd`、`slt`→`cmp.so/uo + br`、`mulh/mulhu`→`mul.so/mul.uo` 的高半分解等），逐条写依据（`contracts/opcodes.yaml` + spec）；
2. 147 个常量按「符号/零扩展边界、NaN 位型、密集位模式、平凡值（0/1/2/3）」分类；
3. 输出 `<运行期证据目录>/port-values-selected.tsv`：op / DADAO id / 常量 / 分类 / 是否已被 `.S` 覆盖 / 是否入选（**每 id ≤10 条**，边界与特殊值优先）。

## 阶段 B：并入 `.S`（只补入选值）

- 对入选的每个 `(id, 常量)`，在对应 `.S` 的合适链位**追加检查点**：**输入用该常量；期望值必须独立推导自 spec**（手算/规则），**不得**照抄 `cases/*.yaml` 的 `expected`（那是 riscv-tests 的值，且 RISC-V 语义与 DADAO 不完全一致）；
- 每个 id 追加 ≤10 条，且该 id 总用例数仍 **≤127**（`check-tests-index` 会机械核）。
- `ft`/`fo`、`cmp`、`mul` 这类涉及标志/高半的，期望要写清依据（如 `mul.so` 高半的符号规则见 `contracts/opcodes.yaml`/spec）。

## 阶段 C：存档与退役

1. 把 `inventory.yaml` 的 **114 条分类 + 57 条 `rewrite` 理由**转成 `.tao/knowledge/refs/riscv-tests-borrowing.md`（保留 `upstream_commit` 与 sha256 溯源；标注「内容溯源，非执行必需」）；
2. `git rm -r tests/riscv-tests/ tools/testcases/riscv_tests/`；
3. 更新 `docs/TestReports/M13-riscv-tests移植与差分.md`（若存在）：加一句「语料已于 M13 精选迁移后退役，借鉴清单见 refs」；
4. `grep -rn "riscv-tests\|riscv_tests"` 在 `Makefile`/`tools/`/`tests/` 只余历史归档与 refs 说明。

## 验收（逐条贴真实 rc / 现场值）

1. `port-values-selected.tsv` 完整；每 id 入选 ≤10 条、边界/特殊值优先；平凡值（0/1/2/3）不入选（`.S` 已有）。
2. **期望独立推导**：抽查 5 条新检查点，核其期望值与 spec 一致、且与 `cases/*.yaml` 的 `expected` **不同源**（若恰好相同，需说明是巧合或有手算依据）。
3. `check-inst-asm` 264 id 不变、镜像数按现场 +N；`check-tests-index`（每 id ≤127 门控）rc=0；`validate-vectors` rc=0；`check-case-ledger` 现场值。
4. 阶段 C 后 `git grep -c "riscv-tests"` 只剩 refs/归档；`tools/testcases/riscv_tests/` 不存在。
5. 可达 FAIL 注入 ≥2 路（改一条新检查点期望 ⇒ `check-inst-asm` 红；把某 id 补到 128 ⇒ 上限门控红），`cp`+md5 还原。
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host`/`check-modules`/`build-*`**；**不要 sync/reset 节点仓库**。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 只改 `tests/inst/**`（`.S`）、`tests/riscv-tests/`（删）、`tools/testcases/riscv_tests/`（删）、`.tao/knowledge/refs/riscv-tests-borrowing.md`（新）、`docs/TestReports/M13-riscv-tests*`（若存在）、任务书；**不改** `spec/`、`contracts/`、`components/**`。
5. 测试派节点、有空位就发；`--jobs` = 核数−2 减占用。

## 待裁定

（实现中写；若某 op 在 DADAO 无等价语义、或某常量无法独立推导期望 ⇒ 停下写清，不得照抄上游）

## 审阅记录

（待填）
