# SPEC-092t: 系统层投影缺口显式 deferred 登记（清缺口②③④）

**模块**：spec
**项目里程碑**：M2
**依赖**：`SPEC-091t`（同改 `spec/README.md`/`Process-02`，串行）
**状态**：待开始

## 目标

对 `spec/README.md` 投影表 / `Process-02` 合约清单中登记的 **3 个系统层缺口**——`contract-sbi.md`（DADAO-12/22）、`contract-exception.md`（DADAO-13/23）、`contract-mmu.md`（DADAO-12 地址转换）——按 M2 门槛②「**缺口清零或显式 deferred**」做成**显式 deferred 登记**：写明 deferred 结论、理由、归属里程碑与触发条件，使投影表不再存在**裸 `缺口`**。

## 背景与现状（实测）

- `spec/README.md` 投影表中，`DADAO-12`（SEE）行为 `缺口（contract-sbi.md；地址转换 → contract-mmu.md）`、`DADAO-13`（HEE）行为 `缺口（contract-exception.md）`、`DADAO-22`（SBI）/ `DADAO-23`（HBI）行为 `缺口`/据实；「登记缺口」表列 `contract-sbi.md`/`contract-exception.md`/`contract-mmu.md` 三行。
- `spec/Process-02` 合约清单：`contract-sbi.md`/`contract-exception.md`/`contract-mmu.md` 状态 = **缺口**（其中 exception/mmu 已括注「可标记 deferred」）。
- 相关上游：`spec/DADAO-12`（SEE，§2 地址空间/§5 异常进入退出）、`spec/DADAO-22`（SBI 功能）、`spec/DADAO-13`/`DADAO-23`（HEE/HBI）。
- **M3 范围**（`milestones.md`）：Basic CodeGen = 标量整数/指针函数（LLVM IR）→ DADAO 汇编 → MC → obj → 链接 → QEMU 执行；**freestanding、same-TU**，不含变参/聚合；**无系统调用、无异常向量、无地址转换（MMU-off）**。故三者在 M3 之前**无消费方**。

## 交付物

1. **`spec/README.md`**：
   - 投影表中 `DADAO-12`/`DADAO-13`/`DADAO-22`/`DADAO-23` 行的 ①叙述合约列，由 `缺口（…）` 改为 **`deferred`（`contract-xxx.md`，归属 M3+ / 触发条件）**；
   - 「登记缺口」表三行更新：`缺口类型` 列由「…缺失」改为 **deferred**，并补 `deferred 理由` 与 `归属/触发`（归属里程碑 + 何时必须补齐）。
2. **`spec/Process-02-合约编写规范.md`**：合约清单中三者状态由 **缺口** 改为 **deferred**（并一句话理由 / 归属）。
3. **deferred 结论与理由**（写入上述两处，文字一致）：
   - **无 M2/M3 消费方**：M2（规范冻结）不实现 SEE/SBI/HEE/MMU；M3 codegen 为 freestanding 单 TU、无 syscall/异常/MMU。
   - **未冻结的后果可控**：M3 生成的代码不依赖 SBI 功能号、异常进入协议、地址转换；
   - **触发条件**：当出现「跨模块/内核/系统态」目标（如 OS→LFS 路线、`SEE/SBI` 消费方落地）时，须先补齐对应 contract 再实现；
   - **上游依据可回溯**：`spec/DADAO-12/13/22/23` 已存在，补齐时按 `Process-02` 归一化，不需新造规范正文。

## 约束

- **不臆造合约内容**：本任务**只登记 deferred**，不写 `contract-sbi/exception/mmu.md` 正文；若判定应直接补齐，须另立任务（不在本任务范围）。
- 只改文档：`spec/README.md`、`spec/Process-02-合约编写规范.md`。不改 `spec/DADAO-*` 正文、不改 `contracts/`、`tests/`、`components/`、`tools/`。
- 「显式 deferred」须**机械可搜**：投影表三格文字含 `deferred`（与 `SPEC-091t` 完成后的 `contract-asm.md`=已清零区分开）。
- ADR 提醒：登记 deferred 属过程取向（可逆、无外部契约），**不立 ADR**；若用户裁定改为「直接补齐合约」，则按新结论走，不沿用本任务。
- 与 `SPEC-091t` 串行（同改两文件）。

## 验收标准

1. `spec/README.md` 投影表中 `DADAO-12`/`DADAO-13`/`DADAO-22`/`DADAO-23` 行的 ① 叙述合约列**不再出现裸 `缺口`**，均为 `deferred`（含归属/触发）。
2. `spec/README.md`「登记缺口」表：`contract-sbi.md`/`contract-exception.md`/`contract-mmu.md` 三行均标 **deferred** + 理由 + 归属。
3. `spec/Process-02` 合约清单三者状态 = **deferred**。
4. 全 `spec/README.md` 与 `Process-02` 中，指向三缺口的字面 `缺口`（表示「未处置」者）= 0（`deferred` 字样除外）。
5. `make check` **EXIT=0**（纯文档改动，如不在门控覆盖内则以 `git status` 目视 + `check-no-residue` 为准）。
6. **反例门控**：一键证据脚本内置「注入反例→预期 FAIL→还原→预期回绿」（如把三行之一改回裸 `缺口` → 自检 FAIL），并在完成区给出真实输出与退出码。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
