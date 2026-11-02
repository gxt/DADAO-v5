# SPEC-161t: `ftrnd`/`fornd` 立册（754-2019 六种取整，one-hot `immu6`，OPC-RF）

**模块**：spec
**项目里程碑**：M9（FP 完备性）
**依赖**：无（本册只立记录与语义）；后续 `QEMU-072t` → `LLVM-125t` → `SPEC-162t`（翻转）→ `TESTCASES-060t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 用户裁定（2026-10-21，原话）

> 「不增加 nearbyint，只实现 754-2019 中的六种取整，按顺序，immu6 用 one-hot 对应上」
> 「ftrnd/fornd 的 opx：000-011/001-011」

补充裁定（同批问答）：**`rf0[33:32]` 不扩充**（不加入第 5 种模式 RMM/`roundTiesToAway`）——用户 2026-10-21 原话「不扩充 round mode」；后果：C23 `fesetround(FE_TONEARESTFROMZERO)` **不支持**（允许返回失败，符合 C 标准），登记为已知边界；RMM 仅由本册 `immu6=0x02` 在"取整到整数"场景提供。另：`nearbyint` 落 **DYN** 档（会置 NX），**登记为已知偏差**（SimRISC 的 NX 只是 `rf0[4:0]` 状态位、不产生异常，值与 IEEE 一致）。

### 语义真源（IEEE 754-2019 §5.3.1 + §5.9）

六种操作，**顺序固定**（one-hot 位序与之对应）：

| immu6 | 754 操作 | 方向 | NX |
|---|---|---|---|
| `0x01` | `roundToIntegralTiesToEven` | 就近取偶（静态） | 不置 |
| `0x02` | `roundToIntegralTiesToAway` | 就近远离 0（静态） | 不置 |
| `0x04` | `roundToIntegralTowardZero` | 向 0 | 不置 |
| `0x08` | `roundToIntegralTowardPositive` | 向 +∞ | 不置 |
| `0x10` | `roundToIntegralTowardNegative` | 向 −∞ | 不置 |
| `0x20` | `roundToIntegralExact` | **读 `rf0[33:32]`** | **置**（结果≠输入） |

共同规则（§5.9）：

- **sNaN ⇒ 置 NV**、返回 qNaN；qNaN ⇒ 原样（canonical 化）
- **`|x| ≥ 2^p`（fo: 53, ft: 24）⇒ 原样返回**（已整数；**禁止**用"转整数再转回"实现）
- **`±0` 符号保留**（`trunc(-0.5) = -0`、`floor(-0.0) = -0`）
- **Inf 原样**；不置 OF/UF
- 5 个静态方向**不受** `rf0` 影响；只有 `0x20` 读 `rf0[33:32]`

### 现场事实（2026-10-21 核，执行前须复核）

- `rf0[33:32]` 仅 4 档：`00 RNE / 01 RTZ / 10 RDN / 11 RUP` —— **没有 RMM** ⇒ `round`（远离 0）**无法**用 `rf0` 表达，必须编码静态方向（本册因此需要 `0x02`）。
- FP 族：`op=0x44`（OPC-RF），`ha`=opx；`ft` 组在前、`fo` 组 +8；**`0x03`/`0x0B` 现场为空** ✓。
- `encode_onehot` 规则已存在（`rev.o_orri_rd`）：**immu6 非 one-hot ⇒ ILLI** ⇒ 6 位内恰好只有 6 个 one-hot 值，与本节 6 种操作**一一对应**，**无需新增合法性规则** ✓。
- `check_fp_contract.py`：12 族 / `fp` 60（FMA、minmax 链落地后为 14 族 / 66）⇒ 本册记录为 `excluded`，**不动族表**。

## 目标

1. 立 `ftrnd`/`fornd` 两条（`scope: excluded`、`decode: ILLI`），`orri`，`immu6` one-hot 6 值；
2. 规范写清 6 种操作的**逐条边界**（含 NX 只对 `0x20`、`±0` 符号、大值原样、sNaN）；
3. 生成物/计数/只读锁同步；记录 `nearbyint` 偏差。

## 接口规范

- **输入**：`tools/spec/generate_opcodes.py`、`tools/spec/check_scope.py`、`spec/SimRISC-07`、`.tao/contracts/contract-fp.md`、`manifests/spec-readonly.lock.toml`。
- **输出**：`opcodes.yaml`（+2）、`SimRISC-07 §1.1`（+2）与 §4.x 新节（含 immu6 表）、`contract-fp.md` 新增 `roundint` 段（含 `<a id="roundint">`）、生成物重跑、只读锁、证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `components/**`、`tests/**`；不改门控判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**）

### A. 语义落地要点

```
ftrnd rfHB, rfHC, immu6     @ op=0x44, ha=0x03 (000-011)
fornd rfHB, rfHC, immu6     @ op=0x44, ha=0x0B (001-011)
```

- 目的 `rf0` ⇒ ILLI（`dst_rf0`）；源可为 `rf0`；
- **`0x20` 的 NX 语义**：结果 ≠ 输入时置 NX；其它 5 档**不得**置 NX（即使结果不精确）；
- **禁止**把 `0x20` 实现成"固定 RNE"：必须读 `rf0[33:32]`（`RNE/RTZ/RDN/RUP` 四档）。

### B. 已知偏差（**必须写进规范**）

- `nearbyint`（"取整但不置 NX"）本 ISA **不提供**硬件变体 ⇒ 后端落 `0x20`（DYN），**值正确、NX 可能被置位**；
- 依据：SimRISC 浮点不产生异常/陷阱，NX 仅 `rf0[4:0]` 状态位；LLVM 非严格模式下 `llvm.rint`/`llvm.nearbyint` 均为 `IntrNoMem + IntrSpeculatable`（标志不可观察）。

### C. 生成物与计数

- `check_scope.py`：`excluded +2`、`total +2`（`fp` 不变）+ changelog 一行；
- `gen_asm_list --embed-spec`（速查 +2）、`gen_legality_list --apply`（`dst_rf0`/`encode_onehot` 清单 + excluded 区块）、`gen_isa_coverage`、`contract-asm-list`；
- `SimRISC-07` 变更记录追加 1 行；只读锁重算。

## 验收标准

1. 两条记录：`op=0x44`、`ha=0x03/0x0B`、`format=orri`、`legality` 含 `dst_rf0` + `encode_onehot`。
2. `check_scope` / `validate-encoding` / `check-rule-refs` / `check-instrinfo` / `check-isa-coverage` / `check_fp_contract`（族与 `fp` 不变）全绿。
3. `check-asm-list*` / `check-spec-*` / `check-spec-readonly` 全绿；`SimRISC-07 §1.1` +2 条。
4. `make check`（L1）rc=0。**L2 不在本册验收面**（`check_qemu_trans` 缺 2 条 trans ⇒ 已知红，登记 issue 由 `QEMU-072t` 关闭）。
5. **可达 FAIL ≥ 2**：① 忘改 `check_scope` 计数 ⇒ 红；② 不重算只读锁 ⇒ 红。
6. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（opx 空闲、`encode_onehot` 现有实现口径、速查表、锚点风格）。
2. 生成器加 2 条（`excluded`）+ 计数 + `check_scope`。
3. 写 `SimRISC-07 §4.x`（6 档表 + 边界）与 `contract-fp.md §roundint`（含偏差声明）。
4. 重生成 + 门控 + 只读锁 + 变更记录。
5. 反例注入 + L1 + 完成区 + 登记 issue。

## 可达 FAIL（**≥2**）

- `check_scope` 计数漏改 ⇒ 红；还原 ⇒ 绿。
- 只读锁不重算 ⇒ `check-spec-readonly` 红；重算 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不提供 `nearbyint` 硬件变体（偏差已声明）；不做 `*mag`；不做 FP→整数转换（已有 `fo2io` 族）。
- 不实现（`QEMU-072t`）、不接后端（`LLVM-125t`）、不翻转（`SPEC-162t`）。

## 完成区

**测试结果**：一键证据 `bash .work/evidence/SPEC-161t/run.sh --inject` = **79/79 PASS（rc=0）**，含 L1 `make check` rc=0。注入 3 例均「注入→红→`cp`+md5 还原→回绿」：① `check_scope` 计数回退 29/260→27/258 ⇒ `check-scope` rc=1；② 只读锁回退 SimRISC-07 sha256 ⇒ `check-spec-readonly` rc=1；③ 删除 `ftrnd` 记录 ⇒ 数据断言 + `check-scope` rc=1。日志 `.work/evidence/SPEC-161t/log/`。
**修改文件**：`contracts/opcodes.yaml`（258→260）；`spec/SimRISC-07-浮点运算.md`（册头/§1.1/§4.3/附录）；`spec/SimRISC-00-指令系统设计.md`（§4.6 两格 + 范围注记、§4 `scope` 分区计数 60→58、附录）；`.tao/contracts/contract-fp.md`（§18 `roundint` + `<a id="roundint">`）；生成物 `.tao/contracts/contract-asm-list.md`、`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`、`tests/llvm/lit/MC/DADAO-gen/gen-excluded.s`；生成器/门控 `tools/spec/{generate_opcodes,check_scope}.py`、`tools/llvm/gen_asm_list.py`、`tools/testcases/generate_lit_vectors.py`；`manifests/spec-readonly.lock.toml`；`.tao/knowledge/{issues.yaml,milestones.md}`；`.tao/tasks/spec/SPEC-161t-立册.md`。
**验收结果**：现场 `total=260 / excluded=29 / fp=58`；`check_scope`（excluded 29、total 260、fp 58）PASS；`validate-encoding` 260 条 OK；`check_fp_contract` 58 条 + 12 族不变；`check_isa_coverage --check` PASS（accept 256/reject 4、复核不符 0）；`check_lit_gen` 64/64；`check_rule_refs`/`check_instrinfo`/`check-asm-list{,-drift}`/`check-legality-{drift,invariants}`/`validate-vectors`/`check-spec-{refs,drift,codeblocks,numbering,changelog,archive,readonly}`/`check-contracts-pending`/`check-milestones-fresh`/`check_issues` 全 rc=0；L1 rc=0。**预期红（非本册验收面）**：`check_qemu_trans --strict` 258/260、`check_interface` 2 项 FAIL（缺 2 条 trans，`ISS-322`）。两记录 `legality` = `rfhb != rf0`（`dst_rf0`）+ 6 值 one-hot 表达式（`encode_onehot`）；`rule_refs` 按既有「excluded ⇒ []」口径为空（与 fence/lr/sc 一致）。
**新发现/坑**：① 原 `check_scope` 判据 `scope:fp ⇔ id 以 _rf 结尾` 与「excluded 的 RF 目的记录」不相容 ⇒ 拆为 `fp⇒_rf` + `_rf⇒scope∈{fp,excluded}`（对 M1/m3/m8/m9 的防线不变；门控判据细化已披露）。② `check_lit_gen` 要求 `gen-excluded.s` 的 @src 集合 ==「excluded 且无 `.td` def」全集 ⇒ 必须重生成该生成物，并给 `generate_lit_vectors._negative_text` 补 orri 反例形态；与任务书「不改 `tests/**`」冲突，按**生成物**处理（无语义向量改动，已披露）。③ 任务书「速查表 46→48」以 FMA（`SPEC-157t`）已落为前提；现场基线 44 ⇒ 本册 **44→46**。④ `SimRISC-07` 册头「fp 60 / SimRISC-02 7 条」与 `SimRISC-00 §4`「fp 60」为 `SPEC-163t` 残留，随册订正为 58 / 5（附录历史行不改写）。⑤ `check_qfc_coverage`（informational）仍报 2 条 M1 内 QFC-only（`cs.eq`/`cs.ne` 0x5E/0x5F 仍在 SimRISC-00 主表）——`SPEC-163t` 残留，未处置（不阻断 L1）。⑥ `gen_isa_coverage` md 静态说明仍把 `clmul.o` 列为 reject 例（`SPEC-155t` 后已 accept），非本册引入、未修。
**遗留问题**：① L2：QEMU 缺 `trans_ftrnd_orri_rf`/`trans_fornd_orri_rf`（已登记 `ISS-322`，`resolved_by: null`，由 `QEMU-072t` 关闭）；② LLVM `.td`/ISel 归 `LLVM-125t`；③ `excluded → fp` 翻转归 `SPEC-162t`。无其它未完成项。

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

### 第 1 轮 reviewer 验收

**判决：Accepted**（工作树快照前后一致、注入已还原；L2 红为预期且已登记 `ISS-322`）

**重跑记录（reviewer 自跑，rc=各命令自身）**：`check-scope` rc=0（fp=58/excluded=29/total=260/m1=156/m3=1/m8=7/m9=9，新增两向判据均 0 条违例）；`validate-encoding` rc=0（260 条 OK）；`check-rule-refs`/`check-instrinfo`/`check-isa-coverage`/`check-fp-contract` rc=0；`check-spec-{refs,drift,numbering,changelog,archive,readonly,codeblocks}` rc=0；`check-asm-list{,-drift,-prose}`/`check-legality-{drift,invariants}`/`validate-vectors`/`check-contracts-pending`/`check-milestones-fresh` rc=0；`check_lit_gen.py` rc=0（64/64）；`check_issues.py` rc=0（57 open/37 closed）；**`make check`(L1) rc=0（38 s）**。生成物幂等：`generate_opcodes`/`gen_asm_list --embed-spec`/`gen_legality_list --apply`/`generate_lit_vectors`/`gen_isa_coverage` 逐个 rc=0 且 `git status --porcelain` 前后无变化。

**约束核验**：① 记录字段逐条核对 —— `ftrnd` op=0x44/ha=0x03/value=0x440C0000、`fornd` ha=0x0B/value=0x442C0000，`orri`、`scope: excluded`、`decode: ILLI`、legality = `rfhb != rf0` + 6 值 one-hot 表达式；`op=0x44` 族内 46 条 ha 现场分布无重复，`0x03/0x0B` 原空位（§4.6 两格与表一致）。② 独立重算 Counter：m1 156/fp 58/excluded 29/m9 9/m8 7/m3 1，total 260。③ 语义面：`SimRISC-07 §2.3` 六档表 6 行、与 754-2019 六操作位序对应；`0x20` 读 `rf0[33:32]` 且**只有它置 NX**；`nearbyint` 偏差 + `rf0[33:32]` 不扩充两项在 `SimRISC-07 §2.3` 与 `contract-fp.md §18 roundint`（锚点在）均可见；`check_fp_contract` id=58、12 族不变（fp 未受污染）。④ 越界披露复核：`SimRISC-00` §4.6 两格 + §4 `fp 60→58` 残留订正**必要且正确**（`SPEC-163t` 删 `cs.eq/ne` 后的残留，锁注释已落授权指针）；`gen-excluded.s` 为 `generate_lit_vectors.py` **生成物重生成**（reviewer 重跑幂等），非手改，`_negative_text` 补 orri 反例形态系 `check_lit_gen` 全集覆盖要求所致，已披露。⑤ `rule_refs: []` 与 fence/lr/sc 29 条 excluded 口径一致。⑥ 未提交/未 push、未落 `.EXIT`、临时产物在 `/tmp/opencode/SPEC-161t-review/`。

**独立注入**（`cp`+md5，禁 checkout）：`check_scope.py` `EXPECTED_EXCLUDED 29→27` ⇒ md5 `123fab30…→a453f16a…`，`check-scope` **rc=1**（`[FAIL] excluded 计数: 期望=27 实际=29`）；`cp` 还原 ⇒ md5 相等、rc=0。**L2 预期红确认**：`check_qemu_trans --strict` rc=1、`258/260`，MISSING 恰为 `trans_ftrnd_orri_rf`/`trans_fornd_orri_rf` —— 与任务书口径及 `ISS-322` 登记（resolved_by: null，`QEMU-072t` 关闭）一致，**不计本册失败**。

**非阻塞观察**（供 architect 知悉，不返工）：① `check_scope` 判据由 `fp ⇔ _rf` 拆为 `fp⇒_rf` + `_rf⇒{fp,excluded}` —— 属判据细化（原式与 excluded RF 记录不相容），M1/m3/m8/m9 防线未弱化，完成区已披露；② 任务书「不改 `tests/**`」与 `gen-excluded.s`（生成物）冲突，按生成物处理口径可接受，建议后续册对「生成物除外」写明例外。

### 第 1 轮 engineer 自审

逐行审查（生成器 / 门控 / spec / 合约 / 证据脚本）后的 finding 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `check_scope` 双向判据与 excluded RF 记录不相容 | ✅已修 | 拆为 `fp⇒_rf` + `_rf⇒{fp,excluded}` | `check_scope` PASS（13 断言） |
| 第二方向是否漏检 `_rf` 记录落入 m1/m3/m8/m9 | ✅已修 | 新增该方向判据 | 正常绿；G3 删记录注入红 |
| 浮点章标题 badge 与混入 excluded 记录不符 | ✅已修 | `section_badge()` 按实际 scope 现场派生 | `check-asm-list{,-drift}` PASS；标题「46 条 = 44 fp + 2 excluded」 |
| 合约注「浮点运算章 46 条」误用章条数（应为 fp 44） | ✅已修 | 改用 `_fp_chapter_fp` | 生成物注记 44；drift PASS |
| `check_lit_gen` 需 `gen-excluded.s` 覆盖新反例 | ✅已修 | `_negative_text` 补 orri 形态 + 重生成 | `check_lit_gen` 64/64 |
| 只读册改动缺授权落纸 | ✅已修 | 锁注释写入用户原话 + 任务书指针 | `check-spec-readonly` 21/21 |
| 证据脚本 G2 断言串与实际日志不符 | ✅已修 | 改匹配 `MISMATCH spec/SimRISC-07` | 注入自检复跑 79/79 |
| `SimRISC-00 §4`「fp 60 条」残留 | ✅已修 | 订正 58 并同步锁哈希 | `check-spec-readonly` PASS；qfc lint 无新增差异 |
| `gen_isa_coverage` md 的 `clmul` reject 旧文案 | ⏸延后 | 非本册引入，不扩面 | 完成区「新发现⑥」 |
| `check_qfc_coverage` 2 条 QFC-only（`cs.eq/ne`） | ⏸延后 | `SPEC-163t` 残留，L1 不阻断 | 完成区「新发现⑤」 |
