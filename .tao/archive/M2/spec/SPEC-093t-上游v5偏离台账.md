# SPEC-093t: 上游 ↔ v5 偏离台账（MEMORY.md 新增节）

**模块**：spec
**项目里程碑**：M2
**依赖**：无
**状态**：已验证

## 目标

在 `.tao/knowledge/MEMORY.md` 新增一节 **「上游 ↔ v5 偏离台账」**，收录 **6 项**上游 spec 与 v5 决策之间的**规范性偏离**，每项给出：偏离点、上游依据、v5 决策、**ADR 指针**、影响/状态。作为 M2 门槛⑤的交付物，使 M3 codegen 的实现者能一眼看到「哪些地方 v5 ≠ 上游」。

## 背景与现状（实测）

- 该台账来源与建议清单见 `docs/m2-spec-planning.md §3 第 3 层` 与 `§4.2`（讨论稿）。
- v5 的偏离均已由 **已 Accepted 的 ADR** 固化，本任务只做**归一化登记 + 指针**，**不新增决策**。
- `.tao/knowledge/MEMORY.md` 现状：`## 当前进度`（大表）+ `## 关键目录速查` + `## 重要决策` + `## 如何参考…` 等节。新增节须不破坏既有表格。

## 交付物

`.tao/knowledge/MEMORY.md` 新增节 **`## 上游 ↔ v5 偏离台账`**（建议置于 `## 关键目录速查` 之前或 `## 重要决策` 之后，择一不影响既有表格），含 6 项（表格或列表，逐项）：

| # | 偏离点 | 上游依据 | v5 决策 | ADR 指针 |
|---|--------|----------|---------|----------|
| 1 | **exit port（程序停机）** | `SimRISC-04 §退出指令`：`escape cfx_<name>, imms18`（退出特权态，非停机） | 自定 **exit port** MMIO（`0xffff_8000_0000`，8 B，只写）；退出码 = `0x80 \| cause_bit`；写入后 `cpu_loop_exit()` 锁定 | **ADR-0004 §D3**（Exit Port 协议）+ **ADR-0011 §D1–D4**（可靠性补全） |
| 2 | **`fence` SBZ 非零** | `SimRISC-04 §fence`：`bits[17:4]` 为 SBZ，**非零值行为保留** | v5 定**非零 SBZ → ILLI**（`0x88`）；且 `fence` 整体 `scope: excluded`（未实现，decode ILLI） | **ADR-0004 §D5.3**（SBZ 非零 → ILLI）+ **ADR-0014 §D1–D3**（fence 移出 M1） |
| 3 | **测试机地址映射 / 复位值** | `spec/` **无测试机层**（`DADAO-12 §2` 仅给地址空间模型，无内存映射/复位值全集/exit 协议） | 采用 spec **核内地址空间模型**（cfxha 63/power）：boot ROM `0xffff_ffff_0000`、RAM `0xffff_0000_0000`(16 MiB)、Exit port `0xffff_8000_0000`；复位 PC=`rb0`=boot ROM；确定复位 `rd0`/`rf0`/RF 全 0 | **ADR-0004 §D1/D2**（内存映射、复位向量与复位值） |
| 4 | **`ra0` 语义（MemRAS 简化）** | `SimRISC-00 §返回地址栈`：`ra0` 高 16 位含 **MemRAS 引用计数** | v5 `ra0` = `[63:54]` SBZ + `[53:48]` **`RACNT`** + `[47:0]` **`MRPTR`**；**取消 MemRAS 引用计数**；有效性判据 = `RACNT` | **ADR-0012 §D7**（D7.1–D7.7） |
| 5 | **`e_flags` 版本字段** | `spec/` **无 ELF/Object ABI**（`e_machine`/`e_flags` 无依据） | `e_machine = EM_DADAO (0x0DA0)`（project-custom，未注册）；`e_flags = 0x00000001`（bits 0–7 = 对象/ABI 格式版本 = 1；bits 8–31 保留 0） | **ADR-0003 §D1**（含 `## 修订` 的 `e_flags` 版本字段） |
| 6 | **M1/M2 排除口径**（**订正**） | 上游把浮点（`SimRISC-03`）、特权 cfx（`DADAO-12/13`）、LR-SC（`SimRISC-12`）、`fence` 均定义为架构指令 | v5 用 `scope ∈ {m1, fp, excluded}` 划范围：`m1` 已实现；**`fp` 60 条已实现（不再是 ILLI）**；`excluded` 15 条（cfx 6 + fence 1 + LR-SC 8）仍 decode **ILLI** | **ADR-0012 §D3.1**（0 号寄存器/范围）+ **ADR-0014**（fence excluded）+ `SPEC-086t`（scope 口径，`contracts/opcodes.yaml` + `check_scope.py`） |

