# INTEG-049t: cg7 空间描述在 QEMU 落地

**模块**：integ
**项目里程碑**：M10
**依赖**：`SPEC-179t`（已验证；cg7 内部空间描述口径已落 `DADAO-12 §3.8`）、`INTEG-044t`（两轴权限 + `CFXREG`/`CFXPERM` 消费点）、`INTEG-045t`（`cfxld`/`cfxst` 已删）、`INTEG-048t`（deleg 强制；其探针 `open_cg7` 依赖旧 cg7 写回，本任务同步改造）
**状态**：待开始

## 执行环境
**执行环境**：本地（仓库 `/mnt/tao/DADAO-v5`，分支 `INTEG-049t`；`.work/source/qemu` 与 `.work/build/qemu` 均在场）

> **门锁现状（预检实测，执行时必读）**：`check-night` 正在跑（pid `3732460`，`2026-10-31T02:31Z` 起持有 `.dadao/gate.lock`，当前处于 `check-tset-llvm-full` 的 dynamic 段）⇒ `build-qemu`/`install-host`/`check`/`check-modules`/`check-arch` 会**排队等待**（`GATE_LOCK_WAIT=3600`）。探针（python 直跑）**不占锁**，可先做。**禁**绕过门控手工 `ninja`/`cp` 二进制（会打破与夜跑的互斥），**禁** kill 夜跑。
>
> **L1 受夜跑中间态影响（预检实测）**：`make check-run-artifacts` 现为 **rc=2**——在跑的夜跑目录 `.dadao/tests/llvm-ts-user/20261031T030901Z-llvm-ts-user-dynamic` 尚未落 `run.json`/`run.log`/`meta.json`（该段仍在进行）。这是**夜跑中间态**、非本任务产物；跑 L1 前须确认夜跑已结束（该目录三文件齐备）或在夜跑结束后重跑，不得据此改本任务判据、不得删夜跑目录。

## 目标（范围）

1. **QEMU 消费点**：移除旧 cg7 `sram_block_sel`/`sram_addr`，改为 16 块 × 4 字的**静态只读描述表**；`cfx2rd` 可读任意 rc（`space[1..15]` 与无空间 cfx 读 0），`cfx2rc` 写任意 cg7 rc ⇒ `CFXREG`；不实现 cache/共享/volatile 语义（属性只回读）。
2. **旧探针改造**：`min_rom_probe_044t`（`reset_values`）、`min_rom_probe_045t`（`cfx2_full_regface` + 写侧新例）、`min_rom_probe_integ048t`（`open_cg7`）按新语义改造，**不删用例、不放宽断言**。
3. **新探针**：`min_rom_probe_integ049t.py`，覆盖四类有空间 cfx、无空间 cfx、只读/`CFXREG`、`exists=0` 读 0、类型 one-hot、attr 值、power `X=1`、`space[1..15]` 清零、未实现 cfx 语义不变。
4. **契约与登记**：`contract-see.md` 补 cg7 块级说明；QEMU `changelog` 1 条；`Makefile` 的 `ARCH_CFX_PROBES` 与 `tools/testcases/arch/README.md` 索引同步；证据脚本（含可达 FAIL 注入）。

## 问题根源

