# m18-linux-018: 套件环境补齐（TMPFS/MEMFD、非 root uid、/proc/iomem）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-005`、`m18-linux-006`（LTP 两轮基线：0.8.1-rc 内核 + 自建 QEMU）
**可并行分片**：是（三个环境项互不重叠）；执行仍受 linux 组件写者互斥约束
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务三个环境项，取 1.5–2× 中位）
**档位**：中改（内核配置/镜像/权限）
**状态**：已验证
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`m18-linux-005` 首轮分诊有 3 条 `SUITE_ENV`（证据行见 `tests/unit/linux/suite/triage.yaml`）：

- `mm-mremap-dontunmap`：`memfd_create` 返回 ENOENT，因套件内核 `CONFIG_TMPFS=n`（无 shmem）；`mremap(MREMAP_DONTUNMAP)` 的匿名映射子测试本身已通过。
- `mm-pfnmap`：`/proc/iomem` 没有 RAM region，整例 SKIP。
- `mm-on-fault-limit`：套件以 PID 1（uid 0）运行，测试要求普通用户，整例 SKIP。
- **`m18-linux-006` 第三轮新增（2026-11-27，LTP 子集两轮）**：
  - `fcntl07`：套件镜像内 `PATH` 为空/不含 `/bin`，用例判 `SUITE_ENV`；
  - `mlockall02`：缺 `/etc/passwd`，`die-no-vma va=0x10` 后被 LTP 捕获为 SIGSEGV，判 `SUITE_ENV`——**须先确认该 `die-no-vma` 不是内核缺陷**（若属实，改写分诊并另立内核任务，不许用环境项盖掉）。

## 目标

1. **TMPFS/MEMFD**：在套件镜像的内核配置中启用 `CONFIG_TMPFS`（及 `CONFIG_MEMFD_CREATE` 所需项），使 `memfd_create` 可用；评估对 K6 镜像与 config pins 的影响，不得改 K6 判据。
2. **/proc/iomem**：让内核导出 RAM region（按 `spec/Kaiwu` 的内存映射，不改硬件语义）；若确属客观不支持，记录原因/证据/复评条件。
3. **非 root uid**：套件 supervisor 在跑用例前降权到非 root uid（需要 `setuid`/`setgid` 与镜像文件属主支持）；不得用「测试改成允许 root」绕过。
4. **套件基础环境**：给套件镜像补 `PATH`（`fcntl07`）与最小 `/etc/passwd`（`mlockall02`），使这两条不再因环境判 `SUITE_ENV`；`mlockall02` 若仍 `die-no-vma`，按内核缺陷改写分诊并停下写「待裁定」。
5. 每项修后重跑对应用例，更新 `triage.yaml`。

## 验收（逐条贴真实 rc）

1. `memfd_create`：套件内直接验证返回有效 fd（`run_suite.py --only mm-mremap-dontunmap`；该例的 memfd 子测试不再 ENOENT）。
2. `/proc/iomem`：`cat /proc/iomem`（套件内）含 RAM region，`mm-pfnmap` 不再因该原因 SKIP；若客观不支持，给出证据与「SKIP 原因」更新，不得静默。
3. 非 root：`mm-on-fault-limit` 不再因 root 拒绝运行；至少一条用例在非 root uid 下完成并有 verdict。
4. `fcntl07`/`mlockall02` 不再因 `PATH`/`/etc/passwd` 判 `SUITE_ENV`（前者应有 verdict；后者若转为内核缺陷，须有 `die-no-vma` 签名与复评条件）。
5. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退 TMPFS 配置 ⇒ memfd 用例回 ENOENT；② 回退 uid 降权 ⇒ 用例回 root SKIP。
6. 不回归：`make check-linux-k6` rc=0；`check-config-pins` 更新的钉子与实况一致；`check-patch-tree` linux 段 0 problem；`check-component-changelog`/`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
7. `check_suite.py --latest` rc=0；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`（配置/必要内核代码）、`components/linux/changelog.md`、`tests/unit/linux/suite/**`（含镜像配置/用例配置/triage）、`tools/linux/suite/**`、`tests/unit/linux/check_config_pins.py` 的钉子（仅随配置变更同步）、本任务书。不改 `Makefile`/`spec/`/`.tao/contracts/`/其它组件。
3. 不改 K6 镜像与 `check-linux-k6` 判据；不改版本号；术语「bank = 寄存器组」。
4. 客观不支持的项：记录原因、证据、影响、复评条件；禁静默跳过。
5. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。

## 待裁定

无（若某项需改 `spec/Kaiwu` 的内存映射语义，停下写「待裁定」）。

## 完成区

