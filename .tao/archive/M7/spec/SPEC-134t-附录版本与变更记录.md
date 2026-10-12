# SPEC-134t: 21 册「附录：版本与变更记录」+ `-rc` 版本口径

**模块**：spec
**项目里程碑**：M7
**依赖**：`SPEC-133t`（**标题编号先统一**；同改 21 册 `spec/*.md` ⇒ **必须串行**）
**状态**：已验证

> 本任务书由**主会话**依用户 2026-10-11 裁定撰写（非常规 architect 起草，已披露）。编号：`SPEC-132m` 为 M7 spec 里程碑保留（`INTEG-033k`）。

## 用户裁定（2026-10-11，**原话要点**）

1. 「对 `spec` 目录下的 `SimRISC-*` 和 `DADAO-*` 文档，增加一个结尾的 Changelog，将从仓库第一个 commit 开始到最新 commit 之间的变动记录下来；对于上一版本之后，版本号没有变化但内容改动的情况，可以统一用 **下一版本** 来记录」；「该任务对其它任务没有依赖，放在**里程碑达成之前**即可」。
2. 「**格式尽量保持一致**（21 册）」。
3. 「**SimRISC 手册中间有一次拆分，按拆分后的分册来记录其改动**」。
4. 「标题用 **版本与变更记录**，**二级标题**；各版本号和发布时间用**三级标题**」。
5. 「**下一版本**如何体现在版本号上…比如 `0.5.5-rc`」→ 裁决：**用 `-rc` + 册头也改**。
6. 「在版本与变更记录里，应该是**版本号的逆序**」。
7. 「**版本与变更记录前面加 `附录：`，不加章节号**」。
8. 「**聚合**（按版本段），但**无需限制条数**；**不带任务号/ADR 号**」。
9. 「`x.y.z` 中的 **x 并不是恒为 0，而是在正式发布之前为 0**」。
10. 口径细节（主会话据上述裁定整理）：**无历史变更的册也加附录**（只列当前版本段）；**"加记录"动作本身不引发 `-rc`**（属记录层，非规范语义）。

## 目的

21 册（`manifests/spec-readonly.lock.toml` 锁内全套 = `SimRISC-00..12` + `DADAO-11/12/13/21/22/23` + `Toolchain-01` + `Machine-01`）**文末统一追加**：

```
## 附录：版本与变更记录        ← 二级标题，**不加章节号**，**逆序**（最新在上）

### 0.5.5-rc（未发布）          ← 累积段：上一发布版本之后的**未发布改动**聚合于此
- 变更…
### 0.5.4（2026-xx-xx）         ← 三级标题 = **版本号 + 发布时间**
- 变更…
### 0.5.3（…）
- …
```

## 接口规范

### 输入 / 取证方法（**必须留档，可审计**）

- **变更来源 = git 史**（**禁凭记忆/推断**）：逐册 `git log --follow -- <路径>`；**首个 commit → HEAD**。
- **版本边界**：册头 `> **版本：X.Y.Z**` 的历史值 + `ADR`/任务书记录的版本变更点（现场核）。
- **发布时间**：由 git 史取证（该版本号写入/对应 ADR 日期等）；**取证命令与结论留档**；取不到 ⇒ 标注不确定（**不得编造**）。
- **SimRISC 拆分**：定位**拆分 commit**（结合 `ADR-0012` 0.5.3→0.5.4）；**拆分前的变动按主题归属到拆分后的分册**；拆分前后**册名/§号不同** ⇒ **映射表留档**。
- **聚合**：按版本段聚合（**不限条数**）；**不带任务号/ADR 号**（只写"改了什么"）。
- `Toolchain-01`/`Machine-01` **已有** changelog（`INFRA-060t` 手工回推）⇒ **与 git 史核对后合并**（去重），统一为 `## 附录：版本与变更记录`。

### 输出

