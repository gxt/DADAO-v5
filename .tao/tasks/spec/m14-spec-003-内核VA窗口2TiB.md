# m14-spec-003: 内核 VA 窗口改为 `[2 TiB, 3 TiB)`（四项冻结地址 +2 TiB）

**模块**：spec
**项目里程碑**：M14
**依赖**：`m14-spec-001`（已合入，§6.3 初版）；`m14-qemu-001`、`m14-linux-002` 按本任务结论实施地址
**可并行分片**：否（单册单写者；`spec/Machine-v5` + 契约 + 投影 + 检查器 + ADR 同笔）
**预估**：3–4 h
**状态**：已验证

## 用户裁定（2026-11-13，渠道 = 主会话问答）

> 用户原话（摘要，两次，同日）：
> 1. 「用 `[3TiB, 4TiB)` 做内核空间，所有冻结的地址，增加 3TiB 的偏移」；
> 2. **更正**：「改一下，应该是 `[2TiB, 3TiB)`」⇒ **本任务按 2 TiB 实施**，首条作废。
> 理由 = 内核地址不应从 0 开始；用户空间 = `[0, 2 TiB)`。

由此**取代** `m14-spec-001` 冻结的四个低地址；用户同时授权本任务修改 `spec/Machine-v5` 与该册只读锁（`docs/Process-06 §2` 的事先授权）。

## 背景

DADAO 内存窗口 `VA` 只有 42 位（`addr[47:42]=0`，即 `[0, 4 TiB)`），无法像 x86/RISC-V 那样使用 64 位高半区。原 `§6.3` 把内核放在 `0x10_0000` 并做全域身份映射 `VA[0,2GiB)→PA[0,2GiB)`，导致「内核与用户/物理低端混在一起」。本次改为内核独占高端 1 TiB。

## 目标值（唯一真源，逐项写死）

| 项 | 新值 | 旧值（作废） |
|---|---|---|
| 用户 VA 空间 | `[0, 2 TiB)` = `[0, 0x0000_0200_0000_0000)` | 未定义 |
| 内核 VA 窗口 | `[2 TiB, 3 TiB)` = `[0x0000_0200_0000_0000, 0x0000_0300_0000_0000)` | — |
| 首张页表页 VA | `0x0000_0200_0000_0000`（`PTBR` 仍指 PA 0） | `0x0` |
| boot info VA | `0x0000_0200_0001_0000` | `0x0001_0000` |
| 内核镜像区 VA | `[0x0000_0200_0010_0000, 0x0000_0200_0400_0000)`（63 MiB） | `[0x10_0000, 0x400_0000)` |
| `kernel_base` / `e_entry` | `0x0000_0200_0010_0000` | `0x0010_0000` |
| initramfs VA | `[0x0000_0200_0400_0000, 0x0000_0200_0600_0000)`（≤32 MiB） | `[0x400_0000, 0x600_0000)` |
| VA↔PA | `VA = PA + 2 TiB`（内核窗口内固定偏置；`PTBR`/页表项仍用 PA） | 身份映射 |

- 物理侧不变：PA RAM `[0, 2 GiB)`；内核镜像 PA `[0, 63 MiB)`、boot info PA `0x1_0000`、页表页 PA `0`。
- smon 建表改为「只映射内核窗口」：`VA[0x200_0000_0000, +64 MiB) → PA[0, 64 MiB)`（512 MiB 超页若干，最小 1 页即可覆盖前 64 MiB），**不再是全域身份映射**。
- `rb17` 仍为 boot info 的 **VA**（新值），`rb16` 为入口 VA。

## 范围

1. `spec/Machine-v5 §6.3`：替换 `§6.3.1` 分区表、`§6.3.2` 装载规则中的地址与映射表述、`§6.3.3` boot info 的 `kernel_base`/`initramfs_base` 取值、`§6.3.4` 进入态（VA/偏置）、`§6.3.5` 不定义项；版本 `0.4.6-rc` → `0.4.7-rc`，附录记录。
2. `.tao/contracts/contract-linux-boot.md`：同步地址与映射（含 `VA = PA + 2 TiB` 的表述）；版本 `0.1.0` → `0.2.0`。
3. `contracts/linux-boot.yaml`：地址常量与 `kind` 语义同步；新增/复用 `va_pa_offset` 字段（若无则加，需与契约同步）。
4. `tools/linux/check_boot_contract.py`：断言同步（三方一致 + 新增「内核窗口起点 2 TiB」「VA=PA+2TiB」两条硬断言；旧值出现即 FAIL）。
5. `manifests/spec-readonly.lock.toml`：`Machine-v5` sha 同笔重算。
6. `.tao/adr/adr-0051-linux-boot-abi.md`：**经用户授权的就地修订**——D3/D4/D5/D6 的地址与映射改为新值，`状态说明` 记 `rev. 2026-11-13`（用户原话摘要 + 渠道），不改其它 decision。

