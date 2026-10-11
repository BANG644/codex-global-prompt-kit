# RTK Output Guide

RTK 只用于压缩预期很长、重复或嘈杂的 CLI 输出；它是输出优化器，不是必经工作流。

## 使用原则

- 小而精确的读取、搜索和命令直接使用原生命令，避免额外包装与往返。
- 测试、构建、lint、大型 diff、递归目录、长日志等可能刷屏时，优先用合适的 `rtk` 包装器。
- 命令已经以 `rtk` 开头时不要重复嵌套。
- 不要为了确认 hook 是否存在而停工，也不要对每条命令先跑一次 `rtk rewrite`。
- 需要原始字节、完整错误上下文或 RTK 摘要不足时，直接读取原始输出或 RTK 提供的完整产物。

常用高噪声形式：

- `rtk git status` / `rtk git diff` / `rtk git log`
- `rtk test <测试命令>`
- `rtk summary <构建、lint 或类型检查命令>`
- `rtk tree`、`rtk grep`、`rtk read`（仅在输出确实较大时）

Windows/PowerShell 下不要假设自动 hook 一定改写命令；是否显式使用 RTK 由预期输出量决定，而不是由命令名称决定。
