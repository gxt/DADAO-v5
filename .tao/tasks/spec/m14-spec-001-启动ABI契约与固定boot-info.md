# m14-spec-001: 启动 ABI 契约（Vast 内核装载 + 固定 boot info）

**模块**：spec
**项目里程碑**：M14
**依赖**：`m14-linux-001`（批次先行；不共享文件）
**可并行分片**：否（单册单写者；与 `m14-spec-002` **串行**，同改 spec 版本锁与 `.tao/contracts/README.md`）
**预估**：6–7 h
**状态**：已验证

## 背景

M14 K0 要冻结「内核怎么进、进来时看到什么」。当前 `spec/Machine-v5 §6` 只规定测试机 BootROM 装载与 `power → hmon → smon` 移交，**没有** Vast 上内核镜像的装载规则、入口寄存器/运行模式、内存分区与启动参数结构；`DADAO-23 §3` 的 S-mode 入口约定以**设备树**为 `rb17` 的语义。主会话派单转达的 2026-11-13 用户确认前提：**不引入设备树 DTB，启动传参改为固定 boot info 结构**；平台 = QEMU system 模式、单核、semihosting 控制台。

本任务把上述决定落成**可实现的契约**：spec 正文 + 人读合约 + 机器可读投影 + 机械一致性检查。K0 只冻结契约，**不实现** QEMU 侧装载扩展（K1）。

## 目标

1. `spec/Machine-v5` 新增 **§6.3「`Machine-v5-Vast` 内核装载与启动 ABI」**（v5 自定），含：
   - 两条装载路径（ELF / raw loadmem）与校验规则；
   - 内核入口地址、进入时运行模式/PTW/寄存器约定；
   - RAM 分区（低端保留区、内核区、initramfs 区）与大小上限；
   - **固定 boot info 结构**（PA、magic/version/size、逐字段偏移/宽度/端序/语义）；
   - 与 §1.1/§2/§6（首张页表、`power → hmon → smon` 移交）的衔接，与 `DADAO-23 §3` 的关系（本机 `rb17` 承载 boot info，**不是** DTB）。
2. 新建 `.tao/contracts/contract-linux-boot.md`（归一化人读契约，版本 `0.1.0`）。
3. 新建机器可读投影 `contracts/linux-boot.yaml`（`check-contracts-dir` 白名单内的 `*.yaml`）。
4. 新建 `tools/linux/check_boot_contract.py`（`make check-linux-boot-contract`，目标由 `m14-linux-001` 已声明）：正文表 ↔ 契约 ↔ YAML 三方逐字段一致；`--self-test` 每类断言可达 FAIL。
5. 版本与只读锁：`Machine-v5` `0.4.5-rc` → **`0.4.6-rc`**，附录新段；`manifests/spec-readonly.lock.toml` 同笔更新该册 sha256 + 注记（其余 20 册不变）。

## 接口规范（本任务冻结值）

> 下列值原为**架构师提案**，已由用户 **2026-11-13 确认「按提案冻结（推荐）」**（渠道 = 主会话问答）：内核基址/入口 `0x0010_0000`、boot info PA `0x0001_0000`、initramfs 区 `0x0400_0000`、`rb17` 承载 boot info 指针、入口 `supv` + 身份映射。实现/评审若发现与既有契约冲突，**不得自改**，登记「待裁定」返回主会话。

**内存分区（Vast，PA RAM `[0, 2 GiB)`）**

| 区间 | 大小 | 用途 |
|---|---|---|
| `[0x0000_0000, 0x0001_0000)` | 64 KiB | 首张页表页（`PTBR = 0`，`DADAO-12 §2.2`；由 smon 建立） |
| `[0x0001_0000, 0x0002_0000)` | 64 KiB | **boot info 页**（固定 PA `0x0001_0000`；其余字节为 0） |
| `[0x0010_0000, 0x0400_0000)` | 63 MiB | 内核镜像区（`kernel_base = 0x0010_0000`，与既有 Vast raw loader 的 `kernel_base` 一致） |
| `[0x0400_0000, 0x0600_0000)` | 32 MiB | initramfs 区（上限 32 MiB） |
| 其余 | — | 内核页分配器可用；`[0, 0x0002_0000)` 与 initramfs 区在内核接管后须保留 |

**内核装载（两条路径，语义等价）**

