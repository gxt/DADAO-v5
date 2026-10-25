# QEMU-074t: `cmp.{ut,uw,ub}` 结果去掉零扩展（ADR-0037）

**模块**：qemu
**项目里程碑**：M10
**依赖**：SPEC-173t（语义已定）、ADR-0037
**状态**：待开始

## 执行环境
**执行环境**：本地（需增量重建 qemu）

## 接口规范

### 背景（ADR-0037）
- `trans_cmp_{ut,uw,ub}` 在 `gen_cmp_three_way`（已给 i64 -1/0/1）之后又做 `ext32u/ext16u/ext8u(result)` ⇒ `cmp.ut(-1)` = `0x00000000FFFFFFFF`，`br.n` 判负失效。
- 新语义：`-1 = 0xFFFF_FFFF_FFFF_FFFF`；`0/1` 不变；源操作数仍按 width 截断。

### 输入
- `components/qemu/patches/target/dadao/insn_trans/trans_compare.c.inc.patch`
- 现有语义测试/向量（`tests/vectors/isa/reg-compare.yaml` 由 TESTCASES-065t 同步）

### 输出
1. `cmp.ut` / `cmp.uw` / `cmp.ub` 删除结果零扩展（保留源截断与 `gen_cmp_three_way`）；
2. 补/改 QEMU 语义测试：`cmp.ut(0xA,0x14) ⇒ rd = 0xFFFFFFFFFFFFFFFF`，且 `br.n` 命中；
3. 不改 `cmp.st/sw/sb`、不改 `cmp.uo/so`。

### 约束
- 只改上述补丁 + 测试；不改 spec/（SPEC-173t 负责）。
- 若 qemu 增量重建 >10 分钟，停下报主会话。

## 验收标准
1. 重建后 `cmp.ut/uw/ub` 的 -1 结果 = 全 1（贴运行输出）。
2. `cmp.ut → br.n` 用例：分支命中（贴 guest 退出码）。
3. 反例注入（恢复零扩展）⇒ 上述用例失败 ⇒ `cp` 还原 ⇒ 绿。
4. L1 / L2 绿（含 qemu smoke / semantics 相关集）。
5. 完成区贴真实输出与退出码。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
