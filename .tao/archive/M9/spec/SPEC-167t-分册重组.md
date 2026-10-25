# SPEC-167t: 分册重组（11=核芯功能扩展 / 12=其它指令 / 非法指令并入 00）

**模块**：spec
**项目里程碑**：M9（收尾前）
**依赖**：FMA 链已完成（`SPEC-158t`/`TESTCASES-058t` 均验证）；`LLVM-126t`/`129t` 不触 spec
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源（用户裁定，2026-10-22/23）

- 「带 cfx 的指令，是否应该叫特权指令」→ 规范原文：`trap/escape/cfx2rd/cfx2rc/cfxld/cfxst` **可在任意运行模式执行**，是否允许由 cfx mask 控制 ⇒ "特权"名不符实
- 「`SimRISC-11` 改为核芯功能扩展指令分册，就放带 cfx 的 6 条指令；`SimRISC-12` 改为其它指令，把 `ct*` 指令移动到该分册，新开一节；`cfxld/cfxst` 移动到新的 `SimRISC-11` 中，注明待定」
- 「可以」（确认归属：`swym`/`fence`/`lr`/`sc` → 12；ILLI/UNDI 规则 → 00）
- 「`swym` 叫占位指令并不合适」→ 「**空转指令**」（体现 `swym N` 的时延语义；`N=0` 为空操作）

## 目标结构（最终形态）

```
SimRISC-00  指令系统设计
   § 编码布局 / 寄存器 / 异常规则（原 11 §2 ILLI/UNDI 并入）
SimRISC-11  核芯功能扩展指令
   trap / escape / cfx2rd / cfx2rc / cfxld(待定) / cfxst(待定)
SimRISC-12  其它指令
   §1 原子指令（fence / lr.* / sc.*）
   §2 空转指令（swym；N=0 为空操作，N>0 为时延）
   §3 位扫描与位计数（ctlz / cttz / ctpop；有效位宽由 hd 决定）
```

## 具体改动

1. **文件重命名**（git mv，保留历史）：
   - `spec/SimRISC-11-其它.md` → `spec/SimRISC-11-核芯功能扩展指令.md`
   - `spec/SimRISC-12-待定.md` → `spec/SimRISC-12-其它指令.md`
2. **SimRISC-11**：只留 cfx 6 条（`trap`/`escape`/`cfx2rd`/`cfx2rc`/`cfxld`/`cfxst`），`cfxld`/`cfxst` 标 **待定**（`deferred`）；删除"特权指令"提法，标题与首段按"任意模式可执行、cfx mask 控制"重写。
3. **SimRISC-12**：迁入 `fence`/`lr`/`sc`（原 11 §4）、`swym`（原 11 §1，节名改**空转指令**）、`ct*`（原 04 §2.2.2，新节**位扫描与位计数**）；`SimRISC-04` 删除 `ct*` 小节并留一句跨册指引（手册名 + 小节标题，不带 §）。
4. **SimRISC-00**：并入原 11 §2 的 ILLI/UNDI 规则（编码→异常的总规则），与既有"异常"章合并去重。
5. **引用同步**：`contracts/opcodes.yaml` 的 `spec_cite`（`fence`/`lr`/`sc`/`swym`/`ctlz`/`cttz`/`ctpop` 由 `SimRISC-11`/`04` 改指新册）；`tests/**` 同类引用；`spec/README.md` 索引；`manifests/spec-readonly.lock.toml` 重算。
6. **生成物**：各册附录 A/B 重生成（`gen_asm_list --embed-spec`、`gen_legality_list --apply`）；`check_tables` 的册名映射同步。
7. **门控**：`check_spec_numbering`（册名/编号不变，仅内容重排）、`check_spec_changelog`（互锁组按册名读取，确认不受影响）、`check_spec_cite_targets`（助记符→新册附录 A）。

## 验收

