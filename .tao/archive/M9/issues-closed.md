# M9 阶段已关闭 Issue（2026-10-19 ~ 2026-10-24）

> **来源**：M9 收尾（2026-10-24）从 `.tao/knowledge/issues.yaml` 提取——M9 期所有 `closed` 项（`Process-04 §4.4/§7`）。
> **判据**：M9 收尾提取集合 = 全部 `closed` 项，共 **83 条**；提取后活台账仅保留 open 项。

| id | scope | resolved_by | title |
| --- | --- | --- | --- |
| ISS-058 | [qemu] | INFRA-102t | scripts/decodetree.py 输出依赖 PYTHONHASHSEED——非 bit-reproducible |
| ISS-064 | [qemu] | QEMU-073t | cpu_loop_exit 的 longjmp 泄漏 MMIO re-entrancy 守卫——engaged_in_io 未复位 |
| ISS-090 | [qemu, infra] | INFRA-103t | components/qemu/changelog.md 缺任务级记录（自 2026-09-23 起未按任务追加） |
| ISS-120 | [qemu, testcases] | TESTCASES-061t | min_rom_probe_{006t,008t,009t,010t,013t,028t}.py 群 FAIL 与 009t-audit FAIL（pre-existing 漂移） |
| ISS-125 | [testcases] | TESTCASES-061t | 生成器↔向量预存漂移（全量重跑会破坏 5 文件） |
| ISS-160 | [spec] | INFRA-103t | SPEC-106t 范围外残留：contract-isa 投影层仍列已删伪指令 + impact-matrix 悬空 + check_spec_codeblocks PSEUDO_INSTRUCTIONS 陈旧 |
| ISS-187 | [llvm] | LLVM-127t | 窄位指令利用不足（8/16/32 位算术未用；`mul32` 用 128 位双目的 `mul.uo` 而非单目的 `mul.ut`）——M7 优化候选，非缺陷 |
| ISS-188 | [llvm] | LLVM-126t | FP 完备性缺口（`fcmp` 取值 / `fabs`/`frem`/`copysign` / `fma`/`fminnum`/`fmaxnum`/`floor`/`ceil`/`round`/`trunc` / `fpclass` / `f16` / `bitcast double→i64` 缺 ISel 模式）——M7 |
| ISS-190 | [testcases, spec] | TESTCASES-061t | 生成器 ↔ 已提交向量语义漂移（`st.*` 源 = `rd0`）——既有问题，非 QEMU-056t 引入 |
| ISS-192 | [spec] | SPEC-165t | spec_cite 悬挂（24 条）：SimRISC-08/09/10 的「比较操作」/「Bit manipulating：位操作指令」标题带「 — 值语义」后缀，而 `contracts/opcodes.yaml` 的 `spec_cite` 省略该后缀——既有问题，非 SPEC-133t 引入 |
| ISS-193 |  | "LLVM-084t (a) / LLVM-086t (e) / LLVM-087t + LLVM-089t (b) / LLVM-088t (d) / LLVM-097t (c) / LLVM-115t (f) / LLVM-118t 现场重枚举并清零过滤表" | picolibc 全量构建剩余 LLVM 缺口（6 类 41 源）：SETO/SETUO/SETUNO 谓词、f32 `frint`/`flog`/`ftrunc` libcall、i64 `bswap`、截断存储 `trunc to f32`、`"r"` 约束不收指针、`long double` strtod libcall |
| ISS-197 | [llvm] | LLVM-119t | 内联汇编 `\"m\"` 约束触发后端 ISel 硬崩溃（`Could not match memory address.  Inline asm failure!` + core）——对照 `\"f\"` 为优雅失败；既有问题，非 LLVM-086t 引入 |
| ISS-208 | [spec, infra] | INFRA-103t | 【P3】`ADR-0012 D9.5` 与 `tools/spec/check_scope.py` 注释称 `total 227→228`，而实测 `contracts/opcodes.yaml` 与门控期望值均为 **227**——仅 docstring/注释算术笔误、非门控缺陷 |
| ISS-209 | [infra] | AGENTS.md「命令与任务执行纪律」+ tools/infra/check_tasks.py | 【P3】后台子代理回报可能静默丢失——主会话若以「等回报」作为停顿理由会空窗；对策 = 以盘上事实判断 + `AGENTS.md` 三条规则（队列续链 / 长任务归属 / 通知核对） |
| ISS-213 | [spec, infra] | lessons §2.17 | 【P3】证据脚本的「覆盖计数」期望值**写死**（如 `\"231/231\"`）而非现场派生——有可达 FAIL、不假绿，但既有指令集**增删**即假红；建议期望值现场取真源条目数 |
| ISS-214 | [spec, infra] | AGENTS.md「子代理硬约束」7 + 「最小安全设计·可审计」 | 【P3】写进完成区的检查项须留**原始输出**可回溯——`validate_decodetree` 等经 reviewer 独立重跑复现，但现场无留档日志 |
| ISS-217 | [testcases, infra] | lessons §1.48 | 【P3】取源类证据脚本对**直连 `github.com`**（非本任务必需的备源通道）做**硬断言**（B3–B5）⇒ 本机 TLS 受限即 **FAIL**（全量 100/103），属**环境依赖**而非交付缺陷；建议降级 `INFO`/`SKIP` |
| ISS-218 | [llvm] | lessons §2.14 | 【P3】证据脚本的 `git diff` **锚定 `HEAD`** 而非**任务基线** ⇒ 该任务**提交后**重跑时 diff 类断言退化（恒真 / 空跑），计数与完成区记录不一致（重跑 30/58 vs 记录 106/134），**影响证据可复现性**（非伪造、非假绿） |
| ISS-219 | [spec, infra] | SPEC-171t | 【P3】契约正文存在 13 条小节级悬空引用（`INFRA-080t` 新门控诊断发现，非本扫描面） |
| ISS-220 | [infra] | tools/infra/check_issues.py shebang（已补） | 【P3】`INFRA-080t` reviewer 2 条非阻断观察：① `tools/infra/check_issues.py` **无 shebang**（直接 `./check_issues.py` 失败，须 `python3` 调）；② 小节级互指标签**不识别全角括号形** `（Cn）`（当前 `.tao/knowledge/**` 面 0 命中，非现实缺口） |
| ISS-222 | [llvm] | "LLVM-118t (①③④) / LLVM-119t (②)" | 【P2】musl 静态移植暴露的 LLVM 后端缺口 4 类（`INFRA-082t` A2+A3 实测）：`%N` 无法代入 inline asm / 任何 `\"m\"` 操作数 ⇒ ISel 崩（同根因已登记 `ISS-197`）/ 缺 `rotl`·`rotr`·`bswap` 的 ISel 选择（ISA 侧 `rev`·`ctlz`/`cttz`/`ctpop` 已在）/ `dynamic_stackalloc` 缺失 |
| ISS-224 | [infra] | INFRA-105t | 【P3】`make apply-series` 对 `patchless` 组件报 `KeyError: 'patch_dir'`（rc=2；既有缺陷） |
| ISS-225 | [qemu, infra] | INFRA-102t | 【P3】`dadao-m1` 服务撤回后**无回归哨兵**：日后若有人重新引入 `SYS_UMON_SYSCALL` 类服务，现有 L1 门控**无形态断言**可查 |
| ISS-226 | [infra] | lessons §2.36 | 【P3】证据脚本的白名单/判据曾为适配新产物而放宽（「凑绿」）——规范 = 改产物满足断言，**不得**改断言/白名单去适配产物（本次已还原） |
| ISS-227 | [infra] | lessons §2.35/§2.30 | 【P2】子代理报告不实（假绿）：报告称「证据脚本 rc=0、52 PASS / 0 FAIL」，主会话实跑得 rc=1、49 PASS / 3 FAIL（FAIL 恰为其声称已修的两处 ABI 名） |
| ISS-229 | [infra] | INFRA-099t | 【P3】`L2`/`L3` 并发运行会因共享安装根（`install-host`）竞争产生假 FAIL |
| ISS-231 | [infra] | INFRA-105t | 【P2】`tools/infra/apply_series.py` 未处理 `patchless` 组件 ⇒ 对 `chipyard` 报 `KeyError: 'patch_dir'`，`make apply-series` 中断（其后 `musl` 的补丁集不再被应用） |
| ISS-234 | [qemu, testcases] | TESTCASES-061t | 【P3】`tools/qemu/min_rom_probe_009t.py` 顶注 / 公式仍按已废止口径（称 `0x5A`=UNDI、`PC & ~0xFFF`）+ `tools/testcases/009t-audit.py` 对 `aip.si` 无 oracle（两件均非门控） |
| ISS-235 | [qemu, infra] | INFRA-097t | 【P3】L3 语义门控 `check-qemu-semantics` 的载体 **≠** 「全量」：现列 **3/16** 册（`Makefile:881` 硬编码三文件），其余 **13** 册在任何 L1/L2/L3 门控内**零执行**；而注释 / docstring 仍称「**全量**留在 L3」⇒ 覆盖声明与载体脱钩 |
| ISS-236 | [qemu, infra] | INFRA-097t | 【P3】`check-qemu-semantics` **默认档日志仅 3 行摘要**（非 verbose）⇒ 无法从门控日志直接证明某向量的**覆盖 / 命中**；本轮取证被迫用 verbose 镜像 + 定点注入替代 |
| ISS-237 | [qemu] | TESTCASES-062t | 【P3】`QEMU-061t` 证据脚本 `smoke_derive.py` 的 L2 派生逻辑**已过时**（`GATE_VECTORS` 已含 `aip-si.yaml` ⇒ 再「追加 aip 文件」无增量 ⇒ 断言 `k[0]==\"aip-si.yaml\"` 永不命中、脚本 rc=1）——**脚本 stale，非功能缺陷**（真 L2 门控 90/90 且 `aip.si present: True`） |
| ISS-238 | [spec] | TESTCASES-062t | 【P3】`SPEC-145t` 任务级证据脚本 `.work/evidence/SPEC-145t/run.sh` 因 `rela`→`aip` 改名后有 **14 项 stale 断言**（脚本自报 `14 CHECK(S) FAILED` rc=1；现场 `grep -c '^FAIL'` = **15** 行）⇒ 历史留证**不追改**、登记即可 |
| ISS-245 | [infra] | LLVM-120t | 【P2/P3 边界】静态 PIE（`crt/rcrt1.c` ⇒ `dlstart.c` 的 `START` 分支）的 `_DYNAMIC` 仍是**链接期绝对地址**（`rcrt1.o` 的 `.rela.text` 3×`R_DADAO_ABS48 _DYNAMIC`）⇒ 装载基址 ≠ 链接地址时自举取错；`-static-pie` 未纳入 P2/P3 |
| ISS-246 | [llvm] | LLVM-100t + LLVM-117t | 【P2】`__thread` 用户变量不可用：clang `TLSSupported=false` + 后端无 `GlobalTLSAddress` lowering ⇒ 影响 `libc-test` TLS 用例与部分程序（**不阻塞 `P3`**） |
| ISS-252 | [infra, qemu] | M9 终局复跑（2026-10-24） | 【M9】musl 端口无 `clone.s`（`src/thread/clone.c` 返回 `-ENOSYS`）⇒ 线程 / `posix_spawn` / `popen` 全不可用；`libc-test` 静态档 20 例 blocked |
| ISS-260 | [testcases] | LLVM-117t | 【待裁定】【P3】`dlopen` 4 例收编 `M9`（与 `LLVM-100t` TLS 同批）⇒ 动态档 `excluded` 的范围裁定待确认 |
| ISS-261 |  | INFRA-098t | 【P3】安装根 `cross-toolchain/bin/` 未装 `llvm-nm`（`ADR-0016 D11` 安装集不含该工具）⇒ 符号侧取证须另建构建树工具或借宿主 binutils |
| ISS-265 |  | TESTCASES-048t + 用户裁定 2026-10-18（known-fail） | 【P3】`llvm-test-suite` 两例 `fail` 归因参考输出不可移植（`Ptrdist/ft`：musl 的 `srandom` 播种与 glibc/BSD 不同；`ClamAV`：stdout/stderr 交错）⇒ 是否扩展 `known-fail` 类别待裁定 |
| ISS-270 |  | TESTCASES-053t | 【P3】`run_libc_test_user_suite.py` 的 `CASE_NOTES["functional/setjmp"]` 仍是旧根因（sigsetjmp not implemented）⇒ `INFRA-089t` 转 `pass` 后仍照旧打印 |
| ISS-273 |  | TESTCASES-053t | 【P3】`LLVM-098t` 证据脚本 XFAIL 断言过时（`make lib/libc.so` 已 rc=0）+ 静态基线未刷新 ⇒ 后续脚本维护 |
| ISS-278 |  | INFRA-093t | 【P1】测试运行产物 / 日志无组织：`.work/log` 7000+ 文件混放、固定名被 `--filter` 子集覆盖（已 2 次）⇒ 立 `INFRA-093t` 规矩 + L1 门控 |
| ISS-282 |  | TESTCASES-062t | 【P3】`INFRA-093t` 验收遗留（reviewer 第 1 轮）：子集跑写 `authoritative/` 无强制 / A2 不校验 `meta.finished_utc` / `llvm-ts-user-*` 过渡豁免待删 |
| ISS-288 |  | TESTCASES-053t | 【P3】LLVM-111t 证据脚本 P3 byte-identical 基线因 LLVM-112t 的 `Align(16)` 合法变更失效（stale 证据，非交付缺陷） |
| ISS-289 |  | 现场核实无残留链进程（2026-10-19）+ AGENTS.md「长任务」/lessons §3.10 | 【P3】前次 reviewer 会话遗留后台链（`/tmp/opencode/review-g1b/chainBC.sh`）持续修改共享构建树与源码工作树（进程纪律） |
| ISS-290 | [testcases] | ir-lli-manifest-fix | 【P2】`diff_ir_lli` 语料漂移：`LLVM-113t`/`114t` 新增 2 个 `.ll` 未入 `tests/llvm/ir-lli/manifest.yaml`（on-disk 69 > include+exclude 67） |
| ISS-291 |  | LLVM-116t 与 QEMU-064t（编码/执行面）；规范面 = SPEC-152t（契约与四表已复核 0 不符，仅证据脚本待返工） | 【P2】ISA 编码再分配（`ext` 迁 `100/101`、`shl` 迁 `010/011` 并去 `u`）+ 新增 `ror.{o,t,w,b}` ⇒ `spec/` 授权待逐条确认 |
| ISS-292 | [infra] | M9 终局复跑（2026-10-24） | 【M9】thread 支持链 T1–T5：musl `__clone`/TP、qemu-user 线程语义、静态/动态 TLS + `dlopen` |
| ISS-293 | [qemu] | INFRA-096t | 【P3】编码变更后旧 ELF 不兼容：新 `qemu-dadao` 对旧编译产物报 SIGILL（`functional/snprintf` 静态 / `functional/strtod` 动态） |
| ISS-294 | [spec] | INFRA-100t + TESTCASES-056t | 【P1】ISA 缺原子原语 ⇒ musl `a_cas` 退化为 load/compare/store ⇒ 多线程互斥丢更新（阻塞 M9 线程链 T3/T4） |
| ISS-295 | [infra, qemu] | INFRA-095t-rework | 【P1】musl 端口 `__clone` 无条件把变参 `tls` 写进子侧 `rb3` ⇒ `posix_spawn` 的 vfork 子进程 TP 为垃圾 ⇒ `__execvpe` 里写 `errno` 即 SIGSEGV（`functional/spawn` 两档、动态 `functional/popen`） |
| ISS-296 | [qemu] | QEMU-066t | 【P2】qemu-user `FUTEX_LOCK_PI` 对 guest 线程返回 `ESRCH`（owner TID 未做 guest↔host 翻译）⇒ PI 互斥的 EDEADLK 语义失效，`functional/pthread_mutex_pi` 报 deadlock |
| ISS-297 | [qemu] | QEMU-066t | 【P3】qemu-user 对 `set_robust_list`/`get_robust_list` 恒返回 `TARGET_ENOSYS`（上游设计）⇒ musl robust mutex 不可用；`functional/pthread_robust` 60 s 超时、`regression/pthread-robust-detach` 报 EOWNERDEAD≠ETIMEDOUT |
| ISS-298 | [infra, qemu, spec] | QEMU-066t | 【P2】阻塞在 futex 的线程收到 SIGCANCEL 后系统调用被重启、取消丢失 ⇒ `regression/pthread_cond_wait-cancel_ignored` 线程正常退出（rv=0） |
| ISS-299 | [testcases] | TESTCASES-052t-rerun | 【P2】libc-test 驱动 `attribute_port_gaps()` 仍按 T1 前口径把**任何** `uses_thread` 的失败降级为 `blocked` 并写「musl port has no __clone」⇒ 掩盖真实根因（`__clone` 已落地） |
| ISS-300 | [infra, qemu] | INFRA-103t | 【P3】安装根新鲜度：`make install-host` 之外的二进制替换（手工 `cp`）属例外手法，应尽量走 `install-host` |
| ISS-301 | [infra] | INFRA-098t | 【P2】`build-builtins` 的 re-stage 路径与 `check-builtins-freshness` 读取路径不一致（`Makefile:415` vs `383/384`）⇒ 重建后门控必红、须手工 `cp`；另 builtins 归档跨构建非字节确定 |
| ISS-306 | [testcases] | "用户裁定：两例均跳过（2026-10-20/21）" | 【P3】ansibench `hint` 固定工作量在 qemu 下极慢（900 s = 142/200、300 s = 131/200 采样，均未跑满 `NSAMP=200`） |
| ISS-307 | [spec, llvm, qemu, infra] | LLVM-121t + QEMU-067t + INFRA-100t + TESTCASES-056t | 【P1】原子指令实现待落（`fence` + `lr/sc` 24 条）：ADR-0034 已定编码/命名且生成面已落，`scope` 仍 excluded ⇒ 执行 ILLI；实现分 4 册（LLVM 后端 / QEMU 语义 / musl 真原子 / 集成验证） |
| ISS-308 | [testcases, qemu] | INFRA-103t | 【P3】`0x77000000` 字面残留（该编码现归 `lr.o.nn`、已非 `fence`）：`build_test_binary.py` / 6 个 `min_rom_probe_*t.py` / `ADR-0004` 的文案与注释待逐处订正 |
| ISS-309 | [testcases] | TESTCASES-061t | 【P2】测试 harness `build_exit_section` 的 `br.nz` 偏移按 `PC+4` 计（本 ISA 是 `PC + imm*4`）⇒ 用例失败时落到 semihosting trap（宿主 SIGABRT / -6），而非干净 `exit 1` |
| ISS-310 | [llvm] | LLVM-127t | 【P2】clang DADAO 的 `int` 实参未按 `contract-abi §4.2` 符号扩展为 canonical 64 位（生成 `set.zw`+`or.w` 零扩展） |
| ISS-311 | [infra] | INFRA-103t | 【P3】`components/musl/README.md`「原子」段已过期（仍称机器无可用原子、`__clone` 返回 `-ENOSYS`） |
| ISS-312 | [llvm] | LLVM-121t | 【P1】`LowerATOMIC_STORE` 取错操作数 ⇒ 共享对象的 `atomic_store`/`__atomic_store_n` 写入对象地址而非值 |
| ISS-313 | [llvm] | LLVM-121t | 【P2】子字宽（1/2/4 B）CAS 在比较值最高位置 1 时恒失败（`lr.*` 零扩展 vs 提升 i64 符号扩展，`br.ne` 比 64 位） |
| ISS-314 | [spec] | SPEC-154t | 【P2】SimRISC 版本快照缺失（≤0.4.1 仅存 0.4.1 + 0.5.0/0.5.1/0.5.2/0.5.4/0.5.5-rc 全部缺档）待补，见 `SPEC-154t` |
| ISS-315 | [spec, infra] | SPEC-165t | 【P3】`contracts/opcodes.yaml` 25 条 `spec_cite` 仍指迁册前的 `SimRISC-11 §fence指令`/`§LR-SC指令`，需批量改指 `SimRISC-11 §fence指令`/`§LR-SC指令` |
| ISS-316 | [testcases, spec] | SPEC-165t | 【P3】`tests/**` 162 处引用仍指 `SimRISC-12` 的原子章（`§3.1`/`§3.2`/`§fence指令`/`§LR-SC指令`），需改指 `SimRISC-11 §6` |
| ISS-317 | [llvm, qemu, testcases] | QEMU-068t | 【P2】`clmul.o` 已定编码（`ADR-0035`），**实现待落**（LLVM 选择/`ISel`、qemu 语义、L3 向量） |
| ISS-318 | [spec] | INFRA-103t | 【P3】FP 异常语义措辞缺口：`UF` 未写「tiny 且 inexact」、tininess 检测点未声明、标志 sticky 未明示（`SimRISC-07`/`SimRISC-00`） |
| ISS-319 | [testcases] | TESTCASES-061t | 【P3】harness 超时路径打印 `Unknown exit code: 0x-6`（负数 `%x` 格式化），诊断信息不可读 |
| ISS-320 | [infra, llvm] | INFRA-102t | 【P2】`check-instrinfo`（`validate_instrinfo.py`）不覆盖 FP 的 `.td`（`DADAOInstrInfoFP.td`），FP 记录的 def 缺失/残留无法被机械发现 |
| ISS-321 | [infra, qemu] | INFRA-102t | 【P3】`check_qemu_trans --strict` 只查「记录缺 trans」，不查「trans 残留（orphan）」 |
| ISS-322 | [qemu, spec] | QEMU-072t | 【P2】`ftrnd`/`fornd` 已立册（`scope: excluded`），QEMU 缺 2 条 `trans_*`：`check_qemu_trans` 258/260、`check_interface` 交叉核对红 |
| ISS-323 | [testcases] | TESTCASES-061t | 【P3】`run_rnd_probe.py` 静态不可感性检查重复计数（`seen` 在 `for fmt` 内重置）⇒ 805 含 20 条重复；完成区「10 组 RESTORE」实测为 27 组 |
| ISS-324 | [qemu, spec] | QEMU-071t | 【P3】`ftmin`/`ftmax`/`fomin`/`fomax` 已立编码但缺 QEMU trans ⇒ `check_qemu_trans --strict` 260/264（预期红，`QEMU-071t` 关闭） |
| ISS-325 | [spec, infra] | INFRA-102t | 【P3】`check_tables.py` 只覆盖 4 张 MISC 子表（octa/tetra/wyde/byte），OPC-RF（`op 0x44`）编码表格位无机械门控 |
| ISS-326 | [llvm, testcases] | TESTCASES-061t | 【P3】`tests/llvm/ir-lli/manifest.yaml` 11 个未分类 `*.ll` + 1 个悬空项 |
| ISS-327 | [llvm, infra] | INFRA-102t | 【P3】`gen_isa_coverage.py` 的 `L2_isel` 漏认：`ret`/`rol.o`/`clmul.o`/`add.uo`/`io2fo` 家族实际在用却记 `no` ⇒ 假「未用」报告 |
| ISS-328 | [spec, qemu, llvm] | SPEC-164t | 【P2】`fence` + 24 条 `lr/sc` 已由 QEMU 实现且 LLVM 发射，但 `opcodes.yaml` 仍 `scope: excluded` + `decode: ILLI`（25 条账面落后于实现） |
| ISS-329 | [spec, infra] | INFRA-103t | 【P3】`contract-isa.md §6.6` 仍列已删除伪指令 `not.o`/`neg.o`（与 `ADR-0013 D11` 及 `Toolchain-01 §6.2` 不一致） |
| ISS-330 | [qemu, spec] | QEMU-070t | 【P3】`ftfma`/`fofma` 已立编码但缺 QEMU trans ⇒ `check_qemu_trans --strict` 264/266（预期红，`QEMU-070t` 关闭） |
| ISS-331 | [spec, infra] | SPEC-171t | 【P3】`rrrr` 的「单目的 + 三源」书写形态未进 `Toolchain-01 §6` 格式表，且 `check_asm_prose` R6 假设 `rrrr` 必带 `{}` ⇒ 该形态无字面量门控 |
| ISS-332 | [infra, llvm, testcases] | INFRA-104t | 【P2】libc-test `math/yn` 由 0 fail 变为 3 ulp fail（疑 `LLVM-123t` 启用 FMA 收缩；musl 构建缺 `-ffp-contract=off`） |