1. **派生方法留档**（`.work/log/spec/`）：命令、版本边界表、发布时间来源、拆分映射表、每册变更计数（**现场统计**）。
2. **21 册附录**（格式如上；**逆序**；`-rc` 段置于顶部；无变更册只列当前版本段）。
3. **`Toolchain-01` / `Machine-01` 与其它 19 册同批处理**（用户 2026-10-11：「同步更新一下 `Toolchain` 和 `Machine`」）：
   - 附录**统一**为 `## 附录：版本与变更记录`，与其**既有** changelog（`INFRA-060t` 手工回推）**与 git 史核对后合并去重**（不重复、不丢项）；
   - 册头**版本号细则**（`INFRA-063t` 写入）的 `x=0` 口径**回改**（见输出 5）；
   - 册头 `-rc` **判据同上**（"自上次发布是否有内容改动"）；**注意**：本任务"加记录"动作本身**不引发** `-rc`，两册既有版本（`Toolchain 0.5.0` / `Machine 0.3.0`）若自其记录点后无新改动 ⇒ **不变号**（判据与结论逐册写入完成区）。
4. **册头 `-rc`**：**仅当该册自上次发布后确有内容改动** ⇒ `> **版本：0.5.4**` → `> **版本：0.5.5-rc**`；**互锁按组同改**：`SimRISC-00..12`（一组）、`AEE↔ABI`、`SEE↔SBI`、`HEE↔HBI`；`Toolchain-01`/`Machine-01` **本次不变号**（"加记录"动作不引发 `-rc`）。
5. **发布动作定义**（写进各册附录头部一行或任务书说明）：发布时把顶部 `-rc` 段去 `-rc` + 补发布日期，并在其**上方新开空 `-rc` 段**。
6. **`x=0` 口径回改**：`Toolchain-01`/`Machine-01` 册头**版本号细则**（`INFRA-063t` 写入）现写「`x=0`」⇒ 改为「**`x=0` 表示尚未正式发布；正式发布后 `x≥1`**」（+ 锁同步）。
7. **连带**：根 `README.md`「当前版本号」表同步（否则 `check-spec-drift` 红）；`manifests/spec-readonly.lock.toml` 21 册 `sha256` 更新。
8. `.tao/knowledge/milestones.md` 流水更新 `SPEC-134t` 行（状态 `待验收`，`完成时间` `—`）。
9. **约定落纸（用户 2026-10-11：「关于 spec 编号、版本与变更记录的各种商定…放在 `spec/README.md` 中如何？」⇒ 采纳）**：在 **`spec/README.md`** 增加一节「**册维护约定**」，只写 **spec/ 目录特有**约定，**不重复** `docs/Process-0x` 的通用规范（重复处只给指针）：
   - **标题编号**：`##`→`N`、`###`→`N.M`、`####`→`N.M.K`（**最深 `####`**）；同册唯一、连续；**引用**可写 `§N.M` 或 `§<标题文本>`，两者等价（解析器剥离前导编号）；
   - **`附录：版本与变更记录`**：二级标题、**不加编号**、**逆序**（最新在上）；三级标题 = `### <版本>（<发布日期>）`；顶部累积段 = `### <上一发布版本 z+1>-rc（未发布）`；
   - **发布动作**：把 `-rc` 段去 `-rc` + 补发布时间，并在其**上方新开**空 `-rc` 段；
   - **版本号语义**：`x.y.z`——**`x=0` 表示尚未正式发布**（正式发布后 `x≥1`）；大改 `y+1`、有影响的小改 `z+1`；
   - **互锁组**：`SimRISC-00..12`、`AEE↔ABI`、`SEE↔SBI`、`HEE↔HBI` 组内版本**必须一致**；
   - **只读册纪律**：21 册 `sha256` 锁（`manifests/spec-readonly.lock.toml`）；改册须**用户事先授权原话** + **同变更内更新锁**（`docs/Process-06`）；
   - **改动记录粒度**：**聚合**（按版本段）、**不限条数**、**不带任务号/ADR 号**。


### 约束

- **只追加附录 + 册头版本行（+2 册细则）**：**不改规范正文语义**（`Process-06 §2` 授权 = 上述用户原话，**落纸**）。
- **格式统一**：21 册一致（标题层级、逆序、`-rc` 段位置、条目形态）。
- **计数不写死**；临时目录 `/tmp/opencode/SPEC-134t/`；**不提交 git**；禁 `git add -A`/`.`。
- 反例注入还原**禁** `git checkout/restore/stash`；一律 `cp` + md5 对账。
- 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位），否则 `check-knowledge-refs` 判悬空、`make check` 自伤。

