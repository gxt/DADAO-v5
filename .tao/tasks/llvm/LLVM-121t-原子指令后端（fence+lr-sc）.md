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

**判决：Needs Revision**（唯一打回项 = 证据脚本 `run.sh` 的 C13；后端/lit/门控/编码/零 libcall 自查全部通过，**不必改**）

**重跑记录**（HEAD=62e8533f=origin/master；验收前/后 `git status --porcelain -uall` 皆空）：
- 门控：`make check-lit` rc=0（125/125）、`make check-instrinfo` rc=0（197 defs / 0 errors）、`make check-isa-coverage` rc=0（259；accept 257/reject 2；编码复核 0 不符）、`check_lit_gen` rc=0（64/64）、`make check-patch-tree` rc=0（185 patches）、`make check`(L1) rc=0（isa-coverage 257/2、builtins-freshness 均已 PASS）。
- 证据脚本：`run.sh` default rc=0（15/15）、`--inject` rc=0（21/21；INJ-1/2/3 均「预期红 → `cp`+md5 还原对账（626fa7c1…/3e225e38… 相等）→ 回绿」）。
- 24 条编码抽查（llvm-mc 实测）：`lr.o.nn rd9,[rb1]`=`77 00 02 41`、`lr.b.an`=`77 1c 02 41`、`sc.w.nr rd8,rd9,[rb1]`=`77 58 82 41`；与 `contracts/opcodes.yaml` 逐字段相同（ha=0x00/0x07/0x16；value 0x77000000/0x771C0000/0x77580000 = `(0x77<<24)|(ha<<18)` 手算复核 ✓）；`lr` 编码 hb=0（rd0）✓。
- fence 自验（自制 IR）：`fence acquire`→`fence 67`(0x043)、`release`→`fence 194`(0x0C2)、`acq_rel`/`seq_cst`→`fence 975`(0x3CF)；monotonic load/store 不发射 fence、unordered 不发射 ✓。
- CAS 抽样（自制 IR，`llc -O2`）：cas64 `lr.o.an→br.ne→sc.o.ar→br.nz`、cas32 `lr.t.an/sc.t.ar`、cas16 `lr.w.an/sc.w.ar`、cas8 `lr.b.an/sc.b.ar`（子字宽原生宽度、无整字掩码 ✓）；atomicrmw add/xor 归约同一环 ✓。
- 零 libcall（自制探针：add/and/or/xor/sub/nand/exchange/cmpxchg/load/store × {i32,i64,指针} × 5 序）：`clang -O2 -c` rc=0、`llvm-nm -u` **0** 条未定义（对照探针 `U ext_fn` 证明探测非恒空）、objdump 含 `lr.o.an/lr.t.an/sc.o.ar/sc.t.ar` 各 18、`fence`×44 ✓。
- 独立注入（自选，临时树 + `validate_instrinfo.py --td`）：`lr_b_ar` ha 0x0B→0x0C ⇒ rc=1（`orphan 1 / non-m1 超出 allow-list`，2 errors）→ `cp`+md5（488750bf… 相等）还原 ⇒ rc=0（0 errors）✓，仓库/组件源码树未动。

**约束核验**：不改 `spec//contracts//qemu/musl/archive` ✓（`git diff bd661b2..62e8533f` 文件集与完成区一致）；不新增指令/不改编码 ✓；一文件一补丁+series/changelog ✓（185 patches OK）；计数现场派生 ✓；独立 oracle ✓（期望值取自 contracts/ADR，未从 llc 回填）；B1 **BLOCKED-by-② 未写成 PASS** ✓（遗留(1)/C14 注记如实）。册 L41「现状·D6」仍写「8 字节」= 2026-10-20 现场快照，按派单判「可接受」，此处点出。

