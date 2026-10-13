# QEMU-055t: 半托管/SEE 返回寄存器 `rd31 → rd8`（实现 + 探针重派生重验）

**模块**：qemu
**项目里程碑**：M6
**依赖**：`SPEC-126t`（Spec-first：契约/规范先行）、`LLVM-062t`（函数返回 ABI 契约，已 `已验证` ⇒ 无硬前置）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 用户裁定（原话）

> **「统一为 rd8」**（系统调用与函数 ABI 统一；此前 `rd31`）。**不立 ADR**（用户既定）。

## 变更边界（两个独立变更，**分别验收**）

- **本任务 = 「系统调用/半托管返回」域的实现侧**（半托管 `rd31 → rd8`）。**不涉**「函数返回」域（`rd8/K=8`，`SPEC-124t` 的 ABI，实现归 `LLVM-062t`）。
- 两者**独立**、**分别验收**；不得以函数返回改动为由跳过本域的半托管返回校验。
- **域 B（本任务收口，用户 2026-10-09 裁定「域 B 并入 QEMU-055t」）**：`tests/llvm/codegen/m5/**`（`m5_semi_write.s`/`expected.yaml`）中半托管服务返回 `rd31 → rd8` **随本任务收口**。理由：实现与向量互相耦合，须**同批落地**才能保持 `test-semihost` 绿（拆分落地即红门控）。

## 接口规范

- **输入**：
  - `SPEC-126t`（服务返回寄存器 `rd8` 的规范/契约结论；`.tao/knowledge/contract-semihosting.md §2/§4`、`contract-see §5`）。
  - `components/qemu/patches/target/dadao/common-semi-target.c.patch`（现 `#define DADAO_SEMI_RET_REG 31`，及头注释 `rd31 = scalar return`）。
  - `spec/Machine-01-测试机运行环境.md §5.2/§5.4`（semihosting 返回）。
  - `tools/qemu/min_rom_probe_046t.py`（25 服务 semihosting 探针，期望值多以 `rd31` 承服务返回）；其余 `tools/qemu/min_rom_probe_*.py`。
- **输出**：
  1. `common-semi-target.c.patch`：`DADAO_SEMI_RET_REG` **31 → 8**（`common_semi_set_ret()` 写 `rd8`），并同步头注释中的返回寄存器措辞（引 `Machine-01 §5.2`/`contract-semihosting`）。
  2. `tools/qemu/min_rom_probe_046t.py`：**服务返回**期望值按 `rd8` 重派生并重验；「返回落 `rd31`」用例改为「返回落 `rd8`（且 `rd31` 不被改）」。
  3. 其余探针：**逐条分类**（`rd31` 作**中间暂存**者**不改**，仅服务返回者改），分类表入完成区。
  4. 重跑相关探针 + 门控，给真实输出与退出码。
  5. **域 B（本轮收口）**：`tests/llvm/codegen/m5/m5_semi_write.s` + `tests/llvm/codegen/m5/expected.yaml`——半托管服务返回 `rd31 → rd8`（含「返回落 `rd8`、`rd31` 不被改」语义），期望值/派生按 `rd8` 重派生并**重验**。
- **约束**：
  - **只改半托管服务返回**：`DADAO_SEMI_RET_REG` 及读服务返回处；**不改** `DADAO_SEMI_NUM_REG`（`rd16` 服务号）/`DADAO_SEMI_ARG_REG`（`rb16`）等**入参**映射；**不改**以 `rd31` 作通用暂存的用法（`rd31` 仍为通用 temp）。
  - **不改 `spec/`**（`git diff --name-only | grep -E '^spec/'` 无输出）；规范侧归 `SPEC-126t`。
  - **重建成本申报**：改 `components/qemu/patches/**` ⇒ 开工前写明「重建 QEMU（增量），预计 N 分钟」；一次构建、勿零散重跑。
  - `series`/`changelog.md` 随任务追加（`Process-01`）。
  - **门控保持全绿**，不回归。

## 硬约束

