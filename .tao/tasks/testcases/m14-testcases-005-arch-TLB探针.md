# m14-testcases-005: `tests/arch` TLB 探针（8 条基础 + ⑨a/⑨b/⑩/⑪/⑫；按子原因断言）

**模块**：testcases
**项目里程碑**：M14
**依赖**：`m14-spec-006`（TLB 契约与 13 条探针清单，**硬依赖**：探针的期望值以契约为唯一来源）；`m14-spec-007`（子原因位表落 `contract-see §6.1`；未落地时位号取 `ADR-0056 D3`）
**可并行分片**：是（载体维度：13 条探针的 `.s` 彼此独立，可分工；**但** `tests/arch.yaml`、`ARCH_CFX_PROBES`、`expected.yaml`、驱动脚本是共享文件 ⇒ 这四处由单一写者串行落）
**并行组**：**可**与 `m14-linux-011` 并行（不同文件域）；**必须早于** `m14-qemu-005` 收口（它的「先红后绿」要以本任务的探针为载体）
**预估**：5–6 h
**档位**：中改（多文件探针 + 清单/索引；复核 ≥4 路注入——取中改上限，因本件是 TLB 语义的判据载体）
**状态**：待验收

## 背景

`tests/arch` 现有 10 条 `umon/*.s`（SEE/semihosting + cfx 级权限）与登记在 `Makefile` `ARCH_CFX_PROBES` 的一批 `min_rom_probe_*`（cfx 场景探针，由 `make check-arch` 逐条跑），**没有任何一条覆盖 TLB**。而 K3 的硬件语义目前只有「QEMU 里有实现」这一个事实来源——按 `AGENTS.md`「Independent oracle」，期望值必须独立派生自 `spec/`，不能从实现反推。

两条载体约束先定清（决定每条探针放哪里）：

- **需要自建页表 / 直写 `cfx_ptw` 寄存器**的 ⇒ 走 `min_rom` 路线：`tools/testcases/arch/node_probe_prelude.py` 已提供「一个 4 MiB `bootrom-image`、无 `-kernel`」的装载模型，power → hmon 两段在 ROM 内，hmon 段写 4 条恒等超页 PTE 到 `cfx_pmem` SRAM、DMA 到 `PT_PA`、失效 TLB、写 PTBR + `ptw_enable=1`，然后跳 body（hmon/hypv）。
- **必须在 `ptw_enable = 0` 下执行**的（⑨a）**不能**在 RAM body 里跑：关掉 PTW 后连取指都是 `CFXMEM`。这类探针的代码与观测必须落在 **`VA[47:42] ≠ 0` 的 cfx 核内空间（BootROM）**里，即沿用 hmon 段的位置执行，不跳 body。

## 目标

在 `tests/arch/ptw/` 落 13 条探针（载体 `.s`），由**一个**新增驱动 `tools/testcases/arch/min_rom_probe_tlb.py` 承载（`--only <case>` 逐条可跑、`--list` 列名），并完成清单/索引/门控接线。每条探针的核心断言是「**`cause_id[15:0]` 的大类 + `[63:48]/[47:32]` 恰一位且等于 `ADR-0056 D3` 的位号**」（或成功路径断言 `[63:48]/[47:32] == 0`）。

**8 条基础探针**

