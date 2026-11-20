# `idl/` — SimRISC ISA 语义源（IDL）

本目录是 **SimRISC ISA 语义的机器可读源**：`spec/SimRISC-*` 里围栏语言标记为 `idl` 的代码块由本目录的 `.idl` 渲染而来（`render.py` 生成，禁手改）。

| 文件 | 内容 |
|------|------|
| `SimRISC-01.idl`…`SimRISC-12.idl` | 每册一个；每条指令一段以 `# id:` 开头的 operation（id 与 `contracts/opcodes.yaml` 一致） |
| `lib/fp.idl` | 浮点语义库（ft/binary32 族移植 UDB `fp.idl`；fo/binary64 族按 IEEE 754-2019 自写） |
| `render.py` | 渲染器 + 门控：按 `# id:` 切分 → 填 `spec/` 的 `<!-- IDL:<id> BEGIN/END -->` 标记 → `--check` 逐字节比对 |
| `.manifests.toml` | 本目录文件集清单（双向集合断言） |

用法：

```text
python3 idl/render.py             # 生成/更新 spec 册内的块
python3 idl/render.py --check     # 逐字节校验（漂移 ⇒ 非零）；make check-idl-sync 调它
python3 idl/render.py --self-test # 临时树内多类注入自检（改 spec 块 / 改源不重渲染 / 删一条 id / 调用未声明函数 / 解码变量当内容用）
```

**语言与语义库正文见 [`spec/IDL-ISA语义描述语言与语义库.md`](../spec/IDL-ISA语义描述语言与语义库.md)**：§1 语法基线、§2 命名约定、§3 寄存器模型、§4 语义库（含 §4.7 浮点原语）、§5 语法扩展提案、§6 `idlc` 复用评估；变更记录见该册文末附录。原 README 的 §1–§7 已整段迁入该册（§1–§6 节号一一对应；§7 → 附录），本文件只保留目录导航与用法——旧文里的 `idl/README §N` 记号对应新册 §N。

**与 UDB 的差异盘点见 [`diff-vs-udb.md`](diff-vs-udb.md)**（263 条 operation 逐条判定 + 整改索引）。

> **待办**：`idl/.manifests.toml` 统一补 `sha256`（工具目录清单维护，不属规范正文）。
