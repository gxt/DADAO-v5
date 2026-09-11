# QEMU-002t: QEMU 组件基线

**模块**：qemu
**项目里程碑**：M1
**依赖**：`INFRA-006t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`manifests/components.lock.toml`（`INFRA-003t` 产出，`qemu` 条目 `enabled = false`、`commit = ""`）、`Makefile`（`INFRA-006t` 产出的 `build-qemu` stub）、QEMU 上游仓库 `https://github.com/qemu/qemu.git`
- 输出：
  - `.tao/knowledge/adr-0006-qemu-baseline.md`（ADR-0006，Status 先 Candidate）
  - `manifests/components.lock.toml` 中 `qemu` 条目 `enabled = true` + 完整 40 字符 commit
  - `Makefile` 的 `build-qemu` 从 stub 替换为真实 `configure` + `make` 构建
- 约束：commit 必须为完整 40 字符十六进制 SHA，不接受 tag/branch/短 SHA；ADR 先于 manifest；只改 `qemu` 条目，不动 llvm/gem5；`make manifest-check` 必须 PASS；ADR 内部引用用章节名（§Context 等），不写行号

## 背景（完整）

### 目标

为 v5 的 QEMU 标量核心开发选定一个可复现的 QEMU 上游 commit，完成：ADR-0006（记录选定理由）、组件锁启用、`build-qemu` 真实构建目标。0628 对应任务 `DL-006a` 在完成区实际选定 QEMU v10.0.0（SHA `385b0a7d9785c8f3ac7b116d7f31d61502b55183`），并经架构评审 Accepted。

### 设计理由

- **稳定性**：选 stable release 系列的最新 commit（避免 master/main 分支 API 颠簸），保证跨开发机与 CI 可复现。
- **TCG API**：确认所选 commit 的 TCG 接口（`tcg_gen_*`、`TCGv`、`gen_helper_*`、翻译块 API）已稳定；QEMU 9.x/10.x 均满足，可优先选较新 stable。
- **构建验证**：在本地或开发容器内能 `./configure --target-list=riscv64-softmmu --enable-tcg` 无错完成（用 riscv64 作为代理验证 TCG 框架可用；DADAO target 在 `QEMU-003t` 添加），并真实 `git checkout <SHA>` 成功。
- **不 bump**：M1 所有 QEMU 补丁针对此 commit 开发，期间不 bump；严重上游 bug 通过 cherry-pick 处理并记录新 ADR。

### 关键概念 / 数据

