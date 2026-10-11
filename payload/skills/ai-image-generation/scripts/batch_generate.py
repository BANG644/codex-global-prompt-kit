"""最多 5 路并发的批量图片生成脚本。"""

from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_image import ImageGenerationError, generate_image, save_image


MAX_CONCURRENCY = 5
FALLBACK_STATUSES = {429, 500, 502, 503, 504}


def _can_fallback(error: Exception | None) -> bool:
    if not isinstance(error, ImageGenerationError):
        return False
    response_text = (error.response_text or "").lower()
    return (
        error.status_code in FALLBACK_STATUSES
        or "origin_gateway_timeout" in response_text
        or "gateway timeout" in response_text
        or "timed out" in response_text
    )


def _provider_chain(
    *,
    provider: str,
    api_key: str | None,
    base_url: str | None,
    model: str | None,
    size: str | None,
    quality: str | None,
    response_format: str,
    background: str | None,
    fallback_provider: str | None,
    fallback_api_key: str | None,
    fallback_base_url: str | None,
    fallback_model: str | None,
    fallback_size: str | None,
    fallback_quality: str | None,
    fallback_response_format: str | None,
    fallback_background: str | None,
    second_fallback_provider: str | None,
    second_fallback_api_key: str | None,
    second_fallback_base_url: str | None,
    second_fallback_model: str | None,
    second_fallback_size: str | None,
    second_fallback_quality: str | None,
    second_fallback_response_format: str | None,
    second_fallback_background: str | None,
) -> list[dict]:
    chain = [
        {
            "provider": provider,
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "size": size,
            "quality": quality,
            "response_format": response_format,
            "background": background,
        }
    ]
    if fallback_provider:
        chain.append(
            {
                "provider": fallback_provider,
                "api_key": fallback_api_key,
                "base_url": fallback_base_url,
                "model": fallback_model,
                "size": fallback_size,
                "quality": fallback_quality,
                "response_format": fallback_response_format or response_format,
                "background": fallback_background,
            }
        )
    if second_fallback_provider:
        chain.append(
            {
                "provider": second_fallback_provider,
                "api_key": second_fallback_api_key,
                "base_url": second_fallback_base_url,
                "model": second_fallback_model,
                "size": second_fallback_size,
                "quality": second_fallback_quality,
                "response_format": second_fallback_response_format or response_format,
                "background": second_fallback_background,
            }
        )
    return chain


def _generate_one(
    *,
    prompt_file: str,
    prompts_dir: str,
    output_dir: str,
    timeout: int,
    retries: int,
    min_width: int,
    min_height: int,
    strict_min_size: bool,
    upscale_to_min: bool,
    reference_images: list[str] | None,
    provider_chain: list[dict],
) -> dict:
    stem = os.path.splitext(prompt_file)[0]
    output_path = os.path.join(output_dir, f"{stem}.png")
    prompt_path = os.path.join(prompts_dir, prompt_file)

    with open(prompt_path, "r", encoding="utf-8") as prompt_handle:
        prompt = prompt_handle.read().strip()

    last_error: Exception | None = None
    active_provider = provider_chain[0]["provider"]
    for provider_index, config in enumerate(provider_chain):
        active_provider = config["provider"]
        if provider_index > 0:
            if not _can_fallback(last_error):
                break
            print(f"[批量] {stem}: 回退到 {active_provider}")

        for attempt in range(retries + 1):
            try:
                image_bytes = generate_image(
                    prompt=prompt,
                    provider=active_provider,
                    api_key=config["api_key"],
                    base_url=config["base_url"],
                    model=config["model"],
                    timeout=timeout,
                    size=config["size"],
                    quality=config["quality"],
                    response_format=config["response_format"],
                    background=config["background"],
                    reference_images=reference_images,
                )
                meta = save_image(
                    image_bytes,
                    output_path,
                    min_width=min_width,
                    min_height=min_height,
                    strict_min_size=strict_min_size,
                    upscale_to_min=upscale_to_min,
                )
                print(f"[批量] 成功: {stem}.png provider={active_provider}")
                return {
                    "prompt_file": prompt_file,
                    "file": os.path.basename(output_path),
                    "output_path": output_path,
                    "status": "success",
                    "provider": active_provider,
                    "width": meta.get("width"),
                    "height": meta.get("height"),
                    "size_kb": round(meta.get("size_kb"), 1) if meta.get("size_kb") is not None else None,
                    "source_width": meta.get("source_width"),
                    "source_height": meta.get("source_height"),
                    "source_below_min": bool(meta.get("source_below_min")),
                    "below_min": bool(meta.get("below_min")),
                    "upscaled": bool(meta.get("upscaled")),
                    "upscaled_from_width": meta.get("upscaled_from_width"),
                    "upscaled_from_height": meta.get("upscaled_from_height"),
                }
            except ImageGenerationError as error:
                last_error = error
                print(f"[批量] 失败: {stem}.png 第 {attempt + 1} 次 ({active_provider}): {error}")
                if not error.retryable:
                    break
                if attempt < retries:
                    wait = error.retry_after or (5 * (attempt + 1))
                    time.sleep(wait)
            except Exception as error:
                last_error = error
                print(f"[批量] 失败: {stem}.png 第 {attempt + 1} 次 ({active_provider}): {error}")
                if attempt < retries:
                    time.sleep(5 * (attempt + 1))

    return {
        "prompt_file": prompt_file,
        "file": os.path.basename(output_path),
        "output_path": output_path,
        "status": "failed",
        "provider": active_provider,
        "error": str(last_error or "图片生成失败"),
    }


