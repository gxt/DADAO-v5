# RTL-012t PR 提交清单

**状态**：用户已确认“核心 RTL PR + 可选 Chipyard 集成 PR”的拆分方式
**日期**：2026-11-02
**当前上游基线**：DADAO-v5 `c6fbcbae`
**建议提交作者**：`fanjie kong <3063598262@qq.com>`
**建议主分支名**：`pr/rtl-m1-tilelink-cpu`

## 一、原则

1. 上游 PR 只提交 DADAO 仓库自身需要长期维护的源码、测试、向量、
   工具和设计记录。
2. 不提交完整 Chipyard 仓库、Chipyard submodule（子模块）或 build
   缓存。
3. `components/chipyard/` 是当前本地可重建 overlay（覆盖层），
   `ADR-0036` 将其定义为受控例外；默认不进入核心 RTL PR。
4. 课程报告、原始输入文本、Clab 环境脚本和构建产物不进入上游 PR。
5. 任何 commit、push 或 PR 创建前仍需用户再次确认。

## 二、核心 RTL PR

### 2.1 目标

提交 SimRISC M1 单周期整数 Core、TileLink-UL CPU 子系统、ROM/RAM、
测试向量、独立 oracle 和验证门控。

### 2.2 包含内容

| 路径 | 内容 |
|---|---|
| `rtl/dadao/build.sbt` | 独立 RTL sbt 工程 |
| `rtl/dadao/project/build.properties` | sbt 版本锁定 |
| `rtl/dadao/src/main/scala/dadao/` | 权威 Chisel RTL |
| `rtl/dadao/src/test/scala/dadao/` | 单元、集成、oracle 和负例测试 |
| `tests/rtl/core/*.yaml` | 固定测试向量 |
| `tests/rtl/core/RTL-012t-bubble-sort-program.hex` | 冒泡排序机器码 |
| `tests/rtl/core/RTL-012t-bubble-sort-program.bin` | 可复现 ROM/RAM 测试镜像 |
| `tools/rtl/generate_dadao_decoder_table.py` | 译码表生成器 |
| `tools/rtl/generate_dadao_exec_table.py` | 执行表生成器 |
| `tools/rtl/generate_dadao_bubble_sort.py` | 冒泡排序机器码生成器 |
| `tools/rtl/check_dadao_*oracle*.py` | 独立 oracle 检查器 |
| `tools/rtl/check_dadao_*negative.sh` | 负例门控 |
| `tools/rtl/check_dadao_vector_hashes.sh` | 向量哈希门控 |
| `tools/rtl/check_rtl_tree.py` | RTL 文件与关键结构检查 |
| `tools/rtl/check_rtl_tree_negative.sh` | RTL 树负例门控 |
| `.tao/adr/adr-0039-simrisc-0.5.5-upgrade.md` | SimRISC 0.5.5 适配 ADR |
| `.tao/adr/adr-0040-ret-rb0-high16-zero.md` | ret/RB0 语义 ADR |
| `.tao/adr/adr-0047-tilelink-cpu-subsystem.md` | CPU 子系统 ADR |
| `.tao/tasks/rtl/RTL-006m-*` 至 `RTL-012t-*` | M1、Core、TileLink 任务记录 |

RTL 顶层关系：

```text
DADAOTile
  -> DADAOCpuTop
       -> DADAOCore
       -> DADAOTLAdapter
       -> DADAOTLXbar
            -> DADAOTLROM
            -> DADAOTLRAM
```

`DADAOTile.scala`、`DADAOConfig.scala`、`DADAOElaborator.scala` 仍随
核心源码提交，但它们不复制任何 Chipyard 源码；独立 `build.sbt`
明确把这 3 个文件排除在 standalone（独立）编译之外。

### 2.3 核心 PR 验证

```text
M1 instruction identities       = 156 / 156
Clean PR aggregate verification = 31 suites / 199 tests / PASS
BubbleSort verification         = 1 suite / 1 test / PASS
Bubble input/output             = [5,1,4,2,3] -> [1,2,3,4,5]
Bubble program size             = 66 instructions / 264 bytes
Bubble BIN SHA-256              = e8e92d27b90caffa95b9514f95d6afe33b09f7067aec122f3acd3bdd093799aa
YAML vectors                    = 37
RTL tree                        = PASS
Negative gates                  = PASS
Independent oracles             = PASS
```

