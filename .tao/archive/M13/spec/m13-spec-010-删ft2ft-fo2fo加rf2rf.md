# m13-spec-010: 删除 `ft2ft`/`fo2fo`、新增 `rf2rf`（OPC-octa / opx `111-100`）；「单精写入宽度」归位

**模块**：spec
**项目里程碑**：M13
**依赖**：**等 M12 收尾**（`m12-integ-002` 验证通过）后再开工——用户 2026-11-14 明示「影响面比较大，等 M12 收尾后再进行」
**可并行分片**：否（ISA 变更，spec/契约/实现/测试须同批次对齐）
**预估**：spec 侧 3–5 h（实现/测试另立任务）
**挂起**：等 M12 **完全收尾**（用户 2026-11-14 裁定：不提前开工；须 `m12-chipyard-016` 合入 **且** `m12-integ-002` 验证通过）
**状态**：已验证

## 用户裁定（2026-11-14，原话）

> 「M13增加：删除ft2ft和fo2fo，增加rf2rf，opc为OPC-octa，opx为111-100；该指令描述放到SimRISC-02中，和rf2rd/rd2rf在一起；注意：该指令不能用rf0做目的操作数，否则ILLI，其它限制参考 寄存器组之间块赋值 的其它指令。此外，**单精（ft）结果的写入宽度** 这部分说明需要保留，应该放在SimRISC-00的2.3，以及SimRISC-07的最头上。这部分改动，影响面比较大，等M12收尾后再进行」

## 目标（spec 侧）

1. **删除** `ft2ft`、`fo2fo` 两条指令（ID、编码、语义段、汇编助记符），其 `opx` 槽位处置见「待裁定」。
2. **新增** `rf2rf`：
   - 编码：`opc = OPC-octa`、`opx = 111-100`（`ha = 0x3C`）；操作数形式与 `rf2rd`/`rd2rf` 同族（`orri`，`rf` 组）；
   - 语义：**rf 组内块复制** `rf2rf {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}`（源 `rfHC` 起、目的 `rfHB` 起，各 `immu6` 个）；
   - 限制（沿用 §1 寄存器组块复制族）：`immu6` = 0 ⇒ ILLI；起始 + `immu6` > 64 ⇒ ILLI；源/目的范围**任何重叠** ⇒ ILLI；**目的含 `rf0` ⇒ ILLI**（用户显式，注意与 `rd2rf` 允许 `rf0` 作目的不同）；`rf0` 作**源**按现有规则（读出完整 64 位，`rd2rf`/`rf2rd` 的注已写）。
   - 位置：`spec/SimRISC-02-寄存器复制.md`，紧跟 `rf2rd`/`rd2rf`；同步其 §1 分类计数、§表格、合法性清单（`dst_rf0`/`mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap` 等规则覆盖）。
3. **「单精（ft）结果写入宽度」保留并归位**：
   - 全文搬入 `spec/SimRISC-00` **§2.3 浮点寄存器**（作为 rf 组写语义的一部分）；
   - `spec/SimRISC-07` **最头上**（§1 之前、规范性引用之后）保留一份**同等效力**的说明（或明确指针 + 关键句），因为它是浮点册的写宽总则；
   - 判据不变（ft 结果族只写低 32、高半保持；例外：`rd2rf`/`rf2rd` 整 64 位、`cs.*` 整 64 位），但**删掉对 `ft2ft`/`fo2fo` 的引用**（它们已删除），改为「rf 组块复制 `rf2rf` 整 64 位逐位复制」。

## 影响面清单（现场 grep，非全部逐条核）

