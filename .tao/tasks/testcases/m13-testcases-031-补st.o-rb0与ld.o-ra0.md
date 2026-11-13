# m13-testcases-031: 补 `st.o rb0`（指令地址作源）与 `ld.o ra0`（RAS 窗口读写）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（`01-load-store` 单元素套件已建）
**可并行分片**：否（共享 `tests/inst/01-load-store/`）
**状态**：已验证

## 背景（`ISS-411` ②③）

`012` 的两条覆盖面缺口：

1. **`st.o rb0`**：`rb0` 读出的是**当前正在执行的这条指令的地址**（`SimRISC-00`），`012` 的宏层无法构造这个期望值，故未覆盖。
2. **`ld.o ra0`**：`ra0` 是 `{SBZ(10), RACNT(6), MRPTR(48)}` 的窗口，`012` 未覆盖读写。

## 用户裁定（2026-11-13，含补充修正）

1. **`st.o rb0` 取「当前指令地址」的期望值**：
   - 方式一：`aip.si rbX, 0`（`imms30 = 0` 合法）⇒ `rbX` = 该 `aip.si` 自身的 IP；再 `add.si rbX, rbX, delta` 得到被测指令地址
   - 方式二：`rb2rb rbX, rb0, 1`（或 `rb2rd rdX, rb0, 1`）直接拷出当前 IP，再求 `delta`
   - `delta` = 被测指令与该取址指令之间的字节差（相邻时即 4）
2. **`ld.o ra0` 读写都测**；**写时 `[63:54]` 的 SBZ 10 位忽略**（`SimRISC-00` 已规定「写无效」）。
   - 注意操作数位置：`ld.o_rrii_ra` 的 **`ra0` 是目的寄存器（第一个操作数）**，即 `ld.o ra0, rbX, imm`
   - **读** `ra0` 需用复制类指令（`ra2rd rdY, ra0, 1`），不是 `ld.o`

## 范围

在 `tests/inst/01-load-store/` 补测（**不改已通过用例**）：

- `st.o_rrii_rb` / `st.o_rrii_rd`：新增 `rb0` 作源用例 ≥2
  - 期望值按上文方式一或方式二构造；`delta` 在注释里写清怎么算
- `ld.o_rrii_ra`（及 `ld.o_rrii_rb` 的 ra 形式如存在）：新增
  - **写**：`ld.o ra0, rbX, imm` 写入含 SBZ 置位的值 ⇒ 读回验证 `[63:54]` 保持 0、`[53:48]`/`[47:0]` 生效
  - **读**：先用 `call`/`ret` 构造已知 `RACNT`/`MRPTR`，再用 `ra2rd rdY, ra0, 1` 拷到 RD 后校验两字段
  - 每组 ≥3 例

## 验收

1. 新增用例数按现场统计；每文件检查点仍 ≤127、点号连续
2. **三方逐字节**（chipyard == QEMU == gem5 同镜像）；**若某平台 `ra0` 写语义不一致 ⇒ 如实记红**，登记 issue 回报，不得放宽期望
3. `make check-inst` rc=0；273 例 md5 不变
4. 可达 FAIL 注入（改一条期望 ⇒ 对应点号退出）
5. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- `aip.si` 的 `imms30` 必须是 **4096 的整数倍**；精确差用 `add.si`（`imms18`，字节为单位）。
- 沿用 `012` 的 hmon 自装 workaround（`ISS-410` 未修前）。
- `.work` 软链（`ISS-389`）；改动只在任务 worktree 内（`AGENTS.md` 硬约束 14）。

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

