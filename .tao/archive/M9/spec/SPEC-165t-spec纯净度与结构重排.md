# SPEC-165t: spec 纯净度与结构重排（去 v5 痕迹 / 附录归位 / 正文重编号 / `MISC-`→`OPC-`）

**模块**：spec
**项目里程碑**：M9（收尾前，优先于其它动 spec 的册）
**依赖**：`SPEC-160t`（min/max 翻转，已收）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源（用户裁定，2026-10-22）

1. **纯净化**：用户原话「我在查看 SimRISC 的 12 个册子的时候，发现你把很多不属于规范文档的内容塞到了文档中，包括 `scope:fp` 以及 `contract-fp.md` 等；这个事情很严重，我建议先处理一下」⇒ 方案 **A（彻底）**。
2. **结构**：「`附录：版本与变更记录` 集中在 `SimRISC-00` 中，其它分册不再逐一单独记录；汇编指令速查 和 合法性检查 放到每个分册的最后，作为附录出现；汇编指令速查 下面的子标题就一个，没必要」；正文重编号选「重编号（彻底）」。
3. **改名**：「前缀用 `OPC-`；`-AMO` 改为 `-MISC`；其它都不做改动」⇒ 只改 6 个表名，不动编码、不新增 `OPC-AMO`/`OPC-LRSC`、不改 `ALU/FPU/IMM/ARITH` 之类。

## 现场盘点（2026-10-22 实测，执行前须复核）

### 污染面
| 类别 | 命中 | 主要分布 |
|---|---|---|
| `scope:` 标记 | 30 | `07` 17、`00` 5、`12` 3、`01` 2、`11` 2、`03` 1 |
| ADR 指针 | 27 | `00` 7、`04/08/09/10` 各 4、`11` 3、`06` 1 |
| 任务号 | 36 | `00` 10、`07` 7、`08/09/10` 各 5、`04` 4 |
| `contract-*.md` 引用 | 2 | `00` |
| 生成区（`ASSEMBLY_LIST_*`） | 13 册各 1 | 含 `### 1.1 <分类>（N 条）｜ scope: …` 子标题与分类列 |
| `附录：版本与变更记录` | 13 册各 1 | 版本重叠、条目不同 |

**溯源**：`git log -S 'scope: fp' -- spec/` 首条 = `SPEC-086t`（M2 期），之后 `SPEC-087t`/`089t`/`16x` 叠加；`.tao/archive/SimRISC-0.5.3/` 原文零命中。

### 改名面（live 树实测 **417 处**）
`OPC-octa` 223 / `OPC-byte` 120 / `OPC-tetra` 87 / `OPC-wyde` 94 / `OPC-RF` 155 / `OPC-MISC`（含在上述总数内）。分布：`contract-isa.md` 168、`contracts/opcodes.yaml` 46、`spec/SimRISC-00` 24、lit 生成物 46、qemu 补丁注释 32、`tools/**` 30+、`spec/SimRISC-04/09/10` 等。
**归档 `.tao/archive/**` 不改**（历史记录保真）。

## 目标

### 1. 纯净化（方案 A）
`spec/SimRISC-00…12` 只允许：指令定义、编码、格式、语义、异常、revision。
**禁止**：`scope`、里程碑（`M1`/`M9`）、任务号（`SPEC-/QEMU-/LLVM-/INFRA-/TESTCASES-`）、`ADR-`、`ISS-`、`contract-*`、`.tao/`、分桶计数（“`scope: fp` 共 64 条”之类）。

**迁出去向（不新建容器）**：
- `scope` + 分桶计数 → `contracts/opcodes.yaml`（已有）+ `contract-isa.md`「范围表」
- ADR / 契约指针 → `contract-isa.md` 对应行
- 落地记录/任务号 → 各任务书 + `milestones.md`

### 2. 结构归位（固定顺序）
```
# <标题>
> 版本 / 分类（不含 scope）
## 1. …（正文，指令定义/编码/语义）
…
## 附录 A：汇编指令速查      ← 单标题，一张表；无 ### 子标题、无分类列
## 附录 B：合法性检查
## 附录：版本与变更记录      ← 仅 SimRISC-00，且必须是最后一个 ##
```

