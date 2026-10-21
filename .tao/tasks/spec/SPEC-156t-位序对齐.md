# SPEC-156t: `fcls` 分类位序改为 IEEE 754-2019 / LLVM 顺序（10 类重排）

**模块**：spec
**项目里程碑**：M9（FP 完备性）
**依赖**：无（纯规范面）；后续实现 = `QEMU-069t`。`ISS-188`（FP 完备性缺口）中的 `fpclass` 项因此**解锁**（后端可零重排直接接 `llvm.is.fpclass`）。
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 用户裁定（2026-10-21，原话）

> 「刚查看了 754-2019 标准，虽然没定义具体编码，但其顺序和 llvm 的 is_fpclass 一致；定一个任务，修改 focls/ftcls 的编码，与 llvm 的 is_fpclass 一致」

**口径澄清（本册据此执行）**：**不改指令编码**（`op`、`format`、字段、汇编语法全部不动），只改 `focls`/`ftcls` **结果掩码的位分配**（10 类各占哪一位）。

### 现状位序（RISC-V `fclass` 式）

`spec/SimRISC-07 §7` 表格 + `.tao/contracts/contract-fp.md`（`classify` 条）：

```
bit0 negativeInfinity  bit1 negativeNormal  bit2 negativeSubnormal  bit3 negativeZero
bit4 positiveZero      bit5 positiveSubnormal bit6 positiveNormal   bit7 positiveInfinity
bit8 signalingNaN      bit9 quietNaN
```

### 目标位序（IEEE 754-2019 `class` 的类别顺序 = LLVM `FPClassTest`）

```
bit0 signalingNaN   bit1 quietNaN        bit2 negativeInfinity   bit3 negativeNormal
bit4 negativeSubnormal bit5 negativeZero  bit6 positiveZero      bit7 positiveSubnormal
bit8 positiveNormal  bit9 positiveInfinity
```

### 事实依据（2026-10-21 核）

- `llvm/include/llvm/ADT/FloatingPointMode.h:338` 的 `FPClassTest`：`fcSNan=0x001`、`fcQNan=0x002`、`fcNegInf=0x004`、`fcNegNormal=0x008`、`fcNegSubnormal=0x010`、`fcNegZero=0x020`、`fcPosZero=0x040`、`fcPosSubnormal=0x080`、`fcPosNormal=0x100`、`fcPosInf=0x200` ⇒ **位序 = 上面目标顺序**（每位一个类）。
- IEEE 754-2019 §5.7「Non-computational operations」含 `class` 与谓词族（`is754version2019`/`isCanonical`/`isFinite`/`isInfinite`/`isNaN`/`isNormal`/`isSignaling`/`isSignMinus`/`isSubnormal`/`isZero`）；**标准只定义类别语义与顺序，不规定整数编码**；10 类顺序与 Fortran `ieee_class_type` 一致（sNaN, qNaN, −∞, −normal, −subnormal, −0, +0, +subnormal, +normal, +∞）。
- 现位序是 **RISC-V `fclass`** 的位序 ⇒ 与 LLVM 掩码差一个「循环右移 2 位」，后端每次使用都要重排常量。

### 影响与代价（须在完成区如实记录）

- **收益**：`fcls` 结果可直接与 `llvm.is.fpclass` 的 `FPClassTest` 掩码做 `and`/比较，**零重排**；与 754 `class` 的类别顺序一致，文档/教学不再需要"转位序"说明。
- **代价（破坏性）**：与 RISC-V `fclass` 的原始位序**不兼容**（直接套用 RISC-V 掩码常量的代码需重映射）。本 ISA 版本 `0.5.5-rc` **未发布** ⇒ 可接受；须在 `SimRISC-07` 变更记录写明"破坏性修正"。

## 目标

1. `SimRISC-07 §7` 的 10 行位表改为目标顺序（含 `[63:10]` 清零表述不变）；
2. `.tao/contracts/contract-fp.md` 的 `classify` 条同步（**两处必须逐字一致**）；
3. `SimRISC-07` 变更记录**追加** 1 行（不改写历史）；只读锁 `sha256` 重算；
4. 不改任何指令编码、不改 `contracts/opcodes.yaml`、不改 `contracts/fp_semantics.yaml`（其只引用 `contract-fp.md#classify` 锚点）。

