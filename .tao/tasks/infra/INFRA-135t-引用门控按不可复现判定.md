# INFRA-135t: `check-knowledge-refs` 按「不可复现」判定具体 `.work/**` 引用（ISS-352）

**模块**：infra
**项目里程碑**：M11
**依赖**：无
**状态**：已验证

## 背景与事实

`check-knowledge-refs` 的 (A) 面对「具体 `.work/**` 路径」只做**存在性检查**：本机有文件 ⇒ 放行。而 `.work/` 被 `.gitignore` 整体忽略、只在本机存在，于是：

- 主控机上绿、**新节点 / fresh clone 才红**
- 12 小时内因此复发 **3 次**（`INFRA-129t` 清理 23 处 → `GEM5-030t` 审阅记录 3 处 → `INFRA-133t` 审阅记录 1 处）
- 每次都是「已经合并、跑节点 L1 才发现」

用户裁定（2026-11-08，原话）：「A」——即具体 `.work/**` 引用**一律 FAIL**，不看本机是否存在。

## 改动

`tools/infra/check_knowledge_refs.py`：

1. 具体路径分支由「存在性检查」改为**直接记入不可复现列表**并判 FAIL；报错信息说明「`.work` 被 gitignore，本机存在不代表 fresh clone 可复现；请改为运行期措辞或升格到 `.tao/knowledge/refs/`」。
2. 统计口径由「具体路径 (校验)」改为「具体路径 (不可复现)」，并单独打印 `[ISS-352]` 段落列出位置。
3. docstring 同步新判据与用户裁定来源。

保留原有豁免与跳过规则（占位/通配、前缀截断、构建/源码树、删除语境）不变。

## 范围 / 非范围

**在范围内**：`tools/infra/check_knowledge_refs.py`、本任务书、`milestones.md`、`issues.yaml`（关闭 `ISS-352`）。

**不在范围**：其它门控、`AGENTS.md` 正文措辞、任何 `components/`、任务书内容改写（本任务不改既有文档引用）。

## 验收标准

1. 当前跟踪树：`python3 tools/infra/check_knowledge_refs.py` **rc=0**（现场具体引用 0 条，改动不误伤）。
2. **可达 FAIL（关键）**：注入一条指向**本机确实存在**的 `.work/**` 具体路径 ⇒ **rc=1** 且报「不可复现」（这条在旧判据下是**绿的**，正是复发的根源）；`cp`+md5 还原后回绿。
3. fresh 树（`git archive` 导出、无运行期目录）跑 `--root` ⇒ rc=0。
4. 两台节点 `make check` rc=0（节点上具体引用恒不存在，新判据必须不给它们新增红）。
5. 反例可复原：注入与还原的 md5 逐字一致；全程未用 git 还原。
6. 完成区 ≤30 行、无运行期路径；`ISS-352` 关闭（`resolved_by: INFRA-135t`）。

## 完成区

**测试结果**：门控改动完成。当前跟踪树 rc=0（具体引用 0 条，不误伤）；**可达 FAIL 已实测**——注入一条指向本机确实存在的 `.work/log/infra/<file>` 具体路径 ⇒ rc=1、报「1 具体 `.work/**` 引用不可复现」（旧判据下该情形为绿，正是复发根源）；`cp`+md5 还原后 md5 逐字一致并回绿。

**修改文件**：`tools/infra/check_knowledge_refs.py`、本任务书、`.tao/knowledge/milestones.md`、`.tao/knowledge/issues.yaml`（关闭 `ISS-352`）。

**验收结果**：
1. 当前树 rc=0；统计口径显示「具体路径 (不可复现): 0」。
2. 注入（存在文件的具体引用）⇒ rc=1，`[ISS-352]` 段列出位置；还原后 rc=0。
3. fresh 树（`git archive`，无运行期目录）`--root` ⇒ rc=0、悬空 0。
4. 两台节点 `make check` rc=0（`具体路径 (不可复现): 0`、`repository checks (L1): PASS`）。

**新发现/坑**：旧判据把「本机存在」当作可复现的充分条件，与 `.work/` 被 gitignore 的事实冲突；本改动的关键是**去掉存在性这一前提**。
**遗留问题**：① `checked` 计数器现为只写不读、(A) 面 `dangling` 分支不可达 ⇒ 行为无影响，登记 `ISS-353` 待清理；② 本任务无独立证据脚本，reviewer 以其自建注入替代（四类阻断面之外）。

