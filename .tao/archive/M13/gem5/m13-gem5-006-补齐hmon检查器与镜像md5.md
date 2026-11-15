# m13-gem5-006: 补齐 gem5 hmon 检查器缺失文件 + 镜像 md5 常量

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-gem5-005`（装载契约，已合入）、`m12-chipyard-019`（hmon 段 56→120 B，已合入）
**可并行分片**：否（组件单写者）
**状态**：已验证

## 背景

`m13-gem5-005` 的完成区声明新增/修改了 4 个文件，但它们**从未进入任何 commit、磁盘上也不存在**（`m12-chipyard-019` 的 reviewer 实测：`git log --all` 无、磁盘无、合入 commit `611f9920` 的 `--stat` 不含）。

后果：`tools/gem5/check_tiny_hmon.py` 现在运行 `exit=2`（引用了不存在的 include），gem5 侧 hmon 门控失效。

同时 `m12-chipyard-019` 把 hmon 段从 **56 B 扩到 120 B**，BootROM 镜像 md5 由 `777b6bc9…` 变为 `33bfe14af0e47d9e6f9c2d4a34fc5ae0`；`m13-gem5-005` 的证据脚本里硬编码了旧值。

## 目标

1. **补齐 4 个文件**（按 `m13-gem5-005` 的设计重新导出，不得凭空造）：
   - `tests/arch/hmon/tiny_hmon_handler.S`
   - `tests/arch/hmon/tiny_hmon_handler.lds`
   - `tests/arch/hmon/tiny_hmon_layout.inc`
   - `tools/gem5/check_tiny_hmon.py`（使其与 `tests/arch/hmon/tiny_hmon.S` 的 include 匹配、可运行）
2. **更新镜像常量**：证据脚本与 checker 中的 `777b6bc9…` → `33bfe14a…`；若代码里有 `56 B`/`size=56` 之类的期望，改为 120 B（以实测为准，不写死猜测值）。
3. **保持 `tests/arch/hmon/expected.yaml`**：`m12-chipyard-019` 已把 `shared_bootrom_md5` 更新为新值 **且等于实测**，不要回退。
4. **可运行**：`python3 tools/gem5/check_tiny_hmon.py` rc=0，断言条数与记录数一致（现场统计）。

## 非范围

- 不改 gem5 引擎实现（`m13-gem5-005` 已定）
- 不改 chipyard/QEMU
- 不改 spec/契约

## 验收标准

1. 4 个文件存在且被 git 跟踪（`git ls-files` 可查），内容与 `tiny_hmon.S` 的 include/符号一致
2. `python3 tools/gem5/check_tiny_hmon.py` rc=0，输出记录数与断言数现场统计
3. `grep -rn '777b6bc9' tools/ tests/` 为 0（或仅历史注释，须说明）
4. `make check-modules` / `check-inst` / `check-unit` 零回归（外部红逐条核实）
5. 一键证据脚本（含可达 FAIL 注入：例如把镜像 md5 改回旧值 ⇒ 应 FAIL）
6. 完成区 ≤30 行、无运行期路径；**「修改文件」清单须与 `git show --stat` 逐项对账**

## 说明

- 必须在独立 `git worktree` 内作业（`ISS-368`）；不占用 207/208。
- 组件单写者；补丁走 `make_patch`。
- 若无法重建 `tiny_hmon_handler.S`（设计细节丢失），**停下报告**，由主会话决定回滚 `m13-gem5-005` 的相应部分。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；**「修改文件」必须与 `git status`/`git show --stat` 对账**。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审

逐行核对 3 个新增用例文件与 `tools/gem5/check_tiny_hmon.py`，并以真跑校验（checker、证据脚本 fast/`--inject`、L2/L3 门控）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 设计细节全部丢失，handler 内容靠猜会失真 | ✅已修 | 用 005 遗留的 handler 平铺段做**逐字节重建**基准；据此写回 `tiny_hmon_handler.S`（含 mailbox/PROBE/IALIGN 恢复） | 重建段与遗留段 md5 相同（`32f1d2b0…`，248 B），`cmp` 无差异 |
| `tiny_hmon_layout.inc` 常量若与链接脚本不符 ⇒ 数据区错位 | ✅已修 | 常量取自 005 handler ELF 的绝对符号（`DATA_BASE=ENTRY+0x3100` 等），并与应用 ELF 实际符号对账 | 证据脚本「layout RECORD_CHECK/RESULTS/SLOT_PTR == 应用符号/`.data`」三项 PASS |
| 旧 checker 按「ELF 自带 BootROM/hmon 段」建 ELF，新契约下不可运行 | ✅已修 | 重写为两件装载：共享 power+共享 hmon 打共享镜像、power+本 handler 打测试镜像；应用只装 SRAM | checker 210 断言全 PASS，guest exit `0x21` |
| 任务书要求「md5 常量 777b6bc9→33bfe14a」 | ✅已修（自决） | checker **不硬编码 md5**：真值取自 `expected.yaml:shared_bootrom_md5` 并与 chipyard 入库 hex 逐字节对账（单一真源，避免第二份常量漂移） | 证据脚本「tools/ 无 md5 常量、tests/ 仅 expected.yaml 一处」PASS；019 合入后自动取 `33bfe14a…`/120 B（已用 019 源实测） |
| 无 FAIL 路径的断言是假门控 | ✅已修 | 证据脚本内建 2 组注入（oracle md5 改错 / 固件 +8 B）与 5 条装载反例（缺 `--bootrom`、镜像非 64 KiB、PT_LOAD 落 BootROM/hmon、`e_entry` 非固定） | `--inject` 23/23；注入后 checker rc=1 且命中 `[FAIL] shared BootROM md5`，还原后 md5 相等并回绿 |
| 交付文件是否与 `git status` 对账（上次丢文件根因） | ✅已修 | 完成后逐项对账 | `git status --porcelain -uall` = 3 新增 + 1 修改 + 任务书自身，无其它改动 |
| `tiny_hmon.lds` 仍是旧三 PHDRS 声明（005 的 lds 改动同样丢失） | ⏸延后 | 未改（不在本任务文件清单） | 实测 lld 丢弃空段，应用 ELF 仅 1 个 SRAM `PT_LOAD`，checker PASS；记为遗留 |

### 第 1 轮 reviewer 验收

**重跑记录（全部为我自己的输出，workdir = 该 worktree 仓库根）**
- `python3 tools/gem5/check_tiny_hmon.py` ⇒ **rc=0**，`check_tiny_hmon: PASS (210 checks, 44 records)`；现场统计 `grep -c '^  \[PASS\]'`=**210**、`[FAIL]`=**0**
- `bash 运行期证据目录下的 `run.sh`` ⇒ rc=0，`evidence: PASS=18 FAIL=0`；`--inject` ⇒ rc=0，`PASS=23 FAIL=0`（oracle md5 注入 rc=1 且命中 `[FAIL] shared BootROM md5`；固件 +8B 注入 rc=1；`cp`+md5 还原 `344c50ad…`/`fdbfebb2…` 相等后回绿）
- **反造比对**：我重建 handler → `md5=32f1d2b0b67f4f18263e7c634a543b49`、248 B、`cmp` 与 ``m13-gem5-005` 运行期遗留的 handler 段` **无差异**（该遗留文件 mtime 11-10 23:42，早于本任务）
- **我的独立注入**（各 `cp` 备份 + md5 还原，末态 `md5sum -c` 全 OK、`git status --porcelain -uall` 0 行）：① layout `DATA_BASE +0x3108` ⇒ checker rc=1（`semihosting…missing`、`result table…missing`）；② oracle id7 期望值 +1 ⇒ rc=1（`record 7 check 7 value` FAIL，2/210）；③ handler lds `ORIGIN +8` ⇒ rc=2（builder 报 `e_entry … != 0xfff00000000`）；④ 同①注入后**重跑同一 run.sh** ⇒ rc=1，`PASS=12 FAIL=6`（含 `layout SLOT_PTR == app .data` FAIL）
- **lds 8 KiB 断言可达**：handler 追加 `.space 9000` ⇒ `ld.lld` **rc=1** `tiny hmon dispatch segment exceeds its 8 KiB budget`（还原后 md5 `8e1751fd…` 与快照相等）
- **门控**：`check-modules` rc=0、`check-inst` rc=0（Vast 980/985+5 deferred、Tiny 44/44，与完成区一致）、`check-unit` rc=0、`check-tests-index`/`check-test-reports` rc=0；L1 `make check` **rc=2 仅停 `check-patch-tree`**（7 条全 chipyard：共享 chipyard 源树 3 个 scala 文件脏，mtime 04:38）；另跑 `check-knowledge-refs`(4)/`check-run-artifacts`(3)/`check-temp-dirs`(5) 红项，**逐条查无 m13-gem5-006 命中**（属 integ-004/testcases-004/night 日志等）
- **019 合入态**：临时树（master `42ffef5b` + 本任务 4 文件）跑同一 checker ⇒ **rc=0，`PASS (210 checks, 44 records)`**，`shared BootROM md5 expected=actual=33bfe14af0e47d9e6f9c2d4a34fc5ae0`、`hmon segment = 120 B`；`grep -nE '[0-9a-f]{32}' tools/gem5/check_tiny_hmon.py` 无命中 ⇒ **无第二份硬编码常量**

**约束核验**：4 文件在 HEAD `77b24b25` 内被跟踪、`tiny_hmon.S` 三个 include 全解析；两件装载均验（共享镜像 == chipyard hex 逐字节 + 测试镜像装 SRAM dump 逐字节），5 条装载反例各 rc+message 共 10 断言全具名；完成区 16 行 ≤30、无运行期路径，`git show --stat` 5 项与完成区对账一致；我未 commit、未动共享软链，结束快照 md5 逐项 OK、status 0 行。

**findings（不阻断，交 architect 收尾改）**：① 完成区「hmon SRAM 全 8192 B」为数字笔误（实测：固件段 248 B、尾零 65288 B、dump 65536 B）；② 验收 3 字面 grep 余 1 处 `expected.yaml:31`（该分支基线的**活值**非注释，engineer 已在遗留问题披露，019 合入后由其行接管）；③ chipyard 脏归属完成区写「并行 019」，019 已 04:18 合入而脏文件 mtime 04:38，更可能属并行 008（本任务 diff 不含 chipyard 文件）。

**判决：Accepted**（验收命令块在 reviewer 重跑下全过、硬约束无违反）

## 完成区

**测试结果**：`check_tiny_hmon` PASS（**210 断言 / 44 记录**，rc=0）；证据脚本 fast **18/18**、`--inject` **23/23**；门控 `check-modules` rc=0、`check-inst` rc=0（Vast 980/985+5 deferred、Tiny 44/44）、`check-unit` rc=0。
**修改文件**：新增 `tests/arch/hmon/tiny_hmon_handler.S`、`tests/arch/hmon/tiny_hmon_handler.lds`、`tests/arch/hmon/tiny_hmon_layout.inc`；改 `tools/gem5/check_tiny_hmon.py`。**对账**：`git status --porcelain -uall` = 这 4 项（`??`×3 + ` M`×1）**+ 本任务书自身**（` M`，仅状态/完成区），无其它改动。
**验收结果**：
- 3 个新增文件：handler 段 248 B、入口 = hmon SRAM 起始、≤ 8 KiB；重建段与 `m13-gem5-005` 遗留平铺段**逐字节一致**（md5 `32f1d2b0b67f4f18263e7c634a543b49`）。
- `check_tiny_hmon`：共享镜像 65536 B、表头 `DBOT/1/1/0x30001`、表项 `type=1 flags=0x3 offset=0x2000`；共享镜像 == chipyard 入库 hex（逐字节）；hmon SRAM 全 8192 B 与固件段逐字节相同、其余全 0；guest exit `0x21`、控制台 `hmon-ok`、停止原因 `semi:ADP_Stopped_ApplicationExit`；44 条记录（含移交帧、cg 寄存器、五类异常×3、`trap`/`escape`/CFXPERM/CFXREG、Tiny 恒 hypv）与 `expected.yaml` 逐条相符。
- 装载反例 5 条（缺 `--bootrom`、镜像非 64 KiB、PT_LOAD 落 BootROM/hmon、`e_entry` 非固定）各 rc=1 且报错具名。
- 注入：oracle md5 改错 ⇒ `FAIL (1/210) shared BootROM md5`；固件 +8 B ⇒ 同一断言 FAIL；两次均 `cp`+md5 还原（`expected.yaml` `344c50ad…`、`hmon.S` `fdbfebb2…`）后回绿。
- 镜像常量：checker 无硬编码 md5；当前基线（`m12-chipyard-019` **未合入**）实测共享镜像 md5 `777b6bc9ba66c19783fb7f0a487249fd`、hmon 段 56 B，与 `expected.yaml`、chipyard hex 三方一致；用 019 源实测为 `33bfe14af0e47d9e6f9c2d4a34fc5ae0`、120 B，checker 同一份代码 **PASS（210/44）**，无需改动。
**新发现/坑**：① 任务书前提「019 已合入」与事实不符（019 仍为 WIP 分支），故 md5/尺寸不能写死为 120 B 值，改为从 `expected.yaml` + chipyard hex 派生（合入后自动生效，避免二次漂移）；② 上次丢文件根因是收尾未做 `git status` 对账（`ISS-377`），本次逐项对账；③ gem5 以 `cwd=outdir` 运行，所有文件参数须 resolve；④ 005 留下的 handler 平铺段是最好的重建基准（逐字节反推比读设计描述可靠）。
**遗留问题**：
- 任务书验收 3「`grep -rn '777b6bc9' tools/ tests/` 为 0」：`tools/` 已 0；`tests/` 仅剩 `expected.yaml:shared_bootrom_md5` 一处（`m12-chipyard-019` 未合入，该行归其更新为 `33bfe14a…`）。**待裁定**：是否按 019 分支基线重做本任务，或等 019 合入后由本 checker 自动生效（当前实现两者皆绿，无需改代码）。
- `tests/arch/hmon/tiny_hmon.lds` 仍是旧三 PHDRS 声明 + 过时注释（005 的 lds 改动同样未入库）；实测只产生 1 个 SRAM `PT_LOAD`，不影响验收，建议随后续任务清理。
- 门控外部红（均非本任务改动）：`check-patch-tree` 7 条全 chipyard（并行 019 的源树不干净）；`check-run-artifacts` 3 条非法名、`check-knowledge-refs` 4 条 `.work` 引用、`check-temp-dirs` 5 个陈旧目录，均来自其它任务。

#### 收尾（architect，2026-11-11 04:52）

- reviewer **Accepted**：4 文件真补齐（重建 handler md5 `32f1d2b0…` 与 ``m13-gem5-005` 运行期证据目录` 遗留段 `cmp` 无差异 ⇒ 非现造）；3 个 include 全部解析。
- `check_tiny_hmon` rc=0 `PASS (210 checks, 44 records)`；md5 **动态派生**（checker 内无硬编码 32 位 hex），与 chipyard 入库 hex 逐字节对账。
- **019 合入后仍 PASS**：临时树（master `42ffef5b`）实测 `33bfe14a…`、hmon 段 120 B、210/44 全绿 ⇒ 无需改代码。
- reviewer 4 次独立注入 + 8 KiB 预算断言（追加 `.space 9000` ⇒ `ld.lld` 超限失败）均可达 FAIL。
- 门控：`check-modules`/`check-inst`/`check-unit`/`check-tests-index`/`check-test-reports` rc=0；L1 仅 patch-tree（chipyard 脏，属并行 008）。
- 文档级（转 `ISS-378`）：完成区「8192 B」笔误、验收 3 的 grep 余 1 处活值、chipyard 脏归属写错（应为 008 非 019）。
