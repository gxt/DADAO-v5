# m15-spec-009: SimRISC 0.5.7 发布投影（README + 契约头 + 规范快照）

**模块**：spec
**项目里程碑**：M15
**依赖**：`m15-spec-008`（0.5.7 发布，**须先合入**）
**可并行分片**：否
**预估**：1 h
**档位**：小改（版本投影 + 归档快照）
**状态**：已验证

## 背景

用户 2026-11-20 授权：SimRISC 版本 **0.5.7** 已发布（`m15-spec-008`），随之修改**引用它的 README 与契约投影**。

`check-spec-drift` 的判据：`contract-*.md` 的 `> **版本：X.Y.Z**` 必须等于 `README.md` 版本表的「已发布版本」列。

## 目标

1. **根 `README.md`**：`| SimRISC | 0.5.6 | 0.5.7-rc |` → `| SimRISC | 0.5.7 | — |`（已发布列取 0.5.7；在研列无在研版本时写 `—`）；
2. **契约版本头**（与 0.5.7 对齐）：
   - `.tao/contracts/contract-isa.md`：`> **版本：0.5.6**` → `0.5.7`；
   - `.tao/contracts/contract-fp.md`：标题与版本头 `0.5.6` → `0.5.7`；
   - `.tao/contracts/README.md` 索引行里的 SimRISC 版本号同步；
   - `.tao/contracts/contract-elf.md` 的「（SimRISC 0.5.4）」引用同步为 0.5.7；
3. **规范快照**：`python3 tools/spec/gen_spec_archive.py --apply`（或现行等价命令）生成 `.tao/archive/SimRISC-0.5.7/`，与 0.5.6 同套路；
4. 契约**正文语义零改动**——只动版本行/引用文本。

## 验收（逐条贴真实 rc）

1. `check-spec-drift` **rc=0**（README 已发布列 = 各契约版本头）；
2. `check-spec-archive` **rc=0** 且 `check-spec-archive-verify` 通过（快照存在、内容与 0.5.7 声明一致）；
3. `check-spec-changelog`/`numbering`/`purity`/`refs`/`codeblocks`、`check-manifests-guard`、`check-contracts-dir`、`check-contract-relocs`、`check-knowledge-refs` 全 rc=0；
4. **正文零改动**：契约剥掉版本行后与 `HEAD~1` 逐字节相同；
5. **可达 FAIL ≥2 路**（临时树/`cp`+md5）：① 把 README 改回 `0.5.6` ⇒ `check-spec-drift` 红；② 删快照目录 ⇒ `check-spec-archive` 红。

## 约束

独立 `git worktree`；不提交 git；**不改契约语义**、不改 `spec/` 正文；术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 完成区

**测试结果**：一键证据脚本 **59/59 通过（rc=0，返工后重跑）**；失败原因：无。另跑 `check-spec-cite-targets`/`check-archive`/`check-no-residue`/`check-dirs` 全 rc=0；`check-temp-dirs` rc=2 只报**他任务** 5 个陈旧临时目录（本任务目录不在列）。

**修改文件**：
- `README.md`：标题 `# DADAO for SimRISC 0.5.7`；版本表 `| SimRISC | 0.5.7 | — |`；说明段补口径句（见「返工 R2」）
- `.tao/contracts/contract-isa.md`（版本头）、`contract-fp.md`（标题 + 版本头）、`README.md`（fp/isa 索引行）、`contract-elf.md`（引用 `contract-isa.md`（SimRISC 0.5.7））、`contract-abi.md`（引用 `contract-isa.md`（0.5.7），**仅版本 token**）
- 新增 `.tao/archive/SimRISC-0.5.7/`：13 册 + `PROVENANCE.md`（`gen_spec_archive.py --apply` 生成，二次运行幂等 `SKIP … 一致`）
- 运行期证据目录内 `run.sh` + `zerodiff.py`（不入仓）

