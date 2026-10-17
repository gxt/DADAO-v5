# LLVM-096t: `P2` 阶段 A1 出口判据的 4 个 `llvm` 面阻塞（驱动 `-shared` 转发 / `-fPIC` 相对查找表 / `-shared` 拒局部 `ABS48` / VLA `stackrestore`）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`INFRA-085t`（**登记源 + 消费方**：`P2` 阶段 A1 现场实测登记 `ISS-239`/`ISS-240`/`ISS-241` + 追加 `ISS-222 ④`；本册解其出口判据的 4 项 `llvm` 面阻塞）；`ISS-239`/`ISS-240`/`ISS-241`/`ISS-222`（④ 条）（`.tao/knowledge/issues.yaml`，**现场证据 + 根因 + 建议修法的真源**）；`LLVM-094t`（`已验证` 2026-10-17：CodeGen PIC/`-fPIC` + LLD `ET_DYN`/`.dynamic`/`.got`·`.plt`/动态重定位基线）、`LLVM-095t`（`已验证` 2026-10-17：`ADR-0029` 的 `aip.si` + `PCREL_HI/LO` 实现）；`ADR-0019 D10`（类型集与编号，**冻结**）/ `D12`（`PCREL_HI`=14 / `PCREL_LO`=15 / `NUM`=16）、`ADR-0026 D2`/`D7②`、`ADR-0029`（`Accepted`；`PCREL_HI/LO` **只服务指令站点**）；契约真源 = `.tao/contracts/contract-elf.md §2.2`/`§3`、`.tao/contracts/contract-dynlink.md §4.3`/`§7`/`§10`；纪律 = `ISS-229`（L2/L3 串行、禁并发）、`ISS-210`（改 MC/`.td`/驱动 ⇒ **必单跑 `install-host`**）、`docs/Process-01`（组件补丁树）、`docs/Process-05`（L1/L2/L3）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现场证据（**先读**）

- 来源 = `INFRA-085t`「完成区（阶段 A1）」的「新发现/坑 ①②③⑤」+「遗留问题」+ 第 1 轮 engineer 自审 F8（`A1 ACCEPTANCE: BLOCKED`）+ `.tao/knowledge/issues.yaml` 的 `ISS-239`/`ISS-240`/`ISS-241`/`ISS-222`（**第 ④ 条**）。architect 立项，2026-10-17（主会话裁定）。
- **事实（现场，勿重复查证）**：`INFRA-085t` 阶段 A1 的**构建接线已完成**（`tools/infra/build_musl.py` 的 `--shared` 档 + `Makefile` 的 `build-musl-shared` + 符号链接/模式守卫 + 证据脚本），**musl 侧补丁 = 0**；A1 的**出口判据整体 = BLOCKED**，成因**全在生产者侧（本模块）**：4 项里 3 项来自 `components/llvm-project/**`，第 4 项（`ISS-222 ④`）是**后端缺 lowering**（同样是本模块）。⇒ 本册 = **A1 出口判据的解阻塞册**。
- **在役绕行（非修本册项）**：`-Wl,-shared`（`build_musl.py` 的 `SHARED_LDFLAGS`；`ADR-0026 D2` 同族口径「构建侧显式传」）⇒ 本册**不改** `infra` 侧（见「不做项 1」），只让**裸传可用**、并保证该绕行**不回归**。
- **证据指针（本机留档，不入库）**：`.work/log/infra/INFRA-085t-evidence/`（`s3-shared-build.log` = 两项编译期失败签名；`s4-probe-link.log` = `-Wl,-shared` 正面；`s5-bare-shared.log` = 裸 `-shared` 被丢；`s4b-gap3-{shared,static}.log` = 局部 `ABS48` 对照）；`.work/evidence/INFRA-085t/run.sh`（节 `S3`/`S4`/`S4b`/`S5.2`）。

## 目标

解掉 `P2` 阶段 A1 出口判据的 **4 个 `llvm` 面阻塞**（下列 ①–④），使 `INFRA-085t` 阶段 A1 的出口判据（真 `musl libc.so` = `ET_DYN` + `.so` 命名/符号链接，见其验收标准 1）**可达**；本册判据 = **能编 + 静态可核**（**不跑**，跑归 `P3`）。

