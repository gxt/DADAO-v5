# m14-linux-015: K3 收口门控 `check-linux-k3`（TLB 四类 + 分页/零页/栈 + K2 不回归 + §4a 退役）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-qemu-005`、`m14-testcases-005`、`m14-linux-011`、`m14-linux-012`（全部 `已验证`）。**`m14-linux-013`（COW）与 `m14-linux-014`（栈增长）均已退役、全归 K4** ⇒ K3 门控**不含** COW 组与栈组
**可并行分片**：否（单一端到端门控；且要对这些任务的产物做注入重建）
**并行组**：K3 串行链**最后一环**；唯一可并行的只读动作是契约/清单的静态比对（不占组件）
**预估**：5–6 h（含 4–5 路注入的重复构建）
**档位**：大改（新建 L2 门控 + 退役既有断言 + 注入改组件源码；复核须独立重跑 + 独立注入）
**状态**：待验收

## 背景

K0/K1/K2 各有收口门控（`check-linux-k0` / `-k1` / `-k2`，均入 L2）。K3 交付了「TLB 规范 + QEMU 对齐 + arch 探针 + 内核页表/故障/COW/栈」，但边界目前只有任务书描述、**没有机械判据**：

- 内核侧：页表原语、`tlb_control` 封装、子原因消费、COW、栈增长各自有探针，但**没有任何一条门控把它们连成阶段**（谁能证明「阶段 K3 达成了」？）；
- 硬件侧：QEMU 的 TLB 语义由 `tests/arch` 的 TLB 探针判（`make check-arch`，**L3**）；
- 历史判据：K1/K2 门控里有若干与「内存/故障/TLB」有关的断言在 K3 之后**不再合适**（`docs/Process-07 §4a`：阶段推进即退役过时判据）。

## 范围

1. **新增** `tools/linux/check_k3.py` + `make check-linux-k3`，并接线：
   - `Makefile`：`PHONY`、`GATE_LOCKED_TARGETS`（本门控会**增量重建**）、`_locked-check-modules`（入 L2）、`make help` 一行、目标块注释（说明成员与层归属）；
   - `docs/Process-07-门控分层规范.md` 的「目标-层」表新增一行（层 = L2，说明 = K3 收口）。
2. **检查组（现场派生，不写死项数；打印 PASS/FAIL 计数）**
   - **B 构建与配置**：`.config` 现场解析 —— `CONFIG_PAGE_SIZE_64KB=y`（⇒ 页大小 == 契约值，禁写死 64 KiB）、`CONFIG_DADAO_K1_EARLY_STOP=n`、`CONFIG_DADAO_K2_{EARLY,TIME}_STOP=n`、K3 自检符号按镜像；构建 rc=0；命令行无 `-d/-D`。
   - **M 页表原语**（011）：`pmd_populate` 写出的 L1 表项 `P=1`/`SP=0`/`SPF==0`/`G==0`/PPN == 表 PA（**不得**是表的 VA）；`tlb_control(op,scope,asid_any)` 的**命令值由门控现场重建**（三个维度按 `spec/DADAO-12 §4.5` 拼位）并与内核打印逐一比对；`ASID` 读回 `[63:16]==0`。
   - **F 故障通道**（012）：缺页 ⇒ 处理 + 重试成功 + 第二次访问不再进 handler（计数增量 == 0）；无 VMA ⇒ 具名终止（cause/sub 名正确）；`ADWBFAIL` ⇒ 不分配、不重试；子原因符号表 ↔ `contract-see §6.1` **现场解析逐位比对**（含「其它 cause 的 `[63:16]==0`」一条）；**大类解析必须按 `cause & 0xffff`**（带子原因位时的 cause 仍须命名正确，不得落入 `unknown cause`）。
   - **C 零页**（012 的 `P8`–`P10`）：读缺页映射共享零页、写缺页换新页、零页未被污染。（**非零页 COW 已随 013 退役移交 K4**，K3 门控不含 COW 组。）
   - **T TLB 行为（内核侧，011 探针）**：fill 与命中（改 PTE 不失效仍见旧映射）、`invalid`+VA/`range`（只影响相交条目）、`clean` 回写 A/D 且条目保留、`flush` 回写+删除、`ASID_ANY=0` 不动 `G` / `=1` 含 `G`、写 `PTBR`/`ASID`/`ptw_enable` 不隐含失效。
     **注**：**不**在本门控里重跑 `tests/arch` 的 TLB 探针——硬件语义的判据是 L3 `make check-arch`（`docs/Process-07 §4` 一层一列）。本门控只做**静态对账**：`ARCH_CFX_PROBES` 是否含 TLB 探针条目、`tests/arch.yaml` ↔ `tests/arch/ptw/**` 载体是否齐全、`expected.yaml` 的期望位号是否全部来自契约（不写魔数）。
   - **X 退出码与静止性**：正例 rc=0；自检失败码 ∈ guest 段 `0x01–0x7F`；异常终止 ∈ monitor 段（`0xC0–0xFF`，supv ⇒ `0xE0|bit`）——段与边界从 `spec/Kaiwu §7.1` **现场解析**，不写死具体码；输出无 `panic`/`unknown cause`/二次初始化痕迹。
   - **R 反向断言**：handler 进入次数 == 现场派生的期望次数（不多不少，防「静默多进」）；无「重试上限触发」痕迹；页分配次数增量与 case 描述一致。
