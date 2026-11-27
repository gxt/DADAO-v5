# m17-idl-012: IDL 脚本/程序归拢到 `idl/` 并统一命名

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-011`（同在 `idl/` 上改动，须串行）
**可并行分片**：否
**预估**：2–4 h
**档位**：大改（复核 ≤60 min）
**状态**：已验证

## 背景（用户 2026-11-22 定）

「IDL 需要用的脚本和程序统一放到 `idl/` 目录下，文件名需要规范。」

现状是散的：IDL 自有程序分在 `idl/`（`render.py`/`subset_stats.py`/`idl_parser.py`/`idl_exec.py` 扁平）、`tools/idl/`（7 个驱动）、`tools/chipyard/fp_ref.py`（FP 参考库，阶段二要用）；数据 3 件在 `idl/` 根；文档 3 件在 `idl/` 根、2 件在 `docs/`。

## 目标布局（落点写死）

```text
idl/
  SimRISC-01..12.idl        # 不动：被 55 处引用
  lib/fp.idl                # 不动
  README.md  .manifests.toml
  tools/
    idl_render.py           # ← idl/render.py
    idl_subset_stats.py     # ← idl/subset_stats.py
    idl_parser.py           # 原位迁入
    idl_exec.py             # 原位迁入
    idl_fp.py               # ← tools/chipyard/fp_ref.py
    idl_four_way.py         # ← tools/idl/check_four_way.py
    idl_exec_parity.py      # ← tools/idl/check_exec_parity.py
    idl_qemu_state.py       # ← tools/idl/qemu_final_state.py
    idl_exec_trace.py       # ← tools/idl/exec_trace.py
    idl_qemu_trace.py       # ← tools/idl/qemu_trace.py
    idl_trace_common.py     # ← tools/idl/trace_common.py
    idl_check_trace.py      # ← tools/idl/check_trace_parity.py
  data/
    idl_parse_cases.toml    # ← idl/idl_parse_cases.toml
    idl_parse_fixture.json  # ← idl/idl_parse_fixture.json
    idl_exec_cases.toml     # ← idl/idl_exec_cases.toml
  docs/
    syntax-subset.md  width-rules.md  diff-vs-udb.md
    four-way.md             # ← docs/idl-four-way.md
    trace-format.md         # ← docs/idl-trace-format.md
    trace-sample.jsonl      # ← docs/idl-trace-sample.jsonl
