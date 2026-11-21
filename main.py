#!/usr/bin/env python3
"""
THE DAILY SIGNAL -- a newspaper front page drawn entirely by this program.

Entry for make.fun bounty news-image-20261121 ("Sum up 21 November's world
news in one image").  Pure Python 3 standard library: the PNG encoder is
built on zlib, and every letter is drawn from a stroke (vector) font defined
below -- no PIL, no external fonts, no image assets.

The picture is rendered on a supersampled canvas and downsampled once, so
the output is smooth.  Nothing here reads the clock, randomness or the
environment to decide what to draw: two runs produce byte-identical PNGs.
"""

import math
import os
import struct
import zlib

# --------------------------------------------------------------------------
# Canvas
# --------------------------------------------------------------------------

W, H = 1024, 1024          # final image size
SS = 2                     # supersampling factor
DW, DH = W * SS, H * SS    # device (drawing) size

PAPER = (247, 243, 232)
INK = (20, 17, 12)
SOFT = (43, 38, 29)
MUTED = (96, 89, 76)
RED = (164, 22, 26)
HAIR = (120, 112, 96)

buf = bytearray(DW * DH * 3)


def _set(dx, dy, color):
    if 0 <= dx < DW and 0 <= dy < DH:
        i = (dy * DW + dx) * 3
        buf[i] = color[0]
        buf[i + 1] = color[1]
        buf[i + 2] = color[2]


def fill_rect(x, y, w, h, color):
    """Filled rectangle in layout (1024) coordinates."""
    x0 = int(round(x * SS)); y0 = int(round(y * SS))
    x1 = int(round((x + w) * SS)); y1 = int(round((y + h) * SS))
    if x0 < 0: x0 = 0
    if y0 < 0: y0 = 0
    if x1 > DW: x1 = DW
    if y1 > DH: y1 = DH
    r, g, b = color
    row = bytes((r, g, b)) * (x1 - x0)
    for dy in range(y0, y1):
        i = (dy * DW + x0) * 3
        buf[i:i + len(row)] = row


def fill_all(color):
    r, g, b = color
    row = bytes((r, g, b)) * DW
    for dy in range(DH):
        i = dy * DW * 3
        buf[i:i + len(row)] = row


# Brush: a filled circle of device-pixel radius r, precomputed as offsets.
_brush_cache = {}


def _brush(r):
    pts = _brush_cache.get(r)
    if pts is None:
        pts = []
        ri = int(math.ceil(r))
        for dy in range(-ri, ri + 1):
            for dx in range(-ri, ri + 1):
                if dx * dx + dy * dy <= r * r + r * 0.4:
                    pts.append((dx, dy))
        _brush_cache[r] = pts
    return pts


def stamp(cx, cy, r, color, clip=None):
    """Filled circle at layout coords (cx, cy), radius r layout units."""
    dcx = cx * SS; dcy = cy * SS; dr = max(0.6, r * SS)
    pts = _brush(round(dr, 1))
    icx = int(round(dcx)); icy = int(round(dcy))
    if clip is not None:
        cx0, cy0, cx1, cy1 = (int(clip[0] * SS), int(clip[1] * SS),
                              int(clip[2] * SS), int(clip[3] * SS))
        for dx, dy in pts:
            px, py = icx + dx, icy + dy
            if cx0 <= px < cx1 and cy0 <= py < cy1:
                _set(px, py, color)
    else:
        for dx, dy in pts:
            _set(icx + dx, icy + dy, color)


def draw_line(x0, y0, x1, y1, width, color, clip=None):
    """Thick line with round caps, in layout coordinates."""
    r = width / 2.0
    dist = math.hypot(x1 - x0, y1 - y0)
    steps = max(1, int(dist / max(0.35, r * 0.55)))
    for i in range(steps + 1):
        t = i / steps
        stamp(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r, color, clip)


def draw_polyline(points, width, color, clip=None, close=False):
    pts = list(points)
    if close and pts:
        pts.append(pts[0])
    for i in range(len(pts) - 1):
        draw_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                  width, color, clip)


