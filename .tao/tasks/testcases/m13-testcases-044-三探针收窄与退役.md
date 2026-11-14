# m13-testcases-044: FMA/minmax/roundint 三个 C 探针收窄（先核 llvm 覆盖，再抽点进 `.S`，最后退役）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-043`（同改 `tests/inst.yaml` 与 `check-case-ledger`，须串行）
**可并行分片**：否
**预估**：3–5 h（阶段 A 审计 ~1 h；阶段 B 补点 ~1–2 h；阶段 C 退役 ~1 h）
**状态**：待开始

## 用户裁定（2026-11-14，原话）

> 「是不是应该考虑 tests/unit/llvm/ 下面是否有匹配？」

→ 即：先核 `tests/unit/llvm/`（lit CodeGen + e2e）与 picolibc 是否已覆盖这三个 C 探针的能力；有覆盖的退役，没覆盖的按「≤127 + 边界/异常优先」抽点补进 `.S`，再退役。

## 三个探针现状（现场）

| 目录 | 文件 | 入口门控（L3） | 覆盖什么 |
|---|---|---|---|
| `tests/inst/fma/` | `fma_common.h`、`fma_edges.c`、`fma_dot.c`、`fma_horner.c` | `make check-fma-probe` | C 层 FMA **单次舍入**（点积/GEMM/Horner），`-O0/-O2`，与 `oracle_fma.py`（`fractions` 精确+一次舍入）比对 |
| `tests/inst/minmax/` | `minmax_common.h`、`minmax_matrix.c`、`minmax_clamp.c`、`minmax_c23.c` | `make check-minmax-probe` | C23 `fmin/fmax`（NaN/±0/clamp），与 `oracle_minmax.py` 比对 |
| `tests/inst/roundint/` | `rnd_common.h`、`rnd_matrix.c`、`rnd_mode.c`、`rnd_flags.c` | `make check-rnd-probe` | `ftrnd/fornd` 六种舍入 × 标志矩阵，与 `oracle_rnd.py` 比对 |

9 条 `.c` 同时登记在 `tests/inst.yaml`（`inst-fma-001..003`、`inst-minmax-001..003`、`inst-roundint-001..003`）。

## 阶段 A：覆盖核对（只读，先做）

逐项核 `tests/unit/llvm/` 与 picolibc 的**真实执行**（不是"文件存在"）：

1. `lit/CodeGen/DADAO/fma.ll`、`p1-fp-minmax.ll`、`p1-fp-rounding.ll`、`p1-fp-rounding-f32.ll`、`fp-rounding-mode.ll` —— 断言的是什么（指令选择 / 结构）；
2. `e2e/fma_e2e.c` + `lit/fma_e2e.test` —— 是否**运行**并验证单次舍入（读源码确认构造了两步舍入会得 0 的输入）；
3. `e2e/p1_fp_e2e.c` —— 注释称 floor/ceil/trunc/round/rint/nearbyint、fmin/fmax 的 libcall 类由 picolibc 证据 runner 承担 ⇒ **实跑 `make check-picolibc-tests`（或对应目标）**，核实 `test-floor/test-ceil/test-round/test-minmax/test-fma` 是否真的在跑、是否比数值（不是只比退出码）。

**输出**：`<运行期证据目录>/coverage-matrix.tsv`（能力 × `.S` × lit × e2e × picolibc × 结论），缺口列明。

## 阶段 B：按缺口抽点补进 `.S`（只在阶段 A 判定「没覆盖」处做）

- 候选载体：`ftfma_rrrr_rf.S`/`fofma_rrrr_rf.S`、`ftmin/ftmax/fomin/fomax_orrr_rf.S`、`ftrnd/fornd_orri_rf.S`；
- 每个缺口 **补 3–5 条**（遵守 `docs/Process-05 §3.1`：特定值 + 随机固定种子；**边界/异常优先**，不许全量补格）；
- 每条在 `.S` 注释写 spec 依据 + 手算过程；期望值**不得**抄 `oracle_*.py` 输出（须由 spec 独立推导；`oracle_*` 只作交叉检查）。

## 阶段 C：退役（阶段 A/B 完成后）

1. 删 `tools/testcases/run_{fma,minmax,rnd}_probe.py` 与 `oracle_{fma,minmax,rnd}.py`；
2. `Makefile` 摘除 `check-{fma,minmax,rnd}-probe`（L3 成员、`.PHONY`、`help` 行），`docs/Process-07` 组合表同步；
3. 删 `tests/inst/{fma,minmax,roundint}/` 三个目录（9 个 `.c` + 3 个 `.h`）与 `tests/inst.yaml` 对应 9 条（现场核计数：`inst` 305 → 296）；
4. `check-case-ledger` 重生成；`grep -rn "run_fma_probe\|oracle_fma\|check-fma-probe"` 在 `Makefile`/`tools/` = 0（历史归档除外）。

## 验收（逐条贴真实 rc / 现场值）

1. 阶段 A 的 `coverage-matrix.tsv` 完整；**若某项"看起来有覆盖"但实际只比退出码 ⇒ 记为缺口**并进入阶段 B。
2. 阶段 B 补的条目：每 id ≤127（门控核）、边界/异常类先行、seed 注明；`check-inst-asm` id 数 264 不变、镜像数按现场 +N。
3. 阶段 C 后：`check-case-ledger` rc=0（计数现场值）、`check-tests-index` rc=0（296 现场核）、`validate-vectors` rc=0；`make check-picolibc-tests` 仍 rc=0。
4. **不许**把这三个探针的 oracle 结果当新向量的期望值（Independent oracle 判据）；`fp_ref.py` 保持"生成期工具"定位。
5. 可达 FAIL 注入 ≥2 路（删一条新 `.S` 点 ⇒ `check-inst-asm` 红；改 `Makefile` 留一处 probe 引用 ⇒ `grep` 断言红）。
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host`/`check-modules`/`build-*`**；**不要 sync/reset 节点仓库**。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 只改 `tests/inst/**`（`.S` 与三个目录）、`tests/inst.yaml`、`tests/case-ledger.tsv`、`tools/testcases/**`、`Makefile`、`docs/Process-07`、任务书；**不改** `spec/`、`contracts/`、`components/**`。
5. 测试派节点、有空位就发；`--jobs` = 核数−2 减占用。

## 待裁定

（实现中写）

## 审阅记录

（待填）
