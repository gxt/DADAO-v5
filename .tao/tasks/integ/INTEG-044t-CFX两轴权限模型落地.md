# INTEG-044t: CFX 两轴权限模型落地

**模块**：integ
**项目里程碑**：M10
**依赖**：ADR-0045（权限）、ADR-0039/0040/0042
**状态**：已验证

## 背景

ADR-0045 已定：运行模式 + cfx 资源两轴授权；每个 cfx cg0–3 使用 `cfxtrap/cfxmem/cfxreg/cfxexe` 四个 64 位来源 mask；`cfx_intr_mask` + monitor 的 `global_cfx_intr_mask`；`CFXPERM=1<<7`、`CFXESC=1<<3`。本任务只落地权限模型，不实现启动链。

## 目标

1. **spec/contracts**
   - cg0–3 重排：
     - rc0 `cfxtrap`
     - rc1 `cfxmem`（直接 ld/st + cfx 内存）
     - rc2 `cfxreg`（cfx2rd/cfx2rc）
     - rc3 `cfxexe`（直接执行/取指）
     - rc4 `cfx_intr_mask`
     - rc8/9 switch、rc10 vector、rc11 cause mask
   - 删除 `global_version`、旧 `global_cfx_mask`；
   - cfx0/1/2/3 cg8/rc1 `global_cfx_intr_mask`，64 位；
   - 初值：power/普通 cfx `0xFFFF_FFFF_FFFF_FFF7`；hmon `0x7FFF_FFFF_FFFF_FFF7`；中断 mask 全 1；
   - 异常表：monitor 增加 `CFXPERM=1<<7`；每个 cfx 增加 `CFXESC=1<<3`；原 0/1/2 保持；
   - 路由：`CFXPERM` 进当前 mode monitor；`CFXESC` 进当前 cfx；权限拒绝不再 ILLI；
   - trap 自动保存/屏蔽 `global_cfx_intr_mask`，escape 恢复；
   - escape `cfxha` = 当前 cfx，返回目标来自帧；固定 offset；不做任意跳转；
   - 同步 contracts/aliases/索引/版本/锁 sha。
2. **QEMU**
   - 实现新寄存器布局/旧字段删除；
   - 实现 4 类同步 mask + 2 类中断 mask 检查；
   - self 只绕过 cfx 轴；模式轴仍检查；
   - trap/escape 自动 mask 保存恢复；
   - CFXPERM/CFXESC 精确异常；
   - 不实现 frame_active/异步重入策略/启动链；保持现有单帧行为并披露。
3. **测试**
   - 四类 mask 允许/拒绝、self bypass、模式轴；
   - 初值/power/hmon；`global_cfx_intr_mask`/`cfx_intr_mask` 两级过滤、pending；
   - CFXPERM/CFXESC cause/info/目标；
   - trap 自动屏蔽、escape 恢复；reserved cfx 仍 ILLI；
   - 回归 Step1–4 探针。

## 验收

- `make check`、`make check-modules`、`make check-arch-smoke`、`make check-arch`、`make check-lit`、`check-spec-readonly`、`check-spec-changelog`、`check-patch-tree`、`check-source-state`、`check-cfx-aliases` 全 rc=0。
- 证据 `.work/evidence/<任务号>/run.sh` 注入→FAIL→cp+md5 还原→PASS。
- 不改启动链/页表流程/多 hart/用户态测试；不跑 full/夜跑。
- 完成区 ≤30 行；任务书/里程碑 `待验收`；临时 `/tmp/opencode/INTEG-044t/`。

## 约束

- 只做 ADR-0045 范围；`frame_active`、异步重入、jmon 代码、用户态测试不碰。
- 不提交、不 push；重建先申报；失败保留现场。

## 完成区

**状态**：已验证

### 修改文件
- QEMU：`components/qemu/patches/target/dadao/{cpu.h,cpu.c,helper.c}.patch`（source 树 commit `f223196`；补丁集 205 OK）
- spec：`DADAO-12`（cg0–3 布局/异常表/§5/附录）、`DADAO-13`（cg3/hmon 表）、`DADAO-22`（示例授权）、`DADAO-23`（初始化约定）、`Machine-01`（权限表述）
- 合约/别名/锁：`.tao/contracts/contract-see.md`、`contract-cfx-aliases.md`（生成）、`contracts/cfx-aliases.txt`（生成）、`manifests/spec-readonly.lock.toml`（5 册 sha）
- 测试：`tests/shared/bootrom/bootrom.S`（power→hmon→user）、`tests/arch/umon/{m5_perm_mask_illi.s,expected.yaml}`、`tests/unit/llvm/lit/MC/DADAO/cfx2-trap-escape.s`、`tests/case-ledger.tsv`、`tools/testcases/arch/min_rom_probe_{044t,045t,046t,047t,integ039t,integ040t,integ042t}.py`、新增 `min_rom_probe_integ044t.py`
- 门控/记录：`Makefile`（`ARCH_CFX_PROBES` 加 integ044t）、`components/qemu/changelog.md`