def fill_poly(points, color, clip=None):
    """Even-odd polygon fill (layout coords) via scanlines."""
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    y0 = int(math.floor(min(ys) * SS)); y1 = int(math.ceil(max(ys) * SS))
    n = len(points)
    for dy in range(y0, y1 + 1):
        ly = dy / SS
        nodes = []
        for i in range(n):
            ax, ay = points[i]; bx, by = points[(i + 1) % n]
            if (ay <= ly < by) or (by <= ly < ay):
                nodes.append(ax + (ly - ay) * (bx - ax) / (by - ay))
        nodes.sort()
        for k in range(0, len(nodes) - 1, 2):
            xa = int(round(nodes[k] * SS)); xb = int(round(nodes[k + 1] * SS))
            if clip is not None:
                xa = max(xa, int(clip[0] * SS)); xb = min(xb, int(clip[2] * SS))
            for dx in range(xa, xb + 1):
                if clip is not None and not (clip[1] * SS <= dy < clip[3] * SS):
                    continue
                _set(dx, dy, color)


def ring(cx, cy, r, width, color, clip=None):
    steps = max(24, int(r * 6))
    pts = [(cx + r * math.cos(2 * math.pi * i / steps),
            cy + r * math.sin(2 * math.pi * i / steps)) for i in range(steps)]
    draw_polyline(pts, width, color, clip, close=True)


# --------------------------------------------------------------------------
# Stroke font.  Grid: cap height = 9 units (y 0..9, baseline y=9),
# x-height top y=3, descenders to y=12.  Each glyph: (advance, [strokes]),
# a stroke is a list of (x, y) points.  Drawn with round joins.
# --------------------------------------------------------------------------

