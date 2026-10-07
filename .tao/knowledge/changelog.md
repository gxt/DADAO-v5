# Changelog

任务对仓库代码的实质改动记录（由 `/complete` 追加）。

> **M1 归档指针（2026-10-03）**：2026-09-22 及之前的 89 条 M1 条目已归档至 `.tao/archive/M1/README.md`（历史指针，不再在此追加）。

> **M2 归档指针（2026-10-04）**：2026-09-23 ~ 2026-10-04 的 61 条 M2 条目已归档至 `.tao/archive/M2/README.md`（历史指针，不再在此追加）。

> **M3 归档指针（2026-10-05）**：2026-10-05 的 35 条 M3 条目已归档至 `.tao/archive/M3/README.md`（历史指针，不再在此追加）。

> **M4 归档指针（2026-10-07）**：2026-10-06 ~ 2026-10-07 的 28 条 M4 条目已归档至 `.tao/archive/M4/README.md`（历史指针，不再在此追加）。

| 日期 | 描述 | 执行方 |
| --- | --- | --- |
| 2026-10-07 | **`INTEG-018t`：M4 任务书归档与回顾（自归档）**。32 个 M4 任务书 `git mv` 入 `.tao/archive/M4/<模块>/`（30 M4 终态 + `SPEC-111t` 改判 M4 + 自归档）；`README.md`（清单 + 28 条 changelog 摘要 + MEMORY 摘录 + 指针）/`m4-retrospective.md`/`issues-closed.md`（12 条）；台账指针（`milestones.md`/`changelog.md`/`MEMORY.md`/`issues.yaml`）；并订正 `cfcb64d` 引入的 `milestones.md` 断表。`make check`/`check-no-residue` EXIT=0；证据 47 PASS。 | engineer + reviewer |
| 2026-10-07 | **`INFRA-047t`：install 落地（`.dadao/` 安装根 + 门控/执行器改从 install 根取可执行）**。落地 `ADR-0016 D3/D4/D5/D11`：新增 `Makefile:install-host`（只装所需 host 工具集 + lit 自包含 launcher + target sysroot 骨架，**非**全量 `cmake --install`）；`Makefile` 路径变量（`LIT_BIN`/`LLC_BIN`/`LLVM_MC_BIN`/`LLVM_OBJCOPY_BIN`/`QEMU_BIN`/`LLD_BIN`）与 `tools/integ/run_{codegen,elf}_e2e.py`、三个 `tests/**/lit.cfg.py`、`tests/scripts/run_qemu_test.py` 全部改经 `$(HOST_TOOLCHAIN_BIN)` / `tools/infra/paths.py` 取可执行（D7 无硬编码）；`check-qemu-semantics` 增传 `--qemu $(QEMU_BIN)`（D9 点名 `run_qemu_test.py` 在补修轮闭合）。`make check`/`check-lit`(60/60)/`check-qemu-semantics`(149/149)/`test-codegen`(15/15)/`test-elf`(5/5) 全绿；注入反例证门控承重、`.work/` 仍为唯一构建真源（可从源码重建）。 | engineer + reviewer |
