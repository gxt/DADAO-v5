# M9 归档（Archive）

> **归档日期**：2026-10-25 ｜ **范围**：M9 里程碑（**FP 完备性 + ISA 收口 + 规范重组**；2026-10-19 起 ~ **2026-10-24 达成**）。
> **状态（如实）**：**项目里程碑 M9 = 达成（2026-10-24，用户裁定「不用等我确认」）**——核验册 `INTEG-037m` 原留活于 `.tao/tasks/integ/`，**M10 核验册建立时（2026-11-01）移入本目录 `integ/`**（留在活目录会被 `check-milestone` 误判为当前 M10 的 m 册）。
> **归档判据**：任务书字段 `**项目里程碑**：M9` 且状态 `已验证`（**69** 个 = infra 11 / integ 1 / llvm 15 / qemu 10 / spec 21 / testcases 11）；`issues.yaml` M9 期关闭项（**83** 条，见 `issues-closed.md`）。
> **留活（不归档）**：`issues.yaml` 11 条 open（全部 M10 登记项）；`INTEG-037m` 已于 2026-11-01 移入本目录 `integ/`（见 `integ/INTEG-037m-M9里程碑核验.md`）。
> **说明**：本目录是**历史归档**，不再活跃；权威摘要见 `m9-retrospective.md`，后续路线见 `.tao/knowledge/milestones.md`。

## 1. M9 任务清单（69 个，按模块）

| 模块 | 数量 |
|---|---|
| infra | 11 |
| integ | 1 |
| llvm | 15 |
| qemu | 10 |
| spec | 21 |
| testcases | 11 |

> 任务书位于同目录下 `infra/` `integ/` `spec/` `llvm/` `qemu/` `testcases/` 子目录（`git mv` 保留 `R` rename 历史）。

## 2 任务流水（冻结）

