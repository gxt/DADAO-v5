# m14-spec-008: 把 DADAO-13 的第 1、2 章正文并入 DADAO-12（DADAO-13 只留引用）

**模块**：spec
**项目里程碑**：M14
**依赖**：无（纯文档重组；`DADAO-13` 0.1.4-rc / `DADAO-12` 0.7.3-rc 当前态）
**可并行分片**：否（同改两册 + 锁）
**预估**：1–1.5 h
**档位**：中改（spec 两册结构 + 锁哈希 + 引用；复核 ≥2 路注入）
**状态**：待验收

## 背景（用户 2026-11-17 原话）

> 「这部分 spec 内容在 DADAO-13 中，你的疑问确实是个事，请把 DADAO-13 的第一章第二章移动至 DADAO-12，DADAO-13 只保留个引用就行。」

起因：`DADAO-12 §3.4 cg3` 正文只有一句「H-mode 寄存器（cg=3）定义见 HEE」，而 `cg3 rc0–rc3` 的四类同步 mask 实际定义在 `DADAO-13 §1`；`DADAO-13 §2` 的 cfx_hmon 异常原因表同样只在 HEE 册。两册割裂导致实现方（chipyard）把四类 mask 合并成一份而未被正文拦住。

## 目标

1. **`DADAO-12 §3.4 cg3 - hypv mode 寄存器`**：用 `DADAO-13 §1` 的**全文**替换现有「定义见 HEE」占位——即寄存器表（rc0–rc12）+ 「`rc0`–`rc3` 四类同步 mask」段 + 「`rc10` 初值与写入」段，逐字搬运，不改语义。
2. **`DADAO-12 §4.4 cfx_hmon - hypervisor monitor`**：迁入 `DADAO-13 §2` 的 **hmon 说明段**（「hmon 为 hypv 下的同步异常处理核芯功能扩展…否则触发 CFXREG」）；异常原因表**不重复贴**，改为「与 `cfx_umon` 一致（表见 §4.1）；`CFXMEM`/`CFXPERM` 的 `cause_info` 与子原因见 §3.6」——避免制造第二真源。删除「详细定义见 HEE」。
3. **`DADAO-13`**：`## 1. cg3 - hypv mode 寄存器` 与 `## 2. cfx_hmon - hypervisor monitor` 两节**只保留标题 + 一行引用**（分别指向 `DADAO-12 §3.4`、`§4.4/§4.1`），章节编号保留作锚点（历史任务书/ADR 的 `DADAO-13 §1/§2` 引用仍可解析）。`## 3. 启动与引导移交`（详见 HBI）与附录不动。
4. **版本与锁**：两册变更记录各加一条**内容条目**（写「章节并入」+ 用户原话来源）；**版本号不得升级**——`DADAO-12` 保持 `0.7.3-rc`、`DADAO-13` 保持 `0.1.4-rc`，是否升级由用户明确认可后再改（用户 2026-11-17 规则）。按 `docs/Process-06 §5` 重算两册锁哈希（`spec/README.md` 索引若含 sha256 同笔更新）。
5. **活跃引用同步**：只改 `spec/README.md` 与 `.tao/contracts/**` 中指向 `DADAO-13 §1/§2` 的**活跃**引用（改成新位置）；**历史任务书/ADR/refs 不改**（锚点仍在，且历史记录不该回写）。

## 验收（逐条贴真实 rc）

