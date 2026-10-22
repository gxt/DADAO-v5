# TESTCASES-061t: harness 与向量工具修正（失败路径可信化 + 工具去陈）

**模块**：testcases
**项目里程碑**：M9（**必须早于终局全量复跑**）
**依赖**：`SPEC-164t`（编码迁移已完成，历史探针里的 `0x77` 全部失效，须一并清理）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源（用户 2026-10-22：「issue 只装缺陷，M9 内尽量关」）

本册收口以下 7 条缺陷（全部为"工具/用例本身错"，非新功能）：

| issue | 一句话 |
|---|---|
| `ISS-309` | `build_test_binary.py` 的 `br.nz` 偏移按 `PC+4` 算，而 ISA 分支基准 = `PC + imm*4` ⇒ 失败时落到 semihosting trap |
| `ISS-319` | 超时路径打印 `Unknown exit code: 0x-6`（负数 `%x`） |
| `ISS-323` | `run_rnd_probe.py` 的 `seen` 在 `for fmt` 内重置 ⇒ 805 含 20 条重复计数 |
| `ISS-120` | `min_rom_probe_{006t,008t,009t,010t,013t,028t}.py` 群 FAIL（pre-existing 漂移） |
| `ISS-234` | `min_rom_probe_009t.py` 顶注/公式仍按已废止口径（`0x5A`=UNDI、`PC & ~0xFFF`） |
| `ISS-125`+`ISS-190` | 生成器 ↔ 已提交向量漂移（全量重跑会破坏 5 文件；`st.*` 源 = `rd0`） |
| `ISS-326` | `tests/llvm/ir-lli/manifest.yaml` 11 个未分类 `*.ll` + 1 悬空项 |

## 目标

1. **`ISS-309`（最高优先）**：`br.nz` 偏移按 `PC + imm*4` 计算；所有用例的 PASS/FAIL 分支落点重新对齐；补 1 条"故意失败"用例，断言落到 FAIL 标签而不是 semihosting trap。
2. `ISS-319`：负数退出码格式化（`0x-6` → `-6 (SIG...)` 或 `0xFFFFFFFA`），并用 1 条超时用例验证。
3. `ISS-323`：`seen` 移出 `for fmt`；计数去重后现场统计（不写死 805）；完成区数字与之对齐。
4. `ISS-120`/`234`：6 个探针按现行口径重跑并对齐；公式/顶注过时的直接改。
5. `ISS-125`/`190`：以生成器为准重生成向量，确保 `make` 幂等（二次运行零 diff）；`st.*` 源寄存器口径统一。
6. `ISS-326`：11 个 `.ll` 补分类（pass/fail + 依据），删悬空项；补一条"manifest ↔ 文件集合双向一致"断言（可进门控）。
7. **编码残留清理**（`SPEC-164t` 遗留）：`tools/qemu/min_rom_probe_*.py` 与 `tests/scripts/**` 中 `0x77`/`0x77000000`/`0111-0111` 残留全部改 `0x47` 系（`OPC-MISC` 迁移后旧值已失效）；改完 `grep -rn '0x77' tools/ tests/` 仅允许出现在无关上下文（逐条判定并记录）。

## 验收

1. `ISS-309` 复现用例：改前落 semihosting trap、改后落 FAIL 标签（两条真实输出贴完成区）。
2. `run_rnd_probe.py` 输出计数 = 去重后唯一用例数（现场统计）；报告里不再有重复项。
3. 6 个探针直跑 PASS（逐个 rc=0）。
4. 生成器二次运行 `git status --porcelain` **无变化**（幂等）。
5. `ir-lli` 集合与 manifest **双向相等**（文件 ⊆ 条目、条目 ⊆ 文件）。
6. `make check`(L1) + `make check-modules`(L2) 绿；`validate-vectors` 绿。
7. **可达 FAIL ≥3**：① 回退 `br.nz` 修复 ⇒ 故意失败用例落到 trap（红）；② 重复一条用例 ⇒ 去重计数断言红；③ 给 manifest 加一条悬空 ⇒ 双向一致断言红。

