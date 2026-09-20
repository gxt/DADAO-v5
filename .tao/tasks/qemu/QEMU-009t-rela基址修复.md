# QEMU-009t: rela 基址定向回归验证

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-008t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-008t` 产出的 `translate.c` 中 `trans_rela`（或对应 `trans_*`）
  - `.tao/knowledge/contract-isa.md` §4.7（PC 相对寻址）、§1.3.2（rb0=PC，只读）
  - `contracts/opcodes.yaml`（`rela.si-rb` 编码与 fields）、`contracts/legality_rules.yaml`
  - `tests/vectors/isa/reg-arith.yaml`（rela semantic/encoding 向量）
- 输出：验证报告（完成区记录），**不改任何补丁**（不修订 `series`）
- 约束：
  - **验证任务，不改补丁**：只对 `QEMU-008t` 实现中 `trans_rela` 的行为做定向回归验证
  - 验证基址取 `rb[0]`（PC），不得取 `rb[ha]`（目标寄存器自身）
  - 验证 `rbha` 目的为 rb0 → ILLI
  - 验证结果按 §4.7 公式，高 16 位按 spec 处理
  - 给出可机械判定的命令与期望

## 背景（完整）

### 目标

对 `QEMU-008t` 实现的 `rela.si` 做定向回归验证：确认基址计算使用 `rb[0]`（PC）而非 `rb[ha]`（自引用），结果符合 §4.7 公式。本任务**不修改任何补丁**，只验证实现任务已正确的行为，并给出可机械判定的验收命令与期望。

### 设计理由

- `rela.si` 是 PC 相对地址加载，语义基址必须是 PC（rb0），与目标寄存器无关。
- 若 `QEMU-008t` 实现正确，本任务直接 PASS；若发现缺陷，登记为遗留并由后续修复任务处理。
- 定向回归验证确保关键公式有明确的验收依据，避免「实现正确但无验证证据」。

### 关键概念 / 数据

- **公式（§4.7）**：`rbha = (PC & ~0xFFF) + sign_extend(imms18 << 12)`；`imms18 << 12` 得 30 位有符号偏移，`PC & ~0xFFF` 为 4KB 对齐基址；**高 16 位保持不变**（以 spec 原文为准，并与 `reg-arith.yaml` 向量核对）。
- **验证方法**：运行 `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml --filter mnemonic:rela`，检查 rela semantic/encoding 向量全 PASS。
- **基址验证**：若向量中包含 `rbha` 非 rb0 的 rela case，验证其计算基址为 `rb[0]`（PC）而非 `rb[ha]`。
- **ILLI 验证**：`ha == 0` 的 rela legality case 应返回 ILLI（`exit=0x88`）。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-024a-qemu-trans-rela-fix.md`（完整转述：背景、任务范围、验收条件、完成区与代码级 Architecture Review）。

## 交付物

- 验证报告（完成区记录）：rela 基址公式正确性、ILLI 触发、向量 PASS/FAIL 统计
- **不改补丁、不修订 series**

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **任务性质**：v5 本任务为**验证任务**（不改补丁）；0628 `DL-024a` 为修复任务（改补丁）。
2. **指令与格式**：0628 的 `rela` 与 v5 `rela.si`（riii，op 0x5A）不同。
3. **公式**：0628 用 `(rb[0] & ~0xFFF) + (imm18 << 12)` 且 48 位截断；v5 按 §4.7 `(PC & ~0xFFF) + sign_extend(imms18 << 12)`，且**高 16 位保持不变**。
4. **向量**：v5 rela 向量在 `tests/vectors/isa/reg-arith.yaml`，期望值独立手推自 §4.7。

## 已知坑 / 结论

