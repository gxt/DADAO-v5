# SPEC-069t: 窄位宽（8/16/32）指令集精简 + 高位规则统一为「值语义」

**模块**：spec（含 `contracts/`）；**影响**：QEMU、LLVM MC、向量、探针、harness、文档生成物（**原子同步 + 全量重建**）
**项目里程碑**：M2
**依赖**：用户裁定（2026-10-01，逐条）：① 删 24 编码；② 剩余窄位宽一律"值语义写满 64 位"；③ `not.t/w/b` 删除只留 `not.o`；④ `cmp.*` 按后缀扩展；⑤ 64 位逻辑真名/存在性已核实（`and.o`/`or.o`/`xor.o`/`xnor.o`，`orrr`，op `0x40`）
**状态**：待开始（**待用户确认任务书后下发**）

## 一、改动内容

### A. 删除 24 个编码（`contracts/opcodes.yaml` 251 → **227**；M1 176 → **152**）

| 组 | 具体 | 形态 |
|---|---|---|
| 窄逻辑 | `and.t/or.t/xor.t/xnor.t`、`and.w/or.w/xor.w/xnor.w`、`and.b/or.b/xor.b/xnor.b` | `orrr`（12）|
| 窄扩展 | `ext.ut/ext.st`、`ext.uw/ext.sw`、`ext.ub/ext.sb` | `orrr` + `orri`（12）|

**不动**：任何 `rwii` 形式（`set.zw`/`set.ow`/`or.w-rwii`/`andn.w-rwii` ✓）；`MISC-octa`（64 位 ✓）；`shl`/`shr`/算术/比较 ✓。

### B. 高位规则统一为「值语义：写满 64 位」（取消"高位不变"）

| 指令 | 新规则 |
|---|---|
| `shl.<w>`（仅 `.u*`）| 结果**零扩展**写满 64 位 |
| `shr.ut/uw/ub` | **零扩展**写满 |
| `shr.st/sw/sb` | **符号扩展**写满 |
| `cmp.ut/st/uw/sw/ub/sb` | 按后缀：`.s*` ⇒ 结果（−1/0/+1）**符号扩展**；`.u*` ⇒ **零扩展**（**现行规范未写**，本次明确）|
| `add/sub/mul/div/rem`（`.u*`/`.s*`）| 已是写满 ✓（无需改）|
| 窄逻辑 / 窄 `ext` | **已删除** ⇒ 不再存在"高位不变" ⇒ **全库只剩一套规则** ✓ |

### C. `not` 伪指令

- **删除** `not.t`/`not.w`/`not.b`；**只保留 `not.o`**（= `xnor.o rdHB, rdHC, rd0` ✓）。

## 二、载体清单（**13 类，逐项打勾验收** —— `SPEC-068t` 五轮教训）

