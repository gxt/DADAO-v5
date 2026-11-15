# m13-testcases-026: `10-arith-logic-byte` —— `.ub`/`.sb` 全族

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（宏层 `inst_test.inc` + `run_asm_suite.py` 已建好）；与其它 `tests/inst` 重构任务**串行**（共享 `tests/inst/`）
**可并行分片**：否
**状态**：已验证

## 背景

延续 `012`/`013` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。分类与用例模板见 `tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移台账）。

本任务覆盖 **21 个 id**（`10-arith-logic-byte`）

## 范围（id 清单，以 `contracts/opcodes.yaml` 为准）

```
add.sb_orrr_rd add.ub_orrr_rd cmp.sb_orrr_rd cmp.ub_orrr_rd div.sb_orrr_rd div.ub_orrr_rd
mul.sb_orrr_rd mul.ub_orrr_rd rem.sb_orrr_rd rem.ub_orrr_rd rev.b_orri_rd rol.b_orri_rd
rol.b_orrr_rd shl.b_orri_rd shl.b_orrr_rd shr.sb_orri_rd shr.sb_orrr_rd shr.ub_orri_rd
shr.ub_orrr_rd sub.sb_orrr_rd sub.ub_orrr_rd
```

## 用例设计（5 类，模板见 `MIGRATION.md §3`）

- **encoding**：该 id 的编码校验（mask/value）
- **legality**：适用的合法性规则（`rd0/rb0`、`immu6=0`、范围/重叠、保留编码…），以 `contracts/legality_rules.yaml` 为准
- **semantic**：正常路径，宽度 × 符号 × 形式
- **boundary**：该族特有边界（进位/借位/最值/次正规/对齐/窗口/掩码…）
- **overlap**：源=目、部分重叠、块复制重叠

## 验收

1. `ls tests/inst/10-arith-logic-byte/` 下本任务 id 的 `.S` 齐全（== **21**；判据 = 任务书 §范围 清单 == 目录内容）
2. 每文件检查点 ≤127、点号连续；失败点号 = 用例序号
3. **三方逐字节**（chipyard == QEMU == gem5 同镜像），含全部故障例
4. `make check-inst` 红集不扩大（当前恰为既有 pin `{divrem.yaml[23]}`，rc=2 属预期）；`check-tests-index` rc=0；273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变
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

- 逐行审查 21 个 `.S` + 2 个片段 + 证据脚本（`check_indep.py`/`run.sh`）；判决：可交付（F1–F7 全部已修）。
- 自动化替代肉眼：头部字段 ↔ `contracts/opcodes.yaml`（A1）、头部分类计数 ↔ 现场行数（A2）、
  324 例规范复算（A3）、三平台字节流 ↔ 复算（B2）、2 路注入（B3）；一键证据脚本（运行期证据目录，未归档）`--full` 全绿。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 编码字边界例 ha 手算进位错：9 处写成相邻 id 的字（6 个 orrr 的 `0x…7F042` + 3 个 orri 的 `0x4363F047`），其中 4 处结果恰好同值 ⇒ 被三平台全绿掩盖，另 5 处由首轮跑批暴露 | ✅已修 | 按 `value+0x3F000+0x40+d` 重算：`0x4383F042`/`0x43A3F042`/`0x43C3F042`/`0x43E3F042`/`0x4343F042`/`0x434BF042`/`0x4367F047`/`0x436BF047`/`0x436FF047` | A1 对账 0 不符；A3 解码复算 0 不符；三平台绿 |
| F2 orri 规范字 `0x…183` 的 `immu6` 实为 3，`rol.b`/`shr.sb` 首例期望按 1 写 ⇒ 首轮 rc=1 | ✅已修 | 改 `0x43645181`/`0x436C5181`（immu6=1） | 首轮 rc=1 → 修复后全绿 |
| F3 orrr 的 c=d 别名例 shamt 由「值」低 3 位决定，`shr.ub` 0x04 / `shr.sb` 0x40 与期望不符 | ✅已修 | 改 0x0A（shamt 2）/`0x46`（shamt 6），注释写明约束 | 点 13 三平台绿；A3 校验别名自洽 |
| F4 `rev.b` 点 10 期望按错误单元序写（0x96 实为 2 位单元回文 ⇒ 0x96 而非 0x99） | ✅已修 | 换 `0xD2 ⇒ 0x87` 并列清单元序 | A3 0 不符 + 三平台绿 |
| F5 证据脚本 A2 两行 `ck "$NCHAIN" "$NCHAIN"` 同源自比（恒真） | ✅已修 | 改为「驱动器统计 vs `grep` 现场行数」= 293 / 31 | 修版首跑即红（`grep '^\t'` 取 0 行）⇒ FAIL 路径可达 |
| F6 故障名注入（ILLI→CFXMEM）期望退出码误写 0xF8 | ✅已修 | 改期望 = 检查点号 14（落点 one-hot 不符 ⇒ 失败码） | 三平台 chipyard=gem5=qemu=14 |
| F7 `rev.b` 点 10 注释残留旧值 | ✅已修 | 注释改 0xD2 ⇒ 0x87 | `grep '0x96\|0x99'` = 0 |

### 第 1 轮 reviewer 验收

**判决：Accepted** —— 下列命令与退出码均为我亲自重跑（主控机 worktree + 节点 `ics160`），不采信完成区转述。

**重跑记录（命令 ⇒ 实测）**
1. `ls tests/inst/10-arith-logic-byte/*.S | wc -l` ⇒ **21**；我自写点号扫描：21 文件点号 `1..N` 连续、最大 17（≤127）；链例 **293** + 故障例 **31** = 镜像 **52**；21 个 id 与 §范围 逐一对应、无多余载体。
2. `<运行期证据目录>`（worktree 内 A 段）⇒ `EXIT=0`、`summary: FAIL=0 / RESULT: PASS`：头部↔`contracts/opcodes.yaml` 0 不符、scan rc=0、`check_indep` a/b 各 **324 例 / 不符 0**、片段 21 条 / 非法 0、根清单未含 10 册。
3. **三平台**（节点 `ics160`，独占 staging work-dir，未传 `--jobs` ⇒ 脚本默认 20）：`run.sh --tree … --full` ⇒ **`RUN_EXIT=0`、`FAIL=0`、48 PASS**；二进制 md5 qemu `5d04d3e8…` / gem5 `bc1b1b5f…` / chipyard `45748f3f…`（与完成区一致）；**52/52 通过**、故障例 **31 全 `0xF8`**、字节流 **63/63**（21 id × 3 平台）逐字节相等；21 个 `.S` 节点侧 md5 与 worktree 逐一相同。
4. L1 我本机逐条：`check_tests_index.py` **rc=0（385）**、`check_case_ledger.py` **rc=0（2184）**、`validate_vectors.py` **rc=0（156/156，gaps 0）**、sweep **md5 `2d4d94651346ef673c5a855e024c1489` / covered=273**。
5. `make check-inst`（节点）⇒ **rc=2**，`1141 total / 1135 passed / 1 failed / 5 deferred`，红集**恰** `divrem.yaml[23]`；`make check-inst-smoke` ⇒ **rc=0（90/90）**。
6. **我自写复算** `indep_rev.py`（语义只据 `spec/SimRISC-10`+`SimRISC-04` 推导，不读 engineer 检查器）：21 id 全量 324 例 ⇒ **不符 0**；反例（改 `mul.ub` 点5 期望）⇒ `MISMATCH …点5`、**rc=1**（FAIL 路径可达）。
7. **独立注入 1 路**：`shr.ub_orrr_rd.S` 点5 期望 `0x0F→0x0E`（注入前 `cp` 备份 + md5 `a666f29f…`）⇒ `run.sh` **rc=1 / FAIL=4**（impl a、b 各 324 例、不符 1）；`cp` 还原 ⇒ md5 复等 `a666f29f…` ⇒ **rc=0 / RESULT: PASS**，`git status -uall` 干净。

**约束核验**
- 范围：`git diff --name-status 3d6ca5f3..2dfce5b3` = **23 A**（21 `.S` + 2 片段）+ **1 M**（任务书）；未动根清单 `tests/inst.yaml`、宏层 `macros/`、驱动器、`contracts/`、`spec/`、`Makefile`。
- 片段：21 条字段集唯一、`file` 全存在、片段内 id 唯一、与根清单 0 重、`001..021` 连续、`file` basename 集合 == 21 个 `.S`。
- F7：orrr 侧有 `rdHD=8≡0`（shl 点9 / shr.sb 点11 / shr.ub 点9 / rol 点11）与 `0x0B⇒3`，orri 侧 `immu6=8/63 ⇒ ILLI=0xF8`；三平台逐字节一致 ⇒ **按掩码、不 ILLI，不判缺陷**（口径仍待用户裁定）。
- 完成区 11 行（≤30）、第 1 轮审阅记录 12 行（≤40）、任务书无运行期路径；我未提交 git、未改主工作树、未重建组件；节点临时树用后已删（日志留存 `/tmp/opencode/m13-testcases-026/node-logs/`）。

**交 architect（不阻断）**
- 验收 4「`make check-inst` 红集不扩大（当前恰为既有 pin `{divrem.yaml[23]}`，rc=2 属预期）」与实测 rc=2 冲突：该红是**既有 pin**（`m13-qemu-010/012` 均以「红集恰 `divrem.yaml[23]`」为基线，归 `m13-testcases-032`），本任务 diff 未触任何被扫 `.yaml` ⇒ 建议收尾把验收文本改为「红集不扩大」。
- 完成区「git status -uall = 23 项全为新增、无既有文件改动」：实为 23 新增 + 任务书 1 项修改 ⇒ 措辞不准（文档级）。
- `discussing.md` 的移位量高位条目现只记 09/08 两册，byte（`SimRISC-10`）同款口径建议一并补。

## 完成区

**测试结果**：21/21 id、52/52 镜像三平台全绿（链例 21 条 × 24–120 B 逐字节一致；故障例 31 全 `0xF8`）；独立复算 324 例不符 0；注入 2 路（链点 9 / 故障点 14）三平台同码后回绿。
**修改文件**：新增 `tests/inst/10-arith-logic-byte/{add.sb,add.ub,cmp.sb,cmp.ub,div.sb,div.ub,mul.sb,mul.ub,rem.sb,rem.ub,rev.b,rol.b_orri,rol.b_orrr,shl.b_orri,shl.b_orrr,shr.sb_orri,shr.sb_orrr,shr.ub_orri,shr.ub_orrr,sub.sb,sub.ub}_*.S`（21）+ `tests/inst/.fragments/m13-testcases-026.{inst.yaml,migration.md}`；`git status -uall` = 23 项全为新增，无既有文件改动、未动共享清单/宏层/台账。
**验收结果**：
- 载体 21（`ls|wc -l`）；`--scan-only` 链例 293 + 故障例 31 = 镜像 52，点号 1..N 连续、每文件 ≤127（最大 17）。
- 三方同镜像（chipyard `45748f3f…` / QEMU `5d04d3e8…` / gem5 `bc1b1b5f…`）52/52 PASS；结果字节流 vs 独立复算 63/63 全等。
- `check_indep` impl a / impl b 各 324 例、不符 0；反例（rev.b 点 8 期望改错）⇒ 非零且命中点 8。
- 片段：`yaml.safe_load` 通过、条目 21、id 合法且与根清单无重、`file:` 全存在、非法项 0。
- 273 例 sweep md5 `2d4d94651346ef673c5a855e024c1489`（covered=273）不变；`check-tests-index` PASS(385)、`check-case-ledger` PASS(2184)、`validate_vectors` PASS（gaps 0）。
- `make check-inst` rc=2、红集**恰** `{divrem.yaml[23]}`（1141/1135/1/5，与施工前基线逐项一致；`.S` 不入该 YAML 门控）；`make check-inst-smoke` rc=0（90/90）。一键证据脚本（运行期证据目录，未归档）`--full` ⇒ `FAIL=0 / RESULT: PASS`。
**新发现/坑**：① 任务书验收 1 写「`.S` == 16」，与 §范围 21 个 id（及 `MIGRATION.md §4` 的 21）矛盾 —— 按 21 交付，任务书数字待改。② orri 的越界 `immu6`（8..63）与 `rev.b` 非 one-hot `k` **汇编器不报错**、原值落盘 ⇒ 故障例可直接用助记符（同 04 族）。③ 编码字别手算：`value + 0x3F000` 会在 ha 段进一位而静默变成相邻 id（本次 9 处，其中 3 处因结果同值被三方全绿掩盖）⇒ 一律按 `value|rd<<12|rd<<6|rd` 现场算，并加「头部 ↔ opcodes.yaml」对账。④ orrr 的 c=d 别名例中 shamt = 该值低 3 位，期望必须与值自洽。⑤ 主控机 gem5 构建产物于 11:16 为 0 B（另一会话重建中）⇒ gem5 md5 只能在节点侧对账（`bc1b1b5f…`），qemu/chipyard md5 与主控机一致。
**遗留问题**：① 任务书验收 1 的「== 16」为笔误（见上），无需实现变更。② 相关 YAML（`base/reg-arith.yaml`/`reg-compare.yaml`/`reg-shift-extend.yaml`/`rev/rev.yaml`/`rol/rol.yaml`）**未删**：仍含 32/16 位 id（待 024/025），且 §5.1 前置（inventory 载体登记 + 数据覆盖门控 + 生成器退役 + 台账重生成）未解 ⇒ 与 `030` 同批处理。③ 未决项：无。

