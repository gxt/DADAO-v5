# LLVM-121t: 原子指令后端（`fence` + `lr/sc` 24 条：MC 定义 / ISel / `__atomic_*` 展开 / CAS 环）

**模块**：llvm
**项目里程碑**：M9
**依赖**：`ADR-0034`（`Accepted`：编码/命名定案）、`contracts/opcodes.yaml`（259 条真源）、`LLVM-116t`（上一轮 ISA 编码迁移的 llvm 册先例，`已验证`）、`ISS-307`（本批 4 册总账）；**下游串行**：`QEMU-067t`（②）→ `INFRA-100t`（③）→ `TESTCASES-056t`（④）
**状态**：待验收

## 执行环境
**执行环境**：本地

> **编号（现场取号，2026-10-21）**：`llvm` 模块现有最大 = `LLVM-120t` ⇒ 取 **`121`**；`find .tao -name 'LLVM-121*'` = 0 命中。
> **本批位置**：`ISS-307` 的 4 册串行链 **① 本册 → ② `QEMU-067t` → ③ `INFRA-100t` → ④ `TESTCASES-056t`**。四册都改**共享安装根**，**禁止并行**（同一工作树同一时间只允许一个写者）。
> **本批边界（用户 2026-10-21 派单）**：**只落组件执行面**；`spec/`、`contracts/**`、`.tao/contracts/**` **不改** ✗（编码已由 `ADR-0034` 定案）；`scope: excluded` 的 re-scope **不在本批**（见「已知边界」）。

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 编码与语义真源（`ADR-0034`，`Accepted`）

- **`fence`**（`D1`/`D2`）：`op = 0x77`、`ha = 0x20`（`100-000`）、`value = 0x77800000`、`mask = 0xFFFC0000`、格式 `oiii`、`id = fence_oiii_imm`。`immu18` 三段：`fm = [17:12]`、`pred = [11:6]`、`succ = [5:0]`；汇编层**仍是**一个 18 位无符号立即数，符号常量按位或组合：

  | 常量 | 值 | 常量 | 值 |
  | --- | --- | --- | --- |
  | `PRED_R` | `1<<6`（`0x040`） | `SUCC_R` | `1<<0`（`0x001`） |
  | `PRED_W` | `1<<7`（`0x080`） | `SUCC_W` | `1<<1`（`0x002`） |
  | `PRED_I` | `1<<8`（`0x100`） | `SUCC_I` | `1<<2`（`0x004`） |
  | `PRED_O` | `1<<9`（`0x200`） | `SUCC_O` | `1<<3`（`0x008`） |

  合法性：`fm = 0` 是**唯一**已定义值（`fm = 8` 为「TSO 预留、当前未定义」，其余保留）⇒ 非 0 ⇒ 保留；`pred[11:10]`、`succ[5:4]` = SBZ，非零 ⇒ 保留。保留编码的执行后果是 **ILLI**（`SimRISC-12 §3.1`）。
- **`lr/sc`**（`D3`/`D4`/`D5`）：24 条，名字 = `<lr|sc>.<b|w|t|o>.<nn|an|nr|ar>`（**宽度在前**），`id = <助记符>_orrr_rd`（`.` → `_`），`op = 0x77`、`mask = 0xFFFC0000`、格式 `orrr`、三字段 `rdhb`/`rdhc`/`rbhd`。落位（`ha` 低 6 位）：

  ```
  lr: 0x00 lr.o.nn  0x01 lr.t.nn  0x02 lr.w.nn  0x03 lr.b.nn
      0x04 lr.o.an  0x05 lr.t.an  0x06 lr.w.an  0x07 lr.b.an
      0x08 lr.o.ar  0x09 lr.t.ar  0x0A lr.w.ar  0x0B lr.b.ar
  sc: 0x10 sc.o.nn  0x11 sc.t.nn  0x12 sc.w.nn  0x13 sc.b.nn
      0x14 sc.o.nr  0x15 sc.t.nr  0x16 sc.w.nr  0x17 sc.b.nr
      0x18 sc.o.ar  0x19 sc.t.ar  0x1A sc.w.ar  0x1B sc.b.ar
  ```

  `lr` 只有 `nn/an/ar`、`sc` 只有 `nn/nr/ar`（`lr.*.nr`、`sc.*.an` **已删除**，组合不存在 ⇒ 汇编器拒绝）。`001-100`–`001-111`、`011-100`–`011-111` 保留空。
- **语义**（`D6`，正文见 `spec/SimRISC-12 §3.2`）：`lr` 的 `hb`（`rdHB`）**必须为 `rd0`**，手工编码 `hb ≠ 0` ⇒ **ILLI**；`sc` 成功写 `rdHB = 0`、失败写 `1`，**无论成败都清本 hart 全部保留标记**；地址须**8 字节自然对齐**，否则 **MALIGN**；`nn`/`nr`/`an`/`ar` = 无 / 释放 / 获取 / 两者兼有。保留粒度由平台定义（可实现为精确地址或 cache line）。

