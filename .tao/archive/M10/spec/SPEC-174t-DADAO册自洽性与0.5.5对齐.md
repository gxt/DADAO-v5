# SPEC-174t: DADAO-11/12/13/21/22/23 自洽性分析与修正（对齐 SimRISC 0.5.5）

**模块**：spec
**项目里程碑**：M10
**依赖**：SPEC-173t（SimRISC 0.5.6-rc 口径）
**状态**：已验证

## 执行环境
**执行环境**：本地（纯文档；spec 只读锁按授权更新）

## 接口规范

### 背景（用户 2026-10-25 要求）
用户准备对 DADAO 架构文档做**一次版本升级**，要求先对 **`DADAO-11/12/13/21/22/23`** 做**自洽性分析 + 修正**，尤其按 **SimRISC 0.5.5**（现 `spec/` 为 0.5.6-rc）调整。

### 输入
- `spec/DADAO-11-AEE-应用程序运行环境.md`、`DADAO-12-SEE-主管系统运行环境.md`、`DADAO-13-HEE-…`、`DADAO-21-ABI/数据表示`、`DADAO-22-SBI`、`DADAO-23-HBI`
- SimRISC 13 册（0.5.6-rc；以 0.5.5 已发布口径为基线）
- `.tao/contracts/contract-*.md`、`contracts/`、相关 ADR

### 分析维度（逐册 + 跨册）
1. **版本 / 引用**：册头版本、互相引用的章节号、对 SimRISC 的章节引用（0.5.x 已重排：cfx/`fence`/FP 位置变化）；
2. **术语 / 编号**：寄存器组（`rd`/`rb`/`rf`/`ra`）、cfx 编号、异常码、地址空间（48-bit / cfxha）、页大小（64 KiB）；
3. **语义一致性**：特权级与异常/中断模型、页表/MMU（`cfx_ptw`/`cfx_tlb`）、SBI/HBI 调用约定、ABI（参数/栈/结构体/`va_list`）；
4. **与 SimRISC 0.5.5 的差异**：指令语义（如 `cmp.u*` 的 -1、`rf0`、`ra`/RAS、`fence`/LR-SC）在 DADAO 层的表述是否过期；
5. **与 contracts 的一致性**：`contract-isa/abi/elf/dynlink` 的归一化叙述。

### 输出
1. **自洽性报告**（落任务书或 `.work/log/spec/`）：逐项「位置 / 现状 / 依据 / 建议 / 类型」；
2. **机械可改的直接修正**：引用、版本号、术语、明显笔误、过期数字；
3. **需用户裁定的冲突清单**：语义冲突/口径选择（**不擅自改语义**）；
4. **版本升级建议**：AEE/ABI/SEE/SBI/HEE/HBI 各册的建议版本号（由用户定）。
5. **`gen_spec_archive --apply` 与 `--verify` 口径统一**：`--apply` 目前仍会重建 `-rc` 目录；统一为跳过 `-rc`（与 INFRA-107t 的 `--verify` 口径一致）。
6. **`tools/spec/check_spec_purity.py --self-test` 锚点更新**：仍钉 `0.5.5-rc`，自 0.5.5 发布起即失败（不在 `make check`）；更新锚点并自证可达 FAIL。

### 约束
- 只改 `spec/DADAO-*`；**不改** SimRISC 册、不改 `contracts/`（除非用户另行授权）；
- `manifests/spec-readonly.lock.toml` 按 `tools/infra/check_spec_readonly.py` 提示更新（用户已授权本次分析/修正）；
- 不建归档；语义冲突留问。

## 验收标准
1. `make check`（L1，含 spec 全套门控）rc=0。
2. 报告覆盖 6 册、每个维度有结论；冲突清单逐条有依据（贴文件/行）。
3. 机械修正与报告一一对应（改了什么、为什么）。
4. 完成区贴真实命令、输出、退出码；冲突清单单列待用户裁定。

## 自洽性报告（6 册 × 5 维度）

**基线**：`spec/` 现行 SimRISC 为 `0.5.6-rc`，**已发布口径 = 0.5.5**；本报告以 0.5.5 为基线比对现行 13 册 + `contracts/` + `.tao/contracts/`。行号 = **改动后**行号（六册行数未变，证据 A10）。`C<n>` = 语义冲突编号（**只登记、未改**）。

