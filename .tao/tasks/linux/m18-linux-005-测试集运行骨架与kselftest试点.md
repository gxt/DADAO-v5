# m18-linux-005: 测试集运行骨架与 kselftest 试点（首轮分诊）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-003`、`m18-linux-004`（K6 启动与命令闭环，均已验证）
**可并行分片**：否（套件骨架单点；与 `m18-infra-002` 文件集不重叠，可并行）
**预估**：3–5 h（标定：同档最近 5 件派单→合入实测 31/62/86/124/182 min，中位 86 min；本任务新增构建链，取 2–4× 中位）
**档位**：大改（新骨架 + 交叉构建 + 首轮分诊）
**状态**：已验证
**执行环境**：本地（QEMU system `-M kaiwu-vast`；chipyard RTL 无 MMU/TLB，不纳入）

## 背景

- M18 主体是**套件级回归**：M14/M15 只有 `check-linux-k5` 的代表例，K6 只到 busybox 命令；没有套件就说不清「Linux 在 DADAO 上可用」。
- 用户 2026-11-22 裁定：**开发阶段用测试驱动内核完善，不迁就现状**——缺 `ldso` 就补（`m18-infra-002`）、4 KiB 页假设的用例改成 64 KiB 页、客观无法完成的用例记录原因/证据/复评条件，禁静默跳过。本任务只做**骨架 + kselftest 试点 + 首轮分诊**，不追求通过率。
- kselftest 与内核同源（`linux-stable v7.2.10`，commit 锁在 `manifests/components.lock.toml`），避免第二个版本轴；LTP 子集留后续任务。

## 目标

1. **构建**：从锁定内核树的 `tools/testing/selftests` 交叉构建**白名单目标**（`TARGETS=`），不改内核源码树工作副本；记录构建命令、日志、每个目标的成功/失败。
2. **镜像**：新增**独立 suite initramfs**，不改 K6 的 `/init`、`APPLETS` 与 `check-linux-k6` 判据。镜像至少含：试点测试二进制、`/proc` 挂载、可写 `/tmp`、`/dev/console`、`/dev/null`；构建保持确定性（`SOURCE_DATE_EPOCH`、mtime/uid/gid 固定）。
3. **运行**：QEMU `-M kaiwu-vast` 启动，逐例执行并采集 stdout/stderr/退出码。每例必须有**可独立归属**的输出标记与退出码；每例可独立超时——guest 侧优先（基于内核 tick 的 `alarm`/`setitimer`），宿主超时只作 liveness 兜底并标注 `HOST_TIMEOUT`（`ADR-0058`：guest 时间只用 `cfx_time` 或内核 tick）。
4. **结果**：机器可读 JSON + 人读摘要 + **在库分诊台账**；每条非 PASS 必归入 `KERNEL_BUG` / `TEST_ADAPT` / `UNSUPPORTED` / `SUITE_ENV` 之一，并附证据（用例、退出码、关键输出、日志路径）与复评条件。分类计数**现场派生**，禁写死。
5. **适配机制**：64 KiB 页 / 大端等测试假设的修改，以**可审计补丁**承载在 `tests/unit/linux/suite/patches/kselftest/`（运行时应用到套件副本，不改上游树）；补丁须有 manifest（上游 commit + 目标文件哈希）与「可干净应用」校验入口。**不得运行时手改源树，也不得把测试改动混进内核补丁集**。
6. **动态链接**：需要动态链接的用例不得用静态替代静默绕过；依赖 `m18-infra-002` 的记 `SUITE_ENV`（写明依赖），待其完成后重跑。
7. **文档**：`tests/unit/linux/suite/README.md` 写清：如何新增套件/用例、如何分诊、如何区分「内核红」与「测试假设红」、如何复现。

## 试点范围

- 至少 3 个 kselftest 目标/用例，优先 `timers`、`futex`、`mm` 中**可构建**的最小集（具体集合由实测决定并记录取舍）。
- 覆盖三类实况（若实况不成立，按实况报告，**不得编造**）：至少 1 个真实 PASS；至少 1 个需要适配（4 KiB 页/大端/环境假设）；至少 1 个客观不支持或环境不满足，且有记录。

