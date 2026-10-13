# SPEC-057t: 全量删除 `rela.si`（跨 spec/qemu/llvm/testcases 原子变更）

**模块**：spec（**跨模块**：`spec/`+`contracts/`+`tools/`+`components/qemu`+`components/llvm-project`+`tests/`）
**项目里程碑**：M2
**依赖**：`SPEC-056t`（`ADR-0012 D5` Accepted）
**状态**：已验证

## 为什么是一个原子任务

`opcodes.yaml` 是**单一真源**：`check_qemu_trans`、`validate_vectors`、`check_lit_bytes`、`check_interface_alignment` 都以它为准。**删 `rela.si` 必然同时改动契约与全部消费者**，任何拆分会留下「红门控」中间态（架构师预检结论，用户裁定「甲」）。故本任务**必须一次性把契约与所有消费者同步**，结束 `make check` **绿**。

## 目标（`ADR-0012 D5`）

从 SimRISC 0.5.4 **删除 `rela.si`**（`riii`，`rbha, imms18`，op **`0x5A`**）；`0x5A` → **UNDI**。指令总数 **254 → 253**，M1 身份 **177 → 176**。**不预设替代方案**（遇具体问题再问用户）。

## 修改内容（逐项）

### A. 契约与生成源

1. `tools/spec/generate_opcodes.py`：移除 `rela.si_riii_rb` 条目；`0x5A` 单元 → 空/保留（解码 **UNDI**）
2. 重生成 `contracts/opcodes.yaml`
3. 重生成 `docs/assembly-list.md` + 12 个 `spec/SimRISC-*.md` 内嵌速查表（`tools/llvm/gen_asm_list.py`）
4. `tools/llvm/gen_asm_list.py`：若 `classify()`/`SECTION_ORDER` 有针对 `rela` 的规则，同步清理

### B. spec/

5. `spec/SimRISC-12-待定.md`：删除 §PC相对寻址（`rela.si`）整节
6. `spec/SimRISC-00-指令系统设计.md`：QFC 表 / 格式表（`0x5A` 行）与
7. `spec/SimRISC-06-控制流.md`：如引用 `rela.si` 则清理
8. `docs/spec/assembly-language.md`：§特例中的 `rela.si` 行

### C. QEMU

9. `components/qemu/patches/target/dadao/insn.decode`：删 `rela_si_riii_rb`
10. `.../insn_trans/trans_ctrl.c.inc`：删 `trans_rela_si_riii_rb`
11. 重建（`make prepare` + `make build-qemu`）→ `check_qemu_trans` **253/253（M1 176/176）**

### D. LLVM MC

12. `components/llvm-project/patches/.../DADAOInstrFormats.td`、`DADAOInstrInfo.td`、`MCTargetDesc/DADAOAsmBackend.cpp`、`MCTargetDesc/DADAOFixupKinds.h`、`MCTargetDesc/DADAOMCInstPrinter.cpp`：移除 `rela.si`
13. 重建 `make build-mc`；`llvm-lit tests/lit/MC/Dadao/ tests/lit/E2E/` 计数更新且全绿

### E. 向量与工具

14. `tests/vectors/isa/reg-arith.yaml`：删 `rela.si` 用例（encoding/legality/semantic/boundary）
15. `tests/vectors/inventory.md`：**177 → 176**
15b. **`tools/integ/check_interface_alignment.py`**：硬编码常量同步 —— `EXPECTED_TOTAL 254→253`、`EXPECTED_M1 177→176`、`EXPECTED_TRANS 254→253`（及注释）；改后该脚本须恢复 **80/80 EXIT=0**
16. `tests/vectors/isa/reserved.yaml`（或等价）：补 `0x5A` → **UNDI** 的保留编码用例
17. `tools/testcases/generate_isa_vectors.py`、`tools/testcases/009t-audit.py`、`tools/qemu/check_005t_coverage.py`、`tools/qemu/min_rom_probe_008t.py`、`min_rom_probe_009t.py`：同步
18. `docs/impact-matrix.md`：同步

### F. 不得改

`spec/SimRISC-0.5.3/`、`docs/m1-retrospective.md`、`docs/testcases-009t-audit.md`、已完成 `.tao/tasks/**`、`deferred.md` 历史条目。

## 约束

