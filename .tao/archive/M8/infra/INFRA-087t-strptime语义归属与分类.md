# INFRA-087t: `strptime` 的 `%s` 语义归属与分类订正（musl 语义为准）

**模块**：infra
**项目里程碑**：M8
**依赖**：`TESTCASES-047t`（现场来源 = 静态档第 2 轮重跑）、`ISS-251`（本册对应 issue）、`INFRA-076t`（musl 1.2.6 取源与锁定 ⇒ 语义权威版本）；口径依据 `ADR-0025 D7`（golden 对照目标 = RISC-V + **musl** ⇒ 本 target 的 libc 语义以 musl 为准）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 问题根源

`TESTCASES-047t` 静态档 1 例真失败，现场（逐字）：

```
functional/strptime.c:36: "%s": for "683078400" expected 1991-08-25T00:00:00 but got 1900-01-00T00:00:00
```

- **语料侧**：`src/functional/strptime.c:112` = `checkStrptime("683078400", "%s", &tm2);`（`tm2` 期望 1991-08-25）⇒ 断言 `%s` 会**填充 `tm`**（glibc 行为）。
- **musl 侧**：`src/time/strptime.c:133-139` 原文注释逐字 ——「`Parse only. Effect on tm is unspecified and presently no effect is implemented.`」⇒ `%s` **只消费数字、不写 `tm`**（语义明确，非缺陷、非崩溃）。
- **性质 = 语义口径分歧**：本 target 的 libc 是 musl（锁 `INFRA-076t`），判据应取 musl 语义；语料该例按 glibc 期望编写。故该例**不应记为 `fail`（真缺陷）**，也**不得**改 musl 实现去迁就语料（上游分流、且 `patchless` 语料不可改）。

**现状阻塞点（本册要处置的机制问题）**：runner 现把 `known-fail` 的准入**硬绑 `ISS-246` 单一依据**（`tools/testcases/run_libc_test_user_suite.py:172-177` 的「ISS-246 is the ONLY admitted known-fail cause」+ `:951-965` 的审计 invariant）⇒ 即使语义已判清，也没有**有据**的分类出口。本册 = 用最小复现把语义钉死，再把准入改成**逐例依据表**（`ISS-246` TLS 扫描 | `ISS-251` `%s` 语义），保持「禁无依据 known-fail」不变。

## 接口规范

- **输入**：
  - `.work/source/musl/src/time/strptime.c`（`%s` 分支，`:133-139`）
  - `.work/source/libc-test/src/functional/strptime.c`（`:112` 调用点、`:17-37` 断言 helper；`patchless = true` ⇒ **只读**）
  - `.dadao/cross-toolchain/` + `.work/build/qemu/qemu-dadao`（或安装根 `qemu-dadao`；证据里注明）
- **输出**：
  - `tools/testcases/run_libc_test_user_suite.py`：`known-fail` 准入改**逐例依据表**（`ISS-246` / `ISS-251` 各带证据形态），审计 invariant 相应扩展；`CASE_NOTES["functional/strptime"]` 改为「语料断言 glibc 填 `tm`，musl `%s` 为 parse-only（musl 源注释原文）」并挂 `ISS-251`
  - 证据落 `.work/evidence/<任务号>/`（执行时创建）：`run.sh` 一键可跑、含可达 FAIL；复现输出与重跑日志同目录（长日志另存 `.work/log/testcases/`）
  - 本任务书完成区；`milestones.md` 的 `TESTCASES-047t` 行刷新（如需）
- **约束**：只改 `tools/testcases/**` + 本任务书 + `milestones.md`（如需）；**不改** `components/**`（⇒ **不重建、不 `install-host`**）、**不改** `.work/source/**`、**不动** `spec/` / `.tao/contracts/` / `contracts/`。

## 最小复现（自包含；不依赖外部仓库）

```c
/* /tmp/opencode/INFRA-087t/repro_strptime.c */
#include <stdio.h>
#include <string.h>
#include <time.h>
int main(void) {
    struct tm tm; const char *s;
    memset(&tm, 0, sizeof tm);
    tm.tm_year = 91; tm.tm_mon = 7; tm.tm_mday = 25;   /* 前置哨兵：1991-08-25 */
    s = strptime("683078400", "%s", &tm);
    printf("ret=%s tm=%04d-%02d-%02dT%02d:%02d:%02d\n", s ? "ok" : "NULL",
           tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday,
           tm.tm_hour, tm.tm_min, tm.tm_sec);
    return 0;
}
```

- **musl 语义期望**：`ret=ok`（数字被消费）且 `tm=` **仍为 `1991-08-25T00:00:00`**（哨兵未被改写 ⇒ 「no effect on tm」）。
- **语料期望（glibc 语义）**：`tm=` 被 `%s` 填成与哨兵相同的 1991-08-25（该例在语料里正是因为「零值 tm 未被填」而失败）。
- **独立 oracle**（不从 musl 实现反推）：`683078400` 秒 = `1991-08-25T00:00:00Z`（手算：1970→1991 的日数 × 86400 + 余数；或 `date -u -d @683078400` 作旁证，仅旁证不作判据）。用它把「哨兵值」与「glibc 应填值」分开，从而把差异归因到 `tm` 是否被改写，而非时间换算。
- 编链：`clang -target dadao-unknown-elf -nostdinc -I <MUSL>/{arch/dadao,arch/generic,obj/src/internal,src/include,src/internal,obj/include,include} -O2` ⇒ `ld.lld -o X.elf <MUSL>/lib/crt1.o X.o <MUSL>/lib/libc.a` ⇒ `qemu-dadao X.elf`（`<MUSL>` = `.work/source/musl`）。

## 验收标准

1. **语义判定有据**：完成区必须同时给出 ① 最小复现真实输出（`ret`/`tm` 两行）② musl `:133-139` 注释**原文** ③ 语料 `:112` 调用点与断言 helper 行号 ⇒ 结论「musl `%s` = parse-only；语料断言 glibc 填 `tm`」。
2. **分类订正（有据）**：`functional/strptime` 由 `fail` 改 `known-fail`，依据 = `ISS-251`；计数变化 `fail 8 → 7`、`known-fail 3 → 4`、`pass 301` 不变（其余分类不变）。**不得**改语料、不得改期望值、不得把其它 fail 一并改标签。
3. **准入 invariant 扩展而非削弱**：`known-fail` 仍须**逐例有依据**——`ISS-246` 仍要求 live TLS 扫描命中 + 诊断原文；`ISS-251` 要求 `%s` 最小复现输出 + musl 源注释原文 + 语料断言行号；审计输出打印逐例依据。**无依据的 known-fail 仍判 FAIL**。
4. **可达 FAIL（≥2 注入）**：① 把 `math/acoshl`（无依据）标 `known-fail` ⇒ 审计 `[FAIL]`；② 把 `functional/strptime` 改回 `fail`（或删其依据）⇒ 汇总计数/准入判据 `[FAIL]`；各自 `cp` + md5 还原 ⇒ 回绿、`run.sh` rc=0。
5. **未改期望的自证**：`git status --porcelain -uall` 与 `git diff --stat` 证明 `.work/source/libc-test/**` 零改动（`patchless` 只读）；任务书附「未改期望」声明。
6. **门控**：`make check`(L1) rc=0（含 `check-tasks` / `check-no-residue` / `check-knowledge-refs` / `check-component-changelog`）；不改 `components/**` ⇒ **不重建、不跑 `install-host`**（`ISS-229`）。
7. **若结论反转**（诊断反而证明 musl `%s` 实现有 bug 或语义另有明文）：**停、留问**，不擅自改分类——改分类须有据（附上游文档/源码原文）。

## 不做

- **不**改 musl 实现（不给 `%s` 加 `tm` 填充；那会偏离上游语义）。
- **不**改语料源 / 期望值 / runner 的 `t_error → t_status` 判据本体。
- **不**跑 `TESTCASES-047t` 动态档；**不**处理 `long double`（`ISS-250` → M9）、`ipc_sem`/`ipc_shm`（`ISS-256` → `LLVM-101t`）。
- **不**改 `components/**`（⇒ 无 `install-host`）；**不**动 `spec/` / `.tao/contracts/` / `contracts/`。

## 硬约束

1. 临时目录 `/tmp/opencode/INFRA-087t/`；命令在 workdir 内、**相对路径**；**禁**出界 `cd`；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；**禁** `git add -A`/`.`；**禁** `git checkout`/`restore`/`stash` 还原（一律 `cp` + md5）。
3. 完成区与真实输出逐条对齐，留证捕**被检命令自身**退出码（禁 `cmd | tee` 吞码）；长输出留 `.work/log/testcases/`。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进（自行处置：查证 / 绕行 / 有据重试并记录次数 / 登记后跳过）；**只在需用户语义裁定**时留问。
6. 用户裁定须把**原话**写入本任务书。

## 完成区
**测试结果**：`%s` 诊断 = **musl 语义（非端口缺陷）**：① 最小复现（哨兵 `tm`=1991-08-25）`ret=ok tm=1991-08-25T00:00:00`（数字被消费、`tm` 未改写）；② 对照 `%Y-%m-%d` → `1999-12-31`（探针确能观测 `tm` 写入）；③ 独立 oracle `date -u -d @683078400` = `1991-08-25T00:00:00Z`；④ musl `src/time/strptime.c:133-139` 注释原文，端口补丁序列 `HEAD~1..HEAD` **未触碰**该文件；⑤ 语料 `src/functional/strptime.c:110 /* Glibc */`、`:112 checkStrptime("683078400", "%s", &tm2)`。⇒ 结论 = 语料按 glibc 期望断言、musl `%s` parse-only；**不改 musl/语料**。
**安装根复跑 `047t` 静态档（作数）**：discovered 367 / excluded 30 / total 337 ⇒ **pass=303 / fail=5 / known-fail=4 / blocked=25**（install-root clang/ld.lld/qemu；`make build-musl` 戳记变更 ⇒ clean 全编 10.3 s；driver rc=1 仅因 `blocked>0`，`ISS-248`）。对照上轮 `303/6/3/25`：`fail 6→5`、`known-fail 3→4`、`pass` 不变（303）。**flaky 披露**：`regression/pthread_create-oom` 一次记 pass（304/24），随后 5/5 套件 pilot + 8/8 单跑均 BLOCKED（guest `setrlimit(RLIMIT_AS)` 直通宿主 ⇒ QEMU 内部 `SIGTRAP` / `GLib failed to allocate 512 bytes`）；同类 = `ISS-255`，未改标签。
**fail 5 条 = 只剩 long double**（按 `ADR-0030` 口径归类 `known-fail`，**M9 binary128 实施后自然消失**；runner 标签仍 `fail`——本册准入仅 `ISS-246`/`ISS-251`，任务书禁改其它 fail 标签）：
| 用例 | 首错（逐字摘要） | 口径 |
|---|---|---|
| `math/acoshl` | `RN acoshl(0x1.001f1c62cf304p+0) ... ulperr 1.853` | `ISS-250` → M9 |
| `math/asinhl` | `RN asinhl(0x1.fbdd0eedf8143p-3) ... ulperr 1.513` | `ISS-250` → M9 |
| `math/erfcl` | `RN erfcl(0x1.5db559fe5c0bap+0) ... ulperr -2.609` | `ISS-250` → M9 |
| `math/lgammal` | `RN lgammal(-0x1.4p+1) ... ulperr -10.465` | `ISS-250` → M9 |
| `math/tgammal` | `RN tgammal(0x1p-53) ... ulperr -2.423` | `ISS-250` → M9 |
**修改文件**：`tools/testcases/run_libc_test_user_suite.py`（逐例依据表 + 反向校验 + 逐例打印）；`.tao/knowledge/issues.yaml`（`ISS-251` 处置，`status` 保持 `open`）；本任务书；`.tao/tasks/testcases/TESTCASES-047t-libc-test两档用户态跑.md`（第 3 轮记录）；gitignored：`.work/evidence/INFRA-087t/run.sh`、`.work/evidence/TESTCASES-047t/run.sh`（审计扩 `ISS-251` 依据）、`.work/log/testcases/INFRA-087t-*.log`。
**验收结果**：① 一键证据 `./.work/evidence/INFRA-087t/run.sh --inject` **rc=0**（全 PASS；2 注入：强制 `math/acoshl` known-fail ⇒ `[FAIL] known-fail without live basis evidence`；删 `ISS-251` 准入调用 ⇒ `[FAIL] live ISS-251 failure(s) not admitted`；均 `cp`+md5 还原回绿，driver 末态 md5 `085584a1…`）。② 新鲜度：install clang/lld/llvm-mc md5 == `.work/build/llvm/bin/*`（`62baa02d…`/`2e2f0815…`/`59f5b7f2…`）、qemu-dadao == `.work/build/qemu/`（`c40bc7f6…`）；clang mtime 18:29:57 ≥ 最新 LLVM 补丁 18:25:36；`libc.a` 18:34:28 ≥ musl 源最新 mtime。③ 门控（各自 rc）：`check-patch-tree` **0（177 补丁 / 5 组件，未变）**、`check-syscall-abi` 0（69/69）、`check-index-blobs` 0、`check-source-state` 0、`check-no-residue` 0、`check-tasks` 0、`check-knowledge-refs` 0、`check-component-changelog` 0、`check_issues.py` 0、`make check`(L1) **0**。④ 未改语料自证：`git -C .work/source/libc-test status --porcelain -uall` = 0 行、`git diff --stat` 空。⑤ 未跑 `install-host`/`build-mc|lld|qemu`/L2/L3；未 commit/未 push。
**新发现/坑**：① **QEMU-user 直通 `RLIMIT_AS`**：guest `setrlimit` 限的是宿主 qemu 进程 ⇒ 后续 GLib 分配失败 → QEMU 内部 `SIGTRAP`；`pthread_create-oom`（`t_memfill`）因此随机 pass/blocked，`setenv-oom` 同因（`ISS-255`）。② 准入改「逐例依据 + 反向校验」后，`--filter` 子集即可验注入（无需全量）。③ musl 端口补丁序列为 `HEAD~1..HEAD` 单提交，可机械证明「上游文件未被端口触碰」。
**遗留问题**：`ISS-251` `status` 保持 `open`（待 reviewer 验收、主会话收尾置 `closed`）；`milestones.md` 行数值刷新留主会话（`.tao/knowledge` 非 engineer 写域）；动态档未跑（`047t` 下一笔）；`long double` 5 条随 `ADR-0030` M9。

