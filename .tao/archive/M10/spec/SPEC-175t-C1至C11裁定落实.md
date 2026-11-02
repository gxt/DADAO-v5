# SPEC-175t: C1–C11 裁定落实与 DADAO 六册版本升级

**模块**：spec
**项目里程碑**：M10
**依赖**：SPEC-174t（冲突清单 C1–C11）、SPEC-173t（SimRISC 0.5.6-rc 口径）
**状态**：已验证

## 执行环境
**执行环境**：本地（文档 + 一个门控脚本；`spec/` 只读锁按本任务授权更新）

## 接口规范

### 背景（用户 2026-10-26 逐条裁定）
SPEC-174t 登记了 C1–C11 语义冲突并只登记未改。用户已逐条裁定（记录见下），本次**统一落实**，并**发布六册**（去 `-rc`，日期 2026-10-26）。

**用户裁定原话（经主会话问答）**：
- C1：「AEE 删除乘除法解释/示例/`ext.so` 提示，不加交叉引用」
- C2：「SBI 地址类返回 `rb8`、值类 `rd8`」
- C3：「删 `ABI:231` 的 16 字节值除外；231 改通则『低地址块 → 低号寄存器』；238 保留；HFA/HPA 不动」
- C4：「维持现状——溢出 per-bank、栈槽全局声明序单栈区；spec 只补措辞；ADR/契约不改」
- C5：「`cfx_timer` 改名 `cfx_time`；`cfx_hart` 加每 hart 比较器 + `1<<10 TIMER`；SBI §10 只留 `SBI_TIME_GET`，`SET_TIMER` 移 §7」（寄存器模型：用户选「ARM Generic Timer 风格」）
- C6：「同步异常全部不可屏蔽；仅异步可屏蔽」（含 `SOFT_RESET`；门控放里程碑）
- C7：逐 cfx `trap cfx_<name>, HBI_<name>_INIT`（FID `0x30001`）→ `trap cfx_smon` 交接；删除 `cfx_power` 的 `prev_cfx_mask=-1` + `escape cfx_power` trampoline
- C8：「SEE §3.8 加预留/未启用说明（decode ILLI），不加跨册引用」
- C9：「按有意排除处理——注释改『除 hmon 外（hmon 由 hypv 保留）』，不加行」
- C10：「补 rc1 保留行」
- C11：「保留『或』，补『用户 `trap` 目标为 smon 时用 `cfx_smon_user_*`』」
- 版本号（用户 2026-10-26）：「这次可以定版，去掉 `-rc`，再有改动，开启新的 `-rc`（未经我认可，只动 `x.y.z` 中的 `z`）；注意，发布之前，把版本与变更记录好好整理一下，这是给人看的」⇒ **本次六册发布**（去 `-rc` + 日期 2026-10-26）。

### 输入（只读事实）
- `spec/DADAO-11/12/13/21/22/23`、`spec/Toolchain-01`（现行文本；行号见 SPEC-174t 冲突表）
- `.tao/contracts/contract-abi.md §4.3`（C4 已定的契约口径，**不改**）
- `.tao/adr/adr-0018`（C4）、`adr-0031`（D6/D7）、`adr-0037`（**均不改**）
- `.tao/contracts/contract-cfx-aliases.md`（**机械生成**，禁止手工维护）

### 约束
- 只改：6 册 DADAO + `spec/Toolchain-01` + `.tao/contracts/contract-asm.md`（示例）+ `tools/spec/`（新门控）+ `Makefile`（门控接入）+ `manifests/spec-readonly.lock.toml`（授权与 sha256）+ 本任务书 + `.tao/knowledge/milestones.md`。
- **不改** SimRISC 13 册、不改 ADR、不改 `contract-abi`/`contract-see`。
- 除本任务书列出的语义改动外，**不做任何“顺手”修改**。
- `spec/` 只读锁：用户裁定即本任务授权；授权文字与 sha256 同笔更新。

## 改动清单（逐条，必须一一对应）

### C1 — AEE 删除乘除法段（`DADAO-11`）
- 删除从 `**乘除法**：乘法结果为 128-bit…` 到引用块 `> 若操作数经过加减乘等运算后高位被污染，除法和乘法前需 ext.so 重新扩展。` 的整段（含两个 `simrisc` 示例块）。
- 保留其后的 `**移位**：…` 及之后内容。
- **不加**任何交叉引用或替代说明。

