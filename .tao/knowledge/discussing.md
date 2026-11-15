# 讨论项

> **组织方式（用户 2026-11-08）**：按里程碑分节，**M12 / M13 / M14** 各为一级标题；M11 已归档（仍有效的口径见「跨期口径」）；**不在这些里程碑内**的事项集中到「三个里程碑之外」。
>
> **维护规则（2026-11-13）**：本文件**只记** ① 当前未决 / 待裁定；② **仍然生效**的口径。裁定一旦落成 `spec/`、ADR、任务书或 `AGENTS.md`，**从本文件删除**（git 历史可回溯）；过程快照、已完成任务的方案叙述、过期队列状态一律不留。任务流水看 `milestones-m14/…`，M13 及以前见 `.tao/archive/`。

# 跨期口径（M11 收口后仍有效，M12/M13 共用）

> M11 已于 2026-11-09 归档（`.tao/archive/M11/`，114 册）；其任务与历史裁定不再在此保留。

- **QEMU/gem5 一致性方向**：QEMU 已实现的 syscall，gem5 必须有等价实现；差异不是「可接受限制」；gem5 通过而 QEMU 未通过不得直接接受，须定位到一致。
- **环境缺口（5 例）**：`popen`/`spawn`/`vfork`/`execle-env`/`unix-smail` 需要 guest 根内的 DADAO `/bin/sh`、`echo`；SE 返回 `ENOEXEC` 正确。QEMU 侧「通过」是执行宿主 x86-64 二进制，**非同架构 baseline**，不计 gem5 能力欠账；不采纳宿主原生执行旁路。
- **SE 动态线边界**：`mprotect` 真权限不建模；主程序 `-pie`/`ET_DYN` 不支持（用非 PIE `ET_EXEC+PT_INTERP`）；语料按 `ADR-0048 D4` 全量；单线程 TLS 由 musl 完成。
- **`SYS_TICKFREQ`**：统一 `1e9` ticks/秒（spec 未定义具体值，暂按此对照；M13 差分时可固化）。
- **`SYS_chmod` 不新增号段**：`chmod()` 经 musl 走 `fchmodat`，不虚构 ABI 号。
- **输出捕获的 stdout/stderr 顺序（`ISS-357`）**：至少 4 例受影响，修复必须保留 fd1/fd2 写序，不能只交换拼接方向。

# M12：chipyard 上跑 `Machine-v5-Tiny`（收口中）

> 已完成 37 项；剩 `m12-chipyard-016`（embench + picolibc-full 在 chipyard Tiny 上全通）与 `m12-integ-002`（里程碑核验与归档）。M12 **不依赖 M13**、不做三平台差分（归 M13）。

## M12 未决

- **口径残留（`spec-003`/`spec-004` 未覆盖项）**：
  - #9 `cfx2rd`/`cfx2rc` 到**保留** cfxha ⇒ `ILLI`（`Machine-v5` 现只说「不存在 cfx 寄存器 ⇒ `CFXREG`」，与 `DADAO-12 §5.2(一)` 冲突）
  - #10 reserved 集统一（正文 `19–61` vs 附录 0.4.0 `16–31、35–61`）
  - #6 退出码由 hmon handler 生成（`§7.1` 只定编码、未定生成方）
  - #3 Tiny 的 hmon 镜像装载路径（与 R13 绑定）
  - （`m13-qemu-001` 新增）`excp_cause_info` 覆盖：`Machine-v5 §4.4` 5 项 vs `DADAO-13 §2` 11 项
  - （`m13-gem5-001` 新增）`escape` 返回 cfx 取自「异常帧」，但寄存器表无 `prev_cfx` 保存寄存器（实现镜像 QEMU/Node 保持目标 cfx）
  - （`m13-gem5-001` 新增）Tiny `cfx_power` 的 cg7（BootROM start/size）与 `cg8 rc1`（power ctrl，WO）无正文
  - （`m13-gem5-001` 新增）Tiny `switch_run_mode` 写非 hypv 值：寄存器 RW 但无强制路径
- **`spec-004` 候选**：Vast 的同步异常仍是 staged 机器 fault（`DADAO-12 §5.2(一)` 要求进向量），5 个 arch 探针 oracle 依赖旧口径；统一需同步改 qemu/gem5 + 探针。

---

# M13：三平台差分对齐（qemu / gem5 / chipyard，含浮点）

## 范围

- **三平台差分**：qemu / gem5 / chipyard 的**指令语义**对齐，**尤其是浮点**语义。
- **riscv-tests**：移植与调整在 M13 完成（M12 不用）。
- 判据仍是「实现之间一致 + 与 spec 逐条核对」；**不允许把「两个实现一致」当正确**（多数表决 ≠ 真值）。

## M13 起点：gem5 超时与运行时间可比性（用户 2026-11-09 裁定）

- **用户原话**：「M13准备专门进行多方测试的差分对比，可以先从gem5的超时问题做起，放到208节点机上，48并行（甚至60并行，你觉得呢）；建立专门的任务，跑3600s，甚至7200s，我们测试一下qemu和gem5的运行时间的比率，对不同的任务是否具有可比性。该任务（或者你可以分解多个任务）不修改源码，不做调试，只记录结果；我来对结果进行分析和裁定。」
- **并行度结论**：**48**（留 16 核给内核/IO）；60 会引入调度/带宽争用，污染时间测量。若 3 例 × 2 次方差 < 5%，再考虑提高。
- **任务分解**：`m13-testcases-001`（static 72 例 × 3600s）、`m13-testcases-002`（dynamic 93 例 × 3600s）、`m13-testcases-003`（3600s 仍超时的例 × 7200s）。
- **只记录不改源码**：这三个任务不做根因分析、不调试；结果由用户分析裁定。
- **M13 台账**：新建 `.tao/knowledge/milestones-m13.md`（`项目里程碑 = M13`），Makefile 的 `check-milestones-fresh` 扩展为校验 M11 + M12 + M13。

