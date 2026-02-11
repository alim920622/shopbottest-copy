from __future__ import annotations

from app.i18n.client import ru, tj, uz


_TEXTS_BY_LOCALE: dict[str, dict[str, str]] = {
    "ru": ru.TEXTS,
    "tj": tj.TEXTS,
    "uz": uz.TEXTS,
}


def _normalize_locale(locale: str | None) -> str:
    """Нормализует locale к ru/tj/uz."""
    if not locale:
        return "ru"

    locale = locale.lower().replace("_", "-")
    base = locale.split("-")[0]

    if base in ("ru",):
        return "ru"
    if base in ("tj", "tg"):
        return "tj"
    if base in ("uz",):
        return "uz"

    return "ru"


def t(locale: str | None, key: str, **kwargs: object) -> str:
    """Возвращает перевод по ключу с fallback на RU."""
    norm = _normalize_locale(locale)
    texts = _TEXTS_BY_LOCALE.get(norm, ru.TEXTS)

    value = texts.get(key) or ru.TEXTS.get(key) or key

    if kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, ValueError):
            return value

    return value
