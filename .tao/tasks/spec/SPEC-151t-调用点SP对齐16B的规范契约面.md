# SPEC-151t: 调用点 `SP` 对齐 8→16 B 的规范 / 契约面（`ADR-0018 C9 D3`）

**模块**：spec
**项目里程碑**：M8
**依赖**：`ADR-0018`（**`C9 D3` 已由 architect 于 2026-10-19 就地修订**，用户原话见下；本册只核对、不重复改 ADR）、`LLVM-112t`（实现面，**同批**；两册落地前契约与后端不得长期不一致）、`ADR-0031 D7`（16 B 栈值对齐的既有依据；SP 16 B ⇒ 其条件不再依赖「相对基址取整」）、`SPEC-150t`（同改 `spec/DADAO-21` 与只读锁；**串行**，后落地者按现场重算 `sha256`）
**状态**：待验收

## 用户授权（原话逐字；渠道 = 经主会话问答，2026-10-19）

> 「**同意，调用点SP对齐改成16B**」

- 授权面：改 `spec/DADAO-21`（只读册；`docs/Process-06 §2` 要求用户事先明确允许 —— **本授权即允许**）+ `.tao/contracts/contract-abi.md` + `contracts/abi.yaml` + 只读锁重算。
- 裁定口径：**`call` 执行时 `sp` 必须 16 字节对齐**（由 8 B 改为 16 B）。栈参数仍按 **8 B 槽**排列；16 B 值（binary128 / 16 B 整数类聚合）仍按 **16 B 对齐**、必要时跳过一个 8 B 槽。
- **不改**：`DataLayout` 串（`…-S128`）与 `i128:128`；`StackFrame` 的 FP 策略（归 `SPEC-150t`）；`spec/DADAO-21 :246`「栈参数…8 字节对齐」的 **8 B 槽**表述。

## 问题根源

1. **规范与裁定冲突**：`spec/DADAO-21 §3.2.4`（现 `:257`）写「call 指令执行时 sp 必须 **8 字节对齐**。变参保存区同样 8 字节对齐」；用户 2026-10-19 裁定改为 **16 B**。
2. **契约三处仍是 8 B**：`.tao/contracts/contract-abi.md` §2.2（现 `:136`）、§4.8 不变量（现 `:251`）、§4.9（现 `:261`）均只承诺 8 B；§4.9（现 `:263`）还明文「本合约**不做 8/16 冲突裁定**，仅登记二事实」——该口径已被用户裁定取代。
3. **机器可读数据仍是 8**：`contracts/abi.yaml` 的 `stack_alignment: 8`、`scalar_calling_convention.stack_frame.call_sp_alignment: 8`，以及 `stack_natural_alignment_bits: 128` 的注释「16B ⊃ 8B，不做 8/16 裁定」。
4. **后果（`D7` 的前置）**：`ADR-0031 D7` 要求栈上 16 B 值 16 B 对齐。基址 `sp` 只有 8 B 对齐时，**绝对地址 `% 16 == 0` 不成立**（`LLVM-111t` 探针只能用 16 B 对齐局部变量钉住基址，已在完成区披露）。SP 改为 16 B 后，**`D7` 的无条件 `%16==0` 成立**：`reassignDADAOArgLocs` 的 `alignTo(StackOff, 16)` + `Align(16)` 帧 ⇒ 任一 16 B 栈值的绝对地址必为 16 的倍数，不再依赖探针技巧。
5. **规范内部一致性**：`spec/DADAO-21 §2.2`（Aggregates）已要求「16 字节值…按 16 字节对齐；栈上的 16 字节值同样按 16 字节对齐」，但 §3.2.4 的调用点 SP 只有 8 B ⇒ 两处张力；本册把 `call` 时 SP 提到 16 B 后消除。

## 判据（写死）

- **单一真源链条**：`spec/DADAO-21`（规范正文）→ `.tao/contracts/contract-abi.md`（人读契约）→ `contracts/abi.yaml`（机器数据）→ `manifests/spec-readonly.lock.toml`（只读锁）。四者逐条一致。
- **数值口径**：`call` 时 `sp % 16 == 0`；栈参数槽仍 8 B；16 B 值占两槽、16 B 对齐（必要时跳过一个 8 B 槽）；变参保存区每槽 8 B，**不要求** 16 B（只要求可被 `stm.o`/`ldm.o` 8 B 对齐访问）。
- **无条件性**：契约须写明「在 `call` 时 SP 16 B 对齐的前提下，栈上 16 B 值的绝对地址无条件 16 B 对齐」；不得再写「不做 8/16 裁定」。
- **版本**：`spec/DADAO-21` 册头保持 `0.9.3-rc`（未发布段内改，不新开版本段）；文末 `### 0.9.3-rc（未发布）` **追加一条**，**不得**出现任务号 / `ADR-` / `ISS-` 号（`check-spec-changelog` 断言 6）。`contract-abi.md` 版本保持 `0.9.2`（= `README.md` 已发布版本；`check-spec-drift` 以已发布列比对），不因本册改动而升版。
- **ADR 已落地**：`ADR-0018` 的 `C9 D3`、`## 修订`（rev. 2026-10-19 第二条）、`## 状态说明` 已由 architect 写入；本册**核对**其与 spec/契约逐条一致，**不重复改**。

