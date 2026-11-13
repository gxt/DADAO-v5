# m13-spec-007: `rootn(±0,2)=+0`、结果 NaN 统一 canonical、比较族 `NV` —— spec 与合约定稿

**模块**：spec
**项目里程碑**：M13
**依赖**：无（本族第一个；`m13-qemu-009` / `m12-chipyard-030` / `m13-gem5-011` / `m13-testcases-032` 等它定稿）
**可并行分片**：否（单册单写者，`spec/SimRISC-07` + `SimRISC-00` + `contract-fp`）
**状态**：待开始

**预估**：2–3 h

## 用户裁定（2026-11-13，落盘 `.tao/knowledge/discussing.md`）

> 「已裁定：`rootn(±0,2)` 收严为 `+0`；NaN 结果统一 canonical（2026-11-13）」

1. **R1**：`rootn(±0,2)` 收严为 IEEE `+0`（IEEE 754-2019 §9.2.1：`rootn(±0, even n>0) = +0`；该节 NOTE 明确 `rootn(−0,2) ≠ squareRoot(−0)`）。
2. **R2**：结果 NaN 统一 **canonical quiet NaN**（payload 全零、符号 0；ft `0x7FC0_0000`、fo `0x7FF8_0000_0000_0000`）。依据：IEEE §6.2.3 payload 传播只是 *should*、§6.3 不规定结果符号 ⇒ canonical 是 IEEE 允许的取值，**不构成偏离**；Berkeley hardfloat 即 canonical。
3. **D1**（2026-11-12 裁定「改为置 NV（跟 IEEE）」）：quiet compare 遇 sNaN 置 `NV`，随本任务补 spec 条款。

审计来源：`docs/TestReports/M13-FP-IEEE对齐审计.md` §D1 / §D2 / §D3 + 文档级 F1。

## 背景（现场原文）

- `spec/SimRISC-07 §2.2`（S1D1）现写：「对于 `rootn(-0, 2)` 的运算结果不做具体要求」——未标注为有意偏离、未给理由。
- `spec/SimRISC-07 §1.4` 现写 `fo2ft`「NaN 传播 payload」，未定义「结果 NaN 的 payload / 符号位」的取值（全册缺口）。
- `spec/SimRISC-07 §4`（比较族）只写结果值与「qNaN/sNaN 符号位为 0」，**无 `NV` 条款**（`contract-fp §8` 同缺）。
- `contract-fp §6` 逐字写「不做具体要求」；`§16 开放点` 仍把该条列为未定。

## 范围（只改 spec 与合约）

1. **`SimRISC-07 §2.2` 收严 R1**：`ftroot`/`foroot` 与平方根运算相同，**唯一例外**为零的符号——按 IEEE 754-2019 §9.2.1，`rootn(±0,2) = +0`（NOTE：`≠ squareRoot(−0)`）；源为 `±0` ⇒ 结果 `+0`，不置任何标志；删除「不做具体要求」。
2. **`SimRISC-07 §1.4` 写 R2（承载点为 §1.4，口径为全册适用）**：
   - 结果应为 **quiet NaN** 的一切情形 ⇒ canonical qNaN（符号 0、payload 全零）：算术（add/sub/mul/div）、scaleB、root、remainder、融合乘加、取整、最小最大（双 NaN）、格式转换 `fo2ft`/`ft2fo`、比较的 **quiet** 无序结果、以及任何无效操作产生的 qNaN。
   - **不适用（须逐项写明）**：`ft2ft`/`fo2fo` 复制类（纯位搬移、不改位、不置标志）；signaling compare 的无序结果（保持 **signaling** NaN 位型、符号 0）；`ftmin`/`ftmax`/`fomin`/`fomax` 的单 NaN 情形（返回那个数）。
   - sNaN 作输入 ⇒ 仍按各节规则置 `NV`，结果取 canonical qNaN。
   - 须写清「取 canonical 是 IEEE 允许的实现选择（§6.2.3 *should*、§6.3 不规定），**不是**有意偏离」——避免与册首「显式标注的有意偏离」机制混淆。
   - 同时删/改 §1.4 中 `fo2ft`「NaN 传播 payload」的措辞，使其不再与本条冲突。
3. **`SimRISC-07 §4` 补 `NV` 三条**（IEEE 754-2019 §5.6.1 / §5.11）：signaling compare 只要**无序**（sNaN 或 qNaN 操作数）即置 `NV`；quiet compare **仅** sNaN 操作数置 `NV`，只含 qNaN ⇒ 安静无序、不置标志；有序不置。比较只可能置 `NV`，不置 `DZ`/`OF`/`UF`/`NX`，标志 sticky 写入 `rf0[4:0]`。
4. **`SimRISC-00` 附录变更记录**：在顶部 `-rc` 段追加（聚合写法、不带任务号）：`rootn(±0,2)=+0`；结果 qNaN 统一 canonical（含不适用清单）；比较族 `NV`。
5. **`contract-fp` 投影同步**：`§6 root` 改写第 3 条；`§8 compare` 补 `NV` 两条 + quiet 无序结果 canonical；在合适处（`§1 全局环境`）补「结果 qNaN 一律 canonical」一条并在各节引用；`§16 开放点` **删除** `rootn(-0,2)` 条（不再未定）。
6. **版本与只读锁**：版本互锁组 `SimRISC-00`…`12` 组内一致；现状 `SimRISC-07`/`SimRISC-00` 均为 `0.5.7-rc`（未发布）⇒ 按既有做法**并入该 `-rc` 段、版本号不变**；若施工时该 `-rc` 已发布，则新开 `x.y.(z+1)-rc` 并 13 册册头同步升版（现场勘定，不猜）。`manifests/spec-readonly.lock.toml` 中 `SimRISC-00`/`SimRISC-07` 两行 sha256 **同笔**更新。

