# m20-testcases-008: A6 位操作边界补齐（clmul 高半/clmulr 组合、ctlz/cttz/ctpop 全 0/one-hot、rev/rol 组合）

**模块**：testcases
**项目里程碑**：M20
**依赖**：`m20-testcases-007`（riscv-arch-test 可移植清单评估，已合入；本任务按其中 A6 行「移植意图」与「不可移植清单」立项）
**可并行分片**：否（与 `tests/inst` 共享生成物串行，见「共享写者」）
**预估**：4–6 h（口径：同类最近 5 件「加 inst 向量」派单→合入实测中位数约 2.3 h；本任务按缺口补整族 + 四方槽，上浮）
**档位**：大改（复核 ≤60 min）
**状态**：已验证

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
2. clmulr 组合（DADAO 无 `clmulr` 指令）：**以 spec 为准**——`spec/SimRISC-04 §1.5` 原文 `clmulr(a,b) = rev(clmul(rev(a), rev(b)))`，按 64 位半展开即 `rev64(clmul_low(rev64 a, rev64 b))`、等价于 `(clmulh(a,b)<<1) | (clmull(a,b)>>63)`；用 `rev` 位反转 + `clmul.o` 高/低半组合表达，高半与低半分别独立断言（spec 独立推导，不引 ACT 代码）。原稿写作 ``clmulr(a,b) ≡ clmul(bitrev(a), b)`` 的**高半**，该恒等式错误（4 位反例 a=`0b1011`、b=`0b0110` ⇒ clmulr=`0b111`，该式给 `0b010`），已删去。
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

## 待裁定

- **clmulr 组合的恒等式口径**：任务书「目标 2」写作 `clmulr(a,b) ≡ clmul(bitrev(a), b)` 的**高半**。该式代数不成立（W=4 反例：a=`0b1011`、b=`0b0110` ⇒ clmulr=`0b111`，而 clmulh(rev a, b)=`0b010`；64 位数值亦反证）。`spec/SimRISC-04 §1.5` 原文为 `clmulr(a,b) = rev(clmul(rev(a), rev(b)))`，按 64 位半展开 = `rev64(clmull(rev64 a, rev64 b))`（与 `(clmulh<<1)|(clmull>>63)` 同值；含全 1/`2^63` 边界数值验证）。**已按 spec 版本实现**（未改 spec）。**主会话裁定：按 spec 原文接受，任务书已订正。**

## 完成区

**测试结果**：全绿——`check-inst-asm` 274/274 镜像；`check-idl` 274/274（idl,qemu）；受影响 6 镜像定向四方 6/6（idl,qemu,gem5,chipyard 逐槽）；`check-tests-index` / `check-case-ledger` / `check-index-blobs` / `check-inst-macro-scope` / `check-knowledge-refs` 均 rc=0；`inst-signature-data` 4605 槽（+14）、`--data-only` 与 `sha256sum -c` PASS
**修改文件**：`tests/inst/04-arith-logic-octa/{clmul.o_rrrr_rd,rev.o_orri_rd,rol.o_orrr_rd}.S`、`tests/inst/12-misc/{ctlz,cttz,ctpop}_orri_rd.S`、`tests/case-ledger.tsv`、`tests/data/inst-signature/{expected.tsv,inputs.sha256}`（未新增 `.S` ⇒ `tests/inst.yaml` 不动）
**验收结果**：证据脚本基线 + 3 路注入 rc=0：① 改 clmul 点 20 期望（md5 `f305…`→`f97d…`）⇒ 定向四方 rc=1，还原后 md5 `f305…`、rc=0；② 删 `__REC` 的 SIGUPD（md5 `2eee…`→`5b01…`）⇒ rc=1，还原 md5 `2eee…`、rc=0；③ 改 ctlz 点 19 期望（md5 `2276…`→`236c…`）⇒ 数据漂移 rc=1，还原 md5 `2276…`、rc=0；每路均验注入后 `git diff --name-only` 非空
**新发现/坑**：① 任务书 clmulr 恒等式与 spec 不一致（见「待裁定」，已订正为 spec 口径）；② 基线 `tests/case-ledger.tsv` 已漂移（HEAD 里 `11-cfx/escape_ciii_cfx.S` 的 **8 处宏调用**未入册；11 次出现 = 3 处宏定义 + 8 处调用；base `check-case-ledger` python 工具 rc=1、`make` 包装 rc=2 已现场取证），`--write` 一并吸收该既有漂移才转绿；③ 新增非 opcode 身份 `.S` 还需同步 `validate_vectors`/`check_tests_index` 的 `NON_ID_CARRIERS` 与 `idl/data/idl_exec_cases.toml`（本任务范围外）⇒ 选择在既有 op 载体追加，保持 op↔文件 1:1 与 127 上限
**遗留问题**：`make check-idl-full` 全量 274 例（nightly 成员、耗时过长）未跑；改用受影响 6 镜像的四方（idl/qemu/gem5/chipyard）覆盖，rc=0

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 任务书 clmulr 恒等式与 `SimRISC-04 §1.5` 不一致 | ❌不修（按 spec 实现） | `.S` 注释写明 spec 展开式；记「待裁定」 | 独立 oracle 三组含边界，rev(clmull(rev a,rev b)) 与 `(clmulh<<1)\|(clmull>>63)` 同值 |
| ctlz/cttz/ctpop 头注释「overlap（链例 N）」误改 | ✅已修 | 恢复为「链例 18」 | 重新 `inst-signature-data` + `--data-only`/`sha256sum -c` 绿 |
| 新检查点期望值正确性（未测输入/边界） | ✅已核对 | 14 个值全部由独立 GF(2)/rev/rol oracle 现场重算 | `oracle cases=14 mismatch=0` |
| 点号连续 / 每 id ≤127 | ✅已核对 | 链例续 1..N、故障例续 N+1..M | `validate-vectors` rc=0；最大 id 26 例 |
| 证据脚本首版解析 `-`（relation 槽）崩溃 | ✅已修 | `expected` 列 `-` → `None` | 基线重跑 rc=0 |
| 注入空注入假绿风险 | ✅已修 | md5 前后对比 + `git diff --name-only` 双检 | 3 路注入均打印「git diff 非空」与不同 md5 |

