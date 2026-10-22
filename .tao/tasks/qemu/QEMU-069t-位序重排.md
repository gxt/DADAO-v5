# QEMU-069t: `fcls` 分类位序重排实现（`fp_classify_one` + 探针 oracle）

**模块**：qemu
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-156t`（**前置**：位表已改为 754/LLVM 顺序）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 语义真源

- `spec/SimRISC-07 §5`（`SPEC-156t` 之后的位表）：bit0 sNaN、1 qNaN、2 negativeInfinity、3 negativeNormal、4 negativeSubnormal、5 negativeZero、6 positiveZero、7 positiveSubnormal、8 positiveNormal、9 positiveInfinity；`[63:10]` 清零。
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
2. 探针的期望掩码**从 `spec/SimRISC-07 §5` 解析派生**（不再手抄常量），并覆盖 ft/fo 各 10 类；
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
- 做法：证据脚本**解析** `spec/SimRISC-07 §5` 的表格（`| 0 | signalingNaN |` 这类行）得到 `类别→位号`；探针用该映射生成期望；若 spec 缺失/格式变化 ⇒ 显式 FAIL（**不得**静默跳过）。
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

**测试结果**：探针 84/84 PASS（rc=0；classify 断言 34 条全部 exactly-1-bit + `[63:10]==0`）；`--selftest` PASS；`--oracle` PASS（spec 解析 10 对，位 0..9）。`check_qemu_trans --strict` = 259/260，与改前基线**逐字相同**（rc=1 为既有 clmul 缺失）。`make build-qemu` rc=0；`make check`(L1) rc=0；`make check-modules`(L2) rc=2（BLOCKED：`check-interface` 既有 clmul 259/260；其余 6 个 L2 子目标逐个 rc=0）。
**修改文件**：实现/探针 2 文件：`components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch`（仅 10 个位号 + new-file index blob）、`tools/qemu/min_rom_probe_035t.py`（spec §7 解析 oracle、classify 断言、7 个边界例、ILLI 终止符适配）；流程状态另改任务书 `**状态**` + `milestones.md` 一行（L1 状态一致性要求）。
**验收结果**：`./.work/evidence/QEMU-069t/run.sh` rc=0（OVERALL PASS）；`--inject` rc=0：(a) 实现旧位序 → 探针红 53/84 → cp+md5 还原 → 绿；(b) 7/8 互换 → 红 74/84 → 还原绿；(c) 临时 spec 换行 → 红 74/84（仓库 spec 零改动）。md5：前 `5eddaef2…` → 注入 `f81ef9d2…` → 还原 `5eddaef2…`；注入 `448853e1…` → 还原同前值；两次还原后源树 `git status` 干净。
**新发现/坑**：035t 探针在改动前的 master 上本已红（73/84）：`fence 0`（0x77000000）自 ADR-0034 起是合法 no-op，原 ROM 终止符不再产生 ILLI；改 `fence fm=1`（0x77801000）恢复 ILLI(0x88)。`trans_fp.c.inc.patch` 是 new-file 补丁，改内容须同步 `index …<blob>`（`check-index-blobs`）；新增 spec 解析默认拒错（缺节/行数≠10/位非 0..9 均显式非零退出）。
**遗留问题**：L2 无法 rc=0：`check-interface` 的 clmul `trans_*` 缺失为**改前既有**（`259/260`，ISS-307/ADR-0035 另册），不在本册 2 文件范围；`milestones.md` 一行按流程留 `/complete` 收尾。

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

### 第 1 轮 reviewer 验收（2026-10-22，提交 `177018aa` 之后重跑）

**重跑记录**（reviewer 亲自执行，均真实 rc）：
- 位号 diff：`git diff bd142109..177018aa -- <trans_fp patch>` 仅 10 行第三参数 + index blob 变化，`fp_and3(...)` 条件 10 行逐字未变；新位号 0 sNaN/1 qNaN/2 negInf/3 negNormal/4 negSubnormal/5 negZero/6 posZero/7 posSubnormal/8 posNormal/9 posInf 与 `spec §7` 表逐项一致。
- `--oracle` rc=0：10 对 类别↔位号（bit 0..9）；`load_class_bits_from_spec` 真解析 spec §7（缺节/行数≠10/位非 0..9 显式 FAIL），oracle 非手抄。
- reviewer 独立注入（cp+md5 纪律，非用工程师脚本）：改仓库 spec 7/8 两行（md5 363b3455→2d078efb）⇒ 全探针红 74/84（CL06/07/16/17/24-30）；`cp` 还原 md5=363b3455 相等 ⇒ 回绿 84/84。`--oracle` 单独仍 PASS 系结构自洽（与 engineer 自审 finding 3 一致，已用全探针补盲）。
- 全探针 rc=0：84/84；classify 断言 34 条 exactly-1-bit=OK + `[63:10]==0` OK；`--selftest` rc=0。
- 计数基线独立核：`git archive bd142109 components/qemu/patches` → /tmp 临时树 + `check_qemu_trans --src <临时树> --strict` = 259/260 rc=1；改后同 259/260 rc=1，输出逐字相同 ⇒ 计数不变，红 = clmul 缺 trans（ISS-307）**既有、非本册**。
- `make build-qemu` rc=0；`make check`(L1) rc=0；`make check-modules`(L2) rc=2：唯一红子目标 `check-interface`（2 FAIL 全为 clmul 259/260），其余 6 个 L2 子目标 rc=0；基线同红 ⇒ **既有，不阻断本册**。
- `run.sh --inject` rc=0：(a) 旧位序→红 53/84→还原绿；(b) 7/8 互换→红 74/84→绿；(c) 临时 spec 换行→红 74/84→绿；md5 对账全成立。
- **`./run.sh`（默认模式）rc=1**：`[FAIL] git diff file count expect=2 actual=0`、`[FAIL] git diff is exactly patch+probe expect=0 actual=1`（其余全部 PASS/BLOCKED 正确）。
- 快照对账：前/后 `git status --porcelain -uall` 均 0 行；patch/probe/spec md5 与开工一致，reviewer 未提交。

**约束核验**：`spec/**`/`contracts/**`/`insn.decode` 零改动 ✓；只动 2 个实现/探针文件（+任务书/milestones 流程文件）✓；未 commit/push ✓。

**判决：Needs Revision**（唯一打回点，产物实质全部达标）：
`run.sh` L138-142 的 diff-scope 检查用**工作树** `git diff --name-only -- components tools/qemu`，改动已提交（`177018aa`）后必为空 ⇒ 一键重放在当前状态必然红，完成区「run.sh rc=0」不可复现。**修法**：改用 `git diff --name-only bd142109..HEAD -- components tools/qemu`（reviewer 已验证恰输出 patch+探针 2 文件），预期重跑 rc=0；只需修脚本，无需重建 QEMU，修后快速复验。

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 探针 035t 在 master 上整片红（73/84）：ROM 终止符 `fence 0` 已合法 | ✅已修 | 终止符改 `fence fm=1` 0x77801000，注释指明 ADR-0034 | 探针 84/84；`--inject`(a)(b) 红/绿均按预期 |
| new-file 补丁改内容后 `check-index-blobs` 红 | ✅已修 | patch 头 `index 00000000..3091b47` → `..71f1cf2` | `make check` rc=0；`check_index_blobs` 132 OK |
| 仅换 spec 行时 `--oracle` 仍 PASS（结构自洽） | ✅已修 | 证据脚本 (c) 改为跑**全探针**（实现不变、spec 换行），并加 IEEE 位型→类别交叉校验 | `--inject`(c) 红 74/84；仓库 spec md5 不变 |
| 证据脚本 L2 基线个数误取 260（实际应为 259） | ✅已修 | 基线解析改为取 `259/260` 的分子 | `run.sh` rc=0，`[BLOCKED] actual=259 baseline=259` |
| 未修 finding | 无 | — | — |

### 第 2 轮 reviewer 验收（2026-10-22，针对第 1 轮唯一打回项复验）

- **脚本改动核验**：`run.sh` L139/144 三处改为提交面 `git -c core.quotepath=false diff --name-only bd142109..HEAD`（范围 + 禁区），已提交后可一键重放；断言仍可达 FAIL（count≠2 / diff 非空 / 禁区非 0 即红）、仍直接捕获 rc、不吞码。
- **重跑**：`bash .work/evidence/QEMU-069t/run.sh` ⇒ **rc=0**，`[PASS] git diff file count actual=2`、`[PASS] git diff is exactly patch+probe`、`[PASS] spec/contracts/insn.decode diff actual=0`；全脚本 25 PASS / 0 FAIL / 1 BLOCKED（L2 既有 clmul，判定不变，不阻断）。
- **快照对账**：前/后 `git status --porcelain -uall` 均仅 1 行 `M 任务书`（=第 1 轮审阅记录本身，reviewer 未提交，属预期）；脚本重跑未引入任何新改动，`trans_fp.c.inc.patch`/探针/spec md5 与第 1 轮一致；HEAD 仍为 `177018aa`，reviewer 未 commit/push。

**判决：Accepted**（第 1 轮唯一打回项已修，产物实质与第 1 轮核验结论不变；L2 红属既有 clmul ISS-307，不阻断本册）。
