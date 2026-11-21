# m14-testcases-005: `tests/arch` TLB 探针（8 条基础 + ⑨a/⑨b/⑩/⑪/⑫；按子原因断言）

**模块**：testcases
**项目里程碑**：M14
**依赖**：`m14-spec-006`（TLB 契约与 13 条探针清单，**硬依赖**：探针的期望值以契约为唯一来源）；`m14-spec-007`（子原因位表落 `contract-see §6.1`；未落地时位号取 `ADR-0056 D3`）
**可并行分片**：是（载体维度：13 条探针的 `.s` 彼此独立，可分工；**但** `tests/arch.yaml`、`ARCH_CFX_PROBES`、`expected.yaml`、驱动脚本是共享文件 ⇒ 这四处由单一写者串行落）
**并行组**：**可**与 `m14-linux-011` 并行（不同文件域）；**必须早于** `m14-qemu-005` 收口（它的「先红后绿」要以本任务的探针为载体）
**预估**：5–6 h
**档位**：中改（多文件探针 + 清单/索引；复核 ≥4 路注入——取中改上限，因本件是 TLB 语义的判据载体）
**状态**：已验证

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
5. **`tests/arch.yaml` 是否登记 13 条**（`m14-testcases-005` 落地时的自决与偏离）：任务书「接线」段要求 `arch.yaml` 新增 13 条 `file: arch/ptw/<name>.s`，但本任务 13 条**全部**需要自建页表/直写 `cfx_ptw`（含 ⑨a/⑫），载体只能是 min-ROM 驱动（`ARCH_CFX_PROBES` 的既有形态，如 `integ040t`），`tests/arch/` 下无 `.s` 可执行载体。**自决：不建 13 个空壳 `.s`、不写幽灵索引**；改为 `tests/arch/ptw/expected.yaml` 登记 13 个 `arch-ptw-00N`（清单 + 来源 §），并让驱动 `--selfcheck` 与其双向核对；`tests/arch/README.md` 写明 `ptw/` 无 `.s` 载体。若裁定要求必须进 `arch.yaml`，需同时新增 13 个真实 `.s`（即另做一版用户态载体）或放宽 `check-tests-index` 的 `file` 语义。
6. **`ARCH_CFX_PROBES` 现登记 `tlb` ⇒ L3 `check-arch` 处于红窗口**（11 条断言：7 条子原因 + 4 条 monitor 路由；见完成区）。这与任务书「`check-arch` 全绿」冲突，但与 `m14-qemu-005`「探针先红后绿」的设计一致。**自决：保持登记**（红窗口即它的判据载体）；若主会话要求 L3 在 QEMU 侧补齐前保持绿，只需从 `ARCH_CFX_PROBES` 去掉 `tlb` 一项（驱动与清单不动，`m14-qemu-005` 仍可用 `--only` 取证）。
   - **红窗口已关闭（2026-11-17 返工轮）**：`m14-qemu-005` 落地后 `tlb` 29/29 全绿，`make check-arch` rc=0。
7. **`m14-qemu-005` 范围需扩充**：其任务书只列「子原因未填 / 不得部分完成 / 命中路径同表」三缺口，未含「非页表类 `CFXMEM` 未进 monitor」（Vast `sync_exc_monitor_entry=false`）。⑨a 与 ⑫ 反例的判决依赖后者，建议把该缺口并入 `m14-qemu-005`（或单立任务），否则 4 条断言会长期红。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-16）

