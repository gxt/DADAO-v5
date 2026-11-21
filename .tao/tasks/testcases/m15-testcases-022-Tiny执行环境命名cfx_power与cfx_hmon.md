# m15-testcases-022: Tiny 执行环境命名 `cfx_power_tiny` / `cfx_hmon_tiny`（四文件）

**模块**：testcases
**项目里程碑**：M15
**依赖**：无
**可并行分片**：否（四文件 + 引用一次性改完）
**预估**：0.5 h
**档位**：小改（重命名 + 引用同步；无组件补丁重建）
**状态**：已验证

## 背景（用户 2026-11-21）

Tiny 的执行环境由两段固件构成：**`cfx_power`** 在复位后校验镜像表、把 **`cfx_hmon`** 装入 hmon SRAM 并移交，从而构建**最初可用的执行环境**；此后应用才在 hmon 的保存-跳转框架下运行。原文件名 `power_tiny.*` / `hmon_tiny.*` 只说了「power / hmon」，没体现二者是 cfx 角色，改为 `cfx_power_tiny.*` / `cfx_hmon_tiny.*`。

## 要做

1. 重命名四文件（源与链接脚本）：
   - `tests/ee-tiny/power_tiny.S` → `tests/ee-tiny/cfx_power_tiny.S`
   - `tests/ee-tiny/power_tiny.lds` → `tests/ee-tiny/cfx_power_tiny.lds`
   - `tests/ee-tiny/hmon_tiny.S` → `tests/ee-tiny/cfx_hmon_tiny.S`
   - `tests/ee-tiny/hmon_tiny.lds` → `tests/ee-tiny/cfx_hmon_tiny.lds`
2. 同步全部**现行**引用：`Makefile`（`build-bootrom`）、`tools/testcases/arch/min_rom_probe_integ007t.py`、`tools/gem5/check_tiny_hmon.py`、`tools/testcases/lib/build_test_binary.py`、`tools/chipyard/excp/causeid.S`、`tests/arch/hmon/{tiny_hmon.S,tiny_hmon_min.S,tiny_hmon_layout.inc}`、`tests/README.md`、`tests/arch/README.md`。
3. 文件头订正为新名，并写明职责：`cfx_power_tiny` 装载 `cfx_hmon_tiny` 并构建最初可用执行环境。
4. **不改**产物名（`power.o`/`hmon.o`/`power.elf`/`hmon.elf`）与镜像字节；**不改**历史记录（`m15-testcases-016/019/021`、`m16-chipyard-015` 任务书、`.tao/archive/**`、`components/chipyard/changelog.md` 的历史条目——它们描述当时事实）。

## 验收（逐条贴真实 rc）

1. **字节不变**：`make build-bootrom` rc=0；`bootrom_tiny.bin` md5 `a5d78816a95469766639fa658b647ef3`、`bootrom.tiny.hex` md5 `9334a87e05340044ab3ee2dd665591d2`（与改前同值）。
2. **无旧名引用**：全仓（除上述历史记录）grep `power_tiny` / `hmon_tiny` = 0 命中。
3. **门控**：`check-tests-index`（472 条 PASS）、`check-dirs`、`check-component-changelog` 均 rc=0。
4. **可达 FAIL**：把 `Makefile:825` 的路径改回旧名 ⇒ `make build-bootrom` rc=2（`llvm-mc: error: ... No such file or directory`）；`cp` 还原 + md5 对账后回绿（已实测）。

## 约束

主工作树直接改（无子代理写）；`git mv` 保历史；不提交 git（提交由主会话在用户确认后执行）；术语「寄存器组」。

## 完成区

**测试结果**：
1. `make build-bootrom` **rc=0**（`build-bootrom: PASS`）；产物 md5 与改前一致：`bootrom_tiny.bin = a5d78816a95469766639fa658b647ef3`、`bootrom.tiny.hex = 9334a87e05340044ab3ee2dd665591d2`。
2. 旧名残留：`grep -rn "power_tiny\|hmon_tiny"`（排除 `.tao/`、`.work/`、`.cache/`、`__pycache__/`）⇒ 仅 `components/chipyard/changelog.md` 历史条目 1 处（按范围保留）。
3. `check-tests-index` **PASS（472 条）**、`check-dirs` **PASS**、`check-component-changelog` **PASS**。
4. **可达 FAIL**：`Makefile:825` 路径改回 `power_tiny.S` ⇒ `make build-bootrom` **rc=2**（`llvm-mc: error: tests/ee-tiny/power_tiny.S: No such file or directory`）；`cp` 还原、`md5sum -c` OK，重跑 **rc=0**、`bootrom_tiny.bin` md5 仍 `a5d78816…`。
5. 命名字节等价复核（改前实测）：同一源带/不带 `-z max-page-size=0x1000` 链接，flat bin md5 相同（`cfx_power = bfe08a4e…`、`cfx_hmon = 78effced…`），且与运行期 `.elf` 的 flat 产物逐字节相同。

