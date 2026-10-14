# LLVM-091t: llvm-project 23.1.1 → 23.1.3（差异调查 ⇒ 升级执行）

**模块**：llvm
**项目里程碑**：M8
**依赖**：无
**状态**：已验证

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

## 第二段：升级执行记录（2026-10-14，**已执行**；**不改写**既有 §D1–D6 与确认表）

> **授权**：用户 2026-10-14 经主会话确认「**可升级**」（原话见主会话记录；本段为执行实测事实）。
> **证据落盘**（`.work/` 已 gitignore）：门控/构建日志 `.work/log/<模块>/`（`LLVM-091t-*.log` + `*.EXIT`）；一键证据脚本 `.work/evidence/<任务ID>/run.sh`（`--full` 全量回归 / `--inject` 反例自检）。

### E1 差异核实（本地浅仓库独立复算，非引用 API）
- `git diff --numstat <23.1.1> <23.1.3>`（两个 shallow 边界树均在场）⇒ **172 files / +6036 −1236**，与 §D1（GitHub compare API）**逐项一致** ✓。
- **A/B/C 复算**：A=2（与 §D2 同两文件）/ B=170 / C=69；分区自检 `A+B=172`、`A+C=71` 成立 ✓。
- `compiler-rt` 变更集仅 3 文件（`lib/builtins/clear_cache.c`、`lib/interception/interception_win.cpp`、`lib/interception/tests/interception_win_test.cpp`）⇒ **`muldc3.c`/`mulsc3.c` 不在内**，不重移植（同 §D3）✓。
- **边界**：`63 commits` **无法本地复算**（浅仓库 `rev-list --count` 见不到中间提交）⇒ 沿用 §D1 的 API 结论，**未独立复现**（如实标注）。

### E2 锁 + 取源（实测）
- 锁改动**恰 2 行**：`commit` → `0d261d1c…`、`shallow_ref` → `llvmorg-23.1.3`（`patch_dir`/`patch_series`/`enabled`/`repository`/`shallow` 均未动；`git diff --stat` = 2 insertions / 2 deletions）。
- 镜像增量取源：`git -C .cache/llvm-project.git fetch --depth 1 origin tag llvmorg-23.1.3` ⇒ **rc=0，63 s，+5.4 MiB**（395,600,999 → 401,224,987 B；远低于 §D4 最坏「0.3–0.4 GiB」；通道 = **SJTU 主**，未动用备源）。
- 源检出：`fetch --depth 1 <commit>` + `checkout --detach` ⇒ rc=0（2 s）；HEAD = `0d261d1c…`、`status` 干净、`git diff` 可用。
- `make fetch` **复跑 rc=0 且幂等**：镜像 `already has 0d261d1ca552; skipping fetch`；源 `already has … as an ancestor (patches applied on top) -- leaving it alone`。

### E3 补丁集处置（A 类 2 个）
- `make apply-series` 的 **`llvm-project` 段 ⇒ `71 applied, 0 skipped`**：71 补丁（**含 A 类 2 个**）在 23.1.3 上**全部干净应用**（`git apply` 按偏移），**零冲突** ⇒ **无补丁需弃**。（**整条 target 仍 rc=2** —— 非补丁冲突，而是其后 `patchless` 组件触发既有缺陷，见「遗留问题①」。）
- A 类语义共存复核（实测）：补丁后 `Triple.h`/`Triple.cpp` **同时**含上游 `AArch64SubArch_arm64e_x1`/`isArm64e_x1()`/`arm64e.x1` 与我方 `dadao`；未打补丁的 23.1.3 base 含 `arm64e.x1`（5 处）而 `dadao` 计数 **0** ⇒ 两侧改动互不吞噬 ✓。
- **重导出**（`tools/infra/make_patch.py`）：`1 written, 70 unchanged` —— 仅 `llvm/lib/TargetParser/Triple.cpp.patch` 被重写（9 行改 = `index` 行 + 各 hunk 头 **+2 行偏移**，无语义变化）；`Triple.h.patch` 正文逐字节一致 ⇒ **未重写**（其 `index` 行仍为 23.1.1 base blob，见「遗留问题②」）。`series` 未变、一文件一补丁保持。
- 门控：`make check-patch-tree` rc=0（`4 component(s), 127 patches OK`）；`make check-index-blobs` rc=0；`--source-state` 全 OK（`llvm-project: HEAD=844ca6b38374 count=1 clean=True`）。