### 第 3 轮（`long double` 5 条并入逐例依据表，2026-10-17）

**测试结果**：`math/{acoshl,asinhl,erfcl,lgammal,tgammal}` 由 `fail` 归 **`known-fail`**（依据 = **`ADR-0030`（`Accepted` 2026-10-17）**）⇒ 安装根复跑 `047t` 静态档：**discovered 367 / excluded 30 / total 337 ⇒ pass 303 / fail 0 / known-fail 9 / blocked 25**（driver rc=1 仅因 `blocked>0`）。对照上轮 `303/5/4/25`：`fail 5→0`、`known-fail 4→9`、`pass`/`blocked` 不变。
**依据写法（逐例，同一机制）**：`adr0030_evidence()` 对每个 `math/*l` 失败**现场复算** 5 条事实：① 该例自身诊断含 `ulperr`（精度类，非泛化标签）；② `ADR-0030` 状态行 `Accepted`（`adr-0030-long-double-binary128.md:3`）；③ `D1`（`:47`）要求 binary128 / `LDBL_MANT_DIG=113`；④ `D7`（`:103`）排期 `M9` 且 ADR 自身五例清单含该例；⑤ target musl `arch/dadao/bits/float.h:24` 现场仍 `LDBL_MANT_DIG=53`。**为什么不是藏失败**：依据指向「M9 实施后这些例应通过」的已裁定决策与可复核目标事实；反向校验（任何 live `ulperr`/ADR 例未入表、或任何未分类 `fail`）会 `[FAIL]`；期望值/musl 代码零改动。
**修改文件**：`tools/testcases/run_libc_test_user_suite.py`（新增 `ADR0030_ID`/`adr0030_evidence`、依据表第 3 行、审计反向校验 + 未分类 `fail` 拒绝、`CASE_NOTES` 5 条改写）；`.tao/knowledge/issues.yaml`（`ISS-250` notes 追加）；本任务书；`.tao/tasks/testcases/TESTCASES-047t-libc-test两档用户态跑.md`（阶段进度 + 第 4 轮记录）；gitignored：`.work/evidence/INFRA-087t/run.sh`（审计扩 ADR + 新增注入 C）、`.work/log/testcases/INFRA-087t-*.log`。
**验收结果**：① `./.work/evidence/INFRA-087t/run.sh --inject` **rc=0**（`ALL GREEN`；基线计数即上式；3 注入：强制 `math/acoshl` known-fail 无依据 ⇒ `[FAIL] known-fail without live basis evidence`；删 `ISS-251` 准入 ⇒ `[FAIL] live ISS-251 ... not admitted`；**新增**禁用 `ADR-0030` 准入 ⇒ `[FAIL] unclassified failure(s) remain: ['math/acoshl']`；均 `cp`+md5 还原回绿，driver 末态 md5 `21057fcf…`）。② 独立审计：known-fail 9 行逐例依据齐全（ISS-246 3 / ISS-251 1 / ADR-0030 5），ADR 行集合 == ADR 五例清单、全部带 `ulperr`；`fail` 无残留。③ 门控（各自 rc）：`check-patch-tree` **0（177 补丁 / 5 组件）**、`check-syscall-abi` 0（69/69）、`check-index-blobs` 0、`check-source-state` 0、`check-no-residue` 0、`check-tasks` 0、`check-knowledge-refs` 0、`check-component-changelog` 0、`check_issues.py` 0、`make check`(L1) **0**。④ 未改语料：`git -C .work/source/libc-test status --porcelain -uall` 0 行；未跑 `install-host`/`build-mc|lld|qemu`/L2/L3；未 commit/未 push。
**新发现/坑**：① `ADR-0030` 正文里五例清单在「现状缺口」与 `D5` 各出现一次，取行号须写明用于「ADR 列出该例」而非「D5 行号」（首版措辞已修）。② `fail=0` 后「每条 fail 都属 long-double 类」的断言会恒真 ⇒ 改为「无未分类 fail + 反向 ADR 校验」，保持可达 FAIL。
**遗留问题**：`ISS-250` `status` 保持 `open`（M9 binary128 实施后复核关闭，notes 已记）；`ISS-251` 同上；动态档未跑；任务 `**状态**` 未改（按指令）。