> **订正说明（第 6 项）**：历史表述「浮点未实现 ⇒ decode ILLI」在 `QEMU-034t`~`037t`（执行层 60/60）后**已不成立**；现行口径为「**浮点已实现**（`scope: fp`），**仅** cfx/LR-SC/fence（`scope: excluded`）仍 ILLI」。本台账以此为准。

## 约束

- **不臆造**：第 1–6 项的 ADR 指针、decision 编号、spec 章节**必须逐一实测核对**（`grep` ADR 文件确认 `D1`/`D3`/`D7`/`D5.3` 等真实存在，且 ADR 状态 `Accepted`）；表述与 ADR 原文一致，不新增/改写决策。
- **纯登记**：不新增 ADR、不改任何 `spec/`/`contracts/`/`tools/`；只往 `MEMORY.md` **追加**一节（不改写既有行/表）。
- 格式：新增节不得破坏 `MEMORY.md` 既有 markdown 表格（表内无空行、无连续空行、文件尾无空行）。
- 术语一致：`scope`、`RACNT`、`MRPTR`、exit 码等用与 `contracts/opcodes.yaml`/ADR 一致的写法。
- ADR 提醒：本任务为**登记已 Accepted 决策**，**不立新 ADR**。

## 验收标准

1. `MEMORY.md` 含新节 `## 上游 ↔ v5 偏离台账`，**恰好 6 项**，覆盖：exit port / fence SBZ / 测试机地址映射+复位值 / `ra0`(MemRAS) / `e_flags` / M1-M2 排除口径。
2. 每项含：偏离点、上游依据、v5 决策、**ADR 指针**（文件 + decision 编号）；6 项的 ADR 指针经实测**全部可定位**（独立复算：`grep` 到对应 decision 且 ADR `Accepted`）。
3. 第 6 项**已订正**为「浮点已实现、不再 ILLI；余 cfx/LR-SC/fence 仍 ILLI」，与 `contracts/opcodes.yaml`（`scope` 分区 152/60/15）一致。
4. `MEMORY.md` 既有表格未被破坏（`git diff` 只新增节；表格行/列完好；无表内空行、无文件尾空行）。
5. 纯文档改动：以 `git status`（仅 `MEMORY.md`）目视 +（如适用）`make check-no-residue` 为准。
6. **反例门控**：一键证据脚本内置「注入反例→预期 FAIL→还原→预期回绿」（如把某项 ADR 指针改成不存在的编号 → 自检 FAIL），并在完成区给出真实输出与退出码。