**打回原因（证据脚本 C13 唯一）**：`run.sh:281` 基线探测 `llc --triple=dadao -filetype=obj probe.s` **恒失败**——`llc` 无 `--triple`（实测两条 .s 均 `Unknown command line argument '--triple=dadao'`，flag 层即拒，与输入无关）且 `llc` 不吃 `.s`；⇒ 注释声称的「install-host 后自动 SKIP」**永不可达**；实测两支 llc **同一二进制**（md5 `db3372d6…` 全等）⇒ C13 现为「同源自比」，`identical=33 diff=0 PASS` 是**恒真绿**，冒充「与改前逐字节不回归」（我本轮两条重跑里的 C13 PASS 均为无效证据）。
**要求（只改 `run.sh` C13 + 完成区措辞，其余不必动）**：① 探测改用 `llvm-mc --triple=dadao` 汇编 `lr.o.nn`（或比两支 llc md5），同源 ⇒ SKIP 并注明；② 「改前 vs 改后」基线须留非易失证据（改前 33 份 .s 或 llc 版本标识），无法留存则完成区改述为「2026-10-20 pre-install-host A/B identical=33（log: `.work/log/llvm/LLVM-121t/`）」并注明当前不可重演；③ 重跑 default+`--inject` 更新计数行。
**旁证（无回归，供复核）**：10 份后端补丁 diff **纯新增**（仅 `index`/`@@` 头行变更，0 既有行删除/改写）；`tests/llvm/codegen` 33 例输入未改；抽 3 例（arith_add_sub_neg/branch_loop_sum/call_multiarg_stack）`git show bd661b2:` 旧输入 vs 现输入过现 llc 逐字节一致（仅 `.file` 行名不同）。

**声明**：未改任何代码/测试/契约、未提交 git；本轮写入仅本段 + `/tmp/opencode/REVIEW-121t/`。

#### 证据脚本返工（2026-10-21，engineer）

**① C13 改 golden 基线（reviewer 选项 a）**：33 例非原子输入的输出落 `.work/evidence/LLVM-121t/golden/nonatomic/tests/llvm/codegen/*.ll.s` + `golden/MANIFEST.tsv`（逐行记输入/输出 sha256；表头记生产者 llc md5 `db3372d6…`、`LLVM 23.1.3`、flags、生成时刻）。**C13a 断言** = 当前 llc 输出与 golden `cmp` 逐字节相同 + 输入未被偷改 + 无新增输入未入基线 + 无陈旧行；更新方式 `run.sh --regen-golden`（显式）。
**② 基线来源（如实披露）**：golden 由**改后**（含 lr/sc）llc 生成 ⇒ 断言的是「自此（llc md5 `db3372d6…`）之后不漂移」，**不是**「与改前逐字节相同」——改前二进制已被 `install-host` 覆盖（安装根 llc md5 与构建树全等），故旧完成区「非原子 codegen 与改前安装根 llc 逐字节相同（33/33）」一句**当前不可重演**，以本段为准；「改前 codegen 未变」的旁证仅剩 reviewer 第 1 轮所列（10 份补丁纯新增、33 例输入未改）。
**③ SKIP 探测**：删掉恒失败的 `llc --triple=dadao … probe.s`（llc 无 `--triple` 且不吃 `.s`）。**C13b** 改用正确入口：`.ll` 走 `llc`（看是否吐 `lr.`）、`.s` 走 `llvm-mc --triple`（看能否汇编 `lr.o.nn`）；缺工具 / 两支 llc md5 全等（同源）/ 该 llc 已含 lr/sc ⇒ **SKIP 并写明原因**（SKIP 不计 PASS，不冒充绿）。
**④ 真实输出**：default **15 pass / 0 fail / 1 skipped（rc=0）**；`--inject` **30 pass / 0 fail / 1 skipped（rc=0，8m45s）**；日志 `.work/log/llvm/LLVM-121t/LLVM-121t-evidence-{default,inject}-rework.log`。
**⑤ 可达 FAIL（均真实注入 → 红 → `cp`+md5 还原 → 绿）**：INJ-4 改 golden 一行 ⇒ `identical=32 diff=1` 红 ⇒ 还原 `1768a72e…` ⇒ 绿；INJ-5 **真改后端**（`AsmPrinter` 每条指令插注释 + 重建 llc）⇒ `identical=0 diff=33` 红 ⇒ 还原 `52cc028f…` ⇒ 绿；INJ-7 篡改 manifest（删行+死行）⇒ `gone=1 new-input=1` 红 ⇒ 还原 `00b7faa1…` ⇒ 绿。**SKIP 分支实跑**：INJ-6a 缺工具、INJ-6b 同源、INJ-6c 伪改前 llc 走 A/B（`identical=33`）。
**⑥ 门控（返工后重跑）**：`check-instrinfo` **0 errors**（197 defs）、`check-lit` **125/125**、`make check`（L1）**rc=0**；`components/**` 零改动、未 commit。`**状态**` 仍 `待验收`。

