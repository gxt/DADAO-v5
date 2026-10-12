# QEMU-058t: NaN 2-NaN 传播规则（参照宿主机实测）

**模块**：qemu
**项目里程碑**：M7
**依赖**：无（同改 `components/qemu/patches` ⇒ 与其它 qemu 侧任务串行）
**状态**：已验证

> 立项来源：用户 2026-10-12 裁定「先在 M7 内做解锁件再归档」+ 本轮讨论（**从易到难第 5 项**）；依据 `ISS-195`（QEMU softfloat `float_2nan_prop_rule == none` ⇒ assert ⇒ blocked **5**）。

## 用户裁定（2026-10-12，**原话/选项标签**）

- 议题：DADAO 的 2-NaN 传播规则取哪条（`s_ab` / `ab` / `x87` / …）。
- 选项：A「`s_ab`（IEEE 754-2019 推荐）+ 实证」／B「`ab`」／C「先查 test 期望再定」。
- **用户选择 = 「参照当前宿主机的实现」**（= **实测宿主机行为，选与之匹配的 softfloat 规则**）。
- 取得渠道：**经主会话问答**取得（2026-10-12）。

## 目的 / 根因（事实）

- `components/qemu/patches/**` 的 `fp_status_init`（或等效）**从未设** `float_2nan_prop_rule` ⇒ 走默认 `float_2nan_prop_none` ⇒ QEMU 在 `parts64_pick_nan` **assert/abort**（architect 已 gdb 定位：`helper.c:550 ftdiv → float32_gen2 → parts64_div → parts64_pick_nan`）⇒ `ISS-195` **5 条** test blocked（如 `test-remquo-quo` rc=−6）。
- 上游规范（`SimRISC-07`/`contract-fp`）只规定「**NaN 传播 payload**」+「**sNaN 作算术输入 ⇒ 置 NV 且结果 qNaN**」+「符合 IEEE 754」⇒ **payload 选谁属实现定义**。
- IEEE 754-2019 §6.2.3 推荐：任一为 sNaN 则传播它，否则传播 quiet，同优先级按 a→b。

## 接口规范

- **输出**：
  1. **实测宿主机行为（必做、先做）**：在**宿主机**（本机 x86_64）用 `sNaN/qNaN × sNaN/qNaN` 组合构造用例（C 或 Python/`numpy` 皆可，须**记录** payload 位、quiet/signaling、符号），得出「**宿主机在 2-NaN 情形取谁的 payload**」的**实测结论**（留档）。
  2. **设置匹配的 softfloat 规则**（`components/qemu/patches/**`）：按实测结果选 `float_2nan_prop_{s_ab,s_ba,ab,ba,x87}` 之一（**给依据：实测结论 ↔ 规则名**）；若实测**无法**与任一规则一一对应 ⇒ **停下报告**。
  3. **重建 QEMU**（增量；申报耗时；`setsid`/`XXX_EXIT`/`JOBS=8`/`124` 判 FAIL 规则同上）+ **跑那 5 条 test**（真实退出码）。
  4. **全量 test**：`make check-picolibc-tests-full` ⇒ **四分类 before/after**（before：`pass 205 / fail 0 / excluded 22 / blocked 8`（立项期旧基线，已按现场订正））+ 解锁清单。
  5. `.tao/knowledge/milestones.md` 流水更新 `QEMU-058t` 行（状态 `待验收`，`完成时间` `—`）。
- **约束**：
  - **不得**改 DADAO 的上游语义主张（只补"实现定义"的那一格）；
  - ⚠️ **若"宿主机实测"与那 5 条 test 的期望冲突**（test 期望 ≠ 宿主行为）⇒ **停下报告**（需用户裁定"以谁为准"，`lessons §3.17`）；
  - **不改** `spec/`、`contracts/`、`tests/vectors/`；**计数不写死**。

## 验收标准

