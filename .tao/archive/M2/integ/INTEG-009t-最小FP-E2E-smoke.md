# INTEG-009t: 最小 FP E2E smoke（门槛④）

**模块**：integ
**项目里程碑**：M2
**依赖**：无（FP 执行层 60/60 已由 `QEMU-034t`~`037t` 落地；`dst_rd0@FP` 由 `LLVM-031t`+`QEMU-038t` 落地）
**状态**：已验证

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
**测试结果**：全部通过，无失败项。`make check-lit` **EXIT=0**（Total 31 / Passed 31，MC 27 + E2E **4/4**，含 `PASS: DADAO-E2E :: smoke_fp.test`）；`make check` **EXIT=0**（`repository checks: PASS`）；一键证据脚本 `.work/evidence/INTEG-009t/run.sh` **27/27 EXIT=0**（含 2 组注入→FAIL→还原+重建→回绿）。失败原因：无。

**修改文件**：
- 新增 `tests/e2e/smoke_fp.s`（sha256 `45fb80d9c474e7d6e72c32b3f3c2377adcd4c1700155514b1c8203c563b63dff`）
- 新增 `tests/lit/E2E/smoke_fp.test`（sha256 `58b8af395457493c587513f8ca8a917c31fa5ba8937917efbc37d8c2039025ee`）
- 新增（工作区、gitignored，非入库）`.work/evidence/INTEG-009t/run.sh`、`.work/evidence/INTEG-009t/derive_fp.py`
- 日志 `.work/log/integ/INTEG-009t-{baseline-check-lit,check-lit,make-check,evidence}.log`
- 本任务书（状态 + 完成区 + 审阅记录）
- **未改任何其它文件**。`git status` 中的 `MEMORY.md`/`README.md`/`spec/README.md`/`spec/Process-02…`/`tools/infra/check_spec_drift.py`/`.tao/knowledge/contract-asm.md` 等为 **并发其它任务（SPEC-093t）** 的改动，非本任务所为；本任务仅新增上列两文件。

**验收结果（真实命令/输出，完整见 `.work/log/integ/`）**：

1) **smoke 组成**（`tests/e2e/smoke_fp.s`，objdump 反汇编逐条核对）：
```
0: 4e 0e ff ff  set.zw rb3, wp2, 0xffff      ; exit port 地址构造
4: 4a 0d 80 00  or.w   rb3, wp1, 0x8000      ; rb3 = 0x0000_ffff_8000_0000
8: 4c 05 3f c0  set.zw rd1, wp1, 0x3fc0      ; f32 1.5  (0x3FC00000)
c: 4c 09 40 10  set.zw rd2, wp1, 0x4010      ; f32 2.25 (0x40100000)
10: 40 f4 10 41 rd2rf {rf1}, {rd1}           ; RD->RF
14: 40 f4 20 81 rd2rf {rf2}, {rd2}
18: 44 40 30 42 ftadd rf3, rf1, rf2          ; 1.5+2.25 = 3.75 (0x40700000)
1c: 44 c0 30 c1 ft2it {rd3}, {rf3}           ; f32->int: trunc(3.75) = 3
20: 4c 10 00 03 set.zw rd4, wp0, 0x3          ; 手算期望 3
24: 40 ac 50 c4 cmp.so rd5, rd3, rd4         ; 相等→0
28: 6b 14 00 02 br.nz {rd5}?, [rb0, 8]        ; ≠0 → Lfail(0x30)
2c: 21 14 30 00 st.o rd5, [rb3, 0]           ; PASS 写 0x00
30: 4c 1c 00 01 set.zw rd7, wp0, 0x1
34: 21 1c 30 00 st.o rd7, [rb3, 0]           ; FAIL 写 0x01
38: 77 08 00 00 swym 0
```
`br.nz` 目标 = `0x28 + 8 = 0x30 = Lfail`，偏移逐字节核对正确。覆盖：① RD 构造位型 + `rd2rf` 入 RF；② ≥2 条 FP 指令（`ftadd` + `ft2it`）；③ f→i 化为整数可判定；④ 与手算期望整数比较 + `br.nz`；⑤ exit port + `swym 0`。

