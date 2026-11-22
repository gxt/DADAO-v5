# `tests/arch` 运行模式迁移清单（`m16-testcases-015`）

本任务只迁移 **1 条代表用例**（`arch-umon-011`，cfx_umon 寄存器面）为
「body + `common/env/{hmon,smon,umon}`」。下表是仍需逐件迁移的用例与其阻塞点；
迁移前它们只登记 `hmon`（`tests/arch/modes.yaml` 的 `modes`），不允许的模式在
`mode_reasons` 写明原因。

## 已迁移

- `arch-umon-011` — body `tests/arch/umon/mode_regs.body.S`；hmon/smon/umon
  三模式均通过，签名逐槽一致（驱动 `tests/arch/umon/check_mode_env.py`）。

## 待迁移（按载体分组）

### `tests/arch/umon/` — `arch-umon-001`…`010`（10 条 asm）

载体是 `tests/arch/umon/m5_*.s`，当前由 step5 BootROM 在 hypv（cfx_umon）交付，
判据是 exit code / console（`tests/arch/umon/expected.yaml`）。

- 迁移方式：抽 body（去掉与 BootROM 交付相关的假设）→ 用 `common/env` 组装；
  semihosting 类（005–009）语义上只依赖自身 cfx 与 RAM，smon/umon 可行；
  `m5_perm_*`（001–004）依赖 `cfx_hmon` 的 fault-record 槽，supv/user 需改判据
  来源（当前模式监视器的 `cg5`）或先解决下面「权限」一条。
- 阻塞点：`asm` 载体仍未接 `--mode`（`run_arch.py` 的 asm 路径显式 fail-closed）；
  需要按 `kind: driver` 或给 asm 载体加环境选择。

### `tests/arch/ptw/` — `arch-ptw-001`…`015`（15 条 driver）

载体 `carrier_tlb.py` 自带 4 MiB BootROM，body 固定在 `cfx_hmon`（hypv），
用 `cfx_hmon` 的 `cg5` 现场与自装 `cfx_hmon` 向量。

- 迁移方式：把「BootROM 段 / 向量 / 签名区」抽到 `common/env`，body 只留 TLB
  检查；运行模式由 env 决定。
- 阻塞点：`cfx_ptw`/`cfx_pmem` 的寄存器与 TLB 命令权限按**源模式行**判定；
  supv/user 下需按目标模式重新配置 `cfx_ptw` 的 `cg2`/`cg0` 行（缺省掩码全屏蔽），
  且 `cfx2rd` 在 supv 还受 `cg_reg_deleg` 约束。属于「迁移一件一议」的权限配置，
  不在本任务范围。

### `tests/arch/cache/` — `cfx5_regs.S`（未登记 `tests/arch.yaml`）

`cfx5` 寄存器面探针（`m16-chipyard-016`），当前只在 chipyard/RTL 上跑。

- 阻塞点：`cfx_cache` 的寄存器访问只能从 `cfx_hmon` 源（hypv 行 bit3=0）通过；
  QEMU 测试链交付的 body 属于 `cfx_umon`（cfx0），对 `cfx_cache` 的 `cfxreg`
  被缺省掩码拒绝，且无法先写其掩码（同一权限）。要迁移成「多模式」需先把
  body 作为 `cfx_hmon` 载体（env 另加一种「进入 cfx_hmon」的启动），或由固件
  为 cfx0 开放 `cfx_cache` 的入口。

### 其它 cfx 目录

`hart/`、`pmem/`、`time/`、`power/` 尚无 `tests/arch.yaml` 用例（M16 后续任务
按需增建）；新增时直接按「body + env」形态落，不要复制本任务之前的单文件形态。
