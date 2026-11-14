# m13-testcases-035: 07 浮点补边界（余数零符号 + 无符号 f2i 负向）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-021`（余数族已建）、`m13-testcases-022`（f2i 族已建）
**可并行分片**：否（`tests/inst` 串行）
**预估**：1–2 h
**状态**：待开始

## 背景（两处规范裁定后的用例缺口）

1. **余数零符号**（`spec/SimRISC-07 §2.1`，2026-11-14 裁定「完全按 IEEE 754-2019 §5.3.1」）：
   - 非零余数符号由 `rfHC − n×rfHD` 决定（可与 `rfHC` 相反）——`021` 已有覆盖；
   - **余数为零时取 `rfHC` 的符号**——**当前无用例**（`+4 rem 2 = +0`、`−4 rem 2 = −0`、`+0 rem 2 = +0`、`−0 rem 2 = −0`）。
2. **无符号 f2i 的负向饱和**（`spec/SimRISC-07 §1.4`，2026-11-14 裁定「与 hardfloat/RISC-V 一致」）：
   - `NaN`/`+Inf`/正溢出 ⇒ 最大无符号值、`−Inf`/负溢出 ⇒ **`0`**；
   - `022` 已覆盖 NaN（含负号 NaN）与正向，**负向（`−Inf`、负溢出 ⇒ 0）无用例**。

## 范围

- `tests/inst/07-floating-point/ftrem_orrr_rf.S`、`forem_orrr_rf.S`：补零余数符号 4 例（`ft`/`fo` 各 2）。
- `tests/inst/07-floating-point/` 的 4 条无符号 f2i（`ft2ut`/`ft2uo`/`fo2ut`/`fo2uo`）：各补「`−Inf` ⇒ 0」「负溢出 ⇒ 0」两例（至少 `ft2uo`/`fo2uo` 各 2 例，其余各 1 例）。
- 其余文件不动；不改 `contracts/`、`spec/`、`Makefile`。

## 验收

1. 新增检查点现场统计、点号连续 ≤127。
2. 三平台逐字节（chipyard == QEMU == gem5，同镜像），含新点；零余数的**符号位**必须逐字节核（`±0` 不能只看数值相等）。
3. 独立复算（自写，用 host `math.remainder` 的 IEEE 语义 + 显式符号位判定）。
4. `check-tests-index` / `check-case-ledger` / `validate_vectors`（gaps 0）/ 273 md5 / `check-generator-sync` / `check-inst`（红集恰 `{divrem.yaml[23]}`）。
5. ≥1 路注入（把 `−4 rem 2` 的期望从 `−0` 改成 `+0`）⇒ 三平台同点号红；`cp`+md5 还原回绿。
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree（分支 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/m13-testcases-035/`。
2. 不提交 git；`run_asm_suite` 用独占 work-dir（`ISS-431`）；节点跑批记录二进制 md5（`ISS-429`）。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 日志 `.work/log/testcases/<任务ID>-<用途>.log`。

## 待裁定

（实现中写）

## 审阅记录

（待填）
