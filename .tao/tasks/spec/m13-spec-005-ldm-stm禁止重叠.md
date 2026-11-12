# m13-spec-005: `ldm` 禁止基址/索引落入传送范围（`stm` 允许）

**模块**：spec
**项目里程碑**：M13
**依赖**：`m13-spec-004`（同册，串行）
**可并行分片**：否（单册单写者）
**状态**：已验证

## 用户裁定（2026-11-13，原话）

> 「不允许重叠，改spec」

补充裁定（2026-11-13，经主会话转达，落纸）：

> 「基址寄存器：与 rf/ra 没有关系」（⇒ RA/RF 形式结构上不可能重叠）
> 「stm 应该是允许这种重叠的」（⇒ 只有 `ldm` 禁止）

## 背景

`ldm`/`stm` 的编码是 `{rdHA:rdHA+immu6-1}, [rbHB, rdHC]`：一段**被传送的寄存器范围** + 一个**基址寄存器** + 一个**索引寄存器**。

现状（`SimRISC-01`）：允许基址/索引寄存器落在传送范围内，靠「地址按**原始** `rdHC` 计算」「按序先读后写」保证确定性，但**行为依赖处理顺序**，使用者需自行避免。

用户裁定：**不允许重叠**。

## 目标

1. **`spec/SimRISC-01`** 的限制列表改写：
   - **`ldm`（装入）禁止重叠**（会写目的寄存器，重叠导致地址依赖处理进度）：
     - RD 形式：`rdHC ∉ [rdHA, rdHA+immu6)` ⇒ 违反 **ILLI**
     - RB 形式：`rbHB ∉ [rbHA, rbHA+immu6)` ⇒ 违反 **ILLI**
   - **`stm`（存储）允许重叠**（只读传送范围、不写寄存器 ⇒ 行为确定）；spec 要写明「允许」及理由，**不要**给它加禁令
   - **RA / RF 形式**：结构上不可能重叠（范围在 RA/RF，基址在 RB、索引在 RD）⇒ 写明「不适用」
   - 删除旧句「可以重叠…按序先读后写…行为依赖顺序」（对 `ldm` 已经不成立）；「地址按原始 `rdHC` 计算」评估是否保留
2. **`contracts/legality_rules.yaml`**：新增规则（如 `mreg_range_base_overlap`），并给 `contracts/opcodes.yaml` 对应记录的 `legality` 加上该规则 id。
3. 与块复制的 `mreg_range_overlap` 保持语义一致（同一族规则的命名/写法）。

## 非范围

- 不改实现（三个平台各有独立任务：`m12-chipyard-027` / `m13-qemu-006` / `m13-gem5-008`）
- 不改测试（`m13-testcases-013` 自己改 overlap 用例）
- 不动 `spec-004` 已定的「多元素内存指令允许部分生效」

## 验收标准

1. `SimRISC-01`：`ldm` 的 **RD/RB** 写明禁令与 ILLI；**`stm` 写明允许**及理由；**RA/RF 写明「不适用」**
2. `legality_rules.yaml` 新规则 + `opcodes.yaml` 的 legality 引用（`check-legality-drift`/`check-rule-refs` rc=0）
3. `git grep` 无残留「可以重叠」「行为依赖顺序」类表述（保留历史段除外）
4. 5 个 spec 门控 + `check-legality-drift`/`check-rule-refs`/`check-knowledge-refs` rc=0
5. 版本/锁按互锁规则同步（`0.5.7-rc` 未发布则并入）
6. 一键证据脚本（含可达 FAIL：删禁令 ⇒ 红）
7. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- `.work` 软链（`ISS-389`）；spec 单写者；与 `spec-004` 串行。
- 本册定稿后三个实现任务才可派单。

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

### 第 1 轮 engineer 自审（2026-11-13）

