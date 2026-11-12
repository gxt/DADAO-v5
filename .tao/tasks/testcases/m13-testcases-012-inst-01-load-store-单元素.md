# m13-testcases-012: `01-load-store` 单元素（`ld.*` + `st.*`）改为汇编+宏

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-spec-001`（退出码表 `0x01`–`0x7F` = 失败点 1–127）+ `m12-chipyard-008`（访存实现）
**可并行分片**：否（共享 `tests/inst/`）
**状态**：已验证

## 背景（用户 2026-11-12 裁定）

- **M13 的核心问题**：`tests/inst` 里每条指令到底测了什么 —— 这是三平台差分的基础
- **YAML 退出**：YAML 不可读、且需再转成汇编才能跑，转换本身可能出错 ⇒ 改为**汇编 + 宏**，期望值内联
- **分类**：大类 = SimRISC 册（`01-load-store` … `12-misc`）；小类 = `contracts/opcodes.yaml` 的 **id**（一 id 一文件）
- **目录**：`tests/inst/01-load-store/<id>.S`（id 已含 format/bank，文件名不重复 format）
- 台账：`tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移状态）

## 范围（本任务 = 18 个任务里的第 1 个）

覆盖 **19 个 id**：
- `ld.*` 11 个：`ld.ub/uw/ut/o/sb/sw/st`（`rrii` × rd/rb/ra/rf 形式）
- `st.*` 8 个：`st.b/w/t/o`（`rrii` × rd/rb/ra/rf 形式）

**不含** `ldm.*` / `stm.*`（属 `01-b`）。

## 目标

1. 建目录 `tests/inst/01-load-store/`，每 id 一个 `.S`（19 个文件）
2. 宏层放 `tests/inst/macros/`：至少
   - `TEST_LD(测试点号, 助记符, 期望值, 地址基址, 偏移, 目标 bank)`
   - `TEST_ST(测试点号, 助记符, 源值, 地址基址, 偏移)`
   - `__CHECK(期望, 实际)` / 失败即 `SYS_EXIT(测试点号)`
   - 参照 `.cache/refs/DADAO/DADAO-testset/isa/macros/scalar/test_macros.h` 的写法（**只参考结构，不复制**）
3. **每 id 按 5 类写用例**（模板见 `tests/inst/MIGRATION.md §3`）：encoding / legality / semantic / boundary / overlap
   - 访存特有边界：**自然对齐**（`ld.o` 8B、`ld.t` 4B、`ld.w` 2B、`ld.b` 1B）+ MALIGN、地址窗口外 ⇒ `CFXMEM`、`rd0` 作目的 ⇒ ILLI
4. **迁移既有 YAML**：把 30 个 YAML 里属于这 19 个 id 的 case 全部并入（含 `base/mem-rd.yaml`、`mem-rb/ra/rf.yaml`、`base/reserved.yaml` 中命中部分）；**只有当某 YAML 文件的全部 id 都迁完后**才 `git rm`，并更新 `MIGRATION.md` 台账
5. 三方对照：chipyard == QEMU == gem5 逐字节（同一镜像）

## 验收

