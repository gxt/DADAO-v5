# QEMU-006t: RD Load/Store

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-005t`、`SPEC-006t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-005t` 产出的 `translate.c`（RD 整数语义已实现，load/store 仍为 ILLI 桩）
  - `.tao/knowledge/contract-isa.md` §1.5（存储模型：有效地址 48 位、高 16 位忽略、大端）、§4.1（存取 RD 寄存器：单/多 load/store、对齐、异常）
  - `.tao/knowledge/adr-0004-test-machine.md`（MALIGN 可观测行为、内存图）
  - `verif/opcodes.yaml`（`ld.*`/`st.*`/`ldm.*`/`stm.*` 的 op/格式/legality）
- 输出：`components/qemu/patches/0004-dadao-load-store.patch`、`components/qemu/patches/series`
- 约束：
  - 大端访问：全部 MemOp 用 `MO_BE*` 变体
  - 有效地址 = `(rbhb + sext12(imms12)) mod 2^48`（高 16 位截断）
  - 多 load/store 在循环前快照 `rdhc`（地址基址），循环内不重新 load
  - ILLI 先于任何寄存器/内存写
  - 本任务不含 RB/RA/RF 存取（RB/**RA** 属 `QEMU-008t`；RF 按 M1 范围排除）
  - 完成后不自行 commit

## 背景（完整）

### 目标

实现 RD 单次与多次 load/store 共 22 条 `trans_*` 的 TCG 语义，使 load/store 正确读写大端内存，MALIGN 精确触发。0628 对应任务 `DL-016a`（含前置修复 `0002` corrupt patch）经评审 Accepted；其 MALIGN/TEMP_EBB 缺陷由 `DL-016b`（`QEMU-007t`）修正。

### 设计理由

- 大端 + 48 位有效地址：0.5.3 存储模型规定高 16 位在地址计算时被忽略（§1.5）。
- 对齐即异常：DADAO 的 MALIGN 需映射到 QEMU `MO_ALIGN_N`，由 `cpu_do_unaligned_access` 精确触发，而非 host SIGBUS/SIGSEGV。
- 展开循环：多 load/store 在 C 层展开为 `immu6` 次单次访问，避免生成循环 TCG。

### 关键概念 / 数据

**EA 计算**：`EA = (rbhb + sext12(imms12)) & 0x0000FFFFFFFFFFFF`（单次）；多 load/store `EA_i = (rbhb + rdhc + i×N) mod 2^48`，`i = 0 … immu6-1`，`N` 为元素字节数，目标为 `rd(ha) … rd(ha+immu6-1)`。

**单次 Load（rrii）** §4.1.1：
| 指令 | 语义 | 对齐 | MemOp（示意） |
|------|------|------|------|
| `ld.sb`/`ld.ub` | 1 字节，符号/零扩展 | 无 | `MO_SB`/`MO_UB` |
| `ld.sw`/`ld.uw` | 2 字节，符号/零扩展 | 2B | `MO_BE` + 对应 + `MO_ALIGN_2` |
| `ld.st`/`ld.ut` | 4 字节，符号/零扩展 | 4B | `MO_BE` + 对应 + `MO_ALIGN_4` |
| `ld.o` | 8 字节，无扩展 | 8B | `MO_BE` + `MO_ALIGN_8` |

**单次 Store（rrii）** §4.1.1：`st.b`/`st.w`/`st.t`/`st.o`，存 `rdha` 低 N 字节；对齐同 load（byte 无要求）。

**多次 Load（rrri）** §4.1.2：`ldm.sb/ub/sw/uw/st/ut/o rdha, rbhb, rdhc, immu6`。

**多次 Store（rrri）** §4.1.2：`stm.b/w/t/o rdha, rbhb, rdhc, immu6`。

**ILLI 检查**（§4.1.1/§4.1.2）：
- 单次/多次：`rdha == 0` → ILLI
- 多次：`immu6 == 0` → ILLI；`rdha + immu6 > 64` → ILLI
- 未对齐 → MALIGN（精确：faulting 指令 PC 保持、目标寄存器/内存不提交）

**多 load/store 快照**：循环前读取 `rdhc`（基址）与 `rbhb`；当读写范围包含 `rdhc` 时，地址计算仍用原始 `rdhc` 值（§4.1.2）。硬件按序号递增逐对先读后写。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-016a-qemu-load-store.md`（完整转述：前置修复 `0002` corrupt patch、22 条指令规格、MemOp 对照、MALIGN、约束、完成区与 Architecture Review）。
- DADAO-0628：`code-agent/tasks/DL-016b-qemu-malign-temp-fix.md`（MALIGN 精确异常 + TEMP_EBB，v5 对应 `QEMU-007t`）。