1. **内容无丢失**：逐行对照——`DADAO-13 §1` 的表格行数 + 两段说明、`§2` 的说明段，全部出现在 `DADAO-12 §3.4/§4.4`（行数与文字逐条比对，给 diff/命令输出）。
2. `DADAO-13 §1/§2` 只剩标题 + 引用行（`grep -c` 表格行 = 0）。
3. `make check-spec-drift check-spec-changelog check-spec-purity check-spec-cite-targets check-spec-refs check-spec-readonly check-spec-codeblocks` 全 rc=0；两册锁哈希与 `spec/README.md` 一致。
4. **≥2 路注入**（`cp`+md5 还原）：① 把 `DADAO-12 §3.4` 的 `rc0` 行删掉 ⇒ 内容对照/检查红；② 把 `DADAO-13 §1` 重新贴回表格 ⇒ 「只留引用」断言红。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树。
2. **只动**：`spec/DADAO-12-*`、`spec/DADAO-13-*`、`spec/README.md`（如需）、`.tao/contracts/**` 的活跃引用、本任务书、锁文件；**（architect 认可，2026-11-17 补记）**另含 `tools/linux/**` 的解析入口/文案/标签改指（判据与期望值未动）、`tools/spec/gen_cfx_aliases.py` 的来源说明、`spec/Kaiwu-*` 的引用行（只改指针，正文语义不动）。**不动** `spec/SimRISC-*`、`tests/`、`components/`、`Makefile` 门控集合。
3. **语义零变更**：不改任何寄存器初始值/位索引/异常语义；只做搬运与引用改写。
4. 不提交 git；注入还原用 `cp`+md5（禁 `git checkout/restore/stash/show`、禁 `reset --hard`）。

## 待裁定

1. ~~跨模块：`tools/linux` 解析目标改指 `DADAO-12 §4.1`~~ ——**已在返工内处置**（见审阅记录第 2 轮 finding 5/7 与完成区）。
2. ~~生成器来源说明改指~~ ——**已处置**（finding 6）；重算后投影计数不变。
3. **版本号**：按用户 2026-11-17 规则保持 `0.7.3-rc` / `0.1.4-rc`，未升级；若后续要升，须先发布 0.7.3/0.1.4（`-rc` 段只能取下一发布段的 z+1，实测 0.7.4-rc 直上会 FAIL），并同笔同步互锁组 SBI/HBI。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 1. 逐字搬运时两处册内引用原为「见 SEE §3.1 / 见 SEE §2.1」（搬入 SEE 后成了册内自指） | ✅已修 | 改为「见 §3.1」「见 §2.1 核内地址空间表」，仅引用形态、语义不变 | `verify.py` B1「0 行缺失（共 5 行）」 |
| 2. `§4.4` 改写后丢了原句「`cause_info` 恒为地址」字面 | ✅已修（评估通过） | 新句显式指 `§3.6`，该册规范句仍在（`§3.6`（六）「恒为地址」） | `grep 恒为地址` 命中 D12 行 451 |
| 3. `contract-syscall` 首次替换把同一册路径写成两条（`…md`（§3.1…）+ `…md §3.4`） | ✅已修 | `§3.4` 并入括号列表、`§8` 行并入节号串 | `check-spec-refs` PASS |
| 4. 表格迁册后投影未重算（cg3 模板行顺序变化） | ✅已修 | 重跑 `tools/spec/gen_cfx_aliases.py`（计数不变：12 scalar / 1308 regs） | `check-cfx-aliases` byte-identical；`check-cfx-alias-table` OK |
| 5. L2 解析器（`k2_trap_probe`/`k3_pt_probe`）指向旧位置会红 | ⏸延后 | 超本任务文件范围，入「待裁定」1/2 | 见待裁定第 1 条（附实测解析结果） |

**判决**：finding 1–4 已修并复验；finding 5 为跨模块事项、按硬约束不自扩范围，记入待裁定由主会话处置。

