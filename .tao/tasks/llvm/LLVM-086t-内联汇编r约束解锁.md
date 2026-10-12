# LLVM-086t: 内联汇编 `"r"` 约束解锁（`ISS-193`(e)）

**模块**：llvm
**项目里程碑**：M7
**依赖**：`LLVM-085t`（同改 `components/llvm-project/patches` ⇒ **串行**）
**状态**：已验证

> 立项来源：用户 2026-10-12 裁定「**先在 M7 内做解锁件再归档**」+ 本轮讨论（**从易到难第 1 项**）；依据 `ISS-193`(e)（blocked 2）。

## 用户裁定（2026-10-12，**原话/选项标签**）

- 议题：`"r"` 语义（GPRD vs GPRB）与是否**立"内联汇编约束约定"**。
- 选项：A「`"r"`→GPRD + 新增 `"b"`→GPRB + `"f"`→GPRF + 立最小约定（于 `spec/Toolchain-01` + lit 钉住）」／B「`"r"`→GPRB 优先」／C「**只解锁，不立约定**」。
- **用户选择 = C「只解锁，不立约定」** ⇒ **只把 `"r"` 映射到通用数据寄存器类（GPRD）**；**不新增 `"b"`/`"f"`**、**不立约束约定**（后置）。
- 取得渠道：**经主会话问答**取得（2026-10-12）。

## 目的 / 根因（实测）

- 根因：DADAO target **未实现** `getRegForInlineAsmConstraint` ⇒ 任何 `"r"` 约束报 **`could not allocate output register for constraint 'r'`**。
- 最小复现（实测 rc=141）：`long c(long*p){long v;__asm__ volatile("" : "=r"(v) : "r"(p)); return v;}`。
- 现场用例（`picolibc`）**均为空 asm 编译器屏障**：`__asm__ __volatile__("" ::"r"(dest) : "memory");`（`libc/string/memset_explicit.c:44`、`memset_s.c:68,75`）⇒ **asm 体内无指令**，寄存器类别不影响语义 ⇒ 映射到数据类即可解锁。
- 事实（`contract-abi`）：**指针类参数使用基址寄存器 `rb16–rb31`**；ISA 有 `rd2rb`/`rb2rd` ⇒ **GPRD 与 GPRB 不通用**（本任务**只解锁**，不做类型分派——分派在 LLVM 后端**不可行**：VT 只有 `i64`）。

## 接口规范

- **输出**：
  1. **实现 `DADAOTargetLowering::getRegForInlineAsmConstraint`**（范围 `components/llvm-project/patches/llvm/lib/Target/DADAO/**`）：`"r"` → **GPRD 类**（`GPRD` vs `GPRD_Allocatable` 由 engineer 按**寄存器分配器口径**选定并**给依据**）；**其余约束回落** `TargetLowering::getRegForInlineAsmConstraint`；**不得**顺手新增 `"b"`/`"f"`（用户裁定：**不立约定**）。
  2. **重建**（`build-mc`+`install-host`；申报耗时；>10 min ⇒ `setsid nohup` + `XXX_EXIT`；`JOBS=8`、禁全核、一次一个；`124` 判 FAIL）。
  3. **picolibc 全量 test 重跑**（`make check-picolibc-tests-full`）⇒ **四分类 before/after**（**before = 现场实测**：`pass 174 / fail 0 / excluded 22 / blocked 39`；~~`pass 152 / fail 0 / excluded 18 / blocked 65`~~ = `LLVM-085t` **之前**口径、已过期 ⇒ 本条按实测**更正**）+ **解锁用例清单**。
  4. `.tao/knowledge/milestones.md` 流水更新 `LLVM-086t` 行（状态 `待验收`，`完成时间` `—`）。
- **约束**：**最小改动**（只 `"r"`）；**不改** `spec/`、`contracts/`、`tests/vectors/`；计数不写死。
  - ⚠️ **若你发现"只映射 `"r"` 不够"**（如某源还需 `"f"`/`"b"`/其它）⇒ **停下报告**（`lessons §3.17`：禁自拟选项自答；**不擅自扩范围**）。

## 验收标准

