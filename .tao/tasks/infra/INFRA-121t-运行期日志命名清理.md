# INFRA-121t: 运行期日志命名清理（check-run-artifacts 7 条既有红）

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-120t`（已验证；任务书运行期路径清零）
**状态**：待开始

## 执行环境
本地；只清理运行期日志，不改仓库跟踪文件、不改门控逻辑。

## 背景

`make check-run-artifacts` 当前报 7 条既有非法命名日志：

- 3 条无任务号/无 `check-` 前缀的通用日志
- 4 条 `GEM5-018t` 旧构建日志使用 `.EXIT`/`.start` 后缀

这些是运行期临时日志，不是源码、不是测试资产；规则只接受 `check-<name>.log` 或 `<TASK-ID>-<purpose>.(log|json|txt)`。

`INFRA-120t` 已把 L1 的 `check-knowledge-refs` 清零；本任务是 L1 最后一个非任务红。

## 任务

1. 以 `make check-run-artifacts` 现场输出为准，确认恰为 7 条。
2. 删除或重命名为合法名称；优先删除旧临时日志，不保留非法命名。
3. 不把文件加入 baseline 豁免，不改 `check-run-artifacts` 规则。
4. 若任务书/知识库引用这些日志，改为“运行期证据已清理，未归档；结果见完成区”的历史说明，不保留具体路径。
5. 重跑 `make check-run-artifacts`、`make check-no-residue`、`make check-milestones-fresh`；确认 L1 不再因该门控失败。

## 验收

- `make check-run-artifacts` rc=0、无 7 条问题；
- 文件被删除或改为合法名，现场 `find`/门控证明无残留；
- 不新增代码/配置/门控改动；
- 完成区 ≤30 行，真实 rc；状态 `待验收`。

## 说明

- 不改 `tools/infra/check_run_artifacts.py`；
- 不改 `.run-artifacts-baseline` 掩盖；
- 不删除有效测试产物；只处理门控列出的 7 条。
