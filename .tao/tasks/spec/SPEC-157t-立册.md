# SPEC-157t: `ftfma`/`fofma` 立册（四操作数 FMA，`rrrr`，`op 0x5E/0x5F`）

**模块**：spec
**项目里程碑**：M9（FP 完备性）
**依赖**：无（本册只立记录与语义）；后续 `QEMU-070t` → `LLVM-123t` → `SPEC-158t`（翻转 `excluded → fp`）→ `TESTCASES-058t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 用户裁定（2026-10-21，原话）

> 「增加任务：ftfma/fofma指令，orrr格式，点积型，OPC-RF，opx为100-010/101-010」
> 「格式改为rrrr，即4个操作数；编码改为ftfma/fofma：0100-0110/0100-0111」（2026-10-22 修订，**以本条为准**）

助记符经确认为 **`fma`**（非 `madd`/`fla`）：FMA 是 IEEE 754 `fusedMultiplyAdd`、LLVM `llvm.fma`、C `fma()` 的通用名；`madd` 会与"`fomul` 再 `foadd`"混淆，`fla` 不表意。

### 现场事实（2026-10-21 核，执行前须复核）

- **`rrrr` = 4 个寄存器槽**（`ha`/`hb`/`hc`/`hd`），本册用作 **1 目的 + 3 源**：`rfHA ← rfHB × rfHC + rfHD`；**`dst_dual_same` 不适用**（那是 `add.uo`/`mul.uo` 等 2 目的形态的规则）。
- 编码落 **`0101-1xxx` 行**：原 `cs.eq_rrrr_rf = 0x5E`（`0101-1110`）、`cs.ne_rrrr_rf = 0x5F`（`0101-1111`）**已由 `SPEC-163t` 删除腾出** ⇒ 取 **`ftfma = 0x5E`、`fofma = 0x5F`**。
- `rrrr` 无 opx ⇒ 每条占一个整 op 字节（这是选主表的代价）；OPC-RF 的 `0x22`/`0x2A` **不再占用**（留空）。
- 汇编形态为**四个普通寄存器**（不是 `{rdA,rdB}` 双目的写法）⇒ `gen_asm_list` **不得**按双目的渲染。
- 现有 `SimRISC-07 §1.1` 速查 = **44 条**（`scope: fp（已实现）`）；加两条 ⇒ 46 条。
- `check_fp_contract.py` 的族/计数由现场派生（`INFRA-102t` 后无写死常量）；现场 `fp` **64**、**14 族**；`scope: excluded` 的记录**不**进 `fp_semantics.yaml` ⇒ 本册**不动**族表/计数（族 `fma` 与 `fp 60→62` 留到 `SPEC-158t` 翻转时）。

## 目标

1. 立 `ftfma`/`fofma` 两条记录（`scope: excluded`、`decode: ILLI`），编码/semantic/合法性/异常齐备；
2. 规范正文写清**四操作数**语义（`rfHA ← rfHB × rfHC + rfHD`）与"目的与源重叠时先读后写"；
3. 生成物与计数同步；`check-instrinfo` 不因"excluded 无 `.td`"报错（`fence` 先例）。

## 接口规范

- **输入**：`tools/spec/generate_opcodes.py`、`tools/spec/check_scope.py`、`spec/SimRISC-07-浮点运算.md`、`.tao/contracts/contract-fp.md`、`manifests/spec-readonly.lock.toml`。
- **输出**：`contracts/opcodes.yaml`（**264→266**）、`SimRISC-07` 新增 fma 语义小节、`contract-fp.md` 新增 `fma` 段（含 `<a id="fma">` 锚点，供 `fp_semantics.yaml` 后续引用）、`gen_asm_list --embed-spec`/`--drift`、`gen_isa_coverage`、只读锁重算、证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：**不**改 `components/**`、`tests/**`；不改门控判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 语义（四操作数：`rfHA ← rfHB × rfHC + rfHD`）

```
ftfma rfHA, rfHB, rfHC, rfHD      @ rfHA ← rfHB × rfHC + rfHD（单精度，单次舍入）
fofma rfHA, rfHB, rfHC, rfHD      @ rfHA ← rfHB × rfHC + rfHD（双精度，单次舍入）
```

- **必须写清**：「目的 `rfHA` **允许**与任一源重叠 ⇒ 硬件**先读**全部源再写结果，行为确定」。
- **单次舍入**：`a×b` 的精确积只舍入一次（`fma` 的核心；与 `fomul`+`foadd` 两条不等价，须给出反例例子）。
- **`×` 可交换**：`rfHB`/`rfHC` 互换结果不变；`rfHA` 与源重叠时按"先读后写"。
- **异常**：sNaN 输入 ⇒ NV + qNaN；结果溢出/下溢按 IEEE 置 OF/UF；**一次运算只置一次**。

### B. 合法性

- 目的 `rf0` ⇒ **ILLI**（`dst_rf0`，与 FP 族 30 条一致）；
- 源可为 `rf0`（读出 FCSR 的 qNaN 位，符合既有 FP 源语义）；
- 无 `rd0`/dual-dest 概念（`rf` 组；本册**不得**引入 `dst_dual_same`）。

### C. 编码与生成物

- `format = rrrr`、`op = 0x5E`（`ftfma`）/ `0x5F`（`fofma`）、**无 `ha`**（整 op 字节选格）；`scope = excluded`、`decode = ILLI`；
- `check_scope.py`：**无写死常量**（`INFRA-102t` 后按现场派生）；现场期望 `excluded 2→4`、`total 264→266`（`fp` 仍 64）+ changelog 一行；
- `generate_opcodes.py`：`rec(...)` 两条 + 文件头计数注释；`docstring` 的 scope 说明补 `fma`；
- 生成物：`gen_asm_list --embed-spec`（速查 44→46）、`gen_legality_list --apply`（`dst_rf0` 清单 + excluded 区块）、`gen_isa_coverage`、`.tao/contracts/contract-asm-list.md`；
- `SimRISC-07` 变更记录**追加** 1 行；只读锁重算。

## 验收标准

1. `contracts/opcodes.yaml` = **266** 条；`excluded` = **4**；`fp` = **64**（现场输出）。
2. `check_scope` / `validate-encoding` / `check-rule-refs` / `check-instrinfo`（0 errors，`excluded` 无 `.td` 合规）/ `check-isa-coverage` / `check_fp_contract`（**14 族 / fp 64** 不变）全绿。
3. `check-asm-list` / `--drift` / `--prose` / `check-spec-codeblocks` / `check-spec-*` / `check-spec-readonly` 全绿。
4. `make check`（L1）rc=0。**L2 不在本册验收面**：`check_qemu_trans --strict` 因新增记录缺 trans 会红（**登记 issue**，由 `QEMU-070t` 关闭；与 `ISS-317` 同类）。
5. **可达 FAIL ≥ 2**：① 忘改 `check_scope` 计数 ⇒ `check-scope` 红；② 不改只读锁 ⇒ `check-spec-readonly` 红。
6. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（`0x5E`/`0x5F` 空闲、`rec()` 形态、`rrrr` 在速查表与 `gen_asm_list` 的渲染、`contract-fp.md` 锚点风格）。
2. 生成器加两条（`excluded`）+ 计数 + `check_scope` 计数。
3. 写 `SimRISC-07 §4.x`（四操作数语义、先读后写、单次舍入、异常）与 `contract-fp.md §fma`。
4. 重生成全部产物 → 门控；只读锁重算；变更记录 1 行。
5. 反例注入 + L1 + 完成区 + 登记缺口 issue。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- 临时把 `check_scope.py` 的 `excluded` 计数改回 28（或漏改）⇒ `check-scope` 红；还原 ⇒ 绿。
- 不更新 `manifests/spec-readonly.lock.toml` ⇒ `check-spec-readonly` 红；重算 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 本册**不**实现（QEMU/LLVM 各一册）；**不**翻转 `scope`（`SPEC-158t`）。
- 不做 `fmsub`/`fnmadd`/`fnmsub`（负号用 `fosgnn` 或后续另立 opx）。
- 不做 `fmsub`/`fnmadd` 的硬件版（负号用 `fosgnn` 组合，结果逐位精确）。
- 不引入 `dst_dual_same`；不改 `rf0` 语义。

## 完成区

**测试结果**：`.work/evidence/SPEC-157t/run.sh` **rc=0**（40 项 PASS，1m12s）：结构化断言（checks.py）+ 16 项门控 + 3 次注入（注入⇒红⇒`cp`+md5 还原⇒绿）+ 1 项预期红。`make check`（L1）**rc=0**（`repository checks (L1): PASS`）；`check_scope` 现场 `m1=156, fp=64, excluded=4, m3=1, m8=7, m9=34, total=266`；`check_tables` 6 表 177 条 0 格不符；`check_instrinfo` **0 errors**（FP 64/64 有 def，4 条 excluded 无需 def）；`validate-encoding` 266 条 OK；`check-spec-purity` 13 册 0 命中；`check-spec-codeblocks` 661 行；`check-spec-readonly` 21 册 OK；`check-fp-contract`/`check-isa-coverage`/`check-asm-list{,-drift}`/`check-legality-drift`/`check-spec-cite-targets` 均 rc=0。
**修改文件**：`tools/spec/generate_opcodes.py`（2 条 `rec` + `S07_FMA` + 头/文档计数）；`contracts/opcodes.yaml`（生成，266/excluded 4）；`spec/SimRISC-00`（主表 `0101-1xxx` x110/x111 + 变更记录 1 行）；`spec/SimRISC-07`（新增 §2.5 + 附录 A/B 重生成）；`.tao/contracts/contract-fp.md`（§20 `fma`）；`.tao/contracts/contract-asm-list.md`（生成）；`.tao/contracts/contract-isa.md`（§0 计数）；`manifests/spec-readonly.lock.toml`（SimRISC-00/07 sha256）；`.tao/knowledge/milestones.md`（状态行）；`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（生成）；`.tao/knowledge/issues.yaml`（ISS-330/331）；`.work/evidence/SPEC-157t/{run.sh,checks.py}`。
**验收结果**：`ftfma_rrrr_rf`/`fofma_rrrr_rf`：`op 0x5E/0x5F`、`mask 0xFF000000`、`value 0x5E000000/0x5F000000`、`format rrrr`、fields `rfha..rfhd` roles `dst/src/src/src`、`scope excluded`+`decode ILLI`、`spec_cite SimRISC-07: ftfma|fofma`、legality `rfha != rf0`。主表 x110/x111 两格已落 `ftfma_rrrr_rf`/`fofma_rrrr_rf`（原残留 `cs.eq/ne_rrrr_rf` 清除；变更记录保留删格历史）。附录 A 52 行 = 现场派生（50 `fp` + 2 `excluded`）；附录 B 列两条 `decode ILLI`。`fp` 仍 64、12 族不变；`fp_semantics.yaml` 未收录（excluded）。`check_qfc_coverage` 主表↔yaml 差异 **2→0**。
**新发现/坑**：① `excluded ⇒ rule_refs: []` 是 `_compute_rule_refs` 的硬规则 ⇒ 任务书写的 `rule_refs: [dst_rf0]` 在 excluded 期不成立；已保留 legality 表达式 `rfha != rf0`，`SPEC-158t` 翻转后自动回填 `dst_rf0`（勿手工改 yaml）。② **`rrrr` 单目的+三源形态无字面量门控**：`check_asm_prose` R6 假设 rrrr 必带 `{}`（四寄存器写法直接判红）、`Toolchain-01 §6` 格式表也无此行；为守「不改门控判定语义」，§2.5 改用行内代码书写并登记 `ISS-331`。③ `check_tables` 只覆盖 6 张子表，**主表格位无门控**（本次由证据脚本自断言 + `check_qfc_coverage` 现场 0 差异）。④ `gen_asm_list --embed-spec` **非幂等**：改写 12 册且各多 2 个空行 ⇒ 已 `git checkout --` 还原 11 册无关文件、SimRISC-07 手工折回单空行。⑤ 下游 `QEMU-070t`/`LLVM-123t` 任务书仍按**三操作数累加器**形态写（`ftfma rfHB, rfHC, rfHD` = `rfHB ← rfHC×rfHD + rfHB`），与本册四操作数裁定冲突，派发前须改书。⑥ `generate_lit_vectors.build_case` 对 rrrr 亦按双目的渲染（矩阵 `L1_asm` 列显示带 `{}`），翻转 `fp` 前须修（已并入 `ISS-331`）。⑦ 反例位型自审时发现手算笔误（`1−2⁻²³` 应为 `0x3F7F_FFFE`，非 `...FFFF`），已按 `Fraction`+`struct` 独立重算订正并加入证据脚本。
**遗留问题**：① `check_qemu_trans --strict` **预期红** rc=1（`264/266`，缺 `trans_ftfma_rrrr_rf`/`trans_fofma_rrrr_rf`）、`check-interface` 同因预期红（L2 不在本册验收面）⇒ 登记 `ISS-330`，由 `QEMU-070t` 关闭。② `ISS-331`（`Toolchain-01 §6` 形态表 + R6 数据驱动化 + `build_case` 渲染）待后续册。③ `fp_semantics.yaml` 族 `fma` 待 `SPEC-158t`。④ `contract-isa.md §0` 的 `m9`(9→34)/`excluded` 行原已落后于现场，本册按 excluded 变化一并订正（汇总 266 自洽）。⑤ `milestones.md` 状态行已同步 `待验收`（`check-milestones-fresh` A1），`已验证`/提交由主会话收尾。


## 审阅记录

### 第 1 轮 engineer 自审（2026-10-23）

审查方式：逐行读改动（`generate_opcodes.py` 新记录与计数、`SimRISC-00` 格位、`SimRISC-07 §2.5`、`contract-fp §20`、锁注释、证据脚本），并对每条断言做可达 FAIL 核对。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务书要求 `rule_refs: [dst_rf0]`，与 `excluded ⇒ rule_refs: []` 机制冲突 | ✅已修（按机制，不改语义） | yaml 由生成器产出空 refs；legality 保留 `rfha != rf0`，注释说明翻转后自动回填 | `checks.py` 断言 `rule_refs == []` PASS；`check-rule-refs` rc=0 |
| F2 四寄存器写法触发 `check-asm-prose` R6（rrrr 必带 `{}`） | ✅已修（不改门控） | §2.5 改用行内代码书写 + 明示「不使用花括号」；登记 `ISS-331` | `make check-asm-prose` rc=0；run.sh rc=0 |
| F3 `--embed-spec` 非幂等，污染 11 册（各 +2 空行） | ✅已修 | `git checkout --` 还原 11 册（本无预期改动）；SimRISC-07 折回单空行 | `git status` 仅 2 册 spec 改动；`check-asm-list` 12 files OK |
| F4 注入还原判据用 `git diff` 对已修改文件恒真（假绿风险） | ✅已修 | 注入断言改「git diff 非空 **且** md5 变化」；还原用 md5 对账 | run.sh 三项注入各 PASS（红⇒还原⇒绿） |
| F5 反例 `b = 1−2⁻²³` 手写位型错为 `0x3F7F_FFFF`（实为 `...FFFE`） | ✅已修 | 规范正文与证据脚本订正；脚本按 `Fraction`+`struct` 独立重算 | `checks.py` 6 条反例断言 PASS（含 fma `0xA8800000`、mul→add `+0`） |
| F6 主表格位无门控（`check_tables` 只覆盖 6 子表） | ⏸延后（超本册范围） | 证据脚本自断言两格 + `check_qfc_coverage` 现场差异 0 | `checks.py` 主表 x110/x111 断言 PASS |
| F7 下游 `QEMU-070t`/`LLVM-123t` 任务书仍按三操作数累加器形态 | ⏸延后（改书非本册权责） | 完成区「新发现⑤/遗留②」留 architect 派发前处理 | 现场读任务书原文（`rfHB ← rfHC × rfHD + rfHB`） |

判决：**全部 finding 已修或已按边界延后登记，无未处置项 ⇒ 状态置 `待验收`**。

### 第 1 轮 reviewer 验收（2026-10-23，独立重跑；rc 取被检命令自身，未用 `| tail` 取码）

**重跑记录**（workdir=仓库根，相对路径）：
- `bash .work/evidence/SPEC-157t/run.sh` → **rc=0**，`[PASS] 40 / [FAIL] 0`，real 1m12.095s；其内 17 项门控 rc 全 0（含 L1）。
- `make check`（L1，**我方单独重跑**）→ **rc=0**（40s），尾行 `repository checks (L1): PASS`。
- `python3 tools/spec/check_scope.py` → rc=0，`m1=156, fp=64, excluded=4, m3=1, m8=7, m9=34, total=266` ⇒ **total 266 / excluded 4 / fp 64 与现场一致**。
- 其余 rc=0：`check_tables`（6 表 177 条 0 格不符）、`make check-spec-purity`（13 册 0 命中）、`make check-spec-cite-targets`（unresolved=0）、`make check-instrinfo`（0 errors）、`validate-encoding`（266 条 OK）、`check-rule-refs`、`check-fp-contract`、`check-spec-readonly`（21 册）、`check-spec-codeblocks`（661 行）、`check_qfc_coverage`（主表↔yaml 差异 0）。
- 预期红（我方单独跑）：`python3 tools/qemu/check_qemu_trans.py --strict` → **rc=1**，`264/266`、`missing=2, orphan=0`，`MISSING: ftfma_rrrr_rf`/`fofma_rrrr_rf`；`make check-interface` → **rc=2**，FAIL 项**恰 2 条**（同因缺 trans），ELF/ADR/Schema 三组全 PASS ⇒ **除这 2 条外无新红**。

**记录字段（现场读 yaml）**：`ftfma_rrrr_rf` `op 0x5E`、`fofma_rrrr_rf` `op 0x5F`，`format: rrrr`，fields `rfha[23:18] role=dst` + `rfhb[17:12]`/`rfhc[11:6]`/`rfhd[5:0] role=src`（**1 目的 + 3 源**），`scope: excluded`、`decode: ILLI`、`legality: [rfha != rf0]`；`rule_refs: []` 与 excluded 口径**自洽**（`_compute_rule_refs` 硬规则，翻转后回填；`check-rule-refs` rc=0）。主表 `0101-1xxx` x110/x111 = `ftfma_rrrr_rf`/`fofma_rrrr_rf`（0101-1110/1111 = 0x5E/0x5F ✓，`cs.eq/ne_rrrr_rf` 残留已清，变更记录 1 行已追加）。

**语义正文**：`spec/SimRISC-07 §2.5`（L191–233）写清 `rfHA ← rfHB × rfHC + rfHD`、**单次舍入**（精确积不先舍入、只在最后舍一次，含 `0xA880_0000` vs `+0` 反例）、NaN/sNaN⇒NV、`0×±Inf`、`Inf+(−Inf)`、±0 零符号、OF/UF/NX 一次运算一次、不触发陷阱、目的与源重叠**先读后写**、乘法可交换；手工 grep `scope|SPEC-\d{3}|ADR-\d{4}|ISS-\d{3}|excluded|266|总计|条数` → **rc=1（0 命中）** + purity rc=0 ⇒ **正文明净 ✓**。

**编码唯一性（全表现场核）**：`id` 无重复；`(op,mask,value)` 无重复；`value` 无重复；`op 0x5E/0x5F` **仅**这 2 条占用（其余重复 op 均属带 `ha`/`opx` 的 OPC 子表）。

**注入 2 次（我方独立，`cp` 备份 + md5 对账，未用 git 还原）**：① `ftfma op 0x5E→0x77`（md5 `363410e8…`→`13bb225c…`）⇒ `validate-encoding` **rc=1**（`value=0x5E000000 与 op/ha 不自洽 (期望 0x77000000)`）、`make` rc=2；还原 md5 相等 ⇒ rc=0。② `SimRISC-07 §2.5` 塞 `SPEC-8888t`+`scope`+`ADR-9999`（md5 `2ddf1adf…`→`76c0452c…`）⇒ `check-spec-purity` **rc=1**（hits=3：范围标注 scope / ADR 指针 / 任务号）、`make` rc=2；还原 md5 相等 ⇒ rc=0（13 册 0 命中）。

**约束核验**：`git diff b5210554~1..b5210554 -- components/` **空**（未改实现）；`-- tests/` **空**；`tools/` 下仅 `generate_opcodes.py` 与生成的 llvm 矩阵 ⇒ **门控脚本零改动**（无凑绿）；提交 13 个文件与完成区「修改文件」逐项对齐；前/后 `git status --porcelain -uall` 快照一致、三文件 md5 还原 `OK`（工作树余 `.tao/tasks/qemu/QEMU-070t-执行语义.md` 未提交改动属他人在途，非本提交、我未触碰）。

**非阻断观察（留 architect）**：① 任务书「可达 FAIL ① 忘改 `check_scope` 计数 ⇒ 红」**不成立**——`check_scope.py:194` 计数为「信息，非判据」且本册未改该文件；工程师以编码注入替代，实交付 3 项可达 FAIL（编码/纯净度/只读锁），未伪造 ⇒ 建议修订该条措辞。② 任务书验收标准 1 写 `262/29/60`、立项来源写 `excluded 28→29`，与现场 `266/4/64` 不符（陈旧数字，非本册改动所致），按裁定口径以现场为准。

**判决：Accepted**（阻断口径逐条核：字段 ✓、语义正文 ✓、编码无冲突 ✓、无非预期红 ✓、未改实现 ✓、purity rc=0 ✓）。