**判决**：实现自审通过；11 条断言红全部落到两处 QEMU 缺口（不是探针缺陷），已在「待裁定 5–7」与完成区登记。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 成功路径断言「`cause_id==0`」恒红：prelude 的 power→hmon 用 `trap cfx_hmon`，帧里已有 `CFXTRAP` | ✅已修 | 改为「取基线帧 → 断言基线 wyde2/wyde3/[31:16] 全 0 → 结尾断言帧未变」 | 13 条成功路径检查全绿 |
| F2 故障断言失败时可能挂死：失败路径在「PTBR 已换表/ptw 关闭」状态下存 `exit_block` ⇒ 再缺页 ⇒ 进 prelude 向量死循环（实测 TIMEOUT） | ✅已修 | 新增统一失败出口：先恢复 PTBR=prelude 表 + `ptw_enable=1` + invalid-all，再 `SYS_EXIT` | 注入 8 路「绿→红」均返回确定的失败码，无 TIMEOUT |
| F3 故障探针存在「不故障也通过」的静默通路 | ✅已修 | handler 用 `add.si` 计次（rd14）；resume 类在恢复后断言计次；取指类/终结类补「必须故障」失败出口 | 注入 `relax-pte-to-ram`（PTE 移到可写 RAM ⇒ 无回写失败）⇒ `flush_adwbfail` 以「handler 应跑 2 次」红 |
| F4 取指故障按 `[ip,+4]` 续跑会再次缺页（`cause_ip` = 被取地址本身） | ✅已修 | ⑨b-取指、⑩-X=0 改由 handler 终结（`resume=False`） | 两条检查在子原因放宽后转绿（隔离注入） |
| F5 子原因位号若写死会漂移 | ✅已修 | 运行期解析 `contract-see §6.1.1` 并与 `spec/DADAO-12 §3.6` 逐位核对；`expected.yaml` 与驱动双向核对 | `--selfcheck` rc=0（18 子原因 / 11 cause） |
| F6 驱动里未使用的导入/常量/函数 | ✅已修 | 删 `struct`/未用的 profile 载入/`VA3`/`read_info`；补 `0x80–0xBF` 退出码段解码 | `python3 -c ast.parse` + 全跑无回归 |

**逐条结果（13 case / 26 检查；`--only` 单跑一致）**

| # | case | 检查（大类 + 子原因 + info） | 结果 |
|---|---|---|---|
| 1 | arch-ptw-001 | fill_hit：无异常，两次同值 | PASS |
| 2 | arch-ptw-002 | hit_no_reread：无异常，读旧 PA | PASS |
| 3 | arch-ptw-003 | invalid_va：无异常，X 重步进 / Y 仍命中 | PASS |
| 4 | arch-ptw-004 | range_hit/scope_all 无异常；range_size0/scope_reserved：`CFXREG` + info=指令编码 | PASS |
| 5 | arch-ptw-005 | asid_any0_keeps_g / asid_any1_takes_g / g_cross_asid | PASS |
| 6 | arch-ptw-006 | clean_vs_invalid：A/D 回写+留条目 vs 不回写+删 | PASS |
| 7 | arch-ptw-007 | flush_ok：A/D 回写+删除 PASS；flush_adwbfail：`CFXMEM`+`[56] ADWBFAIL`+info=PTE PA | **FAIL（wyde3=0）** |
| 8 | arch-ptw-008 | no_implicit_invalidate：四次写后仍命中 | PASS |
| 9 | arch-ptw-009 | ptw_off_bypasses_tlb / ptw_off_no_entry：`CFXMEM` + `[57] NONPTW` | **FAIL（无 monitor 帧，机器 fault `0xF1`）** |
| 10 | arch-ptw-010 | data_unmapped `[52] DGPTRAP` / fetch_unmapped `[48] IGPTRAP` | **FAIL（wyde3=0）** |
| 11 | arch-ptw-011 | nwperm `[37]` / nrperm `[36]` / nxperm `[38]` / nhperm `[35]` | **FAIL（wyde2=0）** |
| 12 | arch-ptw-012 | edit_then_invalidate：旧映射 → 显式失效 → 新映射 | PASS |
| 13 | arch-ptw-013 | pmem_bypass：全空页表下 cfx_pmem 读写 | PASS |
| 13 | arch-ptw-013 | reserved_cfx_ptw_on / _off：`CFXMEM` + `[57] NONPTW` | **FAIL（无 monitor 帧，机器 fault `0xF1`）** |

