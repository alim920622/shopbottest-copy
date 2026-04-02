import json
import re
import hashlib
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.api.deps import get_db
from app.db.database import Database

router = APIRouter(prefix="/yovar", tags=["yovar"])

def _extract_string(val) -> str:
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, dict):
        return str(val.get("name") or val.get("q") or val.get("item") or "").strip()
    return str(val).strip()

def _normalize_list(lst) -> list:
    if not isinstance(lst, list):
        return []
    result = []
    for item in lst:
        s = _extract_string(item)
        if s:
            result.append(s)
    return result

def _parse_json(raw: str) -> dict:
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except Exception:
        pass
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return {}

# ============================================================
# ПРОМПТ 1: намерение
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
# ПРОМПТЫ 2: по намерению
# ============================================================
PROMPT_BY_INTENT = {
    "search": """Извлеки товары, переведи на русский. Словарь:
шир=молоко, нон=хлеб, палов/ош=плов, гушт=мясо, чой=чай
себ=яблоко, пиёз/пияз=лук, калампир=перец, бугдой=мука
енгок=лёгкие, мастава=мастава, кунжут=кунжут
финик/финник=финики, ангур=виноград, тарвуз=арбуз
картошка/картошкаи=картофель, помидор/бадамджон=помидор
кабоб=шашлык, самса=самса, лагман=лагман, шурпо=шурпа
Правила:
1. Переводи только если уверен — иначе оставь как есть
2. НЕ выдумывай перевод незнакомых слов
3. Если слово явно не еда — верни items:[] similar:[]
4. Добавь 1-2 аналога в similar
5. items и similar — только строки!
Только JSON без пояснений: {"items":["товар1"],"similar":["аналог1","аналог2"]}""",
    "suggest": """Предложи 3 блюда для заказа в Душанбе строками.
Только простые названия без скобок и уточнений!
Учти предпочтения и время суток если указаны.
items — только строки, не объекты!
Только JSON без пояснений: {"items":["блюдо1","блюдо2","блюдо3"],"meal_type":"завтрак/обед/ужин/перекус","cuisine":"таджикская/узбекская/любая"}""",
    "budget": """Извлеки бюджет и названия товаров строками.
items и similar — только строки, не объекты!
Только JSON без пояснений: {"items":["товар1"],"filters":{"max_price":null,"min_price":null},"similar":["аналог1"]}""",
    "cart": """Извлеки названия товаров строками и общее количество числом.
Переводи только если уверен — иначе оставь как есть.
НЕ выдумывай перевод незнакомых слов.
items — только строки, не объекты!
Только JSON без пояснений: {"items":["товар1","товар2"],"quantity":1}""",
    "open": """Пользователь спрашивает про режим работы.
Только JSON без пояснений: {"is_open_now":true,"near_me":false,"comment":""}""",
    "near": """Пользователь ищет что-то поблизости. Извлеки название товара если есть.
items — только строки, не объекты!
Только JSON без пояснений: {"near_me":true,"items":["товар1"],"comment":""}""",
    "other": """Кратко опиши что хочет пользователь.
Только JSON без пояснений: {"comment":""}"""
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
    # ЗАПРОС 1: намерение
    intent_raw = await call_mistral([
        {"role": "system", "content": PROMPT_INTENT},
        {"role": "user", "content": user_text}
    ])
    intent = intent_raw.strip().lower().split()[0]
    valid = ["search", "suggest", "budget", "cart", "open", "near", "greeting", "other"]
    if intent not in valid:
        intent = "search"
    # Приветствие — второй запрос не нужен
    if intent == "greeting":
        return {
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
    # ЗАПРОС 2: нужные поля по намерению
    prompt_2 = PROMPT_BY_INTENT.get(intent, PROMPT_BY_INTENT["other"])
    raw = await call_mistral([
        {"role": "system", "content": prompt_2},
        {"role": "user", "content": user_text}
    ])
    data = _parse_json(raw)
    items = _normalize_list(data.get("items", []))
    similar = _normalize_list(data.get("similar", []))
    if not items and data.get("q"):
        items = [_extract_string(data.get("q"))]
    return {
        "intent": intent,
        "corrected": items[0] if items else None,
        "items": items,
        "similar": similar,
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

# ============================================================
# РОУТЫ
# ============================================================
@router.post("/analyze")
async def yovar_analyze(payload: YovarPayload, db: Database = Depends(get_db)):
    return await analyze_query(payload.query, payload.results_count)

@router.post("/correct")
async def yovar_correct(payload: YovarPayload, db: Database = Depends(get_db)):
    return await analyze_query(payload.query, payload.results_count)
