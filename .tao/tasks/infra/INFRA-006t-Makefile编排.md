# INFRA-006t: Makefile 编排

**模块**：infra
**项目里程碑**：M1
**依赖**：`INFRA-004t`、`INFRA-005t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`tools/infra/` 下的 manifest/doctor/status/fetch/apply_series/clean_work 工具
- 输出：顶层 `Makefile`
- 约束：Make 为稳定用户接口，实际逻辑委托给 Python 标准库脚本；构建目标对未就绪组件以 stub 形式存在；不写死绝对路径

## 背景（完整）

### 目标

以 Make 作为统一入口编排 fetch / 打补丁 / 构建 / 容器等操作，使干净 checkout 上可一键准备与构建。

### 设计理由

- ADR-0002（v5：`.tao/knowledge/adr-0002-build-orchestration.md`）：**Use Make as the stable user interface and Python standard-library scripts for manifest processing.**
- 每个构建目标先依赖 `manifest-check`，保证只在锁有效时构建。
- 构建产物落在 `.work/` 下（`QEMU_BUILD` / `LLVM_BUILD` 等变量可覆盖）。

### 关键概念 / 数据

- 0628 `Makefile` 结构：`PYTHON ?= python3`、`.DEFAULT_GOAL := help`、`.PHONY` 列表、`help` 打印所有目标。
- 关键目标与依赖（0628）：
  - `manifest-check` → `python3 tools/infra/manifest_check.py`
  - `doctor` → `python3 tools/infra/doctor.py`
  - `status` → `python3 tools/infra/status.py`
  - `fetch: manifest-check` → `python3 tools/infra/fetch.py`
  - `apply-series: manifest-check` → `python3 tools/infra/apply_series.py`
  - `prepare: fetch apply-series`
  - `build-qemu: manifest-check` → `cd .work/qemu && ./configure --target-list=dadao-softmmu --enable-tcg --disable-werror` 后 `make -j$(nproc)`
  - `build-mc: manifest-check` → `cmake -G Ninja -B .work/build/llvm -S .work/llvm/llvm -DLLVM_TARGETS_TO_BUILD=DADAO -DLLVM_ENABLE_PROJECTS="" -DCMAKE_BUILD_TYPE=RelWithDebInfo -DLLVM_ENABLE_ASSERTIONS=ON` 后 `ninja llvm-mc llvm-objdump`
  - `docker-image` → `docker build -t <tag> containers/dev`
  - `clean-work` → `python3 tools/infra/clean_work.py`
  - `check: manifest-check ...`（仓库级结构检查）
- 路径变量（0628）：`QEMU_SRC ?= .work/qemu`、`QEMU_BUILD ?= .work/build/qemu`、`LLVM_BUILD ?= .work/build/llvm`、`LLVM_SRC ?= .work/llvm/llvm`。

### 上游引用

- DADAO-0628 `Makefile`（完整转述见上；v5 只取编排骨架，不复制 0628 的 picolibc/musl/check-wiki 等后续阶段目标）。
- DADAO-0628 `docs/adr/0002-build-orchestration.md`：Make 用户接口 + Python manifest 处理。
- DADAO-0628 `docs/development-roadmap.md`（M0 段）：仓库检查可在干净主机或开发容器运行。

## 交付物

- `Makefile`（顶层）：
  - 默认目标 `help`，打印可用目标。
  - 基础设施目标：`manifest-check`、`doctor`、`status`、`fetch`、`fetch-refs`、`apply-series`、`prepare`、`clean-work`。
  - 构建目标：`build-mc`、`build-qemu`、`build-gem5`。
  - 容器目标：`docker-image`（`docker build -t dadao-v5-dev:local containers/dev`）、`docker-shell`（`docker run --rm -it -v "$(PWD):/workspace" dadao-v5-dev:local /bin/bash`）。
  - `check`：显式包含 `manifest-check` + `python3 -m compileall -q scripts`（v5 infra M1 范围；不含 0628 的 `validate-encoding`/`check-wiki-*`/`check-qfc` 等后续阶段目标）。
  - **stub 说明**：`build-gem5`、`build-qemu`、`build-mc` 在对应组件 commit 未锁定（`enabled = false`）时，应明确提示"组件未启用/commit 待定"并以非静默方式失败或跳过，不得假装成功。`build-gem5` 与 `docker-shell` 为 v5 新增，先以占位/骨架形式存在，待 gem5 模块与容器任务确定具体命令。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- 无 ISA 相关差异（基础设施，与 ISA 版本无关）；但 `build-mc` 的 target 名与 0.5.3 的 LLVM target 注册在 `llvm` 模块确定，本任务保持 `DADAO` 占位并注明待确认。
- 目标范围收窄：0628 Makefile 含 `build-picolibc` / `build-musl` / `check-wiki-*` / `check-qfc` 等后续阶段目标；v5 infra M1 只保留 `fetch`/`apply-series`/`prepare`/`build-mc`/`build-qemu`/`build-gem5`/`docker-image`/`docker-shell` 及基础检查。
- `build-gem5` 与 `docker-shell` 为 v5 新增：0628 Makefile 无 `build-gem5`（gem5 通过 `tests/scripts/run_gem5_test.py` 驱动）、无 `docker-shell`。
- 容器 tag：`dadao-v5-dev:local`（0628 为 `dadao-0628-dev:local`）。

## 已知坑 / 结论

- 每个构建目标先依赖 `manifest-check`，避免在锁失效时构建。
- 未启用组件的构建目标必须是显式 stub（提示并失败/跳过），不能静默成功。
- `help` 是默认目标，`make` 不带参数应打印帮助。
- 构建产物全部在 `.work/` 下，且 `.work/` 被 git 忽略。

## 参考

- DADAO-0628：`.work/DADAO-0628/Makefile`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0002-build-orchestration.md`
- DADAO-0628：`.work/DADAO-0628/docs/development-roadmap.md`
- DADAO-0628：`.work/DADAO-0628/containers/dev/Dockerfile`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `make`（默认）打印 `help`，列出全部目标
2. `make manifest-check` / `make doctor` / `make status` / `make clean-work` / `make fetch-refs` 可正常调用对应脚本
3. `make prepare` 正确串联 `fetch` + `apply-series`
4. `build-mc` / `build-qemu` / `build-gem5` 在组件未启用时给出明确提示且不假装成功
5. `make docker-image` / `make docker-shell` 指向 `containers/dev` 与 `dadao-v5-dev:local`

