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
| `common/env-{hmon,smon,umon}/` | — | **运行模式环境**（每个模式一个目录，`env.S`；共享 `common/env.lds`）：进入模式、栈、异常向量、退出与签名区；body 与模式解耦（`m16-testcases-015`，见 `common/env-README.md` / `common/env-MIGRATION.md`） |
| `umon/` | `cfx0`（user monitor） | SEE/semihosting 执行向量 + cfx 级权限反例（`m5_*.S`，10 条）+ `expected.yaml`；代表迁移用例 `umon_mode_regs.body.S` + 驱动 `common/check_mode_env.py`（`arch-umon-011`，三模式）；**fence 基础验证** `umon_fence.py`（载体）/ `check_fence.py`（驱动，`arch-umon-012` 放行面三模式、`arch-umon-013` 保留面 hmon）+ `gen_fence_rtl.py` / `check_fence_rtl.py`（按需 RTL 承载，`fence_rtl.lds`）；**cfx0+cfx2 寄存器面 RTL 探针** `cfx02_regs.S` + `check_cfx02_regs.py`（`m16-chipyard-019`，47 条记录）；**U/S/H 模式进入路由 RTL 探针** `mode_entry.S` + `check_mode_entry.py`（`m16-chipyard-020`，同一份 case 链接 TMODE=0/2/3，14/21/14 槽）；cfx0/cfx2 两个 RTL 探针暂未登记 `tests/arch.yaml`——chipyard 后端仍 fail-closed，且 hmon 模式环境只在 QEMU/gem5 载体上可用 |
| `ptw/` | `cfx4`（TLB/PTW） | 15 条 TLB/PTW 探针：载体/生成器 `ptw_carrier_tlb.py`（`m16-testcases-010` 由 `tools/testcases/arch/` 迁入）、期望清单 `expected.yaml`（大类 + 子原因符号 + `cause_info` 语义 + 已接线签名流期望 + 来源 §）、驱动型入口 `check_tlb.py`（`kind: driver`）；QEMU 与 gem5（shim）逐条跑，RTL 由 `m16-chipyard-018` |
| `cache/` | `cfx5`（cache） | 寄存器面 RTL 探针 `cfx5_regs.S` + `check_cfx5_regs.py`（`m16-chipyard-016`）；I/D 维护命令 RTL 探针 `cfx5_maint.S` + `gen_cfx5_maint_tables.py` + `check_cfx5_maint.py`（`m16-chipyard-017`，记录 + 缓存日志时序）；暂未登记 `tests/arch.yaml`（chipyard 后端仍 fail-closed） |
| `hart/` | `cfx15`（cfx_hart） | cg8 管理寄存器 + cg9 异步现场 + TIMER 投递 RTL 探针 `cfx15.S` + `check_cfx15.py`（`m16-chipyard-021`；`TMODE=3/2/0` 出 H/S/U 三个镜像，一份 case）；暂未登记 `tests/arch.yaml` |

其余 cfx 按已有用例增建（`smon/`、`hmon/`、`cache/`、`hart/`、`pmem/`、`time/`、
`power/`）；**不建**空壳子目录。Tiny 的 hmon 用例已迁出 arch（见下）。

## fence 基础验证（`m16-testcases-012`，cfx0）

`fence cfxHA, immu18` 按 `cfxha` 选资源域（`cfx0` = all cfx），`immu18` 的
`hb`（`[17:12]`）SBZ、`pred`（`[11:6]`）/`succ`（`[5:0]`）为六位访问类型掩码
（`cr/cw/ci/co/mr/mw`）。保留 cfxha 或 `hb ≠ 0` ⇒ `ILLI`
（`spec/SimRISC-11 §5`；合法集见 `contracts/opcodes.yaml` 的
`fence_ciii_cfx`）。

