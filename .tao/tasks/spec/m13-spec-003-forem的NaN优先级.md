# m13-spec-003: `forem` 的 NaN 优先级按 IEEE §7.2 f) 写明

**模块**：spec
**项目里程碑**：M13
**依赖**：`m13-spec-002`（同册，串行）
**可并行分片**：否（单册单写者）
**状态**：已验证

## 背景

`m12-chipyard-014` 的 reviewer 发现 `spec/SimRISC-07 §2.1` 对 `qNaN rem ±0` 有两句互相冲突的表述：

- 「`rfHD` 为 ±0 ⇒ NV」
- 「qNaN 作输入不传播标志」

用户 2026-11-12 追问「IEEE 754 标准里有规定吗」，核查结论：**有明文**。

IEEE 754-2019 **§7.2 f)**（无效操作的条件）原文：

> remainder: remainder(x, y), when y is zero or x is infinite **and neither is a NaN**

即：**只要任一操作数是 NaN，remainder 就不属无效操作**，不置 invalid；quiet NaN 原样传播（§6.2：quiet NaN 输入不触发任何异常），signaling NaN 仍按 §7.2 a) 置 invalid。

⇒ 现行实现（NaN 优先、`qNaN rem ±0` 不置 NV）**符合 IEEE**；错的是 spec 那句缺了「且两者都不是 NaN」的限定。

## 目标

1. `spec/SimRISC-07 §2.1`：给「`rfHD` 为 ±0 ⇒ NV」补限定语——**「且两个操作数都不是 NaN」**，并明写优先级：NaN 输入优先于「除数为 ±0」这条无效条件。
2. 同节或脚注补一句 sNaN 例外：sNaN 操作数仍置 `NV`（IEEE §7.2 a）。
3. `.tao/contracts/contract-fp.md` 同步（投影，不反向定义语义）。
4. 版本与 `manifests/spec-readonly.lock.toml` 同笔更新（只改 `SimRISC-07` 一行 sha）。

## 非范围

- 不改任何实现（chipyard/QEMU/gem5 现状即 IEEE 一致）
- 不改向量（现有向量已按 NaN 优先）
- 不动 `fo2ft` 溢出（`m13-spec-002`）

## 验收标准

1. `§2.1` 的 remainder 段逐条给出四种组合的期望（qNaN×零、sNaN×零、finite×零、Inf×finite），且与 IEEE §7.2 f) 一致
2. `git grep` 证明无残留「`rfHD` 为 ±0 ⇒ NV」无条件表述
3. 5 个 spec 门控 + `check-knowledge-refs` rc=0
4. 版本与锁同笔更新，`sha256` 实测 MATCH
5. 一键证据脚本（含可达 FAIL：把限定语删掉 ⇒ 应 FAIL）
6. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- `.work` 必须软链（`ISS-389`）。
- 本任务只改文字，不改行为；若发现实现与 IEEE 仍有出入，**停下登记**，不要顺手改实现。

## 硬约束（子代理必读）

1. 独立 `git worktree` 作业（分支名 = 任务号），禁改主工作树（`ISS-368`）；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
8. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审

