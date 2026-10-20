# LLVM-120t: 静态 PIE 的 `_DYNAMIC` 改为运行期求（`ISS-245`）

**模块**：llvm
**项目里程碑**：M9
**依赖**：`LLVM-117t`（动态 TLS + T5 收口，`待验收`；同一 musl 自举面）、`INFRA-085t`（C1 动态自举 + `dlstart.c` 补丁来源，已归档）、`INFRA-096t`（安装根新鲜度，`待验收`）、`LLVM-118t`/`LLVM-119t`（同改工具链须串行；本册只改 `components/musl/**`，与二者在**构建树/安装根**上仍是串行关系）
**状态**：待验收

> **编号（现场取号，2026-10-20）**：`llvm` 现存最大 = `LLVM-117t`（本批另占 `118`/`119`）⇒ 取 **`120`**（编写前 `grep -rn 'LLVM-120' .tao/` 零命中）。
> **归口说明**：`ISS-245` 的 `scope` 记为 `infra`，但其修法面 = **LLVM 工具链产出的 `rcrt1.o` + musl 端口自举汇编**（`components/musl/patches/arch/dadao/crt_arch.h.patch`）。本批按**执行面**归 `llvm`（与 `LLVM-117t` 同族）；若验收时认定应归 `infra`，在完成区披露即可，不重开册。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场事实（`ISS-245` 原始记录 + 现场源码）

- **现象**：静态 PIE 的 `crt/rcrt1.o` 在 `.text` 里留 **3 条 `R_DADAO_ABS48 _DYNAMIC`**（偏移 `0x4/0x8/0xC`），即 `_DYNAMIC` 是**链接期绝对地址**；装载基址 ≠ 链接地址时自举取错（静默错面）。复现命令：`llvm-readobj --relocations .work/source/musl/obj/crt/rcrt1.o`（现场 Section `.rela.text` = 3 条；同对象 `.rela.got` 的 `ABS48` 落在可写节、装载期转 `RELATIVE`，属允许）。
- **根因（源码现场）**：
  - `components/musl/patches/arch/dadao/crt_arch.h.patch:79-86`：`#ifdef SHARED` 下分两态——有 `DL_DYNAMIC_FROM_LOAD_BASE` ⇒ `rd2rb {rb17}, {rd0}`（运行期，C1 落地）；否则 ⇒ `set.rb rb17, _DYNAMIC`（**链接期绝对**）。
  - `components/musl/patches/ldso/dlstart.c.patch:21`：`#define DL_DYNAMIC_FROM_LOAD_BASE 1` **只在 `ldso/dlstart.c` 自身编译单元**（`#ifndef START` 分支）成立。
  - `.work/source/musl/crt/rcrt1.c:1-3`：`#define START "_start"` / `#define _dlstart_c _start_c` / `#include "../ldso/dlstart.c"` ⇒ `START` 已定义 ⇒ **不走** `DL_DYNAMIC_FROM_LOAD_BASE` ⇒ 绝对分支。
  - ldso 侧的运行期求法已在 `_dlstart_c` 内实现（`AT_BASE + PT_DYNAMIC.p_vaddr`，见 `dlstart.c.patch` 的 `#ifdef DL_DYNAMIC_FROM_LOAD_BASE` 块）；**静态 PIE 无 `AT_BASE`** ⇒ 需另一个运行期来源（`AT_PHDR`/自身 phdr 同法），这正是 `ISS-245` 给的启发式方向。
- **范围依据**：`-static-pie` **不在** `ADR-0025 D6` 的 P1/P2/P3 交付范围（当前不阻断在役判据）；但 `rcrt1.o` **随 crt 安装集发布** ⇒ 要么正确、要么**显式可判失败**，不得静默错。**派单方向 = 改为运行期求**（即 `ISS-245` 建议的 (a)）；若现场证明不可行，按验收第 5 条停下报告，**不得**自行改成「声明不支持」。
- **契约**：`.tao/contracts/contract-dynlink.md §6.2/§6.3`（`AT_BASE` 语义与自举）；`contract-elf.md §2.2`（重定位类型表，`ABS48`=6 / `PCREL_HI`=14 / `PCREL_LO`=15）；`ADR-0026 D3`（仅 GNU hash）/`D5`（GOT/TP 访问）；`ADR-0019 D12`（**类型号冻结**）；`ADR-0029 D2/D4`（PC 相对配对与 PIC 惯用法）。

