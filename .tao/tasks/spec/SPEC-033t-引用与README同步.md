# SPEC-033t: contract-abi 引用修正 + docs/README 同步

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题描述

### G4. contract-abi.md 引用陈旧（2 处）

- `.tao/knowledge/contract-abi.md:142`：`[SimRISC-02 §函数调用]`、`[SimRISC-02 §函数返回]`
- `.tao/knowledge/contract-abi.md:143`：`[SimRISC-02 §函数调用]`

`SimRISC-02` 现为「寄存器复制」；`§函数调用`/`§函数返回` 已迁至 `SimRISC-06-控制流.md`。**应改为 `SimRISC-06`**。

### G5. docs/README.md:17 陈旧

第17行 assembly-list 描述仍为旧顺序/旧名/旧计数：
```
| `assembly-list.md` | ...256 条，按 8位数据运算/16位数据运算/32位数据运算/64位数据运算/64位地址运算/浮点/存储/控制流/寄存器复制/16位立即数操作/其它/待定 分章...；浮点（46）与待定（14）两章整章 deferred... |
```
应为：
```
| `assembly-list.md` | ...254 条，按 取数存数/寄存器复制/16位立即数操作/64位数据运算/64位地址运算/控制流/浮点运算/32位数据运算/16位数据运算/8位数据运算/其它/待定 分章...；浮点运算（46）与待定（12）两章整章 deferred... |
```

## 修改内容

1. `contract-abi.md` 的 `SimRISC-02 §函数调用`/`§函数返回` → `SimRISC-06`
2. `docs/README.md` 第17行：顺序、名称、计数对齐 SimRISC-00~12

## 约束

- 逐条精确替换，**禁止正则批量替换**
- 不改动其他内容

## 验收标准

1. `contract-abi.md` 中无 `SimRISC-02 §函数调用`/`§函数返回`
2. `python3 tools/infra/check_spec_refs.py` 的 Check1 失败中 contract-abi 的 2 条真实陈旧消除（模板占位 `SimRISC-0X` 等除外）
3. `docs/README.md:17` 顺序/名称/计数与 spec 一致
4. 其他内容未改动

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）