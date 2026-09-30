@echo off
cd /d "%~dp0"
REM -r requirements.txt en vez de una lista suelta: el motor SOAP ya no es un
REM fbip.py junto a este script, es el paquete fusion-client. De paso entra
REM openpyxl, que la lista suelta se dejaba fuera aunque app.py lo usa.
pip install -r requirements.txt
REM --collect-all fusion_client: es un paquete instalado, no un modulo suelto.
pyinstaller --onefile --name FusionChecklist --paths . --collect-all fusion_client --collect-all openpyxl --hidden-import checklist --clean --noconfirm app.py
echo.
echo Done -^> dist\FusionChecklist.exe
