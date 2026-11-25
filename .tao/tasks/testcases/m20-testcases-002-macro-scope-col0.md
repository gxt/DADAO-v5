# m20-testcases-002: `check-inst-macro-scope` 与扫描器接受列 0 断言行（ISS-461）

**模块**：testcases
**项目里程碑**：M20
**依赖**：无
**可并行分片**：否（两个扫描器 + 一个自检）
**预估**：1 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景（M20 分诊，2026-11-25）

`ISS-461` 记录 `check-inst-macro-scope` 的 S8（已整例宏化的 `.S` 正文不得再有裸
`__CHECK_*`）只用行首 `\t` 作为识别边界；`llvm-mc` 实测接受列 0 的宏调用/指令，
因此列 0 的裸断言行可以绕过 S8 与用例扫描器。当前仓库列 0 断言行数为 0，
属**潜在漏检**，不是现存红。

现场复核：

- `BARE_CHECK_RE` 对 `__CHECK_RD 1, rd5, 0x0`（列 0）不匹配；
- `run_inst_tiny.CHAIN_CASE_RE` 对列 0 的 `TEST_LD ...` 不匹配；
- `check_inst_macro_scope.py --selfcheck` 当前 PASS，但自检只用 Tab 缩进样例。

## 目标

1. S8 与用例扫描器统一为「允许缩进或列 0」，不放松其它判据。
2. 自检新增一条列 0 裸断言注入：注入即 FAIL，还原即 PASS。
3. 新增一条列 0 的链例/宏调用扫描断言，证明 `run_inst_tiny` 现场计数不因列 0
   而漏例；不得改动 `.S` 向量本身。

## 验收（逐条贴真实 rc）

1. `python3 tools/testcases/check_inst_macro_scope.py --selfcheck`：新注入路径
   真实 FAIL、还原后 PASS；原有 12 类注入全部保持 PASS。
2. `python3 tools/testcases/check_inst_macro_scope.py`：基线 rc=0（当前列 0
   违规数为 0，修复不应引入新红）。
3. `run_inst_tiny.scan_source` 在临时副本上对列 0 的 `TEST_*` 行现场计数，
   与 Tab 缩进副本一致；给出两份输出的对照。
4. `check-inst-asm`、`check-tests-index` 真 rc；`check-patch-tree` 总 rc 受在途
   任务影响时按「本任务未触碰组件补丁」披露。
5. **可达 FAIL**：把列 0 支持改回 `^\t` ⇒ 新自检注入回红；`cp` + md5 还原后回绿。

## 约束

独立 `git worktree`（分支 = `m20-testcases-002`）；不提交 git；只改
`tools/testcases/check_inst_macro_scope.py`、`tests/ee-tiny/run_inst_tiny.py`
与本任务书；不改 `.S` 用例、`components/**`、`spec/`、契约、`Makefile`。
证据落在「运行期证据目录内的 `run.sh`」，不写具体构建/临时路径。

## 完成区

**测试结果**：通过 10/10（证据脚本全量，rc=0）；`--inject` 1/1；失败原因：无
**修改文件**：
- `tools/testcases/check_inst_macro_scope.py`（S8/`__PT_*` 用例行/宏体断言行前缀改 `[ \t]*`；自检新增列 0 S8 注入与列 0↔Tab 的 `scan_source` 对照）
- `tests/ee-tiny/run_inst_tiny.py`（`CHAIN_CASE_RE`/`CHAIN_PT*`/`FAULT_*`/`END_RE` 前缀改 `[ \t]*`）
- 本任务书（状态 / 完成区 / 自审）
**验收结果**（运行期证据目录内 `run.sh` 的真实 rc）：
1. `--selfcheck` rc=0：17 项全 PASS（含新增的「列 0 的 `__PT_*` 用例行」「正文列 0 的裸 `__CHECK_MEM`」「列 0 扫描 == Tab 扫描」）；注入回 `^\t` 后新 S8 项提示 `rc=0 期望 1`、列 0 扫描项 `checks=0` vs Tab `checks=3` → FAIL，cp+md5 还原后回绿
2. 门控 `check_inst_macro_scope.py` rc=0：基线列 0 违规 0，无新红；统计与改前一致（共享层 22 / 已宏化 13 文件 / 用例行 228）
3. `scan_source` 列 0 副本 vs Tab 原件：`ld.o_rrii_rd.S` 21/21 checks、4/4 faults、pts_ok True；`sc.b.ar_orrr_rd.S` 16/16、1/1；两份列 0 副本 `llvm-mc` rc=0
4. `make check-inst-asm` rc=0（274/274 镜像、632 例）；`make check-tests-index` rc=0；`make check-case-ledger` rc=0
5. `make check-patch-tree` rc=2（20 problem：musl/linux/gem5 补丁基线/在途红），本任务未触碰 `components/`、`manifests/`，按「未触碰组件补丁」披露，非本任务引入
6. 可达 FAIL：注入 `^[ \t]*` → `^\t`（两文件 md5 均变）⇒ selfcheck rc=1 且两个新项各自 FAIL、scan 对照 DIFF；`cp` 还原后 md5 与改前逐字节一致、selfcheck/scan rc=0