## 接口规范

- **输入**：`spec/SimRISC-07-浮点运算.md`（§7 + 附录变更记录）、`.tao/contracts/contract-fp.md`、`manifests/spec-readonly.lock.toml`。
- **输出**：
  1. 位表两处同步改 + 变更记录 1 行；
  2. 只读锁重算（`check-spec-readonly` 绿）；
  3. 证据 `.work/evidence/<任务ID>/run.sh`（含"两处位表一致性"文本比对）。
- **约束**：**只**改上述文件；`opcodes.yaml`/`fp_semantics.yaml`/`tests/**` 一律不动（实现归 `QEMU-069t`）；不改门控判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 位表必须机械一致（本册唯一的"漂移风险"）

- 现状：位表只有**人工**抄写（spec 与 contract 各一份），**没有门控**校验两者一致 ⇒ 极易改一处漏一处。
- 本册要求：证据脚本**解析** `spec/SimRISC-07 §7` 的表格（行 `| 位 | 类别 |`）与 `contract-fp.md` 的 `10 类位：...` 行，**逐项比对** 10 个"位号↔类别"对；不一致即 FAIL。
- 建议（可选、非验收前提）：若实现成本低，可把该比对并入既有 `check-fp-contract`（**须另册**，本册不做，避免扩面）。

### B. 变更记录与只读锁

- `SimRISC-07` 附录追加一行（格式照既有条目）：`0.5.5-rc（未发布）` 段内注明「`focls`/`ftcls` 分类位序改为 754-2019 `class` 顺序（与 LLVM `is.fpclass` 一致）；**破坏性**：与 RISC-V `fclass` 位序不兼容」。
- 只读锁：重算 `spec/SimRISC-07` 的 `sha256`（`technique` 照既有做法），`check-spec-readonly` rc=0。

### C. 明确不动的面

- `contracts/opcodes.yaml`：`focls_orri_rf`/`ftcls_orri_rf` 的 `op`/`format`/`value`/`mask`/`rule_refs` **逐字节不变**。
- `contracts/fp_semantics.yaml`：只引用锚点 `contract-fp.md#classify`，位表不在其中 ⇒ 不改。
- `tests/**`：向量与探针归 `QEMU-069t`（本册不改测试，避免"改了测试等于自证"）。

## 验收标准

1. `spec/SimRISC-07 §7` 位表 = 目标顺序（10 行，位号 0..9 各一）；`[63:10]` 清零表述保留。
2. `.tao/contracts/contract-fp.md` 的 `classify` 条与新位表**逐项一致**（证据脚本自动比对，输出 10 对）。
3. `check-spec-readonly` / `check-spec-changelog` / `check-spec-numbering` / `check-spec-drift` / `check-spec-codeblocks` / `check-fp-contract` 全绿。
4. `git diff` 显示 `contracts/opcodes.yaml`、`contracts/fp_semantics.yaml`、`tests/**` **零改动**（粘真实 `git diff --stat`）。
5. `make check`（L1）rc=0。
6. **可达 FAIL ≥ 2**（真实注入 → 红 → `cp`+md5 还原 → 绿）：
   - (a) 只改 spec 不改 contract（或反之）⇒ 一致性脚本红；
   - (b) 不重算只读锁 ⇒ `check-spec-readonly` 红。
7. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（`§7` 表格格式、`contract-fp.md` 该行格式、变更记录段、只读锁条目）。
2. 改位表两处 → 跑一致性脚本 → 变更记录 1 行。
3. 只读锁重算 → 全部门控。
4. 反例注入（2 条）+ 还原。
5. L1 + 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- 只改 `spec/SimRISC-07` 的位表、故意漏改 `contract-fp.md` ⇒ 一致性脚本红；还原 ⇒ 绿。
- 改完 spec 不重算 `manifests/spec-readonly.lock.toml` ⇒ `check-spec-readonly` 红；重算 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不改指令编码（用户口径：只改结果位序）。
- 不改 RISC-V 兼容性说明之外的任何 spec 章节（`§7` 以外不动）。
- 不实现 QEMU/L3 向量（`QEMU-069t`）、不接 LLVM `is.fpclass`（`ISS-188`，另册）。
- 不把"两处位表一致性"并入 `check-fp-contract`（避免扩面，另议）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
