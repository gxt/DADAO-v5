# QEMU-012t: 分支 PC 公式 + call RA 定向回归验证

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-011t`、`TESTCASES-005t`、`TESTCASES-006t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-011t` 产出的 `.work/source/qemu` 工作树（控制流实现已在，含分支 PC 公式与 call RA）
  - `.tao/knowledge/contract-isa.md` §5.1（通用约定）、§5.2（条件跳转）、§5.3（无条件跳转，公式仅作参考；`jump` 的语义验证由 `QEMU-006t`/`008t` 探针承担）、§5.4（函数调用）、§5.5（函数返回）、§5.6（压栈/弹栈流程：§5.6.1 压栈 / §5.6.2 弹栈）
  - `tests/vectors/isa/ctrl-br.yaml`、`tests/vectors/isa/ctrl-jump.yaml`、`tests/vectors/isa/ctrl-call.yaml`、`tests/vectors/isa/ctrl-ret.yaml`（`TESTCASES-005t`/`TESTCASES-006t` 产出，独立 oracle）
  - `.tao/knowledge/adr-0004-test-machine.md`（fault/exit 可观测）
- 输出：验证报告（完成区记录），**不改任何补丁**（不修订 `series`）
- 约束：
  - **验证任务，不改补丁**：只对实现中分支 PC 公式与 call RA 的行为做定向回归验证
  - 验证 taken 公式与 §5 及向量一致
  - 验证 not-taken 推进到下一指令
  - 验证 `call` 返回地址正确（压入 ra63）
  - 给出可机械判定的命令与期望

## 背景（完整）

### 目标

对实现的控制流做定向回归验证：确认分支 taken/not-taken PC 公式、call 返回地址与 §5 及独立向量一致。本任务**不修改任何补丁**，只验证实现任务已正确的行为。

### 设计理由

- 分支 PC 公式是控制流正确性的核心：not-taken 不推进会重复执行同一条；taken 基准错误会跳错地址。
- call 返回地址正确性由 `call→ret→landing` 往返隐式验证。
- 若实现正确，本任务直接 PASS；若发现缺陷，登记为遗留。

### 关键概念 / 数据

**v5 权威公式（§5）**：
- 条件跳转（§5.2）：`if (cond) PC = rb0 + (imms12/imms18 << 2)`；`rb0` = 该分支指令**自身**地址（48 位有效，`rb0[63:48]=0`）。
- `jump-iiii`（§5.3）：`PC = rb0 + (imms24 << 2)`。
- `jump-rrii`/`call-rrii`（§5.3/§5.4）：`PC = rbha + rdhb + (imms12 << 2)`（低 48 位，溢出丢弃；`imms12` 为有符号 12 位立即数）。
- `call`（§5.4）：先计算返回地址（= `call` 的**下一条指令**地址）并按 **§5.6.1** 压栈流程压入 `ra63`（高 16 位引用计数、低 48 位返回地址），再跳转。
- `ret`（§5.5）：`PC = ra63 低 48 位`，按 **§5.6.2** 弹栈流程弹栈；同时 `rdha = sign_extend(imms18)`。

**验证方法**（harness 控制流能力未就绪，见验收；以最小 ROM 探针为主）：
- **主**：最小 ROM 探针（复用/扩展 `tools/qemu/min_rom_probe_008t.py` 的 call/ret 往返框架），逐条覆盖：
  - taken：分支目标 = `rb0 + (imm << 2)`（含正/负偏移、`rb0` 为分支指令自身地址）；
  - not-taken：PC 推进到**下一指令**（不重复执行同一条）；
  - `call` 返回地址 = `call` 下一条指令；`call→ret→landing` 往返 PASS；
  - RA 压栈按 §5.6.1：首次压栈高 16 位=0x0001、递归调用递增、地址不同则移位压栈。
- **辅**：harness 可跑部分（如 `ctrl-ret.yaml` 的 legality 类 RASUF 判定），命令：
  `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/ctrl-ret.yaml --case 1`
  （注意：单文件模式**只跑一个 case**，`--case` 为 **0-based**；「全量」须 `--batch` 指向目录）。
- **BLOCKED**：`ctrl-*.yaml` 的 **semantic/encoding** 类（控制流）需 `017t`/`018t` 增强 harness 后回补（当前会 TIMEOUT 或跳飞）。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-032a-qemu-patch-0007.md`（完整转述：背景、提交/导出/series 步骤、约束、验收、完成区与代码级 Architecture Review）。
- DADAO-0628：`code-agent/tasks/DL-030a-call-ret-semantic.md`（call/ret 返回地址修正）。