2) **运行判定**（`smoke_fp`，`-display none -nographic`）：
```
$ llvm-mc --triple=dadao-unknown-elf -filetype=obj tests/e2e/smoke_fp.s -o t.o   ; EXIT=0
$ llvm-objcopy -O binary --only-section=.text t.o t.bin                          ; EXIT=0
$ timeout 30 qemu-system-dadao -M dadao-m1 -bios tests/scripts/trampoline.bin \
      -kernel t.bin -display none -nographic                                     ; QEMU_EXIT=0  (PASS)
```
（`Blocked re-entrant IO` 警告为既有 E2E 共同现象，见「新发现/坑」。）

3) `make check-lit`：`Total Discovered Tests: 31` / `Passed: 31 (100.00%)`，EXIT=0。
4) `make check`：EXIT=0，`repository checks: PASS`（`check-no-residue: PASS`）。

**期望值独立派生**（**不调用** llvm-mc/llvm-objdump/QEMU；写在 `.s` 注释 + `.work/evidence/INTEG-009t/derive_fp.py`，派生器仅用 CPython `struct`/`math` 宿主锚点）：
- `1.5  = 1.1b×2^0   → 0 01111111 10000000000000000000000 = 0x3FC00000`
- `2.25 = 1.001b×2^1 → 0 10000000 00100000000000000000000 = 0x40100000`
- `ftadd`：`1.5 + 2.25 = 3.75`（binary32 精确，无舍入）→ `0 10000000 111…0 = 0x40700000`
- `ft2it`：向零截断 → `3 = 0x00000003`
- 构造：`set.zw rdN,1,hi` ⇒ `rd1 = 0x0000_0000_3FC0_0000`、`rd2 = 0x0000_0000_4010_0000`
- 派生器逐项 OK（`derive_fp: fail=0`）。

**反例门控（真实输出，`.work/log/integ/INTEG-009t-evidence.log`）**（均作用于 `/tmp/opencode/INTEG-009t/` 临时副本，仓库源始终未动）：
- 注入 A（比较常量 `3 → 4`）：`diff` 确认源码已变 → 重新汇编/objcopy rc=0 → **qemu 退出码 = 1（FAIL）**；还原 + 重建 → **0（回绿）**。
- 注入 B（FP 输入位型 `rd1,1,0x3fc0 → 0x4020`，即 `1.5 → 2.5`，和 `4.75` 截断 `4 ≠ 3`）：重新汇编 rc=0 → **qemu 退出码 = 1（FAIL）**；还原 + 重建 → **0（回绿）**。
- 两组证明：比较路径与 **FP 计算路径**均承重，且脚本能失败。
- **脚本自身可失败（真实输出，`.work/log/integ/INTEG-009t-evidence-scriptfail.log`）**：以固定坏源跑同一脚本 `SMOKE_SRC=<broken.s: 比较常量 3→4> run.sh` → 逐项打印 `[FAIL] smoke_fp qemu exit (PASS): expected=0 actual=1` 等 → `SUMMARY: pass=22 fail=5` / `RESULT: FAIL`，**脚本 EXIT=1** ⇒ 证明「任一检查失败即非零退出」。

**新发现/坑**：
- 既有 3 例 E2E（`smoke_add/arith/jump`）与新增 `smoke_fp` 运行后 QEMU 均打印 `warning: Blocked re-entrant IO on MemoryRegion: dadao-exit-port`——**非本任务引入**；exit port 为「**首次写生效**」（PASS 路径写 0 后落入 FAIL 路径再写 1，仍退出 0），与既有 3 例同构。
- **f→i 舍入口径「未在 contract-fp.md 显式化」（建议主会话/architect 处置，非本任务补）**：`spec/SimRISC-07 §格式转换指令` 泛言「舍入模式由 rf0[33:32] 控制」（默认 RNE），`contract-fp.md §3/§16` **未明** f→i 舍入；本任务按任务书给定前提 + 已验证的 `QEMU-036t` 口径（**f→i 固定向零截断**）取期望 `3`。严格按 rf0=RNE 读则 3.75→4。建议在 `contract-fp.md §3` 显式固化「f→i = 向零截断」（或登记 issues.yaml）。**本任务未擅自补语义**。
- 其余无。