## 验收标准

1. **21 册齐**：每册文末有 `## 附录：版本与变更记录`（**二级、无编号**）；册数=21（现场统计）。
2. **格式一致**：三级标题 = `### <版本>（<日期>）` / 顶部 `### <版本>-rc（未发布）`；**逆序**（机械校验：版本号递减 + `-rc` 在首）；**无表格**；**无任务号/ADR 号**（`grep` 抽样）。
3. **可追溯**：抽查 ≥5 条变更（含至少 1 条 `-rc` 段项、1 条跨拆分项）能回溯到 git 史（给真实命令与输出）。
4. **册头一致**：有未发布改动的册组 = `X.Y.Z+1-rc`，且**附录顶部段号与册头一致**；无改动册保持发布版号（逐册对照表）。
5. **互锁**：`SimRISC-00..12` 组、`AEE↔ABI`、`SEE↔SBI`、`HEE↔HBI` 组内版本**一致**（机械校验）。
6. **门控**：`make check`、`check-spec-readonly`、`check-spec-refs`、`check-asm-prose`、`check-spec-drift` 各 EXIT=0（捕获**命令自身**退出码，禁 `cmd | tee`）。
7. **反例可失败**：注入（打乱逆序 / 册头与附录段号不一致 / 插入一条任务号）⇒ 校验脚本 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿。
8. **一键证据脚本**落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
9. **完成区**（≤30 行）与真实输出逐条对齐。

## 完成区
**测试结果**：`make check`(L1) rc=0；`check_spec_readonly`/`check_spec_refs`/`check_asm_prose`/`check_spec_drift`/`check_spec_codeblocks`/`check_knowledge_refs` 各 rc=0；`check_numbering` rc=0（`files=21 h2=106 h3=163 h4=28 total=297`）；`check_spec_changelog` rc=0（`files=21 segments=99 rc_segments=19 bullets=221`）；一键证据脚本 rc=0（含 6 项反例注入）。
**修改文件**：21 册 `spec/*.md`（+附录 & 册头版本行；`Toolchain-01`/`Machine-01` 另改版本号细则 + 用附录替换旧 changelog）；`spec/README.md`（+「册维护约定」）；根 `README.md`（版本表 +「在研版本」列）；`manifests/spec-readonly.lock.toml`（21 册 sha256 重算 + 授权备注）；`tools/spec/check_numbering.py`（跳过附录段）；**新增** `tools/spec/check_spec_changelog.py`；`.tao/knowledge/milestones.md`（+流水行）。
**验收结果**：
- 1/2：21 册文末均有 `## 附录：版本与变更记录`（二级、无编号）；三级 `### <版本>（<日期>）` + 顶部 `### <版本>-rc（未发布）`；逆序/无表格/无任务号由 `check_spec_changelog` 机械校验（现场 21 册 / 99 段 / 221 条；附录净增 583 行）。
- 3：抽查 7 条可回溯 git 史（含 `-rc` 段项 = ABI 返回值契约 `cc93f64`、跨拆分项 = 存取后缀统一 `eace49e`）——原始命令留 `.work/log/spec/SPEC-134t-*.txt`。
- 4/5：逐册册头 ↔ 附录顶部段号一致；互锁组 `SimRISC-00..12`/`AEE↔ABI`/`SEE↔SBI`/`HEE↔HBI` 组内一致（19 册 `-rc`；`Toolchain-01`=0.5.0、`Machine-01`=0.3.0 不变号）机械校验。
- 6：门控全绿（见「测试结果」）。
- 7：6 项反例注入（逆序乱序 / 册头不一致 / 插入任务号 / 空段 / 表格行 / 互锁不一致）各 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿（证据脚本内，md5 逐项对账）。
- 8/9：校验器入库 `tools/spec/`；证据脚本 rc=0；本区与真实输出逐条对齐。
**新发现/坑**：① **互锁组不能按锁 `group`（`dadao-1x/2x`）取值**——首版断言因此**恒真空转**，被反例注入（命中 x0）当场暴露；改按册名归类；② 段归属口径：用户裁定 1 ⇒ 段 X 收纳「上一版本号写入 → 本版本号写入」间的改动（`0.5.4` 含 2026-07-19~09-28 含重组）；③ **DADAO 册版本自导入未变** ⇒ 上游发布日期 git 史取不到，附录标「日期不详」（不编造），自导入起改动全归 `<z+1>-rc`；④ **README 版本列与 `check-spec-drift` 耦合**（drift 比对 README ↔ `contract-*.md`）⇒ 版本列若改 `-rc` 而不动合约必红；故 README 加「在研版本」列（已发布列供 drift），合约未动。
**遗留问题**：① `check_spec_changelog`（与 `check_numbering` 一样）**未并入 `make check`**（未改共享 `Makefile`，避免越界），现由证据脚本调用；② **越界披露**：除任务书列出对象外，另改 `tools/spec/check_numbering.py`（附录段无编号 ⇒ 须跳过）并新增 `tools/spec/check_spec_changelog.py`（任务书面「校验器必须入库」）；③ `Toolchain`/`Machine` 合并：**旧 changelog 条目全保留**，另补 git 史独有 3 项（`ftlog`/`folog` 删除、D3/D10 汇编文档更新、浮点 `scope`），无重复条目被删（去重数 = 0）。