**修改文件**：重命名 4 件（`tests/ee-tiny/{cfx_power,cfx_hmon}_tiny.{S,lds}`，文件头同步改名并写明职责）；引用同步 10 件：`Makefile`、`tools/testcases/arch/min_rom_probe_integ007t.py`、`tools/gem5/check_tiny_hmon.py`、`tools/testcases/lib/build_test_binary.py`、`tools/chipyard/excp/causeid.S`、`tests/arch/hmon/tiny_hmon.S`、`tests/arch/hmon/tiny_hmon_min.S`、`tests/arch/hmon/tiny_hmon_layout.inc`、`tests/README.md`、`tests/arch/README.md`；台账 1 行。

**遗留问题**：① `Makefile:797` 原注释把 step5 的两个 fault-policy 变体写成「from the same `hmon_tiny.S`」，实际汇编 `hmon_vast.S`，本次随重命名订正为 `hmon_vast.S`；② `tools/testcases/arch/node_probe_prelude.py` 仍是 Python 重写的 power/hmon 前导（仅 PTE 数值声明与 `hmon_vast.S` 同构，无门控），不在本任务范围。

## 审阅记录

### 第 1 轮 reviewer 验收（2026-11-21）

口径：变更集 = `$BASE..HEAD`（`BASE = ff69b07d…`，改动已提交为 `adeb5921`；快照 `git status --porcelain -uall` 为空、rc=0）。以下均为 reviewer 亲自重跑的真实输出。

1. **真 rename**：`git show --name-status -M adeb5921` ⇒ 四条 `R093 / R091 / R096 / R086`（`hmon_tiny.S`、`hmon_tiny.lds`、`power_tiny.S`、`power_tiny.lds` → `cfx_*`），非「删除+新增」；逐个 `[ -e ]` 实测：四个新名 `EXISTS`、四个旧名 `ABSENT`。
2. **零旧名引用**：`grep -rnE '(^|[^A-Za-z0-9_])(power_tiny|hmon_tiny)'`（排除 `.tao/ .work/ .cache/ __pycache__/ .git`）⇒ 命中 **1**，仅 `components/chipyard/changelog.md:133` 历史条目（按范围保留），rc=0。
3. **字节不变**：`make build-bootrom` **rc=0**（`build-bootrom: PASS`）；`md5sum` ⇒ `bootrom_tiny.bin = a5d78816a95469766639fa658b647ef3`、`bootrom.tiny.hex = 9334a87e05340044ab3ee2dd665591d2`，与 `m16-chipyard-015` 既有基线**逐字相同**（非自比）。
4. **diff 只含命名与注释**：`git diff -M $BASE..HEAD` 全文逐行核（16 文件 = 4 rename + 任务书 + 台账 + 引用同步 10 件）⇒ 变化仅为路径字符串、文件头注释标题、`Makefile:797` 的 `hmon_tiny.S`→`hmon_vast.S` 订正；**未见**逻辑、常量、链接地址、产物名变化（产物仍 `power.o/hmon.o/power.elf/hmon.elf`）。
5. **注入可达 FAIL**：`sed -i '825s|cfx_power_tiny.S|power_tiny.S|'` ⇒ `make build-bootrom` **rc=2**，日志 `llvm-mc: error: tests/ee-tiny/power_tiny.S: No such file or directory` + `Makefile:825 … Error 1` → `make … Error 2`；`cp` 备份还原 + `md5sum -c` **OK**（`Makefile = 21a6f4fbda43c70d178398bea2804d9e`）⇒ 重跑 **rc=0**（`build-bootrom: PASS`），两产物 md5 回到第 3 项原值；还原后 `git status` 干净。
6. **门控**：`check-tests-index` **rc=0**（`PASS（472 条）`）、`check-dirs` **rc=0**（`PASS`）、`check-component-changelog` **rc=0**（`PASS`，10 文件 × 4 断言 = 40 项现场统计）。
7. **约束**：本轮只改本审阅记录；不提交 git；产物名与镜像字节未变；历史记录（`.tao/` 任务书、`components/chipyard/changelog.md`）未被改动；术语「寄存器组」合规。

**判决：Accepted**