## 接口规范

- **输入**：`tests/scripts/**`、`tests/vectors/**`、`tools/testcases/**`、`tools/qemu/min_rom_probe_*.py`、`tests/llvm/ir-lli/**`。
- **输出**：修正后的 harness/工具 + 重生成的向量 + manifest 补全。
- **约束**：不改 ISA 语义、不改 QEMU/LLVM 实现；不 commit/push；临时目录 `/tmp/opencode/TESTCASES-061t/`。

## 风险与纪律

- 修正 `br.nz` 会让**所有**失败路径行为改变 ⇒ 必须全量重跑受影响的用例集（不是抽样）。
- 重生成向量前先备份到 `.work/<任务ID>/before/`，逐文件 diff 审阅，禁 `git checkout` 还原。
- 若某条 issue 的根因实为 QEMU/LLVM 缺陷 ⇒ 停下报告，不在此册硬改。

## 完成区

**测试结果**：evidence rc=0（全项）；L1 rc=0、L2 rc=0、validate-vectors rc=0；全量受影响向量 **978 total / 967 passed / 0 failed / 11 deferred**；6 探针 rc=0（006t 28/28、008t 37/37、009t 12/12、010t 28/28、013t 22/22、028t 6/6）；rnd O0/O2 均 total=785（静态单元 20 个、去重后各判 1 次，现场统计；原 805 含 20 条重复）。
**修改文件**：
- harness：`tests/scripts/build_test_binary.py`（br.nz 偏移按 `fail_index-br_index` 派生）、`run_qemu_test.py`（负数退出码 → `SIGABRT`/二补码，超时单列）、新增 `tests/scripts/test_harness_exit_path.py`（故意失败 + `--inject` 旧偏移）。
- 生成器/工具：`tools/testcases/generate_isa_vectors.py`（`.u*` 窄比较零扩展，SPEC-069t；补回 div/rem 除零、INT_MIN/-1、cmp.uo-rb D8.2 边界共 43 条生成规则）、`tools/testcases/run_rnd_probe.py`（`seen` 移出 fmt 循环 + 重复注入）、重生成向量（reg-*/mem-*）、`tests/case-ledger.tsv`。
- 探针：`tools/qemu/min_rom_probe_{005t,006t,008t,009t,010t,011t,012t,013t,022t,028t,030t,032t,033t,034t,035t,036t,037t,038t,040t,042t,044t,045t,049t,061t}.py`（`0x77/0x7788` → `0x47/0x4788`；ILLI 毒饵改用 `cfxld 0x7C000000`；009t 改为现行 `aip.si` 口径并修 T12/偏移；010t 修 RAM 基址与分支偏移）。
- `tests/llvm/ir-lli/manifest.yaml`（11 条补 `no-value-entry` 分类、删 1 悬空）、`tests/llvm/lit/MC/DADAO/oiii.s`（注释 op 0x47）。
**覆盖变化**：向量总数 978（恢复后）← 935（首轮重生成）← 978（基准 `b939886c`）；首轮 `generate_isa_vectors.py` 因旧规则缺 div/rem 定值语义与 cmp.uo-rb 边界，静默丢失 **43 条**（reg-arith −40：16 条除零 encoding + 16 条除零 semantic + 8 条 `INT_MIN/-1` signed semantic；reg-compare −3：`cmp.uo-rb` 64 位 D8.2 边界 semantic）；本轮在生成器补 3 组规则 + 1 组边界规则后重生成，43 条全部恢复（与 `b939886c` 归一化语义逐条 0 缺 0 增），非手写补文件；依据 `SPEC-066t`（div/rem 除零与溢出定值）、`SPEC-081t D8.2`（cmp.uo-rb 全 64 位）。
**验收结果**：ISS-309 改前 rc=-6（SIGABRT，trap）/改后 rc=1（FAIL 标签），两条真实输出见 `.work/evidence/TESTCASES-061t/logs/iss309_{green,inject}.log`；manifest on-disk=78 = include19+exclude59、unclassified/missing=0；悬空注入 rc=1；重复用例注入使 4 行/单元形状断言红且判次不增；删除 1 条恢复用例 ⇒ case-ledger 覆盖哨兵 rc=1，`cp`+md5 还原后 rc=0；`grep -rn 0x77 tools/ tests/` **11 行**、全部无关（退出码 `0x77`×3、clmul/窄加载**数据值**×7、迁移说明×1），另有 1 行仅含 `0111-0111` 迁移说明；`0x77000000|0x77880000|0x77801000` 命中 0；`tests/scripts` 命中 0。
**新发现/坑**：① ISS-309 修后暴露出 3 条**真实**向量期望错（`cmp.ut/uw/ub` 的 −1 应零扩展为 `0xFFFFFFFF/0xFFFF/0xFF`，原生成器一律 64 位全 1）——按 SPEC-069t 修生成器，全量 967 例转绿；② 旧 harness 的失败路径会落 trap（同一失败用例旧版实测 rc=-6，新版 rc=1），故 L2 的 `reg-compare` 3 例此前属“脏红”；③ **生成器规则缺失会静默删用例**：首轮重生成少发 43 条（除零/溢出定值 + cmp.uo-rb 边界），仅看“二次幂等+全绿”无法发现，必须有覆盖哨兵（case-ledger）与恢复性注入；④ 030t/034t/035t/038t/040t 仍有与本册无关的既有失败，见遗留。
**遗留问题**：`030t`（C2/D2/D4b/环槽 5 例）、`034t`（cs.eq/fp 7 例）、`035t`（oracle 找不到 `spec/SimRISC-07` 的 `## 7. 浮点分类指令` 章节）、`038t`（ftcls 2 例）、`040t`（T6 `sub.o rb0` 源）为**既有漂移**，根因不在本册 0x77/harness 面，登记待专项；未改 QEMU/LLVM 实现。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1：br.nz 偏移修复后 L2 smoke 3 例转红（`cmp.ut/uw/ub` 期望 0xFFFF…） | ✅已修 | 生成器 `_cmp_result` 对无符号窄比较返回宽度掩码（SPEC-069t 零扩展），重生成 reg-compare | 全量语义 924/935 pass、0 failed；单例 rc=0 |
| F2：`run_single_test` verbose 把超时哨兵 `-1` 渲染成 SIGHUP | ✅已修 | verbose 分支先判 `timed_out` 打印 TIMEOUT | `test_harness_exit_path.py` 实跑 timeout 分支 |
| F3：evidence 用“distinct check names”验去重（名字天然重复） | ✅已修 | 改为 `static insensitivity` 判次 == 唯一单元数（20/20），并现场打印 total=785 | evidence 输出 `static_cells=20 distinct_static=20` |
| F4：evidence 的 `0x-6` 检查命中自身说明文字 | ✅已修 | 改为精确匹配 `Unknown exit code: 0x-6` | `count=0` |
| F5：`check_aggregates` docstring 仍称“uniqueness assertion” | ✅已修 | 改为“oracle 4 行/单元形状检查” | 文档与注入输出一致 |
| F6：`005t` 预存在 `shl_ut_orri` 未定义导致 NameError | ✅已修（披露） | 改名 `shl_t_orri`（同文件既有定义） | 005t rc=0（18/18、CTL OK） |
| F7：`013t` X4 landing 偏移 0x58 使 ret 落回链首（timeout） | ✅已修 | landing/期望改 0x60（(13+11)*4），注释同步 | 013t 22/22 rc=0 |

