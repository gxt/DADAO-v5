# m20-testcases-008: A6 位操作边界补齐（clmul 高半/clmulr 组合、ctlz/cttz/ctpop 全 0/one-hot、rev/rol 组合）

**模块**：testcases
**项目里程碑**：M20
**依赖**：`m20-testcases-007`（riscv-arch-test 可移植清单评估，已合入；本任务按其中 A6 行「移植意图」与「不可移植清单」立项）
**可并行分片**：否（与 `tests/inst` 共享生成物串行，见「共享写者」）
**预估**：4–6 h（口径：同类最近 5 件「加 inst 向量」派单→合入实测中位数约 2.3 h；本任务按缺口补整族 + 四方槽，上浮）
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景

`m20-testcases-007` 已评估：A 族多数「边界齐」，ACT 增量是**独立签名/寄存器字段组合**，不整族照搬。本任务按 A6 行缺口补位操作边界意图，只移植**测试意图/边界值/判据**，不复制 riscv-arch-test 源码。

## 共享写者（串行约束）

- 写 `tests/inst/**`、`tests/data/inst-signature/{expected.tsv,inputs.sha256}`、`tests/case-ledger.tsv`、`tests/inst.yaml`；
- 与 `m20-testcases-006`（cfx 测试向量/签名/四方迁移）、`m20-infra-002`（cfx 生成器/ledger/门控迁移）**串行**，不得并行；
- 本链内 `m20-testcases-008 → 009 → 010 → 011 → 012` 逐件串行。

## 范围红线

- 不改 `spec/`、`.tao/contracts/`、引擎、`contracts/opcodes.yaml`；不复制 riscv-arch-test 源码；
- 只移植测试意图/边界值/判据；DADAO 侧不可移植项（见 `m20-riscv-arch-test-porting.md`「不可移植清单」：Zbs `bset/bclr/binv/bext` 无 op、C 压缩、V 向量等）**不得硬造**；
- 期望值从 `spec/` 独立派生，不从 QEMU/LLVM/chipyard 实测反推。

## 目标（自包含）

**op 与 spec 段（均已 grep 确认存在于 `contracts/opcodes.yaml` / `spec/`）**：

- `clmul.o_rrrr_rd` —— `SimRISC-04 §1.5`（GF(2) 无进位乘，`{rdHA,rdHB}` 高/低 64 位）
- `ctlz_orri_rd` / `cttz_orri_rd` / `ctpop_orri_rd` —— `SimRISC-12 §3`（位扫描与位计数）
- `rev.o_orri_rd` —— `SimRISC-04 §2.2` + `§2.2.1`（`encode_onehot`：k 须 2 的幂且 k<64）
- `rol.o_orri_rd` / `rol.o_orrr_rd` —— `SimRISC-04 §2.2` + `§2.2.2`（`(x<<n)|(x>>((64-n)&63))`）

**落点规则**：优先在对应 op 的既有 `tests/inst/04-arith-logic-octa/<op>.S`（`clmul.o_rrrr_rd.S` 等）**追加检查点**，保持 op↔文件一一对应；跨 op 组合意图（clmulr 组合、rev/rol 组合）可新增专项 `.S`（文件名按「op 组合 + 意图」命名），新增 `.S` 须进 `tests/inst.yaml` 新条目。**不设条数上限**，只列「必须覆盖的边界意图」。

**必须覆盖的边界意图（逐条，按缺口补齐；现有 21/22 点若已覆盖则跳过、不重复）**：

1. clmul 高半/低半独立校验：`{rdHA,rdHB}=clmul(rdHC,rdHD)`，高半 `rdHA` 与低半 `rdHB` 分别断言；`{rd0,rdN}` 丢弃高半只留低半、`{rdN,rd0}` 丢弃低半只留高半。
2. clmulr 组合（DADAO 无 `clmulr` 指令）：`clmulr(a,b) ≡ clmul(bitrev(a), b)` 的**高半**；用 `rev` 位反转 + `clmul.o` 高半组合表达，断言组合判据与 clmul.o 高半语义一致（spec 独立推导，不引 ACT 代码）。
3. ctlz：全 0 输入 ⇒ 定值 64；one-hot 输入（`2^k`）⇒ 定值 `63−k`；最高位/最低位定值。cttz：全 0 ⇒ 64；one-hot ⇒ `k`。ctpop：全 0 ⇒ 0、全 1 ⇒ 64、one-hot ⇒ 1（§3 定值表）。
4. rev：one-hot `k∈{1,2,4,8,16,32}` 单元反转（64/k 个单元序反转、单元内位序不变）；`k` 非 one-hot 或 `k=0` ⇒ ILLI（§2.2.1 `encode_onehot`）。
5. rol：旋转量 0（原值）、63、边界；`orrr` 形式 `hd[5:0]` 取模（等价 `mod 64`）；`orri` 形式 `immu6` 0..63 全合法、无越界值（§2.2.2）。
6. 源=目的原地（先读后写）；`rd0` 源读出 0。

**签名槽（四方：idl/qemu/gem5/chipyard）与生成物同步**：

- 每个新检查点由 `__CHECK_RD`/`__VERIFY_RD`/`TEST_*` 等宏生成签名槽，四方各自运行同一镜像，槽值对 `tests/data/inst-signature/expected.tsv` 逐槽比对（`check-idl-full`）；
- 新增 `.S` 须同步：`tests/inst.yaml`（新 `inst-<册>-nnn` 条目，`platforms: [system]`、`level: full`、`requires: []`）、`tests/case-ledger.tsv`（`python3 tools/infra/check_case_ledger.py --write`）、`tests/data/inst-signature/{expected.tsv,inputs.sha256}`（`make inst-signature-data` 重生成，逐行带 `文件:行` 来源）。

## 验证

真实目标名（`check-inst`/`check-inst-sig` 均已退役，经 grep Makefile 确认）：

1. `make check-inst-asm`（L2，`.S` 载体全量、单平台 QEMU 执行）—— 全量 PASS，镜像数 = `tests/case-ledger.tsv` 现场派生一致；
2. `make check-idl`（IDL+QEMU 槽比对）与 `make check-idl-full`（四方 idl/qemu/gem5/chipyard 逐槽一致）；
3. `make inst-signature-data` + `python3 tools/testcases/inst/check_inst_sig.py --data-only`（数据无漂移）+ `sha256sum -c tests/data/inst-signature/inputs.sha256`；
4. `make check-tests-index`、`make check-case-ledger`、`make check-index-blobs`、`make check-inst-macro-scope`、`make check-knowledge-refs` 各 rc=0；
5. 证据脚本落「运行期证据目录内的 `run.sh`」，要求可达 FAIL ≥3 路且「注入 → FAIL → `cp`+md5 还原 → 回绿」：① 改一条派生期望值（spec 期望）⇒ 四方槽红；② 删一个 `SIGUPD` ⇒ 槽未写红；③ 改一条边界值的 `.S` 内联期望 ⇒ 数据漂移红。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（按轮次追加）