自审方式：逐行复核 9 个改动文件 + 证据脚本/断言；逐条对照任务书「最终规则」四种形式、验收 7 条。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `tools/spec/generate_opcodes.py` 自 SPEC-194t 起与 `contracts/opcodes.yaml` 漂移（跑生成器整表改 93 行 FP 记录） | ✅已修（绕行+披露） | 不重生成整表：`contracts/opcodes.yaml` 以 HEAD 副本 `cp` 还原后定点补 8 条记录（16 行）；生成器只同步改 `ldm` 部分（+helpers/映射） | 生成器在临时树重跑 ⇒ `ldm`/`stm` 记录与入库 yaml 逐字段相同（S24）；整表漂移登记遗留 |
| F2 证据脚本探针失败计数被「还原后全量复跑」重置 ⇒ 探针失败仍报 SELF-CHECK PASS（假绿） | ✅已修 | 探针失败改独立计数 `PROBE_FAIL`，结尾同时判 `FAIL`/`PROBE_FAIL` | 负控：把 P1 断言改为无关项 ⇒ `PROBE FAIL` + exit 1；改回后 6/6 PASS |
| F3 P1 注入目标串因后续补「执行前判定」而失配 | ✅已修 | 注入改为整行前缀匹配（`- **\`ldm\` 禁止索引寄存器落入传送范围**`） | P1 重新可注入、S1/S3 双红、md5 还原一致 |
| F4 S13 漏掉 `**原始** \`rdHC\`` 变体（P5 注入时未红） | ✅已修 | 残留断言改正则 `原始\**\s*\`rdhc\``，扫描面排除变更记录（附录） | P5 注入 ⇒ S13+S20 双红；还原后 0 红 |
| F5 附录 B 断言把摘要里的 `` `ldm` `` 也当记录 id（集合 9≠8） | ✅已修 | id 解析限 `_rrri_` 形态 | S18 集合=计数=8（现场 8） |
| F6 `DADAO-12 §5`（spec-004 写入）「地址按原始 `rdHC` 计算」与新禁令冲突 | ✅已修（越界，披露） | 改为「本例外前提 = 地址寄存器不被传送过程改写」，并补 0.7.3-rc 条目 + 锁 sha | S20 新前提有/旧口径无；`check-spec-*(readonly/changelog/drift)` rc=0 |
| F7 规则 id 取 `mreg_range_addr_overlap`（任务书示例为 `mreg_range_base_overlap`） | ❌不修（命名更准，披露） | `base` 无法覆盖 RD 形式的索引寄存器；族前缀 `mreg_range_` 与块复制规则一致 | 下游 3 实现任务书均不写死 id（已查）；`check-rule-refs` rc=0 |
| F8 `stm` 允许语句是否与「部分生效」段冲突 | ✅无需改（已核） | 例外段以「地址寄存器不被改写」为前提，`stm` 不写寄存器 ⇒ 前提自动成立 | S2/S6 绿；DADAO-12/SimRISC-00 条目同口径 |
| F9 L1 4 项红是否为本次引入 | ✅已核（环境/他任务） | `check-run-artifacts`：共享日志目录他任务文件名不合规（主工作树同红）；`check-musl-freshness`/`-width-sizes`/`-components`：fresh worktree 缺本机工具链根 | 主工作树复核 `check-run-artifacts` rc=2 同一条目；工具链根在主工作树存在 |

判决：F1–F6 已修并复验，F7 为命名披露、F8/F9 为核查结论。**无未修 finding ⇒ 可标 `待验收`**。

### 第 1 轮 reviewer 验收（2026-11-13）

重跑（HEAD `2c55fa58`；全程未 commit；结束 `git status -uall` 空、5 目标文件 md5 与注入前逐字相等）：
- `./.work/evidence/m13-spec-005/run.sh` ⇒ `semantic: 24/24 PASS` + 15 门控全 `rc=0`，`RESULT: PASS`，**exit=0**（39 项）
- `run.sh --inject` ⇒ P1–P6 六路全 `PROBE PASS`（各先红后绿、还原 md5 一致），`SELF-CHECK PASS`，**exit=0**
- 负控（临时副本把 P1 期望改为无关 `S24`）⇒ `注入后语义 FAIL 项=0`、`PROBE FAIL：P1`、`SELF-CHECK FAIL`，**exit=1**（探针 FAIL 路径可达）
- reviewer 独立注入 3 路（`cp` 备份 + md5 还原）：① `ldm.o_rrri_ra` 加规则 ⇒ `S15 FAIL(9≠8)` 且 `check-legality-drift exit=2`；② §2 区间式改 `+immu6*2` ⇒ `S7 FAIL`；③ 删 §3 RA「不适用」行 ⇒ `S9 FAIL`；还原后 `24/24 PASS`、`git status` 空、md5 相等
- 8 条引用独立派生（`opcodes.yaml` 字段 bank，不看 yaml 引用）：`ldm` rrri 11 条中同组 **8** 条 = RD 7 + RB 1，与引用集合**完全相等**；`stm` rrri 8 条 **0** 引用；RA/RF 3 条不适用；规则 `fault=ILLI kind=static status=active`、表达式与字段名一致
- 锁：21 册 sha256 实测 `mismatch: 0`（3 册为本任务重算）；版本 `0.5.7-rc`/`0.7.3-rc` 未升；生成器全表重跑 ⇒ **仅 18 条 FP 记录漂移（39 删 + 54 增 = 93 行）**、`ldm`/`stm` 逐字段相同（ISS-416 属实，已在 master `2897d237` 登记）

