# QEMU 组件（qemu）

DADAO 的 QEMU 目标（CPU 模型 + 解码 + 标量执行 + 裸机测试机）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定；工作树由 `make fetch` + `make apply-series` 在 `.work/source/qemu` 建立。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），清单见 `series`。
- 规范：`docs/Process-01-组件补丁组织与构建编排.md`；上位决策：`ADR-0002 D4`（rev. 2026-09-23）。
- 规模（2026-10-17 现场统计）：**59 份** = 新增 49 + 修改 10。
- 主要内容：`target/dadao` 骨架、`insn.decode` 解码、RD/RB/RA 指令语义、`translate.c` 拆分（12 个 `insn_trans/*.c.inc`）、控制流、TB 续接修复、SEE/semihosting（含唯一 RAM 段与 boot ROM 映射）；另有 10 处对上游既有文件的修改（`hw/Kconfig`、`hw/meson.build`、`include/qemu/base-arch-defs.h`、`qapi/machine.json`、`qemu-options.hx`、`target/Kconfig`、`target/meson.build`、`linux-user/meson.build`、`linux-user/syscall.c`、`linux-user/syscall_defs.h`）。
- 用户态目标（`QEMU-062t` / P3）：`linux-user/dadao/**`（cpu_loop / elfload / signal / target_* 头 / 号表）+ `configs/targets/dadao-linux-user.mak`，`make build-qemu` 同时产出 `qemu-system-dadao` 与 `qemu-dadao`。

## 校验

```
make check              # 含 check-patch-tree（五断言）
python3 tools/infra/check_patch_tree.py
```
