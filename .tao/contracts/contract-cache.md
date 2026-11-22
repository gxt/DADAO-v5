# Cache 维护接口合约（`cfx_cache` / cfx5）

> **版本：0.7.1** [DADAO-12 §4.6 cfx_cache - cache organization]
>
> **来源**：`spec/DADAO-12-SEE-主管系统运行环境.md`（0.8.0-rc）的 `§1`/`§3.8`/`§4.6`/`§5.2`；测试机运行环境正文 `spec/Kaiwu-测试机运行环境.md`（0.4.7-rc，`§3`/`§3.2`）；寄存器位定义、控制字编码、命令语义与本合约的测试机约定为用户 2026-11-20 与 2026-11-22 的问答结论（句末标 `[spec-decision]`）。版本取 `README.md` 版本表的 SEE / SBI 已发布版，与 `contract-see.md`/`contract-tlb.md` 同法。
>
> **范围**：`cfx_cache` 的寄存器面（`cache_exist`/`cache_enable`/`cache_ctrl`/`cache_addr_start`/`cache_addr_size`）、存在与使能语义、控制字的选择/操作/范围三维与判序、三档范围匹配、I/D 两侧的 `clean`/`invalidate`/`flush` 作用、同步完成与失败语义、per-hart 与测试机实现范围（含 `cache-model=off|on` 的机器配置维度）；消费方 = 各实现的 `cfx5` 落地与 `tests/arch` 的 cache 探针。cache 组织（容量、行大小、组数、替换策略）由实现决定，不在本合约内。
>
> **来源标注**：每条规范性断言句末以方括号标注来源——上游册写 `DADAO-12` + `§` + 章节名，测试机正文写 `Machine-01` + `§N`；上游未规定、由用户逐条确认的口径（2026-11-20 起，含 2026-11-22 的 `cache-model` 补记），句末另标 `[spec-decision]`。不写行号。
>
> **说明**：本合约由 spec/ 归一化投影而来，只做归一化 + 指针、不复制上游正文；面向实现与探针，与 spec/ 冲突时阻断实现，走变更流程（见 `docs/Process-02-合约编写规范.md`）。

---

## §1 归属与寄存器面

- CACHE-01 **归属**：cache 维护属 `cfx5`（`cfx_cache`），与 `cfx4`（`cfx_ptw`）的 TLB 是**两套独立状态**；维护接口只有 `cfx_cache_ctrl` 控制字，不另设独立的 cache 维护指令。[DADAO-12 §1. 运行模式与核芯功能扩展][DADAO-12 §4.6 cfx_cache - cache organization]
- CACHE-02 **以 PA 为键**：cache 以**物理地址（PA）**索引与匹配，不是按 VA 索引，因此控制字与寄存器里**没有 ASID 维度**。[DADAO-12 §4.6 cfx_cache - cache organization]
- CACHE-03 **寄存器位**：`cfx_cache_exist` = `cg8 rc0`（RO）、`cfx_cache_enable` = `cg8 rc8`（RW）、`cfx_cache_ctrl` = `cg8 rc9`（WO、写即执行）、`cfx_cache_addr_start` = `cg8 rc10`（RW，完整 56 位物理地址 `PA[55:0]`）、`cfx_cache_addr_size` = `cg8 rc11`（RW，字节数）。[DADAO-12 §4.6 cfx_cache - cache organization]
- CACHE-04 **其余 rc 保留**：`cg8` 的其余 rc 保留，对该 cfx 的已实现寄存器组合之外的访问（含保留 rc）⇒ `CFXREG`。[DADAO-12 §4.6 cfx_cache - cache organization][DADAO-12 §5.2 异常进入流程]
- CACHE-05 **组织由实现决定**：cache 的容量、行大小、组数、替换策略与是否把 I/D 分为两个独立存储体，全部由实现决定；本合约只固定软件可观测的寄存器语义与命令效果。[DADAO-12 §4.6 cfx_cache - cache organization]

## §2 存在与使能

- CACHE-06 **`cache_exist` 的位定义**：bit0 = 有 I-cache、bit1 = 有 D-cache；其余位保留、读 0；由硬件设置，软件只读。[DADAO-12 §4.6 cfx_cache - cache organization]
- CACHE-07 **`cache_enable` 的位定义**：bit0 = I、bit1 = D，0 = 关闭、1 = 开启；复位后每一位等于对应的 `cache_exist` 位（已存在的 I/D cache 默认开启）；`cache_exist` 位为 0 的位置写 1 **无效果**、读回 0；其余位保留、读 0。[DADAO-12 §4.6 cfx_cache - cache organization]
- CACHE-08 **使能位为 0 的效果**：`cache_enable` 对应位 = 0 时，该侧的维护命令 **no-op**（`clean`/`invalidate`/`flush` 对该侧均无效果、不改变其内容）；编码与 `addr_size` 的校验**不受使能影响**（仍按 CACHE-11 判序执行，非法即 `CFXREG`）。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]

