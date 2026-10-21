# gem5 组件变更

## M8

- **2026-10-12 `GEM5-002t`**
  - 摘要：锁定官方 `v25.1.0.1`；建立 DADAO 目标入口说明及补丁集。
- **2026-10-12 `GEM5-003t`**
  - 摘要：注册 DADAO SCons ISA 构建，加入裸机单核状态、定长大端译码、首批算术和异常路径、规范向量运行夹具。
- **2026-10-12 `GEM5-004t`**
  - 摘要：完成 151 个有 active 向量的 M1 指令 ID，包括整数/地址运算、RD/RB/RA 访存与块操作、控制流、`call`/`ret`、RegRAS/MemRAS 和 `swym`；517 条 current、61 条 skeleton 和三条 smoke 序列通过。
- **2026-10-15 `GEM5-005t`**
  - 摘要：加入 Machine-01 ELF/PT_LOAD、boot ROM、RAM/ROM 地址图、规范 cfx 现场与 trap/escape、完整 25 项 semihosting；47 项机器门控、真实工具链 boot ROM+ELF 及错误期望反例通过。
- **2026-10-15 `GEM5-006t`**
  - 摘要：实现 RF/FCSR、60 条 FP、M3 `sub.o` 和 7 条 M8 位操作；11 条 excluded 编码保持 `ILLI`，234/234 opcode 覆盖、329 条 FP oracle 与 541 条 remaining 用例通过。
- **2026-10-19 `GEM5-007t`**
  - 摘要：同步新增 `aip.si` 及其 IP 相对语义；建立裸机 E2E/Embench 清单、代表档与全量档，记录退出码和最终状态差分，并将 gem5 代表/完整门控接入 L2/L3。
- **2026-10-21 `GEM5-008m`**
  - 摘要：完成裸机闭环核验；opcode 259/259、current 510、Machine-01 47、remaining 620、FP 329、程序 58/58，L1/L2/L3 与反例门控全绿。

## M9

- **2026-10-21 —**
  - 摘要：同步 `ext/shl` 新编码与 `rol` 语义；原子 25 条保持 defined-but-excluded/`ILLI`，覆盖 259/259、current 510、remaining 620。
