import gspread
from google.oauth2.service_account import Credentials
import os

SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

credentials = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

gc = gspread.authorize(credentials)

def buscar_coincidencias(sheet_id, campos_extraidos):
    try:
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.sheet1 

        registros = worksheet.get_all_records()
        coincidencias = []

        for fila in registros:
            match = True
            for campo, valor in campos_extraidos.items():
                if str(fila.get(campo, "")).strip().lower() != str(valor).strip().lower():
                    match = False
                    break
            if match:
                coincidencias.append(fila)

        return coincidencias
    except Exception as e:
        return {"error": str(e)}