**审查方式**：逐行读 `git diff`（4 个文件 + 本任务书），对照 IEEE 754-2019 §7.2 f)／§7.2 a)／§6.2 逐行核表；证据脚本两轮复跑（正常 + `--inject`）；另用独立精确 oracle（`tools/chipyard/fp_ref.py::rem_exact`）对 ft/fo 共 13 组边界复核。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 版本未升（保持 `0.5.7-rc`），与任务书「按 `Process-06` 整体升号」的字面有落差 | ✅按判据执行（自决） | 条目并入既有 `0.5.7-rc` 段；13 册册头与根 `README` 在研列本来即 `0.5.7-rc`，无差异故未改 | 0.5.7 未发布（归档目录无该版）；`check-spec-archive-verify` 输出 `SKIP SimRISC-0.5.7-rc`；证据 C17 版本互锁 PASS |
| F2 锁改 2 行（任务书目标 4 写「只改 `SimRISC-07` 一行 sha」） | ✅必要越界（披露） | `SimRISC-00` 与 `SimRISC-07` 两行 sha256 同笔重算 | 证据 C18 `MATCH 21 / MISMATCH 0`；`check-spec-readonly` rc=0 |
| F3 已发布 `0.5.6` 变更记录段仍有 1 处无条件表述 | ❌不修（历史行不改写） | 无 | 证据 C12b：该表述在 `0.5.7-rc` 段出现 0 次、`0.5.6` 段 1 次（现场统计） |
| F4 `components/chipyard/README.md` 与 `tools/chipyard/fp_ref.py` docstring 仍以「`rfHD` 为 ±0 ⇒ NV」概括 remainder（代码为 NaN 优先） | ⏸延后（范围外，非 spec/合约） | 无 | 完成区「新发现/坑」③ |
| F5 首版证据脚本 `grep -o 'MATCH [0-9]*'` 在 `MISMATCH 0` 上误匹配，MATCH 现场值被重复打印 | ✅已修 | 改 `grep -x`，脚本改为分行输出 `MATCH n` / `MISMATCH n` | 现场统计只余 `MATCH 21` 一个值 |
| F6 首版脚本用 `git diff --name-only` 判「空注入」无效（任务分支本就改该文件，恒非空） | ✅已修 | 改用 md5 前后比对判空注入，`git diff` 仅作打印 | 注入轮打印 `md5 fb9a… → a4a5…`；还原后 md5 相等 |
| F7 首次编辑 `SimRISC-00` 时误把「浮点规范性引用」条目当锚点替换，导致该条被删 | ✅已修 | 立即补回两条并存 | `git diff` 该册仅 `+1` 行，两 bullet 均在 |
| F8 表行「`±Inf` × 有限非 NaN（含 ±0）」措辞冗余（有限已含非 NaN） | ✅已修 | 改「有限（含 ±0）」，证据 C9 期望串同步 | 证据 31/31 PASS |
| F9 证据脚本内建 gates 为 11 项，未含归档两门控（需 `.cache` 只读软链） | ✅披露 | 归档两门控单列手工执行、跑完即删软链 | `check-spec-archive`／`-archive-verify` rc=0 |

**判决**：F1/F2 为按判据的自决与必要越界（均已披露）；F3/F4 为不改/延后的具证项；F5–F9 已修并复验。无未修 finding 阻塞验收。

### 第 1 轮 reviewer 验收

**重跑记录**（worktree HEAD `85f72e59`，全部现场执行，输出为真实终端摘录）：

- 证据脚本 `bash .work/evidence/m13-spec-003/run.sh` ⇒ `小结：31 项检查，PASS 31，FAIL 0`、`exit=0`；`--inject` ⇒ I1 红 `C1/C2/C18/C18b/G:check-spec-readonly`（exit=5）、I2 红 `C7/C11/C18/C18b/readonly`（exit=5），两轮还原 md5 均 `fb9a9295…` 相等、回绿 `31/31 exit=0`——与完成区逐条一致。
- 7 门控亲跑全 rc=0：`check-spec-readonly`（`21 read-only spec volume(s) OK`）、`-changelog`（`PASS`）、`-drift`（`PASS`）、`-numbering`（`PASS`）、`-refs`（`PASS (0 violations)`）、`check-fp-contract`（`PASS`）、`check-knowledge-refs`（`PASS (0 具体 .work/** 引用)`）；另 `check-spec-codeblocks`/`check-asm-prose` 亦 rc=0（完成区补充声明属实）。
- 锁 sha 独立重算：`MATCH 21 / MISMATCH 0`；`SimRISC-00=5c2c8665…`、`SimRISC-07=f826ca07…`，与锁及完成区一致。
- 版本：`.tao/archive/` 无 `SimRISC-0.5.7*`；补 `.cache` 软链后 `check-spec-archive-verify` rc=0、输出 `SKIP SimRISC-0.5.7-rc（预发布 -rc：不纳入归档校验）`（跑完删软链，`git status` 空）；`check-spec-archive` rc=0。
- reviewer 独立注入（`cp` 备份 + md5 对账）：① sNaN 行 `**置**→不置` ⇒ `exit=1`，红 `C7/C18/C18b/readonly`，还原 md5 `fb9a9295…` 复位；② 无条件表述注入 `SimRISC-00` 的 `0.5.7-rc` 段 ⇒ `exit=1`，红 `C12b/C18/C18b/readonly`（C12b 可达 FAIL 实证），还原 md5 `af1eb1bb…` 复位；回绿 `31/31 exit=0`；5 文件 md5 与开工快照逐一相等、无 `.preinject` 残留。

