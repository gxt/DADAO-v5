# QEMU-003t: Target Skeleton

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-002t`、`SPEC-006t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-002t` 选定的 QEMU 上游 commit（`manifests/components.lock.toml` 中 qemu 条目）
  - `.tao/knowledge/adr-0004-test-machine.md`（`SPEC-006t` 产出：内存图、复位值、exit port 协议、MALIGN/ILLI/UNDI 可观测行为）
  - `.tao/knowledge/contract-isa.md` §1（寄存器模型：rd/rb/rf/ra 各 64×64、rd0=0、rb0=PC、rf0=FCSR、ra0–ra63 RegRAS）、§2（32 位大端、4 字节对齐、5 域编码）
  - `contracts/opcodes.yaml`、`contracts/legality_rules.yaml`（`SPEC-003t`/`SPEC-008t`）
- 输出：`components/qemu/patches/0001-dadao-target-skeleton.patch`、`components/qemu/patches/series`、最小冒烟脚本
- 约束：
  - `git am` 到 `.work/source/qemu` 后 `make build-qemu` 成功编译出 `qemu-system-dadao`
  - 所有指令默认走 `gen_exception_illegal()`（ILLI），不做任何静默忽略
  - 大端：指令 fetch 与数据访问均为大端（v11.1.1 的标准配置方式是 `configs/targets/dadao-softmmu.mak` 的 **`TARGET_BIG_ENDIAN=y`**；旧版符号 `IS_LITTLE_ENDIAN` 在 v11.1.1 已不存在——**注（2026-09-19）**）
  - CPUState 字段命名固定为 `rd[64]`/`rb[64]`/`rf[64]`/`ra[64]`/`pc`，后续任务直接引用
  - 完成后不自行 commit

## 背景（完整）

### 目标

在 `QEMU-002t` 基线上创建 DADAO target 骨架（`target/dadao/` + `hw/dadao/`），使 `make build-qemu` 能真实编译出 `qemu-system-dadao`（可启动；任何指令触发 ILLI）。后续 `QEMU-004t`~`QEMU-008t` 在此骨架上逐步实现具体指令和机器外设。0628 对应任务 `DL-013a` 经两轮评审后 Accepted。

### 设计理由

- 骨架先于语义：先把 QOM 注册、翻译框架、机器模型、构建系统集成打通，再逐指令填充。
- 全指令 ILLI：骨架期不做 unimplemented 静默忽略，保证「未实现」可观测为 ILLI（exit code）。
- 机器与 target 解耦：`hw/dadao/` 裸机机器按 ADR-0004 内存图实现，与 CPU target 分离，便于后续接入差分验证。

### 关键概念 / 数据

**CPU 状态（`target/dadao/cpu.h`）**：按 `contract-isa.md` §1：
- `uint64_t rd[64]`（rd0 恒 0）、`uint64_t rb[64]`（rb0=PC）、`uint64_t rf[64]`（rf0=FCSR）、`uint64_t ra[64]`（ra0–ra63 RegRAS）、`uint64_t pc`
- 复位值以 `adr-0004-test-machine.md` D2 冻结值为准：rd/rb/ra 复位（rd0=0、`rb0=0xffff_ffff_0000` = spec 的 `cfx_power_hypv_excp_vector`）、rf0 复位常量须从 0.5.3 `SimRISC-00 §浮点状态寄存器` 位布局独立推导（**不得照抄 0.4.1 常量**），pc 复位到 ADR-0004 冻结的 ROM 入口 `0xffff_ffff_0000`。

**QOM/CPU 注册（`cpu.c`）**：`TypeInfo.name = DADAO_CPU_TYPE_NAME("any")`；实现 `dadao_cpu_do_interrupt()`（存根）；实现 `dadao_cpu_tlb_fill()`（M1 仅物理地址）；`disas_set_info` 可暂缺。

**TCG 翻译骨架（`translate.c`）**：`gen_intermediate_code()` 读取 32-bit 大端指令字（`translator_ldl_swap` 等，以所选 QEMU 版本的 `target/riscv/translate.c` 为准；**注（2026-09-19）**：v11.1.1 已将该文件移至 **`target/riscv/tcg/translate.c`**——见 `deferred.md`）；全部指令分派默认 `gen_exception_illegal()`；fetch 步进 4。

**Helper 骨架（`helper.c`/`helper.h`）**：`raise_exception`、`illegal`；异常编号在 `cpu.h` 定义（ILLI/UNDI/MALIGN/IALIGN，编号以 ADR-0004 D5 与所选 QEMU 版本约定为准，不与 guest exit signature 混用）。

**裸机机器（`hw/dadao/`）**：按 ADR-0004 D1 内存图（**核内地址空间模型** cfxcode 63/power：boot ROM `0xffff_ffff_0000` 64KB / Exit port `0xffff_8000_0000` 8B / RAM `0xffff_0000_0000` 16MB；以 ADR-0004 冻结值为准）：
- loader：ROM 镜像与测试镜像的加载路径、`-bios`/`-kernel` 行为、缺参报错，均以 ADR-0004 唯一启动协议为准。
- Exit port MMIO：按 ADR-0004 D3 实现「写入 → 退出码传播到 host `$?`」的带退出码机制（注意 0628 ADR 的 P0 结论：普通 `qemu_system_shutdown_request()` 不传播 guest 退出码）；非协议宽度访问归 ILLI（ADR-0004 D5）。
- 机器名以 ADR-0004/项目约定为准（0628 用 `dadao-m1`）。

**构建系统集成**：`configs/targets/dadao-softmmu.mak`、顶层 `meson.build`/`Kconfig`、`target/meson.build`、`hw/Kconfig`，并在 `hw/meson.build` 按字母序加入 `subdir('dadao')`（见已知坑）。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-013a-qemu-skeleton.md`（完整转述：CPU 状态、QOM 注册、TCG 骨架、helper、内存映射、exit port、构建集成、最小冒烟、约束、两轮 Architecture Review）。
- DADAO-0628：`docs/adr/0004-test-machine.md`（内存图/exit 协议/复位的 0.4.1 版本，仅作对照，v5 以自身 ADR-0004 为准）。