1. **宿主机实测留档**：用例 + 真实输出（payload/quiet 位），并给出**结论**（宿主机等价于哪条规则）。
2. **规则已设**：`git diff` 显示 `float_2nan_prop_rule` 被设为**与实测匹配**的值（给依据）。
3. **那 5 条 test**：before（blocked/abort）→ after（**真跑 rc=0**，真实输出）；**`fail` 仍须 0**。
4. **全量 test**：`pass` **上升**、`blocked` **下降**（before/after 现场统计 + 解锁清单）。
5. **门控**：`make check`、`check-patch-tree`、`check-no-residue`、`check-picolibc-tests`（快档）各 EXIT=0。
6. **反例可失败**：注入（回退该规则 ⇒ 复现 assert/abort）⇒ 断言/门控 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿。
7. **完成区**（≤30 行）与真实输出逐条对齐。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/QEMU-058t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；补丁导出纪律（写 `/tmp`、行数下限、**非空 blob**、`check-patch-tree` 断言⑥、`.work/source/qemu` 状态与 `series` 一致）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. 只动任务范围（`components/qemu/patches/**`、任务书、`milestones.md` 行）；越界须披露。
5. 失败保留现场并继续推进；**只在需用户语义裁定**时**停止并报告**（禁自拟自答）。
6. 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位）。
7. 一键证据脚本落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
8. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
9. **计数不写死**。

## 完成区

**测试结果**：① 宿主实测（x86_64，`gcc -O2 -fno-fast-math -mfpmath=sse`，`objdump` 证 `addss/subss/mulss/divss %xmm1,%xmm0`，dest=操作数 a）36 行 = 4 组合 × {+,-,*,/} × 交换序，**唯一**匹配 `float_2nan_prop_ab`（`map_rule.py`：`ab`=MATCH ALL；`s_ab`/`x87`/`s_ba`/`ba` 均 mismatch）⇒ **宿主 SSE = 返回第一操作数 a 的 NaN（sNaN 则 quiet）**。② 全量 picolibc（total 235）：**before pass 205 / fail 0 / excluded 22 / blocked 8 → after pass 213 / fail 0 / excluded 22 / blocked 0**；解锁 **8**（= 全部 before blocked），newly_blocked **∅**。③ `ISS-195` 家族**现场枚举** 8 条：`test-remquo-quo`/`test-ctan`/`test-ctanh`/`test-cpow`/`test-fma`/`test-math-errhandling`/`test-math-funcs`/`math_test`；before 全 `signal 6` → after 全 `pass`（rc=0）。
**修改文件**：`components/qemu/patches/target/dadao/helper.c.patch`（+13/−2：`fp_status_init` 增设 `set_float_2nan_prop_rule(float_2nan_prop_ab, st)`）；`.tao/knowledge/milestones.md`（`QEMU-058t` 行）。证据/日志：`.work/evidence/<任务ID>/`、`.work/log/qemu/`（不入库）。
**验收结果**：
1. 宿主实测留档：`host_probe_measured.out`（36 行 payload/quiet/sign）+ `host_probe_objdump.txt`（SSE 指令）+ `host_rule_mapping.out`（5 规则逐一回放）⇒ 唯一 `ab`。
2. 规则已设：`helper.c.patch` 含 1 处 `set_float_2nan_prop_rule(float_2nan_prop_ab, st)`；`check-patch-tree` rc=0（⑥⑨ patch==source）。
3. ISS-195 家族 8 条：before `signal 6` → after rc=0（above）；`fail` 仍 0。
4. 全量四分类 before/after + 解锁 8 + newly_blocked ∅（above；计数现场统计）。
5. 门控 rc：`make check`=0、`check-patch-tree`=0、`check-no-residue`=0、`check-picolibc-tests`(fast)=0。
6. 反例可失败：`run.sh --inject`（回退规则→`none`⇒重建）⇒ 正向断言 `test-remquo-quo passes` **FAIL（act=blocked/signal 6, rc=1）** ⇒ `cp`+md5 还原（`fd16d8ee…`）⇒ 重建 ⇒ 回绿；源树 clean。
7. 一键证据脚本 `.work/evidence/QEMU-058t/run.sh`：默认 22 检查 rc=0；`--inject` 30 检查 rc=0（含可达 FAIL 行）。
**新发现/坑**：(a) 宿主 SSE 的 2-NaN 规则 = `ab`（**非** IEEE-754-2019 §6.2.3 推荐的 `s_ab`）——`(qNaN_a, sNaN_b)` 宿主返回 a，`s_ab` 会返回 b（故实测排除 `s_ab`）；这是"参照宿主机"裁定的直接后果，可沉淀。(b) `float_2nan_prop_rule` 缺省 `none` 时 softfloat 仅**运行时** assert（编译期无告警），暴露面随可编源增多而扩大（本轮 blocked 8 全为本 issue）。
**遗留问题**：① 任务书 §接口规范 4 的 before（`pass 152 / blocked 65`）是立项期旧基线，**现场真基线 = pass 205 / fail 0 / excluded 22 / blocked 8**（architect 收尾同步，订正说明）。② `float_3nan_prop_rule`（muladd）未设；DADAO 无 FMA 指令（60 条 fp 无 muladd）⇒ 当前 0 暴露，**登记备查**，非本任务范围。

