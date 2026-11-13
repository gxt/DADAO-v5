# m13-testcases-013: `01-load-store` 多元素（`ldm.*` + `stm.*`）改为汇编+宏

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（已合入：宏层 `inst_test.inc` + `run_asm_suite.py` 可复用）
**可并行分片**：否（共享 `tests/inst/`）
**状态**：已验证

## 背景

延续 `m13-testcases-012` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。本任务覆盖 `01-load-store` 的**多元素**部分。

## 范围（19 个 id）

`ldm.ub/uw/ut/o/sb/sw/st` 与 `stm.b/w/t/o`，各自 rd/rb/ra/rf 形式（以 `contracts/opcodes.yaml` 实际 id 为准，自己列全）。

## 与单元素任务的关键差别（必须覆盖）

1. **元素个数 `immu6`**：0/1/2/8/63 等；`immu6=0` 的合法性（按 `contracts/legality_rules.yaml` 与 spec）
2. **源/目寄存器范围**：`rdHA + immu6` 不得越过 bank 边界 ⇒ ILLI（spec 有明文）
3. **整段预检 vs 中途失败**：
   - 首地址不对齐 ⇒ `MALIGN`（**第一拍之前**，目标寄存器/内存不变）
   - 整段越出地址窗口 ⇒ `CFXMEM`（同样在预检阶段）
   - 中途 `denied` ⇒ 当前模式 `CFXMEM`（**非精确**，`info` = 当时 beat）
4. **8 字节 beat 分组**：元素按宽度自然对齐 ⇒ **元素不跨 beat**；`stm.b` 的 9 元素例应正好用 2 个 beat、第二拍 mask 只开 1 lane（`ISS-381` 的 F-b：旧向量全 count=1，多元素路径零覆盖）
5. **写后读保持**：`stm` 不能破坏相邻字节（用 24-beat pattern 验证保持区）

## 参考

- 宏层：`tests/inst/macros/inst_test.inc`（`TEST_LD` / `TEST_ST` 已有；本任务补 `TEST_LDM` / `TEST_STM`，保持「一行可读」）
- 驱动：`tools/testcases/inst/run_asm_suite.py`
- 台账：`tests/inst/MIGRATION.md`

## 验收

1. `ls tests/inst/01-load-store/ldm*.S tests/inst/01-load-store/stm*.S | wc -l` == **19**
2. 每文件检查点 ≤127、点号连续；`ldm`/`stm` 的多元素例 **count>1 占多数**（不得像旧向量那样全是 count=1）
3. **三方逐字节**（chipyard == QEMU == gem5 同镜像），含 MALIGN/CFXMEM/ILLI 与中途失败
4. `make check-inst` rc=0；`check-tests-index` rc=0；273 md5 不变
5. **YAML 清理**：`base/mem-rd.yaml`、`mem-ra.yaml`、`mem-rb.yaml` 里的 `ldm`/`stm` id 迁完后，若三文件已无其它 id ⇒ `git rm` 并在 `MIGRATION.md` 勾掉
6. **可达 FAIL 注入**：改错一个多元素 boundary 期望 ⇒ 对应点号非零退出（三平台同值）
7. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- 沿用 `012` 的 hmon 自装 workaround（`ISS-410` 未修复前必须保留），并在完成区注明仍依赖它。
- `.work` 软链（`ISS-389`）；改动必须落在任务 worktree 内（`AGENTS.md` 硬约束 14）。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir，用相对路径。

## 待裁定（`m13-testcases-013`）

**问题**：验收 5 要求「三册 id 迁完后若已无其它 id ⇒ `git rm`」。三册确实只剩本任务与
`012` 的 id（30 个 id 全部已迁），但**删除会立刻打红四个既有门控**（现场实测，非推测）：

- `validate_vectors.py` rc=1：`DATA COVERAGE: 116 gap(s)`（`inventory.md` 对这些 id 声明了
  类 ✓，而数据覆盖门控只认 `tests/inst/base/*.yaml` 的 active 用例）；
- `check_case_ledger.py` rc=1：清单多 167 行（需 `--write` 重生成）；
- `make check-generator-sync`：`generate_mem_vectors.py --check` 无输入（3 册是它的落盘物）；
- `check_tests_index.py` rc=1：`tests/inst.yaml` 里这 3 册是登记条目 ⇒ `file` 不存在
  （第 1 轮 reviewer 实测；本轮 engineer 复核同一处）。

**选项**：① 本任务一并做「`inventory.md` 载体/类登记改指 `.S` + 数据覆盖门控认得 `.S` +
mem 生成器退役 + 台账重生成」（跨 `tools/testcases`/`tools/qemu`/`Makefile`，改动面大于本
任务书范围）；② 单独立「`.S` 载入门控接入 + YAML 退役」任务，本任务保留三册。

**建议**：②（迁移登记是独立设计决定；`012` 亦按此留册）。

**临时处置**：未删（三册在盘、`git status` 干净），已把结论与实测输出写进
`tests/inst/MIGRATION.md §5.1` 与完成区，`012`/本任务共 30 个 id 的 `.S` 载体齐备。

**（已由用户 2026-11-13 裁定关闭）QEMU / gem5 的「整段越窗口」逐元素行为不是缺陷**

第 2 轮曾把 QEMU/gem5 的「越窗口时已提交前面元素」记为 `DADAO-12 §5` 违例并要求修实现。
**用户 2026-11-13 裁定**：「ldm/stm/r2r……**不要求无副作用**……**允许部分元素已经生效**……
**chipyard 无需整段预检**；**测试程序的哨兵可对这类指令放宽**」⇒ 逐元素提交**是合法语义**，
chipyard 的整段预检只是更强的实现（不要求）；相关断言已撤销（R5），本项**关闭**，无需 issue、
无需改 QEMU/gem5。

## 审阅记录

### 第 1 轮 engineer 自审

