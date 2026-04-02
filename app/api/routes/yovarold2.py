import json
import re
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.api.deps import get_db
from app.db.database import Database

router = APIRouter(prefix="/yovar", tags=["yovar"])

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

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

def _parse_json_array(raw: str) -> list:
    """Парсит JSON-массив из ответа модели."""
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "intents" in result:
            return result["intents"]
    except Exception:
        pass
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return []

# ============================================================
# ПРОМПТ 1: ОПРЕДЕЛЕНИЕ НАМЕРЕНИЯ (одно слово)
# УБРАЛИ: logistics, near — не нужны на этом этапе
# ============================================================

PROMPT_INTENT = """Определи намерение запроса одним словом из списка:

search   = ищет конкретный товар, блюдо, продукт
suggest  = просит совет что поесть, что заказать, по настроению
budget   = упоминает цену, сомони, бюджет, "до X", "за X", "дешевле"
cart     = добавить в корзину, заказать конкретное с количеством
promo    = акции, скидки, промокоды, спецпредложения
greeting = привет, салом, salom, здравствуй
other    = всё остальное

Правила:
- Если запрос содержит НЕСКОЛЬКО намерений — выбери ГЛАВНОЕ (то что занимает больше слов)
- Запросы про "ближайший", "рядом", "где находится" — это other
- Только одно слово из списка выше, без пояснений."""

# ============================================================
# ПРОМПТЫ 2: ПО КАЖДОМУ НАМЕРЕНИЮ
# ============================================================