**六册 × 五维度结论索引**（✅ = 无待办；⚠ = 见所列 C 编号；「机械 n」= 本册已改行数）：

| 册 | D1 版本/引用 | D2 术语/编号 | D3 语义（特权/异常/MMU/SBI/ABI） | D4 对 0.5.5 | D5 contracts |
|---|---|---|---|---|---|
| AEE | ✅ 机械 5（基线 2 + 术语 3） | ✅ 术语 3 处已修 | ✅ 本册无异常/MMU 正文（委派 SimRISC-00） | ⚠ C1 | ✅ 与 contract-abi 一致 |
| SEE | ✅ 机械 10（基线 2 + 跨册 2 + 册内 3 + 异常名 3） | ⚠ C10、C11 | ⚠ C5、C6、C7、C8 | ✅ 无过期指令表述 | ✅ 与 contract-see §1–§4 一致 |
| HEE | ✅ 机械 3（基线 2 + 引用 1） | ✅（`global_version` 滞后属发布项） | ✅ 与 SEE §4.4 / HBI 一致 | ✅ 不承载指令 | ⚠ `contract-exception` 仍 deferred（已登记） |
| ABI | ✅ 机械 11（基线 2 + 悬空 2 + 册内 7） | ✅ | ⚠ C3、C4 | ✅ 寄存器/大端/16 B 值 | ✅ 与 contract-abi 逐条一致（C2 契约侧写 `rb8`） |
| SBI | ✅ 机械 7（基线 2 + 引用 5） | ✅ cfx 编号全对 | ⚠ C2 | ✅ 指令示例全绿 | ⚠ C2（与契约「指针 `rb8`」冲突） |
| HBI | ✅ 机械 3（基线 2 + 引用 1） | ✅ | ⚠ C7、C9 | ✅ | ⚠ `contract-exception` 仍 deferred（已登记） |

### 维度 1：版本 / 引用

- **AEE**：册头 `0.9.3-rc` 与 ABI 同号（锁组 `AEE↔ABI` 一致）；基线串 `0.5.4→0.5.5`（L3、L132）；唯一跨册引用「详见 SimRISC-00」（L9）**指对**。⇒ 自洽。
- **SEE**：基线串已修（L3、L865）；`见 HEE 文档 §1/§2`（L337/425）→ 手册名；册内 `§5 异常进入伪代码`（L52）、`参见 普通页/超页的地址转换`（L106/147）→ `§标题`。⇒ 修后无悬空/无带节号跨册引用。
- **HEE**：基线串已修；`详见 HBI 文档 §3`（L47）→ `详见 HBI`。⇒ 自洽。
- **ABI**：基线串已修；**两处指向 AEE 的悬空引用**——`AEE §返回地址栈`（L63，AEE 无此节）、`详见 AEE`（L71，RASOF/RASUF 正文实为 SimRISC-00）⇒ 改指 `SimRISC-00`；册内 7 处数字节号（L117/240/260/282/290/293/343）→ `§标题`。⇒ 修后自洽。
- **SBI**：基线串已修；`参见 DADAO-21-ABI-应用程序二进制接口`（L13/37）→ `参见 ABI`；`见 HBI §3`（L447）、`（§3）`（L695）→ 去节号；示例注释内 ADR 指针（L359）删除。⇒ 自洽。
- **HBI**：基线串已修；`参见 SBI §1`（L11）→ `参见 SBI`。⇒ 自洽。版本互锁 `HEE↔HBI` 同号。

### 维度 2：术语 / 编号