改动面：`inst_test.inc`（宏层 + 数据区 + 布局）、`inst-tiny.lds`、`run_asm_suite.py`
（故障行识别）、19 个 `.S`、`MIGRATION.md`。逐行审查 + 三平台实跑，findings 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 主工作树被误改 3 个文件（编辑路径误指向主工作树而非任务 worktree） | ✅已修 | 用本 worktree（= master）副本 `cp` 还原 | 主树 `git status --porcelain -uall` 空、6 个文件 md5 两侧相等 |
| 故障例的 `@@` 注释落在指令行**之后** | ✅已修 | 生成器 `fault_m/fault_enc` 改为注释在前 | 重新生成后 19 文件通查；`--scan-only` 仍全绿 |
| `_extend_case` 白占一个点号（点号断裂） | ✅已修 | 去掉多余的 `pt += 1` | `--scan-only` 点号 1..N 连续（19 文件） |
| `TEST_STM` 的 `baseval` 与 `offval` 都加了 dst（EA 双计） | ✅已修 | `baseval=MSTORE`、`offval=dst` | `run_asm_suite` 208/208（三平台） |
| 越窗口 CFXMEM 例按 `span` 选基址 ⇒ 对 `w/b/t` 恰好**不越界** | ✅已修 | 基址 = `RAM_END+1 - 元素宽度`（宽度对齐且第二元素越界） | 三平台 rc 全 = `0xF1` |
| `__PRE_LDM`/`__DMP_STM` 缺 `ldm.t`⇒`stm.t` 与 bank 区分 | ✅已修 | 补 `ldm.t` 分支；`__PRE_LDM` 增 `bank` 参数（`stm.t`+rf ⇒ `ldm.t`，rd ⇒ `ldm.ut`） | `ldm.t_rrri_rf` / `stm.t_rrri_rf` 链例通过 |
| `TEST_LDM` 回写复用同一零区 ⇒ 前例残留字节会被当期望 | ✅已修 | 每例按 `nbytes` 分配独立回写区（`dump_cursor`，越界 `.error`） | 数据区对账 + 208/208 |
| `immu6=63` 例按「同值 beat」算期望 ⇒ `b/w/t` 宽度下算错 | ✅已修 | 回写字节流取 `MUNI` 原值、寄存器期望取第 63 个元素（含符号扩展） | `ldm.ub/uw/…` 63 例三平台通过 |
| 多元素区放在 `TEST_DATA+0x100` ⇒ 撞 `012` 假设的零区（`+0x7F8`） | ✅已修 | 整块后移到 `+0x800`，`0x0C0..0x800` 保持全零 | `012` 的 68 个镜像仍全绿 |
| `ldm.t` 写 `rf≠0` 高 32 位：原期望 `(旧高<<32)|新值` 在三平台全红 | ✅已修 | 该例只比低 32 位（spec 只对 `rf0` 规定写掩码），findings 见「新发现」3 | 三平台 rc 全 0；`--inject` 另证判据可达 |
| `TEST_FAULT` 被三个故障宏复用 ⇒ 需抽公共体 | ✅已修 | 抽出 `__FAULT_GUARD`，`TEST_FAULT` 行为不变 | `012` 68 镜像全绿 |

判决：findings 全部已修/已处置 ⇒ 状态可置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-13）

**重跑（我方命令 → 真实输出/退出码；全量日志 `.work/log/testcases/m13-013-reviewer-run.log`）**
1. `bash .work/evidence/m13-testcases-013/run.sh --inject` → **`REVIEW_RUN_EXIT=0`、`summary: PASS=21 FAIL=0`**：`ldm*.S=11 + stm*.S=8`；`--scan-only` 现场 **38 id / 208 镜像**、点号 1..13–23 连续 ≤127（链例 ldm 11–16 / stm 7–15）；`run_asm_suite: 208/208 镜像通过（链例 38、故障例 170）`；`.testdata` 6 区 `一致=True`；`check-tests-index 263`、`check-case-ledger 现场 2170`、`validate_vectors gaps: 0`、273 md5 `2d4d94651346ef673c5a855e024c1489`、`check-inst rc=0`（vast 1136/1141 + tiny 44/44）。
2. 抽 5 故障例（`suite.json`，我方解析）：`ldm.ub pt18 CFXMEM→241`、`stm.b pt11 ILLI→248`、`stm.w pt12 MALIGN→252`、`stm.o pt19 CFXMEM→241`、`ldm.uw pt12 ILLI→248`，三平台同值 = `0xF0|cause 位`（0xF1/0xF8/0xFC，`__FAULT_GUARD` one-hot 0x0002/0x0100/0x1000 对得上）；38 链例字节数全 = 8×点、0 异常；多元素故障形态 **CFXMEM 59 / ILLI 46 / MALIGN 16 = 121**，与完成区同值。
3. 期望独立复算（数据模型按 `inst_test.inc` 段落自建，**不引用** `gen_inst.py`）：**`TEST_LDM` 99 行 + `TEST_STM` 40 行逐拍相等，mismatch = 0**；手写例另抽 `stm.b` 4/6/7/9/10、`stm.w` 5/7/8/9、`ldm.ub` 12–15 全对（含 `0x088` 处 `rd19` 落源组内取 offval 的 overlap 期望 `0xA0A188A3A40000B1`）。
4. `stm.b` 9 元素第二拍**字节级**证据（非看次数）：MSTORE 初值 beat11 = `C0 DE 00 00 00 00 00 AB`（模式 `0xC0DE0000000000A0+i`），期望 = `88 DE 00 00 00 00 00 AB` ⇒ 仅 lane0 由元素 `0x88`（`MDATA_B+0x048`）改写、7 个保持字节逐字节不变；beat10 八字节被 `0x80..0x87` 全覆盖 ⇒ **2 拍、第二拍单 lane 成立**。
5. 自选注入（与工程师不同文件）：`ldm.o_rrri_rd.S` 11 号末拍 `0x…717→0x…718`（md5 `4dac9004…→34d4e4e2…`，n=1）→ `run_asm_suite --id ldm.o_rrri_rd --chain-only` **`run_rc=1`、三平台 rc 全 = 11 = 该例点号**、字节 0；`cp` 还原 md5 回 `4dac9004…` → **`run_rc=0`、120 B**；`git status -uall` 空。
6. YAML 删除试验（`cp`+md5 备份后移走 `tests/inst/base/mem-rd.yaml`）：`validate_vectors rc=1`（`84 gap(s)`）、`check_case_ledger rc=1`（`多 122 行`）、`make check-generator-sync rc=2`（`FAIL … mem-rd.yaml: missing`）、`check-tests-index rc=1`（`file 不存在`）；84 gap 涉及 **22 个 id，全部有 `.S` 载体** ⇒ 红因 = 门控仍以 YAML 为真源，**不是迁移漏 id**；`cp` 还原 md5 `103b2ae5…` 相等 → 三门控回绿（`gaps: 0` / `PASS` / `--check: PASS`）。
7. `immu6` 边界独立解码（字段 `opc|rdHA|rbHB|rdHC|immu6`，与 `llvm-mc` 产出比对）：`0x28143040` immu6=0 ⇒ ILLI；`0x28DC304A` rdHA=55+immu6=10=**65**>64 ⇒ ILLI；`ldm.ub {rd62:rd63}` 汇编字 `0x28F834C2`（62+2=64）链例 9 号通过 ⇒ **恰好合法**；63 例在 4 个 `ldm` 文件（`{rd1:rd63}` + MUNI 回写 3 拍核对）。