| # | issue | 现象（一句话） | 本册判据（详见「做」） |
|---|---|---|---|
| ① | `ISS-239` | 驱动**静默丢弃**裸 `-shared` ⇒ 产物 `ET_EXEC` 且无 `.dynamic`（仅一条 `-Wunused-command-line-argument`，rc=0） | 裸 `-shared` ⇒ `ET_DYN` + `.dynamic`；**不得**静默丢弃 |
| ② | `ISS-240` | `-fPIC` 下 LLVM **relative lookup table** 发 `.dd.t32`（4 字节 PC 相对数据域）⇒ MC 拒（DADAO 无该类型） | `fmtmsg.c`/`regcomp.c` **可 `-fPIC` 编过** + 表项重定位正确（独立 oracle） |
| ③ | `ISS-241` | `-shared` **拒** `R_DADAO_ABS48` 打 `.rodata` 内**局部标签**（`recompile with -fPIC`，而对象本就是 `-fPIC`） | **判清**「应允许」还是「应报错并给出正解」⇒ **如实写进册、不预设**；按判定给对应判据 |
| ④ | `ISS-222 ④` | `ldso/dynlink.c` 的 VLA（`alloca`）⇒ `Cannot select: stackrestore`（**加不加 `-fPIC` 都败**） | `dynlink.lo` **可编**（rc=0）+ VLA 栈调整指令序列可核 |

## 接口规范

- **输入**：4 项的现场复现（见「做」，命令 + 期望 + 现状签名）；`ADR-0019 D10`/`D12`、`ADR-0026 D7②`、`ADR-0029`、`contract-elf.md §2.2`/`§3`、`contract-dynlink.md §4.3`/`§7`/`§10`；**只读**：`.work/source/llvm-project/**`（源码检出）、`.work/source/musl/**`（消费侧复现源）、`.dadao/cross-toolchain/**`（工具链 + sysroot）；`components/llvm-project/patches/**`（现状）；`manifests/components.lock.toml`（版本锁）。
- **输出**：
  1. **组件补丁**：`components/llvm-project/patches/**`（**一文件一补丁**、镜像上游仓内路径，`docs/Process-01`；`check-patch-tree` 机械校验）+ `series` 同步 + `components/llvm-project/changelog.md`（`Process-01 §10` 体例）；
  2. **证据**：`.work/evidence/<任务ID>/run.sh`（**一键、非交互、任一失败非零退出**、逐项打印「检查名 + 期望/实际 + rc」、含 `--inject` 可达 FAIL）+ 原始输出落 `.work/log/llvm/**`；
  3. 本册完成区（≤30 行）+ `.tao/knowledge/milestones.md` 流水行。
- **约束**：**最小改动**、只碰任务范围；**不得**改 `spec/`、`contracts/`、`.tao/contracts/**`（**须用户授权**）；**不得**新增/改重定位类型编号（`ADR-0019 D10` **冻结**；`D12` 的 `PCREL_HI/LO` **只服务指令站点**，**不得**挪用为数据域 PC 相对）；**不得**自拟公式/行为；组件源一律 **git 基线**（只经 `patches/**`，**不得**直接改 `.work/source/**` 作为交付）；**计数不写死**（现场派生）；期望值**独立**（不从 v5 自身实现反推）。

## 做（四项；每项给「复现命令 + 期望 + 验收 + 可达 FAIL」）

> 复现统一在 **workdir（= 仓库根）** 内、相对路径；`<TC>` = 安装根 `cross-toolchain/bin`（`ADR-0016`，路径经 `manifests/` 定位、**不硬编码**）；`<TMP>` = `/tmp/opencode/LLVM-096t/`。改 `components/**` ⇒ **单跑一次** `make install-host`（**申报耗时**、`JOBS=8`、**禁并发**、`ISS-210`）后再跑运行期判据。

### ① `ISS-239`：驱动静默丢弃裸 `-shared` ⇒ **根治驱动（转发）**

- **现场（读源码，真源 = `components/llvm-project/patches/clang/lib/Driver/ToolChains/DADAO.cpp`）**：`dadao::Linker::ConstructJob` 只 `Args.addAllArgs(CmdArgs, {OPT_T, OPT_L, OPT_e, OPT_u, OPT_s, OPT_r})`（+ `AddFilePathLibArgs` + `AddLinkerInputs`）⇒ **驱动层 flag `-shared` 不进 `ld.lld`**；其注释「the driver itself already hands `-Wl,<arg>` / `-Xlinker <arg>` through」**只覆盖 `-Wl,` 形式**。`ld.lld` 单独 `-shared` **可用**（`LLVM-095t` 现场）。
- **复现（现状：产物 `EXEC` + warning、rc=0）**：
  ```
  <TC>/clang --target=dadao-unknown-elf -O1 -fPIC -ffreestanding -nostdinc -c <TMP>/probe.c -o <TMP>/probe.o
  <TC>/clang --target=dadao-unknown-elf -nostdlib -shared -Wl,--hash-style=gnu -Wl,-soname,libc.so -Wl,-z,undefs \
      -o <TMP>/probe-bare.so <TMP>/probe.o
  readelf -h <TMP>/probe-bare.so | grep Type:      # 现状: EXEC
  readelf -d <TMP>/probe-bare.so                    # 现状: There is no dynamic section in this file.
  ```
