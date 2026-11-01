# TESTCASES-088t: 生成器后续收口（mem 落点归位 + 三生成器 `--check`）

**模块**：testcases
**项目里程碑**：M10
**依赖**：`TESTCASES-087t`（已验证；ctrl 两生成器的「落点守卫 + 同渲染函数 `--check`」形态由本任务沿用）
**状态**：已验证

## 执行环境
**执行环境**：本地（仓库 `/mnt/tao/DADAO-v5`，分支 `TESTCASES-088t`）。`python3` + PyYAML 可用；QEMU 安装根 `.dadao/cross-toolchain/bin/qemu-system-dadao`（mtime `2026-11-01 06:09`，35169320 B）；门控 `make check`（L1）/ `make check-modules`（L2）/ `make check-inst`。

## 用户授权原话（主会话转述，逐条引文）

> **TESTCASES-088t：生成器后续收口**
> - 目标：`generate_mem_vectors.py` 输出改到 `tests/inst/base`（落点守卫）；为 `generate_mem_vectors.py`、`generate_isa_vectors.py`、`generate_misc.py` 加 `--check`（写盘/校验共用渲染）；`generate_ctrl_*` 已有的 `--check` 不重复改。
> - 不改任何向量内容/期望/序号；重跑后 `mem-rd/rb/ra.yaml` 与 isa/misc 生成物 byte-identical。
> - 文档 `tools/testcases/README.md` 同步；不改 Makefile（是否入门控留主会话）。
> - 验收：四生成器 `--check` rc=0；默认重跑 0 diff；旧 `tests/vectors` 不存在；注入 OUT_DIR 回旧路径 ⇒ 红→cp+md5 还原→绿；L1/L2。
> - 文件范围只列这些 tools 文件 + README；不改 QEMU/spec/契约/tests/inst 内容。

## 背景（architect 实测，非推测）

1. `tools/testcases/generate_mem_vectors.py:34`：`OUT = os.path.join(REPO, "tests", "vectors", "isa")`（**旧路径**）；唯一写点 `main()`（`:571-579`，`yaml.dump(..., sort_keys=False)`，**无 makedirs**），写 3 册 `mem-{rd,rb,ra}.yaml`。
2. `tools/testcases/generate_isa_vectors.py:22`：`OUT = …/"tests","inst","base"`（落点正确）；写点在**模块级**（`:1678-1693`：`os.makedirs` + 每册 `open(...,"w")` + `Wrote …` + 末尾 `Done. Total identities: N`），写 6 册 `reg-{arith,logic,shift-extend,compare,cond-assign,imm-block}.yaml`；位置参数为文件名过滤器（`:1680-1685`）。
3. `tools/testcases/generate_misc.py:34-35`：落点正确；写点 `write_yaml()`（`:272-292`，header + `yaml.dump(..., sort_keys=False, width=120)`），写 `misc.yaml`。
4. 三者均**无** `--check`；可仿先例：`generate_ctrl_*`（087t）与 `generate_rev_vectors.py --check`。
5. **可行性预演（architect 现场，`/tmp/opencode/TESTCASES-088t/probe`，OUT 重定向到 /tmp 只读重渲染）**：3+6+1 = **10 册 `cmp` 全 IDENTICAL**（mem-rd/rb/ra、6 册 `reg-*`、misc）。
6. ⚠️ `generate_isa_vectors.py:1674-1677` 注释称「6 册中 5 册有已知 generator↔vector drift（issues.yaml）」——**与现场不符**（实测 6/6 byte-identical，可能已被早前任务消解）。本任务以**现场**为准：重跑若出现任一 diff ⇒ **停下报告**，不得顺手接受、不得以注释为由放行。

## 问题根源

087t 只收口了 ctrl 两生成器（落点 + `--check`）。`generate_mem_vectors.py` 的 `OUT` 仍指 `TESTCASES-072t` 迁移前的旧目录 `tests/vectors/isa`：重跑既不刷新真源（`tests/inst/base/mem-*.yaml`），还会新建未跟踪残留目录；另两个生成器虽落点正确但无 `--check`，`tests/README.md:211`「生成器 `--check` 全部 byte-identical」的说法**无机械支撑**——生成器↔产物的一致性只能靠人工 `diff`，漂移无门控能发现。