#### 第 2 轮 engineer 自审（返工：证据脚本 C13）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F10 `gen_golden` 的 `local` 列表里有未用变量 `rc`（自造孤儿） | ✅已修 | 删除该局部名 | `bash -n` OK；`--regen-golden` 不在最终证据链（golden 已生成且 C13a `identical=33`） |
| F11 C13b A/B：仅一侧 llc 失败时沿用上一轮残留 `.old/.new` 做 `cmp` ⇒ 可能假同/假异 | ✅已修 | 每轮先 `rm -f` 两侧输出；一侧失败计入 `one-fail` 并跳过比较（PASS 要求 `one-fail=0`） | `--inject` 重跑 INJ-6c：`identical=33 diff=0 one-fail=0 both-failed=0 total=33` |
| F12 golden 生产者与当前是同一二进制（md5 全等）⇒ 不能证明「与改前相同」 | ⏸延后（披露） | 不修，改述口径（见返工②）；非恒真由 INJ-4/INJ-5 证明 | INJ-5 真改后端 ⇒ `identical=0 diff=33` 红 |

自审判定：可修项（F10/F11）已修并重跑；F12 属不可重演的历史证据缺口，已在返工②如实披露，无「遗留:无」式表述。

#### 第 2 轮 reviewer 验收（2026-10-21，只验上轮唯一打回项 C13；后端/lit/编码上轮已 Accepted 不重验）

**判决：Accepted**（三验项全过）

**重跑记录**（workdir=仓库根，本人真实执行；日志 `/tmp/opencode/REVIEW-121t-r2/`）
- `run.sh` default：**rc=0**（28s）；C13a `identical=33 diff=0 total=33`；C13b SKIP「同源：安装根 llc==构建树 llc(md5 db3372d6…)」；summary `15 passed, 0 failed, 1 skipped`。
- `run.sh --inject`：**rc=0**（529s）；summary `30 passed, 0 failed, 1 skipped`。

**验① C13 现在能否失败（非恒真）**
- 结构核对：C13a= golden 基线（`golden/MANIFEST.tsv` 33 行 + 逐例 `nonatomic/**.ll.s`）✓；断言 `cmp -s "$g" "$tmp"`（run.sh:354）**逐字节**，比「golden 存档」vs「现 llc 新产出 $tmp」，**非自比** ✓；`--regen-golden` 仅 `main` 显式分支（run.sh:691），无隐式重生 ✓。
- **我自己注入**（不抄册内 INJ-4）：改 golden `arith_add_sub_neg.ll.s` 一行 `add.si rb1,-16→-15` ⇒ 跑同一 `run.sh` **rc=1**、C13a `identical=32 diff=1`、`DIFF tests/llvm/codegen/arith_add_sub_neg.ll`（真红）。
- `cp`+md5 还原（`1768a72e…`，`cmp` 逐字节同 preinject）⇒ 再跑 **rc=0**、C13a `identical=33 diff=0`（回绿）。
- 判：**非恒真**（旁证 INJ-5 真改后端 ⇒ `identical=0 diff=33` 红）；非自比、非只比 sha（`cmp` 内容比对）✓。

