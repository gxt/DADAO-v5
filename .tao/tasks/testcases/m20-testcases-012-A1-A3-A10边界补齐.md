# m20-testcases-012: A1–A3 + A10 边界补齐（进位/极值、移位量边界、分支极距、立即数拼装/PC 相对）

**模块**：testcases
**项目里程碑**：M20
**依赖**：`m20-testcases-011`（A4+A5；本任务为同批共享写者链第 5 件，末件）
**可并行分片**：否（与 `tests/inst` 共享生成物串行，见「共享写者」）
**预估**：6–8 h（口径同 008；含 A1/A2/A3/A10 四族，偏 8 h 上沿）
**档位**：大改（复核 ≤60 min）
**状态**：已验证

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

- `add.so_rrrr_rd` / `add.uo_rrrr_rd` —— `SimRISC-04 §1.1`（128 位和：`rdHA`=高 64 位、`rdHB`=低 64 位；`add.uo` 为零扩展、`rdHA`=0/1 进位；`add.so` 为符号扩展、`rdHA`=0 或全 1，**不是** 0/1 进位）
- `shl.o_orrr_rd` / `shr.so_orrr_rd` / `shr.uo_orrr_rd` —— `SimRISC-04 §2.2`（移位；N=63，shamt 0..63 全合法）
- `br.eq_rrii_rd`（及 `br.ne/br.n/br.nn/br.z/br.nz/br.p/br.np` 等）—— `SimRISC-06 §1`（条件跳转，imms14/20 = 编码偏移 <<2）
- `jump_iiii_rb`（及 `jump_rrii_rb`）—— `SimRISC-06 §2`（无条件跳转，imms26 = imms24<<2）
- `set.zw_rwii_rd` —— `SimRISC-03 §1`（16 位立即数赋值，wyde 写、其余 48 位全 0）
- `add.si_riii_rd` —— `SimRISC-04 §1.1`（加立即数，符号扩展）
- `aip.si_riii_rb` —— `SimRISC-05 §4`（IP 相对寻址，imms18 4KiB 块偏移符号扩展左移 12）

**落点规则**：优先在对应册 `<op>.S`（`04-arith-logic-octa/add.so_rrrr_rd.S`、`06-control-flow/br.eq_rrii_rd.S`、`03-wyde-imm/set.zw_rwii_rd.S` 等）追加检查点；跨族组合意图可新增 `.S`（进 `tests/inst.yaml`）。**不设条数上限**，只列「必须覆盖的边界意图」。

**必须覆盖的边界意图（逐族，按缺口补齐）**：

- A1 进位/极值（§1.1，已按 spec 订正）：`add.uo` 的 `rdHA`=进位（0/1）、`add.so` 的 `rdHA`=128 位符号扩展和的**高 64 位**（0 或全 1）、`rdHB`=低 64 位；极值（0+0、全 1+1、全 1+全 1）；源=目的原地（先读后写、128 位捕获）。
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

