#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import asyncio
import json
import logging
import os
import threading
from time import time
from typing import Tuple, List, Dict, Optional

import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import memepay

# — MemePay API:
MEMEPAY_API_KEY = "mp_66d4562d38569b88879f5c8e62a908ce"
MEMEPAY_SHOP_ID  = "755b0055-39a4-4a91-bc6e-3ed590f0de52"
MEMEPAY_CLIENT   = memepay.MemePay(api_key=MEMEPAY_API_KEY, shop_id=MEMEPAY_SHOP_ID)
# — Telegram Bot token, CryptoCloud, 1Plat, Google Sheets:
TELEGRAM_TOKEN      = "7198376627:AAG-vTOZu8XRMBA3nKflcouYx_lH03ETYjA"
BANNER_URL          = "https://drive.google.com/uc?export=view&id=1nuxsSRsHW1FkCsA9EDbfNApKNzMYjjwK"
CRYPTOCLOUD_API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.…"
# ID магазина для работы через API (integration ID)

MEMEPAY_SHOP_ID = "755b0055-39a4-4a91-bc6e-3ed590f0de52"
# Инициализируем клиент MemePay
MEMEPAY_CLIENT = memepay.MemePay(api_key=MEMEPAY_API_KEY, shop_id=MEMEPAY_SHOP_ID)
# Библиотека не инициализирует формат дат для синхронного клиента,
# из-за чего возможен AttributeError при парсинге времени.

MEMEPAY_SHOP_ID = "755b0055-39a4-4a91-bc6e-3ed590f0de52"

# Инициализируем клиент MemePay
MEMEPAY_CLIENT = memepay.MemePay(api_key=MEMEPAY_API_KEY, shop_id=MEMEPAY_SHOP_ID)


from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =========================================
# 1. КОНФИГУРАЦИЯ (ВАШИ РЕАЛЬНЫЕ ДАННЫЕ)
# =========================================

# — Telegram Bot token (BotFather). Замените на свой токен:
TELEGRAM_TOKEN = "7198376627:AAG-vTOZu8XRMBA3nKflcouYx_lH03ETYjA"

# — Ссылка на изображение-баннер (любой внешний URL):
BANNER_URL = "https://drive.google.com/uc?export=view&id=1nuxsSRsHW1FkCsA9EDbfNApKNzMYjjwK"

# — CryptoCloud API (V2):
CRYPTOCLOUD_API_KEY = (
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9."
    "eyJ1dWlkIjoiTlRjMk56TT0iLCJ0eXBlIjoicHJvamVjdCIsInYiOiJkOGVhMjg3"
    "MjNhZDAyYjg5YzBkZjcyMTAyZWI2MjQ2ZTZhOWE2NDBjMzlmNmNjOGU5ZDU5MTBj"
    "YmViZjMwN2E1IiwiZXhwIjo4ODE0ODk0MzQxMH0."
    "Gm4T9igl5jYHV0eZrZTWSeDqRMomnlMDIrWluysHJOU"
)
CRYPTOCLOUD_SHOP_ID = "GBfdQ4QR7vPirbDh"
CRYPTOCLOUD_API_BASE= "https://api.cryptocloud.plus/v2"
PLAT_SHOP_ID        = "378"
PLAT_SECRET         = "6tN-S3G-4Rj-JN212"
PLAT_API_BASE       = "https://1plat.cash"
CHANNEL_USERNAME    = "@BusinessSyndrome"
CHANNEL_URL         = "https://t.me/BusinessSyndrome"
SPREADSHEET_ID      = "1RP-8VTd4RTf92mR426MXznRw8f_-hWbrgyon6ar33-8"
SHEET_SCOPES        = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# — Google Sheets client
CREDS = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SHEET_SCOPES)
GC    = gspread.authorize(CREDS)

# — Кэш для вкладок (листов) с TTL = 1 час
_SHEET_CACHE: Dict[str, List[Dict]]   = {}
_SHEET_CACHE_LOCK                   = threading.Lock()
_SHEET_CACHE_LOADED_AT: Dict[str,float] = {}
_SHEET_CACHE_TTL                    = 3600  # 1 час
# Кэш для вкладок (листов) с TTL = 1 час
_SHEET_CACHE: Dict[str, List[Dict]] = {}
_SHEET_CACHE_LOCK = threading.Lock()
_SHEET_CACHE_LOADED_AT: Dict[str, float] = {}
_SHEET_CACHE_TTL = 3600  # 1 час


def _find_worksheet_by_name(sh: gspread.Spreadsheet, category: str):
    """
    Ищет лист (worksheet) в книге sh по имени category (игнорирует регистр).
    Если не найден, бросает WorksheetNotFound.
    """
    lower_cat = category.strip().lower()
    for ws in sh.worksheets():
        if ws.title.strip().lower() == lower_cat:
            return ws
    raise gspread.exceptions.WorksheetNotFound(f"Лист «{category}» не найден в таблице")