1. **规范已改、实现未跟**：`spec/DADAO-12 §3.8`（`SPEC-179t` 落纸）把 cg7 定为**内部空间描述寄存器**：每 4 个 rc 描述一个空间块、`i=0..15` 共 16 块（`rc = 4i+0..3` = desc/start/size/attr），`exists=0` 时 start/size/attr 读 0，**全部只读、写任意 rc ⇒ `CFXREG`**，且已明确「cg7 只描述空间、不做传输控制」。QEMU 仍实现在**已删除**的旧语义上——块选择 + 块内地址两个 RW 寄存器（实测：`components/qemu/patches/target/dadao/cpu.h.patch:335-336` 的 `sram_block_sel`/`sram_addr`；`helper.c.patch:1577-1578` 的 `cfx_reg_ptr()` `case 7` 返回这两个字段指针 ⇒ 读写均通）。
2. **后果**：软件无法发现 smon/hmon/pmem/power 的核内空间（`§2.1` 表的 start/size/类型无机器可读来源），且旧 RW 语义与「写 ⇒ `CFXREG`」直接冲突（旧实现允许写「块选择」这类已不存在的控制面）。
3. **测试面停在旧语义**（实测）：`min_rom_probe_045t.py:376-378` 用 `cfx2rc` 写 cg7 rc0/rc1 再读回（期望 `0x1234`/`0x5678`）；`min_rom_probe_044t.py::reset_values` 的 docstring 声称覆盖「cg0-cg7 reset values」但**无任何 cg7 断言**；`min_rom_probe_integ048t.py:401-408` 的 `open_cg7` 用 supv 写/读 `cfx_ptw cg7 rc0` 证明 deleg 放行（改造后会因「写 ⇒ `CFXREG`」而红）。
4. **契约投影缺块级**：`.tao/contracts/contract-see.md:44` 只有「每个 cfx 提供 cg0–cg7 共有寄存器」一句，未描述空间块 ⇒ 实现侧无归一化契约可依。
5. **背景（来自 `SPEC-179t` 遗留 1）**：该任务明确把「QEMU 仍按旧语义实现 cg7、`min_rom_probe_044t/045t` 仍测旧 cg7、`contract-see.md` 仍只写 cg0–cg7」登记为**后续任务**，即本任务。

## 已确认口径（用户给定，逐条落纸）

**cg7 空间表（测试机实测值；`desc`：bit0=exists，bit1=SRAM，bit2=ROM，bit3=MMIO，bit4=DRAM，bit5=OTHER；`attr`：bit0=R，bit1=W，bit2=X，bit3=cacheable，bit4=shareable，bit5=volatile）**

| cfx | 名称 | 空间块 | desc | start | size | attr |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | smon | `space[0]` | `0x3`（exists+SRAM） | `0x3ff_0000_0000` | `0x1_0000` | `0x7`（R=1 W=1 X=1，cacheable/shareable/volatile=0） |
| 3 | hmon | `space[0]` | 同 smon | `0x3ff_0000_0000` | `0x1_0000` | `0x7` |
| 17 | pmem | `space[0]` | `0x3` | `0x3ff_0000_0000` | `0x1_0000` | `0x3`（R=1 W=1 **X=0**） |
| 63 | power | `space[0]` | `0x5`（exists+ROM） | `0x3ff_fffc_0000` | `0x4_0000` | `0x5`（R=1 W=0 **X=1**） |
| 0/1/4 | umon/jmon/ptw | 16 块全空 | 0 | 0 | 0 | 0 |

- **所有 cfx 的 `space[1..15]` `exists=0`**，start/size/attr 读 0（即除上表 4 行外，全部 rc 块读 0）。
- **其余 cfx**（`cache`/`hart`/`llc`/`time`/`uart`/reserved）在测试机**未实现** ⇒ 访问其 cfx 寄存器（含 cg7）仍为 `CFXREG`；**不得**把它们改成「可读 0」（`exists=0` 只对**已实现**的 cfx 可见）。
- `cg7` **全部只读**；`cfx2rc` 写**任意** rc（`rc0..rc63`）⇒ `CFXREG`；`cfxld`/`cfxst` 已删除，cg7 **不做传输控制**。
- **地址自洽**：完整核内地址 = `(cfxha << 42) | start` ⇒ smon `0x0bff_0000_0000`、hmon `0x0fff_0000_0000`、pmem `0x47ff_0000_0000`、power `0xffff_fffc_0000`，与 `DADAO-12 §2.1` 表/`contract-see §2` 一致；`start + size ≤ 2^42`（power 恰 `= 2^42`）。
- **属性只回读**：不实现 cache/共享/volatile 模型，不据 `attr` 改变访存/取指权限（`tlb_fill` 与 cfxmem/cfxexe 判定**不动**）。pmem `X=0` 与 `§2.1`「按各自异常向量取指需求给出 X」相容（pmem SRAM 不承载异常向量）。