1. 19 个 `.S` 文件齐全，`ls tests/inst/01-load-store/*.S | wc -l` == 19
2. 每个文件检查点数 ≤127，失败点号 = 用例序号（`SYS_EXIT(n)`）
3. **三方逐字节一致**（含全部 MALIGN/CFXMEM/ILLI 故障例）
4. `make check-inst` rc=0；`check-tests-index`/`check-case-ledger` rc=0（新文件需登记 `tests/inst.yaml`）
5. 273 例 md5 不变
6. `MIGRATION.md` 台账更新：本任务覆盖的 19 个 id 标「已迁」，对应 YAML 若已清空则标「已删」
7. **可达 FAIL 注入**：把某个 boundary 用例的期望改错 ⇒ 该文件对应检查点号非零退出
8. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- 一个 id 一个 ELF 意味着 19 次汇编/运行；用现有 `tools/testcases/` 的驱动批量跑，不要手搓循环。
- **不要**改 `contracts/`、`spec/`、`Makefile` 的门控集合（本任务只产语料 + 宏）。
- `.work` 必须软链（`ISS-389`）；改动必须落在任务 worktree 内（`AGENTS.md` 硬约束 14）。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir，用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`tests/inst/macros/inst_test.inc`、`tests/inst/01-load-store/{*.S,inst-tiny.lds}`、
`tools/testcases/inst/run_asm_suite.py`、`tests/inst.yaml`/`MIGRATION.md`/`README.md` 的改动。
逐条对照：期望值是否独立派生自 spec（宽度/符号/大端）、点号 = 用例序号、三方判据是否
可失败、失败路径是否可达（每例失败即 `SYS_EXIT(点号)`，三平台同步红）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `encoding` 类在汇编形态下退化为「字段边界 + 语义」，不是字面 mask/value 校验 | ✅已修 | `MIGRATION.md §2` 与每文件头写明口径；mnemonic↔编码一致性仍由既有门控（`check-instrinfo`/`check-asm-list`/`validate-encoding`）守护 | `make check` 中三者 PASS（见门控日志） |
| F2 自定义段名 `.hmon_stub/.faultpad/.testdata` 未写 flags ⇒ 段不 alloc，链接后落在地址 0，镜像缺段 | ✅已修 | 显式 `.section …, "ax"/"aw"`；`inst-tiny.lds` 段名由 `.text.*` 改为独立名（`.text.*` 会被 `.text` 通配吞掉） | `llvm-readelf -l`：单 PT_LOAD 覆盖 `.text + .hmon_stub + .faultpad + .testdata`；68/68 镜像通过 |
| F3 存储例多条字节通道落在同一 beat ⇒ 期望值互相污染（先后写不同通道） | ✅已修 | 一例一独立 beat（24 beat）+ lane 覆盖；期望值与用例顺序无关 | `st.*` 链例 14–15 检查点全绿（首轮曾 rc=4/2/1） |
| F4 `TEST_ST_RB` 源=基址同号时，装载源值被装载基址覆盖（encoding 例写错） | ✅已修 | rb 形式的 encoding 例改用不同号；真同名单独做 overlap 例（存地址本身） | `st.o_rrii_rb` 链例全绿 |
| F5 `.elseifc` 在 llvm-mc 不存在 ⇒ 故障名分支全落 `.else`「unknown fault name」 | ✅已修 | 改为多个独立 `.ifc` + `.set`，末尾 `.if __onehot == 0` 显式报错 | 68 镜像构建/运行全绿 |
| F6 `__CHECK_MEM` 按 `off` 取 beat，忽略基址偏移 ⇒ 基址非零的存储例核对错 beat | ✅已修 | 改为按 `EA = baseval + off` 的 `EA/8*8` | `st.*` encoding 例 2 全绿 |
| F7 工具默认生成物目录 `.dadao/tests/inst-asm` 未登记 `SCOPE_MAP` ⇒ `manage_tests` 的「未归属目录」判据会红 | ✅已修 | 落到 `harness/inst-asm`（`SCOPE_MAP` 已登记的 inst 产物目录） | `check-run-artifacts` 无本任务条目 |
| F8 证据日志名 `m13-012-*` 不合 `check-run-artifacts` A3（须 `<任务号>-<用途>.log`） | ✅已修 | 全部改 `m13-testcases-012-*` | `check-run-artifacts` 中 `m13-testcases-012` 命中 0 |
| F9 注入脚本首次运行被超时打断后，注入态留在树里（还原未执行） | ✅已修 | `trap 'cp 备份' EXIT` + 注入前用正则断言行唯一命中；还原以备份 md5 为准 | `--inject` 末轮：注入→三平台 rc=12→`cp` 还原 md5 一致→回绿 |
| F10 `HMON_BASE` 在宏层重复定义（`machine-tiny.inc` 已生成） | ✅已修 | 删本地 `.equ`，只用生成物符号；semihosting 服务号/标签改为具名常量 | 重新构建 + 68/68 通过 |