PROMPT_BY_INTENT = {

    # ----------------------------------------------------------
    # SEARCH — поиск конкретного товара или блюда
    # ----------------------------------------------------------
    "search": """Ты помощник доставки Сабад (Душанбе, Таджикистан).
Пользователь ищет товар или блюдо. База данных хранит товары НА РУССКОМ ЯЗЫКЕ.

ГЛАВНОЕ ПРАВИЛО: items[] должен содержать слова НА РУССКОМ.
- Если запрос на русском — переписывай слова КАК ЕСТЬ, без изменений
- Если запрос на таджикском/узбекском — переводи на русский:
  шир→молоко, нон→хлеб, палов/ош→плов, гушт→мясо, чой→чай,
  себ→яблоко, пиёз→лук, калампир→перец, тарвуз→арбуз,
  кабоб→шашлык, сумбуса→самса, шурпо→шурпа, мастава→мастава
- Если не знаешь перевод — оставь слово как есть
- НИКОГДА не переводи русские слова на таджикский или узбекский
- НИКОГДА не возвращай пустой items[] если в запросе есть еда или товар

Примеры:
"капуста" → items:["капуста"]
"сливки" → items:["сливки"]
"картошка" → items:["картошка"]
"молоко хлеб" → items:["молоко","хлеб"]
"шир ва нон" → items:["молоко","хлеб"]
"плов шашлык" → items:["плов","шашлык"]

В similar — 2-3 похожих товара на русском языке.
items и similar — ТОЛЬКО строки, не объекты.

Только JSON без пояснений:
{"items":["товар1","товар2"],"similar":["аналог1","аналог2"]}""",

    # ----------------------------------------------------------
    # SUGGEST — советует что поесть, по настроению, по времени
    # ----------------------------------------------------------
    "suggest": """Ты помощник доставки Сабад (Душанбе).
Пользователь просит совет что заказать или хочет что-то по настроению.

Популярные блюда в Душанбе: плов, шашлык, манты, шурпа, самса,
шаурма, пицца, мастава, борщ, плов с курицей, лагман.

Предложи 3-4 конкретных блюда под запрос:
- "горячее" → плов, шурпа, лагман
- "быстро" → шаурма, самса
- "сытное" → плов, манты
- "лёгкое" → салат, суп

ВАЖНО: items[] — названия НА РУССКОМ, как они есть в каталоге.
НИКОГДА не возвращай пустой items[].
items и similar — ТОЛЬКО строки, не объекты.

Только JSON без пояснений:
{"items":["блюдо1","блюдо2","блюдо3"],"meal_type":"завтрак/обед/ужин/перекус","similar":["ещё вариант"]}""",

    # ----------------------------------------------------------
    # BUDGET — подбор по бюджету
    # Исправлено: теперь ВСЕГДА возвращает items даже без конкретики
    # ----------------------------------------------------------
    "budget": """Ты помощник доставки Сабад (Душанбе).
Пользователь ищет еду или товары в рамках бюджета.

ВАЖНЫЕ ПРАВИЛА:
1. Всегда извлекай максимальную сумму из текста (число перед "сомони", "руб", "сум")
2. Если пользователь не указал конкретный товар — предложи популярные блюда Душанбе:
   плов (30 сом), шашлык (28 сом), самса (8 сом), манты (25 сом), лагман (22 сом)
3. НИКОГДА не возвращай пустой items[] — всегда предлагай что-то
4. items — конкретные названия для поиска в каталоге

Только JSON без пояснений:
{"items":["товар1","товар2","товар3"],"filters":{"max_price":60,"min_price":null},"similar":["ещё вариант"]}""",

    # ----------------------------------------------------------
    # CART — добавление в корзину
    # ----------------------------------------------------------
    "cart": """Ты помощник доставки Сабад (Душанбе).
Пользователь хочет добавить товары в корзину.

Извлеки названия товаров и количество каждого.

ВАЖНО:
- Названия товаров должны быть НА РУССКОМ ЯЗЫКЕ
- Если запрос на русском — бери название как есть
- Если на таджикском/узбекском — переводи на русский:
  шир→молоко, нон→хлеб, палов/ош→плов, кабоб→шашлык,
  сумбуса→самса, чой→чай, гушт→мясо
- По умолчанию quantity = 1
- items — список объектов с name и quantity

Примеры:
"добавь 2 плова и 3 самсы" → items:[{"name":"плов","quantity":2},{"name":"самса","quantity":3}]
"картошку и молоко" → items:[{"name":"картошка","quantity":1},{"name":"молоко","quantity":1}]

Только JSON без пояснений:
{"items":[{"name":"товар1","quantity":2},{"name":"товар2","quantity":1}]}""",

    # ----------------------------------------------------------
    # PROMO — акции и скидки
    # Исправлено: ЗАПРЕТ искать товары, items всегда []
    # ----------------------------------------------------------
    "promo": """Ты помощник доставки Сабад (Душанбе).
Пользователь спрашивает про акции, скидки или промокоды.

ВАЖНО: НЕ ищи товары. items ВСЕГДА должен быть [].
Просто подтверди что проверишь актуальные акции.

Текущие акции Сабад:
- SABAD20: скидка 20% на первый заказ
- OSH15: скидка 15 сомони на блюда
- APTEKA0: бесплатная доставка из аптеки при заказе от 20 сом

Только JSON без пояснений:
{"items":[],"promo_codes":["SABAD20","OSH15","APTEKA0"],"message":"Актуальные акции: SABAD20 (−20%), OSH15 (−15 сомони), APTEKA0 (бесплатная доставка из аптеки)."}""",

    # ----------------------------------------------------------
    # GREETING — приветствие
    # ----------------------------------------------------------
    "greeting": """Пользователь поздоровался.
Только JSON без пояснений:
{"message":"Салом! Я Ёвар — помощник доставки Сабад. Спрашивайте о меню или что добавить в корзину 😊"}""",

    # ----------------------------------------------------------
    # OTHER — всё остальное
    # ----------------------------------------------------------
    "other": """Пользователь написал что-то непонятное или вне тематики доставки.
Вежливо уточни что именно нужно пользователю.
Только JSON без пояснений:
{"message":"Уточните пожалуйста — что именно вы хотите найти или заказать?"}"""
}

# ============================================================
# ПРОМПТ ДЛЯ МУЛЬТИ-ИНТЕНТ АНАЛИЗА
# Новый — для запросов с несколькими намерениями
# ============================================================

