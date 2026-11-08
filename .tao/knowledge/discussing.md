# 讨论项

> 只记**当前未决/待裁定**事项；任务流水看 `.tao/knowledge/milestones.md`，历史与已落实项不在此保留。

## 2026-11-06 golden / Sail 定位（结论，待落流程）

- **前提**：SimRISC/DADAO 持续变更、不留历史包袱；内核/FPGA 阶段同样如此。工具按“高频变更”取舍，不按“稳定期资产”取舍。
- **Sail：搁置**。形式化模型是稳定期资产；0628 实测只做 6–8 条切片、其余 `SKIP-unsupported`；“权威性”在自有扩展上不成立。重启触发条件：ISA 冻结 / 流片前 / 需要 RTL tandem 或定理证明。
- **golden：不做全量第四实现**。只保留三个窄用途：① 歧义探测（未明处 `SpecificationGap`/`UNSPECIFIED` 显式阻断，不猜默认值）；② 精确计算（FP/位宽/舍入）；③ 裁定回归（把用户裁定固化成向量/断言，防漂移）。PR#5 的全量模型 + 万行 `INSTRUCTION_REFERENCE.md` 属稳定期资产，不并入日常门控。
- **裁判只能是用户**：工具只做“发现歧义 + 举证（各解释下的结果/依据）+ 回归”，不做拍板；差分/fuzz 的分歧须聚类归因后再上报，不把原始分歧直接丢给用户。
- **投资顺序**：规范一致性/歧义探测 > 差分 fuzz + legality 矩阵 > 精确 FP > 轻量边界生成；解释器只在“需要算给看”时写。
- **三条禁忌**：向量里写未记录来源的期望值；模型对未明处选默认值；把“两个实现一致”当正确（多数表决 ≠ 真值）。
- **依据（0628 / PR#5）**：0628 四方差分（interp/QEMU/gem5/Sail）AGREE 198 / DIVERGE 0，`check-golden` 故意不进 `make check`；golden 仅整数 87 条，语义取自 `spec.md`（与 ADR-0009“wiki 直派”的要求不一致）。PR#5：标量 + 66 条 FP，回放 730（173/500/0/57），49 单测，`check-golden` 进 L1；无差分运行器，FP 向量只有 `scaleb`。
- **待落地**：① “歧义登记 → 用户裁定 → ADR/向量 → 回归”的流程；② 是否把“歧义探测”并入现有 spec 门控；③ chipyard 是否已有 DADAO 核（决定 RTL 对拍是否成为主差分）。

## 2026-11-05 异常/中断入口模型（A）

- **执行过程中的同步异常和异步中断，先进入当前运行模式的 monitor**。
- monitor 是**第一处理者**（A，非中转）：
  - 拥有异步来源屏蔽、pending、分发决策；
  - 可自行处理并 `escape`，也可 `trap` 到源 cfx；
  - monitor 处理期间的新事件置 pending，不嵌套 monitor。
- 显式指令仍直接到 cfx：`trap cfx` → 目标 cfx（`CFXTRAP`）；`escape cfx` → 当前 cfx（`CFXESC`）。
- 第 4 项已定（monitor 第一处理者；处理期间 pending、不嵌套）。
- 第 3 项选 **A1**：删除 `inner_cfx_mask`/`switch_cfx_mask`/`excp_prev_cfx_mask`/`excp_cause_mask`/`excp_cause_nonmaskable`；编号保留为 reserved，不重排；monitor 用 `cfx_intr_mask` + `excp_pending`；`global_cfx_intr_mask` 保留（monitor 全局来源掩码，trap 保存/escape 恢复）。`SPEC-186t` 只改使用模型，寄存器定义删除归 `SPEC-188t`。
- 第 2 项选 **B**：`SPEC-186t` 只改 §5.2+§1；`§2.2.6`/`§3.6`/`§4.5` + `DADAO-22 §5.3` + `contract-see` 由 `SPEC-189t` 收口；过渡期 `ISS-344`。
- 执行顺序：`SPEC-186t → SPEC-188t → SPEC-189t → SPEC-187t（退出码）`；188t/189t 同改 DADAO-12，严格串行。

## 当前任务状态（2026-11-06 夜）

> 只列未收口任务；已完成项看 `milestones.md`。

