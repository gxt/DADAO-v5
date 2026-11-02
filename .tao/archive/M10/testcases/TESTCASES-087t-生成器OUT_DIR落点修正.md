# TESTCASES-087t: ctrl 生成器 OUT_DIR 落点修正 + `--check`

**模块**：testcases
**项目里程碑**：M10
**依赖**：`TESTCASES-086t`（已验证；该任务用「重跑到旧路径 → diff → `cp` 单册」绕过，并在完成区遗留「生成器 OUT_DIR 漂移待另立任务修」）
**状态**：已验证

## 执行环境
**执行环境**：本地（仓库 `/mnt/tao/DADAO-v5`，分支 `TESTCASES-087t`）。Python3 + PyYAML 可用；QEMU 安装根 `.dadao/cross-toolchain/bin/qemu-system-dadao`（mtime `2026-10-31 14:39`）；载体门控 `tools/qemu/semantics_gate.py`（经 `make check-inst`）。

## 用户授权原话

> 在 /mnt/tao/DADAO-v5，master 干净。创建 `TESTCASES-087t` 任务书：修正 ctrl 生成器的输出目录。文件名放 `.tao/tasks/testcases/`；先确认 087 未占用。
>
> 背景（TESTCASES-086t 发现）：
> - `tools/testcases/generate_ctrl_jump_call_ret.py` 与 `tools/testcases/generate_ctrl_br.py` 的 `OUT_DIR` 仍指旧 `tests/vectors/isa`；
> - 重跑不会更新真实 `tests/inst/base`；
> - 086t 只能用“重跑→diff→cp 单册”绕过，未改生成器。
>
> 任务目标：
> 1. 把两个生成器的输出目录改为当前真实落点 `tests/inst/base`（先核清两者生成哪些文件，不要误改只读参考目录）。
> 2. 重跑生成器后，`ctrl-jump.yaml`/`ctrl-call.yaml`/`ctrl-ret.yaml` 与现有 `tests/inst/base` byte-identical；若有旁漂移，停下报告。
> 3. 更新生成器注释/文档/README（如需要），并加一个可重复校验（生成器默认输出不再落 `tests/vectors`；可加 `--check` 或测试脚本）。
> 4. 不改测试期望值、不改 QEMU/spec/ADR；不顺手改 `helper.c.patch` 的 `7-14` 注释（另记）。
> 5. 验收：生成器重跑 rc=0；三册 `git diff --quiet`；`check-inst`/L1 绿；证据注入（把 OUT_DIR 改回旧路径 ⇒ 校验 FAIL ⇒ 还原回绿）；不跑夜跑。
>
> 任务书自包含：背景、目标、验收、约束、文件范围、用户授权原话（“不要带... 安排”/“087t”）、5 项预检、完成区模板。先调查实际生成文件与 `OUT_DIR` 使用点，列出文件集；若发现 `tests/vectors` 是只读参考/被锁，标 BLOCKED 并给替代。
>
> 流程：核 clean master；建分支 `TESTCASES-087t`；只写任务书 + milestones；显式 staging；commit `docs: 立 TESTCASES-087t 生成器 OUT_DIR`；不 push、不实现、不跑夜跑；回报路径/commit/预检/风险。

用户授权词（逐字）：「**安排**」（另含「087t」「不顺手改」「不跑夜跑」）。

## 背景（architect 实测，非推测）

1. 两个生成器写盘点（`grep -n OUT_DIR/OUT_FILE`）：
   - `tools/testcases/generate_ctrl_jump_call_ret.py:36` `OUT_DIR = os.path.join(REPO, "tests", "vectors", "isa")`；唯一写点 `_write_yaml()`（`:610-613`，`os.makedirs` + `open(path,"w")`），`main()` 写 **3 册**：`ctrl-jump.yaml`（6 例）、`ctrl-call.yaml`（11 例）、`ctrl-ret.yaml`（10 例）。
   - `tools/testcases/generate_ctrl_br.py:22-23` `OUT_DIR`/`OUT_FILE` 同旧路径；写点 `main()`（`:380-382`），写 **1 册** `ctrl-br.yaml`（40 例）。
   - 两脚本均无命令行参数、无 `--check`、无其它写盘点（`grep "open("` 仅 opcodes 读 + 上述写点）。
