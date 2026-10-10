---
description: Show current project progress - list all task statuses, current phase and next step - 查看项目进展
agent: build
---

# /status — 查看项目进展

输出当前项目的任务状态全览、所处阶段与下一步。

## 执行步骤

### 1. 定位交互目录

按 `.tao/README.md`「交互目录 `$TAO_ROOT` 定位」确定 `$TAO_ROOT`。

### 2. 输出任务状态

遍历 `$TAO_ROOT/tasks/*/*.md`，提取每个任务文件的 `**状态**` 字段，按模块分组输出：

```bash
for f in "$TAO_ROOT"/tasks/*/*.md; do
  id=$(basename "$f" .md | cut -d- -f1,2)
  s=$(grep -m1 '^\*\*状态' "$f" | sed 's/.*：//')
  d=$(grep -m1 '^\*\*依赖' "$f" | sed 's/.*：//; s/^无$//')
  echo "$id [$s]${d:+ ← 依赖 $d}"
done
```

### 3. 输出阶段与下一步

读取 `$TAO_ROOT/knowledge/MEMORY.md` 的「当前进展」段（阶段、下一步、说明），原样呈现。

### 4. 输出流转提示

- 状态机：`待开始 → 待验收 → 已验证`（`待返工` 为审查失败回退）
- 下一步动作建议：
  - 有 `待验收` → 提示 `/complete <任务编号>` 收尾
  - 有 `待开始` 且前置已完成 → 提示 `/dispatch <任务编号>` 下发
  - 有 `待返工` → 提示 `/dispatch <任务编号>` 返工
- 不修改任何文件，纯只读查询。
