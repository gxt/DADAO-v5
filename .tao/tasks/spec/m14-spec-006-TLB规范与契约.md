# m14-spec-006: K3 的 TLB 规范与契约（只定义，不实现）

**模块**：spec
**项目里程碑**：M14
**依赖**：`ADR-0052 D6`（K3 第一步先定义 TLB、第二步才实现）；用户 2026-11-16 三条口径（同步完成 / per-hart / M14 只做 QEMU + `tests/arch` 探针）
**可并行分片**：否（spec + 契约 + 锁，单写者）
**预估**：3–4 h
**档位**：大改（新建契约 + v5 册撤销「不定义」声明 + 锁重算；复核 ≥4 路注入）
**状态**：待验收

## 背景

上游 `DADAO-12` 已把 TLB 写得很细（本任务**收编**，不重写）：

- `§2.2.1`/`§2.2.2`：匹配键 = 虚拟页 + ASID（`G=1` 跨 ASID）、命中不重读 PTE、命中用条目里的 SPF/GPF + HSJU + R/W/X 检查、**只有步进成功才 fill**（缺页/权限失败不填充、不更新 A/D）、替换策略与容量**实现定义**；
- `§2.2.5`：写 PTBR / ASID / `ptw_enable=1` **不隐含 invalidate**；
- `§2.2.6`：异常检查优先级；
- `§4.5`：A/D local/dirty 状态机 + **原子 OR 回写**（失败 ⇒ 当前 monitor `CFXMEM`）；**`cfx_ptw_tlb_control`** 三维正交（操作 `[1:0]` = none/clean/invalid/flush、范围 `[3:2]` = all/VA/range、`bit4` = `ASID_ANY`）、判序（先操作后范围）、`none` 无条件 no-op、`clean` 回写保条目、`invalid` 只删、`flush` 回写后删（**回写失败不删**）、`ASID_ANY=0` **不碰 `G` 条目**、非法编码 ⇒ `CFXREG`。

但 v5 侧现状：

- `spec/Kaiwu §7` 显式写「本节**不定义**：TLB 填充/失效/ASID、cache/LLC、…」⇒ 与上游矛盾，K3 必须先撤；
- 无 TLB 契约（`.tao/contracts/` 只有 see/semihosting/syscall/…），实现与测试无归一化投影可依；
- 用户已定三条口径（`discussing.md` §K3 的 TLB）：**同步完成**、**per-hart（单 hart）**、**M14 只做 QEMU + `tests/arch` 探针**。

## 目标

1. **撤销 v5 的「不定义」**：`spec/Kaiwu §7` 那句里的 TLB 部分改为指向 `DADAO-12 §2.2.1–§2.2.6`、`§4.5`；并在 `§3`（cfx 实现范围 / Vast 段）或 `§7` 补三条 v5 约定：
   - **`tlb_control` 写指令同步完成**（返回即生效，后续访存必见）；`clean`/`flush` 的回写失败**在该写指令上**报 `CFXMEM`，且**不得部分完成**（`flush` 失败不删条目、`clean` 失败不清挂起位）；
   - **per-hart**：`tlb_control` 只作用本 hart；跨 hart 一致性**不在本版范围**（`ISS-459`）；
   - **实现范围**：v5 侧 TLB 由 **QEMU** 承担建模；chipyard/gem5 不在本阶段验收面（`tests/arch` 探针为跨实现判据）。
2. **新建 `.tao/contracts/contract-tlb.md`**（归一化投影，不复制上游正文）：逐条收编上列上游语义（匹配键 / 命中检查 / fill 条件 / A-D 状态机与原子 OR 回写 / `tlb_control` 三维与判序 / 三操作语义 / 范围三档 / `ASID_ANY` 与 `G` / 异常路由），**每条带 `[DADAO-12 §…]` 来源**；三条 v5 约定标 `[spec-decision]`（用户 2026-11-16）。
   - **版本**：`contract-tlb` 映射 `DADAO-12` ⇒ 按 `check-spec-drift` 规则版本须等于 `.tao/contracts/README.md` 的 **SEE / SBI 已发布版（`0.7.1`）**；
   - 同笔在 `.tao/contracts/README.md` 表里加一行（`contract-tlb.md` | TLB 与失效接口合约（K3；0.7.1））。