## 接口规范

### 1. QEMU 最小改法（`components/qemu/patches/target/dadao/{cpu.h,helper.c}.patch`）

1. **删字段**：`cpu.h.patch` 的 `DADAOCfxRegs` 删除 `sram_block_sel` / `sram_addr`（cg7 不再有每 cfx 存储；不新增其它字段）。
2. **静态只读表**（编译期常量，**不占 `CPUArchState`**）：新增 `static uint64_t dadao_cg7_space_reg(int cfxha, unsigned rc)`：
   - `blk = rc / 4`、`fld = rc % 4`；`blk != 0 ⇒ 0`（`space[1..15]` 全空）；
   - `cfxha == 2 || cfxha == 3`：`fld` 0..3 ⇒ `0x3` / `0x3ff_0000_0000` / `0x1_0000` / `0x7`；
   - `cfxha == 17`：同上，`fld == 3 ⇒ 0x3`；
   - `cfxha == 63`：`0x5` / `0x3ff_fffc_0000` / `0x4_0000` / `0x5`；
   - 其它（已实现 `0`/`1`/`4` 等）⇒ `0`；保留位恒 0。
3. **`cfx_reg_ptr()` 删除 `case 7`**（cg7 不再经该函数；读写都返回 `NULL` 的兜底不再使用，见下两条）。注释同步：`DADAOCfxRegs` 结构注释里「cg4..cg7 (config / exception frame / scratch / sram control)」改为不含 sram control 的表述。
4. **`helper_cfx2rd`**：在 `reserved ⇒ ILLI` → `cfx_idx < 0 ⇒ CFXREG` → `cfx_perm_denied(CFXREG 轴) ⇒ CFXPERM` → `cfx_deleg_denied ⇒ CFXPERM` →（`cg == 15 && pmem` 特例）之后、`cfx_reg_ptr()` **之前**插入：
   ```c
   if (cg == 7) {                       /* cg7 内部空间描述（只读，DADAO-12 §3.8） */
       if (rd != 0) env->rd[rd] = dadao_cg7_space_reg(cfxha, rc);
       env->pc = pc + 4; env->rb[0] = pc + 4; return;
   }
   ```
   语义要点：读**无副作用**、可重复读；权限门**先于** cg7 生效（supv 读 power cg7 仍由 cfxreg 轴 ⇒ `CFXPERM`，不得因 cg7 分支绕过）。
5. **`helper_cfx2rc`**：同一位置插入（任意 rc 一律拒绝）：
   ```c
   if (cg == 7) { cfx_raise(env, DADAO_CAUSE_CFXREG, cfxha, pc, info); return; }
   ```
6. **不改**：`tlb_fill`/cfxmem/cfxexe/两轴权限、`-d cpu` dump 格式（不加 cg7 dump 行，避免扰动既有探针解析；cg7 经 `cfx2rd` 观测）、`dadao_cpu_reset_hold()`（静态表无复位值）。
7. **组件工作流（`docs/Process-01`；顺序硬约束）**：`make check-source-state`（改前）→ 改 `.work/source/qemu` → 提交收敛为 base+1 → `python3 tools/infra/make_patch.py qemu` 导出（**禁手改补丁**）→ `make check-patch-tree` → `make build-qemu` → `make install-host` → `make check-source-state`（改后）。

### 2. 旧探针改造（**不删覆盖、不放宽断言**）

