# INFRA-122t: build_gem5.py ccache 调用修复

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-119t`（已验证；ccache 接入）、`INTEG-053t`（已验证；gem5 源树 base+1）
**状态**：待开始

## 执行环境
本地；只改 gem5 构建入口工具，不改 gem5 组件补丁、不改 spec/tests。

## 问题根源

`tools/gem5/build_gem5.py` 在启用 ccache 时把环境变量设成：

```text
CC  = "ccache gcc"
CXX = "ccache g++"
```

gem5 的 SCons 在 `SConstruct` 里用 `readCommand([main['CXX'], '--version'])` 把 `CXX` 当作**单个 argv 元素**传给 `Popen`，于是报：

```text
FileNotFoundError: [Errno 2] No such file or directory: 'ccache g++'
```

结果：原生 `make build-gem5` **rc=2**。`INTEG-053t` 验收时只能用“从 PATH 隐藏 ccache”的 workaround 通过，属于工具缺陷，不是构建成功。

## 目标

1. `build_gem5.py` 在启用 ccache 时不再把带空格的命令串直接塞进 `CC`/`CXX`。
2. 用**单可执行文件**形式接入 ccache：生成包装脚本（如 `ccache-cc` / `ccache-cxx`），内容为 `exec ccache <compiler> "$@"`，把 `CC`/`CXX` 指向包装脚本的绝对路径。
3. 包装脚本放在构建目录内（运行期产物，不入库）；名称/路径由工具决定，不写死到仓库。
4. 保留 `--no-ccache`、`--ccache-dir`、`CC`/`CXX` 环境变量覆盖语义；`--no-ccache` 时行为与现在一致（直接使用真实编译器）。
5. 不改 gem5 源码/补丁、不改 `components/gem5/**`、不改 `Makefile` 的构建语义。

## 接口规范

### 1. `tools/gem5/build_gem5.py`

- 启用 ccache 时：
  - 解析 `CC`/`CXX` 的真实编译器（环境变量优先，否则 `gcc`/`g++`）；
  - 在构建目录下生成两个可执行包装脚本，内容语义等价于：
    ```sh
    #!/bin/sh
    exec ccache <real-compiler> "$@"
    ```
  - 设置 `env["CC"]`/`env["CXX"]` 为包装脚本的**绝对路径**；
  - 打印实际使用的编译器与包装脚本路径（供日志核对）。
- 包装脚本必须可执行；已存在时覆盖重写，避免旧内容残留。
- 若 `ccache` 不存在或 `--no-ccache`：不生成包装脚本，`CC`/`CXX` 保持真实编译器。
- 不把 `ccache` 目录写进仓库跟踪文件；不改 `CCACHE_DIR` 默认语义。
- 错误处理：包装脚本生成失败、不可执行、`ccache` 不可执行 ⇒ 明确报错并返回非零，不静默退回。

### 2. 文档

- 若 `tools/gem5/README.md` 或 `Makefile` 注释描述了 ccache 行为，只做与实现一致的最小文字同步；不新增运行期路径。

## 范围 / 非范围

**在范围内**：
- `tools/gem5/build_gem5.py`
- `tools/gem5/README.md`（仅当现有文字与实现冲突）
- 本任务书、`.tao/knowledge/milestones.md`（本行）
- 运行期证据与日志（已清理，未归档）

**不在范围内**（违反即越界）：
- `components/gem5/**`（源码、补丁、decode 表）
- `components/qemu/**`、`components/llvm/**`
- `spec/**`、`.tao/contracts/**`、`contracts/**`、`.tao/adr/**`
- `tests/**`、`Makefile` 的构建目标语义、门控脚本
- `.tao/knowledge/discussing.md`

## 验收标准

1. **原生构建通过**：`make build-gem5 JOBS=8`（不隐藏 ccache、不手工改 PATH）**rc=0**；日志含 `build-gem5: ccache: on`，且不出现 `FileNotFoundError: 'ccache g++'`。
2. **ccache 实际生效**：构建前后 `ccache -s` 的 cache hit/miss 有变化；或第二次构建（清理单个目标后）出现 hit；证据保留 `ccache -s` 前后快照。
3. **`--no-ccache` 仍可用**：`python3 tools/gem5/build_gem5.py --no-ccache ...`（或等价入口）rc=0 或至少完成 SCons 配置阶段、无 ccache 包装；不得破坏原路径。
4. **行为回归**：`make check-gem5-decode` rc=0、`python3 tools/gem5/check_b6.py` rc=0；gem5 Node/Tiny 代表测试不退化（至少 `check-arch` 或既有 smoke，按现场可用目标）。
5. **范围**：`git status --porcelain -uall` 与 `git diff --name-only` 仅含任务书、`tools/gem5/build_gem5.py`、必要时 `tools/gem5/README.md`、`milestones.md`；`components/**`、`tests/**`、`spec/**`、`Makefile` 零改动。
6. **反例可达 FAIL**：注入一个不可执行的包装脚本或把 `CXX` 改回带空格的字符串 ⇒ 构建/断言 FAIL；`cp` 备份 + `md5sum -c` 还原后回绿；禁 `git checkout/restore/stash`。
7. **门控**：`make check`（L1）rc=0；`make check-no-residue` rc=0。
8. **体例**：完成区 ≤30 行；证据落运行期临时目录（已清理，未归档）；状态置 `待验收`。

## 证据

- 一键证据脚本：构建 + 版本/日志断言 + `ccache -s` 快照 + 门控，输出 `RUN_EXIT`。
- 注入脚本：坏包装脚本 / 旧字符串注入 ⇒ FAIL ⇒ `cp` + `md5sum -c` 还原 ⇒ 回绿，输出 `INJECT_EXIT`。
- 完成区只写结论 + 命令 rc + “运行期证据已清理，未归档”。

## 说明

- 根因是 gem5 SCons 把 `CXX` 当单 argv；不要去改 gem5 源码来“支持带空格命令”，那会扩大组件补丁面。
- 包装脚本是构建入口的职责，放在构建目录，属于运行期产物。
- 不改 `Makefile` 的 `QEMU_STAMP`/`GATE_LOCKED_TARGETS` 语义。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
