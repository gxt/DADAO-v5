# QEMU-006t: RD Load/Store + MALIGN + jump/br.nz（合并任务）

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-005t`、`SPEC-006t`
**状态**：已验证
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

使 load/store 正确读写大端内存、MALIGN 精确触发；harness 在本任务 **+ `QEMU-020t`（dumper 改造，D1 修法 a：普通模式不 emit dumper）** 完成后可端到端跑 RD-only 内存向量（`mem-rd.yaml`）。

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

- `components/qemu/patches/0004-dadao-load-store.patch`：
  - `target/dadao/translate.c`：RD 单/多 load/store + `jump-rrii` + `br.nz` + `gen_check_exit_port_illi`（stm.* exit port 运行期 ILLI）
  - `target/dadao/cpu.c`：`cpu_do_unaligned_access` 注册到 tcg_ops（003t 产物追加）
  - `target/dadao/helper.c`：ROM store ILLI 检测（003t 产物追加）
  - `hw/dadao/dadao-machine.c`：exit port `.impl.max_access_size=8`（003t 产物追加）
- `components/qemu/patches/series`：加入 `0004`
- `tools/qemu/min_rom_probe_006t.py`：34 个测试用例 + 3 个 CTL self-check

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

- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-016a-qemu-load-store.md`
- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-016b-qemu-malign-temp-fix.md`
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
| 8 | **harness e2e RD-only 内存向量**：`python3 tests/scripts/run_qemu_test.py tests/vectors/isa/mem-rd.yaml` 全量 PASS | BLOCKED | 原因：harness 普通模式需 `020t` 完成 dumper 改造（D1 修法 a）后方可不 emit dumper 跑通；`014t` 已验证但 dumper 行为未改造。替代：最小 ROM 探针（见下） |
| 9 | **最小 ROM 探针回归**（harness e2e 不可用时的必需运行期证据）：用 `-bios`/`-kernel` 直接运行含本任务指令的最小 ROM（reset PC=ROM base；ILLI→exit `0x88`），验证**合法 load/store 不崩溃**、MALIGN/ROM store/exit port 非法访问等边界退出码正确；探针能区分「正常完成（exit 0x00）」vs「运行时异常（exit 0x80+）」 | 现在可跑 | 手写最小 ROM binary |
| 10 | 完成区含真实构建/运行输出；未自行 commit | 现在可跑 | |

## 完成区

**测试结果**：通过 34/34；CTL self-check 正确检测3处注入错误（probe OK）
**修改文件**：
- `target/dadao/translate.c`：22 条 RD 单/多 load/store + jump-rrii + br.nz + set.zw/or.w/andn.w rb + store_rb helper + `gen_check_exit_port_illi`（stm.* exit port 运行期 ILLI，含对齐门控）
- `target/dadao/cpu.c`：dadao_cpu_do_unaligned_access 注册到 tcg_ops（003t 产物，本补丁一并修改）
- `target/dadao/helper.c`：ROM store 检测（tlb_fill 中 MMU_DATA_STORE → ILLI）（003t 产物，本补丁一并修改）
- `hw/dadao/dadao-machine.c`：exit port `.impl.max_access_size=8`，移除 `size==4` hack（003t 产物，本补丁一并修改）
- `components/qemu/patches/0004-dadao-load-store.patch`：737 行
- `components/qemu/patches/series`：加入 0004
- `tools/qemu/min_rom_probe_006t.py`：34 个测试用例 + 3 个 CTL self-check

> 注：`cpu.c`/`helper.c`/`hw/dadao/dadao-machine.c` 原为 003t（target skeleton）产物；本补丁在其上追加 MALIGN 回调注册、ROM store ILLI、exit port max_access_size 等改动，故一并纳入0004 补丁。

**验收结果**：

| # | 验收项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | patch 存在且 git am 干净 apply | PASS | `git am` 四条补丁成功（全新 worktree），4 文件 sha256 与构建源逐一相同，`make build-qemu` PASS |
| 2 | 22 条 RD load/store 由 ILLI 替换为真实 TCG | PASS | translate.c 22 个 trans_*；byte 用 MO_UB/MO_SB（无 MO_ALIGN，符合规格），2B=MO_BE{U,S}W|MO_ALIGN_2，4B=MO_BE{U,S}L|MO_ALIGN_4，8B=MO_BEUQ|MO_ALIGN_8 |
| 3 | 大端 MemOp + 48 位 EA 截断 + rdhc 快照 | PASS | MO_BEUQ/BEUW/BEUL/BESW/BESL；byte 用 MO_UB/MO_SB（大端无区别）；gen_ea_rrii 做 `& 0x0000FFFFFFFFFFFF` |
| 4 | ILLI 检查先于写 | PASS | 所有 trans_* 首行 ILLI 检查 |
| 5 | MALIGN 精确异常 + EXCP_MALIGN + cpu_do_unaligned_access | PASS | 探针 T5/T6/T13/T18/T19/T20/T21 验证 exit=0x8C；**新增 T32/T33/T34 验证未对齐 stm.*→exit = MALIGN 0x8C** |
| 6 | jump-rrii + br.nz 替换为真实 TCG | PASS | jump-rrii: tcg_gen_exit_tb + NORETURN（T25）；br.nz: 翻译期 PC rb0 + 条件 exit_tb（T26/T27） |
| 7 | make build-qemu PASS + qemu-system-dadao -M ? | PASS | 构建 PASS；`-M ?` 显示 `dadao-m1` |
| 8 | harness e2e | BLOCKED | 待 020t dumper 改造 |
| 9 | 最小 ROM 探针回归 | PASS | 34/34 PASS；CTL self-check OK（3处反例：st.o→MALIGN 期望错误 + stm.o→exit PASS 期望错误 + stm.o 未对齐 exit MALIGN 但期望 ILLI） |
| 10 | 未自行 commit | PASS | 未自行 commit |

**005t 探针回归**：20/20 PASS，CTL OK（无回归）

**反例验证**：
```
CTL self-check:
  [FAIL] CTL: st.o PASS but expect MALIGN (wrong): exit=0x00 (expect 0x8C)
  [FAIL] CTL: stm.o exit ILLI but expect PASS (wrong): exit=0x88 (expect 0x00)
  [FAIL] CTL: stm.o unaligned exit MALIGN but expect ILLI (wrong): exit=0x8C (expect 0x88)
  Probe: OK (can detect errors)
```
探针正确检测到3处注入错误：
1. 期望 MALIGN 但实际为 PASS（st.o 合法写入 exit port）
2. 期望 PASS 但实际为 ILLI（stm.o → exit port 被 translate 层运行期检查拦截）
3. 期望 ILLI 但实际为 MALIGN（stm.o 未对齐→exit 应触发 MALIGN 而非 ILLI）

**J6 反例（去掉对齐门控）**：临时回退 `gen_check_exit_port_illi` 到无门控版本（旧版无 N 参数）并增量重编后：
```
  [FAIL] T32 stm.o exit+1 (unaligned) → MALIGN: exit=0x88 (expect 0x8C)
  [FAIL] T33 stm.t exit+2 (unaligned) → MALIGN: exit=0x88 (expect 0x8C)
  [FAIL] T34 stm.w exit+1 (unaligned) → MALIGN: exit=0x88 (expect 0x8C)
  Main results: 31/34 passed, 3 failed
  Overall: FAIL
  CTL: stm.o unaligned exit MALIGN but expect ILLI (wrong): exit=0x88 (expect 0x88) → PASS (probe BROKEN)
