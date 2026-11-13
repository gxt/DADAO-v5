# m13-testcases-016: `04-arith-logic-octa` —— `add.*`/`sub.*`/`mul.*`/`div.*`/`rem.*`/`cmp.*`（含宽度×符号）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（宏层 `inst_test.inc` + `run_asm_suite.py` 已建好）；与其它 `tests/inst` 重构任务**串行**（共享 `tests/inst/`）
**可并行分片**：否
**状态**：已验证

## 背景

延续 `012`/`013` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。分类与用例模板见 `tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移台账）。

本任务覆盖 **15 个 id**（`04-arith-logic-octa` 算术（add/sub/mul/div/rem/cmp））

## 范围（id 清单，以 `contracts/opcodes.yaml` 为准）

```
add.si_riii_rd add.so_rrrr_rd add.uo_rrrr_rd cmp.si_rrii_rd cmp.so_orrr_rd cmp.ui_rrii_rd
cmp.uo_orrr_rd div.so_orrr_rd div.uo_orrr_rd mul.so_rrrr_rd mul.uo_rrrr_rd rem.so_orrr_rd
rem.uo_orrr_rd sub.so_rrrr_rd sub.uo_rrrr_rd
```

## 用例设计（5 类，模板见 `MIGRATION.md §3`）

- **encoding**：该 id 的编码校验（mask/value）
- **legality**：适用的合法性规则（`rd0/rb0`、`immu6=0`、范围/重叠、保留编码…），以 `contracts/legality_rules.yaml` 为准
- **semantic**：正常路径，宽度 × 符号 × 形式
- **boundary**：该族特有边界（进位/借位/最值/次正规/对齐/窗口/掩码…）
- **overlap**：源=目、部分重叠、块复制重叠

## 验收

1. `ls tests/inst/04-arith-logic-octa/` 下本任务 id 的 `.S` 齐全（== 16）
2. 每文件检查点 ≤127、点号连续；失败点号 = 用例序号
3. **三方逐字节**（chipyard == QEMU == gem5 同镜像），含全部故障例
4. `make check-inst` rc=0；`check-tests-index` rc=0；273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变
5. YAML 迁移：把相关 YAML 里属于本任务 id 的 case 并入；**该 YAML 文件全部 id 迁完**才 `git rm` 并更新 `MIGRATION.md`
6. **可达 FAIL 注入**：改错一个 boundary 期望 ⇒ 对应点号非零退出（三平台同值）
7. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- 沿用 `012` 的 hmon 自装 workaround（`ISS-410` 未修前必须保留）。
- **不要**改 `contracts/`/`spec/`/`Makefile` 门控集合。
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

## 审阅记录

### 第 1 轮 engineer 自审

改动面：`tests/inst/04-arith-logic-octa/`（15 个 `.S`）、`tests/inst/macros/inst_test.inc`（4 个链例宏 +
4 个故障宏）、`tools/testcases/inst/run_asm_suite.py`（2 个现场统计正则）、`tests/inst.yaml`（+15 条）、
`MIGRATION.md`/`README.md`。逐行自审 + 三平台实跑 + 独立重算，findings 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `add.uo`/`sub.uo` 的 `rdHA` 是**进位/借位 0/1**（不是 128 位高位）：探针首版按 128 位写期望 ⇒ QEMU 点 5 红 | ✅已修 | 改用例与重算口径为 0/1；`.so` 变体才是符号扩展高 64 位 | 探针 34 点三平台绿；MIGRATION §6 记该差异 |
| 装载 `rd0`（`__LI rd0, …` → `set.zw rd0`）触发 ILLI ⇒ 4 个 `cmp.*` 链例挂死（rc=-2 超时） | ✅已修 | 宏层所有初值装载加 `.ifnc \reg, rd0`；编码例不再为 rd0 生成装载 | QEMU 36/36，无挂起 |
| 双目的「被丢弃的一半」仍与 rd0 比对 ⇒ `add.so`/`sub.*`/`mul.*` 的点 5–7 红（rc=5/6/7） | ✅已修 | 丢弃半不比对；点号落在留下的那一半 | 三平台 36/36 |
| 探针 `mul.so (-1)×INT64_MIN` 期望符号错（写成 −2^63） | ✅已修 | 期望改 `0 / 0x8000..0` | 探针三平台绿 |
| `add.si max+0x1FFFF` 手算少一位 | ✅已修 | 期望交独立重算脚本核对（现 212 点不符 0） | C2 段 |
| 驱动器 `scan_source` 不认 `TEST_AR*` / 新故障宏 ⇒ 0 用例 | ✅已修 | `CHAIN_CASE_RE`/`CHAIN_PT_RE` 加 `TEST_AR\w*`，新增 `FAULT_AR_RE` | scan：15 id / 36 镜像、点号 1..N 连续 |
| 编码例 2 号装载 `rd0`、三字段同寄存器成退化解 | ✅已修 | 编码例装载改 first-wins + 跳 rd0；orrr 边界例改 `rd63/rd1/rd2` | 编码对账 15/15 |

判决：findings 全部已修 ⇒ 状态置 `待验收`。**任务书验收 1 写「== 16」**，但 §范围与
`contracts/opcodes.yaml`（`04-arith-logic-octa` 算术族）均 **15 个 id**，`MIGRATION.md §4` 亦为 15
⇒ 按 id 清单执行（现场 15 == 清单），「16」判为任务书笔误，未改验收正文。

### 第 1 轮 reviewer 验收

**重跑（本人执行；下列为现场输出/退出码，不采信完成区）**
1. 一键证据脚本（运行期证据目录 `evidence/<任务ID>/run.sh`，不入库存路径）→ rc=0、`summary: PASS=26 FAIL=0`；加 `--inject` → rc=0、`PASS=32 FAIL=0`（G 段 `div.uo` 10 号注入 → 三平台 rc=10 → `cp`+md5 `e3c23292…` 还原 → 回绿 2/2）。
2. `run_asm_suite.py --vectors tests/inst/04-arith-logic-octa …` → rc=0、**36/36**（链例 15：rc 全 0、字节流三平台相等且 == 8×点数；故障例 21：三平台 rc 全 **248=ILLI**；平台记录 108）；`--scan-only` → rc=0、15 id / 36 镜像、点号 1..N 连续且 ≤127。
3. `make check-inst` → **rc=2**、`Results: 1141 total, 1135 passed, 1 failed, 5 deferred`，红集**恰** `{divrem.yaml[23]}`（fp 册 `forem_orrr_rf`，`m13-qemu-009`/015 既有基线，非本任务）；Tiny 子集单跑 44/44 rc=0。
4. `check-tests-index` rc=0（302 条）｜`check-case-ledger` rc=0（2170）｜`validate_vectors` rc=0（gaps 0）｜`inst_sweep emit` → `sweep_expect.bin` md5 `2d4d94651346ef673c5a855e024c1489`；01/02/03 册 QEMU 回归 235/235、58/58、15/15。
5. `make -k check` → rc=2，唯一失败 `check-milestones-fresh`（**2 项**：016 台账行仍在「待开始」而任务书为「待验收」、有 worktree 未移「进行中」⇒ 归主会话移表），其余目标全 PASS。

**独立核验**
- **id 数（验收 1 的「== 16」）**：现场从 `contracts/opcodes.yaml` 取 `spec_cite: SimRISC-04` 且助记符 ∈ {add,sub,mul,div,rem,cmp} = **15**（该册共 33 = 算术 15 + 逻辑/移位/扩展 18，与 `MIGRATION §1` 一致；`add.si_riii_rb`/`add.o_orrr_bbd`/`cmp.uo_orrr_dbb` 的 cite 是 SimRISC-05，不属本族）⇒ 与 15 个 `.S` 文件名、`tests/inst.yaml` 的 001–015 三方**逐名相等**；**「16」判任务书笔误、按 15 执行成立**。
- **期望值独立复算**（本人脚本：字段解码取自 `opcodes.yaml`、语义按 `spec/SimRISC-04 §1` 手写、寄存器状态跨用例持久建模，与 engineer 脚本不同路）：**212 点全核、不符 0**，点号连续/≤127 同判。重点手算：`mul.so INT64_MIN×INT64_MIN → hi 0x4000…0/lo 0`、`mul.so max×−1 → hi FFFF…F/lo 0x8000…1`、`mul.uo max×max → hi …FE/lo 1`、`mul.uo 2^63×2 → hi 1/lo 0`、`div.so` 除零全 1、`div.so INT64_MIN÷−1 = 0x8000…0`、`rem.so` 除零=被除数、`rem.so` 溢出=0、`cmp.si imms12 0x800→−2048`（点 1 期望 1，零扩展口径会得 −1 ⇒ 可区分）、`cmp.ui immu12` 零扩展（点 8 期望 1）、`add.uo/sub.uo rdHA = 进位/借位 0/1`、`add.si max+0x1FFFF = 0x8000…FFFE` —— 逐条与 `.S` 内联期望一致。
- **独立注入（自设计，未复用 `div.uo` 10 号）**：`mul.so_rrrr_rd.S` 点 10 期望 `0x3FFF…FF → 0x3FFF…FE` ⇒ `run_asm_suite` rc=1、链例三平台 rc 全 **10**（故障例仍 248）；`cp`+md5 `c64a73fd…` 还原 → md5 相等、回绿 3/3；事后 17 个目标文件 `md5sum -c` 全 OK、`git status --porcelain -uall` 0 行、HEAD 仍 `15eeeafb`。
- **YAML 迁移（验收 5）**：15 个 id 的 **73** 条 YAML 用例只在 `reg-arith.yaml`(61) + `reg-compare.yaml`(12)（全仓扫描无第三处），逐类在 `.S` 有对应载体（encoding / semantic / boundary / overlap→故障例 / legality→故障例 / 除零 / 溢出定值），两文件未删（§5.1 前置未解）。

**约束核验**：`git diff HEAD~1 --name-status` = 15 A + 6 M（15 `.S` + 宏层 `inst_test.inc` / `run_asm_suite.py` / `inst.yaml` / `MIGRATION.md` / `README.md` / 本任务书）== 完成区「20 项 + 本任务书 = 21」；未碰 `contracts/`、`spec/`、`Makefile`；完成区 17 行 ≤30、无运行期路径（`check_knowledge_refs.py` rc=0、本任务书命中 0）；注入还原只用 `cp`+md5（未用 `git checkout/restore/stash`）；本轮未提交、未重建组件、未动主工作树。

**非阻断 findings（交 architect 收尾处理）**：① 完成区验收 1 与 `MIGRATION.md §6` 写「每 id 14–15 链例」，现场为 **13–15**（`add.uo_rrrr_rd`=13，其表头 13 与现场一致）——数字笔误，改字即可；② `div.so/div.uo/rem.so/rem.uo` 4 个 id 无「除数字段 = rd0」的字面用例（YAML 那两条的合并形态），其属性已由「hc=rd0 读出 0」「除数 0 → 定值」及同格式 `cmp.uo/cmp.so` 点 7 的 hd=rd0 覆盖 ⇒ 建议 `030` 收口 YAML 退役前补 1 例或在 `MIGRATION §6` 记一句；③ `check-inst` rc=2 为既有红、台账 2 项红归主会话移表（见重跑 3/5）。

**判决：Accepted** —— 上述验收项在本人重跑下全部通过（含独立复算 212/212、独立注入 FAIL → `cp`+md5 还原 → 回绿），无阻断项；findings 均为文档级/覆盖补强级，不改判。

## 完成区

**测试结果**：三平台 **36/36** 镜像通过（15 id；链例 15 + 故障例 21，108 条平台记录）；证据脚本 `--inject` **PASS=32 FAIL=0 / exit 0**；01/02/03 册 QEMU 回归 **235/235 + 58/58 + 15/15**。
**修改文件**（`git status --porcelain -uall` = **20 项**：15 新 + 5 改；收尾后 +本任务书 = 21）：
- 新 `tests/inst/04-arith-logic-octa/{add.si_riii_rd,add.so_rrrr_rd,add.uo_rrrr_rd,cmp.si_rrii_rd,cmp.so_orrr_rd,cmp.ui_rrii_rd,cmp.uo_orrr_rd,div.so_orrr_rd,div.uo_orrr_rd,mul.so_rrrr_rd,mul.uo_rrrr_rd,rem.so_orrr_rd,rem.uo_orrr_rd,sub.so_rrrr_rd,sub.uo_rrrr_rd}.S`
- 改 `tests/inst/macros/inst_test.inc`（`TEST_AR_{DUAL,ORRR,SI,CMPI}` + `TEST_FAULT_{DUAL,ALU3,ALU_SI,ALU_CMPI}`）、`tools/testcases/inst/run_asm_suite.py`（`TEST_AR\w*` + `FAULT_AR_RE`）、`tests/inst.yaml`（+15 条）、`tests/inst/MIGRATION.md`、`tests/inst/README.md`
**验收结果**：
1. 15 个 `.S` == 任务书 id 清单（逐名对账；见审阅记录对「== 16」的处置）；每文件链例 14–15 + 故障例 1–2，点号 1..N 连续、≤127；表头类别合计 == 现场链例数（不符 0）
2. 三方同镜像逐字节：链例 15（rc=0、字节数 == 8×点数、三平台字节流相等）+ 故障例 21（三平台 rc 全 248 = `0xF8` ILLI）
3. 编码对账（独立 oracle）：15 个 id 的 `mask/value` 由 `contracts/opcodes.yaml` × llvm-mc 规范字逐一命中；`.S` 原始编码字 == llvm-mc（15/15）
4. 期望值独立全量重算（纯 Python 大整数、按 `spec/SimRISC-04 §1`）：覆盖点数**现场派生** 212 = 现场链例点数，不符 0；覆盖不足或单文件 0 点即红
5. `check-tests-index` rc=0、`check-case-ledger` rc=0（2170）、`validate_vectors` rc=0（gaps 0）、273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变
6. `make check-inst`：红集**恰** == 既有基线 `{divrem.yaml[23]}`（1141 total / 1135 passed / 1 failed / 5 deferred）；Tiny 子集单独跑 **44/44** rc=0
7. 可达 FAIL：改错 `div.uo_orrr_rd` 点 10（max/2）期望 ⇒ 三平台 rc 全 **10**；`cp`+md5 还原（`e3c23292…`）后回绿 2/2
8. YAML：`base/reg-arith.yaml`（11 id）+ `base/reg-compare.yaml`（4 id）用例已并入；两文件仍含其它宽度 id，未删（按 §5 规则等 024/025/026）
**新发现/坑**：①`add.uo`/`sub.uo` 的 `rdHA` 是 0/1 进位/借位，`.so` 变体才是符号扩展高 64 位（`spec/SimRISC-04 §1.1`）；②`div.uo` 除零定值是**全 1**、`rem.*` 除零是**被除数**、`div.so` INT64_MIN÷−1 = INT64_MIN、`rem.so` 同例 = 0；③`set.zw rd0` 会 ILLI ⇒ 宏层任何「装载」都要跳过 rd0（含为源寄存器造初值）；④`cmp.*` 的 immu12 零扩展、imms12 符号扩展，最高位值可区分两种口径；⑤llvm-mc 对 `dst_dual_same`/`dst_rd0` 非法编码**放行**，故障例可直接用助记符写。
**遗留问题**：①`check-inst` 的 `divrem.yaml[23]` 既有红归 `m13-testcases-032`；②`reg-arith.yaml`/`reg-compare.yaml` 的 `git rm` 与 `.S` 载入门控归 `m13-testcases-030`；③`ISS-410` 的 hmon 自装 workaround 沿用；④任务书验收 1 的「== 16」与 15 个 id 不一致（判笔误，未改正文，留主会话裁定是否修）；⑤L1 `make -k check` rc=2，唯一失败目标 `check-milestones-fresh`（本 worktree 台账仍把 016 列在「待开始」表；派单行移表归主会话）；⑥台账「进行中」行由主会话在主树更新。