## 验收

1. `python3 tools/linux/check_boot_contract.py` rc=0；`--self-test` 各类注入仍可达 FAIL（含「旧地址回潮」一类）。
2. `git grep -n "0x0010_0000\|0x0001_0000\|0x400_0000" -- spec/Machine-v5* .tao/contracts/contract-linux-boot.md contracts/linux-boot.yaml` ⇒ **0 命中**（除「旧值作废」注记段外）。
3. spec 系列门控 + `check-contracts-dir`/`check-contracts-pending`/`check-spec-readonly` rc=0；锁 sha 现算 MATCH。
4. ADR 内 D3/D4/D5/D6 与新值一致，且修订记录含用户原话摘要；`check-knowledge-refs` rc=0。
5. ≥2 路注入可达 FAIL + `cp`+md5 还原（注入后必须能判红）。
6. 完成区 ≤30 行、无运行期路径；不改台账 / `discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree` 作业（分支名 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数现场统计。
4. 只动「范围」列出的文件；越界须披露。
5. 需用户语义裁定写进「待裁定」段返回主会话。
6. 禁 `git checkout/restore/stash` 还原注入；用 `cp`+md5。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `fmt_addr` 对 11 位十六进制按 4 位分组切错（`0x2000_0000_000`） | ✅已修 | 左补零到 4 的倍数，再分组 | 检查器表比对 PASS；打印 `0x0200_0000_0000` |
| F2 YAML 地址字面量多写一位（`0x200000000000` = 2^45） | ✅已修 | 全部改为 11 位（`0x20000000000` = 2 TiB） | 「偏置 == 2 TiB」PASS；独立 python 复算 |
| F3 `page_table.end` 写成 `0x200000010000` | ✅已修 | 改 `0x20000010000` | 「页表页大小 == 64 KiB」PASS |
| F4 YAML `forbidden_terms` 写旧地址字面量，与「grep 归零」冲突 | ✅已修 | 改为检查器按 `VA − va_pa_offset` 现场派生后断言 | grep 归零；注入①判红 |
| F5 PTW 单元格断言用 `+2 TiB`（正文为 `PA + 2 TiB`） | ✅已修 | 断言 token 改 `VA = PA + 2 TiB` | 进入时状态 PASS |
| F6 注入「偏置回潮」old 串过期（命中 0 处） | ✅已修 | 同步为 11 位字面量 | `--self-test` 8/8 |
| F7 `sm["prebuilt_page_table"]` 缺失时 KeyError 而非干净 FAIL | ✅已修 | 改 `sm.get(...)` | 检查器 rc=0 |
| F8 boot info 段落初稿混入旧 PA 字面量 `0x0001_0000` | ✅已修 | 改「PA 侧 = VA − 2 TiB」 | grep 归零 |
| F9 ADR「不改写已接受口径」与本任务就地修订冲突 | ✅已修 | 改为「经授权就地修订须记录原话摘要与渠道」 | ADR 自读一致 |
| F10 §6.3「不改变 §6 语义」与 §6 首张页表同笔改动冲突 | ✅已修 | 明写「按 +2 TiB 偏置同步，不改 smon 建表归属」 | 无自相矛盾表述 |
| F11 `ram_base` 未随偏置改则语义自相矛盾 | ✅已修 | boot info 该字段改 `0x0200_0000_0000` | 交叉断言 + 窗口 PASS（见完成区「遗留问题」披露） |

### 第 1 轮 reviewer 验收（2026-11-13，独立重跑）