## 目标（范围）

1. **mem 落点归位 + 守卫**（与 087t 同形）：
   - `OUT_DIR_REL = os.path.join("tests", "inst", "base")`；`OUT_DIR = os.path.join(REPO, OUT_DIR_REL)`。
   - `main()` 首步（写盘与 `--check` 共用、在**任何** `os.makedirs`/`open(...,"w")` 之前）核 `os.path.relpath(OUT_DIR, REPO)` 以 `tests/inst/` 开头；否则 stderr `ERROR: OUT_DIR 必须位于 tests/inst 之下（当前 %s）` + 非零退出。
2. **三生成器加 `--check`**（写盘与校验共用**同一渲染函数**；`--check` 只读、**不建目录、不写文件**）：
   - mem：抽 `_render_yaml(cases) -> str`（现 header 4 行 + `yaml.dump(cases, default_flow_style=False, sort_keys=False, allow_unicode=True)` 原样搬入）；写盘 = render + `open(...,"w")`；`--check` 逐册与磁盘读入内容比 → 全一致 `--check: PASS（3 册 byte-identical）` rc=0，缺失/不一致逐册 `FAIL` rc=1。
   - isa：把模块级「生成 + 写盘」收进 `main(argv)`（或 `_render_all() -> dict[fname, str]`），`os.makedirs` 移入**写盘分支**；`--check` 复用同一渲染；`--check` 可与位置文件名过滤组合（缺省校验 6 册）。
   - misc：抽 `_render(cases) -> str`（header + dump 原样），`--check` 与 `OUT_FILE` 磁盘内容比。
3. **零漂移**：默认重跑后 10 册对 HEAD **0 diff**；`tests/vectors` 全程不存在。
4. **文档**：`tools/testcases/README.md` 增一节（三生成器命令、落点、`--check` 语义、退出码 0/1/2）。
5. **不动**：`generate_ctrl_*.py`（087t 已收口）、`generate_rev_vectors.py`、任何 yaml 内容、`tests/case-ledger.tsv`、`Makefile`。

## 接口规范

- **退出码**：`0` = 成功/一致；`1` = 不一致或文件缺失；`2` = 参数错误（未知选项、未知文件名）。
- **默认模式 stdout 契约保持**（便于既有日志比对）：
  - mem：`  tests/inst/base/<fname>: N cases`（3 行，含相对册路径；路径口径由本任务订正）+ `Total: N cases across 3 files`；
  - isa：`Wrote <fname>: N cases for M identities`（每册）+ `Done. Total identities: N`；
  - misc：`Generated N cases for misc.yaml:` + 逐例 `  [i] id format class` + `Written to: <path>`。
  - ⚠️ mem **改前**输出 `  mem-rd.yaml: 22 cases`（**不含** `Wrote`）；为满足验收 ①「3 个路径均在 `tests/inst/base/`」，本任务改为 `  tests/inst/base/mem-rd.yaml: 22 cases`（行形/行数不变；仓内无消费者解析该输出）。`--check` 的 PASS/FAIL 与文档统一用 `tests/inst/base/<册>` 表述。
- **`--check` 输出**：一致 → 单行 `--check: PASS（N 册 byte-identical）`；不一致 → 每册 `FAIL <fname>: <missing|mismatch>`（stderr 可）。
- **渲染函数唯一**：写盘与 `--check` 必须调用同一函数（禁「两支路各写一份」——否则校验恒真）。
- **无副作用 `import`**：`--check` 与 `import` 均不得创建目录/文件。
- **守卫文案**与 087t 一致（便于证据脚本 `grep '必须位于 tests/inst 之下'`）。

## 验收标准