**测试结果**：`check-inst-asm` 274/274 镜像 PASS（635 故障例）；`check-idl` 274/274（idl,qemu）；`check-idl-full` 274/274 四方 PASS（一次通过，无 chipyard flake）；`--data-only` 4689 槽（新增 15 槽）、`sha256sum -c` 274 个 `.S` rc=0；`check-tests-index`/`check-case-ledger`/`check-index-blobs`/`check-inst-macro-scope`/`check-knowledge-refs` 各 rc=0；受影响 11 镜像定向四方 11/11。
**修改文件**：`tests/inst/04-arith-logic-octa/{add.so_rrrr_rd,add.uo_rrrr_rd,shl.o_orrr_rd,shr.so_orrr_rd,shr.uo_orrr_rd,add.si_riii_rd}.S`；`tests/inst/03-wyde-imm/set.zw_rwii_rd.S`；`tests/inst/06-control-flow/{br.eq_rrii_rd,br.ne_rrii_rd,jump_iiii_rb,jump_rrii_rb}.S`；`tests/data/inst-signature/{expected.tsv,inputs.sha256}`；`tests/case-ledger.tsv`（官方 `--write` 重生成）；运行期证据目录内 `run.sh`。未新增 `.S`，`tests/inst.yaml` 未改。
**验收结果**：新增 15 个链例检查点，按族：
- A1（4）：`add.so` 15（(-1)+2 ⇒ 高半 0、低半 1；与 `add.uo` 同操作数进位 1 对照）、16（0+0 覆盖全 1 旧值）；`add.uo` 14（全 1+2 ⇒ 进位 1、低半 1）、15（2^63+(2^63−1) ⇒ 进位 0、低半全 1）。
- A2（3）：`shl.o` 19（全 1<<63 ⇒ 仅 bit0 存活 0x8000..0）；`shr.so` 18 / `shr.uo` 18（同一 0x8000..>>1 ⇒ 0xC000../0x4000..，算术 vs 逻辑补位对照）。
- A3（6）：`br.eq` 13/14（imms12 最大 +2047/−2048 ⇒ 字节 +0x1FFC/−0x2000，实测落点 0x3BFC/0x1C10）；`br.ne` 13（−0x2000 ⇒ 落点 0x1C00）；`jump_iiii` 7/8（±0x2000 ⇒ 落点 0x3C00/0x1C20）；`jump_rrii` 7（基址 ENTRY+0x1D40 + rdHB=−0x100 ⇒ 落点 0x1C40）。均断言实际落点 IP，非仅编码。
- A10（2）：`set.zw` 15（wp0→wp1→wp3 连写后仅 0x3333000000000000 ⇒ 每次清其余 48 位、非插入）；`add.si` 15（0x10000+(−2)=0xFFFE ⇒ 负立即数跨 wyde 借位）。
- 定向四方槽数：add.so 16 / add.uo 15 / shl.o 19 / shr.so 18 / shr.uo 18 / add.si 15 / set.zw 15 / br.eq 14 / br.ne 13 / jump_iiii 8 / jump_rrii 7。
- 证据 `run.sh --inject` 5 路均「注入 ⇒ rc=1 ⇒ `cp`+md5 还原 ⇒ 回绿」：① expected.tsv `fe13a968…`→`8e4cbe05…`；② add.si `8d395dbd…`→`8a5d4eb0…`（镜像 rc=15）；③ inst_test.inc `2eee2fb9…`→`bb92e38b…`（槽未写）；④ br.eq `e0b86a1e…`→`53383453…`（rc=13，落点断言）；⑤ set.zw `95850127…`→`c86caeb4…`（rc=15）；还原后 md5 逐字节相符。
**新发现/坑**：（1）口径订正：`add.so` 的 `rdHA` 是 **128 位符号扩展和的高 64 位**（0 或全 1），不是 0/1 进位；0/1 进位只属 `add.uo`（`SimRISC-04 §1.1` 原文）。（2）`.o` 移位 shamt=N=63 全合法（`hd[5:0]`），越界 ILLI 只存在窄宽度 `.b/.w/.t`，本任务未硬造。（3）`aip.si` 既有 11 点已覆盖 0/±块/上下界/低位不清零/64 位全宽/覆盖写，按「不重复造」未加点。（4）`br.z`/`br.nz` 的 rd0 恒真/恒假等值边界既有覆盖，未重复。（5）`jump_iiii` 回向落点初版标签接错（点 8 rc=8），已改为独立落点标签并经四方复验。
**遗留问题**：未提交（architect 唯一提交权）；无其它遗留。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 11 个 `.S` 的 15 个新检查点及既有宏交互（未改宏层）：点号在每文件内 1..N 连续（`run_inst_tiny --scan-only` 全部 `pts_ok`，≤127）；每条期望按 `spec/SimRISC-03/04/05/06` 独立手算，并由证据脚本 oracle 现场重算（15 槽 + 3 个高半/进位派生）双路复核；跳转类断言均写「落点 IP == ENTRY+字面偏移」而非比对编码；未新增自定义 `TEST_FAULT_*`（沿用既有故障宏，仅顺延点号，规避 `ISS-m20-006`）；未动 `spec/`/`.tao/contracts/`/`contracts/opcodes.yaml`/引擎/`tests/inst.yaml`；生成物由官方 `--write` 重生成，与 `case-ledger` 双向对账通过。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `jump_iiii` 回向落点标签接错（首测点 8 rc=8） | ✅已修 | 0x1C20 落点改跳 `__jck_l`、0x3C00 跳 `__jck_f` | 定向四方槽 8 PASS；注入 4 证明落点断言可达 FAIL（rc=13） |
| 任务书/转述把 `add.so` 高半称「进位」 | ✅已核实（以 spec 为准） | 未改 spec；断言按 128 位符号扩展高半（0/全 1） | 四方 PASS；完成区「新发现」1 |
| 新点是否与既有覆盖重复 | ✅已核实 | 逐条对照既有 14/13/18/17/14/11 点，仅补未覆盖组合（同操作数 so/uo 对照、最大编码偏移、连写清零、负借位） | 完成区逐族列点 |
| `.o` 移位越界 ILLI 是否应补 | ❌不修（范围红线） | 未改 | `SimRISC-04 §2.2` 表：N=63、shamt 0..63 全合法 |

### 第 1 轮 reviewer 验收

**重跑记录**（全部由 reviewer 亲自执行，退出码取被检命令自身；验收前/后各记 `git status -uall` + 15 文件 md5 快照，两次逐行/逐字节相同）：