**注入（11/11，`cp`+md5，还原后 md5 与基线逐字一致）**：8 路绿→红→回绿（`case3-invalid-to-none`/`case4-range-outside`/`case5-asid-any-flip`/`case6-clean-to-invalid`/`case7-flush-to-clean`/`case8-drop-invalidate`/`case12-drop-invalidate`/`case13-marker-flip`）；`relax-subcause`（子原因期望归零 ⇒ 7 条子原因检查翻绿、4 条 monitor 路由仍红 ⇒ 隔离出两处缺口）；`relax-pte-to-ram`（放宽后 PTE 移入可写 RAM ⇒ `flush_adwbfail` 再红）；`relax-subcause-neighbour`（放宽后 NWPERM 期望换成 NRPERM ⇒ 该条红、同 case 其余三条绿 ⇒ 子原因断言非恒真）。

### 第 2 轮 engineer 自审（返工，2026-11-17）

**判决**：返工完成 —— `sub_one_hot` 位口径改为绝对位、`m14-qemu-005` 两例入仓；29/29 检查 + 15 探针门控全绿，7 路注入均「注入⇒红⇒还原⇒回绿」。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `sub_one_hot()` 返回 **wyde 内相对位**，而断言用绝对 64 位掩码 ⇒ 11/26 恒红 | ✅已修 | 改 `1 << SUB_BIT[name]`（绝对位号，`contract-see §6.1.1`）；`wyde_values()` 改为返回「期望的 `cause_id & WYDE2/WYDE3`」 | 改前 **15/26（11 红）**，逐条落在 `wyde3 == …`/`wyde2 == …` → 改后 **26/26**；回退注入在终版 15 case 上 ⇒ **16/29**，13 红 == 带子原因的检查数（现场派生） |
| F2 失败码 `(case-1)*9+field` 在 15 个 case 下需 135 个码 ⇒ 撞上机器 fault 退出段 `0x80`–`0xFF` | ✅已修 | 改为「**镜像内**断言序号」（`0x01`–`0x7F`）：每检查一个独立 ROM 镜像，驱动按所跑检查解码；`MAX_FAIL_CODE` 守上限 | 全跑/逐条 `--only` 全绿；注入逐条定位到 `assertion N: <描述>` |
| F3 两例只在运行期取证、未入仓 | ✅已修 | 收编为 `arch-ptw-014`（`flush_stop_after`/`flush_stop_kept`，TLB-37）与 `arch-ptw-015`（`illi_insn_word_window`）；`Check` 增 `image_at`/`hmon_extra` 传参 | `--only` 各自 rc=0；全跑 29/29；`expected.yaml` ↔ 驱动双向核对（`--selfcheck`）rc=0 |
| F4 `arch-ptw-015` 的「必须故障」码不可达（stub 尾部写死 `0x7E`） | ✅已修 | stub 尾部 exit 码 = 该检查的「必须故障」失败码 | 注入「store 改可写页」⇒ `assertion 1: the store into the ROM must fault` |
| F5 TLB-37 不固定遍历顺序，探针按**插入序**命名「第 2 条」 | ⏸延后（已文档化） | `_c014` docstring + `expected.yaml` 注明该假设 | 见「新发现/坑」① |
| F6 `ARCH_CFX_PROBES` 注释与 `tests/arch/README.md` 的「13 条」过期 | ✅已修 | Makefile 注释行、README 两处改 15 条 | `check-arch` 日志 15 条 `[id]`、`tlb` 29/29 |

**逐条结果（15 case / 29 检查）**：001–013 = 26/26（`sub_one_hot` 修复后全绿）；014 = 2/2（`flush_stop_after`：失败前条目 A/D 已回写、失败后条目 PTE 未动；`flush_stop_kept`：失败条目仍命中旧 PA 且 PTE 未变、第 3 条未处理；帧 = `CFXMEM` + `[56] ADWBFAIL` + `cause_info` = 第 2 条 PTE 物理地址 = `0xffffffd00000`）；015 = 1/1（`ILLI` + `cause_info` = `0x21103000` = 探针自身 `st.o rd4, rb3, 0` 的编码）。

