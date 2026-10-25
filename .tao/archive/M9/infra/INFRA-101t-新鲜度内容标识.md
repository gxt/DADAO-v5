# INFRA-101t: 新鲜度门控改用内容标识（build-id）替代 mtime 代理

**模块**：infra
**项目里程碑**：M9（工程效率）
**依赖**：`INFRA-096t`（新鲜度门控落地）、`INFRA-098t`（`llvm-nm`/`llvm-readelf` 入安装根）、`INFRA-099t`（门控互斥，已落地）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 现象（2026-10-22，`LLVM-122t` 夜跑现场）

- 改 `.td` ⇒ `build-mc` 重 link `clang`（确定性构建，**内容逐字节相同**）⇒ 安装根里 `clang` 的 **mtime 变**；
- `check-musl-freshness` / `check-builtins-freshness` 双双判 stale ⇒ 强制重建 musl / builtins；
- 因 L2（`check-modules`）经 `test-semihost` **内嵌 `install-host`**，一次 L2 就触发一次重装 + 重建；
- engineer + reviewer 各跑一次 L2 ⇒ **双倍**。`LLVM-122t` 单册因此耗时 **4 h 28 min**（其余 FP 册 ~20 min）。

### 现场事实（代码位置，2026-10-22 核）

- `tools/infra/build_musl.py:276-288`：`toolchain_stamp()` 对 `STAMP_TOOLS = ("clang","ld.lld")` 生成
  `"<tool> -> <realpath> size=<bytes> **mtime=<ns>** <--version 首行>"`，写入 `obj/.dadao-toolchain-stamp`；
  `check_musl_freshness.py` 重算并**逐字比较**。
- `tools/infra/check_builtins_freshness.py:187-207`：判据是 `archive mtime >= clang mtime` 与"归档成员 mtime 不早于 clang"。
- `Makefile:401-402` 的 `atomic-install` = `cp -aL` + `mv`（**mtime 由 `cp -a` 保留**；问题不在拷贝，在**源被重建**）。
- `ctime` 已在 `ISS-263` 中明确排除（重拷贝会 bump ctime，不是工具链变化）。
- **两个工具都带 GNU build-id**（现场 `readelf -n`）：
  - `clang`：`de2e20d7e585817e19924fa5b26746ca5099cb59`
  - `ld.lld`：`585596725c4908cd13d42a9b4303dbfc77ec6a55`

### 结论

现状**并未判断"内容是否变化"**，只判断 mtime；确定性重建 ⇒ 假 stale。应改为**内容派生标识**。

## 目标

1. `toolchain_stamp()` 用 **build-id**（无 build-id 时退 `sha256`）替代 `mtime`；
2. builtins 门控用"**归档构建时记录的 clang build-id** == 当前 build-id"替代 mtime 排序；
3. **旧 stamp 迁移**：无 build-id 的旧 stamp ⇒ 首次判 stale（一次重建），并在输出里明示"migrating stamp"；
4. 结果：**重建但内容相同 ⇒ 绿**；**内容真变 ⇒ 红**。

## 接口规范

- **输入**：`tools/infra/build_musl.py`、`tools/infra/check_musl_freshness.py`、`tools/infra/check_builtins_freshness.py`、`Makefile`（builtins 归档处需写 sidecar 记录）。
- **输出**：
  1. build-id 读取实现（**优先纯 Python 解析 ELF note**，避免依赖 `readelf` 是否存在；退路 `sha256` 且打印警告）；
  2. musl stamp 新格式（含 `build-id=`，不含 `mtime=`）；
  3. builtins sidecar（如 `obj/.dadao-builtins-toolchain`，记录 `clang build-id` + `ld.lld build-id`）与门控改写；
  4. 两个门控各自 `--self-test` 覆盖新判据；
  5. 证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改构建产物本身、不改 `spec/`/`contracts/`、不改门控**语义**（仍要求"对象由当前工具链产生"）；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 内容标识