### 验收命令与结果（真实输出）
- `make check` rc=0（L1 83/83）
- `make check-modules` rc=0（L2 PASS）
- `make check-arch-smoke` rc=0（forward 10/10 + permission 10/10 + 25 服务）
- `make check-arch` rc=0（044/045/049/integ039/040/042/044 全 PASS；integ044t 6/6）
- `make check-lit` rc=0（159/159）
- `check-spec-readonly` 21 册 OK；`check-spec-changelog` PASS；`check-spec-refs`/`check-asm-prose` PASS
- `check-patch-tree` 205 OK；`check-source-state` qemu clean/base+1；`check-cfx-aliases`/`check-cfx-alias-table` PASS
- 证据 `.work/evidence/INTEG-044t/run.sh`：全量 13 项 rc=0 `EVIDENCE: PASS`；`--inject` 改 `MASK_DEFAULT` ⇒ probe rc=1，`cp` 还原 md5 一致 ⇒ rc=0 `EVIDENCE INJECT: PASS`

### 遗留
- `frame`/`frame_active`、异步重入、jmon 代码、用户态测试未实现（ADR-0045 范围外）；`escape` 帧错误分支在现有单帧模型下不可独立观测（每次进入 cfx 均写有效帧），未造假绿，待 frame_active 任务覆盖。
- `make check-arch` 未含旧 047t（沿用旧期望，未入 `ARCH_CFX_PROBES`）；其 GCM 断言已按新 dump 改为 cfxtrap 默认值检查，但未纳入 L3。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 删除旧别名后 SBI 示例引用失效 | ✅已修 | `DADAO-22` 12 处 `global_cfx_mask` → 目标 cfx `cfxtrap`（supv 源 bit2） | `check-asm-prose` PASS |
| 异步 `cfx_intr_mask` 对 source=target 是否仍生效 | ✅已修/确认 | `cfx_enter` 两级过滤不做 self 旁路；042 交付/挂起两例覆盖 | `min_rom_probe_integ042t` 25/25 |
| 单帧模型下 `frame_active`/escape 帧错误不可独立观测 | ⏸延后 | 不实现 frame_active；仅在完成区登记 BLOCKED，不造假绿 | 书面披露 |

### 第 1 轮 reviewer 验收

**判决：Accepted**（独立重跑全绿 + ADR-0045 逐条符合 + 注入→FAIL→还原→回绿）

**重跑记录（reviewer 自己执行，真实 rc）**：`make check`=0(L1)、`check-modules`=0、`check-arch-smoke`=0、`check-arch`=0（044/045/049/integ039/040/042/044 全 PASS，integ044t 6/6）、`check-lit`=0(159/159)、`check-spec-readonly`=0(21 册)、`check-spec-changelog`=0、`check-patch-tree`=0(205)、`check-source-state`=0(qemu HEAD=f223196 count=1 clean)、`check-cfx-aliases`=0、`check-cfx-alias-table`=0；`min_rom_probe_integ044t.py`=0(6/6)；`.work/evidence/INTEG-044t/run.sh`=0（13 项全 rc=0 `EVIDENCE: PASS`）。

**ADR-0045 符合性**（核 QEMU 源 `.work/source/qemu/target/dadao/{cpu.h,cpu.c,helper.c}` + spec + contract-see）：两轴授权/self 仅绕 cfx 轴（`cfx_perm_denied` self→false，模式轴 HSJU 在 tlb_fill 独立检查）；cg0–3 rc0–4=cfxtrap/cfxmem/cfxreg/cfxexe/cfx_intr_mask；删 `global_version`/旧 `global_cfx_mask`（grep=空）；cfx0–3 cg8/rc1=`global_cfx_intr_mask`；初值 D4（DEFAULT=0x…FFF7 / HMON=0x7…FFF7 / 中断全1）；CFXPERM=1<<7 进当前 mode monitor、CFXESC=1<<3 进当前 cfx、原 0/1/2 保持；trap 自动保存+置全1 `global_cfx_intr_mask`、escape 恢复；reserved→ILLI；中断两级过滤（cfx_intr_mask + global_cfx_intr_mask）；escape cfxha=当前 cfx、返回 `cause_ip+(imm<<2)` 固定偏移。锁 sha 5 册重算并经 check-spec-readonly 校验。

**注入（reviewer 独立，非 run.sh 的 MASK_DEFAULT）**：改探针 `CFX_PERM 1<<7→1<<6`（cp 备份+md5=f369bc73…）⇒ cfxmem_deny/cfxreg_deny/cfxexe_deny 三例 `exp=0x40 got=0x80` FAIL rc=1；`cp` 还原 md5 一致 ⇒ 6/6 PASS rc=0。证明 CFXPERM 路由 case 可达 FAIL 且探针真实比对 QEMU 输出。全程 cp+md5，无 checkout/restore/stash。

**范围核验**：无 frame_active/异步重入/jmon(cfx1)/用户态测试实现；bootrom 改动（power→hmon→user）在任务书在范围内；快照对账 before==after 无遗留。

**遗留/给 architect（非阻塞）**：① 旧 `047t` 现 rc=1（`cfx63_user_vector` 因 bootrom 换 power→hmon→user 流程新增失败；`stack_in_ram0` 早已不一致）。它**本任务前就已排除**在 `ARCH_CFX_PROBES` 外（Makefile 注释源自 INTEG-042t），本任务未移除、非规避；但完成区披露偏软（未明说 047t 现 rc=1）。建议后续任务退役/重写 047t（其测的 power→user 旧引导流已被两轴模型取代）。② escape 帧错误分支单帧模型下不可独立观测，完成区已按 BLOCKED 如实登记、未造假绿。