- **ELF 路径**：ELF64、大端（`EI_DATA = 2`）、`e_machine = 0x0DA0`、`ET_EXEC`；`e_flags` 按 `contract-elf §1.3`；仅 `PT_LOAD`；每段 `p_vaddr == p_paddr`、`p_vaddr % 0x10000 == 0`、`p_align >= 0x10000`、`[p_vaddr, p_vaddr+p_memsz)` 落在 `[0x0010_0000, 0x0400_0000)`；`p_filesz` 数据 + `p_memsz-p_filesz` 零填充；**禁止**任何段与 `[0, 0x0002_0000)`、BootROM `[0xffff_ffc0_0000, 0xffff_ffff_ffff]`、hmon SRAM `[0x0fff_0000_0000, +64 KiB)` 重叠；`e_entry = 0x0010_0000`。
- **raw（loadmem）路径**：**扁平镜像**，首字节 = 入口指令，整体装入 `0x0010_0000`，长度 ≤ 63 MiB；**不含 `.bss`** ⇒ 内核 `head.S` 必须自行把 `__bss_start..__bss_stop` 清零（ELF 路径由 loader 零填充，两者行为须等价）。
- **initramfs**：`cpio`「newc」格式，装入 `0x0400_0000`，长度 ≤ 32 MiB；`boot info` 记录实际长度。
- **失败语义（host/loader 层，不是 guest fault）**：任一校验失败（非 ELF64/端序/机器号、`e_entry` 不符、段越界/重叠、initramfs 超限、boot info 无法写入）⇒ loader **非零退出**，不得静默降级或截断。

**boot info（固定结构；大端；PA `0x0001_0000`；`size = 0x60`）**

| 偏移 | 宽度 | 字段 | 语义 |
|---|---|---|---|
| `0x00` | 4 | `magic` | `0x4442_494E`（ASCII `DBIN`） |
| `0x04` | 2 | `version` | `1`（内核只接受 1；不匹配须显式失败） |
| `0x06` | 2 | `size` | `0x0060`（总字节数；更大 ⇒ 忽略尾部未知字段） |
| `0x08` | 8 | `ram_base` | `0` |
| `0x10` | 8 | `ram_size` | `0x8000_0000`（2 GiB） |
| `0x18` | 8 | `kernel_base` | `0x0010_0000`（= `e_entry` / raw 首字节地址） |
| `0x20` | 8 | `kernel_size` | 装载镜像字节数：ELF = `max(p_vaddr+p_memsz) - kernel_base`；raw = 文件字节数。内核另用自身 `_end` 保留完整镜像（含 `.bss`） |
| `0x28` | 8 | `initramfs_base` | `0x0400_0000` |
| `0x30` | 8 | `initramfs_size` | 实际字节数（`0` ⇒ 无 initramfs） |
| `0x38` | 8 | `cmdline_base` | `0`（K0 无命令行；保留字段） |
| `0x40` | 8 | `cmdline_size` | `0` |
| `0x48` | 8 | `ptbr` | `0`（首张页表根 PA；低 16 位为 0） |
| `0x50` | 4 | `page_size_log2` | `16`（64 KiB 页） |
| `0x54` | 4 | `hart_id` | `0`（K0 单核） |
| `0x58` | 8 | `flags` | `bit0 = 1`：semihosting 控制台可用；其余位 0，内核须忽略未知位 |

- 所有多字节字段**大端**；8 字节字段自然对齐；`0x60` 之后到页尾为 0。
- **写入方与保护**：boot info 由**宿主 loader** 在移交前写入；`power`/`hmon`/`smon` 只读、不得改写；smon 建立首张页表时不得覆盖 `[0x0001_0000, 0x0002_0000)`。
- `magic`/`version`/`size` 任一不符 ⇒ 内核 `head.S` 必须**显式失败**（semihosting `SYS_EXIT` + 固定失败码，码值留给 K1 实现，不在本契约定），不得猜测或继续。

**进入时状态（内核第一条指令处）**

| 项 | 值 |
|---|---|
| 运行模式 | `supv`（`DADAO-23 §3` 的 smon 移交路径；`power → hmon → smon → 内核`） |
| PTW | 开启；身份映射 `VA [0, 2 GiB) → PA [0, 2 GiB)`（`Machine-v5 §6` 首张页表）；`PTBR = 0`；64 KiB 页 |
| `rb17` | boot info PA `0x0001_0000`（与 `DADAO-23 §3` 的「设备树地址」同位；本机**无 DTB**，内核不得按 DTB 解析） |
| `rb16` | 入口地址 `0x0010_0000`（移交用；移交后不再有意义） |
| `rb1`（SP） | 未定义；`head.S` 必须在任何栈使用前自建 early stack |
| `rb3`（rbtp） | `0`（内核态无 TLS） |
| `rd15` / 其它通用寄存器 | 未定义（不得依赖） |
| 异步中断 | 全部屏蔽（沿用 hmon/smon 初值）；内核按需开启 |
| hart | 仅 `hart_id = 0` 在线（K0 单核；多 hart 不定义） |
| cache / LLC | 不引入、不假设一致性 |

**明确不定义**：TLB 填充/失效/ASID（K3）、cache/LLC、设备树、UART、多核启动、SMP 停核协议。

## 范围（改哪些文件）

- `spec/Machine-v5-测试机运行环境.md`（新增 §6.3；§6 Vast 装载段落加指针；§1.1 Vast 的 PA RAM 行加「内部分区见 §6.3」指针；附录 `0.4.6-rc`；册头版本）
- `.tao/contracts/contract-linux-boot.md`（新建，0.1.0）
- `contracts/linux-boot.yaml`（新建）
- `.tao/contracts/README.md`（文件表加一行）
- `tools/linux/check_boot_contract.py`（新建；含 `--self-test`）
- `manifests/spec-readonly.lock.toml`（仅 `Machine-v5` sha + 注记）
- 本任务书

