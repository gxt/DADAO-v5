# m17-testcases-005: 测试向量去除内存实现术语（`beat`/`拍`/字节通道）一次性统一

**模块**：testcases
**项目里程碑**：M17
**依赖**：`m17-testcases-004`（同改 `tests/inst/**` 共享文件，必须串行；004 合并后再开工）
**可并行分片**：否（`tests/inst/**` 全族一次性替换，任何并行都会互相踩）
**预估**：2–3 h
**档位**：中改
**状态**：已验证

## 背景（用户 2026-11-23 裁定）

用户原话：**「不要把 beat 和拍这类的实现用的术语带入到测试向量中，统一调整一次」**。

现场盘点（2026-11-23，**在 m17-testcases-004 合并后复测**，`tests/inst/**` 的 `.S`/`.inc`/`.md`）：

| 术语 | 剩余位置 | 规模 |
| --- | --- | --- |
| `beat` | `01-load-store/01-load-store.inc`（11）、`macros/inst_test.inc`（3，含 `__CHECK_MEM` 形参）、`MIGRATION.md`（3）、`st.o_rrii_ra.S` / `st.o_rrii_rb.S`（各 2，宏形参 + 实参） | **5 个文件 / 24 处** |
| `拍` | `.S` 注释（`8 B 拍`、`多拍`、`末拍`、`尾拍`、`拍内`、`跨多拍`、`一拍`、`全 0 拍`…） | **58 个文件 / 293 处** |
| `字节通道` | `MIGRATION.md` 表格 | 1 处 |
| `总线` / `流水` | 零散注释 | 2 / 1 处 |

这些是**内存流水/颗粒/总线**的实现术语，不属于 ISA 语义；测试向量的注释应只用 ISA 侧说法（字节、元素、寄存器、地址、对齐）与测试框架自身概念（用例、检查点、镜像、槽）。

## 目标

1. **注释与文档**：`tests/inst/**` 下 `.S` / `.inc` / `.md` 中
   - `beat`、`拍` → **「数据单元」**；首次出现或易混处标宽度「**8 字节数据单元**」；
   - 按语境的短语映射（其余可类推，须保持原意）：
     `多拍` → `多个元素`（块指令语境）/ `多个数据单元`；`末拍`/`尾拍` → `末个数据单元` / `尾部数据单元`；`一拍` → `一个数据单元`；`拍内` → `数据单元内`；`跨多拍` → `跨多个数据单元`；`全 0 拍`/`全 1 源/拍` → `全 0 数据单元`/`全 1 源或数据单元`；`整 beat 比` → `整 8 字节比`；`现有 beat` → `现有 8 字节数据单元`；
   - `字节通道` → 窄写句用显式字节数（004 已做）；其余改为「字节」；`总线`/`流水` 改为 ISA 侧说法。
2. **代码标识符**：宏参数 `\beat` → `\unit`、`\beats` → `\units`（`inst_test.inc` 定义 + 全部调用点实参），使 `tests/case-ledger.tsv` 的源行文本里也不再出现 `beat`。
3. 一条命令可验证的终态：`grep -rniE "beat|拍|字节通道" tests/inst` **零命中**（含 `.S`/`.inc`/`.md`）。

## 验收（逐条贴真实 rc）

1. **语义零漂移**：全部 272 个镜像的 `.text` **md5 与改前逐个相同**（注释/参数名不改代码）。做法：改前从 `git show HEAD:<file>` 取基线副本，用同一 `clang`/`ld.lld` 与同一 `.lds` 汇编、链接，逐镜像比对；给出「比对 N 个、不一致 0 个」与脚本路径。
2. **术语清零**：`grep -rniE "beat|拍|字节通道" tests/inst` rc=1（无输出）；`grep -rn "beat" tests/` 全仓零命中（`tests/data/**`、`tools/testcases/**` 也查，若命中一并处理并说明）。
3. **数据与台账**：`make inst-signature-data` 后 `tests/data/inst-signature/expected.tsv` **零变化**（槽级期望）；`inputs.sha256` 记录的是**输入文件整字节 sha256**，纯注释改动必然改变它 ⇒ 判据为「变化行数 == 改动过的输入文件数（本次 `.S`/`.inc` 58 个 + `tests/ee-tiny/tests_inst_tiny.lds` 1 个 = 59），且逐文件复核 sha256 与现文件一致」；`make check-case-ledger --write` 重生成 `tests/case-ledger.tsv`，`git diff` 只含源行文本变化（用例数、点号、镜像数不变）。
4. **门控**：`make check-inst-asm`（镜像数同改前）、`make check-inst-sig`、`make check-case-ledger`、`make check-tests-index`、`make check-inst-macro-scope`、`make validate-vectors`、`make check-asm-prose`、`make check-knowledge-refs` 真实 rc；若某门控基线即红，按「与基线逐行相同」记 KNOWN-RED。
5. **抽样人工复核**：随机抽 10 个文件（含 `stm.*`、`ldm.*`、`12-misc`、两个 `.inc`、`MIGRATION.md`），逐条确认替换后句子仍与 spec 语义一致（贴 diff 片段）。
6. 完成区列出：改动文件数、替换处数（按术语分列）、`.text` 比对计数、以及**未改动**的说明（若有个别处故意保留，必须逐条给理由）。