## 交付物

- `components/qemu/patches/0004-dadao-load-store.patch`：`target/dadao/translate.c`（RD 单/多 load/store）、`target/dadao/cpu.h`（异常编号）、`target/dadao/cpu.c`（对齐异常钩子，若本任务引入）。
- `components/qemu/patches/series`：加入 `0004`。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`ldbs/ldbu/ldws/ldwu/ldts/ldtu/ldo` → `ld.sb/ld.ub/ld.sw/ld.uw/ld.st/ld.ut/ld.o`；`stb/stw/stt/sto` → `st.b/st.w/st.t/st.o`；`ldmbs…ldmo` → `ldm.sb/ub/sw/uw/st/ut/o`；`stmb…stmo` → `stm.b/w/t/o`。
2. **opcode/格式**：v5 的 op 分配（0x10–0x1A、0x20–0x21、0x28–0x3F 等）与 0628 不同，`trans_*` 与 `arg_*` 名按 `QEMU-004t` 的 decodetree 生成结果。
3. **有效地址**：v5 为 48 位有效地址、高 16 位忽略（§1.5），与 0628 的 48 位截断一致，但须以 §1.5 表述为准。
4. **对齐与 MALIGN**：v5 的 MALIGN 可观测行为以 `adr-0004-test-machine.md` D4 为准；对齐规则见 §4.1.1（byte 无要求、wyde 2B、tetra 4B、octa 8B）。
5. **RB/RA/RF 存取**：v5 单列 RB（`QEMU-008t`）与 RA/RF（M1 排除），本任务仅 RD。
6. **不复制补丁正文**：0628 的 `0005-dadao-load-store.patch` 属 0.4.1，仅参考实现风格。

## 已知坑 / 结论

摘自 0628 `DL-016a`/`DL-016b` 完成区与 Architecture Review：

1. **`0002-dadao-hw-meson-subdir.patch` corrupt（P0）**：0628 因 hunk header 与 body 行数不符导致 `git am` 失败；v5 应把 `hw/meson.build` 的 `subdir('dadao')` 并入 `0001` 骨架，避免此类补丁。
2. **MO_ALIGN 全部缺失（P0）**：0628 `DL-016a` 初版未加 `MO_ALIGN_N`，x86 host 上静默放过未对齐访问，MALIGN 永不触发。v5 必须在 `QEMU-006t` 或 `QEMU-007t` 补齐，并以向量验证。
3. **TEMP_EBB**：0628 `do_ldm`/`do_stm` 循环内用 `tcg_temp_new_i64()`（TEMP_TB），最坏 ~130 temp（`TCG_MAX_TEMPS = 512`）；v5 须评估所选 QEMU 版本的 EBB API（0628 的 QEMU 10.0 无 `tcg_temp_ebb_new_i64`）。
4. **48 位 EA 截断**：地址计算后必须 `& 0x0000FFFFFFFFFFFF`。
5. **`rdhc` 快照**：循环前读取，循环内不重新 load。
6. **大端 MemOp**：全部用 `MO_BE*`，不得用小端 flag。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-016a-qemu-load-store.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-016b-qemu-malign-temp-fix.md`
- DADAO-0628：`.work/DADAO-0628/components/qemu/patches/0005-dadao-load-store.patch`（仅参考风格）
- 本项目：`.tao/knowledge/contract-isa.md` §1.5、§4.1；`verif/opcodes.yaml`；`.tao/knowledge/adr-0004-test-machine.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `components/qemu/patches/0004-dadao-load-store.patch` 存在且干净 apply；`series` 已加入
2. RD 单/多 load/store 全部由 ILLI 桩替换为真实 TCG；语义与 §4.1 一致
3. 大端 MemOp；48 位 EA 截断；多 load/store `rdhc` 循环前快照
4. ILLI 检查（`rdha==0`、`immu6==0`、`rdha+immu6>64`）先于写
5. 未对齐访问触发 MALIGN 且精确（faulting PC 保持、无寄存器/内存提交）
6. `make build-qemu` PASS；load/store 向量经「MC 汇编 → QEMU 执行 → 结果比对」与 oracle 一致（若 harness 未就绪，记录依赖并保留可复现命令）
7. 完成区含真实构建/运行输出；未自行 commit

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
