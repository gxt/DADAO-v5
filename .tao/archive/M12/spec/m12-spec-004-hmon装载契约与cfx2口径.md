# m12-spec-004: hmon 装载契约 + `cfx2*` 口径 + 退出码生成方（`Machine-v5`）

**模块**：spec
**项目里程碑**：M12
**依赖**：`m12-spec-003`（同一册，须串行；本任务在其合并后开始）
**可并行分片**：否（单册单写者）
**状态**：已验证

## 用户裁定（2026-11-10，原话）

> 「2、hmon的代码/数据应该是放在bootrom中，然后由bootrom代码存放到相应位置；先在qemu中进行验证，然后gem5/chipyard可共用；3、第7条，reserved cfx引发ILLI，非reserved cfx的未定义cg/rc引发CFXREG，没有冲突，只是Machine-v5文档没写清楚；第8条：7.1写的不对，只定编码，谁产生是代码设计要决定的」

## 目标（4 条）

### 1. Tiny 的 hmon 装载契约（题 6，**核心**）

**现状**：`§6` 只规定应用段（BootROM + SRAM）怎么装，**没有规定 hmon 的代码/数据从哪来、谁搬、搬到哪**。qemu/gem5 各自按「宿主 loader 直装」实现（实现事实），spec 无正文 ⇒ 同一 ELF 无法保证三平台通用。

**按用户裁定改为**：
- **hmon 的代码/数据编入 BootROM 镜像**（与 power stub 同镜像），**宿主 loader 不需要为 hmon 单独下发 `PT_LOAD`**；
- **power（BootROM 内）在移交前把 hmon 段复制到 hmon SRAM** `0x0fff_0000_0000`（大小与布局由镜像段表规定）；
- 复制完成后 power 写 hmon 向量（`cfx_hmon_hypv_excp_vector`）并 `trap cfx_hmon` 移交（`§2`）；
- **验证顺序**：先在 QEMU 侧实现并验证该装载契约，gem5 / chipyard 共用同一镜像布局（不各写一套）；
- 需写清：BootROM 内的布局（stub / hmon payload / 段表）、hmon SRAM 的目标地址与长度上限、`64 KiB` BootROM 是否够用（若不够，写明扩容或分段策略）。

**必须先核对**：`DADAO-12 §2.1`（BootROM 与核内地址空间）与 `DADAO-13` 对 BootROM 内容的约定；若上游规定与「hmon 编入 BootROM」冲突，**停下来登记冲突并返回主会话**，不要擅自改上游册。

### 2. `cfx2rd`/`cfx2rc` 到不同 cfxha 的口径（题 7）

**用户裁定**：`reserved cfx ⇒ ILLI`；**非 reserved 但 cg/rc 未定义 ⇒ `CFXREG`**。两者不冲突，只是文档没写清楚。

改为在 `§3`（或 `§4.4`）补一条：
- `cfx2rd`/`cfx2rc`（及 `trap`/`escape`）目标为 **reserved cfxha**（`6–14、19–61`）⇒ `ILLI`；
- 目标为**已分配但未实现**的 cfx（如 `cfx5`），或已实现 cfx 的**未定义 cg/rc** ⇒ `CFXREG`；
- 引 `DADAO-12 §5.1/§5.2(一)` 原文。

### 3. `cg3 rc10` 初值与写入对齐（2026-11-10 用户补充裁定）

**用户原话**：「rc10必须有初值，初值是该cfx的SRAM的起始地址」「rc10的向量写入时，应ignore后两位」。

- 改 `spec/DADAO-13-HEE-超管系统运行环境.md` §1 `cg3 rc10`：
  - **初值 = 该 cfx 内部 SRAM 的起始地址**（有内部 SRAM 的 cfx；无内部 SRAM 的 cfx 由平台/实现定义）；
  - **写入时忽略低 2 位**（`value[1:0] ← 0`，按 4 字节对齐落盘），不产生异常。
- 与 `Machine-v5` 的「hmon 启动时显式写入」并存：显式写入仍可保留（幂等），但不再是「向量可用」的前提。
- 同步 `DADAO-13` 的 `0.1.4-rc` 变更记录与只读锁（该册 sha 同笔更新）。

