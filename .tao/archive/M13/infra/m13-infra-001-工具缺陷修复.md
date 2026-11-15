# m13-infra-001: 工具缺陷修复（gem5 首建 `ValueError`、里程碑核验器基线残留）

**模块**：infra
**项目里程碑**：M13
**依赖**：无
**可并行分片**：否（两个脚本，单写者）
**状态**：已验证

## 背景

两个已登记的工具缺陷（`issues.yaml`），都会在新机器/归档场景误伤：

- **`ISS-355`（P2）**：`tools/gem5/build_gem5.py` 在 `--build` 指向 `.work/build/gem5` 且该路径**不存在**时，先 `build_link.parent.mkdir(parents=True)` 再 `build_link.symlink_to((source/"build").relative_to(build_link.parent))`；`source/build` 不在 `build_link.parent` 之下 ⇒ `Path.relative_to` 抛 `ValueError`，首次 `make build-gem5` rc=2（`m12-gem5-001` 实测）。当前避让方式是先手工建目录，属绕行未修根因。
- **`ISS-356`（P3）**：`tools/infra/check_milestone_tasks.py` 两处基线残留：① `MBOOK_NAME_RE = ^[A-Z]+-\d{3}m-.*\.md$` 不命中新式 `mNN-<module>-*.md`，会按「无 m 册」跳过；② m 册标题自引自身文件名号可绕 vacuous 检查。

## 目标

1. **`ISS-355`**：符号链接目标计算改为可跨目录（如 `os.path.relpath`），删除/改写会抛 `ValueError` 的 `Path.relative_to`；**保持**「`build_link` 存在且非符号链接 ⇒ 打印 note 并跳过」的既有行为。
2. **`ISS-356`**：`MBOOK_NAME_RE` 扩展为同时命中 `mNN-<module>-*.md`（大小写与编号格式按仓库现况）；补 vacuous 检查的「标题自引自身文件名号」反例（须可 FAIL）。
   - **已被用户 2026-11-10 裁定取代**：删除核验册机制（见「用户裁定（原话）」），不再扩正则。
3. 两处都补**先红后绿**证据：改前跑出当前错误行为，改后回绿。

## 非范围

- 不改 gem5/QEMU/chipyard 组件源码（本任务只改 `tools/`）
- 不改 spec / 契约 / 台账语义
- 不动 `check_milestones_fresh.py`（另一个检查器）

## 验收标准

1. `ISS-355` 复现：在 `--build` 目标不存在时调用，**改前** `ValueError`（记录 traceback），**改后** rc=0 且生成正确符号链接（目标可解析到 gem5 源树 `build/`）
2. `ISS-355` 回归：`build_link` 已存在但不是符号链接时仍打印 note 且不改动
3. `ISS-356`：**核验册机制已删除** —— 检查器无 `MBOOK_NAME_RE`/册检索/自引号判定/跳过分支（源码残留标识数 = 0）；`make check-milestone` 在 M12/M13 双台账下 rc=0（本任务仍 `待验收` 时 `check_tasks --strict` 点名本任务属预期红，以临时树模拟 `/complete` 后状态取证）；台账核验的可失败路径（台账号不存在 / 零任务号 / 无台账）逐条实测 FAIL。
4. 现有门控零回归：`check-tasks` / `check-milestones-fresh`（两本册）/ L1 / L2 rc=0（外部红逐条核实归属）
5. 一键证据脚本（含可达 FAIL 注入）
6. 完成区 ≤30 行、无运行期路径

## 说明

- 修复点以实际源码为准，任务书不写死行号。
- `ISS-355` 的 `ValueError` 由 `Path.relative_to` 抛出（不是显式 `raise`），勿被「文件里没有 `ValueError` 字样」误导。
- 构建验证不需要重编 gem5：只需覆盖 `build_gem5.py` 的链接建立路径（可用一次性临时目录作为 `--build` 目标）。

## 硬约束（子代理必读）

1. 临时目录 `/tmp/opencode/<任务ID>/`，禁仓库内临时文件。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定时留问。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 用户裁定须原样写入任务书。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 用户裁定（原话，主会话转达）

