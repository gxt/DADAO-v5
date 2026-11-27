# m20-testcases-011: A4 乘除余 + A5 load/store 边界补齐（除零/INT_MIN÷−1/商余关系；宽度/符号扩展/MALIGN/大端）

**模块**：testcases
**项目里程碑**：M20
**依赖**：`m20-testcases-010`（A9 双精浮点；本任务为同批共享写者链第 4 件）
**可并行分片**：否（与 `tests/inst` 共享生成物串行，见「共享写者」）
**预估**：5–8 h（口径同 008；含 A4 乘除余 + A5 存取两族）
**档位**：大改（复核 ≤60 min）
**状态**：已验证

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
6. 对齐/MALIGN（§1 对齐要求，原文口径）：`.o` 需 8 字节；`.st`/`.t`/`.ut` 需 4 字节；`.sw`/`.w`/`.uw` 需 2 字节；`.ub`/`.sb` 无对齐要求。未对齐 ⇒ MALIGN。
7. 大端（`SimRISC-00` 存储规则 + `SimRISC-01 §1` 大端读）：load 宽度 + 大端字节序判据（最低地址字节 = 最高有效字节）。

**签名槽（四方）与生成物同步**：同 008 —— 新检查点生成签名槽，四方逐槽比对；新增 `.S` 同步 `tests/inst.yaml` / `tests/case-ledger.tsv` / `tests/data/inst-signature/{expected.tsv,inputs.sha256}`。

## 验证

真实目标名（`check-inst`/`check-inst-sig` 均已退役，经 grep Makefile 确认）：

1. `make check-inst-asm` —— 全量 PASS，镜像数 = `tests/case-ledger.tsv` 现场派生一致；
2. `make check-idl` 与 `make check-idl-full`（四方逐槽一致）；
3. `make inst-signature-data` + `check_inst_sig.py --data-only` + `sha256sum -c .../inputs.sha256`；
4. `make check-tests-index`、`make check-case-ledger`、`make check-index-blobs`、`make check-inst-macro-scope`、`make check-knowledge-refs` 各 rc=0；
5. 证据脚本落「运行期证据目录内的 `run.sh`」，可达 FAIL ≥3 路「注入 → FAIL → `cp`+md5 还原 → 回绿」：① 改 INT64_MIN÷−1 定值期望 ⇒ 红；② 删 `SIGUPD` ⇒ 槽未写红；③ 改一条 `.S` 内联期望 ⇒ 数据漂移红。

## 待裁定

1. **副作用类故障宏的清单覆盖**：`TEST_FAULT_LD_MALIGN_KEEPDST` / `TEST_FAULT_ST_MALIGN_KEEPMEM` 不在 `run_inst_tiny.scan_source` 的既有正则内 ⇒ 不进 `faults` 清单，因而既不进 `case-ledger` 身份清单、也不进「635 例」计数（删除哨兵不守护这 6 行）。`CASE_N` 单例序号仍可用（`__FAULT_BODY_BEGIN` 自带 `.if CASE_N == \pt`；实测 `CASE_N=27` rc=0）。**主会话裁定：登记 `ISS-m20-006`（扫描器盲区），是否扩展 `run_inst_tiny.scan_source` 由后续任务决定，本任务不阻断。**
2. **`.sw` 对齐口径**：原任务书写「`.st`/`.sw` 4 字节」，`spec/SimRISC-01 §1` 与既有用例为 `.st`/`.t`/`.ut` 4 字节、`.sw`/`.w`/`.uw` 2 字节。**主会话裁定：以 spec 为准，本条已订正；engineer 按 spec 落地正确。**

## 完成区