### 第 2 轮 engineer 自审（返工：解析器/生成器改指）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 5.（上轮延后项）`spec_cause_table()` 按 `## 2. cfx_hmon` 切 D13 ⇒ 0 条 `SystemExit`，L2 会红 | ✅已修 | 改解析 `spec/DADAO-12` 的 `### 4.1 cfx_umon`，截断边界随之由 `\n## ` 改 `\n### `；docstring 与 C3 标签同步 | 直调返回 11 条；`verify.py` G1/G2 PASS；注入③（回退 D13）⇒ G1/G2/G4 FAIL |
| 6. 生成器来源行硬写「`DADAO-13`（cg3 hypv 寄存器表）」 | ✅已修 | `render_markdown` 两行来源说明改指 `DADAO-12`（含 `§3.4` cg3 表）+ 模块 docstring | 投影重算后来源行含 `§3.4`；`check-cfx-aliases` byte-identical、`check-cfx-alias-table` OK |
| 7. 导入方/同族脚本仍有 `DADAO-13 §2` 字样指针（`check_k2`、`k3_page_probe`、`k3_pt_probe` 未用常量） | ✅已修 | 注释/报错/检查标签改指 `DADAO-12 §4.1`；`k3_pt_probe` 删掉未使用且已失效的 `SPEC_DADAO13` | `verify.py` G4「0 个文件」；`py_compile` 全通过 |
| 8. 改动后是否仍满足「语义零变更 + 投影计数不变」 | ✅核对 | 只改解析入口与文案，未动判据/期望值 | 投影仍 12 scalar / 36 specific / 1308 regs |
| 9. 门控是否真的回绿（不能只靠单测） | ✅已验 | 跑完整 `check-linux-k2`（含 K0/K1 回归） | `check-linux-k2: PASS (104/104)`，`[GROUP] B 27/27 E 15/15 T 17/17 M 12/12 S 20/20 X 9/9 R 4/4` |

**判决**：finding 5–9 全部已修/核对；`check-linux-k2` 实跑 PASS（104/104）。

### 第 1 轮 reviewer 验收（2026-11-17）

**自证/快照**：`git rev-parse --show-toplevel` = 本 worktree、branch `m14-spec-008`；审前 `git status --porcelain -uall` **0 行**、HEAD `0b98636c` 未动；审后唯一改动 = 本审阅记录（任务书），reviewer 未提交 git。
**内容无丢失（reviewer 独立脚本，非 engineer 的 verify.py）**：`f78c78b9:D13 §1` 24 行（表格 10 数据行）、`§2` 18 行（原因表 11 行）；`§1` 的 15 个非标题非表格行在 D12 §3.4 **0 缺失**、表格 **10/10 逐行相同**、`rc0`–`rc3` 段与 `rc10` 段在位；`§2` hmon 说明段在 D12 §4.4（True）、原因表在现 D13 **残留 0**。现 D13 `§1`/`§2` 表格行 **0/0**、正文行 1/1（仅标题 + 引用）。
**语义零变更**：逐字比对仅 2 处册内引用形态改写（`见 SEE §3.1/§2.1` → `见 §3.1/§2.1`，finding 1 已披露）；`§4.4` 原因句按任务书目标 2 改写，「恒为地址」仍在 `§3.6`（L451）与 `§4.1`（L524/534）。寄存器初始值/位索引/异常语义未改。
**版本与锁**：册头仍 `0.7.3-rc` / `0.1.4-rc`；锁 `9e3e3b73…` / `6a39d003…` 与两册实测 sha256 **逐字节 MATCH**；`spec/README.md` 无 sha256 字段、未改。
**门控（reviewer 重跑，rc 直取）**：`check-spec-drift`/`-changelog`/`-purity`/`-cite-targets`/`-refs`/`-readonly`/`-codeblocks`/`-numbering` + `check-cfx-aliases` + `check-cfx-alias-table` **10/10 rc=0**；`check-linux-k2` **rc=0，PASS (104/104)**（79 s；K0 119/119、K1 112/112）。`check-knowledge-refs` rc=2，唯一红项在他人任务书 `m16-chipyard-001`（本 diff 未触及）。
**证据脚本**：审过 `run.sh`/`verify.py`——每条断言有可达 FAIL 路径、rc 用变量取（无 `| tee` 吞码）、还原走 `cp`+md5、oracle 与 `git show f78c78b9:D13` 逐字节一致；reviewer 重跑 `run.sh` **rc=0、TOTAL rc=0、checks=26 fails=0**，注入**，注入①②③ 各 FAIL（合计 11 个 `[FAIL]`）→ restore rc=0 → 回绿。
**独立注入（2 路，均不在任务书注入清单）**：A 删 D12 §4.4 hmon 段 ⇒ `C1`+`E3` **FAIL rc=1** → `cp` 还原 md5 `05aab2e2…` 相等 → rc=0；B D13 册头改 `0.1.5-rc` ⇒ `E2`+`E3` **FAIL rc=1** → 还原 md5 `3f06c97f…` 相等 → rc=0。全程无 `git checkout/restore/stash/show`、无 `reset --hard`、无 `timeout 124`。
**越界**：`f78c78b9..HEAD` = **12 文件**，与完成区「修改文件」逐一对应；`spec/SimRISC-*`/`spec/Kaiwu-*`/`tests/`/`components/`/`Makefile` 命中 **0**。
**主工作树只读**：`/mnt/tao/DADAO-v5` `git status` 审前/审后 0 行；`.dadao/cross-toolchain` **0** 文件被改、`.work/build` **0** 新增；仅 `.work/source/linux/.git` 新增 86 个松散对象（本仓门控 K12 `apply-series` 的 `read-tree`/`write-tree` 常规副作用，HEAD/index/工作树内容未变）；构建产物 **82** 个新增全在本 worktree `.work/build/linux`。（14:55 主工作树另有并行会话提交 `m16-gem5-011`，与本任务无关。）
**findings（非阻断）**：① `spec/Kaiwu` 仍有 9 行活跃指针写 `DADAO-13 §1/§2`（任务书目标 5 只授权改 `spec/README.md`+`contracts/**`，锚点仍可解析）⇒ 请 architect 定是否补一轮；② `tools/testcases/arch/min_rom_probe_*.py` 注释级 D13 指针（已披露遗留）；③ 越界改 `tools/linux/**`(4)+`tools/spec/gen_cfx_aliases.py`(1)——不在硬约束 2「只动」白名单，但完成区已披露、且是 `check-linux-k2` 保持绿的必要改指（仅解析入口/文案/标签，无判据与期望值改动，`k3_pt_probe` 只删未用常量）；④ `check-isa-coverage` 因缺 `llvm-mc` 未跑（已披露环境限制）。
**判决：Accepted** —— 验收命令在 reviewer 自己重跑下全绿，内容无丢失/语义零变更/版本未升/锁一致/越界合规/主工作树只读六项约束均守住；4 条 finding 留 architect 终审。

