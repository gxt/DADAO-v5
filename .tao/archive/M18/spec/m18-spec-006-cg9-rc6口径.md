# m18-spec-006: `cg9 rc6`（switch_run_mode）口径统一：复位 2、异步进入取 rc6

**模块**：spec
**项目里程碑**：M18
**依赖**：`m18-idl-002`（已合入，`cg9` 七槽执行器）、`m18-spec-004`/`m18-spec-005`（ADR-0061 R2 规格）
**可并行分片**：否
**预估**：1–2 h（标定：`m18-spec-005` 派单→合入 39 min；本任务含 IDL 初值/自检与 RTL 只读核对，取 1.5–2×）
**档位**：小改（单点口径澄清 + 1 行初值）
**状态**：已验证
**执行环境**：本地

## 背景

`m18-idl-002` reviewer 发现 `cg9 rc6` 口径不一致（`ISS-540`）：

- **spec/契约**：`DADAO-12 §4.7` 表给初始值 2，`§5.4` 伪码注「固定 supv」，`contract-see` 同句 ⇒ 读法是“rc6 不可写、恒 supv”。
- **实现**：QEMU `helper.c:3410` 写 `val & 0x3`、进入取 `switch_run_mode`（`helper.c:3209`）、复位 2（`cpu.c:348`）；IDL 执行器同样「接受 2 位、进入取 rc6」。
- **F2**：IDL `Cfx.__init__` 的 `cg9[6]` 初值为 0，与 spec/QEMU 的复位值 2 不一致。

**用户 2026-11-25 裁定**：选①——**改 spec 措辞**为「复位值 2、异步进入取 rc6」，QEMU/RTL/IDL 实现不动。

## 目标

1. `spec/DADAO-12-SEE-主管系统运行环境.md`：§4.7 `cg9 rc6` 行与 §5.4 伪码注，删「固定 supv」表述，改为「复位 2；异步进入按 rc6 切换运行模式」；语义与 ADR-0061 R2 其它条目一致。
2. `.tao/contracts/contract-see.md`：同步同一句（若契约中确有“固定”字样）。
3. `idl/tools/idl_exec.py`：`cg9[6]` 复位值改 2（与 spec/QEMU 一致）；自检补一条「复位值 = 2」。
4. **RTL 只读核对**：查 `components/chipyard/**` 对 `cg9 rc6` 的写入/读取处理，报告是否与「复位 2、进入取 rc6」一致；**发现不一致只登记，不改 RTL**（属 `m18-chipyard-001`/M16 范围）。
5. 版本号不变（内容澄清）；`spec/.manifests.toml` 的 sha 锁按仓库工具重算。

## 验收（逐条贴真实 rc）

