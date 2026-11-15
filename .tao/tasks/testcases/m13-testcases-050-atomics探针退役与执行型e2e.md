# m13-testcases-050: `atomics` 探针退役 + 执行型 `atomics_e2e`（用户裁定 A）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-049`（`00-isa-design/atomic_rmw.S` 覆盖指令层 RMW 合成序）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（≥2 路注入 + 相关门控）
**状态**：已验证

## 用户裁定（2026-11-15）

选 **A**：删 5 个 C 探针与驱动/oracle；指令层由 `atomic_rmw.S` 承担；**编译器语义层补一个执行型 e2e**；争用层记 GAP。

## 背景（现场）

- `tests/inst/atomics/` 5 个 C 探针（`aba_treiber`/`atomic_builtins`/`barrier_probe`/`c11_alltypes`/`counter`）+ `tools/testcases/run_atomics_probe.py` + `oracle_atomics.py`；
- **无任何门控**：`Makefile` 无 `check-atomics-probe`、`tools/testcases/l3_run.py` 无成员；只有 `tools/testcases/README.md` 教人手工跑；
- 分层归属：① 指令层 RMW 合成序 → `m13-testcases-049`（`.S`）；② **builtin/C11 运行期** → 本任务补 **1 个执行型 e2e**；③ 争用（ABA/计数/barrier）与内存序强度 → 单 hart 不可观测，记 GAP（挂 `ISS-440`/`ISS-443`）。

## 任务

1. **退役**：`git rm -r tests/inst/atomics/`、`tools/testcases/run_atomics_probe.py`、`tools/testcases/oracle_atomics.py`；删 `tests/inst.yaml` 里 5 条；`tools/testcases/README.md` 删该节；
2. **新增执行型 e2e**：`tests/unit/llvm/e2e/atomics_e2e.c` + `tests/unit/llvm/e2e/lit/atomics_e2e.test`，**照 `fma_e2e.test` 的形态**（clang `-S` + FileCheck 汇编断言 + **链接 crt0/lds 后用 `%qemu -machine dadao-tiny,bootrom-image=…` 真跑 guest，退出码即判据**）；
   - 覆盖：`__atomic_fetch_add/sub/and/or/xor`（返回值 = 旧值、内存 = 新值）、`__atomic_exchange`、`__atomic_compare_exchange`（成功/失败两路、失败时 memory 不变）、以及 **C11 `<stdatomic.h>`** 的 `atomic_fetch_add`/`atomic_exchange`/`atomic_compare_exchange_strong` 各一例（类型 + 对齐）；
   - 每例失败即 `return 非 0`，并打印可定位的序号（沿用既有 `fma_e2e.c` 风格）；
3. **GAP 登记**：`tests/inst/MIGRATION.md` 新增一节「多 hart / 内存序 GAP」：ABA、互斥计数、`a_barrier` 观测量、`fence` 顺序强度 ⇒ 待多 hart 机型；指 `ISS-440`/`ISS-443`；
4. `case-ledger` 重生成；`tests/inst.yaml` 条数减少（5 条）；`check-tests-index`/`validate-vectors` 计数同步。

## 验收（真实 rc）

1. **e2e 真跑**：`llvm-lit tests/unit/llvm/e2e/lit/atomics_e2e.test -v` ⇒ PASS，且贴 guest 退出码 0（不是只 FileCheck）；
2. **可达 FAIL ≥2 路**（`cp`+md5 还原）：① 把某例期望的"旧值"改错 ⇒ e2e 退出码非 0；② 让 `compare_exchange` 失败路径写入内存 ⇒ 退出码非 0；
3. 退役后：`tests/inst/atomics/`、两个工具文件不存在；`grep -rn "run_atomics_probe\|oracle_atomics" Makefile tools/ tests/ docs/` = 0（`.tao/archive/**`、`components/llvm-project/changelog.md` 历史记录豁免，需在完成区列出）；
4. 门控：`check-tests-index`（现场条数）、`validate-vectors`（载体数）、`check-case-ledger`、`check-inst-asm`（id 264 不变）、`check-lit`、`check-no-residue`、`check-knowledge-refs` rc=0；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只改 `tests/inst/**`（删 5 个 C）、`tests/inst.yaml`、`tests/case-ledger.tsv`、`tests/unit/llvm/e2e/**`、`tools/testcases/{README.md,run_atomics_probe.py（删）,oracle_atomics.py（删）}`、`tests/inst/MIGRATION.md`、本任务书；
- **不改** `spec/`、`contracts/`、`components/**`（`oracle_atomics` 若被组件 import ⇒ 停下写「待裁定」，先核 `grep -rn "import oracle_atomics" components/`）；
- 禁 `install-host`/`check-modules`/`build-*`；不 sync/reset 节点；不提交 git；注入还原 `cp`+md5。

