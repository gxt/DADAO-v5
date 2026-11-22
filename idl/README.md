# `idl/` — SimRISC ISA 语义源（IDL）

本目录是 **SimRISC ISA 语义的机器可读源**：`spec/SimRISC-*` 里围栏语言标记为 `idl` 的代码块由本目录的 `.idl` 渲染而来（`render.py` 生成，禁手改）。

| 文件 | 内容 |
|------|------|
| `SimRISC-01.idl`…`SimRISC-12.idl` | 每册一个；每条指令一段以 `# id:` 开头的 operation（id 与 `contracts/opcodes.yaml` 一致） |
| `lib/fp.idl` | 浮点语义库（ft/binary32 族移植 UDB `fp.idl`；fo/binary64 族按 IEEE 754-2019 自写） |
| `render.py` | 渲染器 + 门控：按 `# id:` 切分 → 填 `spec/` 的 `<!-- IDL:<id> BEGIN/END -->` 标记 → `--check` 逐字节比对 |
| `subset_stats.py` | 语法构造现场统计 + 两份盘点文档的校验（`--check`）：M17 前端实现口径的机械真源 |
| `idl_parser.py` | IDL 子集解析器（Python 标准库）：`.idl` → AST + 构造签名门控（`--check`/`--update`/`--self-test`） |
| `idl_parse_cases.toml` | 解析器拒绝集（语法错误必须报错）+ 接受集（合法样例必须通过） |
| `idl_parse_fixture.json` | 每个 operation/function/enum/常量的**构造签名**冻结（`idl_parser.py --update` 生成） |
| `idl_exec.py` | 执行器核心（`m17-idl-003`）：四寄存器组 / 48 位地址 / 大端存储 / ELF 加载 / 最小 `trap`·`escape`；编码取 `contracts/opcodes.yaml`，语义按各 `.idl` 的 operation 正文 |
| `idl_exec_cases.toml` | 执行器差分用例清单（`tests/inst` 已有载体；`tools/idl/check_exec_parity.py` 读它） |
| `syntax-subset.md` | 语法子集盘点：13 个源文件用到的构造、现场次数、首个出处（`m17-idl-001`） |
| `width-rules.md` | 宽度/符号派生规则表（每条标出处）+ 未定义清单（`m17-idl-001`） |
| `.manifests.toml` | 本目录文件集清单（双向集合断言） |

用法：

```text
python3 idl/render.py             # 生成/更新 spec 册内的块
python3 idl/render.py --check     # 逐字节校验（漂移 ⇒ 非零）；make check-idl-sync 调它
python3 idl/render.py --self-test # 临时树内多类注入自检（改 spec 块 / 改源不重渲染 / 删一条 id / 调用未声明函数 / 解码变量当内容用）
python3 idl/subset_stats.py       # 打印语法构造的现场计数（13 个源文件）
python3 idl/subset_stats.py --check  # 校验 syntax-subset.md / width-rules.md 的计数与出处
python3 idl/idl_parser.py --check  # 全量解析 13 个源 + 构造签名 fixture + 拒绝/接受集（make check-idl-parse 调它）
python3 idl/idl_parser.py --update # 改 .idl 后重生成构造签名 fixture（须评审 diff）
python3 idl/idl_parser.py --stats  # 现场统计（每册 operation/function/enum/节点种类）
python3 idl/idl_parser.py --ast <id>  # 打印某条 operation 的 AST（S 表达式）
python3 idl/idl_parser.py --self-test # 临时树内注入自检（删括号 / 改 AST / 子集外构造）
python3 idl/idl_exec.py --self-test  # 执行器自检（寄存器组/48 位地址/大端/RAS/异常/semihosting）
python3 idl/idl_exec.py --elf <elf> [--bootrom <img>] [--init <json>] [--state-out <json>]
                                     # 运行一个镜像；--init = 初始架构状态（QEMU 观测面）
python3 tools/idl/exec_trace.py --elf <elf> --bootrom <img> --init <entry.json> --out <trace.jsonl>
                                     # 逐指令 trace（格式见 docs/idl-trace-format.md）
python3 tools/idl/qemu_trace.py --elf <elf> --bootrom <img> --entry-out <json> --trace-out <jsonl>
                                     # QEMU 观测面 → 同格式 trace（-d cpu + one-insn-per-tb）
python3 tools/idl/check_trace_parity.py --images <dir> --bootrom <img>
                                     # `tests/inst` 载体的逐指令 trace 差分（≥20 例）
```

**M17 前端实现前先读** [`syntax-subset.md`](syntax-subset.md)（用到哪些语法构造）与 [`width-rules.md`](width-rules.md)（宽度/符号规则 + 10 条「未定义」）。

**M17 解析器**（`idl_parser.py`，`m17-idl-002`）只实现 `syntax-subset.md` §10 的「必须覆盖」；§8 的未使用构造一律显式报错。它**不做语义**（不求值、不推导宽度）：字面量的位宽标注与原文留档，`U04`–`U10` 的裁定留给 `m17-idl-003` 之前取得。

**M17 执行器核心**（`idl_exec.py`，`m17-idl-003`）只有两处外部真源：编码读 `contracts/opcodes.yaml`（opc/mask/字段位域），机器几何与运行布局读 `tools/testcases/lib/machine_profile.py`；每条 operation 的语义按 `.idl` 正文实现（函数上方注明 id 与出处册）。驱动与判据在 `tools/idl/`：`qemu_final_state.py`（QEMU 入口态/末态观测面）、`check_exec_parity.py`（`tests/inst` 载体的最终架构状态/退出码差分）、`exec_trace.py` / `qemu_trace.py` / `check_trace_parity.py`（逐指令 trace 与 QEMU 按 PC 对齐差分，格式见 [`docs/idl-trace-format.md`](../docs/idl-trace-format.md)）。

**M17 执行器补齐**（`m17-idl-006`）：`idl_exec.py` 现覆盖 `tests/inst` 的 `00`/`01`/`02`/`05`/`06`/`11` 六册全部镜像（访存四组与多元素、条件赋值、RAS 压弹栈、`call` 寄存器形式、`fence`）；未注册的 id 仍显式 `ExecError`，其余册随 `m17-idl-007`/`008` 扩、`m17-idl-009` 收口。

> **import 本模块前设 `PYTHONDONTWRITEBYTECODE=1`**：`idl/` 由 `check-manifests-guard` 做**双向目录集合断言**，落 `__pycache__` 会直接判红（`idl_parse_cases.toml` 是数据文件而非模块，正是为此）。

**语言与语义库正文见 [`spec/IDL-ISA语义描述语言与语义库.md`](../spec/IDL-ISA语义描述语言与语义库.md)**：§1 语法基线、§2 命名约定、§3 寄存器模型、§4 语义库（含 §4.7 浮点原语）、§5 语法扩展提案、§6 `idlc` 复用评估；变更记录见该册文末附录。原 README 的 §1–§7 已整段迁入该册（§1–§6 节号一一对应；§7 → 附录），本文件只保留目录导航与用法——旧文里的 `idl/README §N` 记号对应新册 §N。

**与 UDB 的差异盘点见 [`diff-vs-udb.md`](diff-vs-udb.md)**（263 条 operation 逐条判定 + 整改索引）。

> **待办**：`idl/.manifests.toml` 统一补 `sha256`（工具目录清单维护，不属规范正文）。
