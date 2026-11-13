# m13-testcases-032: `rootn(±0,2)=+0`、结果 NaN canonical、quiet compare sNaN 的 `NV` —— 向量与三平台实测

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-spec-007`（口径定稿）+ `m13-qemu-009` + `m12-chipyard-030` + `m13-gem5-011`（期望落定后实测三平台）
**可并行分片**：否（共享 `tests/inst/fp/`）
**状态**：待开始

**预估**：3–4 h

## 用户裁定（2026-11-13，落盘 `.tao/knowledge/discussing.md`）

1. **R1**：`rootn(±0,2)` = IEEE `+0`（§9.2.1；NOTE：`rootn(−0,2) ≠ squareRoot(−0)`）。
2. **R2**：结果 NaN 统一 canonical qNaN（符号 0、payload 全零；ft `0x7FC0_0000`、fo `0x7FF8_0000_0000_0000`）。
3. **D1**（2026-11-12）：「改为置 NV（跟 IEEE）」——quiet compare（`ftqcmp`/`foqcmp`）遇 sNaN 置 `NV`，只含 qNaN 不置。

审计来源：`docs/TestReports/M13-FP-IEEE对齐审计.md` §D1 / §D2 / §D3（含 P4/P6/P8 行为模式表）。

## 背景

- 既有向量**没有** `rootn(±0,2)` 例（`tests/inst/fp/divrem.yaml` 的 `foroot`/`ftroot` 组无 ±0 源）。
- 既有向量**部分 pin 住 QEMU 的 NaN 传播**：如 `divrem.yaml` 的 `forem qNaN rem 2.0 ⇒ rd5 = 0x7FF8_0000_0000_0123`（payload 传播）——与 R2 冲突，须改 canonical。
- 既有 quiet+sNaN 四例（`arith.yaml`）的「左/右」两方向**机器状态相同**（`ISS-407`：`set.w` 为 wyde 部分写、写序可交换，NaN 实际都在同一操作数）⇒ 需补**真实右操作数**独立用例。

## 范围（只改 `tests/`）

1. **R1 向量**（`tests/inst/fp/divrem.yaml`）：`foroot`/`ftroot` 各补 `−0` 输入例 ≥1、`+0` 对照 ≥1：
   - 期望 `+0`（ft 侧低 32 位 `0x0000_0000`、符号 0；高 32 位按该例装载值，逐例在 `notes` 写清装载与读回路径）
   - `rf0[4:0] = 0`（`rd6` 只含复位 qNaN 位，即 `0x7FF8_00007FC00000`）
2. **R2 向量**（`arith.yaml` / `scaleb.yaml` / `convert.yaml` / `divrem.yaml`）——「结果 qNaN ⇒ canonical」至少覆盖：
   - 算术：`ftadd`/`foadd`（或 sub/mul/div）带 payload **且负号** qNaN 输入 ⇒ `0x7FC0_0000` / `0x7FF8_0000_0000_0000`（符号清 0）
   - scaleB：`ftsclb(qNaN 带 payload, n)` ⇒ canonical
   - 转换：`fo2ft(0xFFF8_0000_0000_0123)` ⇒ `0x7FC0_0000`；`ft2fo(qNaN 带 payload)` ⇒ `0x7FF8_0000_0000_0000`
   - 取余：既有 `forem` qNaN 传播例改 canonical
   - **排除项对照（不得改）**：`ft2ft`/`fo2fo` 复制带 payload NaN ⇒ 位型原样；`foscmp(qNaN)` ⇒ `0x7F80_0001` + `NV=1`
3. **D1 向量**（`arith.yaml`）：quiet compare 遇 sNaN 的**左/右两个真实方向**各有独立用例（`ft`/`fo` 各 ≥2，共 ≥4），期望 `NV=1`、结果 canonical qNaN；`qNaN` 对照 `NV=0`。构造要求：两操作数须落在**不同寄存器**、经**非重叠**写序装入（避免 `ISS-407` 的「两例机器状态相同」），并在 `notes` 写明两侧实际值。
4. **全量清扫**：扫描 `tests/inst/fp/*.yaml` 中结果为**非 canonical qNaN**（`rd5`/`rf` 期望 payload≠0 或符号 1）的项 ⇒ 逐条改 canonical；完成区给出 `grep` 命令与命中数（现场值，不写死）。
5. **索引同步**：`tests/case-ledger.tsv` 重生成（`--write`）；`tests/inst/inventory.md` 若门控/覆盖表要求则同步；每文件检查点 ≤127、点号连续。
6. **三平台实测**（期望为准，逐点记录三方位型）：
   - QEMU：`make check-inst`（Vast 全量 + Tiny 子集）
   - gem5：`tools/gem5/check_b7.py --vectors`（指令路径探针 / `b7_ref` 差分）
   - chipyard：`tools/chipyard/fp_unit/unit_run.py` + `tools/chipyard/fp_sweep.py`
   - 某平台未重建/未合入 ⇒ 标 **BLOCKED（原因 + 替代证据）**，禁写「推定一致」

**非范围**：不改实现（`components/**`）、不改 `tools/**` 模型（`fp_ref.py`/`b7_ref.py` 归实现册）、不改 spec/合约。

## 前置（`m13-testcases-021` 已定位根因，2026-11-14）

- 既有唯一红 `divrem.yaml[23]` 的根因已查明：该用例是「`forem` 收到 qNaN、余数 2.0」时**期望 NaN payload 传播**，而 `spec/SimRISC-07 §1.4` 规定 NaN 结果**一律 canonical**；三平台实现均按 canonical ⇒ **是 YAML 旧口径错，不是实现缺陷**。本任务应按 spec 改该 YAML 期望（或按 `030` 口径迁到 `.S`）。
- 另发现一处 **spec 内部不一致**：`spec/SimRISC-07 §2.1` 余数表注「符号随 rfHC」对**非零结果**不成立（三平台实测一致）。属 spec 措辞问题，需用户裁定后另行修订；本任务**不改 spec**。

## 验收标准（可执行、可失败）

1. 新增/修改用例数、每文件检查点号区间、`grep` 命中数：**全部现场统计**并贴出处。
2. `make check-inst` rc=0（Vast/Tiny 计数取现场）；整数 273 例 emit md5 与基线一致（FP 改动不应触及，现场核对）。
3. **三平台逐点一致**：每条新/改语义点给出「QEMU / gem5 / chipyard」三方位型 + 与 spec 期望比对结论；不一致项如实记红并登记 issue（**不得放宽期望**）。
4. **可达 FAIL 注入**：把一条 canonical 期望改回带 payload（如 `0x7FC0_0001`）⇒ 对应用例红；`cp`+md5+`touch` 还原 ⇒ 回绿；再任选一条 root `−0` 期望改回 `0x8000…` ⇒ 红的必须是同一条。
5. 期望派生声明：每条新期望的 `notes` 写明 spec 引用（`SimRISC-07 §1.4` / `§2.2` / `§4` + IEEE 条文）与反算方式（`tools/chipyard/fp_ref.py` 精确 oracle 或手写有理数推导），**不得**从 QEMU/gem5/RTL 输出抄期望。
6. 一键证据脚本 `.work/evidence/<任务ID>/run.sh` `rc=0`；完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账。

## 说明

- `ft` 的 `set.w` 为 wyde 部分写、写序可交换（`ISS-407` 根因）⇒ 构造「sNaN 在右」须换寄存器或用整字宽装载，并在 `notes` 给出实测寄存器值佐证。
- 若 `m13-gem5-011` 的转换 canonical 项（其「待裁定 Q1」）另立册，则 `fo2ft`/`ft2fo` 的 gem5 侧比对标 BLOCKED，其余两点照常收口。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需用户语义裁定写进任务书「待裁定」段返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir（仓库根），用相对路径；临时文件放 `/tmp/opencode/<任务ID>/`。
9. 沿用 `012` 系列既有 hmon 自装 workaround（若仍需要，按现场状态说明）。

## 审阅记录

（待填）