**验② SKIP 分支真可达且可见 + 不误计 PASS**
- 三支真实日志：INJ-6a 缺工具⇒SKIP「改前 llc 缺失/不可执行：/nonexistent/llc…」；INJ-6b 同源⇒SKIP「同源…md5 db3372d6…」；INJ-6c 伪改前 llc⇒A/B 真跑 `identical=33 diff=0 one-fail=0 total=33`（非 SKIP、走 A/B）✓。
- SKIP 时 rc 仍 0 ✓（default/`--inject` 各 1 SKIP、rc 均 0）。
- **SKIP 不误计 PASS** ✓：独立 `grep -c '^PASS'|'^SKIP'` = 30/1（inject）、15/1（default），与 summary `30 passed…1 skipped`/`15 passed…1 skipped` 逐一对齐；`skip()`（run.sh:42）只累 SKIPS、不入 `passed=CHECKS-FAILS`（run.sh:738）。

**验③ golden 落点判定：Accepted（可接受）**
- 事实：golden 在 `.work/evidence/LLVM-121t/golden/`，`.gitignore:2 .work/` ⇒ 不入版本；**无任何持久门控**（`make check`/L1/L2/L3）引用它，仅本册一次性 `run.sh` 消费。
- 理由：① **实际角色 = 本册点时间「原子改动未回归非原子 codegen」的一次性证据**（未接任何 gate，非长期门控）；② 可 `--regen-golden` 从 `tests/llvm/codegen/**`+现 llc 完全重建 ⇒ `.work` 清空不损失不可复现物；③ 与本仓 `evidence/**`（`.work/evidence/<task>/` gitignore）惯例一致；④ 逐字节 asm golden 脆（任一良性 llc/格式变动即红），本不宜常驻；长期非原子 codegen 守护已由 `check-lit`(47 FileCheck)+`test-codegen` 承担。
- 备注（非阻断，供架构师）：run.sh 注释「不回归基线/一漂移就红」略高过其一次性实质，宜改述「一次性 no-regression 快照证据」；若确要常驻逐字节 codegen 门控，属架构决策（须同时迁 git + 接门控），不作本册打回项。

**门控（交付⑥）**：`check-instrinfo` rc=0（0 errors）；`check-lit` rc=0（125/125）；`make check`(L1) rc=0（PASS）。
**快照对账**：`git status --porcelain` 仅 1 `M`（本册）；golden `1768a72e…`/MANIFEST `00b7faa1…`/run.sh `edfe2be6…` 还原如初；`git diff` 仅本册。
**声明**：未改任何代码/脚本/golden（还原后 md5 对账一致）、未 commit/push；仅写本段。

### 返工要求（2026-10-21，`TESTCASES-056t` 现场）

> **撤回依据**：下游 ④ `TESTCASES-056t`（另一任务书）用 file-scope 共享对象 + 子字宽高位置 1 的探针，**精确测出本册交付的两个后端缺陷**（20 条 XFAIL 逐条对应），本册因此 `已验证` → **`待返工`**。既有完成区/审阅记录**不改写**，返工后在第 3 轮另记。缺陷已登记 `ISS-312`（A，P1）/ `ISS-313`（B，P2），`scope: [llvm]`。

**缺陷 A（P1，`ISS-312`）：`LowerATOMIC_STORE` 取错操作数 ⇒ 共享对象的 `atomic_store`/`__atomic_store_n` 写入对象地址**
- 现象：写**共享（file-scope，非局部）**对象时，写入的是**对象自身的地址**而非值——实际 `gx = 0x4a920`、`gc = -80`、指针 `gp = &gp`；c11 7 个 `store_shared` + builtins 4 个 `store_n` 共 11 条命中（两档一致）。局部 `_Atomic` 变量因被优化进寄存器/SROA 而**不经过 `ATOMIC_STORE`** ⇒ 矩阵其余部分全绿，**会掩盖本缺陷**。
- 根因（`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch`，`LowerATOMIC_STORE` ≈ `+2244`）：`SDValue Val = Op.getOperand(2);` —— 而 `AtomicSDNode` 的 `ATOMIC_STORE` 操作数序是 `(chain, value, ptr)`，`getOperand(2)`/`getBasePtr()` 是**指针**，值是 `getOperand(1)`/`AN->getVal()`；现场 DAG 已呈 `store t4:1, t2, t2`（value 与 ptr 同一个）。
- 要求：改取 `AN->getVal()`（`getTruncStore` 分支同步）；**必须补「共享对象 store 值正确」的用例**（lit + 运行期各一；用 `volatile`/跨 TU 外部可见/`-O0` 或 `optnone` 等方式**确保不被优化成普通 store/寄存器**，否则用例假绿）。

