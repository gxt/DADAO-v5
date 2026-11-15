# m13-infra-002: 引导 ics150–ics180 四台新节点

**模块**：infra
**项目里程碑**：M13
**依赖**：无
**可并行分片**：是（四台独立，互不干扰；主控机只做编排）
**状态**：已验证

## 用户授权（2026-11-12，原话）

> 「新的四台节点机，根目录和/home目录是两个磁盘，应该有300G可用，请确认；可以开展apt安装和长构建」

## 实测现状（2026-11-12）

- SSH 别名 `ics150`/`ics160`/`ics170`/`ics180`（映射只在主控机本地 SSH 配置里，**按 2026-11-07 裁定不入库**）；账号 `ubuntu`、`sudo` 免密
- 主机名 `ics150`–`ics180`，Ubuntu 24.04.5，**40 vCPU**、**125 GiB** 内存
- **磁盘确认（用户口径核对）**：`/` = 98 GB（可用 83 GB）、**`/home` = 338 GB（可用 320 GB）**，同一 VG（`sda3` 443.6 GB 拆两个 LV）⇒ 合计可用 **约 403 GB**，与用户「约 300 GB」一致且更宽裕
- **仓库不存在**（节点仓库根缺失）；`git`/`python3` 有；**`gcc`/`make`/`cc`/`ld` 全缺**

## 目标

1. **装包**：`nodes.md §4.2` 那份列表（`build-essential cmake ninja-build scons ccache` 等），四台并行，逐台留 `dpkg -s` 抽查证据。
2. **同步仓库**：用主控机 bundle（不走 GitHub），落到节点仓库根（在 `/home` 大盘上）。
3. **引导**：`tools/infra/bootstrap_node.sh`（`make fetch` → `apply-series` → `build-mc build-lld` → `install-host` → `make check`）。
4. **就绪判据**（`nodes.md §5`）：同一 commit 下 `make check` + `make check-inst` 与主控机一致。

## 参数

- `JOBS=16`（40 vCPU 留一半余量；**不沿用 207/208 的 32**）
- ccache 用节点本地默认目录、`max_size=50G`（不复制主控机配置）
- 每台日志落主控机该任务的运行期日志目录（按主机分文件）；**未建证据子目录**，验证以逐条亲跑 + 日志留证（审阅记录 finding 5）

## 验收标准

1. 四台 `dpkg -s build-essential make gcc` 均 installed
2. 四台 `~/DADAO-v5` 存在且 HEAD 与主控机一致
3. 四台 `make check` rc=0、`make check-inst` 与主控机同结果
4. 四台 `df -h /home` 有 ≥200 GB 余量（构建后）
5. 文档：`nodes.md` 的状态列改「就绪」，补实测口径（vCPU/磁盘/JOBS）

## 说明

- 长构建（LLVM 13 GB）**归主会话**监督：逐台留 PID/日志/EXIT，不 `setsid` 后失联。
- 磁盘余量：`/` 83 GB 给系统与 `/tmp`；构建主体在 `/home`（320 GB），够两套组件树。
- 失败处置：单台失败不阻塞其余三台；失败留现场并在本册记录原因后继续。

## 硬约束

1. 只动节点侧；仓库修改在主控机（本任务不改代码）。
2. 不 commit 节点侧改动；节点不装 OpenCode。
3. 计数与结论从命令现场输出直接抄（`ISS-388` 教训）。
4. 不放 `/tmp` 做跨机中转（`AGENTS.md`）；bundle 走 `.work/`。

## 审阅记录

### 第 1 轮 reviewer 验收（2026-11-12 00:37–00:52）

**重跑记录（reviewer 亲跑，日志 = 本任务运行期日志目录下 `review-*.log`）**
- 四台并行 `ssh <host> 'cd 仓库 && make -s check JOBS=16; …exit $rc'` → ics150/160/170/180 均 **CHECK_RC=0**（00:37:52→00:39:05，各 75 KB 完整门控输出、11 处 `结果: PASS`、**0 条 FAIL**）
- 四台 `make -s check-inst JOBS=16` → 均 **CHECKINST_RC=0**：`Results: 996 total, 991 passed, 0 failed, 5 deferred`、`check-inst: PASS（991/996，载体 24 册）`、`Results: 44 total, 44 passed`、`check-inst: PASS（44/44，载体 24 册）`、`check-inst: PASS (vast full + tiny subset)`；vast 日志另有 `缺册断言…24 册全部在盘 / 载体册数: 24 / 用例总数: 1040`
- 主控机对照（HEAD=a8e85889，与节点仅差 8 个纯文档提交，check-inst 不读 `.tao`）`make -s check-inst` → **rc=0**，结果行**逐字相同** ⇒「与主控机一致」成立
- 主控机 `make -s check` → **rc=2**：`check-patch-tree` 10 条（qemu `trans_fp.c.inc` + chipyard `Wuming*`，补丁文件与源树 apply 状态错位）+ `check-temp-dirs` 5 项他任务遗留 ⇒ 均为并发任务中间态；本任务 8 个提交全在 `.tao/`+`docs/`、不碰 `components/`，**不计本任务失败**（待 m13-qemu-003 等收口后主控机复绿）
- 磁盘/内存亲测：四台 `df -h` = `/` 98G 用 12G 余 **82G**、`/home` 338G 用 69G **余 252G**；`free -g` 125；`nproc` 40 ⇒ 完成区 69/252 口径一致（「/ 余 83 GB」为引导前值，漂移 1 G 正常）
- 无外网亲测（逐台串行）：github/pypi/gitlab `curl rc=28 http=000`（DNS 可解析）、`archive.ubuntu.com` **302 rc=0** ⇒ 前提仍成立，`nodes.md` §网络写对
- 装包：四台 45 个 §4.2 包逐项 `install ok installed`（目标 1 达成）；HEAD 四台 `e8d212cd`、`dirty=0`（clone 日志 23:18 `CLONE_RC=0`，同步时=主控机 HEAD）