> **冻结日期**：2026-11-01（`INFRA-117t`）。原样搬入 `.tao/knowledge/milestones.md`「任务流水」的 M9 期行（68 个模块任务册 + `integ/` 核验册 `INTEG-037m`，共 **69** 行）；行状态 == 归档任务书 `**状态**`；`SPEC-172t` 按任务书取 `已验证` / `2026-10-24 23:57`；全表不含登记注记。

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| INTEG-037m | 已验证 | 2026-10-25 00:00 | M9 整体核验：67 册全验证、终局复跑 0 fail、open issue 10（M10 登记） |
| SPEC-172t | 已验证 | 2026-10-24 23:57 | 发布 SimRISC **0.5.5**（去 `-rc`、补 release note、锁重算；不预开新 rc 段） |
| TESTCASES-062t | 已验证 | 2026-10-24 16:34 | 陈旧证据脚本 3 条：237 集合包含、238 残留 0（73 PASS）、282③ 26 件移档（md5 26/26） |
| INFRA-105t | 已验证 | 2026-10-24 15:49 | `apply_series` 支持 `patchless`（5 组件 skip，rc=0）；`ISS-224` 并入 `ISS-231` 同关 |
| SPEC-171t | 已验证 | 2026-10-24 15:36 | 契约悬空 13 条清零 + `rrrr` 单目的三源入格式表；`check_asm_prose` R6 改读 fields.role |
| QEMU-073t | 已验证 | 2026-10-24 15:16 | `cpu_loop_exit` 前整链复位 MMIO 重入守卫（`ISS-064`）；潜伏缺陷（无 MMIO 设备）；补丁 60→63 |
| INFRA-103t | 已验证 | 2026-10-24 14:30 | 陈旧引用/文案 8 条（关 160/208/308/311/318/090/300/329）+ `gen_asm_list` 幂等 + `frem_proof` 活断言 |
| TESTCASES-053t | 已验证 | 2026-10-24 12:35 | 陈旧证据脚本：270 注记/273 基线（27P6F→35P0F）/282 ①②/288（1F→22/22）；用例 0 增 0 删 |
| SPEC-170t | 已验证 | 2026-10-24 12:00 | schema `op`→`opc`：266 键 + 13 工具；值/顺序/`ha` 未动；重生成零 diff |
| SPEC-168t | 已验证 | 2026-10-24 11:21 | `SimRISC-00`：删 §2.2 高 16 位表与句、7 表列对齐、`op`→`opc`、去 `I 形态`；语义 diff 仅授权删除 |
| SPEC-167t | 已验证 | 2026-10-24 11:20 | 分册重组：11=核芯功能扩展（6 条 cfx）/ 12=其它指令（原子+空转+`ct*`）/ 非法指令→00 |
| TESTCASES-057t | 已验证 | 2026-10-24 10:05 | clmul 集成：两档各 627 checks；GHASH/CRC-32C 标准向量 + 独立 oracle；注入 5 类红 |
| INFRA-104t | 已验证 | 2026-10-24 09:05 | musl 加 `-ffp-contract=off`：libc-test 331 pass/0 fail（`math/yn` 回绿），用户 FMA 无损 |
| LLVM-129t | 已验证 | 2026-10-24 06:10 | `ldm`/`stm` post-RA 合并（10 寄存器 → 1+1）；反例 5 类活；lit 148、embench 38/38 |
| LLVM-126t | 已验证 | 2026-10-24 04:50 | FP 接线：fcmp 12 条/符号/分类/位转/缩放/舍入模式/饱和 + `__builtin_dadao_remainder`；`FREM` 仍不接 |
| TESTCASES-058t | 已验证 | 2026-10-23 22:00 | FMA 集成：O0/O2 各 626 PASS；单次舍入 6 组判别；无 libcall；覆盖 +3/删 0 |
| SPEC-158t | 已验证 | 2026-10-23 21:30 | FMA 解 excluded：`fp` 64→66、15 族、`excluded` 4→2；其余 264 条零改动 |
| LLVM-123t | 已验证 | 2026-10-23 19:05 | FMA 后端：`fma`/`fmuladd`/C `fma` 各 1 条，零拷贝；单次舍入实跑成立 |
| QEMU-070t | 已验证 | 2026-10-23 18:10 | `ftfma`/`fofma` 语义：softfloat `muladd` 单次舍入；探针 122/122（含真判别例）；266/266 |
| SPEC-157t | 已验证 | 2026-10-23 16:50 | `ftfma`/`fofma` 立册（`rrrr` 四操作数、`0x5E/0x5F`、excluded）；total 266 |
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

## 3 终局证据（2026-10-24 复跑）

| 套件 | 结果 |
|---|---|
| L3 `check-full` | PASS（Embencb 38/38、`lit-full`、全量语义 967） |
| libc-test 静态 / 动态 | 331 pass / 0 fail；338 pass / 0 fail（`blocked` 5 / 2） |
| llvm-test-suite 静态 / 动态 | 204 pass / 0 fail；203 pass / 0 fail（`blocked` 13 / 14） |
| 发布版本 | **SimRISC 0.5.5**（13 册；changelog 30→14 条；归档 `SimRISC-0.5.5/`） |

> `rc=1` 仅由 `blocked>0` 触发（`ISS-248` 既定口径），非失败。

## 4 MEMORY 摘录（M9 时期）

> **0 行**——`MEMORY.md` 纯 M9 行在 M9 归档时已移出；当前归档指针见 `.tao/knowledge/MEMORY.md`，权威摘要见本目录 `m9-retrospective.md`。

## 5 指针

- 里程碑定义/达成：`.tao/knowledge/milestones.md`（M9 归档指针行；任务流水 **69** 行已冻结在本 README §2）
- 里程碑回顾：本目录 `m9-retrospective.md`
- 里程碑核验：本目录 `integ/INTEG-037m-M9里程碑核验.md`（2026-11-01 由 `.tao/tasks/integ/` 移入本归档 `integ/`）
- 关闭 issue 快照：本目录 `issues-closed.md`（83 条）
- 遗留台账：`.tao/knowledge/issues.yaml`（issue/待决）、`.tao/knowledge/lessons.md`（教训/方法论）
