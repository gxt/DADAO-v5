# m13-testcases-018: `04-arith-logic-octa` —— `rev.*`/`rol.*`/`clmul.o`

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（宏层 `inst_test.inc` + `run_asm_suite.py` 已建好）；与其它 `tests/inst` 重构任务**串行**（共享 `tests/inst/`）
**可并行分片**：否
**状态**：已验证

## 背景

延续 `012`/`013` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。分类与用例模板见 `tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移台账）。

本任务覆盖 **4 个 id**（`04-arith-logic-octa` 位操作（rev/rol/clmul））

## 范围（id 清单，以 `contracts/opcodes.yaml` 为准）

```
clmul.o_rrrr_rd rev.o_orri_rd rol.o_orri_rd rol.o_orrr_rd
```

## 用例设计（5 类，模板见 `MIGRATION.md §3`）

- **encoding**：该 id 的编码校验（mask/value）
- **legality**：适用的合法性规则（`rd0/rb0`、`immu6=0`、范围/重叠、保留编码…），以 `contracts/legality_rules.yaml` 为准
- **semantic**：正常路径，宽度 × 符号 × 形式
- **boundary**：该族特有边界（进位/借位/最值/次正规/对齐/窗口/掩码…）
- **overlap**：源=目、部分重叠、块复制重叠

## 验收

1. `ls tests/inst/04-arith-logic-octa/` 下本任务 id 的 `.S` 齐全（== 4；现场 `contracts/opcodes.yaml` 本族 = 4）
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

改动面：4 个 `.S`、`tests/inst.yaml`（+4 条）、`MIGRATION.md`/`README.md`；**未改宏层/驱动器**。逐行自审 + 三平台实跑 + 独立重算（58 点）+ 注入反例。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `clmul.o {rd0,rd0}` / `{rd5,rd5}` 被 llvm-mc 静态拒绝（`dst_dual_same`），`TEST_FAULT_DUAL` 无法成像 | ✅已修 | 两条故障例改用 `TEST_FAULT_ENC` 原始编码字 `0x560000C4`/`0x561450C4`（与 YAML 同字） | QEMU 先红后绿；三平台故障例 rc 全 248 |
| `clmul.o` 表头 boundary 写 6、现场 7（漏数一条丢弃半例） | ✅已修 | 表头改 `boundary 7 / 链例 19+2` | `run.sh` 表头审计：4 文件不符 0 |
| 任务书验收 1 原写「== 21」，与 id 清单不符 | ✅已修 | 就地改「== 4」（现场 `contracts/opcodes.yaml` 本族 4；`MIGRATION §4` 同） | 4 个 `.S` 逐名核对；`check-tests-index` PASS 320 |
| clmul YAML 81 例（60+ 满宽随机）无法全塞 `.text` 0x1E00 | ❌不修（设计约束） | 采全部非随机类例 + 2 例随机代表（19 链例）；随机例保留在 YAML | 实测 `.text` 19+2 例 = 0x1128；83 例按 ~209 B/例必超 0x1E00（`lds` ASSERT 会拒） |
| 证据脚本 `>0` 断言误用字符串 `eq`（`>0` vs `58` 恒红） | ✅已修 | 改为数值 `-gt` 分支 | 重跑 `--inject`：PASS=26 FAIL=0 / exit 0 |
| 反例注入点选择 | ✅已修 | clmul boundary 11 低半 `…5555`→`…5556` | 三平台链例 rc 全 **11**；`cp` 还原 md5 `96649fc1…` 回绿 3/3 |

自审结论：逻辑/点号/期望/类别计数逐项对账，无未修代码 finding；遗留项均为 YAML 退役/其它任务。

### 第 1 轮 reviewer 验收（2026-11-14，三平台重跑在 server207）

**重跑记录（全部本人执行，输出为真实终端）**
1. **id 三方对账**：`contracts/opcodes.yaml` 中 mnemonic∈{rev.o, rol.o, clmul.o} 恰 **4** id（`clmul.o_rrrr_rd`/`rev.o_orri_rd`/`rol.o_orri_rd`/`rol.o_orrr_rd`）== 4 个 `.S` == `inst.yaml` 新增 4 条（030..033）；`ctlz/cttz/ctpop` 独立核为 `spec_cite: SimRISC-12`、scope m8 ⇒ 确不在 04 册本族，engineer 陈述成立。
2. **节点全量重跑**（rsync 副本 + `.work`/`.dadao` 软链，跑 engineer 的一键证据脚本）→ **`summary: PASS=22 FAIL=0`，exit=0**。三平台 **12/12**：链例 4（152/104/96/112 B == 8×19/13/12/14 点）、故障 8 rc 全 **248**、36 条平台记录、故障码分布 `{0xf8: 8}`；编码 4/4 mask/value + `.S` 原始字 == llvm-mc；迁移对账 4/4（clmul 12、rev 16、rol 7/9）。
3. **独立复算（reviewer 自写脚本、放运行期临时目录，不采信 58）**：59 点不符 **0**；重点：clmul 64×64 低半（点 6/7/11/14 另用位卷积算法二次核 OK）、rev 字节反转（k=8 `bswap64` 点 6/13、k=1 点 3）、rol 两形式移位量 0/63（orri 点 3/7、orrr 点 3/7）与 64/65（orrr 点 9/8 取低 6 位）全 OK。
4. **主控机门控（不依赖二进制）**：`check-tests-index` rc=0（320）｜`check-case-ledger` rc=0（2170）｜`validate_vectors` rc=0（gaps 0）｜`inst_sweep emit` md5 **`2d4d94651346ef673c5a855e024c1489`** 不变。
5. **独立注入（自设计，非 clmul 点 11）**：`rev.o_orri_rd.S` 点 6 期望 `…2301→…2302` → `run_asm_suite` **exit=1**、链例三平台 rc 全 **6**；同一 `run.sh` 重跑 **`PASS=17 FAIL=5`，exit=1**；`cp` 还原 md5 `1a40a950…` == 注入前 → 同一脚本回绿 **`PASS=22 FAIL=0`，exit=0**；节点无 `.preinject*` 残留。
6. **脚本审核**：32 个断言调用点（30 个独立断言名）逐条有可达 FAIL 路径（非恒真、无两支同写）；覆盖计数现场派生（`58`/`12`/`36` 均由 scan/suite 日志解析，非写死）。
7. **约束核验**：`git diff HEAD~1..HEAD` 恰 8 文件 == 完成区「修改文件」；未碰 `contracts/`/`spec/`/`Makefile`/宏层；完成区 16 行 ≤30；任务书 grep 运行期路径 0；4 个 `.S`+`inst.yaml` md5 与注入前一致（reviewer 未改产物）；未提交 git、未重建组件。

**重试记录**：节点首跑 2 FAIL（`check-inst` vacuous「git 索引 0 册」+ Tiny rc=1）——根因是我方 `git init` 副本索引为空的**环境布置问题**，非交付物缺陷；`git add -A` 补索引后重跑即绿（**第 1 次修复性重跑**），未掩盖根因。

**观察项（不阻断）**：① 节点 `check-inst` rc=0（1136/1141、0 failed），主控机 engineer 记录 rc=1（红恰 `divrem.yaml[23]`）——两机 QEMU 二进制差异，该红为 015/016/017 同款既有基线（归 `m13-testcases-032`），两口径下本任务均无新增红。② 完成区 PASS 计数与本人实测有出入：完成区称 `--inject` PASS=26、完整跑 PASS=23；本人节点实测 `--inject` **PASS=28 FAIL=0 exit=0**、完整跑 **PASS=22 FAIL=0 exit=0**（23↔22 可由 check-inst rc=1 走红集断言 2 条 / rc=0 走单条 1 条的分支差异自洽解释；26↔28 与 `SKIP_*` 配置组合相关，完成区未标注所用 SKIP）——**核心判据不受影响**（FAIL=0、exit=0、注入三平台点号、还原回绿均实测吻合），判文档级标注不精确，留 architect 收尾时补注配置。

**判决：Accepted**（验收 1–7 在本人重跑下全过，硬约束无违反；架构师终审）

## 完成区

**测试结果**：三平台 **12/12** 镜像通过（4 id；链例 4 + 故障例 8，36 条平台记录；故障码全 `0xF8`）；证据脚本 `--inject` **PASS=26 FAIL=0 / exit 0**，完整跑（含 L3）**PASS=23 FAIL=0 / exit 0**；期望独立重算 **58 点 / 不符 0**；04 全册 QEMU 回归 **76/76**（33 id）。
**id 数**：现场 `contracts/opcodes.yaml` 本族 = **4**（`clmul.o_rrrr_rd` / `rev.o_orri_rd` / `rol.o_orri_rd` / `rol.o_orrr_rd`）；任务书验收 1 原写「== 21」已就地改为「== 4」。`ctlz`/`cttz`/`ctpop` **不在本任务 id 清单**（`bitcnt.yaml`，scope m8）；`ext.*` 已由 017 覆盖。
**修改文件**：新 4 个 `tests/inst/04-arith-logic-octa/{clmul.o_rrrr_rd,rev.o_orri_rd,rol.o_orri_rd,rol.o_orrr_rd}.S`；改 `tests/inst.yaml`（+4 条 `inst-04-arith-logic-octa-030..033`）、`tests/inst/MIGRATION.md`（§5 行 + §6/018）、`tests/inst/README.md`（04 行）；本任务书。`git status -uall` 恰这 8 项，无其它残留。
**验收结果**：
1. 4 个 `.S` == id 清单；点号 1..N 连续、≤127；表头类别合计 == 现场链例数（不符 0）
2. 三方同镜像逐字节：链例 4（rc=0、字节数 = 8×点数、三平台相等）+ 故障例 8（rc 全 248）
3. 编码对账：4/4 mask/value 命中；`.S` 原始编码字 == llvm-mc（含 rd63/rd0 字段边界）
4. 期望独立全量重算（`spec/SimRISC-04 §1.5/§2.2`，大整数）：58 点，不符 0
5. `check-tests-index` rc=0（320 条）｜`check-case-ledger` rc=0（2170）｜`validate_vectors` rc=0（gaps 0）｜273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变
6. `make check-inst` rc=1，红集**恰** `{divrem.yaml[23]}`（既有基线；1141 total / 1135 passed / 1 failed / 5 deferred）；Tiny 子集 44/44 rc=0
7. 可达 FAIL：clmul 点 11 期望改错 ⇒ 三平台 rc 全 **11**；`cp`+md5（`96649fc1…`）还原 → 回绿 3/3
8. YAML：rev.o（16 例）、rol.o 两形式（7/9 例）全类例并入；clmul.o 81 例中非随机 12 例 + 2 随机代表并入；三 YAML 文件**未删**（实测删 `clmul.yaml`：`check-tests-index` 1 项、`check-case-ledger` 多 81 行、`semantics_gate --check-only` 3 项 FAIL；md5 `74e259b4…` 已还原）
**新发现/坑**：① `clmul.o` 的 `dst_dual_same` 由 llvm-mc 静态拒绝（`mul.*`/`add.*` 不拒）⇒ 非法双目的只能 `TEST_FAULT_ENC`；② `rev.o` k 非 one-hot（0/3/5）与 `dst_rd0` 三方一致判 ILLI；③ `rol.o` orrr 旋转量取 `rdHD[5:0]`（64→0、65→1，不 ILLI），orri 全 0..63 合法；④ `clmul.o` 源先读后写（目的与源同号时结果按原值）；⑤ 单文件链例数受 `.text` 0x1E00 上限约束（~33 个双目的例即满），大 YAML 随机集需分片载体或紧凑宏。
**遗留问题**：① clmul 满宽随机 semantic（60 例）留在 YAML，`.S` 未全量并入（`.text` 上限；YAML 退役归 `m13-testcases-030`）；② `check-inst` 的 `divrem.yaml[23]` 既有红归 `m13-testcases-032`；③ `ISS-410` 的 hmon 自装 workaround 沿用；④ `check-knowledge-refs` 余红仅 `m14-infra-001`/`m14-spec-003`，与本任务无关（本任务命中 0）。