**遗留问题**：
- 功能/验收层面：无。
- 范围外（建议 /complete 或 architect 处置）：上述 f→i 舍入口径的 contract 显式化 / issue 登记。本任务严格限改 `tests/e2e/`、`tests/lit/E2E/`，未改 `contracts/`、`spec/`、`.tao/knowledge/issues.yaml`。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`tests/e2e/smoke_fp.s`、`tests/lit/E2E/smoke_fp.test`、`.work/evidence/INTEG-009t/{run.sh,derive_fp.py}`（自主逐行审查）。

**逐项意见与判决**：
- **逻辑正确性**：位型构造（`set.zw rdN,1,hi` → bits[31:16]；低 wyde 保持 0）与 `rd2rf` 的 64 位原样搬移一致；`ftadd`/`ft2it` 操作数字段（`rfHB,rfHC,rfHD` / `rdHB,{rfHC}`）与 `contract-asm-list.md` 一致；`cmp.so` 等值→0、结果写满 64 位（`contract-isa.md §6.2.2`），`br.nz {rd5}?` ≠0 → FAIL；`br.nz` 目标 `0x30=Lfail` 经 objdump 逐字节核对。**判决：通过**。
- **边界/未测输入**：`ft2it` 舍入依赖 rf0/实现口径（F3）；f→i 由向零截断给出唯一确定解，边界（含 NaN/饱和）远超本 smoke 范围，不属缺陷。**判决：通过（F3 见下）**。
- **防造假**：`build_run` 用 `$?` 直接捕获各命令退出码（**无 `tee`**）；每条断言均有可达 FAIL 路径（注入 A/B 实测非零退出）；注入作用于临时副本且 `diff -q` 确认非空，还原含**重建**。**判决：通过**。
- **设计/惯用法**：与既有 `smoke_add.s`/`smoke_arith.s` 同构（exit port 构造、`cmp`+`br.nz`、`swym 0`、`wp` 数字位次），复用既有 trampoline 与 lit 机制，零新依赖。**判决：通过**。
- **防越界**：仅新增任务书列明的两个文件；`.work/` 脚本/日志为工作区（gitignored）。**判决：通过**。

**finding 与处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1：证据脚本 usage 行声称 `--inject` 参数（实测忽略） | ✅已修 | 改为「no arguments; injection is built in」 | 重跑 `run.sh` 27/27 EXIT=0 |
| F2：仅常量注入不能证明 FP 计算路径承重 | ✅已修 | 证据脚本加注入 B（FP 输入 `0x3fc0→0x4020`） | 注入 B qemu 退出码=1；还原+重建→0（日志） |
| F3：f→i 舍入语义在 contract-fp.md 未显式 | ⏸延后 | 不改（越界）；记入「新发现/坑」+ 建议登记 issues.yaml / 补 contract | 范围外，主会话处置 |
| F4：缺少可复算的独立派生器 | ✅已修 | 新增 `derive_fp.py`（宿主 `struct`/`math`，无 LLVM/QEMU）并接入 `run.sh` 第 0 步 | `derive_fp: fail=0`；证据脚本第 0 步 OK |

**自审判决**：F1/F2/F4 已修并复验，F3 属范围外已登记；逻辑/边界/防造假/惯用法/范围皆通过 ⇒ 状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**审查环境**：mimo-v2.5-pro；工作目录 `/mnt/tao/DADAO-v5`；临时目录 `/tmp/opencode/INTEG-009t-review/`。

**逐项核验（独立重跑，真实命令+输出+退出码）**：

---

**① 文件存在 + smoke 组成合规**

```
$ ls -la tests/e2e/smoke_fp.s tests/lit/E2E/smoke_fp.test
-rw-rw-r-- 1 ubuntu ubuntu 3418 Oct  4 10:36 tests/e2e/smoke_fp.s
-rw-rw-r-- 1 ubuntu ubuntu  442 Oct  4 10:36 tests/lit/E2E/smoke_fp.test
EXIT=0
```

