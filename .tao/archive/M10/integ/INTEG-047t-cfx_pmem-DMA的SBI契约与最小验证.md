# INTEG-047t: cfx_pmem DMA 的 SBI 契约与最小验证（FID 6/7/8）

**模块**：integ
**项目里程碑**：M10
**依赖**：INTEG-042t（`cfx_pmem` 64 KiB SRAM + cg15 DMA 硬件语义）、INTEG-044t（两轴权限，决定 `trap cfx_pmem` 的来源 mask）、INTEG-046t（step5 启动链，本任务**不得改动**其 smon 主链）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 背景

1. `DADAO-12 §4.9` 已定 `cfx_pmem` cg15 DMA 的**硬件**语义（方向/地址位宽/size 1..2^29、`START` 自清、`BUSY`/`DONE`/`ERROR`/`ERR_CODE`、`BUSY` 期间写被忽略、错误在 `START` 时判定且 `BUSY` 保持 0）。**本任务不改这一段**。
2. `DADAO-22 §9`（`cfx_pmem` 的 SBI 表）只有 FID 0–5（`GET_PM_COUNT`/`GET_PM_START`/`GET_PM_SIZE`/`GET_PM_ATTR`/`ALLOC_PAGE`/`FREE_PAGE`），**没有任何 DMA 封装** ⇒ S-mode 调用方无法在「只用 SBI」的前提下启动/查询块搬运。
3. `INTEG-046t` 明确把「SBI DMA 封装」排除在外（其 smon 直接写 cg15）。当前**仓库无任何 SBI provider 实现**：`spec/DADAO-22 §9` 只有示例级伪代码，`tests/shared/bootrom/step5/smon.S` 不做功能分发。本任务**不**补生产 provider（另立任务），只**定义契约**并给出**测试专用**的最小可执行验证。
4. `WAIT` 语义依赖时钟/定时器；当前测试机无时钟（`cfx_time`/`cfx_hart` 定时器未实现，见 `INTEG-046t` §接口规范 3 的「不得写」清单）⇒ 只能**预留**，不得伪造超时。

## 目标（范围）

1. **spec 正文（唯一真源）**：`DADAO-22 §9` 现有表**后追加** FID 6/7/8 三行 + 表下一段说明 + 该节 `simrisc` 分发示例补 3 个分支与 3 个处理器；`§1` 错误码表追加 `-5 = SBI_ERR_BUSY`；附录 `0.7.3-rc` 段追加 1 条。**不新开章节、不重复/改写 FID 0–5、不动 `DADAO-12 §4.9`**。
2. **只读锁**：`manifests/spec-readonly.lock.toml` 的 `DADAO-22` `sha256` 同笔重算 + 1 行注释（`check-spec-readonly` 否则必红）。
3. **契约投影**：`.tao/contracts/contract-see.md` §5 错误码表 + §2 `cfx_pmem` DMA 段各同步。
4. **测试专用 provider + 探针**：`tools/testcases/arch/min_rom_probe_integ047t.py` —— ①`doc` 用例（纯 Python，读 spec/contract 断言表形态）；②`runtime` 用例（探针**自带 ROM** 内嵌一个**测试专用**的 `cfx_pmem` SBI provider，沿 `min_rom_probe_integ042t.py` 的 `bootstrap_rom()` 范式）。
5. **登记**：`tools/testcases/arch/README.md` 一行、`Makefile` 的 `ARCH_CFX_PROBES += integ047t`、`.tao/knowledge/milestones.md` 任务流水一行。

**明确不做（避免范围漂移）**：
- **不**新增 `SBI_PMEM_GET_SRAM`（SRAM 基址/大小固定：`DADAO-12 §4.9` 内部偏移 `0x3ff_0000_0000` + 64 KiB，平台已定义）；**不**新增其他 FID。
- **不**改 `components/qemu/**`（QEMU 语义零改动）、**不**改 `tests/shared/bootrom/step5/**.S|.lds`（step5 smon 主链零改动）、**不**改 `spec/DADAO-12`、`contracts/**`、`tests/inst/**`、`manifests/spec-readonly.lock.toml` 以外任何锁。
- **不**实现生产 provider（无 cfx 固件承载者）、**不**实现 `WAIT` 轮询、**不**定义 DMA 完成中断（`PMEM_DMA`）与 SBI 的交互。
- **不**把探针内嵌的测试 provider 称作实现或交付物（代码注释与 README 必须标明「测试专用，非生产实现」）。

## 接口规范

### 1. `DADAO-22 §9` 追加的三行（紧接现行 FID 5 行，列与现行表一致）