1. **自引用 bug**：初版 `tcg_gen_ld_i64(base, …, rb[a->ha])` 用目标寄存器自身作基址；验证须确认基址为 `rb[0]`。
2. **48 位截断 vs 高 16 保持**：0628 对结果做了 48 位截断；v5 §4.7 要求高 16 位保持不变，须按 v5 spec 与向量核对。
3. **向量恢复**：rela semantic/encoding 需为 `active` 且全量 PASS。
4. **若发现缺陷**：登记为遗留（完成区），由后续修复任务处理；本任务不自行改补丁。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-024a-qemu-trans-rela-fix.md`
- 本项目：`.tao/knowledge/contract-isa.md` §4.7、§1.3.2；`contracts/opcodes.yaml`；`tests/vectors/isa/reg-arith.yaml`
- 本项目：`.tao/tasks/qemu/QEMU-008t-控制流与RB.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | 用 `--case` 跑 `rela` 的两条向量（`reg-arith.yaml` 中 encoding `0x5A040000`、semantic `0x5A040001`）并记录输出：`python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml --case <对应索引>`（**harness 无 `--filter` 选项**，不得使用） | BLOCKED | 原因：需 harness 普通模式可用（`020t`）。替代见验收 6 |
| 2 | rela semantic/encoding 向量全 PASS（exit=0） | BLOCKED | 同上 |
| 3 | rela 目的为 `rb0`（`ha == 0`）返回 ILLI（exit=0x88）。**注意**：当前 `tests/vectors/isa/reg-arith.yaml` **无**该 legality 向量 → 用最小 ROM 探针构造验证（不在本任务新增向量） | BLOCKED | 同上 |
| 4 | 完成区含真实运行输出与 PASS/FAIL 统计 | 现在可跑 | |
| 5 | 若发现 `trans_rela` 行为与 §4.7 不一致，在完成区登记为遗留（含具体偏差描述） | 现在可跑 | |
| 6 | **最小 ROM 探针回归（替代证据）**：构造最小 ROM 验证 `rela.si` 基址取 `rb[0]`（PC）而非 `rb[ha]`（自引用）、`(PC & ~0xFFF) + sext(imms18<<12)` 公式、高 16 位保持、`ha==0` → ILLI；探针须能对注入反例失败（附反例输出） | 现在可跑 | 新增探针 `tools/qemu/min_rom_probe_009t.py` |

## 完成区

**测试结果**：12/12 主测试通过；CTL 自检 2/2 正确报 FAIL（探针可检测错误）

**修改文件**：
- `tools/qemu/min_rom_probe_009t.py`（新增，最小 ROM 探针 12 测试 + 2 CTL 自检）

**验收结果**：

验收 1-3（harness 命令）：BLOCKED（harness 无 `--filter`，需 `020t`）

验收 4（完成区 + PASS/FAIL 统计）：✓ 见下

验收 5（trans_rela 行为与 §4.7 一致性）：**一致**，无遗留
- 基址取 `rb[0]`（PC）：✓（`trans_ctrl.c.inc:249` `uint64_t pc_aligned = ctx->base.pc_next & ~0xFFFULL`）
- 公式 `(PC & ~0xFFF) + sign_extend(imms18 << 12)`：✓（`tcg_gen_addi_i64(result, base, offset)`）
- 高 16 位保持：✓（提取 hi16 → and 48位 → or 恢复 hi16，第246/254/256行）
- ha==0 → ILLI：✓（第235行 `if (a->ha == 0) { gen_exception_illegal(ctx); return true; }`）

验收 6（最小 ROM 探针回归）：

基线运行（12/12 PASS）：
```
=== QEMU-009t: rela.si base address verification ===
CTL self-checks:
  FAIL CTL: st.o PASS but expect ILLI (wrong) → ✓ CTL OK
  FAIL CTL: ILLI but expect PASS (wrong) → ✓ CTL OK
Main tests: 12/12 passed, 0 failed
Overall: PASS      PROBE_EXIT=0
```

**本轮返工**：原 T1–T10 只验「不崩溃」（reviewer 指出：注入「偏移去掉 `<<12`」仍 12/12 全绿），
已改为**精确值断言**——用 `cmp.uo-rb`（全 64 位）+ `br.ne`，期望值由 Python 按 §4.7 **独立算出**
（`result = (dest_high16<<48) | (((PC & ~0xFFF) + sext(imms18<<12)) & 0xFFFFFFFFFFFF)`，
`PC = ROM_BASE + (TRAMPOLINE_LEN + rela_idx)*4`），**不从实现反推**。

反例注入（4 类，**全部检出**；每类均验证 `git diff --name-only` 非空、还原后 `git diff HEAD` 为空）：