## 验收标准

1. §6.3 与 §1.1/§2/§6 交叉引用自洽：入口模式 `supv`、PTW 开启、`power → hmon → smon → 内核` 与既有文字不冲突；§6.3 明写「`rb17` 与 `DADAO-23 §3` 同位、本机无 DTB」，且**未**修改 `DADAO-23`（上游只读）。
2. boot info 表 = 上文逐字段一致（偏移/宽度/端序/值/对齐/越界语义/写入方与保护）；全册 grep 无「设备树/DTS/DTB 由本机传入」类表述（历史附录除外，须加注）。
3. 装载规则可机械核：ELF 路径 7 条校验 + raw 路径 4 条（基址/入口/长度/BSS 责任）+ initramfs 区/上限 + 失败即 host 非零退出；每条在正文有唯一断言句。
4. 明确「不定义 TLB/cache/LLC/UART/多核」；K0 只引用 `DADAO-12 §2.2` 既有页表语义。
5. `contract-linux-boot.md`（0.1.0）：每条规范句带来源标注（`[Machine-v5 §6.3]` / `[contract-elf §5.2]` / `[DADAO-23 §3]` / `[用户裁定 2026-11-13]`；无上游依据的冻结值标 `[spec-decision]` 并在文末列出）；与 `contract-elf`/`contract-abi`/`contract-semihosting` 无重复正文（只指针）。
6. `contracts/linux-boot.yaml` 与正文表逐字段相等；`python3 tools/linux/check_boot_contract.py` rc=0（打印现场字段数），`--self-test` 注入四类（偏移错、magic 错、入口/基址错、字段缺失）各自 FAIL；`make check-linux-boot-contract` rc=0（目标由 `m14-linux-001` 声明；L1 登记/接线由 `m14-infra-003`）。
7. 版本/锁：`Machine-v5` 册头与附录 `0.4.6-rc`；`make check-spec-readonly` rc=0 且 21 册逐册重算**仅 1 册**变（其余 20 册 sha 与派单基线一致）；`make check-spec-changelog`/`check-spec-drift`/`check-spec-numbering`/`check-spec-refs`/`check-contracts-dir`/`check-knowledge-refs`/`check-test-reports` 全 rc=0。
8. ADR 提醒：启动 ABI 属跨模块外部契约，命中 ADR 判据；**是否立 ADR 由用户裁定**（本任务不写 `adr-*.md`，在完成区登记提醒）。
9. 一键证据脚本（含注入→FAIL→`cp`+md5 还原→回绿）；完成区 ≤30 行、无运行期路径。

## 说明

- **授权提醒**：本任务改 `spec/Machine-v5`（只读锁内册）。按 `docs/Process-06 §2/§5` 须用户**事先**明确允许、留存原话，并同笔更新锁 sha；派单前由主会话把授权原话落到本任务书「用户授权」段；未落纸 ⇒ BLOCKED。
- **`rb17` 语义的边界**：`DADAO-23 §3` 属上游只读册，本任务只在 `Machine-v5` 写「本机约定」；若评审认为必须改上游册，**不得自改**，登记「待裁定」。
- 参考实现只读：`.cache/refs/DADAO/ENV-linux`（5.4 时代）可对照「镜像装载/入口」的踩坑，但**内容溯源，非执行必需**，不复制代码/地址。
- `Machine-v5 §6.3` 运行期装载实现（QEMU 写 boot info、装 initramfs、把 `rb16/rb17` 交给 smon）属 **K1** 任务，不在本任务范围。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数写现场值。
4. 只动「范围」列出的文件；越界须披露。
5. 失败保留现场并继续推进；只有需要用户语义裁定才写「待裁定」并返回主会话。
6. 用户裁定/授权原话不得编造；引用须可在仓库内回溯；自定事项标「自决」。
7. 命令作用域 = workdir（仓库根），用相对路径。
8. 反例注入一律「注入→FAIL→`cp`+md5 还原→回绿」；**禁** `git checkout/restore/stash` 还原。
9. 复杂命令输出留存运行期日志目录（`docs/Process-08`）。
10. 证据脚本的对照基线**钉派单前 commit 常量**，不得取 `HEAD`（WIP 提交会前移 HEAD 使比对恒真）。

## 用户授权

**用户授权（2026-11-13，渠道 = 主会话问答；选项「授权这三处（推荐）」）**：用户同意本批任务修改 `spec/Machine-v5`（含只读锁）、`docs/Process-01`、`docs/Process-07` 三处；本任务按授权执行，其余 `spec/` 与 `docs/Process-*` 改动仍需逐次授权。

本任务范围：`spec/Machine-v5` 新增 §6.3 + 版本与只读锁同笔更新。

## 待裁定