3. **§4a 退役（本任务的重点交付之一）**：逐条审计 `tools/linux/check_k1.py`、`check_k2.py`（若已落地）里**与内存/故障/TLB 相关**的断言（做法：把两个脚本里的断言名/文案按「CFXMEM|TLB|tlb|page|页表|未映射|PTW」现场 `grep` 出清单），给三态处置并逐条写**替代判据的来源**：
   - **保留**：与新阶段不冲突（说明理由）；
   - **改限定语**：语义仍真但只在旧镜像成立 ⇒ 改写成「本镜像（`CONFIG_DADAO_K1_EARLY_STOP=y` / 无 mm 子系统）内 …」，替代 = `check-linux-k3` 的对应组；
   - **删除**：已被新判据完全取代 ⇒ 删除并指向新断言。
   已知候选（须逐条核对实际文案后处置，不得照抄）：
   - `check_k1.py` 的「`CFXMEM` 只出现 1 次（唯一一次预先声明的探针）」与「无 K1 之后的子系统痕迹」——K1 镜像内仍成立 ⇒ 预期**改限定语**，替代 = 本门控 F 组（对 K3 镜像断言「未映射 ⇒ 处理并重试」）；
   - K2 门控的「未注册的 `CFXMEM` ⇒ 具名终止」——K3 起由页故障通道接住 ⇒ 预期**改限定语**为「本镜像无 mm 子系统」，替代 = 本门控 F 组；
   - 若任一旧门控含「TLB 维护为空 stub」「TLB 不参与」类断言（K1/K2 期的合理性假设）⇒ **删除**，替代 = 本门控 T 组 + `check-arch` 的 TLB 探针；
   - **零退役必须给可复核理由**（逐条 `grep` 证据 + 为什么它在新阶段仍成立）；门控内机械断言：改写后的**新文案存在**、被删的**旧文案不存在**。
4. **一键证据脚本**：在运行期证据目录内，一条命令跑完「构建 → 本门控 → selfcheck → 注入 → K0/K1/K2 回归 → TLB 静态对账」，退出码如实传播（禁 `cmd | tee` 吞码）。

## 验收（逐条贴真实 rc）

1. `make check-linux-k3` **rc=0**，检查项计数现场打印（PASS 数 == 总项数、FAIL 0）。
2. `--selfcheck` 每个检查组至少一次「翻转输入 ⇒ 该组红」（用例：把 B 组的 `.config` 值改一位、M 组的命令值改一位、F 组的子原因符号改名、C/S 组各改一处期望、T 组把 `ASID_ANY` 判据对调、X 组把段边界挪一位）。
3. **≥4 路可达 FAIL 注入**（`cp` + md5 还原 + **重建**；还原后必须重建再回绿）：
   - ① 内核 `tlb_control` 封装把 `scope` 移位改错 ⇒ M 组红；
   - ② 页故障 handler 不分配直接重试 ⇒ F 组红（重试上限触发，rc≠0）；
   - ③ 零页被就地写（未换新页）⇒ C 组 `P9`/`P10` 红；
   - ④ 零页写缺页改成"就地写零页" ⇒ C 组 `P9`/`P10` 红（原 S 组的注入随 014 退役作废）；
   - ⑤ 把某条已退役的旧断言原样加回 K1 门控 ⇒ R 组（退役机械断言）红。