## 完成区
**测试结果**：一键证据脚本 `.work/evidence/SPEC-093t/run.sh` **EXIT=0**（4 阶段全过：REAL=0 / INJECT_A=1 / INJECT_B=1 / GREEN=0，共 43 项检查 0 FAIL）；`make check` **EXIT=0**（`repository checks: PASS`，lit 31/31）；`make check-no-residue` **EXIT=0**（PASS）。
**修改文件**：`.tao/knowledge/MEMORY.md`（`git diff --numstat` = `17  0`，**仅新增** `## 上游 ↔ v5 偏离台账` 一节，未删改既有行/表）。新增证据脚本/日志在 gitignore 的 `.work/` 下（`.work/evidence/SPEC-093t/{run.sh,check_ledger.py}`、`.work/log/spec/SPEC-093t-*.log`），不入库。**未越界**。
**验收结果**：
- 台账节含 **恰好 6 项**，覆盖 exit port / fence SBZ / 测试机地址映射+复位值 / `ra0`(MemRAS) / `e_flags` / M1-M2 排除口径（C1/C2/主题 6 项 PASS）。
- 6 项 ADR 指针**全部实测可定位**（C4 + C5）：`ADR-0004 §D3`/`§D1`/`§D2`/`§D5.3`、`ADR-0011 §D1–D4`、`ADR-0014 §D1–D3`、`ADR-0012 §D7`/`§D3.1`、`ADR-0003 §D1`（含 `## 修订`）；5 个 ADR 状态行均含 `Accepted`；`SPEC-086t` 状态 `已验证`；`contract-elf.md §1.3` 存在；`ADR-0012` 含 `D3.1`。
- 第 6 项已订正：台账文本含「**浮点已实现**」「**不再是 ILLI**」；`contracts/opcodes.yaml` 实测 `scope` 分区 **m1=152 / fp=60 / excluded=15 / total=227**（与 `check_scope.py` 一致）。
- 表内无空行、文件尾无空行（C7/C8 PASS）。
- 反例门控真实输出（见 `.work/log/spec/SPEC-093t-evidence.log`）：INJECT_A 把 `ADR-0012 §D7`→`§D99` ⇒ `[FAIL] 指针 item4 ra0 -> ADR-0012 §D7`、rc=1；INJECT_B 删第 6 行 ⇒ `[FAIL] C2 台账恰好 6 项` + `[FAIL] 主题 item6`、rc=1；两注入均在 `/tmp` 副本，运行前后被测文件 SHA256 一致（`7ca9468a…`）、回绿 rc=0。
**新发现/坑**：
- **任务书 spec 章节号沿用 SimRISC 0.5.3 编号**：① exit port vs `escape` 任务书作 `SimRISC-04 §退出指令`，0.5.4 实测为 **`SimRISC-11 §退出指令`**（且 0.5.4 语法为 `escape cfxHA, [excp_cause_ip, imms20]`，编码层 `imms18`）；② `fence` 任务书作 `SimRISC-04 §fence`，实测为 **`SimRISC-12 §fence指令`**；③ 浮点任务书作 `SimRISC-03`，实测为 **`SimRISC-07`**（0.5.3 中 `SimRISC-03`=浮点、`SimRISC-04`=系统类指令；0.5.4 已重排）。已按实测订正并在台账加「章节订正（实测）」脚注；**建议沉淀**：后续任务勿沿用 `docs/m2-spec-planning.md` 的 0.5.3 章节号。
- **任务书 item3 复位值表述有误**：「确定复位 `rd0`/`rf0`/RF 全 0」与 `ADR-0004 §D2.1` 不符——`rf0` 复位常量 = `0x7FF8_0000_7FC0_0000`、`rb0` 复位 = boot ROM 基址（非 0）。已按 ADR 原文精确化（`rd0`/`rb1`–`rb63`/`ra0`–`ra63`/`rf1`–`rf63` = 0、`rf0` = `0x7FF8_0000_7FC0_0000`）。
- **工作区存在其它并行任务的未提交改动**（`README.md`、`spec/Process-02-…`、`spec/README.md`、`tools/infra/check_spec_drift.py`，以及未跟踪 `tests/e2e/smoke_fp.s`、`tests/lit/E2E/smoke_fp.test`），**非本任务所为，未触碰**；`make check` 在这些改动并存下仍 EXIT=0。
**遗留问题**：无。建议主会话 `make check` 交叉时注意上述并行改动归属。

## 审阅记录

#### 第 1 轮 engineer 自审
自审方式：无嵌套子代理（`subagent_depth=1`），对改动逐行审查 + 用独立检查器复算。

**findings 与处置**

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 任务书 item1 上游章节 `SimRISC-04 §退出指令` 与 0.5.4 实测不符（`grep escape spec/*.md` 无命中的 SimRISC-04；实为 `SimRISC-11 §退出指令`） | ✅已修 | 台账 item1 上游依据改用 `SimRISC-11 §退出指令`（并保留编码层 `imms18`） | evidence C4 指针 + 台账节渲染；`grep -n 退出指令 spec/SimRISC-11-其它.md` → L101 |
| F2 任务书 item2 `SimRISC-04 §fence` 与实测不符（`fence` 在 `SimRISC-12 §原子指令/§fence指令`，SBZ 见 `SimRISC-12:67`） | ✅已修 | 台账 item2 改用 `SimRISC-12 §fence指令`；并用 `contracts/opcodes.yaml::fence_oiii_imm`（`scope: excluded`/`decode: ILLI`）佐证 | evidence C4/C6；`grep -n "bits\[17:4\]" spec/SimRISC-12-待定.md` → L67 |
| F3 任务书 item6 浮点作 `SimRISC-03`，实测 0.5.4 浮点为 `SimRISC-07`（`SimRISC-03`=16 位立即数操作） | ✅已修 | 台账 item6 改用 `SimRISC-07`；加「章节订正（实测）」脚注说明 0.5.3→0.5.4 重排 | `head -8 spec/SimRISC-07-浮点运算.md`；`spec/SimRISC-03-16位立即数操作.md` |
| F4 item3 任务书「复位 `rd0`/`rf0`/RF 全 0」与 `ADR-0004 §D2.1` 不符（`rf0`=`0x7FF8_0000_7FC0_0000`、`rb0`=boot ROM） | ✅已修 | item3 v5 决策改为按 ADR 原文精确化的复位值列举 | evidence 主题 item3；`adr-0004-test-machine.md` L42–L51 |
| F5 证据脚本必须「能失败」且反例可还原 | ✅已验证 | `check_ledger.py` 内含可达 FAIL 路径；`run.sh` 内置两处注入 + 还原核验 | `.work/log/spec/SPEC-093t-evidence.log`：REAL=0 / INJECT_A=1（坏 ADR 指针）/ INJECT_B=1（缺项）/ GREEN=0，SHA256 前后一致 |

**判决**：F1–F5 全部已处置，无未修项 → 状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**审查环境**：`mimo-v2.5-pro`，2026-10-04，独立会话。

**一、证据脚本审阅**

`check_ledger.py` 审阅：
- 每条断言（C1–C8、POINTERS、TOPICS、ADR_EXPECT、C5b、C6）均有可达 FAIL 路径——注入坏指针→`<未出现>`→FAIL、删行→行数不匹配→FAIL、改 scope 计数→不等→FAIL。
- 无恒真断言（`check()` 传 `bool(ok)`，非 `True`）。
- `run.sh` 内置两处注入（阶段 2: sed 改 ADR 指针→FAIL；阶段 3: sed 删第 6 行→FAIL），均在 `/tmp` 副本操作，不污染被测文件。SHA256 前后比对。无 `tee` 吞退出码。
- 脚本合格。

**二、重跑记录**

| 命令 | 退出码 | 关键输出 |
|------|--------|---------|
| `bash .work/evidence/SPEC-093t/run.sh` | **0** | REAL=0 / INJECT_A=1 / INJECT_B=1 / GREEN=0，43 项 0 FAIL，SHA256 前后一致 `84ca0aba…` |
| `make check` | **0** | lit 31/31、semantics 149/149、scope 152/60/15/227、fp-contract 60/60、interface 80/80、patch-tree 69、check-no-residue PASS、repository checks: PASS |

**三、约束核验**

| 约束 | 结果 |
|------|------|
| 仅追加（`git diff --numstat` = `17 0`） | ✅ 17 行新增、0 行删除 |
| 表内无空行 | ✅ check_ledger.py C7 PASS |
| 文件尾无空行 | ✅ check_ledger.py C8 PASS |
| 禁改区未触碰（`contracts/`/`spec/`/`.tao/archive/**`） | ⚠️ `spec/README.md` 有改动（-3+2，去掉 `contract-asm.md` 缺口），**非本任务所为**，属并行任务。本任务仅改 `MEMORY.md`。 |
| 未改既有条目/表格 | ✅ git diff 仅新增节（`## 上游 ↔ v5 偏离台账` 到 `## 如何参考…` 之间） |

**四、6 项事实性抽查（第 2/4/5/6 项）**

| 项 | 核验内容 | 结果 |
|----|---------|------|
| item2 fence | `trans_fence_oiii_imm` 补丁注释 "stub: ILLI"；`contracts/opcodes.yaml` fence `scope: excluded`；ADR-0014 存在且 Accepted | ✅ |
| item4 ra0 | ADR-0012 含 `### D7：RegRAS 有效性判据`；D7.1 "RACNT" + "MRPTR" + "MemRAS 引用计数取消" 均在原文 | ✅ |
| item5 e_flags | ADR-0003 §D1 "e_flags = 0x00000001"；contract-elf.md §1.3 同值；状态行 Accepted | ✅ |
| item6 scope | `opcodes.yaml` 实测 m1=152/fp=60/excluded=15/total=227；`decode=ILLI` 恰 15 条与 excluded 一一对应 | ✅ |

**五、披露项核验**

| 订正 | 核验 | 结果 |
|------|------|------|
| exit port `SimRISC-04`→`SimRISC-11` | `grep "退出指令" spec/SimRISC-11-其它.md` 命中 L101；`escape` 在 SimRISC-11:15 | ✅ |
| fence `SimRISC-04`→`SimRISC-12` | `grep "fence" spec/SimRISC-12-待定.md` 命中 L48 "fence指令"、L15 编码行 | ✅ |
| 浮点 `SimRISC-03`→`SimRISC-07` | `head -5 spec/SimRISC-07-浮点运算.md` 确认；`SimRISC-03` 为 16 位立即数操作 | ✅ |
| `rf0` 复位值 `0x7FF8_0000_7FC0_0000` | ADR-0004 D2.1 L50: "RF rf0 \| 0x7FF8_0000_7FC0_0000"；非"全 0" | ✅ |

**六、独立反例注入**

注入方式：复制 `MEMORY.md` → `/tmp/opencode/SPEC-093t-review/memory_inject.md` → sed 改 `ADR-0003 §D1`→`§D99`。
- 注入确认：`diff` 显示 L112 变化（非空注入）
- 脚本报 FAIL：`[FAIL] 指针 item5 e_flags -> ADR-0003 §D1`，EXIT=1
- 原文件未被污染：SHA256 = `84ca0aba…`（与运行前一致）
- 注入仅作用于 `/tmp` 副本，还原无需操作（原文件从未被改）

**判决：Accepted**

全部 6 项验收标准通过：
1. ✅ 恰好 6 项，覆盖全部偏离点
2. ✅ ADR 指针全部实测可定位（5 个 ADR 均 Accepted + SPEC-086t 已验证 + contract-elf.md §1.3 存在）
3. ✅ 第 6 项已订正为「浮点已实现、不再 ILLI」，scope 分区 152/60/15 一致
4. ✅ 既有表格完好（git diff 仅追加 17 行）
5. ✅ 纯文档改动，`make check` 全绿（禁改区 `spec/README.md` 改动属并行任务）
6. ✅ 反例门控通过（engineer 脚本 4 阶段全过 + reviewer 独立注入 FAIL→原文件未污染）

披露项全部核实正确（SimRISC 0.5.4 章节号订正 + rf0 复位值精确化）。

#### 第 1 轮 架构师复核（双模型互验）

**复核环境**：`deepseek/deepseek-flash`（架构师子代理），2026-10-04，独立会话；临时目录 `/tmp/opencode/SPEC-093t-xcheck/`；未改任何被测文件（除本审阅记录只追加）；未提交 git。