## 审阅记录

#### 第 1 轮 engineer 自审
**范围**：21 册附录内容 + 册头/细则 + `tools/spec/check_numbering.py`(改) + `tools/spec/check_spec_changelog.py`(新) + README/lock/milestones 连带。
**逐项审查**：
- 逻辑正确性：10 条断言各有可达 FAIL（6 项注入实测）；**发现 F1**（互锁恒真）当场修；**F2**（段非空死代码 + 计数错位）修。
- 边界：`SEG_RE` 兼容非日期括注（`（上游基线，日期不详）`）；`-rc` 仅首位校验 + z+1 校验；`check_numbering` 自附录起点跳过剩余标题（避免版本号被当章节号）；`check_spec_changelog` 复用锁清单、不硬编码册名。
- 设计/惯用法：计数现场统计（不写死）；`<>`/`*` 占位避免 `.work` 悬空；新校验器与新段口径同源（`APPENDIX_RE` 两处一致）。
- 防造假：附录条目均由 git 史派生（日志留档），抽查 7 条回溯通过；注入还原一律 `cp`+md5，**未用** `git checkout/restore/stash`。
**finding 处置**：
| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 互锁断言恒真（按锁 `group` 取名，AEE/ABI 等不在内） | ✅已修 | `check_spec_changelog.interlock_group()` 按册名归类 | 注入 AEE→0.9.4-rc ⇒ `互锁组 aee-abi` FAIL x1；还原回绿 |
| F2 段非空为 `pass` 死代码 + 计数错位 | ✅已修 | 按段归集 bullets，`nb==0` 报错 | 注入空段 `### 0.0.1` ⇒ `无条目` FAIL x1；还原回绿 |
| F3 附录含 `D3/D10`（ADR 决策号） | ✅已修 | 3 处改「汇编规范文档更新」 | 校验器无任务号/ADR 命中；锁同步重算 |
**判决**：finding 全修；`make check` + 6 项注入 + 全部证据 rc=0 ⇒ 标 `待验收`。

