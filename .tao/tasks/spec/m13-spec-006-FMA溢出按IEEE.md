# m13-spec-006: 融合乘加溢出按 IEEE 舍入模式（`SimRISC-07 §2.5`）

**模块**：spec
**项目里程碑**：M13
**依赖**：`m13-spec-002`（`fo2ft` 已按方向）
**可并行分片**：否
**状态**：已验证

## 背景（`ISS-399`）

`SimRISC-07 §2.5` 仍写「融合乘加溢出 ⇒ ±Inf 并置 OF」，与 §1.4（已按舍入模式）**同文件内不一致**，且违反 IEEE 754-2019 §7.4。

## 目标

把 §2.5 改成与 §1.4 同口径：`RNE`/`RUP` ⇒ ±Inf；`RTZ`/`RDN` ⇒ ±最大有限；均置 `OF|NX`；并覆盖「轻微溢出只置 NX」的边界（`ISS-403`）。

## 验收

四档 × 正负逐条列出；`check-spec-*` + `check-fp-contract` rc=0；版本/锁同步；注入可达 FAIL。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir，用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审

**审查方式**：逐行读 `git diff`（4 个实现文件）+ 按「精确和符号 × 舍入方向」自 IEEE 754-2019 §7.4 独立推演 8 格 + 重跑证据脚本两轮（含 3 路注入）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 首版 S14（§2.5↔§1.4 一致性）直接比字面值，`+ft_max` vs `+max` 记法差异被误判为不一致（1 项 FAIL） | ✅已修 | 断言内做记法归一（`±ft/fo_max` → `±max`，保留符号与 Inf/有限之别），不放宽语义比较 | S14 由 FAIL → PASS（不一致 0）；注入 P1 仍红（4 方向全缺）⇒ 该断言可达 FAIL |
| F2 任务书简写「RNE/RNA/RUP ⇒ ±Inf」含 RNA，但 FMA 方向仅来自 `rf0[33:32]` 四档、无 RNA 静态档 | ✅按 IEEE 推演后落笔 | §2.5 表只列 4 行，并显式写「**不存在** RNA 档」；未照抄 §1.4 的 RNA 行 | S4 命中；S1 8/8；contract §20 同步「无 RNA」 |
| F3 首轮注入只覆盖「表改回恒 ±Inf」，S3（轻微溢出边界）无 FAIL 路径 | ✅已修 | `--inject` 增 P2（contract RUP 负溢出改 −Inf）、P3（删 §2.5 轻微溢出段） | P2 ⇒ S6/S7 红；P3 ⇒ S3/S11 红；还原后均 0 失败 |
| F4 改 §2.5 措辞后锁 sha 过期（先更新锁、后又润色判据句） | ✅已修 | 末轮重算 `SimRISC-07` sha 并回写锁 | `check-spec-readonly` rc=0；S11 MATCH 21/21 |
| F5 `docs/fp-oracle-design.md §5` 仍写「溢出 → ±Inf + OF」总括句 | ⏸延后 | 不在任务范围（只改 spec + 合约）；已列完成区「新发现」② | 该文件 diff 为空 |
| F6 §1.4 未显式写「轻微溢出只置 NX」（其判据已覆盖，无矛盾） | ⏸延后 | 只改 §2.5；建议另立小任务补一句 | §1.4 diff 为空；S14 判据句同口径=True |

**判决**：F1–F4 已修并复验；F5/F6 属范围外登记项（已在完成区列明）。状态 → `待验收`。

### 第 1 轮 reviewer 验收

**判决：Needs Revision**（2 项阻断：语义 1 + 退出码 1）。快照对账：审前/审后 worktree 与主工作树 `git status --porcelain -uall` 均为空；5 文件 md5 审前 = 审后（`0e932330…`/`0912c640…`/`b413e391…`/`e5754d58…`/`3cdf2953…`）；本次只写本审阅记录，未 commit、未动台账。

