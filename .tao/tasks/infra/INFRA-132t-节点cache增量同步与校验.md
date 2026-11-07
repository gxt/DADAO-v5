# INFRA-132t: 节点 `.cache` 增量同步与校验

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-130t`（`remote.py` 已有 ssh 约定）
**状态**：待开始

## 背景与事实

节点无法稳定访问公网（`curl 28` / `GnuTLS recv error`），组件裸仓库 `.cache/<name>.git` 必须由主控机提供。当前做法是**一次性 rsync 全量**，之后无人维护，风险是：

- 主控机更新了 `.cache`（新组件 / 新 commit），节点仍停在旧内容；
- 节点 `make fetch` 发现缺 commit 会转去 **访问公网**，表现为长时间挂起后失败，报错指向网络而不是「缓存过期」。

另有两项已确认事实：

- 主控机到节点**只走 Tailscale**（`ip route` = `dev tailscale0`），节点自身在 `10.42.0.207/24`，与主控机不同网；曾观测到 DERP 中继。
- `.cache` **可写**：`fetch.py` 在镜像缺失时 `git clone --mirror`、缺 commit 时 `git fetch --prune`，二者都写 `.cache`。

用户裁定（2026-11-07）：「增量同步 + 校验」；**不做 NFS/sshfs 挂载**（跨 Tailscale 挂载断链会**挂起**而非报错；只读挂载与 `fetch.py` 写入路径冲突；运行期引入主控机单点依赖）。

## 目标

新增主控机侧脚本，把「主控机 → 节点 `.cache` 增量同步 → 逐 commit 校验」固化为一条命令：

1. **增量同步**：`rsync -a` 推送 `.cache/` 到各节点（裸仓库对象 append-only，增量应显著小于全量）；带 `--dry-run` 只看计划。
2. **逐 commit 校验**：读 `manifests/components.lock.toml`，对每个组件在节点上执行
   `git -C <cache>/<name>.git cat-file -e <commit>^{commit}`，
   全部存在才算该节点 PASS；缺任意一个即 FAIL，并明确提示「缓存过期，请重新同步」。
3. **多节点**：节点清单只从 `--hosts a,b` 或环境变量 `DADAO_NODES` 取（无内置清单）；ssh 一律 `BatchMode=yes`；并发执行、逐节点汇总 `host -> rc`，任一非零则整体非零。
4. **远端路径**：节点侧仓库位置由 `--repo`（仓库根，支持 `~/`）推导出 `<repo>/.cache`；不得写死绝对路径。

## 范围 / 非范围

**在范围内**：新增 `tools/infra/sync_cache.py`、其证据脚本、本任务书、`milestones.md`、`.tao/knowledge/nodes.md`（补「缓存维护」一节）。

**不在范围**：`fetch.py` 逻辑、`Makefile` 目标、`remote.py` 子命令、组件清单、挂载方案。

## 验收标准

1. **`--dry-run`**：打印将同步的源/目标与组件清单，退出码 0，且**不产生任何远端写入**（用两个节点的 `.cache` mtime 或 `du` 前后对比证明）。
2. **真机增量**：对两台节点首次运行完整同步成功；**连续第二次运行**传输量显著小于首次（给出 `rsync` 的 `Total transferred` 实测对比）。
3. **校验正路径**：同步后两节点校验 PASS（逐组件 commit 存在），整体 rc=0。
4. **校验负路径（可达 FAIL）**：给一个**不存在的 commit**（可用临时伪造的清单条目，或在校验器上注入一个假 commit 哈希）⇒ 该节点 FAIL、整体非零，且提示「缓存过期」。注入用临时树或 `cp`+md5，禁 git 还原。
5. **节点不可达**：给一个不可达 host ⇒ 该 host FAIL、整体非零，不静默跳过。
6. **无节点清单** ⇒ rc≠0 并提示如何提供（不得有内置默认）。
7. **不写死主机信息**：脚本内无 IP / 主机名 / 账号 / 家目录字面量（`~/` 由 `$HOME` 展开）。
8. `make check`（L1）rc=0；若唯一红为外部占用（共享 gem5 源树被其它任务占用导致 `check-patch-tree`），核实归属后不算本任务失败。
9. 完成区 ≤30 行、无运行期路径；`nodes.md` 新增「缓存维护」小节：同步命令、校验判据、**禁止挂载**的原因。

## 说明

- 脚本只负责「让节点缓存与主控机一致且可校验」，**不**负责去公网更新 `.cache`（那是主控机 `make fetch` 的职责）。
- 若实测发现 rsync 对裸仓库不安全（例如并发 fetch 导致临时对象），如实记录并给出调用前提（如「主控机不得同时执行 `make fetch`」），不要用 `--delete` 静默兜底。
