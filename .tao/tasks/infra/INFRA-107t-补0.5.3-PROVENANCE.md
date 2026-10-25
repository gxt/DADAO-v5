# INFRA-107t: 补 0.5.3 PROVENANCE 的组合 sha 与逐文件表

**模块**：infra
**项目里程碑**：M10
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地（纯文档，无构建）

## 接口规范

### 背景（ISS-333，实测 2026-10-25）
- `python3 tools/spec/gen_spec_archive.py --verify` rc=1，唯一失败项 = `SimRISC-0.5.3`（5 文件）：其 `PROVENANCE.md` 缺「版本组合 sha256」行与「逐文件 sha256」表；`0.5.4` / `0.5.5` 均 OK。
- `0.5.4` 的现成格式：`- 版本组合 sha256：\`<64 hex>\`` + `## 逐文件 sha256` 表。

### 输入
- `.tao/archive/SimRISC-0.5.3/PROVENANCE.md`（**只增不改**）
- `.tao/archive/SimRISC-0.5.4/PROVENANCE.md`（格式范例）
- `tools/spec/gen_spec_archive.py`（sha 计算口径真源；**不得自创公式**）

### 输出
- 在 0.5.3 `PROVENANCE.md` 追加：版本组合 sha256 行 + 逐文件 sha256 表（5 文件），数值按脚本口径/现场重算。
- 归档正文（5 个 `.md`）**不改**。

### 约束
- 遵守 `docs/Process-06 §8`（归档只增不改，不改归档文件本体）。
- 不改 `tools/spec/**`；若发现脚本口径缺陷，停下报告。

## 验收标准
1. `python3 tools/spec/gen_spec_archive.py --verify` rc=0（0.5.3 通过）。
2. `python3 tools/spec/check_spec_archive.py`（L1）rc=0。
3. `make check` rc=0。
4. 逐文件 sha 与现场重算一致（贴命令与输出）。
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
