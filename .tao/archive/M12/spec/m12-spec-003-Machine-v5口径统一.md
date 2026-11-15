# m12-spec-003: `Machine-v5` 口径统一（reserved 集 / `cause_info` / `escape` 返回 / power cg7·cg8 / `switch_run_mode`）

**模块**：spec
**项目里程碑**：M12
**依赖**：`m12-spec-002`（已合入，`0.4.2-rc`）
**可并行分片**：否（单册单写者）
**状态**：已验证

## 用户裁定（2026-11-10，原话）

> 「1、B；2、hmon的代码/数据应该是放在bootrom中，然后由bootrom代码存放到相应位置；先在qemu中进行验证，然后gem5/chipyard可共用；3、第7条，reserved cfx引发ILLI，非reserved cfx的未定义cg/rc引发CFXREG，没有冲突，只是Machine-v5文档没写清楚；第8条：7.1写的不对，只定编码，谁产生是代码设计要决定的」

- **选 B**：拆 `m12-spec-003`（题 1–5，纯口径统一）+ `m12-spec-004`（题 6–8，新契约）。
- 本任务只做题 1–5。

## 用户裁定（2026-11-10，第二次；返工，经主会话转达，原话）

> 「1、为什么要写reserved cfx号呢？？？我后面还会变啊！！！2、Tiny下，写入3，读回3；3、如果你确定是笔误，就应该改；关键是这部分内容是你写的！！！」

- **① 取代上文 §目标 1 的字面写法**：reserved cfx 集**不列举编号**——改为「规则 + 单一真源指针」（`DADAO-12 §1` 表中 `cfxname = reserved`）；上轮「按上游现行 `6`–`14`、`16`–`31`、`35`–`61` 落地」作废。附录 `0.4.0` 历史条目不按新口径改写，只在 `0.4.3-rc` 记录变更。
- **② 取代上文 §目标 5 的字面写法**：Tiny `switch_run_mode` **写入被忽略、读回恒 `3`**（既非「保存写入值」，也非「读回最后写入值」）。
- **③ 授权改 `DADAO-12`**：`§2.1` 校验示例笔误直接改（**本次 `spec/` 改动的授权依据即此句**）；上文 §非范围「不改 `DADAO-12`」按此授权例外，仅限该笔误。

## 背景

`m12-chipyard-006` 的 §9 与 `m13-qemu-001`/`m13-gem5-001` 的实现期记录共列出若干 spec 缺口。`m12-spec-002` 已解决 cfx 范围、地址图、启动链、异常进向量、向量默认值、退出码常数等；**剩余 5 条属「文档自相矛盾/没写清楚」**，实现侧已各自按 `DADAO-12`/`DADAO-13` 落地，因此本任务只统一文字、不改行为语义。

## 目标（5 条，逐条给出改法）

1. **reserved cfx 集统一**（**本改法已被 §用户裁定「第二次」① 取代：不列举编号，改为规则 + 上游指针**）
   - 现状：正文（`§1.2`/`§3`/`§7.1`）用 `6–14、19–61`；附录 `0.4.0` 的「Step 1」段仍写 `6–14、16–31、35–61`。
   - 改为：全册统一 `6–14、19–61`；并**显式列出已分配位**（`cfx15` timer、`cfx32` pmem、`cfx33`/`cfx34` 等按现行正文），说明 `15–18`、`32–34` 不在 reserved 集的原因。
   - 附录属历史变更记录：**不改历史记录正文**，若与现行一致性问题，只在附录加一行「（口径已由 `0.4.3-rc` 统一为 `6–14、19–61`）」。
2. **`excp_cause_info` 覆盖面**
   - 现状：`§4.4` 列 5 类（`CFXMEM`/`ILLI`/`UNDI`/`MALIGN`/`IALIGN`）的 `info`；`DADAO-13 §2` 列 11 项。
   - 改为：明确「本册只规定下列 5 类的 `info`；其余异常原因（`CFXTRAP`/`CFXESC`/`CFXPERM`/`CFXREG` 等）的 `info` 按 `DADAO-13 §2`，本册不另行规定；未规定者为 0」。**不得**与 `DADAO-13` 冲突。
