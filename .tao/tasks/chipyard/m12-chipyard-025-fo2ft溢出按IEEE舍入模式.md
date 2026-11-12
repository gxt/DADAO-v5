# m12-chipyard-025: `fo2ft` 溢出按 IEEE 舍入模式（RTL + 模型）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m13-spec-002`（已合入）+ `m12-chipyard-014`（已合入）
**可并行分片**：否（单核实现，单写者）
**状态**：已验证

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

### 第 1 轮 engineer 自审（ISS-402 后重做）

**审查方式**：逐行读 `git diff`（7 实现文件 + 本任务书）；对照 `spec/SimRISC-07 §1.4` 定稿表与 IEEE 754-2019 §7.4 逐格核；证据脚本全量 + 注入自检两轮；补丁系列在 master 临时树（`--detach 9f32fbfe`）重放。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `unit_run` 的 `FT_MAX_Q` 用位型当数值算阈值、`ovf_unbounded` 忽略符号 ⇒ 8 例误判 | ✅已修 | `0xFFFFFF·2^104`；RUP/RDN 幅值上舍按符号分派 | 40 例 table-diff=0 |
| F2 「中点下」对照例误叫 `noovf`（RUP 正 / RDN 负 / RNA 仍溢出） | ✅已修 | 改名 `fo2ft_mid_*` 并写清两个方向 | 核上 38 例逐例 ok |
| F3 证据脚本 `conversion family` 的 sed 只匹配 `f2i` | ✅已修 | 改 `f2[if]` | 该检查 0 → PASS |
| F4 证据脚本两处 grep 用带前缀输出查原表、`$` 锚被破坏 | ✅已修 | 改查源表 + 去锚 | 两条 PASS（38 / 18） |
| F5 模型注入未纳入 `EXIT` trap | ✅已修 | `restore_files` 跳过缺失备份；两次注入共用一个 trap | 两次 md5 均还原 |
| F6 x86 交叉检查漏 `-lm` | ✅已修 | 加 `-lm` | 12 方向 mismatch=0 |
| F7 四档覆盖缺 RNA 双向与动态档，未达「18 格」 | ✅已修 | 核心组补 RNA 全形状 + 动态 `0x20`×`rf0[33:32]` 四码×双向（24→38 例）；`fcsr_after` 支持动态码 | 核上 38 例 MISMATCH 0 |
| F8 单元台只比 hardfloat 的值、未比标志 | ✅已修 | 加 `hf-flag-diff` 汇总与断言；补「恰为 `ft_max`」两形状（30→40 例） | `hf-flag-diff=0`；`ftmax` 例 `0x00` |
| F9 `check-patch-tree` 整仓 rc=2 | ⏸记录 | 未改他任务文件；按组件单独跑 | chipyard 2 组 23 补丁 errors=0（任务树 + master 临时树） |
| F10 `tests/inst/fp/convert.yaml` RTZ 例 | ⏸转交 | 属 `m13-qemu-005`（已改）与 `m13-testcases-011` | 见完成区「遗留问题」 |

**判决**：F1–F8 已修并复验；F9/F10 为跨任务/范围外登记项（非「遗留:无」）。

### 第 1 轮 reviewer 验收（2026-11-12）

**文件分析**：逐行读 8 个改动文件 `git diff`（任务书、`components/chipyard/{README,changelog}`、两份 `wuming` 补丁、`fp_ref.py`、`fp_sweep.py`、`fp_unit/unit_run.py`）+ 共享源树 `WumingFP.scala` 舍入原语 + `spec/SimRISC-07 §1.4` + IEEE 754-2019 §7.4 原文；`unit_run.ovf_unbounded` 以 `Fraction` 精确独立推导，非恒真、可达 FAIL（注入证实）。

