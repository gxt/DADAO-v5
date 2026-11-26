# m20-infra-002: cfx 生成器与门控迁移

**模块**：infra
**项目里程碑**：M20
**依赖**：`m20-spec-002`（别名/契约冻结）；M16/M17 收口后派发
**可并行分片**：否（工具/生成器单写者）
**预估**：2–4 h
**档位**：中改
**状态**：待开始

## 背景

`m20-spec-001` 的 cfx 重排会改变 cfx 别名、opcodes/legality 投影、case-ledger、签名与检查脚本。本任务维护 `tools/`/门控的生成器与迁移工具；不改 spec/引擎。

## 范围

- `tools/infra/`、`tools/spec/`、`tools/testcases/` 中 cfx 别名/opcodes/legality/ledger/signature 的生成器与检查器；
- 生成物/门控的版本与输出路径；迁移脚本/索引（如需要）；
- `Makefile` 中仅与这些生成器相关的门控接线（不改其它目标）。

## 验收

1. 生成器从新契约生成 cfx 别名/opcodes/legality/ledger/signature，结果可复现（重复生成 md5 不变）。
2. 相关 L1/L2 门控真 rc；生成物无旧编号/旧名称残留；`check-temp-dirs` 不因本任务新增残留。
3. 至少一条可达 FAIL（旧输入/旧别名注入 ⇒ 红；`cp`+md5 还原后回绿）。
4. 证据落运行期证据目录内 `run.sh`。

## 约束

独立 worktree（分支 = `m20-infra-002`）；不提交 git；不改 `spec/` 正文、引擎、内核；`Makefile` 只做最小接线。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