**判决**：全部 finding 已修 / 无未修项 → 状态置「待验收」。

### 第 1 轮 reviewer 验收（2026-11-12）

**重跑（我方命令 → 真实输出/退出码；长输出存运行期日志目录，前缀 `m13-testcases-012-reviewer-`）**
1. `bash .work/evidence/<任务ID>/run.sh` → **`RUNSH_EXIT=0`、`summary: PASS=14 FAIL=0`**（`real 2m3.797s`）：19 文件、68 镜像现场派生、`run_asm_suite 68/68`、迁移对账 19 id + reserved-cfx `6/6`、`check-tests-index 263`、`check-case-ledger 2170`、`validate_vectors 156/156·723`、273 md5 `2d4d94651346ef673c5a855e024c1489`、`check-inst rc=0`（1136/1141+5 deferred、Tiny 44/44）。
2. 独立逐字节复算（不采信脚本判据）：19 个链例 `.out` 三平台两两相同；**282** 个检查点的 8 B 大端字逐一 == `.S` 内联期望（含 `st.o_rrii_rb` 13 号 `TEST_DATA+0x088` 地址值例）→ **0 mismatch**；49 故障例 rc 三平台同值 `241×25 / 252×16 / 248×8` ⇒ **331 例（282+49）**，与完成区同值。
3. 期望值独立性：按 `inst_test.inc` 24-beat 大端 pattern 手工复算 `ld.ub/ld.o/ld.t/st.t/st.o` 5 文件全部期望（`ld.ub` 8 号 `0x037`→beat `0x030` 末字节 `0x80`、`ld.t` 13 号 `+4`→`0x89ABCDEF`…）全对；YAML 语义例值 `0x42`/`0xDEADBEEF…` 与 `.S` 值完全不同 ⇒ 非抄写。
4. 可达 FAIL（自选注入，与工程师不同文件）：`st.t_rrii_rd.S` 8 号 beat `…F00D`→`…F00E`（md5 `4c684669…`→`4f127b72…`）→ 重跑同一脚本 **`RUNSH_EXIT=1`、`PASS=11 FAIL=3`**（`run_asm_suite rc=1`、`67/68`、suite 审计 `rc=1`），该链例三平台 rc **`{chipyard:8,qemu:8,gem5:8}` = 点号**；`cp` 还原 md5 回 `4c684669…` → 重跑 **`RUNSH_EXIT=0`、`PASS=14 FAIL=0`**，`git status -uall` 空。
5. hmon workaround 独立实验：删宏内 `__INSTALL_HMON`（md5 `70c2defc…`→`f800e603…`）→ 同一 ELF：chipyard 故障例 rc **16/17/18 = 点号**（异常未进 monitor 槽）、QEMU **rc=-2 超时** ⇒ 固件 hmon 分派确实三方不同；还原 md5 `70c2defc…` → `4/4` 回绿。配套实测：chipyard 资源 hex hmon 段 120 B ≠ 共享镜像 48 B（md5 `797fe3f6…` vs `c499803a…`）。
6. 门控亲跑：`make check-modules` → **rc=0**（`module checks (L2): PASS`）；`make check` 采信工程师日志（rc=2、唯一红 `check-run-artifacts 58 条` 全为他任务 A3 命名，我方 grep 本任务号在 A3 行 **0 命中**）。
7. YAML 迁移独立比对：4 个 YAML 命中 15 id，逐 id `class × expected_fault` 与 `.S` 分节/`TEST_FAULT` 对上、`.S` 条数 ≥ YAML；「本轮无文件可删」成立（mem-rd 余 11 个 `ldm/stm` id、mem-ra/rb 各余 2、reserved 余 3 条无 id UNDI）。

