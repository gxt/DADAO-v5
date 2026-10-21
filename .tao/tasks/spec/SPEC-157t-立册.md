# SPEC-157t: `ftfma`/`fofma` 立册（点积型 FMA，MISC-RF，`opx 100-010 / 101-010`）

**模块**：spec
**项目里程碑**：M9（FP 完备性）
**依赖**：无（本册只立记录与语义）；后续 `QEMU-070t` → `LLVM-123t` → `SPEC-158t`（翻转 `excluded → fp`）→ `TESTCASES-058t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 用户裁定（2026-10-21，原话）

> 「增加任务：ftfma/fofma指令，orrr格式，点积型，MISC-RF，opx为100-010/101-010」

助记符经确认为 **`fma`**（非 `madd`/`fla`）：FMA 是 IEEE 754 `fusedMultiplyAdd`、LLVM `llvm.fma`、C `fma()` 的通用名；`madd` 会与"`fomul` 再 `foadd`"混淆，`fla` 不表意。

### 现场事实（2026-10-21 核，执行前须复核）

- FP 族 = `op = 0x44`（`0100-0xxx` 行第 5 格 = MISC-RF），`ha` 即 6 位 opx；**`ft` 组在前、`fo` 组固定 +8**：`ftadd=0x10`/`foadd=0x18`、`ftqcmp=0x20`/`foqcmp=0x28`。
- **`0x22`（`100-010`）与 `0x2A`（`101-010`）现场均为空** ⇒ 正好构成一对（ft/fo +8），符合既有约定。
- `orrr` = opx + 3 个寄存器（`hb`=目的、`hc`/`hd`=源）⇒ **只能 2-address**（目的兼一个源）。
- 4 槽方案（`rrrr`，1 目的 + 3 源）被否：`rrrr` 无 opx，必须占**主编码表** op 字节，且 `0101` 行仅剩 `0x57`/`0x58` 两格 ⇒ 与「浮点不落主表」冲突。
- 现有 `SimRISC-07 §1.1` 速查 = **44 条**（`scope: fp（已实现）`）；加两条 ⇒ 46 条。
- `check_fp_contract.py` 把 FP 分 **12 族**并写死 `fp` 计数 **60**；`scope: excluded` 的记录**不**进 `fp_semantics.yaml` ⇒ 本册**不动**族表/计数（族 `fma` 与 `fp 60→62` 留到 `SPEC-158t` 翻转时）。

## 目标

1. 立 `ftfma`/`fofma` 两条记录（`scope: excluded`、`decode: ILLI`），编码/semantic/合法性/异常齐备；
2. 规范正文写清**点积型**语义（目的兼加数）与"先读后写"；
3. 生成物与计数同步；`check-instrinfo` 不因"excluded 无 `.td`"报错（`fence` 先例）。

## 接口规范

- **输入**：`tools/spec/generate_opcodes.py`、`tools/spec/check_scope.py`、`spec/SimRISC-07-浮点运算.md`、`.tao/contracts/contract-fp.md`、`manifests/spec-readonly.lock.toml`。
- **输出**：`contracts/opcodes.yaml`（260→**262**）、`SimRISC-07 §1.1`（44→46）与新增 §4.x 语义、`contract-fp.md` 新增 `fma` 段（含 `<a id="fma">` 锚点，供 `fp_semantics.yaml` 后续引用）、`gen_asm_list --embed-spec`/`--drift`、`gen_isa_coverage`、只读锁重算、证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：**不**改 `components/**`、`tests/**`；不改门控判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 语义（点积型，**目的兼加数**）

```
ftfma rfHB, rfHC, rfHD      @ rfHB ← rfHC × rfHD + rfHB（单精度，单次舍入）
fofma rfHB, rfHC, rfHD      @ rfHB ← rfHC × rfHD + rfHB（双精度，单次舍入）
```

- **必须写清**：「目的 `rfHB` 同时是加数 ⇒ 硬件**先读**全部源（含旧 `rfHB`）再写结果，行为确定」——现有 §4.1 只写了"先读全部源操作数"，需补"目的作源"的情形。
- **单次舍入**：`a×b` 的精确积只舍入一次（`fma` 的核心；与 `fomul`+`foadd` 两条不等价，须给出反例例子）。
- **`×` 可交换**：`rfHC`/`rfHD` 互换结果不变（加数恒为 `rfHB`）。
- **异常**：sNaN 输入 ⇒ NV + qNaN；结果溢出/下溢按 IEEE 置 OF/UF；**一次运算只置一次**。

### B. 合法性

- 目的 `rf0` ⇒ **ILLI**（`dst_rf0`，与 FP 族 30 条一致）；
- 源可为 `rf0`（读出 FCSR 的 qNaN 位，符合既有 FP 源语义）；
- 无 `rd0`/dual-dest 概念（`rf` 组；本册**不得**引入 `dst_dual_same`）。

### C. 编码与生成物

- `format = orrr`、`op = 0x44`、`ftfma ha = 0x22`、`fofma ha = 0x2A`；`scope = excluded`、`decode = ILLI`；
- `check_scope.py`：`excluded 28→29`、`total 260→262`（`fp` 仍 60）+ changelog 一行；
- `generate_opcodes.py`：`rec(...)` 两条 + 文件头计数注释；`docstring` 的 scope 说明补 `fma`；
- 生成物：`gen_asm_list --embed-spec`（速查 44→46）、`gen_legality_list --apply`（`dst_rf0` 清单 + excluded 区块）、`gen_isa_coverage`、`.tao/contracts/contract-asm-list.md`；
- `SimRISC-07` 变更记录**追加** 1 行；只读锁重算。

## 验收标准

1. `contracts/opcodes.yaml` = **262** 条；`excluded` = **29**；`fp` = **60**（现场输出）。
2. `check_scope` / `validate-encoding` / `check-rule-refs` / `check-instrinfo`（0 errors，`excluded` 无 `.td` 合规）/ `check-isa-coverage` / `check_fp_contract`（**12 族 / fp 60** 不变）全绿。
3. `check-asm-list` / `--drift` / `--prose` / `check-spec-codeblocks` / `check-spec-*` / `check-spec-readonly` 全绿。
4. `make check`（L1）rc=0。**L2 不在本册验收面**：`check_qemu_trans --strict` 因新增记录缺 trans 会红（**登记 issue**，由 `QEMU-070t` 关闭；与 `ISS-317` 同类）。
5. **可达 FAIL ≥ 2**：① 忘改 `check_scope` 计数 ⇒ `check-scope` 红；② 不改只读锁 ⇒ `check-spec-readonly` 红。
6. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（`0x22`/`0x2A` 空闲、`rec()` 形态、速查表结构、`contract-fp.md` 锚点风格）。
2. 生成器加两条（`excluded`）+ 计数 + `check_scope` 计数。
3. 写 `SimRISC-07 §4.x`（点积型语义、先读后写、单次舍入、异常）与 `contract-fp.md §fma`。
4. 重生成全部产物 → 门控；只读锁重算；变更记录 1 行。
5. 反例注入 + L1 + 完成区 + 登记缺口 issue。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- 临时把 `check_scope.py` 的 `excluded` 计数改回 28（或漏改）⇒ `check-scope` 红；还原 ⇒ 绿。
- 不更新 `manifests/spec-readonly.lock.toml` ⇒ `check-spec-readonly` 红；重算 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 本册**不**实现（QEMU/LLVM 各一册）；**不**翻转 `scope`（`SPEC-158t`）。
- 不做 `fmsub`/`fnmadd`/`fnmsub`（负号用 `fosgnn` 或后续另立 opx）。
- 不做 Horner 形态的第二个 opx（将来若热点，另立）。
- 不引入 `dst_dual_same`；不改 `rf0` 语义。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
