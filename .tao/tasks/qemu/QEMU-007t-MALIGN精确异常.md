# QEMU-007t: MALIGN 精确异常 + TEMP_EBB 修复

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-006t`、`SPEC-008t`

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-006t` 产出的 `components/qemu/patches/0004-dadao-load-store.patch`
  - `.tao/knowledge/contract-isa.md` §4.1（各宽度对齐要求）、§2.6/§9（MALIGN 精确性）
  - `.tao/knowledge/adr-0004-test-machine.md` D4/D5（MALIGN 可观测行为、fault→exit 映射）
- 输出：修订后的 `components/qemu/patches/0004-dadao-load-store.patch`（序号不变）、`components/qemu/patches/series`
- 约束：
  - `MO_ALIGN_N` 覆盖所有需要对齐的 load/store（单次与多次）
  - MALIGN 精确：faulting 指令 PC 保持、目标寄存器/内存不提交
  - 异常编号不与既有 ILLI/UNDI 冲突；exit port 的 guest 层 signature 与 QEMU 内部 `EXCP_*` 编号独立
  - 多 load/store 循环内临时变量评估 EBB（若所选 QEMU 版本提供）
  - 完成后不自行 commit

## 背景（完整）

### 目标

修订 `0004` 补丁，使 MALIGN 精确触发（PC 停在 faulting 指令、无寄存器/内存写入），并消除多 load/store 循环的 TEMP 溢出风险。0628 对应任务 `DL-016b` 修正了 `DL-016a` 被 Architecture Review 误判为通过的两处缺陷。

### 设计理由

- **MO_ALIGN 全部缺失（P0）**：0628 `DL-016a` 的 `ldws/ldwu/ldts/ldtu/ldo/stw/stt/sto` 及多次变体均未加 `MO_ALIGN_N`，在 x86 host 上 QEMU 静默放过未对齐访问，`EXCP_MALIGN` 永不触发，MALIGN 向量无法验证。
- **TEMP_EBB（P1）**：`do_ldm`/`do_stm` 循环内 `ea`/`v` 用 `tcg_temp_new_i64()`（TEMP_TB），最坏情形（如 63 元素 octa 多加载）产生约 130 个 temp，`TCG_MAX_TEMPS = 512`，多指令 TB 内有溢出风险。
- 另发现 `cpu.h` 中 `EXCP_MALIGN` 未定义、`cpu_do_unaligned_access` 未实现，须补齐才能让 `MO_ALIGN` 触发异常。

### 关键概念 / 数据

**1. 定义 `EXCP_MALIGN`**（`cpu.h`）：与既有 `EXCP_ILLI`/`EXCP_UNDI` 编号不冲突（0628 中 UNDI 占用 2，MALIGN 用 3；v5 编号以 `QEMU-003t`/ADR-0004 D5 的约定为准）。exit port 的 guest 层 MALIGN signature 与 QEMU 内部 `EXCP_*` 是两套独立编号。

**2. 实现 `cpu_do_unaligned_access`**（`cpu.c`）：QEMU 在 MemOp 含 `MO_ALIGN_N` 且访问未对齐时调用：
```
cpu_restore_state(cs, retaddr);
cs->exception_index = EXCP_MALIGN;
cpu_loop_exit(cs);
```
并在 CPUClass 注册 `.do_unaligned_access`。参考所选 QEMU 版本 `target/riscv/cpu.c` 的 `riscv_cpu_do_unaligned_access`。

**3. fault handler**：在 exception handler 中增加 MALIGN 分支，按 ADR-0004 D4/D5 将 guest-visible 状态映射到 exit code / 测试可观测结果（0628 写 exit port signature `0x02`）。

**4. 补全 `MO_ALIGN_N`**（`translate.c`）：
| 宽度 | MO_ALIGN flag | 指令 |
|------|--------------|------|
| byte | 无 | `ld.sb/ub`、`st.b`、`ldm.sb/ub`、`stm.b` |
| wyde (2B) | `MO_ALIGN_2` | `ld.sw/uw`、`st.w`、`ldm.sw/uw`、`stm.w` |
| tetra (4B) | `MO_ALIGN_4` | `ld.st/ut`、`st.t`、`ldm.st/ut`、`stm.t` |
| octa (8B) | `MO_ALIGN_8` | `ld.o`、`st.o`、`ldm.o`、`stm.o` |