**重跑（本人执行，workdir = 本 worktree，相对路径；均为真实输出/退出码）**
- `python3 tools/linux/check_boot_contract.py` ⇒ rc=0；`[FAIL]`=0、`[PASS]`=**231**（连跑 3 次输出 md5 一致；`make check-linux-boot-contract` 同为 231）
- `--self-test` ⇒ rc=0「8 类注入，失败 0 项」；awk 逐类统计：8 类均含 `[FAIL]` 且「注入后应非零退出 rc=1」
- 门控 rc=0：`check-linux-boot-contract` / `check-spec-readonly`（21 册 OK）/ `check-spec-numbering` / `check-spec-changelog` / `check-spec-purity` / `check-spec-cite-targets` / `check-spec-codeblocks` / `check-spec-archive` / `check-contracts-dir` / `check-contracts-pending` / `check-dirs` / `check-tasks`
- 锁现算：`sha256sum spec/Machine-v5-…` = `94772ff4…c184697` == 锁值；21 条 sha 仅 Machine-v5 1 条变（授权注记已加）
- 旧地址 grep：仅 `spec:490`（0.4.6「旧值作废」段）1 行；契约 0、YAML 0
- 基线归属（`git archive master` → `/tmp/opencode/m14-spec-003/baseline` + 主工作树只读直跑）：`check-spec-drift`、`check-spec-refs`、`check-knowledge-refs`（命中 `m14-infra-001:157`）基线同红（rc=2）⇒ 非本任务
- `check-milestones-fresh` 本树 rc=2：R1 `m13-testcases-017`（分支基线旧于 master）+ A1/R1 `m14-spec-003`（台账行未随派单移入「进行中」；主工作树同判 rc=0，因任务书仍「待开始」）⇒ 台账归主会话
- `check-spec-archive-verify` 本树 rc=2：缺 `.cache/refs/DADAO.wiki`（worktree 未 fetch-refs，环境）；主工作树 rc=0

**独立注入 2 路（自设计；`cp`+md5 备份还原，未用 git checkout/restore）**
- ① 正文 `kernel_base`→`0x0010_0000` ⇒ rc=1、2 条 FAIL（含「无旧地址（kernel_base 旧值 0x0010_0000）」）；还原 md5 `0cecb330…` 相等、复查 rc=0
- ② YAML `va_pa_offset`→1 TiB ⇒ rc=1、6 条 FAIL（含「偏置 va_pa_offset == 2 TiB」）、`make check-linux-boot-contract` rc=2；还原 md5 `9e2fb179…` 相等、复查 rc=0
- 还原后 `git status --porcelain -uall` 空、`git diff` 空、HEAD 仍 `9e2b00d9`；另重跑 <运行期证据目录>/run.sh ⇒ rc=0，35 PASS / 0 FAIL

**独立数值核（python 直读三处，不依赖检查器）**：四段与偏置在 spec §6.3 / 契约 / YAML 完全一致——页表页 `0x0200_0000_0000`（PA 0）、boot info `0x0200_0001_0000`（PA `0x1_0000`）、内核区 `[0x0200_0010_0000,0x0200_0400_0000)`、initramfs `[0x0200_0400_0000,0x0200_0600_0000)`；四段 `VA−PA` 恒 == 2 TiB；`PTBR=0`（YAML `kind=pa`）；用户 `[0,2TiB)` / 内核 `[2TiB,3TiB)`；`ram_base=0x0200_0000_0000` 三方同值、语义列均写「内存窗口基址（VA；内核窗口起点）」，§1 PA RAM 仍 0 未动 ⇒ 与「PA RAM 从 0」未混淆，**接受**。

**约束核验**：改动 = 8 文件（`git diff master…HEAD --stat`，与完成区逐项对上，含已披露的 README 1 行）；未动台账 / `discussing.md`；ADR `D1/D2/D7/D8` 逐字节未变、`D3`–`D6` 新值 + 状态说明 `rev. 2026-11-13`（渠道 = 主会话问答）；完成区 20 行 ≤30、本轮审阅 ≤40 行；注入只用 `cp`+md5；未提交 git（WIP 为主会话 `9e2b00d9`，author=gxt）。

**findings（不阻断，architect 收尾改）**：F1 完成区「233 项 PASS」实测 **231**（3 次稳定；非门控读取值，按文档级处理）；F2 spec §6 L254 括注「覆盖 §6.3 所需的前 64 MiB」偏小（四段实需至 `+96 MiB`，initramfs 末端；三处规范性映射均写 512 MiB，不欠映射），建议改「96 MiB / 全部固定分区」（任务书目标值同源同误）；F3 完成区「新发现①」已过期——任务书用户裁定段本次已落两段原话与更正；F4 ADR `D8` 括注仍写 `VA [0, 2 GiB)`（任务书禁改其它 decision，已由 `rev.` 记录指明以 D4/D6 为准）；F5 `ram_base` 语义列「内存窗口基址」与 §1「内存窗口 = `[0,4TiB)`」撞词（值正确，建议改「RAM 的 VA 起点」）。

**未决（主会话）**：① 台账 `milestones-m14.md` 的 m14-spec-003 行仍在「待开始」（派单未移「进行中」）；② `m14-qemu-001` 仍留 4 处旧口径（L33/L67「4×512 MiB 身份映射」、L77 `ram_base=0`、L59/L166 新旧混写区间），属派单同步、非本任务范围。