1. **`"r"` 可用**：最小用例（整数 input/output、**指针 input**、`+ "memory"` clobber）**rc=0**；汇编产物真出现该寄存器（可给 `-S` 片段）。
2. **解锁**：`memset_s`/`memset_explicit` 两源 **`clang -c` rc=0**；对应 picolibc test **真跑 rc=0**（≥2 条）。
3. **全量 test**：`pass` **上升**、`blocked` **下降**（before/after 现场统计 + 解锁清单；**`fail` 仍须 0**）。
4. **门控**：`make check`、`check-lit`、`check-patch-tree`、`check-index-blobs`、`check-no-residue`、`check-picolibc-tests`（快档）各 EXIT=0。
5. **反例可失败**：注入（回退该 hook / 改错期望）⇒ 断言/门控 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿。
6. **未扩范围**：**未**新增 `"b"`/`"f"`、**未**改 `spec/`（`git diff` 证据）。
7. **完成区**（≤30 行）与真实输出逐条对齐。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/LLVM-086t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；补丁导出纪律（写 `/tmp`、行数下限、**非空 blob**、`check-patch-tree` 断言⑥、`.work/source/llvm-project` = `base+N`、`series` 一致）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. 只动任务范围（`components/llvm-project/patches/**`、`tests/llvm/**`、任务书、`milestones.md` 行）；越界须披露。
5. 失败保留现场并继续推进；**只在需用户语义裁定**时**停止并报告**（禁自拟自答）。
6. 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位）。
7. 一键证据脚本落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、**计数不写死**、捕获退出码）。
8. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
9. **计数不写死**。

## 完成区
**测试结果**：picolibc full（现场统计，`--json` 见 `.work/evidence/<任务ID>/picolibc-full-{before,after}.json`）：before `pass 174 / fail 0 / excluded 22 / blocked 39` → after `pass 176 / fail 0 / excluded 22 / blocked 37`（total 235）。**解锁清单 = `test-malloc`、`test-memset_s`**（both was blocked：`undefined symbol: memset_s`）。最小用例（整数 in/out、**指针 input**、`"memory"` clobber）`clang -c`/`llc` rc=0，`-S` 见 `rb2rd {rd4}, {rb16}`；`memset_s.c`/`memset_explicit.c` `clang -c` rc=0；lit 104/104（含新 `inline-asm-r.ll`）；`--only test-memset_s,test-memset` pass / fail=0。
**修改文件**：① `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.{cpp,h}.patch`（hook 实现，`series` 仍 71）；② `components/picolibc/patches/meson.build.patch`（**越界披露**：删过滤表 (e) 两条 `memset_explicit.c`/`memset_s.c` —— 不删则 test 仍 `undefined symbol: memset_s`，解锁不可达）；③ `tests/llvm/lit/CodeGen/DADAO/inline-asm-r.ll`（新增）；④ `.tao/knowledge/milestones.md` 本行；⑤ 任务书（before 口径**更正** 1 处）。**未改** `spec/`、`contracts/`、`tests/vectors/`、`issues.yaml`。
**验收结果**：门控 `make check` EXIT=0（L1）；`make check-modules`（L2）EXIT=0（479 s）；`check-lit` 104/104 EXIT=0；`check-patch-tree` „4 component(s), 123 patches OK" EXIT=0；`check-index-blobs` „88 new-file OK; 35 modification skipped" EXIT=0；`check-no-residue` EXIT=0；`check-picolibc-tests`（快档）EXIT=0。重建：`build-mc` 238 s、`install-host` 146 s（增量、**未脱离**本地等待；`BUILD_MC_EXIT=0`/`INSTALL_HOST_EXIT=0`）。证据 `.work/evidence/<任务ID>/run.sh --inject` **EXIT=0**：I1 污染 lit 期望 ⇒ lit rc=1 ⇒ `cp`+md5 还原（`b8536f55…`）⇒ 回绿；I2 未映射 `"f"` ⇒ llc rc=1 + 原错误；I3 变更前 `llc` 快照 ⇒ rc=1 + `…constraint 'r'`（hook 回退 oracle）。
**新发现/坑**：① 任务书 before 计数过期（`LLVM-085t` 前），实测 **174/0/22/39**（已更正该条）。② **解锁需消费侧同步**：picolibc `meson.build` 过滤表把两源排除出 `libc.a`，仅修后端时 test 仍链接期 blocked；删 2 条后 `libc.a` 1,686,214→**1,769,726 B**，`llvm-objdump -t` 命中 `memset_s`/`memset_explicit` 定义。③ `"r"`→**GPRD** 依据 = 构造函数 `addRegisterClass(MVT::i64, GPRDRegClass)`（保留集 rd0–rd3 由 `getReservedRegs` 处理，非 `GPRD_Allocatable`；实测 RA 给 rd4）。④ 解锁「预期 2」成立但**非** `test-memset_s`+`test-memset_explicit`（上游无后者）——实为 `test-memset_s`+`test-malloc`。
**遗留问题**：① 组件 `changelog.md` 未加条目（`079t`–`085t` 同样未加，本任务从众）——建议 architect 统一裁定是否补。② `ISS-193`(e) 的 `resolved_by` 回填与契约/ADR 是否留痕由 architect 定（本任务未动 `issues.yaml`/`contracts/`）。(b)(c)(d)(f) 四类仍开放。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查对象**：`DADAOISelLowering.{h,cpp}` hook、`components/picolibc/patches/meson.build.patch`、`tests/llvm/lit/CodeGen/DADAO/inline-asm-r.ll`、`.work/evidence/<任务ID>/run.sh`（逐行）。

