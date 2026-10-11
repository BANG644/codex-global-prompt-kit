"""
HTML 预览质检脚本 — 将图片目录中的所有图片压缩后生成 HTML 预览页。
用法：
  python scripts/build_html_preview.py --input-dir "选题文件夹" --output "preview/review.html"

⚠️ 此脚本是图片质检的唯一合法途径。绝对禁止直接读取原图。
"""

import argparse
import os
import re
import subprocess
import sys

try:
    from PIL import Image
except ImportError:
    print("错误：需要安装 Pillow。运行: pip install pillow", file=sys.stderr)
    sys.exit(1)


def image_sort_key(name: str) -> tuple:
    stem = os.path.splitext(name)[0]
    if stem == "封面":
        return (0, 0, stem)
    if stem.isdigit():
        return (1, int(stem), stem)
    natural_parts = [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", stem)]
    return (2, natural_parts, stem)


def ensure_jpeg_compatible(img: Image.Image) -> Image.Image:
    if img.mode == "RGB":
        return img

    if img.mode in {"RGBA", "LA"} or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background

    return img.convert("RGB")


def console_print(message: str, *, stream=None) -> None:
    stream = sys.stdout if stream is None else stream
    text = message
    encoding = getattr(stream, "encoding", None)

    if encoding:
        try:
            text.encode(encoding)
        except UnicodeEncodeError:
            text = text.encode(encoding, errors="backslashreplace").decode(encoding)

    stream.write(text + "\n")
    stream.flush()

def build_html_preview(
    img_dir: str,
    html_path: str,
    max_dim: int = 1000,
    quality: int = 82,
) -> str:
    """
    将 img_dir 下的所有 PNG/JPG 压缩后写入 HTML 预览页。

    Args:
        img_dir: 图片所在目录
        html_path: 输出 HTML 文件路径
        max_dim: 预览图最大边长（像素）
        quality: JPEG 压缩质量

    Returns:
        HTML 文件路径
    """
    os.makedirs(os.path.dirname(html_path) or ".", exist_ok=True)
    preview_dir = os.path.splitext(html_path)[0] + "_assets"
    os.makedirs(preview_dir, exist_ok=True)

    exts = (".png", ".jpg", ".jpeg")
    imgs = sorted(
        [f for f in os.listdir(img_dir) if f.lower().endswith(exts) and not f.startswith(".")],
        key=image_sort_key,
    )

    if not imgs:
        console_print(f"[预览][WARN] 未在 {img_dir} 找到任何图片文件")
        return html_path

    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>图片质检预览</title>
<style>
body { background: #111; padding: 20px; font-family: 'Segoe UI', sans-serif; color: #fff; }
h1 { color: #fff; border-bottom: 2px solid #333; padding-bottom: 10px; }
.card { margin: 20px 0; padding: 15px; background: #1a1a1a; border-radius: 8px; }
.card h3 { color: #4af; margin: 0 0 10px 0; }
.card .meta { color: #888; font-size: 14px; margin-bottom: 10px; }
.card img { max-width: 100%; border: 2px solid #333; border-radius: 4px; }
.summary { background: #1a2a1a; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
.summary p { margin: 5px 0; }
</style>
</head>
<body>
<h1>📷 图片质检预览</h1>
"""

    html += f'<div class="summary">\n'
    html += f'<p><strong>图片目录：</strong>{os.path.abspath(img_dir)}</p>\n'
    html += f'<p><strong>图片数量：</strong>{len(imgs)} 张</p>\n'
    html += f'<p><strong>预览尺寸：</strong>长边 ≤ {max_dim}px</p>\n'
    html += '</div>\n'

    for fname in imgs:
        src = os.path.join(img_dir, fname)
        try:
            img = Image.open(src)
            w, h = img.size
            ratio = min(1.0, max_dim / max(w, h))
            nw, nh = int(w * ratio), int(h * ratio)

            preview_name = os.path.splitext(fname)[0] + "_preview.jpg"
            preview_path = os.path.join(preview_dir, preview_name)
            preview_img = ensure_jpeg_compatible(img.resize((nw, nh), Image.LANCZOS))
            preview_img.save(preview_path, format="JPEG", quality=quality)

            rel_path = os.path.join(
                os.path.basename(preview_dir), preview_name
            ).replace("\\", "/")

            html += f'<div class="card">\n'
            html += f'  <h3>{fname}</h3>\n'
            html += f'  <div class="meta">原始尺寸: {w}×{h} | 预览尺寸: {nw}×{nh}</div>\n'
            html += f'  <img src="{rel_path}" alt="{fname}">\n'
            html += f'</div>\n'
        except Exception as e:
            html += f'<div class="card">\n'
            html += f'  <h3 style="color:#f44">{fname} — 处理失败</h3>\n'
            html += f'  <div class="meta">错误: {e}</div>\n'
            html += f'</div>\n'
            console_print(f"[预览][FAIL] {fname} 处理失败: {e}", stream=sys.stderr)
            continue

        console_print(f"[预览][OK] {fname} [{w}×{h}] -> 预览 [{nw}×{nh}]")

    html += "</body>\n</html>"

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    console_print(f"\n[预览] HTML 生成完成: {html_path}")
    return html_path


def main():
    parser = argparse.ArgumentParser(description="图片质检 HTML 预览生成")
    parser.add_argument("--input-dir", required=True, help="图片所在目录")
    parser.add_argument("--output", default=None, help="输出 HTML 路径（默认在 input-dir/preview/review.html）")
    parser.add_argument("--max-dim", type=int, default=1000, help="预览图最大边长")
    parser.add_argument("--quality", type=int, default=82, help="JPEG 压缩质量")
    parser.add_argument("--open", action="store_true", help="生成后自动在浏览器中打开")
    args = parser.parse_args()

    output = args.output or os.path.join(args.input_dir, "preview", "review.html")

    html_path = build_html_preview(
        img_dir=args.input_dir,
        html_path=output,
        max_dim=args.max_dim,
        quality=args.quality,
    )

    if args.open:
        abs_path = os.path.abspath(html_path)
        if sys.platform == "win32":
            subprocess.Popen(["start", abs_path], shell=True)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", abs_path])
        else:
            subprocess.Popen(["xdg-open", abs_path])
        console_print("[预览][OPEN] 已在浏览器中打开")


if __name__ == "__main__":
    main()