1. `min_rom_probe_044t.py::reset_values`：**新增** cg7 只读断言（body 在 hmon，读 **cfx3 self** `space[0]` 四字段）：`cfx2rd(3,7,0,rd5)`⇒`0x3`、`(3,7,1,rd6)`⇒`0x3ff_0000_0000`、`(3,7,2,rd7)`⇒`0x1_0000`、`(3,7,3,rd10)`⇒`0x7`。**禁用 rd8/rd9**（`exit_seq()` 会写 rd8/rd9）；docstring 的「cg0-cg7 reset values」保持真实并列明 cg7 空间描述。
2. `min_rom_probe_045t.py::cfx2_full_regface`：cg7 的**两条写回改为只读**——`cfx2rd(0,7,0,45)` / `cfx2rd(0,7,1,46)`，期望 `rd45=0`、`rd46=0`（umon 无空间）；行内注释与文件头用例表同步（「cg7 RO readback」）。
3. `min_rom_probe_045t.py` **新增 1 例**（写侧覆盖不丢）：`cfxreg_cg7_write`——`cfx2rc(0,7,63,rd20)` ⇒ `CFXREG`，期望 `cid:0`/`syncn:0`/`cip:0` = `ROM_BASE + idx*4`；setup 沿用同文件 `cfxreg_cg_oor` 写法（`set_cfx_vector(0,3,H)` + `set_cfx_vector(0,0,H)`）。用例数 13 → **14**。
4. `min_rom_probe_integ048t.py::open_cg7`：**删除写回**（写 cg7 现为 `CFXREG`），改为 supv **读** `cfx_ptw cg7 rc0` ⇒ `rd10 = 0`（ptw 无空间），仍证明 `deleg=0x8` 放行 cg7 读；用例名/描述/`rd` 期望同步。`power_cg7_closed` **保持不动**（cfxreg 轴先拒 ⇒ `CFXPERM`，与 cg7 分支无关；执行时须重跑确认）。

### 3. 新探针 `tools/testcases/arch/min_rom_probe_integ049t.py`

- **布局**沿用 `integ048t`：复位 power/hypv → 2 指令移交 hmon（cfx3/hypv）→ body 在 hmon；半托管参数块按 044t/048t 既有做法（RAM 或 smon SRAM）；观测 = `-d cpu` **最后一块** dump + `SYS_EXIT`；参数 `--qemu/--only/--list`，默认 QEMU = `.work/build/qemu/qemu-system-dadao`；期望值**手推自 `spec/DADAO-12 §2.1/§3.8` + `contract-see §3`**，不读 QEMU 实现。
- **用例（≥10，每例须有可达 FAIL 路径）**：
  1. `space_smon`（cfx2）：desc/start/size/attr = `0x3`/`0x3ff_0000_0000`/`0x1_0000`/`0x7`；
  2. `space_hmon`（cfx3）：同上；
  3. `space_pmem`（cfx17）：`0x3`/`0x3ff_0000_0000`/`0x1_0000`/`0x3`（**X=0**）；
  4. `space_power`（cfx63）：`0x5`/`0x3ff_fffc_0000`/`0x4_0000`/`0x5`（**X=1**）；
  5. `no_space_umon`（cfx0）：64 个 rc 全读、OR 累积 ⇒ 0；
  6. `no_space_ptw`（cfx4）：同 ⇒ 0；
  7. `space1_15_zero`（cfx2/3/17/63）：各自 `rc4..rc63` OR ⇒ 0（仅 `space[0]` 有值）；
  8. `desc_attr_reserved`：四个有空间 cfx 的 `desc & ~0x3F == 0` 且 `(desc>>1)&0x1F` 恰一位为 1；`attr & ~0x3F == 0` 且 `attr & 0x38 == 0`（cacheable/shareable/volatile 全 0）；
  9. `ro_all_rc`：cfx2/cfx63 的 rc0..rc63 **全部可读**（无 `CFXREG`），逐块值与表一致（允许"OR/异或校验 + 抽样逐值"，但抽样须含 rc0..rc3 与 rc60..rc63）；
  10. `write_cfxreg`：写 **cfx3（self）** `cg7` 的 rc0 / rc21 / rc63 各 ⇒ `CFXREG`（三次独立 fault，逐条断言 `cid`/`cip`）；
  11. `unimpl_cfx`：cfx5（cache，未实现）读 `cg7 rc0` ⇒ `CFXREG`（未实现 cfx 语义**不变**）；
  12. `read_stable`：同一 rc 连读两次值一致（无副作用）。
