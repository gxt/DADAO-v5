# LLVM-116t: `ext`/`shl` 编码迁移与 `ror` 后端（MC + ISel + `ROTL/ROTR` 口径重判）

**模块**：llvm
**项目里程碑**：M9
**依赖**：`SPEC-152t`（**前置**：四表 + `contracts/opcodes.yaml` + `.td` 对照的 `id`/助记符已到位）、`ADR-0032`（`Accepted` 后才开工；`D1`–`D6`）、`LLVM-099t`（`ISD::ROTL`/`ROTR` 当时置 `Expand`，理由 = **ISA 无 rotate**）、`LLVM-097t`（`bswap` 的 `Expand` 先例）、`LLVM-047t`/`LLVM-107t`（窄整数扩展/返回 canonical 先例）、`ISS-210`（改 `.td`/MC ⇒ **必单跑 `make install-host`**，禁旧安装根假绿）、`ISS-229`（L2/L3 不并发）、`docs/Process-01`（补丁树：一文件一补丁 + `series` + `changelog`）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

- 来源 = `ADR-0032`（`D1`–`D6`）+ `SPEC-152t`（编码真源）；用户 2026-10-19 原话见 `ADR-0032 §Context`。
- **现状（主会话 2026-10-19 核）**：
  1. `DADAOInstrInfo.td.patch`：`ext_uo_orrr ha=0x10` / `ext_so_orrr ha=0x11` / `shl_uo_orrr ha=0x14`；orri 侧 `ext_uo_orri ha=0x18` / `ext_so_orri ha=0x19` / `shl_uo_orri ha=0x1C`；四宽度 `shl_ut/uw/ub` 同构。
  2. `DADAOCodeGen.td.patch`：仅 `(shl/srl/sra GPRD, GPRD)` 三条 orrr pattern（`shl_uo_orrr` 等），**无 rotate pattern**。
  3. `DADAOISelDAGToDAG.cpp.patch`：跳转表索引 `shl_uo_orri` 直接引用（改名 ripple）。
  4. `DADAOISelLowering.cpp.patch`：`LLVM-099t` 把 `{ISD::ROTL, ISD::ROTR} MVT::i64` 置 **`Expand`**，注释明写「The ISA has no rotate instruction … the rotate proposal in SPEC-141t is still unimplemented」⇒ **该前提已被 `ADR-0032 D4` 推翻**，本册必须重判。
  5. `AsmParser` 无手写 `shl`/`ext` 分支（由 TableGen 生成匹配）；`series` 为树形补丁集（`docs/Process-01`）。
- **证据指针**：`components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOInstrInfo.td.patch,DADAOCodeGen.td.patch,DADAOISelDAGToDAG.cpp.patch,DADAOISelLowering.cpp.patch}`。

## 目标

1. **MC 面**：`ext` 两条（orrr/orri）迁到 `ha 0x20/0x21`、`0x28/0x29`；`shl` 四宽度改 `shl.o/t/w/b` 并迁 `ha 0x10/0x18`；新增 `ror.o/t/w/b`（`ha 0x11/0x19`）。汇编/反汇编/编码往返全通。
2. **ISel 面**：`ISD::ROTR` 直配 `ror.o`（常量 ⇒ `orri` 一条；变量 ⇒ `orrr` 一条）；`ISD::ROTL` 给出**有依据的口径**（`Expand` 保留 / 归一为 `ROTR` / 其它）；**不允许**保留「no rotate instruction」的旧注释与旧 `Expand` 而不重判。
3. **`ROTL/ROTR` 口径重判**：以**实测指令数/正确性**为依据（`llvm.fshl/fshr`、C 层 `(x>>n)|(x<<(64-n))`、musl `crypt_sha512` 的 `ror` 习惯用法），把选择与证据写入完成区；若改走 `ror`，须给 `rotl` 变量路径的归一化代价（`sub`/`and` 条数）。
4. **窄位宽**：现场判 `i32/i16/i8` 是否在 DAG 保留（DADAO 以 i64 GPRD 为主）；保留则补 `ror.t/w/b` pattern，不保留则**只保证 MC 可用**并给出类型合法化证据。
5. **无回归**：既有 `shl`/`shr`/`ext` 代码生成、跳转表 `shl.o` 索引、`-O0..-O3` lit/CodeGen 全绿。

## 接口规范