### C2 — SBI 返回值 bank（`DADAO-22`）
- `SBI_PTW_GET_PTBR` 行：`rd8 = base` → **`rb8 = base`**；同章示例注释 `返回 rd8 = base` → `返回 rb8 = base`。
- `SBI_PMEM_GET_PM_START` 行：`rd8 = start` → **`rb8 = start`**。
- `SBI_PMEM_ALLOC_PAGE` 保持 `rd8 = ppn`（**PPN 是页号，不是绝对地址**，属值类）。
- 在 §1「调用约定」补一句：
  > **返回值 bank**：标量、页号、计数、掩码用 `rd8`；绝对地址用 `rb8`。
- 其余 `rd8` 返回行不动。

### C3 — ABI 231 行（`DADAO-21`）
- 将：
  > ≤ 64 字节：拆分为 1-8 个 8 字节块，放入 RD bank，高位块先入高寄存器（**16 字节值除外**，见下条）
  改为：
  > ≤ 64 字节：拆分为 1-8 个 8 字节块，放入 RD bank，**低地址块先入低号寄存器**（与 `ldm.o`/`stm.o` 寄存器号递增 = 地址递增一致）
- 238 行及「16 字节值」整节**不改**；HFA/HPA 规则**不改**。
- 全册 grep 确认无其它「高位块先入高寄存器」。

### C4 — ABI §3.2.4 补消歧句（`DADAO-21`）
- 在「三 bank 共享同一个栈增长方向，各组溢出参数连续紧凑存放。」之后补：
  > 溢出判定按 **bank 独立**（某 bank 槽位用尽只影响该 bank）；一旦参数进入栈传递，所有溢出参数按源声明中的**全局从左到右顺序**放入**同一个连续栈区**。
- 仅补此句；`contract-abi §4.3`、ADR-0018/0031 **不改**。

### C5 — `cfx_timer` → `cfx_time` + `cfx_hart` 比较器（ARM Generic Timer 风格）

#### C5.1 SEE §4.11（`DADAO-12`）
- 标题：`### 4.11 cfx_timer - timer/counter` → `### 4.11 cfx_time - 全局时间计数器`。
- 正文补一句：
  > `cfx_time` 为 **per-system** 全局时间计数器，所有 hart 共享同一时间基准；只提供时间读数，不产生中断。每 hart 的定时器比较与中断由 `cfx_hart` 提供。
- 寄存器表**替换为**：

  | cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
  |----|----|---------|---------|--------|------|------|
  | 10 | 7 | time freq | cfx_time_freq | — | RO | 计数频率（Hz），硬件设置 |
  | 10 | 8 | time value | cfx_time_value | 0 | RO | 64 位全局时间计数值，自由运行 |

- 异常原因表**删除** `1 << 10 TIMER` 行（只保留 CFXTRAP/CFXMEM/CFXREG）。

#### C5.2 SEE §4.8 `cfx_hart`
- 补 rc1 保留行（C10）：
  `| 8 | 1 | — | — | — | — | 保留 |`
- 新增：
  `| 8 | 6 | timer cmp | cfx_hart_timer_cmp | 0 | RW | 64 位定时器比较值（绝对时间，单位同 cfx_time_value） |`
  `| 8 | 7 | timer ctrl | cfx_hart_timer_ctrl | 0 | RW | bit0=ENABLE，bit1=IMASK，bit2=ISTATUS（RO）；其余保留 |`
- 异常原因表新增：
  `| 1 << 10 | TIMER | 本地定时器比较匹配 | 可 | 全零 |`（**异步**，可屏蔽）
- 正文补：
  > `cfx_time_value >= cfx_hart_timer_cmp` 且 `ENABLE=1` 时置 `ISTATUS`；`IMASK=0` 时触发 TIMER 中断。写新的 `timer_cmp` 即清除本次条件；写全 1 关闭。

#### C5.3 SBI §10（`DADAO-22`）
- 标题：`## 10. 定时器/计数器（cfx_timer）` → `## 10. 全局时间（cfx_time）`。
- 正文：`cfx_time` 为 per-system 全局时间计数器。
- 服务表**只保留**：`| 0 | SBI_TIME_GET | — | rd8 = value | 返回全局时间计数值 |`。
- §10.1/§10.2 的 cfx_time 初始化与 handler **保留但裁剪**：只保留 CFXTRAP→`SBI_TIME_GET` 分支，删除 TIMER 分支与 `SBI_TIMER_SET_TIMER` 实现。
- §10.3 示例只保留 `SBI_TIME_GET`（`#define SBI_TIME_GET 0`）。