#### 第 1 轮 reviewer 验收
**重跑（本人命令，非采信 engineer）**：`make check`=0；`check-spec-readonly/refs/asm-prose/drift` 各=0；`check_numbering`=0（`files=21 h2=106 h3=163 h4=28 total=297`）；`check_spec_changelog`=0（`files=21 segments=99 rc_segments=19 bullets=221`）；证据脚本 `<evidence>/run.sh` 全量=0（6 反例各 rc=1 + md5 还原 + 回绿，实测）。
**格式抽验（6 册）**：SimRISC-00/07、DADAO-12/13、Toolchain-01、Machine-01 —— `## 附录：版本与变更记录` 二级无编号、`### <版本>（<日期>）`、逆序递减、`-rc` 段在首；全 21 册 `grep` 表格行=0、任务号/ADR 号=0；独立统计 segments=99/rc=19/bullets=221 与校验器一致。
**可追溯抽查（6+ 条，全属实）**：① `-rc` 项 DADAO-21「返回值契约收口 rd8/rb8/rf8、K=8、sret 经 rb16」= `cc93f64`(10-09) diff 实证；② 跨拆分项 SimRISC-01「存取后缀统一 ld.ub/st.b…」0.5.2 = `eace49e`(07-18，触旧 5 卷《数据类/地址类/浮点类》)；③ SimRISC-00 0.5.4「重组 12 分册」= `890038e`(09-28，拆分 commit，版本边界 `0.5.0=7320557`…`0.5.4=890038e` 复核一致)；④ Machine-01 0.3.0「RAM 迁 0xFC00…」= `3b36c9a`(10-11)；⑤ Toolchain-01 0.5.0「§7 数据指示符」= `0f7d117`(10-10)；⑥ Toolchain 0.2.1 四条 = `8788fcd/c3769f2/166c1a3/9590851` 均 09-29。**DADAO「上游基线，日期不详」判定恰当**：`3f69139`(07-14) 导入时 DADAO-21 册头即 `版本：0.9.2`、自导入未变，上游发布日期 git 史取不到 ⇒ 不编造（可选改进：补注导入日期）。
**拆分映射抽查**：`eace49e`（存取）→SimRISC-01 合理（主题=取数存数）；旧《数据类》加减/逻辑→SimRISC-04 0.5.2 条目合理；旧《系统类》→SimRISC-11（占位/非法/特权）+SimRISC-12（原子），与映射表 `<log>/SPEC-134t-presplit-themes.txt` 落点一致。
**册头/互锁/段号**：21 册册头 ↔ 附录顶部段逐册一致（SimRISC×13=0.5.5-rc、AEE/ABI=0.9.3-rc、SEE/SBI=0.7.2-rc、HEE/HBI=0.1.3-rc、Toolchain=0.5.0、Machine=0.3.0）；互锁组机械核一致；Toolchain-01/Machine-01 **确未变号**（HEAD 既有 0.5.0/0.3.0）。
**正文零改动**：19 册 `git diff` 删除行仅册头版本行 + 无换行符补正（逐册实测）；SimRISC-00/03/11 与 DADAO-21 给出 diff 证据；Toolchain/Machine 仅册头细则 + 旧编号 changelog→附录（授权范围）。
**Toolchain/Machine 合并**：旧 10/5 条全在（唯一 MISS 为 0.3.2 条目重排合并，语义保留）；`x=0` 回改实测「`x=0` 表示尚未正式发布；正式发布后 `x≥1`」（两册）。
**锁**：独立重算 21 册 sha256 全部与 `manifests/spec-readonly.lock.toml` 一致（mismatch=0）、清单与磁盘 21 册互齐；变更文件与完成区「修改文件」对账一致。
**根 README**：「在研版本」列 = `-rc` 顶部段、「已发布版本」列供 `check-spec-drift`（rc=0，未凑绿）；不冲突。
**校验器判定**：`check_spec_changelog` 10 断言逐条有可达 FAIL 路径（6 注入 + 计数现场统计）；`check_numbering` 跳过段自附录起点始——**独立注入②**（附录前插 `### 9.9`）⇒ `check_numbering` rc=1（编号不连续+父节缺失）⇒ 无过度跳过盲区。**独立注入①**（不与 6 项重复）：SimRISC-06 附录后插 `## 9. …` ⇒ `check_spec_changelog` rc=1「附录段之后仍有 ##」+ `run.sh` rc=1 ⇒ `cp` 还原 md5 `db0445ed…`==备份 ⇒ `run.sh` 回绿 rc=0；验收前后 `git status` 快照逐行一致、关键文件 md5 一致。
**finding**：
| # | 级别 | 问题 | 证据 | 整改 |
|---|---|---|---|---|
| B1 | **阻断** | Toolchain-01 `0.2.2（2026-10-02）` 段**漏记** `b0866c8`（09-30 SPEC-057t 全量删除 `rela.si`，实测删该册前身 `docs/spec/assembly-language.md` 的 rela.si 内容）——「与 git 史核对合并（不重复、不丢项）」未达成；全册 `grep rela`=0 | `git log --follow` 该册 29 commit 逐条比对，仅此 1 条语义变更未入录 | 0.2.2 补一条「删除 `rela.si`」→ 重算 Toolchain-01 sha256 入锁 → 重跑 `run.sh` |
| N1 | 非阻断 | `check_numbering`/`check_spec_changelog` 均未入 `make check`（已披露）；且附录后标题仅后者设防 ⇒ 两器须**同批**入门控，否则静默漂移 | Makefile grep 无两器；注入① 实测 | 登记门控候选 |
| N2 | 非阻断 | DADAO 基线段可补导入日期（07-14）增信息量；README「已发布版本＝各册册头发布版本」措辞与册头现为 `-rc` 略有出入；Toolchain/Machine 册头「见文末 changelog」措辞未随附录化更新 | 现场 grep | 措辞小修，随 B1 或下轮 |
**判决：Needs Revision**——仅 B1 一项阻断（内容漏项，改动极小）；其余 11 项核验全绿、约束无违反。返工只需：补 1 条 bullet + 锁重算 + 证据脚本回归。