- **临时目录** `/tmp/opencode/QEMU-055t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/QEMU-055t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据；**还原须含重建**（源码还原 ≠ 二进制还原）。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/qemu/QEMU-055t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **实现改毕**：`common-semi-target.c.patch` 中 `DADAO_SEMI_RET_REG == 8`，`common_semi_set_ret` 写 `rd8`（给 grep 真实输出）；`rd16`/`rb16` 入参映射**逐条未变**。
2. **探针重派生**：`min_rom_probe_046t.py` 服务返回期望值按 `rd8` 重派生并**重跑通过**（给真实输出与退出码）；「返回落 `rd8`、`rd31` 未被改」用例存在。
3. **逐条分类**：其余探针的 `rd31` 命中**逐条**分类（改 / 不改 + 理由）；暂存用法**不改**。
4. **不回归**：`make check`/`check-qemu-semantics`/`check-patch-tree` EXIT=0（通过数与改前**逐项相等 / 不下降**）。
5. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出。
6. **一键证据脚本**：`.work/evidence/QEMU-055t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如把 `DADAO_SEMI_RET_REG` 改回 `31` ⇒ 断言 FAIL ⇒ `cp`+md5 还原 + **重建** ⇒ 回绿）。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。
8. **域 B 收口 / `test-semihost` EXIT=0**：`make test-semihost` **EXIT=0**（`run_m5_e2e` 全绿，逐项现场统计、不写死计数）；域 B 向量（`m5_semi_write.s`/`expected.yaml`）服务返回 `rd8` 与实现侧一致。

## 完成区

**用户裁定（原话，留痕）**：> 「统一为 rd8」（系统调用与函数 ABI 统一；此前 `rd31`）。**不立 ADR**。
**用户裁定（原话，留痕）**：> 「域B 并入 QEMU-055t」（2026-10-09）：把 `tests/llvm/codegen/m5/**` 中半托管服务返回的 `rd31 → rd8` 收口并入本任务（原属 `TESTCASES-041t` 域 B，其 output 2）⇒ `TESTCASES-041t` 收窄为域 A（函数返回）+ 其余。理由：实现与向量互相耦合，须同批落地以保 `test-semihost` 绿。
**测试结果**：046t 探针 PASS 33/0；6 未改探针 rc=0；`test-semihost` **EXIT=0**（`run_m5_e2e` 10/10）；`test-codegen` EXIT=0（19/19）；`make check`=0（`check-qemu-semantics` 149/149、`check-lit` 73/73）；`check-patch-tree`=0（105）。
**修改文件**：① `components/qemu/patches/target/dadao/common-semi-target.c.patch`（`RET_REG` 31→8+头注释，上轮）；② `tools/qemu/min_rom_probe_046t.py`（返回期望重派生 `rd8`，上轮）；③ `components/qemu/changelog.md`（追加/更新任务行）；④ `tests/llvm/codegen/m5/m5_semi_write.s` + ⑤ `tests/llvm/codegen/m5/expected.yaml`（**域 B 本轮**）。证据 `.work/evidence/QEMU-055t/run.sh`（`.work/` gitignore）。
**验收结果**：
- ① `DADAO_SEMI_RET_REG`=8 写 `rd8`；入参 `DADAO_SEMI_NUM_REG`=16/`DADAO_SEMI_ARG_REG`=16/`SP`=1 **逐条未变**；`rd31` 仍通用暂存（证据脚本 `*_unchanged`/`ret_reg_is_8` PASS）。
- ② **域 B**：`m5_semi_write.s` 的 SYS_OPEN 句柄 + SYS_WRITE 返回**均读 `rd8`**（代码无 `rd31`）；`expected.yaml` 约定 `rd8=return`、derivation 同步（源自 `contract-semihosting §2/§4`+`Machine-01 §5.2`，非反填）；`run_m5_e2e --only m5_semi_write` PASS（exit=66）。
- ③ 门控 rc：`test-semihost`=0 / `test-codegen`=0 / `make check`=0 / `check-patch-tree`=0。
- ⑤ `git diff --name-only | grep -E '^spec/'` 无输出；`check-no-residue`=0；`git status -uall` 仅本任务 6 文件，无 `*_tmp*`/`.orig`/`.rej`。
- ⑥ 证据脚本 `RUN_EXIT=0`；注入A `RET_REG 8→31`（重建）⇒ `ret_rd8`(`rd8 exp=0x3b9aca00 got=0x0; rd31 exp=0x5a5a got=0x3b9aca00`)/`svc_open` FAIL ⇒ cp+md5 还原(`b5415831…`)+重建 ⇒ 回绿；注入B `m5_semi_write.s` OPEN 句柄读 `rd8→rd31`（不重建）⇒ E2E FAIL(`exit=225` 文件空)⇒ cp+md5 还原(`0e301be1…`)⇒ 回绿。

