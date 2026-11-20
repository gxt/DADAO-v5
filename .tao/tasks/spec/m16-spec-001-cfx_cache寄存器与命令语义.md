# m16-spec-001: `cfx_cache`（cfx5）寄存器与命令语义（A 方案：重定义 `cg8 rc9`）

**模块**：spec
**项目里程碑**：M16
**依赖**：无
**可并行分片**：否（改 `spec/` 与 `.tao/contracts/`）
**预估**：3–4 h
**档位**：大改（spec + 契约 + 测试机约定）
**状态**：待开始

## 用户已定口径（2026-11-20，不得自决）

- **重定义 `cg8 rc9`**（旧的 bit0/1/2 数值编码作废；`cfx5` 在 `contract-see` 里是「已分配未实现」，无实现依赖）；
- **选择位在 `[15:14]`**：bit15 = I-cache（1 选中）、bit14 = D-cache（1 选中）⇒ `11` = 全选；
- 操作与范围沿用 TLB 控制字的风格：`[1:0]` 操作、`[3:2]` 范围；
- **不加 ASID**（cache 以 PA 为键，非 VIVT）；
- **`invalidate` 丢弃脏数据不写警告**（DMA 场景这是正确操作）。

## 目标

1. **`spec/DADAO-12 §4.6 cfx_cache`**：
   - `cg8 rc0 cache_exist`（RO）：**bit0 = I、bit1 = D**，其余保留 0；
   - `cg8 rc8 cache_enable`（RW）：**bit0 = I、bit1 = D**，复位值 = exist；`exist=0` 的位置写 1 无效果（读回 0）；
   - `cg8 rc9 cache_ctrl`（WO）：`[1:0]` 操作 = `00=none/01=clean/10=invalidate/11=flush`；`[3:2]` 范围 = `00=all/01=PA 单行/10=PA 区间/11=reserved`；`[15:14]` 选择（bit15=I、bit14=D）；其余保留 0；
   - `cg8 rc10 cache_addr_start`（RW）：`PA[41:0]`；`cg8 rc11 cache_addr_size`（RW）：字节数；
2. **语义写死**：
   - `op=none` 或 `[15:14]=00` ⇒ no-op，且不检查范围编码与 `size`；
   - `scope=all` 忽略 start/size；`PA 单行` 只匹配包含 start 的行；`PA 区间` 匹配与 `[start, start+size)` 相交的行；
   - **I 侧**：`clean` = no-op；`invalidate` = 丢弃；`flush` = 等价 `invalidate`；
   - **D 侧**：`clean` = 写回并清 dirty；`invalidate` = 丢弃（脏数据丢失，**不写警告**）；`flush` = 写回后丢弃；
   - 两侧全选时判序 **I 表先、D 表后**；命令**同步完成**；
   - `cache_enable` 对应位 = 0 ⇒ 该侧命令 no-op；对不可缓存/MMIO 的 PA 无效果、不报异常；
   - **per-hart**；不改 `cfx_cache` 的异常表。
3. **新建 `.tao/contracts/contract-cache.md`**：按 `contract-tlb` 的体例（编号断言 + 来源标注 + 判序/失败语义），覆盖上述全部语义；
4. **`spec/Kaiwu-测试机运行环境.md`**：`cfx5` 从「已分配未实现」改为 **Vast 实现**（Tiny 不实现），补 `§3.x` 测试机约定（同步完成、per-hart、I/D 选择位与「I 先 D 后」）；
5. 版本号**不升**（`DADAO-12` 与 `Kaiwu` 均保持现值），只在各自变更记录加条目（用户认可后再升）。

## 验收（逐条贴真实 rc）

1. **交叉一致**：`DADAO-12 §4.6` 的寄存器表、`contract-cache.md` 的断言、`Kaiwu` 的实现范围三处**逐项对应**（寄存器名、位定义、语义），给一张对应表；
2. **旧编码已废**：全仓 `grep` 旧句「bit0=invalid icache」= 0；`contract-see` 里 `cfx5` 的「未实现」表述已改；
3. **门控**：`check-spec-changelog`、`check-spec-numbering`、`check-spec-purity`、`check-spec-refs`、`check-spec-codeblocks`、`check-manifests-guard`（`spec/` 与 `.tao/` 的 sha256 同步）、`check-contracts-dir`、`check-contract-relocs`、`check-knowledge-refs` 全 rc=0；
4. **可达 FAIL ≥2 路**（临时树/`cp`+md5）：① 删契约里一条断言的来源标注 ⇒ 对应门控红；② 把某一寄存器位定义改错（如 `[15:14]` 的 I/D 对调）⇒ 三处对应表核验红；
5. 补丁/清单纪律：`spec/.manifests.toml`、`.tao/.manifests.toml`（若需）同笔更新。

## 不在本任务范围

不实现 RTL / QEMU / gem5 的 `cfx5`（后续实现任务）；不动 `tests/arch` 的 cache 探针。

## 约束

独立 `git worktree`；不提交 git；术语「寄存器组」；完成区不写具体 `.work/**` 路径；**版本号不得自行升级**。
