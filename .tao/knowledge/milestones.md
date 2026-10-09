# 项目里程碑

> 只承载**当前进度**；历史见 `.tao/archive/M<1..5>/m<i>-retrospective.md`。

## 任务流水（仅当前里程碑 M6，完整表：含所有已规划任务）

| 任务 | 状态 | 开始 | 结束 | 说明 |
| --- | --- | --- | --- | --- |
| `INTEG-023k` | 已验证 | — | — | M6 启动与分解（20 项内涵 + 12 条 LLVM 欠账逐条裁定落纸；`/plan` 通过） |
| `INTEG-024t` | 已验证 | 10-09 00:00 | 10-09 00:05 | issues 台账按性质分流（移出 15 = 规划① 7 + 阻塞/待裁定②③ 8；保留 24 真 issue） |
| `INTEG-025t` | 待开始 | — | — | M6 E2E + 门控收口（`test-m6`） |
| `INTEG-026m` | 待开始 | — | — | M6 integ 里程碑（整体收敛点） |
| `INFRA-050t` | 已验证 | 10-08 23:49 | 10-09 07:09 | LLVM 一次构建（`DADAO;X86` + `clang;lld`）+ 双落点；曾中断，半成品已保命续用 |
| `INFRA-051t` | 待开始 | — | — | Embench 组件接入（组件化 + `enabled` 翻转；ADR-0022 已定上游 commit） |
| `INFRA-052m` | 待开始 | — | — | M6 infra 里程碑 |
| `INFRA-053t` | 已验证 | — | 10-09 20:06 | `ISS-172` 修复：`atomic-install`（`cp -aL …tmp.$$ && mv -f`，`rename(2)` 原子）；串行 ×2 与并行均 0；同 worktree 并发 gate 仍不支持〔已声明〕 |
| `SPEC-122t` | 已验证 | 10-08 23:54 | 10-08 23:57 | M6 ADR 决策落地（`ADR-0018 §C7 D4` 四形态修订 + `ADR-0021`/`0022` 新建；组合加载 ADR 不立） |
| `SPEC-123t` | 已验证 | 10-09 07:21 | 10-09 07:53 | reloc 正文（`REL12`(rb0/PC 相对 `S+A−P`)/`ABS12`(rb1–rb63 `S+A`)、`NUM`=6 + `ABS48` 数据 8B）+ `Toolchain-01 §6.1` `set.fo` 口径 + 锁 |
| `SPEC-124t` | 已验证 | 10-09 08:17 | 10-09 08:22 | 调用约定契约收口（`§6` 三 `[OPEN]` 消解）+ 改册（返回寄存器 `rd31→rd8/rb8/rf8`、声明序递增、每 bank K=8、超者 sret 经 rb16）+ 锁 |
| `SPEC-125m` | 待开始 | — | — | M6 spec 里程碑 |
| `SPEC-126t` | 已验证 | 10-09 08:37 | 10-09 08:48 | 系统调用/半托管返回寄存器 `rd31 → rd8`（`DADAO-21/22/23` + `Machine-01`）+ 两合约同步 + 锁；**入参 `rd15`/参数区不动** |
| `SPEC-127t` | 已验证 | 10-09 10:06 | 10-09 10:17 | 聚合传参收口（**全部聚合含 HFA/HPA 槽位上限 4→8 = 64 B；`>64 B` ⇒ 间接指针**）+ `DADAO-21` 与锁同步 + `contract-abi §6.4` |
| `SPEC-128t` | 已验证 | — | 10-09 12:12 | ABI 寄存器布局重排（spec/契约侧）：RD `rd2–rd3` reserved〔调试/测试保留〕/`rd4–rd7` caller-saved；RB `rb2`=GP/`rb3`=TP/`rb4–rb7` caller-saved/`rb32–rb62` callee saved/`rb63`=FP 条件占用〔callee-saved〕；改 `DADAO-21`+锁+`contract-abi`+`contracts/abi.yaml`+就地修订 `ADR-0018 C7 D6`；**不立 ADR**；不含实现。**册+契约+ADR 修订；RF 表未改；RF 实现放开归 `LLVM-066t`** |
| `SPEC-129t` | 已验证 | — | 10-09 13:17 | `Toolchain-01` 旧口径消除 + §11/§12 移位（`ISS-163` 收口，用户 2026-10-09 裁定「消除写死」+「台账 + 门控清单，ADR 只指向」）：改 `§5`/`§11`/`§13` 三处旧口径（`crrr`/`ciii`→`m1`、仅 `crii` 仍 `excluded`）；**消除写死**（计数指向 `contracts/opcodes.yaml`/`contract-asm-list.md`）；§11→既有投影 `contract-asm.md §11`、§12→既有门控说明（门控名）；`ADR-0013` 只加指向；改只读册 `Toolchain-01`+锁 `sha256` 同步；**不改实现**。**（追加 2026-10-09，用户裁定 8）并入 `spec/DADAO-22` 示例 5 处 `rb3` 当 scratch → 真临时寄存器（`rb8`/`rb9`）+ `DADAO-22` 锁 `sha256` 同步**（同一类「册旧口径同步」）；**遗留①：`contract-asm §11` 状态结论疑似已实现，未擅改、如实登记** |
| `LLVM-062t` | 已验证 | — | 10-09 12:16 | 整数完整调用约定（返回 `rd8`/`rb8`/`rf8` + K=8 + 聚合 `≤64 B`/`>64 B` byval + `sret` 经 `rb16` + 变参 + 间接调用）+ 六条欠账（`043/045/047/148/159/162`）；`ISS-108` 按用户裁定推迟 M7 |
| `LLVM-063t` | 已验证 | — | 10-09 14:59 | DADAO clang target + driver/sysroot（**钉子①**）：clang target 打通（`--print-targets` 含 `dadao`／DL 与后端逐字符一致／E2E `clang→llvm-mc`+`ld.lld`→QEMU `exit=42`／`make check` lit 69/69／`series` 71 条）；遗留：`DADAOABIInfo` 最小首版（HFA/HPA 留 `LLVM-066t`）、sysroot resource-dir `include/` 暂缺 |
| `LLVM-064t` | 已验证 | — | 10-09 16:25 | 大帧寻址四形态（代价驱动；实测三形态：form1 `isInt<12>`/form2 `isInt<18>`/form3 else）+ `mem*` 内建（`MaxStoresPerMem*=16`，切换点 **128 B**〔16×8〕、132 B 起 libcall；自写运行时无 libc）+ `rb63` 批量排除（注释精确化：`contract-isa §15.1` `start+immu6≤64`/FP 专用槽）；`ISS-138` 关闭；>128K E2E QEMU **exit=8**；遗留：无 |
| `LLVM-065t` | 待开始 | — | — | lld reloc 完善（`REL12`/`ABS12` + `FK_Data_*` 静默 0 + `ABS48` 数据表示） |
| `LLVM-066t` | 已验证 | — | 10-09 17:51 | FP/RF codegen（**排整数之后**）：硬件 FP lowering（`fadd/fsub/fmul/fdiv/fsqrt`/转换/比较/`select_cc` 一对一映射）+ FP ABI（参数 `rf16–rf31`／返回 `rf8–rf15`／HFA `{rf8,rf9}`）+ RF 实现侧放开（`rf1–rf7` caller-saved 可分配、`rf0`=FCSR 保留、`rf32–rf63` callee-saved 保存恢复）+ 软浮点**不引 compiler-rt**（核心 FP 无 libcall）；**遗留能力缺口**：`fabs`/`frem`/`fma`/FP 分类/FP↔RB 拷贝 = 显式失败（见「当前进度」） |
| `LLVM-067m` | 待开始 | — | — | M6 llvm 里程碑 |
| `LLVM-068t` | 已验证 | — | 10-09 12:49 | ABI 寄存器重排后端实现：寄存器类（`rd4–rd7`/`rb4–rb7` caller-saved）+ `getReservedRegs`（`rd2–rd3`、`rb2`=GP、`rb3`=TP 保留；**`rb63` 条件保留**）+ `getFrameRegister = hasFP ? rb63 : rb1` + `FrameLowering`（FP=`rb63`、批量保存排除 FP）+ `LLVM-062t` RegMask 同步 + lit 期望；重建；排 `LLVM-063t` 前、与 `LLVM-064t` 串行。**RegMask 核对一致无需改；风险：批量保存排除 FP(rb63) 仅注释未强制 ⇒ 移交 `LLVM-064t`** |
| `QEMU-052t` | 已验证 | 10-09 08:54 | 10-09 10:50 | 改走 `load_elf()`（**钉子②**）+ 调用前薄校验（`e_flags`/`ET_EXEC` + 逐段一致性/范围）；**用户裁定 D**：允许集合 = **仅旧 RAM 段**（`0xffff_0000_0000`/16 MiB），落 ROM 窗口段 ⇒ 加载期非零退出；**RAM@0 未纳入**（留 `QEMU-053t` step2）；`-bios`+ELF 组合不需要 |
| `QEMU-053t` | 已验证 | — | 10-09 18:58 | RAM@0 step2（`ISS-165`）收口 + `ISS-169` 探针迁移。`ISS-165` step2：删旧 RAM 段（`0xffff_0000_0000`）+ 删 exit-port + ~60 文件迁 `0` + `check-interface` 收紧 + `Machine-01` 与锁同步（用户预授权）；`ISS-169`：7 探针 → `SYS_EXIT`（`006t`/`008t`/`010t`/`012t`/`013t`/`030t` rc=0；`009t` 属 OBSOLETE 语义 rc=1）。提交 `2f54df9`（含 `5898601`）；`master` 单提交落地 |
| `QEMU-054m` | 待开始 | — | — | M6 qemu 里程碑 |
| `QEMU-055t` | 已验证 | — | 10-09 20:42 | 半托管/SEE 返回寄存器 `rd31 → rd8`（实现 `DADAO_SEMI_RET_REG=8` + `046t` 探针/期望重派生 + **域 B（`m5_semi_write.s`/`expected.yaml`）随本任务收口**）；`test-semihost` 10/10 |
| `TESTCASES-036t` | 已验证 | — | 10-09 21:34 | M6 新能力向量（L1 编码向量 + L3 执行向量：raw-bin 7/7 + ELF 1/1）；**独立 oracle**（`validate_m6_vectors.py`，无 `subprocess`）；`check-lit` **73→74 PASS（+1）**；遗留：REL12/ABS12（`ld/st` 符号偏移）L1+L3 待 `LLVM-065t`〔`UNSUPPORTED` 暂缓〕、`make test-m6` 接线归 `INTEG-025t` |
| `TESTCASES-037t` | 已验证 | — | 10-09 21:59 | lit 量产：骨架生成器**机械遍历 `contracts/opcodes.yaml` 全部记录**（现行统计 227 = 217 正例 + 10 反例）、期望**机械派生**（禁反填）、**幂等**；**分层**——快档 `gen-fast.s` 入 `make check`（`check-lit` 76/75/1）、全量档 `MC/DADAO-gen/` **opt-in** `check-lit-full`；`make check-lit` 耗时受控；遗留：`DADAO-gen` 完整性仅 opt-in 校验〔M7 分层时定层〕 |
| `TESTCASES-038t` | 已验证 | — | 10-09 22:21 | 上游 IR 编译层 + host `lli` × DADAO(QEMU) **值级对拍**；现场统计：编译 19/19、对拍 19/19 matched、`on-disk 41 / include 19 / exclude 22`；**只做值级**、端序/内存布局类排除、**不作执行语义判据**；遗留：驱动 **opt-in**，接线归 `INTEG-025t`；值通道 = 退出码低 8 位 |
| `TESTCASES-039t` | 待开始 | — | — | Embench 接入（**钉子③**） |
| `TESTCASES-040m` | 待开始 | — | — | M6 testcases 里程碑 |
| `TESTCASES-041t` | 待开始 | — | — | 返回寄存器 `rd8` 收口——受影响向量/期望值重派生重验（域A 函数返回 / 域B 半托管返回**分别验收**） |

