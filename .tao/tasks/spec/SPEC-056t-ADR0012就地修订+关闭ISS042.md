# SPEC-056t: ADR-0012 就地修订（R1–R4）+ 关闭 ISS-042

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：用户逐条确认（2026-09-30）
**状态**：待开始

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
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
