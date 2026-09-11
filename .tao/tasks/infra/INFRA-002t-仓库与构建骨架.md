# INFRA-002t: 仓库与构建骨架 + `.work/` 约定

**模块**：infra
**项目里程碑**：M1
**依赖**：无

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：现有仓库结构（`AGENTS.md`、`README.md`、`.tao/`、`spec/`、`manifests/`、`docs/`、`verif/`）
- 输出：补齐的目录骨架、`.gitignore`、`.work/` 目录约定
- 约束：不写实现代码；只建立骨架与忽略规则；`.work/` 全部内容不入库

## 背景（完整）

### 目标

建立 DADAO-v5 可复现构建所需的仓库骨架与 `.work/` 一次性工作区约定，使后续 manifest / 脚本 / Makefile / 容器有确定的落点。

### 设计理由

- 0628 `docs/repository-layout.md` 明确：仓库永不跟踪上游源码树或构建产物；源码 checkout 由 `components.lock.toml` + 有序补丁序列完全复现。
- ADR-0002 要求所有一次性数据放在 `.work/` 下。
- 工程规则（`docs/greenfield-charter.md`）：保持生成的产物在仓库历史之外。

### 关键概念 / 数据

- `.work/` 子目录职责（0628 `docs/repository-layout.md`）：
  - `.work/source/`：上游组件 checkout（`git clone` + 补丁）。
  - `.work/build/`：树外构建目录。
  - `.work/install/`：宿主工具与产物。
  - `.work/sysroot/`：目标 sysroot。
  - `.work/logs/`：构建与测试日志。
- 0628 顶层骨架：`manifests/`（不可变输入）、`components/`（补丁序列 + 组件文档）、`contracts/`、`tests/`、`scripts/`、`containers/`、`.work/`。
- DADAO-v5 现状：已有 `.gitignore`（含 `.work/`）、`manifests/`、`spec/`、`docs/`、`verif/`、`.tao/`；`components/`、`scripts/`、`containers/` 尚未建立。

### 上游引用

- DADAO-0628 `docs/repository-layout.md`（完整转述见上）。
- DADAO-0628 `.gitignore`：忽略 `.work/`、`__pycache__/`、`*.py[cod]`、`*.swp`、`*.tmp`、`*.log`、`.DS_Store`、`.idea/`、`.vscode/`，以及 lit / gem5 运行产物（`tests/lit/**/Output/`、`m5out/`）。
- DADAO-0628 `docs/adr/0002-build-orchestration.md`：一次性数据集中在 `.work/`。
- DADAO-0628 `docs/greenfield-charter.md` 工程规则 4：生成的产物在仓库历史之外。

## 交付物

- `.gitignore`：在现有基础上补齐 0628 的忽略项（`.work/` 已有，补 `*.tmp`、`*.log` 等，按 v5 目录实际调整；lit/gem5 运行产物待对应目录建立后再登记，本次不加）。
- `.work/` 目录约定：在仓库文档（如 `docs/repository-layout.md`，若新建）或 `README.md` 中记录 `source/` / `build/` / `install/` / `sysroot/` / `logs/` 职责；`.work/` 本身不建目录、不入库。
- `components/`：目录骨架（含 `.gitkeep`），用于放置补丁序列与组件文档。
- `scripts/`：目录骨架（含 `.gitkeep`），用于放置 Python 工具。
- `containers/`：目录骨架（含 `.gitkeep`），用于放置开发容器。
- `manifests/`：已存在，确认与骨架一致（无需新建）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- 无 ISA 相关差异（基础设施，与 ISA 版本无关）。
- 目录差异：v5 用 `.tao/` 承载 agent 中间文件（0628 用 `code-agent/`）；v5 用 `verif/` 承载验证工具（0628 用 `tools/`）；v5 用 `spec/`（0628 用 wiki/contracts）。骨架任务不复制 0628 的 `contracts/`、`code-agent/` 目录。
- `.gitignore` 已存在，本任务为补齐/对齐，而非从零创建。

## 已知坑 / 结论

