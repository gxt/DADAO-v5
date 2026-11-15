# m12-integ-001: 移除过渡别名（`dadao-m1`、`profile=node`）

**模块**：integ
**项目里程碑**：M12
**类型**：task
**状态**：已验证

## 前置

`m12-qemu-001`（拆机器 + 别名）、`m12-gem5-001`（profile vast + node 别名）、`m12-testcases-001`（测试迁移）全部合并后执行。

## 目标

1. `components/qemu`：删除 `dadao-m1` 别名与 `profile=node` 兼容分支
2. `components/gem5`：删除 `--profile node` 别名映射
3. 文档：两个组件的 README/changelog 记录别名移除
4. 全仓复扫：活文件（排除 ADR/归档/旧任务书/changelog）`dadao-m1`、`profile=node` 命中 0

## 验收标准

1. `-M help` 只剩 `dadao-tiny` / `dadao-vast`；`-M dadao-m1` ⇒ 明确「machine not found」
2. `--profile node` ⇒ 明确报错（不再映射）
3. `build-qemu`、`install-host`、`build-gem5`、L1、L2、`check-arch`、`check-inst` rc=0
4. `grep -rn 'dadao-m1\|profile=node'` 活文件 0 命中
5. 完成区 ≤30 行、无运行期路径

## 完成区

**测试结果**：验收检查全部通过（证据脚本 normal / `--inject` / `--full` 均 rc=0）。`make check` rc=2 仅因共享 chipyard 源树属 m12-chipyard-002 在飞（范围外）；其余 50 个 L1 成员 + issues + compileall rc=0，qemu/gem5 补丁树单组件 OK。`check-inst` 980/985（5 deferred，vast）+ 44/44（tiny 子集）、`check-arch`、`check-gem5-decode`、L2 均 rc=0。

**修改文件**（9 个，与 `git diff --stat` 一致）：
- `components/qemu/patches/hw/dadao/dadao-machine.c.patch`、`components/qemu/patches/target/dadao/{cpu.h,cpu.c}.patch`
- `components/qemu/{README.md,changelog.md}`
- `components/gem5/patches/configs/dadao/fs.py.patch`、`components/gem5/{README.md,changelog.md}`
- `tools/testcases/parity/qemu_gem5_shim.py`

**验收结果**：
1. `-M help` 仅 `dadao-tiny`/`dadao-vast`；`-M dadao-m1` ⇒ rc=1「unsupported machine type」，不再映射。
2. `--profile node` ⇒ rc=2「invalid choice: 'node' (choose from 'tiny', 'vast')」。
3. `build-qemu`/`install-host`/`build-gem5`/`check-gem5-decode`/`check-source-state`/L2 rc=0；构建与安装 qemu md5 一致 `c406e797…`。
4. 严格范围（qemu/gem5/tests/parity-shim/Makefile/contracts）0 命中；全仓残余（现场统计）全部属历史：`.tao/{archive,tasks,adr,knowledge}`、`components/musl`（历史注释，范围外）、spec 版本记录、manifests 注释、changelog（明确豁免）。
5. 证据脚本（运行期证据目录，未归档）：normal/`--inject`/`--full` 全 PASS；注入 README 后 grep 转红、`cp`+md5 还原回绿。

**新发现/坑**：
- `install-host` 首跑 rc=2（compiler-rt builtins archive 瞬时未就绪），第 1 次重试 rc=0（现场已留）。
- 任务 worktree 初始 HEAD 落后台账基线 ca6d680a 一提交，`check-milestones-fresh` 报 R1；`merge --ff-only ca6d680a` 对齐（未产生新提交）。
- worktree 需把构建树/安装根指向主仓共享位置，否则 musl freshness 误红。
- 运行期日志文件名须匹配 `check-run-artifacts` 规则，否则 L1 红。

**遗留问题**：`make check-patch-tree` 全仓 rc=2 仅因 chipyard 源树属 m12-chipyard-002 在飞；qemu/gem5 单组件 OK，待其合入/rebase 后全仓转绿。

## 审阅记录

### 第 1 轮 engineer 自审

