# LLVM-091t: llvm-project 23.1.1 → 23.1.3（差异调查 ⇒ 升级执行）

**模块**：llvm
**项目里程碑**：M8
**依赖**：无
**状态**：待开始

> **本任务分两段**：**第一段 = 差异调查（只调查、不升级，已完成，见下）**；**第二段 = 升级执行（← 须用户确认后才另行下发，本任务书尚未授权执行）**。

## 执行环境
**执行环境**：本地

## 用户指令（2026-10-14，经主会话转问，**原话**）

- 「**先查差异 ⇒ 与用户确认后才升级**」。
- 即：**先**做差异调查（**不升级**）⇒ 产出确认表 ⇒ **交用户确认** ⇒ **确认后方可升级**。

## 背景（事实，实测）

- 现状锁：`manifests/components.lock.toml` 的 `llvm-project` = `commit = 6dfe1677ab8dffbc6ec13d53a1e0215d75147689`（= annotated tag `llvmorg-23.1.1` 的 peel commit，实测复核 ✓）+ `shallow_ref = "llvmorg-23.1.1"`；补丁集 = `components/llvm-project/patches/**`（一文件一补丁 + `series`；`make check-patch-tree` 报 `4 component(s), 127 patches OK` ⇒ **llvm-project 71** + qemu 34 + picolibc 18 + embench-iot 4）。
- `.cache/llvm-project.git` = **shallow**（378 MB，仅 1 个 commit、仅 `llvmorg-23.1.1` tag；remote = `https://mirror.sjtu.edu.cn/git/llvm-project.git`）。
- 目标 tag = **`llvmorg-23.1.3`**：annotated tag object = `856f0005e57023e63664c560a829c620360ea1f1` ⇒ peel ⇒ **commit `0d261d1ca552c95a8f007e061c787ac7132fbcbc`**。
  - **三方独立一致**（① GitHub API `GET /git/refs/tags/llvmorg-23.1.3` 的 object.sha；② GitHub API `GET /git/tags/856f0005…` 的 object.sha；③ SJTU 镜像 `git ls-remote` 返回同一 tag object sha）。
  - ⚠ **订正（重要，已查明根因）**：主会话给出的 `7fa03005193c4cc9b882e0b70f9f43a088c52033` **不是 `llvm/llvm-project` 中的任何对象**（API `GET /commits/7fa03005…` = `No commit found`）；它实为 **`llvm-test-suite`** 的 `llvmorg-23.1.3` **annotated tag object**（见并行任务 `INFRA-077t`：test-suite tag object `7fa03005…` ⇒ peel commit `2919e551…`）——即**混库/混字段订正**（把 test-suite 的 *tag object* sha 误当 llvm-project 的 *commit*）。**本任务一律采用 llvm-project 的 `0d261d1c…`（tag object `856f0005…`）**。
  - 简称 `23.1.3` 不是合法 ref；tag 名 **带 `llvmorg-` 前缀**（本仓库锁的 23.1.1 亦然）。

## 第一段：差异调查（已完成，2026-10-14；只读，未拉仓库、未升级）

> **方法**：GitHub compare API `repos/llvm/llvm-project/compare/llvmorg-23.1.1...llvmorg-23.1.3`（HTTP 200；`files[]` 未截断）。
> **证据落盘**（`.work/` 已 gitignore）：`.work/log/llvm/llvm-2313-diff-compare-2311-2313.json`（原始 JSON）、`-analysis.log`（聚合/交集全文）、`-Aclass.log`（A 类上游 diff 全文）、`-patchsim.log`（模拟应用实测）、`-fetchcost.log`（成本估算输入）、`-ourpatched-files.txt`（我方触及文件全集）。

### D1 上游差异总量（`llvmorg-23.1.1` `6dfe1677` … `llvmorg-23.1.3` `0d261d1c`）

