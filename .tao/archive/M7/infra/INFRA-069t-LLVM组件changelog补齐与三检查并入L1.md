# INFRA-069t: LLVM 组件 changelog 补齐 + 三个检查并入 L1

**模块**：infra
**项目里程碑**：M7
**依赖**：与在办 llvm 侧任务**串行**（同改 `Makefile` 与 `components/llvm-project/**`）
**状态**：已验证

> 立项来源：用户 2026-10-12 裁定「**全按建议办（推荐）**」⇒ 本任务承载其中 **① 补齐 LLVM 组件 changelog** 与 **② 三个门控候选并入 L1**。

## 用户裁定（2026-10-12，**原话/选项标签**）

- 议题：① LLVM 组件 changelog 断档是否补齐；② 三个"未入门控"的检查是否并入 `make check`。
- **用户选择 = 「全按建议办（推荐）」** ⇒ ① **补齐**（并与 qemu 侧/M6 做法对齐）+ 定"每任务收尾加一行"；② **并入 L1**。
- 取得渠道：**经主会话问答**取得（2026-10-12）。

## 事实（现场实测）

- `components/llvm-project/changelog.md`：M6 至 `LLVM-078t` **均有条目**；M7 仅 **`LLVM-082t`** 有（其 architect 越界补的一行）⇒ 立项期记「缺 6 条」（`LLVM-079t`/`080t`/`081t`/`084t`/`085t`/`086t`）。**⚠️ 订正（2026-10-12 现场统计）**：此后 `LLVM-087t`/`088t`/`089t` 亦未加 ⇒ 缺口 **9 条** = M7 流水（`milestones.md`）LLVM 任务全集 − changelog 已有条目（`git log --format=%h|%ad` 取证）。数量以**现场统计**为准（不写死）。
- 对照：`components/qemu/changelog.md` **正常**（`QEMU-056t` 已加）。
- 三个未入门控的检查：`tools/llvm/gen_isa_coverage.py --check`（矩阵 ↔ 真源）、`tools/spec/check_numbering.py`（21 册标题编号）、`tools/spec/check_spec_changelog.py`（21 册附录格式）——均**可机械判**且**有 `--check`/自带 FAIL 路径**（`lessons §2.11`：机械生成投影/派生清单须有 drift 门控）。

## 接口规范

- **输出**：
  1. **补齐 9 条**（现场统计：`LLVM-079t`/`080t`/`081t`/`084t`/`085t`/`086t` + 立项后新落的 `087t`/`088t`/`089t`；立项期曾记 6 条）到 `components/llvm-project/changelog.md`：
     - **体例与该文件既有条目一致**（列 = 日期 / 任务号 / 描述 / 执行方；描述含**依据**与**改了哪些文件**，长度量级参照既有行）；
     - 内容**从 git 历史 + 各任务书提炼**（`git log` + `.tao/tasks/llvm/LLVM-08*t-*.md` 完成区），**不得编造**；日期取**落地提交日期**（`git log --format=%ad`）。
     - **`LLVM-082t` 既有行不动**。
  2. **定口径**：在该 changelog 头部（或 `docs/Process-01`）加**一行**："**组件补丁变更后，任务收尾须在同一变更内追一行**"（其后 `LLVM-087t`/`088t` 等按此办）。
  3. **三个检查并入 L1**（`make check`）：为三者各加 Makefile target（若已有 target 则复用）并加入 `check` 依赖链；**须能失败**（各自注入反例 ⇒ FAIL ⇒ 还原 ⇒ 回绿），**计数不写死**。
  4. `.tao/knowledge/milestones.md` 流水更新 `INFRA-069t` 行（状态 `待验收`，`完成时间` `—`）。
- **约束**：**不改** `spec/`、`contracts/`、`tests/vectors/`、各组件 `patches/**`；`LLVM-082t` 既有条目不动；计数不写死。

## 验收标准

1. **9 条补齐**（现场统计）：逐条列出（任务号 → 日期 → 出处 = git 提交 / 任务书章节）；`grep` 证明**每个** M7 LLVM 任务号在文件内**各出现一次**（`082t` 仍一次）。
2. **口径落纸**：新增一行维护规则（`grep` 真实输出）。
3. **三检查入 L1**：`grep` 证明三者已在 `check` 依赖链；`make check` **EXIT=0**；**三者各自**注入反例 ⇒ **FAIL**（真实输出）⇒ `cp`+md5 还原 ⇒ 回绿。
4. **不回归**：`make check`/`check-modules`(L2)/`check-no-residue`/`check_issues` 各 EXIT=0。
5. **完成区**（≤30 行）与真实输出逐条对齐。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-069t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；显式 staging（禁 `git add -A`）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. 只动任务范围（`components/llvm-project/changelog.md`、`Makefile`、`tools/**`（若需）、`docs/Process-01`（若选该落点）、任务书、`milestones.md` 行）；越界须披露。
5. 失败保留现场并继续推进；**只在需用户语义裁定**时**停止并报告**（禁自拟自答）。
6. 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位）。
7. 一键证据脚本落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
8. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
9. **计数不写死**。

