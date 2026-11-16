# m14-qemu-006: `Kaiwu-Vast` 同步异常路由对齐 spec（删 staged 模型 + 修正编码了偏差的 oracle）

**模块**：qemu
**项目里程碑**：M14
**依赖**：`ISS-460`；`DADAO-12 §5.2`（步骤 1–7，MUST）；`m14-testcases-005`（在跑：其 ⑨a/⑫ 反例因本缺口 FAIL）**必须晚于本任务重跑**
**可并行分片**：否（qemu 组件单写者；且要盘点 `tests/arch` 的 oracle）
**预估**：4–6 h（含 28 个 oracle 逐个判定）
**档位**：大改（组件语义修正 + oracle 修正；复核 ≥4 路注入 + 独立重跑全部 arch/K 门控）
**状态**：待验收

## 背景（用户 2026-11-16 裁定「同意」：改实现，不把偏差写进规范）

`DADAO-12 §5.2` 的步骤 1–7 是规范正文：**执行期同步异常**（非仅页表类）→ 确定 cause 与目标（当前运行模式 monitor）→ **保存现场**（`excp_prev_run_mode` / `excp_cause_ip` / `excp_cause_id` / `excp_cause_info`）→ 切换 → **跳转至目标 cfx 的 `<mode>_excp_vector`**。`§7.1` 的退出码只规定"如何把结果编码给宿主"，**不授权绕过异常投递**。

现状（`target/dadao/`）：

- `cpu.c`：`dadao_profile_vast.sync_exc_monitor_entry = false`（注释自称 staged direct-fault mapping）；Tiny 为 `true`；
- `helper.c`：该标志为 false 时，非 PTW、非 `CFXPERM` 的同步异常走 `dadao_excp_to_exit_code()` + `qemu_system_shutdown_request_with_code(..., GUEST_PANIC, code)` ⇒ **guest 收不到异常、无帧、仿真结束**；
- 后果（可观察语义差异，不是实现自由度）：同一段 guest 代码 Tiny/Vast 行为不同；K3 的内核 fault handler 在 Vast 上拿不到帧；`m14-testcases-005` 的 ⑨a（`ptw_enable=0`）与 ⑫（保留 cfx）反例只能看到 `0xF1`。

## 目标

1. **两 profile 统一进 monitor**：`dadao_profile_vast.sync_exc_monitor_entry = true`；**删除 `helper.c` 的 staged 分支**（`dadao_excp_to_exit_code` + shutdown 那条路），统一走 `dadao_sync_enter()`；
   - `CFXPERM` 的 `cfx_perm_info`（`cause_info`）必须**保留传递**（统一后不得丢失）；
   - 保持"已在关停流程中就不再进 monitor/覆盖退出码"的既有短路。
2. **盘点并修正 oracle**：`git grep '0xF1|0xE1|0xD1|monitor 段'` 现行命中 **28 个文件**（`tests/arch` 与 `tools/testcases/arch` 为主）。逐个判定：
   - **Tiny 相关**（hmon 已进 monitor）⇒ **不动**，写清理由；
   - **Vast 相关且编码了 staged 行为** ⇒ 改为**按 spec 的帧级期望**：`cause_id`（含 `cause_info` 语义）、`excp_cause_ip`、`excp_prev_run_mode`，以及"handler 收到帧后如何 `escape`（0/+4）"；
   - 每个改动必须写「**原期望 → 新期望 + 依据（`DADAO-12 §5.2` 步骤 N）**」；
   - **不得**因为"实现改了"而放宽断言；改的是**错误期望**。
3. **回归**：K0/K1/K2 与 arch 门控必须回绿（Vast 是 K1/K2 的平台）。

## 验收（真实 rc + 输出）

