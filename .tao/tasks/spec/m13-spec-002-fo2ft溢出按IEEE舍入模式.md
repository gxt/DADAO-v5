# m13-spec-002: `fo2ft` 溢出按 IEEE 舍入模式（spec 修订）

**模块**：spec
**项目里程碑**：M13
**依赖**：无（本族第一个，其余四项等它定稿）
**可并行分片**：否（单册单写者）
**状态**：已验证

## 背景（共同，5 个子任务共用）

用户 2026-11-12 定规则（`MEMORY.md`「DADAO 反套用清单」末条）：**浮点差分一律以 IEEE-754 2019 为准**，SimRISC 与各模拟器据此更新修订；「与既有实现一致」不构成保留依据。

**条款**：`fo2ft` 溢出。

- 现行 spec（`spec/SimRISC-07 §1.4`）+ `contract-fp §2`：溢出**恒**返回 ±Inf（置 `OF|NX`）
- IEEE 754-2019 §7.4：结果由**舍入方向**决定 —— `RNE` / `RUP`（向 +∞）⇒ ±Inf；`RTZ` / `RDN`（向 −∞）⇒ **±最大有限值**；两种情况都置 `OF|NX`
- hardfloat `RoundAnyRawFNToRecFN` 即按舍入模式给出，可作对照

已登记 `ISS-397`。

## 本任务目标（只改 spec 与合约）

1. `spec/SimRISC-07` 的 `fo2ft` 溢出描述改为按舍入模式分派（写清 `RNE`/`RUP` ⇒ ±Inf、`RTZ`/`RDN` ⇒ ±最大有限，均置 `OF|NX`）。
2. `spec/SimRISC-07` 补一句**规范性引用**：浮点行为以 **IEEE-754 2019** 为准；与本文冲突时以 IEEE 为准（存在有意偏离的，必须显式标注）。
3. `.tao/contracts/contract-fp.md` §2 同步（合约是 spec 的投影，不得反向定义语义）。
4. 版本按 `docs/Process-03`：`SimRISC-07` 版本号 + 附录条目；`manifests/spec-readonly.lock.toml` 同笔更新（只改该册一行 sha）。
5. `ADR`：若认定「原「恒 ±Inf」是有意设计」需要留痕，登记到 `.tao/knowledge/discussing.md` 与 ADR 候选；**不擅自改已 Accepted 的 ADR**（`ADR-0004` 之外若涉及 ADR-0050，逐条确认后才动）。

## 非范围

- 不改任何实现（chipyard / QEMU / gem5）
- 不改向量（`m13-testcases-011`）
- 不动其它 FP 语义（quiet+sNaN 已由 `qemu-004`/`chipyard-024` 处理）

## 验收标准

1. `spec/SimRISC-07` 的 `fo2ft` 条目逐条列出四档舍入的结果形态，且与 IEEE 754-2019 §7.4 一致
2. `contract-fp §2` 与 spec 一致（`git grep` 证无残留「恒 ±Inf」表述）
3. 5 个 spec 门控 rc=0（`check-spec-readonly` / `check-spec-changelog` / `check-spec-drift` / `check-spec-numbering` / `check-spec-refs`）+ `check-knowledge-refs`
4. 版本与锁同笔更新，`sha256` 实测 MATCH
5. 一键证据脚本（含可达 FAIL 注入：把「按舍入模式」改回「恒 ±Inf」⇒ 应 FAIL）
6. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- `.work` 必须软链（`ISS-389`）；spec 单写者。
- 本册定稿后，实现侧三册（`m12-chipyard-025` / `m13-qemu-005` / `m13-gem5-007`）才可派单。

## 硬约束（子代理必读）

1. 独立 `git worktree` 作业（分支名 = 任务号），禁改主工作树（`ISS-368`）；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
8. 命令作用域 = workdir（仓库根），用相对路径。

## 待裁定（ADR-0050 D5 适用范围；本任务未改 ADR）

