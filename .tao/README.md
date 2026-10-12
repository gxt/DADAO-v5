# .tao — DADAO-v5 交互目录

本目录承载任务、知识与协作记录，由架构师/工程师/审查者角色流程使用。
全局规则见 `~/.config/opencode/AGENTS.md`（自动加载）；**角色 / 流程 / 命令**见项目 `AGENTS.md`「角色与流程」，agent 定义与命令（mode）见 `.opencode/agents/`、`.opencode/commands/`。

## 交互目录 $TAO_ROOT 定位

用 `git rev-parse --show-toplevel` 找到当前仓库根，交互目录即 `$REPO_ROOT/.tao/`。后续所有 `$TAO_ROOT` 均指该目录。

## 目录

- `tasks/<module>/` — 任务文件 `<PREFIX>-nnn<suffix>-描述.md`（按模块分子目录）
- 其余各子目录（`knowledge/`、`adr/`、`archive/<里程碑>/`）的**职责与真源索引**见 `.tao/knowledge/MEMORY.md`「入口指针」（`issues.yaml` = **issue 台账**）
- `archive/<里程碑>/` — **历史归档**（`Process-04` 里程碑归档规范）：任务书按模块子目录（`git mv` 保留 `R`）+ `README.md` + `m<i>-retrospective.md` + `issues-closed.md`；现有 `M1`–`M7`（`M7` 为 2026-10-13 **收尾归档**，项目 M7 达成待裁定）
- **任务收尾自查** — 提交前可跑 `make check-tasks`（报告型，默认退出码 `0`；`--strict` 时命中 >0 则非零）：列出「`## 完成区` 已填但 `**状态**` 仍为 `待验收`」的任务书，用于自查漏 `/complete`；**不并入** `make check` 阻断路径

## 模块与任务编号

任务按模块组织：`tasks/<module>/<PREFIX>-nnn<suffix>-描述.md`，`nnn` 为模块内三位递增序号（跨后缀共享，前缀保证全局唯一）；后缀 `k`=启动 / `t`=普通任务 / `m`=里程碑。规则正文（状态机 / 编号 / 头部字段）真源见 `.opencode/agents/architect.md`。

| 模块 | 前缀 | 交付物 |
| --- | --- | --- |
| `infra` | `INFRA` | 构建基础设施（组件锁、fetch/apply、Makefile、容器） |
| `spec` | `SPEC` | 规范锁定、ISA 合约、编码表、ABI/ELF/SBI 合约 |
| `testcases` | `TESTCASES` | 测试用例：向量（schema/validator）+ benchmark |
| `golden` | `GOLDEN` | Python 黄金模型（**未开工**） |
| `llvm` | `LLVM` | LLVM MC + CodeGen |
| `qemu` | `QEMU` | QEMU |
| `integ` | `INTEG` | 集成验证（E2E 套件与回归 + 跨模块接口对齐） |
| `gem5` | `GEM5` | gem5（**未开工**） |
| `sail` | `SAIL` | Sail（**未开工**） |

**文档三分界**：`spec/`（技术规范正文）/ `docs/`（工程流程规范 + 索引 + `DDLN/`）/ `.tao/knowledge/`（结论·设计·口径）——主判据与落点见 `AGENTS.md`「文档分层与单一真源」。