- 主：ELF `NT_GNU_BUILD_ID`（读 note，成本 KB 级）；两个工具均有 ⇒ 正常路径不退化。
- 退路：无 build-id（非 GNU ld 工具链）⇒ `sha256`（并打印一次警告，说明成本）。
- **禁止**把 mtime/size 作为"内容"判据的任何组成部分（size 可留作显示，不作判据）。

### B. musl stamp

```
clang -> /path/to/clang build-id=de2e20d7… <--version 首行>
ld.lld -> /path/to/ld.lld build-id=5855967… <--version 首行>
```

- 旧格式（含 `mtime=`）⇒ 视为 stale + 打印 `stamp format migrated`；
- 比较仍是**逐字字符串相等**（最小改动）。

### C. builtins 门控

- 归档生成处写 sidecar：`clang build-id=<...>`、`ld.lld build-id=<...>`、`source digest`（沿用既有 source stamp 思路）；
- `check_builtins_freshness.py` 判据改为 sidecar 的 build-id == 当前 build-id；**不再**用 mtime 排序；
- 旧归档无 sidecar ⇒ stale（一次重建）。

### D. 不得借机放宽

- 其它断言（成员清单、source digest、`--self-test` 的注入）**保持不动**；只替换"工具链是否变化"的判据。

## 验收标准

1. `toolchain_stamp()` 输出**不含 `mtime=`**、含 `build-id=`（现场打印）。
2. **仅 mtime 变**（`touch` 安装根 clang）⇒ **两个门控都绿**（真实输出）。
3. **内容变**（改 stamp 里记录的 build-id，或换一个不同 build-id 的二进制到临时树）⇒ **红**（真实输出）。
4. **真实工作流**：`touch` 一个 `.td` 源 → `make install-host`（重 link，内容相同）→ `make check-musl-freshness` **rc=0**、`make check-builtins-freshness` **rc=0**，**无需** `build-musl-shared`。
5. **旧 stamp 迁移**：把 stamp 写回旧格式 ⇒ 判 stale 且输出含 `migrated`；重建后转新格式。
6. 两个门控 `--self-test` 全绿，且**新增注入各可达 FAIL**（内容变必须红 / 仅 mtime 变必须绿）。
7. `make check`（L1）rc=0；`make check-modules`（L2）rc=0；`check-run-artifacts` rc=0。
8. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（stamp 路径、builtins 门控逻辑、build-id 读取方式）。
2. 实现 build-id 读取 + musl stamp 改造 + 迁移提示。
3. builtins sidecar + 门控改写。
4. 四种注入（mtime-only 绿 / 内容变红 / 旧 stamp 迁移 / 正常重建绿）。
5. L1/L2 + 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- 仅 `touch` clang（mtime 变、内容不变）⇒ 期望**绿**；若实现仍用 mtime ⇒ 红（证明判据确实换了）。
- 把 sidecar/stamp 里记录的 build-id 改成另一个值 ⇒ 期望**红**；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不改变 L2 内嵌 `install-host` 的结构（另一议题：`--no-rebuild` 快速路径）。
- 不处理 `clang` 无 build-id 的构建配置（退路 sha256 已覆盖）。
- 不动 `ISS-263` 的 ctime 排除逻辑。

## 完成区

