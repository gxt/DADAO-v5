# m15-infra-005: `.manifests.toml` 目录防护第一波（spec / .tao / .tao/knowledge）

**模块**：infra
**项目里程碑**：M15
**依赖**：`m15-infra-003`（盘点结论：6 目录无白名单、`spec` 新增册逃锁）
**可并行分片**：否（跨 spec/.tao/tools/docs）
**预估**：3–4 h
**档位**：中改
**状态**：已验证

## 背景与裁定（用户 2026-11-18）

`refs` 事件暴露：目录与文件没有「只能放什么」的机械约束，新增逃逸、删除无声。用户裁定分步改造，**第一批** = `spec/`、`.tao/`、`.tao/knowledge`。

用户原话要点（逐条落纸）：
1. 第一批三目录；`.tao/.manifests.toml` **只管顶层**，另**支持子目录递归选项**（后续模块如 `patches` 需要）。
2. 清单文件名统一 **`.manifests.toml`**（带点）。
3. `spec/` **只允许 spec 模块任务修改，且需裁定**；`owner` 只作声明、门控只打印不判红。
4. `manifests/spec-readonly.lock.toml` 内容迁入 `spec/.manifests.toml`，**注释全部删除**，只留文件名 + sha256（用户：项目由一人维护，历史看 git log，不必保留过程注记）。
5. `.tao/.manifests.toml` 列当前子目录 + `README.md`，**不准建子目录和新文件**。
6. `.tao/knowledge/.manifests.toml` 列现有文件 + `owner`；**删除 `cfx-register-usage.md`**（改为移到 `docs/` 并就地修订 `ADR-0046` 的引用）。
7. 门控名 **`check-manifests-guard`**；**`check-spec-readonly` 合并进去**（原目标删除）。

## 清单格式（统一 schema）

```toml
schema = 1
owner = "spec"              # 声明性；门控只打印
subdirs = []                # 允许的子目录；空 = 禁止建子目录
recursive = false           # true ⇒ 对 subdirs 递归应用本清单的 files 规则（第一批全 false）

[files."<name>"]
sha256 = "…"                # 可选；有则校验
owner  = "spec"             # 可选；条目级声明
```

- **清单自身不计入集合**（`files` 里不得列 `.manifests.toml`）。
- `files` 的 key 必须是**该目录的直接子文件**（不含子目录内文件）。
- 非递归模式下：目录下新增/删除**任何**文件或子目录 ⇒ 红。

## 三份清单（内容以现场为准，不得照抄本文数量）

### `spec/.manifests.toml`
- `subdirs = []`、`recursive = false`、`owner = "spec"`。
- `files` = 现场 `spec/*.md` 全部册（22 册，现场 `ls` 计数），每条带 `sha256`（从现有 `manifests/spec-readonly.lock.toml` 迁入，**注记全删**）。
- 迁完 `git rm manifests/spec-readonly.lock.toml`。

### `.tao/.manifests.toml`
- `subdirs = ["adr","archive","contracts","knowledge","tasks"]`、`recursive = false`。
- `files` = `README.md`（有则列；现场核对）。

### `.tao/knowledge/.manifests.toml`
- `subdirs = []`、`recursive = false`。
- `files` = 现有文件（**排除** `cfx-register-usage.md`，它被移走），条目带 `owner`：
  - `MEMORY.md`、`milestones-m14.md`、`milestones-m15.md`、`milestones-m16.md`、`discussing.md`、`issues.yaml` → `main-session`
  - `mirrors.md`、`nodes.md` → `infra`

## `cfx-register-usage.md` 与 ADR-0046

- `git mv .tao/knowledge/cfx-register-usage.md docs/cfx-register-usage.md`。
- **就地修订** `.tao/adr/adr-0046-cfx-register-profile.md` 第 26 行的路径引用（`knowledge/` → `docs/`），**不改任何 decision 内容**；ADR docstring/状态不改。
- 核 `docs/` 是否有对应索引需要补一行（`docs/README.md` 若列文件则补；不新建文件）。

## 门控改造

