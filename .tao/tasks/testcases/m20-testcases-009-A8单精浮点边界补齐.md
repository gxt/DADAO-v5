# m20-testcases-009: A8 单精浮点边界补齐（NaN/次正规/舍入/NX/OF/UF、转换饱和、FMA 单次舍入）

**模块**：testcases
**项目里程碑**：M20
**依赖**：`m20-testcases-008`（A6 位操作，链头；本任务为同批共享写者链第 2 件）
**可并行分片**：否（与 `tests/inst` 共享生成物串行，见「共享写者」）
**预估**：5–8 h（口径同 008；浮点四方含 gem5/chipyard 浮点实现差异风险，上浮到 8 h 上沿）
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景

按 `m20-riscv-arch-test-porting.md` A8 行缺口补单精浮点边界意图。只移植**测试意图/边界值/判据**，不复制 riscv-arch-test 源码；`ft` 窄写高 32 保持、无 NaN-boxing（`SimRISC-07` 开篇），ACT F/D 寄存器位型判据不可照搬。

## 共享写者（串行约束）

- 写 `tests/inst/**`、`tests/data/inst-signature/{expected.tsv,inputs.sha256}`、`tests/case-ledger.tsv`、`tests/inst.yaml`；
- 与 `m20-testcases-006`、`m20-infra-002` **串行**，不得并行；
- 本链内 `008 → 009 → 010 → 011 → 012` 逐件串行。

## 范围红线

- 不改 `spec/`、`.tao/contracts/`、引擎、`contracts/opcodes.yaml`；不复制 riscv-arch-test 源码；
- 期望值从 `spec/SimRISC-07`（含 `idl/lib/fp.idl` 库语义）独立派生，不从 QEMU/LLVM/chipyard 实测反推；
- F/D 寄存器模型差异（无 NaN-boxing、`ft` 高 32 保持）不得硬造 ACT 位型判据。

## 目标（自包含）

**op 与 spec 段（均已 grep 确认存在于 `contracts/opcodes.yaml` / `spec/`）**：

- `ftadd_orrr_rf` —— `SimRISC-07 §2.1`（S2D1；NaN/次正规/UF/NX/OF 由库 `ft_add`）
- `ftfma_rrrr_rf` —— `SimRISC-07 §2.5`（融合乘加，一次舍入，库 `ft_muladd`）
- `ftrnd_orri_rf` —— `SimRISC-07 §2.3`（取整；六档 one-hot，只有动态档且结果≠输入置 NX）
- `ftcls_orri_rf` —— `SimRISC-07 §5`（分类，10 类 one-hot）
- `ft2io_orri_rf` / `ft2it_orri_rf` / `ft2uo_orri_rf` / `ft2ut_orri_rf` —— `SimRISC-07 §1.1`/`§1.3`（ft→int 转换，值语义与标志在库 `ft_to_i32`/`ft_to_ui32` 等）

**落点规则**：优先在 `tests/inst/07-floating-point/<op>.S` 追加检查点；转换饱和/ FMA 单次舍入专项可新增 `.S`（进 `tests/inst.yaml`）。**不设条数上限**，只列「必须覆盖的边界意图」。

**必须覆盖的边界意图（逐条，按缺口补齐）**：

1. NaN 传播：sNaN ⇒ NV + canonical qNaN；qNaN 安静传播（不置 NV）；`ftadd` 等 S2D1 的 NaN 优先。
2. 次正规：次正规输入/输出；UF 按「舍入后 tiny 且 inexact」置位（§1.3，库 `ft_add` 内）。
3. 舍入六档：`RNT/RDN/RUP/RTA/RZ/RNA`（§1.1 六档 one-hot immu6）+ 动态档读 `rf0[33:32]`；非六值之一 ⇒ ILLI。
4. NX/OF/UF：溢出四象限（§1.3 四象限表）；`tininess-after-rounding`；有限 inexact ⇒ NX、NV 时不置 NX。
5. 转换饱和（§1.3）：`ft→int32/int64/uint32/uint64` 的 NaN/±Inf/正负溢出 ⇒ 饱和定值（有符号：NaN/±Inf/正溢出 ⇒ 上限、−Inf/负溢出 ⇒ 下限；无符号：NaN/+Inf/正溢出 ⇒ 0xFFFF…、−Inf/负溢出 ⇒ 0）；有限 inexact ⇒ NX；NV 时不置 NX。
6. FMA 单次舍入（§2.5）：精确积 `rfHB×rfHC` 与加数 `rfHD` 相加后**只舍入一次**；`0×±Inf` 即使加数为 qNaN 也置 NV；`Inf+(−Inf)` ⇒ NV；精确和为零 RDN ⇒ −0；溢出四象限与 UF/NX 由库 `ft_muladd` 承担。

**签名槽（四方）与生成物同步**：同 008 —— 新检查点生成签名槽，四方逐槽比对；新增 `.S` 同步 `tests/inst.yaml` / `tests/case-ledger.tsv` / `tests/data/inst-signature/{expected.tsv,inputs.sha256}`。

## 验证

真实目标名（`check-inst`/`check-inst-sig` 均已退役，经 grep Makefile 确认）：

1. `make check-inst-asm` —— 全量 PASS，镜像数 = `tests/case-ledger.tsv` 现场派生一致；
2. `make check-idl` 与 `make check-idl-full`（四方逐槽一致；浮点四方含 gem5/chipyard，任一方槽值漂移即红）；
3. `make inst-signature-data` + `check_inst_sig.py --data-only` + `sha256sum -c .../inputs.sha256`；
4. `make check-tests-index`、`make check-case-ledger`、`make check-index-blobs`、`make check-inst-macro-scope`、`make check-knowledge-refs` 各 rc=0；
5. 证据脚本落「运行期证据目录内的 `run.sh`」，可达 FAIL ≥3 路「注入 → FAIL → `cp`+md5 还原 → 回绿」：① 改转换饱和定值期望 ⇒ 红；② 删 `SIGUPD` ⇒ 槽未写红；③ 改一条 `.S` 内联期望 ⇒ 数据漂移红。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（按轮次追加）
