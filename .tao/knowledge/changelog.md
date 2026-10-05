# Changelog

任务对仓库代码的实质改动记录（由 `/complete` 追加）。

> **M1 归档指针（2026-10-03）**：2026-09-22 及之前的 89 条 M1 条目已归档至 `.tao/archive/M1/README.md`（历史指针，不再在此追加）。

> **M2 归档指针（2026-10-04）**：2026-09-23 ~ 2026-10-04 的 61 条 M2 条目已归档至 `.tao/archive/M2/README.md`（历史指针，不再在此追加）。

> **M3 归档指针（2026-10-05）**：2026-10-05 的 35 条 M3 条目已归档至 `.tao/archive/M3/README.md`（历史指针，不再在此追加）。

| 日期 | 描述 | 执行方 |
| --- | --- | --- |
| 2026-10-06 | **`SPEC-104k`：M4 启动与分解**。M4 = 「ELF 文件支持 + LLD 链接 + 汇编器遗留收口」；建 **21 份任务书**（spec 4 / infra 2 / llvm 8 / qemu 2 / testcases 3 / integ 2）+ 依赖/串行链（LLVM 链 `050→…→056` 严格串行、`QEMU-042t` 可并行、`INTEG-016t` 最后）。据 `ADR-0019`（reloc：RELA/`ABS48`/`REL26/20/14`/无 −4/禁用 relaxation）、`ADR-0013 D11`（伪指令留 8 删 10）、`Process-05`（TDD）；链接脚本 `dadao.lds` 依 `ADR-0004`；reloc/fixup 坑预防 5 条入约束。**用户裁定**：`SPEC-106t` 全 spec 范围删被删伪指令定义；TESTCASES 向量+独立 oracle 暂不接门控。**验证**：reviewer 核验 21 任务书完整性/一致性/自包含/依赖链（Accepted）；`check-no-residue` EXIT=0。**待裁定**：`SPEC-107t` 的 `ADR-0004` 调整、TESTCASES 落点长期性、`SPEC-106t` 投影表。 | architect + reviewer |
