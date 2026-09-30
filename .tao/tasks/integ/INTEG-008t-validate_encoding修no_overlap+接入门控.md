# INTEG-008t: `validate_encoding.py` 修 `no_overlap` + 接入 `make check`

**模块**：integ（含仓库根 `Makefile`）
**项目里程碑**：M1→M2
**依赖**：`SPEC-060t`（暴露该缺陷）、`INTEG-007t`（门控接线先例）
**状态**：已验证

## 问题（两个）

### A. `validate_encoding.py` 有 **pre-existing 报错**

```
$ python3 tools/spec/validate_encoding.py contracts/opcodes.yaml
ERROR: rd2rd_orri_rd: legality 'no_overlap(rdhb, rdhc, immu6)' 引用了不存在的字段/标识符 'no_overlap'
ERROR: rb2rb_orri_rb: legality 'no_overlap(rbhb, rbhc, immu6)' 引用了不存在的字段/标识符 'no_overlap'
验证失败: 2 个错误   (EXIT=1)
```

根因：`tools/spec/validate_encoding.py:121` 的 `ALLOWED_NON_FIELD = {"rd0","rb0","ra0","rf0","aligned"}` **未登记函数式标识符 `no_overlap`**（`check_legality_refs()` 用 `re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr)` 取 token，函数名也被当作标识符检查）。

**全量扫描结论（主会话已跑，`修一类` 依据）**：`contracts/opcodes.yaml` 全部 legality 表达式中，**唯一**未注册标识符就是 `no_overlap`（2 处：`rd2rd_orri_rd`、`rb2rb_orri_rb`）；其余 token 均为字段名或 `{rd0,rb0,ra0,rf0,aligned}`。

### B. 该脚本**未接入任何门控**

`make check` = `manifest-check validate-vectors check-spec-drift check-patch-tree check-asm-list check-issues compileall check-interface` —— **不含**它；`grep -rn validate_encoding Makefile tools/` 无调用方。
⇒ 它报 2 个 ERROR 而 `make check` 仍 EXIT=0（静默漂移，与 `INTEG-007t` 同类）。

## 修改内容

### 1. `tools/spec/validate_encoding.py`（去噪、修一类）

- 在 `ALLOWED_NON_FIELD` 中登记 **`no_overlap`**（保持既有显式白名单风格；**不**改为「任意 `name(` 都放过」——那会削弱检查）。
- 全量复查：改后 `python3 tools/spec/validate_encoding.py contracts/opcodes.yaml` **EXIT=0**；并**证明**除 `no_overlap` 外无其它未注册标识符（贴扫描命令与输出）。

### 2. `Makefile`（接入门控）

- 新增 target **`validate-encoding`**（调用该脚本，带 `contracts/opcodes.yaml` 参数）；
- 加入 `check:` 的依赖（先例 `INTEG-007t` 的 `check-interface`）；
- `.PHONY` 与 help 文本同步。

### 3. 评估项（**预期不改**，如判断需改须在完成区说明理由并**停下询问**）

- ADR-0012 **D3.2**（"寄存器复制不允许覆盖范围"）目前**只在** `opcodes.yaml` 的 per-instruction legality（`no_overlap(...)`）表达，`contracts/legality_rules.yaml` 中**无**对应的规则条目。是否需要在 `legality_rules.yaml` 补一条（如 `copy_range_overlap`）？**本任务不擅自改**，仅评估与报告。

## 约束

