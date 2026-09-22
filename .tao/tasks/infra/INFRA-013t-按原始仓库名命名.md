# INFRA-013t: 按原始仓库名命名

**模块**：infra
**项目里程碑**：M1
**依赖**：`INFRA-003t`、`INFRA-004t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`manifests/components.lock.toml`（`INFRA-003t` 产出）、`manifests/references.lock.toml`（`INFRA-003t` 产出）、`Makefile`（`INFRA-006t` 产出）、`.tao/tasks/llvm/*.md`（LLVM 模块任务书）、`.tao/tasks/infra/INFRA-006t-Makefile编排.md`、`.tao/tasks/integ/INTEG-003t-跨模块接口对齐.md`
- 输出：更新后的 manifest 文件、Makefile、迁移后的缓存/工作树、同步后的文档路径
- 约束：标识符与缓存/工作树目录必须按「原始仓库名」（含大小写）命名；`fetch.py`/`fetch_refs.py` 代码不改（`.cache/<name>.git`、`.cache/refs/<id>.git` 会自然得到仓库名）；ADR-0002 L18 的 `<name>`/`<id>` 占位符本就指原始仓库名，不冲突、不修改、不新增 ADR

## 背景（完整）

### 目标

将 v5 的组件标识符与参考仓库标识符统一为原始仓库名，消除简称与全名之间的不一致。当前问题出在 manifest 的值（用了 v5 内部简称），不是工具代码。

### 设计理由

- **一致性**：`ADR-0002` L18 明确规定 `.cache/<name>.git` 和 `.cache/refs/<id>.git` 按原始仓库名命名。当前 manifest 中 `name = "llvm"` 会导致缓存目录为 `.cache/llvm.git`，而实际仓库名为 `llvm-project`；同理，参考仓库 `id = "dadao-0628"` 与原始仓库名 `DADAO-0628` 大小写不一致。
- **可预测性**：用户或脚本看到 `llvm-project` 仓库时，自然预期缓存目录为 `.cache/llvm-project.git`，而非 `.cache/llvm.git`。
- **不改代码**：`fetch.py`/`fetch_refs.py` 的逻辑是读取 manifest 中的 `name`/`id` 作为缓存目录名，改 manifest 值即可让缓存目录自然变为正确名称，无需修改脚本代码。

### 关键概念 / 数据

- `components.lock.toml`（`INFRA-003t`）：组件 `name` 字段用于 `.cache/<name>.git` 目录名和 `$(call component-enabled,<name>)` Makefile 宏。
- `references.lock.toml`（`INFRA-003t`）：参考仓库 `id` 字段用于 `.cache/refs/<id>.git` 目录名。
- `Makefile`（`INFRA-006t`）：`LLVM_SRC` 默认值和 `component-enabled` 调用均引用组件名。
- `fetch.py`（`INFRA-004t`）：`mirror_dir = cache_root / f"{component['name']}.git"`，按 manifest 的 `name` 值生成缓存路径。
- `fetch_refs.py`（`INFRA-004t`）：`mirror_dir = cache_root / "refs" / f"{ref['id']}.git"`，按 manifest 的 `id` 值生成缓存路径。

### 本次变更范围

| 决策 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| 组件 `name` | `llvm` | `llvm-project` | 与 GitHub 仓库名 `llvm/llvm-project` 一致 |
| `patch_series` 路径 | `components/llvm/patches/series` | `components/llvm-project/patches/series` | 按 `<name>` 索引 |
| 参考仓库 `id` | `dadao-0628` | `DADAO-0628` | 与原始仓库名大小写一致 |
| 参考仓库 `id` | `dadao` | `DADAO` | 与原始仓库名大小写一致 |
| `Makefile` `LLVM_SRC` | `.work/source/llvm/llvm` | `.work/source/llvm-project/llvm` | 按 `<name>` 索引 |
| `Makefile` `component-enabled` | `llvm` | `llvm-project` | 按 `<name>` 索引 |

**不变项**：qemu/gem5 的 `name`（本就等于仓库名）、所有 `repository`/`commit`/`enabled`/`role`/`[[component.source]]`、所有 `path`/`head`/`repository`/`reuse`、`fetch.py`/`fetch_refs.py` 代码。

## 交付物

### 1. `manifests/components.lock.toml`

- `name = "llvm"` → `name = "llvm-project"`
- `patch_series = "components/llvm/patches/series"` → `patch_series = "components/llvm-project/patches/series"`
- `repository`/`commit`/`enabled`/`role`/`[[component.source]]` 不变
- qemu/gem5 条目完全不变

### 2. `manifests/references.lock.toml`

- `id = "dadao-0628"` → `id = "DADAO-0628"`
- `id = "dadao"` → `id = "DADAO"`
- `path`/`head`/`repository`/`reuse` 不变

### 3. `Makefile`

- `LLVM_SRC ?= .work/source/llvm/llvm` → `LLVM_SRC ?= .work/source/llvm-project/llvm`（第 14 行）
- `$(call component-enabled,llvm)` → `$(call component-enabled,llvm-project)`（第 75 行）
- 报错文案 `'llvm'` → `'llvm-project'`（第 76 行）
- `QEMU_SRC`/`LLVM_BUILD`/其他 component-enabled 调用不变

### 4. 本地缓存与工作树迁移

以下目录均在 `.gitignore` 中，但迁移步骤必须执行并验证：

```bash
# 组件缓存
mv .cache/llvm.git .cache/llvm-project.git

# 参考仓库缓存
mv .cache/refs/dadao-0628.git .cache/refs/DADAO-0628.git
mv .cache/refs/dadao.git .cache/refs/DADAO.git
```

**工作树 origin 修正**：`.work/DADAO-0628` 和 `.work/DADAO` 的 `origin` 当前指向旧路径（实测 `origin = /mnt/tao/DADAO-v5/.cache/refs/dadao-0628.git`、`.../dadao.git`）。迁移缓存后需修正：

```bash
# 修正 .work/DADAO-0628 的 origin
git -C .work/DADAO-0628 remote set-url origin /mnt/tao/DADAO-v5/.cache/refs/DADAO-0628.git

# 修正 .work/DADAO 的 origin
git -C .work/DADAO remote set-url origin /mnt/tao/DADAO-v5/.cache/refs/DADAO.git
```

**验证**：运行 `make fetch-refs` 确认工作树可正常更新（或确认 `git -C .work/DADAO-0628 remote -v` 显示新路径）。

**注意**：`.work/source/llvm` 目前不存在（llvm 仍 disabled，未 fetch 过），无需迁移。

### 5. 文档/任务书路径同步

需将 v5 文档中的 `components/llvm/patches` → `components/llvm-project/patches`、`.work/source/llvm` → `.work/source/llvm-project` 同步更新（共 15 个文件）。逐文件清单如下：

#### 需要修改的文件

| 文件 | 改动内容 | 理由 |
|------|---------|------|
| `.tao/tasks/llvm/LLVM-001k-模块启动.md` | 第 20 行 `components/llvm/patches/series` → `components/llvm-project/patches/series`；第 24 行 `.work/source/llvm` → `.work/source/llvm-project`；第 33–38 行任务表中 `components/llvm/patches/` → `components/llvm-project/patches/`（共 8 处）；第 54 行 `.work/DADAO-0628/components/llvm/patches/series` **不改**（0628 自身路径） | v5 任务描述，引用 v5 组件路径 |
| `.tao/tasks/llvm/LLVM-002t-LLVM组件基线.md` | 第 14 行 `llvm` 条目描述（无需改，指 manifest 的 `name` 值，改 manifest 即可）；第 18 行 `components/llvm/patches/series` → `components/llvm-project/patches/series`；第 41 行 `.work/source/llvm/llvm` → `.work/source/llvm-project/llvm`；第 54 行 `components/llvm/patches/` → `components/llvm-project/patches/`；第 60 行 `.work/source/llvm/llvm` → `.work/source/llvm-project/llvm`；第 61 行 `components/llvm/patches/*` → `components/llvm-project/patches/*`；第 68 行 `components/<name>/patches/series`（通用描述，不改）；第 70 行 `LLVM_SRC=.work/source/llvm/llvm` → `.work/source/llvm-project/llvm`（2 处）；第 90 行 `.work/source/llvm/llvm` → `.work/source/llvm-project/llvm`；第 91 行 `components/llvm/patches/series` → `components/llvm-project/patches/series`；第 106 行 `components/llvm/patches/series` → `components/llvm-project/patches/series` | v5 任务描述 |
| `.tao/tasks/llvm/LLVM-003t-Triple注册.md` | 第 14 行 `.work/source/llvm` → `.work/source/llvm-project`、`components/llvm/patches/series` → `components/llvm-project/patches/series`；第 16–18 行 `components/llvm/patches/` → `components/llvm-project/patches/`（3 处）；第 21 行 `.work/source/llvm` → `.work/source/llvm-project`；第 57 行 `components/llvm/patches/` **不改**（0628 自身路径）；第 62–64 行 `components/llvm/patches/` → `components/llvm-project/patches/`（3 处）；第 71 行 `.work/source/llvm/llvm` → `.work/source/llvm-project/llvm`；第 87 行 `.work/DADAO-0628/components/llvm/patches/series` **不改**（0628 自身路径）；第 95 行 `components/llvm/patches/series` → `components/llvm-project/patches/series` | v5 任务描述 |
| `.tao/tasks/llvm/LLVM-004t-Register-TableGen.md` | 第 15 行 `components/llvm/patches/` → `components/llvm-project/patches/`（2 处）；第 48 行 `components/llvm/patches/` **不改**（0628 自身路径）；第 53–54 行 `components/llvm/patches/` → `components/llvm-project/patches/`（2 处）；第 71 行 `.work/source/llvm` → `.work/source/llvm-project`；第 77 行 `.work/DADAO-0628/components/llvm/patches/series` **不改**（0628 自身路径）；第 84 行 `components/llvm/patches/` → `components/llvm-project/patches/` | v5 任务描述 |
| `.tao/tasks/llvm/LLVM-005t-指令格式-TableGen.md` | 第 15 行 `components/llvm/patches/` → `components/llvm-project/patches/`（2 处）；第 65 行 `components/llvm/patches/` → `components/llvm-project/patches/`；第 66 行 `components/llvm/patches/series` → `components/llvm-project/patches/series`；第 98 行 `components/llvm/patches/` → `components/llvm-project/patches/`；第 60 行 `components/llvm/patches/` **不改**（0628 自身路径）；第 91 行 `.work/DADAO-0628/components/llvm/patches/series` **不改**（0628 自身路径） | v5 任务描述 |
| `.tao/tasks/llvm/LLVM-006t-AsmParser与CodeEmitter.md` | 第 15 行 `components/llvm/patches/` → `components/llvm-project/patches/`；第 49 行 `components/llvm/patches/` → `components/llvm-project/patches/`；第 50 行 `components/llvm/patches/series` → `components/llvm-project/patches/series`；第 81 行 `components/llvm/patches/` → `components/llvm-project/patches/`；第 44 行 `components/llvm/patches/` **不改**（0628 自身路径）；第 75 行 `.work/DADAO-0628/components/llvm/patches/series` **不改**（0628 自身路径） | v5 任务描述 |
| `.tao/tasks/llvm/LLVM-007t-CodeEmitter修复与lit.md` | 第 15 行 `components/llvm/patches/` → `components/llvm-project/patches/`；第 59 行 `components/llvm/patches/` → `components/llvm-project/patches/`；第 61 行 `components/llvm/patches/series` → `components/llvm-project/patches/series`；第 54 行 `components/llvm/patches/` **不改**（0628 自身路径） | v5 任务描述 |
| `.tao/tasks/llvm/LLVM-008t-反汇编器.md` | 第 15 行 `components/llvm/patches/` → `components/llvm-project/patches/`；第 42 行 `components/llvm/patches/` **不改**（0628 自身路径）；第 47–48 行 `components/llvm/patches/` → `components/llvm-project/patches/`（2 处）；第 72 行 `.work/DADAO-0628/components/llvm/patches/series` **不改**（0628 自身路径）；第 78 行 `components/llvm/patches/` → `components/llvm-project/patches/` | v5 任务描述 |
| `.tao/tasks/llvm/LLVM-011t-RA指令MC支持.md` | 第 15 行 `components/llvm/patches/series` → `components/llvm-project/patches/series`；第 45 行 `components/llvm/patches/` → `components/llvm-project/patches/`；第 47 行 `components/llvm/patches/series` → `components/llvm-project/patches/series` | v5 任务描述 |
| `.tao/tasks/llvm/LLVM-009t-lit字节CHECK.md` | 第 57 行 `components/llvm/patches/` → `components/llvm-project/patches/` | v5 任务描述 |
| `.tao/tasks/llvm/LLVM-014m-LLVM-MC里程碑.md` | 第 14–20 行 `components/llvm/patches/` → `components/llvm-project/patches/`（补丁清单 7 行，全为 v5 路径） | v5 里程碑清单 |
| `.tao/tasks/infra/INFRA-006t-Makefile编排.md` | 第 265 行 `.work/source/llvm/llvm` → `.work/source/llvm-project/llvm`；第 266 行 `$(call component-enabled,llvm)` → `$(call component-enabled,llvm-project)`；第 511 行 `LLVM_SRC = .work/source/llvm/llvm` → `LLVM_SRC = .work/source/llvm-project/llvm` | v5 路径/标识符说明（指导性内容） |
| `.tao/tasks/integ/INTEG-003t-跨模块接口对齐.md` | 第 18 行 `components/llvm/patches/*` → `components/llvm-project/patches/*` | v5 任务描述 |
| `.tao/tasks/infra/INFRA-009t-组件锁多源字段.md` | 第 70 行 `git -C .cache/llvm.git` → `git -C .cache/llvm-project.git` | **用户裁定 2026-09-17 追加**：示例标识符同步 |
| `.tao/tasks/infra/INFRA-008t-补v5自身ADR.md` | 第 399 行第二个 `INFRA-013m` 补加 `（现 INFRA-014m）` 标注 | **用户裁定 2026-09-17 追加**：里程碑顺延标注 |

#### 不修改的文件及理由

| 文件 | 理由 |
|------|------|
| `.tao/tasks/infra/INFRA-004t-组件获取与打补丁工具.md` | 含 `.cache/refs/dadao-0628.git` 等**历史验证输出**（记录当时事实，不改写） |
| `.tao/logs/**` | 日志文件，记录历史事实 |
| `.work/DADAO-0628/**` | 参考仓库自身内容，不改 |
| `.tao/knowledge/adr-0005-component-lock-multi-source.md` | 含 `.cache/llvm.git` 引用，但为历史决策记录（ADR Accepted 后不回溯改写）；且 ADR 中 `<name>` 占位符本就指原始仓库名 |
| `.tao/knowledge/changelog.md` | 含 `.cache/llvm.git` 引用（历史行，记录当时事实） |

> **已纳入**（用户裁决 2026-09-17）：LLVM-005t/006t/007t/009t/013m 的 v5 路径引用已纳入「需要修改的文件」清单。

### 6. `.tao/knowledge/` 路径同步

经 grep 核对：
- `.tao/knowledge/adr-0005-component-lock-multi-source.md` 第 11 行含 `.cache/llvm.git`，第 22 行含 `name = "llvm"`——为历史 ADR 记录，**不改**（ADR Accepted 后不回溯改写，且 `<name>` 占位符本就指原始仓库名）。
- `.tao/knowledge/changelog.md` 含 `.cache/llvm.git`（第 48 行历史行）——**不改**（记录当时事实）。

**已知坑/结论写入**：标识符 = 原始仓库名。`ADR-0002` L18 的 `<name>`/`<id>` 占位符指的就是原始仓库名（含大小写），manifest 的值必须与之一致。组件 `name` 取 GitHub 仓库名（如 `llvm-project`），参考仓库 `id` 取原始仓库名（如 `DADAO-0628`）。

### 7. `changelog.md`

新增一行记录本次规划（新任务 `INFRA-013t` + 里程碑 `013m`→`014m` 顺延）。

## 与 DADAO-0628 的差异

- 0628 的 `components.lock.toml` 中 `name = "llvm"`（v5 改为 `name = "llvm-project"`）。
- 0628 的 `references.toml` 中 `id = "dadao-0628"`、`id = "dadao"`（v5 改为大写 `DADAO-0628`、`DADAO`）。
- 0628 的 Makefile 中 `LLVM_SRC ?= .work/llvm/llvm`（v5 已改为 `.work/source/llvm-project/llvm`）。
- 无 ISA 相关差异（基础设施，与 ISA 版本无关）。

## 已知坑 / 结论

- **标识符 = 原始仓库名**：`ADR-0002` L18 的 `<name>`/`<id>` 占位符指的就是原始仓库名（含大小写），manifest 的值必须与之一致。这是本次任务的核心原则。
- **`fetch.py`/`fetch_refs.py` 代码不改**：`.cache/<name>.git` 和 `.cache/refs/<id>.git` 的目录名由 manifest 的 `name`/`id` 值决定，改 manifest 即可。
- **`components/<name>/patches/` 目录**：manifest 的 `patch_series` 字段值随 `name` 变化，但实际目录尚不存在（llvm 仍 disabled），迁移时只需改 manifest 值，无需移动目录。
- **`.work/DADAO-0628` 和 `.work/DADAO` 的 origin 修正**：缓存目录重命名后，工作树的 origin URL 需同步更新，否则 `git fetch` 会失败。
- **历史记录不改写**：changelog 历史行、INFRA-004t/INFRA-009t 的历史验证输出、ADR-0005 中的 `.cache/llvm.git` 引用均保留原文，不改写历史事实。

## 参考

- ADR-0002：`.tao/knowledge/adr-0002-build-orchestration.md`（L18：`.cache/<name>.git`、`.cache/refs/<id>.git`）
- 本项目：`.tao/tasks/infra/INFRA-003t-manifest与锁系统.md`、`.tao/tasks/infra/INFRA-004t-组件获取与打补丁工具.md`
- DADAO-0628：`.work/DADAO-0628/manifests/components.lock.toml`（内容溯源，非执行必需）

## 验收标准

1. `manifests/components.lock.toml` 的 `name = "llvm-project"`、`patch_series = "components/llvm-project/patches/series"`；`repository`/`commit`/`enabled`/`role`/`[[component.source]]` 不变；qemu/gem5 条目完全不变
2. `manifests/references.lock.toml` 的 `id = "DADAO-0628"`、`id = "DADAO"`；`path`/`head`/`repository`/`reuse` 不变
3. `Makefile` 的 `LLVM_SRC ?= .work/source/llvm-project/llvm`、`$(call component-enabled,llvm-project)`、报错文案 `'llvm-project'`；`QEMU_SRC`/`LLVM_BUILD` 不变
4. `.cache/llvm.git` → `.cache/llvm-project.git`、`.cache/refs/dadao-0628.git` → `.cache/refs/DADAO-0628.git`、`.cache/refs/dadao.git` → `.cache/refs/DADAO.git` 均已完成
5. `.work/DADAO-0628` 和 `.work/DADAO` 的 `origin` 指向新缓存路径（`git -C .work/DADAO-0628 remote -v` 确认）
6. `make manifest-check` PASS
7. `make fetch-refs` PASS（验证缓存迁移后工作树可正常更新）
8. 文档路径同步：全部 15 个文件（LLVM-001k/002t/003t/004t/005t/006t/007t/008t/009t/011t/013m、INFRA-006t、INFRA-009t、INFRA-008t、INTEG-003t；其中 INFRA-009t/008t 为用户裁定 2026-09-17 追加）中 `components/llvm/patches` → `components/llvm-project/patches`、`.work/source/llvm` → `.work/source/llvm-project`、示例标识符已更新；0628 自身路径引用未被误改
9. `make check` PASS

## 完成区

**测试结果**：通过 9/9 条验收标准；失败原因：无

**修改文件**（本任务 engineer 实现产出）：
- `manifests/components.lock.toml`：`name="llvm"`→`"llvm-project"`、`patch_series` 路径更新
- `manifests/references.lock.toml`：`id="dadao-0628"`→`"DADAO-0628"`、`id="dadao"`→`"DADAO"`
- `Makefile`：L14 `LLVM_SRC`、L75 `component-enabled`、L76 报错文案
- `.tao/tasks/llvm/LLVM-001k-模块启动.md`（L20, L24, L33-38）
- `.tao/tasks/llvm/LLVM-002t-LLVM组件基线.md`（L18, L41, L54, L60, L61, L70, L90, L91, L106）
- `.tao/tasks/llvm/LLVM-003t-Triple注册.md`（L14, L16-18, L21, L62-64, L71, L95）
- `.tao/tasks/llvm/LLVM-004t-Register-TableGen.md`（L15, L53-54, L71, L84）
- `.tao/tasks/llvm/LLVM-005t-指令格式-TableGen.md`（L15, L65-66, L98）
- `.tao/tasks/llvm/LLVM-006t-AsmParser与CodeEmitter.md`（L15, L49-50, L81）
- `.tao/tasks/llvm/LLVM-007t-CodeEmitter修复与lit.md`（L15, L59, L61）
- `.tao/tasks/llvm/LLVM-008t-反汇编器.md`（L15, L47-48, L78）
- `.tao/tasks/llvm/LLVM-009t-lit字节CHECK.md`（L57）
- `.tao/tasks/llvm/LLVM-011t-RA指令MC支持.md`（L15, L45, L47）
- `.tao/tasks/llvm/LLVM-014m-LLVM-MC里程碑.md`（L14-20）
- `.tao/tasks/infra/INFRA-006t-Makefile编排.md`（L265, L266, L511）
- `.tao/tasks/infra/INFRA-009t-组件锁多源字段.md`（L70）— 用户裁定 2026-09-17 追加
- `.tao/tasks/infra/INFRA-008t-补v5自身ADR.md`（L399）— 用户裁定 2026-09-17 追加
- `.tao/tasks/integ/INTEG-003t-跨模块接口对齐.md`（L18）
- 缓存迁移：`.cache/llvm.git`→`.cache/llvm-project.git`、`.cache/refs/dadao-0628.git`→`.cache/refs/DADAO-0628.git`、`.cache/refs/dadao.git`→`.cache/refs/DADAO.git`
- origin 修正：`.work/DADAO-0628` 和 `.work/DADAO` 的 origin URL

**git diff 涉及但非本任务 engineer 引入的文件**（规划阶段 architect 产出）：
- `.tao/knowledge/changelog.md`：INFRA-013t 规划行（architect `/plan` 产出）
- `.tao/knowledge/milestones.md`：INFRA-013m→014m 里程碑顺延（architect `/plan` 产出）
- `.tao/tasks/infra/INFRA-001k-模块启动与任务分解.md`：INFRA-013t 任务分解追加（architect `/plan` 产出）
- `.tao/tasks/infra/INFRA-007t-开发容器.md`：INFRA-013t 依赖更新（architect `/plan` 产出）
- `.tao/tasks/infra/INFRA-013m-infra里程碑.md`（已删除→INFRA-014m）：里程碑顺延（architect `/plan` 产出）

**验收结果**（逐条对应 9 条验收标准，每条附实际命令与关键输出）：

1. ✅ `manifests/components.lock.toml` 的 `name = "llvm-project"`、`patch_series = "components/llvm-project/patches/series"`；`repository`/`commit`/`enabled`/`role`/`[[component.source]]` 不变；qemu/gem5 条目完全不变
   ```
   $ grep -E 'name|patch_series' manifests/components.lock.toml
   name = "llvm-project"
   patch_series = "components/llvm-project/patches/series"
   name = "sjtu"
   name = "qemu"
   patch_series = "components/qemu/patches/series"
   name = "gem5"
   patch_series = "components/gem5/patches/series"
   ```

2. ✅ `manifests/references.lock.toml` 的 `id = "DADAO-0628"`、`id = "DADAO"`；`path`/`head`/`repository`/`reuse` 不变
   ```
   $ grep -E '^id|^path|^head' manifests/references.lock.toml
   id = "DADAO-0628"
   path = ".work/DADAO-0628"
   head = "2d270604b778d609e1a09b4047271b5309005ffc"
   id = "DADAO"
   path = ".work/DADAO"
   head = "f9bde0481668ffab325db8d8c5d8c4cc791c6232"
   ```

3. ✅ `Makefile` 的 `LLVM_SRC ?= .work/source/llvm-project/llvm`、`$(call component-enabled,llvm-project)`、报错文案 `'llvm-project'`；`QEMU_SRC`/`LLVM_BUILD` 不变
   ```
   $ sed -n '14p' Makefile
   LLVM_SRC   ?= .work/source/llvm-project/llvm
   $ sed -n '75,76p' Makefile
   	@$(call component-enabled,llvm-project) || { \
   	  echo "build-mc: component 'llvm-project' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
   ```

4. ✅ 缓存目录已迁移
   ```
   $ ls .cache/ .cache/refs/
   .cache/:
   llvm-project.git  refs
   .cache/refs/:
   DADAO-0628.git  DADAO.git
   ```

5. ✅ 工作树 origin 指向新缓存路径
   ```
   $ git -C .work/DADAO-0628 remote -v
   origin	/mnt/tao/DADAO-v5/.cache/refs/DADAO-0628.git (fetch)
   origin	/mnt/tao/DADAO-v5/.cache/refs/DADAO-0628.git (push)
   $ git -C .work/DADAO remote -v
   origin	/mnt/tao/DADAO-v5/.cache/refs/DADAO.git (fetch)
   origin	/mnt/tao/DADAO-v5/.cache/refs/DADAO.git (push)
   ```

6. ✅ `make manifest-check` PASS
   ```
   $ make manifest-check
   enabled components: none
   references: 2
   manifest validation: PASS
   ```

7. ✅ `make fetch-refs` PASS
   ```
   $ make fetch-refs
   enabled components: none
   references: 2
   manifest validation: PASS
   fetch-refs: DADAO-0628 already at 2d270604b778; skipping
   fetch-refs: DADAO already at f9bde0481668; skipping
   ```

8. ✅ 文档路径同步：15 个文件全部更新（含用户裁定追加的 INFRA-009t/008t）；0628 自身路径引用未被误改。反例核验（严格模式，无尾斜杠）：
   ```
   $ grep -rn "components/llvm/patches\|source/llvm" .tao/tasks/ Makefile | grep -v "llvm-project"
   → 仅 DADAO-0628 保护行（LLVM-001k/003t/004t/005t/006t/007t/008t）、INFRA-013t 任务书自身、INFRA-003t/009t/004t 历史验证输出
   $ grep -rn "source/llvm[^-]" .tao/tasks/ Makefile | grep -v "DADAO-0628"
   → 仅 LLVM-002t L70（删除线历史决议文本）、INFRA-013t 任务书自身
   $ git diff .tao/tasks/ | grep "DADAO-0628"
   → 仅 LLVM-001k 的 v5 路径变更上下文（0628 自身引用未改）
   ```

9. ✅ `make check` PASS（exit=0）；154 条 `DATA COVERAGE GAP` 为已知 report-only 项
   ```
   $ make check
   enabled components: none
   references: 2
   manifest validation: PASS
   DATA COVERAGE: 154 gap(s) found (inventory declares ✓ but no active data case)
   validate_vectors: 178/178 M1 identities covered OK
   repository checks: PASS
   ```

**新发现/坑**：
- `replaceAll` 对含 `components/llvm/patches` 的文本会同时修改 DADAO-0628 保护行（LLVM-007t/008t）；需在 replaceAll 后逐行核查保护行，发现误改须手动 revert。
- `grep -v "llvm-project"` 用尾斜杠模式 `source/llvm/` 会漏检以反引号结尾的写法（如 `.work/source/llvm`）；必须用 `source/llvm[^-]` 或 `source/llvm[^p]` 等更严格模式。
- `git diff --stat` 显示23个文件变更，其中18个为本任务 engineer 实现产出，5个为规划阶段 architect 产出（changelog/milestones/INFRA-001k/007t/013m 删除）。
- `make check` 的154条 `DATA COVERAGE GAP` 是已知 report-only 项，exit=0。

**遗留问题**：
- 无。

**补记（2026-09-17，主会话，交叉复核后）**：architect 交叉复核确认 Accepted，并提出 3 处记录性问题，由主会话直接修正（不另派子代理，用户裁定）：
- **F1**：`.tao/tasks/infra/INFRA-009t-组件锁多源字段.md:258` 的前瞻性陈述仍写 `components/llvm/patches/series`（原任务书清单只覆盖其 L70）→ 已改为 `components/llvm-project/patches/series`。
- **P1**：本完成区验收标准 1 的命令输出被截断（漏 `name = "sjtu"`，即 `[[component.source]]` 的 name）→ 已按真实 stdout 补全。
- **P2**：本任务书 §5 引言原写「共 13 个文件」，与同节表格及验收标准 8 的 15 个不一致 → 已改为 15。
- 复核同时确认：`source/llvm`、`.cache/llvm`、`name = "llvm"`、小写 `dadao-0628`、未标注的 `INFRA-013m` 全仓已无残留（除允许不改的历史记录）；`qemu`/`gem5`/`testcases`/`spec` 无跨模块影响；无需新增 ADR。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审者**：engineer
**时间**：2026-09-17
**方式**：自主逐行审查

#### 逐行审查发现

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| E1-1 | LLVM-007t L54 的 DADAO-0628 保护行被 replaceAll 误改 | ✅已修 | revert 为 `components/llvm/patches/0005-dadao-asmparser.patch` | `sed -n '54p'` 确认含 `components/llvm/patches` |
| E1-2 | LLVM-008t L42 的 DADAO-0628 保护行被 replaceAll 误改 | ✅已修 | revert 为 `components/llvm/patches/0006-dadao-disassembler.patch` | `sed -n '42p'` 确认含 `components/llvm/patches` |
| E1-3 | LLVM-008t L72 的 DADAO-0628 保护行被 replaceAll 误改 | ✅已修 | revert 为 `.work/DADAO-0628/components/llvm/patches/series` | `sed -n '72p'` 确认含 `components/llvm/patches` |
| E1-4 | INFRA-003t/INFRA-009t/INFRA-004t 中残留 `components/llvm/patches` | ❌不修 | 属历史验证输出/引用，任务书明确不改 | 任务书「不修改的文件及理由」表 |
| E1-5 | `git status` 显示非本任务文件有改动 | ❌不修 | 属规划阶段 architect 产出，非 engineer 引入 | `git diff` 归属分析 |

#### 判决

**自主自审通过**：3 项 finding 已修（E1-1/2/3），2 项为设计选择/非本任务范围。

### 第 1 轮 reviewer 验收（Needs Revision）

**审查者**：reviewer
**时间**：2026-09-17
**判决**：Needs Revision

**发现清单**：
- **B1（阻塞）**：LLVM-003t L21 的 `.work/source/llvm` 未改（grep 用 `source/llvm/` 带尾斜杠漏检）
- **N1（越界改动）**：LLVM-003t `## 交付物` L62-64 的 bullet 缩进从 `- ` 被误改为 `  - `
- **N2（口径问题）**：完成区写「7/7」但验收标准有9条；标准1-3缺命令/输出
- **N3（归属错误）**：changelog/milestones/INFRA-001k/007t/008t/013m 被称为「pre-existing」，实为规划阶段 architect 产出
- **N4（用户裁定）**：INFRA-006t L266、INFRA-009t L70、INFRA-008t L399 需更新示例标识符

### 第 1 轮返工

**返工者**：engineer
**时间**：2026-09-17

**逐项处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| B1 | ✅已修 | LLVM-003t L21：`.work/source/llvm`→`.work/source/llvm-project` | `grep -n 'source/llvm[^-]' .tao/tasks/llvm/LLVM-003t-Triple注册.md` → EXIT=1（无匹配） |
| N1 | ✅已修 | LLVM-003t L62-64：`  - ` 恢复为 `- `（顶层 bullet） | `sed -n '62,64p'` 确认缩进为 `- `；`git diff` 确认无非路径格式变动 |
| N2 | ✅已修 | 完成区改为「9/9 条验收标准」；每条补实际命令与输出 | 见上方完成区验收结果1-9 |
| N3 | ✅已修 | 完成区新增「git diff 涉及但非本任务 engineer 引入的文件」段，归属为「规划阶段 architect 产出」 | `git diff --stat` 23文件=18 engineer +5 architect |
| N4 | ✅已修 | INFRA-006t L266：`component-enabled,llvm`→`component-enabled,llvm-project`；INFRA-009t L70：`.cache/llvm.git`→`.cache/llvm-project.git`；INFRA-008t L399：第二个 `INFRA-013m` 补加 `（现 INFRA-014m）` | `sed -n '266p'`/`sed -n '70p'`/`sed -n '399p'` 逐条确认 |

**任务书一致性更新**：
- 「需要修改的文件」表追加 INFRA-009t（L70）、INFRA-008t（L399），标注「用户裁定 2026-09-17 追加」
- INFRA-006t 表项补充 L266 `component-enabled` 变更
- 验收标准第8条更新为15个文件枚举（含追加2个）

**反例核验修正**：
- 旧模式 `source/llvm/`（带尾斜杠）→ 新模式 `source/llvm[^-]`（不含尾斜杠），已重跑确认无遗漏

### 第 2 轮 reviewer 验收

**验收者**：reviewer
**时间**：2026-09-17
**判决**：**Accepted**（9/9 条验收标准满足）

**第 1 轮 5 项发现复核**：B1 ✅已修（`grep -n 'source/llvm[^-]' LLVM-003t` → 无输出、exit=1）；N1 ✅已修（`git show HEAD:` 与工作区 `cat -A` 逐字节对比，仅 `llvm`→`llvm-project` 一处 token 不同，`git diff -w --numstat` 同为 `10 10`）；N2 ✅已改（完成区 9/9 + 逐条命令与输出）；N3 ✅已修（23 = 18 engineer + 5 architect）；N4 ✅已修（三处示例标识符）。

**独立重跑**：`make manifest-check` exit=0；`make fetch-refs` exit=0（`already at …; skipping` ×2，未触网）；`make check` exit=0（154 gap report-only、`178/178`、`repository checks: PASS`）；`git diff --name-only -- tools/infra/` 为空；`enabled=false`/`commit=""` 未变；`git diff -U0 | grep '^[+-].*DADAO-0628：'` 无匹配（保护行未被改）。

**非阻塞记录项**（转主会话当场修正）：P1 完成区 #1 命令输出漏 `name = "sjtu"`；P2 任务书 §5 引言「13 个文件」应为 15。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-17
**判决**：**确认 Accepted**；**无需新增/修订 ADR**（判据 2「跨模块」命中，但判据 3–6 均不命中，且用户已裁定不立 ADR）。

**独立核对**：`make manifest-check`/`make fetch-refs`/`make check` 均 exit=0；缓存目录与两工作树 origin；manifest 逐字段（含 `[[component.source]]` 正确嵌套于 `llvm-project` 下）；全仓 grep 排查（`components/llvm/`、`source/llvm`、`.cache/llvm`、`name = "llvm"`、`dadao-0628`、`INFRA-013m`）；`fetch.py:113 target = source_root / name` 与 `Makefile:14 LLVM_SRC` 三者一致；`status.py`/`clean_work.py`/`fetch_refs.py` 均按 manifest 动态取名、无硬编码。

**新发现**：
- **F1**（非阻塞，应补修）：`.tao/tasks/infra/INFRA-009t-组件锁多源字段.md:258` 的前瞻性陈述仍用旧路径（原任务书清单只覆盖其 L70）。
- **F2**（非阻塞）：`changelog.md` 缺 `INFRA-013t` 实现条目。
- 跨模块影响：`qemu`/`gem5`/`testcases`/`spec` **无影响**（`QEMU-002t` 的 `name` 本就等于仓库名；`INTEG-003t` L18 已更新）。

**MEMORY.md 建议**：infra 进度行区间写法失真（`013t` 已完成但 `010t`~`012t` 待开始），建议改为「`002t`~`009t`、`013t` 已验证；`010t`~`012t` 待开始」；并在「重要决策」段补「标识符 = 原始仓库名」。

### 收尾

- F1/P1/P2 由**主会话**直接修正（用户裁定，2026-09-17），详见完成区「补记」。
- `**状态**` 置 `已验证`（2026-09-17）。
- `changelog.md` 补实现条目（F2）；`MEMORY.md` 更新 infra 进度行 + 追加「标识符 = 原始仓库名」决策。