**约束核验**：① 只动节点侧/不改代码 ✓（8 提交全 `.tao`+`docs`）② 节点零未提交改动、四台无 opencode ✓ ③ 计数现场抄 ✓（44/44、24 册、1040、69/252 GB 皆亲验）④ bundle 在 主控机的节点同步目录、节点侧家目录，无 `/tmp` 中转 ✓ ⑤ 完成区 9 行 ≤30 ✓；验收前后 `git status --porcelain -uall` 空、`nodes.md` md5 未变；reviewer 未 commit/push

**Findings（文档/留证级，按「文档小错不阻断」记档，architect 收尾改）**
1. **任务书 L15 把 SSH 端口段 + `HostName` + 账号写进仓库**：违反 `nodes.md` 维护规则（用户 2026-11-07「不写节点地址与登录凭据」），且与 `nodes.md` L36「地址与端口只在本地 config 不入库」自相矛盾 ⇒ **收尾必删该括注**
2. 任务书 L31 `.work/log/infra/m13-infra-001/<host>/`：任务号错（应 002）、实际落点为 m13-infra-002 平铺；参数要求「逐台留 `*_EXIT`」现场 **0 个**（逐行 rc + `all steps completed` 可替代，但与参数不符）
3. 任务书 4 处含家目录路径（L15/18/23/36；60 个任务书中仅本任务书）
4. 完成区「8 步 rc=0」vs 现场 `[step 0]`–`[step 8]` **9 行 rc=0**（列举亦 9 项）
5. 无 该任务的证据目录 一键证据脚本（硬约束 8）；reviewer 以逐条亲跑替代——标准门控有可达 FAIL 路径（主控机 `check-patch-tree` 亲测红即证）
6. `nodes.md` §8 新增节点流程未串入 `subprojects` 一步；§5 仍标「两台实测」未补四台（§8 step 6 要求）
7. apt 步骤四台 `APT_RC=255`（needrestart 重启 ssh 断连）完成区未披露；目标 1 承诺的「逐台 dpkg -s 抽查证据」未落盘（包已由 reviewer 逐项验真）

**判决：Accepted** —— 四台就绪判据亲跑全绿、`check-inst` 与主控机逐字一致、无外网前提成立；上述 7 条为文档/留证级，交 architect 收尾修订，不另开一轮。

## 完成区（2026-11-12 00:24）

- **四台 `[step 0]`–`[step 8]` 共 9 行 rc=0**：时区 / 预检 / git / 仓库同步 / `make fetch`（本地 `.cache`，未触网）/ `apply-series` / `build-mc build-lld` / `install-host` / `make check`
- **就绪判据**（`nodes.md §5`）：四台 `HEAD=e8d212cd`、`make check-inst` **PASS（44/44，载体 24 册）**、`check-inst: PASS (vast full + tiny subset)`
- **磁盘**：构建后 `/home` 用 69 GB、**余 252 GB**（`/` 83 GB 可用）
- **装包**：§4.2 全套 45 个包，四台逐项 `dpkg -s` 均 `install ok installed`（抽查证据在运行期日志）；apt 走内部镜像（外网不可达）。**披露**：apt 首轮四台 `APT_RC=255`，原因是装完后 `needrestart` 重启服务把 SSH 会话断掉，包实际已装上（复核 `dpkg -s` 确认）
- **两个坑（已入 `nodes.md`）**：
  ① 节点**无外网**（GitHub / PyPI 不可达，apt 通）⇒ 只能 bundle + `.cache`；
  ② QEMU 的 **meson subprojects 不在 `.cache`**，`install-host` 会逐个去 gitlab 拉（先 `keycodemapdb`、再 `berkeley-softfloat-3`）⇒ 需从主控机 rsync **整个** `.work/source/qemu/subprojects/`（6.5 MB）
- 日志：主控机该任务的运行期日志目录（`apt-*` / `clone-*` / `sync-cache` / `bootstrap{,2,3}-*` / `verify-*`）
- 未改任何仓库代码；节点侧只有仓库本体与构建产物

#### 收尾（architect，2026-11-12 01:27）

- reviewer **Accepted**：四台 `make check` rc=0 ×4、`check-inst` **991/996（5 deferred）+ 44/44**、载体 24 册、1040 例；与主控机同 commit 结果**逐字相同**；`/home` 余 252 GB、`/` 余 82 GB、125 GiB、40 vCPU。
- **finding 1 已修（我的违规）**：任务书曾把 SSH 端口 + `HostName` + 账号写进仓库，违反用户 2026-11-07 裁定；已删，只留「映射在主控机本地 SSH 配置，不入库」。
- 其余 finding 已改：任务号 001→002、家目录路径改「节点仓库根」、完成区「8 步」→「`[step 0]`–`[step 8]` 9 行」、披露 apt 首轮 `APT_RC=255`（needrestart 断连、包已装上，`dpkg -s` 复核）。
- `nodes.md §8 step 3` 已补「无外网节点要带 QEMU 的 meson subprojects」；§1.1 记两个坑。
- 主控机 `make -s check` rc=2 属并发任务中间态（`check-patch-tree` 的 qemu 未导出 + 他任务临时目录），四台节点同门控全绿。