**验收结果**（真实 rc）：
1. `check-spec-drift` rc=0；`check-spec-archive` rc=0（声明 9 / 磁盘 10）；`check-spec-archive-verify` rc=0（`OK   SimRISC-0.5.7（13 文件@清单快照）`）
2. 验收第 3 条 9 个门控全 rc=0（changelog/numbering/purity/refs/codeblocks/manifests-guard/contracts-dir/contract-relocs/knowledge-refs）
3. **正文零改动**：`zerodiff.py` 以**固定基线**（分支分叉点 `7bf88240`，非 `HEAD~1`/`git status`/`HEAD:`）判 6 文件 P1（剥版本投影后逐字节相同，差异 0 行）+ P2（变更对只在投影位点：README 3、isa 1、fp 2、contracts/README 2、elf 1、abi 1）全 PASS；`contract-abi` 的 diff 只有那一处版本 token
4. **可达 FAIL 4 路**（均 `cp`/`mv` + md5 对账还原并回绿）：① README 改回 `0.5.6` ⇒ drift rc=2 且提及 0.5.6；② 移走快照目录 ⇒ archive rc=2 且提及 `SimRISC-0.5.7`；③ 契约加一行正文 ⇒ zerodiff 判红；④ abi 引用改回 `0.5.4` ⇒ 引用值断言判红
5. 快照内容：13 册逐文件 sha256 同时等于基线 `spec/` 与 0.5.7 释出提交（`m15-spec-008` 合入）的 `spec/`；`PROVENANCE.md` 快照提交 = 固定基线；`--apply` 幂等
6. 落地自证：相对固定基线 `git diff --stat` = 实现面 10 增 10 删（6 文件）+ 本任务书；另 14 个快照文件；`spec/` 0 改动，无越界。（`HEAD` 已含 architect 的 WIP 提交 `79af549d`，返工改动为未提交的 3 文件）

**返工（第 1 轮 reviewer Needs Revision 之后）**
- R1（必改）`contract-abi.md:5` 的 `contract-isa.md`（0.5.4）→（0.5.7），只动版本 token；diff 仅该行；`run.sh` 增 abi 引用值断言 + 注入④（改回 0.5.4 ⇒ 判红 ⇒ md5 还原回绿）。
- R2（顺手）README 说明段补 `无在研版本时「在研版本」列写 —。`；作为**唯一声明的非版本改动**纳入零改动判据（工作树 1 / 基线 0，「声明补句真实新增」断言 PASS）。
- R3（记录不改）`contract-see.md:5` 保持 `SimRISC-11（0.5.4）`：该文件名只存在于 ≤0.5.4（0.5.6 起改名 `SimRISC-11-核芯功能扩展指令.md`），只改版本号 = 死路径配活版本，文件名口径归 architect（见「遗留问题」）。
- 复验：`run.sh` rc=0（59 PASS / 0 FAIL；较首轮增 abi/补句断言 3 项 + 注入④ 4 项）；10 个必跑门控逐条 rc=0；零改动与快照判据未放宽。

**新发现/坑**：
- `.cache/refs/DADAO.wiki` 是 `gen_spec_archive.py --derive` 的**环境前置**，worktree 默认不带（gitignored）；证据脚本已自动软链主工作树 `.cache`，缺失时判 FAIL 并说明（`make fetch-refs` 可重建）。
- PROVENANCE 的「快照提交」口径 = 生成时的 anchor HEAD（本任务为派单提交）；已核该树 `spec/` 与释出提交 0 差异，并加断言「快照 = 释出提交 spec/ 内容」。
- 零改动判据里「版本 token 值」不作判据（`0.5.4`/`0.5.7` 都归一为 `<V>`）⇒ 版本**值**必须靠显式断言（本轮 abi 即如此），二者缺一不可。

**遗留问题**：
- `contract-see.md:5` 的 `SimRISC-11（0.5.4）` **不改**：旧文件名 `SimRISC-11-其它.md` 仅存在于 ≤0.5.4，0.5.6 起已改名 `SimRISC-11-核芯功能扩展指令.md`；只改版本号 = 死路径配活版本（更错），须连文件名口径一并裁定 ⇒ 归 architect。
- `contracts/README.md` fp 行「60 条」 vs `contract-fp.md` 正文 65 条：旧账，超出本任务「版本投影」范围，未改。
- `check-temp-dirs` 报 5 个他任务陈旧临时目录（m14-linux-008/009/017/025、ksym），非本任务产物，未代删。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查改动（5 个文件 diff + 快照 14 文件 + 证据脚本），findings 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `README.md`「在研版本」说明段未覆盖 `—`，与表格写法存在文义落差 | ❌不修 | 无（任务书明文指定在研列写 `—`；改说明段属口径变更，须 architect 裁定） | 已在「新发现/坑」登记 |
| F2 `contracts/README.md` fp 索引行仍写「60 条」（合约正文为 65 条） | ⏸延后 | 无（超出「版本投影」范围，避免顺手改正文） | 已在「新发现」登记，建议单独任务 |
| F3 `contract-abi.md:5` 引用 `contract-isa.md（0.5.4）`、`contract-see.md:5` 引用 `SimRISC-11（0.5.4）` 仍陈旧 | ⏸延后 | 无（两文件未列入任务范围；仅 elf 的引用按任务要求同步） | 已登记遗留，建议 architect 决定是否立小任务 |
| F4 `check-spec-archive-verify` 依赖 `.cache/refs/DADAO.wiki`，worktree 缺该目录时 rc=2（首轮实撞） | ✅已修 | 证据脚本加环境前置：缺失时软链主工作树 `.cache`，仍缺失则判 FAIL 并说明 | 删 symlink 后重跑：自动软链并回绿（50/50、rc=0） |
| F5 PROVENANCE 快照提交取派单提交而非释出提交，易被误读为「快照取自非发布树」 | ✅已修 | 证据脚本增断言「快照逐文件 sha256 = 0.5.7 释出提交 `spec/`」 | 该断言 PASS（0 差异）；且 `git diff --stat` 两提交 `spec/` 为空 |
| F6 证据脚本初版用 `has_line`/`gate` 仅打印期望=实际，易写死覆盖计数 | ✅已修 | 册数、基线册数、变更对计数全部现场派生（`git ls-tree`/`diff -U0`），无硬编码计数 | 脚本 50 项均为派生比较；注入③证明 zerodiff 可判红 |