**用户裁定（2026-11-13，渠道 = 主会话问答；原话：裁定 A「VA 为 ABI 地址」、裁定 B「M1 预建页表 + VA 入口」）**：
- **A 地址术语**：ABI 里的地址一律是 VA（48 位核内地址、`addr[47:42]=0` 的内存窗口 ⇒ `VA=addr[41:0]`，42 位）；PA 只出现在页表项、`PTBR = PPN<<16`、宿主 loader 写内存的那一刻；入口地址、`rb17` 指向的 boot info、`kernel_base`、initramfs 区、栈指针全部按 VA；`p_vaddr == p_paddr` 改为「ELF/raw 地址是 VA、loader 写到该 VA 映射到的 PA，K0 身份映射下数值相等但术语分开」。
- **B 启动模型 M1**：loader/固件**预建身份映射页表**（64 KiB 页、`VA[0,2 GiB) → PA[0,2 GiB)`、`PTBR` 指向该表、`ptw_enable=1`），随后进入内核 VA 入口（`rb16`）；须写明 `ptw_enable=0` 时访存/取指直接 `CFXMEM`（内核不可能 MMU 关运行）；写明其它 hart 在 K0 状态未定义，以及低端保留区与 initramfs 区不得回收。
- **处置**：已按两项裁定返工 §6.3 / 契约 / YAML / 检查器 / 证据脚本（见「第 2 轮 engineer 自审」）；冻结数值（内核 `0x0010_0000`、boot info `0x0001_0000`、initramfs `0x0400_0000`、`rb17`、`supv` + 身份映射）不变。

**仍待裁定（reviewer 第 1 轮非阻断建议）**：契约版本线 `0.1.0` 与 README `Machine` 列 `0.4.0` 的对齐口径（当前按 ADR-sourced 分类通过 `check-spec-drift`），以及是否为本启动 ABI 立 ADR。

## 完成区

**测试结果**（返工后全量重跑）：`python3 tools/linux/check_boot_contract.py` **rc=0**（boot info 15 字段 ×〔正文/契约〕+ 语义列 15 + 每字段 kind 地址术语断言、分区 5 行、进入状态 10 项、规则 16 条＝elf:7/raw:4/initramfs:3/fail:2、术语/启动模型断言，条数全现场统计）；`--self-test` **rc=0**（**6 类**注入：偏移 / magic / 入口基址 / 字段缺失 / 术语缺失 / boot info 改称 PA，各「注入⇒FAIL⇒还原⇒回绿」）；运行期证据脚本（`.work/evidence/**`）**rc=0**（`PASS=53 FAIL=0`，3 路真实文件注入 + `cp`+md5 还原、锁 21 册仅 1 册变、H 段术语/启动模型逐项）。

**修改文件**（= `git status --porcelain -uall`）：
- `M spec/Machine-v5-测试机运行环境.md`（§6.3 按**裁定 A/B**重写：地址术语 VA / 启动模型 M1 预建页表 + VA 入口 / `ptw_enable=0 ⇒ CFXMEM` 硬约束 / 其它 hart 未定义；§1.1 与 §6 各 1 条指针；册头与附录 `0.4.6-rc`）
- `A .tao/contracts/contract-linux-boot.md`（新建；`0.1.0`；同步 VA 术语与 M1）
- `A contracts/linux-boot.yaml`（新建；增 `address_model` / `startup_model` / 每字段 `kind`、`pa`→`va`）
- `A tools/linux/check_boot_contract.py`（新建；增术语/启动模型断言、kind 地址断言、6 类 self-test）
- `M .tao/contracts/README.md`（文件表 + 投影清单各 1 行）
- `M manifests/spec-readonly.lock.toml`（仅 Machine-v5 sha + 注记；其余 20 册 sha 与基线逐册相同）
- `M` 本任务书（裁定留纸 / 完成区 / 第 2 轮自审 / 状态）

**验收结果**：①**裁定 A** — ABI 地址一律 VA（`addr[41:0]`），PA 仅剩页表项/`PTBR`/loader 写内存（检查器按 `kind` 逐字段断言 va 字段写 VA、`ptbr` 写 PA，并断言旧口径 `p_vaddr == p_paddr`、`固定 PA \`0x0001_0000\`` 已消失）②**裁定 B** — §6.3 明写预建身份映射页表 + `ptw_enable = 1` + `rb16` VA 入口，并写明 `ptw_enable = 0` 取指/访存即 `CFXMEM`（引 `§1.2`）、M1 无 MMU 关中间态；其它 hart 状态未定义；低端保留区与 initramfs 区不得回收③boot info 15 字段逐字段一致（偏移/宽度/字段/值/语义）④规则 16 条各有唯一断言句⑤不定义项逐项点名⑥`check-spec-readonly`/`changelog`/`drift`/`numbering`/`refs`/`contracts-dir`/`contracts-pending`/`test-reports`/`dirs`/`no-residue`/`purity`/`cite-targets` 全 rc=0⑦证据脚本见「测试结果」⑧reviewer 非阻断 finding：§6.3.3 页末措辞已改（「页内偏移 `0x60` 之后至该页末」）；`contracts/README.md` 未改（超范围，登记遗留）。

