# m17-testcases-004: `st.o` 语义行订正 + `rf0` 作源用例 + `.S` 注释术语统一（去 “beat”）

**模块**：testcases
**项目里程碑**：M17
**依赖**：`m17-testcases-001`（签名区数据派生；本任务改 `.S` 后须重生成）
**可并行分片**：否（`tests/inst/**` 为共享文件，串行）
**预估**：3–4 h
**档位**：中改
**状态**：待开始

## 背景（用户 2026-11-23 观察，三条均已现场核实）

1. **`st.o` 语义行写错**：`tests/inst/01-load-store/st.o_rrii_{ra,rb,rd,rf}.S` 第 4 行均写
   `mem[EA] ← 源寄存器低 64 位；…；只改这几条字节通道，beat 其余字节保持`。
   `st.o` 是**整 64 位写满 8 字节**，没有「其余字节保持」这回事；且 “beat” 是存储流水/颗粒的**实现术语**，不应出现在 ISA 语义行。
2. **`st.o_rrii_rf.S` 缺 `rf0` 作源用例**：全文件 `rf0` 只出现在第 6 行注释里（「rf0 读出完整 64 位（合法）」），无实际用例；同族 `ldm.o_rrri_rf.S` 已有 `rf0` 作目的/源的实测例。
3. **“beat” 术语全族不统一**：`tests/inst/**/*.S` 共 **41 个文件**出现 “beat”，其中注释行型为
   `数据块：TEST_DATA（24 个 8 字节 beat，…）`（19 处）、`取自 TEST_DATA 现有 beat`（38 处）、以及窄写语义行里的 `beat 其余字节保持`（`st.b`/`st.w`/`st.t` 共 4 处）。用户裁定：注释统一改用「数据单元」，**并标明宽度**（8 字节）；宏参数名 `\beat` 属代码标识符，**不改**。

## 目标

1. **`st.o` 4 个文件第 4 行**改为：`语义：mem[EA] ← 源寄存器整 64 位；EA = rb[47:0] + imms12（大端）；整 8 字节全部写入`。
2. **`st.o_rrii_rf.S` 补 `rf0` 作源用例**（新增 1 个链例，插在故障段之前）：
   - 先用 `set.w rf0, wp0, 0x0000` 清异常状态、`set.w rf0, wp2, 0x0000` 置舍入模式 RNE（`spec/SimRISC-03 附录 B` 注：wp0 命中 `[4:0]`、wp2 命中 `[33:32]`、wp1/wp3 写无效）；
   - `st.o rf0, [<base>, <off>]`，用 `__CHECK_MEM` 逐字节比对；
   - **期望值必须由 `spec/SimRISC-00 §2.3.1` 位域独立派生**（禁从实测反推）：`[63:51]=0b0111111111111`、`[50:34]` SBZ、`[33:32]`=RM(00)、`[31:22]=0b0111111111`、`[21:5]` SBZ、`[4:0]`=flags(0) ⇒ **`0x7FF8_00FF_C000_0000`**；
   - 原故障例点号顺延（现为 21/22，新增链例占 21 ⇒ 故障例改 22/23），并同步第 8 行「用例：…」计数（`legality 3`、`链例 21 + 故障例 2`）。
3. **注释术语全族统一**（只动 `@@` 注释文本，不动指令）：
   - `24 个 8 字节 beat` → `24 个 8 字节数据单元`；
   - `取自 TEST_DATA 现有 beat` → `取自 TEST_DATA 现有 8 字节数据单元`；
   - 窄写语义行 `只改这几条字节通道，beat 其余字节保持` → `只改这几条字节通道，其余字节保持`（`st.b`/`st.w`/`st.t`）；
   - 其余零散注释里的 “beat” 按语义改成「数据单元（8 字节）」/「整 8 字节」；
   - **宏参数 `\beat` 与代码标识符不改**；改完 `grep -rn "beat" tests/inst --include=*.S` 只应剩宏定义/调用里的参数名。

## 验收（逐条贴真实 rc）

1. **注释改动不改指令流**：被注释改动触及的每个 `.S`，其 `.text` md5 与改前相同（`st.o_rrii_rf.S` 除外，它新增用例）。
2. **`st.o` 语义行**：4 个文件第 4 行逐字为你裁定的措辞；全仓 `grep "源寄存器低 64 位"` 只剩窄写文件（`st.b`/`st.w`/`st.t`）。
3. **`rf0` 用例逐字节**：写入结果 = `0x7FF8_00FF_C000_0000`；至少 2 条可达 FAIL（① 把期望常量改错 ⇒ 红；② 删 `set.w rf0, wp2, …` 让 RM 非 0 ⇒ 红）。
4. **三平台**：同一 ELF 的签名流 qemu / gem5 / chipyard 逐字节相等；chipyard 若被其它任务占用 ⇒ 记 BLOCKED + 替代证据（不得并发构建）。
5. **数据同步**：`make inst-signature-data` 重生成 `tests/data/inst-signature/expected.tsv` 与 `inputs.sha256`；`make check-case-ledger --write` 重生成 `tests/case-ledger.tsv`；两者 `git diff` 只含本任务预期变化。
6. **门控**：`make check-inst-asm`（镜像数应与改前相同 = 272，新增用例不新增镜像）、`make check-inst-sig`、`make check-case-ledger`、`make check-tests-index`、`make check-inst-macro-scope`、`make check-knowledge-refs` 真实 rc。
7. 完成区必须写**需重测周期的镜像清单**（本任务改指令流的镜像：`st.o_rrii_rf`）。

## 约束

独立 `git worktree`（分支 = `m17-testcases-004`）；**不提交 git**；只改 `tests/inst/**`、`tests/data/inst-signature/**`、`tests/case-ledger.tsv` 与本任务书；不改 `spec/`/契约/`contracts/opcodes.yaml`；术语「寄存器组」；完成区不写具体 `.work/**` 路径；`rf0` 期望值不得以实测反推。
