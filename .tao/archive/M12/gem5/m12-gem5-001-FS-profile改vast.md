# m12-gem5-001: gem5 FS profile `node` → `vast`

**模块**：gem5
**项目里程碑**：M12
**类型**：task
**状态**：已验证

## 背景

`configs/dadao/fs.py` 现用 `--profile {tiny,node}`，并有多处 `"node"` / `args.profile == "node"` 判断。用户裁定 profile 概念改名 `Tiny`/`Vast`。

## 目标

1. `components/gem5/patches/configs/dadao/fs.py.patch`：
   - profile 键与 choices 改为 `tiny` / `vast`，注释与帮助文本同步
   - **过渡期同时接受 `node`**（映射到 `vast` 并打印 deprecated 提示），保证测试迁移期间 L1 绿
2. `components/gem5/{README,changelog}.md` 记录改名与别名移除计划
3. 冒烟：`fs.py --profile vast` 用 Vast bootrom/镜像跑通一次；`--profile node` 输出 deprecated 但行为一致

## 验收标准

1. `--profile vast` 与 `--profile node` 同一镜像/参数下退出码与输出一致
2. `build-gem5`、`check-gem5-decode`、`check-source-state`、`check-patch-tree`、L1、L2 rc=0（测试尚未迁移，靠 `node` 别名不红）
3. 完成区 ≤30 行、无运行期路径

## 说明

- 别名的最终移除在 `m12-integ-001`（与 qemu 的 `dadao-m1` 别名一起删）
- 不改 `configs/dadao/se.py`（SE 无 profile）

## 完成区

**测试结果**：证据脚本 `.work/evidence/<任务ID>/run.sh` **12/12 PASS**（rc=0，含注入→FAIL→`cp`+md5 还原→回绿）；`build-gem5` rc=0（`build-gem5: PASS`）；`check-gem5-decode` rc=0（264/264 + 388/388 + 28/28 + 2/2）；`check-source-state` rc=0（gem5 `clean=True`、base+1）；`check-patch-tree` rc=0（7 组件 306 补丁）；L2 `make check-modules` rc=0；L1 `make -k check` rc=2，仅 `check-milestones-fresh` 与 `check-temp-dirs` 红（见遗留问题 1），其余全绿。

**修改文件**：
- `components/gem5/patches/configs/dadao/fs.py.patch`（`make_patch.py gem5` 重导出：1 written / 96 unchanged）
- `components/gem5/README.md`（Vast 章标题、CLI、新增「profile 命名」段含别名移除计划）
- `components/gem5/changelog.md`（新增 `## M12` 节 + 本任务条目）
- `.tao/tasks/gem5/m12-gem5-001-FS-profile改vast.md`（状态 + 完成区 + 审阅记录）

**验收结果**：
- ① `--profile vast` vs `--profile node`：同一 Vast BootROM（md5 `eb75b865…`）+ `m5_semi_exit` 镜像，**rc=19 == 19**，stdout payload 逐字节一致；`node` 的 stderr 恰多 1 行 `fs.py: --profile node is deprecated, use --profile vast`。
- `--profile vast --dump-geometry`：17 键（`bootrom_size=0x400000`、`ram_base=0x0`），`--profile node` 输出与之逐字节一致；`--profile tiny` 仍 9 键（`sram_base=0xffffff000000`）不回归；`--profile bogus` rc=2（choices 仍生效）。
- 注入自检：`PROFILE_ALIASES` 改为 `node→tiny` ⇒ 别名比对 FAIL；还原后 md5 与注入前一致、比对回绿。

**新发现/坑**：① `fs.py` 把 `profile` 直传 C++ `DadaoFsWorkload`，而 C++ 按 `tiny|node` 校验（`fs_workload.cc` 的 `fatal_if`）⇒ 只改 CLI 名会在运行期 fatal，本次用 `WORKLOAD_PROFILES` 显式映射。② 测试侧仍硬编码 `node`：`qemu_gem5_shim.py` 白名单 `("tiny","node")`（`--profile vast` 会被 shim 拒绝）与 `machine-profiles.yaml` 键名 ⇒ `m12-testcases-001` 迁移清单须含该 shim。③ 任务 worktree 无 `.dadao` 安装根，但 gate lock 会先在仓库根建 `.dadao/` 目录 ⇒ 整目录 symlink 失效，须逐个链接安装子目录（cross-toolchain / host-tools / sysroot / tests）。④ `fetch.py`/`apply_series.py` 无 `--component` 过滤，任务 worktree 里 `make fetch apply-series` 会拉全部组件。⑤ `build-picolibc` 对构建目录 `rmtree` ⇒ `.work/build/picolibc` 不能是符号链接（L2 首跑红）。

