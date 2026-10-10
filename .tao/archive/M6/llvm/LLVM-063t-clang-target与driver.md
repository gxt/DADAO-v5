# LLVM-063t: DADAO clang target + driver/sysroot（钉子①）

**模块**：llvm
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建 `DADAO;X86`）、`SPEC-124t`（调用约定契约收口）、`LLVM-068t`（ABI 寄存器布局重排后端；**排本任务之前**）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `.tao/adr/adr-0003-object-abi.md`（`e_machine`/`e_flags`/ELF 形态；`contract-elf.md`）。
  - `.tao/knowledge/contract-abi.md §4/§6`（调用约定；clang ABI 形状来源）。
  - `.tao/adr/adr-0018-m3-codegen-choices.md`（DataLayout C9 等）。
  - `INFRA-050t` 产出的一次构建（`clang`/`llc`/`ld.lld`）。
  - 只读对照（**内容溯源，非执行依赖**）：RISC-V64 形状 + PPC64BE 端序/DataLayout + AArch64 调用约定。
- **输出**：
  1. `components/clang-project`/`components/llvm-project/patches/clang/**`：DADAO clang target——`clang/lib/Basic/Targets/**`（`TargetInfo`：DataLayout/端序/`__dadao__` 宏/类型宽度）、`clang/lib/Driver/**`（driver 名/`--target`/默认 `-march`）、**sysroot** 约定（`ADR-0016` 布局）。
  2. **只用于 freestanding**（无 libc/OS/syscall；`-ffreestanding` 语义为主）。
  3. 与 `clang` 一并入一次构建（`INFRA-050t` 目标产出）。
- **约束**：
  - 模板 = **RISC-V64 形状 + PPC64BE 端序/DataLayout + AArch64 CC**；**不**复制 RISC-V 的 ABI 细节（v5 有自己的 ABI）。
  - **`spec/` 交集为空**。
  - 与 Wave 2 其它任务**同改 `components/llvm-project/patches` ⇒ 串行**。
  - 不改 `LLVM` 数据流以外内容；期望值/校验来自 `contracts/`/`.tao/knowledge/`。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-063t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-063t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：改 `components/**/patches/**` ⇒ 开工前写明「重建 clang（增量），预计 N 分钟」；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-063t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **clang target 生效**：`clang --target=dadao-unknown-elf -c`（freestanding）对最小 C 源产出 DADAO 目标文件（给真实命令 + 输出 + `readelf` 证据：`e_machine`/端序）。
