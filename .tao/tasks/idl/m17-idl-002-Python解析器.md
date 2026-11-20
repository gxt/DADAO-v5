# m17-idl-002: IDL 解析器（Python，子集 → AST）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-001`（语法子集与宽度规则）
**可并行分片**：否
**预估**：3–5 天
**档位**：中改
**状态**：待验收

## 背景

`m17-idl-001` 会给出 `.idl` 实际使用的语法子集与出处。本任务只实现该子集，**不追求覆盖 652 行 treetop 的全语法**；语法真源仍是 UDB 的 IDL 语言规范（`spec/IDL-ISA语义描述语言与语义库.md`），本实现是它的**第二份实现**，靠 fixture 冻结行为防漂移。

## 目标

1. `tools/idl/`（或 `idl/pyparser/`）实现 parser：输入 `.idl`，输出 AST（节点类型与 `001` 的构造表一一对应）；
2. **全量解析 13 个 `.idl`**（12 册 + `lib/fp.idl`），operation 条数与 `render.py` 的 `# id:` 一致；
3. 新增 `make check-idl-parse`（L1 静态）：全量解析 + fixture 接受/拒绝集；
4. 不依赖 Ruby / gem / 网络。

## 验收（逐条贴真实 rc）

1. 263 条 operation 全量解析成功，条数由现场统计；
2. **拒绝集**：≥3 个语法错误样例必须报错（不是静默跳过）；
3. **漂移防护**：每个 operation 的构造签名冻结成 fixture，改动须显式更新；
4. **可达 FAIL ≥2 路**：① 删一个右括号 ⇒ 报错；② 改一条 operation 的 AST 节点 ⇒ fixture 红；
5. `render.py --check`、`check-idl-sync`、`check-knowledge-refs` 仍 rc=0（本任务不得影响渲染链路）。

## 约束

独立 `git worktree`；**不提交 git**；**不得改 `.idl` 与 `spec/`**；术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 完成区

**测试结果**：通过 27/27（一键证据脚本 = 运行期证据目录内的 `run.sh`，rc=0；日志在同目录 `logs/`）；`make check-idl-parse` rc=0。
- 全量解析 13 个源（12 册 + `idl/lib/fp.idl`）：operation **263**（现场统计 = `contracts/opcodes.yaml` 的 `- id:` 263 = `render.py --check` 的「源 operation=263」）、
  function 108、enum 3、全局常量 20；operation id 全在 opcodes 表内。
- 独立 oracle（源码正则 ⇔ AST 节点计数）：call 名字 **117** 个（= `syntax-subset.md` S41 的「117 个不同名字」）+ 7 类结构 × 13 源，逐项 0 差异。
- 拒绝集 13/13 按预期报错（子集外 `while`/`struct`/`sizeof`/`CSR[]`/复合赋值/变量作复制次数/自减、括号与花括号不配对、类型标注缺失、缺 `;`、function 段重复）；接受集 3/3 通过。
- 可达 FAIL 4 路（临时树注入，真实树 13 个源 md5 前后一致）：删右括号 ⇒ rc≠0 且报「期望 `)`」；改一条 operation 的 AST ⇒ fixture 红；
  注入 `while` ⇒ 报「不在子集内」；把解析器的 `ExprStmt` 改成丢 `Call` 节点 ⇒ 独立 oracle 红；还原新拷贝 ⇒ rc=0。

**修改文件**：新增 `idl/idl_parser.py`（词法 + 语法 + AST + fixture + 拒绝/接受集 + 注入自检）、`idl/idl_parse_cases.toml`（拒绝/接受集数据）、
`idl/idl_parse_fixture.json`（263 operation + 108 function + 3 enum + 20 常量的构造签名）；修改 `idl/.manifests.toml`（登记 3 个新文件）、
`idl/README.md`（目录表 / 用法 / import 注意）、`Makefile`（`check-idl-parse` + 进 `_locked-check` + `.PHONY` + help）、
`docs/Process-07`（§1.1 登记行 + §7 表行）、本任务书。**未动 `.idl` / `spec/`**，未改 `render.py` 渲染路径。**落点偏差披露**：任务书举例 `tools/idl/` 或 `idl/pyparser/`，实际放 `idl/` 扁平——与既有 `render.py`/`subset_stats.py` 同目录，避免为 3 个文件新开子目录（`idl/` 的 `subdirs` 由双向目录清单管，多一层只增登记面）。

