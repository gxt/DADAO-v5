# QEMU-067t: 原子指令语义（`fence` + `lr/sc` 24 条：保留标记 / 宿主 CAS / MALIGN / ILLI）

**模块**：qemu
**项目里程碑**：M9
**依赖**：`LLVM-121t`（①；安装根 `clang`/`llvm-mc` 须已能产出 `lr/sc`/`fence` 编码 —— 本册端到端要用）、`ADR-0034`（`Accepted`：编码/命名/语义定案）、`QEMU-064t`（上一轮解码/`trans_*` 迁移先例，`已验证`）、`QEMU-065t`/`QEMU-066t`（qemu-user 线程语义先例）、`ISS-307`（本批 4 册总账）
**状态**：待开始

## 执行环境
**执行环境**：本地

> **编号（现场取号，2026-10-21）**：`qemu` 模块现有最大 = `QEMU-066t` ⇒ 取 **`067`**；`find .tao -name 'QEMU-067*'` = 0 命中。
> **本批位置**：串行链 **① `LLVM-121t` → ② 本册 → ③ `INFRA-100t` → ④ `TESTCASES-056t`**；四册同改共享安装根，**禁止并行**。
> **本批边界**：**不改** `spec/` / `contracts/**` / `.tao/contracts/**` / `components/llvm-project/**` / `components/musl/**`；`scope: excluded` 的 re-scope **不在本批**（见「已知边界」）。

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 语义真源（`spec/SimRISC-12 §3`，`ADR-0034 D6`）

- **`fence`**：`oiii`，`op = 0x77`、`ha = 0x20`；`immu18` 三段 `fm[17:12]` / `pred[11:6]` / `succ[5:0]`；`fm = 0` 唯一已定义（`fm = 8` = 「TSO 预留、当前未定义」）；`pred[11:10]`、`succ[5:4]` 为 SBZ；`fm ≠ 0` 或 SBZ 非零 ⇒ **ILLI**。`pred`/`succ` 的位 = R(`1<<6`/`1<<0`)、W(`1<<7`/`1<<1`)、I(`1<<8`/`1<<2`)、O(`1<<9`/`1<<3`)；`pred = succ = 0` ⇒ **no-op**（不产生任何顺序效果）。语义 = 对 `pred` 类访问与 `succ` 类访问之间的串行化。
- **`lr`**：读内存到 `rdHC` 并**设置本 hart 的保留标记**；`hb`（`rdHB`）**恒为 `rd0`**，手工编码 `hb ≠ 0` ⇒ **ILLI**；地址在 `rbHD`。
- **`sc`**：保留标记仍在**且地址匹配** ⇒ 写入 `rdHC` 并置 `rdHB = 0`；否则不写、置 `rdHB = 1`；**无论成败都清本 hart 全部保留标记**；地址须 **8 字节自然对齐**，否则 **MALIGN**。允许偶发失败（spurious failure）⇒ 软件重试。
- 保留粒度**由平台定义**（精确地址或 cache line 均可）——本册取**精确 8 B**（见「设计要点 B」）。

### 现场事实（2026-10-21 核，执行前须复核）

