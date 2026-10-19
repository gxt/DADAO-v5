# SPEC-150t: 帧指针回归 `rb2`（无条件保留、删别名）+ `rb63` 回归普通 callee-saved

**模块**：spec
**项目里程碑**：M8
**依赖**：`ADR-0018`（`C7 D2`/`D3`/`D6` 的决定源；**architect 已于 2026-10-19 就地修订**，见 `.tao/adr/adr-0018-m3-codegen-choices.md`「C7 D6（rev. 2026-10-19）」+「## 修订」）、`LLVM-110t`（实现面，**同批**；两册合并前不得让契约与后端长期不一致）、`SPEC-128t`（2026-10-09 把 FP 由 `rb2` 迁 `rb63`，本册回退其寄存器选择）
**状态**：待开始

## 用户授权（原话逐字，渠道 = 经主会话问答，2026-10-19）

> 「**frame pointer重新改回rb2，且删除fp/gp等别名；可以立**」
> 「**rb2：不做帧指针的时候，建议不做分配，你说呢？**」→（主会话答复「同意无条件保留」）「**好**」

- 口径：`rb2` = **无条件保留**；`hasFP` 为真时作**帧指针**；**无任何助记别名**（`rbfp`/`rbgp` 都删）。
- `rb63` 回归**普通 callee-saved**；`rb32`–`rb63` 成为**连续可分配池** ⇒ 删除现 `spec/DADAO-21:44/46` 的「`rb63` 条件式 FP / 最高编号 ⇒ `stm`/`ldm` 特例」整段。
- `-fno-omit-frame-pointer` **保留**：`hasFPImpl` 策略不变，`hasFP` 仍由它（及 VLA/取帧址/栈重对齐）触发；本册只改 **FP 的物理寄存器号** 与保留口径。
- `docs/Process-06 §2`：改 `spec/` 须用户事先明确允许 ⇒ 本册具备；授权原话须原样写入完成区。

## 问题根源

1. 2026-10-09 的 `SPEC-128t` 把 FP 从 `rb2` 迁到 `rb63`，并让 `rb63` 条件式保留、`rb2` 改作 GP（`rbgp`）。用户 2026-10-19 裁定**回退**：FP 回 `rb2`，且 GP 概念不再保留（`rb2` 无条件保留，`rb63` 只作普通 callee-saved）。
2. 现行 `spec/DADAO-21 §1.2`、`.tao/contracts/contract-abi.md`、`contracts/abi.yaml`、`.tao/contracts/contract-dynlink.md` 仍写 `rb2=rbgp` / `rb63=rbfp(条件式)`；与用户裁定和 `ADR-0018` 修订后正文矛盾。
3. `rb63` 的「最高编号 ⇒ `stm`/`ldm` 不能从它向上展开」特例只为条件式 FP 存在；`rb63` 回归普通成员后必须删除，否则会误导实现继续排除 `rb63`。

## 判据（必须写死）

- **单一真源链条**：`spec/DADAO-21`（规范正文）→ `.tao/contracts/contract-abi.md`（人读契约）→ `contracts/abi.yaml`（机器可读）→ `.tao/contracts/contract-dynlink.md`（GP 相关事实）；四者逐条一致。
- **`rb2`**：无条件保留（`non_allocatable` / reserved）；`hasFP` 为真时作 FP（prologue 保存旧值、epilogue 恢复），为假时不参与分配；**无 ABI 助记名**；Callee-saved = **Yes**（FP 语义下由 prologue/epilogue 保存恢复）。
- **`rb63`**：普通 callee-saved；与 `rb32`–`rb62` 连续；**不再有**「条件式 / FP / 最高编号特例」任何表述。
- **`rb32`–`rb63`**：连续可分配池（`allocatable.rb` 最后一段为 `[32,63]`；`callee_saved.rb = [32,63]`）。
- **FP 号**：所有 `getFrameRegister` / `FP = ...` 处为 `hasFP ? rb2 : rb1`；所有 `rbfp` 帧表记号替换为 `rb2`。
- **别名清零**：四份文件内 `rbfp`、`rbgp` 字符串 **0 处**（ADR 历史修订段除外，见下「不改」）。
- **不改**：`ADR-0018` 已由 architect 落地，本册**不重复改**；`spec` 只读册的册头版本保持 `0.9.3-rc`（未发布段内改），不新开版本段。

## 改动清单（逐文件，验收按此对账）