## 完成区

**测试结果**：通过 15/15 目标 + 2 项 `make -n` 校验；失败原因：无（三个 build stub 与两个 docker 目标的非零退出为**预期**行为，非缺陷）。

**修改文件**：
- `Makefile`（新增，顶层；唯一交付物）

**验收结果**（真实命令 + 真实退出码；完整输出见 `.tao/logs/INFRA-006t-*.log`）：

1. **默认目标 `make` / `make help`** — 通过，**exit=0**
```
$ make
DADAO-v5 orchestration

  make help            Show this help
  make manifest-check  Validate specification/component/reference locks
  make doctor          Check host or container build prerequisites
  make status          Show locked components and references
  make fetch           Fetch enabled components at exact commits
  make fetch-refs      Fetch locked reference repositories
  make apply-series    Apply ordered patch series to fetched sources
  make prepare         Fetch enabled components and apply their patch series
  make build-mc        Build LLVM MC tools (stub until llvm commit is locked)
  make build-qemu      Configure and compile QEMU (stub until qemu commit is locked)
  make build-gem5      Build gem5 (stub; command owned by the gem5 module)
  make docker-image    Build the development image (dadao-v5-dev:local)
  make docker-shell    Open a shell in the development image
  make clean-work      Remove generated .work content only
  make check           Run repository-level structural checks
exit=0
```
（`.PHONY` 共 15 个目标，help 全部列出；`make help` 同输出 exit=0）