#### C5.4 SBI §7（`DADAO-22`）
- 正文：`cfx_hart` 提供 hart ID 与**每 hart 定时器比较器**。
- 服务表新增：`| 1 | SBI_HART_SET_TIMER | rd16 = timeout | — | 设置本 hart 的定时器比较值（绝对时间），到期触发 TIMER 中断 |`。
- 新增初始化 + handler 示例（从 §10 迁移并按 `cfx_hart` 改写）：
  - 向量：`cfx_hart_supv_excp_vector`；
  - 掩码：`cfx_smon_supv_global_cfx_mask` 清 `1<<15`（cfx_hart = cfx15）；
  - handler：`CFXTRAP(1<<0)` → `cfx_hart_trap_dispatch`（FID 0 = `SBI_HART_GET_ID`、FID 1 = `SBI_HART_SET_TIMER`）；`TIMER(1<<10)` → `cfx_hart_timer_int`；
  - `SBI_HART_SET_TIMER`：`cfx2rc cfx_hart_timer_cmp, rd16`；`set.rd rd2, 1` + `cfx2rc cfx_hart_timer_ctrl, rd2`（ENABLE=1、IMASK=0）。

#### C5.5 机械改名与示例
- `spec/Toolchain-01` 第 335 行示例 `cfx_timer_regs[0]` → **`cfx_ptw_ptbr[0]`**（现成数组，见 SEE §4.6）。
- `.tao/contracts/contract-asm.md` §13.8 同一示例同改。
- 全仓 grep：`spec/` 与 `.tao/contracts/` 中 `cfx_timer` 归零；HBI 中该行随 C7 删除。
- 改完运行 `python3 tools/spec/gen_cfx_aliases.py` 重算别名表（**禁止手工改**），再跑 `make check-cfx-aliases`。

#### C5.6 版本（Toolchain）
- `Toolchain-01` 版本 `0.5.3` → **`0.5.4-rc`**；册头「状态」行同步；文末附录新开 `### 0.5.4-rc（未发布）`，条目：示例随 `cfx_time` 改名改用 `cfx_ptw_ptbr[0]`。

### C6 — 同步异常不可屏蔽（`DADAO-12`）
- §4.10 `cfx_power` 异常表 `SOFT_RESET` 行：`可` → **`否`**。
- 正文步骤 5 补：
  > （同步异常均为不可屏蔽，步骤 2 已跳过；本步只对异步中断生效。）
- 伪代码第 5 步注释：
  `// 同步可屏蔽或异步：设置 pending` → `// 仅异步中断会到达此处（同步异常均不可屏蔽，步骤 2 已跳过）`。
- **门控**：新增 `tools/spec/check_sync_nonmaskable.py`（见「新增门控」）。

### C7 — HBI 启动与移交重写（`DADAO-23`）
把 §3 整节替换为下述内容（**保留**复位三条；**删除** `hypv_cg_reg_deleg` 列表、`cfx_power_excp_prev_*`、`escape cfx_power`）：