## 改动清单（逐文件，验收按此对账）

### 1. `spec/DADAO-21-ABI-应用程序二进制接口.md`（只读册，已授权）

- `§3.2.4 栈溢出规则`：把「call 指令执行时 sp 必须 **8 字节对齐**。变参保存区同样 8 字节对齐。」改为：
  - 「call 指令执行时 sp 必须 **16 字节对齐**。变参保存区按 **8 字节对齐**（每个保存槽 8 字节；不要求 16 字节）。」
- 同节 16 B 值段（现 `:259`）：在「16 字节对齐（必要时跳过一个 8 字节槽位）」后补一句：「在 `call` 时 `sp` 16 字节对齐的前提下，栈上 16 字节值的**绝对地址无条件 16 字节对齐**。」
- `§2.2 Aggregates`（16 B 值按 16 B 对齐）：**已与裁定一致，不改**；执行时核对、在完成区记录「核验不改」。
- `:246`「栈参数按…8 字节对齐」：**不改**（指 8 B 槽；16 B 值是例外，由下一段规定）。
- 文末 `### 0.9.3-rc（未发布）`：追加一条，例如「调用点 SP 对齐由 8 字节改为 16 字节：`call` 执行时 `sp` 必须 16 字节对齐；栈参数仍按 8 字节槽排列，16 字节值按 16 字节对齐（SP 16 字节对齐下其绝对地址无条件对齐）。」——措辞可调，但**不得**含任务号/ADR/ISS 号，且须与正文同义。
- 册头 `> **版本：0.9.3-rc**` **不变**。

### 2. `.tao/contracts/contract-abi.md`

- 顶部「范围」行（现 `:5`）：「`call` 时 SP 8B 对齐」→「`call` 时 SP **16B** 对齐」。
- `§2.1 栈指针与栈方向`：增补一条（与 §2.2 单一真源，不重复细则）：「`SP`（`rbsp`）在 `call` 执行时 **16 字节对齐**；细则见 §2.2。」[DADAO-21 §传参 §栈溢出规则]
- `§2.2 call 时 SP 对齐`（现 `:136`）：
  - 「必须 **8 字节对齐**」→「必须 **16 字节对齐**」。
  - 补一条：「栈参数仍按 **8 字节槽**排列（§4.3）；16 字节值按 **16 字节对齐**（§4.3 末条）。SP 16 B 对齐 ⇒ 栈上 16 B 值的**绝对地址无条件 `% 16 == 0`**，`ADR-0031 D7` 的 16 B 栈对齐不依赖相对基址取整。」[DADAO-21 §传参 §栈溢出规则][ADR-0018（C9）]
- `§3 机器可读事实`：在 `contracts/abi.yaml` 条目注记中补「`stack_alignment` / `call_sp_alignment` = **16**（本册同步）；`stack_natural_alignment_bits: 128` 不变」；版本仍 `0.9.2`。
- `§4.8 prologue / epilogue` 不变量（现 `:251`）：「`call` 执行时 `sp`…必须 **8 字节对齐**」→ **16 字节对齐**。
- `§4.9 栈对齐与 DataLayout`（现 `:261`/`:263`）：
  - `:261` 「8 字节对齐」→「16 字节对齐」。
  - `:263` 「两者**不矛盾**…**不做 8/16 冲突裁定**，仅登记二事实」→ 改为「`S128`（16B）与 `call` 时 SP 16B 对齐**一致**；16 B 栈值的绝对对齐**无条件成立**」。`DataLayout` 串与 `S128` 解释不变。
- 其余 `SPEC-150t` 负责的 FP / `rb2` / `rb63` 行**不碰**（若两册改到同一行，先落者为准，后落者 rebase 后复核，完成区披露）。

### 3. `contracts/abi.yaml`

- 头部注释（现 `:38`）：「与 call 时 SP 8B 对齐不矛盾（16B ⊃ 8B），不做 8/16 裁定」→「与 call 时 SP **16B** 对齐一致；16 B 栈值绝对对齐无条件成立」。
- `stack.stack_alignment: 8` → **`16`**，注释改「call 执行时 SP 必须 16 字节对齐（用户 2026-10-19 裁定）」。
- `scalar_calling_convention.stack_frame.call_sp_alignment: 8` → **`16`**。
- `stack_natural_alignment_bits: 128` **不变**。
- 版本 `"0.9.2"` **不变**；其余字段零改动。

