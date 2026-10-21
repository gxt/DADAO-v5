# LLVM-123t: `ftfma`/`fofma` 后端（`.td` + `llvm.fma`/`fmuladd` 选择 + 拷贝代价断言）

**模块**：llvm
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-157t`（记录已立）、`QEMU-070t`（语义已实现，可端到端验证）；`INFRA-099t`（门控串行）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 真源

- `spec/SimRISC-07 §4.x` + `contract-fp.md §fma`：`fofma rfHB, rfHC, rfHD` = `rfHB ← rfHC × rfHD + rfHB`（**点积型**，目的兼加数），单次舍入。
- 编码：`op = 0x44`、`orrr`、`ftfma ha=0x22`、`fofma ha=0x2A`；`scope: excluded`（`SPEC-158t` 翻转）。

### 现场事实（2026-10-21 核，执行前须复核）

- 后端已有 `orrr` FP 先例（`ftadd_orrr_rf`/`foadd_orrr_rf` 等）⇒ `.td` 定义照抄形态即可，`(outs RF:$hb), (ins RF:$hc, RF:$hd)`。
- **LLVM 侧无需新 intrinsic**：`llvm.fma`（必融合）与 `llvm.fmuladd`（可融合）都是通用 intrinsic；`__builtin_fma` 由 clang 直接发 `llvm.fma` ⇒ **本册只做选择**。
- **点积型的代价（本册必须如实断言）**：
  - `llvm.fmuladd` 在循环里的自然形态是 `acc = acc + a*b` ⇒ 目的 = 累加器 = 加数 ⇒ **零拷贝**；
  - `llvm.fma(a,b,c)` 是 3-address，加数 `c` 不一定在目的寄存器 ⇒ 需 **1 条 `rf2rf` 搬入**（寄存器分配若能合并则消失，**不保证**）；
  - ⇒ 验收须同时给出"循环形态 0 拷贝"与"3-address 形态 ≤1 拷贝"的 `llc` 输出。
- `excluded` 允许有 `.td`（`fence` 先例，`validate_instrinfo.py` 第 34 行）；`gen-excluded.s` 的"UNREC"反例前提需按 `LLVM-122t` 已落地的「`.td` 感知」逻辑处理（若该逻辑尚未落地，本册须先补）。

## 目标

1. `.td` 定义两条（不设 `Pattern`，由伪指令/自定义选择）；
2. `llvm.fma` → 单条 `fofma`/`ftfma`（必要时 +1 搬入）；
3. `llvm.fmuladd` → 同（循环形态 0 拷贝）；
4. 不回归既有 `fomul`+`foadd` 序列（无 FMA 的路径仍可用）。

## 接口规范

- **输入**：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（`DADAOInstrInfoFP.td`、`DADAOCodeGen.td`、`DADAOISelLowering.cpp`）、`tests/llvm/lit/**`。
- **输出**：`ftfma_orrr_rf`/`fofma_orrr_rf` 定义；选择路径（伪指令或 `FMA` 伪指令 + `expandPostRAPseudo`，视是否需要固定目的=加数）；lit 用例；证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`（翻转归 `SPEC-158t`）；不改判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 选择形态：`fma(a,b,c)` 如何落成 2-address

- 目标：`fofma dst, a, b` 计算 `dst = a*b + dst_old` ⇒ 必须先把 `c` 放进 `dst`。
- 实现方式二选一（完成区写明选择）：
  - 甲：ISel 阶段生成 `COPY c→dst` + `FOFMA dst, a, b`（简单；依赖 RA 合并 COPY）；
  - 乙：自定义 DAG 节点/伪指令，在 `expandPostRAPseudo` 里先 `rf2rf` 再 `fofma`（可控，但代码多）。
- **判据**：循环内 `acc += a*b` 的 `llc` 输出必须**恰好 1 条 `fofma`**（0 拷贝）；独立 `fma(a,b,c)` 允许 1 条 `rf2rf`。

### B. 语义区分（**必须断言，不能用 fmuladd 冒充 fma**）

- `llvm.fma` 要求**单次舍入** ⇒ 只能落 `fofma`（不得展开为 `fomul`+`foadd`）；
- `llvm.fmuladd` 允许融合或分两步 ⇒ 落 `fofma`（优先）；
- 若目标关闭 FMA（未来特性开关），`llvm.fma` 必须**落 libm `fma` 调用**，不得静默展开成两条（语义错）——本册不实现开关，但须在代码注释与 lit 反例中说明该约束。

### C. lit 用例

- 正例 1：`@llvm.fmuladd.f64` 在循环（phi 累加器）⇒ 1 条 `fofma`，`FileCheck` 断言**无** `rf2rf`；
- 正例 2：`@llvm.fma.f64` 独立调用 ⇒ 1 条 `fofma`（允许 1 条 `rf2rf`）；
- 正例 3：`ftfma` 单精度同形；
- 反例：`fofma` 汇编/编码 round-trip（编码 `4422xxxx`/`442Axxxx` 现场派生）；目的 `rf0` ⇒ 汇编拒绝。

## 验收标准

1. `llc -O2`：循环形态 **1 条 `fofma`、0 条 `rf2rf`**；3-address 形态 **1 条 `fofma` + ≤1 条 `rf2rf`**（粘真实输出）。
2. `llvm-mc` 编码 == `op=0x44` + `ha=0x22/0x2A`（与 `validate-encoding` 一致）。
3. 反例：`fofma rf0, rf1, rf2` ⇒ 汇编失败/ILLI（`dst_rf0`）。
4. `check-instrinfo` 0 errors（`excluded` 有 `.td` 合规）；`check-lit` / `check-lit-full` 绿（含 `gen-excluded.s` 前提）。
5. **改 `.td` 后必须 `make install-host`**（随后 `make build-builtins` + `make build-musl-shared`，避免新鲜度门控红）。
6. `make check`（L1）rc=0；`make check-modules`（L2）rc=0。
7. **可达 FAIL ≥ 2**：① 把 `llvm.fma` 误展开成 `fomul`+`foadd` ⇒ lit「1 条 fma」断言红；② 去掉 COPY/伪指令 ⇒ `fma` 3-address 形态选不出或搬错 ⇒ 结果错（语义测试红）。
8. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（FP `.td` 形态、ISel 现有 FP 处理、`gen-excluded.s` 的 `.td` 感知是否已落）。
2. `.td` 两条 + 编码 round-trip lit。
3. `llvm.fma`/`fmuladd` 选择（先甲后乙二选一）。
4. lit 三正例 + 反例；`install-host` + builtins/musl。
5. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- `llvm.fma` 改走 `fomul`+`foadd`（临时改 ISel）⇒ lit 断言红；还原 ⇒ 绿。
- 删掉搬入（直接 `fofma dst, a, b` 但 dst 未预置加数）⇒ 语义用例红；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不加 clang builtin（`__builtin_fma` 已映射 `llvm.fma`）。
- 不做 Horner 专用 opx（另议）；不做 `fmsub`/`fnmadd`（负号用 `fosgnn`）。
- 不改 `scope`（`SPEC-158t`）；不做集成基准（`TESTCASES-058t`）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
