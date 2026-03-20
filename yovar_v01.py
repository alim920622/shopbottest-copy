import json
import hashlib
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.api.deps import get_db
from app.db.database import Database

router = APIRouter(prefix="/yovar", tags=["yovar"])

# ============================================================
# ВАРИАНТ 3 — КЭШ
# ============================================================
_cache = {}
CACHE_TTL_MINUTES = 30

def _cache_key(text: str) -> str:
    return hashlib.md5(text.strip().lower().encode()).hexdigest()

def _cache_get(text: str):
    key = _cache_key(text)
    entry = _cache.get(key)
    if entry and entry["expires"] > datetime.utcnow():
        return entry["result"]
    return None

def _cache_set(text: str, result: dict):
    key = _cache_key(text)
    _cache[key] = {
        "result": result,
        "expires": datetime.utcnow() + timedelta(minutes=CACHE_TTL_MINUTES)
    }

# ============================================================
# ВАРИАНТ 1 — ПРОМПТ 1: намерение
# ============================================================
PROMPT_INTENT = """Намерение одним словом:
search=товар/блюдо/продукт
suggest=совет/идея/что поесть
budget=цена/дёшево/сомони/арзон
cart=добавь/корзина/заказать
open=открыт/работает/кушода
near=рядом/близко/наздик/поблизости
greeting=привет/салом/salom
other=остальное
Если несколько намерений — выбери главное.
Только одно слово."""

# ============================================================
# ВАРИАНТ 2 — ПРОМПТЫ 2: по намерению
# ============================================================
PROMPT_BY_INTENT = {
    "search": """Извлеки товары, переведи на русский.
шир=молоко, нон=хлеб, палов=плов, гушт=мясо, чой=чай, себ=яблоко, пиёз=лук
Исправь опечатки. Добавь 1-2 аналога в similar.
JSON: {"items":[],"similar":[]}""",
    "suggest": """Предложи 3 блюда для заказа в Душанбе.
Учти предпочтения и время суток если указаны.
JSON: {"items":[],"meal_type":"завтрак/обед/ужин/перекус","cuisine":"таджикская/узбекская/любая"}""",
    "budget": """Извлеки бюджет и товары из запроса.
JSON: {"items":[],"filters":{"max_price":null,"min_price":null},"similar":[]}""",
    "cart": """Извлеки товары и количество. Переведи на русский. Исправь опечатки.
JSON: {"items":[],"quantity":null}""",
    "open": """Пользователь спрашивает про режим работы.
JSON: {"is_open_now":true,"near_me":false,"comment":""}""",
    "near": """Пользователь ищет что-то поблизости.
JSON: {"near_me":true,"items":[],"comment":""}""",
    "other": """Кратко опиши что хочет пользователь.
JSON: {"comment":""}"""
}

# ============================================================
# МОДЕЛИ
# ============================================================
class YovarPayload(BaseModel):
    query: str
    results_count: int = 0

# ============================================================
# ВЫЗОВ MISTRAL
# ============================================================
async def call_mistral(messages: list) -> str:
    import httpx
    import os
    api_key = os.getenv("MISTRAL_API_KEY", "")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "mistral-small-latest", "messages": messages, "max_tokens": 150, "temperature": 0.1}
        )
        data = resp.json()
        return data["choices"][0]["message"]["content"]

# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================
async def analyze_query(user_text: str, results_count: int) -> dict:
    # ШАГ 1 — Кэш (Вариант 3)
    cached = _cache_get(user_text)
    if cached:
        cached["from_cache"] = True
        return cached
    # ШАГ 2 — Запрос 1: намерение (Вариант 1)
    intent_raw = await call_mistral([
        {"role": "system", "content": PROMPT_INTENT},
        {"role": "user", "content": user_text}
    ])
    intent = intent_raw.strip().lower().split()[0]
    valid = ["search", "suggest", "budget", "cart", "open", "near", "greeting", "other"]
    if intent not in valid:
        intent = "search"
    # ШАГ 3 — Приветствие — второй запрос не нужен
    if intent == "greeting":
        result = {
            "intent": "greeting",
            "items": [],
            "similar": [],
            "filters": {"max_price": None, "min_price": None},
            "cuisine": None,
            "meal_type": None,
            "is_open_now": False,
            "near_me": False,
            "quantity": None,
            "comment": "",
            "action": "greeting",
            "from_cache": False
        }
        _cache_set(user_text, result)
        return result
    # ШАГ 4 — Запрос 2: нужные поля (Вариант 2)
    prompt_2 = PROMPT_BY_INTENT.get(intent, PROMPT_BY_INTENT["other"])
    raw = await call_mistral([
        {"role": "system", "content": prompt_2},
        {"role": "user", "content": user_text}
    ])
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(raw)
    except Exception:
        data = {}
    # ШАГ 5 — Финальный ответ
    items = data.get("items", [])
    # Обратная совместимость со старым форматом
    if not items and data.get("q"):
        items = [data.get("q")]
    result = {
        "intent": intent,
        "corrected": items[0] if items else None,
        "items": items,
        "similar": data.get("similar", []),
        "filters": data.get("filters", {"max_price": None, "min_price": None}),
        "cuisine": data.get("cuisine", None),
        "meal_type": data.get("meal_type", None),
        "is_open_now": data.get("is_open_now", False),
        "near_me": data.get("near_me", False),
        "quantity": data.get("quantity", None),
        "comment": data.get("comment", ""),
        "action": "search" if items else "not_found",
        "from_cache": False
    }
    # ШАГ 6 — Сохраняем в кэш (Вариант 3)
    _cache_set(user_text, result)
    return result

# ============================================================
# РОУТ
# ============================================================
@router.post("/analyze")
async def yovar_analyze(payload: YovarPayload, db: Database = Depends(get_db)):
    result = await analyze_query(payload.query, payload.results_count)
    return result
