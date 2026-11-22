# `tests/arch/cache/` — cfx5（cache）arch 探针

本目录按 `m16-testcases-006` 的落点放 cfx5 用例。当前只有**寄存器面**载体
（`m16-chipyard-016`）；I/D 阵列与维护命令效果是后续任务，不在本目录。

| 文件 | 作用 |
| --- | --- |
| `cfx5_regs.S` | `WumingVastConfig` 上的 cfx5 寄存器面探针：读 `cache_exist`/`cache_enable`，写读 `cache_enable`/`cache_addr_start`/`cache_addr_size`，`cache_ctrl` 的 no-op / 合法 / 非法编码，以及读 WO、写 RO、保留 rc 的 `CFXREG` |
| `cfx5_regs.lds` | 固定 `ENTRY` 布局 + 三个故障例的「回落点 = aip + 16」链接器回读断言 |
| `check_cfx5_regs.py` | 独立判据：期望值现场取自 `.tao/contracts/contract-cache.md` / `contract-see.md` §6.1 / `contracts/opcodes.yaml`；`--self-test` 对每条记录做可达 FAIL 证明 |

## 运行

```sh
llvm-mc --triple=dadao-unknown-elf -filetype=obj -I <repo> cfx5_regs.S -o cfx5_regs.o
ld.lld -T cfx5_regs.lds cfx5_regs.o -o cfx5_regs.elf
simulator-chipyard.harness-WumingVastConfig +permissive +verbose \
    +loadmem=cfx5_regs.elf +semiout=cfx5_regs.out +max-cycles=5000000 \
    +permissive-off none
python3 check_cfx5_regs.py --stream cfx5_regs.out --root <repo>
```

`cfx5_regs.S` **只能**在 `WumingVastConfig` 上跑：`Kaiwu-Tiny` 不实现 cfx5
（`contract-cache` CACHE-28），第一条 `cfx2rd cfx_cache` 就是 `CFXREG`。
本任务只接寄存器面，探针不断言阵列数据，也不依赖维护命令的副作用。

## 与 `run_arch.py` 的关系

本载体目前是**直跑 RTL 探针**（与 `tools/chipyard/*` 的既有探针同型），尚未登记
`tests/arch.yaml`：`run_arch.py` 的 chipyard 后端仍 fail-closed，且同 scope 的
其它 cfx（0/2/4/15/32/34）在 RTL 侧尚未接入。等 chipyard arch 载体落地后，再把
本文件按 `kind: asm` 或 `kind: driver` 登记进索引。