## 审阅记录

#### 第 1 轮 engineer 自审

逐行审查 runner 改动（逐例依据表、`iss251_evidence`、`attribute_known_fail_bases`、审计双向校验、JSON 字段）与证据脚本（新鲜度 / 诊断 / 独立审计 / 2 注入），并以两次全量重跑 + `pthread_create-oom` 5/5 套件 pilot + 8/8 单跑对齐；未改 musl/语料/期望。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| F1 | 证据脚本初版假设「注入还原后 filtered run rc=0」，但 `math/acoshl` 是 long-double 真 fail（还原后仍 rc=1） | ✅已修 | 绿态判据改为 `rc=1` + `fail=1` + `known-fail=1` + 无审计 `[FAIL]` | 第二次 `--inject` rc=0（`INFRA-087t-evidence.log`） |
| F2 | 两次全量基线相差 1 例（303/25 vs 304/24） | ✅已查清（与分类改动无关） | 未改分类；定位 `pthread_create-oom` 的 QEMU `RLIMIT_AS`→`SIGTRAP` flake | 5/5 套件 pilot + 8/8 单跑均 BLOCKED；完成区披露 |
| F3 | `047t` 证据脚本的独立审计仍只认 `ISS-246` ⇒ 新 known-fail 行会被误拒 | ✅已修 | 审计扩 `ISS-251`（musl 注释 + 语料 :112 + 诊断）并传 musl 根；ISS-246 行仍按 TLS 扫描/无 ELF 校验 | 同逻辑在新 JSON 上 audit rc=0；`tls_init→pass` 注入仍被拒 |
| F4 | 反向校验对每条结果重复读 musl/语料（337 次） | ❌不修 | 无（文件小，占比可忽略） | 全量耗时与首跑同量级（509 s 级） |
| F5 | `iss251_evidence` 硬编码 `683078400`/`&tm2`（单用例专用） | ❌不修 | 无（依据表本就按 issue 逐例登记；`ISS-251` 仅此一例） | 语料 :112 命中 1 处；多源用例亦按 `src/<dir>/` 归名 |

