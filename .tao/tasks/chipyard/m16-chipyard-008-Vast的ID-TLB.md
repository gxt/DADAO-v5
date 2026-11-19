# m16-chipyard-008: Kaiwu-Vast 的 I/D TLB（2 组×8 路 + 4 超页）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m17-chipyard-002`（PTW 两级步查）
**可并行分片**：否（改 `dadao-wuming` 核）
**预估**：1–2 天
**档位**：大改
**状态**：待开始

## 用户已定口径（2026-11-19，必须遵守）

- **只设一级 TLB，分 I/D**——I/D 分离是**设计**，不是实现细节；可直接参考 rocket 的 `TLB.scala`（其 `instruction` 参数决定条目是否带 dirty 位：**I-TLB 无 D 位**，只置 A）。
- **普通页：16 条 = 2 组 × 8 路，不设 sectored**（rocket 的 `nSectors=1` 即等价）。
- **超页：4 条全相联 + LRU**（rocket 的 `superpage_entries` + `SetAssocLRU`/`PseudoLRU`，把 PLRU 换 LRU）。
- **无特殊条目**（rocket 的 special entry 是为跨 PMP 区，DADAO 无 PMP）。
- **gem5 侧保持统一**（含组相联设置与超页个数）⇒ 由 `m17-gem5-001` 同步。

## 参考实现形态（BOOM/rocket，主会话 2026-11-19 调研）

- **TLB 在核内**、**PTW 在 tile 级（每核一个）**：BOOM 在 `v3/ifu/frontend.scala` 与 `v3/lsu/lsu.scala` 各 `new TLB(...)`；PTW 在 `v3/common/tile.scala` `Module(new PTW(ptwPorts.length)(...))`，`ptwPorts = ListBuffer(lsu.io.ptw, frontend.io.ptw, core.io.ptw_tlb)`。
- **类跨核复用、实例每核一份**（不是 SoC 共享）。
- PTW 的页表访存走**数据侧 cache 端口**（`HellaCacheIO` / `heccachePorts`）。
- ⇒ DADAO 按同构分工：**TLB 核内、PTW tile 级**；接口 = 「多条 PTW 请求端口 + 异常回传」。
- **待裁定**：PTW 的页表读在 DADAO 是否经 D-Cache（`DADAO-12 §2.2` 只规定用物理地址、不规定是否过 cache）——RTL 与 gem5 必须一致。


> **暂停（用户 2026-11-19）：`WumingVast` 不做，转 `wuqing` 路线**——本任务（基于 Wuming 的 Vast RT��）暂不开工；其 **PTW/TLB 的核无关部分**在重启时按「独立模块 + 核适配层」重写，`cfx_ptw` 寄存器面可复用 `m16-chipyard-006` 的成果。

## 目标

1. **I-TLB / D-TLB 各一套**：普通页 `2×8`、超页 `4` 条全相联；**I 侧无 dirty 位**；
2. **命中路径**（`§2.2` 第二步）：VA 覆盖 + (`G=1` 跨 ASID / `G=0` 比 `cfx_ptw_tlb_asid`）→ 按 `§2.2.6` 优先级判 `frags`（⇒`CFXMEM`）→ HSJU → `R/W/X`（⇒`CFXPERM`）；**命中不重读 PTE**；
3. **未命中**：向 PTW 发请求（`002` 的接口），回填并置 LRU；**淘汰前先回写脏 A/D**（失败 ⇒ `CFXMEM+ADWBFAIL`、条目保留）；
4. **`cfx_ptw_tlb_control` 双表失效**：spec 视角是**单一 TLB**（没有 I/D 选择位）⇒ 一次写命令**必须同时作用于两表**；`asidAny=0` 时跳过 `G=1` 条目；`clean`/`invalid` **条目级 + 遇错即停**（`TLB-37`）；
5. **A/D 合并**：同一 PTE 可能在 I、D 两表中各有本地位 ⇒ **回写按 OR 语义合并到 PTE**，且两表的「失败保留」各自成立；
6. **`PTBR`/`ASID`/`ptw_enable` 写入不隐含失效**（`§2.2` 明文），必须由软件显式 `invalid`。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. **对拍**：`002` 的「无 TLB」配置与本任务「有 TLB」配置跑同一批用例 ⇒ **结果逐条一致**（这是验证 TLB 正确性最有力的手段；不一致即红）；
2. **组相联冲突**：构造两个落在同 set（`VA[16]` 相同）的页交替访问 ⇒ 能观察到互相淘汰并各自重新步查（用 `cfx_hart` 的 insn/cycle 或探针计数现场统计，不写死）；
3. **超页 4 条**：5 个不同 512 MiB 超页交替访问 ⇒ 必有淘汰+步查，且结果正确；
4. **I 无 D 位**：对 I-TLB 条目做 store 不改变其 A/D 状态（结构性断言：I 侧条目无 D 位）；
5. **双表失效**：`scope=全表` 后两表皆空（用「失效后首次访问必步查」证明）；`scope=单 VA` 只清该 VA；`asidAny=0` 时 `G=1` 条目存活；
6. **A/D OR 合并**：I 表置 A、D 表置 A+D，`clean` 后 PTE 的 A/D 同时被写回；构造 I 写回成功、D 写回失败 ⇒ 失败侧条目保留、异常只报一处；
7. ≥3 路注入（① set index 取错位 ⇒ 冲突用例红；② 双表只清一侧 ⇒ 失效用例红；③ 回写覆盖而非 OR ⇒ A/D 合并用例红），`cp`+md5 还原 + 重建回绿。

## 待裁定

（无。I/D 分离、容量、替换策略、双表失效与 A/D 合并均已由用户 2026-11-19 裁定；若实现中发现 spec 缺口，登记「待裁定」并**不改 spec**。）

## 完成区

（待填）