1. **代码证据**：`cpu.c` 两 profile 均 `sync_exc_monitor_entry = true`；`helper.c` 里 `dadao_excp_to_exit_code` + `qemu_system_shutdown_request_with_code` 的那条 staged 路径**已删**（贴 diff/grep）；
2. **先红后绿**：改前用一条 Vast 探针证明"无帧、直接 `0xF1` 退出"（贴真实输出）；改后**同一条**看到 monitor 帧（`cause_id`/`cause_ip`/`cause_info`/`prev_mode` 四项逐个打印并核对）；
3. **28 文件判定表**：逐文件给「Tiny/Vast / 改或不改 / 理由 / 原期望→新期望」；
4. **门控全绿**：`check-linux-k0` 119/119、`check-linux-k1` 108/108、`check-linux-k2` 104/104、`k2_trap_probe` 85/85、`k2_time_probe` 151/151、`k2_irq_probe` 97/97、`check-arch`、`check-arch-smoke`、`check-inst-asm` **904/904**、`check-qemu-forms`；
5. **≥4 路注入**（`cp`+md5 还原 + 重建）：① 把 Vast 的 flag 改回 `false` ⇒ 改过的 oracle/探针红；② 丢掉 `CFXPERM` 的 `cfx_perm_info` 传递 ⇒ 该条红；③ 把 `excp_prev_run_mode` 写入改成常量 ⇒ 红；④ 某个改过的 oracle 新期望写错一位 ⇒ 红；
6. 补丁纪律：`apply_series --component qemu`、`make_patch qemu` 幂等、`check-source-state`、`check-patch-tree`（qemu 0 problem）、`check-component-changelog`；
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **语义以 spec 为准**：只把实现改到 spec，不改 spec/契约（若发现 spec 真有空白，停下报告，不自行扩写）；
- `cause_id` 子原因编码（`ADR-0056`）不在本任务范围（归 `m14-qemu-005`，本任务只需让**帧可达**）；
- 只动 `components/qemu/**`、`tools/testcases/arch/**`、`tests/arch/**`（oracle 与探针期望）+ 本任务书；不动 `spec/`、`contracts/`、`components/linux`；
- 不提交 git；注入还原 `cp`+md5；构建与跑批不同时；`JOBS=32`；脚本按 `git rev-parse --show-toplevel` 推根（`ISS-456`）。

## 28 文件判定表

口径：`git grep -lE '0xF1|0xE1|0xD1|monitor 段' -- tests tools` 现场命中 28 文件。「Tiny 相关」= 该载体/门控跑 `kaiwu-tiny`（含 `tests/inst` 的 Tiny 固件），本改动对 Tiny **逐位不变**（`sync_exc_monitor_entry` 原本即 `true`；staged 分支对 Tiny 是不可达代码），故一律**不动**，只写理由。

| 文件 | 归属 | 判定 | 理由 |
| --- | --- | --- | --- |
| tests/inst/00-isa-design/atomic_rmw.S | Tiny(inst) | 不动 | 0xF123… 是数据常量 |
| tests/inst/00-isa-design/undi_reserved.S | Tiny(inst) | 不动 | 注释：UNDI=0xF9 由 Tiny 固件 hmon 按 cause 出码 |
| tests/inst/06-control-flow/ret_riii_ra.S | Tiny(inst) | 不动 | 注释：CFXMEM=0xF1 同上 |
| tests/inst/10-arith-logic-byte/mul.sb_orrr_rd.S | Tiny(inst) | 不动 | 0xE1 是算术值 |
| tests/inst/10-arith-logic-byte/mul.ub_orrr_rd.S | Tiny(inst) | 不动 | 同上 |
| tests/inst/11-cfx/trap_ciii_cfx.S | Tiny(inst) | 不动 | 0xF10 是地址偏移 |
| tests/inst/{MIGRATION.md,README.md,inventory.md} | Tiny(inst) | 不动 | 文档记录的 Tiny 出码口径 |
| tests/inst/macros/inst_test.inc | Tiny(inst) | 不动 | `__code 0xF1` 宏：Tiny 出码表 |
| tools/infra/check_interface_alignment.py | 门控 | 不动 | 只断言 patch 里有 §7.1 出码公式（`check-interface` PASS） |
| tools/linux/check_k2.py | Vast(K2) | 不动 | 断言的是**内核自报**预测码（guest 侧派生，非 QEMU staged）；K2 全绿 |
| tools/linux/k2_trap_probe.py | Vast(K2) | 不动 | 同上；85/85 PASS |
| tools/linux/semihost_pa_probe.S | Vast | 不动 | 0xE1 是 payload 错误码 |
| tools/testcases/arch/min_rom_probe_{006t,010t,030t,integ038t}.py | Tiny | 不动 | 载体为 `-M kaiwu-tiny`；0xF1/0xF8/0xF9/0xFC 由 Tiny 固件 hmon 出码 |
| tools/testcases/arch/min_rom_probe_034t.py | Vast/Tiny | 不动 | 0xF1F2… 是数据常量 |
| tools/testcases/arch/min_rom_probe_integ051t.py | Vast | 不动 | 0xF1…0xF9 是 guest 自检失败码（`need_eq` 的 FAIL 值） |
| tools/testcases/inst/run_asm_suite.py | Tiny(inst) | 不动 | 断言表 = Tiny 出码 |
| tools/testcases/lib/build_test_binary.py | Tiny(inst) | 不动 | Tiny 故障宏 |
| tools/testcases/oracle_clmul.py | 无关 | 不动 | `0xE1 << 120` 是 GCM 常量 |
| tools/testcases/validate_vectors.py | Tiny(inst) | 不动 | 注释 |

