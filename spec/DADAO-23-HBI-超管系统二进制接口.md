# HBI（超管系统二进制接口）

> **版本：0.1.4-rc**（与 HEE 版本号一致，同步更新）

HBI 定义 H-mode（超管模式）核芯功能扩展提供的功能调用，供 S-mode 内核或其它核芯功能扩展请求需要 H-mode 权限的系统服务。

`trap cfxha, immu18` 中 cfxha 即为服务提供者，immu18 为功能编号。每个核芯功能扩展独立提供一组功能，按照实际需求进行调用。

## 1. 调用约定

与 SBI 调用约定一致（参见 SBI）。

## 2. 系统信息（cfx_hmon）

cfx_hmon 为 hypv 的 monitor，提供 HBI 版本查询和硬件信息。

| immu18 | 名称 | 入参 | 出参 | 说明 |
|--------|------|------|------|------|
| 0 | HBI_GET_VERSION | — | rd8 = version | 返回 HBI 版本号：`(major<<32)\|(minor<<16)\|patch`，当前 0.1.3 = `0x00010003` |

## 3. 启动与引导移交约定

硬件复位后：

1. 运行模式初始化为 hypv，`inner_cfx_code` 初始化为 cfx_power；异步中断统一进入 `cfx_hart`（cfxha 15），其捕获缓冲与 pending 汇总都在 `cfx_hart cg15`（见下条），**不再由任何 monitor 承担**，也不再初始化独立的 cfx 屏蔽层
2. 每个 cfx 的 `cfxtrap`/`cfxmem`/`cfxreg`/`cfxexe` 四类同步来源 mask 初始化为 `0xFFFF_FFFF_FFFF_FFF7`（hmon 自身 `0x7FFF_FFFF_FFFF_FFF7`，只允许 hmon/power）；`cfx0`–`cfx3` 的 `cg15 rc3`（`cfx_<monitor>_async_intr_mask`）初始化为全 1（位 = 源 cfxha，0=允许、1=屏蔽，软件按需清位放行；异步进入与返回语义见 SEE 册 §5.4）；源侧中断面 `cg16 rc16/17/18`（mask/pending/ack）复位为 mask 全 1、pending 0；`cg0`–`cg3` 的 `rc4` 不定义（保留）；`trap` 本身不改写该掩码（只把进入前值抄入目标 cfx `cg5 rc11`）；`escape` 按 `rc11` 整字恢复目标模式 monitor 的 `cg15 rc3`
3. `inner_inst_pointer` 跳转到 `cfx_power_hypv_excp_vector` 指示的地址（初始值为 `0xffff_ffff_0000`，为 DDR 未初始化前硬件可直接执行指令的一段地址空间）

hypv 引导代码完成最小初始化后，按以下流程将控制权**完全移交 smon**：

1. **逐 cfx 初始化**：对每个存在的 cfx（**hmon 除外**；hmon 由 hypv/HEE 保留），调用其 HBI 初始化函数：

   ```simrisc
   trap cfx_ptw, 0x30001           @@ 例：ptw 的 HBI 初始化；其它 cfx 同理换 cfxha
   ```

   - `HBI_<name>_INIT` 的 `immu18` 编码：bits[17:16] = `0b11`、bits[15:0] = `1`，即 `0x30001`。
   - 该编码**不落在 semihosting 区**（`0x3FF00–0x3FFFF`），按一般 trap 进入目标 cfx 向量。
   - 各 cfx 的 `hypv_excp_vector` 复位值应指向其 HBI 初始化入口（由该 cfx 的实现提供）。
   - 初始化内容至少包括：清除自身 `hypv_cg_reg_deleg`（允许 supv 访问 cg；cg3 固定禁止）、设置本 cfx 的 `<mode>_cfxtrap`/`_cfxmem`/`_cfxreg`/`_cfxexe` 来源 mask（位 = 源 cfx，0=允许、1=屏蔽），以及 `<mode>_switch_run_mode`/`<mode>_excp_vector`；其余由各 cfx 自行定义。
   - **引导期授权**：`trap` 查目标 cfx 的 `hypv_cfxtrap` 第「源 cfx（power=63）」位；目标需显式允许 power（hmon 默认允许，其余 cfx 默认只允许 hmon）。
   - 除 smon 外，初始化完成后以 `escape cfx_<name>` 返回引导代码；返回前把该 cfx 的 `cg5 rc10` 写为 `excp_cause_ip + 4`。

