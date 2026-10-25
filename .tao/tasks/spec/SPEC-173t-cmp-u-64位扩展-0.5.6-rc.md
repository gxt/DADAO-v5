# SPEC-173t: `cmp.{ut,uw,ub}` 的 -1 改为 64 位全 1（0.5.6-rc）

**模块**：spec
**项目里程碑**：M10
**依赖**：ADR-0037（已 Accepted）
**状态**：待开始

## 执行环境
**执行环境**：本地（纯文档，无构建）

## 接口规范

### 背景（ADR-0037，用户原话）
- 原文 `SimRISC-08/09/10 §1.2` 写「`.ut/.uw/.ub ⇒ 结果零扩展」⇒ `cmp.ut(-1)` = `0x00000000FFFFFFFF`，`br.n`（看 bit63）判负失效。
- 用户裁定：**-1 结果按 64 位扩展（全 1）**；版本 `0.5.6-rc`，`-rc` 不归档。
- 用户另指出：`SimRISC-00` 第 255 行「SimRISC 0.5.4版本的指令 opc 布局如下」**不应带版本号**。

### 输出（逐条）
1. `spec/SimRISC-08 §1.2`、`SimRISC-09 §1.2`、`SimRISC-10 §1.2`：
   - 高位规则改为：**-1 ⇒ 64 位全 1（符号扩展）；0 ⇒ 0；+1 ⇒ 1**；源操作数仍按 width 截断；`.st/.sw/.sb` 不变。
   - 同步修正该段的例子文字。
2. `spec/SimRISC-00` 第 255 行：删去「0.5.4」，改为不带版本号的表述。
3. **13 册**版本头 `**版本：0.5.5**` → `**版本：0.5.6-rc**`（含 `SimRISC-00`）。
4. `spec/SimRISC-00` 变更记录：新增 `### 0.5.6-rc（2026-10-25）` 段（在 `### 0.5.5` 之前），记「修正 `cmp.{ut,uw,ub}` 的 -1 扩展（原文零扩展为错误）」。
5. `.tao/contracts/contract-isa.md` 的 `cmp.*` 行补「-1 = 64 位全 1」口径（若其版本头需同步，按门控提示）。
6. `manifests/spec-readonly.lock.toml`：按 `tools/spec/check_spec_readonly.py` 提示更新被改文件的 sha（**用户已授权本次 spec 修改**）。
7. **不建** `.tao/archive/SimRISC-0.5.6-rc/`（`-rc` 不归档）。

### 约束
- 只改上述文件；不改其它 spec 册正文。
- 若 `check-spec-drift` / `check-spec-changelog` 要求额外同步（如契约头版本），按提示处理并记完成区。

## 验收标准
1. `make check`（L1：`check-spec-numbering` / `check-spec-changelog` / `check-spec-purity` / `check-spec-cite-targets` / `check-spec-drift` / `check-spec-readonly`）rc=0。
2. `python3 tools/spec/gen_spec_archive.py --verify` rc=0（0.5.6-rc 应 `SKIP`）；`check_spec_archive.py` rc=0。
3. 13 册版本头一致为 `0.5.6-rc`；`SimRISC-00` 第 255 行无版本号（贴改后行）。
4. 08/09/10 三处 §1.2 文字与 ADR-0037 一致（贴 diff）。
5. 完成区贴真实命令、输出、退出码。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