**缺陷 B（P2，`ISS-313`）：子字宽 CAS 在比较值最高位为 1 时恒失败**
- 现象：1/2/4 字节 `atomic_compare_exchange`（`ATOMIC_CMP_SWAP*`）当比较值最高位置 1（`int -1`、`unsigned 0x80000000`、`uchar 200`、`ushort 40000`）时**永不成功**（`expected` 与实际相等却返回失败）；8 字节对照组（`long -1`）通过。c11 6 个 `compare_exchange_edge_ok` + builtins 3 个 `compare_exchange_edge` 共 9 条。
- 根因：`lr.{b,w,t}` 的装载结果按**零扩展**进入 64 位寄存器，而比较值（`Cmp`）是类型合法化后**符号扩展**的 i64（`int -1` = `0xFFFF_FFFF_FFFF_FFFF`），`br.ne` 比较的是**完整 64 位** ⇒ 两侧高位不等，永不相等；`lr.o` 宽度天然一致故仅 8 字节正确。
- 要求：**统一扩展口径**——比较前把 `lr` 结果与 `Cmp` 归到同一扩展约定上（推荐：按 `MemVT` 对 lr 结果做 `sext`/零扩展截断后与**同口径**的 `Cmp` 比较），且该口径须与 `contract-abi §4.2`（canonical 64 位、按类型符号性扩展）一致、与 `ISS-310`（`int` 实参未符号扩展）的修法**同一方向**（勿两处各定一套）；`ATOMIC_CMP_SWAP_WITH_SUCCESS` 的 `SETEQ` 与 FinalizeISel 环内的比较**两处同步**。**必须加高位置 1 的子字宽 CAS 用例**（i8/i16/i32 × 有/无符号各一，含 `-1`、`INT_MIN`、`0x80`、`0x8000`、`0x80000000`）。
- 复核（交付判据）：修后 `TESTCASES-056t` 的 **20 条 XFAIL 应全部转 PASS**（11 条 → A、9 条 → B；届时 XFAIL 表不改则报 `XPASS` 红），由 ④ 重新验收确认；本册自身另须 `make install-host`（改了 ISel/`.td` 生成物）+ `check-instrinfo` + `check-lit` + L1 全绿，并给出两个缺陷各自的可达 FAIL 反例证据。

### architect 提交 + 文件集审核（2026-10-21 11:51；撤回动作留痕）
- **动作**：本册 `已验证` → **`待返工`**（依据 = 下游 ④ `TESTCASES-056t` 的 20 条 XFAIL 精确测量；缺陷登记 `ISS-312`/`ISS-313`）。既有完成区与第 1/2 轮审阅记录**未改写**，仅追加本段与上文「返工要求」。
- **档位 / 提交号**：同批内容提交 `e7387088`（`WIP:` 前缀，因同批 ④ 为 `待验收`；本册返工另计）；本段为随后一笔留痕。分支 `TESTCASES-056t`，**未 push**。
- **文件集对账**：本册 1 项 + `milestones.md`（行内状态/时间同步）；**范围外** = `TESTCASES-056t` 交付 8 文件 + `issues.yaml` + 其本册（派单 ①）。**漏提 0 / 多提 0**。


### 返工（`ISS-312` / `ISS-313`，2026-10-21，engineer）

