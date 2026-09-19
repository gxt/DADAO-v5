# QEMU-006t: RD Load/Store + MALIGN + jump/br.nz（合并任务）

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-005t`、`SPEC-006t`
**状态**：待开始
**补丁**：`0004-dadao-load-store.patch`（ADR-0010 D3 重编号）

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-005t` 产出的 `translate.c`（RD 整数语义已实现，load/store 仍为 ILLI 桩）
  - `.tao/knowledge/contract-isa.md` §1.5（存储模型：有效地址 48 位、高 16 位忽略、大端）、§4.1（存取 RD 寄存器：单/多 load/store、对齐、异常）
  - `.tao/knowledge/contract-isa.md` §5.3（`jump-rrii`：`PC = rbha + rdhb + (imms12<<2)`，48 位）、§5.2.3（`br.nz`：`if (rdha!=0) PC = rb0 + (imms18<<2)`）
  - `.tao/knowledge/adr-0004-test-machine.md`（MALIGN 可观测行为、内存图）
  - `contracts/opcodes.yaml`（`ld.*`/`st.*`/`ldm.*`/`stm.*`/`jump-rrii`/`br.nz` 的 op/格式/legality）
- 输出：`components/qemu/patches/0004-dadao-load-store.patch`、`components/qemu/patches/series`
- 约束：
  - 大端访问：全部 MemOp 用 `MO_BE*` 变体
  - 有效地址 = `(rbhb + sext12(imms12)) mod 2^48`（高 16 位截断）
  - 多 load/store 在循环前快照 `rdhc`（地址基址），循环内不重新 load
  - ILLI 先于任何寄存器/内存写
  - 本任务不含 RB/RA/RF 存取（RB/**RA** 属 `QEMU-008t`/`QEMU-013t`；RF 按 M1 范围排除）
  - `jump-rrii`/`br.nz` 实现为独立 `trans_*`，仅供 harness trampoline/exit 使用；完整的控制流（`br.*` 全族、`call`/`ret`/`rela`/`swym`）仍在 `QEMU-008t`
  - 完成后不自行 commit

## 背景（完整）

### 目标

实现以下内容的 TCG 语义（ADR-0010 D3 合并任务）：

1. **RD 单次与多次 load/store** 共 22 条 `trans_*`（§4.1）
2. **MALIGN 精确异常**（MO_ALIGN_N + `EXCP_MALIGN` + `cpu_do_unaligned_access` + TEMP_EBB 评估）（§2.6/§9、ADR-0004 D4）
3. **`jump-rrii`** 和 **`br.nz`** 各 1 条 `trans_*`（§5.3/§5.2.3）——前置自原 `QEMU-008t`，解锁 harness e2e（ADR-0010 D1）

使 load/store 正确读写大端内存、MALIGN 精确触发，且 harness 在本任务完成后可端到端跑 RD-only 向量（ADR-0010 D1 修法 a：普通模式不 emit dumper）。

### 设计理由

- 大端 + 48 位有效地址：0.5.3 存储模型规定高 16 位在地址计算时被忽略（§1.5）。
- 对齐即异常：DADAO 的 MALIGN 需映射到 QEMU `MO_ALIGN_N`，由 `cpu_do_unaligned_access` 精确触发，而非 host SIGBUS/SIGSEGV。
- 展开循环：多 load/store 在 C 层展开为 `immu6` 次单次访问，避免生成循环 TCG。
- jump/br.nz 前置：各仅 1 条 `trans_*`，实现简单，前置到本任务使 harness e2e 提前 2 个任务可用。

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

**MALIGN 精确异常**（合并自原 `QEMU-007t`）：
- 定义 `EXCP_MALIGN`（`cpu.h`）：与既有 `EXCP_ILLI`/`EXCP_UNDI` 编号不冲突
- 实现 `cpu_do_unaligned_access`（`cpu.c`）：`cpu_restore_state(cs, retaddr)` → `cs->exception_index = EXCP_MALIGN` → `cpu_loop_exit(cs)`；在 CPUClass 注册 `.do_unaligned_access`
- 补全 `MO_ALIGN_N`：byte 无 / wyde `MO_ALIGN_2` / tetra `MO_ALIGN_4` / octa `MO_ALIGN_8`
- TEMP_EBB 评估：`do_ldm`/`do_stm` 循环内改用 EBB temp（若 QEMU 版本提供 `tcg_temp_ebb_new_i64`）

**`jump-rrii`**（§5.3，前置自 `QEMU-008t`）：
- 语义：`PC = rbha + rdhb + sign_extend(imms12 << 2)`（48 位绝对地址）
- 用途：ROM trampoline → BINARY_BASE 跳转；exit 段跳过 FAIL 代码
- 实现：1 条 `trans_jump_rrii`，TCG 为 `tcg_gen_addi_i64(cpu_pc, rbha, rdhb + sext12<<2)` + `& 0x0000FFFFFFFFFFFF`

**`br.nz rd`**（§5.2.3，前置自 `QEMU-008t`）：
- 语义：`if (rdha != 0) PC = rb0 + sign_extend(imms18 << 2)`
- 用途：exit 段 PASS/FAIL 分支（mismatch 累加器非零 → FAIL 路径）
- 实现：1 条 `trans_br_nz_rd`，TCG 为比较 + 条件分支

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-016a-qemu-load-store.md`（load/store 完整规格）
- DADAO-0628：`code-agent/tasks/DL-016b-qemu-malign-temp-fix.md`（MALIGN 精确异常 + TEMP_EBB）

## 交付物

- `components/qemu/patches/0004-dadao-load-store.patch`：`target/dadao/translate.c`（RD 单/多 load/store + `jump-rrii` + `br.nz`）、`target/dadao/cpu.h`（`EXCP_MALIGN`）、`target/dadao/cpu.c`（`cpu_do_unaligned_access`）
- `components/qemu/patches/series`：加入 `0004`

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`ldbs/ldbu/…` → `ld.sb/ld.ub/…`；`stb/stw/…` → `st.b/st.w/…`；`ldmbs…ldmo` → `ldm.sb/…`；`stmb…stmo` → `stm.b/…`。
2. **opcode/格式**：v5 的 op 分配与 0628 不同，`trans_*` 与 `arg_*` 名按 `QEMU-004t` 的 decodetree 生成结果。
3. **有效地址**：v5 为 48 位有效地址、高 16 位忽略（§1.5）。
4. **对齐与 MALIGN**：v5 的 MALIGN 可观测行为以 `adr-0004-test-machine.md` D4 为准。
5. **RB/RA/RF 存取**：v5 单列 RB（`QEMU-008t`）与 RA（`QEMU-013t`），本任务仅 RD。
6. **jump/br.nz 前置**：v5 按 ADR-0010 D1 将此二指令从 `008t` 前置到本任务。
7. **不复制补丁正文**：0628 的 `0005-dadao-load-store.patch` 属 0.4.1，仅参考实现风格。

## 已知坑 / 结论

摘自 0628 `DL-016a`/`DL-016b` 完成区与 Architecture Review：

1. **MO_ALIGN 全部缺失（P0）**：0628 `DL-016a` 初版未加 `MO_ALIGN_N`，x86 host 上静默放过未对齐访问。v5 必须在本任务补齐。
2. **TEMP_EBB**：0628 `do_ldm`/`do_stm` 循环内用 `tcg_temp_new_i64()`（TEMP_TB），最坏 ~130 temp；v5 须评估 EBB API。
3. **48 位 EA 截断**：地址计算后必须 `& 0x0000FFFFFFFFFFFF`。
4. **`rdhc` 快照**：循环前读取，循环内不重新 load。
5. **大端 MemOp**：全部用 `MO_BE*`，不得用小端 flag。
6. **`cpu_do_unaligned_access` 必须注册**：CPUClass `.do_unaligned_access` 回调未注册则 `MO_ALIGN_N` 不触发异常。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-016a-qemu-load-store.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-016b-qemu-malign-temp-fix.md`
- 本项目：`.tao/knowledge/contract-isa.md` §1.5、§4.1、§5.2.3、§5.3；`contracts/opcodes.yaml`；`.tao/knowledge/adr-0004-test-machine.md`
- 本项目：`.tao/knowledge/adr-0010-qemu-task-restructure.md`（D1/D3）
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | `components/qemu/patches/0004-dadao-load-store.patch` 存在且干净 apply；`series` 已加入 | 现在可跑 | `git am` + `make build-qemu` |
| 2 | RD 单/多 load/store 全部由 ILLI 桩替换为真实 TCG；语义与 §4.1 一致 | 现在可跑 | `make build-qemu` PASS + 代码级逐条核对 §4.1 |
| 3 | 大端 MemOp；48 位 EA 截断；多 load/store `rdhc` 循环前快照 | 现在可跑 | 代码级审查 |
| 4 | ILLI 检查（`rdha==0`、`immu6==0`、`rdha+immu6>64`）先于写 | 现在可跑 | 代码级审查 |
| 5 | 未对齐访问触发 MALIGN 且精确（faulting PC 保持、无寄存器/内存提交）；`EXCP_MALIGN` 定义且 `cpu_do_unaligned_access` 实现并注册 | 现在可跑 | 最小 ROM 探针：构造未对齐 load → 验证退出码 `0x8C` |
| 6 | `jump-rrii` 和 `br.nz` 由 ILLI 桩替换为真实 TCG；语义与 §5.3/§5.2.3 一致 | 现在可跑 | `make build-qemu` PASS + 代码级核对 |
| 7 | `make build-qemu` PASS；`qemu-system-dadao -M ?` 显示约定机器名 | 现在可跑 | 构建 + 冒烟 |
| 8 | **harness e2e RD-only 向量**：`python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml` 全量 PASS | BLOCKED | 原因：harness 普通模式需 `020t` 完成 dumper 改造（D1 修法 a）后方可不 emit dumper 跑通；`014t` 已验证但 dumper 行为未改造。替代：最小 ROM 探针（见下） |
| 9 | **最小 ROM 探针回归**（harness e2e 不可用时的必需运行期证据）：用 `-bios`/`-kernel` 直接运行含本任务指令的最小 ROM（reset PC=ROM base；ILLI→exit `0x88`），验证**合法 load/store 不崩溃**、MALIGN/ROM store/exit port 非法访问等边界退出码正确；探针能区分「正常完成（exit 0x00）」vs「运行时异常（exit 0x80+）」 | 现在可跑 | 手写最小 ROM binary |
| 10 | 完成区含真实构建/运行输出；未自行 commit | 现在可跑 | |

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录