## 审阅记录

#### 第 1 轮 engineer 自审
- 审查点①：改 `fp_status_init`（`memset`+round+tininess+default_nan_pattern 之后）新增 `set_float_2nan_prop_rule(float_2nan_prop_ab, st)`。`grep` 证 `float_status` 唯一初始化点即此函数（cvt_ff/cvt_f2i/cvt_i2f/arith/root 全经它）⇒ 覆盖 add/sub/mul/div/rem/scalb/sqrt 全族，无遗漏。
- 审查点②：规则语义核对——`ab`：`ret = is_nan(a)?a:b`（softfloat-types.h L231-232 注释「Prefer A over B regardless of SNaN vs QNaN」；parts.c.inc L63-65），`pick_nan` 末尾对 sNaN 结果 `silence_nan` ⇒ 与实测「sNaN 被 quiet、保留胜者符号」一致；仅一方为 NaN 时 `a?…:b` 亦正确。
- 审查点③：`ab` vs `s_ab` 的判别用例（`(qNaN_a, sNaN_b)`）在 36 行内**双方换序各测**，`map_rule.py` 逐行回放 ⇒ `s_ab` mismatch 8 行（证明断言可区分，非恒真）。
- 审查点④：patch 纪律——`make_patch` 导出、非空 blob（`index 0000000..d214ac5`）、`check-patch-tree` ⑥⑨ rc=0；源树 `base+1` clean。
- 审查点⑤：反例还原——`--inject` 可见 `rc=1` FAIL 行 + `cp`+md5 还原（`fd16d8ee…`）+ 回绿；**未**用 `git checkout/restore/stash`。
- 审查点⑥：范围——`git diff --name-only` 仅 `helper.c.patch`（+`milestones.md` 行）；未触 `spec/`/`contracts/`/`tests/vectors/`/过滤表。
- 判决：改动最小、单点、可失败；`ab` 由实测唯一确定，无需用户裁定；**待验收**。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 需确认 `ab` 而非默认 `s_ab` | ✅已修（按实测选 `ab`） | `helper.c.patch` 设 `float_2nan_prop_ab` | `map_rule.out`：ab=MATCH ALL；s_ab mismatch 8 |
| 规则须覆盖全部 FP 运算 | ✅已修（单点 init） | 同上 | grep 唯一定义点 + 8 条 test 全绿 |
| 反例可达 FAIL 且能还原 | ✅已修 | `run.sh --inject` | 注入行 rc=1（blocked）→ 还原 md5 一致 → pass |

#### 第 1 轮 reviewer 验收