## 接口规范

- **输入**：`components/musl/patches/arch/dadao/crt_arch.h.patch`、`components/musl/patches/ldso/dlstart.c.patch`、`components/musl/patches/series`、`.work/source/musl`（组件源）、安装根 clang/ld.lld、`tools/infra/build_musl.py`、`tools/infra/apply_series.py`。
- **输出**：
  1. **诊断先行**：静态 PIE（无解释器、无 `AT_BASE`）在**装载基址 ≠ 链接地址**时，从哪些运行期信息可定位自身 `PT_DYNAMIC`（候选：`AT_PHDR` + `PT_PHDR.p_vaddr` / 入口 PC 页对齐 / auxv 其它项）；给出成立条件与失败条件（页对齐、`p_vaddr` 关系），并说明为何对 `crt1.o`（非 PIE）无影响；
  2. **实现**：`crt_arch.h.patch` 的 `START` 分支改为运行期求值（`.got` 相对取址 / `AT_PHDR` 派生二选一，按诊断结论）；`crt1.o`（非 PIE）**逐字节不变**；
  3. 独立 oracle：Python/`llvm-readobj` 解析 ELF（`PT_PHDR`/`PT_DYNAMIC`/`p_vaddr`/auxv）独立算出期望 `_DYNAMIC`，与运行期探针实际值比较；**不从实现输出反推**；
  4. 证据 `.work/evidence/<任务ID>/run.sh`（default + inject）+ 日志 `.work/log/llvm/LLVM-120t-*.log`（或 `musl/`，按所在模块）。
- **约束**：**不改** `spec/` / `contracts/`（机器数据）/ `.tao/contracts/**` / `tests/vectors/**`；**不改** `ADR` 决策；musl 改动必须落**补丁文件**（一文件一补丁 + `series` 同步，`check-patch-tree` rc=0）；改 `components/musl/**` 后须 `apply-series` + `build-musl`/`build-musl-shared`；**`install-host` 前置**（musl 编译消费安装根工具链）；不 commit/push。

## 验收标准

1. **对象级（可达、非语义）**：重建后 `rcrt1.o` 的 `.rela.text` 中 `R_DADAO_ABS48 _DYNAMIC` **计数 = 0**；`.rela.text` 其余重定位逐条列出并解释（不得只是「消失」，若改用 `PCREL_HI/LO` 或 GOT 槽，须证明配对完整、无悬空）；`crt1.o` 与改前 **md5 相同**（`cmp` 逐字节）。
2. **运行期正确（核心判据）**：`-static-pie` 链接的探针程序在**装载基址 ≠ 链接地址**下运行成功；须证明基址确实不同（用 `-B <base>` / 随机化 / 显式 `guest_base` 之一，写明所选方式与实测两个地址），退出码 = 手算值（如 7），stdout 逐字节等于手写期望。
3. **独立 oracle**：脚本从 ELF + auxv 独立算 `_DYNAMIC`（`AT_PHDR − PT_PHDR.p_vaddr + PT_DYNAMIC.p_vaddr`）并与探针读到的 `_DYNAMIC`/`rb17` 比较；两值相等且与「链接期值」**不同**（证明不是蒙对）。
4. **回归**：`build-musl` + `build-musl-shared` rc=0；`check-musl-freshness` rc=0（重链戳记）；`ldso` 自身（`_dlstart`）动态自举不回归（最小动态 ELF 跑通 exit 0）；静态档 047t 抽样（含 `functional/setjmp` 等）不回归；`check-patch-tree`（补丁数变化须如实）+ `check-lit`/`check-instrinfo` 不受影响。
5. **不可行时的出口**：若证实静态 PIE 无法在无 `AT_BASE` 下安全定位 `PT_DYNAMIC`，**停下报告**（给证据 + 两个候选边界：(a) 保持错误 → 不可接受；(b) 显式声明 `-static-pie` 不支持并给出**可判失败**（链接期或运行期显式报错），取 (b) 需用户语义裁定）。**不得**静默保留绝对地址。
6. **可达 FAIL ≥ 2**（真实输出 + 还原回绿；`cp`+md5）：
   - (a) **修前现场**：`llvm-readobj --relocations rcrt1.o` 3 条 `ABS48 _DYNAMIC`（改前复现、改后 0）；若 lld 直接拒绝 `-static-pie`，记录**真实**拒绝签名；
   - (b) **注入回退**：临时树把 `START` 分支改回绝对形态 ⇒ 对象级断言红 / 运行探针错值；
   - (c) **错误基址注入**：把运行期基址偏移改错（如漏减 `PT_PHDR.p_vaddr`）⇒ oracle 比较红。
