# INTEG-044t: CFX 两轴权限模型落地

**模块**：integ
**项目里程碑**：M10
**依赖**：ADR-0045（权限）、ADR-0039/0040/0042
**状态**：待开始

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

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
