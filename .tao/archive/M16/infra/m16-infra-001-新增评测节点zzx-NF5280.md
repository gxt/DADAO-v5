# m16-infra-001: 新增评测节点 zzx-NF5280 并引导到就绪

**模块**：infra
**项目里程碑**：M16
**依赖**：无
**可并行分片**：否
**预估**：3–5 h
**档位**：大改（节点引导：装包 + 仓库同步 + 工具链从零构建）
**状态**：已验证

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
6. **L1**：节点 `make -k -j14 check` **rc=2（节点 37 s、主控机同命令 28 s）**，红集与主控机**逐项相同** 5 项（`cfx-aliases`/`cfx-alias-table` = `ISS-511`；`knowledge-refs` = `milestones-m18.md:39` 引用了尚不存在的 ADR 文件；`manifests-guard`；`milestones-fresh` = `m16-qemu-001` 台账行 `\|` 被计 5 格）。主控机多出的 `patch-tree`（`ISS-507`）/`musl-freshness`/`run-artifacts`（566 条历史日志名）/`temp-dirs` 是主控机本地残留（随他人会话清理而变），节点**不复现**。
7. **L2 子集**：`build-bootrom` PASS；`check-inst-asm` **PASS**、`check-inst-sig` **PASS**（合计 51 s）。`make check-inst` 已于 `m13-testcases-043` 退役，任务书原验收项据此改判据（已记 `nodes.md §5`）。
8. **事实**：节点 `69d248ed`、`dirty=0`；`remote.py status` **rc=0/PASS**；`.work` 59 G / `.cache` 4.6 G / `.dadao` 13 G；`/home` 74 %；主控机同期 `21c9d7e0`，差集仅 `.tao` 两册。
9. **登记 issue**：`ISS-511`（`contracts/cfx-aliases.txt` 未随 `m16-spec-001` 重生成 ⇒ L1 两门控红）、`ISS-512`（`check-linux-toolchain` 报告含依赖宿主 `clang` 的行却参与逐字比对）。
10. **未做（明确遗留）**：chipyard conda 环境与 `simulator-*`（§11.6，派 chipyard 任务前建）；`verilator` 仍为系统 4.226（chipyard 口径由 conda 5.022 提供）。
11. 修改文件：`tools/infra/bootstrap_node.sh`、`.tao/knowledge/nodes.md`、`.tao/knowledge/issues.yaml`、本任务书（台账 `milestones-m16.md` 的进行中行由并行会话 `b2aba871` 一并提交，本任务未改该文件）。

## 审阅记录

### 第 1 轮 reviewer 验收（2026-11-22，命令全部本人重跑，rc 捕被检命令自身，不采信完成区转述）

**判决：Accepted**（7 项硬核验全过；5 条文档级/设计层 finding 记档于末尾，按「文档级小错不阻断」不返工）

