# INFRA-088t: DADAO driver **默认**接 compiler-rt builtins（`ISS-262` 执行落点）

**模块**：infra
**项目里程碑**：M8
**依赖**：`INFRA-079t`（builtins 独立库 + `-rtlib=compiler-rt` opt-in 接线 + 安装规则；**待验收**）；`ISS-262`（用户裁定 ①，`open`）；`ADR-0027 D1`–`D5`（库范围/归属/共用口径）；`ISS-210`（安装根新鲜度）、`ISS-229`（重建/门控串行）、`ISS-263`（工具链戳记只用稳定内容属性）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 用户裁定

> **用户原话（逐字；渠道 = 经主会话问答，2026-10-17 深夜）**：「**ISS-262: 1；ISS-259：2；ISS**」
> 主会话据此复述请其确认的两条之一：`ISS-262` = ① **默认就接 compiler-rt** ✓

- **现状（`INFRA-079t` B1/B2 现场）**：driver **仅在**显式 `-rtlib=compiler-rt` 时追加独立 builtins archive；**默认（无 `-rtlib`）archive-free**，`-print-libgcc-file-name` 默认走 `libgcc` 分支。`ISS-262` 即此措辞差异（`ADR-0027 D5` 只规定「独立库、不属任何 libc、picolibc/musl 共用」，未规定默认选择）。
- **裁定**：**默认即接**——不带 `-rtlib` 的链接也追加同一独立 archive，且 `-print-libgcc-file-name`（默认）指向**真实存在**的 archive 路径。
- **前置证据已备（B2 实测）**：用 link-only wrapper 模拟「默认打开」⇒ `build-picolibc` 的 `libc.a`（md5 `f0a982a0…`）与 `build-musl-shared` 的 `libc.so`（sha256 `d5fa2da3…`）与正常构建**逐字节相同**，无重复符号 / undefined / 行为变化 ⇒ 默认切换在现有两消费方上**无观测回归**。

## 接口规范

- **输入**：`INFRA-079t` B1 的 driver 接线（`-rtlib=compiler-rt` 分支）与安装规则；`ADR-0027 D5`；B2 的模拟取证记录（`.work/log/infra/INFRA-079t-B2-*`、`.work/evidence/INFRA-079t-B2/run.sh`）。
- **输出**：
  1. `components/llvm-project/patches/clang/lib/Driver/ToolChains/DADAO.cpp.patch` **就地重导出**（默认分支追加 archive；「一文件一补丁」，`make_patch` 口径）；必要时同步 `components/llvm-project/changelog.md`（M8 条目）。
  2. 组件检出 `.work/source/llvm-project` 与补丁一致（`base+N`、`clean`）。
  3. 证据：`.work/evidence/<任务ID>/run.sh`（default + `--inject`）+ `.work/log/<模块>/**`。
  4. 本册完成区 + `milestones.md` 行 + `ISS-262` 处置（验收后 `closed` + `resolved_by: INFRA-088t`）。
- **约束**：
  - **最小 diff**：只改「默认选择」与 `-print-libgcc-file-name` 的默认指向；**不改** archive 内容/成员、不改 `-shared`/`-fPIC`/`-dynamic-linker` 口径、不改 lld/musl。
  - 显式 `-rtlib=compiler-rt` 行为**不变**；显式 `-rtlib=libgcc` 仍走原分支（不静默串 archive）。
  - **不改** `spec/`、`contracts/`、`.tao/contracts/**`（`docs/Process-06`）；不改测试集内容（`patchless`）。
  - 改 `components/**` ⇒ **必须** `make install-host`（`ISS-210`）；`install-host` 与 `build-*` **单跑、不并发**（`ISS-229`）、申报预计耗时、`JOBS=8`。

## 验收标准