## 审阅记录

### 第 1 轮 reviewer 验收（2026-11-08）

**判决：Accepted**

**重跑记录（均本人执行，workdir=仓库根，取 `cmd; echo $?` 真实退出码）**
- 基线 `python3 tools/infra/check_knowledge_refs.py` ⇒ rc=0，`具体路径 (不可复现): 0`、悬空 0。
- 注入指向**本机确实存在**的 `.work/log/infra/<file>`（任务书追加一行）⇒ **rc=1**，`[ISS-352]` 段列出 `…任务书.md:58`，`结果: FAIL (1 具体 .work/** 引用不可复现)`。
- 同一注入树跑 `git show 720eb774^:tools/infra/check_knowledge_refs.py`（导出至运行期临时目录）`--root .` ⇒ **rc=0**、`具体路径 (校验): 1` ⇒ 旧判据在该情形为绿、新判据红。
- 注入**本机不存在**路径 ⇒ rc=1（报错形态与存在路径一致）。
- `cp` 还原 + `md5sum -c` ⇒ `OK`（`8ed0f7de…`），回 rc=0；`git status --porcelain -uall` 对本人注入文件无残留。
- fresh 树：`git archive HEAD | tar -x` ⇒ `--root` rc=0、`具体路径 (不可复现): 0`、悬空 0。
- 四类豁免各注入 1 条 ⇒ 占位 36→37、前缀 1→2、构建 23→24、删除 1→2、具体 0，rc=0（豁免未变）。
- 反例非恒真：删掉 `concrete.append(...)` 行后跑同一存在性注入 ⇒ **rc=0**（`具体路径: 0`），证明断言确实依赖该行；`cp` 还原后 md5 `351c2118…` 一致、回 rc=1。
- 节点：`.work/log/infra/INFRA-135t/remote/<node>.log` 两台头部 `# rc: 0`、`具体路径 (不可复现): 0`、`repository checks (L1): PASS`；mtime 晚于提交且含新口径标签 ⇒ 确为新判据下结果。

**约束核验**
- 读码：具体路径分支已无 `exists()` 调用，直接 `concrete.append` + 首位 FAIL；`_classify` 四豁免、`found == 0` 空转判据、(B) 小节级与判据顺序均未动（diff 仅 4 处 hunk）。
- `ISS-352`：`status: closed`、`resolved_by: INFRA-135t…`；节点 `check_issues: resolved_by 约束 OK`。
- 完成区 13 行 ≤30、无宿主绝对路径；`milestones.md` 状态「待验收」与任务书一致。

**发现（不阻断，交 architect 收尾处理）**
1. 完成区「遗留问题：节点复跑结果待补」与事实不符（两台已 rc=0），请回填。
2. 无 `.work/evidence/<任务ID>/` 一键证据脚本；本轮以 reviewer 独立注入替代。
3. `checked` 变量现为只写不读、(A) 面 `dangling` 分支不可达（行为无影响，建议清理）。
4. 审查期间工作树被并发修改（`README.md`/`spec/*`/`milestones.md`/新增 SPEC-195t 任务书），非本人注入；本人涉及文件均已 md5 还原且不在 status 中。

**旧判据假绿路径是否已结构性封闭**：**是**——依据：同一注入树上旧脚本（`720eb774^`）rc=0 而新门控 rc=1，且新分支已不调用 `exists()`，本机存在性不再进入判定。

#### 收尾（architect，2026-11-08 08:59）

- 判决 Accepted：reviewer 用**同一条注入在两版脚本上对照**（旧 `720eb774^` rc=0 / 新 rc=1）证明假绿路径已结构性封闭；四类豁免与空转判据逐项注入确认未变；删 `concrete.append` 的反例使注入转绿，证明断言非恒真。
- F1：完成区「节点复跑结果待补」已按事实回填为 rc=0。
- F2：`checked` 只写不读、`dangling` 分支不可达 ⇒ 登记 `ISS-353`（P3，清理时勿改判据）。
- 两台节点在新判据下 L1 rc=0（`具体路径 (不可复现): 0`）。