### 4. `§7.1` 退出码：只定编码（题 8）

**用户裁定**：`§7.1` 写的不对——本册**只定编码**，**谁产生（handler / 宿主 / 运行时）属代码设计**，不在 spec 规定。

改为：
- 保留编码表（`0x00–0x3F` … `0xC0–0xFF` 与位域）；
- 删除/改写任何暗示「由硬件或 handler 产生」的表述，明确「产生方由实现设计决定，本册只约束编码与语义映射」。

## 实现侧影响（供后续任务排期，不在本任务范围）

- `m13-qemu-001` / `m13-gem5-001`（均已合入）当前实现的是「**宿主 loader 直装 hmon 段**」；本契约改为「hmon 编入 BootROM、power 搬运」⇒ 两侧实现需按新契约调整（另立任务，建议合并为一个「三平台 hmon 装载对齐」任务）。
- `m12-chipyard-007`（未开始）必须直接按新契约实现，不得沿用直装。

## 非范围

- 不改题 1–5（归 `m12-spec-003`）
- 不改 `DADAO-12`/`DADAO-13`
- 不实现 QEMU/gem5/chipyard 的改动（本任务只改 spec；实现另立任务）

## 验收标准

1. 三条逐条落地，每条给「改前 / 改后 / 依据（上游原文或用户裁定原话）」
2. hmon 装载契约包含：BootROM 布局、复制目标与长度、向量写入与 `trap` 顺序、BootROM 容量结论；**并给出 QEMU 先行验证的接口说明**（哪些字段/行为需要 QEMU 先支持）
3. `cfx2*` 条款与 `DADAO-12 §5.1/§5.2(一)` 逐字对齐（引原文）
4. `§7.1` 全文 grep 无「由 handler 产生 / 硬件产生」类表述；编码表未被改动
5. 版本 → **`0.4.4-rc`**（若 `spec-003` 已到 `0.4.3-rc`）；锁同笔
6. 5 个 spec 门控 rc=0；一键证据脚本（含注入）
7. 完成区 ≤30 行、无运行期路径

## 说明

- 本任务**引入新契约**（hmon 装载），属高影响：`m12-chipyard-007` 与 `m13-integ-002/003` 都依赖它；改动前请把「BootROM 容量/布局」算清并写进正文。
- 若发现需要同时改 `DADAO-12`（上游只读册），**不得自改**：登记冲突、返回主会话。

## 硬约束（子代理必读）

