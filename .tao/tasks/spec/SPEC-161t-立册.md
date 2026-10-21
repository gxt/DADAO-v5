# SPEC-161t: `ftrnd`/`fornd` 立册（754-2019 六种取整，one-hot `immu6`，MISC-RF）

**模块**：spec
**项目里程碑**：M9（FP 完备性）
**依赖**：无（本册只立记录与语义）；后续 `QEMU-072t` → `LLVM-125t` → `SPEC-162t`（翻转）→ `TESTCASES-060t`
**状态**：待开始

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
- FP 族：`op=0x44`（MISC-RF），`ha`=opx；`ft` 组在前、`fo` 组 +8；**`0x03`/`0x0B` 现场为空** ✓。
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

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