**测试结果**：证据脚本 `run.sh`（full 模式）rc=0。kselftest 8 例 PASS6/SKIP1/FAIL1（pfnmap 停在 `/dev/mem`、futex 为既有 KERNEL_BUG，台账 2 行一致）；LTP 14/14 PASS、台账空；`make check-linux-k6` 82/82；`check-config-pins`/`check-patch-tree`（linux 0 problem）/`check-component-changelog`/`check-knowledge-refs`/`check_suite.py --latest` 均 rc=0。
**修改文件**：`components/linux/patches/arch/dadao/configs/defconfig.patch`、`.../kernel/setup.c.patch`、`components/linux/changelog.md`、`tests/unit/linux/suite/{suite.yaml,triage.yaml,README.md}`、`tests/unit/linux/suite/ltp/{suite.yaml,triage.yaml,README.md}`、`tools/linux/suite/{make_image.py,run_suite.py,suite_cases.py,suite_init.c}`、本任务书；证据脚本 = 运行期证据目录内 `run.sh`。
**验收结果**：① memfd：`mm-mremap-dontunmap` PASS（两臂全过），TMPFS=n 注入回 ENOENT；② `/proc/iomem` 套件内 `cat` 实测 `00000000-7fffffff : System RAM`（证据 `logs/iomem-probe.log`）；③ 非 root：`mm-on-fault-limit` PASS（supervisor `setuid 65534`），回退 `user: root` 即 SKIP；④ `ltp-fcntl07` PASS（PATH=用例目录:/bin）、`ltp-mlockall02` PASS（三 TPASS）；⑤ 注入 ①TMPFS 回退→FAIL/ENOENT、②uid 回退→SKIP，均 `cp`+md5 还原后回 PASS；⑥ K6 82/82、config pins rc=0、patch-tree linux 0、`make check` 红门 4 项（`check-interface`、`check-manifests-guard`、`check-milestones-fresh`、`check-temp-dirs`，逐行同基线；`check-case-ledger` 已随 master `3fa495a4` 重生成台账修复转绿、`ISS-m18-008` 已关闭、`check-syscall-abi` 已绿）；⑦ `check_suite --latest` rc=0。
**mlockall02 判定**：补 `/etc/passwd` 后三子例 TPASS，`die-no-vma va=0x10` 不再出现；该签名是 `getpwnam("nobody")` 返回 NULL 的**用户态 NULL 解引用**，内核 SIGSEGV 投递正确，**不是内核缺陷**，无需另立内核任务。
**新发现/坑**：TMPFS 的 `select MEMFD_CREATE` 是单向的，回退 TMPFS=n 不会自动关 MEMFD；只改 `.config` 时 `run_suite` 因 `kernel-image.json` 命中而跳过内核重建。pfnmap 加 `/dev/mem` 节点后测试 mmap 物理区会把 guest 卡在用户异步投递循环（无进展），本端口 devmem mmap 路径不可用。
**遗留问题**：`mm-pfnmap` 仍 SUITE_ENV（`/dev/mem` + devmem 支持）；一次 `HOST_TIMEOUT` 属 `ISS-m18-005` 族整机 flake，已按 ≤3 重跑取两轮 PASS。

## 审阅记录

### 第 1 轮 engineer 自审
逐行审查 `suite_init.c` / `make_image.py` / `suite_cases.py` / `run_suite.py` / 两个补丁 / 台账与证据脚本。判决：**无未修 finding**。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `backup()` 的 `local f=$1 b="$(...$f...)"` 在同一命令里展开，`$f` 未赋值（`set -u` 报 unbound），所有备份写到同一个 `.bak`，还原会把 suite.yaml 抄进 defconfig/run_suite | ✅已修 | 拆成两条 `local` 赋值 | 两次 `run.sh --skip-full`：三文件 md5 各自还原 PASS |
| F2 `nobody` 子进程 `chdir("/tmp")` 后 `/cases` 的相对 argv 找不到（`execv(tests/...)=ENOENT`） | ✅已修 | 去掉 chdir；`absolute_path()` 把 argv[0] 统一成 `/tests/...` 再 exec | `mm-on-fault-limit` PASS；注入 root 回 SKIP |
| F3 证据脚本在 suite 构建前查 `.config`；`check-patch-tree` 的 `^linux: ` 误匹配汇总行 | ✅已修 | 配置检查移到套件跑完后；只匹配 `linux: assertion/problem` | full run PASS，linux 段判 none |
| F4 TMPFS 注入只改 `.config` 时 `run_suite` 命中 `kernel-image.json` 跳过重建，注入仍 PASS | ✅已修 | 注入同时删 `.config` 与 `kernel-image.json`（回退 defconfig 源码行 + runner 常量） | 注入→FAIL/ENOENT，还原→PASS |
| F5 整机 flake（`HOST_TIMEOUT`，无 die）被当成固定 FAIL | ✅已修 | 两条注入的 FAIL/PASS 期望都做 ≤3 次重试并记录 | 首次 uid 注入 HOST_TIMEOUT，重试后 SKIP；还原 PASS |
| F6 `suite_init` 新增 user 列后 token 上限/argv 下标 | ✅已修 | `tok[MAX_ARGS+4]`、`split(...MAX_ARGS+3)`、argv 从 i=3 起 | 14 例 LTP + 8 例 kselftest 全跑通 |
| F7 补丁改动后 `check-index-blobs` 的 new-hash 过期 | ✅已修 | 按 `git hash-object` 更新两处 `index ...` | `make check-index-blobs` rc=0 |

