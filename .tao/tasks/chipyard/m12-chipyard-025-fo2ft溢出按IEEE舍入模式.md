# m12-chipyard-025: `fo2ft` 溢出按 IEEE 舍入模式（RTL + 模型）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m13-spec-002`（已合入）+ `m12-chipyard-014`（已合入）
**可并行分片**：否（单核实现，单写者）
**状态**：待验收

## 背景（共同，5 个子任务共用）

用户 2026-11-12 定规则（`MEMORY.md`）：**浮点差分一律以 IEEE-754 2019 为准**。

**条款**：`fo2ft` 溢出。现行 spec/实现：溢出**恒** ±Inf + `OF|NX`。IEEE 754-2019 §7.4：`RNE`/`RUP` ⇒ ±Inf；`RTZ`/`RDN` ⇒ **±最大有限值**；均置 `OF|NX`。

## 本任务目标（只改 chipyard RTL 与模型）

1. `WumingFP.scala` 的 `fo2ft`（含 `ft2fo` 的 SBZ 路径若共用溢出逻辑）溢出结果按 `rf0[33:32]` 的舍入模式分派：
   - `RNE`(0) / `RUP`(?) ⇒ ±Inf
   - `RTZ` / `RDN` ⇒ ±最大有限
   - 标志保持 `OF|NX`
   - **先读 spec 定稿**（`m13-spec-002`）确认四档模式编码与符号规则（尤其负数 RDN 到底给 −Inf 还是 −max）
2. 模型 `tools/chipyard/fp_ref.py` 同步（与 spec 一致，不是与 RTL 一致）。
3. 单元台新增/更新溢出向量：四档舍入 × 正/负 × 轻微/严重溢出各 ≥1 例。

## 非范围

- 不改 QEMU（`m13-qemu-005`）、gem5（`m13-gem5-007`）、向量册（`m13-testcases-011`）
- 不动其它 FP 语义

## 验收标准

1. 四档舍入 × 正负的溢出结果逐条给输出（值 + `rf0`），与 hardfloat `RoundAnyRawFNToRecFN` 一致
2. 单元台 `f2f` 组例数 ≥ 原先 + 8，RTL == hardfloat == 模型三方 0 差异
3. 核上专测组 ≥8 例：`fo2ft` 溢出在四档下的 `rd` 值与 `rf0`，与 QEMU（`m13-qemu-005` 后）逐字节
4. **可达 FAIL 注入**：把分派改回「恒 ±Inf」⇒ 至少 RTZ/RDN 两例红；`cp`+md5 还原回绿
5. 273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变；elab/Verilator rc=0；L2 rc=0；`check-patch-tree` rc=0
6. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- `.work` 必须软链（`ISS-389`）；`JOBS=8`。
- 与 `015` 串行（同组件单写者）。
- 若发现 spec 定稿与本任务理解不一致，**停下写「待裁定」**，不要自行选边。

## 硬约束（子代理必读）

1. 独立 `git worktree` 作业（分支名 = 任务号），禁改主工作树（`ISS-368`）；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账；计数现场值（`ISS-388`/`ISS-391`）。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
8. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审

**审查方式**：逐行读 `git diff`（7 个实现文件 + 本任务书）、对照 `spec/SimRISC-07 §1.4` 表与 IEEE 754-2019 §7.4 原文逐格核；证据脚本全量跑两轮、注入跑两轮。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `unit_run` 的 `FT_MAX_Q` 用「`FT_MAX` 位型当数值」算阈值，且 `ovf_unbounded` 忽略符号 ⇒ 8 例误判红 | ✅已修 | 改 `0xFFFFFF·2^104`；RUP/RDN 的幅值上舍按符号分派 | `fo2ft ovf` table-diff=0，30 例全绿 |
| F2 首版把「中点下」对照例一律叫 `noovf`，但 RUP 正 / RDN 负 / RNA 仍溢出 | ✅已修 | 改名 `fo2ft_mid_*`，docstring 说明两种方向 | 核上 24 例逐例 ok；A 段计数同步 |
| F3 证据脚本 `conversion family failures` 的 sed 只匹配 `f2i`（`f2.i`） | ✅已修 | 改 `f2[if]` | 该检查 0 → PASS |
| F4 证据脚本「核上例数」「OF\|NX 数」grep 用带前缀的输出却查原表，且 `$` 锚被后续字段破坏 | ✅已修 | 改查源表 + 去锚 | 两条 `[PASS]`，实测 24 / 8 |
| F5 模型注入未纳入 `EXIT` trap，中断会留篡改 | ✅已修 | `restore_files` 跳过缺失备份；两次注入共用 trap | 两次注入均 md5 还原 |
| F6 x86 交叉检查漏 `-lm` | ✅已修 | 加 `-lm` | 12 方向 mismatch=0 |
| F7 `check-patch-tree` 全量 rc=2 系并行 qemu/gem5 任务在途（其补丁未重导出） | ⏸记录 | 未改他任务文件；chipyard 子集单独跑断言 | chipyard 2 组 23 补丁 errors=0；系列在干净树重放后两文件 md5 == 源码 |
| F8 `tests/inst/fp/convert.yaml` 的 `fo2ft_orri_rf`（RTZ）仍期望 `+Inf` | ⏸延后 | 属 `m13-testcases-011` 范围，任务书禁改 | 见完成区「新发现/坑」② |

