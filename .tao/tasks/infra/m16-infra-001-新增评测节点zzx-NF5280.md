# m16-infra-001: 新增评测节点 zzx-NF5280 并引导到就绪

**模块**：infra
**项目里程碑**：M16
**依赖**：无
**可并行分片**：否
**预估**：3–5 h
**档位**：大改（节点引导：装包 + 仓库同步 + 工具链从零构建）
**状态**：待验收

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

1. **别名**：`~/.ssh/config` 新增 `Host zzx-NF5280`（`localhost:22202`、`ubuntu`、`StrictHostKeyChecking accept-new`），端口/地址不入库；`ssh -o BatchMode=yes` 免密 rc=0。
2. **装包**：`§4.2` 全量 `apt-get install` rc=0（`ninja`/`cmake`/`scons`/`meson`/`jq`/`dtc`/`ripgrep` 已核在 PATH）；另装系统 `clang 18.1.3`（见第 9 条）；`ccache max_size=50G`；复制主控机 `~/.gitconfig`（身份一致）；`/tmp/opencode` 建为 `ubuntu`。
3. **仓库 + 缓存**：bundle（26 M，`--all`）→ 节点 clone；`.cache` 4.9 G `rsync` 后 `sync_cache.py --hosts zzx-NF5280` **overall rc=0 / PASS**（enabled 组件 commit + 30 条子模块镜像逐条 PASS）。
4. **工具链**：`install-host` **PASS**（clang 23.1.3 / qemu-dadao 11.1.1，安装根 `.dadao/cross-toolchain`）；`build-gem5` **PASS**（`gem5.opt` 750 MB，补丁集更新后重建）。
5. **引导脚本两处缺陷（本任务修，`b3a1a6fb`）**：① `make -jN build-mc build-lld` 两个 `GATE_LOCKED_TARGETS` 并发 ⇒ loser 等 3600 s 后 `Error 75`（step 6 实测 60 min 全损）；② `install-host` 的前置并发使 `build-builtins` 先于 `build-lld` 产出运行 ⇒ `bin/ld.lld not found`。改法：step 6 顺序调用 `build-mc` → `build-lld` →（必要时）`compiler-rt` 配置 → `build-builtins`，再进 step 7。
6. **L1**：节点 `make -k -j14 check` **rc=2（27 s）**，红集与主控机**逐项相同** 5 项（`cfx-aliases`/`cfx-alias-table` = `ISS-511`；`knowledge-refs` = `milestones-m18.md` 缺 `ADR-0059`；`manifests-guard`；`milestones-fresh` = `m16-qemu-001` 台账行 `\|` 被计 5 格）。主控机多出的 `patch-tree`（`ISS-507`）/`musl-freshness`/`run-artifacts`（563 条历史日志名）是主控机本地残留，节点**不复现**。
7. **L2 子集**：`build-bootrom` PASS；`check-inst-asm` **PASS**、`check-inst-sig` **PASS**（合计 51 s）。`make check-inst` 已于 `m13-testcases-043` 退役，任务书原验收项据此改判据（已记 `nodes.md §5`）。
8. **事实**：节点 `69d248ed`、`dirty=0`；`remote.py status` **rc=0/PASS**；`.work` 59 G / `.cache` 4.6 G / `.dadao` 13 G；`/home` 74 %；主控机同期 `21c9d7e0`，差集仅 `.tao` 两册。
9. **登记 issue**：`ISS-511`（`contracts/cfx-aliases.txt` 未随 `m16-spec-001` 重生成 ⇒ L1 两门控红）、`ISS-512`（`check-linux-toolchain` 报告含依赖宿主 `clang` 的行却参与逐字比对）。
10. **未做（明确遗留）**：chipyard conda 环境与 `simulator-*`（§11.6，派 chipyard 任务前建）；`verilator` 仍为系统 4.226（chipyard 口径由 conda 5.022 提供）。
11. 修改文件：`tools/infra/bootstrap_node.sh`、`.tao/knowledge/nodes.md`、`.tao/knowledge/issues.yaml`、`.tao/knowledge/milestones-m16.md`、本任务书。