1. `python3 tools/testcases/generate_mem_vectors.py` rc=0，stdout 的 3 个路径均在 `tests/inst/base/`；`test ! -e tests/vectors` rc=0。
2. `git diff --quiet -- tests/inst/base/mem-rd.yaml tests/inst/base/mem-rb.yaml tests/inst/base/mem-ra.yaml` rc=0。
3. `python3 tools/testcases/generate_isa_vectors.py` rc=0 后 `git diff --quiet -- tests/inst/base/reg-arith.yaml tests/inst/base/reg-logic.yaml tests/inst/base/reg-shift-extend.yaml tests/inst/base/reg-compare.yaml tests/inst/base/reg-cond-assign.yaml tests/inst/base/reg-imm-block.yaml` rc=0；`python3 tools/testcases/generate_misc.py` rc=0 后 `git diff --quiet -- tests/inst/base/misc.yaml` rc=0。
4. **四生成器 `--check` 全 rc=0** 且输出含 `PASS`：`generate_mem_vectors.py --check`（3 册）、`generate_isa_vectors.py --check`（6 册）、`generate_misc.py --check`（1 册）、`generate_ctrl_jump_call_ret.py --check` / `generate_ctrl_br.py --check`（087t 不回归）；`--check` 前后 `git status --porcelain -uall` 无变化、无新目录。
5. **幂等**：默认模式连跑两次，第二次后 10 册仍 `git diff --quiet` rc=0、`git status` 不变。
6. **可达 FAIL（注入，禁 `git checkout/restore/stash/show` 还原）**：
   - mem：`cp` 备份 → `OUT_DIR_REL` 改回 `tests/vectors/isa`（md5 变）→ `--check` **rc≠0** 且 stderr 含「必须位于 tests/inst 之下」→ `cp` 还原、md5 与备份一致 → `--check` **rc=0**；全程 `tests/vectors` 不出现。
   - isa / misc：各 `cp` 备份产物册 → 追加一个换行（md5 变）→ 对应 `--check` **rc=1** 且列出该册 `FAIL` → `cp` 还原 md5 一致 → **rc=0**。
7. **参数错误**：三生成器 `--bogus` ⇒ **rc=2**（isa 的未知位置文件名同 rc=2）。
8. `make check`（L1）rc=0；`make check-modules`（L2）rc=0；`make check-inst` rc=0 且含 `0 failed`、`0 errors`（`total`/`deferred` 以现场输出为准、**不写死**；本任务不改向量 ⇒ total 应与修前现场一致）。
9. `python3 tools/testcases/validate_vectors.py` rc=0；`python3 tools/infra/check_case_ledger.py` rc=0（ledger 0 diff）。
10. 证据脚本 `.work/evidence/<任务ID>/run.sh` **rc=0**（含第 1–7 条真实输出与各自 rc）；日志命名以 `TESTCASES-088t-` 起头（L1 `check-run-artifacts` A3 强制）；`git status --untracked-files=all` 无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`tests/vectors` 残留。

## 约束

- **只改**「文件范围」列出的文件；`tests/inst/base/**`、`tests/case-ledger.tsv`、`tests/README.md`、`Makefile`、`tools/testcases/generate_ctrl_*.py`、`tools/testcases/generate_rev_vectors.py`、`components/**`、`spec/**`、`contracts/**`、`.tao/adr/**` **一律不改**。
- **不改任何向量内容/期望/序号**；重跑出现任一 diff ⇒ **停下报告**（真源已漂移，不属本任务处置范围）。
- 不新增/删除 `tests/inst/base` 下的文件；不新增共享库（各脚本内联十余行 `--check` 即可）。
- 不改 `.tao/knowledge/discussing.md`（台账只由主会话维护）。
- 临时目录 `/tmp/opencode/TESTCASES-088t/`；不提交、不 push；**不跑** `check-night` / 全量 `check-full`。
- 失败保留现场并继续推进（自行处置 / 绕行 / 有据重试并记次数）；只在需用户语义裁定时留问。
- 完成区 ≤30 行；每轮审阅记录 ≤40 行；长输出留 `.work/log/testcases/` 或 `.work/evidence/`。

## 文件范围（计划修改）