**问题**：`ADR-0050`（`Accepted`）D5 原文「转换 inexact ⇒ 置 NX；NaN/Inf/超出目标范围 ⇒ 饱和（最大/最小）+ 置 NV，不置 NX」。本任务按 IEEE 754-2019 §7.4 把 `fo2ft` 溢出定为「按舍入方向给 `±Inf` 或 `±` 最大有限值，且置 `OF`+`NX`」。若 D5 被解读为**涵盖** `fo2ft` 的溢出，则 D5 与本修订冲突（D5：饱和 + `NV`、不置 `NX`；本修订：最大有限值/Inf + `OF` + `NX`）。
**自决（未改 ADR）**：D5 上下文是浮点→整数的饱和（饱和只在整型目标有意义；D5 同段「与 RISC-V `fcvt` 同口径」亦指 `fcvt`），故 `fo2ft` 溢出不受 D5 约束，spec/合约按 IEEE 执行。
**待用户裁定**：① 确认 D5 只适用于浮点→整数（维持现状，ADR 不动）；② 若认为 D5 涵盖 `fo2ft`，则需新开 ADR 逐条确认后修订（新语义决策，不在本任务范围）。

## 审阅记录

### 第 1 轮 engineer 自审

**审查方式**：逐行读 `git diff`（16 个实现文件 + 本任务书）+ 对照 IEEE 754-2019 §7.4 原文逐档核符号；重跑证据脚本两轮。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 版本升号连带 13 册册头 + 根 `README` 在研列 + 锁 13 行 sha，超出任务书「只改该册一行 sha」括注 | ✅按门控执行（披露） | 册头互锁是硬断言（`check-spec-changelog` 第 7 条；规则源 = `spec/README.md`「册维护约定」+ `docs/Process-06` 版本/归档段），单册升号必红 | `check-spec-changelog` rc=0，`simrisc_header_versions=['0.5.7-rc']` |
| F2 证据脚本 C1/C5 期望串与最终措辞不一致（首轮 2/13 FAIL） | ✅已修 | 脚本期望串同步为最终文本（动态档行、规范性引用句） | 末轮 13/13 PASS；`--inject` 6/13 FAIL → 还原 0/13 |
| F3 一次性锁更新脚本落在工作树内（未跟踪残留） | ✅已修 | 移至仓库外临时目录，`git status` 0 untracked | `git status --porcelain -uall` = 17 modified（16 个实现文件 + 本任务书）、0 untracked |
| F4 §2.5 融合乘加仍写「溢出 ⇒ 返回 `±Inf` 并置 OF」，与 IEEE §7.4 同类冲突 | ⏸延后 | 不在本任务范围（任务书要求登记不顺手改） | 见完成区「新发现/坑」②，建议另立任务 |
| F5 `check-spec-archive(-verify)` 在 worktree 缺 `.cache/refs` 时非零退出 | ✅绕过 | 只读软链既有 `.cache` 后重跑 | 两门控 rc=0（`0.5.7-rc` 按 `-rc` 跳过归档） |
| F6 §1.4 整数→浮点条仍写「超出目标格式范围 ⇒ ±Inf 并置 OF」 | ⏸延后（无实际冲突） | 8 条 i2f 的可表示范围均小于 ft/fo 上界（int64 最大 ≈9.2e18 ≪ 3.4e38），该分支不可达；语义不动 | 见完成区「新发现/坑」③ |

**判决**：F1/F2/F3/F5 已处置；F4/F6 属范围外登记项（已在完成区列明，非「遗留:无」）。

### 第 1 轮 reviewer 验收

**判决：Accepted**（6 条验收标准在 reviewer 独立重跑下全通过；4 条非阻断 finding 见末）

**重跑记录**（workdir = 仓库根，全部 reviewer 亲跑）
- 13 个门控 rc 全 0：`check-spec-readonly`（21 册 OK）／`-changelog`（`simrisc_header_versions=['0.5.7-rc']`）／`-drift`（9 合约 0 错）／`-numbering`／`-refs`／`check-knowledge-refs`／`check-fp-contract`／`-purity`／`-cite-targets`／`check-asm-list-drift`／`check-legality-drift`／`-archive`（声明 8／磁盘 9）／`-archive-verify`（`SKIP SimRISC-0.5.7-rc`）
- 一键证据脚本（`.work/evidence/<任务ID>/run.sh`）→ `RESULT: PASS (13/13)`，exit=0（与声称一致）
- 同脚本 `--inject` → `注入轮: 6/13 项 FAIL` → 还原 `0/13` → `RESULT: PASS`，exit=0（与声称一致）；md5 `7bd1590b…`／`2b93e9a3…` 前后相等
- **reviewer 独立注入**：把 `RDN` 负溢出 `−Inf`→`−ft_max`（`cp` 备份）→ 同一脚本 `RESULT: FAIL (3/13)`，exit=1，C1 精确点名 `RDN(+max/-Inf): MISSING`（matched=5/6）＋C7 sha MISMATCH＋C8 readonly FAIL → `cp` 还原、md5 相等 → `13/13 PASS`，exit=0
- 锁 sha 独立重算（现场 `tomllib` + `sha256`）：`MATCH 13  MISMATCH 0`，exit=0
- `git show --stat 78a82f4a` = 17 文件，与完成区「16 实现文件 + 本任务书」逐项相符；`git status --porcelain -uall` = 0 行（0 untracked）