## 交付物

- 验证报告（完成区记录）：分支 PC 公式正确性、call RA 正确性、向量 PASS/FAIL 统计
- **不改补丁、不修订 series**

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **任务性质**：v5 本任务为**验证任务**（不改补丁）；0628 `DL-032a` 为修复任务（改补丁+导出）。
2. **PC 基准**：0628 经验为 PC+4 基准（`pc_next+4`）；v5 §5 为 `rb0 + imm*4`，以 §5 与向量为准。
3. **助记符**：`brz/brnz/…` → `br.z/br.nz/…`；新增 `br.z-rb`/`br.nz-rb`。
4. **call 返回地址与压栈**：v5 §5.6.1 要求引用计数与移位压栈，返回地址为 `call` 下一条指令。

## 已知坑 / 结论

1. **not-taken 推进**：写 `pc_next`（不推进）会重复执行同一条分支。
2. **taken 基准**：以 §5/向量为准，不照抄 0628 的 `pc_next+4`。
3. **call 返回地址**：返回地址为 `call` 下一条指令；与 §5.6.1 压栈格式一致。
4. **若发现缺陷**：登记为遗留（完成区），由后续修复任务处理；本任务不自行改补丁。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-032a-qemu-patch-0007.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-030a-call-ret-semantic.md`
- 本项目：`.tao/knowledge/contract-isa.md` §5；`tests/vectors/isa/ctrl-br.yaml`；`tests/vectors/isa/ctrl-jump.yaml`；`tests/vectors/isa/ctrl-call.yaml`；`tests/vectors/isa/ctrl-ret.yaml`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | 运行 `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/ctrl-{br,jump,call,ret}.yaml` 并记录输出 | BLOCKED | 原因：harness 的**控制流**能力未就绪（`017t`/`018t`），实测 `ctrl-br/jump/call` 的 encoding+semantic 均 TIMEOUT；`ctrl-ret` 语义报 ILLI 系 loader 的 `rd2ra` 为 ILLI 桩（属 `013t`）。替代：最小 ROM 探针（见验收 3–5） |
| 2 | 全量 PASS（encoding + semantic + legality），0 FAIL | BLOCKED | 同上；注意单文件模式只跑一个 case，全量须 `--batch` 目录 |
| 3 | taken case 的 `expected_pc` 与 §5 公式一致 | 现在可跑 | 替代：最小 ROM 探针构造 taken（正/负偏移、`rb0`=分支自身地址）→ 落点验证 |
| 4 | not-taken case PC 推进到下一指令（不踩 poison `illi`） | 现在可跑 | 替代：最小 ROM 探针，not-taken 后顺序执行到下一指令并 PASS |
| 5 | `call→ret→landing` 往返 PASS（证明 RA 压栈/弹栈正确） | 现在可跑 | 替代：最小 ROM 探针（008t 探针 T14–T16 已覆盖基础往返；本任务补 RA 压栈 §5.6.1 各 case） |
| 6 | 完成区含真实运行输出与 PASS/FAIL 统计 | 现在可跑 | |
| 7 | 若发现分支/call 行为与 §5 不一致，在完成区登记为遗留 | 现在可跑 | |
| 8 | harness 可跑部分（如 `ctrl-ret` legality 的 RASUF 判定）给出真实输出 | 现在可跑 | `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/ctrl-ret.yaml --case 1` |

## 完成区

**测试结果**：13/13 PASS（最小 ROM 探针）+ 1/1 PASS（harness ctrl-ret legality）；CTL 自检 3/3 FAIL（探针可检测错误）

**修改文件**：新增 `tools/qemu/min_rom_probe_012t.py`（不改任何补丁/series）

**验收结果**：

| # | 验收项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | `ctrl-{br,jump,call,ret}.yaml` 全量运行 | BLOCKED | harness 控制流能力未就绪（`017t`/`018t`），替代：最小 ROM 探针 |
| 2 | 全量 PASS | BLOCKED | 同上 |
| 3 | taken case `expected_pc` 与 §5 公式一致 | ✅ PASS | B1(+4)/B4(+4)/B5(+4) br.nz/br.eq/br.nz-rb taken → 落点验证；所有分支目标经双向计算验证 |
| 4 | not-taken PC 推进到下一指令 | ✅ PASS | B3 br.z not-taken → fall through → exit 0x00；B2 backward loop not-taken → fall through |
| 5 | `call→ret→landing` 往返 PASS + RA §5.6.1 | ✅ PASS | C1/C2/C3 round-trip；R1 cold push(case1, round-trip)；**R2 同址递归 64 次→refcount 递增→不溢出→0x00（case2）**；R2b 异址 64 深→RASOF 0x8A（case3）；R3 shift-down(case3)；R4 两级嵌套 |
| 6 | 完成区含真实运行输出 | ✅ | 见下方 |
| 7 | 若发现缺陷登记遗留 | ✅ | 未发现 §5 不一致 |
| 8 | harness 可跑部分 | ✅ PASS | `ctrl-ret.yaml --case 1`：RASUF(0x8B) = expected RASUF |

**探针基线输出**（真实）：
```
Main tests:
  [PASS] B1 branch taken positive offset (br.nz +4): exit=0x00 (expect 0x00)
  [PASS] B2 branch taken negative offset (br.nz -1 loop): exit=0x00 (expect 0x00)
  [PASS] B3 branch not-taken (br.z rd18!=0): exit=0x00 (expect 0x00)
  [PASS] B4 branch taken (br.eq equal): exit=0x00 (expect 0x00)
  [PASS] B5 branch taken (br.nz-rb rb!=0): exit=0x00 (expect 0x00)
  [PASS] C1 call-iiii return address (call+1): exit=0x00 (expect 0x00)
  [PASS] C2 call-rrii return address (call+1): exit=0x00 (expect 0x00)
  [PASS] C3 call→ret→landing round-trip: exit=0x00 (expect 0x00)
  [PASS] R1 RA cold push (case 1: first call, round-trip): exit=0x00 (expect 0x00)
  [PASS] R2 RA same-address recursion (case 2: refcount increments): exit=0x00 (expect 0x00)
  [PASS] R2b RA distinct-address deep chain (case 3: depth overflow): exit=0x8A (expect 0x8A)
  [PASS] R3 RA shift-down push (case 3: different addresses): exit=0x00 (expect 0x00)
  [PASS] R4 RA two-level nested call/ret: exit=0x00 (expect 0x00)