1. `tools/testcases/generate_mem_vectors.py`（`OUT_DIR_REL`/`OUT_DIR` + 落点守卫 + `_render_yaml`/`--check` + docstring）
2. `tools/testcases/generate_isa_vectors.py`（`main(argv)` 或 `_render_all()` + `--check`，模块级写盘移入函数 + docstring）
3. `tools/testcases/generate_misc.py`（`_render(cases)` + `--check` + docstring）
4. `tools/testcases/README.md`（新增短节：三生成器命令、落点、`--check` 语义、退出码）
5. `.work/evidence/<任务ID>/{run.sh,*.log}`（不入库）

**明确不改**：`tests/inst/base/**`（10 册须 0 diff）、`tests/case-ledger.tsv`、`tests/README.md`、`Makefile`、`tools/testcases/generate_ctrl_jump_call_ret.py`、`tools/testcases/generate_ctrl_br.py`、`tools/testcases/generate_rev_vectors.py`、`components/**`、`spec/**`、`contracts/**`、`.tao/knowledge/discussing.md`。

## 下发前预检（5 项，architect 现场结论）

1. **任务书内部一致：PASS** —— 验收 1–10 与「文件范围」一一对应；「改落点」与「10 册 0 diff」不矛盾（实测 10/10 byte-identical）；「加 `--check`」与「不改 Makefile」不矛盾（脚本自跑）；`check-inst` 即 L3 成员 `inst:base`，故不重复跑全量 L3。
2. **本任务验证手段的全部前置可用：PASS（实测）** —— ① `python3 -c "import yaml"` 成功；② 三生成器在 `/tmp` 重定向 OUT 后 rc=0（isa/misc/mem 均 0）；③ 10 册 `cmp` 全 IDENTICAL（`/tmp/opencode/TESTCASES-088t/probe/out`）；④ `generate_rev_vectors.py --check` 可仿；⑤ QEMU 安装根存在且可执行（35169320 B，2026-11-01 06:09）；⑥ `make -n check` / `-n check-modules` / `-n check-inst` 均 rc=0；⑦ `test ! -e tests/vectors`（旧路径当前不存在，非只读参考、无锁 ⇒ 不构成 BLOCKED）。
3. **验收逐条可跑性**：1–10 均「现在可跑」；**BLOCKED：无**。全量 `check-full`/`check-night` 按任务要求**不跑**（范围排除，非 BLOCKED）。
4. **与 `contracts/`、`tests/inst/` 一致：PASS** —— 现场重渲染 10/10 byte-identical ⇒ 生成器真源与入库向量当前一致；本任务不改任何期望值；`contracts/**` 无生成器路径声明 ⇒ 无需改合约。
5. **拟改文件 × `spec/` 清单：0 命中** —— 4 个拟改路径全在 `tools/`（另 `.work/` 证据不入库）；不触 `spec/**` ⇒ 无需 spec 锁 sha/changelog，也无需额外授权。

## 已知风险 / 遗留（不在本任务修，完成区登记）

- `tools/testcases/test_anti_forgery_008t.py` 仍引用 `tests/vectors/**`（仓内 Makefile/门控均无引用，疑似孤儿脚本）——不改。
- `--check` 是否入 Makefile 门控（L1/L2）留主会话裁定；本任务**不改** `Makefile`。
- `tests/README.md:211`「生成器 `--check` 全部 byte-identical」若在三生成器补齐后仍需与之对齐措辞，由主会话裁定（`tests/README.md` 不在范围）。
- `components/qemu/patches/target/dadao/helper.c.patch` 的 `7-14` 注释笔误（既有 discussing 条目）——不改。

## 完成区