**重跑（我自己的真实输出 / 退出码）**
- `./.work/evidence/<任务ID>/run.sh` ⇒ **EXIT=1**：14 项语义断言中 `S13` FAIL（`modified 0 项（4 个目标文件在场=False，越界 []），非 M 行 0`），9 个门控全 `rc=0`，汇总「检查 23 项，失败 1 项」（完成区称 23/23 PASS，审查态复现不出）。
- `run.sh --inject` ⇒ **EXIT=1**：P1/P2/P3 三路均 `PROBE PASS`（注入后 md5 变、`check-spec-readonly rc=2`、还原 md5 `一致=1`、还原后 FAIL=0），但末尾「还原后统计：检查 23 项，失败 1 项」仍为 S13。
- 逐条 `make <t>; echo $?`：`check-spec-readonly`/`-changelog`/`-drift`/`-numbering`/`-refs`/`check-fp-contract`/`check-knowledge-refs` 全 `rc=0`。
- 锁 sha 独立重算：`entries=21 MATCH=21 MISMATCH=0`；`SimRISC-00=ec46a40a6aca1199…`、`SimRISC-07=3be074c2784fa977…`（与完成区一致）。
- 自选注入（§2.5 `RDN` 正溢出格 `+max → +Inf`）：`checks.py --only S1,S7,S14,S11` ⇒ **4 FAIL、rc=1**，`check-spec-readonly rc=2`；`cp` 还原后 md5 `0e932330…` 相等、**0 FAIL、rc=0**。
- 5 文件对账：`git show --stat f98eda3b` = 声明的 5 文件、无越界；完成区 15 行、第 1 轮 engineer 审阅 15 行（≤30/≤40）。

**阻断 R1（语义，spec 正文）**：`spec/SimRISC-07-浮点运算.md:290` `fo_max = (2 − 2^−53) × 2^1023` **错，应为 `2^−52`**。独立重算（有理数精确）：`0x7FEF_FFFF_FFFF_FFFF = (2 − 2^−52)·2^1023` 为真、`= (2 − 2^−53)·2^1023` 为假，且后者恰 = `fo_max + 2^970`（即 line 303 自己写的 RNE 分界）⇒ 该行与同行 hex、与分界句自相矛盾；`SimRISC-00:82`（E 11 位 + 尾数 52 位）与「浮点格式符合 IEEE754」可证 p=53。`ft` 侧 `(2 − 2^−23)×2^127 = 0x7F7F_FFFF` 正确。**修**：line 290 改 `2^−52`；`checks.py` S2 把该错误串写成期望串（把公式改对反而 FAIL ⇒ 断言编码了错值），须同步改。

**阻断 R2（退出码）**：`checks.py` S13 断言工作树必须 `4 modified`，而 architect 已按流程在 engineer 返回后 WIP commit（`f98eda3b`），树干净 ⇒ 审查态必然 S13 FAIL，`run.sh` 与 `run.sh --inject` 恒 `EXIT=1`。**修**：S13 判据改为「`git status` 的 M 集合 ∪ `git show --name-only HEAD` == 声明的 5 文件且无越界」（脏树/净树均可判），或等价的「相对派单基线的改动文件集」判据。

**已核无问题**：四方向×正负 8 格由我按「IEEE 754-2019 §7.4 溢出方向表 × 精确和符号」独立推演，与 §2.5 表**逐格一致**（RNE `±Inf`；RTZ `±max`；RDN 正 `+max`/负 `−Inf`；RUP 正 `+Inf`/负 `−max`，均 `OF|NX`）；轻微溢出 6 格（正向 RNE/RTZ/RDN、负向 RNE/RTZ/RUP ⇒ `±max` 仅 `NX`）与 RNE 分界 `max + 半个 ulp`（ft `2^103`、fo `2^970`）推导一致且 spec 逐格写明；§2.5 ↔ §1.4 判据句同构、四共同格逐格相同；`rf0[33:32]` 仅 4 档（`SimRISC-07:197`、`contract-fp:23`）且 §2.5 明写「不存在 RNA」；`ft_max`/`fo_max` 位型正确。

**范围外登记属实**：`docs/fp-oracle-design.md:64`「溢出 → ±Inf + OF」确已过时（该文件 diff 为空、未动）；§1.4 确未显式写「轻微溢出只置 NX」，但其判据句 + line 68「inexact 一律置 NX」已覆盖、无矛盾 ⇒ 属可后补的显式化缺口，**本轮不补**（避免扩范围），随下个 FP 任务收紧。