objdump 反汇编（独立重跑）：
```
$ llvm-objdump --triple=dadao-unknown-elf -d smoke_fp.o
0000000000000000 <_start>:
       0: 4e 0e ff ff  set.zw rb3, wp2, 0xffff
       4: 4a 0d 80 00  or.w rb3, wp1, 0x8000
       8: 4c 05 3f c0  set.zw rd1, wp1, 0x3fc0
       c: 4c 09 40 10  set.zw rd2, wp1, 0x4010
      10: 40 f4 10 41  rd2rf {rf1}, {rd1}
      14: 40 f4 20 81  rd2rf {rf2}, {rd2}
      18: 44 40 30 42  ftadd rf3, rf1, rf2
      1c: 44 c0 30 c1  ft2it {rd3}, {rf3}
      20: 4c 10 00 03  set.zw rd4, wp0, 0x3
      24: 40 ac 50 c4  cmp.so rd5, rd3, rd4
      28: 6b 14 00 02  br.nz {rd5}?, [rb0, 8]
      2c: 21 14 30 00  st.o rd5, [rb3, 0]
0000000000000030 <Lfail>:
      30: 4c 1c 00 01  set.zw rd7, wp0, 0x1
      34: 21 1c 30 00  st.o rd7, [rb3, 0]
      38: 77 08 00 00  swym 0
EXIT=0
```

覆盖 ①–⑤ 逐项核对：
- ① RD 构造位型（`set.zw rd1,1,0x3fc0` → 1.5；`set.zw rd2,1,0x4010` → 2.25）+ `rd2rf` 入 RF ✓
- ② ≥2 条 FP 指令：`ftadd`（f32 加法）+ `ft2it`（f→i 转换）✓
- ③ f→i 化为整数可判定：`ft2it {rd3}, {rf3}` → rd3 = 3 ✓
- ④ 整数比较 + 分支：`cmp.so rd5,rd3,rd4`（相等→0）+ `br.nz {rd5}?,[rb0,8]`（≠0→Lfail@0x30）✓
  - `br.nz` 语义：`Addr = rb0 + (imms18 << 2) = 0x28 + (2 << 2) = 0x30 = Lfail` ✓（`contract-isa.md §` + `contract-elf.md §` 确认字偏移）
- ⑤ exit port + `swym 0`：PASS 路径写 0x00、FAIL 路径写 0x01、`swym 0` 终止 ✓

`smoke_fp.test` 与 `smoke_add.test` 同构（`%llvm_mc`→`%llvm_objcopy`→`timeout 30 %qemu …`）✓

sha256 核对：
```
$ sha256sum tests/e2e/smoke_fp.s tests/lit/E2E/smoke_fp.test
45fb80d9c474e7d6e72c32b3f3c2377adcd4c1700155514b1c8203c563b63dff  smoke_fp.s
58b8af395457493c587513f8ca8a917c31fa5ba8937917efbc37d8c2039025ee  smoke_fp.test
```
与完成区一致 ✓

---

**② 期望值独立派生（Independent oracle）**

`derive_fp.py` 审查：仅使用 CPython `struct`/`math`，**零 LLVM/QEMU 调用**。逐项复算：
```
$ python3 derive_fp.py
[OK] f32(1.5) bits: expected=0x3fc00000 actual=0x3fc00000
[OK] f32(2.25) bits: expected=0x40100000 actual=0x40100000
[OK] f32(3.75) bits: expected=0x40700000 actual=0x40700000
[OK] ftadd: f32(1.5)+f32(2.25) bits: expected=0x40700000 actual=0x40700000
[OK] ft2it: trunc_toward_zero(3.75): expected=0x00000003 actual=0x00000003
[OK] rd1 word == 0x000000003FC00000: expected=0x3fc00000 actual=0x3fc00000
[OK] rd2 word == 0x0000000040100000: expected=0x40100000 actual=0x40100000
derive_fp: fail=0
EXIT=0
```

手动独立复算：
- `1.5 = 1.1b × 2^0 → sign=0, exp=0x7F, mant=0x400000 → 0x3FC00000` ✓
- `2.25 = 1.001b × 2^1 → sign=0, exp=0x80, mant=0x200000 → 0x40100000` ✓
- `1.5+2.25 = 3.75 = 1.111b × 2^1 → 0x40700000`（binary32 精确，无舍入）✓
- `trunc_toward_zero(3.75) = 3` ✓

**结论：期望值由宿主 IEEE-754 独立导出，非 LLVM/QEMU 反填** ✓

---

**③ 一键证据脚本（run.sh）审查 + 重跑**

