# m18-linux-008: K1–K4 门控断言补强（ISS-444/457/487/488）

**模块**：linux
**项目里程碑**：M18
**依赖**：无（涉及既有 K1–K5 门控与探针）
**可并行分片**：是（按 issue 四条，文件不重叠）；执行仍受 linux 组件写者互斥约束
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测 31/62/86/124/182 min，中位 86 min；本任务为四条既有 finding 的补强，取 1.5–2× 中位）
**档位**：中改（门控/探针断言）
**状态**：已验证
**执行环境**：本地（QEMU system；K1/K2/K4 既有镜像）

## 背景

M14 遗留四条 P3 finding 已分诊到 M18（`issues.yaml` 的 `milestone: M18`），均属「断言不可达 FAIL / 证据间接 / 措辞归属错」：

- `ISS-444`：K1 三阶段顺序只有间接证据（共享 BootROM 不打印）；需给 hmon/smon/power 各加 1 行 semihosting 标记，门控改直接断言顺序。
- `ISS-457`：K2 两条明确要求缺可达 FAIL 断言（`local_irq_save` 的 flags 截断、`enable` 全清 0 仍全绿）；需补 P1/P5 绝对断言并订正注入标签。
- `ISS-487`：`k4_switch_probe.py` 的 S6 只钉调用字面量、可被注释命中；需改钉调用形态并补 `clocksource_register_hz` 同判；旧断言翻转须补 §4a 退役台账；WARNING 白名单按文本而非 `file:line`。
- `ISS-488`：`TASK_UNMAPPED_BASE` 页对齐半修复无断言；完成区计数不准；补丁树判据缺现场统计行。

## 目标

按 `docs/Process-07` 的「断言可达 FAIL」与 §4a 退役口径逐条闭合上述四条；**不放宽既有判据**，不改内核行为。

## 验收（逐条贴真实 rc）

