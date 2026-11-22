# `idl/` — SimRISC ISA 语义源（IDL）

本目录是 **SimRISC ISA 语义的机器可读源**：`spec/SimRISC-*` 里围栏语言标记为 `idl` 的代码块由本目录的 `.idl` 渲染而来（`tools/idl_render.py` 生成，禁手改）。

| 文件 | 内容 |
|------|------|
| `SimRISC-01.idl`…`SimRISC-12.idl` | 每册一个；每条指令一段以 `# id:` 开头的 operation（id 与 `contracts/opcodes.yaml` 一致） |
| `lib/fp.idl` | 浮点语义库（ft/binary32 族移植 UDB `fp.idl`；fo/binary64 族按 IEEE 754-2019 自写） |
| `tools/idl_render.py` | 渲染器 + 门控：按 `# id:` 切分 → 填 `spec/` 的 `<!-- IDL:<id> BEGIN/END -->` 标记 → `--check` 逐字节比对 |
| `tools/idl_subset_stats.py` | 语法构造现场统计 + 两份盘点文档的校验（`--check`）：M17 前端实现口径的机械真源 |
| `tools/idl_parser.py` | IDL 子集解析器（Python 标准库）：`.idl` → AST + 构造签名门控（`--check`/`--update`/`--self-test`） |
| `tools/idl_check_anchor.py` | 执行器「依据锁」门控（`m17-idl-017`）：`.idl` operation 正文 + `lib/*.idl` 文件 sha256 + `@sem` 实现函数名 ↔ `data/exec_anchor.toml`（`--check`/`--update`/`--self-test`） |
| `tools/idl_exec.py` | 执行器核心（`m17-idl-003`）：四寄存器组 / 48 位地址 / 大端存储 / ELF 加载 / 最小 `trap`·`escape`；编码取 `contracts/opcodes.yaml`，语义按各 `.idl` 的 operation 正文 |
| `tools/idl_fp.py` | FP 独立 spec-exact 参考模型（精确值一次舍入 + `rf0[4:0]` 标志；原 `chipyard/fp_ref.py`）：`07-floating-point` 的 50 个 op 由 `idl_exec.py` 薄封装调用它（`m17-idl-013`） |
| `tools/idl_four_way.py` | 四方差分驱动（IDL / QEMU / gem5 / chipyard；`make check-idl` 的 L2 入口） |
| `tools/idl_exec_parity.py` | `tests/inst` 载体的最终架构状态/退出码差分 |
| `tools/idl_qemu_state.py` | QEMU 入口态/末态观测面 |
| `tools/idl_exec_trace.py` | 用执行器生成逐指令 trace |
| `tools/idl_qemu_trace.py` | 从 QEMU 观测面派生同格式 trace |
| `tools/idl_trace_common.py` | trace 公共口径与 JSONL 读写 |
| `tools/idl_check_trace.py` | 逐指令 trace 与 QEMU 按 PC 对齐差分 |
| `tools/idl_paths.py` | 上述程序共用的仓库路径真源 |
| `data/idl_parse_cases.toml` | 解析器拒绝集（语法错误必须报错）+ 接受集（合法样例必须通过） |
| `data/idl_parse_fixture.json` | 每个 operation/function/enum/常量的**构造签名**冻结（`tools/idl_parser.py --update` 生成） |
| `data/idl_exec_cases.toml` | 执行器差分用例清单（`tests/inst` 已有载体；`tools/idl_four_way.py` 读它） |
| `data/exec_anchor.toml` | 执行器「依据锁」：逐 operation 正文 sha256 + `book`/`impl` + `lib/*.idl` 逐文件 sha256（`tools/idl_check_anchor.py --update` 生成，禁手改） |
| `docs/syntax-subset.md` | 语法子集盘点：13 个源文件用到的构造、现场次数、首个出处（`m17-idl-001`） |
| `docs/width-rules.md` | 宽度/符号派生规则表（每条标出处）+ 已定义语义清单（`m17-idl-001`） |
| `docs/diff-vs-udb.md` | 与 UDB 的差异盘点（结论索引） |
| `docs/four-way.md` | IDL 四方差分口径（`m17-idl-005`） |
| `docs/trace-format.md` | 逐指令 trace 格式（`m17-idl-004`） |
| `docs/trace-sample.jsonl` | trace 样例（由 `tools/idl_check_trace.py --sample-out` 生成） |
| `.manifests.toml` | 本目录文件集清单（双向集合断言） |

用法：