- 仓库永不跟踪上游源码树与构建产物；`.work/` 必须整体忽略。
- 空目录需 `.gitkeep` 才能在 git 中保留（`components/`、`scripts/`、`containers/`）。
- 0628 的 `m5out/`、`tests/lit/**/Output/` 等运行产物忽略项，v5 在对应目录建立后按需保留。

## 参考

- DADAO-0628：`.work/DADAO-0628/docs/repository-layout.md`
- DADAO-0628：`.work/DADAO-0628/.gitignore`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0002-build-orchestration.md`
- DADAO-0628：`.work/DADAO-0628/docs/greenfield-charter.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `.gitignore` 覆盖 `.work/`、Python 缓存、编辑器临时文件与临时产物（`*.tmp`、`*.log`）
2. `components/`、`scripts/`、`containers/` 骨架存在且可被 git 保留
3. `.work/` 子目录约定有明确文档记录
4. `git status` 在干净状态下不显示 `.work/` 内任何文件

## 完成区

**状态**：已验证
**Commit**：无（未提交；提交需用户确认，由主会话处理）
**测试结果**：通过 4/4（对应「验收标准」1–4）；失败原因：无
**修改文件**：
- `.gitignore`（修改：Python 块对齐 0628 为 `*.py[cod]`；新增 `*.tmp`/`*.log`；lit/gem5 运行产物按用户决策不加）
- `components/.gitkeep`（新建）
- `scripts/.gitkeep`（新建）
- `containers/.gitkeep`（新建）
- `docs/repository-layout.md`（新建：仓库布局 + `.work/` 子目录约定）

**验收结果**：

```
$ git status --porcelain
 M .gitignore
?? components/
?? containers/
?? docs/
?? scripts/
（不显示 .work/ 内任何文件）

$ git status --porcelain --ignored | grep '\.work/'
!! .work/

$ git check-ignore -v .work/source/foo .work/logs/x.log a/__pycache__/b.pyc c.pyc d.pyo f.tmp g.log tests/lit/t/Output/x tests/lit/t/.lit_test_times.txt m5out/x
.gitignore:2:.work/	.work/source/foo
.gitignore:2:.work/	.work/logs/x.log
.gitignore:5:__pycache__/	a/__pycache__/b.pyc
.gitignore:6:*.py[cod]	c.pyc
.gitignore:6:*.py[cod]	d.pyo
.gitignore:17:*.tmp	f.tmp
.gitignore:18:*.log	g.log
.gitignore:25:tests/lit/**/Output/	tests/lit/t/Output/x
.gitignore:26:tests/lit/**/.lit_test_times.txt	tests/lit/t/.lit_test_times.txt
.gitignore:29:m5out/	m5out/x

$ git check-ignore -v components/.gitkeep scripts/.gitkeep containers/.gitkeep
（无输出，exit=1 → 未被忽略，可跟踪）

$ git add -n components/.gitkeep scripts/.gitkeep containers/.gitkeep docs/repository-layout.md .gitignore
add '.gitignore'
add 'components/.gitkeep'
add 'containers/.gitkeep'
add 'docs/repository-layout.md'
add 'scripts/.gitkeep'

$ grep -nE '\.work/(source|build|install|sysroot|logs)/' docs/repository-layout.md
26:- `.work/source/`：上游组件 checkout（`git clone` + 有序补丁）。
27:- `.work/build/`：树外构建目录。
28:- `.work/install/`：宿主工具与产物。
29:- `.work/sysroot/`：目标 sysroot。
30:- `.work/logs/`：构建与测试日志。
```

完整命令日志：`.tao/logs/INFRA-002t-*.log`（`git-status` / `git-status-ignored` / `check-ignore` / `git-add-dryrun` / `doc-convention`）。

**验收标准逐条自审**：
1. `.gitignore` 覆盖 `.work/`、Python 缓存（`__pycache__/`、`*.py[cod]`）、编辑器临时文件（`*.swp`/`*.swo`/`*~`/`.vscode/`/`.idea/`）与运行产物（`*.tmp`、`*.log`、lit、`m5out/`）——✅ 通过（`check-ignore` 逐项命中）
2. `components/`、`scripts/`、`containers/` 骨架存在且可被 git 保留——✅ 通过（各含 `.gitkeep`，`check-ignore` exit=1，`git add -n` 可加入）
3. `.work/` 子目录约定有明确文档记录——✅ 通过（`docs/repository-layout.md` 记录 `source/`/`build/`/`install/`/`sysroot/`/`logs/` 职责）
4. `git status` 在干净状态下不显示 `.work/` 内任何文件——✅ 通过（`git status --porcelain` 不显示；`--ignored` 显示 `!! .work/`）

