# feedback_002：生成物落点迁移须「同删旧产物目录」+ 脚本比对 git 路径须关 `core.quotePath`

> 操作规范（"应该这样做 / 不该那样做"）。来源：`INFRA-048t`（生成物落点迁移，2026-10-07）下发前预检修订与验收（reviewer `Accepted` + architect 交叉复核）。

## 背景（触发事件）

`INFRA-048t` 把 `test-codegen`/`test-elf`/lit 的运行产物落点从源码树/构建树迁到 `.dadao/tests/`，并要求清理 `.gitignore` 中的旧忽略规则 `tests/llvm/codegen-e2e/`。**下发前预检**发现：该旧目录**实际存在**（内含 `arith_*.bin/.o/.s/.prog.s` 等运行产物），若只清忽略规则而不删目录，运行产物会暴露为未跟踪残留，与任务自身「无残留」验收**自相矛盾**（实测清规则后 `git status --porcelain -uall` 多出 60 个 `??`）。另：lit scratch 的**实际**旧落点（`.dadao/cross-toolchain/test-output/`，因 `INFRA-047t` 改了 `tools_dir` 默认）与任务书描述的 `.work/build/llvm/test-output/` **不一致**，以实测为准。

## 规律（应固化）

1. **迁移生成物落点 = 改落点 + 清旧忽略规则 + 删残留旧产物目录**，三者须**同一原子落地**；只做前两者会与「无残留」验收冲突。
   - 做法：任务书「输出」须显式列出旧目录为**删除目标**，并要求贴删除前后 `ls`/`git status --porcelain -uall` 真实输出；**不得**以「保留旧忽略规则」回避（旧落点自生效里程碑起须清除）。
   - 判据：清掉忽略规则后 `git status --untracked-files=all` 若暴露旧产物，即证必须同删。

2. **迁移前须`grep`/`ls` 实测旧落点的真实路径，不以任务书/历史描述为准**（路径可能被上游任务改变）。
   - 反例：lit scratch 任务书述 `.work/build/llvm/test-output/`，实为 `.dadao/cross-toolchain/test-output/`（上游改 `tools_dir` 所致）；若照描述迁移会漏改。

3. **脚本比对 `git status` 路径须先 `git -c core.quotePath=false`**：非 ASCII 路径（含中文任务书名）默认被加引号 + 八进制转义，会与按原文匹配的白名单**错配**，产生**假阳性 FAIL**。
   - 反例：证据脚本用默认 `git status` 匹配中文任务书路径，自审实测 `bad-count=1`（假阳性）。

4. **范围判定不得越界**：旧落点删除目标**只列任务书明确列出的目录**；gitignored 树内（`.dadao/`、`.work/`）的其它历史残留（如迁移前的 lit scratch 旧目录）**不在范围内**，应**登记为遗留/另立任务**，不得顺手删（最小原则）。