**一、独立核验（真实命令 + 输出）**

| # | 核验项 | 命令（要点） | 输出 / 退出码 | 结论 |
|---|--------|-------------|--------------|------|
| 1 | 节存在且**恰好 6 项** | `sed -n '102,118p' MEMORY.md \| grep -cE '^\| [1-6] \|'` | `6` | ✅ |
| 1 | 指针逐项可定位（实测 decision 标记 + Accepted） | `grep -nE '^#+ D[0-9]' .tao/adr/adr-000{3,4}-*.md`、`adr-001{1,2,4}-*.md` | ADR-0004 有 `D1/D2/D3`(L19/38/88)、`D5.3`(L147)；ADR-0011 `**D1—**…`(L24–30)；ADR-0014 `- **D1**…`(L23–26)；ADR-0012 `D3.1`(L47)、`D7`(L71)；ADR-0003 `D1`(L24)+`## 修订`(L131)；5 ADR 状态行均含 `Accepted` | ✅ |
| 1 | 事实性抽查 | 见下「二」 | — | ✅ |
| 2 | 仅追加 | `git diff --numstat -- .tao/knowledge/MEMORY.md` | `17	0`（17 增 0 删） | ✅ |
| 2 | 表内无空行 / 文件尾无空行 | `awk 'NR>=107&&NR<=113&&$0==""'`；`tail -c 60 \| od -c` | 无空行；末字节 `\n`（无尾空行） | ✅ |
| 2 | 未触碰禁改区 | `git status --short` | 本任务产物仅 `MEMORY.md`（+ 任务书自身）；`spec/README.md`、`README.md`、`spec/Process-02`、`tools/infra/check_spec_drift.py`、`.tao/knowledge/contract-asm.md`、`tests/e2e/*` 均属**并行任务**（engineer 完成区已披露，非本任务） | ✅（保留意见，见「四」） |
| 3 | `make check` | `make check > log 2>&1; echo rc=$?` | `MAKE_CHECK_EXIT=0`；`repository checks: PASS`、`check-no-residue: PASS`、lit `31/31`、interface `80` 全 PASS | ✅ |
| 4 | 证据脚本重跑 | `bash .work/evidence/SPEC-093t/run.sh` | `SHELL_RC=0`；`REAL=0 / INJECT_A=1 / INJECT_B=1 / GREEN=0`，43 项 0 FAIL，SHA256 前后一致 `84ca0aba…` | ✅ |
| 4 | **独立注入反例**（与 reviewer 注入路径不同：改 item1 指针而非 item5） | 复制 → `/tmp/opencode/SPEC-093t-xcheck/mem_A.md`；`sed 's/ADR-0004 §D3/ADR-0004 §D9/'` | 注入非空（diff 4 行）；重跑 → `INJECT_A_RC=1`、`[FAIL] 指针 item1 exit port -> ADR-0004 §D3`；原文件从未改动（操作在 /tmp 副本） | ✅ 脚本可失败 |

**二、事实性独立核验（对照 spec / ADR / contracts 原文）**