**约束核验**：

1. 四组合 vs IEEE §7.2 f)（按标准原文独立推导，非看表）：f) = `（y 为零 ∨ x 为无穷）∧ 两者皆非 NaN`，叠加 §6.2（qNaN 输入不触发异常）、§7.2 a)（sNaN ⇒ invalid）、§7.2.0（invalid 默认结果 = qNaN）⇒ qNaN×±0 不置、sNaN×±0 置、finite×±0 置、±Inf×finite 置；`neither is a NaN` 同时限定两个析取支 ⇒ qNaN 优先确实覆盖 `y=±0`。表 7 行（含 ±Inf×±Inf、有限×±Inf、有限×有限非零）逐行一致。
2. NV vs DZ：§7.2 f) 把 remainder 的 y=0 归 invalid，§7.3 divideByZero 仅管 division；spec §2.1 L125、contract §5、`SimRISC-00` 条目三处明写「NV 而非 DZ」，全册 grep 无 remainder-DZ 混淆。
3. 实现侧亲核（grep 源码）：chipyard `WumingFP.scala.patch` `invalid = rawA.isSigNaN || rawB.isSigNaN || (!nanIn && (rawA.isInf || rawB.isZero))`，生成 SV ft/fo 两份同式、`passZ ⇒ flags=0`；QEMU `softfloat-parts.c.inc::partsN(modrem)` 的 NaN 分支先于 `a=Inf ∥ b=0 ⇒ invalid`、`pick_nan` 仅 sNaN 置 invalid ⇒ sNaN⇒NV、qNaN×±0⇒零标志、finite×±0 与 ±Inf×finite⇒NV、finite×±Inf⇒透传，均与 IEEE 一致；§6.1 `remainder(subnormal,∞)` 的 underflow 信号按 §7.5 默认处理**不置标志**，故 spec「不置 UF」按标志口径仍正确。
4. 版本与锁：`0.5.7-rc` 未发布属实（归档无目录 + verify `SKIP`）；13 册头／README 在研列／rc 段均 `0.5.7-rc`（C17 现场）；锁两行为必要越界（`SimRISC-00` 已改动、sha 不同笔重算则 readonly 必红），已披露。
5. 旧措辞：无条件表述仅存 `SimRISC-00` 已发布 `0.5.6` 历史段 1 处（历史不改写，合规）；`0.5.7-rc` 段 3 条 bullet 全带限定语；C12b 字面匹配且可达 FAIL（注入②实证）。
6. 纪律：WIP 提交恰含完成区所列 5 文件（architect 已 WIP 提交，`git status` 空 = 对账一致）；完成区 17 行 ≤30、审阅记录 18 行 ≤40；无运行期绝对路径；`.work` 为软链（ISS-389）；本轮 reviewer 未 commit、未改台账。

**判决：Accepted**——验收标准 6 条在 reviewer 自己的重跑下全部成立，硬约束无违反。不阻断的遗留观察：④ `components/chipyard/README.md` 与 `fp_ref.py` docstring 旧概括措辞（F4 已披露延后）；⑤ C12b 为字面匹配，对未来不同措辞的无条件表述不设防（现状无残留，建议 FP 族审计时收紧）。

## 完成区

