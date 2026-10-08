# 项目里程碑

> 只承载**当前进度**；历史见 `.tao/archive/M<1..5>/m<i>-retrospective.md`。

## 当前进度
- **里程碑**：M6（`INTEG-023k`「M6 启动与分解」）
- **规划中**：
  - M6 主题与范围（`-bios` + ELF 组合加载/入口语义；ELF loader 扩 RAM@0；RAM@0 step2；组合加载 ADR 待定）
  - **Embench 接入（M6 待办）**：① 建 **ADR**（记录 Embench 上游选择 + 精确 commit）⇒ 翻 `manifests/components.lock.toml` 的 `enabled = true`；② 建 `components/embench-iot/{patches/**,series,changelog.md}`（board shim 3 函数、`md5sum` 大端适配、最小运行时）；③ 工作树由既有 `make fetch` 机制生成到 `.work/source/embench-iot`
  - **`lessons.md` 瘦身**：下次里程碑归档时按新口径（新增条目 ≤3 行 + 指针，细节进 `.work/log/`；**不追溯重写**）瘦身（现 612 行 / 46 字头）
- **阻塞与待裁定**：8 项归属存疑（`ISS-019/026/047/074/081/163/164/167`；其中 `ISS-163`/`ISS-167` 涉改上游只读册，**须用户授权**）；M6 主题裁定（待用户）

## 任务流水（仅当前里程碑 M6）

| 任务 | 状态 | 开始 | 结束 | 说明 |
| --- | --- | --- | --- | --- |
| `INTEG-023k` | 待开始 | — | — | M6 启动与分解（草案待裁定） |

> 开始/结束由**主会话**在 `/dispatch`／`/complete` 时填写（格式 **`MM-DD hh:mm`**，不带年份）；只填**可考证**时间，**禁编造**。