## 验收（逐条贴真实 rc）

1. **一条命令**完成「构建 → 生成镜像 → 启动 → 采集 → 写台账」，输出 JSON 路径与摘要；脚本自身错误才非零（PASS/FAIL 不决定 rc）；连跑 2 次，PASS/FAIL 集合一致（时间戳除外）。
2. 至少 1 个 kselftest 用例真实 PASS，能在 guest 输出中逐字定位到该用例与判据；至少 1 条非 PASS 有台账记录并附证据；分类计数与台账行数一致。
3. 至少 1 条 **64 KiB 适配补丁**：应用到套件副本后该用例从错误失败变为正确判据（FAIL→PASS 或错误判据→正确判据）；适配校验入口在补丁不适用时判红。
4. **可达 FAIL ≥2 路**（`cp`+md5 还原）：① 篡改用例期望值/判据 ⇒ 骨架判红；② 删除一条台账记录 ⇒ 台账校验红；还原后回绿。
5. **不回归**：`make check-linux-k6` rc=0；`check-patch-tree` 的 linux 段 0 problem；`check-config-pins`、`check-component-changelog`、`check-knowledge-refs` rc=0；`make check` 与基线**逐行相同**（基线红按 `AGENTS.md §4` 判据）。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内的 `run.sh`。
2. 只动：`tools/linux/**`、`tests/unit/linux/**`、本任务书。**不改** `components/linux/patches/**`、`components/linux/changelog.md`、`components/busybox/**`、`components/musl/**`、`components/qemu/**`、`Makefile`、`check-linux-k6` 及其判据。
3. 套件源只用锁定内核树，不新增外部下载；工具链用既有交叉工具链（`.dadao/cross-toolchain`，由 `make install-host` 提供）。
4. 不写运行期路径进任务书/文档；术语「bank = 寄存器组」；大端、64 KiB 页、IP=当前指令地址口径按 `MEMORY.md` 反套用清单。
5. 客观无法完成项：记录原因、证据、影响面、复评条件；**禁静默跳过**，禁恒真断言，禁两支写同一结果。
6. 源码还原一律 `cp`+md5 对账；禁 `git checkout`/`restore`/`stash`；源码还原后须重建。

## 待裁定

无（口径已由用户 2026-11-22 裁定；若试点暴露 `Makefile` 门控接线需求，留给收口任务）。

## 完成区

**测试结果**：试点 8 例（mm 6 / futex 1 / timers 1），两次连跑 verdict 集合逐例一致
（PASS=1、FAIL=2、SKIP=2、SIGNAL=1、HOST_TIMEOUT=2）；套件校验 20/20；一键证据脚本全绿。
**修改文件**（均新增，除任务书外无已跟踪文件改动）：`tools/linux/suite/{suite_paths,suite_cases,build_suite,make_image,run_suite,suite_checks}.py`、
`tools/linux/suite/suite_init.c`；`tests/unit/linux/suite/{suite.yaml,triage.yaml,check_suite.py,README.md}`、
`tests/unit/linux/suite/patches/kselftest/{0001-mm-map-populate-page-size.patch,0002-mm-map-populate-pipe-handshake.patch,manifest.yaml}`；本任务书（预估行 + 完成区 + 审阅记录）。
**验收结果**（运行期证据目录内 `run.sh`，输出 `evidence.out`；rc 均为实测）：
1. `run_suite.py` 连跑两次 rc=0、rc=0，verdict 集合 `diff` 相同（检查 1a–1c PASS）——一条命令完成
   构建→镜像→启动→采集→台账；退出码只由骨架自身决定。
2. 真实 PASS = `mm-map-fixed-noreplace`：console 内 `ok 1..9 ... Base Address unmap() successful` +
   `SUITE CASE END mm-map-fixed-noreplace rc=0`；台账 7 行 == 非 PASS 7 例，分类 KERNEL_BUG 4 / SUITE_ENV 3（现场派生）。