```text
python3 idl/tools/idl_render.py             # 生成/更新 spec 册内的块
python3 idl/tools/idl_render.py --check     # 逐字节校验（漂移 ⇒ 非零）；make check-idl-sync 调它
python3 idl/tools/idl_render.py --self-test # 临时树内多类注入自检（改 spec 块 / 改源不重渲染 / 删一条 id / 调用未声明函数 / 解码变量当内容用）
python3 idl/tools/idl_subset_stats.py       # 打印语法构造的现场计数（13 个源文件）
python3 idl/tools/idl_subset_stats.py --check  # 校验 docs/syntax-subset.md / docs/width-rules.md 的计数与出处
python3 idl/tools/idl_parser.py --check  # 全量解析 13 个源 + 构造签名 fixture + 拒绝/接受集（make check-idl-parse 调它）
python3 idl/tools/idl_parser.py --update # 改 .idl 后重生成构造签名 fixture（须评审 diff）
python3 idl/tools/idl_parser.py --stats  # 现场统计（每册 operation/function/enum/节点种类）
python3 idl/tools/idl_parser.py --ast <id>  # 打印某条 operation 的 AST（S 表达式）
python3 idl/tools/idl_parser.py --self-test # 临时树内注入自检（删括号 / 改 AST / 子集外构造）
python3 idl/tools/idl_check_anchor.py --check  # 执行器依据锁校验（make check-idl-exec-anchor 调它）
python3 idl/tools/idl_check_anchor.py --update # 改 .idl（含 lib/*.idl）后重生成；评审 diff 并说明实现是否跟改
python3 idl/tools/idl_check_anchor.py --self-test # 临时树内注入自检（改正文 / 删 id / 删表条 / 改库文件）
python3 idl/tools/idl_exec.py --self-test  # 执行器自检（寄存器组/48 位地址/大端/RAS/异常/semihosting）
python3 idl/tools/idl_exec.py --elf <elf> [--bootrom <img>] [--init <json>] [--state-out <json>]
                                     # 运行一个镜像；--init = 初始架构状态（QEMU 观测面）
python3 idl/tools/idl_exec_trace.py --elf <elf> --bootrom <img> --init <entry.json> --out <trace.jsonl>
                                     # 逐指令 trace（格式见 docs/trace-format.md）
python3 idl/tools/idl_qemu_trace.py --elf <elf> --bootrom <img> --entry-out <json> --trace-out <jsonl>
                                     # QEMU 观测面 → 同格式 trace（-d cpu + one-insn-per-tb）
python3 idl/tools/idl_check_trace.py --images <dir> --bootrom <img>
                                     # `tests/inst` 载体的逐指令 trace 差分（≥20 例）
```

**M17 前端实现前先读** [`docs/syntax-subset.md`](docs/syntax-subset.md)（用到哪些语法构造）与 [`docs/width-rules.md`](docs/width-rules.md)（宽度/符号规则 + 已定义语义清单）。

**M17 解析器**（`tools/idl_parser.py`，`m17-idl-002`）只实现 `docs/syntax-subset.md` §10 的「必须覆盖」；§8 的未使用构造一律显式报错。它**不做语义**（不求值、不推导宽度）：字面量的位宽标注与原文留档，原 `U04`–`U10` 已由语言规范册 §1.1 定义。

**M17 执行器核心**（`tools/idl_exec.py`，`m17-idl-003`）只有两处外部真源：编码读 `contracts/opcodes.yaml`（opc/mask/字段位域），机器几何与运行布局读 `tools/testcases/lib/machine_profile.py`；每条 operation 的语义按 `.idl` 正文实现（函数上方注明 id 与出处册）。驱动与判据在 `tools/`：`idl_qemu_state.py`（QEMU 入口态/末态观测面）、`idl_exec_parity.py`（`tests/inst` 载体的最终架构状态/退出码差分）、`idl_exec_trace.py` / `idl_qemu_trace.py` / `idl_check_trace.py`（逐指令 trace 与 QEMU 按 PC 对齐差分，格式见 [`docs/trace-format.md`](docs/trace-format.md)）。

**M17 执行器补齐**（`m17-idl-006`）：`tools/idl_exec.py` 现覆盖 `tests/inst` 的 `00`/`01`/`02`/`05`/`06`/`11` 六册全部镜像（访存四组与多元素、条件赋值、RAS 压弹栈、`call` 寄存器形式、`fence`）；未注册的 id 仍显式 `ExecError`，其余册随 `m17-idl-007`/`008` 扩、`m17-idl-009` 收口。

**M17 执行器补齐（续）**（`m17-idl-007`）：`04` 整册（八元算术/位操作）、`12-misc` 整册（`lr`/`sc` 原子、`swym`、`ctlz`/`cttz`/`ctpop`）与 00 册 `atomic_rmw` 载体全部纳入主清单；原子按 `SimRISC-12 §1` 实现「精确地址 + 访问宽度」保留键、窄读保高位、异常进入清标记（单 hart 口径，`ISS-440` 的多 hart 清除不建模），`swym` 为 no-op。

