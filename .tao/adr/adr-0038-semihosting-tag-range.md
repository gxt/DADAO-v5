# ADR-0038: semihosting 判定改为 `immu18` 范围 `0x3FF00–0x3FFFF`

**状态**：Accepted
**日期**：2026-10-26
**关联**：`ADR-0020`（`D1`/`D10` 被本 ADR 取代）、`SPEC-175t`（HBI `0x30001`）、`SPEC-176t`（正文落点）、`QEMU-076t`（译码/测试迁移）、`spec/Machine-01`、`.tao/contracts/contract-see.md`、`.tao/contracts/contract-semihosting.md`

> **决策来源（用户原话，2026-10-26，经主会话问答）**：「**0x3ff00-0x3ffff**」；D1/D2/D4/D5 逐条确认，D3 待定。
> **ADR 不承载规范正文**（`docs/Process-03`）：判定文本、调用约定由 `spec/Machine-01` 与 contracts 落笔。

## Context（背景）

- `SPEC-175t` 按用户裁定把 HBI 初始化服务定为 `HBI_<name>_INIT` = `immu18` bits[17:16]=`0b11`、bits[15:0]=1，即 **`0x30001`**（`DADAO-23 §3`）。
- 但 `ADR-0020 D1/D10` 把 **`immu18[17:16] == 2'b11`** 定义为 **semihosting**（与 `cfxha` 无关），`contract-see.md:44/47`、`contract-semihosting.md:17-18` 同口径。
- 结果：`trap cfx_<name>, 0x30001` 会被实现层当作 semihosting **短路**，不进入 cfx 向量 —— 逐 cfx HBI 初始化**不可用**（`SPEC-175t` 引入的冲突）。
- 用户 2026-10-26 裁定：**改 semihosting tag**，新范围 **`0x3FF00–0x3FFFF`**；`0x30001` 保持不动。

## Decision（决策，逐条）

- **D1 — semihosting 判定**：`trap cfxHA, immu18` 中 **`immu18[17:8] == 0x3FF`**（即 `0x3FF00–0x3FFFF`）⇒ semihosting；**与 `cfxha` 无关**。原 `immu18[17:16] == 2'b11` 判定作废。
- **D2 — HBI INIT 保持**：`HBI_<name>_INIT` 仍为 `0x30001`（bits[17:16]=`0b11`）；`DADAO-23 §3` 补一句「该编码不落在 semihosting 区（`0x3FF00–0x3FFFF`）」。
- **D3 — SBI 保留值处置（不属本 ADR 决策）**：`DADAO-22:863` 的保留值 `0x3FFFF` 现落入 semihosting 区，处置（移到 `0x3FEFF` / 删除 / 收窄范围）待定，登记 `ISS-334`。
- **D4 — 调用点迁移**：所有 semihosting 调用从 `0x300xx` 迁到 **`0x3FFxx`**（低 8 位 op 不变）；QEMU 译码由 `((immu18 >> 16) & 3) == 3` 改为 **`immu18 >= 0x3FF00`**。
- **D5 — 文档与 ADR**：`ADR-0020` 的 `D1`/`D10` 标 **`Superseded by ADR-0038`**（不改原文）；`spec/Machine-01 §4.1/§5.1/§5.2`、`contract-see.md`、`contract-semihosting.md` 同步改判定；`Machine-01` 版本 `0.3.1` → `0.3.2-rc`。

## Rationale（理由）

- `0x3FF00–0x3FFFF` 是 18 位空间**顶部 256 个值**：避开 SBI 小号 FID（`<0x100`）与 HBI INIT `0x30001`；semihosting op 仍占低 8 位，迁移是**常量替换**（`0x30000+op` → `0x3FF00+op`）。
- 不改 `HBI INIT` 的 `0b11` 类编码，保留 `SPEC-175t` 的「类 + 服务号」设计意图。

## 被否方案

- **A：HBI INIT 改 `0x20001`（`0b10` 类）** —— 用户否；不动 semihosting，但放弃 `0b11` 类。
- **B：HBI INIT 改 `0x0100`（小号统一 FID）** —— 用户否；与「类」设计不符。
- **C2：收紧判定为「`0b11` 且 low16 ≤ 0xFF」** —— 仍需改 HBI FID 且规则不直观；用户选「迁移 tag」。

## Consequences（影响）

- **规范/合约**：`spec/Machine-01`、`contract-see.md`、`contract-semihosting.md`、`DADAO-23 §3`。
- **代码/测试**：QEMU 译码；`bootrom{,_app}.S`、`codegen_crt0.s`、`build_test_binary.py`、`tests/llvm/codegen/m5/m5_semi_*.s` 与 `expected.yaml`、`tools/qemu/min_rom_probe_*` —— 全仓 `0x30000/2'b11` 约 **93 处、20 个文件**。
- **只读锁**：`spec/Machine-01` 需用户本次授权（随任务记录原话）并重算 sha256。
- **遗留**：`0x3FFFF` 与 SBI 保留值冲突（`ISS-334`）；`0x3FFxx` 未来若要扩 HBI 类服务需避开该区。