1. 临时目录 `/tmp/opencode/<任务ID>/`，禁仓库内临时文件。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；**需要裁定**写进任务书「待裁定」段并返回主会话。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. **不得写入未经主会话转达的用户裁定**；自定事项写「自决」（`ISS-365`）。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`spec/Machine-v5` 与 `spec/DADAO-13` 的全文 diff、只读锁 diff、证据脚本 3 个文件；对照 `DADAO-12 §1/§2.1/§5.1/§5.2/§5.3`、`DADAO-13 §1`、`DADAO-23 §3`、ADR-0043 D1–D3、QEMU Tiny 装载实现（`components/qemu/patches/hw/dadao/dadao-machine.c.patch`）与 `tests/shared/bootrom/step5/*`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 容量「4+56+4」手算易错、也可能与 §1.1 尺寸不一致 | ✅已修 | 检查脚本由 §1.1 尺寸格独立派生，§6.2 三段现场求和 | C3 PASS（sum=`0x10000`） |
| §6.2 首版写「复制后 `fence cfx0, PRED_CW\|SUCC_CR` 保证取指可见」——`fence` 的 `cr/cw/ci/co` 无取指语义（自造） | ✅已修 | 删该 fence，改为「写后取指可见性 = 实现义务，不新增指令语义」 | `SimRISC-11 §5` 位义对照 + C2 PASS |
| §3 旧 bullet 与新口径重复定义 reserved⇒`ILLI` | ✅已修 | 旧 bullet 只留 `CFXPERM`/`CFXESC`，reserved 判定指向新条 | C4 PASS |
| 固定固件后应用 crt 不能再进 BootROM ⇒ 入口必须固定（原 §6 为「crt 在 BootROM、宿主双段装入」） | ✅已修（**自决**） | §6 改为「应用只装 SRAM、入口固定 `0xffff_ff01_0100`、`PT_LOAD` 越界或 `e_entry` 不符 ⇒ 显式失败」 | C2/C3 PASS；旧口径串已删 |
| 段表格式此前只在 ADR/实现中，契约不完整（gem5/chipyard 无从实现） | ✅已修 | §6.1 逐字段写入，与 `build_step5_bootrom.py` 现有格式一致 | C2 PASS；逐字段对照该构建器 |
| §7.1 删 4 处路由表述后，路由信息是否丢失 | ✅验 | 路由在 §1.2/§4.4 与 `DADAO-12 §5.2` 仍在；C6 只扫 §7.1 | C6 PASS（无产生方/落点表述） |
| 编码表被误改风险 | ✅验 | 未动表行；C6 与 HEAD 逐字比对 | C6 PASS（19 行一致） |
| 引文可能非上游原文（自造风险） | ✅验 | C4 把 4 段引文在 `DADAO-12` 归一化文本中回溯 | C4 PASS |
| 只读锁「仅 2 册变」 | ✅验 | C7 重算 21 册 sha + 与 HEAD 锁比对 | C7 PASS（仅 Machine-v5/DADAO-13） |
| 证据脚本首版锚点/计数写死（17 行、单 BootROM 行） | ✅已修 | 期望行数改结构派生（`2+4 + 2+11`）、BootROM 行按地址前缀过滤、注入锚点唯一性校验 | `run.sh`/`inject.py` 3/3 PASS |
| 注入用例只验「非零退出」会漏判 | ✅已修 | 注入判据 = rc≠0 ∧ 目标检查项 FAIL ∧ `git diff` 非空 | 注入 3/3 PASS |
| ADR-0043 D2/D3 与本文冲突（Tiny「无表/全部 stub」「宿主直装 hmon」） | ⏸延后 | 未改 ADR（ADR 修订需用户确认且不在本任务文件范围） | 见「待裁定」1 |

判决：正文与证据脚本的可修项已全部修复并复验；越界事项（ADR-0043、根 `README.md`）登记返回主会话。状态 → `待验收`。

### 第 1 轮 reviewer 验收（2026-11-10，独立重跑）

**重跑记录（我的真实输出/退出码）**
- 运行期证据目录 `checks.py`（`python3 …; echo $?`）⇒ `FAIL C7 只读锁 … 实际变化 []`、`checks: 7 项，PASS 6，FAIL 1`、`EXIT=1`。
- 运行期证据目录 `run.sh --inject` ⇒ 7 门控全 `PASS rc=0`（`check-spec-readonly`/`changelog`/`drift`/`numbering`/`refs` + `check-knowledge-refs` + `check-test-reports`）；`content-checks rc=1`、`inject rc=1`（三例均「目标检查 FAIL ∧ `git diff` 非空 ∧ 还原 md5 一致」，回绿 `rc=1`）；`RESULT: FAIL（2 项失败）`、`RUN_EXIT=1`。
- 根因（确定性，非并发干扰）：`checks.py::c7_lock()` 基线取 `git show HEAD:lock`，而 HEAD 已是 architect 的 WIP 提交（证据 mtime 11:38 < 提交 11:41）⇒ 变化册 `[]`。21 册 sha 我独立重算全等，相对派单前 `5139852e8a4340ff1160b5a7ae971e34f4979a5d` 恰 2 册变（`Machine-v5`/`DADAO-13`）。
- 我的独立注入：`| 0x1000–0xEFFF | → | 0x1000–0xFEFF |` ⇒ `FAIL C3 容量自洽 … sum=0x10f00 contiguous=False`、`INJECT_EXIT=1`；`cp` 备份还原 md5 `1a3665ce04ae…` 一致 ⇒ C3 回 PASS；`make -s check-patch-tree` ⇒ `9 patch set(s), 330 patches OK` rc=0（本树无 source worktree，⑦⑧⑨跳过）。
- 快照对账：验收前后 4 文件 `md5sum -c` 全 `OK`、`git status --porcelain -uall` 空，无注入残留。