## golden / Sail 定位（结论，待落流程）

- **前提**：SimRISC/DADAO 持续变更、不留历史包袱；内核/FPGA 阶段同样如此。工具按「高频变更」取舍，不按「稳定期资产」取舍。
- **Sail：搁置**。形式化模型是稳定期资产；0628 实测只做 6–8 条切片、其余 `SKIP-unsupported`；「权威性」在自有扩展上不成立。重启触发条件：ISA 冻结 / 流片前 / 需要 RTL tandem 或定理证明。
- **golden：不做全量第四实现**。只保留三个窄用途：① 歧义探测（未明处 `SpecificationGap`/`UNSPECIFIED` 显式阻断，不猜默认值）；② 精确计算（FP/位宽/舍入）；③ 裁定回归（把用户裁定固化成向量/断言，防漂移）。PR#5 的全量模型 + 万行 `INSTRUCTION_REFERENCE.md` 属稳定期资产，不并入日常门控。
- **裁判只能是用户**：工具只做「发现歧义 + 举证（各解释下的结果/依据）+ 回归」，不做拍板；差分/fuzz 的分歧须聚类归因后再上报，不把原始分歧直接丢给用户。
- **投资顺序**：规范一致性/歧义探测 > 差分 fuzz + legality 矩阵 > 精确 FP > 轻量边界生成；解释器只在「需要算给看」时写。
- **三条禁忌**：向量里写未记录来源的期望值；模型对未明处选默认值；把「两个实现一致」当正确。
- **依据（0628 / PR#5）**：0628 四方差分（interp/QEMU/gem5/Sail）AGREE 198 / DIVERGE 0，`check-golden` 故意不进 `make check`；golden 仅整数 87 条，语义取自 `spec.md`（与 ADR-0009「wiki 直派」的要求不一致）。PR#5：标量 + 66 条 FP，回放 730（173/500/0/57），49 单测，`check-golden` 进 L1；无差分运行器，FP 向量只有 `scaleb`。
- **待落地**：① 「歧义登记 → 用户裁定 → ADR/向量 → 回归」的流程；② 是否把「歧义探测」并入现有 spec 门控；③ chipyard 是否已有 DADAO 核（决定 RTL 对拍是否成为主差分）。

## 第一阶段目标（用户 2026-11-09）

- **先定义每条指令的完整且准确的语义**（尤其浮点：舍入方向、异常标志、NaN 传播、边界值）。
- **再重新生成 `tests/inst` 的测试程序**，重点是各种边界。
- 之后才做三平台差分（`m13-integ-002`/`003`）。


- **`07-floating-point` 两处 spec 未明/冲突（待裁定，2026-11-14，`m13-testcases-022` 实测）**：
  1. ~~NaN→整数的饱和方向~~ **已裁定（2026-11-14）：与 hardfloat / RISC-V 一致**——`NaN` 一律按「正」处理（与符号位无关），有符号目的取最大正值、无符号目的取最大无符号值；`±Inf` 与有限超范围按符号饱和（无符号负向 ⇒ `0`）。已写入 `SimRISC-07` 与 `contract-fp §3`。
- ~~`SimRISC-07 §2.1` 余数「符号随 rfHC」~~ **已裁定（2026-11-14）：完全按 IEEE 754-2019 §5.3.1**——非零余数符号由 `rfHC − n×rfHD` 的精确值决定（可与 `rfHC` 相反），余数为零时取 `rfHC` 的符号。已写入规范与 `contract-fp`。


## M13 未决

- 差分矩阵的判据、参与引擎、失败归因口径（启动 M13 时专门讨论）。
- **3600s 长尾结论（2026-11-10，`m13-testcases-001` 全量）**：72/72 例 gem5 SE 仍超时，qemu 72/72 全 pass；最小例（qemu 0.0 s）也吃满 3600 s ⇒ 疑挂死而非慢（`ISS-361`）。
  ~~待用户定 7200s 还是定位挂死~~ **已定（2026-11-10）**：按 qemu 时耗 30 s 分 A/B 组——A 组 7200 s（60 例，已出结果 40 pass/17 blocked/3 fail），B 组无上限（90 例，进行中）。
- **3600s 长尾结论（2026-11-10，`m13-testcases-002` 全量 dynamic）**：93 例中 gem5 **78 blocked / 14 pass / 1 fail**，比值 `n=12`（min 172、median 289、max 1942）；
  qemu 93/93 pass。⇒ dynamic 有一小部分可测、static 全不可测。`neural` 为 gem5 侧 oracle mismatch（`ISS-362`）。

## 待定：运行平台 / 机型 / 用例适用范围 的对应关系（用户 2026-11-14）

**要求**：重新梳理并确定「运行平台、机器型号、测试用例」三者的对应关系（M13 内解决）。

**现状：四套正交概念在字段与工具里混用，无单一真源**

| 概念 | 现在写在哪 | 现取值 | 问题 |
|---|---|---|---|
| 执行模式 | `tests/inst.yaml` 的 `platforms:` | `[system]`（264 个 `.S` 全是）/ `[system,user]` | `system` 字面像"机型"，实际是"qemu-system 模式"；`.S` 实际只跑 Tiny |
| 机型 profile | `tests/shared/machine-profiles.yaml` | `tiny` / `vast`（含 `arch/embench/picolibc` 开关、`qemu_*` 回填） | 与 `platforms` 语义重叠；`vast` 的执行覆盖已被裁定放弃 |
| 引擎 | runner 参数（`--platforms qemu,gem5,chipyard`） | qemu / gem5 / chipyard | gem5 还有 SE/FS 两种，无处标注 |
| 用例适用范围 | 部分 `.S` 的 `profiles: [tiny]` | tiny | 与 `platforms` 双轨；全局/逐例两级混用 |

**已知的硬事实（证据）**

- `run_asm_suite.py` 只支持 `-M dadao-tiny`（L213/225），`platforms:[system]` 的 264 个 `.S` 全在 Tiny 上跑；
- chipyard 只有 `WumingTinyConfig`（无 Vast 实现）；gem5 有 SE/FS；
- `semantics_gate --profile vast` 的 1015 例是 Vast 唯一执行证据，`testcases-043` 已按裁定**放弃 Vast 执行覆盖**；
- `machine-profiles.tiny` 注释里「无任何 cfx」是 M12 前口径（现 `hmon: true`），`default_run_mode: machine` 是旧称。

**待用户裁定（逐条）**

1. 是否把术语定为三层：**引擎（engine）× 机型（machine profile）× 用例适用范围（case scope）**，并各给唯一字段？
2. `platforms:`（`system`/`user`）是保留（改名 `engine`/`mode`）还是**废弃**，用例适用范围统一用 per-case `profiles:`？
3. `user` 模式（qemu-user / llvm-ts）在新模型里算"平台"还是"引擎的一种 mode"？
4. Vast 放弃执行覆盖后，`machine-profiles.vast` 保留（文档/未来）还是删除？
5. gem5 SE / FS 如何标注（引擎的子模式字段）？
6. chipyard 只有 Tiny ⇒ 「三平台一致」的判据范围怎么表述（哪类用例要求三平台、哪类只要求两平台）？

**影响面**：`tests/inst.yaml`（264+ 条 `platforms`）、`machine-profiles.yaml`、`run_asm_suite`/`semantics_gate`/各 runner、`tests/README.md`/`inventory.md`、`Process-07` 与验收口径；`043`/`044`/`045` 正在改这些面，**须在其收口后一次性统一**，避免三处反复改。

---

# M14：Linux bring-up

> 2026-11-01 用户裁定：Linux 开发延至 M12 或后续；**现定为 M14**（三线分开进行）。此前方向沿用。

## 阶段与任务量（K0 后校准）

- K0 基线与契约：5–7 个任务（补丁组件、工具链缺口、启动 ABI、syscall/errno/TLS、initramfs/semihosting、门控）。
- K1 启动与控制台：4–6 个。
- K2 异常与时间：5–7 个。
- K3 内存与 TLB：6–8 个（含 TLB 规范定义）。
- K4 进程与上下文：5–7 个。
- K5 用户态闭环：5–7 个。
- 合计约 30–42 个任务；收口只到 K5，busybox/UART/cache/LLC/gem5 等不阻塞。

---

# M14 未决（2026-11-15 更新）

1. **K2（异常与时间，5–7 件）已获授权立册**（用户原话「4、同意，是否并行根据依赖关系来定」）；范围与验收口径见 K2 各任务书。
2. **TLB 规范正文推迟到 K2 完成后**（用户原话「5、K2完成后再说」）：`ADR-0052 D6` 已定「K3 第一步先定义 TLB、第二步才实现」，具体时点在 K2 收口后由主会话提出。
3. **semihosting 指针 = PA**（用户裁定「1：选1，PA」）：已落 `spec/Machine-v5 §5.2` + `contract-semihosting §2`（0.7.2）；由此产生的 QEMU 侧缺口登记 `ISS-450`（`SYS_WRITE0` 仍走页表）。
4. **`contract-linux-boot §1` 已扩写**（用户裁定「2、1」）：补「内核接管后自建页表并写 `PTBR`」，契约 0.2.1；并澄清 semihosting 指针不属该契约的 ABI 地址。
5. **`ISS-440` 已立 ADR**（用户裁定「3、1」）：`ADR-0054`（单 hart 机型下该清除事件不可观测、暂不实现），decision 待逐条确认。
6. **`contract-see §6.4` 需一处口径修订（待你确认）**：`m14-linux-007` 实测 `escape` 只恢复 mask/mode/IP、**不恢复 `inner_cfx_code`**（`spec/DADAO-12 §5.3`）；故某 cfx 投递过异常后「当前 cfx」变成该 cfx（如 `cfx_hart`），§6.4 写的「当前 cfx = `cfx_smon`」在**首投后不成立**。拟改为「IE 旋钮按**当前 cfx** 选行；正常运行期 = `cfx_smon`，首投后 = 该投递 cfx」，并让 `m14-linux-008` 按此实现（登记 `ISS-454`）。

# 待设计：长仿真如何"证明它还在跑"（gem5 / chipyard，2026-11-15 用户提出）

> 用户原话：「gem5/chipyard 如何在长时间的模拟仿真过程中，让我知道它还在运行，而不是死等运行完成」。

**问题实质**：现在能看到的只有"进程还在（`ps`）"和"打印了完成行"，**单例内部零信息**：既没有"已跑多少周期"，也没有"距预算是近了还是挂了"。因此无法区分「慢」与「挂死」。

**事实（已核）**

- **chipyard / Verilator**：`TestDriver.v` 每拍 `trace_count = trace_count + 1`，但**只在结束** `$fdisplay`（`*** PASSED *** after N cycles` / `*** FAILED ***`）；`+cycle-count` 同样是退出时打印；`+verbose` 是**逐周期 Chisel printf**，代价过高不能当心跳。RTL 里**没有**周期性输出。
- **gem5**：stats 在结束时写 `m5out/stats.txt`；中途无周期性进度（`--debug-flags` 是逐事件日志，量级不可接受）。
- **实际受害案例**：`ics170` 上 6 个 picolibc sim 跑到 **11 h 25 m** 仍无任何进度可观测（`test-iconv`/`test-sin`/`test-sincos-*`/`test-atan2`/`test-memmem`）；`ISS-361` 的「72/72 在 3600 s 全超时」本质上也是缺这个能力才只能靠超时判定。
- **已有基础**：`m16-testcases-001 跑批进度看板 + 增量 JSONL（可见性）` 已覆盖「逐例完成即落盘 + 节点日志/`ps` 汇总表」；但它给不出**单例内部**的周期进度与 ETA。

**可选手段（按侵入性递增，可组合）**

- **A（零改动，先做）**：外层 runner 每 60 s 把「在跑例 + 已跑时长 + `/proc/<pid>/stat` 的 utime + `semi.out` 最后修改时间」写一行 JSONL 心跳。判据：能看出"还在推进"（utime 增长、semi.out 有动静），但**给不出周期数**。
- **B（chipyard，改 RTL 包装）**：`TestDriver.v` 加 `+heartbeat=N`（`trace_count % N == 0` 时 `$fdisplay(stderr, "H %0d", trace_count)`）。收益=**精确周期进度 + 可按吞吐算 ETA**；代价=改 RTL ⇒ **sim md5 变化、单二进制基线要重做**，且 `$fdisplay` 会略微降速（需实测 <1%）。
- **C（gem5，配置层零 C++）**：`configs/dadao/se_timing.py` 用**分块 `m5.simulate(chunk)`** 循环，每块打印 `curTick()` 与已跑 tick ⇒ 零 C++ 改动、零功能影响，天然满足"心跳不改结果"。
- **D（统一呈现）**：A/B/C 的心跳都写同一格式（`ts / task / case / cycles_or_utime / eta`），由看板汇总 ⇒ 一条命令看全部节点与全部套件。

**判据与权衡（设计时必须满足）**

1. **心跳不得改变仿真结果**：chipyard 侧只允许写 stderr（不得进 `semi.out`）；gem5 侧走配置层分块，stats 口径不变；
2. **降速 < 1%**（实测对比心跳开/关的 cycles/s 与总墙钟）；
3. **必须能区分「慢」与「挂死」**：给出"最近 N 分钟周期增量 = 0"这类判据，而不是只有超时；
4. **与单二进制纪律兼容**：若选 B，须在批次开始时把 sim md5 一起登记（`m12-chipyard-016` 的判据已要求如此）。

**待裁定**

1. 是否允许为心跳**改 chipyard RTL 包装**（`TestDriver.v`）？—— 会影响 sim md5 与既有"冻结 sim `079ae015…`"的基线（选项 B）。
2. 若不允许，是否接受"只有宿主侧心跳（A）+ gem5 配置层心跳（C）"的折中（周期进度只能靠 A 的 utime 趋势推断）？
3. 心跳频率与落盘位置口径（默认 60 s / 写节点运行期日志 / 由看板汇总）是否按建议执行。

# 待定：机器/版本命名（用户 2026-11-14）

- **现状**：仓库里混用 `Machine-v5-*`（册名/机型前缀）与 `DADAO-v5`（我临时改的），QEMU 机器名是 `dadao-tiny`/`dadao-vast`。
- **用户口径**：机器名**既不应是 `Machine-v5` 也不应是 `DADAO-v5`**；`tiny`/`vast` 作为**机型名没问题**；`v5` 放在机器名里也不合适。**具体名字待用户确定**，确定前不做批量改名。
- **过渡处置**：`spec/Toolchain-01` 的适用范围已改为「本机（测试机）的汇编语言」，不再引入临时名字；其余 `Machine-v5` 引用保持现状，等命名定案后一次性改（涉及约 147 个文件，含册名、机型前缀、契约与工具）。

# M15：ISA 语义结构化（每条指令一段可解析 operation）

> **定位（用户 2026-11-12/13）**：M15 只做「**结构化**」——把 `spec/` 升级为「每条指令一段**可解析的 operation**」，**不执行**（执行归 M17）。M13 不加 IDL 任务；M14 已分配给内核。

## 目标与出口

- `spec/` 的每条指令记录带一段 operation 块（**语法可解析、语义单元唯一**），与编码字段、合法性规则、异常语义一一对应。
- 出口判据（候选）：264 条记录 **100%** 有 operation 块且 id 一对一；抽取结果与仓库内 `.idl` **逐字节一致**；6 族各一条完整族通过；`check-spec-*` 全绿。

### M15 候选任务（未立册，待批次授权后立）

