# INFRA-066t: 恢复 picolibc `libm`（删源过滤表 + 重建 + 复核）

**模块**：infra
**项目里程碑**：M7
**依赖**：`LLVM-079t`（P0，`已验证`）、`LLVM-080t`（P1，`已验证`）、`INFRA-057t`（过滤表来源，`已验证`）⇒ **均已满足**；同改 `components/picolibc/patches` ⇒ 与其它 picolibc 任务**串行**
**状态**：已验证

> 本任务书由**主会话**依 `ISS-188.notes` 的**衍生待办**与 `TESTCASES-042t` **前置注记**撰写（`LLVM-080t` reviewer 发现：sysroot `libm.a` = **876 B 空壳**）；非常规 architect 起草，已披露。

## 目的

`INFRA-057t` 为换取构建确定成功，在 `components/picolibc/patches/meson.build.patch` 内置**显式源过滤表**（整目录排除 `libm/` + 20 条后端受阻 libc 源）。现 **P0（`LLVM-079t`）/ P1（`LLVM-080t`）均已收口** ⇒ **删表恢复全量**，使 `libm.a` 真实可用（`TESTCASES-042t` 的前置）。

## 接口规范

- **输入（实测）**：过滤表在 `components/picolibc/patches/meson.build.patch`（现场 `grep` 为准；现含 `_p.contains('/libm/')` 与 `@0@` 条数占位）；`.dadao/dadao-unknown-elf/lib/libm.a` = **876 B**（空壳）；探针驱动已入库：`tools/testcases/picolibc-probe-compile.sh`、`tools/testcases/picolibc-probe-fp.sh`。
- **输出**：
  1. **删除源过滤表**（或**最小化**，见约束）⇒ picolibc **全量**构建。
  2. 重建 + 安装（`make build-picolibc` + `install-host`；picolibc 全量构建实测约 **14 s**，若显著变长按「长任务」规则）。
  3. **产物复核（机械）**：`libm.a` **非空**（现场 `ls -la` + 与 `libc.a` 对比）；`nm` 复核 **8 符号**：`floor`/`ceil`/`trunc`/`round`/`rint`/`nearbyint`/`fmin`/`fmax`（真实输出）。
  4. **探针全量复跑**：`tools/testcases/picolibc-probe-compile.sh` + `picolibc-probe-fp.sh` ⇒ 现场统计 `BACKEND_CANNOT_SELECT`/`NOLIBCALL`/`FRONTEND_ERR`/`MISSING_HDR` 各类计数（**不写死**）。
  5. `.tao/knowledge/milestones.md` 流水更新 `INFRA-066t` 行（状态 `待验收`，`完成时间` `—`）。

- **约束**：
  - ⚠️ **不得假绿**：若删表后**仍有源不可编**（后端/前端缺口）⇒ **逐条登记**（`ISS-188` notes 或新 issue，按体例）并把过滤**最小化到不可避免的最小集**，**显式披露**该最小集与理由（**宁可留最小集，也不许静默过滤**）。
  - 只动 `components/picolibc/patches/**`、`Makefile`/`tools/infra/**`（若需）、`issues.yaml`、任务书、`milestones.md` 行；越界须披露。
  - **补丁导出纪律**：补丁写 `/tmp` 再落 `components/`、行数下限、**非空 blob**、`check-patch-tree` 断言⑥；`.work/source/picolibc` 须 `base+N` 且 `series` 一致。
  - **计数不写死**。
  - 临时目录 `/tmp/opencode/INFRA-066t/`；**不提交 git**；禁 `git add -A`/`.`。
  - 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
  - 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位）。

## 验收标准

1. **过滤已删/最小化**：`grep` 证据（过滤逻辑已去除，或列出**最小保留集**并说明每条的缺口依据 + 登记编号）。
2. **`libm.a` 非空**：现场 `ls -la`（与 `libc.a` 量级对比）；**8 符号 `nm` 复核全部命中**（真实输出）。
3. **探针全量**：两个探针脚本复跑 ⇒ 现场统计表；**P0/P1 相关签名计数为 0**；其余类（如 `FRONTEND_ERR`/`MISSING_HDR`）如实列出。
4. **E2E**：picolibc smoke（`make test-picolibc-smoke`）**rc=0**；**新增/改造一条真走 libm 的 E2E**（如调 `floor`/`pow` 并打印结果）⇒ 真实输出 + 退出码。
5. **门控**：`make check`、`check-patch-tree`、`check-no-residue` 各 EXIT=0（**捕获命令自身退出码，禁 `cmd | tee`**）。
6. **反例可失败**：注入（临时把某 `libm` 源重新排除 / 篡改 `libm.a` 符号期望）⇒ 断言/门控 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿。
7. **一键证据脚本**落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
8. **完成区**（≤30 行）与真实输出逐条对齐。