| case | 内容 | 模式 | 尺寸 |
|------|------|------|------|
| `arch-umon-012` | 放行面：`cfx0` 零掩码/全掩码、六个资源域各一位、指定 cfx（3/4/5/32/33/34）、允许集边界（15/62/63） | hmon/smon/umon 各一次 | 17 槽 |
| `arch-umon-013` | 保留面：采样 16/17/18、边界 6/14/31/35/61、`hb=1` 与 `hb` 全 1 | hmon（原因见 `modes.yaml`） | 10 槽 |

- 载体 `umon/umon_fence.py` 现场生成 4 MiB BootROM 镜像（power → hmon 预置
  页表/PTW → body），QEMU 与 gem5（经 `qemu_gem5_shim.py`）跑**同一份字节**；
  模式切换沿用 `common/env-README.md` 的协议（`cfx_hmon` 的 `<mode>` 行
  `switch_run_mode` + `excp_vector` + `trap cfx_hmon`），并用 `-d cpu` 的 `MODE:`
  现场核对 body 实际运行模式（不由 body 自述）。
- 签名槽 = 一个 probe：`0` = fence 正常执行；`ILLI` = 异常（精确值现场从
  `contract-see §6.1` 派生）。放行面在 smon/umon 用「fence 之后写槽」作见证；
  保留面需要当前模式监视器记录 cause（`DADAO-12 §5.2`），故只在 hmon。
- **RTL 按需**：`gen_fence_rtl.py` 从同一张探针表生成 `.S`，
  `check_fence_rtl.py` 经 `tools/testcases/lib/chipyard_engine.py` 在
  `WumingVastConfig` 上跑并逐槽比对（RTL 测试体固定 hypv、同步异常固定进
  hmon；`+loadmem` + semihosting）。`run_arch.py` 的 chipyard 后端仍
  fail-closed（`m16-chipyard-018` / 按需 `check-arch-vast`），故 RTL 不进
  `run_arch` 的常规路径。

**未覆盖项（显式登记，不假装全覆盖；用户 2026-11-22 裁定完整覆盖暂不做）**：

- 全部 cfxha（0–63）× `pred` × `succ` 六位组合的穷举（6 × 6 × 6 × 6 位域组合）
  不做；只取每个资源域一位、`pred = succ`、以及零掩码/全掩码。
- `pred ≠ succ` 的交叉组合、单侧掩码（只 `pred` 或只 `succ`）不做。
- 资源域掩码的**顺序/可见性语义**不测：本实现（QEMU/gem5/RTL）均为「本 hart
  已顺序执行」的 no-op 语义，DMA 不等待（`spec/SimRISC-11 §5`），无 Guest 侧
  可观测差异；只在「不产生异常」层面覆盖。
- cfx1（jmon）在 arch 范围外（`tests/arch/README.md` 顶部 cfx 范围），只按其
  编码合法性间接落在允许集里（未单列 probe）。
- 保留集只采样 6/14/16/17/18/31/35/61（含边界），其余保留编号不逐个跑。

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
- `cases.<id>.cfx_access`（可选，`m16-testcases-017`）：该用例在目标模式下需要
  访问的 cfx 列表（`umon`/`smon`/`hmon`/`ptw`/`cache`/`hart`/`pmem`/`time`/`power`）。
  环境据此在**降模式之前**（仍在 hypv、源 cfx = cfx_hmon）打开目标 cfx 的
  `<mode>` 行来源掩码（`DADAO-12 §3`，只清源 cfx 位）与 `cg_reg_deleg`
  （supv 侧前提），并把**未声明**的 cfx 收窄（源 cfx 位置 1 ⇒ 未声明访问
  `CFXPERM`），退出还原打开的项并回读校验；声明由 `common/platform.py` 的
  `--cfx-access` 交给驱动、驱动再落成逐 cfx 的 `--defsym ENV_CFX_ACCESS_<n>=1`。
  非法/重复/空列表、或只有 `hmon` 的用例上声明 ⇒ `run_arch.py` 报配置错误。
  语义、失败码与已知边界见 `common/env-README.md`。
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
- cfx4 PTW/TLB carrier（`ARCH_PTW_CARRIER = tests/arch/ptw/ptw_carrier_tlb.py`，15 条）
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