**遗留问题**：
1. **L1 两项红，均在任务范围外**：(a) `check-milestones-fresh` A1+R1 —— 本册 `待验收` 但台账行仍在「待开始」（`m12-gem5-001`、`m12-chipyard-001` 同该项）；按分派约定本任务不改 `milestones*.md`，须主会话移入「进行中」并填派单时间后复跑 L1。(b) `check-temp-dirs` —— `m12-infra-001-review`、`INFRA-093t` 两个遗留临时目录（>2 h），清理归各自任务收尾。
2. `tools/gem5/build_gem5.py:191` 预存缺陷：`.work/build/gem5` 不存在时 `(source/"build").relative_to(build_link.parent)` 抛 `ValueError`（首次 `make build-gem5` rc=2）；先跑 `make check-gem5-decode` 建出该目录后 `build-gem5` rc=0。修复属 `tools/**`，超本任务范围，建议登记 issue。
3. C++ 侧机器 id 未改名（`fs_workload.cc` 的 `profile` 取值、`NodeState`/`node_*` 源文件名），由 `fs.py` 映射；彻底改名需另立任务（本次不动 C++ 语义）。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查 `fs.py.patch` 改动、README/changelog 与证据脚本，判决：**可交付（待验收）**。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `PROFILES` 改名后 `geometry_lines()`/`build()` 仍判 `"node"` ⇒ vast 落 tiny 分支 | ✅已修 | 逐处改 `"vast"`（geometry_lines、add_memory、`ram_base/ram_size`、MMU/CPU 分支） | C2 17 键 / C4 rc=19 |
| F2 C++ `FsWorkload` 只收 `tiny|node`，直传 `vast` ⇒ 运行期 fatal | ✅已修 | 新增 `WORKLOAD_PROFILES`（`vast→node`），Python 名不透传内部 id | C4 实跑 rc=19 无 fatal |
| F3 gem5 横幅含 pid/时间/命令行，直接比 stdout 恒不等 | ✅已修 | 证据脚本按 payload（滤横幅）比对；deprecated 只走 stderr | C3/C4 `same=yes`、dep=1 |
| F4 首轮脚本期望写错（`#x` 无下划线、tiny 键数、deprecated 正则误匹配 gem5 统计告警） | ✅已修 | 期望改 `0xffffff000000`、键数 9/17、正则收紧到 `fs.py: --profile node is deprecated` | 重跑 12/12 PASS |
| F5 注入中断会留下脏 `fs.py` | ✅已修 | 脚本加 `trap … EXIT` 用备份还原 | C9 还原后 md5 与注入前一致；C8 阻塞超时中断后源树 `md5`/`git status` 干净 |
| F6 `build-gem5` 首跑 rc=2（`build_gem5.py` 预存缺陷） | ❌不修（超范围） | 缺陷在 `tools/**`（本任务文件集外、与本次改动无关），不改；改用先跑 `check-gem5-decode` 建目录规避 | 二次构建 `build-gem5: PASS`；已登记遗留问题 2 |

### 第 1 轮 reviewer 验收

**审阅对象**：`fs.py.patch`（+ 应用后 `fs.py` 287 行）、`README.md`、`changelog.md`、本任务书、`run.sh`、`fs_workload.cc:84/109`、`machine-profiles.yaml`、`spec/Machine-v5`、`m12-integ-001`/`m12-testcases-001`。