**合计：28 = 24 不改 + 4 改命中**（`049t`/`integ039t`/`integ040t`/`integ042t`）；另 `integ048t` 在 grep 之外、由门控实测发现 ⇒ 共 **5 文件 6 处 case**。

**改（6 处 case，5 个文件；其中 `integ048t` 是 grep 之外由门控实测发现的）**

- `min_rom_probe_049t.py`：`old_ram_unmapped` / `legacy_ram_gone` / `oob_data_cfxmem` / `oob_data_unmapped` / `oob_fetch_cfxmem` / `oob_fetch_unmapped`
  - 原：`{"exit": 0xF1}`（monitor 段机器 fault 码，无帧）
  - 新：`{exit 0, prev_mode=3(hypv), cause_id=1<<1(CFXMEM), cause_ip=触发指令地址, cause_info=访存/取指地址}`，逐例断言四个字段（`frame_expect`）
  - 依据：`DADAO-12 §5.2` 步骤 1（CFXMEM 目标 = 当前模式 monitor）、步骤 5（`excp_prev_run_mode`/`cause_id`/`cause_ip`/`cause_info`）、步骤 7（跳 `<mode>_excp_vector`）；取指例的 `cause_ip` = 非法 IP（§5.2 步骤 5「触发指令地址」+ §5「IP 停留」），故 `cause_ip == cause_info == 取指地址`
- `min_rom_probe_integ039t.py`：`ptw_off_still_cfxmem` 原 `{exit 0xF1}` → `fault_expect(CFXMEM, va=0x1000, ip=fault_at)`（`rd10/11/12` + `syncn3`/`cid3`），依据同上
- `min_rom_probe_integ040t.py`：`tlb_bypass_ptw_off` 原 `{exit 0xF1}` → `{exit 0, rd10=CFXMEM, rd11=VA, rd12=ip, syncn3=1, cid3=CFXMEM}`
- `min_rom_probe_integ042t.py`：`sram_oob_cfxmem` / `sram_old_offset_cfxmem` / `cfx6_reserved_cfxmem` 原 `{exit 0xF1}` → `{exit 0, rd10=CFXMEM, rd11=故障地址, rd12=ip}`（新增 `HMON_FRAME_HANDLER`）
- `min_rom_probe_integ048t.py`（**grep 未命中**：它编码的是 `0xE8` = supv+ILLI 的 staged 码）：`power_bootrom_store` 原 `{exit 0xE8}` → `{exit 0x2E, cid:2=ILLI(1<<8), cinfo:2=该 st.o 的指令编码, cip:2=st.o 地址, prevm:2=SUPV(2), syncn:2=1}`。`cinfo` 期望值由 `contracts/opcodes.yaml`（`st.o_rrii_rd`：opc `0x21`、`rdha[23:18]=rd20`、`rbhb[17:12]=rb4`、`imms12=0`）+ 探针编码器派生 = **`0x21504000`**，**不读实现输出反填**；依据 `DADAO-12 §4.1` / `Kaiwu §4.4`「`ILLI` 的 `cause_info` = 指令编码」

**不改的三处「已进 monitor」既存 oracle（核对后确认无需改）**：`integ040t/ptwerr_monitor_cfxmem_exit`（向量**不可达** ⇒ 仍按 `Kaiwu §7.1` 出 `0xF1`，是保留的兜底语义）；`integ042t/{cfx5_cache_cfxreg,pmem_cg15_reserved_cfxreg}`（`cfx2rd/cfx2rc` 的 `CFXREG` 走 `cfx_raise` 分支，本就不受 staged 影响）。

## 完成区

