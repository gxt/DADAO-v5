# INFRA-007t: 开发容器

**模块**：infra
**项目里程碑**：M1
**依赖**：`INFRA-006t`
**状态**：已验证

> **注（2026-09-14 模块重划）**：脚本目录由 `scripts/` 迁至 `tools/infra/`；下方完成区/审阅记录中的 `scripts/` 为当时的历史路径。

## 执行环境

**执行环境**：本地

## 变更（2026-09-12，用户/架构师决策）

- **M1 范围收窄**：容器只装 M1（LLVM/QEMU）依赖，**移除 gem5 依赖**（gem5 属后续阶段，不应 gate M1 里程碑）。相应调整「目标 / 交付物 / 差异 / 已知坑 / 验收标准 2」；需重跑构建验收（本任务回退 `待返工`）。

## 接口规范

- 输入：`Makefile` 的 `docker-image` / `docker-shell` 目标（`INFRA-006t`）
- 输出：`containers/dev/Dockerfile`
- 约束：容器只装构建依赖，不预置 DADAO 实现/补丁；镜像可复现（固定基础镜像）；不写绝对路径

## 背景（完整）

### 目标

提供可复现的开发容器镜像，作为"干净主机/开发容器"两条构建路径之一的容器路径，满足 **M1** 的 LLVM MC / QEMU 构建依赖（gem5 属后续阶段，不在 M1 容器内）。

### 设计理由

- 0628 `code-agent/designs/0002-detailed-roadmap.md`：M0 交付含"Development container skeleton"。
- `doctor.py` 的判定逻辑：`container` 是**宿主侧**结论（宿主缺 `ninja`/`clang` 但有 docker 时的退路）；**容器内**工具齐全，应报 `native`。故容器须装齐 native 工具（`ninja`+`clang`）。
- 容器把构建依赖与宿主隔离，保证干净环境可复现。

### 关键概念 / 数据

- 0628 `containers/dev/Dockerfile`（完整转述）：
  - `FROM ubuntu:24.04`
  - `ARG DEBIAN_FRONTEND=noninteractive`
  - `apt-get install -y --no-install-recommends`：`build-essential ca-certificates cmake git ninja-build python3 bison flex pkg-config libglib2.0-dev libpixman-1-dev libfdt-dev zlib1g-dev libzstd-dev`
  - 安装后 `rm -rf /var/lib/apt/lists/*`
  - `WORKDIR /workspace`
- 这些依赖覆盖：LLVM 构建（cmake/ninja/bison/flex/zlib/libzstd）、QEMU 构建（glib/pixman/fdt）。
- `Makefile` 容器目标（0628）：`docker-image: docker build -t dadao-0628-dev:local containers/dev`。

### 上游引用

- DADAO-0628 `containers/dev/Dockerfile`（完整转述见上）。
- DADAO-0628 `Makefile`：`docker-image` 目标。
- DADAO-0628 `code-agent/designs/0002-detailed-roadmap.md`：开发容器骨架。
- DADAO-0628 `scripts/doctor.py`：原生/容器构建路径判定。

## 交付物

- `containers/dev/Dockerfile`：
  - 基于固定版本的基础镜像（`ubuntu:24.04`）。
  - 安装 LLVM 与 QEMU 构建依赖（沿用 0628 清单）；**并补 `clang`**（`doctor.py` 的 native 判据含 `clang`，容器内须 native 工具齐全以报 `native` 路径）。
  - **不装 gem5 依赖**（M1 范围外；待 gem5 模块启动时再加，不 gate M1 里程碑）。
  - 安装后清理 apt 缓存；`WORKDIR /workspace`。
- 与 `INFRA-006t` 的 `docker-image` / `docker-shell` 目标联调（镜像 tag `dadao-v5-dev:local`）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- 无 ISA 相关差异（基础设施，与 ISA 版本无关）。
- 0628 Dockerfile 只覆盖 LLVM + QEMU 依赖；v5 M1 容器同样只装 LLVM/QEMU 依赖（**不装 gem5**；gem5 依赖待 gem5 模块启动时再加）。
- 镜像 tag：`dadao-v5-dev:local`（0628 为 `dadao-0628-dev:local`）。
- 待 gem5 模块启动时，再向容器追加 gem5 依赖并重跑验收。

## 已知坑 / 结论

- 基础镜像必须固定版本（`ubuntu:24.04`），保证可复现。
- `--no-install-recommends` + 清理 `apt` 缓存，保持镜像精简。
- 容器只提供构建依赖，不预置任何 DADAO 实现或补丁；源码经 `make fetch` + `apply-series` 在挂载的工作区内重建。
- M1 容器**只装 LLVM/QEMU 依赖**；gem5 依赖待 gem5 模块启动时再加（避免把 M1 里程碑 gate 在 gem5 上）。
- **容器内应报 `native`，非 `container`**：`container` 是宿主侧退路结论（宿主缺 native 但有 docker）；容器内无 docker、且自带构建工具，故 `doctor` 应报 `native`。为此 Dockerfile 必须装齐 `ninja` 与 `clang`（0628 清单有 `ninja-build` 但缺 `clang`，v5 补上）。

## 参考

- DADAO-0628：`.work/DADAO-0628/containers/dev/Dockerfile`
- DADAO-0628：`.work/DADAO-0628/Makefile`
- DADAO-0628：`.work/DADAO-0628/scripts/doctor.py`
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `containers/dev/Dockerfile` 可 `docker build` 成功（`make docker-image`）
2. 镜像内具备 LLVM / QEMU 构建依赖（M1 scope；不含 gem5 依赖）
3. `make docker-shell` 能进入容器并挂载工作区
4. 容器内 `make doctor` 报告 `native` 构建路径可用（容器内 required+native 工具齐全；`docker` 在容器内缺失不影响 native 判定）

## 完成区（M1 收窄返工轮，当前）

**测试结果**：全部通过 4/4（M1 收窄返工轮；验收标准 1-4 均已实测）。
- `make docker-image` → exit 0，**重新构建**（apt 层未命中缓存，`CREATED 34 seconds ago`），`Successfully tagged dadao-v5-dev:local`（新镜像 `sha256:a58255f6e380...`）。
- 容器内 `make doctor` → exit 0，`doctor: PASS (native build path available)`。
- 容器内 M1 依赖检查 → `RESULT=0`（LLVM/QEMU 工具与库齐全）。
- 容器内 gem5 依赖检查 → 全部 ABSENT（`scons`/`protoc`/`libprotobuf-dev`/`protobuf-compiler`/`libhdf5-dev`/`libpng-dev`/`python3-pip`/`python3-dev`/python 模块 `SCons`）。
- Dockerfile 约束静态核对 → 全部满足。