### 第 1 轮 reviewer 验收（2026-10-23，独立重跑）

**判决：Needs Revision** —— 7 条 issue 本身均已真修（证据见下），但重生成**静默删除 43 条已验证且当前全绿的向量**且未披露，判阻断待裁定。

**重跑记录（本人执行，退出码为准，`.work/evidence/TESTCASES-061t/run.sh` 全程重跑 EVIDENCE_EXIT=0）**：
- ISS-309 独立复现（自写翻转期望用例 add.uo_rrrr_rd + 临时树旧 builder）：`4a7a0742~1` ⇒ `rc=-6 SIGABRT guest did not reach SYS_EXIT`（trap）；`4a7a0742` ⇒ `rc=1 Test failed with code 0x01`（FAIL 标签）
- 注入①回退 `br.nz` 偏移（cp+md5）⇒ 自测 `FAIL: 4/5`，fail 用例 rc=-6 落 trap；还原后 5/5 rc=0、md5 相符
- ISS-323 现场统计：O0/O2 `total=785 pass=785 fail=0`，static 20 判次 = distinct 20；复制 1 条 static ⇒ `1 red, 20 distinct cells judged 20`（判次不增、形状断言红，可达 FAIL）
- ISS-319：spin 真超时 `rc=-1 timed_out=True → INCONCLUSIVE/Timeout`；信号渲染 `SIGABRT (rc=-6, 0xFFFFFFFA)`，`0x-6` 计数 0
- 6 探针直跑 rc=0（28/28、37/37、12/12、28/28、22/22、6/6）；旧树对照确有修正：006t/009t/010t/013t/028t 旧 rc=1，008t 旧 CTL 毒饵出 0x89（UNDI）现 0x88（ILLI）
- 生成器：md5.before==run1==run2（对入库向量零漂移 + 二次零 diff）；st./stm.* rd0 源误判 ILLI = 0 条（64 条 st/stm 逐条查）
- manifest：disk 78 = include19+exclude59，overlap/missing=0；新增 11 条逐条无 `@main`；注入②悬空项 rc=1（cp+md5 还原后 rc=0）
- `grep -rn 0x77 tools/ tests/` 11 行逐条判：退出码×3、clmul/窄加载数据值×7、迁移说明×1；`0x77000000|0x77880000|0x77801000`=0；完成区"12 行"另含 `0111-0111` 说明行（口径差 1，非实质）
- cmp.* 独立判据：SimRISC-08/09/10「高位规则：`.ut/.uw/.ub ⇒ 结果零扩展`」⇒ 期望 −1→`0xFFFF_FFFF/0xFFFF/0xFF` 改前后一致且符合 spec；`_cmp_result` 由恒 64 位全 1 改宽度掩码（signed 仍全 1），属收紧非放宽
- 门控：validate-vectors rc=0、L1 rc=0、L2 rc=0、semantics `935 total, 924 passed, 0 failed, 11 deferred`

