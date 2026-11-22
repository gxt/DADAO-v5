# arch scope — Kaiwu-Vast cfx 用例（`tests/arch/`）

本目录**只测 Kaiwu-Vast**（`system` 平台）。QEMU / gem5 / chipyard 是同一 scope 的
三种**承载**，不是三个 scope；用例、驱动、签名薄壳与盘点数据都在本目录内。

- cfx 范围：**0/2/3/4/5/15/32/34/63**（umon/smon/hmon/ptw/cache/hart/pmem/time/power）；
  不含 Tiny、linux-user、jmon/llc/uart。
- 判据：**同一用例在三平台逐槽签名一致**；期望值独立派生自 `spec/` 与
  `.tao/contracts/`，不从实现反推。
- 门控：`tests/arch.yaml` 的 `level: smoke` 代表集由 `run_arch.py` 在 L2/L3
  （`check-arch-smoke` / `check-arch`）现场派生并执行；full 与三平台差分按需/里程碑收口。

## 驱动

```sh
python3 tests/arch/run_arch.py --cfx 4 --platforms qemu --cache-model off
python3 tests/arch/run_arch.py --level smoke --platforms qemu --cache-model off
python3 tests/arch/run_arch.py --case arch-umon-011 --mode smon --platforms qemu
# smoke 不测 cache（off）；cfx5 的 on 用例进按需的 check-arch-vast
python3 tests/arch/run_arch.py --self-test
python3 tests/arch/run_arch.py --list
```

- `--cfx`：0/2/3/4/5/15/32/34/63，可逗号分隔；非法值退出 2。
- `--level`：`smoke` / `full` / `all`（缺省）。按 `tests/arch.yaml` 的 `level`
  **现场派生**代表集；所选集合为空 ⇒ 退出 2（fail-closed，不当作 vacuous 通过）。
- `--platforms`：`qemu` / `gem5` / `chipyard` 逗号列表。`qemu` 与 `gem5`（driver 经
  `tools/testcases/parity/qemu_gem5_shim.py`，`-machine kaiwu-vast`）已接；
  **未实现的 `chipyard`（RTL）fail-closed**：记 `SKIP` 并**非零退出**，禁止静默
  降级为「其余平台通过」。
- `--cache-model`：arch 固定 `on`；传 `off` 退出 2。
- `--case`：只跑 `tests/arch.yaml` 里的一个 id，用于单点复现。
- `--mode`：`hmon` / `smon` / `umon`（缺省 `hmon`），选择运行模式环境
  （hypv/supv/user）。用例的允许集（`tests/arch/modes.yaml`）不含该模式 ⇒ 打印 `N/A` + 原因；
  全部被排除 ⇒ 退出 2（fail-closed）。只有声明多模式的 `kind: driver` 才接
  `--mode`；`kind: asm` 收到非 `hmon` 时**显式**报错，不静默按 hmon 跑。
- `--self-test`：不启动模拟器，只校验索引的 `machine/kind`、各 `expected.yaml` 的
  签名流结构、驱动的 `--selfcheck`，以及 gem5/chipyard 的 fail-closed 探针。
- `--list`：打印 `cfx × case × platform` 计划表，不执行。
- 产物：运行期证据目录下每 case × 平台一份 `signature.bin` + `run.json`
  （进程命令、rc、stdout/stderr 日志路径）；不写固定绝对路径。

退出码：`0` 全通过；`1` 任一用例/平台失败或 SKIP；`2` 用法/配置错误。

## 目录

| 目录/文件 | cfx | 内容 |
|------|-----|------|
| `run_arch.py` | — | 唯一驱动（`--cfx/--platforms/--cache-model/--level/--self-test/--list`） |
| `common/` | — | arch 内共享薄壳：`signature.py` 转调 `tests/shared/signature.py`；`platform.py` 的 qemu/gem5（driver 经 shim）/chipyard（fail-closed）后端 |
| `common/env-{hmon,smon,umon}/` | — | **运行模式环境**（每个模式一个目录，`env.S`；共享 `common/env.lds`）：进入模式、栈、异常向量、退出与签名区；body 与模式解耦（`m16-testcases-015`，见 `common/env-README.md` / `MIGRATION.md`） |
| `umon/` | `cfx0`（user monitor） | SEE/semihosting 执行向量 + cfx 级权限反例（`m5_*.s`，10 条）+ `expected.yaml`；代表迁移用例 `mode_regs.body.S` + 驱动 `check_mode_env.py`（`arch-umon-011`，三模式） |
| `ptw/` | `cfx4`（TLB/PTW） | 15 条 TLB/PTW 探针：载体/生成器 `carrier_tlb.py`（`m16-testcases-010` 由 `tools/testcases/arch/` 迁入）、期望清单 `expected.yaml`（大类 + 子原因符号 + `cause_info` 语义 + 已接线签名流期望 + 来源 §）、驱动型入口 `check_tlb.py`（`kind: driver`）；QEMU 与 gem5（shim）逐条跑，RTL 由 `m16-chipyard-018` |
| `cache/` | `cfx5`（cache） | 寄存器面 RTL 探针 `cfx5_regs.S` + `check_cfx5_regs.py`（`m16-chipyard-016`）；只测寄存器，不测阵列/维护命令效果；暂未登记 `tests/arch.yaml`（chipyard 后端仍 fail-closed） |