**测试结果**：一键证据脚本 PASS（**83 项检查 / 0 失败**）= A 代码证据 11 + B 先红后绿 10 + C 帧级 10 + D 五路注入 18 + E 补丁纪律 10 + F 门控 16；门控真数见下。
**修改文件**：`components/qemu/patches/target/dadao/{cpu.c,cpu.h,helper.c}.patch`、`components/qemu/changelog.md`、`tools/testcases/arch/min_rom_probe_{049t,integ039t,integ040t,integ042t,integ048t}.py`、本任务书；证据脚本与日志在运行期证据目录（未归档）。
**验收结果**：
- 代码：两 profile 均 `sync_exc_monitor_entry = true`；staged 三条（exit-code+shutdown 路、CFXPERM 的 `cfx_raise` 旁路）已删，统一 `dadao_sync_enter()`；CFXPERM 的 `cause_info = cfx_perm_info`、关停中短路、向量不可达兜底均保留。**`ILLI` 的 `cause_info`（`DADAO-12 §4.1`）= 指令编码**：只读 ROM 存储分支（`tlb_fill`）看不到指令 ⇒ 贴 `DADAO_INFO_UNSET` 哨兵，`dadao_sync_cause` 从**触发指令地址**回读 4 字节（核心内段恒等 / monitor SRAM host 区 / 内存窗口用取指建好的 TLB 条目；`address_space_ldl_be` 直读 PA、不经 MMU 不递归），读不到 ⇒ `error_report`+`exit(1)`，绝不静默 0。
- 先红后绿（同一 `049t/old_ram_unmapped`）：钉死基线 `bc1a15da` 补丁集重建 ⇒ `exit exp=0x0 got=0xf1`、`rd11 exp=0x2 got=0x0`（无帧、直落 0xF1）；恢复后 ⇒ `frame prev_mode=3 cause_id=0x2 cause_ip=0xffffffff1020 cause_info=0xffff00001000`。
- `integ048t/power_bootrom_store` 帧实测：`PREVM:0x2 CID:0x100 CIP:0xffffffff120c CINFO:0x21504000`（`CINFO` = 该 `st.o rd20,[rb4,0]` 的编码，由 `contracts/opcodes.yaml` + 探针编码器派生，非反填）。
- 五路注入（`cp`+md5 还原 + 重建，均红→回绿）：①Vast flag=false ⇒ `exit exp=0x0 got=0x1`；②丢 CFXPERM `cfx_perm_info` ⇒ `cinfo:2 exp=0xfffffffe0000 got=0x0`；③`prev_run_mode` 常量 HYPV ⇒ `prevm:2 exp=0x2 got=0x3`；④oracle 期望错一位 ⇒ `rd11 exp=0x12 got=0x2`；⑤ROM 存储分支的 cause_info 哨兵改回 0 ⇒ `cinfo:2 exp=0x21504000 got=0x0`。
- 门控：`check-arch` PASS（14 探针全绿）、`check-arch-smoke` PASS（10/10 + 25 服务）、`check-inst-asm` **904/904**、`check-linux-k1` **108/108**、`check-linux-k2` **102/104**（B/E/T/M/S/X 六组全绿，2 红为 K0 回归项）、`k2_trap`/`k2_time`/`k2_irq` = **85/85 / 151/151 / 97/97**、`check-qemu-forms`+`check-interface`+`check-component-changelog` PASS。
- 补丁纪律：`make_patch qemu` 幂等（重导出 1 written → 再跑 0 written，md5 稳定）、`apply_series --component qemu` rc=0 且 HEAD 不变、`check-source-state` qemu clean、`check-patch-tree` qemu 断言 **0** 问题。
- `check-linux-k0` **116/119**：3 红全为 `K12 apply-series --component linux`（`components/linux` 补丁集落后其源码树本地提交，并发 linux 任务所致，非本改动）；`check-linux-k2` 的 R1/R2 由它派生。
**新发现/坑**：①按 `0xF1|0xE1|0xD1` 盘点 staged 出码会漏别的段码（`0xE8`=supv+ILLI），须以门控实测补齐（由此发现 `integ048t`）；②`ILLI` 的 `cause_info` 在「只读 ROM 存储」raise 点不可得 —— 以「哨兵 + 从触发 IP 回读」补齐，且回读失败必须停下报告（`sync_fault_info=0` 之类的静默值就是实现缺口）；③探针在 `ptw_enable=0` 场景改由 monitor 处理器经 SYS_EXIT 报告时**必须先复原 `ptw_enable`**，否则参数块存储自身 CFXMEM（初版 6 例全 TIMEOUT 的根因）；④取指类 CFXMEM 的 `cause_ip` = 非法取指地址（§5.2 步 5／「IP 停留」），处理器不能 `escape +4` 续跑；⑤Vast 上未装 monitor 处理器的探针会重入 prelude 的 hmon 初始化段（无限重启）——改 oracle 须同时装处理器；⑥共享内核构建树被并发任务占用时 `k2_*` 探针 defconfig/build 假红（`config slice rc=1`），重试 1 次即可。
**遗留问题**：①非门控遗留探针（`min_rom_probe_{005t,006t,008t…074t}`、`integ038t`）不在 28 文件盘点内且在本任务前已不可跑（Tiny `-bios` 收紧、整机改名均早于本任务），其 `0xF8/0xF9/0xF1` 期望未复核 ⇒ 建议并入「探针退役/重建」任务；②本任务改动的 `CFXMEM` 帧断言按 `cause_id == 1<<1` **全宽**比较（无 wyde3 子原因位），`m14-qemu-005` 一旦填子原因位这些断言必红 —— 属 **qemu-005 的连带修正**（已在其任务书登记），本任务范围不含子原因编码，故不改这些期望；③`check-linux-k0` K12 与 `check-patch-tree` 的 26 条 linux 断言红为外部（`components/linux` 补丁集落后），须由 linux 任务侧收口；④安装根现为本改动构建的可执行文件（与交付补丁集一致），合入后按常规重建。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`cpu.c`/`cpu.h`/`helper.c` 三处补丁 diff、5 个探针的完整改动、证据脚本；对照 `spec/DADAO-12 §2.2/§5.2(一)(二)(三)/§5.3`、`spec/Kaiwu §7.1`、`ADR-0004 D5.6`、`ADR-0045 D6`。