- 六册术语与 0.5.5 一致：`cfxha`、`IP`、8/6/6/6/6、`.st/.ut` 后缀、四寄存器组；无 `PC`/`cfxcode`/`储存块`/`MISC-`/`scope` 残留（证据 A1/A3/A4/A6/A7/A9 + grep 复核）。
- **cfx 编号逐项核对**：SEE L20-36 表 ↔ SBI 各章掩码位 `~(1<<n)`：umon0/jmon1/smon2/ptw4/tlb5/cache6/hart15/llc16/pmem17/timer18/uart62/power63 —— 全部相符（SBI L69/304/524/612/712 等）。
- **地址 / 页大小**：48-bit VA、64-bit PA、PTBR 64；L1/L2 各 `2^13` 项 × 8 B = 64 KiB；普通页 64 KiB（8×8 KiB）、超页 512 MiB（8×64 MiB）（SEE L56-58/84-85/124-126/194/219）↔ AEE L88（`shl 42`）↔ SBI L133（页掩码 `0xFFFFFFFFFFFF0000` = 64 KiB、`0xFFFFFFFFE0000000` = 512 MiB）——逐项复算一致。
- **已修术语/名称笔误 6 类（涉 7 行；SEE:52 同行兼有引用修正）**：`ext.s`→`ext.so`（AEE:45）、`算数`→`算术`（AEE:47）、`即opcode`→`即指令名`（AEE:121）、`当前偏移运行模式`→`当前运行模式`（SEE:52）、裸 `PFTRAP`→`I/DPFTRAP`（SEE:99/140）、`GPTRAP/SPTRAP/PFTRAP/NxPERM`→表内规范名（SEE:652）。
- 遗留编号问题：`cfx_hart` 专有寄存器 rc 序列 0,2,3,4,5（SEE:525-529）缺 rc1 且无「保留」行，与 §4.6/§4.7 写法不一致（**C10**）。

### 维度 3：语义一致性（特权级/异常/中断、页表/MMU、SBI/HBI、ABI）

- **特权级/异常**：4 模式两位编码（SEE:11-16）↔ HEE cg3（13 寄存器）↔ HBI 复位初始态（HBI:25-27）自洽；异常原因表 SEE §4.1/§4.4 与 HEE §2 同号同义；异常进入 10 步（SEE:676-820）与退出 4 步（SEE:822-854）闭合——**除 C6/C7**。
- **页表/MMU**：PTE 位域（SEE §2.2.3/§2.2.4）↔ PTW/TLB 寄存器编号（cg8 rc0-3/rc8、cg9 ptbr、cg10 pthi、cg11 pahi、cg12 tlb control/start/size）↔ SBI §4/§5 服务表一致；「TLB 异常 ⊂ PTW 异常」在 SEE:497 与 SBI:285 表述一致。⇒ 无内部矛盾。
- **SBI/HBI 调用约定**：`trap cfxha, immu18` / `escape ... [excp_cause_ip, 4]` / `rd15` 分发 / `rd16-31`·`rb16-31`·`rf16-31` 传参，与 ABI §4 一致；**返回值 bank 与 ABI 冲突（C2）**。
- **ABI**：参数/栈/结构体/`va_list`（七字段 + callee 保存区 + 16 B 值半字序）逐条自洽；**内部矛盾 C3（通用聚合块序）与已知两读 C4（栈溢出区）**。
- **中断**：pending OR 语义、电平触发、低 cfxha 优先（SEE:654/695）自洽；但 `cfx_timer`「本地定时器」与资源作用域表冲突（**C5**）。

### 维度 4：与 SimRISC 0.5.5 的差异

- **指令名/语法层全部对齐**：六册示例助记符全部落在 `contracts/opcodes.yaml`（`check-spec-codeblocks` 663 行 PASS）；`add.so`/`mul.so` 双目的 + `rd0` 丢半（AEE:25/35）符合 SimRISC-00:55；`div.st`/`shr.uo`/`shr.so`/`ext.so`/`shl.o`/`ld.st`/`st.t` 与 SimRISC-01/04/08 一致。
- `escape` 双层偏移（编码 `imms18<<2` / 汇编 `imms20` 字节且 `%4==0`）与 SimRISC-11 §3 + Toolchain-01 §4 一致（SEE:666/830/853）。
- cfx 别名形（`cfx2rc cfx_x_y, rd`）与 SimRISC-11 §4 + Toolchain-01 §13「cfx 别名约定」一致；`fence`/LR-SC 六册不承载（无过期引用）；`rf0[4:0]` 浮点异常口径（SEE:652）与 SimRISC-00:87-110 一致。
- **过期表述 2 处（语义，未改）**：AEE:29/45「乘法 128-bit」与「除法前须扩展」（**C1**，0.5.5 窄位宽已为值语义、`div.st` 只取低 32 位）；SEE 把 `cfxld`/`cfxst` 当可用指令描述（**C8**，SimRISC-11 §5 仍「待定、暂不启用」）。