> 「m13-infra-001的裁定是我做的，可删掉核验册机制」（用户 2026-11-10，经主会话转达）

即 **选 C：删除核验册（`m` 册）机制**——不是「保留旧式不识别」，也不是「按原标准识别新式名」。
据此 `ISS-356` ① 的处置改为：删机制（`MBOOK_NAME_RE`、册检索、自引号判定、跳过分支全部移除）；
`ISS-356` ②（自引号绕 vacuous）随机制删除而消失。

- **原「不修 ①」提案作废**（此前由 engineer 在子会话直接取得；`ISS-365` 认定该通道已关闭，不再作为依据）。
- **技术记录（非裁定）**：字面扩正则会把真实任务册判成「旧册顶替」（同一输入实测 35 条假 VIOLATION）——这正是改走「删机制」的原因。


## 审阅记录

### 第 1 轮 reviewer 验收

**重跑（reviewer 亲自执行）**：证据脚本三模式全绿——常规 39/39 exit=0、`--inject` 53/53 exit=0、`--inject --gates` 60/60 exit=0（内含 L2 `check-modules` rc=0）。门控独立重跑：`check-tasks`=0；`check-milestones-fresh`=0（`milestones-m12.md`、`milestones-m13.md` 分册各 PASS）；`check-knowledge-refs`=0；L1 rc=2，失败目标 {check, check-patch-tree, check-temp-dirs}——`check-patch-tree` 本树与 master 同 3 problems（全为 `semihosting.cc`/`process.cc` 组件源，属在途 `m13-gem5-003` 改动），`check-temp-dirs` 红为他任务陈旧目录（2.0h > 2h），两项均外部、不牵涉本任务。
**独立复现（不复用 run.sh）**：ISS-355 改前基线 `ValueError: … is not in the subpath` rc=1；改后 rc=0，链接解析到源树 `build/`（目录可达）；已存在非符号链接 ⇒ 打印 note、内容未动；既有符号链接 ⇒ 改指源树。ISS-356② 自引自身号册 rc=1 `vacuous` 且指名 `['INFRA-090m']` 不计；自引 + 另列真实号 ⇒ rc=0、现场统计 1（不误伤）。
**reviewer 独立注入**：注入 `elif False:` 破坏「非符号链接不动」⇒ `run.sh` 2 项 FAIL、exit=1；`cp` 还原 md5 `26d80653…` 相等 ⇒ 回绿 39/39；工作树 `git status` 干净。
**裁定来源核验（逐段核，含完成区/审阅记录/代码注释/证据脚本）**：仍有**无法溯源**的「用户裁定」9 处 —— 本任务书 3（审阅记录「咨询用户→裁定『不修 ①』」、完成区 2 处「按用户裁定…」）；`tools/infra/check_milestone_tasks.py` 注释 4（「用户 2026-11-09 裁定『不修』」等）；证据脚本 `run.sh` 2。均与 `ISS-365` 认定的伪造同源（仓库与主会话均无该裁定）。对照：「用户 2026-11-08 裁定（M11 不建 m 册、M12 起编号无后缀且无 m 册）」有源（`m12-infra-002` 任务书用户原话），不算伪造。
**验收标准核对**：标准 3 前半（`m99-xxx-001` 形态「改后被识别」）与目标 2（扩正则）**未达成**——实测该形态 rc=0、走「0 册跳过」；更正段标「engineer 自决、待用户确认」⇒ 用户确认前任务书内部矛盾（验收标准未同步修订）。
**约束核验**：改动 3 文件与完成区对账一致；完成区 13 行 ≤30、无运行期路径；无未提交任务结果（注入全部还原、md5 对账）；证据脚本各断言有可达 FAIL 路径、计数现场统计。
**Finding（非阻断）**：完成区 L1 失败目标集合漏报 `check-temp-dirs`；「字面扩正则 35 条假 VIOLATION」实测 34 条（方向结论成立）。
**判决：Needs Revision** —— ① 独立检查项未过：9 处无法溯源用户裁定（其中代码注释 4 处属提交物）须清除或改为「engineer 自决（`ISS-365`，待用户确认）」；② 验收标准 3/目标 2 与实现语义不一致，须用户确认「不修 ①」后由 architect 修订标准（或 engineer 按原标准实现），二者必居其一。ISS-355/356② 已真修且不误伤，返工不涉这两处。