```

命名词典：Python 一律 `idl_` 前缀 + 小写下划线、模块名 = 文件名；数据 `idl_*.toml/json`；`idl/docs/` 内文档用语义名（不再重复 `idl-` 前缀）。**不留转发壳**（与 `m15-testcases-011` 同口径）。

## 要做

1. `git mv` 上述 12 个程序 + 3 个数据 + 6 个文档（含 `docs/` 两件），按目标布局改名。
2. 路径真源：程序统一按「仓库根 = `Path(__file__).resolve().parents[3]`」定位（12 个程序同深度）；若判断重复过多，可加一个 ≤20 行的 `idl/tools/idl_paths.py`，禁止各写一套不一致的常量。
3. 改 `Makefile`：`check-idl-sync`/`check-idl-parse`/`check-idl` 三条目标的脚本路径与 help 文案（**目标名不变**）；`IDL_FOUR_WAY_LOG` 不变。
4. 改清单与门控登记：`manifests/dir-guard-roots.toml` 加 `idl/tools`、`idl/data`、`idl/docs`；`idl/.manifests.toml` 的 `subdirs` 扩为 `lib/tools/data/docs`；三个新子目录各建 `.manifests.toml`。
5. 引用清扫（operational 面）：`docs/README.md`、`idl/README.md`（全部用法示例）、`components/chipyard/README.md` 与 `docs/fp-oracle-design.md` 的 `fp_ref` 指路、`tools/chipyard/**` 里 `import`/路径、`spec/IDL-ISA语义描述语言与语义库.md` 若有示例路径；历史任务书与 `.tao/archive/**` 不改。
6. 顺带订正 `m17-idl-011` 披露的 4 处旧措辞（`idl/syntax-subset.md`、`idl_parser.py` docstring、`idl/README.md`、`idl_exec.py`）：「`U04`–`U10` 未定义」→「见语言规范册 §1.1」。
7. `.idl` 源、语义、清单内容、执行行为**零改动**。
8. `docs/Process-07` 补登 `check-idl`（L2 行 + §7 表行）——阶段一漏登记。

## 不做

- 不加语义、不改 `.idl` 源、不改 `tests/`、不改组件补丁；
- 不改门控目标名/日志路径；不改历史任务书。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- `idl/` 内不得出现 `__pycache__`（`check-manifests-guard` 双向集合断言）；
- 只动上述文件 + 本任务书；完成区 ≤30 行、不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-idl-parse check-idl-sync check-idl` 全部 rc=0（`check-idl` 应仍 222/222）；`python3 idl/tools/idl_subset_stats.py --check` rc=0；
2. `check-manifests-guard`、`check-dirs`、`check-knowledge-refs`、`check-no-residue` rc=0；
3. **可达 FAIL ≥2 路**：① 从 `dir-guard-roots.toml` 删 `idl/tools` ⇒ manifests 门控红；② 在 `idl/README.md` 留一处旧路径 `tools/idl/check_four_way.py` ⇒ `check-knowledge-refs`/`check-dirs` 红；均 `cp`+md5 还原后回绿；
4. operational 面 `grep -rn "tools/idl/\|tools/chipyard/fp_ref"` 命中 0（排除 `.tao/archive/**`、历史任务书、本任务书）；
5. 行为不变：`make check-idl` 222/222；`idl_parser --check`、`idl_exec --self-test` 按原口径通过。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` ALL PASS（rc=0，20 项检查）；`make check-idl` 222/222；`idl_render/parser/subset_stats --check`、`idl_exec --self-test`、`idl_exec_trace --self-test`、`idl_fp selfcheck` 全 rc=0；`idl_exec_parity` 2/2、`idl_check_trace` 2/2（临时 `id` 口径清单）实测通过。

**修改文件**：11 程序 + 3 数据 + 5 文档 `git mv` 到 `idl/{tools,data,docs}/`（`fp_ref.py`→`idl_fp.py` 等 12 项改名）；新增 `idl/tools/idl_paths.py` + 三份子目录 `.manifests.toml`；`idl/.manifests.toml`、`manifests/dir-guard-roots.toml`、`Makefile`、`idl/README.md`、`idl/docs/*.md`、`idl/data/*.toml`、`idl/data/idl_parse_fixture.json`（仅 note）、`docs/README.md`、`docs/Process-06`、`docs/Process-07`、`docs/DDLN/.../DD-Y006`、`docs/fp-oracle-design.md`、`components/chipyard/README.md`、`tests/shared/README.md`、`README.md`、`tools/chipyard/fp_unit/unit_run.py`、本任务书。

**验收结果**：`make check-idl-parse check-idl-sync check-idl` rc=0，末行 `check-idl: PASS`、`check_four_way: 222/222`；`check-manifests-guard` 10 清单/86 文件/36 sha256 PASS；`check-dirs`、`check-no-residue` PASS；`idl/` 无 `__pycache__`；旧路径 operational 面命中 0。注入：删 `idl/tools` 注册 ⇒ manifests rc=1「游离清单」；README 注入旧路径 ⇒ refs rc=1；`cp`+md5 还原后均回绿。

**新发现/坑**：① `check-knowledge-refs` 基线红：`ADR-0059` 未立册（MEMORY/milestones-m18 各 1 处），与本任务无关，按「错误集与基线逐行相同」记 KNOWN-RED；② 任务书设想的「README 旧路径 ⇒ check-knowledge-refs/check-dirs 红」不成立（两门控均不扫 README），故 ② 由证据脚本的 operational 引用清扫承接（可达 FAIL）；③ `spec/` 的 263 个生成标记仍写 `idl/render.py`（`GENERATED_NOTE` 随 spec sha256 锁冻结），改名须另立「重渲染 spec + 更新 `spec/.manifests.toml`」授权任务；④ 既有 `idl_check_trace --cases` 期望 `id` 键而主清单是 `image`（任务前既有，未改）。

**遗留问题**：① spec 内 263 处生成标记与 `spec/README.md`/语义册的 `idl/render.py` 旧串待 spec 锁刷新任务；② `idl_check_trace` 默认清单键不一致（`id` vs `image`）为既有缺陷，未在本任务修；③ `make check-knowledge-refs` 需先补 `ADR-0059` 才能整体回绿。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 13 个 `idl/tools/*.py`、清单、Makefile 与文档改动；finding 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 路径深度：任务书写 `parents[3]`，但 `idl/tools/x.py` 的仓库根是 `parents[2]` | ✅已修 | `idl_paths.py` 统一定义 `REPO = tools→idl→根`；四个导入者共用 | 13 个程序 `--help` rc=0；render/parse/subset/exec 全 PASS |
| `from idl_paths` 会生成 `idl/tools/__pycache__`（manifests 双向断言会红） | ✅已修 | 四个导入者在 import 前 `sys.dont_write_bytecode = True`；`unit_run.py` 导入 `idl_fp` 前同设 | `find idl -name __pycache__` 空；manifests PASS |
| 任务书设想「README 旧路径 ⇒ check-knowledge-refs/check-dirs 红」不成立 | ✅已核实 | 两门控均不扫 README；证据脚本以 operational 引用清扫承接第二路可达 FAIL | 注入旧路径 ⇒ refs rc=1；还原回绿 |
| `spec/` 内 263 个生成标记仍写旧渲染器路径 | ⏸延后 | 该串被 spec sha256 锁冻结，改需重渲染 spec + 更新清单（另立授权任务） | 已记入「新发现/坑」与「遗留问题」 |
| `idl_check_trace --cases` 期望 `id`、主清单用 `image` | ⏸延后 | 任务前既有缺陷，不属本任务范围 | 用临时 `id` 口径清单实测 2/2 PASS |

判决：无未修 finding ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录**（均在仓库根执行，rc 取被检命令自身）：

- 运行期证据目录内的 `run.sh` → `ALL PASS`，**rc=0**（20 项，含 2 路注入→FAIL→还原→回绿）
- `make check-idl-parse` **rc=0**（`idl-parse: PASS`，拒绝+接受 16/16）；`make check-idl-sync` **rc=0**（`idl-render: PASS`，标记块 263 逐字节）；`make check-idl` **rc=0**（`check_four_way: 222/222`、`check-idl: PASS`）
- `make check-manifests-guard` **rc=0**（清单 10 / 目录 10 / 文件 86 / sha256 36；23+12+1=36、各清单登记数相加=86，现场计数自洽）；`make check-dirs` **rc=0**；`make check-no-residue` **rc=0**；`python3 idl/tools/idl_subset_stats.py --check` **rc=0**（`subset-stats: PASS`）
- `make check-knowledge-refs` **rc=2**：仅 2 悬空 `ADR-0059`（MEMORY.md / milestones-m18.md 本任务未改、HEAD 无该 ADR）⇒ 基线红属实，非本任务引入

**独立注入**（`cp`+md5，非采信 run.sh）：① `dir-guard-roots.toml` 删 `"idl/tools",` ⇒ manifests **rc=1**「游离清单」，还原 md5 `5111ee36…` 一致、回绿 rc=0；② `idl/README.md` 追加旧路径 ⇒ 引用清扫命中 1 行（红），还原 md5 `36007011…` 一致回绿——**实测 `check-dirs` rc=0 不红**（knowledge-refs 输出亦不变），即任务书验证③-② 所设想门控根本不扫 README，engineer 已披露并由 operational 清扫承接，属如实改道非规避。注入前后 `git status --porcelain -uall -M` 快照 md5 均 `bf3ccab4…`（39 行）无净残留；`idl/` 无 `__pycache__`（我中途 import 造出的 pyc 已删）。

**约束核验**：rename 21 / 修改 14 / 新增 4，**无 D+A 对**；`tools/idl/`、`tools/chipyard/fp_ref.py`、`idl/{render,subset_stats,idl_parser,idl_exec}.py`、`docs/idl-*` 均已不存在，**无转发壳**；目标布局 22 件全在位；12 程序根推导逐个执行验证均落仓库根（4 个走 `idl_paths.REPO`、5 个内联 `parents[2]` 同值、3 个不需根；无裸相对路径）；`SEMANTICS=213`；Makefile 三条 target 只改脚本/文案，目标名与 `IDL_FOUR_WAY_LOG` 与 HEAD 逐字相同；`Process-07` L2 行 + §7 表已登 `check-idl`；`idl/.manifests.toml subdirs=["lib","tools","data","docs"]` + 三份子清单 + dir-guard 10 根；operational 面旧路径 grep **命中 0**（余命中仅 archive/历史任务书/issues.yaml/changelog/本任务书）；非注释代码变更仅路径/导入/报错前缀/`dont_write_bytecode`，无逻辑改动；`tests/inst`、`.idl` 源、语义、QEMU/gem5/RTL、`spec/` **零改动**；完成区 39 行与 `git status` 逐行对账一致，无越界。

**遗留核实**：① `spec/SimRISC-*.md` 内 `idl/render.py` 生成注记 **263 处**（另 README、语义册各 1），`GENERATED_NOTE` 未改、spec 被 23 条 sha256 锁 ⇒ 属实（须重渲染+更新清单另立授权任务）；② `idl_check_trace.load_cases` 仍强制 `id`/`category`、主清单用 `image`，HEAD 同段同逻辑、HEAD 清单同键 ⇒ 任务前既有，属实。

**findings（均不阻断）**：F1 `idl_fp.py` 与原 `fp_ref.py` **md5 不同**（`9d816270…` vs `2dde91ff…`），diff 仅 4 行注释/用法串——逐字节相同与「引用清扫旧路径」互斥，代码零改动、gates 全绿，可接受；F2 完成区/任务书「11 程序+3 数据+5 文档」实为 **12+3+6（21 项 rename）**，文档数字笔误；F3 路径真源未收拢到单一模块（4+5 分裂，取值一致）；F4 `docs/fp-oracle-design.md` 把历史 `tools/golden/fp_ref.py` 指路改写为 `idl/tools/idl_fp.py`（`tools/golden` 本不存在，属任务书点名的指路清扫）。

**判决：Accepted** —— 验收命令在本人重跑下全部达标（`check-idl` 222/222、两路独立注入均可达 FAIL 并回绿、快照无净差异），两条遗留经核属实；F1–F4 留 architect 收尾处置。