1. `check-spec-codeblocks`、`check-spec-changelog`、`check-spec-purity`、`check-contracts-dir`、`check-contracts-pending`、`check-contract-relocs`、`check-manifests-guard`、`check-idl-sync`、`check-idl-parse` 全 rc=0。
2. `idl_exec --self-test` 全 PASS，含「cg9 rc6 复位 = 2」与「异步进入取 rc6」两条。
3. 全文扫描：`DADAO-12`/`contract-see` 无「固定 supv」残留；`cg9 rc6` 表述唯一。
4. **可达 FAIL ≥2 路**：① `idl_exec.py` 初值改回 0 ⇒ 自检红；② `check-spec-changelog` 只校验结构（逆序/册头/段非空/无任务号），删**单条**变更记录行不会红 ⇒ 以「删 `### 0.8.0-rc（未发布）` 版本段标题 ⇒ 红」+「删本次变更记录行 ⇒ 证据扫描存在性断红」两路实现；`cp`+md5 还原回绿。
5. **下游独立 oracle 两态**：`tests/arch/hart/check_cfx15.py --root . --mode 0 --self-test` rc=0；spec §4.7 rc6 行注入**旧措辞**「固定 supv（2）」⇒ 仍 rc=0（兼容），两种措辞都不写 ⇒ rc=2（可达 FAIL）。
6. `make check` 与基线逐行相同；版本号未变；`check-knowledge-refs` rc=0。
7. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree（分支 `m18-spec-006`）；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`spec/DADAO-12-SEE-主管系统运行环境.md`、`spec/.manifests.toml`、`.tao/contracts/contract-see.md`、`idl/tools/idl_exec.py`、`idl/data/exec_anchor.toml`（如需）、`tests/arch/hart/check_cfx15.py`（**第 1 轮返工扩围**：spec 措辞改动打断该 oracle 的旧措辞断言，按先例改兼容）、本任务书；**不改** QEMU/RTL/gem5/内核/LLVM/其它 spec 册。
3. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`。
4. 门控有 flock：遇锁按 flock 等待，禁清锁/绕过；本任务不得起内核长跑批（`m18-linux-024` 正占用）。
5. 术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 待裁定

无（用户已裁定方案①）。

## 完成区

**测试结果**：默认 27/27 PASS（11 条门控逐条 rc=0、`idl_exec --self-test` 72/72、残留/口径扫描 10 项、`check_cfx15.py --self-test` rc=0 + 槽表 1 项）；`--inject` 49/49（5 路注入→红/兼容→`cp`+md5 还原→回绿）；`make check` KNOWN-RED（本 worktree 无 host 安装根），错误集与 HEAD 基线逐行相同。
**修改文件**：`spec/DADAO-12-SEE-主管系统运行环境.md`、`spec/.manifests.toml`（sha 重算，版本号 0.8.0-rc 未变）、`.tao/contracts/contract-see.md`、`idl/tools/idl_exec.py`、`tests/arch/hart/check_cfx15.py`（第 1 轮返工扩围：§4.7 rc6 断言改为兼容旧/新措辞，依同文件位图措辞先例）、`.tao/knowledge/issues.yaml`（第 2 笔提交 `126aec2e`：`ISS-540` title 补 RTL 发现；非本轮改动，随分支变更集列明）、本任务书；证据脚本在运行期证据目录。
**验收结果**：
- 门控 rc：codeblocks/changelog/purity 0；contracts-dir/pending/relocs 0；manifests-guard 0；idl-sync/parse/exec-anchor 0；knowledge-refs 0。
- spec：`§4.7` rc6 行「复位值 2（supv），异步进入取本寄存器当前值」；入口段「复位值 2 = supv，异步进入取该值」；`§5.4` 伪码注「取 rc6（复位 2 = supv）」；变更记录新增 1 条（不含任务号/ADR）。
- 契约：§3 的 `cfx_hart`/「异步边界」/「统一异步中断」/「入口寄存器」四条同句、附录 A §6 行、§7 新增变更记录。
- 「固定 supv」（含 ``固定 `supv` `` 反引号变体）两册全文 0 命中；`cg9 rc6` 表述唯一。
- IDL：`cg9[6]` 复位 `MODE_SUPV`（2）；自检新增 4 项（reset/write/entry/entry_uses_rc6），72/72。
- 注入（均 md5 往返一致）：① 初值改回 0 ⇒ `FAIL async_switch_reset`（71/72, rc=1）；② 删本次变更记录行 ⇒ 证据扫描 0≠1 红；③ 删 `### 0.8.0-rc（未发布）` ⇒ `check-spec-changelog` rc=1（册头与顶部段不一致）。
- `check_cfx15.py --root . --mode 0 --self-test`：rc=0（改前 HEAD 为 rc=2「fixed supv value not found」）；注入旧措辞「固定 supv（2）」⇒ rc=0，两种措辞都不写 ⇒ rc=2（`rc6 must say …`），还原后 rc=0。
- `make check`：rc=2，停在 `check-isa-coverage`（无 llvm-mc）；基线树同一条错误，`make -k _locked-check` 的 9 个失败目标与基线 `diff` 为空。
- RTL 只读核对：`GewuFile.scala.patch` 读 rc6 恒 2（:1352）、写 rc6 接受即忽略（:1586）、进入 `runMode := 2.U`（:2000）⇒ RTL 是「恒 supv」，与裁定①「RW、进入取当前值」不一致；未改 RTL，登记交 M16/`m18-chipyard-001`。
**新发现/坑**：① `check-spec-changelog` 只校验结构（逆序/册头/段非空/无任务号），删单条变更记录**不会**红 ⇒ 任务书②路改为「证据自带变更记录存在性扫描」+「删版本段标题」两种可达 FAIL；② 任务 worktree 无 `.dadao` 安装根与 LLVM 构建 ⇒ `make check` 基线即红，按「错误集逐行相同」判；③ `Cfx(CFX_HART,0,0,…)` 复位断言证明 rc6 独立于 `cg3` switch_mode；④ **spec 措辞是下游 oracle 的输入**：`tests/arch/hart/check_cfx15.py` 从 `§4.7` 现场派生期望并断言旧句，改措辞必须同步该断言（同文件 :155-162 已有「兼容新旧」先例）；`make check` 在本 worktree 因 8 driver 环境红，掩盖了该回归。
**遗留问题**：① RTL `cg9 rc6` 恒 supv（写忽略、读回 2、进入恒 2）与 spec 新口径不一致——只登记，不改 RTL（属 `m18-chipyard-001`/M16 范围）；② 旧口径残留（非阻断，交后续统一）：`tests/arch/expected-divergences.yaml` DIV-18、`tests/arch/vast-arch-inventory.md`、`ADR-0060`/`ADR-0061` 表、`tests/arch/hart/cfx15.S` 注释；③ 本 worktree `check-arch-self-test` 因 `common.runlimit` 缺失 + 无工具链 8 driver 先红（基线同），故 `check_hart.py` 全链无法在此复核，只以 `check_cfx15.py --self-test` 直接验证。

