# QEMU-043m: M4 qemu 里程碑

**模块**：qemu
**项目里程碑**：M4
**状态**：待开始
**目标**：`qemu-system-dadao` 支持 ELF 加载——解析 `Elf64_Ehdr`/`Phdr`、按 `VA=PA` 装载 PT_LOAD 段、跳 `e_entry`，替代 `objcopy`+trampoline 的 M3 捷径；同时保留 raw-bin 路径（M3 `make test-codegen` 不回归）；畸形 ELF 显式拒绝（加载层非零退出）。为 `INTEG-016t`（多 TU/多段 ELF E2E）提供加载能力。
**关联任务**：`QEMU-042t`（1 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`hw/dadao/` ELF 加载实现 + 导出补丁；探针 `tools/qemu/min_rom_probe_042t.py`（或 `.work/evidence/QEMU-042t/`）；日志 `.work/log/qemu/`
- `make build-qemu` EXIT=0；`make check`/`make check-qemu-semantics` EXIT=0
- ELF 按 `e_entry` 进入并执行到 exit port（真实探针输出）；raw-bin 路径不回归（`make test-codegen` 15/15）
- 畸形 ELF 负例：≥3 类显式拒绝、非零退出（真实输出）
- `make check-patch-tree` EXIT=0；`check-source-state` clean
- 跨模块影响：`SPEC-107t` 的 `ADR-0004` 修订已落地且与实现一致；与 `INTEG-016t`/`LLVM-056t` 的 `e_entry`/段布局约定对齐

## 核验记录（主会话）
（核验命令、输出与退出码；结论）
