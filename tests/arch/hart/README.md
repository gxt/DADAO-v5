# `tests/arch/hart/` — cfx_hart（cfxha 15）arch 用例

`ADR-0061`（掩码归 monitor、源索引统一 cfxha、`cg9` 七槽）把异步投递统一到
`cfx_hart` 的 supv 单向量。`m16-chipyard-021` 落 cg8 管理寄存器与 cg9 异步现场
+ TIMER，`m16-chipyard-024` 改到 `ADR-0061` 模型，`m16-chipyard-026` 改到
**R2**（`cg9` = 进入瞬间的捕获缓冲，每次进入整体覆盖；`escape imms18 = 2`
不返回），`m16-testcases-013` 把同一份 case 接到 QEMU + RTL 两方逐槽。

| 文件 | 作用 |
| --- | --- |
| `cfx15.S` | **唯一** case 源：cg8（hart_id/cycle/insn/timer_cmp/timer_ctrl）读写与 RO/保留编码；cg9 **七槽**（`rc0`–`rc6`，`rc7`–`rc15` ⇒ `CFXREG`）读写、`src_frame`/`src_pending` 写忽略读回不变；屏蔽写在**当前运行模式 monitor** 的 `cg8 rc1`（bit15 = 源 cfxha 15）；TIMER 投 cfx_hart+supv、`src_frame`/`src_pending` 位 = `1 << 15`；屏蔽期只置 pending、解除后投递；源 ack（重装 `timer_cmp`）后 pending 落；**覆盖语义**（不搬走现场再到期 ⇒ 同一指令边界整体覆盖 `cg9`）；`escape cfx_hart, [excp_cause_ip, 8]`（`imms18 = 2`）⇒ 当前 cfx 的 `CFXESC` 且 `cg9` 不变；`imms18 = 3` / `imms18[17:2] != 0` ⇒ ILLI；**jump 目标精确点**（`SimRISC-06` 的 `jump`，有界 cycle 搜索命中目标边界）；`cg9 rc6` RW（复位 2）：写 0/1/3 读回同值，H 尾段以 rc6=0/2 连续投递、用下一次进入的 `prev_run_mode` 证明进入模式 |
| `cfx15.lds` | RTL 布局：`ENTRY` = `0xffff_ff01_0100`、`.data` = `+0x4000`、签名区 `+0x5000`、`SYS_EXIT` 块 `+0x5800`；`--defsym TMODE=<0\|2\|3>` 在**汇编期**选运行模式 |
| `cfx15_qemu.lds` | QEMU 布局：`ENTRY` = `0x0010_0000`、`.data` = `+0x4000`；同一份 `.S` 由驱动用 `--defsym ENTRY/SIG_BUF/EXITB/HMON_BASE` 覆盖地址 |
| `check_cfx15.py` | 独立判据：期望值现场取自 `spec/DADAO-12` §1/§3/§4.1–§4.7/§5.1/§5.4、`ADR-0061`、`contract-see` §3/§6.1 与 `contracts/opcodes.yaml`；`cause_ip` 用 ELF 符号精确断言；`--self-test` 对每条记录做可达 FAIL 证明 |
| `check_hart.py` | QEMU/gem5 驱动（`run_arch.py` 的 `kind: driver`）：flat bin 从 `ENTRY` 装入，跑 QEMU（`-icount` 使 cycle 搜索确定）/gem5 shim；过 oracle 后写**归一化**签名（每槽 1） |
| `check_hart_rtl.py` | RTL 驱动（`run_arch.py` 的 chipyard 后端按 `check_<cfx_dir>_rtl.py` 发现）：`+loadmem` 同一 ELF，过同一 oracle 后写归一化签名 |
| `expected.yaml` | 归一化签名登记（**不是判据**）：001 = 89 槽、002 = 40 槽，全 1；原始值由 `check_cfx15.py` 现场判 |

## 两条 case（`tests/arch.yaml`，`level: full`）

- **`arch-hart-001`**（hmon/hypv，89 槽）：cg8 寄存器面 + 保留/非法编码 +
  屏蔽→pending→放行 + 捕获/覆盖/RO/`escape` + jump 精确点。只 hmon：槽序含
  `cg3`（hypv-only）与 `cfx_hmon cg8 rc1` 复位值；S/U 的同一捕获流程由 002
  承担。
- **`arch-hart-002`**（smon/supv、umon/user，40 槽）：同一 `cfx15.S` 的
  `TMODE=2/0`；掩码分别取 `cfx_smon` / `cfx_umon` 的 `cg8 rc1`。hmon 由 001
  覆盖。

`cfx15.S` 的槽序（原始）：
- H：46 个寄存器面/屏蔽槽（含 rc6 复位 + 写 0/1/3 读回）+ 32 个捕获/覆盖/escape 槽 +
  6 个 jump 槽 + 5 个 rc6 进入模式槽 = 89；
- S/U：2 个屏蔽槽 + 32 + 6 = 40。

## 三方/两方逐槽

QEMU 与 RTL 的**原始** `cause_ip` 地址不同（`0x0010_00xx` vs
`0xffff_ff01_01xx`），不能直接比；两个驱动先过**本平台** oracle，再写
归一化签名（每槽 1 = 通过），`run_arch.py` 对归一化流逐槽比较。

```sh
python3 tests/arch/run_arch.py --case arch-hart-001 --mode hmon \
    --platforms qemu,chipyard --bootrom <bootrom_step5.bin> \
    --chipyard-sim <simulator-chipyard.harness-WumingVastConfig> --qemu <qemu-system-dadao>
python3 tests/arch/run_arch.py --case arch-hart-002 --mode smon ...   # / umon 同理
```

**三方逐槽**：`arch-hart-001/002` 在 QEMU、gem5、RTL 上各过本平台 oracle 后
比较归一化签名（gem5 的 R2 异步面由 `m16-gem5-026` 补齐：`cg9` 七槽、monitor
`cg8 rc1` 掩码、pending/一次捕获/每次进入覆盖）。**`cg9 rc6` 按
`m18-spec-006` 判**（RW、复位 2、异步进入取该值）：001 写 rc6=0/1/3 读回同值，
并在 supv 下以 rc6=0 / 2 连续投递，用下一次进入的 `prev_run_mode` 证明进入
模式（0 ⇒ user、2 ⇒ supv）。QEMU 已由 `m16-qemu-007` 对齐；RTL 对齐由
`m16-chipyard-028`、gem5 由 `m16-gem5-025`，在此之前这两方在本组槽上红
（`DIV-18` 收窄为这两方 + 用例断言已落地）。

## 运行期证据

运行期证据目录内的 `run.sh`：正向两方三模式、归一化流逐槽（`qemu==rtl`
字节相同）、gem5 预期红、两条注入（“帧门控只置 pending” /
“`escape imms18=2` 返回”）先红后 `cp`+md5 还原回绿、门控 rc。