- **期望**：裸 `-shared` ⇒ **`ET_DYN`** + **有 `.dynamic`**（至少含 `DT_SONAME`/`DT_GNU_HASH`，与 `-Wl,-shared` 路径同形）；`clang` **不得**静默丢弃（`-Wunused-command-line-argument` 只许在**显式拒绝**路径出现）。取**转发**路线（`-shared` ⇒ `-shared` 传给 `ld.lld`）。`-static`/`-pie` 属同族但**不在本册判据内**（顺带做须在完成区披露）。
- **验收**：① 上列命令 rc=0 且 `readelf -h` = `DYN`（`ELF64` + 大端）、`readelf -d` 有 `DT_SONAME` + `DT_GNU_HASH`、**无** `DT_HASH`/`DT_RELR`/版本段（`contract-dynlink §5`）；② **不回归**：`-Wl,-shared` 路径（`INFRA-085t` 在役绕行）产物与基线**逐条同形**；③ 驱动层行为可由**驱动自身**证明（`-###` / `-v` 的命令行含 `-shared`）。
- **可达 FAIL**：断言「裸 `-shared` 产物 `Type: DYN`」 + 「`.dynamic` 非空」—— **现状即 FAIL**（天然可达）；另加**对照断言**：**不传**任何 `-shared` 的同源链接产物必须 `EXEC`（**证断言非恒真**）。

### ② `ISS-240`：`-fPIC` 相对查找表发 `.dd.t32` ⇒ 目标侧缺 **TTI opt-out**

- **现场（读源码）**：`RelLookupTableConverter` 模块 pass（`llvm/lib/Transforms/Utils/RelLookupTableConverter.cpp`；`PassBuilderPipelines.cpp` 内**无条件**加入）把「`static const` 指针常量表 + GEP/load」改写成**相对查找表**（表项 = `元素地址 − 表基址`，32 位）⇒ 需**32 位 PC 相对数据**重定位；DADAO 类型集**冻结无此类**（`ADR-0019 D10`；`ADR-0029` 的两类型**只服务指令站点**）。开关 = `BasicTTIImpl::shouldBuildRelLookupTables()`（`llvm/include/llvm/CodeGen/BasicTTIImpl.h`，默认「PIC + 64 位 + 非 Medium/Large code model」= true），而 DADAO 目标**无 `TargetTransformInfo` 覆盖**（现场核：`components/llvm-project/patches/llvm/lib/Target/DADAO/` 下无 `*TransformInfo*`）。
- **复现（现状：rc≠0；`fmtmsg` 4 错 / `regcomp` 20 错，含 `-ferror-limit`）**：
  ```
  cd .work/source/musl
  <TC>/clang --target=dadao-unknown-elf -std=c99 -nostdinc -ffreestanding -O2 -fPIC \
      -I./arch/dadao -I./arch/generic -Iobj/src/internal -I./src/include -I./src/internal -Iobj/include -I./include \
      -c -o <TMP>/fmtmsg.lo src/misc/fmtmsg.c        # 现状: 4 errors
  <TC>/clang … -c -o <TMP>/regcomp.lo src/regex/regcomp.c   # 现状: 20 errors
  ```
  签名（现场）：`error: relocatable operand in a 1/2/4-byte data field (.byte/.short/.long) cannot carry a 48-bit DADAO address; use '.dd.o64'/'.quad' (8-byte field)` 与 `error: relocatable operand in '.dd.b08/.dd.w16/.dd.t32' is not supported (a DADAO address needs an 8-byte field; use '.dd.o64')`；触发行（`-save-temps`）= `fmtmsg.s` 的 `.dd.t32 .L.str.6-.Lswitch.table.fmtmsg.rel`。
- **期望**：两源**均 rc=0**；落回 **8 字节绝对项**（`.dd.o64`）即为合格（**等价于**目标侧 opt-out：`shouldBuildRelLookupTables() → false`）。**不得**以「新增重定位类型 / 挪用 `PCREL_HI/LO`」实现（`ADR-0019 D10` 冻结）。
- **验收**：① 两条编译命令 rc=0；② **独立 oracle（表项正确性）**：`-save-temps` 保留 `.s` ⇒ 断言**无** `.dd.t32`（或任何 1/2/4 字节数据域携带可重定位符号差），且表项为 **8 字节**绝对项；**独立**用 `llvm-readobj --relocations`（或自写 ELF64-BE 解析）逐条核 `R_DADAO_ABS48`(6) 的落点/宽度，期望值按 `ADR-0019 D10`/`contract-elf.md §2.2` **独立算**（**不从 LLVM 读取器反推**）；③ `-fPIC` 与**非 PIC** 两档均编过，且**非 PIC 产物逐字节不回归**（`LLVM-094t` 阶段 A 基线对账）。
- **可达 FAIL**：`--inject`（把表项改回 4 字节 / 让 pass 重新生效）⇒ 断言 FAIL ⇒ `cp` + md5 还原 ⇒ 回绿。