**逐条分类表（`rd31`/`rb31` 命中；计数现场统计、不写死）**：

| 文件 | 行/用例 | 判定 | 理由 |
|---|---|---|---|
| `m5/m5_semi_write.s` L87/97、`m5/expected.yaml` L38/80 | 半托管返回读 | **改→`rd8`** | 服务返回（域 B） |
| `min_rom_probe_046t.py` | 返回 exp / `ret_rd8` | **改→`rd8`** | 服务返回 |
| `034t/035t/036t/037t/038t` | `load_rf` | 不改 | `rd31` 通用暂存 |
| `045t` L402 | cfx 寄存器观测 | 不改 | 非服务返回 |
| `codegen/{expected.yaml,*.ll,README.md}`、`run_codegen_e2e.py` | crt0/函数返回 | 不改 | 域 A（`TESTCASES-041t`） |

**新发现/坑**：WRITE 返回自检（`rd8` vs 0）**非鉴别**（`rd8`/`rd31` 初值均 0，注入实证）；**鉴别点在 OPEN 句柄读**。末次 `-d cpu` dump 落点使返回原值可捕获（上轮）。共享层「无返回」服务写 `0xdeadbeef`（非笔误）。
**遗留问题**：无（域 B 已收口，`test-semihost` 全绿）。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查（`.c` 源 + patch + 046t 探针 + 证据脚本）：

1. **`.c`**：`DADAO_SEMI_RET_REG` 31→8，`common_semi_set_ret` 经该宏写 `rd8`；入参宏（NUM/ARG/SP）与函数体未动；头注释按 `Machine-01 §5.2/§5.4`、`contract-semihosting §2/§4` 引 `rd8`，参数区 `rd16-rd31` 措辞保留；ADR 引用仅留 D4/D5/D6（返回机制/复用）+ D2/D14（映射，准确）。判决：正确。
2. **探针**：29 处 exp 键 `rd31→rd8`（值不变，spec 派生）；6 处 `st_o(8,..)` 消费 OPEN 句柄；`ret_rd8` 用已知 `TICKFREQ=1e9` + `rd31` 哨兵 `0x5A5A`（强断言）。`0xdeadbeef`（无返回标记）随返回寄存器移至 `rd8`，正确。
3. **门控**：check / check-qemu-semantics(149/149) / check-patch-tree(105) EXIT=0，与改前**逐项相等**；`test-semihost` 失败源自 `tests/llvm/codegen/m5/**`（属 `TESTCASES-041t`），非本任务越界。
4. **防造假**：所有 rc 以 `rc=$?` 捕获（无 `tee`）；证据脚本注入 `RET_REG 8→31` ⇒ 断言 FAIL ⇒ `cp`+md5 还原(`b5415831…`)+重建 ⇒ 回绿（证明可失败、可还原）。

