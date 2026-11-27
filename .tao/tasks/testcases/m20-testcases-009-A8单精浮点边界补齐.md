# m20-testcases-009: A8 单精浮点边界补齐（NaN/次正规/舍入/NX/OF/UF、转换饱和、FMA 单次舍入）

**模块**：testcases
**项目里程碑**：M20
**依赖**：`m20-testcases-008`（A6 位操作，链头；本任务为同批共享写者链第 2 件）
**可并行分片**：否（与 `tests/inst` 共享生成物串行，见「共享写者」）
**预估**：5–8 h（口径同 008；浮点四方含 gem5/chipyard 浮点实现差异风险，上浮到 8 h 上沿）
**档位**：大改（复核 ≤60 min）
**状态**：已验证

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
3. 舍入六档（`SimRISC-07 §1.1` 真实名）：静态 `0x01` RNE（就近取偶）、`0x02` RNA（就近、平局远离 0）、`0x04` RTZ、`0x08` RUP、`0x10` RDN；动态 `0x20` 读 `rf0[33:32]`（`00` RNE / `01` RTZ / `10` RDN / `11` RUP）。非六值之一（含 `0x00`）⇒ ILLI。
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

**测试结果**：`check-inst-asm` 274/274 PASS（635 例）；`check-idl` 274/274 PASS（IDL+QEMU）；`check-idl-full` 274/274 四方 PASS（首次 273/274：chipyard 对 ftadd 输出 0 字节且 rc=0，重试 1 次全绿，非槽值差）；受影响 4 镜像定向四方（idl,qemu,gem5,chipyard）各 1/1 PASS（ftadd 27 槽 / ftfma 31 / ftcls 23 / ft2ut 26）；`--data-only`、`sha256sum -c`、5 个 L1 门控 rc=0；独立 oracle 20/20。
**修改文件**：`tests/inst/07-floating-point/{ftadd_orrr_rf,ftfma_rrrr_rf,ftcls_orri_rf,ft2ut_orri_rf}.S`；`tests/data/inst-signature/{expected.tsv,inputs.sha256}`；`tests/case-ledger.tsv`（官方 `--write` 重生成）；运行期证据目录内 `run.sh`。
**验收结果**：新增 20 检查点（ftadd 9 / ftfma 7 / ftcls 3 / ft2ut 1）——NaN 优先与 canonical 化（qNaN+sNaN、负号/payload 归零、FMA 加数 NaN/sNaN、cls 的负 qNaN 与 payload sNaN）；次正规精确和（ftadd 3 点、fma 1 点）；溢出四象限（ftadd RUP/RDN 正负各 2 点）；FMA `0×−Inf`+qNaN、`Inf×Inf+(−Inf)`；tininess-after-rounding（`max_sub×(1+2^-23)=min_normal−2^-172`：RNE 只置 NX / RTZ 置 UF|NX）；无符号负向溢出饱和。证据 `run.sh --inject` 3 路均「注入⇒红⇒`cp`+md5 还原⇒回绿」（ft2ut `7c19d5e0…`→`9e0ab9ea…`；inst_test.inc `2eee2fb9…`→`5b018e96…`；ftadd `384854fc…`→`e8dc0dca…`；还原后 md5 逐字节相符）。
**新发现/坑**：（1）`check-idl-full` 的 chipyard 腿偶发「0 字节签名流、rc=0」（62 并发时），判为资源型 flake，原样重试 1 次即 274/274；（2）ftadd 的次正规和恒为 2^-149 整数倍 ⇒ 加法不可能产生 tiny-inexact，UF/tininess 用例必须落 FMA（精确积带低位）；（3）六档舍入与 `0x00` ILLI 在既有 ftrnd/转换用例已全覆盖，本任务未重复造点。
**遗留问题**：本分支未提交（按 `.opencode/agents/architect.md`「提交与文件集审核」，提交由 architect 执行）；chipyard 并发 flake 建议登记 issue（本任务未改引擎）。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 4 个 `.S` 的新增检查点与三份生成物：期望值全部由独立有理数 oracle（精确 Fraction + 手写 round-and-pack/饱和/分类）现算并与 `.S` 内联值、内联标志、`expected.tsv` 槽值三路对齐；沿用既有宏（ft 只写低 32、高 32 保留，无 NaN-boxing）；legality 点号顺延无遗漏（ftadd 19→28、ftfma 25→32、ftcls 21–24→24–27、ft2ut 26–29→27–30）；生成物无手改。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| ftadd 无法构造 UF（次正规和恒精确） | ✅已修 | UF/tininess 用例改落 ftfma 点 29/30 | 四方 PASS + oracle 20/20 |
| `check-idl-full` chipyard ftadd 0 字节（rc=0） | ✅已修 | 无代码改动，原样重试 | 重试 274/274 四方 PASS |

### 第 1 轮 reviewer 验收

