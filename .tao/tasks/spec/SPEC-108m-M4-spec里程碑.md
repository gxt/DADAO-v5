# SPEC-108m: M4 spec 里程碑

**模块**：spec
**项目里程碑**：M4
**状态**：待开始
**目标**：M4 的规范层收口——① `contract-elf.md §2–§4` 由 `Deferred to M2` 转为规范正文（按 `ADR-0019` 的 RELA/`ABS48/REL26/REL20/REL14`/无 −4/溢出=link-time error/禁用 relaxation）；② 伪指令集收缩按 `ADR-0013 D11` 落地（权威源迁 `Toolchain-01 §6`；留 8 条合成型、删 10 条别名、`ret` 不加无参、反汇编只显真实指令）并登记上游偏离台账；③ `ADR-0004` 的 ELF `e_entry`/段布局/加载约定调整（若需，经用户逐条确认）与 `contract-elf §5/§6` 同步；④ **MISC-AMO 编码调整**按 `ADR-0012 D3.5` 落地（删 `illi`、`fence ha 0x01→0x00`、`swym ha 0x02→0x22`，跨组件原子 `SPEC-109t`）；⑤ **`Process-05 §6` 落点路径同步**（`INFRA-045t` 组件先行重排后示例路径过期，按 `ADR-0012 D4` 由 spec 模块同步）。为 LLVM/LLD/QEMU 的 M4 实现提供稳定期望值来源。
**关联任务**：`SPEC-105t`、`SPEC-106t`、`SPEC-107t`、`SPEC-109t`、`SPEC-110t`（5 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`.tao/knowledge/contract-elf.md`（§2–§4 正文）、`spec/Toolchain-01 §6`（权威伪指令）+ `spec/SimRISC-00/…` 修订 + `.tao/knowledge/contract-asm.md §6/§11`、`.tao/knowledge/MEMORY.md` 偏离台账（7 项）、`adr-0004` 修订（若需）+ `contract-elf §5/§6`、`contracts/opcodes.yaml`（`illi` 删除 / `fence 0x77000000` / `swym 0x77880000`）
- `contract-elf §2–§4` 与 `ADR-0019` D1–D8 **逐条无矛盾**（编号/公式无 −4/溢出 link-time error/禁用 relaxation）
- `ADR-0012 D3.5` 的 MISC-AMO 编码调整（删 `illi`/`fence`→`0x00`/`swym`→`0x22`）在 `spec`/`contracts`/LLVM/QEMU/tests 全落地且 `check-interface` 绿；`m1=151`/`total=227`
- 伪指令修订与 `ADR-0013 D11` 一致；`ret` 无无参形态；反汇编只显真实指令；权威源唯一为 `Toolchain-01 §6`
- 若调整 `ADR-0004`：每个被改 decision 有**用户逐条确认原话**；`contract-elf §5/§6` 与之同步
- `spec/Process-05-里程碑TDD规范.md §6` 落点示例已随 `INFRA-045t` 同步为新路径（`tests/llvm/lit/MC/DADAO/`、`tests/llvm/lit/CodeGen/DADAO/`、`tests/llvm/codegen/`（+`m4/`）、`tests/qemu/`、`tests/e2e/lit/`）；§1–§5/§7 语义未动
- `make check` 全绿（含 `check-spec-refs`/`check-asm-*`/`check-spec-codeblocks`）
- M4 内**未**改 `contract-elf` 之外的 spec 正文，除 `SPEC-106t` 的伪指令修订（含实测扩展文件）、`SPEC-107t` 的 §5/§6、`SPEC-109t` 的 `SimRISC-00/11`（MISC-AMO 编码）与 `SPEC-110t` 的 `Process-05 §6`（路径同步）

## 核验记录（主会话）
（核验命令、输出与退出码；结论）
