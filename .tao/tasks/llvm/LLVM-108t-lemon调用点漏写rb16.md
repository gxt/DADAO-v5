# LLVM-108t: lemon 调用点漏写 `rb16`（K&R 无原型调用在 bank 分离 ABI 上的归因与收口）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`ISS-277`（本册对应 issue，`open`；源 = `QEMU-063t` 逐例诊断）、`ISS-269`（登记源）、`contract-abi §4.1`（参数寄存器：指针走 `rb16–rb31`）/`§4.2`（指针类参数用基址寄存器）、`QEMU-063t`（现场与证据）、`LLVM-102t`（同文件 `reassignDADAOArgLocs` 最近改动）、`LLVM-107t`（同族 caller/callee 类型口径）
**状态**：待开始

> **立册口径（2026-10-19，architect）**：本册**不以「已确认的后端 miscompile」立册** —— 现场先要判定「后端 bank 分配缺陷」还是「K&R 无原型调用在 bank 分离 ABI 上的语义缺口」。二者处置不同（见「修法候选」与验收 1）。

## 执行环境
**执行环境**：本地

## 问题根源

**现场（`QEMU-063t`，逐字）**：`lemon` 每个 `fork` 子进程以 guest `SIGSEGV/SEGV_ACCERR` 终止；gdb 停在 `cpu_loop_exit_sigsegv(..., access_type=MMU_INST_FETCH, ...)`，`pc = rb32 = 0x7ffff71fdaf0`（guest **栈地址**）⇒ 取指到栈。证据：`.work/log/qemu/QEMU-063t-gdb-lemon.log`、`.work/log/qemu/QEMU-063t-lemon-asm.log`。

**callee 侧（`Configtable_clear`，静态档 `lemon.elf`，`llvm-objdump` 逐条）**：
- `0x3306c` 函数入口；`0x33098: rb2rb {rb32}, {rb16}` —— 形参 `int(*f)(struct config *)` 按 §4.1/§4.2 从 **`rb16`** 取；
- `0x330bc: br.z {rb32}?, [rb0, 148]`（`f == 0` 提前返回）；
- `0x330e8: call [rb32, rd0, 0]` —— `f` 非空时跳到残留的栈地址取指。

**caller 侧（`buildshifts`）**：
- 源 = `lemon.c:1127-1133`（`Configlist_reset`）内的 `Configtable_clear(0)`；
- 实参编译为 `0x24ee0: call [rb0, 57740]`（目标 = `0x3306c`），**该调用前没有任何写 `rb16` 的指令**；附近只有 `0x24eb4: set.zw rd16, wp0, 0x0`（`current = 0` 的存储值，数据 bank），随后 `0x24eb8` 才 `st.o rd16, [rb5, 0]`。

**关键事实（根因候选，未定）**：`lemon.c` 的 `Configtable_clear` 是 **K&R 无原型**写法 ——
- 声明 `lemon.c:334`：`void Configtable_clear(/* int(*)(struct config *) */);`（空参数表 = 无原型）；
- 定义 `lemon.c:4839-4840`：`void Configtable_clear(f)` / `int(*f)(/* struct config * */);`。

用构建树 clang（23.1.3）对等价最小源码实测（`/tmp/opencode/QEMU-063t/knr.c`，`-O2 -emit-llvm -S`）得到**签名不一致的调用**：

```llvm
define dso_local void @Configlist_reset() {
entry:
  tail call void @Configtable_clear(i32 noundef 0)   ; 实参 = i32 ⇒ rd16（§4.1/§4.2）
  ret void
}
define dso_local void @Configtable_clear(ptr nofree noundef readonly captures(address_is_null) %f) {
  ; 形参 = ptr ⇒ rb16
}
```

⇒ 调用点“漏写 `rb16`”**是忠实执行 IR 的 `i32` 实参的结果**：caller 把 0 放进 `rd16`，callee 却按 `ptr` 读 `rb16`。因此**当前证据既可能是调用点/callee 的类型不一致（K&R + bank 分离 ABI 的语义缺口），也可能是后端对无原型调用的 bank 分配缺陷**，须先分类。