### 现场事实（2026-10-21 核，执行前须复核）

1. **MC 面已有 `fence`、没有 `lr/sc`**：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.td.patch:1642` 的 `def fence : DADAOOiii<"fence">` = `op 0x77 / ha 0x20 / Pattern = []`（MC-only）；`grep -n 'lr\.\|sc\.' <该文件>` = **0 命中** ⇒ 现无任何 `lr`/`sc` def，`llvm-mc` 无法汇编这 24 条。
2. **后端零原子面**：`DADAOISelLowering.cpp.patch` 全文件 `grep -i atomic` = **0 命中**；`DADAOSubtarget.cpp.patch`/`DADAOTargetMachine.cpp.patch` 无 `setMaxAtomicSizeInBitsSupported`。LLVM 侧默认值 = `TargetLoweringBase.cpp:1045` `MaxAtomicSizeInBitsSupported = 0`、`TargetLowering.h:2304` `shouldInsertFencesForAtomic()` 返回 `false` ⇒ `AtomicExpandImpl::expandAtomicRMWToLibcall`（`AtomicExpandPass.cpp:2010`，底层 `expandAtomicOpToLibcall:2057`）把 RMW / `cmpxchg` / `load atomic` / `store atomic` 全部降为 `__atomic_*` **libcall**；工具链**不存在**这些符号 ⇒ 任何 `_Atomic` / `__atomic_*` 程序**链接失败**。
3. **门控约束（本册必须同批处理）**：
   - `tools/llvm/validate_instrinfo.py` 的 check 3（orphan：每个 `.td` def 须唯一映射一条 opcodes 记录，join key = `(mnemonic, format, op, ha)`）与 check 5（**非 m1 def 只限 allow-list** `MC_ONLY_EXCLUDED_IDS`，`:82` 现只有 `fence_oiii_imm`）⇒ 新增 24 条 `scope: excluded` def **必须**同批把 24 个 `id` 并入该 allow-list，否则 `make check-instrinfo` 红。
   - `make check-isa-coverage`（`tools/llvm/gen_isa_coverage.py --check`）第①层**逐条把规范操作数形态喂安装根 `llvm-mc`**、并独立比对编码；第②层**机械提取**补丁树里的 `Pat`/`def`/`ISel` 引用。⇒ 改 `.td` 后必须 `make install-host` 重建 `llvm-mc`，并**重生成** `tools/llvm/llvm-isa-backend-matrix.{tsv,md}` 与 `tests/llvm/lit/MC/DADAO-gen/gen-*.s`（`generate_lit_vectors.py`），再 `--check` 绿（`ISS-210` 陈旧安装根 ⇒ 假绿）。
   - `check-patch-tree`：一文件一补丁 + `series` + `changelog`（`docs/Process-01`）。
4. **lit 先例**：MC 编码断言 `tests/llvm/lit/MC/DADAO/oiii.s`（`fence 0` → `77 80 00 00`）；CodeGen 结构断言 `tests/llvm/lit/CodeGen/DADAO/*.ll`（`llc -mtriple=dadao | FileCheck`），汇编器**拒绝**用例先例 `tests/llvm/lit/MC/DADAO/cfx2-trap-escape-err.s`。
5. **参考实现指针**（内容溯源，**非执行必需**，不得复制代码）：`PPCISelLowering.cpp:14250 emitAtomicCmpSwapHardware`（伪指令 + 展开）、`MipsISelLowering.cpp:1866 emitAtomicCmpSwap` / `:1922 emitAtomicCmpSwapPartword`（DAG 内直接展开 + 子字宽掩码合成）、`RISCVISelLowering.cpp:27693 shouldInsertFencesForAtomic`（弱序机 fence 选择口径）。

## ✅ 已裁定（2026-10-21，用户「甲」）

**裁定原话**：「甲」= **按数据宽度对齐**：`.b`=1 / `.w`=2 / `.t`=4 / `.o`=8 字节自然对齐；不满足 ⇒ **MALIGN**。

> **标签对照（勿混）**：用户裁定编号「甲」= **按数据宽度对齐**（即本册旧文「乙」项）；旧文「甲」（全族 8 B）**已作废**。冲突源头已收口：`ADR-0034 D6` 就地修订 + `spec/SimRISC-12 §3.2` 措辞订正（编码不变）。

**对本册的具体影响**：

- **i32 可用 `lr.t/sc.t`**：C 的 `_Atomic int` 4 B 对齐即可，`lr.t` 在 8 B 字内按 `k = addr & 7` 取 4 B 窗 ⇒ `ATOMIC_CMP_SWAP(i32)` 走 `lr.t.an`/`sc.t.ar` 环，**不需** `lr.o/sc.o` 掩码合成。
- **i8/i16** 用 2 B / 1 B 对齐语义；掩码合成时**按宽度判 MALIGN**（`.w` 非 2 B 对齐、`.b` 非 1 B 对齐才 MALIGN），**不要求 8 B 对齐**。
- i64 仍 `lr.o/sc.o`（8 B 窗）；MALIGN 向量 = 低于**该宽度**对齐的地址；保留粒度仍 8 B。

## 目标

1. **MC 面**：24 条 `lr/sc` def + `fence` 立即数的汇编期合法性（`fm≠0`、`pred/succ` 的 SBZ 非零 ⇒ 汇编错误）。
2. **顺序面**：`ISD::ATOMIC_FENCE` → `fence`；普通 `load/store` + `fence` 由 `shouldInsertFencesForAtomic` 决定。
3. **RMW/CAS 面**：`ATOMIC_CMP_SWAP`(i64/i32) → `lr/sc` **重试环**；子字宽（i8/i16）在 4/8 B 字上**掩码合成**且**不破坏同字相邻字段**；`shouldExpandAtomicRMWInIR` ⇒ `CmpXChg`（`swap`/`fetch_*` 全部走 CAS 环）。
4. **`__atomic_*` 家族不再落 libcall**（编译 + 链接期硬判据见「验收 A2」）。
5. lit 新增用例（MC 编码 + CodeGen 结构），门控全绿（`check-instrinfo` / `check-isa-coverage` / `check-lit` / `check-lit-full` / `check-patch-tree`）。

## 接口规范

**输入**（只读）：
- `ADR-0034`（`D1`–`D7`；编码表见「现状」）、`spec/SimRISC-12 §3.1/§3.2`（语义正文，**只读**）、`contracts/opcodes.yaml`（259 条，`fence` = `0x77800000` / `lr.o.nn` = `0x77000000` / `sc.o.nn` = `0x77400000`，均按 `value = (0x77<<24) | (ha<<18)`）。
- `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（现状补丁树）、`.work/source/llvm-project/**`（**只读参照**，源码检出；交付只走 `patches/**`）。
- `docs/Process-01`（组件补丁流：改 `.work/source` → 本地 commit → 重导补丁）、`Makefile` 的 `install-host` / `check-instrinfo` / `check-isa-coverage` / `check-lit`。

**输出**（交付物）：
1. `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.td.patch`：+24 个 `lr/sc` def（`DADAOOrrr`，`Pattern = []`）+ `fence` 立即数合法性的 `.td`/汇编器侧约束（若用 `AsmParser` 前置断言）。
2. `.../DADAOISelLowering.cpp.patch` + `.../DADAOISelLowering.h.patch`：`setMaxAtomicSizeInBitsSupported(64)`、`shouldInsertFencesForAtomic`、`shouldExpandAtomicRMWInIR`、`ATOMIC_FENCE`/`ATOMIC_CMP_SWAP(_WITH_SUCCESS)` 的 action/自定义 lowering。
3. 需要时的伪指令与展开 pass：新文件（如 `.../DADAOExpandAtomicPseudo.cpp/.h`）+ `.../CMakeLists.txt.patch` + `.../DADAOSubtarget.cpp.patch`（pass 注册）+ `.../DADAOInstrInfo.td.patch`（pseudo def）。
4. `tools/llvm/validate_instrinfo.py`：`MC_ONLY_EXCLUDED_IDS` **+24 个 `lr/sc` id**（`fence_oiii_imm` 保留）。
5. `tests/llvm/lit/MC/DADAO/atomics-lrsc.s`（24 条编码）、`tests/llvm/lit/MC/DADAO/atomics-fence-imm.s`（合法立即数 + 保留编码拒绝）、`tests/llvm/lit/CodeGen/DADAO/atomics-*.ll`（结构断言）。
6. 重生成物：`tests/llvm/lit/MC/DADAO-gen/gen-*.s`、`tools/llvm/llvm-isa-backend-matrix.{tsv,md}`。
7. `components/llvm-project/changelog.md`（`## M9` 节）+ `series` 同步。
8. `.work/evidence/LLVM-121t/**`（含 `run.sh` 与 `--inject` 反例）+ `.work/log/llvm/LLVM-121t/**`。
9. 本册完成区。

**约束**：
- **不改** `spec/`、`contracts/**`、`.tao/contracts/**`、`components/qemu/**`、`components/musl/**`、`.tao/archive/**`。
- **不新增指令、不改编码**（`ADR-0034` 已定）；需要新编码 ⇒ **停下报告**。
- 不改期望值迁就实现；**不得**以 libcall/`-lcompiler_rt` 兜底、不得以「放宽断言/跳过用例」当通过。
- 组件补丁**一文件一补丁** + `series` + `changelog`；`check-patch-tree` 断言⑥/⑨。
- **计数现场派生**（`.td` def 数、lit 用例数、矩阵行数），禁写死。
- **独立 oracle**：编码期望值来自 `ADR-0034` 表 / `contracts/opcodes.yaml`，**不从 `llc`/`qemu` 输出回填**；结构断言只断言「应出现的指令序列」，不改语义期望。
- **`install-host` 前置**：本册需重建 `llvm-mc`/`llc`/`clang`，该命令由**主会话**执行（长任务归主会话；执行者不得自行长构建）。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. `fence`：ordering → `(fm, pred, succ)` 映射（**必须逐条断言**）

`fm = 0` 恒定；`pred`/`succ` 取 R/W/I/O 的并集（本机无 I/O 语义，但仍按规范置位）：

| LLVM `AtomicOrdering` | `pred` | `succ` | `immu18` | 最终字 |
| --- | --- | --- | --- | --- |
| `monotonic`/`unordered` | — | — | 不发射 fence | — |
| `acquire` | `R` | `R｜W` | `0x0043` | `0x77800043` |
| `release` | `R｜W` | `W` | `0x00C2` | `0x778000C2` |
| `acq_rel` / `seq_cst` | `R｜W｜I｜O` | `R｜W｜I｜O` | `0x03CF` | `0x778003CF` |

- `seq_cst` 的 load/store 由 `shouldInsertFencesForAtomic` 拆成「acquire 侧前置 / release 侧后置 + seq_cst 追踪 fence」——**顺序位置**以 LLVM `AtomicExpandPass` 的既有语义为准（先用最小 IR 观察该 pass 的插入位置，再落 lowering；不得凭印象）。
- 汇编层：`fence PRED_R|PRED_W|SUCC_R|SUCC_W` 之类符号常量组合必须可汇编并映射到上表值；`fm≠0`、SBZ 非零 ⇒ **汇编错误**（错误文案说明「保留编码」）。

### B. `lr/sc` 重试环（i64 / i32）

`lr`/`sc` 是**唯一**原子原语（`ISS-294` 裁定 LR/SC-only，不加 AMO），所有 RMW/CAS 必须归约到环：

```
   lr.<w>.an  rd_old, [rb_addr]        ; 尺寸 = 宽度
   bne        rd_old, rd_cmp, L_done   ; 不等 ⇒ 失败（rd_old 已是返回值）
   sc.<w>.ar  rd_ok,  rd_new, [rb_addr]
   bne        rd_ok,  rd_zero, L_retry ; 失败 ⇒ 重试
L_done:
```

- **i64** → `lr.o.an` / `sc.o.ar`（8 B 窗）。**i32** → 按「已裁定（按数据宽度）」走 `lr.t.an` / `sc.t.ar`（4 B 窗，可落在 8 B 字的任一 4 B 半；4 B 对齐即合法，不再要求 8 B）。
- 环的落法二选一（**不预设**）：① 伪指令（`.td` 里 `Pattern = []` 的 pseudo）+ 目标 `MachineFunctionPass` 展开（`PPCISelLowering.cpp:14250` 形态）；② `ISD::ATOMIC_CMP_SWAP_WITH_SUCCESS` 的 `Custom` lowering 内直接建环（`MipsISelLowering.cpp:1866` 形态）。选②时须保证寄存器分配不被环破坏（`Mips` 用固定物理寄存器 + `MRI` 约束）。
- **`lr` 的 `hb` 恒为 `0`**（`rd0`）：`lr` 是 2 操作数形态，编码时 `rdhb = 0`；后端**不得**生成 `hb≠0` 的 `lr`（否则执行 ILLI）。

### C. 子字宽（i8/i16）：掩码合成（**必须断言同字相邻字段不被破坏**）

- 原则：CAS 作用在**包含目标字节的 4 B（i16）或 8 B 字**上；`lr` 读整字 → 掩码替换 → `sc` 写整字。
- 实现落点二选一：① IR 层（`shouldExpandAtomicCmpXchgInIR` = `CustomExpand` + 目标 hook，做「读整字 + 掩码」的 IR 环）；② DAG 层 `Custom`（`MipsISelLowering.cpp:1922 emitAtomicCmpSwapPartword` 形态）。
- **断言方式**：lit 结构断言必须能看出「整字读 + 掩码与/或 + 整字 CAS」，且相邻字节的 `andn`/`or` 掩码常量与字节序（大端）一致；**运行期不破坏相邻字段**由 ④ 的探针覆盖（本册 A4 只做结构 + 静态编码证据）。

### D. RMW → CAS

`shouldExpandAtomicRMWInIR()` 对 i8/i16/i32/i64 一律返回 `AtomicExpansionKind::CmpXChg`（`TargetLowering.h:274` 枚举）⇒ `atomicrmw {add,sub,and,or,xor,xchg,nand,min,max,umax,umin}` 全部落到 B/C 的环。

### E. 后端原子开关

`setMaxAtomicSizeInBitsSupported(64)`；`shouldInsertFencesForAtomic()` ⇒ `true`（弱序机，让 `AtomicExpandPass` 只发 fence + 普通访存）；`setOperationAction(ISD::ATOMIC_FENCE, MVT::i64, Custom)`；`ATOMIC_CMP_SWAP`/`ATOMIC_CMP_SWAP_WITH_SUCCESS`（`MVT::i64`/`i32`）⇒ `Custom`；`ATOMIC_LOAD`/`ATOMIC_STORE` ⇒ `Legal`（配 fence）。以上为**最低集合**，实现可增不减。

## 验收标准

**A 档（本册内可跑，结册必达）**

1. **A1 MC 编码**：`llvm-mc -triple=dadao -show-encoding` 对 24 条 `lr/sc` 逐条与「现状·编码表」一致（`ha`/`mask`/`value` 逐条打印）；`fence` 的 4 类合法值按 A 表编码；`fm≠0`、`pred/succ` SBZ 非零 ⇒ **汇编错误**（rc≠0 且报错含「保留」语义）。全部落 `tests/llvm/lit/MC/DADAO/atomics-*.s`。
2. **A2 不落 libcall（硬指标，编译+链接期可判）**：
   - 编译：`clang --target=dadao-unknown-elf -O2 -S` 的 `_Atomic`/`__atomic_*` 探针中 `grep -c '__atomic_'` = **0**；`llc` 输出含 `lr.`/`sc.`/`fence`（计数现场统计）。
   - 链接：`clang -c` 产物 `llvm-nm -u` 中 `__atomic_*` 命中 **0**；并用 `-nostdlib` 静态链接一个只用 `__atomic_*` + `_exit` 的最小 ELF，`llvm-nm` 全符号表中 `__atomic_` = **0**（**证明方式不依赖运行**）。
   - `__atomic_*` 家族覆盖面：`fetch_add/and/or/xor/exchange/compare_exchange/load/store` × `{1,2,4,8}` × `{acquire,release,acq_rel,seq_cst(+relaxed)}`，逐项计数现场派生。
3. **A3 结构断言（lit）**：i64/i32 CAS 环顺序（`lr`→比较→`sc`→重试）、i8/i16 整字掩码合成、`fence` 值与插入位置；断言须能对「改映射/改宽度/漏掩码」失败（见「可达 FAIL」）。
4. **A4 门控**：`make install-host`（主会话）后 `make check-instrinfo` 0 错、`make check-isa-coverage` 0 复核不符（矩阵已重生成且 `--check` 绿）、`make check-lit` 与 `check-lit-full` 全绿、`make check-patch-tree` 绿；`make check`（L1）绿。

**B 档（运行值对照；**BLOCKED-by-②**，不得伪造/降级）**

5. **B1 运行值对照**：`_Atomic` 各类型 + `__atomic_*` 家族的**运行期望值 = 独立 oracle**（Python 手算 / 宿主同源算法，**不从 `llc`/`qemu` 反推**）。**前置 = ② `QEMU-067t` 的 `lr/sc` 执行语义**；在本册交付时该档 **BLOCKED**（`qemu` 现状对这些指令一律 ILLI）。⇒ 本册 `待验收/已验证` 以 **A 档**为准；B1 证据由 ② 的端到端 + ④ 的家族验收落盘后**回填本册完成区**，回填前**不得**声称「运行通过」。

## 做（阶段）

- **阶段 0 现场复核**：打印 `.td` 现状（`fence` 行号、`lr/sc` 0 命中）、`ISelLowering` 的 atomic 0 命中、`validate_instrinfo.py:82` allow-list；记录门控基线（`check-instrinfo`/`check-isa-coverage`/`check-lit` 的 rc 与计数）。复核结论与本册不符 ⇒ 以现场为准并在完成区披露差异。
- **阶段 A MC 面**：加 24 def → `validate_instrinfo.py` allow-list → lit MC 用例 → `install-host`（主会话）→ `check-instrinfo` + `check-isa-coverage`（含矩阵/lit-gen 重生成）。
- **阶段 B 顺序面**：`shouldInsertFencesForAtomic` + `ATOMIC_FENCE` lowering + fence 立即数映射；lit 结构断言。
- **阶段 C CAS 环**：i64/i32（pseudo+pass 或 DAG custom 二选一）；`ATOMIC_CMP_SWAP(_WITH_SUCCESS)` action。
- **阶段 D 子字宽 + RMW**：i8/i16 掩码合成；`shouldExpandAtomicRMWInIR` ⇒ `CmpXChg`；lit 结构断言（含相邻字段掩码）。
- **阶段 E 收口**：`__atomic_*` 家族编译/链接证据（A2）→ `make check`（L1，主会话跑）→ 证据脚本 `--inject` 反例 → 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

1. 把 `acquire` 的 `succ` 改成 `R`（漏 `W`）⇒ `fence` 值从 `0x0043` 变 `0x0041` ⇒ lit 结构断言**红**。
2. 把 i32 CAS 的 `lr.t.an`/`sc.t.ar` 改成 `lr.o.nn`/`sc.o.nn` ⇒ 结构断言（宽度/序）**红**；`check-instrinfo` 不受影响（编码合法）⇒ 证明该断言**非恒真**。
3. `.td` 加 24 def 而不改 `validate_instrinfo.py` allow-list ⇒ `make check-instrinfo` **红**（check 5 报告「不在 allow-list」）。
4. i8/i16 掩码合成里把 `andn`（保留相邻位）改成 `and` ⇒ 结构断言（掩码常量/操作数）**红**；运行期相邻字节被清零由 ④ 覆盖。
5. 改 `fence` 的 `ha`（例如写回 `0x00`）⇒ `check-instrinfo` + `check-isa-coverage`（编码复核）**红**。

## 已知边界（**披露，不自行扩面**）

- **`scope: excluded` 的 re-scope 不在本批**：`contracts/opcodes.yaml` 的 `scope`、`spec/SimRISC-11/12` 的「未实现」措辞、`tools/spec/check_scope.py` 的期望计数、`manifests/spec-readonly.lock.toml` 的 `sha256` 均**不动** ✗。本批落「组件执行面」后会出现**已知张力**：机器可执行、规范面仍标 `excluded`（`decode: ILLI`）⇒ 收口须用户另行授权立册（`docs/Process-06`）。**本册不得**自行改 `spec/`。
- `lr/sc` 的子宽加载**扩展方式**（零扩展/符号扩展）规范未写明 ⇒ 本册按**零扩展**（与 `ld.ub/ld.uw/ld.ut` 口径一致）并在完成区记录该口径；若后继判需符号扩展 ⇒ 停下报告，不得静默改。
- `fence` 的 `I`/`O`（设备 I/O）在本机无执行面：编码按规范置位，执行语义归 ② 的「无 I/O 前提」。

## 完成区
**测试结果**：证据脚本 `.work/evidence/LLVM-121t/run.sh` 默认档 **15/15 PASS（rc=0）**、`--inject` 档 **21/21 PASS（rc=0，3 处注入全部「预期 FAIL → cp+md5 还原 → 回绿」）**；lit `MC/DADAO`+`CodeGen/DADAO` **115/115**（新增 4 例）、`MC/DADAO-gen` **12/12**；`check_lit_gen` **64/64**；`check-instrinfo` **0 errors**（197 defs）；`gen_isa_coverage --check --llvm-mc 构建树` **PASS**（259 条 / accept 257 / reject 2 / 编码不符 0）；`check-patch-tree` **185 patches OK**；`make check`（L1）在 `check-isa-coverage` 之前全绿（该门控与 `check-builtins-freshness` 红，原因见遗留 2）。
**修改文件**：`components/llvm-project/patches/` 下 10 份（`DADAOInstrInfo.td`/`DADAOInstrFormats.td`/`DADAOCodeGen.td`/`DADAOISelLowering.{h,cpp}`/`DADAOISelDAGToDAG.cpp`/`DADAOTargetMachine.cpp`/`MCTargetDesc/DADAOMCInstPrinter.cpp`/`AsmParser/DADAOAsmParser.cpp`/`clang/lib/Basic/Targets/DADAO.h`；`series` 仍 83）+ `components/llvm-project/changelog.md`；新增 `tests/llvm/lit/MC/DADAO/atomics-lrsc.s`、`atomics-fence-imm.s`、`tests/llvm/lit/CodeGen/DADAO/atomics-{fence,cas}.ll`；重生成 `tests/llvm/lit/MC/DADAO-gen/{gen-orrr,gen-excluded,gen-fast}.s`、`tools/llvm/llvm-isa-backend-matrix.{tsv,md}`；`tools/llvm/{validate_instrinfo,gen_isa_coverage}.py`、`tools/testcases/{generate_lit_vectors,check_lit_gen}.py`；证据 `.work/evidence/LLVM-121t/**`、日志 `.work/log/llvm/LLVM-121t/**`。
**验收结果**：**A1**：24 条 lr/sc 编码逐条 == `ADR-0034 D5` 独立表（`lr.o.nn`=`0x77000241`…`sc.b.ar`=`0x776C8241`），`fence` 合法值 `0/0x043/0x0C2/0x3CF/0x0C3`（符号常量 `PRED_R|PRED_W|SUCC_R|SUCC_W` 折叠为 195），保留编码（`fm≠0`、pred/succ SBZ）与越界均硬报错。**A2**：`__atomic_*` 探针（fetch_add/and/or/xor/sub/nand/exchange/cmpxchg/load/store × 1/2/4/8 B ×5 序 + 指针）`clang -O2 -S` 后 `__atomic_` **0**、`lr.` **40** / `sc.` **40** / `fence` **98**；`llvm-nm -u` 未定义符号 **0**（全部）；`-nostdlib` 静态链接最小 ELF rc=0、全符号表 `__atomic_` **0**、objdump 见 `fence 975`/`lr.t.an`/`sc.t.ar`/`lr.o.an`。**A3**：结构断言覆盖 CAS 环形状（`lr.<w>.an`→`br.ne`→`sc.<w>.ar`→`br.nz`）、成功位 `cmp.so`+`cs.z`、宽度按内存宽度（i8 `lr.b`/i16 `lr.w`/i32 `lr.t`/i64 `lr.o`，含 `CHECK-NOT` 反对更宽访问）、fence 值与插入位置。**A4**：见「测试结果」；`make check`（L1）除两项「待 install-host」外全绿。**不回归**：非原子 codegen 与改前安装根 llc 逐字节相同（`tests/llvm/codegen` 33/33；CodeGen lit 38 例中 38 同、2 例两侧同失败），clang 层 15/15 C 源相同。
**新发现/坑**：① `AtomicExpandPass` 是 **per-target 注册**（generic pipeline 不含），缺 `addIRPasses()` 时原子语义**完全不展开且无诊断**；② 类型合法化与 `Custom` 的交互：`ATOMIC_LOAD/STORE/CMP_SWAP_WITH_SUCCESS` 只能按 **i64** 键设 Custom，按窄类型设会走 `ReplaceNodeResults`（本 target 未实现）⇒ abort；③ 目标 DAG 节点不能用 `getMemIntrinsicNode`（需 SDNPMemOperand + `SelectionDAGGenTargetInfo`），改用普通目标节点 + chain；④ `tools/testcases` 的**两处独立口径**（生成器与 `check_lit_gen`）都把 `scope: excluded` 当「汇编器必须拒绝」，MC 实现后必须同步改分类，否则 `gen-excluded.s` 反例假红；⑤ clang `MaxAtomicInlineWidth=0` 会给出 "max lock-free size (0 bytes)" 误导警告，须与后端 `setMaxAtomicSizeInBitsSupported(64)` 同步；⑥ 注入还原用 `cp -p` 保留旧 mtime ⇒ ninja 判定「无需重建」⇒「回绿」假红（已改 `cp`+md5 对账）。
**遗留问题**：**(1) B1 运行值对照 BLOCKED-by-②**（`QEMU-067t` 的 lr/sc 执行语义）：已给独立 oracle（`probe_oracle.c` + `oracle.py` 手算 20 行 == 宿主 x86-64 运行逐行相同；dadao 侧 rc=0、`__atomic_`=0），运行期望由 ② 端到端 + ④ `TESTCASES-056t` 回填。**(2) 待主会话 `install-host`**：`check-isa-coverage` 在**旧安装根 llvm-mc** 下红（accept 233/reject 26 vs 真源 257/2），`check-builtins-freshness` 红（147 个 builtins 对象旧于新 clang）；`make install-host` 依赖 `build-mc`+`build-builtins`，一并收口（脚本 C11/C13 走构建树）。**(3)** 16 B（i128）原子不支持 ⇒ clang 显式硬报错（不在本册范围）。**(4)** `scope: excluded` 与「规范面 decode ILLI」的张力仍需用户授权另立册（任务书「已知边界」）。**(5)** 子字宽按**原生宽度**（`lr.b/lr.w`）而非任务书 C 节「整字掩码合成」：ADR-0034 D6 经用户 2026-10-21 裁定「甲」后按数据宽度对齐，窄宽度访问**不触碰**同字相邻字节（结构断言以 `CHECK-NOT` 反对更宽访问），故无 `andn`/`or` 掩码；窄宽度 `lr` 按**零扩展**（任务书已登记的待定口径）。**未改 `**状态**`**（按派单）、未 commit/push、未 `install-host`、未跑 L2/L3。

## 审阅记录

#### 第 1 轮 engineer 自审
逐行审查改动（`DADAOInstrInfo.td` 24 defs / `DADAOISelLowering.cpp` 原子四钩子+自定义插入器 / `DADAOISelDAGToDAG.cpp` 两个选择分支 / 解析器 3 处 / 打印器 1 处 / clang TargetInfo），并逐条复核：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `ATOMIC_LOAD/STORE/CAS` 按 i8..i64 全部设 Custom ⇒ 类型合法化走 `ReplaceNodeResults` 崩溃 | ✅已修 | 只按 `MVT::i64` 键设 Custom（窄类型由 `PromoteIntRes_Atomic*` 提升、保留窄 **memory VT**） | 修前 `llc` abort `ReplaceNodeResults not implemented`；修后 9 个原子 IR 全部 rc=0 |
| F2 `cast<AtomicSDNode>` 用于 `ATOMIC_FENCE`（实为普通 `SDNode`） | ✅已修 | 改读 `getOperand(1)` 的 TargetConstant ordering | 修前断言崩溃；修后 fence 立即可 lowering |
| F3 `getMemIntrinsicNode` 用于自定义节点 ⇒ 断言「Opcode is not a memory-accessing opcode」 | ✅已修 | 改 `DAG.getNode` + chain（伪指令已 `mayLoad/mayStore/hasSideEffects`） | CAS IR rc=0，-verify-machineinstrs 通过 |
| F4 `fence` 越界立即数被我自己的前置检查抢先报错，破坏既有 `imm-range.s` 的 `error: immediate out of range` 断言 | ✅已修 | 前置检查只在 `[0,0x3FFFF]` 内查保留位，越界交回 `immu18` 操作数类 | `imm-range.s` 回绿；`fence 262144` 仍 `immediate out of range for 'fence'` |
| F5 `fence PRED_R\|...` 符号常量不可汇编（expression 落到 PC-relative fixup，崩溃） | ✅已修 | 解析器 `Initialize()` 预定义 8 个绝对符号（`MCSymbol::setVariableValue`），表达式在解析期折叠 | `llvm-mc -show-encoding` 得 `0x043/0x0C2/0x3CF`；5 组合法值 C2a 5/5 |
| F6 `lr` 用 `[rb, 0]` 形态与 `contract-asm.md`/spec 的 `[rbHD]` 不一致 | ✅已修 | 地址解析支持 `[rb]` 无偏移形态（推基址寄存器）；打印器按助记符前缀输出 `[rb]` | 与 `.tao/contracts/contract-asm.md:173-174` 的两种书写逐字一致 |
| F7 注入还原失败（`$(backup …)` 在子 shell，全局 BACKUP 丢失） | ✅已修 | `backup()` 只设全局、调用方直接调用；还原用 `cp`（不带 `-p`）+ md5 对账 + 注入前 `tree_clean` 门 | `--inject` 20/20；还原后 `git status` 空、blob == HEAD |
| F8 `check_lit_gen`/生成器对 lr/sc 仍按「反例」分类（与实现矛盾） | ✅已修 | 两处各自维护 `MC_IMPLEMENTED_EXCLUDED`（fence + 24 条 lr/sc，按 ADR D3/D4 派生） | `check_lit_gen` 64/64；`gen-excluded.s` 只余 cfxld/cfxst |
| F9 未见 `fence` 的 `hasSideEffects` ⇒ 屏障可能被删除/CSE（MC-only 时无影响，CodeGen 后必须） | ✅已修 | `def fence` 加 `hasSideEffects = 1` | 结构断言里 `fence` 稳定出现在 load 之后/store 之前 |

自审判定：全部 finding 已修，无未修项。

#### 提交记录（architect，2026-10-21 07:50）
- **档位**：按派单「提交 `LLVM-121t`（一笔）」以**正常提交**（无 `WIP:` 前缀）落册。**披露**：本档为 `待验收`、reviewer 未判定，按 `AGENTS.md` 档位严格口径应为 `WIP:`；本次依主会话派单原话执行，差异留此备查。
- **提交号**：**内容提交 `fdfcff79`**（27 files changed, 1579 insertions(+), 208 deletions(-)）；本注为随后一笔留痕，落地 `master` 时与内容一并 `merge --squash` 成单笔。分支 `LLVM-121t`，**未 push**。
- **文件集对账**（`git diff --cached --name-only` 27 项 vs 完成区「修改文件」）：`patches/**` 10 份 = 声明 10 份 ✓；`changelog.md` ✓；新增 lit 4 例 ✓；重生成 `MC/DADAO-gen/gen-{orrr,excluded,fast}.s` 3 份 ✓；矩阵 `.tsv/.md` 2 份 ✓；工具 4 份（`validate_instrinfo.py`/`gen_isa_coverage.py`/`generate_lit_vectors.py`/`check_lit_gen.py`）✓；本册任务书 ✓。**范围外 2 项**（派单明列）：`.tao/adr/adr-0034-atomics-encoding.md`（Context 第 3 条订正）、`.tao/knowledge/milestones.md`（本册状态句同步）。**漏提 0 / 多提 0**。`.work/evidence|log/**` 不入 git（完成区已声明为证据路径）。
- **门控**：`check-patch-tree` = 185 patches OK（rc=0）；`check-milestones-fresh` PASS（24 行；含 ≤120 字符断言）；`make check`（L1）**EXIT=0**。

#### 第 1 轮 reviewer 验收
（待填）
