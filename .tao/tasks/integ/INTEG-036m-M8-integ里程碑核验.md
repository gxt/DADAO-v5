# INTEG-036m: M8 integ 模块里程碑核验（无内核 Linux 用户态栈）

**模块**：integ
**项目里程碑**：M8
**状态**：待开始
**目标**：核验 **M8 = 无内核的 Linux 用户态栈**（`ADR-0025`）：musl（静态 → 动态）+ QEMU user-mode（`P1`→`P3`）。**`P4`（与 RISC-V + musl 的 golden 对照）已由用户 2026-10-18 裁定不作**（原行保留、写明不作，见下阶段表与 `ADR-0025 D7` 就地修订注记）。
**关联任务**：见下「阶段—任务—门控」表（逐行给真实任务号）；核验载体 = 本册。

> **补记说明（2026-10-17）**：本册为**事后补齐**，非开工时建立。M8 自 2026-10-13 起推进时未立 `INTEG-036m`；本笔按 `.opencode/agents/architect.md` 的 `m` 册格式补记，**不伪造当时记录**（当时的计划/裁定仍以 `milestones.md`「M8 规划区」与各任务书为准）。

## 目标与判据

1. **目标** = 无内核 Linux 用户态栈：musl 静态（`P1`）→ 动态（`P2`）→ `qemu-user` 两档跑（`P3`）。
2. **达成判据** ① **静态档 + 动态档都能编能跑**（`build-musl*` rc=0 + `qemu-dadao` 两档 E2E）；② 三套大型测试（embench-iot / libc-test / llvm-test-suite）两档跑通并**如实分类**（pass / fail / known-fail / blocked>0 ⇒ rc=1 / excluded 逐条 reason）；③ **判据修订（2026-10-18，用户裁定；原「golden 对照（RISC-V + musl）归 `P4`、`P4` 未完 ⇒ 本册不得置 `里程碑`」作废）** = **三套大型测试两档如实分类 + 失败逐条归因**（`fail`/`blocked` 逐条有证据与归属；`known-fail` 走逐例依据表）；`RISC-V` 交叉对照**不作**。
   > **用户原话（逐字；渠道 = 经主会话问答，2026-10-18 上午）**：「**1、首先，没必要做risc-v的交叉对比；2、除了thread和binary128以外，还余下多少个测试？**」
   > 本笔据此：三套测试自带 oracle（上游参考输出 / 用例自身退出码 / musl 自带 test），跨 ISA 对照无增量；`P4` 保留行但标「不作」（不删）。

## 阶段—任务—门控

