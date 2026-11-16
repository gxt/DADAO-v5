# m14-infra-004: 测试机改名 `Machine-v5` → `Kaiwu`（含 QEMU 机器串）

**模块**：infra
**项目里程碑**：M14
**依赖**：`ADR-0055`（Accepted，D1–D4）；`ADR-0053`（`Gewu` 归 cfx，不改名）；`ISSUE`-free（本任务只做机械改名，不改语义）
**可并行分片**：否（全仓单写者；涉及 spec 锁与组件补丁）
**预估**：3–4 h（改名 + 锁重算 + QEMU 重建安装 + 全量门控）
**档位**：大改（跨模块机械改名 700+ 文件 + 组件重建；复核 ≥4 路注入）
**状态**：待开始

## 背景

`ADR-0055`（Accepted）定：测试机整机名 = **`Kaiwu`**（开物）；机型名仍 `tiny`/`vast`；`DADAO`（ISA/项目）、`Wuming`（核）、`Gewu`（cfx 寄存器堆）均不改。

现状规模（现场统计，2026-11-16）：

- `Machine-v5`：**557 文件 / 1,542 处**（tests 309、`.tao` 120、components 60、tools 54、docs 7、spec 2、contracts 2、manifests 1、根 `README.md` 1、`Makefile` 1）；
- QEMU 机器串 `dadao-tiny`/`dadao-vast`：**152 文件 / 437 处**（tools 68、tests 35、`.tao` 33、components 10、docs 3、spec 2、manifests 1、README 1、Makefile 1）。

## 目标（严格按 ADR-0055）

1. **整机名替换**：`Machine-v5` → `Kaiwu`（含 `Machine-v5-Tiny`/`Machine-v5-Vast` → `Kaiwu-Tiny`/`Kaiwu-Vast`）；`spec/` 册改名 `spec/Machine-v5-测试机运行环境.md` → `spec/Kaiwu-测试机运行环境.md`，正文与 `spec/README.md` 索引同步。
2. **QEMU 机器串**：`dadao-tiny`/`dadao-vast` → `kaiwu-tiny`/`kaiwu-vast`（**不保留旧名别名**，直接切换）。
3. **范围边界（不得越过）**：
   - **不改**：`DADAO`（ISA/项目名）、三元组 `dadao-unknown-elf`、ELF 机器常量、`dadao-wuming`（核 generator）、`dadao-gewu`（cfx generator）、`DADAO-11..23` 上游册名、`SimRISC-*`、`Toolchain-01`；
   - **不改**：`.tao/archive/**`（历史快照，用户 2026-11-16 裁定）；
   - **要改**：`docs/DDLN/**`（长期讲义，用户同日裁定）；`docs/` 其它（`Process-0x`、`TestReports`、tiers、`core-wuming-cycle-model`）。
4. **锁与登记**：`manifests/spec-readonly.lock.toml` 的 **path 与 sha256 同笔重算**（改名 + 正文替换 ⇒ 两处都变）；`MEMORY.md` 命名段与基线行同步。
5. **组件重建**：QEMU 机器名注册改后必须 `make build-qemu` + `make install-host`；chipyard 侧若资源/驱动里带机器串（`WumingLoadMem.v/.cc`、`WumingSemi.cc` 命中过）**需重建 sim 并登记新 md5**（属 `ADR-0055 D2` 的正文替换范围）。

## 验收（逐条贴真实 rc 与输出）

1. **残留扫描（0 命中）**：`git grep -c 'Machine-v5' -- ':!.tao/archive'` 为 0；`git grep -c 'dadao-tiny\|dadao-vast' -- ':!.tao/archive'` 为 0；且 `git grep -n 'Machine-v5' -- .tao/archive` **仍存在**（证明归档未被误改）。
2. **未越界**：`git grep -c 'dadao-unknown-elf'` 与改前**相同**；`dadao-wuming`/`dadao-gewu` 目录名与内容不变；`DADAO-1x/2x` 册名不变（贴 diff 证据）。
3. **锁与门控**：`check-spec-readonly`（21 册，含改名后的 `Kaiwu-…`）、`check-spec-drift`、`check-spec-refs`、`check-interface`、`check-knowledge-refs`、`check-knowledge-dir`、`check-dirs`、`check-archive`、`check-milestones-fresh`、`check-patch-tree` 全 rc=0。
4. **功能门控（改名不得改行为）**：`check-inst-asm` 镜像数与改前一致（904/904）、`check-lit`、`check-interface`、`check-linux-k0`（119/119）、`check-linux-k1`（108/108）、`k2_trap_probe`（85/85）、`k2_time_probe`（151/151）、`k2_irq_probe`（95/95）、`check-qemu-forms`、`check-arch`；QEMU 新机器名可启动（`-M kaiwu-tiny` 跑 `semihost_smoke` 闭环）。
5. **旧名失效证据**：`-M dadao-tiny` **报错/不被识别**（贴真实输出，证明 D3 无别名）。
6. **≥4 路可达 FAIL 注入**（`cp`+md5 还原）：① 把锁文件 path 改回旧名 ⇒ `check-spec-readonly` 红；② 改一处 `-M kaiwu-tiny` 回旧名 ⇒ `check-qemu-forms`/`check-inst-asm` 红；③ 把 `dadao-unknown-elf` 改成 `kaiwu-unknown-elf` ⇒ 判据（越界扫描）红；④ 在 `.tao/archive/` 里改一处 ⇒ 归档扫描判据红（证明两边都有判据）。
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **只改名，不改语义/编码/契约值**；任何"顺手优化"都属越界，须在完成区披露；
- `spec/` 正文替换需与锁同笔（`docs/Process-06 §5`）；
- 组件重建后必须 `make install-host`（否则门控读旧二进制）；
- 不提交 git；注入还原 `cp`+md5；构建与跑批不得同时；`JOBS=32`；
- 本任务期间**不得**有其它任务改同一批文件（全仓单写者）。

## 审阅记录

（待填）