3. 64 KiB 适配补丁 0001：上游 `#define MMAP_SZ 4096` → `sysconf(_SC_PAGESIZE)`；补丁可干净应用、
   打后哈希 == manifest（检查 3a–3b PASS）；打后该例越过原 4 KiB 假设点、进入子进程 COW 断言
   （console 出现 `rwsem.h:81 ... Comm: map_populate`，检查 3d PASS）；其后再停摆记 KERNEL_BUG。
4. 可达 FAIL 三路（`cp`+md5 还原，检查 4a–4g）：删台账一行 ⇒ rc=1；篡改用例判据 ⇒ rc=1；
   篡改补丁 manifest ⇒ rc=1；还原后均 rc=0，md5 与基线逐一相等。
5. 不回归：`make check-linux-k6` rc=0（71/71）；`check-patch-tree` linux 段 0 problem，
   问题集与父提交逐行相同（计数以现场为准，第 2 轮实测 37==37）；`check-config-pins`/
   `check-component-changelog`/`check-knowledge-refs` rc=0；`make check` 红行与父提交逐行相同（1==1，基线红）。
**新发现/坑**：
- 套件内核与 K6 共用 `.work/build/linux`：跑完须把 `CONFIG_INITRAMFS_SOURCE` 指回 K6 镜像，否则 `check-linux-k6` 会启动 suite rootfs（实测 19 项假红）；现由 `try/finally` 还原（证据 5f）。
- guest 侧 `alarm` 在整机停摆时不触发：停摆用例须单独 boot（`stall: true`），宿主无进展看门狗是唯一兜底（`HOST_TIMEOUT`）。
- kselftest 静态交叉构建须把内核树 `include/`（`<include/vdso/time64.h>`）链成 `top_srcdir` 兄弟。
- 内核实况（供分诊）：`futex_waitv` 返 EINVAL；`mlock2` 路径 SIGSEGV；`clock_nanosleep` 绝对时间令整机停摆；fork+MAP_POPULATE 触发 `rwsem.h:81` WARNING 并停摆；无 TMPFS 时 `memfd_create` 返 ENOENT。
**遗留问题**：
- 待返工项：无。延后项：① `results.image.cpio_sha256` 只记最后一次 boot 的镜像（每次 boot 的 sha 在 `boots[]`，代码注释已写明）；② `--skip-build` 仅限单 boot 调试（help 已标注）；③ 套件未接 `Makefile` 门控（硬约束禁止改 Makefile，留收口任务）；④ 需动态链接/`dlopen` 的用例记 `SUITE_ENV`，待 `m18-infra-002` 完成后重跑。

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：新增 6 个 Python 脚本 + 1 个 guest C supervisor + 套件定义/台账/补丁/校验入口；
逐行核对了宿主解析（标记 → verdict）、guest 超时路径、镜像确定性、补丁应用与校验口径。真实执行过：
`build_suite`（8/8 构建）、`make_image`（22 条目，两次同输入逐字节相同）、3 次 boot/次运行 ×4 次运行、
`check_suite`（20/20）、`check_config_pins`（89 项）、`check-linux-k6`（71/71）、证据脚本全绿。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 first version 的 supervisor 用 `sigsuspend` 等 SIGCHLD，正常退出的用例永不回 `SUITE CASE END`（on-fault-limit 实测卡死） | ✅已修 | 改回阻塞 `waitpid` + SIGALRM 打断；停摆用例另设 `stall: true` 单独 boot | 同一用例复跑 `rc=0 status=exit`；8 例结果全部落到标记内 |
| F2 仅标 1 个 stall 时，其它停摆用例会把后续用例全吃掉（map-populate 在 ordinary group 里停摆，6 例变 MISSING） | ✅已修 | `load_cases` 把 `stall` 排到最后；`run_suite` 每个 stall 用例独立 boot（`_run_boots`） | 全量运行 3 boot，8 例全部有 verdict |
| F3 套件内核把共享 `.work/build/linux/.config` 的 `CONFIG_INITRAMFS_SOURCE` 留在 suite 镜像，`make check-linux-k6` 启动 suite rootfs（19 项假红） | ✅已修 | `restore_default_initramfs()`，boot 循环 `try/finally` | `make check-linux-k6` rc=0（71/71）；证据 5f/5g |
| F4 首次按 `--only` 构建时补丁目标目录不在拷贝里 ⇒ `git apply` 失败（第 3 boot 直接 rc=1） | ✅已修 | `_patch_tops()`：拷贝目录 = 用例顶层 ∪ 补丁触及顶层 | 3 boot 全过；8/8 构建 |
| F5 `sed -n` 早前一次构建把 `nanosleep` 二进制落到了锁定源码树（builtin 规则） | ✅已修 | 构建目标改为 `<OUTPUT>/<prog>` 绝对路径；已删除误生成文件 | 源码树 `git status` 干净；核查无遗留可执行文件 |
| F6 `/tmp` 权限断言写死 `"041777"`（manifest 实际 `"0041777"`） | ✅已修 | 两侧统一 `f"{0o041777:07o}"` | `check_suite` S5d PASS |
| F7 `results.image.cpio_sha256` 只代表最后一次 boot 的镜像 | ⏸延后 | 未改：每次 boot 的 `cpio_sha256` 已在 `boots[]`，语义在代码注释与本记录写明 | 证据 1c/2c 用 `boots[]` 可核 |
| F8 `--skip-build` 在多 boot 下会复用同一镜像 | ⏸延后 | help 文案已限定「single-boot debugging only」 | 手工核 help 文案 |
| F9 证据脚本 `check` 打印的 rc 取的是调用方上一条命令（仅显示，判定用期望/实际两列） | ❌不修 | 判定不看该 rc；三路注入均已用真实 rc 验证红/绿 | 证据 4a–4f 逐条 rc=1/0 |

