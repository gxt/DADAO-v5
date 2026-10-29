# INTEG-039t: Step 2 落地（PTE/页表步进/页权限）

**模块**：integ
**项目里程碑**：M10
**依赖**：ADR-0039（地址空间/PTBR）、ADR-0040（PTE/页表/权限）、master `e601034b`
**状态**：已验证

## 背景
Step 1 已落地单 PTBR/`ptw_enable`，但 `ptw_enable=1` 仍是显式 fail-closed；`spec/DADAO-12` §2.2.3/§2.2.4 仍是旧 PTE 布局（32 位 PPN、顶部 SPF/GPF）。本任务按 ADR-0040 实现页表步进与页权限，**不做 TLB/A-D/DMA/启动**。

## 目标
1. **spec（DADAO-12 §2.2.1–§2.2.6）**
   - PTE 64 位：HSJU `[63:60]`、PPN `[55:16]`/超页 `[55:29]`、SPF/GPF `[15:8]`、flags `[7:0]`（P=0/SP=1/D=2/A=3/X=5/W=6/R=7）；保留位/PPN 低位按 ADR-0040 D9。
   - L1 next-level、L1 超页、L2 普通页；L1/L2 64 KiB、8192 项；索引 `VA[41:29]`/`[28:16]`，页内 `[15:0]`；PA56。
   - HSJU 访问规则；SPF/GPF 8 位小页存在位（64 MiB/8 KiB，`VA[28:26]`/`[15:13]`）；位 0 的 fault 编码。
   - 异常优先级：`P=0`/超页缺失 → SPF/GPF=0 → HSJU → R/W/X；`NUPERM/NJPERM/NSPERM/NHPERM`、`NRPERM/NWPERM/NXPERM`、`IGPTRAP/ISPTRAP/IGPFTRAP/ISPFTRAP` 及 D 对应；页表异常进 `cfx_ptw`。
   - A/D 只定义、不更新（Step 3）；保留位忽略、PPN 低位强制清零。
   - 同步 contracts/spec 引用、`manifests/spec-readonly.lock.toml`、changelog。
2. **QEMU**
   - 用页表步进替换 `ptw_enable=1` 的显式失败；从 PA 读 PTE，检查 P/SP/SPF/GPF/HSJU/RWX，形成 PA56；错误按上述异常。
   - 不实现 TLB、A/D 更新、DMA、启动；不改变 Step 1 的地址分区/PTBR/CFXMEM 语义。
3. **测试**
   - 页表步进：L1 next-level + L2、超页、PA56、页内偏移。
   - 缺失/权限：L1 P=0、L2 P=0、SPF/GPF 位 0、HSJU 四模式、R/W/X、优先级。
   - 保留位忽略、PPN 低位清零、PTBR/页表在 pmem；A/D 不更新（断言）。
   - 覆盖 QEMU 探针/单元/向量；不改 oracle 生成方式。

## 验收
- `make check`、`make check-modules`、`make check-arch-smoke`、`make check-lit`、`check-spec-readonly`、`check-spec-changelog`、`check-patch-tree`、`check-source-state` 全 rc=0。
- 证据 `.work/evidence/<任务号>/run.sh`：注入→FAIL→`cp`+md5 还原→PASS。
- 不改 TLB/A-D/DMA/启动/HSJU 之外的 Step 3+；不跑 `check-full`/夜跑。
- 完成区 ≤30 行；任务书与 `milestones.md` 置 `待验收`；临时目录 `/tmp/opencode/INTEG-039t/`。

## 约束
- 只做 Step 2；不做 Step 3–6。
- 不提交、不 push；长构建先申报。
- 用户已授权 Step 1 的额外 spec 同步；本任务新增 spec 改动须在完成区列出并说明。

## 完成区

**状态**：已验证

**测试结果**：新探针 37/37；回归 044t/045t/049t/integ038t 全 PASS；证据脚本 23/23（注入→FAIL→cp+md5 还原→PASS）。

