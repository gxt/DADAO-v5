# MEMORY — DADAO-v5 入口页（指针 + 偏离/不做台账 + 指令系统要点）

> **维护规则**：本页承载三样——① **入口指针**（导航）；② **偏离 / 不做台账**（**唯一一份**，含上游偏离 + v5 自身决定不做）；③ **指令系统要点**（`docs/DDLN/DD-B*`「本册要点」的汇总镜像，用户 2026-10-25 指定）。①/② 之外不复制其它事实（进度 / 版本 / 决策各归真源；复制必漂移）；③ 是**快照**，`docs/DDLN/DD-B*` 改稿后须同步本页。

## 入口指针

| 主题 | 真源 |
| --- | --- |
| 项目总览 / 里程碑 / 版本号 | 根 `README.md` |
| 当前进度 / 任务流水 / 规划中 / 裁定 | `.tao/knowledge/milestones.md` |
| M9 收尾 / 回顾 / 未决项 | `.tao/archive/M9/m9-retrospective.md`（M10 进度见 `milestones.md` 任务流水） |
| 决策（ADR：架构 / 契约 / 流程） | `.tao/adr/` |
| 交互目录（`$TAO_ROOT` / 结构 / 模块表） | `.tao/README.md` |
| 角色 / 流程 / 命令 | `AGENTS.md`「角色与流程」+ `.opencode/agents/`、`.opencode/commands/` |
| 任务文件 | `.tao/tasks/<module>/` |
| 技术规范（上游 + v5 自定；索引 / 投影表） | `spec/` + `spec/README.md` |
| 工程流程规范 + 仓库级索引 | `docs/Process-0x` + `docs/README.md` |
| DDLN 讲义（定稿索引 / 草稿） | `docs/DDLN/README.md`（草稿 `TT-*` 由 `docs/DDLN/.gitignore` 忽略） |
| 合约（归一化叙述 / 机器可读数据） | `.tao/contracts/contract-*.md` / `contracts/` |
| 代码模型 / 打包规范（REL26 边 ≤ 32 MiB；单 DSO 可执行区跨度 < 30 MiB） | `.tao/adr/adr-0036-code-model.md` §D4/D7 + `make check-code-range` |
| 参考仓库（只读工作树 / 锁文件） | `.cache/refs/` + `manifests/` |
| issue / 教训 | `.tao/knowledge/issues.yaml` / `.tao/knowledge/lessons.md` |
| 历史归档 | `.tao/archive/M*/`（M1–M9；含 `README.md` + `m<i>-retrospective.md` + `issues-closed.md`） |
| 临时 / 一次性产物 | `/tmp/opencode/<任务ID>/` |

## 偏离 / 不做台账（唯一一份）

> **第 1–7 项** = 上游 spec 与 v5 决策之间的**规范性偏离**（M2 门槛⑤成型；`SPEC-106t` 增至 7 项）；**第 8–10 项** = **v5 自身决定不做**的事项（非上游偏离，无 ADR，记此仅为单一清单）。每项均由**已 `Accepted` 的 ADR**（或 M1→M2 过渡任务 `SPEC-086t`）固化；本节只做**归一化登记 + 指针**，不新增决策，权威决策见 `.tao/adr/`。`scope`、`RACNT`、`MRPTR`、exit 码等写法与 `contracts/opcodes.yaml`、ADR 一致。
>
> **位置（2026-10-11，`INFRA-063t`）**：本台账原在根 `README.md`，按用户裁定「放在 `.tao/knowledge/MEMORY.md` 中更合适」迁入本页；根 `README.md` 只留项目总览 / 里程碑 / 版本号。

