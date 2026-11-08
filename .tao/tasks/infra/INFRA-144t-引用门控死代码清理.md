# INFRA-144t: `check_knowledge_refs.py` 死代码清理（ISS-353）

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-135t`（已合入）
**状态**：待开始

## 背景

`INFRA-135t` 把「具体 `.work/**` 引用」改为一律 FAIL 后，`check_knowledge_refs.py` 留下两处死代码：

- `checked` 计数只写不读；
- (A) 面的 `dangling` 分支已不可达（具体路径不再做存在性检查）。

`ISS-353` 记录了这两项。

## 目标

- 删除死代码/死计数，**不得改判据**：具体引用一律 FAIL、四类豁免（占位/前缀/构建源码/删除语境）、`found == 0` 空转、(B) 小节级判定，全部保持原语义。
- 输出里不再出现 `悬空: N`（A 面）这类无意义行；`[ISS-352]` 段落保留。

## 验收

1. `python3 tools/infra/check_knowledge_refs.py` rc=0；fresh 树（`git archive`）`--root` rc=0。
2. 行为等价：注入「本机存在的具体 `.work` 引用」⇒ rc=1；删除全部 `.work` 引用 ⇒ rc=1（vacuous）；两者 `cp`+md5 还原回绿。
3. `make check`（L1）rc=0（并发任务红需核实归属）。
4. 关闭 `ISS-353`；完成区 ≤30 行、无运行期路径。
