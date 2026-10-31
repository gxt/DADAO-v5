# TESTCASES-088t: 生成器后续收口（mem 落点归位 + 三生成器 `--check`）

**模块**：testcases
**项目里程碑**：M10
**依赖**：`TESTCASES-087t`（已验证；ctrl 两生成器的「落点守卫 + 同渲染函数 `--check`」形态由本任务沿用）
**状态**：待开始

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
  - mem：`  <fname>: N cases`（3 行）+ `Total: N cases across 3 files`；
  - isa：`Wrote <fname>: N cases for M identities`（每册）+ `Done. Total identities: N`；
  - misc：`Generated N cases for misc.yaml:` + 逐例 `  [i] id format class` + `Written to: <path>`。
  - ⚠️ mem 现输出的是 `  mem-rd.yaml: 22 cases` **不含** `Wrote`；保持现形即可，但须在 `--check` 的 PASS/FAIL 与文档里统一用 `tests/inst/base/<册>` 表述。
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

**测试结果**：（待填写）
**修改文件**：（待填写）
**验收结果**：（待填写）
**新发现/坑**：（待填写）
**遗留问题**：（待填写）

## 审阅记录

（待 engineer 自审后按轮次追加）
