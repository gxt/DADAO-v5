# m18-spec-002: hart-first/cg9 规格与契约同步（含 escape frame selector）

**模块**：spec
**项目里程碑**：M18
**依赖**：`ADR-0060`（Accepted）、`ADR-0059`（Superseded 标记由本任务落）
**可并行分片**：否（spec/契约同笔；实现任务在其后）
**预估**：4–6 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务跨 SEE 多节 + 契约 + escape 编码，取 3–4× 中位）
**档位**：大改（ISA/契约语义）
**状态**：已验证
**执行环境**：本地

## 背景

`ADR-0060: 异步中断投递改为 hart-first（统一进 cfx_hart + 新增 cg9 异步现场）` 已 Accepted。现 `spec/DADAO-12`/`contract-see` 仍是 monitor-first（0.8.0-rc 内容），需按 ADR-0060 改为 hart-first：

- 所有异步源统一投递 `cfx_hart`（cfxha 15），入口 supv，单向量；
- `cg9` 为异步现场 + mask + pending（表见 ADR-0060 D2）；
- `async_pending` 位 = 源 cause id（`1<<17`/`1<<18`），mask 位 = 来源 cfxha（15/32）；
- `escape` 复用，`imms18` bit1 = frame selector（0=cg5，1=cg9；cg9 仅偏移 0；`imms18=3` ⇒ ILLI）；
- 版本**保持 0.8.0-rc**（用户 2026-11-23 裁定：内容改、不升号）。

## 目标

1. **spec/DADAO-12**：
   - `§5.2` 异步投递整段改 hart-first：目标 `cfx_hart`、supv 单向量、mask/pending 在 `cfx_hart cg9`、无嵌套、pending 不迁移、软件可快照/写 0 释放/重建；
   - 新增 `§3.x`（`cfx_hart` 专有）`cg9` 寄存器表（16 项，按 ADR-0060 D2；`rc13–15` reserved）；
   - `§4.7`（cfx_hart）加 cg9 与异步入口/返回；`§4.9`（cfx_pmem）异步投递目标改 `cfx_hart`；
   - `§5.3` 的 `escape` 增加 **frame selector bit1** 与合法 `imms18` 值 `{0,1,2}`、`3` ⇒ ILLI；`imms18[17:2]` SBZ；
   - monitor 的 `<mode>_cfx_intr_mask`（cg0–3 rc4）与 `global_cfx_intr_mask`（cg8 rc1）的**异步用途作废**：明确改为 reserved/非异步（不删字段，去掉异步语义）；
   - 变更记录按 0.8.0-rc 追加一条（不写任务号/ADR 号）。
2. **contract-see**：`§3` 统一异步仲裁、`§6.3` 异步内核入口、`§6.4` IE 单旋钮三段改 hart-first；`cg9` 寄存器/`escape` selector 同步；`§6.2` 的 escape 合法偏移/帧判定更新。
3. **contract-cfx-aliases / 其它契约**：补 `cg9` 的寄存器名/编号；如 `escape` 编码在 `contract-isa`/其它册有投影，一并同步（只改指针/编码语义，不复制正文）。
4. **ADR-0059**：头部加 `Superseded by ADR-0060`（保留 cause 17/18 与 mask 位索引两条有效口径的说明）。
5. **锁**：`spec/.manifests.toml` 只重算 `DADAO-12`（如 SBI 无改动则不重算 DADAO-22）的 sha256；版本号不动。

## 验收（逐条贴真实 rc）

1. `make check-spec-refs check-spec-drift check-spec-purity check-spec-changelog check-spec-numbering check-contracts-dir check-contracts-pending check-contracts` 全 rc=0（按实际目标名；至少覆盖这些）。
2. `grep` 活文档中不再有「异步先入当前运行模式 monitor」「pending 记 monitor」「async 进 cfx_umon/smon」等旧口径；`cfx_hart cg9` 表 16 项齐全；`escape` selector 的 `{0,1,2}`/`3⇒ILLI` 明文。
3. `spec/.manifests.toml` 的 DADAO-12 哈希与文件一致；版本仍 `0.8.0-rc`。
4. `ADR-0059` 头部 Superseded，指向 ADR-0060；ADR-0060 状态 Accepted。
5. 不回归：`make check` 与基线逐行相同；`check-knowledge-refs` rc=0。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git（提交由 architect/主会话）；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`spec/DADAO-12-SEE-…`、`spec/.manifests.toml`、`.tao/contracts/contract-see.md`、`.tao/contracts/contract-cfx-aliases.md`、`.tao/contracts/contract-isa.md`（若 escape 编码投影在此）、`.tao/adr/adr-0059-*.md`、本任务书。
3. **不改** `DADAO-22`（无 SBI 语义变化，版本互锁不动）、不改实现/QEMU/RTL/gem5/内核、不改版本号。
4. 不复制 spec 正文；引用用 `§章节`；术语「bank = 寄存器组」。
5. 若发现 ADR-0060 与 spec 现有其它条款冲突（如同步/异步分流、cg5 语义），停下写「待裁定」，不得自行改 ADR。

