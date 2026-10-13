# INFRA-049m: M5 infra 里程碑

**模块**：infra
**项目里程碑**：M5
**状态**：里程碑
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

**M5 infra 里程碑核验（2026-10-08，architect 代主会话）**　**判决：满足，置 `里程碑`**

证据来源（既有日志，未重跑 `make`）：`.work/log/infra/INFRA-047t-*.log`、`.work/log/infra/INFRA-048t-*.log`、`.work/evidence/INFRA-047t/`、`.work/evidence/INFRA-048t/`；独立只读复核（`ls`/`grep`/`git status`/`check_patch_tree.py --source-state`/`check_dirs.py --residue`）。

| # | 核验项 | 证据（真实） | 结论 |
| --- | --- | --- | --- |
| 1 | 关联任务均 `已验证` | `INFRA-047t`/`INFRA-048t` 头部 `**状态**：已验证` | ✅ |
| 2 | 产出：`Makefile` install 目标 | `Makefile:273 install-host: build-mc build-lld build-qemu` | ✅ |
| 3 | 产出：`.dadao/cross-toolchain/bin/{llvm-mc,llvm-objdump,FileCheck,not,llc,ld.lld,qemu-system-dadao}` | `ls` 实到：`FileCheck ld.lld llc lld llvm-lit llvm-mc llvm-objcopy llvm-objdump llvm-readobj not qemu-system-dadao`（含全部点名项） | ✅ |
| 4 | 产出：`.dadao/dadao-unknown-elf/{include,lib}` | `ls -la .dadao/dadao-unknown-elf/` → `include/`、`lib/`、`README.md` | ✅ |
| 5 | `make install-host` EXIT=0；删 install 根后可重建 | `INFRA-047t-acc1-install-host.log` 末 `install-host: PASS`；`INFRA-047t-acc4-rebuild.log` 末 `install-host: PASS` | ✅ |
| 6 | 门控/执行器不再取自 `.work/build`（`grep`） | `Makefile:409/423-426` 皆 `$(HOST_TOOLCHAIN_BIN)/…`（`paths.py` 解析，无硬编码）；`INFRA-047t-evidence-run.log`：`run_qemu_test DEFAULT_QEMU` 在 install 根、`free of .work/build`=match；`run_{codegen,elf}_e2e.py` `DEFAULT_*` 同 | ✅ |
| 7 | 落点：`.dadao/tests/{codegen-e2e,elf-e2e,lit-output/<name>}` 有产物 | `ls`：`codegen-e2e/`（60 产物）、`elf-e2e/`（16）、`lit-output/{DADAO-MC,DADAO-CodeGen,DADAO-E2E}`；`Makefile:429/462` 均 `$(TEST_ARTIFACTS_DIR)/…` | ✅ |
| 8 | `.work/log`/`.work/evidence` 未迁移 | `.work/log/infra/`、`.work/evidence/INFRA-047t,048t` 均在原处 | ✅ |
| 9 | `make test-codegen` 15/15、`make test-elf` 5/5、`make check` EXIT=0 | `INFRA-047t-evidence-run.log`：test-codegen 15/15 rc=0、test-elf 5/5 rc=0、`make check` rc=0（`repository checks: PASS`） | ✅ |
| 10 | **假绿守卫**（install 根可执行改名 ⇒ 门控非零 ⇒ 还原回绿） | 同 log：改 `llvm-mc` ⇒ `check-lit` 2/62 FAIL（非零）；还原 md5 相符 ⇒ 60/60 回绿；改 `qemu-system-dadao` ⇒ `check-qemu-semantics` FAIL rc=1；还原 ⇒ 149/149 回绿 | ✅ |
| 11 | `make check-no-residue` 干净 | `INFRA-047t-acc7-no-residue.log` PASS；复核 `check_dirs.py --residue` → `check-no-residue: PASS`（rc=0） | ✅ |
| 12 | `git status` 仅应有改动 | 核验时 `git status --porcelain -uall` **空**（干净） | ✅ |

**跨模块影响**：无。`README §模块里程碑与跨模块交互` 所涉 open 项（`ISS-163…169`）无一指向 `infra`；`install` 布局/落点由 `ADR-0016 D1–D11`（`Accepted`）与本模块自身任务收口。**无未处置跨模块项。**

## 审阅记录

#### M5 模块里程碑核验（architect，2026-10-08）

- **核验对象**：`INFRA-049m`（2 关联任务 `INFRA-047t`/`INFRA-048t`）。
- **判决**：**满足 ⇒ `**状态**` 置 `里程碑`**。依据：关联任务全 `已验证`；12 项核验逐条通过（含 `install-host` EXIT=0、删根重建、门控/执行器取自 install 根、三处落点迁移、假绿守卫有鉴别力、`check-no-residue` 干净）；跨模块无影响。
- **边界**：本次仅改本文件（`**状态**` 字段 + `## 核验记录（主会话）` + 本记录）；**`spec/` 交集为空**；未触 `contracts/**`/`components/**`/`Makefile`/`tools/**`；未新增/删除任务。