**语义独立核验**（先按「精确结果符号 + 舍入方向」推，再对表）
- 四档 × 正负逐格：RNE／RNA `±Inf`；RTZ `±ft_max`；RUP 正 `+Inf`／负 `−ft_max`；RDN 正 `+ft_max`／负 `−Inf` ⇒ 与 spec 表**逐格一致**（IEEE「nearest 给 ±∞、定向舍入按舍入规则」互证）
- `ft_max`：p=24／emax=127 ⇒ `(2−2⁻²³)×2¹²⁷` = 3.4028234663852886e38，位型 `0x7F7F_FFFF`，+1ULP = inf，负 `0xFF7F_FFFF` ⇒ 公式与两值**正确**
- `OF`＋`NX` 两种结果都置；`UF` 仅 tiny 且 inexact（溢出 `|r| ≥ ft_max` 非 tiny）⇒ **不误置 `UF`**，两文件所有「溢出」处无一置 `UF`
- 动态档 `rf0[33:32]` `00/01/10/11` = RNE/RTZ/RDN/RUP 属**本任务未改的既有文**（父提交同文），spec 与 contract 一致、合 RISC-V `frm`；RNA 仅由静态 `0x02` 提供

**约束核验**：① 独立 worktree、分支 = `m13-spec-002` ✓；② 未 commit（HEAD 仍 `78a82f4a`）✓；③ 完成区 17 行 ≤30、计数均现场且我复算全一致 ✓；④ 越界（13 册册头 ＋ 锁 13 行 ＋ README）已在 F1 披露，必要性**实读证实** = `check_spec_changelog` 断言 7「组内版本必须一致」＋ `spec/README` z+1（0.5.6 已于 `9e9a9c3d` 发布，其后确有内容改动）✓
⑤ 一键证据脚本、6 条断言组均可达 FAIL、注入→FAIL→还原（`cp`+md5）→回绿 双向证实 ✓；⑥ `ADR-0050`／`discussing.md` 均未动（diff 无 `.tao/adr`、`discussing.md`）✓；⑦ 无运行期路径、命令用相对路径 ✓；⑧ `.work` 软链（ISS-389）✓

**finding（均非阻断，交 architect 定夺）**：
- R1 `§2.5` FMA（spec L270 ＋ contract L198）「溢出 ⇒ `±Inf` ＋ OF」与 §7.4 冲突、未标注偏离且**可达**；已被本任务册首规范性引用确定性从属（冲突以 IEEE 为准，非「有意偏离」故 IEEE 生效），正确修法须连带三实现 ⇒ **另立任务**（同 F4）
- R2 `§1.4` i2f 同类措辞（spec L71 ＋ contract L53）**不可达**（uint64 max 1.84e19 ≪ ft 3.40e38），证实 F6
- R3 完成区「`git status` = 17 modified」在 architect WIP 提交后已过期；改以 `git show --stat 78a82f4a` 对账，17 文件逐项相符（文档级）
- R4 无门控机械审「全册条目要么合 IEEE、要么显式标注偏离」（C5 只验引用句存在）⇒ 建议随 FP 族任务补一次审计

## 完成区

