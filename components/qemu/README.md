# QEMU 组件（qemu）

DADAO 的 QEMU 目标（CPU 模型 + 解码 + 标量执行 + 裸机测试机）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定；工作树由 `make fetch` + `make apply-series` 在 `.work/source/qemu` 建立。

## 机器（machine）

- 两台机器类型（M12 起，`spec/Kaiwu §1`）：`-M kaiwu-tiny`（64 KiB BootROM + 8 MiB SRAM，无 cfx/PTW）与 `-M kaiwu-vast`（4 MiB BootROM + 2 GiB PA RAM，完整 cfx/PTW）。几何与能力在注册时按机器类型固定（`DadaoProfile`），**不再有运行期 `profile=` 选择器**。
- 过渡别名已移除（`m12-integ-001`）：旧机器名与旧 profile 名不再接受，`-M help` 只列 `kaiwu-tiny`/`kaiwu-vast`；用旧名字启动得到明确的 machine not found / invalid choice 错误，不再静默映射。
- `cfx5`（`cfx_cache`）在 Vast 上**始终存在**（`kaiwu-tiny` 无）：`-machine kaiwu-vast,cache-model=off`（默认）时 `cache_exist` 读 0、`cache_ctrl` 合法编码被接受但无效果、非法编码仍 `CFXREG`；`on` 时 `cache_exist` 读 `0b11`。两种模型下 `cache_enable`/`cache_addr_start`/`cache_addr_size` 都可读写，`cache_ctrl` 为 WO，其余 cg/rc 按 `contract-cache.md` 报 `CFXREG`；`cache-model` 非法值或 Tiny 上给 `on` 均在启动期报错退出。影子 D-Cache 数据通路与维护命令效果不在本版（`m16-qemu-001`）。
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
