# INFRA-007t: 开发容器

**模块**：infra
**项目里程碑**：M1
**依赖**：`INFRA-006t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`Makefile` 的 `docker-image` / `docker-shell` 目标（`INFRA-006t`）
- 输出：`containers/dev/Dockerfile`
- 约束：容器只装构建依赖，不预置 DADAO 实现/补丁；镜像可复现（固定基础镜像）；不写绝对路径

## 背景（完整）

### 目标

提供可复现的开发容器镜像，作为"干净主机/开发容器"两条构建路径之一的容器路径，满足 LLVM MC / QEMU / gem5 的构建依赖。

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
  - **追加 gem5 构建依赖**（v5 新增；具体清单待 gem5 模块确认，候选：`scons m4 python3-dev python3-pip libprotobuf-dev protobuf-compiler libhdf5-dev zlib1g-dev libpng-dev`）。
  - 安装后清理 apt 缓存；`WORKDIR /workspace`。
- 与 `INFRA-006t` 的 `docker-image` / `docker-shell` 目标联调（镜像 tag `dadao-v5-dev:local`）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- 无 ISA 相关差异（基础设施，与 ISA 版本无关）。
- 0628 Dockerfile 只覆盖 LLVM + QEMU 依赖；v5 需增加 gem5 构建依赖（0628 gem5 依赖未进开发容器）。
- 镜像 tag：`dadao-v5-dev:local`（0628 为 `dadao-0628-dev:local`）。
- 若 `doctor.py` 增加 `scons` 等 gem5 工具检测，容器须一并满足。

## 已知坑 / 结论

- 基础镜像必须固定版本（`ubuntu:24.04`），保证可复现。
- `--no-install-recommends` + 清理 `apt` 缓存，保持镜像精简。
- 容器只提供构建依赖，不预置任何 DADAO 实现或补丁；源码经 `make fetch` + `apply-series` 在挂载的工作区内重建。
- gem5 依赖清单需与 gem5 模块的构建方式（scons）对齐，避免容器内构建失败。
- **容器内应报 `native`，非 `container`**：`container` 是宿主侧退路结论（宿主缺 native 但有 docker）；容器内无 docker、且自带构建工具，故 `doctor` 应报 `native`。为此 Dockerfile 必须装齐 `ninja` 与 `clang`（0628 清单有 `ninja-build` 但缺 `clang`，v5 补上）。

## 参考

- DADAO-0628：`.work/DADAO-0628/containers/dev/Dockerfile`
- DADAO-0628：`.work/DADAO-0628/Makefile`
- DADAO-0628：`.work/DADAO-0628/scripts/doctor.py`
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `containers/dev/Dockerfile` 可 `docker build` 成功（`make docker-image`）
2. 镜像内具备 LLVM / QEMU 构建依赖，并包含 gem5 构建所需依赖（清单在任务中标注待 gem5 模块确认）
3. `make docker-shell` 能进入容器并挂载工作区
4. 容器内 `make doctor` 报告 `native` 构建路径可用（容器内 required+native 工具齐全；`docker` 在容器内缺失不影响 native 判定）

## 完成区

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

1. **gem5 依赖清单 `[OPEN]`（跨模块）**：AC2 的 gem5 部分基于候选清单，尚未由 gem5 模块独立确认；**在 gem5 模块确认前不宜将 `INFRA-009m` 置为 `里程碑`**（按 `AGENTS.md` 跨模块交互规则）。
2. 基础镜像 `ubuntu:24.04` 为 tag 而非 digest（满足任务契约；强可复现可后续评估 digest pin）。
3. 文档计数笔误：engineer 第 1 轮称 0628 清单 15 个，实为 14 个（交付物无误）。

**统一判决**：**Accepted**。