- 补丁集组织以 `docs/spec/component-patching.md` 为准（树形 + 一文件一补丁 + `git apply`）
- **期望值独立推导**；不得从 LLVM/QEMU 输出反填
- 反例注入须**可复原且须重建**
- 命令缺失/构建失败 → 停下报告，禁止自行安装

## 验收标准

1. `rela.si` 在 spec/`opcodes.yaml`/`assembly-list`/12 内嵌表/QEMU/LLVM MC/向量/工具中**全部消失**；`0x5A` → **UNDI**（保留编码用例存在）
2. 计数：指令 **253**、M1 身份 **176**、`check_qemu_trans` **253/253（M1 176/176）**、`validate_vectors` **176/176**
3. `make check` **EXIT=0**；`llvm-lit tests/lit/MC/Dadao/ tests/lit/E2E/` 全绿（计数如实更新）
4. 全量 grep：`grep -rn "rela\.si\|rela_si"` 仅命中**历史不变量**文件（逐个列明）
5. 反例注入：把 `rela.si` 加回任一处 → 相应门控**报错**；复原+重建后全绿
6. 无未终态的半成品（本任务结束即 `make check` 绿）

## 完成区
**测试结果**：make check EXIT=0；validate_vectors 176/176；check_qemu_trans 253/253 (M1 176/176)；llvm-lit 25/25 PASS；check_interface_alignment 80/80 EXIT=0
**修改文件**：
- A. 契约：`tools/spec/generate_opcodes.py`（删 `rela.si` 条目 + `S12_RELA` 常量）→ 重生成 `contracts/opcodes.yaml`（253 条, M1 176）
- A. 生成：`tools/llvm/gen_asm_list.py`（移除 `rela.si` 分类 + 更新计数 254→253/177→176）→ 重生成 `docs/assembly-list.md` + 12 个 spec 嵌入表
- B. spec：`spec/SimRISC-12-待定.md`（删 §PC相对寻址整节, header 12→11）；`spec/SimRISC-00-指令系统设计.md`（QFC 表 0x5A 清空 + 算术运算表移除 rela.si）；`spec/SimRISC-06-控制流.md`（删 rela.si 注）；`docs/spec/assembly-language.md`（删 rela.si 特例 + 单位说明）
- C. QEMU：`components/qemu/patches/target/dadao/insn.decode.patch`（删 `rela_si_riii_rb`）；`.../insn_trans/trans_ctrl.c.inc.patch`（删 `trans_rela_si_riii_rb` 函数, 修 @@ 行计数）
- D. LLVM MC：`DADAOInstrInfo.td.patch`（删 `rela_si_rb` def, 修 @@ 行计数）；`DADAOInstrFormats.td.patch`（注释）；`DADAOAsmBackend.cpp.patch`（注释）；`DADAOFixupKinds.h.patch`（注释 + 修 @@ 行计数）；`DADAOMCInstPrinter.cpp.patch`（注释）
- E. 向量：`tests/vectors/isa/reg-arith.yaml`（删 3 条 rela.si 用例）；`tests/vectors/inventory.md`（177→176）；`tests/vectors/isa/reserved.yaml`（新增 Case 2: 0x5A→UNDI）
- E. 工具：`tools/testcases/generate_isa_vectors.py`（删 `gen_rela_si_semantic` + 所有 `is_rela` 引用）；`tools/testcases/009t-audit.py`（删 rela.si 分支）；`tools/qemu/check_005t_coverage.py`（删 rela.si）；`tools/qemu/min_rom_probe_008t.py`（删 T17 + `rela_si_rb` 函数）；`tools/qemu/min_rom_probe_009t.py`（标记 OBSOLETE）
- E. 文档：`docs/impact-matrix.md`（§5.3 标记已删除）
- E. 接口对齐：`tools/integ/check_interface_alignment.py`（3 个硬编码常量 254→253/177→176）
- 知识库：`.tao/knowledge/adr-0013-assembly-syntax.md`（删 rela.si 单位说明）
**验收结果**：
- `make check` EXIT=0（validate_vectors 176/176, check-patch-tree 67 patches OK, check-asm-list-consistency 12 OK, repository checks PASS）
- `check_interface_alignment` **80/80 EXIT=0**（1.ELF 5/2.ADR 26/3.Schema 41/4.Opcodes 8）
- `make build-qemu` PASS → `check_qemu_trans --strict` 253/253 (M1 176/176)
- `make build-mc` PASS → `llvm-lit tests/lit/MC/Dadao/ tests/lit/E2E/` 25/25 PASS
- `validate_vectors` 176/176
- opcodes.yaml: 253 条, M1 176, 0x5A 不存在
- 全量 grep `rela.si|rela_si`（排除 .0.5.3/tasks/work/session-export/m1-retrospective/testcases-009t-audit）：仅命中以下历史不变量文件（逐个列明）：
  1. `.tao/knowledge/MEMORY.md` — 历史进度记录（主会话 /complete 时统一更新）
  2. `.tao/knowledge/adr-0003-object-abi.md` — 已有删除线标注 + ADR-0012 D5 引用
  3. `.tao/knowledge/adr-0012-simrisc-0.5.4-update.md` — D5 决策记录本身
  4. `.tao/knowledge/changelog.md` — 历史变更记录
  5. `.tao/knowledge/contract-elf.md` — 已有删除线 + ADR-0012 D5 引用
  6. `.tao/knowledge/contract-isa.md` — 已有删除线 + ADR-0012 D5 引用
  7. `.tao/knowledge/deferred.md` — 历史条目（任务要求不改）
  8. `docs/issues.yaml` — 历史 issue 记录（已标注"问题消失"）
  9. `tests/vectors/isa/reserved.yaml` — 新增 Case 2（0x5A→UNDI 保留编码用例）
  10. `tools/qemu/min_rom_probe_009t.py` — 标记 OBSOLETE（历史验证产物）
  11. `tools/spec/generate_opcodes.py` — 注释行（说明 0x5A 被删除）
  12. `docs/impact-matrix.md` — 已标注"已删除"