**新发现/坑**：
- 任务「现状」称 `docs/` 已存在，实际不存在：`docs/` 历史上只含 `docs/phases/*.md`，已在 commit `390729d`（去阶段化）全部删除。本任务按交付物「如 `docs/repository-layout.md`，若新建」新建 `docs/` 与 `docs/repository-layout.md` 记录 `.work/` 约定。若后续约定不欢迎 `docs/` 目录，可改记录到 `README.md`。
- 0628 `.gitignore` 的 `*.py[cod]` 是 `*.pyc`/`*.pyo` 的超集（多覆盖 `.pyd`），已据此对齐。
- `.work/` 目录当前已存在（含 `.work/DADAO-0628`），但整体被忽略；本任务**未**在 `.work/` 下新建任何子目录（遵守「`.work/` 本身不建目录」）。
- 未改动 `.tao/README.md` 的项目结构表（其中 `components/`/`scripts/` 原标「按需创建」），保持最小修改；如需同步可另开任务。
- lit（`tests/lit/**/Output/`、`.lit_test_times.txt`）与 gem5（`m5out/`）两条为**前瞻性预留**：v5 当前尚无 `tests/`、`m5out/` 目录，按任务书「按需保留」先登记，待对应目录建立后自然生效（`.tao/README.md` 已将 `tests/` 列为后续交付物）。
- `*.log` 为全局忽略，未来若要提交 `.log` 测试 fixture 需用 `!` 反选（当前无已跟踪 `.log`，无回归）。

**遗留问题**：无

## 审阅记录

### 第 1 轮 engineer 自审（general subagent）

由 `general` subagent 独立重跑关键命令核对，判决 **ACCEPT**。findings 及处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `.gitignore` 四类覆盖、骨架可保留、文档、约束、防造假均通过 | ✅已修 | 无需改动（确认通过） | 独立重跑 `git check-ignore`/`git add -n`/`git status` 全通过 |
| [建议] lit/gem5 条目为前瞻性预留，完成区未点明 | ✅已修 | 完成区「新发现/坑」补一条说明其为前瞻性预留 | 见完成区新增条目 |
| [疑问] 全局 `*.log` 副作用 | ❌不修 | 无 | 与 0628 对齐；`git ls-files` 无已跟踪 `.log`，无回归；已在「新发现」提示 |
| [建议·低] `*.pyc`+`*.pyo` → `*.py[cod]` 属行为变更 | ❌不修 | 无 | 超集（新增 `.pyd`），符合任务「补齐 0628 忽略项」，`check-ignore` 实测 `e.pyd` 命中 |
| [疑问·低] 完成区 `git status` 输出未含任务文件自身改动行 | ❌不修 | 无 | 属输出采集时序（先采集、后写入完成区），非造假；当前重跑 `git status --porcelain` 含 ` M .tao/tasks/...INFRA-002t...md` |

无未修阻塞项；状态与判决对账一致，置「待验收」。

### 第 2 轮 reviewer 独立验收

**审查者**：reviewer subagent
**审查时间**：2026-09-11
**审查方式**：完全独立重跑验收命令，不采信 engineer 完成区输出。

#### 重跑记录

**验收标准 1：`.gitignore` 覆盖 `.work/`、Python 缓存、编辑器临时文件与运行产物**

