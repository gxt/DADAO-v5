# DADAO for SimRISC 0.5.1

## 核心任务

基于 `wiki/` 目录下 11 份规范文档，通过系统性自洽性审查（累计修复 180+ 项缺陷），使文档达到可支撑 LLVM 编译器、QEMU 模拟器、Chipyard 仿真器和 Linux 内核开发的完备程度。

## 最终成果

经过多轮审查，当前 11 份文档零硬缺陷，关键修复包括：

- **指令编码**：brrr/brri 位掩码格式新增、编码表三次重构、所有格式后缀补全、andi/divs-rrrr/divu-rrrr/orii 等删除、命名统一（bitmask→bit position / ww→wpN / phymem→pmem / unimp→illi）
- **异常系统**：IALIGN 新增、FPEXCP 移至 1<<32、异常优先级（IALIGN>ILLI>MALIGN>页表>FPEXCP）、精确异常统一、cfx mask 六类型 per-mode 守卫、步骤 3/4 ILLI 重定向到 monitor
- **寄存器**：pending 统一为 cg5 rc5 excp_pending、timer/uart/power 专有 pending 删除、rd0/rb0 行为 AEE/SimRISC 统一、cg 编号修正
- **SBI**：PTBR/PTHI/PAHI 跳转表 rb3 中转修改、ALLOC_PAGE 返回值统一、ptw handler 四处 TODO 替换实现
- **伪代码**：异常进入步骤 1/3/4/5 语义修正、escape 退出步骤 0 cfx mask 检查、自身 cfxcode 忽略守卫

## 当前版本号

| 组件 | 版本 |
|------|------|
| SimRISC | 0.5.1 |
| AEE / ABI | 0.9.2 |
| SEE / SBI | 0.7.1 |
| HEE / HBI | 0.1.2 |

## 开发下一步

1. **LLVM**：基于 `SimRISC-00` 编码表和 `SimRISC-01~04` 指令定义编写 TableGen `.td` 文件，注意 brrr/brri 格式的 bpN 参数
2. **QEMU**：基于 `SEE §5` 异常流程伪代码实现译码和异常路由，基于 `SBI` 实现各 cfx handler
3. **Chipyard**：基于 `SEE §3-4` 寄存器表逐张实现硬件模块，特别关注 cfx mask 六类型多模式守卫
4. **Linux**：基于 `SBI` 函数表编写内核 SBI 调用包装，基于 `AEE/ABI` 编写用户态库

---

## 仓库映射：DADAO-0628 → DADAO-v5