- **63 commits / 172 files / +6036 −1236 行**（148 modified + 24 added + **0 removed + 0 renamed**）。
- 版本 bump 提交：`e280c5056ed1`「Bump version to 23.1.2」、`67f4a076a097`「Bump version to 23.1.3」。
- 顶层目录聚合（files / +add / −del / 新增文件）：`llvm/` 107 / +4684 / −1028 / 14；`clang/` 20 / +478 / −82 / 4；`libcxx/` 11 / +219 / −13 / 2；`clang-tools-extra/` 9 / +176 / −23 / 0；`lldb/` 9 / +121 / −7 / 0；`lld/` 7 / +192 / −11 / 4；`compiler-rt/` 3 / +19 / −8 / 0；`libc/` 2 / +17 / −6 / 0；`.ci` 1、`.github` 1、`cmake` 1、`mlir` 1。

### D2 ★ 补丁面交集（核心产出）

- 我方触及上游文件全集 = **71**（由 `series` 提取；顶层：`llvm/` 55、`clang/` 12、`lld/` 4）。
- **A = 上游变了 ∧ 我方补丁触及（风险项）= 2**：

  | 我方补丁 | 上游变更摘要（23.1.1→23.1.3） |
  |---|---|
  | `llvm/include/llvm/TargetParser/Triple.h` | **+8 / −1**：`SubArchType` 枚举尾增 `AArch64SubArch_arm64e_x1`；新增 `isArm64e_x1()` 谓词（AArch64 `arm64e.x1`） |
  | `llvm/lib/TargetParser/Triple.cpp` | **+5 / −0**：`getArchName` / `parseArch`（`.Case("arm64e.x1")`）/ `parseSubArch` 三处支持 `arm64e.x1` |

  - **实测（模拟应用，非全树）**：以 23.1.1 base 文件 + 上游该文件 diff 合成「模拟 23.1.3 单文件」，再 `git apply --check` 我方两补丁 ⇒ **两文件均 rc=0**（`Triple.cpp` 仅行号偏移 2–5 行，无冲突）。证据 `.work/log/llvm/llvm-2313-diff-patchsim.log`。
  - **冲突成因**：上游改的是 **AArch64 sub-arch**（`SubArchType`/`parseSubArch`），我方改的是 **`ArchType` 增 `dadao`**（`Triple.cpp` 双方同触 `parseArch`，但落点不同行）。
  - **边界**：该实测**只覆盖这 2 个文件**，**非**全补丁集 × 全 23.1.3 树 ⇒ **不得**据此断言「全补丁集必然干净应用」。
- **B = 上游变了 ∧ 与我无关 = 170**（`llvm/` 105、`clang/` 20、`libcxx/` 11、`clang-tools-extra/` 9、`lldb/` 9、`lld/` 7、`compiler-rt/` 3、`libc/` 2、`.ci`/`.github`/`cmake`/`mlir` 各 1）——**仅计数**。
- **C = 我方触及 ∧ 上游未变 = 69**——**仅计数**；**预期**仍可干净应用，但**不得**断言「必然干净」（须在第二段由 `apply_series` 实测）。

### D3 `compiler-rt` 检查

- `compiler-rt/lib/builtins/muldc3.c`、`mulsc3.c`（我方 `INFRA-067t` 的**移植来源 = 23.1.1**）**均不在** 23.1.1→23.1.3 变更集内 ⇒ **无需重移植**。
- 变更集内的 compiler-rt 文件仅 3：`lib/builtins/clear_cache.c`、`lib/interception/interception_win.cpp`、`lib/interception/tests/interception_win_test.cpp`。

### D4 增量获取成本（只探测，**未执行大 fetch**）

- 既有 `.cache/llvm-project.git` = **378 MB**（shallow，单 commit）。
- **估算（未实测）**：`git fetch --depth 1 origin tag llvmorg-23.1.3` 走增量协商 ⇒ 约「changed blobs」量级（148 个 modified 文件的 **base 字节和 = 14.7 MiB** + 24 个新增文件 + trees）⇒ **数十 MiB**；**最坏**（无增量复用、整快照 pack）≈ **0.3–0.4 GiB**。
- **源可达性实测**：SJTU 镜像 `git ls-remote --tags` **rc=0**（含 `llvmorg-23.1.3`）；直连 `github.com` git 端点 `ls-remote` **超时**（`RC=124`；同环境下 GitHub **API 正常**）⇒ 取源宜走 SJTU 镜像，备 `ghfast.top` / `gh-proxy.com`。

### D5 升级步骤草案（**不执行**；待用户确认后于第二段执行）

