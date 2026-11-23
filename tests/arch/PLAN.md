# `tests/arch` 落点方案（Vast arch scope）

> 任务：`m16-testcases-004`（盘点与方案；不建 `run_arch.py` 实现、不写新用例、不跑仿真）。
> 上位裁定：`.tao/knowledge/discussing.md`「M16 三方差分（Vast arch）批次裁定」（用户 2026-11-22）。
> 盘点证据：`tests/arch/vast-arch-inventory.md`（9 cfx × 3 平台 = 27 格）。
> 本文件只定**落点与接口**；具体实现按批次 2 起拆任务。

## 1. 目标与边界

- arch scope **只测 Kaiwu-Vast**（`system` 平台），不含 Tiny、不含 linux-user；
  cfx 范围 **0/2/3/4/5/15/32/34/63**（umon/smon/hmon/ptw/cache/hart/pmem/time/power）。
- 判据：**同一用例在三平台逐槽签名一致**；期望值独立派生自 `spec/`/`contract`，
  用户是 oracle；不一致由用户裁定。
- 仿真**不进常规门控**（L2/L3）；由 `run_arch.py` 按需/里程碑收口调用。
- QEMU / gem5 / chipyard 是**同一 scope 的三种承载**，不是三个 scope；用例、脚本、
  数据都在 `tests/arch/` 内。

## 2. 目录结构

```text
tests/arch/
  README.md                     # scope 说明（cfx 范围、载体、门控边界）
  run_arch.py                   # 唯一驱动（见 §3）
  common/                       # arch 内共享薄壳（非用例）
    signature.py                #   转调 tests/shared/signature.py（见 §6）
    bootrom.py                  #   step5 BootROM 构建/定位（现 tools/testcases/arch 迁入）
    platform.py                 #   qemu/gem5/chipyard 命令行与产物路径
  vast-arch-inventory.md        #   27 格盘点矩阵（本任务产出）
  expected-divergences.yaml     #   允许差异清单
  umon/                         # cfx0：执行向量 + expected.yaml
  smon/                         # cfx2
  hmon/                         # cfx3（仅 Vast；Tiny 用例迁出，见 §7）
  ptw/                          # cfx4：PTW + TLB（含 driver、tlb/、expected.yaml）
  cache/                        # cfx5：dcache/ icache/ 两组阵列探针 + cfx5 命令用例
  hart/                         # cfx15
  pmem/                         # cfx32
  time/                         # cfx34
  power/                        # cfx63
```

- 每个 `<cfx>/` 自包含：用例（`.s`/`.S`）、`.lds`、生成器（`gen_*.py`）、
  判据（`check_*.py`）、`expected.yaml`。
- 驱动型用例（`kind: driver`）的 `file` 指向本目录 `check_*.py`，由 `run_arch.py` 调起；
  不再把 arch 专属判据放 `tools/testcases/arch/`。
- `tests/arch/` 只放 scope 内入库数据（盘点矩阵、矩阵快照），不被
  `tests/arch.yaml` 当载体、不进 case 清单。

## 3. `run_arch.py` 接口

```text
python3 tests/arch/run_arch.py \
  --cfx 4[,5,...] \
  --platforms qemu,gem5,chipyard \
  --cache-model on \
  [--case arch-ptw-001] [--work-dir <运行期目录>] [--self-test] [--list]
```

- `--cfx <0|2|3|4|5|15|32|34|63>`：可逗号分隔；缺省 = 全部 9 个。非法值 ⇒ 退出码 2。
- `--platforms`：`qemu` / `gem5` / `chipyard` 的逗号列表；缺省 = 三者全跑。
  任一平台不可用 ⇒ 该平台记 `SKIP` 并**非零退出**（禁止静默降级为「两平台通过」）。
- `--cache-model on|off`：**arch 固定 `on`**；传 `off` ⇒ 退出码 2（提示 arch 不测直通模式）。
  映射：QEMU `-M kaiwu-vast,cache-model=on`；gem5 `--profile vast --caches`；
  chipyard `WumingVastConfig`（cache 默认启用）。
- `--case`：只跑指定 case（`tests/arch.yaml` 的 `id`），用于单点复现。
- `--self-test`：不启动模拟器，只校验各 `expected.yaml` 可解析、签名槽数一致、
  driver 声明的 `--selfcheck` 可跑（每条判据有可达 FAIL 路径）。
