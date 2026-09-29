# INFRA-016t: doctor.py 补组件构建依赖检查

**模块**：infra
**项目里程碑**：M1→M2
**依赖**：无
**状态**：已验证

## 问题描述

`tools/infra/doctor.py`（`INFRA-005t`）在 native 路径只查 `git/make/cmake/python3/ninja/clang/docker`，**不检查组件的构建依赖**（glib-2.0 / pixman-1 / libfdt / zlib 等）。

**实证（2026-09-29）**：`make build-qemu` 因缺 `pkg-config`/`glib-2.0` 失败（`meson.build:1059: Dependency lookup for glib-2.0 ... Pkg-config ... not found`），而 `make doctor` 仍 PASS。

`deferred.md` 已登记此缺口（`QEMU-002t` 交叉复核，2026-09-18）。

## 修改内容

`tools/infra/doctor.py`：增加**组件构建依赖检查**（按需/按启用组件）：

- **LLVM**：`cmake`（版本下限）、`ninja`、C++ 工具链
- **QEMU**：`pkg-config`、`glib-2.0`、`pixman-1`、`zlib`、（`libfdt` 视 target 需要）
- 机制：用 `pkg-config --exists <pkg>` 探测（**注意**：Ubuntu 的 `libfdt-dev` 不提供 `libfdt.pc`，需特殊处理或注明）
- 未装 → `doctor` 报 **FAIL**（给出缺失清单与安装建议，**不自行安装**）

## 约束

- 只加检查，不改现有检查
- **`doctor` 只报告、不安装**（命令缺失 → 提示用户）
- 完成后 `make check` EXIT=0（doctor 本身不阻断 `make check`，除非既有约定）

## 验收标准

1. `doctor.py` 检查 QEMU（`pkg-config`/`glib-2.0`/`pixman-1`/`zlib`）与 LLVM（`cmake`/`ninja`/C++）依赖
2. 缺依赖时 `make doctor` 报 FAIL 并列出缺失项
3. 现有检查不受影响
4. 反例验证（模拟缺依赖 → FAIL）

## 完成区

**测试结果**：7/7 反例测试通过（cmake 过低、cmake 充分、无 C++、g++ 在、glib 缺失、glib 存在、全缺失）；`make check` EXIT=0

**修改文件**：`tools/infra/doctor.py`（增加 `component-deps` 层 + 3 个 helper 函数）

**验收结果**：

`make doctor` 真实输出：
```
required
  git        OK       git version 2.53.0
  make       OK       GNU Make 4.4.1
  cmake      OK       cmake version 4.2.3
  python3    OK       Python 3.14.4
native
  ninja      OK       1.13.2
  clang      MISSING
container
  docker     MISSING
component-deps
  cmake      OK       4.2.3 (need >= 3.20)
  ninja      OK
  c++        OK       g++ (Ubuntu 15.2.0-16ubuntu1) 15.2.0
  pkg-config OK
  glib-2.0   OK
  pixman-1   OK
  zlib       OK
  libfdt     OK       (header fallback: /usr/include/fdt.h)
doctor: FAIL; native tools incomplete and Docker unavailable
```
注：现有 FAIL 是预先存在的（本机无 clang/docker），component-deps 全 PASS。

`make check` EXIT=0（repository checks: PASS）

反例验证（模拟全部缺失 → 8 项 FAIL）：
```
component-deps
  cmake      FAIL     cmake not found (need >= 3.20)
  ninja      MISSING
  c++        MISSING
  pkg-config MISSING
  glib-2.0   MISSING
  pixman-1   MISSING
  zlib       MISSING
  libfdt     MISSING
```
8 项缺失均含安装建议（`sudo apt install ...`）。

**新发现/坑**：
- Ubuntu `libfdt-dev` 不提供 `libfdt.pc`（pkg-config 文件），需要 header fallback（检查 `/usr/include/fdt.h`）
- LLVM 23.1.1 的 `cmake_minimum_required(VERSION 3.20.0)` 来自源码 `llvm/CMakeLists.txt` 第 1 行

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审阅范围**：`tools/infra/doctor.py` 全文（208 行）

