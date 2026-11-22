# m17-idl-012: IDL 脚本/程序归拢到 `idl/` 并统一命名

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-011`（同在 `idl/` 上改动，须串行）
**可并行分片**：否
**预估**：2–4 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

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

1. `git mv` 上述 11 个程序 + 3 个数据 + 5 个文档（含 `docs/` 两件），按目标布局改名。
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

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