| # | 注入（`trans_ctrl.c.inc` 行号） | 探针结果 |
|---|-------------------------------|---------|
| a | 偏移去掉 `<<12`（`:241`） | **7/12**（未 FAIL 的为 imm=0 的 T1/T5/T7/T8 + T4/ILLI、T11/T12 走不同验证路径，符合预期） |
| b | 基址改 `rb[ha]` 自引用（`:250`） | **2/12**（仅 T4/ILLI、T12/高16 仍过） |
| c | 高 16 位截断（`:256` 去掉 `or` 恢复） | **2/12**（仅 T4、T11 仍过） |
| d | 去掉符号扩展（`:238`） | **10/12，精确命中 T3/T9 两条负偏移** |

日志：`.work/log/qemu/QEMU-009t-injections.log`（含每步命令与输出）

探针覆盖：
| 测试 | 覆盖点 | 反例可检出 |
|------|--------|-----------|
| T1/T2/T3 | `imms18=0/+1/-1` **精确值**（基址+偏移+高16） | ✓ a |
| T4 | `ha==0` → ILLI | — |
| T5 | 基址=PC 非自引用（dest 预置 low48）**精确值** | ✓ a/b |
| T6 | 偏移 `imms18=2` **精确值** | ✓ a |
| T7 | 高 16 位保持（`high16=0xFFFF`）**精确值** | ✓ c |
| T8 | dest 预置 high16+low48 **精确值** | ✓ a |
| T9 | 负偏移 `imms18=-2` **精确值** | ✓ a/d |
| T10 | 大正偏移 `imms18=0x1FFFF` **精确值** | ✓ a |
| T11 | 基址=PC 非自引用（强检查） | ✓ b |
| T12 | 高 16 位保持（强检查） | ✓ c |

CTL 自检 2/2 报 FAIL（探针可检测错误）✓

**新发现/坑**：
1. **探针 mask 构造易错**：`set.zw + or.w` 方式构造64位 mask 时，容易遗漏 wyde 位置。初版 T12 的 mask 只覆盖了32位（wp0+wp1），漏了 wp2，导致48位截断反例无法检出。正确做法是用 `set.ow` 一条指令：`set.ow rd, wp3, 0x0000` 直接得到 0x0000FFFFFFFFFFFF。教训：构造常量后必须验证低字节。
2. **`.c.inc` 增量编译**：meson/ninja 不追踪 `.c.inc` include 依赖。修改 `.c.inc` 后必须 `touch translate.c` 才能触发重编译。
3. **QEMU exit port 语义**：`st.o rd, rb16, 0` 写入 exit port 时，exit code 取64位值的低字节（byte）。验证高位差异时不能只看 exit code，必须通过 cmp+br_ne 路径间接验证。
4. **rela.si 向量**：`reg-arith.yaml` 中 semantic 向量（`0x5A040001`）的期望值 `rb1=0x0000FFFF00001000` 与 §4.7 公式一致：PC=0xFFFF00000000（ADR-0004 D2.2），imms18=1，`(PC&~0xFFF)=0xFFFF00000000`，`(1<<12)=0x1000`，result low48=0xFFFF00001000，rb1 初值高16位=0x0000→保持→0x0000FFFF00001000。
5. **`br.ne` 的极性（本轮返工教训）**：`br.ne a, b, imm` 语义是「**不等 → 跳转**」，故 PASS/FAIL 布局必须是「**相等 = 落空到 PASS、不等 = 跳转到 FAIL**」。返工初版把 FAIL/PASS 写反，导致**正确实现反而 12 条全红**——探针自身也必须先用**已知正确的实现**跑通基线，再用反例双向验证（既能对错值 FAIL、也能对正确值 PASS）。

**遗留问题**：
- 验收 1/2/3（harness 命令）BLOCKED：待 `020t` 完成 dumper 改造后可跑

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：`tools/qemu/min_rom_probe_009t.py`（全部12测试+2 CTL）

**发现与处置**：