- `GEM5-023t`（进行中）：SE 文件 I/O + 时钟。
- `GEM5-024t`（待开始，依赖 023t）：SE 信号 + 资源限制 + 进程信息。
- `GEM5-025t`（待开始，依赖 024t）：SE IPC/多进程（pipe2/socket、execve/fork/wait4）。
- `GEM5-026t`（进行中）：SE 线程/futex/robust + 每线程 TLS 验收切片（`rb3` 已在 spec 定义、TLS 由 musl 完成）。
- **环境缺口（2026-11-07 裁定）**：`popen`/`spawn`/`vfork`/`execle-env`/`unix-smail` 5 例需要 guest 根内的 DADAO `/bin/sh`、`echo`；SE 返回 `ENOEXEC` 正确。QEMU 侧「通过」是执行宿主 x86-64 二进制（`strace` 证实），**非同架构 baseline**，不计 gem5 能力欠账；不采纳宿主原生执行旁路。DADAO shell/guest root 与「QEMU static 档补 `-L`」登记为 backlog。
- `GEM5-027t`（待开始，依赖 026t）：动态装载器（`ET_EXEC+PT_INTERP` / auxv / `interp-dir`+`redirect`）。
- `GEM5-028t`（待开始，依赖 027t）：文件映射 `mmap` + ldso 装载 DSO + 解释器窗口约束。
- `TESTCASES-103t`（待开始，依赖 023t）：SE 基线预算 120s→按套件 600s，`timeout` 单列。
- `TESTCASES-104t`（待开始，依赖 027t/028t）：SE 动态档驱动 + QEMU dynamic 基线刷新 + 全量对照。
- `INTEG-059t`（待开始，依赖 023t–028t + 103t/104t）：G3 完整 tset 双向一致性 + 矩阵重生成。
- `INTEG-060t`（待开始，依赖 026t）：gem5 SE 参数 bank 三方 argmask 门控 + 路径解析探针（防 rd/rb 混用、dirfd/redirect 拼接错误）。
- `GEM5-029t`（待开始，依赖 026t）：SE syscall 语义对齐（QEMU 已实现项）。
- `GEM5-030t`（待开始，依赖 029t）：SE `mprotect` 真权限 + `RLIMIT_AS/STACK` 强制。
- **口径（2026-11-07 用户）**：QEMU 自己实现的 syscall，gem5 必须有一份等价实现；此类差异不是「可接受限制」，要上报并修复。
- M11 `m` 册：G3 收口后另立。

**本轮范围裁定（architect，按调研结论；可推翻）**：

- `mprotect` 真权限不纳入动态线（保持已登记限制，另立任务再评估）
- 主程序 `-pie`/`ET_DYN` 不支持；动态驱动用非 PIE `ET_EXEC+PT_INTERP`
- 动态语料按 `ADR-0048 D4` 全量（libc-test 337 + llvm-ts 214 + embench 38）
- llvm-ts scope B/C 的两个 TLS 例不纳入（现有 scope A 口径不变）
- 单线程 TLS 由 musl 完成、gem5 0 改动，作为 `GEM5-026t` 的验收切片

**规范/契约已明确、无需裁定**：`rb3=rbtp`（`DADAO-21 ABI`）、TLS 变体与 TP 偏置下放 musl（`contract-dynlink §2.4/§7`）、`PT_INTERP=/lib/ld-musl-dadao.so.1` 与 auxv 集合（`§6.1–§6.4`）、TLS 重定位编号 10–13（`contract-elf §2.2`）。实现发现新语义才停下提交。

**Open issue**：0。

## 2026-11-07 新脚本首次真机使用即暴露假绿

- `INFRA-130t` 验收全绿（16/20 断言），但在真实节点上第一次 `remote.py status` 就报 **rc=0 PASS 而仓库根本没进去**。
- 根因：`cd <repo> && <多行脚本>` 中换行等价 `;`，`&&` 只护住首行 ⇒ cd 失败后其余照跑、rc 取最后一条命令；叠加 `shlex.quote("~/x")` 使 `~` 不展开。
- 教训：证据断言若只覆盖「存在且正常」的路径，会集体漏掉「前置步骤失败」这一类假绿；**每个前置步骤都要有可达 FAIL 断言**。
- 处置：立 `INFRA-131t` 修 cd 语义、`~/` 展开与 rc 传播，并要求在真节点上验收。

## 2026-11-08 chipyard 定位（用户裁定，撤销相关任务）

- **用户原话**：「chipyard --help 的事情：我们没有必要去调试！！！我们不需要去测试chipyard本身，这只是我们要用的平台和工具」
- **处置**：撤销 `INFRA-136t`（chipyard 补丁）与 `INFRA-137t`（补丁工具支持子模块），两者**零源码改动**、无产物，任务书与里程碑行一并删除；`INFRA-133t` 的冒烟判据改为「产物存在且可执行 + `verilator --version` 符合 + 构建日志含版本行」，**不再验证 `--help`**。
- **保留的知识**：`--help`/`+help`/无参数都会 `terminate`，根因是 htif 的参数解析被推迟到首个时钟 tick 且 Verilator `--main` 生成的 `main()` 无 catch；这是上游行为，不是我们的环境偏离 —— 结论保留在本文件上一节，供以后排查参考，不再投入修复。

## 2026-11-08 chipyard `--help` 崩溃：根因复核（结论：上游行为，非环境偏离）

- **现象**：`simulator-… --help`、`+help`、**以及无参数**三种调用都 `terminate called … std::invalid_argument`（`--help` 为 `User queried htif_t help text`，无参数为 `No binary specified`），rc=255。
- **调用链（gdb `catch throw`）**：`htif_t::parse_arguments`（`riscv-isa-sim/fesvr/htif.cc:337`）→ `htif_t::htif_t` → `tsi_t::tsi_t` → `testchip_tsi_t` → `SimTSI.cc::tsi_tick()`（**首个时钟 tick 才构造**）→ `VTestDriver::eval_step()` → Verilator `--main` 生成的 `main()`（**无 try/catch**）。
- **排除环境偏离**（逐项核对）：chipyard `0acc1e1` clean；`generators/testchipip` = gitlink `26f821b`（上游 2026-04-20）clean；`riscv-isa-sim` = `9c190a07`；Verilator **5.022**（chipyard `conda-reqs` 指定版本）。全部为上游锁定态。
- **旁证**：chipyard 仓库内**没有任何脚本/文档**用 `--help` 调用仿真器（`grep` 只命中 build 脚本自身的 help）；正常用法总是带二进制 ⇒ 该路径上游基本无人触发。
- **含义**：不是我们绕开 `build-setup.sh` 造成的；要修仍得改上游代码（父仓自定义 main 或改子模块 `SimTSI.cc`）。

