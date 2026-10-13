# ADR-0008: QEMU 组件基线选版

**状态**：Accepted
**日期**：2026-09-18
**关联**：`QEMU-002t`

## Context（背景）

v5 的 QEMU 标量核心开发需要选定一个可复现的上游 QEMU commit 作为基线。该基线须满足：

- **CPU 框架**：提供 TCG（Tiny Code Generator）翻译框架、`tcg_gen_*` 指令生成 API、`TCGv` 类型、`gen_helper_*` 辅助函数调用、翻译块（TranslationBlock）管理等核心基础设施，用于实现 DADAO 目标的指令语义。
- **目标机定义**：提供 `target/` 目录结构、CPU 模型定义、机器描述（machine description）框架。
- **构建系统**：提供 `./configure` + `make` 构建流程，支持 `--target-list` 选择特定目标。

DADAO 是全新目标（`ADR-0001`），不复用旧版目标代码。所有 M1 补丁均应用于此干净上游 commit。

### 选版约束

1. **可复现性**：commit 必须为完整 40 字符 SHA，不接受 tag/branch/短 SHA。
2. **稳定性**：优先选择 stable release 系列的最新 commit（避免 master/main 分支 API 颠簸），保证跨开发机与 CI 可复现。
3. **TCG API 可用性**：确认所选 commit 的 TCG 接口（`tcg_gen_*`、`TCGv`、`gen_helper_*`、翻译块 API）已稳定。
4. **构建验证**：在本地或开发容器内能 `./configure --target-list=riscv64-softmmu --enable-tcg` 无错完成（用 riscv64 作为代理验证 TCG 框架可用；DADAO target 在 `QEMU-003t` 添加）。
5. **与 0628 的关系**：v5 须独立决定版本，不得直接照搬 0628 的 QEMU v10.0.0；若沿用须重新验证并写明理由。

## Decision（决策）

### D1：版本与 lock 值

- **QEMU 基线** = **v11.1.1**
- **lock 值** = commit `c3d48b7d1e89604920e5b81b91140c2ad39a1943`（完整 40 位十六进制）
- **附注** tag `v11.1.1` 的**对象** SHA = `5e35f26695645b20931e10d8567c7e0169e62c07`（**仅作溯源记录，不作 lock 值**）
- **人类参考 URL** = `https://github.com/qemu/qemu/commit/c3d48b7d1e89604920e5b81b91140c2ad39a1943`（仅供人类参考，不做 lock 用途）

> **风险提示**：任务书原「设计理由」假定基线在 9.x/10.x 系列，而 v11.1.1 超出该假定（v11.x 是最新稳定版）。`QEMU-003t` 及后续任务须关注 TCG/构建 API 在 v11.x 中是否有需适配的变更。

### D2：获取来源与方式，含浅镜像取舍

- `repository` 保持 `https://github.com/qemu/qemu.git`（规范上游身份，不变）
- `[[component.source]]` = `name = "sjtu"`、`url = "https://mirror.sjtu.edu.cn/git/qemu.git"`（ADR-0005 的 schema；`fetch.py` 默认取 `source` 首个）
- 镜像落点 `.cache/qemu.git` 为**浅 bare 预填充**：`git clone --bare --depth 1 --branch v11.1.1`（实测 4.1 s、51.78 MiB、11,630 objects、11,256 文件；**非 treeless**，worktree 可离线重建）
- **Consequences 必须写明「浅镜像无完整历史」的边界**：`git describe`、跨 commit diff、完整历史遍历不可用；`sync_mirror` 的增量 `git fetch --prune` 在浅镜像上的语义受限；如需完整历史须 unshallow 或重建镜像

## Rationale（理由）

1. **稳定性**：v11.1.1 是 QEMU 11.x 系列的最新补丁版本，包含自 v11.1.0 以来的所有 bugfix。作为最新的正式发布版，经过完整的发布测试流程，API 稳定性有保障。