逐行结论：`dadao_cpu_do_interrupt` 的入口顺序（semihosting → PTW_FAULT → 关停短路 → 统一 sync 入口）与 §5.2 步骤 1/2 一致；同步异常不可屏蔽（不查掩码）；`dadao_sync_cause` 的 9 类 cause/info 逐条对 `§5.2(二)` 与 `§3.6`；`cfx_enter` 步骤 4→5→6→7 未被改动；Tiny 路径逐位等价（`sync_exc_monitor_entry` 原本 true，被删的 staged 分支对 Tiny 不可达）。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 删 staged 后若 profile 置 false 会静默丢帧（无第二路由） | ✅已修 | 入口改为 `if (!flag) { error_report + exit(1) }`，显式失败而非兼容桩 | 注入①：`exit exp=0x0 got=0x1` 红；探针 49t 回绿 |
| F2 `049t` 初版把 handler 读帧的 4 个值写进 rd10-13，与用例 scratch 冲突（rd6 被 `reptw` 占用等） | ✅已修 | handler 只用 rd6/rd10-13，用例 scratch 限 rd3/rd4/rd6/rd16/rb2/rb3/rb16，逐例核对不重叠 | C 组 4 例 frame 与期望逐字节相等 |
| F3 `ptw_enable=0` 用例的 monitor 处理器用 SYS_EXIT 报告会自身 CFXMEM（参数块存储走内存窗口） | ✅已修 | `monitor_words(reptw=True)` / `monitor_handler_dict(reptw=True)`：先复原 `ptw_enable=1` 再读帧退出 | 6 例由 TIMEOUT 转 PASS（`049t` 9/9、`integ039t/040t` 全绿） |
| F4 未给探针装 monitor 处理器时，Vast 故障会重入 prelude 的 hmon 初始化段（无限重启） | ✅已修 | `049t` 新增 `setup_monitor`+`MONITOR`；`integ042t` 新增 `HMON_FRAME_HANDLER`；`integ039t/040t` 复用既有 handler 字典 | `check-arch` 14 探针 PASS |
| F5 `integ048t/power_bootrom_store` 若只断言 cause，无法覆盖 `prev_run_mode`（该例是 supv 帧，与 049t 的 hypv 帧互补） | ✅已修 | `observe()` 增 `prevm` 解析；该例加 `prevm:2 = SUPV` 与 `syncn:2 = 1` | 注入③（常量 HYPV）⇒ `prevm:2 exp=0x2 got=0x3` 红 |
| F6 `dadao_excp_to_exit_code()` 是否可随 staged 一起删 | ❌不修 | 保留：`dadao_sync_enter` 在**向量不可达**时仍按 `Kaiwu §7.1` 出 monitor 段机器 fault（`integ040t/ptwerr_monitor_cfxmem_exit` 覆盖该兜底） | 该例仍 PASS；`grep -c qemu_system_shutdown_request_with_code` = 1（仅此兜底） |
| F7 遗留探针（非门控、`0xF8/0xF9`）的期望未复核 | ⏸延后 | 不在 28 文件盘点内，且本任务前已不可跑（Tiny `-bios` 收紧/整机改名早于本任务）；批量改不可复核 | 见完成区遗留① |
| F8（第 2 轮，reviewer 阻断）`integ048t/power_bootrom_store` 断言 `cinfo:2 = 0`，把实现缺口写进 oracle：`ILLI` 的 `cause_info` 按 `DADAO-12 §4.1`/`Kaiwu §4.4` 必须是**指令编码**，而 `tlb_fill` 的只读 ROM 存储分支看不到指令、静默写 0 | ✅已修 | ①该分支改贴 `DADAO_INFO_UNSET` 哨兵（全 1，32 位编码不可能取到）；②`dadao_sync_cause` 的 `ILLI` 分支遇哨兵即 `dadao_insn_word()` 从**触发指令地址**回读 4 字节（核心内段恒等 / monitor SRAM host 区 / 内存窗口用取指建好的 TLB 条目；`address_space_ldl_be` 直读 PA，不经 MMU 不递归），读不到 ⇒ `error_report`+`exit(1)`，绝不静默 0；③oracle 改为期望该 `st.o` 的编码 `0x21504000`（由 `contracts/opcodes.yaml` + 探针编码器派生） | 帧实测 `CINFO:0000000021504000`（`CID:0x100`、`CIP:0xffffffff120c`、`PREVM:0x2`）；新增注入⑤（哨兵改 0）⇒ `cinfo:2 exp=0x21504000 got=0x0` 红，`cp`+md5 还原回绿 |