## 2026-11-08 `AT_UID/EUID/GID/EGID` 口径（用户裁定 A）

- **问题**：`GEM5-027t` 里 auxv 四项写 0（按任务书原文），但 gem5 的 `getuid` 返回宿主 id（1000），同一引擎两条身份通道自相矛盾；QEMU 与 Linux 内核 `create_elf_tables` 都取发起者凭证。
- **用户裁定（2026-11-08，原话）**：「A：改 auxv 为宿主 creds（推荐）」⇒ gem5 SE 的 `AT_UID/EUID/GID/EGID` 取 `::getuid()/geteuid()/getgid()/getegid()`，与 `getuid` 系统调用同源；探针由 `local:` 分侧改为跨引擎逐值相等。
- **落点**：`GEM5-027t` 任务书验收第 2 条按裁定改写并注明；README/changelog 同步；由 engineer 重跑双引擎探针与门控。

## 2026-11-08 M12 计划修订（用户裁定）

- **riscv-tests 移出 M12**：M12 只用 `inst`/`tset` 中已被 qemu/gem5 验证过的子集；riscv-tests 的移植与调整放 **M13**（下一波专门讨论）。
- **chipyard 构建/运行/调试全部在 `server207`**，串行；**所有对仓库的修改仍在主控机**（已写入 `AGENTS.md` 与 `nodes.md`）。
- **任务编号**：`m12-<module>-<NNNN>`（3–4 位），无 k/t/m 后缀；M12 用独立台账 `milestones-m12.md`。
- **m 册门控取消**（用户选 B）：由 `m12-infra-002` 执行。
- M13 = 三个模拟平台（qemu/gem5/chipyard）的**差分对齐**，含指令语义，尤其是**浮点**语义。

## 2026-11-08 chipyard 命名/补丁方式/里程碑（用户裁定）

- **按实现分类，不按 tiny/node**：`dadao-wuming`（单周期）、`dadao-wuqing`（五周期）、`dadao-wuxing`（超标量）；每种实现内部再按 **Tiny / Node** 做测试与验证配置。
- **补丁方式：A**（全部进 chipyard 补丁集；newfiles 也写成补丁）。
- **三线 = 三个里程碑，分开进行**：`M12`（chipyard-tiny）/ `M13`（inst-golden）/ `M14`（linux-bootup）；**讨论清楚一个就开一个**，不并行开三个。
- **参考实现**：`.cache/refs/DADAO/SOC-chipyard/`（`chipyard-0111-newfiles/generators/dadao-wuming` + 5 个接线补丁 + `chipyard.mk`）；riscv-sodor 为第二参考。PR #4 仅参考。

## 2026-11-08 队列与阻塞（巡检记录）

- **进行中**：`INTEG-060t`（argmask 三方门控，gem5 补丁唯一写者）。
- **待开始（依赖满足但需串行）**：`GEM5-031t`（chmod/fchmodat）、`TESTCASES-103t`、`TESTCASES-104t`、`INTEG-059t` —— 均依赖 gem5 源树/二进制稳定，排在 `060t` 之后。
- **等 M11 收口后**：`INTEG-059t` → M11 `m` 册（`make check-milestone` 现报「无 m 册」，属预期）。
- **M12 三线（chipyard-tiny / inst-golden / linux-bootup）**：待用户确认三点——M12 是否现在开、三线模块前缀、M12 台账是否按三线分节。
- **已裁定挂起**：`ISS-345`（futex，语料不可达）；chipyard 相关 ADR 全部重做（用户 2026-11-08）。
- 结论：当前唯一可推进项是 `060t`；其余为串行依赖或等用户确认。

## 2026-11-07 两台构建节点就绪

- 两台 64C/128G 节点已完成引导（软件包、仓库同步、`fetch` → `apply-series` → `install-host`），工具链与主控机同版本。
- 就绪验证：`make check`（L1）两机均 rc=0，各约 64s；`make check-inst` 两机均 rc=0（44/44、载体 23 册，node 全量 + tiny 子集），结果行逐字一致 ⇒ 可作确定性对比基线。
- 后续重活（LLVM/gem5 重建、tset 全量）可外派；引导步骤与跨机派单已立 `INFRA-130t` 固化为脚本。

## 2026-11-07 `check-knowledge-refs` 空转判据（用户裁定 A）

- **背景**：清理任务书运行期证据引用后，fresh clone 上 `.work/**` 整体被 gitignore ⇒ `checked==0` 触发 vacuous FAIL，与「任务书不写运行期路径」冲突。
- **事实核验**：执行子会话里只有派单消息、没有用户问答记录；任务书原写的「用户原话：最小修正空转判据（推荐）」**无 session 证据** ⇒ architect 已撤回门控改动，并向用户求证。
- **用户裁定（2026-11-07，原话）**：「A：按扫描到的引用数判空转」⇒ 门控改为 `found == 0` 才判空转（没有任何 `.work/**` 引用才失败）；悬空判据与 (B) 面不变。
- **处置**：`INFRA-129t` 按真实裁定重新应用门控修正，任务书「用户裁定」节改写为用户实际选项并注明原记录无证据。

## 2026-11-07 新节点 L1 红：运行期证据引用