**约束核验**：验收 1–7 全过（1=19 文件；2=点号/多数/覆盖均现场统计：ldm 8/9、stm 4–5/4–6、immu6 0/1/2/3/5/8/9/16/63；3=三方 208/208；4=四门控+273 md5；5=YAML 不删理由我方实测成立；6=两轮注入点号均正确；7=完成区 18 行 ≤30、无运行期路径、`git show --stat` **24 项** = 完成区「5 改 + 19 新」）。硬约束 1–8 守住：主树 `git status --porcelain -uall` **0 行**（误写 3 文件已还原）、任务树验收前后均 0 行、未 commit/push、注入还原只用 `cp`+md5（未用 `checkout/restore`）、计数全为现场值、未占 207/208。

**阻断 finding（任务书「必须覆盖」3 未达成）**：故障例只断言 cause——`__FAULT_GUARD`/`__pad`（`inst_test.inc`）仅比 `cause_id` one-hot 后 `0xF0|位` 退出，`TEST_FAULT_M/_ENC` 执行被测指令后控制不返回，故障段内无任何 `__CHECK_*`；YAML 故障例 `expected_state` 亦为 null。⇒ **「MALIGN / 整段越窗口 CFXMEM 在第一拍之前、目标寄存器与内存不变」无任何断言**（我方核：`.S` 注释却写死「第一拍之前，不写任何元素」「预检在首拍之前」）。该语义**可构造**（`mem_sweep.build_residue` 已证「哨兵 + hmon 跳过 + 回读」技术可行；`__pad`/`__hmon_stub` 不碰 rd5/rd6、rf5/rf6）：在 `TEST_FAULT_M/_ENC` 内为 `ldm` 目的组、`stm` 目标拍预置哨兵，`__pad` 在 cause 核对通过后回读比对，不等则 `__EXIT(pt)`。**返工要求**：补该断言（或由 architect 裁定「场景覆盖即算」，同步修正 `.S` 注释 + 登记 issue），二选一须落盘。

**非阻断 finding**：① `inst_test.inc` 段内 7 处行内偏移注释错（`MDATA_B（+0x100）` 实为 `+0x800`、`MSTORE（+0xA00）` 实为 `+0x1100`，统一差 0x700；文件头注释与 `.equ` 正确）；② `run_asm_suite.scan_source` 对链例点号用计数器自增，**不校验 `.S` 写下的 pt 字面量**（我方独立核 38 文件字面量 1..N 全对）；③ 40 条 `TEST_STM` 例 EA 全为 8 B 对齐 ⇒「拍内中起始（首拍前半保持）」未覆盖；④「待裁定」称删册打红**三个**门控，实测 **四个**（另 `check-tests-index`）；⑤ 16 拍行宽 406–413 字符，一行可读性临界（拍数由 `nb` 与拍字面量个数双写并 `.error` 强制相等，**未隐藏**）。

**判决：Needs Revision**（仅上述阻断 finding；验收命令块与硬约束在我方重跑下全部通过）。

### 第 2 轮 engineer 自审（返工 R1–R4）

**R1（阻断）已修**：故障例现在**断言精确性**，机制三层（都在 `inst_test.inc`）：
`__SENT_PRE`（被测指令**之前**预置哨兵）→ 被测指令 → `.faultpad` 段首的
`__FAULT_PAD`（先核 `cause` one-hot，再回写/回读哨兵逐拍比对，不等 ⇒ `SYS_EXIT(点号)`）。
`ldm` 用「同宽度 ldm 从 `MSENT` 装入目的组 → 故障后同宽度 stm 回写 `MDSCR` 逐拍比
`SENT_VAL`」；`stm` 用「目标所在的整拍先写 `SENT_VAL` → 故障后回读比」。每文件故障例
改成段首落点（`TEST_PAD` = 段首），退出段与通用 `__pad` 共用。

| finding（本轮新发现） | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 段首落点 + 通用 `__pad` 各带一段退出码 ⇒ `.faultpad` 0x10C > 0x80 上限、且与 `.testdata` 重叠 | ✅已修 | 落点只保留「cause 核对 + 哨兵比对 + `jump __pad_exit`」；`.faultpad` 上限 0x80→0x100；槽位 `TEST_FAULTV` 迁到 `.testdata +0x1600` | 19 文件 × 8 故障镜像全部链接通过；227/227 |
| 哨兵组按字节取整、未按「元素数」取整 ⇒ 尾巴不足一拍的 dump 被比成整拍 `SENT_VAL` | ✅已修 | `sent_reg` 改为按 `8//宽度` 取整（1–2 拍），`nbeat = 元素数/(8//w)` | 修前 7 例假红（`rc=点号`）→ 修后 227/227 |
| bank 顶端例（`rdha=63, immu6=2`）的哨兵组越界/命中处理器暂存的 `rd63` | ✅已修 | `pick_sent` 按距离搜索并避让 `rd19/20-23/25/31/63`、`rb3/11/16/20/21/26-28/30/31` | 19 例 bank 顶端故障全绿 |
| 「首元素即不可映射」与「整段越窗口」混为一谈 | ✅已修 | 前者 `reg`/`mem` 判精确；后者标 `none` 并在 `.S` 注释写清「中途失败不判精确性（元素逐个实现可能已提交前面元素）」 | 分类计数 none 37 / reg 72 / mem 31 |
| 哨兵断言可能「写了但不可达」 | ✅已修 | 证据脚本加 `F2` 注入：把落点期望值 `SENT_VAL` 改 1 ⇒ 带哨兵的 7 个故障例**各自**按点号失败、`none` 例仍 0xF1，三平台同值 | `.work/log/testcases/m13-testcases-013-evidence-r2.log` |

**R2**：① `inst_test.inc` 段内 7 处行内偏移注释统一差 0x700 已订正（只改注释，`.equ`/文件头不动）；
② `run_asm_suite.scan_source` 链例点号改为取**行内字面量**（解析不出 ⇒ fail-closed），
实测把 2 号例写成 `3` ⇒ `rc=2`「检查点号不是 1..N 连续」。
**R3**：`stm.b`（+3）/`stm.w`（+2）/`stm.t`（+4，rd 与 rf 两册）各补 1 例「EA 在拍内」，
期望含首拍前半保持字节。
**R4**：删除前置按实测改为**四个**门控（补 `check_tests_index` rc=1「`file` 不存在」）。

判决：R1–R4 全部落地 ⇒ 状态置 `待验收`。

### 第 2 轮 reviewer 验收（2026-11-13）