3. **`escape` 的返回 cfx**
   - 现状：正文写「返回 cfx 取自异常帧」，但 `DADAO-12` 的异常帧里**没有保存 prev_cfx 的寄存器位**（`m13-gem5-001` 实测）。
   - 改为：明确「帧中**不保存** `prev_cfx`；`escape` 的目标 cfx 恒为**当前 cfx**（即发起 `escape` 的 cfx）」；若 `DADAO-12` 原文另有规定，以 `DADAO-12` 为准并引原文（先核对再写，不得自造）。
4. **Tiny `cfx_power` 的 `cg7` 与 `cg8 rc1`**
   - `cg7`：写明 BootROM 的 `start`/`size` 取值（按 profile 派生：`bootrom_base − (63<<42)`、64 KiB），`attr = R|X`。
   - `cg8 rc1`（power ctrl，WO）：写明 Tiny 下访问 ⇒ `CFXREG`（未实现；显式失败而非静默桩）。
5. **Tiny 的 `switch_run_mode`**（**本改法已被 §用户裁定「第二次」② 取代：写入被忽略、读回恒 `3`**）
   - 现状：`cg3 rc8` 名义 RW，但 `§2` 说 Tiny 运行模式恒 `hypv`。
   - 改为：明确「Tiny 下对该寄存器的写入**被忽略**（读回 `3`），运行模式不变」；与 QEMU（强制 `HYPV`）与 gem5（`m13-gem5-002` 已硬置 `HYPV`）一致。

## 非范围

- 不做题 6–8（hmon 装载契约、`cfx2*` 口径、退出码生成方）——归 `m12-spec-004`
- 不改 `DADAO-12`/`DADAO-13`（上游册；若发现上游矛盾，登记并停下来问，不擅改）——**例外：`DADAO-12 §2.1` 笔误按 §用户裁定「第二次」③ 授权修正**
- 不改任何实现代码（QEMU/gem5/chipyard）

## 验收标准

1. 5 条逐条落地，每条给出「改前原文 / 改后原文 / 依据（`DADAO-12`/`DADAO-13` 章节或用户裁定）」
2. 全册自洽：`reserved cfx` 集只有一处定义（其余处引用），且**正文不出现 reserved 编号列举**（二次裁定 ① 修订，原字面「无 `16–31、35–61` 残留」作废）
3. `excp_cause_info` 不与 `DADAO-13 §2` 冲突（逐项对照表）
4. `escape` 条款与 `DADAO-12` 原文一致（引原文行号）
5. 版本 `0.4.2-rc` → **`0.4.3-rc`**；`manifests/spec-readonly.lock.toml` 同笔更新（**仅 `Machine-v5` 与 `DADAO-12` 两行变、其余 19 册不变**；二次裁定 ③ 修订）
6. 5 个 spec 门控 rc=0：`check-spec-readonly` / `check-spec-changelog` / `check-spec-drift` / `check-spec-numbering` / `check-spec-refs`
7. 一键证据脚本（含可达 FAIL 注入：例如把 reserved 集改回编号列举应 FAIL）
8. 完成区 ≤30 行、无运行期路径
9. （二次裁定 ③ 新增）`DADAO-12 §2.1` 两示例值 = `2^42 − size` 独立派生值，且 `0.7.3-rc` 变更记录有对应条目

## 说明

- 本任务**不引入新语义**；任何一条若发现「必须改行为」而非「统一文字」，**停下来登记**并返回主会话，不要自行扩大范围。（例外：§用户裁定「第二次」② 的 Tiny「读回恒 `3`」为用户裁定的测试机约定，实现侧按「实现影响」另任务对齐。）
- `spec/` 改动须用户事先授权：本任务书即授权范围（`Machine-v5` 一册 + 锁；二次裁定 ③ 追加 `DADAO-12 §2.1` 笔误修正，授权原话见 §用户裁定「第二次」）。

