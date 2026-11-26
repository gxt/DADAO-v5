# `tests/arch/hart/` — cfx_hart（cfxha 15）arch 用例

`ADR-0061`（掩码归 monitor、源索引统一 cfxha、`cg15` 七槽）把异步投递统一到
`cfx_hart` 的 supv 单向量。`m16-chipyard-021` 落 cg8 管理寄存器与 cg15 异步现场
+ TIMER，`m16-chipyard-024` 改到 `ADR-0061` 模型，`m16-chipyard-026` 改到
**R2**，`m18-testcases-004` 迁到 **R3**（`cg5 rc0–rc5` 入口记录 + `rc8–rc11`
出口意图；`cg15 rc0–rc5` + `rc14/rc15`；`escape cfxHA` 正常异步返回），
`m16-testcases-013` 把同一份 case 接到 QEMU + RTL 两方逐槽。

| 文件 | 作用 |
| --- | --- |
| `cfx15.S` | **唯一** case 源：cg8（hart_id/cycle/insn/timer_cmp/timer_ctrl）读写与 RO/保留编码；cg15 捕获布局（`rc0`–`rc5` 入口记录 HW/RO、写忽略；`rc6`–`rc13` ⇒ `CFXREG`；`rc14` switch RW 复位 2、`rc15` vector RW 低 2 位写忽略）；`cg5 rc0`–`rc5` 入口记录写 ⇒ `CFXREG`、`rc8`–`rc11` 出口意图；屏蔽写在**当前运行模式 monitor** 的 `cg15 rc3`（bit15 = 源 cfxha 15）；TIMER 投 cfx_hart+supv、`src_frame`/`src_pending` 位 = `1 << 15`；屏蔽期只置 pending、解除后投递；源 ack 后 pending 落；**覆盖语义**；**正常异步返回** `escape cfx_hart`（`rc11` 整字写目标 monitor、在第一条返回指令前生效）；`imms18 = 3/4` ⇒ ILLI；**jump 目标精确点**；`rc14` 进入模式；**escape 判据**（升权 / 目标 cfx 未实现 / `cfxha` 不符 ⇒ CFXESC） |
| `cfx15.lds` | RTL 布局：`ENTRY` = `0xffff_ff01_0100`、`.data` = `+0x4000`、签名区 `+0x5000`、`SYS_EXIT` 块 `+0x5800`；`--defsym TMODE=<0\|2\|3>` 在**汇编期**选运行模式 |
| `cfx15_qemu.lds` | QEMU 布局：`ENTRY` = `0x0010_0000`、`.data` = `+0x4000`；同一份 `.S` 由驱动用 `--defsym ENTRY/SIG_BUF/EXITB/HMON_BASE` 覆盖地址 |
| `check_cfx15.py` | 独立判据：期望值现场取自 `spec/DADAO-12` §1/§3/§4.1–§4.7/§5.1/§5.4、`ADR-0061`、`contract-see` §3/§6.1 与 `contracts/opcodes.yaml`；`cause_ip` 用 ELF 符号精确断言；`--self-test` 对每条记录做可达 FAIL 证明 |
| `check_hart.py` | QEMU/gem5 驱动（`run_arch.py` 的 `kind: driver`）：flat bin 从 `ENTRY` 装入，跑 QEMU（`-icount` 使 cycle 搜索确定）/gem5 shim；过 oracle 后写**归一化**签名（每槽 1） |
| `check_hart_rtl.py` | RTL 驱动（`run_arch.py` 的 chipyard 后端按 `check_<cfx_dir>_rtl.py` 发现）：`+loadmem` 同一 ELF，过同一 oracle 后写归一化签名 |
| `expected.yaml` | 归一化签名登记（**不是判据**）：001 = 124 槽、002 = 38 槽，全 1；原始值由 `check_cfx15.py` 现场判 |

## 两条 case（`tests/arch.yaml`，`level: full`）

- **`arch-hart-001`**（hmon/hypv，124 槽）：cg8 寄存器面 + 保留/非法编码 +
  屏蔽→pending→放行 + 捕获/覆盖/RO/`escape` + jump 精确点。只 hmon：槽序含
  `cg3`（hypv-only）与 `cfx_hmon cg15 rc3` 复位值；S/U 的同一捕获流程由 002
  承担。
- **`arch-hart-002`**（smon/supv、umon/user，38 槽）：同一 `cfx15.S` 的
  `TMODE=2/0`；掩码分别取 `cfx_smon` / `cfx_umon` 的 `cg15 rc3`。hmon 由 001
  覆盖。

`cfx15.S` 的槽序（原始）：
- H：同步入口 10 + 寄存器面/屏蔽槽（含 rc14 复位 + 写 0/1/3 读回）+ 异步捕获/覆盖/返回 + jump + rc14 进入
  模式 + escape 判据槽 = 123；
- S/U：2 个屏蔽槽 + 异步捕获/覆盖/返回 + jump = 38。

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
比较归一化签名。gem5 侧：`m16-gem5-026` 补齐 R2 异步面，`m18-gem5-004` 迁到
R3 出口帧，`m18-gem5-005` 再迁到 **0.8.1-rc 源接口**（`cfx_hart cg15`
捕获 / monitor `cg15 rc3` 掩码 / `cg16` mask-pending-ack、pending ack
才清）；与 QEMU `m18-qemu-009/010` 同槽位、同 ELF 签名一致。
**`cg15 rc14` 按 `m18-spec-007/009` 判**（RW、复位 2，既是进入目标也是运行
模式上限）：001 写 rc14=0/1/3 读回同值；hmon 首帧把 rc14 抬到 3（hypv）
才从 hypv 进入、handler 首帧后恢复 2；随后在 supv 下以 rc14=0 验证
**不进入**（pending 与 `cg15 rc5` 保留），抬到 2 后进入并用
`prev_run_mode` 证明。RTL 仍在 `m18-chipyard-002/003` 迁移。

## 运行期证据

运行期证据目录内的 `run.sh`：正向两方三模式、归一化流逐槽（`qemu==rtl`
字节相同）、gem5 预期红、两条注入（“`rc11` 整字恢复” /
“旧槽位进入”）先红后 `cp`+md5 还原回绿、门控 rc。