**测试结果**：`check-inst-asm` 274/274 镜像 PASS（635 例）；`check-idl` 274/274（idl,qemu）；`check-idl-full` 274/274 四方 PASS（一次通过，无 chipyard flake）；受影响 12 镜像定向四方各 1/1（idl,qemu,gem5,chipyard）：div.so 18 槽 / div.uo 18 / rem.so 18 / rem.uo 17 / ld.o 22 / ld.st 22 / ld.sw 23 / ld.ub 25 / ld.sb 23 / st.o 22 / st.t 21 / st.w 25；`--data-only` 4674 槽、`sha256sum -c` 274 `.S`、5 个 L1 门控 rc=0；独立 oracle 26/26。
**修改文件**：`tests/inst/04-arith-logic-octa/{04-arith-logic-octa.inc,div.so_orrr_rd.S,div.uo_orrr_rd.S,rem.so_orrr_rd.S,rem.uo_orrr_rd.S}`；`tests/inst/01-load-store/{01-load-store.inc,ld.o_rrii_rd.S,ld.st_rrii_rd.S,ld.sw_rrii_rd.S,ld.ub_rrii_rd.S,ld.sb_rrii_rd.S,st.o_rrii_rd.S,st.t_rrii_rd.S,st.w_rrii_rd.S}`；`tests/data/inst-signature/{expected.tsv,inputs.sha256}`；`tests/case-ledger.tsv`（官方 `--write` 重生成）；运行期证据目录内 `run.sh`。未新增 `.S`，`tests/inst.yaml` 未改。
**验收结果**：新增 26 链例检查点 + 6 故障例（均为无签名槽的副作用核对例）。按边界意图：① 除零定值——div.uo 18（rd0 作除数、被除数高位置 1）、rem.so 18（正被除数）、rem.uo 17（被除数 = 2^63，零扩展写满）；div.so/rem.so 负被除数除零既有第 8 点。② INT64_MIN÷−1——既有 div.so 9 / rem.so 9 已覆盖，未重复。③ 商余关系——div.so 16/17、div.uo 17 用 `mul.uo`+`add.uo` 现场重算 `a=q×b+r`，q/r 另按 C99 truncate-toward-zero 独立重算；含 |a|<|b| 与 r 符号随被除数。④ .so/.uo 对照——div.so 18 vs div.uo 16、rem.so 16 vs rem.uo 15（同一 64 位位型，结果 -3/-1 vs 大数/1）。⑤ 宽度/扩展——同一数据单元 0x0102030405060708：ld.ub 22-25、ld.sb 22/23（0x88 零扩展 vs 符号扩展）、ld.sw 22/23、ld.st 22、ld.o 22。⑥ MALIGN 无副作用——ld.o 27/ld.st 26/ld.sw 27（异常进入且不写目的）、st.o 27/st.t 24/st.w 28（不写目标数据单元）：把 hmon 返回槽改成用例核对点，核完跳回公共落点，仍按 cause one-hot 判异常已进入；四方均一致。⑦ 大端——上述跨宽度同一单元给出字节级嵌套证据；st.w 22 写 0xBEEF 后 23/24 用 ld.ub 读 0xBE/0xEF、25 用 ld.sw 读 0xFFFF…BEEF。证据 `run.sh --inject` 5 路均「注入⇒rc=1⇒`cp`+md5 还原⇒回绿」：expected.tsv `9c3a7770…`→`b56ac044…`、inst_test.inc `2eee2fb9…`→`5b018e96…`、ld.st `2732fbd7…`→`a39c91d8…`、04 册 inc `66f5bf1d…`→`d7459a46…`、01 册 inc `4fa21c89…`→`2ccb8c64…`，还原后 md5 逐字节相符；后两路分别证明「商余关系断言」「MALIGN 副作用断言」可达 FAIL。
**新发现/坑**：（1）用户口径写「`.st/.sw` 4 字节对齐」，`spec/SimRISC-01 §1` 实为 `.st` 4/`.sw` 2，既有用例（0x001 越界例、0x006 合法例）与四方实测一致 ⇒ 本任务按 spec 落地 `.sw` 用奇数偏移。（2）「除零/溢出逐宽度」在 04 册仅 `.o` 适用；`.st/.ut/.sw/.uw/.sb/.ub` 已由 08/09/10 册既有用例覆盖（grep 每宽度均含除零与溢出定值），按范围红线未改。（3）自定义故障宏（`TEST_FAULT_*_MALIGN_KEEP*`）不被 `run_inst_tiny.scan_source` 的既有正则识别 ⇒ 不占 `CASE_N` 单例序号、不进 `case-ledger` 身份清单；为保持 pts 连续，该类例一律放在文件最后一点（= 已识别最大点 +1），本任务 6 例均如此。（4）hmon 返回槽（+0xF8）可指向用例自定义标签（`set.rd` 装标签 + `rd2rb` 写槽），IDL/QEMU/gem5/chipyard 四方一致；hmon 固件只动 rd63，其余寄存器跨异常保持。
**遗留问题**：已提交本分支（未 push，待 architect 复核后由主会话处理）；无其它遗留。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 2 个册宏 + 12 个 `.S` 的 26 个新链例与 6 个副作用故障例：点号在每个文件内 1..N 连续（`scan_source.pts_ok=True` 全部 12 件）；每个新链例的期望值按 `spec/SimRISC-04 §1.4`（C99 truncate-toward-zero + 定值表）与 `spec/SimRISC-01 §1`/`SimRISC-00`（大端、宽度、对齐）独立手算，并由证据脚本 oracle（26/26）与 `.testdata` 现场字面量双路复核；关系断言用 `mul.uo`+`add.uo` 重算 `q×b+r`，q/r 另按 spec 除法定义独立重算；6 个副作用例按 IDL「raise 先于写目的/写存储器」与用户 2026-11-13「单元素 ld/st 精确」裁定设计，返回槽改写机制只借 hmon 公共设施、不改公共落点；未动 `spec/`/契约/`opcodes`/引擎/`tests/inst.yaml`；生成物由官方 `--write` 重生成，`check-case-ledger`/`check-tests-index` 双向对账通过。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 除零/溢出定值仅 `.o` 有覆盖，窄宽度缺口未确认 | ✅已核实（非本任务缺口） | 未改 08/09/10（范围红线）；grep 确认 `.st/.ut/.sw/.uw/.sb/.ub` 均已有除零与溢出定值点 | 完成区「新发现」第 2 条 |
| 商余关系无直接断言（仅 q、r 各自定值） | ✅已修 | 新增 `TEST_AR_DIVREM_REL`（册宏）+ div.so 16/17、div.uo 17；关系用 mul/add 重算 | 四方 PASS；注入 4 破坏 add 少加余数 ⇒ rc=1，还原回绿 |
| MALIGN 只核异常码，未验「不写目的/不写存储器」 | ✅已修 | 新增 01 册宏 `TEST_FAULT_{LD,ST}_MALIGN_KEEP*` + 6 个故障例（ld.o/ld.st/ld.sw/st.o/st.t/st.w） | 四方一致；注入 5 改核对值 ⇒ rc=1，还原回绿 |
| 大端缺跨宽度同单元字节级证据 | ✅已修 | 同一单元 0x0102030405060708 的 ld.ub/ld.sb/ld.sw/ld.st/ld.o 前缀点 + st.w 写后读 4 点 | oracle 26/26；st.w 22-25 四方 PASS |
| `.sw` 对齐口径与任务书文字冲突 | ✅按 spec 处置 | ld.sw MALIGN 用 0x001（2 B 对齐要求） | 既有用例 + 四方实测一致；已挂「待裁定」第 2 条 |
| 自定义故障宏不被扫描器识别（不占 `CASE_N`/ledger） | ⏸延后（范围外） | 保持宏名与公共落点机制；一律放在文件最后一点以保 pts 连续 | `pts_ok=True`；已挂「待裁定」第 1 条 |