1. **新增** `tools/infra/check_manifests_guard.py` + `make check-manifests-guard`（**L1**，进 `_locked-check`）：
   - 发现全仓 `.manifests.toml`（`git ls-files -z | grep '\.manifests\.toml$'`），逐个校验；
   - **双向断言**：实际文件集合 == `files`；实际子目录集合 == `subdirs`；多一个少一个都红；
   - 有 `sha256` 的条目逐字节校验；`recursive = true` 时对子目录递归（第一批无使用者，但要有 `--self-test` 覆盖）；
   - `owner` 仅打印；错误信息给 `目录:文件` 与「多出/缺失」；
   - **必须能失败**：`--self-test` 覆盖「新增文件 / 删除文件 / 改 sha256 / 多建子目录 / 清单自身被列入 / recursive 分支」六类注入。
2. **删除** `check-knowledge-dir`（目标 + `tools/infra/check_knowledge_dir.py`）。
3. **删除** `check-spec-readonly`（目标 + `tools/infra/check_spec_readonly.py`），能力并入 guard（反向断言由 guard 的 `spec/.manifests.toml` 双向校验天然提供）。
4. 同步：`Makefile`（`_locked-check`、`GATE_LOCKED_TARGETS`、help、`check`/`check-full` 成员）、`docs/Process-07`（门控表：删 2 加 1）、`docs/Process-06`（spec 保护改为读 `spec/.manifests.toml`，删锁文件描述）、`AGENTS.md`（加两条：① `spec/` 只允许 spec 模块任务修改且需用户裁定；② 清单/锁类文件只写数据、不写过程注记，变更依据看 git log）。

## 验收（逐条贴真实 rc）

1. 三份清单在位，`check-manifests-guard` rc=0。
2. **六类注入**（`--self-test` 或手工）各产生可达 FAIL；`recursive = true` 分支有一条真实子目录用例（可在临时树构造）。
3. `spec/` 新增一册（临时）⇒ guard **rc≠0**（这是本轮要堵的核心缺口）；删除 ⇒ rc≠0；还原 ⇒ rc=0。
4. `sha256` 校验：改一册 spec ⇒ rc≠0；还原 ⇒ rc=0。
5. `manifests/spec-readonly.lock.toml` 已删；`grep -rn "spec-readonly" Makefile tools docs` = 0（历史任务书/ADR 除外，逐条列明）。
6. `cfx-register-usage.md` 在 `docs/`；`ADR-0046` 引用已改；`grep -rn "knowledge/cfx-register-usage" . --exclude-dir=.work --exclude-dir=.cache` = 0（历史任务书除外）。
7. `make check` 中相关门控全绿：`check-manifests-guard`、`check-knowledge-refs`、`check-contracts-dir`、`check-dirs`、`check-archive`、`check-spec-refs`、`check-milestones-fresh`。
8. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**。
2. **不改版本号**；不动 `spec/` 正文（只读校验）；不动 `contracts/`。
3. 清单**不写任何过程注记**（用户裁定）；迁移时注记丢弃，不加 `note` 字段。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。
5. 若发现某目录实际内容与「只列文件」冲突（如 `.tao/knowledge` 有子目录），**停在待裁定**。

## 待裁定