约束核验：四形式表述（§1 RD 禁 / §2 RB 禁 / `stm` 两处显式「允许」+理由 / §3、§4 不适用含分组理由）✅；10 文件与 `git show --stat 2c55fa58` 逐项对账 ✅；完成区 20 行、全文无运行期路径 ✅；越界①②已披露、下游 3 实现任务书不写死规则 id（实测 grep 0 命中）✅；本 reviewer 仅新增本子区 1 处。

Findings（**非阻断**，architect 收尾提交处理）：
- **F-R1** `docs/DDLN/A-指令系统/DD-A006-指令系统--访存与地址运算.md` L11/L95/L142/L143 仍写「`ldm`/`stm` …可以重叠」「地址仍按原始值计算」——验收 3 的 repo 级 grep 有 1 处**活命中**（非历史段）。DDLN 属讲义非判据（`MEMORY.md`），按文档级 finding：**收尾订正这 4 行**。
- **F-R2** `checks.py` S11–S13 扫描面 = spec/contracts，窄于验收 3 的「git grep」⇒ 建议把 `docs/DDLN` 纳入残留扫描，否则同类残留仍测不到。
- **F-R3** `run.sh` 头注写「5 路注入」实为 6 路（注释笔误）；`spec-004` 完成区仍引「地址按原始 `rdHC` 计算」属历史记录、按规则不改写（备忘）。

**判决：Accepted** —— 验收命令块在我自己的重跑下全绿、硬约束无违反；DDLN 残留为讲义级文档问题，按 6.5 记 finding 不开新一轮。

## 完成区

**测试结果**：证据脚本 **39 项全 PASS**（24 项语义断言 + 15 个门控）rc=0；`--inject` 6 路探针（删 §1 禁令 / 改规则名 / 给 `stm` 加引用 / 锁 sha 改旧 / DADAO-12 恢复旧口径 / 删 `ldm.o-rb` 引用）均「先红后绿」，`cp`+md5 还原 md5 前后一致，`SELF-CHECK PASS`；负控（P1 断言指向无关项）⇒ `PROBE FAIL` + exit 1（探针失败路径可达）。`make check`（L1）4 项红均非本任务：`check-run-artifacts`（共享日志目录他任务文件，主工作树同红）、`check-musl-freshness`/`-width-sizes`/`-components`（fresh worktree 缺本机工具链根）。

**修改文件**（`git status --porcelain -uall` = 10 modified、0 untracked，逐项对账）：
- `spec/SimRISC-01-取数存数.md`（§1/§2 限制列表改写、§1 顺序约束段改口径、§3/§4 不适用、附录 B 重生成 1 行/8 条）
- `spec/SimRISC-00-指令系统设计.md`（0.5.7-rc 段 +1 条）
- `spec/DADAO-12-SEE-主管系统运行环境.md`（§5 例外前提改写 + 0.7.3-rc 段 +1 条）**越界披露①**
- `contracts/legality_rules.yaml`（+`mreg_range_addr_overlap`）
- `contracts/opcodes.yaml`（8 条 `ldm` 记录 +表达式 +`rule_refs`，共 16 行）
- `.tao/contracts/contract-isa.md`（§3.1.2/§3.2 禁令 + §3.3 不适用）
- `tools/spec/gen_legality_list.py`、`tools/spec/generate_opcodes.py`（新规则登记 + `ldm` 表达式）**越界披露②**
- `manifests/spec-readonly.lock.toml`（3 册 sha256 + 头注 + 逐册注）
- 本任务书（状态 + 补充裁定落纸 + 审阅记录/完成区）

