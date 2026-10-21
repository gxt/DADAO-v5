# QEMU-069t: `fcls` 分类位序重排实现（`fp_classify_one` + 探针 oracle）

**模块**：qemu
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-156t`（**前置**：位表已改为 754/LLVM 顺序）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 语义真源

- `spec/SimRISC-07 §7`（`SPEC-156t` 之后的位表）：bit0 sNaN、1 qNaN、2 negativeInfinity、3 negativeNormal、4 negativeSubnormal、5 negativeZero、6 positiveZero、7 positiveSubnormal、8 positiveNormal、9 positiveInfinity；`[63:10]` 清零。
- 语义不变：`focls/ftcls` 为 `orri` **块形态**（`immu6` = 1..63，先读后写），源 `rf`、目的 `rd`，不重叠。

### 现场实现（2026-10-21 核，执行前须复核）

- 实现位置：`components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch`
  - `fp_classify_one(TCGv_i64 raw, bool isdbl)`：用 `fp_set_bit_if(acc, cond, bit)` **逐类置位**，当前位号 = 旧顺序（0 negInfinity … 7 positiveInfinity、8 signalingNaN、9 quietNaN）⇒ **本册只改这 10 个位号参数**，条件表达式不动。
  - `trans_ftcls_orri_rf` / `trans_focls_orri_rf` 只做合法性检查与块循环（`a->hd` 个元素）⇒ **不改**。
- 探针：`tools/qemu/min_rom_probe_035t.py`
  - `CLS = {"negInf": 1<<0, …, "qNaN": 1<<9}`（旧位序常量）；
  - `FT_CLASS_VALS` / `FO_CLASS_VALS`：10 个样本值（`0x00000000`、`0x7FC00000` 等）**值与类别名都不变**，只是期望掩码的来源要改。
- 门控：`tools/qemu/check_qemu_trans.py`（本册**不改** `insn.decode` ⇒ 计数不变，现场派生）。

## 目标

1. `fp_classify_one` 的 10 个位号改为新顺序（条件表达式**逐字不动**，避免"顺手改语义"）；
2. 探针的期望掩码**从 `spec/SimRISC-07 §7` 解析派生**（不再手抄常量），并覆盖 ft/fo 各 10 类；
3. 改后 `check_qemu_trans` 计数不变；L1/L2 绿。

## 接口规范

- **输入**：`components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch`、`tools/qemu/min_rom_probe_035t.py`、`spec/SimRISC-07`（只读，用作 oracle 来源）。
- **输出**：
  1. `fp_classify_one` 位号重排（10 处）；
  2. 探针 `CLS` 改为**从 spec 表解析**（或由脚本生成后再内联 + 断言），并加"10 类位各不相同、且与 spec 表逐项一致"的断言；
  3. 证据 `.work/evidence/<任务ID>/run.sh`（一键：解析 spec → 跑探针 → 断言）。
- **约束**：不改 `insn.decode`、不改 `spec/`、`contracts/`、不改其它 FP 族（sign/compare/convert）；不改门控判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 只改位号，不改条件

- `fp_set_bit_if` 的 10 个调用点：只把第三个参数（bit 号）换成新值；`fp_and3(...)` 条件**逐字保留**。
- 特例：`sNaN`/`qNaN` 的判据是 `exp_all & man≠0` + mantissa MSB（`mmsb`）⇒ 不变；仅位号从 8/9 变为 0/1。
- 改完**自检恒等式**（写进证据脚本）：对每个样本值，结果必须**恰好 1 个 bit 置位**且 `rd[63:10]==0`。

### B. 探针 oracle 必须独立于实现

- **禁止**把 `CLS` 继续手抄（否则实现与期望可以一起错，测不出）。
- 做法：证据脚本**解析** `spec/SimRISC-07 §7` 的表格（`| 0 | signalingNaN |` 这类行）得到 `类别→位号`；探针用该映射生成期望；若 spec 缺失/格式变化 ⇒ 显式 FAIL（**不得**静默跳过）。
- 交叉自检：对 `FT_CLASS_VALS` 的 10 个样本，期望掩码两两不同、且互不包含。

### C. 覆盖面

- ft/fo 各 10 类（现有 20 例保留）；建议补 ≥2 个"同值不同类"的边界（如 `0x7F7FFFFF`（max normal）与 `0x00800000`（min normal）落 `posNormal`；`0x007FFFFF` 落 `posSubnormal`）。
- 块形态 `immu6>1`：保留既有 ≥1 例（验证"逐个元素"而非只算第一个）。

## 验收标准

1. 探针全绿（计数现场派生，粘真实输出）：每类恰好 1 bit、`[63:10]` 为 0。
2. 期望掩码来自 spec 解析（证据脚本输出"10 对 类别↔位号"与 spec 表一致；**改错 spec 或改错实现任一**都能红）。
3. `python3 tools/qemu/check_qemu_trans.py --strict` 计数**与改前相同**（现场派生，粘前后两次数值）。
4. `make build-qemu` rc=0；`make check`（L1）rc=0；`make check-modules`（L2）rc=0。
5. **可达 FAIL ≥ 2**（真实注入 → 红 → `cp`+md5 还原 → 绿）：
   - (a) 只改实现不改期望（或反之）⇒ 探针红；
   - (b) 故意把 `posNormal` 与 `posSubnormal` 位号互换 ⇒ 探针红。
6. `git diff --stat` 显示只动 2 个文件（`trans_fp.c.inc.patch`、探针）；`insn.decode`/`spec/**`/`contracts/**` 零改动。
7. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（`fp_classify_one` 10 个调用点、探针 `CLS`/样本值、`check_qemu_trans` 当前计数）。
2. 重排位号 → 重建 QEMU → 探针跑（先用手抄常量确认实现本身对）。
3. 把期望改为 spec 解析 + 断言（独立 oracle）。
4. 反例注入（2 条）+ 还原。
5. L1/L2 + 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- 实现改新序、探针仍用旧序 ⇒ 探针红（20 例全错位）；还原 ⇒ 绿。
- `posNormal`（bit8）与 `posSubnormal`（bit7）位号互换 ⇒ 探针红；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不接 `llvm.is.fpclass`/`fpclassify`（`ISS-188`，另册；本册只保证硬件语义与 spec 一致）。
- 不改 sign/compare/convert 族；不改 `fcls` 的合法性规则（`dst_rd0`/`mreg_*`）。
- 不与 RISC-V `fclass` 位序兼容（`SPEC-156t` 已定：破坏性修正，0.5.5-rc 未发布）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