## 返工 1（B1 + N2）engineer 处置（2026-10-12）

**B1 要点（reviewer 原文）**：`Toolchain-01` 附录 `### 0.2.2（2026-10-02）` 段**漏记** `b0866c8`（09-30 全量删除 `rela.si`，实测改该册**改名/搬运前**路径 `docs/spec/assembly-language.md`）⇒「与 git 史核对合并·不丢项」未达成。

**已补 bullet（落 `### 0.2.2（2026-10-02）` 段，遵册内约定：`- ` 列表、逆序、无表格、不带任务号/ADR）**：
`- 全量删除 `rela.si`（PC 相对寻址指令）及其立即数 4 KiB 单位口径。`
依据：`git show b0866c8 -- docs/spec/assembly-language.md` ⇒ 删 §特例 `rela.si`（立即数左移 12 位）+ §PC相对寻址整节；`git log --follow` 该册 ⇒ `b0866c8 2026-09-30`，版本边界 `0.2.1=09-29 → 0.2.2=10-02` ⇒ 归 `0.2.2` 段。

**同类漏项排查（逐册 `git log --follow`；锁内 10 册含改名）**：
- 改名清单：**1 册跨目录** `docs/spec/assembly-language.md → spec/Toolchain-01`（`93ba173`）；**9 册** `wiki/* → spec/*` 同名搬运（`bb98fff`，09-10）；余 11 册无改名（`890038e` 拆分/新建）。
- 逐册核对**改名前列出的全部 commit** 与段落条目：`SimRISC-00`(49)/`07`(18)/`11`(15)、`DADAO-11/12/13/21/22/23`(16/15/12/19/23/8) 的 wiki 期改动**均已入录**（0.5.x 各段 + `<z+1>-rc` 段；未逐条列名者仅为 `fc3d814` QFC 表重排、`f77d158` 注释等聚合/编辑类）。
- `Toolchain-01` 改名前后 15 条 commit 逐条比对：**仅 `b0866c8` 1 条缺失**（已补）。
- **结论：除 B1 外无其它同类漏项**；证据 `<log>/SPEC-134t-rework-followaudit.txt`（改名审计表 + 改名前 commit 全量）。
- 另注（非改名类，已披露、不改）：`SPEC-133t`（10-11 标题编号）与 `INFRA-060t/063t` 在 `Toolchain-01`/`Machine-01` 既有发布版之后改动，因两册本次**不变号**（用户裁定；reviewer 已核「确未变号」）故未入录，待发布时随 `-rc` 段处理。