- **spec**：`SimRISC-07`（复制类、写宽段、编码表、NaN 不适用清单）、`SimRISC-02`（分类、语法、限制、表格、合法性清单）、`SimRISC-00`（§2.3、编码主表/子表、附录变更记录）、`SimRISC-03`/`Toolchain-01`/`DADAO-12`（提及处）。
- **契约**：`.tao/contracts/contract-fp.md`、`contract-isa.md`、`contract-asm.md`、`contract-asm-list.md`；`contracts/opcodes.yaml`（`ft2ft_orri_rf`/`fo2fo_orri_rf` 删除、新增 `rf2rf` 条目）、`legality_rules.yaml`（`dst_rf0` 等规则覆盖新 id、删旧 id）、`fp_semantics.yaml`。
- **讲义**：`docs/DDLN/A-指令系统/DD-A009`（浮点运算）、`DD-A002`（指令编码）。
- **实现**（另立任务，逐组件）：LLVM `.td`/MC（编码 + 助记符）、QEMU（`insn.decode`/`trans_*`）、gem5（解码表 + exec）、chipyard RTL（译码/执行）。
- **测试**：`tests/inst/07-floating-point/`（`ft2ft_orri_rf.S`/`fo2fo_orri_rf.S` 删除或改指 `rf2rf`）、`tests/inst.yaml`、`case-ledger`、`tests/inst/inventory.md`、`MIGRATION.md`；`check-inst-asm` 264 id → 263 id（删 2 加 1）。
- **矩阵/工具**：`tools/testcases/generate_lit_vectors.py`、`validate_mc_vectors`、`min_rom_probe_036t.py` 等提到 `ft2ft`/`fo2fo` 的地方。

## 验收（spec 侧；实现/测试任务另立后各自验收）

1. 旧指令归零：`grep -rn "ft2ft\|fo2fo"` 在 `spec/`、`.tao/contracts/`、`contracts/`、`docs/DDLN/` 内 0 命中（`.tao/adr/`、`.tao/archive/` 历史保留）。
2. 新指令在位：`SimRISC-02` 有 `rf2rf` 语法/语义/限制/表格行；`contracts/opcodes.yaml` 有 `rf2rf` 条目（`opc=OPC-octa`、`ha=0x3C`、`orri`/`rf`、`dst_rf0 ⇒ ILLI`）；`legality_rules.yaml` 的规则覆盖新 id。
3. 单精写宽说明在 `SimRISC-00 §2.3` 与 `SimRISC-07` 开头各一份（或一处正文 + 一处指针），判据与今天一致；不再引用已删指令。
4. 编码不冲突：`opcodes.yaml` 全量 id 的 `mask/value` 两两不重叠（机械核）；`check-isa-coverage` 计数一致。
5. 门控 rc=0：`check-spec-readonly`（锁同笔重算改动册）、`check-spec-changelog`、`check-spec-purity`、`check-spec-refs`、`check-asm-list`、`check-asm-prose`、`check-rule-refs`、`check-legality-drift`、`check-legality-invariants`、`check-spec-cite-targets`、`check-spec-numbering`、`check-knowledge-refs`、`check-isa-coverage`。
6. ≥2 路可达 FAIL 注入（`cp`+md5 还原）。
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 已裁定（用户 2026-11-14）

1. **旧编码槽位**：`ft2ft`/`fo2fo` 的两个 `opx` **空置为 reserved**（执行 ⇒ `UNDI`），并在 `opcodes.yaml`/`legality_rules.yaml` 显式登记。
2. **落地范围**：**spec 与实现/测试同批**（不允许「spec 已改、实现还认旧指令」的中间态）。
3. **`rf2rf` 语义**：按本册「目标 2」所写（rf→rf 块复制；源可为 `rf0`；目的区间含 `rf0` ⇒ ILLI；`immu6` 1..63；源/目的任何重叠 ⇒ ILLI；不置标志、不做数值换算）。

### 同批任务（本册为批次总纲；各子任务书在派单时创建，合并时作为一批）

| 序号 | 模块 | 内容 | 预估 |
|---|---|---|---|
| 1 | spec（**本册**） | spec/契约/讲义/锁：删 2 加 1、reserved 登记、单精写宽归位 | 3–5 h |
| 2 | `m13-llvm-001` | `.td`/MC：删两条助记符与编码、加 `rf2rf`（`OPC-octa`/`0x3C`），`llvm-mc` 往返 | 2–3 h |
| 3 | `m13-qemu-016` | `insn.decode` 重生成 + `trans_*`：删 2 加 1（含 `dst_rf0` ILLI、`immu6`/重叠/越界判定） | 3–4 h |
| 4 | `m13-gem5-014` | 解码表 + exec：删 2 加 1（同判据） | 3–4 h |
| 5 | `m13-chipyard-003` | RTL 译码/执行：删 2 加 1（同判据；component 单写者，须与其它 chipyard 任务串行） | 4–6 h |
| 6 | `m13-testcases-038` | `.S` 载体：删 `ft2ft_orri_rf.S`/`fo2fo_orri_rf.S`，新增 `rf2rf_orri_rf.S`（含 `rf0` 目的 ILLI 故障例、重叠/越界/`immu6=0` 故障例）；`inst.yaml`/`ledger`/`inventory` 同步 | 3–4 h |
| 7 | 批末 | 三平台逐字节 + `check-inst-asm` 263 id + 全部静态门控；矩阵/报告刷新 | 2–3 h（并入 testcases 或单列） |

