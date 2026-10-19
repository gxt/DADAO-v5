# INFRA-090t: musl `arch/dadao/bits/float.h` 常量块换 binary128

**模块**：infra
**项目里程碑**：M8
**依赖**：`ADR-0030`（`Accepted`：`D1` 常量、`D5` 只改 `bits/float.h`、`_l` 不改）、`ADR-0031`（`Accepted`：16 B 值半字顺序，供 `_l` 路径的 128 位值传递）、`LLVM-106t`（前端 `__SIZEOF_LONG_DOUBLE__=16` / `__LDBL_MANT_DIG__=113` + 后端 `f128`；**联动**，本册可先行、`_l` 转正验收须其就绪）、`INFRA-079t`（builtins TF 符号）、`ISS-250`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 问题根源

musl `arch/dadao/bits/float.h` 现状按 **binary64** 写死（`LDBL_MANT_DIG 53` / `LDBL_MAX_EXP 1024` / `DECIMAL_DIG 17`，文件头注释明确「`long double` is identically `double`」）。`ADR-0030 D1` 定案 `long double` = IEEE binary128（`LDBL_MANT_DIG` 113 / `LDBL_MAX_EXP` 16384 / `DECIMAL_DIG` 36），`D5` 要求**只换常量块、不改 `_l` 源码**（上游 113 位分支已在场：`.work/source/musl/src/` 下 `LDBL_MANT_DIG == 113` 命中 53 个文件）。不改则 `libc-test` 的 `math/{acoshl,asinhl,erfcl,lgammal,tgammal}`（`ISS-250`）继续偏移 1.5–10 ulp。

**现成同值模板**：`.work/source/musl/arch/aarch64/bits/float.h`（完整 113 常量块）⇒ 逐字对齐、**不自造数值**。

## 接口规范

- **输入**：
  - `.work/source/musl/`（组件源码检出，`git` 干净基线，musl 1.2.6）
  - `components/musl/patches/**` + `series` + `changelog.md`（补丁集化，`docs/Process-01` 树形补丁 + 一文件一补丁）
  - 决策：`ADR-0030`（`D1`/`D5`）、`ADR-0031`（`D6`/`D7`）
- **输出**：
  - `components/musl/patches/arch/dadao/bits/float.h.patch`：常量块换 binary128（`FLT_EVAL_METHOD 0` 保留；`LDBL_TRUE_MIN`/`MIN`/`MAX`/`EPSILON`、`LDBL_MANT_DIG 113`、`LDBL_MIN_EXP -16381`、`LDBL_MAX_EXP 16384`、`LDBL_DIG 33`、`LDBL_MIN_10_EXP -4931`、`LDBL_MAX_10_EXP 4932`、`DECIMAL_DIG 36`），文件头注释同步改写（删除「identically double」表述），数值逐字取 `arch/aarch64/bits/float.h`
  - `series` 计数不变（同文件已有一条补丁）；`changelog.md` 一条
  - 证据：`.work/evidence/<任务号>/run.sh`（default + `--inject`）
  - 本任务书完成区
- **约束**：只改 `components/musl/**` + 本任务书（+ 台账按裁决）；**不改** `spec/`、`.tao/contracts/`、`contracts/`、`components/llvm-project/**`（归 `LLVM-106t`）；**不改** musl `src/math/**` 任何 `_l` 源码（`ADR-0030 D5`）。

## 验收标准

