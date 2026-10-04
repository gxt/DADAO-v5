# SPEC-056t: ADR-0012 就地修订（R1–R4）+ 关闭 ISS-042

**模块**：spec
**项目里程碑**：M2
**依赖**：用户逐条确认（2026-09-30）
**状态**：已验证

## 背景

两件事**本已由 `ADR-0012` 裁定但未落地/未覆盖**，按用户要求**并入 `ADR-0012` 就地修订**（体例同 D2.4：划改 + 注记来源），而非另立 ADR：

- `ADR-0012 D3.1` 早已写「**st 类指令允许 0 号寄存器**：st/stm 的 rdha/rbha/raha 不再触发 ILLI」——但实现层仍按旧语义（见 `SPEC-055t`/`QEMU-028t`/`TESTCASES-019t`）
- 新增需求：**删除 `rela.si`**（编码 `0x5A` → UNDI）

**用户确认（2026-09-30）**：R1–R4 均认可。

## 修改内容

### R1：强化 D3.1（划改 + 注记）

在 `ADR-0012 §D3` 的 D3.1 上就地修订（保留原句 + 划改 + 注记），明确：

- `st.*`/`stm.*` 的**源**为 `rd0`（读出 **0**）/ `rb0`（读出**当前指令的地址**，**非下一条**）→ **合法**，**不得** ILLI
- **仅**「**目的**为 0 号寄存器」才触发 ILLI
- `rb0` **可作访存基址**（`[rb0, imms12]` / `[rb0, rdHC]`）
- 注记来源：`SPEC-055t`、`QEMU-028t`、`TESTCASES-019t`（2026-09-30）

### R2：新增 D5「删除 `rela.si`」

- 从 QFC 表、`opcodes.yaml`、spec 文档移除 `rela.si`（`riii`，`rbha, imms18`）
- 编码 `0x5A`（`riii`）→ **UNDI**（保留编码，不再指派）
- 影响：指令总数 **254 → 253**；M1 身份 **177 → 176**
- 取代方案**不在本 ADR 预设**（用户裁定：遇具体问题再议）
- 关联任务：`SPEC-057t`

### R3：`ADR-0015` 退场

`.tao/knowledge/adr-0015-zero-register-as-source.md` 的文件头 `**状态**` 改为：
`Superseded by ADR-0012（2026-09-30）`
**不得**改写其 decision 正文（只改状态行 + 追加一行原因）。

### R4：连带同步（就地修订 + 注记）

| 位置 | 处置 |
|---|---|
| `.tao/knowledge/contract-isa.md §5.3`（PC 相对寻址 `rela.si`） | 删除该节（`rela.si` 已在 `SPEC-057t` 从 spec 移除）；若保留索引则注明「已删除」 |
| `.tao/knowledge/contract-elf.md §3` 的「PC 相对地址加载（`rela.si`）」行 | 划改：该场景**删除**；PC 相对寻址改为 `rb0` 基址路径（注记 `ADR-0012 D3.1/D5`） |
| `.tao/knowledge/adr-0003-object-abi.md` 中涉 `rela.si` 的场景 | 就地注记（划改 + 指向 `ADR-0012 D5`），不改写其 decision 正文 |
| `ADR-0012 §影响` | 补：254 → 253 条（删 `rela.si`）、M1 177 → 176 |
| `ADR-0012 §状态说明`（若无则新增） | 记录 2026-09-30 的 D3.1 修订与 D5 新增 |

### 关闭 `ISS-042`

`docs/issues.yaml` 的 `ISS-042`（`rela.si` fixup `>>2` vs `<<12`）：`status: open` → 关闭（`resolved_by: SPEC-056t`），理由「`rela.si` 已删除，问题消失」（`SPEC-057t` 落地删除后即成立）。

## 约束

- **不改**：`spec/SimRISC-0.5.3/`、`docs/m1-retrospective.md`、`docs/testcases-009t-audit.md`、已完成 `.tao/tasks/**`、`deferred.md` 历史条目
- **不改写**已 Accepted ADR 的 decision 正文（`ADR-0003` 用**划改+注记**；`ADR-0015` 只改状态行）
- 本任务**只改文档**，因此 `make check` 必须**保持绿**（不涉契约/实现）

## 验收标准