## 硬约束（子代理必读）

1. 临时目录 `/tmp/opencode/<任务ID>/`，禁仓库内临时文件。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；**需要裁定**写进任务书「待裁定」段并返回主会话（子代理不得直接问用户）。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. **不得写入未经主会话转达的用户裁定**；自定事项写「自决」（`ISS-365`）。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 待裁定（需主会话转达用户；子代理不得直接提问）

> **全部已裁定（2026-11-10，原话见上文 §用户裁定「第二次」）**：1 → 不列举编号、改引用上游；2 → 写入被忽略、读回恒 `3`；3 → 笔误直接改。以下保留提问原文作记录。
1. **题 1 目标值与 `DADAO-12` 现行正文冲突（已按上游落地，待确认）**
   - 任务书写「全册统一 `6`–`14`、`19`–`61`」「说明 `15`–`18`、`32`–`34` 不在 reserved 集」。实测上游现行（`DADAO-12` 0.7.3-rc）为 reserved = `6`–`14`、`16`–`31`、`35`–`61`（§1 表、§2.1 说明、§5.1、§5.3 伪代码；变更记录 2026-11-05「保留集改为 `6`–`14`、`16`–`31`、`35`–`61`」）——任务书的 `19`–`61` 是 2026-11-05 前旧值；`INTEG-053t` 当笔只更新了本册附录 Step 1，未改正文三处。
   - 实现侧同口径：gem5 `tinyCfxReserved()` = `{6–14, 16–31, 35–61}`；QEMU 同。
   - 照任务书字面写会**改变行为**（`cfx16`–`cfx18` 由 reserved 变「未分配」）且与上游冲突，故未照字面写。
   - 自决（临时处置）：按 `DADAO-12` 现行统一为 `6`–`14`、`16`–`31`、`35`–`61`，显式列出已分配位与 `cfx16`–`cfx31`（per-task，未分配但仍按 reserved 处理）说明。若用户确要 `19`–`61`，须先改 `DADAO-12` 并另立行为任务。
2. **题 5「写入被忽略（读回 `3`）」= 新行为（未按字面写）**
   - 实测 QEMU（异常进入处 `if (!DADAO_PROFILE(env)->user_mode) inner_run_mode = HYPV;`）与 gem5（异常进入 `s.runMode = 3`）都是**保存写入值、仅在异常进入时强制 `HYPV`**；`m13-gem5-002` 的验收用例正是「guest 写 `0` 后触发 `CFXMEM`，仍应留在 `hypv`」。
   - 要「读回 `3`」须改 QEMU/gem5；本任务不引入新语义 ⇒ 写成「写入**不改变运行模式**（异常进入强制 `hypv`）；读回为最后一次写入值（`DADAO-13 §1` 定义为 RW）」，并把 §4.4「模式切换取 `switch_run_mode`」改为「强制 `hypv`」。
   - 自决：按现状口径；若用户要「写入被忽略/读回 `3`」，需另立 QEMU+gem5 行为任务。