**测试结果**：证据脚本 13/13 PASS（rc=0）；注入「改回恒 ±Inf」6/13 FAIL → `cp` 还原（md5 对账 `7bd1590b…`/`2b93e9a3…`）→ 13/13 PASS（rc=0）。门控 rc 全 0：`check-spec-readonly`、`-changelog`、`-drift`、`-numbering`、`-refs`、`check-knowledge-refs`、`-purity`、`-cite-targets`、`check-fp-contract`、`check-asm-list-drift`、`check-legality-drift`、`-archive`、`-archive-verify`。

**修改文件**（`git status --porcelain -uall` = 17 modified（16 个实现文件 + 本任务书）、0 untracked）：
- `spec/SimRISC-07-浮点运算.md`（规范性引用 + §1.4 `fo2ft` 溢出四档表）
- `spec/SimRISC-00-指令系统设计.md`（册头 + 附录 `0.5.7-rc` 两条）
- `spec/SimRISC-01`…`SimRISC-12`（册头版本 → `0.5.7-rc`，各 1 行；互锁强制）
- `.tao/contracts/contract-fp.md`（§2 `fo2ft` 溢出投影）
- `manifests/spec-readonly.lock.toml`（13 行 sha + 变更注释）
- `README.md`（在研版本列 → `0.5.7-rc`）

**验收结果**：四档 × 正负（`fo2ft`，`ft_max`=`0x7F7F_FFFF`）：RNE `+Inf`/`−Inf`；RNA `+Inf`/`−Inf`；RTZ `+ft_max`/`−ft_max`；RUP `+Inf`/`−ft_max`；RDN `+ft_max`/`−Inf`；动态 `0x20` 按 `rf0[33:32]` 映射；无论 Inf 还是 `ft_max` 均置 `OF`+`NX`。锁 sha 实测 13/13 MATCH（`SimRISC-07` = `864a780e…`、`SimRISC-00` = `bd239031…`）。

**新发现/坑**：① 13 册册头互锁 ⇒ 任何单册语义修订都得同步 13 行锁 sha，「只改一册」在门控下不可行；② §2.5 融合乘加溢出仍「恒 ±Inf」（与 IEEE §7.4 同类冲突，建议另立任务修 spec + 三实现）；③ §1.4 整数→浮点的「超出目标范围 ⇒ ±Inf」分支对现有 8 条 i2f 不可达（无实际冲突，措辞可随后续一并收紧）；④ worktree 内跑归档门控需只读软链 `.cache`（否则 `check-spec-archive-verify` 报缺 `refs`）。

**遗留问题**：F4（`§2.5` 融合乘加溢出）与 F6（`§1.4` i2f 措辞）已登记未改；`ADR-0050 D5` 适用范围待用户裁定（见「待裁定」段），本任务未改任何 ADR。

#### 收尾（architect，2026-11-12 11:21）

- reviewer **Accepted**：13 个门控全 rc=0；证据脚本 13/13；锁 sha 独立重算 **MATCH 13 / MISMATCH 0**；`git show --stat` 17 文件与完成区相符。
- **12 格逐格复核通过**：reviewer 按「精确结果符号 + 舍入方向」独立推演，与表一致；`ft_max = (2−2⁻²³)×2¹²⁷ = 0x7F7FFFFF` 位型正确；`OF|NX` 两结果都置、`UF` 不误置。
- **版本互锁必要且正确**：实读 `check_spec_changelog.py` 断言 7（13 册册头版本必须一致），单册升号必红；0.5.6 已于 `9e9a9c3d` 发布 ⇒ 按 `Process-06` 开 `0.5.7-rc`；`check-spec-archive-verify` 的 `SKIP SimRISC-0.5.7-rc` 证实一致。
- 注入：工程师 6/13 红→还原回绿；reviewer 自选（`RDN` 负溢出改 −ft_max）⇒ 3/13 红（含锁 sha）→ 还原回绿。
- **任务书背景散文「RNE/RUP ⇒ ±Inf；RTZ/RDN ⇒ ±最大有限」在交叉格上不准确**（reviewer 指出）：正确表述是「按精确结果符号 + 舍入方向」，实现与 spec 表按正确表述写。
- 遗留转 `ISS-399`：① `§2.5` FMA 溢出同类冲突（另立任务）；② `§1.4` i2f 措辞冲突但不可达（uint64 max 1.84e19 ≪ 3.40e38）；③ 缺「全册条目要么合 IEEE、要么显式标注偏离」的机械门控（建议随 FP 族审计补）。

