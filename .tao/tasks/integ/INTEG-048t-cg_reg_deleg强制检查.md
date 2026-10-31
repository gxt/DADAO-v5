# INTEG-048t: `cfx_*_cg_reg_deleg` 强制检查（QEMU 消费点缺失 + 046t 前置修正）

**模块**：integ
**项目里程碑**：M10
**依赖**：INTEG-044t（两轴权限模型/`CFXPERM` 落地）、INTEG-046t（Step5 启动链；本任务对其 hmon/smon 与探针做**前置修正**）、INTEG-047t（SBI DMA 契约；其探针 provider 以 hypv 运行 ⇒ 本检查零影响）
**状态**：待开始

## 执行环境
**执行环境**：本地（git worktree `/tmp/opencode/INTEG-048t/repo`，分支 `INTEG-048t`）

## 背景（问题根源）

1. **规范条文**：`DADAO-13 §1` cg3 `rc12` = `cfx_⟨cfxname⟩_hypv_cg_reg_deleg`，复位**全 1**、RW，「cg 访问授权，`bit=0` 时允许 `supv` 访问，`bit3` 固定为 1」；`DADAO-23 §3` 要求各 cfx 的 `HBI_<name>_INIT` **清除自身**该寄存器。别名：`.tao/contracts/contract-cfx-aliases.md`（cfxha 3 / cg 3 / rc 12）。
   ⇒ **cg3 是合法寄存器组**（hypv 可正常读写），`bit3` 恒 1 只是**权限约束**（supv 恒被拒），**不是寄存器非法**，故 deleg 拒绝对 cg3 **不作例外**。
2. **实现缺口（实测）**：QEMU 只有存储点、无消费点——`cpu.c` 复位写 `mode[3].cg_reg_deleg = ~0ULL`（非 hypv 行写 0）；`helper.c` 仅 `cfx_reg_ptr()` 的 `rc==12` 分支返回指针（读写均通），`helper_cfx2rd/cfx2rc` 中**没有** delegation 判定；写侧不做 bit3 强制。046t 遗留亦记「仅存储不检查」。
3. **现状实测（预检原型 `/tmp/opencode/INTEG-048t/proto.py`，QEMU md5 `72d6c653…`，主仓库构建）**：
   - supv 读 `cfx_ptw cg2 rc0`（`deleg=~0`，bit2=1，按规范应拒绝）⇒ **照样成功**，`rd5=0xFFFF_FFFF_FFFF_FFF7`、`rc=0`；
   - 同路径把 deleg 的 bit2 清 0 ⇒ 成功（正例基线，说明「0 = 允许」方向正确）；
   - user 模式（`deleg` bit0=1）读 `cfx_ptw cg0 rc0` ⇒ 成功（现有模型不区分模式，须保持）；
   - supv 读 `cfx_pmem cg3 rc12` ⇒ **CFXREG**（`cid=1<<2`、`cinfo=0x7A443305` = 该指令编码(cfxha=17)、目标 = 被访问的 cfx）——**这是改动前的现状**；按本任务口径 cg3 不作例外，改后应为 `CFXPERM`（`cid=1<<7`），见 §测试 `cg3_supv_perm_rd`；
   - hypv 把 `cg3 rc12` 写 0 后读回 0 ⇒「bit3 固定为 1」当前**未**实现。
4. **语义歧义已裁定**：此前本任务书把「异常类型 / bit3 / 位范围 / self 豁免」立为 R1–R4 BLOCKED；用户已逐项纠正并统一（§已裁定语义，原话见 §用户授权原话）⇒ BLOCKED 解除，按裁定实现，**不再采用「只覆盖 cg0–cg3」的旧结论**。
5. **cg3 例外已撤销（2026-10-31 用户补充裁定）**：cg3 是**合法**寄存器组，只是 `bit3` 固定在 mask 中恒 1 ⇒ supv 访问被权限拒绝，因此 **cg3 的 deleg 拒绝同样走 `CFXPERM`**，不再「先按现有 `CFXREG`」；hypv 访问 cg3 仍允许。
6. **开放策略已简化（2026-10-31 用户第三次裁定）**：hmon 对需要开放的 cfx **一次性写 `0x0000_0000_0000_0008`**——唯一置位是恒 1 的 bit3，其余 cg0–cg63 全为 0 ⇒ 一次性开放全部 cg；**不逐 cg 判定、不逐位清位**。此前「按 smon 实际用到的 cg（cg5/8/9/15）逐位清 mask」的方案及其数值全部作废，任务书与代码中**不得**再出现该类逐位 mask（判据见 §验收 7c）。
7. **`cfx_power` 只读开放（2026-10-31 用户第四次裁定）**：smon（cfx2/supv）需按**固定地址**读 `cfx_power`（cfxha 63）的 BootROM；消费点已存在（044t 的直接 `ld/st` cfxmem 两轴检查），**QEMU 侧零改动**，只需 hmon 在 hypv 写 `cfx_power cg2 rc1`（supv cfxmem）令 **bit2=0**。此开放**只针对 cfxmem 数据轴**，不是 `hypv_cg_reg_deleg`：power 的 deleg 保持复位 `~0`，cfxreg/cfxexe/cg7 均不开放；`cfx_power` 的 `cfxexe` 保持默认（BootROM 的 X 只服务 power 自身启动）。此前「`cfx_hmon`/`cfx_power` 不开放」的表述**限定为 deleg 不开放**，不再表示「power 完全不开放」。

## 已裁定语义（取代原 R1–R4 BLOCKED，追加 R5/R6；原话见 §用户授权原话）

- **R1 = 拒绝走 `CFXPERM`**（`1<<7`，进入当前运行模式 monitor，`cause_info` = 指令编码）；**无 cg3 例外**——cg3 合法，但其 mask 的 `bit3` 恒 1，故 supv 访问任何 cfx 的 cg3 由**同一条** deleg 规则拒绝为 `CFXPERM`（**不**先走 `cfx_reg_ptr` 的 `CFXREG` 分支）。
- **R2 = `bit3` 硬件强制 1**：软件写 0 无效（写路径 `value | (1ULL<<3)`），读回恒 1。
- **R3 = 位图覆盖全 64 个 cg**：bit 索引 = cg 编号（0–63）；复位全 1 = 默认全拒。
- **R4 = 不做 self 豁免**：supv 访问**任何** cfx（含自身）都查**目标 cfx** 的 mask；hypv 自身访问不受该 mask 约束。
- **R5 = 开放策略：整组一次性开放（deleg 轴）**：需要让 supv 使用的 cfx，由 hmon 在 hypv 写 `cg3 rc12 = 0x8`（= 除 bit3 外无置位 ⇒ 全 cg 允许），一次搞定、不按 cg 逐项开。`cfx_hmon`/`cfx_power` 的 **`hypv_cg_reg_deleg` 不开放**（保持复位 `~0`，supv 经 `cfx2rd`/`cfx2rc` 访问任意 cg ⇒ `CFXPERM`），**不写** `cfx_power cg3 rc12`；其余 cfx 亦保持默认 `~0`，需要时按同一约定写 `0x8`。
- **R6 = `cfx_power` 的 cfxmem 只读开放（非 deleg）**：hmon 在 hypv 写 `cfx_power cg2 rc1 = 0xFFFF_FFFF_FFFF_FFF3`——相对复位 `0xFFFF_FFFF_FFFF_FFF7` **只把 bit2（源 smon）由 1 改 0**，其余位不变；用途仅是让 smon 用 `ld` 读固定地址的 power BootROM。**不写** `cfx_power cg3 rc12`、**不写** `cg2 rc2`（cfxreg）/`cg2 rc3`（cfxexe），**不开放** cg7/控制寄存器；`cfx_hmon` 无任何开放项。
  - 事实边界：`cfxmem` 门**不区分读写方向**（0 = 允许直接 `ld/st`）；「smon 只读」由**固件约定**保证，硬件上同段 RAM/MMIO 仍是可写面；BootROM 段本身 RO ⇒ `st` 得 `ILLI`，power 寄存器轴仍 `CFXPERM`。验收按此口径（§验收 4b）。