2. **`manifest-check` / `doctor` / `status` / `fetch` / `apply-series` / `fetch-refs`** — 全部通过，**exit=0**
```
$ make manifest-check
enabled components: none
references: 2
manifest validation: PASS
exit=0

$ make doctor
required
  git        OK       git version 2.43.0
  make       OK       GNU Make 4.3
  cmake      OK       cmake version 3.28.3
  python3    OK       Python 3.12.3
native
  ninja      OK       1.11.1
  clang      OK       Ubuntu clang version 18.1.3 (1ubuntu1)
container
  docker     OK       Docker version 29.1.3, build 29.1.3-0ubuntu3~24.04.2
doctor: PASS (native build path available)
exit=0

$ make status
Components
  llvm     disabled UNSET
  qemu     disabled UNSET
  gem5     disabled UNSET
References
  dadao-0628       MATCH   dirty=0   2d270604b778d609e1a09b4047271b5309005ffc
  dadao            MATCH   dirty=0   f9bde0481668ffab325db8d8c5d8c4cc791c6232
exit=0

$ make fetch
fetch: no components enabled; accept baseline ADRs first
exit=0

$ make apply-series
apply-series: no components enabled
exit=0

$ make fetch-refs
fetch-refs: dadao-0628 already at 2d270604b778; skipping
fetch-refs: dadao already at f9bde0481668; skipping
exit=0
```

3. **`make prepare` 串联 fetch + apply-series** — 通过，**exit=0**
```
$ make prepare
enabled components: none
references: 2
manifest validation: PASS
fetch: no components enabled; accept baseline ADRs first
apply-series: no components enabled
exit=0
```
（`manifest-check` 由 `fetch`/`apply-series` 共享，只运行一次；顺序为先 fetch 后 apply-series）

4. **`check` = manifest-check + compileall** — 通过，**exit=0**
```
$ make check
enabled components: none
references: 2
manifest validation: PASS
repository checks: PASS
exit=0
```

5. **build stub：组件未启用时明确提示且不假装成功** — 通过，**exit=2（make 对 recipe 失败的标准退出码；底层命令 `exit 1`）**
```
$ make build-mc
enabled components: none
references: 2
manifest validation: PASS
build-mc: component 'llvm' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success
make: *** [Makefile:73: build-mc] Error 1
exit=2

$ make build-qemu
build-qemu: component 'qemu' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success
make: *** [Makefile:83: build-qemu] Error 1
exit=2

$ make build-gem5
build-gem5: component 'gem5' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success
make: *** [Makefile:98: build-gem5] Error 1
exit=2
```
**enabled 分支隔离验证**（合成树 `/tmp/opencode/INFRA-006t/enabled-tree`，未污染真实仓库）：
```
# llvm enabled=true：guard 放行，cmake 真实执行（证明 stub 不是永久硬失败）
$ make build-mc LLVM_SRC=/nonexistent-llvm LLVM_BUILD=/tmp/opencode/INFRA-006t/enabled-build
enabled components: llvm
references: 2
manifest validation: PASS
cmake -G Ninja -B /tmp/opencode/INFRA-006t/enabled-build -S /nonexistent-llvm \
  -DLLVM_TARGETS_TO_BUILD=DADAO ...
CMake Error: The source directory "/nonexistent-llvm" does not exist.
make: *** [Makefile:71: build-mc] Error 1   # guard 未触发（grep "not enabled" = 0）
# qemu disabled：guard 拦截
$ make build-qemu
build-qemu: component 'qemu' is not enabled / commit pending ...; refusing to fake success
make: *** [Makefile:83: build-qemu] Error 1
```

