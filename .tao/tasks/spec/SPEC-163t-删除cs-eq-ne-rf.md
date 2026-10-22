# SPEC-163t: 删除 `cs.eq_rrrr_rf`/`cs.ne_rrrr_rf`（原子删除册：spec + LLVM + QEMU + tests）

**模块**：spec（**跨模块原子删除**：`spec` + `llvm` + `qemu` + `testcases` 同一提交）
**项目里程碑**：M9（ISA 精简）
**依赖**：无；**必须早于 `SPEC-157t`（FMA 立册）** —— FMA 将占用腾出的 `0x5E`/`0x5F`。
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 用户裁定（2026-10-22，原话）

> 「删除cs.eq/ne-rrrr-rf，两条指令；然后把ftfma/fofma的编码移动到这两条指令的位置」

### 删除依据（能力面）

- 这两条的语义 = **条件复制**（`if (rdHA == rdHB) rfHB = rfHC else rfHB = rfHD`），能力仅为 `select`；
- **无独特表达力**：等价写法 = `sub rd, a, b` + `cs.z`（2 条）；"判 `qcmp` 结果 == 1"还需先把常量 1 物化（同为 2 条）⇒ **不省指令**；
- 后端 `LowerCmpSelect` 只发射 `CS_N`/`CS_Z`/`CS_P`，**从不生成**这两条（`DADAOISD` 里也没有对应的 CS 节点）；
- ⇒ 死指令 + 占用 `0x5E`/`0x5F`；删掉后该两格交给 FMA（`ftfma`/`fofma`）。

### 现场事实（2026-10-22 核，执行前须复核）

- 记录：`cs.eq_rrrr_rf`（`op=0x5E`）、`cs.ne_rrrr_rf`（`op=0x5F`），`format = rrrr`、**`scope: fp`**、`rule_refs: [dst_rf0]`。
- **计数耦合（写死断言）**：
  - `check_scope.py`：`fp 60 → 58`、`total 260 → 258`（+ changelog 一行）
  - `check_fp_contract.py`：`EXPECTED_TOTAL 60 → 58`；`FAMILY_COUNTS["cs_rf"] 5 → 3`；`dst_rf0` 的 FP 引用条数 `35 → 33`
  - `fp_semantics.yaml`：删 2 条（`family: cs_rf`）
- **原子性硬约束**：`check_instrinfo`（`fp` 记录必须有 `.td` def）与 `check_qemu_trans`（每条记录必须有 `trans_*`）双向校验 ⇒ **records / `.td` / `trans` / lit 必须同一提交**，否则中间态必红。
- 其他触点（现场核）：`DADAOInstrInfoFP.td` 的 `cs_eq_rrrr_rf`/`cs_ne_rrrr_rf`；QEMU `trans_fp.c.inc.patch` 的 2 条 `trans_*`；lit `tests/llvm/lit/MC/DADAO-gen/gen-rrrr.s`、`tests/llvm/lit/MC/DADAO/{fp-encoding.s,fp-legality.s}`；`tests/vectors/isa/reserved.yaml`；`SimRISC-02 §1.1` 2 行 + `§3.3` 正文（含"用 `cs.eq` 判 ==1"的说明）；`contract-fp.md`（若提及）；`contract-isa.md`（**计数类，按用户裁定留到 M9 收尾**，本册只改行为描述）。

## 目标

1. 彻底删除 `cs.eq_rrrr_rf`/`cs.ne_rrrr_rf`（记录 / `.td` / QEMU trans / lit / 向量）；
2. 计数与族表同步（现场派生，不写死猜测）；
3. 规范正文改写：§3.3 删掉"用 `cs.eq` 判 ==1"的指引，改为 `sub`+`cs.z`（或说明仅 `cs.n/z/p` 用于 FP 条件复制）；
4. `0x5E`/`0x5F` 变为**空**（供 `SPEC-157t` 的 FMA 使用），不得在本册占位。

## 接口规范

