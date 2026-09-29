# INFRA-017t: infra 模块小修（deferred 遗留）

**模块**：infra
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题描述（来自 `deferred.md`）

1. **`fetch.py` 选源标签逻辑重复（DRY）**（`INFRA-009t` 遗留）：`main()` 为打印实际使用的源，**重新解析**了一遍 `COMPONENT_SOURCE_<NAME>` 与 `source[0]["name"]`，与 `select_source()` 内部逻辑重复（未来可能不同步）。建议：`select_source()` 返回 `(url, label)`，或在 `main()` 复用其解析结果。
2. **`check_spec_drift.py --test-mode` 判别力不足**（`INFRA-012t` reviewer）：4 个负测试中 `source_missing`/`source_bad_format` 在函数入口无条件 `return ("error", …)`，`version_mismatch`/`unknown_adr` 的注入点也在真实比对之前 ⇒ 只证明「能打印 FAIL」，**不证明能识别该 4 类真实缺陷**。建议：改为**基于临时 fixture 的真实负测试**（构造真实缺陷合约而非注入分支）。

## 约束

- 只做上述 2 项；不改 `fetch.py`/`check_spec_drift.py` 的正常行为
- 命令缺失 → 停下报告，禁止自行安装/下载
- 逐条核对，禁止正则批量替换
- 完成后 `make check` EXIT=0

## 验收标准

1. `fetch.py` 选源解析单一来源（无重复逻辑）；行为不变（`make fetch` 幂等/选源标签打印正确）
2. `check_spec_drift.py --test-mode` 的 4 类负测试改为**真实 fixture**；每类「构造真实缺陷 → exit 1」可复现
3. `make check` EXIT=0

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