| 6 | SBI_PMEM_DMA_START | rd16 = dir（0 = CFX→PA，1 = PA→CFX）、rd17 = src、rd18 = dst、rd19 = size | rd8 = 错误码 | 启动 SRAM ↔ PA 块搬运。**只检查 DMA 忙**：`dma_status.BUSY=1` ⇒ 返回 `SBI_ERR_BUSY`（-5），不写寄存器；否则把 `rd17`→`cg15.rc0`、`rd18`→`cg15.rc1`、`rd19`→`cg15.rc2`、`(rd16 & 1) << 1 \| START`→`cg15.rc3`，返回 0。地址/长度**不在本层校验**；传输错误由 `dma_status.ERROR`/`ERR_CODE` 唯一判定 |
| 7 | SBI_PMEM_DMA_STATUS | — | rd8 = `cfx_pmem_dma_status` | 返回**原始** `dma_status`（bit0 `BUSY` / bit1 `DONE`(W1C) / bit2 `ERROR`(W1C) / bit3–15 `ERR_CODE`，语义见 SEE §4.9）；本层**不另造错误码**，也**不提供** W1C |
| 8 | SBI_PMEM_DMA_WAIT | — | rd8 = 错误码 | **预留，未实现**：当前无时钟/定时器，固定返回 `SBI_ERR_NOT_SUPPORTED`（-2）；**不得**轮询后返回成功，**不得**伪造超时 |

表下追加一段（**不是新标题**，接在现有「初始化方式与其他 cfx 一致…」段之后）：

> `SBI_PMEM_DMA_*` 只做「忙判定 + 寄存器搬运 + 状态回读」：`START` 返回 0 仅表示**调用完成且当时不忙**（硬件可能在 `START` 时即判定非法并置 `ERROR`/`ERR_CODE`、`BUSY` 保持 0），调用方须读 `STATUS` 判定传输结果；`START` 不清 `DONE`/`ERROR`，`STATUS` 不做 W1C。SRAM 基址与大小固定（`DADAO-12 §4.9`），因此**不提供** `SBI_PMEM_GET_SRAM`。

### 2. `DADAO-22 §1` 错误码表追加一行（列与现行表一致）

| -5 | SBI_ERR_BUSY | 资源忙，可重试 |

**二选一决定（已定）**：新增 `-5`，**不复用** `SBI_ERR_FAILED`(-1)。理由：①`BUSY` 是**瞬时且可重试**，`-1` 是终态失败，复用会让调用方无法区分「稍后重试」与「放弃」，且 `STATUS` 是原始值、并不承诺与 `START` 返回值同源；②纯增量：无既有 FID 依赖 `-5` 为保留，对既有读者零破坏；③与「错误唯一由硬件 `ERR_CODE` 判定」的分层一致——SBI 层只报调用层结果（0/忙），传输错误不投影到 SBI 错误码。**已拒绝方案**：复用 `-1`（省一行 spec，但丢失重试语义，且需在 `STATUS` 之外再造约定）。

### 3. `DADAO-22 §9` 分发示例（`simrisc` 块）追加

在 `func 5` 两行之后、`cfx_pmem_unknown:` 之前：

```simrisc
    set.rd   rd3, 6
    br.eq {rd2, rd3}?, [rb0, cfx_pmem_dma_start]  @@ func 6
    set.rd   rd3, 7
    br.eq {rd2, rd3}?, [rb0, cfx_pmem_dma_status] @@ func 7
    set.rd   rd3, 8
    br.eq {rd2, rd3}?, [rb0, cfx_pmem_dma_wait]   @@ func 8
```

并在 `cfx_pmem_free_page` 处理器之后追加三个处理器（同节代码块内）：

```simrisc
cfx_pmem_dma_start:
    @@ rd16 = dir（0 = CFX→PA，1 = PA→CFX），rd17 = src，rd18 = dst，rd19 = size
    @@ BUSY=1 ⇒ rd8 = -5（SBI_ERR_BUSY），不写寄存器
    @@ 否则写 cg15 rc0..rc3（START=1，DIR = rd16 & 1），rd8 = 0
    escape cfx_pmem, [excp_cause_ip, 4]

cfx_pmem_dma_status:
    @@ rd8 = cfx_pmem_dma_status（原始值：BUSY/DONE/ERROR/ERR_CODE）
    escape cfx_pmem, [excp_cause_ip, 4]

cfx_pmem_dma_wait:
    @@ 预留：无时钟/定时器，不实现轮询与超时 ⇒ SBI_ERR_NOT_SUPPORTED(-2)
    set.rd   rd8, -2
    escape cfx_pmem, [excp_cause_ip, 4]
```

### 4. 附录 bullet（`## 附录：版本与变更记录` 的 `### 0.7.3-rc（未发布）` 段，1 条）

内容要点（**不得**出现任务号 / ADR / ISS 编号）：`cfx_pmem` 增加 DMA 的 SBI 封装（启动/状态查询，等待为预留返回不支持）；SBI 错误码增加「忙，可重试」；不提供 SRAM 查询。

### 5. 契约投影（`.tao/contracts/contract-see.md`）