- **`trans_fence` ILLI**：`components/qemu/patches/target/dadao/insn_trans/trans_ctrl.c.inc.patch` 中 `trans_fence_oiii_imm` 注释 `stub: ILLI`，body `gen_exception_illegal(ctx)`；`contracts/opcodes.yaml::fence_oiii_imm` = `scope: excluded` / `decode: ILLI` / `legality: immu18[17:12]==0,[11:6]==0,[5:4]==0`。✅
- **`e_flags`**：`ADR-0003 §D1` 表行 `e_flags = 0x00000001`（bits 0–7 版本=1，bits 8–31 保留 0），`contract-elf.md §1.3` 同值。✅
- **`scope` 计数**：独立解析 `contracts/opcodes.yaml` → `m1=152 / fp=60 / excluded=15 / total=227`，`decode==ILLI` 恰 15 条，excluded 15 = cfx 6 + fence 1 + LR-SC 8（`lr_*` 4 + `sc_*` 4）；`python3 tools/spec/check_scope.py` → `check-scope: PASS`（EXIT=0）。✅
- **`rf0` 复位值**：`ADR-0004 §D2.1` 表行 `RF rf0 | 0x7FF8_0000_7FC0_0000`，附独立推导 `(0xFFF<<51)|(0x1FF<<22)`。台账 item3 取值一致。✅
- **`ra0` 位域**：`ADR-0012 §D7.1`：`[63:54]` SBZ（MemRAS 引用计数取消）、`[53:48]` `RACNT`、`[47:0]` `MRPTR`；`D7.2` 有效性判据 = `RACNT`。台账一致。✅
- **item3 地址**：`ADR-0004 §D1` 表：RAM `0xffff_0000_0000`(16 MiB)、Exit port `0xffff_8000_0000`(8 B)、boot ROM `0xffff_ffff_0000`；`D2.1` `rb0` 复位 = ROM 基址。台账一致。✅

**三、披露项核验**

- `spec/SimRISC-11-其它.md`：`## 特权指令`(L74)、`### 退出指令`(L101)、`escape cfxHA, [excp_cause_ip, imms20]`(L107)——engineer 订正 `SimRISC-04→11` **正确**；编码层字段 `imms18`（`opcodes.yaml::escape_ciii_cfx`）与台账括注一致。✅
- `spec/SimRISC-12-待定.md`：`### fence指令`(L48)、`bits[17:4] 应为零（SBZ），非零值行为保留`(L67)、`### LR-SC指令`(L69)——订正 `SimRISC-04→12` **正确**。✅
- `spec/SimRISC-07-浮点运算.md` 为浮点规范（`SimRISC-03-16位立即数操作.md` 为 16 位立即数）——订正 `SimRISC-03→07` **正确**。✅
- `rf0` 复位值订正 `0x7FF8_0000_7FC0_0000`（非「全 0」）**正确**。✅

**四、补充发现（非阻塞）**

1. **证据脚本事实覆盖有缺口**（观察项，不构成验收失败）：`check_ledger.py` 的 `TOPICS` 对 item3 只查 `["复位","0xffff_8000_0000","0xffff_ffff_0000"]`，**未校验** `rf0` 复位常量、exit 码常量、`excluded` 细分计数。独立注入验证：把台账 item3 的 `rf0` 值改为 `0xDEAD_BEEF_DEAD_BEEF` 后重跑脚本 → **`RF0_INJECT_RC=0`（未检出）**。即脚本对该事实无 FAIL 路径。该事实本身经我对照 `ADR-0004 §D2.1` 原文确认**正确**，且任务 C6 只要求「能失败」，故不影响 Accepted；建议后续（非本任务）若强化，可为 item3 增加数值断言。
2. **禁改区归属**：`spec/README.md`、`README.md`、`spec/Process-02`、`tools/infra/check_spec_drift.py` 等在工作区有未提交改动，与 engineer 完成区披露一致，属并行任务；无证据表明本任务触碰，判**未越界**（保留意见，与 reviewer 一致）。
3. **`make check` 与并行改动并存仍全绿**，其中 `spec/README.md` 改动落在 `make check` 覆盖范围内（`spec/**`），说明当前检查未因该并行改动而变红——不影响本任务结论。

**五、判决**

复核独立核验：**6 项验收标准全部成立**，事实性抽查（`trans_fence` ILLI / `e_flags` / `scope` 152-60-15 / `rf0`）与披露项（`SimRISC-11/12/07`、`rf0` 复位值）**全部正确**；`make check` EXIT=0；证据脚本 4 阶段全过且经**独立注入**证伪可达 FAIL。未发现遗漏关键项或约束违反。

**架构师复核判决：Accepted（与 reviewer 一致）**。上述「四、1」为可选的证据脚本增强建议，非返工要求。