### 3. 正文重编号
原 `§3…§N` → `§1…§(N−2)`；同步改 `contracts/opcodes.yaml` 的 `spec_cite`（264 条）、`tests/**`（约 162 处）、`.tao/contracts/*.md`、`docs/**`、`contract-isa.md`。
一并处理 `ISS-315`/`ISS-316`/`ISS-192`/`ISS-219`（迁册旧引用 `SimRISC-12 §3.x` → `SimRISC-11 §6.x`）。

### 4. 表名改名（用户 2026-10-22：只此 6 项）
`OPC-octa → OPC-octa`、`OPC-tetra → OPC-tetra`、`OPC-wyde → OPC-wyde`、`OPC-byte → OPC-byte`、`OPC-RF → OPC-RF`、**`OPC-MISC → OPC-MISC`**。
- 依据：`SimRISC-00:201` 已定义 `op` 简称 **opc**（8 位头），这些表正是**按 op 划分**的表族；`AMO` 名不符实（`0x77` 装的是 `fence`/`swym`/`lr`/`sc`，无一条读改写原子操作）。
- **不动编码**：不新增 op、不迁移 `lr/sc`、不拆分 `AMO`/`LRSC`（全留 M10）。
- 范围：live 树全部（含注释、生成物、门控常量）；`.tao/archive/**` 不改。

### 5. 工具与门控同步
- `tools/llvm/gen_asm_list.py`：输出改册尾、去子标题与分类列；
- `tools/spec/gen_legality_list.py`：落附录 B；
- `tools/spec/check_numbering.py`：`## 附录 A：`/`## 附录 B：` 与 `## 附录：版本与变更记录` 一并视为**无编号尾段**；断言正文 §1 起连续、附录 A→B 顺序、changelog（仅 00）是最后一个 `##`；
- `tools/spec/check_spec_changelog.py`：扫描面收窄到 `SimRISC-00`；「互锁组一致」改为比 **13 册册头版本**；
- `check_asm_list_consistency.py` / `check_asm_prose.py` / `check_tables.py` / `check_spec_codeblocks.py`：文本格式同步；
- **新增** `tools/spec/check_spec_purity.py`（L1）：禁用词表 ⇒ FAIL；`--self-test` ≥3 类注入（`scope:` / 任务号 / `ADR-` / `MISC-`）；
- **新增** `tools/spec/check_spec_cite_targets.py`（L1）：`spec_cite` 的「书 + 节标题」必须真实存在（覆盖 `contracts/*.yaml` + `tests/**/*.yaml`）。

## 接口规范

- **输入**：`spec/SimRISC-00…12`、`tools/llvm/gen_asm_list.py`、`tools/spec/**`、`contracts/**`、`tests/**`、`.tao/contracts/**`、`docs/**`、`components/qemu/patches/**`（仅注释）。
- **输出**：纯净化 + 归位 + 重编号 + 改名的 13 册；同步后的引用；2 个新门控；同步后的旧门控。
- **约束**：不改任何**指令语义/编码**；不改 `opcodes.yaml` 记录字段（除 `spec_cite` 节号与注释里的表名）；不 commit/push。

## 验收

1. **纯净度**：`grep -nE 'scope:|ADR-[0-9]|ISS-[0-9]|(SPEC|QEMU|LLVM|INFRA|TESTCASES)-[0-9]+|contract-[a-z]+\.md|\.tao/|MISC-' spec/SimRISC-*.md`（**扫描面仅** `spec/SimRISC-*.md`；不含门控源码 / 任务书）⇒ **0 命中**；`check_spec_purity` rc=0。
2. **改名**：`grep -nE 'MISC-' spec/SimRISC-*.md`（同上扫描面）⇒ **0 命中**；全树替换规模以 `git diff <本任务起点>..HEAD` 的删除行**现场统计**（不写死）。
3. **结构**：`SimRISC-01`…`12`（**12 册**）各以 `## 附录 A：汇编指令速查`、`## 附录 B：合法性检查` 结尾（顺序固定），速查下无 `###`；`SimRISC-00` **无** A/B、仅 `## 附录：版本与变更记录`（且为最后一个 `##`）。
4. **重编号**：每册正文 `## 1.` 起连续；`check_numbering` rc=0。
5. **引用完整性**：`check_spec_cite_targets` rc=0；`validate-vectors`、`check_contracts_dir`、`check-spec-refs` rc=0。
6. **语义零漂移**：`git diff` 中指令表行/语义段落逐行相同（仅位置/编号/表名变化）；`check_tables`、`check_asm_list_consistency`、`check-legality-*`、`check_scope`、`check_fp_contract` 全绿。
7. **可达 FAIL ≥4**：① 塞 `scope: fp` ⇒ purity 红；② 塞 `MISC-octa` ⇒ purity 红；③ 附录 A 挪回册首 ⇒ numbering 红；④ 改一条 `spec_cite` 节号 ⇒ cite_targets 红。
8. 收尾：`make check`(L1) + `make check-modules`(L2) 绿；`ISS-315/316/192/219` 按实际结果关闭。