**新发现/坑**：
- **`check-spec-drift` 对 spec-sourced 契约强制「契约版本 == README 已发布版本」**：本契约 `0.1.0` ≠ README `Machine` 列 `0.4.0`，故按 ADR-sourced 分类（引 `adr-0004-test-machine.md`，Accepted；装载模型确为其 `§D2.2`/`§D2.3` 的延伸），版本行写 `> **契约版本**：0.1.0`（reviewer 第 1 轮已确认成立；版本线对齐口径仍列待裁定）。
- **门控前缀**：`check-spec-refs` 只识别 `Machine-\d+`；`[Machine-v5 §6.3]` **不被校验**（不是判红——reviewer 订正），故契约统一写 `[Machine-01 §6.3]`（契约头注明 = `Machine-v5` 册），spec 册内引用按册内惯例写 `§N.M`。
- `check-knowledge-refs` **既有红**（rc=1，5 处具体 `.work/**` 引用全在 `m13-testcases-013` 任务书）：该文件相对基线 `8cd4c184` 未改 ⇒ 非本任务引入（证据脚本 F 段断言归属）。
- `make check-linux-boot-contract` **BLOCKED**：Makefile 目标声明归 `m14-linux-001`（主会话边界裁定「本任务不改 Makefile」）；本任务以直接调用脚本取证。
- 既有 `tests/shared/machine-profiles.yaml` 的 vast profile（`kernel_base`/`entry`/`ram_base`/`ram_size`）与 boot info 冻结值数值一致（仅佐证，不作 oracle）。

**遗留问题**：
- BLOCKED：`make check-linux-boot-contract` 目标接线待 `m14-linux-001`（脚本已就绪，接线即一行）。
- `contracts/README.md` 不在任务书范围，未改（建议合入时补 `linux-boot.yaml` 一行，保持两处 README 对称）。
- 待裁定：契约版本线（`0.1.0` vs README `Machine` `0.4.0`）与「是否为本启动 ABI 立 ADR」；本任务未写 `adr-*.md`。

## 审阅记录

### 第 1 轮 engineer 自审

改动 6 个文件（spec §6.3 / 契约 / YAML / 检查器 / 契约 README / 只读锁）；逐行审查后逐条处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 行数断言把 int 与 `15/15` 串比较，恒 FAIL | ✅已修 | 拆成「正文==YAML」「契约==YAML」两条 | 检查器 rc=0，行数现场打印 |
| F2 `其余` 行的区间列被按 PA 格式化 | ✅已修 | null-start 行区间 = `其余` | 内存分区 5 行双向 PASS |
| F3 `FAIL-KERNEL` 在契约出现 2 次，唯一性断言红 | ✅已修 | 正文改述、不带 id | 规则 id 唯一性全 PASS |
| F4 契约头 `[DADAO-23 §3 …]` 占位被 `check-spec-refs` 当真实引用 | ✅已修 | 改为可解析完整节名 | `check-spec-refs` rc=0（1136 引用，失败 0） |
| F5 §6.3 文字微调后锁 sha 过期 | ✅已修 | 重算并同步 sha（`6dadcbb…`） | `check-spec-readonly` rc=0；相对基线仅 1 册变 |
| F6 证据脚本用字符串比较判「rc!=0」⇒ 恒 FAIL | ✅已修 | 改数值判定；`[PASS]` 前缀匹配顺序修正 | `run.sh` rc=0（PASS=27 FAIL=0） |
| F7 证据脚本把字段/行数期望写死 30/10/20 | ✅已修 | 改为「2 × 正文行数」现场派生 | 断言全 PASS |
| F8 §6.3.1 写「三段固定分区」但表列四段 | ✅已修 | 正文与附录统一为四段 | 检查器 5 行 PASS + 人工核对 |
| F9 §6 原句与 §6.3 内核布局定义存在文字张力 | ✅已修 | 限定为「测试镜像」并加 §6.3 指针 | 验收 1 自查 |
| F10 `self_test` 用 `Path.cwd()` 定位源文件 | ✅已修 | 改用脚本 `ROOT` | self-test rc=0 |

**判决**：无未修 finding；任务置 `待验收`。

### 第 1 轮 reviewer 验收

**判决：Accepted**（下列输出全部为本人在本任务 worktree 独立重跑所得；最终接受归 architect 终审）