**新发现/坑**：
- TableGen 不支持 `#` 注释（用 `//`），且不支持非 ASCII 字符（`→` 须改为 `->`）
- `git apply` 的 `@@ -0,0 +1,N @@` 中 N 必须精确等于 `+` 前缀行数（不含 `+++ b/...` 头行），修改补丁文件后必须同步更新
- `gen_asm_list.py --embed-spec` 只更新 spec 文件的 ASSEMBLY_LIST 嵌入段；`-o` 只更新输出文件；两者需分别调用
- **遗漏消费者**：`check_interface_alignment.py` 有硬编码期望常量（254/177/254），是 opcodes.yaml 条目数的隐式消费者——任务规划时未列入依赖清单，reviewer 验收时捕获
**遗留问题**：
- `min_rom_probe_009t.py` 标记为 OBSOLETE 但未删除（QEMU-009t 历史验证产物；用户可决定是否清理）
- `deferred.md` 第75条（rela.si fixup 占位语义）为历史条目未改（rela.si 已删，问题消失，但条目本身记录了历史决策过程）

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：全部 26 个改动文件逐行审查。

**审查发现**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| F1 | TableGen `#` 注释 + `→` 非 ASCII 导致 build-mc 失败 | ✅已修 | `DADAOInstrInfo.td.patch` 注释改为 `//` + ASCII `->` | build-mc PASS |
| F2 | `@@ -0,0 +1,N @@` 行计数不精确（含 `+++ b/` 行误计） | ✅已修 | 修正 trans_ctrl.c.inc.patch (732→701)、DADAOInstrInfo.td.patch (1501→1496)、DADAOFixupKinds.h.patch (50→49) | check-patch-tree 67 patches OK |
| F3 | `gen_asm_list.py` 的 `classify()` 和 `DEFERRED_SECTIONS` header 未清理 `rela*` | ✅已修 | 移除 `"rela"` from startswith + 更新 header 计数 | assembly-list.md 无 rela 命中 |
| F4 | `generate_isa_vectors.py` 遗留 `is_rela` 变量引用（4 处） | ✅已修 | 逐处移除 `is_rela` 引用 + 删除 `gen_rela_si_semantic` 函数 | `grep is_rela` exit 1 |
| F5 | QEMU insn.decode.patch 加注释行非标准（补丁文件中注释可能干扰 `git apply`） | ⏸延后 | 未改——注释行以 `+` 前缀被 `git apply` 视为新增内容，不影响功能；实际 `make prepare` 已验证通过 | `make prepare` EXIT=0 |