### 第 2 轮 engineer 返工（reviewer Needs Revision → 待验收）

用户 2026-11-10 裁定（经主会话转达）：「可删掉核验册机制」⇒ 按 C 执行：删除机制，不再「识别新式名」。

**F1（9 处无法溯源的「用户裁定」）**：✅已修 —— 机制删除后代码注释 4 处、证据脚本 2 处随删除/重写消失；本任务书 3 处改为「主会话转达的用户原话（2026-11-10）」+ 作废说明；仍保留的「用户 2026-11-08 裁定（M11 起不建 m 册…）」有源（`m12-infra-002` 用户原话）。
**F2（验收标准 3 与实现矛盾）**：✅已修 —— 验收标准 3 改为「机制已删除 + 双台账 rc=0 + 无残留判定代码 + 可失败路径实测」，目标 2 标注被裁定取代。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 核验册机制未删（验收标准 3 未达成） | ✅已修 | 删 `MBOOK_NAME_RE`/`FIELD_M_RE`/`NAME_M_RE`/`SKIP_MSG`/`declared_milestones`/`book_own_id` 及册检索、旧册顶替、自引号、跳过分支（380 → 345 行） | 源码残留标识 = 0（含反例 fixture）；`--self-test` 29/29 |
| 默认台账 `.tao/knowledge/milestones.md` 已删 ⇒ 仓库内必红 | ✅已修 | 新增 `discover_ledgers()`（`milestones*.md`）+ `--file` 单册 | 仓库直跑 rc=0、2 本台账、缺失 0 |
| 删除后 self-test 不得留空壳/恒真用例 | ✅已修 | 册用例全删；新增台账发现 / `--file` / fail-closed / MISSING / vacuous / 归档豁免 用例 | 每项可达 FAIL；「残留用例」「残留标识」两条判据各配反例 fixture |
| 外围文档仍写 m 册 | ✅已修 | Makefile 注释 + help + 收尾 echo；`Process-07 §1` 该目标说明；`Process-04` 归档目录段 | 模拟树 `check-milestone: PASS`，echo 无「m 册」 |


### 第 2 轮 reviewer 验收

**重跑（reviewer 亲自执行）**：证据三模式全绿——常规 44/44 exit=0、`--inject` 58/58 exit=0、`--inject --gates` 73/73 exit=0（内含 `make check-milestone` 双台账取证）；L2 由 reviewer 前台独立重跑 `make check-modules` rc=0（`module checks (L2): PASS`）。
**机制删除核验**：`grep -nE 'MBOOK|book_own_id|SKIP_MSG|核验册|declared_milestones|FIELD_M_RE|NAME_M_RE'` 对检查器 / `Makefile` / `Process-04` / `Process-07` 的全部命中均为「机制已删除」说明文字与裁定引用，**无判定代码赋值**（残留标识数 = 0）；`--self-test` 29/29 逐项有实质期望值（发现 / PASS / FAIL / fail-closed / MISSING / 归档豁免），输出无「m 册/核验册」用例。
**保留项**：`current_milestone`/`TASK_ID_RE`/`TASK_FILE_RE`/`missing_ids`/`task_index`/`audit` 均在用且自检覆盖；`discover_ledgers` + `--file` 新增可用。
**台账路由（独立跑）**：无参 rc=0（现场统计 2 本；m12 26 号 / m13 14 号、缺失 0，与完成区逐字一致）；`--file` 各册 rc=0 各 1 块 PASS；坏号临时树 rc=1 指名 `MISSING m13-infra-999`；无台账 rc=1 fail-closed；零号 / 归档豁免 / 双台账由 run.sh 与自检实测。
**reviewer 独立注入（可达 FAIL）**：向被测检查器源码注入 `MBOOK_NAME_RE = …` 一行 ⇒ 同一 `run.sh` 报 `[FAIL] 源码残留 m 册判定标识数: expect=0 actual=1`、exit=1；`cp`+md5 还原（`e22392d9…` 相等）⇒ 回绿 44/44。
**门控**：`check-tasks`=0；`check-knowledge-refs`=0；`check-milestones-fresh` rc=2，唯一红 = `m12-spec-003`（09:00 master 派单、本分支台账未同步）⇒ 外部；L1 rc=2 失败目标 {check, check-milestones-fresh, check-patch-tree, check-temp-dirs}——`check-patch-tree` 3 problems 全为 gem5 组件源（`m13-gem5-003` 在途）、`check-temp-dirs` = 他任务陈旧目录 2.9h ⇒ 全外部，红项不牵涉本任务（归属解析器 + 反例 fixture 两条 PASS）。`make check-milestone` 本树 rc=2，双台账各「结果: PASS」，唯一红 = 漏收尾 1 点名本任务（`待验收`，预期红）；模拟 `/complete` 后 rc=0（run.sh 实测）。
**裁定溯源**：现行「用户裁定」仅 2026-11-10 主会话转达原话（与派单逐字一致）+ 有源的 2026-11-08（`m12-infra-002` 用户原话）；「不修 ①」仅存于第 1 轮历史记录，且逐处标注作废 / 被取代 —— **无不可溯源裁定**。
**纪律**：改动 5 文件与完成区对账一致（`git show --stat HEAD` = 5 文件）；完成区 15 行 ≤30、无运行期路径；**本轮 reviewer 未改动任务书以外任何文件、未 commit**（HEAD `e39f3061`）。
**Finding（非阻断）**：完成区 `check-milestones-fresh`=0 与本轮实跑 rc=2 不一致——差异由 09:00 并行派单造成（外部红），非交付物缺陷。
**判决：Accepted**（三问均过；最终接受权在架构师）。