**重跑记录（命令 | 退出码 | 关键输出）**
- `python3 tools/linux/check_boot_contract.py` | **rc=0** | `[PASS]` 162 项 / `[FAIL]` 0；现场统计 `§6.3 行数=106`、`规则=elf:7,fail:2,initramfs:3,raw:4`、`DTB 提及=3`
- `python3 tools/linux/check_boot_contract.py --self-test` | **rc=0** | 4 类注入（偏移/magic/入口基址/字段缺失）各自 `注入后 rc=1` → `还原后 rc=0`，`4 类注入，失败 0 项`
- 证据脚本（`.work/evidence/**` 下 run.sh）| **rc=0** | `汇总: PASS=27 FAIL=0`（含 2 路真实文件注入 + `cp`+md5 还原、锁 21 册仅 1 册变）
- 证据脚本 D 段 7 门控（numbering/changelog/refs/drift/contracts-dir/contracts-pending/readonly）**全 rc=0**；本人另直接重跑 `check-spec-refs`（`失败: 0`）、`check-spec-readonly`（`21 read-only spec volume(s) OK`）、`make check-test-reports`/`check-dirs`/`check-no-residue`/`check-spec-purity`/`check-spec-cite-targets` **均 rc=0**
- `python3 tools/infra/check_knowledge_refs.py` | **rc=1** | 5 处全在 `m13-testcases-013` 任务书；该文件与检查器相对基线 `8cd4c184` 的 `git diff` 为空 ⇒ 基线既有红（验收7 该项 BLOCKED，完成区已披露）
- `grep -n check-linux-boot-contract Makefile` | **rc=1**（目标缺席）⇒ `make check-linux-boot-contract` BLOCKED，归 `m14-linux-001` 接线，已披露
- `make check` | **rc=2** | 卡在 `check-patch-tree: chipyard …WumingFP.scala` 补丁与工作树不符；本任务基线以来 diff 仅 7 文件、未触碰 `components/`，该门输入（补丁集 + 组件工作树）与本任务无关 ⇒ 既有/环境红，非本任务引入

**独立核对（不采信检查器）**：spec §6.3 ↔ 契约三表 `diff` 逐字节一致（boot info 17 行 / 分区 7 行 / 状态 12 行）；spec ↔ YAML 15/15 字段偏移·宽度·名·值独立解析全等，抽核 5 字段 = `magic 0x4442_494E@0x00/4`、`ram_size 0x8000_0000@0x10/8`、`kernel_base 0x0010_0000@0x18/8`、`page_size_log2 16@0x50/4`、`flags 0x1@0x58/8`；布局自算 `max(offset+width)=0x60=size`、自然对齐、无重叠、PA `0x1_0000` 页对齐、全字段大端；分区自算 64 KiB / 64 KiB / 63 MiB / 32 MiB；冻结值（内核 `0x0010_0000`、boot info `0x0001_0000`、initramfs `0x0400_0000`、`rb17`、`supv`+身份映射）三处一致。

**独立注入（非工程师自检）**：`cp` 契约→`.preinject` + md5 `173033c7…` → §5 `rb17 0x0001_0000→0x0002_0000` → 检查器 **rc=1**（`进入状态[2] 契约==YAML` FAIL）、同一证据脚本 **rc=1**（`PASS=20 FAIL=7`）→ `cp` 回、md5 相等 → 检查器 **rc=0**、证据脚本 **rc=0**（`PASS=27 FAIL=0`）。快照对账：验收前后 7 文件 md5 逐一相等、`git status --porcelain -uall` 输出为空、无 `.preinject` 残留。

**约束核验**：改动 = 基线 `8cd4c184`→HEAD 恰 7 文件（spec 册 + 契约 + YAML + 检查器 + `.tao/contracts/README.md` + 锁 + 任务书），越界 0；完成区 27 行 ≤30、无运行期路径；证据基线钉 commit 常量非 `HEAD`；`DADAO-23` 与其余 20 册未改（锁现算 sha 全对、仅 Machine-v5 变，册头/附录 `0.4.6-rc`）；全程未提交 git、未动主工作树。

**check-spec-drift 分类裁定：成立（非凑绿）** —— ① ADR-0004 引用有实质：`§D2.2/D2.3` = ELF+raw 双路径与「装载越界 ⇒ host 非零退出」，状态 Accepted，`contract-elf` 同源同引；② 任务同时硬性要求契约 `0.1.0` 与 drift rc=0，而 spec-sourced 分支强制 == README Machine `0.4.0`，二者不可兼得（改 README Machine 列＝篡改「spec 册已发布版本」语义、改契约版本＝违反验收2，均不成立）；③ 仓库已有 ADR-sourced 先例（`contract-elf`、`contract-see`）。**finding**：版本线对齐口径（自有 `0.1.0` vs Machine `0.4.0`）宜登记「待裁定」，与遗留的「是否立启动 ABI ADR」一并交用户/architect 裁定。

**非阻断 finding（文档级，architect 收尾改）**：① spec §6.3.3「`0x60` 之后到页尾（`0x1_0000`）」含混（页为 `[0x0001_0000, 0x0002_0000)`，建议改「页内偏移至 `0x1_0000`」，改后须同笔重算锁 sha）；② 根 `contracts/README.md` 投影表缺 `linux-boot.yaml` 行（超范围，完成区已披露）；③ 自审表 F5 中间 sha `6dadcbb…` ≠ 最终锁值 `b0216180…`（其后改动重算所致）；④ 完成区称 `[Machine-v5 §6.3]` 会被 `check-spec-refs` 判红——本人在临时树全量替换为该形 rc=0，实为「不被校验」而非判红，理由措辞不准（改用 `Machine-01` 前缀的结论仍对，`contract-see` 同惯例）。


### 第 2 轮 engineer 自审（返工：裁定 A 地址术语 / 裁定 B 启动模型）

