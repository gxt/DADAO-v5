# LLVM-002t: LLVM 组件基线

**模块**：llvm
**项目里程碑**：M1
**依赖**：`INFRA-006t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`manifests/components.lock.toml`（`INFRA-003t` 产出，`llvm` 条目 `enabled = false`、`commit = ""`）、`Makefile`（`INFRA-006t` 产出的 `build-mc` stub）、LLVM 上游仓库 `https://github.com/llvm/llvm-project.git`
- 输出：
  - `.tao/knowledge/adr-0005-llvm-baseline.md`（ADR-0005，Status 先 Candidate）
  - `manifests/components.lock.toml` 中 `llvm` 条目 `enabled = true` + 完整 40 字符 commit
  - `components/llvm/patches/series`（占位空文件；`manifest_check.py` 要求 enabled 组件的 `patch_series` 存在）
  - `Makefile` 的 `build-mc` 从 stub 替换为真实 `cmake` + `ninja` 构建
- 约束：commit 必须为完整 40 字符十六进制 SHA，不接受 tag/branch/短 SHA；ADR 先于 manifest；只改 `llvm` 条目，不动 qemu/gem5；`make manifest-check` 必须 PASS；ADR 内部引用用章节名（§Context 等），不写行号

## 背景（完整）

### 目标

为 v5 的 LLVM MC 开发选定一个可复现的 LLVM 上游 commit，完成：ADR-0005（记录选定理由）、组件锁启用、`build-mc` 真实构建目标。

### 设计理由

- **稳定性**：选 release/major 分支的最新 commit（或已稳定 RC），避免 main 分支 API 颠簸，保证跨开发机与 CI 可复现。
- **MC 框架**：确认所选 commit 已包含 `MCTargetDesc` / `MCCodeEmitter` / `MCELFObjectTargetWriter` / `ELFObjectWriter` 的稳定 API。
- **构建验证**：在 `make doctor` 环境（或开发容器）内能 `cmake -DLLVM_TARGETS_TO_BUILD=...` 无错完成 configure；DADAO 是全新 target，不复用 legacy toolchain 代码，所有补丁都应用在此干净上游 commit 上。

### 关键概念 / 数据