3. **上游笔误（不改上游，仅报告）**：`DADAO-12 §2.1` 校验示例写「`size = 64 KiB` ⇒ `start = 0x3_ffff_0000`；`size = 4 MiB` ⇒ `0x3_ffc0_0000`」，少一组 `FF`；按同句公式 `start = 2^42 − size` 应为 `0x3ff_ffff_0000` / `0x3ff_ffc0_0000`（QEMU `dadao_cg7_space_reg` 亦用后者）。本册按公式给值；是否修上游另议。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`spec/Machine-v5` 全文 diff（6 处正文 + 册头 + 附录）、只读锁 diff、证据脚本；对照 `DADAO-12 §1/§2.1/§3.8/§4.12/§5.3`、`DADAO-13 §1/§2`、实现（QEMU `helper.c`/`cpu.c`、gem5 `tiny_cfx.cc`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 题 1 字面值会改 `cfx16–18` 行为且与上游冲突 | ⏸延后（待裁定 1） | 按上游现行写并登记 | 5 spec 门控 rc=0；脚本 reserved 检查 |
| reserved 集四处重复定义（漂移根因） | ✅已修 | §1.2 唯一定义，其余 3 处引 `§1.2` | 脚本 `定义=1 引用=3 正文旧值=0` |
| 题 5「读回 3」= 改行为（QEMU/gem5 存写入值） | ⏸延后（待裁定 2） | 写「不改变运行模式」并修 §4.4 旧口径 | 脚本 switch_run_mode 检查 |
| §4.4「模式切换取 `switch_run_mode`」与 §2 矛盾 | ✅已修 | 改「强制 `hypv`」 | 脚本「旧口径=0」 |
| 题 4 数值手算易错（上游示例另有笔误） | ✅已修 | 由 §1.1 起址独立派生校验 | 两 profile `start+size=2^42:True` |
| 题 3 引文风险（不得自造） | ✅已修 | 逐字引 `DADAO-12 §5.3` 原文并断言可回溯 | 脚本 escape 检查（原文/伪代码无 cfx 恢复） |
| 附录历史段 `19–61` 与现行不一致 | ✅已修 | 0.4.0 条目加一行「（口径已由 `0.4.3-rc` 统一…）」，不改历史正文 | 脚本只扫正文（附录前） |
| 只读锁「21 册只该行变」 | ✅已验 | Machine 行 sha + 1 条注记 | 脚本 `条目=21 / 其余 20 不变 / 变更 sha 行=2（旧+新）` |
| 证据脚本首版：检查函数不返回 rc、注入用例误判 | ✅已修 | `fail` 返回 1；注入用子 shell 隔离计数 | `--inject` 3/3 用例 PASS |

判决：可修项已全部修复并复验；2 条需用户裁定的已登记「待裁定」，正文按上游/实现现行口径落地。状态置 `待验收`。

### 第 2 轮 engineer 自审（返工，自主逐行审查）

审查范围：本轮 diff（`Machine-v5` 4 处正文 + 附录 2 处 + 删 1 处注解、`DADAO-12` §2.1 + 0.7.3-rc 1 条、锁 2 个 sha + 2 段注记）、证据脚本全文；对照用户裁定三条与 `DADAO-12 §1/§2.1`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 上一轮按上游编号落地，违背用户「不写编号」裁定 | ✅已修 | §1.2 定义改为规则 + `DADAO-12 §1` 指针，正文零编号列举 | 脚本 reserved（集合从 `DADAO-12 §1` 现场解析）；`--inject` 改回列举即 FAIL |
| 上一轮给 0.4.0 历史条目自加的「口径已统一为…」注解与新口径矛盾 | ✅已修 | 删除该注解，恢复历史正文原样 | diff 仅该行删注；附录 0.4.0 正文未改 |
| §2 与 §4.4 的 `switch_run_mode` 旧口径（读回最后写入值/不采用写入值） | ✅已修 | 两处统一「写入被忽略、读回恒 `3`」 | 脚本 §2=1 §4.4=1 旧口径=0；注入旧口径即 FAIL |
| 证据脚本区间扫描误报「`1..63` 为 cfx 1–63」分区键句 | ✅已修 | 跳过分区键行（显式条件） | full rc=0；注入列举仍 FAIL |
| DADAO-12 笔误无 FAIL 路径（注入仅覆盖 `Machine-v5`） | ✅已修 | 新增 `d12_typo` 检查（独立由 2^42−size 派生 + 变更记录）及注入用例 | `--inject`「笔误回退」注入→FAIL→还原→PASS |
| 锁检查以往按 HEAD 比较，WIP 已含改动时会误判 | ✅已修 | 改以 `merge-base master` 为基线 | 脚本 `变更=2(Machine+DADAO-12) 全部 sha 匹配` |
| 引用措辞（§1.2「判定见下条」vs §3/§7.1「集见 `§1.2`」） | ❌不修 | 三处均指向同一规则，无歧义 | `grep` 三处引用均在正文 |

