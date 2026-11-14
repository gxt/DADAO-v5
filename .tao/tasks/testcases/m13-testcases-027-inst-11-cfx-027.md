# m13-testcases-027: `11-cfx` —— `cfx2rc`/`cfx2rd`/`escape`/`fence`/`trap`

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（宏层 `inst_test.inc` + `run_asm_suite.py` 已建好）；与其它 `tests/inst` 重构任务**串行**（共享 `tests/inst/`）
**可并行分片**：否
**状态**：已验证

## 背景

延续 `012`/`013` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。分类与用例模板见 `tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移台账）。

本任务覆盖 **5 个 id**（`11-cfx`（cfx2rc/cfx2rd/escape/fence/trap））

## 范围（id 清单，以 `contracts/opcodes.yaml` 为准）

```
cfx2rc_crrr_cfx cfx2rd_crrr_cfx escape_ciii_cfx fence_ciii_cfx trap_ciii_cfx
```

## 用例设计（5 类，模板见 `MIGRATION.md §3`）

- **encoding**：该 id 的编码校验（mask/value）
- **legality**：适用的合法性规则（`rd0/rb0`、`immu6=0`、范围/重叠、保留编码…），以 `contracts/legality_rules.yaml` 为准
- **semantic**：正常路径，宽度 × 符号 × 形式
- **boundary**：该族特有边界（进位/借位/最值/次正规/对齐/窗口/掩码…）
- **overlap**：源=目、部分重叠、块复制重叠

## 验收

1. `ls tests/inst/11-cfx/` 下本任务 id 的 `.S` 齐全（== §范围 id 数，现场派生：5）
2. 每文件检查点 ≤127、点号连续；失败点号 = 用例序号
3. **三方逐字节**（chipyard == QEMU == gem5 同镜像），含全部故障例
4. `make check-inst` 红集 == 基线红集（现为 `{divrem.yaml[23]}`）；`check-tests-index` rc=0；273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变
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

### 第 1 轮 engineer 自审（2026-11-14，重派接手）

**背景**：上一子代理异常结束，留下 5 个未提交 `.S`（任务书仍 `待开始`）。本轮逐行审 + 重写不合格处 + 补片段。

**审查范围**：`tests/inst/11-cfx/*.S`（5 个）、`.fragments/m13-testcases-027.{inst.yaml,migration.md}`；对照
`spec/SimRISC-11`、`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、
`spec/DADAO-12 §1/§3.6/§3.8`、`spec/DADAO-13 §1/§2`、`spec/Machine-v5 §1.1/§2/§4.2/§5.1`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `fence` 未覆盖 `atomics/atomics-fence.yaml` 的 cfx63+`0x082` 与混合 `0x462` | ✅已修 | 新增链例 13/14；故障例重编号 15..21 | 扫描 14+7；fence 21 镜像三方 PASS |
| F2 `escape` 未覆盖 `base/misc.yaml` 的 cfx63 SBZ 用例（且该例能区分 SBZ 先于 CFXESC） | ✅已修 | 新增故障例 19/20（`0x7EFC0002/0003` ⇒ ILLI） | escape 20 镜像三方 PASS |
| F3 `fence`/`escape` 头注释的 QEMU GAP 是「推断」，无实测 | ✅已修 | 探针实测后改写两条 GAP（写明两个方向的实测结论） | 探针：cfx16/17/18 QEMU 落回 `__EXIT pt`、cfx32/33/34 QEMU 无输出 ⇒ 与 spec 不符 |
| F4 `cfx2rd` 点 20（目的 `rd0`）被我的独立复算判为不符 | ❌不修（`.S` 正确） | 改复算脚本：`rd0` 恒 0（`spec/SimRISC-00 §2`） | 复算 109 点 / 137 断言 / 不符 0 |
| F5 `trap` 头注释把 GAP ② 写成「`trap cfx_power` 必重启、不可观测」，未实测 | ✅已修 | 实测后改写 GAP（QEMU/gem5 进 power 向量、chipyard 报 ILLI） | `probe_gap.py` 矩阵：chipyard `0xF8` / QEMU·gem5 `7` |
| F6 分片片段缺失（`tests/inst/.fragments/` 不存在） | ✅已修 | 按 `MIGRATION.md §5.3` 用任务号命名两个片段 | `merge_fragments --check` rc=0；新增 5 条、清单 232 |
| F7 链例镜像里「意外异常」未预置期望槽 ⇒ `__pad` 静默 `exit 0` | ❌不修（共享宏层，本任务不得改） | 证据脚本用「输出字节数 = 8×检查点数」兜住 | `--scan-only` 与三方运行的字节数断言均生效 |
| F8 `trap`/`escape` 用 `.org` 钉住落点、常量与落点靠人工对齐 | ✅已修（加断言） | 复算脚本新增「目标常量 ↔ `.org` 一一对应」与「`cause_info` == 该用例 trap 编码」 | 注入 I3 把 `.org 0x980`→`0x990` ⇒ 结构断言 FAIL |

**判决**：8 条 finding 全部处置（6 修 / 2 不修附证据）⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-14；三平台在节点 `ics180`，长输出 `.work/log/testcases/m13-testcases-027-review/`）

**重跑（全部本机/节点自跑，不采信完成区转述；HEAD `55512d72`）**
- 本地：`--scan-only` rc=0（5 载体；点号 `1..24/29/20/21/15` 连续、最大 29）；`indep_check.py` rc=0（**109 点 / 137 断言 / 不符 0**，保留 cfx 现场解析 `6–14,16–31,35–61`）；`merge_fragments --check` rc=0（新增 5、清单 232）；`check-tests-index` rc=0（427）；`check-case-ledger` rc=0（2184）；`validate-vectors` rc=0（156/156、gaps 0）；`inst_sweep emit` rc=0、md5 `2d4d9465…` 与 273 例基线相同。
- `make check-inst` rc=2、红集 `divrem.yaml[23]`（1141/1135/1/5）＝**基线既有**：11-13 17:14/20:04 历史日志同红同数，本分支 8 个改动文件不含 `tests/inst/fp/` ⇒ 非本任务引入（验收 4 字面 `rc=0` 见 finding②）。
- **节点三平台**（独立 clone + `.work`/`.dadao` 软链；`--jobs` 默认 = 20；独占，loadavg 0.13→8.14）：`bash .work/evidence/m13-testcases-027/run.sh` ⇒ **rc=0、失败项 0**；C4 `40/40 镜像通过（链例 5 + 故障例 35）`，逐行核 **三平台 rc 分歧 = 0**，故障码 `0xF8×26 / 0xF2×9`。节点 md5 qemu `5d04d3e8…`、chipyard `45748f3f…`、llvm-mc `c111b5b5…`、bootrom `51430087…` 与主控机**逐个相同**；gem5 节点 `bc1b1b5f…` ≠ 主控机 `1c521d07…`（与完成区声明一致）。首跑 rc=1 系**我**漏建 `.dadao` 软链（C4/C6/C9 环境失败，staging 缺口、非交付物缺陷），补链后全绿。
- **独立注入（自设计，不复用 engineer 三路）**：`fence` 故障例 21 编码 `0x79F40000`(cfx61 保留) → `0x79F80000`(cfx62 已分配)、期望仍 ILLI ⇒ `indep_check` rc=1（`spec 判定 期望 'ILLI' 实际 None`）、三方 `suite_rc=1`（`[FAIL] fence … 期望 0xF8 / rc {chipyard:21, qemu:21, gem5:21}`）⇒ `cp` 还原，md5 `aa3cedc8…` 前后相同 ⇒ 两路回绿（rc=0 / 8/8）。另证 C5 FAIL 路径：片段 `file` 改 `NOPE.S` ⇒ `merge_fragments --check` rc=1，还原回 rc=0。
- **GAP 4 项钉住（我自跑 `probe_gap.py` rc=0、7 条全 PASS、`不符 0 条`）**：① `fence cfx16/17/18` chipyard/gem5 `0xF8`、QEMU 放行(rc=1/2/3)；`cfx15/62/63/32/33/34` 链例 chipyard/gem5 48 B、QEMU 0 B；② `cg4` 读 chipyard `0xF2`、QEMU/gem5 rc=1，写三方 `0xF2`；③ `trap cfx_power` chipyard `0xF8`、QEMU/gem5 rc=7（确进 power 向量落点）；④ 屏障排序 Tiny 不可观测（`fence_S:14-15`，链例只覆盖编码/合法性/无副作用、逐例预置 rd5）。①②③ 有探针实测输出，④ 属不可观测并写明理由。
- **ISS-432/433 核**：433 与探针逐值一致 ✓；432 实测方向与数值 ✓，但归因「`spec/SimRISC-11` 定义保留集」不准（SimRISC-11 交 SEE 分配，`Machine-v5 §1.2` 以 `DADAO-12 §1` 编号表为唯一真源＝我现场解析值），且 `19–61` 正是 `DADAO-12` 0.7.3-rc 变更记录 / `Machine-v5` 附录 0.4.0 残留（已登记 §9#10、discussing #10）＝QEMU 疑似根因；探针只采样 16/17/18 与 32/33/34，下界 19 属推断。
- **规范核对**：fence `hb=immu18[17:12]` SBZ⇒ILLI、保留集⇒ILLI（`SimRISC-11 §5`）；escape `{0,+4}`+`imms18[17:1]` SBZ⇒ILLI（`SimRISC-11 §3`）；trap `immu18[17:8]==0x3FF` 短路 / 未实现 cfx⇒ILLI / 其余进该 cfx 向量（`Machine-v5 §3/§4.1/§5.1`）；`cfx2rd/rc` reserved⇒ILLI、未实现或未定义/只写⇒CFXREG（`Machine-v5 §3`）——与 `.S` 内联期望、三平台实测逐条相符。
- **约束核验**：改动 = 8 个文件（5 `.S` + 2 片段 + 任务书），越界 **0**；根清单/宏层/驱动器未动；完成区 18 行、任务书与 `.S` 无运行期路径；worktree `git status -uall` 空且 8 个目标 md5 与开审快照逐一相同；主工作树未触碰；节点 clone/证据/bundle 已删，节点主仓库仍 `abd21e7fe` 干净。
**Finding（非阻断，交 architect 收尾一并改）**：① 验收 1「（== §范围 id 数，现场派生：5）」是 `MIGRATION §1` 的**初估**（该列自注「初估，待校准」），与 §范围「5 个 id、以 `opcodes.yaml` 为准」冲突；现场 `opcodes.yaml` 中 `_cfx` 恰 5 条、目录 5 个 ⇒ 交付正确，建议改「== §范围 id 数（现场派生）」（025/026 已是该写法）。② 验收 4 `check-inst rc=0` 与基线既有红不符，建议改「红集 == 基线红集」。③ ISS-432 归因与根因线索、下界推断（上）。④ `cfx2rd/cfx2rc` 头注释称 chipyard 未实现 `cg0–cg2/cg5 rc5/cg6/cg8 rc1`，仅 `cg4` 有探针（其余未入用例、不影响判绿）。
**判决：Accepted** —— 验收命令块在我自跑下全部通过（含节点三平台 40/40、GAP 探针 7 条、独立注入注入→FAIL→还原→回绿），硬约束无违反；上述 4 条为文档/登记级，按「文档级小错」记 finding 不返工。

## 完成区

**测试结果**：三平台逐字节 **40/40 镜像通过**（链例 5 + 故障例 35，同一 ELF；chipyard/QEMU/gem5 各 40）；独立复算 **109 点 / 137 断言 / 不符 0**；注入 3 路全部「注入→FAIL→还原（`cp`+md5 对账）→回绿」。
**修改文件**：新增 7 个（`git status -uall` 现场一致；除本任务书外无 tracked 改动）：`tests/inst/11-cfx/{cfx2rc_crrr_cfx,cfx2rd_crrr_cfx,escape_ciii_cfx,fence_ciii_cfx,trap_ciii_cfx}.S`、`tests/inst/.fragments/m13-testcases-027.{inst.yaml,migration.md}`。
**验收结果**：
1. 载体 5/5（现场 `ls`）；点号 1..N 连续、最大 29（≤127）；三平台逐字节一致（含 35 个故障例，退出码 = `0xF0|异常位索引`）。
2. 节点复跑：评测节点同 **40/40**（qemu md5 `5d04d3e8…`、chipyard `45748f3f…` 与主控机一致；gem5 按任务要求取节点侧 `bc1b1b5f…`，主控机为重建后的 `1c521d07…`，两侧结果相同）。
3. 独立复算（自写，不从实现反推）：保留 cfx 集/编码字/故障分类/寄存器复位值/点号/`.org` 结构/trap `cause_info` 全从 `spec/`+`contracts/` 派生 ⇒ **不符 0**。
4. 注入：① `cfx2rd` 点 5 期望 `3`→`4` ⇒ 复算 FAIL + 三方链例 rc=5；② `escape` 点 17 `ILLI`→`CFXREG` ⇒ 复算 FAIL + 三方 rc=17；③ `escape` `.org 0x980`→`0x990` ⇒ 结构断言 FAIL。三次均 `cp` 还原、md5 前后相同、复算回绿。
5. 片段：`merge_fragments --check` rc=0（新增 5 条、清单 232）；id `inst-11-cfx-001..005`、`file` 存在。
6. GAP 钉住：`probe_gap.py` 复现三方差异矩阵（`fence` 保留集、`cg4`、`trap cfx_power`），7 条断言全绿；矩阵变红 = 平台已修，需删 GAP 并改用例。
7. 门控：`check-tests-index` rc=0（427 条）、`check-case-ledger` rc=0（2184）、`validate-vectors` rc=0（156/156、gaps 0）、`inst_sweep emit` covered=273 md5 `2d4d94651346ef673c5a855e024c1489` 不变；`check-inst` 红集与基线**完全相同**（`divrem.yaml[23]`，1141/1135/1/5，rc=2 属既有 pin；其输入是 YAML，本任务产物不在其中）。
**新发现/坑**：
- QEMU 的 fence reserved 集 = `6–14, 19–61`（spec = `6–14, 16–31, 35–61`）：实测 `fence cfx16/17/18` QEMU 放行、`fence cfx32/33/34` QEMU 报异常（chipyard/gem5 与 spec 一致）⇒ 用例只用三方一致编号。
- chipyard RTL 无 `cg4`（cfx id/version/trap_num 簇）：`cfx2rd cfx_hmon, cg4, rc2` 在 chipyard 报 CFXREG、QEMU/gem5 读成功 ⇒ `trap_num`/`escape_num` 计数不可测。
- `trap cfx_power` 与 spec 的偏离是**平台级**：QEMU/gem5 按 `DADAO-12 §5.2` 进 power 向量，chipyard 报 ILLI；不改向量时该向量 = BootROM 复位入口（表现为重启），故该维度不可跨平台测。
- `cg7` 的 `attr` 在 spec 属 HW 定义（无规范值）：用例钉的是三方一致值（hmon SRAM `R|W|X`、BootROM `R|X`）。
- 链例镜像的「意外异常」经 `TEST_PAD` 走 `__pad`，未预置期望槽时**静默 exit 0**；排障看输出字节数，不能只看 rc。
**遗留问题**：无未完成项。（另：`check-knowledge-refs` 在基线上即红，5 条均为**其它**任务书的运行期路径引用，本任务书无此类引用。）GAP 4 项已钉住：① QEMU fence reserved 集；② chipyard 无 `cg4`；③ `trap cfx_power`（cfx63、`immu18 < 0x3FF00`）：spec 判进 power 向量，QEMU/gem5 实测进入、chipyard 报 ILLI（三方不一致，不构造该维度用例）；④ 屏障排序/可见性在 Tiny 不可观测（`fence` 只覆盖编码/合法性/无副作用）。YAML 载体（`base/misc.yaml`、`atomics/atomics-fence.yaml`）同 id 用例已并入 `.S`，两文件删除按 §5.1 前置与 `m13-testcases-030` 同批。