> **本表即 M6 全部已规划任务**（唯一真源）：每行对应 `.tao/tasks/<模块>/<任务>-*.md` 一份任务书，**状态取自该任务书 `**状态**` 字段**（可机读复核，**不在本表写死计数**）；未开始项以 `—` 占位。

> （时间来源：`INTEG-024t` = 制品 mtime（`.work/INTEG-024t` 创建 00:00 / reviewer Accepted 00:05）；`SPEC-123t` = 锁 mtime 07:21 / 任务书末次写入 07:53；`SPEC-124t`/`SPEC-126t`/`SPEC-127t` = 任务书与台账落盘 mtime；`QEMU-052t` 开始 = 08:54（opencode 日志首个相关进程时间戳）/ 结束 = 10:50（reviewer 判决写入任务书 mtime 10:50:06；reviewer 末次门控 `check.log` 10:49）；`LLVM-068t` 结束 = 12:49（reviewer 证据脚本重跑日志 `/tmp/opencode/LLVM-068t-review/run.log` mtime 12:49:43）；`SPEC-129t` 结束 = 13:17（reviewer 独立注入闭环重建日志 `/tmp/opencode/SPEC-129t-review/restore-test.log` mtime 13:17:34）；`LLVM-063t` 结束 = 14:59（reviewer 判决写入任务书 mtime 14:59:48）；`LLVM-064t` 结束 = 16:25（reviewer 判决写入任务书 mtime 16:25:23）；`LLVM-066t` 结束 = 17:51（reviewer 判决写入任务书 mtime 17:51:20）；`QEMU-053t` 结束 = 18:58（reviewer 判决写入任务书 mtime 18:58:05）；`INFRA-053t` 结束 = 20:06（reviewer 判决写入任务书 mtime 20:06:30）；`QEMU-055t` 结束 = 20:42（reviewer 末次门控日志 `.work/log/qemu/QEMU-055t-review-*.log` mtime 20:42）；`TESTCASES-036t` 结束 = 21:34（reviewer 第 3 轮判决写入任务书 mtime 21:34:53）；`TESTCASES-037t` 结束 = 21:59（reviewer 判决写入任务书 mtime 21:59:00）；`TESTCASES-038t` 结束 = 22:21（reviewer 判决写入任务书 mtime 22:21:47）。）