- ADR 格式：见 v5 `.tao/knowledge/adr-authoring.md`（`Status` / `Context` / `Decision` / `Rationale` / `Consequences`）。
- **Decision 必含字段**：选定的 LLVM 版本（major.minor）、完整 40 字符 commit SHA（不得用 tag/branch）、`llvm-project` GitHub commit URL（仅供人类参考，不做 lock 用途）。
- **Rationale 至少 3 点**：稳定性、MC 框架可用性、构建验证。
- **Consequences**：M1 所有 patch 针对此 commit 开发，commit 在 M1 期间不 bump；若发现严重 MC 框架 bug，通过 cherry-pick 处理并记录新 ADR，不整体 bump。
- `components.lock.toml` schema（`INFRA-003t`）：`format`、`work_root`、`[[component]]` 字段 `name`/`enabled`/`repository`/`commit`/`patch_series`/`role`。
- `build-mc`：`cmake -G Ninja -B .work/build/llvm -S .work/source/llvm/llvm -DLLVM_TARGETS_TO_BUILD=DADAO -DLLVM_ENABLE_PROJECTS="" -DCMAKE_BUILD_TYPE=RelWithDebInfo -DLLVM_ENABLE_ASSERTIONS=ON`，随后 `ninja llvm-mc llvm-objdump llvm-lit FileCheck`；`LLVM_BUILD`/`LLVM_SRC` 用 `?=` 允许外部覆盖。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-005a-llvm-baseline.md`（完整转述：目标、三份交付物、约束、验收门、两轮 Architecture Review）。
- DADAO-0628：`docs/adr/0005-llvm-baseline.md`（内容溯源：Context/Decision/Rationale/Consequences；ADR 格式见 v5 `.tao/knowledge/adr-authoring.md`）。
- DADAO-0628：`manifests/components.lock.toml`、`Makefile`、`scripts/manifest_check.py`。

## 交付物

- `.tao/knowledge/adr-0005-llvm-baseline.md`：ADR-0005，覆盖 Context/Decision/Rationale/Consequences，含完整 40 字符 SHA 与至少 3 条 rationale；Status 先 Candidate，review 通过后 Accepted。
- `manifests/components.lock.toml`：`llvm` 条目 `enabled = true`、`commit = "<40 字符 SHA>"`；其他字段（repository/patch_series/role）不变；qemu/gem5 条目不变。
- `Makefile`：`build-mc` 由 stub 替换为真实 `cmake`+`ninja`（并加入 `.PHONY` 与 `help`）。
- `components/llvm/patches/series`：占位空文件（`components/llvm/patches/` 目录 + 空 `series`）；`manifest_check.py` 对 enabled 组件强制要求 `patch_series` 存在，补丁正文由后续任务（`LLVM-003t` 起）追加。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **基线独立选定**：不得把 0628 的 `llvmorg-22.1.8` / `ca7933e47d3a3451d81e72ac174dcb5aa28b59d1` 直接当作 v5 既定基线。v5 须重新决定版本、重新验证 commit 可达性（`git ls-remote` / fetch 后 `git checkout`）并在 ADR-0005 记录理由；若沿用同一版本，须写明理由并重新验证。
- **ADR 落点**：v5 在 `.tao/knowledge/adr-0005-llvm-baseline.md`（0628 在 `docs/adr/`）。
- **构建路径**：v5 上游 checkout 为 `.work/source/llvm/llvm`（`INFRA-004t` 约定），构建为 `.work/build/llvm`；与 `INFRA-006t` 的 `LLVM_SRC` 默认值需统一（见「已知坑」）。
- **不复制补丁正文/编码数据**：0628 的 `components/llvm/patches/*` 属 0.4.1，本任务只选定上游 commit，不引入任何 0628 补丁。
- **措辞**：不使用按“阶段”命名的字段/目录；路线指向 DADAO-0628。

## 已知坑 / 结论

- **cmake configure 未验证是 0628 的遗留（N1）**：0628 完成区仅做 `git ls-remote`，未真实 configure。v5 本任务须在 `make fetch` 后真实执行 configure，并把输出（≥3 行）写入完成区。
- **tag/branch 不作为可复现基线**：enabled 组件必须有完整 40 位 commit，否则 `make manifest-check` 失败。
- **enabled 必须伴随 `patch_series`**：`manifest_check.py` 对 `enabled = true` 的组件强制要求 `components/<name>/patches/series` 存在；翻转 `enabled` 时必须同时创建占位空 `series`，否则 `make manifest-check` 失败。
- **ADR 先于 manifest**：ADR Status 先 Candidate 即可提交，架构师 review 后升 Accepted。
- **路径一致性**：`INFRA-006t` 的 `LLVM_SRC` 默认值写的是 `.work/llvm/llvm`，而 `INFRA-004t` 的 fetch 落点是 `.work/source/llvm`；本任务须将 `build-mc` 的 `LLVM_SRC` 统一为 `.work/source/llvm/llvm`，或与 infra 侧对齐后记录。
- **不改其他组件条目**：只改 `llvm`。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-005a-llvm-baseline.md`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0005-llvm-baseline.md`
- DADAO-0628：`.work/DADAO-0628/manifests/components.lock.toml`
- DADAO-0628：`.work/DADAO-0628/Makefile`
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/tasks/infra/INFRA-003t-manifest与锁系统.md`、`.tao/tasks/infra/INFRA-004t-组件获取与打补丁工具.md`、`.tao/tasks/infra/INFRA-006t-Makefile编排.md`

## 验收标准

1. `.tao/knowledge/adr-0005-llvm-baseline.md` 存在，含完整 40 字符 SHA 与至少 3 条 rationale，Status 为 Candidate（review 后 Accepted）
2. `manifests/components.lock.toml` 的 `llvm` 条目 `enabled = true`、`commit` 为完整 40 字符十六进制 SHA；qemu/gem5 条目未改
3. `Makefile` 的 `build-mc` 为真实 `cmake`+`ninja`（含 `.PHONY` 与 `help`）
4. `make manifest-check` PASS
5. 完成区含真实 `git checkout <SHA>` 与 `cmake` configure 输出（≥3 行）
6. `Makefile` 的 `build-mc` 中 `LLVM_SRC` 指向 `.work/source/llvm/llvm`（与 `INFRA-004t` 的 fetch 落点一致）
7. `components/llvm/patches/series` 存在（占位空文件）

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
