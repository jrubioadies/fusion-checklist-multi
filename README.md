# Fusion Checklist — Configuration Comparator

Compares Oracle Fusion Cloud configuration across environments (PROD, DEV1, DEV2, TEST).

39 checklist items covering GL, AP, AR, Fixed Assets, Cash Management, Procurement and Intercompany — each with a SQL query that counts entities via BI Publisher.

## Features

- **Multi-environment comparison** — Run all 39 items against 4 environments in parallel
- **Detail view** — Click any count to see the actual records
- **Diff view** — Click "diferencias" to see which records exist in which environments
- **Business Unit filter** — Filter by BU across all items
- **Module/method filters** — Filter by GL, AP, AR, etc. and by config method (REST, FBDI, UI)

## Quick start

```bash
pip install -r requirements.txt
python app.py
```

> `requirements.txt` pulls in [`fusion-client`](https://github.com/jrubioadies/fusion-client)
> (the shared BI Publisher SOAP engine) straight from git, so `pip install requests`
> on its own is no longer enough.

Opens http://127.0.0.1:8900 — log in with your Oracle Fusion credentials.

## Build executable

```bash
# Linux/macOS
bash build.sh

# Windows
build.bat
```

## Configuration

Uses the same config file as Fusion Data Studio: `~/.config/fusion-bip/config.json`

```json
{
  "environments": {
    "PROD": { "base": "https://xxx-fa-ext.oraclecloud.com", "user": "...", "pass": "..." },
    "DEV1": { "base": "...", "user": "...", "pass": "..." }
  }
}
```
