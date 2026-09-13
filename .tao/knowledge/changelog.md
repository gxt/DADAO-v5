# Changelog

任务对仓库代码的实质改动记录（由 `/complete` 追加）。

| 日期 | 描述 | 执行方 |
| --- | --- | --- |
| 2026-09-12 | INFRA-002t：建立仓库骨架（`.gitignore`、`components/`/`scripts/`/`containers/` 骨架、`docs/repository-layout.md`） | engineer |
| 2026-09-12 | INFRA-003t：manifest 系统（`manifests/components.lock.toml`、`manifests/references.lock.toml`、`scripts/manifest_check.py`） | engineer |
| 2026-09-12 | INFRA-004t：组件获取与打补丁工具（`scripts/fetch.py`、`apply_series.py`、`make_patch.py`、`fetch_refs.py`；`.cache/` 持久 bare mirror + `.work/` 可再生工作树） | engineer |
| 2026-09-12 | INFRA-005t：环境与状态工具（`scripts/doctor.py`、`status.py`、`clean_work.py`；clean_work 保护 `.cache/`） | engineer |
| 2026-09-12 | INFRA-006t：顶层 `Makefile` 编排（help/manifest-check/doctor/status/fetch/apply-series/prepare/build-*/docker-*/check；build stub 不假装成功） | engineer |
| 2026-09-12 | INFRA-007t：开发容器 `containers/dev/Dockerfile`（ubuntu:24.04 + LLVM/QEMU 依赖 + clang，M1 scope 不含 gem5；容器内 `make doctor` 报 native） | engineer |
| 2026-09-12 | INFRA-008t：补 v5 自身 ADR（`adr-0001-greenfield-rebuild.md`、`adr-0002-build-orchestration.md`，含 `.cache/` mirror 决策；改 5 文件引用） | engineer |
| 2026-09-12 | SPEC-002t：ISA 规范合约按 M1 范围重新生成（`contract-isa.md`；**RA 进 M1**，浮点 RF/特权/原子 Excluded） | engineer |
| 2026-09-12 | SPEC-003t：编码表按 M1 范围重生成（`verif/opcodes.yaml`：M1 178 + `excluded_m1` 78；修正旧版 2 处 ha 错误 + 5 条块赋值 legality 字段） | engineer |
| 2026-09-12 | SPEC-004t：ABI 合约收窄到 M1 最小事实（`contract-abi.md` + `verif/abi.yaml`；完整调用约定 `Deferred to M2`） | engineer |
| 2026-09-12 | SPEC-005t：Object ABI ADR-0003（M1：ELF 头字段 + 段/流水线；重定位 `Deferred to M2`） | engineer |
| 2026-09-13 | SPEC-005t 修订：ADR-0003 `e_flags` 由 1 位标志改为 bits0–7 版本字段（M1=1，bits8–31 保留） | engineer |
| 2026-09-13 | SPEC-006t：Test Machine ADR-0004（内存映射/复位值/exit port/异常可观测，D1–D6 冻结；Status=Candidate） | engineer |
| 2026-09-13 | ADR-0004 重判修订：D1 改核内地址空间模型（ROM `0xffff_ffff_0000`/RAM `0xffff_0000_0000` 16MiB/Exit `0xffff_8000_0000`）、D5 fault 码改 spec cause 派生（ILLI `0x88`…IALIGN `0x8D`，unmapped `0x87`）、D3 harness 超时兜底、D6 示例修正；同步下游任务书 QEMU-003t/VERIF-004t/VERIF-010t/TESTSUITE-006t/008t | architect |
| 2026-09-13 | SPEC-006t 返工复验：ADR-0004 修订后重开验收（更新验收脚本至 109/109 PASS；reviewer+architect 双模型 Accepted；ADR 修正 D6.4 距离与状态说明两处），任务置 `已验证` | architect |