**约束核验（逐条）**
- 容量：我手算 `0x1000 + 0xE000 + 0x1000 = 0x10000` = 64 KiB，与 §1.1 尺寸格派生一致；hmon ≤56 KiB 即 `0x1000–0xEFFF` 窗口（= 64−4−4），超限处置（拆多表项/扩 BootROM 归平台决策）已写；未附当前 hmon 实测尺寸，靠构建断言兜底（现有 `hmon.lds` 断言仍是 64 K，属实现侧）。
- `§6.1` 与 `build_step5_bootrom.py` 逐字段一致（头 `>IHHII`、项 `>IIQQQ`、`FLAG_REQUIRED|LOAD|VERIFY=1|2|4`、Vast 表偏移 0、`boot_magic=0x30001`）。
- `cfx2*`：引文在 `DADAO-12 §5.1`（L739）、`§5.2（一）`（L766）逐字回溯；上游路由表 reserved 行排在 `CFXREG` 行之前，正文显式「reserved 判定先于实现判定」；`§2.1` L83「未实现的已分配 cfx 由实现约定」支撑第三条（Tiny `trap/escape` 未实现 ⇒ `ILLI` 为既有口径）。
- `rc10`：表行 + 正文 + `0.1.4-rc` 三处一致（初值 = 内部 SRAM 起始、无 SRAM 者平台定义、`value[1:0] ← 0` 不异常、读回落盘值）；`Machine-v5` §1.1/§2/§4.4 全改「初值 = SRAM 起始、显式写为幂等」，正文无旧口径残留（仅 0.4.0/0.4.2 历史条目，0.4.2 已加注）。
- `§7.1`：4 处产生方表述（同步异常落点 / 未映射与 A-D / reserved / Tiny 机器 fault）确实删除，现文只留编码 + 语义映射；19 行编码表与 `HEAD~1` 我逐行 diff **逐字一致**。
- 版本/锁：`0.4.4-rc` 册头与附录段齐、旧 `0.4.3-rc` 段改名；`DADAO-13` 保持 `0.1.4-rc` 就地补条。
- 纪律：完成区 15 非空行 ≤30 且无运行期/宿主路径；审阅记录 ≤40 行；改动 4 文件（3 声明 + 任务书自身）与「修改文件」对账一致；裁定原话 L11/L39 可溯源。

**新发现（任务书未登记）**
- `.tao/contracts/contract-elf.md` §5.2/§5.4 仍写「`Machine-v5-Tiny` 的 crt/启动 stub 段落 BootROM，**允许装入（例外）」，与新 `§6`「宿主不得向 BootROM 下发 `PT_LOAD`、`e_entry` 必须 = `0xffff_ff01_0100`」直接冲突。
- `ADR-0043` 冲突面不止 `D2`/`D3`：`D14`「power 在 trap hmon 后 park、不返回」与 `§6.2` 第 7–8 步（hmon `escape` 回 stub、power 跳应用入口）冲突，「后果」第 37 行同源。

**判决：Needs Revision**
1. 失败命令：运行期证据目录 `run.sh --inject` ⇒ `RUN_EXIT=1`（`content-checks rc=1`、`inject rc=1`）；`checks.py` ⇒ `EXIT=1`。改运行期证据目录 `checks.py` 的 `c7_lock()` 基线为派单前 commit（写死常量 `5139852e8a4340ff1160b5a7ae971e34f4979a5d` + 注释），重跑预期 `RESULT: PASS（0 项失败）`、总 rc=0。
2. 完成区「7/7 内容检查」「三例还原后 rc=0、脚本总 rc=0」与我重跑不符（6/7、总 rc=1），须随修复同笔更正（不改判据值）。
3. 「待裁定」补登 `.tao/contracts/contract-elf.md` 冲突与 `ADR-0043 D14`（均不自改，交主会话）。

