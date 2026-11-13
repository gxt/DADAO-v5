# m13-testcases-014: `02-reg-copy` —— 复制（`rd2rd`/`rb2rb`/`rb2rd`/`rd2rb`/`ra2rd`/`rd2ra`）+ 条件选择（`cs.*`）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（宏层 `inst_test.inc` + `run_asm_suite.py` 已建好）；与其它 `tests/inst` 重构任务**串行**（共享 `tests/inst/`）
**可并行分片**：否
**状态**：已验证

## 背景

延续 `012`/`013` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。分类与用例模板见 `tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移台账）。

本任务覆盖 **16 个 id**（02 寄存器复制 册：复制（`rd2rd`/`rb2rb`/`rb2rd`/`rd2rb`/`ra2rd`/`rd2ra`）+ 条件选择（`cs.*`））。

## 范围（id 清单，以 `contracts/opcodes.yaml` 为准）

```
cs.eq_rrrr_rd cs.n_rrrr_rd cs.n_rrrr_rf cs.ne_rrrr_rd cs.p_rrrr_rd cs.p_rrrr_rf cs.z_rrrr_rd
cs.z_rrrr_rf ra2rd_orri_ra rb2rb_orri_rb rb2rd_orri_rb rd2ra_orri_ra rd2rb_orri_rb rd2rd_orri_rd
rd2rf_orri_rf rf2rd_orri_rf
```

## 用例设计（5 类，模板见 `MIGRATION.md §3`）

- **encoding**：该 id 的编码校验（mask/value）
- **legality**：适用的合法性规则（`rd0/rb0`、`immu6=0`、范围/重叠、保留编码…），以 `contracts/legality_rules.yaml` 为准
- **semantic**：正常路径，宽度 × 符号 × 形式
- **boundary**：该族特有边界（进位/借位/最值/次正规/对齐/窗口/掩码…）
- **overlap**：源=目、部分重叠、块复制重叠

## 验收

1. `ls tests/inst/02-reg-copy/` 下本任务 id 的 `.S` 齐全（== 16）
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

改动面：`tests/inst/02-reg-copy/`（16 个 `.S`）、`tests/inst/macros/inst_test.inc`（宏层 + RDATA/SCRATCH + `rb29`）、
`tools/testcases/inst/run_asm_suite.py`（3 个正则）、`tests/inst.yaml`（+16 条）、`MIGRATION.md`、`README.md`。
逐行自审 + 三平台实跑 + 现场统计复核，findings 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `__SET_MEM` 的偏移参数被写成**值**（`__SET_MEM ra62, 0x0F1E…`）⇒ 算出 `RDATA+巨值` ⇒ CFXMEM、链例挂死（rc=-2） | ✅已修 | boundary 例改 RDATA 偏移（`0x60`/`0x50`） | ra2rd 5/5 镜像通过 |
| `cs.*` 的 rd0 作条件/比较寄存器时仍 `__LI rd0` ⇒ `set.zw rd0` 触发 ILLI（dst_rd0）⇒ 链例挂死 | ✅已修 | `TEST_CS1/CS2/CS1_RF` 内 `.ifnc \cond,rd0` 跳过装载 | cs.* 8 文件各 14+1 全绿 |
| `TEST_FAULT_CS` 用 `{rd1, rd2}` 文本传两个比较操作数 ⇒ 宏参数被逗号切断（汇编失败） | ✅已修 | 拆 `TEST_FAULT_CS`（单条件）/`TEST_FAULT_CS2`（两操作数分开传）+ 驱动 `FAULT_RE` 增 `_CS2` | cs.eq/ne 故障例 rc=248 |
| 故障例签名把故障名放末位 ⇒ 与驱动 `FAULT_RE`（第 4 字段）不符，故障镜像不被识别（只跑 1 个镜像） | ✅已修 | 签名改 `pt, mnem, dst, fault, …` | `--scan-only` 报「故障例 1」 |
| `rd2rb`/`rb2rd` 第 9 例用「上一例刚写入的**目的**」当源（源/目的写反）⇒ 点号 9 红 | ✅已修 | 源改回组顶端寄存器 | 两文件 11+4 全绿 |
| `rd2rb` 63 元素例按 `rd5↔rb6` 算偏移（实际同号对应 `rb6←rd6`）⇒ 点号 11 红 | ✅已修 | 改 `rd6`，注释写清对应关系 | 同文件 11+4 全绿 |
| 同组复制 count=63 不可能（源/目的须不相交 ⇒ n≤31）：`rd2rd {rd1:rd63},{rd0:rd62}` 被汇编器拒绝 | ✅已修 | 同组用 31、跨组用 63，`.S` 注释写明理由 | `rd2rd`/`rb2rb` 链例全绿 |
| 13 个文件的表头「用例：类别…（链例 N + 故障例 M）」与实际点数不符 | ✅已修 | 按现场重算表头；证据脚本加 A2 段机械核对 | 16 文件「表头 == 现场、类别合计 == 链例数」不符 0（A2 PASS） |
| 驱动 `scan_source` 不认识 `TEST_MOV1`/`TEST_CS*` ⇒ 检查点数少算 ⇒ 期望字节数错（必红） | ✅已修 | `CHAIN_CASE_RE`/`CHAIN_PT_RE` 扩 `TEST_MOV\w*`/`TEST_CS\w*` | `--scan-only` 16 行、镜像 58 = 16+42 |
| `.S` 头未说明链接布局从何而来（本册无自己的 `.lds`） | ✅已修 | 每文件头一行「复用 `01-load-store/inst-tiny.lds`」 | 16 文件头齐 |

判决：findings 全部已修 ⇒ 状态可置 `待验收`。

### 第 1 轮 reviewer 验收

判决：**Accepted**（状态保持 `待验收`）。快照对账：审查前 `git status --porcelain -uall` = **0 行**，全部验收命令跑完后仍 **0 行**、22 个目标文件 `md5sum` 前后逐项相等；写入本审阅记录后仅剩本任务书 1 行（reviewer 自己的新增）。HEAD 仍 `9baa9072`（reviewer 未提交、未 checkout）。

**重跑记录（我自己的命令 + 真实输出/退出码）**
1. id 对账：`contracts/opcodes.yaml` 该类恰好 16 个 id，与 `tests/inst/02-reg-copy/*.S` 逐名相等（无遗漏/无多余）；`tests/inst.yaml` 新增 16 条编号 1..16、file 与磁盘一致、platforms/level 全为 `system/full`。
2. `run_asm_suite.py --vectors tests/inst/02-reg-copy --lds …/inst-tiny.lds --scan-only` → **rc=0**：16 id / **58 镜像**，点号 1..N 连续且 ≤127（链例 14×8+11+10+11+12+11+11+12+11 = **201**，故障例 **42**）。
3. 独立三方全量（我起的，非脚本）：`run_asm_suite.py --vectors tests/inst/02-reg-copy --lds … --jobs 4` → **exit=0**、`58/58 镜像通过（16 个 id；链例 16，故障例 42）`；链例三平台 rc 全 0 且字节 = 8×点数、故障例三平台 rc 全 **248**（`0xF8`）。
4. 独立期望值复算（不采信 58/58）：自写 oracle（`spec/SimRISC-02 §1/§2/§3` 语义 + `opcodes.yaml` 字段解码）逐行模拟 16 个 `.S` 的全部 **201 个检查点**与全部手写指令/`.dd.t32` 原始字 → rc=0「**全部期望值与 opcodes.yaml 编码一致**」；`cs.*` 三值条件（n/z/p 取支、eq/ne 目的在第三操作数 rdHC、not-taken 保持初值、rd0/rf0 特例）、块复制各 bank 宽度/符号（64 位二进制不变、同组 ≤31 / 跨组 63、0 号作源）、故障异常码（immu6=0、两侧 起始+immu6=65、部分交错/完全重合、dst_rd0/rb0/rf0 ⇒ ILLI）逐条复算命中；16/16 表头类别合计 == 现场链例数。
5. 门控（我重跑）：`make check-inst` **exit=0**（vast 1136/1141 + tiny 44/44）、`check_tests_index.py` **exit=0**（279 条）、`check_case_ledger.py` **exit=0**（2170）、`validate_vectors.py` **exit=0**（gaps 0）、`inst_sweep.py emit` md5 = `2d4d94651346ef673c5a855e024c1489`（**273 例不变**）。
6. 证据脚本审 + 重跑：逐段核 `run.sh`（A/A2/B/C/D/E 各断言均有可达 FAIL 路径，无恒真、无两支同结果）→ `bash .work/evidence/m13-testcases-014/run.sh` = **`PASS=17 FAIL=0` exit 0**；`… --inject` = **`PASS=23 FAIL=0` exit 0**（与完成区 23/0 一致；F 段还原 md5 `2db20f31…` 后回绿）。
7. **独立注入**（不复用工程师的 rd2rd 11 号）：`cs.z_rrrr_rd.S` 13 号 boundary 期望 `0xFFFF…FFFF`→`…FFFE`（md5 `f93a1a4b…`→`bf3740b6…`）⇒ 重跑**同一** `run.sh` = **`PASS=14 FAIL=3` exit 1**，失败链例三平台 rc 全 **13**（点号 = 用例序号，三平台同值）；`cp` 还原后 md5 复等 `f93a1a4b…`、`git status` 0 行；随后 `--inject` 全绿证实回绿。
8. 回归与 L1 红归属：`01-load-store` 全量 `235/235（38 个 id）` exit 0；`check-knowledge-refs`（5 处全在 m13-013 任务书）、`check_run_artifacts`（17 条全为 infra 日志名）、`check_milestones_fresh`（本 worktree 派单前台账；主树 `milestones-m13.md:54` 已在「进行中」且带派单时间）——三者对本任务文件的命中数 **0**，红均非本交付引入。

**约束核验**：改动面 = `9baa9072` 的 22 文件，全在任务书范围内（16 新 `.S` + `inst_test.inc` / `run_asm_suite.py` / `inst.yaml` / `MIGRATION.md` / `README.md` / 本任务书）；未碰 `contracts/`、`spec/`、`Makefile`；完成区 16 行 ≤30、无具体运行期路径、数字与我重跑逐项一致；YAML 未删（未迁完 ⇒ 不满足 git rm 前置，MIGRATION §6 有实测阻塞理由）；hmon workaround 未动；注入还原只用 `cp`+md5。

**Finding（不阻断，交 architect 收尾改）**：`run.sh:68` 的 `echo` 含反引号 ⇒ 日志出现 `line 68: .S: command not found`、A2 标题被截断；只影响日志文本，不影响任何断言与退出码。

## 完成区

**测试结果**：三方 **58/58** 镜像通过（16 id；链例 16 / 故障例 42，三平台 rc 全 = `0xF8`）；运行期证据脚本 `--inject` **PASS=23 FAIL=0**；`01-load-store` 回归 **235/235**（38 id 全绿）。
**修改文件**（`git status --porcelain -uall` = **22 项**：16 新 + 6 改，含本任务书）：
- 新 `tests/inst/02-reg-copy/<16 个 id>.S`
- 改 `tests/inst/macros/inst_test.inc`（`TEST_MOV1`/`TEST_CS1`/`TEST_CS2`/`TEST_CS1_RF`/`TEST_FAULT_MOV`/`TEST_FAULT_CS{,2}`/`__VERIFY_*`/`__SET_MEM`、RDATA/SCRATCH、`rb29`）、`tools/testcases/inst/run_asm_suite.py`（3 个正则）、`tests/inst.yaml`（+16 条）、`tests/inst/MIGRATION.md`、`tests/inst/README.md`
**验收结果**：
1. 16 个 `.S` == 任务书 id 清单（逐名对账）；点号 **1..15–17** 连续、≤127（`--scan-only` 16 行）
2. 三方同镜像逐字节：链例 16（rc=0、字节=8×点数、三平台字节流相等）+ 故障例 42（三平台 rc 全 248）
3. `check-inst` **PASS**（vast 1136/1141 + tiny 44/44）、`check-tests-index` **PASS**（279 条）、`check-case-ledger` **PASS**（2170）、`validate_vectors` **gaps 0**、273 例 md5 不变
4. 注入（改错 `rd2rd_orri_rd` 11 号期望）⇒ 三平台 rc 全 **11**；`cp`+md5 还原回绿
5. 编码对账（独立 oracle）：16 个 id 的 mask/value 由 `contracts/opcodes.yaml` × `llvm-mc` 规范字逐一命中
6. L2 `make check-modules` **PASS**；L1 `make -k check` 3 项红全是既存（见遗留）
7. YAML 未删：`reg-cond-assign`/`fp/cond-assign` 实测 4–5 个门控阻塞，理由落 `MIGRATION.md §6`
**新发现/坑**：①同组块复制要求源/目的不相交 ⇒ 最多 31 元素（跨组才可 63）；②`set.zw rd0` 是 ILLI（dst_rd0）⇒ 以 rd0 作条件时不能先装载；③`ra0[63:54]` 是 SBZ ⇒ 作目的只能用低位有意义的期望；④`rf0` 读出 FCSR（值不确定）⇒ 作源只能断言「与当前 rf0 相等」；⑤宏参数里的逗号（`{a, b}`）会切断参数 ⇒ 两个操作数分开传。
**遗留问题**：①三个 YAML 的删除归 `m13-testcases-030`（`.S` 载入门控接入 + YAML 退役）；②L1 既存红：`check-knowledge-refs`（m13-013 任务书 5 处 `.work/**` 引用，主树同红）、`check-run-artifacts`（他任务日志名 17 条）、`check-milestones-fresh`（本 worktree 台账是派单前基线：014 与并行任务 `m13-integ-009` 仍记「待开始」；主会话已在主树移入「进行中」）；③`ISS-410` 的 hmon 自装 workaround 仍在。