1. **解码面已就绪**：`components/qemu/patches/target/dadao/insn.decode.patch` = **259 pattern**（`# 259 patterns`，生成自 `contracts/opcodes.yaml`）；字段 `%hb 12:6 / %hc 6:6 / %hd 0:6`，`&misc hb hc hd`（:11-13）；`fence_oiii_imm`（:113）与 24 条 `lr/sc`（:115 起）均已入 `@misc`。⇒ **本册不改 `insn.decode`**（除非现场复核发现漂移，届时按 `tools/qemu/generate_decodetree.py` 重生成）。
2. **执行面全是 ILLI 桩**：`insn_trans/trans_mem.c.inc.patch:481` 起 **24 个** `trans_{lr,sc}_*_orrr_rd`，函数体一律 `/* <id> - stub: ILLI */ gen_exception_illegal(ctx); return true;`；`trans_ctrl.c.inc.patch:504-509` 的 `trans_fence_oiii_imm` 同为 ILLI 桩（`/* fence - stub: ILLI (M1 fence semantics not implemented) */`）。⇒ **本册就是把这 25 个函数体换成真语义**。
3. **寄存器/地址访问惯例**（`translate.c.patch`）：`load_rd(n)`/`store_rd(n, v)`（:90/:105，`rd0` 读 0、写忽略）、`load_rb`/`store_rb`、`gen_ea_rrii(...)`；env = `CPUDADAOState`（`cpu.h.patch:185-187`：`uint64_t rd[64]; uint64_t rb[64];`）。`@misc` 参数经 `arg_misc` 给出 `a->hb`/`a->hc`/`a->hd`：对 `fence` 分别是 `fm`/`pred`/`succ`，对 `lr/sc` 分别是 `rdHB`/`rdHC`/`rbHD`。
4. **MALIGN 通道已在**：`dadao_cpu_do_unaligned_access` 置 `DADAO_EXCP_MALIGN`（`cpu.c.patch:384-392`；枚举 `DADAO_EXCP_MALIGN = 5`，`cpu.h.patch:50`），由访存的 `MO_ALIGN_*` 触发（先例：`trans_mem` 的 `ld.o`/`st.o` 用 `MO_BEUQ｜MO_ALIGN_8`，:111）；user-mode 退出码 `DADAO_EXIT_MALIGN = 0x8C`（`cpu.h.patch:73`），向量侧 `tests/scripts/run_qemu_test.py:59` 已把它映射成 `MALIGN`。运行期条件异常先例：`gen_raise_exception_illi`（`translate.c.patch:71-76`，`gen_helper_raise_exception(tcg_env, tcg_constant_i32(DADAO_EXCP_ILLI))`）。
5. **宿主原子原语可用**：`tcg_gen_atomic_cmpxchg_i64(TCGv_i64 ret, TCGv addr, TCGv_i64 cmp, TCGv_i64 new, TCGArg memidx, MemOp memop)`（声明 `include/tcg/tcg-op-common.h:344`，实装 `tcg/tcg-op-ldst.c:1002`）；LL/SC 的**标准模型先例** = Alpha `gen_store_conditional`（`target/alpha/translate.c:403-435`：per-cpu `lock_addr`/`lock_value` + `tcg_gen_atomic_cmpxchg_i64` + `setcond`）；`tcg_gen_mb(TCGBar)`（`tcg/tcg-op.c:289`）用于屏障，先例 `target/s390x/tcg/translate.c:1486`（`TCG_MO_ALL ｜ TCG_BAR_SC`）。
6. **门控载体**：`make check-qemu-semantics`（L3）的载体是 `Makefile:1054-1065` 里**硬编码的 4 个向量文件** ⇒ 新增向量须**加一行**（现场派生计数，不写死）；L2 `check-qemu-smoke` 由 `tests/scripts/run_qemu_smoke.py --vector-dir tests/vectors/isa` **机械派生代表集** ⇒ 新向量文件自动纳入 L2（预期用例数上升，属预期）。
7. **向量 harness 能力与缺口**（`tests/scripts/run_qemu_test.py` + `build_test_binary.py`）：
   - 单用例 = `[prologue 装载 input_state] + [**一个** 原始编码字] + [epilogue 比对 expected_state]`（`build_test_binary.py:329-332` 只取 `encoding.word`，返回 `[instr_word]`）；
   - 支持 `input_state.{rd,rb,ra,memory}`、`expected_state.{rd,rb,ra,memory}`、`expected_fault`（`tests/vectors/isa/mem-rd.yaml:60-78` 为 memory 用法先例）；
   - **缺口**：`sc` 的成功路径需要**前一条 `lr`** ⇒ 现harness 无法表达；`sc`/`lr` 的 memory 比对宽度需 `derive_width_from_mnemonic` 认识 `lr/sc` 的 `.o/.t/.w/.b`。

### 与 ③/④ 的分工

本册只做 **qemu 执行面 + ISA 语义向量 + 一条端到端**；musl 侧（`a_cas`/`a_cas_p`/`a_barrier`）归 ③，C11/`__atomic_*`/ABA 家族验收归 ④。

## ✅ 已裁定（2026-10-21，用户「甲」）

