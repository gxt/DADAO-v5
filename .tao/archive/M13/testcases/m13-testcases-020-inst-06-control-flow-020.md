# m13-testcases-020: `06-control-flow` —— `br.*`/`jump`/`call`/`ret`（含 RAS 溢出/下溢）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（宏层 `inst_test.inc` + `run_asm_suite.py` 已建好）；与其它 `tests/inst` 重构任务**串行**（共享 `tests/inst/`）
**可并行分片**：否
**状态**：已验证

## 背景

延续 `012`/`013` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。分类与用例模板见 `tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移台账）。

本任务覆盖 **15 个 id**（06 控制流 册：`br.*`/`jump`/`call`/`ret`（含 RAS 溢出/下溢））。

## 范围（id 清单，以 `contracts/opcodes.yaml` 为准）

```
br.eq_rrii_rd br.n_riii_rd br.ne_rrii_rd br.nn_riii_rd br.np_riii_rd br.nz_riii_rb br.nz_riii_rd
br.p_riii_rd br.z_riii_rb br.z_riii_rd call_iiii_ra call_rrii_ra jump_iiii_rb jump_rrii_rb
ret_riii_ra
```

## 用例设计（5 类，模板见 `MIGRATION.md §3`）

- **encoding**：该 id 的编码校验（mask/value）
- **legality**：适用的合法性规则（`rd0/rb0`、`immu6=0`、范围/重叠、保留编码…），以 `contracts/legality_rules.yaml` 为准
- **semantic**：正常路径，宽度 × 符号 × 形式
- **boundary**：该族特有边界（进位/借位/最值/次正规/对齐/窗口/掩码…）
- **overlap**：源=目、部分重叠、块复制重叠

## 验收

1. `ls tests/inst/06-control-flow/` 下本任务 id 的 `.S` 齐全（== 15）
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

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 编码例「编码字段 vs 装载寄存器」不一致（首版生成器把 `rdha=1` 的编码字配 `rd5` 初值；条件碰巧成立 ⇒ 跑批看不出） | ✅已修 | 编码例改装载编码字真正引用的 `rd1`/`rb1`；另加 `encode_check.py`（`opc`/`mask`/`value` + 字段↔装载寄存器）并接入证据脚本，注入可达 FAIL | `encode_check` 15/15 一致；注入 `0x6E042002→0x6E102002` ⇒ rc=1「编码字段 rdha = rd4，但此前未装载」⇒ `cp`+md5 还原 |
| `br.nz_riii_rb` 的 CFXMEM 故障例把初值装到 `rb6`、编码字引用 `rb1` ⇒ 条件不成立、退出码 = 点号 13 | ✅已修 | 故障例初值寄存器改 `rb1`（与编码字一致） | 三平台 rc 全 `0xF1`（34/34 镜像） |
| `TEST_FAULT_RASUF_MEM` 用 `rd2ra {ra0}, {rb5}`（跨银行）⇒ 汇编报错 | ✅已修 | 经 `rd5` 中转（`rd2ra` 源必须在 rd 银行） | 装配+跑批通过；D4b 三平台 rc 全 `0xFB` |
| `call_rrii` 的 C2 例未清栈（上一例压入的条目残留 ⇒ `RACNT=2`） | ✅已修 | 该例前加 `rd2ra {ra0}, {rd0}` | 点 11 由红转绿；三平台 14/14 |
| `call_rrii` 的 `.text` 越过 0x1E00 窗口（lds ASSERT） | ✅已修 | 压缩 `.org` 槽位间距（落点 0x940/0xB80/0xE40） | 14 链例点 + 2 故障例、34/34 镜像 |
| 头部「用例：…」分类计数与现场分段统计不符（3 个文件） | ✅已修 | 逐文件对齐声明；证据脚本加「分类计数现场统计」项 | 15/15 一致（`--inject` 全套 CHECK=84 FAIL=0） |
| 自写 oracle 首版把 RAS 压/弹的有效区位移方向搞反（与三平台相反）；C3b 满栈搬移还把 `ra0`（RACNT/MRPTR 寄存器）当成条目 | ✅已修（**改 oracle 不改用例**） | 按 `spec/SimRISC-00 §2.4.1/§2.4.2` 重写 `push`/`pop`（压栈下移、弹栈上移；满栈时搬移范围 `ra2..ra63`、`ra0` 不参与） | oracle 15/15 全一致（203 点）；字节流与三平台逐字节相同（15×3） |
| `run.sh` 的 id 清单用 shell `sort`（locale 忽略标点）≠ Python 字节序 ⇒ 假 FAIL | ✅已修 | `LC_ALL=C sort` | 三源 id 清单一致（15/15） |
| `oracle --byte-out` 初版写成单文件（后一文件覆盖前一） | ✅已修 | 改按 `<id>.bin` 落盘 | 15 个 bin 与三平台 `.out` 逐字节相同 |

判决：无未修 finding。

### 第 1 轮 reviewer 验收

**id 数（现场三源 + 任务书，不用 `ha` 筛族）**：`contracts/opcodes.yaml` 按 `spec_cite` 前缀 `SimRISC-06:` = **15**；`spec/SimRISC-06` 附录 A = **15**；`tests/inst/06-control-flow/*.S` = **15**；任务书 §范围 = **15** —— 四集合**逐名相等**（对称差 = `∅`）。

**重跑记录（命令 + 本人取的退出码/真实输出）**：
1. 节点 `python3 tools/testcases/inst/run_asm_suite.py --vectors tests/inst/06-control-flow --lds tests/inst/01-load-store/inst-tiny.lds --jobs 8` → **rc=0**，`34/34 镜像通过（15 个 id；链例 15，故障例 19）`；链例点数 `12/13/12/13/12/12/12/12/12/12/18/14/6/6/18` = **184**、三平台字节相同；19 故障例三平台 rc **全同**：UNDI `249`×2、CFXMEM `241`×11、ILLI `248`×2、RASOF `250`×2、RASUF `251`×2（与 `spec/Machine-v5 §7.1` `0xF0|位索引` 逐项对上）。
2. 主控机 `PLATFORMS=qemu <运行期证据目录>/run.sh` → **rc=0，`CHECK=45 FAIL=0`**（id 三源 15=15、点号 15/15 连续≤127、分类计数 15/15、`oracle` 203/203、`encode_check` 15/15、34 镜像、门控 5 项、273 md5 `2d4d94651346ef673c5a855e024c1489` covered=273）。
3. 节点 `run.sh --inject` → **rc=0，`CHECK=88 FAIL=0`**；节点 `run.sh --skip-gates --inject` → **rc=0，`CHECK=84 FAIL=0`**；三路注入均真 FAIL（`br.eq` 点10、`call_iiii` 点5、编码字）后 `cp`+md5 还原回绿（md5 `75fb396c…` 相等）。
4. 门控直跑：`check-tests-index` rc=0（**341** 条）｜`check-case-ledger` rc=0（**2170**）｜`validate_vectors` rc=0（156/156、723 例、**gaps 0**）｜`check-generator-sync` rc=0｜`check-dirs`/`check-tasks`/`check-knowledge-refs` rc=0｜`make check-modules`(L2) rc=0｜`make check-inst` **rc=2**，`1141/1135 passed/1 failed/5 deferred`，红集**恰** `{divrem.yaml[23]}`（已知基线）；节点 `make check-inst` rc=0（`1136 passed/0 failed`、Tiny 44/44）。`check-milestones-fresh` rc=2 = `m14-llvm-002`/`m14-qemu-001`（他任务，基线不判）。
5. **独立复算（reviewer 自写解释器，未读未用其 `oracle.py`）**：按 `SimRISC-06 §1–4` + `SimRISC-00 §2.4.1/§2.4.2` 自行实现（宏展开计址 + RAS C1/C2/C3a/C3b、D1–D4b、`rb0`=当前 IP、字节位移）→ **15 个 id 全量 184 链例点**，逐点「复算值 == 内联期望 == 三平台 45 个 `.out` 字节流」，`RC=0`；抽样：`call` 点5 `0x0001ffffff010904`（计数1 + call+4）、点17 `0x003fffffff014078`（RACNT=63、MRPTR=MEMRAS+0x78）、点18 旧顶落 MemRAS；`ret` 点4/5（D3 上移）、点15/16（D4b 条目压栈、MRPTR+8）、点18（计数1 消费）；`br.nz_rb` 点10–12 落点 `0x1600/0xA00/0x1A00`。
6. **独立注入 1 路（自设计，临时副本）**：`br.n_riii_rd.S` 点11 落点期望 `ENTRY+0x1600 → 0x1604`（md5 `bfdb25e6… → b769805b…`）→ 三平台 rc **全 11**、`SUITE_RC=1`；`cp` 还原 md5 相等 → 回绿 `SUITE_RC=0`、三平台 rc=0/104 B。
7. **4 个 ctrl YAML 未 `git rm` 理由成立**（临时树 `mv` 走逐门控实测）：`validate_vectors` rc=1 **44 gap**、`check_case_ledger` rc=1 **多 67 行**、`check_tests_index` rc=1 **4 项 `file` 缺失**、`check-generator-sync` rc=2（渲染目标缺失）；真工作树 4 个 YAML md5 未变、`MIGRATION §5.2` 已记录并留 `m13-testcases-030`；`.S` 与 YAML 无重复计数（`case-ledger` 中 `06-control-flow` **0 行**）⇒ 未删不构成假绿。

**约束核验**：① 只在任务 worktree 作业，主工作树 `git status` **0 行**、`master` 未动；② 未提交 git（HEAD 仍 `66413d4c`，`WIP:` 前缀）；③ 改动 **21 项** = 完成区声明 21（15 `.S` + `inst_test.inc` + `run_asm_suite.py` + `inst.yaml` +15 条 + `MIGRATION` + `README` + 任务书），**未触 `contracts/`/`spec/`/`Makefile`**，`diff` 仅增故障名/宏识别与 `TEST_BR*` 链例行，无弱化断言；④ 完成区 **15 行**（≤30）、审阅记录 **33 行**（≤40）、任务书无运行期路径；⑤ 快照对账：18 个目标文件 md5 与注入前**全等**、`git status -uall` 0 行；⑥ 未重建组件，临时产物只落任务临时目录（审查后清理），仓库内无残留。

**发现（文档级，按 §6.5 记 finding、不开返工轮，交 architect 收尾改）**：F1 完成区「节点 `run.sh --inject`（三平台）CHECK=84」——按字面命令实测 **88**，84 需加 `--skip-gates`（两种我都跑了）；F2 `MIGRATION §6/020`「（194 点）」与实际 **203**（184 链例复算 + 19 故障码核对）不符（`tools/`/`Makefile` 无引用，非门控值）；F3 `run.sh` 把 19 个故障码核对并入「复算检查点 203/203」，宜分列「链例复算 184 + 故障码核对 19」。

**判决：Accepted** —— 验收 1–7 与全部硬约束在我本人的重跑下通过；F1–F3 为文档级小错，按规则记 finding 由 architect 收尾修正，不构成返工。

## 完成区

**测试结果**：三平台 **34/34** 镜像通过（15 id；链例 15 + 故障例 19）——链例三平台字节流相同且 == 独立复算字节流（15×3 逐字节），故障例三平台退出码全同（`0xF1` CFXMEM / `0xF8` ILLI / `0xF9` UNDI / `0xFA` RASOF / `0xFB` RASUF）；节点一键证据 `run.sh --inject`（三平台）**CHECK=84 FAIL=0 / RESULT=PASS**；主控机 `run.sh`（qemu + 门控）**CHECK=45 FAIL=0**。
**id 数**：现场三源一致 = **15**（`contracts/opcodes.yaml` 的 `spec_cite` 归属 + `spec/SimRISC-06` 附录 A + 任务书 §范围 + 目录 `.S`）。
**点数**：链例 184 点 + 故障例 19 点 = **203 点**（逐文件 12/13/12/13/12/12/12/12/12/12/18/14/6/6/18 + 故障 1×10、1、2、1、1、4；全部 1..N 连续、≤127）；`oracle` 独立复算 **203/203 一致**。
**修改文件**：`git status --porcelain -uall` **21** 项 —— 新 15 个 `tests/inst/06-control-flow/<id>.S`；改 `tests/inst/macros/inst_test.inc`（控制流宏 + `UNDI/RASOF/RASUF` 故障名 + `MEMRAS`）、`tools/testcases/inst/run_asm_suite.py`（`FAULT_CODE` 三类 + 6 个故障行识别 + 链例行 `TEST_BR*`）、`tests/inst.yaml`（+15 条 `inst-06-control-flow-001..015`）、`tests/inst/MIGRATION.md`（§1 标注 + §5 四行 + §5.2 删除阻塞 + §6/020）、`tests/inst/README.md`（06 册行 + 跑法）、本任务书。
**验收结果**：
1. 15 个 `.S` 逐名齐全；点号连续、头部分类计数 == 现场统计（15/15）
2. 编码对账：`encode_check` 15/15（`opc`/`mask`/`value` + 编码字段↔装载寄存器）；`oracle` 203/203（独立解释器逐点比内联期望）
3. `check-tests-index` rc=0（**341** 条）｜`check-case-ledger` rc=0（2170）｜`validate_vectors` rc=0（gaps 0，723 例 / 156 id）｜273 例 sweep md5 `2d4d94651346ef673c5a855e024c1489` 不变（covered=273）｜`check-dirs`/`check-no-residue`/`check-generator-sync`/`check-tasks`/`check-knowledge-refs` rc=0｜`make check-modules`（L2）rc=0，含 `check-inst-smoke`/`check-unit`/`check-arch-smoke` 全 PASS
4. `make check-inst`（主控机）rc=2：`1141 total / 1135 passed / 1 failed / 5 deferred`，红集**恰** `{divrem.yaml[23]}`（既有 pin，归 `m13-testcases-032`；vast 段先红 ⇒ Tiny 子集未跑到，属基线行为）。节点侧同命令（节点 QEMU 较新）**0 红** + Tiny 44/44。
5. 可达 FAIL（三路，均 `cp`+md5 还原并回绿）：`br.eq` 点 10 落点期望 `0x1400→0x1404` ⇒ 三平台 rc 全 **10**；`call_iiii` 点 5 返回地址期望 `+0x804→+0x808` ⇒ 三平台 rc 全 **5**；编码字 `0x6E042002→0x6E102002` ⇒ `encode_check` rc=1（注入后 md5 均变化、还原后逐一相等）
6. YAML：4 个 ctrl 册（`ctrl-br` 9 id/40 例、`ctrl-jump` 2/6、`ctrl-call` 2/11、`ctrl-ret` 1/10）的 id **全部**有 `.S` 载体；**未 `git rm`** —— 实测删除被四条门控阻塞（`validate_vectors` 44 gap / `check_case_ledger` 多 67 行 / `check_tests_index` 4 条 `file` 缺失 / `check-generator-sync` 缺渲染目标），见 `MIGRATION §5.2`，留 `m13-testcases-030`
**新发现/坑**：① `rb0` 的读出恒为**当前指令地址**（`aip.si` 口径），故「跳转落点地址」的实测必须用第一指令 `aip.si rb24,0` 捕获（在分支/跳转之后再用 `st.o rb0` 读到的是该 `st.o` 自身的地址）；② `rd2ra` 的源**必须**是 rd 银行（把地址装进 rb 再 `rd2ra {ra0}` 会汇编报错）；③ RAS 架构视图 = 有效区 `ra[64-RACNT..63]`、`ra63` 恒为栈顶 ⇒ 压栈整段**下移**、弹栈整段**上移**（自写 oracle 首版反了，与三平台对撞后按 spec 改正）；④ `br.rrii` 的 imms12 只有 ±8 KiB，够不到 Tiny 8 MiB SRAM 边界 ⇒ 越界目标只能落在 SRAM 内零字（UNDI），CFXMEM 要靠 riii/jump/call；⑤ 三平台对 `UNDI`（零字取指）、`RASOF`、`RASUF`（含 D4b MemRAS 条目）与 `call+4` 返回地址**完全一致**（无 ISS 级分歧）；⑥ 证据脚本比较 id 清单时必须 `LC_ALL=C sort`（shell locale 排序忽略标点，与 Python 字节序不同）。
**遗留问题**：① 4 个 ctrl YAML 未删（§5.2 四条阻塞）→ `m13-testcases-030`；② `make check-inst` 既有红 `divrem.yaml[23]` → `m13-testcases-032`（节点侧已无此红）；③ `make check-milestones-fresh` rc=2 属**他任务**（`m14-qemu-001` 有 worktree 但台账在「待开始」），非本任务范围；④ `ISS-410` 的 hmon 自装 workaround 沿用。