推论（实现口径，不再另议）：每个 cfx 一个 64 位寄存器，管理该 cfx 的 64 个 cg 是否允许 supv 访问（0=允许、1=拒绝）；检查只作用于 **supv** 路径，user/jail 沿用现有两轴模型（deleg 不参与，cg3 在 user/jail 仍由 `cfx_reg_ptr` 报 `CFXREG`），hypv 不受限（cg3 在 hypv 可正常读写）。cg3 在 supv 的拒绝由 `bit3` 恒 1 自然给出，**不写特例代码**。`0x8` 是「除 cg3 外全开」的唯一写法：cg7（内部存储控制 `sram_block_sel`/`sram_addr`）等接口由「全 cg 开放」自然可读，**不单列 bit7**。`cfx_power` 是**唯一例外**：**不写 deleg**，只把 `cg2 rc1` 的 bit2 清 0（R6），**不属于**「整组开放」。

## 目标（范围）

1. **QEMU 消费点**：`helper_cfx2rd`/`helper_cfx2rc` 的 supv 路径按**目标 cfx** 的 `hypv_cg_reg_deleg` 位判定；`1 ⇒ CFXPERM`；**cg3 一并适用**（其 bit3 恒 1 ⇒ supv 访问任何 cfx 的 cg3 恒 `CFXPERM`，不再走 `cfx_reg_ptr` 的 CFXREG 分支）；hypv 访问 cg3 仍允许；user/jail 不受影响（deleg 不参与，cg3 仍 `CFXREG`）。
2. **写侧 bit3 强制**：写 `cg3 rc12` 时置 bit3=1，读回恒 1；复位值 `~0ULL` 与 `cpu.h` 布局不改。
3. **046t 前置修正（本任务范围内，不另立任务）**：hmon 对 `cfx_ptw`/`cfx_pmem`/`cfx_smon` 各写一次 `cg3 rc12 = 0x8`（整组开放，不逐 cg 清位），并同步 smon 自检、046t 探针 `deleg_dump`（三值均 `0x8`）与 step5 README；另写一行 `cfx_power cg2 rc1 = 0xFFFF_FFFF_FFFF_FFF3`（仅 bit2=0，见下条）。**不得**把「只改探针期望」当作完整修复（hmon 未真正写 `0x8` 则 046t 启动链会被本检查整段拒绝）。
4. **测试与证据**：新增 048 探针——正例（ptw cg8/cg9、pmem cg15、smon cg5 self、cg7）、bit3 恒 1、**未开放 cfx 的 supv 读取 ⇒ `CFXPERM`（隔离 cfxreg 轴）**、hypv 不受限、user 不受影响；证据脚本注入回绿。**不加 Linux 侧测试**（用户裁定：Linux 开发过程不需要验证，只由架构/探针验证）。
5. **power BootROM 只读路径（046t 内闭环）**：hmon 写 `cfx_power cg2 rc1 = 0xFFFF_FFFF_FFFF_FFF3`（相对复位只清 bit2）；smon 以固定地址 `0xFFFF_FFFC_0000` `ld` 读 BootROM 头并自检；探针断言该读成功、写 BootROM ⇒ `ILLI`、power 的 deleg/cfxreg/cg7 仍 `CFXPERM`。**QEMU 侧不改**（cfxmem 消费点已有）；power 的 cfxexe/控制寄存器/deleg 均不动。

## 接口规范（QEMU 侧最小改法，现行代码事实已核对）

1. **不改 `cfx_reg_ptr()` 签名**：其职责保持「寄存器组合 / 读写权限不匹配 ⇒ `NULL` ⇒ 调用方报 `CFXREG`」，不掺 delegation。
2. 新增静态门（`helper.c.patch`，紧邻 `cfx_perm_denied()`）：
   ```c
   /* supv 访问目标 cfx 的 cg 需其 hypv_cg_reg_deleg 对应位 = 0 (DADAO-13 §1)。
    * cg3 不作例外：其 bit3 恒 1 => supv 恒拒（CFXPERM）；hypv/user/jail 不受本检查约束。
    * 软件侧「整组开放」的写法是 0x8（除恒 1 的 bit3 外无置位），硬件仍按位判定。 */
   static bool cfx_deleg_denied(CPUDADAOState *env, int ci, int cg)
   {
       uint64_t mask;

       if (env->inner_run_mode != DADAO_MODE_SUPV || cg > 63) {
           return false;
       }
       mask = env->cfx[ci].mode[DADAO_MODE_HYPV].cg_reg_deleg;
       return (mask & (1ULL << cg)) != 0;
   }
   ```
   数据源固定 `mode[DADAO_MODE_HYPV].cg_reg_deleg`（该字段只存于 hypv 行，`cfx_reg_ptr` 的 `rc==12` 亦取此行）。
3. **调用点（2 处）**：`helper_cfx2rd`/`helper_cfx2rc` 各一处，位置 = `cfx_perm_denied(..., DADAO_CFX_PERM_REG)` 之后、`cg==15 && cfx_pmem` 特例与 `cfx_reg_ptr()` **之前**：
   ```c
   if (cfx_deleg_denied(env, ci, cg)) { cfx_raise_perm(env, info, pc); return; }
   ```
   顺序：reserved ⇒ `ILLI`；`cfx_idx<0` ⇒ `CFXREG`；cfxreg 轴 ⇒ `CFXPERM`；deleg ⇒ `CFXPERM`（**含 cg3**，无「cg3 ⇒ CFXREG」一项）。放在 pmem cg15 特例之前，保证 DMA 分支同受约束。
4. **cg3**：cg3 是**合法**寄存器组 ⇒ 不新增任何放行/特判路径；supv 由 deleg 门（bit3 恒 1）直接拒绝为 `CFXPERM`，**不再**落到 `cfx_reg_ptr()` 的 `cg==3 ⇒ NULL ⇒ CFXREG`。`cfx_reg_ptr()` 的 `cg==3 && inner_run_mode != HYPV ⇒ NULL ⇒ CFXREG` **原样保留**（该规则此后只对 **user/jail** 生效；`045t::cfx2_cg3_nonhypv` 是 user 访问，期望不变）。
5. **写侧 bit3**：`helper_cfx2rc` 在 `p = cfx_reg_ptr(...)` 成功后、通用 `else` 之前加分支 `else if (cg == 3 && rc == 12) { *p = value | (1ULL << 3); }`；**不得**放在门附近（门在 supv 已直接拒绝；该分支只服务 hypv 写路径，须经 `cfx_reg_ptr` 正常取得指针）。
6. 复位值 `mode[3].cg_reg_deleg = ~0ULL` 保留（= 默认全 cg 拒绝，未开放）；非 hypv 行的 0 不动（本检查只读 hypv 行）。
7. **组件工作流**（`docs/Process-01`）：改 `.work/source/qemu` 前/后各跑 `make check-source-state`；改完 `git reset --soft <base>` + 提交收敛为 base+1；`python3 tools/infra/make_patch.py qemu` 导出（**禁手改补丁**）；`make check-patch-tree`；`make build-qemu`；**必须** `make install-host`（安装根 `qemu-system-dadao` 才是门控/探针读的二进制）。
   本 worktree **无 `.work/` 与 `.dadao/`** ⇒ `make build-qemu` 属**首次全量构建**（预计 10–30 min）：先申报耗时、按 AGENTS.md 后台跑并落 `XXX_EXIT` 标记，**不得会话内空等**；增量重建（后续再改）预计 1–3 min。
8. **power BootROM 只读路径不改 QEMU**：直接 `ld/st` 的 cfxmem 检查在 `dadao_cpu_tlb_fill`（`helper.c.patch` 的 `cfx_perm_denied`；cfxha≠0 时取目标 cfx `mode[inner_run_mode]`、位 = 源 cfx）已生效。源 smon(2)/supv 读 cfx63 ROM ⇒ 只查 `cfx[63].mode[2].cfxmem` 的 bit2；本任务对该路径**不新增/不修改 helper**，只在 `hmon.S` 写 mask、在探针断言（验证手段 = `046t` 真链 + 048 探针）。

## 046t 前置修正（同笔落地；不改 046t 任务书历史记录）