**裁定原话**：「甲」= **按数据宽度对齐**：`.b`=1 / `.w`=2 / `.t`=4 / `.o`=8 字节自然对齐；不满足 ⇒ **MALIGN**。

> **标签对照（勿混）**：用户裁定编号「甲」= 按数据宽度对齐（即本册旧文「乙」项）；旧文「甲」（全族 8 B）作废。`ADR-0034 D6` 已就地修订、`spec/SimRISC-12 §3.2` 已订正（编码/lowering 不变）。

**对向量与实现的具体影响**：

- **MALIGN 期望 = 按宽度**：`.o` 非 8 B 对齐（`addr & 7 ≠ 0`）才 MALIGN；`.t` 非 4 B 对齐（`addr & 3 ≠ 0`）才 MALIGN —— `addr & 7 == 4` 的 `.t` **合法**；`.w`/`.b` 同理（2 B / 1 B）。
- `k = addr & 7` 的取值范围随之打开：`.t` ∈ {0,4}、`.w` ∈ {0,2,4,6}、`.b` ∈ 0..7、`.o` 恒 0 ⇒ 抽取/合并移位按 `k` 与宽度算，**不得写死 `k = 0`**。
- ③ 的 `a_cas`（`.t`）可在 4 B 对齐对象上工作；`a_cas_p`（`.o`）仍 8 B。保留粒度仍精确 8 B（不改）。

## 目标

1. `fence`：按 `fm`/`pred`/`succ` 实现顺序语义（`pred = succ = 0` ⇒ no-op；`fm ≠ 0`、SBZ 非零 ⇒ ILLI）；qemu-user 下落 TCG 级屏障。
2. `lr`：读 + 记保留（per-guest-thread）；`hb ≠ 0` ⇒ ILLI。
3. `sc`：**宿主 CAS 实现真原子**（跨线程正确）；成功 `rdHB = 0`、失败 `1`；**无论成败清本 hart 保留**；对齐口径见「已裁定（按数据宽度）」，不满足 ⇒ MALIGN。
4. **粒度与限制写清**（精确 8 B；非一致/设备内存不适用）。
5. **L3 语义向量**（独立 oracle = Python 按语义手算）+ `fence` 各 ordering。
6. **端到端**：安装根 clang 编 `lr/sc` CAS 循环 + 2 线程并发计数 ⇒ `qemu-dadao` 跑通且计数精确。
7. L1/L2/L3 门控全绿（`check-qemu-smoke` 用例数上升、`check-qemu-semantics` 载体 +1）。

## 接口规范

**输入**（只读）：
- `ADR-0034`（`D1`–`D7`）+ `spec/SimRISC-12 §3.1/§3.2`（语义正文）、`contracts/opcodes.yaml`（259 条，`lr/sc` 的 `ha`/`fields` 与编码）。
- 现有补丁树 `components/qemu/patches/target/dadao/**`；`.work/source/qemu/**`（**只读参照**，交付只走 `patches/**`）。
- 向量 schema 先例 `tests/vectors/isa/mem-rd.yaml`、运行器 `tests/scripts/run_qemu_test.py`（`build_binary`/`interpret_exit_code`）、二进制构造 `tests/scripts/build_test_binary.py`。

**输出**（交付物）：
1. `components/qemu/patches/target/dadao/insn_trans/trans_mem.c.inc.patch`：24 个 `lr/sc` 桩 → 真语义。
2. `components/qemu/patches/target/dadao/insn_trans/trans_ctrl.c.inc.patch`：`trans_fence_oiii_imm` → 真语义。
3. `components/qemu/patches/target/dadao/cpu.h.patch`：保留标记字段（per-hart：`lock_addr` / `lock_val` / `lock_valid` 或等价）。
4. `components/qemu/patches/target/dadao/translate.c.patch`：需要时的 helper（如 `gen_raise_exception_malign`）与共用地址/掩码小工具。
5. `tests/vectors/isa/atomics-lrsc.yaml` + `tests/vectors/isa/atomics-fence.yaml`（**独立 oracle** 生成器：`tools/testcases/generate_atomics_vectors.py` 或等价；计数现场派生）。
6. `Makefile`：`check-qemu-semantics` 载体 **+2 行**（两个新向量文件；不写死计数）。
7. `tests/scripts/build_test_binary.py` + `tests/scripts/run_qemu_test.py`：**仅新增** `sequence:` 可选项与 `lr/sc` 的宽度映射（默认单字路径**不变**；见「已知边界」的替代方案）。
8. `components/qemu/changelog.md`（`## M9` 节）+ `series` 同步；`.work/evidence/QEMU-067t/**`（含 `run.sh` 与 `--inject`）+ `.work/log/qemu/QEMU-067t/**`；本册完成区。

