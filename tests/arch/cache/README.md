# `tests/arch/cache/` — cfx5（cache）arch 探针

本目录按 `m16-testcases-006` 的落点放 cfx5 用例。`m16-chipyard-016` 只接寄存器面；
`m16-chipyard-017` 把 `cache_ctrl` 接到 I/D 阵列，本目录随之增加维护命令载体。

| 文件 | 作用 |
| --- | --- |
| `cfx5_regs.S` | `WumingVastConfig` 上的 cfx5 寄存器面探针：读 `cache_exist`/`cache_enable`，写读 `cache_enable`/`cache_addr_start`/`cache_addr_size`，`cache_ctrl` 的 no-op / 合法 / 非法编码，以及读 WO、写 RO、保留 rc 的 `CFXREG` |
| `cfx5_regs.lds` | 固定 `ENTRY` 布局 + 四个故障例的「回落点 = aip + 16」链接器回读断言 |
| `check_cfx5_regs.py` | 独立判据：期望值现场取自 `.tao/contracts/contract-cache.md` / `contract-see.md` §6.1 / `contracts/opcodes.yaml`；`--self-test` 对每条记录做可达 FAIL 证明 |
| `cfx5_maint.S` | 维护命令探针：I 侧（clean no-op / invalidate 单行与区间 / flush）、D 侧（invalidate 丢弃脏行 / clean 写回 / flush 写回+删除；PA 单行、PA 区间、all）、`cache_enable=0` 不维护、无行/不可缓存 PA 无效果、非法编码 ⇒ `CFXREG`；D 侧真值以**取指端口**独立观测 |
| `cfx5_maint.lds` | 探针自己的链接布局：核内 SRAM 的 `.text`/`.faultpad`/`.testdata` + PA RAM 的页表/数据行/代码行；三个故障例的回落点 ASSERT |
| `gen_cfx5_maint_tables.py` | 几何/页表/控制字/magic/期望值单一真源（控制字三维字段与 CFXREG 位号现场取自合约）；`--check-geometry` 自检行分组与区间不跨页 |
| `check_cfx5_maint.py` | 独立判据：31 条记录 + 缓存日志时序断言（invalidate 不写回、I\|clean 不进 I 侧且 I 行仍在、flush 删除后重缺失、区间两行、enable=0 命令未发出、`addr_start` 56 位不截断/不按低 48 位别名）；`--self-test` 对每条记录与四种日志变异做可达 FAIL 证明 |

## 运行

```sh
python3 tests/arch/cache/gen_cfx5_maint_tables.py > <out>/cfx5_maint_tables.inc
llvm-mc --triple=dadao-unknown-elf -filetype=obj -I <repo> -I <out> \
    tests/arch/cache/cfx5_maint.S -o <out>/cfx5_maint.o
ld.lld -T tests/arch/cache/cfx5_maint.lds <out>/cfx5_maint.o -o <out>/cfx5_maint.elf
simulator-chipyard.harness-WumingVastConfig +permissive +verbose \
    +loadmem=cfx5_maint.elf +semiout=cfx5_maint.out +max-cycles=5000000 \
    +permissive-off none
python3 tests/arch/cache/check_cfx5_maint.py \
    --stream cfx5_maint.out --log <sim log> --root <repo>
```

`cfx5_maint.S` **只能**在 `WumingVastConfig` 上跑：`Kaiwu-Tiny` 不实现 cfx5
（`contract-cache` CACHE-28）。探针自身在核内 SRAM（不经翻译、不进缓存），
所以整侧 invalidate/flush 不会打断探针；代码行与数据行按 PA 落在 PA RAM，
`+loadmem=` 装入初值。

## 与 `run_arch.py` 的关系

本载体目前是**直跑 RTL 探针**（与 `tools/chipyard/*` 的既有探针同型），尚未登记
`tests/arch.yaml`：`run_arch.py` 的 chipyard 后端仍 fail-closed，且同 scope 的
其它 cfx（0/2/4/15/32/34）在 RTL 侧尚未接入。等 chipyard arch 载体落地后，再把
本文件按 `kind: asm` 或 `kind: driver` 登记进索引。

## 三方 cfx5 用例（`m16-testcases-009`）

寄存器面/维护命令通过 `run_arch.py --cfx 5` 在 QEMU / gem5 / RTL 上跑**同一组
case、同一槽序**；期望值由 `cache_oracle.py` 现场从 `contract-cache` /
`contract-see §6.1` / `contracts/opcodes.yaml` 派生，登记在 `expected.yaml`。

| case | 内容 | 模式 | 槽 | 来源条款 |
| --- | --- | --- | --- | --- |
| `arch-cache-001` | 寄存器面（exist/enable/ctrl/addr_start/addr_size）+ D 单行 invalidate/clean/flush + I 侧 invalidate/flush 后取指重取 + `enable=0` 不维护 + 编码 no-op/无行 PA 无效果 + **I+D 同选**（`[15:14] = 11`）的 clean/invalidate/flush | hmon/smon/umon | 21 | CACHE-03/06/07/08/12/13/14/15/16/18/19/20/21/22/27 |
| `arch-cache-002` | D 侧范围：PA 单行边界、PA 区间（相邻两行 + 区间外一行）、all | hmon/smon/umon | 12 | CACHE-15/16/17/20 |
| `arch-cache-003` | 拒绝面：读 WO、写 RO、保留 rc、非法编码 ⇒ `CFXREG`，且非法命令不产生维护动作；`enable=0` 不抑制编码校验 | hmon | 16 | CACHE-03/04/08/11/14/25/27 |
| `arch-cache-004` | `cache-model=off`（CACHE-27）：cfx5 存在、`exist=0`、寄存器可访问、合法命令接受无效果、非法编码仍 ⇒ `CFXREG` | hmon（`cache_model: "off"`） | 15 | CACHE-27 |