### E4 重建（实测，`JOBS=8` 单次一个）
- `make build-mc` **rc=0，4320 s（≈72 min）**；`make install-host` **rc=0，298 s（≈5 min）**；合计 4618 s。⚠ **超 §D5 申报的「10–40 min」**——根因 = 版本 bump 落在 `cmake/Modules/LLVMVersion.cmake` ⇒ cmake 重配置 + 版本头被广泛包含 ⇒ 近全量重编（3244 目标）；**申报偏低**，教训进「新发现/坑」。
- 产物核：`.work/build/llvm/bin/clang` 与 `.dadao/cross-toolchain/bin/{clang,llvm-mc}` 均报 **`23.1.3`**（`clang version 23.1.3 (<mirror> 844ca6b38374…)`）。

### E5 回归（★无回归）
- **L1** `make check` rc=0（升级前基线亦 rc=0）；**L2** `make check-modules` rc=0（含 `check-lit` 107/107 = 100%、`check-interface` 83/83 FAIL 0、`check-qemu-smoke`/`test-codegen`/`test-elf`/`test-semihost` 全 PASS、picolibc 快档 18/0/2/0）。
- `make check-patch-tree` / `check-index-blobs` / `check-no-residue` / `check_issues.py` ⇒ 各 **rc=0**。
- **picolibc 全量（M7 达成口径）**：升级前本地实测基线 = `total 235 / pass 213 / fail 0 / excluded 22 / blocked 0`（rc=0）；升级后 = **同值**（rc=0）⇒ **无回归** ✓（计数现场统计，未写死）。
- 证据脚本 `.work/evidence/<任务ID>/run.sh`：`--full` ⇒ **PASS（rc=0）**；`--inject` ⇒ **PASS（rc=0）**（I1 锁值 / I2 补丁截断 / I3 工作树脏 / I4 越界文件 各自「注入→FAIL→cp+md5 还原→回绿」；I5 证明版本断言非恒真）。

## 完成区