> 开始/结束由**主会话**在 `/dispatch`／`/complete` 时填写（格式 **`MM-DD hh:mm`**，不带年份）；只填**可考证**时间，**禁编造**。

## 当前进度
- **历史瑕疵登记（已解决）**：提交 `815d854` 的**内容 = `SPEC-122t`**、**消息曾误写为 `INFRA-050t: …`**；**用户 2026-10-09 批准修正**，已以 `commit --amend` 改写为 `eb10259`（**只改消息、内容未变**：对 `backup/pre-push-squash` 与旧 `origin/master` 两级校验均 0 行差异），并 `--force-with-lease` 推送（**由用户本人执行**，因其 `permission.bash` 策略 `git push --force*` = `deny`）。备份分支：`backup/pre-push-squash`、`backup/before-msgfix`、`backup/pre-msgfix2`。
- **WIP 入史登记（用户裁定）**：已推送历史中含 `5dfd311 WIP: QEMU-052t 候选实现（改走 load_elf()，门控全绿）+ 停下报告：契约 §6.1.2/ADR-0004 D2.3 三类加载期校验丢失，待用户裁定 A/B`——**保命提交**（子代理 `cancelled`、任务卡在裁定）。用户 2026-10-09 裁定「**选 b，保留现状**」⇒ **不改写已推送历史**；`QEMU-052t` 的最终交付提交叠加于其后。
- **SPEC-129t 双提交登记（用户可核）**：`82280d9`（内容）+ `98c2dbc`（收尾台账）**均已 push**、未 squash——主会话 squash 时 **base 写错**（应为父提交）且**用 `;` 无条件串接 push**（`lessons §8.25`）。按「已 push 的提交不得改写历史」**保留现状**；`SPEC-129t` 的交付内容不受影响（`git diff` 前后 = 0 行）。
- **每任务一分支工作流生效（用户 2026-10-09 裁定；`lessons §8.26`）**：`AGENTS.md`「提交分档」已落纸「每任务一分支」——开工前建分支（名 = 任务号前缀）、WIP/返工/reviewer 修改提交在该分支、完全确定后**一次性落地 `master`** 再删分支；**`master` 永不改写已推送历史**。落纸分支 **`INTEG-workflow`（从 `master` 拉，未 push）待主会话合并落地后删除**；**不追溯**既有历史（`SPEC-129t` 双提交 / `QEMU-052t` `WIP` 入史保留）。
- **里程碑**：M6（`INTEG-023k`「M6 启动与分解」）
- **`LLVM-066t` 遗留 FP 能力缺口（M7/后续候选，2026-10-09）**：FP lowering/ABI/RF 放开已交付（见上表），下列能力缺口均为**显式失败、非静默降级**（`report_fatal_error`/ISel crash/`Expand`-libcall，E2E 不涉及）：① `fabs`（双类型 `GPRF` 中裸 `rf0` 不可作 TableGen 操作数 ⇒ `Expand`）；② `frem`/`fmod`（ISA `forem` 为 IEEE remainder，与 LLVM `frem`=`fmod` 语义不同）；③ `fma`（无硬件指令 ⇒ `fmul+fadd`）；④ FP 分类（`ISD::IS_FPCLASS`；MC 层指令已有）；⑤ FP↔RB 跨 bank 拷贝（`copyPhysReg` 显式失败）。
- **`ISS-108` 提请用户裁定（`LLVM-062t`，2026-10-09）**：`LLVM-062t` reviewer 判 **Needs Revision**，唯一缺口 = `ISS-108`（`DADAOInstrInfo.td` **1502 行**、`DADAOAsmParser.cpp` **2349 行**，均 >1000 行）未拆分。**原裁定为「纳入（拆分）」，但现实已变**——两文件规模远超阈值，拆分是**侵入式重构**（`DADAOAsmParser.cpp` 为单一匿名类，需类外提为头文件）且属**非功能性**改动，风险/收益不匹配。⇒ **提请用户**在「**仍在本里程碑（M6）拆分**」/「**推迟到 M7，`LLVM-062t` 转 Accepted**」之间裁定；**不擅自决定**。其余验收项（返回 `rd8/rb8/rf8`+K=8、聚合 ≤64 B/`>64 B` byval、变参、间接调用、六条欠账 `043/045/047/148/159/162`、四门控、证据脚本 16/16 + 注入回绿、补丁纪律、`spec/`/`contracts/` 交集空）**均已通过**。当前 `LLVM-062t` 为本地 **WIP 提交（未 push）**。
- **`ISS-108` 挂账（用户裁定，2026-10-09）**：`ISS-108` 已由用户裁定**推迟 M7**（`DADAOInstrInfo.td` **1502 行** / `DADAOAsmParser.cpp` **2349 行**；**非功能性重构**）。⇒ `LLVM-062t` 唯一缺口移除、转 `Accepted`（提交 `d367bf6`）。
- **`ADR-0018 §C7 D6` 修订措辞复核（用户 2026-10-09）**：`SPEC-128t` 就地修订的 `ADR-0018 §C7 D6`（ABI 寄存器布局重排）措辞经用户复核，裁定「**照此保留**」（**无改动**）——**用户 2026-10-09 复核通过**。
- **规划中**：
  - **门控分层（用户 2026-10-09 裁定）——推迟到 M7**：三层 = **L1 完整性/可用性**（默认 `make check`，秒~几十秒）/ **L2 各模块功能代表集**（几十~几百秒）/ **L3 较完整**（几百~几千秒）+ **模块完整按需**；落地要点 = `check` 收缩为 L1（`check-qemu-semantics` 移出 + 新增 `check-qemu-smoke` 机械派生代表集）、每层须「能失败 + 结构断言」、触发点写 `AGENTS.md`（收尾跑 L2 / 里程碑跑 L3）；**第 0 步 = 逐门控计时**。细节指针：`.work/log/integ/gate-tiering-design.md`（**gitignored**，故本摘要自足）。
  - **M6 主题与范围（已裁定，2026-10-08；见 `INTEG-023k`）**：整数**完整调用约定** + **12 条 LLVM 欠账收口** + **ELF 加载**（改走 `load_elf()`，钉子②）+ **clang target**（仅 freestanding，钉子①）+ **Embench 接入**（钉子③）+ lit 量产 + `lli` 值级对拍；**不含** libc/OS/syscall、golden model、fuzz（后置 M7）；`ISS-003`（LR-SC）**M6 显式排除**
  - **M6 任务书**：逐项见上表（**计数不写死**，需时现场统计）；编号 `INTEG-023k/024t/025t/026m`、`INFRA-050t/051t/052m`、`SPEC-122t…128t/125m`、`LLVM-062t…068t/067m`、`QEMU-052t…055t/054m`、`TESTCASES-036t…041t/040m`；Wave 串行见 `INTEG-023k §C/§D`
  - **本轮新增裁定的连带影响（均已落纸）**：① 返回寄存器 `rd31→rd8/rb8/rf8`（K=8）⇒ `SPEC-124t` ✓ + 实现侧 `LLVM-062t`/`TESTCASES-041t`；② 系统调用/半托管返回 `rd31→rd8` ⇒ `SPEC-126t` ✓ + `QEMU-055t`/`TESTCASES-041t`；③ 聚合槽位 `4→8`（64 B）⇒ `SPEC-127t` ✓ + `LLVM-062t`〔整数〕/`LLVM-066t`〔HFA〕
  - **GP（`rbgp`）候选（M7/优化期，**M6 不做**——用户 2026-10-09 裁定）**：`rb2=rbgp` 现由 **M6 寄存器重排**（`SPEC-128t`）列为 **reserved（编译器不得分配）**（`contract-abi §1.3/§1.6`），后端**无** GP 机制（`rbgp` 仅出现在注释）。启用需：**小数据区**（`.sdata/.sbss` + 阈值）× **链接脚本聚到 `_gp`** × **启动设 `rb2=_gp`** × 后端 `getGlobalBaseReg`（MIPS 式，`%gp_rel`）；**reloc 已备**——我们新定的 **`ABS12`（基址 `rb1–rb63` 相对、`field=S+A`、字节）恰为 GP 相对所需**，且**访存偏移 ±2 KiB 正是小数据区的自然上限**（一次 `ld/st [rbgp,disp12]` 取代三条地址构造）。代价：**改变 `rb2` 的 ABI 语义**（独立裁定）；0628 参考未用 GP。依据：主会话分析（`ABS12`/四形态/访存偏移见 `contract-elf §2–§3`、`ADR-0018 §C7 D4`）。
   - **`GOLDEN-*` 里程碑候选（M7 起，用户 2026-10-09 裁定）**：为 **golden model（结果级 / FP 独立 oracle）另立** `golden` 模块专用里程碑（`GOLDEN-*`，**M7 起**）——承载 `ISS-019`（结果级 / FP 独立 oracle）、`ISS-026`（encoding `imm` 语义守卫依赖 golden）**二者整体**，以及 `ISS-081` **拆分后的 FP 独立 oracle 部分**（`ISS-081` 的 FP 向量 / harness RF 部分**归 M6**：`LLVM-066t`/`TESTCASES-036t`/`041t`）。**本候选仅登记归属，不在本轮立项/建任务书**（任务分解待 M7 规划）。
  - **Embench 接入（M6 待办）**：① ADR 已建（`ADR-0022`，上游选择 + 精确 commit）⇒ 翻 `manifests/components.lock.toml` 的 `enabled = true`（归 `INFRA-051t`）；② 建 `components/embench-iot/{patches/**,series,changelog.md}`；③ 工作树由 `make fetch` 生成到 `.work/source/embench-iot`
  - **`lessons.md` 瘦身**：下次里程碑归档时按新口径（新增条目 ≤3 行 + 指针，细节进 `.work/log/`；**不追溯重写**）瘦身（**行数/字头数现场统计、不写死**）
  - **`issues.yaml` 移入**（规划①，2026-10-08 `INTEG-024t`；原 `scope` 原样括注）：
    - `ISS-003`（原 `[M6]`）：**LR-SC 原子**（`SimRISC-12`，ISA 扩展整体 deferred）—— ① 未开始的能力（M6 显式排除）
    - `ISS-005`（原 `[M6]`）：**完整调用约定未交付部分**（变参 / 聚合传参返回 / 多返回值 / `sret` / 间接调用）—— ① 里程碑待办（M6 主题）
    - `ISS-006`（原 `[M6]`）：**ABI 5 项 `[OPEN]`**（rd1/rb3/rb4 callee-saved、窄返回值扩展、多返回值、red zone、帧指针省略）—— ① 里程碑待办（`contract-abi.md §6`；其中 3 项已由 `SPEC-124t` 消解）
    - `ISS-110`（原 `[llvm, M6]`）：**`cfxld`/`cfxst` + `crii` + `SPEC-075t` 别名表 uart2..30 缺口** —— ① 里程碑待办（`INTEG-022t` 边界拆分余项）
    - `ISS-165`（原 `[testcases, qemu, integ, M6]`）：**C1 step2（RAM@0 收口）** —— ① 里程碑待办（归 `QEMU-053t`）
    - `ISS-168`（原 `[qemu, integ, spec, M6]`）：**「`-bios` + ELF」组合加载 / 扩 `dadao_load_regions[]` / 组合加载 ADR** —— ① 里程碑待办（用户 2026-10-08 裁定；**已由「改走 `load_elf()`」取代**，`SPEC-122t` 记「不立 ADR」）【**已解决 2026-10-09**：组合加载不需要〔M5 裁定〕+ 扩白名单取消〔`QEMU-052t` 删 `dadao_load_regions[]`〕+ 组合加载 ADR 不立〔`SPEC-122t`〕】
    - `ISS-169`（原 `[qemu, testcases, M6]`）：**6 个 M1/M2 探针退出通道 `exit-port` → `SYS_EXIT`** —— ① 里程碑待办（归 `QEMU-053t`）
