# SPEC-159t: `ftmin`/`fomin`/`ftmax`/`fomax` 立册（IEEE 754-2019 `minimumNumber`，MISC-RF）

**模块**：spec
**项目里程碑**：M9（FP 完备性）
**依赖**：无（本册只立记录与语义）；后续 `QEMU-071t` → `LLVM-124t` → `SPEC-160t`（翻转 `excluded → fp`）→ `TESTCASES-059t`
**状态**：待开始

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

- FP 族：`op = 0x44`（MISC-RF），`ha` = 6 位 opx；`ft` 组在前、`fo` 组 +8。
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

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
