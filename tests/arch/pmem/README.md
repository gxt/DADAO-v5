# `tests/arch/pmem/` — cfx_pmem（cfxha 32）DMA 完成中断 + 同界多源

`spec/DADAO-12 §4.9` 把物理存储器管理放在 `cfx_pmem`（cfxha 32）上：64 KiB
SRAM、`cg12/13/14` 的 PM 区域描述、`cg15` 的 SRAM ↔ PA DMA，以及完成事件
`PMEM_DMA` 作为异步源投递 `cfx_hart`（源身份 = 源 cfxha 32，`ADR-0061` D2）。
DMA 与 D-cache **不保证硬件一致**（`§4.9` 的 A 口径）：软件在 `START` 前对 PA
源区间 `clean`、在 `DONE && BUSY=0` 后对 PA 目标区间 `invalidate`（`§4.6`）。

本目录两套载体，判据各一份：

| 文件 | 作用 |
| --- | --- |
| `pmem_dma.S` + `pmem_dma.lds` / `pmem_dma_qemu.lds` | **三方承载同一份 case**（`m16-testcases-014`）：DMA 8 B/3 B 搬运、DONE/ERROR+ERR_CODE、一致性 clean/invalidate（A）、屏蔽→pending、捕获（`src_frame=1<<32`、细节回 `cg15 rc4`）、正常异步 `escape cfx_hart`（`cg5 rc8`–`rc11`、`rc11` 整字）、同界 TIMER(15)+DMA(32) 一次进入（位图并集、计数 +1）、W1C 后 pending 落、覆盖语义；H/S/U 三模式（`--defsym TMODE=3/2/0`） |
| `pmem_oracle.py` | 独立判据：期望值现场取自 `spec/DADAO-12` §1/§4.6/§4.9/§5.1/§5.4、`spec/Kaiwu` §1.1/§3、`ADR-0061`、`contract-see` §3/§6.1、`contracts/opcodes.yaml`；`cause_ip` 用 ELF 符号精确断言；`--self-test` 对每条记录做可达 FAIL 证明。真源解析/编码复用 `check_pmem.py` |
| `check_pmem_dma.py` | QEMU/gem5 驱动（`run_arch.py` 的 driver 承载）：flat bin `ENTRY=0x0010_0000`，`-icount shift=0`；过 oracle 后写归一化签名（每槽 1） |
| `check_pmem_rtl.py` | RTL 驱动（chipyard 后端按 `check_<cfx_dir>_rtl.py` 发现）：`+loadmem` 同一 ELF 到 `0xffff_ff01_0100`；过同一 oracle 后写归一化签名 |
| `expected.yaml` | 归一化签名登记（**不是判据**）：001 = 48 槽、002 = 10 槽，全 1 |
| `pmem.S` + `pmem.lds` + `check_pmem.py` | **寄存器面探针**（RTL 直跑，不进索引）：`pmem_exist`（RO）、`pmem_start/size/attr[0..63]`（RW）、`cg15` 寄存器面全量、BUSY 期写忽略、四类 setup 错误 —— QEMU 已在 `m16-qemu-006`、gem5 已在 `m16-gem5-025` 补齐 `cg8/12/13/14`，三承载寄存器面同口径；本探针仍只作为 RTL 侧的逐槽证据 |

## 用例

- **`arch-pmem-001`**（hmon/hypv，48 槽）：DMA 往返/部分拍、状态与错误码、
  一致性（A）、ILLI 非法 `escape`、捕获/正常异步返回、同界多源、ack、覆盖。
- **`arch-pmem-002`**（smon/supv、umon/user，10 槽）：DMA 在 hypv 启动、完成
  事件落在目标模式；各写**自己** monitor 的 `cg15 rc3` 掩码行 → 只置 pending →
  放行 → 同一界投递（`src_frame = 1<<32`、pending 投递后清、`excp_async_num=1`）。

## 测试机约定（非 spec 常量）

- **PA 测试窗**：`0x20_0000` 起（PTW 首张页表的 PTE0 覆盖 PA `[0, 512 MiB)`，
  VA = PA）；DMA 与 CPU 访问同一窗。`pmem_dma.lds` 把首张页表（4 个 512 MiB
  超页）装到 PA 0，探针在 `_start` 写 PTBR/`ptw_enable`（QEMU/gem5 的 step5
  BootROM 已做，幂等）；U 模式把 PTE0 的 HSJU 改成 `0xF` 并失效 TLB。
- **DMA 的 PA 可访问面**：RAM 可读可写、BootROM 只可读（`spec/Kaiwu §3`）；
  其余 PA 属 `PA_FAULT`。

## 运行

```sh
python3 tests/arch/run_arch.py --cfx 32 --platforms qemu,gem5,chipyard --mode hmon
python3 tests/arch/run_arch.py --cfx 32 --platforms qemu,gem5,chipyard --mode smon
python3 tests/arch/run_arch.py --cfx 32 --platforms qemu,gem5,chipyard --mode umon
```

`arch-pmem-001/002` 三方逐槽（QEMU+gem5+RTL）：gem5 的异步面由
`m16-gem5-026` 补齐、`m18-gem5-004` 迁到 R3 出口帧、`m18-gem5-005` 迁到
**0.8.1-rc 源接口**（`cfx_hart cg15` 捕获 / monitor `cg15 rc3` 掩码 /
`cfx_pmem cg16 rc16/17/18`，`cg16 rc18` 只清 pending）；与 QEMU
`m18-qemu-009/010` 同槽位、同 ELF 签名一致。`arch-pmem-001` 的 hmon 首帧
把 `cg15 rc14` 抬到 3（hypv），handler ack 后恢复 2。RTL 仍在
`m18-chipyard-002/003` 迁移。
RTL 寄存器面探针 `pmem.S` 单独直跑（见 `m16-chipyard-022` 的 README 历史）；
其运行时槽位仍是 0.8.0（`IRQ_EN`/`cg9`），归 RTL 迁移任务。