审查确认：`user` 只允许 root/nobody；`nobody` 固定 65534:65534 与镜像 PASSWD 一致；未改 K6 判据/镜像代码；未用 git 还原注入；`/dev/mem` 不留在镜像（避免 pfnmap 卡死）。

### 第 1 轮 reviewer 验收
（全部命令在分支 worktree 以相对路径本人执行；证据一律指运行期证据目录内的 `run.sh` 及其 `logs/`）

**重跑记录（以本人输出/退出码为准）**
- 范围：`git diff --stat master...HEAD` = **14 文件**，与完成区「修改文件」逐项一致；无 Makefile/spec/契约/其它组件/`components/ltp/**`；`git grep` 冲突标记 0；`git status --porcelain -uall` 空；`git ls-remote --heads origin` 无本分支（未 push）。
- `bash 运行期证据目录内的 run.sh`（full）**rc=1**，唯一 FAIL 见 F1；其余全 PASS：config-pins rc=0（**检查 93 项**）、patch-tree rc=0（464 patches OK，linux/ltp 段 0 problem）、changelog rc=0、knowledge-refs rc=0、`check_suite.py --latest` rc=0（24/24）、`check-linux-k6` **82/82**。
- 四项实测（本人该轮 results/console）：`ok 2 mremap_dontunmap_simple_shmem`（memfd 臂 PASS）；`mm-pfnmap` = `1..0 # SKIP Cannot open '/dev/mem'`，而 `pfnmap.c:find_ram_target()` 只有在 `/proc/iomem` 命中 `System RAM` 行才会走到 `open()` ⇒ 套件内已导出 System RAM，且日志无 `Cannot find ram target`；`SUITE CASE USER mm-on-fault-limit user=nobody` + `ok 1 The map failed respecting mlock limits`；LTP 全量 **14/14 PASS**（`check_suite.py --suite ltp --latest` rc=0、20/20，台账 `rows: []` 与 `{}` 对账）。
- 注入：`run.sh` 内两路（① TMPFS 回退 → FAIL + `memfd_create:No such file or directory` → `cp`+md5 还原 → PASS；② uid 回退 → SKIP + `must be run from a normal user` → 还原 → PASS，各文件 md5 逐项相等）；另**本人手工独立注入** `user: nobody→root`：`verdicts: SKIP=1`、console `# SKIP The test must be run from a normal user`，`cp` 还原 md5 `68d3…eede` 相同 → `verdicts: PASS=1`。
- triage：4 项已转 PASS 的行删除并写入 Resolved 注释；`mm-pfnmap` 保留 SUITE_ENV/SKIP，写明 `/dev/mem` 缺口、试加节点后 guest 卡进用户异步投递循环的证据与复评条件；无静默转 PASS。
- 约束：未动 Makefile/spec/契约/其它组件/K6 判据/版本号；还原全程 `cp`+md5（无 checkout/restore/stash）；状态 `待验收`、完成区 8 行、自审 14 行。

**check-case-ledger 归属（独立验证）**：主工作树 `make check-case-ledger` rc=2 与分支 rc=2 输出 `diff` **IDENTICAL**（缺 8/多 8 行，全在 `tests/inst/11-cfx/escape_ciii_cfx.S`）；两树 `tests/case-ledger.tsv`、`escape_ciii_cfx.S` md5 各自相同；`348cb004` 改 `.S` 且 `--name-only` 不含 ledger ⇒ **master 自身红，非 018 引入**（ISS-m18-008 已登记）。主仓全量 `make check` 未跑成：主仓门锁被他会话持有（`gate-lock: WAIT … held by holder unknown`，900 s 超时终止、未持锁、无残留），master 侧全量红门集合改采信上述逐行 diff。

**F1（阻断）**：证据脚本 full 在 HEAD **rc=1**，唯一 FAIL `make check: no new red gate vs baseline | 实际=check-case-ledger`——运行期证据目录内的 `baseline-gates.txt` 记于合并 master 之前、缺该门；完成区「run.sh（full）rc=0」「红门仅 4 项且逐行同基线」在当前 HEAD 不成立。**改法**：把 `check-case-ledger` 补入该基线清单，并按 AGENTS「基线红判据」在完成区记 KNOWN-RED + ISS-m18-008（红门行同步为 5 项），重跑 full `run.sh` 取 rc=0。

