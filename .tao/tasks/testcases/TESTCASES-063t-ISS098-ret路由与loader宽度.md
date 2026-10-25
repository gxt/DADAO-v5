# TESTCASES-063t: harness ret 路由与 loader 宽度推导修复（ISS-098）

**模块**：testcases
**项目里程碑**：M10
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地（无 LLVM 重建；必要时重跑向量）

## 接口规范

### 背景（ISS-098，architect 复核）
- `tests/scripts/build_test_binary.py` 把 `ret` 语义用例路由到 `build_call_ret_binary`：该构造**合成** `call→ret→landing`（`call` 压 `ra63`，`ret` 从 `ra63` 弹出）并明确 `loader_words=0 for expected_state.ra`；这会**覆盖**向量自身的 RA 输入，导致 `ctrl-ret[0..3]`（0x01）无法按向量语义判定。
- loader 对 `call` 的宽度推导抛 `ValueError`（`ctrl-call[5]`）。
- 与 `ret rd0` 语义无关，属构建/装载侧缺陷。

### 输入
- `tests/scripts/build_test_binary.py`（`build_call_ret_binary` 与 `derive_width_from_mnemonic` 等）
- `tests/vectors/**` 中 `ctrl-ret*` / `ctrl-call*` 用例及其 YAML

### 输出
- `ret` 用例按**向量语义**构造（不覆盖 `expected_state.ra`；若必须合成调用，需让 RA 由向量决定并写明理由）。
- loader 对 `call`/`ret` 的宽度推导不再 `ValueError`（未知 mnemonic ⇒ 明确报错并指出用例，而非崩栈）。
- 不放松既有断言；不放宽向量期望值。

### 约束
- 只改 harness/loader；不改 `spec/`、不改 ISA 语义。
- 每个修复有可达 FAIL 的反例（改回旧路由/旧推导 ⇒ 复现失败）。

## 验收标准
1. `ctrl-ret[0..3]`、`ctrl-call[5]` 按向量语义**真实通过**（贴命令、输出、退出码）。
2. 相关套件 0 fail / 0 blocked（除已登记项）。
3. 反例注入（还原旧路由/旧推导）⇒ 复现失败 ⇒ `cp` 还原 ⇒ 绿。
4. L1 / L2 绿。
5. 完成区贴真实输出。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