## 完成区

**测试结果**：一键证据 `<证据目录>/run.sh` **31/31 PASS rc=0**（三检查各自「基线绿→注入 FAIL→`cp`+md5 还原→回绿」+ 结构断言，计数现场统计）；`make check`(L1) **EXIT=0**（29s）；`make check-modules`(L2) **EXIT=0**（`check-lit` 107/107；`test-semihost`/`test-codegen`/`test-elf`/`check-qemu-smoke`/`check-picolibc-tests` 全 PASS）；`check-no-residue` EXIT=0；`check_issues` EXIT=0（25 open/9 closed）。

**修改文件**：`components/llvm-project/changelog.md`（+规则行+9 条）；`Makefile`（+3 target 并入 `check` + `.PHONY`/help）；`docs/Process-01-组件补丁组织与构建编排.md`（§10 规则 + §13 rev）；`.tao/knowledge/milestones.md`（`INFRA-069t` 行 + 2 规划项收口）；`.tao/knowledge/llvm-isa-backend-matrix.{tsv,md}`（**越界披露**：现场重生成消漂移）；本任务书；证据/日志（非 git，`<证据目录>`/`<日志目录>`）。

**验收结果**（逐条）：
1. 缺口 **9** 条（现场统计 = M7 流水 LLVM 10 任务 − 已有 `082t`）：`079t`/`080t`/`081t`/`084t`/`085t`/`086t`/`087t`/`088t`/`089t`；日期取自落地提交（`079t`=2026-10-11，余=10-12；`git log --format=%ad` 实证），出处 = 各 commit + 任务书完成区；9 号各 `grep -c`=1（`082t`=1 且其行未动，`git diff` 纯插入）。
2. 规则落纸：changelog 头部 + `Process-01 §10`（`grep` 真实输出见证据脚本）。
3. 三检查入 L1：`check` 依赖链含 `check-isa-coverage`/`check-spec-numbering`/`check-spec-changelog`（各另有 target）；三者各自注入 ⇒ FAIL ⇒ 还原 ⇒ 回绿（证据脚本逐条）。
4. 不回归：`make check`/`check-modules`(L2)/`check-no-residue`/`check_issues` 均 EXIT=0。

**新发现/坑**：① **`gen_isa_coverage --check` 基线即红**——`081t` 入库后 `LLVM-084t` 等改补丁，第②层证据行号/条目漂移（`pat 87→97`）⇒ 须先现场重生成矩阵方能绿；印证「生成投影须有 drift 门控」（`lessons §2.11`），也说明「加门控」不能只看 `--check` 是否存在。② **pre-M6 changelog 条目缺失（准确清单，reviewer 第 1 轮现场核）**：`LLVM-028t`/`060t` 确缺，`LLVM-013t`/`014t`/`019t`–`025t` 亦缺（changelog 回溯至 `026t`，属文件创建前的历史截断）；**`LLVM-046t` 不属此类**——其未触碰 `patches/`（仅 `series` 重建）⇒ 无「组件补丁变更须追一行」之义务，先前表述已订正。本次按 M7 范围未补，已登记 `ISS-200`。③ 三检查均依赖 install-root 工具/只读册，L1 因此依赖 `llvm-mc`（与既有 `check-components` 同层同性质）。

**遗留问题**：pre-M6 LLVM 组件任务缺 changelog 条目（**准确清单** = `013t`/`014t`/`019t`–`025t`/`028t`/`060t`；`046t` 未触碰 `patches/` ⇒ **除外**），本次按「M7 断档」范围未补 ⇒ 已登记 `ISS-200`（open，建议归档时按需补或明确「历史不补」）；`gen_isa_coverage --check` 要求凡改 `DADAO*.td`/`ISel*.cpp` 的任务收尾**重生成矩阵**（新口径，建议写入任务书模板）。

## 审阅记录

#### 第 1 轮 engineer 自审

