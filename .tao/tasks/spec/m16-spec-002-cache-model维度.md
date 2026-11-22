# m16-spec-002: CACHE-27 补 `cache-model` 维度

**模块**：spec
**项目里程碑**：M16
**依赖**：`m16-spec-001`（cfx5 契约）已合入
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景（用户 2026-11-22 已认可契约变更）

用户裁定：Linux 内核缺省带 cache 维护逻辑（其它 ISA 不会为“无 cache”单独编译内核），机器配置只决定 cfx5 有没有效果，不决定它是否存在。

- `cache-model=off`：cfx5 **存在但 no-op**——`cache_exist` 读 0，`cache_ctrl` 写被接受、不报 `CFXREG`、不产生效果；
- `cache-model=on`：`cache_exist=0b11`，命令真维护；
- RTL Vast 始终有 cfx5，Tiny 无（不跑 Linux）。

当前 `contracts/contract-cache.md` 的 CACHE-27 未写这个机器维度，需要补。

## 要做

1. `contracts/contract-cache.md`：在 CACHE-27（cfx5 寄存器/命令语义）处补 `cache-model` 维度：
   - `off`：cfx5 存在；`cache_exist` 读 0；`cache_enable`/`cache_ctrl`/`cache_addr_start`/`cache_addr_size` 可访问但无效果；`cache_ctrl` 合法编码不报异常、不产生维护动作；
   - `on`：`cache_exist=0b11`；寄存器与命令按 CACHE-03…CACHE-27 生效；
   - 其他机器维度（若有）不在此展开。
2. 同步 `contract-cache` 的索引/引用（如有 `CACHE-nn` 清单），不升版本号（用户未要求）。
3. 给出需要同步的探针清单：`integ042t cfx5_cache_cfxreg` 的期望要从 `CFXREG` 改为 no-op；由 `m16-qemu-001` 返工同步，不在本任务改探针。

## 不做

- 不改 QEMU/gem5/RTL 实现；
- 不改 `integ042t`（由 qemu-001 返工）；
- 不升 `spec/`/contracts 版本号。

## 约束

- 独立 `git worktree`；**不提交 git**；
- 变更集限 `contracts/contract-cache.md`、本任务书；
- 术语「寄存器组」；不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. `git diff` 只含 `contracts/contract-cache.md` 与本任务书；CACHE-27 新增段落包含 `cache-model=off` 与 `on` 两个分支；
2. `make check-contracts-*`（现场确认目标名）与 `check-spec-refs`、`check-knowledge-refs` 记录 rc；
3. **可达 FAIL**：删掉 `off` 分支 ⇒ 引用/断言检查红；`cp`+md5 还原后回绿；
4. 不升版本号：`git diff` 无版本号变化。

## 完成区