### 第 2 轮 engineer 自审（返工，自主逐行审查）

审查范围：`checks.py`（C6/C7 基线改动）、任务书的「冲突登记 / 待裁定 / 完成区」；`run.sh`/`inject.py` 未改、spec 正文与锁未改；对照 reviewer 第 1 轮 3 条判决。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| reviewer#1：`c7_lock()` 以 `HEAD` 作基线，HEAD 含 WIP 提交 ⇒ 变化册算成 `[]` | ✅已修 | 新增 `DISPATCH_BASE = 5139852e…`（写死派单前 commit）+ `base_text()`；基线不可达即显式失败（不退化回 `HEAD`） | C7 PASS「相对派单前 5139852e 仅 `Machine-v5`/`DADAO-13` 两册变化」 |
| 同根因隐患：C6「编码表与 `HEAD` 比对」在同一提交后也会退化为自比（恒真） | ✅已修 | C6 基线同步改用 `base_text()`（未改判据、未改表内容） | C6 PASS「19 行与基线 5139852e 逐字一致」 |
| reviewer#2：完成区「7/7 内容检查、总 rc=0」与实测不符 | ✅已修 | 完成区改为返工后实测值（逐条 rc） | `run.sh --full` ⇒ `FULL_EXIT=0`；`run.sh --inject` ⇒ `INJECT_EXIT=0` |
| reviewer#3：补登 `ADR-0043 D14`、`contract-elf §5.2/§5.4` | ✅已修 | 新增「冲突登记」段（4 条，含原 `D2`/`D3`），统一标「待用户授权就地修订」 | 见该段 |
| 返工中新发现：reviewer 记录内 3 处运行期证据目录的具体路径（带 `.work` 前缀）使 `check-knowledge-refs` FAIL（具体引用 4 处） | ✅已修 | 只把该 3 处路径措辞改为「运行期证据目录 `run.sh`/`checks.py`」，**未改任何数字/结论** | `check-knowledge-refs` rc=0（具体引用 = 0） |

判决：reviewer 3 条与返工中新发现的路径门控问题已全部修复并复验，无未修 finding。状态保持 `待验收`。

### 第 2 轮 reviewer 验收（2026-11-10，独立重跑）

**重跑记录（我的真实输出/退出码）**
- 运行期证据目录 `checks.py` ⇒ `checks: 7 项，PASS 7，FAIL 0`、`CHECKS_EXIT=0`（C6 实际值「与基线 `5139852e` 逐字一致」、C7「相对派单前 `5139852e` 仅 `Machine-v5`/`DADAO-13` 两册变化」）。
- `run.sh --full` ⇒ 内容检查 1/1 + 7 门控全 `PASS rc=0`、`RESULT: PASS（0 项失败）`、`FULL_EXIT=0`；`run.sh --inject` ⇒ 同上 + `PASS inject … inject: 3 例，FAIL 0`、`INJECT_EXIT=0`。
- 直跑 `inject.py` ⇒ 三例逐条「`rc=1` 目标检查FAIL 注入非空=True」+「还原 md5 一致（`1a3665ce04ae` / `42bb04d02756`）rc=0」、`INJECTPY_EXIT=0`。
- **C7 可失败**：`DISPATCH_BASE = 5139852e8a4340ff1160b5a7ae971e34f4979a5d`（写死常量）；`c6`/`c7` 函数体内均无 `HEAD`、均调 `base_text()`，`head_text` 已删除；基线改 `0000…` ⇒ `SystemExit: git show 00000000:… 失败（基线不可达，请检查 DISPATCH_BASE）`，不退化。
- **C6 可失败（我的注入）**：§7.1 表 `PASS → PASSZ` 一字 ⇒ `FAIL C6 … 一致=False`（连带 C7 sha 不符）、`EXIT=1`；`cp`+md5 还原 `1a3665ce04ae…` ⇒ 7/7、`git status` 空。
- **返工零新增**：`git diff babcd8ab..HEAD -- spec manifests` 空；`5139852e..HEAD` 与 `5139852e..babcd8ab` 补丁 sha 同为 `36b2bd7b02e6…`；全量改动仍 4 文件（spec×2 + 锁 + 任务书），ADR/契约未动。
- 我的第二个注入：任务书追加一条具体证据目录路径引用 ⇒ `check-knowledge-refs` `FAIL (1 具体 … 引用不可复现)`、`GATE_INJECT_EXIT=2`；还原 md5 `1b53be394811…` ⇒ `PASS (0 …)` rc=0（门控非恒真，返工改路径措辞确有必要）。
- 快照对账：7 文件 `md5sum -c` 全 `OK`、`git status --porcelain -uall` 空（未提交、无残留）。