3. **fault 路径：只收编硬件语义，不引入 OS 概念（用户 2026-11-16 澄清：「缺页/COW 与 `CFXMEM`/`CFXPERM` 没有关系」）**
   - **判定顺序必须先分地址类、再分 `ptw_enable`（用户 2026-11-16 补充口径）**：
     ① **先看 `VA[47:42]`**：≠ 0 ⇒ 属 **cfx 核内地址空间**（cfx 1–63，访问规则按 `DADAO-12 §1`/`§2.1` 的核内空间语义，**不进入 PTW/TLB 流程**）；
     ② `VA[47:42] = 0`（内存窗口）且 **`ptw_enable = 0`** ⇒ 访存**直接 `CFXMEM`**（`DADAO-12 §2.2.1 第一步`；`Kaiwu §1.2` 同口径），**不查 TLB、不产生 TLB 条目**；
     ③ `VA[47:42] = 0` 且 **`ptw_enable = 1`** ⇒ 才进入 PTW/TLB 四步流程（`§2.2.1`/`§2.2.2`）：未映射 ⇒ `CFXMEM`、权限不符 ⇒ `CFXPERM`。
   - 契约只固定**硬件侧**：`DADAO-12 §2.2.6`「页表未映射（含超页/小页缺失）与 A/D 回写失败 ⇒ `CFXMEM`；HSJU 或 R/W/X 不符 ⇒ `CFXPERM`」，以及 `cause_info`（`CFXMEM` = 访存地址，A/D 回写失败时为 PTE 物理地址；`CFXPERM` = 访存地址或指令编码）；
   - **不得**把「缺页 / COW / 越权」这类 **OS 概念**写进 `CFXMEM`/`CFXPERM` 的定义：spec 本身只用「页表未映射/权限不符」表述（「缺页」仅出现在括注里解释「未映射」；**COW 在 spec 中完全没有**）；
   - 内核如何把一次 `CFXMEM`/`CFXPERM` 解释成"缺页 / COW / 真越权"，由内核结合 VMA 与 PTE 自行判定，**不进规范、不进契约**；契约只在门控建议里注明"探针按硬件语义断言（未映射 ⇒ `CFXMEM`；写只读页 ⇒ `CFXPERM`）"，不出现 OS 术语。
3. **门控设计（只设计，不实现）**：在契约里给出「门控建议」小节 —— `tests/arch` 8 条探针（fill+命中 / 命中不重读 PTE / `invalid`+VA / `invalid`+range / `ASID_ANY` 与 `G` / `clean` 回写 A/D vs `invalid` 不回写 / `flush` 回写+删除、回写失败 ⇒ `CFXMEM` 且不删 / 写 PTBR·ASID·`ptw_enable` 不隐含 invalidate），并注明载体形态（`tests/arch/umon/*.s` + `expected.yaml`，需自建页表的走 `min_rom_probe` 并登记 `ARCH_CFX_PROBES`）。**另加 5 条与 K3 扩展范围对应的探针（只按硬件语义，不用 OS 术语）**：⑨a `VA[47:42]=0` 且 `ptw_enable=0` ⇒ 访存直接 `CFXMEM`（贴 `cause_info` = 访存地址）；⑨b `ptw_enable=1` 且页表未映射 ⇒ `CFXMEM`；⑩ `VA[47:42]=0`、`ptw_enable=1` 且**权限不符**（写只读页）⇒ `CFXPERM`（与 `CFXMEM` 可区分）；⑪ 改 PTE 后**不** invalidate ⇒ 仍命中旧条目；写 `invalid`+`VA` 后 ⇒ 命中新 PTE；⑫ `VA[47:42] ≠ 0`（cfx 核内空间）⇒ **不走 PTW/TLB**（按核内空间语义处理，不产生 `CFXMEM` 的"未映射"口径）。
4. **锁**：`spec/Kaiwu-…` sha256 同笔重算 + 注记（用户原话「目前只考虑单hart情况」「M14只考虑qemu；但应该在tests/arch中增加这部分的测试」「这本身是一条指令…可以写完等生效才返回」）。

## 验收（真实 rc + 输出）

