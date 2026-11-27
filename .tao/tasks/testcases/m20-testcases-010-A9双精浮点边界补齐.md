# m20-testcases-010: A9 双精浮点边界补齐（FMA 单次舍入、min/max ±0/NaN、溢出方向）

**模块**：testcases
**项目里程碑**：M20
**依赖**：`m20-testcases-009`（A8 单精浮点；本任务为同批共享写者链第 3 件）
**可并行分片**：否（与 `tests/inst` 共享生成物串行，见「共享写者」）
**预估**：5–8 h（口径同 008；浮点四方含 gem5/chipyard 差异风险）
**档位**：大改（复核 ≤60 min）
**状态**：已验证

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

**测试结果**：`check-inst-asm` 274/274 PASS（635 例）；`check-idl` 274/274（IDL+QEMU）；`check-idl-full` 274/274 四方 PASS（一次通过，无 chipyard flake）；受影响 5 镜像定向四方各 1/1（idl,qemu,gem5,chipyard）：foadd 27 槽 / fofma 33 / fomin 21 / fomax 21 / fornd 31；`--data-only` 4648 槽、`sha256sum -c` 274 `.S`、5 个 L1 门控 rc=0；独立 oracle 23/23。
**修改文件**：`tests/inst/07-floating-point/{foadd_orrr_rf,fofma_rrrr_rf,fomin_orrr_rf,fomax_orrr_rf,fornd_orri_rf}.S`；`tests/data/inst-signature/{expected.tsv,inputs.sha256}`；`tests/case-ledger.tsv`（官方 `--write` 重生成）；运行期证据目录内 `run.sh`。
**验收结果**：新增 23 检查点（foadd 9 / fofma 9 / fomin 1 / fomax 1 / fornd 3）。按边界意图：① foadd——负号带 payload qNaN ⇒ canonical 正 qNaN；次正规输入/输出精确（2^-1073 输出、进位到最小正规、和入正规区）；`1.0+minsub` RUP ⇒ 1+2^-52 只置 NX（粘位未丢）；溢出四象限补齐（正 RUP/RDN、负 RDN/RUP，溢出 ≠ Inf）。② fofma——`0×−Inf+qNaN` ⇒ NV（符号无关、无效优先）；加数 sNaN ⇒ NV、加数负 qNaN ⇒ canonical；次正规精确输出与最小正规进位；负溢出 RDN/RTZ/RUP 与正溢出 RDN，OF|NX 且按方向落 ±Inf/±max。③ min/max——b 源 sNaN 分支（结果为数仍置 NV，不置 NX/OF/UF）。④ fornd——动态 0x20 的 qNaN/sNaN canonical 化不置 NX、sNaN 只置 NV；RUP 下 −0.5 ⇒ −0。既有已覆盖项（§2.5 单次舍入反例点 4、±0 定序 7/8、双 NaN canonical 12/13、UF 方向 22/23）未重复造。证据 `run.sh --inject` 3 路均「注入⇒rc=1⇒`cp`+md5 还原⇒回绿」：expected.tsv `87d8a636…`→`eaf00611…`、inst_test.inc `2eee2fb9…`→`5b018e96…`、foadd `404d3eff…`→`0cd1adcd…`，还原后 md5 逐字节相符。
**新发现/坑**：（1）`check-idl-full` 本次 62 并发 274/274 一次通过，`ISS-m20-005` 的 chipyard 0 字节 flake 未复现（不据此排除，定向仍用 `--jobs 1`）；（2）双精同 009：`foadd` 次正规和恒为 2^-1074 整数倍 ⇒ 加法不能产生 tiny-inexact，UF/NX 方向只能落 `fofma`；（3）证据脚本 oracle 的 RUP/RDN 按有符号语义（负值取整方向相反），并内置「负溢出 RUP=−max / RDN=−Inf 必须不同」自检，避免 009 的 `round_f32` 方向 bug；（4）未新增 `.S`、未改 `tests/inst.yaml`：缺口均可追加进既有 op 载体，`check-tests-index` 双向对账通过。
**遗留问题**：本分支未提交（按 `.opencode/agents/architect.md`「提交与文件集审核」，提交由 architect 执行）。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 5 个 `.S` 的 23 个新增点与三份生成物：点号在每个文件内 1..N 连续且唯一（foadd 28 / fofma 34 / fomin 22 / fomax 22 / fornd 35，含故障点）；期望值由独立有理数 oracle（精确 Fraction + 按符号方向的 round-and-pack）现算，并与项目 spec oracle（`fp_spec_arith/minmax/rnd`）双路对照一致；槽号 = 检查点序（故障点不占槽），`--data-only` 与 case-ledger 现场对账一致；未动 `spec/`/契约/`opcodes`/引擎。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| foadd 缺次正规输入/输出与溢出剩余象限；fofma 缺 `0×−Inf`/加数 NaN/负溢出；min/max 缺 b 源 sNaN 分支；fornd 动态档 NaN 不置 NX 未覆盖 | ✅已修 | 追加 23 点（foadd 9 / fofma 9 / fomin 1 / fomax 1 / fornd 3） | 5 镜像四方 PASS；oracle 23/23 |
| 009 证据脚本 `round_f32` 对负数 RUP/RDN 方向反 | ✅已修 | 本脚本 `round_f64` 按符号取方向，并加手写负溢出自检 | `run.sh --inject` 全 PASS；负值 RUP/RDN 结果不同 |
| chipyard 62 并发 0 字节流偶发 | ✅已处置（非本任务缺陷） | 无代码改动；定向四方一律 `--jobs 1`，若再现按 flake 口径原样重试 1 次 | `check-idl-full` 一次 274/274，未复现 |

