# LLVM-099t: `i64 = rotl`/`rotr` 的 ISel 展开（解 `P2` 阶段 A1 的 `C` 刷表后残留 2 源）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`LLVM-097t`（`i64 = bswap` 已 `Expand`；本册 = 同一 `setOperationAction` 块的**紧邻缺口**）、`INFRA-085t`（**登记源 + 消费方**：阶段 A1 的 `C` 类清单「刷表后仍剩 2 源」）、`ISS-222`（③ 条）/`SPEC-141t`（`rotl`/`rotr` 预研：ISA **无** 旋转指令，属「组合 ≥3 条」候选）；纪律 = `ISS-229`（禁并发）、`ISS-210`（改 `components/**` ⇒ 单跑 `install-host`）、`docs/Process-01`（组件补丁树）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现场证据（**先读**）

- 来源 = `INFRA-085t` 完成区「阶段 A(C1 本体) + C + E」的 `C` 类结论：`arch/dadao/arch.mak` 排除表 **13→2** 后，11 源已可编，**仅剩 2 源** `Cannot select: … = rotl`（`src/crypt/crypt_sha512.c`、`src/signal/sigdelset.c`）⇒ 这两个成员（`__crypt_sha512`、`sigdelset`）仍不进 `libc.so`；`ISS-222 ③` 的 `bswap` 半边已由 `LLVM-097t` 收口，`rotl`/`rotr` 半边**未做**。
- **现场签名（本笔独立复现，2026-10-17，安装根 `.dadao/cross-toolchain/bin`）**：

```
$ TC=.dadao/cross-toolchain/bin; M=.work/source/musl
$ INC="-I$M/arch/dadao -I$M/arch/generic -I$M/obj/src/internal -I$M/src/include \
       -I$M/src/internal -I$M/obj/include -I$M/include"
$ $TC/clang --target=dadao-unknown-elf -ffreestanding -nostdinc $INC \
    -fno-stack-protector -fPIC -fno-unwind-tables -fno-asynchronous-unwind-tables \
    -ffunction-sections -fdata-sections -w -O2 -c -o /tmp/opencode/LLVM-099t/x.lo <src>
```

| 源 | rc | 首行（逐字） | 函数 |
| --- | --- | --- | --- |
| `src/crypt/crypt_sha512.c` | **1** | `fatal error: error in backend: Cannot select: t14: i64 = rotl t12, Constant:i64<45>` | `processblock` |
| `src/signal/sigdelset.c` | **1** | `fatal error: error in backend: Cannot select: t21: i64 = rotl Constant:i64<-2>, t2` | `sigdelset` |

- **DAG 形态**：`t12: i64,ch = load<(load (s64) from …)>`（crypt）/ `t2: i64,ch = CopyFromReg … %0`（sigdelset）⇒ 两条都不是常量折叠残渣，而是**真实运行期旋转**。`crypt_sha512.c:25` 的 `static uint64_t ror(uint64_t n,int k){return (n>>k)|(n<<(64-k));}` 被 DAG 组合成 `ROTL`（`rotr(k)` 规范化为 `rotl(64-k)`）；`sigdelset.c:12` 的掩码式旋转同样归到 `ROTL`。
- **根因（本笔读源码，`file:line` = LLVM 23.1.3 检出）**：DADAO `DADAOISelLowering.cpp` 只注册 `MVT::i64` 的寄存器类，**未给 `ISD::ROTL`/`ROTR` 设 action ⇒ 默认 `Legal`** ⇒ node 原样落到 ISel，而目标**无** `ROTL`/`ROTR` pattern（`DADAOInstrInfo.td` 无 `rev`-类旋转；`grep` 现场 0 命中）⇒ `Cannot select`。同一函数内 `setOperationAction(ISD::BSWAP, MVT::i64, Expand)`（`LLVM-097t` 落点）就在邻近，本册是**同一机制的未做半边**。
- **参照实现（现场读源码）**：AArch64 `setOperationAction(ISD::ROTL/ROTR, MVT::i32|i64, Expand)`（`AArch64ISelLowering.cpp:716-720`；有 `extr` 也仍对 i64 标 `Expand`）；RISCV **无 Zbb** 时 `setOperationAction({ISD::ROTL, ISD::ROTR}, XLenVT, Expand)`（`RISCVISelLowering.cpp:441-443`；有 Zbb 才 `Legal`/`Custom`）。展开体 = `TargetLowering::expandROT`（`TargetLowering.cpp:8777`），由 `LegalizeDAG.cpp:4205` 在 `Expand` 时调用 ⇒ 落成 `shl`/`srl`/`or` 组合，全部已在后端可选。
- **ISA 侧（本册不扩）**：`SPEC-141t` 把 `rotl`/`rotr`（含 `fshl`/`fshr` 漏斗移位）列为**最强候选**，但现状 = 「**组合 ≥3 条** ✗」⇒ ISA **无**旋转指令；本册只修「**能不能选中**」，**不做 ISA 扩展**、**不改** `spec/`/`contracts/`。