**修改文件**：
- spec：`DADAO-12`（§2.2.1–§2.2.6 按 ADR-0040 重写、§4.5 引用、附录 0.7.3-rc）、`Machine-01`（§1.2/§3、附录）、`manifests/spec-readonly.lock.toml`（两册 sha）。
- contracts：`contract-see.md`；`contract-cfx-aliases.md`（生成器重算，仅 spec 行号变化）。
- QEMU：`.work/source/qemu/target/dadao/{cpu.h,cpu.c,helper.c}` + 三份导出补丁；`components/qemu/changelog.md`。
- 测试：新增 `tools/testcases/arch/min_rom_probe_integ039t.py`（37 例）；改 `min_rom_probe_integ038t.py`（fail-closed 用例改为「页表不在 pmem」）；`Makefile` 的 `ARCH_CFX_PROBES`。
- 台账/证据：`milestones.md`、本任务书、`.work/evidence/INTEG-039t/run.sh`。

**验收结果**（真实输出）：`make check` rc=0（L1 PASS）；`make check-modules` rc=0（L2 PASS）；`make check-arch-smoke` rc=0（10/10 + 25-service）；`make check-arch` rc=0（integ039t 37/37）；`make check-lit` rc=0（158/158）；`check-spec-readonly`/`check-spec-changelog`/`check-patch-tree`（205 补丁）/`check-source-state` rc=0；证据 `RESULT: PASS=23 FAIL=0`。

**新发现/坑**：
- PTBR 的 PPN 为**就地位段** `[55:16]`（基址 = PTBR 本身），非右移 40 位值；探针初版按 `>>16` 构造 → 读 PA 0 → 显式失败（已修）。
- HSJU 是页面位 `[63:60]`（H=63…U=60），探针初版把位掩码当 4 位值 → 全部误判 NHPERM（已修）。
- `escape` 不恢复 `inner_cfx_code`（M5 遗留）⇒ ptw 异常处理程序一律直接 SYS_EXIT、不嵌套 escape；跨 cfx 嵌套返回留 Step 3 复核。
- 512 MiB 超页的 fragment≥1 落在 16 MiB RAM 外，fragment 选位用「frag0 ok / frag1 fault」双向证明。
- 页表 PA 不在 pmem 属架构未定义：模型 `error_report`+exit(1)，不臆造 page-fault cause。

**遗留问题**：A/D 更新、TLB/CLEAN/FLUSH/INVALID、DMA、启动、cfx 访问权限、Linux 划分按计划留 Step 3+（本任务只定义 A/D 字段）；`docs/DDLN/` 旧 64-PTBR/perm 描述未改（Step 1 已登记，非本任务范围）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-29）

逐行审查 `helper.c` 页表步进 / `do_interrupt` 页表异常入口 / `cpu.h` 字段与 cause 常量 / cpu.c 复位：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 页表读取用 `cs->as` 时该指针在测试机为 NULL → 读失败 | ✅已修 | 改 `address_space_memory`（pmem 系统地址空间），不经过 PTW/TLB | 37/37 |
| F2 PTE 读失败被当作「页缺失」会臆造 cause | ✅已修 | 单独返回 -1，调用方 `error_report`+exit(1)（架构未定义，fail-closed） | integ038t `ptw_on_unbacked_table` |
| F3 同步页表异常未进 cfx_ptw（Step 1 直接退出码） | ✅已修 | 新 `DADAO_EXCP_PTW_FAULT` + `ptw_fault_cause/info`，`do_interrupt` 走 §5 流程设向量；cfx4 `cause_nonmaskable` 补页级 cause | 探针 rd10/cid4/syncn4 |
| F4 已在关机的路上仍进向量会覆盖干净退出码 | ✅已修 | PTW 分支加 `qemu_shutdown_requested_get()` 守卫（与通用 fault 路径一致） | 全量探针回归 |
| F5 超页 fragment 选位只测 frag0 会漏「VA[28:26] 选位」 | ✅已修 | 加 `spf_frag1_fault`（SPF 仅 bit8，VA[28:26]=1 必 fault） | 37/37 |
| F6 步进只测成功路径不足证精确异常 | ✅已修 | 处理器回读 `excp_cause_ip`→rd12，所有 fault 用例断言精确 IP（取指 fault = 被取指 VA） | 37/37 |
| 范围核验 | — | 无 TLB/A-D 更新/DMA/启动/CFX 权限/Linux 改动；Step 1 地址分区、CFXMEM、PTBR、`ptw_enable` 语义未改 | `git diff` 仅 3 个 QEMU 文件 + 文档 |
| 判决 | — | 无未修 finding；状态 `待验收` | — |