多 load/store 的 `mop` 参数已含对齐 flag，由各 `trans_*` 调用处传入。

**5. TEMP_EBB**：`do_ldm`/`do_stm` 循环内改用 EBB temp（若所选 QEMU 版本提供 `tcg_temp_ebb_new_i64`）；循环外的 `base`/`idx` 保持普通 temp（需跨迭代保持）。若版本无 EBB API，记录并评估 temp 上限安全边际。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-016b-qemu-malign-temp-fix.md`（完整转述：背景、修复规格、约束、完成区与 Architecture Review，含 QEMU 10.0 无 EBB API 的结论）。

## 交付物

- 修订后的 `components/qemu/patches/0004-dadao-load-store.patch`：`target/dadao/cpu.h`（`EXCP_MALIGN`）、`target/dadao/cpu.c`（`cpu_do_unaligned_access` + 注册 + handler）、`target/dadao/translate.c`（`MO_ALIGN_N` 补全 + EBB temp）。
- `components/qemu/patches/series`：保持 `0004`（替换原文件）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：对齐表按 0.5.3 命名（`ld.sw`/`st.o`/`ldm.o`…）。
2. **异常编号**：`EXCP_MALIGN` 的具体数值以 v5 `QEMU-003t`/ADR-0004 D5 的约定为准，不照抄 0628 的 `EXCP_MALIGN = 3`。
3. **MALIGN 可观测**：以 `adr-0004-test-machine.md` D4 为准（异常类型、faulting PC、不提交的寄存器/内存、测试断言方式）。
4. **EBB API**：以 v5 所选 QEMU 版本为准；若版本提供 EBB，必须使用，否则记录限制。
5. **范围**：v5 本任务仅修订 load/store 补丁；0628 `DL-026a` 中的 `helper_exit`/`EXCP_EXIT`/reset PC/tlb_fill/machine 改动在 v5 分别归入 `QEMU-003t`/`QEMU-008t`，不混入本任务。

## 已知坑 / 结论

摘自 0628 `DL-016b` 完成区与 Architecture Review：

1. **`EXCP_MALIGN` 不冲突**：与 `EXCP_UNDI` 等既有编号区分；guest signature 与内部编号分离。
2. **精确异常**：`cpu_restore_state` 保证 fault 时 PC 停在 faulting 指令，无寄存器/内存提交。
3. **MO_ALIGN 覆盖计数**：0628 最终 `MO_ALIGN_2` 7 处、`MO_ALIGN_4` 6 处、`MO_ALIGN_8` 4 处；v5 须以实际指令集核对。
4. **TEMP_EBB 版本差异**：0628 的 QEMU 10.0 无 `tcg_temp_ebb_new_i64`，循环内保持 TEMP_TB 且安全边际充分；v5 若版本提供 EBB 则应迁移。
5. **补丁序号保持**：修订同一 `0004` 文件，`series` 不变。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-016b-qemu-malign-temp-fix.md`
- DADAO-0628：`.work/DADAO-0628/components/qemu/patches/0005-dadao-load-store.patch`（仅参考风格）
- 本项目：`.tao/knowledge/contract-isa.md` §4.1、§9；`.tao/knowledge/adr-0004-test-machine.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `EXCP_MALIGN` 定义且与既有异常编号不冲突；`cpu_do_unaligned_access` 实现并注册
2. 所有需要对齐的 load/store（单次+多次）补齐 `MO_ALIGN_N`；byte 类不加
3. MALIGN 精确：faulting PC 保持、无寄存器/内存提交；guest-visible 结果符合 ADR-0004 D4
4. 多 load/store 循环临时变量按所选 QEMU 版本使用 EBB 或记录安全评估
5. `0004` 补丁修订后 `series` 顺序 apply 干净；`make build-qemu` PASS
6. `qemu-system-dadao -M ?` 显示约定机器名；`grep` 证据显示 `MO_ALIGN`/`EXCP_MALIGN`/EBB 使用
7. 完成区含真实构建/运行输出；未自行 commit

## 完成区

**状态**：待开始
**Commit**：
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
