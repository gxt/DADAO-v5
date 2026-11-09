# m12-spec-002: Tiny 引入 `cfx_power` + `cfx3 hmon`（规范修订）

**模块**：spec
**项目里程碑**：M12
**依赖**：无（**M12 的 `007` 与 M13 的 `m13-qemu-001`/`m13-gem5-001` 共同前置**）
**可并行分片**：否（单册修订）
**状态**：待开始

## 用户裁定（2026-11-09）

- **Tiny 实现 `cfx_power`（cfx63）+ `cfx3 hmon`**（决策 1 = B）
- hmon SRAM **复用 `0x0fff_0000_0000`**（64 KiB，决策 2 = A）；**无 PTW/页表**（决策 3 = A）
- **同步异常不经 `trap` 指令**，直接进 hmon 向量；与 semihosting 的 `trap` 无冲突
- **Tiny 的 semihosting `trap` 统一写 `trap cfx_hmon`**；实现只看 `immu18`，不判断 cfxha
- `trap` 判定：`immu18 ∈ 0x3FF00–0x3FFFF` ⇒ semihosting；`cfxha=3` + 其它 `immu18` ⇒ 进 hmon
- **IALIGN 时 IP 停留在非法地址**（`DADAO-12 §5`）

## 目标（`spec/Machine-v5-测试机运行环境.md`）

1. **cfx 实现范围**：Tiny 从「不实现任何 cfx（含 `cfx_power`）」改为「实现 `cfx_power`（启动）+ `cfx3 hmon`（异常）」；仍不实现 smon、不实现 PTW。
2. **地址图（§1.1）**：Tiny 增加 hmon SRAM `0x0fff_0000_0000`（64 KiB，cfxha 3）；说明与 BootROM/SRAM（cfxha 63）的并存关系，以及 `addr[47:42]` 不再是「恒 0x3F」。
3. **运行模式（§2）**：Tiny 的异常承载改为「同步异常进 hmon 向量」；启动链改为 `power → hmon → 测试本体`。
4. **异常（§1.2/§4）**：Tiny 的 `CFXMEM`/`ILLI`/`UNDI`/`MALIGN`/`IALIGN` 进 hmon 的时机与 `excp_cause`；**IALIGN 时 IP 停留在非法地址**。
5. **semihosting（§5.1）**：`trap` 判定规则（`immu18` 区间 vs cfxha）；示例统一写 `trap cfx_hmon`。
6. **版本**：`0.4.1-rc` → 新段（`0.4.2-rc` 或按变更记录体例），同笔更新只读锁。

## 验收标准

1. `make check-spec-readonly` rc=0（锁同笔）
2. `make check-spec-changelog` rc=0（新段在首、册头一致）
3. `make check-spec-drift` / `check-spec-numbering` / `check-spec-refs` rc=0
4. 文中不再有「Tiny 不实现任何 cfx / 无 hmon / fault 直接映射退出码」的旧表述（逐处核）
5. 与 `contract-see` / `contract-isa` 的相关约束一致（如有冲突，列出并说明）
6. `make check`（L1）rc=0
7. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
8. 完成区 ≤30 行、无运行期路径

## 非范围

- 不改 `DADAO-12`/`DADAO-13`（上游册；若需同步，另立或说明）
- 不改任何实现（QEMU/gem5/chipyard 各自任务）
- 不改已 Accepted 的 ADR