6. **`make clean-work`**（**隔离树** `/tmp/opencode/INFRA-006t/clean-work-tree`，避免删除真实 `.work/DADAO*`）— 通过，**exit=0**
```
$ make clean-work
clean-work: removed /tmp/opencode/INFRA-006t/clean-work-tree/.work
exit=0
# 验证：.work 已删除；.cache/refs/dummy.git 完整保留
.work exists?  -> REMOVED
.cache intact? -> .cache/refs/dummy.git/objects.pack 仍在
```
真实参考树未受影响：`git -C .work/DADAO-0628 rev-parse HEAD` = `2d270604b778…`（=锁），`.work/DADAO` = `f9bde0481668…`（=锁）。

7. **`docker-image` / `docker-shell` 指向正确** — 通过（命令指向经 `make -n` 确认为真；真实运行因外部前提失败）
```
$ make -n docker-image
docker build -t dadao-v5-dev:local containers/dev
$ make -n docker-shell
docker run --rm -it -v "/mnt/tao/DADAO-v5:/workspace" dadao-v5-dev:local /bin/bash

# 真实运行（当前必然失败，原因非本任务）：
$ make docker-image
docker build -t dadao-v5-dev:local containers/dev
unable to prepare context: path "containers/dev" not found
make: *** [Makefile:106: docker-image] Error 1
exit=2   # containers/dev 属 INFRA-007t（未开始）
$ make docker-shell
docker run --rm -it -v "/mnt/tao/DADAO-v5:/workspace" dadao-v5-dev:local /bin/bash
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
make: *** [Makefile:109: docker-shell] Error 1
exit=2   # docker daemon socket 权限（环境限制）
```

**新发现/坑**：
- **stub 的退出码语义**：recipe 内 `exit 1` → GNU Make 整体退出 **2**（make 对 recipe 失败的固定退出码）。这是"非静默失败"的正常表现，验收时应按"非零 + 明确提示"判定，勿误认为脚本返回 2。
- **`make clean-work` 会删除整个 `.work/`，含真实 `.work/DADAO*` 参考工作树**：测试删除行为必须在隔离树进行（本任务如此）；真实参考树可从 `.cache/refs/` 离线重建，但不应无故删除。
- **v5 与 0628 路径约定不同**：v5 `LLVM_SRC=.work/source/llvm/llvm`、`QEMU_SRC=.work/source/qemu`（0628 为 `.work/llvm/llvm`、`.work/qemu`）；已按 `LLVM-002t`/`QEMU-002t` 与 `INFRA-004t` fetch 落点统一。
- **`component-enabled` 内联 python 检查**：Make 的 `$(call)` 函数体内逗号不作为参数分隔符，`$(call component-enabled,llvm)` 正常；已用隔离树分别验证 enabled（放行→cmake 执行）与 disabled（拦截）两分支，确认 stub 非永久硬失败。
- **`PWD` 在 GNU Make 中来自环境变量**，`$(PWD)` 可用；`make -n` 确认展开为仓库绝对路径（0628 同）。
- **`QEMU_BUILD` 声明但未使用**：QEMU 沿用 0628 的 in-tree 构建（`cd $(QEMU_SRC) && ./configure`），`QEMU_BUILD` 保留为可覆盖变量占位。
- **`fetch-refs` 依赖 `manifest-check`**：`manifest_check.py` 同时校验 `references.lock.toml`，故该依赖逻辑自洽（任务书未显式要求，属合理增强）。

**遗留问题**：
- `docker-image` 依赖 `containers/dev/Dockerfile`（`INFRA-007t`，未开始），当前真实运行必然失败；本任务仅保证目标命令指向正确（验收标准 5 只要求"指向"）。
- `build-gem5` 构建命令待 gem5 模块确定；当前即便 gem5 `enabled=true` 也以占位消息失败（不假装成功）。
- `build-mc` 的 `-DLLVM_TARGETS_TO_BUILD=DADAO` 为占位，target 名待 llvm 模块（0.5.3）确认；已在 Makefile 注明。
- 三个组件锁仍 `enabled=false`，`build-mc`/`build-qemu` 的**真实构建路径**未跑（无可用 commit）；已用隔离合成树验证 guard 的 enabled 分支会放行到真实 cmake 调用。