**判决**：所有功能性 finding 已修复，F5 为非功能性注释行（已有验证通过证据）。可标「待验收」。

#### 第 2 轮 engineer 返工

**返工依据**：reviewer 判 Needs Revision — `check_interface_alignment.py` 有 3 个硬编码期望常量 (254/177/254) 未随契约同步，导致 78/80 EXIT=1。

**改动**：
- `tools/integ/check_interface_alignment.py` L622-627: `EXPECTED_TOTAL` 254→253, `EXPECTED_M1` 177→176, 注释同步
- `tools/integ/check_interface_alignment.py` L705-707: `EXPECTED_TRANS` 254→253, 注释同步

**复验**：`check_interface_alignment` **80/80 EXIT=0**（真实输出已贴上方）

**自审**：
| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 check_interface_alignment 常量未同步 | ✅已修 | 3 个常量 254→253/177→176 + 注释 | 80/80 EXIT=0 |

#### 第 1 轮 reviewer 验收

**审查者独立重跑，未采信完成区转述。** 工作目录 `/home/ubuntu/DADAO-v5`；临时产物 `/tmp/opencode/SPEC-057t-review/`；日志 `.work/log/spec/SPEC-057t-*-review.log`。真实仓库未被污染（`git status --short` 前后均 26 项）。

**1. 计数（独立复算）**

- `contracts/opcodes.yaml`（PyYAML 直载）：`len=253`、M1=**176**、`excluded_m1=77`；`op=0x5A` 条目 **0**；`rela*` 条目 **0**。
- `tests/vectors/inventory.md`：M1 行 **176**（`grep -c '^| \`'`=176；标题「176 条」）。
- `validate_vectors`：`176/176 M1 identities covered OK (inventory sync OK; 15 data files, 735 cases; data coverage gaps: 0)`。
- `check_qemu_trans --strict`：`253/253 insns have trans impl (M1 176/176)`，**EXIT=0**。
- `check_lit_bytes`：`53 patterns OK` EXIT=0（HEAD 同值，非本任务变动）。
- `check_qfc_coverage`：QFC 253 / YAML 253，双向差异 0，EXIT=0。

**2. `0x5A` → UNDI（独立 QEMU oracle）**

自建最小 ROM 探针 `/tmp/opencode/SPEC-057t-review/probe_0x5A.py`（trampoline + `0x5A040001` 为首条测试指令）：

```
reserved Case0 0x08040001           exit=137
reserved Case1 0x1B040001           exit=137
rela old 0x5A040001                 exit=137   ← UNDI
illi 0x00000000                     exit=136
cfx excluded cfx2rd 0x7A000000      exit=136
```

即 `0x5A` 与其他 QFC 空白单元格一致 → UNDI(137)，且与 ILLI(136)/`excluded_m1`(136) 可区分。`tests/vectors/isa/reserved.yaml` Case 2（word=0x5A040001、`reserved: true`、`expected_fault: UNDI`、spec_cite ADR-0012 D5）内容已核对。

**3. 门控与构建**

- `make check`：**EXIT=0**（validate_vectors 176/176；check-patch-tree 67 patches OK；check-asm-list-consistency 12 spec files OK；repository checks: PASS）。
- `llvm-lit tests/lit/MC/Dadao/ tests/lit/E2E/`：**Total 25 / Passed 25 (100.00%)**，EXIT=0。
- 完整 `make build-mc`/`build-qemu` 未重跑（长任务，按规则不擅自启动），以等价证据替代：
  - `make apply-series` → `already applied; skipping`，EXIT=0（工作树 == 补丁全量应用态）；
  - 应用源一致性：`.work/source/qemu/.../insn.decode` 253 pattern、无 `rela` trans；`.../DADAOInstrInfo.td` 188 def、无 rela def；
  - 二进制 mtime 晚于源（llvm-mc 11:45 > InstrInfo.td 11:32；qemu-system-dadao 11:16:51 > insn.decode 11:16:10）；
  - 功能探针：`llvm-mc -triple=dadao` 汇编 `rela.si` → `error: unrecognized instruction mnemonic`（EXIT=1）；QEMU `0x5A` → UNDI(137)。

**4. 生成物可复现**