**重跑记录（全部本审独立执行，rc=真实退出码，不采信完成区转述）**
- `check_inst_sig.py --data-only` ⇒ rc=0：`274 镜像 / 4625 槽（静态期望 4587 / 运行期关系 38）；数据与 case-ledger 对账一致`
- `sha256sum -c tests/data/inst-signature/inputs.sha256` ⇒ rc=0（274 个 `.S` + 10 个 `.inc/.lds` 全 OK）
- `make check-tests-index`/`check-case-ledger`（现场 5817 条）/`check-index-blobs`/`check-inst-macro-scope`/`check-knowledge-refs` ⇒ 各 rc=0；knowledge-refs 报 0 具体运行期路径引用
- `make check-inst-asm` ⇒ rc=0：`run_asm_suite: 274/274 镜像通过（274 个 id；链例 + 故障链 635 例）`
- `make check-idl` ⇒ rc=0：`274/274 例四方一致（parties=idl,qemu）`
- `make check-idl-full` ⇒ rc=0 ×3 次（第 1 次 + 本审复跑 2 次，均 `274/274（parties=idl,qemu,gem5,chipyard）`）
- 定向四方（ftadd/ftfma/ftcls/ft2ut，`qemu,gem5,chipyard`）⇒ rc=0：`4/4 例四方一致`，槽 27/31/23/26，与完成区一致
- 证据脚本（仓库根执行运行期证据目录内的 `run.sh --inject`）⇒ rc=0 `RESULT: PASS`；3 路注入均「注入⇒rc=1⇒`cp`+md5 还原⇒回绿」，注入/还原 md5 与完成区逐字节相符

**`check-idl-full` 偶发判定**：本审 3 次全量均 rc=0，另做低并发单镜像（chipyard、`--jobs 1`、ftadd）⇒ rc=0、`1/1 例四方一致`，无 0 字节流 ⇒ 判**偶发（资源型 flake）**，非稳定缺陷，不阻断；按完成区建议登记 issue。

**期望值独立派生**：本审另写独立有理数 oracle（Fraction + 手写 round-and-pack/四象限/tininess/饱和/分类，不读 `expected.tsv`、不跑平台），对 4 个 `.S` 全部 115 个可解析检查点（含 20 个新增）逐点复算 ⇒ **0 MISMATCH**。手工复核：canonical qNaN `0x7FC0_0000`；ftadd 21–23 次正规和精确 ⇒ 无 UF/NX；ftfma 29 精确积 = 2^-126 − 2^-172 ⇒ RNE 舍入后 = 最小正规 ⇒ 仅 NX，30 RTZ ⇒ UF|NX(0x18)；ftadd 24–27 溢出四象限与 `§1.3` 表逐格相符；ft2ut 26 负有限 ⇒ 0 + NV、无 NX；FMA `0×−Inf`+qNaN、`Inf×Inf+(−Inf)`、加数 qNaN/sNaN 与 `§2.5` 特例相符；既有 50 个 `.S` 内无同指令同输入重复点（跨指令同输入 ftadd19↔ftmin13、ft2ut26↔ft2uo25 不计）。

**独立注入（本审自做）**：改 `ftfma_rrrr_rf.S` 点 29 期望 `0x800000→0x800001`（注入前 md5 `62e81f87…`、mtime 17:34:56）⇒ `--data-only` rc=1（数据漂移）、四方 `--only ftfma_rrrr_rf` rc=1（`[FAIL] … rc {idl:29,qemu:29}`）；还原前复查 md5 仍为注入值 `c6ddca3a…` 再 `cp` ⇒ md5 回到 `62e81f87…` 逐字节相符 ⇒ 两项复跑 rc=0。

**约束核验**：① `git status -uall` 与开工快照逐行一致（8 个文件：任务书 + `case-ledger.tsv` + `expected.tsv`/`inputs.sha256` + 4 个 `.S`），无 `spec/`/契约/`opcodes`/引擎改动；未新增 `.S` ⇒ `tests/inst.yaml` 无需改（`check-tests-index` 现场对账通过）；② 期望值独立派生，非实测反推；③ 上列门控 rc 全 0；④ 证据脚本断言非恒真、计数现场派生（`IMAGES`/`SLOTS` 现场 `wc -l` = 274/4625，注入三路均有可达 FAIL）；⑤ 完成区 8 行 ≤30、无运行期路径，「修改文件」与 `git status` 对齐；⑥ `ft` 窄写红线：`__FP_CHECK` 对 `ft` 只取低 32 比对、高 32 不作规定，源值经 `set.fo` 装配，全篇无 NaN-boxing 位型。

**findings（均非阻断，交 architect 收尾处置）**：① 证据脚本注释写「21 个新边界检查点」而 `cases` 实为 20 条、完成区写 20 —— 注释笔误（判据取现场 `len(cases)`）；② 该脚本内 oracle 的 `round_f32` 按绝对值做 RUP/RDN（负值方向反），现有 20 条用例未命中该路径、不产生假绿，建议后续修正；③ ft2ut 点 26（−6.3e29 ⇒ 0+NV）与同文件点 15（−1.0 ⇒ 0+NV）意图重叠、输入与 `ft2uo` 点 25 相同（不同指令）——不设条数上限，判冗余不违规。

**判决：Accepted**（验收命令块在本审重跑下全部 rc=0、约束无违反；`check-idl-full` 按 ≥2 次复跑判偶发）
