"""Generated placeholder vehicle imagery (public).

Produces deterministic "studio" SVG frames so the gallery and 360° viewer have colourful, scannable
images without shipping binary assets, hotlinking, or fabricating real photographs. Every frame is
watermarked DEMO. When a provider feed supplies real ``image_urls``, the UI uses those instead.

Public (no auth) because the URLs are referenced directly from <img> tags; the output contains no
dealership data — only generated art derived from a seed string.
"""

from __future__ import annotations

import hashlib
import math

from fastapi import APIRouter, Query, Response

router = APIRouter(prefix="/media", tags=["media"])

SHOT_LABELS = ["Front 3/4", "Nearside", "Rear 3/4", "Interior", "Alloy wheel", "Engine bay"]


def _hue(seed: str) -> int:
    return int(hashlib.sha256(seed.encode()).hexdigest(), 16) % 360


def _svg_header(w: int, h: int, hue: int, floor_hue: int) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" \
viewBox="0 0 {w} {h}" role="img">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="hsl({hue},45%,26%)"/>
      <stop offset="55%" stop-color="hsl({hue},40%,17%)"/>
      <stop offset="100%" stop-color="hsl({(hue + 20) % 360},35%,10%)"/>
    </linearGradient>
    <radialGradient id="spot" cx="50%" cy="32%" r="75%">
      <stop offset="0%" stop-color="hsla({(hue + 30) % 360},70%,70%,0.55)"/>
      <stop offset="60%" stop-color="hsla({hue},50%,30%,0)"/>
    </radialGradient>
    <radialGradient id="floor" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="hsla({floor_hue},30%,60%,0.35)"/>
      <stop offset="100%" stop-color="hsla({floor_hue},30%,10%,0)"/>
    </radialGradient>
    <linearGradient id="body" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="hsl({floor_hue},55%,72%)"/>
      <stop offset="100%" stop-color="hsl({floor_hue},45%,42%)"/>
    </linearGradient>
  </defs>
  <rect width="{w}" height="{h}" fill="url(#bg)"/>
  <rect width="{w}" height="{h}" fill="url(#spot)"/>"""


def _wheel(cx: float, cy: float, r: float) -> str:
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#111"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r * 0.55}" fill="#c9ced6"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r * 0.18}" fill="#6b7280"/>')


def _car(w: int, h: int, floor_hue: int, sx: float) -> str:
    """A stylised car body horizontally scaled by ``sx`` to fake a turn (1=side, ~0.28=head-on)."""
    cx, cy = w / 2, h * 0.6
    bw = 300 * sx
    body = (
        f'<g transform="translate({cx},{cy})">'
        f'<ellipse cx="0" cy="120" rx="{max(70, bw * 0.95)}" ry="26" fill="url(#floor)"/>'
        f'<g transform="scale({sx},1)">'
        f'<path d="M -300 60 Q -300 20 -250 10 L -170 10 Q -120 -60 -40 -66 L 90 -66 '
        f'Q 180 -60 250 10 L 300 20 Q 320 30 300 62 L 260 66 Q 250 96 220 96 Q 190 96 182 66 '
        f'L -182 66 Q -190 96 -220 96 Q -250 96 -260 66 Z" fill="url(#body)" '
        f'stroke="hsl({floor_hue},50%,80%)" stroke-width="2"/>'
        f'<path d="M -150 6 Q -110 -46 -44 -50 L 84 -50 Q 150 -46 180 6 Z" '
        f'fill="hsla(210,40%,88%,0.85)"/>'
        f'<line x1="20" y1="-50" x2="20" y2="6" stroke="hsl({floor_hue},40%,60%)" stroke-width="3"/>'
        f'</g>'
    )
    # Wheels: two when side-on, they slide together as the car turns head-on.
    wheel_dx = 150 * sx
    body += _wheel(-wheel_dx, 70, 34) + _wheel(wheel_dx, 70, 34)
    body += '</g>'
    return body


def _interior(w: int, h: int, hue: int) -> str:
    cx, cy = w / 2, h * 0.58
    return (
        f'<g transform="translate({cx},{cy})">'
        f'<rect x="-320" y="-40" width="640" height="150" rx="18" fill="hsl({hue},18%,18%)"/>'
        f'<rect x="-300" y="-20" width="270" height="120" rx="14" fill="hsl({hue},20%,26%)"/>'
        f'<rect x="30" y="-20" width="270" height="120" rx="14" fill="hsl({hue},20%,26%)"/>'
        f'<rect x="-250" y="-60" width="500" height="40" rx="10" fill="hsl({hue},15%,12%)"/>'
        f'<circle cx="-150" cy="-40" r="26" fill="none" stroke="hsl({hue},30%,60%)" stroke-width="8"/>'
        f'<rect x="60" y="-52" width="150" height="26" rx="6" fill="hsl({(hue+40)%360},50%,45%)"/>'
        f'</g>'
    )


def _wheel_shot(w: int, h: int, hue: int) -> str:
    cx, cy = w / 2, h * 0.55
    spokes = "".join(
        f'<line x1="{cx}" y1="{cy}" x2="{cx + 120 * math.cos(a)}" y2="{cy + 120 * math.sin(a)}" '
        f'stroke="#c9ced6" stroke-width="14" stroke-linecap="round"/>'
        for a in [i * math.pi / 2.5 for i in range(5)]
    )
    return (f'<circle cx="{cx}" cy="{cy}" r="150" fill="#111"/>'
            f'<circle cx="{cx}" cy="{cy}" r="128" fill="hsl({hue},12%,22%)"/>'
            f'{spokes}<circle cx="{cx}" cy="{cy}" r="34" fill="#6b7280"/>')


def _engine(w: int, h: int, hue: int) -> str:
    cx, cy = w / 2, h * 0.58
    blocks = "".join(
        f'<rect x="{cx - 260 + (i % 4) * 130}" y="{cy - 60 + (i // 4) * 70}" width="110" height="54" '
        f'rx="8" fill="hsl({(hue + i * 25) % 360},22%,{30 + (i % 3) * 8}%)"/>'
        for i in range(8)
    )
    return f'<g>{blocks}</g>'


def _footer(w: int, h: int, label: str, shot: str, angle: int | None) -> str:
    ang = f" · {angle}°" if angle is not None else ""
    return (
        f'<rect x="0" y="{h - 46}" width="{w}" height="46" fill="rgba(0,0,0,0.35)"/>'
        f'<text x="18" y="{h - 17}" font-family="Inter,Segoe UI,sans-serif" font-size="18" '
        f'font-weight="700" fill="#fff">{label}</text>'
        f'<text x="{w - 18}" y="{h - 17}" text-anchor="end" font-family="Inter,sans-serif" '
        f'font-size="13" fill="#cbd5e1">{shot}{ang}</text>'
        f'<rect x="{w - 78}" y="14" width="60" height="24" rx="12" fill="rgba(255,255,255,0.14)"/>'
        f'<text x="{w - 48}" y="30" text-anchor="middle" font-family="Inter,sans-serif" '
        f'font-size="12" font-weight="700" fill="#fff">DEMO</text>'
    )


@router.get("/car.svg")
def car_svg(
    seed: str = Query("AUTOBID"),
    label: str = Query("Vehicle"),
    shot: int = Query(0, ge=0, le=5),
    angle: int | None = Query(None, ge=0, le=359),
):
    w, h = 720, 460
    hue = _hue(seed)
    floor_hue = (hue + 140) % 360
    label = label[:40]

    body_angle = angle if angle is not None else [30, 0, 150, 0, 0, 0][shot]
    scene_shot = 1 if angle is not None else shot  # spin frames use the exterior body

    parts = [_svg_header(w, h, hue, floor_hue)]
    if scene_shot in (0, 1, 2):
        sx = 0.28 + 0.72 * abs(math.cos(math.radians(body_angle)))
        parts.append(_car(w, h, floor_hue, sx))
    elif scene_shot == 3:
        parts.append(_interior(w, h, hue))
    elif scene_shot == 4:
        parts.append(_wheel_shot(w, h, hue))
    else:
        parts.append(_engine(w, h, hue))
    parts.append(_footer(w, h, label, SHOT_LABELS[scene_shot], angle))
    parts.append("</svg>")

    return Response(
        content="".join(parts),
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )
