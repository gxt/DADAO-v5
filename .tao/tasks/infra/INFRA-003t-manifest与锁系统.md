# INFRA-003t: manifest 系统 + 组件锁 + 参考锁

**模块**：infra
**项目里程碑**：M1
**依赖**：`INFRA-002t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：DADAO-v5 现有 `manifests/dadao.lock.toml`、`README.md`（规范版本表）
- 输出：`manifests/components.lock.toml`、`manifests/references.lock.toml`、`scripts/manifest_check.py`
- 约束：组件锁只需占位/待定 commit（LLVM/QEMU/gem5 的精确 commit 在后续 llvm/qemu/gem5 模块确定）；reference 锁 DADAO-0628 `2d270604b778d609e1a09b4047271b5309005ffc`；不得复制 0.4.1 的补丁/代码正文

## 背景（完整）

### 目标

提供机器可读、可校验的锁系统：component 锁（上游可构建组件按精确 commit + 补丁序列）与 reference 锁（只读参考仓库按精确 commit），并由 `manifest_check.py` 做结构校验，作为 `make check` 的一部分。

### 设计理由

- ADR-0002：每个组件按完整 commit 获取；tag/branch 不作为可复现基线；环境相关 Git URL 重写、仅按可变分支选版本、未审查的 `fixups` 层均被拒绝。
- 0628 `components.lock.toml` 头注释明确：component 在 ADR 记录上游选择与精确 commit 之前保持 disabled；tag/branch 不被接受为可复现基线。
- reference 采用 `policy = "reference-only"`：只复用规范文本 / 架构与教训，不复制实现。

### 关键概念 / 数据

- `components.lock.toml` schema（0628）：`format = 1`、`work_root = ".work"`，`[[component]]` 数组，字段 `name` / `enabled` / `repository` / `commit` / `patch_series` / `role`。
- `references.toml` schema（0628）：`format`、`captured_on`、`policy`，`[[reference]]` 数组，字段 `id` / `path` / `repository` / `head` / `dirty` / `purpose` / `reuse` / `selected_paths`。
- `manifest_check.py` 校验规则（0628）：
  - spec lock（0628 有、v5 无）：`commit` 为 40 位 SHA-1；`status` ∈ {candidate, frozen}；`foundation_included` 非空。
  - component：`name` 非空且不重复；**enabled 组件必须有完整 40 位 commit**；`patch_series` 文件必须存在。
  - reference：`id` 非空；`head` 为完整 commit；`path` 为绝对路径。
  - 全部通过后打印 spec / enabled components / reference 数量，退出码 0。

### 上游引用

- DADAO-0628 `manifests/components.lock.toml`：component 列表与 schema（含 llvm / qemu / gem5 / llvm-test-suite / embench / musl / linux 的 repository 与 commit；本任务只转述机制，不复制其 commit 作为 v5 基线）。
- DADAO-0628 `manifests/references.toml`：reference 列表与 schema（wiki-candidate、legacy-meta、legacy-llvm、legacy-linux、legacy-musl、llvm-test-suite；`policy = "reference-only"`；`reuse` 字段声明"只取架构/教训/接口，不复制实现"）。
- DADAO-0628 `manifests/spec.lock.toml`：spec 锁的字段布局（`status = "frozen"`、`foundation_included` / `foundation_excluded`）。
- DADAO-0628 `scripts/manifest_check.py`：上述校验逻辑。
- DADAO-0628 `docs/adr/0002-build-orchestration.md`：commit 锁定与 `.work/` 约定。

## 交付物

- `manifests/components.lock.toml`：
  - `format = 1`、`work_root = ".work"`。
  - `[[component]]`：`llvm`（repository `https://github.com/llvm/llvm-project.git`，role "LLVM MC + CodeGen"）、`qemu`（`https://github.com/qemu/qemu.git`，role "CPU core / decode / scalar execution / bare-metal machine"）、`gem5`（`https://github.com/gem5/gem5.git`，role "functional second reference"）。
  - **commit 待定**：三组件 `enabled = false`、`commit = ""`，注释说明待 llvm/qemu/gem5 模块的 ADR 记录上游选择与精确 commit 后再改为 `enabled = true` 并填入完整 40 位 commit。
  - `patch_series` 指向 `components/<name>/patches/series`。
- `manifests/references.lock.toml`：
  - `format = 1`、`policy = "reference-only"`。
  - `[[reference]]` id `dadao-0628`：repository `https://github.com/holight1/DADAO-0628.git`、`head = "2d270604b778d609e1a09b4047271b5309005ffc"`、`path` 指向 `.work/DADAO-0628`、`reuse = "架构与工程教训，不复制实现"`。
  - `[[reference]]` id `dadao`：repository `https://github.com/gxt/DADAO.git`、`head = "f9bde0481668ffab325db8d8c5d8c4cc791c6232"`（取自现有 `manifests/dadao.lock.toml`）、`path` 指向 `.work/DADAO`；其 checkout 由 `INFRA-004t` 的 `fetch_refs.py` 获取。
  - DADAO 与 DADAO-0628 是两套互不相关的仓库（均已不再更新）；DADAO-0628 直接使用已有 `.work/DADAO-0628` clone，`fetch_refs.py` 只做 commit 检查、不重新拉取。
  - `path` 字段按 v5 实际位置填写（`.work/DADAO-0628` 等）。v5 简化 schema，省略 0628 的 `dirty`（执行时计算）、`purpose`（并入 `reuse`）、`selected_paths`（本阶段不需要）字段。
- `scripts/manifest_check.py`：实现 component/reference 锁校验；**v5 无 spec lock 文件**（规范版本表在 `README.md`，脚本不校验 spec 锁），并对 disabled 组件的待定 commit 放行。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- 无 ISA 相关差异（基础设施，与 ISA 版本无关）。
- spec lock schema 不同：v5 为 `[versions]` / `[foundation_included]` / `[foundation_excluded]` 表；`manifest_check.py` 需按 v5 schema 校验（如校验 `[versions].simrisc == "0.5.3"`、`status == "frozen"`），不能照搬 0628 的扁平字段检查。
- 文件名：reference 锁用 `references.lock.toml`（0628 为 `references.toml`）。
- 组件范围：v5 本阶段只锁 llvm / qemu / gem5 三个核心组件（musl / linux / embench / llvm-test-suite 属后续阶段）；commit 全部待定。
- 参考锁：v5 显式锁定 DADAO-0628（`2d270604`）与 DADAO（`f9bde048`），而非 0628 的 wiki-candidate / legacy-* 列表。

## 已知坑 / 结论

- enabled 组件必须有完整 40 位 commit；占位期应保持 `enabled = false`，否则校验失败。
- tag/branch 不作为可复现基线。
- 0628 的 `manifest_check.py` 要求 reference `path` 为绝对路径；v5 若改用项目内相对路径（`.work/DADAO-0628`），需相应调整校验规则并在任务中说明。
- 0628 references 的 `path` 指向其原作者的本地绝对路径，v5 必须改指向本项目内的真实位置（`.work/DADAO-0628` 等），否则 `make status` 会显示 `missing`。

## 参考

- DADAO-0628：`.work/DADAO-0628/manifests/components.lock.toml`
- DADAO-0628：`.work/DADAO-0628/manifests/references.toml`
- DADAO-0628：`.work/DADAO-0628/manifests/spec.lock.toml`
- DADAO-0628：`.work/DADAO-0628/scripts/manifest_check.py`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0002-build-orchestration.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `manifests/components.lock.toml` 含 llvm/qemu/gem5 三组件，commit 明确标注待定且 `enabled = false`
2. `manifests/references.lock.toml` 锁定 DADAO-0628 `2d270604b778d609e1a09b4047271b5309005ffc`
3. `scripts/manifest_check.py` 对 v5 schema 校验通过（退出码 0），且能检出 enabled 组件缺 commit、patch_series 缺失等错误
4. `python3 scripts/manifest_check.py` 直接调用退出码 0

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