**记录改动核对**：第 1 轮记录仅 3 行、4 处带前缀路径改为「运行期证据目录」措辞；判决 1–3 与全部数字/输出原文逐行 diff 未动。

**约束核验**：完成区 15 非空行 ≤30、0 运行期路径；`checks.py` 7 项断言与注入 3 例未删未弱化（C2/C5 旧口径串、C6 `forb` 串与 `expected=(2+4)+(2+11)`、C7 `21 册`/`changed == want` 均在）。

**Findings（文档级，不阻断，architect 收尾改）**
1. 冲突登记节号错：实为 `.tao/contracts/contract-elf.md` `§6.1.2`（装载语义 + over-size 两条）与 `§6.2`（第三处同冲突），`§5.4` 不存在、`§5.2` 是 VA=PA；错源在本记录第 1 轮我写的节号，engineer 照抄。
2. 第 1 轮自审表仍写「见『待裁定』1」，而 ADR 条已移入「冲突登记」，该交叉引用失效。
3. 完成区/自审表写 `run.sh --full`：脚本只有无参与 `--inject` 两模式，`--full` 被静默忽略（数字真实、我复现 exit=0），建议改写为「无参模式」。
4. 第三处旧材料未登记：`.tao/knowledge/refs/m12-006-cycle-design.md`（「宿主 loader 直装 hmon SRAM（推荐）」+ 显式写向量前置）；`tests/shared/machine-profiles.yaml` 26–27 行同源（已在完成区「新发现②/遗留」披露，建议并入冲突登记）；`ADR-0043` `Consequences` 的宿主 `PT_LOAD` 一句与 D3 同源，修订时一并扫。

**判决：Accepted** —— 三份 rc 与声称逐字一致、C6/C7 均真修且可失败、spec/锁零改动、纪律无违反；上述 4 条属文档级，按裁定记 finding、不再开轮，由 architect 收尾一并改。**仍需用户确认**：① `crt 移 SRAM` 属新契约（超出 hmon 装载裁定原话）；② `ADR-0043 D2/D3/D14` 与 `contract-elf` 的就地修订**待用户授权**（本任务未改）。

## 冲突登记（与本文冲突的 ADR / 契约；**待用户授权后就地修订**，本任务不自改）

1. **`ADR-0043 D2`**：写「`Machine-v5-Tiny` 的 64 KiB BootROM 无 image index table，全部为复位/启动 stub」——与新 `§6.1`/`§6.2`（Tiny 用同一 image index table 格式、含 hmon 段）冲突。
2. **`ADR-0043 D3`**（2026-11-10 rev）：写「Tiny 测试镜像仍由宿主 loader 按 `PT_LOAD` 装入 BootROM/SRAM；hmon 代码由 hmon 自身填充 hmon SRAM」——与新 `§6`（BootROM 为固定固件、宿主只装 SRAM、hmon 由 power 复制）冲突。
3. **`ADR-0043 D14`**（第 1 轮 reviewer 补登）：写「power 在 `trap hmon` 后进入 BootROM park/复位等待」——与新 `§6.2` 第 7–8 步（hmon `escape` 回 stub、power 跳应用入口 `0xffff_ff01_0100`）冲突；`Consequences` 段同源的 park 表述一并受影响。
4. **`.tao/contracts/contract-elf.md §5.2/§5.4`**（第 1 轮 reviewer 补登）：现写「`Machine-v5-Tiny` 的 crt/启动 stub 段落 BootROM，**允许装入（例外）**」——与新 `§6`（BootROM 固定固件、宿主不得向 BootROM 下发 `PT_LOAD`、`e_entry` 必须 = `0xffff_ff01_0100`）直接冲突。

