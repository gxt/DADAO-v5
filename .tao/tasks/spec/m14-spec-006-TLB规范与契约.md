# m14-spec-006: K3 的 TLB 规范与契约（只定义，不实现）

**模块**：spec
**项目里程碑**：M14
**依赖**：`ADR-0052 D6`（K3 第一步先定义 TLB、第二步才实现）；用户 2026-11-16 三条口径（同步完成 / per-hart / M14 只做 QEMU + `tests/arch` 探针）
**可并行分片**：否（spec + 契约 + 锁，单写者）
**预估**：3–4 h
**档位**：大改（新建契约 + v5 册撤销「不定义」声明 + 锁重算；复核 ≥4 路注入）
**状态**：待开始

## 背景

上游 `DADAO-12` 已把 TLB 写得很细（本任务**收编**，不重写）：

- `§2.2.1`/`§2.2.2`：匹配键 = 虚拟页 + ASID（`G=1` 跨 ASID）、命中不重读 PTE、命中用条目里的 SPF/GPF + HSJU + R/W/X 检查、**只有步进成功才 fill**（缺页/权限失败不填充、不更新 A/D）、替换策略与容量**实现定义**；
- `§2.2.5`：写 PTBR / ASID / `ptw_enable=1` **不隐含 invalidate**；
- `§2.2.6`：异常检查优先级；
- `§4.5`：A/D local/dirty 状态机 + **原子 OR 回写**（失败 ⇒ 当前 monitor `CFXMEM`）；**`cfx_ptw_tlb_control`** 三维正交（操作 `[1:0]` = none/clean/invalid/flush、范围 `[3:2]` = all/VA/range、`bit4` = `ASID_ANY`）、判序（先操作后范围）、`none` 无条件 no-op、`clean` 回写保条目、`invalid` 只删、`flush` 回写后删（**回写失败不删**）、`ASID_ANY=0` **不碰 `G` 条目**、非法编码 ⇒ `CFXREG`。

但 v5 侧现状：

- `spec/Kaiwu §7` 显式写「本节**不定义**：TLB 填充/失效/ASID、cache/LLC、…」⇒ 与上游矛盾，K3 必须先撤；
- 无 TLB 契约（`.tao/contracts/` 只有 see/semihosting/syscall/…），实现与测试无归一化投影可依；
- 用户已定三条口径（`discussing.md` §K3 的 TLB）：**同步完成**、**per-hart（单 hart）**、**M14 只做 QEMU + `tests/arch` 探针**。

## 目标

1. **撤销 v5 的「不定义」**：`spec/Kaiwu §7` 那句里的 TLB 部分改为指向 `DADAO-12 §2.2.1–§2.2.6`、`§4.5`；并在 `§3`（cfx 实现范围 / Vast 段）或 `§7` 补三条 v5 约定：
   - **`tlb_control` 写指令同步完成**（返回即生效，后续访存必见）；`clean`/`flush` 的回写失败**在该写指令上**报 `CFXMEM`，且**不得部分完成**（`flush` 失败不删条目、`clean` 失败不清挂起位）；
   - **per-hart**：`tlb_control` 只作用本 hart；跨 hart 一致性**不在本版范围**（`ISS-459`）；
   - **实现范围**：v5 侧 TLB 由 **QEMU** 承担建模；chipyard/gem5 不在本阶段验收面（`tests/arch` 探针为跨实现判据）。
2. **新建 `.tao/contracts/contract-tlb.md`**（归一化投影，不复制上游正文）：逐条收编上列上游语义（匹配键 / 命中检查 / fill 条件 / A-D 状态机与原子 OR 回写 / `tlb_control` 三维与判序 / 三操作语义 / 范围三档 / `ASID_ANY` 与 `G` / 异常路由），**每条带 `[DADAO-12 §…]` 来源**；三条 v5 约定标 `[spec-decision]`（用户 2026-11-16）。
   - **版本**：`contract-tlb` 映射 `DADAO-12` ⇒ 按 `check-spec-drift` 规则版本须等于 `.tao/contracts/README.md` 的 **SEE / SBI 已发布版（`0.7.1`）**；
   - 同笔在 `.tao/contracts/README.md` 表里加一行（`contract-tlb.md` | TLB 与失效接口合约（K3；0.7.1））。
