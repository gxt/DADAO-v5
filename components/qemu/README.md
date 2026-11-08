# QEMU 组件（qemu）

DADAO 的 QEMU 目标（CPU 模型 + 解码 + 标量执行 + 裸机测试机）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定；工作树由 `make fetch` + `make apply-series` 在 `.work/source/qemu` 建立。

## 机器（machine）

- 两台机器类型（M12 起，`spec/Machine-v5 §1`）：`-M dadao-tiny`（64 KiB BootROM + 8 MiB SRAM，无 cfx/PTW）与 `-M dadao-vast`（4 MiB BootROM + 2 GiB PA RAM，完整 cfx/PTW）。几何与能力在注册时按机器类型固定（`DadaoProfile`），**不再有运行期 `profile=` 选择器**。
- 过渡别名（`deprecated since M12`，仅保留到 `m12-integ-001`）：`-M dadao-m1` 等同 `dadao-tiny`，其 `profile=tiny|vast` 与 `profile=node`（`node` 映射 `vast`）以及 `DADAO_TEST_PROFILE` 环境变量仍可用；`-M help` 中该机型的描述文本标 `(deprecated)`；**未**使用 `MachineClass::deprecation_reason`（其启动警告会带统一 `qemu-system-dadao:` 前缀，被 `tools/testcases/diff_ir_lli.py` 误判为装载拒绝）。
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
