# `tests/arch/common/` — 运行模式环境（hmon / smon / umon）

本目录把「测试 body」与「运行模式环境」分开（`m16-testcases-015`）：body 只写
**测什么**，环境负责**进入哪种运行模式、栈、异常向量、签名区与退出**。

```text
common/
  env/cfx_perm.inc  权限准备/收窄的**唯一**宏块（三份 env 共用；驱动给 llvm-mc 传 `-I`）
  env-hmon/env.S    hypv：只做准备后直跳 body（不降模式）
  env-smon/env.S    supv：cfx_hmon 的 hypv 行 switch_run_mode = 2 + trap 自身
  env-umon/env.S    user：先给 L1[3] 加 U 位并拷贝 body，再 switch_run_mode = 0
  env.lds           镜像布局：.env @ ENTRY、.body @ +0x1000、.envtail @ +0x2000、
                    .envperm @ +0x4000（权限准备段，只在 hypv 跑、不拷进 U 页）
```

## 模式与环境

运行模式（2 bit，`spec/Kaiwu` §7.1）与当前模式监视器（`DADAO-12 §5.2`）：

| `--mode` | 运行模式 | 当前模式监视器 | 进入方式（本目录） |
|---|---|---|---|
| `hmon`（缺省） | hypv（3） | `cfx_hmon` | BootROM hmon 阶段 `jump` 到 ENTRY（源 cfx = cfx_hmon）；环境做权限准备后直跳 body |
| `smon` | supv（2） | `cfx_smon` | 把 `cfx_hmon` 的 hypv 行 `switch_run_mode`/`excp_vector` 写好，`trap cfx_hmon, 0` |
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
- `ENV_SIG_BUF + 0x1000` 起 `0x120` 字节是**权限准备的原值保存区**（每 cfx
  40 B + 1 个 8 B 的向量槽），body 不得使用（未声明 `cfx_access` 时不写）。

`rb0` 是 IP（只读语义），`rb30` 是签名写指针（`signature.inc` 约定），body 不得
另作他用。

## 驱动

`run_arch.py --mode hmon|smon|umon`（缺省 `hmon`）选择环境；用例的
`tests/arch/modes.yaml` 的允许集决定能否在该模式下运行（不允许 ⇒ 显式 `N/A` +
`reasons` 原因；全部被排除 ⇒ 退出 2，fail-closed）。

## 执行环境起点：cfx_hmon 源（`m16-testcases-017`）

step5 BootROM 的 hmon 阶段在本任务后**直接 `jump` 到镜像 ENTRY**（不再把 ENTRY
写进 `cfx_umon` 的 hypv 向量再 `trap`）⇒ 镜像的 `inner_cfx_code` = **cfx_hmon
（源 cfx = 3）**，`inner_run_mode` = hypv；cfx_hmon 的 hypv 向量仍是固件入口，
body 的同步异常照旧由 `hmon_fault` 记录并按 policy 恢复。

三种模式各由自己的 env 负责（body 一份）：

| 环境 | 降模式方式 | 收尾 |
|---|---|---|
| `hmon` | 不降（已是 hypv） | 直接输出签名并退出 |
| `smon` | `cfx_hmon` 的 hypv 行 `switch_run_mode = 2` + `excp_vector = env_supv_entry`，`trap cfx_hmon` | tail 里 `trap cfx_hmon`（走 `cfx_hmon` 的 supv 行）回到 hypv 的 `env_hypv_return` → 还原 → 输出 → 退出 |
| `umon` | 同上但 `switch_run_mode = 0`、向量 = U 页入口 | tail 里 `trap cfx_hmon`（走 `cfx_hmon` 的 user 行）回到 hypv 的 `env_hypv_return` → 还原 → 输出 → 退出 |

`trap cfx_hmon` 而不是 `trap cfx_umon`：前者目标 = 自身 cfx，源 cfx 保持 3；
后者会把源 cfx 变成 0。

## cfx 访问权限准备（`cfx_access`）

**掩码语义**（`DADAO-12 §3.1`–`§3.4`）：目标 cfx 的 `<mode>` 行 `rc0`–`rc3` =
`cfxtrap`/`cfxmem`/`cfxreg`/`cfxexe` 来源掩码，位索引 = **源 cfx**，`0 = 允许`；
缺省 `0xFFFF_FFFF_FFFF_FFF7`（只允许源 `cfx_hmon`）。另：supv 访问任何 cfx 的
任一 `cg` 还要目标 cfx 的 `cg3 rc12`（`cg_reg_deleg`）对应位 = 0（缺省全 1 ⇒
supv 全拒）；self 只绕过 cfx 轴，不绕过模式轴。

**做法**（一份宏块 `cfx_perm.inc`，三份 env 只写 `<row>`/`<deleg>` 两个字面量，
放在 `.envperm` 段，只在 hypv 跑）：