- **批次合并规则**：7 件全部 `Accepted` 后**一次性**合入 master（或至少 spec + llvm + 三引擎 + 测试同一次合并窗口），中途不得只合 spec。
- **串行约束**：四个实现各自单写者；chipyard 与 `chipyard-002`/其它 chipyard 任务串行；`tests/inst` 与其它 testcases 任务串行。
- **门控联动**：`check-isa-coverage` 计数、`check-asm-list`、`check-inst-asm`（264→263 id）、`check-tests-index`/`case-ledger` 会同时变化，必须同笔对齐。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host`/`check-modules`/`build-*`**（spec 侧不需要构建）。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. `spec/` 正文禁止任务号/ADR/ISS 号；变更记录只写判据句。
5. 大文件落 `/tmp/opencode/m13-spec-010/` 并测完即删。

## 待裁定（engineer 提出，待主会话转达）

1. **`set.ft`/`set.fo` 的 rf→rf 源形式**：`rf2rf` 按整 64 位复制 ⇒ 该形式不再保留「只写低 32 位、高半保持」的窄写。
   - **A（临时处置，已落纸）**：保留该形式、展开为 `rf2rf`，并在 SimRISC-03 / Toolchain-01 / `contract-fp` 写明「整 64 位复制（不保留高半）」；
   - B：删除 rf→rf 源形式（`set.ft`/`set.fo` 只留 rd 源与立即数）；
   - C：另立窄写搬移（需新指令/新编码，超出本次裁定范围）。
   - **建议 A**（唯一不需要新增编码，且与写宽总则的「整 64 位例外」自洽）。
2. **旧 `opx` 槽位「显式登记」的落地形式**：`opcodes.yaml` 只登记真实指令（`check-scope` 要求 scope 六选一、UNDI 只用于空白格；为保留槽位建记录会同时破坏 scope/矩阵/lit 投影），故落地为「QFC 表留白 + `opcodes.yaml` 头部注记 + `legality_rules.yaml` 的 `excp_undi` 点名两格」。若须「以记录形式登记保留编码」，需新开 `decode: UNDI` 语义并同步改 5 个门控 —— 建议另立任务。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 生成器既存漂移：`generate_opcodes.py` 的 `leg_convert_*` 仍按 `immu6` 计数，而 committed `opcodes.yaml` 已按舍入三分（15 六档 / 3 SBZ）；直接重跑会毁掉 15+3 条转换的编码语义 | ✅已修 | `build_misc_rf` 拆 `leg_convert_onehot`/`leg_convert_onehot_f2i`/`leg_convert_sbz`；`EXPR_TO_RULE` 补 `immu6 == 0`→`encode_sbz` | 重跑后与 HEAD 数据 diff = 仅「删 2 条 + 加 `rf2rf`」（脚本逐记录比对：removed=2、added=1、changed=0）；二次重跑 md5 不变 |
| F2 `min_rom_probe_036t.py` 的 FF16/FF17 断言「同格式纯复制搬全部 64 位」，与写宽判据矛盾 | ✅已修 | 八个用例与两个编码函数改指 `rf2rf`（`0x40/0x3C`），期望改为整 64 位逐位复制 | 与 SimRISC-02/00 的 rf2rf 判据逐条对齐；`py_compile` 通过（执行仍阻塞至实现任务） |
| F3 `gen_isa_coverage.py` 的 MD 模板把 `reject` 记录一律渲染成 `scope: excluded`（本次 reject 是 `scope: fp` 的 `rf2rf`） | ✅已修 | 按现场 `r["scope"]` 逐条渲染 | 重生成后该行显示 `rf2rf_orri_rf（scope: fp）`；`check-isa-coverage` rc=0 |
| F4 删 SimRISC-07 §1.3 后 §1.4/§1.5 前移，册内「见 §1.3」与 `contract-fp` 的 `§1.3 复制` 引用失真 | ✅已修 | 符号位段改「见册首」；`contract-fp` 改引 `[SimRISC-00 §浮点寄存器][SimRISC-02 §寄存器组之间块赋值]` | `check-spec-refs` rc=0、`check-spec-cite-targets` rc=0 |
| F5 「rb/rf/ra 之间不能直接赋值」与新 `rf2rf`（同组 rf→rf）冲突 | ✅已修 | SimRISC-02 §1 与 `contract-isa` 两处补「同组块复制只有 `rd2rd`/`rb2rb`/`rf2rf`」 | 与 §1 语法块、附录 B 一致 |
| F6 `set.ft` 的 rf 源展开语义变化（窄写 → 整 64 位） | ⏸延后 | 落「待裁定 1」；临时处置 A 已写进三处正文 | `check-asm-prose` rc=0；`check-spec-codeblocks` rc=0 |
| F7 各处 FP 计数（`contract-fp`/`contract-isa`/`fp_semantics`/矩阵/汇编表）需现场派生、不得写死 | ✅已修 | 66→65、`dst_rf0` 41→40、`mreg_zero`/`range_overflow` 10→9、overlap 2→1；生成物全部重跑 | `check-fp-contract`/`check-rule-refs`/`validate-encoding`/`check-isa-coverage` 全 rc=0 |
| F8 证据脚本首版两处自伤：`validate_encoding.py` 未传文件参数（rc=1 恒红）、`check-knowledge-refs` 命中计数误算（把说明行计入） | ✅已修 | 传 `contracts/opcodes.yaml`；改为「唯一命中 = 基线文件且不含本任务」 | 脚本 32 项检查 0 失败 |

### 第 1 轮 reviewer 验收（大改档；下列 rc 均为 reviewer 本人重跑所得，非采信完成区）

1. **门控**：验收 13 条中 `check-spec-readonly`/`spec-changelog`/`spec-purity`/`spec-refs`/`asm-list`/`asm-prose`/`rule-refs`/`legality-drift`/`legality-invariants`/`spec-cite-targets`/`spec-numbering`/`isa-coverage` **12 条 rc=0**，`check-knowledge-refs` **rc=2**；另 `validate-encoding`（263 条 OK）/`check-scope`/`fp-contract`/`asm-list-drift`/`spec-drift`/`spec-codeblocks`/`check_qfc_coverage` **7 条 rc=0** ⇒ 合计 20 条：19 绿 1 红（完成区写「15/16」为笔误）。
2. **`check-knowledge-refs` rc=2 根因与反证**：唯一命中是 `m16-gem5-007` 任务书审阅记录第 110 行的一处具体证据路径；本分支基线 `121b819f` 落后 master `6fe49b18`（该提交正是把该行改占位、使其回绿）。reviewer 另建临时校验树：`6fe49b18` 单跑该门控 **rc=0**；`6fe49b18` + 本任务 27 文件 diff 重放后 **20 条门控全绿**（仅 `check-isa-coverage` 因临时树缺 llvm-mc 报「找不到 llvm-mc」，主树 rc=0）⇒ 非交付物缺陷、合入 master 后自动消失，**不计入返工范围**，合并后复跑即可。
3. **编码独立推导**：`opc=0x40` ⇒ bits[31:27]=`01000`（QFC 行 `0100-0xxx`）、bits[26:24]=`000`（列 `xxxx-x000`=OPC-octa）；`ha=0x3C` ⇒ opx=`111-100`（行 111 / 列 100），与用户裁定逐位一致；`value=(0x40<<24)|(0x3C<<18)=0x40F00000`、`mask=0xFFFC0000`（锁 bits[31:18]）成立；同族 `rd2rf=111-101`、`rf2rd=111-110` 不同格。
4. **自写全量重叠检查**：263 条两两 `(v_a^v_b)&m_a&m_b==0` ⇒ **0 对重叠**；`value & ~mask` 全 0；`distinct (op,ha)`=263。
5. **五条限制**：`opcodes.yaml::rf2rf` 五条 legality 齐（`rfhb != rf0`、`immu6 != 0`、`rfhb+immu6<=64`、`rfhc+immu6<=64`、`no_overlap(rfhb,rfhc,immu6)`），`rule_refs`=dst_rf0/mreg_zero/range_overflow/range_overlap；**源 `rf0` 无限制项 ⇒ 合法**；`SimRISC-02` §1 正文「目的范围含 `rf0` ⇒ ILLI（与 `rd2rf` 允许 `rf0` 作目的不同）」+「源 `rf0` 读完整 64 位」+ 其余三条限制逐条在位。
6. **写宽归位等价**：`SimRISC-00 §2.3`（`2.3.1` 之前）与 `SimRISC-07` 册首（规范性引用后、`## 1` 之前）各一份；核心判据「只写低 32、高 32 保持原值（不符号扩展、不零填）+ `ld.t`/`ldm.t` 同理」与改前 `contract-fp §1` 既有措辞逐字一致；例外仅按裁定把已删两条换成 `rf2rf` 整 64 位、并补入改前已在 `SimRISC-02` 写明的 `cs.*`-rf 整 64 位 ⇒ 判据等价、无新增语义。
7. **独立计数**：`opcodes.yaml` 263 条（唯一 id 263）、`scope: fp`=**65**、有 `rule_refs`=**242**、`dst_rf0`=**40**、fp `mreg_zero`/`range_overflow`=**9/9**、`overlap`=**3**；`check-isa-coverage` 真源 263 / accept 262 / reject 1；`check_qfc_coverage` QFC 263 = YAML 263、双向差 0。
8. **锁**：reviewer 自算 21 册 sha256 与 `manifests/spec-readonly.lock.toml` **逐册相等**（本任务同笔改 6 册）。
9. **幂等**：`generate_opcodes.py`、`gen_asm_list.py`（与入库逐字节相等）、`gen_isa_coverage.py`、`gen_legality_list.py --verify` 各连跑 2 轮，md5 全等、`git status` 空。
10. **注入 5 路**（自设计，非 engineer 那 2 路；均 `cp`+md5 还原）：① rf2rf `rfhb+immu6<=64→65` ⇒ `check-fp-contract` rc=2「legality 表达式无法分类: rf2rf_orri_rf:rfhb + immu6 <= 65」；② `SimRISC-00 §2.3` 低32→低16 ⇒ `check-spec-readonly` rc=2（sha256 mismatch，1/21）；③ 删 `rf2rf` 记录 ⇒ `check-asm-list-drift`/`check-isa-coverage`/`check-fp-contract` 三门控 rc=2；④ `SimRISC-02` 附录 B `mreg_zero` 行删 `rf2rf` ⇒ `check-legality-drift` rc=2；⑤ `SimRISC-07` 册首判据 32→16 ⇒ `check-spec-readonly` rc=2。还原后 15 门控 rc=0、四文件 md5 与注入前快照逐行相等、`git status -uall` 空。
11. **越界**：`git show --stat b1f6d8fb` = **27 文件**，与完成区声明逐项一致；`tests/inst/**`、`components/**`、`Makefile`、`discussing.md`、台账 **0 改动**；`git diff 6fe49b18..HEAD` 多出的 2 个文件是**基线落后**造成的反向差异、非本任务改动；`git stash list` 空、reflog 仅 1 次 commit ⇒ 无 checkout/restore/stash 迹象。
12. **阻断项（断言与计数：写死值 vs 现场值，3 处）**：
    - `.tao/contracts/contract-isa.md:51`「已归一化，共 **66** 条」⇒ 应 **65**（同文件 :917/:1504 已写 65，自相矛盾）；
    - `.tao/contracts/contract-isa.md:23`「2026-10-30 实测 **264** 条」⇒ 现场 **263**（改数并改日期，或删掉括号内写死值）；
    - `docs/DDLN/A-指令系统/DD-A001-指令系统--设计理念.md:154`「SimRISC：**66** 条」⇒ **65**；同文件 `:146`「200 条（266 − 66 FP）」按现值应 **198 条（263 − 65 FP）**（该行改动前已偏 2，属既存，随本笔对齐）。