### 1. `spec/DADAO-21-ABI-应用程序二进制接口.md`
- `§1.2 RB寄存器` 表：`rb2` 行改为 `frame pointer`、ABI Mnemonic **空**、Callee-saved `Yes`、注「无条件保留；hasFP 为真时为 FP，否则不分配」；删除 `rb63` 独立行；`rb32 - rb63` 行恢复为连续 `callee saved regs`（无特例）。
- `§1.2` 表后两段（现 `:44`/`:46`，`rb63` 条件式 + 最高编号特例）**整段替换**为：`rb2` 为帧指针、无条件保留、无别名；`rb32`–`rb63` 为连续 callee-saved 池、可整段 `stm`/`ldm`。
- `§3.1 The Stack Frame` 帧表：`rbfp` → `rb2`（5 处：`+8n+8`/`+8`/`rb2`/`-8`/正文）；正文「采用 rbfp 作为栈帧的 frame pointer」→「采用 rb2 作为帧指针」。
- `§3.2` 变参游标处（现 `:285`）`incoming_sp（rbfp + 8）` → `（rb2 + 8）`。
- 文末 `### 0.9.3-rc（未发布）`：把「寄存器布局重排」条目改为最终口径（`rb2`=FP 无条件保留、无别名、`rb63` 普通 callee-saved、`rb32`–`rb63` 连续），并把「栈布局以 `rbfp` 为界」改为 `rb2`。**不得**写任务号/ADR/ISS 号（`check-spec-changelog` 断言 6）。

### 2. `.tao/contracts/contract-abi.md`
- `§1.3 RB 寄存器角色`：`rb2` 行改 `frame pointer`（无条件保留、无别名、Callee-saved `Yes`）；删除 `rb63` 行；`rb32–rb63` 合并为连续 callee-saved；表后注记改写（删「`rb63` 条件式 / 最高编号 / 排除 FP」整段，改为 `rb2` 无条件保留 + `rb32–rb63` 连续批量保存）。
- `§1.6`：`RB` 可分配范围改 `rb32–rb63`（连续）；不可分配表 `rb2` 原因改 `frame pointer（无条件保留）`；`rd1`/`rb2`/`rb3` 分类注记改写（`rb2` 为 callee-saved FP，不再按 spec 栏 `-` 归类）。
- `§2.1`：`FP = rb63` → `FP = rb2`。
- `§3 机器可读事实`：权威表注记 `rb1`/`rb63` → `rb1`/`rb2`；`callee_saved` 派生块 `rb: 32–62` → `32–63`；`reserved` 仍 `rd1–rd3`/`rb2–rb3`，但 `rb2` 原因改 FP。
- `§4.3`（现 `:185`）`rbfp + 8` → `rb2 + 8`。
- `§4.5`：callee-saved 改 `rb32–rb63`；删 `rb63` 条件式条；`rb2` 条改「FP/无条件保留」；CSR 字符串保持 `rd32–rd63 ∪ rb32–rb63 ∪ rf32–rf63`（`rb2` 不在 CSR，作 FP 时由 prologue 保存）。
- `§4.7`：帧表 5 处 `rbfp` → `rb2`；`FP = rb63` → `rb2`；`getFrameRegister = hasFP ? rb2 : rb1`；`rb2` 无条件保留、`rb63` 无条件 callee-saved。
- `§4.8`：FP 策略两条中的 `rbfp` → `rb2`；`FP = rb63` → `rb2`。
- 全文 `rbgp` 清零；`rb2` 的 GP 语义只允许出现在「已废止」历史叙述中，且须明示废止。

### 3. `contracts/abi.yaml`
- `stack`：`frame_pointer: rb2`；删 `frame_pointer_abi_name`；`frame_pointer_optional: false`（无条件保留）；注释改 `hasFP` 为真时作 FP、否则不分配。
- `registers.rb`：`rb2` 行 `role: frame_pointer`、无 `abi_name`、`callee_saved: true`；`rb32–rb63` 合并为一行；删除 `rb63` 条件式行。
- `allocatable.rb`：`[[4,7],[8,15],[16,31],[32,63]]`；注释同步。
- `non_allocatable`：`rb2` 原因 `frame_pointer`；删 `rb63` 条件注释。
- `callee_saved.rb: [32,63]`；注释删「32–62 / rb63 不在通用块」。
- `reserved_registers.rb: [2,3]` 不变；注释改 `rb2=FP（无条件保留）`、`rb3=TP`。
- `scalar_calling_convention.callee_saved`：`csr_rb: [32,63]`；`fp_in_csr: false`（FP=rb2 为保留寄存器，作 FP 时 prologue 保存）；`reserved_rb: [2,3]` 注释同步。
- `scalar_calling_convention.stack_frame`：`frame_pointer: rb2`；`get_frame_register: "hasFP ? rb2 : rb1"`；`frame_pointer_always_reserved: true`；`param_overflow_base: "rb2 + 8"`。