```
## 3. 启动与引导移交约定

硬件复位后：

1. 运行模式初始化为 hypv，`inner_cfx_code` 初始化为 cfx_power，`inner_cfx_mask` 初始化为全 1（当前运行掩码屏蔽所有核芯功能扩展；可通过 trap 或 escape 流程更新）
2. user/jail/supv 的 `global_cfx_mask` 初始化为全 1；hypv 的 `global_cfx_mask` 初始化为全 0（引导序列中 hypv 访问不受限）
3. `inner_inst_pointer` 跳转到 `cfx_power_hypv_excp_vector` 指示的地址（初始值为 `0xffff_ffff_0000`，为 DDR 未初始化前硬件可直接执行指令的一段地址空间）

hypv 引导代码完成最小初始化后，按以下流程将控制权**完全移交 smon**：

1. **逐 cfx 初始化**：对每个存在的 cfx（**hmon 除外**；hmon 由 hypv/HEE 保留），调用其 HBI 初始化函数：

   ```simrisc
   trap cfx_ptw, 0x30001           @@ 例：ptw 的 HBI 初始化；其它 cfx 同理换 cfxha
   ```

   - `HBI_<name>_INIT` 的 `immu18` 编码：bits[17:16] = `0b11`、bits[15:0] = `1`，即 `0x30001`。
   - 各 cfx 的 `hypv_excp_vector` 复位值应指向其 HBI 初始化入口（由该 cfx 的实现提供）。
   - 初始化内容至少包括：清除自身 `hypv_cg_reg_deleg`（允许 supv 访问 cg；cg3 固定禁止）、设置本 cfx 作为**源**时各模式可调用的目标：`<mode>_global_cfx_mask` 与 `<mode>_{trap,escape,cfx2rd,cfx2rc}_cfx_mask` 中允许的目标位（位 = 目标 cfx），以及 `<mode>_switch_run_mode`/`<mode>_switch_cfx_mask`/`<mode>_excp_vector`；其余由各 cfx 自行定义。
   - **引导期不会被掩码拦**：`trap` 查的是**源 cfx**（= power）的 `hypv_*_cfx_mask`，复位全 0；`inner_cfx_mask` 只影响异步中断（CFXTRAP 不可屏蔽，步骤 2 跳过）。
   - 除 smon 外，初始化完成后以 `escape cfx_<name>, [excp_cause_ip, 4]` 返回引导代码。

2. **移交 smon**：smon 的 HBI 初始化函数**不返回**引导代码，而是直接完成移交：

   ```simrisc
   @@ rb16 = S-mode 入口地址，rb17 = 设备树地址
   trap cfx_smon, 0x30001
   ```

   - smon 初始化完成后设置：`cfx_smon_supv_{global,trap,escape,cfx2rd,cfx2rc}_cfx_mask`（允许 supv 调用的目标；最简单 = 全 0）、`cfx_smon_excp_prev_run_mode = supv`、`cfx_smon_excp_prev_cfx_mask = 0`、`cfx_smon_excp_cause_ip = rb16`；
   - 执行 `escape cfx_smon, [excp_cause_ip, 0]` 跳转到 S-mode 入口，**不返回**引导代码；
   - 移交完成后：`inner_run_mode = supv`、`inner_cfx_code = smon`、`inner_cfx_mask = 0`。

S-mode 内核入口通过 `rb17` 获取设备树指针；`rb16` 为入口地址，移交后不再使用。
```

- 说明：`escape` 不恢复 `inner_cfx_code` 属**既定语义**（`inner_cfx_code` 保持当前 cfx = smon），无需新增硬件字段。
- **C9 并入**：新文本「hmon 除外」即原有意排除，不再逐行列 delegation。

### C8 — `cfxld/cfxst` 预留说明（`DADAO-12`）
- §3.8 顶部加：
  > **本组为预留设计**：`cfxld`/`cfxst` 当前**未启用**，未实现的机器对这两条指令 decode **ILLI**；§5.1/§5.2 中相关表述**待启用后生效**。
- §5.1 句「trap/escape/cfxld/cfxst/cfx2rd/cfx2rc 指令可以在任意运行模式下执行」后加「（`cfxld`/`cfxst` 当前未启用）」。
- §5.2 「cfxld/cfxst 访问 cfx 内部存储块…」句前加「（待启用）」。
- **不**引用 SimRISC-11。

### C9 — 已并入 C7（无需单独改）

### C10 — `cfx_hart` rc1 保留（已在 C5.2）

### C11 — `user_*` 的 smon 路径（`DADAO-12` 第 289 行）
- 保留「或」，在句后补：
  > 用户 `trap` 按 cfxha 路由：目标为 `cfx_smon` 时使用 `cfx_smon_user_*`（需清除 `user global cfx_mask` 对应位），目标为 `cfx_umon` 时使用 `cfx_umon_user_*`。非 trap 的 U-mode 异常固定进入 `cfx_umon`。

## 版本与记录（本次**发布**）

- **六册 DADAO**：发布当前版本号（**不升号**）——AEE/ABI **`0.9.3`**、SEE/SBI **`0.7.2`**、HEE/HBI **`0.1.3`**；日期 **2026-10-26**。
  - 册头：`> **版本：<ver>-rc**` → `> **版本：<ver>**`。
  - 文末顶部段：`### <ver>-rc（未发布）` → `### <ver>（2026-10-26）`。
  - **不预开**空的 `-rc` 段（后续有改动时再开 `<下一个 z>-rc`）。
  - **变更记录整理**（给人看）：
    - 按主题合并；同一对象的多次中间态只保留**最终态**，不写「返工/修正上一版」；
    - **不写任务号 / ADR 号**；
    - 顺序：对外可见的语义/接口变化在前，机械修正（引用/笔误/版本串）在后；
    - 已发布的历史段**不动**；
    - 本次六册的记录必须覆盖 C1–C11（按册分流，不跨册重复）。
