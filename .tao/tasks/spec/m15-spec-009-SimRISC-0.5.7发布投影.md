# m15-spec-009: SimRISC 0.5.7 发布投影（README + 契约头 + 规范快照）

**模块**：spec
**项目里程碑**：M15
**依赖**：`m15-spec-008`（0.5.7 发布，**须先合入**）
**可并行分片**：否
**预估**：1 h
**档位**：小改（版本投影 + 归档快照）
**状态**：待开始

## 背景

用户 2026-11-20 授权：SimRISC 版本 **0.5.7** 已发布（`m15-spec-008`），随之修改**引用它的 README 与契约投影**。

`check-spec-drift` 的判据：`contract-*.md` 的 `> **版本：X.Y.Z**` 必须等于 `README.md` 版本表的「已发布版本」列。

## 目标

1. **根 `README.md`**：`| SimRISC | 0.5.6 | 0.5.7-rc |` → `| SimRISC | 0.5.7 | — |`（已发布列取 0.5.7；在研列无在研版本时写 `—`）；
2. **契约版本头**（与 0.5.7 对齐）：
   - `.tao/contracts/contract-isa.md`：`> **版本：0.5.6**` → `0.5.7`；
   - `.tao/contracts/contract-fp.md`：标题与版本头 `0.5.6` → `0.5.7`；
   - `.tao/contracts/README.md` 索引行里的 SimRISC 版本号同步；
   - `.tao/contracts/contract-elf.md` 的「（SimRISC 0.5.4）」引用同步为 0.5.7；
3. **规范快照**：`python3 tools/spec/gen_spec_archive.py --apply`（或现行等价命令）生成 `.tao/archive/SimRISC-0.5.7/`，与 0.5.6 同套路；
4. 契约**正文语义零改动**——只动版本行/引用文本。

## 验收（逐条贴真实 rc）

1. `check-spec-drift` **rc=0**（README 已发布列 = 各契约版本头）；
2. `check-spec-archive` **rc=0** 且 `check-spec-archive-verify` 通过（快照存在、内容与 0.5.7 声明一致）；
3. `check-spec-changelog`/`numbering`/`purity`/`refs`/`codeblocks`、`check-manifests-guard`、`check-contracts-dir`、`check-contract-relocs`、`check-knowledge-refs` 全 rc=0；
4. **正文零改动**：契约剥掉版本行后与 `HEAD~1` 逐字节相同；
5. **可达 FAIL ≥2 路**（临时树/`cp`+md5）：① 把 README 改回 `0.5.6` ⇒ `check-spec-drift` 红；② 删快照目录 ⇒ `check-spec-archive` 红。

## 约束

独立 `git worktree`；不提交 git；**不改契约语义**、不改 `spec/` 正文；术语「寄存器组」；完成区不写具体 `.work/**` 路径。