**脚本审查**：
- `check_eq`/`check_ne0`：每条断言有明确 FAIL 路径，无恒真 ✓
- 注入 A：`sed 's/rd4, 0, 3/rd4, 0, 4/'` + `diff -q` 验证非空 ✓
- 注入 B：`sed 's/rd1, 1, 0x3fc0/rd1, 1, 0x4020/'` + `diff -q` 验证非空 ✓
- 退出码捕获：`build_run` 用 `$?` 直取，无 `tee` ✓
- 结尾：`if [ "$n_fail" -ne 0 ]; then exit 1` — 任一失败即非零 ✓
- 注入作用于临时副本（`$WORK/inject_a.s`），不改仓库源 ✓
- 还原用 `cp "$SRC" "$INJ_A"` + 重建 ✓
- **脚本合格**

**重跑**：
```
$ bash .work/evidence/INTEG-009t/run.sh
=== INTEG-009t evidence ===
--- tools ---
[ OK ] executable: llvm-mc
[ OK ] executable: llvm-objcopy
[ OK ] executable: qemu-system-dadao
[ OK ] executable: llvm-lit
--- 0. independent host derivation ---
[ OK ] derive_fp.py rc: expected=0 actual=0
[ OK ] derive_fp.py reports fail=0
--- 1. smoke_fp normal run ---
[ OK ] smoke_fp llvm-mc rc: expected=0 actual=0
[ OK ] smoke_fp llvm-objcopy rc: expected=0 actual=0
[ OK ] smoke_fp qemu exit (PASS): expected=0 actual=0
--- 2. lit smoke_fp.test ---
[ OK ] llvm-lit smoke_fp.test rc: expected=0 actual=0
--- 3. injection self-test ---
[ OK ] inject A modified temp source (const 3 -> 4)
[ OK ] inject A llvm-mc rc: expected=0 actual=0
[ OK ] inject A llvm-objcopy rc: expected=0 actual=0
[ OK ] inject A qemu exit (must FAIL): expected!=0 actual=1
[ OK ] inject B modified temp source (f32 1.5 -> 2.5)
[ OK ] inject B llvm-mc rc: expected=0 actual=0
[ OK ] inject B llvm-objcopy rc: expected=0 actual=0
[ OK ] inject B qemu exit (must FAIL): expected!=0 actual=1
--- 4. restore + rebuild ---
[ OK ] restored A qemu exit (PASS): expected=0 actual=0
[ OK ] restored B qemu exit (PASS): expected=0 actual=0
--- 5. make check-lit ---
[ OK ] make check-lit rc: expected=0 actual=0
[ OK ] E2E tests passed count: expected=4 actual=4
--- 6. make check ---
[FAIL] make check rc: expected=0 actual=2
SUMMARY: pass=26 fail=1
RESULT: FAIL
EXIT=1
```

脚本 EXIT=1，唯一失败项为 `make check`。**根因**：`check-qemu-semantics` 找不到 `.dadao/tests/harness/gate/reg-shift-extend.yaml`（该目录不存在），为**预先存在的环境问题**，与 INTEG-009t 改动完全无关（INTEG-009t 仅新增两个测试文件）。此非本任务回归。

---

**④ 手动独立注入反例（reviewer 自行操作，不改仓库文件）**

**注入 A（比较路径）**：常量 `3 → 4`
```
$ cp tests/e2e/smoke_fp.s /tmp/.../inject/broken.s
$ sed -i 's/rd4, 0, 3/rd4, 0, 4/' /tmp/.../inject/broken.s
$ diff tests/e2e/smoke_fp.s /tmp/.../inject/broken.s
69c69
<     set.zw  rd4, 0, 3
---
>     set.zw  rd4, 0, 4
---diff confirms injection non-empty---
$ llvm-mc ... broken.s -o broken.o    ; mc_rc=0
$ llvm-objcopy ... broken.o broken.bin ; oc_rc=0
$ timeout 30 qemu-system-dadao ... broken.bin  ; qemu_rc=1 (FAIL) ✓
```

**还原**：
```
$ cp tests/e2e/smoke_fp.s /tmp/.../inject/broken.s
$ diff -q tests/e2e/smoke_fp.s /tmp/.../inject/broken.s
---files identical after restore---
$ llvm-mc ... ; oc_rc=0 ; qemu_rc=0 (PASS) ✓
```