### 维度 5：与 contracts 的一致性

- `contract-abi`（0.9.2）↔ DADAO-21：寄存器角色、`rb2`=FP 无条件保留、返回 `rd8/rb8/rf8` 三 bank、16 B 值半字序、`va_list` 七字段、SP 16 B 对齐 —— 逐条一致；C3/C4 属 spec 内部问题（C4 契约 §4.3 已登记取舍）。
- `contract-see` §1–§5 ↔ DADAO-12/13/22：cfx 编号、reserved 范围、两层权限、异常进入步骤、SBI 错误码一致；**C2 在契约层写「指针返回 `rb8`」，与 SBI 表统一 `rd8` 冲突**。
- `contract-sbi.md`/`contract-exception.md`/`contract-mmu.md` 仍 deferred（`spec/README.md` 投影表已登记），本次未动；投影未漂：`check-cfx-aliases` byte-identical、`check-spec-cite-targets` unresolved=0。

### 冲突清单（语义，**未改**，待用户裁定）

| # | 位置 | 现状 | 依据 | 建议 |
|---|---|---|---|---|
| C1 | AEE:29、AEE:45 | 「乘法结果为 128-bit…32-bit 乘积取低 64 位即可」「除法前须确保被除数/除数高位正确扩展」 | SimRISC-08 §1.3「源操作数只取 size 范围内低位，结果仅保留 size 位宽并按符号/零扩展」；SimRISC-04 §2.2 值语义通则（0.5.5 起无「高位保留」）；32 位 `mul.st` 为**单目的 64 位**，128-bit 双目的仅 64 位 `.so/.uo` | 把 128-bit 说明限定到 `.so/.uo`；删/改「除法前须扩展」（`div.st` 已不看高位） |
| C2 | SBI:129/441/444 等；ABI:337/341；contract-see §5 | SBI 所有服务（含**地址类** `SBI_PTW_GET_PTBR`/`SBI_PMEM_GET_PM_START`）统一返回 `rd8`；ABI §3.4 规定「绝对地址 → `rb8`」；契约写「指针返回 `rb8`」 | ABI:341；contract-see §5；SBI 各章返回列 | 二选一：SBI §1 明示「服务返回值统一 `rd8`（覆盖 ABI bank 规则）」，或地址类返回改 `rb8` |
| C3 | ABI:231 vs ABI:238 | 通用聚合「高位块先入**高**寄存器」，与紧随的 16 B 值规则「高半字在**偶号（低号）槽**」及其依据（大端 + `ldm/stm` 寄存器号递增 = 地址递增）**相反** | SimRISC-01 `ldm/stm` 语义；ABI:238 自述依据 | 改为「高位块入**低号**寄存器」，或显式定义块序（影响 codegen，须裁定） |
| C4 | ABI:247 | 同一句并存「按声明顺序从左到右」与「各组溢出参数连续紧凑存放」两种读法 | contract-abi §4.3 已登记：用户裁定取**全局声明序**，spec 未消歧 | 按 C4 裁定补一句消歧（契约层已定，正文待补） |
| C5 | SEE:50 vs SEE:600 / SBI:510-513 | 资源作用域表 `cfx16–cfx63` 全 `per-system`，但 `cfx_timer`(18) 是「**本地**定时器」、SBI 侧按 hart 各自 `SET_TIMER` | SEE:44-50、SEE:600、SBI §10 | 或把 timer 移到 per-hart 编号段（需同步 HHE/HBI/SBI 的 `1<<18`），或作用域表加「timer 例外=per-hart」 |
| C6 | SEE:695 vs SEE:792-794 | prose 只说**异步**被 `excp_cause_mask` 屏蔽时进 pending；伪代码对**同步**被屏蔽也「置 pending 并 return」（既不 ILLI、也不再重试） | SEE §5.2 步骤 5 与伪代码 | 明确同步可屏蔽语义（⇒ pending 丢弃现场 / ⇒ ILLI / ⇒ 不支持屏蔽），二者取一 |
| C7 | HBI:51-53 + SEE:826-853 + SEE:765-775 | 移交前把 `excp_prev_cfx_mask` 设**全 1**；`escape` 只恢复 mask/run_mode、**不恢复 `inner_cfx_code`**（仍为 63）⇒ 进 supv 后首个 `trap cfx_smon` 命中「目标 ≠ 自身 且 inner mask 屏蔽」⇒ ILLI，内核无法发起任何 cfx 调用 | HBI:51-53（「全 1 = 不允许任何 cfx 发生异常」）、SEE:765-775 步骤 3、SEE:846-849 | 移交时 prev mask 置 0，或新增 `inner_cfx_code` 恢复路径；须裁定 |
| C8 | SEE:381/662/683 | 按可用指令描述 `cfxld`/`cfxst`（SRAM 块寄存器、任意模式执行、异常路由） | SimRISC-11 §5「待定（deferred）…暂不启用」，未实现机器 decode ILLI | SEE 加「本组待定，以 SimRISC-11 为准」限定，或待 SimRISC-11 定稿后回填 |
| C9 | HBI:32-45 | 注释说「清除**各 cfx** 的 cg 委托、允许 supv 访问所有 cg」，代码列 12 个 cfx，**漏 `hmon`**(cfx3) | HBI:32 注释 vs 34-45 列表 | 若有意排除 hmon，改注释「除 hmon 外」；否则补一行（会改变启动行为，须裁定） |
| C10 | SEE:525-529 | `cfx_hart` 专有寄存器 rc=0,2,3,4,5，rc1 未列且未标「保留」 | 同册 §4.6/§4.7 均显式写「保留」 | 补 rc1 保留行或说明 |
| C11 | SEE:289 | 「硬件应至少支持 `cfx_umon_user_*` **或** `cfx_smon_user_*` 这一组寄存器」，但 §5.2 步骤 1 把 U-mode 同步异常**固定**路由到 `cfx_umon` ⇒ `smon_user_*` 无触发路径 | SEE:289 vs SEE:686/713-717 | 删去 `smon` 选项，或说明何时路由到 smon |