**阻断（返工项）**：reg-arith −40（SPEC-066t div/rem 除零与 INT_MIN/-1 定值语义）、reg-compare −3（SPEC-081t cmp.uo-rb D8.2 64 位边界）共 43 条**已验证向量被删除**——我方把这 43 条在现 harness/QEMU 复跑 `43 total, 43 passed, 0 failed`，即纯覆盖损失而非修错值；完成区仅写"9 个重生成向量"未披露。要求二选一：① 扩展 `generate_isa_vectors.py` 补发这 43 条（保持幂等+零 diff）；② 经用户/架构师明文裁定删除并登记遗留，完成区补披露 224→184/36→33；随后重跑受影响面（口径将由 935 回到 978）。

**快照对账**：验收前后 `git status --porcelain -uall` 均 0 行、HEAD=4a7a0742 未变；被注入的 `build_test_binary.py`/`manifest.yaml` 及 6 个关键文件 md5 前后一致（`cp` 备份还原，未用 checkout/restore）。

### 第 2 轮 engineer 自审（返工）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1（阻断）：生成器规则缺失导致 43 条已验证向量被静默删除（reg-arith −40、reg-compare −3） | ✅已修 | `generate_isa_vectors.py` 新增 `gen_divrem_zero_encoding` / `gen_divrem_by_zero` / `gen_divrem_signed_overflow` 三组规则（SPEC-066t）+ `gen_cmp_uo_rb_boundaries`（SPEC-081t D8.2）；仅改生成器，未手写补文件 | 重生成后 reg-arith 224、reg-compare 36；与 `b939886c` 归一化语义逐条对比 **0 缺 0 增**；全量 978 total / 967 passed / 0 failed / 11 deferred |
| R2：完成区 `0x77` 行数写 12（实际 `grep -rn 0x77` = 11，另 1 行仅 `0111-0111`） | ✅已修 | 完成区改为 11 行并单列 `0111-0111` | `grep -rn 0x77 tools/ tests/ \| wc -l` = 11 |
| R3：完成区未披露覆盖变化 | ✅已修 | 新增「覆盖变化」节（978←935←978、43 条明细与依据、恢复途径） | 完成区可查；生成器二次运行 md5 一致 |
| R4：删除用例缺少可达 FAIL 证据 | ✅已修 | evidence 新增注入：删 1 条 `reg-arith` 除零 encoding ⇒ case-ledger rc=1；`cp` 备份还原、md5 对账后 rc=0 | `.work/evidence/TESTCASES-061t/logs/coverage-{inject,restored}.log` |

