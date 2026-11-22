# m16-infra-001: 新增评测节点 zzx-NF5280 并引导到就绪

**模块**：infra
**项目里程碑**：M16
**依赖**：无
**可并行分片**：否
**预估**：3–5 h
**档位**：大改（节点引导：装包 + 仓库同步 + 工具链从零构建）
**状态**：待开始

## 背景

- 用户 2026-11-22 提供新节点：反向隧道本地端口 `22202`，账号 `ubuntu`，主机名 `zzx-NF5280`。
- 实测（2026-11-22 15:13）：**16 vCPU**（2×Xeon E5620，4 核×2 线程×2 socket @2.4 GHz，2 NUMA）、内存 **62 GiB**、`/` 可用 **690 G**、`/home` 可用 **311 G**（已用 65%）、Ubuntu **24.04.4**、`sudo -n` 可用、时区已 **CST**、外网可达（`github.com`/`pypi.org` 均 200）。
- 空机：无 `~/DADAO-v5`、`.cache` 为空、无 `.work`/`.dadao`；缺 `ninja`/`cmake` 等 `nodes.md §4.2` 包（`gcc 13.3`、`python3 3.12`、`ccache 4.9.1`、`verilator 4.226` 系统版已有）。

## 目标

1. 本地 `~/.ssh/config` 加别名 `zzx-NF5280`（`localhost:22202` / `ubuntu`；**地址与端口不入库**）。
2. 按 `nodes.md §8` 引导：装 `§4.2` 包 → 复制主控机 git 身份 → bundle 同步仓库 → 推 `.cache` → `bootstrap_node.sh`（`fetch → apply-series → compiler-rt → install-host → make check`）。
3. 更新 `nodes.md` §1 清单与 §5 就绪判据（只写主机名/核数/内存/测试 `--jobs`/角色/状态）。

## 验收（真实 rc）

1. `make check`（L1）rc=0、工作树 clean；`make check-inst` 与主控机同 commit 结果逐字一致（44/44）。
2. `python3 tools/infra/remote.py status --hosts zzx-NF5280 --repo '~/DADAO-v5'` rc=0（`--log-prefix m16-infra-001`）。
3. 证据：每步日志与 `*_EXIT` 落运行期日志目录；记录 `make check` 用时。
4. `nodes.md` 补实测行（16 核 ⇒ 测试 `--jobs` **14**）。

## 约束

- 引导只在节点执行；**不在节点手改被跟踪文件**；日志/中转文件不放 `/tmp`（主控机 `.work/`、节点家目录）。
- 构建/测试 `-j 14`（16 vCPU，留 2 核）；不手写其它值。
- 不改 `spec/`/契约/组件补丁；仓库改动只限本任务书、`nodes.md`、台账；提交前须用户确认。

## 完成区