1. **常量块逐字对齐**：`arch/dadao/bits/float.h` 的 12 个宏与 `arch/aarch64/bits/float.h` **逐字相同**（含 `L` 后缀与有效数字位数）；差异仅限文件头注释。
2. **头文件自洽（独立判据）**：`clang -target dadao-unknown-elf -E -dM` 的 `__LDBL_MANT_DIG__`/`__SIZEOF_LONG_DOUBLE__` 与头内 `LDBL_*` 一致（`LLVM-106t` 就绪时）；未就绪时以「头内数值 = binary128 手算值」独立核对（`DECIMAL_DIG = ceil(1 + 113·log10 2) = 36` 等）。
3. **`_l` 分支在场**：构建后 `nm`/预处理器核 `LDBL_MANT_DIG == 113` 分支被选中（现场统计命中数，不写死）；`_l` 源码零改动（`git diff --name-only` 对账）。
4. **`libc-test` 5 例（`LLVM-106t` 就绪后）**：`math/{acoshl,asinhl,erfcl,lgammal,tgammal}` 静态档 `known-fail/blocked → pass`，且 `TESTCASES-047t` 静态档整体 `fail=0` 不回归（逐例记账）；未就绪时完成区标 `BLOCKED` + 替代证据。
5. **可达 FAIL**：≥2 处注入（例如：把 `LDBL_MANT_DIG` 改回 53、`DECIMAL_DIG` 改回 17）⇒ 对应断言 `[FAIL]`、脚本 rc=1 ⇒ `cp` + md5 还原 ⇒ 回绿、rc=0（**禁** `git checkout`/`restore`/`stash`）。
6. **门控（各留自身 rc）**：`check-patch-tree`、`check-component-changelog`、`check-musl-freshness`、`make check`(L1)；`make build-musl` / `build-musl-shared` rc=0（不并发）。

## 不做

- **不改** `_l` 源码、`libm`、`math` 面实现（`ADR-0030 D5`）。
- **不改** `spec/`、`.tao/contracts/`、`contracts/`、`components/llvm-project/**`。
- **不做** `ISS-250` 之外的 binary128 精度调优；不做 `f80`。
- **不做** 动态档/两档全量复跑（`TESTCASES-*` 归其各自任务）。

## 硬约束

1. 临时目录 `/tmp/opencode/INFRA-090t/`；workdir = 仓库根、相对路径；禁出界 `cd`；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；留证捕**被检命令自身**退出码（禁 `cmd | tee` 吞码）；复杂输出落 `.work/log/infra/`。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定时留问。
6. 用户裁定须把**原话**写入本任务书。
7. 补丁导出纪律：`/tmp` 写入、行数下限、非空 blob、`check-patch-tree` 断言全绿。

## 完成区

