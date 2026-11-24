# m18-linux-023: Linux 侧异常解码适配扁平位图

**模块**：linux
**项目里程碑**：M18
**依赖**：`m17-spec-002`（扁平位图正文）、`m17-qemu-001`/`m17-gem5-001`（已验证）、`m18-linux-022`（已验证，`beb70bb9`）。
**依赖口径（主会话 2026-11-25 裁定）**：`m17-chipyard-001`（Vast RTL）降为**验证对照依赖**——Linux 侧解码按其正文（`m17-spec-002` + `ADR-0062`）先做，Vast 三方对照在 chipyard 未就绪时记 **BLOCKED**，不阻塞本任务的 `check-linux-k1`/`k2` 转绿。
**为什么放宽**：安装根 qemu 已是扁平位图模型（`7148dbca`），内核 105 补丁仍按旧「大类+子原因」解码 ⇒ 任何 PTW 故障都判 `unknown cause=0x10000000000000`（bit 52），导致 K1 61/109、K2 47/89、K5/K6 亦红，`m18-linux-006/015/016/017` 全线无法验证。
**可并行分片**：否
**预估**：4–8 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

扁平位图后，Vast 的 PTW 权限/访存故障不再带 `CFXPERM`/`CFXMEM`（父 cause=0），改由高位位图 `[32..38]`/`[48..56]` 表示。Linux `arch/dadao` 的缺页/权限处理目前按 `CFXMEM`/`CFXPERM` 解码，必须同步，否则内核把页错误当「未知异常」。

## 要做

1. `arch/dadao/mm/fault.c`、`traps.c`（或等价入口）按 ADR 的位图解码：识别 `[32..38]`/`[48..56]` 为页错误，并映射到 `vm_fault` 的 `FAULT_FLAG_*`；
2. `cause_info` 语义按 ADR（PTW 故障 = 访问 VA；ADWBFAIL = PTE PA）；
3. 保留非 PTW 的 `CFXMEM`（cfx 空间非法访问等）与 cfx 掩码 `CFXPERM` 的既有处理；
4. 补 K2/K5 相关探针或单测（至少一例页权限、一例页缺失走新解码）；
5. 不改 spec/契约与其它组件。

## 不做

- 不改 QEMU/gem5/chipyard/IDL；不改 M14 之外的架构；
- 不定义 monitor 路由（由硬件/ADR 决定）。

## 约束

- 独立 `git worktree`；组件补丁按 `docs/Process-01`；不提交 git；
- 只动 `components/linux/patches/arch/dadao/**`、`components/linux/{README.md,changelog.md}`、必要测试、本任务书；完成区 ≤30 行。

## 跨里程碑依赖与冲突（2026-11-24 核对）

- **同组件串行**：`m18-linux-022`（内核异步新模型，待开始）与 `m18-linux-006`（LTP 子集，进行中）同改 `arch/dadao`；本任务须与之串行并 rebase。
- **门控期望**：K2/K5/K6（`check-linux-k2/k5/k6`）的故障码/退出码期望按扁平模型更新；`m18-linux-015..018` 的 KERNEL_BUG/SUITE_ENV 用例可能受异常解码变化影响。
- **组件**：属 `components/linux` 补丁流程；与 QEMU/gem5/chipyard 的 Vast 侧先落地顺序为「平台 → Linux」。

## 验证

1. 页权限/页缺失各一例：内核按新位图识别并正确处理（guest rc=0）；
2. 非 PTW 的 `CFXMEM` 与 cfx 掩码 `CFXPERM` 不回归；
3. **可达 FAIL ≥2 路**：把位图判断改回只认 `CFXPERM`/`CFXMEM` ⇒ 探针红；`cause_info` 单位错 ⇒ 红；`cp`+md5 还原回绿；
4. `check-patch-tree` linux 段 0 problem；K2/K5 门控 rc=0。

## 待裁定/阻塞

- Vast 路由/退出码未定时，先按「硬件把页错误交给当前 monitor」的既有路径接入，具体向量待 ADR；
- 版本号不变。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
