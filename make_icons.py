"""Génère les icônes PNG de l'application (sans dépendance : zlib + struct).

Usage :  python scripts/make_icons.py
Produit static/images/icon-192.png, icon-512.png et icon-maskable-512.png.
"""
import struct
import zlib
from pathlib import Path

VIOLET_TOP = (124, 58, 237)
VIOLET_BOTTOM = (91, 33, 182)
WHITE = (255, 255, 255)

# Éclair, coordonnées normalisées (0..1) dans un carré
BOLT = [(0.57, 0.12), (0.30, 0.55), (0.48, 0.55), (0.40, 0.88), (0.72, 0.42), (0.53, 0.42), (0.62, 0.12)]


def inside(x, y, poly):
    """Test point-dans-polygone (lancer de rayon)."""
    ok, j = False, len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            ok = not ok
        j = i
    return ok


def render(size, maskable):
    # Zone « sûre » : pour une icône maskable, l'éclair reste dans les 60 % centraux
    scale = 0.6 if maskable else 0.82
    off = (1 - scale) / 2
    poly = [(off + bx * scale, off + by * scale) for bx, by in BOLT]
    radius = 0 if maskable else size * 0.22
    rows = []
    for py in range(size):
        t = py / (size - 1)
        bg = tuple(round(VIOLET_TOP[k] + (VIOLET_BOTTOM[k] - VIOLET_TOP[k]) * t) for k in range(3))
        row = bytearray([0])  # filtre PNG « aucun »
        for px in range(size):
            # coins arrondis (transparents) pour l'icône non maskable
            alpha = 255
            if radius:
                cx = min(max(px, radius), size - 1 - radius)
                cy = min(max(py, radius), size - 1 - radius)
                if (px - cx) ** 2 + (py - cy) ** 2 > radius ** 2:
                    alpha = 0
            # sur-échantillonnage 2x2 pour lisser l'éclair
            hits = sum(inside((px + dx) / size, (py + dy) / size, poly) for dx in (.25, .75) for dy in (.25, .75))
            mix = hits / 4
            color = tuple(round(bg[k] * (1 - mix) + WHITE[k] * mix) for k in range(3))
            row += bytes(color) + bytes([alpha])
        rows.append(bytes(row))
    return b"".join(rows)


def png(size, maskable=False):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # RGBA 8 bits
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(render(size, maskable), 9)) + chunk(b"IEND", b""))


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "static" / "images"
    out.mkdir(parents=True, exist_ok=True)
    for name, size, maskable in [("icon-192.png", 192, False), ("icon-512.png", 512, False),
                                 ("icon-maskable-512.png", 512, True)]:
        (out / name).write_bytes(png(size, maskable))
        print("écrit", out / name)
