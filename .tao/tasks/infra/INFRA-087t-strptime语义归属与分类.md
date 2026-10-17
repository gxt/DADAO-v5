# INFRA-087t: `strptime` 的 `%s` 语义归属与分类订正（musl 语义为准）

**模块**：infra
**项目里程碑**：M8
**依赖**：`TESTCASES-047t`（现场来源 = 静态档第 2 轮重跑）、`ISS-251`（本册对应 issue）、`INFRA-076t`（musl 1.2.6 取源与锁定 ⇒ 语义权威版本）；口径依据 `ADR-0025 D7`（golden 对照目标 = RISC-V + **musl** ⇒ 本 target 的 libc 语义以 musl 为准）
**状态**：待开始

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
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
