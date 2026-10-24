# MEMORY — DADAO-v5 入口页（指针 + 偏离/不做台账）

> **维护规则**：本页**只**承载两样——① **入口指针**（导航）；② **偏离 / 不做台账**（**唯一一份**，含上游偏离 + v5 自身决定不做）。**除该台账外，勿在本页复制其它事实**（进度 / 版本 / 决策各归真源；复制必漂移）。

## 入口指针

| 主题 | 真源 |
| --- | --- |
| 项目总览 / 里程碑 / 版本号 | 根 `README.md` |
| 当前进度 / 任务流水 / 规划中 / 裁定 | `.tao/knowledge/milestones.md` |
| M7 收尾 / 待用户裁定 · 操作清单 | `.tao/knowledge/milestones.md`「当前进度」+ `.tao/archive/M7/m7-retrospective.md §7` |
| M8 收尾 / 未决项 | `.tao/archive/M8/m8-retrospective.md`（M9 进度见 `milestones.md` 任务流水） |
| 决策（ADR：架构 / 契约 / 流程） | `.tao/adr/` |
| 交互目录（`$TAO_ROOT` / 结构 / 模块表） | `.tao/README.md` |
| 角色 / 流程 / 命令 | `AGENTS.md`「角色与流程」+ `.opencode/agents/`、`.opencode/commands/` |
| 任务文件 | `.tao/tasks/<module>/` |
| 技术规范（上游 + v5 自定；索引 / 投影表） | `spec/` + `spec/README.md` |
| 工程流程规范 + 仓库级索引 | `docs/Process-0x` + `docs/README.md` |
| 合约（归一化叙述 / 机器可读数据） | `.tao/contracts/contract-*.md` / `contracts/` |
| 参考仓库（只读工作树 / 锁文件） | `.cache/refs/` + `manifests/` |
| issue / 教训 | `.tao/knowledge/issues.yaml` / `.tao/knowledge/lessons.md` |
| 历史归档 | `.tao/archive/M*/`（M1–M8；含 `README.md` + `m<i>-retrospective.md` + `issues-closed.md`） |
| 临时 / 一次性产物 | `/tmp/opencode/<任务ID>/` |

## 偏离 / 不做台账（唯一一份）

> **第 1–7 项** = 上游 spec 与 v5 决策之间的**规范性偏离**（M2 门槛⑤成型；`SPEC-106t` 增至 7 项）；**第 8–10 项** = **v5 自身决定不做**的事项（非上游偏离，无 ADR，记此仅为单一清单）。每项均由**已 `Accepted` 的 ADR**（或 M1→M2 过渡任务 `SPEC-086t`）固化；本节只做**归一化登记 + 指针**，不新增决策，权威决策见 `.tao/adr/`。`scope`、`RACNT`、`MRPTR`、exit 码等写法与 `contracts/opcodes.yaml`、ADR 一致。
>
> **位置（2026-10-11，`INFRA-063t`）**：本台账原在根 `README.md`，按用户裁定「放在 `.tao/knowledge/MEMORY.md` 中更合适」迁入本页；根 `README.md` 只留项目总览 / 里程碑 / 版本号。

| # | 偏离点 | 上游依据 | v5 决策 | ADR / 契约指针 |
|---|--------|----------|---------|----------------|
| 1 | **exit port（程序停机）** | `SimRISC-11 §退出指令`：`escape cfxHA, [excp_cause_ip, imms20]`（**退出特权态**，非停机；编码层 `imms18`） | 自定 **exit port** MMIO（`0xffff_8000_0000`，8 B，只写）；退出码 = `0x80 \| cause_bit`；写入后 `cpu_loop_exit()` 锁定 | **ADR-0004 §D3**（Exit Port 协议）+ **ADR-0011 §D1–D4**（可靠 halt） |
| 2 | **`fence` SBZ 非零** | `SimRISC-11 §fence指令`：`immu18 bits[17:4]` 为 SBZ，**非零值行为保留** | v5 定**非零 SBZ → ILLI**（`0x88`）；且 `fence` 整体 `scope: excluded`（未实现，decode ILLI） | **ADR-0004 §D5.3**（SBZ 非零 → ILLI）+ **ADR-0014 §D1–D3**（fence 移出 M1）；`contracts/opcodes.yaml::fence_oiii_imm` |
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
> **章节订正（实测）**：任务书/`docs/m2-spec-planning.md` 沿用 **SimRISC 0.5.3 编号**；v5 现行规范为 **0.5.4**，章节已重排——上游依据「exit port vs `escape`」现位于 `SimRISC-11 §退出指令`（0.5.3 为 `SimRISC-04`）、`fence` SBZ 位于 `SimRISC-11 §fence指令`（0.5.3 为 `SimRISC-04`）、浮点规范为 `SimRISC-07`（0.5.3 为 `SimRISC-03`）。均以 `contracts/opcodes.yaml` 的 `spec_cite` 实测为准。