**测试结果**：证据 `.work/evidence/INFRA-101t/run.sh` **38/38 PASS，rc=0**（日志 `.work/log/infra/INFRA-101t-evidence.log`）；`toolchain_id.py --self-test` 8/8、`check-musl-freshness --self-test` 10/10、`check-builtins-freshness --self-test` 12/12；L1 `make check` rc=0、L2 `make check-modules` rc=0、`check-run-artifacts` rc=0。
**修改文件**：`tools/infra/toolchain_id.py`（新）、`tools/infra/build_musl.py`、`tools/infra/check_musl_freshness.py`、`tools/infra/check_builtins_freshness.py`、`Makefile`（build-builtins 写 sidecar + 注释/help）、`.tao/tasks/infra/INFRA-101t-新鲜度内容标识.md`、`.tao/knowledge/milestones.md`（流水行状态）、`.work/evidence/INFRA-101t/run.sh`。
**验收结果**：
1. 新 stamp（现场）：`clang -> …/bin/clang build-id=de2e20d7e585817e19924fa5b26746ca5099cb59 clang version 23.1.3 (…)` / `ld.lld -> …/bin/lld build-id=585596725c4908cd13d42a9b4303dbfc77ec6a55 LLD 23.1.3`；`grep -c mtime=` = 0、`size=` = 0。
2. **仅 mtime 变**（`touch` 安装根 clang；build-id 不变）：`check-musl-freshness` rc=0、`check-builtins-freshness` rc=0，stamp 文件未被改写（md5 不变）。
3. **内容变**：改 stamp 记录的 build-id ⇒ musl 门控 rc=1（`actual=different`）；改 sidecar 记录的 build-id ⇒ builtins 门控 rc=1（`recorded clang identity == current`）；`cp` 还原后 md5 一致、两门控 rc=0。
4. **旧格式迁移**：写回 `mtime=` 戳记 ⇒ rc=1 且输出 `stamp format migrated … legacy mtime= stamp`；`make build-musl-shared JOBS=8` rc=0 后转新格式（build-id=2/mtime==0），且内容与注入前逐字节相同（md5 `da0a526b…`）。
5. **真实工作流**：`touch` `DADAOInstrInfo.td` + 强制 link（见坑①）⇒ `make install-host JOBS=8` rc=0（297 s，`Linking CXX executable bin/clang-23`）；clang sha256 `a66f070b…`、build-id 均不变，安装副本已重拷（mtime 变），两门控 rc=0，musl stamp md5 未变 ⇒ **不需要** `build-musl-shared`。
6. sidecar（`.work/build/compiler-rt-builtins/.dadao-builtins-toolchain`）：clang/ld.lld `build-id=` + `archive-sha256=1941b71d…` == 归档 sha256；147/147 成员按**内容**对 `.c.o`（mtime 排序已删）。
**新发现/坑**：① `touch` 一个 `.td` **不会** relink clang——ninja 重跑 tablegen 后见 `.inc` 逐字节相同（restat）就停在 link 前；要复现「重 link 内容不变」须删 link 产物 `bin/clang-23`（删 `bin/clang` 只会让 ninja 重建符号链接）。② 任务书 C 的「source digest」落地为 sidecar 的 `archive-sha256`（三副本 sha256 已互绑，sidecar 再锚定构建时内容）；如需对 compiler-rt 源码再做摘要，属另立判据。③ 无 build-id 退 `sha256` 会读 4.3 GB（clang），仅非 GNU 工具链路径触发并打印一次告警。④ 旧戳记迁移代价 = 一次完整 musl 重建（20.8 s）。
**遗留问题**：`tools/infra/build_picolibc.py:96-110` 的 `toolchain_stamp()` 仍是 size+mtime+ctime 戳记（同一假 stale 类别；本册按任务边界未改，建议后续册改 build-id）。L2 内嵌 `install-host` 的结构按任务边界未动；`ISS-263` 的 ctime 排除逻辑未改。

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

### 第 2 轮 reviewer 验收（2026-10-22，独立重跑；判决 = Accepted）

