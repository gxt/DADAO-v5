# m13-qemu-012: `ra0` 写口丢弃 SBZ `[63:54]`（`ISS-426`，QEMU）

**模块**：qemu
**项目里程碑**：M13
**依赖**：`m13-testcases-031`（已合入：链例点 20 用 `ld.o ra0` 写入 `0xFFFF000000000000`、期望读回 `0x003F000000000000`）
**可并行分片**：否（QEMU 组件单写者）
**预估**：1–2 h
**状态**：已验证

## 背景（`ISS-426`，实测）

- `spec/SimRISC-00 §2.4`：`ra0 = {SBZ(10), RACNT(6), MRPTR(48)}`，`[63:54]` **写无效**（读回恒 0）；`ra2rd`/`rd2ra` 为全 64 位块赋值。
- chipyard `WumingRegFile.writeRa` 合规（`racnt := data(53,48); mrptr := data(47,0)`）。
- QEMU：`helper.c` 的 `helper_ra_store` 直接 `env->ra[phys] = val;` ⇒ 写入位被保留并读回。
- 现场：`m13-testcases-031` 的 `ld.o_rrii_ra` 链例点 20 —— chipyard 退出 0、**QEMU 退出 20**。

## 目标

1. QEMU 的 **RA 写口**（`helper_ra_store` 及其调用者）对 `[63:54]` 置 0：写入值按 `val & 0x003F_FFFF_FFFF_FFFF` 落 `RACNT[53:48]` / `MRPTR[47:0]`。
2. 不影响 RAS 操作的**头更新**路径（那里已有 `kRasSbzMask` 语义）：`call`/`ret`/`escape` 的 RACNT/MRPTR 更新必须与改前逐字节一致。
3. 不改 `spec/`、契约；不改 chipyard/gem5。

## 验收

1. 点 20 转绿：`run_asm_suite.py --vectors tests/inst/01-load-store` 在节点（`server207`）三平台 **235/235**（故障例 197 全绿、链例 38 全绿）。
2. 改前/改后对照：同一探针在**改前二进制**上仍红（钉值），改后绿。
3. RAS 回归：`05-arith-addr`、`06-control-flow` 两册三平台仍全绿（`call`/`ret` 的 RACNT/MRPTR 逐字节不变）。
4. 门控：`check-inst` 红集不变（除既有 `divrem.yaml[23]`）、`check_qemu_trans` 264/264、`check_patch_tree` qemu 段 0 问题、`--source-state` qemu OK、`check-component-changelog` rc=0、安装根 == 构建树。
5. ≥2 路注入可达 FAIL + `cp`+md5 还原（例：掩码改成 `0x007F...`（多留 1 位）⇒ 点 20 红；去掉掩码 ⇒ 回到缺陷）。
6. 完成后 `ISS-426` 在完成区标注「QEMU 侧已修，gem5 侧归 `m13-gem5-014`」。
7. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前 `git rev-parse --show-toplevel` 自证；禁改主工作树。
2. 不提交 git；补丁用 `make_patch.py qemu` 导出。
3. 完成区与真实输出逐条对齐；计数现场统计；日志 `.work/log/qemu/<任务ID>-<用途>.log`。
4. 只动任务书范围；越界须披露。
5. 禁 `git checkout/restore/stash`/`git show <commit>:<path>`；注入还原用 `cp`+md5。
6. **`install-host` 串行**：开工前确认没有别的会话在 `build-qemu`/`install-host`（LLVM 写者可能在跑）。
7. 大文件落 `/tmp/opencode/m13-qemu-012/` 并测完即删。

## 待裁定