1. `tlb_fill_hit`：首次访问一个未映射 VA ⇒ 步进成功、填充、访问完成（读到该页的初值）；再访问同一页 ⇒ **命中且不产生异常**（读回同一标记）。严格判据是「命中不重读 PTE」，由第 2 条承担；本条只证明「首次缺页后第二次不再缺页」。
2. `tlb_hit_no_pte_reread`：fill 后**改 PTE 的 PPN（指向另一页）但不 invalidate** ⇒ 再访问仍落到**旧** PA（在两页分别写不同标记，读回旧标记即证明命中未重读 PTE）。
3. `tlb_invalid_va`：同页两条 VA（或同页内两个偏移）命中后，`invalid` + `scope=VA` + `start` 落该页 ⇒ 该页条目消失（再访问走步进并**看到新 PTE**）、**其它 VA 的条目仍在**（仍命中旧映射）。
4. `tlb_invalid_range`：`scope=range` 覆盖两条条目中的一条 ⇒ 只有相交者失效；`range && size=0` ⇒ `CFXREG`；`scope=11` ⇒ `CFXREG`；`scope=all` 忽略 start/size（start 写成乱值仍全失效）。
5. `tlb_asid_g`：造 `G=0`（ASID=A）与 `G=1` 各一条；`ASID_ANY=0` 且当前 ASID=A ⇒ 只失效 `G=0`（`G=1` 仍命中）；`ASID_ANY=1` ⇒ 两条都失效；切 ASID=B ⇒ `G=0`（A）不命中、`G=1` 命中（跨 ASID）。
6. `tlb_clean_ad`：读一次（置 A 挂起）⇒ `clean` ⇒ **PTE 的 A 被原子 OR 回写**、条目**保留**（再访问仍命中）；对照组：写一次（置 A/D 挂起）后直接 `invalid` ⇒ PTE 的 D **仍为 0**（`invalid` 不回写），且条目消失。
7. `tlb_flush_adwb_fail`：`flush` 正常路径 ⇒ A/D 回写且条目删除（再访问走步进）；**回写失败路径** ⇒ 在**只读**区域放目标 PTE（见「载体提示」），`flush` ⇒ 该写指令上报 `CFXMEM` + 子原因 `[32] ADWBFAIL`，`cause_info` = **该 PTE 的物理地址**，且条目**未被删除**（随后 `invalid` 仍能删它 ⇒ 证明它还在）。
8. `tlb_no_implicit_invalidate`：fill 后分别写 `PTBR`（同值/异值）、写 `ASID`、写 `ptw_enable=1` ⇒ 三次都不清 TLB（原条目仍命中旧映射）；随后显式 `invalid`+`all` ⇒ 才走步进看到新 PTE。

**5 条 K3 扩展探针**

9. `⑨a ptw_off_direct_cfxmem`：`ptw_enable=0` 时对 `VA[47:42]=0` 的普通访存 ⇒ **直接 `CFXMEM`**，且 `cause_info` = 访存地址、子原因按「待裁定 2」（默认 0）；**不产生 TLB 条目**（恢复 `ptw_enable=1` 后该页仍走步进/仍未映射）。在 ROM 内执行（见背景）。
10. `⑨b ptw_on_unmapped`：`ptw_enable=1` + 页表未映射（L1 `P=0`）⇒ `CFXMEM` + 子原因 `[48] IGPTRAP`/`[52] DGPTRAP`（按取指/数据分别断言）、`cause_info` = 访存地址。
11. `⑩ perm_denied_cfxperm`：写一个 `W=0` 的页 ⇒ `CFXPERM` + 子原因 `[37] NWPERM`；读一个 `R=0` 的页 ⇒ `[36] NRPERM`；取指一个 `X=0` 的页 ⇒ `[38] NXPERM`；HSJU：把当前运行模式对应的位置 0 ⇒ `NUPERM`/`NJPERM`/`NSPERM`/`NHPERM` 中对应那位（探针按自己运行的 cfx/mode 现场选，不写死）。三条与 `CFXMEM` **可区分**（大类不同）。
12. `⑪ pte_change_needs_invalidate`：改 PTE 后**不** invalidate ⇒ 仍命中旧条目（与 `tlb_hit_no_pte_reread` 同一现象、不同载体：本条按「改映射语义」组织，附带断言改后 `invalid`+VA ⇒ 命中新 PTE）。
13. `⑫ cfx_space_bypasses_ptw`：`VA[47:42] ≠ 0` 的访问**不走 PTW/TLB**。正例：访问 `cfx_pmem` SRAM 内偏移（已实现的空间）在 `ptw_enable=1`、页表**故意全空**（L1 全 0）的页表条件下仍能读写成功；反例：访问未实现/保留 cfx 的普通访存 ⇒ 得到 `CFXMEM`，但其子原因**不得**是页表「未映射」类（`IGPTRAP`/`DGPTRAP` 等），且 `ptw_enable=0` 时同一地址语义不变（不依赖 PTW 开关）。

