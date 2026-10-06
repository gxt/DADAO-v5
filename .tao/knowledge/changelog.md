# Changelog

任务对仓库代码的实质改动记录（由 `/complete` 追加）。

> **M1 归档指针（2026-10-03）**：2026-09-22 及之前的 89 条 M1 条目已归档至 `.tao/archive/M1/README.md`（历史指针，不再在此追加）。

> **M2 归档指针（2026-10-04）**：2026-09-23 ~ 2026-10-04 的 61 条 M2 条目已归档至 `.tao/archive/M2/README.md`（历史指针，不再在此追加）。

> **M3 归档指针（2026-10-05）**：2026-10-05 的 35 条 M3 条目已归档至 `.tao/archive/M3/README.md`（历史指针，不再在此追加）。

| 日期 | 描述 | 执行方 |
| --- | --- | --- |
| 2026-10-06 | **`SPEC-109t`：删 `illi` / `fence`→`0x00` / `swym`→`0x22`（跨组件原子；**M4 链首**）**。据 `ADR-0012 D3.5`（用户逐条确认）：删 `illi`（**ILLI 异常保留**）、`fence ha 0x01→0x00`（`0x77040000→0x77000000`）、`swym ha 0x02→0x22`（`0x77080000→0x77880000`）；派生 `total 228→227`/`m1 152→151`。覆盖 `spec/SimRISC-00/11`+`Toolchain-01`、`opcodes.yaml`、生成器/`check_scope`、`contract-isa/asm`(list)、LLVM MC（5 补丁重导出）、QEMU（2 补丁重导出）、向量/lit/harness、`adr-0004` 注记（D5.1 行137 示例同步经用户确认保留）。**验证**：`make check`/`check-patch-tree` EXIT=0；`swym 0`→`77 88 00 00`、`fence 0`→`77 00 00 00`、`illi 0`→不识别；QEMU `swym`→exit、`fence`→ILLI；`check-interface` 80/80；`test-codegen` 15/15；证据 + 注入（fence 旧值）→FAIL→还原+重建→回绿。 | engineer + reviewer |
| 2026-10-06 | **`SPEC-104k` 增量修订（用户 2026-10-06 裁定）**。新增 `SPEC-109t`（删 `illi` / `fence`→`0x00` / `swym`→`0x22`，跨组件原子，**M4 链首**）、`INFRA-045t`（`tests/` 组件先行重排：`tests/llvm/lit/{MC,CodeGen,tools}/DADAO` + `tests/llvm/codegen[/m4]` + `tests/qemu` + `tests/e2e`）、`TESTCASES-032t`（`not`/`neg` 功能向量，L1+L3）、`SPEC-110t`（`Process-05 §6` 落点同步）；调整 `SPEC-106t`（权威伪指令集迁 `Toolchain-01`、`SimRISC-00 §伪指令` 降为「功能说明+实现」、**不产向量**）、`TESTCASES-029t/030t`（落点改新结构 + lit `UNSUPPORTED`）、`LLVM-056t`/`QEMU-042t`（补段溢出检查）；`ADR-0012 D3` **就地增补第 5 项**（用户逐条确认）。**验证**：reviewer 复核增量（26 文件、依赖无环、落点一致、`ADR-0012 D3.5` 逐字一致）Accepted；`check-no-residue` EXIT=0。 | architect + reviewer |
| 2026-10-06 | **`SPEC-104k`：M4 启动与分解**。M4 = 「ELF 文件支持 + LLD 链接 + 汇编器遗留收口」；建 **21 份任务书**（spec 4 / infra 2 / llvm 8 / qemu 2 / testcases 3 / integ 2）+ 依赖/串行链（LLVM 链 `050→…→056` 严格串行、`QEMU-042t` 可并行、`INTEG-016t` 最后）。据 `ADR-0019`（reloc：RELA/`ABS48`/`REL26/20/14`/无 −4/禁用 relaxation）、`ADR-0013 D11`（伪指令留 8 删 10）、`Process-05`（TDD）；链接脚本 `dadao.lds` 依 `ADR-0004`；reloc/fixup 坑预防 5 条入约束。**用户裁定**：`SPEC-106t` 全 spec 范围删被删伪指令定义；TESTCASES 向量+独立 oracle 暂不接门控。**验证**：reviewer 核验 21 任务书完整性/一致性/自包含/依赖链（Accepted）；`check-no-residue` EXIT=0。**待裁定**：`SPEC-107t` 的 `ADR-0004` 调整、TESTCASES 落点长期性、`SPEC-106t` 投影表。 | architect + reviewer |