**重跑记录**（本人执行，日志 `/tmp/opencode/INFRA-101t-review/`；rc 取被检命令自身 `cmd >log; echo $?`，无 `| tee`）
1. 提交范围：`git show --stat e2a9bcd2` 仅任务书 1 个文件 +18 行（第 1 轮审阅记录）；`.EXIT` 已改描述式引用（只提目录、不指向不存在文件）。
2. 代码审查：C07 补 `<<'PYEOF'` heredoc（程序真从 stdin 喂入），用**独立** `readelf -n`+regex 取实际 build-id、`hashlib.sha256` 独算 archive 摘要（不依赖被测 `toolchain_id.py`），任一不匹配 ⇒ `sys.exit(1)` ⇒ `C7=$?` 立即捕获、不吞码；C13d 前值取安装根 clang（rm 前必存在）、后值取 relink 后构建树 `clang-23`，relink 改 build-id 即 FAIL，可达。
3. 干净基线全量重跑：`checks=38 fails=0`、`RUN1_RC=0`；重点项 C06/C07（输出真 `C07 OK`）/C08b/C09c/C12d/C13d/C14/C15/C16/C17a 全绿；C13a 299 s relink、C13b 1 条 link 行、C13c sha256 `a66f070b…` 不变。
4. 独立反例注入（`cp`+md5 备份 sidecar `3da7a5bd…`）：`archive-sha256=` 篡改为 `deadbeef…`（注入后 md5 `cd683773…`）⇒ 重跑**同一脚本** ⇒ C07 **FAIL**（输出 `sidecar=deadbeef… actual=1941b71d…` 真实独算 sha），连带 C08c/C10c（门控同判据）/C13i/C17a，`checks=38 fails=5`、`RUN2_RC=1` ⇒ 上轮恒真实锤修复、sha256 arm 可达 FAIL 实证。
5. 还原：`cp` 回 ⇒ sidecar md5 `3da7a5bd…` 逐字节同、stamp `da0a526b…` 未动；musl/builtins 门控亲跑 **rc=0/0** 回绿。
**约束核验**：未 commit/push（HEAD=e2a9bcd2）；未用 git checkout/restore/stash（一律 cp+md5 对账）；临时产物仅落 `/tmp/opencode/INFRA-101t-review/`；`.work/log/infra/` 无 `.EXIT` 残留（现存 `INFRA-101t-*.log` 命名合法，C16 两轮 rc=0）；快照对账：验前/验后 `git status --porcelain -uall` 均空、run.sh/stamp/sidecar md5 全回基线。
**判决 Accepted**（38/38 复核通过 + 注入反例 FAIL 可达实证；最终接受仍归 architect）。

**并行 reviewer 复核补充**（同轮独立会话，逐条对账上述声明，全部与盘上证据一致）：
1. `run1.log` 亲读：`checks=38 fails=0`、`PASS (38/38)`、`RUN1_RC=0`；关键项原文行核对 C06/C07/C08b/C09c/C12d/C13d/C14/C15/C16/C17a 全 PASS（C13d 行 = `de2e20d7…` 单 id，与修后脚本一致）。
2. C07 可达 FAIL 双重实证：本人以 `sed -n '122,147p'` 抽出同一 heredoc 跑 `/tmp` 内篡改 sidecar 副本 ⇒ rc=1；注入窗口内亲测真树 sidecar md5 `cd683773…`（`archive-sha256=deadbeef…`）、两道门控 builtins rc=1/musl rc=0；run2 的 C07 FAIL 同证不吞码。C13d 亲测构建树/安装根 clang build-id 均 `de2e20d7…`（不同二进制 `ld.lld=58559672…` ⇒ 不等分支可达）。
3. 并发观测：run2 由并行会话执行（09:22:43–09:35:5x），其 C13 `install-host` 将 sidecar 重刷为一致内容（C13i FAIL 即此），终态 md5 `3da7a5bd…` 与 run1 基线逐字节同；本人 09:36 亲测双门控 **rc=0/0**、`git status` 干净。
4. 本人自跑 L1：`make check JOBS=8` **rc=0**（38.2 s，尾行 `repository checks (L1): PASS`，日志 `/tmp/opencode/INFRA-101t-review/L1-self.log`）；`.work/log/**` 未新增 `.EXIT`（infra 现存 7 个均为 10-15/10-17 旧任务产物）。
**判决一致：Accepted。**