- fresh clone 上 `check-knowledge-refs` 报 20 处悬空——任务书/知识文件写了具体运行期证据文件；主控机因文件存在而假绿。
- 立 `INFRA-129t` 清理这些引用（只改措辞，不改结论）；完成后新节点可直接 L1 绿。

## 2026-11-07 用户批准：QEMU SS_AUTODISARM 补丁

- `GEM5-029t` 为使 QEMU 与 Linux 一致，改了 `components/qemu/linux-user/{signal.c,dadao/signal.c}`（`SS_AUTODISARM`）。任务书本写「不在范围：QEMU」，属跨模块变更。
- **用户裁定（原话）：「同意」**——保留该补丁；它只是给 QEMU 补 Linux 已有语义，不改变对照方向。
- 收尾时把该批准与补丁范围写进任务书；QEMU 侧仍须 `build-qemu`/`install-host` 绿。

## 2026-11-07 并发派单事故（watchdog）

- **事实**：另一会话（`lecnotes`，2026-10-25 创建）在 13:31 自行派了 `GEM5-027t` engineer 子代理，工作目录在 OpenCode 数据目录下的 worktree，并开始 `make build-gem5`；与本会话的 `GEM5-029t` 共用 `.work/source/gem5`，形成两个 gem5 写者。
- **处置（用户选 A）**：中断该子会话（API `interrupt`）、终止其构建；其 worktree 无改动（clean，`964131ad`）已删除；`GEM5-027t` 回到队列，等 `029t`/`030t` 后再派。
- **规则（待写入 AGENTS）**：外部会话/watchdog 派单前必须查 `job` 表或 gate lock，**同一组件同一时刻只允许一个写者**；共享 `.work` 的任务必须串行。

## 2026-11-06 convert_f2i 舍入语义（已裁定）

- **结论**：`ADR-0050` 已 `Accepted`（用户「ADR0050确认」，D1–D7）；15 条六档 one-hot / 3 条 SBZ / 4 条复制计数；汇编层 18 条单寄存器、无花括号、第三操作数显式。
- **落地**：`SPEC-194t`（规范/契约）→ `INTEG-058t`（LLVM/QEMU/gem5/tests）均已 `已验证`；9 个 `math/*` + `Olden/power` 双引擎转绿，parity 269/0 diff。
- **版本号（2026-11-06 用户裁定）**：保持 `0.5.6-rc（未发布）`，13 册册头不动；M11 收口时再决定是否去 `-rc` 发布。

## 2026-11-05 M11 收口与实现决定

- **1B**：M11 按“含实现”收口；5 个屏蔽寄存器实现 + 退出码实现完成后才算 M11 完成。
- **2B**：实现拆 2 个 INTEG 任务：`INTEG-054t`（5 寄存器）、`INTEG-055t`（退出码），各含 QEMU→gem5→tests 三阶段。
- **3A**：现在 push 当前 master。
- **4A**：小项现在清：`INFRA-124t`（ADR-0013/check_spec_refs/GEM5-017t/Node embench）、`QEMU-084t`（ISS-343 guest rlimit）。

## M11 收口验证状态（2026-11-05）

- `make check-full`（L3）：**PASS 8/8**；`check-l3-report` rc=0（QEMU-083t 后已重跑）。
- `make check-night`：**4/4 绿**（`tset:libc-test`/`llvm-ts`/`embench`/`arch:cfx`）；`check-night-report` rc=0。
- `TESTCASES-100t` 修正 libc-test `malloc-brk-fail`（6×32736 prime 启动堆），static 335/0/2、dynamic 338/0/2。
- 诊断 `TESTCASES-099t`：根因 = musl dynamic loader `reclaim_gaps` 捐赠启动堆；QEMU guest rlimit no-op 是能力缺口（`ISS-343`），非该例直接原因。
- **处置选 C（测试修正）**：`TESTCASES-100t` 在 libc-test 语料侧消耗 dynamic loader 捐赠的启动堆；libc-test 由 `patchless` 转受补丁组件。A/B 不再采用。`TESTCASES-098t`（矩阵）依赖此项收口。
- `TESTCASES-099t` 诊断已 Accepted 并合并（`151fd2a5`）；结论 = musl dynamic 启动堆，非 QEMU mmap/rlimit 直接缺陷；`ISS-343` 记录 QEMU guest rlimit no-op（P3）。
- **处置 C 已实现**：`TESTCASES-100t` 在 libc-test 语料侧 prime 启动堆（6×32736），static 335/0/2、dynamic 338/0/2；**完整夜跑 4/4 成员 rc=0、check-night-report rc=0**。reviewer Accepted，仅剩 QEMU-083t 并发源树导致 `check-patch-tree`/L1 环境红，待其合并后复跑。
- `SPEC-189t` 已 Accepted 并合并（`63b90b46`）；`ISS-344` closed。

## 批次授权

- **2026-11-01 M11 gem5 批次**：B0 解码核心（`GEM5-004t`）+ B1–B7（按 G1 矩阵拆分，任务书待立）+ `SPEC-181t` 语义缺口收口。
- 范围：已接受的 G1 矩阵、FS+SE M11、按 `docs/Process-09` 复用测试；不新增跨模块修改（LLVM/QEMU/picolibc 仍不动）。
- 授权：批次内可直接创建任务书、建任务分支、`/dispatch`、验证、`/complete`、合并 master；不逐任务确认。
- 停止点：批次外新任务、新增/改变 SPEC/契约语义决策、跨模块修改、push、破坏性/硬件操作、验收标准变更。
- 任务仍须落盘 `.tao/tasks/` 且有 `milestones.md` 流水行。