**正确性对照（已实测）**：带原型的 `extern void f(int(*)(int)); void g(void){f(0);}` 编出
```
set.zw rd4, wp0, 0x0
rd2rb {rb16}, {rd4}
jump f
```
⇒ 带原型时 `rb16` 正确写入；K&R 版不写 ⇒ 缺陷只出现在无原型调用路径（或由其实参类型决定）。

## 最小复现方向（自包含）

1. **K&R 最小例**（先复现IR/汇编差异）：

```c
void Configtable_clear();                       /* 无原型 */
void Configlist_reset(){ Configtable_clear(0); }
void Configtable_clear(f)                        /* K&R 定义 */
int(*f)(int);
{ if(f) (*f)(0); }
```

```bash
.work/build/llvm/bin/clang --target=dadao-unknown-elf -O2 -emit-llvm -S knr.c -o knr.ll
.work/build/llvm/bin/clang --target=dadao-unknown-elf -O2 -S knr.c -o knr.s
```
判据：IR 是否 `call … @Configtable_clear(i32 0)` 而定义为 `ptr %f`；汇编 `Configlist_reset` 是否只有 `set.zw rd16`、无 `rd2rb {rb16},…`。

2. **带原型对照**：把声明改成 `void Configtable_clear(int(*)(struct config *));` 重编；若 `rb16` 被写且 `lemon` 行为恢复正常 ⇒ 指向 **K&R/无原型语义缺口**（候选 A/C）；若带原型仍漏写 ⇒ 指向**后端 bank 分配缺陷**（候选 B），用 `-stop-after=finalize-isel` / `-debug-only=isel` 打印 `CCValAssign` 的 `LocReg`。

3. **真实目标复现**：`.dadao/tests/llvm-ts-user/static/MultiSource_Applications_lemon/lemon.elf` 已在 `.work/log/qemu/QEMU-063t-lemon-asm.log` 留现场；单独跑 `lemon.elf example1.y`（cwd = 该例 `run/`）可复现 guest `SIGSEGV`。驱动口径见 `QEMU-063t` 复现段。

## 修法候选（**不预设；先分类、再选路**）

- **(A) ABI 语义缺口（K&R 无原型调用）**：若判定为无原型调用在 bank 分离 ABI 上的未定义行为/未定义规则，需**用户裁定 + ADR/`contract-abi` 变更**；可行方向例如「无原型调用把每个标量实参同时写入 `rdN` 与 `rbN`（双 bank 镜像）」或「显式不支持并登记语料限制」。**代价与影响面必须先写清**（多参数序号、浮点、栈参数、与 `LLVM-102t` D4 的交互），**不得**未经裁定实现。
- **(B) 后端 bank 分配缺陷**：若带原型也复现，修 `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch` 的 `LowerCall` / `reassignDADAOArgLocs`（`LLVM-102t` D4 同文件）或 `DADAOCallingConv.td.patch` 的 `CCIfPtr` 规则；以 `contract-abi §4.1/§4.2` 为准，最小改动。
- **(C) 语料/UB**：若判定 C 标准上该调用本就不可移植（无原型声明与指针形参不兼容），**不改 codegen**；给出条款、`lemon.c:334`/`4839` 行号与分类建议，由主会话裁定 `known-fail`/`excluded` 依据（**不得**擅自改标 `pass`）。

**选择判据**：独立 oracle（带原型对照 + 契约 §4.1/§4.2）优先于实现现象；不破坏 `QEMU-063t` 已修的 MemRAS 路径与 `LLVM-102t` D4 行为。

## 接口规范

- **输入**：
  - `.work/build/llvm/bin/clang`（23.1.3）与安装根 `.dadao/cross-toolchain/bin/clang`（改组件后须 `install-host` 才新鲜）
  - `.work/source/llvm-project/`（23.1.3 只读检出）、`components/llvm-project/patches/**`（唯一可改载体）
  - `.work/source/llvm-test-suite/MultiSource/Applications/lemon/lemon.c`（语料只读；行号 334/1127-1133/4839-4840）
  - `contract-abi §4.1`/`§4.2`（期望值来源，不从实现反推）
- **输出**：
  - **分类结论**（A/B/C）+ 逐条证据（IR 逐字、汇编逐条、必要 `CCValAssign`）
  - 若 (B)：`components/llvm-project/patches/**` 补丁更新 + `series`（如增删）+ `changelog.md` + lit 向量
  - 若 (A)：**裁定请求**（选项/代价/影响面），不写实现；经用户逐条确认后才可改契约
  - `.work/evidence/<任务号>/run.sh`（default + `--inject`，含可达 FAIL；日志 `.work/log/llvm/`）
  - 本任务书完成区（与真实输出逐条对齐）
