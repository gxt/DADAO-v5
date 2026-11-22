# QEMU 组件（qemu）

DADAO 的 QEMU 目标（CPU 模型 + 解码 + 标量执行 + 裸机测试机）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定；工作树由 `make fetch` + `make apply-series` 在 `.work/source/qemu` 建立。

## 机器（machine）

- 两台机器类型（M12 起，`spec/Kaiwu §1`）：`-M kaiwu-tiny`（64 KiB BootROM + 8 MiB SRAM，无 cfx/PTW）与 `-M kaiwu-vast`（4 MiB BootROM + 2 GiB PA RAM，完整 cfx/PTW）。几何与能力在注册时按机器类型固定（`DadaoProfile`），**不再有运行期 `profile=` 选择器**。
- 过渡别名已移除（`m12-integ-001`）：旧机器名与旧 profile 名不再接受，`-M help` 只列 `kaiwu-tiny`/`kaiwu-vast`；用旧名字启动得到明确的 machine not found / invalid choice 错误，不再静默映射。
- `cfx5`（`cfx_cache`）在 Vast 上**始终存在**（`kaiwu-tiny` 无）：`-machine kaiwu-vast,cache-model=off`（默认）时 `cache_exist` 读 0、`cache_ctrl` 合法编码被接受但无效果、非法编码仍 `CFXREG`；`on` 时 `cache_exist` 读 `0b11`。两种模型下 `cache_enable`/`cache_addr_start`/`cache_addr_size` 都可读写，`cache_ctrl` 为 WO，其余 cg/rc 按 `contract-cache.md` 报 `CFXREG`；`cache-model` 非法值或 Tiny 上给 `on` 均在启动期报错退出。
- **影子 D-Cache 数据通路（`cache-model=on`；`m16-qemu-002`）**：8 路 × 128 组 × 64 B 写回 D-Cache（`contract-cache` CACHE-05/27/30，几何与 Wuming RTL 一致），读命中读影子、读缺失整行填充、写命中只改影子并置 dirty、写缺失写分配、脏行淘汰整行写回；数据侧由 `tlb_fill` 重定向到代理 `MemoryRegion`，**DMA（`cfx_pmem`）与镜像装载直连底层 RAM、绕过影子**，`off` 不建代理（行为与直通现状一致）；页表读取与 A/D 回写走同一影子路径以保持一致性。
- **`cache_ctrl` 维护命令（`m16-qemu-003`）**：`[1:0]` 操作（none/clean/invalidate/flush）× `[3:2]` 范围（all/PA 单行/PA 区间/reserved）× `[15:14]` 选择（bit15=I、bit14=D），`addr_start`/`addr_size` 按 56 位 PA；D 侧 clean 写回保留、invalidate 丢弃不写回、flush 写回+删除；I 侧 clean no-op、invalidate/flush 使后续取指重取（不做 I 阵列）；两侧全选先 I 后 D；`cache_enable` 对应位为 0 时该侧不维护（校验不受影响）、不可缓存/MMIO PA 无效果不报异常；`cache-model=off` 下合法命令 no-op、非法仍 `CFXREG`。
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