## 待用户裁定：ADR

### SPEC-180t 的 ADR

- 状态：待用户裁定
- 结论：escape 合法偏移集 `{0,+4}` + `imms18[17:1]` SBZ ⇒ ILLI，按 `docs/Process-03` 命中外部契约变更/多方案/结论固化
- 下一步：逐条确认 decision 后再立 ADR；未确认前只保留为遗留

### 拟议 ADR：Linux bring-up charter（M12/后续，未落文件）

- 状态：方向已确认；ADR decision 文本待逐条确认（尚未落 ADR 文件）
- 已确认方向：Linux 7.2.10、单核 QEMU MVP、semihosting console + exit、Linux 阶段不引入 UART/cache/LLC、TLB 在 K3 定义、busybox 到 K4 后再说、0628 只参考不复制
- 下一步：把上述方向写成 D1–D7，逐条确认后再落正式 ADR；当前只在 discussing 记录

### ADR 状态

- `ADR-0043`/`0045`：已 `Accepted`
- `ADR-0046`：仍 `Proposed`，等 Linux 实测后再收口
- 下一步：不再改 0043/0045 的 decision；0046 保持 `Proposed`

## 待立项 / 后续

### M10 后的 cfx 范围

- 已实现：umon/jmon/smon/hmon/ptw/pmem/time/hart/power
- 后置：cache/llc/uart、PMEM 区域分配、IPI、多 hart
- 下一步：M10 收尾后按 Linux 需求拆任务

### U-mode / cg5 / 异步帧

- 状态：待讨论
- 结论：U-mode 的 cfx 目标不设 ISA 限制，由 OS 策略决定；cg5 单帧、同步/异步分离、递归/重入尚未定
- 下一步：等 cg7 与 escape 收口后再讨论

### SBI 生产 provider / W1C

- 状态：后置
- 结论：当前只有测试专用 provider；生产 provider、`DONE/ERROR` W1C、`WAIT` 属 Linux 集成阶段
- 下一步：不在 M10 通路内实现

### TESTCASES-089t 遗留

- `reserved.yaml` 是否拆册（当前同册承载「保留编码 ⇒ UNDI」与「reserved cfx 地址空间 ⇒ CFXMEM」两类语义）
- `trap`/`escape` → reserved cfx 的 active 向量仍 deferred（`TESTCASES-033t`）

### CFX 审计保留的未决项

- IPI：只有接收端，没有发送服务/寄存器
- TLB：当前**无规范定义**（此前实现只覆盖 invalid，没有 fill）；按 Linux K3 先定义 fill/invalidate/ASID/fault 语义再实现
- `cfx_pmem_exist`：SEE 与 SBI 语义不一致
- UART：实例号/索引语义未定义（Linux 阶段暂缓，留 M12/后续）
- 下一步：确认哪些进入 M10 后/Linux 前任务；不恢复已删除的审计文件

## 当前优先：gem5（M11，PR #3）

- **任务批次（2026-11-02）**：`SPEC-181t`、`LLVM-142t`、`QEMU-078t`、`GEM5-005t`、`TESTCASES-090t` 已一次建齐；按依赖 dispatch，不再逐任务等。记录以 `milestones.md` 流水 + 各任务书为准。
- 用户 2026-11-01 裁定：现有 Linux 开发延至 M12 或后续；先完成 gem5，gem5 成为新里程碑 M11。
- 新模块：`gem5`，任务前缀 `GEM5-`；目录 `.tao/tasks/gem5/`。Linux 模块保留，恢复时再用。
- 工作方式：**不做 PR merge、不建 worktree**；在本仓库普通任务分支上按 DADAO 最新 spec 重写/整理补丁。
- 范围：**同时包含 FS + SE**；参考 0628 的 ADR-0010，**SE 先行、FS 后接**：SE 先建立快速 ISA/ELF/syscall 参考，FS 再做 Machine-01、boot ROM、模式移交、semihosting、PTW/TLB 等；两者复用同一 ISA/执行核心，但按最新 DADAO 规范重做。
- M11 收口：FS 与 SE 都通过，并完成 QEMU/gem5 对应模式的一致性门控。
- 测试：按 `docs/Process-09` 的 `inst/arch/unit/tset` 四 scope 调整；**不新建 `tests/gem5/` 平行体系**；gem5 只作为 system/user 后端，复用现有向量、bootrom、harness 和 case 清单；该合并的合并。
- QEMU/gem5 一致性：
  - **SE ↔ QEMU user**：`tset`（libc-test/llvm-ts/Embench）与用户态 E2E，比通过/失败/退出码/架构结果。
  - **FS ↔ QEMU system**：`inst`/`arch`/裸机 E2E，比架构结果/退出码，不比时序。
  - 不允许拿 gem5 FS 与 QEMU user 冒充一致；不同模式分别出结果矩阵。
