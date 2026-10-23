# 项目里程碑

> 只承载**当前进度**；历史见 `.tao/archive/M<1..7>/m<i>-retrospective.md`。
>
> **M7 收尾归档（2026-10-13，`INTEG-035m`）**：M7 期（2026-10-11 ~ 2026-10-13）任务书/回顾/已关 issue **收尾归档**至 `.tao/archive/M7/`（`README.md` / `m7-retrospective.md` / `issues-closed.md`）；**项目里程碑 M7 = 达成**（2026-10-13 口径纠正：`AGENTS.md`「不得置里程碑」**只针对未处置的*跨模块*影响**，`ISS-201` 属 spec **模块内 backlog**、**不阻断** ⇒ `SPEC-136m`/`INTEG-034m` 置 `里程碑`）。**未决项**（`INFRA-071t` **已验证 2026-10-15**；后随 M8 收尾归档入 `.tao/archive/M8/infra/`）见本页「任务流水」。
>
> **M6 达成（2026-10-11，architect 实测核验）**：门槛 `make check` **EXIT=0** + **opt-in** `make test-m6` **EXIT=0**（`check-lit-full` 12/12 + `diff_ir_lli` 19/19 + Embench 38/38）；6 个模块 `m` 全置 `里程碑` ⇒ **项目里程碑 M6 = 达成**。M6 任务书/回顾/已关 issue 已归档至 `.tao/archive/M6/`（回顾 `m6-retrospective.md`、清单 `README.md`、快照 `issues-closed.md`）。核验命令/证据见各 `m`「核验」与 `.work/log/integ/INTEG-026m-*.log`。
>
> **M8 收口归档（2026-10-19，`INTEG-036m`）**：项目里程碑 **M8 = 达成**；M8 期 **68 册**任务书/回顾/**52 条**已关 issue 已归档 `.tao/archive/M8/`（`README.md` / `m8-retrospective.md` / `issues-closed.md`）。本页「任务流水」只保留未归档项（`LLVM-100t` = `M9`；`SPEC-141t` = 只读预研待开工）。


## 体例约定（硬约束）

1. **任务流水用表格**：列 = `| 编号 | 状态 | 完成时间 | 一句改动 |`；**一句改动 ≤120 字符**（中文按 1 字符计）；细节写各任务书，本文只做**索引**（与 `lessons §1.4` 一致）。
2. **按完成时间倒序**（最新在上）；**未完成任务也必须列**，其时间列 = **登记时间**并加注 `（登记）`；同一时间按任务编号升序。
3. **状态以任务书头部「状态」字段为准**；本文与任务书不一致 ⇒ L1 门控 `check-milestones-fresh` 红。
4. **表格之后的当前进度 / M8 规划区 / 状态快照 / M9 规划须随任务与产物同步更新**；计数一律**现场派生**，不写死。

> 机械校验：`make check-milestones-fresh`（L1；状态一致 / 覆盖 / 长度 / 次序 / 格式五断言，`--self-test` 内置五类反例）。

## 项目里程碑

> 项目里程碑（M1–M7 及达成日/主题/成就）见 README.md「项目里程碑」。

**M6 模块里程碑**（均已 `里程碑`）：`INFRA-052m` / `SPEC-125m` / `LLVM-067m` / `QEMU-054m` / `TESTCASES-040m` / `INTEG-026m`。

**M8 模块里程碑**：仅 **`INTEG-036m`**（整体收敛点，已 `里程碑`，2026-10-19；M8 期未设各模块 `m`，由 68 册任务终态 + 本册判据收敛承担）。

**M7 模块里程碑**（**均 `里程碑`**：`INFRA-072m`/`SPEC-136m`/`LLVM-090m`/`QEMU-059m`/`TESTCASES-043m`/`INTEG-034m`〔整体收敛点〕）：`INFRA-072m` / `SPEC-136m` / `LLVM-090m` / `QEMU-059m` / `TESTCASES-043m` / `INTEG-034m`（整体收敛点）+ `INTEG-035m`（M7 收尾归档，`Process-04`；任务书**已自归档**入 `.tao/archive/M7/integ/`）。

## 任务流水

> 本表 = **未归档任务流水**（M9 及留活项）；M8 已终态流水（68 条）见 `.tao/archive/M8/README.md §2`，M7 及以前见 `.tao/archive/M*/README.md`。列 = `| 编号 | 状态 | 完成时间 | 一句改动 |`；**按完成时间倒序**（最新在上）；**未完成任务也列**（时间 = **登记时间**，加注 `（登记）`；同一时间按任务编号升序）。**一句改动 ≤120 字符**，只写「做了什么 + 关键数字/结论」；细节一律写各任务书（本表只做索引）。**新立任务（任务书落盘）时即加行**。

> **未完成任务册（现场派生，清单见下）**
> - 缺陷修复批（2026-10-20 立册，`ISS-302`；`LLVM-118t`/`119t`/`120t`、`INFRA-096t`/`INFRA-097t` 已 `已验证`）：`INFRA-098t`（`ISS-261` + `ISS-301`）、`INFRA-099t`（`ISS-229` 门控互斥）、`TESTCASES-053t`（`ISS-270`/`273`/`282`/`288` 陈旧证据脚本族）
> - `SPEC-141t`：`M9` / ISA 扩展预研 —— **结册未执行**（2026-10-21；未定项见下「ISA 扩展预研遗留」）
> - `ADR-0034`（2026-10-20 定案 / 2026-10-21 转正）：原子编码定案（`fence` `0x20`、`lr/sc` 24 条），规范面/合约/生成面已落；**实现 4 册全部 `已验证`**（`ISS-307` `closed`，2026-10-21）
> - **原子链 4 册（`ISS-307`）现状**：① `LLVM-121t`（返工修复 `ISS-312`/`ISS-313`，reviewer 第 3/4 轮 `Accepted`，20 条 XFAIL 已转 PASS）、② `QEMU-067t`、③ `INFRA-100t`、④ `TESTCASES-056t`（reviewer 第 2 轮 `Accepted`；两档 711/711、0 xfail）= **全部 `已验证`** ⇒ `ISS-307` `closed`，`ISS-294` 随 ③/④ 收口。
> - 说明：`M8` 已于 2026-10-19 达成；`LLVM-116t`/`QEMU-064t`/`SPEC-152t` = `已验证`（ISA 链收口）、`INFRA-095t`/`TESTCASES-052t` = `已验证`（线程链 T1/T3 收口，19 目标两档 19/19）；未解 `issue` 见 `issues.yaml`（不在此重复）。

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| LLVM-127t | 已验证 | 2026-10-23 15:46 | 窄位 `i8/i16/i32` 全做：各 1 条指令、`ext.uo` 首用、`ISS-310` 修复；lit 135、libc-test 0 fail |
| TESTCASES-059t | 已验证 | 2026-10-23 07:58 | `min/max` 集成：O0/O2 各 3102 PASS、值+标志双断言 1502+1502；无 libcall；注入三类红 |
| LLVM-128t | 已验证 | 2026-10-23 06:10 | `ctlz/cttz/ctpop` + `rev.o/.t` 各 1 条（原 10/7 条）；零值运行期 64/0；lit 132/132 |
| TESTCASES-061t | 已验证 | 2026-10-23 05:24 | harness 失败路径可信化（`br.nz` 偏移）+ 6 条工具去陈；978 全量 0 failed |
| SPEC-164t | 已验证 | 2026-10-23 02:17 | `OPC-MISC` 迁 `op 0x47`（29 条，含 `ct*` 并入）+ 25 条解 `excluded`；264/264、实机全通 |
| INFRA-102t | 已验证 | 2026-10-23 00:55 | 门控去写死计数（改不变量）+ 7 项缺口；L1 增量 <1 s；8 注入全红 |
| SPEC-166t | 已验证 | 2026-10-23 00:17 | 规范收尾：拍平 5 册、删 15 个"已删除"节、断 27 处跨册引用、`spec_cite` 改手册+助记符（264/264 命中） |
| SPEC-165t | 已验证 | 2026-10-22 23:30 | spec 净化+附录归位+重编号+`MISC-`→`OPC-`（485 处）；语义零漂移；关 ISS-192/315/316 |
| SPEC-160t | 已验证 | 2026-10-22 21:43 | `min/max` 解 excluded：`fp` 60→64 / 14 族、`excluded` 31→27；264/264、lit 131/131；注入两例双红 |
| LLVM-124t | 已验证 | 2026-10-22 21:00 | `min/max` 后端：`minnum`/`minimumnum`/C `fmin` 各 1 条；`minimum` 9 条无 libcall；`FMINNUM` 改 Custom（「≤4」裁定放宽） |
| QEMU-071t | 已验证 | 2026-10-22 19:30 | `min/max` 语义：softfloat `minimum_number`；探针 111/111（值+NV/NX）；`check_qemu_trans` 264/264，`ISS-324` closed |
| SPEC-159t | 已验证 | 2026-10-22 16:50 | `ftmin/ftmax/fomin/fomax` 立册（754 `minimumNumber`、`orrr`）；264/31/60；`ISS-324`/`325` 登记 |
| TESTCASES-060t | 已验证 | 2026-10-22 16:20 | 取整集成：6 档矩阵 + 模式敏感 + 标志；两档 805/805；独立 oracle 284/284；L2 边际 ≈6 s |
| SPEC-162t | 已验证 | 2026-10-22 15:40 | 取整解除 `excluded`（`scope → fp`，新族 `roundint`）；fp 60 / excluded 27 / 260；13 族；规则明细同步 |
| LLVM-125t | 已验证 | 2026-10-22 14:20 | 取整后端：7 个 intrinsic → 6 档、各 1 条；`FNEARBYINT` 落 0x20（NX 偏差已注明）；lit 132/132 |
| QEMU-072t | 已验证 | 2026-10-22 13:40 | 取整语义：静态 5 档只合 NV、DYN 读 rf0；探针 413/413；`check_qemu_trans` 260/260，`ISS-322` closed |
| SPEC-161t | 已验证 | 2026-10-22 13:10 | `ftrnd`/`fornd` 立册（754 六种取整、`immu6` one-hot `0x03`/`0x0B`）；260/29/58；证据 79/79 |
| SPEC-163t | 已验证 | 2026-10-22 12:42 | 删 `cs.eq/ne_rrrr_rf`（258 条 / fp 58）；`.td`+trans+lit 原子删除，0x5E/0x5F 腾空 |
| INFRA-101t | 已验证 | 2026-10-22 09:52 | 新鲜度门控改用 build-id（替代 mtime）；两门控 + 旧 stamp 迁移；touch 绿 / 内容变红 / relink 后免重建 |
| SPEC-155t | 已验证 | 2026-10-22 07:12 | clmul 解除 `excluded`（`scope → m9`）；其余 259 条零改动、`accept 258/reject 2`、锁重算 |
| LLVM-122t | 已验证 | 2026-10-22 05:20 | clmul 后端：`.td` + 低/高/双半伪指令 + `llvm.clmul`/`llvm.dadao.clmul` + `__builtin_dadao_clmul`（各 1 条）；scope 仍 excluded |
| QEMU-068t | 已验证 | 2026-10-22 00:52 | `clmul.o` 语义（高/低 128 位、`rd0` 单侧、ILLI）；向量 81/81；`check_qemu_trans` 260/260，`ISS-317` closed |
| QEMU-069t | 已验证 | 2026-10-22 00:31 | `fcls` 位序重排（10 个位号）；探针改由 spec §7 解析（独立 oracle）；84/84 |
| SPEC-156t | 已验证 | 2026-10-22 00:12 | `fcls` 10 类位序改为 754/LLVM 顺序；两处逐项一致（脚本机械比对）、锁重算、破坏性已标注 |
| LLVM-123t | 待开始 | 2026-10-21 23:50（登记） | `ftfma`/`fofma` 后端：`.td` + `llvm.fma`/`fmuladd` 选择；循环形态 0 拷贝 |
| LLVM-126t | 待开始 | 2026-10-21 23:50（登记） | FP 后端接线补齐（`ISS-188` 剩余 8 类：`fcmp`/`fpclass`/`bitcast`/`rounding`）；`frem` 不接 |
| QEMU-070t | 待开始 | 2026-10-21 23:50（登记） | `ftfma`/`fofma` 语义：softfloat mulAdd 单次舍入；探针含 fma≠mul+add 反例 |
| SPEC-157t | 待开始 | 2026-10-21 23:50（登记） | `ftfma`/`fofma` 立册（四操作数 `rrrr`、`op 0x5E/0x5F`；excluded） |
| SPEC-158t | 待开始 | 2026-10-21 23:50（登记） | `ftfma`/`fofma` 解除 `excluded`（`scope → fp`，新族 `fma`） |
| TESTCASES-057t | 待开始 | 2026-10-21 23:50（登记） | clmul 集成：指令级 + GHASH + CRC-32C，独立 oracle、两档 |
| TESTCASES-058t | 待开始 | 2026-10-21 23:50（登记） | `fma` 集成：单次舍入反例 + 点积/GEMM/Horner，独立 oracle、两档 |
| INFRA-099t | 已验证 | 2026-10-21 23:43 | ISS-229：29 个写者/门控由 `flock` 串行（嵌套放行、有界等待、rc=69/75）；真并发验证串行、L1/L2 绿 |
| INFRA-098t | 已验证 | 2026-10-21 19:35 | 安装集补 `llvm-nm`（342 MB/+3.6%）+ `llvm-readelf` 相对链接（0 B）；builtins 4 次重建同 sha；`check-install-tools` 45 项 PASS |
| TESTCASES-054t | 已验证 | 2026-10-21 19:08 | 超时预算重标：lua 840→1320、XSBench 新增 720（实测+120 s）、unix-smail 0.11 s 不入表；清过时注记 |
| INFRA-097t | 已验证 | 2026-10-21 16:49 | ISS-235：L3 载体现场派生 19 册（897 例 886 pass/0 fail/11 deferred）；11 例按 spec 对齐、6 例精确 defer；ISS-235/236 closed |
| SPEC-154t | 已验证 | 2026-10-21 16:14 | SimRISC 8 版本清单双源派生 + 6 个缺档归档（含 PROVENANCE）+ 19 缺段（2 补段/17 diff=∅）+ `check-spec-archive` 入 L1 |
| SPEC-153t | 已验证 | 2026-10-21 15:11 | 原子指令章（`fence`+24 条 `lr/sc`）自 `SimRISC-12` 逐字迁入 `SimRISC-11 §6`；生成区分类改判、两册只读锁重算 |
| TESTCASES-056t | 已验证 | 2026-10-21 14:26 | C11 全类型/`__atomic_*`/计数/ABA 两档 711/711（0 xfail）；关 `ISS-294`；摘除 20 条 XFAIL |
| LLVM-121t | 已验证 | 2026-10-21 13:53 | `fence`+24 条 `lr/sc`+CAS 环；零 libcall；返工修 ISS-312/313，20 XFAIL 转 PASS、711/711 |
| INFRA-100t | 已验证 | 2026-10-21 11:03 | musl `a_cas`/`a_cas_p`/`a_barrier` 落 `lr/sc`+`fence`；4×250000 计数精确 5/5、047t 19/19、证据 164/164 |
| QEMU-067t | 已验证 | 2026-10-21 10:21 | `fence` fm/SBZ 校验 + pred/succ→TCG_MO；`lr/sc` 保留 + 8B 字 CAS + 按宽度 MALIGN；L3 +127 ⇒ semantics 351/351；并发 40000/40000 |
| SPEC-141t | 已验证 | 2026-10-21 00:15 | 结册未执行：未定项转入遗留段 |
| TESTCASES-055t | 已验证 | 2026-10-20 17:11 | ansibench 接入第一步：pin `ef90abd0`、7/8 构建成功、9 次运行、CoreMark/STREAM 自校验 PASS；基线对比=部分可行 |
| INFRA-096t | 已验证 | 2026-10-20 15:26 | ISS-293 真根因 = builtins 归档陈旧：clean 重建 + 三份副本同源 + 新鲜度门控 + `libc.so` 重链戳记 |
| LLVM-118t | 已验证 | 2026-10-20 15:26 | ISS-193 现场重枚举 1120 项 0 失败、过滤表 1→0；ISS-222 ①`%N` 打印落地（lit+运行期）、③④ 复证收口 |
| LLVM-119t | 已验证 | 2026-10-20 15:26 | ISS-197：内联汇编 `m`/`=m`/`+m`/`=&m`/`rm` ISel+打印落地（rc=134→0）；12 运行期探针、lit 111/111 |
| LLVM-120t | 已验证 | 2026-10-20 15:26 | ISS-245：dynv=NULL + 按 `AT_PHDR`−`PT_PHDR.p_vaddr` 求 `_DYNAMIC`；`rcrt1.o` ABS48 3→0、`crt1.o` 逐字节不变；oracle 11/11 |
| LLVM-100t | 已验证 | 2026-10-20 14:30 | T4 静态 `__thread` TLS：`TLSSupported`+local-exec（TP=`rb3`、`ABS48`）；静态 3/3、lit 118/118；证据 78/78（T5 后现场派生） |
| LLVM-117t | 已验证 | 2026-10-20 14:30 | T5 动态 TLS 10/11/12 发射 + lld 消费；3 例 TLS 3/3、dlopen 5/5；动态档 338 pass/0 fail、26 条非 pass→pass；musl 0 改动 |
| QEMU-066t | 已验证 | 2026-10-20 14:30 | 线程 qemu 缺口 3 条：PI futex 大端整字转换、robust list 注册查询、ucontext 去 16B 对齐；4 例两档 4/4 |
| QEMU-065t | 已验证 | 2026-10-20 11:50 | T2 qemu-user 线程语义：clone/TLS/futex/exit/信号；并发互斥丢更新 ⇒ 根因 musl `a_cas` 假原子（另立 ISS-294） |
| INFRA-095t | 已验证 | 2026-10-20 10:52 | T1 musl `__clone`+TP：`rb3` 仅 `CLONE_SETTLS` 时写；spawn/popen 两档 2/2、T3 19 目标 19/19；`ISS-295` closed |
| SPEC-152t | 已验证 | 2026-10-20 10:52 | ISA 编码再分配 + `rol`；ext 迁 100/101、shl 迁 010/011；校验器入 `tools/spec/`，4 表 256 格 0 不符、self-test 4/4 |
| TESTCASES-052t | 已验证 | 2026-10-20 10:52 | T3 线程 19 例两档 19/19（`QEMU-066t` 后）；`ISS-299` closed；`ISS-252` 仍 open（extra 例受 `ISS-257`） |
| LLVM-116t | 已验证 | 2026-10-20 09:02 | ext/shl 编码迁移 + rol.o/t/w/b；ROTL 直连 1 条、ROTR 折 2 条；check-instrinfo 0 错、lit 120/120 |
| QEMU-064t | 已验证 | 2026-10-20 09:02 | 解码 235→243；rol.o/t/w/b 语义；L3 224/224（独立 oracle 64/64）、smoke 90/90；L1 全绿 |
| TESTCASES-053t | 待开始 | 2026-10-20 04:55（登记） | ISS-270/273/282/288：陈旧证据脚本族逐条修或按 `Process-08` 重建；不许放宽断言 |

## 当前进度（2026-10-22）

- **M9 进行中**：进度**只以本页任务流水为准**；细节写各任务书，计数以现场门控输出为准。
- **已收口（本批）**：ISA 链（`rol`）、线程链 T1–T5、原子链 4 册、门控互斥（`INFRA-099t`）、
  `fcls` 位序（`SPEC-156t`/`QEMU-069t`）、`clmul` 4 册、取整 5 册、`min/max`（进行中）。
- **队列**：`min/max` 剩余 → FMA 5 册 → `TESTCASES-057t` → `LLVM-126t` → `TESTCASES-053t` → 终局全量复跑。
- **M8 已归档**（2026-10-19）：`.tao/archive/M8/`（`README.md` / `m8-retrospective.md` / `issues-closed.md`）。
- **计数类口径**（用户 2026-10-22 裁定）：`contract-isa.md` 等分桶计数在**里程碑收尾**统一同步，不随单任务改。

### ISA 候选（`SPEC-141t` 结册）

> 判据（用户 2026-10-21 原话）：**目标应用域能力需求 + 软硬件代价比**；语料频次只回答"今天能否验证"。

- `f16`：**不做**（C23 可选、零语料、硬报错不静默）。
- `mulhu`：**已具备**（`mul.uo` 双目的出全 128 位），撤回候选。
- `fshl`/`fshr`：**保留候选（中）**；后端可先去冗余 mask（实测 9→4 条），将来加指令则 1 条。
- `clmul`：**已定案**（`ADR-0035`，已实现并验证）。
- `crc32c`：**候选（高）**，未立册。
- 未定：`bswap64` 用 `rev.o`；"hw 特化后置"分界（`ADR-0027 D3`）。

## M9（规划）

- 决策载体：`ADR-0030`（`long double`=binary128，排 M9）、`ADR-0031`（变参 ABI）、`ADR-0032`（`rol`，已落）、
  `ADR-0034`（原子）、`ADR-0035`（`clmul`）。
- 实现/排期细则**不在此重复**：见对应任务书与 `issues.yaml`；本段只作导航。