4. **不回归**：`make check-linux-k0` rc=0、`make check-linux-k1` rc=0、`make check-linux-k2` rc=0（**不跑 `check-modules`**：会装共享安装根）。
5. **硬件侧证据（L3，不在本门控内跑）**：完成区贴 `make check-arch` 的 rc 与新增 TLB 探针的逐条结论（由主会话在收口时执行；若尚未跑，完成区必须标「L3 待主会话」，本任务停在 `待验收`，不得自行置 `已验证`）。
6. **期望值全部现场派生**：完成区列出每个期望的来源（契约章节 / `.config` 键 / `spec/Kaiwu §7.1` / 现场计数），并说明**没有**从被测输出反推期望（结构性断言如「handler 进入 1 次」除外）。
7. `docs/Process-07` 的 L2 组成表含 `check-linux-k3`；`make help` 有对应行；`GATE_LOCKED_TARGETS`/`PHONY`/`_locked-check-modules` 均含之（`grep` 现场取证）。
8. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`/`spec/`/`contracts/`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树。
2. **预计改动文件**：`tools/linux/check_k3.py`（新）、`tools/linux/check_k1.py`（**仅** §4a 退役相关断言与文案）、`tools/linux/check_k2.py`（同上，若已落地）、`Makefile`（目标 + L2 接线 + `PHONY`/`GATE_LOCKED_TARGETS`/`help`）、`docs/Process-07-门控分层规范.md`（层表一行 + §4a 处置记录）、本任务书。**不改** `components/**`（注入时临时改、用完还原）、`tests/**`、`spec/**`、`.tao/contracts/**`。
3. 不提交 git；禁 `install-host`/`check-modules`；`JOBS=32`；禁边构建边测试。
4. 禁 `git checkout/restore/stash`；注入还原用 `cp` + md5；注入中途失败也必须 try/finally 还原并重建。
5. 门控必须**能失败**：每条断言有可达 FAIL 路径；禁恒真断言、禁「两支写同一结果」；计数类期望现场派生（禁钉死总项数，除 `spec` 常量）。
6. 只在 `qemu-system vast` 上验收；Vast 固件/镜像用共享产物，**不重建 QEMU**（QEMU 侧判据已由 `check-arch` 承担）。
7. 运行时间：整体若 > 15 min，按 `docs/Process-07 §2` 与节点规则处理（可在计算节点跑，但**不得**改变判据）；主控机上同时只允许 1 个长跑批。

## 待裁定

1. ~~§4a 的退役边界~~ **已裁定（用户 2026-11-16：「A 就地退役」）**：本任务**同笔**改 `check_k1.py`/`check_k2.py`（逐条改限定语或删除 + 门控内机械断言「新文案存在 / 旧文案不存在」），完成区**逐条披露**（哪条断言、为什么、替代判据在哪）。理由：分两笔会留一段「K1/K2 门控红或假绿」的窗口。
2. ~~L3 证据的时序~~ **已确认（用户 2026-11-16）**：`check-arch` 由**主会话在里程碑收口时**执行；本任务 `待验收` 的完成区标「L3 待主会话」，L2 门控不为 L3 证据阻塞。
3. ~~`check-linux-k3` 是否含全部 case~~ **已确认（用户 2026-11-16）**：只跑**代表例**（每类 1–2 个），全量 case 由 `k3_page_probe.py` 单独跑（不入门控）。注：随 `m14-linux-013`/`014` 退役，本门控的组已收为 **B/M/F/C/T/X/R** 七组（无 COW 组、无栈组）。

## 审阅记录

### 第 1 轮 engineer 自审（engineer，2026-11-17）

**范围**：本任务全部改动（`tools/linux/check_k3.py` 新、`check_k1.py` 三条文案、`check_k2.py` 一条文案 + 组注释、`Makefile` 接线、`docs/Process-07` 层表行 + §4a.1、本任务书），逐行读 diff，逐条对照 `spec/DADAO-12 §2.2.2/§2.2.3/§4.5`、`contract-tlb` TLB-04/19/29/34、`contract-see §6.1/§6.1.1`、`spec/DADAO-13 §2`、`spec/Kaiwu §7.1`、`docs/Process-07 §4a`。判决：**可交付**（findings 全部处置，`待验收` 等待独立复核）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `k3pt.one()` 在注入镜像上抛 `SystemExit`（行缺失）⇒ 门控按「输入缺失」rc=2 中途退出，`--inject` 跑不完 | ✅已修 | `_bundle()` 把每段的 `SystemExit` 转成「该组行缺失」红；`run_inject` 同时捕 `(Exception, SystemExit)` | `scope-shift` 注入记 `M 行缺失` 红，`--inject` 6/6 全跑完 |
| F2 `spec_tlb_control()` 首版把 §4.5 的 scope 名 `VA` 当键（内核用 `va`）⇒ 首跑 rc=2 | ✅已修 | spec 与 contract 两侧解析统一 `.lower()` | `§4.5 scopes parsed as [...]` 消失；M4 19 条命令值全绿 |
| F3 `expected.yaml` 的 `subcause: null`（「无子原因」）被当成「符号不在契约里」⇒ T7 假红 | ✅已修 | 过滤 `is not None` | T7 期望符号检查实际 `{}` |
| F4 `K3_PF_MAGIC` 不在 pt 探针的 `kernel_marks()` ⇒ `KeyError` | ✅已修 | 新增 `d["pf"] = k3pf.kernel_consts()`（pf 探针常量） | P2/C2 读回值断言通过 |
| F5 P8 行的 `pte_pa` 已是页号，首版又套一次 PPN 位移 ⇒ 恒 0 | ✅已修 | C1 与 `num(pte_pa)` 直比 | C1 期望 32767 实际 32767 |
| F6 X5 把终止后的寄存器转储 `dadao: rdNN:` 当成终止行（34 条） | ✅已修 | 只数带 `cause=(0x..) ip=` 的行；并改断言「输出末尾是 die 汇总行且 code == rc」 | pf4/pf5 X5 全绿；注入档终止行恰 1 |
| F7 R3 把池计数当数据页数（缺页填充会为新建 L1 表分配一页）⇒ 误红 | ✅已修 | 改为「单次入口至多一页」 | R3 全绿（P3a 首次填充 +1 不再误判） |
| F8 B3 的「无 `-d/-D`」只查门控自己拼的 argv（恒真） | ✅已修 | 增「输出无 `IN:`/`Trace` 逐指令转储标记」的控制台断言 | B 44→48 条（4 镜像 ×1） |
| F9 证据脚本自身把注入路数 `6/6` 读成 `66` ⇒ 假 FAIL | ✅已修 | 用 `sed` 取分子 | 二轮 `注入路数 … 实际=6 路` PASS，全程 `RESULT: PASS` |

> 过程记录：K0/K1/K2 在改动**前**先跑过一遍基线（rc=0/0/0）；`check-linux-k1`/`-k2` 的文案改动后由证据脚本再跑一遍（rc=0/0/0）。共享构建树按镜像逐个 `apply_config_lines` 钉住四个边界符号，未出现「继承上一镜像配置」的假绿。


### 第 1 轮 reviewer 验收（reviewer，2026-11-17）

**重跑（自采 rc，不采信完成区）**
1. `git rev-parse --show-toplevel` = 本任务 worktree；基线与收尾 `git status --porcelain -uall` 均空（快照逐行对账一致）。
2. `make check-linux-k3` rc=0（52 s）：`[GROUP] B 48/48 M 37/37 F 38/38 C 17/17 T 66/66 X 28/28 R 29/29` → `check-linux-k3: PASS (263/263)`。
3. `python3 tools/linux/check_k3.py --selfcheck` rc=0 → `PASS (7/7 组可翻转；未翻转 [])`。
4. 一键证据脚本 `run.sh` rc=0（430 s，`RESULT: PASS`）：build / gate / selfcheck / `--inject 6/6`（逐路 cp+md5 还原 + 重建回绿）/ K0-K2 / TLB 静态 / verify 27 项，全绿。
5. `make check-linux-k0/-k1/-k2` rc=0/0/0（119/119、112/112、104/104）。
6. `min_rom_probe_tlb.py --selfcheck` rc=0（18 子原因 / 11 大类 / 15 case / 29 check）；`check_tests_index` rc=0（arch=11、file 存在）。
7. TLB 静态对账：`ARCH_CFX_PROBES` 含 `tlb`；`expected.yaml` 15 case 全带 source、无裸编码（T7 八条绿）；`tests/arch.yaml` 按其 README 只索引 `.s` 载体、ptw 载体不放 `.s`，与索引门控双向一致。
8. 本轮无外因红（在途 `m16-chipyard-001` 未造成任何门控红项，无需归因）。

**独立注入（cp+md5 + 重建回绿；①③⑤ 为任务书未列的注入面）**
- ① 页大小改 4 KiB（组件 Kconfig 的 select + defconfig，非 `pgtable.h` 断言）⇒ `rc=1`、`B0 期望=0 实际=1`；还原 md5 相等；回绿 263/263。
- ② `tlb_control` 的 OP 移位 0→1（非 engineer 的 scope 移位）⇒ `rc=1`、B5 红 + M 组截断；回绿 263/263。
- ③ 子原因 PERM wyde 32→48（非 MEM）⇒ `rc=1`、B5 红；回绿 263/263（F 侧红由 `--inject subcause-wyde` 实证 `F1 期望=48 实际=32`）。
- ④ 退役旧文案回潮 ⇒ `rc=1`、`R 28/29`、具名 `R4 …已退役的旧文案不在`；回绿 263/263。
- ⑤ 替代判据缺失（k1 三处 `check-linux-k3 F 组` 指向改掉）⇒ `rc=1`、`R 23/29`、6 条 R4 红；回绿 263/263。
- 组件源 4 个被注入文件 md5 全部复位（与 engineer 注入日志的期望值逐一相等）；全程未用 `checkout/restore/stash/reset`。

**断言抽查（跨 B/M/F/C/T/X/R ≥10 条，均可达 FAIL、非恒真）**：B1/B2（破坏 `.config` ⇒ 7 红，`B2 期望=65536 实际=4096`）；M4（`0x16→0x14`）、M3/M5（两侧独立现场值）；F1（`48/32`）、F2（`1/-1`）、F5（`{}` 集合式）；C2（`True/False`）、C3（`zero_dirty`）；T5（`1/0`）、T7（vacuous ⇒ FAIL）；X2（`0x80` 越界）、X1（正例 rc）；R1（`1/2`）、R2（预算现场解析自 `fault.c` 的 `DADAO_PF_RETRY_BUDGET 4`，非写死）、R4（注入④⑤）。**项数现场派生**：`263` 在门控/证据脚本零命中，PASS 打印 `rep.total/rep.total`。

**§4a 退役核对**：改限定语 4 条（k1 K13×3、k2 E8，diff 确认原地改名、断言数不变）；删除 0 条（`stub|不参与|旁路` 零命中）；保留 6 类理由见 §4a.1；机械断言实测可抓「旧文案回潮」（注入④）与「替代判据缺失」（注入⑤）。**越界核对**：`git diff --name-only 3f3914be..HEAD` = 6 文件、与完成区一致，`spec/|.tao/contracts/|tests/|.tao/knowledge/` 零命中；PHONY / GATE_LOCKED_TARGETS / `_locked-check-modules` / `make help` / docs 层表 grep 取证全含；完成区 23 行 ≤30、无运行期路径。

**findings（不阻断，architect 收尾处置）**：① §4a.1 保留清单漏 3 个任务书口径 grep 命中项（k1 `page_size_log2`、k11 阶段序含 PTW、k2 `X9`），建议补三行理由；② 证据脚本 `S1` 用工作树态，提交后恒报「改动文件 0 个」，建议改 `BASE..HEAD` ∪ 未跟踪（我实测其可达 FAIL：在 `spec/` 下放越界文件 ⇒ rc=1，移除回绿）；③ 门控在 guest 早死时于首个 SystemExit 中止、后续组不入报告（rc 仍非 0，`--inject` 路径有逐组归因）；④ 完成区 L3 表述与验收 5 的「L3 待主会话」措辞略异（语义等同）。

**判决：Accepted** —— 验收命令块在我自己的重跑下全部通过、硬约束无违反；L3 `make check-arch` 仍留主会话，任务状态维持 `待验收`。

### 第 2 轮 reviewer 验收（收尾 cleanup）（reviewer，2026-11-17）

**重跑（自采 rc）**：基线与收尾 `git status --porcelain -uall` 均空；一键证据脚本 rc=0（432 s，`RESULT: PASS`）—— gate `PASS (263/263)`（B48 M37 F38 C17 T66 X28 R29）、`--selfcheck 7/7`、`--inject 6/6`（逐路 cp+md5 还原 + 回绿）、K0/K1/K2 rc=0/0/0、TLB 静态、`verify.py` **37/37 PASS rc=0**；`check_k1.py --selfcheck` rc=0（19/19 组可翻转）、`check_k2.py --selfcheck` rc=0（7/7）；`BASE..HEAD` 仍恰 6 文件（任务书 / `Makefile` / `Process-07` / `check_k1/k2/k3.py`），无越界。

**1 §4a.1 补充**：3 行保留理由已入 `docs/Process-07 §4a.1` 补充表；现场 grep 逐条核实断言存在 —— `check_k1.py` K6 `page_size_log2`（L747）、K11 `STAGE_ANCHORS` 含 `ptw-announce/table-build/install/post-switch` 四段（L616-619）+ `ONE_SHOT`，`check_k2.py` X9（L699）；理由成立（交接块字段 / K1 出口判据 / 内核自报值 vs K3 实测 rc，对象不同、互不取代）。`verify.py` RA0–RA2 共 7 项基线全绿，独立反例：
- RA1（文档无理由行）：删掉 `page_size_log2` 保留行 ⇒ **rc=1**、`[FAIL] RA1 …期望=1 实际=0`；cp+md5 还原 ⇒ rc=0（37 项）。
- RA2（源码无该断言）：改名移除 `ptw-announce` ⇒ **rc=1**、`[FAIL] RA2 K11 阶段序 …实际=False`；还原 ⇒ rc=0。

**2 证据脚本 S1**：已改为 `BASE..HEAD ∪ 工作树 ∪ 未跟踪`，STAT 实报 6 个（修复前恒报 0）；`S0` fail-closed 已加。独立注入（任务书未列）：给已跟踪 `README.md` 追加一行 + 在 `spec/` 放未跟踪文件 ⇒ **rc=1**、`[FAIL] S1 …实际=['README.md', 'spec/zz-r2-probe.md']`（N4 反例同步红）；cp+md5 还原 README、删除新文件 ⇒ STAT 回 6 个、rc=0。`S0` 可达 FAIL 以 BASE=HEAD（改动集为空）在内存演示：`[FAIL] S0 …实际=False`。

**3 L3 表述**：完成区与遗留问题均已改为「`make check-arch` 已由主会话执行 rc=0」；我独立核运行期日志：`CHECK_ARCH_EXIT=0`、`check-arch: PASS`，TLB 探针逐条日志 **29 PASS / 0 FAIL、15 个 `arch-ptw` case 齐全、`29/29 checks passed`**。验收 5 原文（条件式判据）未改，完成区已满足其「已跑 ⇒ 贴 rc」分支，二者不再矛盾。

**4 已知限制**：已登记于遗留问题（guest 早死 ⇒ 首个 `SystemExit` 中止、后续组不入报告、rc 仍非 0、`--inject` 路径逐组归因），与上轮 finding ③ 一致。

**findings（不阻断）**：① `RA2` 用子串匹配 token，保留前缀的改名（`ptw-announce`→`ptw-announceX`）实测 **rc=0 不翻红**，建议改带定界的精确匹配；② §4a.1 补充表 K11 行写「`ONE_SHOT` 的 `ptw` 行」，但 `ONE_SHOT` 无 `ptw` 键（实为 `vec/ids/pre/map/post/new/text/boot/mark/done` 等 10 条 `K1 ptw *` 行），措辞建议改准（文档级）。

**判决：Accepted** —— 4 项收尾逐条实证、不回归全绿、`BASE..HEAD` 范围未漂移、L3 证据闭合；状态推进由主会话裁定。

### 第 3 轮 reviewer 验收（finding 处置确认）（reviewer，2026-11-17）

**重跑（自采 rc）**：`make check-linux-k3` **rc=0**、`PASS (263/263)`（B48 M37 F38 C17 T66 X28 R29）；`verify.py` **rc=0、37/37 PASS、0 FAIL**（STAT 实报 `BASE..HEAD ∪ 未跟踪 = 6 个`）；`git diff --name-only 3f3914be..HEAD` 恰 **6 文件**；基线与收尾 `git status --porcelain -uall` 均空。

**1 RA2 已改定界精确匹配**：实现改为 `re.findall` + lookaround 边界（`(?<![A-Za-z0-9_])…(?![A-Za-z0-9_])`，`ptw-announce` 把 `-` 一并纳入边界）。**我注入一路**：`ptw-announce`→`ptw-announceX`（正是上轮的绕过写法）⇒ **rc=1**、`[FAIL] RA2 K11 阶段序：源码里有该断言且是完整 token（定界匹配）…实际=False`；`cp`+md5 还原 ⇒ rc=0。另两 token 现场抽查：`page_size_log2` 原样命中 1 / 加后缀 0；`"X9"` 原样 1 / 加后缀 0 / 改前缀 0，真实 `check_k2.py` 命中 1。

**2 §4a.1 K11 措辞**：已改为「`ONE_SHOT` 里 10 条 `K1 ptw *` 行：`vec`/`ids`/`pre`/`map`/`post`/`new`/`text`/`boot`/`mark`/`done`」；现场解析 `ONE_SHOT`：**17 键、其中 `K1 ptw *` 恰 10 条**、列出的键名逐一对得上、确认无 `ptw` 键 —— 措辞与实际一致。

**判决：Accepted** —— 2 条 finding 处置到位、不回归全绿、`BASE..HEAD` 范围未漂移；无未闭合项（未提交 git，本轮仅改本任务书审阅记录）。

## 完成区

**测试结果**：通过 263/263（`make check-linux-k3` rc=0；分组现场计数 B 48/48 M 37/37 F 38/38 C 17/17 T 66/66 X 28/28 R 29/29，总项数不写死）；`--selfcheck` 7/7 组可翻转；`--inject` 6/6 路（`cp`+md5 还原 + 重建回绿）；一键证据脚本 `RESULT: PASS`（431 s）；K0/K1/K2 各 rc=0；`min_rom_probe_tlb.py --selfcheck` rc=0；静态复核 37 项全 PASS。失败原因：无。

**修改文件**：`tools/linux/check_k3.py`（新：B/M/F/C/T/X/R 七组 + `--selfcheck` + 6 路注入）、`tools/linux/check_k1.py`（仅 K13 三条文案 + 文件头说明）、`tools/linux/check_k2.py`（仅 E8 文案 + E 组注释）、`Makefile`（`_locked-check-linux-k3` 目标 + `PHONY` + `GATE_LOCKED_TARGETS` + `_locked-check-modules` + `help` + 块注释）、`docs/Process-07-门控分层规范.md`（目标-层表一行 + §4a.1 退役记录）、本任务书。（`git status -uall` 对账：跟踪文件改动仅此 6 项，无临时残留。）

**验收结果**（真实输出）
- `[GROUP] B 48/48  M 37/37  F 38/38  C 17/17  T 66/66  X 28/28  R 29/29` → `check-linux-k3: PASS (263/263)`
- `check-k3 selfcheck: PASS (7/7 组可翻转；未翻转 [])`
- `check-linux-k3 --inject: PASS (6/6 路注入按预期变红并还原)`：`page-size-4k` 构建 rc=1 ⇒ B；`scope-shift` ⇒ M；`subcause-wyde` ⇒ F；`zero-page-write` ⇒ C；`retry-no-fill` ⇒ F+R（控制台实录 `try=5 result=die-budget`）；`retired-back` ⇒ R
- `make check-linux-k0/-k1/-k2` rc=0/0/0；`min_rom_probe_tlb.py --selfcheck` rc=0（18 子原因 / 11 大类 / 15 case / 29 check）；`verify.py`（接线 6 + §4a 18 + 补充核对 7 + 改动范围 2 + 反例自检 4）全 PASS
- **L3 已由主会话执行**：`make check-arch` rc=0（TLB 探针含在其中，逐条结论见运行期日志）

**§4a 退役（逐条）**：**改限定语 4 条** —— `check_k1.py` K13「CFXMEM 计数」「CFXMEM resumed」「后置子系统痕迹」、`check_k2.py` E8「未声明 CFXMEM 退出码」，均限定为「本镜像内（`CONFIG_DADAO_K1_EARLY_STOP=y` / 无 mm 子系统）…」，替代判据 = `check-linux-k3` F 组。**删除 0 条**：无「TLB 维护为空 stub / TLB 不参与」类断言（`grep -n 'stub\|不参与\|旁路' tools/linux/check_k1.py tools/linux/check_k2.py` 零命中），故无删除对象。**保留**（各自镜像内仍成立，理由见 `docs/Process-07 §4a.1`）：K1 K8 预建表、K9 内核自建表、K14 半主机按 PA 取值、`FATAL_PATTERNS`；K2 E2/E3 注册探针、X6/X8 退出码分段；**补充核对 3 项**（K1 K6 `page_size_log2`、K1 K11 阶段序含 PTW、K2 X9）经现场 `grep` 复核亦为保留，理由见 §4a.1 补充表。机械断言 = R 组按文档锚点核对「新文案在 / 旧文案不在 / 替代判据指向 / 文档有记录」，`--inject retired-back` 与 selfcheck 各给一条可达 FAIL。

**期望值来源（全部现场派生，未从被测输出反推）**：页大小/几何 ← 镜像 `.config` + `spec/DADAO-12 §2.2.2` + 契约 `page_size`；L1 字段位 ← §2.2.3；`tlb_control` 三维编码与 op 语义（删除/回写）← §4.5 寄存器行与「失效接口」段，并与 `contract-tlb` TLB-19/TLB-29 双向比对；ASID 位宽 ← §4.5 ↔ TLB-04；子原因位/wyde ← `contract-see §6.1/§6.1.1` ↔ 内核 `asm/cause-sub.h`；cause 表 ← `spec/DADAO-13 §2`；退出码段/模式/位号 ← `spec/Kaiwu §7.1`；自检码全集 ← 现场发现的 `k3_*_selftest.c`；重试预算 ← `fault.c`；数据标记 ← 自检源；TLB 探针清单 ← `tests/arch/ptw/expected.yaml` + 载体 `--selfcheck`。结构性常量仅「入口次数 / 分配增量」（case 设计，验收 6 允许）。

**新发现/坑**
1. 运行时间：门控 52 s（4 镜像增量构建 + 4 次启动）、`--inject` ≈3.5 min、全套证据 431 s（未触 15 min 分片线）。
2. `scope-shift` 注入不是「打印值错一位」而是让 `invalid|VA` 变成 `range`+`size=0` ⇒ 内核按 §4.5 判序报 CFXREG 并具名终止，门控看到的是「计划行缺失」；「错值」路径由 `--selfcheck` 的命令值改一位直接覆盖。
3. 共享构建树的 `.config` 会被逐个镜像覆盖 ⇒ `.config`/符号表必须在**该镜像构建后立即**快照（沿用 K2 门控做法）。
4. 池计数不等于数据页数：缺页填充会为新建 L1 表分配页（P3a 首次填充 +1），逆向断言只能定「单次入口至多一页」+ P9/P9b 的分配增量。
5. 建议沉淀：「阶段收口门控 = 代表例 + 跨镜像阶段不变量」；编码/位宽类期望须**同时**从 spec 章节与 contract 条目解析并互比（本任务 M6 已采用）。

**遗留问题**：L3 无遗留（`make check-arch` 已由主会话执行、rc=0，TLB 探针含在其中）；L1 `make check-knowledge-refs` rc=2，两条具体引用都在 `m15-testcases-009`（基线既有、本任务未触及，`git status` 无该文件），非本任务引入；**已知限制**（reviewer finding ③，不阻断、不改代码）：guest 在首个 `SystemExit` 处早死时门控立即中止、后续组不进入报告（rc 仍非 0；`--inject` 路径逐组归因）；其它无。

**第 2 轮 findings 处置**（reviewer ①②）：① `verify.py` 的 RA2 改为**定界精确匹配**（`(?<![A-Za-z0-9_-])ptw-announce(?![A-Za-z0-9_-])` 等，三个 token 各自带两侧边界，不再是更长 token 的前缀）；三行均实测「加后缀改名 ⇒ `[FAIL] RA2 …` rc=1、`cp`+md5 还原 ⇒ rc=0」（`ptw-announce`→`ptw-announceX`、`page_size_log2`→`page_size_log2X`、`"X9"`→`"X9b"`，md5 逐一相等），并在同一文件上对照「旧子串判据 True / 新定界判据 False」。② §4a.1 补充表 K11 行按实际改写为「`STAGE_ANCHORS` 四段 + `ONE_SHOT` 里 10 条 `K1 ptw *` 行（`vec`/`ids`/`pre`/`map`/`post`/`new`/`text`/`boot`/`mark`/`done`）」，键名现场 `grep` 核对（`ONE_SHOT` 无 `ptw` 键，原文有误）。收尾重跑：门控 263/263、`verify.py` 37/37。
