# lessons 清理归档（2026-10-25）

> 背景：`MEMORY.md`/`lessons.md` 古老内容清理。删除条目须**事实已失效**（非"觉得没用"）；编号不复用，历史引用经 `lessons.md` 文末「旧号索引」解析。

## 已删除条目

### 1.28 停机协议迁移（exit-port → semihosting `SYS_EXIT`）
- **约定**：参数为 **64 位大端内存块** `{reason=0x20026, exit_code}`，**块指针在 `rb16`**（非旧寄存器习惯）、服务号 `rd16=0x18`、`trap cfx_umon, 0x30000`（`immu18[17:16]==2'b11` 判定，**与 `cfxha` 取值无关**）；**退出码在内存块第 2 字段**。
- harness 须**显式** `-semihosting-config enable=on,target=native`（否则 `SYS_EXIT` 不可达、host `$?` 不传播）。
- `-d cpu` 观测：`SYS_EXIT` 的 `trap` **不在 trap 前切 TB** ⇒ 若「读观测值的 `ld_o`」与 exit 序列同 TB，会观测到旧值；**修法**：exit 序列**前置一条 no-op `jump-iiii imms24=1`** 强制 TB 边界。
- **迁移类任务**须**先记改前基线**（逐条真实输出）**再对拍**；**范围 / 计数一律脚本枚举**（禁目测抽样）；默认全迁、例外逐条披露并登记 issue。

**删除理由**：`1.28` 描述的是「exit-port → semihosting `SYS_EXIT`」迁移；`exit port` 已随 `ADR-0020 D8` 删除、`dadao-m1` 服务已撤回，该迁移**不会再次发生**，
且 semihosting 协议细节已写入 `spec/Machine-01` 与 `QEMU-060t` 任务书。
