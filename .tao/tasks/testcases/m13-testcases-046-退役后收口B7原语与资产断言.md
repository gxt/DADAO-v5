# m13-testcases-046: 退役后收口（B7 spec 原语 + 资产断言 + 退役依据入仓）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-043`（YAML 全退役，已合 `02fb657b`）、`m13-testcases-044`（三探针退役，已合 `07499170`）
**可并行分片**：否
**预估**：1.5–2 h
**状态**：待开始

## 背景（三处「退役留尾巴」）

1. **`oracle_{fma,minmax,rnd}.py` 悬空**：三探针已退役，但三个 oracle **没删** —— `tools/gem5/b7_ref.py` 在**模块顶层 import** `oracle_fma` 的 `classify/floor_log2/encode`，且 `--selftest` 用三 oracle 作三实现互证。删了会**静默破坏** gem5 B7（无门控覆盖，不会变红）。定位也不对：它们已不是「测试 oracle」，而是**spec 精确算术原语**，却留在 `tools/testcases/`。
2. **`tools/gem5/check_b7.py::asset_check` 已整体失效**：它断言 4 条只读资产 —— `tests/inst/{fma,minmax,roundint}/`（044 已删）与 `tests/inst/fp/scaleb.yaml`（043 已删，且**派单前就已缺**），并用 `scaleb.yaml` 正文核 `rdHD` 口径。结果：**必然 4 条 missing + 后续 crypto 检查全失效**（工具不在任何 make 门控里，所以没人发现）。
3. **044 的退役依据只在运行期**：`coverage-matrix.tsv`（决定删 3 个探针目录、9 个 id 的那张表）只存在于运行期证据目录 ⇒ 退役理由在 fresh clone 上**不可审计**（违「被引用的材料一律不得只放 `.work/`」）。

## 范围

### A. B7 spec 原语（R1，选项 A）

- 三个 oracle 迁到 `tools/testcases/lib/` 作**共享 spec 精确算术原语**，命名脱出「oracle」定位（如 `fp_spec_arith.py` + `fp_spec_minmax.py` + `fp_spec_rnd.py`，或一个模块三个子域，由你按现有代码结构定，但**不得复制粘贴两份**）；
- `tools/gem5/b7_ref.py` 改引用新位置；
- **保留** `--selftest` 的三实现互证（**不得**把原语内联进 `b7_ref`：内联后 selftest 变自比恒真，违「禁同源自比」）；
- 新位置顶部注明「本模块是 **spec 精确算术**（`spec/SimRISC-07`），**不是测试判据**；测试判据一律是 `.S` 内联期望」。

### B. `check_b7.py::asset_check` 收敛（F4）

- 4 条已删资产的断言改为**对 `.S` 载体的断言**（例：`tests/inst/07-floating-point/ftsclb*.S` 存在且含 `rdHD` 口径；`ftfma`/`ftmin`/`ftmax`/`ftrnd` 载体存在）；
- **不得恒真**：删掉/改坏载体 ⇒ 必须红（自己注入验证）；
- 与 `scaleb.yaml` 正文强绑定的 crypto 检查：改用 `.S` 载体或明确移除并在文件头写明「原资产已退役，判据迁至 `.S`」。

### C. 退役依据入仓

- `coverage-matrix.tsv` 入仓为 `.tao/knowledge/refs/m13-044-probe-coverage.tsv`，**同时订正 044 reviewer 指出的两处措辞**：
  - F2：「picolibc 无 minmax 自测」不准确 —— `test-math-errhandling-tests.c` 有 12 条 `fmin/fmax` 值+异常断言（但该套件现 `FAIL exit 3` 且有既有问题，且**不覆盖**次正规/±Inf/±0 序 ⇒ 补点仍成立），改成准确表述；
  - F3：「18 行」含表头（capability 行 17）、`GAP-记账` 严格为 1；
- 文件头加 3–5 行：来源（`m13-testcases-044` 阶段 A 现场）、结论（退役 3 探针 + 3 个 L3 门控；缺口 34 点已补进 `.S`）、不可复现说明（原始运行期证据已清理）。

## 验收（逐条贴真实 rc）

1. `git ls-files tools/testcases/lib | grep fp_spec` 显示新模块；`tools/testcases/oracle_{fma,minmax,rnd}.py` 不存在；`grep -rn "oracle_fma\|oracle_minmax\|oracle_rnd" tools/ tests/ Makefile` = 0（`.cache/refs/**` 与历史任务书/`docs/` 历史报告不改写，需在完成区列出例外）；
2. `python3 tools/gem5/b7_ref.py --selftest` rc=0（三实现互证仍成立，贴关键计数）；`python3 tools/gem5/check_b7.py --vectors`（或等价）rc=0 且**不再报 missing asset**；
3. **可达 FAIL**：删一个 `.S` 载体 ⇒ `check_b7.py` 红；还原 ⇒ 绿（`cp`+md5）；
4. `b7_ref` 引用的模块**有 L1 静态断言**（如 `check-writer-guards` 或 `check-dirs` 里的存在性断言，或新增一条最小静态检查），且该断言可达 FAIL（临时改坏路径验证）；
5. `.tao/knowledge/refs/m13-044-probe-coverage.tsv` 入库，`check-knowledge-refs` rc=0；
6. `check-inst-asm`、`check-tests-index`、`validate-vectors`、`check-case-ledger`、`check-no-residue` rc=0（本任务**不改**任何 `.S`，计数必须与合入前**逐字相同**：265 id / 901 镜像 / 检查点 4132）；
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`/`issues.yaml`。

## 硬约束

- 只改 `tools/testcases/lib/**`、`tools/testcases/oracle_{fma,minmax,rnd}.py`（删）、`tools/gem5/{b7_ref.py,check_b7.py}`、`.tao/knowledge/refs/m13-044-probe-coverage.tsv`、本任务书；
- **不改任何 `.S`**（并发任务 `m13-testcases-037`/`045` 正在改 `tests/inst/**`）；
- `m16-gem5-005` 可能在改 `components/gem5/**`：你只碰 `tools/gem5/` 下那两个文件，若合并冲突由主会话处置；
- 禁 `install-host`/`check-modules`/`build-*`；禁边构建边测试；不 sync/reset 节点；
- 不提交 git；禁 `git checkout/restore/stash`（注入还原 `cp`+md5）。

## 待裁定

（实现中写）

## 审阅记录

（待填）
