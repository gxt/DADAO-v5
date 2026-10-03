# LLVM-002t: LLVM 组件基线

**模块**：llvm
**项目里程碑**：M1
**依赖**：`INFRA-006t`、`INFRA-009t`、`INFRA-013t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`manifests/components.lock.toml`（`INFRA-003t` 产出，`llvm-project` 条目 `enabled = false`、`commit = ""`）、`Makefile`（`INFRA-006t` 产出的 `build-mc` stub）、LLVM 上游仓库 `https://github.com/llvm/llvm-project.git`
- 输出：
  - `.tao/knowledge/adr-0006-llvm-baseline.md`（ADR-0006，Status 先 Candidate）
  - `manifests/components.lock.toml` 中 `llvm-project` 条目 `enabled = true` + 完整 40 字符 commit
  - `components/llvm-project/patches/series`（占位空文件；`manifest_check.py` 要求 enabled 组件的 `patch_series` 存在）
  - `Makefile` 的 `build-mc` 从 stub 替换为真实 `cmake` + `ninja` 构建
- 约束：commit 必须为完整 40 字符十六进制 SHA，不接受 tag/branch/短 SHA；ADR 先于 manifest；只改 `llvm-project` 条目，不动 qemu/gem5；`make manifest-check` 必须 PASS；ADR 内部引用用章节名（§Context 等），不写行号

## 背景（完整）

### 目标

为 v5 的 LLVM MC 开发选定一个可复现的 LLVM 上游 commit，完成：ADR-0006（记录选定理由）、组件锁启用、`build-mc` 真实构建目标。

### 设计理由

- **稳定性**：选 release/major 分支的最新 commit（或已稳定 RC），避免 main 分支 API 颠簸，保证跨开发机与 CI 可复现。
- **MC 框架**：确认所选 commit 已包含 `MCTargetDesc` / `MCCodeEmitter` / `MCELFObjectTargetWriter` / `ELFObjectWriter` 的稳定 API。
- **构建验证**：在 `make doctor` 环境（或开发容器）内能 `cmake -DLLVM_TARGETS_TO_BUILD=...` 无错完成 configure；DADAO 是全新 target，不复用 legacy toolchain 代码，所有补丁都应用在此干净上游 commit 上。

### 关键概念 / 数据