### 第 3 轮 engineer 收口（4 条 reviewer finding）

| finding（reviewer） | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| ① `spec/Kaiwu` 仍有 9 行活跃指针写 `DADAO-13 §1/§2` | ✅已修 | 9 行逐条改指 `DADAO-12 §3.4`（7 行）与 `§4.1`（2 行）；L74「定义见 HEE」改「定义见 `DADAO-12 §3.4`」；`Kaiwu` 锁 `sha256` 重算 | `verify.py check-kaiwu` 4/4；注入④（改回 D13）⇒ K1–K4 全 FAIL → 还原回绿；`check-spec-readonly` rc=0 |
| ② `tools/testcases/arch/min_rom_probe_*.py` 注释级指针 | ⏸登记（不改） | 只记录，不扩范围（不影响门控、锚点仍在） | 见完成区「遗留问题」 |
| ③ 越界改 `tools/linux/**`(4) + `tools/spec/gen_cfx_aliases.py`(1) 不在白名单 | ✅已收口 | 硬约束 2 白名单按 architect 认可补记（仅解析入口/文案/标签/来源说明；判据与期望值未动） | 本任务书硬约束 2 现文 |
| ④ `check-isa-coverage` 缺 `llvm-mc` 未跑 | ⏸环境限制 | 本 worktree 无 `make install-host`，保留披露 | 完成区「遗留问题」 |

**判决**：①③ 已收口并复验；②④ 按登记/环境限制处理，无未修实现项。本轮未升级任何版本号、未提交 git。

### 第 2 轮 reviewer 验收（2026-11-17，4 条 finding 收口 + 不回归）

