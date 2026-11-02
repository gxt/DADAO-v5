# TESTCASES-064t: picolibc `%p` 用例判定与处置（ISS-304）

**模块**：testcases
**项目里程碑**：M10
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地（picolibc full 档）

## 接口规范

### 背景（ISS-304，实测 2026-10-20）
- picolibc full 档：`test-printf` / `test-printf-int` 各 1 例 FAIL；失败断言仅 `test 277` / `test 278`（源 `.work/source/picolibc/test/test-stdio/test-printf-testcases.h:277-278`），两条均 `"%p"`，实参 `(void *)57ULL` / `(void *)57U`，期望 `"0x39"`；实测 `"0x8"`（3 字符）/ `"0x3"`，带宽度对照同形。
- 已排除 `hash_page.c` 过滤改动（A/B 同一 `.o` 输出逐字节相同）。

### 输出（**方案 A 已定**，用户 2026-10-25「选A」）

**根因（已核，高置信）**：
- picolibc `libc/stdio/vfprintf_int.c:62` 的 `%p` 设 `FL_LONG` 后走 `arg_to_unsigned` ⇒ `va_arg(ap, unsigned long)`；
- DADAO 调用约定把**指针参数放 RB 组**（`CCIfPtr` 在 `CCIfType<[i64]>` 之前），整数放 RD 组；`va_list` 七字段按 bank 分光标（`LowerVASTART`，`DADAO-21 §3.3`）；
- 调用侧 `(void*)57` 进 RB，picolibc 侧按 `unsigned long` 读 RD ⇒ **读错 bank**（实测 0x8/0x3），其余 276 条断言走 RD 整数路径故全过；
- 这是 C 的 UB：`%p` 参数类型是 `void*`，库却按整数取。

**实施**：
1. 给 picolibc 端口打补丁：`%p` 改为 `va_arg(ap, void *)`，再转 `uintptr_t` 打印（调用侧/取参侧同为指针类 RB）；
2. 重建 picolibc，跑 `make check-picolibc-tests-full`：两例转绿、其余不回归；
3. 反例：撤补丁 ⇒ 复现 `0x8`/`0x3` ⇒ 还原 ⇒ 绿；
4. 关闭 `ISS-304`（`resolved_by = TESTCASES-064t`）。

### 约束
- 不因两例失败放松 picolibc 全量判据；不改 `spec/`。
- 判定结论与证据写完成区（命令 + 输出 + 退出码）。

## 验收标准
1. 复现命令与真实输出（含 `test 277/278` 期望/实得）。
2. 判定证据链完整（源码行 + 对照/上游）。
3. 若修：picolibc full 档转绿（贴计数）；若判非缺陷：`issues.yaml` 关闭依据充分。
4. L1 / L2 绿。
5. 完成区贴真实输出。

## 完成区
**测试结果**：证据脚本 27/27 通过（`.work/evidence/TESTCASES-064t/run.sh` rc=0）。full 档 `total=235`：修前 `pass=201 fail=9 excluded=22 blocked=3` → 修后 `pass=209 fail=1 excluded=22 blocked=3`；逐例对照**转绿集合恰为 8 个 printf 变体**（`test-printf`/`-int`/`-float`/`-long` + 4 个 `*-scanf*`），**无 pass→非 pass 退化**。L1 `make check`、L2 `make check-modules` 均 rc=0（L2 内 `picolibc-tests fast total=20 pass=18 fail=0 blocked=0`）。
**修改文件**：`components/picolibc/patches/libc/stdio/vfprintf_int.c.patch`（新增，`series` 14→15）、`components/picolibc/series`、`components/picolibc/changelog.md`（`## M10` 节 + 条目）、组件工作树 `libc/stdio/vfprintf_int.c`（E1：base+1 + 干净）、`.tao/knowledge/milestones.md`（本册状态行 `待开始→待验收`，L1 `check-milestones-fresh` 要求；收尾时主会话已补记）。
**验收结果**：
```
$ make check-picolibc-tests-full JOBS=8        # 修后
picolibc-tests: stage=full total=235 pass=209 fail=1 excluded=22 blocked=3
  test-printf test-stdio pass / test-printf-int test-stdio pass   # 修前均 fail（277/278）
$ ... picolibc_tests.py --stage full --only test-printf,test-printf-int
picolibc-tests: stage=full total=2 pass=2 fail=0 blocked=0 / PASS
# 反例（撤补丁→重建→跑，两 ELF 同形）：277 expected "0x39"(4) got "0x8"(3) / 278 got "0x3"(3)
# 还原（git apply + md5 9ebd4cac35f89b30ce05cf66b7da173f 一致）→ 重建 → 两例 pass
L1 `make check` → PASS；L2 `make check-modules` → PASS；`check-patch-tree` → 201 patches OK
```
**新发现/坑**：
1. **实测基线 ≠ 任务书基线**：现行工具链（clang 23.1.3，stamp 变更触发全量重建）下修前 full 档 `fail=9 blocked=3`；多出的 7 例同根因（`%p`，`test-printf-testcases.h:277-278` 被 8 变体共享），另 1 fail + 3 blocked 为既有（见遗留）。
2. **`test-printf-scanf*` 由 printf 侧连带**：断言是 `sprintf("%p")`→`sscanf("%p")` 往返，写侧修好后 4 例一并转绿（`vfscanf.c` 未改）。
3. `%p` 的 `FL_LONG` 去掉后 `vfprintf_int.c` 内无 `FL_LONG` 引用；7 个变体对象（含 shrink/wide）真实重编、`-Werror` 无告警。
**遗留问题**：
1. `test-math-errhandling` fail（`gamma_snan`/`lgamma_snan`/`lgamma_r_snan`：`got sNaN expect qNaN`）—— 修前基线同样 fail，属 `ISS-195`（QEMU 软浮点 2-NaN）同类，**未处置**。
2. `test-ceil`/`test-long-double`/`test-math-funcs` blocked（`ISS-193 (f)` long double 库调用），修前同样 blocked。
3. 残留同族缺口（**未修，超范围**）：`vfprintf.c:452` `skip_to_arg` 对 `%p` 仍走 `arg_to_unsigned`（上游本未置 `FL_LONG` ⇒ 读 `int`）；`__IO_POS_ARGS` 对 int 变体关、对 float/double 强制开 ⇒ `printf("%1$p",…)` 类定位用法仍可能取错银行，建议另立任务或并入 `ISS-304` 后续。
4. `ISS-304` 置 `closed` / `resolved_by=TESTCASES-064t` **留主会话收尾**（本笔未改 `issues.yaml`，避免 `open` + 非空 `resolved_by` 违反 `check_issues`）。

## 审阅记录

#### 第 1 轮 engineer 自审

