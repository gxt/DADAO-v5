# LLVM-138t: 窄整数 canonical extension 折叠

**模块**：llvm
**项目里程碑**：M10
**依赖**：LLVM-137t
**状态**：待开始

## 背景
窄整数（i8/i16/i32）指令可按符号/无符号方向把结果 canonical 扩展到 64 位。当生产者与显式 `sext`/`zext` 方向完全一致时，可直接选 `.st/.ut/.sw/.uw/...` 变体，省掉随后的 `ext.so/ext.uo`。PR 提供 39 组 pattern，但基线和 shift-amount 类型需要核实。

## 目标
1. 在 `DADAOCodeGen.td` 增补精确 pattern：i8/i16/i32 × add/sub/mul/udiv/urem/sdiv/srem × shl/srl/sra，仅方向一致组合；方向不匹配保留 `ext.so/ext.uo`。
2. 核实 shift pattern 的移位量类型（IR 中窄 shift 的 amount 与 value 同宽，PR 写成 `i64 GPRD` 需证明 legalize 后成立）；不成立则改为正确类型或删掉该组。
3. 保留 `sub 0, x`（narrow-neg）既有处理；不改变 LLVM-134t 的 ext 清理口径。
4. 负例：`zext(ashr)`、`sext(lshr)`、`ptrtoint`/`inttoptr`、nsw/nuw、i8/i16 边界、div/rem；每类至少一组。
5. QEMU 运行期 oracle：独立 Python 派生期望，覆盖 39 组代表 + 方向不匹配；不能只看 `CHECK-NOT: ext`。

## 验收
- 新增/重放 lit 全绿；完整 `check-lit` 不回归（现场统计）。
- QEMU 结果与独立 oracle 一致；方向不匹配仍保留 ext。
- `make check`/`check-patch-tree` rc=0；证据 `.work/evidence/<任务号>/run.sh`（注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/LLVM-138t/`。

## 约束
- 只改窄整数 extension 折叠与测试；不碰 i64 移位/code model/tailjmp/指针 PHI。
- 不改 ABI/调用约定；不改 spec/contracts/QEMU。
- **不提交、不 push**；重建申报；全量/夜跑未授权时不跑。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