**N2 三处措辞（改前 → 改后）**：
- ① DADAO 六册基线段：`（上游基线，日期不详）` → `（上游基线；导入日 2026-07-14，发布日不详）`（`0.9.2`/`0.7.1`/`0.1.2`；导入日 = `3f69139` wiki 导入）。
- ② 根 `README.md`：「已发布版本 = 各册**册头发布版本**」→「＝ 各册**最近一次正式发布版本**（见各册文末「附录：版本与变更记录」，注意**非**册头在研版本）」；已发布版本列（供 `check-spec-drift`）**未动**。
- ③ 册头（`Toolchain-01`/`Machine-01` 各 2 处）：「见文末 changelog」→「见文末「附录：版本与变更记录」」；「版本与 changelog 细则」→「版本与变更记录细则」。

**锁新旧 sha256（仅被改 8 册；全值见 `<log>/SPEC-134t-rework-shas.txt`）**：
`Toolchain-01 13b4e67f…cda7→7ea766cc…0ae1`；`Machine-01 f1f48313…0b78→47c06ffd…5913`；`DADAO-11 53f18d08…1195→317b01ba…34fc`；`DADAO-12 1e4df078…08ba→bd07f59b…4fb9`；`DADAO-13 0d0036c8…49c8→7a4779fb…52eb`；`DADAO-21 f749067c…2478→536f701a…6665`；`DADAO-22 322a00ef…58fa→95c406c8…088b`；`DADAO-23 5b9bca45…011e→5823faa3…d4d`（余 13 册不变）。

**真实输出（采命令自身退出码；明细 `<log>/SPEC-134t-rework-gates.txt`）**：`check_numbering`=0（`files=21 h2=106 h3=163 h4=28 total=297`）；`check_spec_changelog`=0（`files=21 segments=99 rc_segments=19 bullets=222`，较上轮 221 **+1**=本 B1 条目）；`check_spec_readonly`=0（21 volumes OK）；`check_spec_refs`=0；`check_spec_drift`=0；`check_asm_prose --strict`=0；`make check`=0；`<evidence>/run.sh`=0（11 检查 + **7** 注入，末行 `ALL PASS (exit=0)`）。
新增 B1 守卫（`run.sh` §E）：正常 rc=0；注入（删该条目）⇒ **rc=1**、md5 变化=yes ⇒ `cp`+md5 还原一致 ⇒ 回绿（可达 FAIL 已证）。

**改动文件（本返工轮）**：`spec/Toolchain-01-汇编语言.md`、`spec/Machine-01-测试机运行环境.md`、`spec/DADAO-{11,12,13,21,22,23}-*.md`（6 册）、`README.md`、`manifests/spec-readonly.lock.toml`（8 册 sha256 + 授权备注）、`<evidence>/run.sh`（B1 守卫 + TMP 可覆盖）、本任务书。
**范围披露**：`contracts/`、`tests/vectors/`、`.tao/archive/**`、`.tao/tasks/**`（本册除外）、`tools/spec/**` 本轮**未动**；上轮产物（21 册附录、`spec/README.md`、`tools/spec/check_*.py`、`.tao/knowledge/milestones.md`）**保持原样**；**未提交 git**。
**遗留**：B1 ✅已修、N2 三处 ✅已修；未修项 = **无**（N1「两校验器未入 `make check`」为上轮披露的非阻断项，仍为门控候选）。