## 约束

独立 `git worktree`（分支 = `m17-testcases-005`）；**不提交 git**；只改 `tests/inst/**`、`tests/case-ledger.tsv`（重生成）与本任务书；**不动** `spec/`/`.tao/contracts/`/`contracts/`/门控脚本；不改任何用例的点号、期望值、镜像数；术语「寄存器组」；完成区不写具体 `.work/**` 路径。**2026-11-23 主会话追加范围**：`tests/arch/ptw/ptw_walk.S` 与 `tests/ee-tiny/tests_inst_tiny.lds` 的同类术语一并清理（`tests/unit`/`tools/testcases` 两处无关英文词经裁定不改）。

## 完成区

**测试结果**：通过 16/16（运行期证据目录 `run.sh` 全绿：术语 3、零漂移 3、签名数据 1、台账 1、门控 8）；其中 `check-inst-asm` 272/272 镜像通过（272 id；链例 + 故障链 632 例）。失败原因：无。

**修改文件**：64 个 = 本任务书 + 63 个产物/数据（`tests/inst/**` 59 = `macros/inst_test.inc`、`MIGRATION.md`、`00-isa-design/atomic_rmw.S`、`05-arith-addr/aip.si_riii_rb.S`、`01-load-store/` 29 = 册 `.inc` + `ld.t` + `st.o`×4 + `stm.*`×9 + `ldm.*`×11 + `st.*`×3、`12-misc/` 26 = 册 `.inc` + `swym` + `lr.*`×12 + `sc.*`×12；`tests/arch/ptw/ptw_walk.S`、`tests/ee-tiny/tests_inst_tiny.lds`；重生成 `tests/case-ledger.tsv`、`tests/data/inst-signature/inputs.sha256`）。完整清单以 `git diff --name-only`（64 项）为准。

**验收结果**：
- 术语清零：`tests/inst` rc=1、0 命中；`ptw_walk.S` + `tests_inst_tiny.lds` rc=1、0 命中。替换处数：`beat` 24 / `拍` 295（tests/inst 293 + 追加 2）/ `字节通道` 1 / `总线` 2 / `流水` 1（另同类实现词：`b/w/t 只改几条通道` → 「几个字节」1 处、`只开 1 lane` → 「只写 1 个字节」2 处）。
- 零漂移：① 272 镜像逐镜像汇编+链接，比 `.text` md5 与整 ELF md5 = **272 比对 / 0 不一致**；② `ptw_walk.S` 不在 272 内，独立取基线汇编+链接，`.text`/ELF md5 均同（`56b0ec2a…` / `dba9040b…`）；③ `tests_inst_tiny.lds` 用 2 个代表镜像（`st.o_rrii_rd`、`lr.b.nn_orrr_rd`）以改前/改后 lds 链接，ELF/`.text` md5 均同（`0bce43f7…`/`64962408…`、`cce2cef9…`/`828adf38…`）。反例自检（基线树注入 4 B → mismatch=1 → `cp` 还原 + md5 对账 → mismatch=0）通过。
- 签名数据：`expected.tsv` md5 与基线相同（`a080ec4e…`，零变化）；`inputs.sha256` 变化 59 行 == 58 个改动 `.S`/`.inc` + 1 个 `tests_inst_tiny.lds`，逐文件 sha256 复核一致。**`inputs.sha256` 非零变化属生成器设计**：它记录输入文件整字节 sha256（`inst_expected.render_inputs`），纯注释改动必然变；判据见验收 3。
- 台账：5706 行不变（含 3 行表头；现场身份 5702 条），仅 2 行内联注释文本变化；`beat` 0 行；身份列/点号/镜像数不变。
- 门控真实 rc：`check-inst-asm` 0、`check-case-ledger` 0、`check-tests-index` 0、`check-inst-macro-scope` 0、`check_inst_sig.py --data-only` 0、`validate-vectors` 0、`check-asm-prose` 0、`check-knowledge-refs` 0。`make check-inst-sig` 已退役（`m17-testcases-003`），以 `--data-only` 代替。
- 证据脚本：运行期证据目录内 `run.sh`（默认全跑；`--inject` 只做注入反例门控）。