## 完成区

**测试结果**：通过 15/15（一键证据 `<evidence>/<任务ID>/run.sh --inject` **rc=0**）；另 `check-modules`(L2) rc=0、`check-lit` 99/99 rc=0。无失败项。

**修改文件**（仅本任务范围；未提交）：`components/picolibc/patches/meson.build.patch`（整目录 `libm/` 排除 → **41 条最小集**；`series` 仍 14 行未变）、`tools/infra/test_picolibc_smoke.py`（新增 **libm E2E 阶段**）、`tools/infra/build_picolibc.py`（docstring 口径）、`components/picolibc/{README.md,changelog.md}`、`.tao/knowledge/issues.yaml`（`ISS-193` + `ISS-188` 指针）、`.tao/knowledge/milestones.md`、本任务书；非 git：`<evidence>/<任务ID>/`、`.work/log/infra/`。

**验收结果**（逐条，与真实输出对齐）：
1. **过滤**：`grep -c "_p.contains('/libm/')"` = **0**；过滤表 = **41 条最小集**（与「本构建**全部 1120 个编译项逐条重编**」得到的 non-OK 集**精确相等**，非手写）；6 类根因逐条登记 **`ISS-193`**(a)–(f)（SETO/SETUO/SETUNO 30、f32 libcall 5、i64 bswap 1、截断存储 2、`"r"` 约束 2、long double libcall 1）。
2. **产物**：`libm.a` **仍 876 B 空壳（上游设计 ⇒ 任务书口径更正，见「新发现」）**；恢复目标是 `libc.a`：**1,241,616 → 1,686,214 B**、成员 998（`libm_*` 317）。8 符号 `nm --defined-only libc.a` **全命中**（`floor/ceil/trunc/round/rint/nearbyint/fmin/fmax`，各 `T`）。
3. **探针（现场统计）**：compile 341 项 = OK 327 / FRONTEND_ERR 12 / MISSING_HDR 1 / BACKEND_OTHER 1，**CANNOT_SELECT=0、NOLIBCALL=0**（同 LLVM-080t 基线）；FP 38 项 = OK 105、NOLIBCALL 3（`fmin_f` f32）、ERROR 6（`isnan_d`/`isfinite_d`）⇒ **P0/P1(f64) 签名计数 0**，余项归 `ISS-193`(a)(b)。
4. **E2E**：`make test-picolibc-smoke` **rc=0**（libm 阶段真实输出 `libm.o undefined symbols = [ceil, cos, floor, fmax, fmin, fmod, log, nearbyint, printf, rint, round, sin, sqrt, trunc]`；`libm: qemu rc=0 output='libm 0\n'`）；`--inject` ⇒ **rc=1**。
5. **门控**：`make check` / `check-patch-tree`（123 补丁）/ `check-no-residue` / `check-source-state` / `check-lit`(99/99) / `check-modules` 全 **EXIT=0**（捕命令自身退出码）。
6. **反例可失败**：注入「目录级 `libm/` 排除」⇒ `filter-no-libm-dir-exclude` **FAIL** ⇒ `cp`+md5 还原（md5 一致）⇒ **回绿**；符号检查对空壳 `libm.a` 必 FAIL。
7. **证据脚本**：`<evidence>/<任务ID>/run.sh` **rc=0**（15 检查；计数现场统计；无 `tee` 吞码）。
8. **补丁纪律**：`make_patch.py` 导出（**非手工编辑**，Process-01 §6.1.1）；`series` 14 行；`meson.build.patch` 99 行、blob 非空；独立临时 index 复核「base+补丁集 == 源工作树」**4199 路径 0 失配**（≈断言⑥）。

**新发现/坑**：
- **`libm.a` 876 B 空壳是 picolibc 上游设计，不是过滤表产物**：`empty-libs/meson.build` 生成 `libm.a`/`libg.a`/`libnosys.a` 空库以兼容 `-lm`；上游 README「Picolibc version 1.7 §1」明写 libc/libm **合并为单一库**。数学源编入 **`libc.a.p/libm_*.c.o`**（mpart 对象并入 libc.a）⇒ 判定「libm 可用」必须查 **`libc.a`**。
- **`ninja` 首次失败只报 4 个 `FAILED`（早停）**，其余缺口不可见 ⇒ 最小集须由**全量重编**（1120 项）得出；且过滤生效后 `compile_commands.json` **会丢掉被排除源**，失败集必须在删表状态下采集。
- `-Oz` 下 `<math.h>` 的 `fmin/fmax` 被 clang 展开为 intrinsic（走 `SETUO`）⇒ E2E 须 `-ffreestanding -fno-builtin` 才产生**真实 libcall**；探针脚本复用旧 `OUT` 会把历史探针 `.c` 计入（78 ≠ 38）⇒ 须用干净 `OUT`。