2. **TCG API 可用性**：QEMU 11.x 的 TCG 框架保持稳定。自 QEMU 7.x–8.x 以来，TCG 核心接口（`tcg_gen_*`、`TCGv`、`gen_helper_*`、翻译块 API）保持向后兼容，11.x 无破坏性变更，可直接用于 DADAO 目标开发。

3. **构建验证**：该 commit 是 `qemu/qemu` 仓库的官方发布 commit，已实际验证——浅 bare 镜像 `git clone --bare --depth 1 --branch v11.1.1` 落地后，`.work/source/qemu` 的 `HEAD` 命中该 commit，并以 `./configure --target-list=riscv64-softmmu --enable-tcg` 验证 TCG 框架可用（DADAO target 待 `QEMU-003t` 注册）。

4. **否决备选 v10.2.4 的理由**：
   - v10.2.4 是 v10.x 系列的维护版本，而 v11.x 是当前活跃的主线稳定系列，支持窗口更长。
   - v11.1.1 包含更多上游 bugfix 和 TCG 改进，减少后续 cherry-pick 需求。

5. **否决备选 v10.0.0（0628 同版）的理由**：
   - **v5 须独立决定**：不得直接照搬 0628 的 v10.0.0，需重新验证并写明理由。
   - **v11.1.1 为最新稳定版**：支持窗口更长，包含更多上游 bugfix。
   - **代价**：缺少与 0628 同版的补丁对照，但 v5 补丁系全新开发，无需直接复用 0628 补丁。
   - **内容溯源**：DADAO-0628 `docs/adr/0006-qemu-baseline.md` 使用 QEMU v10.0.0（tag 对象 SHA `385b0a7d9785c8f3ac7b116d7f31d61502b55183`，其指向的 commit 为 `7c949c53e936aa3a658d84ab53bae5cadaa5d59c`）。v5 须独立验证 commit 可达性，不得直接照搬。

## Consequences（影响）

1. **M1 期间 commit 不 bump**：若发现严重 TCG 框架 bug，通过 cherry-pick 处理并记录新 ADR，不整体 bump。
2. **组件锁启用**：`qemu` 组件在 `manifests/components.lock.toml` 中标记 `enabled = true`，并填入完整 40 字符 commit SHA。
3. **补丁占位**：`components/qemu/patches/series` 作为空占位文件存在，满足 `manifest_check.py` 对 enabled 组件的强制要求。
4. **构建验证**：`Makefile` 的 `build-qemu` 目标使用此 commit 进行真实 `configure` + `make` 构建（`dadao-softmmu` target 待 `QEMU-003t` 引入）。
5. **v11.x 超出原假定**：任务书原设计理由假定基线在 9.x/10.x 系列，v11.1.1 超出该假定。`QEMU-003t` 及后续任务须关注 TCG/构建 API 在 v11.x 中是否有需适配的变更（如 `tcg_gen_*` 签名变化、构建系统参数调整等）。
6. **浅镜像边界**：
   - `git describe`、跨 commit diff、完整历史遍历不可用。
   - `sync_mirror` 的增量 `git fetch --prune` 在浅镜像上的语义受限。
   - 如需完整历史须 `git fetch --unshallow` 或重建镜像。

## 状态说明

- **Accepted**（2026-09-19）：D1、D2 经用户逐条确认后固化；`QEMU-002t` 经 reviewer 两轮验收（第 1 轮 Needs Revision：ADR 事实错/完成区数字不实/伪造 `ls` 输出 → 返工 → 第 2 轮 **Accepted**，10/10）与 architect 交叉复核确认，条件满足，由主会话置 `Accepted`。
- **确认记录**：D1（版本与 lock 值：QEMU v11.1.1、commit `c3d48b7d1e89604920e5b81b91140c2ad39a1943`）、D2（获取来源与方式：SJTU 镜像、浅 bare 预填充）均由用户判定为「保留」。
- 决策变更时新增 ADR 或标注 `Superseded`，不直接改写已 `Accepted` 的决策。