**测试结果**：一键证据脚本 31/31 PASS（rc=0）；`--inject` 两轮：I1 删限定语 ⇒ C1/C2/C18/C18b/readonly 红（exit=5）、I2 删 sNaN 行 ⇒ C7/C11 同组红（exit=5），均 `cp` 还原且 md5 前后相等 → 31/31 PASS（rc=0）。门控 rc 全 0（11 项）：`check-spec-readonly`／`-changelog`／`-drift`／`-numbering`／`-refs`、`check-knowledge-refs`、`check-fp-contract`、`check-spec-purity`、`check-spec-cite-targets`、`check-asm-list-drift`、`check-legality-drift`；另 `check-spec-codeblocks`／`check-asm-prose`／`check-spec-archive`／`-archive-verify` 亦 rc=0。

**修改文件**（`git status --porcelain -uall` = 5 modified、0 untracked；含本任务书）：
- `spec/SimRISC-07-浮点运算.md`（§2.1 remainder 段：§7.2 f) 限定语 + NaN 优先 + sNaN 例外 + 七行期望表）
- `spec/SimRISC-00-指令系统设计.md`（附录 `0.5.7-rc` 段追加 1 条；该册共 `+1` 行）
- `.tao/contracts/contract-fp.md`（§5 remainder 条同步投影）
- `manifests/spec-readonly.lock.toml`（文件头变更注释 + `SimRISC-00`／`SimRISC-07` 两行 sha256）
- `.tao/tasks/spec/m13-spec-003-forem的NaN优先级.md`（本任务书）

**验收结果**：组合期望（`x`=`rfHC`、`y`=`rfHD`，`NV` 置位／结果）——qNaN×±0 = 不置／qNaN；sNaN×±0 = 置／qNaN；有限（含 ±0）×±0 = 置／qNaN；±Inf×有限（含 ±0）= 置／qNaN；±Inf×±Inf = 置／qNaN；有限×±Inf = 不置／返回 `rfHC`；有限×有限非零 = 不置／精确余数（符号随 `rfHC`）。独立 oracle 13 组 ft/fo 边界 MATCH 13/13（`NV` = bit0）。锁 sha 实测 `MATCH 21 / MISMATCH 0`：`SimRISC-00` = `5c2c8665…`、`SimRISC-07` = `f826ca07…`。

**新发现/坑**：① `0.5.7-rc` 未发布 ⇒ 版本不升、条目并入既有 `-rc` 段，13 册册头／根 `README` 在研列无差异（与 `m13-spec-002` 的「已发布 ⇒ 开新 `-rc`」情形不同）；② 无条件表述残留 1 处，位于 `SimRISC-00` 已发布 `0.5.6` 变更记录段（历史行不改写），证据 C12b 机械断言其不得进入 `0.5.7-rc` 段；③ `components/chipyard/README.md` 与 `tools/chipyard/fp_ref.py` docstring 仍用旧概括措辞（实现本身是 NaN 优先）——范围外，建议随 FP 族审计一并收紧；④ 任务 worktree 内跑归档门控需 `.cache` 只读软链（同 `m13-spec-002` F5）。

**遗留问题**：无实现／向量改动；③ 为范围外登记建议（未改任何实现文件）。

#### 收尾（architect，2026-11-12 12:38）

- reviewer **Accepted**：证据脚本 31/31；两轮注入（删限定语 / 删 sNaN 行 / 无条件表述注入 `-rc` 段）均红且可达，还原后 md5 逐一相等。
- **四组合按条文独立推导一致**：`neither is a NaN` 同时限定两个析取支 ⇒ **qNaN 优先确实覆盖 `y=±0`**；`NV` 与 `DZ` 全册无混淆（§7.3 只管 division）。
- **实现侧「无出入」经扩展核对成立**：reviewer 另核 `finite×±0`、`±Inf×finite`、`±Inf×±Inf`、`finite×±Inf`、透传路径，chipyard（Scala 源 + ft/fo 两份生成 SV）与 QEMU（`modrem` + `pick_nan`）均与 IEEE 一致。
- 版本维持 `0.5.7-rc`（未发布，归档无目录 + `SKIP` 实证）；锁两行为必要越界（`SimRISC-00` 也改了）。
- 遗留：`components/chipyard/README.md` 与 `fp_ref.py` docstring 仍是旧概括措辞（实现正确），随 FP 族审计收紧；`C12b` 为字面匹配、对未来不同措辞不设防。