1. **结构**：11 册只含 cfx 6 条（`grep -c` 指令行 = 6，`cfxld`/`cfxst` 标 `待定`）；12 册含原子/空转/位扫描三节；04 册无 `ctlz/cttz/ctpop` 小节但有一句跨册指引。
2. **引用**：`grep -n "SimRISC-0[0-9]: \(fence\|lr\.\|sc\.\|swym\|ctlz\|cttz\|ctpop\)" contracts/opcodes.yaml` 全部指向新册；`check_spec_cite_targets` rc=0；`grep -rn 'SimRISC-1[12] §' spec/ tests/ contracts/` ⇒ 0。
3. **纯净度**：`check_spec_purity` rc=0（不得因搬迁带入 `scope`/任务号）。
4. **语义零漂移**：逐条比对搬迁前后指令语义段（应逐字相同，仅位置变化）。
5. **门控**：`check_tables`（6 表）、`check_asm_list_consistency`、`check-asm-prose`、`check-spec-numbering`、`check-spec-changelog`、`check-spec-readonly`、`check-instrinfo`、`check_qemu_trans --strict`（266/266）、L1、L2 全绿。
6. **可达 FAIL ≥3**：① 把 `fence` 留在 11 ⇒ 结构断言红；② `ctlz` 的 `spec_cite` 仍指 04 ⇒ cite_targets 红；③ 12 册重新出现 `占位指令` 节名 ⇒ 结构断言红。

## 接口规范

- **输入**：`spec/SimRISC-{00,04,11,12}`、`spec/README.md`、`manifests/spec-readonly.lock.toml`、`contracts/**`、`tests/**`、`tools/spec/**`、`tools/llvm/gen_asm_list.py`。
- **输出**：重排后的 4 册 + 索引 + 锁 + 引用 + 生成物 + 门控适配。
- **约束**：**不改任何指令语义/编码**；不新增/删除指令；不 commit/push；临时目录 `/tmp/opencode/SPEC-167t/`。

## 风险与纪律

- 册重命名牵动 `manifests`、`README`、门控册名映射，**先全局 `grep` 出所有引用点**再动手。
- 搬迁语义段前后必须**逐字比对**（`diff`），禁借机改写。
- 若发现 `SimRISC-00` 已有等价异常规则 ⇒ 合并去重，不重复写。

## 完成区