- **输入**：`contracts/opcodes.yaml`、`tools/spec/{generate_opcodes,check_scope}.py`、`tools/spec/check_fp_contract.py`、`contracts/fp_semantics.yaml`、`spec/SimRISC-02`、`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfoFP.td.patch`、`components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch`、`tests/llvm/lit/**`、`tests/vectors/**`、`manifests/spec-readonly.lock.toml`。
- **输出**：删除后的 `opcodes.yaml`（`fp 58`/`total 258`）、`fp_semantics.yaml`（删 2 条）、`check_scope` 计数与 changelog、`check_fp_contract` 计数、`.td` 删除、QEMU trans 删除、lit/向量重生成、`SimRISC-02` 正文与变更记录、只读锁重算、证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：**不得**顺手删 `cs.eq/ne_rrrr_rd`（`0x66/0x67`，用户只定删 rf 两条）；不改门控判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 删除面（逐项，缺一即红）

1. `generate_opcodes.py`：删两条 `rec(...)` + 文件头计数说明；
2. `opcodes.yaml` 重生成（260→258）；
3. `check_scope.py`：`fp 60→58`、`total 260→258` + changelog；
4. `check_fp_contract.py`：`EXPECTED_TOTAL`、`cs_rf`、`dst_rf0` 引用数；
5. `fp_semantics.yaml` 重生成（−2）；
6. `DADAOInstrInfoFP.td.patch`：删 2 def；
7. QEMU `trans_fp.c.inc.patch`：删 2 个 `trans_*`（并清理其 check 调用点）；
8. lit：`gen-rrrr.s`（生成物重生成）、`fp-encoding.s`/`fp-legality.s` 中的对应用例删除；
9. `tests/vectors/isa/reserved.yaml`（若引用）；
10. `SimRISC-02 §1.1` 2 行 + `§3.3` 指引改写 + 变更记录 1 行（标注**破坏性**）；
11. 只读锁 `sha256` 重算。

### B. 不改的边界

- 保留 `cs.n/z/p_rrrr_rf`（FP 条件复制主力）与 `cs.eq/ne_rrrr_rd`；
- `contract-isa.md` 的计数按用户裁定**留到 M9 收尾**，本册只改行为描述（若提及这两条则删句）。

## 验收标准

1. `opcodes.yaml` = **258** 条；`fp` = **58**；两条记录消失（`grep` 零命中）。
2. `check_scope` / `check_fp_contract`（`cs_rf=3`、`dst_rf0` 33）/ `validate-encoding` / `check-rule-refs` / `check-instrinfo`（0 errors）/ `check_isa_coverage` / `check_qemu_trans --strict`（**258/258**）全绿。
3. `check-spec-*` / `check-asm-list*` / `check_lit_gen` 全绿；`0x5E`/`0x5F` 在 `opcodes.yaml` 中**无记录**（留空）。
4. `make check`（L1）rc=0；`make check-modules`（L2）rc=0。
5. **可达 FAIL ≥2**：① 只删记录不删 `.td` ⇒ `check-instrinfo` 红；② 不删 QEMU trans ⇒ `check_qemu_trans` 258/258 红（或残留 trans 报错）。
6. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（记录/`.td`/trans/lit/计数/锁）。
2. 生成器删两条 → 重生成 → `.td`/trans/lit 同步删 → 计数。
3. `SimRISC-02` 正文 + 变更记录 + 只读锁。
4. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2**）

- 临时保留 `.td` def（不删）⇒ `check-instrinfo` 报 orphan / 覆盖率不符 ⇒ 红；补删 ⇒ 绿。
- 临时保留一条 QEMU `trans_*` ⇒ `check_qemu_trans` 计数/残留检查红；删 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不删 `cs.eq/ne_rrrr_rd`；不动 `cs.n/z/p`。
- `contract-isa.md` 计数留 M9 收尾。
- FMA 的 `0x5E`/`0x5F` 编码在 `SPEC-157t` 落地，本册只腾格。

## 完成区