### 机械修正清单（39 行，1:1 行内替换，**0 行增删**；与上表逐项对应）

1. **册头基线串** `SimRISC 0.5.4 → 0.5.5` ×6：AEE:3、SEE:3、HEE:3、ABI:4、SBI:3、HBI:3（对齐已发布基线）。
2. **未发布段基线条目** ×6：AEE:132、SEE:865、HEE:61、ABI:406、SBI:843、HBI:79（同段仍 `-rc`，条目随册头一致）。
3. **跨册引用** ×10：SEE:337/425、HEE:47、SBI:13/37/447/695、HBI:11（改手册名/去节号，按 `spec/README.md`「跨册引用只写手册名」）；ABI:63/71（原指 AEE 的**悬空**节，改指 `SimRISC-00`——RAS 正文所在册）。
4. **册内引用** ×10：SEE:52/106/147、ABI:117/240/260/282/290/293/343（数字节号 → `§<标题文本>`，按同一条维护约定）。
5. **术语/名称/异常名** ×6 行：AEE:45（`ext.s`→`ext.so`，0.5.5 无 `ext.s` 助记符）、AEE:47（算数→算术）、AEE:121（`即opcode`→`即指令名`，opcode≠助记符）、SEE:99/140（裸 `PFTRAP`→`I/DPFTRAP`）、SEE:652（`GPTRAP/SPTRAP/PFTRAP/NxPERM`→`I/DGPTRAP`、`I/DSPTRAP`、`I/DPFTRAP`、`N{R/W/X}PERM`）；另 SEE:52 之「当前偏移运行模式→当前运行模式」与其引用修正同一行（计入第 4 组）。
6. **项目痕迹** ×1：SBI:359 示例注释删「，见 ADR-0013 D11」（规范正文不写 ADR 指针）。

