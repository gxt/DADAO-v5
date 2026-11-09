# m13-gem5-002: gem5 Tiny 恒 `hypv` 与 `cg3` 访问限制（ISS-363）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-gem5-001`（Tiny `cfx_power` + `cfx3 hmon` 已合入）
**可并行分片**：否（组件单写者）
**状态**：已验证

## 背景

`m13-gem5-001` 的 reviewer 在交叉比对 QEMU 实现时发现一处实现分歧（登记为 `ISS-363`）：

- gem5 的 `tinyEnter`（`.work/source/gem5/src/arch/dadao/fs_machine.cc`）在异常进入时**直接取** `cfx_⟨cfxname⟩_hypv_switch_run_mode` 的值作为新运行模式。
- QEMU 侧对**非 user profile** 强制 `inner_run_mode = HYPV`（引 `Machine-v5 §2`「`Machine-v5-Tiny` 运行模式恒 `hypv`，不能进入 `user`/`jail`/`supv`」）。
- 后果：guest 先把 `switch_run_mode` 写成 `≠3`，再触发任意同步异常，gem5 上就会**离开 `hypv`**；QEMU 不会 ⇒ 三平台差分时 Tiny 的越权路径分叉。
- 同时 gem5 未实现 `cg3` 的访问限制（`DADAO-13 §1`：`cg3` 为 `hypv` 模式寄存器，其它运行模式访问 ⇒ `CFXREG`）。

## 目标

1. **Tiny 恒 `hypv`**：非 user profile（Tiny）的异常进入一律 `inner_run_mode ← HYPV`，不再读 `switch_run_mode`；user profile（Vast）保持既有行为（按寄存器值切换）。
2. **`cg3` 访问限制**：非 `hypv` 模式下访问 `cg3` 寄存器（`cfx_⟨cfxname⟩_hypv_*`、`rc0`–`rc11`）⇒ 当前运行模式 monitor 的 `CFXREG`（`excp_cause_id` 位索引 2），不得静默成功。
3. **`excp_prev_run_mode` 正确**：异常进入时保存的是**进入前**的运行模式（Tiny 恒 3）。
4. 与 QEMU（`m13-qemu-001` 已合入）**逐条一致**：同一客程序在两边得到相同的 `excp_prev_run_mode`、`excp_cause_id`、`excp_cause_ip` 与 `inner_run_mode`。

## 非范围

- 不改 `Machine-v5`/`DADAO-13`（本任务按现行 spec 实现，spec 无缺口）
- 不改 QEMU / chipyard
- 不实现 `smon`、不改 Vast 的多模式语义（只保证不回归）
- 不处理 `ISS-357`/`ISS-358`/`ISS-359`（`m13-gem5-003` 与 testcases 侧）

## 验收标准

1. 新用例（`tests/arch/hmon/` 内扩展或新增）：guest 写 `switch_run_mode = 0`（user）后触发 `CFXMEM` ⇒ 断言 `excp_prev_run_mode == 3` 且异常处理期间运行模式仍为 `hypv`（handler 内再读 `cg3` 成功）
2. 非 `hypv` 模式下访问 `cg3` ⇒ `CFXREG`（位索引 2）；正常 `hypv` 下访问 `cg3` 成功
3. 与 QEMU 同程序逐条一致（`excp_prev_run_mode`/`cause_id`/`cause_ip`/模式）；chipyard 侧留给 `m12-chipyard-007` 之后补
4. 现有 `check_tiny_hmon` **148 条**零回归；`check-inst`（Vast 980/985 + 5 deferred、Tiny 44/44）、`check-arch`、`check-inst-smoke`、`check-unit` 零回归
5. `build-gem5` / `install-host` / `check-patch-tree` / `check-source-state` / L1 / L2 rc=0（外部红须逐条核实归属）
6. 补丁由 `make_patch.py gem5` 导出（非手改），`components/gem5/patches/` + `series` + `changelog.md` 同笔
7. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
8. 完成区 ≤30 行、无运行期路径