1. 改锁：`manifests/components.lock.toml` ⇒ `commit = 0d261d1c…`、`shallow_ref = "llvmorg-23.1.3"`。
2. 取源：`make fetch`（经 SJTU 镜像；`--depth 1 <tag>`）⇒ 更新 `.cache/llvm-project.git` + `.work/source/llvm-project`（新 base）。
3. 应用补丁集：`make apply-series`（`tools/infra/apply_series.py`）；**冲突处置策略** = ① 上游已修同一问题 ⇒ **弃该补丁**（逐条论证）；② 仅行号偏移 ⇒ **重做补丁**（`tools/infra/make_patch.py` 重导出，**不改算法**）。
4. 重建：`make build-mc`（**长任务**：`setsid nohup … &` + 落完成标记 + `JOBS=8`；启动前申报耗时）+ `make install-host`。
5. 门控：`make check`（L1）⇒ `make check-modules`（L2）。
6. 登记：`milestones.md` 流水 + 本任务书完成区。

- **预计耗时（估算，未实测）**：取源 数分钟（镜像）/ 补丁应用 分钟级 / **重建 `build-mc` 数十分钟~1–2 小时**（增量，视 ccache）/ L1+L2 数十分钟 ⇒ **总 ≈ 1.5–3 小时**；重建前须再申报。

### D6 确认表（交主会话转问用户）

| 项 | 值 |
|---|---|
| 差异规模 | **63 commits / 172 files / +6036 −1236** |
| **A 类风险补丁** | **2**（`Triple.h`、`Triple.cpp`）——**模拟实测可干净应用（仅偏移）** |
| B / C | **170 / 69** |
| `compiler-rt` 两文件 | **未变** ⇒ 不重移植 |
| 增量获取 | **估算** 数十 MiB（最坏 0.3–0.4 GiB）；**未实测** |
| 预计耗时 | **估算** 1.5–3 小时（含重建） |
| **建议** | **升**（A 类风险面小、仅 2 文件且模拟实测可应用；23.1.1→23.1.3 为 patch-release，含 X86/ARM/AArch64/clang/libc 修复与安全类改动）——**待用户裁定** |
| **不确定项** | ① 全补丁集「必然干净」**未验证**（仅 A 类逐文件模拟）；② 增量 fetch 真实体积/耗时**未实测**；③ `build-mc` 耗时**未实测**；④ 未单列 `23.1.2 ↔ 23.1.3` 窗口（本调查为 23.1.1 ↔ 23.1.3 全程）；⑤ 未评估 23.1.1→23.1.3 对**契约/`contracts/`** 的语义影响 |

## 接口规范（第二段执行用；**待用户确认后方可执行**）

- **输入**：本任务书 §D6 确认表 + 用户「可升级」裁定。
- **输出**：`manifests/components.lock.toml`（2 字段）、更新的 `.cache/llvm-project.git` + `.work/source/llvm-project`（新 base）、补丁集（按需重导出）、`build-mc`/`install-host` 产物、门控日志、`milestones.md` 流水行、本任务书完成区。
- **约束**：只改锁 + 补丁 + 任务书 + 流水；**不改** `spec/`、`contracts/`、`tests/vectors/`；**不改**已有补丁的算法；取源走镜像（先申报）；重建按长任务规则。

## 验收标准（第二段）

1. **锁与源**：`components.lock.toml` = `0d261d1c…` + `llvmorg-23.1.3`；`.work/source/llvm-project` HEAD/base = 同 commit（真实输出）。
2. **补丁集**：`make apply-series` rc=0（或冲突补丁逐条处置并记录）；`make check-patch-tree` rc=0；`--source-state` = 干净 + `base+N`。
3. **构建**：`make build-mc`、`make install-host` rc=0（真实输出/退出码）。
4. **门控**：`make check`(L1)、`make check-modules`(L2) rc=0。
5. **无回归**：既有 `check-*` 结果与升级前一致或更优（现场统计，计数不写死）。
6. **登记**：`milestones.md` 流水行 + 完成区（≤30 行）与真实输出逐条对齐。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 architect 差异调查（2026-10-14）
（第一段只读调查产出见上 §D1–D6；证据 `.work/log/llvm/llvm-2313-diff-*`；**未升级、未拉大仓库、未提交**。第二段升级执行待用户确认后另行下发。）
