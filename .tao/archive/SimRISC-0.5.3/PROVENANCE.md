# PROVENANCE — SimRISC 0.5.3

**口径（用户 2026-10-21 裁定，原话「时间点靠前的为准（早期没有采用 `-rc` 的方式）」）**：

- **快照/版本声明提交 = `eb4eff43`**
  - 标题：`SimRISC: 版本号 0.5.2→0.5.3`
  - 时间：`2026-07-19T05:09:04Z`
  - 该提交把 `wiki/SimRISC-00..04` 的版本串由 `0.5.2` 改为 `0.5.3`。

- **对照（不作 0.5.3 快照）**：`640b879`（同日 `05:07:56Z`，早 68 秒，标题 `SimRISC: setrd/setrb/setrf → set.rd/set.rb/set.rf`）—— 其文档版本串仍为 `0.5.2`，属 **0.5.2** 快照（见 `.tao/archive/SimRISC-0.5.2/PROVENANCE.md`）。

- **v5 归档提交 = `86fdcc8`**（`2026-09-28`，`SPEC-013t: 归档 SimRISC 0.5.3 文档`）—— 仅 `git mv spec/SimRISC-0.5.3 → .tao/archive/SimRISC-0.5.3` 的**搬运**，不是内容来源。

## 披露（口径与文本的差异，照实记录）

- `eb4eff43` 时 `wiki/SimRISC-00-指令系统设计.md` 为 **205 行**；本归档为 **381 行**。
- 差异来源（现场核对）：归档文本取自 v5 的 `spec/SimRISC-0.5.3/`，该副本在 wiki 导入后仍有 v5 侧维护（`--follow` 可见 `3f69139c`→`8049d74`→`954de83`→`8433436`→`1ed38f6`→`5224b8e` 等后续编辑）。
- ⇒ **`eb4eff43` 是"0.5.3 版本声明点"**，归档正文是"v5 侧 0.5.3 文档副本"；两者不完全逐字相同，属预期。

## 复现

```sh
# 版本声明提交
git show eb4eff43 --stat
git show eb4eff43:wiki/SimRISC-00-指令系统设计.md | sed -n '3p'   # > **版本：0.5.3**

# v5 归档搬运提交
git log --oneline -1 86fdcc8
```

**状态**：本文件补上 0.5.3 缺失的 `PROVENANCE.md`（其余 7 个归档目录均已有）。