### 版本升级建议（由用户定；互锁组须同号）

- **方案甲（推荐，最小）**：**不升号**——`0.9.3-rc / 0.7.2-rc / 0.1.3-rc` 三段**均未发布**，本次机械修正并入该 `-rc` 段；发布时去 `-rc` 补日期并同步 `*_global_version`（见下）。理由：无编码/语义变更，仅引用与术语修正。
- **方案乙（把「对齐 0.5.5」作为可追溯里程碑）**：新开 `y+1` —— **AEE/ABI = 0.10.0-rc**、**SEE/SBI = 0.8.0-rc**、**HEE/HBI = 0.2.0-rc**（当前未发布段转正式版 0.9.3 / 0.7.2 / 0.1.3 并补日期）。理由：基线换版对读者可见。
- **若采纳 C1/C3/C5/C7 中的指令/ABI/编号语义改动** ⇒ 必走方案乙（语义变更须 `y+1`），且 `cfx` 编号变更同时牵动 HEE/HBI/SBI。
- **发布同步项（无论哪个方案）**：`cfx_*_user/jail/supv/hypv_global_version` 初值与「当前 x.y.z」文本按**发布版**+1：AEE/ABI `0x0009_0002`→发布版、SEE/SBI `0x0007_0001`、HEE/HBI `0x0001_0002`；HBI/SEE/SBI `GET_VERSION` 示例常量同步（SBI:42/49/57/98、HBI:19、SEE:274/320、HEE:13）。

## 附录：本次未改 SimRISC 册 / 未改 `contracts/`

- `spec/SimRISC-*`：**0 改动**（`check-spec-readonly` 13 册 sha256 与锁一致）。
- `contracts/*` 与 `.tao/contracts/*`：**0 改动**；仅报告 `contract-abi.md §1.5` 的既有悬空引用（已列入完成区遗留）。

## 完成区
**测试结果**：证据脚本 `.work/evidence/SPEC-174t/run.sh` → `PASS=19 FAIL=0`（rc=0，含 `make check`）；`make check` rc=0 / `check-spec-readonly` 21 册 OK / `check-cfx-aliases` byte-identical / `check-spec-codeblocks` 663 行 / `check-spec-purity` 13 册 hits=0。
**修改文件**：`spec/DADAO-11`、`-12`、`-13`、`-21`、`-22`、`-23`（各 1:1 行内替换，**0 行增删**，合计 39 行）；`manifests/spec-readonly.lock.toml`（6 册 sha256 + 授权/变更注释）；`tools/spec/check_spec_purity.py`（自检锚点现场派生）；`tools/spec/gen_spec_archive.py`（`--apply` 跳过 `-rc` + 自检）；`.work/evidence/SPEC-174t/run.sh`（新增）。日志 `.work/log/spec/SPEC-174t-*`。**越界披露**：`.tao/knowledge/milestones.md` L50 仅改状态单元格（`待开始`→`待验收`）——`check-milestones-fresh` A1 强制流水行 == 任务书状态，属机械镜像、非知识内容。
**验收结果**：`make check` rc=0（日志 `.work/log/spec/SPEC-174t-check-final.log`）；证据脚本 `PASS=19 FAIL=0`、rc=0（`.work/log/spec/SPEC-174t-evidence-full.log`）；冲突 11 条**未改语义**，单列待裁定。
**新发现/坑**：
① `.tao/contracts/contract-cfx-aliases.md` 以 **DADAO-12/13 行号**溯源 ⇒ 改这两册只可**行内替换**（行数不变），否则须重生成投影（本次加断言 A10 守此不变量）。
② `check_spec_purity.py --self-test` 钉死版本串属**易腐锚点**（每次发布/新开 `-rc` 即假红）；已改为从册头现场派生。
③ `gen_spec_archive.py --apply` 与 `--verify` 口径曾不一致（前者会重建 `-rc` 目录）；已统一为 SKIP，并把「注入 `is_rc→False` ⇒ 自检红」纳入证据。
④ 六册「`*_global_version` 初值 = 上一发布版」是**有意滞后**（-rc 未发布），发布时才 +1，勿误判为过期数字。
**遗留问题**：冲突 C1–C11 待用户裁定（语义，本次不改）；`.tao/contracts/contract-abi.md §1.5` 仍写「见 [DADAO-11 §返回地址栈]」（正文已改指 `SimRISC-00`，契约侧悬空**未改**，属任务书禁止范围）；版本号建议见 §版本升级建议（由用户定）。