- 约束：其它模块（LLVM/QEMU/picolibc/测试/基础设施）如需修改，先经用户同意；测试调整**单独立任务**，不与实现补丁混在一起。
- PR：`gxt/DADAO-v5#3`，标题“gem5: 提交 DADAO 裸机功能闭环里程碑（GEM5-008m）”，当前 **draft**、`mergeable=false`、`mergeable_state=dirty`。
- 分支：head `JeffffHu:DADAO-v5:pr/gem5-008m-milestone`，head commit `7ea82cfe…`；base 为 `gxt:master` 的 `c6fbcbae…`；差异约 **97 文件 / +7710 行**。
- 本地试合并（基于当前 master）冲突 **12 项**，主要来自 M10 归档后的任务删除、`tests/llvm` 迁 `tests/unit`、Makefile、LLVM/QEMU/picolibc 补丁、ADR 编号碰撞。
- 下一步：先做 M11 gap matrix（FS/SE 共用 ISA、FS/SE 分叉、测试复用/合并、其它模块依赖），再按最新 spec 重做 `components/gem5` 补丁与测试；不直接采用 PR 的旧计数/旧证据。
- M11 子阶段（参考 0628 ADR-0010 修订）：G0 gap/契约 → **G1 共用 ISA 核心 + SE** → **G2 FS 全系统** → G3 QEMU/gem5 双向一致性与测试收口 → G4 里程碑核验。SE 先行拿快速功能参考，FS 后接系统态；两者同属 M11。
- 0628 参考结论（仅参考，不复制代码）：ADR-0010 明确 **SE 先行、FS 留后**；先做 `SEWorkload`/`Process`、真实 ELF、RB1/栈、brk/mmap，再上 Machine-01/PTW/TLB/timer。已知坑：`SEWorkload` 与 `Process` 概念混淆、LLD 多段 ELF 装载、QEMU trampoline 的 RB1 不可照搬到 SE、RB bank/RegClass/rd0/rb0 语义、不要整体克隆 RISC-V arch 充当骨架。
- **语义复用禁令**：编码相同、助记符相同 **不等于** 语义可复用；每条指令必须从当前 `spec/`/`contracts/` 重新推导，单独核对操作数/结果/异常/FP 舍入/标志/内存副作用，并与 0628/PR 的变化逐条对照。G1 先产出“语义重导矩阵”，不得按旧 opcode 表直接搬运。
- 任务量粗估：G0 4–6；G1 SE + 共用 ISA 10–15；G2 FS 15–25；G3 测试/一致性 5–8；G4 1–2；合计约 **35–56**，以 G0 matrix 校准。
- **2026-11-02 裁定**：B7 收口后先做 `GEM5-013t` 全 264 条执行收敛，再进 G1 SE；SE 分阶段，静态 ELF/静态 tset 先行，动态链接、TLS、线程/futex 后补；M11 最终仍按 ADR-0048 D4 覆盖完整 tset，不降级。ADR-0048 原文待恢复或重新裁定。
- **2026-11-02 授权**：用户同意 ADR-0048 按现有讨论重建；同意 G1 任务链（`GEM5-013t` → SE 骨架/ELF/syscall/VMA-TLS/静态 tset → 动态/线程后补 → G2 FS）；不支持 syscall 默认失败报告、不静默忽略；该链内不再逐任务确认，只有新语义/跨模块/破坏性/push 才停。
- **2026-11-02 双链并行授权**：同时授权两条独立任务链推进——**G1 SE**（`GEM5-014t` SE 骨架 → ELF/args/stack → syscall/VMA → TLS → 静态 tset）与 **FS Machine-v5**（`SPEC-183t` → `TESTCASES-091t` → `QEMU-079t` Tiny / `QEMU-080t` Node → gem5 FS 映射）。SE 为优先线，FS 线可并行；共享文件仍串行；两条链均不需逐任务确认，停止点按 AGENTS。
- **2026-11-02 G1 SE 验收基线**：full tset 以 QEMU user 的 pass/fail/skip 集合为基线；gem5 SE 不能少通过；若 **gem5 通过而 QEMU 未通过**，不得直接接受 gem5，须新增 QEMU 调试任务定位并修正，使两者一致；若差异根因是 spec 解释不清，提交用户裁定。静态 SE 先做 `ET_EXEC`，不提前做 `ET_DYN`/static PIE。
- **2026-11-04 gem5 SE 测试范围暂缓**：gem5 上**暂不跑 llvm-ts**；llvm-ts 继续以 QEMU user 为执行/对照环境。gem5 SE 先做 smoke、目标子集、syscall/VMA/TLS 等能力验证；完整 tset 的最终覆盖仍按 ADR-0048 D4 保留，是否恢复/何时恢复由后续用户裁定。该暂缓不改变“QEMU/gem5 同模式双向一致”规则。
- **2026-11-06 用户裁定：SE 要全面支持**：重申 M11 子阶段 G0→G1→G2→G3→G4 不变；`2026-11-04` 的「gem5 暂不跑 llvm-ts」**作废**。G1 剩余按已核对序列推进：`021t`（基线）→ `022t`（brk/mmap）→ `023t`（文件 I/O+时钟）→ `024t`（信号/limits/进程信息）→ `025t`（IPC/多进程）→ `026t`（线程/futex + TLS 切片）→ `027t`（动态装载器）→ `028t`（文件映射/ldso）→ `TESTCASES-103t/104t`（预算/动态驱动）→ `INTEG-059t`（G3）。当前 SE 实测仅有 6 个 syscall（`ioctl/write/writev/exit/exit_group/set_tid_address`）。
- **2026-11-05 gem5 完整 llvm-ts 回归（M11 收口条件）**：M11 SE 收口前必须跑**完整 llvm-ts 回归**，不称“夜跑”；QEMU user 为基线，gem5 不能少通过；gem5 通过而 QEMU 未通过不得直接接受，须定位到一致。先决：gem5 SE 的 syscall/VMA/TLS 等能力齐备；未齐备项如实记 BLOCKED，不伪 PASS。可用现有 `check-night` 门控承载，但触发时间不限定夜间；QEMU user 仍是日间基线。
- **2026-11-04 SYS_TICKFREQ M11 基线**：`SYS_TICKFREQ` 统一按 **`1e9` ticks/秒**；QEMU/gem5 同模式一致。spec 当前未定义具体值，M11 先按此约定实现/对照，后续 spec 收口时可固化。
- **2026-11-05 picolibc `math_test` M11 收口**：`Machine-v5-Tiny` 的 picolibc `math_test` 在 gem5 上记 **BLOCKED**，不得写 PASS：同一 ELF/argv 下 QEMU **0 errors**、gem5 **238/76404 errors**，归因 **B7 浮点数值差异**，不是 FS/PTW/semihosting。M11 接受该已知 BLOCKED；待独立 golden 模型建立后再修 B7 并另立差分任务。报告必须保留 blocked 计数，不得计入 gem5 通过数。
- **2026-11-05 M11 退出码定稿**：guest 段 `0x00–0x3F` = PASS，`0x40–0x7F` = FAIL；机器 fault 段中 `0xC0–0xFF` = monitor（`bit7=1,bit6=1,bit5:4=运行模式,bit3:0=DADAO 异常位索引`），`0x80–0xBF` = 其它 cfx（`bit7=1,bit6=0,bit5:0=cfxHA`）。monitor 异常编号直接使用 DADAO 位索引（CFXTRAP=0、CFXMEM=1、CFXREG=2、CFXESC=3、CFXPERM=7、ILLI=8、UNDI=9、RASOF=10、RASUF=11、MALIGN=12、IALIGN=13）；`PTWERR`、`unmapped`、旧 `0x84`/`0xE1` 均删除。`unmapped` 归当前运行模式 monitor 的 CFXMEM；reserved cfx 普通 ld/st 归 CFXMEM、trap/escape 归 ILLI，均进当前 monitor。运行模式 user/jail/supv/hypv = 00/01/10/11。
- **2026-11-05 DADAO-12 §5.2 同步异常路由**：删除 `inner_cfx_mask`；同步异常权限拒绝统一 CFXPERM 进当前模式 monitor；CFXREG 统一进当前 monitor；保留 cfx 的 ILLI 规则不变；异步中断屏蔽不冻结，留后续任务。`DADAO-12 §5.2` 需要整体重写并更新只读锁。
- **2026-11-05 Node / Embench 归属**：`GEM5-016t`/`QEMU-080t` 的 Node inst/embench 结果转历史，不计入 M11 Node 验收；M11 Node 只验收 cfx/arch/PTW/模式。Embench 的 system/bare-metal 归 Tiny，user static/dynamic 归 SE，Node 不跑 Embench。`tests/parity/matrix-M11.md` 在 M11 收口时原地重生成。
- **2026-11-04 ccache 接入口径**：ccache 使用**全局缓存**（默认 `~/.cache/ccache`），不做全局 PATH 软链/编译器影子；**每个模块的编译入口单独接入**——gem5 已接；QEMU/musl/picolibc/LLVM 等后续编译任务各自在 `CC`/`CXX` 或 CMake/Meson launcher 加 ccache；Linux 随 Linux 阶段接。各模块不得假设其它模块已代为接入。
- **2026-11-02 测试机 RAM 映射裁定**：分 `Machine-v5-Tiny` / `Machine-v5-Node` 两个 FS profile（Node = 完整系统节点，当前单核，可扩展多核/NUMA）。Tiny：BootROM 64 KiB `0xffff_ffff_0000`–`0xffff_ffff_ffff`，SRAM 8 MiB `0xffff_ff00_0000`–`0xffff_ff7f_ffff`，ELF/rodata 由 loader 装入 SRAM，不塞 BootROM；覆盖 Embench 与完整 picolibc 测试集。Node：BootROM 4 MiB `0xffff_ffc0_0000`–`0xffff_ffff_ffff`，RAM 2 GiB 物理 `[0, 2 GiB)`；hmon 直接驱动 cfx_pmem、建立一级页表（2 GiB = 4 个 512 MiB 超页，`SPF=0xFF`）并在 hypv 下跑测试；`power → hmon → smon` 路径保留给内核/smon 测试。DADAO-12 只要求 BootROM ≥64 KiB，Machine-v5 规定实际大小；不做双映射，直接迁移并逐项修问题；不新立 ADR，修改 ADR-0004/0039/0040/0043 与 `spec/Machine-v5-测试机运行环境.md`。
- **2026-11-02 Tiny/Node 澄清与页大小**：Tiny 地址高 6 位恒为全 1（cfxha 63），**不实现任何 cfx（含 `cfx_power`）**，不能进入 user 模式；Tiny 只跑非 cfx 的 `inst` + `embench` + `picolibc`，但**允许 semihosting**（`trap` 只作陷入 host 的开关，不算 cfx 类指令）。Node 跑完整 `inst` + `arch` + `embench`，**不含 `picolibc`**。M11 不覆盖 smon。页大小统一为 **16 位/64 KiB**；QEMU user 当前 `TARGET_PAGE_BITS=12` 是 bug，须改为 16，不得把 4 KiB 当基准。
- **2026-11-02 SPEC-183 ADR 与 picolibc 裁定**：用户逐条确认 ADR-0004/0039/0040/0043 四项修订；picolibc 自测采用 **A 方案**：ELF 的 crt/启动 stub 在 `0xffff_ffff_0000`，应用 `.text` 在 `0xffff_ff01_0100`，picolibc `__start` 在 SRAM 清 BSS，`e_entry` 在 ROM。`dadao.lds` 改为 `dadao-tiny.lds`，Node 用 `dadao-node.lds`，不保留泛名。
- **2026-11-02 DADAO-12 异常流程修订待办**：`DADAO-12 §5` 异常进入流程需修订，明确区分两类拒绝——目标 cfx 的 `cfxtrap`/`cfxmem`/`cfxreg`/`cfxexe` 同步来源 mask 拒绝源 cfx ⇒ `CFXPERM`；硬件内部 `inner_cfx_mask` 屏蔽目标 cfx ⇒ `ILLI`。现行 prose/伪代码把两者混在一起，`m5_perm_mask_*` 已暴露该歧义。归 `SPEC-183t` 或单立 SPEC 任务；改只读册前须用户授权并更新 `spec-readonly.lock.toml`。
- **2026-11-03 cfxha 重编号与作用域（M11 收尾前后执行）**：M11 结尾前后统一重排一次 cfxha：`cfx_pmem` → **32**、`cfx_llc` → **33**、`cfx_time` → **34**。多核系统资源作用域增加一行：**`cfx16–cfx31` = per-task；per-system = `cfx32–cfx63`**。`per-task` 含义：内核或进程需**申请后使用**该 cfx，并在使用完毕后**释放**；使用过程中进程发生上下文切换，**不影响该 cfx 的运行**，即**无需上下文切换**。该改动跨 spec/contracts/QEMU/gem5/tests，须统一任务落地，不得零散改号。