| 文件 | 作用 |
| --- | --- |
| `cache.body.S` | QEMU/gem5 的测试 body（`CACHE_CASE=1..4`）；只写「测什么」，模式环境在 `common/env-*` |
| `cache_oracle.py` | 唯一期望源：契约/opcode 现场解析 + 四条 case 的槽序/期望 + RTL 地址/PTE include |
| `check_cache.py` | QEMU/gem5 驱动（env 镜像、`-d cpu` 模式观测、签名流逐槽） |
| `cache_rtl.S` / `cache_rtl.lds` | RTL 承载（`CCASE=1..3` × `TMODE=3/2/0`；页面/控制字来自 `cache_rtl_tables.inc`） |
| `check_cache_rtl.py` | RTL 驱动（同一槽序 + `+verbose` 模式观测 + 缓存日志断言）；`arch-cache-001/002` 的 hmon/smon/umon 三种模式都跑（`m16-chipyard-027` 起 cfx5 开 `commonRows`），只有 `arch-cache-004` 记 GAP |
| `expected.yaml` | 签名流登记（与 `cache_oracle` 双向核对） |
| `rtl-coverage.yaml` | RTL 覆盖/缺口（`arch-cache-004` = `cache-model=off` 无 RTL 开关 ⇒ gap） |

**I+D 同选（`ISS-517`，CACHE-21）**：控制字的**操作（`[1:0]`）与范围（`[3:2]`）
两维由两侧共用**，`[15:14] = 11` 只多选了一个侧，不会让两侧各带一套操作
（`contract-cache` CACHE-09/10）⇒ 「同选 + 合法操作」只有三条命令：

- `11|invalidate`：I 侧丢弃 + D 侧丢弃（含脏行，不写回）⇒ 读回**内存旧值**；
- `11|flush`：I 侧丢弃（≡invalidate）+ D 侧写回后丢弃 ⇒ 取指重取**新码**
  （两侧都生效才成立；「先 I 后 D」由 RTL 缓存日志核）；
- `11|clean`：I 侧 no-op（CACHE-19）+ D 侧写回（行保留）⇒ 再失效后读回新值。

任务书写的「`I|invalidate` + `D|clean`」这种**逐侧不同操作**的组合在本编码下
不可表达（操作是单一字段）；`11|flush` 的 D 侧正是「写回（clean 的可观测效果）
+ 丢弃」，同选项因此按上面三条覆盖。

**已知三方口径**：

- `arch-cache-004` 只在 QEMU/gem5 上判（RTL 无 `cache-model` 开关，`rtl-coverage.yaml`
  登记 `gap`，`run_arch` 记 `GAP`，不是 PASS）。
- `arch-cache-001/002` 的 smon/umon 在 RTL 上**已可达**（`DIV-16` 已删除）：
  `cache_rtl.S` 在 hypv 打开目标 cfx5 的 supv/user 行（只清源 cfx = hmon 的位）
  与 `cg3 rc12 = 0x8`，再经 `cfx_hmon` 的 `<mode>` 行降模式；`inner_cfx_code`
  保持 hmon，两轴判权不因降模式被放宽。
- I 侧 `clean` 是 no-op（CACHE-19）在**签名槽层面不可判**：QEMU 的 D 写回会经 RAM
  写自动失效 TB（`m16-qemu-003` 新发现①），「D clean 后未发 I 命令仍取到新码」在
  QEMU 上恒成立。该点由 RTL 承载的缓存日志独立断言（`icache` 不得出现 `op=clean`），
  差别登记在 `tests/arch/expected-divergences.yaml`（DIV-15）。
- **DMA 直读**：本目录的 D 侧可见性用「`invalidate`/`flush` 后重新填充读回内存」观察
  （`d_invalidate_single`/`d_clean_single`/`d_flush_single`），没有调用 `cfx_pmem`
  的 DMA 直读；DMA 直读需要一条访问 `cfx_pmem` SRAM 的独立子用例（PTW 之外的
  内部窗口），未纳入本任务（见 `vast-arch-inventory.md` 的未覆盖项）。
- U 模式：`common/env-umon/env.S` 在拷贝 body/tail 后、降模式前，对**声明了 cfx5**
  的用例做一次 `D|flush|all`（`ENV_CFX_ACCESS_5` 门控），否则 `cache-model=on`
  时 user 取指读真实内存会看到未写回的 0 字（QEMU/gem5 的取指不经影子 cache）。

## 运行

```sh
python3 tests/arch/run_arch.py --cfx 5 --platforms qemu,gem5,chipyard --cache-model on
python3 tests/arch/run_arch.py --cfx 5 --platforms qemu,gem5 --mode smon
python3 tests/arch/run_arch.py --self-test
```
