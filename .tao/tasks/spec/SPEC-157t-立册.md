# SPEC-157t: `ftfma`/`fofma` 立册（四操作数 FMA，`rrrr`，`op 0x5E/0x5F`）

**模块**：spec
**项目里程碑**：M9（FP 完备性）
**依赖**：无（本册只立记录与语义）；后续 `QEMU-070t` → `LLVM-123t` → `SPEC-158t`（翻转 `excluded → fp`）→ `TESTCASES-058t`
**状态**：待开始

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
- `check_fp_contract.py` 把 FP 分 **12 族**并写死 `fp` 计数 **60**；`scope: excluded` 的记录**不**进 `fp_semantics.yaml` ⇒ 本册**不动**族表/计数（族 `fma` 与 `fp 60→62` 留到 `SPEC-158t` 翻转时）。

## 目标

1. 立 `ftfma`/`fofma` 两条记录（`scope: excluded`、`decode: ILLI`），编码/semantic/合法性/异常齐备；
2. 规范正文写清**四操作数**语义（`rfHA ← rfHB × rfHC + rfHD`）与"目的与源重叠时先读后写"；
3. 生成物与计数同步；`check-instrinfo` 不因"excluded 无 `.td`"报错（`fence` 先例）。

## 接口规范

- **输入**：`tools/spec/generate_opcodes.py`、`tools/spec/check_scope.py`、`spec/SimRISC-07-浮点运算.md`、`.tao/contracts/contract-fp.md`、`manifests/spec-readonly.lock.toml`。
- **输出**：`contracts/opcodes.yaml`（260→**262**）、`SimRISC-07 §1.1`（44→46）与新增 §4.x 语义、`contract-fp.md` 新增 `fma` 段（含 `<a id="fma">` 锚点，供 `fp_semantics.yaml` 后续引用）、`gen_asm_list --embed-spec`/`--drift`、`gen_isa_coverage`、只读锁重算、证据 `.work/evidence/<任务ID>/run.sh`。
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

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