### 第 1 轮 reviewer 验收

**重跑记录（均本人执行，仓库根；判决只基于本人输出+退出码）**

- 范围：`git diff 399d16d3..201b1658 --name-only` = 10 文件（任务书 + `tests/case-ledger.tsv` + `tests/data/inst-signature/{expected.tsv,inputs.sha256}` + 6 个 `.S`）；`-- tests/inst.yaml` = 0 行；现场 `.S` 数 = `inputs.sha256` 条目 = 274；`expected.tsv` 4605 槽（基线 4591 ⇒ +14）。
- L1（逐条本人跑）：`check-tests-index` / `check-case-ledger` / `check-index-blobs` / `check-inst-macro-scope` / `check-knowledge-refs` 全 rc=0。
- L2：`make check-inst-asm` rc=0（`run_asm_suite: 274/274 镜像通过（… 635 例）`）；`make check-idl` rc=0（`check_four_way: 274/274 例四方一致（parties=idl,qemu）`）。
- 定向四方（本人命令 `idl/tools/idl_four_way.py --platforms qemu,gem5,chipyard --only <6 id>`）：rc=0，`6/6 例四方一致`；槽数 clmul 24 / rev 15 / rol 16 / ctlz 20 / cttz 20 / ctpop 19（共 114）。
- 证据脚本：仓库根执行运行期证据目录内的 `run.sh` ⇒ rc=0；`run.sh --inject` ⇒ rc=0（3 路注入均 md5 变 + `git diff` 非空 + rc=1，还原 md5 相等 + 回绿 rc=0）；计数现场派生（镜像 274 / 槽 4605，非写死）。
- 独立注入（本人，脚本未覆盖的点）：改 `tests/inst/04-arith-logic-octa/clmul.o_rrrr_rd.S` 的 `__VERIFY_RD 20` 期望末位（md5 `f305…`→`32c9…`）⇒ `idl_four_way --platforms qemu --only clmul.o_rrrr_rd` rc=1（`[FAIL] … rc {idl:20,qemu:20}`）；`cp` 还原（md5 回 `f305…`、`git diff` 空）⇒ rc=0（`1/1 例四方一致`）。
- 期望值独立派生：按 `SimRISC-04 §1.5/§2.2/§2.2.1/§2.2.2`、`SimRISC-12 §3` 独立脚本复算 21 项（clmulr 组合 3 槽 + 6 个 VERIFY + rev/rol/ctlz/cttz/ctpop 新槽）`mismatch=0`；未用 QEMU/gem5/chipyard 实测反推；14 行 `来源` 行号逐条对上 `.S` 现场。
- 基线 ledger（主工作树 master `a386f3f7`）：`python3 tools/infra/check_case_ledger.py` rc=1（`make` 包装 rc=2），失败恰为 `escape_ciii_cfx.S` 缺 8 行/多 8 行；本分支新增 8 行与该 `.S` 现场 8 处宏调用逐行一致，`check-case-ledger` 本分支 rc=0（现场 5797 == 清单）⇒ 基线修复非掩盖（`git show --stat` 无 Makefile/tools 改动）。

**约束核验**：未改 `spec/`、`.tao/contracts/`、`contracts/opcodes.yaml`、引擎、`tests/inst.yaml` ✅；无新增 `.S`（故不需 inst.yaml 条目）✅；链例/故障例点号连续、最大 id 26 <127 ✅；既有故障例仅改号未删（clmul 20,21→25,26 等）✅；完成区 5 行 ≤30、无运行期路径、修改文件与 `git show --stat` 逐条对齐 ✅；engineer 审阅记录 ≤40 行 ✅。

**Findings（不阻断，交 architect 收尾）**

1. 任务书「目标 2」`clmulr(a,b) ≡ clmul(bitrev(a),b)` 高半不成立：本人 4 位反例 a=`0b1011`、b=`0b0110` ⇒ clmulr(P>>3)=`0b111` 而 clmulh(bitrev a,b)=`0b010`；`SimRISC-04 §1.5` 原文 `clmulr = rev(clmul(rev a, rev b))` 反而成立（64 位三组含边界同值）⇒ engineer 按 spec 实现正确；**建议订正任务书该句为 spec 原文口径（不改 spec）**。
2. 完成区「新宏 11 处未入册」实为 8 行（11 = 3 处宏定义 + 8 处调用）；「base rc=1」对 python 工具成立、`make` 为 2 —— 文档级笔误。
3. ctpop 点 19（2^32⇒1）与既有 pt14（2^63⇒1）意图重复、rol 点 15 取模与既有 pt8（`0x41`⇒1）相近 ⇒ 过覆盖非缺口；rev「one-hot k∈{1,2,4,8,16,32}` 按 `encode_onehot`（k 为 one-hot）口径既有 pt3–8 已全覆盖。
4. `check-idl-full` 未跑（任务书验证 2 字面项），按派单改用 6 镜像定向四方，本人已独立重跑 6/6。

**判决：Accepted**（验收命令块在本人重跑下全部通过、约束无违反；4 项 finding 由 architect 处置）