**重跑记录**（均为 reviewer 本机真跑，rc=被检命令自身退出码）：
1. 门控：`make check` rc=0、`check-patch-tree` rc=0（4 comp/127 patches）、`check-index-blobs` rc=0、`check-no-residue` rc=0、`check-picolibc-tests`(fast) rc=0（total=20 pass=18）、`check_issues.py` rc=0（23 open/9 closed，0 blocking）；恢复态复跑 `make check` rc=0、`check-patch-tree` rc=0。
2. 独立宿主实测（自写探针，NaN 位 `volatile+memcpy` 运行时构造；`objdump`：`addss/subss/mulss/divss %xmm1,%xmm0` 各 1 条、x87 0 条、操作数栈装载未折叠，dest=xmm0=第一操作数）：16 行=4 组合×{+,-,*,/}×换序，**每行结果=第一操作数 NaN（sNaN 则 quiet）**；关键行 `(qNaN_a=0x7FC0000A, sNaN_b=0x7F80000B)`→fwd **`0x7FC0000A`（回 a，非 sNaN b ⇒ 排除 `s_ab`）**、swap→`0x7FC0000B`；`(qNaN,qNaN)` fwd `0x7FC0000A`/swap `0x7FC0000B`；`(sNaN,sNaN)` fwd `0x7FC0000A`（quiet）⇒ **宿主=`float_2nan_prop_ab`**，与 engineer 36 行表三处关键行逐行一致；其 `.out` 重编译重跑 diff=IDENTICAL（输出真实，非改写）。
3. 规则语义源码核：`softfloat-types.h` L231-232「Prefer A over B regardless of SNaN vs QNaN」；`fpu/softfloat-parts.c.inc` L63-65 `ret = is_nan(a)?a:b` + L111-113 sNaN `silence_nan`；`none`→L107-108 `default: g_assert_not_reached()` ⇒ 「宿主 ⟺ `ab`」依据成立。
4. 设置点核：`git diff` 仅 `fp_status_init` 末 +11 行（注释+`set_float_2nan_prop_rule(float_2nan_prop_ab, st)`），hunk `@@ -0,0 +1,992 @@` 与 992 条 + 行一致、`index 0000000..d214ac5` == `git hash-object` 实测 `d214ac50a2ee…`（非空 blob）；源树 5 个 softfloat helper（cvt_ff/cvt_f2i/cvt_i2f/arith/root）全走该 init、`target/dadao/` 内无第二处 `float_status` ⇒ 全族覆盖、无残留 `none` 路径。
5. 解锁核（**自枚举**，勿采信名单）：注入 B 全量跑（我的 before）⇒ blocked(signal 6) 家族 **8** 条=`math_test,test-cpow,test-ctan,test-ctanh,test-fma,test-math-errhandling,test-math-funcs,test-remquo-quo`；抽 **5** 条（含 `test-remquo-quo`）还原后真跑全 `pass exit 0`；`newly_blocked=∅`、`fail=0`。
6. 全量（我自己的两份 JSON 现场统计）：before `205/0/22/8` → after `213/0/22/0`，差值 **+8/−8**，unlock 8=全部 before blocked，与完成区四数一致。
7. 补丁纪律：hunk 头/非空 blob/`base+1`（`9908fda` 上游+1、源树 clean）/series 一致；`check-patch-tree` ⑥（patched-index blob==源）⑨（HEAD diff==patch 集）rc=0。
8. 独立注入（`cp`+md5，无 `git checkout/restore/stash`）：A）`ab→s_ba`（md5 `fd16d8ee…→0f68de69…`）⇒ family 8 条**仍全 pass、未触发 FAIL**（如实记录：picolibc 不观察 2-NaN payload）⇒ **可达 FAIL 路径**用 B）**去调用**（`cp` 还原后删调用行，md5 `a1cb1b86…`、grep 计数 0）⇒ `test-remquo-quo` **blocked/signal 6**（正向断言「passes」可达 FAIL）+ 全量 blocked 8（即 §5 自枚举）⇒ `cp`+md5 还原（`fd16d8ee…`==快照前值）⇒ 重建 ⇒ 5 条（含 `test-remquo-quo`）全 pass **回绿**。
9. 证据脚本：逐条审 `<>/run.sh`（断言均有可达 FAIL 路径、覆盖计数现场统计非写死、`--inject` 用 `cp`+md5）+ 重跑 22 检查 rc=0 PASS。
10. 快照对账：前后 `git status --porcelain -uall` 逐行一致；`helper.c.patch`（dc215b04…）/源 `helper.c`（fd16d8ee…）/`milestones.md`（57095e64…）md5 与快照前一致（仅本任务书因本审阅记录变更）；改动面=完成区「修改文件」3 项，无越界。

**约束核验**（任务硬约束逐条）：①临时物仅 `<tmp>/QEMU-058t-review/` ✓；②未提交 git、补丁纪律 ✓；③完成区与真实输出逐条对齐 ✓（本记录逐项附真实输出/退出码）；④只动任务范围（未触 `spec/`/`contracts/`/`tests/vectors/`）✓；⑤失败保留现场继续推进、无待裁定项 ✓；⑥记录无字面 work 目录具体路径（均以 `<>` 占位）✓；⑦证据脚本可失败/计数不写死 ✓；⑧还原用 `cp`+md5 ✓；⑨计数现场统计 ✓。

**判决：Accepted**（验收标准 1–7 全部在我自己的重跑下成立）。非阻断建议：① `s_ba` 注入不触发 ⇒ 2-NaN payload 选择对现有 picolibc 测试**不可观测**，`ab` 与宿主一致性仅由宿主实测背书，建议后续补 1 条 payload 断言向量固化；② `map_rule.py` x87 分支对「单 NaN+num」情形漏 `silence`（探针数据不可达，仅备注）；③ 遗留 `float_3nan_prop_rule` 未设维持登记（本轮 `test-fma` 全绿佐证 0 暴露）。