- `--list`：打印 `cfx × case × platform` 计划表，不执行。
- 退出码：`0` 全通过；`1` 任一用例/平台失败；`2` 用法或配置错误。
- 产物：每 case × 平台一份 `signature.bin` + `run.json`（进程命令、rc、stdout/stderr 路径），
  落运行期证据目录；不写固定绝对路径。

## 4. `tests/arch.yaml` 字段方案

现行字段（`id/file/platforms/level/requires`）**保留**；新增两个：

```yaml
- id: arch-ptw-001
  file: arch/ptw/check_tlb.py
  kind: driver                 # asm | driver；缺省 asm
  machine: vast                # arch 固定 vast（tiny/user 由其它 scope 负责）
  platforms: [system]          # 运行模式，不是机型
  level: full                  # smoke | full
  requires: [bootrom]
```

- `kind: asm`：`file` 是执行向量（`.s`/`.S`）；`kind: driver`：`file` 是 scope 内驱动
  （`check_*.py`），由 `run_arch.py` 调起。
- `machine`：枚举 `tiny|vast|user`；arch 条目一律 `vast`。机型不写进 `platforms`。
- `platforms: [system]` 不变（QEMU/gem5/chipyard 是承载，不新增 `platforms` 值）。
- `check-tests-index` / `case-ledger` 的字段校验**本任务不改**（留给落点实施任务，
  需同步：字段白名单、`kind` 缺省、`machine` 必填/取值、跨四册 ID 唯一）。

## 5. 迁移清单

| 来源（现状） | 去向 | 说明 |
|---|---|---|
| `tools/chipyard/ptw/vastptw.S`、`vastptw.lds`、`check_vastptw.py` | `tests/arch/ptw/` | cfx4 寄存器面 carrier + 判据 |
| `tools/chipyard/ptw/vastwalk.S`、`vastwalk.lds`、`gen_vastwalk_tables.py`、`check_vastwalk.py` | `tests/arch/ptw/` | 两级步查/A-D |
| `tools/chipyard/tlb/vasttlb.S`、`vasttlb.lds`、`gen_vasttlb_tables.py`、`check_vasttlb.py` | `tests/arch/ptw/tlb/` | I/D TLB 同属 cfx4 |
| `tools/chipyard/dcache/vastdcache.S`、`gen_vastdcache_tables.py`、`check_vastdcache.py` | `tests/arch/cache/dcache/` | cfx5 阵列面 |
| `tools/chipyard/icache/vasticache.S`、`gen_vasticache_tables.py`、`check_vasticache.py` | `tests/arch/cache/icache/` | cfx5 阵列面 |
| `tools/chipyard/excp/causeid.S`、`check_causeid.py` | `tests/arch/hmon/` | cfx3 异常帧全宽 |
| `tools/chipyard/excp/prevcfx.S`、`check_prevcfx.py` | `tests/arch/power/` | cfx63→cfx3 移交 |
| `tools/testcases/arch/min_rom_probe_tlb.py` | `tests/arch/ptw/ptw_carrier_tlb.py` + `check_tlb.py` | 15 条 `arch-ptw-*` driver（`m16-testcases-010` 已完成迁移） |
| `tools/testcases/arch/min_rom_probe_integ039t.py`、`integ040t.py` | `tests/arch/ptw/` | 页表/TLB 场景 |
| `tools/testcases/arch/min_rom_probe_integ042t.py`、`integ047t.py` | `tests/arch/pmem/` | SRAM/DMA |
| `tools/testcases/arch/min_rom_probe_integ050t.py` | `tests/arch/time/` | cfx34 + cfx15 计数 |
| `tools/testcases/arch/min_rom_probe_integ051t.py` | `tests/arch/hart/` | TIMER 仲裁 |
| `tools/testcases/arch/min_rom_probe_044t.py`、`045t.py` | `tests/arch/umon/` | 寄存器面/权限 |
| `tools/testcases/arch/min_rom_probe_integ046t.py` | `tests/arch/power/` | step5 启动链 |
| `tools/testcases/arch/min_rom_probe_integ048t.py` | `tests/arch/hmon/` | cg_reg_deleg |
| `tools/testcases/arch/min_rom_probe_integ049t.py` | `tests/arch/power/` | cg7 空间描述 |
| `tools/testcases/arch/run_m5_e2e.py` + `tests/arch/umon/*` | `tests/arch/run_arch.py --cfx 0` | 向量执行并入统一驱动 |
| `tools/testcases/arch/min_rom_probe_integ007t.py` | `tests/unit/gem5/` | Tiny hmon，随 §7 迁出 |
| `tests/arch/hmon/{tiny_hmon.*,tiny_hmon_min.S,tiny_hmon_layout.inc,expected.yaml,README.md}` | `tests/unit/gem5/tiny_hmon/` | Tiny，见 §7 |
| `tools/gem5/check_tiny_hmon.py` | `tests/unit/gem5/check_tiny_hmon.py` | Tiny，见 §7 |