## 风险与纪律

- **体量**：13 册 + 417 处改名 + 约 400 处引用重编号 ⇒ 先建**映射表**（旧节号→新节号、旧表名→新表名）落 `.work/`，再机械替换，禁手改。
- **串行**：本册期间禁止其它册改 `spec/**`（FMA 链等全部后置）。
- **逐册自检**：单册失败不污染其它册。
- `spec/` 改动已获用户 2026-10-22 授权（原话见「立项来源」）。

## 完成区

**测试结果**：`make check`(L1) rc=0；`make check-modules`(L2) rc=0；`./.work/evidence/SPEC-165t/run.sh --inject` rc=0（16/16 PASS，含 4 类注入；`run.log` = 该次真实输出）。
**修改文件**：13 册 `spec/SimRISC-00…12`；`spec/README.md`（册维护约定）；门控 `tools/llvm/gen_asm_list.py`、`tools/spec/{gen_legality_list,check_numbering,check_spec_changelog,check_asm_list_consistency,check_tables,check_qfc_coverage}.py` + 新增 `tools/spec/{check_spec_purity,check_spec_cite_targets}.py` + `Makefile`（L1 加 2 项）；引用/改名面 `contracts/opcodes.yaml`、`tests/**`、`.tao/contracts/**`、`docs/**`、`tools/**`、`components/**`（含补丁注释 + `.work/source` 同步）；`manifests/spec-readonly.lock.toml`（13 册 sha256 + 授权记录）；`contract-isa.md §0 范围表`；`issues.yaml`（ISS-315/316/192 关闭）。
**验收结果**：
- 纯净度 `grep -nE 'scope:|ADR-|ISS-|任务号|contract-*.md|.tao/|MISC-|v5' spec/SimRISC-*.md`（扫描面**仅** 13 册）⇒ **0 命中**；`check-spec-purity: files=13 rules=11 hits=0`
- 改名 `grep -nE 'MISC-' spec/SimRISC-*.md`（同上扫描面）⇒ **0**；`git diff a8365daa..HEAD` 删除行现场统计：旧名被替换 **485** 处
- 结构：**12 册**（01–12）各 A→B、速查内 `###`=0、无分类子标题；`SimRISC-00` 仅 changelog 且为末段
- `check-spec-cite-targets: yaml_files=32 spec_cite_lines=1819 unresolved=0`；`check-spec-numbering` / `check-spec-changelog` / `check-asm-list-consistency`(12 册) / `check-legality-drift`(12 册) / `check-tables`(101 条/256 格) / `check-spec-codeblocks`(668 行) / `check-asm-prose` 全 PASS
- 语义零漂移：13 册表格行 multiset 逐册 **−0/+0**；正文 diff 仅表名 / 节号 / 纯净度改写
- 可达 FAIL 4 类（真实报错）：`scope` ⇒ `[范围标注 scope] 'scope'` rc=1；`MISC-` ⇒ `[旧表名 MISC-] 'MISC-'` rc=1；附录 A 挪回册首 ⇒ `正文无任何带编号 ## 节` rc=1；`spec_cite §9.99` ⇒ `在 spec/ 中不存在` rc=1；`cp`+md5 还原 `5647841a…` 后 numbering 回绿
**新发现/坑**：
1. `git ls-files` 默认 `core.quotepath=true` ⇒ 非 ASCII 路径被转义，`Path.read_text` 静默跳过整个 `spec/`（首轮改名漏 13 册）；须 `-c core.quotepath=false ls-files -z`（同 lessons §2.19）。
2. 组件补丁**注释**改名会破 `check-patch-tree` ⑥/⑨：补丁须与 `.work/source/<comp>` 的 base+1 commit 逐字节一致 ⇒ 必须同笔改源树 + `commit --amend` + 重新 `git diff` 生成补丁。
3. 组件源一变 ⇒ `build-mc`/`build-builtins` 链重编、clang build-id 变 ⇒ `check-musl-freshness` 红；须 `make build-musl-shared` 重装（本轮做了 2 次：首次后 LLVM 重编又变）。
4. `check_qfc_coverage` 把子表名写死在正则 ⇒ 改名后静默降级（92 条假差异）；已同步 `OPC-`（恢复为 2 条真差异）。
**遗留问题**：① `.tao/archive/**` 不改（历史快照保真）；`spec/README.md` 与 `.tao/contracts/**` 已同步，但 ADR / `issues.yaml` / 旧任务书正文里的`§N` 旧编号**未全量改写**（历史记录；已改写处均指向现节号），悬空点见 `.work/log/spec/SPEC-165t-L1.log` 之外的 `git grep` 复核；② `check_qfc_coverage` 2 条 M1 内差异 = `cs.eq_rrrr_rf`/`cs.ne_rrrr_rf` 仍在 QFC 主表格位（`SPEC-163t` 遗留，归 `SPEC-157t` FMA 落位）；③ `ISS-219`（contract 互指 13 条悬空）复核仍在，维持 open；④ `check_asm_prose`/`check_spec_codeblocks` 无需改动（按生成区 marker 跳过，与位置无关），已实跑绿；⑤ `.work/source/llvm-project` 一行注释仍写 `§4.1/§3.2`（改它须再重编 LLVM + 重装 musl，收益不抵成本）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-22）

