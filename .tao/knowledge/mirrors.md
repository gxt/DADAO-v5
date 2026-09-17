# 大文件下载与镜像站

> 规则摘要见 `AGENTS.md`「大文件下载与镜像」节；本文件是**执行细则**。

## 为什么

从**国外站**（GitHub 等）下载**较大**软件（LLVM、QEMU、linux-kernel 等）时，直连常慢或不可达。
**实测（2026-09-16）**：`git ls-remote https://github.com/llvm/llvm-project.git` → `Failed to connect to github.com port 443 after 133927 ms: Couldn't connect to server`（exit 128）——**直连 GitHub 当时不可达**。
（对照：`.work/DADAO-0628` 等参考仓库于 2026-09-12 抓取成功，说明可达性**随时间变化**，不可假定。）

## 镜像站入口

- **教育网联合镜像站（CERNET）列表**：<https://mirrors.cernet.edu.cn/list/>
  - 用途：查询目标软件**是否有对应镜像地址**，以及有哪些可用镜像站。

## 流程（必须遵守）

1. **先查**：在 <https://mirrors.cernet.edu.cn/list/> 查询目标软件**是否有镜像地址**。
2. **逐个试**：对候选地址**逐个**测试——① **连通性**；② **下载速度**（小样下载或计时探测，如 `git ls-remote` / `curl -I` 计时）。
3. **给建议**：汇总「候选地址 + 连通性 + 速度」，给出**推荐**（**直连 GitHub 也应作为对照项**列出）。
4. **用户确定**：由**用户**决定从哪个站下载。**不得**自行选定并开始下载。

## 浅下载（默认，但仍须先问）

- 目标有**明确的 release 版本或 tag** 时，**默认浅下载**（如 `git clone --depth 1 --branch <tag>`，或只取该 commit 的树），以省时省流量。
- **仍须先询问用户**再确定：是否浅下载、下载范围（浅/全）、落到哪个目录。
- **例外/冲突提示**：若流程需要**完整历史**（如 `git describe`、跨 commit diff，或现有 `tools/infra/fetch.py` 的 `git clone --mirror` 语义），则**不能**浅下载——须向用户说明并确认。

## 记录（可审计）

- 每次下载的**镜像站选择、实测速度、用户裁决**记入 `.tao/logs/<任务ID>-mirror.log`（该目录已 gitignore）。
- 结论若影响基线选择（如换用镜像站导致 commit/产物差异），须登记到对应 ADR/任务书。