| 候选号 | 内容 | 估时 |
|---|---|---|
| `m15-spec-001` | 语法 v0（`contracts/isa/idl-v0.md`）+ 5 条样板（add.so / ld.o / br.eq / lr.o.nn / trap）+ `extract.py` 原型 | 3–5 天 |
| `m15-spec-002` | 6 族形状定稿（alu/mem/ctrl/atomic/system/fp 各一条完整族）+ 共享函数层 | 5–8 天 |
| `m15-spec-003` | 全量 operations：264 条记录 → 约 90 个语义单元（按族参数化，共享函数 + 薄 block） | 25–35 天 |
| `m15-infra-004` | 抽取器 + L1 门控「spec 抽取结果 == 仓库 `.idl` 逐字节」 | 6–8 天 |
| `m15-infra-005` | 文档渲染：spec 里显示格式化 operation（不是原始 IDL） | 4–5 天 |
| `m15-spec-006` | 版本与只读锁同步、`Process-03` 附录条目 | 1–2 天 |

M15 exit：264 条记录 **100%** 有 operation 块且 id 一对一；抽取结果与 `.idl` 逐字节一致；6 族各一条完整通过；`check-spec-*` 全绿。

## 对标材料（先对标，再定语法）

> 只读参考、不复制实现；引用须带版本/commit。目的是**取形态不取内容**。

- **`riscv-unified-db`**（`manifests/references.lock.toml`；tarball 快照）：机器可读 ISA 数据的**形态**——`operation()` 挂在编码旁、`resolved spec` 展开、生成器矩阵（文档 / ISS / 头文件 / 解码包）；**不复制**其扩展体系、CSR、`X[]` 结构。
- **`DADAO-0628`**：Python 解释器（逐指令 handler + 合法性单列）与 Sail 两套独立实现的**经验**——「独立投影同一份散文规范」的纪律、哪些地方会产生歧义。
- **`DADAO-v5-pr4`**（tarball 快照）：RTL 侧**微操作分层**（24 个 op code + width/signed/dual/aux 的 28 字段 exec descriptor）与「生成器 vs 独立校验器」对偶、negative gate 写法；**微操作只留在 RTL 层，不进规范与分类**。
- **`DADAO`（旧仓）**：`ENV-linux` 与 opcodes/runtime 目录反映的早期编码与运行时假设（只作历史对照）。
- **仓内既有资产**：`contracts/opcodes.yaml`（编码真源）、`contracts/fp_semantics.yaml`（FP 语义投影）、`contracts/legality_rules.yaml`、`spec/SimRISC-0x` 附录 A（id 清单）、`spec/README.md`（分册与修订流程）、`docs/DDLN/B002`（ISA 语义模型讲义）。
- **外部标准形态**（只作形态参考）：ARM ASL（可执行伪代码 + 生成文档）、RISC-V Sail（形式化 + C 模拟器生成）、x86/ARM 官方手册的「伪代码块」体例。

## 设计取向（用户 2026-11-13 裁定）

- **以 `riscv-unified-db` 的 IDL 为准**（`doc/idl.adoc`：`Bits<N>` / `X(rs1)` / `jump()` / `raise(ExceptionCode::…)` / `function` / 配置常量），**优先复用其语法与工具**（`idlc`、`yamlidl`）；**只在不合适处扩展**，不自造"四不像"语法。
- 扩展方式优先用 **IDL 的 `function` 定义**（四 bank 读写、48 位地址、大端访存、cfx 分发），语言本身能不改就不改；确需语法扩展时单列「扩展提案」逐条裁定。

## 对标维度（讨论提纲）

1. **载体**：operation 写在 spec 正文每条指令旁，还是独立 `.idl` 文件（spec 只保留渲染视图）？
2. **语法**：表达式/语句形态（赋值、条件、位切片、内存访问、异常触发）；是否允许共享函数与参数化族。
3. **粒度**：一条指令一段，还是「族 + 参数」薄 block（如 264 → ~90 个语义单元）。
4. **单一真源**：spec 正文 ↔ `.idl` ↔ 契约投影 ↔ 测试期望，谁是源、谁是派生、如何机械校验（逐字节 / AST / 语义等价）。
5. **可执行接口**：为 M16 预留什么（签名、状态结构、内存与异常模型），但 M15 **不实现**执行。
6. **不自造第二套规范**：operation 不得成为与正文并列的"第二真源"；冲突时如何阻断（抽取器 fail-closed）。

## 待定

- 是否直接采用 UDB `idlc` 作为抽取器（版本/许可证/可离线），还是只借语法、自写抽取器。
- 是否在 M15 就冻结 `.idl` 语法版本（`contracts/isa/idl-v0.md`）并进 L1 门控。
- 渲染形态（spec 里显示格式化伪代码，而非原始 IDL）是否需要单独任务。
- 语料次序：先 5 条样板 → 6 族各一条 → 全量，是否按此三阶段立册。

## 待裁定：`tests/inst` 载体整理（用户 2026-11-15 提出）

- **已授权在执行**：汇编宏去重下沉 ⇒ `m15-testcases-001`（9 个重复宏 / 8 文件，零语义变化）。
- **待用户选**：两个 lds（`01-load-store/inst-tiny.lds`、`07-floating-point/inst-tiny-fp.lds`）归到哪个目录——候选 `tests/inst/linker/`（主会话建议；与 `tests/shared/linker/` 呼应、不污染册与宏层）、`macros/`（与 `.inc` 混放，语义不同）、`00-isa-design/`（册内会混入非载体）。定了才动 lds + `run_asm_suite.py` 的 lds 解析（改成按册映射表）。
- **未授权**：272 个文件的头注释模板化（3,780 行重复头，占 13%）——收益最大但会引入生成器，需用户先定"只统一字段 / 加自动生成"。

