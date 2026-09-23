# QEMU 组件（qemu）

DADAO 的 QEMU 目标（CPU 模型 + 解码 + 标量执行 + 裸机测试机）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定；工作树由 `make fetch` + `make apply-series` 在 `.work/source/qemu` 建立。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），清单见 `patches/series`。
- 规范：`docs/spec/component-patching.md`；上位决策：`ADR-0002 D4`（rev. 2026-09-23）。
- 规模（2026-09-23 M1 重整后）：**31 份** = 新增 25 + 修改 6。
- 主要内容：`target/dadao` 骨架、`insn.decode` 解码、RD/RB/RA 指令语义、`translate.c` 拆分（10 个 `insn_trans/*.c.inc`）、控制流、TB 续接修复与 exit-port 可靠 halt；另有 6 处对上游既有文件的修改（`hw/Kconfig`、`hw/meson.build`、`include/qemu/base-arch-defs.h`、`qapi/machine.json`、`target/Kconfig`、`target/meson.build`）。

## 校验

```
make check              # 含 check-patch-tree（四断言）
python3 tools/infra/check_patch_tree.py
```
