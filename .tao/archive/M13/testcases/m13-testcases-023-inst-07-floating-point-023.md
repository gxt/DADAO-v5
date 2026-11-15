# m13-testcases-023: `07-floating-point` —— `ftrnd`/`fornd`/`ftsclb`/`fosclb`/符号族

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（宏层 `inst_test.inc` + `run_asm_suite.py` 已建好）；与其它 `tests/inst` 重构任务**串行**（共享 `tests/inst/`）
**可并行分片**：否
**状态**：已验证

## 背景

延续 `012`/`013` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。分类与用例模板见 `tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移台账）。

本任务覆盖 **8 个 id**（`07-floating-point` 取整/缩放/符号）

## 范围（id 清单，以 `contracts/opcodes.yaml` 为准）

```
fornd_orri_rf fosclb_orrr_rf fosgnj_orrr_rf fosgnn_orrr_rf ftrnd_orri_rf ftsclb_orrr_rf
ftsgnj_orrr_rf ftsgnn_orrr_rf
```

## 用例设计（5 类，模板见 `MIGRATION.md §3`）

- **encoding**：该 id 的编码校验（mask/value）
- **legality**：适用的合法性规则（`rd0/rb0`、`immu6=0`、范围/重叠、保留编码…），以 `contracts/legality_rules.yaml` 为准
- **semantic**：正常路径，宽度 × 符号 × 形式
- **boundary**：该族特有边界（进位/借位/最值/次正规/对齐/窗口/掩码…）
- **overlap**：源=目、部分重叠、块复制重叠

## 验收

1. `ls tests/inst/07-floating-point/` 下本任务 id 的 `.S` 齐全（== **8**；判据 = 任务书 §范围 清单）
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

（待填）

## 完成区

**测试结果**：通过 **22/22** 镜像（8 个 id：链例 8 + 故障例 14）；链例 **152** 点 + 故障例 **14** 点 = **166 点**，逐文件点号 1..N 连续、≤127、失败点号 = 用例序号。另跑 07 册全量回归 **170/170**（52 个 id：链例 52 + 故障例 118）。
**修改文件**（11 条，与 `git status -uall` 逐条对账 = 8 新 `.S` + 2 片段 + 本任务书：`M .tao/tasks/testcases/m13-testcases-023-…md`；无既有实现文件改动）：
- 新增 `tests/inst/07-floating-point/{fornd_orri_rf,fosclb_orrr_rf,fosgnj_orrr_rf,fosgnn_orrr_rf,ftrnd_orri_rf,ftsclb_orrr_rf,ftsgnj_orrr_rf,ftsgnn_orrr_rf}.S`（现场核 == 8）；
- 新增 `tests/inst/.fragments/m13-testcases-023.inst.yaml`（8 条 `inst-07-floating-point-045..052`）与 `m13-testcases-023.migration.md`（§1 行 / §5 注 / §6 段；按 §5.3 新协议以**任务号**命名）；**未改** 根清单、`MIGRATION.md`、`README.md`、`macros/inst_test.inc`、`run_asm_suite.py`（片段协议 §5.3；本册宏全部在 `.S` 内局部定义）。
**验收结果**：
- 三方逐字节（同一份 ELF，chipyard/QEMU/gem5；平台二进制 md5：qemu `5d04d3e8…`、gem5 `0542906b…`、chipyard `45748f3f…`）：**22/22**；链例字节数 = 8×检查点（逐 id 核）、故障例三方同码 `0xF8`；07 册全量回归 **170/170**。
- 独立复算（自写模型 B：`decimal` 六档取整 + `struct` 邻居步缩放 + 阈值溢出判据，**不复用**生成端 `fp_ref.py` 的舍入代码）：**166 例 / 不符 0**；并独立反解编码字位域 + `opcodes.yaml` mask/value + 故障例合法性。检查器反例（改错点 12 的 −0 期望）⇒ 命中点 12 非零。
- 注入 2 路（临时向量树，不写工作树）：`ftrnd` 点 12（−0 符号）、`ftsclb` 点 10（OF 位）⇒ 三平台同点号非零（12/12/12、10/10/10），原文件回绿；另做一次仓库内「cp 备份 → 注入 → md5 变 → cp 还原 → md5 等 → 复算回绿」纪律核对。
- 门控（本 worktree）：`check-tests-index` rc=0（385 条）、`validate_vectors` rc=0（gaps 0）、`check-case-ledger` rc=0（2184 条）；片段自校（`yaml.safe_load` 列表 8 条 / id 格式 045..052 / `file` 存在 / 五项字段）；273 例 sweep md5 `2d4d94651346ef673c5a855e024c1489` 不变。
- 覆盖：五类齐全（encoding 2/id、semantic 4–7、boundary 8–12、overlap 1–2、legality 1–4）；标志 `0x00`/`NV`/`NX`/`OF|NX`/`UF|NX` 全档；`ftrnd/fornd` 六档含动态 `0x20`；`ftsclb/fosclb` 指数 0/正/负/±200/±2000、溢出取 Inf 与下溢 `+0`/最小次正规（RUP）对照；`ft` 形式只写低 32 位（目的预置 `0xDEADBEEFCAFEF00D`、期望按整 64 位比较）。
**新发现/坑**：
1. **自查抓到假绿**：`ft` 的「目的高半预置 `0xDEADBEEF`」技巧被误用到 `fo` 用例（`x | HI<<32`）；`0xDEADBEEF` 的置位恰是 `0xC00C0000`/`0xBFF00000`/`0x3FF80000` 的超集 ⇒ OR 静默改写操作数，overlap 用例实际在缩放/取整一个 NaN 量级值，而三平台仍「一致通过」。修法：高半预置只对 `ft` 生效。教训：**三方一致 ≠ 用例在测设计意图**，操作数语义须人工核。
2. 并行任务重建期间 `gem5.opt` 会被写坏（实测 `PermissionError`）⇒ 跑批前须确认 md5 在窗口内稳定并重同步（本轮 `m16-gem5-008` 重建，最终 `0542906b…`）。
3. `sync_node_artifacts.sh` 的逐件 md5 用 `'~/…'` 引号包住 ⇒ `~` 不展开、恒报 MISMATCH（rsync 本身写得对）；以绝对 `REPO=` 绕开。
4. `run_asm_suite.py` 链例正则 `TEST_FP\w*` 会把局部宏体里的 `__CHECK_RD \pt, …` 也当成用例行（点号出现 `-1`）⇒ 本册局部宏内联判据、不调用 `__CHECK_RD`。
**遗留问题**：
1. `fp/roundint.yaml`(46)/`fp/scaleb.yaml`(13)/`fp/sign.yaml`(28) 的 8 个 id 已全部有 `.S` 载体，但三文件**未删**：`scaleb.yaml` 在根清单有 `file:` 条目（删后 `check-tests-index` 红），且受 §5.1 前置阻塞 ⇒ 随 `m13-testcases-030` 批处理。
2. 任务书「验收 1」写「本任务 id 的 `.S` 齐全（== 12）」与「范围」列的 **8** 个 id 不一致 ⇒ 按 **8** 执行（提示词与 `MIGRATION.md §4` 均记 8），建议修正该行。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-14）

**范围**：8 个 `.S`（166 点）逐行 + 2 个片段 + 证据脚本（`fp_ref.py`/`gen_cases.py`/`check_indep.py`/`inject_expect.py`/`run.sh`）；重点核「期望值是否独立派生」「`ft`/`fo` 写宽」「编码字位域」「点号口径」。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 模型 A 的 RUP/RDN 按绝对值取整 ⇒ 负数定向档方向反了（`-2.1 RDN` 误算 −2.0） | ✅已修 | `_round_int(..., sign)` 按原值符号交换上下界 | `-2.1 RDN → -3.0`、`-2.1 RUP → -2.0`；复算 166/0 |
| F2 `ft` 的「目的高半预置 HI」误用于 `fo` ⇒ OR 静默改写操作数、overlap 用例失真 | ✅已修 | 新增 `hip()` 仅在 `w=='ft'` 时 OR（4 处） | `fornd` 点 23 `-3.5→-4.0`、`fosclb` 点 22 `1.5×2^2=6.0`；复算 166/0；三方 22/22 |
| F3 局部宏体调用 `__CHECK_RD` 被驱动器链例正则误计（多出点号 `-1`） | ✅已修 | `__FP_CHK64` 内联判据（`__LI`+`__REC`+`br.eq`+`__EXIT`） | `--scan-only` 8 文件点号 1..N 连续 |
| F4 `copySignNeg` 的 3 条 semantic 注释写死 `-1.5/+1.5`，与 negate 语义相反 | ✅已修 | 注释按 `negate` 分支现算 | `fosgnn` 点 3/4/5 注释与期望一致 |
| F5 `fosclb` 的「最小次正规×2^1」注释沿用 ft 的 `2^-148` | ✅已修 | 注释按 `emin-fbits+1` 现算 ⇒ `2^-1073` | 生成物注释与值一致 |
| F6 故障编码是否真能到 ILLI（`dst_rf0` / `immu6` 非 one-hot） | ❌不修 | —（非缺陷） | 14 个故障镜像三方均 `0xF8` |
| F7 编码字是否与 `opcodes.yaml` 一致 | ❌不修 | —（非缺陷） | 模型 B 反解位域 + mask/value 全通过 |

**判决**：全部 finding 已处置 ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-14，独立重跑）

**重跑（命令 → 真实输出/退出码）**
1. 主控 worktree `./<运行期证据目录>` ⇒ `summary: FAIL=3 / RESULT: FAIL / RC=1`；FAIL 全在 A5（`FileNotFoundError … .fragments/07-floating-point.inst.yaml`），A1/A2/A3/A4/A6 全 PASS（8 id、166 点、复算不符 0、273 md5 `2d4d9465…`）。
2. 节点 server208 独立同步树（rsync 交付树、自建 `.work`、`--tree` 指定、默认 jobs、独占 work-dir）`run.sh --tree … --full` ⇒ `EXIT=1, FAIL=3`（同 A5）；**B1 三平台 22/22**（链例字节=8×检查点、故障例三方 `0xF8`）、B0 md5 qemu `5d04d3e8…`/gem5 `0542906b…`/chipyard `45748f3f…`、B2 注入 `12/12/12`、`10/10/10`+回绿、B3 cp+md5 还原、A6 273 md5 均 PASS。
3. 同树 07 册全量 ⇒ `170/170（52 id；链例52/故障例118）EXIT=0`。
4. `make check-tests-index RC=0（385）`、`make check-case-ledger RC=0（2184）`、`make validate-vectors RC=0（156/156，gaps 0）`。
5. `make check-inst` ⇒ `RC=2`：`FAIL divrem.yaml[23]`（`1141 total, 1135 passed, 1 failed, 5 deferred, 0 errors`）；重跑 #1 同错；**基线树 `git archive f1215710` 同错同计数** ⇒ 既有红、非本任务引入。

**独立核验（自写模型，不采信 engineer 脚本）**
- 复算 8 文件链例 **152/152 不符 0**（六档+动态 NX、±指数 scaleb、OF/UF/NX、±0/NaN/次正规、ft bit31/fo bit63、高半 `0xDEADBEEF`）；编码 16 条 ENC + 14 条故障字对 `contracts/opcodes.yaml` mask/value/字段 + `dst_rf0`/`immu6` one-hot ⇒ 不符 0。
- 独立注入 1 路：`fosclb` 点22 期望 `0x4018000000000000`→`0x4018800000000000` ⇒ 三平台全 `rc=22`、批 rc=1；`cp` 备份还原 md5 `352881f3…` 相等 ⇒ 回绿 `1/1`（176 B×3、rc 0/0/0）。
- **假绿修复独立确认**（llvm-objdump）：`fosclb` 点3/点22 源操作数 `0x3FF0000000000000`/`0x3FF8000000000000`（无 `0xDEADBEEF` OR）；`ftrnd` 点1/点23 目的预置 `0xDEADBEEFCAFEF00D`、源纯低 32；`ftsgnj` 点15 目的=符号源预置一致。

**约束核验**：id==8 与 §范围逐条对应；点号 1..N 连续（28/23/16/16×2…=166）且 ≤127；ft 只写低 32、fo 整 64、sgnj 取 bit31/bit63、rnd 六档 one-hot、sclb 第三操作数为 rd 有符号指数 —— 与 `spec/SimRISC-07 §2.1/§2.3/§3` 一致并被复算覆盖；片段 `m13-testcases-023.{inst.yaml,migration.md}` 8 条 `045..052` 唯一、`file` 存在、与根清单 44 条无冲突；**未改**根清单/`MIGRATION.md`/`macros/inst_test.inc`/`run_asm_suite.py`（驱动器 `^\t…TEST_FP\w*` + `pts … else -1` 已核，本册无 `__CHECK_RD` 调用）；提交 11 文件与完成区对账一致，`git status -uall` 前后快照均空；完成区 21 行 ≤30、无宿主绝对路径。**采信未独立重跑**：engineer 的 `check_indep.py` 166 例计数（以自写 152 例复算替代）。日志留存 `/tmp/opencode/m13-testcases-023/`。

**判决：Needs Revision**（仅 1 项返工）
1. **F1 阻断**：`run.sh` A5 写死 `07-floating-point.{inst.yaml,migration.md}`，交付树实际为 `m13-testcases-023.*`，且 master `3d6ca5f3` 已把协议改为 `<任务号>.inst.yaml` ⇒ 一键证据脚本在交付树上 `exit=1`。改法：A5 两处路径改 `m13-testcases-023.inst.yaml`/`.migration.md`（或按 `*.inst.yaml` 通配），改后 `run.sh` 须 `RESULT: PASS`；完成区第66行文件名同步。
2. **F2 待主会话裁定（不列入本任务返工）**：验收4 `make check-inst rc=0` 因 `divrem.yaml[23]` 既有红不成立（基线同红）⇒ 另行归属/派修。
3. **F3 文档级 finding**：完成区第66行片段名与实际不符（随 F1 一并改）；第80行「验收1 ==12」已由主会话改为 8，现文一致。

### 第 2 轮 reviewer 复核（2026-11-14）

**返工面核对**：仅 `<运行期证据目录>`（A5 两处路径）+ 本任务书完成区第66行；8 个 `.S` 与 2 个片段 md5 与第 1 轮逐条相同（片段 `9a631e7e…`/`f33b0347…`）⇒ 未越界改交付物；`git status -uall` 仅 `M` 本任务书（第1轮记录 + 完成区行）。

**重跑（真实 rc/计数）**
1. 主控 worktree `./<运行期证据目录>` ⇒ **`RC=0`、`summary: FAIL=0`、`RESULT: PASS`、`[PASS]=18 / [FAIL]=0`**（A1 2 + A2 5 + A3 3 + A4 3 + A5 4 + A6 1）；A2 `152 链+14 故障=166`、`22 镜像`，A3 `166 例/不符 0`，A6 `273 md5=2d4d94651346ef673c5a855e024c1489`。
2. 节点 rsync 交付树（自建 `.work`、`--tree` 指定、默认 jobs、独占 work-dir）`run.sh --tree … --full` ⇒ **`EXIT=0`、`[PASS]=35 / [FAIL]=0`、`RESULT: PASS`**；B0 md5 qemu `5d04d3e8…`/gem5 `0542906b…`/chipyard `45748f3f…`、B1 **22/22**（链例字节=8×检查点、故障例三方 `0xF8`）、B2 注入 `12/12/12`、`10/10/10` + 回绿、B3 `cp`+md5 还原、A6 273 md5 全 PASS。
3. **A5 四项全绿**：`片段 YAML 解析 0/0`（`片段条目数=8 / id=…045…052`）、`片段声明条目数 8/8`、`migration 片段存在 yes/yes`、`根清单 44 条 07 条目 44/44`。

**返工面 2/3 项核验**：A5 写死 `tests/inst/.fragments/m13-testcases-023.inst.yaml`（run.sh:110）与 `…m13-testcases-023.migration.md`（run.sh:132），**无 `*.inst.yaml` 通配/兜底**（grep 仅此两处命中）；本地与节点 run.sh md5 同为 `0988e6027c6c13b7fe8e37abbfe9b399`。完成区第66行写 `m13-testcases-023.inst.yaml` + `m13-testcases-023.migration.md` ⇒ 与树内 `ls`（仅此两件）一致。

**F2 处置**：`make check-inst` 的 `divrem.yaml[23]` 红经基线树（`f1215710`）同红确认为既有问题，主会话已归 `m13-testcases-032` ⇒ **不判本任务**，仅记录。

**判决：Accepted** —— 验收 1–7 在我自己的重跑下全部通过（第 1 轮的自写 152 例复算、30 条编码核验、独立注入与反汇编结论对本轮仍成立，因 `.S`/片段字节未变）；日志留存 `/tmp/opencode/m13-testcases-023/{round2-runA.log,node-logs/round2-full.log}`。
