# 项目里程碑

> **项目里程碑 = M11**（当前里程碑；`check-milestone` 取 `项目里程碑 = M<n>` 断言的**最大 n**，本行是唯一断言；只在里程碑切换时改）
>
> 只维护任务流水；历史任务见 `.tao/archive/`，当前讨论/规划见 `.tao/knowledge/discussing.md`。
>
> **M9 归档指针（2026-11-01）**：M9 任务书 **68** 册 + 根级核验册 `INTEG-037m` 与 M9 期关闭 issue **83** 条已冻结到 `.tao/archive/M9/`（`README.md` / `m9-retrospective.md` / `issues-closed.md`）；流水 **69** 行已冻结到 `.tao/archive/M9/README.md §2`，本页不再保留 M9 行。
>
> **M10 归档指针（2026-11-01）**：M10 任务书 **71** 册（含核验册 `INTEG-052m`）与 M10 期关闭 issue **17** 条已冻结到 `.tao/archive/M10/`（`README.md` / `m10-retrospective.md` / `issues-closed.md`）；流水 **70** 行已冻结到 `.tao/archive/M10/README.md §2`，本页仅留 M10 后维护行（`check-milestones-fresh` A1/A2 对归档册同样生效，已归档号豁免回填）。

## 任务流水

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| INFRA-133t | 待验收 | 2026-11-08 02:15（登记） | 节点 chipyard/Verilator/RISC-V 环境；两台 RocketConfig 构建通过、conda 包一致 |
| INFRA-132t | 已验证 | 2026-11-07 22:23 | 节点 `.cache` 增量同步（rsync，无 --delete）+ 逐 commit 校验；不做挂载 |
| INFRA-131t | 已验证 | 2026-11-07 21:35 | remote.py 假绿根除（cd 失败即非零）+ `~/` 展开 + git 失败不再报假状态 |
| INFRA-130t | 已验证 | 2026-11-07 21:11 | 节点引导 bootstrap_node.sh（8 步幂等）+ 远程派单 remote.py（status/preflight/run/collect） |
| INFRA-129t | 已验证 | 2026-11-07 20:28 | 清理运行期证据引用 23 处；空转判据按 found==0（用户裁定 A） |
| GEM5-029t | 已验证 | 2026-11-07 17:03 | SE syscall 语义对齐 7 项；436/146、6/0 不变；QEMU SS_AUTODISARM 补丁 |
| GEM5-026t | 已验证 | 2026-11-07 12:40 | gem5 SE 线程/futex/TLS；pass 435/blocked 147，threads 桶清零 |
| GEM5-030t | 待开始 | 2026-11-07 08:40（登记） | SE mprotect 真权限 + RLIMIT_AS/STACK 强制；高回归风险 |
| INTEG-060t | 待开始 | 2026-11-07 08:20（登记） | gem5 SE syscall 参数 bank（三方 argmask 门控）+ 路径解析探针 |
| GEM5-025t | 已验证 | 2026-11-07 07:50 | gem5 SE IPC/多进程；pass 418/blocked 164，两桶清零；5 例环境缺口 |
| GEM5-024t | 已验证 | 2026-11-07 03:13 | gem5 SE 信号+资源限制+进程信息；pass 409/blocked 178，三桶清零 |
| GEM5-023t | 已验证 | 2026-11-06 23:47 | gem5 SE 文件 I/O + 时钟；pass 399/blocked 188，两桶清零 |
| GEM5-028t | 待开始 | 2026-11-06 21:15（登记） | gem5 SE 文件映射 mmap + ldso 装载；解释器窗口约束 |
| TESTCASES-104t | 待开始 | 2026-11-06 21:15（登记） | SE 动态档驱动 + QEMU dynamic 基线刷新 + 全量对照 |
| GEM5-027t | 待开始 | 2026-11-06 20:30（登记） | gem5 SE 动态装载器：ET_EXEC+PT_INTERP/auxv/interp-dir+redirect |
| INTEG-059t | 待开始 | 2026-11-06 20:30（登记） | G3 完整 tset 双向一致性（static+dynamic）+ 矩阵重生成 |
| TESTCASES-103t | 待开始 | 2026-11-06 20:30（登记） | SE 基线预算 120s→按套件 600s；timeout 单列并重跑 |
| INTEG-058t | 已验证 | 2026-11-06 20:00 | 转换舍入编码迁移：LLVM/QEMU/gem5/tests；9 math+pi 转绿、parity 269/0 |
| TESTCASES-102t | 已验证 | 2026-11-06 17:40 | timing 探针去 icount：20 例轮询/窗口断言；node/arch 269/269 blocked 0 |
| SPEC-194t | 已验证 | 2026-11-06 16:10 | 转换指令舍入编码三分（ADR-0050）：15 六档 / 3 SBZ / 4 计数 |
| GEM5-022t | 已验证 | 2026-11-06 15:55 | gem5 SE heap/VMA：brk+mmap+munmap+mremap；blocked 270→217 |
| GEM5-021t | 已验证 | 2026-11-06 13:28 | gem5 SE tset 基线调查：qemu 587/gem5 310/blocked 270/9 f2i |
| INFRA-127t | 已验证 | 2026-11-06 10:55 | 夜跑独立化：night-run（无别名）+ night.lock 独立锁 + meta 机器信息 |
| INFRA-126t | 已验证 | 2026-11-06 10:11 | 夜跑退出里程碑收口门控：check-milestone 去 night-report 依赖 |
| TESTCASES-101t | 已验证 | 2026-11-06 09:55 | malloc-brk-fail 改 cur=0/max=inf；宿主与目标两侧 PASS |
| QEMU-084t | 已验证 | 2026-11-06 09:02 | QEMU user-mode guest rlimit 记账：AS/DATA/STACK；39 条断言入库；ISS-343 关闭 |
| INTEG-057t | 已验证 | 2026-11-06 07:30 | 其余生成器 notes/折行对齐；check-generator-sync 6/6 绿 |
| INTEG-056t | 已验证 | 2026-11-06 03:40 | ctrl-jump/call/ret 生成器 notes 对齐，3 册 byte-identical |
| INTEG-055t | 已验证 | 2026-11-06 03:10 | 退出码三段式实现迁移 + 页表异常改投当前 monitor；parity 249/0 |
| INFRA-125t | 已验证 | 2026-11-05 23:45 | embench/libc-test 迁入 tests/tset；manifest/门控同步 |
| INFRA-124t | 已验证 | 2026-11-05 23:31 | ADR-0013/check_spec_refs/GEM5-017t/Node embench 小残留清理 |
| INTEG-054t | 已验证 | 2026-11-05 23:08 | 5 个屏蔽寄存器实现清理：QEMU/gem5/tests；parity 249/0 |
| INFRA-123t | 已验证 | 2026-11-05 21:15 | DDLN TT 退役：81→0、DD 81；lecnotes agent 删除 |
| SPEC-191t | 已验证 | 2026-11-05 21:08 | ADR-0004/0009/0041 + DDLN/Machine-00 旧码清理；D3/D5 三段式 |
| SPEC-193t | 已验证 | 2026-11-05 20:23 | spec/README 外部指针修复：5 处悬空清零；L1 绿 |
| SPEC-192t | 已验证 | 2026-11-05 20:22 | 退出码表迁 §7.1；同步 contract-see/ADR-0020/ADR-0004 指针 |
| SPEC-185t | 已验证 | 2026-11-05 19:40 | spec 非 spec 引用清理：223→0，保留 spec 互引；README 治理节恢复 |
| TESTCASES-098t | 已验证 | 2026-11-05 19:08 | M11 矩阵重生成：node/arch 249 AGREE、0 fail；14 条红转绿 |
| GEM5-020t | 已验证 | 2026-11-05 18:20 | gem5 CFXREG 目标对齐当前 monitor；node/arch 249 AGREE、14 红转绿 |
| SPEC-187t | 已验证 | 2026-11-05 15:29 | 退出码迁移 SPEC：Machine-v5 三段表、ADR 指针化、ISS-341 |
| SPEC-190t | 已验证 | 2026-11-05 14:55 | DADAO-23 §3 与 DDLN 旧 mask 引用清理；TT 已同步主树 |
| TESTCASES-100t | 已验证 | 2026-11-05 14:54 | libc-test malloc-brk-fail 64K 页修正；夜跑 4/4 绿、night-report 绿 |
| QEMU-083t | 已验证 | 2026-11-05 14:52 | CFXREG 目标改当前 monitor；10 处 helper、复现 exit=0x53 |
| SPEC-189t | 已验证 | 2026-11-05 13:45 | DADAO-12/22/Machine-v5/contract-see 页表异常原因表同步为当前 monitor 的 CFXMEM/CFXPERM |
| SPEC-188t | 已验证 | 2026-11-05 12:25 | 删除 5 个无效屏蔽寄存器定义（rc9/rc11/cg5 rc1/cg5 rc63/inner），reserved 不重排 |
| SPEC-186t | 已验证 | 2026-11-05 12:15 | DADAO-12 §5.2 重写：A/A1 monitor 入口、7 步、异步 pending、删除 cause mask |
| TESTCASES-099t | 已验证 | 2026-11-05 12:02 | libc-test dynamic malloc-brk-fail 诊断：musl 启动堆，非 QEMU 直接缺陷 |
| TESTCASES-097t | 已验证 | 2026-11-05 10:31 | smon/hmon 页表同步 D10：4 超页、HSJU=0xC、低地址 VA |
| INFRA-122t | 已验证 | 2026-11-05 10:30 | build_gem5.py ccache 单 argv 缺陷：包装脚本接入，原生 build-gem5 rc=0 |
| SPEC-184t | 已验证 | 2026-11-05 08:04 | spec §6 Node D10 收口（ISS-340）：VA/PA 0–2 GiB 4 超页、smon 建表、合约投影、锁 sha |
| INTEG-053t | 已验证 | 2026-11-05 07:44 | cfxha 重编号 pmem32/llc33/time34；作用域 per-task 16–31、per-system 32–63；保留集 6–14/16–31/35–61 |
| INFRA-121t | 已验证 | 2026-11-05 01:26 | 运行期日志命名清理：check-run-artifacts 7 条既有红 |
| GEM5-019t | 已验证 | 2026-11-05 01:00 | SYS_ELAPSED 与 SYS_TICKFREQ 统一 1e9 ticks/s；64 位无溢出换算、046t/parity 零退化 |
| INFRA-120t | 已验证 | 2026-11-04 23:00 | 任务书运行期路径清零：清 42 册具体运行期路径、AGENTS 固化规则 |
| INFRA-119t | 已验证 | 2026-11-04 22:18 | LLVM/QEMU 构建入口接 ccache：CMake launcher + configure CC/CXX，全局默认缓存 |
| TESTCASES-096t | 已验证 | 2026-11-04 20:15 | parity 清理 7 条 GEM5-018t 已修复的 KNOWN_GEM5_BLOCKED；node/arch rejudge 全绿、stale 0 |
| TESTCASES-090t | 已验证 | 2026-11-04 16:56 | scaleB/sc 测试；LLVM lit/isa matrix 已同步；QEMU/gem5 tiny+node 52/52 AGREE_PASS，F2 复跑通过 |
| GEM5-018t | 已验证 | 2026-11-04 16:49 | FS semihosting 修复：WRITEC/WRITE0 rd8=0xdeadbeef、SYS_TICKFREQ=1e9；046t 32/32、node/arch 7 条转 AGREE_PASS |
| GEM5-017t | 已验证 | 2026-11-04 13:05 | FS parity：2658 行、AGREE 2301、DIFF/GEM5_ONLY/QEMU_ONLY 0；7 条 semihosting 待 018 |
| GEM5-016t | 已验证 | 2026-11-04 05:35 | FS Machine-v5-Node：4 MiB ROM/2 GiB RAM、hmon/PTW/hypv、inst 968/963、embench 38/38 |
| GEM5-015t | 已验证 | 2026-11-04 00:05 | FS Machine-v5-Tiny：64 KiB ROM/8 MiB SRAM、inst 1003/1003、embench 38/38、semihosting；picolibc math_test 既有 B7 blocked |
| TESTCASES-095t | 已验证 | 2026-11-03 19:00 | lit mcmodel/12 透传 + codegen 19 + ir-lli 20 收口；QEMU 无缺陷 |
| QEMU-082t | 已验证 | 2026-11-03 18:30 | cfx_power 描述符按 profile：Node 4 MiB、Tiny 不可达、legacy 退役 |
| TESTCASES-094t | 已验证 | 2026-11-03 15:10 | L3 异步/boot-chain：050/051/046/046t 全绿、async 6/6；space_power 描述符另立 QEMU |
| TESTCASES-093t | 已验证 | 2026-11-03 14:30 | L3 探针 F4/prelude + 9 册 167 例；残余 049/050/051/046 拆 094 |
| TESTCASES-092t | 已验证 | 2026-11-03 11:20 | Tiny/Node 执行资产 P0–P5：inst 968+44、arch 10/10、token/profile/hmon；P6 13 探针拆 093 |
| QEMU-080t | 已验证 | 2026-11-03 08:55 | Machine-v5-Node 系统机：4 MiB BootROM + 2 GiB RAM、hmon/PTW/hypv、identity 4×512 MiB 超页 |
| GEM5-014t | 已验证 | 2026-11-03 06:55 | G1 SE 平台骨架：SEWorkload/Process/MMU、AtomicSimpleCPU、静态 ELF/栈/MemRAS、最小 libc syscall 面 |
| QEMU-079t | 已验证 | 2026-11-03 05:00 | Machine-v5-Tiny 系统机：64 KiB BootROM + 8 MiB SRAM、无 cfx/PTW/user、raw/ELF 与 semihosting |
| QEMU-081t | 已验证 | 2026-11-03 04:20 | QEMU user 页大小 12→16（64 KiB）：缺陷修正 + 4 KiB 假设审计 + 用户态/系统态回归 |
| SPEC-183t | 已验证 | 2026-11-03 00:04 | Machine-v5 Tiny/Node 规范收口：两 profile 几何 + DADAO-12 BootROM ≥64 KiB + ADR-0004/0039/0040/0043 修订 + 只读锁 |
| TESTCASES-091t | 已验证 | 2026-11-03 00:01 | Machine-v5 Tiny/Node 测试资产迁移、minimal_crt0 BSS、dadao-tiny/node、picolibc A、m5 CFXPERM；静态门控全绿，真实执行留 QEMU |
| GEM5-013t | 已验证 | 2026-11-02 21:03 | B7 后全 ISA 收敛门控：264 条统一 dispatcher 可达 + NotBx 边界矩阵 + 矩阵旧注刷新 |
| GEM5-012t | 已验证 | 2026-11-02 19:15 | B7 FP 执行核心 55 条：12 族 IEEE754（fma/rem/sclb/f2i/compare/minmax/roundint）+ 独立 oracle |
| GEM5-011t | 已验证 | 2026-11-02 16:55 | B6 系统/原子/屏障 30 条：swym/trap/escape/cfx2rd/cfx2rc/fence/lr/sc + 单槽保留标记与 CFXREG/CFXESC |
| SPEC-182t | 已验证 | 2026-11-02 15:58 | F1 收口：12 条 lr.* 的 hb(rdHB)≠rd0 ⇒ ILLI 写入契约/生成器；编码不变 |
| GEM5-010t | 已验证 | 2026-11-02 15:11 | B5 块搬移/条件赋值/控制流与 RAS：28 条（rd/ra/rb/rf 块复制、cs.*、br/jump/call/ret、RegRAS+MemRAS） |
| GEM5-009t | 已验证 | 2026-11-02 14:00 | B4 窄位宽执行：32/16/8 位算术/比较/移位 + rev.t/w/b 共 63 条 |
| GEM5-008t | 已验证 | 2026-11-02 13:13 | B3 64 位运算执行：42 条（128 位加减乘/clmul、逻辑移位、ext/rev、位扫描、除余定值、RB 运算） |
| GEM5-007t | 已验证 | 2026-11-02 12:26 | B2 16 位立即数执行：8 条 rwii（or.w/andn.w/set.zw/set.ow/set.w），含 wyde 选择与 rf0 FCSR 掩码 |
| GEM5-006t | 已验证 | 2026-11-02 11:52 | B1 取数存数执行核心：38 条 load/store + ldm/stm 语义与定向断言 |
| QEMU-078t | 已验证 | 2026-11-02 10:56 | scaleB C1 第三源 rdHD + sc rdHB=rd0 静态 ILLI；QEMU trans/helper |
| LLVM-142t | 已验证 | 2026-11-02 10:55 | scaleB C1（第三源 rf→rd）+ sc rd0 汇编期 ILLI；LLVM TD/MC/CodeGen |
| GEM5-005t | 已验证 | 2026-11-02 10:54 | scaleB C1 第三源 rf→rd + sc rd0 的 gem5 decode/断言更新 |
| SPEC-181t | 已验证 | 2026-11-02 10:53 | gem5 语义契约收口：ADR-0044 Accepted、FP remainder/scaleB/f2i、call IP+4、sc rd0、保留粒度 |
| GEM5-004t | 已验证 | 2026-11-01 23:40 | B0 解码核心 + 264 条解码断言（388 反例）；gem5 骨架可构建，B1–B7 留边界 |
| GEM5-002t | 已验证 | 2026-11-01 22:28 | M11 指令语义重导矩阵：逐条对照当前 spec 与 0628/PR，禁止同助记符默认复用 |
| GEM5-003t | 已验证 | 2026-11-01 22:02 | gem5 锁定 v25.1.0.1 / c8222cc6；组件暂 disabled，G1 建骨架后启用 |
| GEM5-001k | 已验证 | 2026-11-01 21:42 | M11 启动：gem5 FS/SE 差距矩阵、测试复用与任务拆分 |
| INFRA-113t | 已验证 | 2026-11-01 15:31 | M10 后清理：退役失效 M1 门控判据（check_issues/Process-04）+ 清 ADR-0030/M9 过时 known-fail 基准 |
| INFRA-118t | 已验证 | 2026-11-01 15:04 | M9/M10 根级 INTEG m 册迁入 integ，归档根仅三件套 + 模块任务书 |
| INFRA-117t | 已验证 | 2026-11-01 14:33 | M1–M10 归档归一：M9/M10 流水冻结、M6/M2 状态、M7 notes 并入回顾 |
| INFRA-116t | 已验证 | 2026-11-01 14:06 | Process-04 归档规则修订（m 可选/流水落 README/三文件）+ check-archive 门控 |
| INFRA-115t | 已验证 | 2026-11-01 13:02 | tests/inst 计数 152→156、生成器 `--check` 措辞列名化、anti_forgery 迁 tests/inst；新 check-generator-sync 挂 L2 |
| QEMU-077t | 已验证 | 2026-11-01 11:45 | helper.c/cpu.h 注释 reserved cfx 7-14→6-14 与宏一致；补丁重导出，行为不变不重建 |