## §3 控制字编码与判序

- CACHE-09 **编码**：`cfx_cache_ctrl[1:0]` 操作 = `00 = none`/`01 = clean`/`10 = invalidate`/`11 = flush`；`[3:2]` 范围 = `00 = all`/`01 = PA 单行`/`10 = PA 区间`/`11 = reserved`；`[15:14]` 选择（**bit15 = I、bit14 = D**，`11` = 两侧全选、`10` = 只 I、`01` = 只 D、`00` = no-op）；其余位保留、写忽略。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]
- CACHE-10 **三维正交**：选择（`[15:14]`）、操作（`[1:0]`）、范围（`[3:2]`）三个维度互相独立，不互相隐含。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]
- CACHE-11 **判序**：先判选择位、再判操作，最后才判范围编码与操作数。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]
- CACHE-12 **`[15:14] = 00` 无条件 no-op**：不报异常，且**不检查**范围编码与 `addr_size`（`[3:2] = 11` 或 `PA 区间` 且 `size = 0` 在该情形下同样不报）；`addr_start`/`addr_size` 均被忽略。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]
- CACHE-13 **`op = none` 无条件 no-op**：不报异常，且**不检查**范围编码与 `addr_size`；选择位、`addr_start`、`addr_size` 均被忽略。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]
- CACHE-14 **非法编码/操作数**：仅在「选中至少一侧」且操作非 `none` 时校验——`[3:2] = 11`，或 `PA 区间` 且 `addr_size = 0` ⇒ `CFXREG`（`cause_info` = 指令编码）。[DADAO-12 §4.6 cfx_cache - cache organization][DADAO-12 §5.2 异常进入流程]

## §4 范围匹配

- CACHE-15 **`all`**：忽略 `addr_start` 与 `addr_size`，作用于被选中一侧的全部 cache。[DADAO-12 §4.6 cfx_cache - cache organization]
- CACHE-16 **`PA 单行`**：只作用于**包含** `addr_start` 的那个 cache 行（按 56 位 PA 比较），忽略 `addr_size`（行大小由实现决定，软件不得假定其值）。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]
- CACHE-17 **`PA 区间`**：作用于与 `[addr_start, addr_start + addr_size)` **相交**的 cache 行（比较对象是 56 位 PA）；`addr_size = 0` 属非法操作数（CACHE-14），不是「匹配空集」。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]
- CACHE-18 **`addr_start` 的宽度**：寄存器承载**完整 56 位物理地址** `PA[55:0]`，位 `[63:56]` 保留、读 0、写忽略；范围匹配按 56 位 PA 逐位比较，不做任何截断。[DADAO-12 §4.6 cfx_cache - cache organization]

## §5 I/D 两侧的操作语义

- CACHE-19 **I 侧**：`clean` = **no-op**（I-cache 无 dirty 状态）；`invalidate` = 丢弃；`flush` 等价 `invalidate`。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]
- CACHE-20 **D 侧**：`clean` = 写回并清 dirty；`invalidate` = 丢弃（其中的脏数据随之丢失，**不写警告、不报异常**）；`flush` = 写回后丢弃。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]
- CACHE-21 **两侧全选的判序**：`[15:14] = 11` 时先处理 I 侧、再处理 D 侧；两侧各自按所选范围匹配，互不影响。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]
- CACHE-22 **不适用地址**：`addr_start`（`PA 区间` 时连同整个区间）落在不可缓存或 MMIO/device 的 PA 上时，命令对该部分**无效果、不报异常**；判定依据是 `cg7` 空间描述（`attr.cacheable = 0`，或空间类型为 MMIO）；内存窗口（`addr[47:42] = 0`）没有 `cg7` 空间描述，其可缓存性由实现决定；区间跨越可缓存与不可缓存部分时，只作用于可缓存部分。[DADAO-12 §4.6 cfx_cache - cache organization][DADAO-12 §3.8 cg7 - 内部空间描述寄存器][spec-decision]
- CACHE-23 **正常完成不报异常**：`none`、两侧都不选、`cache_enable` 对应位为 0（该侧不被维护），以及各操作的正常路径都不产生异常；非法编码仍按 CACHE-14 报 `CFXREG`；`invalidate` 丢弃脏数据**不报任何异常**。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]

## §6 完成与失败语义

- CACHE-24 **同步完成**：`cfx_cache_ctrl` 的写指令**同步完成**——指令返回即生效，其后的访存必见维护结果；无 busy/done 位、无异步完成信号。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]
- CACHE-25 **唯一失败是 `CFXREG`**：维护命令没有可观察的失败状态位；唯一的失败是编码/操作数非法触发的 `CFXREG`（CACHE-14），按判序（CACHE-11）它发生在任何维护动作之前 ⇒ 不存在「部分完成」的可观测状态，不需要命令级重试协议。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]
- CACHE-26 **路由**：`CFXREG` 进**当前运行模式 monitor**（`user→cfx0`、`jail→cfx1`、`supv→cfx2`、`hypv→cfx3`），不进入 `cfx_cache` 自身向量；`cfx_cache` 自身只报 `CFXTRAP`/`CFXESC`。[DADAO-12 §5.2 异常进入流程][DADAO-12 §4.6 cfx_cache - cache organization]