| 阶段 | 任务（真实号） | 门控 / 判据 |
|---|---|---|
| `P0` 契约 | `SPEC-138t`（Linux syscall 映射）、`SPEC-139t`（动态链接 ABI）、`SPEC-140t`（musl TLS 硬依赖查证） | L1 `make check`（`check-spec-drift` / `check-contracts-dir` / `check-contract-relocs`） |
| `P1` 静态 | `INFRA-076t`（musl 1.2.6 取源锁定）、`INFRA-082t`（静态最小集）、`QEMU-060t`（`dadao-m1` syscall 服务回退）、`TESTCASES-045t`（P1 能力边界度量） | L1 + `make build-musl` rc=0；运行验证由 `P3` 承接 |
| `P2` 动态（生产者侧） | `LLVM-094t`（PIC/LLD 动态）、`LLVM-095t`（`PCREL_HI/LO` + PLT）、`LLVM-096t`（A1 四项阻塞）、`LLVM-097t`（`bswap`）、`LLVM-098t`（`-fPIC` `.rodata`）、`LLVM-099t`（`rotl`/`rotr`）、`LLVM-101t`（可变参聚合 `union semun` + `shmat()` 指针返回 bank；`047t` 静态档暴露）、`SPEC-145t`（`rela.si`）、`QEMU-061t`（`rela.si` 解码/语义） | L1 `check-patch-tree` / `check-instrinfo` / `check-contract-relocs` + **单跑** `install-host`（`ISS-210`、`ISS-229` 串行） |
| `P2` 动态（ABI 面） | `ADR-0031`（变参 ABI：`va_list` 七字段三游标 + callee 快照保存区 + 聚合三类〔HFA/HPA/通用聚合，64 B 门槛〕+ 16 B 半字顺序；**`Accepted`**，2026-10-18 `D1`–`D9` 逐条确认） | 已按 `Process-06` 授权改册（`spec/DADAO-21 §2.2`/`§3.2.3`/`§3.2.4`/`§3.3`/`§3.4` + 锁 `sha256`）与 `contract-abi`（`§4.2`/`§4.3`/`§4.4`/`§5`/`§6.3`/`§6.4`）；实现 = `LLVM-102t` B 项（已解阻塞）/ `LLVM-106t` / `INFRA-090t` |
| `P2` 动态（消费/构建） | `INFRA-085t`（`libc.so` + 动态可执行）、`INFRA-079t`（compiler-rt builtins，**全量**；排期见下） | `make build-musl-shared` rc=0 + `PT_INTERP` / `DT_NEEDED` 静态可核 |
| `P2` 动态（消费/构建） | `INFRA-088t`（driver **默认**接 compiler-rt builtins；`ISS-262` 用户裁定 ①） | **默认**（不带 `-rtlib`）链接端到端 rc=0 + `qemu-dadao` 跑通 + `install-host` 后安装根复核 + `build-musl`/`build-musl-shared`/`build-picolibc` 无回归 + 复跑四组零转移；`ISS-229` 串行；**实现完成、待验收（2026-10-18）** |
| `P3` 运行 | `QEMU-062t`（`qemu-dadao` 静态 + 动态两档 E2E） | L2 `check-modules` + L3 `check-full`（`check-qemu-semantics`） |
| 测试面 | `TESTCASES-044t` / `LLVM-093t`（语料取源锁定）、`TESTCASES-046t` / `TESTCASES-047t` / `TESTCASES-048t`（两档跑）、`INFRA-087t`（`strptime %s` 语义归属与分类订正；`047t` 静态档暴露） | runner 自身 rc（`blocked>0 ⇒ rc=1`，`ISS-248` 口径）；**不入 L1/L2/L3**（curated，`Process-07 §3`）；**`046t` = ✅ 静态 38/38 + 动态 38/38**（2026-10-17；动态档复跑于 `ISS-258` 处置后，driver rc=0）；**`047t` = ✅ 两档 `fail=0`**（静态=安装根，2026-10-17 第 4 轮：`pass 303 / fail 0 / known-fail 9 / blocked 25`，excluded 30；`known-fail 9` = TLS 3（`ISS-246`）+ `strptime` 1（`ISS-251`）+ `long double` 5（`ADR-0030`→`M9`）；`blocked 25` = `ISS-252`/`ISS-253`/`ISS-254`/`ISS-255` + compiler-rt；`pthread_create-oom` 计数抖动 = `ISS-257`）；**动态档 ✅（2026-10-17 第 5 轮）= `pass 298 / fail 0 / known-fail 8 / blocked 31`**（excluded 30；`blocked 31` = `ISS-252` 19 + `ISS-253`/`ISS-254`/`ISS-255` 各 1 + COPY 8（`ADR-0026 D7②`，待裁定 `ISS-259`）+ `pleval` 1（上游不构建，同上）） |
| 测试面 | `TESTCASES-049t`（libc-test 动态档用户 TU 改 `-fPIC`；`ISS-259` 用户裁定 ②） | 动态档 COPY 8 例：**7 例 `blocked→pass`** + `math/lgammal`→`known-fail`（`ISS-250`/`ADR-0030`）+ `musl/pleval` 仍 `blocked`；静态档 `303/0/9/25` 不变；**逐例记账** + 可达 FAIL；**真值（2026-10-18）= 动态 `305 / 0 / 9 / 23`**（基线 `298/0/8/31` 转移恰 8 条）、**静态 `303 / 0 / 9 / 25` 337 例逐例零 diff**；证据 `.work/evidence/TESTCASES-049t/run.sh`（default 62 PASS / `--inject` 3 处可达 FAIL） |
| 测试面 | `TESTCASES-048t`（llvm-test-suite 两档用户态跑） | A 类 **222** 单元 × 两档（静态→动态）：**真值（2026-10-18）= 两档逐数相同 `total 222 / pass 193 / fail 2 / known-fail 0 / blocked 27 / excluded 0`**（pass 拆分 = 参考 oracle **192** + exit-only 1）；残 2 `fail` = 参考输出可移植性（`ISS-265`，待裁定）；`blocked 27` = 编译/方言 7 + 300s 超时 6 + qemu 宿主信号 4（`ISS-266`）+ 缺头 3 + clang 崩溃 2 / `flog` libcall 2 / varargs 1 / `brind` 1 / `RUNTIME_INIT` 1（`ISS-267`）；证据 `.work/evidence/TESTCASES-048t-step2/run.sh`（17 项 PASS + 2 处可达 FAIL）；B 类 1890 **未跑** |
| `P4` golden 对照 | **不作**（用户 2026-10-18 裁定：不做 RISC-V 交叉对比；`ADR-0025 D7` 加就地修订注记） | 保留行 ✗ 不删；**不再作为 `M8` 判据**（判据③ 见上）；原「立册后另行定义」废止 |
| `M8` 收口·llvm | `LLVM-102t`（`brind` 间接分支 ISel；变参寄存器耗尽 **已解阻塞**） | lit 向量（`indirectbr` ⇒ `jump [rbX, rd0, 0]` 形态 + bank 依据）+ `evalloop` 两档转 `pass`；`check-patch-tree`/`check-instrinfo`/L1 + **单跑 `install-host`**；**② 项依据（2026-10-18）= `ADR-0031`（`Accepted`）`D2` callee 快照 / `D4` 不拆半 / `D8` 默认 `-Werror=varargs`**（`contract-abi §5` 已改「M8 收口」） |
| `M8` 收口·llvm | `LLVM-103t`（`flog` libcall 最小补齐） | 只补现场真正需要者（逐条列 + 理由）+ `CoMD`/`consumer-lame` 两档转 `pass` + lit 向量 + 可达 FAIL + L1 + **单跑 `install-host`**；**实现完成、待验收（2026-10-18）**：`LOG_F64`/`LOG10_F64` 两条注册 + lit（CodeGen 32/32）、补丁 **173**；`CoMD` 两档 `pass`（byte-exact）、`consumer-lame` 根因前移 = 变参寄存器耗尽（`LLVM-102t` 待开始）⇒ 两档转 `pass` **未达成**、`048t` 计数待 `LLVM-102t` 后合并作数 |
| `P3` 运行 | `QEMU-063t`（8 例宿主/guest 信号 + `unix-smail` 卡死） | 诊断时间盒 **1–2 h**（用户裁定「同意」；追加 `lua`/`lemon` 后不变）；逐例「信号/`si_code`/guest `PC`/归属/处置」；修或归因留 `ISS-255`/`ISS-266`/`ISS-269`（`open`）；`check-qemu-smoke` + L1；**2026-10-18 追加两表行** = `lua`（宿主 `SIGSEGV`，静态停 `bench/process.lua` / 动态停 `bench/meteor.lua`，并入 `ISS-266`）+ `lemon`（guest `SIGSEGV`，`example1.y` 最小复现，`ISS-269`） |
| 测试面 | `TESTCASES-050t`（驱动与口径收尾：include 路径 / 逐例超时 / 静态 builtins / `siod` 排除） | `048t` 两档 + `047t` 静态复跑**逐例记账**、无回归；可达 FAIL ≥3；L1 + 测试面门控；**实现完成、待验收（2026-10-18）**：include 解析/回退 + 逐例超时表（lemon 480 / lua 840 / SimpleMOC 480 / mafft 1620 / nbench 480）+ 静态 builtins（`303→304 / 25→24`）+ `excluded` 2 条；8 例两档 `4 pass / 3 blocked / 2 excluded`（filtered），libc 静态全量逐例 diff 仅 `tgmath`；**全量 220 例两档未跑**（计数为转移集派生） |
| `P1` 静态 | `INFRA-089t`（musl 端口 `sigsetjmp`；`ISS-254` 归属 = 端口面，不并入 `TESTCASES-050t`） | `functional/setjmp` 静态 `blocked→pass`（savemask 两支语义独立 oracle）；或显式不支持 + **留问**改标；`check-patch-tree`/`build-musl`/L1；**实现完成、待验收（2026-10-18）**：新增 `src/signal/dadao/sigsetjmp.s`（`series` 19、补丁 **174**），`047t` 静态 `functional/setjmp` **blocked→pass**（savemask 1 恢复 / 0 不恢复），全量 `047t` 静态档待复跑 |