## 审阅记录

### 第 1 轮 engineer 自审

范围：4 文件 `git diff` 逐行、证据脚本逐行、RTL 三条证据行回读、注入日志核对。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 契约变更记录「QEMU/IDL/上游册行为不变」与 IDL 初值 0→2 矛盾 | ✅已修 | 改「QEMU 侧行为不变；IDL 仅把 `cg9[6]` 复位 0 对齐为 2」 | 契约 §7 现句；门控 rc=0 |
| F2 spec 历史变更记录（hart-first 条）被写成「目标模式由 `rc6` 给出」，与该条 16 槽年代不符 | ✅已修 | 改为年代中性的「目标模式 supv」 | `grep -c 固定 supv`=0；diff 复核 |
| F3 证据脚本 `self-test-pass-lines` 期望取自 `grep -c` 自身（恒真） | ✅已修 | 改为「日志自报总数 == `^PASS` 行数」 | 输出 want=72 actual=72 |
| F4 脚本注入判定用命令替换内的 `$?`，取值脆弱 | ✅已修 | 显式 `rc1=`/`rc3=` 后再比较 | `--inject` 38/38 |
| F5 残留扫描首跑红：命中 1 = 我新增的契约变更记录引述「固定 supv」 | ✅已修 | 改「恒定 supv」表述 | residue-fixed-supv want=0 actual=0 |
| F6 spec 两次改动后 manifest sha 只重算过第一版 | ✅已修 | 最终版重算并回读 | check-manifests-guard rc=0 |
| F7 `spec-rc6-row-reset2` 期望 1 实际 2（表行 + 变更记录同串） | ✅已修 | 改断言唯一串「异步进入取本寄存器当前值」 | want=1 actual=1 |
| F8 复位断言是否受构造参数 `switch_mode` 影响 | ❌不修（已核） | — | 传 0 仍得 rc6=2，证明 rc6 独立于 cg3 |
| F9 残留扫描漏检反引号变体（`固定` 与 `supv` 间夹反引号时未命中） | ✅已修 | 扫描改正则 ``固定 *`?supv``，并加「入口寄存器」条断言 | 手工注入该变体 ⇒ 命中 1；`cp`+md5 还原 ⇒ 0 |

判决：finding 全部闭环（8 修 1 核否），状态 → `待验收`。


### 第 1 轮 reviewer 验收

**重跑记录（均本人在仓库根执行，取真实 rc）**
- 11 条门控 `make <g>` 逐条 rc=0：check-spec-codeblocks / -changelog / -purity、check-contracts-dir / -pending、check-contract-relocs、check-manifests-guard、check-idl-sync / -parse / -exec-anchor、check-knowledge-refs。
- `python3 idl/tools/idl_exec.py --self-test` rc=0：72/72（`PASS` 行 72、`FAIL` 行 0），含 `async_switch_reset/write/entry/entry_uses_rc6` 4 条。
- 仓库根运行期证据目录内 `run.sh`：25/25 rc=0；`run.sh --inject` 38/38 rc=0（三路注入 → 红 → `cp`+md5 → 回绿）。
- `make -k check` rc=2，失败 9 目标：check-isa-coverage（缺 llvm-mc）、check-components / check-width-sizes / check-linux-toolchain / check-syscall-abi（缺安装根与内核源）、check-milestones-fresh、check-writer-guards、check-temp-dirs（磁盘 75.3%>70%）、check-arch-self-test（缺工具链）；与基线树（`git worktree add --detach 8eef380a`，收尾已 `git worktree remove`）同命令的错误行逐行 `diff` 为空。`make check-idl` rc=2（缺安装根 QEMU，环境）。
- 口径对照：两册 `grep -E '固定 *`?supv'` 0 命中；`DADAO-12` §4.7 表行、§4.7 入口段、§5.4 伪码注与 `contract-see` §3 三条 + §6.3 + 附录 A 共 5 处统一「RW、复位 2 = supv、异步进入取该值」。QEMU：`helper.c:3410` 写 `val & 0x3`、`helper.c:3209` 进入取 `switch_run_mode`、`cpu.c:348` 复位 `DADAO_MODE_SUPV`，行号与引文逐条对上。
- 范围：`git diff 8eef380a..HEAD --name-only` = 6 文件（5 + `.tao/knowledge/issues.yaml`），无 QEMU/RTL/gem5/内核/LLVM/其它 spec 册；版本仍 `0.8.0-rc`；`git ls-remote --heads origin m18-spec-006` 为空（未 push）；状态待验收；完成区 15 行；无「银行」。
- RTL 只读核对：`GewuFile.scala.patch`:1352 `Mux(rows.isAsyncSwitch, 2.U…)`（读恒 2）、:1586「accepted, ignored, reads return 2」、:2000 `runMode := 2.U`，`git diff … -- components/` 为空（RTL 未改）；该发现已写入 `ISS-540` title。
- 自设注入：spec §4.7 rc6 行改回「固定 supv（2）」⇒ `run.sh` rc=1（`residue-fixed-supv` 0≠1、`spec-rc6-row-reset2` 1≠0、`check-manifests-guard` 0≠2）；`cp`+md5 还原（md5 与注入前相等）⇒ `run.sh` rc=0、`git status` 空。

**finding**
- **F1（阻断：门控/断言）**：本改动打断下游独立 oracle——`python3 tests/arch/hart/check_cfx15.py --root . --mode 0 --self-test` 在 HEAD **rc=2**（`spec §4.7: fixed supv value not found`；旧措辞/注入态 rc=0）。链路 `check_hart.py:123 → check_cfx15.py:262 → :164-165`；装机条件实测（工具链与 `runlimit` 就位）`python3 tests/arch/hart/check_hart.py --selfcheck` rc=1、traceback 正落该行；主仓装机旧措辞 `make check-arch-self-test` rc=0 PASS ⇒ 合入后 L1 `_locked-check` 成员 `check-arch-self-test` 由绿转红。本 worktree 缺安装根/`runlimit`，8 个 driver 先红于环境，故「错误集 diff 为空」掩盖了该回归；任务书「待裁定：无」亦未披露。修法由 architect 裁定二选一：① 扩本任务范围，照同文件 :155-162 先例让断言兼容新旧措辞；② 另立任务并在此登记 KNOWN-RED。
- **F2**：任务书验收④②路仍写「删 spec 变更记录行 ⇒ `check-spec-changelog` 红」，与完成区自述（该门控只查结构、不会红）不一致，验收文字须同步。
- **F3**：完成区「修改文件」漏列 `.tao/knowledge/issues.yaml`（第二笔提交 `126aec2e`）。
- **F4（非阻断，交 architect 定）**：`tests/arch/expected-divergences.yaml` DIV-18、`tests/arch/vast-arch-inventory.md`、`ADR-0060/0061` 表、`cfx15.S` 注释仍持旧「固定 supv」口径。

**判决：Needs Revision**（F1 阻断；其余验收项本人重跑全绿，口径、QEMU 对照、IDL、RTL 结论、范围、版本、未 push 均已核过）。

### 第 2 轮 engineer 自审（Needs Revision 返工）

返工范围：F1（阻断）+ F2/F3（文档订正）；F4 按裁定只登记、不动文件。

**F1 复验（真实输出，`python3 tests/arch/hart/check_cfx15.py --root . --mode 0 --self-test`）**
- 当前 HEAD 工作树（新措辞）：`[PASS] control stream accepted` / `[PASS] every slot mutation is rejected` / `[PASS] truncation / extra slot rejected` ⇒ **rc=0**（改前同命令 rc=2：`spec §4.7: fixed supv value not found`）
- 注入旧措辞（§4.7 rc6 行 = 「异步进入时切换的运行模式；固定 supv（2）」）⇒ **rc=0**（兼容），`cp`+md5 还原
- 两措辞都不写（改「软件可改写」）⇒ **rc=2**，stderr `spec §4.7: rc6 must say '固定 supv（2）' or '复位值 2（supv）' + '异步进入取本寄存器当前值'`；还原后 **rc=0**
- 修法：只读 `rows["cfx_hart_async_switch_run_mode"][2]` 单元，旧句 或（「复位值 2（supv）」+「异步进入取本寄存器当前值」）二选一；两者皆无 ⇒ 抛 `OracleError`（非恒真、未删断言）。
- 环境说明：本 worktree `check_hart.py --selfcheck` 因 `common.runlimit` 缺失先红（基线同），整链 `make check-arch-self-test` 无法在此转绿；已把该 oracle 直接纳入 `run.sh`（27 项）与注入 ④⑤（49 项）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 oracle 依赖旧措辞被改红 | ✅已修 | `check_cfx15.py` :164-175 兼容旧/新两措辞（沿用同文件位图先例） | 三态 rc=0 / rc=0 / rc=2；`run.sh` 27/27 |
| F2 验收④②与实测不符 | ✅已修 | 任务书验收④改写「删版本段标题 ⇒ 红」+「删记录行 ⇒ 证据扫描红」 | `--inject` inject2/inject3 PASS |
| F3 完成区漏列 issues.yaml | ✅已修 | 「修改文件」列明 `.tao/knowledge/issues.yaml`（`126aec2e`，非本轮改动） | `git diff 8eef380a..HEAD --name-only` 6 文件 |
| F4 旧口径残留（非阻断） | ⏸延后 | 未动 `expected-divergences.yaml`/`vast-arch-inventory.md`/ADR 表/`cfx15.S` 注释 | 已记入完成区「遗留问题」② |

**新发现**：spec 措辞即下游 oracle 的输入——`check_cfx15.py` 从 `§4.7` 现场派生期望并断言原句；同文件 :155-162 已有「兼容新旧措辞」先例可循。`make check` 在本 worktree 因 8 driver 环境红，掩盖该类回归。

判决：F1–F3 已修、F4 按裁定登记；状态 → `待验收`。

### 第 2 轮 reviewer 验收

**重跑记录（均本人在仓库根执行，取真实 rc）**
- 11 条门控 `make <g>` 逐条 rc=0：codeblocks / changelog / purity、contracts-dir / pending、contract-relocs、manifests-guard、idl-sync / parse / exec-anchor、knowledge-refs。
- 运行期证据目录内 `run.sh`：**27/27 rc=0**；`run.sh --inject`：**49/49 rc=0**（④旧措辞 ⇒ rc=0 兼容、⑤两措辞皆无 ⇒ rc=2 且 `rc6 must say` 命中、md5 往返一致）。
- `python3 idl/tools/idl_exec.py --self-test` rc=0：**72/72**、FAIL 行 0。
- **F1 三态**（本人执行）：① 新措辞 `check_cfx15.py --root . --mode 0 --self-test` **rc=0**；② 注入旧措辞「固定 supv（2）」⇒ **rc=0**；③ 两措辞皆无 ⇒ **rc=2**（stderr `spec §4.7: rc6 must say …`）。断言未删、非恒真（读 `rows["cfx_hart_async_switch_run_mode"][2]` 单元，且其前置已断言该行 rc6/RW 存在）。
- **F1 整链（装机条件）**：工具链就位后 `python3 tests/arch/hart/check_hart.py --selfcheck` **rc=0**（`selfcheck: PASS`，3 case 期望槽全 PASS）——第 1 轮同命令 rc=1 OracleError，已恢复；符号链用后即删、`git status` 空。
- `make -k check` rc=2，失败 9 目标；与基线树（`git worktree add --detach 452fa733`，收尾已 `git worktree remove`）错误行逐行 **diff 为空**；两树原因同：isa-coverage / components / width-sizes / linux-toolchain / syscall-abi / arch-self-test（缺 llvm-mc、安装根、工具链）、milestones-fresh（**他人台账** `m16-qemu-006` 表=已验证/册=待验收）、writer-guards、temp-dirs（他人陈旧临时目录、磁盘）；两树 run_arch FAIL 驱动列表一致（`check_hart`/`check_pmem_dma`，均缺 llvm-mc）。
- 口径未回退：两册 `grep -E '固定 *`?supv'` **0 命中**；`DADAO-12` §4.7 表行 / §4.7 入口段 / §5.4 伪码注各 1、`contract-see` 5 处均「RW、复位 2 = supv、进入取该值」；IDL `self.cg9[CG9_SWITCH] = MODE_SUPV`。
- 范围：`git diff master..HEAD --name-only` **恰 7 文件**（contract-see、issues-m18、任务书、idl_exec、manifests、DADAO-12、check_cfx15），无 QEMU/RTL/gem5/内核/LLVM/其它 spec 册；版本 `0.8.0-rc`；`git ls-remote --heads origin m18-spec-006` 空（未 push）；状态待验收；完成区 16 行。
- 分册迁移：`ISS-540` 在 `.tao/knowledge/issues-m18.yaml`（scope 含 `chipyard`），`issues.yaml` 已不存在，`check-knowledge-refs` rc=0。
- 本人独立注入（与第 1 轮不同）：spec rc6 行清空两措辞 + `check_cfx15.py` 断言弱化为 `if False:` ⇒ `--self-test` rc=0（**恒真即漏检**，证其不可接受）；仅还原代码 ⇒ **rc=2**（可达 FAIL）；还原 spec ⇒ rc=0、`check-manifests-guard` rc=0，两文件 md5 与注入前相等，`git status` 空。

**finding（均非阻断）**
- **F-a**：完成区「修改文件」写 `.tao/knowledge/issues.yaml`——该文件经 master 分册已不存在、变更集中实为 `.tao/knowledge/issues-m18.yaml`，路径表述未随迁移更新；收尾由 architect 补一句迁移说明（文档级，不改判）。
- **F-b**：旧口径残留（沿第 1 轮 F4，完成区「遗留问题」②已列、登记不动）：`expected-divergences.yaml` DIV-18、`vast-arch-inventory.md`、`ADR-0060/0061` 表、`cfx15.S` 注释。

**判决：Accepted**（第 1 轮 F1–F3 全部闭环：F1 兼容分支二选一、非恒真、可达 FAIL 且装机条件整链回绿；F2 验收④改实测口径、F3 列全 7 文件；口径未回退、门控与基线逐行相同、范围/版本/未 push/状态均核过）。