2. `tests/vectors` **不存在**（`ls: cannot access 'tests/vectors'`）；本仓只读参考目录是 `.cache/refs/**`，`tests/vectors` 既非只读参考也无锁 ⇒ **不构成 BLOCKED**。反之：旧路径一旦被跑，会**新建**未跟踪目录 `tests/vectors/isa/`（086t 用 `trap` 清理过）。
3. 真实落点 `tests/inst/base/` 存在 17 册，含 `ctrl-{jump,call,ret,br}.yaml`（mtime `10-31 17:03` / `10-24 11:38`）；`tools/testcases/validate_vectors.py:747` 已把 `tests/inst/base` 当真源。
4. **可行性已预演**（architect 在 `/tmp/opencode/TESTCASES-087t/probe` 以 monkeypatch `OUT_DIR` 重渲染，不写仓库）：4 册与 `tests/inst/base` **逐字节一致**（`cmp` 全 IDENTICAL，rc=0）⇒ 改落点后重跑不应产生任何向量 diff；若出现 diff ⇒ 说明真源已漂移，按任务书**停下报告**。
5. 同风格先例：`tools/testcases/generate_rev_vectors.py --check`（`:385-406`，重派生→与入库逐字节比→不一致非零退出）；`tests/README.md:211` 亦声称「生成器 `--check` 全部 byte-identical」，而本仓 4 个 `generate_*.py` 尚无 `--check`（`generate_ctrl_*`、`generate_isa_vectors.py`、`generate_misc.py`、`generate_mem_vectors.py` 中的前二者属本任务）。

## 问题根源

`TESTCASES-072t` 把向量从 `tests/vectors/isa/` 迁到 `tests/inst/base/` 时，只搬了**产物**与 harness/门控，**未回头改生成器的输出目录**；于是「真源（生成器）→ 产物」链路断开：重跑写到一个已不存在的旧路径（并新建残留目录），`tests/inst/base` 永远不会被生成器刷新。086t 需要改 `ctrl-ret.yaml[9]` 时只能人工 `cp` 单册，可复现性靠临时脚本兜底——即生成器**不再能证明产物来自真源**，而这类漂移没有任何门控能发现。

## 目标（范围）

1. **落点归位**：两生成器的输出目录改为 `tests/inst/base`，且**落点带守卫**（解析结果必须位于 `tests/inst/` 之下，否则 `ERROR` + 非零退出），使「产物落旧路径」这件事**机械不可发生**，而非仅靠注释约定。
2. **加 `--check`（可重复校验）**：
   - 无参 = 现行为（渲染 + 写盘 + 原 `Wrote …` 摘要行）；
   - `--check` = **只读**：进程内渲染 1..N 册内容，与磁盘现存文件**逐字节**比较；全部一致 ⇒ 打印 `... --check: PASS（N 册 byte-identical）` rc=0；缺失或不一致 ⇒ 逐册列 `FAIL` rc=1（**不写盘、不建目录**）；
   - 写盘与 `--check` 必须走**同一个渲染函数**（禁止「两条支路各写一份结果」——否则校验恒真）；
   - 参照 `generate_rev_vectors.py --check` 的用法/输出风格（DRY），但**不新建共享库**：两脚本各自内联十余行即可（它们本就是独立一次性入口）。
3. **重跑零漂移**：两生成器重跑 rc=0，`tests/inst/base/ctrl-{jump,call,ret,br}.yaml` 对 HEAD **0 diff**；`tests/vectors` 全程不存在。**三册（jump/call/ret）为硬要求，`ctrl-br.yaml` 同属本任务重跑面，亦须 byte-identical**；任一旁漂移 ⇒ 停下报告（不得顺手接受）。
4. **文档/注释同步**：两生成器 docstring 写明「输出 = `tests/inst/base/<册>`；校验 = `python3 … --check`」；修正 `generate_ctrl_br.py` docstring 里的旧 ADR 路径 `.knowledge/adr-0004-test-machine.md` → `.tao/adr/adr-0004-test-machine.md`（仅注释事实修正）；`tools/testcases/README.md` 增一小节（两生成器命令 + `--check` 语义 + 落点）。
   - **不含** `.tao/knowledge/discussing.md`：该台账**只由主会话维护**，子代理不得修改（见「约束」）。其中「生成器 OUT_DIR 修正」条目改「已转任务 / → 已转 TESTCASES-087t」由**主会话在本任务收尾（`/complete`）后**执行。