处置建议：`ADR-0043` 按既有「就地修订」授权同笔改 `D2`/`D3`/`D14`；`contract-elf` 随投影同步改 §5.2/§5.4 的 Tiny 例外条款。本任务均未动。

## 待裁定（需主会话转达用户；子代理不得直接提问）

1. **根 `README.md` 的「在研版本」列仍 `0.4.3-rc`**：本任务限定文件范围不含 `README.md`。**建议**：收尾同笔改 `0.4.4-rc`（`check-spec-drift` 只看「已发布版本」列，当前门控不受影响）。**自决**：未改，登记。
2. **`cfx_pmem` 的 `rc10` 初值**：规则统一后其初值 = pmem SRAM 起始（`0x83ff_0000_0000`）；若 gem5/QEMU 现值不同，或期望向量指向 pmem 内代码，需实现侧对齐（属实现任务）。**自决**：正文按用户裁定统一，不改实现。

## 完成区

**测试结果**（返工后实测）：`checks.py` 7/7 PASS（`EXIT=0`）；`run.sh --full` 内容检查 1/1 + 门控 7/7 PASS（`FULL_EXIT=0`）；`run.sh --inject` 追加注入 3/3 PASS（`INJECT_EXIT=0`）；失败原因：无。

**修改文件**：本轮返工只改证据脚本 `checks.py`（C6/C7 基线 → 派单前 commit 常量）与任务书自身；`spec/Machine-v5-…`、`spec/DADAO-13-…`、`manifests/spec-readonly.lock.toml` **本轮未改**（首轮成果，md5 经 reviewer 核对）。

**验收结果**（真实输出）：
- 门控：`check-spec-readonly` / `check-spec-changelog` / `check-spec-drift` / `check-spec-numbering` / `check-spec-refs` / `check-knowledge-refs` / `check-test-reports` 逐项 `rc=0`。
- 注入（注入→目标检查 FAIL→`cp`+md5 还原→回绿）：§7.1 产生方表述 ⇒ C6 FAIL；§6.2 窗口 56→52 KiB ⇒ C3 FAIL；`rc10` 旧口径 ⇒ C5 FAIL；三例均「目标检查 FAIL ∧ `git diff` 非空 ∧ 还原 md5 一致」，还原后 rc=0。
- 容量：§6.2 三段窗口现场求和 = `0x10000`，与 §1.1 尺寸格派生 64 KiB 相等。
- 锁：21 册逐册重算一致；相对**派单前 `5139852e`** 仅 2 册 sha 变（`Machine-v5`/`DADAO-13`）。
- 版本：`Machine-v5` `0.4.3-rc` → `0.4.4-rc`（原 `-rc` 段记 `0.4.3（未发布，被 0.4.4-rc 取代）`）；`DADAO-13` 保持 `0.1.4-rc` 就地补条目。

**四条改动（改前 → 改后 → 依据）**：
1. **hmon 装载**：Tiny BootROM「全部为 stub、无表、宿主直装 hmon 段」→「固定固件镜像（power ≤4 KiB / hmon ≤56 KiB / 表 4 KiB）+ power 复制到 `0x0fff_0000_0000` 后 `trap` 移交；宿主只装 SRAM、入口固定；表格式见新增 §6.1/§6.2」——用户裁定原话（hmon 入 BootROM、power 搬运、QEMU 先行）。
2. **`cfx2*` 口径**：原只写 `trap`/`escape` → 补「reserved cfxha ⇒ `ILLI`；已分配未实现 / 未定义 cg-rc ⇒ `CFXREG`」两条互斥规则并引原文——用户裁定 + `DADAO-12 §5.1`/`§5.2（一）`。
3. **`cg3 rc10`**：「初值由平台/实现定义」→「初值 = 该 cfx 内部 SRAM 起始（无内部 SRAM 者平台定义）；写入忽略低 2 位（`value[1:0] ← 0`）」——用户裁定原话。
4. **`§7.1`**：删「同步异常落点 / 未映射 / reserved / Tiny 机器 fault」4 处产生方表述 → 「只定编码 + 产生方属实现设计」；编码表 19 行逐字未动——用户裁定原话。