- 另加**探针内算术断言**：`start + size ≤ 2^42`，power 恰 `== 2^42`（smon/hmon/pmem `0x3ff_0000_0000 + 0x1_0000 < 2^42`）。

### 4. `.tao/contracts/contract-see.md`（块级说明，补 §3）

在 §3 现有条目后**追加一条**（体例同全文：单条断言 + 末尾来源标注；不用表格）：

> - **cg7 内部空间描述**：每个 cfx 用 cg7 描述自身核内空间——每 4 个 rc 一个空间块、`i=0..15` 共 16 块（`rc = 4i+0..3`）：desc（bit0=`exists`；bit1=SRAM/bit2=ROM/bit3=MMIO/bit4=DRAM/bit5=OTHER，存在时 one-hot）、start（42 位内部偏移，完整地址 `(cfxha << 42) | start`）、size（`start + size ≤ 2^42`）、attr（bit0=R/bit1=W/bit2=X/bit3=cacheable/bit4=shareable/bit5=volatile）；`exists=0` 时 start/size/attr 读 0；cg7 全部只读，写任意 rc ⇒ `CFXREG`；cg7 只描述空间、不做传输控制。测试机实测块：smon/hmon `start=0x3ff_0000_0000 size=0x1_0000 attr=R|W|X`、pmem 同 start/size 而 `X=0`、power `start=0x3ff_fffc_0000 size=0x4_0000 attr=R|X`；其余已实现 cfx（umon/jmon/ptw）无空间（16 块全 `exists=0`），未实现 cfx 访问仍 `CFXREG`。[DADAO-12 §3.8 cg7 - 内部空间描述寄存器][Machine-01 §3]（块值 = 测试机约定）

并在**附录 A** 的 `§3` 行来源列补 `§3.8 cg7 - 内部空间描述寄存器`。版本行不动（仍 `0.7.3-rc`，与 `DADAO-12` 同版本）。

### 5. changelog / Makefile / README

- `components/qemu/changelog.md`：`## M10` 节**文末追加 1 条**（体例：`- **2026-10-31 \`INTEG-049t\`**` + 缩进行 `  - 摘要：…` + `  - 执行者：engineer`），摘要写清「cg7 由旧 `sram_block_sel`/`sram_addr` 改为 16×4 只读空间描述表；写任意 rc ⇒ `CFXREG`；新增探针 N 例」。
- `Makefile`：`ARCH_CFX_PROBES` 追加 `integ049t`（追加在行尾）；`ARCH_CFX_PROBES` 上方的逐条注释区补一行 `# integ049t = cg7 内部空间描述（16×4 静态表 / 全部只读 / 写任意 rc ⇒ CFXREG）。`
- `tools/testcases/arch/README.md`：表格追加 `min_rom_probe_integ049t.py` 一行；第 20 行 `--qemu` 名单追加 `integ049t`。

## 修改文件范围

1. `components/qemu/patches/target/dadao/cpu.h.patch`
2. `components/qemu/patches/target/dadao/helper.c.patch`
3. `tools/testcases/arch/min_rom_probe_044t.py`
4. `tools/testcases/arch/min_rom_probe_045t.py`
5. `tools/testcases/arch/min_rom_probe_integ048t.py`
6. `tools/testcases/arch/min_rom_probe_integ049t.py`（新增）
7. `.tao/contracts/contract-see.md`
8. `components/qemu/changelog.md`
9. `Makefile`
10. `tools/testcases/arch/README.md`
11. 本任务书（完成区 + 状态）
12. `.tao/knowledge/milestones.md`（本任务流水行状态）

