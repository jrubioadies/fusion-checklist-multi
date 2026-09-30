#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

python3 -m venv .buildvenv
# -r requirements.txt en vez de una lista suelta: el motor SOAP ya no es un
# fbip.py junto a este script, es el paquete fusion-client, y sólo el
# requirements.txt sabe de dónde se descarga. De paso entra openpyxl, que la
# lista suelta se dejaba fuera aunque app.py lo usa para exportar a Excel.
.buildvenv/bin/pip install --upgrade pip
.buildvenv/bin/pip install -r requirements.txt

# --collect-all fusion_client en vez de --hidden-import fusion_client.bip:
# fusion_client es ahora un paquete instalado, no un módulo suelto. --collect-all
# arrastra todos sus submódulos (bip, ess, errors) y los metadatos de la
# distribución de una vez. openpyxl va igual porque app.py lo importa dentro de
# una función y el análisis estático de PyInstaller no lo ve.
.buildvenv/bin/pyinstaller --onefile --name FusionChecklist \
  --paths . --collect-all fusion_client --collect-all openpyxl \
  --hidden-import checklist --hidden-import profiles --collect-all keyring \
  --clean --noconfirm app.py

echo
echo "✅ Listo -> dist/FusionChecklist"