## Linux（M12 或后续，暂缓）

> 2026-11-01 用户裁定：现有 Linux 开发延至 **M12 或后续**；此前记录的方向在恢复时沿用，但不再作为当前里程碑。

### 已确认方向（2026-11-01，用户逐条确认）

- **模块归属**：新建 `linux` 模块，任务前缀 `LINUX-`；目录 `.tao/tasks/linux/`。
- **内核基线**：Linux **7.2.10**，commit `7b20d05f…`；不采用 5.4。
- **平台**：恢复时只做 QEMU system 模式，单核；**不纳入 gem5**。
- **MVP**：内核日志 → built-in initramfs 的静态 `/init` → 至少一次 Linux 系统调用往返；不要求 login/shell。
- **控制台**：**semihosting** 负责控制台输出与测试退出闭环；**不引入 UART**，不新增 cfx。
- **initramfs**：先放静态 musl 自定义 init（write/getpid/brk + 错误路径），**busybox 到 K4 之后再决定**，不预设进该阶段。
- **TLB**：当前**没有规范定义**（DDLN 只是讲义，不是规范）；K3 先定义 fill/invalidate/ASID/fault 语义，再实现；K0 不定义。
- **cache/LLC**：该阶段不引入，留到后续。
- **0628**：只参考阶段划分、踩坑和测试思路；不复制 `arch/dadao`、补丁或实现代码。