**验收结果**（真实 rc）：`make check-idl-parse`=0；`idl/render.py --check`=0（263 条逐字节一致）；`check-idl-sync`=0；
`check-manifests-guard`=0（文件 58 / sha256 23 全符）；`check-knowledge-refs`=0。L1 逐目标实跑 57 项：**50 项 rc=0**，7 项环境性失败
（与本任务无关）：`check-isa-coverage`/`check-width-sizes`/`check-components`/`check-linux-toolchain`/`check-writer-guards` 缺安装根
（`missing tool: llvm-mc`，提示 `run make install-host first`）、`check-syscall-abi` 缺 linux 组件源码检出（未 `apply-series`）、
`check-temp-dirs` 报 `m14-*` 陈旧临时目录（只报告不删除，他任务目录）。

**新发现/坑**：
- `syntax-subset.md` 未单列 `true`/`false`（Boolean 字面量，25 处）与 `0s`（32 处）的构造行，`subset_stats.py` 也不统计（`0s` 并入 S39 正则、`true`/`false` 无行）。
  解析器按实际用法实现（`BoolLit` + 有符号字面量原文留档）；建议 001 补行，否则「AST ↔ 构造表一一对应」有缺口。
- `idl/` 有**双向目录集合**门控 ⇒ 任何 `import` 都会落 `__pycache__` 判红（门控自己弄脏树）⇒ 拒绝/接受集改 TOML **数据**文件，README 记 `PYTHONDONTWRITEBYTECODE=1`（实测：误 `import` 后本门控与清单门控同时红）。
- fixture 只证「AST 没变」（自比），不能证「没收错」⇒ 另加源码正则独立 oracle；实测 call 名字 117 与 S41 文档数字吻合（交叉印证）。
- 字面量一律只留原文与位宽标注（`U04`/`U07`）、`Bits<N>` 的 N 只留字符串、加宽/二元运算不推宽度 ⇒ 解析器对 `U04`–`U10` **零假设**。

**遗留问题**：① `U04`–`U10` 仍未裁定（解析器已避开；`m17-idl-003` 求值前必须取裁定）；② 建议 `m17-idl-001` 补 `true`/`false`、`0s` 构造行（本任务不改其文档与脚本）；③ L1 的 7 项环境性失败需 `make install-host` / 组件检出后复跑（本任务无编译输入变化，未重建）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行）

