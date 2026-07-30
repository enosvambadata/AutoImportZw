"""Blur the background of vehicle photos so auction-house signage (IAA/AA boards, watermarks) is not
legible, while keeping the car itself sharp.

Primary path: segment the car with rembg (u2netp) and blur everything behind it — a clean, studio-like
depth-of-field that reduces wall logos and watermarks to soft smudges. If rembg is unavailable at
runtime, fall back to a centre-ellipse heuristic so uploads never fail.
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter

_session = None
_session_failed = False


def _radius(short: int) -> int:
    return max(20, min(72, round(short * 0.03)))


def _get_session():
    global _session, _session_failed
    if _session is None and not _session_failed:
        try:
            from rembg import new_session
            _session = new_session("u2netp")
        except Exception:
            _session_failed = True
    return _session


def _segmented(img: Image.Image) -> Image.Image | None:
    session = _get_session()
    if session is None:
        return None
    try:
        from rembg import remove
        mask = remove(img, only_mask=True, session=session).filter(ImageFilter.GaussianBlur(4))
        blurred = img.filter(ImageFilter.GaussianBlur(_radius(min(img.size))))
        return Image.composite(img, blurred, mask)
    except Exception:
        return None


def _heuristic(img: Image.Image) -> Image.Image:
    w, h = img.size
    short = min(w, h)
    blurred = img.filter(ImageFilter.GaussianBlur(max(18, min(70, round(short * 0.055)))))
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([int(w * 0.09), int(h * 0.36), int(w * 0.91), int(h * 0.95)], fill=255)
    draw.rectangle([0, 0, w, int(h * 0.30)], fill=0)
    draw.rectangle([int(w * 0.70), int(h * 0.78), w, h], fill=0)
    draw.rectangle([0, int(h * 0.78), int(w * 0.30), h], fill=0)
    mask = mask.filter(ImageFilter.GaussianBlur(round(short * 0.05)))
    return Image.composite(img, blurred, mask)


def blur_background(data: bytes) -> bytes:
    img = Image.open(BytesIO(data)).convert("RGB")
    out = _segmented(img) or _heuristic(img)
    buf = BytesIO()
    out.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()