**测试结果**：L1 rc=0（升级前/后）；L2 rc=0（lit 107/107、interface 83/83 FAIL 0、codegen/elf/semihost smoke 全 PASS）；picolibc 全量 前=后=**235/213/0/22/0**（fail=0，无回归）；check-patch-tree / check-index-blobs / check-no-residue / check_issues 各 rc=0；证据脚本 `--full` 与 `--inject` 均 rc=0。
**修改文件**：`manifests/components.lock.toml`（2 行）、`components/llvm-project/patches/llvm/lib/TargetParser/Triple.cpp.patch`（重导出 9 行）、本任务书、`.tao/knowledge/milestones.md`（1 行）；**未改** `spec/`、`contracts/`、`tests/vectors/`、任何 `tools/`。
**验收结果**：源 `.work/source/<组件>` HEAD=`844ca6b38374`（base `0d261d1c` + 1 提交）、干净；镜像 `llvmorg-23.1.3^{commit}` = `0d261d1ca552…`；`build-mc` 4320 s rc=0、`install-host` 298 s rc=0，装出的 clang/llvm-mc 报 `23.1.3`；`make fetch` 复跑 rc=0 幂等。日志见 `.work/log/<模块>/`，脚本见 `.work/evidence/<任务ID>/`。
**新发现/坑**：① `make apply-series` rc=2 —— `tools/infra/apply_series.py:108` 对 **`patchless` 组件**（chipyard/linux/llvm-test-suite）取 `component["patch_dir"]` ⇒ `KeyError`；**既有缺陷、与本升级无关**（用未改动的脚本 + 仅 chipyard 的临时 manifest 已单独复现，见遗留①）。② 版本 bump 提交改 `cmake/Modules/LLVMVersion.cmake` ⇒ 触发**近全量重编**，申报耗时须按此量级（≈72 min）。③ 浅镜像跨 tag 切换可用 `fetch --depth 1 <tag>` + 双 shallow 边界，无需 `--unshallow`（增量仅 5.4 MiB）。④ `make_patch.py` 的 §6.2 比较**归一化 `index` 行** ⇒ 上游变而正文等价者**不重写**（`Triple.h.patch` 的 `index` 行因此陈旧，但全部门控均归一化该行）。⑤ 运行 `make fetch` 会顺带重建缺失的 `.cache/chipyard.git`（5.5 MB bare，本地镜像；非本任务目标，已披露）。⑥ **自审抓到**：门控脚本用 `git status --porcelain` 时**非 ASCII 路径被引号转义** ⇒ 需 `-c core.quotepath=false`（同 `lessons §2.19`）；另「预期 FAIL 的反例探针」不可复用会置全局失败的 `record()`。
**遗留问题**：① **`make apply-series`（含 `make prepare`）对 `patchless` 组件 crash**（`KeyError: 'patch_dir'`，rc=2）⇒ 验收标准②的「rc=0」**BLOCKED by 既有缺陷**；替代证据 = 本次 71 补丁实际全部干净应用 + `check-source-state` 全 OK + `check-patch-tree` rc=0。建议（**越界未改，待 architect 决定**）：在 `tools/infra/apply_series.py` 源树存在性检查后加 `if component.get("patchless"): continue`（对齐 `check_patch_tree.py:310` 的既有写法）。② `Triple.h.patch` 的 `index` 行仍指向 23.1.1 base blob（工具按 §6.2 判为「未变」而未重写；门控归一化该行、`check-index-blobs` 只查 new-file 补丁）⇒ 保持工具产出、未手工改；如需刷新请 architect 定夺。③ `63 commits`（§D1）未能本地复算（浅仓库无中间提交）。

## 审阅记录

#### 第 1 轮 architect 差异调查（2026-10-14）
（第一段只读调查产出见上 §D1–D6；证据 `.work/log/llvm/llvm-2313-diff-*`；**未升级、未拉大仓库、未提交**。第二段升级执行待用户确认后另行下发。）