首轮证据脚本两处自缺陷当场修复并复跑 `RUN_EXIT=0`：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `$f_no_regression` unbound（`set -u`） | ✅已修 | 改 `probe_${f}_no_regression` | 复跑 6 探针断言全 PASS |
| F2 `grep -c rd31 == 0` 过严（参数区 `rd16-rd31` 合法） | ✅已修 | 改断言「`RET_REG 31` 无匹配」 | `ret_reg_not_31` PASS |
| F3 `test-semihost` E2E 失败 | ⏸延后 | 未改（属 `TESTCASES-041t` 域 B） | 完成区「遗留问题」 |

判决：F1/F2 已修；F3 为跨任务依赖（非本任务文件）已登记。本任务自身验收（patch + 探针 + `make check`/`check-qemu-semantics`/`check-patch-tree` + 证据脚本）**全部通过**；因 `test-semihost` 未绿（依赖 `TESTCASES-041t`），状态保持「待开始」，交主会话裁定依赖处置。

#### 第 1 轮 reviewer 验收

**重跑记录**（完整输出留 `.work/log/qemu/QEMU-055t-review-*.log`）：
- `bash .work/evidence/QEMU-055t/run.sh > …/run.log 2>&1; rc=$?` ⇒ **EXIT=0**、`RESULT: PASS`：`ret_reg_is_8`=1、`set_ret_writes_rd_index`=1、`num_reg_rd16_unchanged`=1、`arg_reg_rb16_unchanged`=1、`ret_reg_not_31`=0、`patch_ret_reg_is_8`=1、域B 6 项（`vec_no_rd31`/`vec_open_handle_rd8`/`vec_write_ret_rd8`/`yaml_*`）全 PASS、`046t_full` **rc=0 PASS=33 FAIL=0**、`046t_ret_rd8` rc=0、6 未改探针（034t–038t/045t）rc=0、`test_semihost` **rc=0**（`Results: 10/10`、`run_m5_e2e: PASS`）、`check_patch_tree` rc=0（105 patches）。
- `make test-codegen` ⇒ **EXIT=0**（`Results: 19/19`）；`make check` ⇒ **EXIT=0**（`check-qemu-semantics` 149/149、`check-lit` Passed 73、`check-patch-tree` 105、`check-no-residue` PASS）；与改前（QEMU-053t 台账 149/105/19）**逐项相等、不下降**。
**脚本审核**（先审后跑）：每条断言 FAIL 路径可达（`[cond] && rc=0 || rc=1` 双支不同结果 + `verdict`→`FAILED`→`exit 1`）；注入 A（源 `RET_REG 8→31`）非空（`cmp` 判变）+ **重建**、还原 `cp`+md5（`b5415831…` 相等）+ **重建**回绿；注入 B（向量）不重建、`cp`+md5（`0e301be1…`）还原回绿；无 `tee`（grep 仅命中注释）、无 `git checkout/restore/stash`、结尾直接 `exit`。合格。
**独立反例注入（与 engineer 两处均不同）**：`expected.yaml` `m5_semi_write` 的 `expected_exit_code: 0x42→0x43` ⇒ `run_m5_e2e --only m5_semi_write` **EXIT=1**（`FAIL m5_semi_write expected=67 actual=66 exit=66`）⇒ `cp`+md5 还原（前 `190381029dc17d63786c69cb464c3007` = 后）⇒ 复跑 **EXIT=0**（1/1 PASS）⇒ 反例可失败、可还原。
**约束核验**：
1. impl：`git diff` 该补丁逐 hunk 仅头注释 + `+#define DADAO_SEMI_RET_REG   8`；`common_semi_set_ret` 经宏写 `env->rd[DADAO_SEMI_RET_REG]`（grep matches=1）；`NUM_REG=16(rd16)`/`ARG_REG=16(rb16)`/`SP_REG=1` 为 diff 上下文行**零改**；`rd31` 通用暂存保留（`ret_rd8` 哨兵 `0x5A5A` 存活实证）。
2. 域B：`m5_semi_write.s` L87 `st.o rd8,[rb16,0] ; handle returned in rd8`、L97 `cmp.so rd11, rd8, rd12`（两处服务返回 == `rd8`，代码无 `rd31`）；`expected.yaml` derivation 逐条指向 `contract-semihosting §2/§4`+`Machine-01 §5.2`（与契约 `返回值 → rd8` 一致），期望值（`0x42`/`WXYZ`）在 diff 中为上下文**未改** ⇒ 非反填。
3. 逐条分类复核：`034t` L215/`035t` L186/`036t` L239/`037t` L222/`038t` L208 的 `rd31` 均为 `load_imm64_rd(31,…)`+`rd2rf` 通用暂存、非服务返回 ⇒ **不改正确**；`045t` L374 `cfx2rd(0,0,8,31)` → L402 exp `"rd31": 2` 为 cfx 寄存器观测、非服务返回 ⇒ **不改正确**；全量 `grep rd31 tests/ tools/` 无其它服务返回残留 ⇒ **无漏改**。
4. 门控真实 rc：`test-semihost`=**0**（`run_m5_e2e` **10/10**）/ `test-codegen`=0（19/19）/ `make check`=0（149/149、lit 73）/ `check-patch-tree`=0（105）。
5. **域A 未被越界触碰**：`git diff --name-only` 过滤 `tests/llvm/codegen/{expected.yaml,*.ll,README.md}`、`tests/scripts/codegen_crt0.s`、`tools/integ/run_codegen_e2e.py`（m5 子目录除外）**无输出**（rc=1）。
6. 无残留：`git status --porcelain -uall` 前后快照**逐行一致**（6 文件、md5 全等：patch `555a71f5…`、046t `75a18d56…`、changelog `fa8310e4…`、vec `0e301be1…`、yaml `19038102…`、`.c` 源 `b5415831…`）⇒ 注入均已还原（含重建）；`spec/` 交集空（rc=1）；无 `*_tmp/_orig/_rej/_preinject`（engineer 备份均在 `/tmp/opencode/QEMU-055t/`）；补丁 34 **无新增**（改既有，series 无改动）。
**判决：Accepted** —— 验收命令块在独立重跑下全部通过、约束无违反、域A 无越界。

#### 第 2 轮 engineer 自审（域 B 收口）

自主逐行审查（`m5_semi_write.s` + `expected.yaml` + `changelog.md` + 证据脚本）：

1. **向量**：L87 `st.o rd8,[rb16,0]` 存 SYS_OPEN 句柄（在 L88 `set.zw rd8,..` 覆盖前，顺序正确）；L97 `cmp.so rd11, rd8, rd12` 取 SYS_WRITE 未写计数（L89 `trap` 后）。两处均为服务返回；`fail:` 语义未变。
2. **expected.yaml**：约定行 `rd8=return`；derivation 由 `contract-semihosting §2/§4`+`Machine-01 §5.2` 派生（不复述 QEMU/llc）；期望值（exit 0x42 / file WXYZ）未变、未反填。
3. **分类表**：`tests/**`/`tools/**` 全量排查 `rd31`/`rb31`；改 2 处（域 B 向量+yaml）+ 上轮 1 处（046t）；其余（`load_rf` 暂存、`045t` cfx 观测、codegen 函数返回域 A、`run_codegen_e2e.py`）**不改**。
4. **防造假**：rc 全用 `rc=$?`（无 `tee`）；注入 A（重建）/B（不重建）均实证「注入→FAIL→cp+md5→回绿」。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 注入 B 首版改 `cmp.so` 行**非鉴别**（`rd31`/`rd8` 初值均 0 ⇒ 注入后仍 PASS） | ✅已修 | 注入 B 改改 **OPEN 句柄读** `st.o rd8→rd31`（鉴别点） | 注入后 `run_m5_e2e` FAIL rc=225（文件空）；还原后回绿 |
| F2 `vec_no_rd31` 断言把注释里的 `rd31` 也计入 | ✅已修 | 断言改 `grep -vE '^[[:space:]]*;'` 去注释行 | `vec_no_rd31` matches=0 PASS |

判决：全部 finding 已修；门控全绿，证据脚本 `RUN_EXIT=0`。状态置 `待验收`。
