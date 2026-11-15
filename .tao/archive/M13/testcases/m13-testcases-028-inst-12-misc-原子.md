# m13-testcases-028: `12-misc` 原子 —— `lr.*`/`sc.*`（24 个 id）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（宏层 `inst_test.inc` + `run_asm_suite.py` 已建好）；与其它 `tests/inst` 重构任务**串行**（共享 `tests/inst/`）
**可并行分片**：否
**状态**：已验证

## 背景

延续 `012`/`013` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。分类与用例模板见 `tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移台账）。

本任务覆盖 **24 个 id**（`12-misc` 原子（lr/sc 24 形态））

## 范围（id 清单，以 `contracts/opcodes.yaml` 为准）

```
lr.b.an_orrr_rd lr.b.ar_orrr_rd lr.b.nn_orrr_rd lr.o.an_orrr_rd lr.o.ar_orrr_rd lr.o.nn_orrr_rd
lr.t.an_orrr_rd lr.t.ar_orrr_rd lr.t.nn_orrr_rd lr.w.an_orrr_rd lr.w.ar_orrr_rd lr.w.nn_orrr_rd
sc.b.ar_orrr_rd sc.b.nn_orrr_rd sc.b.nr_orrr_rd sc.o.ar_orrr_rd sc.o.nn_orrr_rd sc.o.nr_orrr_rd
sc.t.ar_orrr_rd sc.t.nn_orrr_rd sc.t.nr_orrr_rd sc.w.ar_orrr_rd sc.w.nn_orrr_rd sc.w.nr_orrr_rd
```

## 用例设计（5 类，模板见 `MIGRATION.md §3`）

- **encoding**：该 id 的编码校验（mask/value）
- **legality**：适用的合法性规则（`rd0/rb0`、`immu6=0`、范围/重叠、保留编码…），以 `contracts/legality_rules.yaml` 为准
- **semantic**：正常路径，宽度 × 符号 × 形式
- **boundary**：该族特有边界（进位/借位/最值/次正规/对齐/窗口/掩码…）
- **overlap**：源=目、部分重叠、块复制重叠

## 验收

1. `ls tests/inst/12-misc/` 下本任务 id 的 `.S` 齐全（== 24）
2. 每文件检查点 ≤127、点号连续；失败点号 = 用例序号（链例 + 故障例续号）
3. **三方逐字节**（chipyard == QEMU == gem5 同镜像），含全部故障例
4. `make check-inst` 红集不扩大（现恰为既有 pin `{divrem.yaml[23]}`）；`check-tests-index` rc=0；273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变
5. YAML 迁移：`atomics/atomics-lrsc.yaml`/`sc-rd0.yaml` 里属于本任务 id 的用例已有 `.S` 载体；
   **文件未删**（§5.1 前置 + 根清单 `file:` 条目），片段里写明（`MIGRATION.md §5.3`）
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

### 第 1 轮 engineer 自审（2026-11-14）

审查范围：24 个 `.S`（头注 / 用例段 / 期望 / 故障段 / 点号逐文件核，另由独立复算全量重放）、
生成器与独立复算脚本、证据脚本四件、两个片段文件；`git status -uall` 仅本任务新增。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 派单口径与 spec 冲突：称「sc 失败返回 0、成功返回 1」、保留粒度称「自然对齐 8 字节字」 | ✅已修 | 按 `spec/SimRISC-12 §1`/`contract-isa §14.2`/ADR-0034 D6：成功 `rdHB=0`、失败 `1`；粒度按「精确地址+宽度」写注释，分歧路径不写断言 | 三平台 66/66；`sc` 成功点实测 0、无标记点实测 1 |
| F2 `sc` 文件的 setup `lr` 误用本 id 助记符（3 操作数） | ✅已修 | 生成器按族选配对助记符（`lr.<w>.nn` / `sc.<w>.nn`） | 首轮 `llvm-mc: invalid operand for instruction`；修复后 24 文件全汇编 |
| F3 故障例地址实参含空格 ⇒ `run_asm_suite` 的故障例正则静默漏收（首轮只 1 个镜像） | ✅已修 | 地址改用 `.equ` 单 token（`A0`/`LMAL`），复用 `TEST_FAULT_CF1` | 首轮「1 个镜像」→ 修复后 66 镜像（24 链 + 42 故障） |
| F4 MALIGN 示例地址初版固定 `0x7F4`，对 `.w`/`.t` 是对齐地址（不会触发 MALIGN） | ✅已修 | `LMAL = 0x7F0 + w/2`，生成时断言 `LMAL % w != 0` | 18 个 `.w/.t/.o` 文件的 MALIGN 故障例三方均 `0xFC` |
| F5 encoding 类初版只按助记符执行，缺「规范编码字直执行」的 mask/value 校验 | ✅已修 | 每文件补 1 例 `.dd.t32`（word = value + hc=rd2 + rb=rb3；sc 另置 hb=rd5） | 独立复算按 `opcodes.yaml` 的 opc/ha 重拼编码并仿真；三平台通过（链点 384→408） |
| F6 证据脚本与片段初版把覆盖计数写死（384/66、15–17 链例） | ✅已修 | 链点数/镜像总数改为现场派生（`grep __CHECK_RD`/`TEST_FAULT_CF1`）；片段改写 408/16–18 | `run.sh points`：`n_chk=408 == points.tsv`；`run3`：`24+42=66` 现场相等 |
| F7 任务书标题/背景/验收 1、5 是 `11-cfx`/29 的残留（与 §范围 的 24 个 lr/sc id 不一致） | ✅已修 | 标题与验收 1/5 改为 12-misc/lr-sc/24（不改验收判据本身） | 本文件 §范围 与派单口径一致；完成区披露 |

未修 finding：无。任务状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-14，HEAD `7983789f`）

**重跑记录（本人执行，非采信完成区）**
- `run.sh points` ⇒ `evidence: PASS` **rc=0**：`.S`=24、`oracle_check` 408 条 0 不符、点号连续、片段 PASS。
- `run.sh gates` ⇒ **rc=0**：`check-tests-index` 0／`check-case-ledger` 0／`validate-vectors` 0(gaps 0)／`check-generator-sync` 0／sweep md5 `2d4d9465…` 且 covered=273==list／`check-inst` 红集**恰** `divrem.yaml[23]`。
- `run.sh run3` ⇒ **rc=0**：`66/66 镜像通过（24 id；链例 24 + 故障例 42）`、`verify_bytes: 24 文件 / 408 记录 / PASS`；42 故障例 = **24×`0xF8` + 18×`0xFC`**，三平台 rc 全同；节点 gem5 `bc1b1b5f…` 跑批前后不变（本机 `1c521d07…` 被 `m16-gem5-008` 重建 ⇒ 按派单用节点侧）。
- **独立复算（自写 `review_oracle.py`，bytearray 大端模型 + 位域从 `opcodes.yaml fields` 现场解析）** ⇒ `24 文件 / 408 断言 / 0 错` rc=0；另 **6 id 手工推导 12 项**（大端窗口/零扩展/sc 合并与不写）与内联期望全等。
- **独立注入（锚点 `lr.w.nn` pt11，与 engineer 不同）**：基线 rc=0 → 注入 md5 `e9a222af…` → `2/3 镜像`、`rc {'chipyard':11,'qemu':11,'gem5':11}` → `cp` 还原 md5 `6c559883…`==注入前、节点同 → **回绿 3/3 rc=0**，脚本 EXIT=0。

**约束核验**：§范围 == `opcodes.yaml` lr/sc 24 == `ls *.S` 24（集合三方相等）；点号 1..N 连续 ≤127（408 链 + 42 故障）；`git diff 2d41e98d..7983789f` 仅 24 `.S` + 2 片段 + 本任务书（根清单/宏层/驱动器/`spec`/`contracts`/`Makefile` **零改动**）；`12-misc` 内**无** `swym`/`ct*` 文件 ⇒ 029 未被碰；片段 24 条可解析、`file` 全存在、id 唯一升序、与根清单零交集、§1/§5/§6 锚点在；`git status -uall` 干净；完成区 11 行 ≤30；`atomics-{lrsc,sc-rd0}.yaml` 未删且其 24 个 mnemonic 全有 `.S`。

**`sc` 返回值方向（独立结论）**：`spec/SimRISC-12 §1` 正文「设置成 **0**，表示写入成功／设置成 **1**，表示写入失败」+ 引注「标记仍在时写入内存并**返回 0**，否则不写入并**返回非 0**」；`contract-isa §14.2`、`ADR-0034 D6` 同口径 ⇒ **成功=0、失败=1**。**派单口径「成功1/失败0」是写反的，engineer 按 spec 执行正确**；408 项复算与三平台实测（成功点=0、失败点=1）一致。

**粒度分歧（本人独立探针 `probe_gran.S`，三平台同 ELF）**：`rc {'chipyard': 2, 'qemu': 1, 'gem5': 0}`（gem5 24 B=3 点全过）⇒ ① 点1「同字异址 `sc.b`」**QEMU 红**＝字粒度（判成功，与 spec 相反），chipyard/gem5 与 spec 一致；② 点2「同 hart 改同字另一字节」**chipyard 红**＝整字值比较（spec 未列此清除事件），gem5 通过；③ 三平台**互不一致**、且 QEMU 与 spec 字面不符。**判断：应登记 `issues.yaml`，不能只留任务书 GAP**（处置二选一：改实现对齐 spec，或改 spec 允许字值失效/spurious）。

**发现（不阻断本任务，architect 收尾处置）**：F1 片段 §6 GAP-3 把「同字异址 `sc` 成功」同时归给 chipyard/QEMU，实测该轴 chipyard 与 spec 一致 ⇒ 合并 `MIGRATION.md` 前把归属写准；F2 `verify_bytes.py` docstring 仍写「384 链点」（现场 408，文档级）；F3 验收 4 写 `check-inst rc=0` 实测 rc=2（既有 pin，同 031/035），建议模板改为「红集不扩大」。

**判决：Accepted** —— 7 条验收在本人重跑下全部通过、约束无违反；**但单列阻断项（上条粒度分歧须立 issue）供 architect 定夺，不随本判决放行。**

## 完成区

**测试结果**：三平台 `run_asm_suite` 24 id / **66 镜像 66/66**（链例 24 + 故障例 42，chipyard==QEMU==gem5 rc 全同）；结果缓冲 **408 链点 × 3 平台逐字节一致**且 == 独立复算（408/408、0 不符）；注入 2 路各三平台同点红（`lr.o.nn` pt6 / `sc.o.nn` pt3）、`cp`+md5 还原回绿；门控 9 项全绿（`check-inst` rc=2，红集恰既有 pin `divrem.yaml[23]`）。证据脚本 `run.sh {points,run3,inject,gates}` rc=0。
**修改文件**：新增 `tests/inst/12-misc/{lr,sc}.{b,w,t,o}.{nn,an,ar|nn,nr,ar}_orrr_rd.S` 共 24 个（`ls tests/inst/12-misc/*.S | wc -l` = 24）；新增 `tests/inst/.fragments/m13-testcases-028.{inst.yaml,migration.md}`（24 条 + §1/§5/§6 片段）；改本任务书（标题/验收 1、5 的 027 残留更正 + 审阅记录 + 完成区 + 状态）。`git status -uall` 仅上述新增与任务书。
**验收结果**：
- `.S` 数 24 == `contracts/opcodes.yaml` 的 lr/sc id 数 24；每 id 16–18 链例 + 1–2 故障例，点号 1..N 连续、≤127（现场：链点 408、故障 42）。
- 三方逐字节：66/66 镜像；408 个「平台×点」记录三平台完全相同且 == 独立复算；故障例 ILLI `0xF8` / MALIGN `0xFC` 三方同值。
- 独立复算（模型 B：字节数组内存 + 直接解析 `.S` 仿真 `lr/sc/st.o/LOAD_ADDR/__LI`；编码按 `opcodes.yaml` opc/ha 重拼）：408/408 PASS。
- 注入：`lr.o.nn` pt6 期望 `…CDEF→…CDEE`、`sc.o.nn` pt3 结果 `0→1` ⇒ 三平台均 rc=6/3（套件 rc=1）；还原后 md5 本地==节点、套件回绿。
- 273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变（covered 273 == list 273）；`check-tests-index`/`check-case-ledger`/`validate-vectors`（gaps 0）/`check-generator-sync` rc=0。
- 产物 md5：qemu `5d04d3e8…`、chipyard `45748f3f…`（本机==节点）；gem5 本机侧正被他会话重建（读不稳定）⇒ 以节点侧 `bc1b1b5f…` 为准，跑批前后不变。
**新发现/坑**：① 派单口径与 `spec/SimRISC-12 §1`/`contract-isa §14.2` 冲突（`sc` 成败返回值方向、保留粒度）⇒ 以 spec 为准；粒度实测 chipyard/QEMU = 8 B 字值比较、gem5 B6 = 精确地址+宽度 ⇒ 只能 GAP。② `run_asm_suite` 故障例靠行首 `TEST_FAULT_*` 正则扫描，宏实参含空格会静默漏收 ⇒ 地址实参用 `.equ` 单 token。③ 共享构建区的 `gem5.opt` 可被并发会话重建（读不稳定/不可执行）⇒ 产物 md5 以节点侧跑批前后不变为准。④ 多 hart / 异常进入 / 存储序强度 / 偶发失败在单 hart 链例不可构造（GAP 已钉，不伪造）。
**遗留问题**：GAP 5 项（多 hart 同址写清标记、异常/中断进入清标记、保留粒度平台分歧、存储序强度、spurious failure）需多 hart/异常返回载体或先统一 spec 口径；`atomics/atomics-lrsc.yaml`/`sc-rd0.yaml` 未删（§5.1 前置 + 根清单 `file:` 条目，与 `m13-testcases-030` 同批）。无未修 finding。