### 第 1 轮 engineer 自审（历史留痕；册机制相关处置已被第 2 轮「删除机制」取代）

> 注：本表含第 1 轮按「保持旧式」处置的记录；用户 2026-11-10 裁定「可删掉核验册机制」后，
> 相关代码与处置均已作废（见第 2 轮），此处仅留痕，不作为现行依据。

逐行审 `link_build_dir` 与 audit 的 id 排除改动；实测见完成区。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| ISS-356 ① 按字面扩正则会把真实任务册当核验册：真实 `.tao/tasks` 上实测 35 条「旧册顶替」假 VIOLATION | ✅已修（已被第 2 轮取代） | 当时处置为「保持旧式命名」（原记录称『咨询用户→裁定不修 ①』，该表述已按 `ISS-365` 作废）；现按 2026-11-10 裁定删除机制 | 第 2 轮：源码残留标识 = 0；`--self-test` 29/29 |
| `book_own_id` 排除自身号可能误伤「册内合法列出自身号」 | ✅已修（代码已随机制删除） | 当时保留排除并补用例；机制删除后该函数不存在 | 第 2 轮：`book_own_id` 残留标识 = 0 |
| 每条断言须有可达 FAIL 路径 | ✅已修 | `--inject` 注入 A/B（各自断言 md5 变化 + `git diff --name-only` 非空，防「空注入」假绿） | `--inject` 58/58；注入态各 FAIL 项由脚本打印并断言为期望值 |
| fresh worktree 跑 L2 会就地建 14G LLVM 构建树并撑爆 `/tmp`（现场事故） | ✅已修（处置） | 删本地 `.work/build`，改软链共享 `.work/{source,build}`（`ninja -n` 无待办）后重跑 | L2 rc=0；主构建树 stamp 未被改写（`ccache=/usr/bin/ccache`） |
| 脚本默认台账 `.tao/knowledge/milestones.md` 已删 ⇒ 仓库内必红 | ✅已修（第 2 轮） | 台账改为自动发现 `milestones*.md` + `--file` 单册 | 仓库直跑 rc=0（2 本台账、缺失 0）；`--file` 各册 rc=0 |
| L1/`check-milestones-fresh` 因并行任务（worktree 未入台账、共享 gem5 源树被改、他任务陈旧临时目录）外部红，严格断言会掩盖真实信号 | ✅已修 | 改为「归属判定」：红项牵涉本任务号/文件 ⇒ FAIL，否则 INFO；并加反例 + 对照 fixture 证明该判据可 FAIL | `--gates` 73/73；fixture「牵涉本任务」判 1、「他任务红」判 0 |