- **版本常量**（发布时同步）：
  - `DADAO-12:274` `user_global_version`：`0x00090002` → **`0x00090003`**，「当前 0.9.2」→「当前 0.9.3」
  - `DADAO-12:320` `supv_global_version`：`0x00070001` → **`0x00070002`**，「当前 0.7.1」→「当前 0.7.2」
  - `DADAO-13:13` `hypv_global_version`：`0x00010002` → **`0x00010003`**，「当前 0.1.2」→「当前 0.1.3」
  - `DADAO-22:42/49/57`：`0.7.1 = 0x00070001` → **`0.7.2 = 0x00070002`**
  - `DADAO-23:19`：`0.1.2 = 0x00010002` → **`0.1.3 = 0x00010003`**
- **Toolchain-01**：已发布 `0.5.3`（2026-10-19）→ 按「再有改动 = 下一个 `z` + `-rc`」开 **`0.5.4-rc`**（册头「状态」行 + 文末附录新段 `### 0.5.4-rc（未发布）`），条目：示例随 `cfx_time` 改名改用 `cfx_ptw_ptbr[0]`。
- `manifests/spec-readonly.lock.toml`：文件头追加 2026-10-26（SPEC-175t）授权说明（用户逐条裁定 C1–C11 + 本次发布原话）；**重算** 7 个文件 sha256（DADAO-11/12/13/21/22/23 + Toolchain-01），其余不动。

## 新增门控 `check-sync-nonmaskable`（里程碑层）

- 脚本：`tools/spec/check_sync_nonmaskable.py`。
- 规则：扫描 `spec/DADAO-12/22/23` 的异常原因表；**只有**异步源（`IPI`、`TIMER`、`UART*`、占位行 `...`）允许「可」，其余任何 cause 行出现「可」即 **FAIL**（打印 file:line）。
- `--self-test`：在临时副本注入一条同步 cause=可 → 必须 FAIL；还原后 PASS。
- `Makefile`：`check-milestone` 依赖追加 `check-sync-nonmaskable`，并补 help 行。
- **不进 L1**（用户要求）。

## 验收标准

1. `make check`（L1）rc=0；`make check-milestone` rc=0（含新门控）。
2. `python3 tools/spec/gen_cfx_aliases.py` 后 `make check-cfx-aliases` rc=0。
3. 新门控可达 FAIL：贴「注入 → FAIL → 还原 → PASS」真实输出（禁止 `git checkout` 还原；用 `cp` + md5）。
4. 逐条核对（每条给出真实 grep/命令输出）：
   - C1：AEE 无「乘除法」段、无 `ext.so` 提示；
   - C2：`SBI_PTW_GET_PTBR`/`SBI_PMEM_GET_PM_START` 返回 `rb8`；PPN 仍 `rd8`；
   - C3：无「16 字节值除外」「高位块先入高寄存器」；
   - C4：§3.2.4 含「bank 独立」「全局从左到右顺序」「同一个连续栈区」；
   - C5：`spec/`+`.tao/contracts/` 中 `cfx_timer` 计数 = 0；`cfx_time_value`/`cfx_time_freq`/`cfx_hart_timer_cmp`/`cfx_hart_timer_ctrl` 在册；TIMER 行只在 `cfx_hart`；
   - C6：`SOFT_RESET` 行 = `否`；伪代码注释为「仅异步」；
   - C7：HBI §3 无 `cfx_power_excp_prev_cfx_mask`、无 `escape cfx_power`、无 12 行 delegation 列表；含 `0x30001`、「hmon 除外」、`rb17`；
   - C8：SEE §3.8 含「未启用…decode ILLI」；
   - C9：HBI §3 含「hmon 除外」；
   - C10：`cfx_hart` 含 `| 8 | 1 | — | — | — | — | 保留 |`；
   - C11：SEE:289 附近含「目标为 `cfx_smon` 时使用 `cfx_smon_user_*`」。
