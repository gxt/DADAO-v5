# 机器路由表

远端任务路由表，dispatch/complete 据此同步/拉取任务文件。无远端任务时留空即可：

| 执行环境 | 传输命令（push 任务文件到远端） | 远端执行方 |
| --- | --- | --- |
| `远端 21 · <repo>` | `scp <file> user@host-21:~/<repo>/.tao/tasks/` | 远端智能体 |
| `远端 152 · <repo>` | `scp -P 22005 <file> user@host-152:~/<repo>/.tao/tasks/` | 远端智能体 |

- 传输命令**以本表为准**（可能是 scp / scp -P / rsync），不要假设一律 rsync
- pull（远端拉回本地）由 push 命令反推：`scp [-P port] user@host:remote_path/<file> <local_file>`
- 主机地址只写在本表，不写进命令/角色文件