1. R1–R4 逐条落地；`ADR-0012` 的 D3.1 与 D5 内容与用户裁定**逐条一致**
2. `ADR-0015` 状态行已标 `Superseded by ADR-0012`；其 decision 正文**逐字未变**（diff 证据）
3. `ISS-042` 已关闭（`docs/issues.yaml` 证据）
4. `make check` EXIT=0（本任务不破坏任何门控——给证据）
5. 反例验证：注入回退（如把 D3.1 的「rb0 读出当前指令地址」删掉）→ 可检出；复原后无残留

## 完成区
**测试结果**：`make check` EXIT=0（6 文件改动均为文档，不涉契约/实现门控）

**修改文件**：
1. `.tao/knowledge/adr-0012-simrisc-0.5.4-update.md` — R1 D3.1 划改 + R2 D5 新增 + 影响更新 + 状态说明
2. `.tao/knowledge/adr-0015-zero-register-as-source.md` — R3 状态行 → Superseded（decision 正文未动）
3. `.tao/knowledge/contract-isa.md` — R4a §5.3 删除 + QFC 表 `rela.si-rb` → UNDI + 编码表 0x5A → UNDI + §7 引用修复
4. `.tao/knowledge/contract-elf.md` — R4b rela.si 行划改 + 脚注 rela.si 例外删除 + §2 引用修复
5. `.tao/knowledge/adr-0003-object-abi.md` — R4c D2 引用注记 + rela.si 行划改 + 修订注记
6. `docs/issues.yaml` — ISS-042 关闭（`resolved_by: SPEC-056t`）

**验收结果**：
- R1：ADR-0012 D3.1 已划改+注记，明确 rd0（读出0）/rb0（读出当前指令地址，非下一条）合法、仅目的为0号寄存器才ILLI、rb0可作访存基址
- R2：ADR-0012 D5 已新增（rela.si→UNDI，254→253，M1 177→176，关联SPEC-057t）
- R3：ADR-0015 状态行 → `Superseded by ADR-0012（2026-09-30）——D1–D4 全部并入 ADR-0012 D3.1/D5 就地修订`；decision 正文（D1–D4/Rationale/Consequences）逐字未变（diff 仅2行：状态行）
- R4：contract-isa.md §5.3 删除 + QFC/编码表 UNDI；contract-elf.md rela.si 行划改+脚注清理；adr-0003 引用注记
- ISS-042：`status: closed`，`resolved_by: "SPEC-056t"`，`notes: "rela.si 已删除（ADR-0012 D5，2026-09-30），编码 0x5A → UNDI，问题消失。"`
- `make check` EXIT=0（真实输出：`repository checks: PASS`、`check_issues: 63 open, 11 closed`）

**反例验证**：
- 注入：删除 D3.1 中 `rb0（读出**当前指令的地址**，**非下一条**）` → `git diff` 确认注入有效（文本缺失）
- 复原：`git checkout` + 重新编辑 → `git diff --stat` 确认6文件改动与预期一致、无残留
- `make check` EXIT=0（复原后）

**新发现/坑**：
- `adr-0003` 的修订注记区（`## 修订`）中也有 `rela.si` 例外描述，需一并注记（历史记录用划改+注记，不删除原文）
- `contract-elf.md §2` 的场景登记引用了 `contract-isa.md §5.2–§5.4`，§5.3 删除后引用范围断裂，需同步修复
- `contract-isa.md` 有两处 QFC 相关表（§2.7 主表 + 末尾编码详表），rela.si 出现在两处，需分别处理

**遗留问题**：无

**第 2 轮返工 — F1 修复**：
- **F1**：`contract-isa.md:415` §5 范围行残留「PC 相对寻址」（§5.3 已删但范围行未同步）→ 已删去「；PC 相对寻址」
- **同类全面排查**（凡提到「PC 相对寻址」/「§5.3」/`rela.si` 的范围行/索引行）：

