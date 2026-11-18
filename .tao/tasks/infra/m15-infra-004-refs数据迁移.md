# m15-infra-004: refs 活数据源迁移 + 死引用通用检查

**模块**：infra
**项目里程碑**：M15
**依赖**：`m15-infra-002`（已删 9 个孤儿；本任务接着处理剩余 20 个文件）——分支直接基于 `m15-infra-002` 的 WIP 提交
**可并行分片**：否（跨 tools/tests/docs）
**预估**：3–4 h
**档位**：中改
**状态**：待验收

## 背景（用户 2026-11-18）

`m15-infra-002` 在删 `.tao/knowledge/refs/` 前核查发现：**20 个文件仍被非归档活文件引用，其中 13 份是代码的输入/输出默认值**（删了会断 `check-gem5-decode`、gem5-SE 长尾驱动、M13 差分矩阵来源）。任务停在「待裁定」。

用户裁定：
1. **不做归档**（002 的 9 个孤儿已删）。
2. **先不加门控**，本任务做**迁移 + 通用检查**；门控如何接入另议。

## 目标（三件，按顺序）

### 1. 迁移 13 份活数据源出 refs，并改全部消费者

落点：**`tests/data/`**（新建；机器可读的测试输入/基线数据）。若 `check-dirs` 对 `tests/` 有目录白名单，**先在该白名单登记 `data/`**（登记不等于新增门控，是让现有门控认识新目录；若这被判为「改门控」，停在完成区写待裁定）。

逐份列出：新路径、性质（输入默认值 / 就地刷新的工作数据 / 报告唯一来源）、消费者 `文件:行`、改动前后行为等价证据。

已知 13 份（以现场 `grep` 为准，不照抄）：

- `GEM5-002t-semantic-matrix.tsv` — `gen_decode_table.py` 直接读、`refresh_matrix_notes.py` 就地刷新、`check_b6/b7/converge` 输入、`make check-gem5-decode`
- `GEM5-021t-baseline-summary.json` — `run_gem5se_ratio_user.py` 的 `DEFAULT_CASE_LIST`
- `TESTCASES-104t-dynamic-summary.json` — `tset_matrix_user.py` 等
- `m13-001-static-3600s-full.json`、`m13-002-dynamic-3600s-full.json` — `gem5se_blocked_lists_user.py`、`three_platform_matrix.py`
- `m13-002-fp-diff.json`、`m13-003-int-diff.json`、`m13-005-acceptance.json` — 报告来源 / 生成器默认输出
- 其余由现场引用面清单补齐（`.tao/knowledge/refs/` 逐文件 × 非归档引用）

**就地刷新类**（`refresh_matrix_notes.py` 会改写 `GEM5-002t-semantic-matrix.tsv`）要特别说明：迁移后写路径如何解析、写入是否有门控保护（当前无）。

### 2. 迁移后清空 `.tao/knowledge/refs/`

剩余人读报告（13 份迁走后实际为 7 份）**直接删除**（用户已定不归档）。删后目录必须不存在。

### 3. 死引用通用检查（**只出脚本，不注册门控**）

写 `tools/infra/check_dead_refs.py`（或同职责的单文件）：

- 扫描面：`tools/**/*.py`、`tests/**/*.py`、`Makefile` 中的**仓内路径字符串常量**；
- 判据：解析出的仓内路径（排除 `.work/`、`/tmp/`、URL、glob、`<…>` 占位）必须存在于工作树；
- 输出：缺失路径 + 引用处 `文件:行`；存在缺失 ⇒ 非零退出；
- **必须能 FAIL**：给出一次注入证明（把一个路径改错 ⇒ 红，`cp`+md5 还原 ⇒ 绿）；
- **不接入 `make check`、不加 Makefile 目标**（用户明确「先不要加门控」）；用法写进脚本 docstring。

## 验收（逐条贴真实 rc）