本仓库的设计参考了 [DADAO-0628](https://github.com/gxt/DADAO-0628)，但目录结构根据 DADAO-v5 的实际情况做了调整。下表列出每个 DADAO-0628 的文件/目录在 DADAO-v5 中的对应位置，以及由哪个阶段生成。

### 根目录文件

| DADAO-0628 | DADAO-v5 对应 | 生成阶段 |
|---|---|---|
| `README.md` | `README.md`（追加本表） | 已有 |
| `Makefile` | `Makefile` | Phase 0 |
| `.gitignore` | `.gitignore` | Phase 0 |
| `CODEX.md` | 拆入 `AGENTS.md` + 角色规则文件 | Phase 0 |
| `DS.md` | `project/rule-subagent.md` | Phase 0 |
| `reviewer.md` | `project/rule-reviewer.md` | Phase 0 |
| — | `AGENTS.md`（精简通用规则） | 已有，Phase 0 更新 |
| — | `project/rule-architect.md`（新增） | Phase 0 |
| — | `project/MEMORY.md`（新增） | Phase 0 |

### manifests/（锁文件，根目录）

| DADAO-0628 | DADAO-v5 对应 | 生成阶段 |
|---|---|---|
| `manifests/spec.lock.toml` | `manifests/spec.lock.toml` | Phase 0 |
| `manifests/components.lock.toml` | `manifests/components.lock.toml` | Phase 0 |
| `manifests/references.toml` | `manifests/references.toml` | Phase 0 |

### contracts/ → project/contracts/（归一化规范）

| DADAO-0628 | DADAO-v5 对应 | 生成阶段 |
|---|---|---|
| `contracts/isa/spec.md` | `project/contracts/isa-spec.md` | Phase 1 |
| `contracts/abi/spec.md` | `project/contracts/abi-spec.md` | Phase 4 |
| `contracts/elf/spec.md` | `project/contracts/elf-spec.md` | Phase 4 |
| `contracts/exception/README.md` | `project/contracts/exception-contract.md` | 推迟 |
| `contracts/mmu/README.md` | `project/contracts/mmu-contract.md` | 推迟 |
| — | `project/contracts/sbi-spec.md`（DADAO-v5 新增） | Phase 4 |

### verif/（验证工具，DADAO-0628 中名为 tools/）

| DADAO-0628 | DADAO-v5 对应 | 生成阶段 |
|---|---|---|
| `tools/opcodes.yaml` | `verif/opcodes.yaml` | Phase 1 |
| `tools/legality_rules.yaml` | `verif/legality_rules.yaml` | Phase 1 |
| `tools/abi.yaml` | `verif/abi.yaml` | Phase 4 |
| `tools/dadao_interp.py` | `verif/dadao_interp.py` | Phase 3 |
| `tools/validate_interp.py` | `verif/validate_interp.py` | Phase 3 |
| `tools/run_differential.py` | `verif/run_differential.py` | Phase 3（骨架）→ Phase 8（完整） |

### scripts/（工具脚本）

| DADAO-0628 | DADAO-v5 对应 | 生成阶段 |
|---|---|---|
| `scripts/doctor.py` | `scripts/doctor.py` | Phase 0 |
| `scripts/manifest_check.py` | `scripts/manifest_check.py` | Phase 0 |
| `scripts/fetch.py` | `scripts/fetch.py` | Phase 0 |
| `scripts/apply_series.py` | `scripts/apply_series.py` | Phase 0 |
| `scripts/status.py` | `scripts/status.py` | Phase 0 |
| `scripts/clean_work.py` | `scripts/clean_work.py` | Phase 0 |
| `scripts/validate_encoding.py` | `scripts/validate_encoding.py` | Phase 1 |
| `scripts/validate_vectors.py` | `scripts/validate_vectors.py` | Phase 2 |
| `scripts/check_wiki_drift.py` | 合并入 `scripts/check_wiki_refs.py` | Phase 1 |
| `scripts/check_wiki_refs.py` | `scripts/check_wiki_refs.py` | Phase 1 |
| `scripts/check_codegen_abi.py` | `scripts/check_codegen_abi.py` | Phase 8 |
| `scripts/check_legality_matrix.py` | `scripts/check_legality_matrix.py` | Phase 8 |
| `scripts/check_qemu_trans.py` | `scripts/check_qemu_trans.py` | Phase 8 |
| `scripts/check_qfc_coverage.py` | `scripts/check_qfc_coverage.py` | Phase 8 |
| `scripts/check_issues.py` | 暂不需要 | — |
| `scripts/check_lit_bytes.py` | `scripts/check_lit_bytes.py` | Phase 8 |

### components/（组件补丁）

| DADAO-0628 | DADAO-v5 对应 | 生成阶段 |
|---|---|---|
| `components/llvm/patches/` | `components/llvm/patches/` | Phase 6 |
| `components/qemu/patches/` | `components/qemu/patches/` | Phase 7 |
| `components/gem5/patches/` | `components/gem5/patches/` | Phase 9 |
| `components/linux/patches/` | `components/linux/patches/` | 推迟 |
| `components/musl/patches/` | `components/musl/patches/` | 推迟 |
| — | `components/chipyard/patches/`（DADAO-v5 新增） | 推迟 |

### sail/（形式化规范，根目录）

| DADAO-0628 | DADAO-v5 对应 | 生成阶段 |
|---|---|---|
| `sail/`（.sail + build.sh + c_harness） | `sail/` | Phase 10 |

### tests/（测试）

| DADAO-0628 | DADAO-v5 对应 | 生成阶段 |
|---|---|---|
| `tests/vectors/`（schema + inventory + isa/*.yaml） | `tests/vectors/` | Phase 2 |
| `tests/e2e/` | `tests/e2e/` | Phase 8 |
| `tests/lit/` | `tests/lit/` | Phase 6（MC）+ Phase 8（E2E） |
| `tests/scripts/`（crt0.s, dadao.ld, 运行器） | `tests/scripts/` | Phase 8 |
| `tests/interface/` | 用到时创建 | — |
| `tests/runtime/` | 用到时创建 | — |

### project/adr/ + project/ 根（架构决策与策略，分散在 project/ 下）

| DADAO-0628 | DADAO-v5 对应 | 生成阶段 |
|---|---|---|
| `docs/adr/`（12 个 ADR） | `project/adr/` | 各阶段 |
| `docs/repository-layout.md` | `project/repository-layout.md` | Phase 0 |
| `docs/definition-of-done.md` | `project/definition-of-done.md` | Phase 0 |
| `docs/architecture-boundaries.md` | `project/architecture-boundaries.md` | Phase 0 |
| `docs/greenfield-charter.md` | `project/greenfield-charter.md` | Phase 0 |
| `docs/development-roadmap.md` | `project/development-roadmap.md` | Phase 0 |
| `docs/test-strategy.md` | `project/test-strategy.md` | Phase 0 |
| `docs/issues.yaml` / `open-spec-issues.md` | 用到时创建 | — |
| 其余阶段性报告 | `project/`，按需创建 | 各阶段 |

### project/（agent 中间文件集中目录）

| DADAO-0628 | DADAO-v5 对应 | 生成阶段 |
|---|---|---|
| `code-agent/tasks/` | `project/tasks/` | 各阶段 |
| `code-agent/designs/` | `project/designs/` | 各阶段 |
| `code-agent/knowledge/` | `project/knowledge/` | 各阶段 |
| `code-agent/reviews/` | `project/reviews/` | 各阶段 |
| `code-agent/README.md` | 信息并入 `project/MEMORY.md` | Phase 0 |
| — | `project/steps/`（阶段执行计划） | 已有 |

### 开发环境

| DADAO-0628 | DADAO-v5 对应 | 生成阶段 |
|---|---|---|
| `containers/dev/Dockerfile` | `containers/Dockerfile` | Phase 5 |
| `.github/workflows/skeleton.yml` | 暂不需要 | — |