1. **gem5 同一缺陷未修（跨模块）**：验收 #1「三平台 235/235」在 gem5 修好前不可达；本任务交付 = chipyard 235/235 + QEMU 235/235 + gem5 234/235（唯一红 = `ld.o_rrii_ra` 链例点 20，脚本钉住不放宽）。gem5 侧归 `m13-gem5-014`（尚未立册）。是否按此接受，请裁定。
2. ~~安装根一致性补测窗口~~ **已闭环（2026-11-14 06:37–06:39 串行窗口）**：`make install-host JOBS=32` rc=0 / 143 s，五件工具 `md5(构建树)==md5(安装根)` 全等；窗口内 `check-inst` rc=2、红集恰 `divrem.yaml[23]`。实测值已写入完成区 #6。

## 完成区

**测试结果**：一键证据脚本（运行期证据目录）`run.sh --no-install`（完整：节点三平台 + 双注入 + 门控；`--no-install` 因共享安装根串行，安装根一致性另行窗口实测见 #6）→ **PASS=56 FAIL=0 / rc=0**；`run.sh --no-install --no-node --no-inject` → **PASS=34 FAIL=0 / rc=0**。逐项真实输出见同目录 `log/` 与 `run-all.log`。
**修改文件**：`components/qemu/patches/target/dadao/helper.c.patch`（`make_patch.py qemu`：1 written / 65 unchanged）、`components/qemu/changelog.md`（M13 一条）、本任务书；与 `git status --porcelain -uall` 三条逐条一致。组件源树收敛为 base+1 单提交、clean（不入本仓库）。
**验收结果**：
1. **改动点**：`helper_ra_store()`（`target/dadao/helper.c`）对逻辑 0（`ra0`）的写入按 `RA0_WRITE_MASK = 0x003FFFFFFFFFFFFF` 掩码 ⇒ 只落 `RACNT[53:48]`/`MRPTR[47:0]`，`[63:54]` 丢弃（`spec/SimRISC-00 §2.4`）；`ra1`–`ra63` 不掩码（其 `[63:48]` 是 16 位递归计数）。对改前源码 `diff -u` = **1 个 hunk、0 行删除/修改、10 行新增** ⇒ RAS 头更新路径逐字节不变。
2. **点 20 改前/改后**：改前二进制（md5 `a4ec042d…`）跑同册仅 1 条红 = `ld.o_rrii_ra` 链例 **rc=20**；改后（`1037740c…`）该例 rc=0，点 20/21/22 字节 = `003f000000000000`/`0000000001234568`/`002aa5a55a5a1230`，RAS 读回点 16/17/19 = `0001000000000000`/`0002000000000000`/`0000ffffff014080`。
3. **三平台（server207）**：`01-load-store` chipyard **235/235**、QEMU **235/235**（链例 38 + 故障例 197）；gem5 **234/235**，唯一红 = `ld.o_rrii_ra` 链例 rc=20（pin 的跨模块缺口）。`05-arith-addr` 12/12、`06-control-flow` 34/34，三平台全绿。
4. **门控**：`check-inst` rc=2、红集恰 `divrem.yaml[23]`（1141 total / 1135 passed / 1 failed / 5 deferred）；`check_qemu_trans` 264/264；`check-patch-tree` qemu 段 0 问题；`--source-state` qemu **OK**（base+1、clean）；`check-component-changelog` rc=0。
5. **注入（2 路）**：A 掩码多留 1 位（`0x007F…`）⇒ 点 20 红（rc=20）；B 去掉掩码（`0xFFFF…`）⇒ 点 20 红。均 `cp`+md5 还原 ⇒ 重建二进制 md5 回 `1037740c…`、探针回绿、组件源树 clean（未用 git 还原）。
6. **安装根一致性**：本任务串行窗口内实测 `make install-host JOBS=32` **rc=0 / 143 s**（`06:37:12→06:39:35`），五件 `md5(构建树)==md5(安装根)` 全等（`qemu 1037740c…`、`clang c4f9247e…`、`llc ee60b612…`、`llvm-mc fec66e82…`、`ld.lld 53f9c071…`）；窗口内 `check-inst` **rc=2 / 21 s**、红集恰 `divrem.yaml[23]`。此后 `m14-llvm-006` 的注入窗口把注入版 QEMU（`7f51c6f4…`）装进安装根，**主会话已串行恢复**（07:14:25 完成，rc=0）：恢复后实测 `qemu-system-dadao 1037740c…` == 构建树；LLVM 四件随 `m14-llvm-006` 合入变为 `clang 5534ae0c…`、`llc c143cbc5…`、`llvm-mc c111b5b5…`、`ld.lld 45990808…`，亦逐件等于构建树。
7. **`ISS-426`**：**QEMU 侧已修**；gem5 侧（同一缺陷）归 `m13-gem5-014`（尚未立册）。
**新发现/坑**：① 证据脚本的「改前基线」**不得取自 HEAD/工作树**——任务产物一旦提交，基线就与被测物同源而恒假红；须冻结基线件并钉 md5（本轮 reviewer 抓到的阻断）；② 节点工具链与其它会话共享，`llvm-mc` 被并行 `install-host` 替换时镜像 build 报 `Text file busy` ⇒ 证据脚本对 build 失败自动重试 1 次并打印次数（本轮 0 次）；③ `run_asm_suite` 的 fault 记录 `expected` 存的是故障**名字**、不是退出码 ⇒ 统计每平台通过数须查 runner 的 `FAULT_CODE`；④ 同一 `.S` 有多条记录（chain + N×fault），按 `file` 建字典会取到最后一条 fault ⇒ 必须按 `kind` 过滤；⑤ 证据脚本运行中不可编辑（bash 增量解析 ⇒ 语法错乱）。
**遗留问题**：仅「待裁定」1（gem5 跨模块缺口，归 `m13-gem5-014`）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`helper_ra_store()` 改动（10 行新增）、导出补丁 hunk、changelog 条目、`run.sh`/`node-run.sh` 全脚本。