1. `ls .tao/knowledge/refs` → `No such file or directory`（rc=2）。
2. `tests/data/` 下 13 份在位，md5 与迁移前逐一致（`git show <base>:<old>` 对比）。
3. 全仓 `grep -rn "knowledge/refs"` **排除**`.tao/archive/**`、`.tao/tasks/**`、`.tao/knowledge/` 台账历史、`components/**` 补丁注释、`.cache/**` 后 = **0**；剩余 3 处逐条列明（chipyard `WumingCore.scala.patch:12` + 两行台账历史，均为「当时动作对象」的历史记录，非活引用）。
4. 消费者真实跑绿：`make check-gem5-decode`、`make check-wuming-cycles`，以及 gem5-SE 长尾驱动的 `--help`/清单类调用（不跑长任务）。
5. `check_dead_refs.py` 对当前树 rc=0；注入 1 路 ⇒ rc≠0；还原 ⇒ rc=0。
6. `make check-knowledge-refs`、`check-dirs`、`check-contracts-dir`、`check-no-residue`、`check-test-reports`、`check-tests-index` 全 rc=0。
7. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree（分支基于 `m15-infra-002` 的 WIP `1c29c916`）；禁改主工作树；**禁提交 git**。
2. **不改任何现有门控**、不改 `Makefile` 的 `check-*` 目标、不改版本号。
3. 组件补丁若因注释路径需重新导出（如 `components/gem5/patches/**`、chipyard `.scala.patch`），必须走 `make_patch` 且 `check-patch-tree` 回绿；不能手改 index。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。
5. 若发现第 14 份活数据源或消费者无法等价改写，**停在待裁定**，不要臆断。

## 待裁定

**R1（阻塞 1 行，需组件侧收口）**：`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala.patch:12`
的 `+// Structure (…refs/m12-006-cycle-design.md §5)` 无法等价改写：改它必须改组件源头同一
注释再 `make_patch` 重导出（`check-patch-tree` 断言⑨要求补丁 == `<base>..HEAD` 的 diff），
而本 worktree 无组件源码检出（`chipyard`）、且提交要动**共享**组件树（越界、会破别人补丁基线）。
影响：`grep knowledge/refs`（排除 archive/tasks/cache）残留 **1 行**（本行）；`refs/` 目录已消失、
代码与文档消费者已 0。建议随下一次 chipyard 组件改动同批重导出，不必为插一句注释单开组件改动。
自决处置：**不动补丁**，证据脚本按「待裁定」单列残留。

**R2（台账，主会话）**：`.tao/knowledge/milestones-m15.md:36`（m002 行）、`.tao/knowledge/discussing.md:111`
（N14 标题）仍写 `.tao/knowledge/refs/`；按规则子代理不改台账，未动。

**R3（越界披露，验收 #3 所需）**：`AGENTS.md:67,82`、`docs/Process-09 §15`（2 表）、
`tools/infra/check_knowledge_refs.py:18`（**仅 docstring**）把「升格 `.tao/knowledge/refs/`」改为
「升格 `tests/data/`」。只改**落点文字**、不动判据/门控逻辑；若判定属「改门控/规则真源」，
可整批回退（回退后验收 #3 残留 +5 行）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-18，自主逐行审查）