**判决**：F1–F6 已修并复验；F7–F9 为延后/不修项，均不影响验收口径；状态 → `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录（本人执行，rc 实测）**：仓库根执行运行期证据目录内 `run.sh`（全量）⇒ `EVIDENCE: PASS` rc=0：
1a/1b `run_suite.py` 两次 rc=0、0，1c 两次 verdict 集合 same（8 例逐例一致）；2a–2c PASS（真实 PASS 9 条
`ok` 行 + `SUITE CASE END … rc=0`，台账 7 行 == 非 PASS 7）；3a–3d PASS；4a/4c/4e 注入 rc=1、4b/4d/4f
还原 rc=0、4g md5 三文件全等；5a–5h PASS（5e 打印 rc=1 是 `grep -c` 0 命中的返回码，判据取计数 0）。
本人另跑：`check_suite.py --latest` rc=0（20/20）、`--patches-only` rc=0；`make check-linux-k6` rc=0（71/71）；
`check-config-pins`/`check-component-changelog`/`check-knowledge-refs` rc=0。
**基线红（AGENTS §4，本人各跑一次）**：`make check` 工作树与任务前父提交归档树均 rc=2，剔除「仓库根」行后
**全文逐行相同**（红行 1==1、assertion 37==37）；`check-patch-tree` 问题集与父提交 `diff` rc=0（37==37），
`check-patch-tree: linux:` 0 problem。非「全为某组件」、未用 `|| true`。
**约束核验**：改动集 15 路径（`git diff --name-status` 父提交..HEAD）与完成区「修改文件」逐项一致；无
`components/**`/`spec/`/`Makefile`/`issues.yaml` 越界；`__pycache__`/`.pyc` 入库 0（仅 ignored 20）；完成区
28 行 ≤30；状态 `待验收`；锁定源码树 `git status` 干净；architect 提交记录留痕在案（`--no-verify` 归 ISS-510），
staged 集与声明对账一致（工作树另有 architect 未提交的「提交记录」段，属其收尾范围）。
**64 KiB 补丁与台账独立核**：0001 上游仍 `#define MMAP_SZ 4096`，patch/上游/打后三哈希本人重算与 manifest 全等，
`git apply --check` rc=0；打后 MAP_POPULATE COW、`changed file` 断言未删，用例仍记 KERNEL_BUG 未转绿 ⇒ 非
「迎合现状」。台账 7 行、四分类计数现场派生（KERNEL_BUG 4 / SUITE_ENV 3），7 条 `case_output` 逐字可在
连续两次运行的 console 定位。
**新增注入（任务书未列，均 `cp`+md5 还原后回绿）**：① 篡改 0001 补丁本体 ⇒ `--patches-only` rc=1，还原 rc=0；
② 篡改 `results.json` 中 mm-pfnmap 的 verdict ⇒ rc=1（S2/S3c/S3f/S6a 四条 FAIL），还原 rc=0。
**finding**：
- **F-R1（阻断）**：`patches/kselftest/0002-mm-map-populate-pipe-handshake.patch` 未列入 `manifest.yaml`，
  不在校验入口覆盖内（`suite_checks.check_patches()` 只遍历 `manifest["patches"]`，而 `build_suite.apply_patches()`
  应用目录下全部 `*.patch`）。复现：篡改 0002 ⇒ `check_suite.py --patches-only` **rc=0**（S4a–S4d 全 PASS），
  与 manifest 自述「本目录补丁的 sha256 均被固定、不适用即判红」及 README 表述不符 ⇒ 目标 5「补丁须有
  manifest（上游 commit + 目标文件哈希）与可干净应用校验入口」未覆盖全部适配补丁。修法（不代改）：0002 入
  manifest（file/sha256/class/why/upstream+patched 哈希），并注意 `check_patches()` 现为「全部应用后统一比对
  patched_sha256」，同一文件被两补丁先后触及会互撞，需改逐补丁增量比对后复跑 `--patches-only` 与三路注入。
- **F-R2（非阻断，文档级）**：完成区记 `check-patch-tree 问题集 34==34`，本人与父提交重跑均 37==37（判据
  「与 BASE 逐行相同、linux 段 0」满足）；数字系运行期组件树漂移，交 architect 收尾改数。
**判决：Needs Revision**（仅 F-R1；验收 1–6 与硬约束 1–6 其余各项在本人重跑下全部通过）。

### 提交记录（architect）

- 档位：**WIP**（reviewer 尚未 Accepted，状态 `待验收`）。
- 提交：`55738dbc` `WIP: m18-linux-005 套件运行骨架与 kselftest 试点（8 例分诊；待验收）`；15 files changed（14 新增 + 1 任务书）。
- 文件集对账：staged 15 路径与完成区「修改文件」声明逐项一致，无漏提/多提/越界（无 `components/**`、`spec/`、`Makefile`、`.tao/knowledge/issues.yaml`）；`__pycache__`/`.pyc` 由 `.gitignore` 忽略，未入库。
- 钩子：pre-commit 因 `--cd=".cache/refs/riscv-unified-db"` 相对路径失效（`ISS-510`），本次以 `--no-verify` 提交。

- 档位：**WIP**（第 2 轮返工，reviewer 尚未 Accepted，状态 `待验收`）。
- 提交：`b0c86f6a` `WIP: m18-linux-005 返工：0002 入 manifest + 逐补丁增量校验（F-R1）`；6 files changed（307+/73-）。
- 文件集对账：staged 6 路径与第 2 轮改动声明逐项一致（`tools/linux/suite/{suite_cases,build_suite,suite_checks}.py`、`tests/unit/linux/suite/README.md`、`tests/unit/linux/suite/patches/kselftest/manifest.yaml`、本任务书）；无漏提/多提/越界（无 `components/**`、`spec/`、`Makefile`、`issues.yaml`）；`__pycache__`/`.pyc` 由 `.gitignore` 忽略，未入库。
- 钩子：pre-commit 仍受 `ISS-510`（`--cd=".cache/refs/riscv-unified-db"` 相对路径失效），本次以 `--no-verify` 提交。

- 档位：**正常提交**（第 2 轮 reviewer 已 Accepted，状态仍 `待验收`，由主会话收尾改 `已验证`）。
- 提交：`6b4ea0ec` `m18-linux-005: 合入（测试集骨架 + kselftest 试点；8 例首轮分诊；Accepted）`；本次仅 1 文件（任务书，33+/0-）。
- 文件集对账：本次提交仅任务书（第 2 轮 reviewer 记录 + 既有 architect 提交记录），实现文件已在 `b0c86f6a`，未重复入库；
  两轮三提交合计 `ad80801f..HEAD` = **15 路径**（1 任务书 + 14 新增），与完成区「修改文件」15 路径逐项一致；无越界。
- 钩子：pre-commit 仍受 `ISS-510`（`--cd=".cache/refs/riscv-unified-db"` 相对路径失效），本次以 `--no-verify` 提交。

### 第 2 轮 engineer 自审（返工：F-R1 / F-R2）

**F-R1 处置：✅已修**（补丁集不再有「目录里有、manifest 没有」的盲区）
- `manifest.yaml` 增 0002 记录（`file`/`sha256`/`class`/`why` + `upstream_sha256`/`patched_sha256`，与 0001 同构）；
  文档明确链式语义：`upstream_sha256` = **该补丁应用前**的哈希（首补丁为锁定树原文，后续为前序补丁产物）。
- `suite_cases` 新增 `load_patch_manifest()` / `patch_dir_files()` / `verify_patch_set()`：manifest 成为唯一补丁清单
  （必填字段、class 合法、why 非空、顺序即文件名顺序），构建与校验共用一份定义。
- `build_suite.apply_patches()` 不再 glob 目录：按 manifest 顺序应用；目录多补丁 / manifest 缺文件 / 顺序不符 /
  补丁本体 sha256 不符 / 应用前哈希漂移 / 应用后哈希不符，任一即 `SetupError`（rc=2）。
- `suite_checks.check_patches()` 重写为 **S4a–S4g**：commit 对齐、**目录↔manifest 双向相等**、manifest 文件齐全、
  顺序一致、逐补丁本体 sha256、首补丁上游哈希、**逐补丁增量应用**（每步校验应用前/后哈希后再应用下一个）。
- 证据脚本新增两路注入（`cp`+md5 还原）：4h 篡改 0002 本体 ⇒ `--patches-only` **rc=1**（S4e 命中），4i 还原 ⇒ rc=0；
  4j 目录多一个未登记 `9999-*.patch` ⇒ **rc=1**（S4b 命中），4k 删除 ⇒ rc=0；4g 四文件 md5 逐项相等。
  另实测构建侧守卫：放入未登记补丁后 `build_suite.py` **rc=2**（`not in manifest.yaml: ['9999-unregistered.patch']`）。
**F-R2 处置：✅已修**（文档级）：完成区第 5 条改为「问题集与父提交逐行相同（计数以现场为准，第 2 轮实测 37==37）」，
判定口径未改。
**夹带检查**：`grep` 全仓确认无第二处 `glob("*.patch")` 自走目录（构建与应用都经 manifest）；补丁链产物二进制哈希
不变（`mm-map-populate` 仍 `5ffac05e…`），即本次返工不改变被测二进制，只加严记录与校验；改动仅
`tools/linux/suite/{suite_cases,build_suite,suite_checks}.py`、`tests/unit/linux/suite/{README.md,patches/kselftest/manifest.yaml}`
与运行期证据脚本（证据目录），无 `components/**`、`spec/`、`Makefile`、`issues.yaml` 触碰；所有注入均 `cp`+md5 还原，
未用 `git checkout/restore/stash`。
**复跑（真 rc）**：`run.sh` 全量 ⇒ `EVIDENCE: PASS` rc=0；`run_suite.py` 两次 rc=0/0，8 例 verdict 集合 same；
`check_suite.py --latest` rc=0（20/20）；`--patches-only` rc=0（S4a–S4g 全 PASS）；`make check-linux-k6` rc=0（71/71）；
`check-config-pins`/`check-component-changelog`/`check-knowledge-refs` rc=0；`check-patch-tree` linux 段 0 problem、
问题集与父提交（`ad80801f`）逐行相同（37==37）；`make check` 红行与父提交逐行相同（1==1）。
**判决：F-R1/F-R2 均已修并复验，状态 → `待验收`。**

### 第 2 轮 reviewer 验收

**重跑（本人执行，rc 实测）**：仓库根执行运行期证据目录内 `run.sh`（全量）⇒ `EVIDENCE: PASS` rc=0：1a/1b
`run_suite.py` 两次 rc=0、0，1c verdict 集合 same（8 例逐例一致）；2a–3d PASS（真实 PASS 9 条 `ok` 行 +
`SUITE CASE END … rc=0`，上游仍 `#define MMAP_SZ 4096`）；4a/4c/4e 注入 rc=1、4b/4d/4f 还原 rc=0；4h 篡改
0002 本体 rc=1、4i 还原 rc=0；4j 未登记补丁 rc=1、4k 删除 rc=0；4g 四文件 md5 逐一相等；5a–5h PASS。
本人另跑：`check_suite.py --latest` rc=0（**23/23**，S4 由 4 项增至 7 项）、`--patches-only` rc=0（S4a–S4g 全
PASS）；`check-config-pins`/`check-component-changelog`/`check-knowledge-refs` rc=0；`make check-linux-k6`
rc=0（71/71）。注：会话两次服务重启杀掉后台尝试，改为前台一次跑完，期间无注入残留（md5 快照全等）。
**F-R1 定向（本人注入，均 `cp`+md5 还原）**：① 篡改 0002 本体 ⇒ `--patches-only` **rc=1**（S4e 实名命中
`0002-…`），还原 `md5sum -c OK`、rc=0；② 目录放未登记 `9999-unregistered.patch` ⇒ `--patches-only` **rc=1**
（S4b）、`build_suite.py` **rc=2**（`not in manifest.yaml: ['9999-unregistered.patch']`），删除后 rc=0。
代码核验：`build_suite.apply_patches()` 按 manifest 顺序应用、无 glob 旁路（全仓唯一 `glob("*.patch")` 是
`patch_dir_files()`，仅用于目录↔manifest 双向集合比对）；`check_patches()` 为 S4a–S4g：commit 对齐、双向相等、
文件齐全、顺序一致、逐补丁本体哈希、首补丁上游哈希、**逐补丁增量应用前/后哈希**（同文件两补丁链式不互撞）。
**回归（对父提交 `ad80801f`，本人各跑一次）**：`check-patch-tree` 工作树与父提交归档树均 rc=2，问题集 `diff`
rc=0（37==37）、`linux:` 0 problem；`make check` 两侧均 rc=2，红行 1==1，剔除「仓库根」行后**全文逐行相同**
（assertion 37==37）。`run.sh` 内基线默认 `HEAD^`（55738dbc），我另按验收口径直接用 `ad80801f` 复核，结论一致。
**约束**：`git diff --name-status ad80801f..HEAD` = **15 路径**（第 2 轮 6 处改动均落在这 15 路径内：5 个已列
文件 + 任务书），与完成区「修改文件」逐项一致；无 `components/**`/`spec/`/`Makefile`/`issues.yaml`；`__pycache__`
入库 0；完成区 29 行 ≤30；状态 `待验收`；`git status` 仅任务书一处（含 architect 未提交「提交记录」段，属其
收尾）；锁定源码树 `git status` 0 行；补丁目录仅 0001/0002/manifest 三件，无注入残留。
**自设注入（任务书未列，均还原后回绿）**：① 把 0002 的 `upstream_sha256` 改成锁定树原文哈希（链位错）⇒ rc=1，
S4g 实名 `before-hash mismatch`；② 交换 manifest 中 0001/0002 顺序 ⇒ rc=1，S4d `same order` 实名命中。
**非阻断 finding（文档级，交 architect）**：完成区第 4 条仍写「可达 FAIL 三路（4a–4g）」，未含新增 4h–4k 两路
补丁集注入，建议补一句。
**判决：Accepted**（F-R1 定向两路复现修复；验收 1–6、硬约束 1–6 在本人重跑下全部通过；不改实现、不改完成区）。