13. **非阻断 finding**：① 完成区「15/16」与现场 20 条口径不一致（笔误）；② `manifests/spec-readonly.lock.toml:46` 历史注释仍点名两条已删指令（不在验收 grep 面内）；③ `check_qfc_coverage` 对 M1 外差异恒 exit 0（informational），删 `rf2rf` 靠其余门控拦；④ 既存过时计数簇（`contracts/README.md`、`.tao/contracts/README.md`、`legality_rules.yaml` 头注释、`docs/Process-02`、`docs/fp-oracle-design.md` 的「60 条」；TestReports 与 `docs/README.md` 的「66 条」）改动前即不成立，建议另立文档同步；⑤ 分支基线落后 master 1 提交。
14. **待裁定技术意见**：① `set.ft`/`set.fo` 的 rf 源形式——**倾向 A（保留形式 + 三处注明整 64 位）**：`rf2rf` 已是整 64 位、无窄写载体，B 会砍既有伪指令源形式、C 需新编码；但 A 使 `set.ft` 的 rf 源由「窄写」变「整 64 位」属**可观察语义变化**，建议批次合并前请用户点头。② 旧 `opx` 槽位——**同意「留白 + 注记 + `excp_undi` 点名」**（scope 词表无 UNDI 档，为保留槽位建记录会同时破坏 scope/矩阵/lit 投影）；「以记录形式登记」须新开 `decode: UNDI` 语义并改 5 个门控，建议另立任务。
15. **判决：Needs Revision** —— 仅第 12 条 3 处计数需返工；第 1–11、13–14 条全部通过。`check-knowledge-refs` 依第 2 条不计入返工；返工后 reviewer 复跑同一门控集 + ≥4 路注入收口。