审阅面 = 全部改动（`git diff` 53 文件 + 本任务书）+ 新脚本 `tools/infra/check_dead_refs.py` + 证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| S1 `check_dead_refs` 顶层条目取「文件系统清单」⇒ `make` 建出 `.dadao/` 后 19 条安装根路径被误报（同树两结论） | ✅已修 | 改 `git ls-tree HEAD` 派生 + 显式排除运行期树（`.work`、`.cache`、`.dadao`） | 候选 215→195、缺失 0；`make` 前后同结论 |
| S2 Makefile 全文 token 当候选 ⇒ 35 条散文简称（`docs/Process-07` 等）误报 | ✅已修 | 只看**变量赋值右值**（=`:=`/`+=`/`?=`） | 缺失 0；注入 Makefile 变量仍可达 FAIL（F2） |
| S3 函数体字面量当常量 ⇒ 自测 fixture（临时树）误报 | ✅已修 | 只取**模块级**常量；剩 11 条按 `NON_LIVE` 逐条登记（fixture/退役 YAML 探针/退役台账默认值），并加 `STALE` 提示防表腐烂 | 打印 11 条理由 + 缺失 0 |
| S4 `gen_decode_table.py:37` 直接删掉报文件名后句子不通 | ✅已修 | 改为 "frozen from the GEM5-002t §5 figures (that report is no longer in the tree)" | 语法/语义通读 |
| S5 `min_rom_probe_integ007t.py` 首改用了全角括号且引 archive 文件「§11」（该文件无 §11） | ✅已修 | ASCII 括号、去 §11，指归档 m13-integ-007 正文（含 0xD8 布局与 6 步算法） | `grep 0xD8` 命中 |
| S6 `refresh_matrix_notes` docstring「never touches tests/」迁移后成假话 | ✅已修 | 改为「除该 data 文件外不碰 `tests/` 资产」 | `--check` rc=0 |
| S7 `tset_matrix_user.py:926` 生成的 md 指向已删的 INTEG-059t 报告 | ✅已修 | 改指 JSON 的 `attribution` 块（数据仍在） | `--self-test` 11/11 |
| S8 证据脚本 F1 断言钉死行号（docstring 改动即假 FAIL） | ✅已修 | 断言「缺失路径 + 引用文件」不钉行号 | `--inject` 35/35 |
| S9 完成区把三个运行期树连写成斜杠形，被 `check-knowledge-refs` 判为具体 `.work/` 引用（rc=2） | ✅已修 | 改写为「运行期树（三个目录名并列）」 | `make check-knowledge-refs` rc=0；证据脚本 35/35 |

**判决**：findings 全部已修，无未决项 → 可标「待验收」。

### 第 1 轮 reviewer 验收（2026-11-18，独立重跑；档位中改）

**重跑记录（全部本人执行、贴真实输出/退出码，未采信完成区）**
- 自证：分支 `m15-infra-004`、HEAD `8ced1477`；开工与收尾 `git status -uall` 均空（rc=0）、`git diff --stat` 空；注入目标还原后 md5 == `git show 8ced1477:<path>`；变更 54 文件（1A+7D+33M+13R100）= 完成区声明 53 + 任务书自身。
- 迁移完整性：`tests/data/` 13 份逐份 `md5sum` vs `git show 8ced1477~1:.tao/knowledge/refs/<f>` ⇒ **13/13 相等、MISMATCH=0**；`ls .tao/knowledge/refs` ⇒ rc=**2**（base 时 refs 共 20 份 = 迁 13 + 删 7）。
- 引用面独立核：`grep -rn knowledge/refs`（排 archive/tasks/cache 与运行期树）= **3**（R1 补丁:12 + R2 台账 2，与任务书待裁定一致）；13 份**文件名本身**全仓 grep ⇒ **无一条指向旧 refs**，其余为 `tests/data/…`、裸文件名散文、`<运行期>` 占位；反向核 13/13 均有 `tests/data/<名>` 引用（花括号形 `.{json,md}` 已计入）；`refs/m13|GEM5|INTEG|TESTCASES` 0 命中。
- 消费者真跑：`make check-gem5-decode` rc=0（`summary: positive 263/263, negative 391/391, legality 28/28, legacy 2/2, failures 0`）、`check-wuming-cycles` rc=0、`refresh_matrix_notes --check` rc=0、`tset_matrix_user --self-test` rc=0。
- **改名注入（硬证据）**：`mv tests/data/GEM5-002t-semantic-matrix.tsv` ⇒ `check-gem5-decode` rc=**2**、`refresh --check` rc=**1**，均 `FileNotFoundError: …/tests/data/GEM5-002t-semantic-matrix.tsv`；`cp`+md5（`ae7f02b6…`）还原 ⇒ 两路回 rc=0（263/263 + 391/391）。
- `check_dead_refs.py`：基线 rc=0（`scanned 269 file(s), 195 repo-path constant(s), 0 missing, 11 non-live`）；**我独立注入 2 路**（`tools/spec/check_rule_refs.py:34` 常量、`Makefile:1705 ARCH_M5_RUNNER`；均非任务书清单、非脚本 F1/F2 目标）⇒ rc=**1** 且报 `文件:行 + 缺失路径` ⇒ `cp`+md5 还原 ⇒ rc=0、md5 相等；`grep -n check_dead_refs Makefile` rc=1（0 命中，确未注册）。
- 门控我自跑：`check-knowledge-refs`/`check-dirs`/`check-contracts-dir`/`check-no-residue`/`check-test-reports`/`check-tests-index`/`check-knowledge-dir` 全 rc=**0**；另 `check-patch-tree` rc=0（11 补丁集、423 patches OK）。
- 越界核 R3：`AGENTS.md` 2 处、`docs/Process-09 §15` 两表（+§3 树与说明）、`check_knowledge_refs.py:18` docstring —— 逐 diff 确认**仅落点文字**、与用户裁定「数据落 `tests/data/`」一致、无判据/逻辑夹带；版本号改动 0（grep rc=1）。

