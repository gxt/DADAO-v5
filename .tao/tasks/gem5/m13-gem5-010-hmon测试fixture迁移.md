# m13-gem5-010: gem5 的 hmon 测试 fixture 迁到最小 handler

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-integ-007`（新 hmon 已合入，共享镜像 md5 `514300876…`）
**可并行分片**：否
**状态**：已验证

## 背景

`m13-integ-007` 把 hmon 改成「最小保存-跳转」（11 条 / 44 B，代码 `0x00`、数据 `0xD8–0xFF`），共享镜像已更新，QEMU 在用。

但 **gem5 的测试分派 fixture 仍是旧版**：

- `tests/arch/hmon/tiny_hmon_handler.S` / `.lds`：**旧 18 条 / 248 B**，仍记录 frame、重写 IALIGN/+4
- 因此 `tests/arch/hmon/expected.yaml` 的 records 0 / 17–31 仍按旧 fixture 推导
- `expected.yaml` 的 `pending_followups` 已列此条，但一直没派单

## 目标

1. 把 `tests/arch/hmon/{tiny_hmon.S,tiny_hmon_handler.S,tiny_hmon_min.S}` 统一到**最小 handler**（与 `tests/shared/bootrom/tiny/hmon.S` 同一算法）
2. `expected.yaml` 的 cause 记录改为读 hmon SRAM `0xE0/0xE8/0xF0/0xF8`（code@0x00、data@0xD8），**重派生** records 0/17–31
3. 删除 `require_layout=False` 之类的旧布局 opt-out
4. 更新 `tests/arch/hmon/README.md` 说明

## 验收

1. `check_tiny_hmon` 全绿，且 **不再有 `[PENDING]` 行**
2. hmon 段长度 44 B（表项对齐 48 B）、数据区不在镜像段内
3. 五类异常（CFXMEM/ILLI/UNDI/MALIGN/IALIGN）的 cause_id/ip/info 与 QEMU 探针逐值一致
4. `expected.yaml` 的 `pending_followups` 清空或只剩 chipyard 那条
5. 完成区 ≤30 行；「修改文件」与 `git status` 对账

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），动手前 `git rev-parse --show-toplevel` 自证；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir，用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`tiny_hmon.S`（槽记录 + `LOAD_ABS`）、`expected.yaml`（cause 记录改 `return_slot`、删 check 37）、`check_tiny_hmon.py`（单一共享镜像 + 槽断言 + 去 chipyard PENDING）、`build_tiny_bootrom.py`（删 `require_layout`/`--allow-legacy-hmon`）、两份 README。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `LOAD_ADDR` 不能取段内标签（forward label 汇编期报错） | ✅已修 | 新增 `LOAD_ABS`（R_DADAO_ABS48），landing/`record_cause` 改用它 | 汇编+链接 OK；205 checks PASS |
| 旧 fixture 的 in-handler cg3 探针（check 37）在最小 handler 下无载体 | ✅已修（删除并记录理由） | 应用去掉 PROBE 写入/读取；`expected.yaml` 删 check 37；两 README 注明该钩子随 dispatch fixture 删除 | 记录数 43（由 oracle 现场统计）；36/42/38–40 语义不变 |
| chipyard hex 身份检查与「输出无 `[PENDING]`」验收冲突 | ✅已修（移出 gem5 门控） | 删 `chipyard_image()`/`CHIPYARD_HEX`/PENDING 分支；chipyard 跟随仍由 `pending_followups` + m12-chipyard-028 跟踪 | checker PENDING 行数 0；证据脚本静态断言 |
| 旧「hmon SRAM tail is zero」在新布局下必假（数据槽运行时被写） | ✅已修 | 改为 code==固件 / 48B padding / 0xD8 前空隙为 0 / 数据槽==最后一次异常 / 0x100 以上为 0 | 5 项逐项 PASS（`.work/log/gem5/check-tiny-hmon.log`） |
| 单元素 `for ... in ((...),)` 循环非惯用 | ✅已修 | 去循环，直接单镜像检查 | checker 仍 205 PASS |
| 数据槽 0xE0/0xE8/0xF0/0xF8 硬编码 | ✅已修 | 改用 `bld.HMON_SLOT_*` 常量 | 同上 |

判决：全部 finding 已修，标「待验收」。

### 第 1 轮 reviewer 验收

**重跑（本 worktree 亲跑，输出/退出码均为实测）**
- `bash` 该任务的运行期证据脚本 ⇒ rc=0 `PASS (18 checks)`；`--inject` ⇒ rc=0 `PASS (25 checks)`（注入段 `FAIL (82/201)`、records 43→42、还原 md5 `e00ef5c4…` 回绿）
- `check_tiny_hmon` ⇒ rc=0 `PASS (205 checks, 43 records)`，`[FAIL]`=0、`[PENDING]`=0（另直跑 2 次同值）
- `make check-tests-index` ⇒ rc=0（263 条）；`make check-case-ledger` ⇒ rc=0（2170 条）
- `build_tiny_bootrom.py --self-test --out-dir/--power-elf/--hmon-elf/--llvm-*` ⇒ rc=0 `self-test: PASS`（4 项反例注入全被拒）
- QEMU `min_rom_probe_integ007t` ⇒ rc=0 `PASS (64 checks)`；五类 id/info 与 gem5 逐值全等，IALIGN 两边 `info==ip`
- 独立注入：`expected.yaml` 中 `f_hypv` 的 `return_slot: land_hypv`→`land_trap` ⇒ rc=1 `FAIL (2/205)`（`SRAM data slots (last fault)` 与 `record 39 return_slot` 同红）；`cp`+md5+`touch` 还原 ⇒ md5 `3da30455…` 相等、回绿 rc=0
- 10 文件对账：`git diff --name-status 34da4549..HEAD` = 8 M + 2 D + 任务书，与完成区逐项一致；HEAD 仍 `05a1ce6a`、`git status -uall` 干净、reviewer 未提交

**期望值独立派生抽查（按 spec+ELF 自算，未读 gem5 结果）**
- rec0：`id=0x1`、`ip=boot_magic_trap=0xffffffff013c`、`info` 我现汇 `trap cfx_hmon,0x30001`=`0x7f0f0001`、`ret=trap+4`（power.S `rb2rd/+16→0xF8`）——四项全对上
- rec18 CFXMEM `0x2/0xffffff01031c/0x1000000000/0xffffff010320`、rec30 IALIGN `0x2000/ip==info==0xffffff011d01/0xffffff0104d0` = 我自建 ELF 的 `llvm-nm` 符号值
- 布局实测 dump：code 44 B、`0x2C–0xD7` 全 0、`0xD8–0xFF`=`0/0x2/0xffffff0105f8/0xfff00010000/0xffffff0105fc`（=最后一次 f_hypv）、`0x100+` 全 0
- `cause_id` 位索引与 `info` 语义对 `spec/Machine-v5 §4.4`、`DADAO-12 §5.1`、`DADAO-13 §2` 逐条复核一致

**L1 相关项**：`make check` rc=2 卡 `check-patch-tree`（chipyard 源树被并发任务 `m12-chipyard-027` 写，有据重试 1 次仍红 ⇒ 环境/并发）；另逐项跑 46 项 ⇒ 40 绿 / 6 红：`check-components`/`check-musl-freshness`/`check-width-sizes` 因本 worktree 无 `.dadao`（主工作树重跑均 rc=0），余 3 项见 findings。

**约束核验**：硬约束 1–8 逐条核——独立 worktree、未提交、完成区与真实输出对账、越界（`tests/arch/README.md`）已在文件清单披露、一键证据脚本、无 `reset`/`checkout` 还原，均无违反；完成区 12 行（≤30）、本轮审阅记录 ≤40 行。

**Findings（不阻断，收尾处置）**
1. 任务书 56/71 行含具体 `.work/**` 路径 ⇒ `check-knowledge-refs` 计 3 条新违规（基线已有 1 条）；按 AGENTS 改「运行期…」措辞或 `<>` 占位。
2. `run.sh:119` 产出的日志名（非 `check-*.log`/`<任务号>-*.log`）⇒ `check-run-artifacts` 判非法名（该门控基线已因他任务红）；改名并删旧文件。
3. `milestones-m13` 中本任务行仍在「待开始」⇒ `check-milestones-fresh` A1+R1 红；主会话移入「进行中」补派单时间（reviewer 不改台账）。
4. `m13-testcases-012` 完成区仍指「`check_tiny_hmon [PENDING]`」，该机制已随本任务删除 ⇒ 指针过期（文档级）。

**三个专项答复**：① 期望值独立派生**成立**（符号 + spec 表达式，非 gem5 反填）；删 check 37 **可接受**（已披露于审阅记录/`expected.yaml`/README；共享 handler 无测试钩子，原语义由 handler 自身 hypv-only `cg5` 读 + 36/38–40/42 承接）。② chipyard PENDING 删除**非静默降级**（4 处披露 + ISS-410 open + `m12-chipyard-028` 在「待开始」+ 任务验收第 4 条本就预期；且原检查恒 `report(True)` 本就不报红），但现仅文档级跟踪、无门控会对 chipyard hex 不一致报红。③ `require_layout`/`--allow-legacy-hmon` 移除**彻底**（`git grep` 代码侧零残留，仅任务书历史描述提及），`--self-test` rc=0。

**判决：Accepted**

## 完成区

**测试结果**：`check_tiny_hmon` PASS（205 checks / 43 records，0 个 `[PENDING]`、0 个 `[FAIL]`）；QEMU 探针 `min_rom_probe_integ007t` PASS（64 checks）；`build_tiny_bootrom.py --self-test` PASS；`check-tests-index` 263 条 PASS、`check-case-ledger` 2170 条 PASS；证据脚本正常模式 18 项 PASS、`--inject` 25 项 PASS。
**修改文件**（与 `git status -uall` 逐项一致）：`tests/arch/hmon/{tiny_hmon.S,tiny_hmon_layout.inc,expected.yaml,README.md}`、`tests/arch/README.md`、`tools/gem5/check_tiny_hmon.py`、`tools/testcases/arch/build_tiny_bootrom.py`；删除 `tests/arch/hmon/tiny_hmon_handler.{S,lds}`；本任务书。`tiny_hmon_min.S` 未改（本就是最小 handler 的 QEMU 应用）。
**验收结果**：
1. hmon 段 code 44 B、表项 48 B（8 对齐）、停于 0xD8 数据基址之下；SRAM 0x00–0x2B 与固件逐字节相同、0x2C–0xD7 为 0、0xD8–0xFF 为运行时数据槽、0x100 以上为 0。
2. 五类异常 vs QEMU：`cause_id` 全等（0x2/0x100/0x200/0x1000/0x2000）；常量 `info` 全等（CFXMEM `0x1000000000`、ILLI `0x7f1c0000`、UNDI `0x08040001`、MALIGN `0xffffff000001`）；IALIGN 两边 `info == ip`（gem5 `0xffffff011d01`、QEMU `0xffffff011e01`，各为本应用 ELF 的非法 IP 目标，属布局差异非语义差异；两类 fault IP 同样由各自 ELF 符号派生）。
3. `pending_followups` 只剩 1 条：`chipyard: bootrom.tiny.hex == new shared_bootrom_md5`。
4. 注入（`LOAD_ABS rb5, land_mem0` 后插 `add.si rb5, 4`）⇒ checker rc=1（`FAIL (82/201)`，record count 43→42）；`cp`+md5+`touch` 还原 ⇒ md5 相同、回绿 `PASS (205 checks, 43 records)`。
5. 一键证据：该任务的运行期证据目录（日志落该模块运行期日志目录）；本 worktree 无 `.dadao`，故以显式 `--toolchain-bin` 直调 checker/探针与 builder `--self-test`（`make build-bootrom` 在此 worktree 报 llvm-mc 缺失，属环境路径非代码问题）。
**新发现/坑**：① 最小 handler 无 mailbox，handover 证据只能来自 hmon 数据槽（0xE8 保存的 IP 不被 handler 覆盖，0xF8 是框架返回地址）；② 数据槽运行时非零 ⇒ 旧「SRAM tail 全零」断言必须改为按槽断言；③ `LOAD_ADDR` 只接受可绝对化的常量表达式，段内标签须用 R_DADAO_ABS48（`LOAD_ABS`）。
**遗留问题**：chipyard `bootrom.tiny.hex` 仍是旧固件（m12-chipyard-028），已不在 gem5 门控内；gem5 侧无遗留。

#### 收尾（architect，2026-11-13 09:34）

- reviewer **Accepted**：`run.sh` 18 checks rc=0、`--inject` 25 checks rc=0；`check_tiny_hmon` **205 checks / 43 records**、0 `[FAIL]`、0 `[PENDING]`；QEMU 探针 64 checks；builder `--self-test` PASS。
- **期望值独立派生复核通过**：rec0 / rec18 / rec30 由 spec + ELF 符号现推，与 `expected.yaml` 逐值相等；`info` 语义对 `Machine-v5 §4.4`、`DADAO-13 §2` 复核一致。
- **删 check 37 可接受**：旧 dispatch fixture 专属 in-handler cg3 钩子，最小 handler 无钩子（加钩子会破坏「三平台同一镜像」）；任务书、`expected.yaml` 注释、hmon README 三处已披露，handler 入口的 hypv-only `cg5` 检查仍在。
- **删 chipyard PENDING 不是门控降级**：原实现是 `report(True, …)`，**从不报红**，只是可见性提示；现由 `pending_followups`（run.sh 静态断言只剩 chipyard 一条）+ `m12-chipyard-028` + `ISS-410` 承接。**注意**：目前没有门控对 chipyard hex 不一致报红，`m12-chipyard-028` 派单前不得当已闭合。
- **`require_layout`/`--allow-legacy-hmon` 移除彻底**：`tools/ tests/ Makefile/ components/ spec/ docs/` 零残留（只在两份任务书的历史描述里出现）；`0xD8` 布局契约无条件强制。
- 布局实测：code 44 B / 表项 48 B / `0x2C–0xD7` 全 0 / 数据槽 `0xD8–0xFF` = 最后一次 `f_hypv` / `0x100+` 全 0。
- 收尾处置 F1–F3：完成区与审阅记录里的具体运行期路径改占位措辞；证据脚本日志名改为 `<任务号>-…` 口径（`check-run-artifacts` 回绿）；台账行移入「已验证」。
- F4（`m13-testcases-012` 完成区仍指 `check_tiny_hmon [PENDING]`）属历史记录，按「不改写既有完成区」保留；机制已删，读者以本任务为准。
\n