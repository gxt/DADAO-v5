# INTEG-009t: 最小 FP E2E smoke（门槛④）

**模块**：integ
**项目里程碑**：M2
**依赖**：无（FP 执行层 60/60 已由 `QEMU-034t`~`037t` 落地；`dst_rd0@FP` 由 `LLVM-031t`+`QEMU-038t` 落地）
**状态**：待开始

## 目标

新增**最小 FP 端到端冒烟**：用 `llvm-mc` 汇编一段含**少量 FP 指令**的 `.s` → `llvm-objcopy` 取 `.text` → `qemu-system-dadao -M dadao-m1` 执行 → 以 **exit port 退出码**判定，期望值**独立手算**（禁 LLVM/QEMU 校准）。补齐 M2 门槛④「FP = 执行层 60/60 + `dst_rd0@FP` + **最小 FP smoke**」的最后一项。

## 背景与现状（实测）

- 现有 E2E 冒烟：`tests/e2e/{smoke_add.s,smoke_arith.s,smoke_jump.s}` + `tests/lit/E2E/{smoke_add.test,smoke_arith.test,smoke_jump.test}`；`make check-lit` 运行 `llvm-lit tests/lit/MC/Dadao tests/lit/E2E`（当前 **3/3** E2E）。
- E2E 机制（`tests/lit/E2E/lit.cfg.py`）：`%llvm_mc`→`.o`、`%llvm_objcopy -O binary --only-section=.text`→`.bin`、`%qemu -M dadao-m1 -bios %trampoline -kernel %t.bin -display none -nographic`；`trampoline.bin` 在 `tests/scripts/`。
- 退出协议（`ADR-0004 §D3`）：写 exit port `0xffff_8000_0000`（8 B，只写）；写 `0x00` = PASS、非 0 = FAIL；测试程序自行构造该地址。
- FP 语义真源：`.tao/knowledge/contract-fp.md`（§2–§13）；汇编字面：`spec/Toolchain-01-汇编语言.md` + `.tao/knowledge/contract-asm-list.md`。FP 指令可汇编（`LLVM-029t`，`tests/lit/MC/Dadao/fp-encoding.s` 60 条）+ 可执行（`QEMU-034t`~`037t`）。
- **本任务不引入 FP 独立 oracle / FP 向量**（归 M3，`GOLDEN-*`/`TESTCASES-024t`）；只做**一条**最小 smoke。

## 交付物

1. **`tests/e2e/smoke_fp.s`**（新建）：一段自包含 FP 冒烟程序，至少覆盖：① 把若干 FP 位型**装入 RF**（经 RD 构造后 `rd2rf`，或 `set.ft`/`set.fo` 伪指令，按 `Toolchain-01` 字面）；② **≥2 条 FP 运算**（如 `ftadd`，可再叠 `ft2it` 或 `ftqcmp`）；③ 把结果化为**整数可判定**（f→i 转换或浮点比较 → RD 位型）；④ 与手算期望比较，跳 PASS/FAIL；⑤ 写 exit port（`0x00` PASS / `0x01` FAIL）+ `swym 0` 终止符。
2. **`tests/lit/E2E/smoke_fp.test`**（新建）：与 `smoke_add.test` 同构的 RUN 行（`%llvm_mc` → `%llvm_objcopy` → `timeout 30 %qemu …`），`qemu` 退出码即 lit 判定。
3. **期望值独立派生说明**：在 `.s` 注释或单独说明中写明——输入位型、FP 运算、手算结果（含舍入/截断依据，如 `1.5 + 2.25 = 3.75` f32 精确、`ft2it` 向零截断 → `3`）、以及「**不从 LLVM/QEMU 反推**」。

**候选场景（示意，须按 `contract-fp.md`/`Toolchain-01` 核对字段与字面后采用，勿照抄）**：f32 `1.5 + 2.25 = 3.75` → `ft2it` 得 `3` → 与常量 `3` 整数比较 → 相等则 PASS。

## 约束

- **Independent oracle（硬约束）**：期望值**只能**由 `contract-fp.md`（IEEE754 手算）或已核实的数学事实导出，**不得**用 `llvm-mc`/`llvm-objdump`/QEMU 输出作为期望来源或「对拍通过」依据。
- 只改 `tests/e2e/`、`tests/lit/E2E/`；**不改** QEMU/LLVM 实现、`contracts/`、`spec/`、`tests/vectors/`、`tools/`。
- 不改 `ADR-0004` 机器约定；沿用 `-M dadao-m1` 与既有 trampoline。
- 程序须能在 `-display none -nographic` 下确定性退出（写 exit port 后立即停止，无需 `swym` 兜底也可，但保留终止符更稳）。
- 汇编字面须与生成投影一致（寄存器组记法 `{…}`、`wpN` 用数字位次如 `set.zw rdH, 1, immu16`，参见 `smoke_add.s` 的 NOTE：`wpN` 具名常量当前被静默忽略）。
- ADR 提醒：属 E2E 测试补充，**不立 ADR**；若发现 spec/contract 未明的 FP 语义，登记 `issues.yaml`（不臆造、不在本任务补语义）。

## 验收标准

1. `tests/e2e/smoke_fp.s` + `tests/lit/E2E/smoke_fp.test` 存在；`make check-lit` **全绿**（E2E **4/4**，MC 不回归）。
2. 运行 `smoke_fp`：`qemu` 退出码 = **0**（PASS）；完成区给出真实命令、输出与退出码。
3. 期望值**独立派生**：说明与其手算过程可逐位复算；派生器（若有）**不调用** LLVM/QEMU。
4. **反例门控**（承重）：改期望常量（如把比较用 `3` 改为 `4`）→ 重新汇编运行 → `qemu` 退出码非 0 / lit `smoke_fp` FAIL；还原 → 回绿。完成区给出「注入→FAIL→还原→回绿」真实输出与退出码。
5. **被检命令退出码**留证不得用 `tee` 吞（用 `cmd > log 2>&1; rc=$?; …` 或 `${PIPESTATUS[0]}`）。
6. `make check` **EXIT=0**。
7. 一键证据脚本：非交互；任一检查失败即非零退出；逐项打印「检查名 + 期望/实际 + 退出码」；内置注入自检（或 `--inject`）。落点 `.work/evidence/INTEG-009t/`。

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
