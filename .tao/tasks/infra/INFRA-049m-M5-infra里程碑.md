# INFRA-049m: M5 infra 里程碑

**模块**：infra
**项目里程碑**：M5
**状态**：待开始
**目标**：基础设施支持 M5——① **install 落地**（`ADR-0016 D1–D11`）：host 工具链 → `.dadao/cross-toolchain`、target sysroot → `.dadao/dadao-unknown-elf`、单一真源定位（`D7/D8`）、**门控/执行器改从 install 根取可执行**、`.work/` 仅作 build 区、保留「从源码可重建」；② **生成物落点迁移**：`test-codegen`/`test-elf`/lit `test_exec_root` → `.dadao/tests/`（`.work/log`/`.work/evidence` 不动）；`test-codegen` 15/15、`test-elf` 5/5 不回归。
**关联任务**：`INFRA-047t`、`INFRA-048t`（2 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`Makefile` install 目标、`.dadao/cross-toolchain/bin/{llvm-mc,llvm-objdump,FileCheck,not,llc,ld.lld,qemu-system-dadao}`、`.dadao/dadao-unknown-elf/{include,lib}`；`Makefile`/`tools/integ/run_*_e2e.py`/`lit.cfg.py` 落点指向 `.dadao/tests/`
- `make install-host` EXIT=0；门控/执行器不再取自 `.work/build`（`grep` 证据）；删 install 根后可重建
- `make test-codegen` 15/15、`make test-elf` 5/5、`make check` EXIT=0
- 落点：`.dadao/tests/{codegen-e2e,elf-e2e,lit-output/<name>}` 有产物；`.work/log`/`.work/evidence` 未迁移
- 假绿守卫：install 根可执行改名 ⇒ 门控非零 ⇒ 还原回绿
- `make check-no-residue` 干净；`git status` 仅应有改动

## 核验记录（主会话）

（核验命令、输出与退出码；结论）
