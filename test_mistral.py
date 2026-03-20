#!/usr/bin/env python3

import os
import sys
import subprocess
import json

# ---------------------------
# 1. Проверка и создание виртуального окружения
# ---------------------------
venv_path = os.path.join(os.path.dirname(__file__), "venv")
venv_python = os.path.join(venv_path, "bin", "python")
venv_pip = os.path.join(venv_path, "bin", "pip")

if not os.path.isdir(venv_path):
    print("Виртуальное окружение не найдено. Создаём venv...")
    subprocess.check_call([sys.executable, "-m", "venv", venv_path])
    print("venv создан. Устанавливаем mistralai...")
    subprocess.check_call([venv_pip, "install", "--upgrade", "pip"])
    subprocess.check_call([venv_pip, "install", "mistralai"])

# ---------------------------
# 2. Перезапуск скрипта внутри venv, если нужно
# ---------------------------
if sys.executable != venv_python:
    print("Перезапуск скрипта внутри виртуального окружения...")
    os.execv(venv_python, [venv_python] + sys.argv)

# ---------------------------
# 3. Импорт только после активации venv
# ---------------------------
from mistralai.client import Mistral

# ---------------------------
# 4. Настройка API ключа
# ---------------------------
api_key = "zOYozUkX1QuTOBayrPQKpGVMnqMxBCvU"  # <-- твой ключ
client = Mistral(api_key=api_key)

# ---------------------------
# 5. Запрос к модели
# ---------------------------
model_name = "mistral-medium-latest"

user_prompt = (
    "Хочу заказать два плова, но бюджет должен быть до 30 сомони. "
    "Отвечай строго в виде JSON с полями: request, results, recommendation. "
    "Не добавляй лишнего текста."
)

response = client.chat.complete(
    model=model_name,
    messages=[{"role": "user", "content": user_prompt}]
)

# ---------------------------
# 6. Обработка ответа
# ---------------------------
text_response = response.choices[0].message.content

# Убираем ```json и ```
text_response = text_response.strip("`json\n").strip("`")

try:
    data = json.loads(text_response)
except json.JSONDecodeError:
    print("Ошибка при разборе JSON. Выводим как текст:")
    print(text_response)
    sys.exit(1)

# Красивый вывод
print(json.dumps(data, ensure_ascii=False, indent=2))