干净 PR worktree 已通过 XML 聚合验证：31 suites / 199 tests /
0 failed。验证分两批执行：

- 首批 22 suites；
- 剩余 9 suites / 61 tests；
- Verilator 冒泡排序测试单独重跑；
- 37 个 YAML 的哈希清单 SHA-256：
  `e9e7d3ae0a2873ac0d5a9cb899a1464fe1b923953150e889f6d311d58b5a4730`。

## 三、可选 Chipyard 集成 PR

### 3.1 目标

只在作者同意复现 Chipyard 1.14.0 elaboration（硬件展开）时提交。
该 PR 不包含 Chipyard 本体，只包含针对精确 commit 的可重建补丁。

### 3.2 包含内容

| 路径 | 内容 |
|---|---|
| `components/chipyard/README.md` | 集成说明 |
| `components/chipyard/changelog.md` | 版本与验证记录 |
| `components/chipyard/series` | 24 个 patch 的应用顺序 |
| `components/chipyard/patches/` | Chipyard 覆盖补丁 |
| `tools/rtl/chipyard_patch.sh` | overlay 重建与导出 |
| `tools/rtl/check_chipyard_patch.py` | patch 数量和树哈希检查 |
| `tools/rtl/check_chipyard_patch_negative.sh` | patch 负例门控 |
| `tools/rtl/build_dadao_verilog.py` | CHIRRTL/SystemVerilog 构建 |
| `tools/rtl/check_dadao_verilog.py` | 生成结果层级检查 |
| `tools/rtl/check_dadao_verilog_negative.sh` | Verilog 负例门控 |
| `.tao/adr/adr-0036-dadao-chipyard-overlay-exception.md` | 本地例外 ADR |
| `.tao/tasks/rtl/RTL-001k-*` 至 `RTL-005t-*` | Chipyard overlay 任务记录 |

固定依赖：

```text
Chipyard tag     = 1.14.0
Chipyard commit  = 0acc1e1de2d3284bcd4d876956932a013ffe1949
Chisel           = 6.7.0
firtool          = 1.75.0
Verilator        = 5.022
```

验证证据：

```text
Chipyard patches = 24
Tree hash        = 0ea0ee1d18c165c85f00719e05664257a225280a
CHIRRTL bytes    = 4,047,921
Verilog bytes    = 7,067,300
Elaboration      = PASS
```

## 四、明确排除

### 4.1 完整 Chipyard

- Chipyard Git 仓库本体；
- `generators/rocket-chip/`、`tools/cde/`、
  `generators/diplomacy/`、`generators/hardfloat/` 等 submodule；
- Chipyard `.conda-env/`；
- Verilator C++ 生成目录和 native 二进制。

### 4.2 本地环境

- SSH 私钥、公钥、密码、`rd_password`；
- Clab/WSL 用户目录和绝对路径配置；
- `tools/rtl/clab-env.sh`；
- `tools/rtl/run_verilator_test.sh`；
- `.cache/`、Coursier、Ivy、Conda 包缓存；
- 完整磁盘上的运行日志和临时构建副本。

### 4.3 报告和原始输入

- `20260929report/`
- `20261013report/`
- `20261020report/`
- `20261027report/`
- `20261013report.txt`
- `1020course.txt`
- `1027report.txt`

这些内容保留在本地和 Clab 记录中，不进入上游 PR。

## 五、提交前检查

```bash
git status --short
git diff --check
python3 tools/rtl/check_rtl_tree.py
sbt -batch test
bash tools/rtl/run_verilator_test.sh dadao.DADAOBubbleSortSpec
```

若创建 Chipyard 集成 PR：

```bash
python3 tools/rtl/check_chipyard_patch.py
bash tools/rtl/check_chipyard_patch_negative.sh
bash tools/rtl/check_dadao_verilog_negative.sh
```