**快照**：`git rev-parse --show-toplevel` = 本 worktree、branch `m14-spec-008`、HEAD `ec18fe28`；审前 `git status --porcelain -uall` **0 行**；审后唯一改动 = 本审阅记录（reviewer 未提交 git）。
**① Kaiwu 9 行指针**：`grep -c 'DADAO-13 §1|DADAO-13 §2' spec/Kaiwu` = **0**；`0b98636c..HEAD` 该册 **9 增/9 删**，逐行 diff 只换指针（7 行 → `DADAO-12 §3.4`、2 行 → `DADAO-12 §4.1`；L74「定义见 HEE」→「定义见 `DADAO-12 §3.4`」），正文语义未动。
**② 版本与锁**：三册册头 `0.7.3-rc` / `0.1.4-rc` / `0.4.7-rc` 均未变；锁 `9e3e3b73…`、`6a39d003…`、**`6b26cd6f…`** 与三册实测 sha256 逐字节 **MATCH**。
**③ 不回归（reviewer 重跑）**：`run.sh` **rc=0 / TOTAL rc=0**，spec 组 **26/26** + Kaiwu 组 **4/4**，4 路注入各 FAIL（15 个 `[FAIL]`）→ restore rc=0 → 回绿；`check-linux-k2` **rc=0，PASS (104/104)**（77 s、0 FAIL；K0 119/119、K1 112/112）；`check-spec-drift/-changelog/-purity/-cite-targets/-refs/-readonly/-codeblocks/-numbering` + `check-cfx-aliases` + `check-cfx-alias-table` **10/10 rc=0**。
**③ 越界/只读**：`f78c78b9..HEAD` = **13 文件**（≤15；Kaiwu 已入白名单并在完成区「修改文件」列明）；`spec/SimRISC-*`/`tests/`/`components/`/`Makefile` 命中 **0**；主工作树 `git status` **0 行**、`.dadao/cross-toolchain` **0** 文件被改。
**④ 独立注入（非脚本④那行）**：把 Kaiwu **L166** 指针改回 `DADAO-13 §2` ⇒ `K1`+`K2` **FAIL rc=1**（现 md5 `d31b17f9…`）→ `cp` 还原 md5 `0ee26fe6…` 相等 ⇒ `check-kaiwu` rc=0、主组 rc=0；无 `git checkout/restore/stash/show`、无 `reset --hard`、无 `cmd | tee`。
**findings 闭合**：① ✅ 本轮收口并复核；③ ✅ 白名单口径已入硬约束 2；② `min_rom_probe_*` 注释级指针与 ④ `check-isa-coverage` 缺 `llvm-mc` 按完成区「遗留问题」**登记不改**（非阻断）。
**判决：Accepted（第 2 轮）** —— 4 条 finding 收口到位、不回归，留 architect 终审。

## 完成区