5. **不动语义面**：不改任何 yaml 内容、期望值、用例序号/数量、`case-ledger.tsv`、QEMU/`components/**`、`spec/**`、`.tao/adr/**`、`contracts/**`、`Makefile`。

## 接口规范

- **落点常量**（两文件同形）：
  ```python
  OUT_DIR_REL = os.path.join("tests", "inst", "base")   # TESTCASES-072t 迁移后的真实落点
  OUT_DIR = os.path.join(REPO, OUT_DIR_REL)
  ```
- **落点守卫**（`main()` 首步、两条路径共用）：
  - 计算 `os.path.relpath(OUT_DIR, REPO)`，要求其以 `os.path.join("tests", "inst") + os.sep` 开头；
  - 否则 `print("ERROR: OUT_DIR 必须位于 tests/inst 之下（当前 %s）" % OUT_DIR, file=sys.stderr)` 并返回非零；
  - 守卫须在**任何** `makedirs`/`open(...,"w")` 之前，`--check` 路径同样先过守卫。
- **渲染/写盘**：
  - `generate_ctrl_jump_call_ret.py`：`_render_yaml(header, cases) -> str`（现 `_write_yaml` 内的 `header + yaml.dump(...)` 原样搬入，参数 `default_flow_style=False, allow_unicode=True, width=120` 保持不变）；`_write_yaml` = `render` + 写盘 + 摘要行；`--check` 用 `render` 与 `open(path).read()` 比。
  - `generate_ctrl_br.py`：把 `main()` 里的头部 6 行注释 + `yaml.dump(...)` 抽成 `_render() -> str`，写盘与 `--check` 共用。
- **退出码**：`0` = 成功/一致；`1` = 不一致或文件缺失；`2` = 参数错误（未知参数）。`--check` 模式**不得**产生任何文件/目录。
- **不变契约**：默认模式的 stdout 仍含 `Wrote <path>: N cases (...)`（与现有输出同形，便于既有日志比对）。

## 验收标准

1. 重跑 `python3 tools/testcases/generate_ctrl_jump_call_ret.py` 与 `python3 tools/testcases/generate_ctrl_br.py` 均 **rc=0**，stdout 的 `Wrote` 路径为 `tests/inst/base/…`。
2. `git diff --quiet -- tests/inst/base/ctrl-jump.yaml tests/inst/base/ctrl-call.yaml tests/inst/base/ctrl-ret.yaml tests/inst/base/ctrl-br.yaml` **rc=0**（4 册 byte-identical，含 br）；若任一册漂移 ⇒ 停下报告，不得提交产物差异。
3. `test ! -e tests/vectors` 成立（重跑前后均核；`ls tests/vectors` 必须报 No such file）。
4. `python3 tools/testcases/generate_ctrl_jump_call_ret.py --check` 与 `python3 tools/testcases/generate_ctrl_br.py --check` 均 **rc=0**，输出含 `PASS`；`--check` 前后 `git status --porcelain -uall` 无变化、无新目录。
5. **幂等**：连续跑两次默认模式，第二次后 `git diff --quiet` 仍 rc=0、`git status` 不变。
6. **可达 FAIL 注入**：`cp` 备份 → 把 `OUT_DIR_REL` 改回 `tests/vectors/isa`（md5 须变化）→ `--check` **rc≠0** 且 stderr 含 `tests/inst` 落点守卫信息或该册不存在 → `cp` 还原 + md5 与备份一致 → `--check` 回绿 rc=0。**禁** `git checkout/restore/stash/show` 还原。
7. `make check-inst` **rc=0**，`failed=0 errors=0`；`total`/`deferred` 与修前基线（`978 total … 5 deferred`）一致，以现场输出为准（不写死）。
8. L1 `make check` rc=0；L2 `make check-modules` rc=0。`python3 tools/testcases/validate_vectors.py` rc=0；`python3 tools/infra/check_case_ledger.py` rc=0（ledger 不应有 diff）。
9. 文档面：两生成器 docstring 含落点与 `--check` 用法；`tools/testcases/README.md` 有对应小节；`generate_ctrl_br.py` 的 ADR 路径已修正。
10. 证据脚本 `.work/evidence/<任务ID>/run.sh` **rc=0**（含第 2/3/4/5/6 条真实输出；日志留 `.work/log/testcases/`）；`git status --untracked-files=all` 无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`tests/vectors` 残留。**不跑** `check-night`/全量 `check-full`（`check-inst` 即 L3 成员 `inst:base`）。

