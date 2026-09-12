# INFRA-007t: 开发容器

**模块**：infra
**项目里程碑**：M1
**依赖**：`INFRA-006t`
**状态**：待开始

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

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