**测试结果**：证据脚本 `.work/evidence/SPEC-167t/run.sh` 默认 **PASS**；`--inject` **48 PASS / 0 FAIL**（3/3 注入可达 FAIL 且 `cp`+md5 还原回绿）。门控 20/20 rc=0（见下）。
**修改文件**：
- `spec/`：`SimRISC-11-其它.md`→`SimRISC-11-核芯功能扩展指令.md`、`SimRISC-12-待定.md`→`SimRISC-12-其它指令.md`（`git mv`）；`SimRISC-00`、`SimRISC-04` 正文/生成区；`spec/README.md`。
- `contracts/opcodes.yaml`（31 条 `spec_cite`）、`contracts/legality_rules.yaml`（注释）；`.tao/contracts/contract-asm-list.md`（重生成）、`contract-isa.md`、`contract-see.md`；`manifests/spec-readonly.lock.toml`；`docs/Process-06`（册名示例）。
- `tools/`：`llvm/gen_asm_list.py`（classify/册映射/分章文案）、`spec/generate_opcodes.py`、`spec/generate_bitcnt_vectors.py`、`infra/check_spec_{refs,drift}.py`（册名映射）、`qemu/generate_atomics_vectors.py`、`qemu/min_rom_probe_044t/045t.py`、`testcases/{generate_misc,generate_lit_vectors,validate_m5_vectors}.py`。
- `tests/`：10 处注释引用（m5/lit/scripts）；重生成 `vectors/{atomics/*,bitcnt,isa/misc}.yaml`、`lit/MC/DADAO-gen/gen-{oiii,orri,orrr,excluded}.s`、`gen-fast.s`。
- `.work/evidence/SPEC-167t/{run.sh,inject.py}`。
**验收结果**（真实 rc，均现场重跑）：
- 结构：11 附录 A 指令行 **6**（含 `cfxld`/`cfxst` 两条「待定」标注）；12 三节（原子/空转/位扫描与位计数）+ 附录 A **29** 行；04 无 `ct*` 小节、留 1 句跨册指引；00 有「6.1 非法指令 / 6.2 保留编码」。
- 引用：`grep -nE "SimRISC-0[0-9]: (fence|lr\.|sc\.|swym|ctlz|cttz|ctpop)" contracts/opcodes.yaml` 29 行全指 `SimRISC-12`；`grep -rnE 'SimRISC-1[12] §' spec/ tests/ contracts/` = **0**；`check_spec_cite_targets` rc=0（unresolved=0）。
- 门控：purity / tables(6 表 177 条) / asm_list_consistency(12) / asm_prose --strict / numbering / spec_changelog / spec_readonly(21) / spec_refs(1053 引用 0 失败) / spec_drift / asm_list_drift / legality_drift(12) / spec_codeblocks(661) / instrinfo(0 errors) / qemu_trans --strict(**266/266**) / validate_encoding(266) / validate_vectors(706) / bitcnt --check —— 全 rc=0。
- 语义零漂移：搬迁段对 `master` 逐字 diff——atomic 93 行、swym 16 行、bitcount 45 行、cfx3 56 行、sram 21 行**全等**（仅标题/编号 + 用户裁定的「占位→空转」两处措辞）；ILLI/UNDI 逐句并入 00。
**新发现/坑**：① `gen_asm_list --embed-spec` 会重写全部 12 册并在标记前多留 2 空行（必须备份后只回填 04/11/12，`check_legality_drift` 断言 A/B 间隔 ≤1 空行）；② `check-contracts-pending` 会拦生成契约里裸「待定」⇒ 生成器文案改 `deferred`；③ 证据断言若只按 cfx 助记符计数，注入 `fence` 行不可达 FAIL（须加「附录 A 全部行数」）；④ `check_spec_refs` 只校验 `.tao/contracts/*.md` 的 `[手册 §节]` 形——换册/换节名必须同笔改，否则 L1 红。
**遗留问题**：① `components/{qemu,llvm-project,musl}/patches/**` 注释仍写旧册名/`§4.1`/`§特权指令`（改注释须走 Process-01 重导补丁 + 重建，本任务不动；建议随下次组件变更顺带）；② `.tao/adr/adr-0020`、`.tao/contracts/contract-see.md:5` 的旧册名为历史溯源（0.5.4 时点名），按 ADR 不可改纪律保留；③ `.tao/knowledge/{MEMORY,milestones,issues}.md` 的 `SimRISC-11 §fence指令/§LR-SC指令/§特权指令` 引用待主会话 `/complete` 统一改指（知识库由主会话维护）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-24）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 生成器重写全部 12 册并多留空行 | ✅已修 | 备份 `.bak` 后 `cp` 还原 01–10；04/11/12 规范化 A 标记前空行 | `git status` 仅 4 册；`check_legality_drift` rc=0 |
| F2 生成契约「分章」行裸「待定」触 `check-contracts-pending` | ✅已修 | `gen_asm_list` 文案改 `deferred` 并重生成 | 该门控 rc=0 |
| F3 tests 首轮替换残留 `SimRISC-12 §原子指令` | ✅已修 | 二次正则去 `§` | `grep -rnE 'SimRISC-1[12] §'`=0 |
| F4 注入①（fence 留 11）不可达 FAIL | ✅已修 | 证据脚本增「11 附录 A 全部指令行 == 6」 | `--inject` 注入① actual=1 |
| F5 12 附录行数统计误计正文表格（38） | ✅已修 | 改 awk 限定附录区段 | actual=29 |
| F6 `spec_cite` 计数正则漏 `lr.*/sc.*` 后缀（5≠29） | ✅已修 | 正则补 `\.[a-z][a-z]` | actual=29 |
| F7 `SECTION_TITLES` 空壳 / `CONTRACT_BADGES` 孤儿 | ✅已修 | 删除死代码，直接用 `cls` | `check_asm_list_drift` rc=0 |
| F8 `.tao/contracts` 旧 `§特权指令/§占位指令/§非法指令/fence/LR-SC/SRAM` 引用 28 处 | ✅已修 | 逐条改指新册新节（`行首/表格/正文`全覆盖） | `check_spec_refs` 1053 引用 0 失败 |
| F9 组件补丁注释、历史 ADR/来源行旧册名 | ⏸延后 | 未改（属 Process-01 重建面 / 历史溯源） | 已登记「遗留问题」① ② |
| F10 `.tao/knowledge` 台账引用 | ⏸延后 | 未改（知识库由主会话 `/complete` 维护） | 已登记「遗留问题」③ |

