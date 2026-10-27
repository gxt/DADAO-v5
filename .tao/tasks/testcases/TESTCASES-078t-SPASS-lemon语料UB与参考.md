# TESTCASES-078t: SPASS/lemon 语料 UB 修复与 SPASS 参考重定

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-076t、TESTCASES-069t
**状态**：待开始

## 背景（自包含，2026-10-27 全量实测）
1. **SPASS**（`MultiSource/Applications/SPASS`）：
   - `cnf.c:2760` 把 `int symbol_Equal(int,int)` 强转 `BOOL(*)(POINTER,POINTER)`；bank 分离 ABI 下 caller 传 `rb16/rb17`、callee 读 `rd16/rd17`（`0x510fc` → `0x46758`）⇒ 自由变量过滤错 → `list_Top(NULL)`，guest SIGSEGV（si_addr=0x8）。
   - `TESTCASES-069t` 在 `/tmp` 副本改成匹配原型 wrapper 后，DADAO `-O2` 构建 rc=0，stdout+exit md5 `74365d61…`，与**宿主 gcc 构建逐字节相同**；但仍 ≠ 上游 `SPASS.reference_output.small` 的 `b0b56c51…`（已登记 **ISS-338**）。
2. **lemon**（`MultiSource/Applications/lemon`）：
   - `lemon.c:334` 以空参数表声明 `Configtable_clear`；`:1127-1133` 以 `Configtable_clear(0)` 调用；`:4839-4840` 定义参数为 `int(*f)(struct config *)`。C11 6.5.2.2p6 下 `0` 保持 int，与指针参数不兼容 ⇒ UB；DADAO 下调用读到 stale 指针，输出 `Error while running on: <input>`，md5 oracle 不可达（已登记 **ISS-277**）。
   - x86-64/riscv64 因 int/pointer 共用寄存器而「碰巧可用」。

## 目标
1. **语料 UB 修复（可控、可审计）**：以补丁/构建胶水方式修复两处 UB（不改上游源码树本体；补丁落 `tests/tset/llvm-ts/patches/` 或等价非易失位置，并在驱动中显式应用/记录）：
   - SPASS：把 `symbol_Equal` 调用改为匹配原型（或等价、语义等价的 wrapper），保留 SPASS 原逻辑；
   - lemon：给 `Configtable_clear` 加原型/正确调用，使 `0` 以空指针传递。
2. **SPASS 参考重定**：在修复 UB 后，按**可复现、独立于 LLVM/QEMU**的方式重定 `reference_output.small`（宿主 gcc 构建可作为独立 oracle，但须记录编译器/选项/输入/哈希；不得用 DADAO 自身输出作 oracle）。若上游参考的生成条件无法复现，须给出证据并明确「参考不可用」的处置（例如按已记录条件重生成），不得静默改期望。
3. 不把 SPASS/lemon 降级为 known-fail；修复后两者须 **pass**（输出+exit 与重定参考一致）。

## 验收
- 定向（static+dynamic）：`SPASS`、`lemon` 均 pass；SPASS 参考哈希与重定记录一致；lemon 输出 oracle 可达。
- `make check-tset-llvm-full`（static+dynamic）rc=0（与 077/079 合并后全量无未知 fail/blocked）。
- 参考重定证据：宿主 gcc 版本/命令/输入/输出 md5，及与 DADAO 输出的逐字节对账；`ISS-338`/`ISS-277` 更新或关闭（按实际）。
- `make check` rc=0；证据 `.work/evidence/<任务号>/run.sh`（含注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/TESTCASES-078t/`。

## 约束
- 只改本任务范围内的 `tests/tset/llvm-ts/`、`tools/testcases/tset/llvm-ts/`、补丁/胶水、索引/ledger、任务书/milestones；不改 spec/qemu/LLVM 语义。
- 上游源码只读：补丁/胶水必须可重复应用、可审计；不得把 `tests/tset/llvm-ts/` 变成上游源码副本。
- **不提交、不 push**；长构建/长跑申报预计耗时；不跑无关全量。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