### ③ `ISS-241`：`-shared` 拒 `ABS48` 打 `.rodata` 内局部标签 ⇒ **先判性质、再给正解**

- **现场（读源码 + 最小复现）**：`-fPIC` 下**常量指针表**（本条来自 `catopen()` 的 dense `switch` 派生表，`src/locale/catopen.c`）被 LLVM 留在**只读节**（`.rodata.catopen`，**非** `.data.rel.ro`）并以**绝对地址**（`ABS48`）表达；共享对象里「局部符号的绝对地址」只能在**装载期**由动态重定位（`R_DADAO_RELATIVE` 族）修正 ⇒ 要求 ①编译器把该常量放进**可写可重定位**节，**或** ②链接器把局部 `ABS48` 转成 `R_DADAO_RELATIVE` 并把节置可写 —— 现状**两者都缺**（lld 直接报错）。
- **复现（现状：rc=1、单对象 20 处；同一对象静态链接**不**报该错）**：
  ```
  <TC>/clang --target=dadao-unknown-elf -nostdlib -Wl,-shared -o <TMP>/gap3.so \
      .work/source/musl/obj/src/locale/catopen.lo          # rc=1, 20x: relocation R_DADAO_ABS48 cannot be used
  <TC>/clang --target=dadao-unknown-elf -nostdlib -Wl,-e,_dlstart -o <TMP>/gap3.exec \
      .work/source/musl/obj/src/locale/catopen.lo          # 对照: 不报该错
  llvm-readobj --relocations .work/source/musl/obj/src/locale/catopen.lo   # 现场: .rela.rodata.catopen 有 3 条 R_DADAO_ABS48 .L0
  ```
- **必须判清的性质（**如实写进完成区、不预设**）**：
  - **(甲) 应允许**：局部符号的 `ABS48` 在 `-shared` 下**应可解析** ⇒ 修法 = 编译侧按 PIC 规则把此类常量放 **`.data.rel.ro`**（首选，与各 arch 一致）／或链接侧把**局部** `ABS48` 降级为 `R_DADAO_RELATIVE`(8) + 节置可写（**不得**新增类型编号）。
  - **(乙) 应报错并给出正解**：若判定「本 ISA/ABI 下该形态**不可支持**」⇒ 允许 **rc≠0**，但**文案必须给出可执行的正解**；现文案 `recompile with -fPIC` 在**对象本就是 `-fPIC`** 时**误导** ⇒ 至少须改为**可执行指引**，且**不得**静默。
  - **判定依据** = `ADR-0019 D10`（类型集语义）/ `ADR-0026 D7②` / `contract-dynlink.md §4.3`/`§10` / ELF gABI 惯例；**若修法触及 ABI·契约口径或须改 `.tao/contracts/**`/`spec/` ⇒ 停下留问**（须用户裁定 / 可能需要 ADR，`docs/Process-03`）。
- **验收（按判定分支）**：**甲** ⇒ 该命令 rc=0、`.rela.dyn` 含 `R_DADAO_RELATIVE`(8) 打该节、该节**可写**（`readelf -S` 段标志含 `W`），且**独立 oracle** 按 `B+A` 无符号 48 位公式独立算并逐条对账；**乙** ⇒ rc≠0 但文案含**可执行正解**、且**不**再出现「对 `-fPIC` 对象说 `recompile with -fPIC`」的误导文案。**两种情形均须**给「同对象静态链接不报该错」的**对照组**证据（现状已有）。
- **可达 FAIL**：甲 ⇒ 把节标志改回只读（副本注入）⇒ 断言 FAIL ⇒ 还原回绿；乙 ⇒ 把文案改回误导句 ⇒ 断言 FAIL ⇒ 还原回绿。

### ④ `ISS-222 ④`：`alloca`/VLA 的 `DYNAMIC_STACKALLOC`（`stackrestore`）无法 select