**验收结果**：**RD**：`rdHA <= rdHC < rdHA + immu6` ⇒ ILLI（静态、指令执行前判定、不产生元素效果）；**RB**：`rbHA <= rbHB < rbHA + immu6` ⇒ ILLI（同）；**`stm`（RD/RB）**：允许 + 理由（只读传送范围、不写寄存器、地址不随处理进度改变）；**RA/RF**：不适用（范围在 RA/RF，基址在 RB、索引在 RD）。规则 `mreg_range_addr_overlap`（ILLI/static/active，引用 8 条 = RD 7 + RB 1，由字段 bank 现场派生；`ldm` rrri 共 11 条中同组 8 条；`stm` 0 条）。门控 15 个 rc=0：5 个 spec 门控 + `check-legality-drift`/`check-rule-refs`/`check-isa-coverage`/`check-knowledge-refs` + `validate-encoding`/`check-asm-list{,-drift}`/`check-spec-codeblocks`/`check-legality-invariants`/`check-contracts-dir`。锁：3 册 sha256 实测同步（21 册全对、其余 18 册不变）。版本不升（`0.5.7-rc`/`0.7.3-rc` 均未发布，并入既有段）。

**新发现/坑**：① `tools/spec/generate_opcodes.py` 自 SPEC-194t 起与 yaml 漂移——该任务只改 `contracts/opcodes.yaml` 未改生成器，重跑整表会改 93 行 FP 记录；本次定点编辑规避，建议另立任务收口（复原生成器↔yaml 一致性）；② 证据脚本的「还原后统计」会重置失败计数，探针失败须独立计数（否则假绿），已加负控；③ 注入串须整行/正则匹配，正文补字后固定串会失配；④ 残留断言扫描面须排除「变更记录」附录（历史段保留旧口径字样）；⑤ 任务书示例 id 的 `base` 不覆盖索引形式，族命名宜用 `addr`。

**遗留问题**：无功能遗留。（a）生成器整表漂移（坑①，非本任务引入）；（b）L1 四项环境红（见测试结果）；（c）越界披露①（DADAO-12 跨册一致性）与②（`contracts/` 生成器）需 reviewer 确认属授权范围。

#### 收尾（architect，2026-11-13 07:54）

- reviewer **Accepted**：39 项证据全 PASS；6 路注入 + 负控均可达；**3 路独立注入**（RA 形式加引用 / 区间改成 `immu6*2` / 删 RA「不适用」）全部按名变红、还原回绿。
- **8 条引用独立派生复核**：`ldm` rrri 共 11 条中地址寄存器与范围同组者 **8 条**（RD 7 + RB 1），与 `opcodes.yaml` 实际引用集合**完全相等**；`stm` **0 条**；`ldm.o-ra/rf`、`ldm.t-rf` 不在集合。
- **与 `spec-004` 自洽**：`DADAO-12 §5` 例外前提改为「地址寄存器不被传送过程改写」，四种形态下地址在任意中断点都不变 ⇒ 「允许部分生效」仍成立。
- **生成器漂移（`ISS-416`）处置可接受**：全表重跑确认 264 条中 **18 条 FP** 记录不同（93 行），`ldm`/`stm` 逐字段相同；定点编辑避免夹带无关改动。
- **F-R1 已修**：`docs/DDLN/A-指令系统/DD-A006` 的 4 行（L11/L95/L142/L143）原写「`ldm`/`stm` 可重叠」「地址按原始值」，已按新规则改写（`ldm` 禁止、`stm` 允许、RA/RF 不适用）。
- F-R2：`checks.py` S11–S13 扫描面窄于 repo 级 grep（未含 `docs/DDLN`），建议后续把 DDLN 纳入残留扫描 → `ISS-417`。
- F-R3：`run.sh` 头注「5 路注入」实为 6 路（笔误）。