- **写语义**：仅逻辑 0 掩码——`ra1`–`ra63` 的 `[63:48]` 是 16 位递归计数，掩码会破坏 `C2`/`D2` 递归折叠；点 16–19 读回与 `06-control-flow` 的 `call`/`ret` 三平台全绿即反证。
- **写路径覆盖**：`grep -rn 'env->ra\['` 现场核对，只剩 `helper.c` 的 RAS 头更新与 `helper_ra_store`；指令侧全部经 `store_ra()`→`helper_ra_store`（`ld.o`/`ldm.o`/`rd2ra`）；`ra2rd` 只读。
- **边界**：`logical_idx` 越界由 ILLI 前置检查挡（`raha+immu6>64`）；掩码不改 `ra_phys` 计算。
- **防造假**：逐条有可达 FAIL 路径；两路注入走不同失败路径（多留 1 位 / 去掉掩码）；还原用 `cp`+md5+`touch`；计数（235/38/197/264）现场派生、不写死。
- **自审发现（均已处置）**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `{file: rec}` 字典取到 fault 记录（rc=241）⇒ 钉值断言假红 | ✅已修 | 按 `kind=="chain"` 过滤（改前对照与注入两处） | 改前 rc=20；注入 A/B rc=20 |
| F2 `grep -c RA0_WRITE_MASK` 把定义+使用算成 2 | ✅已修 | 改判 `^#define RA0_WRITE_MASK` | 断言 1 |
| F3 「RAS 未改」断言把自注释里的 `RACNT` 计入 | ✅已修 | 收窄为 `ras_push|ras_pop|ras_base|ras_tmp`，配合「0 行删除/修改」 | 0/0 |
| F4 `node-run.sh` heredoc 缺 `PY` 终结行；且边跑边改脚本导致 bash 解析错乱 | ✅已修 | 补终结行；落地先 `bash -n`、运行中不改脚本 | `bash -n` rc=0 |
| F5 节点共享工具链被并行会话替换 ⇒ `llvm-mc: Text file busy`，199 例 build 失败 | ✅已修 | `run_book()` 对 build 失败自动重试 1 次（60 s）并打印次数 | 本轮重试 0 次、235/235 |
| F6 `analyse` 拿 fault 的 `expected`（名字）与 rc 比 ⇒ 每平台通过数只剩链例（38/235） | ✅已修 | 从 runner 的 `FAULT_CODE` 现场取期望码 | chipyard/QEMU 235/235、gem5 234/235 |
| F7 `install-host` 与并发 LLVM 写者共用安装根（主会话指出的串行冲突） | ✅已修（流程） | 证据脚本加 `--no-install`，等待窗口期只跑 `build-qemu`；7 次历史调用留档 | `DEFERRED` 显式打印，不冒充通过 |