判决：所有 finding 已修或已按范围/裁定登记，无未修的可修项 ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收

**重跑（全部仓库根执行、reviewer 亲自跑，不采信完成区转述）**
- `check-spec-drift`=0；`check-spec-{changelog,numbering,purity,refs,codeblocks}`=0；`check-manifests-guard`/`check-contracts-dir`/`check-contract-relocs`/`check-knowledge-refs`=0。
- `check-spec-archive`=0（声明 9 / 磁盘 10）；`check-spec-archive-verify`=0（`OK   SimRISC-0.5.7（13 文件@清单快照）`）；`check-archive`/`check-spec-cite-targets`/`check-no-residue`=0；`check-temp-dirs`=2（5 项全为他任务目录、本任务不在列，与完成区一致）。
- 投影逐项核：README 标题 `# DADAO for SimRISC 0.5.7`、表行 `| SimRISC | 0.5.7 | — |` ↔ `contract-isa`/`contract-fp` 版本头 `0.5.7`、`contracts/README` 两行 `0.5.7`、`contract-elf` 引用 `（SimRISC 0.5.7）`，四向一致。

**正文零改动（自写比对，固定基线 = 分支分叉点 `7bf88240`；不用 `git status`/裸 `diff`/`HEAD:`）**：`README.md` + 4 份契约打码（版本号/`—`）后逐字节相同、各变更块打码后全等 ⇒ rc=0；`git diff --name-only <分叉点> HEAD` = 20 文件（5 实现 + 本任务书 + 快照 14），`spec/` 0 改动，与完成区对账一致。

**快照**：13 册 `cmp` 对 `spec/` 现文件 13/13 相同（sha256 逐文件相等）+ `PROVENANCE.md`；`gen_spec_archive.py --apply` rc=0、13 条全 `SKIP …一致`、归档 md5 前后不变。

**可达 FAIL（reviewer 独立注入，`cp`/`mv` + md5 还原）**：① README 改回 `0.5.6` ⇒ `check-spec-drift` rc=2（`错误 2 个`、输出含 0.5.6）→ 还原 rc=0、README md5 `339d417c…` 相等；② 移走快照 ⇒ `check-spec-archive` rc=2（`A1 目录缺失：SimRISC-0.5.7`）+ `archive-verify` rc=2（`FAIL SimRISC-0.5.7`）→ 还原 rc=0、`PROVENANCE` md5 `7a4000ef…` 相等、册数 13。运行期证据目录内 `run.sh` 我重跑 rc=0（50 PASS / 0 FAIL），其 3 路注入同样红→还原回绿；断言有可达 FAIL 路径、计数均现场派生，脚本合格。

**约束核验**：独立 worktree + 分支名相符 ✓；未提交 git（收尾 `git status -uall` 为空）✓；契约语义零改动 ✓；`spec/` 零改动 ✓；无「银行」误译 ✓；本记录无运行期路径 ✓。

**判决：Needs Revision（仅 1 处必改）** — `contract-abi.md:5` 仍写 `contract-isa.md`（0.5.4）：与本次已改的 `contract-elf.md:7`（同形、同指 `contract-isa.md`）自相矛盾（0.5.7 vs 0.5.4）；本任务已确立「引用版本跟随当前」口径却只改其一 ⇒ 属 0.5.7 发布投影的闭环缺口。**改法**：该处版本文本 `0.5.4` → `0.5.7`（只动版本），改后重跑 `check-spec-drift` + 正文零改动比对。

**findings（给 architect，不阻断）**：F-a `contract-see.md:5` `spec/SimRISC-11-其它.md`（0.5.4）——该文件名仅存在于 ≤0.5.4（0.5.6 起改名 `SimRISC-11-核芯功能扩展指令.md`、现 0.5.7），只改版本号 = 死路径配活版本，且旧名在多处 ADR/归档属历史层 ⇒ 须连文件名口径一并裁，**有独立理由不入本轮**；F-b `contracts/README.md` fp 行「60 条」vs `contract-fp.md` 正文 65 条（旧账，F2 已登）；F-c README 在研列 `—`：说明段只定义「无改动=与已发布相同」、未定义 `—`，与 Toolchain 行写法不一 ⇒ 建议补半句，文档级自明、不阻断。