**Finding 1**：Line 167 `__import__("os").path.isfile` 非惯用写法
- 处置：✅已修 → 改为模块顶部 `import os` + `os.path.isfile`
- 复验：`python3 -m py_compile` 通过，`make doctor` 正常

**Finding 2**：Line 132 docstring "Returns a list of (pkg, install_hint) tuples" 与实际返回类型（`list[str]`）不符
- 处置：✅已修 → docstring 改为 `list of "<pkg> (<install-hint>)" strings`
- 复验：`py_compile` 通过

**Finding 3**：Line 152 `cpp_label = cpp_name or "g++/clang++"` 赋值后未使用
- 处置：✅已修 → 删除该行
- 复验：`py_compile` 通过，`make doctor` 正常

**判决**：3 项 finding 均已修，无遗留

#### 第 1 轮 reviewer 验收

**审查对象**：`tools/infra/doctor.py`（工作树 208 行，`git diff` +136/-2）；任务文件完成区。

**重跑记录（reviewer 独立执行，均为真机输出）**

1. `make doctor`（真实环境）：
```
required
  git        OK       git version 2.53.0
  make       OK       GNU Make 4.4.1
  cmake      OK       cmake version 4.2.3
  python3    OK       Python 3.14.4
native
  ninja      OK       1.13.2
  clang      MISSING
container
  docker     MISSING
component-deps
  cmake      OK       4.2.3 (need >= 3.20)
  ninja      OK
  c++        OK       g++ (Ubuntu 15.2.0-16ubuntu1) 15.2.0
  pkg-config OK
  glib-2.0   OK
  pixman-1   OK
  zlib       OK
  libfdt     OK       (header fallback: /usr/include/fdt.h)
doctor: FAIL; native tools incomplete and Docker unavailable
make: *** [Makefile:59: doctor] Error 1
```
`EXIT=2`（make 自身错误码）。与完成区贴出的输出**逐行一致**，无美化/转述。

2. **归因复核（环境既有 FAIL）**：取出 `HEAD:tools/infra/doctor.py`（74 行）直接执行：
```
native
  ninja      OK       1.13.2
  clang      MISSING
container
  docker     MISSING
doctor: FAIL; native tools incomplete and Docker unavailable
EXIT=1
```
→ HEAD 版同样因 `clang`/`docker` MISSING 而 FAIL。**归因成立**：`make doctor` 的 FAIL 是本机环境既有，非本任务引入。

3. `make check`（`cmd > log 2>&1; rc=$?`）：`EXIT=0`，末行 `repository checks: PASS`。且 `Makefile:123` 的 `check` 目标**不含 `doctor`**，故 doctor 不阻断 `make check`，与任务约束一致。

4. **反例注入（均在 `/tmp/opencode/INFRA-016t/` 的临时 fake PATH 下，未改仓库）**：
   - **无 `pkg-config`**（required/native 保留、fake `docker` 使既有分支不短路）→ `component-deps` 显示 `pkg-config/glib-2.0/pixman-1/zlib MISSING`，末行 `doctor: FAIL; missing component build dependencies:` 并逐条列出 `sudo apt install ...` 建议，`EXIT=1`。
   - **cmake 版本过低**（fake `cmake` 输出 `3.10.0`）→ `cmake FAIL 3.10.0 (need >= 3.20)`，`EXIT=1`。版本比较正确。
   - **无 C++ 编译器**（fake PATH 去掉 `g++`）→ `c++ MISSING`，`EXIT=1`。
   - **选择性缺失**（fake `pkg-config` 仅令 `pixman-1` 失败）→ 仅 `pixman-1 MISSING`，`glib-2.0/zlib` 仍 OK；证明逐包探测有效，非"一刀切"。
   - **libfdt 三条路径**：真实机 `libfdt.pc` 不存在（`pkg-config --exists libfdt` 退出 1）而 `/usr/include/fdt.h` 存在 → `OK (header fallback)`；fake `pkg-config` 令 `libfdt` 成功 → `OK (pkg-config)`；导入模块把 `_pkg_exists` 恒 False + `_LIBFDT_HEADER` 指向不存在路径 → `libfdt MISSING`，返回安装建议。
   - 所有反例均**只报告、不安装**：`grep` 全文仅见字符串中的 `sudo apt install` 提示，无任何执行安装的调用（无 `apt`/`pip`/`install` 子进程）。