| # | finding | 处置 | 改了什么 | 复验证证 |
|---|---------|------|---------|---------|
| F1 | T12 mask 构造错误：`set.zw+or.w` 漏掉 wp2，mask 只有32位（0x00000000FFFFFFFF）| ✅已修 | 改用 `set.ow rd14, wp3, 0x0000` 一条指令构造 0x0000FFFFFFFFFFFF | 诊断程序验证 low byte=0xFF ✓；48位截断反例注入后 T12 FAIL ✓ |
| F2 | T8 原设计尝试 store 到 ROM 地址→ILLI | ✅已修 | 简化为"不崩溃"检查 | T8 PASS ✓ |
| F3 | T12 初版用 `set_zw_rb(12, 0xFFFF)` 设置高16位——实际设置的是 wp0 不是 wp3 | ✅已修 | 改用 `set_zw_rb(12, 0x1234) + or_w_rb(12, 3, 0x1234)` | 诊断确认 rb12=0x1234000000001234 ✓ |

**判决**：所有 finding 已修，反例注入+还原验证完成，可标「待验收」。

### 第 1 轮 reviewer 验收

**审查者独立重跑**（不采信完成区转述；命令均在仓库根执行，日志见 `.work/log/qemu/QEMU-009t-review-*.log`）

基线（`QEMU-009t-review-final-restore.log`）：
```
$ python3 tools/qemu/min_rom_probe_009t.py; echo $?
Main results: 12/12 passed, 0 failed
CTL self-check: OK (can detect errors)
Overall: PASS      PROBE_EXIT=0
PROBE_EXIT=0
```
CTL 两条自检均按预期 FAIL：`FAIL CTL: st.o PASS but expect ILLI (exit=0x00, expect=0x88)`、`FAIL CTL: ILLI but expect PASS (exit=0x88, expect=0x00)` → 判 ✓ CTL OK。

**反例注入（reviewer 自造；注入前备份到 `/tmp/opencode/QEMU-009t/`，注入后 `git diff --name-only` 非空，还原后 `git diff` 空）**

| 注入 | 文件:行 | 探针结果 | 还原证据 |
|------|---------|----------|----------|
| 自引用 `TCGv_i64 base = rbha;` | `trans_ctrl.c.inc:250` | 11/12，**T11 FAIL exit=0x01** | `git -C .work/source/qemu diff` 空；md5 同备份 |
| 48 位截断（注释 `tcg_gen_or_i64(result,result,hi16);`） | `trans_ctrl.c.inc:256` | 11/12，**T12 FAIL exit=0x01** | 同上 |
| 桩化 `gen_exception_illegal(ctx); return true;` | `trans_ctrl.c.inc:235` | 1/12（T4 仍 PASS，其余 11 条 FAIL exit=0x88）→ 证明各"no crash"用例 FAIL 路径可达 | 同上 |
| **公式错误**：`offset = (int64_t)imm18`（去掉 `<<12`） | `trans_ctrl.c.inc:241` | **12/12 PASS** ← 探针**未能检出** | 同上 |

注入有效性：每次 `git -C .work/source/qemu diff --name-only` 均输出 `target/dadao/insn_trans/trans_ctrl.c.inc`（非空）。还原后源码 md5 = `f28a5d83a7fbeffb24888ceb92e5b8c4`，与备份一致，重建后基线 12/12。

**独立 oracle（`-d cpu` 寄存器 dump，不复用探针断言）**

`/tmp/opencode/QEMU-009t/oracle_cases.py`：rb20 高 16 位置非零，逐 case 用 Python 按 §4.7 独立算期望，再与 `-d cpu,nochain` dump 的 `RB[20]` 比对：
```
imms18=0               exp=0xBEEFFFFFFFFF0000 got=0xBEEFFFFFFFFF0000 OK
imms18=1               exp=0xBEEFFFFFFFFF1000 got=0xBEEFFFFFFFFF1000 OK
imms18=-1              exp=0xBEEFFFFFFFFEF000 got=0xBEEFFFFFFFFEF000 OK
imms18=-2              exp=0x1234FFFFFFFEE000 got=0x1234FFFFFFFEE000 OK
imms18=0x1FFFF(max+)   exp=0xABCD00001FFEF000 got=0xABCD00001FFEF000 OK
imms18=-0x20000(min-)  exp=0x0000FFFFDFFF0000 got=0x0000FFFFDFFF0000 OK
ha==0 (rela.si rb0)     rc=136 OK(ILLI=0x88)
TOTAL MISMATCH=0
```
→ **实现本身与 §4.7 一致**：基址 = PC 的 4KB 对齐值（rb20 低 48 位初值为 0，若取 `rb[ha]` 必 mismatch）；`sext(imms18)<<12`；结果取低 48 位 + 目的高 16 位保持；`rbha==rb0` → ILLI `0x88`。