## 待裁定

1. **越界两文件（已改，待确认纳入范围）**：`tests/README.md`（活索引：`inst/{atomics,clmul}/*.[ch]` 行 + `2.4 探针` 里的 atomics 手工命令块）与 `tests/INVENTORY.md`（`atomics/` 目录行 + §5.3「未接线的测试资产」行）。理由：验收项 3 要求 `grep -rn "run_atomics_probe\|oracle_atomics" Makefile tools/ tests/ docs/` = 0，而这两个文件是唯二仍指向已删工具的**活文档**（其余命中均在 `.tao/archive/**` 与 `components/llvm-project/changelog.md`，属豁免）。选项：A) 纳入本任务（**已按此执行**，仅改这两行/一块）；B) 回退并把验收项 3 记 BLOCKED。建议 A。
2. **`check-inst-asm` 现场口径与任务书不符（不是缺陷，仅登记）**：任务书写「id 264 不变」，现场为 **271 id / 903 镜像**（264 是 `m13-spec-010` 之前的 id 数；`spec-010` 删 2 加 1、`m13-testcases-048/049` 增 8 个非 id 载体）。本任务未改任何 `.S`，903/903 全绿即为「不变」。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-15）

逐行复查：e2e 的 20 个检查点（每点一个递增退出码、失败即 `return N`）、文件/对象布局（file-scope 对象防优化、`sw8/16/32` 天然对齐邻居）、lit 的 RUN 链（`-S` 断言 → 无 libcall → 编译 → 链接 crt0/lds → QEMU 真跑）、退役面（5 C + 2 脚本 + 索引 5 条 + README 节 + GAP 节）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 1 字节 RMW 首版用 `(uint8_t *)&sw.mid`：**大端**下指向最高字节，check 13 直接红（guest exit 13） | ✅已修 | 改按宽度独立、天然对齐的 `sw8/sw16/sw32` 邻居结构（`pre/field/post`） | guest exit 由 13 转 **0**；`llvm-mc` 无 `-Watomic-alignment` |
| `0x00FF0000` 命中 `check-tests-index` 的 `FORBIDDEN_EXACT`（旧 16 MiB 顶偏移）⇒ 门控红 | ✅已修 | check 15 数据改 `0x001E0000`（期望 `0x001EFFFF`） | `check-tests-index` rc=0（地址扫描 776 文件 / 旧几何残留 0） |
| 文件头初版写「不覆盖 8 字节 `store_n` 与窄 CAS（已知缺陷）」与现场矛盾（`ISS-312`/`ISS-313` 已随 `LLVM-121t` 修复） | ✅已修 | 改为两条**普通回归断言**（check 19/20），并注明原缺陷编号 | 两条断言在现工具链上绿；且 `tools/testcases/README.md` 的「历史缺陷」节改指 e2e |
| `exp64` 声明为 `unsigned long long` 与 `__atomic_compare_exchange_n` 的 `uint64_t *` 不匹配（DADAO 上 `uint64_t` = `unsigned long`） | ✅已修 | `r64`/`exp64` 改 `uint64_t` | `clang -Wall -Wextra` rc=0 |
| MIGRATION/tools README 里保留被删工具名 ⇒ 验收项 3 的字面 grep 不为 0 | ✅已修 | 改述为「驱动脚本与 oracle 脚本」/「atomics 探针 oracle」 | `grep -rn "run_atomics_probe\|oracle_atomics" Makefile tools/ tests/ docs/` = 0 命中 |
| 注入①「改动落盘」原用 `git diff --name-only`（新文件 untracked ⇒ 恒空、会假 FAIL） | ✅已修 | 改为断言源文件含注入文本（直接防空注入，非恒真） | `--inject` 两次均打印「源文件含注入文本」 |
| 任务书写「打印可定位的序号」，但 freestanding e2e 无 stdio（`-nostdlib`，同 `fma_e2e.c`） | ❌不修（口径按现场） | 用**退出码序号**（0=全过，N=第 N 例），文件头与 `.test` 注释显式说明 | guest exit 逐例可定位（注入①→1、注入②→10，与检查点号一致） |