逐行审了词法/语法/AST/规范化/fixture/门控/自检七段，并按「可达 FAIL」逐路真跑。finding 与处置如下（均在同一轮内修完并复验）：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `::` 不在运算符表 ⇒ `Enum::Member` 解析失败 | ✅已修 | `_OPS` 加 `::`（长度降序，先于 `:`） | 13 源全解析；接受集 `EnumRef` 命中 |
| `?` 后缀只在紧跟 `(` 时归并 ⇒ `function is_sp_neg_inf? {` 失败 | ✅已修 | 词法规则扩到「`?` 后隔空格紧跟 `(` 或 `{`」 | 108 个 function 全解析（含 10 个 `?` 名） |
| `0s`（无撇号有符号字面量）被切成 `0` + `s` | ✅已修 | 新增 `RE_SIGNED_ZERO` + `literal_fields` 分支（只留原文） | `SimRISC-07` 10 处 / `fp.idl` 22 处解析通过 |
| `true`/`false` 被 `RESERVED` 拦成「关键字不能作表达式」 | ✅已修 | `parse_primary` 产出 `BoolLit`（S08 一类） | 25 处 Boolean 字面量解析通过 |
| `description` 块只发 `desc` token、不发 `description` ident ⇒ function 段识别失败 | ✅已修 | 先发 `ident("description")` 再发 `desc` | 3 个库文件枚举/函数段全解析 |
| 拒绝/接受集原为 Python 模块：`import` 落 `__pycache__` ⇒ `check-manifests-guard` 判红 | ✅已修 | 改为 TOML 数据文件（`tomllib` 标准库），解析器不再 import 任何本目录模块 | `check-manifests-guard` rc=0；证据脚本第 9 项断言无 `__pycache__` |
| fixture 与解析器同源（自比）⇒ 只能证「没变」 | ✅已修 | 新增独立 oracle：源码正则统计（与 `subset_stats.py` 同口径抹注释/散文）⇔ AST 节点计数 | 0 差异；call 名字 117 = S41 |
| `parse_function` 重复段静默「后者覆盖前者」 | ✅已修 | 四段各加重复检测并报错 | 新增拒绝样例 `duplicate-function-section`（报「`returns` 段重复」），13/13 全过 |
| `parse_simple_stmt` 用 `self.toks[self.i-2]` 反查 `++` token（脆弱） | ✅已修 | 捕获 `optok = self.take()` | `--check` PASS；`Incr` 计数与源码 `++` 一致（oracle） |
| `parse_type` 两处重复同文案条件 | ✅已修 | 合并为单一条件 | 拒绝集 `bits-without-width` / `missing-type-annotation` 仍按预期报错 |
| 拒绝/接受集可被删薄（剩 1 条也过） | ✅已修 | `load_cases` 加下限（拒绝 ≥3、接受 ≥2）并报错 | 临时树删到 3 条仍过（= 门槛）；删到 2 条即红（手动验后还原） |
| `--check` 只核 operation 条数，未核 id 成员 | ✅已修 | 加 `id ⊆ opcodes.yaml` 断言（条数 + 成员双向） | 临时树把一条 id 改坏 ⇒ 报「operation id 不在 contracts/opcodes.yaml」 |
| 给 `"` 加友好报错时误把 `for … else` 的 else 分支改成顺序执行 ⇒ 任何运算符 token 都报错 | ✅已修 | 改用显式 `matched` 标志 + `continue` | `--check` 当场红（13 源全失败）→ 修后 rc=0；字符串/`include` 仍按预期报错 |
| `n_books` 用字符串包含判断册/库 | ✅已修 | 改 `startswith(LIB_REL + "/")` | 输出「册 12 + 库 1」 |

### 第 1 轮 reviewer 验收（中改档；判据全部现场重跑，不采信完成区）