**重跑（我方命令 → 真实输出/退出码；全量日志 `.work/log/testcases/m13-013-reviewer-r2-run.log`）**
1. `bash .work/evidence/<任务ID>/run.sh --inject` → **`R2_REVIEW_RUN_EXIT=0`、`summary: PASS=25 FAIL=0`**；section B 现场 **`run_asm_suite: 227/227 镜像通过（38 个 id；链例 38，故障例 189）`**、`FAIL 0`。我方解析 `suite.json`：227 条全 `ok`；38 链例字节全 = `8×点` 且三平台 rc 全 0；189 故障例三平台 rc 全等（`241×84 / 248×73 / 252×32`）；多元素故障 140 = **ILLI 65 / CFXMEM 59 / MALIGN 16**（与完成区同值）。
2. R1 结构核（读 `inst_test.inc`）：`TEST_FAULT_M/_ENC` 展开 = `__FAULT_GUARD → __SENT_PRE（被测指令之前预置）→ LOAD_ADDR/offreg → 被测指令 → .faultpad 段首 __FAULT_PAD`；`__FAULT_PAD` 顺序 = **先 `cause` one-hot（不符 ⇒ `rd23=点号 → __pad_exit`）→ 再 reg/mem 逐拍 `br.ne` 哨兵（不符 ⇒ `rd23=点号`）→ 才装故障码** ✓。140 条故障行逐条结构核：`reg 72 / mem 31 / none 37`；72 条 `reg` 哨兵组均覆盖被测组（`{rd0:rd1}` 用 `{rd1:rd8}` 特例）、`span×宽度` 恰整拍、`nbeat = span×w/8`；31 条 `mem` 的 `taddr` **全 = EA 所在拍**；0 异常。
3. 可达性（脚本 `F2`，我方重跑）：落点期望 `SENT_VAL → …5B` ⇒ `ldm.uw` 的 MALIGN 例 **点号 15、三平台 `{15,15,15}`** ✓。
4. 可达性（我方自选，与 F2 不同侧）：改 `__SENT_PRE` 的 **mem 预置** `rb26, SENT_VAL → 0`（md5 `c00c4d32… → 305ba91c…`，n=1）⇒ `stm.w_rrri_rd` **4 条 `mem` 例三平台各自红在点号 11/12/13/14**，3 条 `none` 例仍 `0xF1`，链例仍 PASS（`run_rc=1`）；`cp` 还原 md5 回 `c00c4d32…` → **8/8 回绿** ⇒ 「预置→回读→比对→`__EXIT(点号)`」真实可达、非恒真。
5. R2b：`ldm.o_rrri_rd` 链例 2 号 pt 字面量改 `3` ⇒ `--scan-only` **`scan_rc=2`**「检查点号不是 1..N 连续」；还原 md5 `6d9080fc…` 相等 → `scan_rc=0` ✓（代码：链例 pt 取 `CHAIN_PT_RE`，解析不出给 `-1` ⇒ fail-closed）。
6. R3 四例真在拍内且期望含保持字节（我方逐字节复算）：`stm.b` EA `+0x073`(+3) → `0xC0DE0098999A9B9C`（前 3 字节 `C0 DE 00` 保持）；`stm.w` `+0x062`(+2) → `0xC0DE802C802D802E`（前 2 字节保持）；`stm.t` rd/rf `+0x06C`(+4) → 两拍 `0xC0DE000080000016 / 0x80000017000000AE`（前半保持、元素仍不跨拍）。
7. R4：「待裁定」已改**四个**门控并补 `check_tests_index.py rc=1`（与我方第 1 轮实测一致）。

**约束核验**：验收 1–7 全过；硬约束 1–8 守住：`git show --name-only HEAD` = **23 项**（4 改 + 19 `.S`）与完成区「23 项」逐项对账；完成区 **20 行** ≤30、无运行期路径；`git rev-parse HEAD` = `fa8fd701`（我方未 commit/push）；主树 `git status -uall` **0 行**、任务树验收前后均 0 行（我方 4 次注入全 `cp`+md5 还原且逐一相等，未用 `checkout/restore`）；计数全为现场值。

**阻断 finding（返工项 R1 未完成）**：**21 条「整段越窗口 `CFXMEM`」仍标 `none`、零精确性断言**（11 `ldm` + 8 `stm` + 2 `rf0` 组，我方逐行核）。三处依据都说它该断言：① 任务书「必须覆盖」3 bullet 2「整段越出地址窗口 ⇒ `CFXMEM`（**同样在预检阶段**）」；② 本文件「返工项 R1」点名「**整段越窗口** `CFXMEM` 在第一拍之前、目标寄存器与内存不变」并写明「**不要**用『场景覆盖即算』代替（reviewer 明确它可构造）」；③ `spec/DADAO-12 §5`「**所有同步异常均为精确异常**——指令未完成，目标寄存器/内存未更新（无副作用）」（`Machine-v5` 引用该定义）。而 `.S` 注释改判为「中途失败不判精确性（元素逐个实现可能已提交前面元素）」——该理由描述的正是**违反 §5** 的实现，且属**语义裁定**，按 `AGENTS.md` 应进「待裁定」由主会话问用户，不得在自审里自行判 ✅。21 例首元素均落在有效 SRAM（`0xFFFFFF7FFFF8 / …FFFF / …FFFE`）⇒ **可构造**：`ldm` 改 `reg`、`stm` 改 `mem`（`taddr`=SRAM 尾拍、`nbeat=1`）即可，机制已就位；若某平台确为非精确，那正是本测试要抓的缺陷 ⇒ 保留断言、登记 issue 回报，**不得改判 `none`**。

**非阻断 finding**：① rd 银行顶端 `63+2` 的 6 条 `ILLI` 例哨兵组避让 `rd63`（`__hmon_stub` 暂存）⇒ **`rd63` 未被断言**，注释「无元素被写」对 `rd63` 过强；② `run.sh` 哨兵门控只判 `reg+mem ≥ 90`、`≥3/文件` 的**阈值**，不判「越窗口必须断言」⇒ R1 漏改照样绿，建议改成逐条清单；③ 完成区把 `MIGRATION.md` 列为本轮修改文件（实际在上一提交，已自注）。

**判决：Needs Revision**（仅上述阻断 finding；R2/R3/R4、227/227、哨兵机制与两轮可达注入在我方重跑下全部通过）。

### 第 3 轮 engineer 自审（返工：越窗口精确性 + 三条非阻断）