- ADR 格式：见 v5 `.tao/knowledge/adr-authoring.md`（`Status` / `Context` / `Decision` / `Rationale` / `Consequences`）。
- **Decision 必含字段**：选定的 LLVM 版本（major.minor）、完整 40 字符 commit SHA（不得用 tag/branch）、`llvm-project` GitHub commit URL（仅供人类参考，不做 lock 用途）。
- **Rationale 至少 3 点**：稳定性、MC 框架可用性、构建验证。
- **Consequences**：M1 所有 patch 针对此 commit 开发，commit 在 M1 期间不 bump；若发现严重 MC 框架 bug，通过 cherry-pick 处理并记录新 ADR，不整体 bump。
- `components.lock.toml` schema（`INFRA-003t`）：`format`、`work_root`、`[[component]]` 字段 `name`/`enabled`/`repository`/`commit`/`patch_series`/`role`；`[[component.source]]`（`name`/`url`，由 `INFRA-009t` 引入，见 ADR-0005）。
- `build-mc`：`cmake -G Ninja -B .work/build/llvm -S .work/source/llvm-project/llvm -DLLVM_TARGETS_TO_BUILD=DADAO -DLLVM_ENABLE_PROJECTS="" -DCMAKE_BUILD_TYPE=RelWithDebInfo -DLLVM_ENABLE_ASSERTIONS=ON`，随后 `ninja llvm-mc llvm-objdump llvm-lit FileCheck`；`LLVM_BUILD`/`LLVM_SRC` 用 `?=` 允许外部覆盖。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-005a-llvm-baseline.md`（完整转述：目标、三份交付物、约束、验收门、两轮 Architecture Review）。
- DADAO-0628：`docs/adr/0005-llvm-baseline.md`（内容溯源：Context/Decision/Rationale/Consequences；ADR 格式见 v5 `.tao/knowledge/adr-authoring.md`）。
- DADAO-0628：`manifests/components.lock.toml`、`Makefile`、`scripts/manifest_check.py`。

## 交付物

- `.tao/knowledge/adr-0006-llvm-baseline.md`：ADR-0006，覆盖 Context/Decision/Rationale/Consequences，含完整 40 字符 SHA 与至少 3 条 rationale；Status 先 Candidate，review 通过后 Accepted。
- `manifests/components.lock.toml`：`llvm-project` 条目 `enabled = true`、`commit = "<40 字符 SHA>"`；`repository` 不变；`[[component.source]]` 由 `INFRA-009t` 添加（本任务不重复添加）；`patch_series`/`role` 不变；qemu/gem5 条目不变。
- `Makefile`：`build-mc` 由 stub 替换为真实 `cmake`+`ninja`（并加入 `.PHONY` 与 `help`）。
- `components/llvm-project/patches/series`：占位空文件（`components/llvm-project/patches/` 目录 + 空 `series`）；`manifest_check.py` 对 enabled 组件强制要求 `patch_series` 存在，补丁正文由后续任务（`LLVM-003t` 起）追加。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **基线独立选定**：不得把 0628 的 `llvmorg-22.1.8` / `ca7933e47d3a3451d81e72ac174dcb5aa28b59d1` 直接当作 v5 既定基线。v5 须重新决定版本、重新验证 commit 可达性（`git ls-remote` / fetch 后 `git checkout`）并在 ADR-0006 记录理由；若沿用同一版本，须写明理由并重新验证。
- **ADR 落点**：v5 在 `.tao/knowledge/adr-0006-llvm-baseline.md`（0628 在 `docs/adr/`）。
- **构建路径**：v5 上游 checkout 为 `.work/source/llvm-project/llvm`（`INFRA-004t` 约定），构建为 `.work/build/llvm`；与 `INFRA-006t` 的 `LLVM_SRC` 默认值需统一（见「已知坑」）。
- **不复制补丁正文/编码数据**：0628 的 `components/llvm-project/patches/*` 属 0.4.1，本任务只选定上游 commit，不引入任何 0628 补丁。
- **措辞**：不使用按“阶段”命名的字段/目录；路线指向 DADAO-0628。

## 已知坑 / 结论

- **cmake configure 未验证是 0628 的遗留（N1）**：0628 完成区仅做 `git ls-remote`，未真实 configure。v5 本任务须在 `make fetch` 后真实执行 configure，并把输出（≥3 行）写入完成区。
- **tag/branch 不作为可复现基线**：enabled 组件必须有完整 40 位 commit，否则 `make manifest-check` 失败。
- **enabled 必须伴随 `patch_series`**：`manifest_check.py` 对 `enabled = true` 的组件强制要求 `components/<name>/patches/series` 存在；翻转 `enabled` 时必须同时创建占位空 `series`，否则 `make manifest-check` 失败。
- **ADR 先于 manifest**：ADR Status 先 Candidate 即可提交，架构师 review 后升 Accepted。
- **路径一致性**：~~`INFRA-006t` 的 `LLVM_SRC` 默认值写的是 `.work/llvm/llvm`，而 `INFRA-004t` 的 fetch 落点是 `.work/source/llvm`~~ **已解决（2026-09-16）**：`INFRA-006t:265,511` 已统一 `LLVM_SRC=.work/source/llvm-project/llvm`，与 `INFRA-004t` fetch 落点一致。本任务确认 `build-mc` 使用该路径即可。
- **不改其他组件条目**：只改 `llvm-project`。

## 参考

- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-005a-llvm-baseline.md`
- DADAO-0628：`.dadao/DADAO-0628/docs/adr/0005-llvm-baseline.md`
- DADAO-0628：`.dadao/DADAO-0628/manifests/components.lock.toml`
- DADAO-0628：`.dadao/DADAO-0628/Makefile`
- DADAO-0628：`.dadao/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/tasks/infra/INFRA-003t-manifest与锁系统.md`、`.tao/tasks/infra/INFRA-004t-组件获取与打补丁工具.md`、`.tao/tasks/infra/INFRA-006t-Makefile编排.md`

## 验收标准

1. `.tao/knowledge/adr-0006-llvm-baseline.md` 存在，含完整 40 字符 SHA 与至少 3 条 rationale，Status 为 Candidate（review 后 Accepted）
2. `manifests/components.lock.toml` 的 `llvm-project` 条目 `enabled = true`、`commit` 为完整 40 字符十六进制 SHA；qemu/gem5 条目未改
3. `Makefile` 的 `build-mc` 为真实 `cmake`+`ninja`（含 `.PHONY` 与 `help`）
4. `make manifest-check` PASS
5. 完成区含真实 `git checkout <SHA>` 与 `cmake` configure 输出（≥3 行）
6. `Makefile` 的 `build-mc` 中 `LLVM_SRC` 指向 `.work/source/llvm-project/llvm`（与 `INFRA-004t` 的 fetch 落点一致）
7. `components/llvm-project/patches/series` 存在（占位空文件）

## 完成区

**测试结果**：通过 7/7；DADAO configure 失败属预期行为（ADR-0007：target 尚未注册），真实构建待 `LLVM-003t`
**修改文件**：
1. `.tao/knowledge/adr-0006-llvm-baseline.md`（重写）
2. `manifests/components.lock.toml`（llvm-project 条目 enabled=true + commit）
3. `components/llvm-project/patches/series`（新建占位空文件）
4. `Makefile`（`build-mc`：ninja 命令添加 `llvm-lit FileCheck`；help 行去掉 stub 措辞；`-DLLVM_TARGETS_TO_BUILD=DADAO` 注释改指向 ADR-0007）

**验收结果**：逐条对应 7 条验收标准：

1. **ADR-0006 存在，含完整 40 字符 SHA 与至少 3 条 rationale，Status 为 Candidate**
   - 命令：`sed -n '1,60p' .tao/knowledge/adr-0006-llvm-baseline.md`
   - 输出：`**状态**：Candidate`、`**日期**：2026-09-17`、`**关联**：LLVM-002t`；Decision 含 D1（commit `6dfe1677ab8dffbc6ec13d53a1e0215d75147689`）、D2（SJTU 镜像）；Rationale 含 3 点（稳定性、MC 框架可用性、构建验证）+ 否决 22.1.8 理由

2. **manifests/components.lock.toml 的 llvm-project 条目 enabled=true、commit 为完整 40 字符十六进制 SHA；qemu/gem5 条目未改**
   - 命令：`grep -A5 'name = "llvm-project"' manifests/components.lock.toml`
   - 输出：`enabled = true`、`commit = "6dfe1677ab8dffbc6ec13d53a1e0215d75147689"`
   - 命令：`grep -A5 'name = "qemu"' manifests/components.lock.toml`
   - 输出：`enabled = false`、`commit = ""`（未改）

3. **Makefile 的 build-mc 为真实 cmake+ninja（含 .PHONY 与 help）**
   - 命令：`grep -A10 'build-mc:' Makefile`
   - 输出：`cmake -G Ninja -B $(LLVM_BUILD) -S $(LLVM_SRC) -DLLVM_TARGETS_TO_BUILD=DADAO ...`、`ninja -C $(LLVM_BUILD) llvm-mc llvm-objdump llvm-lit FileCheck`

4. **make manifest-check PASS**
   - 命令：`make manifest-check`
   - 输出：`enabled components: llvm-project`、`references: 2`、`manifest validation: PASS`

5. **完成区含真实 git checkout <SHA> 与 cmake configure 输出（≥3 行）**
   - git checkout 输出：`HEAD is now at 6dfe1677a [SLP]Fix crash in canBuildSplitNode on struct-typed scalars`
   - cmake configure（DADAO）输出：`CMake Error at CMakeLists.txt:1175 (message): The target 'DADAO' is not a core tier target...`（退出码 1）
   - cmake configure（X86 验证）输出：`-- Configuring done (20.0s)`、`-- Generating done (4.2s)`、`-- Build files have been written to: /tmp/opencode/LLVM-002t/build-x86`（退出码 0）

6. **Makefile 的 build-mc 中 LLVM_SRC 指向 .work/source/llvm-project/llvm**
   - 命令：`grep 'LLVM_SRC' Makefile`
   - 输出：`LLVM_SRC   ?= .work/source/llvm-project/llvm`

7. **components/llvm-project/patches/series 存在（占位空文件）**
   - 命令：`ls -la components/llvm-project/patches/series`
   - 输出：`-rw-rw-r-- 1 ubuntu ubuntu 0 Sep 17 10:53 components/llvm-project/patches/series`

**新发现/坑**：
1. DADAO target 未注册（属 LLVM-003t），LLVM 的 CMake 报「unknown target」，退出码 1。用 X86 target 验证 checkout 与宿主工具链可用（configure 成功，退出码 0）。
2. 浅镜像边界：`git describe`、跨 commit diff、完整历史遍历不可用；`sync_mirror` 的增量 `git fetch --prune` 在浅镜像上的语义受限。
3. `make fetch` 走 SJTU 镜像且短路（mirror already has commit），生成 `.work/source/llvm-project`。

**遗留问题**：
1. 待 LLVM-003t 注册 DADAO target 后，`build-mc` 才能真实构建（当前 cmake configure 失败）。
2. 浅镜像无完整历史，如需完整历史须 unshallow 或重建镜像。

**补记（2026-09-17，用户裁定 + ADR-0007）**：
DADAO configure 失败属**预期**——target 尚未注册，LLVM 的 `llvm/CMakeLists.txt` core-tier 校验必然拦截。注册通道已由用户定为「加入 `LLVM_ALL_TARGETS`」并固化于 ADR-0007（否决 `LLVM_EXPERIMENTAL_TARGETS_TO_BUILD` 通道）。`build-mc` 配方不变（仍用 `-DLLVM_TARGETS_TO_BUILD=DADAO`）。待 `LLVM-003t` 落地（补丁包含 `LLVM_ALL_TARGETS` 增项）后可真实构建。

**补记（2026-09-17，用户裁定 + LLVM-003t）**：
`llvm-lit` **不是** ninja 构建目标——它是 CMake `configure_file` 在 configure 阶段生成的 Python 脚本（`bin/llvm-lit`），无对应 ninja target。任务书第 41、100、116、164、181 行中 `ninja … llvm-lit …` 的表述**有误**，以本补记为准。`Makefile` 的 `build-mc` 已在 `LLVM-003t` 中改为 `ninja -C $(LLVM_BUILD) llvm-mc llvm-objdump FileCheck`（三者均为有效 ninja 目标）。

**返工记录（2026-09-17，第 1 轮 reviewer 验收 Needs Revision）**：
1. **B1（完成区口径错误）**：已修复。测试结果从 `6/7` 改为 `7/7`，说明 DADAO configure 失败属预期行为（ADR-0007），不属验收标准失败项。
2. **B2（Makefile 陈旧文案）**：已修复。help 行去掉 stub 措辞；注释改为指向 ADR-0007。
3. **#4（任务书 llvm 简写残留）**：已修复。逐行判断并修改 7 处 manifest 组件条目简写。
4. **#7（完成区 #1 引用命令不精确）**：已修复。命令从 `head -20` 改为 `sed -n '1,60p'`，覆盖 Decision/Rationale 内容。

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：ADR-0006、manifests/components.lock.toml、components/llvm-project/patches/series、Makefile、验证命令输出。

**发现**：

1. **ADR-0006 格式合规**：符合 adr-authoring.md 模板，包含 Context/Decision/Rationale/Consequences/状态说明。Decision 严格按用户确认的 D1/D2 写入，无增删改写。
2. **manifests/components.lock.toml 正确**：只改 llvm-project 条目（enabled=true、commit=6dfe1677...），qemu/gem5 未动。
3. **components/llvm-project/patches/series 存在**：空文件，满足 manifest_check.py 对 enabled 组件的要求。
4. **Makefile build-mc 更新**：ninja 命令添加 llvm-lit FileCheck，与任务要求一致。
5. **验证命令全部执行**：
   - `make manifest-check` PASS
   - `make fetch` 走 SJTU 镜像且短路，生成 .work/source/llvm-project
   - `git rev-parse HEAD` == 6dfe1677ab8dffbc6ec13d53a1e0215d75147689
   - cmake configure（DADAO）失败（退出码 1），符合预期（DADAO target 未注册）
   - cmake configure（X86）成功（退出码 0），证明 checkout 与宿主工具链可用
   - `make check` 通过（退出码 0），154 条 DATA COVERAGE GAP 为已知 report-only 项
6. **浅镜像边界已记录**：在 ADR-0006 Consequences 和完成区新发现/坑中均已说明。

**判决**：所有发现均为正面，无需修复。任务可标为「待验收」。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| ADR-0006 格式合规 | ✅已修 | 无（初始实现即正确） | 读取文件确认模板结构 |
| manifest 锁正确 | ✅已修 | 无 | grep 确认 enabled=true、commit 正确 |
| series 占位存在 | ✅已修 | 无 | ls 确认文件存在且为空 |
| Makefile build-mc 更新 | ✅已修 | 无 | grep 确认 ninja 包含 llvm-lit FileCheck |
| 验证命令全部执行 | ✅已修 | 无 | 完成区记录真实输出 |
| 浅镜像边界已记录 | ✅已修 | 无 | ADR-0006 Consequences §5 |

### 第 1 轮 reviewer 验收（Needs Revision）

**审查结果**：Needs Revision

**阻塞项**：
1. **B1（完成区口径错误）**：第 95 行 `**测试结果**：通过 6/7；失败原因：DADAO target 未注册导致 cmake configure 失败（待 LLVM-003t）`。→ 改为 `7/7`：7 条验收标准实际全部满足；DADAO configure 失败是**用户已裁定的预期行为**（ADR-0007：target 尚未注册，注册通道 = 加入 `LLVM_ALL_TARGETS`），**不属任何验收标准的失败项**；真实构建待 `LLVM-003t`。
2. **B2（Makefile 陈旧文案，与交付目标矛盾）**：
   - `Makefile:43`：`@echo "  make build-mc        Build LLVM MC tools (stub until llvm commit is locked)"` → commit 已锁（`enabled=true` + 40 位 SHA），文案失真。
   - `Makefile:72-73`：`# -DLLVM_TARGETS_TO_BUILD=DADAO is a placeholder: the exact target name is` / `# registered by the llvm module (0.5.3) and must be confirmed there.` → target 名已由 **ADR-0007 D1** 固化为 `DADAO`。

**非阻塞项**：
1. **#4（任务书 `llvm` 简写残留）**：`.tao/tasks/llvm/LLVM-002t-LLVM组件基线.md` 中凡指**manifest 组件条目**的 `` `llvm` 条目 `` / `` `llvm` 的 `` 等简写，改为 `llvm-project`。
2. **#7（完成区 #1 引用命令不精确）**：完成区第 1 条用 `head -20 .tao/knowledge/adr-0006-llvm-baseline.md`，只覆盖到 Context，无法证明其声称的 D1 commit 与 rationale 内容。

### 第 1 轮返工

**返工时间**：2026-09-17

**处置**：

| 项目 | 处置 | 改了什么 | 复验证据 |
|------|------|---------|---------|
| B1（完成区口径错误） | ✅已修 | 第 95 行改为 `通过 7/7；DADAO configure 失败属预期行为（ADR-0007：target 尚未注册），真实构建待 LLVM-003t` | 读取文件确认口径与逐条明细一致 |
| B2（Makefile 陈旧文案） | ✅已修 | 1. help 行去掉 stub 措辞（`Build LLVM MC tools (requires llvm-project enabled)`）；2. 72-73 注释改为指向 ADR-0007（`DADAO is registered by adding it to LLVM_ALL_TARGETS in llvm/CMakeLists.txt (see ADR-0007). Until LLVM-003t lands that patch, cmake configure will fail.`） | `grep -n 'stub\|placeholder' Makefile` 无 build-mc 相关残留；`git diff -- Makefile` 确认只改文案未改命令 |
| #4（任务书 llvm 简写残留） | ✅已修 | 逐行判断并修改 7 处：第 14/17/20/52/71/86/108 行的 `'llvm' 条目` / `只改 'llvm'` 改为 `'llvm-project' 条目` / `只改 'llvm-project'` | `grep -n "llvm" .tao/tasks/llvm/LLVM-002t-LLVM组件基线.md` 确认无 manifest 组件条目简写残留 |
| #7（完成区 #1 引用命令不精确） | ✅已修 | 命令从 `head -20` 改为 `sed -n '1,60p'`，覆盖 Decision/Rationale 内容 | 读取文件确认命令更新 |

**复验结果**：
1. `make manifest-check`：PASS（exit=0）
2. `make check`：PASS（exit=0），154 条 DATA COVERAGE GAP 为已知 report-only 项
3. `grep -n 'stub\|placeholder' Makefile`：无 build-mc 相关残留（仅 build-qemu/build-gem5 的 stub 文案）
4. `git diff -- Makefile`：确认除文案外**未改** `build-mc` 的命令与守卫
5. `git status --short`：显示任务文件、Makefile、manifest 等已修改

### 第 2 轮 reviewer 验收

**验收者**：reviewer
**时间**：2026-09-17
**判决**：**Accepted**（7/7 条验收标准满足）

**第 1 轮 4 项复核**：B1 ✅（第 95 行已改 `7/7`，与逐条明细一致）；B2 ✅（`grep -n 'stub\|placeholder' Makefile` 仅剩 qemu/gem5 的合法文案；`git diff -- Makefile` 确认 `build-mc` 的 cmake 命令与 `component-enabled` 守卫逐行未变）；#4 ✅（7 处组件条目简写改为 `llvm-project`，且 `**模块**：llvm`/`llvm-mc`/`adr-0006-llvm-baseline.md`/路径等**未被误改**）；#7 ✅（命令改为 `sed -n '1,60p'`，输出确实覆盖 D1 commit 与 Rationale）。

**独立重跑**：`make manifest-check` exit=0；`make check` exit=0（154 gap report-only、`178/178`）；`git rev-parse HEAD` = `6dfe1677…`；`series` 0 字节；cmake DADAO exit=1（预期）/ X86 exit=0（`Configuring done (20.1s)`、`Generating done (4.2s)`，与完成区 20.0s/4.2s 属计时抖动）；`make build-qemu`/`build-gem5` 仍拒绝（exit=2）；qemu/gem5 条目与 HEAD 逐字段相同；ADR-0006/0007 的 D1/D2 与用户确认值逐字一致且未被返工误改。

**非阻塞观察**：完成区「修改文件」对 `Makefile` 的描述不完整（只提 ninja 命令）；任务书 `**依赖**` 未含 `INFRA-013t`（规划元数据）。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-17
**判决**：**确认 Accepted**；7 条验收标准独立复核全部满足。

**ADR 终审**：`adr-0006` 满足 Candidate→Accepted 条件（D1/D2 与用户确认值逐字一致、Rationale 4 点含被否决方案、Consequences 含浅镜像边界、reviewer 两轮通过）→ 由主会话置 `Accepted`。`adr-0007` **保持 `Candidate`**：其 D1 的有效性取决于 `LLVM-003t` 的 0001 补丁能否成功加入 `LLVM_ALL_TARGETS` 并使 `build-mc` 真实构建通过，当前尚未验证，过早升 Accepted 违反 `adr-authoring.md` 流程。

**跨文件一致性**：全仓 grep 6 种旧标识符/陈旧表述模式（`source/llvm[^-]`、`components/llvm/`、`.cache/llvm[^-]`、`name = "llvm"`、`stub/placeholder` 与 `build-mc`、`llvmorg-22.1.8`/`ca7933e47d3a`）**全部无命中**。

**跨模块**：`LLVM-003t` 与 ADR-0007 一致（三处均为 `llvm/CMakeLists.txt`）；`qemu`/`gem5`/`integ` 未被破坏。

**新发现（非阻塞）**：
- **F1**：ADR-0006 Rationale 第 3 点原写「可通过 `git ls-remote` 验证可达性」，与实测方式（浅镜像 clone + checkout + cmake configure）不符 → 已由主会话改写为实测描述（置 Accepted 之前）。
- **F2**：ADR-0006 末尾缺换行符 → 已补。
- **F3**：`adr-0005` L22 的 TOML 示例仍用 `name = "llvm"` → 属已 `Accepted` ADR 的历史示例，按 `adr-authoring.md` 不改。
- **#5**：`LLVM-002t` 的 `依赖` 应补 `INFRA-013t`（`component-enabled,llvm-project`、`components/llvm-project/patches/series` 均源自它）→ 已补；`LLVM-001k` 任务表同步。
- **⑧**：完成区「修改文件」对 `Makefile` 的描述不完整 → 已补全（help 行 + 注释）。

**ADR 提醒**：本次无命中判据而未立 ADR 的决策。

### 收尾

- `adr-0006-llvm-baseline.md` 置 `Accepted`（2026-09-17）；`adr-0007` 保持 `Candidate`（待 `LLVM-003t` 验证）。
- F1/F2/#5/⑧ 由**主会话**直接修正（收尾）；F3 不改（已 Accepted 的历史示例）。
- `**状态**` 置 `已验证`（2026-09-17）。
- `MEMORY.md`、`changelog.md` 已同步。