**测试结果**：`bash .work/evidence/INFRA-090t/run.sh` **32/32 PASS，rc=0**（30.8 s）；`--inject` **2 处可达 FAIL，rc=0**（`LDBL_MANT_DIG 113→53`、`DECIMAL_DIG 36→17`，`cp -p`+md5 还原后回绿；md5 `7653db34…`）。① 头常量：12 宏与 `arch/aarch64/bits/float.h` **逐字相等**（`LDBL_MANT_DIG 113`/`MAX_EXP 16384`/`MIN_EXP (-16381)`/`DIG 33`/`MIN_10_EXP (-4931)`/`MAX_10_EXP 4932`/`DECIMAL_DIG 36`/`TRUE_MIN`/`MIN`/`MAX`/`EPSILON`/`FLT_EVAL_METHOD 0`）；`clang -dM`：`__LDBL_MANT_DIG__=113`/`__SIZEOF_LONG_DOUBLE__=16`/`__SIZEOF_FLOAT128__=16`。② 编译期断言探针（9×`_Static_assert`，含 `sizeof==16`）rc=0。③ `_l` 113 位分支现场 **53** 文件命中；`git diff <base> -- src/math` **空**。④ **ISS-250 5 例**：`math/{acoshl,asinhl,erfcl,lgammal,tgammal}` **静态 5/5 pass、动态 5/5 pass**（每档 `fail=0`/`known-fail=0`/`blocked=0`；原 `known-fail` 表不再命中）。⑤ `%Lf`/`%La`/`%.20Lf` 探针 11 值（含 ±0、`2^100`、`2^-40`、`1+2^-20`、`1+2^-100`、`1+(1+2^-100)`、`(1+2^-100)^2`）与**独立 Fraction oracle 逐字一致**（oracle rc=0）。⑥ 无回归：10 例小样本**两档 10/10** + 12 例其它静态用例 **12/12**。
**修改文件**：①（组件补丁）`components/musl/patches/arch/dadao/bits/float.h.patch`（常量块 + 注释；`series` 22 不变）、`components/musl/changelog.md`（+1 条）、`components/musl/README.md`（平台事实改 binary128）；②（**越界披露**）`tools/infra/build_musl.py`（builtins archive 按 `clang -print-libgcc-file-name` 现场解析，旧窄化路径仅作 fallback）、`tools/testcases/run_libc_test_user_suite.py`（动态链接行补 builtins；JSON `static_builtins`→`builtins`）；③ `.tao/knowledge/issues.yaml`（`ISS-250` 追加 + `closed`/`resolved_by: INFRA-090t`）；④ 本册完成区+自审。组件树 `.work/source/musl` = base+1 且干净（本地 `commit --amend`，未 push）。
**验收结果**：`make build-musl JOBS=8` **rc=0**（13.54 s，10/10 ELF checks）；`make build-musl-shared JOBS=8` **rc=0**（12.96 s，clean 后全量；`libc.so` sha256 `f74afb9c…`，安装副本全等）；`check-musl-freshness` rc=0（source stamp `df901c44…`）；`check-patch-tree` rc=0（**5 components / 180 patches**，计数不变）；`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check_issues.py` 全 rc=0；**`make check`（L1）rc=0**（34.58 s）。补丁导出 = `tools/infra/make_patch.py musl`（初次 1 written / 21 unchanged；幂等复核 0 written / 22 unchanged）。
**新发现/坑**：① **构建侧 archive 漂移**：`build_musl.py` 硬编码 `lib/linux/libclang_rt.builtins-dadao.a`（INFRA-079t 窄化期，仅 `__muldc3/__mulsc3`），而当前 per-target archive 是 `lib/dadao-unknown-unknown-elf/…`（TF 29 符号）；binary128 令 `libc.so` 新增 18 个 `__*tf*` 未定义 ⇒ `--no-undefined` 链接失败（现场 `.work/log/infra/INFRA-090t-build-musl-shared.log`）。改为按驱动 `-print-libgcc-file-name` 解析（与 `Makefile::install-host` 同源）。② **动态测试链接行缺口**：`libc.so` 以 `--exclude-libs=ALL` 隐藏自有 compiler-rt 成员（上游 musl 口径），用户 TU 与 `src/common/mtest.c` 的 TF libcall **不能**由其解析 ⇒ 047t 动态档 `math/*` 会全 `blocked`；静态行自 TESTCASES-050t 已带 archive，动态行本笔补齐。③ 源码头注释写 `src/math/*.c` 会触发 `-Wcomment`（块注释内 `/*`），已改写。④ `%La` 的 28 位十六进制尾零裁剪、`-0.0` 符号、`2^100` 整数字符串均与 oracle 一致（大端半字序无影响）。
**遗留问题**：① **未跑** `install-host`/L2/L3（按派单）；未 `commit`/`push`、未改 `**状态**`（按派单）。② **越界 2 文件**（`tools/infra/build_musl.py`、`tools/testcases/run_libc_test_user_suite.py`）请 architect 裁定归属；若要求严格零越界，需拆出独立任务后回退这两处。③ `.work/build/compiler-rt-builtins/lib/linux/` 旧窄化 archive 仍在（仅作 fallback），建议 INFRA-079t 收口清理。④ `TESTCASES-047t/046t` 两档**全量**未复跑（归各自任务）；其动态档现依赖驱动补 builtins（本笔已接）。