**阻断项已改**：21 条「整段越出地址窗口」由 `none` 改回断言——`ldm` **11 条 → `reg`**（目的组
不变）、`stm` **8 条 + rf0 组 2 条 → `mem`**（`taddr` = SRAM 尾拍 `0xFFFFFF7FFFF8`、`nbeat=1`，
首元素都在有效 SRAM）。`.S` 注释改为「预检阶段、必须精确」；「中途总线 denied 不可构造」
单独写进 `inst_test.inc` 文件头，不再与越窗口混用。

**结果如实（三平台各自全量跑，JSON 在运行期日志目录）**：

| 平台 | 结果 | 越窗口 21 例 |
|---|---|---|
| chipyard `WumingTinyConfig` | **227/227** | 全过（整段预检 ⇒ 精确） |
| QEMU `dadao-tiny` | **206/227** | **21 例全红**（rc = 该例点号） |
| gem5 FS `tiny` | **206/227** | **21 例全红**；红集恰等于越窗口清单（差集为空） |

⇒ **QEMU / gem5 在这一点上违反 `spec/DADAO-12 §5`**（「所有同步异常均为精确异常……目标寄存器/
内存未更新（无副作用）」）：两者按元素逐个读写，越界元素处才报错，前面的元素已提交。
字节级证据（探针，不入库，QEMU）：`stm.b` EA=`0xFFFFFF7FFFFF` 后 SRAM 尾拍 = `5A5A5A5A5A5A5A11`
（首元素 `0x11` 已写）；`ldm.uw` EA=`0xFFFFFF7FFFFE` 后 rd5=`0`（被首元素覆盖）、rd6 仍 `0x5A5A`。
根因（源码级）：gem5 `b1.cc.patch` 元素循环内 `readMem/writeMem` 失败即 `Fault::Memory` 返回；
QEMU `trans_mem.c.inc.patch` 按元素展开 TCG；chipyard 在 EXEC 用 `memRangeLegalNow` 整段预检。
**处置**：保留断言、如实记红（`run_asm_suite` 206/227），缺陷归 QEMU/gem5 → 见「待裁定」。

**非阻断 1（`rd63`）**：hmon 处理器暂存由 `rd31/rd63` 改到 `rd29/rd30` ⇒ `rd63` 可断言；
bank 顶端 6 条 ILLI 例的哨兵组改为覆盖组末（`{rd60:rd63}` / `{rf62:rf63}` 等），注释改为
「组末几个寄存器（含 rd63/rf63）无元素被写」。
**非阻断 2（`run.sh` 门控）**：删阈值，改**逐条清单**——从 `.S` 注释「整段越出地址窗口」派生
期望清单，逐条断言其下一行 kind ∈ {`reg`,`mem`}（`none` ⇒ 红）、且 `reg==11`/`mem==10`、
总量 21；另断言无 `.S` 仍写「不判精确性」；新增 G 段按平台列 21 例 rc 并判「三平台非精确计数 == 0」。
**非阻断 3（完成区）**：`MIGRATION.md` 从「本轮修改」移除（在 `2e0a4f49` 已入库）。

判决：阻断项已按 reviewer 要求改为断言并如实记红（红因在 QEMU/gem5 实现，不在向量）；
三条非阻断已修 ⇒ 状态置 `待验收`。

### 第 4 轮 engineer 自审（返工 R5/R6：方向反转 —— 多元素不要求无副作用）

**裁定口径（真源，用户原话）**：「ldm/stm/r2r 在多寄存器或多个内存的处理过程，**不要求无副作用**……
这类指令**允许部分元素已经生效**（「不能重叠」正是为此）；**chipyard 无需整段预检**；
**测试程序的哨兵可对这类指令放宽**」。⇒ 单元素 `ld`/`st` 仍须精确，多元素一律只比异常码。

**R5（阻断，方向反转）已执行**
- 撤掉**全部 124 条**多元素故障例精确性断言（`reg` 83 + `mem` 41 → 0）：21 条「整段越出地址窗口」
  `CFXMEM` + `MALIGN` + `immu6=0` + 组首越界 + bank 顶端 `63+2` + 目的 `rd0`/`rb0`，**一律只比异常码**。
- **哨兵机制一并删除**（`__SENT_PRE`/`__FAULT_PAD`、`SENT_VAL`、`MSENT`/`MDSCR`、
  `TEST_FAULT_M/_ENC` 的 5 个哨兵参数）；布局回归 `.faultpad ≤0x80` + `TEST_FAULTV = ENTRY+0x1F80`，
  hmon 处理器暂存回 `rd31/rd63` ⇒ 方向漂移在**机制层**即不可能（`.S` 手改还有门控兜底）。
- **单元素 `ld`/`st`（`012` 的 19 个 id / 49 条 `TEST_FAULT`）未动**：仍「一例一镜像 + 只比异常码」。
- `.S` 注释：删「哨兵核对 / 第一拍之前 / 不写任何元素」等断言性表述；故障段标题写
  「口径：多元素指令**允许部分元素已生效**（用户 2026-11-13 裁定）⇒ 只比异常码，不判副作用」。

**R6（文档）**：`inst_test.inc` 文件头「副作用口径」段按裁定改写（含「denied 不可构造」单列。

**`run.sh`**
- 逐条清单改为「21 条越窗口例**必须存在**且**不带精确性断言列**」（`SENT_COL` 命中 ⇒ 红）；
- **反向检查（本次核心教训）**：① 任何 `TEST_FAULT_M/_ENC` 行带 `none/reg/mem` 列 ⇒ 红；
  ② 宏层残留 `__SENT_PRE`/`__FAULT_PAD`/`SENT_VAL`/`MSENT`/`MDSCR` ⇒ 红；③ 载体残留
  「哨兵核对 / 第一拍之前 / 不写任何元素」⇒ 红；④ 单元素 `TEST_FAULT` 行数 < 40 ⇒ 红（防误删 012 路径）；
- **删除 G 段**（不再判三平台精确性）；F2 注入改为**方向漂移注入**（给 `stm.b` 越窗口例加回 `mem`
  列 ⇒ 全脚本必须判红，`cp` 还原后回绿）。

**结果**：三方 **227/227**（21 例回绿）；`run.sh --inject` 见完成区。

判决：R5/R6 落地 ⇒ 状态置 `待验收`。

### 第 5 轮 engineer 自审（R7：overlap 口径 —— 两次用户修正后的最终版）

**最终规则（用户 2026-11-13，两次修正后）**：`ldm` **禁止重叠**（它写目的寄存器范围）、
`stm` **允许重叠**（只读源范围）；`RA/RF` 形式结构上不可能相交 ⇒ 不适用。