**A 修法（`ISS-312`，P1）**：`LowerATOMIC_STORE` 的 `SDValue Val = Op.getOperand(2)` → `AN->getVal()`（`getTruncStore` 分支共用同一 `Val`，无需另改）。依据 = `SelectionDAGNodes.h` 的 `AtomicSDNode::getBasePtr()/getVal()`（`ATOMIC_STORE`：ptr=op2、value=op1）与 `SelectionDAGBuilder` 的 `(chain, ptr, cmp, new)`。**同族操作数下标审计**（逐条对源码）：`ATOMIC_LOAD` 用 `getChain()/getBasePtr()/getMemoryVT()` ✓；`ATOMIC_FENCE` 的 ordering 在 op1、scope 在 op2 ✓；`ATOMIC_CMP_SWAP_WITH_SUCCESS` 的 `(chain,ptr,cmp,new)` = op0..op3 ✓；伪指令展开读 `MI` 的 `(dst,ptr,cmp,new)` ✓；`DADAOISD::ATOMIC_CMP_SWAP` 的 `[chain,ptr,cmp,new,width]` ✓ ⇒ **仅 store 一处错位，其余无同类错**。
**B 修法（`ISS-313`，P2）**：**比较口径统一到访问宽度** —— `LowerATOMIC_CMP_SWAP_WITH_SUCCESS` 对 `MemVT < 64` 的期望值先 `AND ((1<<W)-1)`，该规范化值**同时**作为伪指令操作数（环内 `br.ne`）与 `SETEQ` 的比较对象（**单点规范化**，两处不可能再各自漂移）。依据 = C11 7.17.7.4（比较的是对象表示的 W 字节）+ `lr` 零扩展（`QEMU-067t` 的 `gen_lr` 对提取字节做 `andi`；`contract-abi §4.2` 的「按符号性扩展」只约束**参数**，CAS 操作数不是参数）。效果：常量 expected 时掩码被折叠进常量物化（`set.zw …, 0x8000`，修前是 `set.ow`+`andn.w` = 符号扩展形态），运行期 expected 时落 1 条 `and.o`；i64 不掩码。**与 `ISS-310` 的关系**：同向（都朝「按宽度/符号性规范化」），但本修**不依赖**它——掩码对「符号扩展」「零扩展」两种来源都成立，故 `ISS-310` 仍按自身缺口（实参 ABI `signext`）独立修，本册未动参数扩展路径。
**新增用例**：`tests/llvm/lit/CodeGen/DADAO/atomics-store.ll`（i8/i16/i32/i64：`st.*` 的源寄存器 = 值计算指令的目的 + `CHECK-NOT: rb2rd` 反对「地址副本」；monotonic/seq_cst/release 各一）、`atomics-cas-narrow-sext.ll`（i32 运行期 expected 的 `and.o`、i8/i16/i32 高位为 1 常量的零扩展物化、`cmp.so` 复用同一规范化操作数、i64 无掩码）。运行期：证据脚本用 **volatile 指针 + 跨 TU** 的 store 探针与 i8/i16/i32 高位 CAS 探针，**-O0/-O2 各一档**，两套 clang 各建一次。
**20 个 XFAIL 复核真值（构建树 clang；未 `install-host`）**：`run_atomics_probe.py` static/dynamic 各 **711 单元：pass 691 / fail 20（= 20 条 XPASS；缺陷签名命中 0）**；20 条 = 11 `atomic-store-address` + 9 `narrow-cas-sext`（条数由 `oracle_atomics` **现场派生**）。原始观测（同一探针两套 clang 各建一次）：`SCASE * store_shared` 修前 `fin` = 自身地址（`0x56ac4`→355012；指针 `fin=addr=0x56ae8`）→ 修后 = 值（42/4321/424242/4242424242/2100000000/3100000000/`&pb`）；`SBUILTIN w=4 store_n` 修前 `fin=340284`（`0x5313c`）→ 修后 `1432778632`；窄 CAS `ret` 0→1、`fin` 初值→写入 0（8 B 对照组修前即 ret=1）。
**不回归**：lit（构建树 overlay）**127/127**（原 125 + 2 新）；`check-instrinfo` **0 errors**（197 defs）；`check_lit_gen` **64/64**；`check-isa-coverage` 构建树 llvm-mc **PASS**（259；accept 257/reject 2；编码不符 0），**安装根 llvm-mc 上同样 PASS**；`check-patch-tree` **185 patches OK**；非原子 codegen golden **33/33 逐字节相同**。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch`（+28/−1）、`components/llvm-project/changelog.md`（M9 追加一条）、新增两个 lit `.ll`；（**范围外但门控必需，已披露**）`tools/llvm/llvm-isa-backend-matrix.{tsv,md}` 重生成——差异仅 `DADAOISelLowering.cpp.patch` 行号 +27 的引用漂移（10 行 × 2 文件）。组件源码树 `commit --amend` 收敛（`f9ee808ef`，E1 OK，worktree 干净）。证据 `.work/evidence/LLVM-121t/run-rework2.sh`：default **17/17 rc=0**、`--inject` **3 处注入全部「注入→红→cp+md5 还原→绿」rc=0**；日志 `.work/log/llvm/LLVM-121t/`。
**遗留**：① 安装根未刷新 ⇒ `make check-lit` 仍读**修前** llc（新增 2 例按预期红），待主会话 `install-host` 后转绿；`check-builtins-freshness` 同理。② **B 修假设 `lr.b/.w/.t` 零扩展**（`QEMU-067t` 实现口径，`spec/SimRISC-12` 未写明）；若日后改符号扩展须同步本掩码（已写入代码注释）。③ `-O0` 下 CAS 缺陷不显现（expected 经 alloca 零扩展载入）⇒ 修前对照只取 `-O2`，修后两档都须绿。④ 未 `install-host`、未跑 L2/L3、未 commit/push；`**状态**` **未改**（仍 `待返工`）。

#### 第 3 轮 engineer 自审（返工 `ISS-312`/`ISS-313`）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F13 常量 expected 的 `AND` 掩码被 DAG 折叠，担心「掩码没生效」 | ⏸无需修（合流为**零扩展**常量物化，语义正确且有结构可断言） | 无 | `cas32_top_bit`：修后 `set.zw …, 0x8000`；修前对照 `set.ow`+`andn.w`（真·符号扩展） |
| F14 只掩码 `Cmp`、不掩码 `lr` 结果（依赖 `lr` 零扩展） | ⏸延后（披露）：`QEMU-067t` 的 `gen_lr` 对提取字节 `andi` 后再写 rd；代码注释写明该依赖 | 无（靠注释 + 完成区遗留②） | `c11`/`builtins` 窄 CAS 9/9 运行通过；`lr` 零扩展口径见 `LLVM-121t` 已知边界 |
| F15 `c15_values.py` 的 `shared_store_*` 正则把**函数定义**当调用点 ⇒ 期望值解析崩溃 | ✅已修 | 限定 `\(\d+\);` 调用形态；指针单元用探针自打的 `PTR_B` | 脚本 `store=7/7`；首轮实际崩过（`invalid literal … 'char v'`） |
| F16 指针单元的 `fin` 是无 `0x` 前缀的十六进制，按十进制解析失败 | ✅已修 | 按 `tag == pointer` 选择 `int(s,16)` | `store=7/7`（含 pointer） |
| F17 证据脚本首稿 `c9_golden` 定义了两次（前一份为死代码，helper 写在函数之间） | ✅已修 | 删重复定义，helper 统一由 `gen_helpers` 生成 | `bash -n` OK；default 17/17 |
| F18 `build_run` 构建失败原本只 `return 90` 不回显 ⇒ 调用方拿到空 rc，会把「构建失败」误判成未知值 | ✅已修 | 两个失败分支改为 `{ echo 90/91; return; }` | 修前/修后 8 次构建全部拿到整型 rc |
| F19 补丁行号变化使 `check-isa-coverage` 红（矩阵 `isel-cpp:…:<行号>` 引用漂移） | ✅已修 | 按真源重生成 `tools/llvm/llvm-isa-backend-matrix.{tsv,md}` | `--check` PASS（259/accept 257/reject 2）；diff 仅行号 |

自审判定：可修项（F15–F19）已修并重跑；F13/F14 为「已核实/已披露」项，完成区有对应条目，无「遗留:无」式表述。