**重跑（reviewer 亲跑，命令 / 真实输出 / 退出码）**
- 运行期证据目录下的 `run.sh` → `12/12 checks passed, 0 failed`、`RUNSH_EXIT=0`（还原后复跑同）。
- `--profile vast|node --dump-geometry`：rc=0/0；vast 17 键、node 17 键、tiny 9 键；去横幅后 `cmp rc=0`（各 583 B）；node stderr 恰 1 行 `fs.py: --profile node is deprecated, use --profile vast`，stdout 无该行；`--profile bogus` rc=2（choices `{tiny,vast,node}`）。
- 真跑（BootROM md5 `eb75b865…` + `m5_semi_exit.bin`）：vast rc=19、node rc=19，stdout 去横幅逐字节相同，stderr 仅多 1 行 deprecated。
- **改动前基线对照**（用 `git show HEAD:` 的 `fs.py.patch` 重建 265 行旧 `fs.py`）：旧 `node` 几何 payload `diff` 空、真跑 rc=19、stderr **无** deprecated 行、旧 `--profile vast` rc=2 ⇒ 别名与原 `node` 行为等价，唯一差异即新增的 stderr 行。
- 几何 vs `tests/shared/machine-profiles.yaml`：vast 11 个重叠键 + tiny 9 键全 OK、`total DIFF = 0`；yaml 对 hmon/smon/pmem 只有布尔，按 `spec/Machine-v5 §1.1` 抽核 `0x0fff_0000_0000` / `0x0bff_0000_0000` / `0x83ff_0000_0000` × 64 KiB 一致。
- 门控：`make build-gem5` rc=0（`build-gem5: PASS`）；`check-patch-tree` rc=0（7 组件 306 补丁）；`check-source-state` rc=0（gem5 `HEAD=8d64ea9f83ef count=1 clean=True`）；`check-gem5-decode` rc=0（`positive 264/264, negative 388/388, legality 28/28, legacy 2/2, failures 0`）；`make check-modules` rc=0（`module checks (L2): PASS`）；`make -k check` rc=2。
- L1 现场：唯一红 = `check-milestones-fresh`（M12 册 4 条：A1 `m12-gem5-001` 表=待开始/册=待验收；R1 `m12-gem5-001`、`m12-chipyard-001`、`m12-infra-002`）；**`check-temp-dirs` 本轮 PASS**（`陈旧 0 个`，两遗留目录已清）。主工作树 `make check-milestones-fresh` → **rc=0、`VIOLATION` 0 条**。
- **独立反例注入（engineer 未用）**：vast `bootrom_size 0x40_0000 → 0x1_0000` ⇒ 同一 `run.sh` **`8/12 checks passed, 4 failed`、`RUNSH_EXIT=1`**（C2 `bootrom_size=0x10000`、C4 `rc=1`、C7×2 `rc=2` = 断言⑥⑦ `worktree is not clean` / `patch does not reproduce worktree`）；`cp`+md5 还原 `8f2d86f9…` 相等 ⇒ 复跑 **`12/12`、rc=0**。
- `WORKLOAD_PROFILES` 必要性：删定义 ⇒ `NameError: name 'WORKLOAD_PROFILES' is not defined` rc=1；绕过映射直传 `profile=args.profile` ⇒ `fs_workload.cc:84: fatal: DADAO FS: unknown profile vast (tiny|node)` rc=1（≠19）。
- 补丁完整性：`python3 tools/infra/make_patch.py gem5` → `0 written, 97 unchanged`；`git status --porcelain -uall` 仍只 4 文件、`components/gem5/patches/` 下只 `fs.py.patch`、无未跟踪文件（无漏 staging）。
- 快照对账：4 改动文件 + `fs.py` + `logs/fs.py.bak` 的 md5 与注入前逐个相等；完成区 22 行 ≤30、无绝对/运行期路径（`.work/evidence/<任务ID>/`、`.work/build/**` 属豁免形）；「修改文件」4 项 == 实改 4 项。

**约束核验**：未改 `se.py` / `contracts/` / `spec/` / 测试断言；未动共享台账（主工作树 `git status` 干净）；别名等价、几何、门控、反例可达 FAIL、补丁完整性、完成区六项逐条见上，均守住。

**判决：Accepted**

**文档级 finding（不阻断，architect 收尾改）**：完成区/遗留问题 1 写「仅 `check-milestones-fresh` 与 `check-temp-dirs` 红」，本轮实测 `check-temp-dirs` 已 PASS、L1 现仅 1 项红；`make_patch` 记「1 written / 96 unchanged」，复核为「0 written / 97 unchanged」（合计均 97，时点差异）。

#### 收尾（architect，2026-11-09 00:25）

- 判决 **Accepted**：reviewer 用**改动前** `fs.py` 实跑对照，证明 `node` 别名与原 `node` 逐字节等价（唯一差异 = 新增 stderr 提示）；删 `WORKLOAD_PROFILES` ⇒ `NameError`、直传 `vast` ⇒ C++ fatal，证明映射必要且非掩盖缺陷。
- 独立反例（vast `bootrom_size` 改回 1 MiB）⇒ 证据脚本 8/12、rc=1 ⇒ `cp`+md5 还原 ⇒ 12/12 回绿。
- 补丁完整性：`make_patch.py gem5` → 0 written / 97 unchanged，无漏 staging。
- 遗留：`qemu_gem5_shim.py` 白名单仍 `("tiny","node")` ⇒ 已归 `m12-testcases-001`。