## 审阅记录

### 第 1 轮 engineer 自审（自主自审，嵌套受限）

**自审者**：engineer
**时间**：2026-09-12
**方式**：**自主自审（嵌套受限）** —— 尝试 `task(general)` 做代码级 review 返回 `Subagent depth limit reached (1)`，按 engineer 规则降级为逐行审查 Makefile + 重跑全部验收命令。

#### 逐行审查发现

| # | finding | 严重度 | 处置 | 改了什么 / 证据 |
|---|---------|--------|------|-----------------|
| E1-1 | `help` 未列出 `help` 目标本身，验收标准 1 要求"列出全部目标" | 中 | ✅已修 | 在 help 首行加 `make help  Show this help`；`make` 输出已含 15 个目标（含 help），exit=0 |
| E1-2 | `build-mc` 的 `DADAO` target 名未注明为占位（任务书要求"注明待确认"） | 低 | ✅已修 | 在 `build-mc` 上方加注释：`-DLLVM_TARGETS_TO_BUILD=DADAO` 为占位，待 llvm 模块确认 |
| E1-3 | `fetch-refs` 依赖 `manifest-check` 是否超出任务要求？ | 低 | ❌不修 | 属合理增强：`manifest_check.py` 校验 `references.lock.toml`；不改变验收语义，已记录 |
| E1-4 | `QEMU_BUILD`/`GEM5_SRC`/`GEM5_BUILD` 声明但未使用 | 低 | ❌不修 | 与任务书「路径变量」及 0628 一致（QEMU_BUILD 为可覆盖占位）；gem5 为占位目标 |
| E1-5 | `$(call component-enabled,...)` 的 shell/Make 引号是否可靠？ | 高 | ✅验证 | 隔离树双分支实测：enabled→cmake 执行（无 "not enabled"）；disabled→拦截；函数体逗号未破坏 `$(call)` |
| E1-6 | stub 退出码是否为"非静默失败"？ | 中 | ✅验证 | `exit 1` → make 退出 2 + `Error 1` + 明确提示，无 "PASS" 输出 |
| E1-7 | 是否写死绝对路径 / 残留 0628 目标？ | 中 | ✅验证 | `grep -nE "/mnt/\|0628\|picolibc\|musl\|check-wiki\|check-qfc" Makefile` → none |
| E1-8 | `make check` 是否含 manifest-check + compileall？ | 中 | ✅验证 | 日志：先 `manifest validation: PASS`，后 `repository checks: PASS` |
| E1-9 | `make clean-work` 测试是否误删真实参考树？ | 高 | ✅验证 | 仅隔离树运行；真实 `.work/DADAO*` HEAD 仍等于锁 |
| E1-10 | `.PHONY` 是否覆盖全部目标？ | 中 | ✅验证 | 15 个目标全部列入 `.PHONY`，与 help 一致 |

#### 防造假核对

- 所有验收命令为真实执行，输出 `tee`/重定向落盘至 `.tao/logs/INFRA-006t-*.log`（17 个文件）。
- `make clean-work` 在隔离树 `/tmp/opencode/INFRA-006t/clean-work-tree` 执行，未触碰真实 `.work/`。
- enabled 分支隔离树 `/tmp/opencode/INFRA-006t/enabled-tree`，未修改真实 `manifests/`。
- 未执行 `git commit`；`git status --short` 仅 `?? Makefile`（无其它改动）。

#### 验收标准逐条自审

