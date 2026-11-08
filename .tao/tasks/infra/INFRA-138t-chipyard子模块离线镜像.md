# INFRA-138t: chipyard 子模块离线镜像与 fetch 集成

**模块**：infra
**项目里程碑**：M11
**依赖**：无
**状态**：待开始

## 背景与事实

- `fetch.py` 对 `submodule` 的引用数 = **0**：chipyard 的 55 个子模块**完全不在** `make fetch` 的管理范围内。
- `.cache/` 只有 11 个**组件**镜像（`chipyard.git` 是父仓），**没有**任何子模块镜像。
- 三台机器的子模块是**各走各的路**拿到的：主控机 34/55（早期手工）、`server207` 30/55（chipyard 的 init 脚本，GitHub clone）、`server208` 30/55（内网 tar 中继）。
- 后果：新机器**无法离线复现**；三台集合不一致；GitHub 在这些机器上时通时不通。
- 已有基础：`manifests/chipyard-submodules.lock.toml` 已锁全部 55 个的 `path`/`url`/`commit`，并用 `lite = true` 标出**最小必需集**（chipyard `init-submodules-no-riscv-tools.sh` 的默认集）。实测该集 git 数据约 **260 MB**。
- 用户裁定（2026-11-08）：「同意你的建议」——做离线子模块镜像 + `fetch` 集成。

## 目标

1. **镜像**：`.cache/submodules/<sanitized-path>.git`，覆盖 lock 里全部 `lite = true` 的子模块；bare 镜像（`git clone --mirror` 或等价），含锁定 commit。
   - 目录名由 `path` 确定性派生（如 `generators/testchipip` → `generators__testchipip.git`），不得用可能重名的 basename。
2. **`fetch.py` 集成**：组件声明 `submodule_lock = "manifests/chipyard-submodules.lock.toml"` 时：
   - 对每个 `lite` 子模块：镜像缺失 ⇒ **明确失败**并提示「从主控机 `sync_cache` 同步」；镜像存在 ⇒ `git -C <source> submodule init` + 把 `submodule.<path>.url` 指向本地镜像 + `git submodule update --init --checkout <path>`，并校验 `rev-parse HEAD == commit`。
   - 幂等：已在锁定 commit 且 clean ⇒ 跳过（打印 `already initialized`）。
   - 不触碰 `lite = false` 的子模块。
3. **`sync_cache.py` 校验扩展**：除组件 commit 外，校验各节点 `.cache/submodules/*.git` 是否含 lock 中全部 `lite` commit；缺任一 ⇒ 该节点 FAIL（提示重新同步）。
4. **文档**：`nodes.md` §11 补「子模块来源」；`docs/Process-01` 补一段「子模块镜像」约定。

## 范围 / 非范围

**在范围内**：`tools/infra/fetch.py`、`tools/infra/sync_cache.py`、`manifests/components.lock.toml`（仅给 chipyard 加 `submodule_lock` 字段）、`manifests/chipyard-submodules.lock.toml`（如需修 `lite` 标记错误）、`nodes.md`、`docs/Process-01`、本任务书、`milestones.md`。

**不在范围**：子模块补丁能力（已撤销的 `INFRA-137t`）、chipyard 源码/构建改动、`lite = false` 的子模块、`Makefile` 目标名。

## 验收标准

1. `.cache/submodules/` 中 lite 镜像数量 == lock 中 `lite = true` 条目数（现场统计，不写死）；每个镜像 `git cat-file -e <commit>^{commit}` 通过。
2. **离线可复现（核心）**：在临时目录用 `.cache/chipyard.git` 克隆一份 chipyard，**屏蔽网络**（如 `http_proxy=http://127.0.0.1:9`、`https_proxy` 同）跑 `fetch.py` 的子模块初始化 ⇒ 全部 lite 子模块检出到 lock 的 commit，`git submodule status` 无 `-`，无网络访问成功记录。
3. **幂等**：再跑一次 ⇒ 全部 `already initialized`，源树 HEAD/内容不变（md5 对照）。
4. **失败路径**：临时移走一个镜像 ⇒ 明确报错（指出路径与「从主控机同步」），非零；`cp` 还原后回绿。
5. **`sync_cache.py`**：两节点在镜像同步后校验 PASS；人为删一个镜像 ⇒ 该节点 FAIL、提示重新同步。
6. 现有 `make fetch` / `make apply-series` / `check-patch-tree` / L1 零回归。
7. 完成区 ≤30 行、无运行期路径；`nodes.md` 与 `docs/Process-01` 已更新。

## 说明

- **镜像建立**：主控机可联网时由 `fetch.py` 首次克隆（失败可重试），失败则明确报错；节点不做公网克隆，只从主控机同步。
- 现有三台已初始化的子模块**不需要重装**；实现完成后用「临时克隆 + 离线初始化」证明能力即可（不要为了验收去重置共享源树）。
- 子模块数量取 lock 现场统计，不得在代码/文档里写死。