**逐行审查结论**：① hook 签名与 `TargetLowering` 基类虚函数逐字一致（编译通过即证），放在 `public` 段、`override`；② `Constraint.size()==1 && Constraint[0]=='r'` 精确匹配单字母 `"r"`（`=`/`&`/`%` 前缀在 `InlineAsm` 解析期已剥入 Type/修饰位，不进 `Codes`），其余（含多字符 `"rm"`）**回落** generic ⇒ 不新增失败面；③ 映射类选 **`GPRD`**：依据 = ctor `addRegisterClass(MVT::i64, GPRDRegClass)`（RA 入口口径）+ 保留集 rd0–rd3 由 `getReservedRegs` 排除、`_Allocatable` 仅影响 `getMinimalPhysRegClass` 确定性（`DADAORegisterInfo.td`「双保险」注释）；实测 RA 分配 **rd4**（`rb2rd {rd4}, {rb16}`）；④ lit 断言钉**库**而非「能编过」：指针 `"r"` 必现 `rb2rd`、i64 `"r"` 禁现 `rb2rd`/`rd2rb`（GPRB 映射会产 `rd2rb`），`;APP` 正锚防「函数没编」假绿；⑤ 过滤表只删 (e) 两条、注释同步，未动其它 9 条；⑥ 证据脚本每条断言均可失败（见下 finding 1、I1–I3）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 1 证据脚本 "only 'r'" 正则 `[b-eg-z]` 把合法 `'r'` 计入 ⇒ 断言**假 FAIL**（首轮 rc=1） | ✅已修 | 改 `[ab-qst-z]`（除 `r` 外全小写）+ 增 `'r'` 正锚（`lessons §2.20`） | 复跑 `run.sh --inject` ⇒ `count=0`/`count=1` 双绿，整体 EXIT=0 |
| 2 证据脚本 `newly_blocked` 空集显示 `?`（不可判定外观） | ✅已修 | `${newly:-(none)}` | 复跑显示 `(none)`，rc=0 |
| 3 picolibc 源 `-c` 检查未给 sysroot include（build-tree clang 不自动找 `string.h`） | ✅已修 | 增 `-I "$SYSROOT/include"`（用 `paths.py target_sysroot_dir`） | 两源 rc=0 |
| 4 `n_int_out` awk 结束判据过宽（注释行可能提前结束区间） | ✅已修 | 改 `^[A-Za-z_.][A-Za-z0-9_.]*:` 标签判据 + `;APP` 正锚 | 现场算得 int in/out `cross=0`、`app=1` |
| 5 任务书 before 计数（`152/0/18/65`）为 `LLVM-085t` 前口径、不可复现 | ✅已修 | 任务书该条更正为实测 `174/0/22/39`（留删除线原值）+ 完成区披露 | 实测 JSON `counts` 与更正一致 |

**判决**：findings 全部 ✅已修，无 ⏸/❌；状态 → `待验收`。

#### 第 1 轮 reviewer 验收

**审查对象**：hook 实现（`.cpp.patch`/`.h.patch`）、picolibc 过滤表（`meson.build.patch`）、lit 回归（`inline-asm-r.ll`）、证据脚本。

**门控**（全部 EXIT=0）：`make check`（L1）、`check-lit`（104/104）、`check-patch-tree`（4 component, 123 patches）、`check-index-blobs`（88 new-file, 35 modification skipped）、`check-no-residue`、`check-picolibc-tests`（fast: 16/0/2/2）。

**`"r"` 实现核**：hook `Constraint.size()==1 && Constraint[0]=='r'` → `GPRDRegClass`，其余回落基类 — **只映射 `'r'`**（`grep` 非-`r` 分支计数=0，`'r'` 锚点=1）。最小用例 `clang -c`/`llc` rc=0；`-S` 见 `rb2rd {rd4},{rb16}`（指针跨 GPRB→GPRD）；整数 in/out 无 `rb2rd`/`rd2rb`（已在 GPRD）。

**约束形态矩阵**：`"r"`/`"=r"`/`"+r"`/`"=&r"` rc=0（均映射 GPRD）；`"i"` rc=0（泛型处理）；`"m"` rc=1（backend 不支持内存操作数 inline asm）；`"f"` rc=1（未映射，泛型无法分配）。与裁定 C「只解锁 `"r"`」一致。

**解锁核**：`memset_s.c`/`memset_explicit.c` `clang -c` rc=0；`test-memset_s`/`test-memset` 真跑 pass/rc=0。