**越界归属（architect 判）**：`tools/infra/build_musl.py` 与 `tools/testcases/run_libc_test_user_suite.py` 两处改动**归本册**（binary128 跑通所必需的构建/驱动侧修正，不是顺手改）；理由 = 不改则 shared 构建 rc=2（18 个 TF undefined）、`math/*` 全 blocked。

## 审阅记录

#### 第 1 轮 engineer 自审
改动逐行审查（`build_musl.py` / 测试驱动 / float.h / changelog / issues）。判决：**实现正确，越界改动如实披露**。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `build_musl.py` 旧路径导致 `build-musl-shared` rc=2（18 个 TF undefined） | ✅已修 | archive 解析改为 `clang -print-libgcc-file-name`（不猜路径），旧路径仅 fallback | `make build-musl-shared` rc=0；`nm libc.so` 含 `__addtf3`（本地符号） |
| F2 动态链接行无 builtins ⇒ mtest/用户 TU 的 TF libcall 无法解析 | ✅已修 | 动态 link 追加 `cfg["builtins"]`；两档统一前置探测 | 5 例动态 5/5、10 例动态 10/10 |
| F3 `static_builtins` JSON 字段在动态档为 null，语义过期 | ✅已修 | 改为 `builtins`（全仓无其它消费者，`grep` 0 命中） | 两档 JSON 均记录 archive；driver rc=0 |
| F4 探针期望若由实现反推则违 independent oracle | ✅已修 | oracle 用 `Fraction` 精确解码/舍入 binary128，独立派生 `%Lf`/`%La` | 11/11 逐字一致；注入常量后断言翻红 |
| F5 注入还原需可审计、禁 git 还原 | ✅已修 | `cp -p` 备份 + md5 对账；两次还原 md5 全等 | `--inject` rc=0（I1/I2 各 4 项翻红 + 3 项回绿） |
| F6 越界改 `tools/**` 与任务约束冲突 | ⏸延后 | 已在完成区/遗留问题显著披露，待 architect 裁定（拆任务或纳入） | 本笔保留现场 `.work/log/infra/INFRA-090t-*` |


#### 第 1 轮 reviewer 验收（2026-10-19）

**重跑记录**（脚本按新规矩重定向输出至 `/tmp/opencode/review-A/`，仅改 ROOT/TMP/LOG 路径 4 行，断言不变）：
- default rc=0，32/32 PASS（含 A1 12 宏逐字对比、A3 clang -dM 三项、B1 分支命中、C1–C5 门控、D4 oracle 11/11、E1/E2 ISS-250 5+5 两档、F1–F3 回归 22/22）
- `--inject` rc=0，14/14 PASS（I1: `LDBL_MANT_DIG 113→53` → 常量/probe/编译断言均红 → cp+md5 还原回绿；I2: `DECIMAL_DIG 36→17` 同理）

**约束核验**：
1. 12 宏与 `arch/aarch64/bits/float.h` **逐字一致** ✓（`diff` 空，md5 `7653db34…` 与完成区一致）
2. 头文件自洽 ✓（`__LDBL_MANT_DIG__=113` / `__SIZEOF_LONG_DOUBLE__=16` / `__SIZEOF_FLOAT128__=16`）
3. `_l` 分支 53 文件命中 ✓；`git diff` 对 `src/math` 空 ✓
4. ISS-250 5 例两档 5/5 + 5/5 ✓；10+12 回归样本均 pass ✓
5. 注入两处可达 FAIL + cp+md5 还原回绿 ✓
6. 门控：`check-patch-tree` 180 ✓、`check-musl-freshness` ✓、`make check`(L1) ✓、`check-run-artifacts` ✓

**如实性抽查**：① 12 宏 diff 空 ✓；② md5 `7653db341ee9ed90224c53134bd78948` 与完成区前 8 位一致 ✓；③ oracle 11 行全 PASS 含 ±0/2^100/2^-40/add/mul ✓

**判决**：**Accepted** — 所有验收标准逐条通过，无阻断发现。