逐行复核改动源码（生成器 / 4 个门控 / 2 个新门控 / 3 个机械脚本）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 改名首轮 `git ls-files` 未禁 `quotepath`，13 册 `spec/` 被静默跳过 | ✅已修 | `rename.py` 改 `-c core.quotepath=false ls-files -z` | 二次运行命中 82 处；C2 grep = 0 |
| F2 组件补丁只改 `.patch` ⇒ ⑥/⑨ 红（40 问题） | ✅已修 | 新增 `sync_component_sources.py`：改源树→`commit --amend`→`git diff` 重生成 15 个补丁 | `check-patch-tree: 5 component(s), 192 patches OK` |
| F3 `check_numbering` 原逻辑「见附录即跳过其余全文」会把「A 挪回册首」判成 PASS | ✅已修 | 重写：正文=首个无编号尾段之前，断言正文非空 + 自 `§1` 起连续 + 尾段后禁带编号 `##` | 注入 I3 rc=1、还原后 rc=0 |
| F4 `check_spec_cite_targets` 自检曾用行内偏移当全文偏移（假绿） | ✅已修 | 按整行替换注入 + 仅取含 `spec_cite` 的行 | 自检 broken-cite rc=1 |
| F5 证据脚本 `check()` 参数位错（`--` 被当命令）⇒ 全部 rc=127 却"PASS" | ✅已修 | 调用改 `check <名> <期望> <说明> -- cmd`，`shift 4` | 重跑 C4–C9 均 rc=0 且打印真实 rc |
| F6 `echo "…\`scope: fp\`…"` 反引号被 shell 求值 | ✅已修 | 改用单引号 | I1/I2 输出正常 |
| F7 历史任务书被改名/节号同步（是否越界） | ❌不修 | 保留：任务书改名面为「live 树」且仅排除 `.tao/archive`；diff 核对仅表名/节号指针变化，结论未改 | `git diff .tao/tasks` 逐行核对 |
| F8 `check_qfc_coverage` 在改名后静默降级（92 假差异） | ✅已修 | `MISC_PTR`→`OPC_PTR` 及两处正则/注释 | 现场 2 条真差异（FMA 遗留） |

### 第 1 轮 reviewer 验收（2026-10-22，全部本人独立重跑）