| # | 偏离点 | 上游依据 | v5 决策 | ADR / 契约指针 |
|---|--------|----------|---------|----------------|
| 1 | **exit port（程序停机）** | `SimRISC-11 §退出指令`：`escape cfxHA, [excp_cause_ip, imms20]`（**退出特权态**，非停机；编码层 `imms18`） | 自定 **exit port** MMIO（`0xffff_8000_0000`，8 B，只写）；退出码 = `0x80 \| cause_bit`；写入后 `cpu_loop_exit()` 锁定 | **ADR-0004 §D3**（Exit Port 协议）+ **ADR-0011 §D1–D4**（可靠 halt） |
| 2 | **`fence` SBZ 非零** | `SimRISC-11 §fence指令`：`immu18 bits[17:4]` 为 SBZ，**非零值行为保留** | v5 定**非零 SBZ → ILLI**（`0x88`）；`fence` 已在 `M9` 实现（`scope: m9`，见第 6 项） | **ADR-0004 §D5.3**（SBZ 非零 → ILLI）+ **ADR-0014 §D1–D3**（fence 移出 M1；后被 `SPEC-164t`/`ADR-0034` 转入 `m9`）；`contracts/opcodes.yaml::fence_oiii_imm` |
| 3 | **测试机地址映射 / 复位值** | `spec/` **无测试机层**（`DADAO-12 §2.1` 仅给核内地址空间模型，无内存映射 / 复位值全集 / exit 协议） | 采用 spec 核内地址空间模型（cfxha 63/power）：boot ROM `0xffff_ffff_0000`、RAM `0xffff_0000_0000`(16 MiB)、Exit port `0xffff_8000_0000`；复位 PC=`rb0`=boot ROM；`rd0`/`rb1`–`rb63`/`ra0`–`ra63`/`rf1`–`rf63` 复位 `0`、`rf0` 复位 `0x7FF8_0000_7FC0_0000`（架构自定义确定性复位） | **ADR-0004 §D1/D2**（内存映射、复位向量与复位值） |
| 4 | **`ra0` 语义（MemRAS 简化）** | `SimRISC-00 §返回地址栈`（v5 修订前；对照归档 `.tao/archive/SimRISC-0.5.3/SimRISC-00`）：`ra0` 高 16 位 = **MemRAS 引用计数** | v5 `ra0` = `[63:54]` SBZ + `[53:48]` **`RACNT`** + `[47:0]` **`MRPTR`**；**取消 MemRAS 引用计数**；有效性判据 = `RACNT` | **ADR-0012 §D7**（D7.1–D7.7） |
| 5 | **`e_flags` 版本字段** | `spec/` **无 ELF/Object ABI**（`e_machine`/`e_flags` 无依据） | `e_machine = EM_DADAO (0x0DA0)`（project-custom，未注册）；`e_flags = 0x00000001`（bits 0–7 = 对象/ABI 格式版本 = 1；bits 8–31 保留 0） | **ADR-0003 §D1**（含 `## 修订` 的 `e_flags` 版本字段）；投影 `contract-elf.md §1.3` |
| 6 | **M1/M2 排除口径**（**订正**） | 上游把浮点（`SimRISC-07`）、cfx（`SimRISC-11 §核芯功能扩展指令` + `DADAO-12/13`）、LR-SC 与 `fence`（`SimRISC-12 §原子指令`）均定义为架构指令 | v5 用 `scope ∈ {m1, fp, excluded}` 划范围：`m1` 已实现；**`fp` 66 条已实现（不再是 ILLI）**；`fence` + `lr/sc` 24 条已实现（`scope: m9`）；`excluded` **2 条**（`cfxld`/`cfxst`）仍 decode **ILLI** | **ADR-0012 §D3.1**（0 号寄存器/范围）+ **ADR-0014**（fence 首次 excluded）+ **ADR-0034**（原子编码；`## 修订` 记 `op 0x77→0x47`）+ `SPEC-086t`（scope 口径，`contracts/opcodes.yaml` + `check_scope.py`）+ `SPEC-164t`（fence/lr/sc 转 `m9`、`ct*` 并入 `OPC-MISC`）（2026-10-22 按现场订正） |
| 7 | **汇编伪指令集收缩**（删上游 5 类伪指令） | `SimRISC-0.5.4 §伪指令`：定义 18 条伪指令，含 `nop`/`return`/`not.{b,w,t,o}`/`neg.{b,w,t,o}` 共 10 条 1:1 别名 | v5 只保留「ISA 无法直接表达、需多指令合成」的 **8 条合成型**（`set.rd`×2/`set.rb`×2/`set.ft`×2/`set.fo`×2）；删除 10 条 1:1 别名（`nop`→`swym 0`、`return`→`ret rd0, 0`、`not.*`→`xnor.o`、`neg.*`→`sub.sX`）；`ret` 不加无参形态；反汇编只显真实指令 | **ADR-0013 §D11** |
| 8 | `ISS-093` 行内 code span 检测 | —（v5 自身，非上游偏离） | **不做**：`check_asm_prose.py` 不查反引号内旧格式；`INFRA-021t` 方案 b 评估为风险>收益。**复查**：出现行内 span 回退再评估保守版 | —（见 `ISS-093`） |
| 9 | `ISS-108` LLVM 侧两文件 >1000 行 | —（v5 自身，非上游偏离） | **不做**：`Process-01 §11` 建议性非强制；拆分会牵动补丁树与全部门控，零功能收益。**复查**：出现维护痛点再评估 | —（见 `ISS-108`） |
| 10 | `ISS-054` 探针标签化框架 | —（v5 自身，非上游偏离） | **不做（M9）**：收尾不改工具链；手算偏移风险由 `ISS-309`（harness 偏移修正）部分缓解。**复查**：再出现手算偏移错误即立项 | —（见 `ISS-054`） |
> **订正说明（第 6 项）**：历史表述「浮点未实现 ⇒ decode ILLI」在 `QEMU-034t`~`037t`（执行层 60/60）后**已不成立**；现行口径为「**浮点已实现**（`scope: fp`），**仅** cfx/LR-SC/fence（`scope: excluded`）仍 ILLI」。本台账以此为准。
>
> **章节订正（实测）**：部分历史任务书沿用 **SimRISC 0.5.3 编号**；v5 现行规范为 **0.5.6-rc**（已发布 0.5.5），分册与章节已重排——上游依据「exit port vs `escape`」现位于 `SimRISC-11 §3 退出指令`（0.5.3 为 `SimRISC-04`）、`fence` SBZ 现位于 `SimRISC-12 §1.1 fence指令`（0.5.3 为 `SimRISC-04`）、浮点规范为 `SimRISC-07`（0.5.3 为 `SimRISC-03`）。均以 `contracts/opcodes.yaml` 的 `spec_cite` 实测为准。