**判决**：所有 finding 已处置（1 项延后已挂待裁定），任务标「待验收」。

### 第 1 轮 reviewer 验收

**重跑记录（reviewer 实跑，退出码原样）**

- 范围：`git show --stat 5b44f133` = 18 文件（任务书 + `01-load-store.inc`/`04-arith-logic-octa.inc` + 8 个 load/store `.S` + 4 个 div/rem `.S` + `expected.tsv`/`inputs.sha256`/`case-ledger.tsv`）；`git status --porcelain -uall` 空、`git diff HEAD` 空；无 `spec/`/契约/`opcodes`/引擎/`tests/inst.yaml` 改动；未新增 `.S`。
- L2/L3：`make check-inst-asm` rc=0「274/274 镜像通过（274 个 id；链例 + 故障链 635 例）」；`make check-idl` rc=0「274/274 例四方一致（parties=idl,qemu）」；`make check-idl-full` rc=0「274/274 例四方一致（parties=idl,qemu,gem5,chipyard）」，一次通过无 flake。
- 数据：`check_inst_sig.py --data-only` rc=0「274 镜像 / 4674 槽」（== 现场 `expected.tsv` 行数）；`sha256sum -c inputs.sha256` rc=0（`.S` 条目 274 == `find tests/inst -name '*.S'` 现场 274）。
- L1 五门控 rc 全 0：`check-tests-index` / `check-case-ledger` / `check-index-blobs` / `check-inst-macro-scope` / `check-knowledge-refs`。
- 定向四方（`idl_four_way.py --platforms qemu,gem5,chipyard --jobs 1 --only …`，逐条 rc=0、`1/1 … {idl:0,qemu:0,gem5:0,chipyard:0}`）：div.so 18 / div.uo 18 / rem.so 18 / rem.uo 17 / ld.o 22 / ld.st 22 / ld.sw 23 / ld.ub 25 / ld.sb 23 / st.o 22 / st.t 21 / st.w 25 —— 与完成区数字逐一对上。
- 证据脚本：仓库根执行运行期证据目录内的 `run.sh --inject` rc=0（`RESULT: PASS`），oracle `cases=26 mismatch=0`；五路注入各自「md5 变 ⇒ rc=1 ⇒ `cp` 还原 md5 相符 ⇒ rc=0」，五组 md5（`9c3a7770…`/`2eee2fb9…`/`2732fbd7…`/`66f5bf1d…`/`4fa21c89…`）与完成区逐一相符。
- **重点一（6 个 MALIGN 副作用例）独立判定：确实执行、可达 FAIL、不静默。** ① 静态：6 镜像 `.faulttab` 新点号槽非零、后继槽 0 哨兵（ld.o pt27=`ffffff0124cc`、ld.st pt26、ld.sw pt27、st.o pt27、st.t pt24、st.w pt28=`ffffff0124f4`）；`__fc_27` 反汇编 = one-hot `0x1000`+点号 `0x1b` 写 `TEST_FAULTV` → 预置 `rd1=0xA5A5…` → 返回槽 `[HMON_BASE+0xF8]←ffffff012560` → `ld.o rd1,[rb3,4]` → 异常未发生则 `__EXIT 27` → `__mal_keepdst_27` 比对不符亦 `__EXIT 27`、相符则 `jump [rb0,7008]` → `__pad`（`ffffff014100`）。② 动态（我的独立注入：注入前 `cp` 备份并记 md5/mtime）：把 ld.o pt27 偏移 `0x004`→`0x008`、st.w pt28 `0x0D1`→`0x0D0`（改对齐地址）⇒ `make check-inst-asm` `272/274`、gate `FAIL (rc=1)`，明细 `[FAIL] ld.o_rrii_rd.S … rc {'qemu': 27}`、`[FAIL] st.w_rrii_rd.S … rc {'qemu': 28}`（正是两例点号）；`cp` 还原后 md5 逐字节相符（`08c276fd…`/`3335a52e…`）⇒ `check-inst-asm` rc=0、`274/274` 回绿 ⇒ 「MALIGN 没触发」走 `__FAULT_BODY_END` 的 `__EXIT 点号` 判红，无恒真/无断言静默；engineer 注入 5（改 `__VERIFY_RD` 期望）rc=1 又证明核对点确在执行路径上。③ `-defsym CASE_N=27` 单例镜像 build+qemu rc=0，单例调试路径对新点号同样可用。
- **盲区实测**：删掉 ld.o pt27 一例并跑官方 `inst-signature-data --write` + `check_case_ledger.py --write` 后，`case-ledger.tsv`（`64f14415…`）与 `expected.tsv`（`9c3a7770…`）md5 与删除前**逐字节相同**、仅 `inputs.sha256` 的 ld.o 哈希行变；随后五门控 + `--data-only` + `check-inst-asm` 全 rc=0 ⇒ 删除哨兵确实不守护这 6 行（`scan_source` 不识别 ⇒ 不进 ledger、也不进「635 例」计数）。已 `cp` 还原 4 文件、`md5sum -c` 全 OK、`git status` 空、门控回绿。该盲区已挂「待裁定 1」，建议架构师裁是否立后续任务扩展 `run_inst_tiny.scan_source` 正则（顺带让计数与 ledger 含这 6 例）。