**重跑记录**（workdir=仓库根，退出码取 `cmd; echo $?`；日志落 `.work/log/chipyard/m12-chipyard-025-reviewer-*.log`）：
1. `git status --porcelain -uall && git diff --stat` ⇒ **8 文件 / 276 insertions(+), 59 deletions(-)**（与声称一致；本段为追加本审阅记录之前的快照，追加后为 8 文件 / 295(+), 59(−)）；主工作树 `master` 的 `git status -uall`、`git diff` 均空 ⇒ 主树干净；分支停在基线 `3e4f218a`、全部未 commit。
2. `bash .work/evidence/m12-chipyard-025/run.sh` ⇒ `RUNSH_EXIT=1`、`summary: PASS=61 FAIL=1`（逐项与完成区一致）：唯一红 `check-patch-tree rc actual=2`；elab/Verilator rc=0 且 `%Error`=0；L2 rc=0；`index-blobs`/`source-state` rc=0；`f2f fo2ft ovf: 40 vectors | table/hf-value/hf-flag/oracle=0`；`f2f fo2ft`/`ft2fo` 各 1000 三方 0 差；核上 38 例 `MISMATCH 0`、severe 18/18 `rf0` 低 5 位 `0x14`、`cvt_ff` 27 例逐字节；273 md5 `2d4d94651346ef673c5a855e024c1489`。
3. 逐格核（我方抄录）：核心 38 行 + 单元台 40 行（8 形状×5 档）全合 spec 表——`RUP 负` sev `−ft_max/0x14`、mild `−ft_max/0x10`；`RDN 正` sev `+ft_max/0x14`、mild `+ft_max/0x10`；`RTZ` 双向 mild `±ft_max/0x10`；恰为 `ftmax` 10 行全 `0x00`；`dyn0..3` 的 `rf0[33:32]`=00/01/10/11 且逐例等于 RNE/RTZ/RDN/RUP 静态档。
4. x86 SSE 独立 32 格（8 形状 × RNE/RTZ/RDN/RUP，`fesetround`+`fetestexcept`）与模型 `mismatch=0`；实测 mild 的 RTZ/正 RDN/负 RUP = `--|NX`（无 OF），恰为 `ft_max` 四档**无任何异常位**。
5. `run.sh --self-test-inject` ⇒ `INJECT_EXIT=0`：RTL 注入 `table-diff=4`、`unit total failures=320`，还原 md5 `a3fd385f…` 回绿；模型注入 `8/38 mismatch`，还原 md5 `fb953019…` 回绿。
6. reviewer 独立注入（`f2f_exact` 改「精确值 > `ft_max` 即 OF|NX」，`cp`+md5 备份）⇒ `ONLY=B` `x86 mismatch=4` FAIL、`ONLY=E` `MISMATCH 12` FAIL（均 exit=1）；还原后 `ONLY=B` `PASS=3 FAIL=0`、`ONLY=E` `PASS=10 FAIL=0`（exit=0），`git status` 仍 8 文件、md5 `fb953019…`、无 `.inj-bak` 残留。
7. QEMU 对照（安装根 `qemu-system-dadao`，md5 `5654343d…` == build）：`cvt_ff_ovf` ⇒ QEMU == 核 == 模型 `0b67961d…`（608 B、**38/38 逐字节同**，含 18 severe + 4 轻微 + 10 中点 + 8 动态）；`cvt_ff` ⇒ `dae15ff9…` 27 例同（`fo2ft_rtz_ovf=0x7F7FFFFF`）⇒ **轻微溢出 QEMU 同样支持，无覆盖缺口**。
8. `python3 tools/infra/make_patch.py chipyard`（真跑）⇒ `0 written, 21 unchanged` + `0 written, 2 unchanged`；全树 md5 与 `git diff` md5 前后不变。

**约束核验**：独立 worktree ✓ 未 commit ✓ 8 文件 == 完成区（`ISS-377`）✓ 完成区 17 行 ≤30、无宿主绝对路径 ✓ 计数全为现场值 ✓ 只动任务书范围（未碰 QEMU/gem5/spec/向量册）✓ 注入 `cp`+md5 还原 ✓。
**偏离（不阻断）**：① `check-patch-tree rc=2` 根因已定位——任务分支基线 `3e4f218a` 早于 `m13-qemu-005`（12:03 合入）与 `m13-gem5-007`（审查期间合入），任务树内 qemu/gem5 补丁落后于共享源树（`merge-base --is-ancestor 91d8591c HEAD` ⇒ 非祖先），故 2 qemu + 4 gem5 红；主树（`master`）同刻仅剩 **chipyard 4 红 = 本任务未合入**、qemu/gem5 均绿，且任务树内 chipyard 子集 0 错误 ⇒ 非本交付物缺陷，合入后须复跑确认全绿。完成区「6 项全是并发在途」的归因对 qemu 不准（属基线过旧），文档级待改。② 完成区与 `fp_sweep.QEMU_GROUPS` 注释称「QEMU 仍恒 ±Inf、未落地」已过时（实测 38 例全同）⇒ 文档级，architect 收尾改；向量覆盖缺口按 `ISS-403③` 归 `m13-testcases-011`。
**采信未重跑**：无（上列数字全部出自我方终端输出）。
**判决**：**Accepted** —— 除上述跨任务/环境红项外，验收命令在我方重跑下全绿；语义按 IEEE 754-2019 §7.4「以无界指数按所选方向舍入后 > `ft_max` 才置 OF」实现，RTL / hardfloat / 精确模型 / x86 硬件 / QEMU 五方互证。

## 完成区

**测试结果**：证据脚本全量 `PASS=61 FAIL=1`（唯一 FAIL = `check-patch-tree` rc=2，红项为 qemu `helper.c` / gem5 `b7.cc|b7_test.cc` = 并行任务在途；chipyard 子集 `2 组 23 补丁 errors=0`，在 master 临时树重放仍 0）。`--self-test-inject`：RTL 注入「恒 ±Inf」⇒ 4 例 TABLE 红（RTZ 正/负、RDN 正、RUP 负）、`TOTAL failed=320`；模型注入 ⇒ 核上 8/38 红；两次均 `cp`+md5 还原回绿（`a3fd385…` / `fb95301…`）。