判决：finding 全部处置完毕（1 条判不修并附证据）；full 9/9、inject 4/4 通过。状态保持 `待验收`。

### 第 1 轮 reviewer 验收（独立重跑，2026-11-10）

**重跑记录**（worktree 根、相对路径；`echo $?` 取真实退出码）：
- `./运行期证据目录/run.sh` → 9/9 `[PASS]`（version/reserved/cause_info/escape/power_cg7/switch_run_mode/d12_typo/lock/gates），`SUMMARY: all checks PASS`，`FULL_EXIT=0`；其中 `gate check-spec-{readonly,changelog,drift,numbering,refs} rc=0`。
- `run.sh --inject` → 4/4「注入 md5 变更 → 该检查 FAIL → `cp` 还原 md5 一致 → 回 PASS」，`INJECT_EXIT=0`。
- 门控独立亲跑（不走脚本）：5 个 spec 门控 rc=0；`check-spec-purity/cite-targets/codeblocks` rc=0；`check-contracts-dir/knowledge-refs/knowledge-dir/dirs/no-residue/run-artifacts/milestones-fresh` rc=0（= 完成区所称 10 门控）；`check-spec-archive` rc=0、`check-patch-tree` rc=0。
- `check-spec-archive-verify` worktree rc=2：`git rev-parse … @ .cache/refs/DADAO.wiki: No such file`（本 worktree 未 `fetch-refs`；主仓 `make check-spec-archive-verify` rc=0）⇒ 环境性、且属 SimRISC 归档专项，不在验收清单。
- `check-temp-dirs` rc=2：`VIOLATION /tmp/opencode/m13-gem5-002-review: 2.9h`（外部任务陈旧目录）⇒ 与完成区遗留②一致，非本任务产物。
- **reviewer 独立注入①**（脚本用例之外的写法）：§7.1 `reserved cfx（集见 §1.2）` → `（6–14、16–31、35–61）` → `rc_injected=1`，`[FAIL] reserved 引用=2`、`[FAIL] lock sha 不符`、`check-spec-readonly rc=2`；`cp -p` 还原后 md5 `c55c7feab245d4542ffce1f3b0414dc1` 与注入前相等，`rc_restored=0`（回绿）。
- **reviewer 独立注入②**（脚本未覆盖的 `power_cg7`）：§3 `start = 0x3ff_ffff_0000 → 0x3ff_fffe_0000` → `rc=1`，`[FAIL] power_cg7 … 缺 0x3ff_ffff_0000`；还原 md5 相等，`rc=0`。
- 锁独立复算（reviewer 自写，非脚本）：`entries=21`、`sha mismatch: NONE`、`changed=[DADAO-12, Machine-v5]`、`unchanged=19`。三目标文件 md5 注入前后逐字节相等；`git status --porcelain -uall` 基线干净、收尾干净（reviewer 自建 `oldD12.md` 已删）。