def _circ(cx, cy, r, n=10):
    return [(cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


FONT = {
    'A': (6.4, [[(0, 9), (3.2, 0), (6.4, 9)], [(1.3, 6), (5.1, 6)]]),
    'B': (6.2, [[(0, 0), (0, 9)],
                [(0, 0), (3.4, 0), (5, 1.3), (5, 3.1), (3.4, 4.4), (0, 4.4),
                 (4, 4.4), (5.6, 5.7), (5.6, 7.7), (4.2, 9), (0, 9)]]),
    'C': (6.2, [[(5.7, 2), (4.2, 0.5), (2.2, 0), (0.9, 1), (0.1, 2.6),
                 (0.1, 6.4), (0.9, 8), (2.2, 9), (4.2, 9), (5.7, 7)]]),
    'D': (6.2, [[(0, 0), (0, 9)],
                [(0, 0), (3.4, 0), (5.3, 1.6), (5.3, 7.4), (3.4, 9), (0, 9)]]),
    'E': (5.6, [[(5.6, 0), (0, 0), (0, 9), (5.6, 9)], [(0, 4.5), (4.4, 4.5)]]),
    'F': (5.6, [[(5.6, 0), (0, 0), (0, 9)], [(0, 4.5), (4.4, 4.5)]]),
    'G': (6.4, [[(5.8, 2), (4.4, 0.5), (2.2, 0), (0.9, 1), (0.1, 2.6),
                 (0.1, 6.4), (0.9, 8), (2.2, 9), (4.6, 9), (5.8, 7.4),
                 (5.8, 5.4), (3.6, 5.4)]]),
    'H': (6.6, [[(0, 0), (0, 9)], [(6.6, 0), (6.6, 9)], [(0, 4.5), (6.6, 4.5)]]),
    'I': (2.4, [[(1.2, 0), (1.2, 9)], [(0.1, 0), (2.3, 0)], [(0.1, 9), (2.3, 9)]]),
    'J': (5.2, [[(5.2, 0), (5.2, 6.4), (4.2, 8.4), (2.2, 9), (0.6, 8.1),
                 (0.1, 6.4)]]),
    'K': (6.4, [[(0, 0), (0, 9)], [(5.9, 0), (0.2, 4.8)], [(1.7, 3.4), (6.4, 9)]]),
    'L': (5.6, [[(0, 0), (0, 9), (5.6, 9)]]),
    'M': (7.6, [[(0, 9), (0, 0), (3.8, 5.2), (7.6, 0), (7.6, 9)]]),
    'N': (6.8, [[(0, 9), (0, 0), (6.8, 9), (6.8, 0)]]),
    'O': (6.6, [[(3.3, 0), (5.2, 0.8), (6.3, 2.6), (6.3, 6.4), (5.2, 8.2),
                 (3.3, 9), (1.4, 8.2), (0.3, 6.4), (0.3, 2.6), (1.4, 0.8),
                 (3.3, 0)]]),
    'P': (6.2, [[(0, 9), (0, 0), (3.4, 0), (5.3, 1.3), (5.3, 3.7),
                 (3.4, 5), (0, 5)]]),
    'Q': (6.6, [[(3.3, 0), (5.2, 0.8), (6.3, 2.6), (6.3, 6.4), (5.2, 8.2),
                 (3.3, 9), (1.4, 8.2), (0.3, 6.4), (0.3, 2.6), (1.4, 0.8),
                 (3.3, 0)], [(4.1, 6.6), (6.8, 9.6)]]),
    'R': (6.2, [[(0, 9), (0, 0), (3.4, 0), (5.3, 1.3), (5.3, 3.7),
                 (3.4, 5), (0, 5)], [(3.1, 5), (6.2, 9)]]),
    'S': (6.0, [[(5.5, 1.6), (4.1, 0.3), (2.1, 0), (0.8, 1), (0.1, 2.9),
                 (1, 4.3), (4.6, 5.3), (5.6, 6.4), (5.5, 7.9), (4.1, 9),
                 (1.6, 9), (0.1, 7.9)]]),
    'T': (6.4, [[(0, 0), (6.4, 0)], [(3.2, 0), (3.2, 9)]]),
    'U': (6.6, [[(0, 0), (0, 6.4), (0.9, 8.2), (2.4, 9), (4.2, 9), (5.7, 8.2),
                 (6.6, 6.4), (6.6, 0)]]),
    'V': (6.4, [[(0, 0), (3.2, 9), (6.4, 0)]]),
    'W': (8.6, [[(0, 0), (1.9, 9), (4.3, 3.4), (6.7, 9), (8.6, 0)]]),
    'X': (6.2, [[(0, 0), (6.2, 9)], [(6.2, 0), (0, 9)]]),
    'Y': (6.4, [[(0, 0), (3.2, 4.6), (6.4, 0)], [(3.2, 4.6), (3.2, 9)]]),
    'Z': (6.2, [[(0, 0), (6.2, 0), (0, 9), (6.2, 9)]]),

    'a': (5.6, [[(5.1, 3), (5.1, 9)],
                [(5.1, 4.9), (4.1, 3.5), (2.1, 3.1), (0.8, 3.9), (0.2, 6),
                 (0.8, 8.2), (2.1, 9), (4.1, 8.6), (5.1, 7.2)]]),
    'b': (5.7, [[(0, 0), (0, 9)],
                [(0, 5.1), (1.1, 3.9), (2.6, 3.1), (4.4, 3.9), (5.3, 6),
                 (4.4, 8.2), (2.6, 9), (1.1, 8.2), (0, 7.1)]]),
    'c': (5.2, [[(5, 4.3), (3.9, 3.3), (2.1, 3), (0.9, 4), (0.3, 6),
                 (0.9, 8.1), (2.1, 9), (3.9, 8.8), (5, 7.9)]]),
    'd': (5.7, [[(5.1, 0), (5.1, 9)],
                [(5.1, 5.1), (4.1, 3.9), (2.6, 3.1), (1.1, 3.9), (0.2, 6),
                 (1.1, 8.2), (2.6, 9), (4.1, 8.2), (5.1, 7.1)]]),
    'e': (5.2, [[(0.3, 6.1), (5.1, 6.1), (4.9, 4.6), (3.9, 3.3), (2.1, 3),
                 (0.9, 4.1), (0.3, 6.1), (0.9, 8.1), (2.1, 9), (3.9, 8.8),
                 (5, 7.9)]]),
    'f': (3.6, [[(3.4, 1.2), (2.7, 0.2), (1.5, 0), (0.8, 0.9), (0.8, 9)],
                [(0, 4.4), (2.9, 4.4)]]),
    'g': (5.7, [[(5.1, 3), (5.1, 10.4), (4.4, 11.8), (2.6, 12.3),
                 (0.9, 11.6), (0.3, 10.4)],
                [(5.1, 5.1), (4.1, 3.9), (2.6, 3.1), (1.1, 3.9), (0.2, 6),
                 (1.1, 8.2), (2.6, 9), (4.1, 8.2), (5.1, 7.1)]]),
    'h': (5.7, [[(0, 0), (0, 9)],
                [(0, 5.6), (1.1, 4.1), (2.9, 3.1), (4.4, 3.9), (5.1, 5.6),
                 (5.1, 9)]]),
    'i': (2.2, [[(1.1, 3), (1.1, 9)], [(1.1, 0.7), (1.1, 1.15)]]),
    'j': (2.6, [[(1.9, 3), (1.9, 10.4), (1.3, 11.8), (0.2, 12.1)],
                [(1.9, 0.7), (1.9, 1.15)]]),
    'k': (5.2, [[(0, 0), (0, 9)], [(4.9, 3), (0.6, 6.6)], [(1.9, 5.3),
                 (5.2, 9)]]),
    'l': (2.2, [[(1.1, 0), (1.1, 9)]]),
    'm': (8.8, [[(0, 3), (0, 9)],
                [(0, 5.4), (1.1, 4), (2.7, 3.1), (3.9, 4), (4.3, 5.4),
                 (4.3, 9)],
                [(4.3, 5.4), (5.4, 4), (7, 3.1), (8.2, 4), (8.6, 5.4),
                 (8.6, 9)]]),
    'n': (5.7, [[(0, 3), (0, 9)],
                [(0, 5.6), (1.1, 4.1), (2.9, 3.1), (4.4, 3.9), (5.1, 5.6),
                 (5.1, 9)]]),
    'o': (5.7, [[(2.8, 3), (4.4, 3.6), (5.3, 5.1), (5.3, 6.9), (4.4, 8.4),
                 (2.8, 9), (1.3, 8.4), (0.4, 6.9), (0.4, 5.1), (1.3, 3.6),
                 (2.8, 3)]]),
    'p': (5.7, [[(0, 3), (0, 12.1)],
                [(0, 5.1), (1.1, 3.9), (2.6, 3.1), (4.4, 3.9), (5.3, 6),
                 (4.4, 8.2), (2.6, 9), (1.1, 8.2), (0, 7.1)]]),
    'q': (5.7, [[(5.1, 3), (5.1, 12.1)],
                [(5.1, 5.1), (4.1, 3.9), (2.6, 3.1), (1.1, 3.9), (0.2, 6),
                 (1.1, 8.2), (2.6, 9), (4.1, 8.2), (5.1, 7.1)]]),
    'r': (4.2, [[(0, 3), (0, 9)], [(0, 5.6), (1.3, 4), (3.1, 3.2),
                 (4.2, 3.7)]]),
    's': (5.0, [[(4.7, 4.3), (3.7, 3.3), (1.9, 3), (0.7, 3.9), (0.7, 5.3),
                 (1.5, 6.3), (3.7, 7), (4.7, 7.9), (4.4, 8.8), (3.1, 9),
                 (1.3, 9), (0.2, 8.2)]]),
    't': (3.7, [[(1.9, 1.6), (1.9, 7.7), (2.5, 8.7), (3.5, 8.8)],
                [(0.2, 4.1), (3.5, 4.1)]]),
    'u': (5.7, [[(0, 3), (0, 7.1), (0.8, 8.4), (2.3, 9), (4.1, 8.5),
                 (5.1, 7.1), (5.1, 3)], [(5.1, 9), (5.1, 8.4)]]),
    'v': (5.6, [[(0, 3), (2.8, 9), (5.6, 3)]]),
    'w': (8.2, [[(0, 3), (1.7, 9), (4.1, 4.7), (6.5, 9), (8.2, 3)]]),
    'x': (5.2, [[(0, 3), (5.2, 9)], [(5.2, 3), (0, 9)]]),
    'y': (5.7, [[(0, 3), (2.7, 8.3)],
                [(5.7, 3), (2.7, 8.3), (2.3, 10.9), (1.2, 12.1),
                 (0.1, 11.5)]]),
    'z': (5.0, [[(0, 3), (5, 3), (0, 9), (5, 9)]]),

    '0': (5.8, [[(2.9, 0), (4.5, 0.7), (5.4, 2.6), (5.4, 6.4), (4.5, 8.3),
                 (2.9, 9), (1.3, 8.3), (0.4, 6.4), (0.4, 2.6), (1.3, 0.7),
                 (2.9, 0)]]),
    '1': (4.6, [[(1.6, 1.6), (3.1, 0), (3.1, 9)], [(1.4, 9), (4.6, 9)]]),
    '2': (5.8, [[(0.6, 1.9), (1.6, 0.5), (3.6, 0), (5.1, 1.5), (5.1, 3.6),
                 (0.4, 9), (5.4, 9)]]),
    '3': (5.8, [[(0.6, 1.6), (1.9, 0.2), (3.9, 0.2), (5.1, 1.8), (4.7, 3.8),
                 (3.1, 4.6)],
                [(3.1, 4.6), (4.9, 5.2), (5.4, 7), (4.6, 8.6), (2.6, 9),
                 (0.9, 8.6), (0.2, 7.2)]]),
    '4': (6.0, [[(4.2, 9), (4.2, 0), (0, 6.6), (6, 6.6)]]),
    '5': (5.8, [[(5.2, 0), (0.9, 0), (0.6, 4.3), (2.3, 3.7), (4.1, 3.9),
                 (5.3, 5.7), (5.1, 7.6), (3.9, 8.9), (1.9, 9), (0.4, 8)]]),
    '6': (5.8, [[(5, 1.6), (3.6, 0.3), (1.9, 0.8), (0.6, 3), (0.4, 6.5),
                 (1.1, 8.3), (2.6, 9), (4.3, 8.4), (5.3, 6.8), (5.1, 5.1),
                 (3.9, 4.1), (2.1, 4.3), (0.6, 5.6)]]),
    '7': (5.8, [[(0, 0), (5.8, 0), (2.6, 9)]]),
    '8': (5.8, [[(2.9, 4.5), (1.3, 3.9), (0.6, 2.3), (1.1, 0.8), (2.9, 0.1),
                 (4.7, 0.8), (5.2, 2.3), (3.9, 3.9), (2.9, 4.5), (1.1, 5.3),
                 (0.4, 6.9), (1.1, 8.6), (2.9, 9), (4.7, 8.6), (5.4, 6.9),
                 (3.9, 5.3), (2.9, 4.5)]]),
    '9': (5.8, [[(0.6, 7.4), (1.9, 8.7), (3.6, 8.3), (4.9, 6), (5.3, 2.6),
                 (4.6, 0.8), (3.1, 0.1), (1.4, 0.7), (0.4, 2.3), (0.6, 4.1),
                 (1.8, 5.1), (3.6, 4.9), (5.1, 3.6)]]),

    '.': (1.6, [[(0.8, 8.5), (0.8, 8.95)]]),
    ',': (1.8, [[(1.1, 8.1), (0.7, 9.9)]]),
    ';': (1.8, [[(0.9, 3.6), (0.9, 4.05)], [(1.1, 8.1), (0.7, 9.9)]]),
    ':': (1.8, [[(0.9, 3.3), (0.9, 3.75)], [(0.9, 8.4), (0.9, 8.85)]]),
    "'": (1.5, [[(1, 0), (0.7, 2.1)]]),
    '-': (3.6, [[(0.3, 5.4), (3.3, 5.4)]]),
    '\u2014': (5.4, [[(0.2, 5.4), (5.2, 5.4)]]),
    '!': (1.8, [[(0.9, 0), (0.9, 6.2)], [(0.9, 8.4), (0.9, 8.85)]]),
    '?': (5.4, [[(0.6, 1.9), (1.6, 0.5), (3.5, 0.2), (4.7, 1.4), (4.5, 3.2),
                 (2.9, 4.7), (2.7, 6.2)], [(2.7, 8.4), (2.7, 8.85)]]),
    '$': (6.0, [[(2.9, -1.1), (2.9, 10.1)],
                [(5.5, 1.6), (4.1, 0.3), (2.1, 0), (0.8, 1), (0.1, 2.9),
                 (1, 4.3), (4.6, 5.3), (5.6, 6.4), (5.5, 7.9), (4.1, 9),
                 (1.6, 9), (0.1, 7.9)]]),
    '%': (8.6, [_circ(1.7, 1.9, 1.35), _circ(6.9, 7.1, 1.35),
                [(7.9, 0.4), (0.7, 8.6)]]),
    '&': (6.4, [[(5.6, 7.6), (3, 9.2), (0.9, 8.6), (0.2, 6.8), (0.9, 5.2),
                 (3.4, 2.2), (4.6, 0.9), (4, 0.1), (2.6, 0.5), (0.9, 2.6),
                 (0.6, 4.6), (1.6, 6.2), (4.2, 8.7), (5.6, 9.2)]]),
    '/': (5.6, [[(0.4, 9.4), (5.2, -0.4)]]),
    '(': (4.4, [[(4.2, 0), (2.1, 1.6), (1.2, 4.5), (2.1, 7.4), (4.2, 9)]]),
    ')': (4.4, [[(0.2, 0), (2.3, 1.6), (3.2, 4.5), (2.3, 7.4), (0.2, 9)]]),
    '"': (3.6, [[(0.9, 0), (0.6, 2.1)], [(2.7, 0), (2.4, 2.1)]]),
    '+': (5.2, [[(2.6, 2), (2.6, 7)], [(0.3, 4.5), (4.9, 4.5)]]),
    '=': (5.2, [[(0.3, 3.4), (4.9, 3.4)], [(0.3, 6.1), (4.9, 6.1)]]),
    '*': (5.2, [[(2.6, 0.8), (2.6, 5.2)], [(0.9, 1.8), (4.3, 4.2)],
                [(4.3, 1.8), (0.9, 4.2)]]),
    '\u00b7': (2.2, [[(1.1, 5.1), (1.1, 5.55)]]),
    ' ': (3.2, []),
}

SPACE_W = 3.2


def glyph(ch):
    return FONT.get(ch, FONT[' '])


def text_width(text, scale, spacing=0.85):
    w = 0.0
    for ch in text:
        w += glyph(ch)[0] + spacing
    if text:
        w -= spacing
    return w * scale


def draw_text(x, y, text, scale, weight, color, spacing=0.85, align='left',
              clip=None):
    """Draw text with baseline at y (layout coords).  Returns its width."""
    w = text_width(text, scale, spacing)
    if align == 'center':
        x -= w / 2.0
    elif align == 'right':
        x -= w
    cx = x
    for ch in text:
        adv, strokes = glyph(ch)
        for stroke in strokes:
            pts = [(cx + px * scale, y + (py - 9.0) * scale)
                   for (px, py) in stroke]
            if len(pts) == 1:
                stamp(pts[0][0], pts[0][1], weight * scale / 2.0, color, clip)
            else:
                draw_polyline(pts, weight * scale, color, clip)
        cx += (adv + spacing) * scale
    return w


def wrap(text, scale, spacing, max_w):
    words = text.split()
    lines = []
    cur = ''
    for word in words:
        trial = word if not cur else cur + ' ' + word
        if text_width(trial, scale, spacing) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(x, y, text, scale, weight, color, spacing, max_w,
                 line_h=None, clip=None):
    """Draw wrapped text starting with baseline y; returns end baseline."""
    if line_h is None:
        line_h = 12.6 * scale
    lines = wrap(text, scale, spacing, max_w)
    for i, line in enumerate(lines):
        draw_text(x, y + i * line_h, line, scale, weight, color, spacing,
                  clip=clip)
    return y + len(lines) * line_h, len(lines)


# --------------------------------------------------------------------------
# PNG output (deterministic: fixed zlib level, filter 0 rows)
# --------------------------------------------------------------------------

def downsample():
    out = bytearray(W * H * 3)
    for oy in range(H):
        for ox in range(W):
            r = g = b = 0
            base = ((2 * oy) * DW + 2 * ox) * 3
            for dy in (0, 1):
                i = base + dy * DW * 3
                r += buf[i] + buf[i + 3]
                g += buf[i + 1] + buf[i + 4]
                b += buf[i + 2] + buf[i + 5]
            o = (oy * W + ox) * 3
            out[o] = (r + 2) // 4
            out[o + 1] = (g + 2) // 4
            out[o + 2] = (b + 2) // 4
    return out


def png_bytes(rgb):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        c += struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
        return c

    ihdr = struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) +
            chunk(b'IDAT', zlib.compress(bytes(raw), 9)) +
            chunk(b'IEND', b''))


