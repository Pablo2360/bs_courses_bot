#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# === Константы ===
SHEET_ID   = "1RP-8VTd4RTf92mR426MXznRw8f_-hWbrgyon6ar33-8"
SHEET_NAME = "TELEGRAM"

# === Авторизация ===
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)

# === Google Sheets ===
gc    = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
data  = sheet.get_all_values()

# === Google Docs & Drive ===
docs_service  = build("docs", "v1", credentials=creds)
drive_service = build("drive", "v3", credentials=creds)

for idx, row in enumerate(data[1:], start=2):
    try:
        # Проверяем минимум 6 колонок
        if len(row) < 6:
            row += [""] * (6 - len(row))

        title     = row[2].strip()   # C: название курса
        desc      = row[3].strip()   # D: описание
        image_url = row[1].strip()   # B: URL картинки
        doc_link  = row[5].strip()   # F: уже существующая ссылка

        # Пропускаем, если нет названия или описания
        if not title or not desc:
            print(f"[{idx}] пропущено (нет названия или описания)")
            continue

        # Пропускаем, если ссылка уже есть
        if doc_link.startswith("http"):
            print(f"[{idx}] пропущено (уже есть): {doc_link}")
            continue

        # 1) Создаём документ
        new_doc = docs_service.documents().create(body={"title": title}).execute()
        doc_id  = new_doc["documentId"]

        requests = []
        current_index = 1

        # 2) Вставляем изображение (если есть)
        if image_url:
            requests.append({
                "insertInlineImage": {
                    "location": {"index": current_index},
                    "uri": image_url,
                    "objectSize": {
                        "width":  {"magnitude": 500, "unit": "PT"},
                        "height": {"magnitude": 280, "unit": "PT"}
                    }
                }
            })
            # После картинки — 4 переноса строки
            newlines = "\n" * 4
            requests.append({
                "insertText": {
                    "location": {"index": current_index + 1},
                    "text": newlines
                }
            })
            current_index += 1 + len(newlines)

        # 3) Вставляем заголовок ("title\n\n")
        header_text = title + "\n\n"
        requests.append({
            "insertText": {
                "location": {"index": current_index},
                "text": header_text
            }
        })
        start_header = current_index
        end_header   = start_header + len(header_text)
        # Стилизация заголовка: жирный, 20pt
        requests.append({
            "updateTextStyle": {
                "range": {"startIndex": start_header, "endIndex": end_header},
                "textStyle": {
                    "bold": True,
                    "fontSize": {"magnitude": 20, "unit": "PT"}
                },
                "fields": "bold,fontSize"
            }
        })

        # 4) Вставляем описание ("desc\n") сразу после заголовка
        desc_text = desc + "\n"
        requests.append({
            "insertText": {
                "location": {"index": end_header},
                "text": desc_text
            }
        })
        start_desc = end_header
        end_desc   = start_desc + len(desc_text)
        # Стилизация описания: 12pt
        requests.append({
            "updateTextStyle": {
                "range": {"startIndex": start_desc, "endIndex": end_desc},
                "textStyle": {"fontSize": {"magnitude": 12, "unit": "PT"}},
                "fields": "fontSize"
            }
        })

        # 5) Отправляем batchUpdate
        try:
            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": requests}
            ).execute()
        except HttpError as e:
            error_body = e.content.decode()
            if "Invalid requests" in error_body and "updateTextStyle" in error_body:
                # Удаляем запрос стилизации описания
                requests = [
                    r for r in requests
                    if not (r.get("updateTextStyle") and r["updateTextStyle"]["range"] == {"startIndex": start_desc, "endIndex": end_desc})
                ]
                docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={"requests": requests}
                ).execute()
            else:
                raise

        # 6) Делаем документ доступным по ссылке
        drive_service.permissions().create(
            fileId=doc_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        # 7) Получаем webViewLink (просмотр без входа)
        meta = drive_service.files().get(
            fileId=doc_id,
            fields="webViewLink"
        ).execute()
        public_url = meta.get("webViewLink")

        # 8) Сохраняем ссылку в таблице
        sheet.update_cell(idx, 6, public_url)
        print(f"[{idx}] готово → {public_url}")

        time.sleep(1)

    except Exception as e:
        print(f"[{idx}] ошибка: {e}")
        continue