### 第 2 轮 engineer 自审（返工）

按第 1 轮 reviewer 的三条意见逐条处置（第 1 轮 F3 拆为 R1/R3 两半）：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1 `contract-abi.md:5` 仍指 `contract-isa.md`（0.5.4），与已改 `contract-elf.md:7` 同形冲突 ⇒ 漏改 | ✅已修 | 只把该处版本 token `0.5.4`→`0.5.7`，别处不动 | 该文件 `git diff` 仅 1 行 1 对；zerodiff `P1 差异 0 行 / P2 1 组`；引用值断言 PASS；注入④ 判红→md5 还原→回绿 |
| R2 README 表用 `—` 而说明段未定义该写法 | ✅已修 | 说明段末补「无在研版本时「在研版本」列写 `—`。」，表格不动 | 作为唯一声明的非版本改动纳入 zerodiff（「声明补句真实新增」工作树 1 / 基线 0）；README P1 差异 0 行、P2 3 组 |
| R3 `contract-see.md:5` `SimRISC-11（0.5.4）` 不改 | ❌不修（按 reviewer 判定记录） | 无 | 理由已入「遗留问题」：旧文件名仅存于 ≤0.5.4，只改版本号=死路径配活版本 |
| S1 返工可能夹带无关改动 | ✅自证 | 无额外改动 | 相对固定基线实现面 6 文件 10 增 10 删；`spec/` 0 改动；快照未动（`--apply` 二次全 `SKIP`） |

判决：R1/R2 已修并复验，R3 按裁定不改且已记录 ⇒ 状态保持 `待验收`，提请复审。

### 第 2 轮 reviewer 验收

**重跑（仓库根执行，真实 rc）**：运行期证据目录内 `run.sh` rc=0（**59 PASS / 0 FAIL**，4 路注入全走「注入→判红→`cp`/`mv`+md5 还原→回绿」）；`zerodiff.py <分叉点>` rc=0（6 文件 P1/P2 全 PASS + 「声明补句真实新增 1/0」）；门控抽样 `check-spec-drift`/`check-spec-changelog`/`check-manifests-guard`/`check-contracts-dir`/`check-spec-archive` 全 rc=0（drift `错误 0 个`、archive `声明 9 / 磁盘 10`）。

**R1 必改项自验**：`git diff <分叉点>..HEAD -- .tao/contracts/contract-abi.md` = **1 文件、1 行 1 对**，仅 `（0.5.4）`→`（0.5.7）`；派生交叉核对 `contract-isa 版本头 = abi 引用 = README 已发布 = contract-fp 版本头 = 0.5.7` ⇒ `CROSSCHECK=ALL_EQUAL`。

**零改动仍有效（我自己注入，`cp`+md5 还原）**：① `contract-isa.md` 正文 +1 字符 ⇒ zerodiff rc=1（P1 差异 1 行 + P2 增删行数不等）→ 还原 md5 `3a0c2c7b…` 相等、回绿 rc=0；② README 说明段**非声明句** +1 字符 ⇒ rc=1（P1 差异 1 行 + P2 1 组超出投影位点）→ 还原 md5 `11304a63…` 相等、回绿 rc=0 ⇒ 声明补句白名单非放水口。

**R2 验证**：本轮提交对 `README.md` 只有说明段追加 `无在研版本时「在研版本」列写 —。`，**版本表未动**（表行改动在第 1 轮提交）。

**范围**：`git show --name-only HEAD` = 3 文件（`contract-abi.md` / `README.md` / 本任务书）；`git diff 79af549d..HEAD -- .tao/archive/` = 0 文件；`gen_spec_archive.py --apply` rc=0 全 `SKIP …一致`；`spec/` 相对分叉点 0 改动；复核前 `git status -uall` 为空（返工已全部落提交，我未提交）。

**findings（文档级，不阻断）**：完成区写「较首轮增 abi/补句断言 3 项 + 注入④ 4 项」合计 7，实测新增 **10** 项（另含 P1/P2 abi、D 声明补句、P2 README 2→3 组），总数 59 无误 ⇒ 数字表述笔误，architect 收尾改；`contract-see.md:5` 与 `contracts/README.md`「60 条」两项遗留维持第 1 轮 finding。

**判决：Accepted** — 第 1 轮唯一必改项已闭环，验收命令在我自己的重跑下全绿、反例可判红、约束无违反。
