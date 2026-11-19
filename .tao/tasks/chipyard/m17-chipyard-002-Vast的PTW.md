# m17-chipyard-002: Kaiwu-Vast 的 PTW（两级步查 + A/D）

**模块**：chipyard
**项目里程碑**：M17
**依赖**：`m17-chipyard-001`（核参数与地址通路、`cfx_ptw` 寄存器面）
**可并行分片**：否（改 `dadao-wuming` 核 + 新增 PTW 模块）
**预估**：2–3 天
**档位**：大改
**状态**：待开始

## 背景与真源

DADAO 的页表是**两级、64 KiB 页**：`L1 索引 = VA[41:29]`、`L2 索引 = VA[28:16]`、页内 `[15:0]`；512 MiB **超页**在 L1 直接出（`SPF`）。PTE 为 **8 字节大端**，权限在 `[63:60]` 的 **HSJU**（H=63/S=62/J=61/U=60），另有 `frags[8]` 分片存在位、`R/W/X`、`A/D`。真源：`spec/DADAO-12 §2.2.1–§2.2.6`、`§4.5`；契约 `.tao/contracts/contract-tlb.md`（TLB-01…TLB-43）、`ADR-0040`（PTE/走查）、`ADR-0041`（TLB/A-D）、`ADR-0056`（子原因编码）。

**可参考**：rocket `PTW.scala` 的状态机骨架与多请求仲裁（`Vec(n, TLBPTWIO)`）——但 PTE 格式、权限位、异常码、A/D 语义**全部要重写**（见任务书模板中的「不能复用」清单，转抄自调研结论见 `discussing.md` 的 Vast 节）。

## 目标

1. **两级步查器**：按 `PTBR`（PA）+ 索引读 PTE；页表访问**走物理地址、不经 TLB**，且必须在 RAM/ROM 范围内（否则按 `CFXMEM` 处理，具体按 `§2.2` 核对）；
2. **PTE 解析**：`SPF`/`GPF`、HSJU、`R/W/X`、`frags`、`A/D`；超页（512 MiB）在 L1 直接结束走查；
3. **A/D 本地化 + 回写**：`A` 由取指/load 置位、`D` 由 store 置位；**淘汰/`clean`/`flush` 时回写 PTE**；回写失败 ⇒ `CFXMEM + [56] ADWBFAIL`，`cause_info` = **PTE 物理地址**，失败条目保留；
4. **异常**：未映射/分片缺失 ⇒ `CFXMEM`；HSJU 或 `R/W/X` 不符 ⇒ `CFXPERM`；均进**当前运行模式 monitor**（`§5.2`）；子原因位号从契约取，不写死；
5. **`cfx_ptw` 的执行语义**：`tlb_control` 写即执行（`op`/`scope`/`asidAny`）、`clean`/`invalid` 的**条目级 + 遇错即停**（`TLB-37`）；TLB 侧归 `003`，本任务先让命令在 PTW 侧可解析、可返回错误；
6. **不做 TLB**：本任务每次访存都步查（功能正确性优先），`003` 再加 TLB 并做「有 TLB vs 无 TLB」对拍。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `make verilog CONFIG=WumingVastConfig` 能 elaborate、能跑最小镜像（1 页映射 + 取指/读写）；
2. **超页用例**：512 MiB 超页映射下访问页内多个 64 KiB 子页均命中；跨超页边界访问未映射 ⇒ `CFXMEM`；
3. **权限用例**：HSJU 不符 ⇒ `CFXPERM`；`R/W/X` 缺失分别给对应子原因（`NRPERM`/`NWPERM`/`NXPERM`，位号取自契约）；
4. **分片用例**：`frags` 某位为 0 的 64 KiB 页访问 ⇒ `CFXMEM` + 对应分片子原因；
5. **A/D 用例**：首次取指置 A、首次 store 置 A+D；`clean` 后 PTE 的 A/D 被写回；**回写失败**（页表放 BootROM 只读区）⇒ `CFXMEM + ADWBFAIL` 且 `cause_info == PTE PA`；
6. ≥3 路注入（① 索引位宽写错 ⇒ 用例红；② A/D 只置本地不回写 ⇒ clean 用例红；③ 回写失败静默丢弃 ⇒ 用例红），`cp`+md5 还原 + 重建回绿；
7. 与 gem5 对拍：同一镜像在 gem5 `--profile vast` 与 RTL 上**逐指令 trace 一致**（至少覆盖上述 2–5 的用例）。

## 待裁定

（无。PTE 布局/权限/异常码/回写语义均由 spec 与契约钉死；若实现中发现 spec 缺口，登记「待裁定」并**不改 spec**。）

## 完成区

（待填）