**约束**：
- **不改** `insn.decode` 的 259 pattern（现场复核无漂移即不动）；**不改** `spec/`/`contracts/**`/`components/llvm-project/**`/`components/musl/**`。
- 补丁**一文件一补丁** + `series` + `changelog`；`check-patch-tree` 断言；**改 qemu 后必须 `make install-host`**（`ISS-210`：否则门控读旧安装根 ⇒ 假绿）。
- **向量必须独立 oracle**：期望值 = Python 按 `SimRISC-12 §3` 手算（含掩码/字节序），**不得**从 `qemu` 运行结果回填；**不得**以「抬超时/放宽断言/删用例」当通过。
- 别把「宿主 CAS 的语义」写成「规范语义」：规范允许更粗粒度，但**不允许更细**；实现取舍必须写进完成区。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. `fence`

```
if (a->hb != 0)                              -> ILLI   /* fm ≠ 0（含 fm=8 TSO 预留） */
if ((a->hc & 0x30) || (a->hd & 0x30))        -> ILLI   /* pred[11:10] / succ[5:4] SBZ 非零 */
if (a->hc == 0 && a->hd == 0)                -> no-op  /* 不发屏障 */
else  tcg_gen_mb(<按 pred/succ 派生> ｜ TCG_BAR_SC)
```

- `pred`/`succ` → `TCG_MO_*` 的映射：`R` ⇒ 读类（`TCG_MO_LD_LD`/`TCG_MO_ST_LD` 的读侧）、`W` ⇒ 写类（`TCG_MO_LD_ST`/`TCG_MO_ST_ST` 的写侧）、`I`/`O` ⇒ 本机无 I/O 语义 ⇒ 按 `TCG_MO_ALL` 处理（**只能更强，不得更弱**）。允许的最简实现 = 任一非零 ⇒ `TCG_MO_ALL ｜ TCG_BAR_SC`（语义上强于规范，安全），但**必须**在完成区声明所用映射，并让向量断言 `pred = succ = 0` 真的不发屏障。
- `TCG_BAR_SC` 的顺序强度：qemu-user 下多 guest 线程 = 多宿主线程 ⇒ 屏障必须跨宿主线程可见（`TCG_MO_ALL ｜ TCG_BAR_SC` 即为此；不得只在单 vCPU 内自洽就宣称实现完成）。

### B. `lr` / `sc`：per-hart 保留 + 宿主 CAS

