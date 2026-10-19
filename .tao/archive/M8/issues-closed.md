# M8 阶段已关闭 Issue（2026-10-13 ~ 2026-10-19）

> **来源**：`INTEG-036m`（2026-10-19）从 `.tao/knowledge/issues.yaml` 提取——M8 期（2026-10-13 起 ~ 达成日 2026-10-19）所有 `closed` 项（`Process-04 §4.4/§7`）。
>
> **判据**：项目里程碑 **M8 = 达成（2026-10-19）** ⇒ 提取集合 = `resolved_by` 提交/关闭日 ≤ 达成日的 `closed` 项，共 **52 条**；提取后活台账仅保留 open 项（**61** 条）。
> **说明**：首条 `ISS-199` 关闭于 M8 首日（2026-10-13，服务重启复验）；其余均在 M8 期内。

| id | scope | resolved_by | title |
| --- | --- | --- | --- |
| `ISS-199` | infra | 用户复验（opencode service restart，2026-10-13） | 出界 `cd` fail-fast 在当前服务下未生效（agent frontmatter `external_directory` deny + `POST /api/location/reload` 无效）⇒ 待 `opencode service restart` 后复验 |
| `ISS-200` | infra, llvm | LLVM-092t | pre-M6 LLVM 组件 changelog 条目缺失（`013t`/`014t`/`019t`–`025t`/`028t`/`060t`；`046t` 未触碰 `patches/` ⇒ 除外）——文件创建前的历史截断，M7 范围外未补 |
| `ISS-201` | spec | SPEC-137t | 未定义弱符号决策（`ADR-0019 D9` / `contract-elf §3.3`）的实现边界分支未入规范：`R_DADAO_REL26` 落点既非 `call-iiii`(0x74) 也非 `jump-iiii`(0x70) 时实现显式报错（本批 0 例）——既有边界编码，非 `SPEC-135t` 引入 |
| `ISS-202` | infra | INFRA-071t | `contract-*.md` → `contracts/` 迁移（`INFRA-070t` Phase B）因引用冲突需用户授权——只读锁册 / `contracts/` 内容 / 范围外目录三类冲突 |
| `ISS-203` | infra, spec | INFRA-080t | 门控覆盖缺口 2 项（`SPEC-137t` reviewer 非阻断发现）：`check-spec-refs` 不覆盖 `.tao/knowledge/**` 互指；`check_issues.py` 不校验 `closed` 条目必填 `resolved_by`（本次均靠人工核） |
| `ISS-204` | infra | INFRA-083t | `.cache/embench-iot` 为 checkout（非裸仓库），与「`.cache/` 只放裸仓库」约定不符——建议后续清理/迁移 |
| `ISS-205` | llvm | LLVM-091t | `LLVM-091t` reviewer 子代理未返回最终判定（只报 13 项已核 + 等 picolibc）——任务书保持 `待验收`，处置 = 重派 reviewer 1 次 |
| `ISS-206` | spec, llvm, testcases | LLVM-094t | `DADAO.def`（lld 生产者）须随 `ADR-0019 D10` 重编号（`NONE=0` / `ABS48` 0→6 / 动态 7–13 / `NUM=14`）+ `contract-elf.md §2.2` 同步 + 排查既有 ELF 产物·向量里写死的类型字段——属 P2 必做 |
| `ISS-210` | llvm, infra | AGENTS.md「构建与注入测试的成本控制」（改 MC 后必须补跑 make install-host；本笔补落） | 【P2】改 MC（`.td` / InstrInfo）后**只重建、未 `make install-host`** ⇒ 门控 / lit 走**旧安装根** `llvm-mc`，与旧生成物**互相自洽而照绿**（假绿）；对策 = 把 `install-host` 纳入「改 MC 后」必跑步骤（纪律与/或一致性门控） |
| `ISS-211` | spec, llvm | SPEC-142t（阶段 C） | 【P3】口径记录：**MC 层不实现合法性规则**（`dst_rd0` / `encode_onehot` 等落在**契约 / 生成器**与**执行层**；`ILLI` 属**执行期**异常）——`rev.*` 非 one-hot / 越范围被 MC **静默接受**属**既有分层口径**、非本任务缺陷 |
| `ISS-212` | infra | AGENTS.md「任务收尾」（逐任务收尾·禁积压 + 分支一次性落地）+ lessons §3.21（跨分支取号唯一性） | 【P2】长期未合并的分支 × 共享 `.work/source/<组件>` 会致 `check-patch-tree` 错配红——换分支后仓库补丁表回退而源树仍停旧分支 base+1 |
| `ISS-215` | spec, llvm, infra | SPEC-143t（阶段 C） | 【P2】门控 `check-instrinfo` 的 Check 2b（每条 `scope: m8` 记录须有唯一 `.td` def）与「契约先行」的三阶段拆分**结构性冲突**——阶段 A（仅契约/编码层）**必然** L1 红 |
| `ISS-216` | qemu, infra | INFRA-082t | 【P2】`dadao-m1` 机体现**无 `SYS_UMON_SYSCALL` 服务方**——P1（`INFRA-082t`）的 syscall stub 在 QEMU 侧**无可执行路径**，须先定「谁提供 `umon` syscall 服务」口径 |
| `ISS-221` | spec, qemu, infra | QEMU-060t | 【P2】`spec/Machine-01 §4.3` 仅列两条 syscall 路由，未覆盖新增的第三条：user `trap cfx0,0` 由 QEMU 接管（`SYS_UMON_SYSCALL`） |
| `ISS-230` | llvm, spec | LLVM-095t | 【P2】`ADR-0026` 的「超 ±2 KiB 用 `ABS48` 序列 + `ldm.o_rrri_rb`」在现有 ABI 下不可实现（无链接器可用 `rd`、无宽相对重定位类型）⇒ 契约与可用通道不闭合 |
| `ISS-233` | qemu, infra | QEMU-061t | 【P3】L3 门控载体（`check-qemu-semantics`）未含 `aip-si.yaml` ⇒ `aip.si` 在 L3 门控零覆盖（`Makefile` 的 `for v in …` 硬编码两文件） |
| `ISS-239` | llvm | LLVM-096t | 【P2】DADAO clang driver **静默丢弃** bare `-shared`（`Linker::ConstructJob` 只转发 `-T/-L/-e/-u/-s/-r`）⇒ musl `lib/libc.so` 配方的 shared 链接实际产出 **ET_EXEC 且无 `.dynamic`**（仅一条 `-Wunused-command-line-argument`，无错） |
| `ISS-240` | llvm | LLVM-098t | 【P2】`-fPIC` 下 LLVM **relative lookup table** 发射 `.dd.t32 <sym>-<base>`（4 字节 PC 相对**数据**域）⇒ DADAO MC **拒绝**（无该重定位类型）⇒ `src/misc/fmtmsg.c`、`src/regex/regcomp.c` 编不过（23 处错误）⇒ 共享库构建受阻 |
| `ISS-241` | llvm | LLVM-096t | 【P2】`-shared` 链接**拒绝** `R_DADAO_ABS48` 打**局部标签**（`-fPIC` 对象 `.rodata` 里的常量指针表，如 `.rela.rodata.catopen → .L0`）⇒ `recompile with -fPIC`（而该对象**本就是 `-fPIC`**）⇒ 真实 musl 共享库链接受阻 |
| `ISS-242` | infra | INFRA-085t | 【P2】musl DADAO 移植**缺 `src/thread/dadao/syscall_cp.s`**（可取消系统调用 asm）⇒ `__syscall_cp_asm` / `__cp_begin` / `__cp_end` / `__cp_cancel` **全树无定义** ⇒ 任何拉入 `pthread_cancel.o` 的链接（**共享库必拉**）失败 |
| `ISS-243` | llvm | LLVM-107t | 【P2】i32 窄返回值**未按 ABI `C5` 做 callee canonical 化**：clang DADAO ABI 不给 i32 返回打 `zeroext`/`signext` ⇒ `RetCC_DADAO` 的 `CCPromoteToType<i64>` 落 `AExt` ⇒ `LowerReturn` 发 `ANY_EXTEND`（空操作）⇒ `unsigned addu(unsigned,unsigned)` 以 `add.uo {rd0, rd8}` 直接 `ret`，`rd8[63:32]` 为溢出位（`contract-abi.md §4.4 C5` 违约） |
| `ISS-244` | llvm | LLVM-096t | 【P2】`-fPIC` 对象 `.rodata.<fn>` 仍发 `R_DADAO_ABS48` 打**本对象局部标签**（`.L0`）⇒ lld 以 `recompile with -fPIC` 拒绝 ⇒ `make build-musl-shared` 失败（**第三类**：跳转表 / 相对查找表已由 `LLVM-096t` 处置；**根因未定**） |
| `ISS-248` | infra, testcases | ISS-248（architect 直接派修，未立任务书；证据 `.work/evidence/ISS-248/run.sh`） | 【L2】`picolibc-tests` 自 2026-10-16 19:15 起 `blocked=20`（`link error`）⇒ 代表集覆盖归零而门控仍 PASS；根因 = picolibc 构建树陈旧（旧重定位编号 0）+ `build_picolibc.py` 无工具链戳记守卫 |
| `ISS-249` | infra, qemu | argmask 表补全 12→245 + 三载体逐项一致 + 大端 `ipc_perm.mode` 补偿（2026-10-17，`TESTCASES-047t` 静态档重跑收口；门控 `make check-syscall-abi`） | 【P1】musl 端口 `__dadao_argmask` 覆盖不足（`arch/dadao/syscall_arch.h:63` 仅 12 个 syscall）⇒ 指针参数落入错误寄存器银行；`libc-test` 静态档 4 例真失败（`ipc_msg`/`ipc_sem`/`ipc_shm`/`socket`）；三载体同表（musl argmask / `syscall_cp.s` / QEMU `cpu_loop`） |
| `ISS-250` | infra | INFRA-090t | 【P2】`long double` ≡ `binary64`（`LDBL_MANT_DIG=53`）而 musl `_l` 实现按更高精度编写/取整 ⇒ `libc-test` 静态档 5 例偏 1.5–10 ulp（`math/{acoshl,asinhl,erfcl,lgammal,tgammal}`）；精度口径尚未明文写入契约 |
| `ISS-251` | infra | INFRA-087t | 【P3/语义】`strptime %s` 在 musl 实现中无效果（`src/time/strptime.c:133-139`）⇒ `libc-test` 静态档 1 例真失败；倾向按 musl 语义、改语料分类 |
| `ISS-253` | infra, llvm | LLVM-105t | 【P2】`wchar_t` 有符号性冲突：musl `typedef int wchar_t` vs clang `__WCHAR_TYPE__ = unsigned int` ⇒ `libc-test` 静态档 `mbsrtowcs-overflow` blocked（编译期类型冲突） |
| `ISS-254` | infra | INFRA-089t | 【P2】musl 端口缺 `sigsetjmp`（链接期 `undefined symbol: sigsetjmp`）⇒ `libc-test` 静态档 `setjmp` 用例 blocked（`INFRA-082t` 遗留⑧；与 `ISS-242` 同一信号帧面） |
| `ISS-256` | llvm | LLVM-101t | 【P1】两处独立 codegen/ABI 缺陷（`libc-test` 静态档 `ISS-249` 收口后余 2 例）：① 变参聚合实参两侧取法不一致（`union semun` 经 `semctl(...,IPC_STAT,arg)` ⇒ `arg.buf` 读到 0、`EFAULT`）；② `shmat()` 指针返回经 `__syscall_ret` 尾调用未落 `rb8`（`p` 为栈地址 ⇒ `shmdt` `EINVAL`） |
| `ISS-258` | infra, qemu | TESTCASES-046t | 【P1】安装根动态 `libc.so` 早于 `ISS-249` argmask 协议变更（13:49 < 17:33）且与现行 `qemu-dadao`（18:31）不匹配 ⇒ 一切动态可执行在 musl ldso 的 RELRO `mprotect` 处 `rc=127`（`TESTCASES-046t` 动态档 38/38 blocked；`047t`/`048t` 动态档同样被挡） |
| `ISS-259` | testcases | TESTCASES-049t | 【待裁定】【P3】`libc-test` 动态档 8 例非 PIC 用户可执行触发 lld COPY 重定位拒绝（+`pleval` 上游 hidden 符号）⇒ 是否把动态档用户编译改为 `-fPIC`/`-pie`（现按 `ADR-0026 D7②` 记 `blocked`） |
| `ISS-262` | infra, llvm | INFRA-088t | 【待裁定】【P3】compiler-rt builtins 的 driver 默认选择维持 opt-in（`-rtlib=compiler-rt`）与 `ADR-0027 D5`「自动接线」措辞存在解释差异 ⇒ 待用户/架构裁定 |
| `ISS-263` | infra | INFRA-086t | 【P2】`check-musl-freshness` 门控假红：toolchain stamp 含 `ctime`（inode 元数据）⇒ `install-host` 用 `cp -aL`+`rename(2)` 重拷同字节也判「toolchain changed」 |
| `ISS-264` | testcases | TESTCASES-048t | 【P3】子代理异常：`TESTCASES-048t` 第 2 步首次下发返回 `Task cancelled`（盘上零改动）⇒ 同任务原样重试一次 |
| `ISS-267` | llvm | LLVM-102t + LLVM-103t + LLVM-105t | 【P3】`llvm-test-suite` 暴露的 LLVM/DADAO 后端缺口：clang 崩溃 2（`lencod`/`obsequi`，rc=-6）+ `brind` Cannot select + varargs 未支持 + f80 `flog` libcall 缺 |
| `ISS-268` | llvm, infra | ADR-0031 | 【P2】变参 ABI 未在契约层规定：`va_list` = 单 `void*` + caller 整块保存区；聚合在变参中的分类 / 寄存器耗尽 / 16 B 半字顺序均无条款 ⇒ 归 `ADR-0031`（`Accepted`，2026-10-18；spec/契约已同步） |
| `ISS-269` | qemu | LLVM-108t | 【P3】`qemu-dadao` 上 `lemon` 的**每个 fork 子进程以 guest SIGSEGV 终止**（`first_error = Error while running on: <input>`；260 次全败、无 parser 产出）⇒ 归 qemu 面诊断（guest 故障路径 / 指令语义） |
| `ISS-271` | infra | INFRA-092t | 【P2】musl 变参封装在 ADR-0031 三 bank 下把指针实参按整数取：`fcntl`/`syscall()` 两处 ⇒ `047t functional/fcntl` 两档 EFAULT |
| `ISS-272` | llvm | TESTCASES-051t | 【P3】`LLVM-101t` 证据脚本 `asm-semctl-vaarg-direct` 检查方法有误（在汇编里查 `rd2rb`，应查 IR）⇒ 后续修正，本笔不改脚本 |
| `ISS-274` | testcases | TESTCASES-051t | 【P3】`TESTCASES-047t` 静态证据脚本 3 处 stale（`audit.py` NameError / `ADR-0030` 未认 / `ipc_msg` 期望过时）⇒ 后续维护 |
| `ISS-275` | llvm | LLVM-111t | 【P2】`LLVM-102t` D4 caller 侧两处执行期偏差：① 9–15 B 两块按「偶号起」（`D6` 只强制 16 B）；② `f128` 栈上两块连续 8 B、未做 16 B 补位（`D7` 字面要求）⇒ 待用户裁定 |
| `ISS-276` | testcases | TESTCASES-051t | 【P3】`run_llvm_ts_user.py` 的 run 目录只按 `RUN_OPTIONS` 建输出子目录 ⇒ `lencod` 缺 `Output/`（路径写在 `encoder_small.cfg`）⇒ 运行失败、产物缺失 |
| `ISS-277` | llvm | LLVM-108t | 【P3】`lemon` 的 `Configtable_clear(0)` 调用点漏写 `rb16`（null 函数指针参数）⇒ callee 读到栈地址并在取指处 `SIGSEGV`；归 LLVM DADAO 后端 |
| `ISS-279` | spec | SPEC-147t | 【P2】汇编注释符 `;`→`@@`：规范 0.5.3 已改，LLVM 实现与 99 文件语料迁移待做（`SPEC-147t`/`LLVM-109t`） |
| `ISS-280` | spec | SPEC-150t | 【P2】帧指针回归 `rb2`（无条件保留、删 `rbfp`/`rbgp` 别名）+ `rb63` 回归普通 callee-saved；setjmp 端口需加 `rb2` 槽 |
| `ISS-281` | infra | LLVM-109t | 【P1】`LLVM-109t` 注释符迁移未覆盖组件补丁里的汇编（musl/picolibc 仍用 `;`）⇒ `make build-musl` 失败、`libc.a`/`crt1.o` 清空 |
| `ISS-283` | llvm | LLVM-113t | 【P2】`build-picolibc` rc=2：`strtold.c` 的 i128→f128 `uint_to_fp` libcall 未注册（需 `__floatuntitf`）；改前亦失败，既有缺口 |
| `ISS-284` | spec | SPEC-151t | 【P1】调用点 SP 对齐 8→16 B：spec/契约/abi.yaml 仍只承诺 8 B，后端 StackAlignment=Align(8)；落点 SPEC-151t / LLVM-112t |
| `ISS-285` | infra | INFRA-094t | 【P3】L2/L3 两处红（INFRA-094t）：ir-lli 5 个 lit CodeGen 未归类 + `.work/tests/authoritative/latest` 缺失；已修，check-modules 残余红 = ISS-283 |
| `ISS-286` | testcases | LLVM-109t | 【P1】`LLVM-109t` 注释符迁移又漏 `tools/**` 的 `.s`（`picolibc_test_crt0.s` 仍用 `;`）⇒ `make check-picolibc-tests` 汇编 crt0 失败 |
| `ISS-287` | llvm | LLVM-115t | 【P2】picolibc `math_test` 链接 `undefined symbol: __atold_engine`：binary128 触发 `ld128` 引擎路径，`atold_engine.c` 仍在我方 meson 过滤表（`ISS-193` (f)） |
| `ISS-290` | testcases | ir-lli-manifest-fix | 【P2】`diff_ir_lli` 语料漂移：`LLVM-113t`/`114t` 新增 2 个 `.ll` 未入 `tests/llvm/ir-lli/manifest.yaml`（on-disk 69 > include+exclude 67） |

> **未提取**：M7 及以前的阶段关闭项见 `.tao/archive/M1..M7/issues-closed.md`。
