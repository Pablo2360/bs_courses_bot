import gspread
from oauth2client.service_account import ServiceAccountCredentials
import threading
from time import time
from typing import List, Dict

# 1) Скоупы доступа
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# 2) Креды сервисного аккаунта
CREDS = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPES)
CLIENT = gspread.authorize(CREDS)

# 3) ID вашей таблицы
SPREADSHEET_ID = "1RP-8VTd4RTf92mR426MXznRw8f_-hWbrgyon6ar33-8"

# 🗄️ Кэш для каждой вкладки: 
#     ключ — название листа (категории), значение — список словарей из этого листа
_CACHE: Dict[str, List[Dict]] = {}
_CACHE_LOCK = threading.Lock()
_CACHE_LOADED_AT: Dict[str, float] = {}
# TTL в секундах; если нужно всегда брать из памяти, оставьте очень большим
_CACHE_TTL = 3600  


def _find_worksheet_by_name(sh: gspread.Spreadsheet, category: str):
    """
    Попытка найти лист (worksheet) в книге sh, название которого совпадает
    с category (регистр игнорируется). Если ничего не найдено, кидает WorksheetNotFound.
    """
    lower_cat = category.strip().lower()
    for ws in sh.worksheets():
        if ws.title.strip().lower() == lower_cat:
            return ws
    # Если дошли до конца цикла — листа нет
    raise gspread.exceptions.WorksheetNotFound(f"Лист «{category}» не найдено в таблице")


def _load_sheet_cache(sheet_name: str):
    """
    Загружает в кэш данные именно из листа с названием sheet_name (регистр неважен).
    """
    global _CACHE, _CACHE_LOADED_AT
    sh = CLIENT.open_by_key(SPREADSHEET_ID)
    try:
        worksheet = _find_worksheet_by_name(sh, sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        # Если листа нет — заполняем пустым списком и запоминаем "время загрузки"
        _CACHE[sheet_name] = []
        _CACHE_LOADED_AT[sheet_name] = time()
        return

    records = worksheet.get_all_records()
    _CACHE[sheet_name] = records
    _CACHE_LOADED_AT[sheet_name] = time()


def get_courses_by_category(category: str, offset: int = 0, limit: int = 10) -> List[Dict]:
    """
    Берёт порцию курсов (limit штук) из листа <category>, начиная с позиции offset.
    Если листа с таким именем нет, возвращает пустой список.
    (category сравнивается с названиями листов без учёта регистра)
    """
    sheet_name = category.strip()
    with _CACHE_LOCK:
        # Если кэша нет или устарел — перезагрузим
        if (sheet_name not in _CACHE) or (time() - _CACHE_LOADED_AT.get(sheet_name, 0) > _CACHE_TTL):
            _load_sheet_cache(sheet_name)

    data = _CACHE.get(sheet_name, [])
    return data[offset : offset + limit]


def count_courses_by_category(category: str) -> int:
    """
    Считает общее число строк в листе <category> (регистр игнорируется).
    Если лист не найден, возвращает 0.
    """
    sheet_name = category.strip()
    with _CACHE_LOCK:
        if (sheet_name not in _CACHE) or (time() - _CACHE_LOADED_AT.get(sheet_name, 0) > _CACHE_TTL):
            _load_sheet_cache(sheet_name)

    data = _CACHE.get(sheet_name, [])
    return len(data)


def get_categories() -> List[str]:
    """
    Возвращает список названий всех вкладок (листов) в таблице.
    Полезно, если вы захотите собирать категории динамически.
    """
    sh = CLIENT.open_by_key(SPREADSHEET_ID)
    return [ws.title for ws in sh.worksheets()]


def get_all_courses() -> List[Dict]:
    """
    Возвращает плоский список всех курсов сразу из всех вкладок.
    Сейчас не используется, но может пригодиться.
    """
    courses = []
    for sheet_name in get_categories():
        with _CACHE_LOCK:
            if (sheet_name not in _CACHE) or (time() - _CACHE_LOADED_AT.get(sheet_name, 0) > _CACHE_TTL):
                _load_sheet_cache(sheet_name)
        courses.extend(_CACHE.get(sheet_name, []))
    return courses