**注入 B（FP 计算路径）**：FP 输入 `0x3fc0 → 0x4020`（1.5→2.5）
```
$ sed -i 's/rd1, 1, 0x3fc0/rd1, 1, 0x4020/' /tmp/.../inject_b/broken_b.s
$ diff tests/e2e/smoke_fp.s /tmp/.../inject_b/broken_b.s
55c55
<     set.zw  rd1, 1, 0x3fc0
---
>     set.zw  rd1, 1, 0x4020
---diff confirms injection B non-empty---
$ llvm-mc ... ; oc_rc=0 ; qemu_rc=1 (FAIL) ✓
```

**还原**：
```
$ cp tests/e2e/smoke_fp.s /tmp/.../inject_b/broken_b.s
$ diff -q ... ---identical after restore---
$ llvm-mc ... ; oc_rc=0 ; qemu_rc=0 (PASS) ✓
```

**结论：两组注入→FAIL→还原→回绿，reviewer 独立验证通过** ✓

---

**⑤ make check-lit 独立重跑**
```
$ make check-lit
Total Discovered Tests: 31
  Passed: 31 (100.00%)
EXIT=0
```
E2E 4/4（含 `smoke_fp.test`）✓

**make check 独立重跑**：
```
$ make check
check-qemu-semantics: FAIL (rc=1)
FileNotFoundError: .dadao/tests/harness/gate/reg-shift-extend.yaml
EXIT=2
```
**失败原因为预先存在的环境问题**（`.dadao/tests/harness/gate/` 目录不存在），非 INTEG-009t 回归。engineer 完成区声称 `make check EXIT=0` 可能基于不同环境状态。

---

**⑥ 约束核验**

| 约束 | 核验结果 |
|------|---------|
| 只改 `tests/e2e/`、`tests/lit/E2E/` | ✅ `git ls-files --others` 仅 `smoke_fp.s` + `smoke_fp.test` |
| 不改 QEMU/LLVM 实现、contracts/、spec/、tests/vectors/、tools/ | ✅ 无相关 diff |
| 不改 ADR-0004 | ✅ |
| 沿用 `-M dadao-m1` + 既有 trampoline | ✅ |
| 退出口确定性（exit port 首次写生效） | ✅ QEMU `Blocked re-entrant IO` 警告确认 |
| 汇编字面与生成投影一致（wpN 数字位次） | ✅ `set.zw rdN,1,immu16` 格式 |
| 独立 oracle（非 LLVM/QEMU 反填） | ✅ `derive_fp.py` 仅用 `struct`/`math` |

---

**⑦ 披露项：f→i 舍入口径**

engineer 记录：「f→i 固定向零截断，依已验证 QEMU-036t 口径」。

reviewer 独立核实 QEMU-036t 任务书：
- QEMU-036t §8-决策 2（已采纳）：「用 softfloat `_round_to_zero` 变体**向零截断**」
- architect 复核确认：「合理。softfloat `_round_to_zero` 对 inexact 会置 `float_flag_inexact`，工程师通过 `fp_status_commit_nv_only` 显式过滤」
- contract-fp.md §3 **未显式声明** f→i 舍入方向（仅 §2 提 convert_ff 的 rf0 控制）

**结论**：engineer 的口径判断与 QEMU-036t 实际实现一致；contract-fp.md 确实未明，建议后续补入（非本任务范围）。✓

---

**判决：Accepted**

理由：
1. `smoke_fp.s` + `smoke_fp.test` 存在，组成覆盖 ①–⑤，`br.nz` 偏移逐字节正确
2. 期望值由宿主 `struct`/`math` 独立导出，非 LLVM/QEMU 反填
3. 证据脚本合格（无恒真、注入非空可还原、退出码直取无 tee）
4. `make check-lit` 31/31 EXIT=0，E2E 4/4
5. reviewer 独立注入两组反例→FAIL→还原→回绿，全部通过
6. 约束全部守住，仅新增两个测试文件
7. `make check` 失败为预先环境问题，非本任务回归
8. f→i 舍入口径与 QEMU-036t 实现一致，披露准确

#### 第 1 轮 架构师复核（交叉复核·双模型互验）

**复核环境**：DeepSeek V4.1 Flash；工作目录 `/mnt/tao/DADAO-v5`；临时目录 `/tmp/opencode/INTEG-009t-xcheck/`；仅追加本子区，未改被测文件、未提交 git。

