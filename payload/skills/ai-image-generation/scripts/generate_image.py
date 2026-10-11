"""
统一图片生成脚本
用法：
    python scripts/generate_image.py --prompt "提示词" --output "输出路径.png"
    python scripts/generate_image.py --prompt-file prompts.txt --output "输出路径.png"
    python scripts/generate_image.py --provider beeapi-gpt-image-2 --prompt "提示词" --output "输出路径.png"
"""

import argparse
import base64
import io
import json
import mimetypes
import os
from pathlib import Path
import sys
import time

from local_env import ensure_local_env_loaded

# Windows GBK 终端下 emoji 会崩溃，强制 utf-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import requests
except ImportError:
    print("错误：需要安装 requests。运行: pip install requests", file=sys.stderr)
    sys.exit(1)

# === 默认配置 ===
DEFAULT_API_KEY = None
DEFAULT_BEEAPI_BASE_URL = "https://beeapi.ai/v1"
DEFAULT_PROVIDER = "beeapi-gpt-image-2"
DEFAULT_GPT_IMAGE_MODEL = "gpt-image-2.5"
DEFAULT_GROK_IMAGE_MODEL = "grok-imagine-image-quality"
DEFAULT_MIN_WIDTH = 0
DEFAULT_MIN_HEIGHT = 0

ensure_local_env_loaded()

PROVIDER_ALIASES = {
    "beeapi-gpt-image-2": "beeapi-gpt-image-2",
    "beeapi": "beeapi-gpt-image-2",
    "beeapi-image": "beeapi-gpt-image-2",
    "bee": "beeapi-gpt-image-2",
    "bee-image": "beeapi-gpt-image-2",
    "grok": "grok-imagine-image-quality",
    "grok-image": "grok-imagine-image-quality",
    "grok-quality": "grok-imagine-image-quality",
    "grok-imagine-image-quality": "grok-imagine-image-quality",
    "xai": "grok-imagine-image-quality",
}


class ImageGenerationError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_text: str | None = None,
        retryable: bool = True,
        charge_risk: bool = False,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
        self.retryable = retryable
        self.charge_risk = charge_risk
        self.retry_after = retry_after


def parse_retry_after(headers: dict | None) -> int | None:
    if not headers:
        return None
    raw_value = headers.get("Retry-After") or headers.get("retry-after")
    if not raw_value:
        return None
    try:
        return max(1, int(raw_value.strip()))
    except ValueError:
        return None


def build_api_error(status_code: int, response_text: str, headers: dict | None = None) -> ImageGenerationError:
    preview = (response_text or "")[:500]
    lowered = preview.lower()
    retryable = True
    charge_risk = False
    retry_after = parse_retry_after(headers)

    if status_code == 524:
        # Cloudflare 524 经常意味着代理超时，但上游仍可能继续生成并计费。
        retryable = False
        charge_risk = True
    elif status_code == 403 and (
        "insufficient_user_quota" in lowered
        or "额度不足" in preview
        or "预扣费额度失败" in preview
    ):
        retryable = False
    elif status_code == 429:
        retryable = True
        retry_after = retry_after or 20
    elif 400 <= status_code < 500:
        retryable = False

    message = f"API 返回 HTTP {status_code}: {preview}"
    if charge_risk:
        message += " [高风险：524 可能已在服务端继续处理并计费]"
    if retry_after:
        message += f" [建议等待 {retry_after}s 后重试]"

    return ImageGenerationError(
        message,
        status_code=status_code,
        response_text=response_text,
        retryable=retryable,
        charge_risk=charge_risk,
        retry_after=retry_after,
    )


def normalize_provider(provider: str | None) -> str:
    raw_value = provider or os.environ.get("IMAGE_PROVIDER", DEFAULT_PROVIDER)
    canonical = PROVIDER_ALIASES.get(raw_value.strip().lower())
    if canonical:
        return canonical
    raise ValueError(
        f"不支持的 provider: {raw_value}。可选值: {', '.join(sorted(set(PROVIDER_ALIASES.values())))}"
    )


def build_openai_compatible_url(base_url: str, path: str) -> str:
    normalized_base = base_url.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    if normalized_base.endswith("/v1"):
        return f"{normalized_base}{normalized_path}"
    return f"{normalized_base}/v1{normalized_path}"