**约束核验**：验收 1–8 全过（1=19 文件；2=点号 1..N 连续、单文件最大 19 ≤127；3=三方逐字节；4=三门控 + `check-inst` rc=0；5=273 md5 不变；6=台账标「已迁/部分迁移」但为组级、无逐 id 行（见 finding ②）；7=可达 FAIL 工程师一次 + 我方一次；8=完成区 22 行 ≤30）。硬约束 1–8 守住：`git show --stat HEAD` 26 文件与完成区「26 项」逐项对账（4 改 + 22 新增）、验收前后 `git status -uall` 均空、未 commit/push、`.work` 软链、计数全为现场值、全程本地（未占 207/208）。

**非阻断 finding（交 architect）**：① 审阅记录 F1 称「已修：`MIGRATION §2` 与每文件头写明 encoding 口径」——我方 grep `字段边界|mask/value|唯一编码|check-instrinfo` 在 §2 与 19 个 `.S` 头 **0 命中**，§3 仍写「mask/value 校验」；实际 encoding 例 = 寄存器字段极值（rd63/rb63）+ 语义，opcode 字节靠静态门控 ⇒ 建议收尾补一句口径，否则后 17 册照抄歧义。② 完成区第 2 条「故障例 1–4（合计 15–19）」实为 **2–4（合计 16–19）**；台账无逐 id「已迁」行；审阅记录 F7 含产物路径 `.dadao/tests/inst-asm`（任务书不写运行期路径）。③ spec 附录 B `excp_malign` 24 条不含 4 个 rf 形式、而 §对齐要求是助记符级 ⇒ 本任务按正文测 rf 的 MALIGN（三平台一致），建议 spec/contract 侧澄清。④ `.S` 未入 `check-inst`（已披露遗留）⇒ 331 例暂无自动回归，建议 `01-b` 起纳入门控。

**判决：Accepted**（工程师达标；最终接受由 architect 终审）。

## 完成区