1. `make`（默认）打印 `help`，列出全部目标 —— ✅ 通过（15/15，含 help，exit=0）
2. `manifest-check`/`doctor`/`status`/`clean-work`/`fetch-refs` 正常调用对应脚本 —— ✅ 通过（均 exit=0；clean-work 隔离树验证）
3. `make prepare` 正确串联 `fetch` + `apply-series` —— ✅ 通过（顺序正确，exit=0）
4. `build-mc`/`build-qemu`/`build-gem5` 未启用时明确提示且不假装成功 —— ✅ 通过（明确提示 + 非零退出；enabled 分支隔离验证 guard 会放行）
5. `docker-image`/`docker-shell` 指向 `containers/dev` 与 `dadao-v5-dev:local` —— ✅ 通过（`make -n` 确认命令；真实失败因 `containers/dev` 缺失（INFRA-007t）与 docker socket 权限）

#### 判决

**自主自审通过**：2 项 finding 已修（E1-1、E1-2），其余为设计选择/已验证，无未修缺陷。任务状态置 `待验收`，交主会话 `/complete` 由 reviewer 独立验收。

### 第 1 轮 reviewer 验收

**审查者**：reviewer
**时间**：2026-09-12
**方式**：独立重跑全部验收命令，不采信完成区。

#### 重跑记录（真实终端输出 + 退出码）

**1. `make`（默认目标 = help）— exit=0 ✅**
```
$ make
DADAO-v5 orchestration

  make help            Show this help
  make manifest-check  Validate specification/component/reference locks
  make doctor          Check host or container build prerequisites
  make status          Show locked components and references
  make fetch           Fetch enabled components at exact commits
  make fetch-refs      Fetch locked reference repositories
  make apply-series    Apply ordered patch series to fetched sources
  make prepare         Fetch enabled components and apply their patch series
  make build-mc        Build LLVM MC tools (stub until llvm commit is locked)
  make build-qemu      Configure and compile QEMU (stub until qemu commit is locked)
  make build-gem5      Build gem5 (stub; command owned by the gem5 module)
  make docker-image    Build the development image (dadao-v5-dev:local)
  make docker-shell    Open a shell in the development image
  make clean-work      Remove generated .work content only
  make check           Run repository-level structural checks
exit=0
```
15 个 `.PHONY` 目标全部在 help 中列出，与 Makefile 第 23-24 行一致。

**2. `make manifest-check` — exit=0 ✅**
```
enabled components: none
references: 2
manifest validation: PASS
exit=0
```

**3. `make doctor` — exit=0 ✅**
```
required
  git        OK       git version 2.43.0
  make       OK       GNU Make 4.3
  cmake      OK       cmake version 3.28.3
  python3    OK       Python 3.12.3
native
  ninja      OK       1.11.1
  clang      OK       Ubuntu clang version 18.1.3 (1ubuntu1)
container
  docker     OK       Docker version 29.1.3, build 29.1.3-0ubuntu3~24.04.2
doctor: PASS (native build path available)
exit=0
```

**4. `make status` — exit=0 ✅**
```
Components
  llvm     disabled UNSET
  qemu     disabled UNSET
  gem5     disabled UNSET
References
  dadao-0628       MATCH   dirty=0   2d270604b778d609e1a09b4047271b5309005ffc
  dadao            MATCH   dirty=0   f9bde0481668ffab325db8d8c5d8c4cc791c6232
exit=0
```

**5. `make fetch` — exit=0 ✅**
```
enabled components: none
references: 2
manifest validation: PASS
fetch: no components enabled; accept baseline ADRs first
exit=0
```

**6. `make apply-series` — exit=0 ✅**
```
enabled components: none
references: 2
manifest validation: PASS
apply-series: no components enabled
exit=0
```

**7. `make fetch-refs` — exit=0 ✅**
```
enabled components: none
references: 2
manifest validation: PASS
fetch-refs: dadao-0628 already at 2d270604b778; skipping
fetch-refs: dadao already at f9bde0481668; skipping
exit=0
```

**8. `make prepare`（串联 fetch + apply-series）— exit=0 ✅**
```
enabled components: none
references: 2
manifest validation: PASS
fetch: no components enabled; accept baseline ADRs first
apply-series: no components enabled
exit=0
```
顺序正确：manifest-check → fetch → apply-series；manifest-check 仅运行一次（Make 依赖优化）。