- **不迁**：`tools/testcases/lib/{chipyard_engine,gem5_se_engine,build_test_binary,run_qemu_test}.py`
  被 ≥2 scope 复用，留 `tools/testcases/lib/`。
- `tools/testcases/arch/build_step5_bootrom.py`、`node_probe_prelude.py`、`gen_machine_inc.py`
  → `tests/arch/common/`（arch 专用构建）；`build_tiny_bootrom.py` → `tests/ee-tiny/`
  （Tiny 执行环境资产，不属 arch）。
- 迁移顺序：先 §6 签名（005），再 cfx4（ptw/tlb）→ cfx5（cache）→ 其余 cfx；
  **每步只搬文件 + 改路径，不改判据**；`check-arch`/`check-arch-smoke` 在迁移完成前保持现状。

## 6. 与 `m16-testcases-005` 的接口

- 签名机制唯一真源：汇编侧 `tests/shared/asm/signature.inc`、host 侧
  `tests/shared/signature.py`（`m16-testcases-005` 迁入）。
- arch **不复制解析器**：`tests/arch/common/signature.py` 只做薄壳——
  1. 重导出 `parse` / `compare` / `unwritten` / `Emitter` 等公共 API（真源 `tests/shared/signature.py`）；
  2. 固定 arch 的槽宽（8 字节）与 `0xdeadbeef` 未写哨兵；
  3. 把 `expected.yaml` 的 arch 字段（`signature:` 列表）映射成公共比较输入。
- 若 005 尚未落地，`run_arch.py` 必须**显式失败**（`ImportError` 带缺件路径），
  不内置第二份实现、不静默回退。

## 7. Tiny hmon 迁出 arch（方案，不执行）

现状冲突：`tests/arch.yaml` 的 `arch-hmon-001`（`tests/arch/hmon/tiny_hmon.S`）跑 gem5
**Tiny FS**，与 arch 只 Vast 冲突。

- **落点**：`tests/unit/gem5/tiny_hmon/`（用例、`.lds`、`expected.yaml`、README），
  driver `tests/unit/gem5/check_tiny_hmon.py`，QEMU 同契约探针
  `tests/unit/gem5/min_rom_probe_integ007t.py`。
- **索引**：从 `tests/arch.yaml` 删除 `arch-hmon-001`；在 `tests/unit.yaml` 增
  `unit-gem5-hmon-001`（`file: unit/gem5/tiny_hmon/tiny_hmon.S`、`kind: asm`、
  `machine: tiny`、`platforms: [system]`、`level: full`、`requires: [gem5-fs, toolchain]`）。
- **需同步改的文件**：
  1. `tests/arch.yaml`（删条目）、`tests/unit.yaml`（增条目）；
  2. `tests/arch/README.md`（删 `hmon/` 行与 `check_tiny_hmon` 门控行，改为「Tiny 已迁出」）；
  3. `tests/unit/README.md`（当前不存在：新建或在 `tests/unit/` 现有说明中补 gem5 Tiny 小节）；
  4. `tests/INVENTORY.md`（arch/unit 文件计数与目录说明）；
  5. `tests/case-ledger.tsv`（生成物，按 `check-case-ledger` 重新生成）；
  6. `docs/Process-07-门控分层规范.md` 的读方护栏清单（`tools/gem5/check_tiny_hmon`
     路径改为 `tests/unit/gem5/check_tiny_hmon.py`）；
  7. `tools/testcases/arch/build_tiny_bootrom.py` 的落点（建议 `tests/ee-tiny/`）与
     `Makefile` 的 `build-bootrom` 引用（只改路径，不改行为）。