**判决：Needs Revision**（仅 F1；范围、四项功能、两路注入、门控、triage、硬约束均本人复核通过）。

### 第 2 轮 reviewer 验收
（命令均在分支 worktree 本人执行；证据指运行期证据目录内的 `run.sh`；主工作树对照另跑）

**F1 闭环**：`bash 运行期证据目录内的 run.sh`（full）**rc=0**、`run.sh: PASS`；`make check rc=2; gates=check-interface check-manifests-guard check-milestones-fresh check-temp-dirs`（**4 项**）；`comm` 与基线双向皆空（无新增红、无残留绿门行）；`make check-case-ledger` **rc=0**（`清单 == 现场派生`，现场 5797 条）。
**删行正当性**：转绿源于 master `3fa495a4` 重生成 `tests/case-ledger.tsv`（该 commit `--name-only` 含此文件）；分支未改台账/`escape_ciii_cfx.S`（与 master md5 逐字节同 `5d2c7c02…`/`f1645884…`），`git diff master...HEAD --name-only` 不含 `Makefile`/台账/检查脚本（判据未放宽）；`baseline-gates.txt` 现 4 行、无 `check-case-ledger`、无 `check-syscall-abi`。
**范围**：`git diff --stat master...HEAD` = **14 文件**；本轮新增提交 `0cff1e9f` 自身仅任务书 1 文件（`1 file changed, 25 insertions(+), 3 deletions(-)`），另一提交 `9dfb1666` 为 master 合并；无实现/判据/K6 改动。
**不回归（本人输出）**：`check-linux-k6` **82/82**；`check-config-pins` rc=0（**93 项**）；`check-patch-tree` rc=0（464 patches OK，linux 105 / ltp 1，0 problem）；changelog rc=0；knowledge-refs rc=0；`check_suite.py --latest` rc=0（24/24）。
**红门逐行比对**：分支 4 项（interface/manifests-guard/milestones-fresh/temp-dirs）**逐项都在 master 红名单内、同名**；master 同轮 `make check -k` rc=2 共 **7 项**，多出 `check-patch-tree`/`check-musl-freshness`/`check-run-artifacts`——均为主工作树并发状态（主树 `.work/source/{qemu,linux}` 被 ISS-520 在途改动、`build-musl-shared` 提示重建、659 条 `after-iss520` 等非法名日志），**非 018 引入**（018 只含套件/工具 14 文件，且分支比主树更绿）。结论：018 **无新增红**；主树这 3 项属他会话在途状态，不在本任务可改范围。
**更正第 1 轮记录**：`.dadao` 是指向主仓的符号链接、全项目共用一把 `gate.lock`；上轮「主仓门锁被他会话持有」不准确——`holder unknown（锁文件为空）`实为**我自己 `flock(1)` 外层持锁与 `gate_lock.py` 自锁**，本轮已按正确方式（不加外层 `flock`）重跑 master 门控；该更正不影响 F1 判定。
**状态核**：工作树 `git status --porcelain -uall` 空、注入三文件 md5 全还原（`68d3…`/`3c12…`/`9398…`）、`git ls-remote` 无本分支（未 push）、状态 `待验收`、完成区红门行 = 4 项与实测一致。

**判决：Accepted**（F1 已闭环；finding：主工作树 3 项并发态红见上，供 architect 收尾时知悉）。

### 第 2 轮 engineer 自审
F1 处置（只动运行期证据与本任务书；实现/判据未改）：
- **归属复核**：分支 `make check-case-ledger` rc=2；在本任务基线 master `18c86f67` 的临时 worktree 上同一命令 rc=2，两输出 `diff -u` **为空**（`logs/case-ledger-branch-vs-base18c-round2.diff`，0 行）；分支未改 `tests/case-ledger.tsv`/`escape_ciii_cfx.S`（`git diff 18c86f67 HEAD --` 为空）⇒ 基线红，归属 `348cb004` + `ISS-m18-008`。
- **现状差异（已记录）**：当前 master `b95d801f` 实测 `check-case-ledger` rc=0（`3fa495a4` 重生成台账）；本分支未含该提交，故本分支仍红。合并 master 后应删基线行。
- **改动**：运行期 `baseline-gates.txt` 增 `check-case-ledger` 及 KNOWN-RED/ISS-m18-008/归属/复评注释；`run.sh` 比较前过滤 `^#` 注释行。
- **复跑**：full `run.sh` **rc=0**，红门 5 项（`check-case-ledger`、`check-interface`、`check-manifests-guard`、`check-milestones-fresh`、`check-temp-dirs`），`check-syscall-abi` 已绿；`check-case-ledger` 重跑 rc=2 输出留档。
判决：F1 已修（按基线红判据登记，未放宽容差）。