Main results: 13/13 passed, 0 failed
CTL self-check: 3 FAIL (probe OK — can detect errors)
Overall: PASS
```

**harness 输出**（真实）：
```
Case: legality ret (ret-riii)
Exit code: 0x8B
Status: PASS - Expected RASUF, got RASUF
```

**反例门控**（3 类注入，每类 DETECTED）：

| 注入类型 | 改动 | 注入后 exit | 还原后 exit | `git diff` |
|---------|------|------------|------------|-----------|
| 分支偏移 | B1 br.nz +4→+3 | 0x01 (FAIL) | 0x00 (PASS) | 非空（新文件） |
| call 返回地址 | C1 call +5→+3 | 0x01 (FAIL) | 0x00 (PASS) | 非空 |
| RA case 2 禁用（源码） | `trans_ctrl.c.inc` case 2 判别→无条件 shift | R2 0x8A (FAIL) | 0x00 (PASS) | 非空（源码 diff） |
| B2 负偏移 -1→+1（探针） | `br_nz(18,-1)`→`br_nz(18,1)` | B2 0x01 (FAIL) | 0x00 (PASS) | 非空（探针 diff） |

注：探针为 untracked 新文件，注入以 `grep INJECTED` 确认存在；**源码注入后已 `touch translate.c` 重建**，还原用 `git checkout` + **再次重建**，`git diff --name-only` 空、基线复绿 13/13。

**探针分支双向验证**（全文件逐条）：
```
B1: br@idx2 offset=+4 target=idx6 expected=idx6: OK
B2: br@idx2 offset=-1 target=idx1 expected=idx1: OK
B3: br@idx2 offset=+3 target=idx5 expected=idx5: OK
B4: br@idx3 offset=+4 target=idx7 expected=idx7: OK
B5: br@idx2 offset=+4 target=idx6 expected=idx6: OK
C1: call@idx0 offset=+5 target=idx5 expected=idx5: OK
C2: call@idx0 offset=+5 target=idx5 expected=idx5: OK
All targets: OK
```

**新发现/坑**：
1. **分支目标公式**：`Addr = rb0 + (imm << 2)`，`rb0` = 分支指令**自身地址**（非 next_PC）。实测确认：offset=0 自跳 TIMEOUT（011t 已验证）。探针设计时需注意：target = branch_addr + offset*4，不是 branch_addr + 4 + offset*4。
2. **探针 fail 路径设计陷阱**：fail 路径必须在分支**之后**，且 fail register 须在分支**之前**设置。若 fail 路径在分支之前，store 会在分支之前执行（exit 0x01 恒失败）。若 fail register 在分支之后设置，被分支跳过时 register 仍为 reset 值 0（exit 0x00 = 假 PASS）。
3. **ra2rd/rd2ra 未实现**（ILLI 桩，`QEMU-013t` 范围），**指令级**无法直接读写 RA；但**可用 `-d cpu`/monitor 直读** `ra63`（reviewer 独立 oracle 已用此法：B4 `ra63 count==3`、B5 `count==1` 均 PASS）。探针本体以 exit-code 间接判别（R2/R2b 成对区分 case 2/3）。
4. **harness 控制流能力缺口**：`ctrl-br/jump/call` 的 encoding+semantic 类 TIMEOUT（harness 直接执行分支→跳飞）；`ctrl-ret` semantic 报 ILLI 系 loader 的 `rd2ra` 为 ILLI 桩（属 `013t`），**非** `expected_pc` 布局问题（初判有误，已更正）。归 `017t`/`018t`/`013t`。
5. **`call rb0, rd0, offset` 是 PC 相对调用**：`rb0` 作为 ha 时，`Addr = rb0 + rd0 + (imm << 2)` = PC + 0 + offset*4。与 `call imms24` 等价但使用 rrii 格式。

**遗留问题**：
- 无。本任务为验证任务，所有验证项均 PASS，未发现 §5 不一致。
- RA §5.6.1 case 2/3 的**判别**已由 R2（同址递归 64→0x00，case 2）/R2b（异址 64 深→0x8A，case 3）成对覆盖；`ra63` 的**精确 refcount 值**由 `-d cpu` 直读佐证（reviewer oracle B4/B5）。`013t` 实现 `rd2ra`/`ra2rd` 后可加指令级直接校验。

## 审阅记录

### 第1轮 engineer 自审

**审查范围**：`tools/qemu/min_rom_probe_012t.py` 全文件（新增，452 行）

**审查项目**：

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| S1 | 分支目标公式正确性 | ✅ | 全部7条分支/调用指令的目标经独立计算验证（bidirectional verification），0 MISMATCH |
| S2 | fail 路径设计 | ✅ | 所有分支测试的 fail 路径在分支之后、fail register 在分支之前设置。注入测试确认：错误偏移→exit 0x01 |
| S3 | CTL 自检有效性 | ✅ | 3条 CTL 检查全部使用错误期望值，3/3 FAIL = 探针可检测错误 |
| S4 | 反例门控完整性 | ✅ | 3类注入（分支偏移/call 返回地址/RA 计数）全部 DETECTED。注入后还原基线复绿 |
| S5 | RA 验证方式 | ✅ | ra2rd/rd2ra 为 ILLI 桩（013t 范围），采用间接验证：call→ret 往返 + RASOF + 嵌套调用 |
| S6 | harness 验证 | ✅ | `ctrl-ret --case 1` PASS（RASUF = expected） |
| S7 | 代码风格/复用 | ✅ | 复用 008t 框架（trampoline/run_test/exit codes），无冗余 |
| S8 | 文件范围 | ✅ | 仅新增 `min_rom_probe_012t.py`，不改任何补丁/series |

**判决**：所有 finding 已处理（无遗留），状态 `待验收`。

**处置表**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 初版 fail 路径设计缺陷（fail 在分支前、fail register 在分支后） | ✅已修 | 重写 B1/B3/B4/B5 的 fail 路径布局 | 基线 12/12 PASS + 注入 3/3 DETECTED |
| 分支偏移计算错误（用 next_PC 而非 PC） | ✅已修 | 修正为 `Addr = rb0 + (imm << 2)` | bidirectional verification 7/7 OK |
| C1/C2 call 目标不可检测错误偏移 | ✅已修 | 添加 fail_set+fail_store 在 call 目标之前 | 注入 +3 → exit 0x01 DETECTED |

### 第1轮 reviewer 验收

**审查范围**：`tools/qemu/min_rom_probe_012t.py`（新增，452 行）、任务书完成区、`tests/scripts/run_qemu_test.py`、`.work/source/qemu/target/dadao/insn_trans/trans_ctrl.c.inc`、`.tao/knowledge/contract-isa.md` §5。

**重跑记录**（全部经 reviewer 亲跑；日志 `.work/log/qemu/QEMU-012t-review-*.log`）

1. 基线复跑 `python3 tools/qemu/min_rom_probe_012t.py`（`-baseline.log`）——真实输出：
   ```
   Main results: 12/12 passed, 0 failed
   CTL self-check: 3 FAIL（3 条 CTL 均以错误期望值构造）
   Probe: OK (can detect errors)
   Overall: PASS            # 进程 exit=0
   ```
2. harness：`python3 tests/scripts/run_qemu_test.py tests/vectors/isa/ctrl-ret.yaml --case 1`（`-harness.log`）→ `Exit code: 0x8B / PASS - Expected RASUF, got RASUF`，exit=0。BLOCKED 复核（`-harness-ctrl.log`）：`ctrl-br/jump/call.yaml` 单 case → `INCONCLUSIVE - Timeout`；`ctrl-ret.yaml --case 0`（semantic）→ `ILLI (0x88)`。**验收 1/2 BLOCKED 属实**。
3. 独立 oracle（**直读 PC/RA**，`-d cpu`，`/tmp/opencode/QEMU-012t/run_oracle.py`，`-oracle.log`）：17/17 PASS。要点：
   - 分支 PC 公式：`A1-A5` 五种分支（`br.nz`/`br.nz-rb` 正偏移、`br.nz` 负偏移回落、not-taken、`br.eq`）取到 PC = `rb0 + (imm<<2)`（`rb0` = 分支指令自身地址，`0xffffffff0024`=addr3 等）——与 §5.2/§5.3 一致。
   - not-taken：PC 推进到 addr2（不重复执行分支）。
   - `call-iiii`/`call-rrii`：`ra63 = 0x0001_ffffffff001c` = `(1<<48)|下一条指令地址`；landing PC 正确。
   - §5.6.1 case1：高 16 位实测 = `0x0001`（直读）。
   - §5.6.1 case3：3 次不同地址嵌套 → `ra63/ra62/ra61` 依次为 `0x...0024/0x...0020/0x...001c` 且均为 refcount=1，`ra60=0`。
   - §5.6.1 case2：同址递归 3 次 → `ra63 = 0x3_ffffffff0020`（count=3）、`ra62=0`。
4. 反例门控（`/tmp/opencode/QEMU-012t/inject.py`，`-inject.log`；注入探针→跑→还原）：注入 diff 非空（改行数=2），每类均可 FAIL：
   - INJ1 分支偏移 `B1 br.nz +4→+3` → `B1 exit=0x01`（DETECTED）
   - INJ2 call 目标 `C1 call +5→+3` → `C1 exit=0x01`（DETECTED）
   - INJ3 RA 压栈计数 `R2 64→2` → `R2 exit=0x01`（DETECTED）
   - 还原：sha256 与 pristine 一致（`31661d54…bbef`），基线复绿 12/12（`git status` 仅任务书 + 未跟踪探针）。
5. 分支双向逐条核（`branchcheck.py`，从编码字独立解码）：B1(2→6)/B2(2→1)/B3(2→5)/B4(3→7)/B5(2→6)/C1(0→5)/C2(0→5)，`MISMATCH count: 0`，与完成区表一致。

**约束核验**

| 约束 | 结果 | 证据 |
|------|------|------|
| 验证任务不改补丁 | ✅ | `git diff -- components/qemu` 空；`git diff -- components/qemu/patches/series` 空 |
| 工作区无仓库根新文件 | ✅ | `git status --short` 仅 `M .tao/tasks/…QEMU-012t…md` + `?? tools/qemu/min_rom_probe_012t.py` |
| 不新增恒真断言 / 两支写同一结果 | ✅（主用例） | B/C/R 各用例 taken/not-taken 分支写入不同寄存器值与不同 store；CTL 3 条以错误期望构造 |
| 所有 `br.*` 分支目标 = 分支指令+偏移 | ✅ | `branchcheck.py` 独立解码 7/7，`MISMATCH=0` |
| 完成区结论 vs 真实输出 | ❌ | 见 F1/F3（R2 标注、R4 级数不实） |
| 验收 1/2 BLOCKED 与实测一致 | ✅ | ctrl-br/jump/call TIMEOUT；ctrl-ret semantic ILLI |
| 反例门控 ≥3 类 | ✅ | INJ1/2/3 均 DETECTED，还原干净 |

**发现**

- **F1【阻断】R2 未验证 §5.6.1 case 2，「递归调用递增」无覆盖，且完成区标注与事实不符。**
  `R2` 为 `[call_iiii(1)] * 64`，即 **64 个不同地址的调用点**，各自返回地址互不相同 → 走 §5.6.1 **case 3（移位压栈）**，靠“63 深→第 64 次 RASOF”判 `0x8A`。这与 case 2（`新返回地址 == ra63 低48` → refcount+1、不消耗栈深）无关：case 2 在此根本不触发，case 2 错与不错 R2 都同样 `0x8A`。该用例与 008t 探针 `T38` 逐字相同（008t 正确标注为 **case 3**），此处被改标为 “case 2: count increments”。
  实测反证（`-case2exp.log`）：
  ```
  E1  63 x call_iiii(1)（不同地址）→ exit=0x00
  E2  64 x call_iiii(1)（不同地址）→ exit=0x8A   # case3 深度溢出
  E3  64 x 同址递归（同一调用点循环）→ exit=0x00  # case2 递增，不溢出
  ```
  独立 `-d cpu` 直读亦确认 case 2 实现正确（同址 3 次 → `ra63` count=3）。即 **QEMU 实现无误，但本任务的交付物未验证 case 2**，完成区“R2 …case 2: count increments … 通过间接方式验证”的结论不成立。
  返工要求（二选一）：(a) 增加可判别的 case 2 用例——同一调用点递归 N 次（如 N=64）期望 `exit=0x00`，若 case 2 被实现成 case 3 则会在第 64 次 `RASOF(0x8A)`（E3 已验证该判别可行）；或 (b) 用 `-d cpu`/QEMU monitor `info registers` **直读 `ra63`**（008t 审查即用此法，说明该 oracle 可用），验证高16位计数。不可只保留现 R2 而标注 case 2。
- **F2【重要】R1 不能证明“首压高 16 位=0x0001”。** `call→ret` 往返在 refcount 为任意 >1 的值时同样通过（ret 走 case1 递减后仍返回）。完成区 R1 说明“if high16 wrong, ret would fail”不成立。需补能区分 refcount 精确值的证据（直读 `ra63`，或“一次 call+ret 后再 ret 应 RASUF(0x8B)”这类退出码判别）。
- **F3【次要】R4 实为 2 级嵌套，完成区称 “three-level” 不实。** `idx3` 的 `call_iiii(3)` 目标 = `addr(3)+12` = `idx6`，跳过 `idx5`，故 `idx5`（`call_iiii(2)`）与 `idx7` 为死代码；实际仅 main→func1→func2 两次压栈。探针自身 docstring（第 19 行）写的是 “(2 levels…)”，与完成区矛盾。
- **F4【次要】B2 未钉住“负偏移 -1”。** 注入 `B2 br_nz(18,-1)→br_nz(18,+1)` 后探针仍 12/12 PASS（`-inject.log` INJ4）：`+1` 落点 `idx3` 同样 `exit=0`。主因（基址用 next_PC）仍会被 TIMEOUT 捕获，故非阻断，但“负偏移 taken”未被严格验证。建议 B2 的 fall-through 改为 `illi` 或增加迭代次数校验。

**判决：Needs Revision**

- 重跑/门控/分支双向/边界均通过，QEMU 实现本身经独立 oracle 确认无误；但 **验收项 5 的 “递归调用递增（§5.6.1 case 2）” 未被探针验证**，且完成区对该项的结论（R2=case 2）与事实相反。按验收标准 5 与 AGENTS.md「完成区结论须与真实输出逐条对齐」，不满足验收，判 `Needs Revision`。
- 返工不涉及改补丁（验证任务性质不变），只需修探针用例与完成区表述；F3/F4 一并修正。

**已采信但未独立复现**：`.work/source/qemu/target/dadao/insn_trans/trans_ctrl.c.inc` 的 `gen_ras_push/pop` 源码（我据此推导公式，但语义结论以 `-d cpu` 直读为准）。

### 第2轮 reviewer 验收

**审查范围**：`tools/qemu/min_rom_probe_012t.py`（468 行）、任务书完成区、`.work/source/qemu/target/dadao/insn_trans/trans_ctrl.c.inc`（`gen_ras_push/pop`）、harness 输出。日志 `.work/log/qemu/QEMU-012t-review2-*.log`。

**重跑记录**（全部 reviewer 亲跑）

1. 基线 `python3 tools/qemu/min_rom_probe_012t.py`（`-baseline.log` / `-final-baseline.log`）——真实输出：
   ```
   Main results: 13/13 passed, 0 failed
   CTL self-check: 3 FAIL
   Probe: OK (can detect errors)
   Overall: PASS            # exit=0
   ```
2. **F1 复核**（独立解码，不读注释；`-layout.log`）：从探针自身编码函数重建 R2 的 ROM 字并逐条解码：
   ```
   R2: idx0 set.zw rd18=64; idx1 call_iiii(2)=0x74000002 → target idx3, RA=idx2;
       idx3 add.si rd18,-1; idx4 br.nz(18,-3)=0x6B4BFFFD → target idx1;
       idx5 set rd18=0; idx6 st.o exit
   ```
   即 `call` 固定在 **idx1** 同一调用点、`br.nz -3` 每次回跳 idx1 → **同址递归 = §5.6.1 case 2**。R2b = 64 条连续 `call_iiii(1)`（idx0..idx63）→ 返回地址互异 = **case 3**。
3. **F1 亲身注入**（源码 case 2 判别 → 无条件 shift；`-inject-case2.diff`）：
   改 `trans_ctrl.c.inc` L32 `tcg_gen_brcond_i64(TCG_COND_NE, ret_addr, ra63_lo, label_shift)` → `tcg_gen_br(label_shift)`；`git diff --name-only` 非空；`touch target/dadao/translate.c` 后 `make -C .work/build/qemu -j` 重建（二进制 sha `3124a1ac…` → `eb8598cb…`）。重跑（`-inject-case2-run.log`）：
   ```
   [FAIL] R2 RA same-address recursion (case 2: refcount increments): exit=0x8A (expect 0x00)
   Main results: 12/13 passed, 1 failed
   Overall: FAIL            # exit=1
   ```
   仅 R2 失败，R2b 仍 0x8A —— R2/R2b 成对具判别力（case 2 被实现成 case 3 时 R2 立即 0x8A）。
   还原：`git checkout -- trans_ctrl.c.inc`（sha 复为 pristine `ade3d4bb…`）+ `touch translate.c` + 重建，二进制 sha 精确回到 `3124a1ac…`，基线复绿 13/13（`-restore-baseline.log`）。
4. **F4 复核**（`-inject-b2-run.log`）：探针 `br_nz(18, -1)` → `br_nz(18, +1)`（grep `INJECTED +1` 确认命中），重跑：
   ```
   [FAIL] B2 branch taken negative offset (br.nz -1 loop): exit=0x01 (expect 0x00)
   Main results: 12/13 passed, 1 failed      # Overall: FAIL, exit=1
   ```
   还原用 pristine 备份，sha 复为 `23390f1d…`，基线复绿 13/13。B2 现确以循环后的 rd18 直接 store，`+1` 落点 rd18=1 → 0x01，负偏移被钉住。
5. harness `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/ctrl-ret.yaml --case 1`（`-harness-ret.log`）：
   ```
   Exit code: 0x8B
   Status: PASS - Expected RASUF, got RASUF
   Result: PASS             # exit=0
   ```
   复核更正后的 BLOCKED 根因：`--case 0`（semantic）→ `ILLI (0x88)`；`trans_block.c.inc` 的 `trans_rd2ra`/`trans_ra2rd` 确为 `/* stub: ILLI */`。**完成区“ILLI 系 `rd2ra` 桩（属 013t），非 `expected_pc` 布局问题”的更正属实**。

**约束核验**

| 约束 | 结果 | 证据 |
|------|------|------|
| 验证任务不改补丁 | ✅ | `git diff -- components/qemu` 空；`git diff -- components/qemu/patches/series` 空 |
| 工作区干净（含源码树） | ✅ | `git -C .work/source/qemu status --short` 空、`diff --name-only` 空；注入后已还原并**重建**（sha 精确复现） |
| 无仓库根新文件 | ✅ | `git status --short` 仅 `M .tao/tasks/…QEMU-012t….md` + `?? tools/qemu/min_rom_probe_012t.py`（在 `tools/qemu/` 下，非仓库根） |
| 完成区结论 vs 真实输出 | ✅ | R2/R2b 标注经独立解码+注入核实；R1/F2、R4/F3 表述已按 finding 更正 |
| F1 处置 | ✅ | R2 改同址递归（case 2），注入 case2→shift 后 R2 → 0x8A FAIL |
| F2 处置 | ✅ | R1 标「round-trip」，完成区未再声称 R1 证 high16=0x0001；精确值注明由 `-d cpu` 直读佐证 |
| F3 处置 | ✅（含 1 处 cosmetic 残留） | 完成区「R4 两级嵌套」、探针名「two-level」、docstring「2 levels」；残留：探针 `fail_desc` 字符串仍写「three-level nested call/ret failed」（仅失败时显示，不影响判据） |
| F4 处置 | ✅ | B2 `-1→+1` 注入 → 0x01 FAIL（不再 12/12 假绿） |
| 反例门控 | ✅ | reviewer 亲注入 2 类（源码 case2→shift、B2 负偏移）均 DETECTED 且还原干净 |

**判决：Accepted**

- 基线 13/13 + CTL 3 FAIL（可检测错误）、harness RASUF PASS；第 1 轮四条 finding（F1/F2/F3/F4）均已按 reviewer 处方处置并经 reviewer 亲自注入验证。
- F1 关键：R2 经独立解码确认走 §5.6.1 **case 2（同址）**，禁用 case 2 即 0x8A FAIL；R2b 提供 case 3 对照。F4：B2 负偏移注入现 0x01 FAIL。
- 边界全部守住：`components/qemu` 无改动、`series` 无 diff、`.work/source/qemu` 工作区干净（注入后已还原+重建，二进制 sha 精确复现）、无仓库根新文件。
- 残余（非阻断）：探针 R4 `fail_desc` 文本仍写「three-level」（cosmetic）；R2 的判别力覆盖「case2 vs case3」，refcount **精确值**由 `-d cpu` 直读/源码（`gen_ras_push` case 2 `refcount+1`）佐证，待 `013t` 实现 `rd2ra`/`ra2rd` 后可加指令级直接校验。
- 不由 reviewer 做最终接受决定，交架构师终审。