5. **独立性/反例目录**：全部注入在 `/tmp/opencode/INFRA-016t/` 下，仓库未受污染——`git status --porcelain` 仍仅两文件改动（任务文件 + `doctor.py`）。

**约束核验（逐条）**

| 约束 | 结论 | 证据 |
|---|---|---|
| 只加检查，不改现有检查 | ✅ 守住 | `REQUIRED`/`NATIVE`/`report()` 与 HEAD 逐字节 `diff` 无差异；`main()` 既有三分支逻辑未动，仅在末尾追加 `missing_deps` 分支 |
| doctor 只报告不安装 | ✅ 守住 | 全文无安装子进程，仅 `print` 建议字符串 |
| 检查 QEMU/LLVM 依赖 | ✅ 守住 | `pkg-config/glib-2.0/pixman-1/zlib` + `cmake(>=3.20)/ninja/c++`；libfdt 走 header fallback |
| 缺依赖 → FAIL + 缺失项 | ✅ 守住 | 反例 4：末行 FAIL 并列出缺失清单与安装建议 |
| `make check` EXIT=0 | ✅ 守住 | 重跑 EXIT=0，`repository checks: PASS` |
| 环境既有 FAIL 归因 | ✅ 成立 | HEAD 版 doctor 同样 FAIL（clang/docker MISSING），非本任务引入 |

**自审 finding 复核**：完成区所述 3 项 engineer 自审 finding（`__import__` 惯用写法、docstring 返回类型、未用变量）在当前 208 行代码中均已落实（第 20 行 `import os` + 第 167 行 `os.path.isfile`；第 133 行 docstring 已改；无孤儿变量）。

**遗留观察（非阻断，供架构师）**

1. **verdict 短路顺序**：`main()` 中 `missing_native and not docker` 分支排在 `missing_deps` 之前。在本机（clang/docker 双缺）若同时存在组件依赖缺失，末行只会报 native 原因，组件依赖的**安装建议摘要**不会打印（`component-deps` 分节的 `MISSING` 行仍照常显示）。功能路径本身正确（fake `docker` 反例已证明 `missing_deps` 分支可用且给出建议）。
2. **组件依赖检查为无条件执行**：任务修改内容写"按需/按启用组件"，实现对所有运行一律检查。与验收标准 1/2 一致（标准未附条件），且仓库无"组件启用"机制，取最简实现尚可；但在"仅用容器、宿主机无 glib"场景会报 FAIL。属设计取舍，非缺陷。
3. **完成区"新发现"笔误**：称 `cmake_minimum_required` 在 `llvm/CMakeLists.txt` 第 1 行，实际在第 2 行（第 1 行为注释）；版本 `3.20.0` 与 `_CMAKE_MIN_VERSION=(3,20)` 结论正确。

**判决：Accepted**

- 验收命令块在 reviewer 独立重跑下全部通过；硬约束逐条守住；反例注入确认每条新增检查均有可达 FAIL 路径；`make doctor` 的 FAIL 经 HEAD 对照确认为环境既有。上述"遗留观察"不影响本任务验收，请架构师在设计层酌情定夺（尤其观察 1、2 是否需后续调整）。

**验证方式说明**：本审查所有数字/结论均来自 reviewer 亲自执行的命令输出；未采信工程师完成区的任何转述（其贴出的 `make doctor` 输出经比对与真机一致）。