**依据（smon 的 supv 访问：既有部分已核对 `tests/shared/bootrom/step5/smon.S`；power 一行为本任务新增）**：
- `cfx_ptw` **cg8**（`rc8` ptw_enable 写/读）、**cg9**（`rc0` ptbr 写/读）；
- `cfx_pmem` **cg15**（`rc0`–`rc3` 写、`rc4` 读）；
- `cfx_smon` **cg5**（`rc2` cause_id、`rc4` cause_info）——**自身访问，不豁免**；
- `cfx_power`（cfxha 63）**BootROM 固定地址 `0xFFFF_FFFC_0000`**：smon 新增一条 `ld.o`（源 cfx2/supv）⇒ 查 `cfx_power` supv `cfxmem`（`cg2 rc1`）的 **bit2**；复位 `0xFFF7` 为 1 ⇒ 现状 `CFXPERM`（基线 FAIL）。

其他 cfx 的 supv cfx2 访问：**无**（`cfx_ptw`/`cfx_pmem` 的 cg5 仅 047t 探针内 provider 使用，且其向量写 `cfx_pmem` **hypv** 行 `cg3 rc8 = 3` ⇒ deleg 零影响）。

**cg3 核对（已核）**：`smon.S` 的 supv 访问**不含 cg3**；`hmon.S` 的 `cg3` 读写（`cfx_smon cg3 rc8/rc10`、`cfx_ptw/cfx_pmem/cfx_smon cg3 rc12`、`cfx_pmem cg3 rc0/rc1/rc2/rc3` 撤销段）全部在 **hypv** ⇒ hypv 不受 mask 约束，**允许**；`cg3 rc12` 写入后 `bit3` 恒 1（R2）。故 046t 的启动链**不因 cg3 统一 `CFXPERM` 而需要任何额外处理**。

**hmon（cfx3/hypv）的 deleg 开放——每个 cfx 写一次 `0x8`（`cg3 rc12`）**：

- `cfx_ptw`(4) `cg3 rc12 = 0x0000_0000_0000_0008`
- `cfx_pmem`(17) `cg3 rc12 = 0x0000_0000_0000_0008`
- `cfx_smon`(2) `cg3 rc12 = 0x0000_0000_0000_0008`（原无 `rc12` 写，**新增一行**）

三值语义相同：唯一置位是恒 1 的 bit3 ⇒ cg0–cg2、cg4–cg63 全允许，覆盖 smon 的 cg5/cg8/cg9/cg15 且**不需要**枚举具体 cg。`cfx_hmon`(3)、`cfx_power`(63) **不写 deleg**（保持复位 `~0`）。

**power BootROM 只读（cfxmem 轴；与 deleg 无关）**：

- hmon 在写 ptw/pmem 的 `cg2 rc0–rc3` 之后、**同一 `rd6 = 0xFFFF_FFFF_FFFF_FFF3` 尚在时**增加一行：`cfx2rc cfx_power, cg2, rc1, rd6`。相对复位 `0xFFF7` **只把 bit2（源 smon）1→0**；`bit3` 复位已是 0，hmon 自身访问不受影响。
- **只此一行**：不写 `cfx_power cg3 rc12`（deleg 保持 `~0`）、不写 `cg2 rc2/rc3`（cfxreg/cfxexe 保持默认）、不写 cg7/控制寄存器；**禁止**照搬 044t/045t bootstrap 的 `for cg in (0,1,2,3): cfx2rc(63, cg, 1/3, 0)` 整组清 0（那是探针取指布置，不是固件策略）。
- smon 在 magic 自检之后、SRAM 清空前：先 `LD64 rd20, 0,0,0,0`（保证被拒时确定性失败），再 `ld.o rd20, [0xFFFF_FFFC_0000]`；期望 `0x44424F54_0001_0002`（`build_step5_bootrom.py` 的 `>IHHII` 头 = magic `0x44424F54` + version 1 + count 2，大端 64 位读）。
- smon 从 cfx2 SRAM 取指（self，不查 cfxexe），**不执行** power BootROM；`cfx_power` 的 cfxexe 仍为默认（X=1 属 power 自身启动代码），与本只读不冲突。

**保持不动的既有内容**（与 deleg 无关）：hmon 里 `cfx_ptw`/`cfx_pmem` 的 `cg2 rc0–rc3`（cfxreg 轴）、`cfx_hmon cg2 rc0`、以及末尾撤销自身 `cfx_pmem cg3 rc0/rc1/rc3/rc2` 的 `0xFFFF…FFFF`。

**回读与自检同步**：
- hmon 写完三份 deleg 后**分别回读**（`cfx2rd <cfx> cg3 rc12`），按现有 RAM 视图存 `0xFC00_0001_0018`（ptw）/`…_0020`（pmem）/`…_0028`（smon）；再读 `cfx_power cg2 rc1` 存 `…_0030`、`cfx_power cg3 rc12` 存 `…_0038`。
- **`rd6` 会被三次 deleg 写与回读覆盖**：写 `cfx_hmon cg2 rc0` 前须**重新装入** `0xFFFF_FFFF_FFFF_FFF3`（否则会把 cfx_hmon 的 supv `cfxtrap` 写成 `0x8`，放开全部来源）。
- smon 把 `0x…0018/20/28` 装入 `rd17/rd18/rd19`、`0x…0030/38` 装入 `rd21/rd22`（`rd20` = 直接 ROM 读；`rd16` 起为自由观测区，实现时核对无占用）；自检（现 `smon.S:207` 单条比较）扩为：`rd17=rd18=rd19=0x8`、`rd21=0xFFFF_FFFF_FFFF_FFF3`、`rd22=0xFFFF_FFFF_FFFF_FFFF`、`rd20=0x44424F54_0001_0002`，失配仍走 `0xB9`。
- `tools/testcases/arch/min_rom_probe_integ046t.py`：`deleg_dump` **仍只**断言 `rd17 = rd18 = rd19 = 0x8`（**不把 power 混入**），用例描述同步为「`cg_reg_deleg = 0x8`（除固定 bit3 外全 cg 开放）」；**新增** case `power_bootrom_read` 断言 `rc=0`、`rd20=0x44424F54_0001_0002`、`rd21=0xFFFF_FFFF_FFFF_FFF3`、`rd22=0xFFFF_FFFF_FFFF_FFFF`（后者同时证明 power 的 deleg 未被 hmon 打开、cfxmem 未被过度放开）。
- `tests/shared/bootrom/step5/README.md`：hmon 阶段描述改为「opens `cfx_ptw`/`cfx_pmem`/`cfx_smon` for source smon by writing `cg3 rc12 = 0x8`（除恒 1 的 bit3 外全 cg 允许）；`cfx_hmon`/`cfx_power` 的 `hypv_cg_reg_deleg` 保持复位 `~0`；`cfx_power cg2 rc1` 仅 bit2=0，供 smon 读 BootROM」；观测寄存器表补 `rd17/rd18/rd19`（三个 deleg 回读，均为 `0x8`）、`rd20`（BootROM 头）、`rd21`（power supv cfxmem）、`rd22`（power deleg，全 1）。

**重跑**：`integ046t`（16 例）与 `make check-arch`（L3，含 047t）、`make check-modules`（L2）。046t 任务书的旧单值回读属历史记录**不回写**，权威值以本节为准。

## 测试与证据（每例须有可达 FAIL）

新增 `tools/testcases/arch/min_rom_probe_integ048t.py`（复用 044t/046t 的 ROM 组装范式；body 从 hypv 启动，按用例设向量/模式后 `trap` 切换）。