2. **DataLayout/端序**：生成对象/IR 与 `contract-abi.md §4.9` 的 DataLayout（大端 `E`）一致（给真实输出）。
3. **driver/sysroot**：`--target`/`-ffreestanding`/`-isystem`（sysroot）按 `ADR-0016` 布局解析（给真实输出）。
4. **无 libc 依赖**：`clang` 可编最小程序且**不**隐式引入 libc/syscall（给证据）。
5. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等**）。
6. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出。
7. **一键证据脚本**：`.work/evidence/LLVM-063t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检，给真实输出与退出码。
8. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：全绿。`make check` EXIT=0（lit 69/69）；`make check-patch-tree` EXIT=0（105 patches）；`make check-no-residue` EXIT=0；证据脚本 `run.sh`（`--no-inject` 与含注入自检两跑）均 `RUN_EXIT=0`。日志 `.work/log/llvm/LLVM-063t-*.log`。

**修改文件**：组件源码 12 处（新增 `clang/lib/Basic/Targets/DADAO.{h,cpp}`、`clang/lib/Driver/ToolChains/DADAO.{h,cpp}`、`clang/lib/CodeGen/Targets/DADAO.cpp`；改 `clang/lib/Basic/{Targets.cpp,CMakeLists.txt}`、`clang/lib/Driver/{Driver.cpp,CMakeLists.txt}`、`clang/lib/CodeGen/{CodeGenModule.cpp,TargetInfo.h,CMakeLists.txt}`）→ `components/llvm-project/patches/clang/**` + `series`（59→71）+ `README.md` + `changelog.md`；测试 `tests/e2e/clang_dadao_target.c`、`tests/e2e/lit/clang_dadao_target.test`、`tests/e2e/lit/lit.cfg.py`；证据脚本 `.work/evidence/LLVM-063t/run.sh`（不入 git）。

**验收结果**（真实输出）：
1. target 生效：`clang -target dadao-unknown-elf -c` rc=0；`llvm-readobj`：`Machine: 0xDA0` / `BigEndian` / `Class: 64-bit` / `Flags (0x1)`。
2. 宏：`__dadao__ 1`、`__DADAO__ 1`、`__BYTE_ORDER__ __ORDER_BIG_ENDIAN__`、`__SIZEOF_{POINTER,LONG,INT}__ = 8/8/4`。
3. `-S -O2`：标量 `add.uo {rd0, rd8}, rd17, rd16`；`struct{long,long}` 返回 `rd2rd {rd8},{rd16}` + `rd2rd {rd9},{rd17}`；按值传参 `rd16/rd17`；>64B `st.o rd4,[rb16,0]`（sret）。
4. DataLayout：clang `E-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128` == 后端（`TargetDataLayout.cpp` `case dadao`）逐字符一致。
5. sysroot：`-isystem .../cross-toolchain/bin/../../dadao-unknown-elf/include`（realpath = `.dadao/dadao-unknown-elf/include`）；无 `/usr/include`。
6. E2E：`clang -c → llvm-mc crt0 → ld.lld -T dadao.lds → qemu` 退出码 **42**（标量与 struct 传参/返回各一）。
7. 注入自检：改 `DADAO.h` TargetInfo DL 为小端 → clang 报 `err_data_layout_mismatch`（`backend data layout 'E-m:…' does not match expected target description 'e-m:…'`，rc=1）→ `cp`+md5 还原（md5 相等）→ 重建 → 回绿。

**新发现/坑**：
- clang `-emit-llvm` 的 `target datalayout` 源自 **TargetMachine**（`BackendUtil`），非 TargetInfo；二者由 clang 内置 `err_data_layout_mismatch` **强制一致** ⇒ TargetInfo 侧**必须** `resetDataLayout()` 由 triple 派生（写死字面量会编译报错）；0628 的 0020 写死旧串即反例。
- clang 默认 `DefaultABIInfo` 对**所有聚合**用间接（返回 sret、传参按指针），不满足 `contract-abi §6.1/§6.4` 的「≤64B 入寄存器」⇒ 须补 clang 前端 `DADAOABIInfo`（本任务已补）。
- 去 host `/usr/include` 须 `addClangTargetOptions` 加 `-nostdsysteminc`。
- driver 已自动透传 `-Wl,`/`-Xlinker`；工具内**不要**再 `AddAllArgValues(OPT_Wl_COMMA)`（会重复 `-T` → ld.lld `region already defined`）。
- 本机 LLVM 增量重链 clang ≈2–4 min；注入自检 2 轮重建可控（`make build-mc` + `install-host`，`JOBS=8`）。

**遗留问题**：
- **越界披露**：任务「输出」仅列 `clang/lib/Basic/Targets/**` + `clang/lib/Driver/**`；为满足验收②（`struct{i64,i64}⇒rd8/rd9`），**增动** `clang/lib/CodeGen/**`（`DADAOABIInfo` + 分发）。ABI 口径全取自 `contract-abi §6.1/§6.4`（非新决策），未擅自新增。
- `DADAOABIInfo` 为**最小首版**：仅「≤64B 直接值 / >64B 间接」；HFA/HPA（RF/RB bank）与更细跨 bank 拆分留 `LLVM-066t`（FP）及后续。`long double` 取 64-bit（`spec/` 未定义，freestanding 不涉 f128）。
- target sysroot 的 resource-dir `include/`（`cross-toolchain/lib/clang/23/include`）不在 `install-host`（ADR-0016 D11）范围、实际不存在 ⇒ `stddef.h` 等内建头暂不可用（freestanding 最小程序不受影响；如需另立任务）。


## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`clang/lib/{Basic/Targets/DADAO.*,Driver/ToolChains/DADAO.*,CodeGen/Targets/DADAO.cpp}` 及 4 处注册/CMake 改动；`.work/evidence/LLVM-063t/run.sh`。

**逐行审查意见与处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `Args.AddAllArgs(CmdArgs,{…})` 编译失败（多 id 重载是小写 `addAllArgs`） | ✅已修 | DADAO.cpp 改 `Args.addAllArgs` | `make build-mc` EXIT=0 |
| driver 内 `AddAllArgValues(OPT_Wl_COMMA)` 与 clang 自动透传叠加 → `-T` 重复 → ld.lld `region 'RAM' already defined` | ✅已修 | 删该调用（clang 已自动透传 `-Wl,`/`-Xlinker`） | `-###` 现 `-T …` 仅一次；driver 链接 E2E qemu rc=42 |
| cross clang 搜索到 host `/usr/include` | ✅已修 | 新增 `addClangTargetOptions` 推 `-nostdsysteminc` | `-E -v` 搜索表仅 sysroot include |
| 默认 `DefaultABIInfo` 对所有聚合间接（返回 sret），不满足 `contract-abi §6.1/§6.4` 的 ≤64B 入寄存器 | ✅已修 | 新增 `clang/lib/CodeGen/Targets/DADAO.cpp` 的 `DADAOABIInfo`（≤64B `getDirect`、>64B 间接）+ 分发/声明/CMake | `struct{long,long}` 返回 `rd8/rd9`、传参 `rd16/rd17`；struct E2E rc=42 |
| TargetInfo DL 若写死字面量会与后端偏离（clang 报 `err_data_layout_mismatch`） | ✅已修 | `DADAO.h` 用 `resetDataLayout()`（由 triple 派生，单一真源） | DL 逐字符一致；注入自检复现该诊断 |
| 证据脚本：sysroot 断言误匹配 `-cc1` 命令行 | ✅已修 | 只在 "search starts here" 段内匹配 + `realpath` 归一 | `run.sh --no-inject` 全绿 |
| 证据脚本：注入改 TargetInfo DL 后 `-emit-llvm` 的 DL 来自 TargetMachine，原「DL 不等」断言检测不到 | ✅已修 | 注入断言改为「clang 编译报 `data layout` 错误、rc≠0」 | 注入段 `inject_datalayout_mismatch_detected` PASS，还原后回绿 |
| lit 宏 CHECK 与 clang 输出顺序不符（`__DADAO__` 先于 `__dadao__`） | ✅已修 | 改 `MACRO-DAG`（无序组） | `llvm-lit tests/e2e/lit` 5/5 |

**判决**：finding 全部 ✅已修；`make check`/`check-patch-tree`/证据脚本（含注入自检）均 EXIT=0；`spec/` 交集为空、无残留。状态置 `待验收`。**越界披露**：为满足验收②增动 `clang/lib/CodeGen/**`（口径全取自 `contract-abi`，非新决策），详见完成区「遗留问题」。


#### 第 1 轮 reviewer 验收

**证据脚本审核**：合格。`check`/`check_rc` 正确递增 `FAILS`、无 `tee`、`set -u`、trap 清理、`cp`+`md5sum` 还原、注入非空可检测。

**重跑（--no-inject）**：36/36 PASS，`RUN_EXIT=0`。关键行：
- `datalayout_matches_backend expected=[E-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128] actual=[…S128]` ✓
- `e2e_qemu_exit_code expected_rc=42 actual_rc=42` ✓
- `e2e_struct_qemu_exit_code expected_rc=42 actual_rc=42` ✓

**独立注入（与 engineer 不同）**：改 `DADAO.h` 的 `LongWidth=64→32`。
- 注入前 md5=`66b1b01eb07c7a80f0fe4aa00609b533`
- 注入后 `__SIZEOF_LONG__=4` → `sizeof_long_8=FAIL`（预期）✓
- `cp`+md5 还原（md5 相等）→ 重建 → `__SIZEOF_LONG__=8` → PASS ✓
- 源树 `git diff .work/source/` 无残留，md5 一致。

**独立复核**：
- ① `--print-targets`：`dadao - DADAO SimRISC` ✓
- ② 宏：`__dadao__=1 __DADAO__=1 __BYTE_ORDER__=BIG_ENDIAN __SIZEOF_{POINTER,LONG,INT}__=8/8/4` ✓
- ③ DL：clang `E-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128` == 后端逐字符 ✓
- ③ 独立 E2E：自写 `my_e2e.c`（scalar 40+2）QEMU_EXIT=42 ✓；自写 `my_struct_e2e.c`（mkpair(30,12)+sum）QEMU_EXIT=42 ✓
- ④ 越界：`CodeGen/Targets/DADAO.cpp`（DADAOABIInfo）为 ABI 必需（DefaultABIInfo 对所有聚合间接，不满足 contract-abi §6.1/§6.4 的 ≤64B 入寄存器），已披露。无其它未披露越界。
- ⑤ 补丁：series 71 行（59+12 clang），12 补丁均非空，一文件一补丁 ✓；`make check-patch-tree` EXIT=0 ✓
- ⑥ 门控：`make check` EXIT=0（lit 69/69）✓；`make check-no-residue` EXIT=0 ✓
- ⑦ `git status`：仅任务文件 + `components/llvm-project/patches/clang/**` + `tests/e2e/**`；`spec/` 交集空 ✓；无 `_tmp/_orig/_rej` ✓

**判决：Accepted**