**修改文件**：
- `containers/dev/Dockerfile`（本轮由主会话移除 gem5 依赖；engineer 仅验证，未再改动）
- `.tao/tasks/infra/INFRA-007t-开发容器.md`（本完成区/审阅记录）
- 临时检查脚本（非仓库）：`/tmp/opencode/INFRA-007t/check-deps-m1.sh`
- 日志（gitignored）：`.tao/logs/INFRA-007t-rework-docker-image.log`、`INFRA-007t-rework-doctor.log`、`INFRA-007t-rework-container-deps.log`、`INFRA-007t-rework-mount.log`、`INFRA-007t-rework-no-impl-check.log`

**验收结果**（真实输出，含退出码）：

1. 验收标准 1 —— `make docker-image`（工作目录 `/mnt/tao/DADAO-v5`；完整日志 `.tao/logs/INFRA-007t-rework-docker-image.log`）：
```
docker build -t dadao-v5-dev:local containers/dev
DEPRECATED: The legacy builder is deprecated and will be removed in a future release.
Sending build context to Docker daemon  3.072kB
Step 1/4 : FROM ubuntu:24.04
 ---> 224a1869083a
Step 2/4 : ARG DEBIAN_FRONTEND=noninteractive
 ---> Using cache
 ---> 6265f83d6823
Step 3/4 : RUN apt-get update && apt-get install -y --no-install-recommends ... zlib1g-dev libzstd-dev     && rm -rf /var/lib/apt/lists/*
 ---> 1e115fd8e4b7
Step 4/4 : WORKDIR /workspace
 ---> a58255f6e380
Successfully built a58255f6e380
Successfully tagged dadao-v5-dev:local
EXIT=0
```
- `docker history` 证实 apt 层为**新构建**（`CREATED 34 seconds ago`，非 `Using cache`），命令与 Dockerfile 逐字一致（`apt-get update && apt-get install -y --no-install-recommends`）。
- 构建日志中 `grep -E 'scons|libprotobuf-dev|protobuf-compiler|libhdf5-dev|libpng-dev|python3-pip|python3-dev'` → `NONE`（**无 gem5 包被安装**）。
- 基础层 `FROM ubuntu:24.04 ---> 224a1869083a` 与 `docker image inspect ubuntu:24.04` 的 ID `sha256:224a1869083a...` 一致（固定基础镜像）。
- 新镜像 `docker image inspect dadao-v5-dev:local`：`WorkingDir=/workspace`，`Os=linux`，`Arch=amd64`，`Size=281074945`。

2. 验收标准 3 —— `make docker-shell` 挂载工作区（`make -n docker-shell` → `docker run --rm -it -v "/home/ubuntu/tao/DADAO-v5:/workspace" dadao-v5-dev:local /bin/bash`，`/home/ubuntu/tao` 为 `/mnt/tao` 软链；日志 `.tao/logs/INFRA-007t-rework-mount.log`）：
```
$ docker run --rm -v "$(pwd):/workspace" dadao-v5-dev:local /bin/bash -c 'pwd; test -f /workspace/Makefile && ...'
/workspace
host Makefile visible: yes
host .tao visible: yes
host Dockerfile visible: yes
EXIT=0
```

3. 验收标准 4 —— 容器内 `make doctor`（日志 `.tao/logs/INFRA-007t-rework-doctor.log`）：
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
  docker     MISSING  
doctor: PASS (native build path available)
EXIT=0
```
容器内 `docker` 缺失（符合预期），required+native 齐全，报 `native`。

4. 验收标准 2 —— 容器内依赖检查（脚本 `/tmp/opencode/INFRA-007t/check-deps-m1.sh`；日志 `.tao/logs/INFRA-007t-rework-container-deps.log`）：
```
== M1 tools (must be present) ==
  ninja OK /usr/bin/ninja     clang OK /usr/bin/clang     cmake OK /usr/bin/cmake
  bison OK /usr/bin/bison     flex OK /usr/bin/flex       pkg-config OK /usr/bin/pkg-config
  git OK /usr/bin/git         make OK /usr/bin/make       python3 OK /usr/bin/python3
== M1 pkg-config modules (must be present) ==
  glib-2.0 OK 2.80.0          pixman-1 OK 0.42.2          zlib OK 1.3        libzstd OK 1.5.5
== fdt (headers + linkable lib; libfdt-dev has no .pc) ==
  libfdt OK header + libfdt.so present
== gem5 deps (must be ABSENT in M1 scope) ==
  scons ABSENT / protoc ABSENT
  libprotobuf-dev ABSENT / protobuf-compiler ABSENT / libhdf5-dev ABSENT / libpng-dev ABSENT
  python3-pip ABSENT / python3-dev ABSENT / python module SCons ABSENT