- §5 错误码句末追加 `−5 = SBI_ERR_BUSY`（"资源忙，可重试"），来源标 `[DADAO-22 §1. 调用约定]`。
- §2 `cfx_pmem` DMA 两条 bullet 之后追加一条：SBI 层封装 = FID 6 `START` / 7 `STATUS` / 8 `WAIT`（预留，返回 `SBI_ERR_NOT_SUPPORTED`）；SBI 层只做忙判定与寄存器搬运、不校验地址/长度、不另造错误码（错误只看 `ERR_CODE`），`START` 返回 0 时仍须读 `STATUS`；来源标 `[DADAO-22 §9. 物理存储器管理（cfx_pmem）]`。

### 6. 探针（`min_rom_probe_integ047t.py`）

- 复用 `min_rom_probe_integ042t.py` 的编码器/`run()`/`observe()`/`bootstrap_rom()` 范式（import 或就地复制，二选一并说明；**不得**改 042t 文件）。body 跑在 **hmon（cfx3）** 下，故 `trap cfx_pmem` 的来源 mask 位（bit3）默认为 0，无需抢改 `cg0/cg3` 掩码。
- 测试 provider 放在 **ROM 的 handler 区**（`high6 == 63` 恒等映射，`cfx=17` 下仍可取指；已实测），向量写 `cfx_pmem` 的 **hypv 行**（`cg3 rc8 = 3`、`cg3 rc10 = handler`）。
  注意：`escape cfx_pmem, [excp_cause_ip, 4]` 的**编码字段是 1**（`ret = cause_ip + imms18*4`，与 `044t/045t` 探针一致）。
- 命令行沿用现有探针约定（`--qemu`/`--only`/`--list`），**另加 `--doc`**：只跑 ①doc 用例（不起 QEMU）；不带 `--doc` 时默认 = doc + runtime 全跑，`--list` 一并列出两类用例。
- `doc` 用例（无需 QEMU）：断言 §9 表 `immu18` 集恰为 `{0..8}`、无重复、0–5 名称与出参不变、6/7/8 名称符合 §1、`§1` 错误码含 `-5 SBI_ERR_BUSY` 且 `-1..-4` 未变、spec §9 **无该 FID 表行/无处理器**（允许唯一「不提供」否定句）、`contract-see.md` 不含该串、`contract-see.md §5` 含 `SBI_ERR_BUSY`。

## 修改文件范围（已按现状核对存在性）

- `spec/DADAO-22-SBI-主管系统二进制接口.md`（§1 错误码 1 行、§9 表 3 行 + 1 段 + 示例 3 分支/3 处理器、附录 1 条）。
- `manifests/spec-readonly.lock.toml`（`DADAO-22` 条目：sha256 重算 + 1 行注释）。
- `.tao/contracts/contract-see.md`（§5 一句、§2 一条）。
- `tools/testcases/arch/min_rom_probe_integ047t.py`（新文件）。
- `tools/testcases/arch/README.md`（表中 1 行）。
- `Makefile`（`ARCH_CFX_PROBES` 加 `integ047t`）。
- `.tao/knowledge/milestones.md`（任务流水 1 行）。
- **不动**：`components/**`、`tests/shared/bootrom/**`、`spec/DADAO-12*`、`spec` 其余册、`contracts/**`、`tests/inst/**`、`docs/**`。

## 验收

1. **doc 用例**：`python3 tools/testcases/arch/min_rom_probe_integ047t.py --doc` 全 PASS（离线、不起 QEMU）；逐条打印实测集合/名称，FID 集恰 `{0..8}`。
2. **runtime 用例**（测试专用 provider；每例自证可达 FAIL）：
   - `start_cfx_to_pa`：`dir=0`，SRAM 写 `MAGIC` → SBI `START` 返回 0 → 轮询 `STATUS` 至 `BUSY=0` → `STATUS == DONE`（bit1，非 0/不含 ERROR）→ PA 内容 == `MAGIC`。
   - `start_pa_to_cfx`：`dir=1`，PA 写 `MAGIC2` → `START` → `STATUS == DONE` → SRAM 内容 == `MAGIC2`。
   - `status_raw_equals_cg15`：同一时刻 `STATUS` 返回值与直接 `cfx2rd cfx_pmem, cg15 rc4` **逐位相等**（证明本层不加工）。
   - `no_sbi_side_validation`：`size=0` ⇒ `START` 返回 **0**（SBI 不校验）且 `STATUS = ERROR \| SIZE`(bit3)；`src` 取 SRAM 之外 ⇒ 同理 `ERROR \| CFX_RANGE`(bit4)。证明「错误唯一由硬件 `ERR_CODE` 判定」。
   - `wait_not_supported`：FID 8 ⇒ `rd8 == -2`（且**不**轮询、不返回成功）。
   - `start_busy_returns_busy`：连续两次 `START`（第二次紧接第一次）⇒ 第一次 0、第二次 `-5`。**风险处置见 §BLOCKED**：默认虚拟时钟下 1 ms 窗口可能被 `-d cpu` 转储耗时吃掉（**预检实测：默认时钟下不可观测**）⇒ 实现时先试 `-icount shift=N`（N 现场调，使 1 ms ≫ 若干条指令）；若仍不稳定 ⇒ 该例标 **BLOCKED** 并给替代证据，**禁止**改成恒真断言或伪造。