1. `grep -n "不定义" spec/Kaiwu-…md` ⇒ TLB **不再**出现在「不定义」列表；`grep -c "DADAO-12 §2.2"` 命中 ≥1、`§4.5` 命中 ≥1；
2. 契约：条目数现场统计（≥12 条），**每条**有来源标注；`grep -c "spec-decision"` == 3（三条 v5 约定）；`contract-tlb` 版本 == README 表 `SEE / SBI` 已发布版；
3. 门控：`check-contracts-dir`、`check-contracts-pending`（无待定标记）、`check-contract-relocs`、`check-spec-refs`、`check-rule-refs`、`check-spec-drift`、`check-spec-purity`、`check-spec-changelog`、`check-spec-readonly`（Kaiwu 重算后 21 册 OK）、`check-knowledge-refs`、`check-dirs`、L1 `make check` 全绿；
4. **≥4 路注入**（`cp`+md5 还原）：① 把 `contract-tlb` 版本改成 `0.7.2` ⇒ `check-spec-drift` 红；② 契约里某条来源改成不存在的 `§9.9` ⇒ `check-spec-refs` 红；③ 把「不定义」句里的 TLB 加回去 ⇒ 判据 1 红；④ 锁 sha 改 1 字符 ⇒ `check-spec-readonly` 红；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **只定义、不实现**：不改 `components/qemu`、不改 `tests/arch`（探针实现归下一件任务）；
- **不复制上游正文**：契约只做归一化 + 指针（`docs/Process-02`）；
- 不改 `.tao/archive/**`、`.tao/adr/**`；
- 不提交 git；注入还原 `cp`+md5。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `check-spec-refs` 红：来源标注行里的占位 `[Machine-01 §章节名]` 被判悬空 | ✅已修 | 该行改述为「上游册写 `DADAO-12` + `§` + 章节名」，不再用方括号占位 | `check-spec-refs` rc=0（失败 0） |
| F2 L1 红：`check-linux-boot-contract` 逐项断言「不定义」句点名 TLB（数据源 `contracts/linux-boot.yaml` 的 `not_defined`） | ✅已修（**越界，见完成区**） | `contracts/linux-boot.yaml` 删 `- TLB`；`contract-linux-boot.md` §6 删排除项、加 TLB 指针条、契约版本 `0.2.1`→`0.2.2` | `check-linux-boot-contract` rc=0；L1 rc=0 |
| F3 注入②首版改 `§9.9 超页的地址转换` 未红（该门控按标题文本解析、不校验节号） | ✅已修 | 注入改为 `[DADAO-12 §9.9]` | 注入后 `check-spec-refs` rc=2 |
| F4 注入④首版片元是多语句，`eval` 语法错 ⇒ 空注入（假绿风险） | ✅已修 | 片元改单表达式（整条 sha 行替换） | 注入「diff 非空」PASS + 门控 rc=2 + md5 还原对账 |
| F5 ⑨b 子原因名错：SP=0 普通页缺失应为 `[52] DGPTRAP`（原写 `DSPTRAP`=超页缺失） | ✅已修 | §11 表 ⑨b 行 | 与 `DADAO-12 §2.2.6` 第 2 步一致 |
| F6 ⑦ 失败子用例原设「PTBR 指向只读 BootROM」不成立（BootROM 属 cfx 核内空间、非 PA；PA RAM 全可写） | ✅已修 | 改注「机器级不可达，实现层注入 PTE 写失败覆盖」 | §11 载体/行内注，无悬空构造 |
| F7 ⑨a 原断言「重开 `ptw_enable` 后从冷态步进」与 TLB-29（写使能不隐含失效）自相矛盾 | ✅已修 | 改为「旁路期间不查 TLB、不产生条目（PTE 的 A/D 仍 0）」 | §11 ⑨a 行自洽 |
| F8 TLB-06 原写「按 `VA[41:29]`/`VA[41:16]` 定位条目」属实现细节外推 | ✅已修 | 改为「按页大小覆盖 512 MiB / 64 KiB 对齐区间」并指 `§2.2.3`/`§2.2.4` | 引用可解析（`check-spec-refs` rc=0） |
| F9 `ISS-459` 无法写入 `Kaiwu`（`check-spec-purity` 禁 `ISS-\d+`） | ❌不修 | 保留「跨 hart 一致性不在本册范围」措辞；ISS 号落锁注记 + `contract-tlb` TLB-38 | 写入即 `check-spec-purity` 红；现 rc=0 且 ISS 号在契约/锁可检索 |
| F10 TLB-14「写在同规则之外」表述含糊 | ✅已修 | 改为「写除上述置位外，还须在 `D_local = 0` 时置 `D`」 | 与 `DADAO-12 §2.2.5` 一致 |

判决：finding 全部处置（仅 F9 为有据不修），状态可置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-16，大改档：看 diff + 独立重算 + 4 路自设计注入）

