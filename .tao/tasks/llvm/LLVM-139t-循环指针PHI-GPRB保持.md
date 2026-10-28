# LLVM-139t: 循环指针 PHI 的 GPRB 保持（machine pass）

**模块**：llvm
**项目里程碑**：M10
**依赖**：LLVM-138t
**状态**：待开始

## 背景
DADAO 的 i64/指针共用位宽，SelectionDAG 可能把循环 pointer PHI 分到 GPRD，导致每轮地址消费前插 `rd2rb`。PR 新增 `DADAOPointerPHIBank`（post-ISel、pre-RA），仅处理「入口已在 GPRB、单入口/单回边、无 call/inline asm 的直接 pointer PHI + 两段 GEP」，重建 GPRB PHI 和 RB 加法。该 pass 是机器级改写，风险最高，必须独立评审。

## 目标
1. 重放/实现 pass，保持窄范围：多回边、call/inline asm、select 派生、ptrtoint/inttoptr、普通 i64 PHI 一律回退，不改变全局 i64 寄存器类/ABI。
2. **补正确性保护**：
   - `BaseCopy`/被替换的 `CopyDst` 必须与 PHI 在同一支配域（或证明使用点受 MBB 支配）；不能只看存在性；
   - `add_o_bbd` 的 GPRB/GPRD 操作数约束、`TailConst` 插入、PHI 删除顺序；
   - 不破坏 debug loc、kill flags、live range（pre-RA）。
3. 测试：正例 + 至少覆盖跨块 COPY、循环内 call、多回边、switch、select、inline asm、ptr-int、i64 PHI；RUN 行加 `-verify-machineinstrs`（`-stop-after` 与最终 asm 两路）。
4. 运行期验证：QEMU 执行正例循环，检查结果；llvm-ts 定向（至少一个 pointer-loop 基准）不回归。
5. 更新 docs/矩阵；报告注明「减少 rd2rb」是汇编级指标，不冒充整体性能。

## 验收
- 新增 lit 全绿；完整 `check-lit` 不回归（现场统计）；`-verify-machineinstrs` 无报错。
- QEMU 正例结果与独立 oracle 一致；llvm-ts 定向 rc=0。
- `make check`/`check-patch-tree` rc=0；证据 `.work/evidence/<任务号>/run.sh`（注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/LLVM-139t/`。

## 约束
- 只改该 machine pass、pass 接线、测试/文档/补丁；不碰 code model/tailjmp/i64 移位/窄 extension。
- 不改 ABI/全局寄存器类/spec/contracts/QEMU。
- **不提交、不 push**；重建申报；全量/夜跑未授权时不跑。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