5. 版本：六册册头为 `0.9.3` / `0.7.2` / `0.1.3`（无 `-rc`），顶部段带 `2026-10-26`，**无空 `-rc` 段**；版本常量与发布号一致；Toolchain-01 为 `0.5.4-rc`；锁文件 7 个 sha256 已更新。
6. 完成区 ≤30 行，贴命令 + 退出码 + 关键输出；证据落 `.work/evidence/SPEC-175t/`。

## 完成区

**状态**：已验证

**测试结果**：证据脚本 76/76 PASS（rc=0）；新门控/`check-spec-readonly`/`check-cfx-aliases`/归档门控 rc=0；`make check-milestone` 仅本任务「待验收」交接窗口项红；`make -k check` 仅 `check-milestones-fresh` 红（architect 收尾）。

### 修改文件
- `spec/DADAO-11/12/13/21/22/23`：C1–C11 落点；发布号 AEE/ABI `0.9.3`、SEE/SBI `0.7.2`、HEE/HBI `0.1.3`（2026-10-26，无空 `-rc`）；变更记录按主题重排（语义在前/机械在后、只留最终态、无任务号）；版本常量同步。
- `spec/Toolchain-01`：状态行 + 附录新开 `### 0.5.4-rc（未发布）`；§13.8 示例改 `cfx_ptw_ptbr[0]`；`.tao/contracts/contract-asm.md` §13.8 同改；`.tao/contracts/contract-cfx-aliases.md`（生成器重算，未手改）。
- 工具与锁：`tools/spec/check_sync_nonmaskable.py`（新增，含 `--self-test`）、`Makefile`（目标 + `check-milestone` 依赖 + help + `.PHONY`）、`manifests/spec-readonly.lock.toml`（2026-10-26 授权说明含用户发布原话；7 册 sha256 重算）。
- **越界披露（为使 C5/门控自洽所必需，均最小改动）**：`tools/spec/check_asm_prose.py` `_CFX_NAMES` `timer`→`time`（否则 R3 假红）；`DADAO-12` §1 cfxha 表 `18 | timer`→`18 | time`（否则别名表仍生成 `cfx_timer`）；`DADAO-12` cg1 `jail_global_version` 同步 `0x00090003`（原文「与 user 版本号相同」）。

### 验收命令与结果
- `bash .work/evidence/SPEC-175t/run.sh` → **rc=0**：76 项全 PASS（C1–C11 + 版本/常量 + 锁 + 接线 + 注入自检）；日志 `.work/log/spec/SPEC-175t-*.log`。
- `python3 tools/spec/gen_cfx_aliases.py` rc=0（13 标量 / 36 专有 / 66 模板）→ `make check-cfx-aliases` rc=0；`check_sync_nonmaskable.py` rc=0（tables=10 rows=68 maskable_rows=7）、`--self-test` rc=0（注入 `SOFT_RESET` 可 → FAIL；还原/`TIMER`=可 → PASS）；`make -n check-milestone` 含新门控；归档结构/内容 sha/`check_milestone_tasks` rc=0；`make check-spec-readonly` rc=0。
- `make check-milestone` rc=2：唯一红项 = 本任务「待验收」被 `check_tasks.py --strict` 判「漏收尾」（交接窗口，`/complete` 后转绿）；其组成门控均绿。
- `make -k check` rc=2：**唯一红目标** `check-milestones-fresh`（`活任务册 SPEC-175t 未列入流水`），其余 L1 目标全绿（374 PASS 行）。
- 逐条核对（`run.sh` §1–§10 打印期望/实际）：C1 无 `**乘除法**` 段与 `重新扩展`；C2 `GET_PTBR`/`GET_PM_START`=`rb8`、`ALLOC_PAGE`=`rd8 = ppn`；C3 两式计数 0；C4 三句在册；C5 `cfx_timer`=0、TIMER 行仅 `cfx_hart`；C6 `SOFT_RESET=否`+「仅异步」；C7 无 `cfx_power_excp_prev_cfx_mask`/`escape cfx_power`、deleg 仅 1 处、含 `0x30001`/`rb17`；C8 三处措辞；C9/C10/C11 各 1 处。