```bash
$ git check-ignore -v .work/source/foo .work/logs/x.log a/__pycache__/b.pyc c.pyc d.pyo f.tmp g.log tests/lit/t/Output/x tests/lit/t/.lit_test_times.txt m5out/x
.gitignore:2:.work/	.work/source/foo
.gitignore:2:.work/	.work/logs/x.log
.gitignore:5:__pycache__/	a/__pycache__/b.pyc
.gitignore:6:*.py[cod]	c.pyc
.gitignore:6:*.py[cod]	d.pyo
.gitignore:17:*.tmp	f.tmp
.gitignore:18:*.log	g.log
.gitignore:25:tests/lit/**/Output/	tests/lit/t/Output/x
.gitignore:26:tests/lit/**/.lit_test_times.txt	tests/lit/t/.lit_test_times.txt
.gitignore:29:m5out/	m5out/x
EXIT_CODE=0
```

补充验证 `.pyd` 与编辑器临时文件：

```bash
$ git check-ignore -v e.pyd e.swp e.swo 'file~'
.gitignore:6:*.py[cod]	e.pyd
.gitignore:10:*.swp	e.swp
.gitignore:11:*.swo	e.swo
.gitignore:12:*~	file~
EXIT_CODE=0
```

**结论**：✅ 通过。`.work/`、Python（`__pycache__/`、`*.py[cod]` 含 `.pyc`/`.pyo`/`.pyd`、`*.egg-info/`）、编辑器（`*.swp`/`*.swo`/`*~`/`.vscode/`/`.idea/`）、临时文件（`*.tmp`/`*.log`）、系统文件（`.DS_Store`/`Thumbs.db`）、lit 运行产物、gem5 运行产物全部命中。行号与 `.gitignore` 实际内容一致。

**验收标准 2：`components/`、`scripts/`、`containers/` 骨架存在且可被 git 保留**

```bash
$ ls -la /mnt/tao/DADAO-v5/components/ /mnt/tao/DADAO-v5/scripts/ /mnt/tao/DADAO-v5/containers/
（各目录均存在，含 .gitkeep，大小 0 字节）

$ git check-ignore -v components/.gitkeep scripts/.gitkeep containers/.gitkeep
EXIT_CODE=1
（无输出 → 未被忽略）

$ git add -n components/.gitkeep scripts/.gitkeep containers/.gitkeep docs/repository-layout.md .gitignore
add '.gitignore'
add 'components/.gitkeep'
add 'containers/.gitkeep'
add 'docs/repository-layout.md'
add 'scripts/.gitkeep'
EXIT_CODE=0
```

**结论**：✅ 通过。三个骨架目录均存在且含 `.gitkeep`，`check-ignore` exit=1（未忽略），`git add -n` 可加入暂存。

**验收标准 3：`.work/` 子目录约定有明确文档记录**

```bash
$ grep -nE '\.work/(source|build|install|sysroot|logs)/' docs/repository-layout.md
26:- `.work/source/`：上游组件 checkout（`git clone` + 有序补丁）。
27:- `.work/build/`：树外构建目录。
28:- `.work/install/`：宿主工具与产物。
29:- `.work/sysroot/`：目标 sysroot。
30:- `.work/logs/`：构建与测试日志。
```

**结论**：✅ 通过。`docs/repository-layout.md` 完整记录了五个 `.work/` 子目录的职责与不入库约定（第 22–33 行）。

**验收标准 4：`git status` 在干净状态下不显示 `.work/` 内任何文件**

```bash
$ git status --porcelain
 M .gitignore
 M ".tao/tasks/infra/INFRA-002t-仓库与构建骨架.md"
?? components/
?? containers/
?? docs/
?? scripts/
EXIT_CODE=0
（不显示 .work/ 内任何文件）

$ git status --porcelain --ignored | grep '\.work/'
!! .work/
EXIT_CODE=0
```

**结论**：✅ 通过。`git status --porcelain` 不含 `.work/` 内文件；`--ignored` 显示 `!! .work/` 确认整体被忽略。

#### 约束核验

| 约束 | 状态 | 证据 |
|------|------|------|
| 不写实现代码 | ✅ | 仅新建 `.gitkeep`（空文件）和 `docs/repository-layout.md`（文档），修改 `.gitignore`（配置）；无 `.py`/`.c`/`.sv` 等实现代码 |
| 只建立骨架与忽略规则 | ✅ | `components/`/`scripts/`/`containers/` 仅含 `.gitkeep`；`.gitignore` 为忽略规则；`docs/repository-layout.md` 为文档 |
| `.work/` 全部内容不入库 | ✅ | `git check-ignore -v .work/source/foo .work/logs/x.log` 全部命中 `.gitignore:2:.work/`；`git status` 不显示 `.work/` 文件 |
| 不新建 `.work/` 子目录 | ✅ | 仅在文档中记录子目录职责，未在 `.work/` 下创建任何子目录 |