改动面 = 6 个文件（spec §6.3 / 契约 / YAML / 检查器 / 只读锁 / 任务书），逐行审查并逐条处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1 ABI 文本仍把入口/boot info/kernel_base/initramfs/栈写成 PA | ✅已修 | 全量改 VA；PA 仅存于页表项/`PTBR`/loader 写内存 | 检查器 `kind: va` 逐字段「语义标注 VA、不得写 PA」全 PASS |
| R2 `p_vaddr == p_paddr` 旧口径留在规则/PROSE | ✅已修 | 规则改 `ELF-VA-TO-PA`（VA→映射 PA，`p_paddr` 不作为装载地址） | 检查器 + 证据脚本均断言该串出现 0 次 |
| R3 未写「`ptw_enable=0` ⇒ `CFXMEM`」硬约束与 M1 中间态不存在 | ✅已修 | §6.3 增「硬约束」段并引 `§1.2`；契约 §1 同步 | 检查器断言 §6.3 含 `CFXMEM` + `ptw_enable = 0`；self-test 术语缺失类可达 FAIL |
| R4 未写其它 hart 在 K0 的状态 | ✅已修 | 进入状态表 + bullet：仅 hart 0 在线、其它未定义、不得依赖 | 检查器断言进入状态 hart 项含「其它 hart」 |
| R5 YAML 只有 `boot_info.pa`，字段无地址类别，无法机械核术语 | ✅已修 | 增 `address_model`/`startup_model`、`pa`→`va`、每字段 `kind`（va/pa/scalar/runtime） | 检查器按 kind 断言；页大小/`ptw_enable`/寄存器与 YAML 交叉一致 |
| R6 self-test 仅 4 类，未覆盖新裁定 | ✅已修 | 增「术语缺失（CFXMEM→CFXPERM）」「boot info 改称固定 PA」两类 ⇒ 6 类，各可达 FAIL | `--self-test` rc=0，6 类注入 6 次「注入 FAIL → 还原回绿」 |
| R7 证据脚本注入类数写死 4、缺术语/启动模型段 | ✅已修 | 类数由 self-test 日志现场派生；新增 H 段（术语/旧口径/M1/其它 hart/保留区）与第 3 路真实注入 | 证据脚本 rc=0，`PASS=53 FAIL=0` |
| R8 reviewer finding① §6.3.3「页尾」措辞含混 | ✅已修 | 改「页内偏移 `0x60` 之后至该页末（页内偏移 `0x1_0000`）」 | 文本核对；锁 sha 同笔重算 |
| R9 reviewer finding④ 完成区称 `[Machine-v5 §6.3]`「判红」不准 | ✅已修 | 改为「不被校验」 | 完成区已更新 |
| R10 表格 header 改「区间（VA）」后检查器未同步 | ✅已修 | 检查器表头匹配同步改「区间（VA）」 | 分区 5 行双向 PASS |
| R11 新块拼接后 §6.3.5 与 `---` 缺空行 | ✅已修 | 补空行 | 结构检查（numbering/changelog）rc=0 |

**判决**：无未修 finding；任务置 `待验收`（返工部分待第 2 轮 reviewer 复核）。

### 第 2 轮 reviewer 验收

**判决：Accepted**（下列输出全部为本人在本任务 worktree 独立重跑所得；最终接受归 architect 终审）

**重跑记录（命令 | rc | 关键输出）**
- `python3 tools/linux/check_boot_contract.py` | **0** | `[PASS]` 199 项 / `[FAIL]` 0；现场统计 `§6.3 行数=115`、`规则=elf:7,fail:2,initramfs:3,raw:4`、`DTB 提及=3`
- `… --self-test` | **0** | `self-test: 6 类注入，失败 0 项`；6 类（偏移/magic/入口基址/字段缺失/术语缺失/地址术语回退）逐类「命中 1 处 → 注入后 rc=1 → 还原后 rc=0」
- `bash <运行期证据目录>/run.sh` | **0** | `汇总: PASS=53 FAIL=0`（返工后跑 2 次均绿；3 路真实文件注入 + `cp`+md5 还原；日志内 4 条 `[FAIL]` 均为 `[INFO]` 回显的注入态失败，非断言失败）
- 门控 `make check-spec-{readonly,changelog,drift,numbering,refs}`、`check-contracts-{dir,pending}`、`check-test-reports`、`check-{dirs,no-residue}`、`check-spec-{purity,cite-targets}` **全 rc=0**（readonly=`21 read-only spec volume(s) OK`，refs=`0 violations`，drift=`错误 0 个`）
- `python3 tools/infra/check_knowledge_refs.py` | **1** | 5 条全在 `m13-testcases-013` 任务书；该文件与检查器相对基线 `8cd4c184` diff 为空 ⇒ 基线既有红（非本任务引入，验收7 该项照旧 BLOCKED）
- 锁现算：`sha256sum spec/Machine-v5-…` = `e13ac126…` 与锁值相等；`git diff 8cd4c184..HEAD -- manifests/spec-readonly.lock.toml` 仅 1 hunk、仅 Machine-v5（其余 20 册 sha 不变）
- `grep check-linux-boot-contract Makefile` **本分支缺席**（分支基线早于 `m14-linux-001` 的 `6e1b0f14` 合入）；用 `make -f <(git show master:Makefile) check-linux-boot-contract` 验 master 侧目标 **rc=0** ⇒ 目标可用，合入 master 后即可直接跑

