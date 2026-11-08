# SPEC-196t: SimRISC 发布 0.5.6（版本与变更记录重整理）

**模块**：spec
**项目里程碑**：M11
**状态**：待开始

## 用户裁定（原话）

「SimRISC可以发布0.5.6，注意重新整理一下版本与变更记录」

## 背景

13 册 `spec/SimRISC-*` 册头现均为 `0.5.6-rc`（实测逐册确认）。`convert_f2i`（`ADR-0050`）等改动已全部落地并经 M11 验证，`-rc` 的发布时机已到。

## 目标

1. **版本发布**：13 册册头 `0.5.6-rc` → `0.5.6`；`SimRISC-00` 的索引/版本说明同步。
2. **变更记录重整理**（不是简单替换）：
   - 逐册检查现有变更记录是否「按重要性/主题归并」；散碎的同主题条目合并，重复条目去重
   - 确保每条只写「改了什么 + 影响面」，不复述实现细节
   - 倒序（最新在上）与 `check-spec-changelog` 判据一致
   - 13 册之间的同一改动（如 `convert_f2i` 六档舍入）表述一致，不各写一套
3. **只读锁同笔更新**：`manifests/spec-readonly.lock.toml` 的 13 册 sha256。
4. **引用同步**：`spec/README.md`、`contracts/` 中若写死 `0.5.6-rc` 的版本字符串，同步为 `0.5.6`（先 grep 确认范围）。

## 验收标准

1. `make check-spec-readonly` rc=0（13 册哈希同笔更新，其余册不变）
2. `make check-spec-changelog` rc=0（册头与附录首段一致、倒序、格式）
3. `make check-spec-drift` / `check-spec-numbering` / `check-spec-refs` rc=0
4. `grep -rn '0\.5\.6-rc' spec/ .tao/contracts/ docs/ contracts/` 为 0（历史归档/ADR/任务书除外，逐处确认）
5. 13 册版本行逐册核对一致（脚本统计打印，不写死）
6. `make check`（L1）rc=0
7. 完成区 ≤30 行、无运行期路径

## 非范围

- 不改任何指令语义、编码、合法性规则
- 不改已 Accepted 的 ADR
- 不发布 `Machine-v5`（其版本线独立，`m12-spec-001` 已置 `0.4.1-rc`）

## 说明

- 变更记录重整理**不得删掉历史事实**：合并条目可以，但要保留「何时改了什么」的可追溯性（日期/版本段可归并，条目内容不可丢）。
