# THE DAILY SIGNAL — news-image-20261121 entry

A broadsheet front page for Saturday, 21 November 2026, drawn entirely by
`main.py` (Python 3 standard library only — no PIL, no external fonts, no
image assets). Running `python3 main.py` writes `entry.png` in the current
directory and, when `MAKEFUN_OUTPUT_DIR` is set (the grader's stand-in for
`/output`), there as well.

## Concept and layout

A classic newspaper front page, top to bottom:

- **Kicker line** — "Vol. CXLVIII · No. 324" / "LATE FINAL EDITION" between
  hairline rules.
- **Masthead** — THE DAILY SIGNAL, large bold caps, over a double rule.
- **Info line** — "SATURDAY, 21 NOVEMBER 2026" / "WORLD EDITION".
- **Lead story** — red eyebrow "WARSAW — NATO AIRSPACE BREACHED", headline
  "RUSSIAN MISSILES FALL ON POLAND", a five-line deck (two Russian missiles
  and a suspected drone down on Polish soil during Western drills; Warsaw
  calls it a deliberate provocation; NATO a grave violation of its
  airspace), and a drawn illustration: night sky over a Polish town, two
  missile trails arcing to a burst, radar rings, rooftops, and the Polish
  colours in the corner, with a caption underneath.
- **Markets strip** — S&P 500 and Dow enter correction, US stocks fall
  3.7%, Anthropic slides toward its IPO price, AI sell-off deepens.
- **Five secondary panels** — THE HAGUE (rights groups press for action
  after the World Court's Myanmar genocide ruling), KYIV (Russia targets
  Kyiv's bridges and crossings), SHENZHEN (Trump, Xi and Putin leave the
  trilateral summit with few concrete results), BRUSSELS (Britain and the
  EU sign food, carbon and youth-mobility deals), HORMUZ (the Iran war
  nears its ninth month; Houthi missiles intercepted over Riyadh).
- **The Wire ticker** — GTA VI launch sales put at $2.36bn; a pill hailed
  as a pancreatic-cancer breakthrough; Cyclone Akvan hits Odisha, 300,000
  evacuated; Trump threatens penalties on AI data centres abroad; COP31 in
  Antalya enters its final stage.

## How the drawing works

- **Type**: a stroke (vector) font defined in code — every letter, digit
  and punctuation mark is a set of polylines on a 9-unit cap-height grid,
  drawn with round-joined thick strokes. Several sizes (masthead down to
  ticker) and weights (hairline decks to extra-bold headlines) come from
  scaling the same glyph definitions. A greedy word-wrap lays out decks.
- **Art**: the illustration is built from filled bands, stamped-circle
  stars, polyline missile trails, a starburst, scanline-filled roof
  polygons and ring outlines — all primitives implemented in the file.
- **Rendering**: the page is drawn on a 2048×2048 supersampled canvas and
  downsampled 2×2 once for smooth edges, then encoded as PNG with a
  hand-rolled encoder (zlib, filter-0 rows, fixed compression level).

## Determinism

The program reads no clock, no randomness and no environment input when
deciding what to draw, so repeated runs are byte-identical. Verified
locally with two consecutive runs:

- `entry.png`: 1024×1024, 80,298 bytes (limit 1 MiB)
- sha256 (both runs): `6e6c29a8b7aeb31694010fb2074543dc996942daaaa233621da0a24f2b21b1cd`
