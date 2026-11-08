# INFRA-135t: `check-knowledge-refs` 按「不可复现」判定具体 `.work/**` 引用（ISS-352）

**模块**：infra
**项目里程碑**：M11
**依赖**：无
**状态**：待验收

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
4. 两台节点 `make check` 见「遗留问题」。

**新发现/坑**：旧判据把「本机存在」当作可复现的充分条件，与 `.work/` 被 gitignore 的事实冲突；本改动的关键是**去掉存在性这一前提**。
**遗留问题**：节点复跑结果待补（若 `make check` 红，需确认是否为本改动引入）。