**改动审视（逐行）**：`%p` 分支去掉 `FL_LONG`（此后 `vfprintf_int.c` 内无 `FL_LONG` 引用，已 `grep` 证实），改 `ptr_arg=1` + `x = (ultoa_unsigned_t)(uintptr_t)va_arg(ap, void *)`；`if/else` 的 `else` 分支承接 `arg_to_unsigned` 宏（宏体本身是 `if…else…`，dangling-else 绑定正确，7 个变体对象真实重编 `-Werror` 通过）；`uintptr_t` 经 `sys/types.h→stdint.h` 传递引入，实测编译无告警。整数/浮点/`%p` 之外的路径**未动**（`git diff` 仅 3 处 hunk）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| ① 证据脚本 oracle 注入首版未带 `--inject-test`，注入未落到被过滤库存（默认 `basename`）⇒ 该断言恒绿 | ✅已修 | 加 `--inject-test test-printf` | 复跑：`test-printf fail injected expectation rc=7 actual=0`，脚本 rc=1→0 |
| ② `FL_LONG` 删除检查用 `grep -F 'flags \|= FL_LONG;'`，会命中补丁的**删除行** ⇒ 恒真 | ✅已修 | 改双断言：`^-…FL_LONG;` 必须命中、`^+…FL_LONG;` 必须不命中 | 脚本打印 `removal_rc=0 addition_rc=1` |
| ③ full 档只比 fail/blocked 集合，漏「pass→excluded」类退化 | ✅已修 | 加逐例 `join` 对照：退化集必空 + 转绿集合恰为 8 个 printf 变体 | `无 pass → 非 pass 的退化: ∅`、`转绿集合恰为 8 个 printf 变体` |
| ④ 首版 `changelog.md` edit 把 `LLVM-118t` 摘要误复制成 M10 条目下的重复段 | ✅已修 | 删除重复 `  - 摘要` 行 | `check_component_changelog.py` → 20/20 PASS（picolibc 12 条/4 节，M[7,8,9,10] 递增） |
| ⑤ 「撤补丁仍 FAIL」可能因构建未生效/旧 ELF 假绿 | ✅已修 | 反例段加「修复代码消失（`ptr_arg` absent）+ 重建 rc=0 + 逐 ELF QEMU 输出含 277=0x8/278=0x3（各 2 次）」三证据 | `.work/evidence/TESTCASES-064t/log/counter-qemu.log` |
| ⑥ `skip_to_arg`（`vfprintf.c:452`）定位参数路径对 `%p` 仍读 `int`，与本改动后取参侧不一致 | ⏸延后 | 未改（任务范围仅 `vfprintf_int.c`；上游该路径本已与读侧不一致） | 已记入遗留 3；picolibc 测试无定位 `%p` 用例（`grep '\$p' test/` 空） |
| ⑦ `uintptr_t` 可用性未单独探针验证 | ❌不修 | 以真实构建为证据 | `make build-picolibc` rc=0，7 个变体对象（含 wide/shrink）在 `-Werror` 下重编通过 |

**判决**：findings 全部 ✅已修 / ⏸延后（附因）/ ❌不修（附证据），无未处置项 ⇒ 状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**判决：Needs Revision**（2026-10-26，HEAD=bb8aae09，分支 TESTCASES-064t）。唯一阻断：`milestones.md` 流水行未随任务书翻状态 ⇒ 交付树 **L1/L2 均 rc=2**（验收标准 4 不达标）；修复面仅 1 行 + 复跑，其余全部达标。

**重跑记录**（reviewer 亲自执行，日志 `.work/log/testcases/TESTCASES-064t-reviewer-*.log`）：
- `picolibc_tests.py --only test-printf,test-printf-int` rc=0：2/2 pass ✅。
- `make check-picolibc-tests-full JOBS=8` rc=2：`total=235 pass=209 fail=1 excluded=22 blocked=3`，fail 仅 `test-math-errhandling`（ISS-195 同类）、blocked=3（ISS-193），与完成区逐数字一致 ✅。
- `bash .work/evidence/TESTCASES-064t/run.sh` rc=0：**27/27 PASS**，含内置反例（撤补丁→rc=1→277/278 各 2 次 0x8/0x3→还原 md5 一致→回绿）✅。
- **`make check`（L1）rc=2 ✗**：恰 1 项 `VIOLATION: L58 TESTCASES-064t: 表「待开始」≠ 任务书「待验收」`。**`make check-modules`（L2）rc=2 ✗**：同一 VIOLATION 经 `test-semihost` 内嵌 L1 传播（其前模块全绿：lit 152/152、QEMU smoke 90/90、test-elf PASS；全文恰 1 处 VIOLATION）；补跑 `make check-picolibc-tests` rc=0（`fast total=20 pass=18 fail=0 blocked=0`，与完成区一致）✅。`check-patch-tree`：`5 component(s), 201 patches OK` ✅。

