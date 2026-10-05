# SPEC-108m: M4 spec 里程碑

**模块**：spec
**项目里程碑**：M4
**状态**：待开始
**目标**：M4 的规范层收口——① `contract-elf.md §2–§4` 由 `Deferred to M2` 转为规范正文（按 `ADR-0019` 的 RELA/`ABS48/REL26/REL20/REL14`/无 −4/溢出=link-time error/禁用 relaxation）；② 伪指令集收缩按 `ADR-0013 D11` 落地（留 8 条合成型、删 10 条别名、`ret` 不加无参、反汇编只显真实指令）并登记上游偏离台账；③ `ADR-0004` 的 ELF `e_entry`/段布局/加载约定调整（若需，经用户逐条确认）与 `contract-elf §5/§6` 同步。为 LLVM/LLD/QEMU 的 M4 实现提供稳定期望值来源。
**关联任务**：`SPEC-105t`、`SPEC-106t`、`SPEC-107t`（3 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`.tao/knowledge/contract-elf.md`（§2–§4 正文）、`spec/SimRISC-00/03/…` 伪指令修订 + `.tao/knowledge/contract-asm.md §6/§11`、`.tao/knowledge/MEMORY.md` 偏离台账（7 项）、`adr-0004` 修订（若需）+ `contract-elf §5/§6`
- `contract-elf §2–§4` 与 `ADR-0019` D1–D8 **逐条无矛盾**（编号/公式无 −4/溢出 link-time error/禁用 relaxation）
- 伪指令修订与 `ADR-0013 D11` 一致；`ret` 无无参形态；反汇编只显真实指令
- 若调整 `ADR-0004`：每个被改 decision 有**用户逐条确认原话**；`contract-elf §5/§6` 与之同步
- `make check` 全绿（含 `check-spec-refs`/`check-asm-*`/`check-spec-codeblocks`）
- M4 内**未**改 `contract-elf` 之外的 spec 正文，除 `SPEC-106t` 的伪指令修订（含实测扩展文件）与 `SPEC-107t` 的 §5/§6

## 核验记录（主会话）
（核验命令、输出与退出码；结论）