| 位置 | 命中内容 | 处置 |
|------|---------|------|
| `contract-isa.md:415` §5 范围行 | 「；PC 相对寻址」 | ✅已删（本次 F1 修复） |
| `contract-isa.md:649` §7 范围行 | 「PC 相对寻址见 §5.3」 | ✅第1轮已修（finding#4） |
| `contract-isa.md:230` QFC 主表 | `~~rela.si-rb~~ UNDI` | ✅第1轮已修（划改+UNDI） |
| `contract-isa.md:1239` 编码详表 | `~~rela.si-rb~~ UNDI` | ✅第1轮已修（划改+UNDI） |
| `contract-elf.md:66` 场景登记引用 | 「§5.3 `rela.si` 已删除」 | ✅第1轮已修（注记） |
| `contract-elf.md:74` rela.si 行 | `~~PC 相对地址加载~~` | ✅第1轮已修（划改） |
| `adr-0003:94` D2 引用 | `~~rela 语义见 [contract-isa §5.3]~~` | ✅第1轮已修（注记） |
| `adr-0003:102` rela.si 行 | `~~PC 相对地址加载~~` | ✅第1轮已修（划改） |
| `adr-0003:144` 修订注记 | `~~rela.si 例外~~` | ✅第1轮已修（注记） |
| `adr-0012:52-69` D5/影响/状态说明 | rela.si/PC相对寻址 | ✅新增节（正常文档，非悬空） |

- `make check` EXIT=0（复原后）
- 反例注入：向 §5 范围行加回「；PC 相对寻址」→ grep 可检出 → 复原后无残留

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：6 个改动文件逐行审查

**发现**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | ADR-0012 D3.1 划改内容是否完整覆盖用户裁定的4个要点（rd0/rb0源合法、仅目的ILLI、rb0作基址、注记来源） | ✅已修 | 划改文本逐条覆盖 | grep 确认4个要点均在D3.1注记中 |
| 2 | ADR-0012 D5 的影响数字（254→253、177→176）是否与ADR-0012影响段一致 | ✅已修 | D5与影响段均写254→253、177→176 | diff 确认两处数字一致 |
| 3 | ADR-0015 decision正文是否被误改 | ✅已修 | diff仅2行：状态行；D1-D4/Rationale/Consequences逐字未变 | `git diff adr-0015` 确认 |
| 4 | contract-isa.md §5.3 删除后§7的引用是否断裂 | ✅已修 | §7引用从"§5.2；PC相对寻址见§5.3"改为"§5.2" | grep 确认无残留§5.3引用 |
| 5 | contract-elf.md §2脚注的rela.si例外是否清理 | ✅已修 | 脚注从含"rela.si例外"改为不含 | diff 确认 |
| 6 | ISS-042关闭是否符合issues.yaml格式（status/resolved_by/notes） | ✅已修 | 格式与ISS-056等已关闭issue一致 | grep 确认closed+resolved_by+notes |
| 7 | make check 是否真实PASS（非伪造） | ✅已修 | EXIT=0，log含"repository checks: PASS" | `/tmp/opencode/SPEC-056t-check-final.log` |
| 8 | 反例注入是否可复原 | ✅已修 | 注入→检测→复原→验证完整闭环 | git diff确认注入有效+复原后无残留 |

**判决**：所有 finding 已修，无遗留。标「待验收」。

#### 第 1 轮 reviewer 验收（reviewer 子代理，2026-09-30）

**核验方式**：独立重跑；不采信完成区转述。所有判断均以本机真实输出/退出码为准。

##### 重跑记录（真实输出）

1. `make check > /tmp/opencode/SPEC-056t/check.log 2>&1; rc=$?` → **`EXIT=0`**；log 末两行：
   `check_issues: 63 open, 11 closed (0 blocking M1-gate: 0)` / `repository checks: PASS`
2. `python3 tools/infra/check_issues.py` → `check_issues: 63 open, 11 closed (0 blocking M1-gate: 0)`，EXIT=0；独立 `grep -c` 亦得 open=**63**、closed=**11**（与工具一致，计数如实）
3. `git diff --numstat .tao/knowledge/adr-0015-…md` → `1  1`；剔除 `**状态**` 行后对新旧全文 `diff` → **逐字一致**（正文/D1–D4/Rationale/Consequences 未动）
4. `git diff --name-only` → 7 项：6 个产物 + 本任务书；**未见** `spec/SimRISC-0.5.3/`、`docs/m1-retrospective.md`、`docs/testcases-009t-audit.md`、`deferred.md`、其他已完成 `.tao/tasks/**`
5. ISS-042（`docs/issues.yaml:316–322`）→ `status: closed`、`resolved_by: "SPEC-056t"`、`notes:` 合理
6. **反例注入**（`/tmp/opencode/SPEC-056t/` 副本，自建 `check_056t.sh`，28 项内容断言）：
   - 基线 → `RESULT: PASS`，`EXIT=0`
   - 删 D3.1 中「`rb0`（读出**当前指令的地址**，**非下一条**）」→ 2 项 `[FAIL]`，`RESULT: FAIL`，**`EXIT=1`**（可检出）
   - 复原 → `RESULT: PASS`，mirror 与仓库文件 `diff` 一致；`git status --porcelain` 仍仅 7 项（**无残留**）