**测试结果**：验收 1–10 全通过（10/10）；证据脚本 `.work/evidence/TESTCASES-088t/run.sh`（full）rc=0、`--inject` rc=0；失败原因：无。
**修改文件**：`tools/testcases/generate_mem_vectors.py`（`OUT_DIR_REL`/`OUT_DIR` + 落点守卫 + `_build_files`/`_render_yaml`/`_check`/`main(argv)`）；`tools/testcases/generate_isa_vectors.py`（模块级写盘收进 `main(argv)` + `_render_yaml`/`_selected_files`/`--check`，未知册 rc=2）；`tools/testcases/generate_misc.py`（`_render` + `--check` + `main(argv)`）；`tools/testcases/README.md`（新增三生成器节）；`.tao/knowledge/milestones.md`（088t 行 待开始→待验收）；`.work/evidence/TESTCASES-088t/run.sh`（不入库）。
**验收结果**：
- ① mem rc=0，stdout 3 行路径均 `tests/inst/base/mem-*.yaml`；`test ! -e tests/vectors` rc=0。
- ②③ 10 册（mem 3 + reg 6 + misc 1）重跑后 `git diff --quiet` rc=0，md5 与起始基线逐册全等。
- ④ `--check` rc=0：mem `PASS（3 册）`、isa `PASS（6 册）`、misc `PASS（1 册）`、ctrl-jump-call-ret `PASS（3 册）`、ctrl-br `PASS（1 册）`；前后 `git status -uall` 一致、无新目录。
- ⑤ 幂等：连跑两次后 10 册 0 diff、status 不变。⑦ `--bogus`×3 rc=2；isa 未知册名 rc=2。
- ⑥ 注入（cp+md5 还原，禁 git 还原）：mem `OUT_DIR_REL→tests/vectors/isa` ⇒ rc=1 含「必须位于 tests/inst 之下」、`tests/vectors` 未出现 ⇒ 回绿；isa/misc 追加换行 ⇒ rc=1 `FAIL …: mismatch` ⇒ 回绿；missing 分支（临时 OUT）rc=1 且不建目录。
- ⑧ `make check` rc=0；`make check-modules` rc=0；`make check-inst` rc=0（`Results: 982 total, 977 passed, 0 failed, 5 deferred, 0 errors`，现场值不写死）。
- ⑨ `validate_vectors` rc=0；`check_case_ledger` rc=0。⑩ 日志均 `TESTCASES-088t-*`；无 `_tmp`/`_gate`/`.orig`/`.rej`/`tests/vectors` 残留。
**新发现/坑**：isa 的模块级写盘使 `import` 有副作用，收进 `main()` 后 `--check`/`import` 零副作用（临时 OUT 断言「不建目录」可机械验证）；`--check` 的 PASS 册数与现场 glob 计数对账（3+6+1 == 10）优于写死；任务书背景 6 的「5/6 册 drift」注释与现场不符（实测 6/6 byte-identical），随重写删除。
**遗留问题**：`tools/testcases/test_anti_forgery_008t.py` 仍引用 `tests/vectors/**`（任务书已知风险，未改）；`--check` 是否入 Makefile 门控、`tests/README.md:211` 措辞未动（留主会话裁定）；mem 默认 stdout 改为 `  tests/inst/base/<册>: N cases`（为满足验收 ①，行形/行数不变，仓内无消费者解析该输出）。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`git diff` 逐行审查 3 个生成器 + README（自主逐行；`subagent_depth=1` 无法起独立子代理）。
**判决**：无未修 finding（8 条处置完毕），交 reviewer 验收。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 mem stdout 只印 `<fname>`，不满足验收①「3 条路径均在 tests/inst/base/」 | ✅已修 | 输出改为 `  tests/inst/base/<册>: N cases`（行形/行数不变） | `grep -c '^  tests/inst/base/mem-.*\.yaml: [0-9]* cases$'` = 3；仓内无解析该输出的消费者 |
| F2 isa 模块级写盘使 `import`/`--check` 有副作用 | ✅已修 | 写盘 + `os.makedirs` 移入 `main(argv)` 写盘分支 | 临时 OUT 跑 `--check`：rc=1 且目录未创建（`inject-missing-branch`） |
| F3 写盘与 `--check` 可能各写一份渲染（校验恒真） | ✅已修 | 抽 `_render_yaml`/`_render`，两支路共用 | 每脚本 `yaml.dump(` 计数=1、渲染函数调用=3（`render-shared-*`） |
| F4 isa 未知位置文件名被静默忽略（旧 `_SELECTED`） | ✅已修 | 位置参数 `choices=sorted(FILE_MAP)` | `reg-nope.yaml` ⇒ rc=2 |
| F5 isa `Done. Total identities` 过滤模式下仍报全量 | ✅已修 | 按本次 targets 求和；默认值不变 | 默认跑仍为 `Total identities: 105`（与改前同值） |
| F6 守卫须在任何写操作之前 | ✅已修 | `main()` 在 argparse 后、`makedirs`/`open(...,"w")` 前调 `_check_out_dir()` | 注入 rc=1 且 `tests/vectors` 未创建 |
| F7 6/6 drift 旧注释与现场不符 | ✅已修 | 随重写删除，docstring 说明输出/校验 | 10 册重跑 md5 全等；5 个 `--check` rc=0 |
| F8 `--check` 逐册印 `OK:` 行（任务书称「单行 PASS」） | ❌不修 | 保留与 087t 同形（逐册 OK + 单行汇总 PASS） | `generate_ctrl_jump_call_ret.py --check` 同形且已 Accepted；汇总行仍是单行 `PASS（N 册 byte-identical）` |

