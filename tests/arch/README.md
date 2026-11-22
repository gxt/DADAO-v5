# arch scope — Kaiwu-Vast cfx 用例（`tests/arch/`）

本目录**只测 Kaiwu-Vast**（`system` 平台）。QEMU / gem5 / chipyard 是同一 scope 的
三种**承载**，不是三个 scope；用例、驱动、签名薄壳与盘点数据都在本目录内。

- cfx 范围：**0/2/3/4/5/15/32/34/63**（umon/smon/hmon/ptw/cache/hart/pmem/time/power）；
  不含 Tiny、linux-user、jmon/llc/uart。
- 判据：**同一用例在三平台逐槽签名一致**；期望值独立派生自 `spec/` 与
  `.tao/contracts/`，不从实现反推。
- 仿真**不进常规门控**（L2/L3）；按需/里程碑收口时跑 `run_arch.py`。

## 驱动

```sh
python3 tests/arch/run_arch.py --cfx 4 --platforms qemu --cache-model on
python3 tests/arch/run_arch.py --self-test
python3 tests/arch/run_arch.py --list
```

- `--cfx`：0/2/3/4/5/15/32/34/63，可逗号分隔；非法值退出 2。
- `--platforms`：`qemu` / `gem5` / `chipyard` 逗号列表。**未实现的后端 fail-closed**：
  记 `SKIP` 并**非零退出**，禁止静默降级为「其余平台通过」。
- `--cache-model`：arch 固定 `on`；传 `off` 退出 2。
- `--case`：只跑 `tests/arch.yaml` 里的一个 id，用于单点复现。
- `--self-test`：不启动模拟器，只校验索引的 `machine/kind`、各 `expected.yaml` 的
  签名流结构、驱动的 `--selfcheck`，以及 gem5/chipyard 的 fail-closed 探针。
- `--list`：打印 `cfx × case × platform` 计划表，不执行。
- 产物：运行期证据目录下每 case × 平台一份 `signature.bin` + `run.json`
  （进程命令、rc、stdout/stderr 日志路径）；不写固定绝对路径。

退出码：`0` 全通过；`1` 任一用例/平台失败或 SKIP；`2` 用法/配置错误。

## 目录

| 目录/文件 | cfx | 内容 |
|------|-----|------|
| `run_arch.py` | — | 唯一驱动（`--cfx/--platforms/--cache-model/--self-test/--list`） |
| `common/` | — | arch 内共享薄壳：`signature.py` 转调 `tests/shared/signature.py`；`platform.py` 的 qemu/gem5/chipyard 后端骨架 |
| `data/` | — | scope 内入库数据（三平台 cfx 盘点矩阵），不成册、不进 `tests/arch.yaml` |
| `umon/` | `cfx0`（user monitor） | SEE/semihosting 执行向量 + cfx 级权限反例（`m5_*.s`，10 条）+ `expected.yaml` |
| `ptw/` | `cfx4`（TLB/PTW） | 15 条 TLB/PTW 探针的期望清单 `expected.yaml`（大类 + 子原因符号 + `cause_info` 语义 + 已接线签名流期望 + 来源 §）；驱动型入口 `check_tlb.py`（`kind: driver`），转调既有 `tools/testcases/arch/min_rom_probe_tlb.py`（判据未变） |

其余 cfx 按已有用例增建（`smon/`、`hmon/`、`cache/`、`hart/`、`pmem/`、`time/`、
`power/`）；**不建**空壳子目录。Tiny 的 hmon 用例已迁出 arch（见下）。

## 索引字段

`tests/arch.yaml`（`id` / `file` / `platforms: [system]` / `level` / `requires`，外加）：

- `machine: vast`（arch 条目**必填**，只能 `vast`；Tiny/user 由其它 scope 负责）；
- `kind: asm | driver`（arch 条目**必填**）。`asm` 的 `file` 是 `.s`/`.S` 执行向量；
  `driver` 的 `file` 是本目录内的驱动（如 `arch/ptw/check_tlb.py`），由
  `run_arch.py` 调起。
- 门控：`make check-tests-index`（L1，静态）校验字段、`machine/kind` 取值与
  `file` 存在；条数现场统计，不写死。

## 观测通道

**签名流 = 观测点的判据载体**：每个观测点把实测 8 字节写进
`tests/shared/asm/signature.inc` 约定的签名区（预填 `0xdeadbeef`；漏跑 ⇒ host 报
「槽 N 未写」），收尾整段输出，host 侧用 `tests/shared/signature.py` 按槽比对。
机制只有一份：汇编侧 `signature.inc`、host 侧 `signature.py`；`tests/arch` 的
word-builder 探针用同一个 `.py` 的 `Emitter`，`common/signature.py` 只做薄壳重导出。

退出码（semihosting `SYS_EXIT`：`0x00` 通过、`0x01`–`0x7F` = 镜像内第 N 条断言失败）
只作**镜像级兜底**：已接线的检查以签名流比对为准。`ptw` 的
`arch-ptw-002/006/007` 已接线，期望值登记在 `expected.yaml` 的 `signature:` 并由
驱动 `--selfcheck` 双向核对。

## 门控

```sh
make check-arch-smoke   # L2：arch 代表集（SEE/semihosting + cfx 权限 + 25 服务覆盖）
make check-arch         # L3：check-arch-smoke + cfx min-ROM 场景探针（含 ptw 的 15 条）
```

`run_arch.py` **不在** L2/L3 内（仿真按需/里程碑收口跑）。

## Tiny hmon 已迁出

`arch-hmon-001` 与 `tests/arch/hmon/` 已迁到 `tests/unit/gem5/tiny_hmon/`
（驱动 `tests/unit/gem5/check_tiny_hmon.py`；`m16-testcases-006`）。Tiny hmon 的
**QEMU 同契约探针** `tools/testcases/arch/min_rom_probe_integ007t.py` 仍在
`check-arch` 的 `ARCH_CFX_PROBES` 内——本次只移用例与 gem5 驱动，不改门控集合。

## 前置

`make install-host`（工具链 + QEMU 取自安装根，ADR-0016 D9）与
`make build-bootrom`（Vast step5 固件与 K1 boot 链在 `tests/ee-vast/`）。