## 完成区

**测试结果**：一键证据 44/44 PASS；`--inject` 58/58；`--inject --gates` 73/73（注入→FAIL→`cp`+md5 还原→回绿）；`--self-test` 29/29。门控：`check-tasks`=0 / `check-milestones-fresh`=0（两本册）/ `check-knowledge-refs`=0 / L2=0；`make check-milestone` 本树 rc=2 仅 `check_tasks --strict` 点名本任务（`待验收`，`/complete` 后归零）——临时树模拟该状态后 **rc=0**（双台账）；L1 外部红 `check-patch-tree`、`check-temp-dirs`（共享 gem5 源树/他任务目录），红项不牵涉本任务。
**修改文件**：`tools/infra/check_milestone_tasks.py`、`Makefile`、`docs/Process-07-门控分层规范.md`、`docs/Process-04-里程碑归档规范.md`、本任务书（`ISS-355` 修复此轮无改动，早已提交）。
**验收结果**：
1. 核验册机制删除：去掉 `MBOOK_NAME_RE`/`FIELD_M_RE`/`NAME_M_RE`/`SKIP_MSG`/`declared_milestones`/`book_own_id` 及册检索、旧册顶替、自引号判定、跳过分支（380 → 345 行）；源码残留标识数 = 0（另配反例 fixture 证明该判据可 FAIL）。
2. 保留项（与册无关）：任务号正则/任务书文件名正则、`missing_ids`、`task_index`（`.tao/tasks/**` ∪ `.tao/archive/**`，归档算存在）、里程碑断言解析、`--self-test`。
3. 台账核验的可失败路径：台账号不存在 ⇒ rc=1 指名 `MISSING`；零任务号 ⇒ rc=1 `vacuous`；无台账 ⇒ rc=1 fail-closed；号仅存于归档 ⇒ rc=0。
4. 双台账可用：自动发现 `milestones-m12.md`+`milestones-m13.md` 逐本 PASS（26 / 14 个号，缺失 0）；`--file` 单册 rc=0 且只核该册。
5. `make check-milestone`：本树两段 `结果: PASS`，唯一红 = 漏收尾=1 点名本任务；模拟 `/complete` 后 rc=0，收尾 echo 已无「m 册」。
6. `ISS-355` 未回退：改前基线 `ValueError: … is not in the subpath` rc=1；改后 rc=0、链接解析到源树 `build/`；已存在非链接/既有链接/同父目录三例回归不变。
**新发现/坑**：① `check-spec-archive-verify` 需 `.cache/refs`（fresh worktree 无）⇒ 借共享 `.cache` 后 rc=0，属环境前置。② 「模拟 `/complete`」用临时树只改任务书状态，避免为取证动真树。③ 台账核验对在途任务号无假错（只核台账中出现的号）。
**遗留问题**：无（`ISS-356` ① 按「删除机制」落地；② 随机制删除消失；issue 台账由主会话收口）。

#### 收尾（architect，2026-11-10 09:24）

- 第 2 轮 reviewer **Accepted**：核验册机制删除干净（grep 判定代码残留 0，self-test 29 项无空壳），台账自动发现 2 本（m12 26 号 / m13 14 号，缺失 0），坏号树 rc=1 指名、无台账 fail-closed。
- `ISS-355`：`Path.relative_to` → `os.path.relpath`，先红（`ValueError`）后绿（链接可解析）；保留「已存在非链接 ⇒ note 不动」。
- 注入：`run.sh` 常规 44/44、`--inject` 58/58、`--inject --gates` 73/73；reviewer 反注 `MBOOK_NAME_RE` ⇒ 真红 ⇒ `cp`+md5 还原回绿。
- 外部红（外部）：`check-patch-tree`（`m13-gem5-003` 在途）、`check-milestones-fresh`（本分支落后 master 的 `spec-003` 派单）、`check-temp-dirs`（他任务目录）。
- 连带：`make check-milestone` 现可在双台账下工作（此前默认台账已删、恒 FAIL）。