**四档 × 正负（核上 `value`/`rf0`；sev = ±fo 最大有限，mild = 中点上方 1 ulp）**：
- RNE/RNA：正负 sev+mild 全 `±Inf`/`OF|NX`
- RTZ：sev 正 `+ft_max`、负 `−ft_max`（`OF|NX`）；mild 正负 `±ft_max`/**`NX` 仅**
- RDN：sev 正 `+ft_max`、负 `−Inf`（`OF|NX`）；mild 正 `+ft_max`/**`NX` 仅**、负 `−Inf`/`OF|NX`
- RUP：sev 正 `+Inf`、负 `−ft_max`（`OF|NX`）；mild 正 `+Inf`/`OF|NX`、负 `−ft_max`/**`NX` 仅**
- 动态 `0x20`：`rf0[33:32]`=00/01/10/11 逐双符号同 RNE/RTZ/RDN/RUP，`rf0` 保留模式位（如 `0x7FF800017FC00014`）
- 恰为 `ft_max`：五档全 `ft_max`/`0x00`（阈值开区间 + 精确 ⇒ 无 OF 无 NX）
- 与 hardfloat（值+标志）、模型、x86 SSE（12 方向）逐格一致

**验收结果**：单元台 `fo2ft ovf` 40 例 table/hf-value/hf-flag/oracle 四差 0、`TOTAL failed=0`；`f2f fo2ft`/`ft2fo` 各 1000 三方 0 差；核上 `cvt_ff_ovf` 38 例 MISMATCH 0（severe 18 例 `rf0` 低 5 位 `0x14`）、`cvt_ff` 27 例逐字节一致；273 例 md5 `2d4d94651346ef673c5a855e024c1489`（期望与核输出同）；elab/Verilator rc=0 且 `%Error`=0；L2 rc=0；`check-index-blobs`/`check-source-state` rc=0；`make_patch chipyard` ⇒ `0 written, 2 unchanged`。
**修改文件**（`git status -uall` 8 项，逐项一致）：本任务书；`components/chipyard/{README.md,changelog.md}`；`components/chipyard/patches/.../WumingFP.scala.patch`、`.../WumingFPUnitHarness.scala.patch`；`tools/chipyard/fp_ref.py`、`fp_sweep.py`、`fp_unit/unit_run.py`。
**新发现/坑**：① 溢出判定 = 「无限指数范围舍入后再与 `ft_max` 比」⇒ 轻微溢出在 RTZ / 正向 RDN / 负向 RUP 下**只置 `NX`**；② 上一轮改动实际落在主工作树（已按 `cp`+md5 备份后恢复干净）；master `9f32fbfe` 误带本任务书旧完成区，合并须以本版为准；③ `check-patch-tree` 无按组件过滤，且共享 `.work/source` 只反映最后落盘任务 ⇒ 并行期整仓必红；④ 运行期脚本执行中不得编辑（bash 增量读，会 `syntax error`）。
**遗留问题**：`check-patch-tree` 整仓 rc=2（6 项全指向 qemu/gem5 在途改动，重试 3 次同）；`tests/inst/fp/convert.yaml` RTZ 溢出例由 `m13-qemu-005` 改、8+ 例矩阵归 `m13-testcases-011`；`cvt_ff` 组仍在 `QEMU_GROUPS`，QEMU 侧未落地前其 ovf 例为已知差异。

#### 收尾（architect，2026-11-12 13:35）

- reviewer **Accepted**：盘上自证成立（8 文件 / `276+/59-`）、**主工作树干净**；证据脚本 `PASS=61 FAIL=1`（唯一红 `check-patch-tree`，见下）；`fo2ft ovf` 40 例三方 0 差、`f2f` 各 1000 例 0 差、核上 38 例 mismatch 0；273 md5 不变；L2 rc=0。
- **轻微溢出语义双证**：RTL `common_overflow = (sRoundedExp >> (oe-1)) >= 3` 是**加进位后**再判（无界舍入后比较），与 `fp_ref` 同式；x86 SSE 32 格 mismatch 0；「恰为 `ft_max` ⇒ 四档无任何异常位」也符合 IEEE。
- **QEMU 已对齐（修完成区旧表述）**：`cvt_ff_ovf` **38/38** 与核、模型逐字节全同（含 18 severe + 4 轻微 + 10 中点 + 8 动态）⇒ 轻微溢出 QEMU 同样支持，无实现差异。
- **`check-patch-tree` 红因已更正**：任务分支基线 `3e4f218a` 早于 `m13-qemu-005`/`m13-gem5-007` 两次合入 ⇒ 任务树内 2 qemu + 4 gem5 补丁落后于共享源树（**基线过旧**，非「并发在途」）；chipyard 子集 0 错误，合入后需复跑全绿。
- 遗留转 `ISS-404`：完成区与 `fp_sweep.QEMU_GROUPS` 注释仍称「QEMU 恒 ±Inf、未落地」，已过时（QEMU 12:03 已合入）。