### 新发现/坑
- `check_asm_prose.py` **硬编码** cfx 名单：改 cfxname 必须同笔同步，否则 `cfx2rd/2rc` 别名形 R3 假红。
- `cfx2rd`/`cfx2rc` 目的 bank **仅 RD**：返回 `rb8` 的示例必须 `set.rb` 中转。列表项内**缩进**的围栏不被 `extract_code_blocks` 扫描（行首 ``` 才识别）⇒ HBI §3 两段示例不在 asm 门控面内。
- `check-milestones-fresh` 以「活任务册 ⊆ 流水表」为断言：任务书一落地即红，属 architect 收尾职责（非实现缺陷）。

### 遗留
- L1 未全绿：仅 `check-milestones-fresh` 要求 `SPEC-175t` 进 `milestones.md` 流水（本任务书**禁改**该文件）⇒ architect 收尾补行后复跑。
- 六册附录 `> **发布动作**` 注记仍写「再于其上方新开空 `-rc` 段」，与本次「不预开」不符；**未改**（不在清单），建议后续统一为 SimRISC-00 措辞。
- `check-milestone` 报告当前里程碑 = M9（`milestones.md` 未更新，同属 architect 收尾）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行复审）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| C7 变更记录含字面 `escape cfx_power`，会与验收 grep 撞车 | ✅已修 | 改为「`excp_prev_cfx_mask` 置全 1 后经 `escape` 跳转」 | `run.sh` §7 `escape cfx_power` = 0 |
| C5 变更记录含 `cfx_timer`，破坏「归零」验收 | ✅已修 | 条目改为直接陈述 `cfx_time` 最终态 | `run.sh` §5 计数 0 |
| `cfx2rd` 目的 bank 仅 RD，`rb8` 返回示例不能直写 | ✅已修 | 表项 `cfx2rd … rd8` + `set.rb rb8, rd8`，并注「经 rd8 中转」 | `check-asm-prose` rc=0；`check-spec-codeblocks` rc=0 |
| 变更记录未按「语义在前/机械在后」 | ✅已修 | 六册附录逐册重排（SEE 拆 rc0/pending/FPEXCP 为接口/语义项；ABI 基线/标题/格式移至末段） | `check-spec-changelog` rc=0 |
| 新门控 `_is_separator` 为死代码；自检注入列号硬编码 | ✅已修 | 删死代码；注入前断言行形态（5 列 + 原值 `否` / 名称 `TIMER`） | `compileall` OK；`--self-test` rc=0 |
| `check_asm_prose.py` 硬编码 cfx 名单未随访 | ✅已修 | `timer`→`time`（越界披露） | `check-asm-prose` rc=0（改前 2 条 R3 假红） |
| 漏 `jail_global_version` 同步（原文「与 user 相同」） | ✅已修 | `0x00090002`→`0x00090003`（越界披露） | `run.sh` §10 断言 2 处 `0x00090003` |
| `make check` 全绿不可达（milestones 流水行属 architect） | ⏸延后 | 不动 `milestones.md`（任务书禁） | 已在完成区「遗留」登记 + run.sh 以「唯一红目标」判据取证 |


### architect 收尾修正（2026-10-26）
- 六册 + Toolchain 的「发布动作」注记统一为中央口径：「把顶部 `-rc` 段去 `-rc` 并补发布日期；`-rc` 段只在确有未发布改动时新开」，与 `SimRISC-00` / `spec/README` 一致（消除「发布后再预开空 `-rc`」的矛盾）。
- Toolchain 状态行改为「当前（0.5.4-rc，未发布；0.5.3 定稿于 2026-10-19…）」，避免把未发布 rc 写成「生效」。
- 上述 7 册 sha256 重算；`make check` rc=0；证据脚本 76/76 PASS（断言随最终文本同步）。
- `milestones.md` 流水行由 architect 收尾添加（任务书「约束」允许），engineer「遗留」中「禁改」措辞不再适用。

### 第 1 轮 reviewer 验收（2026-10-26）—— Accepted

**重跑记录（reviewer 独立执行，`workdir=仓库根`，退出码经 `cmd; echo $?` 实取）**
- `make check` → **rc=0**（L1 全绿，含 `check-milestones-fresh`——流水行已随本提交落地）。
- `python3 tools/spec/check_sync_nonmaskable.py` → rc=0（files=3 tables=10 rows=68 maskable_rows=7）；`--self-test` → rc=0（注入 SOFT_RESET→FAIL、还原→PASS、异步 TIMER=可→PASS，全 [OK]）。
- `python3 tools/spec/gen_cfx_aliases.py` → rc=0（13 scalar/36 specific/66 template，重算后 `git status` 该文件无 diff）→ `make check-cfx-aliases` → rc=0（byte-identical）。
- `make check-spec-readonly` → rc=0（21 册 OK）；另用 python 独立重算 sha256 对账：**7/7 MATCH**。
- `bash .work/evidence/SPEC-175t/run.sh` → **rc=0，76/76 PASS**（含内置注入反例与 `make check-milestone` 红项定界：唯一红 = 本任务「待验收」交接窗口，日志确认 `漏收尾: 1`）。
- **独立反例（非 SOFT_RESET，选 POWEROFF）**：`cp` 备份 md5=`a0ec5fe9…` → 注入 `DADAO-12:655 POWEROFF 否→可`（md5 变）→ 门控 **rc=1**，输出「`DADAO-12…:655: 同步异常原因 POWEROFF 被标为可屏蔽`」→ `cp` 还原，md5=`a0ec5fe9…` 与快照一致 → 门控 **rc=0** 回绿；`git status --porcelain -uall` 前后均 0 行。

**逐条核对**：C1（无乘除法段/无「重新扩展」，移位段保留）；C2（GET_PTBR/GET_PM_START=`rb8`，ALLOC_PAGE 仍 `rd8 = ppn`，§1 补返回值 bank 句，示例经 `set.rb rb8, rd8` 中转自洽）；C3（全 spec 两式计数 0，238/「16 字节值」节/HFA/HPA 未动）；C4（三句在册，contract-abi/ADR 未改）；C5（`cfx_timer` 计数 0；`cfx_time` cg10 rc7/ro8 与 SBI §10 `SBI_TIME_GET`/`cfx_time_value` 一一对应；TIMER 行仅 `cfx_hart`（DADAO-12:548）；§7 `SBI_HART_SET_TIMER` 用 `cfx_hart_timer_cmp/ctrl` 与 SEE 表一致；`cfx_time` 异常表无 TIMER、确无中断）；C6（SOFT_RESET=否；`excp_cause_nonmaskable` 为 HW 按异常表静态设置 ⇒ 表/寄存器/伪代码三者自洽，「仅异步可屏蔽」伪代码在 nonmaskable==0 护栏内）；C7（无 `cfx_power_excp_prev_cfx_mask`/`escape cfx_power`/12 行 deleg；「hmon 除外」「0x30001」「rb17」在册；源 cfx 掩码语义与 SEE §5.2 步骤 1/4 及 SBI 清 `cfx_smon_supv_global_cfx_mask(1<<15)` 用法一致；HEE cg3 rc1/6/7 复位全 0、`hypv_switch_run_mode`=3(hypv)、`hypv_excp_vector` 复位式与「复位值指向 HBI 初始化入口」自洽；rb16/rb17 前后一致）；C8 三处措辞；C9 并入 C7；C10 rc1 保留行；C11 补句照裁定原文。版本：六册册头 0.9.3/0.7.2/0.1.3 无 `-rc`、`### …（2026-10-26）`×6、无空 `-rc` 段、常量 0x00090003/0x00070002/0x00010003（无旧值残留）、Toolchain 0.5.4-rc；「发布动作」与 `spec/README:136`/`SimRISC-00:399` 逐字一致。锁文件：授权原话（含发布裁定）在文件头，7 sha256 现算 MATCH。变更记录：按主题合并、只留最终态、新段无任务号/ADR 号（awk 逐册扫描 0 命中）、语义在前机械在后、C1–C11 按册全覆盖、无自相矛盾。越界：`git show --stat` 16 文件均在允许清单内（`check_asm_prose.py timer→time`、DADAO-12 cfxha 表 18 改名、`jail_global_version` 同步已披露且为自洽必需）。

**非阻塞 finding（文档级，交 architect 收尾时顺手改）**：① 本节上方「architect 收尾修正」写「证据脚本 76/76 PASS」，reviewer 实跑为 **76/76**（完成区 76 与实测一致）；② 任务书 §遗留称「本任务书禁改 milestones.md」，与 §约束允许清单及本提交已加流水行相矛盾（结果正确、措辞待统一）；③ SEE §5.2 步骤 5 补句「步骤 2 已跳过」易误读为「跳过步骤 2」，实义为「已在步骤 2 判为不可屏蔽并跳过 3–5」——该句为任务书照录原文，语义本身正确。

**剩余风险**：HBI §3 列表内缩进围栏不被 `check-asm-prose` 扫描（engineer 已披露，属门控覆盖面既有行为）；`make check-milestone` 在 `/complete` 前恒红（交接窗口，非缺陷）。
