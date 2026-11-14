# m13-testcases-025: `09-arith-logic-wyde` —— `.uw`/`.sw` 全族

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（宏层 `inst_test.inc` + `run_asm_suite.py` 已建好）；与其它 `tests/inst` 重构任务**串行**（共享 `tests/inst/`）
**可并行分片**：否
**状态**：已验证

## 背景

延续 `012`/`013` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。分类与用例模板见 `tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移台账）。

本任务覆盖 **21 个 id**（`09-arith-logic-wyde`）

## 范围（id 清单，以 `contracts/opcodes.yaml` 为准）

```
add.sw_orrr_rd add.uw_orrr_rd cmp.sw_orrr_rd cmp.uw_orrr_rd div.sw_orrr_rd div.uw_orrr_rd
mul.sw_orrr_rd mul.uw_orrr_rd rem.sw_orrr_rd rem.uw_orrr_rd rev.w_orri_rd rol.w_orri_rd
rol.w_orrr_rd shl.w_orri_rd shl.w_orrr_rd shr.sw_orri_rd shr.sw_orrr_rd shr.uw_orri_rd
shr.uw_orrr_rd sub.sw_orrr_rd sub.uw_orrr_rd
```

## 用例设计（5 类，模板见 `MIGRATION.md §3`）

- **encoding**：该 id 的编码校验（mask/value）
- **legality**：适用的合法性规则（`rd0/rb0`、`immu6=0`、范围/重叠、保留编码…），以 `contracts/legality_rules.yaml` 为准
- **semantic**：正常路径，宽度 × 符号 × 形式
- **boundary**：该族特有边界（进位/借位/最值/次正规/对齐/窗口/掩码…）
- **overlap**：源=目、部分重叠、块复制重叠

## 验收

1. `ls tests/inst/09-arith-logic-wyde/` 下本任务 id 的 `.S` 齐全（== **21**；判据 = 任务书 §范围 清单 == 目录内容）
2. 每文件检查点 ≤127、点号连续；失败点号 = 用例序号
3. **三方逐字节**（chipyard == QEMU == gem5 同镜像），含全部故障例
4. `make check-inst` 的**红集恰为既有 pin** `{divrem.yaml[23]}`（rc=2 属预期）；`check-tests-index` rc=0；273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变
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

审查范围：21 个 `.S`（逐文件读、逐例对照 `spec/SimRISC-09` 与 `opcodes.yaml`）、生成脚本、
独立复算脚本、两个片段、证据脚本。逐例复算由 `oracle.py` **独立重写**（解析 `.S` 文本
按宏层装载顺序重建寄存器状态），不共用生成脚本代码。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `shr.sw` 按「先移位后符号扩展」算，`0x8000>>15` 得 1（应 −1） | ✅已修 | 模型改「先 16 位符号扩展再算术右移」 | 首轮 QEMU 两册链例红（`shr.sw_orri` 点 4、`shr.sw_orrr` 点 15）⇒ 修后 335 点三方全绿 |
| F2 YAML 的 orri `dst_rd0` 故障例误用 3 寄存器宏（`rev.w rd0, rd6, rd7` 汇编失败） | ✅已修 | 按 format 选宏（orri ⇒ `TEST_FAULT_ALU_ORRI`） | 修前 1 例 build 失败 ⇒ 现 56 故障例三平台全 `0xF8` |
| F3 注释与内联期望不符 6 处（`rol.w` 两源同名 amount=15、`shr.uw` 两处 `<<`/`−1`、`shr.sw 0xFF00>>4 ⇒ −16`） | ✅已修 | 只改注释，期望值以模型为准 | 注释-期望尾值比对脚本：仅剩「先 16 位中间值再扩展」的合法解释链 |
| F4 类别配额不足（`shl.w` semantic 2、`rev.w`/`rol.w` orri overlap 1） | ✅已修 | 每册补 1–2 条 semantic/overlap | 现各 id：encoding 2–3 / semantic 3–7 / boundary 3–9 / overlap 2–3 |
| F5 装载序列里出现 `__LI rd0`（YAML `rdhc=rd0` 例） | ✅已修 | 跳过 rd0 装载（写 rd0 会 ILLI） | 链例全绿、0 例误触 ILLI |
| F6 证据脚本：检查名含反引号被 shell 当命令、镜像数误用「点数」、summary 取错行 | ✅已修 | 去反引号；镜像数 = 链例镜像 + 故障例；`grep 镜像通过` | `run.sh` 17 项全绿 |
| F7 `shl.w`/`shr.*` orrr 的 `hd[5:4]`：spec §2 表「应为零 + shamt>N ⇒ ILLI」与 §2.2「低 4 位参与」冲突 | ⏸延后 | 用例取「低 4 位掩码」口径并覆盖 `shamt=16`（三平台一致）；措辞收窄属 spec 任务 | 三方 77/77（含该 2 点） |

判决：F1–F6 已修并复验；F7 是 spec 措辞裁定（本任务不可决，且不影响用例）⇒
**无未修 finding**，状态置 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录**（reviewer 亲跑；HEAD `5786b6a2`；`git status -uall` 验收前/后均空，仅本审阅记录为新改动）

- `./.work/evidence/m13-testcases-025/run.sh`（三平台 ics150，日志 `.work/log/testcases/m13-testcases-025-reviewer-run1.log`）⇒
  `合计 17 项检查，失败 0 项` / `RUN_EXIT=0`；现场派生 `链例 21 个镜像（335 点）+ 故障例 56 = 77`、`77/77`、`模型字节流 vs 三方（63 文件）0 偏差`、`sweep covered=273 md5=2d4d94651346ef673c5a855e024c1489`、注入自检 2 路均 FAIL→还原回绿。
- 三方产物独立复核：node JSON 77 条（21 chain 三平台 rc 全 0、bytes=8×点且和 335；56 fault 三平台 rc 全 `248=0xF8`）；reviewer 对 63 份链例输出自跑 `cmp`（chipyard↔qemu↔gem5）⇒ **差异 0**。
- reviewer 自写复算 `reviewer_oracle.py`（按 `SimRISC-09/04` 独立实现，不读 engineer 脚本）⇒ `ids=21 复算点=335 偏差=0` `EXIT=0`：核 `shl.w` 高 16 位清零、`shr.sw` 先符号扩展再移位（`0x8000>>15⇒−1`）、`rol.w` 循环、`rev.w` 块内单元倒序、`mul.uw` 16×16 取低 16、`div/rem` 定值表与向零截断、`cmp.sw/uw` 16 位比较（−1/0/1 写满 64 位），并核编码字 mask/value+位域、故障判据、点号 1..N 连续。
- 门控：`check-tests-index` rc=0（385 条）、`check-case-ledger` rc=0（2184 条）、`validate-vectors` rc=0（723 例/156 id、gap 0）、`check-dirs`/`check-no-residue` PASS；`make check-inst` ⇒ `CHECK_INST_EXIT=2`，红集**恰** `divrem.yaml[23]`（`1141 total / 1135 passed / 1 failed / 5 deferred`）——`semantics_gate.py` 载体集 = `CARRIER_DIRS` 下 git 跟踪 YAML，本任务未改任何该类 YAML ⇒ 输入集与任务前相同，红为既有 pin（`MIGRATION.md §6`/`021`），与本任务无交集。
- 独立注入 1 路：`shr.uw_orrr_rd.S` 点 4 boundary 期望 `…0001→…0002` ⇒ `run.sh --no-platform` `INJECT_RUN_EXIT=1`（`独立复算 期望=0 实际=1`）；`cp`+md5 还原（`066a49fe34f17fc501dab9020ecbf860` 前后相等）⇒ `RESTORE_RUN_EXIT=0`、`失败 0 项`、`git status` 空。

**约束核验**：① 21 个 `.S` == §范围 21 id（无缺无多），点号连续 ≤127（最大 29），各文件头部分类和 = 链例+故障例 现场核一致；② 三平台 77/77、故障全 `0xF8`、链例字节流三方一致（reviewer `cmp` 0 差异）；③ 独立复算 335 点 0 偏差（非采信 engineer oracle）；④ F7：spec §2（`hd[5:4]` 应为零 + `shamt>N ⇒ ILLI`）与 §1.4/§2.2（低 4 位参与）确有张力，`discussing.md`（主工作树，2026-11-14，024/025）已记待裁定，本册 `shl.w_orrr[9]`/`shr.uw_orrr[10]`/`shr.sw_orrr[9]` 以 `shamt=16 ≡ 0` 覆盖且三平台一致 ⇒ **不判缺陷**；⑤ 片段 21 条可解析、id `001..021` 合法唯一、file 存在、与根清单（185 条）id/file 零重叠，根清单/`MIGRATION.md`/`README`/宏层/驱动器零改动（`git diff --name-only 3d6ca5f3..5786b6a2` = 21 `.S` + 2 片段 + 任务书，与完成区声明一致）；⑥ 完成区 6 行、无运行期路径，各项数字与我方重跑逐条对齐；⑦ 越界无。

**Findings（不阻断，architect 收尾处置）**
- D1（文档级）：片段 `m13-testcases-025.migration.md` 写「链例 318 点」「每 id 11–19 链例」，现场 335 点、每 id 链例 13–21；该数字不被任何门控读取 ⇒ 改片段文本即可。
- D2（判据级）：验收 4「`make check-inst` rc=0」与现场 rc=2 冲突，红为既有 pin 且输入集与本任务无交集 ⇒ 需 architect 改该子项口径（同验收 1 的 16→21），非 engineer 缺陷。

**判决：Accepted** —— 验收 1/2/3/5/6/7 全部由 reviewer 重跑通过；验收 4 的 md5/`check-tests-index` 子项通过，`check-inst` 子项按 D2 交 architect 改判据。

## 完成区

**测试结果**：`.S` 21/21（按任务书 §范围 现场核 id 清单）；点号连续且 ≤127（链例 335 点 + 故障例 56 = 77 个镜像）；三方逐字节 **77/77 全绿**（chipyard == QEMU == gem5；56 个故障例退出码全 `0xF8`）；独立复算 335 点 + 56 故障例，不符 **0**；模型派生字节流 vs 三方各自输出（63 个文件）0 偏差；反例注入 2 路（改错 boundary 期望 / 改坏编码字 opc）均 FAIL，`cp`+md5 还原后回绿；片段 21 条（`yaml.safe_load` OK、id 合法唯一、file 存在）；273 例 sweep md5 `2d4d94651346ef673c5a855e024c1489` 不变。
**修改文件**：新增 `tests/inst/09-arith-logic-wyde/*.S`（21 个）；新增 `tests/inst/.fragments/m13-testcases-025.inst.yaml`、`tests/inst/.fragments/m13-testcases-025.migration.md`；本任务书（完成区/审阅记录/状态）。未改根清单、`MIGRATION.md`、`README.md`、宏层、驱动器、台账。
**验收结果**：证据脚本 17 项全绿（rc=0）；`check-tests-index` rc=0（385 条）、`check-case-ledger` rc=0（2184 条）、`validate-vectors` rc=0（723 例/156 id、gap 0）、`check-dirs`/`check-no-residue` PASS；`make check-inst` rc=2、红集仍**恰** `divrem.yaml[23]`（1141 total / 1135 passed / 1 failed / 5 deferred）——与本任务前一致（该红 pin 见 `MIGRATION.md §6` 的 `021` 条）。
**新发现/坑**：① 任务书验收 1 写「== 16」与 §范围/§4 表（21）冲突，按 §范围 取 21（现场 21 个 `.S`）；② `shl.w`/`shr.*` orrr 的 `hd[5:4]` 口径 spec 两处措辞冲突（见 F7），本册按低 4 位掩码覆盖并三平台一致，建议 spec 收窄（`rol.w` 已明示低 4 位）；③ `llvm-mc` 对 `immu6>15` 与 `rev.w k∉{1,2,4,8}` **不报错** ⇒ orri 越界故障例可直接用助记符宏，无需原始编码字；④ `shr.sw` 必须「先 16 位符号扩展再算术右移」（`0x8000>>15 ⇒ −1`），「先移位再扩展」会错。
**遗留问题**：F7 的 spec 措辞裁定（不影响用例：现覆盖取掩码口径）；YAML 五册未删（仍含 32/8 位 id 且受 `MIGRATION.md §5.1` 前置阻塞）；根清单合并与 `check-*` 复跑归主会话；`make check-milestones-fresh` rc=2（台账 `milestones-m12.md` 的 025/026/035 行仍在「待开始」——台账归主会话，本任务不改台账；该 R1 违规在改状态前即存在）。
