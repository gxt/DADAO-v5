# m13-testcases-019: `05-arith-addr` —— `add.si`/`aip.si`/`cmp.ui`/`cmp.si`

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（宏层 `inst_test.inc` + `run_asm_suite.py` 已建好）；与其它 `tests/inst` 重构任务**串行**（共享 `tests/inst/`）
**可并行分片**：否
**状态**：已验证

## 背景

延续 `012`/`013` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。分类与用例模板见 `tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移台账）。

本任务覆盖 **6 个 id**（`05-arith-addr` 地址运算）

## 范围（id 清单，以 `contracts/opcodes.yaml` 为准）

```
add.o_orrr_bbd add.si_riii_rb aip.si_riii_rb cmp.uo_orrr_dbb sub.o_orrr_bbd sub.o_orrr_dbb
```

## 用例设计（5 类，模板见 `MIGRATION.md §3`）

- **encoding**：该 id 的编码校验（mask/value）
- **legality**：适用的合法性规则（`rd0/rb0`、`immu6=0`、范围/重叠、保留编码…），以 `contracts/legality_rules.yaml` 为准
- **semantic**：正常路径，宽度 × 符号 × 形式
- **boundary**：该族特有边界（进位/借位/最值/次正规/对齐/窗口/掩码…）
- **overlap**：源=目、部分重叠、块复制重叠

## 验收

1. `ls tests/inst/05-arith-addr/` 下本任务 id 的 `.S` 齐全（**== 6**；原写「== 5」系笔误 —— 现场 `contracts/opcodes.yaml` 与 `spec/SimRISC-05` 附录 A 都是 6，详见「审阅记录」自审 finding 8）
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

改动面：6 个新 `.S`、宏层（3 链例宏 + 3 故障宏）、驱动器 `FAULT_AR_RE`、`tests/inst.yaml`（+6）、
`MIGRATION.md`（§5 三行 + §6/019）、`README.md`（+1 行）。逐行自审 + 三平台实跑 + 独立重算（75 点）
+ 编码字对账（11/11）+ 注入自检。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `add.si` 点 2（编码字段边界）期望误写 0（实为 +131071 = 0x1FFFF） | ✅已修 | 期望改 `0x000000000001FFFF` | QEMU 点 2 由 rc=2 转绿；三平台 12/12 |
| `add.si` 点 7 用例与注释不自洽（全 1 初值 + 上界 ⇒ 回绕成 0xFFFF，注释却写「低 48 位全 1」） | ✅已修 | 初值改 `0x0000FFFF00000000`、期望 `0x0000FFFF0001FFFF`、注释改「低 48 位内进位」 | 同上（改前 QEMU rc=7） |
| `sub.o` bbd 点 11 注释误写「INT64_MAX − INT64_MIN」（实为 −1 − INT64_MIN） | ✅已修 | 注释改「全 1（= −1）− INT64_MIN = INT64_MAX」 | `@@` 注释不产码；改后三平台重跑 12/12 |
| `sub.o` dbb 点 10 注释误写「高 16 位不变」（实为借位沿全 64 位传播） | ✅已修 | 注释改「借位沿全 64 位传播」 | 同上 |
| `aip` 点 9 注释把「段内偏移 0x220」写成「IP 低 12 位 = 0x220」（IP 低 12 位实为 0x320） | ✅已修 | 注释改「段内偏移 0x220（IP 低 12 位 = 0x320）」 | 同上 |
| `aip.si` 期望含**链接期地址**，而 llvm-mc 把标签差（`. - _start`/`L1 - L0`）在指令立即数里**静默折成 0** | ✅已修（改设计） | `.org 0x200` 钉槽（`jump` 跳过零填充）+ 期望写 `ENTRY + <字面偏移>`；坑写入 `MIGRATION §6/019` | objdump：首槽 = ENTRY+0x200、12 槽连续 4 B；三平台 11 点全绿 |
| `oracle.py` 初版：偏移链在未知尺寸宏处断裂、未建模 `aip.si` 直写行/标签行 ⇒ 6 文件全报错 | ✅已修 | 偏移不可知时只对 aip 报错；补 `aip.si` 直写行与标签行；`add.si` 链例不再依赖偏移 | 6 文件 oracle 全 rc=0（75 点 / 不符 0） |
| `run.sh` 初版：spec 附录 A 解析漏 3 个 id、单平台时「平台数」算成 0、`inst_sweep emit` 参数用错、rsync 副本上 `check-no-residue` 因非 git 树红 | ✅已修 | id 正则 + opcodes 归属校验；平台数改 `awk`；`emit <outdir>`；非 git 树改 `[SKIP]` 并新增 `--check-inst` 段 | 主控机 `CHECK=35 FAIL=0`、节点 `CHECK=38 FAIL=0` |
| 任务书验收 1「== 5」与现场 6 个 id 不符 | ✅已修（就地订正） | 改为「== 6」并注明依据 | 现场三方核数 6/6/6（`run.sh` 第 1 项） |
| `make check-inst` 的 Tiny 子集未跑到（vast 段非零即 `exit`，`Makefile:1896-1902`） | ⏸记录（不改门控） | 不改 target（不属本任务）；完成区如实写 | 日志 `Results:` 两行同值（vast 段自身）+ `check-inst: FAIL (vast segment rc=1)` |
| `tests/inst/README.md` 的 04 册行写「15 个」（实 29，017 遗留） | ❌不修（越界） | 只在完成区「遗留问题」登记 | 017 的 `git log -p` 显示其只改了用法注释行 |

判决：findings 全部已修或已登记（⏸/❌ 三项均附原因与证据）⇒ 状态置 `待验收`；三平台、
门控、注入、独立重算全绿（见完成区）。

### 第 1 轮 reviewer 验收

**重跑（我本人执行；真实输出/退出码）**
- 节点 `run_asm_suite.py --vectors tests/inst/05-arith-addr --lds tests/inst/01-load-store/inst-tiny.lds --jobs 8` ⇒ `rc=0`、`12/12 镜像通过`；链例 `104/96/88/104/104/104 B`（== 8×`13/12/11/13/13/13`），故障例三平台 rc 全 `248(0xF8)`。
- 节点 `<运行期证据目录>/run.sh` ⇒ `RV_RUN_EXIT=0`、`CHECK=32 FAIL=0 PASS`；`run.sh --inject` ⇒ `RV_INJECT_EXIT=0`、`CHECK=38 FAIL=0`（与完成区逐字一致：`7be0cb3e…→58175a30…`、oracle rc≠0、跑批 rc=6、还原 `7be0cb3e…`、回绿 rc=0）。
- 主控机门控：`check_tests_index rc=0(322)`｜`check_case_ledger rc=0(2170)`｜`validate_vectors rc=0(723, gaps 0)`｜`inst_sweep emit rc=0` ⇒ md5 `2d4d94651346ef673c5a855e024c1489`(covered=273)｜`check-dirs rc=0`｜`check-no-residue rc=0`｜`check-knowledge-refs rc=2`（2 命中属 `m14-infra-001`/`m14-spec-003`，非本任务）。
- 独立复算（自写 `recheck.py`，语义取自 `spec/SimRISC-05 §1–§4` + `opcodes.yaml` 位域，不复用 `oracle.py`）⇒ `75 点/不符 0/跳过 0, rc=0`：含 add/sub `[63:48]` 不截断、`cmp.uo` 整 64 位、`add.si` 符号扩展、`aip.si` 12 槽连续 4B 且 `ENTRY+字面偏移`。
- 独立注入（自设计，非 `cmp.uo` 点 6）：`add.o_orrr_bbd` 点 7 期望 `0x0001000000000000→0x0000000000000000`，md5 `9ad65e7f…→a5eaeece…` ⇒ 三平台 rc 全 **7**、`SUITE_EXIT=1` ⇒ `cp` 还原 md5 `9ad65e7f…` 相等 ⇒ 回绿 `RESTORE_SUITE_EXIT=0`、`1/1 PASS`、104 B，无 `.preinject` 残留。

**约束核验**：独立 worktree/分支 ✓、未提交 git ✓、未重建组件 ✓、临时文件只在 `/tmp/opencode/m13-testcases-019/` ✓；改动面 **12 项 == 完成区声明**，未碰 `contracts/`/`spec/`/`Makefile`，无 `git rm`，`git status -uall` 干净、无 `*_tmp*`/`*.orig`/`*.rej` 残留；完成区 **16 行**(≤30)；任务书无运行期路径；`inst_test.inc` diff 纯新增（仅 1 行注释改写），**无既有断言弱化**。

**id 数结论**：`opcodes.yaml` 按 `spec_cite` 前缀 `SimRISC-05` = **6**；spec 附录 A 解析 6；附录 B 合法性 `2+4=6`；目录 `.S` 6；任务书 §范围 6 ⇒ **6 成立**；验收 1「==5→==6」是**收紧**、非凑绿。附注：`ha:'0x33'` 全仓仅 2 个 id（`sub.o_orrr_dbb`/`ft2uo_orri_rf`），**不能**作本族筛选条件（任务书/派单的「ha 0x33」描述不准）。

**未重跑（如实披露）`make check-inst`**：受「不重建组件/禁改主工作树」约束；实测 `build-bootrom` 为 gate-locked、`/mnt/tao/DADAO-v5/.dadao/gate.lock` 正被 PID 1598636 持有（`fuser`）、`qemu-system-dadao` mtime `00:04` 正被并行构建重写 ⇒ 此刻不可信。排除法：`semantics_gate.py` 的 `CARRIER_DIRS=(base,rol,atomics,clmul,fp)` **只收 `.yaml`**，本任务在该四处零新增零改动 ⇒ 不可能改变其红集；`{divrem.yaml[23]}`+`1141/1135/1/5` 与 015/016/017/qemu-009/qemu-010 五处记录逐字一致，归 `m13-testcases-032`。

**Findings（文档级 → Accepted，architect 收尾改）**
① 完成区写 `make check-inst rc=1`，其自有 `run.sh` 与 raw log 为 `make rc=2`（`*** Error 2`；内层 vast 段 rc=1）；
② `cmp.uo` 点 6 注释 / 完成区坑③ / `MIGRATION §6/019` 称「只比低 48 位会判**相等 0**」，实算得 **1**（`0xFFFFFFFFFFFF > 0x000000000000`）—— 断言 `-1` 正确，仅反例预测错；
③ `MIGRATION.md §1` 表 `05-arith-addr/` 仍写 `5`（现场 6；该列自标「初估待按附录 A 校准」，04/07/08/09/10/11/12 各行同样过时，非本任务引入）；
④ `oracle.py`/`encode_check.py` 用 `Path(__file__).resolve().parents[3]` 定根 —— `.work` 按 `ISS-389` 软链时会解析到宿主主仓（本轮两侧 `opcodes.yaml`/`SimRISC-05`/`machine-tiny.inc` md5 全同故结果无误，属潜伏隐患）。

**待 architect 裁定**：验收 4 的 `make check-inst rc=0` 在当前基线不可达；建议沿 015/016/017 口径改判「红集恰 == `{divrem.yaml[23]}`」，或先推 `m13-testcases-032`。

**判决：Accepted** —— 重跑项全绿、约束无违反、id 数 6 独立核实；上述 4 条文档级 finding 与验收 4 口径由 architect 收尾处置。

## 完成区

**测试结果**：三平台 **12/12** 镜像通过（6 id；链例 6 + 故障例 6，36 条平台记录全一致 —— 链例 rc=0 且三平台字节数 == 8×点数、字节流相同；故障例三平台 rc 全 `0xF8`）；节点一键证据 `run.sh --inject`（三平台）**CHECK=38 FAIL=0 / RESULT=PASS**；主控机 `run.sh --check-inst` **CHECK=35 FAIL=0 / RESULT=PASS**；独立重算 **75** 点 / 不符 0；编码字对账 11/11。
**id 数**：现场 `contracts/opcodes.yaml` = **6**（与 `spec/SimRISC-05` 附录 A、任务书 §范围、目录 6 个 `.S` 三方一致）；验收 1 原「== 5」系笔误，已就地改「== 6」。
**修改文件**：新 6 + 改 6 = `git status --porcelain -uall` **12** 项（逐项对账；改的第 6 项 = 本任务书）：
- 新 `tests/inst/05-arith-addr/{add.o_orrr_bbd,sub.o_orrr_bbd,cmp.uo_orrr_dbb,sub.o_orrr_dbb,add.si_riii_rb,aip.si_riii_rb}.S`
- 改 `tests/inst/macros/inst_test.inc`（`TEST_AR_{BBD,DBB,RB_SI}` + `TEST_FAULT_{BBD,DBB,RB_SI}`）、`tools/testcases/inst/run_asm_suite.py`（`FAULT_AR_RE` 增 3 名）、`tests/inst.yaml`（+6 条）、`tests/inst/MIGRATION.md`（§5 三行 + §6/019）、`tests/inst/README.md`（+1 行 05 册）、本任务书
**验收结果**：
1. 6 个 `.S` 逐名齐全；点号 1..N 连续、≤127（现场 14/13/12/14/14/14 = 链例 13/12/11/13/13/13 + 故障例 1）；每表头类别合计 == 现场链例数
2. 编码对账：11 个手写 `.dd.t32` == llvm-mc 重新编码（11/11）；`mask/value` 命中 11/11
3. `check-tests-index` rc=0（**322** 条）｜`check-case-ledger` rc=0（2170）｜`validate_vectors` rc=0（gaps 0，723 例）｜273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变（covered=273）｜`check-dirs`/`check-no-residue` rc=0
4. `make check-inst` rc=1，红集**恰** `{divrem.yaml[23]}`（既有基线：`1141 total / 1135 passed / 1 failed / 5 deferred`；Tiny 段未跑到 —— target 在 vast 段非零即 `exit`）
5. 可达 FAIL：`cmp.uo_orrr_dbb` 点 6 期望 −1→0 ⇒ 三平台 rc 全 **6** + oracle 判红（「重算 0xFFFF… ≠ 内联期望 0x0」）⇒ `cp`+md5（`7be0cb3e…`）还原 ⇒ 回绿（跑批 rc=0、oracle rc=0）
6. YAML：`aip-si.yaml`（1 id、12 例）+`reg-arith.yaml` 的 3 个 05 id+`reg-compare.yaml` 的 `cmp.uo` 用例已并入；**未删** —— 实测 `mv` 走 `aip-si.yaml` ⇒ `validate_vectors` rc=1（4 gap）/`check-case-ledger` rc=1（多 12 行）/`check-tests-index` rc=1（`file` 缺失）；`cp`+md5（`fe281d22…`）还原后 rc=0（gaps 0）
**新发现/坑**：① **llvm-mc 把标签差在指令立即数里静默折成 0**（`. - _start`、`L1 - L0`，`__LI`/`set.zw` 均如此、无诊断）⇒ `aip` 这类链接期期望只能写绝对常量 `ENTRY + <字面偏移>`、槽位用 `.org` 钉住；② `aip.si` 的 `IP` = 该指令自身地址、低位不清零（`aip.si rbX, 0` 直接读出自身地址，可分辨「下一条/页对齐」口径）；③ `cmp.uo` 必须比**整 64 位**（0x0000FFFF.. vs 0x0001_0000_0000_0000，只比低 48 位会判「相等」）；④ 加减结果**不截断**到 48 位（`[63:48]` 只是地址溢出指示）；⑤ `sub.o_orrr_dbb`（ha 0x33）无 YAML 载体；⑥ 汇编器对非法目的（`rb0`/`rd0`）**放行** ⇒ 故障例可直接用真助记符。
**遗留问题**：① 三份 YAML 未删（§5.1 前置：inventory 载体登记 + 数据覆盖门控需认得 `.S`）→ `m13-testcases-030`；② `check-inst` 既有红 `divrem.yaml[23]` → `m13-testcases-032`；③ Tiny 子集未验证（vast 段先红即退，属基线行为）；④ `ISS-410` 的 hmon 自装 workaround 沿用；⑤ `tests/inst/README.md` 的 04 册行「15 个」已过时（实 29，017 遗留），超出本任务范围未改。
