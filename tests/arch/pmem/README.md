# `tests/arch/pmem/` — cfx_pmem（cfxha 32）arch 探针

`spec/DADAO-12 §4.9` 把物理存储器管理放在 `cfx_pmem`（cfxha 32）上：64 KiB
SRAM、`cg12/13/14` 的 PM 区域描述、`cg15` 的 SRAM ↔ PA DMA，以及完成事件
`PMEM_DMA` 作为异步源投递 `cfx_hart`（源身份 = 源 cfxha 32，`ADR-0061` D2）。

本目录承载它的 RTL 用例（`m16-chipyard-022`）。

| 文件 | 作用 |
| --- | --- |
| `pmem.S` | `WumingVastConfig` 上的 cfx_pmem 探针：`pmem_exist`（RO）、`pmem_start/size/attr[0..63]`（RW）、`cg15` DMA 寄存器（`dma_size` 30 位、START 自清、DIR/IRQ_EN 读回、BUSY 期写忽略、DONE/ERROR W1C、ERR_CODE one-hot）；DMA 逐字节搬运（8 B/32 B 往返、3 B 非对齐部分拍保留邻居字节）、四类 setup 错误（SIZE / CFX_RANGE / PA_RANGE / PA_FAULT）与只读 BootROM 可读不可写；完成投递（屏蔽期只置 `cfx_hart cg9 src_pending` bit32 → 放行后 `src_frame` = bit32、pending 投递即清）；同一界 timer(15)+DMA(32) 一次进入、`src_frame` 位图并集、`excp_async_num` 每次进入 +1；`dma_status` W1C 后 pending 落（解除掩码无遗留投递）；覆盖语义（再触发 ⇒ 第二次进入整体覆盖 `cg9`）；`escape imms18 = 2` ⇒ `CFXESC` 且 `cg9` 不变 |
| `pmem.lds` | 固定 `ENTRY` 布局；`--defsym TMODE=<0\|2\|3>` 在**汇编期**选运行模式（同一份 `.S` 出 H/S/U 三个镜像） |
| `check_pmem.py` | 独立判据：期望值现场取自 `spec/DADAO-12` §1/§3.6/§4.9/§5.1/§5.4、`spec/Kaiwu` §1.1/§3、`ADR-0061`、`contract-see` §3/§6.1、`contract-cfx-aliases` 与 `contracts/opcodes.yaml`；`cause_ip` 用 ELF 符号精确断言；`--self-test` 对每条记录做可达 FAIL 证明 |

## 测试机约定（非 spec 常量）

- **`pmem_exist` 读回全 1**：`§4.9` 只说“硬件设置，指示 PM 区域是否存在”，
  本机按“最多 64 个不连续 PM 区域”实现 64 位位图并报告全部存在。该值是
  **测试机约定**，checker 以 `PMEM_REGIONS = 64` 显式声明。
- **DMA 的 PA 可访问面**：RAM 可读可写、BootROM 只可读（`spec/Kaiwu §3`
  测试机 DMA 规定）；其余 PA 属 `PA_FAULT`。

## 运行

```sh
llvm-mc --triple=dadao-unknown-elf -filetype=obj -I <repo> -defsym TMODE=3 \
    tests/arch/pmem/pmem.S -o <out>/pmem_h.o
ld.lld -T tests/arch/pmem/pmem.lds <out>/pmem_h.o -o <out>/pmem_h.elf
simulator-chipyard.harness-WumingVastConfig +permissive +verbose \
    +loadmem=pmem_h.elf +semiout=pmem_h.out +max-cycles=20000000 \
    +permissive-off none
python3 tests/arch/pmem/check_pmem.py --stream pmem_h.out --elf pmem_h.elf \
    --nm llvm-nm --mode 3 --root <repo>
```

`TMODE`：`3` = hmon/hypv（寄存器面 + DMA + 捕获全量），`2` = smon/supv，
`0` = umon/user（两者只验证“各写自己 monitor 掩码行 + 投递”，DMA 在 hypv
里先启动、完成事件落在目标模式）。

## 与 `run_arch.py` 的关系

与 `tests/arch/hart/`、`tests/arch/cache/` 的 RTL 探针同型：直跑 RTL，暂未登记
`tests/arch.yaml`（`run_arch.py` 的 chipyard 后端仍 fail-closed）。
