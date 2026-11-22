# m16-spec-002: CACHE-27 补 `cache-model` 维度

**模块**：spec
**项目里程碑**：M16
**依赖**：`m16-spec-001`（cfx5 契约）已合入
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（用户 2026-11-22 已认可契约变更）

用户裁定：Linux 内核缺省带 cache 维护逻辑（其它 ISA 不会为“无 cache”单独编译内核），机器配置只决定 cfx5 有没有效果，不决定它是否存在。

- `cache-model=off`：cfx5 **存在但 no-op**——`cache_exist` 读 0，`cache_ctrl` 写被接受、不报 `CFXREG`、不产生效果；
- `cache-model=on`：`cache_exist=0b11`，命令真维护；
- RTL Vast 始终有 cfx5，Tiny 无（不跑 Linux）。

当前 `contracts/contract-cache.md` 的 CACHE-27 未写这个机器维度，需要补。

## 要做

1. `contracts/contract-cache.md`：在 CACHE-27（cfx5 寄存器/命令语义）处补 `cache-model` 维度：
   - `off`：cfx5 存在；`cache_exist` 读 0；`cache_enable`/`cache_ctrl`/`cache_addr_start`/`cache_addr_size` 可访问但无效果；`cache_ctrl` 合法编码不报异常、不产生维护动作；
   - `on`：`cache_exist=0b11`；寄存器与命令按 CACHE-03…CACHE-27 生效；
   - 其他机器维度（若有）不在此展开。
2. 同步 `contract-cache` 的索引/引用（如有 `CACHE-nn` 清单），不升版本号（用户未要求）。
3. 给出需要同步的探针清单：`integ042t cfx5_cache_cfxreg` 的期望要从 `CFXREG` 改为 no-op；由 `m16-qemu-001` 返工同步，不在本任务改探针。

## 不做

- 不改 QEMU/gem5/RTL 实现；
- 不改 `integ042t`（由 qemu-001 返工）；
- 不升 `spec/`/contracts 版本号。

## 约束

- 独立 `git worktree`；**不提交 git**；
- 变更集限 `contracts/contract-cache.md`、本任务书；
- 术语「寄存器组」；不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. `git diff` 只含 `contracts/contract-cache.md` 与本任务书；CACHE-27 新增段落包含 `cache-model=off` 与 `on` 两个分支；
2. `make check-contracts-*`（现场确认目标名）与 `check-spec-refs`、`check-knowledge-refs` 记录 rc；
3. **可达 FAIL**：删掉 `off` 分支 ⇒ 引用/断言检查红；`cp`+md5 还原后回绿；
4. 不升版本号：`git diff` 无版本号变化。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
