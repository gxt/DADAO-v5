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
| 2026-09-12 | SPEC-003t：编码表按 M1 范围重生成（`contracts/opcodes.yaml`：M1 178 + `excluded_m1` 78；修正旧版 2 处 ha 错误 + 5 条块赋值 legality 字段） | engineer |
| 2026-09-12 | SPEC-004t：ABI 合约收窄到 M1 最小事实（`contract-abi.md` + `contracts/abi.yaml`；完整调用约定 `Deferred to M2`） | engineer |
| 2026-09-12 | SPEC-005t：Object ABI ADR-0003（M1：ELF 头字段 + 段/流水线；重定位 `Deferred to M2`） | engineer |
| 2026-09-13 | SPEC-005t 修订：ADR-0003 `e_flags` 由 1 位标志改为 bits0–7 版本字段（M1=1，bits8–31 保留） | engineer |
| 2026-09-13 | SPEC-006t：Test Machine ADR-0004（内存映射/复位值/exit port/异常可观测，D1–D6 冻结；Status=Candidate） | engineer |
| 2026-09-13 | ADR-0004 重判修订：D1 改核内地址空间模型（ROM `0xffff_ffff_0000`/RAM `0xffff_0000_0000` 16MiB/Exit `0xffff_8000_0000`）、D5 fault 码改 spec cause 派生（ILLI `0x88`…IALIGN `0x8D`，unmapped `0x87`）、D3 harness 超时兜底、D6 示例修正；同步下游任务书 QEMU-003t/QEMU-015t/INTEG-002t/TESTCASES-006t/008t | architect |
| 2026-09-13 | SPEC-006t 返工复验：ADR-0004 修订后重开验收（更新验收脚本至 109/109 PASS；reviewer+architect 双模型 Accepted；ADR 修正 D6.4 距离与状态说明两处），任务置 `已验证` | architect |
| 2026-09-14 | ADR-0003 rev. 2026-09-14：D2 登记补充（绝对地址并入「绝对 64-bit 数据地址」、不单列 wyde 地址构造场景；相对分支/call/jump `<<2`、有效范围=位宽+2；`rela.si` `<<12`、4KB 对齐、与页无关、无 `<<2`） | architect |
| 2026-09-14 | SPEC-007t：ELF 合约（`.tao/knowledge/contract-elf.md`；§1 头字段 + §5 段对齐/VA=PA + §6 pipeline；§2/§3/§4 重定位 `Deferred to M2`） | engineer |
| 2026-09-14 | 模块重划：`verif` 解散——通用 CI 检查→`infra`（`INFRA-010t` issue registry/`INFRA-011t` spec 引用审计/`INFRA-012t` drift）、验证依据→`spec`（`SPEC-008t` legality/`SPEC-009t` QFC）、组件自测→`qemu`（`QEMU-014t`~`019t` harness×5+trans lint）/`llvm`（`LLVM-012t` lit oracle）、集成→新模块 `integ`（`INTEG-002t` E2E/`INTEG-003t` 接口对齐）；目录 `verif/`→`contracts/`（数据）+`tools/<module>/`（脚本）、`scripts/`→`tools/infra/`；里程碑顺延（`INFRA-013m`/`SPEC-011m`/`LLVM-013m`/`QEMU-020m`/`INTEG-004m`） | architect |
| 2026-09-14 | SPEC-008t 重做+返工：`contracts/legality_rules.yaml` 重新生成（增补 RA 规则；删除 `ra0_no_exception`——ra0 可读写无异常；fault 枚举限定 6 值 `ILLI/UNDI/MALIGN/IALIGN/RASOF/RASUF`；对齐 `legality` 字段引用；修正 `spec_cite` 重复键/行号与 RF/LR/CFX 规则状态） | engineer |
| 2026-09-14 | SPEC-009t：QFC 覆盖校验（`tools/spec/check_qfc_coverage.py`；QFC 表 ↔ `contracts/opcodes.yaml` 双向比对，256/256 差异 0，只读 informational） | engineer |
| 2026-09-14 | SPEC-010t：Spec 冻结（`docs/impact-matrix.md` 逐节覆盖 + `README.md` 冻结状态标 `已冻结`）；`contract-elf.md` Status → Accepted | engineer |