#### 修改文件清单核对

Engineer 声称的修改文件：

| 文件 | 声称 | 实际 | 一致？ |
|------|------|------|--------|
| `.gitignore`（修改） | ✅ | `git status` 显示 ` M .gitignore` | ✅ |
| `components/.gitkeep`（新建） | ✅ | `ls` 确认存在，`git status` 显示 `?? components/` | ✅ |
| `scripts/.gitkeep`（新建） | ✅ | `ls` 确认存在，`git status` 显示 `?? scripts/` | ✅ |
| `containers/.gitkeep`（新建） | ✅ | `ls` 确认存在，`git status` 显示 `?? containers/` | ✅ |
| `docs/repository-layout.md`（新建） | ✅ | `ls` 确认存在，内容含 33 行文档，`.work/` 五子目录职责齐全 | ✅ |

**额外发现**：`git status` 还显示任务文件自身被修改（` M ".tao/tasks/infra/INFRA-002t-仓库与构建骨架.md"`），这是 engineer 写入完成区的正常行为，不计入交付物偏差。

#### Engineer 自审结论差异

| 项目 | Engineer 自审 | Reviewer 独立验证 | 差异 |
|------|--------------|-------------------|------|
| 验收标准 1 | ✅ 通过 | ✅ 通过 | 无 |
| 验收标准 2 | ✅ 通过 | ✅ 通过 | 无 |
| 验收标准 3 | ✅ 通过 | ✅ 通过 | 无 |
| 验收标准 4 | ✅ 通过 | ✅ 通过 | 无 |
| 行号准确性 | 声称 line 2/5/6/17/18/25/26/29 | 独立验证一致 | 无 |
| `.pyd` 覆盖 | 声称 `*.py[cod]` 含 `.pyd` | `check-ignore` 验证 `e.pyd` 命中 line 6 | 无 |
| `*.log` 副作用 | 提示全局忽略可能影响 fixture | `git ls-files --cached -- '*.log'` 无已跟踪 `.log`，当前无回归 | 无 |

#### 判决

**Accepted**

四条验收标准全部通过，约束全部守住，修改文件清单与仓库实际状态一致。无阻塞缺陷。

### 第 3 轮：用户决策修订（lit/gem5 运行产物不加入）

**决策者**：用户（2026-09-11）
**内容**：`.gitignore` 不需要增加 lit 运行产物（`tests/lit/**/Output/`、`tests/lit/**/.lit_test_times.txt`）与 gem5 运行产物（`m5out/`）——v5 当前无对应目录，属前瞻性预留。
**处置**：移除 `.gitignore` 第 24–29 行（lit/gem5 两节）；同步更新本任务「交付物」「验收标准 1」与完成区「修改文件」。

**复验（真实输出）**：

```bash
$ git check-ignore -v .work/source/foo .work/logs/x.log a/__pycache__/b.pyc c.pyc d.pyo f.tmp g.log .DS_Store
.gitignore:2:.work/	.work/source/foo
.gitignore:2:.work/	.work/logs/x.log
.gitignore:5:__pycache__/	a/__pycache__/b.pyc
.gitignore:6:*.py[cod]	c.pyc
.gitignore:6:*.py[cod]	d.pyo
.gitignore:17:*.tmp	f.tmp
.gitignore:18:*.log	g.log
.gitignore:21:.DS_Store	.DS_Store
exit=0

$ git check-ignore -v tests/lit/t/Output/x tests/lit/t/.lit_test_times.txt m5out/x
exit=1  （无输出 → 均未被忽略，符合用户决策）
```

**结论**：修订完成。剩余忽略项（`.work/`、Python 缓存、编辑器临时文件、`*.tmp`/`*.log`、系统文件）全部命中；lit/gem5 运行产物不再忽略。验收标准 1（修订后）通过。