其余 cfx 按已有用例增建（`smon/`、`hmon/`、`cache/`、`hart/`、`pmem/`、`time/`、
`power/`）；**不建**空壳子目录。Tiny 的 hmon 用例已迁出 arch（见下）。

## 命名规范

- 目录：`tests/arch/<cfx>/`，cfx 名用 `DADAO-12 §3`（`umon/smon/hmon/ptw/cache/hart/pmem/time/power`）；**不建** `data/` 子目录。
- 汇编载体：`<prefix>_<name>.S`（统一大写 `.S`，即使不预处理）；历史 `m5_*` 前缀保留。
- 链接脚本：`<prefix>_<name>.lds`。
- 驱动：`check_<prefix>_<name>.py`；生成器：`gen_<prefix>_<name>.py`；载体：`<cfx>_<name>.py`。
- body：`<prefix>_<name>.body.S`；env：`common/env-{hmon,smon,umon}/env.S`，共享 `common/env.lds`。
- 期望：`<cfx>/expected.yaml`；全局差异：`tests/arch/expected-divergences.yaml`；模式/权限元数据：`tests/arch/modes.yaml`。
- **禁止**：`data/` 子目录；`tools/` 下新增 arch 专用脚本；随意名（`carrier_*`、`mode_regs.body.S` 等）；新增用例必须登记 `tests/arch.yaml`。
- 根 `tests/arch/README.md` 维护本目录总表；每个 cfx 目录可选一份说明。

## 索引字段

`tests/arch.yaml`（`id` / `file` / `platforms: [system]` / `level` / `requires`，外加）：

- `machine: vast`（arch 条目**必填**，只能 `vast`；Tiny/user 由其它 scope 负责）；
- `kind: asm | driver`（arch 条目**必填**）。`asm` 的 `file` 是 `.s`/`.S` 执行向量；
  `driver` 的 `file` 是本目录内的驱动（如 `arch/ptw/check_tlb.py`），由
  `run_arch.py` 调起。
- 运行模式允许集登记在**并列清单** `tests/arch/modes.yaml`（`m16-testcases-015`）：
  `cases.<id>.modes`（`hmon`/`smon`/`umon`）与 `cases.<id>.reasons`（被排除模式的
  **显式原因**）。与 `tests/arch.yaml` 的 id 集合**双向**核对；缺项/多项/非法
  模式/缺原因由 `run_arch.py`（含 `--self-test`）报红。不写进 `tests/arch.yaml`
  是因为该文件的字段受 `check-tests-index` 白名单约束（未知字段即红）。
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
make check-arch-smoke   # L2：level=smoke 代表集（run_arch.py 现场派生）+ 25 服务 + ptw/tlb carrier
make check-arch         # L3：与 check-arch-smoke 同一套检查（用户 2026-11-22 裁定）
```

- 代表集条数由 `tests/arch.yaml` 的 `level: smoke` **现场派生**，不写死；代表集为空 /
  `run_arch.py` 或索引缺失 / 任一 case 失败 ⇒ 非零（fail-closed，不得 `|| true`）。
- cfx4 PTW/TLB carrier（`ARCH_PTW_CARRIER = tests/arch/ptw/carrier_tlb.py`，15 条）
  **并入 `check-arch-smoke`**；`check-arch` 只依赖 smoke + echo，两目标同跑。
- 旧 `ARCH_CFX_PROBES`（010 后 14 项、无 `tlb`）**不再被 `check-arch` 调用**；
  文件与变量保留，**待 cfx4 迁移任务处理**（`m16-testcases-007`）。
- 25 服务覆盖（`min_rom_probe_046t`）仍是 `check-arch-smoke` 的一部分。
- full 集（`run_arch.py --level full` 的 `arch-ptw-*` 跨平台逐槽比对）**不进** L2/L3，
  按需/里程碑收口跑 `run_arch.py`；L2/L3 的 ptw 面由 carrier 的 15 条 QEMU 探针承担。

## Tiny hmon 已迁出

`arch-hmon-001` 与 `tests/arch/hmon/` 已迁到 `tests/unit/gem5/tiny_hmon/`
（驱动 `tests/unit/gem5/check_tiny_hmon.py`；`m16-testcases-006`）。Tiny hmon 的
**QEMU 同契约探针** `tools/testcases/arch/min_rom_probe_integ007t.py` 仍保留在
`ARCH_CFX_PROBES` 变量内，但该变量**不再被 `check-arch` 调用**——待 cfx4 迁移任务处理。

## 前置

`make install-host`（工具链 + QEMU 取自安装根，ADR-0016 D9）与
`make build-bootrom`（Vast step5 固件与 K1 boot 链在 `tests/ee-vast/`）。