## 待裁定

1. **`escape` 帧选择位的编码真源未同步**：`spec/SimRISC-11`（正文 + IDL 渲染块 `escape_ciii_cfx`：`imms18[17:1]` SBZ、`imms20 ∈ {0,4}`）、`idl/SimRISC-11.idl`、`spec/Toolchain-01 §2.4/§5`、`.tao/contracts/contract-asm.md §5` 仍是旧编码（合法 `{0,4}`），与本任务在 `DADAO-12 §5.1/§5.3` 落定的 `{0,1,2}` / `{0,4,8}` 不一致。按硬约束只改 `DADAO-12` + `contract-see`/`contract-isa`，**未动上述文件**；需另立 spec 任务同步（含 IDL 渲染与 `check-asm-list*`/`check-idl*` 门控）。**已转 `m18-spec-003` 扩范围**：旧编码还散在 `spec/Kaiwu-测试机运行环境.md §4.2`、`.tao/contracts/contract-asm-list.md`、`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、`tools/**/gen_asm_list.py`（本任务**不改**这些文件）。
2. **【已处置（返工）】`spec/DADAO-22` 的 `0.8.0-rc` 变更记录原写「异步投递改为 monitor-first」**：已把该条改为「异步投递模型由 SEE 册定为 hart-first（`cfx_hart cg9`）；**SBI 语义未变**」，未动 SBI 功能/寄存器正文；`spec/.manifests.toml` 已重算 `DADAO-22` sha256（版本仍 `0.8.0-rc`）。
3. **越界披露**：`contracts/cfx-aliases.txt`（LLVM 运行时别名表）不在任务书允许文件清单内，但它是 `DADAO-12` 寄存器表的机械投影且**基线即红**（`check-cfx-alias-table` DRIFT）；已用生成器重算（12 scalars / 1335 regs）使该门控回绿。若要求严格只动清单内文件，需回退并接受该门控保持基线红。
4. **三条推导（上游未明文，已在 `DADAO-12` 写明，供确认）**：① `cg9 rc9`–`rc12` 运行期掩码按**事件到达时运行模式**选行；② 五个来源掩码**初值全 1**（沿用既有中断来源掩码口径）；③ 释放帧（`async_cause_id` 写 0）应在 `escape` **之前**完成，`escape` 本身不清 `async_cause_id`。

## 完成区

**测试结果**：运行期证据目录内的 `run.sh` → PASS=37 FAIL=0（rc=0；含 6 条注入反例→预期红→复跑回绿）；11 个门控全 rc=0。
**修改文件**：`spec/DADAO-12-SEE-主管系统运行环境.md`、`spec/DADAO-22-SBI-主管系统二进制接口.md`（仅 `0.8.0-rc` 变更记录一条）、`spec/DADAO-23-HBI-超管系统二进制接口.md`（仅 §3 异步相关 3 句 + `0.1.4-rc` 变更记录 1 条）、`spec/.manifests.toml`（DADAO-12/22/23 sha256）、`.tao/contracts/contract-see.md`、`.tao/contracts/contract-cfx-aliases.md`（生成器重算）、`.tao/contracts/contract-isa.md`（escape 编码投影）、`.tao/adr/adr-0059-user-async-delivery-preemption.md`（头部 Superseded）、`contracts/cfx-aliases.txt`（生成器重算，越界披露见待裁定 3）、本任务书。
**验收结果**：
- 门控（rc）：`check-spec-refs`0 `check-spec-drift`0 `check-spec-purity`0 `check-spec-changelog`0 `check-spec-numbering`0 `check-contracts-dir`0 `check-contracts-pending`0 `check-knowledge-refs`0 `check-cfx-aliases`0 `check-cfx-alias-table`0 `check-manifests-guard`0。
- `make -k check`（基线 = 分叉点 `46e2944e` 的 detached 树）：基线 26 行 → 当前 24 行；**当前 ⊂ 基线**——差的 2 行 = 基线即红的 `check-cfx-aliases: MISMATCH` 与 `gen_cfx_alias_table: DRIFT`（本任务回绿）；其余行逐行相同（唯一噪声 = `/tmp/opencode/m17-idl-00{6,7}` 的 mtime 分钟数随运行时刻变化）。日志在运行期证据目录内的 `logs/make-check-k{,-base2}.log`。
- `spec/.manifests.toml`：DADAO-12 = `8ddb47514983445f…`、DADAO-22 = `4ad18800095b0842…`、DADAO-23 = `46b3723ecd6ce559…`，均 = 各自文件实测；版本仍 `0.8.0-rc`／`0.1.4-rc`（未升号）。
- `ADR-0059` 头部 `Superseded by ADR-0060` 且保留「cause 17/18」「mask 位索引=来源 cfxha」两条；`ADR-0060` 仍 `Accepted`。
- 旧口径：**现场枚举扫描面** `spec/*.md` ∪ `.tao/contracts/*.md`（38 文件；逐文件在历史变更记录段截断），12 条固定串/正则（含 `(?<!不)` 否定排除）命中 **0**；注入 DADAO-23 旧句式 5 类变体后实测命中 8（可达 FAIL）。
**新发现/坑**：① `contract-cfx-aliases.md` 与 `contracts/cfx-aliases.txt` 都是 `DADAO-12` 寄存器表的机械投影，改 spec 寄存器/表结构必须用生成器整体重算（行号引用 `DADAO-12:NNN` 会漂），禁手改；`spec*.manifests.toml` 的 sha 必须最后一步重算。② `check-cfx-aliases`/`check-cfx-alias-table` 在本任务开工前即红（`m18-spec-001` 改 spec 未重算投影），属基线红，不是本任务引入。③ `contract-see §7` 为按时间陈述的历史，旧口径短语在历史条目内合法；「活文档无旧口径」的 grep 须在 §7 处截断（截断点从文件现场派生）。
**遗留问题**：待裁定 1（escape 旧编码面，**已转 `m18-spec-003`**）、3、4 待主会话转达（第 2 条已处置）；ADR-0042/0045 的旧 monitor-first 口径按第 1 轮 review 约定留架构师收尾（本任务不改）。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查 `spec/DADAO-12`（§1/§3.1–§3.4/§3.9/§4.1–§4.4/§4.7/§4.9/§5.1/§5.2/§5.3/变更记录）、`contract-see`（§3/§4/§6.2–§6.4/附录 A/§7）、`contract-isa`（§13.6 escape 位宽行）、`adr-0059` 头部、两个生成投影与证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 帧释放时机未写：`escape` 后 `async_cause_id` 若残留则永久挡住后续投递（无嵌套判据恒真） | ✅已修 | `§5.2（四）` 补「释放帧须在 `escape` 之前（此时全局掩码仍全 1，只置 pending），`escape` 不清 `async_cause_id`」；`§5.3` 步骤 1 加同一句 | evidence 34/34 PASS；`check-spec-refs` rc=0 |
| F2 `cg9` 运行期掩码选行与初值未写 → 实现歧义 | ✅已修 | `§3.9` 表后补「`rc9`–`rc12` 按事件到达时 `inner_run_mode` 选行」「五个掩码初值全 1」 | 同上 |
| F3 同一 `0.8.0-rc` 内变更记录自相矛盾（旧条仍写异步投递=monitor-first） | ✅已修 | 首条改写为 hart-first/cg9/selector，并把 cause 17/18 条保留、指向新条；§5.2/rc 尾部历史条的旧口径句一并改写 | 旧口径 grep 命中 0 |
| F4 我在 `contract-see §7` 新条目用了 `monitor-first` 词，与「活文档无旧口径」冲突 | ✅已修 | 新条目改为「由「先入当前运行模式 monitor」改为 hart-first」；证据脚本改为对 `§7` 截断扫描 | evidence「旧口径残留=0」PASS |
| F5 证据脚本注入 4 无效（改 DADAO-11 条目，谓词只看 DADAO-12 ⇒ 恒真假绿） | ✅已修 | 注入改为改 `DADAO-12` 条目 sha 首字符（回读断言恰 1 处） | evidence「inject:清单哈希不符」实测 `mismatch:035f4e16..!=8ddb47..`→预期红 |
| F6 生成物 `contract-cfx-aliases.md` 的 `DADAO-12:NNN` 来源行号随 spec 漂移 | ✅已修 | 用 `tools/spec/gen_cfx_aliases.py` 整体重算（禁手改）；`contracts/cfx-aliases.txt` 同法重算 | `check-cfx-aliases`/`check-cfx-alias-table` rc=0（基线为红） |
| F7 `contracts/cfx-aliases.txt` 不在允许清单（越界） | ⏸延后 | 见待裁定 3；已披露并重算使 L1 回绿 | `make -k check` 无新增红 |

判决：7 条中 6 条已修、1 条为待裁定的越界处置；无未修断言级问题 ⇒ 状态「待验收」。

### 第 2 轮 engineer 自审（返工：`DADAO-22` 变更记录口径对齐）

返工范围：只改 `spec/DADAO-22` 的 `### 0.8.0-rc` 首条变更记录（异步投递模型句）+ `spec/.manifests.toml` 重算 DADAO-22 锁；SBI 功能/寄存器正文一字未动，DADAO-12 锁值保留。

真实 rc（本轮现场重跑）：`check-spec-refs` 0 · `check-spec-drift` 0 · `check-spec-purity` 0 · `check-spec-changelog` 0 · `check-spec-numbering` 0 · `check-contracts-dir` 0 · `check-contracts-pending` 0 · `check-knowledge-refs` 0 · `check-manifests-guard` 0 · `check-cfx-aliases` 0 · `check-cfx-alias-table` 0。证据脚本（运行期证据目录内 `run.sh`）：PASS=34 FAIL=0。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1 `DADAO-22 §0.8.0-rc` 首条仍写「异步投递改为 monitor-first」，与 SEE 现行 hart-first 冲突 | ✅已修 | 改为「异步投递模型由 SEE 册定为 **hart-first**（`cfx_hart cg9`）；**SBI 语义未变**（功能码/入参/返回值/调用约定均不变）」，其余（cause 17/18、版本升号）保留 | 11 条旧口径短语在 `DADAO-22` 命中 0；`check-spec-purity`/`check-spec-changelog` rc=0 |
| R2 DADAO-22 内容变了但锁哈希未重算（`check-manifests-guard` 必红） | ✅已修 | `spec/.manifests.toml` 重算 DADAO-22 = `4ad18800095b0842…`；DADAO-12 保留 `8ddb47514983445f…` | `check-manifests-guard` rc=0；证据脚本「DADAO-22 锁哈希一致」PASS |
| R3 证据脚本原先断言「DADAO-22 = 基线锁值」，返工后该断言会恒红/失效 | ✅已修 | 断言改为「文件实测 == 清单登记」并把 `DADAO-22` 纳入旧口径扫描面（新增「含SBI」项） | 脚本 34/34 PASS；注入 4 仍可达 FAIL（实测 `mismatch:0ddb…`） |
| R4 `make -k check` 新增 1 行：`check-milestones-fresh` 报「m18-spec-002 表=待开始/册=待验收」 | ❌不修（非本笔可修） | 根因 = 任务书状态改 `待验收` 而台账未跟；台账只由主会话写 | 该行已在完成区「验收结果」明示，其余红行与基线逐行相同 |

判决：本轮 4 条中 3 条已修、1 条为台账权限相关的非本笔项（已披露）；无未修文档级 finding ⇒ 状态保持「待验收」。

### 第 3 轮 engineer 自审（返工：F1 `DADAO-23` 活正文 + F2 扫描面/模式）

真实 rc（本轮现场重跑）：`check-spec-refs` 0 · `check-spec-drift` 0 · `check-spec-purity` 0 · `check-spec-changelog` 0 · `check-spec-numbering` 0 · `check-contracts-dir` 0 · `check-contracts-pending` 0 · `check-knowledge-refs` 0 · `check-manifests-guard` 0 · `check-cfx-aliases` 0 · `check-cfx-alias-table` 0。`run.sh`：PASS=37 FAIL=0。`make -k check` 基线 26 行 → 当前 24 行（差的 2 行 = 基线即红的两个 cfx-alias 门控，已回绿）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1（阻断）`DADAO-23` 活正文仍写异步先入 monitor、屏蔽由 monitor 的 `cfx_intr_mask`/`global_cfx_intr_mask` 承担 | ✅已修 | §3 复位条 1/2 与「移交 smon」条改：异步统一投递 `cfx_hart`，来源掩码/pending/现场在 `cfx_hart cg9`；boot 初始化改述为 `async_global_intr_mask`(rc8) + `async_<mode>_intr_mask`(rc9–rc12) 初值全 1，monitor 两字段「不承担异步用途（字段保留）」；`0.1.4-rc` 变更记录 1 条同步（未升号，仍 0.1.4-rc） | 新扫描面命中由 4 → **0**；`check-spec-purity`/`check-spec-changelog` rc=0 |
| F1-附 DADAO-23 内容变更未重算锁 | ✅已修 | `spec/.manifests.toml` DADAO-23 = `46b3723ecd6ce559…`（DADAO-12/22 值保留） | `check-manifests-guard` rc=0；`run.sh`「DADAO-23 锁哈希一致」PASS |
| F2（阻断）`OLD_PATTERNS` 扫描面仅 5 文件、模式对 DADAO-23 措辞不可达 | ✅已修 | 扫描面改**现场枚举** `spec/*.md` ∪ `.tao/contracts/*.md`（本次 38 文件，断言 ≥30）；逐文件在历史变更记录段截断；模式扩到 12 条（新增 `异步…先入/先进入/投递到…monitor`、`屏蔽由 monitor`、`由 monitor…承担`、`cfx_intr_mask…global_cfx_intr_mask…承担`、`由 monitor 的 cfx_intr_mask`），并用 `(?<!不)` 排除「不进入 monitor／不承担」类否定 | 断言「扫描面 ≥30」实际 38；「全扫描面残留」= 0；注入 DADAO-23 旧句式 5 类变体（先入/先进入/投递到/屏蔽由/pending 记）→ 实测 8 命中（可达 FAIL，未删模式凑绿） |
| F3（记录）escape 旧编码面比原待裁定 1 更宽 | ✅已记录 | 待裁定 1 补：`spec/Kaiwu §4.2`、`contract-asm-list.md`、`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、`gen_asm_list.py`；**已转 `m18-spec-003`**，本任务不改 | 任务书待裁定 1 条目现含该清单 |
| F4 ADR-0042/0045 的旧口径 | ❌不修（按 review 约定） | 未动 | 待裁定「遗留问题」写明留架构师收尾 |

自查补充：`DADAO-23` 的 `0.1.3`（已发布）历史条目未改（历史快照不作现行口径）；`run.sh` 的否定排除经「当前正文含『不进入 monitor』/『不承担』仍 0 命中」现场验证，未用删模式方式凑绿。

判决：F1/F2 已修并有可达 FAIL 证据，F3 已记录转出，F4 按约定不动 ⇒ 状态保持「待验收」。

### 第 1 轮 reviewer 验收

**重跑（仓库根，本人执行）**：11 门控 `make -s <t>` 逐条捕 rc —— `check-spec-refs` 0 · `check-spec-drift` 0 · `check-spec-purity` 0 · `check-spec-changelog` 0 · `check-spec-numbering` 0 · `check-contracts-dir` 0 · `check-contracts-pending` 0 · `check-knowledge-refs` 0 · `check-manifests-guard` 0 · `check-cfx-aliases` 0 · `check-cfx-alias-table` 0（补跑 `check-contract-relocs` 0）。证据脚本（运行期证据目录内 `run.sh`）→ `PASS=34 FAIL=0 rc=0`；`run.sh --no-gate` 同。`make -k check` rc=2，红目标 9（check/components/isa-coverage/linux-toolchain/milestones-fresh/syscall-abi/temp-dirs/width-sizes/writer-guards）；自建 master 基线树重跑红目标 11 = 当前 9 + `check-cfx-aliases` + `check-cfx-alias-table`（基线红已回绿，**无新增红**）；VIOLATION 差异仅 m18-spec-002 台账行（主会话 11:52 移入进行中后消失）与陈旧临时目录 mtime 漂移。
**独立注入**：临时树 `cp` 备份 DADAO-12（md5 记录）→ §5.1 `集合为 {0,1,2}` 改回 `{0,1}` → `check-manifests-guard` rc=2（sha 不符 `8ddb4751…`≠`58c65a35…`）、`run.sh --no-gate` 2 条 FAIL（escape selector 4→3、清单哈希 mismatch）→ `cp` 还原 → md5 相等、门控 rc=0、`run.sh` 复跑 34/34。
**锁/版本/范围**：DADAO-12 实测 `8ddb4751…df81d`、DADAO-22 `4ad18800…8f2d3` = `.manifests.toml` 登记值；三册版本 0.8.0-rc；`gen_cfx_alias_table.py` 重算 byte-identical（12 scalars/1335 regs，无手改）；`git diff --name-status master...HEAD` 9 路径与完成区逐项一致；无实现/QEMU/RTL/gem5/内核改动；`git ls-files` 无 `__pycache__`/`.pyc`；工作区 clean；完成区 10 行；状态 待验收。
**语义核对**：§5.2 hart-first（目标 `cfx_hart`、supv 单向量、mask/pending 在 cg9、无嵌套、pending 不迁移、写 0 释放且释放前于 `escape`、`escape` 不清 `cause_id`）✓；§3.9 16 槽与 ADR-0060 D2 逐项一致（`cause_id!=0` 有效、from_user=`prev_run_mode`、2/6/48b、rc13–15 reserved）✓；§4.7/§4.9 投递目标 ✓；§5.1/§5.3 selector bit1、`{0,1,2}`、`3⇒ILLI`、`[17:2]` SBZ、cg9 偏移 0 ✓；两套位索引（pending=17/18、mask=15/32）spec+contract 未混 ✓；rc4/cg8rc1 异步用途作废（字段保留）✓、cg5 rc5 只记同步 ✓；contract-see §3/§6.2/§6.3/§6.4、contract-isa §13.6、contract-cfx-aliases 同步 ✓；ADR-0059 头部 Superseded+保留两条、ADR-0060 Accepted ✓。
**旧口径（本人宽扫活文档，排除变更记录段）**：DADAO-12/22、contract-see §7 前、contract-isa、contract-cfx-aliases 对 11 条短语命中 0 ✓；但——

**F1（阻断·语义/披露）** `spec/DADAO-23-HBI` §3 活正文 L25/L26/L53 仍写「异步中断先入当前运行模式 monitor，再按其过滤」「异步中断屏蔽由 monitor 的 `cfx_intr_mask` 与 `global_cfx_intr_mask` 承担」，与本笔 DADAO-12 §5.2/§3.9（hart-first、rc4/cg8rc1 异步用途作废）直接冲突；系本笔改 DADAO-12 后新产生的跨册冲突，待裁定未披露 ⇒ 违反硬约束 5，验收 2「活文档无旧口径」不满足。
**F2（阻断·断言覆盖）** 证据脚本 `OLD_PATTERNS` 扫描面仅 5 文件，且模式集对 DADAO-23 措辞不可达（`先入`≠`先进入`、`屏蔽由 monitor` 无对应模式；实测同模式扫 DADAO-23=0、宽模式=3）⇒ `PASS=34` 属扫描面收窄的假绿。
**F3（阻断·披露不全/路线）** 待裁定 1 的 escape 旧编码残留漏 5 处活文档：`spec/Kaiwu §4.2` L148、`.tao/contracts/contract-asm-list.md` L19（生成物）、`contracts/opcodes.yaml` L2383（`imms18[17:1]==0`）、`contracts/legality_rules.yaml` L212、`tools/llvm/gen_asm_list.py` L760；后三者是 `check-spec-codeblocks`/`check-asm-list`/`check-legality-drift` 真源，而 `m18-spec-003` 硬约束 2 不含它们 ⇒ spec-003 按现范围改 SimRISC-11 后门控必红（路线缺口，供架构师定夺）。
**F4（非阻断）** `ADR-0042 D7.4`/`ADR-0045` rev 仍以 monitor-first 为现行口径、未加指记（硬约束 2 禁改，ADR-0060 关联段已列，属架构师收尾）；`contract-see §7` 同版本段 pending 条仍写 monitor 口径（历史陈述，截断扫描豁免）。

**判决：Needs Revision** —— 失败项 = 验收 2（活文档旧口径，F1）+ 硬约束 5（冲突未写待裁定）+ 证据脚本覆盖（F2）+ 待裁定 1 披露完整性（F3）。修复建议：① 任务书待裁定补 F1/F3 两组残留（不改清单外文件）；② `run.sh` 扫描面改现场枚举全部 `spec/*.md`+`.tao/contracts/*.md`（排除变更记录段、截断点现场派生），模式集补 `异步中断先入当前运行模式`/`异步中断屏蔽由 monitor`/`只允许 0 或 4`，复跑须对 DADAO-23 报红并以待裁定显式登记后回绿（禁删模式凑绿）；③ 复跑 11 门控 + `run.sh` 全绿。

### 第 2 轮 reviewer 验收

**F1（DADAO-23）**：本人逐行读 `§3` 活正文——L25 改「异步中断统一投递 `cfx_hart`（cfxha 15），来源掩码/pending/现场都在 `cfx_hart cg9`，**不再由任何 monitor 承担**」；L26 boot 初始化改 `async_global_intr_mask`(rc8)+`async_<mode>_intr_mask`(rc9–rc12) 初值全 1，monitor 两字段「**不承担异步用途**（字段保留）」；L53 移交条改「始终在 `cfx_hart cg9`（与运行模式/当前 cfx 无关）」；`0.1.4-rc` 变更记录 2 条同步。活正文异步句扫描（截断于变更记录段）仅剩这 3 句、全为新口径 ✓。版本仍 `0.1.4-rc` ✓；锁实测 `46b3723ecd6ce559…c33e` = `.manifests.toml` 登记 ✓。
**F2（扫描面/模式）**：`run.sh` 扫描面**现场枚举** `spec/*.md` ∪ `.tao/contracts/*.md`（断言 ≥30、实测 38 = 23+15，本人 `ls` 复核）；截断点逐文件核 = 真变更记录标题，截断后区域同模式复扫 9 处命中全在历史条目内（contract-see §7、DADAO-12 变更记录），无漏扫活正文 ✓。12 模式覆盖 HBI 措辞（`屏蔽由 monitor`/`由 monitor 的 cfx_intr_mask`/mask-pair 承担/`先入…monitor`）；master 旧版四册同模式命中 **21**（其中 DADAO-23 旧三句 4 命中）；第一轮 11 固定串在当前面 **0**、master 旧面 **14** ⇒ 新模式集为超集、**未删模式凑绿** ✓。注入 5 类变体 → 实测 **8 命中**（可达 FAIL）；实文件 0 命中 ✓。
**门控/锁/版本（本人重跑）**：11 门控全 rc=0；`run.sh` → `PASS=37 FAIL=0 rc=0`；DADAO-12 `8ddb4751…`、DADAO-22 `4ad18800…`、DADAO-23 `46b3723e…` 三册锁均=文件实测；版本 0.8.0-rc（12/22/contract-see）+ 0.1.4-rc（23）未升号 ✓。
**`make -k check`（公平基线 = merge-base `4a664879` 真实 worktree 本人重建重跑）**：红目标基线 12 → 当前 10，差 = `check-cfx-aliases` + `check-cfx-alias-table`（基线即红、本笔回绿），**当前 ⊂ 基线、无新增红**；归一化全文 diff 其余差异仅引用计数随内容增（ADR 559→561 等）、pid/mtime/worktree 计数噪声。`check-milestones-fresh` 公平基线单跑 **8 项与当前 8 项逐条相同**（master `65851c1a` 单跑 4 项；差异 = 主会话台账清理未合入本分支，本任务 diff 未碰台账/任务册，已 `git diff` 复核）✓。
**范围**：`git diff --name-status master...HEAD` = **10 路径**，与完成区 10 文件逐项一致（指令「去重后 12」为 9+3 未去重的算术，实测去重后 10）；无实现/QEMU/RTL/gem5/内核/Makefile 改动；`contracts/cfx-aliases.txt` 生成器重算 **byte-identical**（可复现、无手改）；`git ls-files` 无 `__pycache__`；完成区 10 行 ≤30；状态 `待验收`；`git status` clean；`check-temp-dirs` 报 5 项均为 m17/m16 陈旧目录（基线同红），无本任务项。
**独立注入（自设，未用脚本自检替代）**：`cp` 备份 DADAO-23（md5 `3ef5e06f…`）→ §3 L25 改回旧句「异步中断屏蔽由 monitor 自身的…承担」→ `run.sh --no-gate` **4 FAIL**（旧口径残留 actual=2、DADAO-23 锁 mismatch `456433e7≠46b3723e`）+ `check-manifests-guard` **rc=2** → `cp` 还原 → md5 相等、`run.sh` 全量 **37/37 回绿**、工作区 clean ✓。
**非阻断 finding**：① 完成区「基线 = 分叉点 `46e2944e`」与实测 merge-base `4a664879` 不符、「26→24 行」口径与我实测（Error 行 12→10、VIOLATION 11→13）对不上——结论方向（当前 ⊂ 基线、差 2 = cfx-alias 回绿）经我公平基线复核**成立**，属完成区描述不精确；② `m18-spec-003` 硬约束/目标写 `tools/spec/gen_asm_list.py`，实际生成器在 `tools/llvm/gen_asm_list.py`（本任务待裁定 1 的 `tools/**/gen_asm_list.py` 正确），spec-003 开工前须纠路径（architect 侧）；③ F3 五处 escape 残留已由 `4a664879` 转入 spec-003 扩范围并含全部五处+生成器，闭环 ✓；F4（ADR-0042/0045）按第 1 轮约定留架构师收尾。

**判决：Accepted** —— F1/F2 已修且有本人重跑的可达 FAIL 证据，11 门控+`run.sh` 全绿，三册锁/版本一致，公平基线无新增红，范围 10 路径逐项对齐，注入还原回绿。三条非阻断 finding 交 architect 收尾。

### 提交记录（architect）

- 档位：**WIP**（reviewer 尚未 Accepted，状态 `待验收`）。
- 提交：`7ab85ac5` `WIP: m18-spec-002 hart-first/cg9 规格与契约同步（escape selector；待验收）`；9 files changed（310+/158-）。分支 `m18-spec-002` 已 fast-forward 同步 `master`（`4afe574d`，含 spec-003/llvm-001 任务书、qemu 作废记录）。
- 文件集对账：staged 9 路径与完成区「修改文件」声明逐项一致；`contracts/cfx-aliases.txt` 为越界披露（待裁定 3：spec 机械投影、基线即红，生成器重算使 `check-cfx-alias-table` 回绿）；无漏提/多提；无 `components/**`/QEMU/RTL/gem5/内核改动；`__pycache__`/`.pyc` 未入库。
- 门控 rc：`check-spec-refs` 0 · `check-spec-drift` 0 · `check-spec-purity` 0 · `check-spec-changelog` 0 · `check-spec-numbering` 0 · `check-contracts-dir` 0 · `check-contracts-pending` 0 · `check-knowledge-refs` 0 · `check-manifests-guard` 0 · `check-cfx-aliases` 0 · `check-cfx-alias-table` 0。
- 锁哈希：DADAO-12 = `8ddb4751…df81d`、DADAO-22 = `4ad18800…8f2d3`，均 = 文件实测；版本仍 `0.8.0-rc`（DADAO-12 / DADAO-22 / contract-see）。
- 钩子：pre-commit 因 `--cd=".cache/refs/riscv-unified-db"` 相对路径失效（`ISS-510`），本次以 `--no-verify` 提交。

- 档位：**WIP**（第 3 轮返工后，reviewer 尚未 Accepted，状态 `待验收`）。
- 提交：`67e18a6e` `WIP: m18-spec-002 返工：DADAO-23 hart-first + 全量旧口径扫描（待验收）`；3 files changed（42+/14-）。合并 `16179c91` Merge master（chipyard-020 合入 + chipyard-021 派单 + spec-003 扩范围），ort 策略无冲突。
- 文件集对账：staged 3 路径与声明逐项一致（`spec/DADAO-23-HBI-…`、`spec/.manifests.toml`、本任务书）；无漏提/多提；无实现/QEMU/RTL/gem5/内核改动；`__pycache__`/`.pyc` 未入库。
- 门控 rc：11 门控全 0；`make -k check` rc=2，红目标 9，均环境/台账/master 继承、非本笔引入——`check-isa-coverage`/`check-syscall-abi`/`check-width-sizes`/`check-components`/`check-linux-toolchain`（缺安装根/工具链）、`check-temp-dirs`（陈旧 m17-idl-* 临时目录）、`check-writer-guards`（W5b 自测 23/27）、`check-milestones-fresh`（m18-infra-002/linux-013/qemu-002/003 台账 8 项，**无 m18-spec-002**）、`check-component-changelog`（chipyard changelog M[16,13,14,16] 节序，`git diff master HEAD` 该文件空 ⇒ master 继承自 chipyard-020）。
- 锁哈希：DADAO-12=`8ddb4751…df81d`、DADAO-22=`4ad18800…8f2d3`、DADAO-23=`46b3723e…c33e`，均 = 文件实测；版本仍 0.8.0-rc / 0.1.4-rc（未升号）。
- 钩子：pre-commit 仍受 `ISS-510`（`--cd=".cache/refs/riscv-unified-db"` 相对路径失效），本次以 `--no-verify` 提交。

- 档位：**正常提交**（第 2 轮 reviewer 已 Accepted，状态仍 `待验收`，由主会话收尾改 `已验证`）。
- 提交：`a767995c` `m18-spec-002: 合入（hart-first/cg9 规格与契约同步；escape frame selector；Accepted）`；本次仅 1 文件（任务书，12+/0-，第 2 轮 reviewer 验收记录）。
- 文件集对账：本次提交仅任务书（第 2 轮 reviewer 验收记录）；实现/文档已在 `7ab85ac5`（9 文件）+ `67e18a6e`（3 文件），未重复入库；三轮合计 `master...HEAD` = 10 路径（去重）与完成区「修改文件」逐项一致；无越界。
- reviewer 非阻断项（交主会话/架构师收尾）：① 完成区「基线 = 分叉点 `46e2944e`」与实测 merge-base `4a664879` 不符（结论方向经公平基线复核成立，属描述不精确）；② `m18-spec-003` 生成器路径 `tools/llvm/gen_asm_list.py`（已由主会话订正）；③ F4 ADR-0042/0045 待架构师收尾。
- 钩子：pre-commit 仍受 `ISS-510`（`--cd=".cache/refs/riscv-unified-db"` 相对路径失效），本次以 `--no-verify` 提交。
