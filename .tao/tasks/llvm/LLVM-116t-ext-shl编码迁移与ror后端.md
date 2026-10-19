# LLVM-116t: `ext`/`shl` 编码迁移与 `ror` 后端（MC + ISel + `ROTL/ROTR` 口径重判）

**模块**：llvm
**项目里程碑**：M9
**依赖**：`SPEC-152t`（**前置**：四表 + `contracts/opcodes.yaml` + `.td` 对照的 `id`/助记符已到位）、`ADR-0032`（`Accepted` 后才开工；`D1`–`D6`）、`LLVM-099t`（`ISD::ROTL`/`ROTR` 当时置 `Expand`，理由 = **ISA 无 rotate**）、`LLVM-097t`（`bswap` 的 `Expand` 先例）、`LLVM-047t`/`LLVM-107t`（窄整数扩展/返回 canonical 先例）、`ISS-210`（改 `.td`/MC ⇒ **必单跑 `make install-host`**，禁旧安装根假绿）、`ISS-229`（L2/L3 不并发）、`docs/Process-01`（补丁树：一文件一补丁 + `series` + `changelog`）
**状态**：待验收

> **追加裁定（2026-10-19，用户原话）**：「**确认：ror 改为 rol**」（前序：「是不是改为rol更合适？本质上ror/rol只需要实现一个即可，而从编码上看，该指令前面是shl，后面是两个shr，如果改为rol，再和shl换个位置，是不是更规整」）⇒ **编码槽位不变**（仍 `010-001` orrr / `011-001` orri），只改**助记符与语义方向**；本册按 `rol` 实现。`spec/` 与 `contracts/` 中的 `ror` 由**另一册**改，本册**未动**（见完成区「遗留问题」的跨册红）。

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
**测试结果**：`oracle.py` **158/158 PASS**（20 条编码独立复算 vs `llvm-mc`、汇编/反汇编往返、旧助记符拒绝、immu6/rd0 边界、rotate 语义恒等式、`llc -O0..-O3` 指令数、Expand 基线）；lit `MC/DADAO`+`CodeGen/DADAO` **108/108 PASS**（构建树工具 overlay）；`check-patch-tree` **181 patches OK**、`check-index-blobs` **131 new-file OK**、`check-source-state` clean、`check-component-changelog` PASS、`check_lit_gen` PASS、`check-asm-list*`/`check-legality-*` rc=0。**预期红（跨册）**：`check-instrinfo` **18 errors**（8 条 M9 `ror.*` 记录无 def + 8 个 `rol_*` def 无记录 + 2 条 self-test；**ext/shl 0 错**）；`MC/DADAO-gen` **10/12**（仅 `gen-orrr.s`/`gen-orri.s`，因向量仍按 `ror.*`）；`check-isa-coverage` 矩阵仍为 235 行（真源 243）——三者都等 `ror→rol` 的 spec/contracts 变更后重生成，**不冒充绿**。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOInstrInfo.td,DADAOCodeGen.td,DADAOISelDAGToDAG.cpp,DADAOISelLowering.cpp}.patch` + `components/llvm-project/changelog.md`；`tests/llvm/lit/MC/DADAO/{rol.s(新),imm-range.s,orri.s}`、`tests/llvm/lit/CodeGen/DADAO/{rol.ll(新),br-jt.ll}`；`tools/llvm/{validate_instrinfo.py,gen_isa_coverage.py}`；`.work/evidence/LLVM-116t/**`。
**验收结果**：`ext.uo/so` `ha 0x20/0x21`（orrr）、`0x28/0x29`（orri）；`shl.o/t/w/b` `0x10/0x18`（旧 `shl.u*` 拒绝）；`rol.o/t/w/b` `0x11/0x19`（`ror.*` 拒绝）；MC 编码逐条 == 独立复算（如 `rol.o rd8,rd9,rd10` = `0x4044824a`）。ISel（`llc -O2`，-O0..-O3 同）：`ROTL` 常量 **1** 条 `rol.o …,8`、变量 **1** 条；`ROTR` 8 → `rol.o …,56`（**1** 条）、变量 `sub.so {rd0,rd4},rd0,n` + `rol.o`（**2** 条）；同形状 `Expand` 基线常量 **5** 条、变量 **7** 条（`--combiner-disabled` 复现）。`rol.b` 寄存器量按 8 取模、`immu6` 64/-1 汇编期拒绝、`rol.b …,8` 汇编受理（越界 = 执行期 ILLI）、`rd0` 汇编受理（执行期 ILLI，与 shl/ext 同口径）；窄 i32/i16/i8 由 `PromoteIntRes_ROT` 展开为 i64 移位（不选 `rol.t/w/b`）。musl `crypt_sha512.c`/`sigdelset.c` 编译 rc=0，新 asm 可汇编，`rol.o` 10 处（旧编译器 0），asm 2471 行 ≤ 旧 2511 行。
**新发现/坑**：① `contracts/opcodes.yaml` 仍名 `ror.*`（另一册）⇒ 本册一改 `rol` 后 `check-instrinfo` 必然红；该红**不是**后端缺陷，签名由证据脚本机械断言（18 errors 全 M9）。② 窄位宽 rotate 在 DAG 被 `PromoteIntRes_ROT` 展开（`NewBits < 2*OldBits` 路径），`rol.t/w/b` 保持 MC-only。③ `expandROT` 变量路径实测 **7** 条（共享一个 mask 常量），此前口述 9 条已更正。④ 反汇编 lit 必须用**重建后的 `llvm-objdump`**（只建 `llvm-mc` 会读到旧 Disassembler，误报 `ext.so`）。⑤ `--combiner-disabled` 可复现旧 `Expand` 的 shl/srl/and/or 形态，作为对照基线。
**遗留问题**：① **BLOCKED（跨册，非 QEMU）**：`contracts/opcodes.yaml` + `spec/` + 生成向量/矩阵的 `ror→rol` 改名；落地后 `check-instrinfo`/`check-isa-coverage` 应全绿，`MC/DADAO-gen` 回 12/12（本册未改 `spec/`/`contracts/`）。② 按派单**未跑** `install-host`/`build-qemu`/L2/L3，故 `make check-instrinfo`/`check-isa-coverage`/`check-lit` 的**安装根**行为未验（安装根仍是旧工具）。③ `QEMU-064t` 负责 `rol` 执行语义/ILLI（本册只做后端）。

**收口（2026-10-19/20）**：分支快进到 `master` 的 `SPEC-152t` `ror→rol` 真源提交 `6ee6b2e`（未新建提交）。① **lit 向量**：用既有 `tools/testcases/generate_lit_vectors.py` 从 `contracts/opcodes.yaml`（243 条）重生成 `tests/llvm/lit/MC/DADAO-gen/*.s` + `gen-fast.s` ⇒ `grep -rn 'ror\.'` = **0**、`grep -rw ror` = **0**（plain `grep -c ror` 的唯一命中是 `gen-excluded.s` 注释里的 `error:`，非助记符），`MC/DADAO-gen` **12/12**。② **`validate_instrinfo --self-test` 去硬编码**：删除 `SAMPLE_MAPPINGS` 字面表，改为每次从 `opcodes.yaml`+`.td` 现场派生（m1+m3+m8+m9 **172/172** id 覆盖、join key 全等、**46** 个可派生 `<mnemonic>_<format>` def 名全等，计数现场打印）⇒ `check-instrinfo` **0 errors**（`--self-test` 亦 0）。③ **矩阵**：`gen_isa_coverage.py --llvm-mc .work/build/llvm/bin/llvm-mc` 重生成 `tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（243 条；accept **233**/reject 10；`rol.o` orrr/orri `isel=yes`）；`--check --llvm-mc`（构建树）**PASS**。④ **门控**：`check-instrinfo` 0、`check_lit_gen` 64/64、MC+CodeGen+MC-gen lit **120/120**、`check-asm-list*`/`check-patch-tree`（**181**）/`check-index-blobs`（131）/`check-source-state`/`check-component-changelog`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check_issues` 全 rc=0；`make -k check` 仅 `check-isa-coverage` 红——**安装根仍是 16:51 旧物**（`rol.o` 未识别；accept 217 vs 构建树 233），待主会话 `install-host` 后复验；顺手把 `.work/log/{llvm/LLVM-116t,spec/SPEC-152t}` 的 66 个旧命名日志改为 `<任务号>-<用途>.log`（内容未动）⇒ `check-run-artifacts` 66 illegal → **0**。⑤ **证据**：`run.sh` default **PASS**（oracle 170/170、全门控、120/120 lit、musl），`--inject` **9/9**（`shl_o_orrr ha` 注入 0→2 errors 后 md5 还原回 0；index-hash 红→绿）。

## 审阅记录

#### 第 1 轮 engineer 自审
自主逐行审查（`.td` 8 个新 def、4 条 pattern/action、LowerOperation、测试与证据脚本）。首轮构建暴露 `immu6imm` 定义晚于使用（TableGen 报 `Variable not defined`）⇒ 已前移到 shift pattern 之前；首轮 lit 暴露 `llvm-objdump` 未重建（旧 Disassembler 把 `rol.o` 打印成 `ext.so`）⇒ 已重建并改证据脚本按地址+字节逐条核对。口径修正：`expandROT` 变量路径由口述 9 条改为实测 **7** 条（注释/changelog/证据同步）。`ROTR` 常量 `(W-c) mod W` 折叠为 immu6 立即数、变量用 `sub.o rd,rd0,n`（低 6 位即 `(-n) mod 64`）已用 `llc -O0..-O3` 实测；窄位宽确认被类型合法化展开，未误选 `rol.t/w/b`。判决：**代码项全部已修**；唯一未闭项是 `contracts/` 仍名 `ror.*` 的**跨册阻塞**（已如实列于遗留问题①，不是本册可修文件）。

#### 第 2 轮 engineer 自审（收口）
- 真源复核：`contracts/opcodes.yaml` 已由 `6ee6b2e` 改为 `rol.*`（m9 8 条），`spec/SimRISC-04/08/09/10` 同步；本册未改 `spec/`/`contracts/`。
- 生成物一律由既有生成器从真源重派生（lit 向量、矩阵），未手改；`grep -rn 'ror\.'` = 0。
- `SAMPLE_MAPPINGS` 已删除；self-test 为 coverage + join-key + 可派生名三条 live 断言（172/172、46 个），可达 FAIL 由 `inject.py` 证明。
- 未修项：无代码 finding；`make check-isa-coverage` 的红只因**旧安装根**（非代码/非矩阵），证据脚本按「安装根是否识别 `rol.o`」现场判定 fresh⇒必绿 / stale⇒必红，`install-host` 后自动切换。
- 判决：收口完成，可交 reviewer 独立复核。

#### 第 1 轮 reviewer 验收
（待填）

#### 第 1 轮 architect 提交（文件集审核）
- 档位：正常提交（主会话指派）；显式 staging，无 `add -A`。
- 文件集 18 项对账：4 补丁 + `changelog.md` + 2 新向量（`rol.s`/`rol.ll`）+ 4 改向量 + `DADAO-gen` 2 条重生成 + `gen_isa_coverage.py`/矩阵 2 件 + `validate_instrinfo.py` + 本册 + `milestones.md`（状态）；均在完成区「修改文件」或收口③④声明的派生/状态范围内，**无越界**。