**测试结果**：运行期证据目录 `run.sh` 默认模式 **8/8 PASS（rc=0）**；`run.sh --inject` **3 路注入 / 6 项 PASS（rc=0）**（删 off 分支、off 改回「可读写」、删非法编码句——各自断言红后 `cp`+md5 还原回绿）。
**修改文件**：`.tao/contracts/contract-cache.md`（CACHE-27 + 头部来源/范围 + §8 变更记录）、本任务书。**未提交 git**。
**验收结果**：
- 变更集 = 上述 2 文件（`git diff --name-only` + 未跟踪现场统计，脚本断言 ⊆ 白名单）；
- CACHE-27 段落现场计数：`cache-model=off` 分支 1 行、`cache-model=on` 分支 1 行；off 含「`cfx5` 存在 / `cache_exist` 读 0 / 不报 `CFXREG` / `cache_ctrl`（WO，只写）可访问 / 合法编码不报异常、不产生维护动作 / 编码与 `addr_size` 校验不受 `cache-model` 影响、非法仍 ⇒ `CFXREG`」，on 含「`cache_exist` 读回 `0b11` / 按 CACHE-03…CACHE-27 生效」；
- 版本不升：版本头仍 `**版本：0.7.1**`，`git diff` 无 `版本：` 行变更；
- 门控 rc：`check-spec-refs`=0、`check-contracts-dir`=0、`check-contracts-pending`=0、`check-contract-relocs`=0、`check-spec-drift`=0、`check-tasks`=0；`check-knowledge-refs` 脚本 rc=1（make rc=2）= **KNOWN-RED**，悬空集与 HEAD 基线（`git archive HEAD` 临时树）**逐行相同**：`.tao/knowledge/MEMORY.md:15`、`.tao/knowledge/milestones-m18.md:39` 的 `ADR-0059` 目标缺失，非本改动；
- 探针生成器 `tests/arch/cache/check_cfx5_regs.py --expected` rc=0，首条 `exist (RO)=0x3`（off 措辞未劫持 `0b11` 解析）；
- 可达 FAIL 实测（3 路）：删 off 分支 ⇒ `off 分支行数 0`；off 改回“`cache_ctrl`/… 可读写” ⇒ 报「缺 WO（只写）」+「仍写可读写」；删非法编码句 ⇒ 报「缺 校验不受影响」+「缺 非法仍 ⇒ `CFXREG`」；三路 `cp` 还原后 md5 `f74e8b5f8223acc5a03f90d12ba54cea` 均一致且断言回绿。
**新发现/坑**：① 契约实际落点是 `.tao/contracts/contract-cache.md`（任务书写 `contracts/`）；根 `contracts/` 顶层由 `check-contracts-dir` 只允许 `*.yaml`、`contract-*.md` 已迁出，故按实际落点改、未动 `contracts/`。② `check_cfx5_regs.py:88` 用**全局**正则 `` `cache_exist` 读回 `0b([01]+)` `` 派生 Vast 期望：off 分支若写「读回 `0b00`」会先命中并把它静默改成 0 ⇒ off 只写「读 0」，并加「`--expected` 首条 = 0x3」守卫。③ `check-knowledge-refs` 基线即红，判据取「悬空集与 HEAD 树逐行相同」，不按 rc 单独判绿。
**遗留问题**：
- **返工补记（第 2 轮，用户 2026-11-22 裁定）**：`cache-model=off` 下非法编码仍 ⇒ `CFXREG`（校验不受机器维度影响）已补进 CACHE-27；第 1 轮「待裁定」项闭环。
- `m16-qemu-001`（现 `待验收`）任务书仍写「off ⇒ cfx5 寄存器按 `CFXREG`」，与本合约冲突；按本任务「要做 3」由 `m16-qemu-001` 返工同步（其完成区「exist 无可观测路径」的疑问也由「off 下 `cache_exist` 读 0」解除）。
- `integ042t cfx5_cache_cfxreg` 期望需从 `CFXREG` 改为 no-op（本任务不改探针，按任务书交 qemu-001 返工）。
- `tests/arch/cache/README.md` 与各组件 `changelog.md` 仍是旧口径，随对应返工任务同步，本任务未动。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 off 写「`cache_exist` 读回 `0b00`」会劫持 `check_cfx5_regs.py` 全局正则，把 Vast 期望静默改成 0 | ✅已修 | off 改「`cache_exist` 读 0」，on 保留「读回 `0b11`」 | `--expected` rc=0、首条 `exist=0x3`；`chk_probe_derivation` PASS |
| F2 「寄存器可访问」无限定，易读成 off 下任意 rc 不报 `CFXREG`（与 CACHE-04 冲突） | ✅已修 | 限定「CACHE-03 的五个寄存器…（其余 rc 仍按 CACHE-04 处理）」 | 文本断言 PASS；`check-spec-refs` rc=0 |
| F3 「寄存器面恒在」与 CACHE-28（Tiny 无 cfx5）易生歧义 | ✅已修 | 改为「Vast 的寄存器面恒在」 | 重跑 `run.sh` 全绿 |
| F4 头部「来源/来源标注」只写 2026-11-20，新增维度来源不可追溯 | ✅已修 | 「2026-11-20 与 2026-11-22」/「2026-11-20 起，含 2026-11-22 的 `cache-model` 补记」 | `git diff` 已载；`check-spec-refs` rc=0 |
| F5 契约改动无变更记录，版本不升会失去授权可追溯 | ✅已修 | §8 增 2026-11-22 条目（版本不变 + 授权原话 + Process-02 依据），措辞避开 Check 2 规范词 | `check-spec-refs` rc=0；`check-contracts-pending` rc=0 |
| F6 证据脚本 `run_all` 花括号错位、`chk_gate` 参数冗余 | ✅已修 | 修 `run_all` 闭合；`chk_gate` 收为单参数 | `bash -n` rc=0；`run.sh` rc=0 |
| F7 off 下非法编码口径未定 | ✅已修（第 2 轮） | 用户 2026-11-22 裁定「校验不受机器维度影响、非法仍 ⇒ `CFXREG`」，已补入 CACHE-27 | `run.sh` 分支断言 + `drop-cfxreg` 注入红/还原绿 |