RESULT=0
EXIT=0
```
- LLVM 依赖：`cmake ninja bison flex zlib libzstd` ✅
- QEMU 依赖：`glib-2.0 pixman-1 fdt` ✅（`libfdt` 用头文件 + `libfdt.so` 判定）
- gem5 依赖：全部缺失 ✅（符合**收窄后**的验收标准 2）
- 补充：`dpkg -l` 确认 `ninja-build clang cmake bison flex pkg-config libglib2.0-dev libpixman-1-dev libfdt-dev zlib1g-dev libzstd-dev` 均 `installed`。

5. Dockerfile 约束静态核对（`containers/dev/Dockerfile`）：
```
9:FROM ubuntu:24.04                       # 固定基础镜像
20:RUN apt-get update && apt-get install -y --no-install-recommends \
21:    build-essential ca-certificates cmake git ninja-build clang python3 \
24:    && rm -rf /var/lib/apt/lists/*     # 清理 apt 缓存
26:WORKDIR /workspace                     # 工作目录
```
- 含 `clang`（行 21）✅；`--no-install-recommends`（行 20）✅。
- 无宿主绝对路径（`grep -nE '/mnt|/home/'` 无命中）。
- 无 DADAO 实现/补丁：`ls -A /workspace` 空；镜像内 `find / -xdev -iname '*dadao*' -o -iname '*.patch' -o -iname '*.series'` 无命中（日志 `.tao/logs/INFRA-007t-rework-no-impl-check.log`）。

**新发现/坑**：
- **`m4` 是 `flex`/`bison` 的硬 `Depends`**（`apt-cache depends flex` → `Depends: m4`；`apt-cache rdepends --installed m4` → `bison`/`flex`），因此 M1 镜像内存在 `m4` 属正常，**不是** gem5 依赖泄漏。检查 gem5 缺失时不可把 `m4` 列入（初版检查脚本误判，已修正）。
- **gem5 依赖清单此前标注 `[OPEN]`**；本收窄后 M1 容器明确不装 gem5 依赖，该 `[OPEN]` 对 M1 不再适用，待 gem5 模块启动时再定义其容器依赖。
- 其余沿用前轮：Ubuntu 24.04 `libfdt-dev` 无 `.pc` 文件；容器内 git `dubious ownership`（root vs uid 1000，`make doctor` 不受影响）。

**遗留问题**：
- 无阻塞项。收窄后的验收标准 1-4 全部实测通过。
- 待 gem5 模块启动时，再向容器追加 gem5 依赖并重跑验收（非本任务范围）。
- 待用户/架构师决定：容器内 git `dubious ownership` 对 `make fetch`/`apply-series` 的影响是否需预置 `safe.directory`（本轮按最小改动未改 Dockerfile）。

---

## 完成区（历史轮：gem5 依赖版，已被上方取代）

**测试结果**：全部通过 4/4（验收标准 1-4 均已实测）。
- `make docker-image` → exit 0，`Successfully tagged dadao-v5-dev:local`（命中已有层缓存）。
- 容器内 `make doctor` → exit 0，`doctor: PASS (native build path available)`。
- 容器内构建依赖逐项检查 → `RESULT=0`（工具 + pkg-config + libfdt + SCons 全 OK）。
- Dockerfile 约束静态核对 → 全部满足。

**修改文件**：
- `containers/dev/Dockerfile`（v5 首个开发容器定义；本轮**未改动**，仅验证）
- `.tao/tasks/infra/INFRA-007t-开发容器.md`（本完成区/审阅记录）
- 日志（gitignored）：`.tao/logs/INFRA-007t-docker-image.log`、`INFRA-007t-docker-shell-doctor.log`、`INFRA-007t-container-deps.log`、`INFRA-007t-container-deps-diag.log`、`INFRA-007t-libfdt-diag.log`、`INFRA-007t-mount-check.log`、`INFRA-007t-no-impl-check.log`、`INFRA-007t-make-n-docker-shell.log`

**验收结果**（真实输出，含退出码）：

1. 验收标准 1 —— `make docker-image`（工作目录 `/mnt/tao/DADAO-v5`；完整日志 `.tao/logs/INFRA-007t-docker-image.log`）：
```
docker build -t dadao-v5-dev:local containers/dev
DEPRECATED: The legacy builder is deprecated and will be removed in a future release.
Sending build context to Docker daemon  3.072kB
Step 1/4 : FROM ubuntu:24.04
 ---> 224a1869083a
Step 2/4 : ARG DEBIAN_FRONTEND=noninteractive
 ---> Using cache
 ---> 6265f83d6823
Step 3/4 : RUN apt-get update && apt-get install -y --no-install-recommends     build-essential ... libpng-dev     && rm -rf /var/lib/apt/lists/*
 ---> Using cache
 ---> 50e34641651a
Step 4/4 : WORKDIR /workspace
 ---> Using cache
 ---> 16464a20fd5b
Successfully built 16464a20fd5b
Successfully tagged dadao-v5-dev:local
EXIT=0
```
基础层 `Step 1/4 : FROM ubuntu:24.04 ---> 224a1869083a` 与本地 `docker image inspect ubuntu:24.04` 的 ID `sha256:224a1869083a...` 一致（固定基础镜像）。

2. 验收标准 3 —— `make docker-shell` 为交互式（`-it`），用等价非交互命令验证挂载 + 工作区（`make -n docker-shell` 输出 `docker run --rm -it -v "/home/ubuntu/tao/DADAO-v5:/workspace" dadao-v5-dev:local /bin/bash`；`/home/ubuntu/tao` 为 `/mnt/tao` 软链，解析后即本仓库）：
```
$ docker run --rm -v "$(pwd):/workspace" dadao-v5-dev:local /bin/bash -c \
    'pwd; test -f /workspace/Makefile && echo "host Makefile visible: yes"; test -d /workspace/.tao && echo "host .tao visible: yes"'
/workspace
host Makefile visible: yes
host .tao visible: yes
EXIT=0
```
（附注：同一命令里附加的 `git -C /workspace rev-parse` 因容器 root 与宿主 uid 不一致触发 git `dubious ownership` 而退出 128；这是 git 安全检查，**与挂载无关**，见「新发现/坑」。挂载本身由上面 `Makefile`/`.tao` 可见性证实。）

3. 验收标准 4 —— 容器内 `make doctor`（等价 `docker-shell` 的 `cd /workspace && make doctor`；日志 `.tao/logs/INFRA-007t-docker-shell-doctor.log`）：
```
$ docker run --rm -v "$(pwd):/workspace" dadao-v5-dev:local /bin/bash -c 'cd /workspace && make doctor'
required
  git        OK       git version 2.43.0
  make       OK       GNU Make 4.3
  cmake      OK       cmake version 3.28.3
  python3    OK       Python 3.12.3
native
  ninja      OK       1.11.1
  clang      OK       Ubuntu clang version 18.1.3 (1ubuntu1)
container
  docker     MISSING  
doctor: PASS (native build path available)
EXIT=0
```
容器内 `docker` 缺失（符合预期），但 required+native 齐全，故报 `native`，满足修订后的验收标准 4。

4. 验收标准 2 —— 容器内构建依赖逐项检查（脚本 `/tmp/opencode/INFRA-007t/check-deps.sh`；日志 `.tao/logs/INFRA-007t-container-deps.log`）：
```
== tools ==
  ninja OK /usr/bin/ninja     clang OK /usr/bin/clang       cmake OK /usr/bin/cmake
  bison OK /usr/bin/bison     flex  OK /usr/bin/flex        pkg-config OK /usr/bin/pkg-config
  scons OK /usr/bin/scons     m4    OK /usr/bin/m4          python3 OK /usr/bin/python3
  pip3  OK /usr/bin/pip3      protoc OK /usr/bin/protoc
== pkg-config modules ==
  glib-2.0 OK 2.80.0          pixman-1 OK 0.42.2            zlib OK 1.3        libzstd OK 1.5.5
== fdt (headers + linkable lib; libfdt-dev has no .pc) ==
  libfdt   OK  header + libfdt.so present
== python3 modules ==
  SCons    OK
RESULT=0
EXIT=0
```
- LLVM 依赖：`cmake ninja bison flex zlib libzstd` ✅
- QEMU 依赖：`glib-2.0 pixman-1 fdt` ✅（`libfdt` 用头文件 `/usr/include/libfdt.h` + 库 `libfdt.so` 判定；`cc -lfdt` 链接测试通过，见 `.tao/logs/INFRA-007t-libfdt-diag.log`）
- gem5 依赖：`scons m4 python3-dev python3-pip protobuf/hdf5/png` ✅（`scons --version` = 4.5.2，`python3 -c "import SCons"` OK）

5. Dockerfile 约束静态核对（`containers/dev/Dockerfile`）：
```
9:FROM ubuntu:24.04                       # 固定基础镜像
20:RUN apt-get update && apt-get install -y --no-install-recommends \
26:    && rm -rf /var/lib/apt/lists/*     # 清理 apt 缓存
28:WORKDIR /workspace                     # 工作目录
```
- 无宿主绝对路径（grep `/mnt`、`/home` 无命中；仅容器内路径 `/var/lib/apt/lists`、`/workspace`）。
- 无 DADAO 实现/补丁：`docker run --rm dadao-v5-dev:local ls -A /workspace` 为空；镜像内 `find / -xdev -iname '*dadao*' -o -iname '*.patch' -o -iname '*.series'` 无命中（日志 `.tao/logs/INFRA-007t-no-impl-check.log`）。
- 镜像 `docker image inspect`：`WorkingDir=/workspace`，`Arch=amd64`。

**新发现/坑**：
- **Ubuntu 24.04 的 `libfdt-dev` 不提供 pkg-config 文件**：`dpkg -L libfdt-dev` 只有 `fdt.h`/`libfdt.h`/`libfdt_env.h`/`libfdt.a`/`libfdt.so`，无 `libfdt.pc`（`pkg-config --list-all | grep fdt` 为空）。因此不能用 `pkg-config libfdt` 判定；头文件 + `libfdt.so` + `cc -lfdt` 链接均可，QEMU `--enable-fdt=auto` 可回退内部 dtc，非阻塞。后续若 QEMU 明确要求系统 fdt，需注意此点。
- **SCons 的 Python 模块名是大写 `SCons`**（`import SCons` OK，`import scons` 报 ModuleNotFoundError），但 `/usr/bin/scons` 可执行文件正常（v4.5.2）。检查脚本判据须用 `SCons`。
- **容器内 git `dubious ownership`**：容器以 root 运行，绑定挂载的宿主仓库属主为 uid 1000，`git -C /workspace ...` 报 `detected dubious ownership` 并退出 128。`make doctor` 不受影响（doctor 只查 `git --version`）；但若后续在容器内执行 `make fetch`/`apply-series` 等 git 操作，需 `git config --global --add safe.directory /workspace`（或等效）。0628 Dockerfile 同样未处理，属沿用行为。
- gem5 依赖清单为任务给定候选，任务中仍标注"待 gem5 模块确认"（[OPEN]，保留未猜值）；本次已按候选清单装入并验证存在。
- Docker Hub 阻塞已由宿主 `/etc/docker/daemon.json` 的 `registry-mirrors`（`docker.m.daocloud.io`、`dockerproxy.net`）解决，`ubuntu:24.04` 已本地存在，构建全部命中缓存。

**遗留问题**：
- 无阻塞项。验收标准 1-4 全部实测通过。
- 待确认（非本任务阻塞，交 gem5 模块/架构师）：gem5 构建依赖最终清单（任务标注"待 gem5 模块确认"）；如需补充 `capstone`/`boost` 等可选依赖，另行开任务。
- 待确认（非本任务验收项，交用户/架构师决定是否处置）：容器内 git `dubious ownership` 对 `make fetch`/`apply-series` 的影响，是否需要在 Dockerfile 中预置 `safe.directory`（本轮按最小改动未改 Dockerfile）。

## 审阅记录

### 第 1 轮 engineer 自审（自主自审（嵌套受限））

嵌套 subagent 深度受限（`Subagent depth limit reached (1)`），按 engineer 规则降级为自主逐行自审。

审查对象：`containers/dev/Dockerfile`（仅此一个代码文件改动）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 0628 清单 15 个依赖是否齐全 | ✅无问题 | — | 逐项比对 `.work/DADAO-0628/containers/dev/Dockerfile`：15 项全在（行 21-23） |
| `clang` 是否补上（native 判据） | ✅无问题 | — | 行 21 含 `clang`；`scripts/doctor.py` 的 `NATIVE={ninja,clang}` 可满足 |
| gem5 候选依赖是否加入 | ✅无问题 | — | 行 24-25 含 `scons m4 python3-dev python3-pip libprotobuf-dev protobuf-compiler libhdf5-dev libpng-dev`；`zlib1g-dev` 与 LLVM 段共享未重复（行 23） |
| apt 包名在 Ubuntu 24.04 是否有效 | ✅无问题（未实测） | — | 均为 24.04 有效包名；`pkg-config` 为 pkgconf 过渡包，仍可用。因网络阻塞未能 apt 实测 |
| `--no-install-recommends` + 清理 apt 缓存 | ✅无问题 | — | 行 20 `--no-install-recommends`；行 26 `rm -rf /var/lib/apt/lists/*` |
| `WORKDIR /workspace` / 基础镜像固定 / 无宿主绝对路径 / 无 DADAO 实现 | ✅无问题 | — | 行 9 `FROM ubuntu:24.04`；行 28 `WORKDIR /workspace`；无其它路径；无任何 DADAO 代码 |
| Dockerfile 语法（续行/`&&`/单 RUN） | ✅无问题 | — | 行 20-26 单 RUN，`\` 续行 + `&&` 链；注释在 RUN 外，无解析风险 |
| 镜像 tag 与 Makefile 一致 | ✅无问题 | — | `make -n docker-image` 输出 `-t dadao-v5-dev:local`，与 `DOCKER_TAG` 一致 |
| 构建可验证性 | ⏸环境阻塞 | — | `make docker-image` 因 Docker Hub 不可达失败（见完成区）；未改代码、未绕过 |

判决：**文件内容无 blocker（ACCEPT）**；但验收标准 1-4 因网络阻塞未实测，任务状态保持 `待开始`，返回主会话由主会话决定下一步。

### 第 2 轮 engineer 自审（自主自审（嵌套受限））

本轮为阻塞解除后的复验：**未改动任何代码**（`containers/dev/Dockerfile` 与第 1 轮完全一致，`git status` 仍为 `?? containers/dev/`），仅重跑真实构建/运行并核对约束。嵌套 subagent 深度受限，按 engineer 规则降级为自主逐行自审；审查对象为「验收标准逐条实测证据」与「Dockerfile 静态约束」。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| AC1 `make docker-image` 可构建成功 | ✅已修（实测通过） | 无代码改动 | `make docker-image` EXIT=0，`Successfully tagged dadao-v5-dev:local`；日志 `INFRA-007t-docker-image.log` |
| AC2 镜像内 LLVM/QEMU/gem5 构建依赖齐全 | ✅已修（实测通过） | 无 | `check-deps.sh` RESULT=0；`cc -lfdt` 链接 OK；`scons --version` OK |
| AC3 `docker-shell` 可进容器并挂载工作区 | ✅已修（实测通过） | 无 | 等价非交互命令 `/workspace` 下可见宿主 `Makefile`/`.tao`，EXIT=0；`make -n docker-shell` EXIT=0 |
| AC4 容器内 `make doctor` 报 `native` | ✅已修（实测通过） | 无 | 输出 `doctor: PASS (native build path available)`，EXIT=0 |
| Dockerfile 约束（固定镜像/no-install-recommends/清理缓存/WORKDIR/无实现/无宿主路径） | ✅无问题 | 无 | grep 行 9/20/26/28；`ls -A /workspace` 空；`find` 无 dadao/patch/series；`inspect WorkingDir=/workspace` |
| Ubuntu 24.04 `libfdt-dev` 无 `.pc` 文件 | ⏸延后（非验收阻塞） | 无 | 头文件 + `libfdt.so` + `cc -lfdt` 均 OK；QEMU `--enable-fdt=auto` 可回退内部 dtc。已记入「新发现/坑」，待 QEMU 模块确认是否需要系统 fdt |
| 容器内 git `dubious ownership`（root vs uid 1000） | ⏸延后（非本任务验收项） | 无 | `make doctor` 不受影响（只查 `git --version`）；若容器内跑 `make fetch`/`apply-series` 需 `safe.directory`。0628 同样未处理，按最小改动未改 Dockerfile，已记入「新发现/坑」 |

判决：验收标准 1-4 **全部实测通过**，Dockerfile 无 blocker；两项非验收范围的观察项（libfdt `.pc`、git ownership）延后并已记录，不阻塞本任务。任务状态更新为 `待验收`，返回主会话重新 `/complete`。

### 第 3 轮 reviewer 验收

审查者独立重跑，不采信完成区。工作目录 `/mnt/tao/DADAO-v5`，临时脚本 `/tmp/opencode/INFRA-007t-review/`。

#### 1. 重跑记录

**AC1 — `make docker-image`**（日志 `.tao/logs/INFRA-007t-review-docker-image.log`）：
```
$ make docker-image
docker build -t dadao-v5-dev:local containers/dev
DEPRECATED: The legacy builder is deprecated and will be removed in a future release.
Sending build context to Docker daemon  3.072kB
Step 1/4 : FROM ubuntu:24.04
 ---> 224a1869083a
Step 2/4 : ARG DEBIAN_FRONTEND=noninteractive
 ---> Using cache
 ---> 6265f83d6823
Step 3/4 : RUN apt-get update && apt-get install -y --no-install-recommends ...
 ---> Using cache
 ---> 50e34641651a
Step 4/4 : WORKDIR /workspace
 ---> Using cache
 ---> 16464a20fd5b
Successfully built 16464a20fd5b
Successfully tagged dadao-v5-dev:local
EXIT=0
```

**AC2 — 容器内依赖检查**（日志 `.tao/logs/INFRA-007t-review-container-deps.log`）：
```
== tools ==
  ninja        OK /usr/bin/ninja
  clang        OK /usr/bin/clang
  cmake        OK /usr/bin/cmake
  bison        OK /usr/bin/bison
  flex         OK /usr/bin/flex
  pkg-config   OK /usr/bin/pkg-config
  scons        OK /usr/bin/scons
  m4           OK /usr/bin/m4
  python3      OK /usr/bin/python3
  pip3         OK /usr/bin/pip3
  protoc       OK /usr/bin/protoc
== python3 modules ==
  SCons        OK (version: 4.5.2)
== pkg-config modules ==
  glib-2.0     OK 2.80.0
  pixman-1     OK 0.42.2
  zlib         OK 1.3
  libzstd      OK 1.5.5
== fdt (headers + lib) ==
  libfdt       OK  header + libfdt.so present
== protoc ==
libprotoc 3.21.12
== gem5 extras ==
  python3-dev               OK (installed)
  python3-pip               OK (installed)
  libprotobuf-dev           OK (installed)
  libhdf5-dev               OK (installed)
  libpng-dev                OK (installed)
== gcc/g++ ==
gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
RESULT=0
EXIT=0
```

**AC3 — 挂载工作区**（日志 `.tao/logs/INFRA-007t-review-mount.log`）：
```
$ docker run --rm -v "$(pwd):/workspace" dadao-v5-dev:local /bin/bash -c 'pwd; test -f /workspace/Makefile && echo "host Makefile visible: yes"; test -d /workspace/.tao && echo "host .tao visible: yes"; test -f /workspace/containers/dev/Dockerfile && echo "host Dockerfile visible: yes"'
/workspace
host Makefile visible: yes
host .tao visible: yes
host Dockerfile visible: yes
EXIT=0
```

**AC4 — 容器内 `make doctor`**（日志 `.tao/logs/INFRA-007t-review-doctor.log`）：
```
$ docker run --rm -v "$(pwd):/workspace" dadao-v5-dev:local /bin/bash -c 'cd /workspace && make doctor'
required
  git        OK       git version 2.43.0
  make       OK       GNU Make 4.3
  cmake      OK       cmake version 3.28.3
  python3    OK       Python 3.12.3
native
  ninja      OK       1.11.1
  clang      OK       Ubuntu clang version 18.1.3 (1ubuntu1)
container
  docker     MISSING  
doctor: PASS (native build path available)
EXIT=0
```

**镜像元数据**：
```
$ docker image inspect dadao-v5-dev:local --format '{{.Os}}/{{.Architecture}} WorkingDir={{.Config.WorkingDir}}'
linux/amd64 WorkingDir=/workspace
$ docker image inspect dadao-v5-dev:local --format '{{.Size}}' → 302.0 MB
```

#### 2. Dockerfile 约束核对

| 约束 | 结果 | 证据 |
|------|------|------|
| 固定 `ubuntu:24.04` | ✅ | `FROM ubuntu:24.04`（行 9）；`Step 1/4 : FROM ubuntu:24.04 ---> 224a1869083a` |
| `--no-install-recommends` | ✅ | 行 20 `apt-get install -y --no-install-recommends` |
| 清理 apt 缓存 | ✅ | 行 26 `rm -rf /var/lib/apt/lists/*` |
| `WORKDIR /workspace` | ✅ | 行 28；`docker inspect` 确认 `WorkingDir=/workspace` |
| 无 DADAO 实现/补丁 | ✅ | 镜像内 `ls -A /workspace` 为空；`find / -xdev -iname '*dadao*' -o -iname '*.patch' -o -iname '*.series'` 无命中 |
| 无宿主绝对路径 | ✅ | `grep -n '/mnt\|/home/' Dockerfile` 无命中 |
| 含 `clang` | ✅ | 行 21 `ninja-build clang`；`clang --version` → `Ubuntu clang version 18.1.3` |
| 无 ENTRYPOINT/CMD | ✅ | 不强制要求，但确认无（交互 shell 模式） |

#### 3. 修改文件清单核对

```
$ git status --short
 M ".tao/tasks/infra/INFRA-007t-开发容器.md"   # 本任务文件（审阅记录）
?? containers/dev/                              # Dockerfile（新增）
$ git ls-files --others --exclude-standard | grep -v '\.tao/logs/'
containers/dev/Dockerfile
```

修改范围与任务一致：仅 `containers/dev/Dockerfile`（新增）+ 任务文件本身（审阅记录）。未越界改别的文件。

#### 4. 约束核验（逐条）

| 验收标准 | 判定 | 证据 |
|---------|------|------|
| AC1: `containers/dev/Dockerfile` 可 `docker build` 成功 | ✅ PASS | `make docker-image` EXIT=0，`Successfully tagged dadao-v5-dev:local`（命中层缓存） |
| AC2: 镜像内具备 LLVM / QEMU / gem5 构建依赖 | ✅ PASS | 工具 11 项全 OK；pkg-config 4 模块 OK；libfdt 头文件+库 OK；SCons OK；gem5 extras 5 包全 OK |
| AC3: `make docker-shell` 能进入容器并挂载工作区 | ✅ PASS | `/workspace` 下可见宿主 `Makefile`、`.tao`、`containers/dev/Dockerfile` |
| AC4: 容器内 `make doctor` 报告 `native` | ✅ PASS | 输出 `doctor: PASS (native build path available)`，EXIT=0 |

#### 5. 与完成区自审结论的差异

| 项目 | 完成区（engineer） | reviewer 独立验证 | 差异 |
|------|-------------------|------------------|------|
| AC1 `make docker-image` | EXIT=0，命中缓存 | EXIT=0，命中缓存 | **一致** |
| AC2 依赖检查 | RESULT=0，11 工具 + 4 pkg-config + fdt + SCons | RESULT=0，完全相同结果 | **一致** |
| AC3 挂载检查 | Makefile + .tao 可见 | Makefile + .tao + Dockerfile 可见（多检查一项） | **一致**（更完整） |
| AC4 `make doctor` | PASS (native)，EXIT=0 | PASS (native)，EXIT=0 | **一致** |
| Dockerfile 约束 | 全部满足 | 全部满足 | **一致** |
| 修改文件清单 | `containers/dev/Dockerfile` + 任务文件 | `containers/dev/Dockerfile` + 任务文件 | **一致** |

完成区自审结论与独立验证**完全一致**，无差异。

#### 6. 判决

**Accepted** — 验收标准 1-4 在独立重跑下全部通过，Dockerfile 约束全部满足，修改范围未越界。任务可进入 `已验证`。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-12
**结论**：确认 reviewer 的 **Accepted**（4/4 独立重跑）。

**独立核对**：`make docker-image` exit 0；用 `docker history` 反查 apt 层创建时间/命令与 Dockerfile 逐字一致（证实非仅缓存假象）；容器内 `make doctor` → `PASS (native)`（对照 `doctor.py`：native 齐 → mode=native，`docker` 缺失不 FAIL）；`dpkg-query` 逐项核对 0628 的 14 包 + `clang` + gem5 候选全部 installed；约束全守住（固定 base、`--no-install-recommends`、清理缓存、`WORKDIR`、无 DADAO 实现/补丁、无绝对路径）；与 `INFRA-006t` target/tag/context 逐字一致。

**非阻塞观察**：

1. **gem5 依赖清单 `[OPEN]`（跨模块）**：AC2 的 gem5 部分基于候选清单，尚未由 gem5 模块独立确认；**在 gem5 模块确认前不宜将 `INFRA-013m`（现 `INFRA-014m`）置为 `里程碑`**（按 `AGENTS.md` 跨模块交互规则）。
2. 基础镜像 `ubuntu:24.04` 为 tag 而非 digest（满足任务契约；强可复现可后续评估 digest pin）。
3. 文档计数笔误：engineer 第 1 轮称 0628 清单 15 个，实为 14 个（交付物无误）。

**统一判决**：**Accepted**。

### 第 4 轮 engineer 自审（自主自审（嵌套受限））

本轮为 **M1 范围收窄返工轮**：`containers/dev/Dockerfile` 由主会话移除 gem5 依赖，engineer 真实重跑构建/容器内验收并逐条核对收窄后的验收标准。尝试开 `general` subagent 做代码级 review 被拒（`Subagent depth limit reached (1)`），按 engineer 规则降级为自主逐行自审。

审查对象：`containers/dev/Dockerfile` 的 `git diff`（应仅移除 gem5 依赖）+ 本轮真实输出证据（含退出码）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| Dockerfile diff 是否只移除 gem5 依赖、保留 M1 依赖 + `clang` | ✅无问题 | 无 | `git diff`：删除 `scons m4 python3-dev python3-pip libprotobuf-dev protobuf-compiler libhdf5-dev libpng-dev` 及 gem5 注释；保留 `cmake ninja clang bison flex pkg-config libglib2.0-dev libpixman-1-dev libfdt-dev zlib1g-dev libzstd-dev` |
| AC1 `make docker-image` 可构建成功（apt 层已变，须重新构建） | ✅已修（实测） | 无 | `EXIT=0`，新镜像 `sha256:a58255f6e380...`；`docker history` 显示 apt 层 `CREATED 34 seconds ago`（非缓存）；日志 `INFRA-007t-rework-docker-image.log` |
| AC2 镜像内具备 LLVM/QEMU 依赖、**不含 gem5 依赖** | ✅已修（实测） | 无 | 依赖检查 `RESULT=0`：M1 工具/pkg-config/fdt 全 OK；`scons`/`protoc`/`libprotobuf-dev`/`protobuf-compiler`/`libhdf5-dev`/`libpng-dev`/`python3-pip`/`python3-dev`/python 模块 `SCons` 全 ABSENT |
| AC3 `docker-shell` 可进容器并挂载工作区 | ✅已修（实测） | 无 | 非交互等价命令 `/workspace` 下可见宿主 `Makefile`/`.tao`/`containers/dev/Dockerfile`，`EXIT=0` |
| AC4 容器内 `make doctor` 报 `native` | ✅已修（实测） | 无 | `doctor: PASS (native build path available)`，`EXIT=0` |
| 初版检查脚本把 `m4` 误列为 gem5 依赖导致 `RESULT=1` | ✅已修 | 修改 `/tmp/opencode/INFRA-007t/check-deps-m1.sh`（移除 `m4` 并注明其为 `flex`/`bison` 硬依赖） | `apt-cache depends flex` → `Depends: m4`；`apt-cache rdepends --installed m4` → `bison`/`flex`；修正后 `RESULT=0`，`EXIT=0` |
| Dockerfile 约束（固定 base/`--no-install-recommends`/清理缓存/`WORKDIR`/无宿主绝对路径/含 `clang`） | ✅无问题 | 无 | 行 9/20/24/26；`grep -nE '/mnt\|/home/'` 无命中；行 21 含 `clang` |
| 无 DADAO 实现/补丁 | ✅无问题 | 无 | `ls -A /workspace` 空；`find / -xdev -iname '*dadao*' -o -iname '*.patch' -o -iname '*.series'` 无命中 |
| 防造假（构建非缓存假象、命令真实执行） | ✅无问题 | 无 | `docker history` apt 层新建时间 34s ago + 构建日志含完整 `apt-get` 下载/安装 185 MB；所有验收命令退出码已留存日志 |

判决：**验收标准 1-4（收窄后）全部实测通过，Dockerfile 无 blocker**；检查脚本对 `m4` 的误判已修正。任务状态更新为 `待验收`，返回主会话重新 `/complete`。

### 第 5 轮 reviewer 验收（M1 收窄返工验收）

审查者独立重跑，不采信完成区。工作目录 `/mnt/tao/DADAO-v5`，临时脚本 `/tmp/opencode/INFRA-007t-review/`。

#### 1. 重跑记录

**AC1 — `make docker-image`**（日志 `/tmp/opencode/INFRA-007t-review/.tao/logs/INFRA-007t-review-docker-image.log`）：
```
$ make docker-image
docker build -t dadao-v5-dev:local containers/dev
DEPRECATED: The legacy builder is deprecated and will be removed in a future release.
Sending build context to Docker daemon  3.072kB
Step 1/4 : FROM ubuntu:24.04
 ---> 224a1869083a
Step 2/4 : ARG DEBIAN_FRONTEND=noninteractive
 ---> Using cache
 ---> 6265f83d6823
Step 3/4 : RUN apt-get update && apt-get install -y --no-install-recommends     build-essential ca-certificates cmake git ninja-build clang python3     bison flex pkg-config libglib2.0-dev libpixman-1-dev libfdt-dev     zlib1g-dev libzstd-dev     && rm -rf /var/lib/apt/lists/*
 ---> Using cache
 ---> 1e115fd8e4b7
Step 4/4 : WORKDIR /workspace
 ---> Using cache
 ---> a58255f6e380
Successfully built a58255f6e380
Successfully tagged dadao-v5-dev:local
EXIT=0
```

**AC2 — 容器内依赖检查**（脚本 `/tmp/opencode/INFRA-007t-review/check-m1-deps.sh`；日志 `/tmp/opencode/INFRA-007t-review/.tao/logs/INFRA-007t-review-container-deps.log`）：
```
=== M1 tools (must be present) ===
  ninja        OK /usr/bin/ninja
  clang        OK /usr/bin/clang
  cmake        OK /usr/bin/cmake
  bison        OK /usr/bin/bison
  flex         OK /usr/bin/flex
  pkg-config   OK /usr/bin/pkg-config
  git          OK /usr/bin/git
  make         OK /usr/bin/make
  python3      OK /usr/bin/python3

=== M1 pkg-config modules ===
  glib-2.0     OK 2.80.0
  pixman-1     OK 0.42.2
  zlib         OK 1.3
  libzstd      OK 1.5.5

=== fdt (headers + lib; libfdt-dev has no .pc) ===
  libfdt       OK  header + libfdt.so present

=== gem5 deps (must be ABSENT in M1 scope) ===
  scons                ABSENT
  protoc               ABSENT
  libprotobuf-dev      ABSENT
  protobuf-compiler    ABSENT
  libhdf5-dev          ABSENT
  libpng-dev           ABSENT
  python3-pip          ABSENT
  python3-dev          ABSENT
  python SCons      ABSENT

RESULT=0
EXIT=0
```

**AC3 — 挂载工作区**（日志 `/tmp/opencode/INFRA-007t-review/.tao/logs/INFRA-007t-review-mount.log`）：
```
$ docker run --rm -v "$(pwd):/workspace" dadao-v5-dev:local /bin/bash -c 'pwd; test -f /workspace/Makefile && echo "host Makefile visible: yes"; test -d /workspace/.tao && echo "host .tao visible: yes"; test -f /workspace/containers/dev/Dockerfile && echo "host Dockerfile visible: yes"'
/workspace
host Makefile visible: yes
host .tao visible: yes
host Dockerfile visible: yes
EXIT=0
```

**AC4 — 容器内 `make doctor`**（日志 `/tmp/opencode/INFRA-007t-review/.tao/logs/INFRA-007t-review-doctor.log`）：
```
$ docker run --rm -v "$(pwd):/workspace" dadao-v5-dev:local /bin/bash -c 'cd /workspace && make doctor'
required
  git        OK       git version 2.43.0
  make       OK       GNU Make 4.3
  cmake      OK       cmake version 3.28.3
  python3    OK       Python 3.12.3
native
  ninja      OK       1.11.1
  clang      OK       Ubuntu clang version 18.1.3 (1ubuntu1)
container
  docker     MISSING  
doctor: PASS (native build path available)
EXIT=0
```

**m4 依赖核实**（容器内 `apt-cache depends`）：
```
$ docker run --rm dadao-v5-dev:local /bin/bash -c 'apt-cache depends flex | grep -E "m4|Depends"; echo "---"; apt-cache depends bison | grep -E "m4|Depends"'
  Depends: libc6
  Depends: m4
---
  Depends: m4
  Depends: libc6
EXIT=0
```
`m4` 确为 `flex` 和 `bison` 的硬 `Depends`，镜像内存在属正常，不是 gem5 泄漏。

**镜像元数据**：
```
WorkingDir=/workspace  Os=linux  Arch=amd64  Size=281074945
Base image ubuntu:24.04 ID: sha256:224a1869083a...
```

#### 2. Dockerfile 约束核对

| 约束 | 结果 | 证据 |
|------|------|------|
| 固定 `ubuntu:24.04` | ✅ | `FROM ubuntu:24.04`（行 9）；base ID `224a1869083a` |
| `--no-install-recommends` | ✅ | 行 20 `apt-get install -y --no-install-recommends` |
| 清理 apt 缓存 | ✅ | 行 24 `rm -rf /var/lib/apt/lists/*` |
| `WORKDIR /workspace` | ✅ | 行 26；`docker inspect` 确认 `WorkingDir=/workspace` |
| 无 DADAO 实现/补丁 | ✅ | 镜像内 `ls -A /workspace` 为空；`find` 无 dadao/patch/series 命中 |
| 无宿主绝对路径 | ✅ | `grep -nE '/mnt\|/home/'` 无命中 |
| 含 `clang` | ✅ | 行 21 `ninja-build clang`；`clang --version` → `Ubuntu clang version 18.1.3` |
| **不含 gem5 依赖** | ✅ | `grep -nE 'scons\|protoc\|libprotobuf\|libhdf5\|libpng-dev\|python3-pip'` 无命中；`docker history` apt 层命令不含 gem5 包 |

#### 3. 修改文件清单核对

```
$ git status --short
 M ".tao/tasks/infra/INFRA-007t-开发容器.md"   # 本任务文件（审阅记录 + 变更说明）
 M ".tao/tasks/infra/INFRA-013m-infra里程碑.md"（现 `INFRA-014m`）  # 跨模块前置说明更新（gem5 gate 移除）
 M containers/dev/Dockerfile                      # 移除 gem5 依赖
```

`git diff containers/dev/Dockerfile` 确认：仅删除 gem5 相关行（`scons m4 python3-dev python3-pip libprotobuf-dev protobuf-compiler libhdf5-dev libpng-dev` 及 gem5 注释），保留全部 M1 依赖 + `clang`，注释更新为 M1 scope 说明。修改范围与任务一致，未越界。

`INFRA-013m`（现 `INFRA-014m`）的改动是同步更新跨模块前置说明（gem5 gate 移除），属合理联动。

#### 4. 约束核验（逐条）

| 验收标准 | 判定 | 证据 |
|---------|------|------|
| AC1: `containers/dev/Dockerfile` 可 `docker build` 成功 | ✅ PASS | `make docker-image` EXIT=0，`Successfully tagged dadao-v5-dev:local` |
| AC2: 镜像内具备 LLVM/QEMU 构建依赖（M1 scope；不含 gem5 依赖） | ✅ PASS | M1 工具 9 项全 OK；pkg-config 4 模块 OK；libfdt 头文件+库 OK；gem5 依赖 9 项全 ABSENT |
| AC3: `make docker-shell` 能进入容器并挂载工作区 | ✅ PASS | `/workspace` 下可见宿主 `Makefile`、`.tao`、`containers/dev/Dockerfile` |
| AC4: 容器内 `make doctor` 报告 `native` | ✅ PASS | `doctor: PASS (native build path available)`，EXIT=0 |

#### 5. 与完成区自审结论的差异

| 项目 | 完成区（engineer 第 4 轮） | reviewer 独立验证 | 差异 |
|------|--------------------------|------------------|------|
| AC1 `make docker-image` | EXIT=0，新镜像 `a58255f6e380`（apt 层非缓存） | EXIT=0，同一镜像 `a58255f6e380`（缓存命中） | **一致**（reviewer 重跑时层已缓存，属正常） |
| AC2 依赖检查 | RESULT=0，M1 工具+pkg-config+fdt 全 OK，gem5 全 ABSENT | RESULT=0，完全相同结果 | **一致** |
| AC3 挂载检查 | Makefile + .tao + Dockerfile 可见 | 相同 | **一致** |
| AC4 `make doctor` | PASS (native)，EXIT=0 | PASS (native)，EXIT=0 | **一致** |
| m4 依赖核实 | `apt-cache depends flex` → `Depends: m4` | 相同 | **一致** |
| Dockerfile 约束 | 全部满足 | 全部满足 | **一致** |
| 修改文件清单 | `containers/dev/Dockerfile` + 任务文件 | 同 + `INFRA-013m`（现 `INFRA-014m`）联动更新 | **一致**（reviewer 额外核对了 `INFRA-013m` 的合理联动） |

完成区自审结论与独立验证**完全一致**，无差异。

#### 6. 判决

**Accepted** — 验收标准 1-4（M1 收窄后）在独立重跑下全部通过，Dockerfile 约束全部满足（含「不含 gem5 依赖」新增约束），修改范围未越界。`m4` 存在确为 `flex`/`bison` 的 Depends，非 gem5 泄漏。任务可进入 `已验证`。

### 交叉复核（architect，返工后）

**复核者**：architect
**时间**：2026-09-12
**结论**：确认 reviewer 第 5 轮的 **Accepted**。

**独立核对**：`git diff` 确认 Dockerfile 仅删 gem5 依赖行；任务书「目标/交付物/差异/已知坑/验收标准 2」已一致收窄；`INFRA-013m`（现 `INFRA-014m`）gem5 gate 已移除（与 `milestones.md` 的 M1 = MC+QEMU 一致）。4/4 重跑通过（AC2 正例 M1 依赖齐 + 反例 gem5 全 ABSENT）；`docker history` 反查 apt 层不含 gem5 且层 ID 与旧 gem5 版不同（非缓存假象）；`m4` 经 `apt-cache rdepends` 确认仅为 `flex`/`bison` 的 Depends，非 gem5 泄漏。

**非阻塞观察**：

1. `ubuntu:24.04` 为 tag、apt 包未锁版本（满足任务契约；强复现可后续评估 digest pin）。
2. 任务书保留历史轮（gem5 版）完成区/审阅记录（已标注被取代）。
3. 容器内 git `dubious ownership` 沿用 0628，对 `make doctor` 无影响。

**统一判决**：**Accepted**。