**全量 test**（ reviewer 独立重跑）：before `174/0/22/39` → after `176/0/22/37`（total 235）。解锁=test-malloc,test-memset_s；newly_blocked=∅；fail=0。差值 +2 pass / −2 blocked ✓。

**越界核**：过滤表删除 (e) 两条（`memset_explicit.c`/`memset_s.c`）+ 注释同步，保留 9 条（(b)5+(c)1+(d)2+(f)1）。抽验 `sf_log10.c`(b)/`hash_page.c`(c) 仍 rc=1 ✓。无其它条目误删。

**补丁纪律 + 未扩范围**：`series` 71 行不变；`.work/source` 源树 clean（base+1）；3 补丁非空 blob；`git diff --name-only` 无 `spec/`/`contracts/`/`tests/vectors/`。

**独立注入**：改 lit CHECK-NOT → CHECK non-existent pattern ⇒ lit rc=1 ⇒ `cp`+md5 还原（`b8536f55…`）⇒ 回绿 rc=0。与 I1/I2/I3 不重复。

**判定**：**Accepted** — 全部门控通过、`"r"` 只映射 `'r'` 映射 GPRD、解锁 2 test 无回归、全量四数核对一致、越界最小必要、补丁纪律合规、反例可失败。无阻断项。非阻断建议：① `"m"` 约束 crash（ISel `SelectInlineAsmMemoryOperands`）为已知 backend 缺口，非本任务范围；② 组件 `changelog` 未加条目（从众）。

#### 交叉复核 + 提交（architect，2026-10-12）

- **交叉复核（独立重跑，现场 rc）**：`make check` rc=0（`repository checks (L1): PASS`）；`make check-lit` rc=0（104/104，含 `inline-asm-r.ll`）；`make check-patch-tree` rc=0（`4 component(s), 123 patches OK`）；`make check-index-blobs` rc=0（`88 new-file patch(es) OK; 35 modification patch(es) skipped`）；`make check-no-residue` rc=0（`PASS`）；`make check-picolibc-tests` rc=0（`stage=fast total=20 pass=16 fail=0 excluded=2 blocked=2`）；`python3 tools/infra/check_issues.py` rc=0（24 open / 8 closed）。任务书 `**状态**`=已验证。日志 `/tmp/opencode/<本次任务>/`；复核记录 `.work/log/<模块>/`。
- **台账登记**：① `ISS-193` 追加「(e) 类已收口（`LLVM-086t`）」段（**只追加**、正文未重写；**保持 `open`**、`resolved_by` 仍 `null` —— 六类未全清，依字段约束「open 时 null」，(e) 的 `resolved_by` 记于 notes）。核 (b)/(c)/(d)/(f) 仍开放且口径准确（过滤表现 **9** 条 = (b)5+(c)1+(d)2+(f)1；`full-after.json` 逐条 reason 分桶与上文一致）。② 新立 **`ISS-197`**（`scope: [llvm]`，open）：内联汇编 `"m"` 约束 ⇒ `report_fatal_error`（`Could not match memory address.  Inline asm failure!`）**硬崩溃**（`llc` rc=**134** core / `clang` rc=1 + crash dump）；**既有问题**（变更前 llc 快照跑**纯** `"m"` 用例同样 rc=134、同签名）；对照 `"f"` = **优雅失败**（`clang` `invalid input constraint 'f'` rc=1 / `llc` `unknown asm constraint 'f'` rc=1）；性质 = **健壮性缺陷**；picolibc 源 **0 处**使用 `"m"`（无 test 暴露 ⇒ 非阻塞）。`check_issues.py` rc=0。
- **milestones**：`LLVM-086t` 行 → `已验证` + `完成时间` `2026-10-12 13:00`（= 落地提交时间；提交时强制 `GIT_{AUTHOR,COMMITTER}_DATE`）。
- **提交（architect；档位=正常，reviewer 判 `Accepted`）**：显式 staging（逐路径，禁 `git add -A`/`.`）；`git diff --cached --name-status`：**A=1**（`tests/llvm/lit/CodeGen/DADAO/inline-asm-r.ll`）、**M=6**（`issues.yaml`、`milestones.md`、本任务书、`DADAOISelLowering.{cpp,h}.patch`、`meson.build.patch`）；与完成区「修改文件」对账：**无漏提 / 多提**；超出完成区清单者 = `issues.yaml`（本轮 architect 登记，已披露）；相对任务书「接口规范」原范围，`meson.build.patch` 属**已披露越界**（消费侧同步、解锁必需，完成区②披露）；**排除** gitignored `.work/`、`.dadao/`、`.cache/`。分支 `LLVM-086t` = `e70ffca`；落地 `master`（`merge --squash` 单提交）；**未 `push`**、分支已删。
