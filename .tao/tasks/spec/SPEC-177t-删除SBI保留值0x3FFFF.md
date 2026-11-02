# SPEC-177t: 删除 SBI 保留值 `0x3FFFF`（ISS-334 / ADR-0038 D3）

**模块**：spec
**项目里程碑**：M10
**依赖**：ADR-0038（D1/D2/D4/D5 已 Accepted；D3 本次定）
**状态**：待开始

## 背景（用户 2026-10-26 选 B）
semihosting 已迁至 `0x3FF00–0x3FFFF`；`DADAO-22:863` 的保留值 `0x3FFFF` 正落在该区间，若将来用于「SBI 协议版本协商」会被 semihosting 短路。用户在 A（移到 `0x3FEFF`）/ B（删除）/ C（收窄区间）中选 **B：删除该保留约定**。

## 改动
1. `spec/DADAO-22-SBI-主管系统二进制接口.md:863`：删除「保留 `immu18` 值 `0x3FFFF`（最大）用于将来可能的 “SBI 协议版本协商” 功能。」一句；保留前半句（新增 cfx 时新增章节/功能码表）。
   - **不要**改 SBI 里其它 `0x3FFFF`（那些是 `set.rd rd3, 0x3FFFF` 的 immu18 掩码常量）。
2. 版本：SBI `0.7.2` → **`0.7.3-rc`**；SEE 同步 **`0.7.3-rc`**（`check-spec-changelog` 的 SEE↔SBI 互锁）；两册附录新开 `### 0.7.3-rc（未发布）`，SBI 条目写「删除 `0x3FFFF` 保留值（与 semihosting 区冲突，ADR-0038 D3）」。
3. `ADR-0038`：在 D3 处补「**D3 决议（2026-10-26，用户选 B）**：删除保留值；ISS-334 由 SPEC-177t 关闭」。
4. `issues.yaml`：ISS-334 `closed`，`resolved_by: SPEC-177t`。
5. 锁：`manifests/spec-readonly.lock.toml` 头补授权（用户原话「B」）；重算 DADAO-22、DADAO-12 sha256。

## 约束
- 只改上述 2 册 + ADR-0038 + issues + 锁 + 任务书/`milestones.md`；不改 semihosting 判定、不改其它 `0x3FFFF` 掩码。
- 临时目录 `/tmp/opencode/SPEC-177t/`；不提交。

## 验收
- `make check` rc=0；`check-spec-readonly`、`check-spec-changelog`、`check-contracts-*` rc=0。
- grep：`DADAO-22` 中「SBI 协议版本协商」= 0；`0x3FFFF` 掩码常量数量不变；SBI/SEE 册头/附录段一致。
- ISS-334 closed + resolved_by 正确。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
