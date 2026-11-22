# `tests/arch/common/env/` — 运行模式环境（hmon / smon / umon）

本目录把「测试 body」与「运行模式环境」分开（`m16-testcases-015`）：body 只写
**测什么**，环境负责**进入哪种运行模式、栈、异常向量、签名区与退出**。

```text
common/env/
  hmon/env.S   进入 hypv（step5 BootROM 已交付在 hypv，环境只设栈后跳 body）
  smon/env.S   进入 supv（cfx_umon 的 hypv 行 switch_run_mode = 2 + trap 自身）
  umon/env.S   进入 user（switch_run_mode = 0；先给 L1[3] 加 U 位并拷贝 body）
  env.lds      镜像布局：.env @ ENTRY、.body @ ENTRY+0x1000、.envtail @ ENTRY+0x2000
```

## 模式与环境

运行模式（2 bit，`spec/Kaiwu` §7.1）与当前模式监视器（`DADAO-12 §5.2`）：

| `--mode` | 运行模式 | 当前模式监视器 | 进入方式（本目录） |
|---|---|---|---|
| `hmon`（缺省） | hypv（3） | `cfx_hmon` | BootROM hmon 已把 `cfx_umon.hypv` 向量指到 ENTRY 并以 hypv 交付；环境只设栈 |
| `smon` | supv（2） | `cfx_smon` | 在 hypv 把 `cfx_umon` 的 hypv 行 `switch_run_mode`/`excp_vector` 写好，`trap cfx_umon, 0` |
| `umon` | user（0） | `cfx_umon` | 同上，`switch_run_mode = 0`；body 在 user 下取指/访存需页表 `U` 位 |

## 与 body 的契约（汇编层）

环境在跳 body **之前**设定，body 只需遵守：

- `rb1` = 栈指针（`ENV_STACK`，在 L1[3] 内；umon 的首次访存由 U 页 TLB 填充）；
- `rb6` = 退出例程地址（`.envtail` 的 `env_finish`；umon 指向拷贝后的 `0x6000_1000`）；
- `ENV_SIG_BUF` / `ENV_SIG_SLOTS`：签名区首地址与槽数，由驱动按 profile 用
  `--defsym` 传入（缺省 `0x6200_0000` / 8，均在 L1[3]）；body 用
  `tests/shared/asm/signature.inc` 的 `SIG_BEGIN` 预填并 `SIGUPD` 逐槽写；
- body 末尾 `jump [rb6, rd0, 0]`：环境负责整段输出签名（`SIG_DUMP_CHARS`，
  semihosting `SYS_WRITEC`）并 `SYS_EXIT(0)`。

`rb0` 是 IP（只读语义），`rb30` 是签名写指针（`signature.inc` 约定），body 不得
另作他用。

## 驱动

`run_arch.py --mode hmon|smon|umon`（缺省 `hmon`）选择环境；用例的
`tests/arch/modes.yaml` 的允许集决定能否在该模式下运行（不允许 ⇒ 显式 `N/A` +
`reasons` 原因；全部被排除 ⇒ 退出 2，fail-closed）。

代表用例 `arch-umon-011`（驱动 `tests/arch/umon/check_mode_env.py`，
body `tests/arch/umon/mode_regs.body.S`）在三种模式下各跑一次：

```sh
python3 tests/arch/run_arch.py --case arch-umon-011 --mode hmon --platforms qemu
python3 tests/arch/run_arch.py --case arch-umon-011 --mode smon --platforms qemu
python3 tests/arch/run_arch.py --case arch-umon-011 --mode umon --platforms qemu
```

判据（驱动现场派生，见 `.tao/contracts/` 与 `spec/`）：

- QEMU `-d cpu` 的 `MODE:` 必须等于请求模式，且至少一个 `MODE:` 落在 body
  执行窗口内（`hmon/smon`：`ENTRY+0x1000`；`umon`：`0x6000_0000`）——
  运行模式由**模拟器现场观测**，不由 body/环境自述；
- 8 槽签名逐槽比对（暂存寄存器回读、`global_cfx_intr_mask` 初值、入口 trap 的
  `excp_prev_run_mode`/`excp_cause_id`、`cfx0` 的 `cg7` 空空间描述）；
- 退出码 `0`；环境的 fail-closed 退出码（`0xE0` user 故障 / `0xE1` supv
  显式 trap 回流）不是 PASS。

## 已知限制（显式登记，不静默降级）

- **smon 无法安装 cfx_smon 的异常向量**：step5 测试链不装载 smon；从 hypv
  （源 cfx_umon）写 `cfx_smon` 的 supv 行被其 hypv 行 `cfxreg`/`cfxtrap` 缺省
  掩码拒绝（`DADAO-12 §3`、`ADR-0045 D4`）。因此 supv 下的 body **不得依赖同步
  异常**；显式 `trap cfx_umon` 由环境装在 `cfx_umon` 的 supv 行（`0xE1`
  fail-closed）。要放开该限制需固件（`tests/ee-vast/`）为 supv 预开权限，
  超出本目录范围。
- **umon 需要改一条页表项**：step5 页表 `HSJU = 0xC`（U=0）。环境把 L1[3] 的
  PTE 改成 `0xF` 并把 body 拷进该 512 MiB 超页；不改 `cfx_ptw`/`cfx_pmem`、
  不做 TLB 失效（全靠「该页在 user 之前未被访问过」首次填充）。因此 **body 与
  tail 必须落在 L1[3] 且 ≤ 0x1000 窗口**（`env.lds` 固定）。
- **hmon 的异常向量属于 BootROM 固件**：hypv 的同步异常由 `cfx_hmon` 处理，
  固件把 cause/cause_ip 写 profile 的 fault-record 槽并 `escape` 回
  `cause_ip + 4`；环境不改该向量（源 cfx_umon 被拒绝）。
- **代表用例只接 QEMU 承载**：`check_mode_env.py` 需要 `-kernel` flat bin +
  `-d cpu` 的 `MODE:` 观测；gem5 shim / chipyard 由驱动显式失败（run_arch 记
  FAIL，不静默跑成别的语义）。

## 未迁移用例

见 `MIGRATION.md`。本目录只交付 1 条代表用例，其余用例仍按原载体运行
（`modes.yaml` 里只登记 `hmon`，并写明原因）。
