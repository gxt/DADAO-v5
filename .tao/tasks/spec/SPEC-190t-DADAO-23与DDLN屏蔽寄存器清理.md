# SPEC-190t: DADAO-23 与 DDLN 屏蔽寄存器旧引用清理

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-188t`（已验证；5 个无效屏蔽寄存器定义已删）、`SPEC-189t`（跨节原因表同步；同改 spec 锁，须串行）
**状态**：待开始

## 执行环境
本地；只改 DADAO-23 与 DDLN 的旧屏蔽寄存器引用，不改语义结论、不改实现。

## 背景

`SPEC-188t` 已删除 5 个无效屏蔽寄存器，但仍有旧引用：

- `spec/DADAO-23-HBI-超管系统二进制接口.md` §3：
  - `inner_cfx_mask` 初始化/移交（约 25/53/71/72 行）
  - `<mode>_switch_cfx_mask`（约 40 行）
  - `excp_prev_cfx_mask`（约 51/71 行）
- `docs/DDLN/C-资源管理/{DD-C002,DD-C003,TT-C002,TT-C003}`：
  - `switch_cfx_mask`、`excp_prev_cfx_mask`、`excp_cause_nonmaskable` 仍按旧模型解释

这些与 A/A1 模型冲突：

- 同步异常不可屏蔽
- 异步中断先入当前 monitor，按 `cfx_intr_mask` + `global_cfx_intr_mask` 过滤，屏蔽置 `excp_pending`
- `escape` 不再恢复 `excp_prev_cfx_mask`；`global_cfx_intr_mask` 保留
- `switch_cfx_mask`/`inner_cfx_mask` 不存在

## 目标

1. `DADAO-23 §3` 的 HBI 启动/移交初始化改为 A/A1：
   - 不再初始化 `inner_cfx_mask`/`switch_cfx_mask`/`excp_prev_cfx_mask`
   - 初始化 monitor 的 `cfx_intr_mask`/`global_cfx_intr_mask`（按需要）
   - 移交后 `inner_run_mode`/`inner_cfx_code` 保留；不再设置无意义 mask
   - `escape` 不再恢复 prev mask；`global_cfx_intr_mask` 的 trap 保存/escape 恢复保留
2. DDLN 四册的旧解释同步为 A/A1；只改说明，不改技术结论。
3. 同笔重算 `manifests/spec-readonly.lock.toml` 的 `dadao-23` sha（若 DADAO-23 在锁内）；其它册不变。
4. 不改 QEMU/gem5/tests；实现同步另立任务。

## 接口规范

- DADAO-23：保留 §3 结构/标题；只改初始化与移交句；不新增寄存器。
- DDLN：保留问答结构；把旧 mask 名称替换为现行模型；不得把 DDLN 写成规范真源。
- 历史段/变更记录不改；DADAO-23 追加一条变更记录（无任务号/ADR/ISS）。
- 锁：仅 `dadao-23` 块（若锁含该册）；`docs/` 不入 spec 锁。

## 范围 / 非范围

**在范围内**：`spec/DADAO-23-HBI-超管系统二进制接口.md`（仅 §3 + 变更记录）、`docs/DDLN/C-资源管理/{DD-C002,DD-C003,TT-C002,TT-C003}.md`、`manifests/spec-readonly.lock.toml`、本任务书、`milestones.md`。

**不在范围内**：QEMU/gem5/tests、`contracts/**`、`.tao/contracts/**`、`DADAO-12/13/22/Machine-v5`（已由 186t/188t/189t 处理）、`DADAO-23` 其它章节。

## 验收标准

1. **引用清零**：`inner_cfx_mask`/`switch_cfx_mask`/`excp_prev_cfx_mask` 在 DADAO-23 活文件与 DDLN 四册 0 命中（历史/变更记录除外）。
2. **A/A1 一致**：DADAO-23 初始化/移交不再设置无效 mask；`cfx_intr_mask`/`global_cfx_intr_mask` 保留；`escape` 不再恢复 prev mask。
3. **DDLN**：四册解释与现行 spec 一致，不引入新规范结论。
4. **锁**：`dadao-23` sha 与 `sha256sum` 逐字相等（若在锁内）；其它册不变。
5. **门控**：`check-spec-readonly/refs/drift/changelog/numbering/purity/cite-targets/codeblocks`、`check-knowledge-refs`、`check-milestones-fresh`、`make check`（L1）rc=0。
6. **反例可达 FAIL**：把 `switch_cfx_mask` 写回一处 ⇒ 断言 FAIL；`cp`+`md5sum -c` 还原后回绿。
7. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- DDLN 是“给别人看”的讲义层，不是规范真源；同步以 spec 为准。
- 若 DADAO-23 §3 的初始化语义需要新增/变更寄存器，先留问，不自行扩。
- 实现（QEMU/gem5/tests）由后续任务处理；本任务只清文档/规范引用。

## 未决（下发前确认）

1. DDLN 四册是否全部纳入，还是只改直接引用 `switch_cfx_mask`/`excp_prev_cfx_mask` 的两册；默认四册全改。
2. DADAO-23 §3 初始化是否需要新增 monitor `cfx_intr_mask` 初始化值；默认只删无效 mask，不新增语义。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
