# SPEC-189t: DADAO-12 跨节异常原因表同步

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-186t`（§5.2 A/A1 模型定稿）、`SPEC-188t`（rc9/cg5 rc1 寄存器定义删除；同改 DADAO-12，须串行）
**状态**：待开始

## 执行环境
本地；只改 SPEC/合约的异常原因表与路由，不改 QEMU/gem5/tests 实现。

## 背景

`SPEC-186t` 只改 `§5.2`+`§1`；以下跨节仍写旧模型：

- `DADAO-12 §2.2.6`：页表异常“都进入 `cfx_ptw`”；原因名 `IGPTRAP`/`DGPTRAP`/`NUPERM`/`NJPERM`/`NSPERM`/`NHPERM`/`NXPERM`/`NWPERM`/`NRPERM`
- `DADAO-12 §3.6`：`1 << 7` 在 `cfx_ptw` 为 `PTWERR`
- `DADAO-12 §4.5` 原因表：`PTWERR` + `NUPERM`…`NRPERM` + `IGPTRAP`…`DSPFTRAP`
- `DADAO-22 §5.3`：A/D 回写失败报 `cfx_ptw` 的 `PTWERR`
- `Machine-v5`：`NUPERM` 等 PTW 权限层、`PTWERR` 旧描述
- `contract-see`：页表异常进入 `cfx_ptw`、A/D 回写失败报 `PTWERR`

这与 `§5.2` 的“执行期事件先入当前 monitor”冲突。

## 目标（与 §5.2/A1 一致）

1. 页表异常统一按当前 monitor 路由，原因收敛为：
   - `ptw_enable = 0`、`P = 0`、SPF/GPF 缺失、fragment 缺失、A/D 回写失败 ⇒ `CFXMEM`（当前 monitor）
   - HSJU 不符、R/W/X 不符 ⇒ `CFXPERM`（当前 monitor）
   - 取指/读写不再区分 `IGPTRAP`…/`NUPERM`…；`cause_info` 保留访存地址（A/D 回写失败用 PTE 物理地址）
2. `§4.5 cfx_ptw` 原因表只保留 cfx_ptw 自身可处理的显式原因（`CFXTRAP`、`CFXESC`）；删除 `PTWERR`/`NUPERM`…/页表缺失类原因。
3. `§3.6`：`1 << 7` 在 `cfx_ptw` 标 reserved；不再写 `PTWERR`。
4. `DADAO-22 §5.3`、`Machine-v5`、`contract-see` 同步：A/D 回写失败 ⇒ `CFXMEM` 当前 monitor；页表异常 ⇒ 当前 monitor；删除 `PTWERR`/`NUPERM` 旧口径。
5. 同笔重算 `dadao-12`/`dadao-22`/`machine-v5` 锁 sha；其它册不变。

## 接口规范

### 1. `DADAO-12 §2.2.6`

- 保留优先级顺序：IALIGN → ILLI/UNDI → MALIGN → 页表异常。
- 页表内部优先级保留：`ptw_enable=0` → L1 P/SP → SPF/GPF → L2 → HSJU → R/W/X。
- 原因名改为：前 5 类缺失/回写失败 ⇒ `CFXMEM`；HSJU/R/W/X ⇒ `CFXPERM`。
- 删除“取指 I 前缀/数据 D 前缀”原因名与“进入 cfx_ptw”句；改为“进入当前运行模式 monitor”。
- 不改变“只报最高优先级”规则。

### 2. `DADAO-12 §3.6`

- `1 << 7`：`cfx0`–`cfx3` 仍为 `CFXPERM`；`cfx_ptw` 标 reserved。
- 删除 `PTWERR`；其余位说明不动。

### 3. `DADAO-12 §4.5`

- 原因表删除 `PTWERR`（1<<7）与 `NUPERM`…`NRPERM`（1<<8–14）、`IGPTRAP`…`DSPFTRAP`（1<<16–23）。
- 保留 `CFXTRAP`（0）、`CFXESC`（3）；`CFXREG`（2）是否保留按“CFXREG 统一当前 monitor”删除。
- A/D 回写失败正文改为“按 `CFXMEM` 进入当前 monitor，`cause_info` = PTE 物理地址；失败条目保留”。
- 不改 TLB 寄存器表/命令语义。

### 4. `DADAO-22 §5.3`

- 标题与正文改为“A/D 回写失败（CFXMEM）”：`clean`/`flush` 失败保留条目，`excp_cause_info` = PTE 物理地址，进入当前 monitor 的 `CFXMEM`；不再提 `PTWERR`。

### 5. `Machine-v5` / `contract-see`

- 删除 `NUPERM`/`NJPERM`/`NSPERM`/`NHPERM` 与 `PTWERR` 旧描述；改为 `CFXPERM`/`CFXMEM` 当前 monitor。
- 保留“PTW 层权限”与“cfx 访问权限”区分的**结论**，但原因名改为 `CFXPERM`；不得把两者混同。

### 6. 锁

- 仅 `dadao-12`/`dadao-22`/`machine-v5` 重算；注记含日期 + 授权原话指针 + 改动摘要。

## 范围 / 非范围

**在范围内**：`spec/DADAO-12-*`（仅 §2.2.6/§3.6/§4.5 + 变更记录）、`spec/DADAO-22-*`（仅 §5.3 + 变更记录）、`spec/Machine-v5-*`（仅 PTW 权限/PTWERR 句）、`.tao/contracts/contract-see.md`、`manifests/spec-readonly.lock.toml`、本任务书、`milestones.md`、`ISS-344` 关闭。

**不在范围内**：`SPEC-186t` 的 §5.2/§1；`SPEC-188t` 的 rc9/cg5 rc1；QEMU/gem5/tests/LLVM；`contracts/` 机器数据；`Makefile`；门控脚本；退出码表（`SPEC-187t`）。

## 验收标准

1. **活文件清零**：`PTWERR`、`NUPERM`、`NJPERM`、`NSPERM`、`NHPERM`、`NXPERM`、`NWPERM`、`NRPERM`、`IGPTRAP`、`ISPTRAP`、`IGPFTRAP`、`ISPFTRAP`、`DGPTRAP`、`DSPTRAP`、`DGPFTRAP`、`DSPFTRAP` 在 DADAO-12/22/Machine-v5/contract-see 活文件 0 命中（历史段除外）。
2. **路由一致**：页表缺失/A/D → `CFXMEM` 当前 monitor；HSJU/R/W/X → `CFXPERM` 当前 monitor；`cfx_ptw` 不再是页表异常目标。
3. **原因表**：`§4.5` 仅保留 cfx_ptw 显式原因；`§3.6` 1<<7 在 cfx_ptw reserved；无 `PTWERR`。
4. **contract/Machine-v5**：A/D 回写失败、页表异常口径与 DADAO-12 一致；“两层权限”结论保留、原因名更新。
5. **锁**：三册 sha 与 `sha256sum` 逐字相等；其它册不变。
6. **门控**：`check-spec-readonly/refs/drift/changelog/numbering/purity/cite-targets/codeblocks`、`check-contracts-dir`、`check-contract-relocs`、`check-issues`、`check-milestones-fresh`、`make check`（L1）rc=0。
7. **反例可达 FAIL**：把 `PTWERR` 写回一处 ⇒ 断言 FAIL；`cp`+`md5sum -c` 还原后回绿。
8. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- 本任务只做 SPEC/合约；QEMU/gem5/tests 的页表异常原因、`PTWERR`、`NUPERM` 实现与期望值由后续实现任务处理。
- `§4.5` 删除大量原因后，`cfx_ptw` 的异常表可能只剩 `CFXTRAP`/`CFXESC`；若现场发现 cfx_ptw 仍需处理某类内部故障，先留问，不自行新增。
- 顺序：`SPEC-186t → SPEC-188t → SPEC-189t → SPEC-187t（退出码）`；`SPEC-188t/189t` 同改 DADAO-12，严格串行。

## 未决（下发前确认）

1. `§4.5` 是否保留 `CFXREG`（按“CFXREG 当前 monitor”默认删除）。
2. `Machine-v5` 的 PTW 权限段是否整段重写，还是只改原因名；默认只改原因名与 `PTWERR`。
3. QEMU/gem5/tests 实现任务是否本任务完成后按影响创建；默认是。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