**注入（7 路，`cp`+md5，还原后 md5 与基线逐字一致）**：`sub-relbit`（回退位口径）、`case14-info-va`（`cause_info` 换访存地址）、`case14-stop-after`（假装第 3 条已处理）、`case14-sub-nonptw`（子原因换 `NONPTW`）、`case15-illi-info`（期望换相邻指令字）、`case15-illi-zero`（期望 0 ⇒ 证明「静默 0」判红）、`case15-no-fault`（ROM store 改可写页）。

### 第 3 轮 reviewer 验收（2026-11-17）

**判决**：**Accepted**（中改档 ≥3 路自设计注入 + 门控 + diff 全过）。

- **重跑**（当前安装根 QEMU md5 `0acc25bf…`）：`--list` 15 case/29 检查 rc=0；`--selfcheck` PASS（§6.1.1 ≡ spec §3.6，18 子原因/11 cause）；全量 `29/29 checks passed` rc=0；`--only 014` 2/2、`--only 015` 1/1 rc=0；`check-tests-index` **472 条 PASS**、`check-dirs` PASS、`check-no-residue` PASS；手动跑 `ARCH_CFX_PROBES` **15 成员全绿**（`check-arch: [id]` 行数 15 == 成员数，`tlb` 29/29）。
- **位口径**：`sub_one_hot = 1 << SUB_BIT[name]`（绝对位号，运行时解析 §6.1.1 + 交叉核对 §3.6，不一致即 abort）；`wyde_values` 返回 `(cause_id & WYDE2/WYDE3)` 绝对掩码；断言**未放宽**（仍 `a_masked` 逐 wyde 比绝对位 + `[31:16]==0`）。与 §6.1.1 逐位一致。
- **两例期望**：014 用 `VA[41:29]` 选 L1 索引（VX/VY/VZ=0/1<<29/2<<29 → L1[0]/[1]/[2]），Y 的 leaf PTE 放 ROM `image_at`（只读 BootROM）⇒ flush 回写必失败，`info=ROM_L2`=该 PTE PA，符合 TLB-37/ADR-0041 D3.2/§4.5；015 `0x21103000 = st_o(4,3,0) = 0x21<<24|4<<18|3<<12|0`，由 `contracts/opcodes.yaml`（opc 0x21, rdha[23:18], rbhb[17:12], imms12[11:0]）独立推出，ILLI `info=指令字` 依据 ADR-0004 D5.6/contract-see §6.1。
- **3 路自设计注入**（`cp`+md5，md5 均还原为基线 `7f3549…`）：① `sub_one_hot` 回相对位 ⇒ **13 红/16 绿**（16/29，红点全在 `wydeN == <子原因>`）；② 014「第 3 条不处理」改"已处理" ⇒ **2 红**（assertion 9/10 `entry 3 …was not processed`）；③ 015 `cinfo` 换 `st_o(4,3,4)` ⇒ **1 红**（`cause_info == 0x21103004`）。均「注入⇒红⇒还原⇒回绿」。
- **`arch.yaml` 未登记偏离**：**可接受 + 记遗留**。15 条 ptw 载体是 min-ROM 驱动（无 `.s`），`check-tests-index` 规则 5 要求 `file` 实际存在（登记必建空壳 `.s`）；与既有 `integ039t` 等同形态（走 `ARCH_CFX_PROBES`、不进 `arch.yaml`）。`expected.yaml`+`--selfcheck` 双向核对已覆盖清单一致性。是否另做用户态 `.s` 载体进 `arch.yaml` 请架构师裁定（遗留①）。
- **越界**：diff 仅 5 文件（`min_rom_probe_tlb.py`/`expected.yaml`/`Makefile` 注释/`README.md`/任务书），未碰 `spec/`、`contracts/`、`components/**`、`tests/inst/**`、`node_probe_prelude.py`、`run_m5_e2e.py`。
- **环境干扰**：`check-arch-smoke` 本轮 **REFUSED rc=75**——`m14-qemu-007` 的 `install-host` writer（pid 961077，自 07:39）活跃重建工具链，非交付物缺陷；采信 engineer 05:18 证据日志（`check-arch-smoke: PASS`、`check-arch: PASS` 15 成员、qemu md5 `f8b6c575…`）。
- **finding（不阻断）**：完成区「QEMU 安装根 md5 `115654a9`」与实际不符（05:18 证据为 `f8b6c575`、当前 `0acc25bf`），系 md5 笔误，建议主会话收尾订正。

