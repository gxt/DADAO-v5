# SPEC-032t: opcodes.yaml spec_cite 按位宽拆分

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题描述（G2）

`contracts/opcodes.yaml` 中 **78 条** 8/16/32 位数据运算指令的 `spec_cite` 全部指向 `SimRISC-04`（64位数据运算），应为各自的位宽文档：

| 位宽 | 后缀 | 应指向 | 条数 |
|------|------|--------|------|
| 32 位 | `.ut`/`.st` | `SimRISC-08` | 26 |
| 16 位 | `.uw`/`.sw` | `SimRISC-09` | 26 |
| 8 位 | `.ub`/`.sb`/`.b` | `SimRISC-10` | 26 |

**根因**：`tools/spec/generate_opcodes.py` 的 `S04_*` 常量未按位宽拆分，所有数据运算都用了 `S04`（SimRISC-04）。

## 修改内容

### tools/spec/generate_opcodes.py

按位宽拆分 spec_cite 常量：
- 64 位（`.uo`/`.so`/`.o`）→ `SimRISC-04`
- 32 位（`.ut`/`.st`/`.t`）→ `SimRISC-08`
- 16 位（`.uw`/`.sw`/`.w`）→ `SimRISC-09`
- 8 位（`.ub`/`.sb`/`.b`）→ `SimRISC-10`

对应各章节（如 `§加减操作`、`§比较操作`、`§乘除操作`、`§Logic operators：逻辑运算`、`§Bit manipulating：位操作指令`）在 08/09/10 中均存在同名章节。

### 重生成

```
python3 tools/spec/generate_opcodes.py
```

## 约束

- **改生成器，不改产物**
- 只改 8/16/32 位数据运算指令的 spec_cite；其他指令（存储/控制流/浮点等）不动
- 逐条核对，禁止正则批量替换
- 修后 `check_qfc_coverage.py` 仍 0 差异

## 验收标准

1. 8/16/32 位数据运算指令的 spec_cite 分别指向 SimRISC-10/09/08
2. 验证脚本「引用文档须含该指令」0 错（原 78 条）
3. `check_qfc_coverage.py` 0 差异
4. 生成器重跑输出与仓库文件一致
5. `make check` EXIT=0

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