## 指令系统

> 本级为 `docs/DDLN/DD-B001..B011` 各册「本册要点」的**快照**（2026-10-25）；DD-B* 改稿后须同步本页（见页首维护规则 ③）。

### DD-B001-大道至简--设计理念

- **简单** = 清晰简洁的内部设计与接口逻辑；**实用** = 模拟器 / FPGA 可实现，性能可接受。
- 设计顺序：边实现边定义，不先写死 ISA；软硬件相互依存。
- DRY：复用 generic 实现，避免重复造轮子。
- 为什么要新 ISA：教学载体、没有历史包袱、在 RISC 上做探索、软硬件协同。
- 为什么 64 位：字长/寄存器/地址一起定，位域够用，没有 32 位包袱。
- 为什么 RISC：规整、load/store、可实现可验证；但不教条。
- 数据宽度命名：byte/wyde/tetra/octa（Knuth/MMIX）。
- 产业界 ISA（12 个）与其他开放/教学 ISA（7 个）的对照。
- **设计目标与非目标**：可实现、可验证、可教学；不追求商用性能、不背兼容、不追求指令数最少。
- **主要取舍**：定长/变长、值条件/标志位、分组/统一、RAS/软件栈、拼接/常量池、大端/小端、LR-SC/AMO。

本体系架构借DADAO之名，寓意简单且实用。

- 简单的真实含义：每个系统都很复杂，其设计者都是盖世奇才；然后因为受限于各种接口与依赖，需要进行各种妥协，因此只能采用各种方式进行修修补补；
Dadao希望利用清晰简洁的内部设计和接口逻辑让多个系统尽量按照其本意顺畅运转起来。
就好像两个轮子要联动，可以把两个轮子做成相互咬合的齿轮，也可以用一根连动杆将速率一致的部位连接起来；
而不是在两个轮子旁边分别安放一个监控器，然后增加通知模块和同步模块，然后每个轮子有变化的时候相互通知，然后进行同步。
- 实用的真实含义：计算机系统处处都是权衡，很多权衡的真实原因是性能、成本和历史的包袱。
Dadao没有历史的包袱，也不刻意追求高性能，更不存在成本问题，所以一个底线就是可实用化；实用的评价指标就是模拟器和FPGA可实现且其性能可接受。

