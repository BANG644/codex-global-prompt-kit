# 可转发给其他人的配置提示词

```text
请把我的 Codex 全局提示词配置同步到这台设备，严格使用公开仓库的固定版本：
https://github.com/BANG644/codex-global-prompt-kit/tree/v1.1.0

请按以下步骤完成，不要只给我操作建议：

1. 先检查当前环境是否有 Git、Python 3.10 或更新版本，以及支持 `codex plugin marketplace` 和 `codex plugin add` 的 Codex CLI。按系统选择实际可用的 Python 启动命令（Windows 可用 `py -3`，macOS/Linux 通常用 `python3`，也可使用版本正确的 `python`）。缺少必需项时，说明缺少什么、它影响哪一步和最短的补齐方式；不要在未说明的情况下安装系统软件。
2. 将仓库固定版本 `v1.1.0` 克隆到临时或用户可见的工作目录，不要使用浮动的 `main` 分支。阅读 `README.md`、`MANIFEST.json`、`NOTICE.md` 和 `install.py`，然后用已确认的 Python 启动命令运行 `install.py --check`。检查输出中的文件清单、依赖、目标路径和 Ponytail 冲突状态。
3. 这次操作已授权你安装仓库列出的全局提示词、8 个白名单 Skills 和 Ponytail 插件。用同一个 Python 启动命令运行 `install.py --apply --yes` 完成安装。安装器会在本机先备份被替换的同名提示词和 Skill；如果需要调用 Codex 插件命令修改 `config.toml`，也会先把该文件备份到本机。备份不得上传或粘贴到对话中。
4. 只安装 `MANIFEST.json` 列出的两个全局提示词文件、8 个 Skills，以及固定版本的 Ponytail 插件。`review-ready-report` 中的通俗化写作指南使用通用示例，不包含来源材料的文件名或实际研究数据。不要导入整份 `config.toml`，不要复制 MCP 连接、账号登录状态、个人目录或白名单外的 Skills，也不要删除其他插件或配置。
5. 如果安装器报告 `ponytail` 市场源或版本冲突，不要先删除现有市场或插件。检查哪些已安装插件依赖这个市场、现有版本和来源；能在不影响其他插件的前提下安全对齐时再处理，否则保留当前状态并把冲突和可选处理步骤告诉我。
6. 安装结束后，使用前面确认的 Python 启动命令重新运行 `install.py --check`。确认输出显示所有提示词和 8 个 Skill 目录内的文件均已通过 `payload.sha256` 完整性校验；确认 Ponytail 已启用、版本为 `5.3.3`，其市场仓库提交与 `MANIFEST.json` 中固定的提交一致。区分“文件已复制”“插件已注册/启用”和“当前 Codex 会话已重新加载”；需要重启时明确告诉我，不要把静态安装结果说成运行时已生效。
7. RTK、CodeGraph 和图片生成 API 密钥属于可选或账号级依赖。只检查工具是否存在，不读取、展示、复制或上传任何凭据；缺少时说明对应能力的影响和本地配置方法。不要为了验证而发起真实生图请求或产生费用。

完成后用简洁中文告诉我：已安装哪些内容、文件放在哪里、备份在哪里、插件实际状态、还缺哪些可选依赖，以及是否需要重启 Codex。
```
