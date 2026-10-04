# SPEC-099m: M3 spec 里程碑

**模块**：spec
**项目里程碑**：M3
**状态**：待开始
**目标**：v5 标量调用约定合约落地——`contract-abi.md` §4 由 `Deferred to M2` 变为正文（参数寄存器/返回值/callee-save/帧布局/prologue-epilogue），`contracts/abi.yaml` 同步扩展，为 M3 CodeGen 提供稳定期望值来源。
**关联任务**：`SPEC-097t`（1 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`.tao/knowledge/contract-abi.md`（§4 正文）、`contracts/abi.yaml`（新增字段）
- `contract-abi.md` 每条规范句有 spec 来源标注；`contracts/abi.yaml` YAML 解析通过且与正文一致；`make check` 全绿
- M3 取舍项（帧指针策略/栈对齐/窄返回扩展等，C1–C17）已由 `project_M3-codegen-choices.md §5` 判定固化（`ADR-0018`）；`SPEC-097t` 按判定落地，未擅自选边

## 核验记录
（核验时由主会话/架构师填写：命令原样 + 退出码）
