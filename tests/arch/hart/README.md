# `tests/arch/hart/` — cfx_hart（cfxha 15）arch 探针

`ADR-0061`（掩码归 monitor、源索引统一 cfxha、`cg9` 七槽）把异步投递统一到
`cfx_hart` 的 supv 单向量。本目录承载 `cfx_hart` 的 RTL 用例；`m16-chipyard-021`
落 cg8 管理寄存器与 cg9 异步现场 + TIMER，`m16-chipyard-024` 改到 `ADR-0061`
模型，`m16-chipyard-026` 改到 **R2**（`cg9` = 进入瞬间的捕获缓冲，每次进入
整体覆盖；`escape imms18 = 2` 不返回），`m16-chipyard-022` 补 PMEM_DMA 源。

| 文件 | 作用 |
| --- | --- |
| `cfx15.S` | `WumingVastConfig` 上的 cfx_hart 探针：cg8（hart_id/cycle/insn/timer_cmp/timer_ctrl）读写与 RO/保留编码；cg9 **七槽**（`rc0`–`rc6`，`rc7`–`rc15` ⇒ `CFXREG`）读写、`src_frame`/`src_pending` 写忽略读回不变；屏蔽写在**当前运行模式 monitor** 的 `cg8 rc1`（bit15 = 源 cfxha 15）；TIMER 投 cfx_hart+supv、`src_frame`/`src_pending` 位 = `1 << 15`；屏蔽期只置 pending、解除后投递；源 ack（重装 `timer_cmp`）后 pending 落；**覆盖语义**（不搬走现场再到期 ⇒ 同一指令边界整体覆盖 `cg9`）；`escape cfx_hart, [excp_cause_ip, 8]`（`imms18 = 2`）⇒ 当前 cfx 的 `CFXESC` 且 `cg9` 不变；`imms18 = 3` / `imms18[17:2] != 0` ⇒ ILLI |
| `cfx15.lds` | 固定 `ENTRY` 布局；`--defsym TMODE=<0|2|3>` 在**汇编期**选运行模式（同一份 `.S` 出 H/S/U 三个镜像） |
| `check_cfx15.py` | 独立判据：期望值现场取自 `spec/DADAO-12` §1/§3/§4.1–§4.7/§5.1/§5.4、`ADR-0061`、`contract-see` §3/§6.1 与 `contracts/opcodes.yaml`；`cause_ip` 用 ELF 符号精确断言；`--self-test` 对每条记录做可达 FAIL 证明 |

## 运行

```sh
llvm-mc --triple=dadao-unknown-elf -filetype=obj -I <repo> -defsym TMODE=3 \
    tests/arch/hart/cfx15.S -o <out>/cfx15_h.o
ld.lld -T tests/arch/hart/cfx15.lds <out>/cfx15_h.o -o <out>/cfx15_h.elf
simulator-chipyard.harness-WumingVastConfig +permissive +verbose \
    +loadmem=cfx15_h.elf +semiout=cfx15_h.out +max-cycles=5000000 \
    +permissive-off none
python3 tests/arch/hart/check_cfx15.py --stream cfx15_h.out --elf cfx15_h.elf \
    --nm llvm-nm --mode 3 --root <repo>
```

`TMODE`：`3` = hmon/hypv（额外做寄存器面与非法编码），`2` = smon/supv，
`0` = umon/user；三个镜像跑同一份 checker（按模式给期望槽）。

## 与 `run_arch.py` 的关系

与 `tests/arch/cache/`、`tests/arch/umon/` 的 RTL 探针同型：直跑 RTL，暂未登记
`tests/arch.yaml`（`run_arch.py` 的 chipyard 后端仍 fail-closed）。用例定义只有
一份，等后端接入后由 `check-arch-vast` 按需跑三方。
