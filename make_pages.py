#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegraph import Telegraph, exceptions as tg_exceptions

# --- Google Sheets access ---
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPE)
GC    = gspread.authorize(CREDS)

SPREADSHEET_ID = "1RP-8VTd4RTf92mR426MXznRw8f_-hWbrgyon6ar33-8"
SHEET_NAME     = "TELEGRAM"    # <- здесь имя листа

# --- Telegraph setup ---
tg = Telegraph()
tg.create_account(short_name="BS_COURSES")

def make_pages():
    sh    = GC.open_by_key(SPREADSHEET_ID)
    sheet = sh.worksheet(SHEET_NAME)
    data  = sheet.get_all_values()

    for idx, row in enumerate(data[1:], start=2):
        try:
            # гарантируем минимум 6 колонок
            if len(row) < 6:
                row += [''] * (6 - len(row))

            image_url = row[1].strip()  # колонка B
            title     = row[2].strip()  # колонка C
            desc      = row[3].strip()  # колонка D
            tele_link = row[5].strip()  # колонка F

            if tele_link.startswith("https://telegra.ph/"):
                print(f"[{idx}] пропущено (уже есть) → {tele_link}")
                continue

            # собираем HTML: сначала обложка, затем абзацы описания
            parts = []
            if image_url:
                parts.append(f'<figure><img src="{image_url}"/></figure>')
            for line in desc.split('\n'):
                if line.strip():
                    parts.append(f'<p>{line}</p>')
            html_content = "\n".join(parts)

            # flood control при создании страницы
            while True:
                try:
                    resp = tg.create_page(title=title, html_content=html_content)
                    page_url = "https://telegra.ph/" + resp["path"]
                    break
                except tg_exceptions.RetryAfterError as e:
                    wait = e.retry_after
                    print(f"[{idx}] flood, ждём {wait}s…")
                    time.sleep(wait + 1)

            sheet.update_cell(idx, 6, page_url)
            print(f"[{idx}] создано → {page_url}")

        except Exception as e:
            # не дам скрипту упасть — просто логируем ошибку и идём дальше
            print(f"[{idx}] ошибка: {e}")
            continue

if __name__ == "__main__":
    make_pages()
