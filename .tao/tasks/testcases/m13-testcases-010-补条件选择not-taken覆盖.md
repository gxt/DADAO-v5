# m13-testcases-010: 补条件选择指令的 not-taken 分支覆盖

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m12-chipyard-010`（已合入）、`m12-chipyard-011`（已合入，已顺手修 RTL）
**可并行分片**：否（共享 `tests/inst/`，单写者）
**状态**：待开始

## 背景（`ISS-387`）

`m12-chipyard-011` 发现并修好了一个既有 RTL 缺陷：

```scala
// 原（错）：cs.n/.z/.p 也被做成条件写
csTaken = !d.isCs || csCondTrue
// 新（对）：第一类恒写两源之一，只有 cs.eq/.ne 才是条件写
csTaken = !d.isCs || csCond <= 2 || csCondTrue
```

spec 依据：`SimRISC-02 §2` —— 第一类 `if (cond) rdHB=rdHC; else rdHB=rdHD`（**恒写两源之一**），第二类 `cs.eq/.ne` 才是「条件成立才写」。

**根因不是 oracle 写错，是向量没覆盖**：`tests/inst/base/reg-cond-assign.yaml` 的 5 条语义例**全部落在 taken 支**（`cs.n=−1`、`cs.z=0`、`cs.p=+1`、`cs.eq` 相等、`cs.ne` 不等），**else 支从未被执行**。因此 `m12-chipyard-010` 的 605 例自写 oracle 与该任务 reviewer 都看不见「不写」这个错误行为。

## 目标

1. 在生成器 `tools/testcases/generate_isa_vectors.py` 里，为**每个** `cs.*`（`cs.n`/`cs.z`/`cs.p`/`cs.eq`/`cs.ne`）补 **not-taken** 语义例：
   - 第一类（`cs.n/.z/.p`）not-taken ⇒ 期望 `rdHB = rdHD`（**必须写**，这是回归点）
   - 第二类（`cs.eq/.ne`）not-taken ⇒ 期望 `rdHC` 保持不变
2. `rd` 与 `rf` 两种形式都要覆盖（两者解码路径不同，共用 `csTaken/csCondTrue`）。
3. 重新生成 `tests/inst/base/reg-cond-assign.yaml`；**禁手改 YAML**（该文件由生成器产出）。
4. 同步 `tests/inst/inventory.md` 的覆盖声明（若条目变化）。

## 验收标准

1. `reg-cond-assign.yaml` 中 `cs.n/.z/.p` 的 not-taken 例 **≥3 条**（rd 形式），`cs.eq/.ne` 的 not-taken 例 ≥2 条；`rf` 形式各 ≥1 条
2. **可达 FAIL 反例**：把 RTL 的 `csTaken` 改回旧写法（`!d.isCs || csCondTrue`）⇒ 新向量必须红；还原后回绿
3. 新向量在 QEMU 与 chipyard 上逐例一致（chipyard 侧可与 `016` 合并跑，见「说明」）
4. `make check-inst`（Tiny）与 `make check-tests-index` rc=0；273 例 md5 不变
5. 一键证据脚本；完成区 ≤30 行、无运行期路径；**「修改文件」与 `git status` 对账**（`ISS-377`）

## 说明

- 与 `m12-chipyard-012`–`015` **串行**：它们改 chipyard 组件（单写者），本任务要跑 chipyard 验证，不能并行。
- 若排期上与 `012`–`015` 冲突，可先落「生成器 + YAML + QEMU 验证」，chipyard 侧验证并入 `016`（T0 冒烟）并在完成区注明。
- 本任务是 `ISS-387` 的行动项之一；另一项（`Process-09` 增加「条件语义须有 taken/not-taken 双支」判据）由 architect 另行处理，不在本任务范围。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树（`ISS-368`）；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
8. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

（待填）