1. **提交对齐 PASS**：`ssh -o BatchMode=yes zzx-NF5280 'cd ~/DADAO-v5 && git rev-parse HEAD && git status --porcelain -uall | wc -l'` → `495c82b941876d7c6d6c6a19e3149f7553dd5872` + `0`，rc=0；主控机 `git rev-parse HEAD` 同值，`git status --porcelain -uall` 为空。
2. **remote.py PASS**：`python3 tools/infra/remote.py status --hosts zzx-NF5280 --repo '~/DADAO-v5' --log-prefix m16-infra-001` → `zzx-NF5280 -> 0 (PASS)`、`overall rc=0`，rc=0（另记 commit 同上、`dirty_files=0`、`clang 23.1.3`、`qemu 11.1.1`、`disk_use_pct=74`）。
3. **L1 红集 PASS**：节点 `make -k -j14 check` rc=2，`make: ***` 失败目标**恰 5 项**：`check-cfx-aliases`、`check-cfx-alias-table`、`check-knowledge-refs`、`check-manifests-guard`、`check-milestones-fresh`（我独立跑 2 次同集，日志落运行期日志目录 `m16-infra-001/review-node-check.log`）。主控机同命令 rc=2，失败目标 9 项 = 上述 5 项 + `check-temp-dirs`、`check-musl-freshness`、`check-run-artifacts`、`check-patch-tree` ⇒ **超集成立**。5 项同门控失败原因两侧**同类**：cfx-aliases `DADAO-12:605 vs 603`（140 vs 142 行）、alias-table `regs=1322 vs 1320`、knowledge-refs 悬空 2（`milestones-m18.md:39` + `nodes.md:160` 均缺同一目标 ADR）、manifests-guard `tests/ee-tiny 多出 __pycache__`、milestones-fresh `L33 实得 5 格` + `m16-qemu-001 未列入三表`。
4. **L2 双门控 PASS**：节点 `make -j14 check-inst-asm` → `check-inst-asm: PASS`、`ASM_RC=0`；`make -j14 check-inst-sig` → `check-inst-sig: PASS`（272/272 镜像、静态槽 4501）、`SIG_RC=0`。
5. **改法 PASS**：`bash -n tools/infra/bootstrap_node.sh` rc=0；`--dry-run` rc=0 且第 6 步文案与实现逐句一致；`GATE_LOCKED_TARGETS` 含 `build-mc build-lld build-builtins install-host`；`_locked-install-host: install-cfx-aliases build-mc build-lld build-qemu build-builtins` 全在锁内、经「持有者为祖先」嵌套放行 ⇒ 不再互等；脚本内已无「一次 make 传多个锁内目标」（仅单目标 `install-host`/`check`）。节点引导日志实证：旧跑 `[step 6] cmd: make -j14 build-mc build-lld → rc=2`（内含 `build-lld Error 75`），修复后 `build-mc rc=0 → build-lld rc=0 → build-builtins rc=0 → install-host rc=0 → check rc=2`，全程无 `ld.lld not found`。
6. **数字抽查 PASS（节点现场复算）**：`nproc=16`；`MemTotal 65933704 kB ≈ 62 G`；`du -sh` → `.work 59G / .cache 4.6G / .dadao 13G`；`df -h /home` → `74%`；`.dadao/cross-toolchain/bin/clang` = `23.1.3`、`qemu-dadao` = `11.1.1`；测试 `--jobs 14`；`ISS-511` 与两侧现象逐字相符，`ISS-512` 与「系统 `clang 18.1.3` 已装 ⇒ `check-linux-toolchain: PASS`」相符。
7. **无越界 PASS**：`git show --name-only b3a1a6fb 495c82b9` 并集 = `tools/infra/bootstrap_node.sh`、`.tao/knowledge/nodes.md`、`.tao/knowledge/issues.yaml`、本任务书，全在完成区清单内；未动 `Makefile`/`spec/`/契约/组件补丁。

**Finding（文档级，交 architect 收尾改，不返工）**
- F1 L1 用时写 `27 s`（§5 与完成区第 6 条），现场我测 `37.19 s`、工程师自有节点日志 `elapsed=0:37.23`；`27.56 s` 是主控机数字 ⇒ 归属错。
- F2 knowledge-refs 实为悬空 **2** 项，其中 `nodes.md:160` 的字面 ADR 引用由本任务提交写入（`git log -S` 定位 495c82b9）⇒ 本次改动使该门控多 1 条违规（rc 与红集不变）；完成区只描述 1 项。
- F3 主控机多出项文档写 3，我实测 4（多 `check-temp-dirs`，因他人会话陈旧临时目录超 2 h，17:50 工程师跑时未超阈值）；`run-artifacts` 文档 563 条、我测 566 条（均时变）。
- F4 完成区「修改文件」列 `milestones-m16.md`，但两提交均未动它（台账行由并行会话 `b2aba871` 加入）；`b3a1a6fb` 提交信息「+台账进行中行」与 `--stat` 不符。
- F5 设计残留（本任务范围外，供 architect 定夺）：`_locked-build-builtins: manifest-check build-mc` 缺 `build-lld` 前置，而其 recipe 断言 `ld.lld` 存在 ⇒ 手跑 `make -jN install-host`（冷树）仍可能报 `ld.lld not found`；建议另立 issue 把 `build-lld` 补进前置。

**快照对账**：验收前后各一次 `git status --porcelain -uall` 均为空（rc=0）⇒ 4 个目标文件与 HEAD 一致；本轮仅在运行期日志目录新增 `review-node-check.log`、`review-master-check.log`（均在忽略目录内），允许的临时目录内的中间件（dry-run/计时）已清理；未改任何受跟踪交付物（本审阅记录除外）、未在节点改被跟踪文件、未执行任何 git 提交。