### ARCH 复核与提交（architect，第 1 轮）

**独立重跑**（日志 `/tmp/opencode/TESTCASES-088t/review/`）：`--check` mem/isa/misc rc=0（`PASS 3/6/1 册`）；`generate_ctrl_jump_call_ret`/`generate_ctrl_br --check` rc=0（087t 无回归）；三生成器默认重跑 rc=0，10 册 `git diff --quiet -- tests/inst/base` rc=0 且 md5 与起始基线逐册全等；`test ! -e tests/vectors` rc=0；`--bogus`×3 与 isa 未知册名均 rc=2。
**独立反例（本方，非 engineer 脚本）**：mem-rd 追加换行 ⇒ rc=1 `FAIL tests/inst/base/mem-rd.yaml: mismatch` ⇒ `cp` 还原 md5 `f43f03f4…` ⇒ rc=0、base 0 diff；`/tmp` 临时树置 `OUT_DIR_REL=tests/vectors/isa` ⇒ rc=1 `ERROR: OUT_DIR 必须位于 tests/inst 之下` 且未建目录。
**门控**：L1 `make check` rc=0（53s）；L2 `make check-modules` rc=0；`make check-inst` rc=0（`982 total, 977 passed, 0 failed, 5 deferred, 0 errors`）；`validate_vectors` rc=0；`check_case_ledger` rc=0；证据脚本 `run.sh --inject` rc=0，跑后三生成器 md5 不变、base 0 diff（还原干净）。
**任务书订正（仅文字，主会话派单）**：`## 接口规范` mem stdout 契约 `  <fname>: N cases` → `  tests/inst/base/<fname>: N cases`，并改掉其下「现输出 `  mem-rd.yaml`…保持现形即可」旧口径（与完成区、`tools/testcases/README.md` 一致）。
**文件集对账**：`git status -uall` 6 项 == 完成区「修改文件」（3 生成器 + `tools/testcases/README.md` + 本任务书 + `milestones.md`）；无 `tests/inst/base`/`case-ledger.tsv`/`Makefile`/ctrl/rev 改动；`.work/evidence/**` 由 `.gitignore` 忽略、不入库。
**档位/提交**：`待验收`（reviewer 未判决）+ 零改动式收口 ⇒ 按主会话派单原话用 `feat(testcases): TESTCASES-088t 生成器后续收口`（非 `WIP:`；偏差已在本轮声明）；分支 `TESTCASES-088t`，**未 push**，哈希见 `git log -1`。
**遗留（交主会话裁定）**：`tools/testcases/test_anti_forgery_008t.py` 仍指 `tests/vectors/**`（门控无引用）；`tests/README.md:211` 措辞；`--check` 是否入 Makefile 门控。

### 第 1 轮 reviewer 验收