**判决**：F1–F6 已修并复验；F7/F8 为跨任务/范围外登记项（非「遗留:无」）。

## 完成区

**测试结果**：证据脚本全量 `PASS=56 FAIL=1`（唯一 FAIL = `check-patch-tree` 整仓 rc=2，并行 qemu 任务在途未导出；chipyard 子集断言 0 错误）。`--self-test-inject`：RTL 注入「恒 ±Inf」⇒ 表 4 例红（RTZ 正/负、RDN 正、RUP 负）、`TOTAL failed=320`；模型注入 ⇒ 核上 4/24 红；两次均 `cp`+md5 还原后回绿。

**四档 × 正负（核上 `value`/`rf0` 低 5 位；mild = 中点上方 1 ulp，severe = ±fo 最大有限）**：
- RNE：正 `+Inf`/`OF|NX`、负 `−Inf`/`OF|NX`（severe 与 mild 同）
- RTZ：severe 正 `+ft_max`/`OF|NX`、负 `−ft_max`/`OF|NX`；mild 两侧 `±ft_max`/**`NX` 仅**
- RDN：severe 正 `+ft_max`/`OF|NX`、负 `−Inf`/`OF|NX`；mild 正 `+ft_max`/`NX`、负 `−Inf`/`OF|NX`
- RUP：severe 正 `+Inf`/`OF|NX`、负 `−ft_max`/`OF|NX`；mild 正 `+Inf`/`OF|NX`、负 `−ft_max`/**`NX` 仅**
- 4×2 交叉格与 hardfloat `RoundAnyRawFNToRecFN`、模型、x86 SSE（12 方向）逐格一致

**验收结果**：单元台 `fo2ft ovf` 30 例 table/hf/oracle 三方差 0，`f2f fo2ft` 740、`ft2fo` 740 三方 0 差，`TOTAL failed=0`；核上 `cvt_ff_ovf` 24 例 MISMATCH 0（≥8 例），四档×正负按名齐全、8 例 severe `rf0` 低 5 位 `0x14`；273 例 md5 `2d4d94651346ef673c5a855e024c1489`（期望值与核输出均同）；elab/Verilator rc=0 且 `%Error`=0；L2 rc=0；`check-index-blobs`/`check-source-state` rc=0；L1 定点补跑 12 项（fp-contract / case-ledger / tests-index / components / no-residue / knowledge-refs / vectors / component-changelog / spec-drift / asm-list-drift 均 0），红仅 `check-run-artifacts`/`check-temp-dirs`（offender 全为他任务）。
**修改文件**（`git status -uall` 含本任务书共 8 项，逐项一致）：本任务书；`components/chipyard/{README.md,changelog.md}`；`components/chipyard/patches/.../WumingFP.scala.patch`、`.../WumingFPUnitHarness.scala.patch`（`make_patch` 导出）；`tools/chipyard/fp_ref.py`、`fp_sweep.py`、`fp_unit/unit_run.py`。
**新发现/坑**：① 溢出按「无限指数范围舍入后再与 `ft_max` 比」判定 ⇒ 轻微溢出在 RTZ/正 RDN 下**不置 `OF`**（只 `NX`），x86 与 hardfloat 同证；② `tests/inst/fp/convert.yaml` 的 `fo2ft_orri_rf`（RTZ）期望仍 `+Inf`（属 `m13-testcases-011`，QEMU 改好后该例必红）；③ `check-patch-tree` 无按组件过滤，只能整仓跑。
**遗留问题**：`check-patch-tree` 全量 rc=2 来自并行 qemu / gem5 任务在途（其工作树 commit 与已导出补丁不一致），不属本任务改动；重试 3 次，每次红项均指向在途组件，本任务 chipyard 子集始终 0 错误（2 组 23 补丁），且补丁系列在干净树重放后两文件 md5 与源码相等。