**新发现/坑**：① `fence` 的 `cr/cw/ci/co` 是「cfx memory/IO 访问」，**不含取指可见语义**，不能拿它给「复制后可取指」背书（已改为实现义务）；② BootROM 变固定固件后，Tiny 应用入口必须固定，旧「crt 在 BootROM、宿主双段装」装载模型整体失效（`tests/shared/machine-profiles.yaml` 注释同源，需连带改）；③ 只读锁注记须与 sha 同笔，正文每改一次都要重算；④ **证据脚本的对照基线不能取 `HEAD`**——architect 的 WIP 提交会前移 `HEAD`，令「相对基线变了什么」算成空（reviewer 实测 C7 `实际变化 []`）；一律钉派单前 commit 常量。

**遗留问题**：`ADR-0043 D2/D3/D14` 与 `contract-elf §5.2/§5.4` 待用户授权后就地修订（见「冲突登记」1–4）；根 `README.md` 在研版本与 `cfx_pmem` rc10 见「待裁定」1–2；实现侧对齐（profiles yaml / QEMU `mon_elf_segments` / gem5 Tiny 直装 / chipyard `m12-chipyard-007` / step5 构建器 Tiny 分支）建议合并为「三平台 hmon 装载对齐」任务，本任务未做。其余无未完成项。

#### 收尾（architect，2026-11-10 12:14）

- 第 2 轮 **Accepted**：C7/C6 基线改 `DISPATCH_BASE=5139852e`；reviewer 构造反例（基线改 `0000…` ⇒ 显式 `SystemExit`；§7.1 改一个字 ⇒ C6 FAIL）证明不退化 HEAD、不恒真。三份 rc 与声称逐字一致（`7/7`、`FULL_EXIT=0`、`INJECT_EXIT=0`）。
- 返工零新增：`5139852e..HEAD` 与 `5139852e..babcd8ab` 补丁 sha 相同。
- 四条登记（本收尾补正）：
  1. `ADR-0043 D2/D3/D14` 与新契约冲突（D14 = power park vs `§6.2` escape 回 stub）；
  2. `.tao/contracts/contract-elf.md` 的冲突实际在 **§6.1.2 与 §6.2**（原记录写 §5.2/§5.4 有误）；
  3. `.tao/knowledge/refs/m12-006-cycle-design.md` 仍写「宿主直装 hmon SRAM」，待随契约更新（**本条本收尾已在设计报告加注**）；
  4. `tests/shared/machine-profiles.yaml` 26–27 行同源，待同步。
- **待用户确认**：① `crt 移 SRAM`（新契约，超出原裁定原话）；② `ADR-0043` 就地修订（D2/D3/D14）；③ `contract-elf` / `machine-profiles.yaml` / 设计报告 同步。
- `run.sh --full` 实为不支持（静默忽略），记录改为无参/`--inject` 两种模式。

### 收尾后更正（architect，2026-11-10，用户裁定）

用户原话：「power 8KiB，hmon 8KiB，image index table 放在最后，也是8KiB」。

- Tiny BootROM 布局改为：power `0x0000–0x1FFF`（8 KiB）/ hmon `0x2000–0x3FFF`（8 KiB）/ 保留区 `0x4000–0xDFFF`（40 KiB，全零）/ 段表 `0xE000–0xFFFF`（8 KiB）。
- 复制长度上限 56 KiB → **8 KiB**；容量结论改为 `8+8+40+8=64`，并明确「**hmon 8 KiB 是校验阈值，不是目标尺寸**（最小 handler 预计 1–3 KiB）」。
- 原「hmon ≤56 KiB」是「剩余空间全给它」的产物，用户指出后改正。
- 锁 sha 同笔重算；`check-spec-readonly`/`check-spec-changelog`/`check-spec-drift` 复跑 rc=0。