## 已知限制 / 后置

- **剩余非 `pass` 例（现场派生，2026-10-18）**：`TESTCASES-048t` A 类两档**逐数相同 = 29 例**（`27 blocked + 2 fail`）⇒ **20 要动 / 9 有据**。要动 = 缺头 3（`TESTCASES-050t ①`）+ 超时 6（`TESTCASES-050t ②` 5 + `QEMU-063t` `unix-smail` 1）+ 宿主信号 4（`QEMU-063t`）+ `flog` libcall 2（`LLVM-103t`）+ `brind` 1 / varargs 1（`LLVM-102t`）+ clang 崩溃 2（`ISS-267 ①`，**本批未立册**）+ `siod` 1（`TESTCASES-050t ④` 转 `excluded`）；有据 = 编译/方言 6（现代 clang `-Wimplicit-int`；保留 `blocked`）+ `RUNTIME_INIT` 1（AArch64 专有）+ 参考可移植性 2（`ISS-265`，待裁定）。`TESTCASES-047t` 另记（静态 `25 blocked + 9 known-fail`、动态 `23 + 9`）⇒ **要动 5**（`ISS-254` 1 → `INFRA-089t`、`ISS-253` 1 **未立册**、`ISS-255` 2 → `QEMU-063t`、静态 `tgmath` 1 → `TESTCASES-050t ③`）/ **有据 29**（`ISS-252` 20 → `M9` + `known-fail` 9）。**无册覆盖 = `ISS-267 ①`（2 例）与 `ISS-253`（1 例）**，如实留待下一批。**`TESTCASES-050t` 后投影（2026-10-18，未跑全量）**：`048t` 的 `27 blocked + 2 fail` ⇒ 4→`pass`（`Polybench` 模板 + `SimpleMOC`/`mafft`/`nbench`）+ 2→`excluded`（`siod`/`office-ispell`）⇒ `total 220 / pass 197 / fail 2 / blocked 21 / excluded 2`（`discovered 222`）；`lemon`/`lua` 由平台崩溃终结（`ISS-269`/`ISS-266`）仍计 `blocked`，`archie-client` 仍 `blocked`（`re_comp`，`ISS-267 ⑥`）；`047t` 静态 = `pass 304 / fail 0 / known-fail 9 / blocked 24 / excluded 30`（`tgmath` 转入，全量实测）。
- **`long double` = IEEE binary128 ⇒ `M9`**（`ADR-0030` **`Accepted`**，用户 2026-10-17 逐条确认；`D1` = binary128 / `D2` = RF 双槽〔半字顺序经 `ADR-0031 D6` 修订为**高半在偶号**〕/ `D7` = 排 `M9`）；`M8` 判据**不含** `ISS-250` 的 5 例（`math/{acoshl,asinhl,erfcl,lgammal,tgammal}`），由 `M9` 覆盖 —— 执行落点 = **`LLVM-106t`**（前端/ABI/后端/builtins TF）+ **`INFRA-090t`**（musl `bits/float.h`）。
- **`LLVM-100t`（`__thread` 用户变量 TLS codegen）⇒ `M9`**（用户 2026-10-17 原话「**tls 可以推到 M9**」）；`M8` 不要求 `dlopen`/模块级 TLS。
- **线程面 `__clone`**（musl 端口无 `clone.s`）⇒ **`M9`**；`TESTCASES-047t` 静态档 20 例 `blocked` 按此归类（`ISS-252`）。
- **`INFRA-079t` = 全量** compiler-rt builtins（7 类接入点 + 独立库 + 移除 picolibc vendored 副本 + driver/`-print-libgcc-file-name` 落点）；**排期 = 先于 `M8` 收尾**（2026-10-17 用户原话「**既然要做，就做好；所以，要做，就把compiler-rt都做完，该调整任务链就调整任务链**」⇒ 撤销「只提前 `__muldc3`/`__mulsc3`」的窄化）；**生产者侧进度（2026-10-17）= 实现完成、待 L2/终局复跑**（`milestones.md` 同名行；本册 `M8` 判据/`状态` 不因此改动）。
- **其它挂账（不阻断 `M8`）**：`ISS-232`（`--show-encoding` 低半显示断言）、`ISS-235`（L3 载体 3/16 册）、`ISS-243`（i32 窄返回值 canonical 化）、`ISS-245`（静态 PIE `_DYNAMIC`）、`ISS-247`（`dadao.lds` 基址超宿主 VA）；`ISS-249` **已 `closed`**（argmask 收口）；`ISS-250`–`ISS-255`（`TESTCASES-047t` 余下失败 / `blocked` 归类）+ `ISS-256`（`ipc_sem`/`ipc_shm` 两个 codegen 缺陷 ⇒ `LLVM-101t`；`ISS-251` ⇒ `INFRA-087t`）+ `ISS-257`（`pthread_create-oom` 的 `RLIMIT_AS` 直通宿主 flake）。