**探针基座**：
- `cfx_smon`：cg2 rc10 = `CFXPERM` handler；cg3 rc8 = `3`（**handler 回 hypv**，否则 handler 在 supv 读 cg5 会被同一规则再拒）；cg3 rc9 = 0、cg2 rc11 = 0（放开 `switch_cfx_mask` / `excp_cause_mask`）。
- `cfx0`：cg3 rc8 = `2`（body 跑 supv）、cg3 rc10 = body、cg3 rc9 = 0、cg3 rc11 = 0（源 cfx63 的 `trap` 由 cfx0 复位 `cfxtrap` 的 bit63=0 放行）。
- self 用例（4/14）与 **power 用例（7/7a–7f）** 另需：`cfx_smon` cg3 rc10 = body、cg3 rc8 = 2（从 cfx_smon/hypv `trap cfx_smon` 进入 supv body，源 = cfx2）；其余同基座。
- **deleg 布置**：每例在进入 supv 前由 hypv 显式写目标 cfx 的 `cg3 rc12`——开放 = `0x8`；未开放 = `0xFFFF_FFFF_FFFF_FFFF`（复位值，显式写回以免依赖用例执行顺序）。**`cfx_power` 除外**：其 deleg **从不写 `0x8`**（固件不开放）；需要隔离时只打开 cfxreg 轴（`cg2 rc2` 的 bit2=0），使拒绝只能来自 deleg。
- **power 用例的取指布置（仅探针）**：power 用例以 `cfx_smon`/supv 进入（源 = cfx2），body 仍在 `-bios` 窗口 `0xFFFF_FFFF_0000`（cfxha 63）取指 ⇒ 基座把 `cfx_power cg2 rc3`（supv cfxexe）的 **bit0/bit2** 清 0。此布置**仅为探针取指**，不是固件行为（046t 不碰 cfxexe，X 保持默认），也**不是**「全 cg 开放」（不碰 `cg3 rc12`、不把 cg0–cg3 整组清 0）。
- **power 固定地址（关键：须与取指页不同页）**：048 探针自身 ROM 的哨兵放 `0xFFFF_FFFF_1000`（`-bios` 段第 2 页，cfxha 63）= `0x1122_3344_5566_7788`，由 `build_rom` 填充；supv `ld.o`/`st.o` 该地址即读/写 power BootROM 区。**不得**放在 body 取指页（同页会命中取指 TLB 而绕过 `tlb_fill` 的 cfxmem 检查 ⇒ 假绿）；`0x1000` 页在 `-bios` 64 KiB 窗口内，image 需覆盖到 `0x1008`。
- **退出/故障路径不碰 power 内存**：handler 与 semihosting 退出块放 `cfx_smon` SRAM（handler 以 cfx2 运行 ⇒ self，不查 cfxmem），避免 supv 直接写 `cfx_power` RAM 而额外需要 `cfx_power` **cfxmem（`cg2 rc1`）** 的 bit0；power 的 cfxmem **只按例开 bit2**（7a/7b/7c 显式布置），基座不得顺手清 `cg2 rc1` 的 bit0（`cg2 rc3` 的取指位是另一寄存器，见上条）。
- **cfxreg 轴隔离（强制）**：目标 cfx 的 supv 行 `cfxreg`（`cg2 rc2`）位[源]显式清 0 并回读为 0；一般反例配一条同路径「deleg = `0x8` ⇒ 成功」对照（两轴拒绝同为 `CFXPERM`，无对照可能假绿）。**`cfx_power` 例外**：其 deleg 固件不开放 ⇒ power 的 deleg 反例只用 cfxreg=0 隔离、**不写 `0x8`**；power 的 **cfxmem** 反例（7b）以 7a 为同路径成功对照。
- handler 读 `cfx_smon` cg5 rc2/rc3/rc4 记录 `cause_id`/`cause_ip`/`cause_info` 后经 semihosting 退出。

用例：
1. `open_ptw_cg9`：deleg=`0x8` ⇒ supv 写/读 `cfx_ptw cg9 rc0`（PTBR）往返成功；**FAIL 路径**：被拒（门把 cg9 位当置位/只放行枚举过的 cg）。
2. `open_ptw_cg8`：deleg=`0x8` ⇒ supv 写 `cg8 rc8 = 1` → 读 1 → **立即写回 0** → 读 0；必须**在任何 RAM 访存之前**完成（否则后续访存走翻译）。**FAIL 路径**：被拒。
3. `open_pmem_cg15`：deleg=`0x8` ⇒ supv 读 `cfx_pmem cg15 rc4`（dma_status）成功；**FAIL 路径**：被拒（说明 cg15 未随整组开放）。
4. `open_smon_cg5_self`：源=目标=`cfx_smon`、deleg=`0x8` ⇒ supv 读 `cg5 rc2` 成功；**FAIL 路径**：对 self 误加检查（cfxreg 轴对 self 的绕过不得连带绕过 deleg）。
5. `open_cg7`：deleg=`0x8` ⇒ supv 写/读 `cfx_ptw cg7 rc0`（`sram_block_sel`）往返成功（内部存储/空间描述接口由整组开放自然可读，**不单列 bit7**）；**FAIL 路径**：被拒（说明实现只放行了测试枚举的 cg）。
6. `closed_hmon_cg0`：`cfx_hmon` deleg=`~0`（不开放）⇒ supv 读 `cfx_hmon cg0 rc0` ⇒ **`CFXPERM`**（`cause_id=0x80`、`cause_info` = 该 `cfx2rd` 编码、目标 = cfx_hmon）；**开放对照**：cfx_hmon deleg=`0x8` 时同一访问成功（仅探针轴隔离用，固件不写 cfx_hmon 的 deleg）。**FAIL 路径**：门缺失 ⇒ 成功。
7. `closed_power_cg4`：源 = `cfx_smon`/supv（bit2），`cfx_power` deleg=`~0`，**cfxreg 轴 bit2 显式清 0**（隔离）⇒ supv 读 `cfx_power cg4 rc0`（cfx_id）⇒ `CFXPERM`；**不做 `0x8` 成功对照**（固件不开放 power deleg，开放态对照会与策略矛盾）。**FAIL 路径**：成功（deleg 门缺失）。
7a. `open_power_bootrom`：源 = `cfx_smon`/supv，`cfx_power cg2 rc1` 写 `0xFFFF_FFFF_FFFF_FFF3`（bit2=0），cfxreg/deleg 保持 `~0` ⇒ `ld.o [0xFFFF_FFFF_1000]` 成功且值 = `0x1122_3344_5566_7788`；**FAIL 路径**：`CFXPERM` 或值不符（hmon/布置未开 bit2 或开错位）。
7b. `closed_power_bootrom`：同 7a 但 `cfx_power cg2 rc1` 显式写回 `0xFFFF_FFFF_FFFF_FFF7`（bit2=1）⇒ 同一 `ld.o` ⇒ `CFXPERM`（`cause_id=0x80`、`cause_info` = 该地址）；7a 是其同路径成功对照。**FAIL 路径**：读取成功（cfxmem 门缺失）。
7c. `power_bootrom_store`：同 7a（bit2=0）⇒ `st.o` 同一固定地址 ⇒ **`ILLI`**（`cause_id=0x100`；ROM 段 RO），证明 cfxmem 开放不等于可写 power 内存/控制面。**FAIL 路径**：写入成功，或得 `CFXPERM`（说明开错位）。
7d. `power_control_write`：默认双轴（cfxreg=deleg=`~0`）⇒ supv `cfx2rc cfx_power cg2 rc1 = 0` ⇒ `CFXPERM`；`-d cpu` dump 的 `CFX63 M2 MEMMASK` 仍 `0xFFFF_FFFF_FFFF_FFF7`（未被改写）。**FAIL 路径**：写入成功（dump 值变化或访问被放行）。
7e. `power_cg7_closed`：默认双轴 ⇒ supv 读 `cfx_power cg7 rc0`（`sram_block_sel`）⇒ `CFXPERM`。**FAIL 路径**：成功（cg7/控制面被开放）。
7f. `no_power_full_open`：把 048 的整组开放只用于 ptw/pmem/smon（各 `cg3 rc12=0x8`），**不写** `cfx_power`；随后 supv 读 `cfx_power cg4 rc0` 仍 `CFXPERM`，且 dump `CFX63 M2 MEMMASK` = `0xFFFF_FFFF_FFFF_FFF7`（power 未被整组开放波及）。**FAIL 路径**：power 被一并开成 `0x8`（MEMMASK 变化或访问成功），即与整组开放混淆。
8. `closed_hmon_cg8`：`cfx_hmon` deleg=`~0` ⇒ supv 读 `cfx_hmon cg8 rc1`（global_cfx_intr_mask）⇒ `CFXPERM`（证明位图覆盖 cg≥8，锁死「只覆盖 cg0–cg3」的旧结论）。**FAIL 路径**：漏检 ⇒ 成功。
9. `cg3_supv_perm_rd`（cg3 反例·读）：`cfx_ptw` deleg=`0x8`（bit3 恒 1）⇒ supv 读 `cfx_ptw cg3 rc0` ⇒ **`CFXPERM`**（`cid=1<<7`、`cinfo` = 该 `cfx2rd`(cfxha=4,cg3,rc0,rd5) 编码、目标 = cfx_ptw）；**FAIL 路径**：得 `CFXREG`（`cid=1<<2`，说明仍被 `cfx_reg_ptr` 截获）或放行。
10. `cg3_supv_perm_wr`（cg3 反例·写）：supv 写 `cfx_pmem cg3 rc12 = 0` ⇒ **`CFXPERM`**（同一 `cause_id`，`cinfo` 为 `cfx2rc` 编码），且该寄存器值不变（回到 hypv 读回 = 写前值）；**FAIL 路径**：得 `CFXREG`，或写入被错误放行。
11. `cg3_bit3_locked`：hypv 写 `cfx_ptw cg3 rc12 = 0` ⇒ 读回 `0x8`；随后 supv 读 `cfx_ptw cg3 rc0` ⇒ **仍 `CFXPERM`**；**FAIL 路径**：bit3 清 0 生效 ⇒ supv 被放行。
12. `cg3_hypv_allowed`（cg3 正例）：hypv 读 `cfx_ptw cg3 rc0`、写/读 `cfx_ptw cg3 rc12 = 0x…CAFE`（bit3 已 1，读回同值）均成功、无异常；**FAIL 路径**：把 cg3 做成「不分模式一律拒」（hypv 也 `CFXPERM`）。
13. `bit3_forced`：hypv 写 `cfx_ptw cg3 rc12 = 0` ⇒ 读回 `0x8`；再写 `0xFFFF_FFFF_FFFF_FFF7`（bit3=0、其余全 1）⇒ 读回 `0xFFFF_FFFF_FFFF_FFFF`；**FAIL 路径**：读回 `0` / `0xFFFF_FFFF_FFFF_FFF7`。
14. `self_not_exempt`：源=目标=`cfx_smon`、deleg=`~0` ⇒ supv 读 `cg5 rc2` ⇒ `CFXPERM`；对照（deleg=`0x8`）⇒ 成功；**FAIL 路径**：self 被豁免。
15. `hypv_unaffected`：`cfx_ptw` deleg=`~0` ⇒ hypv 读 `cfx_ptw cg2 rc0` 成功；**FAIL 路径**：把 hypv 纳入检查。
16. `user_unaffected`：`cfx_ptw` deleg=`~0` ⇒ cfx0 → user 读 `cfx_ptw cg0 rc0` 成功（保持现有模型）。
17. `user_cg3_cfxreg`：cfx0 → user 读 `cfx0 cg3 rc0` ⇒ **`CFXREG`**（user 不走 deleg，仍由 `cfx_reg_ptr` 判定；与 `045t::cfx2_cg3_nonhypv` 对齐）；**FAIL 路径**：把 user 的 cg3 也改成 `CFXPERM`。
18. （可选）`jail_unaffected`：同 16，`switch_run_mode=1`。
19. 零回退：`make check-arch` 内 `044t/045t/049t/integ039t/integ040t/integ042t/integ044t/integ046t/integ047t` + 新探针全 PASS。
20. 证据脚本 `.work/evidence/INTEG-048t/{run.sh,check.py}`：默认全绿；`--inject` ≥3 处（建议：门内 bit 判定、hmon 的三份 deleg 写值、hmon 的 `cfx_power cg2 rc1` 写值先把 bit2 写回 1）→ 对应 `integ046t`/048 用例 FAIL → `cp` 备份 + `md5sum` 还原 → 回绿，输出 `EVIDENCE INJECT: PASS`。