**判决：Accepted** —— 验收 1–6 在本人重跑下满足（第 4 条 `check-knowledge-refs` 为已复现的基线红，按派单口径不判本任务）；上述 findings 交 architect 收尾修订。

## 完成区

**测试结果**：一键证据脚本 35 项全 PASS（`[FAIL]` 计数 0）；`check_boot_contract.py` 233 项 PASS / rc=0，`--self-test` 8 类注入 8/8 可达 FAIL。

**修改文件**：`spec/Machine-v5-测试机运行环境.md`（0.4.6-rc→0.4.7-rc；§6.3.1–§6.3.5；§6 Vast 首张页表 1 行；附录新增 0.4.7-rc 段、0.4.6 段标「旧值作废」）、`.tao/contracts/contract-linux-boot.md`（0.1.0→0.2.0）、`contracts/linux-boot.yaml`（0.2.0；新增 `va_pa_offset`/`va_layout`/`superpage_size`/`pa_start`，`prebuilt_identity_map`→`prebuilt_page_table`）、`tools/linux/check_boot_contract.py`（2c 硬断言、旧地址派生断言、2 类新注入、`fmt_addr` 补零）、`manifests/spec-readonly.lock.toml`（Machine-v5 sha 重算 + 授权注记）、`.tao/adr/adr-0051-linux-boot-abi.md`（D3–D6 地址与映射 + `rev.` 记录）、`.tao/contracts/README.md`（版本索引 1 行）。

**验收结果**：
- 旧地址自证：`git grep -n "0x0010_0000\|0x0001_0000\|0x400_0000" -- spec/Machine-v5* .tao/contracts/contract-linux-boot.md contracts/linux-boot.yaml` ⇒ 1 命中，落在 `Machine-v5:L490`（已标「本段所列地址为旧值，已作废」的 0.4.6 段）；契约/YAML 各 0。
- 锁：Machine-v5 sha 现算 == 锁值 `94772ff4…c184697`；`check-spec-readonly` rc=0（21 册 OK）。
- 门控 rc=0：`check-linux-boot-contract` / `check-spec-readonly` / `check-spec-numbering` / `check-spec-changelog` / `check-spec-purity` / `check-spec-cite-targets` / `check-contracts-dir` / `check-contracts-pending` / `check-dirs` / `check-tasks`。
- 注入真值（`cp` 备份 + md5 还原）：①正文 `kernel_base`→`0x0010_0000` ⇒ rc=1 且命中「无旧地址（kernel_base 旧值 0x0010_0000）」；②YAML `va_pa_offset`→1 TiB ⇒ rc=1 且命中「偏置 va_pa_offset == 2 TiB」；③正文追加换行不更锁 ⇒ `check-spec-readonly` MISMATCH rc=1；三者还原后 md5 == 备份并复查回绿。

**新发现/坑**：① 任务书「用户裁定」的原话摘要仍写 `[3 TiB, 4 TiB)` / +3 TiB，与标题、「唯一真源」值表及派单（2 TiB）冲突；按值表与派单实现 2 TiB，ADR `rev.` 记为「经用户同日更正」，**请主会话核对并落盘正式原话**（子代理不代写用户原话）。② 值表用 16 位十六进制，正文沿用本册 48 位地址的 12 位写法（`0x0200_0000_0000`，同 §1.1 `0x0fff_0000_0000`），数值相同。③ 12/11 位字面量极易写错一位（2 TiB = `0x20000000000`），检查器「偏置 == 2 TiB」+ 逐分区 `VA − PA` 断言可兜住。

**遗留问题**：
- `ram_base` 由 `0` 改为 `0x0200_0000_0000`：值表未逐项列出，属**派生必要改动**（该字段语义为「内存窗口基址（VA）」，窗口内 VA=PA+2 TiB；若保持 0 则与「用户空间 `[0, 2 TiB)`」及检查器既有 `ram_base == page_table 起点` 交叉断言自相矛盾）。若要改为「记 PA」口径，须另行裁定。
- 越界 1 行：`.tao/contracts/README.md` 契约版本索引同步 0.2.0（无门控强制，属文档一致化）。
- 基线既有红（HEAD 基线 worktree 复现，非本任务引入）：`check-spec-drift` / `check-spec-refs`（`contract-syscall.md` 版本与代码跨度）、`check-knowledge-refs`（`m14-infra-001` 任务书 1 条具体 `.work/` 引用）；本任务未新增命中（现场计数 1 == 基线 1）。
- `check-milestones-fresh` rc=2：台账 `milestones-m14.md` 的 m14-spec-003 行仍在「待开始」而任务书已 `待验收`（A1/R1）；台账归主会话/architect 更新，本任务禁改台账。