3. `make check` **rc=0**（含 `check-spec-readonly` 新 sha256、`check-spec-changelog` 附录形态与互锁组、`check-contracts-dir`、`check-knowledge-refs`、`check-milestones-fresh`）。
4. `make check-modules` **rc=0**；`make check-arch` **rc=0**（`integ047t` 全 PASS + 既有 `044t/045t/049t/integ039t/integ040t/integ042t/integ044t/integ046t` 全 PASS，证明零回退）。
5. 证据 `.work/evidence/<任务号>/{run.sh,check.py}`：默认全绿；`--inject` ≥2 处（建议：doc 用例期望 FID 集、runtime 期望 `DONE` 位）→ FAIL → `cp` 备份 + `md5sum` 还原 → 回绿，输出 `EVIDENCE INJECT: PASS`。
6. 探针内 provider 与 README 明标「测试专用，非生产实现」；`git diff` 证明 `components/**` 与 `tests/shared/bootrom/**` 零改动。
7. 完成区 ≤30 行、审阅记录每轮 ≤40 行；`**状态**` 置 `待验收`；临时目录 `/tmp/opencode/INTEG-047t/`。

**BLOCKED（如实登记，不得硬造）**
- **`START` 忙分支的可执行验证**：`START` 后 1 ms 虚拟时钟窗口在两次 `trap` 之间（中间有 `-d cpu` 转储）可能已过期 —— 预检原型实测默认时钟下**不可观测**。处置：先试 `-icount`；仍不可稳定观测 ⇒ 该例 BLOCKED，替代证据 = `INTEG-042t` 的 `dma_busy_visible` 硬件级实测 + provider 忙分支代码审查 + `--inject` 静态演示该分支可达。任务书要求在完成区写明**取哪条路径**。
- **生产 provider**：无 cfx 固件承载者（`smon` 不做功能分发，`INTEG-046t` 明确排除）⇒ 本任务只出契约 + 测试专用 provider；生产实现另立任务。
- **`DONE`/`ERROR` 的清除**：SBI 层不提供 W1C（dispatch 只授权 6/7/8，未授权清除 FID）⇒ 仅 SBI 权限的调用方无法清粘滞位；登记为遗留（下一版可加 `CLEAR` 或 `STATUS` 写语义）。
- **doc 断言的门控层级**：doc 断言随探针在 **L3**（`check-arch`），L1 无 SBI 表守卫；若需 L1 守卫，另立任务把它提为 `tools/spec/` 检查器。

## 参考对照（`DADAO-0628` 只读检索；**内容溯源，非执行必需**，不作执行依赖、不复制代码）

- **0628 做法**：无 `cfx_pmem`、无 SRAM↔PA 块搬运，`SBI_` 面只有 `cfx_timer` 的 `SBI_TIMER_SET_TIMER`/`GET_TIME`（`code-agent/tasks/KL-133a-cfx-timer.md` §3，`contracts/isa/spec.md` 第 1238 行附近）；其「按 `immu18` 分发的函数表」结构可作**分发范式**对照。
- **本项目差异**：v5 已有硬件级 DMA（`DADAO-12 §4.9`）+ 既有 FID 0–5；本任务补的是**SBI 层薄封装**与「忙/错误分层」口径，且 `WAIT` 因**无时钟**只能预留。
- **建议落点**：`DADAO-22 §9` 为唯一真源，0628 仅证明「SBI 用函数表按 `immu18` 分发」可行，不参与本项目语义设计。

## 约束

- 只做本任务；**不提交、不 push**（提交权归 architect）；不跑长构建/夜跑；重建前先申报预计耗时（本任务**不需要**重建 QEMU）。
- **`spec/` 改动限于 `DADAO-22` 一册**（§2 授权流程：授权原话见下节）；`DADAO-12`、`Machine-01` 一字不改。改完**同一变更**内更新 `manifests/spec-readonly.lock.toml` 的对应 `sha256`。
- **`components/**` 与 `tests/shared/bootrom/**` 零改动**；`-bios` 语义与既有探针不得回退。
- 反例/失败注入的还原一律 `cp` + `md5sum`（禁 `git checkout/restore/stash`）。
- 失败保留现场并继续推进（自行处置 / 有据重试并记次数）；**仅在需用户语义裁定**时留问。

## 用户授权原话

**主会话派单原话（原样落纸；`spec/` 授权依据）**：

