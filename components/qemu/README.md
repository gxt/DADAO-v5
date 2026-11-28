# QEMU 组件（qemu）

DADAO 的 QEMU 目标（CPU 模型 + 解码 + 标量执行 + 裸机测试机）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定；工作树由 `make fetch` + `make apply-series` 在 `.work/source/qemu` 建立。

## 机器（machine）

- 两台机器类型（M12 起，`spec/Kaiwu §1`）：`-M kaiwu-tiny`（**8 KiB BootROM + 256 KiB SRAM + 8 KiB hmon SRAM**，无 cfx/PTW；`m19-qemu-001` 起的新几何）与 `-M kaiwu-vast`（4 MiB BootROM + 2 GiB PA RAM，完整 cfx/PTW）。几何与能力在注册时按机器类型固定（`DadaoProfile`），**不再有运行期 `profile=` 选择器**。
- **Tiny 装载与主 SRAM 布局（`spec/Kaiwu §6.2/§6.2.1`；`m19-qemu-001`）**：`bootrom-image`/`-bios` 只接受**恰好 8 KiB** 的固件、原样装入 `0xffff_ffff_0000`（复位 PC 不变）；`-kernel`（raw 或 ELF）只能落在应用窗口 `MAIN_SRAM_BASE + 0x2000` 起 128 KiB 内，raw 基址与入口统一 `0xffff_ff00_2000`（`kernel_reserved = 0`），`e_entry ≠ 0xffff_ff00_2000`、`PT_LOAD` 落在 BootROM/hmon SRAM/头区或窗口外、bootrom 尺寸不符均**报错退出**；头区（`VERSION`@0x0000、`MAILBOX`@0x0020、`EXIT_BLOCK`@0x0030）、`DUMP`@0x0800（0x800）、`SIGNATURE`@0x1000、`STACK`@0x39000、`MemRAS`@0x3F000 按该布局建模，`guard_lo`@0x38000（4 KiB）不映射（访存 ⇒ `CFXMEM`）。`MAILBOX` magic 仍为 `[OPEN]`（N44），QEMU 不实现放核握手。
- 过渡别名已移除（`m12-integ-001`）：旧机器名与旧 profile 名不再接受，`-M help` 只列 `kaiwu-tiny`/`kaiwu-vast`；用旧名字启动得到明确的 machine not found / invalid choice 错误，不再静默映射。
- `cfx5`（`cfx_cache`）在 Vast 上**始终存在**（`kaiwu-tiny` 无）：`-machine kaiwu-vast,cache-model=off`（默认）时 `cache_exist` 读 0、`cache_ctrl` 合法编码被接受但无效果、非法编码仍 `CFXREG`；`on` 时 `cache_exist` 读 `0b11`。两种模型下 `cache_enable`/`cache_addr_start`/`cache_addr_size` 都可读写，`cache_ctrl` 为 WO；`cg0`–`cg7` 走 `contract-see §3` 的共有寄存器表（含 `cg3 rc12` 的 `hypv_cg_reg_deleg`，bit3 恒 1），`cg8` 的其余 rc 按 `contract-cache.md` 报 `CFXREG`；`cache-model` 非法值或 Tiny 上给 `on` 均在启动期报错退出。
- **影子 D-Cache 数据通路（`cache-model=on`；`m16-qemu-002`）**：8 路 × 128 组 × 64 B 写回 D-Cache（`contract-cache` CACHE-05/27/30，几何与 Wuming RTL 一致），读命中读影子、读缺失整行填充、写命中只改影子并置 dirty、写缺失写分配、脏行淘汰整行写回；数据侧由 `tlb_fill` 重定向到代理 `MemoryRegion`，**DMA（`cfx_pmem`）与镜像装载直连底层 RAM、绕过影子**，`off` 不建代理（行为与直通现状一致）；页表读取与 A/D 回写走同一影子路径以保持一致性。
- **`cache_ctrl` 维护命令（`m16-qemu-003`）**：`[1:0]` 操作（none/clean/invalidate/flush）× `[3:2]` 范围（all/PA 单行/PA 区间/reserved）× `[15:14]` 选择（bit15=I、bit14=D），`addr_start`/`addr_size` 按 56 位 PA；D 侧 clean 写回保留、invalidate 丢弃不写回、flush 写回+删除；I 侧 clean no-op、invalidate/flush 使后续取指重取（不做 I 阵列）；两侧全选先 I 后 D；`cache_enable` 对应位为 0 时该侧不维护（校验不受影响）、不可缓存/MMIO PA 无效果不报异常；`cache-model=off` 下合法命令 no-op、非法仍 `CFXREG`。
- **异常原因编码是扁平位图（`m17-qemu-001`；`ADR-0062`；`contract-see §6.1/§6.1.1`）**：`excp_cause_id` 的 64 位内**恰一位**为 1——`[15:0]` 同步 cause（`CFXMEM` = 非 PTW 核内访存、`CFXPERM` = cfx 来源掩码拒绝，两者都**不**带高位位图），或 PTW 故障的 `[38:32]` 权限类 / `[56:48]` 缺失类 / `[56] ADWBFAIL`（此时 `[15:0]` 全 0）。`[39]`/`[57]` 已删除（恒 0）。`cause_info`：`CFXPERM` = 触发指令地址（与 `excp_cause_ip` 同值）、`CFXMEM` = 被访问的核内地址、PTW 权限/缺失 = 访问的 VA、`[56]` = PTE 物理地址。PTW 故障按当前运行模式进对应 monitor（Tiny 无 PTW，Vast 的退出码不承载 PTW 故障）。`dadao_cause_check()` 在异常进入时按上述不变式校验，违反即 `exit(1)`（不静默屏蔽）。
- 安装根 `qemu-system-dadao` 由 `make install-host` 写入（ADR-0016 D9）。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），清单见 `series`。
- 规范：`docs/Process-01-组件补丁组织与构建编排.md`；上位决策：`ADR-0002 D4`（rev. 2026-09-23）。
- 规模（2026-11-08 现场统计）：**66 份** = 新增 49 + 修改 17。
- 主要内容：`target/dadao` 骨架、`insn.decode` 解码、RD/RB/RA 指令语义、`translate.c` 拆分（12 个 `insn_trans/*.c.inc`）、控制流、TB 续接修复、SEE/semihosting（含唯一 RAM 段与 boot ROM 映射）；另有 17 处对上游既有文件的修改（`accel/tcg/cpu-exec-common.c`、`hw/Kconfig`、`hw/meson.build`、`include/qemu/base-arch-defs.h`、`include/system/memory.h`、`linux-user/{meson.build,mmap.c,qemu.h,signal.c,syscall.c,syscall_defs.h,user-mmap.h}`、`qapi/machine.json`、`qemu-options.hx`、`system/memory.c`、`target/{Kconfig,meson.build}`）。
- 用户态目标（`QEMU-062t` / P3）：`linux-user/dadao/**`（cpu_loop / elfload / signal / target_* 头 / 号表）+ `configs/targets/dadao-linux-user.mak`，`make build-qemu` 同时产出 `qemu-system-dadao` 与 `qemu-dadao`。

## 校验

```
make check              # 含 check-patch-tree（五断言）
python3 tools/infra/check_patch_tree.py
```