1. **声明白名单**：用例在 `tests/arch/modes.yaml` 写 `cfx_access: [...]`；驱动
   （`common/platform.py` → `check_mode_env.py`）逐 cfx 落成
   `--defsym ENV_CFX_ACCESS_<cfxha>=1`；
2. **打开**声明的 cfx：保存原值 → 把源 cfx 位清 0（可验证的幂等写）→
   `cg_reg_deleg = 0x8`（supv 侧前提；user/hmon 不产码）→ 回读校验；
3. **收窄**未声明的 arch cfx：保存原值 → 把源 cfx 位置 1（fail-closed）→ 回读
   校验 ⇒ **未声明访问 `CFXPERM`**。`cfx_hmon`(3) 是源 cfx 本身（self 绕过，
   收窄无意义）⇒ 跳过；`cfx_umon`(0) 的 `rc0`（`cfxtrap`）保持打开——环境自用
   （supv 下显式 `trap cfx_umon` 的 fail-closed 回落要能进它的 supv 行）。
   `cfxreg`（rc2）必须**最后**写且不读回：它一封就再读不到该 cfx 的寄存器
   （self-lockout），故只写不校验（其余三类照常回读校验）；
4. **还原**：只还原第 2 步打开的项（退出前回读校验）；收窄项不还原——镜像随后
   `SYS_EXIT`，掩码不跨镜像持久；
5. **失败语义（fail-closed `0xE2`，不是 PASS）**：回读不符（写被拒、被固件静默
   resume、寄存器不存在）⇒ 签名区前 4 槽记 `(cfxha, row/rc/phase, 预期, 实测)`
   并以 `0xE2` 退出。

**为什么只留一份宏块**：`llvm-mc` 不搜索源文件所在目录，env 之间的共享 include
必须靠 `-I`；驱动现在给 `llvm-mc` 传 `-I tests/arch/common/env`，三份 env 因此
只写三行入口（`include` + `ENV_PERM_PREP <row>, <deleg>` +
`ENV_PERM_RESTORE_PREP <row>, <deleg>`）。`run_arch --self-test` 机械校验
「三份 env 都 include、无人再内联」。

## 按需开关（缺省不变；`m16-testcases-019`）

有的载体不能把 body 放在 `ENTRY + 0x1000` 的 RAM 镜像里（cfx4 的 `tests/arch/ptw/`
需要运行期只读的页表/内存窗口，故 body 留在载体自己的 4 MiB ROM；镜像 = 载体
固件段 + env 三段 + body）。这类载体给环境传以下 `--defsym`（缺省行为与原来
完全一致）：

| defsym | 缺省 | 作用 |
|---|---|---|
| `ENV_PERM_ALLOW` | `0xFFFF_FFFF_FFFF_FFF7` | 「打开」时清哪些源 cfx 位。缺省只清 `cfx_hmon(3)`；cfx4 的同步故障处理程序在**当前模式监视器**（cfx_smon/cfx_umon）名下运行，它对声明的 cfx 的访问源是 2/0，故传 `…F3`/`…F6`（再清那位） |
| `ENV_TLB_INVALIDATE` | 未定义 | 定义后，umon 在改完 L1[3] 的 U 位时整侧 `invalid|all`：hypv 阶段若已按旧 HSJU（0xC）填过该页，user 命中会按条目判 `[32] NUPERM` |
| `ENV_UENTRY` | `ENV_UCOPY` | 进 user 的跳转目标（body 不在 U 页拷贝区时传 body 的真实地址） |
| `ENV_UTAIL` | `0x6000_1000` | 收尾段地址（body 在 ROM 时传 ROM 里的 `.envtail`） |
| `ENV_UPAGE_PTE_PA` | `0x18` | 写 L1[3] 的 U 位的那张表的物理地址（L1 不在 PA 0 时传，如 cfx4 的 `0x7ff0_0018`） |
| `ENV_COPY_OCTAS` | 512 | umon 的 body 拷贝长度；`0` = 不拷贝（body 已在 user 可达处） |

## 已知语义边界（实测登记，不静默降级）

- **`cfx_cache`（cfx5）的三模式准入依赖 `m16-qemu-005`**：该任务前 cfx5 只实现
  `cg8` 寄存器面（`cg0`–`cg7` 一律 `CFXREG`）⇒ 掩码/`deleg` 写不进、supv 恒拒。
  qemu-005 之后 cfx5 走通用 `cg0`–`cg7`，`cfx_access: [cache]` 即可在
  **hmon/smon/umon** 三模式访问（证据脚本已实测三模式签名一致）。
  **ISS-520（open，两句话分开）**：① 共享 **`.work/source/qemu` 旧态**仍旧态
  （`helper.c` 缺 002/003、qemu 段 8 条 ⑥⑨ 未清）、共享构建树 `.work/build/qemu/` 已重建；
  ② **安装根** `.dadao/cross-toolchain/bin/qemu-system-dadao` 仍是 qemu-005 之前的
  旧态，待 `make install-host`。⇒ 证据脚本取「最新构建的那个」并按
  `md5=dd831552353a3dcbb70719c3a80297fd` 基线比对（不符只 WARN 并要求复核）；
  **安装根刷新后必须复跑 `run.sh` 并更新基线**。