- **不动**：`tests/ee-tiny/cfx_hmon_tiny.S`（Tiny BootROM 共享最小编码，属执行环境资产）；
  `docs/TestReports/M13-*`（历史报告，路径保持原样）。
- **门控影响**：`arch-hmon-001` 不在 `Makefile` 任何目标内（`check-arch*` 只跑 QEMU 探针），
  迁移**不改** L2/L3 集合；`check-tests-index` 需在改索引后复跑。

## 8. Process-09 修订（原文 → 新文）

> 本任务已按用户 2026-11-22 裁定**直接改正文**（`docs/Process-09-测试组织规范.md`）。
> 下表逐条给「原文 → 新文」，供复核与后续任务引用。
> 另在 §1 增一条 arch 范围注记（cfx 集合与「只 Vast」），消除 §1 仍列 UART 的歧义。
> 说明：任务书所称「§7 目录结构」在本册现行编号中对应 **§3「源码目录」**（§7 是「平台」）；
> 为避免重排全册编号，目录树改在 §3，另在 §7 增 `7.1` 记录 arch 的平台×目录对应。

### 8.1 §3 scope→目录映射

- 原文（§3 目录树 `arch/` 两行）：

  ```text
    arch/                     # cfx/权限
      umon/ jmon/ smon/ hmon/ ptw/ tlb/ cache/ hart/ llc/ pmem/ time/ uart/ power/
  ```

- 新文：

  ```text
    arch/                     # cfx/权限（只测 Kaiwu-Vast；范围 0/2/3/4/5/15/32/34/63）
      umon/ smon/ hmon/ ptw/ cache/ hart/ pmem/ time/ power/
                              # 每 cfx 一目录：用例、.lds、生成器、check_*.py、expected.yaml
      run_arch.py             # arch 驱动（--cfx / --platforms / --cache-model / --self-test）
      common/                 # arch 内共享薄壳（签名流等，转调 tests/shared/）
  ```

  并在 §3 末追加三条：

  ```text
  - **scope 专用脚本/数据随 scope**（2026-11-22，`m16-testcases-004`）：arch 的驱动
    `tests/arch/run_arch.py`、共享薄壳 `tests/arch/common/`、盘点/矩阵 `tests/arch/`
    都在 `tests/arch/` 内；`tools/testcases/arch/` 只保留跨 scope 共享部分，arch 专属探针
    按 `tests/arch/PLAN.md` 的迁移清单**待迁**（迁移完成前门控不变）。
  - `tests/arch/` 下的盘点/矩阵文件（如 `vast-arch-inventory.md`、`expected-divergences.yaml`）
    是 scope 内的入库数据，与 `tests/data/` 同性质：不被 `tests/arch.yaml` 当载体、不进 §5 的 case 清单。
  - `tests/arch` **只测 Kaiwu-Vast**；Tiny 的 hmon 用例移出 arch（`tests/unit/gem5/`，
    见 `tests/arch/PLAN.md`）。
  ```

### 8.2 §5 根级清单（驱动型 case + `machine` 字段）

- 原文（§5 示例块之后无驱动型说明；示例只有 `asm` 一种载体）：

  ```yaml
  # tests/inst.yaml
  - id: inst-01-load-store-001
    file: inst/01-load-store/ld.o_rrii_ra.S   # 载体 = 执行型 .S（唯一载体模型）
    platforms: [system]            # inst 必填；system = qemu-system 运行模式，不是机型
    level: full                    # smoke | full
    requires: []                   # 如 [user-mode]
  ```

- 新文（示例块后追加）：

  ```yaml
  # tests/arch.yaml（驱动型 case 与 `machine` 字段，2026-11-22）
  - id: arch-ptw-001
    file: arch/ptw/check_tlb.py    # 载体 = scope 内驱动（kind: driver）
    kind: driver                   # asm | driver；asm = .s/.S 执行向量
    machine: vast                  # arch 固定 Kaiwu-Vast（tiny/user 由其它 scope 负责）
    platforms: [system]            # 运行模式，不是机型；arch 只有 system
    level: full                    # smoke | full
    requires: [bootrom]
  ```

  并追加一条字段规则：

  ```text
  - **驱动型 case 与 `machine` 字段**（2026-11-22，`m16-testcases-004`）：`kind: asm|driver`
    （缺省 `asm`）；`driver` 的 `file` 指向 scope 内驱动（arch = `tests/arch/<cfx>/check_*.py`），
    由 `run_arch.py` 调起。`machine: vast` 固定机型；`platforms` 仍是 `system|user|hw`
    运行模式，不由机型推导。
  ```