| # | 载体 | 改动要点 |
|---|---|---|
| 1 | `spec/SimRISC-00-指令系统设计.md` | QFC 主表 + `MISC-octa/tetra/wyde/byte` 四子表删 24 条；伪指令表删 `not.t/w/b`；增设**高位规则通则**（值语义）|
| 2 | `spec/SimRISC-08/09/10` | 删 24 条条目与速查，改"高位保持"表述为**写满**，删 `not.*`（留 `not.o` 指引），`cmp.*` 明确高位规则 |
| 3 | `spec/SimRISC-04` | `shl/shr/ext` 公式中的 `rdHB[63:N+1] = rdHB[63:N+1]` 子句**删除/改写**（N=63 时为空区间，改后与通则一致）|
| 4 | `.tao/knowledge/contract-isa.md` | 表/条款/计数同步（251→227、176→152）|
| 5 | `contracts/opcodes.yaml` | 删 24 条记录（**不改其它**）|
| 6 | `tools/spec/generate_opcodes.py` | 三个 `build_misc_{byte,wyde,tetra}` + `_SPECIAL_IDS` 等同步；**重跑生成器 → `git diff contracts/opcodes.yaml` 为空**（幂等）|
| 7 | `tools/llvm/gen_asm_list.py` | 计数为动态推导 ✓（若含硬编码 **必须去掉**）；**重生成 `docs/assembly-list.md`** |
| 8 | **QEMU** | `insn.decode.patch`（三子表）+ `trans_logic.c.inc.patch`/`trans_extend.c.inc.patch` + `translate.c.patch`（cmp 扩展）；补丁 `index` 同步；**重建**（`make build-qemu`，`JOBS=8`）|
| 9 | **LLVM MC** | `DADAOInstrInfo.td` + AsmParser + Disassembler + **`tools/llvm/test_encoding_oracle.py`** + `tests/lit/MC/Dadao/**`；补丁 `index` 同步；**全量重建（30–90 分钟）** |
| 10 | 向量 | `tests/vectors/isa/*.yaml`：删 24 条相关用例；`shl/shr/cmp` 用例期望值**按新高位规则**更新（**独立重算**，不得从实现反推）|
| 11 | 探针/harness | `tools/qemu/min_rom_probe_*.py` 相关用例；`tests/scripts/build_test_binary.py` + `check_harness_ops.py` |
| 12 | 文档计数 | `docs/README.md`（251→227、其余计数）、`docs/assembly-list.md`（生成物）、`tests/vectors/inventory.md`（**176→152**）|
| 13 | 门控 | `check_interface_alignment` 的跨载体计数（`INTEG-007t` 已改推导 ✓ ⇒ 应自动反映 227/152）；`check_qemu_trans`（227/227）；`validate_vectors`；`check_lit_bytes` |

## 三、约束

- **原子**：13 类一次改完（中途态会造成载体间矛盾）。
- **串行**：与任何其它任务不得并行（共享 `contracts/`、`Makefile`、`spec/`、向量）；**并行子代理 ≤ 8**；**构建并行 `JOBS=8`**、一次一个长构建。
- **不改历史**：`spec/SimRISC-0.5.3/`、`.tao/tasks/**`、`docs/m1-retrospective.md`、`docs/testcases-009t-audit.md`。
- **不适用的表述**：全文不得再出现「高位不变」（除历史归档）。
- 反例注入须**可复原（含重建）**；命令缺失/失败 → **停下报告**。

## 四、验收标准

1. **计数**：`opcodes.yaml` = **227**（M1 **152**、excluded 75）；`inventory.md` M1 = 152；各门控自动反映（**不得改数字凑绿** ✗）。
2. **删除彻底**：24 条 id 与 `not.t/w/b` 在 `contracts/`+`spec/`+`tools/`+`tests/` **0 命中**（历史归档除外，逐条说明）。
3. **高位规则**：`shl/shr/cmp` 的值语义在 spec 与实现中一致；`grep "高位不变"` 在生效文件中 0 命中。
4. **两个生成器幂等**：`generate_opcodes.py` 与 `gen_asm_list.py` 重跑后与交付**逐字节一致**。
5. **LLVM/QEMU 实测**：`lit` 全绿、独立 oracle 全绿、`llvm-mc` 编码正确；QEMU 探针覆盖"新语义"（如 32 位 `shr.ut` 的高位为零、`cmp.st` 结果符号扩展）✓。
6. **反例门控（≥4 例，真 FAIL + 复原含重建）**：(a) 漏删某条 (b) 生成器未同步（重跑 diff 非空）(c) `shl.ut` 仍留旧高位语义 (d) oracle/lit 未同步。
7. **门控全绿**：`make check`、`check_qemu_trans --strict`、`check_interface_alignment`、`validate_vectors`、`check_lit_bytes`、`lit`、`check_harness_ops`、oracle（真实退出码）。
8. **13 类载体逐项打勾**（完成区出对照表）。
9. `git diff --name-only` 与清单对齐；未触历史。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