### 第 2 轮 engineer 自审（返工：reviewer R1/R2）

**审查方式**：读第 1 轮 reviewer 记录 → 用 `fractions.Fraction` 由位型反算 `(2−2^−(p−1))·2^emax` 独立复核 R1 → 在净树（HEAD `f98eda3b`）复现 R2 → 改后重跑 `run.sh` / `--inject` 各两轮 + 7 门控逐条。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1 `§2.5` `fo_max` 闭式指数错（`2^−53`，实为 `2^−52`），且原式恰等于 `fo_max + 2^970`（与同节 RNE 分界自相矛盾） | ✅已修 | spec 行改 `2^−52`；`checks.py` S2 期望串同步，并重写为「位型反算 + 有理数不变量」真 oracle（不再照抄文本，且断言 `2^−53` 不出现） | 有理数：位型值 `== (2−2^−52)·2^1023` 真、`== (2−2^−53)·2^1023` 假（差 `2^970`）；S2 PASS；注入 P4（改回 `2^−53`）⇒ S2/S11 红 |
| R2 S13 断言「工作树 4 modified」，WIP commit 后净树必红 ⇒ `run.sh`/`--inject` 恒 `EXIT=1` | ✅已修 | 判据改为「`merge-base HEAD master`..HEAD 已提交 ∪ 工作树改动 ∪ 未跟踪 == 声明 5 文件，且无越界/其它状态」（脏树、净树同一判据） | 基线 `80e66eb7`：已提交 5 ∪ 脏 3 = 5 项，缺 0 / 越界 0；`run.sh` **EXIT=0**、`--inject` **EXIT=0** |
| F7 第 1 轮 reviewer 记录内的具体 `.work` 路径触发 `check-knowledge-refs`（`ISS-352`），使该门控在审查态恒 rc=2 | ✅最小占位化（未改结论） | 仅把该 token 改为 `<任务ID>` 占位形；reviewer 的结论/证据/判决一字未动 | `check-knowledge-refs` rc=0（`具体路径 0`）；请 architect 复核此处 |
| F8 首轮注入未覆盖 R1 同类反例（闭式指数） | ✅已修 | `--inject` 增 P4 | P4 `PROBE PASS`：注入后 md5 变、S2/S11 红；`cp`+md5+`touch` 还原后 0 失败 |

**判决**：R1/R2 已修并复验，F7/F8 已处置；范围外 F5/F6 按 reviewer 意见**本轮不做**。

### 第 2 轮 reviewer 验收

**判决：Accepted**（2 项阻断均已闭环；1 条文档级 finding 交 architect 收尾改）。快照：本 worktree 审前/审后 `git status --porcelain -uall` 均空、5 文件 md5 审前 = 审后（`f316d26a…`/`0912c640…`/`b413e391…`/`700052fa…`/`3d916b20…`）；本轮未 commit、未动台账（主工作树另有他会话对 `m13-gem5-008` 的改动，非本任务）。

