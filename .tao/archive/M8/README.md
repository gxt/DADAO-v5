# M8 归档（Archive）

> **归档日期**：2026-10-19 ｜ **范围**：M8 里程碑（**无内核 Linux 用户态栈**，`ADR-0025`；2026-10-13 起 ~ **2026-10-19 达成**）的全部任务书与相关记录。
> **状态（如实）**：**项目里程碑 M8 = 达成（2026-10-19）**——`INTEG-036m` 置 `里程碑`；判据 ① 两档能编能跑 / ② 三套测试两档如实分类 + 失败逐条归因 / ③ `P4` 不作（用户 2026-10-18 裁定、`ADR-0025 D7` 注记）/ ④ 门控 L1/L2/L3 全绿 + `check-patch-tree` 181 / ⑤ 跨模块影响已核（`issues.yaml` 无 `blocks`）。
> **归档判据**：任务书字段 `**项目里程碑**：M8` 且状态终态（**68** 个 = infra 21 / llvm 23 / qemu 4 / spec 11 / testcases 8 / integ 1）；`milestones.md`「任务流水」中 <= 达成日的行（**68** 条，见 §2）；`MEMORY.md` 纯 M8 进度行（**0** 行，指针页）；`issues.yaml` M8 期关闭项（**52** 条，见 `issues-closed.md`）。
> **留活（不归档）**：`SPEC-141t`（`**项目里程碑**：M8`、`待开始` —— ISA 扩展只读预研，未开工，不属 M8 判据）；`LLVM-100t`（`M9`，`__thread` TLS）。
> **说明**：本目录是**历史归档**，不再活跃；权威摘要见本目录 `m8-retrospective.md`，路线/后续见 `.tao/knowledge/milestones.md`。

## 1. M8 任务清单（68 个，按模块）

| 模块 | 数量 |
|---|---|
| infra | 21 |
| llvm | 23 |
| qemu | 4 |
| spec | 11 |
| testcases | 8 |
| integ | 1 |

> 任务书位于同目录下 `infra/` `spec/` `llvm/` `qemu/` `testcases/` `integ/` 子目录（`git mv` 保留 `R` rename 历史）。
> **特别项**：`integ/INTEG-036m`（**本归档核验册**）按 `Process-04 §4.1` **自归档**（2026-10-19，状态 `里程碑`）。

## 2. 任务流水与实质改动（M8 时期，2026-10-13 ~ 2026-10-19，68 条）