**测试结果**：L1 `make check` rc=0；L2 `make check-modules` rc=0；`bash .work/evidence/SPEC-163t/run.sh --inject` PASS=55 FAIL=0（rc=0）。
**修改文件**：`contracts/{opcodes,fp_semantics}.yaml`；`tools/spec/{generate_opcodes,check_scope,check_fp_contract}.py`；`tools/llvm/{gen_asm_list.py,llvm-isa-backend-matrix.{tsv,md}}`（矩阵重生成）；`tools/qemu/check_005t_coverage.py`；`components/llvm-project/.../DADAOInstrInfoFP.td.patch`；`components/qemu/.../{insn.decode,insn_trans/trans_fp.c.inc}.patch`；`tests/llvm/lit/MC/DADAO-gen/gen-rrrr.s`、`tests/llvm/lit/MC/DADAO/{fp-encoding,fp-legality}.s`；`tests/vectors/isa/reserved.yaml`；`.tao/contracts/{contract-asm-list,contract-fp,contract-isa}.md`；`spec/SimRISC-02`；`manifests/spec-readonly.lock.toml`；本任务书 + `milestones.md` 一行；`.work/evidence/SPEC-163t/`。
**验收结果**：opcodes **258** 条 / fp **58**；`0x5E`/`0x5F` 无记录。`check_scope` fp=58/total=258 PASS；`check_fp_contract` id=58、cs_rf=**3**、dst_rf0=**33** PASS；`check_qemu_trans` **258/258**（M1 156/156）；`check_instrinfo` 0 errors；`check_interface` QEMU trans_*=258；`validate-encoding`/`check-rule-refs`/`check_isa_coverage`/`check-spec-*`/`check-asm-list*`/`check_lit_gen` 全 rc=0。可达 FAIL：E1 `.td` def 残留→显式文本断言 rc=1；E2 lit 残留→`check_lit_gen` rc=1；E3 QEMU trans 残留→`check_interface` rc=1（259≠258）；均 `cp`+md5 还原回绿（md5 逐项一致）。
**新发现/坑**：★ `check-instrinfo` **不覆盖 FP `.td`**：`tools/llvm/validate_instrinfo.py` 只解析 `DADAOInstrInfo.td.patch`，FP def 在 `DADAOInstrInfoFP.td.patch`；实测保留 `def cs_eq_rrrr_rf` 后 `check-instrinfo` 仍 rc=0（`gen_isa_coverage --check` 亦 rc=0）⇒ 任务书「records/.td 双向校验」前提不成立，`.td` 原子性无门控，本册用证据脚本 `td_def_absent` 文本断言兜底。② `make apply-series` 对 patchless 组件（chipyard）报 `KeyError: 'patch_dir'`（rc=2；llvm/qemu 已先应用+提交，可继续），属预存缺陷。
**遗留问题**：① SimRISC-00 QFC 主表格位与 SimRISC-07 FP 总账仍列两条旧指令（本册按任务书只改 SimRISC-02；SPEC-157t 落 FMA 同一格时一并同步；`check_qfc_coverage` 为 informational 不阻断）；② `contract-isa.md` 计数按用户裁定留 M9 收尾（本册只改行为/编码行）；③ 建议另立任务把 FP `.td` 纳入 `validate_instrinfo`，消除上述门控盲点。

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

### 第 1 轮 engineer 自审（2026-10-22）

逐行核对：生成器→opcodes/fp_semantics→`.td`/trans/decode→lit/向量→spec/合约→锁；真实输出见 `.work/evidence/SPEC-163t/log/`。