**测试结果**：证据脚本 spec 组 26/26 + Kaiwu 组 4/4 PASS（4 路注入均 FAIL → `cp`+md5 还原 → 回绿，`TOTAL rc=0`）；spec 门控 8 项 + `check-cfx-aliases`/`check-cfx-alias-table` 全 rc=0；`check-linux-k2` **PASS（104/104）**，含 K0 119/119、K1 112/112 回归（本 worktree 无安装根，跑门控时把只读安装根与组件源码软链进来，构建产物全部落在本 worktree）。
**修改文件**：
- `spec/DADAO-12-…md`：`§3.4` 占位换成 HEE `§1` 全文（cg3 表 10 数据行 + 四类 mask 段 + `rc10` 初值/写入段）；`§4.4` 迁入 hmon 说明段、原因表改引 `§4.1`/`§3.6`、删「详细定义见 HEE」；附录 `0.7.3-rc` 加内容条目。
- `spec/DADAO-13-…md`：`§1`/`§2` 只留标题 + 一行引用（编号作锚点）；`§3` 与附录其余条目不动；附录 `0.1.4-rc` 加内容条目。
- `.tao/contracts/contract-see.md`：cg3 4 处 + 原因表 14 处来源指针改指 `DADAO-12 §3.4`/`§4.1`、附录 A 两行、`§7` 一条；`contract-syscall.md` 3 处改指 `§3.4`。
- `.tao/contracts/contract-cfx-aliases.md`：投影重算（12 scalar / 36 specific / 1308 regs，计数不变）。
- `tools/linux/k2_trap_probe.py`：`spec_cause_table()` 改解析 `DADAO-12 ### 4.1 cfx_umon`（h3 边界截断），docstring 与 C3 标签同改；`tools/linux/check_k2.py`、`k3_page_probe.py`、`k3_pt_probe.py`（删未用失效常量）指针改指 `§4.1`。
- `tools/spec/gen_cfx_aliases.py`：来源说明改指 `DADAO-12`（含 `§3.4` cg3 表）。
- `spec/Kaiwu-测试机运行环境.md`：9 行活跃指针改指 `DADAO-12 §3.4`（7 行）/`§4.1`（2 行），正文语义不动；锁 `sha256` 同笔重算。
- `manifests/spec-readonly.lock.toml`：两册 `sha256` 重算 + 注记；本任务书。
**验收结果**：
- 内容无丢失：`§1` 说明段 5 行、表格 12 行、`§2` 说明段 1 行，逐行在 D12（0 缺失）；`§2` 原因表 0 行残留在 D13。
- 只留引用：`§1`/`§2` 表格行 = 0/0，正文行 = 1/1；D12 `§3.4` 数据行 10（rc0/rc10 均在位）。
- 门控：`check-spec-drift` / `-changelog` / `-purity` / `-cite-targets` / `-refs` / `-readonly` / `-codeblocks` / `-numbering`、`check-cfx-aliases`、`check-cfx-alias-table` 全 rc=0；锁哈希 `9e3e3b73…` / `6a39d003…` 与实测一致；`spec/README.md` 无 `sha256` 字段，无需更新。
- 注入：①删 `rc0` 行 ⇒ `B2/D1/D3/E3` FAIL；②贴回表格 ⇒ `A1/A3/A5/E3` FAIL；③解析目标回退 D13 ⇒ `G1/G2/G4` FAIL；④Kaiwu 指针改回 D13 ⇒ `K1–K4` FAIL；四者均 `cp`+md5 还原后回绿。
- 返工项：`spec_cause_table()` 返回 11 条且与 `contract-see §6.1` 逐项一致；`spec_exit_segments()`/`contract_freq()` 亦跑通；`tools/linux/**` 已无 D13 规格文件引用；`check-linux-k2` 全绿（E3/C3 标签已改指 `§4.1`）。
- Kaiwu 改指：`verify.py check-kaiwu` 4/4（`DADAO-13 §` 残留 0、「定义见 HEE」0、§3.4 活跃行 7）；注入④改回 D13 ⇒ K1–K4 全 FAIL → 还原回绿；锁 `6b26cd6f…` 与实测一致。
**版本号**：未变（`0.7.3-rc` / `0.1.4-rc`，按用户 2026-11-17 规则）。
**新发现/坑**：
1. `-rc` 段版本只能 = 下一发布段 z+1；0.7.3/0.1.4 未发布时直写 0.7.4-rc/0.1.5-rc 必 FAIL，且 SEE↔SBI、HEE↔HBI 互锁要求 4 册同升 ⇒ 版本升级 = 先发布 + 互锁同步。
2. 事实源迁册会切断按 h2 标题切册的解析器；标题层级（h2→h3）也须随目标段调整，否则截断越界。
3. 生成器的来源说明是硬写字符串，不随解析来源变化 ⇒ 重算后会失真，需与解析器同笔更新。
**遗留问题**：（reviewer finding ②，登记不改）`tools/testcases/arch/min_rom_probe_*.py`、`tools/chipyard/excp/check_log.py` 等注释级指针仍写 `DADAO-13 §1/§2`——不影响门控、锚点仍在，按范围不扩；（reviewer finding ④）`check-isa-coverage` 仍因本 worktree 缺 `llvm-mc`（`make install-host`）跑不了（先存环境限制）。另：`check-knowledge-refs` 红的 1 条在他人任务书 `m16-chipyard-001`（先存，`git diff` 未触及）。