**约束核验**：① 正文（`§1.2`/`§3`×2/`§7.1`）零编号，3 处只引 `§1.2`；`awk NR<297` 扫编号区间仅命中 `1..63`/semihosting 区/步骤号；附录 0.4.0 两处旧编号与 master 逐字相同（历史记录，未作现行口径）。② 规则**可判定**：`DADAO-12 §1` 表实有 `6-14|reserved`、`16-31|reserved`、`35-61|reserved`，脚本现场解析 `上游解析=52`（9+16+27）。③ `§2`（写入被忽略、读回恒 `3`，`inner_run_mode ← 3`）/`§4.4`（同措辞，见 `§2`）/附录 `0.4.3-rc`（同）三处一致，与 `§2`「运行模式恒 `hypv`」互证；`§2` 上位句「取 `switch_run_mode` 的值」对 Tiny 亦得 `3=hypv`，不构成冲突。④ 自算 `2^42−64KiB=0x3ff_ffff_0000`、`2^42−4MiB=0x3ff_ffc0_0000`、两者 `+size=2^42=True`；`DADAO-12` 全册 diff 仅 2 行（§2.1 示例值 + 0.7.3-rc 一条），`start = 2^42 − size` 规则句与其余正文未动。⑤ diff = 4 文件，与完成区「修改文件」逐一对账一致；完成区 19 行（≤30）、无运行期路径；用户裁定仅两段（与主会话转达原话逐字一致），锁内引用同源。

**findings（文档级，不阻断，交 architect 收尾）**：① `README.md` 版本表 `Machine | 0.4.0 | 0.4.2-rc` 未随 `0.4.3-rc` 同步（engineer 已在遗留③披露）；② 附录 `0.4.1（未发布，被 0.4.2-rc 取代）` 指向已改名的 `0.4.2` 段；③ §待裁定 1/2 的「自决」文本仍是已被裁定①②取代的旧口径、未标作废；④ 验收标准 4 要求「引原文行号」，完成区只写 `§5.3`（实际原文 = `DADAO-12` 行 895，已核）。

**判决：Accepted**（验收命令块在 reviewer 自跑下全绿；硬约束无违反；上述 4 条为文档级 finding）

## 完成区

**测试结果**：5 个 spec 门控 rc=0（readonly/changelog/drift/numbering/refs）；另 10 个相关门控 rc=0（spec-purity/spec-cite-targets/spec-codeblocks/contracts-dir/knowledge-refs/knowledge-dir/dirs/no-residue/run-artifacts/milestones-fresh）；证据脚本 full 9/9、`--inject` 4/4 均 rc=0。
**修改文件**：`spec/Machine-v5-测试机运行环境.md`、`spec/DADAO-12-SEE-主管系统运行环境.md`、`manifests/spec-readonly.lock.toml`、本任务书（用户裁定/待裁定/审阅记录/完成区）。
**逐条落地（改前 → 改后 → 依据）**：
1. reserved：`6`–`14`、`16`–`31`、`35`–`61`（§1.2/§3×2/§7.1 各写一遍）→ **只留规则**「`DADAO-12 §1` 表中 `cfxname = reserved` 的编号即保留 cfx（含 per-task 段未分配）」，正文零编号；其余 3 处只引 `§1.2`；0.4.0 历史正文恢复原样；依据用户裁定 ①。
2. `info`：§4.4 增「本册只规定 5 类；其余按 `DADAO-13 §2`，未规定者为 0」；依据 `DADAO-13 §2`（11 项逐项比对一致）。
3. `escape`：增「帧中不保存 `prev_cfx`；目标 cfx 恒为当前 cfx」，逐字引 `DADAO-12 §5.3` 原文；依据 `DADAO-12 §5.3`。
4. power：§3 增 `cg7` 块 0 = BootROM（Tiny `0x3ff_ffff_0000`/64 KiB、Vast `0x3ff_ffc0_0000`/4 MiB、`attr = R|X`）与 `cg8`/`rc1`（Tiny ⇒ `CFXREG`）；依据 `DADAO-12 §3.8`/`§4.12`。
5. `switch_run_mode`：§2「不采用该值…读回最后一次写入值」→「**写入被忽略、读回恒 `3`**」；§4.4 同步；附录 0.4.3-rc 同步；依据用户裁定 ②。
6. `DADAO-12 §2.1`：`0x3_ffff_0000`/`0x3_ffc0_0000` → `0x3ff_ffff_0000`/`0x3ff_ffc0_0000`；`0.7.3-rc` 追加一条（版本不变）；依据用户裁定 ③。
**实现影响**：
- `switch_run_mode` 口径变更：QEMU（`m13-qemu-001`）与 gem5（`m13-gem5-002`）现为「保存写入值、仅异常进入强制 HYPV」⇒ 须改为「写入被忽略、读回恒 `3`」；归后续「三平台 hmon/开关对齐」任务，本任务不改实现。
- reserved 集：文档不再列举编号，实现侧集合不变（仍按上游现行表），**无行为变化**。
**验收结果**：证据脚本 full 9/9 PASS（version/reserved/cause_info/escape/power_cg7/switch_run_mode/d12_typo/lock/gates），rc=0；`--inject` 4/4（reserved 列举 / D12 笔误 / 版本不一致 / switch_run_mode 旧口径）「注入→FAIL→`cp`+md5 还原→回绿」，rc=0；锁 21 册、全部 sha=实测、相对 merge-base 恰 2 册变（Machine-v5、DADAO-12），其余 19 册不变。
**新发现/坑**：① 集合编号写进下游文档必然随上游漂移，引用规则优于抄值；② 检查器区间扫描须排除「地址分区键」句（`1..63` 为 cfx 1–63），否则误报；③ 锁检查以 HEAD 为基线时，WIP 已含改动会把「0 变化」判失败——应以 `merge-base` 为基线；④ 上游 §2.1 示例少一组 `FF`（已修并留变更记录）。
**遗留问题**：① L1 `make check` 在任务 worktree 中断于 `check-isa-coverage`（无 host 工具链构建树、`llvm-mc` 缺；纯文档改动未重建）——与本次改动无关。② `check-temp-dirs` 红来自其它任务的陈旧临时目录（非本任务产物），未删，由对应任务收尾清理。③ `README.md` 版本表「Machine 在研版本」仍 `0.4.2-rc`（不在本任务范围，未动；需随收尾同步）。④ L2 未跑（纯文档改动，无编译输入变化；由主会话收尾按需执行）。

