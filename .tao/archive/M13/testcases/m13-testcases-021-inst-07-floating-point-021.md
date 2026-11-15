# m13-testcases-021: `07-floating-point` —— 加/乘/FMA/除/开方/取余

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（宏层 `inst_test.inc` + `run_asm_suite.py` 已建好）；与其它 `tests/inst` 重构任务**串行**（共享 `tests/inst/`）
**可并行分片**：否
**状态**：已验证

## 背景

延续 `012`/`013` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。分类与用例模板见 `tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移台账）。

本任务覆盖 **18 个 id**（`07-floating-point` 算术与最小最大）

## 范围（id 清单，以 `contracts/opcodes.yaml` 为准）

```
foadd_orrr_rf fodiv_orrr_rf fofma_rrrr_rf fomax_orrr_rf fomin_orrr_rf fomul_orrr_rf forem_orrr_rf
foroot_orri_rf fosub_orrr_rf ftadd_orrr_rf ftdiv_orrr_rf ftfma_rrrr_rf ftmax_orrr_rf ftmin_orrr_rf
ftmul_orrr_rf ftrem_orrr_rf ftroot_orri_rf ftsub_orrr_rf
```

## 用例设计（5 类，模板见 `MIGRATION.md §3`）

- **encoding**：该 id 的编码校验（mask/value）
- **legality**：适用的合法性规则（`rd0/rb0`、`immu6=0`、范围/重叠、保留编码…），以 `contracts/legality_rules.yaml` 为准
- **semantic**：正常路径，宽度 × 符号 × 形式
- **boundary**：该族特有边界（进位/借位/最值/次正规/对齐/窗口/掩码…）
- **overlap**：源=目、部分重叠、块复制重叠

## 验收

1. `ls tests/inst/07-floating-point/` 下本任务 id 的 `.S` 齐全（== **18**；判据 = 本任务 §范围 清单 == 目录内容，逐一对应、无缺无多）。**注意**：`contracts/opcodes.yaml` 的 `spec_cite: SimRISC-07` 含 **52** 个 id（07 册分 021/022/023 三件），不能拿 52 当本任务判据。
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

审查面：宏层新块（`__FP_ENV/__FP_CHECK/TEST_FP3/4/PROOT/FPENC*/TEST_FAULT_FP`）、
`__FP_LAYOUT` 条件块、runner 三处正则、18 个 `.S` 的期望与分类、新 lds 的段址。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 共享宏层加 `__FP_LAYOUT` 条件块可能影响 01–06 的链接布局 | ✅已修（改为纯条件分支，未定义时 `.equ` 原值） | `tests/inst/macros/inst_test.inc` | 用 HEAD 版宏层与新版分别汇编 01/03/04/06 各一例，ELF md5 两两相同（4/4） |
| F2 `TEST_FP*` 行不被 runner 的链例/故障例正则识别 ⇒ 点号统计为 0 | ✅已修 | `run_asm_suite.py`：`CHAIN_CASE_RE`/`CHAIN_PT_RE` 加 `TEST_FP\w*`，新增 `FAULT_FP_RE` | `--scan-only`：18 id / 38 镜像，314+20 点、点号 1..N 连续 |
| F3 `foroot` 的 sqrt(最小次正规)=2^-537 为**精确**，原注释写「+NX」 | ✅已修（只改注释，期望 0x00 本就正确） | `foroot_orri_rf.S` 注释 | `check_s`/`check_indep` 复算 0 不符；三方跑批该点绿 |
| F4 独立复算若复用生成常量的同一实现 ⇒ 同源自比 | ✅已修（第二套实现 `check_indep.py`：host FPU/`math.remainder`/`Decimal` + 精确有理数比较 + 编码字 ±1 求邻值） | 证据目录新增 `check_indep.py` | 318 例 0 不符；与 `fpref` 独立得出同一期望 |
| F7 div/rem 缺 qNaN 输入用例；复查发现 `divrem.yaml[23]`（既有红 pin）正是「qNaN rem 2.0 期望 payload 传播」 | ✅已修（按 spec §1.4 canonical 补 4 例：`ftrem`/`forem` 的 qNaN rem 2.0、`ftdiv`/`fodiv` 的 qNaN÷2.0） | 4 个 `.S` | 三平台均按 canonical 通过；YAML 旧口径与该例红 pin 同源，记入「新发现」 |
| F5 节点首轮 chipyard 20 个故障例报「rc=点号（未触发 ILLI）」，同 sim/ELF 后续两轮全绿 | ⏸延后（未复现，记入「新发现/坑」待查） | 未改代码 | 独立 work-dir + pin 二进制复跑两轮：38/38 全绿（含 20 故障例 0xF8） |
| F6 节点 QEMU/gem5 为旧构建，rootn(±0)/NaN 口径与 master 不一致（首轮点 8 红） | ✅已修（改用 master 构建的 qemu/gem5 pin 副本，md5 现场核对） | 证据脚本 `--full` 支持 `QEMU_BIN`/`GEM5_BIN` | 三平台同镜像 38/38 全绿 |

判决：全部可修项已修，无可推进的未修项 ⇒ 状态置 `待验收`。

### 第 2 轮 reviewer 验收

判决：**Accepted**。下列输出全部为 reviewer 亲跑（worktree @ `bb7d3464`，`git status` 空）。

**重跑**：`run.sh` A 段 `rc=0`/FAIL=0（id 18、`.S` 18、链例 318、故障例 20、镜像 38；`check_s` 338/0、`check_indep` 318/0；`check-tests-index` rc=0 **total=359 = 341+18**；`check-case-ledger` rc=0/2170；`validate_vectors` rc=0/gaps 0/723 例；sweep md5 `2d4d94651346ef673c5a855e024c1489` covered=273；`check-generator-sync` rc=0）。
`make check-inst` **rc=2**、`1141 total/1135 passed/1 failed/5 deferred`、红集**恰** `{divrem.yaml[23]}`；**基线树 `c5a3a854` 临时 worktree 复跑逐字一致**（rc=2、同数字、同一红）⇒ 既有红，非本任务引入。
**三平台（server207，reviewer 自跑）**：`SUITE_EXIT=0`、`38/38`；json 现场 `records=38 chain=18 fault=20 not_ok=0 cross_platform_diff=0 fault_rc_set=['0xf8']`。
**本审查所用二进制（现场 md5）**：qemu `1037740c55c4e9f317e11306e3328c3f`（`v11.1.1-1-g0bad885`）、gem5 `b96154304af2e34f0001c5de6989e1d4`；节点主仓对照 qemu `ff06f43471b97cc302ebfe038436a4b3`（`v11.1.1-1-gcd44d5f`）、gem5 `a4c136ba23bcc1cca7f4901ec55dbf71`。节点树 22 关键文件 md5 与 reviewer worktree `diff` 空（`f2c08d18…`）。
**旧二进制复现（F6 成立）**：主仓 qemu 下 `foroot` 链例 `rc=8`、`foadd` 链例 `rc=10`，与首轮日志逐字同 ⇒ 首轮 qemu/gem5 红确为旧构建口径。
**独立复算（第三套：自写 C + 硬件 FPU + `fenv.h`，不复用其两套）**：foadd 舍入 / fomul 溢出次正规 / forem 符号 NaN / foroot 负数 NV —— **69 例全量、不符 0**；反例注入→`不符 1`→还原→`不符 0`（md5 同）。
**独立注入（自设计，非 ftadd/15、forem/9）**：`fomul` 点 13 标志 `0x18→0x00` ⇒ `INJECT_RC=0`、`SUITE_EXIT=1`、`{'chipyard':13,'qemu':13,'gem5':13}`；`cp`+md5 `RESTORE_OK`（`e915f0c6…`）→ 回绿 `BACK_GREEN_EXIT=0`。

**约束逐条**：① id 18/18 与 §范围 清单逐一对应、点号 1..N 连续且 ≤127 ✅；② 三方逐字节（`cross_platform_diff=0`）+ 20 故障例 `0xF8` ✅；③ 门控如上 ✅；④ YAML 未删（`MIGRATION.md` §5/§6 已记，合「全迁才删」）✅；⑤ 注入可达 FAIL ✅；⑥ 完成区 21 行 ≤30、无运行期路径 ✅；⑦ 越界 `19 A + 6 M = 25` 与「修改文件」逐项一致、`git status` 空 ✅；⑧ 未改 `contracts/`/`spec/`/`Makefile` ✅。

**divrem.yaml[23] 根因 —— 同意主会话前置结论**：`spec/SimRISC-07 §1.4`「NaN 结果的取值（全册适用）」明确把**取余（remainder）**列入 canonical 适用清单（不适用者仅复制类 / signaling compare / min-max 单 NaN）；YAML `notes` 自述「payload 传播」、期望 `0x7FF8000000000123` ⇒ **YAML 是旧口径**；三平台实测 canonical（`.S` forem 点 10 同输入绿）⇒ 实现正确，该 YAML 归 `m13-testcases-032` 退役，**不得修实现凑绿**。

**节点首轮 20 故障例 rc=点号 —— 并发环境假红，非本任务真问题，且不满足 `ISS-429` 触发条件**：① 首轮 05:49 `running` 含并发的 `01-load-store` suite + 默认共享 work-dir；② reviewer 用**同参**（默认 `harness/inst-asm` + `jobs=8`）但节点空闲复跑 ⇒ `SHARED_EXIT=0`、38/38；③ 独立 work-dir 三轮全绿（工程师 2 + reviewer 1）；④ `ISS-429` 判据（sim 与 bootrom 失配）在首轮与复跑之间**未变**（sim `02:38`、bootrom `03:42`）⇒ 若属固件失效应稳定复现。同现象另有已知根因 `ISS-429`，建议保留为排查项，不据此返工。

**findings（文档级，不阻断）**：F1 转述「`spec_cite: SimRISC-07` 含 44 个 FP id」，现场实为 **52**（§范围 18 与目录一致，验收 1 判据不受影响）；F2 验收 1 措辞「按 SimRISC-07 加 §范围 清单核数」有歧义（52≠18），建议改写为「§范围 清单 == 目录」。

## 完成区

**测试结果**：通过 38/38 镜像（现场：18 链例 + 20 故障例）；链例检查点 318、故障例 20，点号逐文件 1..N 连续且 ≤127。
**修改文件**：
- 新增 `tests/inst/07-floating-point/{foadd_orrr_rf,fodiv_orrr_rf,fofma_rrrr_rf,fomax_orrr_rf,fomin_orrr_rf,fomul_orrr_rf,forem_orrr_rf,foroot_orri_rf,fosub_orrr_rf,ftadd_orrr_rf,ftdiv_orrr_rf,ftfma_rrrr_rf,ftmax_orrr_rf,ftmin_orrr_rf,ftmul_orrr_rf,ftrem_orrr_rf,ftroot_orri_rf,ftsub_orrr_rf}.S`（18）＋`inst-tiny-fp.lds`；
- 改 `tests/inst/macros/inst_test.inc`（FP 宏 + `__FP_LAYOUT`）、`tools/testcases/inst/run_asm_suite.py`（正则）、`tests/inst.yaml`（18 条 index）、`tests/inst/MIGRATION.md`（§5 行 + §6/021）、`tests/inst/README.md`（表 + 跑法）。
**验收结果**：
- 三方逐字节（同一份 ELF）：chipyard == QEMU == gem5，38/38 全绿（18 链例字节流逐字节一致；20 故障例同为 `0xF8`）。
- 独立复算：`check_s` 338 例 / 不符 0；`check_indep` 318 例 / 不符 0（两套自写实现）。
- 门控：`check-tests-index` rc=0；`check-case-ledger` rc=0（2170 条）；`validate_vectors` rc=0（gaps 0，723 例/156 id）；273 例 sweep md5 `2d4d94651346ef673c5a855e024c1489`（covered=273）；`check-generator-sync` rc=0；`check-inst` rc=2 且红集**恰** `{divrem.yaml[23]}`（1141 total/1135 passed/1 failed/5 deferred）。
- 注入 2 路：`ftadd` 点 15（结果）、`forem` 点 9（标志）⇒ 三平台同点号非零退出（15/15/15、9/9/9）；`cp`+md5 还原后回绿（md5 对账一致）。
- 标志覆盖（现场统计）：`0x00` 219、`NV` 42、`DZ` 4、`NX` 29、`OF|NX` 18、`UF|NX` 6；舍入档 RNE 228 / RTZ 10 / RDN 40 / RUP 4；分类 encoding 36 / semantic 72 / boundary 174 / overlap 36 / legality 20。
**新发现/坑**：
1. 节点 QEMU/gem5 曾为**旧构建**（与 master 构建 md5 不同）：`rootn(±0)` 返回 −0、部分 NaN/标志口径不同 ⇒ 三方差分前必须 pin/刷新平台二进制并现场核 md5（平台二进制属评测前置，不是测试对象）。
2. 首轮（默认共享产物目录 + 节点同时跑另一批 suite、jobs=8）chipyard 20 个故障例读回「rc=点号」；随后同 sim/ELF 两轮（独立 work-dir）全绿 ⇒ 未复现，疑共享产物目录/并发干扰，**根因未定**（登记 issue 候选）。
3. **既有红 pin `divrem.yaml[23]` 的根因已定位**：它是「`forem` qNaN rem 2.0 期望 payload 传播」，而 spec §1.4 规定 qNaN 结果一律 canonical（m13-spec-007 定稿）⇒ 实现（三平台）按 canonical 是对的、YAML 是旧口径；该 YAML 退役时随载体删除即可，不应「修实现」凑绿。
4. `spec/SimRISC-07 §2.1` 的 `forem/ftrem` 表注「精确余数 rfHC − n×rfHD（符号随 rfHC）」对**非零**结果不成立（`5.5 rem 2 = −0.5`），按同节「IEEE 754 remainder」表述与规范第 6 条以 IEEE 为准；建议 spec 措辞任务收窄为「零余数取被除数符号」。
5. 宏层新增的 `__FP_LAYOUT` 条件布局是从 01 册 0x1E00 `.text` 上限解耦的可复用写法（浮点册 `.text` 最大 0x14CC，上限 0x4000）。
**遗留问题**：
1. 任务书「范围」列 18 个 id、验收 1 却写「== 14」——按 18 执行（范围清单与 contract 一致），请主会话确认以 18 为准并修正该行。
2. 任务书「说明」第 1 条要求沿用 hmon **自装** workaround，但 `m12-chipyard-028` 已合入固件 hmon、`ISS-410` 已修（子代理提示亦明确撤销）⇒ 本任务按**固件 hmon** 实现（返回槽 `+0xF8`、cause_id `+0xE0`），无自装桩。
3. `fp/divrem.yaml` 的 6 个 id 全部有 `.S` 载体，但**未删**：它是 `check-inst` 的 L3 载体且 §5.1 前置未解；`fp/arith.yaml` 仍含 4 个比较 id（待 022）。
4. 「共享产物目录/并发」下的 chipyard 异常（坑 2）需在 `m13-testcases-030` 或 infra 侧查（是否有可复现的并发路径）。