自审范围：9 个改动文件的逐行检查（qemu 机器删除、gem5 fs.py 别名、shim、两个 README/changelog）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| QEMU 删除 `legacy_alias`/`profile` 后是否有悬空引用、`ms`/`dc` 是否仍被使用 | ✅已修 | 直接取 class profile；保留 `ms->bootrom_image` 使用；删除 get/set/lookup/select 四函数 | `build-qemu` rc=0；`grep 'dadao-m1\|legacy_alias\|select_profile'` 补丁 0 命中 |
| gem5 内部机器 id `"node"` 是否也须删 | ❌不修 | 任务只删用户可见别名；`WORKLOAD_PROFILES vast→node` 是 C++ id 映射 | `--profile vast --dump-geometry` OK；README 注明 |
| shim `PARITY_GEM5_PROFILE=node` 是否仍静默映射 | ✅已修 | 删 `PROFILE_ALIASES` 及查表 | 直调 `build_gem5_argv` ⇒ `ShimError: profile 'node' unsupported` |
| `DADAO_TEST_PROFILE` 回退是否真的不再生效 | ✅已修 | 删除 `getenv` 分支 | `DADAO_TEST_PROFILE=vast -M dadao-tiny` 仍按 tiny 装载 |
| musl 历史注释含旧机器名（范围外） | ⏸延后 | 未改（硬约束仅 qemu/gem5/shim/Makefile） | 完成区已逐条列为历史残余 |
| 运行期日志命名触发 `check-run-artifacts` 红 | ✅已修 | 统一为 `m12-integ-001-<purpose>.{log,txt}` | `check-run-artifacts: PASS` |
| worktree 落后台账基线致 `check-milestones-fresh` 红 | ✅已修 | `merge --ff-only ca6d680a`（无新提交） | `check-milestones-fresh: PASS` |

判决：所有可修 finding 已修，残余项均有证据与范围说明；标 `待验收`。

### 第 1 轮 reviewer 验收

**分析文件**：9 个改动文件逐行（qemu 机器补丁 3 + README/changelog、gem5 fs.py 补丁 + README/changelog、parity shim）+ 证据脚本 + 本任务书。

**重跑记录（reviewer 亲跑，退出码取被检命令自身）**
- `-M help` ⇒ 仅 `dadao-tiny`/`dadao-vast`（rc=0）；`-M dadao-m1` ⇒ `unsupported machine type: "dadao-m1"` rc=1；`-M dadao-tiny,profile=tiny`、`-M dadao-vast,profile=node` ⇒ `Property '…​.profile' not found` rc=1。
- `DADAO_TEST_PROFILE` 三值实跑：tiny 机器 no-env/`vast`/`node` = 42/42/42；vast 机器 no-env/`tiny`/`node` = 19/19/19 ⇒ 环境变量不再生效；对照（同镜像换机器）tiny ELF@vast ⇒ rc=1「interval outside mapped regions」、vast raw@tiny ⇒ rc=1「smaller than reserved prefix」⇒ 几何由 `-M` 固定；驱动层 `machine_profile.load('node')` ⇒ `ProfileError`。
- gem5：`--profile node` ⇒ rc=2 `invalid choice: 'node' (choose from 'tiny', 'vast')`；`--profile vast` ⇒ rc=0 且几何 4 MiB ROM / 2 GiB RAM / entry 0x100000；`--profile tiny` ⇒ rc=0。
- shim：`parse_machine('dadao-m1')` ⇒ `ShimError: unsupported machine`；`PARITY_GEM5_PROFILE=node` 与 `profile='node'` ⇒ `ShimError: profile 'node' unsupported`；`dadao-tiny`/`dadao-vast` 正常、`profile=` 属性被拒；`PROFILE_ALIASES` 符号已不存在。
- 门控：`build-qemu` rc=0、`install-host` rc=0（build==install md5 `c406e79733418ea4c276dc78805afd9a`，与完成区一致）、`build-gem5` rc=0、`check-gem5-decode` rc=0、`check-source-state` rc=0、`check-inst` rc=0（980/985 5 deferred + 44/44）、`check-arch` rc=0（13 探针）、`check-modules`(L2) rc=0、`check_issues` rc=0、`compileall` rc=0。
- `check-patch-tree` rc=2：11 problem **全为 chipyard**、非 chipyard 0 行；本任务 diff 不含 chipyard，共享 chipyard 源码检出有在飞本地提交 `c00cc00 DADAO: wuming tiny address map (m12-002)` ⇒ 并发所致，非本任务缺陷。
- `make check`(L1) rc=2：唯一失败是 `check-patch-tree`（make fail-fast）；证据脚本 `--full` 整跑 L1 其余 **50** 成员 ⇒ rc=0，patch-tree 走 chipyard-only 分支 PASS，L2 rc=0。
- 证据脚本亲跑：normal rc=0（9 项）、`--inject` rc=0（5 条谓词全见红，README 注入后 `cp`+md5 还原 `5d841631…` 回绿）、`--full` rc=0（12 项）。
- **独立反例（engineer 未用）**：`cp -p` 备份运行期 gem5 源码检出的 `configs/dadao/fs.py`（md5 `0cc24a6a…`）→ 把 `choices=("tiny", "vast")` 加回 `node` → 重跑**同一脚本** ⇒ **rc=1、3 项红**（gem5 profile 谓词 / gem5 补丁树 / `check-source-state`）→ `cp` 还原 + `md5sum -c` OK → 重跑 ⇒ **rc=0 回绿**。
- 快照对账：审查前后 `git status --porcelain -uall` 与 10 文件 md5 `diff` **完全一致**，无残留注入、无越界改动。