- 逻辑：删除仅 2 条 `scope: fp` 记录（`0x5E/0x5F`），`cs.eq/ne_rrrr_rd`（`0x66/0x67`）与 `cs.n/z/p_rrrr_rf` 保留；`fp_semantics` 族计数 `cs_rf 5→3`、`dst_rf0 35→33` 与 `check_fp_contract` 写死值一致；`.td` 注释同步 60→58、rrrr 5→3；QEMU `insn.decode` 由生成器重导出（260→258 patterns）。
- 防造假：`check-index-blobs` 对 3 份 new-file 补丁重算 index；`apply-series` 重放成功（llvm HEAD `4e7f250f3` / qemu `7bab658`）；注入全程 `cp`+md5，逐项一致。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务书称 `check-instrinfo` 覆盖 FP `.td`，实测不覆盖（只解析 `DADAOInstrInfo.td.patch`） | ❌不修（属门控语义扩展，任务边界外；已登记遗留③） | 无 | 注入 `def cs_eq_rrrr_rf` 后 `validate_instrinfo` rc=0、`gen_isa_coverage --check` rc=0 |
| F2 可达 FAIL ① 无法按指定门控成立 | ✅已修（改用显式 `td_def_absent` 文本断言 + lit/QEMU 两个真门控） | 证据脚本 E1 | E1 inject rc=1 → 还原 → rc=0（md5 一致） |
| F3 `check_qemu_trans` 只查缺失、不查多余 trans | ✅已修（多余 trans 由 `check_interface`「QEMU trans_* 定义数」判出） | 证据脚本 E3 | 注入后 `check_interface` rc=1（259≠258）→ 还原 rc=0 |
| F4 `fp-encoding.s` 头注仍写 “all 60 instructions” | ✅已修 | 改为 58 | `make check-lit` 130/130 rc=0 |
| F5 `contract-isa.md` 计数（60/5 等）仍为旧值 | ⏸延后（用户裁定留 M9 收尾；本册只改编码/行为行） | 删 0x5E/0x5F 两行、QFC 两格置 `—` | `make check` rc=0（无计数门控） |
| F6 SimRISC-00 QFC 格位 / SimRISC-07 总账仍列旧指令 | ⏸延后（任务书只列 SimRISC-02；SPEC-157t FMA 占同格时同步） | 无 | `check_qfc_coverage` informational；L1 rc=0 |
| F7 `make apply-series` 对 patchless 组件（chipyard）`KeyError: 'patch_dir'` | ⏸延后（预存缺陷，与本册无关） | 无 | 失败现场 `/tmp/opencode/SPEC-163t/apply-series.log`；llvm/qemu 已先应用，续跑成功 |

### 第 1 轮 reviewer 验收（2026-10-22，全部自跑、不信完成区）

**重跑记录（真实输出/退出码）**
- 记录面：`opcodes.yaml` 自解析 = **258** 条 / `fp` **58**；`cs.eq_rrrr_rf`/`cs.ne_rrrr_rf` grep 零命中；`0x5E`/`0x5F` 无记录；保留项 `cs.n/z/p_rrrr_rf` 与 `cs.eq/ne_rrrr_rd`（0x66/0x67）在位。`check_scope` rc=0（fp=58/total=258）；`check_fp_contract` rc=0（id=58、**cs_rf=3**、**dst_rf0=33**）；`validate_encoding`「258 条记录 OK」rc=0；`check_rule_refs` PASS rc=0；`check_instrinfo`「0 errors」rc=0；`check_qemu_trans --strict`「258/258（M1 156/156）」rc=0；`check_interface` 83 项全 PASS rc=0；`gen_isa_coverage --check` PASS rc=0；`check_lit_gen` 64/64 rc=0。
- 原子性零残留：`.td`/`insn.decode.patch`/`trans_fp.c.inc.patch`/lit（gen-rrrr / fp-encoding / fp-legality）grep `cs_(eq|ne)_rrrr_rf` 均 0 命中；`SimRISC-02` §1.1 = 16 条、`dst_rf0` 3 条、§3.3 指引已改 `sub`+`cs.z`、附录**追加**且标「破坏性」；只读锁 **21 册 sha256 自算全一致**（SimRISC-02 = 3a58a931…）。
- L1 `make check` rc=0（check-patch-tree 1008 files/0 illegal；llc/clang/qemu 3/3）；L2 rc=0：reviewer 上一轮的 L2 输出随会话丢失，由**主会话补跑** `make check-modules`（`/tmp/opencode/SPEC-163t/L2-own.log`，md5 ed0aee1a…，尾行 `module checks (L2): PASS`，lit 130/130、picolibc pass=18 fail=0）。
- 证据脚本 `run.sh --inject` 重跑：**PASS=55 FAIL=0 rc=0**。脚本合格：无 `| tee` 吞码（`gate`/`expect_fail` 均取被检命令自身 rc）；D 段回读的是**当次**日志（每次 `>` 覆盖，非陈旧）；E1/E2/E3 均真注入 + `cp`+md5 还原逐项一致。E1 为文本断言（非真门控）已在完成区披露，见下。
- **reviewer 独立注入**（`cp`+md5，禁 checkout）：① `DADAOInstrInfoFP.td.patch` 加回 `def cs_eq_rrrr_rf`（含 hunk 计数 493→500）⇒ `check-instrinfo` **仍 rc=0**（0 errors）、`gen_isa_coverage --check` **仍 rc=0**；还原 md5 `66dcca0e…` 一致。② `trans_fp.c.inc.patch` 残留一条 `trans_cs_eq_rrrr_rf`（hunk 976→991）⇒ `check_interface` **rc=1**（期望 258 实际 259），`check_qemu_trans --strict` **仍 rc=0**（只查缺失方向）；还原 md5 `d10dc294…` 一致，两门控回绿。