- **未声明 cfx ⇒ `CFXPERM`** 由第 3 步的**收窄**保证（源 cfx3 在缺省允许集内，
  不收窄就会放行）。
- **smon 不支持同步异常**：step5 链不装载 `cfx_smon`，supv 下的同步异常无处可
  去（015 已登记）；env 只提供「显式 `trap cfx_umon`」的 fail-closed 回落。
- **umon 的 U 页**：仍靠把 L1[3] 的 PTE 改成 `0xF` 并把 body/tail 拷进该超页。

代表用例 `arch-umon-011`（驱动 `tests/arch/common/check_mode_env.py`，
body `tests/arch/umon/umon_mode_regs.body.S`）在三种模式下各跑一次：

```sh
python3 tests/arch/run_arch.py --case arch-umon-011 --mode hmon --platforms qemu
python3 tests/arch/run_arch.py --case arch-umon-011 --mode smon --platforms qemu
python3 tests/arch/run_arch.py --case arch-umon-011 --mode umon --platforms qemu
```

判据（驱动现场派生，见 `.tao/contracts/` 与 `spec/`）：

- QEMU `-d cpu` 的 `MODE:` 必须等于请求模式，且至少一个 `MODE:` 落在 body
  执行窗口内（`hmon/smon`：`ENTRY+0x1000`；`umon`：`0x6000_0000`）——
  运行模式由**模拟器现场观测**，不由 body/环境自述；
- 8 槽签名逐槽比对（暂存寄存器回读、`global_cfx_intr_mask` 初值、`cfx0` 的
  `cg7` 空空间描述；另外两槽（`excp_prev_run_mode`/`excp_cause_id`）原本读的
  是**入口 trap** 的现场，交付改为「hmon 直接跳转」后恒为 0/0
  —— `m16-testcases-017` 待裁定项，见该任务书）；
- 退出码 `0`；环境的 fail-closed 退出码（`0xE0` user 故障 / `0xE1` supv
  显式 trap 回流）不是 PASS。

## 已知限制（显式登记，不静默降级）

- **smon 无法安装 cfx_smon 的异常向量**：step5 测试链不装载 smon；`cfx_smon`
  的 hypv 行 `cfxreg`/`cfxtrap` 缺省掩码不拒绝源 cfx_hmon（bit3=0），但
  `cg_reg_deleg` 缺省全 1 ⇒ supv 侧无从接手。因此 supv 下的 body **不得依赖
  同步异常**；显式 `trap cfx_umon` 由环境装在 `cfx_umon` 的 supv 行（`0xE1`
  fail-closed）。要放开该限制需固件（`tests/ee-vast/`）装载 cfx_smon 或预开
  deleg，超出本目录范围。
- **umon 需要改一条页表项**：step5 页表 `HSJU = 0xC`（U=0）。环境把 L1[3] 的
  PTE 改成 `0xF` 并把 body 拷进该 512 MiB 超页；不改 `cfx_ptw`/`cfx_pmem`、
  不做 TLB 失效（全靠「该页在 user 之前未被访问过」首次填充）。因此 **body 与
  tail 必须落在 L1[3] 且 ≤ 0x1000 窗口**（`env.lds` 固定）。
- **hmon 的异常向量属于 BootROM 固件**：hypv 的同步异常由 `cfx_hmon` 处理，
  固件把 cause/cause_ip 写 profile 的 fault-record 槽并 `escape` 回
  `cause_ip + 4`；hmon 环境不改该向量。**smon/umon 环境会临时改它**（降模式要
  用 `cfx_hmon` 的 hypv 行向量），smon 在 `env_hypv_return` 里按保存值还原；
  umon 不还原（镜像结束即失效）。
- **代表用例只接 QEMU 承载**：`check_mode_env.py` 需要 `-kernel` flat bin +
  `-d cpu` 的 `MODE:` 观测；gem5 shim / chipyard 由驱动显式失败（run_arch 记
  FAIL，不静默跑成别的语义）。
- **cfx4 的 body 在 ROM**（`m16-testcases-019`）：env 只负责进入/退出与权限
  准备，body 由载体的固件段交付；因此 smon/umon 的「body 必须落在 L1[3] 且
  ≤ 0x1000 窗口」与「umon 要拷贝」两条限制对它不适用（ROM 取指走 cfx 空间，
  `cfx_power` 的 `<mode>_cfxexe` 要声明）。

## 未迁移用例

见 `env-MIGRATION.md`。本目录只交付 1 条代表用例，其余用例仍按原载体运行
（`modes.yaml` 里只登记 `hmon`，并写明原因）。