DADAO的版本号拟遵循语义化版本控制规范SemVer 2.0.0： <https://semver.org/lang/zh-CN/> 。
当前处于开发初始阶段，因此主版本号为零，即（0.y.z），一切都可能未事先声明而随时被改变。

### DD-B002-大道至简--指令编码

- 32 位定长、4 字节对齐；`IP[1:0] ≠ 0` 触发 IALIGN。
- `8/6/6/6/6`：8 位 `opc` + 4×6 位 `ha/hb/hc/hd`；`opx` 复用 `ha`。
- 12 种操作数格式：`rrrr`/`rrri`/`rrii`/`riii`/`iiii`/`rwii`/`orrr`/`orri`/`oiii`/`crrr`/`crii`/`ciii`。
- 立即数跨字段拼接：6/12/18/24 位；`rwii` 用 2 位 wyde-position + 16 位。
- 6 位寄存器号是组内编号，组由 `opc`/`opx`/格式决定。
- 位宽子表：`OPC-octa`/`OPC-tetra`/`OPC-wyde`/`OPC-byte`，另有 `OPC-RF`/`OPC-MISC`。
- 保留编码 → UNDI；已定义但操作数/字段非法 → ILLI（含 SBZ 非零）。
- 位宽子表把宽度编码进 `opc`，不占每条指令的位。
- 伪指令（`set.*`）不是硬件指令，由汇编器展开。
- 指令字按大端存放：bits[31:24] 在最低地址。

### DD-B003-大道至简--寄存器设计

- 四组寄存器：`rd`（数据）、`rb`（基址）、`rf`（浮点）、`ra`（返回地址），各 64 个 × 64 位。
- `rd`/`rb` 分离：地址常驻占用与数据运算分开，等效 128 个通用寄存器。
- 6 位字段是组内编号，组由指令的 `opc`/`opx`/格式决定。
- 0 号槽承载特殊状态：`rd0` 常数 0、`rb0` = IP、`rf0` = FCSR/qNaN、`ra0` = RAS 状态。
- `rd0` 只读为 0；作目的按规则丢弃或 ILLI。
- `rb0` 是当前指令地址（不是下一条），使相对/绝对寻址共用一套指令。
- 多寄存器块复制（`rd2rd` 等）：起始寄存器 + 6 位计数，1–63 个连续寄存器。

### DD-B004-大道至简--条件判断

- 主流 CZSO 的动机：几乎免费、编码省位、一次比较多个谓词、多精度。
- CZSO 的代价：隐式状态、假依赖、重命名/异常恢复复杂、比较结果不可复用。
- SimRISC 取消 CZSO：条件直接来自寄存器值。
- 六种条件：N/NN/Z/NZ/P/NP；两寄存器另有 EQ/NE。
- `cmp` 产生 -1/0/1；`.s`/`.u` 区分符号性。
- `br.eq`/`br.ne` 把两寄存器比较融进分支。
- 条件赋值 `cs.*` 以寄存器为条件源。
- `cs.*` 是"二选一"（两条路径都写），区别于 `cmovcc` 的条件写。

### DD-B005-大道至简--立即数处理

- 主流立即数赋值：分片拼接 vs 常量池。
- 64 位化后一个立即数域装不下一个寄存器。
- 常量池：多一次访存 + 数据 cache 污染；拼接：多几条指令、无访存。
- 常用立即数：8 位约一半、16 位约 80–90%、32 位 95% 以上。
- `rwii`：16 位立即数 + 2 位 wyde-position，最多 4 条拼 64 位。
- `set.zw`/`set.ow`/`or.w`/`andn.w` 的语义与组合。
- 不同寄存器组（`rd`/`rb`/`rf`）的 `rwii` 变体与写入语义。

### DD-B006-大道至简--访存与地址运算

- 48 位虚拟地址（256 TiB），物理地址 64 位。
- `rb` 64 位；访存取低 48 位，高 16 位作地址溢出标记。
- 地址运算专用指令：`add.o`/`sub.o`/`cmp.uo-rb`/`add.si`/`aip.si`。
- `aip`：IP 相对，±512 MiB，4 KiB 粒度。
- load 的符号/零扩展：`ld.sb/ub`、`ld.sw/uw`、`ld.st/ut`、`ld.o`。
- `ldm`/`stm`：1–63 个连续寄存器。
- RB/RA 只有 `.o`，RF 有 `.t`/`.o`；多寄存器检查 0 号/重叠/原始地址。
- 对齐按宽度；未对齐 MALIGN。
- `ld` 目的不能是 `rd0`；`st` 源可以是 `rd0`。
- 大端序。