- **musl 封装 `va_arg` 类型面（2026-10-18 新立 `INFRA-092t`，`ISS-271`）**：`ADR-0031` 三 bank 下，musl 变参封装把**指针实参读成整数**（`fcntl` `unsigned long`、`syscall` `syscall_arg_t`）⇒ `047t functional/fcntl` 两档 `FAIL`（`fcntl.c:27 … errno = Bad address`，日志 `.work/log/testcases/libc-test-user-{static,dynamic}.log`）+ `syscall(SYS_uname,…)` 探针 `EFAULT`；落点 = `INFRA-092t`（infra 模块，只立册）；`047t` 计数以修复后**全量复跑**为准（本笔不改任何计数）。

## 核验

- **关联任务是否均已 `已验证`**：**否** —— `LLVM-096t`–`LLVM-099t`、`INFRA-079t`、`SPEC-141t`、`TESTCASES-046t`/`047t`/`048t` 仍非终态；**2026-10-18 新立 5 册**（`LLVM-102t`/`LLVM-103t`/`QEMU-063t`/`TESTCASES-050t`/`INFRA-089t`）中 `LLVM-103t`/`TESTCASES-050t`/`INFRA-089t` = **`待验收`**（实现完成、待 reviewer），其余 2 册（`LLVM-102t`/`QEMU-063t`）仍 `待开始` ⇒ **不置 `里程碑`**。
- **`P1`/`P2`/`P3` 能力**：`QEMU-062t` 静态 + 动态两档 E2E **已通**（`已验证`）；`INFRA-085t` 交付 A1/B1/C1 + `D1` 部分（`已验证`），`D2` 推迟 `M9+`。
- **三套测试两档进度（现场）**：`TESTCASES-046t` 静态 √ 38/38 / 动态 √ 38/38（2026-10-17，`ISS-258` 处置后复跑）；`TESTCASES-047t` 静态 √ **`fail=0`**（第 4 轮 = 安装根：`pass=303 / fail=0 / known-fail=9 / blocked=25 / excluded=30`；`known-fail 9` 与 `blocked 25` 归属见上「测试面」行；第 2 轮 `301/8` 的收口链见任务书）/ 动态 √ `fail=0`（第 5 轮 = 安装根：`pass=298 / fail=0 / known-fail=8 / blocked=31 / excluded=30`；COPY 8 / `pleval` 1 见任务书第 5 轮；任务级 `状态` 本笔未改，仍 `待开始`；**2026-10-18 = `TESTCASES-049t` `-fPIC` 后动态 `305/0/9/23`（静态不变）**）；`TESTCASES-048t` **A 类 222 两档 ✅ 已跑（2026-10-18）= 两档逐数相同 `pass 193 / fail 2 / known-fail 0 / blocked 27`（pass 拆分 192 参考 + 1 exit-only）**：残 2 `fail` = 参考可移植性（`ISS-265`，待裁定）、`blocked 27` 逐条归因（`ISS-266`/`ISS-267`）；B 类 1890 未跑。
- **`P4`**：**用户 2026-10-18 裁定不作**（不做 RISC-V 交叉对比）⇒ **不再是 `M8` 阻断项**；阶段表保留该行并标「不作」，`ADR-0025 D7` 已加**就地修订注记**（只加注记、不改 `D1`–`D7` 正文）。
- **判据③ 修订后**：`M8` 的判定只看 ① 两档能编能跑 + ② 三套测试两档如实分类 + 失败逐条归因（`known-fail` 走逐例依据表）；**`P4` 不参与判定**。
- **门控**：本批跑 `make check`(L1) / `check-patch-tree` / `check-contracts-pending` / `check-contract-relocs` / `check-milestone` 并如实记录；**L2/L3 本笔未跑**（`ISS-229` 并发禁令）。
