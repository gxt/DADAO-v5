# contracts/ — 机器可读合约数据

从 `.tao/contracts/contract-*.md` 与 ADR 派生的**机器可读合约数据**，供各模块工具与实现消费。**人读契约正文在 `../.tao/contracts/`**（本目录只放机器数据）。

## 文件说明

| 文件 | 内容 | 来源 |
|------|------|------|
| `opcodes.yaml` | 每条指令的编码字段、mask、value、变体 | `contract-isa.md`（`SPEC-003t`）；**生成物**：只由 `tools/spec/generate_opcodes.py` 产出（`make check-opcodes-repro` 逐字节守漂移，禁手改；`ISS-416`） |
| `abi.yaml` | 参数寄存器编号、callee-saved 列表、DataLayout | `contract-abi.md`（`SPEC-004t`） |
| `legality_rules.yaml` | 非法编码组合、非对齐访问规则 | `contract-isa.md` 异常条款（`SPEC-008t`） |
| `fp_semantics.yaml` | FP（`scope: fp`，60 条）语义投影：FCSR 环境、12 族、`id→family→spec_cite→semantics_ref→legality_refs`（不含编码、不含期望值） | `contract-fp.md`（`SPEC-087t`） |
| `linux-boot.yaml` | 启动 ABI 投影：boot info 15 字段（偏移/宽度/`kind`）、内存分区、进入状态、装载规则；与 `Kaiwu §6.3` 逐字段一致 | `contract-linux-boot.md`（`m14-spec-001`） |
| `wuming-cycles.yaml` | **chipyard ↔ gem5 的周期对照源**：263 条指令 → 类 / 周期 / 动态参数（`ld`/`st`/`ldm`/`stm` 分行给值），gem5 时序模型与对标脚手架共用 | `docs/core-wuming-cycle-model.md` + `opcodes.yaml`（`m16-gem5-002`；生成器 `tools/gem5/gen_wuming_cycles.py`，`make check-wuming-cycles` 守漂移） |

## 原则

- **独立于实现**（Independent oracle）：只从 `spec/` 与合约派生，不从 LLVM/QEMU 反推。
- **载体分工**：扁平锁 / 清单 → TOML（如 `manifests/*.toml`）；嵌套合约数据 → YAML（本目录）；叙述型契约正文 → Markdown（`../.tao/contracts/`）。
- `opcodes.yaml` 须自检：每条指令的 mask & value 唯一、同 mnemonic 的变体共享基名、无编码空间重叠（由 `tools/spec/validate_encoding.py`）。
- **工具脚本不放这里**：生成/校验脚本在 `tools/spec/`，各模块检查脚本在 `tools/<module>/`。
- 黄金模型（Python 独立 oracle）属 `golden` 模块（M2），不在此目录。