**追加范围（主会话 2026-11-23）**：① `tests/arch/ptw/ptw_walk.S:13`「逐拍读回」→「逐个数据单元读回」（同句其余不动）。② `tests/ee-tiny/tests_inst_tiny.lds:14`「单元素 24 拍模式」→「单元素 24 个数据单元模式」；判断依据 = 该句描述 `.testdata` 布局：`0x800` 负偏移区之后 `TEST_DATA` 起 192 B 模式（24 × 8 B），与 `inst_test.inc` 的「24 个 8 字节数据单元」逐项对应，不是别的东西。③ 按用户裁定不改并留说明：`tests/unit/linux/k5_signal_probe.py` 的 `heart-beating` 指进程存活（非内存术语），`tools/testcases/arch/min_rom_probe_036t.py` 的 `static beats default` 中 `beats` 是动词「胜过」。④ worktree 内 `.dadao` 是 gitignored 软链，指向共享安装根，仅用于取 QEMU/bootrom/工具链跑 L2 门控；**不入库，主会话收尾可直接删除**。

**新发现/坑**：① `inputs.sha256` 是输入文件（`tests/inst` 的 `.S`/`.inc`、共享 asm、`tests_inst_tiny.lds`）整字节哈希，注释改动必变；判据 =「变化行集 == 改动输入文件集 + `expected.tsv` 零漂移」。② worktree 无 gitignored `.dadao` 安装根，需运行期软链到共享安装根才能跑 L2 门控（未入库）。③ 证据脚本首版把台账内联注释当成第 3 列，且数据检查未把 lds 计入输入集，均已修正并以真实差异复验。

**遗留问题**：无未完成项。依用户裁定保留不改：`tests/unit/linux/k5_signal_probe.py`（`heart-beat*`，进程 liveness）、`tools/testcases/arch/min_rom_probe_036t.py`（`static beats`，英文动词）。

### 抽样人工复核（验收 5，固定种子 20261123 分层抽取 10 个文件）