##### 约束核验（逐条）

| 裁定/约束 | 结论 |
|---|---|
| R1 D3.1 划改+注记（原句划改保留；`rd0`读出0 / `rb0`读出当前指令地址（非下一条）合法、仅**目的**为0才 ILLI、`rb0` 可作访存基址、来源注记） | ✅ 逐条一致 |
| R2 D5 新增（`rela.si`→UNDI、`0x5A` 保留、254→253、M1 177→176、不预设替代、关联 `SPEC-057t`） | ✅ 逐条一致 |
| R3 `ADR-0015` 仅状态行 → `Superseded by ADR-0012`，正文逐字未变 | ✅（numstat 1/1） |
| R4b `contract-elf §3` 划改+注记；R4c `adr-0003` 仅划改+注记（decision 正文未改写）；R4d `ADR-0012 §影响`·`§状态说明` | ✅ |
| R4a `contract-isa §5.3` 删除 | ⚠️ **未完全**（见 F1：§5 章首范围行仍写「PC 相对寻址」） |
| `ISS-042` 关闭（`status: closed` + `resolved_by: SPEC-056t`） | ✅ |
| 不改 `spec/SimRISC-0.5.3`/`m1-retrospective`/`009t-audit`/已完成任务书/`deferred.md` | ✅（git 证据） |
| 只改文档、`make check` 保持绿 | ✅ `EXIT=0` |
| 反例注入可检出 + 复原无残留 | ✅（自建检查器，非采信工程师） |

##### Findings

- **F1（阻断）** `contract-isa.md:415` §5 章首范围行**未随 §5.3 删除同步**：
  `> 范围：16 位立即数设置类指令（set.zw/set.ow/or.w/andn.w），支持 RD 和 RB 寄存器组；**PC 相对寻址**。块赋值见 §4。`
  该行与 `HEAD` 完全相同（`git show HEAD:… | sed -n 415p` 一致），而 `### §5.3 PC 相对寻址（riii 格式）` 已删（HEAD:445）→ 描述悬空/不准确。engineer 自审 finding#4 已修**同类**问题（§7 范围行「PC 相对寻址见 §5.3」，HEAD:658），却漏改 §5 自身范围行 → 「同类未修全」。
  **修法（一行）**：删去「；PC 相对寻址」，或改为「；PC 相对寻址已删除（见 `ADR-0012 D5`）」。预期：`grep -n "PC 相对" .tao/knowledge/contract-isa.md` 无「§5 范围」命中，`make check` 仍 EXIT=0。
- **F2（非阻断，观察）** `make check-spec-refs`（**独立 target，不在 `make check` 链路内**；基线 `HEAD` 已 `FAIL (57)`）由本任务升为 `FAIL (58)`——新增命中 `contract-isa.md:230`（QFC 主表 `~~rela.si-rb~~ UNDI` 行，Check2「无引用规范断言」启发式）。因该 target 本已红、且非门控，不判回归；仅记录。
- **F3（观察，不阻断）** `ADR-0012 D5` 写「**不预设替代方案**：PC 相对寻址改用 `rb0` 基址路径」——「不预设替代」与指名路径存在措辞张力；因 `rb0` 基址系 R1 已确立的**既有能力**（非新方案），判可接受。

##### 关于验收要点 #8（`contract-isa.md` QFC/编码表 UNDI 与 `contracts/opcodes.yaml` 暂不一致）

**判定：可接受的瞬时态，不阻断**。理由：
1. R4 范围含 `contract-isa §5.3` 删除。若只删 §5.3 而 QFC/编码表仍把 `rela.si` 列为**有效指令**，该文档将**自相矛盾**（有 QFC 行、无语义节）；标 **UNDI** 使 `contract-isa.md` 内部自洽，属**完成 R4 的必要收敛**，非无端扩张。
2. **无门控**比较 `contract-isa.md` 与 `contracts/opcodes.yaml`：`make check` EXIT=0；`validate_vectors` 与各生成器均读 `opcodes.yaml`（现仍 177/177），**行为未变**。
3. `SPEC-057t` 是**原子任务**，其目标即删 `opcodes.yaml`/spec/QEMU/LLVM 中的 `rela.si` 并收敛到 `validate_vectors 176/176`；窗口仅一个任务。
4. **交接注意（给架构师/`SPEC-057t`）**：`SPEC-057t` 验收 #4 要求 `grep rela.si` 仅命中「历史不变量」文件——届时 `contract-isa.md`/`contract-elf.md`/`adr-0003` 因保留划改原文会被命中，须在 #4 中列为历史不变量，否则误判为残留。