**受影响既有探针（须同步/重跑；逐条核运行模式）**：

- `045t::cfx2_cg3_nonhypv`：**user** 模式访问 cfx0 cg3 ⇒ **期望仍 `CFXREG`，不改值**（deleg 只查 supv）；仅把用例描述改为「user/jail 的非 hypv cg3 ⇒ `CFXREG`」并加一行指针到本任务 `cg3_supv_perm_rd`；**不得**顺手改成 `CFXPERM`。
- `045t::cfx2_full_regface`：hypv 写 `cfx0 cg3 rc12 = 0xCAFE`（bit3 已为 1）⇒ 读回不变，**无需改**；重跑确认。
- `046t`：`smon.S` 的 supv 访问不含 cg3；hmon 的 cg3 读写均在 hypv ⇒ 不受 cg3 变更影响；受影响者是 smon 的 cg5/cg8/cg9/cg15 —— 由 hmon 写 `0x8` 整组开放（见 §046t 前置修正），**不再逐位清**。**新增** smon 的 power BootROM 固定地址 `ld`：由 hmon 的 `cfx_power cg2 rc1` bit2=0 放行（R6），`cfx_power` 不进整组开放、deleg 保持 `~0`；046t 用例数 15 → 16。
- `044t` / `integ044t`：`init_masks` 中 cfx0/cfx3 的 cg3 `rc0`–`rc4` 读、`integ044t` 的 cg3 写全部在 **hypv** ⇒ 期望不变；重跑。
- `integ038t`/`integ039t`/`integ040t`/`integ042t`/`integ047t`：body 均在 hypv、fault handler 经 `switch_run_mode=H` 回 hypv、无 supv cg3 ⇒ 期望不变；重跑零回退。
- **机械复核（范围含共享固件）**：`grep -n "cfx2r[dc]" tests/shared/bootrom/**/*.S tools/testcases/arch/*.py` 逐处标注「运行模式 + 目标 cfx 的 deleg 布置」；凡 **supv 且目标 cfx 未开放**的访问，须在该探针基座显式写 `0x8`（或改到 hypv），并在完成区逐条登记（属本任务范围）；未发现则写「复核：无未开放的 supv 访问」。

**门控**：`make check`、`make check-modules`、`make check-arch`、`check-patch-tree`、`check-source-state`、`check-component-changelog` 全 rc=0；`check-spec-readonly` 不受影响（不动 `spec/`）。

## 修改文件范围

- `components/qemu/patches/target/dadao/helper.c.patch`（唯一 QEMU 面：`cfx_deleg_denied` + 两处调用点 + 写侧 bit3 掩码）。
- `components/qemu/changelog.md`（同变更追加一条，`Process-01 §10`）。
- `tools/testcases/arch/min_rom_probe_integ048t.py`（新）。
- `tools/testcases/arch/README.md`（登记新探针 1 行）。
- `Makefile`（`ARCH_CFX_PROBES` 加 `integ048t`）。
- **046t 前置修正**：`tests/shared/bootrom/step5/hmon.S`（三份 `cg3 rc12 = 0x8` + 三路回读 + **一行 `cfx_power cg2 rc1 = 0xFFFF_FFFF_FFFF_FFF3`** + power cfxmem/deleg 回读）、`tests/shared/bootrom/step5/smon.S`（`rd17/18/19/21/22` 装入 + `rd20` 读 BootROM + 自检期望）、`tools/testcases/arch/min_rom_probe_integ046t.py`（`deleg_dump` 三值 `0x8` + 新 case `power_bootrom_read`）、`tests/shared/bootrom/step5/README.md`（hmon 描述 + 观测寄存器表）。
- `tools/testcases/arch/min_rom_probe_045t.py`（**仅同步**：`cfx2_cg3_nonhypv` 用例描述标明 user/jail 轴、期望值 `CFXREG` **不变**，并加指针到 048 的 supv 用例）。
- `.tao/contracts/contract-see.md` §3：一条 delegation 投影（`bit=0` 允许 supv 访问、`bit3` 恒 1、覆盖全 64 cg、不豁免 self、拒绝 = `CFXPERM` **含 cg3**；**软件约定：需开放的 cfx 由 hmon 写 `cg3 rc12 = 0x8` 整组开放，不逐 cg 清位**；**`cfx_power` 例外：其 deleg 保持 `~0`，只写 `cg2 rc1` 的 bit2=0 供 smon 读 BootROM（cfxmem 轴，不改 deleg 语义）**；user/jail 的非 hypv cg3 仍由 `cfx_reg_ptr` 报 `CFXREG`；标 `[DADAO-13 §1][DADAO-23 §3]`）。
- `.tao/knowledge/milestones.md`（本任务流水 1 行；收尾只改状态/时间）。
- **不动**：`spec/**`（含 `manifests/spec-readonly.lock.toml`）、`contracts/**`（机器可读）、`tests/inst/**`、`docs/**`、`.tao/adr/**`、`cpu.h.patch`/`cpu.c.patch`、`tests/shared/bootrom/step5/{power.S,hmon.lds,smon.lds,power.lds}`、Linux 侧任何测试。

## 验收