## §7 测试机约定（per-hart 与实现范围）

- CACHE-27 **实现范围（Vast）与 `cache-model` 维度**：`Kaiwu-Vast` 实现 `cfx5` 的寄存器与维护命令，I 与 D 两侧均存在；cache 几何由实现决定、本册不规定。机器配置的 `cache-model` 只决定这些寄存器与命令**有没有效果**，不决定 `cfx5` 是否存在（Vast 的寄存器面恒在）：
  - **`cache-model=off`**：`cfx5` 存在；CACHE-03 的五个寄存器均可访问、不报 `CFXREG`（其余 rc 仍按 CACHE-04 处理）；`cache_exist` 读 0（存在位为 0 ⇒ `cache_enable` 写 1 也读回 0，CACHE-07）；`cache_ctrl`（WO，只写）/`cache_addr_start`/`cache_addr_size` 可访问，但维护命令**无效果**——`cache_ctrl` 的**合法编码不报异常、不产生维护动作**；`cache_ctrl` 的**编码与 `addr_size` 校验不受 `cache-model` 影响**，非法编码（`[3:2] = 11`、PA 区间且 `size = 0` 等）仍 ⇒ `CFXREG`。[Machine-01 §3.2 cache（cfx5）的测试机约定][spec-decision]
  - **`cache-model=on`**：`cache_exist` 读回 `0b11`、`cache_enable` 复位值同；寄存器与命令按 CACHE-03…CACHE-27 生效。[Machine-01 §3.2 cache（cfx5）的测试机约定][spec-decision]
  - 各实现是否暴露该配置开关、缺省取何值，由实现与测试机约定另行规定；本合约只固定两种取值的效果。[Machine-01 §3.2 cache（cfx5）的测试机约定][spec-decision]
- CACHE-28 **实现范围（Tiny）**：`Kaiwu-Tiny` 不实现 `cfx5`——寄存器访问与 `cfx2rd`/`cfx2rc` ⇒ `CFXREG`，`trap`/`escape` ⇒ `ILLI`。[Machine-01 §3.2 cache（cfx5）的测试机约定][spec-decision]
- CACHE-29 **per-hart**：寄存器与维护命令都是 per-hart 状态，命令只作用于执行该写指令的 hart；跨 hart 的维护传播与一致性**不在本版范围**。[Machine-01 §3.2 cache（cfx5）的测试机约定][DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]
- CACHE-30 **可观测判据**：实现可自由选择组织，但必须满足本合约的可观测量——`cache_exist`/`cache_enable` 的位值、命令生效后的访存结果（I 侧重取指、D 侧写回/丢弃）、非法编码的 `CFXREG`；探针与门控只按这些观测量断言。[Machine-01 §3.2 cache（cfx5）的测试机约定][DADAO-12 §4.6 cfx_cache - cache organization]

## §8 变更记录

- **0.7.1（2026-11-20）**：首版。收编 `DADAO-12 §4.6` 的 `cfx_cache` 寄存器面与语义（CACHE-01…CACHE-26）与 `Kaiwu §3.2` 的测试机约定（CACHE-27…CACHE-30）。旧的「bit0 = 无效 I-cache / bit1 = 无效 D-cache / bit2 = 刷新 D-cache」数值编码作废，改为选择/操作/范围三维控制字；`cache_exist`/`cache_enable` 位定义补为 bit0 = I、bit1 = D；`cache_addr_start` 承载**完整 56 位物理地址** `PA[55:0]`（`[63:56]` 读 0），范围匹配按 56 位 PA 比较。版本取 `README.md` 版本表的 SEE / SBI 已发布版（与 `contract-see.md`/`contract-tlb.md` 同法），上游正文为 0.7.3-rc 在研。
- **2026-11-22（`m16-spec-002`，版本不变）**：CACHE-27 增补机器配置维度 `cache-model=off|on`——`off` = `cfx5` 存在但寄存器/命令无效果（`cache_exist` 读 0、合法命令不报异常且不生效，编码与 `addr_size` 校验不受该维度影响、非法仍 ⇒ `CFXREG`），`on` = `cache_exist=0b11` 且命令生效。授权：用户 2026-11-22 裁定「机器配置只决定 cfx5 有没有效果，不决定它是否存在」（渠道 = 经主会话问答）。版本号仍为 `0.7.1`（`docs/Process-02-合约编写规范.md` §版本管理：合约版本号与对应 `spec/` 文档一致；本次不改上游 `spec/` 正文）。