### 第 1 轮 reviewer 验收（2026-11-15，中改档）

**重跑（本人执行，rc=真实退出码）**：`llvm-lit tests/unit/llvm/e2e/lit/atomics_e2e.test -v` ⇒ **PASS rc=0**；失败样例里可见 `timeout 30 %qemu …` 行 **在 lit 内真执行**（`error: command failed with exit status: N`）。手动全链 `clang -S → FileCheck → not grep ×2 → clang -c → llvm-mc → ld.lld → timeout 30 qemu` 七步 rc 全 0、**guest exit=0**。门控全部本人重跑 rc=0：`check-tests-index`（475 = inst275/arch11/unit186/tset3，现场派生）、`validate-vectors`（271 `.S` + 8 非 id、M1 156/156）、`check-case-ledger`（现场 5425 条 / 文件 5429 行；`--ledger` 重生成与仓内 **md5 `4eaab468…` 逐字节相同**）、`check-inst-asm` **903/903（271 id）**、`check-lit` **177/177（含 atomics_e2e）**、`check-no-residue`/`check-knowledge-refs`/`check-milestones-fresh` rc=0。
**证据脚本**：审 `<运行期证据目录>/run.sh`——各断言均有可达 FAIL（grep rc≠1、计数≠275、guest exit≠期望、md5 不等、make rc≠0 均判红），无恒真/两支同果；重跑 `run.sh --inject` ⇒ **23/23 PASS rc=0**（其注入①→guest 1、②→10，还原 md5 `80e04b8e…` 回绿）。
**独立注入 3 路（`cp`+md5，均非工程师那两路）**：① check7 `exchange` 期望改新值 ⇒ lit FAIL `Exit Code: 7`；② check13 邻域期望 `0xA5→0x5A` ⇒ `Exit Code: 13`；③ check12 CAS 失败「内存不变」期望改新值 ⇒ `Exit Code: 12`；另在 check13 后插邻域写 ⇒ 先红在 FileCheck 形状链（rc=1）。三路均还原 md5 `80e04b8e…`、lit 回 rc=0，`git status -uall` 干净（起止快照对账一致）。
**语义抽验 3 例（按 C11/GCC 推导后与断言比对）**：① `fetch_add` 返回**旧值**、内存=旧+delta ⇒ 100 / 105 ✓；② `compare_exchange_n` 失败 ⇒ 返回假、**内存不变**、`expected` 写回实际值（0x1234 / 0x1234 ✓），成功 ⇒ 内存=desired 且 `expected` 不动 ✓；③ 子字宽 `fetch_or` 仅动 2 字节：`0x00FF|0x0F00=0x0FFF`、`pre/post` 保持 `0xA5A5` ✓（大端下用天然对齐字段、无指针偏移）。20 例逐条对过，无与推导相悖者。
**`__atomic` 无 libcall 判定：该 grep 非恒真**——我用 `__atomic_is_lock_free(16,&g16)` 得 `call [rb0, __atomic_is_lock_free]`，`not grep -q '__atomic'` ⇒ **rc=1（会红）**；>8 字节 RMW 在本 target 是 clang 硬错（`unsupported atomicrmw`，根本不产 libcall）⇒ 「`-mcmodel`/去 `-nostdlib`」不可行，以 libcall 样例证明可达性即可。
**退役完整性**：3 路径均不存在；`grep -rn "run_atomics_probe\|oracle_atomics" Makefile tools/ tests/ docs/` = **0 命中**（豁免仅 `.tao/archive/**` + `components/llvm-project/changelog.md`）；`inst.yaml` 280→**275**，id 集合 = 基线减 5 条 atomics（`diff` 相同），本任务 **0 个 `.S` 改动**。
**GAP 节**：§5.6 三层分工 + 四项（ABA / 互斥计数 / `a_barrier` 形状≠语义 / `fence` 强度）均如实标「未验证」并给恢复入口；`ISS-440`、`ISS-443` 确在 `issues.yaml`（均 open）。
**约束核验**：`git show 6aa461fc --name-only` 15 文件全在任务书范围 + 已追认两文件，`spec/`、`contracts/`、`components/` **0 改动**；未跑 `install-host`/`check-modules`/`build-*`；主工作树 `git status` 干净；完成区 12 行 ≤30、无运行期路径、`**状态**` 待验收。
**发现（均文档级，不阻断，交 architect 收尾改）**：① `lit/atomics_e2e.test:13` 写「18 checks」实为 **20**；② `tests/inst/README.md:4` 仍写「另含 `atomics/clmul` 探针源」（`atomics/` 已删，属本任务漏改的同类活文档，不在其越界清单内）；③ §5.6 把 `ISS-443` 注为「内存序强度口径」与其实际标题（`sc` 异常/中断进入清保留三平台不实现）不符，建议改述或另挂口径 issue；④ **合入后须复跑门控**：本 worktree 基线（17:06 派单）早于 049 合入（17:21），`atomic_rmw.S` 在本树不存在（`git merge-tree` 三方 **0 冲突标记**，合入后引用可定位），届时计数变 inst **276** / `.S` **272** / 非 id **9** / 镜像 **916**——完成区数字是 worktree 口径；⑤ ASM FileCheck 为顺序匹配（无 `ASM-LABEL` 锚），布局变化会先红在形状链（实测），非缺陷但后续易误报。

