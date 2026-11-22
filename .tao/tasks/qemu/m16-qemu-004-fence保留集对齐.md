# m16-qemu-004: QEMU `fence` 保留 cfx 集对齐（ISS-432）

**模块**：qemu
**项目里程碑**：M16
**依赖**：`m16-qemu-001` 返工合入（同组件写者）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（用户 2026-11-22 选 A）

`ISS-432`（P2）：`fence` 的保留 cfx 集三平台不一致。真源 `Kaiwu §1.2` + `DADAO-12 §1` = **`6–14, 16–31, 35–61`**（`hb≠0` ⇒ `ILLI`）；实测 QEMU 是 **`6–14, 19–61`**（cfx16/17/18 放行、cfx32/33/34 报异常），chipyard/gem5 与 spec 一致。

## 要做

1. QEMU 的 `fence` 保留 cfx 集改为 `6–14, 16–31, 35–61`；`hb≠0` ⇒ `ILLI`。
2. 保留集边界与 `cfx0`/`cfx_umon`=all、`cfx1–63` 指定、六位资源域的现有语义不变。
3. 探针采样：cfx16/17/18（应 `ILLI`）、cfx32/33/34（应放行）、6–14 与 35–61 边界各 1；与 chipyard/gem5 一致。
4. 关闭 `ISS-432`（`issues.yaml`：`status: closed`、`resolved_by: m16-qemu-004`）。

## 不做

- 不改 fence 的六位语义/屏障实现；
- 不改 chipyard/gem5（它们已与 spec 一致）；
- 不写完整 fence 用例（由 `m16-testcases-012`）。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py qemu` 幂等；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. 保留集探针：cfx16/17/18 ⇒ `ILLI`；cfx32/33/34 ⇒ 放行；边界 cfx14/15/31/32/35/61 逐条；
2. 与 chipyard/gem5 的同组探针结果一致；
3. **可达 FAIL**：注入「保留集仍 19–61」⇒ 探针红；`cp`+md5 还原后回绿；
4. `check-patch-tree` qemu 段 0 problem、`check-index-blobs`、`check-tasks`、`check-issues` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
