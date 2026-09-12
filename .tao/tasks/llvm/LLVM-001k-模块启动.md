# LLVM-001k: llvm 模块启动

**模块**：llvm
**项目里程碑**：M1
**依赖**：无
**状态**：待开始

## 问题根源

DADAO-v5 基于 SimRISC 0.5.3，需要从零为 `dadao-unknown-elf` 目标构建 LLVM MC 层（汇编器 / 反汇编器 / 编码器 / ELF object emitter），使 `llvm-mc` 能汇编、`llvm-objdump` 能反汇编全部 M1 指令，并输出字节与独立 oracle 一致。当前仓库尚未规划 llvm 模块任务；而 DADAO-0628 的 LLVM 任务基于 SimRISC 0.4.1，其指令命名、QFC 编码表、格式体系与 v5 完全不同，不能照搬其任务中的补丁正文或编码数据。

因此需要先把 0628 的 LLVM MC 任务链（DL-005a…DL-011b、DL-035a）完整转述并按 0.5.3 重新分解，作为 v5 llvm 模块的规划基线。

## 目的

规划 v5 llvm 模块 M1 阶段任务链：从锁定 LLVM 上游基线 → 注册 triple/最小骨架 → 寄存器 TableGen → 指令格式 TableGen → AsmParser+MCCodeEmitter → CodeEmitter 修复+全量 lit → 反汇编器 → lit 字节级 CHECK → 系统指令助记符/smoke 修正 → 里程碑，使 M1 结束时 `llvm-mc` / `llvm-objdump` 能汇编/反汇编全部 M1 标量指令，编码字节与 `.tao/knowledge/contract-isa.md`、`verif/opcodes.yaml` 独立推导的期望值一致，lit 0 failures。

## 对照关系

- **借鉴**：DADAO-0628 LLVM MC 任务链——`DL-005a`（组件基线+ADR-0005+build-mc）、`DL-007a`（triple 注册+最小 build）、`DL-008a`（寄存器 TableGen）、`DL-009a`（指令格式 TableGen）、`DL-010a`（AsmParser+CodeEmitter）、`DL-010b`（CodeEmitter 修复+全量 lit）、`DL-011a`（反汇编器）、`DL-011b`（lit 字节级 CHECK）、`DL-035a`（halt/系统助记符+smoke 修正）；以及其 `components/llvm/patches/series` 的补丁命名与顺序、`tests/lit/MC/Dadao/` 的 lit 组织方式。
- **差异**：
  - 规范版本 0.4.1 → 0.5.3：指令命名使用 `.b/.w/.t/.o` 与 `s`/`u` 后缀；QFC 编码表重组；格式体系引入 MISC-byte/wyde/tetra/octa 子表；`add.si`/`rela.si` 为 riii；新增 `br.z-rb`/`br.nz-rb`、浮点条件赋值等。补丁正文与编码数据必须按 0.5.3 重新生成。
  - oracle 不同：v5 的编码期望值来自 `.tao/knowledge/contract-isa.md`（§1 寄存器、§2 编码、§3–§5 标量、§7 系统）与 `verif/opcodes.yaml`（256 条），而非 0628 的 `contracts/isa/spec.md`。
  - 目录/工具不同：v5 任务在 `.tao/tasks/llvm/`；上游 checkout 落在 `.work/source/llvm`（`INFRA-004t` 约定），构建落在 `.work/build/llvm`；参考锁指向 `.work/DADAO-0628`。
  - 不照抄 0628 的 LLVM commit 作为既定基线；版本由 `LLVM-002t` 的 ADR-0005 独立记录并验证。
  - 路线与参考直接指向 DADAO-0628，不使用任何按“阶段”命名的目录或字段。

## 任务分解

| 编号 | 任务 | 交付物 | 依赖 |
|------|------|--------|------|
| `LLVM-002t` | LLVM 组件基线（commit + ADR-0005 + `build-mc`） | `.tao/knowledge/adr-0005-llvm-baseline.md`、`manifests/components.lock.toml`（llvm enabled+commit）、`Makefile` 真实 `build-mc` | `INFRA-006t` |
| `LLVM-003t` | Triple 注册 + 最小 build | `components/llvm/patches/0001-dadao-triple-registration.patch`、`0002-dadao-target-skeleton.patch`、`series`、最小 lit | `LLVM-002t`、`SPEC-007t` |
| `LLVM-004t` | Register TableGen | `components/llvm/patches/0003-dadao-register-info.patch` | `LLVM-003t`、`SPEC-004t` |
| `LLVM-005t` | 指令格式 TableGen | `components/llvm/patches/0004-dadao-instrinfo.patch` | `LLVM-004t` |
| `LLVM-006t` | AsmParser + MCCodeEmitter | `components/llvm/patches/0005-dadao-asmparser.patch` | `LLVM-005t` |
| `LLVM-007t` | MCCodeEmitter 修复 + 全量 lit | 修订 `0005-dadao-asmparser.patch`、全量 lit 文件 | `LLVM-006t` |
| `LLVM-008t` | 反汇编器 | `components/llvm/patches/0006-dadao-disassembler.patch` | `LLVM-007t` |
| `LLVM-009t` | lit 字节级 CHECK | 13+ 个 `tests/lit/MC/Dadao/*.s` 的 OBJ/ASM 前缀 | `LLVM-008t` |
| `LLVM-010t` | halt 助记符 + smoke `.s` 修正 | 系统指令助记符定义 + smoke `.s` 修正 | `LLVM-009t`、`SPEC-006t` |
| `LLVM-011m` | LLVM MC 里程碑 | 里程碑标记 | `LLVM-002t`~`LLVM-010t` |

- **依赖关系**：`002t → 003t → 004t → 005t → 006t → 007t → 008t → 009t → 010t`；`002t` 依赖 infra 的 `INFRA-006t`（Makefile 编排），`003t` 依赖 `SPEC-007t`（ELF 合约），`004t` 依赖 `SPEC-004t`（ABI 合约），`010t` 依赖 `SPEC-006t`（Test Machine ADR）；`011m` 汇总全部。
- **分解理由**：按「基线 → 骨架 → 寄存器 → 指令格式 → 汇编/编码 → 修复+测试 → 反汇编 → 字节级测试 → 系统指令/冒烟」逐层推进，每层可独立 `git am` 一个补丁并独立验收（`make build-mc` + lit）；补丁序号与 0628 `series` 前 6 项对齐（0001–0006），后续按 0.5.3 需要重新生成。

## 说明

- 只规划不实现；本模块任务文件由工程师按 `## 交付物` 生成补丁与测试，架构师不写补丁正文。
- M1 范围为标量核心（`contract-isa.md` §3 标量整数、§4 地址/内存、§5 控制流、§7 系统指令中测试机所需部分）；浮点 §6 按 M1 范围排除。
- 0628 的 ELF relocation 完善任务（其 `DL-012a`）在本任务集中未单列；本任务集只到反汇编/字节级 lit 与系统指令冒烟。若 M1 需要完整 ELF relocation，另立 `LLVM-012t`（待用户确认）。
- `LLVM-010t` 标题沿用 0628 的 `halt` 命名，但 v5（0.5.3）`contract-isa.md` 无 `halt` 助记符，等价机制为 §7 的 `escape`/`trap` 与 ADR-0004 的 exit port；差异详见该任务。
- 参考：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`、`.work/DADAO-0628/docs/development-roadmap.md`、`.work/DADAO-0628/components/llvm/patches/series`。