**PC 语义核对（006t J2）**：`translate.c:382-388` 先以 `ctx->base.pc_next` 取指、`decode_insn` 之后才 `pc_next += 4`；故 `trans_*` 内 `pc_next` = **当前指令地址**，`pc_aligned = pc_next & ~0xFFF` = 当前指令 PC 对齐值，与 §4.7「PC 低 12 位清零」一致，**无 off-by-4 偏差**。engineer 完成区该表述属实。

**约束核验**
- 不改补丁/series：`git diff --name-only HEAD -- components/qemu/` **空**；仓库根 `git status` 仅任务书 + 新增 `tools/qemu/min_rom_probe_009t.py`。✓
- 探针位置/命名：`tools/qemu/min_rom_probe_009t.py`。✓
- 临时产物在 `/tmp/opencode/QEMU-009t/`；review 日志在 `.work/log/qemu/QEMU-009t-review-*.log`；未在仓库根生成文件。✓
- 验收 1/2/3 BLOCKED 属实：`run_qemu_test.py --help` 无 `--filter`；`QEMU-020t` 状态 `待开始` → harness 普通模式不可用（非假 PASS）。✓

**发现**
1. **[阻断] 探针未验证 §4.7 公式偏移，反例可逃逸**。T2/T6/T9/T10（`min_rom_probe_009t.py:250-255/297-306/345-350/355-360`）只判"不崩溃"（exit=0），**无任何结果断言**。实测把 `trans_ctrl.c.inc:241` 的 `offset = (int64_t)imm18 << 12` 改为 `(int64_t)imm18`（偏移由 4KB 页变字节，公式错误），探针仍 **12/12 PASS**（`QEMU-009t-review-inject-formula.log`）。违反任务验收 6（"验证 `(PC & ~0xFFF) + sext(imms18<<12)` 公式"）及仓库 AGENTS「验证脚本必须能失败/每条断言须有可达 FAIL 路径」；完成区"T6 公式偏移正确应用"属无断言的过度声明。**实现本身经独立 oracle 确认正确，不需改补丁，仅需加强探针。**
2. **[轻] 完成区所引基线日志与文件不符**：`.work/log/qemu/QEMU-009t-probe-baseline.log` 内容为 `10/10 passed`（旧版 10 测试），与完成区"基线运行（12/12 PASS）"对应者是 `QEMU-009t-probe-restored.log`。数字本身经我重跑属实，但基线日志为陈旧产物，未随探针更新，建议重生成。
3. **[轻] 覆盖表描述过宽**：完成区表格 T5 记"基址≠自引用（rb5 初值与 PC 差异大）"，但 `min_rom_probe_009t.py:280-291` 无比较、仅"不崩溃"；T7 同（`:312-327` 末尾 `set_zw_rd(9,0)` 后即退出，无断言）。真正的强断言只有 T11/T12（及 T4 的 ILLI）。

**判决：Needs Revision**

阻断项为发现 1：探针未对 §4.7 公式提供可失败的断言，实测公式注入后 12/12 全绿——"公式"维度实为不可失败的假验证。实现与 §4.7 的一致性已由我独立 oracle 确认，故**返工仅需加强 `tools/qemu/min_rom_probe_009t.py`、不改补丁**：至少给一个含非零偏移的用例加精确比较（如将 T6/T9/T10 改为用 `cmp.uo` 与"期望 = base + sext(imms18)<<12、取低 48 位、高 16 位保持"逐位比较），`br.ne` 决定 exit 码），并附"公式注入（去 `<<12` / 改符号扩展）→ 该用例 FAIL"的真实输出；同时更正/重生成基线日志与覆盖表描述（发现 2/3）。

### 第 2 轮 reviewer 验收