自审结论：改动面与任务书一致；指令语义/编码零变更（`contracts/opcodes.yaml` diff 仅 31 条 `spec_cite` + 1 行生成头注释）；无未修 finding ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-10-24，工作树快照前后对账一致：11 个 M 文件，md5 无漂移）

**重跑记录（我自己的输出/rc）**：`bash .work/evidence/SPEC-167t/run.sh` ⇒ rc=0（结构 13 断言、引用 4 断言、12 门控 GATE rc=0、语义零漂移 5 段+illi-undi 全 PASS）；逐个重跑 `check-spec-numbering`/`check-spec-changelog`/`check-spec-purity`/`check_tables.py`(6 表 177 条)/`check-asm-list`/`check-spec-readonly`(21 册)/`check-instrinfo`(0 errors)/`check_qemu_trans --strict`(**266/266**)/`validate-vectors`(706 cases)/`check-spec-cite-targets`(unresolved=0) ⇒ 均 rc=0。
**独立注入**：`spec_cite 'SimRISC-12: ctlz'`→`SimRISC-04: ctlz`（`cp` 备份+md5 前后对账）⇒ run.sh rc=1（指向 12 计数 28≠29、cite_targets rc=1）；`cp` 还原 md5 相等 ⇒ 回绿 rc=0。
**结构**：11 附录 A 指令行=6（cfxld/cfxst 标「待定」，正文含 deferred 说明）；11 无「特权指令」提法；12 三节（原子/空转/位扫描与位计数）+附录 A 29 行；04 无 ct* 小节、留跨册指引（不带 §）；00 §6.1/6.2 并入 ILLI/UNDI。
**语义零漂移（对 `4070c563~1` 我自己逐段 diff）**：atomic 93 行、swym 16 行、bitcount 45 行、cfx3 56 行、sram 21 行——差异仅标题编号 + 用户裁定的「占位→空转」两处措辞 + sram 节「待定」提示行，正文逐字相同。
**引用**：opcodes.yaml 29 条 fence/lr.*/sc.*/swym/ctlz/cttz/ctpop `spec_cite` 全指 `SimRISC-12`；`grep -rn 'SimRISC-1[12] §' spec/ tests/ contracts/`（限定源文件）=0；锁文件 21 条 sha 现算 0 失配；README 索引、Process-06 册名单已同步；opcodes 指令记录 665=665，增删=0。
**⚠ 阻断（门控红，提交快照）**：`git worktree` 干净检出 `4070c563` 重跑 ⇒ `check_spec_refs` **rc=1（29 violations）**、`check_asm_list_consistency` **rc=1（3 inconsistencies，仍指 `SimRISC-11-其它.md`/`SimRISC-12-待定.md`）**——完成区声明的 11 个 `tools/*.py` 改动**未包含在提交内**，仅以未提交形式存在于工作树（`git diff 4070c563 -- tools/` = 11 文件）。修复：architect 在分支内补提交这 11 个文件后重验；工作树交付物本身全绿，非 engineer 实现缺陷。

### 第 2 轮 reviewer 验收（2026-10-24，amend 后复验）

- **提交完整性**：`git show --stat HEAD`（amend 后 `e0c28f7d`）已含 11 个 `tools/*.py`；`git status --porcelain -uall` 仅剩任务书审阅记录本身，工作树干净。
- **干净检出复验**：`git worktree add` 至 `e0c28f7d` ⇒ `check_spec_refs` rc=0（0 violations）、`check_asm_list_consistency` rc=0（12 spec files OK）——上一轮两处门控红已清；关键产物（4 册 + opcodes.yaml + lock + gen_asm_list.py）md5 与上一轮全绿工作树逐一相等，语义零漂移结论延续有效。
- **L1**：`make check` rc=0（`repository checks (L1): PASS`，llc/clang/qemu 均可用）。
- **证据脚本**：`run.sh` 重跑 rc=0（SPEC-167t evidence: PASS）。
- **判决：Accepted**——上一轮唯一阻断（11 个 tools 文件未提交）已消除，全部验收项在提交态复验通过；建议主会话按流程 `/complete`。