**约束核验**：不 commit/push ✓（验收前后 `git status --porcelain -uall` 快照逐行对账一致，全程干净）；未落 `.EXIT` 到 `.work/log` ✓；未顺手删 `cs.eq/ne_rrrr_rd` ✓；**未改门控判定语义** ✓（`check_scope`/`check_fp_contract`/`gen_asm_list`/`check_005t_coverage` 的改动仅为计数 60→58 / 260→258 / 5→3 / 35→33 + 生成器注释）；生成器↔记录一致 ✓（重跑 `generate_opcodes.py` 输出与 `contracts/opcodes.yaml` 字节相同，`git status` 干净）。

**判决：Accepted** —— 验收标准 1–7 在 reviewer 自己的重跑下全部通过；完成区与真实输出逐条对齐，无夸大、无凑绿。

**门控缺口（两处，均不阻断本册，建议登记 issue 由架构师定夺）**：
- ① **FP `.td` 原子性无门控**：`tools/llvm/validate_instrinfo.py` 默认只解析 `DADAOInstrInfo.td.patch`（L58），`gen_isa_coverage --check` 亦仅做 record→def 单向映射（reviewer 注入实证两门控均 rc=0）。任务书「records/.td 双向校验」前提不成立；engineer 未擅改门控语义、改用 `td_def_absent` 文本断言兜底并醒目披露（F1/遗留③），处理正确而非规避。建议另立任务把 `DADAOInstrInfoFP.td.patch`（含 orphan 方向）纳入 `validate_instrinfo`。
- ② **`check_qemu_trans --strict` 只查缺失方向**：仅校验 YAML 记录→trans 存在，**残留多余 `trans_*` 不报**（reviewer 注入实证 `--strict` 仍 rc=0，而 `check_interface` rc=1 抓到 259≠258）。建议该门控补 orphan 方向，或维持现状并以 `check_interface` 为兜底（须知会后续任务）。

**遗留（披露，非本册范围）**：`SimRISC-00 §QFC`（0101-1xxx 末两格仍写 `cs.eq/ne_rrrr_rf`）与 `SimRISC-07` 册头（「fp 共 60 条」「寄存器复制 7 条」）未同步；`check_qfc_coverage` informational rc=0（QFC 260 vs YAML 258，2 条 M1 内差异）。两册属只读锁文件，须用户授权原话方可改；建议随 SPEC-157t（FMA 占 0x5E/0x5F）一并同步，否则规范主表与合约长期矛盾。

**过程披露**：reviewer 核验时误把 `python3 tools/spec/generate_opcodes.py --help` 当帮助调用（该脚本无 argparse，直接执行并重写 `contracts/opcodes.yaml`）；产出与 HEAD 字节相同（`git status`/`git diff` 均干净），无实质影响，已如实记录。