## 说明

- `m13-gem5-001` reviewer 第 1 轮 finding 3 的原始描述见该任务书；`ISS-363` 为正式登记。
- 组件单写者：本任务期间不得有其它任务改 `.work/source/gem5`。
- 构建在主控机（`JOBS=8`），不占用 207/208。

## 硬约束（子代理必读）

1. 临时目录 `/tmp/opencode/<任务ID>/`，禁仓库内临时文件。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进（自行处置：派修/绕行/有据重试并记录次数/登记后跳过）；只在需用户语义裁定时留问。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 用户裁定须原样写入任务书。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`tiny_cfx.cc`（两处改动）、`tiny_hmon.S`/`expected.yaml`/README、证据 `run.sh`+`cg3probe.py`+探针源；对照 `Machine-v5 §1.1/§2/§4.4/§7.1`、`DADAO-12 §5.2/§5.3`、`DADAO-13 §1`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 缺陷位置实为 `tiny_cfx.cc`（`fs_machine.cc` 只调 `tinyCfxRaise`） | ✅已修（文档） | 完成区/本记录按实际位置表述 | 两处改动均在 `tiny_cfx.cc`；补丁 1 份 |
| 注入「reset 即非 hypv」时 boot 首个 cg3 访问先于 slot 初始化 ⇒ handler 写 0 地址 → CFXMEM 递归 | ✅已修 | `tiny_hmon.S` boot 改为先初始化 slot 再写向量（指令数不变，record 0 ip 不变） | `--inject` C4a 探针 PASS；172 checks |
| handler 内 cg3 探针须一次性且不落入 IALIGN 路径 | ✅已修 | 探针放在 `br.nz` 的非 IALIGN 侧，先清 PROBE 再读 cg3 | checker 42 records / 172 checks；IALIGN 3 例仍 PASS |
| 证据 v1 的模型注入（去掉强制）使 guest 挂死、无结果表，无法观察 CFXREG | ✅已修 | 改为两个注入：escape→非 hypv（探针直接观察 cause 4）、入口强制移除（checker FAIL） | `--inject` 23/23；探针 `records=[(1,…),(4,cg3_probe,…),(1,4,HMON,…)]` |
| 自身日志名 `…-gates.sh/.out` 触发 `check-run-artifacts` | ✅已修 | 改名 `<TASK-ID>-<purpose>.txt/log` | 重跑 L1 rc=0 |
| 编辑误落主工作树（tests 3 件） | ✅已修 | `cp` 对账归位，主工作树 `git status` 干净 | 主工作树 porcelain 空 |