**非范围**：不改任何实现（`components/**`）、不改向量（`tests/inst/**`）、不改 `contracts/fp_semantics.yaml`（除非 `check-fp-contract` 现场要求同步，改动须在完成区说明）、不新增 signaling compare 的 sNaN 位型收紧（见「说明」）。

## 验收标准（可执行、可失败）

1. **残留清扫**：`git grep -n "不做具体要求" -- spec/ .tao/contracts/` ⇒ **0 命中**；`contract-fp §16` 无 `rootn` 条。
2. **条款在场**（证据脚本断言，逐条打印命中行）：
   - `§2.2` 含 `+0` 与 `§9.2.1`（或 `9.2.1`）字样，且含「不置任何标志」；
   - `§1.4` 含 `0x7FC0_0000` 与 `0x7FF8_0000_0000_0000`（或等价无下划线写法，断言须两种写法都接受）与「不适用」清单三项；
   - `§4` 含「signaling」（无序即置）、「quiet」（仅 sNaN）、「有序」三档 + `NV`；
   - `contract-fp §6/§8` 与 spec 同口径（逐条 grep 关键串）。
3. **门控**：`check-spec-readonly` / `-changelog` / `-drift` / `-numbering` / `-refs` / `-purity` / `-codeblocks` / `-cite-targets`（按现场可用目标逐一 `rc=0`）+ `check-fp-contract` + `check-knowledge-refs` 全 `rc=0`。
4. **锁**：现场重算 sha256 与锁文件逐行 MATCH（册数/命中数取现场输出，不写死）。
5. **可达 FAIL 注入（≥2 路）**：① 把 `§2.2` 改回「不做具体要求」⇒ 验收 1 红；② 把 `§1.4` 的 canonical 位型改成带 payload（如 `0x7FC0_0001`）⇒ 验收 2 红；③（可选）删 `§4` quiet 行 ⇒ 验收 2 红。每路均 `cp`+md5+`touch` 还原 ⇒ 回绿。
6. **一键证据脚本**：`.work/evidence/<任务ID>/run.sh`（含上述断言与注入自检），`rc=0`；复杂输出留 `.work/log/<模块>/`。
7. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 逐项对账。

## 措辞草案（提案，engineer 定稿并按门控调整；不得含任务号/里程碑号）

`§2.2`：

> `ftroot`/`foroot` 实现 `rootn(x, 2)`，与 `ftsqrt`/`fosqrt` 的运算相同，**唯一例外**是零的符号：IEEE 754-2019 §9.2.1 规定 `rootn(±0, 2) = +0`（该节 NOTE 明确 `rootn(−0, 2)` 与 `squareRoot(−0) = −0` 不同），本册按 `rootn` 语义取 **`+0`**：源为 `+0` 或 `−0` 时结果一律为 `+0`，不置任何标志。

`§1.4`（NaN 结果，全册适用）：

> **NaN 结果的取值**：凡结果应为 quiet NaN 的情形（算术、缩放、开方、取余、融合乘加、取整、最小最大、格式转换，以及比较的 quiet 无序结果与一切无效操作产生的 qNaN），一律返回 **canonical quiet NaN**——符号位 0、payload 全零，即 ft `0x7FC0_0000`、fo `0x7FF8_0000_0000_0000`；sNaN 作输入仍按各节置 `NV`。**不适用**：`ft2ft`/`fo2fo` 复制（纯位搬移、不置标志）；`ftscmp`/`foscmp` 的无序结果（signaling NaN 位型、符号 0）；`ftmin`/`ftmax`/`fomin`/`fomax` 的单 NaN 情形（返回那个数）。IEEE 754-2019 §6.2.3 对 payload 传播只是 *should*、§6.3 不规定 NaN 结果的符号位，取 canonical 属 IEEE 允许的实现选择，**不是**有意偏离。

`§4`：

> **异常标志**（IEEE 754-2019 §5.6.1 / §5.11）：Signaling Compare（`ftscmp`/`foscmp`）只要比较**无序**（任一操作数为 sNaN 或 qNaN）即置 **`NV`**；Quiet Compare（`ftqcmp`/`foqcmp`）**仅**在操作数含 **sNaN** 时置 **`NV`**，只含 qNaN 时为安静的无序结果、不置任何标志；有序比较不置标志。四条比较指令只可能置 `NV`，不置 `DZ`/`OF`/`UF`/`NX`，标志按累积（sticky）语义写入 `rf0[4:0]`。

## 说明

- 本任务只定措辞与合约投影；三实现与向量由后续 4 件承接。
- **signaling compare 的 sNaN 位型**（现 spec 只写「符号位为 0」，向量已钉 ft `0x7F80_0001` / fo `0x7FF0_0000_0000_0001`）：本任务**不**新增该收紧（避免超范围），只保证新条款不与之冲突；如需收紧另立小任务。
- 若判定本变更触及 ADR 判据（外部契约 / 多方案 / 结论固化），**先提醒主会话**再决定是否立 ADR；不擅自改已 `Accepted` 的 ADR。
- 改 `spec/` 的授权已在用户 2026-11-13 裁定中给出（落盘见上）；只读锁同笔更新。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需用户语义裁定写进任务书「待裁定」段返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir（仓库根），用相对路径；临时文件放 `/tmp/opencode/<任务ID>/`。
9. `spec/SimRISC-*` 正文禁任务号/里程碑号/`ISS` 号（`check-spec-purity`）。

## 审阅记录

（待填）
