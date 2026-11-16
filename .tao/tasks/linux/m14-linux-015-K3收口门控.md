# m14-linux-015: K3 收口门控 `check-linux-k3`（TLB 四类 + 分页/零页/栈 + K2 不回归 + §4a 退役）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-qemu-005`、`m14-testcases-005`、`m14-linux-011`、`m14-linux-012`、`m14-linux-014`（全部 `已验证`；`m14-linux-013` **已退役**，COW 归 K4）
**可并行分片**：否（单一端到端门控；且要对这些任务的产物做注入重建）
**并行组**：K3 串行链**最后一环**；唯一可并行的只读动作是契约/清单的静态比对（不占组件）
**预估**：5–6 h（含 4–5 路注入的重复构建）
**档位**：大改（新建 L2 门控 + 退役既有断言 + 注入改组件源码；复核须独立重跑 + 独立注入）
**状态**：待开始

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
   - **S 栈增长**（014）：一页下沉成功；超 `RLIMIT_STACK` 不扩；非 `VM_GROWSDOWN` 不扩；权限类不扩栈。
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
   - ④ 栈增长去掉 `VM_GROWSDOWN` 判定 ⇒ S 组红；
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

1. **§4a 的退役边界**：本任务被授权改动 `check_k1.py`/`check_k2.py`（退役必须落在同笔），这与「各任务只动自己的文件面」有冲突——若用户希望 K1/K2 门控的任何改动都另立任务，则本任务只产出「退役清单 + 建议 diff」，由新任务落地。建议**就地退役**（`§4a` 要求「新门控落地后」退役，分两笔会留一段冲突期）。
2. **L3 证据的时序**：`check-linux-k3` 属 L2，硬件语义由 L3 `check-arch` 判。是否要求本任务在 `待验收` 前就跑一次 `check-arch`（会很慢，且与节点规则冲突），还是由主会话在里程碑收口时跑、完成区先留空？建议**后者**（L2 门控不为 L3 证据阻塞；但 `待验收` 的完成区必须标「L3 待主会话」）。
3. **`check-linux-k3` 是否要包含 K3 自检镜像的全部 case**：会拉长 L2。建议：只跑**代表例**（每类 1–2 个，符合用户「简单验证即可」），全量 case 由 `k3_*_probe.py` 单独跑（不在门控内）。

## 审阅记录

（待填）
