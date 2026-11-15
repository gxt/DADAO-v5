# m13-testcases-015: `03-wyde-imm` —— `set.zw`/`set.ow`/`or.w`/`andn.w`/`set.w`

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（宏层 `inst_test.inc` + `run_asm_suite.py` 已建好）；与其它 `tests/inst` 重构任务**串行**（共享 `tests/inst/`）
**可并行分片**：否
**状态**：已验证

## 背景

延续 `012`/`013` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。分类与用例模板见 `tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移台账）。

本任务覆盖 **8 个 id**（03 16 位立即数操作 册：`set.zw`/`set.ow`/`or.w`/`andn.w`/`set.w`）。

## 范围（id 清单，以 `contracts/opcodes.yaml` 为准）

```
andn.w_rwii_rb andn.w_rwii_rd or.w_rwii_rb or.w_rwii_rd set.ow_rwii_rd set.w_rwii_rf set.zw_rwii_rb
set.zw_rwii_rd
```

## 用例设计（5 类，模板见 `MIGRATION.md §3`）

- **encoding**：该 id 的编码校验（mask/value）
- **legality**：适用的合法性规则（`rd0/rb0`、`immu6=0`、范围/重叠、保留编码…），以 `contracts/legality_rules.yaml` 为准
- **semantic**：正常路径，宽度 × 符号 × 形式
- **boundary**：该族特有边界（进位/借位/最值/次正规/对齐/窗口/掩码…）
- **overlap**：源=目、部分重叠、块复制重叠

## 验收

1. `ls tests/inst/03-wyde-imm/` 下本任务 id 的 `.S` 齐全（== 8）
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

改动面：`tests/inst/03-wyde-imm/`（8 个 `.S`）、`tests/inst/macros/inst_test.inc`（宏层 + WDATA/WSCRATCH + `rb27`）、
`tools/testcases/inst/run_asm_suite.py`（3 个正则）、`tests/inst.yaml`（+8 条）、`MIGRATION.md`、`README.md`。
逐行自审 + 三平台实跑 + 独立重算复核，findings 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `rf0/wp2` 位映射错：把 `[33:32]` 当成 wp2 立即数的 `[9:8]`（用例写 `0x0300`、宏算 `(imm>>8)&3`）⇒ QEMU 点 15 红（rc=15） | ✅已修 | 用例改 `0x03FF`、宏改 `(imm & 3)`（顺带让「未加掩码写整 wyde」也可检：`0x03FF` 上位非零） | QEMU 先红后绿；三平台 15/15；QEMU `store_rf`/chipyard `WumingFcsr`/gem5 `b2.cc` 三处掩码 `0x30000001F` 逐处核对 |
| 证据脚本双引号里的反引号 `` `.S` `` 被命令替换 ⇒ 日志 `command not found`、A2/C/C2 标题被截断（014 reviewer 已记录同款） | ✅已修 | 去掉反引号 | `bash -n` rc=0；重跑标题齐、`summary: PASS=27 FAIL=0` |
| 编码对账正则 `^@@ 规范编码字` 未允许**前导制表** ⇒ 8/8 报「(缺)」、C 段假红 | ✅已修 | 改 `^\s*@@ 规范编码字` | C 段 8/8 `OK` + `.S 原始字 == llvm-mc` |
| 独立重算脚本首版正则漏普通 `TEST_WI_*` 行 ⇒ 每文件只核 3 点（`_MEM`/编码点） | ✅已修 | 正则补普通变体与期望列 | 每文件 14 点（`set.w` 13）、合计 **111** 点、不符 0；注入错期望 ⇒ 脚本 rc=1（可达 FAIL） |
| 宏参数 `\imm` 参与 `((\imm) >> 8) & 3` 时依赖「立即数位宽」假设（错误来源同 finding 1） | ✅已修 | 改为 `(\imm) & 3` / `(\imm) & 0x1F`，全部按 wyde 低位取 | 上述三平台绿 |
| `check-inst` 在 master 基线有既有红 `divrem.yaml[23]`（`m13-qemu-009` 现场登记、由 `m13-testcases-032` 收口）⇒ 无法以 rc=0 判 | ✅按基线判 | 证据 E 段改判「红集**恰** == {divrem.yaml[23]}」+ Vast 短路后单独跑 Tiny 子集 | 红集逐字相等；Tiny **44/44** rc=0；计数 1135/1141 + 5 deferred 与 `m13-qemu-009` 记录一致 |
| `.S` 头未说明「链接布局复用 01 册」「探针为何不借被测指令」「`_MEM` 为何必要」 | ✅已修 | 8 个文件头补齐三行（含 `wp0..wp3` 位映射） | 8 文件头齐；A2 表头审计不符 0 |

判决：findings 全部已修 ⇒ 状态可置 `待验收`。`set.w` 的 rf0 四点（13–16）由**运行时**从写前值派生期望，
故不在「逐例重算」覆盖内（111 = 115 − 4）；其可达 FAIL 已由 finding 1 的实跑（QEMU rc=15）证实。

**过程披露**：写本任务书时误将「完成区」整文件覆盖（原 59 行被替换）⇒ 用 `git show HEAD:<path>` 读回
基线原文重建（仅 `**状态**` 改为 `待验收`、`（待填）` 换成两段记录），逐行 diff 已核「除状态行外零差异」；
未改动任务书其它正文，也未用它还原任何**注入**（注入还原一律 `cp`+md5）。

### 第 1 轮 reviewer 验收

**重跑（全部本人执行；下列为现场输出/退出码，不采信完成区）**
1. `python3 tools/testcases/inst/run_asm_suite.py --vectors tests/inst/03-wyde-imm --lds tests/inst/01-load-store/inst-tiny.lds --scan-only` → rc=0：8 id / 15 镜像，点号 1..14（`set.w` 1..17）连续、≤127。
2. 一键证据脚本（运行期证据目录 `evidence/<任务ID>/run.sh`）→ rc=0，`summary: PASS=21 FAIL=0`（76 s）；加 `--inject` → rc=0，`PASS=27 FAIL=0`（F 段改 9 号期望 → 三平台 rc=9 → `cp`+md5 `2f6f2c69…` 还原 → 回绿）。
3. `check-tests-index` rc=0（287 条）｜`check-case-ledger` rc=0（2170）｜`validate_vectors` rc=0（gaps 0）｜`inst_sweep emit` → `sweep_expect.bin` md5 `2d4d94651346ef673c5a855e024c1489`。
4. `make check-inst` → `Results: 1141 total, 1135 passed, 1 failed, 5 deferred`，红集**恰** `{divrem.yaml[23]}`（与 `m13-qemu-009` 现场记录逐字一致）；Tiny 单跑 44/44 rc=0；01/02 册 QEMU 回归 235/235、58/58。
5. `make -k check` → rc=2，失败目标恰 5 个：`check-patch-tree` / `check-knowledge-refs` / `check-milestones-fresh` / `check-run-artifacts` / `check-temp-dirs`。

**独立核验**
- id 清单：`contracts/opcodes.yaml` 现场取 `role=wyde_pos` 的 8 个 id（== `spec/SimRISC-03` 附录 A 的 8 个 id）与 8 个 `.S` 文件名、`tests/inst.yaml` 8 条 `file` 三方**逐名相等**。
- 期望值独立复算（本人脚本、按 16 位 wyde 整字段运算，与逐位实现不同路）：**111 点、不符 0**（含 8 个 `_MEM` 点对 WDATA 表核对，期望不来自被测指令）；`set.w` rf0 4 点系运行时期望，按 spec 写语义手算宏公式 `pre_byte+(imm&3 / imm&0x1F)` 正确且进位不越界。
- 合法性：故障例 7 个 == `opcodes.yaml` 中有 `dst_rd0`/`dst_rb0` 的 7 个 id；`set.w_rwii_rf` 无规则 ⇒ 无故障例。
- 范围/对账：`git show --stat e512efcd` = 14 文件（8 新 + 5 改 + 本任务书），未碰 `contracts/`/`spec/`/`Makefile`；注入前后 `git status --porcelain -uall` 均 0 行、目标文件 md5 与注入前相等；`git rev-parse --show-toplevel` == 作业树，未动主工作树；本轮未提交。

**独立注入（自设计，`cp`+md5 还原，未用 `git checkout/restore/stash`）**
- ① `inst_test.inc` 的 WDATA `+0x40` 改值 ⇒ `set.zw_rwii_rd` 点 7 三平台 rc=**7**；还原 md5 `2996d114…` 相等 ⇒ 回绿 rc=0。
- ② `andn.w_rwii_rd.S` 点 11 期望 `…FF→…FE` ⇒ 三平台 rc=**11**；还原 md5 `54467126…` 相等 ⇒ 回绿 rc=0。

**阻断 finding（2 项，须 engineer 改）**
1. **完成区「验收结果」第 9 项造出本任务自己的门控红**：`make check-knowledge-refs` rc=2、`FAIL (6 具体 .work/** 引用)`，其中第 6 处就是本任务书该行（现场报 `…015.md:122`；基线 `HEAD~1` 同文件该类引用 0 处）；完成区却写「5 处全在 m13-013、对本任务文件命中 0」⇒ 计数与现场不符；同一行还写了具体临时目录路径。**改法**：该行删去具体运行期日志目录/临时目录路径（改「运行期日志目录」「临时目录」措辞）、计数改现场值，重跑 `make check-knowledge-refs` 断言**本任务文件命中 0**（013 的 5 处为既存红，仍 FAIL 属正常）。
2. **证据脚本 C2 段计数写死且覆盖无 FAIL 路径**：`evidence/<任务ID>/run.sh` 第 331 行断言名写死「115 个链例点逐例重算」，现场（其自身 `recompute.log`、完成区、本人复算）均为 **111**；该断言只判 rc ⇒ 万一正则漏行，0 点也 PASS。**改法**：判据改现场派生（scan.log 链例点数 − 显式列出的 `TEST_WI_RF0_*` 运行时期望点），覆盖不足即 FAIL；改后重跑 `--inject` 应 `PASS≥27 FAIL=0`。

其余验收项在本人重跑下全部通过。**判决：Needs Revision**（仅上述 2 项）。本轮 reviewer 只写本审阅记录，其余文件未动。

### 第 2 轮 engineer 自审（返工 R1/R2）

改动面：本任务书「完成区」（R1）+ 运行期证据脚本 `run.sh`（R2）；`.S`/宏层/驱动/索引未动（reviewer 已重跑通过）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1 完成区第 9 项写具体运行期路径（他人任务的日志目录/临时目录）⇒ `check-knowledge-refs` 新增 1 处（本任务书）；且「5 处全在 013、本任务 0」与现场（6 处、含本任务 1）不符 | ✅已修 | 该行删具体路径（改「他人任务的运行期日志目录」「他人任务的临时目录」措辞），计数改现场值并显式断言本任务 0 | `check_knowledge_refs.py`：具体 `.work/**` 引用剩 **5 处、逐条全在 `m13-testcases-013` 任务书**，本任务书命中 **0**（`grep -c` 现场 0）；叠加主树已清基线（`4a2eb89c` 版 013 文件临时替换，`cp`+md5 `f294ca3f…` 还原）复跑 ⇒ **PASS / rc=0（0 处）** |
| R2 证据脚本 C2 断言名写死「115 个链例点」（现场 111），且只判 rc ⇒ 正则漏行时 0 点也 PASS | ✅已修 | 断言改**现场派生**：`NCHAIN`（scan.log 链例合计）− `NRF0`（`.S` 显式 `TEST_WI_RF0_*` 点）= 期望覆盖数，与 `NGOT`（重算日志合计）须逐个相等；脚本内另加「0 点即红」 | 派生 `115 − 4 = 111`、`NGOT=111` ⇒ PASS（`PASS=31 FAIL=0`）；**可达 FAIL 演示**：把审计正则的普通 `TEST_WI_*` 分支改坏 ⇒ 每文件只核 2/3 点、`NGOT=17`、脚本自身 rc=0「无不符」，新断言判 `111 ≠ 17` 红（改坏副本已删） |
| E2 新增哨兵自身的假绿风险：`check_knowledge_refs.py` 在本分支 rc=1（他人任务书余红）⇒ 只判 rc 会把本任务书命中数掩盖 | ✅已修 | E2 不判全局 rc，改判「本任务书命中数 == 0」与「余红条目中本任务文件数 == 0」两个现场派生值，并打印 rc 与余红明细 | 两断言各 `expected=0 actual=0`；余红明细 5 条全为 013 |

判决：两项阻断已修，新增项的哨兵也改为可独立判红 ⇒ 状态保持 `待验收`。

### 第 2 轮 reviewer 验收（返工 R1/R2）

**R1 完成区门控红**
1. 文本面：完成区 18 行，`/tmp/`、`/mnt/`、`/home/` 命中 **0**；`.work` token **仅通配形 `.work/**`**（门控口径：通配形跳过）；第 9 项计数已改现场值（「具体 `.work/**` 引用 5 处、逐条全在 `m13-testcases-013`、本任务文件 0」）。
2. `python3 tools/infra/check_knowledge_refs.py`（worktree 原地跑）→ **rc=1、`FAIL (5 具体 .work/** 引用)`**，5 条逐条 `m13-testcases-013-…md:114/115/146/159/276`，`grep -c m13-testcases-015…` = **0**（第 1 轮为 6 处、含本任务 1 处）。
3. 叠加主树基线（**临时树**：`cp AGENTS.md spec .tao` + `git show 4a2eb89c:<013 任务书> > 临时树`，未动仓库文件）→ `check_knowledge_refs.py --root <临时树>` → **rc=0、`PASS (0 具体 .work/** 引用; 0 悬空小节级互指)`**，本任务书命中 0；并核 `4a2eb89c` **不是** `HEAD` 祖先 ⇒ 完成区「本分支未含主树清理提交」属实。

**R2 证据脚本计数现场派生**
4. 代码核：`NCHAIN`（scan.log 现场求和）/`NRF0`（`.S` 现场数 `TEST_WI_RF0_*`）/`NGOT`（recompute.log 求和）/`NEXPECT=NCHAIN−NRF0`；`NCHAIN>0` 否则 `bad`；内层 `if nchk==0: bad+=1`；E2 判「本任务书命中 0 / 余红中本任务文件 0」两个现场值（不判全局 rc）。
5. **可达 FAIL（我自造两次，`cp`+md5 `8c770149…` 还原，未用 git 还原）**：
   - 改坏 `TEST_WI_(RD|RB|RF)` → `(RD|RB|RZ)`：`set.w` 覆盖 13→3，内层 `重算不符 0` ⇒ `[PASS] 逐例重算 rc actual=0`（**旧只判 rc 的写法在此假绿**），新断言 `[FAIL] …（115 − 4）expected=111 actual=101` ⇒ 脚本 **rc=1**。
   - 再改坏 RD + `__CHECK_RD` 两分支：4 个 rd 文件 `逐例重算 0 点（解析覆盖缺失）` ⇒ `[FAIL] 逐例重算 rc actual=1`、覆盖 `expected=111 actual=55` ⇒ **rc=1**（0 点守卫生效）。
   - 两次还原 md5 均 `8c770149…` 相等；`git status --porcelain -uall` 0 行。

**回归（本人重跑 `run.sh --inject`）**
6. **rc=0、`PASS=31 FAIL=0`**：15/15 三平台；`check-inst` 红集**恰** `{divrem.yaml[23]}`（`1141 total/1135 passed/1 failed/5 deferred` + Tiny `44/44`）；273 例 md5 `2d4d94651346ef673c5a855e024c1489`；`check-tests-index`(287)/`check-case-ledger`/`validate_vectors` rc=0；E2 两断言 `expected=0 actual=0`、余红 5 条全为 013；F 段 9 号注入 → `cp`+md5 还原 → 回绿。

**约束**：未动主工作树；仓库文件零改动（验证全在临时树与运行期证据目录，`run.sh` 前后 md5 相等）；本轮未提交；未重建组件。

**判决：Accepted** —— R1/R2 两项阻断均已修复，且有我自造的可达 FAIL 证据（旧写法假绿、新写法判红），回归全绿。

## 完成区

**测试结果**：三方 **15/15** 镜像通过（8 id；链例 8 / 故障例 7，45 个平台记录）；证据脚本 `--inject` **PASS=31 FAIL=0 / exit 0**；`01-load-store` + `02-reg-copy` 的 QEMU 回归 **235/235 + 58/58**。
**修改文件**（`git status --porcelain -uall` = **14 项**：8 新 + 5 改 + 本任务书）：
- 新 `tests/inst/03-wyde-imm/<8 个 id>.S`
- 改 `tests/inst/macros/inst_test.inc`（`TEST_WI_{RD,RB,RF}{,_MEM}`/`TEST_WI_RF0_{NOOP,WRITE}`/`TEST_FAULT_WI`、WDATA/WSCRATCH、`rb27`）、`tools/testcases/inst/run_asm_suite.py`（3 个正则）、`tests/inst.yaml`（+8 条）、`tests/inst/MIGRATION.md`、`tests/inst/README.md`
**验收结果**：
1. 8 个 `.S` == 任务书 id 清单（逐名对账）；点号 1..14/17 连续、≤127；表头类别合计 == 现场链例数（A2 不符 0）
2. 三方同镜像逐字节：链例 8（rc=0、字节 = 8×点数、三平台字节流相等）+ 故障例 7（三平台 rc 全 248 = `0xF8`）
3. 编码对账（独立 oracle）：8 个 id 的 `mask/value` 由 `contracts/opcodes.yaml` × llvm-mc 规范字逐一命中；`.S` 原始编码字 == llvm-mc
4. 期望值独立全量重算（逐位实现，与生成公式不同路）：覆盖数**现场派生**（链例点数 115 − 运行时期望点 4）= **111** 个链例点 + WDATA 表 → 不符 0；证据脚本 C2 段：覆盖数不等或单文件 0 点均判红
5. `check-tests-index` PASS（287 条）、`check-case-ledger` PASS（2170）、`validate_vectors` gaps 0、273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变
6. `make check-inst`：Vast 红集**恰** == 既有基线 `{divrem.yaml[23]}`（1135/1141 + 5 deferred）；Tiny 子集单独跑 **44/44** rc=0
7. 可达 FAIL：改错 `or.w_rwii_rd` 9 号期望 ⇒ 三平台 rc 全 **9**；`cp`+md5 还原（`2f6f2c69…`）后回绿
8. YAML 未删：`reg-imm-block.yaml` 的 7 个 rwii id 用例已并入（`set.w_rwii_rf` 原无载体），删除仍受 §5.1 前置阻塞
9. L1 `make -k check` rc=2：5 项红全为既存/并行漂移（`check-patch-tree` 的 chipyard 源树在飞、`check-knowledge-refs` 命中全在他人任务书、`check-milestones-fresh` 本 worktree 台账未移「进行中」、`check-run-artifacts` 命中全在他人任务的运行期日志目录、`check-temp-dirs` 为他人任务的临时目录），**本任务文件命中 0**（`check_knowledge_refs.py` 现场：具体 `.work/**` 引用 5 处，逐条全在 `m13-testcases-013` 任务书 —— 本分支基线未含主树的清理提交；叠加主树已清基线复跑本任务书 ⇒ 0 处、rc=0；证据脚本 E2「本任务书命中数 0 / 余红中本任务文件数 0」两断言均 0）
**新发现/坑**：①`rf0` 的 `wp2` 命中 `[33:32]` = wp2 立即数**低 2 位**（不是 [9:8]），`wp0` 的 `[4:0]` = 低 5 位；②`set.w rf0` 写掩码 `0x30000001F` 三平台一致，wp1/wp3 完全写无效；③`__LI` 本身用 `set.zw`/`or.w` 拼常量 ⇒ 本册期望必须有内存装载的 `_MEM` 变体防「期望自证」；④字节级期望可用 `ld.ub`+`add.si`+`st.b` 构造，但前提是被写域已清 0。
**遗留问题**：①`check-inst` 的 `divrem.yaml[23]` 既有红归 `m13-testcases-032`（非本任务）；②`reg-imm-block.yaml` 的 `git rm` 与 `.S` 载入门控归 `m13-testcases-030`；③`ISS-410` 的 hmon 自装 workaround 仍在（本册沿用）；④L1 五项红属既存/并行（见验收 9），本任务无新增红；⑤台账「进行中」行由主会话在主树更新（本 worktree 派单前基线）。