## 交付物

- `components/qemu/patches/0001-dadao-target-skeleton.patch`（**20 文件 / 954 行**）：`target/dadao/{cpu.h,cpu.c,cpu-param.h,cpu-qom.h,translate.c,helper.c,helper.h,meson.build,Kconfig}`（9）、`hw/dadao/{dadao-machine.c,meson.build,Kconfig}`（3）、`configs/targets/dadao-softmmu.mak`、**`configs/devices/dadao-softmmu/default.mak`**（v11.1.1 必需，minikconf 输入）、构建系统集成（**`hw/meson.build` 的 `subdir('dadao')`（按字母序，P0）**、`hw/Kconfig`、`target/meson.build`、`target/Kconfig`、**`qapi/machine.json`（`SysEmuTarget` 枚举）**、**`include/qemu/base-arch-defs.h`（`QEMU_ARCH_DADAO`）**）。
- `components/qemu/patches/series`：加入 `0001`。
- `Makefile`：`build-qemu` 切换为真实 `dadao-softmmu` **out-of-tree** 构建（`mkdir -p $(QEMU_BUILD) && cd $(QEMU_BUILD) && $(CURDIR)/$(QEMU_SRC)/configure …`，产物 `.work/build/qemu/`）。
- **`tools/qemu/smoke-dadao-m1.sh`**：最小冒烟脚本（启动不崩溃、任意指令 → ILLI 0x88；不验证指令语义）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **寄存器模型**：v5 为 rd/rb/rf/ra 各 64×64（`contract-isa.md` §1）；0628 的字段布局可借鉴，但 rf0/FCSR 复位值必须从 0.5.3 `SimRISC-00` 位布局推导。
2. **内存图与启动协议**：以 v5 `adr-0004-test-machine.md` 冻结值为准（地址、大小、`-bios`/`-kernel` 唯一协议、ROM blob 布局、RAM entry），不照抄 0628。
3. **exit port**：以 ADR-0004 D3 的带退出码机制为准；不得沿用「`qemu_system_shutdown_request()` 即传播退出码」的错误假设。
4. **异常命名/编号**：0.5.3 异常为 ILLI/MALIGN/UNDI/IALIGN/RASOF/RASUF/CFXREG（§9）；`unimp`→`illi`。
5. **指令命名**：本任务不做指令语义，但骨架中若出现示例指令须用 0.5.3 命名。
6. **不复制补丁正文**：只借鉴文件组织与注册方式，补丁内容按 0.5.3 与所选 QEMU 版本重新生成。

## 已知坑 / 结论

摘自 0628 `DL-013a` 两轮 Architecture Review：

