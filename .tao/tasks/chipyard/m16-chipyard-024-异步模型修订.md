# m16-chipyard-024: RTL 异步模型修订（cg9 七槽 + 掩码归 monitor + 源位图）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m18-spec-004`（spec/契约落地）合入；`m16-chipyard-021` 已合入（在其 cg9 上改）
**可并行分片**：否（同改 `components/chipyard`）
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景

`ADR-0061` 修订异步模型：来源掩码归 monitor、源身份统一 cfxha、`cg9` 精简 7 槽、两个位图软件只读、帧由 `escape` 结束。`m16-chipyard-021` 已实现 `cg8` + 16 槽 `cg9`（含 5 个掩码、cause id 17、`saved_global_intr_mask`），本任务把它改到新模型。

## 要做

1. **`cg9` 改 7 槽**（`DADAO-12 §4.7`）：
   - `rc0 prev_run_mode`、`rc1 prev_cfx`、`rc2 cause_ip`（= 提交后的 `rb0`）、`rc3 src_frame`（64b，**HW/RO**，位 = 源 cfxha，非 0 = 有效帧）、`rc4 src_pending`（64b，**HW/RO**，位 = 源 cfxha）、`rc5 excp_vector`、`rc6 switch_run_mode`（固定 supv=2）；`rc7–15` reserved ⇒ `CFXREG`。
   - 删除原 `rc3 cause_id` 的 17/18 语义、`rc4 saved_global_intr_mask`、`rc8–rc12` 五个掩码。
   - 读写属性按 `m18-spec-004` 落地结果：`src_frame`/`src_pending` 为 **HW/RO，软件写忽略、读回不变、不产生异常**（与 cycle/insn 的"写 ⇒ `CFXREG`"不同）。
2. **来源掩码移 monitor**：`cfx0`/`cfx1`/`cfx2`/`cfx3` 的 `cg8 rc1` 实现为"本运行模式异步来源掩码"（位 = 源 cfxha，复位全 1，`0=允许`/`1=屏蔽`）；投递时按 `inner_run_mode` 选行求值。删除 `cfx_hart` 侧掩码相关逻辑。
3. **仲裁**：同一指令边界把**所有** `pending && !masked` 的源一次性投进一帧：`src_frame` = 这些位的并集、`src_pending` 扣除这些位、`excp_async_num` +1；`src_frame != 0` 时新事件只置 pending（无嵌套）；**不要**逐源循环投递。
4. **pending 跟随源事件**：投递即清位；源被 ack（`timer_cmp` 重装 / `dma_status` W1C）后 pending 自动落；软件不写。
5. **`escape`**：保留 `imms18[1]` 帧选择位与 `{0,1,2}`/`3⇒ILLI`；`cg9` 帧有效 = `src_frame != 0`；合法返回时清 `src_frame`（释放），不改 `escape` 编码。
6. **探针**：`tests/arch/hart/cfx15.S` + `check_cfx15.py` 改到新模型（掩码写 hmon/smon/umon 的 `cg8 rc1` 放行 bit15、7 槽逐项、`src_pending`/`src_frame` 只读、ack 后 pending 落）；H/S/U 三模式。
7. **不回归**：Tiny 无 cfx15 不变；cfx3/4/5 既有语义与 020 的两轴判权不变。

## 不做

- 不做 cfx32/34（022/023）；
- 不改 `escape` 编码与工具链；
- 不改 QEMU/KERNEL/gem5。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；**失败路径短 timeout、禁长时间 `-d cpu` dump**（ISS-522）；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. `cg9` 7 槽读写/保留（`rc7–15` ⇒ `CFXREG`）；`src_frame`/`src_pending` 只读行为符合 spec；
2. hmon/smon/umon 三模式各写自己的 `cg8 rc1` 放行 bit15 ⇒ TIMER 投 `cfx_hart`/supv；屏蔽 ⇒ 只置 pending、解除后投递；
3. `src_frame` 位 = 源 cfxha（15）、pending 同索引；ack 源（重装 `timer_cmp`）后 pending 落；
4. `escape imms18=2` 返回并释放；`3`/`[17:2]≠0` ⇒ `ILLI`；
5. **可达 FAIL ≥2**：注入"掩码留在 cfx_hart"或"pending 位记 17" ⇒ 红；`cp`+md5 还原并强制重建回绿；
6. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