> 在 /mnt/tao/DADAO-v5，master 已含 INTEG-046t，工作树干净。创建 `INTEG-047t` 任务书：cfx_pmem DMA 的 SBI 契约与最小验证（文件名放 `.tao/tasks/integ/`，先确认 047 未占用；若占用顺延）。
>
> 已确认的接口决策（按此落纸，不要改）：
> - 在 §9 现有表后追加：
>   - `immu18 = 6` `SBI_PMEM_DMA_START`
>   - `immu18 = 7` `SBI_PMEM_DMA_STATUS`
>   - `immu18 = 8` `SBI_PMEM_DMA_WAIT`：**预留，不实现**（当前无时钟/定时器）
> - 不新增 `SBI_PMEM_GET_SRAM`（SRAM 基址/大小固定，已由平台定义）
> - `START` 参数：`rd16=dir`（0=CFX→PA，1=PA→CFX）、`rd17=src`、`rd18=dst`、`rd19=size`、`rd8=返回`；地址/偏移是整数，不用 `rb`
> - `START` 不在 SBI 层重复校验地址/长度；只检查 DMA 忙；忙返回 `SBI_ERR_BUSY`（如现有错误表无此项，任务书决定是新增 `-5` 还是复用 `SBI_ERR_FAILED`，必须二选一并说明；不要编造已确认）
> - `STATUS` 返回原始 `dma_status`（含 BUSY/DONE/ERROR/ERR_CODE），不在 SBI 层另造错误码
> - `WAIT` 预留：调用应返回 `SBI_ERR_NOT_SUPPORTED`（或明确未实现），不得伪造超时
> - 硬件 cg15 布局/语义完全沿用 `DADAO-12 §4.9`，不改

> **说明**：上述派单原话中的「按此落纸」「在 §9 现有表后追加」即 `spec/DADAO-22` 的**事先授权**（`docs/Process-06 §2`）；本任务书的 §接口规范 1–3 是该授权的逐字落纸，未新增其他 spec 语义。**二选一已按 §接口规范 2 定为新增 `-5`（附理由与已拒绝方案）**。

## 下发前预检（5 项）

1. **任务书内部一致**：PASS —— §接口规范 1（3 行 + 1 段）/2（`-5`）/3（示例 3 分支 + 3 处理器）/4（附录）/5（契约）与「目标」「验收 1/2/3」逐项对应；`START` 返回 0 的「可能已被硬件判非法」口径与验收 `no_sbi_side_validation` 对应；`WAIT` 预留口径与 `wait_not_supported` 对应。
2. **验证手段前置实际可用**（本轮实测）：
   - `make check` **rc=0**（48 s，`/tmp/opencode/INTEG-047t/L1-baseline.log`）——`check-spec-readonly`/`check-spec-changelog`/`check-contracts-dir` 基线绿。
   - `min_rom_probe_integ042t.py --only dma_cfx_to_pa` **PASS**、`--only pmem_dma_irq_delivered` **PASS**（`.work/build/qemu` 与安装根 md5 同为 `72d6c653…`）——探针框架、`bootstrap_rom()`、cg15 写入与 BUSY 观测链**可用**。
   - **原型实测（`/tmp/opencode/INTEG-047t/proto{,3}.py`）**：`trap cfx_pmem, 6` → `cfx_pmem` hypv 向量（`cg3 rc8/rc10`）→ ROM 内 handler 取指（`high6==63`）→ `rd16..rd19` 可见 → `escape(…,1)` 返回，`rc=0` 且观测值逐条相符；provider 内写 cg15 后 PA 内容 == `MAGIC`（SBI `START` 端到端生效）。
   - **前置缺口**：`START` 忙分支跨 trap 的时序窗口（见 §BLOCKED，已给处置与替代证据）。
3. **验收逐条可跑性**：验收 1（doc，离线）**现在可跑**；验收 2 的 `start_*`/`status_raw_equals_cg15`/`no_sbi_side_validation`/`wait_not_supported` **现在可跑**（原型已证同一路径）；`start_busy_returns_busy` **条件可跑**（`-icount` 待调，失败则 BLOCKED + 替代证据）；验收 3/4/5 **现在可跑**（L1 基线 48 s，`check-arch` 既有 8 探针绿）。
4. **与 `contracts/`、`tests/inst/` 一致**：PASS —— 全套只用既有指令（`trap`/`escape`/`cfx2rd`/`cfx2rc`/`ld.o`/`st.o`/`set.zw`/`or.w`/`and.o`/`br.ne`/`jump`），`contracts/opcodes.yaml` 现行条目；不新增指令/编码；`tests/inst/**` 不改；`contracts/` 机器可读目录不改（无 SBI 机器表，`grep SBI_ERR` 实测仅 `contract-see.md` 命中）。
5. **拟改文件 × `spec/` 清单**：**命中 1 册** = `spec/DADAO-22-SBI-主管系统二进制接口.md`；授权 = 上节派单原话（逐字落纸，含「在 §9 现有表后追加」三行 FID 与「按此落纸」）⇒ 不构成 BLOCKED；同笔更新 `manifests/spec-readonly.lock.toml` 的 sha256（`docs/Process-06 §5`）。其余拟改文件（lock/contract/tools/README/Makefile/milestones）**不命中** `spec/`。**若主会话判定该授权不足以改 `spec/`**：本任务的 spec/锁 两项转 BLOCKED，仅落 contract 投影 + 探针（探针 doc 用例随之改判），须在完成区写明。