判决：无未修 finding；「待裁定」1（gem5 跨模块缺口）非本任务可修、2（安装根窗口）已在放行窗口内闭环 ⇒ 状态置 `待验收`。

### 第 2 轮 engineer 返工（reviewer Needs Revision：证据脚本基线自引用）

reviewer 阻断（唯一）：`run.sh` 原先用 `git show HEAD:…helper.c.patch` 重建「改前」基线；任务产物提交（`bb1df1a0`/`2e5b9447`）后 HEAD 已含掩码 ⇒ 基线与被测物同源，提交后 `run.sh` rc=1、4 条断言恒假红。

**修法选择：方案 2** —— 把改前 patch blob 冻结为 `pre-change/helper.c.patch.before`（md5 钉死 `ea8ae380c3d3ea7a7c26e8eeb672fc99`）。理由：① 与仓库历史解耦，不受产物提交/amend/rebase 影响，重复运行基线恒定；② 不留「哪个提交才是改前」的隐性契约（`8e6056ab` 现在可达，但依赖历史不改写）；③ 冻结件 md5 本身成为一条新的可达 FAIL 断言（谁用改后内容重生成基线即红）。

**可达 FAIL 现场演示（`cp` 备份 + 还原，未用 git 还原）**：撤掉组件源里 10 行掩码改动（备份 source `md5 e2813d6c…`，删除 `RA0_WRITE_MASK` 块与 `if` 块）⇒ `run.sh --no-install --no-node --no-inject` **rc=1、PASS=20 FAIL=14**，目标 4 条全红：`diff hunk count 1→0`、`hunk is the helper_ra_store body 1→0`、`added lines = 0`，以及探针点 20/21/22 转红（`expected=… actual=` 空）、`source tree clean`/patch-tree/source-state 报红作旁证。`cp` 还原 ⇒ 源 md5 回 `e2813d6c…`、源树 clean、重建二进制回 `1037740c…`；同模式重跑 **rc=0、PASS=34 FAIL=0**（日志 `log/demo-baseline-revert-FAIL.log`、`log/demo-baseline-restored-PASS.log`）。

返工后复跑：`run.sh --no-install`（完整：节点 + 双注入 + 门控）**rc=0、PASS=56 FAIL=0**（`run-all.log`）；`--no-install --no-node --no-inject` **rc=0、PASS=34 FAIL=0**。其余断言与数字未变（56 = 原 53 + 新增基线件 md5 断言 1 + `check-inst` 2 条）。

### 第 1 轮 reviewer 验收

**判决：Needs Revision**（1 项阻断 = 证据脚本提交后不回绿；1 项环境待处置）。以下全部为 reviewer 自己执行的输出。