#### 第 2 轮 engineer 自审（2026-10-14，LLVM-091t 升级执行）
自主逐行审查对象 = 我的改动集（锁 2 行、`Triple.cpp.patch` 重导出、证据脚本 `run.sh`）+ 全部真实验收输出。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `make apply-series` rc=2（`KeyError: 'patch_dir'`） | ⏸**延后**（越界，未改 `tools/`） | 无（记录根因+建议修法） | 未改动脚本的隔离复现：仅 chipyard 的临时 manifest ⇒ 同一 `KeyError`（rc=1）；本仓库 rc=2（traceback 指向 `apply_series.py:108`） |
| F2 `Triple.h.patch` 的 `index` 行陈旧（23.1.1 base blob） | ❌**不修**（工具既定语义） | 无 | `make_patch` `1 written, 70 unchanged`（§6.2 归一化比较）；`check-patch-tree` rc=0、`check-index-blobs` rc=0（该行被归一化 / 仅查 new-file 补丁） |
| F3 证据脚本 `--inject` 模式缺陷：直接复用 `record()` ⇒ 「预期 FAIL」会污染脚本退出码 | ✅**已修** | 新增 `probe()`（只打印不改 `rc_all`），由调用方判定 | `--inject` rc=0（改前 rc=1，实际输出留 `.work/log/<模块>/LLVM-091t-evidence-inject.log`） |
| F4 证据脚本 `check_patch_tree` 用相对 `patch_series` ⇒ 依赖调用方 cwd | ✅**已修** | 传入 `ROOT` 并在 python 内 `os.path.join` | 从仓库根运行 `make check-patch-tree` 段 rc=0、`series_total=127` 现场统计 |
| F5 证据脚本 I5 与「期望版本」耦合 ⇒ 重建前误报（非恒真验证失败） | ✅**已修** | I5 改为自足判别（真实子串必须命中、两个伪造版本号必须不命中） | 重建后 `--inject` rc=0，I5 `act=yes/no` |
| F6 A 类「2 个补丁重导出」预期 vs 实际只重写 1 个 | ✅**已核**（非缺陷） | 无 | A 类两文件均**干净应用**；`Triple.h` 正文与 base diff 逐字节一致故按 §6.2 不重写；语义共存实测（`dadao` 与 `arm64e.x1` 同时在场） |
| F7 `build-mc` 实测 72 min，超申报 10–40 min | ⏸**延后**（估算问题，非代码） | 无 | 实测 `elapsed_s=4320`（`.work/log/<模块>/LLVM-091t-build-timing.log`）；教训已入「新发现/坑」② |
| F8 剥离过程纪律：改用绝对 `cd` 的分离包裹脚本（冗余） | ✅**已修** | 后续命令一律用工具 `workdir` + 相对路径，不再 `cd` | 其后所有证据/门控命令均相对路径执行；本项为过程披露 |
| F9 证据脚本 `check_scope` 未加 `core.quotepath=false` ⇒ 任务书**非 ASCII 路径被引号转义** ⇒ 误报「越界」 | ✅**已修** | `git -C "$ROOT" -c core.quotepath=false status --porcelain -uall` + 路径去引号归一化 | 修前 `evidence(LLVM-091t, mode=fast): FAIL — repo: changes within task scope`（留日志）；修后同命令 **rc=0**（`scope OK (4 path(s) changed)`）；`--inject` rc=0 |
| F10 脚本改动后，先前 `--full` 记录已非最终版 | ✅**已做**（重跑） | 无 | 最终版（`md5 d27c3307…`）`--full` 与 `--inject` 均 **rc=0** |

#### 第 1 轮 reviewer 验收（重派接续，2026-10-14；前位 reviewer 未落判定 = ISS-205）

> 全部判定依据 = reviewer 亲跑命令的真实输出/退出码（日志留 `.work/log/<模块>/` 的 `LLVM-091t-reviewer-*` 系列）；未重建 llvm。