- **现场（两轮实测）**：`ldso/dynlink.c` 的 `__dls2` 有 VLA `size_t addends[symbolic_rel_cnt+1]`（`ldso/dynlink.c:1752`；上界由 `ADDEND_LIMIT` + `a_crash()` 保证）⇒ `clang -c` **rc≠0**：`fatal error: error in backend: Cannot select: t66: ch = stackrestore t65, t5`（`t5: i64,ch = stacksave t0`），pass = `DADAO DAG->DAG Pattern Instruction Selection`；**加不加 `-fPIC` 都失败**（同签名）。它**同时挡 `INFRA-085t` 阶段 C1 的 `ldso` 真接入**（`dynlink.c` 是 `LDSO_OBJS` 唯一来源）。
- **复现（现状：rc≠0，两轮同签名）**：
  ```
  <TC>/clang --target=dadao-unknown-elf -ffreestanding -nostdinc -fno-stack-protector -fPIC \
      -I./arch/dadao -I./arch/generic -Iobj/src/internal -I./src/include -I./src/internal -Iobj/include -I./include \
      -c -o <TMP>/dynlink.lo .work/source/musl/ldso/dynlink.c      # rc≠0, stackrestore
  <TC>/clang … -c -o <TMP>/dynlink.o   …                           # 无 -fPIC, 同签名
  ```
- **期望**：**`dynlink.lo` rc=0**（`ISD::DYNAMIC_STACKALLOC` + `STACKSAVE`/`STACKRESTORE` 有 lowering/`Cannot select` 消失）。**默认修后端**；若判「有界 VLA ⇒ 定长数组」走**源语义**改动 ⇒ **停下留问**（语义裁定；该源属 musl 移植面、改源即补丁面扩大）。
- **同族顺带复验（非本册判据）**：`ISS-223` 的 13 源里 `dynamic_stackalloc` 类（`src/process/{execl,execle,execlp,execvp}.c`、`src/unistd/getcwd.c`、`src/network/res_msend.c`）**若可编则记录**（并说明各自结果）；**逐条回删排除项归 `ISS-223`**（另册）。
- **验收**：① `dynlink.lo` rc=0；② **指令面 oracle**：`llvm-objdump -d`（或独立反汇编核对）证明栈指针按运行期量调整（VLA 语义落地、**非**固定小窗），**不**给「能跑」判据（无 `qemu-user` ⇒ 跑归 `P3`）；③ 既有非 VLA 函数**不回归**（同源其它函数反汇编/对象 md5 对账）。
- **可达 FAIL**：`--inject`（在副本里把该 lowering 分支回退成 `Cannot select` 形态，或把 VLA 判定改回）⇒ 断言 FAIL ⇒ `cp` + md5 还原 ⇒ 回绿。

## 验收标准

1. **四项逐条达成**：按「做」①–④ 各自的验收条款（每项**独立留证**，不得合写）。
2. **构建纪律**：改 `components/**` ⇒ **单跑一次** `make install-host`（**申报预计耗时**、`JOBS=8`、**禁**全核、**不与其他 L2/L3 并发**——`ISS-229`）；改 `.td`/MC/驱动 ⇒ **安装根必须新鲜**（`ISS-210`：lit/门控**读新根**，**禁**与旧生成物自洽的假绿）；组件源树按 `docs/Process-01 §6.3/§6.4` 收敛（E1/E3；`.work/source` **可 `git diff`**）。
3. **独立 oracle**：重定位/表项期望值 = `ADR-0019 D10`/`D12` + `contract-elf.md §2.2`/`§3` + `contract-dynlink.md §4.3` **独立算**；**不从 LLVM/LLD/QEMU/本仓工具反推**（`contract-dynlink §8`）；大端（`ELFDATA2MSB`）逐字节核。
4. **不回归**：① 静态档（非 PIC）路径与 `LLVM-094t` 阶段 A 基线**逐字节**对照（差异须逐条归因）；② `-Wl,-shared` 绕行路径同形；③ 无 `spec/`/`contracts/`/`.tao/contracts/**` 改动（若判需改 ⇒ **留问**，不擅改）。
5. **可达 FAIL 证据**：`.work/evidence/<任务ID>/run.sh` 可跑通（非交互、逐项打印期望/实际/rc、任一失败非零退出）；**每条断言有可达 FAIL 路径**（`--inject` ⇒ FAIL ⇒ `cp` + md5 对账还原 ⇒ 回绿）；**禁恒真断言**、**禁** `git checkout/restore/stash` 还原；**计数不写死**。
6. **门控**（各留**自身**真实 rc；**禁** `cmd | tee` 吞码）：`make check`（L1）；`make check-patch-tree`、`check-index-blobs`、`check-instrinfo`（若改 `.td`）、`check-source-state`、`check-no-residue`、`check-tasks`、`check-knowledge-refs`、`check-knowledge-dir`、`check-component-changelog`、`python3 tools/infra/check_issues.py` 各 **rc=0**；**L2（`make check-modules`）任务收尾跑**（**串行、禁与 L3 并发**）；**L3 归里程碑 / `/complete`**。
7. **不做运行验证（显式声明）**：无 `qemu-user`（`P3`）⇒ 完成区**不得**出现「运行通过 / E2E 通过」叙述；判据一律 = **能编 + 静态可核**。
8. **完成区与真实输出逐条对齐**（≤30 行）；`milestones.md` 流水行已更新。