**判决：Accepted**（基于本人重跑，不采信 engineer 叙述；日志 `/tmp/opencode/TESTCASES-088t-review/`）
**重跑记录**：① `git diff --name-status 4b410bec^ 4b410bec` = 6 项（3 生成器+README+任务书+milestones），无 `tests/inst/base`/case-ledger/Makefile/ctrl/rev 改动。② 默认重跑 mem/isa/misc rc=0；mem stdout `grep -c '^  tests/inst/base/mem-…'`=3；10 册 `git diff --quiet` rc=0 且 `md5sum -c` 与起始快照全等；`test ! -e tests/vectors` rc=0。③ 5 个 `--check` rc=0：PASS 3/6/1/3/1 册（汇总 10 == 现场 glob 10）；`--bogus`×3 rc=2、isa 未知册 rc=2（含 `--check` 组合）；`--check`+位置参数组合 rc=0；前后 `git status -uall` 一致。
**独立注入（非 engineer 的 OUT_DIR 方案，cp+md5 还原、未用 git 还原）**：misc.yaml / mem-rd.yaml / reg-arith.yaml 各追加换行 ⇒ 对应 `--check` rc=1 `FAIL …: mismatch` ⇒ `cp` 还原 md5 全等（bb6d7bc1…/f43f03f4…/2359931…）⇒ rc=0、0 diff。
**证据脚本**：审读 `run.sh` —— 每条断言有可达 FAIL 路径（精确 rc 断言、注入前校验 md5 变+`git diff` 非空、册数现场 glob 对账不写死、dump=1 防双渲染、cp+md5 对账还原），无恒真/吞码；重跑 full rc=0（57 项全 PASS）；**独立注入产物后重跑同一脚本 rc=1**（check-md5/status-unchanged 等 FAIL）⇒ 还原后 rc=0。
**门控（本人重跑）**：`make check` rc=0；`make check-modules` rc=0；`make check-inst` rc=0（`982 total, 977 passed, 0 failed, 5 deferred, 0 errors`，与完成区数字一致）；`validate_vectors` rc=0（156/156、712 cases）；`check_case_ledger` rc=0（1965 身份、ledger 0 diff）。
**代码核验**：每生成器 `yaml.dump(` 唯一（渲染同源，非两支路）；mem 守卫在任何 makedirs/open(w) 之前；isa 模块级写盘已收进 `main()`（import 零副作用由 missing 分支测试机械验证）；misc `yaml` 顶层导入。
**约束核对**：文件范围 6 项相符；快照对账——审前/审后 `git status -uall` 均空、22 个目标文件 md5 全等、无 `*_tmp*`/`_gate*`/`.orig`/`.rej`/`tests/vectors` 残留；注入全部 cp+md5 还原；未跑 check-full/check-night；未提交。
**遗留评估**：mem stdout 改 `tests/inst/base/<册>` 可接受（满足验收①、行形行数不变、仓内无该输出消费者——grep 实证、接口规范已同步）；`--check` 未入 Makefile 符合授权原话（留主会话）；`test_anti_forgery_008t.py`（孤儿，门控无引用）与 `tests/README.md:211` 措辞均为已登记遗留、不在本任务范围。

### /complete 交叉复核与提交（architect）

**交叉复核（本人现场，不采信叙述）**：`git diff --name-status 4b410bec^ 4b410bec` = 6 项；`--check` mem/isa/misc rc=0（3/6/1 册）；10 册 `git diff --quiet -- tests/inst/base` rc=0、`test ! -e tests/vectors` rc=0；L1 `make check` rc=0；`make check-inst` rc=0（`982 total, 977 passed, 0 failed, 5 deferred, 0 errors`，与 reviewer/完成区一致）；收尾前 `git status -uall` 仅本任务书、无 `*_tmp*`/`_gate*`/`.orig`/`.rej`/`tests/vectors` 残留。L2 由 reviewer 本轮重跑 rc=0（本机同日同树），未重复跑。
**档位/提交**：reviewer Accepted ⇒ 正常提交 `review: TESTCASES-088t Accepted（reviewer + architect 交叉复核）`；文件集 2 项（本任务书 `待验收→已验证`、`milestones.md` 088t 行 同改）；分支 `TESTCASES-088t`，**未 push、未 merge**，哈希见 `git log -1`。
**遗留（交主会话）**：`test_anti_forgery_008t.py` 仍指 `tests/vectors/**`；`tests/README.md:211` 措辞；`--check` 是否入 Makefile 门控。