**重跑记录（本人真实输出 / 退出码）**
- 运行期证据目录内的 `run.sh` ⇒ `EVIDENCE: PASS（27/27 项检查通过）`、`EXIT=0`（内含 `idl_parser.py --check`/`render.py --check`/`check-idl-sync`/`check-manifests-guard`/`check-knowledge-refs`/`make check-idl-parse`/`--self-test` 全 0，注入 4 路各自非零）。
- 拒绝集逐条独立核（`python3 -B` 直调 `parse_text`，绕过门控汇总）：**13/13 真报错且类别相符**，例 `unbalanced-paren …3:18: 期望 \`)（实得 \{\``、`missing-semicolon …期望 \`;（实得 <eof>`、`duplicate-function-section: returns 段重复`；**另造 2 条未覆盖非法输入**：`assert(…)` ⇒ `构造不在子集内：assert（S61）`、`include "lib/fp.idl";` ⇒ `字符串字面量不在子集内`，均报错、未被当合法。
- 接受集 **3/3 通过且非空**（`ops=1/1/0`、kinds 18/17/16，`must_kinds` 无缺）；随机抽 3 条真实 operation（seed=20261120：`shr.sb_orrr_rd`/`div.uw_orrr_rd`/`fornd_orri_rf`）⇒ nodes=43/49/45 非空。
- 263 三处自洽：`grep -c '^- id:' contracts/opcodes.yaml`=**263**；`grep -h '# id:' idl/*.idl idl/lib/*.idl | wc -l`=**263**；`idl/render.py --check` ⇒ `源 operation=263 条 … 逐字节一致` rc=0；另**不经解析器**的 id 集合 `diff` 双侧 263 项完全一致。
- 可达 FAIL 自跑 **3 路**（临时树 + `cp` 备份/md5 还原，未用 `git checkout`）：① 删右括号 ⇒ `idl-parse: FAIL —— idl/SimRISC-01.idl:3:18: 期望 \`)（实得 \{\``、rc=1；② 合法加一行改 AST ⇒ `operation.ld.o_rrii_rd: AST 摘要变了（fixture 4863e9294227 ≠ 现场 e6dd8778ca73）`、rc=1；③ 改解析器 `Incr` 节点名 ⇒ 独立 oracle 红 `` `++` 源码 19 处 ⇔ AST 0 个 `Incr` 节点``、rc=1；三路还原均 rc=0 且 md5 与注入前相同。
- L1 接线 + 非恒真：`check-idl-parse` 在 `_locked-check` 成员表、`.PHONY`、`help`、目标体共 4 处；临时树 `make check-idl-parse` 基线 rc=0 ⇒ 注入坏 `.idl` ⇒ `make` rc=2（`期望 \`)`），还原 rc=0。
- 语义零假设抽 3 处代码：`literal_fields`（`0s`→`width=None`，Verilog 位宽只留字符串组、全文件无 `int(` 位宽转换）；`parse_type` 的 `BitsType(width=wid.text)`（`Bits<N>` 的 N 只留字符串）；`parse_binary` 仅组 `Binary(op,left,right)`（不推结果宽度/截断）——另 `Replicate.count` 也是原文 `IntLit`，未见 U04–U10 任何内置假设。
- 真实门控 rc（各跑 ≥2 次）：`check-idl-parse`/`check-idl-sync`/`check-manifests-guard`/`check-knowledge-refs`/`render.py --check` **全 0**；范围 `git show --name-only HEAD` **恰 8 文件**、未动 `.idl`/`spec/`；`idl/.manifests.toml` `files` 21 项 + `subdirs=["lib"]` 与目录集合一致。审查前后 `git status --porcelain -uall` 均为空、目标文件 md5 四项逐一相同、`idl/` 全程无 `__pycache__`。

**两条自报 finding 判真伪**
- `syntax-subset.md` 缺 `true`/`false` 构造行：**证真**（全文无 `true/false`、`subset_stats.py` 亦无行，AST `BoolLit`=24）；`0s` **半真**——S39 行标题与正则已含 `0s`（32 处并入合并计数 48），只是未单列 ⇒ `ISS-479` 成立（重点在 `true/false`）。
- `idl/` 落 `__pycache__` ⇒ 清单门控判红：**证真**（临时树造 `idl/__pycache__/*.pyc` ⇒ `ERROR: idl: 多出子目录 __pycache__（未在 subdirs 中登记）`、`check-manifests-guard` rc=2；删后 rc=0）⇒ `ISS-480` 成立。

**Findings（文档级/落点级，不阻断，交 architect 收尾）**
1. 完成区「Boolean 字面量 25 处」实测 **24**（AST `BoolLit`=24；全量词形 26 含 2 处行尾注释）——数字笔误，请改正。
2. 落点：任务书举例 `tools/idl/` 或 `idl/pyparser/`，实际 `idl/` 扁平（已披露、已进清单与 README，与 `render.py`/`subset_stats.py` 同目录）——请 architect 终审裁定是否维持。
3. `--self-test` 的临时树用 `mkdtemp(prefix="idl-parse-")` 建在系统 opencode 临时根下、未套任务号子目录（`finally` 自清）——建议后续收进任务号子目录。

**约束核验**：独立 worktree 作业、未提交 git、未改 `.idl`/`spec/`、完成区无具体运行期路径、术语「寄存器组」——均守住；本轮审查未改任何代码，注入全部走临时树 + `cp`/md5 还原。

**判决：Accepted**（验收 5 条与核心判据 1–9 在本人重跑下全部通过；3 条 finding 为文档级/落点级，不改验收结论）。