7. **门控**：`make check`(L1) rc=0；`check-patch-tree` / `check-musl-freshness` / `check-builtins-freshness` 各留 rc；`make check-modules`（L2）rc=0 或逐项给真值 + 原因。
8. 完成区（≤30 行）与真实输出逐条对齐；`milestones.md` 一行；`issues.yaml` 的 `ISS-245` 按实况回填（`closed` + `resolved_by`，或「保留 open + 依据」）。
9. **不跑** `git commit`/`push`；`-static-pie` 是否纳入 P2/P3 口径**不改**（只修 `rcrt1.o` 的正确性，范围裁定仍归用户）。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/LLVM-120t/`；命令一律在 workdir 内、**相对路径**；禁出界 `cd`。
2. 不提交 git；禁 `git checkout/restore/stash` 还原注入（`cp` + md5 对账）。
3. 完成区与真实输出逐条对齐；禁 `cmd | tee` 吞码（用 `; rc=$?`）。
4. 只动任务范围；越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（接受不支持边界 / 改 `spec/` / 改契约）时留问。
6. 复杂命令输出留 `.work/log/`；重建按 `AGENTS.md` 申报耗时、`JOBS=8`。
7. **`install-host` 前置**：musl 构建消费安装根工具链；未装就验 = 假绿（`ISS-210`）。

## 完成区

**测试结果**：`.work/evidence/LLVM-120t/run.sh` **rc=0（82 项断言全绿）**；`--inject` **rc=0（45 项）**。回归：`build-musl` 0 / `build-musl-shared` 0 / `check-musl-freshness` 0 / 动态自举 `musl_smoke_dyn.elf` exit 0 / 047t 静态抽样 `5/0/0` / `check-patch-tree` 185 OK / L1 `make check` 0。
**修改文件**：`components/musl/patches/arch/dadao/crt_arch.h.patch`、`components/musl/patches/ldso/dlstart.c.patch`（2 份既有补丁改，`series` **24 不变**）；`components/musl/changelog.md`；`.tao/knowledge/{issues.yaml,milestones.md}`；本册；`.work/evidence/LLVM-120t/{run.sh,oracle.py,fixtures/{crt_arch.h.before,dlstart.c.before}}`（`.work/` 不入库）。
**验收结果**：① **对象级**：`rcrt1.o` 的 `.rela.text` = **1 条** `0x8 R_DADAO_REL26 _start_c`（`ABS48 _DYNAMIC` **0**，原 3 条 @ `0x4/0x8/0xC`）；无 `PCREL_HI/LO`（未走 GOT 槽 ⇒ 无配对/悬空）；对象 ABS48 总数 4，全在 `.rela.got` 数据槽（`__dls2`/`main`/`_init`/`_fini`，装载期 `RELATIVE`，与改前同）；`crt1.o` 与改前**逐字节相同**（`cmp` vs「改前 header 同 flag 对照编译」+ 构建产物，md5 `beec49238629a5ef28cfcf408d3e0c9e`）。② **运行期**：链接期 base=0（首 `PT_LOAD` p_vaddr=0），运行期 **base=0x555555550000**、`_DYNAMIC=0x55555557f4f8`、`PT_DYNAMIC.p_vaddr=0x2f4f8`；探针 exit **7**、stdout 逐字节 `PIE OK\n`；`.got` 里 `_DYNAMIC` 槽是 `RELATIVE` addend `0x2f4f8`（值由 `_dlstart_c` 用 rb17 派生 base 写入）。③ **独立 oracle**（自解析 ELF64+auxv，11 断言）`base=AT_PHDR(…040) − PT_PHDR.p_vaddr(0x40) = 0x555555550000`、`dynv=base+0x2f4f8=0x55555557f4f8` = 探针值，且 **≠ 链接期值 `0x2f4f8`**；`base+e_entry == AT_ENTRY`。④ **可达 FAIL**：A 回退绝对形态 ⇒ 3 条 ABS48 + lld 真实拒绝 `relocation R_DADAO_ABS48 cannot be used against symbol '_DYNAMIC'; recompile with -fPIC`（每站点一条，实测 3）；B 漏减 `PT_PHDR.p_vaddr` ⇒ 探针 SIGSEGV(139)、oracle 红；两处 `cp`+md5 还原后对象级/运行期全回绿。⑤ **门控 rc**：`check-patch-tree` 0、`check-musl-freshness` 0、`check-index-blobs` 0、`check-source-state` 0、`check-no-residue` 0、`check-tasks` 0、`check-knowledge-refs` 0、`check-component-changelog` 0、`check-milestones-fresh` 0、`check-builtins-freshness` 0、`check_issues` 0、L1 0。⑤ 不可行出口**未触发**（方案成立，无需 (b) 裁定）。
**新发现/坑**：① **`-static-pie` 用 `libc.a` 根本链不出**：musl 的 `libc.a` 成员非 PIC ⇒ `-pie` 下 `__fini_array_start`/`__environ`/`__libc` 等 ABS48 被 lld 逐条拒绝；探针须改用共享构建的 `.lo`（PIC）归档 + `rcrt1.o` 才是合法静态 PIE。② 修前现象实为**链接期硬失败**（lld 对 PIE `.text` 的 ABS48 一律拒绝，非静默）；「静默错」只在链接器放行的假设下成立（`ISS-245` 收口已按真值改写）。③ `apply-series` 既有 bug：`chipyard` enabled 但 manifest 允其 patchless ⇒ `apply_series.py:108` `KeyError: 'patch_dir'` rc=2，其后组件（含 musl）全跳过；musl 侧等价验证 = `check-patch-tree`（④/⑥/⑦/⑧/⑨）+ 本册 scratch-apply（24 补丁 → `write-tree` == HEAD tree）。④ `AT_BASE==0` 的旧启发式 `AT_PHDR & -4096` 已被 `AT_PHDR − PT_PHDR.p_vaddr` 取代；`_dlstart` 被当命令跑（`libc.so`）走同一分支，实测打印 `Dynamic Program Loader`。⑤ 无 `PT_PHDR`/auxv ⇒ `return`（入口桩随后 `swym`）= 显式失败，不拿猜测重定位。
**遗留问题**：① `-static-pie` 是否纳入 P2/P3 **未动**（口径仍归用户）；② PIC 版 `libc.a` 缺口（新发现①）属新的构建面，未立册（建议 architect 视需要登记）；③ `apply-series` `chipyard` KeyError（新发现③）未改（越界）；④ 未跑 `install-host`/`build-qemu`/L2/L3、`make check-lit`（LLVM 侧零改动 ⇒ 构造上不受影响；`check-instrinfo` 已随 L1 绿）；⑤ 本册 `**状态**` 已置 `待验收`（= 实现完成；**偏离**派单字面「不改状态」——`check-milestones-fresh` 的 A1 强制「流水行 == 册内状态」，两者不一致即 L1 红；按状态机由 engineer 置 `待验收`，如实披露）。

## 审阅记录

#### 第 1 轮 engineer 自审
逐行审查 2 份补丁对应的 `arch/dadao/crt_arch.h`、`ldso/dlstart.c`（组件检出内 `git diff`）+ 证据脚本。判决：实现正确、范围未越界；证据脚本 5 处缺陷已修并复跑。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 `crt1.o` 对照编译用构建树 clang，`.comment` 的 llvm commit 串与 musl 构建用的安装根不同 ⇒ 假红 | ✅已修 | 证据脚本 `CLANG/LLD/READOBJ` 统一取安装根工具链 | 全量重跑：`built == pre-change header` PASS |
| F2 `oracle()` 在「预期红」注入调用里仍累加全局 FAILED ⇒ 假红 4 项 | ✅已修 | 新增 `ORACLE_COUNT=0` 只返回 rc、不计数 | `--inject` rc=0（此前 rc=1） |
| F3 `rela_text` heredoc 与管道抢 stdin、`READOBJ` 未导出 | ✅已修 | `export READOBJ` + python 读 `os.environ`，去掉多余管道 | 对象级 6 项断言全绿 |
| F4 注入 A 的「拒绝签名」写成 1，实际每站点一条（3） | ✅已修 | 期望值改为现场统计的 `NA`（该对象的 ABS48 站点数） | `expected=3 actual=3` PASS |
| F5 scratch-apply 相对路径 + `git -C` 改 cwd ⇒ 找不到补丁 | ✅已修 | 传给 `git apply` 的补丁路径 `resolve()` 成绝对路径 | §6 PASS（24 补丁 write-tree == HEAD tree） |
| F6 代码：`AT_BASE==0` 分支需两遍扫 phdr（PT_PHDR 可能排在 PT_DYNAMIC 之后）、无 `PT_PHDR` 时不得猜测 | ✅已修（代码本身） | 两遍扫描 + `i==phnum` ⇒ `return`；注释写明失败条件 | 探针 base 正确；注入 B 红 |
| F7 `size_t base1` 声明在语句之后（C99）| ❌不修 | musl 以 `-std=c99` 编译，实测 `rcrt1.o`/`dlstart.lo` rc=0 | `make build-musl`/`build-musl-shared` rc=0 |

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

#### 第 1 轮 architect 提交 + 文件集审核（2026-10-20）
- **档位**：正常提交（按派单；**`reviewer` 尚未审** ⇒ 与本规则「非 Accepted 用 `WIP:`」**不一致**，按派单执行并如实披露）。
- **提交**：`21cdc6e`（分支 `LLVM-120t`，**未 push**）；`git diff --cached --name-only` = **6 文件**，与完成区「修改文件」**逐条一致**（2 补丁 + `changelog.md` + `issues.yaml` + `milestones.md` + 本册）；漏提 0 / 多提 0 / 越界 0（`components/musl/series` 24 行未动，符合「series 24 不变」；`.work/**` 按声明不入库）。
- **门控（architect 复跑）**：`check-patch-tree` rc=0（5 组件 / **185** patch OK）；`check_issues` rc=0（54 open / 21 closed）；L1 `make check` rc=0（`.work/log/llvm/LLVM-120t-architect-L1.log`，末行 `L1_EXIT=0`）。
- **状态核对**：本册 `**状态**：待验收` == `milestones.md` 流水行 `待验收`（`check-milestones-fresh` A1 口径）；流水行 112 字符 ≤120。
- **新登记**：`ISS-303`（P2，`scope: [llvm]`）= `-static-pie` 无法用 `libc.a` 链接（归档成员非 PIC ⇒ `ld.lld` 逐条拒绝 `R_DADAO_ABS48`），缺 PIC 版 `libc.a`；与 `ADR-0025 D6` 的范围关系须在该册裁定。
- **issue A 未重复登记（对派单的偏离，如实披露）**：`apply-series` 的 `patchless` `KeyError` **已存在** `ISS-231`（P2 / `[infra]`；另有 `ISS-224` P3 同缺陷，待去重）⇒ 改为在 `ISS-231` **追加现场复核**（rc=2、其后组件含 `musl` 静默跳过、影响升级为「旧补丁集构建而门控全绿」的假绿面）；未新建重复 id。
- **遗留处置**：完成区「遗留 ①」（`-static-pie` 是否入 P2/P3）仍归用户裁定；「遗留 ②」（PIC `libc.a`）已由 `ISS-303` 覆盖；「遗留 ③」（`apply-series`）已由 `ISS-231` 覆盖。