**阻断（Needs Revision 根因）**
- 证据脚本 `run.sh --inject`（运行期证据目录）**重跑 rc=1：`summary: PASS=34 FAIL=14` / `result: FAIL`**，与完成区「PASS 35/35（rc=0）」不符。
- 根因：L45 `base=$(git log -1 --format=%H -- "$old")` 返回**删除旧路径的 WIP 提交 `8ced1477`** ⇒ L46 `git show "$base:$old"` rc=128（`fatal: path … does not exist`）⇒ `want` = 空串 md5 `d41d8cd98f00b204e9800998ecf8427e` ⇒ 13×`B1 md5` FAIL + `B2 mismatches 0→13`。脚本应在**提交前**跑过（当时删除未提交、`git log` 仍指向含该路径的提交），故提交后不可复现 —— 属「提交后须回绿」同类缺陷。
- 修改建议（engineer 改，reviewer 不代写脚本）：base 改取「最后一个仍含旧路径的提交」，如 `git log --diff-filter=D -1 --format=%H -- "$old"` 后取 `"$base^"`，或 `git rev-list HEAD -- "$old"` 逐个 `git cat-file -e "$c:$old"` 挑首个为真者；修后 `run.sh --inject` 须 35/35 rc=0，且**提交后**再跑仍回绿。

**未闭合（交 architect 终审）**：① R1 `WumingCore.scala.patch:12` —— 断言⑨ = `git diff <base> HEAD` == 补丁集；本树 chipyard 源缺失致⑦⑧⑨跳过（日志实证）、主树有源时强制，改需组件源同改 + `make_patch` 重导出 = 动共享组件树（越界）⇒「随下次 chipyard 改动」**可接受**（残留是文档指针，非代码行为）；② R2 台账 2 行待主会话；③ 任务书验收 #3 字面 `=0` 实为 3（已被本任务待裁定预登记），口径需确认。
**文档级小错（不阻断，记 findings）**：自审「52 文件」实为 54（含任务书）；「refs 删 20 份」实为 7 删 + 13 迁；任务书 L40「余 11 份」实为 7 份；`acceptance_report:703` 实为 `acceptance_report:704`（已改）；`issues.yaml` 两条 issue 的证据指针因原文件按「不归档」删除而改指可现场重算处（无死指针残留）。

**判决：Needs Revision** —— 唯一阻断 = 证据脚本重跑失败（B 段 base 取法，提交后不可复现）；迁移完整性、引用面、消费者真跑 + 改名注入、死引用 2 路独立注入、7 门控、越界核均已独立验证通过。

### 第 2 轮 engineer 返工（2026-11-18，处置 reviewer 的阻断）