3. **补「缺页/fault 路径」的契约口径（K3 扩展范围所需）**：用户 2026-11-16 裁定「K3：做（按需分页/COW/栈增长），简单验证即可」⇒ 契约需明确：
   - **未映射 / 权限拒绝 / A-D 回写失败** 三类 fault 的 `cause_info` 语义（`CFXMEM` 的 `info` = 访存地址；`CFXPERM` 的 `info` 口径），供内核 page fault handler 区分"缺页/COW/越权"；
   - **软件改 PTE 后的责任**：改 PTE（或写 PTBR/ASID/`ptw_enable`）**不隐含 invalidate** ⇒ 内核必须写 `tlb_control`（`invalid` 或 `flush`）；写明推荐的组合（如 COW 用 `invalid`+`VA`）；
   - **不引入新寄存器/新异常**：按需分页与 COW 全部用既有 fault + `tlb_control` 表达。
3. **门控设计（只设计，不实现）**：在契约里给出「门控建议」小节 —— `tests/arch` 8 条探针（fill+命中 / 命中不重读 PTE / `invalid`+VA / `invalid`+range / `ASID_ANY` 与 `G` / `clean` 回写 A/D vs `invalid` 不回写 / `flush` 回写+删除、回写失败 ⇒ `CFXMEM` 且不删 / 写 PTBR·ASID·`ptw_enable` 不隐含 invalidate），并注明载体形态（`tests/arch/umon/*.s` + `expected.yaml`，需自建页表的走 `min_rom_probe` 并登记 `ARCH_CFX_PROBES`）。**另加 3 条与 K3 扩展范围对应的探针**：⑨ 未映射访问 ⇒ `CFXMEM` 且 `cause_info` == 访存地址（供缺页判定）；⑩ 权限拒绝 ⇒ `CFXPERM`（与 `CFXMEM` 可区分）；⑪ 改 PTE 后**不** invalidate ⇒ 仍命中旧条目、写 `invalid`+`VA` 后 ⇒ 命中新 PTE（COW 的最小闭环）。
4. **锁**：`spec/Kaiwu-…` sha256 同笔重算 + 注记（用户原话「目前只考虑单hart情况」「M14只考虑qemu；但应该在tests/arch中增加这部分的测试」「这本身是一条指令…可以写完等生效才返回」）。

## 验收（真实 rc + 输出）

1. `grep -n "不定义" spec/Kaiwu-…md` ⇒ TLB **不再**出现在「不定义」列表；`grep -c "DADAO-12 §2.2"` 命中 ≥1、`§4.5` 命中 ≥1；
2. 契约：条目数现场统计（≥12 条），**每条**有来源标注；`grep -c "spec-decision"` == 3（三条 v5 约定）；`contract-tlb` 版本 == README 表 `SEE / SBI` 已发布版；
3. 门控：`check-contracts-dir`、`check-contracts-pending`（无待定标记）、`check-contract-relocs`、`check-spec-refs`、`check-rule-refs`、`check-spec-drift`、`check-spec-purity`、`check-spec-changelog`、`check-spec-readonly`（Kaiwu 重算后 21 册 OK）、`check-knowledge-refs`、`check-dirs`、L1 `make check` 全绿；
4. **≥4 路注入**（`cp`+md5 还原）：① 把 `contract-tlb` 版本改成 `0.7.2` ⇒ `check-spec-drift` 红；② 契约里某条来源改成不存在的 `§9.9` ⇒ `check-spec-refs` 红；③ 把「不定义」句里的 TLB 加回去 ⇒ 判据 1 红；④ 锁 sha 改 1 字符 ⇒ `check-spec-readonly` 红；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **只定义、不实现**：不改 `components/qemu`、不改 `tests/arch`（探针实现归下一件任务）；
- **不复制上游正文**：契约只做归一化 + 指针（`docs/Process-02`）；
- 不改 `.tao/archive/**`、`.tao/adr/**`；
- 不提交 git；注入还原 `cp`+md5。

## 审阅记录

（待填）