判决：全部 finding 已修并复验；状态置 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录**（全部由我亲跑，退出码取被检命令自身；证据落运行期证据目录/运行期日志）：
- `python3 tools/gem5/check_tiny_hmon.py` ⇒ rc=0，`PASS (172 checks)`，record 0–41 逐条 PASS（42 records）。
- 证据脚本 fast ⇒ rc=0，`13 checks, 0 failed`；`--inject` ⇒ rc=0，`23 checks, 0 failed`；其中 C3 oracle 注入 rc=1、C4a 负控 probe rc=1、C4b checker rc=1 均为真实 FAIL 后还原回绿（md5 对账一致）。
- 同一 ELF 直跑 QEMU ⇒ rc=33（`0x21`），结果表与 gem5 `cmp` 逐字节相同，md5 `451205816c3b2cdccff4d7e0ebd26d91`。
- `make check-patch-tree` rc=0（9 集 329 补丁）；`make check-source-state` rc=0（gem5 HEAD=e3c34a5 count=1 clean=True）；`python3 tools/infra/make_patch.py gem5` 复跑 `0 written, 99 unchanged`，补丁 md5 不变、`git status` 空。
- `make install-host` rc=0；`make check-gem5-decode` rc=0；`make check-inst` rc=0（Vast 980/985 + 5 deferred、Tiny 44/44）；`make check-inst-smoke` rc=0（90/90）；`make check-unit` rc=0；`make check`（L1）rc=0（check-tests-index 现场 total=243、check-index-blobs 244 OK、check-run-artifacts/check-no-residue/check-temp-dirs PASS）；`make check-modules`（L2）rc=0。
- `make check-arch` **rc=2**：`min_rom_probe_integ047t / start_busy_returns_busy` exit `0x62`。归属核实：该探针跑 QEMU pmem DMA，QEMU 二进制 md5/mtime 自 03:50 未变，本交付物只改 gem5 Tiny 与 hmon 用例；**重跑 `make check-arch` rc=0 且该用例 PASS** ⇒ 判既有 flaky/外部红，非本交付物。
- **独立注入**：`regPtr` 的 cg3 限制改「恒可读」+ `tinyEscape` 留在非 hypv ⇒ 重建 rc=0 ⇒ 专用探针 `--expect cfxreg` **rc=1 FAIL**（记录显示非 hypv 下 cg3 读成功）⇒ `cp`+md5 还原（源 md5 回 `e9ce0b47…`）⇒ 重建 rc=0 ⇒ checker 172 PASS、探针 `--expect clean` rc=0、工作树干净。
- boot 改序前后同 lds 汇编对比：`hmon_handover=0xffffffff0038`、`main=0xffffff010100` 完全一致 ⇒ 既有 record 0 的 IP 期望未受影响（且 IP 走 ELF 符号解析）。

**约束核验**：提交 7 文件 = 完成区「修改文件」6 件 + 任务书本身（HEAD 为 architect 的 WIP 提交；我未 commit/push、未改台账）；完成区 5 行 ≤30、无运行期路径；前后两次 `git status` + 7 个 md5 快照逐项一致（注入全部 `cp`+md5 还原，无 `git checkout`）；证据脚本每条断言均有可达 FAIL 路径且本轮被真实触发，覆盖计数现场派生未写死；`expected.yaml` 新 6 条可从 spec 独立推出（cause one-hot、CFXMEM info=访存地址、`excp_prev_run_mode`=进入前模式、`switch_run_mode` 初值 3），非先跑实现再抄。

**判决：Accepted**
① **spec 一致**：`Machine-v5 §2`「Tiny 运行模式恒 hypv、不能进入 user/jail/supv」⇒ `tinyEnter` 步骤 6 硬置 `runMode=3`、不再读 `switch_run_mode`；`excp_prev_run_mode` 在改动前一行保存 `entryMode`（进入前模式，与 `DADAO-12 §5.2 步骤5` 一致）；`DADAO-13 §1`「cg3 仅 hypv 可访问否则 CFXREG」⇒ `regPtr` 非 hypv 返回 `nullptr` → `CFXREG`（位索引 2），rc9/rc11 保留位同为 CFXREG，与 QEMU `cfx_reg_ptr` 同构。
② **与 QEMU 逐条一致**：同一 ELF 两边 guest exit 均 `0x21`，结果表逐字节相同，故 `excp_cause_id`/`excp_cause_ip`/`excp_cause_info`/`excp_prev_run_mode`/handler PC 全等；这些值我另按 spec 复核（不以两边互证）。
③ **Vast 零回归**：本交付物未改 `node_cfx.cc`（Vast 仍按寄存器值切换，与 QEMU `user_mode=true` 同口径），tiny 路径仅在 `tinyState().active` 下启用；`check-inst`（Vast 980/985+5 deferred）、`check-arch`、`check-inst-smoke`、`check-unit`、L1/L2 全 rc=0。

**非阻塞 finding**：`tests/arch/hmon/README.md` 的「records 36–40」实为 check id 36–40（表下标 36–41），文档级笔误，请 architect 收尾时改；`§4.4` 步骤 6 字面与 `§2` 的张力已按任务书口径（`§2` 优先）实现并在完成区登记，建议后续在 spec 层补一句消歧。