改动面：`components/llvm-project/changelog.md`（头部规则 + 9 行）、`Makefile`（3 target + `.PHONY` + help + `check` 依赖）、`docs/Process-01`（§10/§13）、`.tao/knowledge/milestones.md`（1 行 + 2 处规划项收口）、`.tao/knowledge/llvm-isa-backend-matrix.{tsv,md}`（现场重生成）。逐项核对结论：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| **`gen_isa_coverage.py --check` 基线即红**：入库矩阵为 `LLVM-081t` 产物，此后 `LLVM-084t`（`DADAOCodeGen.td` 增 `DADAOFPSelCC` pattern）等改动使补丁文本变化 ⇒ 第②层证据行号/条目漂移（`pat 87→97`），`--check` rc=1 | ✅已修（当场派修，越界披露） | `python3 tools/llvm/gen_isa_coverage.py` 现场重生成 `.tsv`/`.md`（纯机械重派生，见 diff 仅证据列变化） | `--check` rc=0（227/①217+10/②86+141）；证据脚本注入⇒FAIL rc=1⇒`cp`+md5(`6297bc3f…`)还原⇒rc=0 |
| `check-isa-coverage` 使 L1 依赖 `llvm-mc`（install root）；缺失即 rc≠0 | ✅已核（fail-closed，可接受） | 无（沿用 `resolve_llvm_mc` 明确报错） | 与既有 `check-components` 同层同依赖；`make check` rc=0 |
| 头部规则行 grep 断言首跑 FAIL（模式未含 markdown 粗体 `**同一变更**`） | ✅已修 | 证据脚本模式改 `组件补丁变更后，任务收尾须在` | 证据脚本 `rule line` PASS |
| `088t` 行正文误引 `LLVM-079t` ⇒ `grep -c` 该号 = 2（违「各出现一次」） | ✅已修 | 改为「与 P0 的 `EXTLOAD` 载入互为镜像」 | 9 个任务号各 `grep -c`=1；`082t`=1 |
| 反例注入改 `spec/`（只读册）有残留风险 | ✅已修 | 证据脚本 `trap restore_all EXIT`；`cp` 备份 + md5 对账（**禁** `git checkout/restore`） | 三处 md5 逐一相等；`check-spec-readonly` 21 册 rc=0；`git status -- spec/` 空 |
| 缺口范围：立项期「6 条」是否含历史（pre-M6）缺口？ | ✅已核定 | 全集取 **M7 流水表（`milestones.md`）LLVM 任务**（`git log` 取落地日期）⇒ 缺 **9** 条；pre-M6 的 `028t`/`046t`/`060t` 断裂为 M6 前口径、**不扩范围**（另记「新发现」） | 现场统计：M7 LLVM 10 任务 − changelog 已有（082t）= 9 |
| 任务书「6 条」陈旧计数 | ✅已修（按主会话预检 #3 授权） | 改「事实」「接口规范 §1」「验收 #1」为现场数 9，并注明立项后新落 `087t`/`088t`/`089t` | §「事实」现场统计口径落纸 |
| 三检查是否「层间不重复」/放错层 | ✅已核（L1 静态/机械；属 L1 定位） | 无 | `make check` 29s；三 target 各自 rc=0 |

判决：全部 finding 已修/已核定；无未修项 ⇒ 可标 `待验收`。

#### 第 1 轮 reviewer 验收