### 8.3 §6 落点（scope 专用脚本随 scope）

- 原文（§6 开头 + `tools/testcases/arch/` 行）：

  ```text
  目标：**runner/driver/generator 全部收拢到 `tools/testcases/`**，`tests/` 只放用例与 `shared/`：
  ...
    arch/         # bootrom/min-ROM/CFX 场景（原 min_rom_probe）
  ```

- 新文：

  ```text
  目标：**跨 scope 共享的 runner/driver/generator 收拢到 `tools/testcases/`；scope 专用
  脚本随 scope**（`tests/<scope>/`）。`tools/` 只放跨 scope 共享，`tests/` 放用例、
  scope 专用驱动与 `shared/`：
  ...
    arch/         # 【待迁】arch 专属探针原址；迁往 tests/arch/<cfx>/（m16-testcases-004 清单）
  ```

  并在 §6 追加一条：

  ```text
  - **scope 专用脚本随 scope**（2026-11-22，`m16-testcases-004`）：只服务一个 scope 的
    驱动/生成器/判据放该 scope 内（arch → `tests/arch/<cfx>/`、`tests/arch/run_arch.py`、
    `tests/arch/common/`）；`tools/testcases/` 保留被 ≥2 scope 复用的 `lib/` 与跨 scope
    套件驱动。判据：**第二个 scope 也开始用**才上移 `tools/`。
  ```

### 8.4 §7 目录结构（arch）

- 原文（§7「平台」末条之后无目录说明）：

  ```text
  - 将来硬件在环：`platforms` 增 `hw`，不改用例 ID。
  ```

- 新文（其后追加 `7.1`；**不重排** §8 起的编号）：

  ````markdown
  ### 7.1 arch scope 的平台与目录（2026-11-22）

  arch 只测 Kaiwu-Vast（`system` 平台）；QEMU/gem5/chipyard 是同一 ELF 的三种承载，
  不是三个 scope。目录固定为：

  ```text
  tests/arch/
    <cfx>/        # 用例（.s/.S）、.lds、生成器、check_*.py、expected.yaml
    run_arch.py   # --cfx / --platforms / --cache-model / --self-test
    common/       # 签名等薄壳（转调 tests/shared/）
    vast-arch-inventory.md  # 盘点矩阵等入库数据
  ```

  - `tools/testcases/arch/` 的 arch 专属探针**待迁**到 `tests/arch/<cfx>/`
    （清单见 `tests/arch/PLAN.md`）；迁移完成前不改门控。
  ````

## 9. 实施分期（供后续任务）

1. **批次 1（本任务）**：盘点矩阵 + 本方案 + Process-09 正文。
2. **签名（005）**：`tests/shared/signature.py` + `signature.inc`；arch 薄壳。
3. **cfx4/cfx5 载体**：迁 `tools/chipyard/{ptw,tlb,dcache,icache}` 与 `min_rom_probe_tlb.py`；
   建 `tests/arch/run_arch.py`（先只支持 `--cfx 4/5`）。
4. **共享 cfx**：umon/smon/hmon/power（现有 QEMU 探针迁移），再 hart/pmem/time。
5. **索引与门控**：改 `tests/arch.yaml` 字段、`check-tests-index`、`case-ledger`；
   新增按需 `check-arch-vast`（**不进 L2/L3**，只在里程碑收口手工跑）。

## 10. 待裁定 / 遗留

- **`platforms` 语义**：`[system]` 与 `--platforms qemu,gem5,chipyard` 两套词汇并存；
  是否把承载（engine）提升为索引字段（`engines:`）待用户裁定。
- **gem5 载体缺口**：gem5 现无任何 Vast cfx 用例（Tiny hmon 除外），三方差分前需先建
  gem5 FS 最小载体（`m16-gem5-020` 之后）。
- **RTL 缺口**：cfx0/2/15/32/34 在 chipyard 完全缺；cfx5 只有阵列、无命令面
  （`m16-chipyard-016`）。
- **Task 010/011 边界**：`m16-chipyard-010` 的 I-Cache 与 `m16-chipyard-016` 的 cfx5
  命令面可能同文件冲突，实施时串行。
