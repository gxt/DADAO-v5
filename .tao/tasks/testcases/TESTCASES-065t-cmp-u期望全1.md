# TESTCASES-065t: `cmp.{ut,uw,ub}` 向量期望改为 64 位全 1

**模块**：testcases
**项目里程碑**：M10
**依赖**：SPEC-173t、QEMU-074t、ADR-0037
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

### 背景（ADR-0037）
- 向量 `tests/vectors/isa/reg-compare.yaml` 现按**零扩展**写期望（如 `cmp.ut` 的 -1 = `0x00000000FFFFFFFF`）。
- 新语义：`-1 = 0xFFFF_FFFF_FFFF_FFFF`；`0/1` 不变。

### 输出
1. 逐条改 `tests/vectors/isa/reg-compare.yaml` 中 `cmp.ut` / `cmp.uw` / `cmp.ub` 的 **-1 期望值**为 `0xFFFFFFFFFFFFFFFF`（0/1 用例不动）；同步 `notes` 里的描述。
2. 若向量格式支持多指令序列，新增一条 `cmp.ut` + `br.n` 的语义用例（判负命中）；若不支持，在完成区说明，并引用 QEMU-074t 的 br.n 用例。
3. 不改 `cmp.st/sw/sb` 及其它指令期望。

### 约束
- 期望值从 ADR-0037 / SPEC-173t 派生，**不从 QEMU 实现反推**；改完须全量重算而非抽样。
- 只改向量与必要说明；不改 `spec/`。

## 验收标准
1. `python3 tools/testcases/validate_elf_vectors.py`（或向量校验入口）rc=0；`make check` rc=0。
2. 全量语义跑：相关 cmp 用例 pass，0 fail / 0 blocked（贴计数）。
3. 反例注入（保留一条零扩展期望）⇒ 该用例红 ⇒ `cp` 还原 ⇒ 绿。
4. L1 / L2 绿。
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