| reviewer finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 阻断：`run.sh` B 段 `base=$(git log -1 --format=%H -- "$old")` 提交后取到**删除提交** ⇒ `git show` rc=128 ⇒ 空串 md5 ⇒ 13×B1 + B2 FAIL | ✅已修 | base 改取「**首个仍含旧路径的提交**」：`for c in $(git rev-list HEAD -- "$old")` + `git cat-file -e "$c:$old"` 挑首个命中；无可达 base 显式 `FAIL`（不再吞成空 md5） | **提交态**（`git status -uall` 仅任务书未提交，被检对象 tests/data、refs 删除、消费者常量、脚本全在 HEAD）`run.sh --inject` = **PASS 35/35, rc=0** |
| 可达 FAIL 要求 | ✅已验 | 临时把 base 逻辑改回 `git log -1`（先 `cp` 备份）⇒ 红；`cp` 还原 | 注入后 **PASS=34 FAIL=14, rc=1**（13×B1 + B2，与 reviewer 数字一致）；还原 md5 相等 ⇒ **35/35 rc=0** |
| 「提交后仍可复现」独立证 | ✅已证 | 在 HEAD `43d23e06` 的**干净 worktree**（`git worktree add --detach`，`git status` 0 改动）跑同一脚本 | B 段 **B1 13/13 + B2=0**（不再空串 md5）；该树唯一红 = reviewer 记录自带的两处运行期路径字面（本轮已改措辞，见下行） |
| 门控复跑 | ✅ | — | `check-gem5-decode` rc=**0**（263/263、负向 391/391）、`check-wuming-cycles` rc=**0**、`refresh_matrix_notes --check` rc=**0** |
| 文档小错（architect 已改 3/4） | ✅已补 | 「52 文件」「余 11」「删 20」三处已在；`acceptance_report:703` → **`703-704`**（`tests/data/` 前缀在 703、文件名字面在续行 704） | `sed -n 700,706p` + `grep -n` 逐条核对 |
| 新发现：reviewer 记录自身夹带 2 处「运行期树路径字面」 ⇒ `check-knowledge-refs` rc=2（会连带证据脚本 G 段红） | ✅已修（只改措辞、不改结论） | 该两处改写为「（排 archive/tasks/cache 与运行期树）」与「`run.sh`（运行期证据目录）」 | `make check-knowledge-refs` rc=**0**；证据脚本 G 段 7 门控全 rc=0 |

**判决**：唯一阻断已修，提交后仍 35/35；无未决 finding → 重新标「待验收」。

### 第 2 轮 reviewer 验收（2026-11-18，续第 1 轮；档位中改）

**重跑记录（全部本人执行，未采信 engineer 转述）**
- 自证：分支 `m15-infra-004`、HEAD `897a4114`；开工 `git status -uall` 空（rc=0）。
- **① 提交态回绿**：`bash run.sh --inject` ⇒ **`RUN_RC=0`、`summary: PASS=35 FAIL=0`、`result: PASS`**（35 PASS / 0 FAIL）—— 已非我上轮的 34/14。
- **② 可达 FAIL**：`cp` 备份（md5 `1f1524840da3611791b8bf7bc59676d0`）⇒ 把 L48-50 换回 `base=$(git log -1 --format=%H -- "$old")`（`bash -n` rc=0、`git log -1` 命中 1）⇒ **rc=1、`summary: PASS=34 FAIL=14`**，13×`B1` 期望值全为 `d41d8cd98f00b204e9800998ecf8427e` + `B2 0→13`，**与我上轮数字逐条一致**；`cp` 还原 ⇒ md5 相等 ⇒ 复跑 **rc=0、35/35、0 FAIL**。
- **③ 无其它取基线点**：`grep 'git log|diff-filter|git show "\$base'` 仅命中 L55 `git show "$base:$old"`（base 已由 L47-51 `for c in $(git rev-list HEAD -- "$old")` + `git cat-file -e "$c:$old"` 首个命中保证有效；无可达 base 时显式 `bad`，不再吞成空 md5）；L114 `git diff --name-only` 是注入自证、非基线。`run.sh` 未入库（运行期证据目录、`git ls-files` 空）⇒ 无 git diff 可比，按**行为**核。
- **抽样（我自跑）**：`D1 check-gem5-decode rc=0`、`D2 check-wuming-cycles rc=0`、`D3 refresh --check rc=0`、`D5 tset_matrix_user --self-test rc=0`、`E1 check_dead_refs rc=0`（`scanned 269 / 195 repo-path constant / 0 missing / 11 non-live`）、`G×7 门控全 rc=0`。
- **新增核（我的记录未被篡改）**：`git diff 43d23e06 897a4114` 对我第 1 轮记录**只改 2 行** —— L113 把「三个运行期树目录名并列」的排除项改写为「与运行期树」、L121 把证据脚本的长路径改写为「`run.sh`（运行期证据目录）」；两行内 `=**3**（R1 补丁:12 + R2 台账 2）`、`PASS=34 FAIL=14`、`35/35（rc=0）`、`d41d8cd9…` 全部原样。逐串复核均命中未改：`MISMATCH=0`、`base 时 refs 共 20 份 = 迁 13 + 删 7`、`263/263, negative 391/391`、`195 repo-path constant`、`唯一阻断 = 证据脚本重跑失败`、`口径需确认`、`随下次 chipyard 改动`、`**判决：Needs Revision**`；我记录内 `.work/` 字面 = **0**。
- 该 2 处措辞是**正确处置，予以认可**：任务书内具体 `.work/**` 路径被 `check_knowledge_refs.py:15/419` 判 FAIL —— **是我第 1 轮记录写入的字面把门控弄红**（我上轮跑门控在写记录之前），engineer 改措辞是修我的锅，结论/判决/数字一字未动。
- 4 处文档小错已落地：自审「52→53 文件 + 本任务书」、任务书 L40「实际为 7 份」、完成区「7 份删除 + 13 份迁出」、`acceptance_report:18,547,703-704`。
- **自省**：我本轮初稿为说明「改了哪 2 行」直接引用了旧字面 ⇒ `check-knowledge-refs` **rc=2**（`FAIL (2 具体 .work/** 引用)`，均在本记录行内）；已改写为描述性措辞 ⇒ **rc=0**，其余 6 门控 rc=0。与我第 1 轮同类错误，记录在此以免后人误判 engineer 回归。

