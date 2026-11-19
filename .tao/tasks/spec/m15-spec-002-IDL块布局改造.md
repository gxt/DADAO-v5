# m15-spec-002: IDL 块在 spec 内的布局改造（节末集中 + 三级标题）

**模块**：spec
**项目里程碑**：M15
**依赖**：`m15-idl-001`…`m15-idl-012` 全部合入（否则每册重渲染两遍）；`m15-spec-001`（`idl/render.py` 已就绪）
**可并行分片**：否（一次改 `render.py` + 12 册，串行）
**预估**：4–6 h
**档位**：中改
**状态**：待开始

## 目标

当前 IDL 块（`idl/render.py` 生成的 ```idl``` 段）**内联插在散文段落之间、无标题、无导语、块首 `# id:` 与上下文重复**，读起来生硬。按用户 2026-11-19 裁定（`discussing.md` N26）改为：

1. **每册每个 `##` 节末尾集中**该节全部 operation，配**一个三级标题** `### N.M 形式化语义（IDL）`（标题数 = 每册 3–4 个，不是逐指令一个）；
2. 块前一句生成导语：「本节各指令的形式化语义由 `idl/SimRISC-0X.idl` 生成，逐条如下：」；
3. 块内去掉与上下文重复的 `# id:` 行，改用一行粗体标注 `**`<id>`**`；
4. 保留 `<!-- IDL:<id> BEGIN/END -->` 标记（`render.py --check` 与 `check-idl-sync` 依赖）；
5. **不新增附录**（`check-spec-numbering` 断言 6/7 限定 `SimRISC-01`–`12` 尾段只能是附录 A、B）。

## 硬约束

1. **散文一字不动**：只允许 `render.py` 写标记块与上述导语/标题；散文段落原样保留（"散文零改动" 判据改为「剥掉标记块 + 生成标题/导语后与基线逐字节相同」）。
2. **不升级版本号**；变更记录在 `SimRISC-00` 的 `0.5.7-rc` 段追加条目。
3. **不逐条加标题**：`SimRISC-07` 有 50 条指令，逐条标题会让目录失控。
4. 术语一律「寄存器组」。

## 交付

1. `idl/render.py`：支持新布局（节末聚合 + 三级标题 + 导语 + 去 `# id:`）；`--check` 仍逐字节校验；
2. 12 册 `spec/SimRISC-0X-*.md` 全部重渲染；
3. `spec/.manifests.toml` 的 12 册 sha256 同笔重算；
4. `SimRISC-00` 变更记录追加条目。

## 验收（逐条贴真实 rc）

1. `python3 idl/render.py --check` rc=0（12 册全部逐字节一致）；
2. `make check-idl-sync`、`check-manifests-guard`、`check-spec-numbering`、`check-spec-changelog`、`check-spec-purity`、`check-spec-codeblocks`、`check-spec-drift`、`check-spec-refs`、`check-asm-list`、`check-asm-prose`、`check-legality-drift` 全 rc=0；
3. **散文零改动**：每册剥掉「标记块 + 生成标题 + 导语」后与改造前逐字节相同（逐册给哈希）；
4. 标题数与节数现场统计相等（逐册打印 `节数 / 新标题数`），且无 `#####`；
5. **可达 FAIL ≥2 路**：① 某册手改生成标题 ⇒ `--check` 必须红；② 删某册的导语 ⇒ 判据必须红（各 `cp`+md5 还原）。

## 批次

- 批 1：`render.py` 改造 + 先在 `SimRISC-03`（8 条，最小）上验证 + 全套门控；
- 批 2：其余 11 册重渲染 + 门控 + 散文哈希逐册核对。

## 待裁定

（无。布局方案已由用户 2026-11-19 裁定为 A：节末集中 + 三级标题；时机为用户选「等 12 册全部合入后」。）