#### 收尾（architect，2026-11-10 09:30）

- reviewer **Accepted**：reserved 规则可机械判定（`DADAO-12 §1` 表 3 行 `reserved`，现场解析 52 个编号），正文已无编号列举；`switch_run_mode` 三处自洽；`DADAO-12 §2.1` 两处笔误改正（`2^42−64KiB=0x3ff_ffff_0000`、`2^42−4MiB=0x3ff_ffc0_0000`，规则句未动）。
- 门控：5 个 spec 门控 + 10 个相关门控 rc=0；证据脚本 9/9、`--inject` 4/4；reviewer 另做 2 例独立注入（reserved 改回列举 / power cg7 值）⇒ 均真红 ⇒ `cp`+md5 还原回绿。
- 锁：21 册恰 2 行变（`Machine-v5`、`DADAO-12`），其余 19 册 sha 不变。
- 实现影响（转后续任务）：QEMU/gem5 的 `switch_run_mode` 需改为「写入被忽略、读回恒 3」。
- 文档项：`README.md` 的 Machine 在研版本随收尾同步到 `0.4.3-rc`（本收尾一并改）。

### 收尾后更正（architect，2026-11-10，用户裁定）

用户原话：「读回不应该恒为3，应该是保存的值，也就是3」⇒ 原措辞「读回恒 `3`」是**常量语义**，改为**寄存器保存值语义**：

- `§2`：写入被忽略（保存值保持 `3`），**读回为寄存器保存值**；
- `§4.4`：同上（引 `§2`）；
- 附录 `0.4.3-rc`：补一条澄清；
- 只读锁 sha 同笔重算（`Machine-v5` 一行）；
- 门控 `check-spec-readonly` / `check-spec-changelog` / `check-spec-drift` / `check-knowledge-refs` 复跑 rc=0。

实现影响不变：QEMU/gem5 需做到「写入被忽略、保存值保持 3」，而不是「读接口返回常量」。

