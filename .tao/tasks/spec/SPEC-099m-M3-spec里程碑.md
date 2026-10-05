# SPEC-099m: M3 spec 里程碑

**模块**：spec
**项目里程碑**：M3
**状态**：里程碑
**目标**：v5 标量调用约定合约落地——`contract-abi.md` §4 由 `Deferred to M2` 变为正文（参数寄存器/返回值/callee-save/帧布局/prologue-epilogue），`contracts/abi.yaml` 同步扩展，为 M3 CodeGen 提供稳定期望值来源；并落地**新增指令 `sub.o_orrr_dbb`**（RB−RB→RD，`scope:m3`）与**三条既有 RB 算术指令改名/改编码**（`add.o_orrr_bbd`/`sub.o_orrr_bbd`/`cmp.uo_orrr_dbb`）的规范正文/编码（`SPEC-100t`/`SPEC-101t`，依据 `adr-0012 D9`）。
**关联任务**：`SPEC-097t`、`SPEC-100t`、`SPEC-101t`（3 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`.tao/knowledge/contract-abi.md`（§4 正文）、`contracts/abi.yaml`（新增字段）；`spec/SimRISC-00/05` 新指令/改名正文、`contracts/opcodes.yaml`（新条目 + 3 条改名）、`check_scope.py`（含 `m3`）（`SPEC-100t`/`SPEC-101t`）
- `contract-abi.md` 每条规范句有 spec 来源标注；`contracts/abi.yaml` YAML 解析通过且与正文一致；`make check` 全绿
- **`adr-0012 D9`**（新增指令 + 三条改名/改编码，用户逐条确认）已落地；`SPEC-100t`/`SPEC-101t` 编码/legality 与 `spec/`、`opcodes.yaml`、汇编清单三处一致；全仓无旧 id 残留
- M3 取舍项（帧指针策略/栈对齐/窄返回扩展等，C1–C17）已由 `project_M3-codegen-choices.md §5` 判定固化（`ADR-0018`）；`SPEC-097t` 按判定落地，未擅自选边

## 核验记录（主会话 2026-10-05）

- 关联任务 `SPEC-097t`/`SPEC-100t`/`SPEC-101t`：均 `**状态**：已验证`。
- 产出存在：`.tao/knowledge/contract-abi.md`（§4 正文）、`contracts/abi.yaml`、`spec/SimRISC-00/05` 新指令/改名正文、`contracts/opcodes.yaml`（`sub.o_orrr_dbb` + 3 条改名）、`tools/spec/check_scope.py`（含 `m3`）。
- `python3 -c "yaml.safe_load(contracts/abi.yaml)"` → **EXIT=0**。
- `make check` → **EXIT=0**（`repository checks: PASS`；含 spec 门控/spec-refs）。
- `adr-0012 D9` 落地：`sub.o_orrr_dbb` 经 `SPEC-100t`；三条既有 RB 算术改名/改编码经 `SPEC-101t`；编码/legality/spec 三处一致。
- M3 取舍项 C1–C17 由 `project_M3-codegen-choices.md §5` 判定固化为 `ADR-0018`；`SPEC-097t` 按判定落地、未擅自选边。
- 追加：`SPEC-102t`（规范/文档一致性清理，关闭 `ISS-082/129/121/107/131`）亦已验证。
- **结论：置 `里程碑`。**