- **保留状态**（`CPUDADAOState` 新增，per guest thread）：`lock_addr`（**8 B 对齐后的地址**）、`lock_val`（`lr` 时观测到的**整 8 B 字值**）、`lock_valid`。
- **`lr`**：`hb ≠ 0` ⇒ ILLI；`addr = rb[hd]`；**对齐判定按「已裁定」口径 = 按数据宽度**（`addr & (W-1) == 0`，`W` = 1/2/4/8）⇒ 不满足 ⇒ MALIGN（仿 `gen_raise_exception_illi` 加 `gen_raise_exception_malign`，**不经**猜测的 `MO_ALIGN_*` 副作用）；读**包含该地址的 8 B 字**（`word_addr = addr & ~7`，`MO_BEUQ｜MO_ALIGN_8`，对齐由构造保证）；按 `k = addr & 7` 与宽度 `W` 抽取，大端移位 `shift = (8 - k - W) * 8`（`.o` ⇒ `k = 0`、整字；窄宽度按 `k` 取窗，见已裁定节）；`store_rd(a->hc, value)`；写 `lock_addr = word_addr`、`lock_val = word`、`lock_valid = 1`。
- **`sc`**：`addr = rb[hd]`；**先做对齐判定**（同 `lr` 的已裁定口径 = 按宽度；失败路径也必须 MALIGN ⇒ 显式 `gen_raise_exception_malign`，不得「不访存就不检查」）；`new = merge(lock_val, rdHC 值, 宽度, k)`；`ret = tcg_gen_atomic_cmpxchg_i64(word_addr, expected = lock_val, new, MO_BEUQ)`；`ret == lock_val` ⇒ 成功（`rdHB = 0`）否则失败（`rdHB = 1`）；**两条路径都清 `lock_valid`**。
- **大端掩码公式**（字节偏移 `k = addr & 7`、宽度 `W` 字节）：`shift = (8 - k - W) * 8`、`mask = (1 << (8W)) - 1`、`new = (old & ~(mask << shift)) ｜ ((val & mask) << shift)`。**`sc.o` 的 `k` 恒 0**。
- **保留失败判定 = 整 8 B 字值比对**：任何 hart 对这 8 B 字的写入（任意宽度）只要改了值 ⇒ CAS 失败 ⇒ `sc` 失败（比「cache line 写」更严），**规范允许**（spurious failure 合法）。⇒ 完成区须写明两条**限制**：① 另一 hart 写入**相同值**时本实现检不出（ABA）；② 粒度 = 精确 8 B（非 cache line）。
- **异常/信号进入时清保留**：规范要求。user-mode 下可在 `dadao_cpu_do_interrupt`/信号投递路径清 `lock_valid`（成本可控时做）；**做不到**则必须在完成区写明限制，并把对应向量排除（**不得**静默算过）。

### C. 向量（**24 条 × 各自的语义面**；计数现场派生）

- **`lr`（12 条）**：① 语义：不同宽度从 8 B 字正确抽取（大端 + `k = addr & 7`）+ 置保留（后续 `sc` 同址成功可证）；② MALIGN：低于**该宽度**对齐的地址（`.o` 非 8 B、`.t` 非 4 B 对齐才 MALIGN，`.t` 的 `addr & 7 == 4` 须为**合法**用例）；③ ILLI：手工编码 `hb ≠ 0`（每宽度 1 条即可，仍按 12 条派生）。
- **`sc`（12 条）**：① 成功（**前接同址 `lr`**，写出 = 期望值，`rdHB = 0`，内存按宽度/字节偏移**只改目标字节**、相邻字节不变）；② 失败（无保留 / 地址不匹配 ⇒ 不写内存、`rdHB = 1`、且保留被清：**用「失败后再 `sc` 一次同址仍失败」证清保留**）；③ MALIGN（失败路径下也不得跳过对齐判定）。
- **`fence`**：`pred/succ` 组合（`0/0` no-op、`R/W/I/O` 单点与组合、典型 acquire `pred=R｜W,succ=R` 形、release `pred=R｜W,succ=W` 形）+ `fm ≠ 0` ⇒ ILLI + SBZ 非零 ⇒ ILLI。
- **独立 oracle**：生成器（Python）按 §3 语义**手算**内存/寄存器期望（大端字节偏移、宽度掩码），并与实现无共享代码；向量文件头写清生成器与 oracle 口径。

### D. 端到端

安装根 `clang` 编一个**只用 `__atomic_*`**、2 线程 × N 次并发计数的程序（`-nostdlib` 或配 ③ 前的 musl；③ 未落地时可用 `__atomic_*` + `clone` 的最小探针，或先做**单线程** CAS 环正确性 + ② 的多线程探针）：
- 判据：`qemu-dadao` 退出码 0、计数 **精确 = N×M**（独立 oracle = 乘法手算），重复 ≥5 轮；
- 该程序同时是 **① 的 B 档（运行）证据**：`llvm-nm -u` 无 `__atomic_*`，两次运行结果一致。

## 验收标准