**重跑记录（命令 → 真实输出 / 退出码）**
- 纯净度：`grep -nE 'scope:|ADR-[0-9]|ISS-[0-9]|(SPEC|QEMU|LLVM|INFRA|TESTCASES)-[0-9]+|contract-[a-z]+\.md|\.tao/|MISC-' spec/SimRISC-*.md` ⇒ 0 命中（rc=1）；`check_spec_purity` rc=0 `files=13 rules=11 hits=0`；`--self-test` rc=0（5 类注入各报 FAIL）
- 结构：`01–12` 各以 `## 附录 A：汇编指令速查` → `## 附录 B：合法性检查` 收尾且为末两个 `##`、A 内 `###`=0；`## 附录：版本与变更记录` 仅 `SimRISC-00` 且是其最后一个 `##`（SimRISC-00 无 A/B，见 findings①）
- 重编号 + 引用：`check_numbering` rc=0；`check_spec_cite_targets` rc=0 `spec_books=21 yaml_files=32 spec_cite_lines=1819 unresolved=0`；独立解析抽 5 条全部命中标题（06 §条件跳转指令 / 04 §比较操作 / 01 §存取RA寄存器 / 00 §压栈流程 / 03 §立即数常数赋值），复合引用 `SimRISC-00 §返回地址栈 §C1` 亦命中 `### 2.4 返回地址栈`
- 门控：`make check`(L1) rc=0（`L1_EXIT=0`，日志 214–217 行＝2 个新门控真跑）；`make check-modules`(L2) rc=0（`L2_EXIT=0`，全量无 FAIL）；`check-patch-tree` rc=0 `192 patches OK`；`check-musl-freshness` rc=0；`check-builtins-freshness` rc=0
- 改名（现场统计，未写死）：旧名@`0e7662d5~1`=**485**（octa145/tetra54/wyde54/byte58/RF126/AMO48）、新名@工作树=**490**（147/57/57/60/122/47，同排除面），与完成区 485/490 逐项一致；`.tao/archive` 改动文件=0；按验收②字面（仅排 archive/work/cache）`grep 'MISC-'` ⇒ **11 行 / 2 文件**（判 2）
- 独立注入（`cp`+md5 还原，未用 `git checkout/restore/stash`）：① `SimRISC-12` 第 6 行插 `> **scope: fp**` ⇒ purity **rc=1** `hits=1 by_rule={'范围标注 scope':1}` → 还原 md5 `0aa93995…` 相等 → rc=0；② `SimRISC-05` 附录 A 挪到 `## 1.` 之前 ⇒ numbering **rc=1** `正文无任何带编号 ## 节`+`附录段之后出现带编号 ## 节` → 还原 md5 `a8be4752…` 相等 → rc=0；验收前后 `git status --porcelain -uall` 逐行对账一致（均仅 ` M Makefile`，SNAPSHOT_IDENTICAL）

**语义零漂移（`git diff 0e7662d5~1..0e7662d5 -- spec/`，13 册逐册）**
- 指令表行数 前/后：00 **121/121**、01 **40/40**、02 **18/18**、03 **10/10**、04 **74/74**、05 **8/8**、06 **17/17**、07 **72/72**、08 **39/39**、09 **39/39**、10 **39/39**、11 **48/48**、12 **4/4**（逐册差 0；含助记符的指令语义行 237→237）；表行 multiset（归一 `MISC-AMO→OPC-MISC`、其余 `MISC-→OPC-`）逐册 **旧独有 0 / 新独有 0**
- 删除行分类（行 multiset 差 719 条）：changelog 区 **433**（列表194/标题79/引言12/空行148 ＝ 各册变更记录并入 00，允许）；正文区 **286** ＝ 标题133（重编号改号，归一后正文标题**丢失 0**；每册消失的 3 个结构标题＝`## 汇编指令速查`/`## 合法性检查` 改为附录 A/B ＋ 速查 `### <分类>（N条）` 子标题，目标§2 允许）+ 列表19 + 引言16 + 段落66 + 表格2 + 空行50
- 正文『非标题』消失行 103 条逐条判：**43 条为净化改写存活**（抽 39 条逐字比对，语义全留，只删 `ADR-xxxx`/`SPEC-069t`/`QEMU-xxx`/`scope`/`v5`，或 `v5`→`本版`、`SPEC-069t 高位规则`→`高位规则`、§4.2→§2.2）；余 **21 条** ＝ `---` 分隔线13 + 空引行1 + scope/分桶总账3（00 L290/L291、07 L6，允许删）+ 残留括注 `（ADR-0032 D3/D4）。`3（同句主体存活）+ 11 L110（改写后「未实现 ⇒ 触发 ILLI」语义仍在）⇒ **指令行与语义段落零删改**
- 越界核查：`contracts/opcodes.yaml` 改动 142 行 **100% 是 `spec_cite`**；`tests/**` 改动 460 行 ＝ spec_cite 127 对 ＋ 注释里的书名/节号/表名 ⇒ 未动编码与期望值（合「接口规范-约束」）