**明确不动**：`spec/**`（含 `DADAO-12`/`Machine-01`，用户明确不改）、`.tao/adr/**`（cg7 布局已固化，**不新建/不改 ADR**；如需改决策由主会话先与用户逐条确认）、`components/llvm-project/**`（LLVM 汇编端 stride 缺口仍登记遗留）、`contracts/**`（机器可读数据：`cfx-aliases.txt` 已由 SPEC-179t 生成 768 条 `space_*`）、`tests/**`、`tests/shared/bootrom/**`、`manifests/**`、`docs/DDLN/**`（讲义口径滞后，登记遗留）。

## 约束

1. **只落回读**：仅实现 cg7 只读表与写拒绝；不实现 cache/共享/volatile 语义，不改 `tlb_fill`/cfxmem/cfxexe/两轴权限。
2. **未实现 cfx 语义不变**：cfx5 与 reserved 仍 `CFXREG`；`exists=0` 只对已实现 cfx 可见。
3. **不扩状态**：cg7 值来自静态常量表，**不得**在 `DADAOCfxRegs`/`CPUArchState` 新增 16×4 存储，也不得保留旧字段。
4. **禁手改补丁/生成物**：补丁唯一来源 `.work/source/qemu` + `make_patch.py`；`contract-see.md` 手写（非生成物）。
5. **门控互斥**：`build-qemu`/`install-host`/`check*` 一律经 `make`（自动 `flock` 排队）；**禁**手工 `ninja`、**禁**手工 `cp` 二进制到安装根（`ISS-300` 口径）、**禁** kill 在跑的夜跑。
6. **旧探针最小改造**：只把旧语义断言换成新语义断言，用例数不减、断言不放宽（`045t` 13→14、`044t` 13 不变、`integ048t` 不减）。
7. **证据**：`.work/evidence/<任务ID>/run.sh`（+ `--inject`，实现期落地）一键复跑；至少 1 项「注入 → FAIL → 还原 → 绿」，还原用 `cp` 备份 + `md5` 对账，**禁** `git checkout/restore/stash/show`。
8. **临时目录** `/tmp/opencode/INTEG-049t/`；长日志落 `.work/log/integ/`；仓库内不得留 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`*.bak`。
9. **构建成本**：改 `.c/.h` 不动 meson ⇒ `make build-qemu` 走增量（**估算 1–3 min**，`cpu.h` 变更会重编 `target/dadao` 全目标并链接）；`install-host` 其余组件应为 no-op。若出现「需 `build-qemu-reconfig`」或「首次全量构建（10–30 min）」⇒ **停手上报**，不自行跑长构建/夜跑。若门锁排队超过 15 min ⇒ 记录现场（`cat .dadao/gate.lock` + `pgrep -af check-night`）并继续等待或先做不占锁的探针工作，不 kill。
10. **提交权归 architect**：engineer 只改文件 + 填完成区；**不提交、不 push**。

## 验收标准