1. **语义向量全绿**：`make check-qemu-semantics`（载体 +2 行）**全量 PASS**，用例数现场派生（`lr/sc` 24 条 × 各自语义面 + `fence` 合法/非法），FAIL 数 0；日志 `.work/log/qemu/check-qemu-semantics.log` + 本册自有日志落盘。
2. **L2 不回退**：`make check-qemu-smoke` PASS（用例数因新向量集上升，属预期；逐条 PASS）。
3. **端到端**：`__atomic_*` CAS 循环（2 线程 × N）跑通、计数精确、重复 ≥5 轮一致；证据脚本固化命令与 oracle。
4. **异常路径**：`lr` 的 `hb ≠ 0` ⇒ ILLI；`fm ≠ 0`/SBZ 非零 ⇒ ILLI；**低于该宽度对齐**的地址 ⇒ MALIGN（`0x8C`，口径见「✅ 已裁定」）——向量逐条可跑。
5. **门控**：`make install-host`（主会话）后 `make check-qemu-semantics` + `make check-qemu-smoke` + `make check-patch-tree` + `make check`（L1）绿；`python3 tools/qemu/check_qemu_trans.py --strict` 与 `validate_decodetree.py` 仍绿（本册不改 decode 名集合）。
6. **限制与口径写清**：精确 8 B 粒度、ABA 等价写入检不出、设备/非一致内存不适用、异常清保留的实现取舍 —— 完成区逐条列。

## 做（阶段）

- **阶段 0 现场复核**：打印 24 桩 + `fence` 桩的行号与函数名、`insn.decode` 的 259 pattern 与 `fence/lr/sc` pattern 行、`cpu.h` 的 env 字段；记录基线（`check-qemu-smoke`/`check-qemu-semantics` rc 与用例数）。
- **阶段 A `fence`**：换真语义 + `gen_raise_exception_malign`（如需）→ 向量（`atomics-fence.yaml`）→ L2/L3。
- **阶段 B `lr`**：保留状态字段 + 读/抽取/置保留 + ILLI/MALIGN → 向量。
- **阶段 C `sc`**：对齐判定 + 掩码合并 + 宿主 CAS + 清保留 → 向量（含「失败后仍失败」证清保留）。
- **阶段 D 端到端**：CAS 循环 + 并发计数（独立 oracle）→ 证据脚本 `--inject` 反例 → 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

1. `sc` 失败路径**不清**保留 ⇒ 「失败后同址再 `sc`」向量由失败变成功 ⇒ **红**。
2. 把 `sc` 的宿主 CAS 换成普通 load/store（或 `tcg_gen_qemu_st`）⇒ 端到端并发计数**丢更新**（< N×M，或 hang）⇒ **红**；单线程向量仍绿 ⇒ 证明该断言**非恒真**。
3. `lr` 的子宽抽取错（`.t` 取低 4 B 而非大端高 4 B）⇒ 语义向量 **红**。
4. `sc` 的掩码偏移错（把 `.w` 写到字尾）⇒ 相邻字节被改的向量 **红**。
5. `fence` 把 `pred = succ = 0` 也发 `TCG_MO_ALL`（no-op 断言失效）或漏 `fm ≠ 0` 的 ILLI ⇒ 对应向量 **红**。

## 已知边界（**披露，不自行扩面**）

- **`tests/scripts/**` 的改动**超出本册声明的「`components/qemu/**` + `tests/vectors/**` + `Makefile`」范围，但 `sc` 成功路径**必须**能表达「`lr` 后接 `sc`」⇒ 本册只允许**新增可选字段** `sequence:`（`[word, ...]`，缺省时行为与现状**逐字节一致**）+ `derive_width_from_mnemonic` 的 `lr/sc` 宽度映射。**替代方案**（若用户拒绝动 `tests/scripts`）：`sc` 成功向量降级为「端到端证据 + `sc` 失败/MALIGN 向量」，并在完成区记「成功路径无 ISA 级向量」的缺口 —— 二者择一须**明确记录**，不得静默。
- **`scope: excluded` 的 re-scope 不在本批**：`contracts/opcodes.yaml`/`spec/`/`check_scope.py`/只读锁不动 ⇒ 完成后「机器可执行、规范面仍标未实现」的已知张力由另行授权的 spec 册收口。
- **非一致/设备内存**（`I`/`O` 语义、cache line 粒度）本机不涉及：qemu-user 只有普通 RAM，`fence` 的 I/O 成分按 `TCG_MO_ALL` 保守处理；本册**不**声称设备语义。
- **`lr/sc` 的保留清除**对「异常/中断进入」若实现成本过高 ⇒ 记限制 + 排除对应向量，**不得**静默算过。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