**9. `make check`（manifest-check + compileall）— exit=0 ✅**
```
enabled components: none
references: 2
manifest validation: PASS
repository checks: PASS
exit=0
```

**10. `make build-mc`（组件未启用）— exit=2 ✅**
```
enabled components: none
references: 2
manifest validation: PASS
build-mc: component 'llvm' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success
make: *** [Makefile:73: build-mc] Error 1
exit=2
```

**11. `make build-qemu`（组件未启用）— exit=2 ✅**
```
enabled components: none
references: 2
manifest validation: PASS
build-qemu: component 'qemu' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success
make: *** [Makefile:86: build-qemu] Error 1
exit=2
```

**12. `make build-gem5`（组件未启用）— exit=2 ✅**
```
enabled components: none
references: 2
manifest validation: PASS
build-gem5: component 'gem5' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success
make: *** [Makefile:101: build-gem5] Error 1
exit=2
```

**13. `make -n docker-image` — 命令指向正确 ✅**
```
$ make -n docker-image
docker build -t dadao-v5-dev:local containers/dev
exit=0
```

**14. `make -n docker-shell` — 命令指向正确 ✅**
```
$ make -n docker-shell
docker run --rm -it -v "/mnt/tao/DADAO-v5:/workspace" dadao-v5-dev:local /bin/bash
exit=0
```

**真实 docker 运行（预期失败）：**
```
$ make docker-image
docker build -t dadao-v5-dev:local containers/dev
unable to prepare context: path "containers/dev" not found
make: *** [Makefile:109: docker-image] Error 1
exit=2   # containers/dev 属 INFRA-007t（未开始）

$ make docker-shell
docker run --rm -it -v "/mnt/tao/DADAO-v5:/workspace" dadao-v5-dev:local /bin/bash
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
make: *** [Makefile:112: docker-shell] Error 1
exit=2   # docker socket 权限（环境限制）
```

**15. `make clean-work`（隔离树验证）— exit=0 ✅**
隔离树：`/tmp/opencode/INFRA-006t-review/`（含 `.work/`、`.cache/`、`Makefile`、`tools/infra/`、`manifests/`）
```
$ cd /tmp/opencode/INFRA-006t-review && make clean-work
clean-work: removed /tmp/opencode/INFRA-006t-review/.work
exit=0
```
验证：`.work` 已删除；`.cache/` 完整保留。真实参考树未受影响：
```
$ git -C .work/DADAO-0628 rev-parse HEAD
2d270604b778d609e1a09b4047271b5309005ffc   (=锁)
$ git -C .work/DADAO rev-parse HEAD
f9bde0481668ffab325db8d8c5d8c4cc791c6232   (=锁)
```

#### 路径约定核验

`LLVM_SRC = .work/source/llvm/llvm`、`QEMU_SRC = .work/source/qemu` — 与 `tools/infra/fetch.py` 中 `source_root = work_root / "source"` 的落点一致（`work_root` 默认 `.work`）。不是 0628 的 `.work/llvm/llvm`、`.work/qemu`。✅

#### 回归核验

```
$ python3 -m compileall -q scripts
exit=0

$ python3 tools/infra/manifest_check.py
enabled components: none
references: 2
manifest validation: PASS
exit=0
```

#### component-enabled guard 隔离验证

用隔离树 `/tmp/opencode/INFRA-006t-review/enabled-tree`（含 `enabled=true` 的 `components.lock.toml`）：
```
$ python3 -c "import tomllib,sys;m=tomllib.load(open('manifests/components.lock.toml','rb'));sys.exit(0 if any(c['name']=='llvm' and c.get('enabled') for c in m.get('component',[])) else 1)"; echo $?
0    # guard 通过（enabled=true）

$ python3 -c "import tomllib,sys;m=tomllib.load(open('manifests/components.lock.toml','rb'));sys.exit(0 if any(c['name']=='qemu' and c.get('enabled') for c in m.get('component',[])) else 1)"; echo $?
1    # guard 拦截（enabled=false）
```
确认 stub 不是永久硬失败：当组件 enabled=true 时 guard 放行，后续命令（cmake 等）会真实执行。