- **不改** `contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、`spec/`、QEMU（除非评估项经用户同意）。
- 反例注入须**可复原**；命令缺失/失败 → **停下报告**。
- 不引入新依赖。

## 验收标准

1. `python3 tools/spec/validate_encoding.py contracts/opcodes.yaml` **EXIT=0**（贴真实输出）。
2. **修一类证据**：贴全量 legality token 扫描（证明仅 `no_overlap` 一项且已修）。
3. **接线有效（关键）**：在 `/tmp` 副本中向 `contracts/opcodes.yaml` 的某条 legality 注入一个**不存在的标识符**（如 `bogus_fn(rdha)`）→ **`make check` 变红**（EXIT≠0，且失败来自 `validate-encoding`）；复原后 EXIT=0。
4. **反例门控**：(a) 把 `no_overlap` 从 `ALLOWED_NON_FIELD` 移除 → 脚本 **FAIL**（2 错）；(b) 注入非法标识符 → 脚本 **FAIL**；(c) 注入**真**字段名（如 `rdha != rd0`）→ **PASS**（证明不致过度报错）。各给真实输出。
5. 正常态：`make check` **EXIT=0**；`python3 tools/integ/check_interface_alignment.py` **80/80 EXIT=0**；`validate-vectors` 仍绿。
6. 反例注入**可复原**（`git status`/`git diff` 证据）；`git diff --name-only` 与清单对齐（`Makefile` + `tools/spec/validate_encoding.py` + 任务文件）。
7. 评估项结论写入完成区（需/不需补 `legality_rules.yaml` 规则 + 理由）。

## 完成区
**测试结果**：全部验收项通过
**修改文件**：`Makefile`、`tools/spec/validate_encoding.py`（+任务文件）
**验收结果**：
1. `python3 tools/spec/validate_encoding.py contracts/opcodes.yaml` → `validate_encoding: 253 条记录 OK` EXIT=0 ✓
2. **修一类证据**（全量 legality token 扫描）：
   ```
   === All legality tokens (16) ===
   aligned, immu18, immu6, no_overlap, raha, rahb, rahc, rb0, rbha, rbhb, rbhc, rd0, rdha, rdhb, rdhc, rdhd
   === Unknown identifiers (0) ===   ← 修前为 2（仅 no_overlap），修后为 0
   ```
3. **接线有效**：注入 `bogus_fn(rdha)` → `make check` 变红（EXIT=2，失败来自 `validate-encoding`：2 个错误）；复原后 EXIT=0 ✓
4. **反例三例**：
   - (a) 移除白名单项 `no_overlap` → FAIL（2 错：rd2rd_orri_rd + rb2rb_orri_rb）EXIT=1 ✓
   - (b) 注入非法标识符 `bogus_fn(rdha)` → FAIL（2 错：`bogus_fn` + `rdha` 均非该记录字段）EXIT=1 ✓
   - (c) 注入真字段名 `rdhb != rd0` → PASS（`rdhb` 是真实字段，`rd0` 是白名单常量）EXIT=0 ✓
5. 正常态：`make check` EXIT=0 ✓；`check_interface_alignment.py` 80/80 EXIT=0 ✓；`validate-encoding` EXIT=0 ✓
6. 反例注入可复原：注入前备份 `/tmp/opencode/INTEG-008t/opcodes.yaml.bak`，复原 `cp` 后 `make check` EXIT=0 ✓
7. `git diff --name-only`：`Makefile` + `tools/spec/validate_encoding.py` ✓
8. **评估项结论**：见下方「评估项」。

**评估项：ADR-0012 D3.2 `no_overlap` 是否需补 `legality_rules.yaml` 条目**
- **结论**：建议补，但本任务不擅自改。
- **理由**：
  - D3.2 原文（ADR-0012）：「寄存器复制不允许覆盖范围：rd2rd/rb2rb 等块赋值指令，源范围与目的范围有任何交集即报 ILLI」——这是一条**运行时语义规则**（实现必须在执行时检查并报 ILLI）。
  - `legality_rules.yaml` 已有 `multi_immu6_zero` 和 `multi_range_overflow` 两条块赋值相关规则（静态），但**无覆盖检查**规则。
  - 当前 `no_overlap` 仅在 `opcodes.yaml` 的 per-instruction legality 中表达（2 条：`rd2rd_orri_rd`、`rb2rb_orri_rb`），是编码层标注而非独立规则条目。
  - `legality_rules.yaml` 的定位是「规则目录」，每条规则有 `id/fault/kind/spec_cite/status/description`——D3.2 的覆盖检查完全符合该格式。
  - **需补的条目建议**：`id: copy_range_overlap`、`fault: ILLI`、`kind: dynamic`、`spec_cite: SimRISC-02 §寄存器复制`、`status: active`。
  - **需用户确认后方可执行**（AGENTS.md 约束：不改 `contracts/legality_rules.yaml` 除非评估项经用户同意）。

**新发现/坑**：
- `check_legality_refs()` 用 `re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr)` 提取 token，函数名（如 `no_overlap`）也会被当作标识符检查——白名单必须显式登记函数式标识符。
- `bogus_fn(rdha)` 注入会报 2 个错误（`bogus_fn` + `rdha`），因为 `rdha` 不是 `rd2rd_orri_rd` 的字段（该记录字段为 `rdhb/rdhc/immu6`）。
- `legality_rules.yaml` 与 `opcodes.yaml` 的 legality 字段职责不同：前者是规则目录（实现必须检查），后者是编码标注（per-instruction 约束）。

**遗留问题**：
- 评估项（D3.2 `copy_range_overlap` 规则补入 `legality_rules.yaml`）待用户确认。

## 审阅记录

#### 第 1 轮 engineer 自审

**审阅范围**：`tools/spec/validate_encoding.py`（L121）+ `Makefile`（.PHONY/L53/L126/L158-161）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 无（所有改动最小化，逻辑正确） | — | — | — |

**判决**：通过。所有验收项真实验证，反例三例均有 FAIL 路径，接线有效（`make check` 变红/复原 EXIT=0）。

#### 第 1 轮 reviewer 验收

**审查范围**：`tools/spec/validate_encoding.py`（L121）、`Makefile`（.PHONY L25-26 / help L53 / check L126 / target L160-161）、`contracts/opcodes.yaml`（调用对象）、`contracts/legality_rules.yaml`、ADR-0012。全部命令由 reviewer 独立重跑，不采信完成区。

**1. 重跑记录（真实输出/退出码）**

- A 去噪：`python3 tools/spec/validate_encoding.py contracts/opcodes.yaml` → `validate_encoding: 253 条记录 OK`，**EXIT=0**。
- 独立全量 token 扫描（reviewer 自写 `/tmp/opencode/INTEG-008t/scan_tokens.py`，直接 import 该脚本的 `ALLOWED_NON_FIELD`）：
  ```
  ALLOWED_NON_FIELD = ['aligned', 'no_overlap', 'ra0', 'rb0', 'rd0', 'rf0']
  === all legality tokens (16) ===
  aligned, immu18, immu6, no_overlap, raha, rahb, rahc, rb0, rbha, rbhb, rbhc, rd0, rdha, rdhb, rdhc, rdhd
  === unknown identifiers (0) ===   EXIT=0
  ```
  与完成区一致（16 项、未知 0）。实现方式核对：`check_legality_refs()` L135 为 `if tok in field_names or tok in ALLOWED_NON_FIELD`，**显式白名单**，非「任意 `name(` 放过」的放宽。
- B 接线：`make check` 基线 **EXIT=0**，日志含 `validate_encoding: 253 条记录 OK`。向 `contracts/opcodes.yaml` 的 `rd2rd_orri_rd` 注入 `bogus_fn(rdha)` 后 `make check` **EXIT=2**，失败源为 `validate-encoding`：
  ```
  ERROR: rd2rd_orri_rd: legality 'bogus_fn(rdha)' 引用了不存在的字段/标识符 'bogus_fn' ...
  ERROR: rd2rd_orri_rd: legality 'bogus_fn(rdha)' 引用了不存在的字段/标识符 'rdha' ...
  验证失败: 2 个错误
  make: *** [Makefile:161: validate-encoding] Error 1
  ```
  `cp` 备份复原后 `git diff --name-only contracts/` 为空，脚本 EXIT=0。
- 反例三例（独立跑）：
  - (a) 白名单移除 `no_overlap`（`/tmp` 改本副本 `ve_no_whitelist.py`）→ 2 错（`rd2rd_orri_rd` + `rb2rb_orri_rb`）**EXIT=1**；
  - (b) 注入 `bogus_fn(rdha)` → FAIL（`bogus_fn` + `rdha`）**EXIT=1**；
  - (c) 注入**真**字段名表达式 `rdhb != rd0` → `253 条记录 OK` **EXIT=0**（不过度报错）。
- 门控：`make check` **EXIT=0**（含 `validate-vectors` 176/176、`repository checks: PASS`）；`python3 tools/integ/check_interface_alignment.py` **总数 80 项 | PASS 80 | FAIL 0**，**EXIT=0**。

**2. 约束核验（逐条）**

| 约束 | 结论 |
|------|------|
| `contracts/opcodes.yaml` 无改动 | ✓ 仅作临时注入，已复原，`git diff` 空 |
| `contracts/legality_rules.yaml` 无改动 | ✓ `git diff --name-only` 不含，`grep 覆盖/overlap` 无命中 |
| `spec/`、QEMU 0 改动 | ✓ `git diff --name-only -- spec/` 为空，无 qemu 路径 |
| `git diff --name-only` = 清单 | ✓ `Makefile` + `tools/spec/validate_encoding.py` + 任务文件 |
| 反例可复原 | ✓ 备份 `/tmp/opencode/INTEG-008t/opcodes.yaml.bak`，复原后工作树仅 3 个允许文件 |
| 不引入新依赖 | ✓ 仅改常量集合与 Makefile target |
| 不改 `no_overlap` 为放宽检查 | ✓ L135 显式白名单 |

**3. 评估项判定（`copy_range_overlap` 建议）**

- **有依据**：ADR-0012 D3.2「寄存器复制不允许覆盖范围…源范围与目的范围有任何交集即报 ILLI」是一条运行时语义规则；`legality_rules.yaml` 为规则目录，其中同类范围规则已有 `multi_range_overflow`/`ra_multi_range_overflow`，但**确无**覆盖（overlap）检查条目；`no_overlap` 当前仅出现在 `opcodes.yaml` 的 per-instruction legality（2 处）。建议与「补一条规则条目」的定位相符 → **判定有依据**。
- **未擅自改动**：`contracts/legality_rules.yaml` 无 diff，用户确认前未落盘 → 合规。
- 备注（非阻断）：建议的 `kind: dynamic` 与同类的 `multi_range_overflow`（标 `static`）口径不一致；该细节仅为提案，供架构师/用户定性时留意。

**4. 完成区真实性核对**

逐条与重跑对齐，未发现不实/矛盾：`253 条记录 OK`、16 token / 未知 0、注入 `make check` EXIT=2、反例三例、接口 80/80、EXIT=0 全部复现一致。唯一措辞瑕疵：完成区第 7 条只列 `Makefile`+脚本，未提任务文件（与验收 6 的三项清单表述略不完整），属表述不全、非事实错误。

**判决**：**Accepted**。验收命令块在 reviewer 独立重跑下全部通过（A/B/反例三例/门控），硬约束逐条无违反；接线有效（`make check` 随 `opcodes.yaml` 非法标识符变红、复原转绿）。评估项建议有依据且未擅自改动，`copy_range_overlap` 是否补入 `legality_rules.yaml` 及 `kind` 取值留待用户/架构师定夺，不构成本任务阻断。