- `锁门控` → `清单门控` 的措辞修正因超出授权已回退；如需该措辞，请用户另行授权。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：新增 guard 脚本 + 三份清单、Makefile 接线、docs/AGENTS 同步、cfx 迁移、两处消费脚本改读新清单。**未改**：`spec/` 正文、`contracts/`、任何版本号、ADR decision。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `load_manifest` 解析失败分支引用已删变量 `rel` ⇒ NameError，红不出预期原因 | ✅已修 | 提前定义 `where = str(path)` | 新增自检例「清单不可解析」：rc=1 且命中「无法解析 TOML」 |
| F2 条目 `owner` 打印被 `sha is None: continue` 跳过 ⇒ 无 hash 条目永不打印 owner | ✅已修 | owner 打印前移到 hash 判断前 | 实跑打印 8 条 knowledge owner；`quiet` 模式不打印 |
| F3 清单发现原用 `git ls-files` ⇒ 未提交清单被静默跳过（fail-open） | ✅已修 | 一律遍历磁盘（剪掉 `.git`、`.work`、`.cache`；3100 文件 30 ms） | 未提交清单/新增文件注入均红 |
| F4 recursive 原按「每层都要存在全部 subdirs」⇒ 基线自测误红 | ✅已修 | 顶层双向、递归层单向 ⊆ | 基线 rc=0；两例 recursive 注入 rc=1 且原因命中 |
| F5 self-test 只判 rc，可能「红在别的原因」 | ✅已修 | 每例加「期望错误子串」匹配 | 9/9 均「原因命中=True」 |
| F6 证据脚本 `grep -A6 GATE_LOCKED_TARGETS` 漏末行 ⇒ 假 FAIL | ✅已修 | 改 `sed -n '/^GATE_LOCKED_TARGETS/,/[^\\]$/p'` | 证据 45/45 PASS |
| F7 旧门控名残留于 Makefile/docs | ✅已修 | 改「原…门控」措辞 | `grep -rn spec-readonly Makefile tools docs` = 0 |