> 原样搬入 `.tao/knowledge/milestones.md`「任务流水」的 M8 **已终态**行（68），只做索引；细节见各任务书。

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| QEMU-062t | 已验证 | 2026-10-17 14:37 | qemu-user 后端：静态+动态两档 E2E 通（ldso 真跑、AT_* 对账、crt1 修） |
| QEMU-063t | 已验证 | 2026-10-19 07:54 | MemRAS 初始化（1 MiB + MRPTR 哨兵）⇒ dbms 两档 pass；9 例诊断表落册；ISS-277→LLVM-108t |
| QEMU-060t | 已验证 | 2026-10-16 00:21 | dadao-m1 syscall 服务回退：helper.c.patch 还原 761dfa3；删 2 探针；关 ISS-221 |
| QEMU-061t | 已验证 | 2026-10-17 07:51 | aip.si 解码/语义：rbHA=PC+(imms18<<12)；L2 90/90、L3 161/161；关 ISS-233 |
| TESTCASES-046t | 已验证 | 2026-10-18 22:22 | Embench 两档 38/38 + 38/38 已跑；reviewer Accepted |
| TESTCASES-047t | 已验证 | 2026-10-18 22:22 | libc-test 两档：静态 305/0/9/23、动态 305/0/9/23（excluded 30）；reviewer Accepted |
| TESTCASES-045t | 已验证 | 2026-10-15 21:46 | 两套 runner + 首份度量：libc-test 7/9、llvm-test-suite 9/9；收窄为 P1 边界度量 |
| TESTCASES-044t | 已验证 | 2026-10-15 13:39 | libc-test 取源锁定：最新 commit b7ec4679（无 tag）、patchless |
| TESTCASES-048t | 已验证 | 2026-10-18 21:06 | llvm-test-suite A 类两档 193/2/0/27；050t 后投影 197/2/21/2；B 类未跑 |
| TESTCASES-051t | 已验证 | 2026-10-19 19:11 | lencod 预建 Output/ 两档 pass + 与参考 diff rc=0；ISS-272 改查 IR、ISS-274 三处 + 注入 4/5/6；证据 51/51 |
| TESTCASES-049t | 已验证 | 2026-10-18 21:06 | libc-test 动态档用户 TU 改 -fPIC（ISS-259②）：COPY 7 例 pass；305/0/9/23 |
| TESTCASES-050t | 已验证 | 2026-10-18 21:06 | 驱动四项：include/逐例超时/静态 builtins/siod excluded；048t 投影 197/2/21/2 |
| INTEG-036m | 里程碑 | 2026-10-19 20:23 | M8 收口：三套两档如实分类 + 失败逐条归因；P4 不作（ADR-0025 D7）；项目 M8 达成 |
| LLVM-108t | 已验证 | 2026-10-19 20:18 | lemon 定性 = 语料 UB（`lemon.c:334` 无原型 ⇒ 实参 int 对形参指针，C11 6.5.2.2p6）；不改语料/实现，仅改 048t reason 归因 |
| LLVM-115t | 已验证 | 2026-10-19 19:12 | picolibc `__atold_engine` 接入：删 meson 过滤条目（2→1）；build/tests rc=0、pass 18/blocked 0、047t 5 例两档 pass、探针 11/11 |
| LLVM-105t | 已验证 | 2026-10-19 07:54 | vector SetCC 补齐（`WidenVecRes_LOAD` 断言）+ wchar_t 改有符号；两例编译 rc=0、lit 103/103 |
| LLVM-101t | 已验证 | 2026-10-18 22:00 | 可变参聚合 union semun + shmat 指针返回 bank 两缺陷；reviewer Accepted |
| LLVM-109t | 已验证 | 2026-10-19 18:50 | `CommentString=@@`/`SeparatorString=;`；101 文件 3684 行迁移 + 工具同步；补丁 181；组件 4 补丁漏项收口 |
| LLVM-114t | 已验证 | 2026-10-19 18:59 | f128 math libcall 补齐（floor/rint/round/trunc/log + latent sqrt/fma）；解 build-picolibc 余 12 个 libm/ld TU（ISS-283） |
| LLVM-102t | 已验证 | 2026-10-19 19:35 | brind 间接分支 + 变参三游标 ABI + D4 整组分配；安装根复验 112/112 + 11/11 注入、与基线一致、无缺陷 |
| LLVM-103t | 已验证 | 2026-10-18 21:06 | flog libcall 补齐：LOG_F64/LOG10_F64 注册；CoMD 两档 pass；patch 173 |
| LLVM-094t | 已验证 | 2026-10-17 07:51 | LLVM/LLD PIC+动态：ET_DYN/.dynamic/仅 gnu.hash/rela.dyn+plt；静态零回归 |
| LLVM-099t | 已验证 | 2026-10-18 22:22 | i64 rotl/rotr ISel 展开；reviewer Accepted |
| LLVM-106t | 已验证 | 2026-10-19 19:35 | long double=binary128 全链：f128 三宏/21 libcall/高半在偶号/栈 16B；安装根复验一致、无缺陷 |
| LLVM-112t | 已验证 | 2026-10-19 18:50 | SP 对齐 16 B 实现+全链复验：Align(16)、crt1/musl/setjmp 核对、探针 8 项、install-host、L2/L3、三套两档 |
| LLVM-097t | 已验证 | 2026-10-18 22:00 | i64 bswap 改 Expand：五档 rc=0、端序 oracle 7/7；reviewer Accepted |
| LLVM-098t | 已验证 | 2026-10-18 22:22 | -fPIC 下 .rodata 仍发 ABS48（build-musl-shared EXIT=2）；诊断完成，reviewer Accepted |
| LLVM-113t | 已验证 | 2026-10-19 18:59 | i128↔f128 四转换 libcall 补齐（floattitf/floatuntitf/fixtfti/fixunstfti）；解 build-picolibc strtold 缺口（ISS-283） |
| LLVM-096t | 已验证 | 2026-10-18 22:00 | P2 A1 llvm 面 4 阻塞已解（裸 -shared/PIC 表/stackrestore）；reviewer Accepted |
| LLVM-095t | 已验证 | 2026-10-17 07:51 | PCREL_HI/LO=14/15、NUM=16：rela.si 配对、PLT 12 B、GOT 2 条；①–⑤ 验收 |
| LLVM-093t | 已验证 | 2026-10-15 13:49 | llvm-test-suite 23.1.3 取源入锁（tag ⇒ 2919e551）；baseline 待 musl 跑通 |
| LLVM-107t | 已验证 | 2026-10-19 07:54 | i32 窄返回 callee canonical 化：`classifyReturnType` 对 <64 位整型统一 `getExtend`；探针修前 2 FAIL→8/8、lit 34/34 |
| LLVM-110t | 已验证 | 2026-10-19 18:50 | FP 回归 rb2（无条件保留）+ rb63 普通 callee-saved；删 FP 专用槽；setjmp 端口加 rb2 槽；探针 6 项 |
| LLVM-111t | 已验证 | 2026-10-19 18:50 | 16 B 栈对齐补齐（f128/2 块 RD 组）：caller/callee/va_arg 同规则取整；8 B 基线不变；ISS-275 落点 |
| LLVM-092t | 已验证 | 2026-10-15 15:07 | llvm changelog 历史补录：机械枚举表内=95、多集空；三处口径同步 |
| LLVM-091t | 已验证 | 2026-10-14 17:34 | llvm-project 升 23.1.3：63 commits/172 files；71 补丁零冲突；L1/L2 无回归 |
| SPEC-142t | 已验证 | 2026-10-15 10:19 | rev.{o,t,w,b} 落地：4 条 orri + encode_onehot；trans_* 231/231 |
| SPEC-145t | 已验证 | 2026-10-17 07:51 | aip.si（原 rela.si）恢复：riii/0x5A；opcodes 234→235；L1/L2/L3 绿 |
| SPEC-140t | 已验证 | 2026-10-14 11:22 | 查证 musl TLS/TP 硬依赖（源码 file:line 取证）⇒ TLS 纳入 M8 |
| SPEC-151t | 已验证 | 2026-10-19 19:11 | SP 对齐 8→16 B 规范面：DADAO-21 §3.2.4、contract-abi §2/§4.8/§4.9、abi.yaml、只读锁；ADR-0018 C9 D3 已落 |
| SPEC-150t | 已验证 | 2026-10-19 19:11 | 帧指针回归 rb2（无条件保留、删 rbfp/rbgp）；rb63 连续 callee-saved；contract/abi.yaml/锁同步 |
| SPEC-139t | 已验证 | 2026-10-14 18:12 | 动态链接 ABI 契约：8 类型定号、GOT/PLT/TLS/PT_INTERP 口径；表 A 九项裁定 |
| SPEC-149t | 已验证 | 2026-10-19 19:11 | 上游只读册汇编示例注释 `;`→`@@`：11 册 298 行；C 分号不动；只读锁重算 |
| SPEC-138t | 已验证 | 2026-10-14 10:45 | syscall 契约：rd15 号、trap cfxha/umon、参数 rd8、errno=rd8 负值、AUDIT_ARCH=BE64 |
| SPEC-147t | 已验证 | 2026-10-19 20:18 | 注释符 `;`→`@@`、`;` 改语句分隔符：§2.2+示例+变更记录+`contract-asm` 0.5.3+只读锁重算；实现/回归证据 = LLVM-109t |
| SPEC-143t | 已验证 | 2026-10-15 12:51 | ctlz/cttz/ctpop 落地：3 条 orri（opx 011-101/110/111）；trans_* 234/234 |
| SPEC-144t | 已验证 | 2026-10-16 01:02 | DADAO-0628 对照：6 项×5 列、72 条 path:line；结论=仅工程流程可借鉴 |
| INFRA-084t | 已验证 | 2026-10-15 17:31 | 4 组件 changelog 表格→列表+里程碑分节；122/122 摘要无损；新增形态门控 |
| INFRA-087t | 已验证 | 2026-10-18 22:00 | strptime %s 语义归属与分类订正（以 musl 为准）；reviewer Accepted |
| INFRA-078t | 已验证 | 2026-10-14 19:27 | compiler-rt 预研：126 缺符号、13 核源编不过、7 接入点；ADR-0027 提案 |
| INFRA-086t | 已验证 | 2026-10-18 22:00 | 收口门控三条（milestone 册 / pending 标记 / 重定位表一致）；reviewer Accepted |
| INFRA-080t | 已验证 | 2026-10-15 15:46 | 门控补齐：knowledge 小节互指 + issues closed⇒resolved_by；并入 L1 |
| INFRA-079t | 已验证 | 2026-10-17 23:56 | compiler-rt builtins 全量：147 成员/14 libcall + 独立库 + driver 接线；L2 零回归 |
| INFRA-091t | 已验证 | 2026-10-18 20:57 | milestones 体例改造 + L1 门控 check-milestones-fresh（五断言 + self-test） |
| INFRA-088t | 已验证 | 2026-10-18 20:57 | driver 默认接 compiler-rt（ISS-262①）：RLT_CompilerRT 覆写；实现完成待验收 |
| INFRA-090t | 已验证 | 2026-10-19 07:54 | musl bits/float.h 换 binary128：12 宏与 aarch64 逐字、_l 零改；047t 5 例两档 5/5；ISS-250 closed |
| INFRA-073t | 已验证 | 2026-10-13 10:33 | Chipyard 1.14.0 预研：锁方案/镜像测速/成本/复用清单；只探测未下载 |
| INFRA-076t | 已验证 | 2026-10-15 09:23 | musl 1.2.6 取源入锁（v1.2.6 / 9fa28ece / patchless）；libc-test 定源 |
| INFRA-071t | 已验证 | 2026-10-15 00:04 | 11 份 contract-*.md 迁入 .tao/contracts/ + check-contracts-dir 白名单；裁定①a②a③a |
| INFRA-085t | 已验证 | 2026-10-17 13:37 | 动态链接 P2 能编：A1/B1/C1 通过，libc.so + PT_INTERP 静态可核；D2 推 M9 |
| INFRA-089t | 已验证 | 2026-10-18 20:57 | musl sigsetjmp：新增 dadao/sigsetjmp.s；setjmp blocked→pass；patch 174 |
| INFRA-075t | 已验证 | 2026-10-14 10:47 | Linux 7.2.10 取源验签入锁（TUNA；sha256 一致；commit 7b20d05f；patchless） |
| INFRA-083t | 已验证 | 2026-10-15 16:18 | .cache/embench-iot 非裸 checkout 清理；.cache 恢复只放裸仓库 |
| INFRA-094t | 已验证 | 2026-10-19 19:12 | 修 L2/L3 两红：ir-lli 5 个 lit CodeGen 入 exclude（no-value-entry）；authoritative 补 6 个真跑目录+latest |
| INFRA-093t | 已验证 | 2026-10-19 10:31 | 三驱动 `--json-out` 必填 + 独立 run 目录三件套 + L1 `check-run-artifacts`（A1–A3/self-test/注入）；`Process-08` 规范 |
| INFRA-082t | 已验证 | 2026-10-15 20:50 | musl 静态最小集 P1：arch/dadao + crt + syscall + TLS(TP=rb3)；hello/exit E2E 通 |
| INFRA-092t | 已验证 | 2026-10-18 20:57 | musl 封装 va_arg 类型面：syscall()/fcntl()/getrlimit 按三 bank 取型；fcntl 两档 pass、10/10；补丁 177→180 |
| INFRA-074t | 已验证 | 2026-10-14 00:09 | Chipyard 参考平台跑通 P1–P4（RocketConfig Verilator + 裸机 hello）；pk 未通 |

## 3. MEMORY 摘录（M8 时期，0 行）

> `MEMORY.md` 自 `INFRA-062t` 起为**纯指针页**，不承载进度事实 ⇒ 本里程碑无纯 M8 进度行可搬；M8 指针见 §4。

## 4. 指针

- 里程碑定义/达成：`.tao/knowledge/milestones.md`（「M8」段 + 「M8 状态快照（2026-10-19 收口）」）
- 里程碑回顾：本目录 `m8-retrospective.md`
- 已关 issue 快照：本目录 `issues-closed.md`（52 条）
- 遗留台账：`.tao/knowledge/issues.yaml`（open 项）/ `.tao/knowledge/lessons.md`（教训）
- 任务流水（之后）：`.tao/knowledge/milestones.md`「任务流水」（未归档项）

> **跨文件引用说明**：本归档**未更新**历史引用；凡引用原 `.tao/tasks/**/M8 任务书` 或 `milestones.md` M8 流水行者，其内容现位于本目录。