**独立反例**（cp 备份 + `git apply -R`，禁 checkout/restore）：撤补丁（`ptr_arg` 消失、树 M 1 文件、src md5 `9ebd4cac→787daf36`）→ 重建 rc=0 → **reviewer 独立 pre-fix 全量** `pass=201 fail=9`（恰 = 8 printf 变体 + math-errhandling）→ 两 ELF 直跑 QEMU：`test 277 expected "0x39"(4) got "0x8"(3)`、`278 got "0x3"(3)`、rc=1 → cp 还原 md5=`9ebd4cac` 一致、组件树 clean、HEAD 仍 `b71e403` → 重建 → 2/2 回绿；逐例 join：退化 ∅、转绿恰 8 printf 变体。注：首次撤补丁因相对路径层级错（应 `../../../`）rc=128 未生效，md5 证实现场未变，修正后重试 1 次成功（有据重试）。

**独立核对**：补丁 3 hunk 仅动 `%p`（`ptr_arg` + `va_arg(ap, void*)`），`%u/%o/%x` 仍走原 `arg_to_unsigned`、dangling-else 绑定正确；`vfprintf_int.c` 内 `FL_LONG` 引用 0（grep rc=1）；series 15 行/15 补丁（14→15）；组件树 E1 clean+base+1（base 2ae376c == manifest pin）；WIP 提交 4 文件与完成区「修改文件」一致、无越界（未触 `spec/`、`docs/DDLN`）；ISS-304 仍 open / resolved_by=null（与遗留 4 一致）；审查前后快照对账：patch/series/src md5、HEAD、主树与组件树状态全一致（注入零残留）。

**返工要求（最小面）**：① `.tao/knowledge/milestones.md` L58 状态 `待开始`→`待验收`（`TESTCASES-065t` 先例：流水行同步属工程师完成区，其完成区即列该文件）；② 复跑 `make check` / `make check-modules` 期望 rc=0；③ 完成区「修改文件」补列该文件，「L1/L2 rc=0」声明改以交付态复跑输出为据（现声明基于 01:24/01:37 翻状态前运行）。勿动其余已达标内容。

#### 第 2 轮 reviewer 验收

**判决：Accepted**（2026-10-26，HEAD=bb8aae09，分支 TESTCASES-064t；第 1 轮唯一阻断已消除）。

**阻断消除核验**（reviewer 亲自重跑，非采信主会话日志；日志 `TESTCASES-064t-reviewer-12/13-*.log`）：
- `make check`（L1）**rc=0**，末行 `repository checks (L1): PASS`，全文 0 处 VIOLATION/FAIL；`check-patch-tree: 5 component(s), 201 patches OK`。
- `make check-modules`（L2）**rc=0**，末行 `module checks (L2): PASS`，0 处 VIOLATION；lit 152/152、QEMU smoke 90/90、`picolibc-tests fast total=20 pass=18 fail=0 blocked=0`（与完成区一致）。
- 与主会话 `.work/log/testcases/TESTCASES-064t-close-L1.log`、`.work/log/testcases/TESTCASES-064t-close-L2.log` 的末行/计数逐项一致，无转述失实。
- 修复面核对：`milestones.md` diff 恰 1 行（L58 状态 `待开始→待验收`，时间格保持登记时间）；完成区「修改文件」已补列该文件。

**其余证据不变（快照对账）**：patch `a320c19d` / series `663e637b` / 源树 `9ebd4cac`、组件树 HEAD `b71e403`（E1 clean+base+1）、主 HEAD `bb8aae09` 均与第 1 轮审查前后快照逐字节一致 ⇒ 第 1 轮已独立重跑的全量档、反例、run.sh 结论对当前交付物继续成立，未重跑（采信边界：交付物字节级未变）。

**采信未重跑**：第 1 轮已亲跑的 `check-picolibc-tests-full`（209/1/22/3）、独立反例（撤补丁 277=0x8/278=0x3 → 还原回绿）、`run.sh` 27/27——因产物 md5 未变而沿用；完成区「测试结果」段 L1/L2 rc=0 声明经本轮交付态复跑证实为真。

**快照对账**：本轮前后主树仅 `milestones.md`（主会话修复）+ 任务书（完成区补记 + 审阅记录）两处未提交增量，与声明一致，无越界、无注入残留。提交由 architect 执行。
