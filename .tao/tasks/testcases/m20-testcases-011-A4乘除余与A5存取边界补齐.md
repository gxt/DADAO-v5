# m20-testcases-011: A4 乘除余 + A5 load/store 边界补齐（除零/INT_MIN÷−1/商余关系；宽度/符号扩展/MALIGN/大端）

**模块**：testcases
**项目里程碑**：M20
**依赖**：`m20-testcases-010`（A9 双精浮点；本任务为同批共享写者链第 4 件）
**可并行分片**：否（与 `tests/inst` 共享生成物串行，见「共享写者」）
**预估**：5–8 h（口径同 008；含 A4 乘除余 + A5 存取两族）
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景

按 `m20-riscv-arch-test-porting.md` A4、A5 行缺口补乘除余与 load/store 边界意图。只移植**测试意图/边界值/判据**，不复制 riscv-arch-test 源码。DADAO 数据与指令字均为**大端序**（`SimRISC-00` 存储规则、`SimRISC-01 §1` 大端读），大端属原生特性、可移植。

## 共享写者（串行约束）

- 写 `tests/inst/**`、`tests/data/inst-signature/{expected.tsv,inputs.sha256}`、`tests/case-ledger.tsv`、`tests/inst.yaml`；
- 与 `m20-testcases-006`、`m20-infra-002` **串行**，不得并行；
- 本链内 `008 → 009 → 010 → 011 → 012` 逐件串行。

## 范围红线

- 不改 `spec/`、`.tao/contracts/`、引擎、`contracts/opcodes.yaml`；不复制 riscv-arch-test 源码；
- 期望值从 `spec/` 独立派生，不从 QEMU/LLVM/chipyard 实测反推；
- 「非对齐正例」不可移植（DADAO 要求自然对齐、未对齐为 MALIGN，`SimRISC-01 §1`）；ACT misaligned 正例不得硬造。

## 目标（自包含）

**op 与 spec 段（均已 grep 确认存在于 `contracts/opcodes.yaml` / `spec/`）**：

- `div.so_orrr_rd` / `div.uo_orrr_rd` / `rem.so_orrr_rd` / `rem.uo_orrr_rd` —— `SimRISC-04 §1.4`（除零/INT64_MIN÷−1 定值表、商余关系、符号）
- `ld.o_rrii_rd` / `ld.ub_rrii_rd` / `ld.sb_rrii_rd` / `ld.sw_rrii_rd` / `ld.st_rrii_rd` —— `SimRISC-01 §1`（宽度、符号/零扩展、对齐/MALIGN、大端）

**落点规则**：优先在 `tests/inst/04-arith-logic-octa/<op>.S`、`tests/inst/01-load-store/<op>.S` 追加检查点；除零/溢出定值专项可新增 `.S`（进 `tests/inst.yaml`）。**不设条数上限**，只列「必须覆盖的边界意图」。

**必须覆盖的边界意图（逐条，按缺口补齐）**：

1. 除零（§1.4 定值表）：`div.uo`/`div.so` 除零 ⇒ 定值全 1；`rem.uo`/`rem.so` 除零 ⇒ 被除数（`rem.uo` 零扩展写满 64 位、`rem.so` 符号扩展）。
2. INT64_MIN÷−1（§1.4 定值表）：`div.so` 溢出取定值；`rem.so` `INT64_MIN % −1` ⇒ 0。
3. 商余关系：`a = q×b + r`，`r` 符号 = 被除数符号（C99 truncate-toward-zero，§1.4）。
4. 符号：`.so`（有符号 truncate-toward-zero）与 `.uo`（无符号）对照。
5. load 宽度（§1）：`.o`/`.st`/`.sw`/`.ub`/`.sb` 的位宽截断；`.s` 符号扩展、`.u` 零扩展至 64 位。
6. 对齐/MALIGN（§1 对齐要求）：`.o` 需 8 字节、`.st`/`.sw` 需 4 字节；未对齐 ⇒ MALIGN；`.ub`/`.sb` 无对齐要求。
7. 大端（`SimRISC-00` 存储规则 + `SimRISC-01 §1` 大端读）：load 宽度 + 大端字节序判据（最低地址字节 = 最高有效字节）。

**签名槽（四方）与生成物同步**：同 008 —— 新检查点生成签名槽，四方逐槽比对；新增 `.S` 同步 `tests/inst.yaml` / `tests/case-ledger.tsv` / `tests/data/inst-signature/{expected.tsv,inputs.sha256}`。

## 验证

真实目标名（`check-inst`/`check-inst-sig` 均已退役，经 grep Makefile 确认）：

1. `make check-inst-asm` —— 全量 PASS，镜像数 = `tests/case-ledger.tsv` 现场派生一致；
2. `make check-idl` 与 `make check-idl-full`（四方逐槽一致）；
3. `make inst-signature-data` + `check_inst_sig.py --data-only` + `sha256sum -c .../inputs.sha256`；
4. `make check-tests-index`、`make check-case-ledger`、`make check-index-blobs`、`make check-inst-macro-scope`、`make check-knowledge-refs` 各 rc=0；
5. 证据脚本落「运行期证据目录内的 `run.sh`」，可达 FAIL ≥3 路「注入 → FAIL → `cp`+md5 还原 → 回绿」：① 改 INT64_MIN÷−1 定值期望 ⇒ 红；② 删 `SIGUPD` ⇒ 槽未写红；③ 改一条 `.S` 内联期望 ⇒ 数据漂移红。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（按轮次追加）