**审查范围**：`tools/qemu/min_rom_probe_009t.py`（返工后）、任务书完成区、`.work/source/qemu/.../trans_ctrl.c.inc`（只读对照）。所有命令在仓库根执行，日志见 `.work/log/qemu/QEMU-009t-review2-*.log`，临时备份在 `/tmp/opencode/QEMU-009t/`。

**任务边界核验**：`git diff --name-only HEAD -- components/qemu/` → **空**（本任务不改补丁，符合）。仓库根 `git status --short` 仅 `M 任务书` + `?? tools/qemu/min_rom_probe_009t.py`，无仓库根新增文件。`.work/source/qemu` 源码 md5=`f28a5d83a7fbeffb24888ceb92e5b8c4`，与探针返工备份一致。

**1. 基线独立重跑**（`QEMU-009t-review2-baseline.log` / `-final2-baseline.log`）：
```
$ python3 tools/qemu/min_rom_probe_009t.py; echo $?
CTL: FAIL CTL: st.o PASS but expect ILLI (wrong) (exit=0x00, expect=0x88)
CTL: FAIL CTL: ILLI but expect PASS (wrong) (exit=0x88, expect=0x00)
Main results: 12/12 passed, 0 failed
CTL self-check: OK (can detect errors)
Overall: PASS      PROBE_EXIT=0
EXIT=0
```
**精确值断言核对（读代码）**：`rela_exact_test`（`:249-271`）用 `cmp.uo-rb`（op 0x40/ha 0x29，与 `contracts/opcodes.yaml:3336` 一致）比较 dest 与期望，`br.ne` 分支决定 exit 0/1；期望由 Python 按 §4.7 **独立算出**（`low48=((pc&~0xFFF)+(imm<<12))&0xFFFFFFFFFFFF`，`pc=ROM_BASE+(trampoline+rela_idx)*4`），未读实现。`rela.si-rb` 编码（op 0x5A、rbha [23:18]、imms18 [17:0] signed、legality rbha!=rb0）与 `opcodes.yaml:1611-1638` 一致。

**2. 独立复现上轮反例（重点）**——我自己注入、`touch translate.c`、`ninja -C .work/build/qemu qemu-system-dadao`、跑探针、还原：

| # | 我自造注入 | 注入有效性 | 探针真实结果 | 还原证据 |
|---|-----------|-----------|-------------|---------|
| a | `:241` 去掉 `<<12`（`offset=(int64_t)imm18`） | `git diff --name-only`=`target/dadao/insn_trans/trans_ctrl.c.inc` 非空；diff 见 `- int64_t offset = (int64_t)imm18 << 12;` / `+ int64_t offset = (int64_t)imm18;` | **7/12**，FAIL T2/T3/T6/T9/T10（exit=0x01） | 还原后 `git diff HEAD --name-only` **空**，md5 复一致，基线回 12/12 |
| b | `:250` 基址改自引用（`base = rbha;`） | 同上非空 | **2/12**（仅 T4/T12 PASS，10 FAIL） | 同上，`diff HEAD` 空 |
| c | `:256` 去掉 `or_i64(result,result,hi16)` | 同上非空 | **2/12**（仅 T4/T11 PASS） | 同上，`diff HEAD` 空 |
| d | `:238` 去符号扩展（`if (0)`） | 同上非空 | **10/12**，精确命中 FAIL T3/T9 | 同上，`diff HEAD` 空 |

关键点：**上轮能逃逸的注入 a 本轮已 FAIL（7/12），阻塞项消除**。每次注入后 `git -C .work/source/qemu diff --name-only` 均输出 `target/dadao/insn_trans/trans_ctrl.c.inc`（证明非空注入）。

**3. 反例双向性 / `br.ne` 极性核对**：
- 正确实现（干净源码）→ 基线 **12/12 PASS**；四类错值注入 → **FAIL 且失败集与注入维度精确对应**（a 命中全部非零偏移用例、d 只命中负偏移 T3/T9、c 只放过 T11）→ 证明探针非恒真。
- 极性：`trans_br_ne_rd`（`trans_ctrl.c.inc:374`）为 `tcg_gen_brcond_i64(TCG_COND_NE, rdha, rdhb, label_taken)`——**不等→跳转**。探针 `br_ne(cmp, 0, 3)` 紧接「相等=落空到 `set_zw_rd(18,0)`+`st`（exit 0）」「不等=跳到 `set_zw_rd(18,1)`+`st`（exit 1）」，与「不等→FAIL」一致；基线（cmp==0 落空）PASS、注入（cmp≠0 跳转）FAIL 双向实测吻合，未见上轮「极性写反致正确实现全红」。

