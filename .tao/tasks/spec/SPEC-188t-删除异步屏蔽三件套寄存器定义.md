# SPEC-188t: 删除异步屏蔽三件套寄存器定义

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-186t`（A/A1 使用模型：monitor 用 `cfx_intr_mask` + `excp_pending`）；`INTEG-053t`（cfxha 新号）
**状态**：待开始

## 执行环境
本地；只改 SPEC/合约中的寄存器定义，不改 QEMU/gem5/tests 实现。

## 背景

`SPEC-186t` 已定 A1：

- 删除 `inner_cfx_mask`（内部）
- 删除 `switch_cfx_mask`（cg0–3 rc9）
- 删除 `excp_prev_cfx_mask`（cg5 rc1）
- monitor 用自己的 `cfx_intr_mask`（cg0–3 rc4）过滤异步来源，用 `excp_pending`（cg5 rc5）保存屏蔽期间事件
- `escape` 不再恢复 mask

但这些寄存器的**定义**仍散落在：

- `DADAO-12 §3.1–3.4`：`<mode>_switch_cfx_mask`（rc9）
- `DADAO-12 §3.6`：`excp_prev_cfx_mask`（cg5 rc1）
- `DADAO-13`：hypv 模式对应行
- `Machine-v5`、`contracts`、`.tao/contracts`：寄存器投影/访问行为
- `DADAO-12 §1`：`inner_cfx_mask` 注记（186t 已改，本任务复核）

## 目标

1. 删除三件套的**语义定义**，不重排 `cg/rc`：
   - `cg0`–`cg3` `rc9` 标 `reserved`（不再定义 `switch_cfx_mask`）
   - `cg5` `rc1` 标 `reserved`（不再定义 `excp_prev_cfx_mask`）
   - `inner_cfx_mask` 从内部寄存器描述中删除
   - 访问 reserved 寄存器 ⇒ `CFXREG`（沿用现有 reserved 规则）
2. `escape` 文本删除“恢复 `excp_prev_cfx_mask`”与“恢复 mask”的表述；只恢复运行模式、cause 等必要现场。
3. 同步 `DADAO-13` hypv 行、`Machine-v5` 与 contracts 投影；`cfx_intr_mask`（rc4）与 `excp_pending`（cg5 rc5）保留，作为 monitor 的异步来源表/pending。
4. 同笔重算 `manifests/spec-readonly.lock.toml` 的 `dadao-12`/`dadao-13`/`machine-v5` sha；其它册不变。
5. 登记后续实现任务（QEMU/gem5/tests）的范围，不在本任务改实现。

## 接口规范

### 1. `DADAO-12`

- §3.1–3.4：删除 rc9 行或改为 `rc9 reserved`（推荐后者，保留编号；访问 ⇒ `CFXREG`）。不重排 rc8/rc10。
- §3.6：`cg5 rc1` 改为 `reserved`；删除 `excp_prev_cfx_mask` 说明。
- §1：`inner_*` 注记删除 `inner_cfx_mask`；如仍出现，改为“A1 下不存在”。
- §5.1/§5.3：`escape` 文本删除 mask 恢复；`cfx_intr_mask`/`excp_pending` 保留。
- 历史段不改；变更记录追加一条（无任务号/ADR/ISS）。

### 2. `DADAO-13`

- hypv 模式 rc9 行改 `reserved`；cg5 rc1 同步；不改其它 HEE 语义。
- 变更记录追加一条。

### 3. `Machine-v5` / contracts

- 删除对三件套的寄存器名/行为投影；`cfx_intr_mask`/`excp_pending` 保留。
- reserved 访问按 `CFXREG`；不新增寄存器。

### 4. 锁

- 仅 `dadao-12`/`dadao-13`/`machine-v5` 重算；注记含日期 + 授权原话指针 + 改动摘要。

## 范围 / 非范围

**在范围内**：`spec/DADAO-12-*`、`spec/DADAO-13-*`、`spec/Machine-v5-*`、`.tao/contracts/**`（仅寄存器投影）、`manifests/spec-readonly.lock.toml`、本任务书、`milestones.md`。

**不在范围内**：QEMU/gem5 实现、`tests/**`、`contracts/` 机器数据（若需同步另立）、`Makefile`、门控脚本、`DADAO-22` 其它语义。

## 验收标准

1. **活文件清零**：`switch_cfx_mask`、`excp_prev_cfx_mask`、`inner_cfx_mask` 在 `DADAO-12/13/Machine-v5/contracts` 活文件 0 命中（历史段/变更记录除外）。
2. **reserved 行为**：rc9/cg5 rc1 标 `reserved`；访问 ⇒ `CFXREG`；`escape` 文本无 mask 恢复。
3. **保留项**：`cfx_intr_mask`（cg0–3 rc4）与 `excp_pending`（cg5 rc5）仍定义，作为 monitor 异步来源/pending。
4. **跨册一致**：DADAO-12/13/Machine-v5/contracts 对同一 rc/cg 的描述一致；锁 sha 与 `sha256sum` 逐字相等，仅三册变化。
5. **门控**：`check-spec-readonly/refs/drift/changelog/numbering/purity/cite-targets/codeblocks`、`check-contracts-dir`、`check-contract-relocs`、`check-issues`、`check-milestones-fresh`、`make check`（L1）rc=0。
6. **反例可达 FAIL**：把 `switch_cfx_mask` 写回一处 ⇒ 断言 FAIL；`cp`+`md5sum -c` 还原后回绿。
7. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- 本任务只做 SPEC/合约定义删除；QEMU/gem5/tests 的寄存器访问、`escape` 恢复、测试期望需另立实现任务（建议 QEMU/GEM5/TESTCASES 各一），并引用本任务定稿。
- `switch_cfx_mask`/`excp_prev_cfx_mask` 用 `reserved` 而非删号，避免 rc 重排波及 decode/contracts。
- 若发现 reserved 访问在现有 spec 中不是 `CFXREG`，先留问，不自行改语义。

## 未决（下发前确认）

1. `rc9`/`cg5 rc1` 是标 `reserved` 还是彻底删行；默认 `reserved`。
2. contracts 机器数据（`contracts/`）是否同笔同步；默认只改 `.tao/contracts` 人读投影，机器数据另立。
3. 后续 QEMU/gem5/tests 任务是否同批创建；默认本任务完成后按实际影响创建。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