逐行审三个 `.S` 的新增段、`inst_test.inc` 新宏、驱动器正则与证据脚本（`oracle.py` / `run.sh`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `ld.o ra0` 写例 1 的源常量手算错（`0xFFFF3F00…` 的低 48 位是 `0x3F0000000000` 而非 0）⇒ 期望本身错、chipyard 也红 | ✅已修 | 三例源值改 `0xFFFF00…` / `0xFFC0000000000000+0x1234568` / `0xFFEAA5A55A5A1230`，期望由掩码派生并逐项注释 | chipyard 链例 rc=0；读回 22 点与 oracle、手算逐点一致 |
| F2 `__CHECK_MEM_RB` 名字带 `_RB` 后缀，驱动器 `__CHECK_MEM\b` 匹配不到 ⇒ 少计检查点（字节流长度与点数错位） | ✅已修 | `CHAIN_CASE_RE`/`CHAIN_PT_RE` 改 `__CHECK_(?:RD\|MEM)\w*` | `--scan-only` 三文件 17/16/22 与 `__REC` 次数一致；02/06 等册计数不变（58/34） |
| F3 `st.o_rrii_rd` 的 rb0 作基址会把 8 B 写进 `.text`（潜在执行/越界风险） | ✅已修 | 目标槽由 `.org` 留出、被 `jump` 跳过（只写不执行）、每例独立 8 B；EA 与 `st.o` 地址都钉成链接期常量 | 三平台链例 rc=0；oracle 用反汇编核算 `st.o` 地址 + imms = 声明槽 |
| F4 `oracle.py` 在 rsync 副本上取不到宏层 `.equ`（`parents[3]` 指到家目录仓库） | ✅已修 | REPO 优先取 cwd（被测树），再回落 `__file__` | 节点上三文件 `oracle.py` rc=0（此前 rc=1，现场保留在证据日志） |
| F5 证据脚本的头部分类审计把全册 38 个文件都纳入（他任务书头格式不同）⇒ 假红 | ✅已修 | 审计收窄到本任务 3 个文件；`legality` 口径 = 链例 legality 段 + 故障例（既有册约定） | 三文件「头部分类计数全部一致」 |
| F6 `ld.o ra0` 写段若放在读段之前，QEMU/gem5 会在点 16 就红、读段（16–19）永远跑不到 | ✅已修 | 段顺序改为**先读后写**（写段是分歧点，放最后） | 节点三平台：读段 4 点全绿、QEMU/gem5 恰在点 20 红 |

未修 finding：无。上述 6 条均已有复验证据；任务状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-14）

**判决：Accepted**（代码行为 / 门控退出码 / 断言计数 / 语义 四类阻断面均无违反；F1–F3 为非阻断 finding，交 architect 收尾）。

**重跑记录（全部 reviewer 自己执行，未采信完成区转述）**

- `run_asm_suite.py --scan-only` rc=0：38 id / **235** 镜像；`rb 17+2`、`rd 16+4`、`ra 22+2`，点号 1..N 连续且 ≤127；新增链例点 **7+3+1 = 11**（现场派生）。
- **节点三平台全量**（server207 + server208；staging 树 8 文件 md5 == 本 worktree，节点仓 `git status` 干净）：两台均 `234/235`、链例 37/38、**故障例 197/197**；唯一坏记录 `ld.o_rrii_ra chain: chipyard=0,qemu=20,gem5=20`；两台 705 个字节流 `cmp` 全同。
- **独立复算**（自写 `review/recheck.py`：llvm-objdump 取址 + `spec §2.4` RAS 状态机 + SBZ 掩码，**不读** `oracle.py`）：两台各 `PASS=43 FAIL=0 SKIP=2`（SKIP 仅限文档化红镜像的空字节流，且已断言「空字节流恰 = ld.o_rrii_ra 的 qemu/gem5」）。
- 门控：`check-inst` **rc=2**、红集**恰** `FAIL divrem.yaml[23]`（`1141 total / 1135 passed / 1 failed / 5 deferred`）；`check-tests-index` rc=0(341)、`check-case-ledger` rc=0(2170)、`validate_vectors` rc=0(gaps 0, 723 例/156 id)、`check-generator-sync` rc=0、`inst_sweep emit` md5 `2d4d94651346ef673c5a855e024c1489` covered=273、`check-tasks/dirs/temp-dirs/knowledge-dir/contracts-dir/no-residue` rc=0。
- **证据脚本重跑**：`run.sh --skip-suite` rc=0 `CHECK=15 FAIL=0`；`PLATFORMS=qemu run.sh --inject` rc=0 `CHECK=39 FAIL=0 RESULT=PASS`（3 路「注入→FAIL→`cp`+md5→回绿」全过）。
- **独立注入（自设计，非脚本自带的 3 路）**：节点 staging 上改方式一 `add.si rb12, 8→4`（`grep -c` 锚点=1）⇒ `INJ_RCS=chipyard=15,qemu=15,gem5=15`、`INJ_SUITE_RC=1`；`cp` 还原后 md5 `8d383082…` 相等 ⇒ `GREEN_RCS=0/0/0`、`GREEN_SUITE_RC=0`（两台各一轮）。

**约束核验（逐条）**

1. 既有链例行**零改动**（3 个 `.S` 删除行仅 = 头部注释 2 行 + 故障例点号顺延）；`inst_test.inc` **13/0 纯追加**（唯一新宏 `__CHECK_MEM_RB`）；`inst-tiny.lds` **无 diff**；`MIGRATION.md` **30/0、只加 1 个 `###`**；`run_asm_suite.py` **2/2 仅正则**放宽为 `__CHECK_(?:RD|MEM)\w*`（全仓仅 3 个 `__CHECK_*` 宏，其它册 scan 点号仍连续 ⇒ 无副作用）。
2. **`delta=8` 独立核实**（reviewer 自己 `llvm-objdump -d`）：方式一 `aip.si@…0990 → add.si+8 → st.o@…0998`；方式二 `rb2rb@…0a04 → add.si+8 → st.o@…0a0c`；方式三 `.org` 后 `st.o@…11900 == ENTRY+0x1800`。三路地址互异，方式三期望取 `machine-tiny.inc` 的 `.equ ENTRY` **链接期绝对常量**（非 IP 派生）⇒ 确能独立打破「两条 IP 通路同错也自洽」。
3. **`ld.o ra0` 读写**：写 3 例 chipyard 读回 `0x003F000000000000 / 0x0000000001234568 / 0x002AA5A55A5A1230` = 源值 & `0x003FFFFFFFFFFFFF`（与独立掩码复算逐个相等）；读 4 例 `0x0001000000000000 / 0x0002000000000000 / 0x003FFFFFFF014078 / 0x0000FFFFFF014080`（MEMRAS = ENTRY+0x3F00 = `0xffffff014000`）与 C1/C3a/C3b/D4b 推演一致。
4. **点 20 的红 = 平台缺陷，非期望错**：`spec/SimRISC-00 §2.4` 明写 `ra0 = {SBZ(10), RACNT(6), MRPTR(48)}`、`[63:54] = SBZ（写无效）`；源码实证 —— chipyard `WumingRegFile.writeRa` 对 idx0 只写 racnt/mrptr（丢 SBZ），QEMU `helper_ra_store` 直接 `env->ra[phys]=val`、gem5 `writeReg→writeInt(Bank::Ra,…)` **均无掩码**（仅 gem5 `writeRasHeader` 用 `kRasSbzMask`）⇒ 与 `ISS-426` 描述逐条一致；`.S` 仍断言 SBZ=0，**期望未放宽**。
5. `issues.yaml` 在本 worktree **无 diff**；`ISS-426`（`8d14f1f1`）的标题/现场值/修法与本红一致。
6. **越界 8 项改动数全 0**：`spec/`、`contracts/`、`Makefile`、`.tao/knowledge/`、`.tao/adr/`、`tests/inst/{base,02-reg-copy,03-wyde-imm,…}`、`inst-tiny.lds`、`issues.yaml`；`git status -uall` 恰 **8** 项，与完成区「修改文件」逐项一致；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`；注入全结束后 3 个 `.S` + `inst_test.inc` md5 与审查前快照**逐个相等**。
7. 完成区非空 **29** 行（≤30；含空行 37）；主工作树 `git status` 干净，reviewer 未提交 git、未改主树、临时物全在 `/tmp/opencode/m13-testcases-031/`。

**重试记录（1 次，环境干扰）**：`run.sh --inject`（三平台）第 1 次第 5 段全绿（234/235、红集正确），第 7 段因并行任务正在重建 `.work/source/gem5/build/DADAO/gem5.opt`（`PermissionError`，该文件当时 `-rw-rw-r--` 非可执行）而无法起 gem5 ⇒ 未采信；改用脚本文档化的 `PLATFORMS=qemu` 模式重跑 1 次 ⇒ rc=0。

**非阻断 finding（交 architect）**：F1 完成区段含空行 37 行（非空 29），建议收尾压到 ≤30；F2 `check-milestones-fresh` rc=2 的 2 条 VIOLATION **是本任务自己的台账行**（`m13-testcases-031` 仍在「待开始」表、任务书已「待验收」），**不是他任务** —— 按用户口径基线不判，但收尾须移行；F3 README/MIGRATION/任务书仍写「issue 候选号见任务书」，`ISS-426` 已登记，建议补号。

## 完成区

**测试结果**：节点三平台（同一份 ELF）**234/235 镜像通过**；唯一红 = `ld.o_rrii_ra` 链例（chipyard rc=0 / QEMU rc=20 / gem5 rc=20，`ra0`
的 SBZ 写语义分歧，**如实记红、期望未放宽**）。`st.o_rrii_rb` 17/17、`st.o_rrii_rd` 16/16 三平台全绿；本册 197 个故障例 0
红。一键证据脚本（`.work/evidence/<任务ID>/`）在节点跑 `--inject`：**CHECK=43 FAIL=0（RESULT=PASS）**，含 3 路「注入→FAIL→`cp`+md5 还原→回绿」、235 镜像/197 故障例、3 平台字节流 vs 独立复算。

**新增用例数**（现场派生）：链例检查点 **+11** = `st.o_rrii_rb` +3（`rb0` 作源）/ `st.o_rrii_rd` +1（`rb0` 作基址）/ `ld.o_rrii_ra`
+7（`ra0` 读 4 + 写 3）；故障例无新增（只顺延点号）。逐文件 17+2 / 16+4 / 22+2，点号 1..N 连续、≤127。

**`st.o rb0` 期望构造**：①`aip.si rb12,0` + `add.si rb12,8`（delta = 取址指令→被测 `st.o` 的字节差：A / A+4 / A+8 ⇒
**8**）；②`rb2rb {rb13},{rb0}` + `add.si rb13,8`；③`.org 0x1800` 钉住后写 `ENTRY+0x1800`。三者与 ELF
反汇编地址逐一相符：`0xffffff010998 / 0xffffff010a0c / 0xffffff011900`。

**`ld.o ra0` 读写**：写 3 例——chipyard 读回 `0x003F000000000000 / 0x0000000001234568 /
0x002AA5A55A5A1230`（SBZ=0、两字段生效）；QEMU/gem5 **保留写入的 SBZ 位** ⇒ 点 20 红。读 4 例（call C1 / 两层 call / 满栈 call C3b /
ret D4b）三平台一致：`0x0001…`、`0x0002…`、`0x003F…+MEMRAS+0x78`、`MEMRAS+0x80`。

**修改文件**：`git status --porcelain -uall` **8** 项 —— 3 个
`tests/inst/01-load-store/*.S`、`tests/inst/macros/inst_test.inc`（新宏
`__CHECK_MEM_RB`，纯追加）、`tests/inst/MIGRATION.md`（§6/031）、`tests/inst/README.md`、`tools/testcases/inst/run_asm_suite.py`（正则放宽）、本任务书。

**验收结果**：`check-tests-index` rc=0（341 条）｜`check-case-ledger` rc=0（2170）｜`validate_vectors` rc=0（gaps 0，723
例/156 id）｜273 例 sweep md5 `2d4d94651346ef673c5a855e024c1489`
不变（covered=273）｜`check-generator-sync`/`check-tasks`/`check-dirs`/`check-temp-dirs`/`check-no-residue`/`check-knowledge-dir`/`check-contracts-dir`
rc=0｜`make check-inst` rc=2，红集**恰** `{divrem.yaml[23]}`（1141/1135/1/5，既有
pin）。两处**既有**红与本任务无关：`check-patch-tree`（共享 `.work/source/*` 被并行组件构建改动）、`check-knowledge-refs`（5 条 `.work/**`
引用全在**他任务**书内）。

**新发现/坑**：① `ra0` 的 `[63:54]` SBZ 写语义 **QEMU/gem5 与 RTL 不一致**（RTL 丢弃、两模拟器保留）；② `st.o_rrii_rd` 的源银行是
rd（`rdha:src:rd`），`rb0` 只能作**基址**（`rbhb`），EA 必落 `.text` ⇒ 用「被 `jump` 跳过的零填充槽」承载（三平台写 RAM 均正常）；③ `rb0`
期望不能用标签差（`ISS-424` 静默折 0），须「IP 派生 + 绝对常量」两路并用才防「同错自洽」；④ 新增 `__CHECK_*` 宏必须同步驱动器正则（`\b` 不匹配 `_` 后缀 ⇒ 少计点）。

**遗留问题**：① **提案登记 issue（登记归主会话；本任务未改 `issues.yaml`）**：「`ld.o ra0`/`rd2ra {ra0}` 未丢弃 `[63:54]` 的 SBZ 位 ——
`SimRISC-00 §2.4` 规定 `ra0 = {SBZ(10),RACNT(6),MRPTR(48)}`、`[63:54]` 写无效（读回恒 0）；chipyard RTL
`WumingRegFile.writeRa` 按此丢弃，QEMU `trans_ld_o_rrii_ra → store_ra(0,val)` 全 64 位、gem5 ld.o 写 RA 口未掩码（仅 RAS 头更新用
`kRasSbzMask` 保留位）⇒ 写入位被保留并读回。现场：写 `0xFFFF000000000000` 读回原值、期望 `0x003F000000000000`，该链例点 20 在 QEMU/gem5
红。建议：两平台 RA 写口对 `[63:54]` 置 0（或读回恒 0）」；② `ISS-424` 仍在；③ `ISS-410` 的 hmon 自装 workaround 沿用（本任务**未新增故障例**、未依赖
`__INSTALL_HMON`/`.hmon_stub`）；④ `st.o_rrii_ra/rf`、`ld.o_rrii_rb/rd/rf` 其它形状未扩测（不在本任务范围）。
