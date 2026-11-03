# RTL-012t: TileLink CPU 与片内 RAM/ROM

**模块**：rtl
**项目里程碑**：RTL-M3
**依赖**：`RTL-011t`
**状态**：实现完成，门控通过，待用户确认本地提交与上游 PR
**最后更新**：2026-11-02

## 目标

在 RTL-011t 单周期 Core 上实现一个自包含 CPU 子系统：

- 真实 TileLink-UL（无缓存轻量级事务）客户端；
- 64 KiB TileLink BootROM；
- 16 MiB TileLink RAM；
- 64-bit `beatBytes = 8`；
- 从 BootROM 复位执行；
- 不包含 UART、GPIO、Timer、DMA 和外部 DRAM。

## 冻结参数

| 项目 | 值 |
|---|---|
| BootROM base | `0xFFFF_FFFF_0000` |
| BootROM size | 64 KiB |
| RAM base | `0xFC00_0000_0000` |
| RAM size | 16 MiB |
| Reset vector | `0xFFFF_FFFF_0000` |
| TileLink beatBytes | 8 |
| Client source ID | `0` |
| Outstanding requests | 1 |

## 实施分段

| 阶段 | 内容 | 出口条件 |
|---|---|---|
| `012t.1` | ADR、参数和任务书 | 地址、错误和协议范围冻结 |
| `012t.2` | `DADAOTLAdapter` | A/D 握手、背压和 denied 测试通过 |
| `012t.3` | TLROM/TLRAM 拓扑 | ROM 读、RAM 读写和地址覆盖测试通过 |
| `012t.4` | CPU 顶层与 Core 连接 | 从 ROM 取指、RAM 数据闭环 |
| `012t.5` | 程序级集成测试 | 启动、分支、调用、访存和 CFX 通过 |
| `012t.6` | 全量门控 | 回归、hash、RTL tree、elaboration 通过 |
| `012t.7` | PR 审阅 | 文件范围、提交和 PR 前确认 |

## 验收标准

1. Core 不感知 TileLink 细节，仍只使用 `DADAOMemPort`。
2. Adapter 每次只有一个 outstanding transaction。
3. RAM 支持 1/2/4/8-byte 读写和 byte-enable。
4. BootROM 支持取指/load，拒绝 store。
5. Reset 后从 BootROM 执行。
6. TileLink denied 精确映射为 Core `ILLI`，无部分提交。
7. 测试向量和 oracle 在测试前后哈希一致。
8. 全量回归、RTL tree、24-patch 和 Chipyard elaboration 通过。
9. 未经用户确认不提交 Git、不 push、不创建 PR。

## 不包含

- UART、GPIO、Timer、DMA；
- 外部 DRAM；
- Cache 与一致性；
- 多 hart 和多 master；
- Chipyard SystemBus 连接；
- 完整 SoC 验收。

## 实施结果

### 新增 RTL

- `DADAOTileLink.scala`
  - `DADAOTLAdapter`：`DADAOMemPort` 与 TileLink-UL A/D 通道适配；
  - `DADAOTLXbar`：ROM/RAM 地址分派和单 outstanding 控制；
  - `DADAOTLROM`：64 KiB 只读 BootROM manager；
  - `DADAOTLRAM`：16 MiB `SyncReadMem` RAM manager。
- `DADAOCpu.scala`
  - `DADAOCpuTop`：Core、Adapter、Xbar、ROM、RAM 的自包含 CPU 顶层。
- `DADAOTile.scala`
  - Tile 实例改为 `DADAOCpuTop`，不再直接实例化裸 Core。

### 新增测试

- `DADAOTLAdapterSpec`：A/D 握手、背压、窄写掩码、端序和
  `denied → ILLI`。
- `DADAOTLMemorySpec`：ROM 读/拒写、RAM 窄写合并和回读。
- `DADAOCpuSpec`：从 ROM 启动，执行
  `set.zw → st.w → ld.uw → swym`，经 TileLink RAM 将 `0x1234`
  写入 RD3。
- `DADAOBubbleSortSpec`：执行 25 条生成的冒泡排序机器指令，
  输入 `[3, 1, 2]`，验证 RD1–RD3 和 RAM 读回后的 RD8–RD10
  均为 `[1, 2, 3]`。

### 最终门控

```text
Clean PR aggregate     = 31 suites / 199 tests / 199 passed
Failed / skipped       = 0 / 0
Chipyard patches       = 24
Chipyard tree hash     = 0ea0ee1d18c165c85f00719e05664257a225280a
YAML hash files        = 37
Generator deterministic = 1
YAML hash-list SHA-256 = e9e7d3ae0a2873ac0d5a9cb899a1464fe1b923953150e889f6d311d58b5a4730
CHIRRTL bytes          = 4,047,921
SystemVerilog bytes    = 7,067,300
```

- Chipyard patch、RTL tree、Verilog 三类 negative gate：
  `EXIT=0`；
- decoder、exec coverage、静态合法性、保留单元、ALU、memory、
  control 七个独立 oracle：PASS；
- YAML 变更负例门控：PASS；
- `DADAOTop → DADAOTile → DADAOCpuTop → DADAOCore /
  DADAOTLAdapter / DADAOTLROM / DADAOTLRAM` 层级检查：PASS。

干净 PR worktree 的验证分两批执行：首批完成 22 个 suite，剩余
9 个 suite 批次为 61/61 通过；合并 XML 报告为
31 suites / 199 tests / 0 failed。单次 `sbt test` 在末尾 Verilator
make 阶段中断后，`DADAOBubbleSortSpec` 已单独重跑通过。

### 冒泡排序机器码示例

- 汇编/机器码：`tests/rtl/core/RTL-012t-bubble-sort-program.yaml`
- 纯十六进制：`tests/rtl/core/RTL-012t-bubble-sort-program.hex`
- 原始镜像：`tests/rtl/core/RTL-012t-bubble-sort-program.bin`
- 机器码表：`rtl/dadao/src/test/scala/dadao/DADAOBubbleSortProgram.scala`
- 生成器：`tools/rtl/generate_dadao_bubble_sort.py`
- 程序长度：66 条 32-bit 指令，共 264 bytes；
- 输入：`[5, 1, 4, 2, 3]`；
- 输出：`[1, 2, 3, 4, 5]`；
- 最终 RAM beats：
  `0x0001_0002_0003_0004`、`0x0005_0000_0000_0000`；
- BIN：264 bytes，SHA-256
  `e8e92d27b90caffa95b9514f95d6afe33b09f7067aec122f3acd3bdd093799aa`；
- HEX：66 行，SHA-256
  `02f12adca6af17d808ace121593629de2abd718a0ecead6f7c18dc4f01dbfde8`；
- `DADAOBubbleSortSpec`：1 suite / 1 test / PASS。

### Verilator 后端

- Clab 已安装 Verilator `5.022`；
- `DADAOBubbleSortSpec` 使用 `VerilatorBackendAnnotation`；
- Verilator 5.022 的 PCH 并行构建存在竞争，通过
  `VM_PARALLEL_BUILDS=0` 和 `MAKEFLAGS=-e` 改为合并翻译单元；
- 专用运行脚本：

  ```bash
  bash tools/rtl/run_verilator_test.sh dadao.DADAOBubbleSortSpec
  ```

- 5 元素程序 Verilator 实测约 67 秒；
- 3 元素对照测试由 Treadle 约 634 秒降至 Verilator 约 53 秒，
  约 12 倍加速。

### 未执行

- 未 commit、未 push、未创建 PR，等待用户逐项确认。
- 未接入 UART、外部 DRAM、Chipyard SystemBus、Cache 或多 hart。
