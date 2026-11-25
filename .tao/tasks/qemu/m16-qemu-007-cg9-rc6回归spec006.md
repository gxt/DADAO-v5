# m16-qemu-007: QEMU `cg9 rc6` 回归 spec-006（写落地、进入取 rc6）

**模块**：qemu
**项目里程碑**：M16
**依赖**：`m18-spec-006`（已合入：`cg9 rc6` 复位 2、异步进入取该值）；`m16-qemu-006` 已合入（其 rc6「写忽略」实现与 spec-006 相反，由本任务回归）
**可并行分片**：否（`components/qemu` 单写者）
**预估**：1–1.5 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（用户 2026-11-25 在 `m18-spec-006` 裁定①）

`cg9 rc6`（`async_switch_run_mode`）口径统一为：**RW、复位 2（supv）、异步进入取该寄存器当前值**；QEMU/IDL 实现不动、RTL 后补（`m16-chipyard-028`）。

但 `m16-qemu-006` 按更早的 `ISS-m16-003`（当时按「固定 supv」理解）把 QEMU 改成了「写接受但忽略、读回恒 2、投递固定 supv」——**与 spec-006 相反**。本任务把它改回 spec-006 行为。

## 要做

1. `cfx2rc` 写 `cg9 rc6`（`helper.c` 的 `case 6` 路径）：`a->switch_run_mode = val & 0x3` **落地**（去掉 `switch_run_mode_write_ignored` 门控）；读回该值；复位 2。
2. 异步进入：`inner_run_mode = a->switch_run_mode & 0x3`（当前已有 `helper.c:3209` 路径，确认没被 qemu-006 改掉；若有硬编码 2 则改回取 rc6）。
3. 探针/期望：`arch-hart-001` 增加「写 rc6=0/1/3 后读回」「异步进入按 rc6 切换」断言（与 `m16-chipyard-028` 的 RTL 面同场景）；`DIV-18` 收窄/关闭（`close_when` = QEMU 回归 + RTL 028 + 用例断言）。
4. **不改** spec（spec-006 已是真源）、不改 RTL。

## 不做

- 不改 RTL（028）；
- 不改其它 `cg9` 槽语义。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出、`make_patch.py qemu` 幂等；
- 不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. 写 rc6=0/1/3 读回同值；复位 2；异步进入 `inner_run_mode == rc6`（含 rc6=0 进 user、rc6=2 进 supv 两条）；
2. 与 `m18-idl-002` 的 IDL 向量同场景一致（可只读对照，不在本任务改 IDL）；
3. **可达 FAIL ≥2**：注入"写忽略（恒 2）"、"进入硬编码 2" ⇒ 红；`cp`+md5 还原并重建回绿；
4. `check-patch-tree` qemu 段 0 problem、`check-component-changelog`、`check-knowledge-refs`、`run_arch --self-test` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