**M17 执行器补齐（窄位宽 ALU）**（`m17-idl-008`）：`08`/`09`/`10` 三册（32/16/8 位算术、比较、乘除余、移位/循环/反转）与 `03` 剩余 6 个镜像全部纳入主清单，`pending` 清零（主清单 222）；窄位宽按 `.idl` 正文的 size 截断 + `.s`/`.u` 符号/零扩展实现，orri/orrr 共用参数化路径（移位量取 `immu6` 或 `rdHD` 低位）。

**M17 执行器补齐（浮点，阶段二）**（`m17-idl-013`）：`07-floating-point` 整册 **50 个 op**（转换 18 / 算术 12 / 比较 4 / 符号 4 / minmax 4 / 分类 2 / 取整 2 / 开方 2 / fma 2）纳入主清单；执行器只做薄封装（合法性、`rf0[33:32]` 或 `immu6` 六档取舍入方向、ft 窄写/fo 整写、标志 sticky 并入 FCSR），值与标志由 `tools/idl_fp.py` 给出 ⇒ `SEMANTICS` **263/263**（`contracts/opcodes.yaml` 全覆盖）、主清单 **272**。

**执行器「依据锁」**（`m17-idl-017`）：`data/exec_anchor.toml` 锁住 `tools/idl_exec.py` 每条 `@sem` 实现所依据的 operation 正文（`# id:` 行起、至下一条之前，切分复用 `tools/idl_render.py`）与 `idl/lib/*.idl` 文件全文；判据 = 集合相等（条数现场派生）+ sha 逐条命中 + `impl` 在 `@sem` 注册里。**改 `.idl`（含 `lib/*.idl`，FP 语义在库里）⇒ 必须 `--update`**，并在评审里说明对应实现是否跟改；不跟改也要显式更新，让「正文变了、实现没动」在 diff 里可见。

## 四方差分与门控（阶段一收口，`m17-idl-009`）

阶段一 = 非 FP 的 `tests/inst` 镜像在 IDL / QEMU / gem5 / chipyard 四方一致。判据 = **签名槽流逐槽全等 + 退出码全等**，且每方槽值再对独立 oracle `tests/data/inst-signature/expected.tsv` 逐槽比对（四方一致但全错仍红）；口径正文见 [`docs/four-way.md`](docs/four-way.md)。

用例清单 `data/idl_exec_cases.toml`：`[[case]]` = 主清单，`[[pending]]` = **必须为空**（阶段二已收口；能力缺口另立任务）。门控在 `tools/idl_four_way.py` 内**现场派生**并断言 `{主清单} == {tests/inst/*/*.S} − {pending}` 且 `pending` 必须为空：主清单少/多一条、`pending` 非空（含「一致地把一条移进 pending」）、越界或与主清单相交 ⇒ rc=2，文案「pending 必须为空」；计数不写死。**当前 `pending` 为空、主清单 == 现场派生（272 条，含 `07-floating-point` 整册 50 例）**。

```text
make check-idl                                                      # L2：IDL + QEMU（不依赖 gem5/Verilator 构建）
python3 idl/tools/idl_four_way.py --platforms qemu,gem5,chipyard    # 全四方（收口 / 节点）
python3 idl/tools/idl_four_way.py --only ld.o_rrii_rd               # 单例诊断
```

`make check-idl` 在 `GATE_LOCKED_TARGETS` 内（与 L2/L3 串行）；缺 QEMU 安装根或 BootROM 固件即 ERROR。退出码：`0` 全一致 / `1` 有 FAIL / `2` setup·清单·输入错误 / `75` 共享构建树有活跃写者（writer-guard 拒绝，见 `docs/Process-07 §2.1`）。

逐指令 trace（`tools/idl_check_trace.py`，格式 [`docs/trace-format.md`](docs/trace-format.md)）**不进判据**：只在四方红例后用于归因（定位首个分叉指令/异常），不做逐指令全量门控。

> **import 本模块前设 `PYTHONDONTWRITEBYTECODE=1`**：`idl/` 由 `check-manifests-guard` 做**双向目录集合断言**，落 `__pycache__` 会直接判红（数据文件而非模块，正是为此）。

**语言与语义库正文见 [`spec/IDL-ISA语义描述语言与语义库.md`](../spec/IDL-ISA语义描述语言与语义库.md)**：§1 语法基线、§2 命名约定、§3 寄存器模型、§4 语义库（含 §4.7 浮点原语）、§5 语法扩展提案、§6 `idlc` 复用评估；变更记录见该册文末附录。原 README 的 §1–§7 已整段迁入该册（§1–§6 节号一一对应；§7 → 附录），本文件只保留目录导航与用法——旧文里的 `idl/README §N` 记号对应新册 §N。

**与 UDB 的差异盘点见 [`docs/diff-vs-udb.md`](docs/diff-vs-udb.md)**（263 条 operation 逐条判定 + 整改索引）。

> **待办**：`idl/.manifests.toml` 统一补 `sha256`（工具目录清单维护，不属规范正文）。