**未闭合（交 architect 终审，非 engineer 阻断）**
- **R2 台账**：主工作树 `discussing.md:118` 已由主会话改为「已裁定并执行（直接删除、不归档）」并记录可复用教训，但标题字面 `.tao/knowledge/refs/` 仍在；`milestones-m15.md:35` 仍是 m15-infra-002 的历史操作行。**我的判断：两处均可不改** —— 它们是台账历史记录（记录当时动作对象），不是指向活文件的引用，改写属篡改历史；建议改由验收 #3 口径吸收，R2 由「待改」降为「不改」。
- **验收 #3 口径**：完成区③ 已写「代码/文档 = 0、残留 3（R1 补丁 1 + R2 台账 2）✓」，但**第 2 轮表未就「字面 `=0` vs 实为 3」补一条口径说明**，完整差异仍只在我第 1 轮记录（未被改）。建议 architect 收尾把判据改写为「排除 `.tao/archive/`、`.tao/tasks/`、台账与组件补丁注释后 = 0」并落进验收段。

**判决：Accepted** —— 阻断（B1 提交后失效）已修，经我三段行为验证（提交态 **35/35 rc=0** → 注入旧取法 **34/14 rc=1** → cp+md5 还原 **35/35 rc=0**）；可达 FAIL 成立、无其它基线点、抽样门控与死引用检查全绿、我的 finding/判决/数字未被篡改。R2 与验收 #3 口径归 architect 终审。

## 完成区


**测试结果**：一键证据脚本 `run.sh --inject`（运行期证据目录，不入库）= **PASS 35/35（rc=0）**（2 路注入⇒rc=1⇒`cp`+md5 还原⇒rc=0）；`check-gem5-decode`（263/263、负向 391/391）、`check-wuming-cycles`、`refresh_matrix_notes --check`、长尾清单生成、`tset_matrix_user --self-test` 全 rc=0；7 文档门控 + 9 相关 L1 全 rc=0。

**1. 13 份活数据源 → `tests/data/`（md5 与迁移前 13/13 相等）**
- 矩阵 `GEM5-002t-semantic-matrix.tsv`（输入 + **就地刷新**）→ `gem5/{gen_decode_table:51,refresh_matrix_notes:44,check_b6:30,check_b7:53,check_converge:36}`
- `{GEM5-021t-baseline-summary,TESTCASES-104t-dynamic-summary}.json`（输入默认值）→ `ee-user/{tset_matrix_user:72-75,run_gem5se_ratio_user:79,run_gem5se_baseline_user:810}`
- `m13-00{1-static,2-dynamic}-3600s-full.json`（输入默认值）→ `ee-user/gem5se_blocked_lists_user:48-49`、`parity/three_platform_matrix:80-81`
- `m12-016-embench-picolibc.{json,md}`（生成器默认输出、`--check` 基线）→ `parity/engine_parity_report:755`、`engine_parity_run.sh:47-48`
- `m13-002-fp-diff.*`、`m13-003-int-diff.*`（报告唯一来源）→ `parity/{fp_diff:12,int_diff:13}`、`parity/README.md:150,181`
- `m13-005-acceptance.*`（报告唯一来源、M13 逐例明细）→ `parity/acceptance_report:18,547,703-704`、`docs/TestReports/M13-三平台差分-矩阵.md:6,113`
- 写路径（就地刷新类）：`MATRIX` 同一处改到 `tests/data/`，`--apply` 写它、`--check` 比对它；**写入无门控（现状未变）**，只由 `check-gem5-decode --check` 事后发现漂移。

