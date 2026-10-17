---
description: 讲义笔记（lecnotes）：整个仓库只读，仅可修改 docs/DDLN；不跑 shell、不派生 subagent
mode: primary
permissions:
  # 写入：默认全禁，只放 docs/DDLN（先宽后窄，「最后匹配者胜」）
  - action: edit
    resource: "*"
    effect: deny
  - action: edit
    resource: "docs/DDLN/*"
    effect: allow
  # 不跑 shell（只读诉求由 read/glob/grep 承担；shell 能直接写文件，是"只读"的漏洞）
  - action: shell
    resource: "*"
    effect: deny
  # 禁派生 subagent（子代理用**自己的**权限，不继承本 agent，会成为越权后门）
  - action: subagent
    resource: "*"
    effect: deny
---

# 规则：讲义笔记（lecnotes，primary）

本会话**整个仓库只读**，唯一可写目录是 **`docs/DDLN/`**。

## 允许

- 读取 / 检索仓库任意内容：`read`、`glob`、`grep`。
- **仅**在 `docs/DDLN/` 下创建 / 修改 / 删除文件（讲义笔记）。

## 禁止（由本文件 frontmatter `permissions` 机械拦截，不靠自觉）

- 修改 `docs/DDLN/` 以外的任何文件（含 `spec/`、`docs/`（非 DDLN）、`.tao/`、`contracts/`、`tools/`、`Makefile` 等）。
- 运行 shell 命令。
- 派生子代理（`subagent`）。

## 遇到需要越界时

**停下，向用户说明"要做什么 + 为什么"，请用户裁定**；不得改用其它工具绕行（例如用 `execute` 里的嵌套工具、`webfetch` 等变相达成）。

## 备注

- 如需放开（例如允许只读 shell、或允许改更多目录），由用户决定后改本文件 frontmatter；不自行修改。
- `external_directory` 保持全局默认（`ask`）：读仓库外的目录仍可用，但写入已被上面的 `edit` 规则全局禁止。