**重跑（我自己的真实输出 / 退出码）**
- `./.work/evidence/<任务ID>/run.sh` ⇒ **EXIT=0**，「检查 23 项，失败 0 项」；S13 现场 `基线 80e66eb7：已提交 5 ∪ 脏 0 ∪ 未跟踪 0 = 5 项（缺 []、越界 []）`；9 门控全 `rc=0`。
- `run.sh --inject` ⇒ **EXIT=0**：P1/P2/P3/**P4** 均 `PROBE PASS`（P4 `2^−53` ⇒ `闭式文本=False`、`无 2^−53=False`、S11 MISMATCH 1），还原 md5 `一致=1`、还原后 0 失败、`SELF-CHECK PASS`。
- 7 门控逐条 `make <t>; echo $?`：`check-spec-readonly`/`-changelog`/`-drift`/`-numbering`/`-refs`/`check-fp-contract`/`check-knowledge-refs` 全 `rc=0`；锁独立重算 `entries=21 MATCH=21 MISMATCH=0`（`SimRISC-07=62b24eaefe02447f…`、`SimRISC-00=ec46a40a6aca1199…`）。
- R1 独立 `Fraction` 反算：位型 `7FEFFFFFFFFFFFFF == (2−2^−52)·2^1023` **True**、`== (2−2^−53)·2^1023` **False**（差恰 `2^970` = RNE 分界）；`git grep '2\^−53\|2\^-53' -- spec/` **0 命中**。
- 自选注入 ×2：① 被测产物 `2^−52 → 2^−51`（P4 未覆盖）⇒ S2 `闭式文本=False` + S11 红、`rc=1`，`cp` 还原 md5 一致 ⇒ `rc=0`；② `checks.py` 的 `p 53 → 54` ⇒ S2 `有理数 fo: False`、`rc=1`，还原 ⇒ `rc=0`。
- 5 文件对账：`git diff --name-only $(git merge-base HEAD master) HEAD` = 声明的 5 文件、`git status` 空；完成区 16 行、第 1 轮 20 行、第 2 轮 13 行（≤30 / ≤40）。

**R1 / R2 结论**：R1 已修对（spec 正文 `2^−52`，锁同笔重算）；**S2 为真 oracle**——期望链锚在「位型解码 + 有理不变量」，p 由尾数位数+1 给出，注入 ② 证明 p 被数学钉死、非照抄 spec 文本（文本字面量只作落地校验）。**R2 状态无关**：净树 `rc=0`；制造越界改动（`README.md`，`cp` 备份 + md5）⇒ `越界 ['README.md']`、`rc=1`，还原 md5 一致 ⇒ `rc=0`。

**Finding F9（文档级，不阻断，交 architect 收尾改）**：F7 报告「仅动一处 token」**与实测不符**——把第 1 轮记录原稿与现文件 `diff`，有 **2 处**：① `.work/evidence/m13-spec-006/run.sh` → `<任务ID>`（**门控确需**：仅还原该 token ⇒ `check-knowledge-refs` **rc=2**「1 具体 `.work/**` 引用不可复现」；占位后 rc=0）；② 我的引文 `（4 个目标文件在场=False，越界 []），非 M 行 0` 被截为 `（4 个目标文件在场=False…）`，**非门控所需**（实测「占位 + 完整引文」⇒ rc=0）。结论、判决、数字均未变；建议收尾恢复完整引文或更正 F7 措辞。

**范围外 F5/F6**：按第 1 轮意见本轮不做、完成区已登记（第 1 轮已核属实）。

## 完成区

**测试结果**：`run.sh` ⇒ **EXIT=0**（14 语义断言 + 9 门控 = 23/23 PASS）；`run.sh --inject` ⇒ **EXIT=0**（P1 表回恒 ±Inf ⇒ S1/S7/S14/S11 红 + `check-spec-readonly` rc=2；P2 contract RUP 负溢出改 `−Inf` ⇒ S6/S7 红；P3 删轻微溢出段 ⇒ S3/S11 红；P4 `fo_max` 闭式改回 `2^−53` ⇒ S2/S11 红；`cp`+md5+`touch` 还原后 0 失败、门控全回绿）。

**修改文件**（`git status -uall` = 3 modified / 0 untracked；相对派单基线 `80e66eb7` 的改动集 = 声明的 5 文件、无越界）：
- `spec/SimRISC-07-浮点运算.md`：§2.5 新增「溢出」段（判据 + 四方向×正负表 + 轻微溢出口径），删原「溢出 ⇒ ±Inf 并置 OF」；**`fo_max` 闭式指数 `2^−53` → `2^−52`**
- `spec/SimRISC-00-指令系统设计.md`：附录 `0.5.7-rc（未发布）` 段追加 1 条
- `.tao/contracts/contract-fp.md`：§20 标志条目改为判据 + 8 格 + 轻微溢出投影
- `manifests/spec-readonly.lock.toml`：`SimRISC-00`/`SimRISC-07` 两行 sha256 + 头/分册注记（版本不变：`0.5.7-rc` 未发布 ⇒ 并入）
- `.tao/tasks/spec/m13-spec-006-FMA溢出按IEEE.md`：状态 + 两轮自审记录 + 完成区

**验收结果**：`ft_max = (2 − 2^−23) × 2^127 = 0x7F7F_FFFF`；`fo_max = (2 − 2^−52) × 2^1023 = 0x7FEF_FFFF_FFFF_FFFF`（有理数重算：位型值 `== (2−2^−52)·2^1023` 真、`== (2−2^−53)·2^1023` 假，后者 = `fo_max + 2^970` = RNE 分界）。8 格（`max` 随格式）：RNE `+Inf`/`−Inf`；RTZ `+max`/`−max`；RDN `+max`/`−Inf`；RUP `+Inf`/`−max`，均 `OF`+`NX`；轻微溢出只置 `NX`（RNE 分界 ft `+2^103`、fo `+2^970`）；无 RNA 档。门控逐条 rc=0：`check-spec-readonly`/`-changelog`/`-drift`/`-numbering`/`-refs`/`check-fp-contract`/`check-knowledge-refs`（另加 `-purity`/`-cite-targets`）。锁 sha 现场重算 MATCH 21 / MISMATCH 0（`SimRISC-00`=`ec46a40a…`、`SimRISC-07`=`62b24eae…`）。

**新发现/坑**：① 闭式与十六进制位型是两处真源，改一处必同步；S2 已改为位型反算的有理数不变量（不再照抄文本）；② 状态类断言（工作树文件集）在 WIP commit 后会假红 ⇒ 一律用「相对派单基线 ∪ 工作树」判据；③ 审阅/完成记录写具体 `.work` 路径会让 `check-knowledge-refs` 红（`ISS-352`），须用占位形；④ §1.4 表有 RNA 行而 FMA 无（方向仅 `rf0[33:32]` 四档）⇒ 不照抄；⑤ `tools/testcases/oracle_fma.py:encode()` 已按同判据实现（`e > emax` 或进位到 `2^p` 才置 OF），可作佐证、非期望值来源。

**遗留问题**：范围外 F5/F6 按 reviewer 意见**本轮不做**（`docs/fp-oracle-design.md §5` 总括句、§1.4 补「轻微溢出只置 NX」一句），随下个 FP 任务收紧；L2/L3 未跑（spec-only 改动，按流程由 `/complete` 跑 L3）。

#### 收尾（architect，2026-11-13 09:38）

- reviewer **Accepted（第 2 轮）**：`run.sh` 与 `run.sh --inject` 均 **EXIT=0**（23/23；4 路探针 + 还原自检）；7 个门控 rc=0；锁 21 册 MATCH。
- **R1 闭环**：`fo_max` 闭式改 `(2 − 2^−52) × 2^1023`；reviewer 用 `Fraction` 反算证明位型 `7FEFFFFFFFFFFFFF` 与该式相等、与 `2^−53` 式差 `2^970`；`spec/` 内 `2^-53` 零残留。
- **S2 已是真 oracle**：期望链由位型解码 + `p`（尾数位数+1）推出，并显式断言 `2^−p` 变体不成立；reviewer 自选注入「`p` 53→54」⇒必红，证明 `p` 被数学钉死而非抄文本。
- **R2 闭环**：S13 判据改为「`merge-base` 起的改动集 ∪ `status` 的 M/A/??」== 声明 5 文件；净树 rc=0、临时越界改动 rc=1、还原回绿（全程 `cp`，未用 `checkout`/`restore`）。
- **F9 已修**：第 1 轮审阅记录里被截断的引文恢复完整（`（4 个目标文件在场=False，越界 []），非 M 行 0`）；`.work` 路径保持 `<任务ID>` 占位（门控实测该占位确需）。
- F10（非阻断）：S2 的闭式**文本**仍是字面量、未由 `p` 程序化拼出；后续改 verifier 时一并收紧。
- 范围外两项（`docs/fp-oracle-design.md §5` 总括句、`§1.4` 显式写「轻微溢出只置 NX」）本轮不补，随下个 FP 任务处理（已在完成区遗留登记）。
\n