**重跑记录（命令 / 真实输出 / 退出码）**
1. `bash <运行期证据目录>/run.sh --no-install`（完整：含节点三平台 + 双路注入）→ `summary: PASS=51 FAIL=4`、`RESULT: FAIL`；另跑 `--no-install --no-node --no-inject` 取真码 → **rc=1**（非管道码）。
2. 4 条 FAIL 全为假红：`(no RA0_WRITE_MASK) expected=0 actual=2`、`diff hunk count 1→0`、`hunk is helper_ra_store 1→0`、`added lines = 0`。根因：脚本 L105 `git show HEAD:components/qemu/patches/target/dadao/helper.c.patch` 重建“改前”基线；`bb1df1a0` 提交后 HEAD 已含掩码（实测 `grep -c RA0_WRITE_MASK` = 2）⇒ 违反「提交后仍须回绿、基线须锚定固定提交」。
3. 同轮其余项我自己的输出全绿：节点 `01-load-store images=235 chipyard=235/235 qemu=235/235 gem5=234/235`、`[GAP] ld.o_rrii_ra.S gem5 rc=20`、`chain=38 fault=197`；`05-arith-addr 12/12`、`06-control-flow 34/34` 三平台全绿；`node summary: PASS=13 FAIL=0`。
4. 门控（我重跑）：`check-inst rc=2`、红集恰 `FAIL divrem.yaml[23]`（1141 total / 1135 passed / 1 failed / 5 deferred）；`check_qemu_trans 264/264`；`check-patch-tree qemu 0`；`--source-state qemu OK`；`check-component-changelog rc=0`。
5. 改前对照：改前二进制同册 `rc=1`、失败记录恰 1 条、`ld.o_rrii_ra` 链例 `rc=20`。
6. **独立注入 1 路（自设计）**：掩码 `0x003F…` → `0x00FFFFFFFFFFFFFF`（只丢 `[63:56]`，多留 bit55/54）⇒ `build-qemu rc=0`、二进制 `7f51c6f4…` ⇒ 探针 **rc=1**、链例 `rc=20`（点 20 断言红；点 21/22 因链在 20 中止而不可达）⇒ `cp`+md5 还原（`e2813d6c…` 相等、源树 clean、无 `INJECT-REV` 残留）⇒ 重建 `rc=0`、md5 回 `1037740c…` ⇒ 探针 **rc=0**，点 16/17/19/20/21/22 六值全对。
7. 安装根==构建树（首测 07:0x，**未跑 install-host**）：5 件全 EQUAL —— `qemu 1037740c…`、`clang c4f9247e…`、`llc ee60b612…`、`llvm-mc fec66e82…`、`ld.lld 53f9c071…`。

**约束核验**
- 只此一处改动 ✓：`git diff 8e6056ab..HEAD` 仅 3 文件（`helper.c.patch`、`changelog.md`、本任务书）；补丁 1 hunk、纯新增 10 行、**0 删除**。
- RAS 头更新逐字节不变 ✓：新旧补丁整体 diff 仅第 1113/1117 行两处插入（均在 `helper_ra_store` 内）；抽出的 `helper_ras_push`/`helper_ras_pop` md5 新旧分别 `fc09ab87…`/`c6325168…` 相同。
- 未动 `spec/`、`contracts/`、gem5、chipyard、`tests/`、`tools/` ✓；`git status -uall` 与 `git diff --stat` 前后均空 ✓（快照对账）；完成区 15 行 ≤30、无运行期绝对路径 ✓；未提交 git、未跑 install-host ✓。

**阻断项（返工要求）**
1. 修 `run.sh` L105 基线锚点：改锚变更前提交（`8e6056ab`）或把改前 patch blob 存 `$HERE/pre-change/`；重跑须 `RESULT: PASS`、**rc=0**，且撤掉改动时该断言仍须红（保可达 FAIL）。reviewer 不代写该脚本。
2. 环境（非 engineer 缺陷，但挡验收 #4）：`m14-llvm-006` 于 07:11:37 并发跑 `install-host`（rc=0、07:12:18 完）把**注入期**的 qemu 装进共享安装根 ⇒ 现 `安装根 7f51c6f4… ≠ 构建树 1037740c…`；须主会话串行窗口重跑 `install-host` 后复核（reviewer 按约束未跑、亦未手工 cp）。
3. 「待裁定」1（gem5 缺口、三平台 234/235）按任务书口径不阻断本任务。