- 重跑 `generate_opcodes.py`（OUT_PATH 改指 /tmp）→ 与 `contracts/opcodes.yaml` **byte-identical**。
- 重跑 `gen_asm_list.py -o /tmp/...` → 与 `docs/assembly-list.md` **identical**；`--embed-spec` → `git diff -- spec/` 仅本任务那 3 个文件（其余 9 个嵌入表 byte-identical）。
- 重跑 `generate_isa_vectors.py`（/tmp 副本）→ `tests/vectors/isa/*.yaml`**全部 byte-identical**（diff 空）。

**5. 残留 grep 判定**

`grep -rn "rela\.si\|rela_si"`（排除 `.git`/`.work`）= 283 行，逐类判定**全部为历史不变量或有意注记**，无「新引入的活体引用」：

- 禁改文件：`spec/SimRISC-0.5.3/**`(7)、`docs/m1-retrospective.md`(2)、`docs/testcases-009t-audit.md`(2)、已完成 `.tao/tasks/**`、`deferred.md`(1)。
- 有意注记：`adr-0012`(6)、`adr-0003`(3)、`contract-isa.md`(2)/`contract-elf.md`(2)（删除线划改 + ADR-0012 D5 引用）、`impact-matrix.md`(1)、`reserved.yaml`(2)、`generate_opcodes.py`(1 注释)、QEMU `insn.decode.patch`(1 注释)、LLVM `DADAOInstrInfo.td.patch`(1 注释)。
- 历史台账：`MEMORY.md`(2)/`changelog.md`(8)/`issues.yaml`(2)（`/complete` 统一更新）。
- `tools/qemu/min_rom_probe_009t.py`(49)：**判定可接受（历史产物）**——已标 OBSOLETE/DO NOT RUN，`grep` 确认无任何自动入口调用；`tools/` 编译门控通过（compileall）。不构成假绿（无入口）。是否删除留用户/架构师裁定（与任务书遗留一致），非阻断。

**6. 反例注入（/tmp 副本，可复原+已复原）**

在 `/tmp/opencode/SPEC-057t-review/inj/`（仓库 /tmp 镜像，排除 `.work`/`.git`）注入 `rela.si_riii_rb`(=op 0x5A) 回 `contracts/opcodes.yaml`：

```
validate_vectors:            EXIT=1  INVENTORY MISSING + reserved.yaml case[2] word 0x5A040001 matches defined
check_qemu_trans --strict:   EXIT=1  253/254 (M1 176/177) MISSING trans_rela_si_riii_rb
check_asm_list_consistency:  EXIT=1  content length mismatch
make check:                  EXIT=2  （validate-vectors 拦截）
```

复原（md5 `b1b3cced19f99fef24891f17b9a0a75d` 一致）后 `make check` **EXIT=0**。注入仅作用于 opcodes.yaml（纯 Python 门控消费），未触碰组件源码/二进制，故无需重建。

**7. 未弱化既有断言**

`git diff` 核对：`tests/lit/**` 未改；`reg-arith.yaml` 仅删 3 条 rela.si 用例；`inventory.md` 仅删 rela 行；`validate_vectors.py` 未改（门控未放松）；生成器重跑 byte-identical。无「改契约/测试凑绿」。

**8. 阻断发现（唯一）——`check_interface_alignment` 被打破为红门控**

- 父提交 HEAD（`08f8498`）独立重跑：`总计 80 项 | PASS 80 | FAIL 0`，**EXIT=0**。
- 当前工作树重跑：**EXIT=1**，`总计 80 项 | PASS 78 | FAIL 2`：

```
[4.Opcodes] opcodes.yaml 条目数   FAIL  期望 总计254/M1177，实际 总计253/M1176
[4.Opcodes] QEMU trans_* 定义数    FAIL  期望 254 trans_*，实际 253
```

- 原因：该文件硬编码 `EXPECTED_TOTAL=254`(L626)/`EXPECTED_M1=177`(L627)/`EXPECTED_TRANS=254`(L707)，未随本任务同步。
- **任务书自证其属本任务范围**：任务书「为什么是一个原子任务」明确把 `check_interface_alignment` 列为 `opcodes.yaml` 的消费者，并写「删 `rela.si` 必然同时改动契约与全部消费者……必须一次性把契约与所有消费者同步」。⇒「消费者未同步 → 红门控」属任务未完成，而非可选后续。项目先例：`SPEC-024t` 在 opcodes 变更时修复了同两项（254/177）。
- 已在 /tmp 镜像验证修复方案：仅将这 3 个常量改为 253/176/253 → 立即恢复 `80/80 EXIT 0`（未改真实仓库）。

