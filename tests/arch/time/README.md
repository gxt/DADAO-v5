# `tests/arch/time/` — cfx_time（cfxha 34）arch 用例

`cfx_time` 是 **per-system 全局时间计数器**（`DADAO-12 §4.10`）：只读、自由运行、
**没有中断**。per-hart 的定时器比较与 `TIMER` 中断在 `cfx_hart`（`§4.7`，
`tests/arch/hart/`）——本目录不配置、不等待任何中断。

| 文件 | 作用 |
| --- | --- |
| `time_oracle.py` | **唯一**期望值来源：现场从 `spec/DADAO-12 §1/§4.10`、`contract-see §3/§6.1`、`spec/Kaiwu §7.1` 派生 cfxha/cg/rc/RO/freq/CFXREG/模式编码，给出两条 case 的槽序与静态期望（含原始读数复核函数 `check_time_value`） |
| `time.body.S` | `arch-time-001` 的 body（env 机制，三种模式各跑一次）：`time_freq` 与 RO 再读、隔约 900 条指令两次读 `time_value` 的**单调/严格递增/增量有界/epoch 高位**、与 `cfx_hart cg8 rc2 cycle` 的**同基准** |
| `time_reject.body.S` | `arch-time-002` 的 body（只 hmon）：`cg10 rc2`/`rc63` 保留 rc 读、`rc0`/`rc1` 的 RO 写 ⇒ `CFXREG`；被拒的写不改 `time_freq` |
| `check_time.py` | QEMU/gem5 驱动（`run_arch.py` 的 `kind: driver`）：用 `common/env-{hmon,smon,umon}` 装镜像、跑引擎、按 `-d cpu` 的 `MODE:` 核对运行模式、逐槽比对签名流 |
| `time_rtl.S` + `time_rtl.lds` | RTL 承载（chipyard `WumingVastConfig`）：汇编期 `--defsym TCASE=1|2 --defsym TMODE=3|2|0`；case 定义与 QEMU/gem5 **同一份**（同一槽序） |
| `check_time_rtl.py` | RTL 驱动（`run_arch.py` 的 chipyard 后端按 `check_<cfx_dir>_rtl.py` 命名发现）：逐槽比对 + 从 `+verbose` 的 `cfx2 …` trace 核对运行模式与**原始读数** |
| `expected.yaml` | 签名流登记（**不是判据**）：由两个承载的 `--selfcheck`/`--self-test` 与 `time_oracle.py` 的派生值**双向**核对 |

## 两条 case（`tests/arch.yaml`，`level: full`）

- **`arch-time-001`**（7 槽，`hmon`/`smon`/`umon` 各跑一次；`cfx_access: [time, hart]`）
  1. `time_freq`（cg10 rc0）= 1 GHz（`contract-see §3`：1 count = 1 ns）；
  2. `time_freq` 再读（RO 稳定）；
  3. 单调：隔约 900 条指令后 `t1 >= t0`；
  4. 严格递增：`t1 > t0`（计数器不动即判红）；
  5. 增量有界：两次读数的高 32 位差 ∈ {0,1} ⇒ `delta < 2^33`；
  6. epoch 合理：`t0` 高位置 0（`contract-see §3`：复位后从 0 起算）；
  7. 同基准：`cfx_hart cg8 rc2 cycle` 不早于紧邻的 `time_value` 读数且同一 2^32
     窗口（`contract-see §3`：「与 `cfx_time_value` 同基准、单 hart 下读数相等」
     ⇒ 只能判同基准，**不判两者不等**）。
- **`arch-time-002`**（6 槽，只 `hmon`；`cfx_access: [time]`）：`time_freq`、
  `cg10 rc2`/`rc63` 读、`rc0`/`rc1` 写 ⇒ 四个 `CFXREG`（cause = `1 << 2`）、
  写被拒后 `time_freq` 不变。`cg10` 只有 rc0/rc1 —— 这就是「cfx34 没有
  `timer_cmp`/`timer_ctrl`、没有中断」的机械证据。

## 三方逐槽（同一 case）

`run_arch.py` 一次跑三平台、同一份 `expected.yaml` 逐槽比较（`expected-divergences`
无本条登记 ⇒ 三侧必须与规范值相等）：

```sh
python3 tests/arch/run_arch.py --case arch-time-001 --mode hmon \
    --platforms qemu,gem5,chipyard --bootrom <bootrom_step5.bin> \
    --chipyard-sim <simulator-chipyard.harness-WumingVastConfig> \
    --gem5 <gem5.opt> --gem5-config <configs/dadao/fs.py>
```

## RTL 承载的运行

```sh
llvm-mc --triple=dadao-unknown-elf -filetype=obj -I <repo> \
    --defsym TCASE=1 --defsym TMODE=2 tests/arch/time/time_rtl.S -o t.o
ld.lld -T tests/arch/time/time_rtl.lds t.o -o t.elf
simulator-chipyard.harness-WumingVastConfig +permissive +verbose \
    +loadmem=t.elf +semiout=t.out +max-cycles=5000000 +permissive-off none
python3 tests/arch/time/check_time_rtl.py --only arch-time-001 --mode smon
```

**注意**：`TCASE`/`TMODE` 是 `llvm-mc` 的 `--defsym`（**汇编期**）；传给 `ld.lld`
的 `--defsym` 对本探针无效（`.if` 已在汇编期求值）。

## 与 QEMU/gem5 的已知差异（不写进判据）

- **故障观察通道**：RTL 的 hmon 是共享的 **Tiny 保存-跳转处理程序**（cause_id 槽 =
  hmon 数据页 +0x00、回落点 = +0x18，`HMON_FRAME_*`）；QEMU/gem5 的 step5 固件把
  cause 写进 `FAULT_RECORD` 并从 `cause_ip + 4` 回。判据（cause 值与槽序）两侧相同。
- **gem5 无 cfx5**（`kCfxhaMap` 不含 5）：env 的「未声明 cfx 收窄」会对 cfx5 报
  `CFXREG`，故驱动只在 gem5 上跳过对 cfx5 的收窄（`ENV_PERM_SKIP_NARROW_5`）——
  未实现 cfx 的访问本身已是 `CFXREG`，fail-closed 性质不变。
- **本用例不断言两计数器不等**：单 hart 测试机上 `cfx_time_value` 与
  `cfx_hart cycle` 同基准且读数相等（`contract-see §3`），「per-system vs per-hart」
  的差异要等多 hart（`cfx_time` 全 hart 共享、`cycle` 各自计数）才有观测面。