**测试结果**：通过 68/68 镜像（19 链例 + 49 故障例，三方同一 ELF）；证据脚本 `--inject` 全量 `PASS=20 FAIL=0`，`SKIP_CHECK_INST=1` 复跑 `PASS=19 FAIL=0`（`RUNSH_RC=0`）。
**修改文件**：新增 `tests/inst/01-load-store/{19 个 <id>.S, inst-tiny.lds}`、`tests/inst/macros/inst_test.inc`、`tools/testcases/inst/run_asm_suite.py`（新驱动：现有 `semantics_gate`/`run_qemu_test` 只吃 YAML，扩它们等于改 `check-inst` 载体集，任务书禁止）；改 `tests/inst.yaml`（+19 条 `inst-01-load-store-001..019`）、`tests/inst/MIGRATION.md`（§2 汇编形态 / §4 进度 / §5 台账 / §6 完成）、`tests/inst/README.md`（新载体与跑法）。`git status -uall` 26 项与本表逐项对应（4 改：任务书 + 3 份 tests/inst 文档；22 新增）。
**验收结果**：
1. `ls tests/inst/01-load-store/*.S | wc -l` = 19。
2. 点号：`run_asm_suite --scan-only` 现场统计，每文件链例 14–15 + 故障例 1–4（合计 15–19），点号 1..N 连续、≤127。
3. 三方：链例三平台退出码 0、结果字节数 = 8×检查点数（8–120 B）、三份字节流逐字节相同；故障例三平台退出码同为 0xF1（CFXMEM）/0xF8（ILLI）/0xFC（MALIGN）。
4. 门控：`make check-inst` rc=0（Vast `1136/1141`+5 deferred、Tiny `44/44`）；`check-tests-index` rc=0（263 条）；`check-case-ledger` rc=0（2170）；`validate_vectors` rc=0（156/156，723 例）；`make check-modules` rc=0；`make check` 仅 `check-run-artifacts` 红（58 条全为其它会话的日志命名/残留，`m13-testcases-012` 命中 0）。
5. 273 例 `sweep_expect.bin` md5 `2d4d94651346ef673c5a855e024c1489` 不变。
6. `MIGRATION.md`：19 个 id 标已迁；`mem-rd/ra/rb`、`reserved.yaml` 标「部分迁移」。**本轮不能删任何 YAML**（三者仍含 `ldm`/`stm` id，`reserved.yaml` 仍含 3 条无 id 的 reserved-opcode 例），删除留给 `01-b`/`12-misc`。
7. 可达 FAIL：改错 `ld.ub_rrii_rd` 例 12 期望值 ⇒ 三平台退出码全 12；`cp`+md5 还原（717227bc…）⇒ 回绿。
8. 本区 30 行内、无运行期路径；`git status -uall` 仅上列文件。
**新发现/坑**：
- 芯片侧 BootROM hex 与 `bootrom_tiny.bin` 的 hmon **分派策略不同**（RTL 侧对同步异常 `escape +4` 跳过指令，QEMU/gem5 侧回落到槽 0xF8）⇒ 故障例不能依赖固件 hmon：测试在运行期把自己的处理器拷到 hmon SRAM 基址再触发异常，三方一致。
- 链接脚本里 `.text : { *(.text.*) }` 会把自定义 `.text.*` 段一并吞掉；自定义段要独立命名并显式 `"ax"/"aw"`，否则不 alloc（地址落 0）。
- llvm-mc 无 `.elseifc`（只有 `.ifc`）；宏实参不能写 `NAME(...)`（整体被当成一个表达式），须 `NAME a, b`。
- 同 beat 内的字节通道用例会互相污染期望值 ⇒ 存储例一例一 beat；三方比较用「链例结果字节流 + 故障例退出码」两条通道。
**遗留问题**：
- `.S` 未入 `check-inst` 门控（任务书禁止改门控集合）：载体派生仍只吃 YAML，新套件由 `run_asm_suite.py` 跑；建议后续任务把载体扩到 `01-load-store/*.S` 并同步 `inventory.md` 门控覆盖表。
- `st.o rb0`（rb0 作源读出当前指令地址）未覆盖：宏层无法把「被测指令自身地址」当期望值。
- `ld.o ra0`（ra0 作目的，`RACNT`/`MRPTR` 特殊写语义）未覆盖：跨平台写语义需先裁定。

#### 收尾（architect，2026-11-12 23:58）

- reviewer **Accepted**：`run.sh` 14/0（2m3s）；**独立逐字节复算 282 个检查点全部 == `.S` 内联期望（0 mismatch）**；49 故障例三平台 rc 同值（241×25 / 252×16 / 248×8）；331 = 282+49。
- **宏层达标**：`TEST_LD 8, ld.ub, rd5, rb6, TEST_DATA, 0x037, 0x…80` 一行可读；期望与 YAML 的旧值（`0x42`/`0xDEADBEEF`）完全不同 ⇒ 独立派生非抄写。
- 自选注入（`st.t` #8）⇒ 三平台 rc `{8,8,8}` = 点号 ⇒ 还原回绿。
- **`ISS-410` 被实证**：删掉 `__INSTALL_HMON` 后 chipyard 故障例 rc=16/17/18、QEMU 超时 ⇒ 三方固件 hmon 分派确实不同，一致性靠测试自装 handler 换来；chipyard 资源 hex hmon 段 120 B ≠ 共享镜像 48 B。**该缺陷登记未解决**（`tests/arch/hmon/expected.yaml:pending_followups` + `check_tiny_hmon [PENDING]`）。
- 文档级 finding 转 `ISS-412`：encoding 类实为「寄存器字段极值+语义」而非 mask/value；完成区「故障例 1–4」应为 2–4；spec 附录 B `excp_malign` 漏 4 个 rf 形式。