def _load_sheet_cache(sheet_name: str):
    """
    Загружает записи из листа sheet_name в кэш.
    """
    global _SHEET_CACHE, _SHEET_CACHE_LOADED_AT
    sh = GC.open_by_key(SPREADSHEET_ID)
    try:
        worksheet = _find_worksheet_by_name(sh, sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        _SHEET_CACHE[sheet_name] = []
        _SHEET_CACHE_LOADED_AT[sheet_name] = time()
        return
    records = worksheet.get_all_records()
    _SHEET_CACHE[sheet_name] = records
    _SHEET_CACHE_LOADED_AT[sheet_name] = time()


def get_courses_by_category(category: str, offset: int = 0, limit: int = 10) -> List[Dict]:
    """
    Возвращает список (offset:offset+limit) записей из листа <category>.
    Если листа нет, вернёт пустой список.
    """
    sheet_name = category.strip()
    with _SHEET_CACHE_LOCK:
        if (sheet_name not in _SHEET_CACHE) or (time() - _SHEET_CACHE_LOADED_AT.get(sheet_name, 0) > _SHEET_CACHE_TTL):
            _load_sheet_cache(sheet_name)
    data = _SHEET_CACHE.get(sheet_name, [])
    return data[offset: offset + limit]


def count_courses_by_category(category: str) -> int:
    """
    Возвращает общее число записей в листе <category>.
    """
    sheet_name = category.strip()
    with _SHEET_CACHE_LOCK:
        if (sheet_name not in _SHEET_CACHE) or (time() - _SHEET_CACHE_LOADED_AT.get(sheet_name, 0) > _SHEET_CACHE_TTL):
            _load_sheet_cache(sheet_name)
    data = _SHEET_CACHE.get(sheet_name, [])
    return len(data)


# =========================================
# 3. ПАМЯТЬ О ПОЛУЧЕННЫХ ОПЛАТАХ (paid_users.json)
# =========================================

PAID_USERS_FILE = "paid_users.json"


def load_paid_users() -> set:
    """
    Загружает из paid_users.json список user_id. 
    Если файла нет или он битый, создаёт новый с пустым массивом.
    """
    if not os.path.exists(PAID_USERS_FILE):
        with open(PAID_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        return set()
    try:
        with open(PAID_USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data if isinstance(data, list) else [])
    except Exception:
        return set()


def save_paid_users(users: set):
    """
    Сохраняет множество users (user_id) в paid_users.json.
    """
    try:
        with open(PAID_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(users), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[paid_users] Ошибка при записи {PAID_USERS_FILE}: {e}")


PAID_USERS = load_paid_users()  # загружаем при старте


def has_active_subscription(user_id: int) -> bool:
    """
    True, если user_id уже есть в списке оплаченных.
    """
    return user_id in PAID_USERS


def add_subscription(user_id: int):
    """
    Добавляет user_id в множество оплаченных и сразу сохраняет в JSON.
    """
    PAID_USERS.add(user_id)
    save_paid_users(PAID_USERS)


# =========================================
# 4. INVOICES: CryptoCloud (invoices.json)
# =========================================

INVOICES_FILE = "invoices.json"
INVOICES_LOCK = threading.Lock()
# Ключ: "<user_id>|<category>|<offset>|<idx>" → uuid счета
INVOICES: Dict[str, str] = {}


def load_invoices_cc():
    """
    Загружает INVOICES из invoices.json. Если файл не существует, создаёт пустой словарь.
    """
    global INVOICES
    if os.path.exists(INVOICES_FILE):
        try:
            with open(INVOICES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    INVOICES = data
                else:
                    INVOICES = {}
        except Exception as e:
            print(f"[invoices_cc] Ошибка при чтении {INVOICES_FILE}: {e}")
            INVOICES = {}
    else:
        INVOICES = {}
    print(f"[invoices_cc] Загружено {len(INVOICES)} записей.")


def save_invoices_cc():
    """
    Сохраняет текущий словарь INVOICES в invoices.json.
    """
    try:
        with INVOICES_LOCK:
            with open(INVOICES_FILE, "w", encoding="utf-8") as f:
                json.dump(INVOICES, f, ensure_ascii=False, indent=2)
        print(f"[invoices_cc] Сохранено {len(INVOICES)} записей.")
    except Exception as e:
        print(f"[invoices_cc] Ошибка при записи {INVOICES_FILE}: {e}")


def make_invoice_key(user_id: int, category: str, offset: int, idx: int) -> str:
    """
    Собирает строковый ключ для INVOICES из параметров пользователя и выбранного курса.
    """
    return f"{user_id}|{category}|{offset}|{idx}"


# =========================================
# 5. INVOICES: 1Plat (invoices_1plat.json)
# =========================================

INVOICES_1PLAT_FILE = "invoices_1plat.json"
INVOICES_1PLAT_LOCK = threading.Lock()
# Ключ: "<user_id>|<category>|<offset>|<idx>" → guid счета
INVOICES_1PLAT: Dict[str, str] = {}

# 6bis. INVOICES: MemePay (invoices_memepay.json)
INVOICES_MEMEPAY_FILE   = "invoices_memepay.json"
INVOICES_MEMEPAY_LOCK   = threading.Lock()
INVOICES_MEMEPAY: Dict[str, str] = {}

def load_invoices_memepay():
    """
    Загружает INVOICES_MEMEPAY из invoices_memepay.json.
    """
    global INVOICES_MEMEPAY
    if os.path.exists(INVOICES_MEMEPAY_FILE):
        try:
            with open(INVOICES_MEMEPAY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                INVOICES_MEMEPAY = data if isinstance(data, dict) else {}
        except Exception:
            INVOICES_MEMEPAY = {}
    else:
        INVOICES_MEMEPAY = {}
    print(f"[invoices_memepay] Загружено {len(INVOICES_MEMEPAY)} записей.")

def save_invoices_memepay():
    """
    Сохраняет INVOICES_MEMEPAY в invoices_memepay.json.
    """
    try:
        with INVOICES_MEMEPAY_LOCK:
            with open(INVOICES_MEMEPAY_FILE, "w", encoding="utf-8") as f:
                json.dump(INVOICES_MEMEPAY, f, ensure_ascii=False, indent=2)
        print(f"[invoices_memepay] Сохранено {len(INVOICES_MEMEPAY)} записей.")
    except Exception as e:
        print(f"[invoices_memepay] Ошибка при записи {INVOICES_MEMEPAY_FILE}: {e}")



def load_invoices_1plat():
    """
    Загружает INVOICES_1PLAT из invoices_1plat.json. Если файл не существует, создаёт пустой словарь.
    """
    global INVOICES_1PLAT
    if os.path.exists(INVOICES_1PLAT_FILE):
        try:
            with open(INVOICES_1PLAT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    INVOICES_1PLAT = data
                else:
                    INVOICES_1PLAT = {}
        except Exception as e:
            print(f"[invoices_1plat] Ошибка при чтении {INVOICES_1PLAT_FILE}: {e}")
            INVOICES_1PLAT = {}
    else:
        INVOICES_1PLAT = {}
    print(f"[invoices_1plat] Загружено {len(INVOICES_1PLAT)} записей.")


def save_invoices_1plat():
    """
    Сохраняет текущий словарь INVOICES_1PLAT в invoices_1plat.json.
    """
    try:
        with INVOICES_1PLAT_LOCK:
            with open(INVOICES_1PLAT_FILE, "w", encoding="utf-8") as f:
                json.dump(INVOICES_1PLAT, f, ensure_ascii=False, indent=2)
        print(f"[invoices_1plat] Сохранено {len(INVOICES_1PLAT)} записей.")
    except Exception as e:
        print(f"[invoices_1plat] Ошибка при записи {INVOICES_1PLAT_FILE}: {e}")


# =========================================
# 6. CRYPTOCLOUD API V2: создание и проверка счета
# =========================================
def create_cryptocloud_invoice(
    user_id: int,
    category: str,
    offset: int,
    idx: int,
    rub_amount: float = 490.0,
    rub_currency: str = "RUB"
) -> Tuple[str, str]:
    """
    Создаёт счет через CryptoCloud V2 (POST /invoice/create).
    Возвращает (invoice_uuid, pay_link).
    """
    order_id = f"{user_id}:{category}:{offset}:{idx}"
    url = f"{CRYPTOCLOUD_API_BASE}/invoice/create"
    headers = {
        "Authorization": f"Token {CRYPTOCLOUD_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "shop_id": CRYPTOCLOUD_SHOP_ID,
        "amount": rub_amount,
        "currency": rub_currency,
        "order_id": order_id,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    print(f"[create_invoice_cc] HTTP {resp.status_code}")
    print(f"[create_invoice_cc] BODY: {resp.text}")

    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Невалидный ответ при создании счета CryptoCloud: HTTP {resp.status_code}")

    if data.get("status") != "success":
        err = data.get("result") or data.get("detail") or data.get("error") or data
        raise RuntimeError(f"CryptoCloud вернул ошибку при создании счета: {err}")

    result = data["result"]
    invoice_uuid = result.get("uuid")
    if not invoice_uuid:
        raise RuntimeError(f"Не получили uuid счета от CryptoCloud: {result}")

    pay_link = f"https://pay.cryptocloud.plus/{invoice_uuid}?lang=ru"
    return invoice_uuid, pay_link


def check_invoice_status_cc(invoice_uuid: str) -> str:
    """
    Проверяет статус счета через V2-метод:
        POST https://api.cryptocloud.plus/v2/invoice/merchant/info
    В теле JSON: {"uuids": ["<invoice_uuid>"]}
    Возвращает строку со статусом инвойса: "created", "pending", "paid", "overpaid", "canceled" и т.д.
    """
    url = f"{CRYPTOCLOUD_API_BASE}/invoice/merchant/info"
    headers = {
        "Authorization": f"Token {CRYPTOCLOUD_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"uuids": [invoice_uuid]}

    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    print(f"[check_status_cc] HTTP {resp.status_code}")
    print(f"[check_status_cc] BODY: {resp.text}")

    if resp.status_code != 200:
        raise RuntimeError(f"CryptoCloud: счёт не найден или ошибка авторизации (HTTP {resp.status_code})")

    try:
        data = resp.json()
    except Exception as e:
        raise RuntimeError(f"Не удалось распарсить JSON-ответ при проверке CryptoCloud: {e}")

    if data.get("status") != "success":
        err = data.get("detail") or data.get("result") or data.get("error") or data
        raise RuntimeError(f"CryptoCloud вернул ошибку при проверке: {err}")

    result_list = data.get("result")
    if not isinstance(result_list, list) or len(result_list) == 0:
        raise RuntimeError("CryptoCloud: в ответе нет result или result пустой")

    info = result_list[0]
    status = info.get("status")
    if not status:
        raise RuntimeError("CryptoCloud: в ответе нет поля status для инвойса")
    return status  # "created", "pending", "paid", "overpaid", "canceled", ...

# =========================================
# 7. MemePay API: создание и проверка счёта
# =========================================

def create_memepay_invoice(amount_rub: float = 490.0, method: Optional[str] = None) -> Tuple[str, str]:
    """Создаёт платёж через MemePay и возвращает (payment_id, pay_url)."""
    resp = MEMEPAY_CLIENT.create_payment(amount=amount_rub, method=method)
    return resp.payment_id, resp.payment_url

def check_memepay_status(payment_id: str) -> str:
    """Возвращает статус платежа MemePay."""
    info = MEMEPAY_CLIENT.get_payment_info(payment_id)
    return info.status


# =========================================
# 7. 1Plat API: создание и проверка счета (crypto и SBP)
# =========================================

def create_1plat_invoice(
    user_id: int,
    category: str,
    offset: int,
    idx: int,
    amount_rub: int = 490,
    method: str = "crypto",
    currency: Optional[str] = "USDT",
    email: str = ""
) -> Tuple[str, str]:
    """
    Создаёт счет через 1Plat (POST /api/merchant/order/create/by-api).
    method: "crypto" или "sbp" (или "card", "qr" и т.д., но мы используем "crypto" и "sbp").
    Для crypto обязательна currency (например, "USDT"); для sbp currency не передаётся.
    Возвращает (guid, pay_link).
    """
    merchant_order_id = f"{user_id}:{category}:{offset}:{idx}"
    url = f"{PLAT_API_BASE}/api/merchant/order/create/by-api"
    headers = {
        "x-shop": PLAT_SHOP_ID,
        "x-secret": PLAT_SECRET,
        "Content-Type": "application/json",
    }

    payload = {
        "merchant_order_id": merchant_order_id,
        "user_id": user_id,
        "amount": amount_rub,
        "method": method,
        "email": email,
    }
    if method == "crypto" and currency:
        payload["currency"] = currency

    # Отправляем запрос
    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    print("=== DEBUG create_1plat_invoice ===")
    print("URL   :", url)
    print("HEADERS:", headers)
    print("PAYLOAD:", json.dumps(payload, ensure_ascii=False))
    print("==============================")
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"1Plat: невалидный ответ при создании счета (HTTP {resp.status_code})")

    if resp.status_code != 200 or not data.get("success"):
        err = data.get("error") or data.get("message") or data
        raise RuntimeError(f"1Plat вернул ошибку при создании счета: {err}")

    guid = data.get("guid")
    pay_url = data.get("url")  # URL → "https://pay.1plat.cash/pay/{guid}"
    if not guid or not pay_url:
        raise RuntimeError(f"1Plat: не получили guid или url при создании счета: {data}")

    return guid, pay_url


def check_1plat_invoice_status(guid: str) -> int:
    """
    Проверяет статус счета через GET /api/merchant/order/info/:guid/by-api.
    Возвращает целое значение status:
      -2, -1, 0, 1, 2
      (см. документацию 1Plat: 0 = ожидает оплаты, 1 = успешно оплачен,
       ожидает мерчантом, 2 = подтверждён мерчантом и полностью закрыт).
      (см. документацию 1Plat: 0 = ожидает оплаты, 1 = успешно оплачен,
       ожидает мерчантом, 2 = подтверждён мерчантом и полностью закрыт).

      (см. документацию 1Plat: 0 = ожидает оплаты, 1 = успешно оплачен,
       ожидает мерчантом, 2 = подтверждён мерчантом и полностью закрыт).
      (см. документацию 1Plat: 0 = ожидает оплаты, 1 = успешно оплачен,
       ожидает мерчантом, 2 = подтверждён мерчантом и полностью закрыт).

      (см. документацию 1Plat: 0 = ожидает оплаты, 1 = успешно оплачен,
       ожидает мерчантом, 2 = подтверждён мерчантом и полностью закрыт).

      (см. документацию 1Plat: 0 = ожидает оплаты, 1 = успешно оплачен, ожидает
       мерчантом, 2 = подтверждён мерчантом и полностью закрыт).

    # --- ТЕСТОВАЯ ЗАГЛУШКА: для GUID="TEST-GUID-1234" сразу считаем платёж успешным
    if guid == "TEST-GUID-1234":
        return 2



    """

    # --- ТЕСТОВАЯ ЗАГЛУШКА: для GUID="TEST-GUID-1234" сразу считаем платёж успешным
    if guid == "TEST-GUID-1234":
        return 2
    url = f"{PLAT_API_BASE}/api/merchant/order/info/{guid}/by-api"
    headers = {
        "x-shop": PLAT_SHOP_ID,
        "x-secret": PLAT_SECRET,
    }
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"[check_status_1plat] HTTP {resp.status_code}")
    print(f"[check_status_1plat] BODY: {resp.text}")

    try:
        data = resp.json()
    except Exception as e:
        raise RuntimeError(f"1Plat: не удалось распарсить JSON-ответ при проверке: {e}")

    if not data.get("success"):
        err = data.get("error") or data
        raise RuntimeError(f"1Plat вернул ошибку при проверке счета: {err}")

    payment = data.get("payment", {})
    status = payment.get("status")
    if status is None:
        raise RuntimeError("1Plat: нет поля status в ответе при проверке счета")
    return int(status)  # -2, -1, 0, 1, 2


# =========================================
# 8. ЛОГИРОВАНИЕ
# =========================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# =========================================
# 9. ИНИЦИАЛИЗАЦИЯ ТЕЛЕГРАМ-БОТА
# =========================================

bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
# — Асинхронная проверка 1Plat (должна быть до @dp.startup)

async def poll_1plat_invoices():
    while True:
        items = list(INVOICES_1PLAT.items())
        for key, guid in items:
            try:
                status = check_1plat_invoice_status(guid)
            except Exception as e:
                logger.warning(f"[poll_1plat] Ошибка при проверке {guid}: {e}")
                continue

            user_id_str, category, offset_str, idx_str = key.split("|", 3)
            user_id = int(user_id_str)
            offset = int(offset_str)
            idx = int(idx_str)

            if status in (1, 2):
                with INVOICES_1PLAT_LOCK:
                    INVOICES_1PLAT.pop(key, None)
                save_invoices_1plat()
                add_subscription(user_id)

                cr = get_courses_by_category(category, offset, 10)[idx]
                title = cr["Название"]
                cover = cr.get("Обложка") or BANNER_URL
                tele_desc = cr.get("Описание", "").strip()
                course_link = cr.get("Ссылка на курс", "").strip()

                caption = f"🎉 <b>{title}</b>\n\nТеперь у вас есть доступ к материалам:"
                kb = InlineKeyboardBuilder()
                if tele_desc:
                    kb.button(text="📓 Читать описание", url=tele_desc)
                if course_link:
                    kb.button(text="💎 Перейти к изучению", url=course_link)
                kb.adjust(1)

                await bot.send_photo(
                    chat_id=user_id,
                    photo=cover,
                    caption=caption,
                    reply_markup=kb.as_markup(),
                )

            elif status in (-1, -2):
                with INVOICES_1PLAT_LOCK:
                    INVOICES_1PLAT.pop(key, None)
                save_invoices_1plat()

        await asyncio.sleep(60)


# Эмодзи для отображения рядом с курсом
CURRENCY_EMOJI = ["💴", "💷", "💶", "💲"]

# =========================================
# Фоновая проверка счетов 1Plat
# =========================================
# =========================================
# 10. HANDLERS
# =========================================

@dp.startup()
async def on_startup():
    """
    При старте бота:
      • Загружаем незавершённые счета из invoices.json и invoices_1plat.json
      • Сбрасываем старые апдейты (Webhook-оконфликт)
    """
    load_invoices_cc()
    load_invoices_memepay()
    load_invoices_1plat()
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot started, polling is ready…")

    # Запускаем фоновую задачу для авто-проверки 1Plat
    asyncio.create_task(poll_1plat_invoices())



@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    Обработчик команды /start:
      • Продающий текст
      • Стикер
      • Inline-кнопка «💎 GO»
    """
    selling_text = (
        "<b>Строим капитал, пока другие мечтают\n"
        "Находим ходы там, где все уперлись в стену\n"
        "Качаем дисциплину, характер и мозги до предела\n"
        "Бросаем вызов каждому дню, а не ждём шанса\n\n"
        "Чувствуешь, что создан для большего?\n"
        "Тогда не упусти свой момент:\n"
        "Доступ к тысячам курсов всего за 490 ₽ (≈ 5–6 USD)!\n\n"
        "Обновляемся, как Netflix. Только ты прокачиваешь себя, а не деградируешь🧬\n\n"
        "Потому что «потом» — это ложь, самодельная петля, на которой вешаешь цели💀\n\n"
        "Хватит мечтать — пора действовать! Ждём тебя в своих рядах!💎</b>"
    )
    await message.answer(selling_text)

    await message.answer_sticker(
        "CAACAgUAAxkBAAE1kl1oOEACQJAT9YaXxuWR77eFnTaC_gACYxkAAhoBCFQAATaz0ezI1JI2BA"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="💎 GO", callback_data="go")
    kb.adjust(1)
    await message.answer("Жми «💎 GO», чтобы выбрать категорию", reply_markup=kb.as_markup())


@dp.callback_query(lambda c: c.data == "go")
async def go_callback(query: CallbackQuery):
    """
    Callback «go»: Проверяем подписку на канал.
     • Если не подписан — предлагаем подписаться.
     • Если подписан — показываем категории.
    """
    user_id = query.from_user.id
    member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
    if member.status not in ("creator", "administrator", "member"):
        kb_sub = InlineKeyboardBuilder()
        kb_sub.button(text="Подписаться🌴", url=CHANNEL_URL)
        kb_sub.button(text="Проверить подписку", callback_data="check_subscription")
        kb_sub.adjust(1)

        await query.message.edit_media(
            media=InputMediaPhoto(
                media=BANNER_URL,
                caption="Сначала подпишись на канал, чтоб не потерять нас:",
                parse_mode="HTML"
            ),
            reply_markup=kb_sub.as_markup()
        )
        await query.answer()
        return

    await show_categories(query)
    await query.answer()


@dp.callback_query(lambda c: c.data == "check_subscription")
async def check_subscription(query: CallbackQuery):
    """
    Callback «check_subscription»:
     • Если подписан — благодарим и переходим к категориям.
     • Если нет — снова просим подписаться.
    """
    user_id = query.from_user.id
    member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
    if member.status in ("creator", "administrator", "member"):
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=BANNER_URL,
                caption="Спасибо за подписку! Теперь можно выбрать категорию 👍",
                parse_mode="HTML"
            ),
            reply_markup=None
        )
        await asyncio.sleep(0.3)

        class FakeQuery:
            def __init__(self, message, from_user):
                self.data = "show_categories"
                self.message = message
                self.from_user = from_user
            async def answer(self, *args, **kwargs):
                pass

        fake = FakeQuery(query.message, query.from_user)
        await show_categories(fake)
    else:
        kb_retry = InlineKeyboardBuilder()
        kb_retry.button(text="Подписаться🌴", url=CHANNEL_URL)
        kb_retry.button(text="Проверить подписку", callback_data="check_subscription")
        kb_retry.adjust(1)

        await query.message.edit_media(
            media=InputMediaPhoto(
                media=BANNER_URL,
                caption=(
                    "Друг, ты ещё не подписан на канал.\n"
                    "Подпишись, а затем жми «Проверить подписку»."
                ),
                parse_mode="HTML"
            ),
            reply_markup=kb_retry.as_markup()
        )
    await query.answer()


@dp.callback_query(lambda c: c.data == "show_categories")
async def show_categories(query: CallbackQuery):
    """
    Callback «show_categories»: Показываем inline-клавиатуру с категориями (2 кнопки в ряд).
    Если пользователь отписался после «go», снова предлагаем подписаться.
    """
    user_id = query.from_user.id
    member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
    if member.status not in ("creator", "administrator", "member"):
        kb_sub = InlineKeyboardBuilder()
        kb_sub.button(text="Подписаться🌴", url=CHANNEL_URL)
        kb_sub.button(text="Проверить подписку", callback_data="check_subscription")
        kb_sub.adjust(1)

        await query.message.edit_media(
            media=InputMediaPhoto(
                media=BANNER_URL,
                caption="Сначала подпишись на канал, чтоб не потерять нас:",
                parse_mode="HTML"
            ),
            reply_markup=kb_sub.as_markup()
        )
        await query.answer()
        return

    categories = [
        ("💎TELEGRAM",       "Telegram"),
        ("YOUTUBE",          "YouTube"),
        ("VK",               "VK"),
        ("TIKTOK",           "TIKTOK"),
        ("AVITO",            "АВИТО"),
        ("ДРОПШИППИНГ",      "ДРОПШИППИНГ"),
        ("МАРКЕТПЛЕЙСЫ",     "МАРКЕТПЛЕЙСЫ"),
        ("АРБИТРАЖ ТРАФИКА", "АРБИТРАЖ ТРАФИКА"),
        ("ХАКИНГ",           "ХАКИНГ"),
        ("САМОРАЗВИТИЕ",     "САМОРАЗВИТИЕ"),
        ("БАЗЫ ПОСТАВЩИКОВ", "БАЗЫ ПОСТАВЩИКОВ"),
        ("НЕЙРОСЕТИ",        "НЕЙРОСЕТИ"),
        ("ФРИЛАНС",          "ФРИЛАНС"),
        ("КРИПТОВАЛЮТЫ",     "КРИПТОВАЛЮТЫ"),
        ("ТРЕЙДИНГ",         "ТРЕЙДИНГ"),
        ("СХЕМЫ ЗАРАБОТКА",  "СХЕМЫ ЗАРАБОТКА"),
        ("ИНВЕСТИЦИИ",       "ИНВЕСТИЦИИ"),
        ("ПСИХОЛОГИЯ",       "ПСИХОЛОГИЯ"),
        ("ПИКАП",            "ПИКАП"),
        ("ПРОДАЖИ💎",        "ПРОДАЖИ"),
    ]

    kb = InlineKeyboardBuilder()
    for display_text, cat_key in categories:
        kb.button(text=display_text, callback_data=f"cat|{cat_key}|0")
    kb.adjust(2)

    await query.message.edit_media(
        media=InputMediaPhoto(
            media=BANNER_URL,
            caption="📓 Выбери категорию:",
            parse_mode="HTML"
        ),
        reply_markup=kb.as_markup()
    )
    await query.answer()


@dp.callback_query(lambda c: c.data.startswith("cat|"))
async def cat_callback(query: CallbackQuery):
    """
    Callback «cat|<category>|<offset>»:
     • Если не подписан — просим подписаться.
     • Иначе — показываем список курсов с пагинацией.
    """
    user_id = query.from_user.id
    member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
    if member.status not in ("creator", "administrator", "member"):
        kb_sub = InlineKeyboardBuilder()
        kb_sub.button(text="Подписаться🌴", url=CHANNEL_URL)
        kb_sub.button(text="Проверить подписку", callback_data="check_subscription")
        kb_sub.adjust(1)
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=BANNER_URL,
                caption="Сначала подпишись на канал, чтоб не потерять нас:",
                parse_mode="HTML"
            ),
            reply_markup=kb_sub.as_markup()
        )
        await query.answer()
        return

    _, category, offset_str = query.data.split("|", 2)
    offset = int(offset_str)
    total = count_courses_by_category(category)

    if total == 0:
        kb_empty = InlineKeyboardBuilder()
        kb_empty.button(text="Категории", callback_data="show_categories")
        kb_empty.adjust(1)
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=BANNER_URL,
                caption=f"📓 Курсы «{category}»\n\n❗️ Нет доступных курсов в этой категории.",
                parse_mode="HTML"
            ),
            reply_markup=kb_empty.as_markup()
        )
        await query.answer()
        return

    courses = get_courses_by_category(category, offset, 10)
    page_num = offset // 10 + 1
    total_pages = (total - 1) // 10 + 1

    header = f"📓 Курсы «{category}»\nСтр. {page_num} из {total_pages}\n\n"
    lines = [f"➤ {i + 1}. {cr['Название']}" for i, cr in enumerate(courses)]
    caption = header + "\n\n".join(lines)

    kb = InlineKeyboardBuilder()
    for i in range(len(courses)):
        kb.button(text=str(i + 1), callback_data=f"course|{category}|{offset}|{i}")
    kb.adjust(5)

    nav_buttons = []
    if offset > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="❮", callback_data=f"cat|{category}|{offset - 10}")
        )
    nav_buttons.append(
        InlineKeyboardButton(text=f"{page_num}/{total_pages}", callback_data=f"cat|{category}|{offset}")
    )
    nav_buttons.append(
        InlineKeyboardButton(text="Категории", callback_data="show_categories")
    )
    if offset + 10 < total:
        nav_buttons.append(
            InlineKeyboardButton(text="❯", callback_data=f"cat|{category}|{offset + 10}")
        )
    kb.row(*nav_buttons)

    await query.message.edit_media(
        media=InputMediaPhoto(media=BANNER_URL, caption=caption, parse_mode="HTML"),
        reply_markup=kb.as_markup()
    )
    await query.answer()


@dp.callback_query(lambda c: c.data.startswith("course|"))
async def course_callback(query: CallbackQuery):
    """
    Callback «course|<category>|<offset>|<idx>»:
     • Если пользователь уже оплатил (has_active_subscription) — показываем реальные ссылки.
     • Иначе — показываем кнопку «Перейти к изучению» (pay_options).
    """
    user_id = query.from_user.id
    member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
    if member.status not in ("creator", "administrator", "member"):
        kb_sub = InlineKeyboardBuilder()
        kb_sub.button(text="Подписаться🌴", url=CHANNEL_URL)
        kb_sub.button(text="Проверить подписку", callback_data="check_subscription")
        kb_sub.adjust(1)
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=BANNER_URL,
                caption="Сначала подпишись на канал, чтоб не потерять нас:",
                parse_mode="HTML"
            ),
            reply_markup=kb_sub.as_markup()
        )
        await query.answer()
        return

    _, category, offset_str, idx_str = query.data.split("|", 3)
    offset = int(offset_str)
    idx = int(idx_str)

    cr = get_courses_by_category(category, offset, 10)[idx]
    title = cr["Название"]
    cover = cr.get("Обложка") or cr.get("Обложка (URL)", BANNER_URL)
    tele_desc = cr.get("", "").strip()
    course_link = cr.get("Ссылка на курс", "").strip()

    # Если пользователь уже оплатил, сразу отображаем реальные ссылки
    if has_active_subscription(user_id):
        random_emoji = CURRENCY_EMOJI[hash(title) % len(CURRENCY_EMOJI)]
        caption = f"{random_emoji} <b>{title}</b>"

        kb = InlineKeyboardBuilder()
        if tele_desc:
            kb.button(text="📓 Читать описание", url=tele_desc)
        if course_link:
            kb.button(text="💎 Перейти к изучению", url=course_link)
        kb.button(text="🔙 Вернуться", callback_data=f"cat|{category}|{offset}")
        kb.adjust(1)

        await query.message.edit_media(
            media=InputMediaPhoto(media=cover, caption=caption, parse_mode="HTML"),
            reply_markup=kb.as_markup()
        )
        await query.answer()
        return

    # Если ещё не оплатил, показываем кнопку «Перейти к изучению»
    random_emoji = CURRENCY_EMOJI[hash(title) % len(CURRENCY_EMOJI)]
    caption = f"{random_emoji} <b>{title}</b>"

    kb = InlineKeyboardBuilder()
    if tele_desc:
        kb.button(text="📓 Читать описание", url=tele_desc)
    kb.button(text="💎 Перейти к изучению", callback_data=f"pay_options|{category}|{offset}|{idx}")
    kb.button(text="🔙 Вернуться", callback_data=f"cat|{category}|{offset}")
    kb.adjust(1)

    await query.message.edit_media(
        media=InputMediaPhoto(media=cover, caption=caption, parse_mode="HTML"),
        reply_markup=kb.as_markup()
    )
    await query.answer()


@dp.callback_query(lambda c: c.data.startswith("pay_options|"))
async def pay_options_callback(query: CallbackQuery):
    """
    Callback «pay_options|<category>|<offset>|<idx>»:
    Показываем «Выберите способ оплаты💎» и кнопки «CryptoCloud☁️», «1Plat Crypto💎»,
    «1Plat SBP📱» и «🔙 Вернуться».
    """
    _, category, offset_str, idx_str = query.data.split("|", 3)
    offset = int(offset_str)
    idx = int(idx_str)

    new_caption = "Выберите способ оплаты💎"
    kb = InlineKeyboardBuilder()
    kb.button(text="CryptoCloud☁️", callback_data=f"pay_cc|{category}|{offset}|{idx}")
    kb.button(text="1Plat Crypto💎", callback_data=f"pay_1plat_crypto|{category}|{offset}|{idx}")
    kb.button(text="1Plat SBP📱", callback_data=f"pay_1plat_sbp|{category}|{offset}|{idx}")
    kb.button(text="MemePay🤣", callback_data=f"pay_memepay|{category}|{offset}|{idx}")
    kb.button(text="🔙 Вернуться", callback_data=f"course|{category}|{offset}|{idx}")
    kb.adjust(1)

    await query.message.edit_caption(
        caption=new_caption,
        parse_mode=ParseMode.HTML,
        reply_markup=kb.as_markup()
    )
    await query.answer()


# ----- CryptoCloud callbacks -----

@dp.callback_query(lambda c: c.data.startswith("pay_cc|"))
async def pay_cc_callback(query: CallbackQuery):
    """
    Callback «pay_cc|<category>|<offset>|<idx>»:
    1) Убедимся, что пользователь подписан на канал.
    2) Создаём счёт через CryptoCloud.
    3) Сохраняем invoice_uuid в invoices.json.
    4) Отправляем карточку «Оплатить крипто» + «🔄 Проверить оплату» + «🔙 Вернуться».
    """
    _, category, offset_str, idx_str = query.data.split("|", 3)
    offset = int(offset_str)
    idx = int(idx_str)
    user_id = query.from_user.id

    member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
    if member.status not in ("creator", "administrator", "member"):
        kb_sub = InlineKeyboardBuilder()
        kb_sub.button(text="Подписаться🌴", url=CHANNEL_URL)
        kb_sub.button(text="Проверить подписку", callback_data="check_subscription")
        kb_sub.adjust(1)
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=BANNER_URL,
                caption="Сначала подпишись на канал, чтоб не потерять нас:",
                parse_mode="HTML"
            ),
            reply_markup=kb_sub.as_markup()
        )
        await query.answer()
        return

    # 1) Создаём новый счёт CryptoCloud
    try:
        invoice_uuid, pay_link = create_cryptocloud_invoice(
            user_id=user_id,
            category=category,
            offset=offset,
            idx=idx,
            rub_amount=490.0,
            rub_currency="RUB"
        )
    except Exception as e:
        await query.answer("❌ Не удалось создать счёт CryptoCloud. Попробуйте позже.", show_alert=True)
        print(f"[pay_cc] Ошибка при создании счета CryptoCloud: {e}")
        return

    # 2) Сохраняем invoice_uuid
    key_cc = make_invoice_key(user_id, category, offset, idx)
    with INVOICES_LOCK:
        INVOICES[key_cc] = invoice_uuid
    save_invoices_cc()

    # 3) Отправляем карточку с кнопками «Оплатить крипто» и «🔄 Проверить оплату»
    caption = (
        "<b>⚡ Чтобы получить доступ к курсу, оплатите счёт ниже.</b>\n\n"
        "Сумма: <code>490 ₽</code>\n"
        "CryptoCloud пересчитает её в USD/USDT по текущему курсу.\n\n"
        "Нажмите кнопку «Оплатить крипто», чтобы перейти на страницу оплаты.\n\n"
        "После оплаты нажмите «🔄 Проверить оплату»."
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="Оплатить крипто", url=pay_link)
    kb.button(text="🔄 Проверить оплату", callback_data=f"check_payment_cc|{category}|{offset}|{idx}")
    kb.button(text="🔙 Вернуться", callback_data=f"pay_options|{category}|{offset}|{idx}")
    kb.adjust(1)

    await bot.send_photo(
        chat_id=user_id,
        photo=BANNER_URL,
        caption=caption,
        reply_markup=kb.as_markup()
    )
    await query.answer()


@dp.callback_query(lambda c: c.data.startswith("check_payment_cc|"))
async def check_payment_cc_callback(query: CallbackQuery):
    """
    Callback «check_payment_cc|<category>|<offset>|<idx>»:
    1) Берём invoice_uuid из invoices.json.
    2) Делаем POST /invoice/merchant/info → получаем status.
       • Если status in ("created","pending","draft") → «Счёт ещё не оплачен…»
       • Если status in ("paid","overpaid","success") → считаем оплату успешной:
           – удаляем запись из invoices.json,
           – добавляем user_id в PAID_USERS (paid_users.json),
           – отправляем конечную карточку с прямыми ссылками.
       • Если status in ("expired","canceled","refunded") → «Срок истёк или отменён…»
    """
    _, category, offset_str, idx_str = query.data.split("|", 3)
    offset = int(offset_str)
    idx = int(idx_str)
    user_id = query.from_user.id

    key_cc = make_invoice_key(user_id, category, offset, idx)
    invoice_uuid = INVOICES.get(key_cc)
    if not invoice_uuid:
        await query.answer("❌ Счет не найден. Сначала нажмите «Оплатить крипто».", show_alert=True)
        return

    try:
        status = check_invoice_status_cc(invoice_uuid)
    except Exception as e:
        await query.answer("❌ Не удалось проверить оплату CryptoCloud. Попробуйте позже.", show_alert=True)
        print(f"[check_payment_cc] Ошибка при check_invoice_status_cc для uuid={invoice_uuid}: {e}")
        return

    # Статусы, означающие, что платёж ещё не пришёл/не подтверждён
    if status in ("created", "pending", "draft"):
        await query.answer("⌛ Платёж CryptoCloud ещё не подтверждён. Подождите минуту и попробуйте снова.", show_alert=True)
        return

    # Статусы, означающие успешную оплату
    if status in ("paid", "overpaid", "success"):
        # Удаляем запись
        with INVOICES_LOCK:
            INVOICES.pop(key_cc, None)
        save_invoices_cc()

        # Добавляем пользователя в PAID_USERS
        add_subscription(user_id)
        await query.answer("✅ Оплата CryptoCloud подтверждена! Доступ к курсу ниже.", show_alert=True)

        cr = get_courses_by_category(category, offset, 10)[idx]
        title = cr["Название"]
        cover = cr.get("Обложка") or cr.get("Обложка (URL)", BANNER_URL)
        tele_desc = cr.get("", "").strip()
        course_link = cr.get("Ссылка на курс", "").strip()

        caption = f"🎉 <b>{title}</b>\n\nТеперь у вас есть доступ к материалам:"
        kb = InlineKeyboardBuilder()
        if tele_desc:
            kb.button(text="📓 Читать описание", url=tele_desc)
        if course_link:
            kb.button(text="💎 Перейти к изучению", url=course_link)
        kb.adjust(1)

        try:
            await bot.send_photo(
                chat_id=user_id,
                photo=cover,
                caption=caption,
                reply_markup=kb.as_markup()
            )
        except Exception as send_err:
            print(f"[check_payment_cc] Не удалось отправить карточку курса user_id={user_id}: {send_err}")
        return

    # Статусы, означающие, что счет просрочен/отменён
    if status in ("expired", "canceled", "refunded"):
        with INVOICES_LOCK:
            INVOICES.pop(key_cc, None)
        save_invoices_cc()
        await query.answer(
            "❌ Срок оплаты CryptoCloud истёк или счёт отменён. Нажмите «🔙 Вернуться» и создайте новый счёт.",
            show_alert=True
        )
        return

    # Непредвиденные статусы
    await query.answer(f"⚠ Статус CryptoCloud: «{status}». Возможно, платёж не завершён.", show_alert=True)


# ----- 1Plat callbacks -----

@dp.callback_query(lambda c: c.data.startswith("pay_1plat_crypto|"))
async def pay_1plat_crypto_callback(query: CallbackQuery):
    """
    Callback «pay_1plat_crypto|<category>|<offset>|<idx>»:
    1) Убедимся, что пользователь подписан на канал.
    2) Создаём счёт через 1Plat (crypto).
    3) Сохраняем guid в invoices_1plat.json.
    4) Отправляем карточку «Оплатить крипто (1Plat)» + «🔄 Проверить оплату 1Plat» + «🔙 Вернуться».
    """
    _, category, offset_str, idx_str = query.data.split("|", 3)
    offset = int(offset_str)
    idx = int(idx_str)
    user_id = query.from_user.id

    member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
    if member.status not in ("creator", "administrator", "member"):
        kb_sub = InlineKeyboardBuilder()
        kb_sub.button(text="Подписаться🌴", url=CHANNEL_URL)
        kb_sub.button(text="Проверить подписку", callback_data="check_subscription")
        kb_sub.adjust(1)
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=BANNER_URL,
                caption="Сначала подпишись на канал, чтоб не потерять нас:",
                parse_mode="HTML"
            ),
            reply_markup=kb_sub.as_markup()
        )
        await query.answer()
        return

    # 1) Создаём новый счёт 1Plat (crypto)
    try:
        guid, pay_link = create_1plat_invoice(
            user_id=user_id,
            category=category,
            offset=offset,
            idx=idx,
            amount_rub=490,
            method="crypto",
            currency="USDT",
            email=""
        )
    except Exception as e:
        await query.answer("❌ Не удалось создать счёт 1Plat (crypto). Попробуйте позже.", show_alert=True)
        print(f"[pay_1plat_crypto] Ошибка при создании счета 1Plat (crypto): {e}")
        return

    # 2) Сохраняем guid
    key_1p = make_invoice_key(user_id, category, offset, idx)
    with INVOICES_1PLAT_LOCK:
        INVOICES_1PLAT[key_1p] = guid
    save_invoices_1plat()

    # 3) Отправляем карточку с кнопками «Оплатить (1Plat)» и «🔄 Проверить оплату 1Plat»
    caption = (
        "<b>⚡ Чтобы получить доступ к курсу, оплатите счёт 1Plat ниже (crypto).</b>\n\n"
        "Сумма: <code>490 ₽</code>\n"
        "1Plat пересчитает её в USDT.\n\n"
        "Нажмите кнопку «Оплатить крипто (1Plat)», чтобы перейти на страницу оплаты.\n\n"
        "После оплаты нажмите «🔄 Проверить оплату 1Plat».")
    kb = InlineKeyboardBuilder()
    kb.button(text="Оплатить крипто (1Plat)", url=pay_link)
    kb.button(text="🔄 Проверить оплату 1Plat", callback_data=f"check_payment_1plat|{category}|{offset}|{idx}")
    kb.button(text="🔙 Вернуться", callback_data=f"pay_options|{category}|{offset}|{idx}")
    kb.adjust(1)

    await bot.send_photo(
        chat_id=user_id,
        photo=BANNER_URL,
        caption=caption,
        reply_markup=kb.as_markup()
    )
    await query.answer()


# ----- MemePay callbacks -----
@dp.callback_query(lambda c: c.data.startswith("pay_memepay|"))
async def pay_memepay_callback(query: CallbackQuery):
    # Разбираем данные
    _, category, offset_str, idx_str = query.data.split("|", 3)
    offset = int(offset_str)
    idx = int(idx_str)
    user_id = query.from_user.id

    # Проверяем подписку на канал
    member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
    if member.status not in ("creator", "administrator", "member"):
        kb = InlineKeyboardBuilder()
        kb.button(text="Подписаться🌴", url=CHANNEL_URL)
        kb.button(text="Проверить подписку", callback_data="check_subscription")
        kb.adjust(1)
        await query.message.edit_media(
            media=InputMediaPhoto(media=BANNER_URL,
                                  caption="Сначала подпишись на канал, чтобы продолжить:",
                                  parse_mode="HTML"),
            reply_markup=kb.as_markup(),
        )
        return

    # Создаём платёж через MemePay
    try:
        payment_id, pay_link = create_memepay_invoice(amount_rub=490.0)
        key_mp = make_invoice_key(user_id, category, offset, idx)
        with INVOICES_MEMEPAY_LOCK:
            INVOICES_MEMEPAY[key_mp] = payment_id
        save_invoices_memepay()
    except Exception as e:
        await query.answer("❌ Не удалось создать счёт через MemePay. Попробуйте позже.", show_alert=True)
        print(f"[pay_memepay] Ошибка при создании платежа: {e}")
        return

    # Отправляем карточку с кнопками оплаты и проверки
    caption = (
        "<b>⚡ Чтобы получить доступ к курсу, оплатите через MemePay:</b>\n\n"
        "Сумма: <code>490 ₽</code>\n\n"
        "Нажмите «Оплатить в MemePay🤪», чтобы перейти к оплате.\n"
        "После оплаты нажмите «🔄 Проверить оплату»."
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="Оплатить в MemePay🤪", url=pay_link)
    kb.button(text="🔄 Проверить оплату", callback_data=f"check_payment_memepay|{category}|{offset}|{idx}")
    kb.button(text="🔙 Вернуться", callback_data=f"pay_options|{category}|{offset}|{idx}")
    kb.adjust(1)

    await bot.send_photo(chat_id=user_id, photo=BANNER_URL, caption=caption, reply_markup=kb.as_markup())
    await query.answer()


@dp.callback_query(lambda c: c.data.startswith("check_payment_memepay|"))
async def check_payment_memepay_callback(query: CallbackQuery):
    # Парсим ключ
    _, category, offset_str, idx_str = query.data.split("|", 3)
    offset, idx = int(offset_str), int(idx_str)
    user_id = query.from_user.id
    key_mp = make_invoice_key(user_id, category, offset, idx)

    payment_id = INVOICES_MEMEPAY.get(key_mp)
    if not payment_id:
        await query.answer("❌ Счёт не найден. Сначала нажмите «Оплатить».", show_alert=True)
        return

    try:
        status = check_memepay_status(payment_id)
    except Exception as e:
        await query.answer("❌ Не удалось проверить оплату MemePay. Попробуйте позже.", show_alert=True)
        print(f"[check_payment_memepay] Ошибка при getPaymentInfo: {e}")
        return

    if status in ("payed", "completed"):
        # Убираем из INVOICES и даём доступ
        with INVOICES_MEMEPAY_LOCK:
            INVOICES_MEMEPAY.pop(key_mp, None)
        save_invoices_memepay()
        add_subscription(user_id)
        await query.answer("✅ Оплата MemePay подтверждена! Доступ к курсу ниже.", show_alert=True)

        cr = get_courses_by_category(category, offset, 10)[idx]
        title = cr["Название"]
        cover = cr.get("Обложка") or BANNER_URL
        link = cr.get("Ссылка на курс", "")
        caption = f"🎉 <b>{title}</b>\n\nТеперь у вас есть доступ к материалам:"
        kb = InlineKeyboardBuilder()
        if link:
            kb.button(text="💎 Перейти к изучению", url=link)
        kb.adjust(1)
        await bot.send_photo(chat_id=user_id, photo=cover, caption=caption, reply_markup=kb.as_markup())
    else:
        await query.answer(f"⌛ Статус платежа: {status}. Подождите и попробуйте снова.", show_alert=True)


@dp.callback_query(lambda c: c.data.startswith("pay_1plat_sbp|"))
async def pay_1plat_sbp_callback(query: CallbackQuery):
    """
    Callback «pay_1plat_sbp|<category>|<offset>|<idx>»:
    1) Убедимся, что пользователь подписан на канал.
    2) Создаём счёт через 1Plat (SBP).
    3) Сохраняем guid в invoices_1plat.json.
    4) Отправляем карточку «Оплатить SBP (1Plat)» + «🔄 Проверить оплату 1Plat» + «🔙 Вернуться».
    """
    _, category, offset_str, idx_str = query.data.split("|", 3)
    offset = int(offset_str)
    idx = int(idx_str)
    user_id = query.from_user.id

    member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
    if member.status not in ("creator", "administrator", "member"):
        kb_sub = InlineKeyboardBuilder()
        kb_sub.button(text="Подписаться🌴", url=CHANNEL_URL)
        kb_sub.button(text="Проверить подписку", callback_data="check_subscription")
        kb_sub.adjust(1)
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=BANNER_URL,
                caption="Сначала подпишись на канал, чтоб не потерять нас:",
                parse_mode="HTML"
            ),
            reply_markup=kb_sub.as_markup()
        )
        await query.answer()
        return

    # 1) Создаём новый счёт 1Plat (SBP)
    try:
        guid, pay_link = create_1plat_invoice(
            user_id=user_id,
            category=category,
            offset=offset,
            idx=idx,
            amount_rub=490,
            method="sbp",
            currency=None,
            email=""
        )
    except Exception as e:
        await query.answer("❌ Не удалось создать счёт 1Plat (SBP). Попробуйте позже.", show_alert=True)
        print(f"[pay_1plat_sbp] Ошибка при создании счета 1Plat (SBP): {e}")
        return

    # 2) Сохраняем guid
    key_1p = make_invoice_key(user_id, category, offset, idx)
    with INVOICES_1PLAT_LOCK:
        INVOICES_1PLAT[key_1p] = guid
    save_invoices_1plat()

    # 3) Отправляем карточку с кнопками «Оплатить SBP (1Plat)» и «🔄 Проверить оплату 1Plat»
    caption = (
        "<b>⚡ Чтобы получить доступ к курсу, оплатите счёт 1Plat ниже (SBP).</b>\n\n"
        "Сумма: <code>490 ₽</code>\n"
        "Оплатите через СБП по номеру телефона.\n\n"
        "Нажмите кнопку «Оплатить SBP (1Plat)», чтобы перейти на страницу оплаты.\n\n"
        "После оплаты нажмите «🔄 Проверить оплату 1Plat».")
    kb = InlineKeyboardBuilder()
    kb.button(text="Оплатить SBP (1Plat)", url=pay_link)
    kb.button(text="🔄 Проверить оплату 1Plat", callback_data=f"check_payment_1plat|{category}|{offset}|{idx}")
    kb.button(text="🔙 Вернуться", callback_data=f"pay_options|{category}|{offset}|{idx}")
    kb.adjust(1)

    await bot.send_photo(
        chat_id=user_id,
        photo=BANNER_URL,
        caption=caption,
        reply_markup=kb.as_markup()
    )
    await query.answer()


@dp.callback_query(lambda c: c.data.startswith("check_payment_1plat|"))
async def check_payment_1plat_callback(query: CallbackQuery):
    """
    Callback «check_payment_1plat|<category>|<offset>|<idx>»:
    1) Берём guid из invoices_1plat.json.
    2) GET /api/merchant/order/info/:guid/by-api → получаем status.
       • Если status == 0 → «Счёт ещё не оплачен…» (ожидание).
       • Если status in (1, 2) → оплата успешна:
           – удаляем запись из invoices_1plat.json,
           – добавляем user_id в PAID_USERS (paid_users.json),
           – отправляем карточку с прямыми ссылками.
       • Если status in (-2, -1) → «Отменён…» (нужно создать новый счёт).
    """
    _, category, offset_str, idx_str = query.data.split("|", 3)
    offset = int(offset_str)
    idx = int(idx_str)
    user_id = query.from_user.id

    key_1p = make_invoice_key(user_id, category, offset, idx)
    guid = INVOICES_1PLAT.get(key_1p)
    if not guid:
        await query.answer("❌ Счёт 1Plat не найден. Сначала нажмите «Оплатить».", show_alert=True)
        return

    try:
        status = check_1plat_invoice_status(guid)
    except Exception as e:
        await query.answer("❌ Не удалось проверить оплату 1Plat. Попробуйте позже.", show_alert=True)
        print(f"[check_payment_1plat] Ошибка при check_1plat_invoice_status для guid={guid}: {e}")
        return

    # status == 0 → ожидает оплаты
    if status == 0:
        await query.answer("⌛ Платёж 1Plat ещё не подтверждён. Подождите минуту и попробуйте снова.", show_alert=True)
        return

    # status == 1 или 2 → оплата успешна
    if status in (1, 2):
        # Удаляем запись
        with INVOICES_1PLAT_LOCK:
            INVOICES_1PLAT.pop(key_1p, None)
        save_invoices_1plat()

        # Добавляем пользователя в PAID_USERS
        add_subscription(user_id)
        await query.answer("✅ Оплата 1Plat подтверждена! Доступ к курсу ниже.", show_alert=True)

        cr = get_courses_by_category(category, offset, 10)[idx]
        title = cr["Название"]
        cover = cr.get("Обложка") or cr.get("Обложка (URL)", BANNER_URL)
        tele_desc = cr.get("", "").strip()
        course_link = cr.get("Ссылка на курс", "").strip()

        caption = f"🎉 <b>{title}</b>\n\nТеперь у вас есть доступ к материалам:"
        kb = InlineKeyboardBuilder()
        if tele_desc:
            kb.button(text="📓 Читать описание", url=tele_desc)
        if course_link:
            kb.button(text="💎 Перейти к изучению", url=course_link)
        kb.adjust(1)

        try:
            await bot.send_photo(
                chat_id=user_id,
                photo=cover,
                caption=caption,
                reply_markup=kb.as_markup()
            )
        except Exception as send_err:
            print(f"[check_payment_1plat] Не удалось отправить карточку курса user_id={user_id}: {send_err}")
        return

    # status == -2 или -1 → счёт отменён
    if status in (-2, -1):
        with INVOICES_1PLAT_LOCK:
            INVOICES_1PLAT.pop(key_1p, None)
        save_invoices_1plat()
        await query.answer(
            "❌ Срок оплаты 1Plat истёк или счёт отменён. Нажмите «🔙 Вернуться» и создайте новый счёт.",
            show_alert=True
        )
        return

    # Непредвиденные статусы
    await query.answer(f"⚠ Статус 1Plat: «{status}». Возможно, платёж не завершён.", show_alert=True)


# =========================================
# Фоновая проверка счетов 1Plat
# =========================================
# =========================================
# 11. ЗАПУСК POLLING
# =========================================

async def main():
    print("Запускаем polling Telegram…")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())