**新发现/坑**：
- `check_case_ledger` 复用 `run_inst_tiny` 的同一组正则 ⇒ 前缀一处改动由 L2/L1 共用，无需另改（其 rc=0 已复验）
- 只放松 `CHAIN_CASE_RE` 会「计数对但点号 −1」⇒ `pts_ok=False`；列 0 支持必须整组（含 `CHAIN_PT*`/`FAULT_*`/`END_RE`）同改
- 宏体断言正则原为 `^\s+`，同样排除列 0（S6/S7/S9 可被列 0 断言绕过）；一并改 `[ \t]*` 属收紧，改前/改后 274 个 `.S` 的 `scan_source` 结果逐字段一致
- 任务 worktree 需自建 `.dadao` 软链（共享安装根），否则 L2 门控报「not found」假红

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**判决**：可交付（无未修 finding）。自审方式：自主逐行审查 `git diff` + 重跑证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 1. 只放松 `CHAIN_CASE_RE` ⇒ 列 0 用例计数对但点号 −1 | ✅已修 | `CHAIN_PT_RE`/`CHAIN_PT_PT_RE`/全部 `FAULT_*`/`END_RE` 同改 `[ \t]*` | 列 0 副本 pts_ok=True、全字段等于 Tab 副本 |
| 2. 已宏化文件判定依赖 `PT_CASE_LINE_RE`，只改 `BARE_CHECK_RE` 仍漏 | ✅已修 | `PT_CASE_LINE_RE` 同改；新注入把唯一 `__PT_*` 行与裸断言**都**放列 0（两项同时承重） | 注入回 `^\t` ⇒ 新 S8 项 FAIL |
| 3. 宏体断言 `^\s+` 排除列 0，S6/S7/S9 可被绕过 | ✅已修 | `COUNTING_ASSERT_RE`/`ANY_ASSERT_RE` 改 `[ \t]*`（收紧非放松） | 门控 rc=0；改前/改后 274 `.S` 的 scan 逐字段一致 |
| 4. 新自检可能空转（0==0 假绿） | ✅已修 | 断言列 0 用例行确在列 0、`checks>0`、三字段等于 Tab 副本 | 正常 3 vs 3；注入后 0 vs 3 → FAIL |
| 5. 文档写死「12 类注入」与实际不符 | ✅已修 | docstring/help 改「各类注入」，末尾现场打印项数 | 实测输出 `PASS（17 项）` |
| 6. 证据脚本「注入后任何红」都可能假绿 | ✅已修 | 注入后分别 grep 两个新项的 `→ FAIL`，并校验两文件 md5 均变、还原 md5 等于改前 | `--inject` 两行 FAIL 命中；md5 `f52f3280→c9b46730→f52f3280`、`32cf36ea→e6c25ef9→32cf36ea` |

补充逐行核对：正则只改行首前缀、断言主体（点号/操作数/故障名）未动；`[ \t]*` 不吞换行，多行匹配行为不变；`nrun` 计数与打印项数一致（17）；证据脚本还原走 `cp -p` + md5 对账，未用 `git checkout`/`restore`。

#### 第 1 轮 reviewer 验收

**判决**：**Accepted**（1 条非阻断 finding，见末尾）。以下均为 reviewer 亲跑输出，未采信工程师叙述。