##### 判决

**Needs Revision** —— 唯一阻断项 **F1**（`contract-isa.md:415` §5 范围行残留「PC 相对寻址」，与 R4a 的 §5.3 删除不自洽，且工程师对同类 §7 引用已修、此处漏修）。其余 R1–R4（含 `ADR-0015` 正文逐字未变、`adr-0003` 仅注记）、`ISS-042` 关闭、范围约束、`make check EXIT=0`、反例注入可检出+复原无残留，均**通过**。修掉 F1（一行）后即可复核通过。`ADR-0015`/`adr-0003` 的划改+注记体例正确，`opcodes.yaml` 暂不一致判为可接受瞬时态。

#### 第 2 轮 engineer 返工

**返工项**：F1 — `contract-isa.md:415` §5 范围行残留「PC 相对寻址」

**修复**：
- `contract-isa.md:415`：从 `> 范围：16 位立即数设置类指令（set.zw/set.ow/or.w/andn.w），支持 RD 和 RB 寄存器组；PC 相对寻址。块赋值见 §4。` 删去「；PC 相对寻址」

**同类全面排查**（grep `PC 相对|§5\.3|rela\.si` 跨 4 个改动文件）：

| 文件 | 行 | 命中 | 类型 | 处置 |
|------|-----|------|------|------|
| `contract-isa.md` | 230 | `~~rela.si-rb~~ UNDI` | QFC表划改 | ✅第1轮已修 |
| `contract-isa.md` | 1239 | `~~rela.si-rb~~ UNDI` | 编码表划改 | ✅第1轮已修 |
| `contract-elf.md` | 66 | 「§5.3 `rela.si` 已删除」 | 注记（说明已删） | ✅第1轮已修 |
| `contract-elf.md` | 71-73 | PC 相对短程分支/双寄存器分支/call/jump | 合法分支指令（非 rela.si） | 无需改 |
| `contract-elf.md` | 74 | `~~PC 相对地址加载~~` | 划改 | ✅第1轮已修 |
| `adr-0003` | 94 | `~~rela 语义见 [contract-isa §5.3]~~` | 划改+注记 | ✅第1轮已修 |
| `adr-0003` | 99-101 | PC 相对短程分支/双寄存器分支/call/jump | 合法分支指令（非 rela.si） | 无需改 |
| `adr-0003` | 102 | `~~PC 相对地址加载~~` | 划改 | ✅第1轮已修 |
| `adr-0003` | 144 | `~~rela.si 例外~~` | 划改+注记 | ✅第1轮已修 |
| `adr-0012` | 52-69 | rela.si/PC相对寻址 | D5新增节/影响/状态说明 | 正常文档 |

**结论**：除 F1 外无其他悬空引用。所有剩余命中均为：① 划改+注记（说明已删除）、② 合法分支指令（非 rela.si）、③ 新增 D5 节（正常文档）。

**自审**：

| # | finding | 处置 | 复验证据 |
|---|---------|------|---------|
| 1 | §5 范围行是否已删去「PC 相对寻址」 | ✅已修 | `grep -n "PC 相对" contract-isa.md` 无§5范围行命中 |
| 2 | 同类排查是否遗漏 | ✅已修 | 上表10项逐一确认，无新增悬空 |
| 3 | make check 是否仍绿 | ✅已修 | EXIT=0 |
| 4 | 反例注入可检出 | ✅已修 | 注入→grep命中→复原→无残留 |

**判决**：F1 已修，同类全面排查无遗漏，标「待验收」。

#### 第 2 轮 reviewer 复核（reviewer 子代理，2026-09-30）

**复核方式**：独立重跑；不采信返工说明。

##### 重跑记录（真实输出）