### 第 1 轮 reviewer 返工复核（仅核返工面；下列 rc 均为 reviewer 本人重跑）

1. **3 处计数自洽**：现场 `grep` —— `contract-isa.md` 中 `264`/`66 条` 0 命中（唯一 `264` 命中是 :1562 的编码值 `0x42640000`）；`:23`=「2026-11-15 实测 **263** 条」，`:51`/`:917`/`:1504` 三处均 **65 条**、互不矛盾；`DD-A001:154`=「**65** 条」、`:146`=「**198 条（263 − 65 FP）**」（263−65=198 ✓）。
2. **锁注释判断成立**：`check_spec_readonly.py` 只解析 `[[spec]]` 条目并强制 `path` 以 `spec/` 开头，锁文件自身不在被钉清单（亦无法自钉）；另两个读锁的 `check_spec_changelog`/`check_numbering` 只取数据字段、不校验锁文件哈希；本次对锁文件的 diff **仅 1 行注释**、`[[spec]]` 与 sha256 未变 ⇒ 确无需重算；reviewer 自算 **21 册 sha256 全相等**。
3. **门控（我自跑，20 条全 rc=0）**：`check-spec-readonly`(21 册 OK)/`spec-drift`/`asm-list-drift`(byte-identical)/`legality-drift`(12 chapters)/`isa-coverage`(真源 263、accept 262/reject 1)/`fp-contract`/**`check-knowledge-refs`(PASS，具体引用 0、悬空 0)**，加 `changelog`/`purity`/`refs`/`asm-list`/`asm-prose`/`rule-refs`/`legality-invariants`/`cite-targets`/`numbering`/`validate-encoding`(263 OK)/`scope`/`spec-codeblocks`/`check_qfc_coverage` 均 rc=0 ⇒ 完成区「**20/20**」属实。
4. **基线合并**：`git log --oneline -3` = `052c2390` 返工 / `35fa1946 Merge branch 'master' into m13-spec-010` / `9e004395`；`git show --stat 35fa1946` 8 文件全为 master 自身改动，且 `git diff 9e004395 HEAD -- <该 8 文件>` = **0 行**（逐字节同 master）⇒ 未夹带本任务外改动；返工面 `git diff 35fa1946..052c2390` = **4 文件**（contract-isa、DD-A001、lock 注释、任务书），与自述一致。
5. **文档面**：完成区 10 行 ≤30、无运行期路径；`ft2ft|fo2fo` 在 `spec/`、`.tao/contracts/`、`contracts/`、`docs/DDLN/`、`manifests/` 全 **0** 命中；第 1 轮 reviewer 记录**原样保留**（diff 仅在其后追加、未改写）。
6. **判决：Accepted** —— 第 12 条 3 处阻断全部消除、无新增问题，`check-knowledge-refs` 已随基线合并转绿；非阻断 finding 沿用第 1 轮第 13 条（既存「60 条」计数簇等）留后续文档同步。

## 完成区

**测试结果**：门控 **20/20 rc=0**（首轮为 19 绿 + `check-knowledge-refs` 1 红，红因基线 `121b819f` 落后 master、`m16-gem5-007` 任务书内 1 处具体引用未修；合并 master 后转绿，非交付物缺陷）。计数：`opcodes.yaml` 264→**263**（fp 66→65）；`check-isa-coverage` 记录 264→263（accept 262 / reject 1 = `rf2rf` 待后端受理）。
**修改文件**：spec/{SimRISC-00,SimRISC-02,SimRISC-03,SimRISC-07,Toolchain-01,DADAO-12}；`.tao/contracts/{contract-fp,contract-isa,contract-asm,contract-asm-list}`；`contracts/{opcodes.yaml,legality_rules.yaml,fp_semantics.yaml}`；`manifests/spec-readonly.lock.toml`（6 册 sha256 同笔重算 + 1 处历史注释去旧名）；`docs/DDLN/A-指令系统/{DD-A001,DD-A002,DD-A009}`；`tools/spec/{generate_opcodes.py,check_asm_prose.py}`；`tools/llvm/{gen_asm_list.py,gen_isa_coverage.py,test_encoding_oracle.py,llvm-isa-backend-matrix.tsv,llvm-isa-backend-matrix.md}`；`tools/testcases/{generate_lit_vectors.py,validate_mc_vectors.py,arch/min_rom_probe_036t.py}`。
**验收结果**：旧名归零 = spec/.tao-contracts/contracts/docs-DDLN 各 0 命中；`rf2rf` 编码 `opc=0x40(OPC-octa)`/`ha=0x3C`/`value=0x40F00000`/`orri`/`rf`，legality 含 `rfhb != rf0`、`immu6 != 0`、两起始 + `immu6 <= 64`、`no_overlap(rfhb, rfhc, immu6)`；写宽两份：`SimRISC-00 §2.3` 正文 + `SimRISC-07` 册首同等效力段；门控 rc 全 0（readonly/changelog/purity/refs/asm-list/asm-prose/rule-refs/legality-drift/legality-invariants/cite-targets/numbering/isa-coverage + validate-encoding/check-scope/check-fp-contract/check-asm-list-drift/check-spec-drift）。
**新发现/坑**：① 生成器与入库 `opcodes.yaml` 曾漂移（SPEC-194t 只改数据未改生成器）⇒ 已修并验证可复现；② 生成物一律重跑（含覆盖矩阵），否则 `--check` 必红；③ 保留槽位只能「留白 + 注记」登记（scope 词表没有 UNDI 档）。
**遗留问题**：待裁定 2 项（见上，按 A/「留白+注记」处置）。以下**不属本任务**、需后续任务改：`tests/inst/07-floating-point/{ft2ft,fo2fo}_orri_rf.S` 与 `tests/inst.yaml`/`case-ledger`/`MIGRATION.md`/`README.md`（→ testcases 任务：删 2 加 1，263 id）；`tests/unit/llvm/lit/{MC/DADAO,MC/DADAO-gen,CodeGen/DADAO}/*`（→ llvm 任务）；`components/{llvm-project,qemu,gem5,chipyard}` 的 patch 与 changelog/README（→ 四个实现任务）；`tools/gem5/{b7_ref.py,check_b7.py,wuming_cycles.yaml}` 与 `components/gem5/decode-assertions.tsv`；`docs/{TestReports/M13-FP-IEEE对齐审计.md,core-wuming-cycle-model.md}` 及 `components/*/README` 内的旧指令名与「SimRISC-07 §1.3/§1.4」旧节号（纯文档同步）。

**返工（第 1 轮）**：按 reviewer 阻断项改 3 处写死计数——`contract-isa` 的 `scope: fp` 66→**65**、`opcodes.yaml` 实测条数 264→**263**（日期同改 2026-11-15，保留「现场派生」句义，不删括号）；`DD-A001` 泛算数 200（266−66）→**198（263−65）**、浮点 66→**65**（前者改动前已偏 2，随本笔对齐）。顺手项：完成区「15/16」→现场 **20/20**；`spec-readonly.lock.toml` 历史注释的旧指令名改为「块复制族」（**无需重算 sha256**：锁只钉 `spec/` 21 册，锁文件自身未入锁）。
**基线**：分支融合 master `9e004395`（merge commit `35fa1946`；master 7 提交，含 `check-knowledge-refs` 基线修复），合并后该门控 rc=0。