## 完成区

**测试结果**：doc 17/17 PASS；runtime 6/6 PASS（`start_busy_returns_busy` 连续 5/5 稳定，未走 BLOCKED）；evidence 默认与 `--inject` 均 rc=0（3 处注入→FAIL→cp+md5 还原→回绿，`EVIDENCE INJECT: PASS`）。
**修改文件**：`spec/DADAO-22-SBI-主管系统二进制接口.md`、`manifests/spec-readonly.lock.toml`、`.tao/contracts/contract-see.md`、`tools/testcases/arch/min_rom_probe_integ047t.py`（新）、`tools/testcases/arch/README.md`、`Makefile`、`.tao/knowledge/milestones.md`、本任务书（状态+完成区）。
**验收结果**：`make check` rc=0（48.5s，`.work/log/integ/INTEG-047t-check.log`）；`make check-modules` rc=0（3m47s）；`make check-arch` rc=0（终版复跑 41s，`044t/045t/049t/integ039t/integ040t/integ042t/integ044t/integ046t/integ047t` 全 PASS，日志 `.work/log/integ/INTEG-047t-check-arch-final.log`）；证据日志 `.work/log/integ/INTEG-047t-evidence-inject.log`。`git diff --name-only` 无 `components/**`、`tests/shared/bootrom/**`、`spec/DADAO-12`。
**新发现/坑**：① 本 ISA/QEMU 的 `br.*` 目标 = 当前指令地址 + `imms12<<2`（`rb0` 为当前 IP；与 helper 注释里的 `pc_next` 字面不符），探针汇编器按此实现，已用 6 例实测校准；② `-icount shift=0` 下本 QEMU 的 `-d cpu` 寄存器转储全 0，故 busy 例改由**自检 + semihosting 退出码**报告（1 ns/指令，1 ms 忙窗口 ≈ 1e6 指令，稳定）；③ `BOOTSTRAP_OFF=0x48` 使 handler 实际地址 = 构建偏移 + 0x48，向量已显式加该偏移（不再依赖 `swym` 滑行）；④ `GET_SRAM` doc 断言按「未定义」实现（0 表行/0 处理器，唯一字面出现在「不提供」句中）——任务书「§9 不含该串」与 §接口规范 1 的否定句字面冲突，此处取语义一致口径。
**遗留问题**：SBI 层不提供 `DONE`/`ERROR` W1C（仅 SBI 权限调用方无法清粘滞位，按任务书登记）；生产 provider 未实现（无 cfx_pmem 固件承载者，另立任务）；doc 断言仅在 L3（`check-arch`），L1 无 SBI 表守卫；`SBI_PMEM_GET_SRAM` 字面口径见上。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 分支偏移约定初版取 `idx+1`，5 例全红（handler 落到 unknown） | ✅已修 | `Asm.resolve` 改为 `labels - idx`（当前 IP 相对），并以受控实验校准 | 6/6 runtime PASS；`check-arch` 9 探针全绿 |
| busy 例原设计轮询到完成，`-icount` 下需 ~1e6 指令而 40 s 超时 | ✅已修 | busy 例只校验「首次 0 / 紧接 -5」，完成性由 `start_cfx_to_pa` 覆盖；并补 `icount_shift=0`（初版漏传） | `--only start_busy_returns_busy` 5/5 PASS；注入去忙检查 ⇒ exit 0xE2 FAIL |
| handler 向量依赖 `swym` 滑行到 `0x848`（0042t 旧范式） | ✅已修 | `setup_provider` 显式用 `PMEM_HANDLER + BOOTSTRAP_OFF` | 6/6 runtime PASS；PC 轨迹直接落在 handler |
| doc「§9 不含 `SBI_PMEM_GET_SRAM`」与必写的否定句冲突 | ✅已修（语义口径） | 断言改为「无表行/无处理器，唯一字面出现在‘不提供’行」 | `--doc` 17/17 PASS（`rows=0 handlers=0 mentions=1`） |
| 证据脚本注入曾用 `sed` 未命中（`{}` 元字符） | ✅已修 | `check.py` 用 `str.replace` + 计数必须为 1 | `--inject` 3/3 注入 rc!=0 且 md5 还原一致 |
| 生产 provider / SBI 层 W1C 缺失 | ⏸延后 | 任务书明确排除（无固件承载者；dispatch 未授权 CLEAR FID） | 完成区遗留问题已登记 |

#### 第 1 轮 architect 提交（文件集审核）

档位：`待验收`（reviewer 未验收）——按主会话派单原话用 `feat(integ): INTEG-047t cfx_pmem DMA SBI 契约与最小验证` 提交（非 `WIP:`；偏差在本轮声明，未 push）。提交号见下轮 reviewer 前 `git log`。