### 第 1 轮 reviewer 验收（2026-10-22，独立重跑；判决 = Needs Revision）

**重跑记录**（本人执行，rc 均取被检命令自身 `cmd >log; echo $?`；日志 `/tmp/opencode/INFRA-101t-review/`）
1. 判据：`bm.toolchain_stamp()` 现场打印 2 行 `build-id=`、`grep -c 'mtime=' =0`、`'size=' =0`；`readelf -n` vs `toolchain_id.elf_build_id` 对安装根+构建树 clang/lld **四比对逐字一致**（`de2e20d7…`/`58559672…`）。
2. 注入A：`touch .dadao/cross-toolchain/bin/clang` ⇒ 双门控 **rc=0/0**，stamp/sidecar md5 不变。**反向证明**：`cp`+md5 备份 toolchain_id.py（`cbceeee0…`）临时注入「identity 带 mtime+关 legacy 短路」并重写 stamp/sidecar ⇒ touch 前双绿、touch 安装 clang ⇒ musl **rc=1**（`actual=different`）、touch `clang-23` ⇒ builtins **rc=1**；还原 md5 全等 ⇒ 双绿（双向可达实证）。
3. 注入B：篡改 stamp/sidecar 记录的 `build-id=` ⇒ musl/builtins **rc=1/1**（`actual=different`/`expected=…0000…`）；`cp` 还原 ⇒ **rc=0/0**。
4. 注入C：旧 `mtime=` stamp ⇒ **rc=1** 且输出 `stamp format migrated … legacy mtime= stamp`；`make build-musl-shared JOBS=8` rc=0 ⇒ 转新格式（mtime=0/build-id=2）、rc=0、stamp md5 `da0a526b…` 与注入前逐字节同。
5. 真实工作流（本人重跑 run.sh C13）：touch `.td` + 删 `bin/clang-23` ⇒ `make install-host` **rc=0（512 s、2×`Linking CXX executable bin/clang-23`）**、sha256 `a66f070b…`与 build-id 不变、两门控 **rc=0**、stamp/sidecar md5 不变 ⇒ **无需** `build-musl-shared`。
6. 三 `--self-test` 亲跑 **rc=0**（8/8、10/10、12/12）；不放宽逐条 diff：musl 检查4/5/6/7 全留、builtins 三副本 sha256+成员清单保留（成员 mtime 排序→内容比对，**更强**）、self-test 注入 4→6 语义不减；`spec/`、`contracts/` 未动；commit 范围 = 声明的修改文件（C02 7 paths PASS）。
7. 门控：`make check` **rc=0**、`make check-modules` **rc=0**、`check-run-artifacts` **rc=0** —— 但交付盘面曾全红，见 R2。