```
T32/T33/T34 正确检测到 J6（旧代码无对齐门控，未对齐 stm.*→exit 被 ILLI 抢先返回 0x88 而非 MALIGN 0x8C）；CTL3 也由 FAIL 转 PASS（probe BROKEN），证明门控缺失时探针丧失判别力。恢复后 34/34 PASS，CTL 3/3 FAIL（probe OK）。

**新发现/坑**：
1. **TCG `.impl.max_access_size` 控制 MMIO 拆分**：QEMU TCG 后端按 `.impl.max_access_size`（缺省4）将大访问拆分。设置 `.impl.max_access_size = 8` 可防止64位 MMIO 写入被拆成2×32位，比在 handler 中猜测拆分意图更可靠。
2. **ROM store 需在 tlb_fill 中拦截**：`memory_region_init_rom` 创建的 ROM 区域虽然是只读的，但 TCG 快速路径不检查写权限，store 会直接写入 host 内存。正确做法是在 `dadao_cpu_tlb_fill` 中检测 `MMU_DATA_STORE` 到 ROM 区域并 raise ILLI。
3. **rb0 翻译期常量化**：rb0 = PC，在翻译期已知（`ctx->base.pc_next`），不应从 `env.rb[0]` 读取运行时值（后者仅在 TB 入口更新）。
4. **jump-rrii 必须有 tcg_gen_exit_tb**：`DISAS_NORETURN` 在 `tb_stop` 中不生成出口，必须在 trans 函数中显式调用 `tcg_gen_exit_tb`。
5. **D5.6 优先级**：对齐检查（MALIGN `0x8C`）优先于访问种类检查（ILLI `0x88`）。实现时必须确保 `MO_ALIGN_N` 对齐检查在 ILLI 地址判定之前生效——对未对齐 EA 应放行给 `MO_ALIGN_N` 触发 MALIGN，而非抢先 raise ILLI。
6. **stm.*→exit port 需 translate 层运行期检查**：`.impl.max_access_size=8` 消除 TCG 拆分后，`stm.o` 与 `st.o` 在设备侧生成同一条 8B store，无法区分。ADR-0004 D5.6 要求 ALL `stm.*` → exit port = ILLI，故需在 translate 层对 `trans_stm_*` 循环内每次 store 前做 EA 运行期判定（`gen_check_exit_port_illi`）。使用 `gen_raise_exception_illi`（不设 NORETURN），参照 005t B1/N2 的教训。
7. **对齐门控实现**：`gen_check_exit_port_illi(ctx, ea, N)` 增加 N 参数（元素字节数），当 N>1 时先检查 `ea & (N-1)==0`（自然对齐），未对齐则跳过 ILLI 检查，放行给 `MO_ALIGN_N` 触发 MALIGN。N==1（byte）无对齐要求，直接检查 exit port 范围。这确保了 ADR-0004 D5.6 的判定优先级：对齐 > 访问种类。

**遗留问题**：
- 验收 8（harness e2e）BLOCKED：待 020t dumper 改造后验证
- `add.si rb`（op=0x5B）仍为 ILLI 桩（属 008t 范围）
- `andn.w rb`（translate.c:906）不在 ADR-0010 D1 最小集且 harness 未使用，属范围调整（建议移回 008t 或明确登记）

## 审阅记录

### 第 1 轮 reviewer 验收（2026-09-19）

**判决：Needs Revision（阻断）**

#### 一、重跑记录（本人独立执行，非转述）

| 命令 | 本人真实输出 / 退出码 | 日志 |
|---|---|---|
| `make build-qemu` | 末尾 `build-qemu: PASS`，真实 `exit=0`（`${PIPESTATUS[0]}`） | `.work/log/qemu/QEMU-006t-review-build-qemu.log` |
| 临时 worktree `git am` 0001→0002→0003→0004（从 `c3d48b7`/v11.1.1 起） | 四条均 `exit=0`，无 reject | 终端输出 |
| `python3 tools/qemu/min_rom_probe_006t.py`（engineer 探针） | `Main results: 19/19 passed`；CTL `[FAIL] ... (expect 0x8C)` → `Probe: OK`；`Overall: PASS`，`exit=0` | `.work/log/qemu/QEMU-006t-review-probe.log` |
| 反例：把 `trans_ld_o_rd` 临时回退为 ILLI 桩并增量重编 | probe `15/19 passed, 4 failed`（T3/T4/T5/T6 失败）、`Overall: FAIL`、`exit=1`；随后恢复并重编，probe 复 `19/19 PASS` | `...-probe.log`；`/tmp/opencode/QEMU-006t/` |
| 本人独立边界 ROM（`/tmp/opencode/QEMU-006t/edge*.py`，复用 006t 编码器自建 ROM） | 见「二、阻断问题」E4/E8/E9/E11/E12/F1/F2/F4 等 | `.work/log/qemu/QEMU-006t-review-edge{,2,3}.log` |
| 本人 `rb0` 语义探针（branch@0x20，imms18=3） | 实得 `0x12`（落 0x24）；正确契约应为 `0x13`（落 0x2c） | `.work/log/qemu/QEMU-006t-review-rb0.log` |
| 本人 jump-rrii 端到端（`jump rb2(RAM),rd0,0` → RAM PASS 代码） | `returncode = -6`（SIGABRT）：`cpu-exec.c:911: cpu_loop_exec_tb: Assertion 'icount_enabled()' failed.` | `.work/log/qemu/QEMU-006t-review-jump-ram.log` |
| 反例：把 exit-port handler 回退为 003t 形式（`size!=8→ILLI`） | `st.o` 到 exit port → `exit=0x88`（证明 TCG 确实把 8B MMIO 拆成 2×4B；改动必要） | `.work/log/qemu/QEMU-006t-review-exitport-revert.log` |

#### 二、阻断问题（必须修复）

**J1（阻断）`trans_jump_rrii` 无 TB 出口 → 执行即 SIGABRT（违反验收 6）**
- 文件:行号：`target/dadao/translate.c:1298-1318`，尤其 `1318: ctx->base.is_jmp = DISAS_NORETURN;` **之前没有 `tcg_gen_exit_tb`**；`dadao_tr_tb_stop`（`translate.c:3610-3619`）对 `DISAS_NORETURN` 不生成出口。
- 证据（本人重跑）：ROM 仅 `jump rb2(0x0000FFFF_0000_0000=R腔RAM), rd0, 0`，kernel 为 PASS 代码 → `returncode=-6`，`Assertion 'icount_enabled()' failed`。这也正是任务书遗留「未端到端测试 jump-rrii」与 ADR-0010 D1「前置 jump/br.nz 解锁 harness e2e」的缺口：harness `gen_trampoline.py:12` 的 `jump rb2, rd0, 0` 会崩溃。
- 对照上游：`target/xtensa/translate.c:349-364 gen_jump_slot` 先 `tcg_gen_exit_tb` 再设 NORETURN。修复建议：`tcg_gen_exit_tb(NULL, 0)`（或 `ctx->base.is_jmp = DISAS_TOO_MANY` + goto_tb）后再置 NORETURN。

**J2（阻断）`rbo`（env.rb[0]）在 TB 内不逐指令更新 → `br.nz`/`jump-rrii` 目标算错（违反验收 6；题面疑点 3 的隐藏问题）**
- 文件:行号：`translate.c:1239-1243`（`trans_br_nz_rd` 读 `env.rb[0]`）；`rb[0]` 仅在 `cpu.c:29-35`(set_pc)、`63-71`(synchronize_from_tb)、`73-81`(restore_state_to_opc) 更新，TB 内部从不更新。
- 证据（本人重跑）：branch 在 0x20、`imms18=3` 时契约 `target = PC+12 = 0x2c`(应出 0x13)，实测 `0x12`（落 0x24）——即 `rb0 = TB 起始 PC`。`in_asm` 亦显示该程序被反复从 TB 起点重入直至凑巧收敛。harness `build_test_binary.py:337` 的 `jump rb0, rd0, 3`、`br.nz rd61, 4` 依赖 `rb0 = 当前 PC`，故 harness 退出段同样不正确。
- 修复建议：用翻译期常量 `ctx->base.pc_next - 4`（当前指令地址）作 rb0（`tcg_constant_i64`），不要读运行时 `env.rb[0]`；或每指令同步 `rb[0]`。

**J3（阻断）`trans_st_o_rd` 缺 `MO_ALIGN_8` → 未对齐单次 `st.o` 不触发 MALIGN（违反验收 2/5）**
- 文件:行号：`translate.c:435 tcg_gen_qemu_st_i64(val, ea, ctx->memidx, MO_BEUQ);`（对比 `ld.o` 425、`ldm.o` 695、`stm.o` 714 均带 `MO_ALIGN_8`）。`series`/0004 补丁第 269 行同样缺。
- 证据（本人重跑）：`st.o rd18=0x42, (RAM)+1` → `0x89`（应 `0x8C`）；`+4` → `0x89`（应 `0x8C`）；`st.o …, exit+4` → `0x00`（应 `0x8C`）。engineer 探针无未对齐单次 `st.o` 用例，故 19/19 为**覆盖缺口导致的假通过**。

**J4（阻断，ADR-0004 D3/D5.6 违反）exit-port handler 改动接受真实的非 8B 访问（题面疑点 1）**
- 文件:行号：`hw/dadao/dadao-machine.c:76-81`（`else if (size == 4 && addr == 4)` 直接按正常 exit 处理）。
- 证据（本人重跑，均以 `st.t`/`stm.o` 单次 4B/8B 访问打到 `0xffff_8000_0004`）：
  - `st.t rd18=0x42, exit+4` → `0x42`（D3 要求 **ILLI 0x88**）；
  - `stm.o rd18=0x42, rb16, immu6=1` → `0x42`（D5.6 要求 `stm.*` → **ILLI 0x88**）。
  故该改动把「第二个拆分半字」与「guest 真实 4B 非 8B 访问」混为一谈，破坏 D3 冻结行为。
- 该改动**确实必要**：本人把 handler 回退为 003t `size!=8→ILLI` 后，合法 `st.o` 到 exit port 即 `exit=0x88`（TCG 拆分为 `(addr=0,size=4)+(addr=4,size=4)`，机制见 `system/memory.c:541-542,559-570,1550-1554`，`.impl.max_access_size` 缺省为 4）。此外第一次拆分半字会先发 `SHUTDOWN_CAUSE_GUEST_PANIC/0x88`，仅靠第二次调用「后写覆盖」才得正确码，实现脆弱。
- 正确修法（供架构师定夺，勿自行实施）：设备侧无法区分 `st.o` 与 `stm.o`（生成同一条 8B store）；应在 translate 层对 `stm.*` 目标地址做运行期 exit-port 检查（→ ILLI），或用 `.impl.max_access_size=8` 消除拆分并在设备侧仅接受 `size==8`。无论哪种，均超出本任务交付物清单，须登记。

**J5（验收 9 声称过宽）ROM store 未映射为 ILLI，且探针无对应用例**
- 证据（本人重跑）：`st.o rd19=0x42, ROM base` 后接显式 PASS 写 → `exit=0x00`（D5.6 要求 ROM store → **ILLI 0x88**）。责任代码在 `target/dadao/helper.c:104-108`（ROM prot=READ|EXEC，未对写做处理，属 003t），但验收 9 明写「ROM store … 边界退出码正确」，探针无此用例，完成区「边界退出码正确」无证据。

#### 三、题面三处疑点判定

1. **`hw/dadao/dadao-machine.c` 改动**：(a) **必要**（回退即 `st.o→0x88`，见 J4）；但实现**不正确**，使 D3/D5.6 对 `st.t`/`stm.*` 失效（J4），且依赖「后写覆盖」。是否「TCG 拆 8B MMIO 为 2×4B 为正常行为」→ 是，`.impl.max_access_size` 缺省 4（`memory.c:541`）。(b) **是**，破坏 D3：guest `st.w` 到 exit+0/+4 仍正确（size 2 不触发该分支），但 guest `st.t` 到 exit+4 与 `stm.o` 均被当合法退出（`0x42`）。(c) **应登记**：任务书交付物仅列 `translate.c/cpu.h/cpu.c`，实际改了 `hw/dadao/`，完成区仅在「新发现」提及，未进入交付物/补丁说明的正式范围。
2. **`set.zw-rb`/`or.w-rb`**：**合理的范围调整**。ADR-0010 D1 最小可用集表列 `set.zw rd/rb` + `or.w rd/rb`（原归 005t「不变」），而 005t 仅做 rd，harness `gen_trampoline.py:12-17` 实际使用 rb 形式；编码与 `contracts/opcodes.yaml`（`set.zw-rb` op=0x4E、`or.w-rb` op=0x4A、wpN=[17:16]、immu16_hi/mid/lo）一致，`translate.c:847-877` 的 `wp=hb>>4`、`immu16=((hb&0xF)<<12)|(hc<<6)|hd` 正确。**但** `andn.w-rb`（`translate.c:880`）既不在 D1 最小集、也不被 harness 使用，属额外范围，完成区未登记，建议移回 008t 或明确登记。
3. **`br.nz` 的 TB 处理**：条件退出的**技术**正确（taken 用 `tcg_gen_exit_tb`、not-taken 自然继续、未设 `is_jmp=NORETURN` → 未重蹈 005t B1；本人跑 taken/not-taken 均无 SIGABRT、退出码确定）。**但目标地址错误**（读 TB 起始 PC，见 J2），因此不能判为「正确」；`jump-rrii` 则连 TB 出口都缺（J1）。

#### 四、验收表逐条复核

| # | 结论 | 依据 |
|---|---|---|
| 1 | ✅ | `git am` 四项干净、`make build-qemu` PASS，series 含 0004 |
| 2 | ❌ | 22 条 trans_* 确已替换（`translate.c:317-714`，`grep -c`=22），但 `st.o-rd` 缺 `MO_ALIGN_8`（J3） |
| 3 | ✅（有注） | 全 `MO_BE*`（byte 用 `MO_UB`/`MO_SB`）；`gen_ea_rrii` 做 `& 0x0000FFFFFFFFFFFF`；`ldm/stm` 循环前 `load_rd(a->hc)` 快照；唯一例外见 J3 |
| 4 | ✅ | 单/多 ILLI 检查均在 EA/写之前（`translate.c:317,485,701` 等） |
| 5 | ❌ | `EXCP_MALIGN` 定义于 003t `cpu.h:39`、回调注册于 `cpu.c:227` ✅；但未对齐单次 `st.o` 不触发 MALIGN（J3） |
| 6 | ❌ | `jump-rrii` SIGABRT（J1）、`br.nz` 目标错（J2） |
| 7 | ✅ | 构建 PASS；`qemu-system-dadao -M ?` 显示 `dadao-m1` |
| 8 | ✅（诚实） | BLOCKED 如实标注，原因成立；但即使 020t 完成，J1 也会使 harness 崩溃 |
| 9 | ❌ | 探针 19/19 PASS 属实且 CTL 能报错（我已复核反例），但**未覆盖**未对齐单次 `st.o`、jump-rrii e2e、ROM store，故漏掉 J1/J3/J5，不能支撑「边界退出码正确」 |
| 10 | ⚠️ | 未 commit ✅；但证据「git status 无未提交改动」与真实不符（实际有 task 文件、series 修改 + patch/probe 未跟踪） |

#### 五、反例门控（AGENTS「验证脚本反例门控」）

- **CTL 自检**：本人重跑见到 `[FAIL] CTL: st.o PASS but expect MALIGN (wrong): exit=0x00 (expect 0x8C)` + `Probe: OK`，说明探针对错误期望值会 FAIL。
- **回退为桩**：本人将 `trans_ld_o_rd` 临时改为 ILLI 桩并增量重编，探针 `15/19`、`Overall: FAIL`、`exit=1`（T3/T4/T5/T6 失败）；随后恢复、重编、probe 复 `19/19 PASS`（`.work/source/qemu` 已确认 `git status` 干净、`translate.c` sha256 复原）。探针本身有效，**问题在于覆盖不全**（J3/J1/J5 无用例）。
- 未发现改 contract/spec/向量/测试来凑绿：主仓 `git status` 仅本任务产出（task 文件、series、0004 patch、probe 脚本）。

#### 六、范围外桩核验

RB/RA 存取（`ld_o_rb/ra`、`ldm_o_rb/ra`、`st_o_rb/ra`、`stm_o_rb/ra`）、`br.*` 全族（含 `br_z_rb`/`br_nz_rb`）、`jump_iiii`/`call_*`/`ret_riii`/`rela_si_rb` 均仍为 ILLI 桩（共 108 个 stub，逐个 grep 确认）✅。`swym_iiii` 为 004t 既有 NOP，非本任务改动。

#### 七、结论

构建、patch 集、22 条 RD load/store 主体、ILLI 次序、48 位 EA、`rdhc` 快照、MALIGN 注册与外范围桩达标；但存在 **J1（jump-rrii SIGABRT）**、**J2（rb0 错误 → br.nz/jump 目标错）**、**J3（st.o 缺 MO_ALIGN_8）** 三个运行期缺陷，**J4（exit-port 改动破坏 ADR-0004 D3/D5.6）**，以及 J5/完成区若干不实表述 → **Needs Revision**。返工后须重跑：`make build-qemu` + 本人边界 ROM（含未对齐单次 `st.o`、jump-rrii/br.nz 端到端、`st.t`/`stm.*` 与 ROM store 到 exit port/ROM 的边界码）+ harness e2e（若 020t 就绪）。

### 第 2 轮 reviewer 验收（2026-09-19）

**判决：Needs Revision（阻断：J4 未完全修复）**

J1/J2/J3/J5 已修复，本人独立重跑确认；但 **J4 只修了一半**——`st.t`/`st.w`/`st.b`/`stm.b/w/t`/`ld.*`/`ldm.*` → exit port 已恢复 ILLI `0x88`，而 **`stm.o`（8B 多寄存器 store）→ exit port 仍被当作合法退出**（返回写入值，如 `0x42`），违反 ADR-0004 D3/D5.6 冻结行为，且完成区未登记。探针 T22/T23 只测单次 `st.t`，无 `stm.o`→exit 用例，故 27/27 漏检该点。

#### 一、重跑记录（本人独立执行，全部真实输出 / 退出码）

| 命令 | 本人真实输出 / 退出码 | 日志 |
|---|---|---|
| `make build-qemu` | 末尾 `build-qemu: PASS`，`exit=0` | `.work/log/qemu/QEMU-006t-review2-build-qemu.log` |
| `python3 tools/qemu/min_rom_probe_006t.py` | `Main results: 27/27 passed`；CTL `[FAIL] ... (expect 0x8C)` → `Probe: OK`；`Overall: PASS`，`exit=0` | `...-review2-probe.log` |
| 本人自建落点测试 `/tmp/opencode/QEMU-006t/landing_test.py`（每 4B 槽一个唯一退出码探针） | `Landing/J1 results: 6/6 OK`，`exit=0`（详见 J2） | `...-review2-landing.log` |
| 本人自建边界测试 `/tmp/opencode/QEMU-006t/boundary_test.py`（39 例） | `results: 36/39 OK`；3 例 FAIL 均为 `stm.o`→exit（详见 J4），`exit=1` | `...-review2-boundary.log` |
| `python3 tools/qemu/min_rom_probe_005t.py`（回归） | `Main tests: 20/20`、`CTL probe: OK`、`Overall: PASS`，`exit=0` | `...-review2-probe-005t.log` |
| `qemu-system-dadao -M ?` | `dadao-m1  DADAO M1 bare-metal test machine`，`rc=0` | `...-review2-machines.log` |
| 全新 worktree `c3d48b7` + `git am` 0001→0002→0003→0004 | `am_rc=0`，无 reject；四文件 sha256 与构建源一致 | `...-review2-gitam.log` |
| 反例：临时删除 `trans_st_o_rd` 的 `MO_ALIGN_8` 且删除 `trans_jump_rrii` 的 `tcg_gen_exit_tb` 后增量重编 | probe `24/27`：`T20/T21 FAIL exit=0x89 (expect 0x8C)`、`T25 FAIL exit=0x-6`（SIGABRT），`Overall: FAIL` | `...-review2-ctl-build.log` / `...-review2-ctl-probe.log` |
| 恢复源文件（sha256 复原 `e8733cc9…`）并重编 | probe 复 `27/27 PASS`，`exit=0` | `...-review2-restore-build.log` / `...-review2-probe-after-restore.log` |

#### 二、逐条验证

**J1（jump-rrii TB 出口）——已修复 ✅**
- 代码：`translate.c:1325 tcg_gen_exit_tb(NULL, 0);` 在 `1326 ctx->base.is_jmp = DISAS_NORETURN;` **之前**。
- 本人端到端：ROM `jump rb2(RAM base),rd0,0` → RAM 内核（`set.zw rb16…; st.o rd18=0, exit`）得 `exit=0x00`；内核改 `rd18=0x5A` 得 `exit=0x5A`（证明真实跳转，非仅"不崩"）。旧 J1 的 `returncode=-6` 未再出现。
- **「修一类」核对**：全文件仅 3 处 `is_jmp = DISAS_NORETURN`——`translate.c:63/76`（`gen_exception_illegal`/`gen_exception_undi`，前面是 `gen_helper_raise_exception`，helper 内 `cpu_loop_exit`，无需 `exit_tb`）与 `1326`（jump-rrii，已有 `exit_tb`）；PC 写入仅 `translate.c:1257-1258`（br.nz taken，后接 `1260 exit_tb`）与 `1322-1323`（jump-rrii）。无第二处"无条件跳转却缺出口"。✅

**J2（rb0 = 当前 PC）——已修复，落点逐字节一致 ✅**
- 语义依据（源码级）：`dadao_tr_translate_insn`（`translate.c:3608-3615`）以 `ctx->base.pc_next` 取指、**之后**才 `pc_next += 4`，故 `trans_*` 内 `pc_next` = **当前指令地址**。engineer 的 `tcg_constant_i64(ctx->base.pc_next)` 正确（非 pc+4）。
- **落点逐字节比对**（每 4B 槽独立 `st.o rdK,rb16,0` 探针，rd20..rd27 = 0x20..0x27；退出码直接编码落点槽号）：
  - `br.nz rd18=1, imm=1` @ `0xffffffff003c` → 契约 target `0xffffffff0040`，**实测 exit `0x20`**（落第 1 槽）；若误用 pc+4 应得 `0x21`。
  - `br.nz rd18=1, imm=3` @ `0xffffffff003c` → 契约 target `0xffffffff0048`，**实测 exit `0x22`**（落第 3 槽）；若 pc+4 应得 `0x23`。
  - `br.nz rd18=0（not-taken）` @ `...003c` → **实测 exit `0x20`**（落 fall-through 第 1 槽）；若误 taken 应得 `0x22`。
  - `jump rb0,rd0,imm=1` @ `0xffffffff0038` → 契约 target `0xffffffff003c`，**实测 exit `0x20`**。
  - `jump rb0,rd0,imm=3` @ `0xffffffff0038` → 契约 target `0xffffffff0044`，**实测 exit `0x22`**。
- `-d cpu` 交叉证据：br.nz imm=3 的 dump 中 `PC: 0000ffffffff0048` 且 `RB[00]: 0000ffffffff0048`；jump rb0 imm=3 为 `PC/RB[00]: 0000ffffffff0044`——与手算**完全一致**（证据文件 `/tmp/opencode/QEMU-006t/{brnz,jump-rb0}-imm3-dcpu.log`）。
- 无 off-by-4。

**J3（MO_ALIGN）——已修复 ✅**
- 代码级逐条：22 条 RD load/store 的 `tcg_gen_qemu_{ld,st}_i64` MemOp 全部与 §4.1 期望一致（`translate.c:328…720`）；`trans_st_o_rd` 为 `441: MO_BEUQ | MO_ALIGN_8`（旧缺）。byte 用 `MO_UB`/`MO_SB`（无 align，符合规格），2B=`MO_BE{U,S}W|MO_ALIGN_2`，4B=`MO_BE{U,S}L|MO_ALIGN_4`，8B=`MO_BEUQ|MO_ALIGN_8`。22/22 OK，0 mismatch。
- 运行期：`st.o` 到 `RAM+1` / `RAM+4` → **`0x8C`**（j3 修复生效）；`ld.o RAM+1` → `0x8C`。

**J4（exit port）——未完全修复 ❌（阻断）**
- 代码：`hw/dadao/dadao-machine.c:87 .impl.max_access_size = 8;`，`70: if (size != 8) → ILLI`，`size==4 && addr==4` hack 已移除 ✅。
- 原 J4 失败项（`st.t`→exit+4）已恢复：`st.t`/`st.w`/`st.b`（exit+0/+4）、`stm.b/w/t`、`ld.*`、`ldm.*` → **均 `0x88`** ✅；合法 `st.o` → exit 值（`0x00`/`0x5A`/`0x42`）✅；未对齐 exit → `0x8C` ✅。
- **残余违规**：`stm.o`（rrri，`immu6≥1`，生成 8B store）→ exit port **得写入值 `0x42`，而非 D5.6 要求的 `0x88`**。真实输出（本人重跑）：
  - `exit: stm.o x1 -> ILLI  got 0x42 (expect 0x88)`
  - `exit: stm.o x2 -> ILLI  got 0x42 (expect 0x88)`
  - `exit(rb18=exit port): stm.o x1 -> ILLI  got 0x42 (expect 0x88)`
- 根因：`.impl.max_access_size=8` 消除了 TCG 拆分，设备侧唯一可判据是 `size`；而 `st.o` 与 `stm.o` 在 `translate.c` 生成**同一条 8B store**（`trans_stm_o_rd`，`translate.c:707-723`，无 exit-port 地址检查），设备无法区分。这正是第 1 轮 J4 预测的「设备侧不可区分」问题，改 `max_access_size` 只解决了「拆分半字」的一半，`stm.*→ILLI` 仍缺 translate 层运行期检查。
- 由于 `stm.*→ILLI` 是 ADR-0004 **D3/D5.6 冻结项**、且为本轮 J4 明确验收项，判阻断。修法（供架构师定夺）：在 `trans_stm_*`（至少 `stm.o`）store 前对 EA 落入 `[0xffff80000000, +8)` 做运行期判断 → 抛 ILLI；或在 ADR 层面正式登记为已知偏差并给出归属任务。

**J5（ROM store）——已修复 ✅**
- 代码：`helper.c:109` 对 `MMU_DATA_STORE` 到 ROM 抛 `DADAO_EXCP_ILLI`。
- 运行期：ROM 对齐 store `st.o rb0+4/+12`、`st.b rb0+0`、`st.w rb0+2`、`stm.o rb0+16` → **均 `0x88`** ✅；ROM 未对齐 `st.o rb0+5` → `0x8C`（MALIGN 优先级正确）✅；ROM 读 `ld.o rb0+8` 允许（随后 PASS）✅。
- 登记：完成区「修改文件」已列 `target/dadao/helper.c` / `hw/dadao/dadao-machine.c`；但「交付物」段（任务书 96-99 行）仍只列 `translate.c/cpu.h/cpu.c`，未把 `helper.c`、`hw/dadao/dadao-machine.c` 纳入正式交付物，也无与 003t 产物的关系说明。**部分登记**（不单独阻断，建议随 J4 返工一并补全）。

#### 三、探针效力（AGENTS「验证脚本反例门控」）

- **CTL 自检**：本人重跑见 `[FAIL] CTL: st.o PASS but expect MALIGN (wrong): exit=0x00 (expect 0x8C)` + `Probe: OK`，探针对错误期望值会 FAIL。
- **自造反例（实现回退）**：本人把 `trans_st_o_rd` 的 `MO_ALIGN_8` 删除、并删除 `trans_jump_rrii` 的 `tcg_gen_exit_tb`，增量重编后 probe：`T20/T21 FAIL exit=0x89 (expect 0x8C)`、`T25 FAIL exit=0x-6`（SIGABRT）、`Overall: FAIL`。**证明新增 T20/T21/T25 确有判别力**；随后 `git checkout` 复原（sha256 复原）、重编、probe 复 `27/27 PASS`。
- **T20–T27 真实性**：本人对每个新用例独立重算并另建等价 ROM 复跑（落点/J3/J4/J5 各项见上），与 engineer 期望一致。`stm.o`→exit 是本轮唯一未被探针覆盖的 J4 点（T22/T23 仅单次 `st.t`）。
- 未发现改 contract/spec/向量/测试凑绿：主仓 `git status` 仅 006t 产出（task 文件、series）+ 未跟踪 patch/probe。

#### 四、完成区准确性

| 声明 | 核对 |
|---|---|
| patch `684` 行 | ✅ `wc -l`=684 |
| 22 条 trans_* 由 ILLI 替换 | ✅ 22 个 trans_*（本任务范围） |
| 「22 个 trans_*，全部含 MO_ALIGN_N」 | ⚠️ 措辞不实：byte 类正确无 `MO_ALIGN`（规格如此）；证据里写的 `MO_BESB` 非真实 MemOp 名 |
| 修改文件清单（translate/cpu/helper/machine/patch/series/probe） | ✅ 与实际 patch 触及文件一致 |
| 探针 27/27 + CTL OK；005t 20/20 | ✅ 本人重跑一致 |
| 「移除 size==4 hack」 | ✅ 源码已无 |
| 「构建 28/28」 | ⚠️ 本机实测 `[29/29]`（configure 步数计数，无关紧要） |
| 遗留「`andn.w rb`（translate.c:880）」 | ⚠️ 行号已陈旧，实际 `translate.c:886` |
| 未自行 commit | ✅ 无新 commit |

#### 五、验收表逐条复核

| # | 结论 | 依据 |
|---|---|---|
| 1 | ✅ | `git am` 四补丁 `rc=0`（全新 worktree），`make build-qemu` PASS |
| 2 | ✅ | 22 条 MemOp 逐条 OK（含 `st.o` `MO_ALIGN_8`） |
| 3 | ✅ | 全 `MO_BE*`（byte `MO_UB/MO_SB`）；48 位截断；`rdhc` 快照 |
| 4 | ✅ | 单/多 ILLI 检查先于写 |
| 5 | ✅ | MALIGN（`st.o` +1/+4 = `0x8C`）；`EXCP_MALIGN` 定义/注册（003t 既存） |
| 6 | ⚠️→需重判 | jump-rrii/br.nz 已修复且落点逐字节正确 ✅；但实现被 J4 的 exit-port 违规旁及（exit 协议是 br.nz 的观测通道），待 J4 修复后一并复验 |
| 7 | ✅ | `-M ?` 含 `dadao-m1` |
| 8 | ✅（诚实） | BLOCKED 如实 |
| 9 | ❌ | 27/27 PASS 属实、CTL 有效、新用例有判别力，但**无 `stm.o`→exit 用例**，故漏检 J4 残余 |
| 10 | ✅ | 未 commit |

#### 六、结论

J1（jump-rrii SIGABRT）、J2（rb0 落点，已 `-d cpu` 逐字节确认无 off-by-4）、J3（22/22 MemOp）、J5（ROM store→ILLI）均**已修复**；构建/patch/005t 回归/`-M ?` 达标。**阻断项：J4 残余——`stm.o` → exit port 未被识别为 ILLI，返回写入值 `0x42`，违反 ADR-0004 D3/D5.6**；且探针未覆盖该点、完成区未登记。**判 Needs Revision**。返工后须：修 `stm.*`→exit 的运行期 ILLI（translate 层地址判定，或由架构师正式登记偏差）；在探针补 `stm.o`→exit 用例；补全交付物/003t 关系登记与陈旧行号。harness e2e 仍 BLOCKED（020t）。

### 第 3 轮 reviewer 验收（2026-09-20）

**判决：Needs Revision（阻断：新增 J6——未对齐 `stm.*` 打到 exit port 时 MALIGN 被 ILLI 抢占）**

J4 主体**已修复**：`stm.b/w/t/o` → exit port 全部 `0x88`；合法 `st.o` → exit、合法 `stm.*` → RAM 均正常；J1/J2/J3/J5 无回归；探针 31/31 与反例有效性均属实。**但 J4 的修法把运行期 exit-port 检查放在 `MO_ALIGN_N` 之前**，使未对齐的 `stm.*` 打到 exit port 时返回 ILLI `0x88`，而 ADR-0004 D5.6 判定优先级要求 MALIGN `0x8C`（任务书「已知坑 #5」亦明确「对齐检查优先于访问种类检查」）。违反验收 5 与冻结的 D5.6 → Needs Revision。

#### 一、重跑记录（本人独立执行，真实输出/退出码）

| 命令 | 本人真实输出/退出码 | 日志 |
|---|---|---|
| 全新 clone + `git checkout c3d48b7` + `git am` 0001→0004 | 四条 `am_rc=0`，无 reject | `.work/log/qemu/QEMU-006t-review3-gitam.log` |
| 与构建源比对 sha256（4 文件） | clean-apply 后 4 文件 sha256 与 `.work/source/qemu` 工作树**逐一相同**（`translate.c`=`102280adee…`） | `...-src-hashes.log` |
| `make build-qemu` | `build-qemu: PASS`，真实 `exit=0`（含 J4 修复；`ninja: no work to do`） | `...-review3-build-qemu.log` |
| `qemu-system-dadao -M ?` | `rc=0`，`dadao-m1  DADAO M1 bare-metal test machine` | `...-machines.log` |
| `python3 tools/qemu/min_rom_probe_006t.py` | `Main results: 31/31 passed, 0 failed`；CTL 两项 `[FAIL] … (expect 0x8C/0x00)` → `Probe: OK`；`Overall: PASS`，`exit=0` | `...-engineerprobe.log` |
| `python3 tools/qemu/min_rom_probe_005t.py` | `Main tests: 20/20`、`CTL probe: OK`、`Overall: PASS`，`exit=0` | `...-probe-005t.log` |
| **本人自建独立探针** `/tmp/opencode/QEMU-006t/review3_probe.py`（42 例，编码独立派生自 `contracts/opcodes.yaml`，未 import engineer 脚本） | `39/42 passed`，3 例 FAIL 全为 PRIO（见 J6） | `...-ownprobe.log` / `...-ownprobe-after-restore.log` |
| 确定性：`stm.o`→exit 同一 ROM ×10 | `[136]*10`，`distinct:[136]`，无 SIGABRT | `...-determinism.log` |
| `-d exec`（`-D` 文件 + `-monitor none -serial none`，×6） | 每次**恰好 2 条 TB 执行**（`0xffffffff0000`、`0xffffffff0018`），无 TB 起点重放 | `...-dexec-stmo-exit.log`；终端 |
| 反例：删除 4 处 `gen_check_exit_port_illi` 调用 + 增量重编 | engineer 探针 `30/31`（`T28 FAIL exit=0x42`；T29–T31 仍 PASS，设备兜底）；本人探针 `stm.o`→exit 全 `0x42`、**PRIO 三项转 `0x8C`** | `...-ctl-build.log` / `...-ctl-engineerprobe.log` / `...-ctl-ownprobe.log` |
| 恢复备份（sha256 复原 `102280adee…`）并重编 | build PASS；engineer 探针复 `31/31`；本人探针复 `39/42` | `...-restore-build.log` / `...-probe-after-restore.log` |
| 22 条 `trans_*` MemOp 逐条提取比对 | `22/22 OK, 0 mismatch`；范围内无残留 ILLI 桩 | `...-memops.log` |
| 范围外桩清单提取 | RB/RA/RF load/store、`br.*`（除 `br.nz-rd`）、`jump_iiii`/`call_*`/`ret_riii`/`rela_si_rb`/`add.si_rb` 共 26+ 项仍 ILLI 桩 | `...-stubs.log` |

#### 二、J4 独立复现（本人自建探针，不采信 engineer）

- **`stm.*` → exit port 全 `0x88`** ✅：`stm.b`/`stm.w`/`stm.t`/`stm.o`（原 J4 残余）均 `rc=0x88`；`stm.o` 经 `rdhc` 偏移/多元素/`base=exit+7` 等路径亦 `0x88`。
- **合法 `st.o` → exit** ✅：值 `0x00`/`0x42`/`0x7F` 分别得 `0x00`/`0x42`/`0x7F`（正常退出码，未被 ILLI 误拦）。
- **合法 `stm.*` → RAM** ✅：`stm.b/w/t/o`(1 元素) → RAM → 对应 `ldm.*` 回读 → `st.o` 出值 `0x42`。
- **单次 `st.b/w/t` → exit = ILLI** ✅（设备 handler 兜底）；`st.t`→exit+4 亦 `0x88`。
- **`ld.*`/`ldm.o` → exit = ILLI** ✅（设备读 handler）。
- 结论：第 2 轮 J4 残余（`stm.o`→exit 返回 `0x42`）**已修复**。

#### 三、J6（阻断）未对齐 `stm.*` → exit port 返回 ILLI `0x88`，应为 MALIGN `0x8C`

- 违反依据：ADR-0004 D5.6「判定优先级」明确 **2. 对齐（MALIGN `0x8C`）先于 3. 访问种类/宽度（ILLI `0x88`）**；矩阵「Exit port … 未对齐 load/store」列 = **MALIGN `0x8C`**。任务书「已知坑 #5」原文亦写「对齐检查（MALIGN）优先于访问种类检查（ILLI）」。
- 责任代码：`target/dadao/translate.c:78-87 gen_check_exit_port_illi()`（0004 补丁 `+119`），在 `MO_ALIGN_N` 之前调用（调用点 `translate.c:662/681/700/738`，对应 store `664/683/702/740`）。
- 本人重跑（真实输出，`...-ownprobe.log`）：
  ```
  [FAIL] PRIO stm.o exit+1 (unaligned): rc=0x88 (expect 0x8C)
  [FAIL] PRIO stm.t exit+2 (unaligned): rc=0x88 (expect 0x8C)
  [FAIL] PRIO stm.w exit+1 (unaligned): rc=0x88 (expect 0x8C)
  ```
  （`stm.o`/`stm.t`/`stm.w` 各以 `rdhc=1/2/1` 使 EA=exit+1/+2/+1，均为未对齐访问。）
- **因果证明**（`...-ctl-ownprobe.log`）：临时删除 4 处 `gen_check_exit_port_illi` 调用后，同 3 例**转 PASS `0x8C`**（对齐检查正常触发）；恢复后复 FAIL —— 确认 `0x88` 由新增检查抢先所致。
- 影响：验收 5（「未对齐访问触发 MALIGN 且精确」）在该角落不成立；这是本轮 J4 修法**新引入**的回归（修复前该角落为 `0x8C`）。
- 修复建议（供架构师定夺，勿由 reviewer 实施）：`gen_check_exit_port_illi` 增加自然对齐门控——仅当 `ea` 自然对齐（`ea & (N-1) == 0`，N=元素字节数）时才 raise ILLI，否则放行到 `MO_ALIGN_N` → MALIGN；或在 TCG 中把对齐判定排在该检查之前。相应在探针补 `stm.o/t/w` 未对齐→exit 用例。

#### 四、运行期路径（005t B1/N2 核查）

- `gen_raise_exception_illi` 不设 `is_jmp`，helper `helper_raise_exception`（`helper.c:141-147`）用 `cpu_loop_exit_restore(cs, GETPC())`（N2 标准修法），故不重蹈 B1。
- `stm.o`→exit ×10 退出码恒 `136`，无 `-6`（SIGABRT）。
- `-d exec` 6/6 仅 2 条 TB 执行、无起点重放。
- ⚠️ 注：以 `-nographic` + Python `capture_output` 抓 `-d exec` 时曾见同 TB 行重复（2 vs 112 行不等），改用 `-D <file> -monitor none -serial none` 后稳定为 2 行 —— 系 monitor/stdio 交错假象，非 TB 重放。

#### 五、「修一类」核对

- 需要改的变体：AD 中 exit-port store 约束为「非 8B `st.b/w/t` 或 `stm.*` → ILLI」。单次 `st.b/w/t` 由设备 `size!=8` 兜底（本人复跑 `0x88` ✅）；`ld.*`/`ldm.*` 由设备读 handler 兜底（`0x88` ✅）；仅 `stm.*` 需 translate 层检查，已覆盖 4/4 变体 ✅。
- **但**这 4 处检查的对齐优先级错误（J6），属同一修法的系统性缺陷，须「修一类」。

#### 六、探针效力（AGENTS「验证脚本反例门控」）

- CTL：本人重跑见 `[FAIL] CTL: st.o PASS but expect MALIGN` + `[FAIL] CTL: stm.o exit ILLI but expect PASS` → `Probe: OK`。
- 实现回退（删 4 处检查）：`T28 FAIL exit=0x42 (expect 0x88)`、`Main results: 30/31`、`Overall: FAIL`，与完成区所述一致；T29–T31 仍 PASS（设备兜底）。**T28 有判别力**；T29–T31 因设备兜底对「translate 检查」本身判别力弱（但仍正确断言 `stm.*`→exit=ILLI）。
- 未发现改 contract/spec/向量/测试凑绿：主仓 `git status` 仅 task 文件、`series`、未跟踪 `0004` 补丁与 `min_rom_probe_006t.py`。

#### 七、完成区准确性

| 声明 | 核对 |
|---|---|
| 「通过 31/31；CTL 检测 2 处注入错误」 | ✅ 本人重跑一致 |
| patch `712` 行 | ✅ `wc -l`=712 |
| 交付物段登记 `cpu.c`/`helper.c`/`hw/dadao/dadao-machine.c`（003t 产物追加） | ✅ 已补全；0001(skeleton) 引入这 4 文件，0004 在其上追加；`git am` 干净 |
| 「byte 用 MO_UB/MO_SB（无 MO_ALIGN）」订正 | ✅ 已订正；全文不再出现 `MO_BESB` |
| 构建计数 | ✅ 已不再出现 `28/28` 等错误计数（本机增量编 `[6/6]` 链接、configure 计数无关紧要） |
| `andn.w rb`（translate.c:906） | ✅ 实际 `translate.c:906` |
| 新发现 #5「MALIGN 优先于 ILLI」 | ✅ 描述正确；**但实现与自述相反**（J6） |
| 「stm.o 反例 exit=0x42 / T29–T31 仍 PASS」 | ✅ 本人复现逐字一致 |
| 未自行 commit | ✅ 无新 commit（`.work/source/qemu` 工作树含未提交 `translate.c` 改动，0004 补丁已完整包含，clean-apply 字节一致） |

#### 八、验收表逐条复核

| # | 结论 | 依据 |
|---|---|---|
| 1 | ✅ | 四条补丁 `git am` `rc=0`；clean-apply 4 文件 sha256 与构建源一致；`make build-qemu` PASS |
| 2 | ✅ | 22/22 MemOp 逐条 OK（含 `st.o MO_ALIGN_8`），无残留桩 |
| 3 | ✅ | 全 `MO_BE*`（byte `MO_UB/MO_SB`）；`gen_ea_rrii` 48 位截断；`rdhc` 循环前快照 |
| 4 | ✅ | 单/多 ILLI 检查先于写 |
| 5 | ❌ | `st.o`/`ld.o`/`stm.o`(RAM) 未对齐 → `0x8C` ✅；但**未对齐 `stm.*` → exit port → `0x88`（应 `0x8C`）**（J6） |
| 6 | ✅ | jump-rrii/br.nz 落点本人逐槽验证（`+1/+2/+3`、taken/not-taken 唯一码）无 off-by-4 |
| 7 | ✅ | `-M ?` 含 `dadao-m1` |
| 8 | ✅（诚实） | BLOCKED 如实 |
| 9 | ❌ | 31/31 与 CTL 属实、T28 反例有判别力；**无未对齐 `stm.*`→exit 用例**，故漏检 J6 |
| 10 | ✅ | 未 commit |

#### 九、结论

第 2 轮唯一阻断 J4（`stm.*`→exit port 未返 ILLI）**已修复**：J4 主体、J1（jump 出口）、J2（落点）、J3（22/22 MemOp）、J5（ROM store）均通过；clean-apply 字节一致、构建/005t 回归/`-M ?`/确定性/无 TB 重放/探针反例均属实；完成区前轮表述问题已订正。

**但新增阻断 J6**：`gen_check_exit_port_illi`（`translate.c:78-87`，调用点 662/681/700/738）在 `MO_ALIGN_N` 之前执行，使**未对齐 `stm.*` 打到 exit port 返回 ILLI `0x88`，违反 ADR-0004 D5.6 优先级（应 MALIGN `0x8C`）与验收 5**；本人已用独立探针复现并以「删检查→转 `0x8C`」证明因果。**判 Needs Revision**。返工后须：给该检查加自然对齐门控（或调整判定次序），并在探针补未对齐 `stm.*`→exit 用例；harness e2e 仍 BLOCKED（020t）。

### 第 4 轮 engineer 自审（2026-09-20，J6 返工）

#### 一、修改点

**`gen_check_exit_port_illi` 增加自然对齐门控**（`translate.c:73-105`）：
- 函数签名新增 `int N` 参数（元素字节数：1/2/4/8）
- N>1 时：先 `tcg_gen_andi_i64(diff, ea, N-1)` + `brcondi NE, diff, 0, unaligned`；对齐才检查 exit port 范围；未对齐跳到 `unaligned` 标签放行
- N==1 时：byte 无对齐要求，直接检查 exit port 范围（行为与旧版一致）
- 4 处调用点更新：`stm.b`(N=1)、`stm.w`(N=2)、`stm.t`(N=4)、`stm.o`(N=8)

**探针新增3个 PRIO 用例**（`min_rom_probe_006t.py` T32-T34）：
- T32: `stm.o` exit+1（未对齐 8B）→ MALIGN `0x8C`
- T33: `stm.t` exit+2（未对齐 4B）→ MALIGN `0x8C`
- T34: `stm.w` exit+1（未对齐 2B）→ MALIGN `0x8C`

**CTL 新增1项**（验证探针能检测对齐优先级错误）：
- CTL3: `stm.o` 未对齐 exit MALIGN 但期望 ILLI → 应 FAIL（probe 能检测）

#### 二、逐行审查

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `tcg_temp_new_i64()` 在 if(N>1) 块内创建 `diff`，但两个分支都使用 | ✅已修 | TCG temp 生命周期以 TB 为单位，不受 C 作用域限制；两分支不同时执行，无冲突 | QEMU TCG temp pool 机制；构建 PASS 无 sanitizer 告警 |
| N=1（stm.b）走 else 分支，无对齐检查 | ✅已修 | byte 无对齐要求（规格 §4.1.1），行为与旧版一致 | T31 stm.b exit→ILLI `0x88` PASS |
| 4 处调用点 N 值与 MemOp 对齐常量一致 | ✅已修 | stm.b:MO_UB→N=1, stm.w:MO_BEUW|MO_ALIGN_2→N=2, stm.t:MO_BEUL|MO_ALIGN_4→N=4, stm.o:MO_BEUQ|MO_ALIGN_8→N=8 | grep 确认4处调用点 |
| 「修一类」：是否还有其它路径存在同类优先级倒置 | ✅已修 | 仅 `trans_stm_*` 使用 `gen_check_exit_port_illi`；单次 `st.b/w/t` 由设备 `size!=8` 兜底（不经过此函数）；`ld.*`/`ldm.*` 由设备读 handler 兜底 | grep 确认无其它调用点 |

#### 三、验证结果

| 验证项 | 结果 | 证据 |
|--------|------|------|
| `make build-qemu` | PASS | `.work/log/qemu/QEMU-006t-j6-build-qemu.log` |
| 006t 探针 34/34 | PASS | `.work/log/qemu/QEMU-006t-j6-probe-final.log` |
| CTL 3/3 检测错误 | PASS | 同上 |
| 005t 回归 20/20 | PASS | `.work/log/qemu/QEMU-006t-j6-probe-005t.log` |
| `git am` 干净 apply | PASS | 4 文件 sha256 逐一相同 |
| `qemu-system-dadao -M ?` | PASS | `dadao-m1` |
| 反例：去掉门控→T32/T33/T34 FAIL | PASS | `.work/log/qemu/QEMU-006t-j6-ctl-anti.log`：31/34（T32-T34 FAIL exit=0x88 expect 0x8C）；CTL3 由 FAIL 转 PASS（probe BROKEN） |
| 恢复门控→34/34 PASS | PASS | 构建+探针恢复 |

#### 四、判决

J6 已修复：`gen_check_exit_port_illi` 增加自然对齐门控，未对齐 EA 放行给 `MO_ALIGN_N` 触发 MALIGN `0x8C`；4 处调用点 N 值正确；探针 T32-T34 覆盖 PRIO 三例；反例验证（去掉门控）证明新用例有判别力；005t 无回归。标「待验收」。

### 第 4 轮 reviewer 验收（2026-09-20）

**判决：Accepted**

第 3 轮唯一阻断 **J6 已修复并经本人独立复现**；J1–J5 无回归；`make build-qemu` PASS、patch clean-apply 字节一致、005t 20/20；探针 34/34 + CTL 3/3 且反例有效（去掉门控 T32–T34 真 FAIL）；范围外指令仍为 ILLI 桩。唯一遗留为任务书「交付物」段（第 104 行）测试计数陈旧（见「七、残余」），不影响交付物正确性，供架构师终审订正。

#### 一、重跑记录（本人独立执行，真实输出/退出码）

| 命令 | 本人真实输出/退出码 | 日志 |
|---|---|---|
| 全新 clone `c3d48b7` + `git am` 0001→0004 | 四条均 `rc=0`，无 reject | `/tmp/opencode/QEMU-006t/am-*.log` |
| clean-apply 后 4 文件 sha256 vs 构建源 `.work/source/qemu` | `translate.c`=`a8b1644786…`、`cpu.c`=`3eac01d877…`、`helper.c`=`b08d74afa7…`、`dadao-machine.c`=`8e95603b83…` **逐一相同** | 终端 |
| `make build-qemu` | 末尾 `build-qemu: PASS`，`rc=0`（链接 `qemu-system-dadao`） | `.work/log/qemu/QEMU-006t-review4-build-qemu.log` |
| `python3 tools/qemu/min_rom_probe_006t.py`（engineer 探针） | `Main results: 34/34 passed, 0 failed`；CTL 3 项均 `[FAIL]`→`Probe: OK`；`Overall: PASS`，`rc=0` | `...-engineerprobe.log` |
| **本人自建独立探针** `/tmp/opencode/QEMU-006t/review4_probe.py`（46 例，编码独立派生自 `contracts/opcodes.yaml`，**未 import** engineer 脚本） | `Main results: 46/46 passed, 0 failed`；CTL 3 项均 `[FAIL]`→`Probe: OK`；`Overall: PASS`，`rc=0` | `...-ownprobe.log` |
| `qemu-system-dadao -M ?` | `dadao-m1  DADAO M1 bare-metal test machine`，`rc=0` | 终端 |
| `python3 tools/qemu/min_rom_probe_005t.py`（回归） | `Main tests: 20/20`、`CTL probe: OK`、`Overall: PASS`，`rc=0` | `...-probe-005t.log` |
| 反例：删除对齐门控（`gen_check_exit_port_illi` 回退为无门控）+ 增量重编 | `T32/T33/T34 FAIL exit=0x88 (expect 0x8C)`、`Main results: 31/34`、CTL3 由 FAIL 转 PASS、`Probe: BROKEN`、`Overall: FAIL`，`rc=1` | `...-ctl-build.log` / `...-ctl-engineerprobe.log` / `...-ctl-ownprobe.log` |
| 本人探针在同一反例构建下 | 6 个 J6 例 `rc=0x88`（expect `0x8C`）→ FAIL，`Main results: 40/46, 6 failed` | `...-ctl-ownprobe.log` |
| `git checkout` 复原 `translate.c`（sha256 复原 `a8b1644786…`）+ 重编 | `build-qemu: PASS`；engineer 探针复 `34/34`；本人探针复 `46/46` | `...-restore-build.log` / `...-probe-after-restore.log` / `...-ownprobe-after-restore.log` |
| 22 条 `trans_*` MemOp 逐条提取比对 | `22/22 OK, 0 mismatch` | `...-memops.log` |
| `rdhc` 快照 + 48 位 mask 提取 | ldm/stm 5 个多存取均 `load_rd(a->hc)` 循环前 + `& 0x0000FFFFFFFFFFFF` | `...-memops.log` |
| 范围外桩抽样（RB/RA/RF load/store、`br.*`、`jump_iiii`/`call_iiii`/`ret_riii`/`rela_si_rb`/`add_si_rb`） | 12 个抽样函数体均 `gen_exception_illegal(ctx); return true;` | 终端 |

#### 二、J6 独立复现（本人自建探针，不采信 engineer）

- **未对齐 `stm.*` → exit port = MALIGN `0x8C`**（ADR-0004 D5.6：对齐 > 访问种类）：
  ```
  [PASS] J6 stm.o exit+1: rc=0x8C expect=0x8C
  [PASS] J6 stm.o exit+2: rc=0x8C expect=0x8C
  [PASS] J6 stm.o exit+4: rc=0x8C expect=0x8C
  [PASS] J6 stm.t exit+1: rc=0x8C expect=0x8C
  [PASS] J6 stm.t exit+2: rc=0x8C expect=0x8C
  [PASS] J6 stm.w exit+1: rc=0x8C expect=0x8C
  ```
  （`exit+1/+2/+4` 分别覆盖 8B/4B/2B 的非自然对齐；engineer 只测了 `+1/+2/+1`，本人额外覆盖 `stm.o exit+2`、`stm.o exit+4`、`stm.t exit+1`。）
- **对齐 `stm.*` → exit = ILLI `0x88`**（J4，N 门控不误放行）：`stm.o`/`stm.t`/`stm.w` exit+0、`stm.o x2` exit+0 均 `0x88`。
- **byte 例外（N=1）**：`stm.b` exit+0 / exit+1 均 `0x88`（byte 无对齐要求，仍需 exit-port 范围检查）。
- **合法 `st.o` → exit 正常**：值 `0x00`/`0x42`/`0x7F` 分别得 `0x00`/`0x42`/`0x7F`。
- **合法 `stm.{b,w,t,o}` → RAM 往返**：写后经 `ldm.{ub,uw,ut,o}` 回读并 `st.o` 出值，四者均 `0x42`。
- **反例因果**（`...-ctl-ownprobe.log`）：删门控后同 6 例全部 `0x88` —— 确证 `0x8C` 由门控放行给 `MO_ALIGN_N` 所致。
- **确定性**：`stm.o exit+1` ×3 恒 `0x8C`，无 `-6`（SIGABRT）（`...-extra-romread.log`）。

#### 三、「修一类」核对

- 4 处调用点 N 与 MemOp 对齐常量逐一吻合（`...-memops.log`）：
  `trans_stm_b_rd` N=1/`MO_UB`、`trans_stm_w_rd` N=2/`MO_BEUW|MO_ALIGN_2`、`trans_stm_t_rd` N=4/`MO_BEUL|MO_ALIGN_4`、`trans_stm_o_rd` N=8/`MO_BEUQ|MO_ALIGN_8`。
- 全文件 `gen_check_exit_port_illi(ctx` **恰好 4 处**，无其它调用点。
- 无其它同类优先级倒置路径（本人额外验证）：
  ```
  [PASS] ld.o exit+1 (unaligned load): rc=0x8C expect=0x8C
  [PASS] ldm.o exit+1: rc=0x8C expect=0x8C
  [PASS] ld.uw exit+1: rc=0x8C expect=0x8C
  [PASS] st.b exit+1 (byte): rc=0x88 expect=0x88
  [PASS] stm.o exit+8 (aligned out-of-region): rc=0x87 expect=0x87
  ```
  单次 `st.b/w/t`→exit 与 `ld.*`/`ldm.*`→exit 由设备侧兜底，对齐由 TCG `MO_ALIGN_N` 先于设备触发，故无倒置。

#### 四、回归（J1–J5）

- **J1**（jump 出口）：`jump rb2(RAM),rd0,0` → `rc=0x88`（kernel=illi），无 SIGABRT。
- **J2**（落点）：`br.nz rd=1, imms18=3`（taken）跳过 FAIL 落 PASS → `0x00`；若 off-by-4 会落 `st.o rd19=1` 得 `0x01`；`br.nz rd=0`（not-taken）→ `0x00`。
- **J3**（`MO_ALIGN`）：22/22 MemOp；运行期 `st.o exit+1/+4`、`st.t exit+2`、`ld.o RAM+1/+4`、`ld.uw RAM+1`、`ld.ut RAM+2` 均 `0x8C`。
- **J4**（`stm.*`→exit ILLI 主体）：`stm.b/w/t/o`→exit 均 `0x88`；`st.b/w/t`→exit、`ld.o/ldm.o`→exit 均 `0x88`；合法 `st.o`→exit 正常。
- **J5**（ROM store）：对齐 `st.o`/`stm.o`→ROM 均 `0x88`；未对齐 `st.o`→ROM 得 `0x8C`（MALIGN 优先）；ROM 对齐读 `ld.o rb0+0/+8` 允许（→`0x00`）。

#### 五、探针效力（AGENTS「验证脚本反例门控」）

- **CTL**：本人重跑 engineer 探针见 3 项 `[FAIL]`（含新增 CTL3：`stm.o unaligned exit MALIGN but expect ILLI: exit=0x8C (expect 0x88)`）→ `Probe: OK`。
- **实现回退**：临时删除对齐门控并增量重编后，engineer 探针 `T32/T33/T34 FAIL exit=0x88 (expect 0x8C)`、`Main results: 31/34`、`Overall: FAIL`，且 **CTL3 由 FAIL 转 PASS → `Probe: BROKEN`**；本人独立探针 6 例 J6 同步 FAIL。**证明 T32–T34 与门控均有判别力**。随后 `git checkout` 复原（sha256 `a8b1644786…`）、重编、两探针复全绿。
- 未发现改 contract/spec/向量/测试凑绿：主仓 `git status` 仅 task 文件、`series`（M）、未跟踪 `0004` 补丁与 `min_rom_probe_006t.py`。

#### 六、完成区准确性

| 声明 | 核对 |
|---|---|
| 「通过 34/34；CTL 检测 3 处注入错误」 | ✅ 本人重跑一致（`TESTS=34`、`CTL_CHECKS=3`） |
| patch `737` 行 | ✅ `wc -l`=737；触及 4 文件（translate/cpu/helper/dadao-machine） |
| `series` 加入 0004 | ✅ 4 行含 0004；clean-apply 字节一致 |
| 修改文件清单 | ✅ 与 patch 实际触及文件一致 |
| 「`stm.*` exit port 运行期 ILLI 含对齐门控」 | ✅ `gen_check_exit_port_illi(ctx,ea,N)`，N=1/2/4/8 |
| 「反例 T32–T34 FAIL、CTL3 转 PASS（probe BROKEN）」 | ✅ 本人复现逐字一致 |
| 005t 回归 20/20 | ✅ 本人重跑一致 |
| 「未自行 commit」 | ✅ 主仓 HEAD 仍 `6d05bbb`，无新 commit |
| 「交付物」段 `min_rom_probe_006t.py：31 个测试用例 + 2 个 CTL`（第 104 行） | ⚠️ **陈旧**：实际 `TESTS=34`、`CTL_CHECKS=3`（完成区第 160 行已写 34+3）；见「八、残余」 |

#### 七、验收表逐条复核

| # | 结论 | 依据 |
|---|---|---|
| 1 | ✅ | 四条补丁 `git am rc=0`；clean-apply 4 文件 sha256 与构建源一致；`make build-qemu` PASS |
| 2 | ✅ | 22/22 MemOp 逐条 OK（含 `st.o MO_BEUQ\|MO_ALIGN_8`），无残留桩 |
| 3 | ✅ | 全 `MO_BE*`（byte `MO_UB/MO_SB`）；`gen_ea_rrii` 48 位截断；多存取 `load_rd(a->hc)` 循环前快照 |
| 4 | ✅ | 单/多 ILLI 检查在 EA/写之前 |
| 5 | ✅ | 未对齐 `st.o`/`ld.o`/`stm.*`(RAM 与 exit) → `0x8C`；**未对齐 `stm.*`→exit = `0x8C`（J6 已修）**；`EXCP_MALIGN` 定义/注册（003t 既存） |
| 6 | ✅ | jump-rrii 无 SIGABRT；br.nz taken/not-taken 落点正确 |
| 7 | ✅ | `-M ?` 含 `dadao-m1` |
| 8 | ✅（诚实） | BLOCKED 如实，待 020t |
| 9 | ✅ | 探针 34/34 + CTL 3/3 属实；T32–T34 反例证明有判别力；本人另建 46 例独立复现一致 |
| 10 | ✅ | 未自行 commit |

#### 八、残余问题（不阻断）

1. **任务书第 104 行（交付物段）陈旧**：`31 个测试用例 + 2 个 CTL self-check` ≠ 实际 `34 + 3`（完成区第 160 行已正确）。建议架构师终审时就地订正为 `34 + 3`。
2. **`andn.w rb`（`translate.c:906`）**：既不在 ADR-0010 D1 最小集、harness 亦未使用，属额外范围（任务书「遗留问题」已登记）。按第 1 轮意见，建议移回 008t 或明确登记——属架构层归属决定，非本轮实现缺陷。
3. `add.si rb`（op=0x5B）仍为 ILLI 桩（属 008t），与任务书登记一致。

#### 九、结论

**Accepted。** J6（未对齐 `stm.*`→exit port 的 MALIGN/ILLI 优先级倒置）**已修复**：4 处 `stm.*` 调用点带正确 N（1/2/4/8）的自然对齐门控，未对齐 EA 放行给 `MO_ALIGN_N` 触发 `0x8C`；本人以独立探针（46 例，含 `stm.o exit+2/+4`、`stm.t exit+1` 等 engineer 未覆盖的角点）复现，并用「删门控→6 例转 `0x88`、CTL3 转 PASS/BROKEN」证明因果与探针判别力。J1–J5 无回归、22/22 MemOp、005t 20/20、patch clean-apply 字节一致、构建/`-M ?` 通过、范围外仍桩、未自行 commit。唯一遗留为第 104 行交付物计数陈旧（文档级，已记录），不构成阻断。harness e2e 仍 BLOCKED（020t）。