### 4. `.tao/contracts/contract-dynlink.md`
- `§2.1` RB 表：`rb2 | rbgp | GP | 保留不分配` → `rb2 | — | frame pointer（无条件保留） | 保留不分配`。
- 相关事实/裁定行（现 `:92`/`:93`/`:219`/`:259`/`:293`/`:308`）：把「spec 已把 `rb2`/`rbgp` 定义为 GP」改为「`rb2` 为帧指针（无条件保留）；**无 GP 寄存器**」；「不引入 GOT 固定基址寄存器（`rbgp` 不承载 GOT）」保留**决策**，但措辞改为「无 GP 寄存器」。
- `ADR-0021 D3`（不引入 GOT 固定基址寄存器）**不改**（决定本身仍成立）；只引用与 `rb2` 角色有关的事实更新。

### 5. `manifests/spec-readonly.lock.toml`
- 仅 `spec/DADAO-21-ABI-应用程序二进制接口.md` 的 `sha256` 重算（其余 20 册不动）。
- 顶部注释补一行变更注记（日期、册、改动要点、授权原话指针），不写任务号以外的编号规则保持既有风格。

## 不改（禁区）

- `ADR-0018` 正文：architect 已就地修订；本册只做一致性核对。
- `spec/SimRISC-*`、`DADAO-11/12/13/22/23`、`Toolchain-01`、`Machine-01`：本裁定不涉及（`rb63` 作为编号边界的使用属 ISA 事实，不改）。
- `.tao/knowledge/project_M3-codegen-choices.md`：历史设计记录，保持原样。
- `ADR-0021` / `ADR-0025` / `ADR-0031`：决定不变。

## 接口规范

- **输入**：本册「判据」+ 改动清单；`ADR-0018`（修订后）；`spec/DADAO-21` 现行文本；`contracts/abi.yaml`。
- **输出**：上述 5 个文件按清单改；证据 `.work/evidence/SPEC-150t/*`（含可达 FAIL）；日志 `.work/log/spec/SPEC-150t-*.log`。
- **约束**：临时目录 `/tmp/opencode/SPEC-150t/`；禁 `git checkout/restore/stash`；不跑 `install-host`/`build-*`（纯文档）；不 `push`。

## 验收标准

1. **别名清零**：`grep -RIn "rbgp\|rbfp"` 在 `spec/DADAO-21*`、`.tao/contracts/contract-abi.md`、`.tao/contracts/contract-dynlink.md`、`contracts/abi.yaml` 中 **0 行**。
2. **FP 号一致**：上述文件 `grep -n "hasFP.*rb"` 只出现 `hasFP ? rb2 : rb1`；`grep -n "FP = rb"` 只出现 `FP = rb2`。
3. **连续池**：`contracts/abi.yaml` 中 `allocatable.rb` 末段 `[32,63]`、`callee_saved.rb [32,63]`；`spec/DADAO-21` 与 `contract-abi` 无「`rb63` 条件式/最高编号/排除」表述（`grep -n "rb63"` 人工逐条核对，只允许普通成员语义）。
4. **变更记录**：`make check-spec-changelog` rc=0（册头 0.9.3-rc 与附录顶部段一致、逆序、无任务号/ADR/ISS 号、无表格）。
5. **只读锁**：`make check-spec-readonly` rc=0；`git diff -- manifests/spec-readonly.lock.toml` 只有 `DADAO-21` 一项 hash 变化，且与 `sha256sum` 一致。
6. **门控**：`make check`（L1）rc=0；另逐条 rc=0：`check-spec-readonly` / `check-spec-changelog` / `check-spec-drift` / `check-spec-refs` / `check-asm-prose` / `check-contracts-dir` / `check-contracts-pending` / `check-tasks` / `check-knowledge-refs` / `check-no-residue` / `check-milestones-fresh` / `check_issues`。
7. **可达 FAIL**：证据脚本对「`getFrameRegister` 写成 `rb63`」「`rb2` 行残留 `rbgp`」「`allocatable.rb` 残留 `[63,63]`」三类形态各注入一次 ⇒ FAIL；`cp` 备份 + `md5sum` 还原后回绿。
8. **与后端对齐**：`LLVM-110t` 完成后，其 `getReservedRegs`/`getFrameRegister` 的实现与本册契约逐条一致（交叉引用两册完成区，不在本册跑构建）。
9. 完成区贴真实命令输出 + 退出码（≤30 行）；长输出留 `.work/log/spec/`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