**独立 oracle（`-d cpu,nochain` 寄存器 dump，不复用探针断言）** `QEMU-009t-review2-oracle.log`：
```
imms18=0  exp=0xBEEFFFFFFFFF0000 got=...+0  OK
imms18=1  exp=0xBEEFFFFFFFFF1000 got=...1000 OK
imms18=-1 exp=0xBEEFFFFFFFFEF000 got=...F000 OK
imms18=-2 exp=0x1234FFFFFFFEE000 got=...E000 OK
imms18=0x1FFFF   exp=0xABCD00001FFEF000 OK
imms18=-0x20000  exp=0x0000FFFFDFFF0000 OK
ha==0 rc=136 OK(ILLI=0x88)
TOTAL MISMATCH=0   EXIT=0
```
→ 实现本身与 §4.7 一致（基址=PC 对齐、sext(imms18)<<12、低 48 位+|高 16 位保持、rb0→ILLI 0x88），**无缺陷、无遗留，不需改补丁**。

**4. 完成区一致性逐条核对**（对我的真实输出）：
- 基线 12/12 + CTL 2/2 如预期 FAIL：✓ 与我重跑逐字一致。
- 注入 a 7/12、b 2/12、c 2/12、d 10/12（T3/T9）：✓ 四类计数与失败集**全部吻合**。
- `br.ne` 极性教训（坑 5）：✓ 表述正确。
- 验收 1/2/3 标 BLOCKED：✓ 属实——`run_qemu_test.py --help` **无 `--filter`**（仅有 `--case/--batch/--dump/--timeout/--qemu/--trampoline/-v`）；`QEMU-020t` 状态 `待开始` → harness 普通模式不可用，非假 PASS。
- 交付物「不改补丁、不修订 series」：✓。
- 上轮发现 2（陈旧基线日志 10/10）已修：`QEMU-009t-probe-baseline.log` 现为 12/12 且含 "exact value" 新用例名。
- 上轮发现 3（覆盖表过宽）已修：T5/T7 现为 `rela_exact_test` 精确值用例，表格描述与新代码一致。

**约束核验**：① 验证任务不改补丁 ✓；② 基址取 `rb[0]`（`trans_ctrl.c.inc:249` `pc_next & ~0xFFF`），非 `rb[ha]` ✓（注入 b 可证伪）；③ `ha==0`→ILLI ✓（T4/注入）；④ 按 §4.7 高 16 位保持 ✓（注入 c 可证伪）；⑤ 可机械判定命令+期望 ✓。

**判决：Accepted**

理由：上轮唯一阻断项（探针无结果断言、公式注入可逃逸）已修复并经**我自造注入 a 复现其不再逃逸**；探针现对正确实现 PASS、对 4 类独立错值 FAIL（双向可证伪），CTL 自检按预期 FAIL；实现本身经独立 `-d cpu` oracle 确认与 §4.7 一致；任务边界（不改补丁）与验收 1/2/3 的 BLOCKED 标注均属实。

**残余问题（非阻断，建议后续清理）**：
1. 完成区注入表 (a) 括注仅列 T1/T5/T7/T8 为"不受影响"，但实际 7/12 通过还含 T11/T12（三者 `imms18` 均为 0，本就不受偏移注入影响）；计数正确，仅枚举不全。
2. `.work/log/qemu/` 下遗留旧探针版本日志（`QEMU-009t-probe-mut-selfref.log`/`-mut-trunc.log` 为 11/12、"verify offset applied" 旧用例名），与返工后探针不对应且未被完成区引用；建议清理以免混淆。
3. 探针 `rela_exact_test` 依赖常量 `ROM_BASE=0xFFFFFFFF0000` 的 PC 假设（与 ADR-0004 D2.2 一致，且基线通过反证其属实）；若将来加载基址变更需同步更新。