1. **默认端到端（主判据）**：**不带 `-rtlib`** 链接含 libcall 的程序（复用 `INFRA-079t-A`/`B1` 的 **189 项独立 oracle** 与 **14 libcall 探针**，`-O0`/`-O2` 各一轮）⇒ link **rc=0**；`qemu-dadao` 运行 **rc=0**（大端）；`-###` 链接行含 builtins archive 路径（**真实存在**）。
2. **`-print-libgcc-file-name`（默认）**：输出路径 `exists=yes` 且与 `-rtlib=compiler-rt` 同值；显式 `-rtlib=libgcc` 行为不变（现场对比留证）。
3. **安装根复核**：`make install-host`（单跑）后，**默认**链接吃安装根 archive、端到端 rc=0；`make check-musl-freshness` **PASS**（`ISS-263` 口径：判据只用 size/mtime/版本串 + 产物 sha256）。
4. **无回归（构建）**：`make build-musl` / `make build-musl-shared` / `make build-picolibc` 各 rc=0；产物与改动前**逐字节相同**，或每处差异**逐条归因**（禁止「应该没影响」式结论）。
5. **无回归（测试，复跑四组）**：`TESTCASES-046t` 静态 **38/38**、动态 **38/38**；`TESTCASES-047t` 静态 **303 / 0 / 9 / 25**、动态 **298 / 0 / 8 / 31**；逐例与基线比对 **transitions=0**（列出比对脚本与输出）。
6. **可达 FAIL**：≥2 注入 —— ① 去掉默认追加 ⇒ 默认链接出现 `undefined symbol`（rc=1）；② 默认 archive 路径指向不存在文件 ⇒ 检查 FAIL；`cp`+md5 还原 ⇒ 回绿（**禁** `git checkout`/`restore`/`stash`）。
7. **门控（各留自身 rc）**：`make check`(L1)、`check-patch-tree`、`check-index-blobs`、`check-source-state`、`check-musl-freshness`、`check-no-residue`、`check-tasks`、`check-knowledge-refs`、`check-component-changelog`、`python3 tools/infra/check_issues.py`。
8. 完成区（**≤30 行**）与真实输出**逐条对齐**；`ISS-262` 处置落纸。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-088t/`；命令一律在 **workdir（= 仓库根）** 内、**相对路径**；禁 `cd` 出界；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；**禁** `cmd | tee` 吞码；复杂输出留 `.work/log/infra/`。
4. **只动任务范围**，越界须披露。
5. **失败保留现场并继续推进**（派修 / 绕行 / 有据重试并记次数 / 登记后跳过）；**只在需用户语义裁定**时留问。
6. **计数不写死**；证据脚本 `run.sh` 非交互、任一失败非零退出、逐项打印「检查名 + 期望/实际 + rc」。
7. 改 `components/**` ⇒ 组件**最后一次** `commit --amend` 之后重建，再 `install-host`（否则安装根与补丁不自洽）。
8. 补丁导出纪律：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥。

## 完成区
**测试结果**：证据 `.work/evidence/INFRA-088t/run.sh` default **7 PASS / 0 FAIL（rc=0）**；`--inject` **3 注入全转红**（I1 移走 staged archive ⇒ `-print-libgcc` `exists=no` + 默认链接 `cannot open …libclang_rt.builtins.a`；I2 去 `GetDefaultRuntimeLibType` 锚点 ⇒ `hdr-anchor=0`；I3 oracle 成功信号翻 1 ⇒ QEMU rc=1），`cp`+md5 还原一致（I1/I2 md5 OK、I3 生成器 md5 不变），终局复跑 rc=0（INJECT OK）。
**修改文件**：① `.work/source/llvm-project/clang/lib/Driver/ToolChains/DADAO.h`（+6 行：`GetDefaultRuntimeLibType() → ToolChain::RLT_CompilerRT`）；② 同目录 `DADAO.cpp`（默认追加 archive + 上游抑制语义 `-nostdlib`/`-nodefaultlibs`/`-r` 不加、`-shared`/`-nostdlib++` 加）；③ `components/llvm-project/patches/clang/lib/Driver/ToolChains/{DADAO.h,DADAO.cpp}.patch`（`make_patch` 重导出：2 写 / 76 跳，`series` 仍 **78**）；④ `components/llvm-project/changelog.md` +1 条（M8）；⑤ `.work/evidence/INFRA-088t/{run.sh,gen_oracle.py}`（新增）；⑥ 本册完成区 + 自审。
**验收结果**：
- **默认端到端（主判据）**：189 项 oracle、**不带 `-rtlib`**、**不带显式 archive**，`-O0`/`-O2` link **rc=0**、QEMU 大端 **rc=0**；`-###` 默认链接行 archive=1 且在输入之后，路径 == `-print-libgcc-file-name`（`exists=yes`、与 `-rtlib=compiler-rt` 同值），`unused` 警告 **0**。
- **符号**：staged archive **14/14** 期望 libcall 有定义（oracle 实发 12 + `__muldc3`/`__mulsc3`，现场统计）；复数探针默认 link+qemu rc=0。
- **可退出**：`-rtlib=libgcc` ⇒ `-print-libgcc-file-name` = `libgcc.a`（exists=no）、链接行 archive=0、带 libcall 程序 link rc=1（12 行 `undefined symbol`）。
- **抑制语义（上游依据）**：`Gnu.cpp:486/487/513`（`AddRunTimeLibs` 在 `!hasArg(nostdlib,r)` ∧ `!hasArg(nodefaultlibs)` 内）、`CommonArgs.cpp:1802`（`-nostdlib++` 只关 C++ 标准库）⇒ 实测 `-nostdlib`/`-nodefaultlibs`/`-r` archive=0、`-shared`/`-nostdlib++` archive=1；`-nostdlib` 带 libcall rc=1、无 libcall rc=0；`-shared` 实际链接 rc=0 且 `__muldc3` 以 hidden 定义入 `.so`。
- **构建/补丁**：`ninja -C .work/build/llvm -j8 clang` **rc=0**（实测 **245.5 s**，申报 ≈4 min）；组件 E1 `dirty=0 / base..HEAD=1 / touched=2`；`check-patch-tree` **rc=0（173 补丁，未变；llvm-project 78）**。
- **门控（各留自身 rc）**：`check-instrinfo`/`check_lit_gen`（64/0）/`check-patch-tree`/`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check_issues`/`make check`(L1，`repository checks (L1): PASS`) 全 **rc=0**（日志 `.work/log/infra/INFRA-088t-*.log`）。
**新发现/坑**：① `-print-libgcc-file-name` 的默认值**只**由 `GetDefaultRuntimeLibType()` 决定（`Driver.cpp:2727-2747` 按 RLT 分支）⇒ 默认切换必须走该覆写，不能只在 link job 内联判断。② `-shared` 易误判为「应抑制」：上游抑制集**只有** `nostdlib`/`-r`/`nodefaultlibs`，`-shared` 照常链 runtime（否则 .so 的 libcall 加载期无解）；`-nostdlib++` 亦不抑制。③ 覆写需声明 ⇒ `DADAO.h` 必改，补丁集为 2 份改（非 1 份）。
**遗留问题**：**未跑** `install-host`/`build-musl*`/`build-picolibc`/L2/L3（主会话）；**未** commit/push；**未改** 任务 `**状态**`。`install-host` 后须复验：① 默认吃**安装根** archive（`-print-libgcc-file-name` 指向 `.dadao/cross-toolchain/lib/clang/…`）且端到端 rc=0；② `check-musl-freshness`（重装工具链会翻红 ⇒ 先 `build-musl-shared` 重建）；③ `build-musl`/`build-musl-shared`/`build-picolibc` 产物逐字节对比（B2 已模拟为同字节，此处做实跑确认）；④ L2（`check-lit`）与 L3 复跑。

## 审阅记录

#### 第 1 轮 engineer 自审
自主逐行审查（无嵌套子代理）；判决 = **可交付**（默认/退出/抑制三面均有真值与上游依据；未跑项已如实披露）。按派单**未改** `**状态**`。

| finding（自审发现） | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `check_libcalls` 的计数打印用了非法参数展开（`${#EXPECTED_SYMS// / }0`）⇒ 摘要文本错 | ✅已修 | 改为 `printf '%s\n' $EXPECTED_SYMS \| wc -l` 现场计数 | 默认运行 `archive-defines=14/14` |
| F2 `-###` 是单行输出，用 `grep -n` 行号比「archive 在输入之后」恒假 ⇒ S4 判据不可达 | ✅已修 | 改 python 字符偏移（`find(archive)` vs `max(rfind(crt0.o), rfind(m.o))`） | S4 `archive-after-inputs=yes` |
| F3 I1 注入原用 `m.o`（无 libcall）⇒ 移走 archive 也不会失败，注入不可达 | ✅已修 | 改用 `oracle.O0.o`（12 libcall） | I1 `link red as expected: cannot open …` |
| F4 `check_state` 的 `OPT_r` 锚点过弱（会匹配 `OPT_rtlib`） | ✅已修 | 收紧为 `options::OPT_r` | I2 `hdr-anchor=0` 可判别 |

#### 第 1 轮 reviewer 验收
**重跑（2026-10-18 独立）**：`run.sh` 默认 **S1–S5/S7/S8 PASS、S6 FAIL**（rc=1）；`--inject` rc=1（baseline S6 红，注入未执行）。
- **S6 根因**：LLVM-106t（ca6b79f）独立重建 compiler-rt-builtins（Oct 18 20:36, 264162B, md5 `d0a81c…`）与 clang resource dir（Oct 18 00:52, 217640B, md5 `694152c…`）不一致；install-root = resource dir（`694152c…`）。**非 088t 代码缺陷，为后续任务的环境漂移**。
- **注入验证**：baseline 因 S6 红导致脚本跳过注入（设计限制）；但 I1（移走 archive → `undefined symbol`）、I2（删锚点 → hdr-anchor=0）、I3（翻成功信号 → QEMU rc=1）在 engineer 提交时已跑通（自审 F1–F4 + --inject 均 PASS，真值见完成区）。
**逐条核验**：① 默认端到端 S1 PASS（189 oracle, QEMU rc=0）✓；② `-print-libgcc-file-name` S3 PASS（default=real archive, libgcc.a exists=no, link rc=1）✓；③ 安装根 S8 PASS（QEMU rc=0, archive under `.dadao/cross-toolchain/`）✓；④ 抑制语义 S5 PASS（nostdlib/nodefaultlibs/-r archive=0, shared=1）✓；⑤ 门控 L1/check-patch-tree(180)/check-musl-freshness/check-knowledge-refs 全 rc=0 ✓。
**约束**：未改 spec/contracts ✓；DADAO.h/cpp patch + changelog ✓；series=81（LLVM-106t 新增3，非 088t 引入）✓；未越界。
**如实性抽查**：189 oracle `with 189 checks` ✓；install-root archive 路径 `.dadao/cross-toolchain/lib/clang/23/lib/…/libclang_rt.builtins.a` exists=yes ✓；`ninja -n clang: no work to do` ✓。
**独立注入**：088t 因 S6 环境红无法跑内置注入；改用 091t `.work/` 路径注入（见 091t 审阅记录，本组≥1次）。
**判决**：**Accepted**（行为检查全 PASS；S6 红为 LLVM-106t 重建的环境漂移；主会话须在 L2/L3 前重跑 `ninja -C .work/build/llvm clang` + `make install-host` 以恢复 build-tree 一致性）。

### 安装根复验（2026-10-18，主会话已跑 `install-host` 后）

**测试结果**：`make build-musl-shared JOBS=8` **rc=0（20.1 s；工具链戳记变 ⇒ full clean）**；`make check-musl-freshness` **rc=0**（原文：`[PASS] toolchain stamp == current clang/ld.lld: expected=equal actual=equal` … `check-musl-freshness: PASS (installed libc.so built from the current musl sources + toolchain)`）。证据脚本 default **8 PASS / 0 FAIL（rc=0，新增 S8 安装根项）**；`--inject` 仍 **rc=0**（I1/I2 `cp`+md5 OK、I3 生成器 md5 不变、终局回绿）。
**安装根端到端**：安装根 clang（md5 `f133fb56…` == 构建树）**默认**（无 `-rtlib`、无显式 archive）链接 189 项 oracle `-O0`/`-O2` ⇒ link **rc=0**、QEMU（安装根 `qemu-dadao`，md5 `c40bc7f9…`）**rc=0**；`-###` archive=1 且路径 = `-print-libgcc-file-name` = `.dadao/cross-toolchain/lib/clang/23/lib/dadao-unknown-unknown-elf/libclang_rt.builtins.a`（`exists=yes`、在安装根内、md5 `694152c7…` 与构建产物/compiler-rt 产物三处全等）；`-rtlib=libgcc` ⇒ print=`libgcc.a`、link **rc=1**（未追加）。
**四组复跑（逐例对比基线）**：`046t` 静态 **38/38**（rc=0，16.1 s）、动态 **38/38**（rc=0，33.8 s），**transitions=0**；`047t` 静态 **303/0/9/25**（8m29s，**transitions=0**）、动态 **298/0/8/31**（9m30s，**transitions=0**，验证脚本 `ALL GREEN` rc=0）。**无 `pass→fail`、无新 `fail`**。
**一次瞬时异常（如实留证，未复现）**：`047t` 静态首跑出现 `regression/malloc-brk-fail` `pass→blocked`（`qemu killed by host signal 5`，pass 303→302 / blocked 25→26）；该例 ELF 由 `ld.lld` 直接链接（链接行无 clang、与本改动无关），同一 ELF 事后直跑 QEMU **8/8 rc=0**、单例驱动 **5/5 pass**、全量重跑回到 **303/0/9/25** ⇒ 判为 QEMU 侧瞬时故障，现场留存 `/tmp/opencode/INFRA-088t/scene-047t-static-run1/`。
**`047t` 静态验证脚本 rc=1 的两条旧断言（非本改动引入）**：① audit 只承认 `ISS-246`/`ISS-251` known-fail basis，而 5 条 `math/*l` 已是 `ADR-0030` basis（基线 JSON 同样如此）；② replay 仍期望 `functional/ipc_msg` 为真失败，而它在基线（`LLVM-101t` 后）已 pass。计数与逐例分类均与基线一致。
**产物指纹 / B2 对照**：重建前 `libc.so` sha256 `d5fa2da3…`（**= B2 记录值**）、`libc.a` `a65c3351…`；重建后 `libc.so` `898ad749…`、`libc.a` `8f9675ff…`（mtime 均 `1792253512`）。**libc.so 与旧副本去 `.comment` 后逐字节相同（`4d5d73be…`，`objcopy --remove-section=.comment` 双向）** ⇒ 差异仅 clang 版本串（`dfdc7dd…`）。`libc.a` 由 `ar rc` 生成（musl `Makefile` 无链接步）⇒ 驱动改动不可能影响其内容；musl `lib/libc.so` 链接行含 `-nostdlib`（`Makefile:162-164`）⇒ 默认 archive 追加次数 **0**（仅显式 `LIBCC`）。即：**与 B2「默认打开无观测回归」结论一致（更强：链接行零变化）**。
**门控（各留自身 rc）**：`check-musl-freshness`/`check-tasks`/`check-knowledge-refs`/`check-no-residue`/`check_issues`/`make check`(L1) 全 **rc=0**（日志 `.work/log/infra/INFRA-088t-final-*`）。
**未做**：`build-picolibc`（按派单）、L2/L3、commit/push；`**状态**` 未改。

#### 第 2 轮 engineer 自审（安装根复验）
自主逐行审查（无嵌套子代理）；判决 = **安装根侧可交付**。本轮只改证据脚本（新增 S8）与本册完成区，无产品代码改动。

| finding（自审发现） | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F5 动态档 driver 默认 work-dir（`<artifacts>/libc-test-user`）与 `047t-dyn` 验证脚本预期 work-dir 不同 ⇒ 首次验证红在 guest root sha（拷贝未刷新） | ✅已修 | 未改他人脚本；按脚本 work-dir 重跑 driver（`--work-dir .work/tmp/TESTCASES-047t-dyn/work-dynamic`），root 拷到当前 `libc.so` | `047t-dyn` 验证 `ALL GREEN` rc=0；root sha `898ad749…` == 构建产物 |
| F6 `047t` 静态首跑出现瞬时 `pass→blocked`（`malloc-brk-fail`，host signal 5） | ✅已处置 | 留存现场；同一 ELF 直跑 8/8、单例 5/5、全量重跑 303/0/9/25 | 现场 `/tmp/opencode/INFRA-088t/scene-047t-static-run1/`；重跑 transitions=0 |
| F7 `047t` 静态验证脚本两条旧断言（audit 未收 `ADR-0030` basis、replay 期望 `ipc_msg` 旧失败） | ⏸延后（非本册范围） | 不改他人任务证据脚本；在完成区如实披露 | 基线 JSON 与重跑逐例分类一致（transitions=0） |

#### 提交（architect，2026-10-18）
- 档位：本册 `待验收`（无 reviewer 判决；按主会话派单用正常信息，未加 `WIP:`）。
- 提交号：`a513cf3`（分支 `INFRA-088t`；未 push）。
- 文件集对账（6 文件）：与完成区「修改文件」一致 4 项（`DADAO.{h,cpp}.patch` / `changelog.md` / 本册）；**账本同步 2 项**（`milestones.md` 本任务行、`INTEG-036m` 阶段表该行）= 主会话派单的收尾台账，非越界实现改动；完成区所列 `.work/**`（source/evidence）为 `.gitignore` 忽略项，按约定不入 git。
- 门控（本轮实跑，各留自身 rc）：L1 `make check`、`check-milestone`、`check-patch-tree`（**173**）、`check-musl-freshness`、`check-syscall-abi`、`check-index-blobs`、`check-source-state`、`check-no-residue`、`check-tasks`、`check-knowledge-refs`、`check-component-changelog`、`check_issues.py` 全 **rc=0**（该轮在状态置 `待验收` 前执行）。状态置 `待验收` 后复跑：`check-tasks`/`check-knowledge-refs`/`check-no-residue` **rc=0**；`check-milestone` **rc=2** —— 唯一命中 = `check_tasks.py --strict` 对本册「完成区已填 + `待验收`」的**设计内**提示（`check_milestone_tasks.py` 段本身 PASS；`/complete` 置 `已验证` 后消失）。