1. **文件集精确（12 项）**：`git status --porcelain -uall`（实现阶段）/`git diff --name-only master...HEAD`（提交后）仅含上述 12 项；`spec/**`、`.tao/adr/**`、`components/llvm-project/**`、`contracts/**`、`tests/**`、`manifests/**`、`docs/**` **零改动**；越界即 FAIL。
2. **旧语义零残留**：`grep -rn 'sram_block_sel\|sram_addr' components/qemu/patches tools/testcases/arch`（排除 `__pycache__`）⇒ **0**；`helper.c.patch` 的 `cfx_reg_ptr()` 中**不再有** cg7 分支（人工核 diff 上下文，避免误命中其它 `case 7`）；`cpu.h.patch` 的 `DADAOCfxRegs` 无这两个字段。
3. **表值逐条**：探针用例 1–4、7、9 覆盖 16 块 × 4 字段（cfx2/3/17/63 全 64 rc）+ cfx0/4 全 64 rc；另以脚本独立断言 4 组 `(desc,start,size,attr)` 与 `start+size ≤ 2^42`（power 恰 `= 2^42`），并断言 `(cfxha<<42)|start` 等于 `§2.1` 四个地址。
4. **新探针**：`python3 tools/testcases/arch/min_rom_probe_integ049t.py` rc=0（**≥10 例**）；`--list` 含「接口规范 §3」列出的 12 个用例名。
5. **旧探针**：`min_rom_probe_044t.py` rc=0（13 例，含 cg7 `space[0]` 4 值断言）、`min_rom_probe_045t.py` rc=0（**14 例**，含 `cfxreg_cg7_write`）、`min_rom_probe_integ048t.py` rc=0（`open_cg7` 只读化后仍 PASS、`power_cg7_closed` 仍 `CFXPERM`）。
6. **组件闭环**：`make check-patch-tree` rc=0（`205 patches OK`）；`make build-qemu` rc=0；`make install-host` rc=0；安装根 `qemu-system-dadao` 与 `.work/build/qemu/qemu-system-dadao` 的 `md5sum` **相同**（证明安装同步，`ISS-210` 口径）；`make check-source-state` rc=0（源树干净、base+1）。
7. **门控 L1/L2/L3**：`make check` rc=0；`make check-modules` rc=0；`make check-arch` rc=0（日志含 `integ049t` 在内的 **11** 个 cfx 探针，且 `arch-smoke` 绿）。
8. **契约/文档**：`contract-see.md` §3 含 cg7 块级条目（`grep` 在 §3 段内命中 `space`、`exists`、`CFXREG`、`0x3ff_fffc_0000`、`(cfxha << 42)` 各 ≥1）、附录 A `§3` 行含 `§3.8`；`make check-contracts-dir` rc=0；`changelog` 新增恰 1 条且 `make check-component-changelog` rc=0；`Makefile` 的 `ARCH_CFX_PROBES` 含 `integ049t`（`grep -c` ≥1）；`tools/testcases/arch/README.md` 含 `integ049t` 两处（表格行 + `--qemu` 名单）。
9. **证据脚本**：`bash .work/evidence/<任务ID>/run.sh` rc=0；`bash .work/evidence/<任务ID>/run.sh --inject` rc=0，含 ≥1 项可达 FAIL（建议：把静态表某 `attr` 由 `0x7` 改成 `0x5`，或恢复 `cfx_reg_ptr()` 的 cg7 分支 ⇒ 探针 FAIL；`cp`+`md5` 还原后回绿）。
10. **收尾**：完成区 ≤30 行、`**状态**` = `待验收`、`milestones.md` 流水行状态同步；仓库无临时残留。

## 下发前预检（5 项，architect 本轮实测）