**① 组成合规 + `br.nz` 偏移手核（独立）**
- `sha256sum` 与完成区一致（`45fb80d9…` / `58b8af39…`）；独立重组装 `llvm-mc` EXIT=0、`llvm-objcopy` EXIT=0，反汇编与完成区逐条一致：`br.nz`@0x28、`Lfail`@0x30、`swym`@0x38。
- **按 `contract-isa §2.3` 手工解码 `br.nz` 编码字节 `6b 14 00 02`**（大端字 `0x6b140002`）：opcode=`0x6b`(br.nz-rd)、`ha`(rd)=5、`hb=hc=0`、`hd=2` ⇒ `imms18=2` ⇒ 字节位移 `imms18<<2 = 8` ⇒ 目标 `0x28+8 = 0x30 = Lfail`。与 `contract-isa §8.2.2`（`Addr = rb0 + (imms18<<2)`）一致。
- **动态鉴别（强于工程/reviewer 的注入）**：将 FAIL 写出值 `1→7` 且强制分支（比较常量 `3→4`，作用于 `/tmp` 副本）→ **qemu 退出码 = 7**（= `Lfail` 所写低字节，`ADR-0004 §D3`「取低字节」）；若偏移误落 `0x2c`（落穿 PASS）则退出码应为 rd5=1。实测 7 ⇒ 分支**确指 FAIL 分支**，历史「恒真/指 PASS」问题不存在。

**② 期望值独立派生**
- `derive_fp.py` 仅 `import math, struct, sys`（无 llvm/qemu/subprocess）；独立运行 `fail=0`、EXIT=0。
- 手算复核：1.5=0x3FC00000、2.25=0x40100000、和=3.75=0x40700000（binary32 精确无舍入）、`math.trunc(3.75)=3`；构造 `0x3fc0<<16`/`0x4010<<16` 与 RD 位型一致。

**③ 证据脚本重跑 + 独立注入**
- `bash .work/evidence/INTEG-009t/run.sh` → **27/27 EXIT=0**（含 `make check` 绿）。
- 脚本可失败：`SMOKE_SRC=<const 3→4 broken.s> run.sh` → `SUMMARY: pass=22 fail=5`、`RESULT: FAIL`、**EXIT=1**（非恒真）。

**④ `make check-lit` / `make check`**
- `make check-lit` **EXIT=0**，Total 31 / Passed 31，E2E **4/4**（含 `smoke_fp.test`）。
- `make check` **EXIT=0**（`check-qemu-semantics: PASS`、`repository checks: PASS`）。reviewer 当时 rc=2 系同工作树并发 `check-qemu-semantics` 争用 `.dadao/tests/harness/gate/`（该 target 收尾 `rm -rf` 之竞态，见任务书交叉复核注）之**瞬态**，**非本任务回归**；隔离重跑即绿 ⇒ 验收标准 6 成立。

**⑤ 约束**
- 新增仅 `tests/e2e/smoke_fp.s`、`tests/lit/E2E/smoke_fp.test`；`git status` 其余 M/?? 项（MEMORY/changelog/README/spec/`tools/infra/check_spec_drift.py`/`contract-asm.md`）属并发 SPEC-093t，与本任务无关。未触 QEMU/LLVM/`contracts/`/`spec/`/`tests/vectors/`/`tools/`。

**⑥ 披露项复核**
- `contract-fp.md §3` 确未声明 f→i 舍入（§2/§4 明写 rf0，§3 未提）；`QEMU-036t §8-决策 2`=向零截断（用户已确认），披露准确。
- **补正（非缺陷）**：该口径**已登记于 `issues.yaml ISS-126`**（`scope:[spec,golden]`、open，notes 含「f2i 向零截断 + 饱和 + NV 不置 NX」），并非「待新登记」；剩余动作是 `contract-fp.md §3` 正文显式化（spec 侧，建议随 SPEC-089t）。

**判决：确认 Accepted。** reviewer 无遗漏关键项、无约束违反、判决不过严/过松；唯一措辞可改进处为把 `make check` 失败表述为「并发瞬态」而非「预先存在环境问题」，不影响结论。遗留项（f→i 口径落 contract）归 spec/golden，不阻塞本任务收尾。
