"""
atlas_layout.py - Pure-stdlib layout helpers for Context Atlas.

The ownership map uses a squarified treemap so domains and documents preserve
relative size without needing a client-side charting dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from math import inf
from typing import Iterable


@dataclass
class Rect:
    id: str
    x: float
    y: float
    w: float
    h: float
    value: float

    def as_dict(self) -> dict:
        return asdict(self)


def squarify(items: Iterable[dict], width: float = 100.0, height: float = 100.0) -> list[dict]:
    """Return treemap rectangles for items with `{id, value}`.

    Coordinates are percentages in a `width` x `height` canvas. Zero or
    negative values receive a tiny floor so every item remains discoverable.
    """
    prepared = []
    for idx, item in enumerate(items):
        ident = str(item.get("id") or item.get("name") or idx)
        try:
            value = float(item.get("value") or 0)
        except (TypeError, ValueError):
            value = 0.0
        prepared.append({"id": ident, "value": max(value, 1.0), "index": idx})
    if not prepared:
        return []

    total = sum(i["value"] for i in prepared) or 1.0
    scale = (width * height) / total
    sizes = [
        {"id": i["id"], "area": i["value"] * scale, "value": i["value"], "index": i["index"]}
        for i in sorted(prepared, key=lambda x: (-x["value"], x["id"]))
    ]

    rects: list[Rect] = []
    _squarify(sizes, [], 0.0, 0.0, width, height, rects)
    by_input = sorted(rects, key=lambda r: next((i["index"] for i in sizes if i["id"] == r.id), 0))
    return [r.as_dict() for r in by_input]


def _squarify(items: list[dict], row: list[dict], x: float, y: float,
              w: float, h: float, rects: list[Rect]) -> None:
    if not items:
        if row:
            _layout_row(row, x, y, w, h, rects)
        return

    item = items[0]
    side = min(w, h)
    if not row or _worst(row + [item], side) <= _worst(row, side):
        _squarify(items[1:], row + [item], x, y, w, h, rects)
        return

    used = _layout_row(row, x, y, w, h, rects)
    if w >= h:
        _squarify(items, [], x, y + used, w, max(0.0, h - used), rects)
    else:
        _squarify(items, [], x + used, y, max(0.0, w - used), h, rects)


def _worst(row: list[dict], side: float) -> float:
    if not row or side <= 0:
        return inf
    areas = [max(0.0001, r["area"]) for r in row]
    total = sum(areas)
    largest = max(areas)
    smallest = min(areas)
    side2 = side * side
    return max((side2 * largest) / (total * total), (total * total) / (side2 * smallest))


def _layout_row(row: list[dict], x: float, y: float, w: float, h: float,
                rects: list[Rect]) -> float:
    total = sum(r["area"] for r in row)
    if total <= 0 or w <= 0 or h <= 0:
        return 0.0

    if w >= h:
        row_h = min(h, total / w)
        cur_x = x
        for item in row:
            item_w = min(w - (cur_x - x), item["area"] / row_h if row_h else 0.0)
            rects.append(Rect(item["id"], cur_x, y, item_w, row_h, item["value"]))
            cur_x += item_w
        return row_h

    col_w = min(w, total / h)
    cur_y = y
    for item in row:
        item_h = min(h - (cur_y - y), item["area"] / col_w if col_w else 0.0)
        rects.append(Rect(item["id"], x, cur_y, col_w, item_h, item["value"]))
        cur_y += item_h
    return col_w
