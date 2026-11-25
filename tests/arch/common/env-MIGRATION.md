# `tests/arch` 运行模式迁移清单（`m16-testcases-015`）

本任务只迁移 **1 条代表用例**（`arch-umon-011`，cfx_umon 寄存器面）为
「body + `common/env-{hmon,smon,umon}`」。下表是仍需逐件迁移的用例与其阻塞点；
迁移前它们只登记 `hmon`（`tests/arch/modes.yaml` 的 `modes`），不允许的模式在
`mode_reasons` 写明原因。

## 已迁移

- `arch-umon-011` — body `tests/arch/umon/umon_mode_regs.body.S`；hmon/smon/umon
  三模式均通过，签名逐槽一致（驱动 `tests/arch/common/check_mode_env.py`）。
- `arch-ptw-001`…`013`、`015`（cfx4）— `m16-testcases-019`：载体 `ptw_carrier_tlb.py`
  用共享 `common/env-{hmon,smon,umon}` 进入/退出（`--mode`），`modes.yaml`
  三条模式全开；body 留在载体自己的 ROM（015 需要只读内存窗口；007/014 已按
  用户 2026-11-25 裁定删除，载体不再有只读页表），
  故障处理程序装在**当前模式监视器**的 `<mode>` 行、在触发模式里运行。

## 待迁移（按载体分组）

### `tests/arch/umon/` — `arch-umon-001`…`010`（10 条 asm）

载体是 `tests/arch/umon/m5_*.S`，当前由 step5 BootROM 在 hypv（cfx_umon）交付，
判据是 exit code / console（`tests/arch/umon/expected.yaml`）。

- 迁移方式：抽 body（去掉与 BootROM 交付相关的假设）→ 用 `common/env-*` 组装；
  semihosting 类（005–009）语义上只依赖自身 cfx 与 RAM，smon/umon 可行；
  `m5_perm_*`（001–004）依赖 `cfx_hmon` 的 fault-record 槽，supv/user 需改判据
  来源（当前模式监视器的 `cg5`）或先解决下面「权限」一条。
- 阻塞点：`asm` 载体仍未接 `--mode`（`run_arch.py` 的 asm 路径显式 fail-closed）；
  需要按 `kind: driver` 或给 asm 载体加环境选择。

### `tests/arch/umon/` 的 asm 载体（001–010）仍待迁移

见上一节：`asm` 载体仍未接 `--mode`（`run_arch.py` 的 asm 路径显式 fail-closed）。

### `tests/arch/cache/` — `cfx5_regs.S`（未登记 `tests/arch.yaml`）

`cfx5` 寄存器面探针（`m16-chipyard-016`），当前只在 chipyard/RTL 上跑。

- 阻塞点（`m16-testcases-017` 之前）：`cfx_cache` 的寄存器访问只能从 `cfx_hmon`
  源通过；旧交付链的 body 属于 `cfx_umon`（cfx0），对 `cfx_cache` 的 `cfxreg`
  被缺省掩码拒绝，且无法先写其掩码（同一权限）。该阻塞点已由 017 改为
  cfx_hmon 源解决（见下）。
- `m16-testcases-017` 已把交付源 cfx 改成 **cfx_hmon(3)**（BootROM 的 hmon 阶段
  直接 `jump` 到 ENTRY），并把「按 `cfx_access` 声明打开目标 cfx 掩码 / `deleg`、
  收窄未声明 cfx、退出还原 + 回读校验」做进三份环境。cfx5 的三模式准入依赖
  `m16-qemu-005`（cfx5 改为通用 `cg0`–`cg7`）：该任务之后 `cfx_access: [cache]`
  在 **hmon/smon/umon** 都能访问（证据脚本已实测三模式签名一致）。
  **ISS-520（open）**：共享 `.work/source/qemu` 仍旧态（qemu 段 8 条 ⑥⑨ 未清）、构建树已是新态，但
  **安装根**仍是 qemu-005 之前的旧态（待 `make install-host`）⇒ 证据脚本取「最新
  构建的那个」并按 md5 基线比对；安装根刷新后必须复跑 `run.sh` 并更新基线。

### 其它 cfx 目录

`hart/`、`pmem/`、`time/`、`power/` 尚无 `tests/arch.yaml` 用例（M16 后续任务
按需增建）；新增时直接按「body + env」形态落，不要复制本任务之前的单文件形态。