## 约束

- **只改**「文件范围」列出的文件；`tests/inst/base/*.yaml`、`tests/case-ledger.tsv`、`tests/README.md`、`tests/INVENTORY.md`、`tests/inst/{inventory.md,schema.md,README.md}`、`Makefile`、其它 `generate_*.py`（`generate_mem_vectors.py`/`generate_isa_vectors.py`/`generate_misc.py`）、`tools/testcases/test_anti_forgery_008t.py` **一律不改**。
- **不新增/删除用例**、不改任何用例的字段值；本轮只动生成器代码 + 注释/文档。
- **子代理不改台账**：`.tao/knowledge/discussing.md` **不得修改**——该台账**只由主会话维护**；087 收尾（`/complete`）后由**主会话**把「生成器 OUT_DIR 修正」条目置为「已转任务 / → 已转 TESTCASES-087t」。任务书/完成区/验收**均不得**把该文件列为子代理改动。
- **不顺手改** `components/qemu/patches/target/dadao/helper.c.patch` 的 `7-14` 注释（既有 discussing 条目，另记）。
- 生成器 `--check` **不纳入 Makefile 门控**（避免改共享文件；是否入 L1/L2 留主会话裁定，见遗留）。
- 临时目录 `/tmp/opencode/TESTCASES-087t/`；不提交、不 push（提交权归 architect）；不跑夜跑。
- 失败保留现场并继续推进（自行处置/绕行/有据重试并记次数）；只在需用户语义裁定时留问。
- 完成区 ≤30 行；每轮审阅记录 ≤40 行；长输出留 `.work/log/testcases/` 或 `.work/evidence/`。

## 文件范围（计划修改）

1. `tools/testcases/generate_ctrl_jump_call_ret.py`（`OUT_DIR` 落点 + 守卫 + `_render_yaml`/`--check` + docstring）
2. `tools/testcases/generate_ctrl_br.py`（同上 + `_render()` + docstring 的 ADR 路径修正）
3. `tools/testcases/README.md`（新增短节：两生成器命令、落点、`--check` 语义）
4. `.work/evidence/<任务ID>/{run.sh,*.log}`（不入库）

**明确不改**：`.tao/knowledge/discussing.md`（台账只由主会话维护）、`tests/inst/base/ctrl-{jump,call,ret,br}.yaml`（须 0 diff）、`tests/case-ledger.tsv`、`tests/README.md`、`tests/INVENTORY.md`、`Makefile`、`components/**`、`spec/**`、`.tao/adr/**`、`contracts/**`、`.tao/contracts/**`。

## 下发前预检（5 项，architect 现场结论）