### 4. `manifests/spec-readonly.lock.toml`

- 仅重算 `spec/DADAO-21-ABI-应用程序二进制接口.md` 的 `sha256`（**现场** `sha256sum`；不写死）。
- 顶部注释补一行变更注记：日期、册、改动要点（call 时 SP 8→16 B）、授权原话指针（本册 §用户授权）。
- 其余 20 册哈希**不动**；若 `SPEC-150t` 已先落地同一册，按其现场值与注记依序追加，**不得**回退他人改动。

## 不改（禁区）

- 代码 / 补丁 / 测试：**零改动**（实现归 `LLVM-112t`）。
- `ADR-0018` 正文：architect 已就地修订；本册只核对。
- `ADR-0031`：`D7` 决定不变（16 B 栈值对齐）；本册只是让它的**前置**（SP 16 B）成立。
- `spec/DADAO-21 §2.2` 聚合 16 B 对齐条款、`:246` 8 B 栈槽表述：不改。
- `README.md` 版本表、`contract-abi.md` 版本号：不改（仍 `0.9.2` = 已发布版本）。

## 执行环境

**执行环境**：本地

## 接口规范

- **输入**：本册判据 + 用户裁定原话 + `ADR-0018 C9 D3`（architect 已落）+ `ADR-0031 D7` + 现 `spec/DADAO-21` / `contract-abi.md` / `abi.yaml` / 只读锁。
- **输出**：上述 4 个文件的改动；完成区逐条真实命令输出；无代码改动。
- **约束**：临时目录仅 `/tmp/opencode/SPEC-151t/`；不提交 git（提交权归 architect）；不改 `**状态**`；失败保留现场并继续推进（自行处置 / 有据重试并记录次数；只在需用户语义裁定时留问）。

## 验收标准

1. `spec/DADAO-21 §3.2.4` `call` 时 `sp` = **16 字节**；变参保存区措辞自洽（8 B 槽、不要求 16 B）；`:246` 8 B 栈槽与 §2.2 16 B 值对齐未误改；文末 `0.9.3-rc` 追加条目且**无任务号/ADR/ISS 号**；册头仍 `0.9.3-rc`。
2. `.tao/contracts/contract-abi.md` §2.1/§2.2/§3/§4.8/§4.9 全部为 **16 B**，且写明「SP 16 B ⇒ 栈上 16 B 值绝对地址无条件 `%16==0`、`D7` 不依赖相对取整」；全文 `call` 时 SP 的 8 B 断言 **0 处**（`grep` 证据）。
3. `contracts/abi.yaml` `stack_alignment` 与 `call_sp_alignment` 均为 **16**，注释同步，其余字段零 diff；版本仍 `0.9.2`。
4. `manifests/spec-readonly.lock.toml` 的 `DADAO-21` `sha256` 与 `sha256sum spec/DADAO-21-…md` 逐字一致；其余 20 册未变。
5. `ADR-0018` 核对通过：`C9 D3` / `## 修订`（2026-10-19 第二条）/ `## 状态说明` 三处口径与 spec/契约一致（只读核对，不改）。
6. 门控全绿（真实 rc）：`make check`（L1）、`make check-spec-readonly`、`make check-spec-changelog`、`make check-spec-drift`、`make check-tasks`、`make check-knowledge-refs`、`make check-no-residue`、`make check-milestones-fresh`、`python3 tools/infra/check_issues.py`。
7. 完成区贴真实命令/退出码/关键输出（不转述）；用户授权原话原样写入。