**判决：Accepted**——验收 1–5 全部在本人重跑下通过，硬约束无违反；上述 ①–⑤ 为文档级/合入期事项，按 6.5 记 finding 不返工。

## 完成区

**测试结果**：证据脚本 **13/13**（`--inject` 23/23）；e2e guest exit=**0**（20 例）；lit `atomics_e2e.test` PASS、e2e 目录 **21/21**、`make check-lit` **177/177**；`check-tests-index` rc=0（475 条：inst 275 / arch 11 / unit 186 / tset 3；`.S` 载体 271 / 非 id 8）、`validate-vectors` rc=0（271 `.S` + 8 非 id、M1 156/156）、`check-case-ledger` rc=0（5429 行，重生成**逐字节不变**）、`check-inst-asm` **903/903**（271 id）、`check-no-residue`/`check-knowledge-refs`/`check-milestones-fresh` rc=0。
**修改文件**：删 `tests/inst/atomics/{aba_treiber,atomic_builtins,barrier_probe,c11_alltypes,counter}.c`、`tools/testcases/{run_atomics_probe,oracle_atomics}.py`；改 `tests/inst.yaml`（−30 行 / 5 条，280→275）、`tests/inst/MIGRATION.md`（+§5.6 GAP 节）、`tools/testcases/README.md`（删探针节、改写「历史缺陷」节）；新增 `tests/unit/llvm/e2e/atomics_e2e.c`、`tests/unit/llvm/e2e/lit/atomics_e2e.test`；**越界**：`tests/README.md`、`tests/INVENTORY.md`（见待裁定 1）；`tests/case-ledger.tsv` 重生成无差异；本任务书。
**验收结果**：
1. **退役**：`tests/inst/atomics/`、`tools/testcases/run_atomics_probe.py`、`tools/testcases/oracle_atomics.py` 均不存在；`grep -rn "run_atomics_probe\|oracle_atomics" Makefile tools/ tests/ docs/` = **0 命中**（豁免命中仅 `.tao/archive/**` 4 册 + `components/llvm-project/changelog.md` 历史条）；`inst-atomics-*` 索引 0 条。
2. **e2e**（`lit/atomics_e2e.test` 的 RUN 链）：`%clang -target dadao-unknown-elf -nostdlib -O2 -S` → `%FileCheck --check-prefix=ASM`（`fence cfx_umon, 4095` + `lr/sc` × `t/o/b/w` 四宽度）→ `%not grep -q '__atomic'` / `'__sync'` → `%clang -c` → `%llvm_mc`(crt0) → `%ld -T dadao-tiny-app.lds` → `timeout 30 %qemu -machine dadao-tiny,bootrom-image=%bootrom -kernel %t.elf -semihosting-config enable=on,target=native`。**guest 退出码 = 0**（20 例全过）；每例失败返回其检查点号（1–20），文件头与 `.test` 注释列出编号含义。
3. **覆盖**：`__atomic_fetch_{add,sub,and,or,xor}`（ret=旧值 / mem=新值，含 64 位高位进位）、`__atomic_exchange`（4/8 字节）、`__atomic_compare_exchange_n` 成功/失败两路（失败：mem **不变** + expected 更新，4/8 字节）、子字宽 1/2/4 字节 `fetch_or` 邻域保持、C11 `atomic_fetch_add`/`atomic_exchange`/`atomic_compare_exchange_strong` 各一例（`_Atomic uint32_t/uint64_t` + `_Static_assert` 4/8 字节对齐）、`ISS-312`（8 字节 `store_n` 存值）/`ISS-313`（1 字节 CAS 最高位置 1 必成功）回归各一例。
4. **GAP 节**：`tests/inst/MIGRATION.md §5.6「多 hart / 内存序 GAP」` —— 三层分工表（指令层 `atomic_rmw.S` / 编译器层 `atomics_e2e` / 争用=GAP）+ 四项清单（ABA、互斥计数丢更新、`a_barrier` 观测量、`fence` 顺序强度）+ 恢复入口，挂 `ISS-440`/`ISS-443`。
5. **注入**（`cp`+md5）：① check 1 期望旧值 `100→101` ⇒ guest exit=**1**；② 在 CAS 失败路径插一条 `p32 = 0x5678;`（模拟「失败也写内存」）⇒ guest exit=**10**；两路还原 md5 `ac705f00…` 一致后均回 **0**。
**新发现/坑**：① **大端**：`(uint8_t *)&uint64` 指向**最高**字节（首版 check 13 因此红）——子字宽探针一律用天然对齐的独立字段，不靠指针偏移。② `check-tests-index` 会扫所有文本文件的 `0x…` 字面量，`0x00FF0000`/`0xFC00`/0xFC00_RAM 段等旧几何值出现在**测试数据**里也会红（本任务换值，不放宽门控）。③ e2e 是 `-nostdlib` 裸机：没有 `printf`，「失败点号」只能走**退出码**（`fma_e2e.c` 同款）。④ 验收项 3 的字面 grep 会命中**文档里的历史叙述**，退役说明须改述为「驱动脚本与 oracle 脚本」。⑤ 新文件 untracked 时 `git diff --name-only` 恒空，注入「改动落盘」要用内容 grep。
**遗留问题**：① 越界两文件待确认（待裁定 1）；② `tests/INVENTORY.md` 另有 YAML 期残留（`atomics/{lrsc,fence}.yaml`、`check-qemu-semantics` 20 册等）与 `tools/qemu/{generate_atomics_vectors.py,semantics_gate.py}`、`tests/inst/schema.md` 的 `tests/inst/atomics/*.yaml` 注释——均指 **043 已删的 YAML**，非本任务退役对象，属既有陈旧引用，建议另立清理任务；③ 台账行仍在「待开始」表（`check-milestones-fresh` 报「待开始 1 行」），台账归主会话；④ 未跑 L3（`check-full`/`check-lit-full`），本任务未触 CodeGen/生成器。