**重跑记录（亲跑）**：
- 门控 6 项各 rc=0：`make check`(L1) 尾行 `repository checks (L1): PASS`；`make check-modules`(L2) = lit `107/107 Passed 100%` + interface `83 项 PASS 83 FAIL 0` + picolibc 快档 18/0/2/0 + `module checks (L2): PASS`；`check-patch-tree` = `4 component(s), 127 patches OK`；`check-index-blobs` = `91 new-file patch(es) OK; 36 modification patch(es) skipped`；`check-no-residue` = PASS；`check_issues.py` = `27 open, 2 closed`。退出码均直接捕获（无 tee 吞码）。
- 锁/源/镜像：对提交 `6502abb` 逐行核 `components.lock.toml` **恰 2 行**（`commit=0d261d1c…`、`shallow_ref=llvmorg-23.1.3`，余字段未动）；源 HEAD=`844ca6b3…`=base+1、脏行 0、净 diff 71 = `series` 71（series↔补丁树 diff rc=0）；镜像 `cat-file -t 0d261d1c…`=commit、`llvmorg-23.1.3^{commit}`=`0d261d1c…`、tag obj `856f0005…`=tag。
- `Triple.cpp.patch` **逐行核**（`git show 6502abb -- <该补丁>`）：18 行改动 = `index` 1 行 + 8 个 `@@` 头（各 hunk 两侧同增偏移 +2…+5、行数不变、正文零改动）⇒ **零语义变化** ✓；`series` 不在改动集 ✓。A 类语义共存抽验：`Triple.h` 同含 `AArch64SubArch_arm64e_x1`/`isArm64e_x1()` 与 `dadao`（`LastArchType = dadao`）、`Triple.cpp` 含 `arm64e.x1` 与我方 dadao ⇒ 互不吞噬 ✓。
- 版本+抽验：`clang --version` = `clang version 23.1.3 (…844ca6b3…)`、`llvm-mc --version` = `LLVM version 23.1.3`；`llc -march=dadao` 产 `add.uo {rd0, rd8}, rd16, rd17`/`ret rd0, 0`（rc=0）；`llvm-mc --show-encoding` = `[0x50,0x00,0x84,0x11]`/`[0x76,0x00,0x00,0x00]`，`0x50` 对上 `contracts/opcodes.yaml` `add.uo` op ✓。
- ★picolibc：before/after 四数均 `213 pass / 0 fail / 22 excluded / 0 blocked`（total 235，rc=0），**逐用例 diff 0 行**；**reviewer 自跑全量一次**（长任务规则）rc=0 = 同四数、与 after 逐用例 diff 0 行 ✓（harness 以工具链 clang 逐例现编，after 运行时该二进制已 = 23.1.3；前基线 L1 rc=0 采信既有日志）。
- 遗留复现：`make apply-series` **rc=2**，traceback `apply_series.py:108 KeyError: 'patch_dir'`（crash 于第 5 个 enabled 组件 chipyard=patchless；前 4 组件 `already applied … skipped` 幂等无副作用）⇒ **既有缺陷、与升级无关**（脚本不在改动集），任务书遗留①如实登记 ✓。
- 反例（独立注入，`cp`+md5 还原，未用 git 还原）：① 锁 `commit` 末位 c→d ⇒ `check-patch-tree` **rc=2**（`read-tree …128`）⇒ 还原 md5 `27dc6790…` 前后一致 ⇒ 回绿 `127 patches OK`；② `Triple.cpp.patch` 正文 `.Case("dadao", dadao)`→`dadaoX` ⇒ **rc=2**（断言⑥⑨双命中 ⇒ 门控真查语义、非恒真）⇒ 还原 md5 `8db4ad5b…` 一致 ⇒ 回绿 ✓。
- 收尾对账：验收前后 `git status --porcelain -uall` 均 0 行、4 关键文件 md5 逐项一致（注入无残留）；改动集与完成区「修改文件」逐一对账 ✓。

**约束核验**：只动锁 2 行 + `Triple.cpp.patch` 重导出 + 任务书 + milestones（`6502abb` 文件集核对，`spec/`/`contracts/`/`tests/vectors/`/`tools/` 零改动 ✓）；未重建 llvm；完成区 ≤30 行且与真实输出逐条对齐 ✓。

**判定：Accepted**（验收①③④⑤⑥ 亲跑全通过；验收② 的 `apply-series rc=0` 按替代证据口径满足 = 71 补丁全净应用 + `check-patch-tree` rc=0 + source-state OK）。
- **阻断项：无**（`apply-series` rc=2 属既有缺陷、不在本任务改动集；建议 architect 单立小任务给 `apply_series.py` 补 `patchless` 守卫，对齐 `check_patch_tree.py:310`）。
- **非阻断项**：① `Triple.h.patch` 的 `index` 行陈旧（实测 `d819c4975b13…` = 23.1.1 blob，23.1.3 应为 `c5af2325…`）——门控归一化该行、维持工具产出即可（遗留②）；② **reviewer 新发现**：picolibc 库本体（`libc.a` mtime 10-12）未随 23.1.3 重编（meson 缓存编译器检测仍报 23.1.1）⇒ 无回归实证面 = 新编译器现编 235 测试 + 既有库，建议 architect 决定是否补「工具链变更后强制重建 picolibc 库」；③ `63 commits` 浅仓库无法本地复算（沿用 API 结论）。

#### 第 1 轮 architect 收尾（2026-10-14；picolibc 强制重建 + 提交落地）

> **只追加**，不改写既有结论（§D/§E/完成区/前轮审阅记录原样保留）。触发 = reviewer `Accepted` 的**非阻断项②**（picolibc 库本体未随 23.1.3 重编）。

