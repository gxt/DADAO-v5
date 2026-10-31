# `tools/testcases/arch/` — arch scope 执行驱动（TESTCASES-073t）

`docs/Process-09 §6`：**runner/driver 全部收拢到 `tools/testcases/`**，`tests/` 只放用例与
`shared/`。本目录是 arch scope 的驱动与 min-ROM 场景（`TESTCASES-073t` 由集成驱动目录迁入）：

| 文件 | 作用 |
|------|------|
| `run_m5_e2e.py` | SEE/semihosting + cfx 权限端到端驱动（llvm-mc → objcopy → qemu + bootrom；`--inject` 自检） |
| `min_rom_probe_*.py` / `.sh` | min-ROM 场景探针（各自内嵌 ROM 程序 + `-d cpu` 观测；期望值手推自 `spec/`+`contracts/`） |
| `min_rom_probe_integ046t.py` | step5 BootROM 链探针（power→hmon→smon、vector/PTW/PTE/双向 VA-PA、poison、`0xB1`–`0xB7` 反例；`--qemu/--bootrom-image/--only/--list`，默认读 `.dadao/tests/bootrom/step5/`） |
| `min_rom_probe_integ047t.py` | cfx_pmem DMA 的 SBI 契约探针（FID 6/7/8；内嵌 provider 为**测试专用，非生产实现**；`--doc` 离线表形态 + runtime 用例；`--qemu/--only/--list`） |
| `min_rom_probe_integ048t.py` | `cfx_<name>_hypv_cg_reg_deleg` 强制检查探针（supv 按目标 cfx 的 64 位 cg 位图判定 ⇒ `CFXPERM`、cg3 无例外、bit3 恒 1、不豁免 self、hypv/user 不受约束、power BootROM 只读；`--qemu/--only/--list`） |
| `build_step5_bootrom.py` | step5 256 KiB BootROM 打包器（image index table + 三镜像尺寸/ELF 自检 + trap magic 回填 + `--self-test` + `--max-image-size` 注入） |

- 用例**资产**（`.s` 向量 + `expected.yaml`）在 `tests/arch/<cfx>/`；本目录只放驱动，
  不放用例数据。
- 门控：`make check-arch-smoke`（L2）/ `make check-arch`（L3）。
- 迁移期的旧路径薄 wrapper 已在 `TESTCASES-084t` 删除；现行入口只有本目录。
- 探针的 QEMU 默认值是 `.work/build/qemu/qemu-system-dadao`（历史约定，M1–M6 期）；
  `044t/045t/046t/049t/061t/integ046t/integ047t/integ048t` 接受 `--qemu`，门控 `check-arch` 从安装根传入
  （ADR-0016 D9）。其余探针（005t…042t、070t…074t）无 `--qemu`，且未纳入门控
  （部分期望值已与现行 spec 漂移，见 `TESTCASES-073t` 遗留）。