### 第 2 轮 reviewer 验收（2026-10-23，独立重跑，只复验上轮唯一阻断）

**判决：Accepted** —— 43 条确已恢复且为生成器驱动，门控全绿；阻断项全部消除。

**重跑记录（本人执行，退出码为准）**：
- 43 条恢复：`reg-arith` 184→224（+40）、`reg-compare` 33→36（+3）；与基线 `b939886c` **语义签名级 0 缺 0 增**（9 个重生成文件逐条比对 id/class/word/input/expected/fault/status 全等）。本人构造恢复集子目录、用与门控同一 `run_batch` 入口逐条实跑：**`43 total, 43 passed, 0 failed`**（rc=0），恢复集 = div/rem 除零 encoding 16 + 除零 semantic 16 + `INT_MIN/-1` signed 8 + `cmp.uo` D8.2 边界 3，与完成区明细逐组吻合
- 生成器驱动（非手写）：临时树 `rm reg-arith.yaml reg-compare.yaml` ⇒ 跑 `generate_isa_vectors.py` 重新生成，两文件 **md5 与删除前完全一致**（`2359931…`/`a2f8c72…`）；二次运行 md5 不变、`git status --porcelain` 0 行（幂等）
- 生成器新增 4 组规则（`gen_divrem_zero_encoding`/`gen_divrem_by_zero`/`gen_divrem_signed_overflow`/`gen_cmp_uo_rb_boundaries`）逐条对照 `SimRISC-04` 定值表（除零全 1/宽度掩码、rem=被除数、溢出截断符号扩展）相符；返工 diff 仅 5 文件（任务书/ledger/两向量文件/生成器），纯新增无删改
- 总数口径：`make check-qemu-semantics` **`978 total, 967 passed, 0 failed, 11 deferred, 0 errors`** rc=0（935→978 归位）；`spec/`、`contracts/` 改动 0 个文件
- 覆盖哨兵独立注入（本人做，非采信 run.sh）：删 1 条本轮恢复用例 `div.uo_orrr_rd encoding` ⇒ `check_case_ledger.py` **rc=1**「清单多出（未重新生成?）…0x40e01080」；`cp`+md5 还原（`2359931…` 相符）⇒ **rc=0**
- 抽核上轮 3 项仍 ✅：`ISS-309` 改前注入 `rc=-6`（SIGABRT 落 trap）/改后 `rc=1`（FAIL 标签）；去重 O0/O2 均 `total=785`、static 判次 20 = distinct 20（注入复制 1 条 ⇒ 形状断言红）；`cmp.*` 零扩展期望与基线全等、未回退
- 门控（本人重跑 run.sh 全量，`EVIDENCE_EXIT=0`、`RESULT: PASS (0 failing checks)`）：L1 **rc=0**、L2 **rc=0**、validate-vectors rc=0、6 探针 rc=0（28/37/12/28/22/6）
- 完成区「覆盖变化」与现场一致：978←935←978、43 条明细与依据、恢复途径均可复现
- **快照对账**：验收前后 `git status --porcelain -uall` 均 0 行、HEAD=`b7f45cb2` 未变；注入文件 md5 前后相等（`cp` 备份，未用 checkout/restore）