文件集对账（8 项，全部显式 staging，未用 `git add -A`），与完成区「修改文件」逐项一致：
- `spec/DADAO-22-SBI-主管系统二进制接口.md`：实测 sha256 `7541b6e4…8f5ac` = 锁条目值；diff 仅 §1 加 `-5 SBI_ERR_BUSY`、§9 加 FID 6/7/8 三行 + 1 段说明 + 示例 3 分支/3 处理器、附录 `0.7.3-rc` 1 条；FID 0–5 行逐字未变（`git diff` 无对应 `-` 行）；`SBI_PMEM_GET_SRAM` 全册仅 1 处字面（「不提供」否定句），**无新增表行/处理器**。
- `manifests/spec-readonly.lock.toml`：仅 `DADAO-22` 条目 1 行注释 + sha256，其余 `[[spec]]` 未变。
- `.tao/contracts/contract-see.md`：§5 错误码句尾追加 `−5`、§2 追加 1 条 SBI 封装 bullet（2 处）。
- `tools/testcases/arch/min_rom_probe_integ047t.py`（新，766 行，文件头明标「test-only，非生产实现」）；`tools/testcases/arch/README.md`（1 行 + `--qemu` 名单）；`Makefile`（`ARCH_CFX_PROBES` 加 `integ047t`）；`.tao/knowledge/milestones.md`（流水 1 行 `待开始`→`待验收`）；本任务书（状态 + 完成区 + 自审记录）。
- **零改动核验**：`git status -uall` 无 `components/**`、`tests/shared/bootrom/**`、`spec/DADAO-12*`、`contracts/**`、`tests/inst/**`、`docs/**`；其它锁文件未变。
- 临时残留：无（`*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`*.bak` 均 0；证据在 `.work/` 且被 ignore）；`git diff --check` rc=0。
- architect 独立复核（不采信叙述，未跑长构建）：`python3 tools/testcases/arch/min_rom_probe_integ047t.py --doc` **rc=0**，17/17 PASS，实测 FID 集 `[0..8]`、`-1..-4` 未变、`-5 SBI_ERR_BUSY`、`no_get_sram_defined_in_spec9 rows=0 handlers=0 mentions=1`。
- 漏提/多提/越界：无。

#### 第 1 轮 reviewer 验收

**重跑记录（reviewer 亲自执行，非采信叙述）**：分支 `INTEG-047t`、HEAD `8d1be3e4`、`git status -uall` 干净；`git diff master...HEAD --stat` 8 文件与完成区逐项一致（contract-see/milestones/任务书/Makefile/lock/DADAO-22/README/探针），无越界文件。
- `min_rom_probe_integ047t.py --doc` → **rc=0，17/17 PASS**（FID 集 `[0..8]`、`rows=9`、`GET_SRAM rows=0 handlers=0 mentions=1`、`err_codes` 含 `-5` 且全表等值）。
- runtime 全量 → **rc=0，6/6 PASS**；`make check` → **rc=0（48.32s）**；`make check-arch` → **rc=0（42.29s，9 探针全绿含 integ047t 6/6）**；`make check-modules` → **rc=0（240.32s）**。`check-spec-readonly`/`check-spec-changelog`/`check-contracts-dir`/`check-milestones-fresh`/`check-knowledge-refs`/`check-run-artifacts` 均在日志内 PASS。
- 证据 `run.sh` 默认 rc=0；`run.sh --inject` rc=0、3 处注入全 FAIL（rc=1）且 md5 还原一致、`EVIDENCE INJECT: PASS`。
- **reviewer 独立注入 3 处（非 engineer 注入点）**：①改 spec 表 FID 8 名 → `--doc` rc=1（`fid_8_name FAIL`）；②改 provider STATUS 处理器恒返 0 → `status_raw_equals_cg15` rc=1（`rd6 exp=0xc got=0x0`）；③改忙判断为恒忙 → `start_busy_returns_busy` rc=1（`exit exp=0x0 got=0xe1`）。三处均 `cp` 备份 + md5 相等还原 → 复跑回绿、树净。

**约束核验**：spec 仅 DADAO-22 §1/§9/附录，FID 0–5 行无 `-` 行（未动），`DADAO-12`/其余册/`contracts/**`/`tests/inst/**`/`docs/**` 零改动；`components/**`、`tests/shared/bootrom/**` 零改动；lock sha 实算 `7541b6e4…8f5ac` 一致；`SBI_PMEM_GET_SRAM` 全册仅「不提供」否定句 1 处、无表行/处理器；`-bios` 探针与 042t/044t/046t 零回退（evidence+check-arch 双证）。探针/README 明标「测试专用，非生产实现」。busy 例真跑 `-icount shift=0`（case → run() 传参）、只断言「首次 0/紧接 -5」（半主机退出码 0xE1/0xE2 可达 FAIL，注入③实证），未伪造完成；`wait_not_supported` 真返 -2（rd5=全 1 位模式，且 STATUS=0、目标未动）；`status_raw_equals_cg15` 逐位（注入②实证可达 FAIL）；`no_sbi_side_validation` 两例 START=0 + 硬件 ERR_CODE，期望值独立派生自 DADAO-12 §4.9 bit3/bit4。完成区 5 行 ≤30、审阅记录各轮 ≤40、无临时残留。

**findings（不阻断）**：① 任务书验收 1「§9 不含 `SBI_PMEM_GET_SRAM`」与 §接口规范 1 强制否定句**字面冲突**；engineer 取语义口径（0 表行/0 处理器/唯一字面须含「不提供」）并在完成区披露——口径正确，建议 architect 收尾时修任务书措辞。② reviewer 首跑 `make check` rc=2，根因 = **reviewer 自己**的日志名 `REVIEW-*` 触发 `check-run-artifacts`（3 illegal names 全为我方日志，非交付物缺陷）；删后合规名重跑 rc=0（有据重试 1 次）。③ README 除表 1 行外同步了 `--qemu` 名单行，属一致性补充。

**判决：Accepted** —— 验收 1–7 在 reviewer 独立重跑下全部通过（rc 如上），硬约束无违反，证据脚本无恒真、注入可达 FAIL。可进入 `/complete`。

#### 第 1 轮 architect 交叉复核（`/complete`）
档位：**Accepted ⇒ 正常提交**（`review: INTEG-047t Accepted（reviewer 记录 + architect 交叉复核）`，仅任务书；分支 `INTEG-047t`，**不 merge、不 push**）。

独立复核（不采信叙述；日志 `/tmp/opencode/INTEG-047t/architect/`）：
- **判决校准（未过松）**：reviewer 的 3 处独立注入 + 本方下述 6 项控制实验，逐条命中可达 FAIL。
- **busy 例可执行证据真实**：`@case(..., icount_shift=0)` → `run()` 实传 `-icount shift=0`；`exp` 仅 `{"exit":0}`，只两条断言（首次 0 / 紧接 -5），无轮询完成、无伪造。`--only start_busy_returns_busy` 连跑 **5/5 rc=0**。
- **控制实验**（`/tmp` 脚本 import 探针、仅内存改写内嵌 provider，**仓库文件零改动**）：A 去掉 icount（默认时钟）⇒ FAIL `exit got=0xe2`（证明 `-icount` 承重、断言非恒真）；B 忙判定永不命中 ⇒ `0xe2`（第二断言可达 FAIL）；C STATUS 恒报忙 ⇒ `0xe1`（第一断言可达 FAIL）；D 去掉 cg15 ctrl 写 ⇒ `no_sbi_side_validation` FAIL（rd6/rd8 exp=0xc/0x14 got=0x0）；E FID 8 返 0 ⇒ `wait_not_supported` FAIL（rd5 exp=…fffe got=0x0）；F STATUS 加工 +0x4 ⇒ `status_raw_equals_cg15` FAIL（rd6 exp=0xc got=0x10）。
- **spec 范围**：`git show 8d1be3e4 -- spec/DADAO-22…` 仅 §1 +`-5` 1 行、§9 +3 表行/+1 段/+3 分支/+3 处理器、附录 +1 条；FID 0–5 无 `-` 行；`DADAO-12` 及其余册零改动。
- **锁 sha**：`sha256sum` 实算 `7541b6e4…8f5ac` = `manifests/spec-readonly.lock.toml` 条目值。
- **`GET_SRAM`**：§9 `rows=0 handlers=0 mentions=1`（唯一字面为「不提供」句）；`contract-see.md` 0 次。
- **零改动**：`git show --stat` 8 文件，无 `components/**`、`tests/shared/bootrom/**`。
- **门控复跑**：`make check` rc=0（L1 PASS）、`make check-arch` rc=0（9 探针全 PASS），日志 `architect/check.log`、`architect/check-arch.log`。
- **长度**：完成区 5 行 ≤30；各轮审阅记录 ≤40 行。

finding 处置：reviewer 非阻断 ① 已改任务书 §接口规范 6 doc 断言措辞为「§9 无该 FID 表行/无处理器（允许唯一「不提供」否定句）」——语义不变，消除与 §接口规范 1 强制否定句的字面冲突；②③ 接受 reviewer 说明，无动作。

文件集对账：本次提交仅本任务书（reviewer 记录 + 措辞 1 处 + 本记录），**无多提/漏提/越界**；提交号见本分支 `git log` 首行。

#### 主会话统一收尾

reviewer 与 architect 两份独立复核均为 **Accepted**，无分歧；主会话采信并置任务 `已验证`。本任务只交付 SBI 契约 + 测试专用 provider 探针，不包含生产 provider、`DONE`/`ERROR` W1C、`WAIT` 实现；这些按完成区遗留处理。`spec/DADAO-22` 的改动限于既有 §9 的 FID 6/7/8 顺延与 `-5` 错误码，未改 `DADAO-12` 硬件语义。