**接线**

- `tests/arch.yaml` 新增 13 条 `arch-ptw-001`…`arch-ptw-013`（`file: arch/ptw/<name>.s`、`platforms: [system]`、`level: full`、`requires: [bootrom, ptw]`），字段恰好五项（`check-tests-index` 校验）；
- `tests/arch/expected.yaml`（或新增 `tests/arch/ptw/expected.yaml`，二选一并在 README 写明）：每条 case 的期望大类、期望子原因**位号来源**（`contract-see §6.1` 的符号名，不写魔数）、退出码、观测通道；
- `Makefile` 的 `ARCH_CFX_PROBES` **追加一个** id（驱动文件名），并在其上的注释块加一行说明；
- `tests/arch/README.md` 增加 `ptw/` 一行（目录/cfx/内容）与探针清单指针。

## 增补要求（`m14-qemu-005` 复核，2026-11-17）

### 1. 修 `min_rom_probe_tlb.py::sub_one_hot()` 的位口径 bug（必须）

现状：`sub_one_hot()` 返回的是 **wyde 内相对位**（`DGPTRAP` ⇒ `0x10`），而断言用**绝对 64 位掩码** ⇒ 11/26 条恒红（`m14-qemu-005` 实测）。

- 改为返回**绝对位**（`1 << 绝对位号`，位号取 `contract-see §6.1.1`）；
- 修完必须给「**先红后绿**」证据：改前 11 条红、改后 26/26；
- 不得通过放宽断言（比如改成只比大类）来"修绿"。

### 2. 收编 `m14-qemu-005` 的两个临时例（必须）

该任务的以下两例当时只在运行期取证、未入仓，由本任务收编（落 `tests/arch/ptw/**` + `tests/arch.yaml` 登记）：

- **三条目「遇错即停」**：第 1 条正常、第 2 条 A/D 回写必失败、第 3 条正常 ⇒ 断言第 1 条已处理、**第 2 条原样保留**、**第 3 条不处理**；帧 = `CFXMEM` + `ADWBFAIL` + `cause_info` = 第 2 条的 PTE 物理地址；
- **内存窗口 IP 的 `ILLI`**：`ptw_enable=1` 且异常 IP 落在**内存窗口**内 ⇒ `cause_info` 由「guest TLB 页基 + 页内偏移」算出 PA 回读；取不到 ⇒ 必须 `error_report + exit(1)`（不得静默 0）。

## 验收（逐条贴真实 rc）