**重跑记录（全部自跑、非采信）**：一键证据脚本 `bash .work/evidence/<任务ID>/run.sh`（占位形，具体路径不入任务书）⇒ `== 检查 45 项，失败 0 项 ==`、`EXIT=0`（判据 1–3 + 15 个门控 rc=0 + 其 4 路注入「红 ⇒ cp+md5 还原 ⇒ 回绿」+ L1 `make check` rc=0，71 s，日志落运行期日志目录）；`make -s check-spec-readonly` ⇒ `21 read-only spec volume(s) OK` rc=0；独立重算 `sha256sum spec/Kaiwu-…md` = `841d93d275967199dac5799989e686e4ad3154adc78d862d1d31468e5e07c751`，与锁逐字相同。判据 1：`awk '/不定义/ && /TLB/'` = 0、`DADAO-12 §2.2` 10 处、`§4.5` 8 处；判据 2：契约 `^- TLB-` 43 条、缺来源 0、`spec-decision` 3 行、版本 `0.7.1` == README `SEE / SBI` 已发布版 `0.7.1`、README 表 1 行；判据 3：§11 探针 13 行、13 行均含 wyde 断言。
**越界核对**：`git diff --name-only 262aac2b..HEAD` = 7 文件（`spec/Kaiwu-…`、`.tao/contracts/{README.md,contract-tlb.md,contract-linux-boot.md}`、`contracts/linux-boot.yaml`、`manifests/spec-readonly.lock.toml`、本任务书）；`components/**`、`tests/**`、`tools/**`、`.tao/adr/**`、`.tao/archive/**` 改动 = 0；注入前后 `git status --porcelain -uall` 均为空（快照对账一致）。
**我的 4 路注入（自设计、`cp`+md5 还原，非复用其 4 路）**：① `[DADAO-12 §4.5 cfx_ptw - page table walker]` → 纯 `[DADAO-12 §9.9]` ⇒ `check-spec-refs` rc=2，还原 md5 `19eb87cd…` 相等、回绿 rc=0；② TLB-37「同步完成」→「异步完成」⇒ **我的内容判据** `grep '^- TLB-37 ' | grep -c '同步完成'` 1→0（红；同时 `check-spec-refs`/`check-contracts-dir` 仍 rc=0 ⇒ 契约语义无机械门控），还原回 1；③ `linux-boot.yaml::not_defined` 加回 `- TLB` ⇒ `check-linux-boot-contract` rc=2（FAIL 1 项），还原回绿 rc=0；④ 契约版本 `0.7.1`→`0.7.2` ⇒ `check-spec-drift` rc=2，还原回绿 rc=0。四路 md5 均对账相等，收尾 `git status` 空。
**契约质量**：43 条逐条带来源；抽 3 条比原文——TLB-05/TLB-17 为改写压缩，TLB-02（字段枚举）/TLB-19（编码枚举）与原文规范化后重合 58%/70%（码值与字段表须逐字），无长段散文照抄（43 条平均最长重合 25 字符）；抽 5 条语义核对——TLB-05（`G=1` 跨 ASID）、TLB-11（仅步进成功才 fill、失败不填充不更新 A/D）、TLB-17（`clean` 回写保留 / `invalid` 只删不回写 / `flush` 回写后删且失败不删）、TLB-26（`ASID_ANY=0` 不碰 `G`）、TLB-29（写 PTBR/ASID/`ptw_enable` 不隐含失效）均与 `DADAO-12 §2.2.1/§2.2.5/§4.5` 一致。三条约定与 `discussing.md` 用户原话（同步 / 单 hart / QEMU+`tests/arch`）逐条对应，Kaiwu §3.1 与契约 §9 同文。
**子原因位号**：`[48] IGPTRAP`、`[52] DGPTRAP`、`[37] NWPERM`（⑩ 写只读页，未与 `NRPERM` 写反）、`[56] ADWBFAIL`、`[57] NONPTW` 与 ADR-0056 D3 及 `DADAO-12 §2.2.6` 逐位一致；TLB-34 wyde 归属（wyde2=`CFXPERM` / wyde3=`CFXMEM`、另一 wyde 全 0、保留区 `[47:40]`/`[63:58]`）正确。
**下游同步最小性**：yaml 仅删 `- TLB`（`cache`/`LLC`/`设备树（DTB）`/`UART`/`多核` 5 项仍在），`contract-linux-boot.md §6` 仅撤 TLB 排除 + 加指针、版本 `0.2.1→0.2.2`；注入③证明该同步是 `check-linux-boot-contract` 变绿的必要条件，非凑绿。
**判决：Accepted**（非阻断 finding，交架构师：① §11 载体写 `tests/arch/ptw/*.s`，任务书写 `tests/arch/umon/*.s`——`tests/arch/README.md` 明确「`ptw` 等其余 cfx 按需增建」，属路径级偏差，派探针任务时定落点并在 `tests/arch.yaml` 登记（该清单 `file` 须存在）；② 契约侧三条约定无机械门控（Kaiwu 侧有 `同步完成`/`per-hart`/`QEMU` 检索判据），语义靠人工判据兜底；③ 完成区「新发现⑤」已核实属实——`m14-testcases-005` 仍写 `[16]/[20]/[28]/[29]/[30]/[32]` 与保留区 `[63:33]`，派单前须按 ADR-0056 订正）。