**判决：Needs Revision** —— 语义零漂移、纯净度、结构、重编号、引用、6 项门控 rc 全部通过；阻断项均为「断言/计数与现场不符」：
1. **证据脚本 C2 提交后不可复现（假绿）**：本人原样重跑 `run.sh:39` `git grep -n 'MISC-' -- . ':!.tao/archive' ':!.tao/tasks' ':!.work' ':!.cache'` ⇒ **rc=0、命中 4 行**（`tools/spec/check_spec_purity.py:8,15,45,102`）⇒ 现跑 run.sh 必进 else 分支 FAIL，而 `run.log` 记 `C2 rc=1 hits=0`、`PASS=16 FAIL=0`。根因实证：`git grep`（无 rev）**不搜未跟踪文件**（探针：未跟踪 rc=1 / staged rc=0）；门控 21:59:36 建、22:54:31 跑证据、22:55:30 才提交 ⇒ 跑时不可见。**改法**：C2 改工作树 `grep -rn`（含未跟踪）并对 `tools/spec/check_spec_purity.py` 的禁用词表/自测夹具设白名单（或只匹配六个旧名 `MISC-(octa|tetra|wyde|byte|RF|AMO)`）；C2b 的 OLD 计数改 `git grep <旧名> 0e7662d5~1`（现 `git diff HEAD` 恒 0）；修后重跑 run.sh 出 16/16。
2. **验收② / 完成区「live 树 `grep -rn 'MISC-'` ⇒ 0」与现场 11 行不符**（本任务书正文 7 行 ＋ 上述门控 4 行）：验收措辞须写明豁免面（`.tao/tasks`、门控自身文件）或改写规则串避免自触发，完成区该行同步订正。
3. **提交不完整**：`Makefile`（L1 挂载 2 个新门控）仍是未提交改动（`git status`＝` M Makefile`；`git show 0e7662d5:Makefile` 查无 `check-spec-purity`）⇒ 提交态 `make check` 不含新门控、与完成区「修改文件」不符，须 architect 补提交（reviewer 无提交权）。

**findings（不阻断）**：① SimRISC-00 无附录 A/B、以 changelog 收尾（合 `check_numbering` 规则8 与任务书目标§2，但与验收③「13 册均 A→B」表述冲突，以任务书正文为准）；② 净化改写措辞降级 3 处（00/04「`xnor.b/w/t` 已随 `SPEC-069t` 删除」→「窄位宽 `xnor` 已删除」等）与 `（ADR-0032 D3）` 括注删除，编码/语义未变；③ 同步改名面 126 文件含 `.tao/adr`/`.tao/contracts`/组件补丁注释，与任务书「live 树」授权一致。
**采信**：`validate-vectors`/`check-scope`/`check-fp-contract`/`check-tables`/`check-legality-*`/`check-asm-*` 未单独重跑，采信其被 L1/L2 覆盖（我重跑 L1/L2 rc=0 且日志无 FAIL）。