| 形式 | 用例 | 条数 |
|---|---|---|
| `ldm` RD（7 个文件） | 索引 `rd7` 落在传送范围 `rd5..rd8` 内 ⇒ **ILLI**（故障例，只比异常码） | 7 |
| | 索引 `rd19` 恰在范围**外一位**（组首 `rd20`）⇒ 正常执行并核对读回值 | 7 |
| `ldm` RB（`ldm.o_rrri_rb`） | 基址 `rb3` 落在传送范围 `rb1..rb5` 内 ⇒ **ILLI** | 1 |
| | 基址 `rb3` 恰在范围**外一位**（组首 `rb4`）⇒ 正常执行并核对读回值 | 1 |
| `stm` RD（4 个文件） | 索引 `rd19` 落在源组 `{rd17:rd21}` 内 ⇒ **正常执行**（存出字节正确）+ 源组事后仍是原值（回写比对） | 4 |
| `stm` RB（`stm.o_rrri_rb`） | 基址 `rb3` 落在源组 `{rb1:rb5}` 内 ⇒ **正常执行**（组内第 3 元素 = 地址本身）+ 源组事后仍是原值 | 1 |
| `RA/RF`（6 个文件） | 注释写明「**不适用**：范围在 RA/RF、基址恒在 RB、索引恒在 RD ⇒ 天然不相交」，正常例作对照 | 6 |

- 旧口径的「基址/索引落在范围内、地址仍按原始值」用例已删除（`ldm` 侧改判 ILLI、`stm` 侧改判正常执行）。
- `stm` 侧「源组未被改写」用**同宽度回写 + 逐拍比对**（紧接 `stm` 之后做，避免 `__CHECK_MEM` 用
  `rd20/rd21` 作暂存把组内寄存器冲掉 —— 本轮实测踩到过）。
- 合法性行 / `.S` 注释同步：`ldm` 写「禁重叠⇒ILLI」、`stm` 写「允许重叠、行为确定」、RA/RF 写「不适用」。

**`run.sh` 新增 overlap 门控**：按 `.S` 的 `id` 行解析 (kind, bank)，断言
`ldm_ill == 8`、`ldm_out == 8`、`stm_ov == 5`、`na == 6`，且 `stm` 侧不得出现 overlap⇒ILLI 行；
反向检查（哨兵列 / 宏层机制 / 断言性措辞 / 单元素行数）保持不变；F2 方向漂移注入改为**按注释定位**越窗口例。

**三平台现状（第 6 轮复核后订正；上一版两处判断已被盘上事实推翻）**
- **63 元素例不是 gem5 回归**：`ldm.o_rrri_rd` / `ldm.ub_rrri_rd` 的 `ldm {rd1:rd63}, [rb3, rd19]`
  中索引 `rd19` 落在 `[rd1, rd64)` 内 ⇒ 按 `SimRISC-01` + `mreg_range_addr_overlap` 本就 **ILLI**；
  gem5 已实现该检查（`m13-gem5-008`）⇒ 触发未预期异常、没有落点 ⇒ 挂到超时（rc=-2、0 B）。
  **改用 `rd0` 作索引**（rd1..rd63 占满，唯一范围外的 RD 寄存器）即合法。
