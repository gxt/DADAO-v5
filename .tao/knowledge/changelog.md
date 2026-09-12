# Changelog

任务对仓库代码的实质改动记录（由 `/complete` 追加）。

| 日期 | 描述 | 执行方 |
| --- | --- | --- |
| 2026-09-12 | INFRA-002t：建立仓库骨架（`.gitignore`、`components/`/`scripts/`/`containers/` 骨架、`docs/repository-layout.md`） | engineer |
| 2026-09-12 | INFRA-003t：manifest 系统（`manifests/components.lock.toml`、`manifests/references.lock.toml`、`scripts/manifest_check.py`） | engineer |
| 2026-09-12 | INFRA-004t：组件获取与打补丁工具（`scripts/fetch.py`、`apply_series.py`、`make_patch.py`、`fetch_refs.py`；`.cache/` 持久 bare mirror + `.work/` 可再生工作树） | engineer |
| 2026-09-12 | INFRA-005t：环境与状态工具（`scripts/doctor.py`、`status.py`、`clean_work.py`；clean_work 保护 `.cache/`） | engineer |
| 2026-09-12 | INFRA-006t：顶层 `Makefile` 编排（help/manifest-check/doctor/status/fetch/apply-series/prepare/build-*/docker-*/check；build stub 不假装成功） | engineer |
| 2026-09-12 | INFRA-007t：开发容器 `containers/dev/Dockerfile`（ubuntu:24.04 + LLVM/QEMU/gem5 依赖 + clang；容器内 `make doctor` 报 native） | engineer |
| 2026-09-12 | INFRA-008t：补 v5 自身 ADR（`adr-0001-greenfield-rebuild.md`、`adr-0002-build-orchestration.md`，含 `.cache/` mirror 决策；改 5 文件引用） | engineer |