- ADR 格式：见 v5 `.tao/knowledge/adr-authoring.md`（`Status` / `Context` / `Decision` / `Rationale` / `Consequences`）。
- **Decision 必含字段**：选定的 QEMU 版本（如 `QEMU x.y.z`）、完整 40 字符 commit SHA、`qemu/qemu` GitHub commit URL（仅供人类参考）。
- **Rationale 至少 3 点**：稳定性、TCG API 可用性、构建验证。
- **Consequences**：M1 所有补丁针对此 commit；不整体 bump。
- `components.lock.toml` schema（`INFRA-003t`）：`format`、`work_root`、`[[component]]` 字段 `name`/`enabled`/`repository`/`commit`/`patch_series`/`role`。
- `build-qemu`：`QEMU_SRC ?= .work/source/qemu`、`QEMU_BUILD ?= .work/build/qemu`（与 `INFRA-004t` 的 fetch 落点 `.work/source/<name>` 一致）；`configure --target-list=dadao-softmmu --enable-tcg --disable-werror` 后 `make -j$(nproc)`；`QEMU_SRC`/`QEMU_BUILD` 用 `?=` 允许外部覆盖。本任务先以 `riscv64-softmmu` 代理验证 configure；`dadao-softmmu` 由 `QEMU-003t` 引入。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-006a-qemu-baseline.md`（完整转述：目标、三份交付物、约束、验收门、两轮 Architecture Review）。
- DADAO-0628：`docs/adr/0006-qemu-baseline.md`（ADR 内容：Context/Decision/Rationale/Consequences，QEMU v10.0.0 与 40 字符 SHA）。
- DADAO-0628：`manifests/components.lock.toml`、`Makefile`、`scripts/manifest_check.py`。

## 交付物

- `.tao/knowledge/adr-0006-qemu-baseline.md`：ADR-0006，覆盖 Context/Decision/Rationale/Consequences，含完整 40 字符 SHA 与至少 3 条 rationale；Status 先 Candidate，review 通过后 Accepted。
- `manifests/components.lock.toml`：`qemu` 条目 `enabled = true`、`commit = "<40 字符 SHA>"`；其他字段（repository/patch_series/role）不变；llvm/gem5 条目不变。
- `Makefile`：`build-qemu` 由 stub 替换为真实 `configure` + `make`（并加入 `.PHONY` 与 `help`）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **基线独立选定**：不得把 0628 的 QEMU v10.0.0 / `385b0a7d…` 直接当作 v5 既定基线。v5 须重新决定版本、重新验证 commit 可达性（`git ls-remote` / fetch 后 `git checkout`）并在 ADR-0006 记录理由；若沿用同一版本，须写明理由并重新验证。
- **ADR 落点**：v5 在 `.tao/knowledge/adr-0006-qemu-baseline.md`（0628 在 `docs/adr/`）。
- **构建路径**：v5 上游 checkout 为 `.work/source/qemu`（`INFRA-004t` 约定），构建为 `.work/build/qemu`；与 `INFRA-006t` 的 `QEMU_SRC` 默认值需统一。
- **不复制补丁正文/编码数据**：0628 的 `components/qemu/patches/*` 属 0.4.1，本任务只选定上游 commit，不引入任何 0628 补丁。
- **措辞**：不使用按开发批次命名的字段/目录；路线指向 DADAO-0628。

## 已知坑 / 结论

- **configure 未验证是 0628 的遗留**：0628 完成区记录了 `./configure --target-list=riscv64-softmmu --enable-tcg` 通过；v5 仍须在 `make fetch` 后真实执行 configure，并把输出（≥3 行）写入完成区。
- **tag/branch 不作为可复现基线**：enabled 组件必须有完整 40 位 commit，否则 `make manifest-check` 失败。
- **ADR 先于 manifest**：ADR Status 先 Candidate 即可提交，架构师 review 后升 Accepted。
- **路径一致性**：`build-qemu` 的 `QEMU_SRC` 必须指向 `.work/source/qemu`（`INFRA-004t` 的 fetch 落点），避免与 `INFRA-006t` 的默认值不一致。
- **不改其他组件条目**：只改 `qemu`。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-006a-qemu-baseline.md`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0006-qemu-baseline.md`
- DADAO-0628：`.work/DADAO-0628/manifests/components.lock.toml`
- DADAO-0628：`.work/DADAO-0628/Makefile`
- v5：`.tao/knowledge/adr-authoring.md`（ADR 格式与模板）
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/tasks/infra/INFRA-003t-manifest与锁系统.md`、`.tao/tasks/infra/INFRA-004t-组件获取与打补丁工具.md`、`.tao/tasks/infra/INFRA-006t-Makefile编排.md`

## 验收标准

1. `.tao/knowledge/adr-0006-qemu-baseline.md` 存在，含完整 40 字符 SHA 与至少 3 条 rationale，Status 为 Candidate（review 后 Accepted）
2. `manifests/components.lock.toml` 的 `qemu` 条目 `enabled = true`、`commit` 为完整 40 字符十六进制 SHA；llvm/gem5 条目未改
3. `Makefile` 的 `build-qemu` 为真实 `configure` + `make`（含 `.PHONY` 与 `help`）
4. `make manifest-check` PASS
5. 完成区含真实 `git checkout <SHA>` 与 `./configure` 输出（≥3 行）
6. `Makefile` 的 `build-qemu` 中 `QEMU_SRC` 指向 `.work/source/qemu`（与 `INFRA-004t` 的 fetch 落点一致）

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