PROMPT_MULTI_INTENT = """Ты помощник доставки Сабад (Душанбе, Таджикистан).
Пользователь отправил сложный запрос с НЕСКОЛЬКИМИ намерениями одновременно.

Твоя задача — разбить запрос на отдельные намерения и для каждого извлечь данные.

Типы намерений:
- search: поиск товара/блюда → поле "items": ["название"]
- cart: добавить в корзину → поле "items": [{"name":"..","quantity":N}]
- promo: акции/скидки → поле "venue": "название заведения если есть"
- suggest: совет что поесть → поле "items": ["предложение1","предложение2"]
- budget: по бюджету → поле "items": ["товар"], "max_price": число

Словарь: ош/палов=плов, кабоб=шашлык, нон=хлеб, чой=чай, гушт=мясо,
самса/сумбуса=самса, манты=манты, шурпо=шурпа

Правила:
1. Каждое намерение — отдельный объект в массиве
2. Не дублируй — если плов упомянут в search и cart, раздели их
3. НИКОГДА не добавляй logistics/near/location намерения
4. Максимум 4 намерения в одном запросе
5. Верни ТОЛЬКО JSON массив без пояснений

Пример входа: "плов шашлык + добавь 3 капусты + есть ли акции в Шаурма Алижон"
Пример выхода:
[
  {"type":"search","items":["плов","шашлык"]},
  {"type":"cart","items":[{"name":"капуста","quantity":3}]},
  {"type":"promo","venue":"Шаурма Алижон"}
]

Запрос пользователя: {query}

Только JSON массив:"""

# ============================================================
# МОДЕЛИ
# ============================================================

class YovarPayload(BaseModel):
    query: str
    results_count: int = 0

class YovarMultiPayload(BaseModel):
    query: str

# ============================================================
# ВЫЗОВ MISTRAL
# ============================================================

async def call_mistral(messages: list, max_tokens: int = 200) -> str:
    import httpx
    import os
    api_key = os.getenv("MISTRAL_API_KEY", "")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY не задан в .env")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-small-latest",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.1
            }
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ АНАЛИЗА (одно намерение)
# ============================================================

async def analyze_query(user_text: str, results_count: int) -> dict:

    # ШАГ 1: определяем намерение
    intent_raw = await call_mistral([
        {"role": "system", "content": PROMPT_INTENT},
        {"role": "user", "content": user_text}
    ], max_tokens=10)

    intent = intent_raw.strip().lower().split()[0]
    valid = ["search", "suggest", "budget", "cart", "promo", "greeting", "other"]

    if intent not in valid:
        intent = "search"  # fallback

    # Приветствие — второй запрос не нужен
    if intent == "greeting":
        return {
            "intent": "greeting",
            "items": [],
            "similar": [],
            "filters": {"max_price": None, "min_price": None},
            "quantity": None,
            "corrected": None,
            "action": "greeting",
            "comment": "Салом! Я Ёвар — помощник доставки Сабад. Спрашивайте о меню или что добавить в корзину 😊",
            "from_cache": False
        }

    # ШАГ 2: извлекаем данные по намерению
    prompt_2 = PROMPT_BY_INTENT.get(intent, PROMPT_BY_INTENT["other"])
    raw = await call_mistral([
        {"role": "system", "content": prompt_2},
        {"role": "user", "content": user_text}
    ], max_tokens=300)

    data = _parse_json(raw)

    # Нормализуем items — может быть список строк ИЛИ список объектов (для cart)
    raw_items = data.get("items", [])
    if intent == "cart":
        # Для cart items — список объектов {"name":..,"quantity":..}
        cart_items = []
        if isinstance(raw_items, list):
            for it in raw_items:
                if isinstance(it, dict):
                    cart_items.append({
                        "name": str(it.get("name", "")).strip(),
                        "quantity": int(it.get("quantity", 1))
                    })
                elif isinstance(it, str) and it.strip():
                    cart_items.append({"name": it.strip(), "quantity": 1})
        items = [i["name"] for i in cart_items if i["name"]]
        cart_data = cart_items
    else:
        items = _normalize_list(raw_items)
        cart_data = []

    similar = _normalize_list(data.get("similar", []))

    # Для promo — items всегда пустой, берём promo_codes
    if intent == "promo":
        items = []
        similar = []

    # corrected = первый item если есть
    corrected = items[0] if items else None

    # action
    if intent in ["greeting", "promo", "other"]:
        action = intent
    elif items:
        action = "search"
    else:
        action = "not_found"

    return {
        "intent": intent,
        "corrected": corrected,
        "items": items,
        "cart_items": cart_data,        # только для cart
        "similar": similar,
        "filters": data.get("filters", {"max_price": None, "min_price": None}),
        "promo_codes": data.get("promo_codes", []),
        "meal_type": data.get("meal_type", None),
        "quantity": data.get("quantity", None),
        "comment": data.get("message", ""),
        "action": action,
        "from_cache": False
    }