1. 四条 issue 逐条有处置证据（文件 + 断言 + 注入记录），并在 `issues.yaml` 关闭（`closed_in: M18`、`resolved_by` 指向本任务）。
2. 每条新增/修改断言至少 1 路**可达 FAIL**：注入 → 目标断言红 → `cp`+md5 还原 → 回绿；证据脚本一键跑。
3. `ISS-444`：BootROM 三阶段标记在 `check-linux-k0` 与 `check-linux-k1` 上均可观测；顺序断言可直接判红（注入乱序或去标记）。
4. `ISS-457`：P1（高位参与比较）与 P5（`enable == disable & ~SOURCE_BITS`）在注入下判红；`run.sh --inject` 标签与实况一致。
5. `ISS-487`：S6 在「删除注册行」注入下判红、注释命中不再假绿；WARNING 白名单按文本匹配；补 §4a 退役记录。
6. `ISS-488`：补「exec 后 `mm->mmap_base` 页对齐」断言；计数现场派生；补丁树判据打印问题总数。
7. 不回归：`check-linux-k0`、`check-linux-k1`、`check-linux-k2`、`check-linux-k5`、`check-linux-k6` 全 rc=0；`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
8. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`tests/unit/linux/**`、`tools/linux/**`、`tests/shared/bootrom/**`、`docs/Process-07*.md`（仅 §4a 退役记录）、`.tao/knowledge/issues.yaml`、本任务书。不改 `components/**`、`Makefile`。
3. 每条断言有可达 FAIL；禁恒真、禁两支写同一结果、禁同源自比；计数现场派生。
4. 源码还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。
5. 不改版本号；术语「bank = 寄存器组」。

## 待裁定

1. **ISS-444 需要放宽文件集**：任务书硬约束允许的 `tests/shared/bootrom/**` **不存在**；共享固件实际是
   `tests/ee-vast/{power_vast,hmon_k0_vast,smon_k0_vast}.S`，BootROM 构建器是 `tools/qemu/k0_boot_probe.py`
   （`build_firmware()` 无 power 阶段 defsym 入口，需加 `power_defs`）。两处均在本任务允许路径之外，且
   chipyard 侧同源 `power_vast.S`（`POWER_RTL_BODY=1`）与签入 bootrom hex 必须逐字节不变 ⇒ 标记须
   `--defsym` 默认 0、仅 K0/K1 打开。请裁定：①另立任务放开这两条路径；②或把「三阶段标记」改为只做 K1 侧
   可观测的其它方案。
2. **ISS-488 R1 需要内核探针**：`exec` 后 `mm->mmap_base` 在用户态不可观测（本端口 `CONFIG_MMU` +
   无 `HAVE_ARCH_PICK_MMAP_LAYOUT` 的 legacy 布局，`unmapped_area()` 的 `PAGE_ALIGN(low_limit)` 抹掉非对齐），
   只能由 `components/linux` 的 `k5_pagesz_selftest` 打印；本任务禁改组件补丁 ⇒ 建议并入 m18-linux-014/015
   等已占 `components/linux` 的任务，或另立。

## 完成区

**测试结果**：证据 `run.sh` 全绿 31/31 rc=0（static 18 + boot 13）；`check-linux-k1` 112/112；K5 `--selfcheck`
11/11；`check_k6 --only R` 34/34；`make -k check` 与基线（HEAD 临时 worktree）失败集逐行相同；
`check-knowledge-refs`/`check_issues` rc=0。

**修改文件**：`tests/unit/linux/{k4_switch_probe,k2_irq_probe,k5_clocksource_probe,check_k6}.py`、
`docs/Process-07-门控分层规范.md`（§4a.4）、`.tao/knowledge/issues.yaml`、本任务书（证据脚本为运行期产物）。

**验收结果**（均取自 `run.sh` 实测，逐条「注入 ⇒ FAIL ⇒ cp+md5 还原 ⇒ 回绿」）：
① ISS-487 F-a：`s6-inject-comment` ⇒ 两条注册断言红且**旧字面量判据此时仍绿**（= 原 finding）；单删
clockevents ⇒ 只其一条红；`s6-restore`（md5 相等）回绿。
② ISS-487 F-c：白名单 5 臂 + 源码锚点（改 `init/main.c` 的 WARN 文本 ⇒ 红 ⇒ `cp` 还原 ⇒ 绿）；K5 实跑 C1 全绿。
③ ISS-487 F-b：§4a.4 三行在且被机械核对；`retired-back-44` ⇒ R 红 ⇒ md5 还原 ⇒ 回绿；K6 R 34/34。
④ ISS-457：`flags-32` ⇒ P1 两条绝对锚点红（实 `0xffff7fff`/期 `0xffffffffffff7fff`）；`enable-write-zero` ⇒
P5 两条绝对锚点红（实 `0x0`/`0x8000`）；均还原回绿；路数 `--list` 现场派生。
⑤ ISS-488 R3/R2：patch-tree 4 臂 + 解析器「一致/不一致」两例；现场 rc=0（total=0、linux=0，按 pin 重建源码树后）。
⑥ 无回归与基线：K1 112/112、K6 R 34/34；`make -k check` 失败集（`check-cfx-aliases`/`check-milestones-fresh`/
`check-temp-dirs`）与基线逐行相同（`diff` 见证据日志）。

**新发现/坑**：**K1 在共享安装根 qemu（`7148dbca…`，按 master 69 补丁重放构建的新模型）下当前为 KNOWN-RED**（`unknown cause=0x10000000000000`，61/109），根因是「新模型 qemu × 未迁移旧内核」的**跨任务缺口**，归口 `m18-linux-022`；跨任务比对前须核安装根 md5（`ISS-373`，已 open）。① 共享安装根的 `qemu-system-dadao` 被在途 qemu 任务覆盖：用它跑 `check-linux-k1` 直接红
（`cause=0x10000000000000` 不在 11 项表内），换 `m18-testcases-003` 留存的旧模型 qemu（md5 `f734b701…`）后
112/112 ⇒ 安装根应隔离/记录 md5。② 从主仓运行期工作区拷内核源码树会带上他人在途提交（本次报 4 条 linux
补丁树问题、K1 死于 unknown cause）；正确姿势 = `.cache/linux.git` + pin checkout + `apply_series --component linux`。
③ `apply_config_lines()` 不写 `CONFIG_INITRAMFS_SOURCE` ⇒ 新 worktree 里 K5/K6「No working init found」假红，
先跑 `tools/linux/make_defconfig.py`。④ 基线 KNOWN-RED：K2 `C0`（契约 §6.4 已改 `cg8/rc1`、内核仍 `cg2/rc4`）
⇒ ISS-457 运行期断言以 `static=False` 取证并点名。

**遗留问题**：① ISS-444 全条、② ISS-488 R1 —— 需越出允许路径（见「待裁定」1/2）；其余（457、487 三条、
488 R2+R3）已闭合并在 `issues.yaml` 同步（444/488 保持 open 并写明根因）。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 6 个改动文件与证据脚本，findings 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `code_only()` 保留字符串内容 ⇒ 字符串里的调用形态仍会被当「调用」 | ✅已修 | 字符串/字符字面量内容空白化（保留引号与换行） | 注入样例 `call in code? False`；`code_only` 输出打印 |
| F2 `unknown_warnings()` 只识别一种 banner ⇒ 其它格式的 `WARNING:` 漏判 | ✅已修 | 未解析成块的 `WARNING:` 行直接判红 + 新增 selfcheck 臂 | `selfcheck C1-warn 另一种 banner` PASS |
| F3 补丁树统计臂在干净树下恒真（total==rows==0） | ✅已修 | 抽出 `parse_patch_tree()` + 「一致/不一致」两例解析自检 | `iss488-patch-tree-parser` PASS（不一致臂 5≠1） |
| F4 ISS-457 的 P5 只有**相对**锚点：`enable-write-zero` 下实测 `disable=0x8000/enable=0x0` 仍绿 | ✅已修 | 补两条绝对锚点（`enable == 复位全1 只清源位`、`disable == 复位全1`） | `iss457-enable-zero-red` PASS（红项点名两条绝对锚点） |
| F5 证据脚本的 static 段与 boot 段并行会互污（boot 段临时改内核源码 ⇒ 补丁树判据红） | ⏸已记录 | `run.sh` 头部注明单实例串行；static 段判据保持 fail-closed | 串行跑 `run.sh` 全绿 |
| F6 内核源码树带他人在途提交（拷自主仓运行期工作区） | ✅已修 | 从 `.cache/linux.git` 按 pin 重建 + `apply_series --component linux` | `check_patch_tree` rc=0、K1 112/112 |
| F7 取证用的 qemu 不能污染共享安装根 | ✅已修 | 本 worktree 内 `.dadao` 只 symlink 工具链、qemu 用本地副本；`run.sh` 打印其 md5 | 证据日志首部 `qemu : f734b701` |

**判决**：F1–F7 全部已修/已记录，无未修 finding ⇒ 状态 → `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录（本人执行，rc 取被检命令自身）**：① 仓库根执行运行期证据目录内 `run.sh --part static` → **rc=0，18/18**：S6 两路注入（删调用留注释 ⇒ 两条新断言红且旧字面量判据仍绿；单删 clockevents ⇒ 仅其一红）、WARN 白名单 5 臂 + 源码文本锚点注入红/`cp` 还原绿、§4a.4 表+文档行、`retired-back-44` 红→绿、patch-tree 解析「一致/不一致」两臂 + 现场 `total=0=Σrows`、`rc==0 ⇔ total==0`、`check-knowledge-refs rc=0`。② `run.sh --part boot` → **rc=0，13/13**：`flags-32` ⇒ P1 两条绝对锚点红（实 0xffff7fff/期 0xffffffffffff7fff）；`enable-write-zero` ⇒ P5 两条绝对锚点红（enable 实 0x0、disable 实 0x8000），**此时相对锚点 0==0 仍绿 = 原漏洞被绝对锚点补上**；两路 `cp`+md5 还原回绿；`check-linux-k1` **112/112**。③ `check_k6.py --only R` → `R 34/34 items=34` **rc=0**。④ **独立注入（非 engineer 自检）**：向 `k4_switch_probe.py` 追加旧字面量注释行 ⇒ `run.sh --part static` **rc=1**、红项 `iss487-4a4-table 旧判据回潮`；`cp` 还原 + md5 `7cc1746d…` 相等 ⇒ 重跑 **rc=0**。⑤ **基线**：HEAD 临时树（接同一安装根与运行期目录）`make -k check` **rc=2**，失败目标 = `check-cfx-aliases`/`check-milestones-fresh`/`check-temp-dirs`（3 项）、FAIL 行 **16** 条，与本树输出 `diff` **逐行相同**。

**换 QEMU 二进制（重点核，非采信）**：本树安装根副本 md5 `f734b701…` = **pre-ADR-0061 旧模型**，由 m18-testcases-003（`old-model-qemu/`）与 m18-infra-003（`oldqemu.md5`）各自留存并在任务书点名「旧模型 qemu 配旧内核」；master 内核仍是旧模型（m18-linux-022 = 待开始）⇒ 与 K1 被测对象配对正确，**不是随手挑的**。本人复现：把共享安装根 qemu（`7148dbca…`，11-24 23:45 由共享源树按 master 69 补丁重放后构建）拷入 → `check_k1` **rc=1、FAIL (61/109)**、`unknown cause=0x10000000000000 (not in the 11-item table)`；`cp` 还原 + md5 相等后回到 112/112。⇒ 该红是 ADR-0061 新模型 qemu × 未迁移旧内核的**既有跨任务缺口**（m18-qemu-005/006 已 11-23/24 合入，内核侧归口 m18-linux-022），与本任务 7 个改动文件无因果，**不判「用旧二进制掩盖新回归」**。披露：完成区「新发现/坑①」已含 md5 与建议；「共享安装根被在途任务覆盖」**已有 open 的 P1 issue ISS-373**（含「跨任务比对前先核安装根 md5」），无需另立。

**约束核验**：范围 `git diff --name-only` = 7 文件、与完成区声明一致，未碰 `components/**`、`Makefile`，无未跟踪残留，未提交 git；快照前后 `git status --porcelain -uall` 同为该 7 行。可达 FAIL 五路（S6/WARN/retired-back-44/两路内核注入）均本人红→还原→绿；计数现场派生。**待裁定①成立**：`tests/shared/bootrom/**` 不存在，固件在 `tests/ee-vast/{power,hmon_k0_vast,smon_k0_vast}.S`，`k0_boot_probe.build_firmware` 对 power 只 assemble、无 defsym 入口，`check_k0.py` 除组件名外无 qemu 引用（不启动 QEMU）；落地须越出允许路径且保 `POWER_RTL_BODY`（Makefile / components/chipyard README 引用）逐字节不变 ⇒ 本任务内非低成本。**待裁定②成立**：`.config` 无 `HAVE_ARCH_PICK_MMAP_LAYOUT`，`unmapped_area()` 对 low_limit 上取整 ⇒ 用户态观测不到 `mmap_base` 非对齐，只能内核探针（`components/linux`，本任务禁改）。

**未采信项**：K5 `--selfcheck 11/11` 未本人重跑（需重建 K5 镜像，超时限），采信完成区；其余验收命令均本人重跑。

**finding（文档级，不阻断，交 architect 收尾补）**：坑①补一句「K1 在安装根 qemu 下当前为 KNOWN-RED，归口 m18-linux-022，引 ISS-373」。

**判决**：**Accepted**。
