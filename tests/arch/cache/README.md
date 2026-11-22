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
| `check_cfx5_maint.py` | 独立判据：29 条记录 + 缓存日志时序断言（invalidate 不写回、I\|clean 不进 I 侧且 I 行仍在、flush 删除后重缺失、区间两行、enable=0 命令未发出）；`--self-test` 对每条记录与四种日志变异做可达 FAIL 证明 |

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