1. **任务书内部一致：PASS** —— 验收 1–10 与「文件范围」逐条对应（`.tao/knowledge/discussing.md` 已移出范围，见「约束」）；「改成 `tests/inst/base`」与「4 册 0 diff」不矛盾（实测重渲染 byte-identical）；「加 `--check`」与「不改 Makefile」不矛盾（脚本自身可跑）。验收 7/8 的 `check-inst` 即 L3 成员 `inst:base`，故不再重复跑全量 L3。
2. **本任务验证手段的全部前置可用：PASS（实测）** —— ① `python3 -c "import yaml"` 成功；② `make -n check-inst` rc=0、`make -n check` rc=0；③ QEMU 安装根存在且可执行（`-rwxrwxr-x … 35153368 B`）；④ 落点目录存在（17 册）；⑤ `--check` 先例 `generate_rev_vectors.py --check` 可读可仿；⑥ 4 册重渲染 `cmp` 全 IDENTICAL（可行性预演，`/tmp/opencode/TESTCASES-087t/probe`）。
3. **验收逐条可跑性**：1/2/3/4/5/6/7/8/9/10 均「现在可跑」；**BLOCKED：无**。`tests/vectors` 不存在（非只读、无锁）⇒ 用户设想的 BLOCKED 分支**不触发**。全量 `check-full`/`check-night` 按用户要求**不跑**（范围排除，非 BLOCKED）。
4. **与 `contracts/`、`tests/inst/` 一致：PASS** —— 落点 `tests/inst/base` 是 `validate_vectors.py:747` 与 `tests/README.md:49` 的现行真源；4 册重渲染 byte-identical ⇒ 生成器真源与入库向量当前一致，本任务不改任何期望值；`contracts/**` 无生成器路径声明 ⇒ 无需改合约。
5. **拟改文件 × `spec/` 清单：0 命中** —— 3 个拟改路径全在 `tools/`（另 `.work/` 证据不入库）；不触 `spec/**` ⇒ 无需 spec 锁 sha/changelog，也无需额外授权。

## 已知风险 / 遗留（不在本任务修，完成区登记）

- `tools/testcases/generate_mem_vectors.py:34` 同为旧路径 `tests/vectors/isa`（产物 `mem-ra/rb/rd.yaml` 在 `tests/inst/base`）——同类漂移，**本任务不扩围**。
- `tools/testcases/test_anti_forgery_008t.py:17-61` 仍引用 `tests/vectors/**`，仓内无任何 Makefile/门控引用（疑似孤儿脚本），**本任务不改**。
- `generate_isa_vectors.py`/`generate_misc.py` 无 `--check`（落点已正确），与 `tests/README.md:211`「全部 byte-identical」表述不符——**本任务不扩围**。
- 证据脚本须无条件断言 `test ! -e tests/vectors`：旧路径的存在性检查是唯一能发现「落点回退」的机械证据。

## 完成区

