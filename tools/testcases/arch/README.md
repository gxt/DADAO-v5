# `tools/testcases/arch/` — arch scope 执行驱动（TESTCASES-073t）

`docs/Process-09 §6`：**runner/driver 全部收拢到 `tools/testcases/`**，`tests/` 只放用例与
`shared/`。本目录是 arch scope 的驱动与 min-ROM 场景（`TESTCASES-073t` 由集成驱动目录迁入）：

| 文件 | 作用 |
|------|------|
| `run_m5_e2e.py` | SEE/semihosting + cfx 权限端到端驱动（llvm-mc → objcopy → qemu + bootrom；`--inject` 自检） |
| `min_rom_probe_*.py` / `.sh` | min-ROM 场景探针（各自内嵌 ROM 程序 + `-d cpu` 观测；期望值手推自 `spec/`+`contracts/`） |
| `min_rom_probe_m18qemu008.py` | **异步 escape 出口（`ADR-0061` R3，`DADAO-12` 0.8.0）**：21 例 / 150 断言，纯 word 编码（不依赖汇编器 `escape` 语法）——`cg5 rc0`–`rc3` 写 ⇒ `CFXREG`、`rc8`–`rc11` RW 且 `rc11` 复位全 1；`cg0`–`cg3` 四行**各自**验证 `rc14`/`rc15` 生效与旧 `rc8`/`rc10` ⇒ `CFXREG`（槽位/复位值/低 2 位规则现场取自 `DADAO-12 §3.1–§3.4`）、`cg9` 的 `rc0`–`rc5`/`rc14`/`rc15` 与 `rc6`–`rc13` ⇒ `CFXREG`、`cg9 rc0`–`rc5` 写忽略；同步 `trap` 与异步进入的写入集合；`escape` 正常返回（mode/cfx/ip/mask）、`rc11` 整字恢复、`imms18≠0` ⇒ `ILLI`、错 cfxha/未实现目标/升权 ⇒ `CFXESC`、`escape_num`+1；`--self-test` 逐断言注入可达 FAIL；`--qemu/--case` |
| `min_rom_probe_integ046t.py` | step5 BootROM 链探针（power→hmon→smon、vector/PTW/PTE/双向 VA-PA、poison、`0xB1`–`0xB7` 反例；`--qemu/--bootrom-image/--only/--list`，默认读 `.dadao/tests/bootrom/step5/`） |
| `min_rom_probe_integ047t.py` | cfx_pmem DMA 的 SBI 契约探针（FID 6/7/8；内嵌 provider 为**测试专用，非生产实现**；`--doc` 离线表形态 + runtime 用例；`--qemu/--only/--list`） |
| `min_rom_probe_integ048t.py` | `cfx_<name>_hypv_cg_reg_deleg` 强制检查探针（supv 按目标 cfx 的 64 位 cg 位图判定 ⇒ `CFXPERM`、cg3 无例外、bit3 恒 1、不豁免 self、hypv/user 不受约束、power BootROM 只读；`--qemu/--only/--list`） |
| `min_rom_probe_integ049t.py` | cg7 内部空间描述探针（16×4 静态只读表：smon/hmon/pmem/power 四类空间块、`space[1..15]` 全 0、`desc`/`attr` 位规则、全 rc 可读、写任意 rc ⇒ `CFXREG`、未实现 cfx 仍 `CFXREG`；`--qemu/--only/--list`） |
| `min_rom_probe_integ050t.py` | `cfx_time`（cfxha 34：`cg10 rc0` 1 GHz、`rc1` 64 位时间、`SBI_TIME_GET`）与单 hart `cfx_hart`（cfxha 15：`cg8 rc0` hart_id、`rc2/rc3` 64 位 cycle/insn、`rc4/rc5` timer_cmp/timer_ctrl、`SBI_HART_GET_ID`/`SBI_HART_SET_TIMER`）探针；TIMER 按 ADR-0061 R2 投递 `cfx_hart` 的 `cg9 rc5` supv 单向量、源身份 = 源 cfxha（bit 15）、`cg9 rc3/rc4` 捕获/待投位图、来源 mask = 当前运行模式 monitor 的 `cg8 rc1`、`IMASK` 只延后到 `cg9 rc4`、源 ack（`timer_cmp` 重装）落位；内嵌 provider 为**测试专用，非生产实现**；`--doc` 离线表形态 + runtime 用例（寄存器用例走 `-d cpu` 观测；定时器/计数用例自检、无 dump：读当前 `cfx_time` 设相对 deadline 后有界轮询，断言到期前不触发 / 窗口内触发 / ISTATUS / 捕获与 pending / 单次与每次覆盖 / ack 无陈旧投递 / 单调性 / `cmp=~0` 关闭）；`--qemu/--only/--list` |
| `min_rom_probe_async_094t.py` | 两 cfx 异步捕获最小探针（ADR-0061 R2）：TIMER（源 cfxha 15）/PMEM_DMA（32）投递 `cfx_hart` `cg9 rc5` supv 单向量；`cg9 rc3/rc4` 捕获与待投位图 HW/RO（写忽略）；来源 mask = 当前运行模式 monitor `cg8 rc1`（屏蔽只置 pending、解除后进入）；同界多源一帧；第二次进入覆盖第一次；源 ack 落位；`escape imms18=2` ⇒ `CFXESC`、`3`/SBZ ⇒ `ILLI`；`--qemu/--only/--list` |
| `min_rom_probe_integ051t.py` | 统一异步中断仲裁探针（ADR-0061 R2：所有源投递 `cfx_hart` 的 `cg9 rc5` supv 单向量；源身份 = 源 cfxha（15/32）；`cg9 rc3` 捕获位图 / `rc4` 待投位图 HW/RO；来源 mask = 当前运行模式 monitor 的 `cg8 rc1`；同界多源一帧、`excp_async_num` 每帧 +1；每次进入整体覆盖、无「帧活动期」/`frame_valid`/软件清帧；TIMER `IMASK` 只延后、源 ack 落位；`escape imms18=2` ⇒ 当前 cfx `CFXESC`（不是异步返回）、`3`/SBZ ⇒ `ILLI`；`--doc` 契约条目 + 补丁树结构（无 `async_enable`/无聚合位图/单一 async 入口）；`--qemu/--only/--list`） |
| `min_rom_probe_integ007t.py` | Tiny hmon「最小保存-跳转」算法契约（m13-integ-007）：构建 64 KiB 固定 BootROM + SRAM-only 应用，QEMU `kaiwu-tiny` 上验证框架写 A/B 即跳 A/B、五类异常现场三值、rd63 保存/恢复、power 默认返回地址（CFXTRAP 闭环）；`--qemu/--toolchain-bin/--work-dir/--timeout` |
| `build_step5_bootrom.py` | step5 256 KiB BootROM 打包器（image index table + 三镜像尺寸/ELF 自检 + trap magic 回填 + `--self-test` + `--max-image-size` 注入） |