1. QEMU 侧：supv 对目标 cfx 的 cg 按 mask 位判定（0 允许 / 1 ⇒ `CFXPERM`）；**cg3 不作例外**——supv 访问任何 cfx 的 cg3 ⇒ `CFXPERM`（`cid=1<<7`），不再得 `CFXREG`；hypv 访问 cg3 允许；user/jail 的 cg3 仍 `CFXREG`；写侧 bit3 恒 1。
2. 新探针用例 1–17（+可选 18）与 **7a–7f** 全 PASS，每例有可达 FAIL（19 = 零回退、20 = 证据脚本）；其中 cg3 覆盖：读反例 `cg3_supv_perm_rd`、写反例 `cg3_supv_perm_wr`、不可绕过 `cg3_bit3_locked`、hypv 正例 `cg3_hypv_allowed`、user 对照 `user_cg3_cfxreg`；power 覆盖：`open_power_bootrom`/`closed_power_bootrom`/`power_bootrom_store`/`power_control_write`/`power_cg7_closed`/`no_power_full_open`。
3. **046t 在 048 强制开启后仍通过**：`integ046t` **16 例** PASS（`deleg_dump` 的 `rd17`/`rd18`/`rd19` **均 = `0x8`**；`power_bootrom_read` 的 `rd20`/`rd21`/`rd22` 见 4b）；`make check-arch`（L3）全 PASS（含 047t 与既有 8 探针零回退）；`make check-modules`（L2）rc=0。cg3 对本任务链无额外处理需求（smon 无 supv cg3 访问、hmon 的 cg3 写入在 hypv）。
4. **正例覆盖**：ptw cg8/cg9、pmem cg15、smon cg5（self）、cg7（`sram_block_sel`）在 deleg=`0x8` 下 supv 访问成功；**反例覆盖**：`cfx_hmon`（cg0、cg8）与 `cfx_power`（cg4）的 **deleg 未开放** ⇒ supv 读取 `CFXPERM`；power 反例只用 cfxreg=0 隔离（**无 power deleg=`0x8` 对照**），其余反例保留「deleg=`0x8` ⇒ 同路径成功」对照，cfxreg 轴位[源]回读为 0。
4b. **power BootROM 只读**：smon 在固定地址 `0xFFFF_FFFC_0000` `ld` 成功 ⇒ `rd20 = 0x44424F54_0001_0002`；`rd21 = 0xFFFF_FFFF_FFFF_FFF3`（`cfx_power cg2 rc1` 相对复位只清 bit2）；`rd22 = 0xFFFF_FFFF_FFFF_FFFF`（power deleg 未被打开）；048 探针：`ld` 成功（7a）、bit2=1 ⇒ `CFXPERM`（7b）、`st` ROM ⇒ `ILLI`（7c）、控制/寄存器写与 cg7 读 ⇒ `CFXPERM`（7d/7e）、整组开放后 power 仍不开放（7f）。
5. `bit3` 写 0 读回 `0x8`；写 `0xFFFF_FFFF_FFFF_FFF7` 读回 `0xFFFF_FFFF_FFFF_FFFF`；且写 0 之后 supv 的 cg3 访问仍 `CFXPERM`（不可绕过）。
6. **self 不豁免**：源=目标=cfx2 且 deleg=`~0` ⇒ `CFXPERM`；deleg=`0x8` ⇒ 成功。
7. `make check`/`check-modules`/`check-arch`/`check-patch-tree`/`check-source-state`/`check-component-changelog` 全 rc=0。
7b. **无 cg3 `CFXREG` 残留**：任务书 + `helper.c.patch` + 探针内 `grep -n "cg3"` 逐处核，无「cg3 仍 CFXREG / 例外 / 先按 CFXREG」表述；QEMU 侧 `cfx_deleg_denied` 不含 `cg == 3` 早退项（判据以真实 `grep` 输出落完成区）。
7c. **无逐 cg / 旧 deleg mask 残留**：`grep -niE "FC[F]B|7[F]FB|F[F]DF|逐位|逐 cg" tests/shared/bootrom/step5/{hmon.S,smon.S,README.md} tools/testcases/arch/min_rom_probe_integ046t.py tools/testcases/arch/min_rom_probe_integ048t.py` ⇒ **无命中**（`-i` 必须带，`hmon.S`/`smon.S` 的值为小写十六进制）；`grep -n "cfx2rc.*cg3, rc12" tests/shared/bootrom/step5/hmon.S` ⇒ **3 条**（ptw/pmem/smon，值均 `0x8`、**无** `cfx_power`）；`grep -n "cfx2rc.*cfx_power" tests/shared/bootrom/step5/hmon.S` ⇒ **仅 1 条** `cg2, rc1`（值 `0xFFFF_FFFF_FFFF_FFF3`）；`grep -n "cfx2rd.*cfx_power" tests/shared/bootrom/step5/hmon.S` ⇒ **仅 2 条**只读回读（`cg2, rc1` / `cg3, rc12`）；**无** `cfx2rc.*cfx_power.*cg3` / `cg2, rc2` / `cg2, rc3`（各段真实输出落完成区）。**注**：`0x…FFF3` 在本任务中有两处合法用途（ptw/pmem 的 `cg2` cfxreg mask 既有值、power 的 `cg2 rc1` 只读值），故残留判据不再 grep `FFF3` 单值，改按 `cg3 rc12`/`cfx_power` 行定位；任务书仅在 §用户授权原话 保留作废数值作为裁定存证。
8. 证据脚本默认与 `--inject` 均 rc=0（`EVIDENCE INJECT: PASS`）；还原用 `cp`+`md5sum`（禁 `git checkout/restore/stash`）。
9. `install-host` 后 `.dadao/cross-toolchain/bin/qemu-system-dadao` md5 == `.work/build/qemu/qemu-system-dadao`（防旧安装根假绿，`ISS-210`）。
10. `git diff` 证明 `spec/**`、`contracts/**`、`.tao/adr/**`、`tests/inst/**` 零改动；**无 Linux 侧测试新增**。
11. 完成区 ≤30 行、审阅记录每轮 ≤40 行；任务书 `**状态**` 置 `待验收`；临时产物统一 `/tmp/opencode/INTEG-048t/`。

## BLOCKED / 遗留（如实登记，不硬造）

- **无实现级 BLOCKED**：R1–R6 已裁定；QEMU 消费点、写侧 bit3、046t 前置修正（含 power BootROM 只读）均在本任务内闭环。
- **开放策略为软件约定（R5/R6）**：spec 未规定 hmon 必须开放哪些 cfx，也未规定「整组开放」的写法；本任务按用户裁定统一写 `0x8`（ptw/pmem/smon）、power 只写 `cg2 rc1` 的 bit2=0，并投影到 `.tao/contracts/contract-see.md §3`，**spec 正文不动**。
- **`cfxmem` 无方向位（如实登记）**：`cfxmem` 0 = 允许直接 `ld/st`，硬件不区分读/写；「smon 只读 power BootROM」是**固件约定**（smon 只发 `ld`）+ ROM 段 RO（`st` ⇒ `ILLI`）。本任务**不测** power 的 RAM/MMIO 写（未要求，且硬件上该面随 bit2=0 可写）；若将来要求硬件级只读，须另立任务/改 spec。
- **power 的 cfxexe 不动**：`cfx_power supv cfxexe` bit2 保持 1（BootROM 的 X=1 属 power 自身启动代码）；smon 从 cfx2 SRAM 取指（self），不执行 power 代码。048 探针为自身取指清 `cfx_power cg2 rc3` 的 bit0/bit2 属**探针布置**，不是固件行为、不得据此改 `hmon.S`。
- **spec 正文缺口（不改，登记）**：`DADAO-13 §1` 未写「拒绝走哪个异常」「覆盖 64 位全 cg」「self 是否豁免」；`DADAO-23 §2` 只规定「各 cfx 清自身 deleg」，未规定 power BootROM 的只读开放写法（R6 为本项目约定）。
- **046t 任务书为历史记录**：其旧的单值回读不回写；权威值以本任务书 §046t 前置修正（三值 `0x8` + power 三值）为准。
- **Linux 侧不测**：用户裁定 Linux 开发过程不需要验证 deleg **与 power BootROM 只读路径**；本任务**不新增** Linux 侧测试，行为仅由 048 探针、046t 真链与架构核验。
- **生产 SBI DMA provider 的 supv 前置**：047t 只定义契约、provider 以 hypv 运行；将来若以 supv 运行 provider，须由 hmon（或自身 init）对 `cfx_pmem` 写 `0x8` 整组开放——本任务不实现。

