# INFRA-006t: Makefile 编排

**模块**：infra
**阶段**：0

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`scripts/` 下的 manifest/doctor/status/fetch/apply_series/clean_work 工具
- 输出：顶层 `Makefile`
- 约束：Make 为稳定用户接口，实际逻辑委托给 Python 标准库脚本；构建目标对未就绪组件以 stub 形式存在；不写死绝对路径

## 背景（完整）

### 目标

以 Make 作为统一入口编排 fetch / 打补丁 / 构建 / 容器等操作，使干净 checkout 上可一键准备与构建。

### 设计理由

- ADR-0002：**Use Make as the stable user interface and Python standard-library scripts for manifest processing.**
- 每个构建目标先依赖 `manifest-check`，保证只在锁有效时构建。
- 构建产物落在 `.work/` 下（`QEMU_BUILD` / `LLVM_BUILD` 等变量可覆盖）。

### 关键概念 / 数据

- 0628 `Makefile` 结构：`PYTHON ?= python3`、`.DEFAULT_GOAL := help`、`.PHONY` 列表、`help` 打印所有目标。
- 关键目标与依赖（0628）：
  - `manifest-check` → `python3 scripts/manifest_check.py`
  - `doctor` → `python3 scripts/doctor.py`
  - `status` → `python3 scripts/status.py`
  - `fetch: manifest-check` → `python3 scripts/fetch.py`
  - `apply-series: manifest-check` → `python3 scripts/apply_series.py`
  - `prepare: fetch apply-series`
  - `build-qemu: manifest-check` → `cd .work/qemu && ./configure --target-list=dadao-softmmu --enable-tcg --disable-werror` 后 `make -j$(nproc)`
  - `build-mc: manifest-check` → `cmake -G Ninja -B .work/build/llvm -S .work/llvm/llvm -DLLVM_TARGETS_TO_BUILD=DADAO -DLLVM_ENABLE_PROJECTS="" -DCMAKE_BUILD_TYPE=RelWithDebInfo -DLLVM_ENABLE_ASSERTIONS=ON` 后 `ninja llvm-mc llvm-objdump`
  - `docker-image` → `docker build -t <tag> containers/dev`
  - `clean-work` → `python3 scripts/clean_work.py`
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

**状态**：待开始
**Commit**：
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