### 第 2 轮 engineer 返工（2026-10-22，按 reviewer Needs Revision）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| B1 证据 C2 提交后不可复现（`git grep` 不搜未跟踪文件；且扫描面含门控源码 ⇒ 原样重跑命中 4 行） | ✅已修 | `run.sh` C2 改 `grep -nE 'MISC-' spec/SimRISC-*.md`（扫描面与 `check_spec_purity` 一致，**不**用 `git grep`、**不**靠排除门控文件）；另加「扫描面前置」防 glob 未展开；C2b 旧名计数改 `git diff $(git merge-base HEAD master)..HEAD` 删除行 | `./run.sh --inject` rc=**0**，`PASS=16 FAIL=0`；C2 `实际_rc=1 hits=0`；C2b `旧名被替换=485 处`；`run.log` 已更新为该次真实输出 |
| B2 验收② / 完成区「live 树 `grep -rn 'MISC-'` ⇒ 0」与现场不符（任务书自身 + 门控源码 11 行） | ✅已修 | 验收② 改为 `grep -nE 'MISC-' spec/SimRISC-*.md` + `git diff` 现场统计；验收① 明示「扫描面仅 13 册」；完成区「改名」行同步 | 现场 `grep -nE 'MISC-' spec/SimRISC-*.md` ⇒ rc=1 / 0 行 |
| B3 验收③「13 册均 A→B」与现场不符（00 无 A/B） | ✅已修 | 验收③ 改「**12 册**（01–12）A→B；`SimRISC-00` 无 A/B、仅 changelog 且为末段」；完成区「结构」行同步 | `check_spec_numbering`：`appendixA=12 appendixB=12 changelog=9` rc=0 |
| B4 验收⑦注入措辞残留改名后名称（`OPC-octa`） | ✅已修 | 恢复为 `MISC-octa`（注入的是**旧名**） | 证据 I2 命中 `[旧表名 MISC-] 'MISC-'` rc=1 |
| B5（reviewer 阻断 3）`Makefile` 未提交 | ⏸不由本角色处置 | architect 已补提交 `3a8a7319` | `git log -1 --stat` 含 `Makefile` |

### 第 2 轮 reviewer 验收（2026-10-22，仅复验上轮 3 条阻断 + 抽核，全部本人独立重跑）

- **阻断1（证据可复现）**：`bash .work/evidence/SPEC-165t/run.sh --inject` ⇒ **rc=0、`PASS=16 FAIL=0`**，输出与提交的 `run.log` **逐字节一致**（`diff` rc=0；run1/run2/run.log 三方 md5 同 `9b5d362a…`）⇒ 二次重跑一致。C2 扫描面核实＝`run.sh:48 grep -nE 'MISC-' spec/SimRISC-*.md`（**只** 13 册，不含门控源码/任务书），本人独立复跑 rc=1 / 0 命中；脚本内无 `git checkout/restore/stash/show`（还原用 `cp`+md5）。C2b 独立重算 `git diff -U0 a8365daa..HEAD -- . ':!.work' ':!.tao/tasks'` 删除行旧名 = **485**（octa145/tetra54/wyde54/byte58/RF126/AMO48）＝run.log 与完成区。
- **独立注入**（`cp` 备份 + md5，未用 git 还原）：`SimRISC-07` L7 插 `> **scope: fp**` ⇒ `check_spec_purity` **rc=1** `hits=1 by_rule={'范围标注 scope':1}` → 还原 md5 `2e6c6a9d…` 相等 → 回绿 rc=0。
- **阻断2/3（表述与现场一致）**：验收③/完成区「12 册（01–12）各 A→B、速查内无 `###`；`SimRISC-00` 无 A/B、仅 changelog 且为末段」＝实测（逐册 A=1 B=1 CL=0，末 `##` 均为附录 B；00 为 A0 B0 CL1、末 `##`＝changelog）；验收①② grep 均**限定** `spec/SimRISC-*.md`，实测 rc=1 / 0 行；「485 处」＝现场统计。`check_numbering` rc=0 `appendixA=12 appendixB=12`。
- **抽核**：`make check`(L1) **rc=0**（日志 214–217 行＝2 个新门控真跑，无 FAIL）；`check_spec_purity`（`files=13 rules=11 hits=0`）/`check_spec_cite_targets`（`spec_cite_lines=1819 unresolved=0`）/`check_numbering` 均 rc=0。语义零漂移抽查 01/07：表行 前/后 **40/40**、**72/72**，归一改名后 multiset 旧独有 0 / 新独有 0。`git show HEAD:Makefile | grep check-spec-purity` 命中（57/175/720/757 行）。验收前后 `git status --porcelain -uall` 快照 + 13 册 md5 对账**一致**（仅本审阅记录新增改动）。
- **采信**：`make check-modules`(L2) 与 `validate-vectors`/`check-legality-*`/`check-tables` 等未单独重跑，采信上轮本人重跑 `L2_EXIT=0` 及本轮 L1 rc=0（本轮返工提交仅动任务书 42+/8−，未触 `spec/`）。
- **判决：Accepted** —— 3 条阻断全部消除，验收命令块在本人重跑下全绿、约束无违反。
