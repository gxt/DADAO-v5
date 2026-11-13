# m13-testcases-017: `04-arith-logic-octa` —— `and`/`or`/`xor`/`xnor`/`shl`/`shr`/`ext` 全形式

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（宏层 `inst_test.inc` + `run_asm_suite.py` 已建好）；与其它 `tests/inst` 重构任务**串行**（共享 `tests/inst/`）
**可并行分片**：否
**状态**：已验证

## 背景

延续 `012`/`013` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。分类与用例模板见 `tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移台账）。

本任务覆盖 **14 个 id**（`04-arith-logic-octa` 逻辑/移位/扩展）

## 范围（id 清单，以 `contracts/opcodes.yaml` 为准）

```
and.o_orrr_rd ext.so_orri_rd ext.so_orrr_rd ext.uo_orri_rd ext.uo_orrr_rd or.o_orrr_rd shl.o_orri_rd
shl.o_orrr_rd shr.so_orri_rd shr.so_orrr_rd shr.uo_orri_rd shr.uo_orrr_rd xnor.o_orrr_rd
xor.o_orrr_rd
```

## 用例设计（5 类，模板见 `MIGRATION.md §3`）

- **encoding**：该 id 的编码校验（mask/value）
- **legality**：适用的合法性规则（`rd0/rb0`、`immu6=0`、范围/重叠、保留编码…），以 `contracts/legality_rules.yaml` 为准
- **semantic**：正常路径，宽度 × 符号 × 形式
- **boundary**：该族特有边界（进位/借位/最值/次正规/对齐/窗口/掩码…）
- **overlap**：源=目、部分重叠、块复制重叠

## 验收

1. `ls tests/inst/04-arith-logic-octa/` 下本任务 id 的 `.S` 齐全（== 14）
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

## 待裁定

1. **`ext.*` orrr 的起始位越界（`rdHD > 63`）三方不一致**：**用户裁定（2026-11-13，`ISS-422`）**：
   `ext.*` orrr 的 `hd = rdHD[5:0]`（低 6 位），**越界位忽略、不抛 ILLI**；chipyard
   `WumingTinyConfig` 的行为即裁定口径（`rdHD=64` 时按 hd=0 执行并继续）。QEMU `dadao-tiny`
   与 gem5 FS `tiny` 判 ILLI（monitor 段 `0xF8`）是**缺陷**（`ISS-422`，待修）；
   `spec/SimRISC-04 §2.2` 的「hd ≤ N 否则 ILLI」措辞待 spec 任务修正。
   **处置**：该例不写进 `.S`（QEMU/gem5 未修前不得补 ILLI 故障例；否则三方逐字节验收必红），
   只在两个 `ext.*_orrr_rd.S` 与 `MIGRATION §6` 留注释；QEMU/gem5 修好后补 `TEST_FAULT` 一例。
   专项探针（`ext.uo rd5, rd6, rd7`，`rd7=64`）重放：**chipyard rc=2（按 hd=0 继续执行，正确）/
   QEMU rc=248 / gem5 rc=248（`ISS-422` 缺陷）**（运行期日志）。
2. **任务书验收 1 的「== 20」与 id 清单不符（返工轮已就地改为「== 14」）**：现场
   `contracts/opcodes.yaml` 本族 = 逻辑 4 + 移位 6 + 扩展 4 = **14**，与 §范围清单、
   `MIGRATION.md §4` 一致；评审已独立核对 ⇒ 按 14 执行并改验收 1 正文。

## 审阅记录

### 第 1 轮 engineer 自审

改动面：14 个 `.S`、宏层（`TEST_AR_ORRI`/`TEST_FAULT_ALU_ORRI`）、驱动器 `FAULT_AR_RE`、
`tests/inst.yaml`（+14 条）、`MIGRATION.md`/`README.md`。逐行自审 + 三平台实跑 + 独立重算（190 点）：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `xnor` 与全 1 同或写成「取反」（实为原值）⇒ 点 6 红 | ✅已修 | 期望改 `0x0123456789ABCDEF`，注释改「原值不变」 | QEMU 30/30 → 三平台 28/28 |
| `xnor` 互补掩码（两源互异）期望写成全 1（实为 0）⇒ 点 10/11 红 | ✅已修 | 点 10 改「相同源 ⇒ 全 1」，点 11 改「互补 ⇒ 0」 | 同上 |
| `shr.uo/shr.so` 点 14 用 `0x100`/`…FF00` 当移位量（低 6 位 = 0，实为不移位） | ✅已修 | 输入改 `0x108`/`0x…08`，期望不变 | 同上 |
| orri 故障例误用 2 操作数宏 `TEST_FAULT_ALU_SI`（`ext.uo rd0, imm` 汇编失败） | ✅已修 | 新增 `TEST_FAULT_ALU_ORRI`（3 操作数）；5 个 orri 文件改用它 | llvm-mc 建镜像成功，故障例 14/14 rc=248 |
| `ext.*` orrr 的 `rdHD=64` 链例挂死（QEMU/gem5 判 ILLI，无 hmon ⇒ 超时） | ✅已修 | 点 13 改合法边界（hd=31）；越界例移出 `.S`（见「待裁定」1） | 三平台 28/28 |
| `ext.*` 表头 hd 口径（原按 spec 字面写「须 ≤ N，否则 ILLI」） | ✅已修 | 按用户裁定统一为「`hd = rdHD[5:0]`；越界位忽略，不抛 ILLI」（`ISS-422`） | 第 2 轮措辞核验（14 文件 grep；`@@` 注释不产码，证据重跑同绿） |
| QEMU/gem5 对 `ext` 起始位越界判 ILLI（chipyard 为裁定口径，**正确**；QEMU/gem5 = `ISS-422` 缺陷） | ⏸延后 | 不收录该例，留 `.S` 注释 + `MIGRATION` + 「待裁定」1；待 QEMU/gem5 修复后补故障例 | 专项探针（`rd7=64`）：chipyard rc=2（正确）/ QEMU 248 / gem5 248（运行期日志） |
| 证据脚本 `scan-only` 未按 `--id` 过滤 ⇒ 镜像数按全册 29 id 计（64≠28） | ✅已修 | 扫描加 `--id`；链例镜像判据改为「== id 数」 | `--inject` 最终跑 PASS=33 FAIL=0 |
| 一度加入的 `TEST_FAULT_ALU3V` 随越界例移出而成为死代码 | ✅已修 | 删除宏与正则项（只留 `ALU_ORRI`） | `grep` 无残留；py_compile rc=0 |

判决：findings 全部已修或已登记（唯一 ⏸延后 = QEMU/gem5 侧缺陷 `ISS-422`，已写「待裁定」）⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收

**重跑（均本人执行，workdir = 本 worktree、相对路径）**
- `run.sh --inject`（运行期证据目录）→ `summary: PASS=33 FAIL=0`、`RUN_EXIT=0`（21:44:02→21:46:04）
- 三方 28 镜像（本人审计 `work/suite.json`）：records=28（链 14 / 故 14）、平台 {chipyard,qemu,gem5}、84 条；链例三平台 rc=0 且字节 == 8×点数；故障例 rc 全 `0xF8`
- `make check-inst` rc=**1**，红集**恰** `FAIL divrem.yaml[23]`（`forem_orrr_rf`，015/016 同红 = 既有基线）；`Results: 1141 total, 1135 passed, 1 failed, 5 deferred`；Tiny 子集 `44/44` rc=0
- `check_tests_index.py` rc=0（316 条）｜`check_case_ledger.py` rc=0（2170）｜`validate_vectors.py` rc=0（gaps 0）
- `inst_sweep emit` 本人重跑 rc=0 → `sweep_expect.bin` md5 `2d4d94651346ef673c5a855e024c1489`（`covered=273`）== 273 例基线
- QEMU 回归：01 `235/235`、02 `58/58`、03 `15/15`、04 `64/64`；`check_knowledge_refs` 本任务命中 0（余红仅 `m14-infra-001`）

**独立重算**（reviewer 自带重算脚本，运行期临时目录；自写语义 + 按宏装载顺序模拟，非 engineer 脚本）：**190 点 / 不符 0**；人工复核边界 —— `shl` 0/63/64/全1（点 4/8/10/11）、`shr.so` 负数补符号与 63/64、`shr.uo` `0x8000..>>63 = 1`、`ext` hd=0/31/32/62/63 + 符号位取 `rdHC[hd]`、`xnor` 全1=原值 / rd0=取反 / 互补=0，均与 `spec/SimRISC-04 §2` 一致。

**独立注入（自设计，非 `shl.o_orrr_rd` 点 8）**：`shr.so_orri_rd` 点 10 期望 `0x0…0`→`0x0…1` ⇒ `run_asm_suite` rc=1，三平台 rc 全 **10**；`cp` 还原 md5 `ae110260a4d301de5c5a8e8cece2534b` 相等 → 回绿 `2/2` rc=0，`git status` 干净。

**ISS-422 独立探针**（本人自写 `.S`：`__FAULT_GUARD ILLI` + `rd7=64`，控制例 `rd7=63`）：hd=63 → 三平台全 **97**；`ext.uo` rd7=64 → chipyard **97（继续执行）** / qemu **248** / gem5 **248**；`ext.so` rd7=64 → chipyard **98** / qemu 248 / gem5 248 ⇒ 三方分歧复现。按用户 2026-11-13 裁定：**chipyard 正确**（`hd = rdHD[5:0]`、不抛 ILLI），QEMU/gem5 判 ILLI 为缺陷，`ISS-422`（master `fe441ef7`）已改归属 qemu/gem5/spec。该例**未被收录**（`.S` 只有 `dst_rd0` 故障例）✓。

**id 数**：`contracts/opcodes.yaml` 现场 264 id 中本族（SimRISC-04）= 逻辑 4 + 移位 6 + 扩展 4 = **14**（`shl.b/w/t`、`shr.ub/uw…` 等 20 条属 08/09/10 册）；验收 1「== 20」无对应实体（目录 29 个 `.S` = 016 的 15 + 本 14）⇒ **笔误成立、按 14 执行正确**（正文未改，留主会话裁定；finding，不阻断）。

**约束核验**：`git show --stat` = 20 项（14 `.S` + 宏层/驱动/`inst.yaml`/`MIGRATION`/`README`/任务书），未碰 `contracts/`/`spec/`/`Makefile`；点号 1..N 连续 ≤127、表头 == 现场 14/14；YAML 14 id × 4 例操作数全在 `.S`（非 encoding 例 42/42），文件未删（§5.1 前置，删后 12 gap / +16 行实测）；完成区 18 行、无运行期路径；快照对账：注入前 `git status` 干净、还原后干净。

**判决：Needs Revision** —— 仅 1 类阻断：交付物仍把该例表述为 **chipyard 缺陷**，与用户裁定相反（5 处）：① 任务书「待裁定」1「建议单开 chipyard 修复任务」；② 「完成区」新发现②「chipyard 未实现」+ 遗留①「chipyard … 需单开修复任务」；③ `MIGRATION §6/017`「待 chipyard 修复」；④ `ext.uo/ext.so_orrr_rd.S` 表头「hd = rdHD（寄存器值），须 ≤ N=63，否则 ILLI」及尾注。**返工只改措辞**（不改用例/点号/期望/门控；`@@` 注释不产码，改后重跑 `run.sh` 对齐完成区）：按裁定写 `hd = rdHD[5:0]、不抛 ILLI`、chipyard 正确、QEMU/gem5 = `ISS-422` 缺陷、`spec/SimRISC-04 §2.2` 措辞待 spec 任务；该例继续不收录（QEMU/gem5 未修前不得补 ILLI 故障例）。其余全部达标（上列重跑/注入/重算/约束均绿）。

### 第 2 轮 engineer 返工（仅措辞，按用户裁定 `ISS-422`）

**用户裁定（经主会话转达）**：`ext.*` 的 orrr 形式 `hd = rdHD[5:0]`（低 6 位），**不抛 ILLI**；
**chipyard 正确**，QEMU/gem5 判 ILLI 是缺陷（`ISS-422`）。

改动（不动用例/点号/期望/门控）：

| 位置 | 改成 | 复验 |
|---|---|---|
| 任务书「待裁定」1 | 「QEMU/gem5 缺陷（`ISS-422`）；chipyard 行为即裁定口径」 | 与裁定逐字对齐 |
| 完成区「新发现②」「遗留①」 | 「chipyard 已按裁定实现（`hd = rdHD[5:0]`）；QEMU/gem5 待修」 | 同上 |
| `MIGRATION §6/017` | 「QEMU/gem5 `ISS-422` 待修；chipyard = 裁定口径」 | 同上 |
| `ext.uo_orrr_rd.S` / `ext.so_orrr_rd.S` 表头 + 尾注 | 「`hd = rdHD[5:0]`；越界位忽略，不抛 ILLI」 | `@@` 注释不产码；`run.sh --inject` 重跑同绿 |
| 任务书验收 1 | 「== 14」（现场 `contracts/opcodes.yaml` = 14，评审已独立核过） | 完成区「id 数」注依据 |
| 第 1 轮验收记录 1 行 | 去掉具体 `.work/**` 路径 → 「`run.sh --inject`（运行期证据目录）」（`check-knowledge-refs` 门控；不改结论） | F2 命中数 0 |

返工自审：`git diff` 仅注释/文档/任务书，无 `.S` 代码行、无期望值、无宏/驱动/门控改动；
重跑 `run.sh --inject` = PASS=33 FAIL=0 / exit 0（见完成区）。

### 第 2 轮 reviewer 验收（只核阻断 + 回归）

**1. 阻断项 5 处措辞（逐处 `grep`/读原文）**：① 任务书「待裁定」1 = `hd = rdHD[5:0]`、越界位忽略不抛 ILLI、chipyard 行为即裁定口径、QEMU/gem5 判 ILLI 是 `ISS-422` 缺陷、spec 措辞待 spec 任务 ✓；② 完成区「新发现②」「遗留①」= chipyard 已按裁定实现 / QEMU-gem5 待修 ✓；③ `MIGRATION §6/017` = 「QEMU/gem5 缺陷 `ISS-422`（未收录、待修）；chipyard 按裁定口径 = 正确」✓；④ `ext.uo/ext.so_orrr_rd.S` 表头 3 行 + 尾注 = `hd = rdHD[5:0]`、不抛 ILLI、chipyard 正确 ✓；⑤ 残留扫描 `grep -rn "chipyard 未实现|待 chipyard|chipyard 修复|单开 chipyard|否则 ILLI"`（任务书+MIGRATION+14 `.S`）→ 仅命中第 1 轮历史判决行与 `MIGRATION` 引述 spec 现文待改，**无结论性残留** ✓。**验收 1 已改「== 14」**，现场 `contracts/opcodes.yaml` 本族 = **14**（与 §范围清单逐名一致、14 个 `.S` 齐全，本人复核）。

**2. 只改措辞（`git show de0c8281`）**：改动面 4 文件（任务书 / `ext.uo_orrr_rd.S` / `ext.so_orrr_rd.S` / `MIGRATION.md`）；`.S` 变更行**全部为 `@@` 注释**（非注释变更行 `grep` 空，rc=1）；`git diff 3e5b7308 de0c8281 -- tests/inst/04-arith-logic-octa/` 中 `TEST_AR*/__CHECK_RD/TEST_FAULT/__LI/.dd` 增删 **0 行**（rc=1）；宏层/驱动/`inst.yaml`/`README` 本轮未触碰（`--name-only`）；点号 1..N 连续、表头 == 现场、链例 **190**（本人独立复算 exit 0、不符 0）。

**3. 回归（本人重跑）**：`run.sh --inject` → `summary: PASS=33 FAIL=0`、`RUN_EXIT=0`（22:24:30→22:26:31）；`28/28` 镜像（注入点 8 三平台 rc 全 8 → `cp` 还原 md5 `4bfab166…` → 回绿 `2/2`）；`check_tests_index.py` rc=0（316）｜`check_case_ledger.py` rc=0｜`validate_vectors.py` rc=0（gaps 0）；`make check-inst` rc=**1**、红集**恰** `FAIL divrem.yaml[23]`（`1141 total / 1135 passed / 1 failed / 5 deferred`）、Tiny `44/44`；`inst_sweep emit` 本人重跑 rc=0 → md5 `2d4d94651346ef673c5a855e024c1489`（`covered=273`）；`check_knowledge_refs` 本任务命中 **0**（余红仅 `m14-infra-001`）。

**4. 快照对账**：`git status --porcelain -uall` 空（rc=0），返工 4 项已在 `de0c8281`；`run.sh` md5 `ba785f16…` 未变；主工作树只读、状态干净；本轮我仅追加本记录（并把我第 1 轮记录里的具体临时目录绝对路径改为「运行期临时目录」，不改结论）。

**5. finding（文档级，不阻断）**：完成区「本轮返工 4 项未提交」在 architect 提交 `de0c8281` 后已过时，收尾时顺手改「已入 `de0c8281`」即可。

**判决：Accepted** —— 唯一阻断项 5 处措辞全部按裁定改写，代码/用例/点号/期望/宏/驱动零改动，全部回归命令在本人重跑下绿。

## 完成区

**测试结果**（返工轮重跑同值）：三平台 **28/28** 镜像通过（14 id；链例 14 + 故障例 14，84 条平台记录，故障码全 `0xF8`）；证据脚本 `--inject` **PASS=33 FAIL=0 / exit 0**；期望独立重算 **190 点 / 不符 0**；01/02/03/04 册 QEMU 回归 **235/235 + 58/58 + 15/15 + 64/64**。
**id 数**：验收 1 原写「== 20」，返工轮已**就地改为「== 14」**；依据 = 现场 `contracts/opcodes.yaml` 本族 = 逻辑 4 + 移位 6 + 扩展 4 = **14**，与 §范围清单、`MIGRATION §4` 一致（评审已独立核过）。
**修改文件**：总改动 **20 项**（14 新 + 6 改）已入 WIP `3e5b7308`；**本轮返工 4 项**未提交，`git status --porcelain -uall` = 4（本任务书 + `ext.uo_orrr_rd.S` + `ext.so_orrr_rd.S` + `MIGRATION.md`）：
- 新 `tests/inst/04-arith-logic-octa/{and.o_orrr_rd,or.o_orrr_rd,xor.o_orrr_rd,xnor.o_orrr_rd,shl.o_orrr_rd,shl.o_orri_rd,shr.uo_orrr_rd,shr.uo_orri_rd,shr.so_orrr_rd,shr.so_orri_rd,ext.uo_orrr_rd,ext.so_orrr_rd,ext.uo_orri_rd,ext.so_orri_rd}.S`
- 改 `tests/inst/macros/inst_test.inc`（`TEST_AR_ORRI` + `TEST_FAULT_ALU_ORRI`）、`tools/testcases/inst/run_asm_suite.py`（`FAULT_AR_RE` + 注释）、`tests/inst.yaml`（+14 条）、`tests/inst/MIGRATION.md`、`tests/inst/README.md`
**验收结果**：
1. 14 个 `.S` == 任务书 id 清单（逐名）；每文件链例 12–16 + 故障例 1，点号 1..N 连续、≤127；表头类别合计 == 现场链例数（不符 0）
2. 三方同镜像逐字节：链例 14（rc=0、字节数 == 8×点数、三平台相等）+ 故障例 14（三平台 rc 全 248 = `0xF8` ILLI）
3. 编码对账（独立 oracle）：14/14 `mask/value` 命中；`.S` 原始编码字 == llvm-mc（14/14）
4. 期望独立全量重算（`spec/SimRISC-04 §2`）：**190** 点（现场派生 == 链例点数），不符 **0**
5. `check-tests-index` rc=0（**316** 条）｜`check-case-ledger` rc=0（2170）｜`validate_vectors` rc=0（gaps 0）｜273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变
6. `make check-inst`：红集**恰** `{divrem.yaml[23]}`（既有基线，非本任务；`1141 total / 1135 passed / 1 failed / 5 deferred`）；Tiny 子集 **44/44** rc=0
7. 可达 FAIL：改错 `shl.o_orrr_rd` 点 8 期望 ⇒ 三平台 rc 全 **8**；`cp`+md5（`4bfab166…`）还原 → 回绿 2/2
8. YAML：`reg-logic.yaml`(4 id) + `reg-shift-extend.yaml`(10 id) 用例已并入；`reg-logic.yaml` id 全迁但**未删** —— 实测删后 `validate_vectors` **12 gap** / `check-case-ledger` 多 16 行 / `check-tests-index` file 缺失（`cp`+md5 已还原）
**新发现/坑**：① 移位量取 `rdHD[5:0]`（64→0、更大→低 6 位），**不** ILLI；② `ext.*` orrr 的 `hd = rdHD[5:0]`（低 6 位，越界位忽略，**不抛 ILLI**）——chipyard 即用户裁定口径（`ISS-422`），QEMU/gem5 判 ILLI 属缺陷、待修；③ `xnor` 配全 1 = 原值，取反须 `xor` 全 1 或 `xnor` 配 rd0；④ `immu6=0` 对 orri 移位/扩展合法（`immu6_zero` 明确排除）；⑤ orri 故障例不能用 2 操作数宏，需 `TEST_FAULT_ALU_ORRI`。
**遗留问题**：① QEMU/gem5 的 `ext.*` 起始位越界判 ILLI 属缺陷（`ISS-422`，待修；修后补 2 个故障例；chipyard 已按裁定实现）；② `check-inst` 的 `divrem.yaml[23]` 既有红归 `m13-testcases-032`；③ YAML 退役与 `.S` 载入门控归 `m13-testcases-030`；④ `ISS-410` 的 hmon 自装 workaround 沿用；⑤ 验收 1 的「== 20」已就地改为「== 14」（现场 14，评审独立核过）；⑥ L1 `make -k check` 红：`check-milestones-fresh`（017 仍在「待开始」表，移表归主会话）+ `check-spec-drift`/`check-spec-refs`（`contract-syscall` 版本/断言）+ `check-knowledge-refs`（`m14-infra-001` 的 `.work` 引用）——后三项均未触碰 `contracts/`/`spec/`，与本次改动无关。