#### 第 2 轮 engineer 自审（返工 1）
**范围**：本返工轮改动 = `Toolchain-01`（B1 bullet + 册头措辞）、`Machine-01`（册头措辞）、`DADAO-11/12/13/21/22/23`（基线段导入日）、`README.md`（措辞）、`spec-readonly.lock.toml`（8 册 sha256 + 备注）、`<evidence>/run.sh`（B1 守卫 + TMP 可覆盖）。
**逐项审查**：
- 逻辑/准确性：B1 bullet 与 `b0866c8` diff 逐句对应（§特例 + §PC相对寻址整节）；DADAO 导入日 = `3f69139` 各册 log 均含（非推断）。
- 格式：新 bullet 遵册内约定（`- `、逆序、无表格、**无任务号/ADR**）；基线段仍匹配 `SEG_RE`；`check_numbering`/`changelog` 段数/计数现场统计（`segments=99` 不变、`bullets=222` = +1）。
- 防造假：sha256 由 `sha256_file` 同法实测（`check-spec-readonly` 21/21 OK）；注入还原一律 `cp`+md5，**未用** `git checkout/restore/stash`。
- 边界：`--no-inject` 路径亦 rc=0；`awk` 守卫在 `0.2.2` 段缺失时报 FAIL（非恒真）。
**finding 处置**：
| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `run.sh` 注入⑥ sed 仍按**旧**基线段措辞匹配 ⇒ N2① 改后该注入静默失效（互锁注入不命中 ⇒ 自检自伤） | ✅已修 | 同步 sed 新措辞；`TMP` 改为 `SPEC134T_TMP` 可覆盖（默认返工临时目录） | `run.sh` 全量 rc=0（6 注入各 rc=1 + 还原回绿）；`--no-inject` rc=0 |
| F2 B1 内容漏项**无门控覆盖**（结构校验器不查内容） | ✅已修 | `<evidence>/run.sh` §E 增 `b1_toolchain_022_rela_si`（段内 awk 断言）+ 反例注入 | 正常 rc=0；删该条目 ⇒ rc=1、md5 变化=yes ⇒ 还原一致 ⇒ 回绿 |
| F3 越界披露：`<evidence>/run.sh` 不在任务书硬约束清单内 | ⏸披露 | — | 为使「`run.sh` 回归 rc=0」保持有效所必需（否则注入⑥伪绿）；`.work/` 已 gitignore，不入提交文件集 |
| F4 同类漏项排查可审计性 | ✅已修 | 审计表 + 改名前 commit 全量留 `<log>` | `<log>/SPEC-134t-rework-followaudit.txt`（10 改名册 + 190 条 commit） |
**判决**：F1/F2/F4 ✅已修、F3 为披露项（无需改）；全部门控 + `run.sh` rc=0 ⇒ 标 `待验收`。

#### 第 2 轮 reviewer 复验（B1/N2 返工）
**B1 核**：`Toolchain-01` 0.2.2 段已补 bullet「全量删除 `rela.si`（PC 相对寻址指令）及其立即数 4 KiB 单位口径」；依据 `b0866c8`（09-30）触 `docs/spec/assembly-language.md`，diff 删 `rela.si = 4 KiB` 单位注 + `rela.si rb2, 1` 示例，段归属 0.2.1(09-29)→0.2.2(10-02) 正确；格式无任务号/ADR/表格 ✓。B1 回归守卫（`run.sh` awk 断言 ≥1 bullet 含 `rela.si`）+ 反例注入（删 bullet ⇒ rc=1，还原回绿）均实测通过。
**同类漏项**：SimRISC-00（69 commits）+ DADAO-21（26 commits）`--follow` 抽样核——主题归册合理（add.si riii 格式/opcode 调整归 SimRISC-05 0.5.3、cs.*-rf/ft2ft 归 SimRISC-07 0.5.3）；`Toolchain-01` 29 条独立计数仅缺 `b0866c8` 已修；无新阻断项。
**N2 三处**：① 6 册 DADAO 基线段改「（上游基线；导入日 2026-07-14，发布日不详）」✓；② README「已发布版本＝各册最近一次正式发布版本（注意非册头在研版本）」✓；③ 两册「见文末`「附录：版本与变更记录」`」✓。
**锁**：独立重算 21 册 sha256 mismatch=0；8 册新值含 Toolchain `7ea766cc…`/Machine `47c06ffd…`/DADAO-11..23 各更新 ✓；余 13 册 mtime 保留在 round-1 时段 + 未被本轮修改。
**门控**：`make check`=0；`check_spec_changelog`(segments=99, bullets=**222**)=0；`check_numbering`(total=297)=0；`check-spec-readonly`/`check-spec-drift`=0；`run.sh`（**7** 注入 + B1 守卫）rc=0；contracts/tests/vectors/.tao/archive/ 未动。
**正文零改动**：DADAO-21 `git diff` 仅新增附录 + 基线段措辞（附录区内，非正文）✓。
**判定：Accepted**——B1 已修、N2 已修、无新阻断；其余核验保持（门控全绿、21 册格式/互锁/锁/正文均通过）。非阻断建议：`check_numbering`/`check_spec_changelog` 应并入 `make check`（两器不同入门控 ⇒ 附录后标题静默漂移风险仍存）。