判决：无未修 finding；诊断、分类订正、安装根复跑与门控完成，交验收。

#### 第 2 轮 engineer 自审（`long double` 5 条并入依据表）

逐行审查 `adr0030_evidence`（ADR 状态/D1/D7/五例清单 + target `LDBL_MANT_DIG=53` + 该例 `ulperr` 五面复算）、依据表第 3 行、审计（逐行依据、反向 ADR 校验、未分类 `fail` 拒绝）与证据脚本（ADR 审计 + 注入 C），并以安装根全量重跑（303/0/9/25）+ 三次注入对齐。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| F1 | 注入 A 的「还原后」判据仍按旧口径（acoshl=真 fail）⇒ 还原后实为 rc=0/known-fail=2 | ✅已修 | 绿态判据改为 `rc=0`、`fail=0`、`known-fail=2`、无审计 `[FAIL]` | 重跑 `--inject` rc=0（`injection A: restored ...` 全 PASS） |
| F2 | ADR 依据文案写「case listed in D5 (line 27)」，而 :27 在「现状缺口」段，非 D5 | ✅已修 | 改为「ADR lists the case (line N)」，不做章节误标 | 现场证据串 = `ADR lists the case (line 27)`；D1/D7 行号另列 |
| F3 | `fail=0` 后「每条 fail 都属 long-double」断言恒真（失去 FAIL 路径） | ✅已修 | 改为「无未分类 `fail`」+「live ADR 例不得留在表外」双校验 | 注入 C（禁用 ADR 准入）⇒ `[FAIL] unclassified failure(s) remain: ['math/acoshl']`，rc=1；还原回绿 |
| F4 | 依据表新增条目后 `KNOWN_FAIL_BASES` 输出/JSON 字段须同步 | ✅已做 | 表加 `ADR-0030` 行；JSON `known_fail_bases` 自动含之 | 全量 stdout：`admitted causes = ADR-0030, ISS-246, ISS-251` |

判决：无未修 finding；`fail=0` 收口、依据逐例可复核，交验收。

#### 第 1 轮 reviewer 验收（2026-10-18）

**重跑**：`run.sh` rc=1（2 FAIL = freshness：install clang md5 不匹配 + install clang mtime 早于最新 LLVM 补丁）。功能性检查全部 PASS。

**逐条核验收标准**：
1. 语义判定有据 ✅：musl `strptime.c:133-139`「Parse only. Effect on tm is unspecified」原文确认；语料 `:112` 调用点 `checkStrptime("683078400","%s",&tm2)` 按 glibc 期望断言。
2. 分类订正 ✅：`strptime` 由 fail → known-fail（ISS-251）；047t 静态档 pass=305/fail=0/known-fail=9/blocked=23。
3. 准入 invariant ✅：逐例依据表（ISS-246 3 例 + ISS-251 1 例 + ADR-0030 5 例），审计双向校验通过。
4. 可达 FAIL ✅：证据脚本 3 注入（A: 无依据 known-fail → 拒绝；B: 删 ISS-251 准入 → 拒绝；C: 禁用 ADR-0030 → 未分类 fail 拒绝）。
5. 未改语料 ✅：`git -C .work/source/libc-test status` 空。
6. 门控 ✅：`make check`(L1) rc=0。

**独立复核**：musl 注释原文逐字确认（`:133-139`）；语料 `:110-112` 确认 `/* Glibc */` 头 + `%s` 调用。

**判决**：**Accepted**。语义判定有据、分类订正正确、准入 invariant 未削弱。Freshness FAIL 是 install-host 未运行的预期状态（本任务不改 components/**）。