**判决**：7 条 finding 全部已修；证据脚本 45/45（rc=0）。状态 → `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录（我自跑，真实 rc；workdir = 任务 worktree，开工/收尾 `git status -uall` 均空，HEAD `7b2267ab`）**
- 清单正确性：三清单与现场 `ls` **逐项相等**（spec 22/22、`.tao` 1 文件+5 子目录、knowledge 8/8，多出/缺失/子目录 diff 全空）；旧锁 `git show 4aa0cb03:manifests/spec-readonly.lock.toml` 21 条 sha256 与 `spec/.manifests.toml` **0 差异**，另现场重算 22 条全 MATCH（`spec/README.md` 必须列，否则「多出文件」红）。
- 基线：`python3 tools/infra/check_manifests_guard.py` **rc=0**；`--self-test` **9/9 rc=0**；`make check-manifests-guard` **rc=0**；证据脚本（运行期证据目录 `m15-infra-005/run.sh`）**45/45 PASS rc=0**（我重跑，非采信），跑完 status 空。
- 6 路注入（`cp`+md5 还原、md5 相等）：新增册 rc=1「多出文件」｜删册 rc=1「缺失文件」｜改内容 rc=1「sha256 不符」｜spec 建子目录 rc=1「多出子目录」｜**`.tao/` 建子目录（任务书未列）rc=1**｜**清单自身写进 `files` rc=1**；还原后均 rc=0。
- `recursive` 临时树实测：顶层删文件红｜sub 多文件红｜sub 多目录红｜sub 空（单向 ⊆）绿｜`recursive=false` 同场景绿 ⇒ 开关真实生效。
- 删门控无残留：`grep -rn "spec-readonly\|check-knowledge-dir" Makefile tools docs AGENTS.md README.md tests/` = **0**；锁+两脚本已删；`_locked-check`/`GATE_LOCKED_TARGETS`/`.PHONY`/help/`_locked-check-modules`/`_locked-check-full` 全清。
- 能力：`check_numbering.py`、`check_spec_changelog.py` 改读新清单后 `files=21` **rc=0**。ADR-0046 **仅 1 行**路径、状态 `Proposed` 与 Decision 未动；三清单零注释、零 `note`（写 `note` ⇒ 门控 rc=1，实测）。越界：`git diff --name-status 4aa0cb03..7b2267ab` = 18 项与完成区一致，`spec/` 仅 `A spec/.manifests.toml`、`contracts/` 0 改动、无版本号变更。`make check` rc=2，断点 `check-isa-coverage`「找不到 llvm-mc」；`make -k check` rc=2（6 项：`check-isa-coverage`/`-width-sizes`/`-components`/`-linux-toolchain` 缺安装根、`check-temp-dirs` 报**其它**任务陈旧目录、`check-writer-guards` W5b 读共享 writer 注册表）——均未触及本任务改动面；本任务点名的 7 门控我重跑全 rc=0。

**阻断（1 条）：删清单 = 静默关闭门控（fail-open）**
- 实测：`rm spec/.manifests.toml` ⇒ guard **rc=0**（`清单 2；受检目录 2；文件 9；sha256 0`，spec/ 完全不受检）；`.tao/.manifests.toml`、`.tao/knowledge/.manifests.toml` 单删同样 **rc=0**；仅「三份全删」才红（`未找到任何 .manifests.toml`）。
- 对照：旧 `check-spec-readonly` 锁缺失 ⇒ **rc=1**（`lock file not found`，我抽旧脚本实测）；任务书 §门控改造 1 指定的 `git ls-files` 发现方式对该场景 READ-FAIL ⇒ rc=1（我模拟实测）。⇒ 能力回退 + 与任务书指定发现方式不符，`make check` 全绿即可绕过本任务要堵的核心缺口。
- **修法（架构侧已定）**：① 加**必需清单注册表**（`manifests/dir-guard-roots.toml` 或同类）列出「哪些目录必须有 `.manifests.toml`」，guard 读它逐个校验，**缺清单 / 目录不存在 ⇒ FAIL**，不用「扫到什么管什么」；② 注册表自身也纳入「必须有」语义（删注册表即红）；③ `--self-test` 各补一例（缺清单、缺目录）。

**待返工项（非阻断）**：`spec/README.md:76` 死命令 `make check-spec-readonly` → `make check-manifests-guard`（**用户已授权**），**同笔重算 `spec/README.md` 的 sha256**；**21 册技术册 sha256 一律不得变动**（改前/后逐条比对现清单）。

**豁免面（逐条）**：`.tao/adr/*`（9 处，不改 decision）、`.tao/contracts/{README.md:27,contract-dynlink.md:11}`、`.tao/tasks/spec/*`、`.tao/archive/**`（历史）、`.tao/knowledge/issues.yaml:626`（ISS-436 台账原话）。

**判决：Needs Revision**（阻断 1 条 + 待返工 1 条；其余验收项与硬约束在我重跑下全部通过）。

### 第 2 轮 engineer 自审（返工）

**范围**：注册表 + guard 取清单方式改造、self-test 补例、`spec/README.md:76` 门控名 + README sha256 重算、证据脚本扩充。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1（reviewer 阻断）删清单 = 静默关闭门控（fail-open） | ✅已修 | 新增 `manifests/dir-guard-roots.toml`；guard 改**按注册表逐个取清单**，缺清单即 FAIL 并点名目录 | 删 `spec/`、`.tao/`、`.tao/knowledge/` 清单各 rc=1（`ERROR: <dir>: 缺少清单 .manifests.toml`），`cp`+md5 还原后 rc=0 |
| R2 注册表自身可删（同类 fail-open） | ✅已修 | 注册表缺失/不可解析/`roots` 空 ⇒ FAIL | 删注册表 rc=1（「注册表缺失」），还原 rc=0 |
| R3 未登记的清单会被静默忽略（新增清单不生效） | ✅已修（选**报红**） | 游离清单 ⇒ FAIL 并提示登记一行；理由：只提示＝另一个 fail-open | 仓库根注入 `.manifests.toml` ⇒ rc=1（「游离清单」），删除后 rc=0 |
| R4 self-test 未覆盖「缺清单/缺目录」 | ✅已修 | 补 4 例：删清单、删注册表、登记目录不存在、游离清单 | `--self-test` 13/13（每例校验 rc + 预期原因子串） |
| R5 `spec/README.md:76` 死命令 | ✅已修（第 3 轮返工后为最终形态） | **仅命令名** `make check-spec-readonly` → `make check-manifests-guard`（其余文字不动）+ 同笔重算 README 的 sha256（`ebe91b62…`→`3f2d57a7…`） | `git diff a263bd7b -- spec/README.md` = 第 76 行 1 行、只差命令名；对照 `4aa0cb03`：21 册 **21/21 MATCH**；README 条目 == 现场 sha256（证据 4c） |
| R6 评审记录里一处具体 `.work/**` 路径使 `check-knowledge-refs` 红 | ✅已修（**披露**） | 仅把该处改为「运行期证据目录」措辞，判决原文与结论不动 | `make check-knowledge-refs` rc=0 |

**判决**：6 条全部已修；证据脚本 **72/72**（rc=0）。状态 → `待验收`。

### 第 3 轮 engineer 自审（返工）

**范围**：`spec/README.md:76` 回退超授权的 4 字措辞、重算 README sha256、订正自审/完成区措辞。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R7（reviewer 阻断）第 76 行改了 2 处，其中 `锁门控`→`清单门控` 超出授权 | ✅已修 | 回退为原文 `sha256` 锁门控，只保留命令名替换；同笔重算 README sha256 | `git diff a263bd7b -- spec/README.md` = 1 行且只差命令名（见完成区）；21 册 21/21 MATCH；证据重跑全绿 |
| R8 第 2 轮记录里另有一处具体证据脚本路径，使 `check-knowledge-refs` 红 | ✅已修（**披露**） | 仅把该处改为「一处具体证据脚本路径」措辞，判决/阻断原文不动 | `make check-knowledge-refs` rc=0 |

**判决**：R7 已修；证据脚本 **72/72**（rc=0）。状态 → `待验收`。

### 第 2 轮 reviewer 验收

**重跑（我自跑、真实 rc；开工/收尾 `git status -uall` 均空，HEAD `27671938`）**
- **第 1 轮阻断复验**（5 类注入 + 游离，均 `cp`+md5、`md5sum -c` 全 OK、还原后基线 **rc=0**）：删 `spec/` 清单 **rc=1**「`spec: 缺少清单 .manifests.toml`」｜删 `.tao/` 清单 **rc=1** 点名 `.tao`｜删 `.tao/knowledge/` 清单 **rc=1** 点名｜删注册表 **rc=1**「注册表缺失（…删它等于关闭本门控）」｜注册表加 ghost **rc=1**「`ghost-dir: 注册表登记的目录不存在`」｜仓库根游离清单 **rc=1**「游离清单…请在注册表加一行」。
- **游离清单选报红已实现、理由成立**：只提示 ⇒ 新增清单静默不生效 = 第二个 fail-open；docstring A0 / `Process-06 §5` / `Process-07` 三处口径一致。
- `--self-test` **13/13 rc=0**；12 个 FAIL 例 **全部 `原因命中=True`**、`原因命中=False` = **0**（基线例 rc=0 无 needle）。
- 证据脚本我重跑 **72/72 PASS rc=0**（4b 注册表 4 例各含「rc+原因子串+ERROR 点名+md5 对账+回绿」、4c 21 册对 `git show 4aa0cb03` 现算 + README 现场 sha），跑后 status 空。
- 门控我逐个跑 **16/16 rc=0**：manifests-guard、knowledge-refs、contracts-dir、dirs、archive、spec-refs、milestones-fresh、spec-numbering、spec-changelog、no-residue、asm-prose、spec-purity、spec-codeblocks、asm-list、tasks、manifest-check。
- **21 册**：与旧锁 `4aa0cb03` **21/21 MATCH**（我自解析重算，非采信）；清单 22 条现场重算 0 不符；`git diff 4aa0cb03..HEAD -- spec/` = 仅 `spec/README.md` + `spec/.manifests.toml`（**21 册本体 0 改动**）。
- **越界**：`git diff --name-status 4aa0cb03..HEAD` = **20 项**，全在「任务书 + 三清单 + 注册表 + guard + 删两脚本/锁 + 消费者 + README 一行 + 文档」内；`contracts/` 0；版本号 0。
- **我第 1 轮记录未被篡改**：`git diff a263bd7b..HEAD` 对本任务书只改 **1 处**（一处具体证据脚本路径 → 「运行期证据目录 `m15-infra-005/run.sh`」，为 `check-knowledge-refs` 回绿），**判决 / 阻断 / 待返工三条原文一字未动**。

**阻断（1 条）：`spec/README.md:76` 实际改动超出授权原话**
- `git diff 4aa0cb03..HEAD -- spec/README.md` = **仅第 76 行 1 行**，但该行改了 **2 处**：① `make check-spec-readonly` → `make check-manifests-guard`（**授权内**）；② `sha256 锁门控` → `sha256 清单门控`（**授权外 4 字**）。授权原话（主会话转达）只写「死命令修正（A→B）+ 同笔重算 sha256」，任务书内亦无覆盖②的用户原话。
- 完成区写「改 `spec/README.md`（**仅**第 76 行**门控名**）」、自审 R5 写「改为 `make check-manifests-guard`」⇒ **与实际不符（②未披露）**。
- **修法二选一**：**A** 回退 `清单门控`→`锁门控`（4 字）+ 同笔重算 README sha256（2 文件），其余不动；**B** 补用户对这 4 字的**追认原话**落任务书「待裁定」段 + 把完成区措辞改为准确描述（并入 A/B 一并订正「仅…门控名」）。若主会话转达的授权本就含措辞修正，请补原话落纸后改判。

**判决：Needs Revision**（阻断 1 条；**返工主体本身已验证有效**——注册表 fail-closed 全部通过，其余验收项与硬约束在我重跑下全部通过）。

### 第 3 轮 reviewer 验收

**重跑（我自跑、真实 rc；开工/收尾 `git status -uall` 均空，HEAD `c76bc552`）**
1. **越授权 4 字已回退**：`git diff 4aa0cb03..HEAD -- spec/README.md` = **单行**（±各 1 行）；把新行的 `make check-manifests-guard` 还原回旧命令名后与旧行**逐字节相同**（我用 python 归一化比对 = `True`），`sha256 锁门控` **原词保留**、`清单门控` 已消失 ⇒ 该行**只差命令名**。
2. **README sha256 同笔重算**：`spec/.manifests.toml` 相对第 1 轮 `7b2267ab` **仅 `README.md` 一条** sha 变化（`ebe91b62…` → `3f2d57a7…`）；21 册对照 `4aa0cb03` 我自解析重算 = **21/21 MATCH**；清单 22 条现场重算 **0 不符**；`git diff 4aa0cb03..HEAD -- spec/` 仍只有 `spec/README.md` + `spec/.manifests.toml`（**21 册本体 0 改动**）。
3. **措辞留痕**：`## 待裁定` 新增「`锁门控` → `清单门控` 的措辞修正因超出授权已回退；如需该措辞，请用户另行授权」✓；自审 R5 与完成区均已改为「**仅命令名** / 其余文字不动」并更新 sha `3f2d57a7…` ✓（原「仅第 76 行门控名」已订正）。
4. **我第 2 轮记录未被篡改**：`diff` 两个 ref 抽出的该节 = **只改 1 行**（`.work/evidence/…` → 「一处具体证据脚本路径」，为 `check-knowledge-refs` 回绿），**`阻断（1 条）` 与 `判决：Needs Revision` 两行原样**，全节 `.work` 字面残留 **0**。
5. **门控**：`make check-manifests-guard` **rc=0**、`make check-knowledge-refs` **rc=0**。
6. **非阻断（记一笔）**：小节顺序为「第 2 轮 engineer 自审 → **第 3 轮 engineer 自审** → 第 2 轮 reviewer → 第 3 轮 reviewer」，第 3 轮自审被排在第 2 轮验收之前（engineer 落位时所致）；只影响阅读顺序，不改任何文字，无需返工。

**判决：Accepted**（本轮 3 项核验 + 1 处披露全部通过；前两轮已验项按采信，未重跑 `make check`）。

## 完成区

**测试结果**：证据脚本 **72/72 PASS（rc=0）**；`guard --self-test` **13/13**；相关门控全绿（`check-manifests-guard`/`check-knowledge-refs`/`check-contracts-dir`/`check-dirs`/`check-archive`/`check-spec-refs`/`check-milestones-fresh` + `check-spec-numbering`/`check-spec-changelog`/`check-no-residue`/`check-asm-prose`/`check-spec-purity`/`check-spec-codeblocks`/`check-asm-list`/`check-tasks`/`manifest-check`）。`make check` 整链在 `check-isa-coverage` 处 rc=2（本 worktree 无安装根、缺 `llvm-mc`；该脚本本任务未改）。
**修改文件**：新增 `manifests/dir-guard-roots.toml`（必需清单注册表）、`spec/.manifests.toml`（22 条含 sha256）、`.tao/.manifests.toml`、`.tao/knowledge/.manifests.toml`、`tools/infra/check_manifests_guard.py`；删除 `manifests/spec-readonly.lock.toml`、`tools/infra/check_spec_readonly.py`、`tools/infra/check_knowledge_dir.py`；改名 `.tao/knowledge/cfx-register-usage.md` → `docs/cfx-register-usage.md`；改 `spec/README.md`（仅第 76 行门控名，**用户授权**）、`Makefile`、`AGENTS.md`、`docs/Process-06`、`docs/Process-07`、`docs/README.md`、`.tao/adr/adr-0046`（仅第 26 行路径）、`tools/spec/check_numbering.py`、`tools/spec/check_spec_changelog.py`、`tools/infra/check_contracts_dir.py`（docstring）。
**验收结果**：① 三清单 + 注册表在位，`check-manifests-guard` rc=0；② 六类注入全可达 FAIL（self-test 13/13，含 `recursive` 真实子目录用例）；③ `spec/` 新增册 rc=1（「多出文件」）/删除 rc=1（「缺失文件」）/还原 rc=0，新增子目录 rc=1（「多出子目录」）；④ 改一册 sha256 rc=1（「sha256 不符」）→ `cp`+md5 还原 rc=0；⑤ 旧锁与两脚本已删，`grep -rn spec-readonly Makefile tools docs spec/` = 0；⑥ cfx 在 `docs/`、ADR-0046 引用已改，`grep knowledge/cfx-register-usage`（排除历史任务书/归档）= 0；⑦ 相关门控 rc=0。
**返工（第 1 轮 reviewer Needs Revision）**：**阻断已修**——注册表 `roots = ["spec", ".tao", ".tao/knowledge"]`，guard 改为**按注册表逐个校验**：删 `spec/` 清单 ⇒ rc=1 且 `ERROR: spec: 缺少清单 .manifests.toml`；删 `.tao/`、`.tao/knowledge/` 清单与删注册表各 rc=1 且点名（均 `cp`+md5 还原后 rc=0）；**游离清单**（目录未登记）⇒ rc=1（理由：只提示＝新增清单静默不生效，另一个 fail-open）。**待返工项已做**：`spec/README.md:76` **仅替换命令名**（`make check-spec-readonly` → `make check-manifests-guard`，其余文字不动），同笔重算 README 的 sha256（`ebe91b62…` → `3f2d57a7…`）；**21 册对照历史锁 `4aa0cb03` 全部 21/21 MATCH**（清单条目与改前逐条相同）。`git diff a263bd7b -- spec/README.md` 只有第 76 行 1 行、只差命令名。
**新发现/坑**：① fail-open 的真源是「取清单方式」而非「校验逻辑」——按注册表取，删清单/删注册表/清单未登记三条路都红；② 任务书记录里写具体 `.work/**` 路径会让 `check-knowledge-refs` 红（本返工把 reviewer 记录该处改为「运行期证据目录」措辞，判决不动）；③ `check-isa-coverage` 需安装根 ⇒ 本 worktree 只能逐门控跑；④ `recursive` 语义 = 顶层双向、子目录单向 ⊆；⑤ 门控遍历磁盘时剪掉 `.git`、`.work`、`.cache` 三个目录。
**遗留问题**：`.tao/contracts/README.md:27`、ADR-0032/0034/0035/0012/0055/0031/0030、`issues.yaml` 等历史/决策文本仍提旧锁文件名（不改 decision/历史）；`check-full` 成员表 = `tools/testcases/l3_run.py:DEFAULT_MEMBERS`（仅 L3），按 Process-07「一个检查只在一层」未把 L1 门控列进 L3，如需入 L3 须另裁。