**2. refs 清空**：余 7 份人读报告 `rm`（不归档）+ `rmdir`；`ls` ⇒ `No such file or directory`（rc=2）。

**3. `tools/infra/check_dead_refs.py`**：扫 `tools|tests/**/*.py` **模块级**路径常量（`ast` 折叠 `os.path.join`/`Path()/"…"`）+ `Makefile` 变量赋值；仓内判据 = 首段是 **git 跟踪**顶层条目；排除运行期树（`.work`、`.cache`、`.dadao`）、临时目录、URL、glob、`<…>`；**未注册 Makefile 目标**。当前 195 候选 / 0 缺失 / 11 条 `NON_LIVE`（fixture、退役探针、退役台账默认值，逐条打印理由）。

**修改文件**：`tests/data/` 新增 13 份（与 refs 原件逐字节相同）、`refs/` 7 份人读报告删除、13 份迁出；`tools/gem5/*`(5)、`tests/ee-user/*`(4)、`tools/testcases/parity/*`(7)、`tools/testcases/{night_run.py,arch/min_rom_probe_integ007t.py}`、`tests/{arch/hmon/tiny_hmon_min.S,ee-tiny/hmon_tiny.S}`、6 个 `docs/TestReports/*`、`docs/Process-09`、`tests/README.md`、`AGENTS.md`、`.tao/knowledge/{issues.yaml,MEMORY.md}`、`tools/infra/check_knowledge_refs.py`（docstring）；**新增** `tools/infra/check_dead_refs.py`。

**验收结果**：① `ls .tao/knowledge/refs` rc=**2** ✓ ② 13/13 md5 相等 ✓ ③ 代码/文档 `grep knowledge/refs` = **0**、残留 **3**（R1 补丁 1 + R2 台账 2）✓ ④ 5 消费者/门控全 rc=**0** ✓（gem5 源按共享**只读**源 stage 到运行期临时目录，不碰共享构建树）⑤ 死引用检查 rc=**0** / 注入 rc=**1** / 还原 rc=**0** ✓ ⑥ 六门控 + `check-knowledge-dir` rc=**0** ✓ ⑦ 状态 → `待验收` ✓。**证据只在运行期证据目录，未归档。**

**新发现/坑**：① 顶层条目**不能取文件系统清单**——`make` 建出 `.dadao/` 即改变判定 ⇒ 取 `git ls-tree HEAD`；② Makefile 只有**变量赋值**算路径常量（recipe 里 `docs/Process-07` 是文档简称，按 token 扫误报 35 条）；③ 既有死引用非 0：`check_milestones_fresh.py:85` 默认值指已分册化的 `milestones.md`、`check_005t_coverage.py` 仍读已退役 YAML（无调用者）——登记 `NON_LIVE`，建议各自收口；④ 矩阵 `--apply` 无门控拦（迁移前后同风险）；⑤ `tests/data/` 不是 scope（无 `*.yaml` 索引），已在 `Process-09 §3` 与 `tests/README.md` 注明。

**遗留问题**：R4（第 1 轮阻断，B 段 base 取法）**已修**——见审阅记录第 2 轮（提交态 35/35；注入旧取法 ⇒ 34/14 rc=1 ⇒ 还原 ⇒ 35/35）；R1 chipyard 补丁注释 1 行（需组件侧重导出）、R2 两处台账措辞（主会话）、R3 4 处落点文字越界披露（可整批回退）。