### Linux 补丁策略（待 K0 落任务书）

- 当前 `manifests/components.lock.toml` 的 `linux` 条目是 `patchless = true`，角色仅为 syscall 号表参考。
- 恢复时建议复用同一 7.2.10 commit，转为受补丁组件：`patch_dir = components/linux/patches`、`patch_series = components/linux/series`，角色改为“Linux 内核移植目标 + syscall 参考”。
- 按 `docs/Process-01`：`.work/source/linux` 为干净 git 基线；一文件一补丁；新增 `arch/dadao/**` 也用 `new file mode` 补丁；`make apply-series` + `check-source-state`。
- 不直接改 `.work/source/linux` 作为真源，不复制 0628 的补丁集。

### 阶段与任务量（K0 后校准）

- K0 基线与契约：5–7 个任务（补丁组件、工具链缺口、启动 ABI、syscall/errno/TLS、initramfs/semihosting、门控）。
- K1 启动与控制台：4–6 个。
- K2 异常与时间：5–7 个。
- K3 内存与 TLB：6–8 个（含 TLB 规范定义）。
- K4 进程与上下文：5–7 个。
- K5 用户态闭环：5–7 个。
- 合计约 30–42 个任务；Linux 阶段收口只到 K5，busybox/UART/cache/LLC/gem5 等不阻塞。

### 待办

- Linux 恢复时立定义与 K0 任务书（`linux` 模块）；拟议 ADR 的 decision 逐条确认。
- K0 前不写内核代码；先冻结补丁策略、启动 ABI、工具链缺口和测试门控。

### K0 兼容性缺口（待矩阵化）

- 兼容性缺口：`arch/dadao`、`llvm-ar/ranlib/strip`、`asm goto` 输出、栈保护、`.quad/.long/.short/.byte`、inline asm 约束、`-mcmodel=kernel`
- 入口判据：spike 清单归零或有规避法 + 工具链就位 + `arch/dadao` 最小骨架能 `make ARCH=dadao` 出 vmlinux
- 详细兼容性记录不在此展开；K0 落任务书/矩阵后移入对应文档

## 现行约定（非讨论项）

- 任务流水体例由 `make check-milestones-fresh` 机械校验（状态一致 / 覆盖 / ≤120 字符 / 倒序 / 格式），不在本文复述。