- **约束**：只改 `components/llvm-project/**`（判 (B) 时）+ 探针/证据 + 本任务书；**不动** `spec/` / `.tao/contracts/` / `contracts/` / musl / 语料源。

## 验收标准

1. **分类先落盘（硬前置）**：给出 A/B/C 判定，且必须解释「为何带原型版写 `rb16`、K&R 版不写」；证据含 K&R 最小例与带原型对照的 **IR 逐字 + 汇编逐条**（不得只贴反汇编片段）。
2. **若判 (B)（后端缺陷）**：
   - `lemon` **静态 + 动态两档 pass**（048t 口径：参考 oracle 逐字节一致，或 exit-only 按 048t 分类）；
   - 汇编核对调用点确有写 `rb16`（`rd2rb {rb16}, …` 或等价），且 callee `0x33098` 读到 0；
   - **无回归**：`048t` 抽样 ≥10 例两档、lit 全绿、`QEMU-063t` 的 `dbms` 两档仍 pass；
   - **可达 FAIL ≥2**：注入（如把带原型对照的 `rb16` 写入删掉 / 篡改探针 oracle）⇒ 脚本 rc=1 ⇒ `cp`+md5 还原 ⇒ 回绿（**禁** `git checkout`/`restore`/`stash`）。
3. **若判 (A)（ABI 语义缺口）**：交付「选项 + 代价 + 影响面 + 需用户裁定的原话问题」并**留问**；**不得**擅自改 `contract-abi`/`spec/`，**不得**以 `lemon pass` 作本册交付、**不得**改标 `pass`。
4. **若判 (C)（语料/UB）**：交付 C 标准条款/`lemon.c` 行号/独立 oracle，给出分类建议；不改 codegen、不改计数。
5. **契约对照**：`§4.1`（`rb16–rb31` 地址参数）/`§4.2`（指针类参数用基址寄存器）逐条「条款 → 证据」；**不得**以 x86-64 偶然通过充当 oracle。
6. **`install-host` 前置**：判 (B) 改 `components/llvm-project/**` ⇒ **单跑** `install-host`（`JOBS=8`、不并发、`ISS-210`；**启动前申报预计耗时**），完成后核安装根 `clang --version` 新鲜，并用**安装根**重跑 `lemon` 两档 + 探针（不得只用 `.work/build` 树下结论）。
7. **门控（各留自身 rc）**：`check-patch-tree`（现 **180**，改后现场计数）、`check-instrinfo`（若改 `.td`）、`check-component-changelog`、`make check`(L1) rc=0；L2/L3 按主会话指派、不并发（`ISS-229`）。
8. 完成区 ≤30 行；长输出留 `.work/log/llvm/`。

## 不做

- **不**把本册当「已确认 miscompile」宣传；分类前不得直接改代码。
- **不**在 caller 侧加补偿写 `rb16` 冒充修复（若为 K&R 语义缺口，须先有 ABI 规则）。
- **不**改 `contract-abi` / `spec/` / 语料 / 测试期望；**不**把失败改标 `known-fail`/`pass`。
- **不**动 `QEMU-063t` 的 MemRAS 修复、`LLVM-102t` D4 既有语义、`ISS-253`/`ISS-267`。

## 硬约束

1. 临时目录 `/tmp/opencode/LLVM-108t/`；命令在 workdir 内、**相对路径**；**禁**出界 `cd`；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；**禁** `git add -A`/`.`；**禁** `git checkout`/`restore`/`stash` 还原（一律 `cp` + md5）。
3. 完成区与真实输出逐条对齐，留证捕**被检命令自身**退出码（禁 `cmd | tee` 吞码）。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进（自行处置：查证 / 绕行 / 有据重试并记录次数 / 登记后跳过）；**只在需用户语义裁定**时留问。
6. 用户裁定须把**原话**写入本任务书。
7. 判 (B) 时 `check-patch-tree` / `check-index-blobs` / `check-source-state` 须绿（改 `components/**` 的补丁集完整性）。

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
