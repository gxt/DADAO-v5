# m20-testcases-012: A1–A3 + A10 边界补齐（进位/极值、移位量边界、分支极距、立即数拼装/PC 相对）

**模块**：testcases
**项目里程碑**：M20
**依赖**：`m20-testcases-011`（A4+A5；本任务为同批共享写者链第 5 件，末件）
**可并行分片**：否（与 `tests/inst` 共享生成物串行，见「共享写者」）
**预估**：6–8 h（口径同 008；含 A1/A2/A3/A10 四族，偏 8 h 上沿）
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景

按 `m20-riscv-arch-test-porting.md` A1、A2、A3、A10 行缺口补加减/移位/分支/立即数边界意图。只移植**测试意图/边界值/判据**，不复制 riscv-arch-test 源码。四族分属 `04-arith-logic-octa`、`06-control-flow`、`03-wyde-imm`、`05-arith-addr` 四册，共享 `tests/inst` 生成物，故合为一件但逐族落地。

## 共享写者（串行约束）

- 写 `tests/inst/**`、`tests/data/inst-signature/{expected.tsv,inputs.sha256}`、`tests/case-ledger.tsv`、`tests/inst.yaml`；
- 与 `m20-testcases-006`、`m20-infra-002` **串行**，不得并行；
- 本链内 `008 → 009 → 010 → 011 → 012` 逐件串行。

## 范围红线

- 不改 `spec/`、`.tao/contracts/`、引擎、`contracts/opcodes.yaml`；不复制 riscv-arch-test 源码；
- 期望值从 `spec/` 独立派生，不从 QEMU/LLVM/chipyard 实测反推；
- **移位越界 ILLI 不可硬造到 `.o`**：`shl.o`/`shr.so`/`shr.uo` 的 N=63、shamt 0..63 全合法、`hd[5:0]` 全有效（`SimRISC-04 §2.2` 表），无越界；「越界 ILLI」仅窄宽度（`.b/.w/.t`，N=7/15/31，`SimRISC-08/09/10`）成立，若列为缺口须用窄宽度 op，不写进 64 位 `.o`。

## 目标（自包含）

**op 与 spec 段（均已 grep 确认存在于 `contracts/opcodes.yaml` / `spec/`）**：

- `add.so_rrrr_rd` / `add.uo_rrrr_rd` —— `SimRISC-04 §1.1`（65 位加：`rdHA`=进位/借位、`rdHB`=结果低 64 位）
- `shl.o_orrr_rd` / `shr.so_orrr_rd` / `shr.uo_orrr_rd` —— `SimRISC-04 §2.2`（移位；N=63，shamt 0..63 全合法）
- `br.eq_rrii_rd`（及 `br.ne/br.n/br.nn/br.z/br.nz/br.p/br.np` 等）—— `SimRISC-06 §1`（条件跳转，imms14/20 = 编码偏移 <<2）
- `jump_iiii_rb`（及 `jump_rrii_rb`）—— `SimRISC-06 §2`（无条件跳转，imms26 = imms24<<2）
- `set.zw_rwii_rd` —— `SimRISC-03 §1`（16 位立即数赋值，wyde 写、其余 48 位全 0）
- `add.si_riii_rd` —— `SimRISC-04 §1.1`（加立即数，符号扩展）
- `aip.si_riii_rb` —— `SimRISC-05 §4`（IP 相对寻址，imms18 4KiB 块偏移符号扩展左移 12）

**落点规则**：优先在对应册 `<op>.S`（`04-arith-logic-octa/add.so_rrrr_rd.S`、`06-control-flow/br.eq_rrii_rd.S`、`03-wyde-imm/set.zw_rwii_rd.S` 等）追加检查点；跨族组合意图可新增 `.S`（进 `tests/inst.yaml`）。**不设条数上限**，只列「必须覆盖的边界意图」。

**必须覆盖的边界意图（逐族，按缺口补齐）**：

- A1 进位/极值（§1.1）：`add.so`/`add.uo` 的 `rdHA`=进位（`sum[64]`）、`rdHB`=低 64 位；65 位加/减（借位 = 被减数<减数 ⇒ 1）；极值（0+0、全 1+1、全 1+全 1）；源=目的原地（先读后写、65 位捕获）。
- A2 移位量边界（§2.2）：`shl.o`/`shr.so`/`shr.uo` 的 shamt=0（原值）、shamt=63（边界）；符号扩展（`shr.so` 高位补 `rdHC[63]`）vs 零扩展（`shr.uo`）；`orrr` 形式 `hd[5:0]` 全有效。越界 ILLI 见「范围红线」（不写 `.o`）。
- A3 分支极距（§1/§2）：`br.eq` 前向/后向、正/负最大偏移（编码偏移 <<2）；等值边界（`rd0` 源读出 0 ⇒ `br.z` 恒真/`br.nz` 恒假，§1 特例）；`jump_iiii_rb` 相对（imms24<<2）、`jump_rrii_rb` 绝对（`rbHA+rdHB+(imms12<<2)`）。
- A10 立即数拼装/PC 相对（§1/§4）：`set.zw` 16 位分片拼 64 位（wpN 选 wyde、其余 48 位全 0）；`add.si` 负立即数（符号扩展）；`aip.si` PC 相对（4KiB 块偏移符号扩展左移 12、64 位全宽加 `ip()`）。

**签名槽（四方）与生成物同步**：同 008 —— 新检查点生成签名槽，四方逐槽比对；新增 `.S` 同步 `tests/inst.yaml` / `tests/case-ledger.tsv` / `tests/data/inst-signature/{expected.tsv,inputs.sha256}`。

## 验证

真实目标名（`check-inst`/`check-inst-sig` 均已退役，经 grep Makefile 确认）：

1. `make check-inst-asm` —— 全量 PASS，镜像数 = `tests/case-ledger.tsv` 现场派生一致；
2. `make check-idl` 与 `make check-idl-full`（四方逐槽一致）；
3. `make inst-signature-data` + `check_inst_sig.py --data-only` + `sha256sum -c .../inputs.sha256`；
4. `make check-tests-index`、`make check-case-ledger`、`make check-index-blobs`、`make check-inst-macro-scope`、`make check-knowledge-refs` 各 rc=0；
5. 证据脚本落「运行期证据目录内的 `run.sh`」，可达 FAIL ≥3 路「注入 → FAIL → `cp`+md5 还原 → 回绿」：① 改进位期望 ⇒ 红；② 删 `SIGUPD` ⇒ 槽未写红；③ 改一条 `.S` 内联期望 ⇒ 数据漂移红。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（按轮次追加）