**测试结果**：`.work/evidence/TESTCASES-087t/run.sh --with-gates` rc=0（36 项全 PASS；含 L1/L2/check-inst）。check-inst：978 total / 973 passed / **0 failed / 0 errors** / 5 deferred（与基线一致，现场统计）。`validate_vectors.py`、`check_case_ledger.py` rc=0。
**修改文件**：`tools/testcases/generate_ctrl_jump_call_ret.py`、`tools/testcases/generate_ctrl_br.py`、`tools/testcases/README.md`（+ 未入库 `.work/evidence/TESTCASES-087t/run.sh`、`.work/log/testcases/TESTCASES-087t/*.log`）。`tests/inst/base/*.yaml` 0 diff。`.tao/knowledge/discussing.md` **不在本任务改动**（台账只由主会话维护，见审阅记录「第 1 轮 architect 文件集审核」）。
**验收结果**：① 两生成器默认重跑 rc=0，`Wrote …/tests/inst/base/…`；② 4 册 `git diff --quiet` rc=0（jump/call/ret/br byte-identical）；③ `test ! -e tests/vectors` 重跑前后/`--check` 后/注入期间均成立；④ 两 `--check` rc=0 且输出 `PASS（3/1 册 byte-identical）`，前后 `git status -uall` 无变化；⑤ 连跑两次默认模式 diff 仍 0、status 不变；⑥ 注入 `OUT_DIR_REL→tests/vectors/isa`（md5 双变、`git diff --name-only` 非空）⇒ 两 `--check` rc=1 且 stderr 含「OUT_DIR 必须位于 tests/inst 之下」⇒ `cp` 还原 md5 一致 ⇒ 回绿 rc=0；⑦ `make check`/`make check-modules`/`make check-inst` rc=0；⑧ 未知参数 rc=2；⑨ docstring/README/ADR 路径均已同步。
**新发现/坑**：`check-run-artifacts`（L1）对 `.work/log/**` 新文件强制 `check-<name>.log` 或 `<TASK-ID>-<purpose>.log`，自建证据日志须以任务号前缀命名，否则 L1 rc=2（首轮踩中，已改名复跑）。`make check-inst` 的计数行实际为 `Results: N total, X passed, 0 failed, D deferred, 0 errors`，不是 `failed=0 errors=0`。`--check` 复用同一 `_render*`，注入落点即触发守卫，证明校验非恒真。
**遗留问题**：无（本任务范围）。范围外同类漂移仍存：`generate_mem_vectors.py` 旧 `tests/vectors/isa` 落点、`test_anti_forgery_008t.py` 旧路径引用、`generate_isa_vectors.py`/`generate_misc.py` 无 `--check`；`--check` 未入 Makefile 门控；`helper.c.patch` 7-14 注释未动。均按任务书登记，待另立任务。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `generate_ctrl_br._render` 仅收参数，与接口规范 `_render() -> str` 字面不符 | ✅已修 | 参数改 `all_cases=None`，缺省内部 `_build_cases()` | `_render()` 无参调用 == `ctrl-br.yaml` 内容；`--check` rc=0 |
| 证据日志命名违反 L1 `check-run-artifacts` A3（`rerun-*.log` 等 17 个非法名）⇒ 首次 `make check` rc=2 | ✅已修 | 全部日志前缀 `TESTCASES-087t-`；清理旧日志 | L1 rc=0；A3 `[PASS]`（日志见 `.work/log/testcases/TESTCASES-087t/`） |
| check-inst 计数断言写死为 `failed=0 errors=0`，与实际输出格式不符 ⇒ 假 FAIL | ✅已修 | 改 `grep -E "Results: .* 0 failed, .* 0 errors"` | `check-inst-counts` PASS；实际 973/978、5 deferred |
| 注入需验证「非空注入」且不得用 git 还原 | ✅已核 | `git diff --name-only` 非空 + 双 md5 变化；`cp` 备份还原 + md5 对账 | 注入 rc=1×2、还原 md5 `fe77898c…` 一致、回绿 rc=0 |
| 默认输出契约（`Wrote <path>: N cases`）与旁册零漂移 | ✅已核 | 未改摘要行；4 册仅落点变化 | 重跑 stdout 路径为 `tests/inst/base`；4 册 diff rc=0 |

#### 第 1 轮 reviewer 验收

**判决：Needs Revision**（唯一阻断 = 验收 8 的 L1；产出物本身全部达标，见下）

