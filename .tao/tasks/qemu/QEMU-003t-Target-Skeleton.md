# QEMU-003t: Target Skeleton

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-002t`、`SPEC-008t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-002t` 选定的 QEMU 上游 commit（`manifests/components.lock.toml` 中 qemu 条目）
  - `.tao/knowledge/adr-0004-test-machine.md`（`SPEC-008t` 产出：内存图、复位值、exit port 协议、MALIGN/ILLI/UNDI 可观测行为）
  - `.tao/knowledge/contract-isa.md` §1（寄存器模型：rd/rb/rf/ra 各 64×64、rd0=0、rb0=PC、rf0=FCSR、ra0–ra63 RegRAS）、§2（32 位大端、4 字节对齐、5 域编码）
  - `verif/opcodes.yaml`、`verif/legality_rules.yaml`（`SPEC-003t`/`VERIF-002t`）
- 输出：`components/qemu/patches/0001-dadao-target-skeleton.patch`、`components/qemu/patches/series`、最小冒烟脚本
- 约束：
  - `git am` 到 `.work/source/qemu` 后 `make build-qemu` 成功编译出 `qemu-system-dadao`
  - 所有指令默认走 `gen_exception_illegal()`（ILLI），不做任何静默忽略
  - 大端：指令 fetch 与数据访问均为大端，`IS_LITTLE_ENDIAN = false`
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
- 复位值以 `adr-0004-test-machine.md` D2 冻结值为准：rd/rb/ra 复位（rd0、rb0 的高 16 位按 spec）、rf0 复位常量须从 0.5.3 `SimRISC-00 §浮点状态寄存器` 位布局独立推导（**不得照抄 0.4.1 常量**），pc 复位到 ADR-0004 冻结的 ROM 入口。

**QOM/CPU 注册（`cpu.c`）**：`TypeInfo.name = DADAO_CPU_TYPE_NAME("any")`；实现 `dadao_cpu_do_interrupt()`（存根）；实现 `dadao_cpu_tlb_fill()`（M1 仅物理地址）；`disas_set_info` 可暂缺。

**TCG 翻译骨架（`translate.c`）**：`gen_intermediate_code()` 读取 32-bit 大端指令字（`translator_ldl_swap` 等，以所选 QEMU 版本的 `target/riscv/translate.c` 为准）；全部指令分派默认 `gen_exception_illegal()`；fetch 步进 4。

**Helper 骨架（`helper.c`/`helper.h`）**：`raise_exception`、`illegal`；异常编号在 `cpu.h` 定义（ILLI/UNDI/MALIGN/IALIGN，编号以 ADR-0004 D5 与所选 QEMU 版本约定为准，不与 guest exit signature 混用）。

**裸机机器（`hw/dadao/`）**：按 ADR-0004 D1 内存图（参考布局 ROM `0x0010_0000` 64KB / Exit port `0x1000_0000` 8B / RAM `0x8000_0000` 128MB，最终以 ADR-0004 冻结值为准）：
- loader：ROM 镜像与测试镜像的加载路径、`-bios`/`-kernel` 行为、缺参报错，均以 ADR-0004 唯一启动协议为准。
- Exit port MMIO：按 ADR-0004 D3 实现「写入 → 退出码传播到 host `$?`」的带退出码机制（注意 0628 ADR 的 P0 结论：普通 `qemu_system_shutdown_request()` 不传播 guest 退出码）；非协议宽度访问归 ILLI（ADR-0004 D5）。
- 机器名以 ADR-0004/项目约定为准（0628 用 `dadao-m1`）。

**构建系统集成**：`configs/targets/dadao-softmmu.mak`、顶层 `meson.build`/`Kconfig`、`target/meson.build`、`hw/Kconfig`，并在 `hw/meson.build` 按字母序加入 `subdir('dadao')`（见已知坑）。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-013a-qemu-skeleton.md`（完整转述：CPU 状态、QOM 注册、TCG 骨架、helper、内存映射、exit port、构建集成、最小冒烟、约束、两轮 Architecture Review）。
- DADAO-0628：`docs/adr/0004-test-machine.md`（内存图/exit 协议/复位的 0.4.1 版本，仅作对照，v5 以自身 ADR-0004 为准）。

## 交付物

- `components/qemu/patches/0001-dadao-target-skeleton.patch`：`target/dadao/{cpu.h,cpu.c,translate.c,helper.c,helper.h,meson.build}`、`hw/dadao/{dadao-machine.c,meson.build,Kconfig}`、构建系统集成（含 `hw/meson.build` 的 `subdir('dadao')`）。
- `components/qemu/patches/series`：加入 `0001`。
- `Makefile`：`build-qemu` 切换为真实 `dadao-softmmu` 构建（若 `QEMU-002t` 已建立）。
- 最小冒烟脚本（启动不崩溃，不验证指令语义）。

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
2. **rf0 复位值遗漏（P0）**：0628 初版把 rf0 全置 0，评审要求改为从 spec 位布局推导的常量；v5 须从 0.5.3 位布局独立推导（`SPEC-008t`/ADR-0004 冻结）。
3. **机器名偏差可接受**：0628 用 `dadao-m1`（与里程碑一致），非 spec 的 `dadao-baremetal`；v5 沿用项目约定并记录。
4. **exit port 宽度违规归 ILLI**：非协议宽度的访问必须触发 ILLI，不得静默忽略（ADR-0004 §D5）。
5. **`make prepare` 前置**：完成区须注明已 fetch 源码并应用补丁序列。
6. **CPUState 字段命名固定**：后续 `QEMU-004t`~`QEMU-008t` 直接引用 `rd[64]`/`rb[64]`/`rf[64]`/`ra[64]`/`pc`。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-013a-qemu-skeleton.md`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0004-test-machine.md`
- DADAO-0628：`.work/DADAO-0628/components/qemu/patches/0001-dadao-target-skeleton.patch`（仅参考文件组织，不复制正文）
- 本项目：`.tao/knowledge/contract-isa.md` §1、§2、§9；`.tao/knowledge/adr-0004-test-machine.md`（待 `SPEC-008t` 产出）
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

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