## 不做项（显式）

1. **`P2` 的 `infra` 面**（`INFRA-085t` 范围）✗：`ISS-242`（`src/thread/dadao/syscall_cp.s`，**语义实现 / 或经用户裁定显式声明不支持**）、阶段 **C1** 的 `ldso` 真接入（`GETFUNCSYM` 基址相关化、`arch/dadao/reloc.h` 复核）、阶段 B1/D1/E 的构建侧、`tools/infra/build_musl.py`/`Makefile` 的任何改动、**回退 `-Wl,-shared` 绕行**。
2. **`D2`（TLS 类动态重定位发射）** ✗ —— 见「待确认项 ①」（**另行裁定**；未裁定前本册不含）。〔**2026-10-17 已推迟**到 `M9+`（主会话决定、待用户追认），见「待确认项 ①」注记〕
3. **`ISS-222` ①②③**（`%N` 代入 / `"m"` 操作数 ISel 崩 = `ISS-197` / `rotl`·`rotr`·`bswap` ISel 选择）与 `ISS-223` 的**逐条回删排除项** ✗（另册；本册只解 ④）。
4. **运行验证 / `qemu-user` / 三套测试集**（`P3`/`P4`）✗。
5. **改 `spec/`、`contracts/`（机器数据）、`.tao/contracts/**`（正文）** ✗（须用户事先授权）；**新增/改重定位类型编号** ✗（`ADR-0019 D10` 冻结）；**relaxation** ✗（`ADR-0019 D7`）。
6. **`L3` 与里程碑判定** ✗（归主会话 / `/complete`）。

## 待确认项

| # | 项 | 我的默认（**待用户确认**） | 备选 / 影响 |
|---|---|---|---|
| ① | **`D2`（TLS 类动态重定位**发射**）归属**：**并入 `LLVM-096t`** 还是 **另立 `LLVM-097t`** | **不预设（本册不替用户定）** —— 未裁定前本册**按「不含 `D2`」执行**（见「不做项 2」）。**现场事实（供裁定）**：`components/llvm-project/patches/lld/ELF/Arch/DADAO.cpp` **现对类型 10/11/12（`TLS_DTPMOD`/`TLS_DTPREL`/`TLS_TPREL`）显式拒绝**（`getRelExpr` + `relocate` 两处；文案 `TLS dynamic relocation … is not supported yet (contract-dynlink.md §7)`），**非静默**（`ADR-0026 D7②`/`contract-dynlink §10②` 的「首版不发射、遇即报错」）；其打通还牵 `INFRA-085t` 阶段 **D1**（`infra` 面：`PT_TLS`/`TP=rb3`/`TLS_ABOVE_TP`/`DTPMOD`·`DTPOFF`·`TPOFF`/静态 `__thread`）与 `contract-dynlink §7` 的 musl arch 宏 | **(甲)** 并入本册 ⇒ 本册范围 = 4 + 1 项（**A1 出口判据仍只算前 4 项**；`D2` 的可核判据 = `__thread` 变量可编译并落 TLS 类重定位，编号与 `§4.3` 一致）；**(乙)** 另立 `LLVM-097t` ⇒ 本册**只解 4 项**、`D2` 独立排期（**与 `D1` 的先后**须同时排定）；**(丙)** 其它。⇒ 影响：任务粒度 / 验收面 / 与 `INFRA-085t` 阶段 D 的串行关系〔**收尾注记（2026-10-17，主会话决定、待用户追认）**：**`D2` 已推迟到 `M9+`** ⇒ 本项「归属」**无需裁定**、本册「不含 `D2`」即为终态；依据（`D1` 已够 `M8`、`D2` 仅 `dlopen` 需要）/ 触发条件（引入 `dlopen` 时）= `INFRA-085t`「待确认项 ⑦」/ `milestones.md` 中 `INFRA-085t` 行〕 |
| ② | **回退 `-Wl,-shared` 绕行**（`build_musl.py` 的 `SHARED_LDFLAGS`）的**时机** | **不在本册**：属 `infra` 面 ⇒ 由 `INFRA-085t`（或其后小任务）在①落地后回退；本册只保证**裸传可用**且**绕行不回归**（验收 4②） | 若要求本册一并回退 ⇒ 须扩范围到 `tools/infra/**`（与 `INFRA-085t` 同改共享文件 ⇒ **串行**），并重跑 A1 证据脚本 |

