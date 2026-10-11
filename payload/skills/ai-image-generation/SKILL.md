---
name: ai-image-generation
description: 本地可复用的 AI 图片生成 skill。用于单张或批量生图、参考图编辑、BeeAPI GPT Image 2、Grok Imagine quality、API 回退、最多 5 路并发和 HTML 预览质检。触发词：生图、图片生成、AI 生成图、参考图、image generation、gpt-image-2、grok、批量生成图片。
---

# AI 图片生成

## 接口与原则

- 当前只保留两条可用链路：BeeAPI GPT Image 2（provider：`beeapi-gpt-image-2`）和 Grok Imagine quality（provider：`grok-imagine-image-quality`）。
- BeeAPI GPT Image 2.5 默认请求 `https://beeapi.ai/v1`，模型为 `gpt-image-2.5`。这里的 `gpt-image-2.5` 是 BeeAPI 的模型名，不是另一条 provider 链路；调用时使用 `beeapi-gpt-image-2`。
- Grok 只保留 quality 模型 `grok-imagine-image-quality`；light 模型已移除。
- 参考图只支持 BeeAPI GPT Image 2：使用 `/images/edits` 的 multipart `image[]`。Grok 不加载参考图，只能按纯文本生成。
- GPT Image 2 因服务端故障回退到 Grok 时，必须明确输出：`使用 Grok 生图时无法加载参考图链路`，且不得把参考图发送给 Grok。
- Grok 仅在 Image 2 返回可安全回退的服务端错误时使用；不把余额不足、鉴权失败或 524 请求自动重试或切换，避免重复扣费。
- 输出必须来自图片接口并保存为 PNG/JPEG 位图；不使用 SVG、HTML、CSS 或手工图形替代一次真实图片请求。
- 不把 API key 写进 prompt、仓库、skill 或日志；脚本读取本机环境变量和当前项目 `.local`。
- 未显式指定 `--size` / `--min-width` / `--min-height` 时，使用 provider 默认画布，不强制固定比例。

## 环境变量

```text
BEEAPI_IMAGE_API_KEY=...
BEEAPI_API_KEY=...
OPENAI_API_KEY=...
GROK_IMAGE_QUALITY_API_KEY=...
GROK_IMAGE_API_KEY=...
BEEAPI_GROK_API_KEY=...
GROK_IMAGE_BASE_URL=https://beeapi.ai/v1
BEEAPI_IMAGE_BASE_URL=https://beeapi.ai/v1
BEEAPI_BASE_URL=https://beeapi.ai/v1
```

也可在目标项目放 `.local/secrets/workflow.env`，或用 `IMAGE_GENERATION_ENV_FILE` 指向自定义 env 文件。

## 单张生成

```powershell
python "scripts/generate_image.py" `
  --provider beeapi-gpt-image-2 `
  --prompt-file ".\prompts\封面.txt" `
  --output ".\output\封面.png"
```

显式需要固定尺寸时才加：

```powershell
--size 1024x1024 --min-width 1024 --min-height 1024
```

## 批量生成与并发

```powershell
python "scripts/batch_generate.py" `
  --prompts-dir ".\prompts" `
  --output-dir ".\output" `
  --provider beeapi-gpt-image-2 `
  --fallback-provider grok-imagine-image-quality `
  --max-concurrency 5 `
  --skip-existing
```

- `--max-concurrency` 的合法范围是 `1-5`，默认 `5`，超过 5 直接拒绝执行。
- 批量请求按最多 5 张一波提交，不会一次性提交超过 5 个在途请求。
- 当前波任意一张失败，取消后续波次；因此不会在前一波异常时继续处理第 6 张及之后的请求。
- 同一张图的 provider 回退是串行的；全局在途的逻辑图片请求仍不超过 5 个。
- 带参考图的批量任务只能由 BeeAPI GPT Image 2 加载参考图；回退到 Grok 时按纯文本生成并输出固定告警。

## 参考图编辑

单张或批量请求都可重复指定本地参考图；不指定时仍走纯文本生图接口：

```powershell
python "scripts/generate_image.py" `
  --provider beeapi-gpt-image-2 `
  --reference-image ".\output\source.png" `
  --prompt "保持参考图的主体和整体风格，改成蓝色背景的产品图" `
  --output ".\output\edited.png"
```

- `--reference-image` 可重复指定多张图；参考图只作为 BeeAPI GPT Image 2 的请求输入，不会写入 prompt 或日志。
- `batch_generate.py` 支持同样的 `--reference-image` 参数，会把相同参考图传给每个提示词任务。
- Grok 没有参考图编辑链路。若 GPT Image 2 失败并切换到 Grok，Grok 不会加载参考图，只进行纯文本生成，并明确输出：`使用 Grok 生图时无法加载参考图链路`。

## HTML 预览

```powershell
python "scripts/build_html_preview.py" `
  --input-dir ".\output" `
  --output ".\output\_preview\review.html"
```

批量完成后优先用 HTML 总览检查图片数量、尺寸、文字和明显失败结果。

## 资源

- `scripts/generate_image.py`：单张图片生成，支持 BeeAPI GPT Image 2 和 Grok Imagine quality。
- `scripts/batch_generate.py`：最多 5 路并发，按波次执行并在失败时停止后续波次。
- `scripts/build_html_preview.py`：压缩生成 HTML 总览。
- `templates/image_workflow.template.json`：项目级配置样例。

## 失败处理

- `429`：按 `Retry-After` 等待；重试次数仍受当前波限制。
- `500/502/503/504/origin_gateway_timeout`：当前图片可安全回退到 Grok quality；带参考图时按纯文本生成并输出固定告警。
- `524`：可能已在服务端继续处理并计费，停止自动重试和后续波次。
- `403` 余额不足、`400` 鉴权失败或其他不可重试错误：立即停止当前波，不继续发出后续请求。
- 缺 key：先查本机环境变量，再查目标项目 `.local/secrets/workflow.env`。