### DD-B007-大道至简--整数运算

- `.s`/`.u` 决定高位扩展，不是标志位。
- 64 位加减/乘法用双目的 `{rdHA, rdHB}` 给 128 位结果。
- 窄宽度（8/16/32）运算：只算低位，结果扩展到 64 位。
- `cmp` 结果 -1/0/1；-1 统一为 64 位全 1（不按 `.u` 零扩展），供六种条件使用。
- 乘法：64 位给 128 位；窄宽度给 64 位单目的。
- 除零/溢出返回定值；有符号除法向零截断。
- `add.si`：18 位立即数自增/自减，全 64 位。

### DD-B008-大道至简--位操作

- 逻辑：`and.o`/`or.o`/`xor.o`/`xnor.o`；无 `not`，用 `xnor` + `rd0`。
- 移位：`shl`/`shr.u`/`shr.s`/`rol`；`shl`/`rol` 不分符号。
- 移位量：寄存器取低位，立即数越界 ILLI。
- `rev`：逐块反转，`k` 为 one-hot，覆盖 bswap/bitreverse。
- `ctlz`/`cttz`/`ctpop`：`hd` 指定有效位上界，全 0 返回 `hd+1`。
- `clmul.o`：GF(2) 无进位乘，128 位结果。
- `ext.uo`/`ext.so`：64 位位段符号/零扩展。

### DD-B009-大道至简--浮点运算

- IEEE 754 默认模型：异常只置状态位，不陷入。
- 状态位 NV/DZ/OF/UF/NX；舍入模式 RNE/RTZ/RDN/RUP。
- min/max 采用 `minimumNumber`/`maximumNumber`（NaN 不传播）。
- FMA：`a×b+c` 只舍入一次。
- 格式转换（`ft2fo`/`fo2ft`、int↔float）：`orri` 块操作，1–63 条，源/目的不重叠。
- 算术/取整/平方根/scaleB：`ftadd`…、`ftrnd`/`fornd`、`ftroot`/`foroot`、`ftsclb`/`fosclb`。
- 比较/分类/符号位：`ftqcmp`/`ftscmp`、`ftcls`/`focls`、`ftsgnj`/`ftsgnn`。
- 除零：浮点返回 ±Inf/qNaN 并置 DZ/NV；整数返回定值，不陷入。
- `rf0` 既是 qNaN 又是 FCSR；可作源/目的，不可作浮点运算目的。
- 保存 `rf0`–`rf63` 即保存 FCSR。

### DD-B010-大道至简--控制流

- 分支用相对地址；偏移左移 2 位。
- `br.eq`/`br.ne`：两寄存器比较，±8 KiB。
- `br.n/nn/z/nz/p/np`：六种条件，±512 KiB；`br.z/nz` 有 `rb` 变体。
- `jump`/`call`：相对（±32 MiB）与绝对（基址+变址+偏移）。
- `call` 压入 RAS，`ret` 弹出；RegRAS 63 槽 + MemRAS。
- `call` 返回地址 = `IP + 4`；`ret` 可能从 MemRAS 取；`rb` 变体按整 64 位判零。
- `ra0`：`RACNT` + `MRPTR`。
- RASOF/RASUF；递归折叠。
- `ret rd, imm` 带返回值；RAS 与数据栈分离。

### DD-B011-大道至简--原子操作

- LR/SC 合成任意 RMW，不需要 AMO。
- `lr` 设置保留标记，`sc` 条件写并返回 0/1。
- `lr` 的 `hb` 固定为 `rd0`，`hb ≠ 0` → ILLI。
- acquire/release 后缀：`lr.*.an/.ar`、`sc.*.nr/.ar`。
- `fence`：`fm`/`pred`/`succ` 位掩码。
- 保留粒度由平台定义；LR/SC 按宽度对齐。
- 异常/中断/另一条 `lr` 会清除保留；SC 可能偶发失败。
