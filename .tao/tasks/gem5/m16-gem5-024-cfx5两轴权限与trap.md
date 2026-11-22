# m16-gem5-024: gem5 cfx5 两轴权限 / trap / escape

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m16-gem5-023`（off no-op）合入
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（用户 2026-11-22 选 A）

`m16-gem5-023` 的遗留①：gem5 的 cfx5 **不进 `kCfxhaMap`**，所以 `trap cfx_cache`/`escape cfx_cache` 与 `<mode>_cfxtrap/cfxreg/cfxmem/cfxexe` 两轴掩码路径没接；QEMU/RTL 都有。用户要求每个 cfx 在 H/S/U 下跑，权限路径必须齐。

## 要做

1. **进 map**：cfx5 加入 `kCfxhaMap`（或等价通用路径），获得 `<mode>_cfxtrap/cfxreg/cfxmem/cfxexe` 行与异常向量。
2. **trap/escape**：`trap cfx_cache`、`escape cfx_cache` 按通用路径进入/返回；目标 cfx 的向量与帧字段按契约。
3. **两轴权限**：默认仅 hmon 可访问；smon/umon 访问按掩码 ⇒ `CFXPERM`；`m16-testcases-017` 的 env 打开掩码后允许。
4. **不回归**：023 的寄存器面、off/on 的 cfx5 命令语义、021 的 D/I 维护不回归；Tiny 无 cfx5。
5. **三方一致**：与 QEMU 的 `dadao_cfxha_map`、RTL 的通用 cfx 权限行对齐；差异登记 `expected-divergences.yaml`。

## 不做

- 不改 cache 数据通路/命令语义（021/023）；
- 不改 QEMU/RTL；
- 不加多核/uart。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py gem5` 幂等；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. cfx5 在 `kCfxhaMap` 中可查；`trap`/`escape cfx_cache` 进入/返回正确；
2. 默认 hmon 可访问、smon/umon 访问 ⇒ `CFXPERM`；env 打开掩码后允许（若 017 未合入，先用探针直接改掩码）；
3. off/on 的 023 寄存器面与 021 D/I 语义不回归；Tiny 无 cfx5；
4. **可达 FAIL**：注入「cfx5 不进 map」⇒ trap/权限用例红；注入「smon 默认放行」⇒ 红；`cp`+md5 还原并重建回绿；
5. `check-gem5-decode`、`check-patch-tree` gem5 段、`check-index-blobs`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` → **25/25 PASS（EXIT=0）**；`run.sh --inject all` → **43/43 PASS（EXIT=0）**。实现口径：cfx5 进 `kCfxhaMap`（末位追加，保持 trace 索引）→ 通用 cg0–cg7（两轴 mask、向量、cg4/cg5 帧与计数）+ cg8 五个 cache 寄存器；`trap`/`escape cfx_cache` 走通用进入/返回。默认 mask `0xFFFF…FFF7`（只允许 hmon）：hypv 下 cfx_umon 的 `cfx2rd` 与 `trap` 两轴均 CFXPERM+NCFXPERM（`0x0000008000000080`）；固件按行打开后允许。smon（supv）默认 CFXPERM（handler 在 cfx_smon 检查帧），打开 supv 行 + `cg3 rc12=0x8` 后允许且 user 行仍读默认；umon（user）默认 CFXPERM，打开 user 行后允许，escape 回 hypv 后 hypv 行仍拒绝。trap cfx5 两轮：`cg5 rc2/rc3/rc4/rc0/rc1`、`cg4 rc2` 与两轮 prev_cfx=0 全对，escape 返回下一条并恢复调用者 cfx。023 off 向量（逐字）off=0x10、on 机=0x101（非空转）；021 D/I 向量 on=0x10；Tiny：`tiny_cfx.cc` 无 cfx5/无 Node map，功能探针 `cfx2rd cfx5⇒CFXREG`、`trap cfx5⇒ILLI`=0x10。
**修改文件**：组件源 + 补丁 2 份：`src/arch/dadao/node_cfx.cc`、`node_cfx.hh`（`components/gem5/patches/` 对应 `.patch`，`make_patch.py gem5` 首跑 `2 written, 104 unchanged`、重跑 `0 written, 106 unchanged`）；`components/gem5/{README.md,changelog.md}`；`tests/arch/expected-divergences.yaml`（无遗留差异条目：临时项 DIV-07 已随 `m16-qemu-005` 关闭删除，`updated` 改 2026-11-23）；本任务书；运行期证据（`run.sh`、`make_hmon_variant.py`、6 个 `.s` 向量、2 个 lds、日志，gitignored）。
**验收结果**（真实 rc）：`check-gem5-decode` 0；`check-tasks` 0；`check-index-blobs` 0；`check-component-changelog` 0；`check-patch-tree` **gem5 段 0 problem**（整树 rc=2，18 行全在其它段：chipyard 10 条 assertion + 8 条 worktree-absent skip）；`make_patch.py gem5` 0（幂等）。三路注入各「红→`cp`+md5→重建→绿」，源 md5 均回 `8e32b6f9…`：① `nomap`（cfx5 移出 map）→ 红 2817（0x0B01）；② `defaultallow`（cfx5 supv 行 + deleg 默认放行）→ 红 3104（0x0C20）；③ `noescapedrest`（escape 不恢复 inner_cfx_code）→ 红 2576（0x0A10）。环境 Linux 6.8.0-149 x86_64 / nproc=64；`gem5.opt` md5 `c6631dc1…`；首次全建首跑撞共享盘 `No space left on device`（重试 1/3 后 5m57s 过），增量重建 **126 s**，注入 6 次重建每次约 125 s（22:50:02–23:00:14）。未提交 git；未改 021/023 的 cache 数据通路/命令语义、QEMU/RTL、`spec/`/契约版本。**`m16-qemu-005`（`53b3b162`）补齐 QEMU cfx5 通用 cg0–cg7、删除 `DIV-07` 后重跑：`run.sh` 25/25（EXIT=0）、`--inject all` 43/43（EXIT=0）**，文档改动对判据无影响。
**新发现/坑**：① **cfxexe 轴是真实的**：cfx_smon 的 supv handler 若放在 hmon SRAM，取指受 cfx_hmon hypv 行 `cfxexe` 约束（源 bit2 默认拒），不打开就无限 CFXPERM 循环；证据里显式打开（`0x7FFF…FFF3`）。② **semihosting 参数块必须在 RAM**：放在 hmon SRAM 时 gem5 `readBlob` 失败（端口代理不背 cfx 空间）。③ hmon 启动含 1 µs DMA（≈1e6 ticks），`--max-ticks 2e6` 会像「死循环」；证据统一 ≥1e8。④ **标签地址必须链接**：对可重定位对象直接 `objcopy` 得段内相对地址，向量/期望 IP 会静默错；本任务向量改为 `ld.lld -Ttext=ENTRY` 后取 flat。⑤ CFXPERM 的 NCFXPERM 位是 `1<<39`（`0x0000008000000080`），不是 `1<<63`。⑥ 01 册（Chipyard 共享 sim）在并行会话重建期跑出 0 字节签名（1/38），且两实例共用工作目录；改用自包含 Tiny 功能探针（更直接覆盖「Tiny 无 cfx5」），失败现场保留。⑦ 实现时 QEMU 的 cfx5 只有 cg8（其余 cg⇒CFXREG），与 gem5/RTL/contract-see §3 的共用行不一致，曾登记 `DIV-07`；**`m16-qemu-005`（`53b3b162`）已补齐 QEMU 的 cfx5 通用 cg0–cg7（`cfx2rd/cfx2rc` 走 `cfx_reg_ptr` 通用表，`cg8` 专属）**，DIV-07 已按 `expected-divergences.yaml` 的 temporary 规则删除。
**遗留问题**：① ~~`DIV-07` 待追认~~ **已关闭**：`m16-qemu-005`（`53b3b162`）补齐 QEMU cfx5 通用 cg0–cg7，差异项已删除；本任务未改 QEMU。② cfx5 的 reset `excp_vector` 为通用 `(5<<42)+2^42-64K`（QEMU 同），RTL `vectorBase=0`；软件必须先写向量，暂不构成可观测差异，未入 divergences。③ `cfxmem` 轴对 cfx5 结构性不可达（无内部空间），证据只做 mask 行存在/回读。④ 固件侧：`tests/ee-vast/hmon_k0_vast.S` 目前不打开 cfx5 的 supv 行/委托（Linux 目前不访问 cfx5）；`m16-testcases-017` 的 env 需按声明打开 mode 行 + deleg。⑤ `check-patch-tree` 整树 rc=2 为其它组件既有问题（非本任务文件）。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查（本深度无嵌套子代理）：`kCfxhaMap` 末位追加 5 后所有消费点（`nodeCfxIndex`、复位循环、`cfxRegPtr`、`isa.cc` 的 `kTraceCfxha[9]`）逐一核对无索引错配；`nodeCfxRead/Write` 的 cfx5 分支已移到 cfxreg mask + `cg3 rc12` 委托之后，cg8 之外的通用行与 `CFXREG` 边界；`nodeTrap`/`nodeEscape`/`nodeCfxEnter` 对 cfx5 的向量、帧、计数与 self/cfx 轴；复位行（mask/deleg/switch/vector）与 ADR-0045 D4；023 的 `exist==0` 早返回与 CACHE-14 判序未被触碰；证据脚本的注入锚点唯一性、md5 还原、红/绿双向与 `--inject` 自检。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 可重定位对象直接 objcopy ⇒ 标签地址为段内相对，向量/期望 IP 静默错 | ✅已修 | 任务向量改 `llvm-mc → ld.lld -Ttext=ENTRY → objcopy`，021/023 保持原构建 | 修前 0x0A01 误红 → 修后 hypv 用例 0x10 |
| F2 NCFXPERM 常量误写 `1<<63`（`0x8000…`） | ✅已修 | 全部改为 `0x0000008000000080`（`1<<39`） | 默认拒绝用例转绿；`--inject nomap` 仍红 |
| F3 cfx_smon handler 在 hmon SRAM 取指被 cfxexe 轴拒 ⇒ CFXPERM 自循环 | ✅已修 | 证据 BootROM 显式开 cfx_hmon hypv `cfxexe` 源 bit2；不入产品代码 | 修前 max-ticks 耗尽 rc 0 → 修后 0x10 |
| F4 semihosting 块放 hmon SRAM ⇒ `readBlob` fatal | ✅已修 | 证据 helper 改用 RAM 的 `EXIT_BLOCK` | 修前 fatal rc 1 → 修后 0x10 |
| F5 `--max-ticks 2e6` 小于 hmon 1 µs DMA 启动，误判为死循环 | ✅已修 | 证据统一 ≥1e8 ticks | 4e9 下 supv/user/trap 全绿 |
| F6 01 册依赖共享 Chipyard sim，并行重建期 0 字节签名（1/38） | ✅已修（换判据） | 改为自包含 Tiny 功能探针（CFXREG/ILLI）+ 静态检查；失败现场保留 | Tiny 探针 0x10；01 册 attempt/retry 日志留盘 |
| F7 run.sh 期望值按十六进制当十进制比较（10≠16），首跑假红 | ✅已修 | 期望统一为十进制 16/257，打印带两制 | 修后基线 **25/25** |
| F8 QEMU 的 cfx5 仅 cg8 与 gem5/RTL/contract-see §3 冲突 | ✅已关闭 | `m16-qemu-005` 合入后删除 `DIV-07`；未改 QEMU | `53b3b162` 补齐 cfx5 通用 cg0–cg7；divergences 无 DIV-07 |
| F9 cfx5 reset 向量与 RTL 不同（软件必须先写） | ❌不修（不影响判据） | 记入遗留② | hypv 用例显式写向量后全绿 |
| F10 `check-patch-tree` 整树 rc=2 | ❌非本任务 | — | 18 行 = chipyard 10 + 8 条 worktree-absent skip，gem5 段 0 |

**约束核验**：改动集 = 组件源 2 + 补丁 2 + README/changelog + divergences + 本任务书（证据 gitignored）；未改 QEMU/RTL、`spec/`/契约版本、021/023 数据通路；组件源 `base..HEAD==1` 且干净、无 `INJECT` 残留；未提交 git；术语「寄存器组」；任务书无运行期路径。
**判决**：**待验收**（F1–F7 已修并复验；F8 待用户追认，F9/F10 已披露且不影响判据）。

### 第 1 轮 reviewer 验收

**重跑（仓库根执行运行期证据目录内的 `run.sh`，不采信完成区）**
- `run.sh` → `SUMMARY: pass=25 fail=0 inject=none`、**EXIT=0**（07:00:37，gem5.opt md5 `9f441b2f…`）；现场 rc：`check-gem5-decode` 0、`check-tasks` 0、`check-index-blobs` 0、`check-component-changelog` 0、patch-tree gem5 段 `106 patch(es)` 0 problem（整树 rc=2）、`make_patch.py gem5` `0 written`。
- `run.sh --inject all` → **43/43 PASS、EXIT=0**（07:01:09–07:13:34）：nomap 红 2817(0xB01)、defaultallow 红 3104(0xC20)、noescapedrest 红 2576(0xA10)；三路 `cp`+md5 均回 `8e32b6f9…` 并重建回绿 16；组件源树干净、`INJECT` 残留 0。
- **reviewer 自写变异 R1**（`nodePermDenied` 的 `cfxreg` 分支置 0，非脚本注入）：重建 rc=0 → `run.sh` **rc=1（pass=19 fail=6）**，行为红 4 条（hypv 默认拒 0xA01、user 默认拒 0xE01、user 打开后仍拒 0xF03×2）+ 2 条门控红（源树脏：patch-tree 2 problems、make_patch 非 `0 written`，同 021/023 审查先例）；`cp`+md5 回 `8e32b6f9…` → 重建 → **25/25、rc=0**、残留 0。
- **01 册探针（隔离 work-dir 重跑）** → `38/38 镜像通过（197 例）、rc=0、FAIL 行 0`（07:19:14–07:20:05）。

**实现核验（读源/补丁/契约逐条）**：`kCfxhaMap[…,5]` 末位、`NodeNumCfx=10`、`nodeCfxIndex` 与复位循环同步改；`isa.cc` 的 `kTraceCfxha[9]` 循环仍 `i<9`（无越界、固定 dump 序不变）；cfx5 的 `cg8` 分支在 cfxreg mask + `cg3 rc12` 委托**之后**，cg0–cg7 走通用行（`cfxModeReg` 四类 mask/向量、cg4/cg5 帧与计数、cg7 对 cfx5 全 0）；复位 `0xFFF…F7`、hmon `0x7FFF…F7`、self 只绕 cfx 轴，与 contract-see §3、ADR-0045 D4 逐字一致；`nodeTrap`/`nodeEscape` 通用进入/返回，`escape` 恢复 `inner_cfx_code`（`node_cfx.cc:1298`）。trap 向量实测断言 `cg5 rc2/rc3/rc4/rc0/rc1`、`cg4 rc2/rc5/rc3`、两轮 `prev_cfx=0`，非空转。

**不回归**：023 off 向量 0x10、on 机 0x101（非空转）；021 D/I on=0x10；Tiny 无 `kCfxhaMap`/`CfxhaCache` 且功能探针 0x10；023 向量 md5 `fd0bba1c…` 与 023 任务书记录一致（021「逐字」仅间接核对，其证据目录已随合并删除）。

**DIV-07 已关闭**：master 的 `expected-divergences.yaml` 现场 YAML 解析 = DIV-01…06（`updated 2026-11-23`）；`53b3b162` 已在 master，其 `helper.c.patch` 写明 cg0–cg7 由 generic `cfx_reg_ptr` 服务、cfx5 不特例 ⇒ 差异消失；本分支不含该提交但不改 QEMU，合并无冲突。

**遗留②（reset 向量 gem5/QEMU `(5<<42)+2^42−64K`、RTL 0）：不阻断**。spec `DADAO-12 §3.4` 规定「无内部 SRAM 的 cfx，`hypv_excp_vector` 初值由平台/实现定义」，cfx5 无内部空间 ⇒ 属实现定义；RTL=0 时软件不写向量即跳 0，故各平台 trap 前都必须写向量，现有判据全部显式写向量 ⇒ 当前不可观测。**建议**：按差异清单文件头「有差异必须由用户裁定并登记」，由 architect 提请用户裁定是否补登 permanent 条目（reviewer 不代裁）。

**遗留③（cfxmem 对 cfx5 结构性不可达）：可接受，但说法有误（finding）**。`node_tlb.cc:364` 对 `addr[47:42]=5` 的每次 ld/st/取指**先查 mask**：默认 ⇒ CFXPERM、打开后 ⇒ 无空间 CFXMEM，该轴可观测、并非不可达；证据只做 mask 行读回。四类 mask 同一初始化、同一 `nodePermDenied` 分支，现有 cfxreg+trap 覆盖足够 ⇒ 不阻断；建议改写遗留③并可选补一条 partition-5 访问用例。

**01 册 1/38 判定：环境并发假红、非 gem5 回归**。原日志 94 组三平台字节三元组中 `qemu==gem5` 全部相等（0 处不一致），9 条 FAIL 全为 `{'chipyard':0,…}` 且 rc 全 0；attempt1 记「chipyard 不存在」，共享 sim 在 22:36–23:46 被并行会话重建（现存 md5 `34c26203…` ≠ 当时 `40916651…`）；默认 work dir 取自 manifest 的**绝对共享**测试产物目录（01:16 仍有他会话写入）。复跑 38/38 全绿（见上）。

**Findings（均不阻断，architect 收尾改）**：F-a 完成区把 patch-tree 18 行分解写错（实为 chipyard 10 + **8** 条 worktree-absent skip，非「…各 1 + 3 skip」）；F-b changelog 仍写「QEMU 侧 cfx5 仅保留 cg8 收窄差异」，与 F8/`m16-qemu-005` 已补齐矛盾；F-c 遗留③措辞（见上）；F-d 遗留②待用户裁定登记。

**约束核验**：改动集 = 声明的 6 文件，验收前后 `git status` 快照逐行一致、md5 全等；组件源树干净（`HEAD=d36aa4e`、md5 `8e32b6f9…`）；证据脚本/向量 md5 前后全等；任务书无运行期路径、术语「寄存器组」；未改 QEMU/RTL/`spec`/契约版本；**未提交 git**。

**写入本记录后的 `make check-knowledge-refs` → rc=2（基线红，非本任务）**：2 条悬空 `ADR-0059` 互指，全在本任务未改动的 `MEMORY.md`/`milestones-m18.md`（本分支 HEAD 即有，master 同样只有引用、无该 ADR 文件，属并行会话在途）；本记录新增运行期目录具体路径 0、`ADR-0059` 引用 0（门控输出「具体路径 (不可复现): 0」）。`check-tasks` 重跑 rc=0。

**判决：Accepted** —— 验收命令块在我自己的重跑下全部通过、三路脚本注入 + 一路自写变异均「红 → `cp`+md5 → 重建 → 回绿」、约束无违反；F-a…F-d 记 finding，最终接受由架构师定。
