# m13-integ-007: Tiny hmon handler 改为「最小保存-跳转」算法（QEMU 先行验证）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-qemu-002`（Tiny 装载契约，已合入）、`m12-chipyard-019`（异常进 hmon + 寄存器语义，已合入）
**可并行分片**：否（共享 BootROM 固件单写者）
**状态**：待开始

## 用户裁定（2026-11-11，原话）

> 「hmon本身不应该产生退出码，hmon在测试环境下的代码应该是：保存两个临时寄存器，读取excp cause id/excp cause ip/excp cause info三个寄存器的内容，分别存储在hmon的sram的固定位置，然后从sram的另一固定位置取出异常返回地址（由测试框架程序事先写好），将其存入excp cause ip，然后恢复那两个临时寄存器，然后escape即可；余下的应该是测试框架程序要处理的事情。」
> 追加：「放在低地址；紧跟着代码区后面，8字节对齐」「只需要一个临时寄存器，rd63」「跳转到 0x30」「ld/st 支持负立即数」
> 归属：「这个hmon handler应该放在m13，用qemu先验证」

算法全貌见 `.tao/knowledge/refs/m12-006-cycle-design.md §11`。

## 背景

hmon handler 是**guest 代码**（BootROM 固件的一部分），三平台共用同一份镜像，与 RTL 无关。`m12-chipyard-019` 的版本带三处策略判断（magic 校验 park、IALIGN 改写、`escape +4`），按新裁定应全部删除，只保留「保存现场 + 跳到框架指定地址」。

**QEMU 先行**：先在 QEMU 上把算法跑通并固定为契约，再让 gem5/chipyard 跟随（避免三处各自发明）。

## 目标

1. **重写 `tests/shared/bootrom/tiny/hmon.S`**（**代码起点偏移 0，无 jump**）：
   - `st.o rd63, [rb0, off(0xD8)]`（保存 rd63）
   - `cfx2rd cg5 rc2/rc3/rc4` → 分别存 `0xE0/0xE8/0xF0`
   - `ld [0xF8]` → `cfx2rc cg5 rc3`（返回地址写入 `excp_cause_ip`）
   - `ld [0xD8]`（恢复 rd63）→ `escape cfx_hmon, [excp_cause_ip, 0]`
   - **删除**：magic 校验、IALIGN 特判、`+4` 策略、park 循环
2. **数据区固定在 `0xD8`–`0xFF`**：`0xD8` rd63 / `0xE0` cause_id / `0xE8` cause_ip / `0xF0` cause_info / `0xF8` 返回地址；**代码区必须 ≤ `0xD8`（216 B）**，构建器断言。
3. **`power.S`**：`trap cfx_hmon` 之前把默认返回地址写入 `hmon_base + 0xF8`（= `trap` 下一条）；**不改异常向量**（初值已指向 `0x00`）。power **只复制代码区**（表项 `size` = 代码长度），数据区保持 SRAM 初值。
4. **构建器**（`tools/testcases/arch/build_tiny_bootrom.py`）：强制 `data_base = 0xD8`、8 字节对齐、代码区 ≤0xD8、镜像仍恰好 64 KiB。
5. **QEMU 验证**（核心）：
   - 框架写 A 地址 ⇒ 异常后跳到 A；写 B ⇒ 跳 B（hmon 不做判断）
   - 三个现场值与 `cg5 rc2/rc3/rc4` 逐值相等（五类异常各 1 例）
   - `rd63` 异常前后相同（有保存/恢复，应用可自由使用）
   - `CFXTRAP` 移交闭环（power 的默认返回地址生效）
6. **同步断言**：`tests/arch/hmon/expected.yaml` 与 `tools/gem5/check_tiny_hmon.py` 中依赖旧行为（magic park / IALIGN 改写 / +4）的条目按新算法改写；「待 gem5/chipyard 跟随」的部分在完成区列清单。

## 非范围

- 不改 QEMU/gem5/chipyard 的 RTL/引擎（本任务只改 guest 固件与断言）
- 不做 `tests/inst` fault 类期望值迁移（另立任务）
- 不在本任务做 gem5/chipyard 的完整回归（只需给「如何跟随」的清单与命令）

## 验收标准

1. **算法逐条**：上述 6 步在 QEMU 上可观测（返回地址可被框架任意指定、三个现场值、`rd63` 恢复）
2. **删除项清零**：`grep` 无 magic 校验/park/IALIGN 特判/`+4` 策略残留（注释说明可留）
3. **镜像合规**：恰好 64 KiB；hmon 代码区 **≤0xD8（216 B）**、数据区固定在 `0xD8`–`0xFF`；power 只复制代码区（表项 `size` = 代码长度）
4. **QEMU 回归**：`check-inst` Tiny 44/44、`check-arch`/`check-arch-smoke` rc=0
5. **跟随清单**：给出 gem5（`check_tiny_hmon` 需要改的条目）与 chipyard（回归命令）的明确清单
6. 一键证据脚本（含可达 FAIL 注入：例如让 hmon 改成 `+4` 固定跳转 ⇒ 应 FAIL）
7. 完成区 ≤30 行、无运行期路径；**「修改文件」与 `git status` 对账**（`ISS-377`）

## 说明

- 必须在独立 `git worktree` 内作业（`ISS-368`）；**不要占用 207/208**（两个长跑在跑）。
- BootROM 固件是共享资产：本任务期间不得有其它任务改 `tests/shared/bootrom/**`、`tests/arch/hmon/**`。
- **QEMU 验证优先**：gem5/chipyard 的跟随若需要重构建/长门控，列清单交后续任务，不在本任务硬跑。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

（待填）
