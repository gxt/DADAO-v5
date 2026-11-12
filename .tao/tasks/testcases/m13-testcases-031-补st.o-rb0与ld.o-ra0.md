# m13-testcases-031: 补 `st.o rb0`（指令地址作源）与 `ld.o ra0`（RAS 窗口读写）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（`01-load-store` 单元素套件已建）
**可并行分片**：否（共享 `tests/inst/01-load-store/`）
**状态**：待开始

## 背景（`ISS-411` ②③）

`012` 的两条覆盖面缺口：

1. **`st.o rb0`**：`rb0` 读出的是**当前正在执行的这条指令的地址**（`SimRISC-00`），`012` 的宏层无法构造这个期望值，故未覆盖。
2. **`ld.o ra0`**：`ra0` 是 `{SBZ(10), RACNT(6), MRPTR(48)}` 的窗口，`012` 未覆盖读写。

## 用户裁定（2026-11-13，含补充修正）

1. **`st.o rb0` 取「当前指令地址」的期望值**：
   - 方式一：`aip.si rbX, 0`（`imms30 = 0` 合法）⇒ `rbX` = 该 `aip.si` 自身的 IP；再 `add.si rbX, rbX, delta` 得到被测指令地址
   - 方式二：`rb2rb rbX, rb0, 1`（或 `rb2rd rdX, rb0, 1`）直接拷出当前 IP，再求 `delta`
   - `delta` = 被测指令与该取址指令之间的字节差（相邻时即 4）
2. **`ld.o ra0` 读写都测**；**写时 `[63:54]` 的 SBZ 10 位忽略**（`SimRISC-00` 已规定「写无效」）。
   - 注意操作数位置：`ld.o_rrii_ra` 的 **`ra0` 是目的寄存器（第一个操作数）**，即 `ld.o ra0, rbX, imm`
   - **读** `ra0` 需用复制类指令（`ra2rd rdY, ra0, 1`），不是 `ld.o`

## 范围

在 `tests/inst/01-load-store/` 补测（**不改已通过用例**）：

- `st.o_rrii_rb` / `st.o_rrii_rd`：新增 `rb0` 作源用例 ≥2
  - 期望值按上文方式一或方式二构造；`delta` 在注释里写清怎么算
- `ld.o_rrii_ra`（及 `ld.o_rrii_rb` 的 ra 形式如存在）：新增
  - **写**：`ld.o ra0, rbX, imm` 写入含 SBZ 置位的值 ⇒ 读回验证 `[63:54]` 保持 0、`[53:48]`/`[47:0]` 生效
  - **读**：先用 `call`/`ret` 构造已知 `RACNT`/`MRPTR`，再用 `ra2rd rdY, ra0, 1` 拷到 RD 后校验两字段
  - 每组 ≥3 例

## 验收

1. 新增用例数按现场统计；每文件检查点仍 ≤127、点号连续
2. **三方逐字节**（chipyard == QEMU == gem5 同镜像）；**若某平台 `ra0` 写语义不一致 ⇒ 如实记红**，登记 issue 回报，不得放宽期望
3. `make check-inst` rc=0；273 例 md5 不变
4. 可达 FAIL 注入（改一条期望 ⇒ 对应点号退出）
5. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- `aip.si` 的 `imms30` 必须是 **4096 的整数倍**；精确差用 `add.si`（`imms18`，字节为单位）。
- 沿用 `012` 的 hmon 自装 workaround（`ISS-410` 未修前）。
- `.work` 软链（`ISS-389`）；改动只在任务 worktree 内（`AGENTS.md` 硬约束 14）。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir，用相对路径。

## 审阅记录

（待填）
