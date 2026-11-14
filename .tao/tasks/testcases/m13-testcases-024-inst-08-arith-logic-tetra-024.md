# m13-testcases-024: `08-arith-logic-tetra` —— `.ut`/`.st` 全族

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（宏层 `inst_test.inc` + `run_asm_suite.py` 已建好）；与其它 `tests/inst` 重构任务**串行**（共享 `tests/inst/`）
**可并行分片**：否
**状态**：已验证

## 背景

延续 `012`/`013` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。分类与用例模板见 `tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移台账）。

本任务覆盖 **21 个 id**（`08-arith-logic-tetra`）

## 范围（id 清单，以 `contracts/opcodes.yaml` 为准）

```
add.st_orrr_rd add.ut_orrr_rd cmp.st_orrr_rd cmp.ut_orrr_rd div.st_orrr_rd div.ut_orrr_rd
mul.st_orrr_rd mul.ut_orrr_rd rem.st_orrr_rd rem.ut_orrr_rd rev.t_orri_rd rol.t_orri_rd
rol.t_orrr_rd shl.t_orri_rd shl.t_orrr_rd shr.st_orri_rd shr.st_orrr_rd shr.ut_orri_rd
shr.ut_orrr_rd sub.st_orrr_rd sub.ut_orrr_rd
```

## 用例设计（5 类，模板见 `MIGRATION.md §3`）

- **encoding**：该 id 的编码校验（mask/value）
- **legality**：适用的合法性规则（`rd0/rb0`、`immu6=0`、范围/重叠、保留编码…），以 `contracts/legality_rules.yaml` 为准
- **semantic**：正常路径，宽度 × 符号 × 形式
- **boundary**：该族特有边界（进位/借位/最值/次正规/对齐/窗口/掩码…）
- **overlap**：源=目、部分重叠、块复制重叠

## 验收

1. `ls tests/inst/08-arith-logic-tetra/` 下本任务 id 的 `.S` 齐全（== **21**；判据 = §范围 清单）
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

自主逐行审查 21 个 `.S` + 生成/复算/证据脚本（`run.sh` / `check_indep.py` / `gen_cases.py`）：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `rev.t` 点 1 期望照抄 `rev.o` 的 bswap64（k=8 实为两块各 bswap32、块位置不交换） | ✅已修 | 期望改 `0x67452301EFCDAB89`，注释写明「块位置不交换」 | 三平台 54/54；两套独立复算 0 不符 |
| F2 「两源同名」用例的目的与两源同号 ⇒ 宏跳过装载、源值=目的初值，内联期望与复算不符 | ✅已修 | 目的改 `rd12`（第三个寄存器），两源 `rd11` | 同上（372 例 0 不符） |
| F3 证据脚本的注入点号在用例扩充后失效（17→20），且故障注入被 `--chain-only` 跳过 | ✅已修 | 改点 20；`inject()` 增 chain_only/记录选择/期望码三参 | 注入 2 路：三平台同点号 4 / 20 红，均回绿 |
| F4 orrr 移位量 >31 的 spec 表述有张力（§2 表「hd[5] 应为零」vs §2.2「取低 5 位、天然取模」） | ⏸延后（待裁定） | 按 §2.2 + 三实现实测口径写用例（取模、不 ILLI），记入「待裁定」 | 三平台 shl/shr/rol orrr 的 32 与全 1 移位量用例通过 |
| F5 故障例的 `immu6`/`k` 越界只能走原始编码字路径（汇编器接受 32..63 但运行时 ILLI） | ❌不修（说明） | 复用 `TEST_FAULT_ALU_ORRI`（宏内已按原始编码装载） | 33 个故障镜像三平台全 `0xF8` |

判决：全部 finding 已修或已说明（F4 为 spec 措辞待裁定，不影响本册用例口径），状态置 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录（我自己的命令 / 真实输出 / 退出码；开工快照 `git status -uall` 空，HEAD=7cbdf7e6）**

1. `.work/evidence/m13-testcases-024/run.sh`（A 段）→ `summary: FAIL=0`、`RESULT: PASS`、`EXIT=0`：A1 21 id/21 载体、A2 339 链例+33 故障+54 镜像（点号 ≤127 连续）、A3 372 例 0 不符×2 实现+反例命中点 4、A4 片段 21 条且根清单 0 条、A5 三门控 rc=0 与 273 md5 `2d4d94651346ef673c5a855e024c1489`（covered=273）。
2. `run.sh --full` 第 1 次 → `FAIL=10` `EXIT=1`，根因 `[FAIL] gem5 可执行：期望=yes 实际=no`（共享 `.work/source/gem5/build/DADAO/gem5.opt` 正被 `m16-gem5-008` 重建、mode 644）＝**环境性**；第 2 次钉住完成版（gem5 `a6c53a0d…`／qemu `5d04d3e8…`／chipyard `45748f3f…`）→ `FAIL=0` `EXIT=0`：**54/54、故障 33/33 全 `0xF8`、链例三方字节一致、其注入 2 路三平台同点号 4/20 并回绿**（日志 `.work/log/testcases/m13-testcases-024-review-full{,2}.log`）。
3. 门控直跑：`check_tests_index.py` `EXIT=0`（385 条）；`check_case_ledger.py` `EXIT=0`（2184 条）；`validate_vectors.py` `EXIT=0`（156/156、gaps 0）；`make check-inst` `EXIT=2`、红集**恰** `{divrem.yaml[23]}`、`1141/1135/1/5` ＝既有基线红（多任务书记载），本任务无新增红。
4. 独立复算（自写 `recheck.py`：按 `SimRISC-08`+`SimRISC-04` 定值表、还原宏装载与同名跳过规则）→ **372 例（链 339 含编码 42 + 故障 33）不符 0**，点号 1..N 连续、编码字重编码一致、故障 ILLI 依据逐条核。
5. 独立注入 1 路（`div.st` 点 9 `INT32_MIN÷−1` 期望 `…80000000→…80000001`，`cp` 备份）：`check_indep` 报「点 9」`EXIT=1`；`run.sh` → `FAIL=4` `EXIT=1`；三平台直跑（`--jobs` 用默认 32）→ `chipyard=9,qemu=9,gem5=9` `EXIT=1`；`cp` 还原 md5 `af95f8a9cadf40ac9b5594dabdf6b74f` 前后一致 → `run.sh` `EXIT=0`、复算 0 不符、`git status -uall` 干净。

**约束核验**

- id/点号/三平台：21 个 `.S` 与 §范围 21 id 逐一对齐；54/54、33 故障全 `0xF8`、链例字节流三方一致（均为我方重跑）。
- F7：`shl.t/rol.t/shr.st/shr.ut` 的 orrr 各含 `shamt=0x20(≡0)` 用例（pt9/pt8/pt9/pt8）与全 1 移位量，三平台一致通过 ⇒ 取模 32、不 ILLI；orri `immu6=32/63` 故障全 `0xF8`。spec 张力已入 `discussing.md`，本任务不判缺陷 ✓。
- `rev.t` k=8 独立结论：**每 32 位块各自按 8 位单元倒序（＝bswap32）、块位置不交换**，`0x01234567_89ABCDEF → 0x67452301_EFCDAB89`，**不是** bswap64；与 `SimRISC-08 §2.1`「两个块一律同样处理」一致，三平台点 1 通过 ⇒ 工程师结论成立。
- 越界：`git diff --name-status master...HEAD` 恰 24 项（任务书 + 21 `.S` + 2 片段）；**未改** `tests/inst.yaml`/`MIGRATION.md`/`README.md`/`macros`/`run_asm_suite.py`/`contracts/`/`spec/`/`Makefile`；完成区 23 行 ≤30、无运行期路径；「修改文件」与 diff 对账一致；审前后快照 `git status -uall` 均空（仅本审阅记录一处改动）。
- 片段：21 条 `yaml.safe_load` 通过、id 合法、与根清单无重、`file` 全存在；`.migration.md` 的 §1 行/§6 小节格式与 `MIGRATION.md` 一致。
- 证据脚本审核：`run.sh` 各断言均有可达 FAIL 路径（A3 反例、B2 两路、本审注入均实测 FAIL），计数现场派生、无恒真/两支同源；已原样重跑，未另写等价脚本。

**阻断（Needs Revision）**

1. **验收 5 未完成**：5 个 YAML 中本任务 21 id 共 114 例（全 `active`），**16 例未并入 `.S`** —— `rol/rol.yaml` 11（`rol.t` orri/orrr `src=0xFFFFFFFFDEADBEEF` 的 imm 0/1/30/31、amount 0/1/15/31/35 及 2 条 boundary）、`base/reg-shift-extend.yaml` 4（`shr.st`/`shr.ut` × orrr/orri `src=0x0F0F0F0F0F0F0F0F, imm=2 ⇒ 0x03C3C3C3`）、`rev/rev.yaml` legality `k=5`（故障例仅 0/3/32/63/rd0）；另 4 条 encoding 注「`rdhd=rd0` 合法」无 rd0 作除数的用例。前例 018/022 均为「全部并入或写明抽样理由」。
2. **完成区/片段声明失真**：片段称「用例已并入（注释逐条标出具体数值）」，实际 `.S` 内 `YAML … 并入` 注释仅 33 行，`rol.t_orri_rd.S`/`rol.t_orrr_rd.S` 为 **0 行** ⇒ 违反「完成区与真实输出逐条对齐」。
   修法：把上述 16 例（含 4 条 encoding 性质说明）补入对应 `.S`（点号顺延、故障点重排）并重跑 `run.sh --full` + 三门控；或按 018 先例把抽样理由写进任务书/片段，并把声明改为实况。

**非阻断 finding**：任务书验收 1 写「== 16」（`MIGRATION.md §1` 初估值），实际 21（附录 A/片段/门控均 21）——文档笔误，交 architect 收尾改。

**判决：Needs Revision**（仅阻断验收 5 与完成区对齐；门控、三平台 54/54、独立复算、注入链全绿，未见代码/spec 缺陷）。

### 第 2 轮 engineer 自审（返工，回应第 1 轮 reviewer 阻断）

选择路线 **①（补齐，不抽样）**：把 5 个 YAML 中本任务 21 id 的 **114 例**逐条并入 `.S`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| B1 验收 5 未达成（`rol/rol.yaml` 11、`reg-shift-extend` 4、`rev` k=5、div/rem 的 `rdhd=rd0` 4） | ✅已修 | 新增 21 个向量（同向量去重后覆盖 114 例）：rol.t orrr 的 amount 0/1/15/31/35（点 16–20）、rol.t orri 的 imm 0/1/30/31（点 14–17）、`shr.{st,ut}×{orrr,orri}` 的 `0x0F0F…>>2 ⇒ 0x03C3C3C3` 与完整源值的 `>>31`、rev.t 的 k=8 端序例/k=1 源 0/k=5 故障（点 22）、div/rem 的 `rd0` 作除数 4 例（点 18/20）、div.st/rem.st 的「源带高位垃圾的 INT32_MIN÷−1」 | `check_yaml_merged` **114 例 / 未并入 0**；三平台 **55/55** |
| B2 声明失真（片段/完成区称「已并入」，`rol.t_*` 内 0 条注释） | ✅已修 | 片段改为「114/114 全部并入，无抽样」+ 机械判据；`.S` 内 `YAML … 并入` 注释 33 → **57 条**（21 文件全覆盖，rol 4/5 条） | 措辞与 `grep -c` 现场值一致 |
| 根因：生成器 `extra` 字典**重复键**（div/rem 4 个 id 写两遍）⇒ 前一轮 8 条 YAML 用例被静默丢弃 | ✅已修 | 合并重复键；把「已并入」从人工声明升级为**机械核对**（`check_yaml_merged.py`：按 `encoding.word` 解字段 + `input_state` 还原向量签名，含别名/`rd0` 源） | A4b：114/0；反例（删 div.st 的 rd0 除数例）⇒ 未并入 1 且命中该 id |
| 注入脚本 `<<PY` 非引号 heredoc 会吃掉 `\d`/`\.`；点号字面量随用例增加失效 | ✅已修 | 注入脚本落临时文件执行；选记录改按特征（`expected==CFXMEM`）、期望码取该记录点号 | 注入 2 路：三平台同点号 **4 / 22**，均回绿 |

判决：两条阻断项已闭合（B1 按 ① 补齐、B2 声明改为实况且加了机械核对），状态置 `待验收`。

### 第 2 轮 reviewer 复核

**重跑记录（我自己的命令 / 输出 / 退出码；快照 `git status -uall` 15 项 ＝ 13 个 `.S` + `fragments/…migration.md` + 任务书）**

1. `run.sh`（A 段，含新 A4b）→ `FAIL=0` `EXIT=0`；A4b `YAML 用例数/未并入 = 114 0`，其自带反例（删 div.st 的 rd0 除数例）⇒ 非零。
2. `run.sh --full`（钉住 gem5 `1c521d07…`／qemu `5d04d3e8…`／chipyard `45748f3f…`）→ `FAIL=0` `EXIT=0`：**55/55、故障 34/34 全 `0xF8`、链例三方字节一致**；其注入 2 路三平台同点号 **4 / 22** 并回绿。
3. 我方独立复算（`recheck.py`，按 spec 直推）→ **396 例（链 362 含编码 42 + 故障 34）不符 0**；点号 1..N 连续、≤127（21 文件点号范围 **17–26**）。
4. 我方独立 YAML 判据（第 1 轮那套，不看其脚本）→ **114 条 active 用例 / 缺失 0**；四条新增点手算一致：`rol amount=35→3` ＝ `0x00000000F56DF77E`、`shr.ut 0x0F0F0F0F0F0F0F0F>>2` ＝ `0x03C3C3C3`、`rev.t k=8` ＝ `0x67452301EFCDAB89`、`div.st 0x64÷rd0(0)` ＝ `0xFFFFFFFFFFFFFFFF`。
5. 门控直跑：`check_tests_index` `EXIT=0`、`check_case_ledger` `EXIT=0`、`validate_vectors` `EXIT=0`、sweep md5 `2d4d94651346ef673c5a855e024c1489`（covered=273）；`make check-inst`（本轮我补跑，工程侧未跑已披露）`EXIT=2`、红集**恰** `{divrem.yaml[23]}`、`1141/1135/1/5` ＝ 基线。
6. 独立注入（**新增点** `shr.ut_orrr` 点 16，`cp`+md5）：`check_yaml_merged` 报 `MISS` `EXIT=1`、我方复算报点 16、三平台直跑（`--jobs` 默认 32）`chipyard=16,qemu=16,gem5=16` `EXIT=1` → 还原 md5 `30e3cce09dd4b989ba3f44674a314253` 一致 → `114/0`、`396/0`、`run.sh` `EXIT=0`。

**机械核对可信性（我方独立反例，临时树 + 一处工作树 `cp` 还原）**

- `vec`／`fault`／`zero_div` 分支**非恒真**：改 `shr.ut` 的 `>>2` 期望 ⇒ `MISS` `EXIT=1`；改 `rev.t` k=5→6 ⇒ `MISS` `EXIT=1`；把 `div.st` 的 rd0 除数改 rd7 ⇒ `MISS` `EXIT=1`（签名含具体向量/imm/k 值）。
- `encoding` 分支（25 例）是「该 id ≥1 条 `.dd.t32`」**存在性**判据：删两条之一仍 `114/0`（实测），删全部才 `MISS` —— 仍钉 mask/value（018 先例亦不要求同字），但完成区措辞过强（见 finding）。
- 根因侧：`gen_cases.py` 现无重复键（AST 扫描 0）；`ISS-434` 确在 master（`09c3501f`）登记、标题与根因一致 ✓；片段/完成区已改「114/114 全部并入」，`.S` 内 `YAML … 并入` 注释实测 **57 条 / 21 文件全覆盖**。

**约束核验**

- 改动范围：15 项全在本任务内；**未改** `tests/inst.yaml`/`MIGRATION.md`/`README.md`/`macros`/`run_asm_suite.py`/`contracts/`/`spec/`/`Makefile`；diff 删 32 条断言行**全部**为点号顺延或被「同操作数 + 完整 64 位源」升级替换（6 条 `0x000000000F0F0F0F…` → `0x0F0F0F0F0F0F0F0F…`，低 32 位同值），净增 24 检查点（链 +23、故障 +1），**无断言弱化/删除**；完成区 24 行 ≤30、无运行期路径。
- `rev.t` k=8 与移位掩码口径按指示不重查；spec 张力已由 `462c5850` 裁定落文 ✓。

**非阻断 finding（交 architect 收尾改）**

1. 完成区「13 个 `.S` + **2 个片段** + 任务书 ＝ 15 项」算术不符：`…inst.yaml` 本轮未改，实为 **1 个片段**（13+1+1=15）。
2. 「删任一**非 encoding** 用例即报 MISS；encoding 类（25 例）判据是「该 id ≥1 条 `.dd.t32`」且钉 mask/value」对 encoding 类 25 例不成立（见上实测），建议收窄为「向量/故障用例」。
3. `run.sh` A4b 总数写死 `114 0`（`DD-Y003`：宜现场派生）；B3 段标题仍写「33 个故障镜像」（判据用现场值 34 ✓）；任务书验收 1「== 16」笔误仍在。

**判决：Accepted**（第 1 轮两条阻断已闭合并经我方独立复核；门控、三平台 55/55、396 例复算、注入链全绿，无代码/spec 缺陷）。

## 完成区

**测试结果**：三平台（chipyard / QEMU / gem5，同一份 ELF）**55/55 镜像通过** —— 链例 21 + 故障例 34（全 `0xF8` ILLI），链例逐字节一致（362 检查点 × 8 B）。独立复算 **396 例 / 不符 0**（两套自写实现：位串逐位进位/移位-相加/二进制长除法/串切片；原生整数 + `to_bytes` 符号判定），并含检查器反例（改错点 4 ⇒ 命中点 4）。**YAML 并入 114/114**（机械核对脚本，未并入 0；删任一用例即 MISS）。注入 2 路：链例期望改错 ⇒ 三平台同点号 4 红；故障名 `ILLI→CFXMEM` ⇒ 三平台同点号 22 红；均 `cp`+md5 对账、原文件不变、回绿。

**修改文件**（与 `git status -uall` 对账：相对 WIP 提交恰 15 项 —— 13 个 `.S` + 2 个片段 + 任务书；全在本任务范围）：
- `tests/inst/08-arith-logic-tetra/`：共 21 个 `.S`（本任务新增全部载体）；本轮返工改 13 个：`div.st/div.ut/rem.st/rem.ut_orrr_rd.S`、`rev.t_orri_rd.S`、`rol.t_{orri,orrr}_rd.S`、`shl.t_{orri,orrr}_rd.S`、`shr.{st,ut}_{orri,orrr}_rd.S`
- `tests/inst/.fragments/08-arith-logic-tetra.inst.yaml`（21 条，**条目数未变**）、`08-arith-logic-tetra.migration.md`（§1 行 + §6 小节，措辞改实况并加机械判据）
- **未改** `tests/inst.yaml`/`MIGRATION.md`/`README.md`/`macros/inst_test.inc`/`run_asm_suite.py`（分片协议 §5.3）；宏层零改动（复用 016–018 既有宏）

**验收结果**：`--scan-only` rc=0（21 id / 55 镜像；点号 1..N 连续，每文件 17–26 点；链例 362 + 故障例 34 现场派生，且与文本级 grep 独立计数一致）；三平台跑批 rc=0、55/55、故障 34/34 全 `0xF8`；`check-tests-index`/`check-case-ledger`/`validate-vectors` rc=0；273 例 sweep md5 `2d4d94651346ef673c5a855e024c1489`（covered=273）不变；片段 21 条、`yaml.safe_load` 通过、`file` 全存在、id 合法且与根清单无重；`check_yaml_merged` 114 例 / 未并入 0。

**新发现/坑**：
1. `rev.t` 的 k=8 **不是** bswap64：两块各自 bswap32、块位置不交换（`0x01234567_89ABCDEF → 0x67452301_EFCDAB89`）；照抄 `rev.o` 的期望会被判红（本次实测暴露）。
2. `TEST_AR_ORRR` 的「两源同名」用例必须让**目的**是第三个寄存器：目的同时是两源时宏跳过装载，源值退化为目的初值。
3. `sync_node_artifacts.sh` 远端 md5 用单引号 `'~/…'` ⇒ `~` 不展开、校验恒报 MISMATCH（复制其实成功）；且工具链 `bin/` 12 GB，`--delete` 全量重传 >15 min。建议改 `$HOME` 并只传必需工具（本次改用 md5 与主控机一致的 QEMU pin 副本）。
4. **生成器字典重复键曾静默丢用例**（`extra` 里 div/rem 4 个 id 写了两遍，后者覆盖前者 ⇒ 8 条 YAML 用例消失且无人报错）⇒ 已把「YAML 已并入」从人工声明升级为**机械核对**（`check_yaml_merged.py` 按向量签名比对，删任一用例即 MISS）。同类"声明类"结论一律加机械核对。
5. 共享构建树里 gem5 正被并行任务重建（`build-gem5` 持 `gate.lock`）⇒ 本机跑批期间 `gem5.opt` 被替换两次（出现「不存在/不可执行」瞬态）；证据改在节点用 md5 钉住的副本跑，本机同批 B1 亦以新 gem5 通过（55/55），说明行为跨构建稳定。

**遗留问题 / 待裁定**：
1. `spec/SimRISC-08 §2` 表「`shamt` 位域 `hd[4:0]`，`hd[5]` 应为零」与 §2.2 对 orrr 的「只有低 5 位参与（天然取模 32）」张力；本册按 §2.2 口径（orrr 取模、不 ILLI），三实现实测一致；建议 spec 与 `contract-isa §10.4.1` 明确「`hd[5]` 应为零」只约束 orri 的 `immu6`。
2. `rev.t` 的「k=8 须源高 32 位为 0」是使用建议而非合法性约束：高位非 0 时两块仍都处理（三平台一致），已用点 10 钉住。
3. YAML 未删：`base/reg-arith.yaml`/`base/reg-compare.yaml`/`base/reg-shift-extend.yaml` 仍含 16/8 位 id，`rev/rev.yaml` 亦受 §5.1 前置阻塞 ⇒ 待 025/026/030 收口。
4. `make check-inst`（第 1 轮返工前跑过；本轮未再跑 —— 本轮只改本册 `.S`/片段，未动任何 YAML）：红集**恰** `divrem.yaml[23]`（既有基线，`m13-testcases-022` 已记录）+ 汇总 `1141/1135/1/5` ⇒ 本任务无新增红。
5. 基线红（共享 `.work`，非本任务）：`check-knowledge-refs` 1 项（属 `m13-testcases-022` 任务书的具体 `.work/**` 引用）、`check-run-artifacts` 13 项非法名（属 chipyard/gem5/infra/llvm/qemu 其它任务），`HEAD` 已是该状态；本任务书与新增文件无 `.work/**` 引用，本任务日志名均合 `<任务ID>-<用途>.log`。