# ============================================================
# ФУНКЦИЯ МУЛЬТИ-ИНТЕНТ АНАЛИЗА
# ============================================================

async def analyze_multi_intent(user_text: str) -> list:
    """
    Разбивает сложный запрос на несколько намерений.
    Возвращает список объектов типа:
    [
      {"type":"search", "items":["плов","шашлык"]},
      {"type":"cart",   "items":[{"name":"капуста","quantity":3}]},
      {"type":"promo",  "venue":"Шаурма Алижон"}
    ]
    """
    prompt = PROMPT_MULTI_INTENT.replace("{query}", user_text)

    raw = await call_mistral([
        {"role": "user", "content": prompt}
    ], max_tokens=400)

    intents = _parse_json_array(raw)

    # Валидация и очистка
    valid_types = ["search", "suggest", "budget", "cart", "promo"]
    result = []
    for item in intents:
        if not isinstance(item, dict):
            continue
        t = item.get("type", "")
        if t not in valid_types:
            continue
        # Нормализуем items внутри каждого намерения
        if t == "cart":
            cart_items = []
            for ci in item.get("items", []):
                if isinstance(ci, dict):
                    cart_items.append({
                        "name": str(ci.get("name", "")).strip(),
                        "quantity": int(ci.get("quantity", 1))
                    })
                elif isinstance(ci, str):
                    cart_items.append({"name": ci.strip(), "quantity": 1})
            item["items"] = cart_items
        else:
            item["items"] = _normalize_list(item.get("items", []))

        result.append(item)

    # Если Mistral вернул пустой список — fallback к обычному search
    if not result:
        result = [{"type": "search", "items": _normalize_list([user_text])}]

    return result

# ============================================================
# РОУТЫ
# ============================================================

@router.post("/analyze")
async def yovar_analyze(payload: YovarPayload, db: Database = Depends(get_db)):
    """Анализ одного намерения. Основной эндпоинт."""
    return await analyze_query(payload.query, payload.results_count)


@router.post("/correct")
async def yovar_correct(payload: YovarPayload, db: Database = Depends(get_db)):
    """Алиас для /analyze — обратная совместимость с yovar-test.html."""
    return await analyze_query(payload.query, payload.results_count)


@router.post("/multi")
async def yovar_multi(payload: YovarMultiPayload, db: Database = Depends(get_db)):
    """
    Мульти-интент анализ.
    Для запросов с несколькими намерениями одновременно.

    Пример запроса:
    {"query": "плов шашлык + добавь 3 капусты + есть ли акции в Шаурма Алижон"}

    Пример ответа:
    {"intents": [
      {"type":"search", "items":["плов","шашлык"]},
      {"type":"cart",   "items":[{"name":"капуста","quantity":3}]},
      {"type":"promo",  "venue":"Шаурма Алижон"}
    ]}
    """
    intents = await analyze_multi_intent(payload.query)
    return {"intents": intents, "count": len(intents)}