### 第 2 轮 engineer 自审（返工：reviewer Accepted 后用户补裁）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1 off 分支缺用户裁定的「非法编码仍 ⇒ `CFXREG`」，实现方可能据此取消校验 | ✅已修 | CACHE-27 off 补「`cache_ctrl` 的编码与 `addr_size` 校验不受 `cache-model` 影响；非法编码（`[3:2] = 11`、PA 区间且 `size = 0` 等）仍 ⇒ `CFXREG`」 | `check-spec-refs` rc=0；`drop-cfxreg` 注入 ⇒ 两条断言红、还原回绿 |
| R2 off 写 `cache_ctrl`「可读写」，与 CACHE-03 的 **WO** 冲突 | ✅已修 | 改「`cache_ctrl`（WO，只写）/`cache_addr_start`/`cache_addr_size` 可访问」 | `off-rw-wording` 注入 ⇒ 「缺 WO / 仍写可读写」红；还原回绿 |
| R3 新增两条语义断言无独立可达 FAIL 证据（仅「删整行」一路） | ✅已修 | `--inject` 扩为 3 路（`delete-off` / `off-rw-wording` / `drop-cfxreg`），各自 `cp`+md5 还原 | `--inject` rc=0，6 项 PASS；md5 三路还原均 `f74e8b5f…` |
| R4 §8 变更记录只写「合法命令」，未记非法编码口径 | ✅已修 | §8 条目补「编码与 `addr_size` 校验不受该维度影响、非法仍 ⇒ `CFXREG`」 | `check-spec-refs` rc=0；`check-contracts-pending` rc=0 |

### 第 1 轮 reviewer 验收（2026-11-22）

**分析文件**：`contract-cache.md`（CACHE-03/04/07/08/14/23/27/30、头部、§8）、本任务书、运行期证据目录内 `run.sh`、`tests/arch/cache/check_cfx5_regs.py`、discussing M16 `cache-model` 条目。

**契约核验**：off 分支与用户口径逐条一致——`cfx5` 存在、CACHE-03 五寄存器可访问不报 `CFXREG`（其余 rc 按 CACHE-04）、`cache_exist` 读 0（引 CACHE-07：写 1 读回 0）、合法 `cache_ctrl` 不报异常且不产生维护动作；on = `cache_exist` 读回 `0b11`、按 CACHE-03…CACHE-27 生效；来源标注 `[spec-decision]` + `Machine-01 §3.2` 齐；头部来源/范围/来源标注已同步 2026-11-22 补记。

**版本号**：第 3 行仍 `**版本：0.7.1**`；`git diff -U0 | grep '版本：'` rc=1（无版本行变更）；§8 新增 2026-11-22 条目（版本不变 + 授权原话 + Process-02 依据）。

**变更集**：`git diff --name-only` = 契约 + 本任务书；未跟踪为空；任务书无运行期目录引用、无绝对路径（grep rc=1）；无「银行」术语。

**重跑记录（仓库根，我方独立执行）**：
- 运行期证据目录内 `run.sh`：**rc=0，8/8 PASS**（3 门控 rc=0；KNOWN-RED 悬空集与 `git archive HEAD` 基线逐行相同 = `MEMORY.md:15`、`milestones-m18.md:39` 的 ADR-0059；`check_cfx5_regs.py --expected` rc=0、首条 `exist (RO)=0x3`）；
- `run.sh --inject`：**rc=0，2/2 PASS**——删 off 分支 ⇒ `[FAIL] chk_cache27_branches（off=0 on=1）`，还原后 md5 `eb600c6a1266f562fa203f5aebc55307` 与注入前一致、断言回绿；
- 门控独立重跑：`check-spec-refs`=0、`check-contracts-dir`=0、`check-contracts-pending`=0（run.sh 内）、`check-contract-relocs`=0、`check-spec-drift`=0、`check-tasks`=0（①漏收尾 1 = 本任务待验收，报告型）、`check-knowledge-refs` make rc=2 / 脚本 rc=1（悬空 2 条；我方另建 HEAD 归档树复算，悬空集与当前**逐行相同** ⇒ KNOWN-RED，非本改动）。
- 完成区所列数字与退出码与我方实测**逐项一致**。

**待裁项判定（`off` 下非法编码是否仍 `CFXREG`）**：**应写进契约，但须用户裁定后写入**——① 现文本无矛盾：off ⇒ `cache_exist`=0 ⇒ `cache_enable`=0（CACHE-07），即落入 CACHE-08「校验不受使能影响、非法即 `CFXREG`」，CACHE-14/23/30 也无机器维度豁免，故可推得「off 下非法仍 `CFXREG`」；② 但 CACHE-08 措辞只限「使能位」，off 是**机器维度**，QEMU/gem5/RTL 三方有分叉风险，宜补一句仿 CACHE-08 的「编码与 `addr_size` 校验不受 `cache-model` 影响」；③ 用户 2026-11-22 口径只覆盖「合法编码」，契约语义增补须用户认可 ⇒ **记 finding 交主会话转用户**（engineer F7「不擅自扩语义」处理正确）。附带非阻断 finding：off 分支写 `cache_ctrl`「可读写」，CACHE-03 定其 WO，建议随裁定一并改「可访问（WO 只写）」。