**判决**：所有 finding 已处置，任务标「待验收」。

### 第 1 轮 reviewer 验收

**重跑记录（reviewer 本机实跑，退出码原样）**

- 范围：`git status -uall` = 9 行（任务书 + `case-ledger.tsv` + `expected.tsv`/`inputs.sha256` + 5 个 `.S`）；无 `spec/`/契约/`opcodes`/引擎改动；无新增 `.S`（`inst.yaml` 已含 5 op），`make inst-signature-data` rc=0 且再生成后三份生成物 md5 逐字节不变 ⇒ `tests/inst.yaml` 无需改。
- L1 五门控 rc 全 0：`check-tests-index`（503 条）/ `check-case-ledger`（现场 5840 条）/ `check-index-blobs` / `check-inst-macro-scope` / `check-knowledge-refs`。
- 数据：`check_inst_sig.py --data-only` rc=0「274 镜像 / 4648 槽」；`sha256sum -c inputs.sha256` rc=0（274 个 `.S` 条目 == `find tests/inst -name '*.S'` 现场 274）。
- L2/L3：`check-inst-asm` rc=0「274/274 镜像通过（635 例）」；`check-idl` rc=0「274/274 例四方一致（idl,qemu）」；`check-idl-full` rc=0（一次通过，无 flake）「274/274 例四方一致（idl,qemu,gem5,chipyard）」。
- 定向四方（`idl_four_way.py --platforms qemu,gem5,chipyard --jobs 1 --only …`，逐条 rc=0）：foadd 槽27 / fofma 槽33 / fomin 槽21 / fomax 槽21 / fornd 槽31，均「1/1 … {idl:0,qemu:0,gem5:0,chipyard:0}」——与完成区数字逐一对上。
- 证据脚本：仓库根执行运行期证据目录内的 `run.sh --inject` rc=0，oracle `cases=23 mismatch=0`，三路注入各自「md5 变 ⇒ rc=1 ⇒ `cp` 还原 md5 相符 ⇒ rc=0」（`87d8a636…`/`2eee2fb9…`/`404d3eff…` 三组与我方快照一致）。
- reviewer 独立注入：`expected.tsv` 的 fornd 槽31 期望 `0x8000…`→`0x0000…`（注入前 `cp` 备份并记 mtime；md5 `87d8a636…`→`bd673f76…`）⇒ 同一 `run.sh` rc=1（data-only / check-idl / fourway.fornd / oracle 四处红）；还原前复核备份 md5 相符后 `cp` 回（`87d8a636…`）⇒ 重跑 rc=0 回绿。
- 快照对账：注入前后 `git status --porcelain -uall` 与 9 个目标文件 md5 与开工快照 **逐行/逐字节相同**（两次 `diff` 均空）。

**约束核验**

① 范围红线守住：git status 无 `spec/`/契约/`opcodes`/引擎/`inst.yaml`；② 期望值独立派生：23 点按 `SimRISC-07 §1.3/§2.1/§2.3/§2.4/§2.5` 手算复核——minsub+minsub=2^-1073、maxsub+minsub=最小正规、maxsub+maxsub=0x001FFFFFFFFFFFFE 均精确、无 UF/NX；`1.0+minsub` RUP ⇒ 1+2^-52 仅 NX；溢出四象限按 §1.3/§2.5 表 `OF|NX` 落 ±Inf/±max；`0×−Inf+qNaN` ⇒ NV、加数 sNaN ⇒ NV、`−fo_max×2` 的 RDN/RTZ/RUP 与 `+fo_max×2` 的 RDN 与表逐行相符；min/max 的 (−0,+0) 与单 NaN/sNaN 按 §2.4 第 2/4/6 条；fornd 动态档 NaN 不置 NX、静态 RUP −0.5 ⇒ −0 按 §2.3；未用平台实测反推 ✅；与既有点无重复（fofma 新增符号无关 0×Inf/加数 NaN/负溢出，min/max 新增 b 源 sNaN 分支，fornd 新增动态档 NaN，既有均为静态档）✅；③ 上列门控 rc 全 0 ✅；④ 脚本断言可达 FAIL、计数现场派生（`find`/`expected.tsv` 行数/awk 现取槽数）✅；⑤ 负数 RUP/RDN 方向有内置自检（负溢出 RUP=−max ≠ RDN=−Inf 断言）✅；⑥ 完成区 7 行 ≤30、无运行期路径、「修改文件」与 `git status` 对齐（任务书自身不列入，沿 008/009 惯例）✅。

**非阻断观察**：fornd 点31 用静态档 `0x08` 验「−0.5 ⇒ −0」，未与动态档 `0x20` 组成单点；该两条子意图（动态档 NX 规则、取整为 0 保符号）已由点 8/9/27/28/29/30/31 分别覆盖，不判返工，供架构师定夺是否补点。

**判决**：**Accepted**——验收命令块在我自己的重跑下全部 rc=0、独立注入可达 FAIL 并还原回绿、任务硬约束逐条守住；完成区每个数字与我实跑一致，无转述失真。