## 完成区

**测试结果**：一键证据 45/45 PASS（判据 1–3 + 15 个门控 + 4 路注入 + L1）；4 路注入均「注入 ⇒ 门控/判据红 ⇒ `cp`+md5 还原 ⇒ 回绿」，diff 非空有校验。
**修改文件**：`spec/Kaiwu-测试机运行环境.md`（新增 `§3.1` 三条约定、`§6.3.5` 撤销 TLB 排除项、`0.4.7-rc` 变更条目）；`.tao/contracts/contract-tlb.md`（新建，43 条 `TLB-nn` + §11 门控建议）；`.tao/contracts/README.md`（加 `contract-tlb.md` 行）；`manifests/spec-readonly.lock.toml`（Kaiwu sha256 重算 + 三条用户原话注记）；**越界披露**：`contracts/linux-boot.yaml` 与 `.tao/contracts/contract-linux-boot.md`（撤销 TLB 排除项、契约版本 0.2.2）——不撤则 `check-linux-boot-contract` 逐项点名 TLB 即红。
**验收结果**：
- 判据 1：`不定义` 句中 TLB 命中 0（原句已撤）；册内「同步完成」2 /「per-hart」2 /「QEMU」8；`DADAO-12 §2.2` 10 处、`§4.5` 8 处。
- 判据 2：条目 43 条（≥14）、缺来源 0 条、`spec-decision` 3 行、版本 `0.7.1` == README 表 SEE / SBI 已发布版、README 表已加行。
- 判据 3：探针 13 行，13 行均含「断言点（大类 + 子原因位）」。
- 判据 4：`check-spec-readonly` = 21 册 OK（Kaiwu 新 sha256 `841d93d2…e07c751`）；`check-spec-refs`/`-purity`/`-changelog`/`-numbering`/`-codeblocks`、`check-rule-refs`、`check-contracts-dir`、`-pending`、`check-contract-relocs`、`check-spec-drift`、`check-interface`、`check-knowledge-refs`、`check-dirs`、`check-linux-boot-contract` 全 rc=0；L1 `make check` rc=0。
- 判据 5：①版本 `0.7.2` ⇒ `check-spec-drift` rc=2；②来源 `§9.9` ⇒ `check-spec-refs` rc=2；③TLB 加回不定义 ⇒ 判据 1 红（命中 1）；④锁 sha 改 1 字符 ⇒ `check-spec-readonly` rc=2。
**新发现/坑**：① `check-linux-boot-contract` 把 `contracts/linux-boot.yaml::not_defined` 当「不定义」的机械真源 ⇒ 撤 spec 排除项必须同笔同步契约 + YAML（跨层耦合，容易漏）；② `check-spec-refs` 对 `[X §9.9 标题]` 只校验标题文本、不校验节号（改错节号不会红），注入须用纯 `§9.9`；③ `check-spec-purity` 禁 `ISS-\d+`/`v5`/`M\d+`/`用户裁定`，`Kaiwu` 里不能写 ISS 号（改落锁注记与契约）；④ 页表页必在可写 PA RAM ⇒ A/D 回写失败的机器级探针不可达，需实现层注入（`tests` 侧设计要改口径）；⑤ **`m14-testcases-005` 任务书的子原因位号与本契约/`contract-see §6.1.1` 不一致**（其写 `[16] IGPTRAP`/`[20] DGPTRAP`/`[28] NRPERM`/`[29] NWPERM`/`[30] NXPERM`/`[32] ADWBFAIL`、保留区写 `[63:33]`；权威为 `[48]`/`[52]`/`[36]`/`[37]`/`[38]`/`[56]`，保留区 `[63:58]`+`[47:40]`）⇒ 派单探针任务前须订正该任务书。
**遗留问题**：无（探针实现与 `tests/arch.yaml` 登记归 `m14-testcases-005`；跨 hart 传播 `ISS-459` 待多 hart 机型）。

