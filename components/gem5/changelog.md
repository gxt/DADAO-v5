# gem5 组件变更

- `GEM5-002t`：锁定官方 `v25.1.0.1`；建立 DADAO 目标入口说明及补丁集。
- `GEM5-003t`：注册 DADAO SCons ISA 构建，加入裸机单核状态、定长大端译码、首批算术和异常路径、规范向量运行夹具。
- `GEM5-004t`：完成 151 个有 active 向量的 M1 指令 ID，包括整数/地址运算、RD/RB/RA 访存与块操作、控制流、`call`/`ret`、RegRAS/MemRAS 和 `swym`；517 条 current、61 条 skeleton 和三条 smoke 序列通过，独立审阅 `Accepted`。