## 完成区

**测试结果**：`check_tiny_hmon` **172/172**（42 records = 原 36 + 新 6；原 148 条全覆盖）；证据 fast **13/13**、`--inject` **23/23**。新用例：写 `switch_run_mode=0` 后 `CFXMEM` ⇒ handler 内 cg3 读成功（record 37）、`excp_prev_run_mode=3`（38）、故障后 cg3 可读（39）、写入值保留（40）。
**修改文件**：`tests/arch/hmon/tiny_hmon.S`、`tests/arch/hmon/expected.yaml`、`tests/arch/hmon/README.md`、`tests/arch/README.md`、`components/gem5/patches/src/arch/dadao/tiny_cfx.cc.patch`（`make_patch.py gem5` 导出：1 written/98 unchanged）、`components/gem5/changelog.md`；组件源 `dadao: gem5 patch series`（base+1，clean）。证据脚本、QEMU 同程序比对与注入探针在运行期证据目录。
**验收结果**：`build-gem5` / `install-host` / `check-patch-tree`（9 集 329 补丁）/ `check-source-state`（gem5 HEAD=e3c34a5 count=1 clean=True）/ L1 / L2 / `check-inst`（Vast 980/985+5 deferred、Tiny 44/44）/ `check-inst-smoke` / `check-unit` / `check-arch` / `check-tests-index`(243) / `check-index-blobs` / `check-run-artifacts` / `check-gem5-decode` 全 rc=0。QEMU 与 gem5 跑**同一 ELF**：guest exit 均 `0x21`，结果表 md5 完全相同（`45120581…`）。
**新发现/坑**：① `tinyEnter` 实际在 `tiny_cfx.cc`；② QEMU Tiny 可直接 `-kernel` 含 BootROM PT_LOAD 的 ELF（无需 `bootrom-image`），reset 到 BootROM 段，故三平台可用同一 ELF；③ handler 内二次故障会覆盖共享帧 `cause_ip`（单帧设计），故 cg3 非 hypv 检测用专用探针程序而非主用例；④ 口径备注（非缺口）：`§4.4` 字面「模式切换取 switch_run_mode」与 `§2`「Tiny 恒 hypv」按 `§2` 优先，QEMU 同口径，未改 spec。
**遗留问题**：① 三平台一致（chipyard 侧 `m12-chipyard-007`）BLOCKED，同一 ELF/期望表可复用；② 非 hypv 的 cg3⇒CFXREG 在 Tiny 恒 hypv 下由模型注入证明（探针直接观察 `cause=4`、`cause_ip=cg3_probe`），非 guest 常规路径。

#### 收尾（architect，2026-11-10 06:34）

- 第 1 轮 reviewer **Accepted**：`check_tiny_hmon` 172/172、`run.sh` fast 13/13 + `--inject` 23/23；reviewer 独立注入（cg3 限制改「恒可读」）⇒ 探针 rc=1 ⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 172 PASS。
- 与 QEMU 同 ELF：guest exit 均 `0x21`，结果表 md5 `45120581…` **逐字节相同**（cause_id/cause_ip/info/prev_run_mode/handler PC）。
- 门控：`install-host`/`check-gem5-decode`/`check-inst`/`check-inst-smoke`/`check-unit`/L1/L2/`check-patch-tree`（9 集 329 补丁）/`check-source-state` 全 rc=0；`check-arch` 首跑 rc=2（`start_busy_returns_busy` 既有 flaky，重跑 PASS，QEMU 二进制未变）→ 转 `ISS-364`。
- Vast 零回归（未改 `node_cfx.cc`；tiny 路径仅在 `tinyState().active` 下启用）。
- 文档更正：`tests/arch/hmon/README.md` 的「records 36–40」实为 check id 36–40（表下标 36–41）。