**裁定落地（逐条核）**：**A ✓** — §6.3 L324「地址术语硬约定：一律 VA、`addr[41:0]`、PA 只三处」、L385/L416/L417 VA 口径、L351/L357 `p_paddr` 不作装载地址；YAML `address_model.abi_addresses: va` + 每字段 `kind`（`pa` 仅 `ptbr`）。**B ✓** — L326 M1「预建 64 KiB 身份映射 `VA[0,2GiB)→PA[0,2GiB)`、`PTBR` 指向、`ptw_enable=1`、`rb16` VA 入口」、L328「`ptw_enable=0` 取指/访存直接 `CFXMEM`（引 §1.2）、不存在 MMU 关运行」、L422/L428 其它 hart 未定义、L345 保留区与 initramfs 区不得回收；契约 §1/§7 与 YAML `startup_model` 同步。

**独立核对（自写解析器，不 import 被测脚本）**：boot info 15 行 / 分区 5 行 / 进入状态 10 项 / 规则 16 条，spec↔契约↔YAML 三方全等；布局自算 `max(offset+width)=0x60=size`、自然对齐无重叠；分区自算 64 KiB / 64 KiB / 63 MiB / 32 MiB。抽 5 字段：`ram_base`/`kernel_base`/`initramfs_base` 语义带（VA）、`ptbr` 语义 PA（唯一）、`flags` 标量，语义列 spec==契约。`grep -n "PA"` 逐条判：spec 仅 §1.1 PA RAM 行、§6 smon 写 PA 0/PTE、§6.3 三处术语说明+身份映射+loader 写 PA+`ptbr`、附录历史；契约/YAML 同构；旧口径 `p_vaddr == p_paddr`、`固定 PA \`0x0001_0000\`` 出现 **0 次**，**无 ABI 地址被称 PA**。

**独立注入（自设计，`cp`+md5）**：① spec 表 `kernel_base` 语义（VA）→（PA）⇒ **rc=1**（3 条 FAIL：语义列不等 / 标注 VA / 不得写 PA）→ 还原 md5 `2ec9b06b…` 相等、rc=0；② 删 §6.3「硬约束」整段 ⇒ **rc=1**（2 条 FAIL：术语 `CFXMEM` 缺、`ptw_enable=0 ⇒ CFXMEM` 缺）→ 还原 rc=0。验收前后 `git status --porcelain -uall` 均 0 行、md5 与验收前快照一致、无 `.preinject`/self-test 临时树残留。

**约束核验**：基线 `8cd4c184`→HEAD 恰 7 文件，与完成区声明逐一对上（越界 0）；完成区 28 行 ≤30、无宿主绝对路径；证据基线钉 commit 常量非 `HEAD`；`DADAO-23` 与其余 20 册未改；全程未提交 git、未动主工作树、未重建组件。

**非阻断 finding（文档级，architect 收尾改）**：① 任务书「目标」L22 与「接口规范」L38/L50/L80 仍写 PA（与裁定 A 冲突；`待裁定` 段已声明以裁定为准，建议改 VA 或加注）；② 检查器 L405 注释「4 类注入」应为 6 类、L72 `fmt_addr` docstring 误写「PA 格式」；③ 证据脚本 L65 注释「4 类注入」；④ `--self-test` 用 `tempfile.mkdtemp()` 落系统 `/tmp`（已自清），建议 `dir=` 指到任务临时目录；⑤ 根 `contracts/README.md` 缺 `linux-boot.yaml` 行（沿第 1 轮遗留）。

**未决（交 architect/用户）**：「页表由谁建」在 §6.3 L326 与契约 §1 写成**固件（smon）建立、loader 亦可预置**两可（与裁定 B 原话「loader/固件」一致），但 K1 须钉唯一写者与冲突语义（smon 重写 loader 预置表是否等价）；另沿第 1 轮：契约版本线 `0.1.0` vs README `Machine` `0.4.0`、是否立启动 ABI ADR。

### 收尾（architect，2026-11-13）

- 用户追加裁定：**身份页表只由 `smon` 固件建立**（宿主 loader 不代写页表页）。已按此改写 `Machine-v5 §6.3` 启动模型段与 `contract-linux-boot.md §1`；检查器 `check_boot_contract.py` 复跑仍 PASS（`--self-test` 6 类）。
- 顺带修 reviewer 非阻断项：`check_boot_contract.py` 注释「4 类」→「6 类」、`fmt_addr` docstring 改「地址格式（VA/PA 通用）」、根 `contracts/README.md` 补 `linux-boot.yaml` 行、锁 sha 按 §6.3 改动重算（`c9a373e4…`）。
- 台账/`discussing.md` 由主会话维护。
