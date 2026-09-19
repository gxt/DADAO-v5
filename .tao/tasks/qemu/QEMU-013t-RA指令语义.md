# QEMU-013t: RA 指令语义

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-008t`、`SPEC-002t`、`SPEC-003t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`.tao/knowledge/contract-isa.md` §4.9（RA 寄存器存取与块赋值）、§1.3.4（ra0–ra63 MemRAS/RegRAS）；`contracts/opcodes.yaml`（RA 指令编码）；`.tao/knowledge/adr-0004-test-machine.md`（fault/exit 可观测）
- 输出：`components/qemu/patches/` 中 RA 指令补丁（`trans_*`）+ RA 向量补充
- 约束：Spec-first（语义以 §4.9/§1.3.4 为准，不从实现反推）；异常按 ADR-0004；只处理 RA 指令，不越界改其它指令

## 背景（完整）

### 目标

在 QEMU 中实现 M1 的 **RA 相关指令语义**：`ld.o-ra`、`st.o-ra`（RA 单存取）、`ldm.o-ra`、`stm.o-ra`（RA 多存取）、`rd2ra`、`ra2rd`（RA↔RD 块赋值），含 RA 寄存器模型（MemRAS/RegRAS）。**本任务拥有 RA 全部指令**（含从 `QEMU-008t` 移出的 `rd2ra`/`ra2rd`）。

### 设计理由

- RA 相关指令在 M1 范围（2026-09-12 范围变更，见 `.tao/knowledge/deferred.md`）。
- RA 是独立寄存器组（`ra0`=MemRAS、`ra1–ra63`=RegRAS），存取语义与 RD/RB 不同，**需专门任务与专门验证**，不并入 RD/RB 任务。

### 关键概念 / 数据

- RA 指令（`contract-isa.md` §4.9）：RA 单/多存取、RA↔RD 块赋值。
- RA 寄存器模型（§1.3.4）：`ra0` MemRAS 引用计数/指针（低 48 位为 0 时仅 RegRAS）；`ra1–ra63` RegRAS（`ra63` 为栈顶）。
- 异常（§4.9 + ADR-0004）：RA 存取对齐 → MALIGN；`immu6 == 0` / 起始+immu6>64 → ILLI。

## 交付物

- `components/qemu/patches/0008-dadao-ra-semantics.patch`：RA 指令 `trans_*`（`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`/`rd2ra`/`ra2rd`）+ RA 寄存器模型辅助函数。
- `components/qemu/patches/series`：追加 `0008`。
- RA 向量补充（`tests/vectors/isa/mem-ra.yaml`，含 normal/legality/boundary）。

## 验收标准

1. `components/qemu/patches/0008-dadao-ra-semantics.patch` 存在且干净 apply；`series` 已追加 `0008`
2. RA 指令语义与 `contract-isa.md` §4.9 一致（含 MemRAS/RegRAS 模型；`rd2ra`/`ra2rd` 块赋值含 ILLI 检查）
3. 对齐/合法性异常按 ADR-0004 可观测（MALIGN/ILLI，精确、无 commit）
4. 每完成一个 `trans_*` 即用 `QEMU-014t`/`QEMU-015t` 的 harness 验证：RA 向量经「raw encoding → QEMU 执行 → 结果比对」一致（TDD 式；若 harness 尚未完成，记录依赖并保留可复现命令。该免责仅适用任务级验收；`QEMU-020m` 里程碑核验必须全量语义 PASS）
5. `make build-qemu` 全绿；未越界改动非 RA 指令

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