**判决 Needs Revision**
- **R1 证据脚本 C07 恒真（无可达 FAIL）**：`run.sh:121` `python3 - "$SIDECAR" …` 无 heredoc、从空 stdin 读程序 ⇒ 恒 rc=0。实锤：把 sidecar `archive-sha256=` 篡改为 `deadbeef` 后该命令 **rc=0、输出 0 B**，同篡改下门控 rc=1；工程师现场 `c07.log` 亦 0 B。⇒ 改 `python3 -c`/补 heredoc + 给 C07 可达 FAIL 演示，重跑全脚本。
- **R2 交付盘面 L1/L2/check-run-artifacts 红（本任务残留）**：证据流程 07:50:47 落盘 ``INFRA-101t-evidence.EXIT`（曾误落于 `.work/log/infra/`）`，被 A3 判 illegal（非 `check-*.log`/`<TASK-ID>-<purpose>.(log|json|txt)`）⇒ 本人首跑 run.sh **EVIDENCE_RC=1**（C14/C15/C16 want rc=0 got **2/2/2**）；移走该文件 ⇒ `check-run-artifacts` rc=0（`1008 new, 0 illegal`）、L1 rc=0；`cp` 移回（md5 `38f506ac…`、mtime 保持）⇒ 复现 rc=2。完成区「38/38、三门控 rc=0」与工程师日志一致（未造假），但在交付盘面**不可复现**且未披露残留。⇒ rc 结论改落 `<TASK-ID>-<purpose>.txt` 或不落 `.EXIT`，完成区补披露。
- **并发披露（有据重试1次）**：另一 `opencode serve` 会话 08:24/08:29 在同树重跑 run.sh，其 C11 legacy 注入致本人 L2 首跑红（`stamp format migrated`、stamp mtime 08:29:00）；等其退出 600 s 后重试 L2 得 rc=0（未以重试掩盖根因）。该会话期间 `.EXIT` 从盘面消失（非本 reviewer 操作；本 reviewer 08:31 已按纪律移回并 md5 对账）。
**约束核验**：未 commit/push（HEAD=00f36442）；未用 git checkout/restore/stash（一律 cp/mv+md5 对账）；临时产物在 `/tmp/opencode/INFRA-101t-review/`；快照对账：`git status --porcelain -uall` 验前/验后均空、6 个修改文件 md5==HEAD、stamp/sidecar 回基线 `da0a526b…`/`3da7a5bd…`。
**遗留（只记录）**：① `build_picolibc.py:96-110` 仍 size+mtime+ctime 戳记（同类假 stale、范围外）⇒ 建议登记 issue；② `.EXIT` 落盘惯例与 A3 规则结构性冲突（历史 `.EXIT` 仅靠 `mtime≤epoch` 豁免）⇒ 建议登记 issue 供 architect 定夺。

### 第 1 轮 engineer 自审（2026-10-22，自主逐行审查）

审查面：`toolchain_id.py` 的 ELF note 解析（shdr/PT_NOTE 两路、ELF32/64、大小端）、两个门控的判据替换（只动"工具链是否变化"）、`Makefile` 的 sidecar 写入与既有断言保留、证据脚本的可达 FAIL。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 合成 ELF32 头（52 B、无 phdr/shdr）会因 `len(rest) < 48` 误判"不可解析" | ✅已修 | 按 ELF class 分别要求 36/48 B | `toolchain_id --self-test` rc=0（含 PT_NOTE-only 变体） |
| F2 `archive_entries` 短名保留 `ar` 的尾 `/`，显示成 `b.c.o/`（旧实现同问题） | ✅已修 | `raw.rstrip("/")` | `--self-test` inject-5 命中 `b.c.o`；实现树 147/147 成员 |
| F3 `build-builtins` 写 sidecar 需 `bin/ld.lld`，而原目标只依赖 `build-mc` | ✅已修 | 加显式 `test -f bin/ld.lld` + 提示先 `build-lld`；**不**加前置（避免与 `build-mc` 并行写同一构建树） | `make -n build-builtins` 含该检查；实跑 rc=0 |
| F4 任务书 C 的字面 "source digest" 未按字面实现 | ⏸延后（已落为 `archive-sha256`，对 compiler-rt 源码摘要属新增判据） | — | 完成区「坑②」 |
| F5 `build_picolibc.py:96` 仍是 size+mtime+ctime 戳记（同类假 stale） | ❌本册不修（任务边界只列 3 脚本 + `Makefile`） | — | 已登记「遗留问题」 |
| F6 若照抄"touch `.td` ⇒ relink"会得到恒绿注入（ninja restat 不 link） | ✅已修 | 证据脚本改为删 link 产物 `bin/clang-23` 强制 link，并断言 `Linking CXX executable` | `[10/11] Linking CXX executable bin/clang-23`，297 s，sha256 不变 |
| F7 门控在"归档可读但 0 成员"时 SKIP（不区分空归档） | ❌不修（改前同语义；空归档非可达状态） | — | — |

判决：F1–F3/F6 已修并复验；F4/F5/F7 有据不改/延后。证据脚本 38/38 PASS（rc=0），无未修 finding ⇒ 状态置 `待验收`。
