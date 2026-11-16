# m14-spec-007: `cause_id` 子原因编码落地（`DADAO-12` 三处 + `contract-see §6.1` 扩列）

**模块**：spec
**项目里程碑**：M14
**依赖**：`ADR-0056`（Accepted，D1–D7）；`m15-spec-003`（在跑：**同改 `manifests/spec-readonly.lock.toml`** ⇒ 必须先合入）
**可并行分片**：否（上游册 + 契约 + 锁）
**预估**：2–3 h
**档位**：大改（上游只读册正文 + 契约 + 锁重算；复核 ≥4 路注入）
**状态**：待开始

## 背景（`ADR-0056` D1–D7，用户 2026-11-16 逐条确认）

M11 的 `SPEC-186t`/`SPEC-189t` 把页表异常的细粒度原因名（`IGPTRAP`…`DSPFTRAP`、`NUPERM`…`NRPERM`）并入了 `CFXMEM`/`CFXPERM`，用户 2026-11-16 指出**收敛过头**。`ADR-0056` 确定的落地方式：

- **低 16 位不变**（11 项 one-hot cause）；
- **`cause_id[32:16]`（17 位）为子原因 one-hot**，**仅 `CFXMEM`/`CFXPERM` 有效**，其它 cause 必须全 0；
- 位图：`[16..23]` 缺失类（I/D × 4）、`[24..30]` 内存权限类（HSJU 4 + R/W/X 3）、`[31] NCFXPERM`（cfx 访问被来源掩码拒绝）、`[32] ADWBFAIL`（A/D 回写失败）；
- **`CFXMEM`/`CFXPERM` 的 `cause_info` 恒为地址**（`cfxtrap`/`cfx2r*` 拒绝时填**触发指令地址**，与 `excp_cause_ip` 同值，规范须写明"刻意统一"）；其它 cause 的 `info` 语义不变；
- `§7.1` 退出码**不受影响**（仍取低位 cause 索引）。

## 目标

1. **`spec/DADAO-12 §3.6`**：把「所有异常原因编码为 one-hot（64 位）」改写为分层表述 —— `[15:0]` = cause one-hot；`[32:16]` = 子原因 one-hot（仅 `CFXMEM`/`CFXPERM` 有效，其它 cause 必须全 0，非 0 ⇒ 按"未列出位被错误触发"处理）；`[63:33]` 保留。
2. **`spec/DADAO-12 §4.1–§4.6`**（各 monitor/其它 cfx 的原因表）：在 `CFXMEM`/`CFXPERM` 两行注明"`cause_info` = 地址"并**给出 17 位子原因表**（或指向 §3.6 的表 + 一条指针，避免表格重复三处）。
3. **`spec/DADAO-12 §2.2.6`**：把 7 步优先级与子原因对齐（每步对应哪个子原因位），并保留"仅触发优先级最高的异常"表述。
4. **`contract-see §6.1`**：11 项表增「子原因」列（`CFXMEM`/`CFXPERM` 两行给出 17 位映射），并注明"`info` 恒为地址 + `NCFXPERM` 时 = 指令地址"。
5. **锁**：`spec/DADAO-12` sha256 同笔重算 + 注记（引用户 2026-11-16 原话：「收敛过头了…」/「放在31位，然后ADWBFAIL放到32位」/「agree」的确认语）；`contract-see` 版本处理按 `docs/Process-02`（ADR-sourced，版本头不动）。
6. **`discussing.md` 那条"待裁定"改为已定**（由主会话改，不在本任务范围）。

## 验收（真实 rc + 输出）

1. **表完整性**：`§3.6` 或 §4.x 的 17 位表**逐位齐全**（16…32 共 17 行，无重号、无缺号，脚本现算）；`CFXMEM`/`CFXPERM` 两行都注明"`info` = 地址"；
2. **不越界**：低 16 位 11 项 cause 表**一字未改**（`git diff` 该段为空）；`§7.1` 退出码表**零改动**；
3. **契约**：`contract-see §6.1` 增「子原因」列且与 spec 逐项一致（脚本比 17/17）；
4. 门控：`check-spec-readonly`（DADAO-12 重算后 21 册 OK）、`check-spec-refs`、`check-spec-purity`、`check-spec-changelog`、`check-rule-refs`、`check-contracts-dir`、`check-contract-relocs`、`check-interface`、`check-knowledge-refs`、L1 `make check`；
5. **≥4 路注入**（`cp`+md5 还原）：① 删子原因表某一行 ⇒ 完整性判据红；② 把某子原因位号改成 31（与 `NCFXPERM` 撞）⇒ 重号判据红；③ 把 `CFXPERM` 的 `info` 改回"地址或指令编码" ⇒ 判据红；④ 锁 sha 改 1 字符 ⇒ `check-spec-readonly` 红；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **只改规范/契约/锁**，不改实现与测试（三实现归后续任务）；不改 `.tao/archive/**`、`.tao/adr/**`（`ADR-0040`/`ADR-0020` 的旧名注记由主会话单独处置）；
- 上游册改动须与锁同笔（`docs/Process-06 §5`）；
- 不提交 git；注入还原 `cp`+md5。

## 审阅记录

（待填）