## 目标

让 `i64 = rotl`/`rotr`（含由 `(x>>k)|(x<<(64-k))` 组合出的形态）**有合法 lowering** ⇒ 上述 2 源 `-O2`（含 `-fPIC`）**rc=0**、`Cannot select` **0 处**，从而解 `INFRA-085t` 阶段 A1 的 `C` 类尾项（`libc.so` 的 LOBJS 不再缺这 2 个成员）。

**默认路线 = `Expand`**（与 AArch64/RISCV-无-Zbb 同款；语义由 `expandROT` 通用展开保证）。**可选 = Custom → 组合 `shl/srl/or` 手写**，仅在 `Expand` 语义有误时考虑；选它须在完成区写明理由并走同一 oracle。

## 接口规范

- **输入**：本册「立项来源」的现场签名与根因；`contract-isa.md`（**无**旋转指令的现状）；只读：`.work/source/llvm-project/**`（源码检出）、`.work/source/musl/**`（消费侧复现源）。
- **输出**：
  1. **组件补丁**：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch`（**一文件一补丁**、`docs/Process-01`；`check-patch-tree` 机械校验）+ `components/llvm-project/changelog.md`（`Process-01 §10` 体例）；**预期不改 `series` 计数**（只改既有补丁）。
  2. **证据**：`.work/evidence/<任务ID>/run.sh`（一键、非交互、逐项打印「检查名 + 期望/实际 + rc」、任一失败非零退出、含 `--inject` 可达 FAIL）+ 原始输出落 `.work/log/llvm/<任务ID>/`。
  3. 本册完成区（≤30 行）+ `.tao/knowledge/milestones.md` 流水行（收尾归 `/complete`）。
- **约束**：**最小改动**；**不得**改 `spec/`、`contracts/`、`.tao/contracts/**`；**不得**新增 ISA 指令 / 改重定位类型（`ADR-0019 D10` 冻结）；**不得**改 musl 源（锁条目 `patchless` 保持；本缺口是**生产者侧**）；组件源一律 **git 基线**（只经 `patches/**` 交付）；期望值**独立**、**不从 LLVM/本仓工具反推**。

## 做

### ① 复现（现状 2 源 rc=1）

用「立项来源」表中的命令编译两源，断言首行分别含 `Cannot select: … i64 = rotl`（rc=1）。**对照**：同命令编译 `-O0`（或不含旋转的源，如 `src/string/strlen.c`）⇒ rc=0，证明断言非恒真。

### ② 修法（默认 `Expand`，两行 action）

在 `DADAOISelLowering::DADAOISelLowering` 的既有 `BSWAP → Expand` 语句**紧邻处**加：

```cpp
  // `rotl`/`rotr` (ISS-222 ③ 的未做半边; SPEC-141t 预研结论 = ISA 无旋转
  // 指令).  Without an explicit action they default to `Legal`, so the DAG
  // reaches ISel as `i64 = rotl` and aborts with "Cannot select".  Expanding
  // is what AArch64 (AArch64ISelLowering.cpp:716-720) and RISCV-without-Zbb
  // (RISCVISelLowering.cpp:441-443) do; TargetLowering::expandROT lowers it
  // to shl/srl/or, all of which this backend selects.
  setOperationAction({ISD::ROTL, ISD::ROTR}, MVT::i64, Expand);
```

- **导出**：只改 `.work/source/llvm-project` 的**工作树**、`git diff` 导出为补丁（`docs/Process-01 §6.3/§6.4` 收敛 base+1 单 commit）；**重 build + `install-host` 由本任务单跑一次**（申报预计 **≈10 min**：`ninja -C .work/build/llvm -j8 clang lld` ≈4 min〔`LLVM-097t` 实测 3m59s〕+ `install-host` ≈5 min〔`LLVM-091t` 实测〕；`JOBS=8`、**禁**全核、**禁**与任何 L2/L3 并发 —— `ISS-229`；改后端 ⇒ 安装根必须新鲜 —— `ISS-210`）。
- **若 `Expand` 后暴露 `fshl`/`fshr`**（同族漏斗移位，`SPEC-141t` 已登记为候选但**非**本册目标）：**停下报告**、在完成区登记现场签名，**不擅自扩范围**（与 `LLVM-097t`「现场发现新触发面 ⇒ 登记后转出」同口径）。

### ③ 验收

1. **2 源 rc=0**：两源在 `-O2` **与** `-O2 -fPIC` 两档均 rc=0，日志 **0** 处 `Cannot select`；`-O0` 保持 rc=0。
2. **真实构建档**：`make build-musl-shared JOBS=8` 的这两个目标可编（`obj/src/crypt/crypt_sha512.{o,lo}`、`obj/src/signal/sigdelset.{o,lo}` rc=0）；**不要求** `libc.so` 整体可链（仍有 B/D 以外登记项，归 `INFRA-085t`）。
3. **独立 oracle（位序敏感，必做）**：
   - 语义 = 64 位循环左移 = `((v << k) | (v >> (64-k))) & 0xFFFF_FFFF_FFFF_FFFF`（`k=0` ⇒ `v`）、循环右移 = 同式反向。**期望值在 `run.sh` 内以手写十六进制常量表固定**（**不**现算、**不**调用 LLVM/本仓工具、**不**复用被测展开式）。
   - **取值必须端序敏感**（大端）：`0x0102030405060708`、`0x00000000000000FF`、`0xFF00000000000000`、`0x00FF00FF00FF00FF`、`0x8000000000000001`、`0xFFFFFFFFFFFFFFFF`、`0xA5A5A5A5A5A5A5A5`；**断言对象 `ELFDATA2MSB`**，`.dd.o64` 立即数按大端解释。
   - **旋转量边界**：`0`、`1`、`31`、`32`、`63` **逐值断言**（正确性）；**`64` 不作值断言** —— C 层 `(x<<64)|(x>>0)` 是 **UB**、IR `fshl` 移位量 `≥` 位宽为 **poison**，故 `64` 只作为「不得崩溃、不得残留 `rotl` 节点」的稳健性项，完成区须写明该口径（**禁**伪造一个期望值去比对）。
   - 实现方式：对**同一探针源**（`uint64_t rotl64(uint64_t x, unsigned k)` + 常量/运行期两版）编译出对象，用 `llvm-objdump -d` 取该函数中 `shl/srl/or/and` 链，按**自写指令级模型**逐条求值；断言链长 > 0（防空转绿）+ 结构断言「`rotl` 已展开为移位组合」。
4. **不回归**：① `install-host` 后 `make check`（L1）rc=0；② `LLVM-097t` 的三例探针（`strlen`/`memcpy`/`atoi`，`-O2 -fPIC`）剥离 `.comment` 后与 `LLVM-097t` 基线**逐字节相同**；③ `check-patch-tree`（**仍 152**，本册只改既有补丁）、`check-instrinfo`、`check-index-blobs`、`check-source-state`、`check-no-residue`、`check-tasks`、`check-knowledge-refs`、`check-component-changelog`、`python3 tools/infra/check_issues.py` 各 **rc=0**（各留**自身**真实 rc；禁 `cmd | tee` 吞码）。
5. **可达 FAIL**：`--inject` 至少 2 条 —— (i) 把两行 action 注释掉（或改 `Legal`）⇒ 断言「2 源 rc=0」**FAIL**（`Cannot select: … = rotl` 复现）⇒ `cp` 备份 + md5 对账还原（`cp -p` 后 `touch` 源文件，`LLVM-097t` 坑③）⇒ 回绿；(ii) 把指令级模型的移位量/期望值改错一处 ⇒ oracle **FAIL** ⇒ 还原 ⇒ 回绿。**禁恒真断言**；**禁** `git checkout`/`restore`/`stash` 还原（`cp` + md5 或临时树）。

## 不做项（显式）

1. **ISA 扩展 / 新增旋转指令** ✗（`SPEC-141t` 候选未立项；本册只修选中）。
2. **`fshl`/`fshr` 漏斗移位的完整支持** ✗（同族但独立；触发即登记转出）。
3. **`INFRA-079t` 其余接入点（i128/原子/f16/compiler-rt）** ✗。
4. **`libc.so` 整体可链 / `build-musl-shared` rc=0** ✗（归 `INFRA-085t`；本册只解 2 源）。
5. **运行验证 / `qemu-user` / 三套测试集**（`P3`/`P4`）✗ —— 判据 = **能编 + 静态可核**，完成区**不得**出现「运行通过」叙述。
6. **改 `spec/`、`contracts/`、`.tao/contracts/**`、musl 源/锁条目** ✗。
7. **`L2`/`L3` 与里程碑判定** ✗（归主会话 / `/complete`）。

## 验收标准

1. 「做 ①」2 源 `-O2`/`-O2 -fPIC` 四档全 rc=0、`Cannot select` 0 处。
2. 独立 oracle（位序敏感、大端、边界 `0/1/31/32/63` 逐值；`64` 按 UB 口径）全绿；**可达 FAIL** 每条断言可证。
3. 构建纪律：改 `components/**` ⇒ **单跑一次** `install-host`（申报 ≈10 min、`JOBS=8`、不并发、`ISS-210`）；组件源 base+1 单 commit、`check-source-state` rc=0。
4. 不回归（「做 ③ 4」逐条）；门控各留自身 rc=0。
5. 完成区与真实输出逐条对齐（≤30 行）；`milestones.md` 流水行更新（收尾归 `/complete`）。

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