- **输入**：`contracts/opcodes.yaml`（`SPEC-152t` 后）；`spec/SimRISC-04 §4.2`（`ror` 语义）；`.td` 现有定义与 `DADAOOrrr`/`DADAOOrri` 类；`DADAOISelLowering` 的 `LLVM-099t` 段；`llvm-mc`/`llc`/`clang` 安装根（`ADR-0016`，路径从 `manifests/` 取，不硬编码）。
- **输出**：
  1. `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.td.patch`（编码/助记符/def 名 + `ror` 定义）；
  2. `DADAOCodeGen.td.patch`（`shl_o_*` 改名 + `ror` pattern；`ROTL` 若归一则加 pattern）；
  3. `DADAOISelDAGToDAG.cpp.patch`（`shl_uo_orri` → `shl_o_orri`；必要时 `ror` 的 `ROTL` 归一）；
  4. `DADAOISelLowering.cpp.patch`（`ROTL/ROTR` 的 `setOperationAction` 与注释重写）；
  5. 其它 ripple 文件（`DADAOInstrInfo.h` 等，**只在编译/门控要求时改**）；
  6. `components/llvm-project/changelog.md`（`## M9` 节，`docs/Process-01 §10` 体例）；
  7. `tests/llvm/lit/CodeGen/DADAO/ror.ll`（新增：常量/变量/0/边界；`CHECK` 断言 `ror.o`）；
  8. `.work/evidence/LLVM-116t/**`（default + `--inject`）+ 日志 `.work/log/llvm/LLVM-116t/**`；
  9. 本册完成区。
- **约束**：
  - **不改** `spec/`、`contracts/**`、`.tao/contracts/**`（`SPEC-152t` 已落；冲突 ⇒ 停并留问）。
  - **不改** QEMU/语料驱动；**不改** 重定位/ABI；**不新增** ISA 指令（只 `ror`）。
  - **一文件一补丁** + `series` 同步；**不得**把 `.work/source/**` 直改当交付。
  - **改 `.td`/MC ⇒ 必单跑 `make install-host`**（申报耗时、`JOBS=8`、禁全核、不与其他 L2/L3 并发；`ISS-210`）。
  - **计数不写死**；期望编码/语义从 `opcodes.yaml` + `spec/` 取，**不从 `llvm-mc` 反推**。
  - **`ROTL/ROTR` 不许「只改注释」**：动作必须与实测一致；`Expand` 注释若保留必须仍成立。

## 做

### 阶段 0：现场复核与基线

1. 核 `SPEC-152t` 已 `已验证`；`grep -n "shl_uo\\|shl\\.uo"` 于 `components/llvm-project/patches/**` 得基线清单（预计 3 文件 6 处，现场派生）。
2. 记录基线：`llvm-mc --version`、`sha256sum` 安装根 `llvm-mc`；`musl` 的 `crypt_sha512` 现有 asm（`Expand` 路径）作为对照。

### 阶段 A：MC（`.td`）

1. `ext_uo_orrr`/`ext_so_orrr` → `ha=0x20`/`0x21`；`ext_uo_orri`/`ext_so_orri` → `ha=0x28`/`0x29`（def 名/助记符不变）。
2. `shl_uo_orrr` → `shl_o_orrr`（`<"shl.o">`, `ha=0x10`）；`shl_ut/uw/ub` 同理改名 + `ha=0x10`；orri 全部 `ha=0x18`。
3. 新增 `ror_o_orrr`/`ror_o_orri`（`ha=0x11`/`0x19`）+ `ror_t/w/b` 四宽度同构；操作数 = `GPRD`（`dst, src, amount`），`Pattern = []`（由 `CodeGen.td` 选）。
4. 全量 ripple：`DADAOISelDAGToDAG.cpp` 的 `shl_uo_orri` → `shl_o_orri`；任何 `DADAOInstrInfo.h` 枚举引用编译期自然更新（不手改生成物）。

### 阶段 B：ISel（`ROTR`/`ROTL` 重判，**先判后写**）

1. **判据（现场实测，写完成区）**：
   - `ISD::ROTR i64`：置 `Legal` 后 pattern 是否命中？常量/变量各生成几条？（期望 1 条 `ror.o`）
   - `ISD::ROTL i64` 三条候选：
     - (甲) **保留 `Expand`**：`(x<<n)|(x>>(64-n))` ⇒ 多条；**正确性**已有；
     - (乙) **归一为 `ROTR`**：`rotl(x,n) = rotr(x, (64-n)&63)`；常量可折叠（1 条 `ror.o`），变量需 `sub`/`and`（≥2 条）；
     - (丙) 自定义 lower 到 `ror` + 单条取负（若 ISA 的 mod 64 可直接用 `sub` 后 `ror`）。
     - **必须给出**：三候选的指令数（用 `llc -O2` 实测）、`rotl` 语义正确性、与 `fshl/fshr` 的关系。
2. `DADAOISelLowering.cpp`：删除/重写 `LLVM-099t` 的「ISA has no rotate instruction」注释与动作；按判定落 `setOperationAction`。
3. `DADAOCodeGen.td`：
   - `def : Pat<(rotr GPRD:$a, GPRD:$b), (ror_o_orrr GPRD:$a, GPRD:$b)>;`
   - 常量形态（`orri`）按 TableGen 可匹配写法补；若常量被 DAG 折叠为其它形式，须在完成区说明并给替代证据。
   - 若选 (乙)，补 `ROTL` → `ror` 的归一 pattern/`Select`。