**重跑记录**
1. `python3 tools/testcases/check_inst_macro_scope.py --selfcheck` → rc=0，`selfcheck PASS（17 项）`；两项新注入真实承重：`正文列 0 的裸 __CHECK_MEM（ISS-461）…→ PASS`、`列 0 扫描 == Tab 扫描: 列 0 checks=3 faults=1 pts_ok=True / Tab … → PASS`。
2. `python3 tools/testcases/check_inst_macro_scope.py` → rc=0，统计 `共享层宏 22 / 已宏化 .S 13 个（用例行 228 行）`，与 HEAD 版（`git show` 取出在临时树跑）逐行一致且同为 rc=0 ⇒ 未引入新红。
3. 临时副本独立 scan 对照（reviewer 自写，非工程师脚本）：`ld.o_rrii_rd.S` 移列 0 26 行，Tab `checks=21 faults=4 pts_ok=True` vs 列 0 同值 => SAME；`sc.b.ar_orrr_rd.S` 移 18 行，16/1/True vs 同值 => SAME；rc=0。全量 `tests/**/*.S` 318 个，HEAD 版与改版 `scan_source` 逐字段 diff=0（rc=0）⇒ `.S` 用例与扫描结果未被改坏。
4. `bash 运行期证据目录内的 run.sh`（full）→ rc=0，`RESULT: PASS（checks 10，failed 0）`：check-tests-index rc=0（504 条）、check-case-ledger rc=0（现场 5726 条）、selfcheck rc=0、macro_scope gate rc=0、列 0 副本 `llvm-mc rc=0`、`check-inst-asm rc=0`（274/274 镜像、632 例）、整体注入回退 `^\t` ⇒ 两个新项各自 FAIL + 列 0 副本 `checks=0 vs 21/16 => DIFF`，cp+md5 还原 `f52f3280→c9b46730→f52f3280`、`32cf36ea→e6c25ef9→32cf36ea` 后回绿。
5. `make check-patch-tree` → rc=2，`22 problem(s)`，全部属 llvm-project(2)/qemu(6)/linux(12)/musl(2) 组件补丁树（断言⑨/⑥），本 worktree `git status` 无 `components/`、`manifests/` 改动 ⇒ 归属基线/在途组件红，非本任务引入（披露口径与任务书验收 4 相符）。

**独立反例注入（工程师证据脚本未覆盖的单点注入，均 cp+md5 还原）**
- A：只回退 `CHAIN_PT_PT_RE` 前缀为 `^\t`（保持 `CHAIN_CASE_RE` 等放宽）⇒ `列 0 扫描 == Tab 扫描: pts_ok=False / True → FAIL`，selfcheck rc=1；还原 md5 `32cf36ea` 相等、回绿 rc=0 ⇒ 新扫描项非恒真，列 0 `__PT_*` 点号解析确实承重。
- B：只回退 `PT_CASE_LINE_RE` 前缀为 `^\t` ⇒ `正文列 0 的裸 __CHECK_MEM（ISS-461）: rc=0 期望 1 → FAIL`，selfcheck rc=1；还原 md5 `f52f3280` 相等、回绿 rc=0 ⇒ S8 注入非恒真，「已宏化」判定承重。
- 还原均走 `cp -p` 备份 + md5 相等核验，未用 `git checkout/restore`；审查后无 `.preinject` 残留。

**约束核验**
- 改动范围：`git status`（审查前后两次快照一致）仅 `tools/testcases/check_inst_macro_scope.py`、`tests/ee-tiny/run_inst_tiny.py`、本任务书 3 项，与完成区「修改文件」逐项对齐，无越界（无 `.S`/`components/`/`spec/`/契约/`Makefile`）。
- `.dadao` 软链：`git ls-files .dadao` 空、被 `.git/info/exclude` 排除，未被跟踪。
- 整组同改：`run_inst_tiny.py` 内 14 条用例/故障/END 正则前缀全部为 `^[ \t]*`，无残留 `^\t` 断言类正则（残留仅 `.macro/.endm/.if` 伪指令类，非漏检面）；`check_inst_macro_scope.py` 4 条同改。任务书正文无运行期路径。
- 证据脚本审核：`run.sh` 每条断言有可达 FAIL 路径（rc 比对、`same` 比对、md5 双变校验、grep 命中具体新项、锚点数防空注入），无恒真/两支同结果；inject 段 `col0_copies` 的 rc 未直接入 ok 判定属小瑕疵，被后续 `scan_compare` 间接覆盖，不阻断。

**遗留 / finding**
- F1（非阻断，文档数字）：完成区写 `check-patch-tree rc=2（20 problem）`，reviewer 两次实测均为 `22 problem`（rc=2 一致，归属组件补丁树，非本任务）。疑为时点/共享源树漂移或笔误，建议收尾提交时把完成区该数字更正为 22 或注明实测时点。
- 其余：无。
