# 项目里程碑

> 只维护任务流水；历史任务见 `.tao/archive/`，当前讨论/规划见 `.tao/knowledge/discussing.md`。

## 任务流水

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| INFRA-112t | 待开始 | 2026-10-31 22:45（登记） | `check-knowledge-dir` 回 L1：进 `_locked-check`、退出 `check-milestone`、Process-07 登记同步 |
| INTEG-050t | 已验证 | 2026-10-31 22:29 | cfx_time + 单 hart cfx_hart（64 位 cycle/insn、定时器、探针、m5 换 cfx_llc） |
| TESTCASES-087t | 已验证 | 2026-10-31 18:20 | ctrl 生成器 OUT_DIR 迁回 tests/inst/base；`--check` 逐字节校验 + 落点守卫 |
| TESTCASES-086t | 已验证 | 2026-10-31 16:10 | reserved cfx 异常期望修正：ctrl-ret[9] 取指 ⇒ CFXMEM；审计 tests/inst 全部 fault 期望 |
| INTEG-049t | 已验证 | 2026-10-31 12:30 | cg7 空间描述落地：16×4 只读表、写任意 rc ⇒ CFXREG、四类空间探针 |
| TESTCASES-085t | 已验证 | 2026-10-31 12:10 | runner 外杀后清理 qemu 孤儿：PID/PGID 登记 + SIGTERM/INT/HUP 钩子 + 公共助手 + 自检 |
| INTEG-048t | 已验证 | 2026-10-31 10:30 | `cfx_*_cg_reg_deleg` 强制检查：`CFXPERM`/bit3 恒 1/全 cg/不豁免 self；hmon 写 `0x8` 开 ptw/pmem/smon；power 仅 cfxmem bit2 开 BootROM |
| SPEC-179t | 已验证 | 2026-10-31 09:10 | 启动链/BootROM/权限口径清理：DADAO-12 BootROM 256 KiB；cg7 空间描述改 4 行数组（stride 4，768 别名）；Machine-01 启动链/PA0 |
| INTEG-047t | 已验证 | 2026-10-31 01:30 | cfx_pmem DMA 的 SBI 契约：§9 补 FID 6/7/8（WAIT 预留）、错误码 `-5` 忙、测试专用 provider 探针 |
| INTEG-046t | 已验证 | 2026-10-31 00:50 | Step5 启动链：256 KiB BootROM 表/ELF 校验、power→hmon→smon、smon 首张页表+PTW（ADR-0043） |
| INTEG-045t | 已验证 | 2026-10-30 20:41 | cfx 指令清理：reserved 规则/删 cfxld-cfxst/fence 宏表 |
| INTEG-044t | 已验证 | 2026-10-30 18:39 | CFX 两轴权限模型落地（ADR-0045） |
| INTEG-043t | 已验证 | 2026-10-30 11:06 | cfx_pmem SRAM 内偏移迁 0x3ff_0000_0000（核内 0x47ff_0000_0000；QEMU/探针 25 例/锁） |
| INTEG-042t | 已验证 | 2026-10-30 08:01 | Step 4：cfx_pmem 64 KiB SRAM + SRAM↔PA DMA/PMEM_DMA（ADR-0042；探针 23 例） |
| INTEG-041t | 已验证 | 2026-10-30 00:25 | fence ciii 落地（ADR-0044：0x79/cfxha/pred-succ/移册） |
| SPEC-178t | 已验证 | 2026-10-29 21:37 | 术语清理：移除地址高 6 位讨论期简写，统一 addr[47:42]/cfxha 表述 |
| INTEG-040t | 已验证 | 2026-10-29 15:23 | Step 3：TLB 并入 cfx_ptw/16 位 ASID/G/A-D 回写/PTWERR（ADR-0041；探针 34 例） |
| LLVM-140t | 已验证 | 2026-10-29 15:05 | 窄 neg extend 按节点自身类型（i32/i16）选 ext；lit 159、e2e 19/19、McCat 18-imp 两档 PASS |
| INTEG-039t | 已验证 | 2026-10-29 10:55 | Step 2：PTE/页表步进/页权限（ADR-0040；A/D 留 Step 3） |
| INTEG-038t | 已验证 | 2026-10-29 07:10 | Step 1：地址空间/PTBR/PTW 落地（ADR-0039；不含 PTE/TLB/DMA/启动） |
| TESTCASES-084t | 已验证 | 2026-10-28 20:22 | 测试残留清理：e2e→unit/llvm、删旧链接/32 wrapper/spec 路径/补丁注释 |
| LLVM-139t | 已验证 | 2026-10-28 18:35 | 循环指针 PHI GPRB machine pass（支配/verify/负例；lit 158、e2e 18/18） |
| LLVM-138t | 已验证 | 2026-10-28 17:15 | 窄整数 canonical extension 折叠（39 组；lit 156、oracle 84/84） |
| LLVM-137t | 已验证 | 2026-10-28 16:49 | i64 常量移位立即数选择（shl.o/shr.uo/shr.so；lit 155、oracle 18/18） |
| LLVM-136t | 已验证 | 2026-10-28 16:13 | PR 审计：不整体 merge（三回退保留）；137–139 重放点入 audits；lit 工具链 opt-in+identity |
| TESTCASES-076t | 已验证 | 2026-10-28 15:40 | 测试迁移收口（删旧+门控重写+clean/repro/night；L3/夜跑报告绿） |
| TESTCASES-083t | 已验证 | 2026-10-28 09:58 | L3 结果报告 + check-milestone 机检（check-l3-report） |
| TESTCASES-082t | 已验证 | 2026-10-28 09:55 | L3 去 tset smoke（严格一层；tset full 归夜跑） |
| TESTCASES-077t | 已验证 | 2026-10-28 07:47 | llvm-ts：aarch64/archie/plot2fig 等排除、Burg/cdecl/OptimizerEval 方言、mafft 1800s；两档 214/214、零 known-fail |
| TESTCASES-081t | 已验证 | 2026-10-28 02:35 | gawk/make/p2c 按 CMake 排除；archie/plot2fig excluded；ClamAV；SIG 判据（077 余项清） |
| TESTCASES-078t | 已验证 | 2026-10-28 01:59 | SPASS/lemon 胶水补丁；SPASS 参考不须重定（069t 74365d61 = 多传 -DocProof）；两档 md5-exact（ISS-338 关闭） |
| TESTCASES-080t | 已验证 | 2026-10-28 01:23 | llvm-ts 零 known-fail：obsequi/ft glibc PRNG、8b10b LE→BE；三条两档 pass、known-fail=0 |
| TESTCASES-079t | 已验证 | 2026-10-28 00:07 | consumer-typeset：musl catclose 无效句柄守卫（-1/EBADF），两档由 SIGBUS 转 pass（ISS-339） |
| TESTCASES-075t | 已验证 | 2026-10-27 06:35 | tset 迁移（libc-test/llvm-ts/embench；check-tset） |
| TESTCASES-074t | 已验证 | 2026-10-27 05:11 | unit 迁移（lit/codegen/ir-lli/picolibc；check-unit） |
| TESTCASES-073t | 已验证 | 2026-10-27 03:49 | arch 迁移：m5→tests/arch/umon、min-ROM→tools/testcases/arch、bootrom→shared、check-arch(-smoke)+旧名别名 |
| TESTCASES-072t | 已验证 | 2026-10-27 02:26 | inst 迁移：向量/探针→tests/inst、harness→tools/testcases/{lib,inst}、check-inst(-smoke)+旧名别名 |
| TESTCASES-071t | 已验证 | 2026-10-27 01:51 | 测试骨架与根级索引（P1；四 scope 目录 + 索引 + check-tests-index） |
| TESTCASES-069t | 已验证 | 2026-10-27 01:35 | ISS-266 四例判定：8b10b known-fail、dbms pass、SPASS 语料 UB、typeset 语料+musl；0 blocked |
| TESTCASES-068t | 已验证 | 2026-10-27 00:32 | qemu-user OOM 修复：-R 4G + flockfile known-fail（ISS-255/257） |
| TESTCASES-070t | 已验证 | 2026-10-27 00:01 | rev 向量重生成+门控、diff_ir_lli 2 个 .ll 归类（ISS-335/336） |
| INFRA-110t | 已验证 | 2026-10-26 23:44 | semihosting 旧口径文档清理（README 历史注记、DDLN、Machine-00、audit 头注） |
| SPEC-177t | 已验证 | 2026-10-26 23:27 | 删除 SBI 保留值 0x3FFFF（ISS-334 B）；SBI/SEE 0.7.3-rc |
| LLVM-135t | 已验证 | 2026-10-26 17:27 | cfx 别名运行时表：源码/反汇编共用名字，数据更新不重建 LLVM |
| TESTCASES-067t | 已验证 | 2026-10-26 14:05 | 测试框架调研与 tests 组织方案（主流 ISA 对照 + 生成物 A/B + 确定性） |
| QEMU-076t | 已验证 | 2026-10-26 13:18 | semihosting 调用点迁至 0x3FFxx（QEMU 译码 + bootrom/测试/探针 + picolibc/embench/musl 组件） |
| SPEC-176t | 已验证 | 2026-10-26 11:20 | semihosting 判定迁至 0x3FF00–0x3FFFF（ADR-0038）；HBI INIT 0x30001 解冲突 |
| SPEC-175t | 已验证 | 2026-10-26 09:47 | C1–C11 落实 + 六册发布 0.9.3/0.7.2/0.1.3（去 -rc）+ cfx_timer→cfx_time + HBI 启动移交重写 + 同步不可屏蔽门控 |
| TESTCASES-063t | 已验证 | 2026-10-26 06:45 | harness ret 路由/宽度修正；`ctrl-ret[0..3,8]`、`ctrl-call[5]` 转绿 |
| SPEC-174t | 已验证 | 2026-10-26 05:10 | DADAO 六册自洽性：机械修正 39 行；语义冲突 C1–C11 待裁定 |
| QEMU-075t | 已验证 | 2026-10-26 04:43 | 宿主信号族诊断：三组不同源（VA 耗尽 / 语料 / 未定）；`-R 4G` 可解 OOM 组 |
| INFRA-108t | 已验证 | 2026-10-26 04:23 | PIC libc 归档（`libc_pic.a`）+ 驱动 `-static-pie` 自动选 |
| LLVM-134t | 已验证 | 2026-10-26 03:41 | 去冗余 `ext.so`（6→0）+ ABS48 显示偏移 + cc1as/llvm-mc DWARF64 默认 |
| TESTCASES-064t | 已验证 | 2026-10-26 02:27 | picolibc `%p` 改 `va_arg(void*)`（bank 不匹配）；8 个 printf 变体转绿 |
| LLVM-132t | 已验证 | 2026-10-25 23:08 | fixup 元数据大端修正（`PCREL_HI 14` / `PCREL_LO 20`），`--show-encoding` 不再断言 |
| INFRA-109t | 已验证 | 2026-10-25 20:09 | 归档门控（结构 + `--verify`）移到 `check-milestone`，退出 L1 |
| LLVM-133t | 已验证 | 2026-10-25 19:45 | `cmp.u*` 语义核对（零代码改动）+ `cmp.ut→br.n` lit 断言 |
| TESTCASES-065t | 已验证 | 2026-10-25 19:28 | `cmp.{ut,uw,ub}` 向量期望改为 64 位全 1；生成器同步 + `cmp.ut→br.n` 序列 |
| QEMU-074t | 已验证 | 2026-10-25 18:33 | `cmp.{ut,uw,ub}` 去掉结果零扩展（-1 = 64 位全 1） |
| SPEC-173t | 已验证 | 2026-10-25 17:20 | `cmp.u*` 的 -1 改 64 位全 1；13 册 0.5.6-rc；00 第 255 行去版本号 |
| INFRA-107t | 已验证 | 2026-10-25 16:46 | 补 0.5.3 PROVENANCE 组合 sha + 逐文件表；`--verify` 跳过 `-rc`（ISS-333） |
| LLVM-131t | 已验证 | 2026-10-25 15:56 | 代码模型 default/large：驱动 `-mcmodel` 口径 + large 间接调用序列 + 远距布局用例 |
| INFRA-106t | 已验证 | 2026-10-25 13:48 | 代码跨度门控：REL26/20/14 余量报告 + 单 DSO 可执行区 <30 MiB（L2） |
| LLVM-130t | 已验证 | 2026-10-25 12:15 | 64 位缺省：CodePointerSize/CalleeSaveStackSlotSize=8 + 默认 DWARF64 + 位宽探针 |
| INTEG-037m | 已验证 | 2026-10-25 00:00 | M9 整体核验：67 册全验证、终局复跑 0 fail、open issue 10（M10 登记） |