**约束核验**

① 范围红线守住（见上）；② 期望值独立派生：按 `SimRISC-04 §1.4` 定值表 + C99 向零截断手算并与我方 python 现算逐字对照——div.so 16/17/18（−14/0/−3）、div.uo 16/17/18（`0x7FFF…FC`、q=`0x1745D1745D1745D1` r=2、除零全 1 且除数为 rd0）、rem.so 16/17/18（−1/−2/100）、rem.uo 15/16/17（1/2/`0x8000…0` 零扩展）全部一致；`.so`/`.uo` 同位型对照（−3 vs `0x7FFF…FC`、−1 vs 1）成立；`0x0102030405060708` 大端跨宽度 `ld.o/st/sw/ub/sb` 与 `st.w` 写 `0xBEEF` 后 `ld.ub` 读 `0xBE`/`0xEF`、`ld.sw` 读 `0xFFFF…BEEF` 按 `SimRISC-01 §1`/`SimRISC-00` 手算一致；逐宽度除零/溢出在 08/09/10 册既有（`grep` 每宽度均含除零与溢出定值、含 rd0 作除数）；未用平台实测反推 ✅；③ 上列门控 rc 全 0 ✅；④ 脚本断言可达 FAIL、计数现场派生 ✅；⑤ 完成区 8 行 ≤30、无运行期路径、「修改文件」与 `git status` 对齐（任务书自身不列入，沿 008/009 惯例）✅；⑥ **`.sw` 对齐口径**：`spec/SimRISC-01 §1` 原文 = `ld.o`/`st.o` 8B、`ld.st`/`st.t`/`ld.ut` 4B、`ld.sw`/`st.w`/`ld.uw` 2B、`ld.sb`/`st.b`/`ld.ub` 无要求 ⇒ engineer 按 spec 落地正确（ld.sw MALIGN 用 `0x001`、ld.st `0x002`、st.w `0x001`、st.t `0x002`，与既有用例一致），**任务书「`.st`/`.sw` 需 4 字节」一句应订正为「`.st`/`.t`/`.ut` 4 字节、`.sw`/`.w`/`.uw` 2 字节」，不改 spec**。

**非阻断 finding（文档级，按「文档小错不阻断」记 Accepted）**：完成区「新发现(3)」与「待裁定 1」写「不占 `CASE_N` 单例序号」不准确——`__FAULT_BODY_BEGIN` 自带 `.if CASE_N == \pt`，实测 `CASE_N=27` 单例镜像 rc=0；真正缺的只有 `scan_source` 的 `faults` 清单（⇒ `case-ledger` 身份清单与「635 例」计数）。措辞请架构师收尾顺手改，不影响门控。

**判决**：**Accepted** —— 验收命令块在我自己的重跑下全部 rc=0；独立注入（对齐地址）使 `check-inst-asm` 变红且失败点号精确为 27/28、还原回绿；任务硬约束逐条守住；完成区每个数字与我实跑一致，无转述失真。