- 用例**资产**（`.s` 向量 + `expected.yaml`）在 `tests/arch/<cfx>/`；本目录只放驱动，
  不放用例数据。
- 探针的**模型代际**：`min_rom_probe_m18qemu008.py` 已按 `ADR-0061` R3；其余异步/异常
  探针（`046t`、`integ050t`、`integ051t`、`async_094t`）仍按 R2 的 `cg5`/`cg9` 槽位与
  `escape imms18`，等 `m18-testcases-004` 统一改写（汇编器已改为 `escape cfxHA`）。
- 门控：`make check-arch-smoke`（L2）/ `make check-arch`（L3）。
- 迁移期的旧路径薄 wrapper 已在 `TESTCASES-084t` 删除；现行入口只有本目录。
- 探针的 QEMU 默认值是 `.work/build/qemu/qemu-system-dadao`（历史约定，M1–M6 期）；
  `044t/045t/046t/049t/061t/async_094t/integ042t/integ046t/integ047t/integ048t/integ049t/integ050t/integ051t` 接受 `--qemu`，门控 `check-arch` 从安装根传入
  （ADR-0016 D9）。其余探针（005t…042t、070t…074t）无 `--qemu`，且未纳入门控
  （部分期望值已与现行 spec 漂移，见 `TESTCASES-073t` 遗留）。