判决：F1–F5、F8 已修并复验（证据脚本全绿），F6 结论有 spec 依据，F7 登记遗留；状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-16）

**重跑（全部自采，不采信转述）**：运行期证据脚本全量 ⇒ `RESULT: PASS (76 checks)`（含 B 组先红后绿：基线 `bc1a15da` ⇒ `exit exp=0x0 got=0xf1` + `rd11 exp=0x2 got=0x0`、恢复 rc=0；D 组四路注入全红、md5 还原）；另直采 rc：`make check-arch=0`（14 探针）、`check-arch-smoke=0`、`check-inst-asm=0`（904/904）、`check-linux-k1=0`（108/108）、`check-linux-k0=2`（116/119，6 条 FAIL 全为 K12 `apply-series --component linux`）、`check-linux-k2=2`（102/104，仅 R1/R2 = K0 回归项）、`check-qemu-forms`/`check-interface`/`check-component-changelog=0`、`check-patch-tree` qemu 断言 **0**（linux 26 条为外因）、`--source-state` qemu clean、`make_patch` 0 written 且 md5 不变、`k2_trap/time/irq = 85/85、151/151、97/97`。
**单路由核**：`dadao_excp_to_exit_code` 仅剩 **1 个**调用点（`helper.c` 的 `dadao_sync_enter`「向量不可达/未进入」兜底，`Kaiwu §7.1` 机器 fault，由 `integ040t/ptwerr_monitor_cfxmem_exit` 覆盖）；`target/dadao` 内 `qemu_system_shutdown_request_with_code` 仅 1 处（同处）；staged 三条为真删（非 `if (0)`）；`cfx_raise*`（17+5 处）只写帧跳向量、不写退出码；profile=false ⇒ 具名 `error_report` + `exit(1)`，无第二条把同步异常映射成退出码的路径。
**帧三项自跑**：数据 `CFXMEM` = `prev_mode=3 / cause_id=0x2 / cause_ip=触发指令 / cause_info=访存地址`；取指 `CFXMEM` = `cause_ip = cause_info = 0x1000000`（§5 IP 停留）；`CFXPERM`（`integ048t/closed_power_bootrom`）= `cid=1<<7、cinfo=访存地址、cip=触发指令`，且丢 `cfx_perm_info` 注入必红 ⇒ 传递仍在。
**oracle 复推**：`049t` 6 例、`integ042t` 3 例按 `§5.2(一)(二)` + 步骤 5 逐字段推出、与 oracle 一致；`integ048t/power_bootrom_store` 的 `prevm=2 / cid=1<<8 / cip=st.o 地址 / syncn=1` 可推出，**`cinfo:2 = 0` 推不出**（`DADAO-12 §4.1`、`Kaiwu §4.4` 均写 `ILLI` 的 `info = 指令编码`）。
**「不改」4 抽**：`006t`/`030t`/`integ038t` 载体为 `-M kaiwu-tiny`（Tiny 逐位不变）；`integ051t` 的 `0xF1/0xD1` = guest `need_eq` 自检失败码；`check_k2`/`k2_trap` 的 `0xE1` = 内核 `head.S:FAIL_X` 自报码（K2 实测绿）；`tests/inst` 的 `0xF1/0xF8` = Tiny 固件出码宏（`check-inst-asm 904/904`）。
**5 路自设计注入（cp+md5+重建）**：① `prev_run_mode` 改读切换后 `inner_run_mode` ⇒ `prevm:2 exp=0x2 got=0x3`；② 关掉向量可达兜底 ⇒ `ptwerr_monitor_cfxmem_exit TIMEOUT`；③ `CFXMEM cause_info ← cause_ip` ⇒ `rd13 exp=0xffff00001000 got=0xffffffff1020`；④ `target` 写死 0 ⇒ 帧四项全 0；④b `mode[entry_mode] → mode[0]` ⇒ `exit exp=0x0 got=0xf1`；全部还原（md5 与注入前相同）+ 重建后 5 个金丝雀 rc=0 回绿。
**越界/快照**：`git diff --name-only bc1a15da..4d50bbb4` = 10 文件（3 补丁 + changelog + 5 探针 + 本任务书），`components/linux`、`tests/inst`、`spec`、`contracts`、`.tao/knowledge` = **0 改动**；验收前后 `git status -uall` 空、HEAD `4d50bbb4`、12 个目标文件 md5 前后逐项相同（`cp`+md5，未用 checkout/restore）。
**判决：Needs Revision** — 阻断项（语义/spec 不一致）：`tools/testcases/arch/min_rom_probe_integ048t.py` 的 `power_bootrom_store` 断言 `"cinfo:2": 0`，spec 规定 `ILLI cause_info = 指令编码`，0 只能来自实现 ⇒ 与本任务「把实现改到 spec、不把偏差写进期望」相违（复推第 3 项判据）。改法：`dadao_sync_cause` 对 `DADAO_EXCP_ILLI` 在 `sync_fault_info == 0` 时按已恢复的 `env->pc` 取指令编码（或由 raise 点携带），oracle 改期望该编码；若判定确实不可得，按硬约束停下报告，不得以 0 收口。其余各项（单路由、帧可达、门控真数、补丁纪律、越界、注入）均达标。
**非阻断 finding**：① 交付摘要「22 文件判定不改」与判定表实数 **24** 不符（28 = 24 不改 + 4 改命中；改 5 文件 6 例，`integ048t` 在 grep 之外）——数字笔误，收尾改；② 5 个 `CFXMEM` oracle 断言 `cause_id` 全宽 = `1<<1`（无 wyde3 子原因），任务书已划归 `m14-qemu-005`，但该任务书未提这些探针 ⇒ 跨任务耦合未登记；③ `run.sh` 的 `k2_*`「BLOCKED 不计 FAIL」分支可达（本轮三探针实测 PASS，未触发）；④ K0/K2 红项为外因（共享 linux 源树被并发任务提交、`components/linux` 补丁集落后），须 linux 侧收口后复跑。

