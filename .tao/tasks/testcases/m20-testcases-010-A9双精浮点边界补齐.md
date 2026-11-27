# m20-testcases-010: A9 双精浮点边界补齐（FMA 单次舍入、min/max ±0/NaN、溢出方向）

**模块**：testcases
**项目里程碑**：M20
**依赖**：`m20-testcases-009`（A8 单精浮点；本任务为同批共享写者链第 3 件）
**可并行分片**：否（与 `tests/inst` 共享生成物串行，见「共享写者」）
**预估**：5–8 h（口径同 008；浮点四方含 gem5/chipyard 差异风险）
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景

按 `m20-riscv-arch-test-porting.md` A9 行缺口补双精浮点边界意图。只移植**测试意图/边界值/判据**，不复制 riscv-arch-test 源码；`fo` 双精无 NaN-boxing（`SimRISC-07` 开篇），ACT D 寄存器位型判据不可照搬。

## 共享写者（串行约束）

- 写 `tests/inst/**`、`tests/data/inst-signature/{expected.tsv,inputs.sha256}`、`tests/case-ledger.tsv`、`tests/inst.yaml`；
- 与 `m20-testcases-006`、`m20-infra-002` **串行**，不得并行；
- 本链内 `008 → 009 → 010 → 011 → 012` 逐件串行。

## 范围红线

- 不改 `spec/`、`.tao/contracts/`、引擎、`contracts/opcodes.yaml`；不复制 riscv-arch-test 源码；
- 期望值从 `spec/SimRISC-07`（含 `idl/lib/fp.idl`）独立派生，不从 QEMU/LLVM/chipyard 实测反推。

## 目标（自包含）

**op 与 spec 段（均已 grep 确认存在于 `contracts/opcodes.yaml` / `spec/`）**：

- `foadd_orrr_rf` —— `SimRISC-07 §2.1`（S2D1；NaN/次正规/OF/UF/NX 由库 `fo_add`）
- `fofma_rrrr_rf` —— `SimRISC-07 §2.5`（融合乘加，106 位精确积 + 192 位对齐，一次舍入，库 `fo_muladd`）
- `fomin_orrr_rf` / `fomax_orrr_rf` —— `SimRISC-07 §2.4`（`minimumNumber`/`maximumNumber`）
- `fornd_orri_rf` —— `SimRISC-07 §2.3`（取整；六档 one-hot，动态档结果≠输入才置 NX）

**落点规则**：优先在 `tests/inst/07-floating-point/<op>.S` 追加检查点；min/max ±0/NaN 专项、FMA 单次舍入专项可新增 `.S`（进 `tests/inst.yaml`）。**不设条数上限**，只列「必须覆盖的边界意图」。

**必须覆盖的边界意图（逐条，按缺口补齐）**：

1. FMA 单次舍入（§2.5）：精确积 `rfHB×rfHC` 与加数 `rfHD` 一次舍入；`0×±Inf` ⇒ NV（即使加数为 qNaN）；`Inf+(−Inf)` ⇒ NV；精确和为零 RDN ⇒ −0；溢出四象限与 UF/NX 由库 `fo_muladd` 承担。
2. min/max 的 ±0/NaN（§2.4 `minimumNumber`/`maximumNumber`）：`−0 < +0` ⇒ `fomin(−0,+0)=−0`、`fomax(−0,+0)=+0`；单 NaN ⇒ 返回那个数；双 NaN ⇒ canonical qNaN；sNaN 作输入 ⇒ NV（即使结果为数）；不涉舍入 ⇒ 不置 NX/OF/UF。
3. 溢出方向（§2.1/§1.3 四象限表）：`foadd`/`fofma` 溢出时按舍入方向落 ±Inf 或最大/最小有限值；UF（次正规）与 NX 方向一致性。
4. 次正规与 NaN 传播：`foadd` 的次正规输入/输出、sNaN ⇒ NV + canonical qNaN、qNaN 安静传播。

**签名槽（四方）与生成物同步**：同 008 —— 新检查点生成签名槽，四方逐槽比对；新增 `.S` 同步 `tests/inst.yaml` / `tests/case-ledger.tsv` / `tests/data/inst-signature/{expected.tsv,inputs.sha256}`。

## 验证

真实目标名（`check-inst`/`check-inst-sig` 均已退役，经 grep Makefile 确认）：

1. `make check-inst-asm` —— 全量 PASS，镜像数 = `tests/case-ledger.tsv` 现场派生一致；
2. `make check-idl` 与 `make check-idl-full`（四方逐槽一致）；
3. `make inst-signature-data` + `check_inst_sig.py --data-only` + `sha256sum -c .../inputs.sha256`；
4. `make check-tests-index`、`make check-case-ledger`、`make check-index-blobs`、`make check-inst-macro-scope`、`make check-knowledge-refs` 各 rc=0；
5. 证据脚本落「运行期证据目录内的 `run.sh`」，可达 FAIL ≥3 路「注入 → FAIL → `cp`+md5 还原 → 回绿」：① 改 min/max ±0 期望 ⇒ 红；② 删 `SIGUPD` ⇒ 槽未写红；③ 改一条 `.S` 内联期望 ⇒ 数据漂移红。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（按轮次追加）