- `01-load-store/stm.w_rrri_rd.S`：`mem16[EA + 2i] ← 源 i 低 16 位`；16 位元素按 2 B 对齐、宽度整除 8 ⇒ 「元素不跨 8 字节数据单元」与 `spec/SimRISC-01 §1` 对齐限制一致。diff：`8 B 拍`→`8 字节数据单元`、`一拍`→`一个数据单元`。
- `01-load-store/ldm.o_rrri_rd.S`：`mem64[EA + 8i]`；`count=8（多个数据单元…）` 与 8 个 8 字节元素一一对应。
- `12-misc/lr.b.nn_orrr_rd.S`：每例独立 8 字节数据单元；保留粒度 = 精确地址 + 访问宽度（`spec/SimRISC-12 §1`）；`全 0 数据单元`/`最后一个数据单元（地址上界）` 两句语义不变。
- `01-load-store/st.w_rrii_rd.S`、`st.t_rrii_rf.S`：三条边界存储**各写一个数据单元**；b/w/t 分别只改 2/4 字节、其余保持（`spec/SimRISC-01` 存储宽度）。
- `05-arith-addr/aip.si_riii_rb.S`：改为「无 ±4 修正项、低位不清零」，对应 `spec/SimRISC-05 §4`「无 ±4 流水偏移……无需任何修正项；IP 低位不清零」。
- `01-load-store/ld.t_rrii_rf.S`：`ld.o` 预置 8 字节数据单元高半非零，`ld.t` 只写低 32 位、高半保持（`spec/SimRISC-01 §4` 窄写注）。
- `01-load-store/st.o_rrii_rb.S`：宏形参 `beat`→`unit`、`\beat`→`\unit`，调用点实参未动；`.text` 比对证明无代码漂移。
- `macros/inst_test.inc`：MUNI/MSTORE/RDATA/WDATA 定义补「8 字节」宽度；`__CHECK_MEM` 仍以 EA 所在 8 字节单元（`EA/8*8`）为单位比较（大端）。
- `01-load-store/01-load-store.inc`：`TEST_ST`/`TEST_ST_RF` 形参 `beat`→`unit`，`\beats`→`\units`，`.error` 文案同步；`字节通道`→「窄写的字节范围」。
- `MIGRATION.md`：表项改「数据单元期望」「该 8 字节数据单元逐字节相等（b/w/t 只改其中几个字节）」；`总线`→`访存`；`同值拍`→`同值数据单元`。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `inputs.sha256` 按任务预期应零变化，实际变 58 行 | ❌不修（设计使然） | 无；核实生成器为整字节 sha256 | `expected.tsv` md5 不变；变化行集 == 58 个改动源文件；`--data-only` rc=0 |
| `aip` 初版写「无 ±4 附加偏移」，与 spec 的「无需任何修正项」措辞不贴 | ✅已修 | 改为「无 ±4 修正项」 | `SimRISC-05 §4` 对照；重生成 `inputs.sha256` 后 `--data-only` 0 |
| 「数据区末个数据单元的 sc」等句生硬 | ✅已修 | `末个`→`最后一个`（25 处） | 抽样复核句子可读、语义不变 |
| 替换产生「数据单元 的」多余空格（2 处） | ✅已修 | 删除空格 | `grep "数据单元 的"` 0 命中 |
| `b/w/t 只改几条通道` 与 `只开 1 lane` 属同类实现术语，但不在 `字节通道` 字面规则内 | ✅已修 | 改为「只改其中几个字节」1 处、「只写 1 个字节」2 处 | `grep 通道\|lane tests/inst` 0 命中；`--data-only` rc=0 |
| 证据脚本台账检查误报 2 行列变化 | ✅已修 | 内联注释列下标 2→3（仅在该列允许术语变化） | `run.sh` 全跑 PASS=13 FAIL=0 |
| `tests/arch`、`tests/ee-tiny/*.lds`、`tests/unit`、`tools/testcases` 仍有同/近形词 | 部分改 | 第 2 轮按主会话追加：`ptw_walk.S` 与 `tests_inst_tiny.lds` 已改；`tests/unit`/`tools/testcases` 按裁定保留 | 见第 2 轮 |

### 第 2 轮 engineer 自审（主会话追加范围）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `ptw_walk.S` 不在 272 镜像内，需独立零漂移证据 | ✅已修 | 取基线 `tests/arch/ptw/**` 独立汇编+链接（带生成器 `ptw_walk_tables.inc`） | `.text` `56b0ec2a…`、ELF `dba9040b…` 基线与现树相同 |
| `tests_inst_tiny.lds` 注释改动需证明零影响 | ✅已修 | 2 个代表镜像（`st.o_rrii_rd`、`lr.b.nn_orrr_rd`）用改前/改后 lds 链接 | ELF/`.text` md5 均同；272 镜像比对亦覆盖该 lds |
| lds 也是 `inputs.sha256` 的输入，验收 3「== `.S`/`.inc` 数」在追加后不成立 | ✅已修 | 验收 3 改为「改动输入文件数（58 `.S`/`.inc` + 1 lds = 59）」；证据脚本输入集加入 lds | `inputs.sha256` 变化 59 行；逐文件 sha256 一致；`--data-only` rc=0 |
| `k5_signal_probe.py` 的 `heart-beating`、`min_rom_probe_036t.py` 的 `static beats` 是否误改 | ❌不修（用户裁定） | 无（前者进程存活、后者英文动词） | 完成区「追加范围」③ |

### 第 1 轮 reviewer 验收（2026-11-23，档位 中改 / 40 min）

**重跑记录（全部为 reviewer 自己的命令与真实输出/退出码）**