## 约束

- 只做本任务；**不提交、不 push**（提交权归 architect）；不跑 `check-full` 夜跑；重建前申报耗时（首次全量 10–30 min、增量 1–3 min）。
- 不改 `spec/**`（含 `manifests/spec-readonly.lock.toml`）、不改 `.tao/adr/**` 正文；缺口登记，不越权补正文。
- 不新增 Linux 侧测试；不逐 cg 清位、不引入除 `0x8` 之外的 deleg 写值（测试中的 `~0` 仅作「未开放」态）。
- **power 专项**：`hmon.S` 对 `cfx_power` **只允许** `cg2 rc1 = 0xFFFF_FFFF_FFFF_FFF3` 一行；**禁**写 `cfx_power` 的 `cg3 rc12`、`cg2 rc2/rc3`、cg7/控制寄存器，**禁**把 power 纳入 `0x8` 整组开放；`cfx_power` 的 cfxexe 不动。
- **不改 QEMU 的 cfxmem 消费点**（R6 只靠 hmon 写 mask + 探针断言）；若实现中发现必须改 QEMU，先停下报告，不得擅自扩大范围。
- `components/qemu/patches/**` **禁手工编辑**（`Process-01 §6.1.1`）；改源码树后导出。
- 失败保留现场并继续推进（自行处置/有据重试并记次数）；**仅需用户语义裁定**时留问。
- 临时/一次性产物一律 `/tmp/opencode/INTEG-048t/`；日志落 `.work/log/integ/`。

## 参考对照（`DADAO-0628` 只读检索；**内容溯源，非执行必需**，不复制代码、不作执行依赖）

- **0628 做法**：O1 只存储 `cfx_hypv_cg_reg_deleg[64]`，写路径 `value | (1ULL << 3)`（bit3 强制 1），注释明写「no permission enforcement reads it yet -- that is O2 scope」（`components/qemu/patches/0024-*.patch`）；`code-agent/tasks/KL-111a-*-permission-recon.md` 结论：「deleg 拒绝时的异常类别是真正的 wiki 空白」。
- **本项目差异**：v5 采纳 0628 的 `| 1<<3`（R2），但**异常类型定为 `CFXPERM`**（ADR-0045 D6 的权限拒绝口径）、**覆盖 64 位全 cg**（R3），并**不豁免 self**（R4）；**cg3 不作例外**（bit3 恒 1 ⇒ supv 恒 `CFXPERM`）。0628 无消费点、也无 step5 启动链，故没有「hmon 开放哪几个 cfx / 怎么开」的对照面；**`0x8` 整组开放是本项目约定（R5）**，不从 0628 推导。
- **建议落点**：独立 gate（§接口规范 2–3），不复用 `cfx_perm_denied`（后者是两轴 cfxreg，self 绕过 cfx 轴，语义不同层）。
- **power BootROM 只读**：0628 无「smon 读 power BootROM」的对照面（其 step5 启动链未落地），**R6 是本项目约定**，仅内容溯源到两轴 cfxmem 模型（ADR-0045 D2/D3），不从 0628 推导。

## 用户授权原话

**用户裁定（主会话转述，逐字落纸，2026-10-31）**：

> 用户已纠正并统一 `cfx_<cfxname>_hypv_cg_reg_deleg` 语义：
> - 每个 cfx 一个 64 位寄存器，管理该 cfx 的 64 个 cg 是否允许 supv 访问；
> - bit=0 允许，bit=1 拒绝；
> - bit3 硬件固定 1，软件写 0 无效，读回恒 1；
> - supv 访问任何 cfx（含自身）都查目标 cfx 的 mask，**不做 self 豁免**；
> - hypv 自身访问不受该 mask 约束；
> - 除 cg3 仍按现有 `CFXREG` 外，deleg 拒绝用 **`CFXPERM`**；
> - 不再采用此前"只覆盖 cg0–cg3"的错误结论。

**用户补充裁定（主会话转述，2026-10-31；**取代**上一条「除 cg3 仍按现有 `CFXREG` 外」）**：

> `cg3` 是合法寄存器组，只是 bit3 固定 1，supv 被权限拒绝，因此 **cg3 的 deleg 拒绝也统一为 `CFXPERM`，不再例外走 `CFXREG`**；hypv 访问 cg3 仍允许。

**用户第三次裁定（主会话转述，2026-10-31；简化模型，**取代**任何「逐 cg / 逐位清 mask」的方案；下列旧数值仅作存证，见 §验收 7c 的残留判据）**：

> - hmon 对需要开放的 cfx **一次性开放所有 cg 给 smon**，不要逐 cg 询问/逐位清；
> - 对 `cfx_ptw`、`cfx_pmem`、`cfx_smon` 写 `hypv_cg_reg_deleg = 0x0000_0000_0000_0008`（只保留 bit3 固定 1，其余 cg0–cg63 全允许）；
> - 不再使用 ptw `0x…FCFB`、pmem `0x…7FFB`、smon `0x…FFDF` 这类逐位 mask；
> - `cfx_hmon`/`cfx_power` 不开放；默认 mask 保持全 1（**第四次裁定限定为 deleg 不开放**；power 另按 R6 开 cfxmem bit2）；
> - 测试程序必须包含"未开放 cfx 的 supv 读取 → CFXPERM"反例，并隔离 cfxreg 轴，确保失败确由 deleg 引起；
> - Linux 开发过程不需要测试这一点，只由架构/探针验证；
> - cg3 仍合法但 bit3 固定 1，supv 访问 → CFXPERM；hypv 允许；
> - `cg7` 空间描述接口通过"全 cg 开放"自然可读，不需要单独列 bit7。

**用户第四次裁定（主会话转述，2026-10-31；**限定**上一条「`cfx_hmon`/`cfx_power` 不开放」为 **deleg 不开放**，并新增 power cfxmem 只读开放）**：

> - smon 按**固定地址**读取 `cfx_power` 的 BootROM；不通过 cg7 枚举 power；
> - hmon 只修改 `cfx_power cg2 rc1`（supv cfxmem mask）的 **bit2=0**，允许 smon 只读；
> - 不开放 `cfx_power` 的 cg7/cfxreg/控制寄存器；
> - `cfx_power` 的 `hypv_cg_reg_deleg` 仍不开放（保持默认）；
> - BootROM 的 `X=1` 是 power 自己执行启动代码，和 smon 只读不冲突；
> - Linux 开发过程不需要测这个只读路径，测试探针可覆盖。

**主会话派单原话（原样落纸，背景保留；其中「写 BLOCKED」「cg3 固定拒绝」等要求已被上述裁定取代）**：

> 在 /mnt/tao/DADAO-v5，master 已含 INTEG-046t/047t，工作树干净。创建 `INTEG-048t` 任务书：`cfx_*_cg_reg_deleg` 强制检查（QEMU 实现缺口）。文件名放 `.tao/tasks/integ/`；先确认 048 未占用，若占用顺延。
>
> 任务范围（先调查现状再落纸，不要假设）：
> - 在 QEMU 的 `cfx2rd`/`cfx2rc` 访问路径强制 `hypv_cg_reg_deleg`：目标 cfx 的 cg 对应 bit=0 允许 supv 访问；bit=1 拒绝；cg3 固定 1（禁止）；hmon/hypv 路径按 spec 处理；user/jail 仍按现有权限模型。
> - 拒绝时按 spec 触发正确异常（先核 DADAO-12/13：是 CFXREG 还是 CFXPERM；不要猜）。
> - 不修改 `spec/**`；如 contract 投影需同步，限制在 `.tao/contracts/`。
> - 测试：deleg=0 允许、deleg=1 拒绝、cg3 固定拒绝、hmon 设置前后差异、模式轴不受影响、既有 044t/046t/047t 零回退。
> - QEMU 需重建；任务书要写清预检、预计耗时、证据脚本（注入→FAIL→cp+md5 还原→回绿）。
>
> 流程：… 若 `hypv_cg_reg_deleg` 位语义/异常类型有歧义，写 BLOCKED 并给替代证据，不要猜。