1. `make check-arch-smoke` rc=0（不回归）；`make check-arch` rc=0，且日志中新增探针逐条出现（**计数现场统计**，检查 ARCH_CFX_PROBES 的成员数 == 日志里的 `check-arch: [<id>]` 行数）。
2. `python3 tools/testcases/arch/min_rom_probe_tlb.py --list` 列出 13 个 case；`--only <case>` 逐条 rc=0；不指定时全跑 rc=0。
3. **每条探针能 FAIL**：≥6 条各做一路注入（其余至少 `--selfcheck` 覆盖翻转），示例注入（`cp`+md5 还原）：把 `invalid` 换成 `none`、`ASID_ANY` 置反、`range` 起点挪出页、`G` 位写反、期望子原因换成相邻位、把只读 PTE 换到可写页（`ADWBFAIL` 就不再发生 ⇒ 该断言必红）。逐路贴「注入后哪条断言红 + 还原后回绿」。
4. 子原因断言**逐位现场派生**：期望位号从契约解析（不写死数字）；成功路径断言 `[63:48]/[47:32]==0`；每条故障探针额外断言 `[63:33]==0`（保留区）。
5. `check-tests-index` rc=0（索引↔载体双向、字段五项、id 全局唯一）。
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树。
2. **只改**：`tests/arch/**`、`tests/arch.yaml`、`Makefile`（`ARCH_CFX_PROBES` 一行 + 注释一行）、`tools/testcases/arch/min_rom_probe_tlb.py`（**新增**驱动）。**不改**既有 `min_rom_probe_*.py`、`node_probe_prelude.py`、`run_m5_e2e.py`；**不改** `components/**`、`tools/linux/**`、`spec/**`、`.tao/contracts/**`、`tests/arch/ptw/*.s`（现有向量）。
3. 不提交 git；注入还原 `cp` + md5；权限/模式等 `defsym` 参数用 `DADAO_TEST_PROFILE=vast`。
4. 期望值**不从 QEMU 输出反推**：探针在 **guest 内**自检（读回 `cfx2rd` 的 `cause_id`/`cause_info`、PTE 内容、标记字），host 只判退出码与清单；`expected.yaml` 的每一项必须写「来源 §」。
5. 单条探针的执行时间要能进 L3（避免轮询大循环）；不得用 `-d` 逐指令日志。
6. 驱动必须能被 `make check-arch` 直接调用：`check-arch` 的调用形式是 `DADAO_TEST_PROFILE=vast python3 tools/testcases/arch/min_rom_probe_<id>.py --qemu <qemu 路径>`，故新驱动必须接受 `--qemu`（并沿用 `node_probe_prelude` 的 profile 解析），不得要求额外环境变量。

## 载体提示（非判据，省时间的实现路线）

- **`ADWBFAIL` 怎么造**：BootROM 是 `memory_region_init_rom`（只读）。把 PTBR 指向 ROM 内的一张页表、把目标 leaf PTE 放在 ROM 里 ⇒ 步进**读得到**、`clean`/`flush` 的原子 OR 回写**写不进** ⇒ 得到「读成功、写失败」，正是 `spec/DADAO-12 §4.5` 的回写失败场景。别忘了 `cause_info` 要断言成该 PTE 的物理地址（不是 VA）。
- **⑨a/⑫ 的位置**：这两条要在 hmon 段（ROM）内完成，不要跳 body；`ptw_enable=0` 时 body 的取指会直接 `CFXMEM`。
- **`flush` 后条目真的删了（对应第 7 条）**：不要只看「再访问还能成功」（可能又填充），要断言「再访问时步进侧观测到一次 miss」（探针可让 PTBR 指向另一张表后 `flush`，再访问 ⇒ 若条目还在就命中旧 PA、不在就落到新表）。

## 待裁定

1. **驱动的粒度**：`ARCH_CFX_PROBES` 的每个条目对应**一个** `min_rom_probe_<id>.py`（`check-arch` 按文件名循环）⇒ 建议 13 个 case 由**一个**驱动承载（`min_rom_probe_tlb.py`，`--only` 逐 case），登记一个 id。替代方案是每条一个驱动、登记 13 个 id（`check-arch` 会起 13 次 QEMU，慢但仍可）。**建议前者**。
2. **`CFXMEM` 非页表类子原因**（与 `m14-qemu-005` 待裁定 2 同一问题）：⑨a 与 ⑫ 涉及的 `CFXMEM` 在 `ADR-0056 D3` 无位号。建议 `[63:48]/[47:32]=0` 并在契约里写明「页表类恰一位、非页表类为 0」；若裁定要求一律 one-hot，本任务相应断言改为新位。
3. **⑩ 的 mode 取位**：探针跑在 hmon/hypv ⇒ HSJU 不匹配应命 `[27] NHPERM`。是否需要在同一个探针里再切一次 run mode 覆盖 `NSPERM`？（建议：只覆盖当前模式，另用 `arch-ptw` 的下一条 case 覆盖 supv；不引入逐 mode 穷举。）
4. **`level` 取值**：13 条都定 `full`（由 L3 `check-arch` 覆盖）。若希望其中「fill/hit」「invalid VA」进 L2 代表集（`check-arch-smoke`），需改 smoke 的成员定义（会加长 L2）——**默认不进**。

## 审阅记录

（待填）