**判决：Accepted**——验收命令在我方重跑下全部通过、变更集/版本号/来源标注等硬约束无违反；上述 finding 交用户裁定，不阻断本轮。

### 第 2 轮 reviewer 验收（2026-11-22，返工复核）

**两条 finding 核验**
- R1「off 下非法编码仍 `CFXREG`」**已落进契约正文**：CACHE-27 off 分支现含「`cache_ctrl` 的**编码与 `addr_size` 校验不受 `cache-model` 影响**，非法编码（`[3:2] = 11`、PA 区间且 `size = 0` 等）仍 ⇒ `CFXREG`」（现场 `grep -c` = 1）；与 CACHE-08「编码与 `addr_size` 的校验**不受使能影响**（仍按 CACHE-11 判序执行，非法即 `CFXREG`）」同构同义——维度词由「使能」换「`cache-model`」，非法例取自 CACHE-14。§8 2026-11-22 条目同步「编码与 `addr_size` 校验不受该维度影响、非法仍 ⇒ `CFXREG`」（`grep -c` = 1）。
- R2「`cache_ctrl` 可读写」**已改**：off 分支现为「`cache_ctrl`（WO，只写）/`cache_addr_start`/`cache_addr_size` 可访问」，与 CACHE-03 `cfx_cache_ctrl` = `cg8 rc9`（WO、写即执行）一致；契约全文 `grep '可读写'` rc=1（无残留）。
- 版本号未升：第 3 行仍 `**版本：0.7.1**`；`git diff -U0 | grep '版本：'` rc=1。

**重跑记录（仓库根，我方独立执行）**
- 运行期证据目录内 `run.sh`：**rc=0，8/8 PASS**（`check-spec-refs`/`check-contracts-dir`/`check-contracts-pending` 各 rc=0；`check-knowledge-refs` KNOWN-RED 悬空 2 条与 `git archive HEAD` 归档树**逐行相同** = `MEMORY.md:15`、`milestones-m18.md:39` 的 ADR-0059；`check_cfx5_regs.py --expected` rc=0、首条 `exist (RO)=0x3`）。
- 运行期证据目录内 `run.sh --inject`：**rc=0，3 路 / 6 项 PASS**——`delete-off` ⇒ `[FAIL] off/on 分支缺失或重复（off=0 on=1）`；`off-rw-wording` ⇒ 「缺 WO（只写）」+「仍写可读写」；`drop-cfxreg` ⇒ 「缺 校验不受影响」+「缺 非法仍 ⇒ `CFXREG`」；三路 `cp` 还原 md5 均 `f74e8b5f8223acc5a03f90d12ba54cea`、断言回绿。与完成区所列数字/退出码**逐项一致**。
- 门控独立重跑：`check-spec-refs`=0、`check-contracts-dir`=0、`check-contracts-pending`=0、`check-contract-relocs`=0、`check-spec-drift`=0、`check-tasks`=0（①漏收尾 1 = 本任务待验收，报告型）；`check-knowledge-refs` make rc=2 / 脚本 rc=1，我方另建 HEAD 归档树复算 `diff` 空 ⇒ 悬空集逐行相同 = KNOWN-RED，非本改动。

**独立注入（我方自行改被测产物，非脚本自带模式）**：`cp` 备份 + 记 md5 `f74e8b5f8223acc5a03f90d12ba54cea` → 自行删去 off 分支「校验不受影响 / 非法仍 ⇒ `CFXREG`」句（注入后 md5 `7b2b54129e47586268dc70ebba454643`）→ 重跑同一 `run.sh` ⇒ **rc=1**、`[FAIL] chk_cache27_branches`（缺两条要件）→ `cp` 还原 → md5 回 `f74e8b5f8223acc5a03f90d12ba54cea` → 重跑 **rc=0 全绿**；`git status --porcelain -uall` 与注入前快照逐行相同（仅契约 + 本任务书），无残留。

**约束核验**：变更集 = `.tao/contracts/contract-cache.md` + 本任务书、未跟踪为空；版本未升；任务书/审阅记录无运行期与绝对路径（grep rc=1）；无「银行」；`bash -n` run.sh rc=0；各断言均有可达 FAIL（3 路注入实测），无恒真、无同源自比（基线取 `git archive HEAD` 独立树）。

**非阻断观察**：CACHE-08 在「不受影响」后引「仍按 CACHE-11 判序执行」，CACHE-27 off 未引判序、以非法例代之；因「非法编码」已由 CACHE-14 限定（选中至少一侧且操作非 `none`），不构成矛盾，建议后续统一措辞时补引 CACHE-11。

**判决：Accepted**——两条 finding 均真实落进契约正文、措辞与 CACHE-08 一致、版本未升；验收命令在我方重跑下全部通过、独立注入可红可还原回绿、硬约束无违反。