def batch_generate(
    prompts_dir: str,
    output_dir: str,
    delay: int = 5,
    timeout: int = 180,
    retries: int = 2,
    provider: str = "beeapi-gpt-image-2",
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    size: str | None = None,
    quality: str | None = None,
    response_format: str = "b64_json",
    background: str | None = None,
    reference_images: list[str] | None = None,
    fallback_provider: str | None = "grok-imagine-image-quality",
    fallback_api_key: str | None = None,
    fallback_base_url: str | None = None,
    fallback_model: str | None = None,
    fallback_size: str | None = None,
    fallback_quality: str | None = None,
    fallback_response_format: str | None = None,
    fallback_background: str | None = None,
    second_fallback_provider: str | None = None,
    second_fallback_api_key: str | None = None,
    second_fallback_base_url: str | None = None,
    second_fallback_model: str | None = None,
    second_fallback_size: str | None = None,
    second_fallback_quality: str | None = None,
    second_fallback_response_format: str | None = None,
    second_fallback_background: str | None = None,
    min_width: int = 0,
    min_height: int = 0,
    strict_min_size: bool = False,
    upscale_to_min: bool = False,
    skip_existing: bool = False,
    max_concurrency: int = MAX_CONCURRENCY,
) -> dict:
    if not 1 <= max_concurrency <= MAX_CONCURRENCY:
        raise ValueError(f"max_concurrency 必须在 1-{MAX_CONCURRENCY} 之间")

    os.makedirs(output_dir, exist_ok=True)
    prompt_files = sorted(f for f in os.listdir(prompts_dir) if f.endswith(".txt"))
    if not prompt_files:
        print(f"[批量] 警告：未在 {prompts_dir} 找到任何 .txt 提示词文件")
        return {"success": [], "failed": [], "below_min": [], "skipped": [], "upscaled": [], "image_results": []}

    provider_chain = _provider_chain(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
        size=size,
        quality=quality,
        response_format=response_format,
        background=background,
        fallback_provider=fallback_provider,
        fallback_api_key=fallback_api_key,
        fallback_base_url=fallback_base_url,
        fallback_model=fallback_model,
        fallback_size=fallback_size,
        fallback_quality=fallback_quality,
        fallback_response_format=fallback_response_format,
        fallback_background=fallback_background,
        second_fallback_provider=second_fallback_provider,
        second_fallback_api_key=second_fallback_api_key,
        second_fallback_base_url=second_fallback_base_url,
        second_fallback_model=second_fallback_model,
        second_fallback_size=second_fallback_size,
        second_fallback_quality=second_fallback_quality,
        second_fallback_response_format=second_fallback_response_format,
        second_fallback_background=second_fallback_background,
    )

    results_by_file: dict[str, dict] = {}
    pending_files: list[str] = []
    for prompt_file in prompt_files:
        output_path = os.path.join(output_dir, f"{os.path.splitext(prompt_file)[0]}.png")
        if skip_existing and os.path.exists(output_path):
            results_by_file[prompt_file] = {
                "prompt_file": prompt_file,
                "file": os.path.basename(output_path),
                "output_path": output_path,
                "status": "skipped",
            }
        else:
            pending_files.append(prompt_file)

    print(f"[批量] 找到 {len(prompt_files)} 个提示词，最大并发: {max_concurrency}")
    if fallback_provider:
        print(f"[批量] 回退 provider: {fallback_provider}")

    stopped_after_wave = False
    for wave_start in range(0, len(pending_files), max_concurrency):
        wave = pending_files[wave_start:wave_start + max_concurrency]
        print(f"[批量] 启动第 {wave_start // max_concurrency + 1} 波: {len(wave)} 张")
        with ThreadPoolExecutor(max_workers=len(wave), thread_name_prefix="image-gen") as executor:
            futures = {
                executor.submit(
                    _generate_one,
                    prompt_file=prompt_file,
                    prompts_dir=prompts_dir,
                    output_dir=output_dir,
                    timeout=timeout,
                    retries=retries,
                    min_width=min_width,
                    min_height=min_height,
                    strict_min_size=strict_min_size,
                    upscale_to_min=upscale_to_min,
                    reference_images=reference_images,
                    provider_chain=provider_chain,
                ): prompt_file
                for prompt_file in wave
            }
            for future in as_completed(futures):
                prompt_file = futures[future]
                try:
                    results_by_file[prompt_file] = future.result()
                except Exception as error:
                    results_by_file[prompt_file] = {
                        "prompt_file": prompt_file,
                        "file": f"{os.path.splitext(prompt_file)[0]}.png",
                        "output_path": os.path.join(output_dir, f"{os.path.splitext(prompt_file)[0]}.png"),
                        "status": "failed",
                        "provider": provider,
                        "error": str(error),
                    }

        wave_failed = any(results_by_file[prompt_file]["status"] == "failed" for prompt_file in wave)
        if wave_failed:
            stopped_after_wave = True
            print("[批量] 本波出现失败，取消后续波次；并发硬上限仍为 5。")
            break
        if wave_start + max_concurrency < len(pending_files) and delay > 0:
            time.sleep(delay)

    ordered_results = [results_by_file[prompt_file] for prompt_file in prompt_files if prompt_file in results_by_file]
    results = {"success": [], "failed": [], "below_min": [], "skipped": [], "upscaled": [], "image_results": ordered_results}
    for item in ordered_results:
        if item["status"] == "success":
            results["success"].append(item["output_path"])
            if item.get("below_min"):
                results["below_min"].append((item["output_path"], item.get("width"), item.get("height")))
            if item.get("upscaled"):
                results["upscaled"].append((item["output_path"], item.get("upscaled_from_width"), item.get("upscaled_from_height"), item.get("width"), item.get("height")))
        elif item["status"] == "skipped":
            results["skipped"].append(item["output_path"])
        elif item["status"] == "failed":
            results["failed"].append((item["prompt_file"], item.get("error", "图片生成失败")))

    print("=" * 50)
    print(f"[批量] 完成：成功 {len(results['success'])} / 跳过 {len(results['skipped'])} / 失败 {len(results['failed'])}")
    if stopped_after_wave:
        print("[批量] 已停止后续波次，避免发出超过 5 路的并发请求。")
    print("=" * 50)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="最多 5 路并发的批量图片生成")
    parser.add_argument("--prompts-dir", required=True, help="提示词文件目录")
    parser.add_argument("--output-dir", required=True, help="图片输出目录")
    parser.add_argument("--delay", type=int, default=5, help="每波之间的等待秒数")
    parser.add_argument("--timeout", type=int, default=180, help="API 超时秒数")
    parser.add_argument("--retries", type=int, default=2, help="单张失败重试次数")
    parser.add_argument("--provider", type=str, default="beeapi-gpt-image-2", help="主 provider：beeapi-gpt-image-2")
    parser.add_argument("--api-key", type=str, default=None, help="主 provider API Key")
    parser.add_argument("--base-url", type=str, default=None, help="主 provider API Base URL")
    parser.add_argument("--model", type=str, default=None, help="模型名")
    parser.add_argument("--size", type=str, default=None, help="图片尺寸，例如 1024x1024")
    parser.add_argument("--quality", type=str, default=None, help="图片质量参数")
    parser.add_argument("--response-format", type=str, default="b64_json", help="返回格式")
    parser.add_argument("--background", type=str, default=None, help="背景参数")
    parser.add_argument("--reference-image", action="append", dest="reference_images", help="本地参考图片路径；可重复指定")
    parser.add_argument("--fallback-provider", type=str, default="grok-imagine-image-quality", help="主 provider 服务端故障时回退的 provider")
    parser.add_argument("--second-fallback-provider", type=str, default=None, help="二级回退 provider")
    parser.add_argument("--min-width", type=int, default=0, help="最小目标宽度")
    parser.add_argument("--min-height", type=int, default=0, help="最小目标高度")
    parser.add_argument("--strict-min-size", action="store_true", help="实际尺寸低于目标时直接失败")
    parser.add_argument("--skip-existing", action="store_true", help="跳过已有同名图片")
    parser.add_argument("--max-concurrency", type=int, default=MAX_CONCURRENCY, help="并发数，硬上限为 5")
    args = parser.parse_args()

    batch_generate(
        prompts_dir=args.prompts_dir,
        output_dir=args.output_dir,
        delay=args.delay,
        timeout=args.timeout,
        retries=args.retries,
        provider=args.provider,
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        size=args.size,
        quality=args.quality,
        response_format=args.response_format,
        background=args.background,
        reference_images=args.reference_images,
        fallback_provider=args.fallback_provider,
        second_fallback_provider=args.second_fallback_provider,
        min_width=args.min_width,
        min_height=args.min_height,
        strict_min_size=args.strict_min_size,
        skip_existing=args.skip_existing,
        max_concurrency=args.max_concurrency,
    )


if __name__ == "__main__":
    main()