## 完成区
**测试结果**：证据脚本 `.work/evidence/SPEC-151t/run.sh` 正向 9/9 PASS（rc=0）；`--inject` 2/2 反例均先 FAIL、`cp`+md5 还原后回绿（rc=0）。门控真实 rc：`make check`=0、`check-spec-readonly`=0、`check-spec-changelog`=0、`check-spec-drift`=0、`check-spec-refs`=0、`check-contracts-pending`=0、`check-contract-relocs`=0、`check-tasks`=0、`check-knowledge-refs`=0、`check-no-residue`=0、`check_issues.py`=0。
**修改文件**：`spec/DADAO-21-ABI-应用程序二进制接口.md`、`.tao/contracts/contract-abi.md`、`contracts/abi.yaml`、`manifests/spec-readonly.lock.toml`、`.work/evidence/SPEC-151t/run.sh`（新增，`.work/` 不入库）。
**验收结果**：
- spec §3.2.4：`call 指令执行时 sp 必须 16 字节对齐（栈区起点 16 字节对齐；上段栈参数槽宽仍为 8 字节）。变参保存区每个保存槽 8 字节、按 8 字节槽宽排列（不要求 16 字节对齐）。`；16 B 值段补「在 `call` 时 `sp` 16 字节对齐的前提下…绝对地址无条件 16 字节对齐」；文末 `0.9.3-rc` 追加 1 条（无任务号/ADR/ISS 号）；册头仍 `0.9.3-rc`。
- spec `:115`（§2.2 聚合「至少 8 字节对齐」）**不动**：属**数据/类型**对齐（内存中聚合的自然对齐），与调用点栈对齐无关；`ADR-0018 C9 D3` 明示 `DataLayout`/`S128` 不变；下一行 `:117` 已单列 16 B 值按 16 B 对齐。`:247` 栈参数 8 字节为**槽宽**，16 B 值例外由 `:260` 规定，故保留原句，澄清并入 `:258`。
- 残留分类（`grep` 现场）：`sp.*8 字节对齐|SP 8B 对齐` 于 `spec/`+`contract-abi.md` = **0**；`spec` 中剩余「8 字节对齐」2 处 = `:115` 数据对齐、`:247` 栈槽宽（均属保留类）；`contract-abi` 剩余 1 处 = `:192` 栈槽宽。
- 契约：`:7` 范围、§2.1 新增条、§2.2、§3 机读事实注记、§4.8、§4.9 均为 16 B；写明 8 B 槽宽不变 + 无条件 `%16==0` + `D7` 不依赖相对取整；无「不做 8/16 裁定」。
- `abi.yaml`：`stack_alignment: 16`、`call_sp_alignment: 16`、`stack_natural_alignment_bits: 128` 不变、`version: "0.9.2"` 不变。
- 只读锁：`sha256sum` 现场值 = `7f2bb07391617fcf6cd51d3ec7ec45f6b5d4f1c8086b6217adc43d1a5f95dd11`，锁内一致；其余 20 册未动。
- `ADR-0018 C9 D3` 核对：`call` 时 `sp` **16 B 对齐**、栈参数 **8 B 槽**、16 B 值两槽/16 B 对齐、`S128` 不变——与 spec/契约逐条同义（只读核对，未改 ADR）。
- 用户授权原话（逐字）：「**同意，调用点SP对齐改成16B**」。
**新发现/坑**：`.tao/contracts/contract-dynlink.md:308` 仍有「入口栈向量；SP/8B 对齐」表述——指**进程入口**栈向量、非 `call` 调用点，且不在本册改动范围；建议后续由 dynlink 契约归属任务核定（本册未改）。
**遗留问题**：无（上述 dynlink 观察项为范围外登记）。


## 审阅记录

#### 第 1 轮 engineer 自审
**判决**：通过（无未修 finding）。
**审查范围**：4 个改动文件 + 证据脚本；逐条对照本册「改动清单 / 不改（禁区）/ 验收标准」。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 初始证据脚本 `c_contract_16` 以 `call.*sp.*16 字节对齐` 计数，§2.1 行词序（SP 在 call 前）漏计 1 → 期望 4 实际 3 | ✅已修 | 改为 4 个规范落点（§2.1/§2.2/§4.8/§4.9）逐条 `grep -q` + 现场计数 | `run.sh` 9/9 PASS；`--inject` 反例 1 使该断言由 4→3 并 FAIL |
| F2 spec `:258` 初稿「变参保存区按 8 字节对齐」会被验收 grep `sp.*8 字节对齐` 误命中（非 call 断言） | ✅已修 | 改「变参保存区每个保存槽 8 字节、按 8 字节槽宽排列（不要求 16 字节对齐）」 | `grep -rnE 'sp.*8 字节对齐|SP 8B 对齐' spec/ .tao/contracts/contract-abi.md` = 0 |
| F3 判 `:115` 聚合 8 B 是否需改成 16 B | ❌不修（有理据） | 未改 | 属数据/类型自然对齐；`C9 D3` 明示 `DataLayout`/`S128` 不变；`:117` 已单列 16 B 值 16 B 对齐 |
| F4 `:247`「栈参数…8 字节对齐」是否违背 16 B 裁定 | ❌不修（按册「不改」项） | 未改原句，澄清并入 `:258`「槽宽仍为 8 字节、栈区起点 16 字节对齐」 | 契约 §2.2/§4.3 同步「8 B 槽宽不变」；证据断言 `c_untouched_sections` PASS |
| F5 证据脚本注入还原纪律 | ✅已做 | `cp` 备份 + md5 对账 + `trap` 兜底；未用 `git checkout/restore/stash` | `--inject` 两轮：FAIL→md5 相符→回绿；`git status -uall` 仅 4 个内容文件 + 本册 |
**自审补充**：无越界文件（`git status -uall` = spec/契约/yaml/lock 4 个内容文件 + 本册）；未改实现、未改 ADR、未改 `**状态**`、未 `add/commit/push`。


#### 第 1 轮 reviewer 验收
（待执行）