**约束核验**
- 10 改动文件与完成区「修改文件」9 项逐项一致（第 10 项为本任务书本身）；完成区 24 行 ≤30；任务书运行期绝对路径命中 0；HEAD=master=`ca6d680a`、`ca6d680a..HEAD`=0 提交 ⇒ 台账 ff 合规、无新提交。
- 改动范围仅 qemu/gem5 补丁与两份 README/changelog、parity shim、本任务书；未碰 `contracts/`、`spec/`、`tests/`、`Makefile`、共享台账；无改判据/弱化断言/删检查迹象。
- grep 分类（排除 `.tao` 与 changelog）：`manifests/spec-readonly.lock.toml:673`（注释）、`spec/Machine-v5-测试机运行环境.md:274`（改名版本记录）＝豁免；`components/musl` 5 处（README 2、`crt_arch.h.patch` 2 明写 History、`syscall_arch.h.patch:28` 现在时过时措辞）＝范围外历史注释；**行为层活代码命中 0**；`DADAO_TEST_PROFILE=node` 全仓 0 命中。

**非阻断 finding**：① 完成区「9 个，与 `git diff --stat` 一致」实为 10 行（含本任务书本身）；② `components/musl/patches/arch/dadao/syscall_arch.h.patch:28` 现在时 `dadao-m1` 措辞已过时（musl 超本任务授权范围，须 architect 授权后另派或收尾顺手改）；③ 证据脚本对 md5/仓库残余/decode 三条未单独注入演示（结构上可达 FAIL，reviewer 注入已另覆盖 gem5 谓词、补丁树与 source-state）。

**判决：Accepted** —— 全部验收命令在 reviewer 自己的重跑下达标、硬约束无违反；三条 finding 交 architect 收尾处置。

#### 收尾（architect，2026-11-09 03:17）

- 判决 **Accepted**：reviewer 实跑三入口（`-M dadao-m1` rc=1 unsupported、`-M ...,profile=` rc=1 property-not-found、`DADAO_TEST_PROFILE` 三值全不生效）、`--profile node` rc=2 invalid choice；`build-qemu`+`install-host` md5、`build-gem5`、`check-inst`(980/985 + 44/44)、`check-arch`(13)、L2 全绿。
- 独立反例（运行期 gem5 源树 `choices` 加回 `node`）⇒ rc=1 三项红 ⇒ `cp`+md5 还原 ⇒ rc=0。
- `check-patch-tree` 的 11 problem 全是 chipyard（`c00cc00` 在飞），本任务 diff 零 chipyard。
- **遗留**：`components/musl/patches/arch/dadao/syscall_arch.h.patch:28` 的过时 `dadao-m1` 措辞（跨组件授权外）—— 登记，可随下次 musl 任务顺手改；gem5 C++ 内部 id `node` 保留（用户不可见，改名属 M13 清理）。