## ISS-436 授权审计（2026-11-14，read-only 核查）

11 册失配的**最后一次改动**逐册核对提交信息（`git log -1 -- spec/<册>`）：

- `SimRISC-01` `511ec1b1` / `SimRISC-02` `1447f6fc` / `SimRISC-07` `c35d7146` / `SimRISC-08·09·10` `462c5850`：均为「裁定落地：…」，正文即用户浮点/移位裁定的落地；
- `DADAO-11·12·22` `14af8b8b`、`Machine-v5` `c539eba3`：spec 纯净化（去 scope / 去 ADR 引用 / 去阶段代号），对应用户「spec 不写 ADR、不写元话术、禁用 scope」的要求；
- `Toolchain-01` `7d5e45c5`：机器命名待定 ⇒ 改中性表述（用户 2026-11-14 讨论项）。

结论：**改动均有授权来源，缺的只是「同一变更内重算锁哈希」**（`Process-06 §5`）。⇒ 修复 = 重算这 11 册 sha256 + 追加注记（逐册写明授权出处），**不需要重新裁定**；但注记必须一册一条、可回溯到上述提交/裁定，不得批量刷哈希。

## ISS-435 裁定（2026-11-14，用户原话）

> 「ISS-435：严格按spec来」

- 落地：保留标记粒度 = **精确地址 + 访问宽度**；`sc` 成败只由「标记是否持有 + 键是否匹配」决定，**不得**因同字其它字节被写而失败。
- 三处落地：QEMU `m13-qemu-014`（去整字值 CAS）、chipyard `m13-chipyard-002`（去 `resvWord` 比较）、测试 `m13-testcases-037`（把 `m13-testcases-028` 的一次性探针 `probe_gran.S` 升为正式向量）。gem5 已合规。
- 多 hart「同址同宽 store 清除」当前无载体（单 hart）⇒ 只写实现、不造用例（GAP）。

# 三个里程碑之外

## 待用户裁定：ADR

### `SPEC-180t` 的 ADR

- 状态：待用户裁定。
- 结论：escape 合法偏移集 `{0,+4}` + `imms18[17:1]` SBZ ⇒ ILLI，按 `docs/Process-03` 命中外部契约变更/多方案/结论固化。
- 下一步：逐条确认 decision 后再立 ADR；未确认前只保留为遗留。

### ADR 状态（其余）

- `ADR-0043`/`0045`：已 `Accepted`。
- `ADR-0046`：仍 `Proposed`，等 Linux 实测后再收口。
- 不再改 0043/0045 的 decision；0046 保持 `Proposed`。

## 架构未决项

### cfx 范围（M10 后）

- 已实现：umon/jmon/smon/hmon/ptw/pmem/time/hart/power。
- 后置：cache/llc/uart、PMEM 区域分配、IPI、多 hart。
- 下一步：按 Linux 需求拆任务（M14 启动时）。

### U-mode / cg5 / 异步帧

- 状态：待讨论。
- 结论：U-mode 的 cfx 目标不设 ISA 限制，由 OS 策略决定；cg5 单帧、同步/异步分离、递归/重入尚未定。
- 下一步：等 cg7 与 escape 收口后再讨论。

### SBI 生产 provider / W1C

- 状态：后置。
- 结论：当前只有测试专用 provider；生产 provider、`DONE/ERROR` W1C、`WAIT` 属 Linux 集成阶段。
- 下一步：不在 M10/M11 通路内实现。

### CFX 审计保留的未决项

- IPI：只有接收端，没有发送服务/寄存器。
- TLB：当前**无规范定义**（此前实现只覆盖 invalid，没有 fill）；按 Linux K3 先定义再实现。
- `cfx_pmem_exist`：SEE 与 SBI 语义不一致。
- UART：实例号/索引语义未定义（Linux 阶段暂缓）。
- 下一步：确认哪些进入 Linux 前任务；不恢复已删除的审计文件。

### `TESTCASES-089t` 遗留

- `reserved.yaml` 是否拆册（当前同册承载「保留编码 ⇒ UNDI」与「reserved cfx 地址空间 ⇒ CFXMEM」两类语义）。
- `trap`/`escape` → reserved cfx 的 active 向量仍 deferred（`TESTCASES-033t`）。

## IDL 里程碑归属（用户 2026-11-12 裁定）

- **M13 不加任何 IDL 任务**（M13 收口判据不变：三平台差分矩阵冻结）。
- **M14 已分配给内核**，不占用。
- IDL 分 **M15 / M17**，分界 = **不执行 / 执行**：M15 见本文件一级节「M15：ISA 语义结构化」；**M17「可执行参考模型」**= 把 M15 的 `.idl` 跑起来，作第四方差分参照。（**M16 已改分配给 gem5 时序模型**，见 `milestones-m16.md`。）

### M17 候选任务（未立册；可执行参考模型）

| 候选号 | 内容 | 估时 |
|---|---|---|
| `m17-idl-001` | lexer / parser / AST / 类型检查（Python） | 12–16 天 |
| `m17-idl-002` | 解释器：加载 ELF、四 bank 状态、48 位地址/大端、异常与 monitor、trace | 10–14 天 |
| `m17-idl-003` | 差分接入：273（整数）+ 167（访存）+ 67（控制流）逐例与 QEMU 一致，纳入 L2 | 8–10 天 |
| `m17-idl-004` | 向量「算期望」派生（输入仍人挑，期望由 IDL 算；**不做输入自动生成**） | 8–10 天 |
| `m17-idl-005` | FP 特殊值语义（NaN/Inf/次正规/五类标志；数值舍入交引用库并显式标注） | 15–20 天 |

