# INTEG-008t: `validate_encoding.py` 修 `no_overlap` + 接入 `make check`

**模块**：integ（含仓库根 `Makefile`）
**项目里程碑**：M1→M2
**依赖**：`SPEC-060t`（暴露该缺陷）、`INTEG-007t`（门控接线先例）
**状态**：待开始

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
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
