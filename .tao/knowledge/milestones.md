# 项目里程碑

> **项目里程碑 = M10**（当前里程碑；`check-milestone` 取 `项目里程碑 = M<n>` 断言的**最大 n**，本行是唯一断言）
>
> 只维护任务流水；历史任务见 `.tao/archive/`，当前讨论/规划见 `.tao/knowledge/discussing.md`。
>
> **M9 归档指针（2026-11-01）**：M9 任务书 **68** 册 + 根级核验册 `INTEG-037m` 与 M9 期关闭 issue **83** 条已冻结到 `.tao/archive/M9/`（`README.md` / `m9-retrospective.md` / `issues-closed.md`）；流水 **69** 行已冻结到 `.tao/archive/M9/README.md §2`，本页不再保留 M9 行。
>
> **M10 归档指针（2026-11-01）**：M10 任务书 **71** 册（含核验册 `INTEG-052m`）与 M10 期关闭 issue **17** 条已冻结到 `.tao/archive/M10/`（`README.md` / `m10-retrospective.md` / `issues-closed.md`）；流水 **70** 行已冻结到 `.tao/archive/M10/README.md §2`，本页仅留 M10 后维护行（`check-milestones-fresh` A1/A2 对归档册同样生效，已归档号豁免回填）。

## 任务流水

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| TESTCASES-093t | 待开始 | 2026-11-03 12:19（登记） | L3 探针收口：F4 check-arch --qemu、power 复位+hmon identity-PTW prelude、去 -kernel、13+1 册逐例判定；未绿不写 PASS |
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
| TESTCASES-090t | 待验收 | 2026-11-02 07:07（登记） | scaleB/sc 测试；LLVM lit/isa matrix 已同步；QEMU/gem5 对照 BLOCKED |
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