M17 exit：507 例与 QEMU 逐例一致；每个 operation 分支至少被一个向量走到；`make check-idl` 进 L2；分歧归因落 spec 裁定（**不是「IDL 一定对」**）。

# 待处理：清空 `.tao/knowledge/refs/`（用户 2026-11-15 已定；**执行时间点：M13 收口前后 或 M15**）

- 用户原话：「`.tao/knowledge/refs/` 目录下一步也要清空」。
- 影响：refs 内现有报告（`m12-016-embench-picolibc.{json,md}`、`m13-003-int-diff.{json,md}`、`m13-044-probe-coverage.tsv` 等）**不再作为结论载体**；结论改落根 `README.md`、`docs/DDLN/`、`.tao/archive/M*/README.md` 与台账。
- 清空前须确认：① 还有谁在引用（任务书/台账/门控）→ 先改成「结论已迁至 X」；② 删除 or 归档到 `.tao/archive/M*/refs/`；③ 是否同步改 `docs/Process-0x` 关于 refs 落点的规定。
- **在此之前：新任务不得再往 `refs/` 写文件**（`m12-integ-002` 已按此收窄）。

# 待处理：`tools/` 脚本台账与孤儿清理（2026-11-15；用户裁定**延后到 M13 收口前后 或 M15**）

- 现状（现场统计）：`tools/**` 下 **260** 个 py/sh；仅 `tools/testcases/README.md` 一份索引且只登记 **3** 个（该目录 120 个 ⇒ 117 无索引）；其余 7 个模块无 README，也无 `tools/README.md`；**53 个零外部引用**（如 `tests/inst` 侧的 `min_rom_probe_*` 整族、`tools/qemu/generate_{atomics,clmul,rol}_vectors.py`、`tools/gem5/check_b{1,2,4,6}.py`）。
- 待用户选口径：**A 归档到 `.tao/archive/tools/`（不删除，建议）/ B 直接删除 / C 只报告不动**。
- 建议任务形状（1–2 h）：8 模块补索引（路径/用途/入口/调用者）+ 零引用者逐个处置 + 新增 L1 `check-tools-index`（只报告不删除）。
- 另挂：`m12-chipyard-017` 里的 `engine_parity_run.sh`/`engine_parity_collect.sh` 按新规则属一次性编排、待迁回运行期目录。

## M16 未决（2026-11-15，待用户裁定）

### M16 现场：gem5/chipyard 比值 3.1–4.0×，主因是 gem5 取指无 icache（2026-11-15）

`m16-gem5-007 对标脚手架 + embench 集成` 实测（同 ELF、`-O2`、三例）：

| 例 | chipyard 拍 | gem5 拍 | 比值 |
|---|---|---|---|
| `ud` | 11 476 575 | 35 628 680 | **3.10** |
| `aha-mont64` | 6 949 075 | 25 574 829 | **3.68** |
| `depthconv` | 10 079 080 | 39 767 332 | **3.95** |

- **归因**：gem5 **取指/基础项占 |Δ| 的 80.2%–87.0%** —— `TimingSimpleCPU` **无 icache**，每指令 8 拍（7 拍 SRAM 往返 + 1 拍执行）；chipyard 硬件是 8-beat 摊销（~0.06 拍/指令）。次项：chipyard 侧取指摊销 `A` −1.13…−1.54 拍/指令、分支 `A2` −3.30…−7.77、块复制 `D′` −1.02…−1.67；正项 `B1` 乘法（模型 3 拍 vs 实测 1.00–1.30）。
- **含义**：当前比值**不是周期模型本身的误差**，而是 gem5 配置（无 icache）与 chipyard（8-beat 摊销）的结构差异。若目标是"模型对标"，应先决定是否给 gem5 配 icache 再比；否则 3–4× 的结论对模型改进没有指导意义。
- **同批发现的模型偏差**（建议 `m16-chipyard-001 周期模型收口复测` 一并复核）：`B1` 乘法实测 ≈1 拍（模型初值 3）；`B3` 除法硬件 1 拍（文档"待实测"、模型 0）。
- **另一条硬事实**：gem5 **SE 完全没有 semihosting** ⇒ Tiny 应用在 SE 上不可直接跑；`007` 给 `DadaoSEWorkload` 加了 `semihosting` 参数（默认 `NULL`、SE 行为逐字节不变、`--semihost on` 才开）。**待裁定**：是否接受该开关，还是改走 FS 方案。

### M16 未决之二：C 类（`ld/st`）拍数用哪个口径？（2026-11-15）