**约束核验**

| 约束 | 结果 | 证据 |
|---|---|---|
| A–F 逐段落地 | 通过（除 §8） | opcodes 253/176；spec 12/00/06 + assembly-language；QEMU decode+trans；LLVM MC 5 文件；向量+工具；impact-matrix |
| 补丁集（树形+一文件一补丁+`git apply`） | 通过 | check-patch-tree 67 patches OK；apply-series 幂等跳过 |
| 期望值独立推导（不反填） | 通过 | 生成器重跑一致；我独立复算计数 |
| 计数 253/176/0x5A 不存在/176/176…/253-253 | 通过 | §1、§2 |
| `0x5A`→UNDI 保留用例存在 | 通过 | reserved.yaml Case 2 + QEMU 探针 137 |
| `make check` EXIT=0 / lit 全绿 | 通过 | §3 |
| 全量 grep 仅历史不变量/有意注记 | 通过 | §5 |
| 反例注入可复原且须重建 | 通过 | §6 |
| 不得弱化既有断言 | 通过 | §7 |
| 命令缺失/构建失败即停 | 通过 | 未发生 |
| **全部消费者同步（任务书原子性要求）** | **不通过** | `check_interface_alignment` EXIT=1（§8） |

**判决：Needs Revision**

理由：验收标准 1–6 除「原子性/无半成品」外均在我的独立重跑下通过，交付主体正确（253/176、`0x5A`→UNDI、四门控绿、反例可失败）。但本任务书的原子性前提（「必须一次性把契约与所有消费者同步」）未满足——`tools/integ/check_interface_alignment.py` 由 HEAD 的 `80/80 EXIT=0` 退化为 `78/80 EXIT=1`，正是任务书点名要消除的「红门控中间态」。

修复建议（具体）：
1. 改 `tools/integ/check_interface_alignment.py`：`EXPECTED_TOTAL 254→253`、`EXPECTED_M1 177→176`、`EXPECTED_TRANS 254→253`，并同步 L622/623/705 注释中的 254/177；我在 /tmp 镜像实测改后 `80/80 EXIT=0`。
2. 重跑 `python3 tools/integ/check_interface_alignment.py`（应 80/80 EXIT=0）与 `make check`（EXIT=0）。

（若架构师判定该文件属 `integ` 模块、另立任务修复，则请在任务书中显式登记该跨模块影响并从本任务排除；否则按上述在本任务内闭合。本项属设计/路线层判定，供架构师定夺。）

**非阻断观察**

- `009t-audit.py` 当前 EXIT=1（28 条 ctrl-br/mem-ra/mem-rb mismatch）：我用 `git archive HEAD` 在 /tmp 重跑 HEAD 版，mismatch 集合与当前**完全一致**，确认为 pre-existing，与本任务无关。
- `validate_instrinfo.py` 179 errors（pre-existing 命名漂移，`deferred.md` 已登记）。
- `min_rom_probe_009t.py` 保留为 OBSOLETE：可接受（§5），是否清理交用户决定。
- `insn.decode` 的 `0x5A` 注释行系人手加入（生成器不产出）：`validate_decodetree` 跳过注释故不影响门控；若未来重跑生成器会丢失该注释，属可维护性提示，非阻断。

#### 第 2 轮 reviewer 复核

**审查者独立重跑，未采信返工转述。** 本轮只针对第 1 轮阻断项 F1（`check_interface_alignment` 三常量）复核，并全套回归。

**1. F1 改动范围核对（`git diff`）**

`tools/integ/check_interface_alignment.py`：`1 file changed, 6 insertions(+), 6 deletions(-)`，仅 3 处常量 + 注释：
- L622 `EXPECTED_TOTAL 254→253`、L623 注释同步
- L627 `EXPECTED_M1 177→176`、L622 注释同步
- L707 `EXPECTED_TRANS 254→253`、L705 注释同步