1. **F1 现状**：`sed -n '413,416p' contract-isa.md` →
   `> 范围：16 位立即数设置类指令（set.zw/set.ow/or.w/andn.w），支持 RD 和 RB 寄存器组。块赋值见 §4。`
   （「；PC 相对寻址」已删）✅
2. **全文悬空引用排查**（我独立执行，非采信工程师表）：
   - `grep -n "PC 相对\|PC相对" .tao/knowledge/contract-isa.md` → **无命中（exit 1）**
   - `grep -n "§5\.3\|5\.3" .tao/knowledge/contract-isa.md` → **无命中（exit 1）**
   - 6 个改动文件中 `§5.3` 仅剩 2 处，**均为已注记**：`adr-0003:94`（`~~rela 语义见 [contract-isa §5.3]~~` + 注记）、`contract-elf:66`（`（§5.3 rela.si 已删除，见 ADR-0012 D5）`）；`rela.si` 仅剩划改历史行/D5 正文/注记
   - **指向已删内容的悬空「范围行/索引行」= 0** ✅
3. `make check > log 2>&1; rc=$?` → **`EXIT=0`**；末行 `check_issues: 63 open, 11 closed (0 blocking M1-gate: 0)` / `repository checks: PASS`
4. **R1–R4 仍逐条成立**：自建检查器（28 项，含新增 F1 两项 `chknot`）→ `RESULT: PASS`
5. `ADR-0015`：`git diff --numstat` = `1 1`；剔除状态行后全文 `diff` → **A15-BODY-IDENTICAL**（正文逐字未变）
6. `ISS-042`（`issues.yaml:316–322`）→ `status: closed` / `resolved_by: "SPEC-056t"` ✅
7. **范围**：`git diff --name-only` 仍 7 项；`grep` 禁改路径 → `no forbidden` ✅
8. **反例注入**（`/tmp/opencode/SPEC-056t/mirror` 副本 + 自建检查器）：
   - 基线 → `RESULT: PASS`，`EXIT=0`
   - **F1 回归注入**（把「；PC 相对寻址」加回 §5 范围行）→ `[FAIL] F1: 无 PC 相对寻址悬空引用`，`RESULT: FAIL`，**`EXIT=1`**（可检出）
   - **R1 回归注入**（删「rb0 读出当前指令的地址，非下一条」）→ 2 项 `[FAIL]`，**`EXIT=1`**（可检出）
   - 复原 → `RESULT: PASS`，mirror 两文件与仓库 `diff` 逐字节一致；`git status --porcelain` 仍仅 7 项（**无残留**）

##### 约束核验（逐条）

| 裁定/约束 | 结论 |
|---|---|
| F1：§5 范围行无「PC 相对寻址」；全文指向已删内容（PC 相对寻址/§5.3/rela.si）的悬空范围/索引引用 = 0 | ✅ 0 处 |
| R1（D3.1 划改+注记，4 要点） / R2（D5，254→253、177→176） / R4b/4c/4d | ✅ 逐条一致（未引入新问题） |
| R3：`ADR-0015` 仍仅改状态行，正文逐字未变 | ✅ |
| `ISS-042` 仍 `closed` + `resolved_by: SPEC-056t` | ✅ |
| 范围：禁改文件（`SimRISC-0.5.3`/`m1-retrospective`/`009t-audit`/已完成任务书/`deferred.md`）未动 | ✅ |
| `make check EXIT=0` | ✅ |
| 反例注入可检出 + 复原无残留 | ✅（自建检查器，非采信） |

##### 观察（非阻断，沿用第 1 轮）

- F2：`make check-spec-refs`（**独立 target，不在 `make check` 链路内**；基线已红）命中数不因本次返工变化——仍为 `contract-isa:230` QFC 划改行的启发式命中，非门控、非回归，仅记录。
- 交接注意（仍成立）：`SPEC-057t` 验收 #4 的 `grep rela.si` 将命中 `contract-isa.md`/`contract-elf.md`/`adr-0003` 的划改历史原文，须在 #4 中列为历史不变量。

##### 判决

**Accepted** —— F1 已修复且**全文悬空引用为 0**；R1–R4 逐条仍成立、`ADR-0015` 正文逐字未变、`ISS-042` closed、范围守住、`make check EXIT=0`、两组反例注入均**可检出**且复原**无残留**（mirror 与仓库逐字节一致）。第 1 轮 F1 阻断项解除，无新增问题。复审通过，交主会话/架构师终审。