#### 约束核验

| # | 约束 | 结果 | 证据 |
|---|------|------|------|
| C1 | Make 委托 Python 脚本，不做重型逻辑 | ✅ | 每个目标调用 `$(PYTHON) tools/infra/*.py`；构建目标仅 shell 一行 guard + cmake/make |
| C2 | 不写死绝对路径 | ✅ | `grep -nE '/mnt/\|/home/' Makefile` → 无匹配 |
| C3 | stub 不假装成功 | ✅ | disabled 组件：明确提示 + `exit 1`（make 退出 2）；无 "PASS" 输出 |
| C4 | `help` 为默认目标 | ✅ | `.DEFAULT_GOAL := help`（第 21 行）；`make` 输出与 `make help` 一致 |
| C5 | `clean-work` 只删 `.work/`、保留 `.cache/` | ✅ | 隔离树验证；`tools/infra/clean_work.py` 逻辑确认（shutil.rmtree(work)） |
| C6 | 构建目标依赖 `manifest-check` | ✅ | `build-mc`/`build-qemu`/`build-gem5` 均声明 `: manifest-check` |
| C7 | `check` 含 manifest-check + compileall | ✅ | Makefile 第 117-119 行；运行输出先 `manifest validation: PASS` 后 `repository checks: PASS` |
| C8 | 修改文件仅 Makefile（新增） | ✅ | `git status` → `?? Makefile` + 任务文件状态变更（已完成） |

#### 判决

**Accepted**

全部 15 个目标独立重跑通过（含退出码），5 条验收标准逐条满足，8 条约束全部守住。Makefile 为唯一新增交付物，脚本 compileall 通过，manifest_check PASS。与完成区自审结论**无差异**。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-12
**结论**：确认 reviewer 的 **Accepted**；5 条验收标准、4 条约束、交付物清单均独立复现通过，无遗漏。

**独立核对**：程序化核对 `.PHONY` 与 help 目标集合一致（15 个）；合成树塞入语法错误脚本 → `check` exit=2（compileall 真门禁）；`build-mc` enabled 分支 guard 放行、disabled 分支拦截；隔离树 `clean-work` 删 `.work` 保留 `.cache`、真实 `.work/DADAO*` 未动；无 `/mnt/`/`/home/`/0628 后续阶段目标残留。

**接口一致性**：与 `INFRA-004t`（脚本名 + `.work/source` 落点）、`INFRA-005t`（doctor/status/clean_work + `.cache/` 保护）、`INFRA-007t`（tag/context）、`LLVM-002t`/`QEMU-002t`（`build-mc`/`build-qemu` + `LLVM_SRC`/`QEMU_SRC`）均吻合。

**非阻塞观察（无需返工，后续落地时顺带处置）**：

1. `QEMU_BUILD` 声明未使用（QEMU 沿用 in-tree 构建，产物在 `.work/source/qemu`；若需 out-of-tree 由 `QEMU-002t` 处理）。
2. `component-enabled` 内联 Python 谓词，与 ADR-0002（v5：`.tao/knowledge/adr-0002-build-orchestration.md`）「manifest 处理交 Python 脚本」边界略模糊（一行谓词，可接受）。
3. `make -j prepare` 不保证 `fetch`→`apply-series` 顺序（默认串行下成立）。
4. `make -n build-qemu` 非纯 dry-run（GNU Make `-n` 对含 `$(MAKE)` 的递归行仍执行）。
5. 完成区记录的 `Makefile` 行号（71/83/98）因加注释位移，与实际（73/86/101）不符（文档小瑕疵）。
6. v5 无自身 ADR 记录 Make 接口决策（任务书本身充当 v5 接口权威）。

**统一判决**：**Accepted**。

