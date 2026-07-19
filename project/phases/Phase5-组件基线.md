# Phase 5：组件基线

> 对应 DADAO-0628 的 DL-005a（LLVM baseline）+ DL-006a（QEMU baseline）

## 目标

确定上游组件的精确 commit 版本，创建补丁系列目录结构，建立可复现的组件获取/构建流程。所有组件均 fork 自干净的上游 commit，通过有序补丁系列进行调整。

## 输入文件

| 来源 | 文件 | 用途 |
|------|------|------|
| Phase 0 | `manifests/components.lock.toml` | 组件锁定（需更新 commit hash） |
| Phase 0 | `scripts/fetch.py` | 组件获取脚本 |
| Phase 0 | `scripts/apply_series.py` | 补丁应用脚本 |
| Phase 1 | `contracts/isa/spec.md` | ISA 规范 |
| Phase 4 | `contracts/abi/spec.md` | ABI 规范 |
| Phase 4 | `contracts/elf/spec.md` | ELF 规范 |
| DADAO-0628 | `components/llvm/patches/series` | 补丁系列顺序参考 |
| DADAO-0628 | `components/qemu/patches/series` | 补丁系列顺序参考 |
| DADAO-0628 | `components/gem5/patches/series` | 补丁系列顺序参考 |
| DADAO-0628 | `manifests/components.lock.toml` | 组件 commit 参考 |

## 输出文件

```
DADAO-v5/
├── components/
│   ├── llvm/
│   │   ├── README.md                # LLVM 组件说明
│   │   └── patches/
│   │       └── series               # 补丁顺序文件（初始为空）
│   ├── qemu/
│   │   ├── README.md                # QEMU 组件说明
│   │   └── patches/
│   │       └── series               # 补丁顺序文件（初始为空）
│   ├── gem5/
│   │   ├── README.md                # gem5 组件说明
│   │   └── patches/
│   │       └── series               # 补丁顺序文件（初始为空）
│   └── chipyard/
│       ├── README.md                # Chipyard 组件说明（DADAO-v5 新增）
│       └── patches/
│           └── series               # 补丁顺序文件（初始为空）
├── manifests/
│   └── components.lock.toml         # 更新——加入具体 commit
```

## 子代理分解

### Agent F1：组件锁定与基线

**职责**：选择上游 commit，更新组件锁文件

**提示词**：
```
你是 DADAO-v5 的组件管理工程师。确定各上游组件的精确 commit 并创建组件目录结构。

1. 确定上游 commit（选择最近稳定版本，与 DADAO-0628 可不同）：

   - **LLVM**：https://github.com/llvm/llvm-project.git
     选择一个最近（2026年）的稳定 release commit（如 llvmorg-19.x 或更新）
     
   - **QEMU**：https://github.com/qemu/qemu.git
     选择一个最近（2026年）的稳定 release commit（如 v9.x 或更新）
     
   - **gem5**：https://github.com/gem5/gem5.git
     选择一个最近的稳定 commit
     
   - **chipyard**：https://github.com/ucb-bar/chipyard.git
     选择适合 SimRISC 定制的版本（DADAO-v5 新增的硬件目标）

2. 更新 `manifests/components.lock.toml`：
   - 填入各 enabled 组件的具体 commit
   - LLVM, QEMU, gem5 = enabled
   - chipyard, musl, linux = disabled（初始）
   - 每个组件标注 role 和 patch_series 路径

3. 创建 `components/README.md`：
   - 说明组件选择的理由
   - 如何添加新的组件
   - 补丁系列格式说明

4. 为每个组件创建目录结构：
   ```
   components/<name>/
     README.md          # 组件说明（用途、上游 URL、commit）
     patches/
       series           # 空文件，后续阶段填充
   ```
   
   每个 README.md 包含：
   - 组件名称和角色
   - 上游仓库 URL 和 commit
   - 补丁系列说明
   - 构建说明

5. 更新 Makefile——添加组件相关的 target：
   - `make fetch`：获取所有 enabled 组件到 .work/
   - `make apply-series`：应用补丁
   - `make prepare`：fetch + apply-series
   - `make build-llvm`  `make build-qemu`（骨架）

6. 创建补丁生成指南补丁：
   在 `scripts/` 下创建 `make_patch.py`：
   - 在 .work/source/<name> 中修改文件后生成 unified diff
   - 自动编号并添加到 patches/series
```

### Agent F2：构建环境与 Docker

**职责**：创建开发容器和构建脚本

**提示词**：
```
你是 DADAO-v5 的 DevOps 工程师。创建可复现的开发环境和构建基础。

1. 创建 `containers/dev/Dockerfile`：
   - 基于 Ubuntu 24.04 或 Debian testing
   - 安装：git, make, cmake, ninja-build, python3, gcc, g++
   - LLVM 构建依赖：zlib, libffi, libedit, libxml2
   - QEMU 构建依赖：glib2, libpixman, libfdt
   - gem5 构建依赖：python3-dev, libprotobuf-dev
   - Chipyard 构建依赖：verilator, sbt, java

2. 添加 Makefile target：
   - `make docker-image`：构建开发镜像
   - `make docker-shell`：在容器中启动 shell
   - 将 .work 目录映射到容器外（保持可复现）

3. 创建 `scripts/doctor.py` 更新：
   - 检查 cmake, ninja 是否安装
   - 检查各组件的构建依赖
   - 输出详细建议（缺失的依赖包名）
```

## 阶段验证

- `make fetch` 成功获取各组件到 `.work/source/`
- `make apply-series` 对空 series 无报错
- `make status` 显示正确的组件 commit 和状态

## 依赖关系

- 依赖 Phase 0（目录结构、manifest、脚本）
- 是 Phase 6（LLVM MC）和 Phase 7（QEMU）的前提