**遗留问题**：① **41 条最小集仍在**（`pow`/`hypot`/`j0`/`y0`/复数/`scanf` 族/`memset_s` 不可链接）⇒ `ISS-193`，建议 **(a) 类（`SETO`/`SETUO`/`SETUNO`）单独立 LLVM 任务**（一次改动可删 30/41）；② `test_picolibc_smoke.py --work-dir` 默认仍 `/tmp/opencode/INFRA-057t/smoke`（沿用未改）；③ 范围外未做：LLVM 后端补齐、`TESTCASES-042t` 接入。

## 审阅记录

#### 第 1 轮 engineer 自审（自主逐行审查 + 真实复验）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 删表后构建 FAIL（4 源）；`ninja -j8` **早停**，其余缺口不可见（自审发现：`FAILED` 仅 4 条而探针 0 报） | ✅已修 | 以 `compile_commands.json` **全量 1120 项逐条重编**（`scan-sources.py`）得到精确失败集，程序化生成过滤块 | 扫描 TSV 1120 行 / non-OK 41；证据 `filter-set==scan-non-ok` PASS |
| 过滤表按 **basename 后缀**匹配，可能误伤同名构建源（如构建内 `close.c`/`crt0.c` 确有重名） | ✅已核（机制沿用，未改） | — | 全量统计：排除集 41 个 basename **无一**与其它构建源重名（证据 `no-basename-overmatch` PASS） |
| 任务书口径「`libm.a` 空壳 = 过滤表产物」**不成立**（上游 `empty-libs/` 设计） | ✅已修（按事实更正并留痕） | 验收对象改为 `libc.a`；README「移植要点」+ changelog + `ISS-188` 追加更正 + `ISS-193` 登记 | `empty-libs/meson.build` + 上游 README「1.7 §1」；`nm libc.a` 8/8 |
| libm E2E 首版直接调 `<math.h>` 的 `fmin/fmax` ⇒ 后端 `unsupported floating-point branch condition`，编译 FAIL | ✅已修 | 该阶段加 `-ffreestanding -fno-builtin`，使 8 符号成为**真实 libcall** | 编译 rc=0；`nm -u` 含 8 符号；guest `libm 0`、rc=0 |
| 证据脚本 `run gate <target>` 丢参 ⇒ `set -u` 下 `$1: unbound variable`，3 个门控假红 | ✅已修 | `run()` 改 `"$@"` | 重跑 15 检查全绿、rc=0 |
| FP 探针 `OUT` 复用旧目录 ⇒ 计到 78 个探针（含历史 `.c`），计数失真 | ✅已修 | 以干净 `OUT` 复跑并落盘 | 38 项；现场计数 OK 105 / NOLIBCALL 3 / ERROR 6 |
| 注入还原是否会清掉未提交改动 | ✅已核 | 全程 `cp` 备份 + md5 对账，**禁** `git checkout/restore/stash` | `inject-restored-md5` PASS（md5 一致） |
| 源树改动的 E1 不变量（干净 + base+1） | ✅已核 | 用 `commit --amend`（不动工作树、不用 `reset --hard`） | `check-source-state` picolibc `count=1 clean=True`；`check-patch-tree` rc=0 |

