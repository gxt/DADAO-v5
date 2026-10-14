# SPEC-138t: Linux syscall 映射契约（`contract-syscall.md`）

**模块**：spec
**项目里程碑**：M8
**依赖**：`ADR-0025`（M8 范围与 Linux 兼容路线，`Accepted`，`D1`= 沿用 RISC-V 编号）；`SPEC-139t`（并列契约，无先后硬依赖）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 背景 / 依据

- **M8 主线**（`ADR-0025`）：无内核的 Linux 用户态栈；**P0 = 契约先行**（`ADR-0025 D6`）。
- **上游已有 syscall ABI（勿重复发明）**：`spec/DADAO-21-ABI §4` 已定发起方式 / 传参 / 返回；`spec/DADAO-22-SBI §2` 已定 `umon(cfx0)` / `jmon(cfx1)` 的 `SBI_*_SYSCALL`（`immu18=0`）。**缺的是 Linux 语义映射**（号表 / errno / 参数与返回值语义）。
- **号表口径 = 沿用 RISC-V 编号**（`ADR-0025 D1`；用户原话「沿用 RISC-V 编号（推荐）」）。
- **errno 约定待定**：`rderrno`（`rd1`，`spec/DADAO-21-ABI §1`）与 musl 的关系**本任务内待定 / 需查证**；**不得臆造**。

## 接口规范

- **输入**：`spec/DADAO-21-ABI §4`、`spec/DADAO-22-SBI §2`、`ADR-0025`、`ADR-0004`（exit port 协议）、RISC-V Linux 号表（**外部参照，仅作内容溯源，非执行依赖**）。
- **输出**（落点 `.tao/knowledge/contract-syscall.md`）：
  1. **号表口径**：syscall 号在 `rd15`、**沿用 RISC-V Linux 编号**（`ADR-0025 D1`）；**不复制**上游正文，**指针**到 `spec/DADAO-21-ABI §4` / `spec/DADAO-22-SBI §2`。
  2. **入口**：`trap cfxha, immu18`（`umon` 路径）与 SBI `SBI_UMON_SYSCALL`（`immu18=0`）的关系（**引用**，不重复正文）。
  3. **参数与返回**：参数 `rd16–31` / `rb16–31` / `rf16–31`、返回 `rd8`（**指针** `spec/DADAO-21-ABI §4`）。
  4. **errno 约定**：`rderrno`（`rd1`）与 musl 的关系——**待定**，须在任务内查证或标为待用户裁定（**不得臆造**）。
  5. **独立 oracle 口径**：期望值 / 对照来源（与 `ADR-0025 D7` golden 对照衔接）；**不从实现反推**。
- **约束**：**不复制**上游 `spec/` 正文（只**指针**）；**不改** `spec/`、`contracts/` 机器数据、组件补丁。
- **落点迁移接口**：本契约暂落 `.tao/knowledge/contract-syscall.md`（`check-knowledge-dir` 白名单允许 `contract-*.md`）；若 `INFRA-071t`（`contract-*.md` → `contracts/`，**待用户授权**）获批，本契约**随之整体迁移** ⇒ 引用路径须**可切换**（不写死具体目录）。

## 验收标准

1. `contract-syscall.md` 落 `.tao/knowledge/`，含上述 5 项；对外引用均**指针**到 `spec/DADAO-21-ABI §4` / `spec/DADAO-22-SBI §2`（`grep` 真实输出），**无**上游正文复制。
2. 号表口径与 `ADR-0025 D1` 一致（`rd15` + 沿用 RISC-V 编号），`grep` 可证。
3. errno 一项**有明确归属**（已定 **或** 标「待用户裁定」并给出选项），**无臆造**。
4. 门控：`make check` / `check-knowledge-dir` / `check-knowledge-refs` / `check-no-residue` / `python3 tools/infra/check_issues.py` 各 rc=0。
5. （若 errno 需裁定）用户裁定**原话**原样写入本任务书。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