**① picolibc 强制重建（处置非阻断项②）**
- **做法**（申报 = 秒~分钟级）：`meson --reconfigure` **复用** `coredata.dat` 内既有 compiler 对象、**不重跑**编译器检测（实测缓存仍报 `23.1.1`）⇒ 改**删 `.work/build/picolibc`** 后 `make build-picolibc`（走**全新 `meson setup`**，重跑检测）；旧树先 `mv` 至 `<临时目录>` 留存（可还原，**非** `rm`）。**未改**任何 `components/picolibc/**`。
- **实测**：重建 **rc=0 / 15 s**（1120 条 `Compiling C object`）；全量复核 **rc=0 / 367 s**。日志 = `.work/log/<模块>/LLVM-091t-arch-*`。
- **「libc.a 属新工具链产物」可核证据**：装出 `libc.a` md5 `c5617aa7…` / 1802210 B / mtime `10-14 17:24`（基线 `816fb4fb…` / 1803426 B / `10-12 20:15`）；**归档内成员** `libc_argz_argz_add.c.o` 的 `.comment` = `clang version 23.1.3 (…844ca6b3…)`（基线同成员 = `23.1.1`）；`meson-log` 检测行 = `clang 23.1.3`、`coredata.dat` = `Clang 23.1.3`。
- **复核四数**：`stage=full total=235 pass=213 fail=0 excluded=22 blocked=0`（rc=0）⇒ **与升级前基线同值**；与「重编前」**逐用例 diff 0 行**（235 行）⇒ **不回归** ✓。

**② 非阻断项登记（四条，追加）**
- ① `Triple.h.patch` 的 `index` 行仍指 23.1.1 blob（`make_patch.py §6.2` 归一化 `index` 行 ⇒ 正文等价者不重写；门控均归一化该行、`check-index-blobs` 只查 new-file 补丁）⇒ **不影响门控**，维持工具产出（同「遗留②」）。
- ② `63 commits`（§D1）浅仓库**不可本地复算**（仅 `172 files / +6036 −1236` 可复算）；沿用 API 结论（同「遗留③」）。
- ③ picolibc 强制重建的**做法与证据** = 上①（本轮）。
- ④ `make apply-series` 对 `patchless` 组件 `KeyError: 'patch_dir'`（`tools/infra/apply_series.py:108`，rc=2）= **既有缺陷**；**建议**在其源树存在性检查后加 `if component.get("patchless"): continue`（对齐 `check_patch_tree.py:310`）。**本次不改**（独立小任务，待用户/后续立项）。

**③ `ISS-205`**：其触发事实（reviewer 判定缺位）已由本轮重派 reviewer `Accepted` **消解**；是否 `close`（补 `resolved_by`）由主会话 `/complete` 处置（**本次未改** `issues.yaml`）。

**④ 交叉复核（architect 自跑，均现场 rc）**：`make check`(L1) **rc=0**；`make check-modules`(L2) **rc=0**；`check-no-residue` **rc=0**；`check-knowledge-refs` **rc=0**；`check_issues.py` **rc=0**。日志 `.work/log/<模块>/LLVM-091t-arch-*`。

#### architect 提交留痕（LLVM-091t 收尾，分支 `LLVM-091t-final`）

- **档位**：**正常提交**（reviewer 最新判决 `Accepted`，**无** `WIP:` 前缀）。
- **提交信息**：`LLVM-091t: llvm-project 23.1.3 升级收尾（强制重建 picolibc、四数复核 235/213/0/22/0）（已验证）`。
- **提交号**：随本条同 commit 落地 ⇒ **不内嵌自身 hash**（避免 `--amend` 造成悬空 hash，对照 `INFRA-073t` F2）；现场取证 = `git log --oneline -1`。**只 `commit`、未 `push`**；`merge --ff-only` 落地 `master`。
- **文件集对账**（显式 staging，逐个路径，**禁** `git add -A`/`.`）：`M`×2 = 本任务书 + `.tao/knowledge/milestones.md`——与完成区「修改文件」+ 本任务范围**逐条对齐**（**无漏提 / 多提 / 越界**）。