**重跑记录（reviewer 亲自执行，全部相对路径、真实 rc）**
1. 分支/状态：`TESTCASES-087t`，`git status -uall` 干净；实现 commit `2e83b640` 恰 4 文件（任务书 + 3 个 tools 文件）与完成区「修改文件」对账一致；`milestones.md` 属立任务 commit `453842b3`（architect），非 engineer 改动；**`discussing.md` 零改动**（工作树 + `master...HEAD` 双向 diff 均空）✅
2. 两生成器默认重跑：均 rc=0，`Wrote …/tests/inst/base/…`（6/11/10/40 cases）；`test ! -e tests/vectors` 前后均 rc=0；4 册 md5 重跑前后逐值一致、`git diff --quiet` rc=0；连跑两次幂等 md5 不变 ✅
3. `--check`：两脚本 rc=0（`PASS（3/1 册 byte-identical）`）；`--bogus` 两脚本 rc=2 ✅
4. reviewer 独立注入（cp 备份+md5，禁 git 还原）：`OUT_DIR_REL→tests/vectors/isa`（md5 双变）⇒ 两 `--check` rc=1 + stderr「OUT_DIR 必须位于 tests/inst 之下」且未建 `tests/vectors` ⇒ `cp` 还原 `md5sum -c` OK ⇒ 回绿 rc=0 ✅
5. 证据脚本重跑 `run.sh --with-gates`：**`RESULT: FAIL`、`RUN_EXIT=1`**——36 项 35 PASS，唯 `L1-make-check rc=2 FAIL`；L2 `check-modules` rc=0、`check-inst` rc=0（`978 total, 973 passed, 0 failed, 5 deferred, 0 errors`，与基线一致，非写死）；`validate_vectors`/`check_case_ledger` rc=0 ✅
6. **L1 失败根因（单项定位）**：`check-milestones-fresh` A1——本 commit 把任务书状态翻为 `待验收`，milestones L56 表行仍 `待开始` ⇒ `MISMATCH` rc=2。注入实验：临时把任务书改回 `待开始` ⇒ 该项 PASS rc=0；`cp`+md5 还原 ⇒ 复 FAIL（确定性、可复现，非环境噪声）❌
7. 无临时残留（`*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`tests/vectors` 均无）；审查前后 `git status -uall` 快照逐行对账一致 ✅

**约束核验**：只改范围内文件 ✅；4 册/期望值/Makefile/contracts/spec 零改动 ✅；`discussing.md` 未动 ✅；`helper.c.patch` 未动 ✅；证据脚本逐条断言均有可达 FAIL 路径（注入由 `git diff --name-only`+双 md5 证非空，还原用 cp+md5）✅；完成区 7 行 ≤30、审阅记录 ≤40 ✅。

**Needs Revision 具体项**
- **阻断（门控/退出码）**：验收 8 要求 L1 `make check` rc=0，当前 rc=2（上记 6）。修复：`.tao/knowledge/milestones.md` L56 `待开始` → `待验收` 一行；该台账归 architect 维护而门控机械要求两者同步——**此口径（任务书翻状态时谁同步 milestones 行）属流程缺口，请架构师裁定**（授权 engineer 一行修复，或 architect 收尾提交时改后复验）。
- **完成区与真实输出不对齐**：声称「run.sh --with-gates rc=0（37 项全 PASS）」，reviewer 重跑为 FAIL 且实为 36 项——修复 L1 后复跑证据脚本取真实 rc/计数，改写完成区对应句。
- **文档级小错（不阻断，收尾改）**：完成区「37 项」实为 36 项（35 PASS+1 FAIL）。

#### 第 2 轮 reviewer 验收（返工提交 `7e96aeac`）

**判决：Accepted**（唯一阻断已修，`run.sh --with-gates` 亲跑 rc=0 全绿）

**重跑记录（reviewer 亲跑，真实输出/rc）**
1. 分支 `TESTCASES-087t`、`git status -uall` 干净；返工提交 `7e96aeac` 恰改 2 文件（milestones.md 一行 `待开始`→`待验收` + 任务书追加第 1 轮审阅记录），与修复指令一致、无越界 ✅
2. 状态一致：任务书 `**状态**：已验证`（L6）== milestones L56 表行 `待验收`；`make check-milestones-fresh` **rc=0**（A1 63 行全一致）✅
3. `bash .work/evidence/TESTCASES-087t/run.sh --with-gates`：**RESULT: PASS，RUN_EXIT=0**——**36 项全 PASS**（现场计数，非写死）：含 `L1-make-check rc=0`、`L2-make-check-modules rc=0`、`check-inst rc=0`；check-inst 计数行 `978 total, 973 passed, 0 failed, 5 deferred, 0 errors` 与完成区一致 ✅
4. 四册 byte-identical：`git diff --quiet -- tests/inst/base/ctrl-{jump,call,ret,br}.yaml` rc=0；`test ! -e tests/vectors` 成立（脚本内 4 处断言 + 独立复核均 PASS）✅
5. 独立反例注入（cp 备份+md5，禁 git 还原）：milestones L56 改回 `待开始`（md5 变）⇒ `check-milestones-fresh` **rc=2**（`L56 MISMATCH 表=待开始 册=待验收`）⇒ cp 还原 md5 一致 ⇒ 复跑 rc=0 回绿——门控可达 FAIL、非恒真 ✅
6. `discussing.md` 零改动（`git diff master...HEAD --stat` 空 + md5 前后一致）；审查前后 `git status -uall` 快照逐行对账 IDENTICAL；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`tests/vectors` 残留 ✅

**约束核验**：只改范围内文件 ✅；4 册/期望值/Makefile/contracts/spec 零改动 ✅；`discussing.md`/`helper.c.patch` 未动 ✅；不提交/不 push/不跑夜跑 ✅。

**Finding（文档级小错，不阻断，收尾改）**：完成区「37 项全 PASS」实际为 **36 项**全 PASS（本次重跑现场计数）；rc=0 声明与真实输出一致，仅计数笔误——由 architect 收尾提交时改为 36。

#### 第 2 轮 architect 交叉复核（`/complete`）

**判决：确认 Accepted，无补充阻断**（复核独立重跑，未采信 reviewer 叙述）

1. **判决是否过松**：验收 1–10 逐条对照 reviewer 重跑记录，均有对应现场证据；实现 diff（`2e83b640`）核过——`OUT_DIR_REL`/守卫先于 `makedirs` 与 `open(...,"w")`、写盘与 `--check` 共用 `_render_yaml`/`_render`、`--check` 无写盘路径、`Wrote …` 摘要契约保留、`--bogus` 走 argparse rc=2 ⇒ 无「恒真校验」「双支路」问题；`tests/inst/base` 4 册、期望值、Makefile、contracts、spec、`.tao/adr` 零改动。
2. **状态/门控（独立重跑）**：任务书 L6 `待验收` == milestones L56 行 `待验收`；`make check-milestones-fresh` **rc=0**（`结果: PASS (63 行…)`）。
3. **证据脚本独立重跑**：`bash .work/evidence/TESTCASES-087t/run.sh --with-gates` ⇒ **`== RESULT: PASS ==`，`RUN_EXIT=0`**；现场计数 **36 项 PASS / 0 FAIL**（`grep -cE "PASS$"` = 36，`grep -c FAIL` = 0）——证实 reviewer「36 项」而非完成区原写「37 项」。
4. **门控**：L1 `make check` rc=0（`repository checks (L1): PASS`，含 `check-milestones-fresh`、`check-run-artifacts`）；L2 `make check-modules` rc=0；`make check-inst` rc=0（`Results: 978 total, 973 passed, 0 failed, 5 deferred, 0 errors`，与基线一致）。
5. **四册 byte-identical**：`git diff --quiet -- tests/inst/base/ctrl-{jump,call,ret,br}.yaml` rc=0；`test ! -e tests/vectors` 成立。
6. **`discussing.md` 零改动**：`git diff --quiet master...HEAD -- .tao/knowledge/discussing.md` rc=0 且工作树 diff rc=0（md5 `9a45b58e…`）。
7. **无残留**：`git status --porcelain -uall` 仅任务书 1 项（本记录），无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`tests/vectors`。
8. **finding 处置**：完成区「37 项」→「36 项」（仅改文字，证据与 rc 未动）；reviewer 第 1 轮提的「谁同步 milestones 行」口径，按返工实践裁定为——**任务状态翻转的同一提交方同步 milestones 对应行**，`check-milestones-fresh` 已机械约束，不再靠人工约定（建议主会话收 `lessons.md` 一行）。
9. **本轮未做（留给主会话 `/complete` §5）**：任务书 `待验收`→`已验证` 与 milestones L56 同行翻转（须同一次提交，否则 L1 rc=2）；`discussing.md`「生成器 OUT_DIR 修正」置「→ 已转 TESTCASES-087t」；merge squash + push。

#### 主会话统一收尾

reviewer 复审与 architect 交叉复核均为 **Accepted**，无分歧；主会话采信并置任务 `已验证`，同步 `milestones` 与 `discussing.md`。本任务只修生成器 `OUT_DIR`/`--check`，未改测试期望、QEMU、spec。遗留：`generate_mem_vectors.py` 同类旧落点、`generate_isa_vectors.py`/`generate_misc.py` 无 `--check`、`test_anti_forgery_008t.py` 旧路径；另记。