## 下发前预检（5 项）

1. **任务书内部一致**：PASS——§已裁定语义（R1–R6，含「cg3 无例外」「`0x8` 整组开放」「R6 = power cfxmem bit2 只读」）↔ §接口规范 2–8（门/调用点/cg3/写侧/复位/power 不改 QEMU）↔ §046t 前置修正（三处 `0x8` ↔ smon 实际 cg 全覆盖；power 一行 `cg2 rc1` + 五路回读 + `rd20/21/22` + `deleg_dump` 改 + `power_bootrom_read` 新 + README）↔ §测试 1–17（+可选 18）、7a–7f、19/20 ↔ §验收 1–4b/5–10 逐项对应；「整组开放」对应测试 1–5（正例）与 6/8（未开放反例）；「cg3 统一 `CFXPERM`」对应 9–12、17；「power 只读」对应 7a–7f 与验收 4b；「不与整组开放混淆」对应 7f 与验收 7c 的 `cfx_power`/`cg3 rc12` grep；无实现级 BLOCKED。
2. **验证手段前置实际可用**：**部分需自建**——本 worktree 无 `.work/`/`.dadao/` ⇒ 首次 `make build-qemu` + `make install-host` 属**长任务**（10–30 min，须申报 + 后台 + `XXX_EXIT`）；预检原型 `/tmp/opencode/INTEG-048t/proto.py` 与日志（`deleg0_sup-cpu.log`/`cg3supv-cpu.log` 等）已在主仓库跑通 5 条基线；`make check-source-state`、`tools/infra/make_patch.py`、`check-patch-tree` 流程既有绿；`make build-bootrom` 依赖安装根工具链（全量构建后可用）。power 只读路径**不需要**新 QEMU 构建面（复用 044t 的 cfxmem 消费点），但 046t 真链需 `make build-bootrom`（安装根就绪后）。
3. **验收逐条可跑性**：验收 1/2/4/5/6 **现在可跑**（同路径已被原型验证，QEMU 全量构建 + 增量重建后；cg3 用例期望 `CFXPERM` 由 §已裁定语义给定，FAIL 路径为现状 `CFXREG`/放行，已在 `cg3supv-cpu.log` 记录基线；未开放反例的 FAIL 路径为现状「成功」，已由原型 `deleg0_sup` 记录）；验收 4b **实现后可跑**（基线由复位 `cfxmem=0xFFF7` 与 `helper.c.patch:641` 的 `cfx_perm_denied` 直接给出 ⇒ 现状 `CFXPERM`；实现后由 `integ046t` 真链 + 048 探针 7a–7f 复核）；验收 3 **可跑**（`integ046t` **16 例** + `check-arch` 串行、分钟级；`build-bootrom` 依赖安装根工具链）；验收 7–10 **可跑**；验收 7b/7c 的 `grep` 复核**需在实现后跑**（任务书侧已按本次修订清零，仅 §用户授权原话留存证）；无 BLOCKED 项。
4. **与 `contracts/`、`tests/inst/` 一致**：PASS——只用既有指令（`trap`/`escape`/`cfx2rd`/`cfx2rc`/`ld.o`/`st.o`/`set.zw`/`or.w`），`contracts/opcodes.yaml` 无新增；`tests/inst/**` 不改；`contracts/` 机器可读目录不改。
5. **拟改文件 × `spec/` 清单**：**不命中**——`components/qemu/**`、`tools/testcases/arch/**`、`tests/shared/bootrom/step5/**`、`Makefile`、`.tao/contracts/contract-see.md`、`.tao/knowledge/milestones.md` 均不在 `spec/`；`manifests/spec-readonly.lock.toml` 不动 ⇒ 无 spec 授权需求。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 任务书修订（architect，2026-10-31；未进入验收轮次）
- 依据用户**补充裁定**（cg3 是合法寄存器组，bit3 恒 1 只是权限约束；cg3 的 deleg 拒绝统一 `CFXPERM`；hypv 访问 cg3 允许）修订：撤销 R1 的「cg3 例外」；`cfx_deleg_denied` 去掉 `cg == 3` 早退项；cg3 不再落到 `cfx_reg_ptr` 的 `CFXREG` 分支（该规则保留给 user/jail）。
- 用例新增 `cg3_supv_perm_rd`/`cg3_supv_perm_wr`/`cg3_bit3_locked`/`cg3_hypv_allowed` 与 `user_cg3_cfxreg`；后序用例重编号，全文引用同步。
- 新增 §受影响既有探针（`045t`/`046t`/`044t`/`integ044t`/`integ038t`/`039t`/`040t`/`042t`/`047t`）：`045t::cfx2_cg3_nonhypv` 为 **user** 轴 ⇒ 期望 `CFXREG` **不变**（仅描述同步 + 指针）。

#### 任务书修订 2（architect，2026-10-31；未进入验收轮次）
- 依据用户**第三次裁定（简化模型）**把开放策略改为 **R5 = 整组一次性开放**：hmon 对 `cfx_ptw`/`cfx_pmem`/`cfx_smon` 各写 `cg3 rc12 = 0x8`（唯一置位 = 恒 1 的 bit3 ⇒ 全 cg 允许）；删除「按 smon 实际 cg 逐位清」的方案与旧数值（ptw `FC[F]B` / pmem `7[F]FB` / smon `F[F]DF`），任务书内仅 §用户授权原话 保留作废数值作存证。
- §046t 前置修正：三处 `0x8` + 三路回读（`rd17/18/19`）+ smon 自检三条 `0x8` + `deleg_dump` 三值 + README 同步；重跑 046t/L2/L3。
- §测试重写：正例 `open_ptw_cg9`/`open_ptw_cg8`/`open_pmem_cg15`/`open_smon_cg5_self`/`open_cg7`；反例改为「未开放 cfx（`cfx_hmon` cg0/cg8、`cfx_power` cg4）supv 读取 ⇒ `CFXPERM`」且**每例配 `0x8` 同路径成功对照**以隔离 cfxreg 轴；`bit3_forced` 改用 `0x0` 与 `0xFFFF_FFFF_FFFF_FFF7`（去旧数值）；删除原 bit2 逐位 deny/allow 用例。
- §目标/§接口规范/§修改文件范围/§验收/§BLOCKED/§预检 同步；新增验收 7c（无逐 cg/旧 mask 残留的 `grep` 判据）与「Linux 侧不测」约束；范围仍仅任务书（+ `milestones.md` 一行），未实现。

#### 任务书修订 3（architect，2026-10-31；未进入验收轮次）
- 依据用户**第四次裁定**：把「`cfx_hmon`/`cfx_power` 不开放」限定为 **deleg 不开放**；新增 **R6 = `cfx_power cg2 rc1` bit2=0（supv cfxmem）只读开放**，明确不是 deleg，不写 cg3 rc12/cg2 rc2/cg2 rc3/cg7；`cfx_power` 的 cfxexe 与 deleg 保持默认。
- §背景 +7、§已裁定语义 R5 改写 + R6 + 推论末句（power 是唯一例外）、§目标 +5、§接口规范 +8（该路径不改 QEMU）。
- §046t 前置修正：hmon 增加一行 `cfx_power cg2 rc1 = 0xFFFF_FFFF_FFFF_FFF3`（只清 bit2）；smon 固定地址 `0xFFFF_FFFC_0000` 读 BootROM 头（`rd20=0x44424F54_0001_0002`）、`rd21=power cfxmem`、`rd22=power deleg`；`rd6` 重装提醒；`deleg_dump` **仍只**断言 ptw/pmem/smon = `0x8`，新增 `power_bootrom_read`；README 同步；046t 15→16 例。
- §测试：新增 7a–7f（固定地址读成功/关闭 ⇒ `CFXPERM`/写 ROM ⇒ `ILLI`/控制写与 cg7 仍拒/整组开放不含 power）；power 的 deleg 反例不写 `0x8`；探针取指仅清 `cfx_power cg2 rc3` bit0/bit2 并标明是探针布置。
- §验收新增 4b、7c 改为按 `cfx_power`/`cg3 rc12` 行 grep（`FFF3` 现有两处合法用途，不再按单值 grep）；§BLOCKED 增加 cfxmem 无方向位与 power cfxexe 说明；§约束/§预检/§milestones 同步。范围仍仅任务书 + `milestones.md` 一行，未实现。