无其它断言被改动、无 FAIL→SKIP/MANUAL 降级、`EXPECTED_LIT=53`/`EXPECTED_E_FLAGS` 未动。逐文件比对确认本轮工作树相对第 1 轮快照**仅 integ 文件 + 任务书**有改动（其余 26 个产出文件 byte-identical）⇒ 无越界、无夹带。

**2. F1 重跑（我自己执行）**

```
$ python3 tools/integ/check_interface_alignment.py; echo EXIT=$?
总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
  1.ELF: 5  2.ADR: 26  3.Schema: 41  4.Opcodes: 8
全部机械可判定项 PASS。
EXIT=0
```

**3. 全套门控回归（我自己执行）**

| 命令 | 真实输出 | 退出码 |
|---|---|---|
| `make check` | `validate_vectors: 176/176 … gaps: 0`；`check-patch-tree: 67 patches OK`；`check-asm-list-consistency: 12 spec files OK`；`repository checks: PASS` | **0** |
| `check_qemu_trans.py --strict` | `253/253 insns have trans impl (M1 176/176)` | **0** |
| `validate_vectors.py` | `176/176 M1 identities covered OK (inventory sync OK; 15 data files, 735 cases; data coverage gaps: 0)` | **0** |
| `llvm-lit tests/lit/MC/Dadao/ tests/lit/E2E/` | `Total Discovered Tests: 25 / Passed: 25 (100.00%)` | **0** |

**4. 无新回归**

- 计数（PyYAML 直载）：opcodes `len=253`、M1=**176**、`excluded_m1=77`；`op=0x5A` **不存在**；`rela*` **0**；`inventory.md` M1 行 **176**。
- `0x5A→UNDI`：重跑独立 QEMU 探针 → `0x5A040001 -> exit=137`（UNDI，与 ILLI=136 区分）。
- 残留 grep：290 行；除任务书自身（本轮新增复核文本）外，**唯一新增命中**为 `check_interface_alignment.py:623` 的有意注释（解释 `rela.si` 删除 254→253），与此前「有意注记」同类；无任何新引入的活体引用。
- 禁改文件：`git diff --name-only` 中**不含** `spec/SimRISC-0.5.3/`、`m1-retrospective.md`、`testcases-009t-audit.md`、`deferred.md`、已完成 `.tao/tasks/**`（仅当前任务书本身）。

**5. 反例注入（/tmp 新镜像，可复原+已复原）**

在 `/tmp/opencode/SPEC-057t-review/inj2/`（本轮新 rsync 的 /tmp 镜像）注入 `rela.si_riii_rb`(=0x5A) 回 `contracts/opcodes.yaml`：

```
validate_vectors:            EXIT=1  INVENTORY MISSING + reserved case[2] word 0x5A040001 matches defined
check_qemu_trans --strict:   EXIT=1  253/254 (M1 176/177)
check_interface_alignment:   EXIT=1  [4.Opcodes] opcodes.yaml 条目数 FAIL（期望 253/M1176，实际 254/M1177）
make check:                  EXIT=2
```

复原（md5 `b1b3cced19f99fef24891f17b9a0a75d`）后：`make check` **EXIT=0**、`check_interface_alignment` **EXIT=0（80/80）**，无残留。改后 integ 门控仍是**承重**的（反例下仍 FAIL）。

**判决：Accepted**

理由：第 1 轮唯一阻断项 F1 已按建议修复（3 常量 254/177/254 → 253/176/253 + 注释），我在自己的重跑下 `check_interface_alignment` 恢复 **80/80 EXIT=0**；全套门控 `make check`(EXIT=0)、`check_qemu_trans --strict`(253/253, M1 176/176)、`validate_vectors`(176/176)、`llvm-lit`(25/25) 全绿；计数（253/176、0x5A 不存在）、`0x5A→UNDI`、残留判定、禁改文件、反例注入（可检出且复原无残留）均无新问题；改动范围严格限于 1 文件 3 常量，无弱化断言、无凑绿。

**说明**：我第 1 轮判 Needs Revision 时曾注明「若架构师判定该文件属 integ 模块另立任务，请显式登记并排除」——工程师选择在本任务内就地闭合（与任务书「必须一次性把契约与所有消费者同步」一致），此为本任务范围内的合法处置，故予 Accepted。终审交架构师。
