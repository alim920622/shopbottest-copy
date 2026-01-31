from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from app.services.search_utils import normalize_text


@dataclass(frozen=True)
class ParsedProduct:
    name: str
    price: float
    description: str = ""


@dataclass(frozen=True)
class ImportPreview:
    items: list[ParsedProduct]
    errors: list[str]


def _parse_price(value: str) -> float | None:
    raw = (value or "").strip().replace(",", ".")
    if not raw:
        return None
    try:
        price = float(raw)
    except ValueError:
        return None
    if price < 0:
        return None
    return price


def parse_products_csv(data: bytes, encoding: str = "utf-8") -> ImportPreview:
    text = data.decode(encoding, errors="replace")
    stream = io.StringIO(text)
    sample = text[:1024]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        reader = csv.reader(stream, dialect)
    except csv.Error:
        reader = csv.reader(stream, delimiter=";")

    items: list[ParsedProduct] = []
    errors: list[str] = []
    seen: set[str] = set()

    for idx, row in enumerate(reader, start=1):
        if not row or all(not cell.strip() for cell in row):
            continue
        if len(row) < 2:
            errors.append(f"Строка {idx}: ожидается минимум 2 колонки (Название; Цена).")
            continue
        name = row[0].strip()
        price = _parse_price(row[1])
        description = row[2].strip() if len(row) > 2 else ""

        if not name:
            errors.append(f"Строка {idx}: пустое название.")
            continue
        if price is None:
            errors.append(f"Строка {idx}: цена должна быть числом.")
            continue

        norm = normalize_text(name)
        if norm in seen:
            errors.append(f"Строка {idx}: дубликат названия '{name}'.")
            continue
        seen.add(norm)

        items.append(ParsedProduct(name=name, price=price, description=description))

    return ImportPreview(items=items, errors=errors)