- 仓库根执行运行期证据目录内的 `run.sh --inject` ⇒ rc=0、`RESULT: PASS`：`check-inst-asm` rc=0（274/274）、`check-idl` rc=0（274/274）、定向四方 11/11（槽数 16/15/19/18/18/15/15/14/13/8/7 现场对账）、L1 五门控各 rc=0、独立 oracle（15 槽+3 派生）rc=0；注入 1–5 各 rc=1 → `cp`+md5 还原（md5 相等）→ 回绿 rc=0，注入点 md5 与完成区所列逐字节相符。
- `make check-idl-full` ⇒ rc=0；日志 `PASS=274 FAIL=0`、`四方一致 274/274`（一次通过，`ISS-m20-005` 未触发、无需重试）。
- **独立注入（reviewer，非脚本自检）**：改 `add.so` 点 15 高半期望 0→2 ⇒ `idl_four_way --platforms qemu --only add.so_rrrr_rd` rc=1、`[FAIL] add.so_rrrr_rd 槽 16 / rc {idl:15,qemu:15}`（高半 `__VERIFY_RD` 断言可达 FAIL、非恒真）；`cp` 还原（md5 `cfa8cb1b…` 相等、mtime 复原）⇒ rc=0 `[PASS] 槽 16`。
- 现场派生：274 镜像 / 635 故障例 / 4689 槽；`inst-signature-data` 重生成后 `expected.tsv`/`inputs.sha256`/`case-ledger.tsv` md5 不变；`--data-only` rc=0（4689 槽）、`sha256sum -c` rc=0（274 个 `.S`）；11 个改动 `.S` 的 `scan_source` 槽数 == 槽、`pts_ok`、故障例点号顺延正确；`check-tests-index`/`check-case-ledger`/`check-index-blobs`/`check-inst-macro-scope`/`check-knowledge-refs` 各 rc=0。

**约束核验**：

- 范围：`status` 恰 15 文件（任务书 + `case-ledger.tsv` + `expected.tsv`/`inputs.sha256` + 11 个 `.S`）、无 untracked；无 `spec/`/`.tao/contracts/`/`contracts/opcodes.yaml`/引擎/`tests/inst.yaml` 改动；未新增 `.S` ✓
- A1（重点）：按 `SimRISC-04 §1.1` 原文（`add.uo` ZX `rdHA`=0/1 进位；`add.so` SX `rdHA`=高 64 位）；add.so 15（(−1)+2 ⇒ 高 0/低 1）、16（0+0 覆盖全 1 旧值）、add.uo 14（全 1+2 ⇒ 进位 1）、15（2^63+(2^63−1) ⇒ 进位 0、低全 1）手算全对，高半走 `__VERIFY_RD` 断言（上列注入证明可达 FAIL）；任务书订正后 grep「65 位」无命中、无残留误导 ✓
- A3（重点）：`SimRISC-06 §1/§2` IDL 为 `ip()+disp`、`rb+rd+(imms12<<2)`；六处落点手算全对（0x1C00+0x1FFC=0x3BFC、0x3C10−0x2000=0x1C10、0x3C00−0x2000=0x1C00、0x1C00+0x2000=0x3C00、0x3C20−0x2000=0x1C20、ENTRY+0x1D40−0x100=ENTRY+0x1C40，ENTRY=0xffffff010100）；断言比 `aip.si` 实测落点 IP（非编码字）；负偏移落点标签配对无误（`__m_b_land`→14、`__m_f_land`→13、`__jb_land`→8、`__jf_land`→7、jump_rrii `__l7`→7）✓
- A2/A10：shamt 0（既有点 4/9/4）与 63、全 1<<63=0x8000..0、同一 0x8000..0>>1 ⇒ 0xC000..（so）/0x4000..（uo）、set.zw wp0→wp1→wp3 ⇒ 0x3333000000000000（`SimRISC-03 §1` 其余 48 位清 0）、0x10000+(−2)=0xFFFE 手算全对；`.o` 未硬造越界 ILLI（范围红线）✓
- `ISS-m20-006` 规避：未新增自定义 `TEST_FAULT_*`（仅既有宏顺延点号，`scan_source` 仍识别 635 例）✓；完成区 15 行 ≤30、无运行期路径、文件清单与 `status` 一致；`run.sh` 计数全部现场派生（274/4689）✓

**发现（文档级，不阻断）**：① `br.eq_rrii_rd.S` 段头注释「imms12 = ±2048」应为「+2047/−2048」（完成区已写对）；② 验收提示里 `shl.o 0x8000..<<63 = 0` 与实现操作数（全 1<<63 ⇒ 0x8000..0）不同，任务书文本与实现一致、shamt=63/0 边界均已覆盖，算术手算正确。

**判决：Accepted**