### 第 2 轮 reviewer 复核

**判决：Accepted**（第 1 轮唯一阻断已修）。以下均为 reviewer 本轮亲自执行的输出；未跑 `install-host`、未提交 git、未改主工作树。

**重跑（命令 / 真实输出 / 退出码）**
1. `bash <运行期证据目录>/run.sh --no-install`（完整：门控 + 节点三平台 + 双注入）→ `summary: PASS=56 FAIL=0`、`RESULT: PASS`、**REAL_RC=0**。
2. `bash <运行期证据目录>/run.sh --no-install --no-node --no-inject` → **rc=0**、`PASS=34`、`FAIL=0`（与返工声明一致）。
3. 改动范围：与第 1 轮备份 `diff` 仅 3 处 hunk（L101–118、25 行），全在「改前基线」块；`git show HEAD:` 调用已删（全脚本仅注释提及），其余断言逐行未动。
4. 冻结件 `pre-change/helper.c.patch.before` md5 = `ea8ae380c3d3ea7a7c26e8eeb672fc99` == `git show 8e6056ab:…helper.c.patch`（`diff` 空、rc=0），亦 == 第 1 轮我自行导出的改前补丁；新增「基线 md5」断言两次绿跑均 PASS。

**可达 FAIL 演示（我自做：`cp`+md5 备份、`touch` 还原，未用 git 还原）**
5. 撤掉组件源 10 行掩码（`git diff --stat` = `10 deletions(-)`、`grep -c RA0_WRITE_MASK` = 0）⇒ 同一脚本 **rc=1、PASS=20 FAIL=14**；第 1 轮那 4 条里 **3 条真红**：`diff hunk count 1→0`、`hunk is helper_ra_store 1→0`、`added lines = 0`；另有 `RA0_WRITE_MASK defined exactly once 1→0`、点 20/21/22 转红、`source tree clean`/`check-patch-tree`/`--source-state` 报红，共 14 条。`(no RA0_WRITE_MASK)` 仍 PASS——它查的是冻结基线，本就该绿。
6. 还原：源 md5 回 `e2813d6c…`、源树 clean ⇒ 重跑 **rc=0、PASS=34 FAIL=0**，构建树 md5 回 `1037740c…`。

**安装根（本轮未跑 install-host）**
7. 5 件 `md5(构建树)==md5(安装根)` 全 EQUAL：`qemu 1037740c…`、`clang 5534ae0c…`、`llc c143cbc5…`、`llvm-mc c111b5b5…`、`ld.lld 45990808…`；安装根 qemu mtime = 07:14:25（主会话串行恢复），本轮无新增 install 日志。

**其余断言与第 1 轮一致**
8. 节点 `01-load-store images=235 chipyard=235/235 qemu=235/235 gem5=234/235`、`[GAP] ld.o_rrii_ra.S gem5 rc=20`、`chain=38 fault=197`；`05-arith-addr 12/12`、`06-control-flow 34/34` 三平台全绿；`node summary: PASS=13 FAIL=0`；`check-inst rc=2`、红集恰 `divrem.yaml[23]`（1141/1135/1/5）。

**约束核验**
9. 仓库侧改动仅本任务书（完成区「测试结果/#6/新发现」更新 + 本记录）：`git status -uall` 单条、`git diff --stat` 仅任务书；完成区 15 行 ≤30；组件源树 clean、构建树 `1037740c…`。
10. L1 `check-knowledge-refs` 首跑 rc=1，红源是**我第 1 轮记录**里的具体 `.work/` 路径（行 102，reviewer 自己的笔误）⇒ 已改 `<运行期证据目录>` 占位，复跑 **rc=0**。
11. 非阻断 finding（6.5）：完成区「与 `git status …` 三条逐条一致」在两件产物提交后已过时（现 status 仅 1 条）⇒ 建议收尾改为「与分支累计改动三条一致」。
