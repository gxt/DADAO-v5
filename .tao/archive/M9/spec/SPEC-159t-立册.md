# SPEC-159t: `ftmin`/`fomin`/`ftmax`/`fomax` 立册（IEEE 754-2019 `minimumNumber`，OPC-RF）

**模块**：spec
**项目里程碑**：M9（FP 完备性）
**依赖**：无（本册只立记录与语义）；后续 `QEMU-071t` → `LLVM-124t` → `SPEC-160t`（翻转 `excluded → fp`）→ `TESTCASES-059t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 用户裁定（2026-10-21，原话）

> 「1、同意 ftmin/fomin/ftmax/fomax（number 语义）；2、按 IEEE 规定，并参考 RISC-V 实现…」
> 「同意；opx：ftmin/ftmax：100-110/100111；fomin/fomax: 101-110/101-111」

即：**单条 number 语义**（不做 NaN 传播版 `minimum`），语义取 **IEEE 754-2019 §9.6 `minimumNumber`/`maximumNumber`**，与 RISC-V `fmin/fmax` 一致。

### 语义真源（IEEE 754-2019 §9.6 + §6.2）

- `minimumNumber(x,y)`：`x<y` ⇒ x；`y<x` ⇒ y；**一个操作数是数、另一个是 NaN（含 sNaN）⇒ 返回那个数**；**双 NaN ⇒ canonical quiet NaN**（§6.2）；**`−0` 小于 `+0`**；`x==y` 同号 ⇒ 任一。
- **sNaN**：置 **NV**（即使结果为数字）；qNaN 输入**不置**标志。
- 不涉舍入（无舍入、不置 NX）；canonical qNaN = 正号 + payload 全零（与我们 `foqcmp` 的 qNaN 常量同源）。
- **RISC-V 一致性**：`FMIN.S`/`FMAX.S` 原文（−0<+0、双 NaN → canonical、单 NaN → 非 NaN、sNaN 置 NV 即使结果非 NaN）与上述**逐条一致**（已核 RISC-V 规范 F 2.2 注记：v2.2 起由 754-2008 `minNum` 改为 201x `minimumNumber`）。

### 现场事实（2026-10-21 核，执行前须复核）

- FP 族：`op = 0x44`（OPC-RF），`ha` = 6 位 opx；`ft` 组在前、`fo` 组 +8。
- **`0x26`/`0x27`/`0x2E`/`0x2F` 现场均为空** ✓（`0x22`/`0x2A` 归 FMA）。
- `check_fp_contract.py`：12 族、`fp` 计数 60（FMA 链落地后为 13 族 / 62）⇒ 本册仍**不动**族表（记录为 `excluded`）。
- `SimRISC-07 §1.1` 速查条数现场派生（FMA 落地后为 46）；本册 +4。

## 目标

1. 立 4 条记录（`scope: excluded`、`decode: ILLI`）：`ftmin/ftmax/fomin/fomax`，`orrr`；
2. 规范正文写清 `minimumNumber` 的每一条边界（NaN/±0/相等/标志）；
3. 生成物与计数同步；只读锁重算。

## 接口规范

- **输入**：`tools/spec/generate_opcodes.py`、`tools/spec/check_scope.py`、`spec/SimRISC-07`、`.tao/contracts/contract-fp.md`、`manifests/spec-readonly.lock.toml`。
- **输出**：`opcodes.yaml`（+4、total 现场派生：266）、`SimRISC-07 §1.1`（+4）与 §4.x 新节、`contract-fp.md` 新增 `minmax` 段（含 `<a id="minmax">`）、`gen_asm_list --embed-spec`、`gen_legality_list --apply`、`gen_isa_coverage`、`contract-asm-list`、只读锁、证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `components/**`、`tests/**`；不改门控判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 语义表（**必须逐条写进规范**）

- `min(x,y)` / `max(x,y)` 的四种组合：有序、相等（含 `±0`）、单 NaN（q/s）、双 NaN；
- `−0 < +0`：`min(+0,−0)=−0`、`max(+0,−0)=+0`；
- sNaN ⇒ NV + 返回数字；双 NaN ⇒ canonical qNaN（正号、payload 0）；
- **不得**实现成"返回第二操作数"（x86 遗留语义）或"任一"（`minNum` 的宽松处）。

### B. 合法性

- 目的 `rf0` ⇒ ILLI（`dst_rf0`）；源可为 `rf0`（读出 FCSR 的 qNaN 位）；
- 不引入 `dst_dual_same`（`orrr` 单目的）。

### C. 编码与生成物

```
ftmin rfHB, rfHC, rfHD   @ op=0x44, ha=0x26 (100-110)
ftmax rfHB, rfHC, rfHD   @ op=0x44, ha=0x27 (100-111)
fomin rfHB, rfHC, rfHD   @ op=0x44, ha=0x2E (101-110)
fomax rfHB, rfHC, rfHD   @ op=0x44, ha=0x2F (101-111)
```

- `simplify` 无（`orrr` 3 寄存器，`hb`=目的）；
- `check_scope.py`：`excluded +4`、`total +4`（`fp` 不变）+ changelog 一行；
- `SimRISC-07` 变更记录追加 1 行；只读锁重算。

## 验收标准

1. `opcodes.yaml`：+4 条（`excluded` +4、`total` 现场派生）；4 条的 `op/ha/format/legality` 与上表一致。
2. `check_scope` / `validate-encoding` / `check-rule-refs` / `check-instrinfo`（`excluded` 无 `.td` 合规）/ `check-isa-coverage` / `check_fp_contract`（族与 `fp` 计数**不变**）全绿。
3. `check-asm-list*` / `check-spec-*` / `check-spec-readonly` 全绿。
4. `make check`（L1）rc=0。**L2 不在本册验收面**：`check_qemu_trans` 因新增记录缺 trans 会红（登记 issue，由 `QEMU-071t` 关闭）。
5. **可达 FAIL ≥ 2**：① 忘改 `check_scope` 计数 ⇒ 红；② 不重算只读锁 ⇒ 红。
6. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（opx 空闲、`rec()` 形态、速查表、`contract-fp.md` 锚点风格）。
2. 生成器加 4 条（`excluded`）+ 计数 + `check_scope`。
3. 写 `SimRISC-07 §4.x` 与 `contract-fp.md §minmax`。
4. 重生成 + 门控 + 只读锁 + 变更记录。
5. 反例注入 + L1 + 完成区 + 登记 issue。

## 可达 FAIL（**≥2**）

- `check_scope` 计数漏改 ⇒ 红；还原 ⇒ 绿。
- 只读锁不重算 ⇒ `check-spec-readonly` 红；重算 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不做 `minimum`/`maximum`（NaN 传播）硬件版；由 LLVM 从本条展开（`LLVM-124t`）。
- 不做 `*mag`（`minNumMag` 类）；不做整数 min/max。
- 不实现（`QEMU-071t`）、不接后端（`LLVM-124t`）、不翻转（`SPEC-160t`）。

## 完成区

**测试结果**：一键证据 `bash .work/evidence/SPEC-159t/run.sh --inject` = **146/146 PASS（rc=0）**，含 L1 `make check` rc=0（末轮现场）。注入 2 例均「注入→红→`cp`+md5 还原→回绿」：① `check_scope` 计数回退 31/264→27/260 ⇒ rc=1（命中 excluded/total 两断言）；② 只读锁 SimRISC-07 sha256 回退上一版 ⇒ `check-spec-readonly` rc=1（MISMATCH spec/SimRISC-07）。日志 `.work/evidence/SPEC-159t/log/`。
**修改文件**：`contracts/opcodes.yaml`（260→264）；`spec/SimRISC-07-浮点运算.md`（册头/§1.1/§2 合法性/§4.4/附录）；`spec/SimRISC-00-指令系统设计.md`（§4.6 四格+注记、附录）**越界（披露见坑④）**；`.tao/contracts/contract-fp.md`（§19 `minmax` + `<a id="minmax">` + 首段）；生成物 `.tao/contracts/contract-asm-list.md`、`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`、`tests/llvm/lit/MC/DADAO-gen/gen-excluded.s`；生成器/门控 `tools/spec/{generate_opcodes,check_scope}.py`、`tools/testcases/generate_lit_vectors.py`；`manifests/spec-readonly.lock.toml`（SimRISC-00/07 两册 sha）；`.tao/knowledge/{issues.yaml,milestones.md}`；本任务书；`.work/evidence/SPEC-159t/run.sh`。
**验收结果**：现场 `total=264 / excluded=31 / fp=60 / m1=156 / m3=1 / m8=7 / m9=9`；四条 `op=0x44`、`ha=0x26/0x27/0x2E/0x2F`、`orrr`、`value=0x44980000/0x449C0000/0x44B80000/0x44BC0000`、`legality=['rfhb != rf0']`、`scope=excluded`、`decode=ILLI`、`rule_refs=[]`；其余 260 条**逐字段不变**（证据 A2）。`check_scope`（excluded 31/total 264）PASS；`validate-encoding` 264 条 OK；`check_rule_refs`/`check_instrinfo`/`check_isa_coverage --check`（accept 258/reject 6）/`check_fp_contract`（60 条/13 族/`dst_rf0`=35 全不变）/`check_lit_gen`（258+ / 6−，64/64）/`check-asm-list{,-drift}`/`check-legality-{drift,invariants}`/`check-spec-{refs,drift,codeblocks,numbering,changelog,archive,readonly}`/`check_contracts_pending`/`check_milestones_fresh`/`check_issues` 全 rc=0；L1 rc=0。**预期红（L2 非验收面）**：`check_qemu_trans --strict` 260/264（缺本 4 条 trans，`ISS-324`）。
**新发现/坑**：① 任务书「total 现场派生：266」与现场不符——`SPEC-157t`（FMA 4 条）**未落** ⇒ 基线 260，本册 **260→264**（按现场派生，不按 266 凑数）。② 「不改 `tests/**`」与「生成物 lit-gen」冲突：按**生成物**处理（`gen-excluded.s` 机械派生、无语义向量），并给 `generate_lit_vectors._negative_text` 补 rf-orrr 反例形态——否则会生成 `ftmin rd9, [rb1, 0]` 错形反例，llvm-mc 因**语法错**而拒绝 ⇒ 反例「假绿」。③ `check_tables.py` 只覆盖 4 张 MISC 子表、**不覆盖 OPC-RF** ⇒ SimRISC-00 §4.6 格位无机械门控（本册靠证据 C3 断言 100/101 行 110/111 四格；已登记 `ISS-325`）。④ SimRISC-00 §4.6 **不在**任务书文件清单内，但它是编码唯一真源（空格=reserved/UNDI，与新增 ILLI 记录矛盾）⇒ 按 `SPEC-161t` 先例补四格+注记+附录+锁 sha（越界已在此披露）。
**遗留问题**：① QEMU 缺 4 条 trans（`ISS-324`，`resolved_by: null`，由 `QEMU-071t` 关闭）；② `.td`/ISel 归 `LLVM-124t`；③ `excluded → fp` 翻转 + 新族 `minmax`（4 条）归 `SPEC-160t`；④ `check_tables` 未覆盖 OPC-RF（`ISS-325`，P3）。无其它未完成项。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

**审查面**：`generate_opcodes.py`（4 条记录/`S07_MINMAX`/docstring）、`check_scope.py`（计数+changelog）、`SimRISC-07 §2.4`（6 条边界语义）、`contract-fp.md §19`、`SimRISC-00 §4.6` 四格与注记、`generate_lit_vectors.py` 反例分支、重生成产物、只读锁、证据脚本断言（逐条可失败性）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 反例生成器对 rf-orrr 走 lr/sc 形态（`ftmin rd9, [rb1, 0]`）⇒ 语法错导致「假绿」 | ✅已修 | `_negative_text` 增 `ft*/fo*` 分支 → `ftmin rf8, rf9, rf10` | `gen-excluded.s` 4 条为正确形态；`check_lit_gen` 反例 6 条全命中（证据 D/H） |
| F2 `spec_cite` 写作 `（minimumNumber/maximumNumber）`，与章节标题（含空格）不一致 | ✅已修 | `S07_MINMAX` 对齐为 `（minimumNumber / maximumNumber）`；重生成 opcodes/lit/矩阵 | 证据 A 四条 `spec_cite` 逐字相等 |
| F3 §4.4 正文重复声明 `op/ha`，与 SimRISC-00 编码表构成**双真源** | ✅已修 | 删除「编码：…」段，编码只留 SimRISC-00 §4.6 表 | `check_spec_codeblocks` PASS；证据 C 断言不再依赖该段 |
| F4 SimRISC-00 §4.6 仍把 4 格读作 reserved/UNDI，与「编码已定义、ILLI」矛盾 | ✅已修（越界披露 ④） | 填 4 格 + 表下注记（50=46fp+4excluded）+ 附录 1 行 + 锁 sha | 证据 C3（列 110/111 逐格比对）+ `check_spec_readonly` 21/21 |
| F5 证据脚本「合法性区 excluded 4 条」匹配串写成 `orr_rf`（实际 id 为 `orrr_rf`）⇒ 断言恒 0 | ✅已修 | 改为 `` `(ftmin\|ftmax\|fomin\|fomax)_orrr_rf`：decode ILLI `` | 修前实测 FAIL(actual=0) → 修后 PASS(actual=4)（可失败性已现场证明） |
| F6 证据 C3 行匹配 `\| 100-xxx \|` 不容忍多空格 ⇒ missing-row | ✅已修 | 改正则 `^\|\s*1(00\|01)-xxx\s*\|` | 修前 FAIL(missing-row) → 修后 PASS(OK) |
| F7 rf-orrr 分支是否会误伤 `lr.*`/`sc.*` 反例 | ❌不修（附证据） | — | `lr`/`sc` 助记符不以 `ft`/`fo` 开头；`gen-excluded.s` 中 `cfxld/cfxst` 形态不变，lr/sc 非反例（有 `.td`）⇒ 无交集 |
| F8 canonical qNaN 常量与 `rf0` 复位值是否同源 | ❌不修（附证据） | — | `rf0` 复位 = `0x7FF8_0000_7FC0_0000`（高 32 位 fo qNaN / 低 32 位 ft qNaN），与 §4.4 的 `0x7FF8_0000_0000_0000`/`0x7FC0_0000` 一致（ADR-0004 §D2） |

**判决**：全部 finding 已修或已附证据不修；状态置 `待验收`，返回主会话由 `reviewer` 独立验收。

### 第 1 轮 reviewer 验收（2026-10-22，独立重跑，非采信 engineer 叙述）

**重跑记录**（workdir=仓库根，全部本人执行；单步均 ≤39 s）：
- 记录核验：自解析 `opcodes.yaml`——4 条 `op=0x44`、`ha=0x26/0x27/0x2E/0x2F`、`orrr`、`excluded`、`ILLI`、`legality=['rfhb != rf0']`、`value=0x44980000/0x449C0000/0x44B80000/0x44BC0000` 与任务书表逐条一致；`op=0x44` 族现场 50 条、ha 唯一；total=264 / m1=156 / fp=60 / excluded=31 / m3=1 / m8=7 / m9=9。
- 门控（各 rc=0）：`check_scope`（excluded 期望=31 实际=31、total 264）/`validate-encoding`（264 条 OK）/`check-rule-refs`（规则 16、引用 337 处）/`check-instrinfo`（0 errors，4 条 excluded 无 .td 合规）/`check-fp-contract`（id 60、13 族、`dst_rf0`=35、「FP 专属规则未被非 fp 引用」=0）/`check-isa-coverage`（accept 258/reject 6）/`check-spec-{refs,drift,numbering,changelog,archive,readonly}`（readonly 21/21）/`check-asm-list`（12 files OK）`-drift`（byte-identical）/`check_lit_gen`（64/64）/`make check-lit`（132/132）。
- **L1**：`make check` rc=0（38.7 s，`repository checks (L1): PASS`）。
- **预期红属实**：`python3 tools/qemu/check_qemu_trans.py --strict` rc=1，`260/264`，MISSING 恰为本 4 条 ⇒ `ISS-324` open、`resolved_by: null`，不阻断。
- **生成物幂等**（5 项全跑、各 ≤3 s）：`generate_opcodes`/`gen_asm_list -o`+`--embed-spec`/`gen_legality_list --apply`/`generate_lit_vectors`/`gen_isa_coverage` 全 rc=0，跑后 `git status` 无 diff、关键产物 md5 与跑前一致。
- **独立注入 1 次**：`check_scope.py` `EXPECTED_EXCLUDED 31→27`（注入前 `cp` 备份、md5=1ac28fc1…）⇒ `check-scope: FAIL — excluded 计数: 期望 27，实际 31` rc=1；`cp` 还原、md5 相等、重跑 rc=0 回绿。禁用 git 还原，终态 `git status --porcelain -uall` 干净。

**约束核验**：① 语义面——SimRISC-07 §2.4 六边界 + `contract-fp.md §19` 与 754-2019 §9.6/§6.2 逐条一致（单 NaN 含 sNaN ⇒ 数字、sNaN 置 NV、双 NaN ⇒ canonical qNaN（ft `0x7FC0_0000`/fo `0x7FF8_0000_0000_0000`）、`−0<+0`、等值同号任一、不置 NX），并明文禁 x86「返回第二操作数」与 2008 `minNum` 宽松口径 ✓；② 越界——SimRISC-00 §4.6 四格+注记+附录为编码真源必需（对照 SPEC-161t 先例），锁 sha256 自对 MATCH（00=a89039b8…、07=6e5421f9…）✓；③ `ISS-325` 描述与现场一致（`check_tables.OP_TABLE` 仅 `0x40–0x43`，无 `0x44` OPC-RF）✓；④ 「修改文件」15 文件与 `git show --stat` 逐一对账一致、完成区 ≤30 行、验收前/后快照均干净 ✓。注：「`rule_refs` 含 `dst_rf0`」不能字面成立——31 条 excluded 的 `rule_refs` 均空、`check_fp_contract` 禁非 fp 引用 FP 规则；`dst_rf0` 由 legality `rfhb != rf0` 映射（`generate_opcodes.py:843`），实质满足。证据脚本按用户裁定未整份重跑，抽查断言（计数/预期红/I1 注入）均具可达 FAIL 且与本人重跑输出一致。

**判决：Accepted**（验收命令在本人重跑下全绿、预期红属实、注入→FAIL→还原→回绿真实、无未披露越界）。