1. **`hw/meson.build` 缺 `subdir('dadao')`（P0）**：仅改 `hw/Kconfig` 不够，`hw/dadao/meson.build` 不会执行、机器不编译、`qemu-system-dadao -M ?` 不显示机器。v5 必须在 `0001` 骨架内按字母序加入 `subdir('dadao')`（0628 的独立 `0002-dadao-hw-meson-subdir.patch` 在 v5 应并入骨架补丁）。
2. **rf0 复位值遗漏（P0）**：0628 初版把 rf0 全置 0，评审要求改为从 spec 位布局推导的常量；v5 须从 0.5.3 位布局独立推导（`SPEC-006t`/ADR-0004 冻结）。
3. **机器名偏差可接受**：0628 用 `dadao-m1`（与里程碑一致），非 spec 的 `dadao-baremetal`；v5 沿用项目约定并记录。
4. **exit port 宽度违规归 ILLI**：非协议宽度的访问必须触发 ILLI，不得静默忽略（ADR-0004 §D5）。
5. **`make prepare` 前置**：完成区须注明已 fetch 源码并应用补丁序列。
6. **CPUState 字段命名固定**：后续 `QEMU-004t`~`QEMU-008t` 直接引用 `rd[64]`/`rb[64]`/`rf[64]`/`ra[64]`/`pc`。
7. **v11.1.1 的 `TCGCPUOps` 非 NULL 断言（2026-09-19 补记）**：v11.1.1 的 `accel/tcg/cpu-exec.c` 硬断言 `cpu_exec_interrupt`/`cpu_exec_halt`/`cpu_exec_reset`/`pointer_wrap` 均非 NULL（共 4 个，另有 `tlb_fill`）；骨架已全部实现 stub，后续任务修改 `cpu.c` 时不得移除。
8. **`make prepare` 非幂等（2026-09-19 补记）**：`tools/infra/apply_series.py` 要求组件 HEAD == 基线 commit，已 patched 的组件（如 `.work/source/llvm-project` 含 5 个 patch commit）会使 `make prepare` 整体失败；单组件重放用 `git checkout --detach <base> && git am components/<name>/patches/*.patch`（已登记 `deferred.md` 的 `## infra`）。

## 参考

- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-013a-qemu-skeleton.md`
- DADAO-0628：`.dadao/DADAO-0628/docs/adr/0004-test-machine.md`
- DADAO-0628：`.dadao/DADAO-0628/components/qemu/patches/0001-dadao-target-skeleton.patch`（仅参考文件组织，不复制正文）
- 本项目：`.tao/knowledge/contract-isa.md` §1、§2、§9；`.tao/knowledge/adr-0004-test-machine.md`（待 `SPEC-006t` 产出）
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `components/qemu/patches/0001-dadao-target-skeleton.patch` 存在且 `git am` 干净应用到 `.work/source/qemu`；`series` 已加入
2. `make build-qemu` PASS，生成 `qemu-system-dadao`
3. `qemu-system-dadao -M ?` 显示约定机器名（如 `dadao-m1`）
4. CPUState 含 `rd[64]`/`rb[64]`/`rf[64]`/`ra[64]`/`pc`；复位值符合 ADR-0004 冻结值（含 rf0 从 0.5.3 位布局推导）
5. 内存图/启动协议/exit port 符合 ADR-0004 D1/D2/D3；非协议宽度 exit port 访问触发 ILLI
6. 未实现任何指令语义：任意指令均触发 ILLI，无静默忽略
7. `hw/meson.build` 含 `subdir('dadao')`
8. 完成区含 `make build-qemu` 与 `-M ?` 的真实输出；未自行 commit

## 完成区

**测试结果**：通过 8/8；无失败项

**修改文件**：
- `components/qemu/patches/0001-dadao-target-skeleton.patch`（新增，20 files changed, 954 insertions）
- `components/qemu/patches/series`（更新，加入 0001）
- `Makefile`（更新 build-qemu 为 out-of-tree 构建）
- `tools/qemu/smoke-dadao-m1.sh`（新增，最小冒烟脚本）

**验收结果**：

### 1. `git am` 干净应用
```
$ git checkout c3d48b7d1e89604920e5b81b91140c2ad39a1943 --detach && git clean -fd && git am components/qemu/patches/0001-dadao-target-skeleton.patch
HEAD is now at c3d48b7 Update version for 11.1.1 release
Applying: target/dadao: Add DADAO target skeleton
```

### 2. `make build-qemu` PASS
```
$ make build-qemu
[2363/2363] Linking target tests/fp/fp-test
build-qemu: PASS
```
退出码：0

### 3. `qemu-system-dadao -M ?` 含 dadao-m1
```
$ .work/build/qemu/qemu-system-dadao -M ?
Supported machines are:
dadao-m1             DADAO M1 bare-metal test machine
none                 empty machine
```

### 4. CPUState 字段与复位值
`target/dadao/cpu.h` 定义 `CPUDADAOState` 含 `uint64_t rd[64]`/`rb[64]`/`rf[64]`/`ra[64]`/`pc`。
复位值（`cpu.c` → `dadao_cpu_reset_hold`）：
- `rb[0] = pc = 0xffff_ffff_0000`（boot ROM 基址 = cfx_power_hypv_excp_vector）
- `rf[0] = 0x7FF8_0000_7FC0_0000`（从 SimRISC-00 §浮点状态寄存器位布局独立推导：fo QNaN `[63:51]=0xFFF`、ft QNaN `[31:22]=0x1FF`、其余 SBZ/R/W 复位为 0）
- `rd[1..63]`/`rb[1..63]`/`ra[0..63]`/`rf[1..63]` = 0

### 5. 内存图/启动协议/exit port
- `dadao-machine.c` 实现 ADR-0004 D1 内存图：RAM `0xffff_0000_0000` 16MiB、Exit port `0xffff_8000_0000` 8B、Boot ROM `0xffff_ffff_0000` 64KiB
- Exit port MMIO：仅 8 字节 store 有效（`size != 8` → ILLI 退出码 0x88），写入值 `& 0xFF` 通过 `qemu_system_shutdown_request_with_code(SHUTDOWN_CAUSE_GUEST_SHUTDOWN, exit_code)` 传播到 host `$?`
- 双镜像启动：`-bios rom.bin` + `-kernel test.bin`，缺参报错退出
- 机器名：`dadao-m1`

### 6. 任意指令 → ILLI
`translate.c` 的 `dadao_tr_translate_insn` 对所有指令调用 `gen_exception_illegal()`，最终通过 `helper_raise_exception` → `dadao_cpu_do_interrupt` → `qemu_system_shutdown_request_with_code(GUEST_PANIC, 0x88)` 退出。
冒烟测试验证：exit code = 136 (0x88)

### 7. `hw/meson.build` 含 `subdir('dadao')`
```
$ grep "subdir('dadao')" .work/source/qemu/hw/meson.build
subdir('dadao')
```

### 8. 真实输出与未自行 commit
`make build-qemu` 退出码 0，`-M ?` 输出含 `dadao-m1`，冒烟 exit code 136。
主仓库 `git status` 显示 Makefile/series/patch 为待提交状态，QEMU 源码仅含 patch commit。

**新发现/坑**：
1. **v11.1.1 需要额外构建系统集成点**：`configs/devices/dadao-softmmu/default.mak`（设备配置）、`qapi/machine.json` 的 `SysEmuTarget` 枚举、`include/qemu/base-arch-defs.h` 的 `QEMU_ARCH_DADAO`——这些在旧版（0628 的 v10.0.0）可能不需要或位置不同
2. **TCGCPUOps 必填字段**：v11.1.1 要求 `cpu_exec_interrupt` 和 `pointer_wrap` 非 NULL（assertion 检查），M1 用 stub `cpu_exec_interrupt` 返回 false + `cpu_pointer_wrap_notreached`
3. **`SHUTDOWN_CAUSE_GUEST_CRASH` 不存在**：v11.1.1 用 `SHUTDOWN_CAUSE_GUEST_PANIC`
4. **`load_image_targphys_as` 签名变化**：v11.1.1 需要5个参数（含 `Error **errp`）
5. **helper noreturn 签名**：`DEF_HELPER_2(raise_exception, noreturn, env, i32)` 生成 `G_NORETURN void helper_raise_exception(CPUDADAOState *env, uint32_t arg1)`——C 实现须匹配
6. **translator_ldl_swap 存在但需正确调用**：使用 `translator_ldl_end(env, db, pc, MO_BE)` 直接获取大端指令字
7. **rf0 复位常量推导**：从 SimRISC-00 §浮点状态寄存器位布局独立推导：fo QNaN `[63:51]=0xFFF`（符号0、E全1、尾数最高位1）、ft QNaN `[31:22]=0x1FF`、SBZ 位=0、R/W 位复位=0 → `0x7FF8_0000_7FC0_0000`。与 ADR-0004 D2 冻结值一致。

**遗留问题**：
- 无。所有8条验收标准均已通过。

## 审阅记录

### 第 1 轮 reviewer 验收

**验收者**：reviewer
**时间**：2026-09-19
**判决**：**Accepted**（8/8）

**独立重跑**：回基线 `c3d48b7d…` + clean 后 **`git am` 干净应用**（exit 0）；清空 build 目录后**干净 out-of-tree `make build-qemu` exit 0**（1m35s，`[2363/2363]`）；产物 `.work/build/qemu/qemu-system-dadao` 34,313,632 B；`-M ?` 含 `dadao-m1`；冒烟 `tools/qemu/smoke-dadao-m1.sh` exit 0（**ILLI 0x88=136**）；`hw/meson.build:5 subdir('dadao')`。

**独立验证亮点**：**QMP `info registers`（`-S`）实测复位值**——PC/RB[0]=`0000ffffffff0000`、**RF[0]=`7ff800007fc00000`**、其余全 0；**rf0 从 `SimRISC-00` 位段独立复算**（`[63:51]=0xFFF<<51` | `[31:22]=0x1FF<<22` = `0x7FF8_0000_7FC0_0000`）与 ADR-0004 D2 及实测三者一致；**`info mtree` 实测**三区域（RAM 16MiB / exit 8B / ROM 64KiB）与 D1 一致；**6 个自造非零指令字全部 exit=136、stderr 0 字节**（含 `add.si rd16,7`=`0x59400007`）；6 个启动协议边界用例（缺 `-bios`/`-kernel`、超 ROM/kernel 尺寸、文件不存在）均 exit 1 且报错清晰；**交叉构建 `alpha-softmmu` exit 0** 证明不破坏其它 target；`make check` exit 0。

**跨模块阻断（非本任务缺陷）**：`make prepare` 整体 **exit 2**——`tools/infra/apply_series.py` 非幂等（组件 HEAD ≠ 基线即拒绝），而 `.work/source/llvm-project` 已含 5 个 patch commit，在到达 qemu 前中止（与 `fetch.py` 的「已 patched 就保留」冲突）。qemu 补丁本身 `git am` 干净应用 ✓。

**前瞻风险（非阻塞）**：① `dadao_cpu_tlb_fill` 未用 `access_type`/未做 48 位屏蔽（ADR D5.6 的 ROM store→ILLI 等留 `QEMU-004t`/`006t`）；② `translate.c` 的 `tb_stop` 分支当前不可达（骨架完整性需要）；③ 任务书 `IS_LITTLE_ENDIAN` 措辞在 v11.1.1 已不存在（实为 `TARGET_BIG_ENDIAN`）；④ `helper.c`/`helper.h`/`translate.c` 缺行尾换行。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-19
**判决**：**确认 Accepted**；**无需新增/修订 ADR**（target 集成方式/`TARGET_BIG_ENDIAN`/exit port 机制/`tlb_fill` 地址模型/`TCGCPUOps` 断言 均被 ADR-0004 或 ADR-0008 覆盖）。

**独立核对**：8 条验收标准逐条通过；补丁 20 文件范围（14 新增 + 6 共享集成，每处 +1 行、无越界）；`qapi/machine.json`/`base-arch-defs.h`/`configs/devices/dadao-softmmu/default.mak` 确为 v11.1.1 必需且最小（后者缺失即 configure 失败；前者是「每个 `SysEmuTarget` 配一个 `QEMU_ARCH`」的既有惯例）；`TCGCPUOps` 实为 **4 个**非 NULL 断言（`cpu_exec_interrupt`/`cpu_exec_halt`/`cpu_exec_reset`/`pointer_wrap`）+ `tlb_fill`；指令 fetch 用 `translator_ldl_end(..., MO_BE)` ✓。

**新发现**：
- **F1**：任务书 `IS_LITTLE_ENDIAN` 措辞过时 → 已改 `TARGET_BIG_ENDIAN=y`。
- **F2**：3 个源文件缺行尾换行 → 登记 `deferred.md`（成本低但需重生成补丁；下次 touch 时补）。
- **F3**：任务书「已知坑」缺 `TCGCPUOps` 非 NULL 断言 → 已补第 7 条。
- **交付物清单**不完整（缺 6 个文件 + 冒烟脚本）→ 已补全。
- **`deferred.md` 更新**：`QEMU_BUILD` 条目→**已消解**；新增 `make prepare` 非幂等（infra）、`tlb_fill` 的 `access_type`（qemu）。
- **`QEMU-014t:129`** 的构建路径（原写 in-tree）→ 已改为 out-of-tree `.work/build/qemu/`。

### 收尾

- F1/F3 + 交付物清单由**主会话**直接修正；F2 登记 `deferred.md`。
- `**状态**` 置 `已验证`（2026-09-19）。
- `MEMORY.md`（qemu `002t`~`003t`）、`changelog.md` 已同步。