## 完成区

**测试结果**：`.work/evidence/LLVM-096t/run.sh` **54 PASS / 0 FAIL（rc=0）**；`run.sh --inject` **66 PASS / 0 FAIL（rc=0）**（12 条注入/还原逐项「预期 FAIL → 副本还原 → 回绿」，含 `md5 -c` 逐文件对账）。门控（各留自身 rc）：`check-patch-tree` **150 份/0**、`check-instrinfo` 0 errors、`check_lit_gen` 64/0、`check-index-blobs`/`check-source-state`（base+1、clean、HEAD=`04b2a59`）/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-knowledge-dir`/`check-component-changelog`/`check-issues`/`check-dirs`/`validate-vectors` 全 **rc=0**；**L1 `make check` rc=0**。**未跑** `install-host`/L2/L3（归主会话）。
**修改文件**：组件源（`.work/source/llvm-project`，E1 收敛为 base+1 单 commit）**5 改 + 3 增** ⇒ 补丁 8 份（`series` 147→**150**）：`clang/lib/Driver/ToolChains/DADAO.cpp`（122 行）；`llvm/lib/Target/DADAO/{CMakeLists.txt, DADAOISelLowering.cpp, DADAOTargetMachine.cpp, DADAOTargetMachine.h}`；新增 `DADAOTargetTransformInfo.h`（63）、`DADAOTargetObjectFile.{h,cpp}`（31/76）。v5 侧：`components/llvm-project/{patches/**, series, changelog.md}`。证据：`.work/evidence/LLVM-096t/{run.sh, jt_rela_oracle.py, vla_oracle.py, mutate_elf.py, jtlink-stubs.c, baseline.json}`（日志 `.work/log/llvm/LLVM-096t/`）。
**验收结果**：① `ISS-239`：裸 `-shared` ⇒ **`ET_DYN`** + `.dynamic`（`SONAME`/`GNU_HASH`/`BIND_NOW`，无 `DT_HASH`/`DT_RELR`/版本段），`-###` 恰传 **1** 个 `-shared`；对照（不传 `-shared`）⇒ `ET_EXEC`；`-Wl,-shared` 的 `ld.lld` argv + 产物 md5 与改动前**逐字节相同**。② `ISS-240`：`fmtmsg`/`regcomp` `-fPIC` **rc=0**（原 4/20 错）、`.s` **零** `.dd.t32`（`.dd.o64` 33/278 条）、独立 ELF64-BE oracle 全绿（表 = 8 字节 `R_DADAO_ABS48`，计数现场派生）。③ `ISS-241`：判定 = **(甲) 应允许**（依据 `contract-dynlink §4.3` 已定义 `RELATIVE`=`B+A` + ELF `.data.rel.ro` 惯例；**未改契约/`spec`、未新增类型**）⇒ `-shared` **rc=0**、`.rela.dyn` **41** 条 `R_DADAO_RELATIVE` 打 `.data.rel.ro`（`B+A` 逐条独立对账）、节 `SHF_WRITE`，同对象静态链接对照不报该错。④ `ISS-222④`：`dynlink.c` `-O0`（**含/不含** `-fPIC`）**rc=0**，`__dls2` 反汇编 `rb2rd{rd4},{rb1}` → `sub.uo{rd0,rd4},rd4,rd6` → `rd2rb{rb1},{rd4}`（运行期量）+ 第二次 `rb1` 写回（`stackrestore`）。
**新发现/坑**：1) ④ 修好后 `dynlink.c` 的 `-O2` 编译又暴露**另一个既存缺口** `Cannot select: i64 = bswap`（`map_library`）——`-emit-llvm` 前后 **diff 0 行** ⇒ 非本册引入，属 `ISS-222 ③`/`ISS-193(c)` 面（本册「不做项 3」）⇒ **A1 出口判据在 `-O2` 仍被该缺口挡住**，不是 `-shared`/`-fPIC` 面能解。2) `tests/scripts/dadao-dyn.lds` **未列** `.data.rel.ro`（当前无任何流程引用该脚本；A1 用 musl `LDFLAGS` 不用它）⇒ 后续若用它链接带 dense switch 的 PIC 对象，`.data.rel.ro` 成 orphan（lld 归 RWX `PT_LOAD`：功能正确、不进 RELRO）。3) 驱动顺带转发 `-static`/`-pie`（同族静默丢弃；仓库内**无**流程传 `-static`，已核）。4) `CodeGenTargetMachineImpl::getTargetTransformInfo` 默认给 `BasicTTIImpl`（PIC+64 位 ⇒ rel 表 true），故必须**目标侧覆写**才能 opt-out（`TargetMachine` 基类返回的 `NoTTIImpl` 反而恒 false，别混淆）。
**遗留问题**：① **`dynlink.lo` `-O2` rc=0 未达**（`bswap`，另册 `ISS-222③`）——本册 ④ 的「能编」判据在 `-O0` 达成、`-O2` 仅达成「`stackrestore` 消失」；② 任务 `**状态**` 与 `.tao/knowledge/milestones.md` 流水行按派发要求**未改**（归 `/complete`）；③ `ISS-241` 判定 (甲) 已落纸；若须 ADR 固化（`docs/Process-03` 判据）请主会话裁定——本册未写 ADR。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：8 份补丁（5 改 3 增）+ 证据脚本 6 份。逐行审查改动源码、证据断言与注入路径。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `mutate_elf.py patch-byte` 把指令地址按十进制解析（`int(x,0)`）⇒ 注入落到错误偏移，I4 实际未改字节 | ✅已修 | 地址改 `int(x,16)`；并加两条断言（`I4a` 变更已落地、`I4b` 回读反汇编须显示 `sub.uo {rd0, rd4}, rd4, rd4`） | `--inject` 中 I4a/I4b/I4c 全 PASS；mutated 反汇编实测 `52 00 41 04` |
| F2 `jt_rela_oracle` 原断言「`.rela.dyn` 里除跳转表外不得有 `RELATIVE`」——GOT 槽合法地也有 `RELATIVE` ⇒ 假红（把真问题掩在噪声里） | ✅已修 | 计数/配对限定在 `.data.rel.ro` 地址区间内（GOT 在外） | oracle `41 vs 41`、`matched=41 of 41`，rc=0 |
| F3 oracle 第一版假设输出仍有 `.text.catopen` 节（lld 把 `.text.*` 并入 `.text`）⇒ 锚点取值失败 | ✅已修 | 改为「锚符号 `catopen` 在 object 的节内偏移 vs 输出地址」求放置偏置；对象 JT 尺寸 == 输出 `.data.rel.ro` 尺寸亦作断言 | `anchor 'catopen' ... value=0x10908`、`328 vs 328` |
| F4 `S1.16` argv 归一化把占位符包进引号（`"<OBJ>"`）⇒ 1 条假 FAIL | ✅已修 | sed 连引号一起替换 | 改动前后 argv 逐字相同 |
| F5 组件检出需回到 E1（base+1 + clean）才能导出补丁 | ✅已做 | `git add -A` + `commit --amend`（未推送；任务派发已允许）；**只动 `.work/source/llvm-project`** | `check-source-state`：`HEAD=04b2a59 count=1 clean=True`；`check-patch-tree` 150/0 |
| F6 `-mcmodel=large` 下 JT 前缀为 `.lrodata` ⇒ 我造 `.ldata.rel.ro`，而 lld 的 `getOutputSectionName` 前缀匹配会把它并进 `.ldata`（可写、可重定位，但**不进** RELRO） | ⏸延后 | 不改（大码模型当前未启用；功能正确性不受影响） | 已在完成区「新发现 2」类项记录；`-mcmodel=large` 场景无任务/测试覆盖 |
| F7 ④ 的验收条款「`dynlink.lo` rc=0」在 musl 的 `-O2` 下不可达（`bswap`，`ISS-222③` 另册） | ⏸延后 | 不越界修 `bswap`；改为「`-O0` 真实源 rc=0 + `-O2` 仅断言 `stackrestore` 消失」双证据 | `-emit-llvm` 前后 diff 0 行 ⇒ 缺口既存；`S4.1/S4.3/S4.4` 输出入日志 |
| F8 `tests/scripts/dadao-dyn.lds` 未列 `.data.rel.ro`（本册把 PIC 跳转表挪进该节） | ⏸延后 | 不改（属 `tests/**`，越界；当前无流程引用该脚本，A1 走 musl `LDFLAGS`） | `grep` 全仓：仅 `.work/evidence/LLVM-094t/**` 引用；已写入完成区与回报 |
| F9 驱动顺带转发 `-static`/`-pie`（任务仅硬性要求 `-shared`） | ✅已披露 | 三者同族（同为 `MachineOutputFlags` 被驱动吃掉）；`-Wl,` 通道不重复 | 全仓核：无流程传 `-static`；`-Wl,-shared` 仍恰 1 个 `-shared`、产物 md5 不变 |

**判决**：F1–F5、F9 已处置并复验；F6–F8 为**范围外/大码模型边角**，均已如实登记（未修 ≠ 未发现）。**无未修的实现缺陷** ⇒ 实现侧可交验收；任务 `**状态**` 与 `milestones.md` 按派发要求不动（归 `/complete`）。

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