- **事实①**：`docs/core-wuming-cycle-model.md` 的 C 类写 **4–7 拍**；但 `m16-gem5-006` 实测 chipyard `ld.*` = **9**、`st.*` = **10**（存储侧零方差）。
- **事实②**：`006` 采用的算法是「用文档 **D 类**（块传送）模型在 **N=1** 处求值」⇒ 得 9/10，13/13 落在 ≤1 拍容差内。**但这条规则是在见到 chipyard 的 9 之后自决的**（原先取文档 C 行下界 4，差 5 拍），reviewer 判为**语义裁定**、不代裁。
- **选项**：① 承认 C 类 9/10 为实测真值，`m16-chipyard-001` 回填文档并把「C 行 4–7」记为**外推失效**（推荐：四源一致、且 D 模型在 N=1 的自洽性有算术依据）；② 保留文档 4–7，认为 chipyard 的 9/10 含了不该计的流水/取指开销，需先做拍数归因拆解再定；③ 双轨记录（模型按 9/10、文档保留 4–7 并注明偏差）。
- **影响**：`m16-gem5-007 对标脚手架 + embench 集成` 的报告要直接用这套拍数；`m16-chipyard-001 周期模型收口复测` 的"权威版本"取决于此。


**Timing 下数据访问只能 functional（不计时），要不要二期做真时序？**（`m16-gem5-006` 现场结论）

- 事实①：gem5 v25.1 **无 ISA 级 `readMem`**（`src/arch/{generic,dummy,x86}` 均无）；`ExecContext::readMem` 直调 `BaseSimpleCPU::readMem` ⇒ `panic`。x86/riscv 的 load 用 `initiateAcc/completeAcc` **两阶段**。
- 事实②：`006` 的落点是 `src/arch/dadao/inst.cc` 的 `Gem5B1Context` —— Timing 模式下数据访问走 `SETranslatingPortProxy` **功能访问**（与 SE 系统调用、ELF 装载同路径），**未触 `src/cpu/simple/**`**。
- 事实③（后果）：Timing 下数据访问**功能正确但不计时**；`NoncoherentXBar`+`SimpleMemory` 的真实时序**只作用于取指**；实测 `system.mem` 的 Timing 数据侧 **0 包**；`simCycles` 比 9.19× 主要由取指与墙钟启动开销构成。ld/st 的 9/10 拍来自**周期模型**（`docs/core-wuming-cycle-model.md` 现场解析），不是这次 Timing 跑出来的。
- **选项**：① 接受现状（M16 的时序=取指真实时序 + 数据按周期模型记账），把"数据侧真时序"列入 M17/后续；② 做二期：把执行核改成 `initiateAcc/completeAcc` 两阶段（需重构 bundle 执行，跨 `src/cpu/simple/**` 与 `src/arch/dadao/**`，属"高代价 + 跨模块"，按 ADR 判据应先出 ADR）；③ 折中：只对 `ld/st` 单元素类做两阶段、块传送仍按模型。
- **影响**：M16 的"真时序"表述边界（报告/门控措辞）、`m16-chipyard-001` 的周期模型回填口径、`M17`（可执行参考模型）是否接手。

### M16 待确认（周期模型文档口径，2026-11-14）

`m16-gem5-002` 现场解析 `docs/core-wuming-cycle-model.md` 生成 264 行表时遇到 6 处文档本身不闭合（已按类级口径自决，**需用户口头确认一次**）：

1. **16 条 FT 侧 FP 族**（`ftadd/ftsub/ftmul/ftfma/ftmax/ftmin/ftqcmp/ftsclb/ftscmp/ftrnd`、`fosub/fosclb/foscmp/fosgnj/fosgnn/fornd`）§3 无专行，只有 §2 B4「1–2」类级口径 ⇒ 表内落 B4 + `dynamic: fp-op`、值留空给 003/004。建议把文档词法改 `ftsgn*`→`f*sgn*`、行 70 的 `fo*`→`f*` 即可逐条定死。
2. `ext` = 2 拍属**推断**（无实测），已标来源与「待 003 复核」。
3. §3 行 75/76/77 的「全套」把 A 档写 `1`，与 §2 的 A 两档、§5 `shl.o`=2 冲突 ⇒ 表按 §2 两档解析（`shl.t`=2、`rem.st`=17）。建议文档改列消歧。
4. `clmul.o` 唯一 override（行 61 的 B1/3 是估计，行 87 + 行 117 实测 A/2）⇒ 记入表 `overrides`。
5. `jump/call/ret` 的 8/26/15 是**预取失效期上界**（文档 §5 称「`015` 收口时复测」，但 `m12-chipyard-015` 已完成、未回填）⇒ 表暂按现值；将来回填文档后**必须重跑生成器**（`check-wuming-cycles` 绑文档 sha256，会立刻红——设计意图）。
6. `B2`（1 可配）按「可配」处理，`value` 留空。

### 参考材料分工（`.cache/refs/`，只读参考、不复制实现）

- **`riscv-unified-db`**（`manifests/references.lock.toml` 已登记）：机器可读 ISA 数据的**形态**——`operation()` 挂在编码旁、`resolved spec` 展开、生成器矩阵（文档/ISS/头文件/解码包）；**不复制其 RISC-V 专属结构**（扩展体系、CSR、`X[]`）。
- **`DADAO-0628`**：Python 解释器（逐指令 handler + 合法性单列）与 Sail 两套独立实现的**经验**；尤其「独立投影同一份散文规范」的纪律。
- **`DADAO-v5-pr4`**（本次新增）：RTL 侧的**微操作分层**（24 个 op code + width/signed/dual/aux 的 28 字段 exec descriptor）与「生成器 vs 独立校验器」对偶、negative gate 的写法；**微操作只留在 RTL 层，不进规范与分类**。

### 参考材料落盘方式（2026-11-12 实测调整）

`riscv-unified-db` 与 `DADAO-v5-pr4` 两份参考材料**不用 git 镜像**，改为 **tarball 快照**（`manifests/reference-snapshots.toml` 记录 URL/commit/sha256）。

原因