**独立重跑验证**（命令均在仓库根、相对路径）：
- **门控 rc**：`make check` EXIT=0（L1 全通过）；`check-no-residue` EXIT=0；`check_issues.py` EXIT=0；`check-patch-tree` EXIT=0；`check-index-blobs` EXIT=0。
- **缺口统计独立复核**（方法：`git log -- patches/ series` 取后端落地任务全集 × M7 流水表交集 − 已有 `082t`）：M7 LLVM 任务 = 10（`079t`/`080t`/`081t`/`082t`/`084t`/`085t`/`086t`/`087t`/`088t`/`089t`），changelog 现有 10 = 全覆盖，缺口确为 9 条 ✓；无漏补/多余（`083t` 不存在、`090t+` 无任务）✓。
- **条目抽查 ≥3 条**：`079t`（date=2026-10-11，3 文件 `DADAOISelLowering.cpp`/`DADAOCodeGen.td`/`DADAOInstrInfoFP.td`，CANNOT_SELECT 64→0）、`084t`（date=2026-10-12，过滤表 41→11，pass 132→152）、`089t`（date=2026-10-12，`DADAOSubtarget.cpp.patch`+`meson.build.patch`，pass 196→197）——日期/改文件/解锁数与 `git show --stat` 及 commit message 逐项一致 ✓；体例与既有行一致 ✓。
- **口径行**：`components/llvm-project/changelog.md` 第 5 行含"组件补丁变更后，任务收尾须在**同一变更**内"；`Process-01 §10` 第 162 行对应规则；不与既有条文矛盾 ✓。
- **三检查入 L1 证据**：`check` 依赖链含 `check-isa-coverage`/`check-spec-numbering`/`check-spec-changelog`（Makefile 第 445 行，grep 实证）；target 定义各有独立行。**三者各自注入→FAIL**（证据脚本 SHOW=1 真实输出）：① isa-coverage tsv 附伪行→`FAIL: 与真源不一致`（rc=1）→`cp`+md5(`6297bc3f`)还原→rc=0；② spec-numbering 重复首标题→`FAIL (2 violation(s))`（rc=1）→`cp`+md5(`e333ef6b`)还原→rc=0；③ spec-changelog 附录插 `SPEC-999t`→`FAIL (1 violation(s))`（rc=1）→`cp`+md5(`e333ef6b`)还原→rc=0。证据脚本 31/31 PASS ✓。
- **矩阵重生成正当性**：`git diff` 仅第 9-10 列（ISel 证据列，如 `pat:DADAOCodeGen.td.patch:333`→`:333;:608`）变化，前 8 列不变（机械性 ✓）；`gen_isa_coverage.py --check` rc=0（提交内容 = 生成器输出 ✓）；`--check` 现绿 ✓。diff 量级：54+52 行证据列更新。
- **不回归**：`make check`(L1) EXIT=0 ✓；`make check-modules`(L2) PASS（picolibc-tests fail=0、test-semihost PASS、QEMU 86/86）✓；check 依赖链原 23 target 未缺（现 26 = 23+3）✓。
- **独立反例**（不与④重复）：从 `check` 依赖链删除 `check-spec-numbering`→证据脚本 `[FAIL] Makefile: check-spec-numbering in check deps expected=1 actual=0`（TOTAL=31 FAILED=1，RESULT: FAIL）→`cp`+md5(`38905edb`)还原→回绿 31/31 PASS ✓。
- **工作区快照对账**：审阅前后 `git status --porcelain -uall` 一致；目标文件 md5 不变（Makefile=`38905edb`，milestones=`e209a799`）✓。

**非阻断发现**：①「新发现②」称"pre-M6 的`028t`/`046t`/`060t` 亦缺"——`046t` 实际未触碰 `patches/`（仅 series 重建），且早期任务 `013t`/`014t`/`019t`–`025t` 亦缺条目（changelog 回溯至 `026t`，属文件创建前的历史截断），建议收尾时修正式描述但不阻断 M7 交付。② `milestones.md` 两条「待排期」规划项收口注释为追加说明（"已由 `INFRA-069t` 落地"），可接受。

**判定：Accepted**——验收标准 4 项全部由 reviewer 独立重跑通过；缺口 9 条无误；三检查各自注入→FAIL→还原→回绿有完整 md5 证据；越界（矩阵重生成）正当且必要（基线即红）；无阻断项。

#### 提交与文件集审核（architect，2026-10-12）

- **档位**：**正常提交**（reviewer 第 1 轮判决 `Accepted`）；本回合另含**收尾文本准确化**（`046t` 除外 + pre-M6 准确清单）与 `ISS-200` 登记。
- **分支提交**：`ad912ca`（`INFRA-069t` 分支，已 `merge --squash` 后删除）。
- **落地提交**：`b61664b`（`master`，2026-10-12 23:57）。
- **文件集对账**：显式 staging **8** 个路径（**A=1 + M=7**；禁 `git add -A`）——A = 本任务书（此前未入库）；M = `Makefile`、`components/llvm-project/changelog.md`、`docs/Process-01-*`、`.tao/knowledge/{milestones.md,issues.yaml,llvm-isa-backend-matrix.md,llvm-isa-backend-matrix.tsv}`。与完成区「修改文件」逐条一致（`issues.yaml` 为本轮遗留登记），**未含**两份未跟踪外来任务书（`INFRA-070t`/`SPEC-135t`）✓
- **交叉复核**（architect 本机重跑）：`make check` rc=0 / `make check-modules`(L2) rc=0 / `check-no-residue` rc=0 / `check-patch-tree` rc=0 / `check-index-blobs` rc=0 / `check_issues.py` rc=0（**26 open / 9 closed** = 25/9 + 本轮 `ISS-200`）；未 `push`。