- **阻塞与待裁定**：8 项归属存疑（`ISS-019/026/047/074/081/163/164/167`；其中 `ISS-163`/`ISS-167` 涉改上游只读册，**须用户授权**）；M6 主题**已裁定**（2026-10-08，见 `INTEG-023k`）
  - **`issues.yaml` 移入**（阻塞②/待裁定③，2026-10-08 `INTEG-024t`；原 `scope` 原样括注；**待用户裁定**）：
    - `ISS-019`（原 `[golden, M5]`）：结果级 / **FP 独立 oracle**（golden model）—— ③ 归属未定 —— **待用户裁定**；选项 A 归 M6 / B 另立 `GOLDEN-*` 里程碑 / C 保留待规划 【**已裁定（用户 2026-10-09）**：选 **B** ⇒ golden（含 FP 独立 oracle）**另立 `GOLDEN-*` 专用里程碑（M7 起）**；见「规划中」`GOLDEN-*` 候选】
    - `ISS-026`（原 `[testcases, M5]`）：encoding `imm` **语义守卫依赖 golden** —— ③ 归属未定（同 `ISS-019`）—— **待用户裁定**；选项 A 归 M6 / B 另立 golden 里程碑 / C 保留待规划 【**已裁定（用户 2026-10-09）**：同 `ISS-019` ⇒ 随 golden 归 **`GOLDEN-*` 专用里程碑（M7 起）**】
    - `ISS-047`（原 `[llvm, M5]`）：`llvm-objdump -d` 需显式 `--triple`（`e_machine` 未映射到 dadao）—— ③ 归属存疑 —— **待用户裁定**；选项 A 归 M6「欠账收口」/ B 判为真 issue / C 保留待规划 【**已解决（用户 2026-10-09）**：**归 M6** 并标已解决——实测已修（`EM_DADAO→Triple::dadao`，见 `LLVM-062t` 欠账 `047` ✅）】
    - `ISS-074`（原 `[testcases, M5]`）：`cs.*` 条件赋值 **overlap 语义（C-27）**未指定 —— ③ 归属未定 —— **待用户裁定**；选项 A 归 M6 / B 随 FP（M7+）/ C 保留 【**挂账（用户 2026-10-09）**：**待实现时再定**——后端当前**不发** `cs.*`；待实现/发射时定 overlap 语义（含改上游册需授权）】
    - `ISS-081`（原 `[spec, golden, testcases, llvm, qemu, integ, M5]`）：**FP 后续衔接点** —— ③ 归属未定（FP 不在 M6 显式范围）—— **待用户裁定**；选项 A 归 M6 / B 归 M7+ / C 保留 【**已裁定（用户 2026-10-09，按性质拆分）**：**FP 向量 / harness RF 归 M6**（`LLVM-066t`/`TESTCASES-036t`/`041t`）；**FP 独立 oracle 随 golden 归 `GOLDEN-*`（M7 起）**】
    - `ISS-163`（原 `[spec, M5]`）：`Toolchain-01 §5/§11/§13` **旧口径与 `contracts/opcodes.yaml` 不符** —— ②③ 须**用户授权**方可收口上游只读册（2026-10-08 已裁定「暂登记遗留」）—— **待用户裁定** 【**已裁定：立任务收口** ⇒ `SPEC-129t`（用户 2026-10-09：「消除写死」+「台账 + 门控清单，ADR 只指向（推荐）」；授权改 `Toolchain-01` + 同步锁）】 【**已解决 2026-10-09**：`SPEC-129t` 收口——`Toolchain-01 §5/§11/§13` 旧口径改对（`crrr`/`ciii`→`m1`、仅 `crii` 仍 `excluded`；cfx 4 条→`m1`）+ 写死计数消除 + §11/§12 移位 + 锁同步；reviewer `Accepted`（提交 `82280d9`）】
    - `ISS-164`（原 `[qemu, M5]`）：cfx mask 与 `excp_cause_mask` **屏蔽路径当前不可观测** —— ② 须后续实现带可屏蔽 cause 的 cfx 后补验 —— **待用户裁定** 【**保留跟踪（用户 2026-10-09）**：**不入 M6**；待带可屏蔽 cause 的 cfx / 特权层里程碑补验】
    - `ISS-167`（原 `[spec, qemu, M5]`）：`DADAO-12 §5` 异常退出流程 **prose 与伪代码张力** —— ②③ 须**用户授权**方可收口上游只读册 —— **待用户裁定** 【**挂账**（用户 2026-10-09：「现在和异常退出流程没有关系，需要的时候，提出问题，我来判定」）】
