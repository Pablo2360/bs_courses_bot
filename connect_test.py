import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Настройка доступа к Google Sheets
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Точный ID таблицы из ссылки
spreadsheet_id = "1RP-8VTd4RTf92mR426MXznRw8f_-hWbrgyon6ar33-8"
sheet = client.open_by_key(spreadsheet_id).sheet1

# Проверка: выводим первую строку
print("Первая строка таблицы:")
print(sheet.row_values(1))