## 审阅记录

#### 第 1 轮 engineer 自审
自审范围：6 册 39 处行内替换 + 2 个工具 + 锁文件 + 证据脚本（逐行）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 首轮证据 A8 红：SEE:99/140 仍有裸 `PFTRAP`（非表内规范名） | ✅已修 | 2 行 → `I/DPFTRAP`（与 SEE:257 同写法） | A8=0 行；`make check` rc=0 |
| F2 新参数 `archive` 使 `verify_one` 的 `dest.relative_to(REPO)` 对临时树可抛 `ValueError` | ✅已修 | 加 `is_relative_to(REPO)` 分支 | `--self-test`/`--verify` 复跑绿 |
| F3 purity 自检用 `assert` 报锚点缺失（栈回溯、信息不明确） | ✅已修 | 改为打印「应恰 1 条、实得 N 条」并 `return 1` | 注入 C3（册头无版本行）⇒ rc=1 |
| F4 是否需重生成 `contract-cfx-aliases.md`？ | ❌不修 | 六册行数不变（A10），行号溯源不漂 | `check-cfx-aliases: PASS (byte-identical)` |
| F5 语义冲突是否顺手改（C1–C11）？ | ⏸延后 | 任务约束「语义冲突只登记、不擅自改」 | 冲突清单已落报告，逐条带文件/行 |
| F6 锁文件是否合规（用户授权 + 同变更） | ✅已修 | 6 册 sha256 + 授权依据注释（任务书 §背景原话） | `check-spec-readonly: 21 read-only spec volume(s) OK` |

判决：F1–F3、F6 已修并复验；F4 判不需改（有门控证据）；F5 按约束延后并登记 ⇒ **任务状态置 `待验收`**（无未修 finding 阻塞验收）。

#### 第 1 轮 reviewer 验收