1. **任务书内部一致**：目标（4 项）/接口规范（QEMU 7 条〔含工作流〕+ 3 个旧探针 + 新探针 12 例 + 契约 + 登记）/修改文件（12 项）/验收（10 条）逐条对应；用户给定 cg7 空间表已逐行落纸（含 `desc`/`attr` 派生数值 `0x3`/`0x5`/`0x7`/`0x3`/`0x5`）；依赖 `SPEC-179t`、`INTEG-044t`、`INTEG-045t`、`INTEG-048t` 均 `已验证`（`milestones.md` 流水行实测）。结论：**PASS**。
2. **验证手段前置实际可用（本轮实测）**：`python3 tools/testcases/arch/min_rom_probe_044t.py` rc=0（`.work/log/integ/INTEG-049t-precheck-044t.log`，14 PASS 行）；`045t` rc=0（14 PASS 行）；`min_rom_probe_integ048t.py` rc=0（24 PASS 行，含 `open_cg7`）；`make check-patch-tree` rc=0（`5 component(s), 205 patches OK`）；`tools/infra/make_patch.py`、`.work/source/qemu/.git`、`.work/build/qemu/build.ninja`、`.work/build/qemu/qemu-system-dadao`（35 MB，10-31 10:16）均在。**未取到 L1 基线**：`.dadao/gate.lock` 被在跑的 `check-night` 持有（pid `3732460`，`2026-10-31T02:31:26Z` 起，正在 `check-tset-llvm-full` dynamic 段），`make check` 进入排队后由本方主动终止（日志 2 行 = `WAIT` + `Terminated`，`.work/log/integ/INTEG-049t-precheck-check.log`）；另实测 `make check-run-artifacts` rc=2（夜跑目录 `.dadao/tests/llvm-ts-user/<stamp>-dynamic` 未落盘三文件，中间态），`check-tasks`/`check-knowledge-refs`/`check-contracts-dir`/`check-dirs`/`check-no-residue` 均 rc=0。结论：**PASS（带门锁前置条件，见「执行环境」与约束 5/9）**。
3. **验收逐条可跑性**：验收 1–10 **现在可跑**（构建/安装/门控在锁释放后自动排队；探针不占锁）；无 BLOCKED 项。`build-qemu` 增量 **1–3 min 为估算**（`.c/.h` 改动与 no-op 基线的实测须在任务内留证，不符时按实际耗时登记，不改判据）。结论：**PASS（无 BLOCKED）**。
4. **与 `contracts/`、`tests/inst/` 一致**：`contracts/cfx-aliases.txt` 已由 SPEC-179t 生成 768 条 `cfx_*_space_{desc,start,size,attr}[n]`（实测 `reg cfx_umon_space_desc[0] 0 7 0 1 canonical`）⇒ 本任务**不动机器可读数据**；`tests/inst/**` 与 `tests/**` 无 `cg7`/`space_*` 别名引用（grep 0 命中）；`contract-see.md` 缺块级说明**在本任务范围内补**；`Makefile`/README 的探针登记亦在本任务范围。结论：**PASS**。
5. **拟改文件 × `spec/` 清单**：命中 **0**（12 项全在 `spec/` 之外；用户明确「不改 `spec/**`」）⇒ **不构成 BLOCKED**，无需 spec 授权。ADR：无需新建——cg7 布局由 `SPEC-179t`（用户 2026-10-31 裁定）固化，本任务只落地实现与投影。

## 风险与已知缺口

1. **门锁排队 + L1 中间态**：夜跑在跑（见「执行环境」）；`build-qemu`/`install-host`/`check*` 可能各等十数分钟，且 `check-run-artifacts` 在夜跑未收尾时会红（实测 rc=2）。处置：先做探针改造（不占锁），构建/门控集中一次排队；**不得**绕过门控；L1 重跑前确认夜跑已收尾并记录现场。
2. **`integ048t::open_cg7` 的连带失败**：若不改该探针，`make check-arch` 必红（写 cg7 变 `CFXREG`）。已列入范围（改只读）。
3. **supv 侧可见性**：cg7 读仍受**两轴权限**与 `deleg` 约束（supv 读 power cg7 ⇒ `CFXPERM`）；新探针以 hypv（hmon）运行，不叠加这两道门；**不得**为实现探针方便而放宽权限。
4. **`docs/DDLN/C-资源管理/{DD,TU}-C003/C004`** 仍按旧口径描述「cg7 = SRAM `block_sel`/`sram_addr`」⇒ 讲义漂移，**不在本任务范围**，登记为遗留（需另立文档任务）。
5. **LLVM 汇编端**仍不能拼写 `cfx_<name>_space_*[i]`（`SPEC-179t` 遗留 2：运行时表 `format=1` 无 stride 字段）⇒ 本任务不改 LLVM，新探针只用 `cfx2rd`/`cfx2rc` 编码，不依赖汇编别名。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