2. **移交 smon**：smon 的 HBI 初始化函数**不返回**引导代码，而是直接完成移交：

   ```simrisc
   @@ rb16 = S-mode 入口地址，rb17 = 设备树地址
   trap cfx_smon, 0x30001
   ```

   - smon 初始化完成后设置：`cfx_smon_supv_{global,trap,escape,cfx2rd,cfx2rc}_cfx_mask`（允许 supv 调用的目标；最简单 = 全 0）、`cfx_smon_excp_escape_run_mode = supv`、`cfx_smon_excp_escape_cfx_code = smon`、`cfx_smon_excp_escape_ip = rb16`、`cfx_smon_excp_escape_intr_mask = 全 1`（fail-safe；内核随后按需放行）；
   - 执行 `escape cfx_smon` 跳转到 S-mode 入口（`rc10 = rb16`），**不返回**引导代码；
   - 移交完成后：`inner_run_mode = supv`、`inner_cfx_code = smon`；异步中断的捕获缓冲与 pending 汇总始终在 `cfx_hart cg15`（与当前运行模式/当前 cfx 无关，移交不改变其归属），来源掩码按当前运行模式取 monitor 的 `cg15 rc3`；`escape` 按出口意图恢复运行模式/cfx/IP，并按 `cg5 rc11` 整字恢复目标模式 monitor 的 `cg15 rc3`；异步 handler 可用 `cfx_hart cg5 rc8`–`rc11` 出口意图 `escape cfx_hart` 返回被中断现场，也可走 smon/umon 正常路径。

S-mode 内核入口通过 `rb17` 获取设备树指针；`rb16` 为入口地址，移交后不再使用。

---

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期；`-rc` 段只在确有未发布改动时新开。

### 0.1.4-rc（未发布）

- 与 SEE 的异步模型修订同步（内容改，版本仍 `0.1.4-rc`）：异步来源掩码改在**当前运行模式 monitor** 的 `cg8 rc1`（`cfx_<monitor>_async_intr_mask`，位 = 源 cfxha、0=允许/1=屏蔽、复位全 1），`cfx_hart cg9` 只保留 pending 与现场；`cg0`–`cg3` 的 `rc4` 不定义（保留）；`trap`/`escape` 不再保存、恢复掩码。**HBI 功能码与调用约定不变**。

- §3 初始化约定改为两轴权限模型：四类同步来源 mask 初值 `0xFFFF_FFFF_FFFF_FFF7`（hmon `0x7FFF_FFFF_FFFF_FFF7`），`cfx_hart cg9` 的异步来源 mask 全 1；`trap` 由目标 cfx 的 `cfxtrap` 源位授权。
- §3 初始化与移交删除独立 cfx 屏蔽层（`inner_cfx_mask`/`switch_cfx_mask`/`excp_prev_cfx_mask`）：异步中断的来源掩码、pending 与现场统一在 `cfx_hart cg9`（`async_global_intr_mask` 与四个 `async_<mode>_intr_mask` 初值全 1），monitor 不再承担异步，`escape` 不再恢复屏蔽状态。
- §3 补充：`HBI_<name>_INIT`（`0x30001`）不落在 semihosting 区（`0x3FF00–0x3FFFF`），按一般 trap 进入目标 cfx 向量。

### 0.1.3（2026-10-26）

- 启动与引导移交改为「逐 cfx HBI 初始化 → 移交 smon」：以 `trap cfx_<name>, 0x30001`（`HBI_<name>_INIT`）逐 cfx 初始化（hmon 除外，由 hypv/HEE 保留）；各 cfx 初始化后 `escape` 回引导代码，smon 则直接 `escape` 进入 S-mode 入口、不返回。
- 删除原本由 `cfx_power` 承担的交接 trampoline（`excp_prev_cfx_mask` 置全 1 后经 `escape` 跳转）；移交由 smon 的 HBI 初始化完成，移交后 `inner_run_mode` = supv、`inner_cfx_code` = smon、`inner_cfx_mask` = 0。
- 引导期 `trap` 不受掩码阻挡：`trap` 查源 cfx（power）的 `hypv_*_cfx_mask`（复位全 0），`inner_cfx_mask` 只影响异步中断。
- 设备树指针改由 `rb17` 传递，`rb16` 为 S-mode 入口地址（移交后不再使用）。
- `global_cfx_mask` 由全 1 改为 hypv 例外全 0。
- 版本号常量同步：HBI 版本号 0.1.3。
- 汇编格式迁移新格式；术语 `cfxcode`→`cfxha`，寄存器名改 `cfx_<name>_<mode>`。
- 服务返回寄存器为 `rd8`。

### 0.1.2（上游基线；导入日 2026-07-14，发布日不详）

- 上游 DADAO 超管系统二进制接口（HBI）基线（基于 SimRISC 0.4.1）。