# --------------------------------------------------------------------------
# Page furniture
# --------------------------------------------------------------------------

MX = 40.0                    # page margin
CW = W - 2 * MX              # content width (944)


def rule(y, thick=1.2, color=INK, x0=MX, x1=W - MX):
    fill_rect(x0, y, x1 - x0, thick, color)


def illustration(x, y, w, h):
    """Lead art: night sky over a Polish town, missile trails, a burst."""
    clip = (x, y, x + w, y + h)
    # sky bands
    bands = [(26, 34, 62), (33, 43, 76), (42, 53, 90), (52, 63, 102),
             (63, 73, 110)]
    bh = h * 0.78 / len(bands)
    for i, c in enumerate(bands):
        fill_rect(x, y + i * bh, w, bh + 1, c)
    # stars
    star_pts = [(0.06, 0.10), (0.16, 0.30), (0.28, 0.08), (0.42, 0.22),
                (0.55, 0.06), (0.68, 0.16), (0.80, 0.05), (0.90, 0.28),
                (0.36, 0.38), (0.12, 0.52), (0.60, 0.34), (0.95, 0.48)]
    for fx, fy in star_pts:
        stamp(x + fx * w, y + fy * h * 0.7, 1.1, (210, 216, 235), clip)
    # radar rings from lower-left
    rcx, rcy = x + w * 0.16, y + h * 0.80
    for rr in (18, 34, 50):
        ring(rcx, rcy, rr, 1.1, (110, 150, 190), clip)
    draw_line(rcx, rcy, rcx + 44, rcy - 30, 1.1, (110, 150, 190), clip)
    # missile trails: two parabolas ending at the burst point
    bx, by = x + w * 0.76, y + h * 0.52
    for sx, sy, bend in ((x + w * 0.30, y + h * 0.06, 26),
                         (x + w * 0.52, y + h * 0.02, 18)):
        pts = []
        for i in range(25):
            t = i / 24.0
            px = sx + (bx - sx) * t
            py = sy + (by - sy) * t - bend * 4 * t * (1 - t)
            pts.append((px, py))
        draw_polyline(pts, 3.4, (196, 120, 60), clip)
        draw_polyline(pts, 1.5, (250, 214, 150), clip)
        stamp(sx, sy, 2.2, (250, 230, 180), clip)
    # burst
    for ang in range(0, 360, 30):
        a = math.radians(ang)
        draw_line(bx, by, bx + 20 * math.cos(a), by + 20 * math.sin(a),
                  2.0, (240, 150, 60), clip)
    stamp(bx, by, 7.5, (224, 110, 40), clip)
    stamp(bx, by, 4.2, (250, 200, 110), clip)
    # ground + rooftops
    gy = y + h * 0.80
    fill_rect(x, gy, w, h * 0.20, (13, 16, 22))
    houses = [(0.03, 0.10, 0.045), (0.16, 0.07, 0.06), (0.55, 0.09, 0.05),
              (0.68, 0.06, 0.07), (0.86, 0.11, 0.05)]
    for fx, fw, fh in houses:
        hx = x + fx * w; hw = fw * w; hh = fh * h
        fill_rect(hx, gy - hh, hw, hh, (13, 16, 22))
        fill_poly([(hx - 2, gy - hh), (hx + hw / 2, gy - hh - 7),
                   (hx + hw + 2, gy - hh)], (13, 16, 22), clip)
        stamp(hx + hw * 0.5, gy - hh * 0.45, 1.3, (250, 205, 110), clip)
    # Polish colours, top-left corner
    fx0, fy0 = x + 10, y + 10
    fill_rect(fx0, fy0, 34, 11, (240, 240, 238))
    fill_rect(fx0, fy0 + 11, 34, 11, (196, 30, 42))
    draw_polyline([(fx0, fy0), (fx0 + 34, fy0), (fx0 + 34, fy0 + 22),
                   (fx0, fy0 + 22)], 1.1, (10, 10, 10), clip, close=True)
    # frame
    draw_polyline([(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
                  2.2, INK, close=True)
    draw_polyline([(x + 5, y + 5), (x + w - 5, y + 5), (x + w - 5, y + h - 5),
                   (x + 5, y + h - 5)], 0.8, INK, close=True)


def panel(x, y, w, label, headline, deck, h_scale=1.95, d_scale=1.75):
    draw_text(x, y + 13, label, 1.5, 1.05, RED, spacing=1.1)
    hy = y + 13 + 12.6 * h_scale + 2
    end_y, _ = draw_wrapped(x, hy, headline, h_scale, 0.98, INK, 0.8, w)
    dy = end_y + 1
    draw_wrapped(x, dy, deck, d_scale, 0.6, SOFT, 0.85, w)


def build_page():
    fill_all(PAPER)

    # --- kicker line ------------------------------------------------------
    rule(26, 1.1)
    draw_text(MX, 48, 'Vol. CXLVIII \u00b7 No. 324', 1.55, 0.7, SOFT)
    draw_text(W - MX, 48, 'LATE FINAL EDITION', 1.55, 0.85, SOFT,
              align='right')
    rule(56, 2.6)

    # --- masthead ---------------------------------------------------------
    draw_text(W / 2, 138, 'THE DAILY SIGNAL', 8.1, 1.12, INK, spacing=1.15,
              align='center')
    rule(152, 1.1)
    rule(157, 3.2)

    # --- info line --------------------------------------------------------
    draw_text(MX, 184, 'SATURDAY, 21 NOVEMBER 2026', 1.6, 0.95, INK)
    draw_text(W - MX, 184, 'WORLD EDITION', 1.6, 0.95, INK, align='right')
    rule(194, 1.1)

    # --- lead story -------------------------------------------------------
    draw_text(MX, 225, 'WARSAW \u2014 NATO AIRSPACE BREACHED', 1.85, 1.05,
              RED, spacing=1.0)
    draw_text(MX, 284, 'RUSSIAN MISSILES', 5.6, 1.2, INK, spacing=0.7)
    draw_text(MX, 348, 'FALL ON POLAND', 5.6, 1.2, INK, spacing=0.7)
    deck = ('Two Russian missiles and a suspected drone came down on Polish '
            'soil during Western military drills. Warsaw calls it a '
            'deliberate provocation; NATO calls it a grave violation of '
            'its airspace.')
    draw_wrapped(MX, 384, deck, 2.3, 0.62, SOFT, 0.85, 545)
    illustration(624, 208, 360, 196)
    draw_wrapped(624, 428, 'Two missiles and a suspected drone fell on '
                 'Polish soil as allied forces exercised nearby.', 1.7, 0.6,
                 MUTED, 0.85, 360)

    # --- markets strip ----------------------------------------------------
    rule(516, 2.6)
    draw_text(MX, 544, 'MARKETS', 1.85, 1.05, RED, spacing=1.0)
    markets = ('S&P 500 AND DOW ENTER CORRECTION \u00b7 US STOCKS FALL '
               '3.7% \u00b7 ANTHROPIC SLIDES TOWARD ITS IPO PRICE \u00b7 '
               'AI SELL-OFF DEEPENS')
    draw_wrapped(168, 538, markets, 1.8, 0.85, INK, 0.8, CW - 128)
    rule(572, 1.1)

    # --- secondary panels ---------------------------------------------------
    rule(586, 1.1, HAIR)
    panel(MX, 594, 622,
          'THE HAGUE',
          "Rights groups press for action after the World Court's ruling "
          "that Myanmar committed genocide against the Rohingya",
          'The court ruled Myanmar committed genocide against the Rohingya.',
          h_scale=2.0, d_scale=1.85)
    panel(682, 594, 302,
          'KYIV',
          "Russia targets Kyiv's bridges and crossings",
          "Days after Ukraine's latest hit on the Crimean Bridge.")
    rule(776, 1.1, HAIR)
    panel(MX, 784, 302,
          'SHENZHEN',
          'Trump, Xi and Putin leave the first trilateral summit with '
          'few concrete results',
          'Three days of talks end without a signed declaration.')
    panel(361, 784, 302,
          'BRUSSELS',
          'Britain and the EU sign deals on food trade, carbon markets '
          'and youth mobility',
          'PM Andy Burnham signs three agreements at the Brussels summit.')
    panel(682, 784, 302,
          'HORMUZ',
          'The Iran war nears its ninth month',
          'Trump says he is not rushing decisions and may not decide '
          'until 2027; Saudi-led coalition intercepts Houthi missiles '
          'over Riyadh and strikes Hodeidah.', d_scale=1.65)

    # --- wire ticker --------------------------------------------------------
    rule(970, 2.2)
    ticker = ('THE WIRE \u00b7 GTA VI launch sales put at $2.36bn \u00b7 '
              'Pill hailed as pancreatic-cancer breakthrough \u00b7 Cyclone '
              'Akvan hits Odisha; 300,000 evacuated \u00b7 Trump threatens '
              'penalties on AI data centres abroad \u00b7 COP31 in Antalya '
              'enters final stage')
    draw_wrapped(MX, 990, ticker, 1.45, 0.68, SOFT, 0.85, CW)


def main():
    build_page()
    data = png_bytes(downsample())
    with open('entry.png', 'wb') as f:
        f.write(data)
    out_dir = os.environ.get('MAKEFUN_OUTPUT_DIR')
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, 'entry.png'), 'wb') as f:
            f.write(data)
    elif os.path.isdir('/output'):
        try:
            with open('/output/entry.png', 'wb') as f:
                f.write(data)
        except OSError:
            pass
    print('entry.png written:', len(data), 'bytes')


if __name__ == '__main__':
    main()