- 术语：`grep -rniE "beat|拍|字节通道" tests/inst --include=*.S --include=*.inc --include=*.md` → rc=1、0 行。`grep -rni beat tests/` → 仅 2 行：`tests/unit/linux/k5_signal_probe.py:43,146`（进程存活 `heart-beating`/`group-heartbeats`，按裁定保留）；`tools/testcases` 仅 `min_rom_probe_036t.py:932`（`static beats default`，beats=英文动词）。现树计数：`拍`=0、`beat`=0、`字节通道`=0、`通道|lane|总线|流水`=0；基线计数 = 拍 293（+追加 2）/ beat 24 / 字节通道 1 / 总线 2 / 流水 1 / lane 2，与完成区一致。
- 零漂移（reviewer 独立脚本：基线 `git archive HEAD` 到临时树 + 同一交叉工具链逐镜像汇编/链接，未复用 engineer 脚本）：`images=272 current=272 lists_equal=True mismatch=0 error=0`，rc=0；指定 8 文件（`stm.o_rrri_ra`、`ldm.o_rrri_rd`、`st.b_rrii_rd`、`st.o_rrii_rf`、`rf2rf_orri_rf`、`sc.b.nn_orrr_rd`、`st.w_rrii_rd`、`ld.o_rrii_rd`）`.text` 与整 ELF md5 逐一 SAME。
- 追加 2 处：`ptw_walk.S` 基线 vs 现树 `.text=56b0ec2a…`、`ELF=dba9040b…` 相同；`tests_inst_tiny.lds` 用 `st.o_rrii_rd`、`lr.b.nn_orrr_rd` 以改前/改后 lds 链接，ELF/`.text` md5 均 SAME（`0bce43f7…`/`64962408…`、`cce2cef9…`/`828adf38…`）。
- 脚本可失败：运行期证据目录内 `run.sh --inject` rc=0，`mismatches=1`（注入 `pseudo_set.rd_reg.S`）→ `cp` 还原 + md5 对账 → `mismatches=0`；全量 `run.sh` rc=0、`PASS=16 FAIL=0`（与完成区 16/16 一致）。
- 数据：`expected.tsv` md5 `a080ec4e…` == HEAD；`inputs.sha256` 变化 59 行，与改动输入集（58 个 `.S`/`.inc` + 1 个 lds）`diff` rc=0 全等；抽 3 文件（`inst_test.inc`、`sc.b.nn_orrr_rd.S`、`tests_inst_tiny.lds`）sha256 与现文件一致；台账 5706 行、身份列 md5 与末列（点号）md5 同基线、diff 仅 2 行内联注释、`beat` 0 行、现场身份 5702。
- 门控（逐条重跑、捕被检命令自身 rc）：`check-inst-asm` 0（272/272、链例+故障链 632 例）、`check-case-ledger` 0、`check-tests-index` 0（492 条）、`check-inst-macro-scope` 0、`check_inst_sig.py --data-only` 0（272 镜像/4540 槽）、`validate-vectors` 0（272 carriers）、`check-asm-prose` 0、`check-knowledge-refs` 0（悬空 0）。
- 语义抽检 >10 处：`8 B 拍`→`8 字节数据单元`、`多拍`→`多个数据单元`、`末拍/尾拍`→`最后一个/尾部数据单元`、`拍内`→`数据单元内`、`全 0 拍`→`全 0 数据单元`、`整 beat 比`/`现有 beat`（基线 0 命中，无需映射）、`MIGRATION.md` 表格（`beat 期望`→`数据单元期望`、`字节通道`→`其中几个字节`、`总线`→`访存`）、`aip` `无 ±4 修正项` 对 `spec/SimRISC-05:141`、`tests_inst_tiny.lds` `24 个数据单元` = 192 B/8 与 `inst_test.inc` 对应 —— 逐句读过，未见元素/数据单元/边界混用；`\beat` 全仓 0，`\unit`/`\units` 定义与 7/3 处调用配套（宏按位置传参，`check-inst-asm` 272/272 佐证）。
- 范围与残留：`git diff --name-only` 64 项全在白名单（`tests/inst/**`、`ptw_walk.S`、`tests_inst_tiny.lds`、`case-ledger.tsv`、`inputs.sha256`、本任务书）；`spec/ contracts/ Makefile tools/` diff = 0；`git status` 64 行全为 ` M `、`??` 0 项；`.dadao`（软链）与运行期证据脚本均 ignored、未入库；验收前后 `git status` 行集相同，产物 md5 未变（审查全程只读 + 临时树注入，未动工作树）。

**判决：Accepted** —— 验收 1–6 与全部硬约束在我自己的重跑下通过，无阻断项；工程师完成区计数与现场复算逐项吻合。architect 终审。

## 待裁定

- 无。`tests/unit/linux/k5_signal_probe.py` 与 `tools/testcases/arch/min_rom_probe_036t.py` 按用户裁定保持不改，理由见完成区「追加范围」③。