### 第 1 轮 reviewer 验收（2026-10-29）：**Accepted**

**重跑记录**（reviewer 亲自执行，均在仓库根、无 `| tee` 吞码）：
- `make check` rc=0；`make check-modules` rc=0（L2 PASS）；`make check-arch-smoke` rc=0（10/10 + 25-service）；`make check-lit` rc=0（158/158）；`make check-arch` rc=0（044t/045t/049t/integ039t，37/37）。
- `check-spec-readonly` rc=0（21 册；并手工重算两册 sha256：DADAO-12=`a73b9d7f…`、Machine-01=`00cfaea8…`，与 lock 逐字相符）；`check-spec-changelog` rc=0；`check-patch-tree` rc=0（205 补丁）；`check-source-state` rc=0（qemu HEAD=2c3cadc clean=True，源码树与补丁一致）。
- 证据脚本 `bash .work/evidence/INTEG-039t/run.sh` rc=0：`RESULT: PASS=23 FAIL=0`，engineer 注入（禁 HSJU 检查）→ hsju/prio 探针 rc=1、对照 rc=0、cp+md5 还原（`72b3fe06…` 前后相等）→ 回绿，真实输出与完成区声明一致。
- 独立探针重跑：`min_rom_probe_integ039t.py` 37/37 rc=0；回归 044t/045t/049t/integ038t rc=0。

**独立反例注入**（与 engineer 注入点不同）：`cp` 备份 + md5（`72b3fe06…`）后禁用 helper.c 的 L2 GPF 小页检查 → `gpf_frag0_fault` rc=1（cause 未报、0xEE 泄漏）、`prio_gpf_over_perm` rc=1（cause 落为 NRPERM）、对照 `l2_page_load` rc=0；cp 还原后 md5 相等、源码树 0 脏、重建 rc=0、全量探针 37/37 rc=0。全程未用 checkout/restore/stash。

**约束核验**：diff 仅 Step 2 范围（PTE/步进/HSJU/SPF-GPF/RWX/优先级/进 cfx_ptw）；无 TLB、A/D 更新、CLEAN/FLUSH/INVALID、DMA、启动、cfx 权限、Linux 划分；spec §2.2.3/§2.2.4 已收口 ADR-0040 布局、无旧新混用（`bits[47:16]`/顶部 SPF 已清除）；`escape`/`cfx_enter` 主体未被触碰，`ptw_enable=0→CFXMEM` 语义保留并有探针回归；页表 PA 不在 pmem 的 fail-closed（`error_report`+exit(1)，不臆造 cause）已在代码注释/Machine-01/完成区如实披露并被 integ038t `ptw_on_unbacked_table` 断言。任务书/`milestones.md` 均置 `待验收`；完成区 ≤30 行；临时产物均在 `/tmp/opencode/INTEG-039t/`。

**快照对账**：验收前后 `git status --porcelain -uall` 逐行相同（`SNAPSHOT IDENTICAL`），仓库无 `*_tmp*`/`*.orig`/`*.rej` 残留；与完成区「修改文件」清单一致。**判决：Accepted，可提交（待 architect 终审）。**