## 完成区

**测试结果**：15 case / **29 检查 29/29 PASS**（QEMU 安装根 md5 `115654a9…`）；`--only` 逐条 rc=0；`make check-arch` **rc=0**（15 个 `ARCH_CFX_PROBES` 成员 == 日志 15 条 `check-arch: [id]`，14 条既有探针 + `tlb` 全绿）、`check-arch-smoke` rc=0；`check-tests-index`（472 条）/`check-dirs`/`check-no-residue` rc=0；证据脚本绿路径 31 项、注入 43 项全过。
**修改文件**：`tools/testcases/arch/min_rom_probe_tlb.py`（`sub_one_hot` 绝对位、失败码改镜像内序号、新增 014/015、`Check` 增 `image_at`/`hmon_extra`）、`tests/arch/ptw/expected.yaml`（新增 014/015 + 来源 § + 顺序假设注）、`Makefile`（`ARCH_CFX_PROBES` 注释行 13→15 条；成员未变）、`tests/arch/README.md`（`ptw/` 行与门控行改 15 条）、本任务书。
**验收结果**：`sub_one_hot` **改前 15/26（11 红）→ 改后 26/26**；`--selfcheck` rc=0（`contract-see §6.1.1` ≡ `spec/DADAO-12 §3.6`，18 子原因/11 cause；15 case/29 检查 ↔ `expected.yaml` 双向一致）；`--list` 15 case/29 检查；注入 7 路（`cp`+md5 还原，均「注入⇒红⇒还原⇒回绿」，红点逐条定位到 `assertion N`）。
**新发现/坑**：① `TLB-37` 只固定「停在首个失败条目、其后不处理」，**不固定遍历顺序** ⇒ 014 的「第 1/3 条」判定以插入序为前提（已在 docstring 与 `expected.yaml` 注明）；跨实现（chipyard/gem5）跑该例前需确认遍历顺序口径。② 失败码上限 `0x7F` 与「一镜像一断言集」才是可扩展口径：`(case-1)*9+field` 在 15 case 下溢出到机器 fault 退出段。③ `ILLI` 的 `cause_info` 在内存窗口 IP 上必须靠 guest TLB 页基 + 页内偏移回读（`dadao_insn_word`），探针只需断言「等于该 IP 上的指令编码」即可同时否掉「静默 0」与「访存地址」（后者由 `case15-illi-zero`/`case14-info-va` 两路注入证）。
**遗留问题**：① `tests/arch.yaml` 仍未登记 `arch-ptw-*`（沿「待裁定 5」自决：无 `.s` 载体、`check-tests-index` 要求 `file` 真实存在，登记清单落 `tests/arch/ptw/expected.yaml` 并由 `--selfcheck` 双向核对）；要进 `arch.yaml` 须另做真实 `.s` 载体或放宽 `file` 语义，请裁定。② `tools/testcases/arch/node_probe_prelude.py`、`tools/testcases/parity/run_parity.py` 的 docstring 仍写「13 `ARCH_CFX_PROBES`」（本任务禁改，建议主会话补一行）。③ 「取不到 ⇒ `error_report + exit(1)`」是 QEMU 侧行为（`m14-qemu-005` 已实现），本任务只由探针断言 `cause_info == 指令编码`（不等即红）覆盖，未在 `components/**` 侧复注入（越界）。