### 第 2 轮 reviewer 验收（2026-11-16，产出 `ac90f857`）

**重跑（自采）**：证据脚本全量 ⇒ `RESULT: PASS (83 checks)`、`RUNSH_RC=0`（首次尝试在 `make install-host` 处被外力 `Terminated`、源树一度停在基线 ⇒ 用 `cp` 从证据备份还原（md5 与补丁派生内容一致）后 `setsid` 重跑；记环境干扰 **1/3**，非交付物缺陷）；A10/A11、B 先红后绿、C 帧级、D 五路注入全红均复现。
**`dadao_insn_word` 可靠性四项**：① 地址规则与取指同源 —— `cfxha` = bits[47:42]（`>>42 & 0x3f`，不受高位影响）、48 位掩码后分段判定与 `tlb_fill` 同序同边界；内存窗口 `e->pa | (va & ((1<<size_log2)-1))` 与 `tlb_fill` 的 `DADAO_SIZE_MASK` 同宏；pmem/hmon/smon SRAM 同 offset + 同 host 基址；RAM/ROM 恒等。② 不递归 —— `dadao_tlb_lookup` 是纯数组扫描（不回填、不调 `tlb_fill`），`address_space_ldl_be` 对 PA 直读、不经 MMU；读不到 ⇒ `error_report` + `exit(1)`（A11=1，绝不静默 0）。③ `env->pc` 即触发指令地址 —— `dadao_sync_cause` 读的与随后传给 `cfx_enter` 当 `cause_ip` 的是同一变量、其间无写；同例 `cip:2` 断言 = `st.o` 地址、`cinfo:2` = 该地址上的字，交叉一致；注入②（+4）取到 `st.o` 的**下一词**进一步坐实。④ 端序/哨兵 —— 取指 `translator_ldl_end(..., MO_BE)`、回读 `address_space_ldl_be`、镜像 `pack(">I")` 三者同为大端（既有 `CFXREG` 类 `cinfo` = 探针编码器值通过，即证 `ctx->opcode` 同序）；`DADAO_INFO_UNSET = ~0` 与 32 位零扩展的指令编码不可能碰撞，且 `ILLI` 仅两个 raise 点（`translate.c` 传 `ctx->opcode`、只读 ROM 存储贴哨兵）。
**oracle 独立派生**：按 `contracts/opcodes.yaml` `st.o_rrii_rd`（opc `0x21`、`rdha[23:18]=20`、`rbhb[17:12]=4`、`imms12=0`）算 `(0x21<<24)|(20<<18)|(4<<12)` = **`0x21504000`**，与 oracle 期望一致（未读实现输出反填）。
**3 路注入（`cp`+md5+重建）**：① 哨兵改回 `0` ⇒ `cinfo:2 exp=0x21504000 got=0x0` 红；② 回读地址 `env->pc + 4` ⇒ `got=0x70000001` 红（= 该例 `st.o` 后一词 `jump [rb0,1]`，独立预测命中 ⇒ 证明按触发指令地址读且为大端）；③ `address_space_ldl_be → ldl_le` ⇒ `got=0x405021` 红（= `bswap(0x21504000)`，独立预测命中）；三次均还原（md5 = `8a8cf1c1…`）+ 重建后 `integ048t/{power_bootrom_store,closed_power_bootrom}`、`049t/old_ram_unmapped`、`040t/ptwerr_monitor_cfxmem_exit` 全 rc=0，`--source-state` qemu clean。
**门控真数（自采 rc）**：`check-arch=0`（14 探针 PASS）、`check-arch-smoke=0`、`check-inst-asm=0`（**904/904**）、`check-linux-k1=0`（**108/108**）、`check-linux-k0=2`（**116/119**）、`check-linux-k2=2`（**102/104**，仅 R1/R2）、`k2_trap/time/irq = 85/85、151/151、97/97`、`check-qemu-forms`/`check-interface`/`check-component-changelog=0`、`check-patch-tree` qemu 断言 **0**、`make_patch` 0 written 且 md5 稳定、`apply_series --component qemu` rc=0 且 HEAD 不变。**K0/K2 独立归因**：失败条目 = `K12 apply-series --component linux`（第 1/2 次）+ `K12 两次运行只处理 linux`，原文 `apply-series: linux HEAD (64f82a081a3b) is neither base (7b20d05fd38d) nor base+1 matching the patch set; refusing to apply`；共享 linux 源树 HEAD `64f82a081 dadao: linux patch series`（Guan Xuetao，2026-11-16 17:21，`m14-linux-011` 的补丁集本地提交），本任务 `components/linux` 改动 **0** ⇒ K2 R1/R2 由 K0 派生，均外因。
**越界/快照**：`git diff --name-only bc1a15da..ac90f857` = 10 文件（3 补丁 + changelog + 5 探针 + 本任务书），`components/linux`/`tests/inst`/`spec`/`contracts`/`.tao/knowledge`/`tools/linux`/`Makefile` = **0**；与第 1 轮快照比仅 `helper.c.patch`、`helper.c`、`min_rom_probe_integ048t.py` 三项变化（返工范围吻合）；验收前后 `git status -uall` 空、HEAD `ac90f857`。
**判决：Accepted** —— 第 1 轮阻断项已改到实现（哨兵 + 按触发 IP 回读 + 读失败具名退出），期望值由契约独立派生且与回读一致，三路注入证伪通过，门控与补丁纪律无回归。
**非阻断**：① 第 1 轮 ②（`cause_id` 全宽无 wyde3）已由主会话在 `m14-qemu-005` 任务书登记（master `c744f393`），本分支不含该提交，收尾时确认即可；② 证据脚本首次运行被外力 `Terminated`（环境干扰 1/3，已记录、已还原并重跑成功，未掩盖）；③ `dadao_insn_word` 的内存窗口分支当前无用例覆盖（唯一哨兵来源是只读 ROM 存储），建议后续补一例。