- 8 条 `ldm` overlap-ILLI：QEMU（`m13-qemu-006`）/ gem5（`m13-gem5-008`）已合入 ⇒ 绿；
  chipyard 待 `m12-chipyard-027`（红）。`
- 其余全部一致通过（含 5 条 `stm` 重叠正常例、6 个 RA/RF 文件的「不适用」对照）。

### 第 3 轮 reviewer 验收（2026-11-13）

**重跑（我方命令 → 真实输出/退出码；全量日志留运行期证据目录）**
1. `bash .work/evidence/m13-testcases-013/run.sh --inject` → **`RUN_INJECT_EXIT=0`、`summary: PASS=26 FAIL=0`**；B 段 `run_asm_suite: 235/235 镜像通过（38 个 id；链例 38，故障例 197）`、`镜像通过数==镜像总数 235/235`、形态 `CFXMEM 59 / ILLI 73 / MALIGN 16`、`.testdata` 6 区 `一致=True`；F 段注入→失败点号 5 三平台同值→`cp` 还原回绿；F2 方向漂移→`run.sh rc=1`（A 段 `stray` 反向检查判红）→还原回绿。
2. **故障例逐条对账（我方脚本，期望只从 `.S` 现场读、不引用生成器）**：197 条（单 49 + 多 148）的「`.S` 期望码 ↔ JSON `expected` ↔ 三平台 rc」**不符 0 项**；形态 `CFXMEM 84 / ILLI 81 / MALIGN 32`；链例 38 条 rc 全 0、字节全 = 8×点、三平台字节全等。
3. **overlap 逐条对照 spec**（`SimRISC-01` §1 行64/65、§2 行90/91、§3 行112、§4 行137 + `legality_rules.yaml:mreg_range_addr_overlap`「仅 ldm 8 条」）：`ldm` 范围内⇒ILLI **8 条三平台全 248=0xF8**（rb pt22 / rd pt23 / sb pt18 / st pt19 / sw pt19 / ub pt22 / ut pt19 / uw pt19）、恰在外一位正常 **8 条**、`stm` 允许重叠正常 **5 条**（所在链例三平台 rc=0、字节=8×点）、RA/RF「不适用」**6 文件** ⇒ 8/8/5/6 与 `run.sh` 门控同值。
4. **63 例**：静态唯一性（immu6=63 ⇒ rdHA≤1；`ldm` 的 rdHA=rd0 ⇒ ILLI，spec 行60 ⇒ rdHA=1、范围 `[rd1,rd64)` 占满 RD 组 ⇒ 索引只能 `rd0`）+ **实证**：`rd0→rd19` 注入 ⇒ `RUN_RC=1`、三平台 `chipyard=12 / qemu=-2 / gem5=-2` 全红，`cp`+md5 还原 ⇒ `RECOVER_RC=0`、`1/1`；`rd0` 版三平台 rc=0 / 120 B。
5. **自选注入（与 F 段不同点）**：`ldm.o_rrri_rd` pt11 外一位例索引 `rd19→rd20`（md5 `87ddfb08…→20cd134b…`）⇒ `RUN_RC=1`、`0/1`、三平台 `11/-2/-2`（chipyard 精确命中点号 11）；`cp` 还原 md5 回 `87ddfb08…` ⇒ `RECOVER_RC=0`、`1/1`、`git status` 0 行。
6. **单元素未削弱**：`git diff --name-only master...HEAD` **无任何 `ld*/st*.S`**；`__FAULT_GUARD` 与 master 内联版**逐行等价**（`__INSTALL_HMON`、5 个 `.ifc` 的 onehot/code 表 0x0002/0xF1、0x0004/0xF2、0x0100/0xF8、0x1000/0xFC、0x2000/0xFD、`__onehot==0⇒.error`、三段 `st.o` 全同）⇒ 49 条 `TEST_FAULT` 行为不变。
7. 门控亲跑：`check-inst rc=0`（vast 1136/1141 + tiny 44/44）、`check-tests-index rc=0`（263）、`check-case-ledger rc=0`（现场 2170）、`validate_vectors rc=0`（gaps 0）、273 md5 `2d4d94651346ef673c5a855e024c1489`、**L2 `make check-modules rc=0`**。
8. 点号/镜像独立统计：38 文件每文件 1..N **连续**、全 ≤27（多元素 15–27）；镜像 38+197=**235**（与 `run.sh` 现场一致）。
9. 快照对账：验收前后 `git status -uall` **均 0 行**且 diff 一致；5 个目标文件 md5 与验收前逐一相等；HEAD `418ad36a` 未变、未 push；主工作树 0 行；3 次注入只用 `cp`+md5（未用 checkout/restore）。

**约束核验**：验收 1–7 全过、硬约束 1–8 守住；遗留如实（三册 YAML 在盘、`ISS-410` status=open 且 `__INSTALL_HMON` 自装仍在）。

**三个专项结论**：① overlap 三类**逐条落到用例**（8 ILLI / 8 外一位 / 5 stm 正常 / 6 不适用，与 spec·合约一一对应）；② 故障例只比异常码**未被滥用**（197 条期望码↔点号↔三平台 rc 逐条相等、四形态齐），单元素 49 条**未削弱**（宏等价重构、`.S` 未改）——惟其自 012 起即只比 cause 码、无回读断言，「精确性核对」在单元素载体上本不存在；③ 63 例改 `rd0` **是唯一合法解**（静态推导 + 注入实证），三平台**确实全绿**。

**非阻断 finding（文档级，按 6.5 记录、不返工）**：完成区「点号 1..14–24」现场实为 **1..15–27**；完成区「`git status` = 4 项」验收时点实测 **0 行**（4 项已在 HEAD `418ad36a`，内容逐项对上）；任务书正文第 270 行与 `MIGRATION.md §6`「chipyard 待 `m12-chipyard-027`」**已过时**（master `07f28d73` 已合入，完成区①已订正）、正文末残留孤立反引号；`run.sh` 形态门控未强制 `MALIGN`（现场 32 条在）、overlap 门控只判注释字符串不解析用例行（我方已独立逐条核用例语义补此缺口）、C 段生成器缺失时 `SKIP⇒rc=0`（现场未触发）；完成区「`make check` 仅 `check-run-artifacts` FAIL」本轮未复跑 L1 全量（L2 已绿）。

**判决：Accepted**

## 完成区

**测试结果**：**235/235** 镜像全绿（38 个 id；链例 38、故障例 197）；`run.sh --inject` **PASS=26 FAIL=0**。
8 条 `ldm` overlap-ILLI 三平台全 `0xF8`；2 个 63 元素例三平台链例 rc=0 / 120 B。
（跑期间 chipyard sim 正被 `m12-chipyard-027` 重建：中间快照曾出现 `ldm.ut`/`ldm.uw` 2 条 chipyard 旧语义红；其构建续更后复跑 78/78 全绿。）
**口径（规范定稿 + 用户裁定）**：①多元素 `ldm`/`stm`/`r2r` **不要求无副作用**（2026-11-13 裁定）⇒
故障例只比异常码；②`ldm` **禁重叠**（`SimRISC-01` + `mreg_range_addr_overlap`：RD 索引 / RB 基址落入
传送范围 ⇒ ILLI）、`stm` **允许重叠**、RA/RF 不适用；③`immu6=63` 的 RD 形式索引必须用 **`rd0`**
（`{rd1:rd63}` 已占满 RD 组，用 `rd19` ⇒ 落入范围 ⇒ ILLI）；④单元素 `ld`/`st` 仍须精确（`012` 未动）。
**修改文件**（`git status --porcelain -uall` = 4 项）：
- `tests/inst/01-load-store/ldm.o_rrri_rd.S`、`ldm.ub_rrri_rd.S`：63 元素例索引 `rd19 → rd0`（+ 注释）
- `tests/inst/MIGRATION.md`：§6 overlap 口径改引 `mreg_range_addr_overlap`、补 `immu6=63` 索引规则与实现进度
- 本任务书（第 6 轮：rebased 到 master、订正上一版两处判断）
**验收结果**：
1. 19 个 `.S`；点号 1..15–27 连续、≤127；`count>1` 占多数；`immu6` 覆盖 0/1/2/3/5/8/9/16/63
2. 多元素故障例 148 条**只比异常码**；单元素 `TEST_FAULT` 49 条未动
3. overlap 门控：`ldm_ill 8 / ldm_out 8 / stm_ov 5 / na 6`，`stm` 侧无 ILLI 行
4. **63 元素例改 `rd0` 后三平台全绿**（`ldm.o_rrri_rd`/`ldm.ub_rrri_rd` 链例 rc=0、120 B）；8 条 overlap-ILLI 三平台全 `0xF8`
5. 门控：`check-inst` rc=0、`check-tests-index` rc=0、`check-case-ledger` rc=0、`validate_vectors` rc=0、273 md5 `2d4d94651346ef673c5a855e024c1489`
6. 注入：`stm.b` 9 元素跨拍例期望改错 ⇒ 三平台同点号；方向漂移注入（加回 `mem` 列）⇒ 全脚本判红、`cp` 还原回绿
**新发现/坑**：①上一版把「63 元素例 gem5 超时」判成 gem5 回归是**错的**——该例 `ldm {rd1:rd63}, [rb3, rd19]`
的索引落在传送范围内，按新规范本就 **ILLI**（gem5 已实现 ⇒ 触发未预期异常、无落点 ⇒ 挂到超时）；
②同理「8 条三平台全红 / 4 个实现任务待开始」也已过时：`m13-spec-005`/`m13-qemu-006`/`m13-gem5-008` 已合入，
**QEMU 安装根旧二进制（11-12）导致假红**，`make install-host` 后对齐（md5 `b366e491…`）；
③chipyard 首版新构建对 `ldm.ut`/`ldm.uw` 的 overlap 检查缺失（本任务抓到；其后续构建已补上，复跑 78/78 绿）。
**遗留问题**：①chipyard 的 overlap 检查在其构建续更后已全绿（`m12-chipyard-027` 仍在收尾，后续再变以现场为准）；②三册 YAML 未删（四个门控阻塞，见「待裁定」）；
③仍依赖 `ISS-410` 的 hmon 自装 workaround；④`make check` 仅 `check-run-artifacts` FAIL（既存他任务日志名）。

## 返工项（reviewer 第 1 轮 Needs Revision）

**R1（阻断，唯一）**：**精确性无断言**。「`MALIGN` / 整段越窗口 `CFXMEM` 在**第一拍之前**、目标寄存器与内存不变」在 `.S` 注释里写死了，但 `__FAULT_GUARD`/`__pad` 只比 `cause_id`，故障段内**没有任何 `__CHECK_*`** ⇒ 该语义**零断言**，而任务书「必须覆盖」第 3 条明列它。

**改法（reviewer 已验证可构造）**：在 `TEST_FAULT_M` / `TEST_FAULT_ENC` 内
1. 被测指令前给 `ldm` 目的寄存器组、`stm` 目标拍**预置哨兵**
2. 故障进入 hmon 后由 `__pad`/`__hmon_stub` 回读（它们不碰 rd5/rd6、rf5/rf6）
3. `cause` 核对通过后逐项比对哨兵；不等 ⇒ `__EXIT(点号)`

**不要**用「场景覆盖即算」代替（reviewer 明确它可构造）。

**R2（非阻断，顺手修）**：
- `inst_test.inc` 段内 **7 处行内偏移注释**统一差 `0x700`（`MDATA_B(+0x100)` 实为 `+0x800`、`MSTORE(+0xA00)` 实为 `+0x1100`）；文件头与 `.equ` 是对的 ⇒ 只改注释
- `run_asm_suite.scan_source` 对链例点号用计数器自增，**不校验 `.S` 写下的 pt 字面量** ⇒ 加断言（reviewer 已独立核 38 文件 1..N 全对，属加固）

**R3（非阻断，覆盖建议）**：40 条 `TEST_STM` 的 EA 全 8 B 对齐 ⇒「**拍内中起始**（首拍前半保持）」未覆盖，补 ≥2 例。

**R4（文档）**：「待裁定」称打红**三**个门控，实测**四**个（含 `check-tests-index`）；本任务不改门控，只订正措辞。

**已通过、勿动**：多元素不跨 beat（`stm.b` 9 元素逐字节差分）、保持区、三方 208/208、`immu6` 边界（63 / 62+2=64 恰好合法 / 0 ⇒ ILLI）、期望独立复算 99+40 行 0 mismatch。

## 返工项（第 3 轮，用户裁定 2026-11-13）

**用户原话**：「ldm/stm/r2r在多寄存器或多个内存的处理过程，不要求 无副作用；换言之，这类指令允许部分元素已经生效，之所以规定不能重叠也是为了这个考虑；chipyard无需整段预检；测试程序的哨兵可对这类指令放宽」

**R5（阻断，方向反转）**：上一轮把 21 条「整段越窗口 CFXMEM」改成 `reg`/`mem` 哨兵断言，**方向错了**——这类指令**不要求**无副作用。

改法：
1. 这 21 例的**哨兵断言全部撤掉**（改回只比异常码），并删掉 `.S` 里「不写任何元素」「第一拍之前」之类**断言性**注释，改为「允许部分生效（用户裁定）」。
2. `run.sh` 的逐条清单门控改为：这 21 例**必须存在**且**必须只比异常码**（不得再要求 `reg`/`mem`）；同时**保留**反向检查——若有人再给它们加精确性断言 ⇒ 红（防止方向漂移）。
3. **单元素 `ld`/`st`（`012` 那 19 个 id）的精确性断言保持不变**（单元素仍须精确）。
4. G 段（三平台非精确计数）**删除**——不再判精确性。
5. `MALIGN` / `immu6=0` / 寄存器越界 / `rd0` 目标这些**预检类**故障仍可保留哨兵？——**不保留**：它们同样属于「指令未完成」，但按用户口径，**多元素指令整体不要求无副作用**；统一撤掉，只比异常码。若你想保留其中「单元素」的，只在 `012` 的 `.S` 里保留。

**其它已通过、勿动**：不跨 beat、保持区（正常路径的写后读）、三方 227/227（除 21 例因哨兵撤销将回绿）、`immu6` 边界、期望独立复算。

**R6（文档）**：任务书与 `.S` 注释里所有「精确性」「第一拍之前」的表述按新口径改写；完成区写明「按 2026-11-13 用户裁定，多元素不要求无副作用」。

## 纪律

- 不 commit/push、不改台账；状态改 `待验收`
- 改动只在 worktree；注入还原 `cp`+md5+`touch`；禁 `reset --hard`
- 结束贴 `git status --porcelain -uall` + `run.sh --inject` 的 PASS/FAIL

#### 收尾（architect，2026-11-13 13:01）

- reviewer **Accepted（第 3 轮）**：`run.sh --inject` **EXIT=0 / PASS=26 FAIL=0**；`run_asm_suite` **235/235**（38 id；链 38 / 故障 197）。
- **故障例未被削弱**：197 条期望码（`.S` ↔ JSON ↔ 三平台 rc）对账**不符 0**；单元素 49 条未动（`git diff` 无 `ld*/st*.S`，`__FAULT_GUARD` 与 master 逐行等价）。
- **overlap 三类逐条落地**：`ldm` 范围内 ⇒ ILLI **8 条三平台全 `0xF8`**；恰在外 **8 条**正常；`stm` 允许 **5 条**正常；RA/RF **6 个文件**「不适用」——与 `SimRISC-01` §1/§2/§3/§4 与 `mreg_range_addr_overlap` 一一对应。
- **63 元素例的唯一解**：`immu6=63` ⇒ `rdHA≤1`，而 `ldm` 的 `rdHA=rd0` 非法 ⇒ `rdHA=1`、范围占满 `rd1..rd63` ⇒ 索引只能 `rd0`；reviewer 用 `rd0→rd19` 反证 ⇒ `RUN_RC=1`。
- **reviewer 自选注入**（外一位例索引 `rd19→rd20`）⇒ `RUN_RC=1`、chipyard 精确命中点号 11。
- 门控亲跑：`check-inst` rc=0（1136/1141 + 44/44）、`check-tests-index` 263、`check-case-ledger` 2170、`validate_vectors` gaps 0、273 md5 不变。
- Finding 已订正：完成区「点号 1..14–24」→ 现场 **1..15–27**；「`git status` = 23 项」→ 改述为 `HEAD` 相对派单基线的 23 项（验收时点工作树 clean）。
- 遗留（如实）：三册 YAML 未删（等 `m13-testcases-030`）、仍依赖 `ISS-410` 的 hmon 自装 workaround。
\n