def _load_reference_images(reference_images: list[str] | None) -> list[dict]:
    loaded: list[dict] = []
    for raw_path in reference_images or []:
        path = Path(raw_path).expanduser()
        if not path.is_file():
            raise ValueError(f"参考图片不存在或不是文件: {path}")
        mime_type, _ = mimetypes.guess_type(path.name)
        if not mime_type or not mime_type.startswith("image/"):
            raise ValueError(f"参考图片格式无法识别: {path}")
        data = path.read_bytes()
        if not data:
            raise ValueError(f"参考图片为空: {path}")
        loaded.append({"path": path, "mime_type": mime_type, "data": data})
    return loaded


def resolve_provider_config(
    provider: str,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> dict:
    if provider == "beeapi-gpt-image-2":
        return {
            "api_key": (
                api_key
                or os.environ.get("BEEAPI_IMAGE_API_KEY")
                or os.environ.get("BEEAPI_API_KEY")
                or os.environ.get("OPENAI_API_KEY")
                or DEFAULT_API_KEY
            ),
            "base_url": (
                base_url
                or os.environ.get("BEEAPI_IMAGE_BASE_URL")
                or os.environ.get("BEEAPI_BASE_URL")
                or DEFAULT_BEEAPI_BASE_URL
            ),
            "model": (
                model
                or os.environ.get("BEEAPI_IMAGE_MODEL")
                or DEFAULT_GPT_IMAGE_MODEL
            ),
        }

    if provider == "grok-imagine-image-quality":
        return {
            "api_key": (
                api_key
                or os.environ.get("GROK_IMAGE_QUALITY_API_KEY")
                or os.environ.get("GROK_IMAGE_API_KEY")
                or os.environ.get("BEEAPI_GROK_API_KEY")
                or DEFAULT_API_KEY
            ),
            "base_url": (
                base_url
                or os.environ.get("GROK_IMAGE_BASE_URL")
                or os.environ.get("BEEAPI_BASE_URL")
                or DEFAULT_BEEAPI_BASE_URL
            ),
            "model": (
                model
                or os.environ.get("GROK_IMAGE_QUALITY_MODEL")
                or DEFAULT_GROK_IMAGE_MODEL
            ),
        }

    raise ValueError(f"未知 provider: {provider}")


def ensure_api_key(config: dict, provider: str) -> None:
    if config.get("api_key"):
        return

    if provider == "beeapi-gpt-image-2":
        raise ValueError(
            "缺少 API Key。请通过 --api-key 或环境变量 BEEAPI_IMAGE_API_KEY / BEEAPI_API_KEY 提供。"
        )

    if provider == "grok-imagine-image-quality":
        raise ValueError(
            "缺少 API Key。请通过 --api-key 或环境变量 GROK_IMAGE_QUALITY_API_KEY / GROK_IMAGE_API_KEY / BEEAPI_GROK_API_KEY 提供。"
        )

    raise ValueError("缺少 API Key。请通过 --api-key 或环境变量提供。")


def request_with_proxy_fallback(method: str, url: str, timeout: int, **kwargs):
    try:
        return requests.request(method, url, timeout=timeout, **kwargs)
    except (requests.exceptions.ProxyError, requests.exceptions.SSLError) as first_error:
        reason = "代理连接失败" if isinstance(first_error, requests.exceptions.ProxyError) else "TLS/SSL 握手失败"
        print(f"[NET] 检测到{reason}，改为直连重试一次...")
        try:
            with requests.Session() as session:
                session.trust_env = False
                return session.request(method, url, timeout=timeout, **kwargs)
        except Exception:
            raise first_error


def _extract_image_bytes(data: dict, timeout: int, label: str) -> bytes:
    items = data.get("data") or []
    if not items:
        raise ValueError(f"{label}图片接口返回成功，但 data 为空。")

    first = items[0]
    encoded = first.get("b64_json") or first.get("base64")
    if encoded:
        return base64.b64decode(encoded)

    image_url = first.get("url")
    if image_url:
        image_response = request_with_proxy_fallback(
            "GET",
            image_url,
            timeout=timeout,
            headers={"Accept": "image/*"},
        )
        if image_response.status_code != 200:
            raise build_api_error(image_response.status_code, image_response.text, dict(image_response.headers))
        return image_response.content

    raise ValueError(f"{label}图片接口返回成功，但既没有 base64，也没有 url。")


def generate_image_via_gpt_image(
    prompt: str,
    api_key: str,
    base_url: str,
    model: str,
    timeout: int,
    size: str | None = None,
    quality: str | None = None,
    response_format: str | None = "b64_json",
    background: str | None = None,
) -> bytes:
    """调用 OpenAI 兼容图片接口生成图片。"""
    url = build_openai_compatible_url(base_url, "/images/generations")
    payload = {
        "model": model,
        "prompt": prompt,
    }
    if size:
        payload["size"] = size
    if quality:
        payload["quality"] = quality
    if response_format:
        payload["response_format"] = response_format
    if background:
        payload["background"] = background

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    print(f"[GPT-IMG] 正在生成图片... (timeout={timeout}s)")
    start = time.time()
    resp = request_with_proxy_fallback(
        "POST",
        url,
        json=payload,
        headers=headers,
        timeout=timeout,
    )

    if resp.status_code != 200:
        raise build_api_error(resp.status_code, resp.text, dict(resp.headers))

    data = resp.json()
    elapsed = time.time() - start
    print(f"[GPT-IMG] API 响应耗时: {elapsed:.1f}s")

    return _extract_image_bytes(data, timeout, "GPT-IMG")


def generate_image_via_gpt_image_edit(
    prompt: str,
    api_key: str,
    base_url: str,
    model: str,
    timeout: int,
    reference_images: list[str],
    size: str | None = None,
    quality: str | None = None,
    response_format: str | None = "b64_json",
    background: str | None = None,
) -> bytes:
    """使用本地参考图调用 GPT Image 编辑接口。"""
    url = build_openai_compatible_url(base_url, "/images/edits")
    form_data = {
        "model": model,
        "prompt": prompt,
    }
    if size:
        form_data["size"] = size
    if quality:
        form_data["quality"] = quality
    if response_format:
        form_data["response_format"] = response_format
    if background:
        form_data["background"] = background

    files = [
        ("image[]", (reference["path"].name, reference["data"], reference["mime_type"]))
        for reference in _load_reference_images(reference_images)
    ]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    print(f"[GPT-IMG-EDIT] 正在生成图片... (参考图 {len(files)} 张, timeout={timeout}s)")
    start = time.time()
    resp = request_with_proxy_fallback(
        "POST",
        url,
        data=form_data,
        files=files,
        headers=headers,
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise build_api_error(resp.status_code, resp.text, dict(resp.headers))

    elapsed = time.time() - start
    print(f"[GPT-IMG-EDIT] API 响应耗时: {elapsed:.1f}s")
    return _extract_image_bytes(resp.json(), timeout, "GPT-IMG-EDIT")


def generate_image_via_grok_image(
    prompt: str,
    api_key: str,
    base_url: str,
    model: str,
    timeout: int,
    response_format: str | None = "b64_json",
    aspect_ratio: str | None = None,
    resolution: str | None = None,
) -> bytes:
    """调用 xAI Imagine 的 OpenAI 兼容图片接口。"""
    url = build_openai_compatible_url(base_url, "/images/generations")
    payload = {
        "model": model,
        "prompt": prompt,
    }
    if aspect_ratio:
        payload["aspect_ratio"] = aspect_ratio
    if resolution:
        payload["resolution"] = resolution
    if response_format == "b64_json":
        payload["image_format"] = "base64"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    print(f"[GROK-IMG] 正在生成图片... (timeout={timeout}s)")
    start = time.time()
    resp = request_with_proxy_fallback(
        "POST",
        url,
        json=payload,
        headers=headers,
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise build_api_error(resp.status_code, resp.text, dict(resp.headers))

    data = resp.json()
    elapsed = time.time() - start
    print(f"[GROK-IMG] API 响应耗时: {elapsed:.1f}s")
    return _extract_image_bytes(data, timeout, "Grok")


def generate_image(
    prompt: str,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    timeout: int = 180,
    size: str | None = None,
    quality: str | None = None,
    response_format: str | None = "b64_json",
    background: str | None = None,
    aspect_ratio: str | None = None,
    resolution: str | None = None,
    reference_images: list[str] | None = None,
) -> bytes:
    """按 provider 调用对应图片接口，返回 PNG/JPEG 字节。"""
    normalized_provider = normalize_provider(provider)
    config = resolve_provider_config(
        provider=normalized_provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
    ensure_api_key(config, normalized_provider)

    if normalized_provider == "grok-imagine-image-quality":
        if reference_images:
            print("使用 Grok 生图时无法加载参考图链路", file=sys.stderr)
        return generate_image_via_grok_image(
            prompt=prompt,
            api_key=config["api_key"],
            base_url=config["base_url"],
            model=config["model"],
            timeout=timeout,
            response_format=response_format,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )

    if normalized_provider == "beeapi-gpt-image-2":
        if reference_images:
            return generate_image_via_gpt_image_edit(
                prompt=prompt,
                api_key=config["api_key"],
                base_url=config["base_url"],
                model=config["model"],
                timeout=timeout,
                reference_images=reference_images,
                size=size,
                quality=quality,
                response_format=response_format,
                background=background,
            )
        return generate_image_via_gpt_image(
            prompt=prompt,
            api_key=config["api_key"],
            base_url=config["base_url"],
            model=config["model"],
            timeout=timeout,
            size=size,
            quality=quality,
            response_format=response_format,
            background=background,
        )

    raise ValueError(f"未知 provider: {normalized_provider}")


def inspect_image_dimensions(img_bytes: bytes) -> tuple[int | None, int | None]:
    """尽量从图片字节中读取宽高。"""
    try:
        from PIL import Image
    except ImportError:
        return None, None

    with Image.open(io.BytesIO(img_bytes)) as img:
        return img.size


def _ensure_rgb_image(img):
    from PIL import Image

    if img.mode == "RGB":
        return img
    if img.mode in {"RGBA", "LA"} or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return img.convert("RGB")


def normalize_image_to_target_canvas(img_bytes: bytes, target_width: int, target_height: int):
    """无裁切校正到目标画布：前景等比缩放，背景使用同图模糊补边。"""
    try:
        from PIL import Image, ImageEnhance, ImageFilter
    except ImportError as exc:
        raise RuntimeError("需要 Pillow 才能执行图片比例校正。运行: pip install pillow") from exc

    with Image.open(io.BytesIO(img_bytes)) as raw_img:
        source = _ensure_rgb_image(raw_img)
        source_width, source_height = source.size

        fit_scale = min(target_width / source_width, target_height / source_height)
        fit_width = max(1, int(round(source_width * fit_scale)))
        fit_height = max(1, int(round(source_height * fit_scale)))
        foreground = source.resize((fit_width, fit_height), Image.LANCZOS)
        if fit_scale > 1.0:
            foreground = foreground.filter(ImageFilter.UnsharpMask(radius=1.15, percent=118, threshold=2))

        background_scale = max(target_width / source_width, target_height / source_height)
        bg_width = max(target_width, int(round(source_width * background_scale)))
        bg_height = max(target_height, int(round(source_height * background_scale)))
        background = source.resize((bg_width, bg_height), Image.LANCZOS)
        blur_radius = max(12, int(min(target_width, target_height) * 0.018))
        background = background.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        background = ImageEnhance.Brightness(background).enhance(0.82)

        left = max(0, (bg_width - target_width) // 2)
        top = max(0, (bg_height - target_height) // 2)
        canvas = background.crop((left, top, left + target_width, top + target_height))

        paste_x = (target_width - fit_width) // 2
        paste_y = (target_height - fit_height) // 2
        canvas.paste(foreground, (paste_x, paste_y))

    return canvas, {
        "source_width": source_width,
        "source_height": source_height,
        "width": target_width,
        "height": target_height,
        "scale": round(fit_scale, 4),
    }


def save_image(
    img_bytes: bytes,
    output_path: str,
    min_width: int = DEFAULT_MIN_WIDTH,
    min_height: int = DEFAULT_MIN_HEIGHT,
    strict_min_size: bool = False,
    upscale_to_min: bool = False,
) -> dict:
    """将图片字节保存到文件，并返回基础尺寸信息。"""
    width, height = inspect_image_dimensions(img_bytes)
    source_below_min = False
    normalized_meta: dict | None = None

    if width is not None and height is not None and min_width and min_height:
        source_below_min = width < min_width or height < min_height
        if source_below_min and strict_min_size and not upscale_to_min:
            raise ValueError(
                f"图片实际尺寸过低: {width}x{height}，低于目标 {min_width}x{min_height}"
            )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    if (
        upscale_to_min
        and width is not None
        and height is not None
        and min_width > 0
        and min_height > 0
        and (width != min_width or height != min_height)
    ):
        normalized_img, normalized_meta = normalize_image_to_target_canvas(
            img_bytes,
            min_width,
            min_height,
        )
        normalized_img.save(output_path, format="PNG", optimize=True)
        final_width = min_width
        final_height = min_height
        size_kb = os.path.getsize(output_path) / 1024
        print(
            f"[IMG] 图片已校正: {output_path} "
            f"({width}x{height} -> {final_width}x{final_height}, {size_kb:.0f} KB)"
        )
    else:
        with open(output_path, "wb") as f:
            f.write(img_bytes)
        final_width = width
        final_height = height
        size_kb = len(img_bytes) / 1024
        if width is not None and height is not None:
            print(f"[IMG] 图片已保存: {output_path} ({width}x{height}, {size_kb:.0f} KB)")
        else:
            print(f"[IMG] 图片已保存: {output_path} ({size_kb:.0f} KB)")
            print("[IMG] ⚠️ 当前无法读取图片实际宽高，请补做尺寸核验", file=sys.stderr)

    unresolved_below_min = (
        final_width is not None
        and final_height is not None
        and min_width
        and min_height
        and (final_width < min_width or final_height < min_height)
    )
    if source_below_min and not normalized_meta:
        print(
            f"[IMG] ⚠️ 实际尺寸低于目标 {min_width}x{min_height}，当前为 {width}x{height}；"
            "后续即使导出 1080×1920 也只会放大而不是真正增清晰度",
            file=sys.stderr,
        )
    if unresolved_below_min:
        print(
            f"[IMG] ⚠️ 校正后尺寸仍低于目标 {min_width}x{min_height}，当前为 {final_width}x{final_height}",
            file=sys.stderr,
        )

    return {
        "width": final_width,
        "height": final_height,
        "size_kb": size_kb,
        "below_min": bool(unresolved_below_min),
        "source_width": width,
        "source_height": height,
        "source_below_min": bool(source_below_min),
        "upscaled": normalized_meta is not None,
        "upscaled_from_width": normalized_meta["source_width"] if normalized_meta else None,
        "upscaled_from_height": normalized_meta["source_height"] if normalized_meta else None,
    }


def main():
    parser = argparse.ArgumentParser(description="统一图片生成")
    parser.add_argument("--prompt", type=str, help="图片生成提示词")
    parser.add_argument("--prompt-file", type=str, help="从文件读取提示词")
    parser.add_argument("--output", type=str, required=True, help="输出图片路径")
    parser.add_argument(
        "--provider",
        type=str,
        default=DEFAULT_PROVIDER,
        help="图片 provider：beeapi-gpt-image-2 或 grok-imagine-image-quality",
    )
    parser.add_argument("--fallback-provider", type=str, default=None, help="主 provider 失败后回退的 provider，例如 beeapi-gpt-image-2")
    parser.add_argument("--second-fallback-provider", type=str, default=None, help="二级回退 provider，例如 grok-imagine-image-quality")
    parser.add_argument("--api-key", type=str, default=None, help="API Key")
    parser.add_argument("--base-url", type=str, default=None, help="API Base URL")
    parser.add_argument("--model", type=str, default=None, help="模型名；默认随 provider 决定")
    parser.add_argument("--timeout", type=int, default=180, help="超时秒数")
    parser.add_argument("--retries", type=int, default=2, help="失败重试次数")
    parser.add_argument("--size", type=str, default=None, help="图片尺寸，例如 1024x1024；主要用于 gpt-image-2.5")
    parser.add_argument("--quality", type=str, default=None, help="图片质量参数；主要用于 gpt-image-2.5")
    parser.add_argument("--response-format", type=str, default="b64_json", help="返回格式；默认 b64_json")
    parser.add_argument("--background", type=str, default=None, help="背景参数；主要用于 gpt-image-2.5")
    parser.add_argument("--reference-image", action="append", dest="reference_images", help="本地参考图片路径；可重复指定")
    parser.add_argument("--aspect-ratio", type=str, default=None, help="宽高比；主要用于 Grok Imagine，例如 16:9")
    parser.add_argument("--resolution", type=str, default=None, help="分辨率档位；主要用于 Grok Imagine，例如 1k 或 2k")
    parser.add_argument("--min-width", type=int, default=DEFAULT_MIN_WIDTH, help="最小目标宽度，默认 0（不强制）")
    parser.add_argument("--min-height", type=int, default=DEFAULT_MIN_HEIGHT, help="最小目标高度，默认 0（不强制）")
    parser.add_argument("--strict-min-size", action="store_true", help="实际尺寸低于目标时直接失败")
    parser.add_argument("--upscale-to-min", action="store_true", help="无裁切校正到最小目标尺寸，并做轻锐化")
    args = parser.parse_args()

    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
    elif args.prompt:
        prompt = args.prompt
    else:
        print("错误：必须提供 --prompt 或 --prompt-file", file=sys.stderr)
        sys.exit(1)

    provider_chain = [args.provider]
    if args.fallback_provider:
        provider_chain.append(args.fallback_provider)
    if args.second_fallback_provider:
        provider_chain.append(args.second_fallback_provider)

    last_error: Exception | None = None
    for provider_index, active_provider in enumerate(provider_chain):
        if provider_index > 0:
            print(f"[IMG] 切换到回退 provider: {active_provider}")

        for attempt in range(args.retries + 1):
            try:
                img_bytes = generate_image(
                    prompt=prompt,
                    provider=active_provider,
                    api_key=args.api_key if provider_index == 0 else None,
                    base_url=args.base_url if provider_index == 0 else None,
                    model=args.model if provider_index == 0 else None,
                    timeout=args.timeout,
                    size=args.size,
                    quality=args.quality,
                    response_format=args.response_format,
                    background=args.background,
                    aspect_ratio=args.aspect_ratio,
                    resolution=args.resolution,
                    reference_images=args.reference_images,
                )
                save_image(
                    img_bytes,
                    args.output,
                    min_width=args.min_width,
                    min_height=args.min_height,
                    strict_min_size=args.strict_min_size,
                    upscale_to_min=args.upscale_to_min,
                )
                print(f"[IMG] ✅ 生成成功: {args.output}")
                print(f"[IMG] provider={active_provider}")
                return
            except ImageGenerationError as e:
                last_error = e
                print(f"[IMG] ⚠️ 第 {attempt + 1} 次尝试失败 ({active_provider}): {e}", file=sys.stderr)
                if not e.retryable:
                    if e.charge_risk:
                        print(
                            "[IMG] 检测到 524/origin timeout。该请求可能已在服务端继续执行并计费，停止当前 provider 的自动重试。",
                            file=sys.stderr,
                        )
                    else:
                        print("[IMG] 检测到不可安全重试的错误，停止当前 provider 的自动重试。", file=sys.stderr)
                    break

                if attempt < args.retries:
                    wait = e.retry_after or (5 * (attempt + 1))
                    print(f"[IMG] 等待 {wait}s 后重试...")
                    time.sleep(wait)
                else:
                    print(f"[IMG] 当前 provider {active_provider} 尝试失败", file=sys.stderr)
            except Exception as e:
                last_error = e
                print(f"[IMG] ⚠️ 第 {attempt + 1} 次尝试失败 ({active_provider}): {e}", file=sys.stderr)
                if attempt < args.retries:
                    wait = 5 * (attempt + 1)
                    print(f"[IMG] 等待 {wait}s 后重试...")
                    time.sleep(wait)
                else:
                    print(f"[IMG] 当前 provider {active_provider} 尝试失败", file=sys.stderr)

    print(f"[IMG] ❌ 所有 provider 均失败。最后错误: {last_error}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