**重跑记录（本人执行，workdir=仓库根）**
1. `make check` → 尾行 `repository checks (L1): PASS`，`MAKE_CHECK_EXIT=0`（日志 `.work/log/spec/SPEC-174t-reviewer-make-check.log`，584 行、无真 FAIL）。关键子项：`check-spec-readonly: 21 read-only spec volume(s) OK`、`check-cfx-aliases: PASS (byte-identical)`、`check-spec-codeblocks: PASS (663 行)`、`check-spec-purity: files=13 rules=11 hits=0`、`check-spec-cite-targets: unresolved=0`、`check-numbering/check-spec-changelog/check-milestones-fresh` 均 PASS。
2. `bash .work/evidence/SPEC-174t/run.sh` → `SPEC-174t evidence: PASS=19 FAIL=0`，rc=0（日志 `SPEC-174t-reviewer-evidence.log`；`diff` 与 engineer `SPEC-174t-evidence-full.log` 逐行一致——输出真实性核对通过）。含 B4 `make check rc=0`。
3. `python3 tools/spec/gen_spec_archive.py --verify` rc=0（`0.5.5-rc`/`0.5.6-rc` 打印 SKIP）；`python3 tools/spec/check_spec_purity.py --self-test` rc=0（5 case）；`gen_spec_archive.py --self-test` rc=0（6 case）；`python3 tools/infra/check_spec_readonly.py` rc=0 → `21 read-only spec volume(s) OK`。
4. **独立反例注入**（cp 备份 + md5，非 engineer 自检）：AEE 册头 `0.5.5→0.5.4`（pre md5 `541e9173…`）⇒ 重跑同一脚本 rc=1：`A1 实际=1 行`、`A2 实际=5 册`、`B3 rc=1`、`C5 1/0`、`PASS=14 FAIL=4`；`cp` 还原后 md5 复等 `541e9173…`，再跑 `--skip-make-check` ⇒ `PASS=18 FAIL=0` rc=0。工具反例另独立注入：`g.is_rc=lambda _v:False` ⇒ `--self-test` rc=1（apply 建出 `SimRISC-0.0.0-rc`、SKIP=False）；剥除册头版本行 ⇒ `[FAIL] …应恰 1 条，实得 0 条` rc=1。两者均可达 FAIL。
**机械修正核对**：`git show 923cdb58 --numstat` 六册 = 5/10/3/11/7/3（增=删，合计 39/39、净 0）；父提交 `d4d4057f` 行数 142/876/66/415/847/83 与现树逐册相等（A10 写死值经本人对父提交独立复核成立）。逐行读全量 diff：仅 ①基线串 `0.5.4→0.5.5`（册头+未发布段 12 处）②跨册引用改名/去 §（10）③册内数字节号→`§<标题>`（10）④术语/异常名（6 行：`ext.s→ext.so`、算数→算术、即opcode→即指令名、`PFTRAP→I/DPFTRAP`、`GPTRAP…→表内规范名`、当前偏移运行模式）⑤删 ADR 指针（SBI:359）——与清单 39 行一一对应；`spec/SimRISC-*`、`contracts/*`、`.tao/contracts/*` 在 commit 中 **0 命中**（`contract-abi.md` 等未动）。
**冲突抽查（读原文，5 条含 C2/C3/C7）**：C2 — SBI:129 `SBI_PTW_GET_PTBR … rd8 = base`、ABI:341「绝对地址→rb8」、contract-see:54「指针返回值用 `rb8`」，三方冲突属实；C3 — ABI:231「高位块先入高寄存器」vs ABI:238「高位半字在偶号（低号）槽」+ SimRISC-01 `ldm/stm` 寄存器号递增=地址递增，矛盾属实；C7 — HBI:51-53「prev_cfx_mask 全 1」+ SEE:846-849 `escape` 只恢复 mask/run_mode（无 `inner_cfx_code`）+ SEE:765-775 同步被屏蔽→ILLLI，链条属实；C1 — AEE:29/45 与 SimRISC-08:58「只取 size 范围内低位」冲突属实（AEE:45 仅改助记符，语义句未动）；C9 — HBI:32 注释 vs 34-45 仅 12 个 cfx、漏 `hmon`(cfx3，表见 SEE:21-24) 属实。行号全部对得上，未夸大、未编造；C1–C11 所列行在 diff 中**一处未改**。
**§标题命中逐条手核**：SEE:52→`5.2 异常进入流程`、SEE:106/147→`2.2.2/2.2.1`、ABI:117/240/260/282/290/293/343→`3.2.3/3.4/3.2.4/3.2` 等 10 处全部指向真实标题；跨册 10 处均改手册名，符合 `spec/README.md`「册内 `§<标题>`、跨册只写手册名」。
**约束核验**：只改六册+锁+两工具+证据脚本+任务书（+披露的 milestones 状态单元格 1 行）；语义冲突只登记不改 ✓；不建归档 ✓；快照对账：审查前后 `git status --porcelain -uall` 均为空、10 个目标文件 md5 与审查前快照 `diff` 为空（`/tmp/opencode/SPEC-174t-review/`），无残留（`*.preinject` 已删）。
**发现（文档级，不阻断）**：① AEE:121 除「即opcode→即指令名」外同加反引号（清单未单列，纯格式）；② 报告「AEE §返回地址栈（AEE 无此节）」措辞偏硬——AEE:7 §1 标题含「返回地址栈」但非独立节、正文无 RASOF/RASUF（SimRISC-00:125-153 才有），悬空判断在 § 约定下仍成立；③ A10 期望行数写死，后续合法增行会假红（维护提示）；④ 册内自由文本 `§<标题>` 无门控（`check-spec-refs` 只审 contract-*.md、`cite-targets` 只审 YAML `spec_cite`），本次由 reviewer 手核——可考虑后续入门控。
**判决：Accepted**——验收命令块在本人重跑下全部通过、机械修正 39 行对称且仅含允许类别、5 条冲突抽查真实且未改、工具反例独立可达 FAIL。冲突 **C1–C11 与各册版本号选择（方案甲/乙）留给用户裁定**，architect 终审。
