# DAN Web API + arayuz (http://localhost:8124)
# 8000 Manager.exe, 8123 ClickHouse tarafindan tutuldugu icin 8124 kullanilir.
.\venv\Scripts\python.exe -m uvicorn src.api.app:app --host 127.0.0.1 --port 8124
