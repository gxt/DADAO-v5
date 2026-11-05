# SPEC-185t: spec 非 spec 引用清理

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-184t`/`SPEC-186t`/`SPEC-188t`/`SPEC-189t`/`SPEC-190t`/`SPEC-187t`（均已完成；spec 正文已定稿）
**状态**：已验证

## 执行环境
本地；只删 `spec/` 内对非 `spec/` 目录的引用标记，不改任何规范语义。

## 背景

用户裁定（2026-11-05）：

> 「清理 spec 目录下的各文件的交叉引用，尤其是对非 spec 目录的文件的引用，全部清理掉。」
> 边界选 **A**：只删非 spec 引用，保留 spec 内部互引。
> 引用处理选 **A1**：只删引用标记，保留句子；不内联 ADR/契约内容。

现场统计（2026-11-05）：

- `Machine-v5-测试机运行环境.md`：`ADR-*` 65 处
- `Toolchain-01-汇编语言.md`：`ADR-*` 9、`contract-*` 14、`.tao/contracts` 6、`.tao/knowledge` 2、`contracts/` 12、`tools/` 3
- `spec/README.md`：`ADR-*` 3、`contract-*` 30、`.tao/contracts` 3、`docs/` 12、`contracts/` 17、`manifests/` 1、`tests/` 6、`tools/` 12
- 其它 19 册主要只有 spec 内部互引（`SimRISC-*`/`DADAO-*`/`Machine-v5`/`Toolchain-*`）

## 目标

1. 删除 `spec/*.md` 中对 **非 spec 目录** 的引用：
   - `ADR-*`
   - `contract-*` / `contracts/*`
   - `.tao/contracts/*` / `.tao/knowledge/*`
   - `docs/*`
   - `tests/*`
   - `tools/*`
   - `manifests/*`
   - `0628`
   - 外部 URL（`http://`/`https://`）
2. 保留 **spec 内部互引**：`SimRISC-*`、`DADAO-*`、`Machine-v5`、`Toolchain-*`、`spec/*.md`。
3. `spec/README.md` 只保留 spec 册索引：
   - 全部分册清单
   - Tiny/Node 投影
   - 推荐阅读顺序
   - 删除 contracts/tests/tools/manifests/docs 等非 spec 投影行；若某节整体是非 spec 内容，删除该节。
4. 同笔重算 `manifests/spec-readonly.lock.toml` 中所有被改 spec 册的 sha；未改册不变。

## A1 规则（只删标记）

- 优先只删引用 token，例如：
  - `……建立首张页表。[ADR-0043 D10]` → `……建立首张页表。`
  - `见 contract-isa §3` → 删除引用；若整句仅为指针，删除该句（不新增语义）
- 不把 ADR/contract 的规则内联进 spec；不新增数值/编码/异常语义。
- 若删除后句子语法不完整（只剩“见/参见”），允许最小删除“见/参见”短语；逐处记录。
- 不改变任何“应当/必须/不得”的规范强度。

## 范围 / 非范围

**在范围内**：`spec/*.md`（22 册）、`spec/README.md`、`manifests/spec-readonly.lock.toml`、本任务书、`milestones.md`。

**不在范围内**：`.tao/**`、`contracts/**`、`docs/**`、`components/**`、`tests/**`、`tools/**`、`Makefile`、ADR、门控脚本。

## 验收标准

1. **非 spec 引用清零**：`ADR-`、`contract-`、`.tao/`、`contracts/`、`docs/`、`tests/`、`tools/`、`manifests/`、`0628`、`http(s)://` 在 `spec/*.md` 活正文 0 命中（历史段/变更记录是否保留由现场判定并披露；默认历史段也不得保留非 spec 路径引用）。
2. **spec 互引保留**：`SimRISC-*`/`DADAO-*`/`Machine-v5`/`Toolchain-*`/`spec/` 引用仍在（数量不减少；README 索引仍指向 spec 册）。
3. **语义零改动**：`git diff` 只能删除引用 token / 指针句 / README 非 spec 行；不得新增或改写规范句。脚本对“删除引用后正文”做归一化比对，差异仅为被删 token/空行。
4. **README**：只索引 spec 册；profile/阅读顺序存在；contracts/tests/tools/manifests/docs 投影 0 命中。
5. **锁**：所有被改册 sha 与 `sha256sum` 逐字相等；未改册不变。
6. **门控**：`check-spec-readonly`/`check-spec-refs`/`check-spec-drift`/`check-spec-changelog`/`check-spec-numbering`/`check-spec-purity`/`check-spec-cite-targets`/`check-spec-codeblocks`、`check-milestones-fresh`、`make check`（L1）rc=0。
7. **反例可达 FAIL**：写回一处 `[ADR-xxxx]` 或 `contract-isa §x` ⇒ 断言 FAIL；`cp`+`md5sum -c` 还原后回绿。
8. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是“去引用”，不是“去内容”：句子保留，规则不搬。
- 若某处删除引用后无法判断语义，保留现场并留问，不自行补写。
- 与其它 spec 任务串行改锁；当前 186t/188t/189t/190t/187t 均已合入，可直接执行。
- 原 `SPEC-185t`（spec 自包含 + README 索引迁移）是主会话误拟，已由本任务书取代；本任务不新增册头、不重写索引结构。

## 未决（下发前确认）

1. 历史段/变更记录中的旧 ADR/contract 引用是否也删；默认删（保持“spec 内无非 spec 引用”）。
2. `spec/README.md` 中纯非 spec 的投影表是否整节删除；默认删除。
3. `Toolchain-01` 中若引用是句子主干（如“见 contract-isa 的编码表”），是否允许最小删除“见…表”短语；默认允许并逐处记录。

## 完成区

**测试结果**：一键证据 `.work/evidence/SPEC-185t/run.sh` 19/19 PASS（RUN_RC=0）；基线审计 223 → 改后 0；9 门控 + `make check`（L1）全 rc=0；反例注入 FAIL→`cp`+md5 还原 PASS。
**修改文件**：`spec/README.md`、`spec/Machine-v5-测试机运行环境.md`、`spec/Toolchain-01-汇编语言.md`、`manifests/spec-readonly.lock.toml`、`.tao/knowledge/milestones.md`、本任务书。
**验收结果**：
- 审计（audit.py）：`spec/*.md` 非 spec token 223→0；按类 ADR 78 / contract- 50 / .tao 25 / contracts 29 / docs 18 / tests 7 / tools 15 / manifests 1；http(s)/0628 基线即 0。日志 `.work/log/spec/SPEC-185t-audit-{before,after}.log`。
- 互引：21 册跨册互引逐册计数不变（`semantics.py` PASS）；README 链接 21/21 册。
- 语义：diff 仅删除（新行均为旧行字符子序列；删除段含非 spec token）；README 恢复 `定位说明`/`规范修订流程`/`册维护约定`/`Rationale`，`投影表` 改为 spec-only 锚点；逐项清单 `.work/log/spec/SPEC-185t-deletions.log`。
- 门控：check-spec-readonly/refs/drift/changelog/numbering/purity/cite-targets/codeblocks、check-milestones-fresh、`make check` 全 rc=0。
- 锁：Machine-v5 / Toolchain-01 sha256 同笔重算；其余 19 册不变（check-spec-readonly 21 OK）。
- 反例：临时树写回 `[ADR-9999]` ⇒ audit rc=1 + readonly-lock rc=1；`cp` 备份 + `md5sum -c` 还原 ⇒ 双 rc=0（未触碰真实 spec 树）。
**新发现/坑**：worktree 的 `.work/` 是指向主工作树的软链，证据脚本不能用自身路径推导仓库根（须 `git rev-parse --show-toplevel`）；运行期临时树不得放 `.work/log/**`（会触发 `check-run-artifacts` A3 红）。任务书删除对象是明确 token 列表；不在列表内的任务号/里程碑/ISS/门控名（如 `QEMU-079t`、`M11`、`ISS-157`、`check-asm-prose`）按口径保留。
**遗留问题**：
- `Toolchain-01` §11/§12 仅剩标题：唯一内容是指向非 spec 的整句指针，按 A1 整句删除；为保持 §13 编号连续未删标题，正文为空。
- README 基线无显式 Tiny/Node profile 节与「推荐阅读顺序」节；按「不新增内容」只保留五组 spec 分册索引（阅读顺序）与 Machine-v5 行（Tiny/Node），未新增章节。
- 外部悬空指针（root README、`docs/Process-02/06`、`docs/README`、`contract-asm`、`MEMORY`）不在本任务范围，已登记待后续任务修。

## 审阅记录

#### 第 1 轮 engineer 自审

逐行审查 4 个被改文件 + diff，finding/处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| reviewer：README 整节过度删除（定位/修订流程/维护约定/Rationale/投影表） | ✅已修 | 从 HEAD 恢复五节，仅删非 spec 指针；投影表改 spec-only 锚点句 | audit 0 / semantics PASS / 门控 rc=0 |
| README 删表后内部引用总数变化 | ✅已核对 | 互引判据为「21 册跨册互引逐册不变」；README 链接 21/21；未新增规范内容 | semantics.py PASS |
| Toolchain §11/§12 成空节 | ⏸延后（披露） | 指针句整句删除；保留标题以保编号连续；空心句按 A1 不润色 | check-spec-numbering rc=0 |
| 基线/注入树放 `.work/log` 触发 check-run-artifacts A3 | ✅已修 | 运行期临时树移出 `.work/log/**` | `make check` rc=0 |
| worktree `.work` 软链致审计扫到主工作树 | ✅已修 | audit.py 加 `--root`；run.sh 用 `git rev-parse --show-toplevel` | 基线 223 / 改后 0 |
| 是否存在非删除式改写 | ✅已核对 | semantics.py 子序列 + 删除段 token/强度词断言 | semantics PASS |
| reviewer F5：配对被跳过的旧行未入整行删除断言 | ✅已修 | `pair_lines` 返回全部未配旧行并逐行断言含 token | semantics PASS |

判决：无未修 finding；状态 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑（reviewer 本人执行，任务 worktree HEAD=`f0d1253c`，不采信完成区转述）**
- 自写审计（非采信 223 转述）：基线 `git archive HEAD spec` 非 spec token **223**（ADR-78 / contract-50 / .tao25 / contracts29 / docs18 / tests7 / tools15 / manifests1；0628、http=0）；工作树 22 册 **0**（逐类 0；`grep -rnE 'ADR-|contract-|\.tao/|contracts/|docs/|tests/|tools/|manifests/|0628|https?://' spec/*.md` ⇒ 0 行）。
- 门控 9 项本人重跑 **rc=0**：check-spec-readonly（21 volumes OK）/refs（0 violations）/drift/changelog/numbering/purity/cite-targets/codeblocks/milestones-fresh；`make check`（L1）**rc=0**（`repository checks (L1): PASS`）。
- 证据脚本重跑：`.work/evidence/SPEC-185t/run.sh` ⇒ **RC=0，PASS 19 / FAIL 0**（与完成区 19/19 一致；逐项输出见 `.work/log/spec/SPEC-185t-*.log`）。
- **独立注入（改真实被测产物，非脚本自检）**：`cp` 备份 + md5 `f89cac2c…` ⇒ Machine-v5 §1.1 行尾写回 `[ADR-0043 D1/D4/D5]`（md5 变 `b476ff8b…`）⇒ 重跑同一 run.sh ⇒ **RC=1、FAILS=5**（after audit actual=1；check-spec-readonly rc=2；make check rc=2）⇒ `cp` 还原 + `md5sum -c` OK（回 `f89cac2c…`）⇒ 再跑 ⇒ **RC=0、19/19**；注入前后 6 文件 md5 与 `git status` 与审查开始快照逐项一致。
- 锁：21 条 sha 与 `sha256sum` 现值**全等**；仅 Toolchain-01 `025a5cd0→d7822c77`、Machine-v5 `180bdb0b→b858d55d` 变化，其余 19 册锁值与 HEAD 内容**逐字未变**。
- 语义（reviewer 自写字符级核验）：**无任何新增行**；删除段仅为「引用 token + 包裹标点」或指针短语（Machine-v5 43 行内删 + 2 整行、Toolchain 15 行内删 + 4 整行指针 + 2 空行、README −101 纯删除）；被删规范强度词 **0**；未见语法残句。
- 互引：21 册跨册计数**逐册不变**；README 五组索引 **21/21** 链接（README 内部提及 48→26 / 33→12 / 8→2 系整节删除所致，链接未减；Toolchain-01 少 1 处自指来自被删 §12 指针行）。
- Toolchain §11/§12 空标题：临时树删标题 ⇒ `check_spec_refs --spec-dir` **RC=1**（4 violations「节标题未找到」），原样 **RC=0** ⇒ **保留空标题是门控必需**（删标题会让 `contract-asm.md` 的 `[Toolchain-01 §11/§12]` 悬空），§13/§14/附录编号未动。
- 范围：`git diff` 仅 6 文件（README / Machine-v5 / Toolchain-01 / lock / milestones / 本任务书），无 ADR/contracts/docs/tests/QEMU/gem5/Makefile 改动、无未跟踪残留；完成区 13 行 ≤30、状态 `待验收`；完成区数字（223→0、按类 78/50/25/29/18/7/15/1、19/19、9 门控+L1、锁 2 册）与现场**逐项相符**。

**finding（均文档级，不改判，供 architect 处置）**
1. README 删节致**外部指针悬空 ≥8 处**：根 `README.md:16`、`docs/Process-02:20/34`、`docs/Process-06:61`、`docs/README.md:26`、`.tao/contracts/contract-asm.md:260`、`.tao/knowledge/MEMORY.md:17/50` —— 均在本任务禁改范围，须另立任务或收尾同步。
2. README「册维护约定」中纯 spec 条款（标题编号 / 无编号尾段 / 纯净化 / 改动记录粒度 / 只读册纪律）活文档失唯一家（仅存 archive；版本号语义、互锁组另有册头与根 README 覆盖）＝目标 3「只保留索引」的既定代价，是否迁移请 architect 定。
3. 完成区含运行期路径 `/tmp/opencode/SPEC-185t-tmp/`（AGENTS「任务书不写运行期路径」）。
4. Toolchain §1「指令集权威：本规范只规定书写形式。」、§2.4「取值范围：…位宽与取值范围。」删后语义空心（非语法残句）；§14 删「指令语义与编码以 … 为准，」分句（A1 允许的指针句删除）。若润色须同笔重算锁。
5. `semantics.py` 配对时被跳过的旧行不进「整行删除须含 token」断言（本次无实质影响，reviewer 已独立逐行覆盖），建议补断言。

**判决：Accepted** —— 验收命令块在 reviewer 自己的重跑下全部通过、约束无违反；上述 5 条按「文档级小错不阻断」记 finding。

#### 第 2 轮 reviewer 验收（返工复验）

**重跑（reviewer 本人执行，HEAD 仍 `f0d1253c`，不采信完成区转述）**
- 非 spec token：自写审计基线 **223 → 0**；`grep -oE 'ADR-|contract-|\.tao/|contracts/|docs/|tests/|tools/|manifests/|0628|https?://' spec/*.md | wc -l` ⇒ **0**。
- 恢复完整性：README 新增 **19 行**，逐行核验 **18 行 = HEAD 行的删除式子串**、**1 行 = 唯一新句**「投影落点属实现层，不在 spec 目录维护。」（本轮派单指定锚点）；`定位说明` 4 条 / `册维护约定` **9 条** / `Rationale` 5 条 / `规范修订流程` 五步齐全；删除段仅非 spec token（含表头/空行等脚手架）。除锚点外**无任何字符新增**，两 spec 卷 md5 与轮 1 逐字相同（A1 成立）。
- 互引：21 册跨册计数逐册不变；README 链接 **21/21**；README 内部提及由 26/12/2 回升至 **35/14/5**（基线 48/33/8，差额=已删非 spec 表格行）。
- 门控 9 项 **rc=0**（readonly `21 volumes OK`、refs `0 violations`、drift/changelog/numbering/purity/cite-targets/codeblocks、milestones-fresh）；`make check`（L1）**rc=0**（`repository checks (L1): PASS`）。
- 证据脚本：`run.sh` 干净重跑 **RC=0、PASS 19 / FAIL 0**（两次）。
- **独立注入①（本轮被改文件 README）**：备份 md5 `95502fec…` → 锚点句写回 `（见 \`contract-isa.md §3\`）` → 同一脚本 **RC=1、FAILS=3**（after audit actual=1；semantics FAIL；restore-audit rc1）→ `cp` 还原 `md5sum -c` OK → 重跑 **RC=0、19/19**。
- **独立注入②（专测 F5 修复）**：删 Machine-v5 一条**不含非 spec token** 的整行 → `semantics.py` **rc=1** 并打印「整行删除不含非 spec 引用 token」（轮 1 该路径不可达）→ 还原后 **rc=0** ⇒ F5 断言已真实补齐；`ALLOWED_NEW` 为**整句精确白名单**（非模式），无法掩盖其它新增。
- 锁：21 条 sha 与 `sha256sum` 全等；仅 Toolchain-01、Machine-v5 与 HEAD 不同，其余 19 册内容 == HEAD；锁文件自身 md5 与轮 1 相同（本轮未动锁）。
- 范围/体例：`git diff` 仍**仅 6 文件**，`adr/ contracts/ docs/ tests/ tools/ Makefile components/` 零触碰、无未跟踪残留；完成区 **14 行 ≤30**、无 `/tmp`/`/home`/`/mnt`/`~` 运行期路径（F3 已修）。

**finding（文档级，不改判，供 architect 处置）**
1. **README 内部悬空（新增）**：`规范修订流程` 步骤 4「投影缺失者记入本文『投影表』缺口」，而缺口表已删；未列入完成区登记清单。
2. **外部仍悬空（须真立后续任务）**：`docs/Process-02:20`（登记缺口表 + 投影表列）、`docs/Process-06:61`（历史版本表）、`.tao/knowledge/MEMORY.md:50`（投影/缺口表）、`.tao/contracts/contract-asm.md:260`（投影表 `Toolchain-01` 行 ③）、`docs/README.md:26`（投影表内容层）。**已消解**：根 `README.md:16`（册维护约定+版本号语义）、`docs/Process-02:34`（规范修订流程）、`MEMORY.md:17`（节级）。
3. 措辞：完成区/deletions.log 首句「diff 仅删除（新行均为旧行字符子序列）/所有改动均为删除」对 README 不完全成立（+1 锚点，虽已在同段另行披露）。
4. token 外删除两处已披露：册头 `> **状态**`（含 `SPEC-084t`，与「任务号按口径保留」略有出入）、步骤 3「（make check 相关目标）」；另 `纯净化` 条无法再写 `contract-*`/`.tao/` 字样（写入即违规），与门控实际规则存在表述落差——均属 token 口径的固有代价。
5. 轮 1 finding 4（Toolchain §1「指令集权威：本规范只规定书写形式。」、§2.4 空心句）**仍开放**（engineer 选择不润色以免改锁，已披露）。

**判决：Accepted** —— 返工项（F1/F2/F3/F5）在 reviewer 自己的重跑下全部复验通过，验收命令块全绿、范围与体例无违反；上述 5 条按「文档级小错不阻断」记 finding，其中 1、2 须 architect 在收尾/后续任务落实。

#### 收尾（architect，2026-11-05）

- F1：README「规范修订流程」步骤 4 的内部悬空已改为「缺口登记（投影缺失者登记，若有）」，不再指向已删缺口表。
- F2：5 处外部悬空指针另立 `SPEC-193t`。
- F3：完成区“仅删除”表述对 README +1 锚点不完全成立，已在完成区说明。
- F5：Toolchain 空心句按 A1 原样保留，登记遗留。
- 判决 Accepted，状态置 `已验证`。
