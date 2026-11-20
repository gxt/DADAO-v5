# m15-spec-006: IDL 语言规范与语义库迁入 `spec/`（新册 `IDL-01-DADAO-ISA语义描述语言与语义库`）

**模块**：spec
**项目里程碑**：M15
**依赖**：无（`m15-spec-005` 已收尾；`.idl` 内容不动）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改
**状态**：待开始

## 背景（用户 2026-11-20 裁定）

`idl/README.md` 现有 **428 行**，实际是**规范正文**：§1 语法基线（UDB IDL 子集）、§2 命名约定、§3 寄存器模型、§4 语义库（4.1–4.7，约 260 行）、§5 语法扩展提案、§6 `idlc` 复用评估、§7 变更记录。而 `spec/README.md:36` 把它当真源指（「语法基线、寄存器模型与语义库见 `../idl/README.md`」）。

⇒ 规范正文寄生在**工具目录的 README** 里，与三分界（`spec/` = 技术规范正文唯一真源）相反。

**UDB 的对应做法**：语言说明书是独立文档 **`doc/idl.adoc`**（ISA Description Language），语义库是 `spec/std/isa/isa/*.idl`。

**用户裁定**：
1. **就一册**（语言 + 语义库同册）；
2. 文件名**要写清是什么语言**——即 **DADAO ISA 语义描述语言**（`IDL-01-DADAO-ISA语义描述语言与语义库.md`）。

## 要做

1. **新建** `spec/IDL-01-DADAO-ISA语义描述语言与语义库.md`：
   - 正文 = 现 `idl/README.md` 的 §1–§6（保持内容，可重排编号适配 spec 体例）；
   - §7 变更记录迁入本册的**变更记录附录**（`check-spec-numbering` 对非 `SimRISC-` 册要求「变更记录附录为最后一个 `##`」）；
   - 册内 `## N.` 编号连续、不跳级（`check-spec-numbering`）。
2. **`idl/README.md` 精简**为**目录导航 + 用法**（≤60 行）：12 册 `SimRISC-NN.idl`、`lib/fp.idl`、`render.py` 的三条用法、`.manifests.toml`；语言与语义库的正文**指向** `spec/IDL-01-…`。
3. **`idl/render.py` 的扫描面改指新册**：现 `render.py:210-213` 解析 `idl/README.md §4` 的代码块，作为「每条 operation 调用的函数都在语义库声明」这条断言（E 组）的扫描面；改为解析 `spec/IDL-01-…` 的语义库章节。**保持「+ `idl/lib/*.idl`」那一半不变**。
4. **`spec/README.md`**：「ISA 语义（IDL）」节的指针改指新册；「分册清单」加一行（可按现有分组，或新开「ISA 语义（IDL）」组内列入本册）。
5. **`spec/.manifests.toml`**：加本册条目 + `sha256`；`spec/README.md` 的 `sha256` 同笔重算。

## 硬约束

- **不动任何 `.idl` 内容**（12 册 + `lib/fp.idl` 一字不改）；
- **不改门控判据**（`check-idl-sync`/`check-spec-*` 的逻辑不变，只换被扫描的路径）；
- 术语一律「寄存器组」；
- 不升级版本号。

## 验收（逐条贴真实 rc）

1. `python3 idl/render.py --check` rc=0（263 条 / 12 册逐字节一致）；
2. `make check-idl-sync`、`check-manifests-guard`、`check-spec-numbering`、`check-spec-purity`、`check-spec-codeblocks`、`check-spec-drift`、`check-spec-refs`、`check-spec-changelog`、`check-knowledge-refs` 全 rc=0；
3. **断言 E 仍可达 FAIL**：临时在某条 operation 里调用一个未声明函数 ⇒ `render.py --check` 必须红（`cp`+md5 还原）；
4. **内容零丢失**：新册正文与 `idl/README.md` 旧 §1–§7 逐段对账（可用 diff，排除重排编号），列出差异仅为「编号/标题层级」；
5. **`idl/README.md` ≤60 行**且无规范正文（只有导航 + 用法 + 指针）。

## 完成区

（待填）