4. 窄类型：`llc` 喂 `i32`/`i16`/`i8` 的 `llvm.fshl`/`rotr`，观察 legalize 结果；保留窄类型则补 `ror.t/w/b` pattern，否则在完成区给出「类型被提升」的证据与「MC 仍支持四宽度」的边界。

### 阶段 C：构建、安装与验证

1. **单跑** `make install-host`（`JOBS=8`；申报预计耗时；不与 L2/L3 并发）。
2. MC 往返：对 6 组（`shl.o/t/w/b` + `ext.uo/so` + `ror.o/t/w/b`）用 `llvm-mc -filetype=obj` + `llvm-objdump -d` 核汇编/反汇编/字节；编码期望从 `opcodes.yaml` 的 `mask`/`value` 独立算。
3. `llc -O0/-O1/-O2/-O3` + `-verify-machineinstrs`：`ror.ll` 全绿；`crypt_sha512` 类用例的 `ror` 指令数下降（对照基线）。
4. 重生成覆盖率矩阵：`python3 tools/llvm/gen_isa_coverage.py`（或 `--check`，按脚本用法），确认 `ror.*` 行 = `accept` / `isel=yes`（o 变体至少），`shl.*` id 改名后 `isel=yes` 保持。
5. 证据脚本 `--inject`：把 `ror_o_orrr` 的 `ha` 改成 `0x10`（与 `shl.o` 冲突）⇒ `check-instrinfo`/MC 往返必须红；`cp` 备份 + `md5` 对账还原后回绿。

## 验收标准

1. **前置**：`SPEC-152t` = `已验证`；`ADR-0032` = `Accepted`。
2. **MC 逐条**：`ext.uo/so`（orrr/orri）编码 = `100-000/001`、`101-000/001`；`shl.o/t/w/b` = `010-000`/`011-000`；`ror.o/t/w/b` = `010-001`/`011-001`；与 `contracts/opcodes.yaml` **逐条**（`mask`/`value`/`ha`）一致；`llvm-mc` 汇编 + `llvm-objdump` 反汇编双向可逆。
3. **助记符**：`llvm-mc` 拒绝 `shl.uo/shl.ut/shl.uw/shl.ub`（非零 + 诊断），接受 `shl.o/t/w/b`；`ext.uo/ext.so` 不变；给真实输出。
4. **ISel**：`ror` 常量 = **1 条** `ror.o … imm`；变量 = **1 条** `ror.o … reg`；`ROTL` 口径有**三候选对比表 + 实测指令数 + 正确性**，动作与结论一致；无 `Cannot select`。
5. **窄类型**：`i32/i16/i8` 的 rotate 行为有实测结论（选中 `ror.t/w/b` 或证明被提升并保证语义正确）；不得只写「不适用」而无证据。
6. **`ROTL/ROTR` 注释**：`DADAOISelLowering.cpp` 不再含「ISA has no rotate instruction」的失效断言（或已改写为生效口径）。
7. **门控**：
   - `make check-instrinfo` rc=0；
   - `make check-isa-coverage` rc=0（矩阵重生成后）；
   - `make check-patch-tree` rc=0（`series` 与补丁树一致）；
   - `make check-component-changelog` rc=0；
   - `make check-source-state` rc=0；
   - `make check-lit` rc=0（L2，含 `tests/llvm/lit/MC/DADAO`、`CodeGen/DADAO`、`tests/e2e/lit`）；
   - `python3 tools/testcases/check_lit_gen.py` rc=0；
   - `make check-lit-full` rc=0（L3 全量 MC；若耗时超预算，须申报并落后台 + 完成标记）。
   - **跨册预期红**：`make check-interface` / `check-qemu-smoke` / `check-qemu-semantics` 在 `QEMU-064t` 前为红，**如实列出**，不得冒充绿。
8. **可达 FAIL**：`--inject`（`ha` 冲突）后 `check-instrinfo` 或 MC 往返非零；还原后 `md5` 一致、门控回绿；三段输出齐全。
9. **无回归**：既有 `shl`/`shr`/`ext` CodeGen lit（现场计数）全绿；跳转表用例（`br-jt.ll`）仍过；musl `crypt_sha512`/`sigdelset` 编译不回归。
10. **补丁纪律**：一文件一补丁；`series` 不变或只增不删；`changelog.md` 有 `## M9` 条目（含用户原话指针、改动摘要、实测数字）。
11. **`install-host` 新鲜度**：证据须含安装根 `llvm-mc`/`llc` 的 `sha256`/时间戳 + `--version`，证明来自本次构建（`ISS-210`）。

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
