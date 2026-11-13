# m14-spec-001: 启动 ABI 契约（Vast 内核装载 + 固定 boot info）

**模块**：spec
**项目里程碑**：M14
**依赖**：`m14-linux-001`（批次先行；不共享文件）
**可并行分片**：否（单册单写者；与 `m14-spec-002` **串行**，同改 spec 版本锁与 `.tao/contracts/README.md`）
**预估**：6–7 h
**状态**：待开始

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

（需用户语义裁定的事项写这里：问题 + 选项 + 建议 + 自决的临时处置；返回主会话。）

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审（待填）

### 第 1 轮 reviewer 验收（待填）
