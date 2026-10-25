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

- 版本组合 sha256：`955bc1114832375a4a22f1a8273e20005d33cc32fa64e1be78d4e3b8fdcf23ba`

## 逐文件 sha256

```
5de94d8e3e334f4d0caf7991b1421adda9bba01120b0c181aa6f4295d47b7837  SimRISC-00-指令系统设计.md
6866c803bf0676e7d97a59679db49b9e6ad34c0c6e0997c29a0ca9cb0bbb08dc  SimRISC-01-数据类指令.md
738f6d6b657ada3df90d6343006c8371ba17c15201dca00321adab1479494014  SimRISC-02-地址类指令.md
0441fbafe5653fc9357e7eb669ba53e5465e10282e4ffc839f94f554168514ca  SimRISC-03-浮点类指令.md
df831ca935c51ebea0b55a80db3f69402142bf4fda1ba20d40df95654115d474  SimRISC-04-系统类指令.md
```

**口径**：上表为归档目录内 5 个 `SimRISC-*.md` 的现场 sha256，与 v5 归档提交
`86fdcc8e92ae5946efcbb74813873cd629e16929` 的快照内容逐文件全等；组合 sha256 按 `tools/spec/gen_spec_archive.py`
口径重算（文件名排序拼 `<sha256>  <basename>` + 换行后取 sha256）。
2026-10-25 补记（INFRA-107t）；归档正文与上文均未改动。
