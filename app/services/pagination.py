from dataclasses import dataclass
from aiogram.types import InlineKeyboardButton

@dataclass(frozen=True)
class PageInfo:
    page: int
    total_pages: int
    limit: int
    offset: int

def calc_page(total: int, page: int, page_size: int) -> PageInfo:
    if page_size <= 0:
        page_size = 8
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    return PageInfo(page=page, total_pages=total_pages, limit=page_size, offset=page * page_size)

from aiogram.types import InlineKeyboardButton

LEFT = "\u2b05\ufe0f"   # ??
RIGHT = "\u27a1\ufe0f"  # ??

def pager_row(prefix: str, page: int, total_pages: int) -> list[InlineKeyboardButton]:
    # Только стрелки, без "1/2"
    if total_pages <= 1:
        return []

    row: list[InlineKeyboardButton] = []

    if page > 0:
        row.append(InlineKeyboardButton(text=LEFT, callback_data=f"{prefix}:p:{page-1}"))

    if page + 1 < total_pages:
        row.append(InlineKeyboardButton(text=RIGHT, callback_data=f"{prefix}:p:{page+1}"))

    return row