**判决**：7 条 finding 全部 ✅（无延后/不修）；任务可标 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑记录**（本人命令 + 真实输出/退出码；禁 tee 吞码）：
- 门控 6 项各 `echo rc=$?` = **0**：`check`（L1 PASS）、`check-patch-tree`（123 patches OK）、`check-no-residue`、`check-source-state`（picolibc `count=1 clean=True`）、`check-lit`（Passed 99）、`check-modules`（L2 PASS）。
- **口径更正判定 = 有据（非事后圆场）**：`<source>/picolibc/empty-libs/meson.build`（补丁集不含此文件 ⇒ 上游原文）`empty_lib_names=['g','m','nosys']`、「Build a set of empty libraries for compatibility with existing build scripts」；上游 README「Picolibc version 1.7 §1: Merge libc and libm into a single library」；构建日志「Installing empty-libs/libm.a」。`libm.a` 空壳属上游设计成立，恢复目标改 `libc.a` 正确。
- 产物现场：`libc.a` **1,686,214 B** / `ar t` **998** 成员 / `libm_*` **317**（均现场统计）；`libm.a` **876 B** 仅 `empty.c.o`（与 `libg.a`/`libnosys.a` 同源）。8 符号 `nm --defined-only libc.a` 独立复核 **8/8 `T`**（floor/ceil/trunc/round/rint/nearbyint/fmin/fmax）。
- 41 条最小集：从 `meson.build.patch` 独立提取 **41** 条，与 `<evidence>/<任务ID>/scan-full.tsv`（**1120** 行 = 1079 OK + 41 non-OK）non-OK 集 `diff` ⇒ **SETS-EQUAL**；`grep -c "_p.contains('/libm/')" = 0`。
- 抽 5 条自编复现（工具链 `clang -target dadao-unknown-elf`）：`s_pow.c` rc=1「unsupported floating-point branch condition」(a)、`sf_log10.c` rc=1「no libcall available for flog」(b)、`hash_page.c` rc=1「Cannot select: i64 = bswap」(c)、`vfscanf.c` rc=1「Cannot select: store … trunc to f32」(d)、`memset_s.c` rc=1「could not allocate input reg for constraint 'r'」(e) ⇒ **5/5 确实编不过**、签名与 TSV 一致。
- 反向抽 3 条未排除源：`s_sin.c`/`s_sqrt.c`/`memcpy.c` **rc=0 可编** ⇒ 无「能编却被排除」。
- 归属对照（程序化解析补丁注释分组）：(a)30/(b)5/(c)1/(d)2/(e)2/(f)1=41，**逐条有归属、0 缺失**，与 `ISS-193` 六类计数逐类相符。
- 探针独立重跑（干净 OUT）：compile **341** = OK 327 / FRONTEND_ERR 12 / MISSING_HDR 1 / BACKEND_OTHER 1（`dcvt.c`），**CANNOT_SELECT=0、NOLIBCALL=0**；FP **38** 项×O0/O1/O2 = OK 105 / NOLIBCALL 3（仅 `fmin_f` f32「no libcall for fminnum」）/ ERROR 6（`isnan_d`/`isfinite_d`）/ **CANNOT_SELECT=0**（f64 范围 NOLIBCALL=0 达标）。
- E2E：`make test-picolibc-smoke` **rc=0**，libm 阶段 `libm.o undefined symbols` 14 项含 8 符号、`libm: qemu rc=0 output='libm 0\n'`；`--inject` **rc=1**。阶段期望值按 C99 独立核（floor(2.75)→2、ceil(2.75)→3、trunc(-2.75)→-2、round(2.75)→3、rint(2.5)→2、nearbyint(3.5)→4、fmin/fmax/fmod/sqrt/sin/cos/log）逐项正确。
- 证据脚本：重跑 `<evidence>/<任务ID>/run.sh` **rc=0**（verdict 14 行；`--inject` rc=0、17 行）；**独立注入**（`cp`+md5 备份 `<source>/picolibc/meson.build`，删 `'s_pow.c'` 条目，与 engineer 注入不同）⇒ run.sh **rc=1**：`filter-set==scan-non-ok` **FAIL**（scan-only=['s_pow.c']）+ build/smoke/gates **rc=2** ⇒ `cp` 还原 **md5 一致**（efff4cf5…）⇒ 重跑 **rc=0 回绿**。`check-patch-tree`/`check-source-state` 在注入态正确变红（可失败路径真实可达）。
- 补丁纪律：`series` **14** 行未动（git diff 0）、`meson.build.patch` **99** 行、hunk 非空；`check-patch-tree` rc=0（断言④⑥⑨：补丁集复现源工作树）。完成区「4199 路径 0 失配」全树口径未独立重跑（**采信**），机械等价由断言⑥覆盖补丁目标路径。

**约束核验**：`git status --porcelain -uall` 验前/验后 **逐行 IDENTICAL**、7 个目标文件 md5 全等（未改被测实现、未提交 git）；还原全程 `cp`+md5、无 `checkout/restore/stash`；记录内路径用 `<>` 占位；计数全部现场统计。

**遗留核**：`ISS-193` 存在、6 类齐全（30/5/1/2/2/1）；(a) 类 LLVM 任务已在其 notes **登记为可执行建议**（含「一次可删 30/41」收益），按「只登记不建任务」惯例无独立任务载体 ⇒ 判「已登记」；`--work-dir` 默认仍 `<tmp>/INFRA-057t/smoke`（已披露遗留②）。

**findings**：
- N1（非阻断，文档事实）：`components/picolibc/README.md`「picolibc **自 1.8 起**合并 libc/libm」与所引「version **1.7** §1」不符（合并实为 1.7）⇒ 建议一行改「自 1.7 起」。
- N2（非阻断）：`test_picolibc_smoke.py --work-dir` 默认旧任务路径，建议后续参数化/改名。
- N3（口径注记，非 finding）：完成区「15/15」= 检查项口径（c2 计 1 项 + 注入 2 项 = 15）；verdict 行数为 14/17。非失真、无需返工。

**判决：Accepted** —— 验收 1–8 全过、无阻断项；N1/N2 为整改建议（交主会话/后续任务，不阻塞收尾）。
